"""LS4E v1 residual pulse diagnostic. Not a diffraction or origin classifier."""
from __future__ import annotations

import itertools
import math
import numpy as np


def channel_indices(fch1: float, foff: float, nchans: int, low: float, high: float) -> np.ndarray:
    """Include exactly channel centers in the closed requested frequency interval."""
    if not all(math.isfinite(x) for x in (fch1, foff, low, high)) or foff == 0:
        raise ValueError("invalid frequency geometry")
    if not isinstance(nchans, (int, np.integer)) or nchans < 1 or low > high:
        raise ValueError("invalid channel count or interval")
    centers = fch1 + np.arange(nchans, dtype=np.float64) * foff
    indices = np.flatnonzero((centers >= low) & (centers <= high))
    if len(indices) < 2:
        raise ValueError("requested band contains fewer than two channel centers")
    return indices


def detrend_region(values: np.ndarray, tile_samples: int) -> np.ndarray:
    """Remove a robust line independently in each tile, never across region edges.

    The line joins medians of the first/last quarter at their sample-center
    coordinates. A final partial tile uses the same rule at its own length.
    """
    residual = np.empty_like(values, dtype=np.float64)
    for start in range(0, len(values), tile_samples):
        block = values[start:start + tile_samples]
        quarter = max(1, len(block) // 4)
        first, last = np.median(block[:quarter]), np.median(block[-quarter:])
        xfirst, xlast = (quarter - 1) / 2, len(block) - (quarter + 1) / 2
        slope = (last - first) / (xlast - xfirst) if xlast > xfirst else 0.0
        residual[start:start + len(block)] = block - (first + slope * (np.arange(len(block)) - xfirst))
    return residual


def blocks(values: np.ndarray, width: int, offset: int, dt: float):
    count = len(values) // width
    means = values[:count * width].reshape(count, width).mean(axis=1)
    times = (offset + (np.arange(count) + 0.5) * width) * dt
    return means, times


def pulse_clusters(scores: np.ndarray, times: np.ndarray, threshold: float, merge_gap: float) -> list[dict]:
    above = np.flatnonzero(scores >= threshold)
    groups = []
    if not len(above):
        return groups
    splits = np.flatnonzero(np.diff(times[above]) > merge_gap) + 1
    for indices in np.split(above, splits):
        peak = indices[np.argmax(scores[indices])]
        groups.append({"first_center_s": float(times[indices[0]]), "last_center_s": float(times[indices[-1]]),
                       "peak_time_s": float(times[peak]), "peak_score": float(scores[peak]),
                       "above_threshold_blocks": int(len(indices))})
    return groups


def residual_metrics(values, dt: float, start: float, stop: float, settings: dict) -> dict:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)) or len(values) < 32:
        raise ValueError("non-finite, short or non-vector series")
    if not math.isfinite(dt) or dt <= 0 or not 0 <= start < stop <= len(values) * dt:
        raise ValueError("invalid timing")
    centers = (np.arange(len(values)) + 0.5) * dt
    lo, hi = np.searchsorted(centers, [start, stop], side="left")
    guard = settings["reference_guard_s"]
    before = int(np.searchsorted(centers, start - guard, side="left"))
    after = int(np.searchsorted(centers, stop + guard, side="left"))
    tile = max(4, round(settings["detrend_tile_s"] / dt))
    regions = [(0, values[:before]), (int(lo), values[lo:hi]), (after, values[after:])]
    residuals = [(offset, detrend_region(region, tile)) for offset, region in regions]
    records = []
    for requested in settings["pulse_width_s"]:
        width = max(1, round(requested / dt))
        summaries = [blocks(region, width, offset, dt) for offset, region in residuals]
        reference = np.concatenate([summaries[0][0], summaries[2][0]])
        if len(reference) < 32 or len(summaries[1][0]) < 3:
            raise ValueError("insufficient candidate or reference blocks")
        location = float(np.median(reference))
        scale = float(1.4826 * np.median(np.abs(reference - location)))
        if not math.isfinite(scale) or scale <= np.finfo(float).eps:
            raise ValueError("degenerate reference scale")
        clustered = []
        for means, times in summaries:
            scores = (means - location) / scale
            clustered.append(pulse_clusters(scores, times, settings["threshold"], settings["cluster_gap_s"]))
        records.append({"requested_width_s": requested, "effective_width_s": width * dt,
                        "reference_location": location, "reference_scale": scale,
                        "inside_pulses": clustered[1], "reference_pulses": clustered[0] + clustered[2],
                        "inside_block_count": len(summaries[1][0]), "reference_block_count": len(reference)})
    return {"sample_count": len(values), "sample_time_s": dt, "envelope_s": [start, stop], "scales": records}


def matched_pulses(left: list[dict], right: list[dict], tolerance: float) -> int:
    """Greedy chronological one-to-one matching; one event cannot count twice."""
    i = j = matched = 0
    while i < len(left) and j < len(right):
        delta = left[i]["peak_time_s"] - right[j]["peak_time_s"]
        if abs(delta) <= tolerance:
            matched += 1
            i += 1
            j += 1
        elif delta < 0:
            i += 1
        else:
            j += 1
    return matched


def compare_residuals(on: dict, off: dict, settings: dict) -> dict:
    if on["sample_count"] != off["sample_count"] or on["sample_time_s"] != off["sample_time_s"] or on["envelope_s"] != off["envelope_s"]:
        raise ValueError("ON/OFF geometry differs")
    widths = [x["requested_width_s"] for x in on["scales"]]
    if widths != settings["pulse_width_s"] or widths != [x["requested_width_s"] for x in off["scales"]]:
        raise ValueError("pulse banks differ")
    # This conservative diagnostic requires pulse-free controls at every width.
    off_veto = any(x["inside_pulses"] or x["reference_pulses"] for x in off["scales"])
    reference_veto = any(x["reference_pulses"] for x in on["scales"])
    support = []
    for a, b in itertools.combinations(on["scales"], 2):
        tolerance = max(a["effective_width_s"], b["effective_width_s"])
        count = matched_pulses(a["inside_pulses"], b["inside_pulses"], tolerance)
        if count >= settings["minimum_separated_pulses"]:
            support.append({"widths_s": [a["requested_width_s"], b["requested_width_s"]], "matched_pulse_count": count})
    return {"residual_pulse_pattern_pass": bool(support) and not off_veto and not reference_veto,
            "off_pulse_veto": bool(off_veto), "on_reference_pulse_veto": bool(reference_veto),
            "supporting_scale_pairs": support, "origin_inferred": False, "diffraction_model_fitted": False}
