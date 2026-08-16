"""Multi-epoch planet-frame template-bank search and null calibration."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
import json

import numpy as np
from astropy.time import Time

from .dedoppler import dedoppler_shifts, robust_block_normalize
from .orbit import DAY_S, celestial_frequency_factor, make_location, make_target


def load_scan(path: str | Path, keep_raw_data: bool = False) -> dict:
    path = Path(path)
    with np.load(path) as archive:
        data = archive["data"].copy()
        frequency = archive["frequency_mhz"].copy()
        metadata = json.loads(archive["metadata"].item())
    header = metadata["header"]
    times = Time(
        header["tstart"] + (np.arange(data.shape[0]) + 0.5) * header["tsamp"] / DAY_S,
        format="mjd", scale="utc",
    )
    result = {
        "path": str(path),
        "normalized": robust_block_normalize(data),
        "frequency_mhz": frequency, "metadata": metadata,
        "header": header, "times": times,
    }
    if keep_raw_data:
        result["data"] = data
    return result


def make_templates(config: dict) -> list[tuple[float, float]]:
    scales = config["search"]["projected_scales"]
    phases = config["search"]["phase_offsets_cycles"]
    return [(0.0, 0.0)] + [
        (float(scale), float(phase))
        for scale in scales if float(scale) != 0.0
        for phase in phases
    ]


def make_subsets(epoch_count: int, minimum_active_epochs: int = 2) -> list[tuple[int, ...]]:
    return [
        subset
        for size in range(minimum_active_epochs, epoch_count + 1)
        for subset in combinations(range(epoch_count), size)
    ]


def make_rest_grid(window: dict, channel_width_mhz: float) -> np.ndarray:
    half_bins = int(np.floor(window["rest_half_width_khz"] / 1000.0 / abs(channel_width_mhz)))
    return window["rest_center_mhz"] + np.arange(-half_bins, half_bins + 1) * abs(channel_width_mhz)


def template_vector(
    scan: dict,
    rest_frequency_mhz: np.ndarray,
    reference_frequency_mhz: float,
    projected_scale: float,
    phase_offset_cycles: float,
    config: dict,
) -> tuple[np.ndarray, dict]:
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    factor, observer, planet = celestial_frequency_factor(
        scan["times"], projected_scale, phase_offset_cycles,
        target, location, config["orbit"],
    )
    frequencies = scan["frequency_mhz"]
    df_mhz = float(frequencies[1] - frequencies[0])
    observed_track = reference_frequency_mhz * factor
    reference_indices = np.rint((observed_track - frequencies[0]) / df_mhz).astype(int)
    shifts = reference_indices - reference_indices[0]
    spectrum, margin = dedoppler_shifts(scan["normalized"], shifts)
    observed_needed = rest_frequency_mhz * factor[0]
    indices = np.rint((observed_needed - frequencies[0]) / df_mhz).astype(int)
    if indices.min() < margin or indices.max() >= spectrum.size - margin:
        raise RuntimeError(
            f"{scan['path']} does not cover the rest grid for "
            f"scale={projected_scale}, phase={phase_offset_cycles}"
        )
    duration_s = (scan["times"][-1] - scan["times"][0]).to_value("s")
    drift_hz_s = reference_frequency_mhz * 1e6 * (factor[-1] - factor[0]) / duration_s
    details = {
        "observer_start_m_s": float(observer[0]),
        "planet_start_m_s": float(planet[0]),
        "predicted_drift_hz_s": float(drift_hz_s),
        "max_track_shift_bins": int(margin),
    }
    return np.asarray(spectrum[indices], dtype=np.float32), details


def build_bank(
    scans: list[dict], rest_frequency_mhz: np.ndarray,
    reference_frequency_mhz: float, templates: list[tuple[float, float]], config: dict,
) -> tuple[np.ndarray, list[list[dict]]]:
    vectors = np.empty((len(templates), len(scans), rest_frequency_mhz.size), dtype=np.float32)
    details: list[list[dict]] = []
    for template_index, (scale, phase) in enumerate(templates):
        template_details = []
        for epoch, scan in enumerate(scans):
            vector, info = template_vector(
                scan, rest_frequency_mhz, reference_frequency_mhz,
                scale, phase, config,
            )
            vectors[template_index, epoch] = vector
            template_details.append(info)
        details.append(template_details)
    return vectors, details


def search_bank(
    vectors: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
    exclusion_mask: np.ndarray | None = None,
) -> dict:
    best: dict | None = None
    for template_index, (scale, phase) in enumerate(templates):
        for subset in subsets:
            active = vectors[template_index, list(subset)]
            if stack_statistic == "sum":
                stacked = np.sum(active, axis=0) / np.sqrt(len(subset))
            elif stack_statistic == "minimum_epoch":
                stacked = np.sqrt(len(subset)) * np.min(active, axis=0)
            else:
                raise ValueError(f"Unknown stack statistic: {stack_statistic}")
            if minimum_active_epoch_snr is not None:
                stacked = np.where(
                    np.all(active >= minimum_active_epoch_snr, axis=0), stacked, -np.inf
                )
            if exclusion_mask is not None:
                mask = exclusion_mask[template_index]
                if mask.ndim == 2:
                    mask = np.any(mask[list(subset)], axis=0)
                stacked = np.where(mask, -np.inf, stacked)
            frequency_index = int(np.nanargmax(stacked))
            record = {
                "snr": float(stacked[frequency_index]),
                "frequency_mhz": float(rest_frequency_mhz[frequency_index]),
                "frequency_index": frequency_index,
                "template_index": template_index,
                "projected_scale": scale,
                "phase_offset_cycles": phase,
                "active_epochs_zero_based": list(subset),
            }
            if best is None or record["snr"] > best["snr"]:
                best = record
    assert best is not None
    return best


def evaluate_record(vectors: np.ndarray, record: dict) -> float:
    subset = record["active_epochs_zero_based"]
    stacked = np.sum(vectors[record["template_index"], subset], axis=0) / np.sqrt(len(subset))
    return float(stacked[record["frequency_index"]])


def search_spectral_bank(
    vectors: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: list[int] | tuple[int, ...],
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
    exclusion_mask: np.ndarray | None = None,
) -> dict:
    """Search [width, orbital template, epoch, frequency] vectors."""
    if vectors.ndim != 4 or vectors.shape[0] != len(spectral_widths):
        raise ValueError("spectral bank shape does not match the width list")
    best: dict | None = None
    for width_index, width in enumerate(spectral_widths):
        record = search_bank(
            vectors[width_index], rest_frequency_mhz, templates, subsets,
            minimum_active_epoch_snr, stack_statistic,
            None if exclusion_mask is None else exclusion_mask[width_index],
        )
        record["spectral_width_channels"] = int(width)
        record["spectral_width_index"] = width_index
        if best is None or record["snr"] > best["snr"]:
            best = record
    assert best is not None
    return best


def evaluate_spectral_record(
    vectors: np.ndarray,
    record: dict,
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
) -> float:
    subset = record["active_epochs_zero_based"]
    active = vectors[record["spectral_width_index"], record["template_index"], subset]
    if stack_statistic == "sum":
        stacked = np.sum(active, axis=0) / np.sqrt(len(subset))
    elif stack_statistic == "minimum_epoch":
        stacked = np.sqrt(len(subset)) * np.min(active, axis=0)
    else:
        raise ValueError(f"Unknown stack statistic: {stack_statistic}")
    if minimum_active_epoch_snr is not None and not np.all(
        active[:, record["frequency_index"]] >= minimum_active_epoch_snr
    ):
        return float("-inf")
    return float(stacked[record["frequency_index"]])


def scramble_maxima(
    banks: dict[str, np.ndarray],
    subsets: list[tuple[int, ...]],
    n_scrambles: int,
    seed: int,
    min_shift_bins: int,
    minimum_active_epoch_snr: float | None = None,
    stack_statistic: str = "sum",
    exclusion_masks: dict[str, np.ndarray] | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Destroy inter-epoch coherence while preserving each marginal spectrum."""
    rng = np.random.default_rng(seed)
    global_maxima = np.full(n_scrambles, -np.inf)
    per_window = {key: np.full(n_scrambles, -np.inf) for key in banks}
    for scramble in range(n_scrambles):
        for key, bank in banks.items():
            if bank.ndim == 3:
                bank = bank[None, ...]
            if bank.ndim != 4:
                raise ValueError("bank must have [template, epoch, frequency] or [width, template, epoch, frequency]")
            nfreq = bank.shape[-1]
            exclusion_mask = None if exclusion_masks is None else exclusion_masks.get(key)
            if nfreq <= 2 * min_shift_bins:
                raise ValueError("Rest grid is too short for the requested scramble shift")
            shifts = [0] + [
                int(rng.integers(min_shift_bins, nfreq - min_shift_bins))
                for _ in range(bank.shape[2] - 1)
            ]
            rolled = [
                np.roll(bank[:, :, epoch, :], shifts[epoch], axis=-1)
                for epoch in range(bank.shape[2])
            ]
            rolled_masks = None
            if exclusion_mask is not None:
                if exclusion_mask.ndim == bank.ndim:
                    rolled_masks = [
                        np.roll(exclusion_mask[:, :, epoch, :], shifts[epoch], axis=-1)
                        for epoch in range(bank.shape[2])
                    ]
                elif exclusion_mask.ndim != bank.ndim - 1:
                    raise ValueError("exclusion mask has incompatible dimensions")
            window_max = -np.inf
            for subset in subsets:
                if stack_statistic == "sum":
                    stack = sum(rolled[epoch] for epoch in subset) / np.sqrt(len(subset))
                elif stack_statistic == "minimum_epoch":
                    stack = rolled[subset[0]].copy()
                    for epoch in subset[1:]:
                        np.minimum(stack, rolled[epoch], out=stack)
                    stack *= np.sqrt(len(subset))
                else:
                    raise ValueError(f"Unknown stack statistic: {stack_statistic}")
                if minimum_active_epoch_snr is not None:
                    eligible = rolled[subset[0]] >= minimum_active_epoch_snr
                    for epoch in subset[1:]:
                        eligible &= rolled[epoch] >= minimum_active_epoch_snr
                    stack[~eligible] = -np.inf
                if exclusion_mask is not None:
                    if rolled_masks is None:
                        stack[exclusion_mask] = -np.inf
                    else:
                        active_mask = rolled_masks[subset[0]].copy()
                        for epoch in subset[1:]:
                            active_mask |= rolled_masks[epoch]
                        stack[active_mask] = -np.inf
                window_max = max(window_max, float(np.nanmax(stack)))
            per_window[key][scramble] = window_max
            global_maxima[scramble] = max(global_maxima[scramble], window_max)
    return global_maxima, per_window


def empirical_p(observed: float, null_maxima: np.ndarray) -> float:
    return float((1 + np.count_nonzero(null_maxima >= observed)) / (null_maxima.size + 1))


def inject_track(
    scan: dict, rest_frequency_mhz: float, reference_frequency_mhz: float,
    projected_scale: float, phase_offset_cycles: float, target_snr: float, config: dict,
) -> dict:
    """Inject a nearest-bin ideal track; intended as a known-answer test."""
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    factor, _, _ = celestial_frequency_factor(
        scan["times"], projected_scale, phase_offset_cycles,
        target, location, config["orbit"],
    )
    frequencies = scan["frequency_mhz"]
    df_mhz = frequencies[1] - frequencies[0]
    observed = rest_frequency_mhz * factor
    indices = np.rint((observed - frequencies[0]) / df_mhz).astype(int)
    injected = dict(scan)
    injected["normalized"] = scan["normalized"].copy()
    injected["normalized"][np.arange(indices.size), indices] += target_snr / np.sqrt(indices.size)
    return injected
