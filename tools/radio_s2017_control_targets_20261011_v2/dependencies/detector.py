"""Prospective six-scan exploratory SETI detector; no data or jobs at import.

The statistic is an empirical robust box-track score, NOT turboSETI S/N or
calibrated sky significance. Every carrier's maximum and every ON threshold
carrier are retained. This module neither downloads nor opens observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.ndimage import median_filter


@dataclass(frozen=True)
class Scan:
    scan_id: str
    role: str
    power: np.ndarray
    tstart_mjd: float
    tsamp_s: float
    fch1_hz: float
    df_hz: float
    source_channel0: int
    normalization_source_channels: np.ndarray
    valid_mask: np.ndarray | None = None
    expected_nrows: int = 16


@dataclass(frozen=True)
class Config:
    max_drift_hz_s: float = 4.0
    widths: tuple[int, ...] = (1, 3, 9, 33)
    running_median_channels: int = 501
    on_threshold: float = 10.0
    off_threshold: float = 8.0
    carrier_count: int = 4096
    drift_tile: int = 16
    carrier_tile: int = 512
    match_tile: int = 64

    def check(self) -> None:
        if self.max_drift_hz_s != 4.0 or self.widths != (1, 3, 9, 33):
            raise ValueError("Different scientific search family requires a new freeze")
        if self.running_median_channels != 501:
            raise ValueError("Different preprocessing requires a new freeze")
        if self.on_threshold != 10 or self.off_threshold != 8:
            raise ValueError("Different thresholds require a new freeze")
        if self.carrier_count != 4096:
            raise ValueError("The scientific family requires all 4096 ON carriers")
        if any(x <= 0 for x in (self.carrier_count, self.drift_tile,
                                self.carrier_tile, self.match_tile)):
            raise ValueError("Positive dimensions required")


def cadence_geometry(scans: list[Scan], cfg: Config) -> dict[str, Any]:
    """Use actual file start epochs and gaps, never concatenate time rows."""
    cfg.check()
    if len(scans) != 6 or [s.role for s in scans] != ["ON", "OFF"] * 3:
        raise ValueError("Exactly six chronologically ordered ON/OFF scans required")
    if len({s.scan_id for s in scans}) != 6:
        raise ValueError("Unique scan identifiers required")
    anchor = min(s.tstart_mjd for s in scans)
    times = []
    previous_end = -np.inf
    for s in scans:
        p = np.asarray(s.power)
        if (p.ndim != 2 or p.shape[0] != s.expected_nrows or
                p.shape[0] < 2 or p.shape[1] < cfg.running_median_channels):
            raise ValueError(f"{s.scan_id}: complete declared two-dimensional rows required")
        if not np.isfinite([s.tstart_mjd, s.tsamp_s, s.fch1_hz, s.df_hz]).all():
            raise ValueError(f"{s.scan_id}: finite header coordinates required")
        if s.tsamp_s <= 0 or s.df_hz == 0:
            raise ValueError(f"{s.scan_id}: invalid integration/channel width")
        start = (s.tstart_mjd - anchor) * 86400.0
        if start < previous_end:
            raise ValueError("Scan integrations overlap or are not chronological")
        previous_end = start + p.shape[0] * s.tsamp_s
        times.append(start + (np.arange(p.shape[0]) + 0.5) * s.tsamp_s)
    first, last = times[0][0], times[-1][-1]
    span = float(last - first)
    tref = float((first + last) / 2.0)
    relative = [t - tref for t in times]
    min_df = min(abs(s.df_hz) for s in scans)
    n = int(np.ceil(cfg.max_drift_hz_s * span / min_df))
    grid = np.linspace(-cfg.max_drift_hz_s, cfg.max_drift_hz_s, 2*n + 1)
    grid[n] = 0.0
    step = float(grid[1] - grid[0])
    if step * span / min_df > 1.0 + 1e-12:
        raise ValueError("Half-grid displacement exceeds half a channel")
    return {"mjd_anchor": float(anchor), "tref_seconds_from_anchor": tref,
            "tref_mjd": float(anchor + tref/86400.0), "span_s": span,
            "max_abs_t_from_tref_s": float(max(np.max(np.abs(t)) for t in relative)),
            "times_from_tref_s": relative, "drift_grid_hz_s": grid,
            "drift_step_hz_s": step}


def _input_mask(s: Scan) -> np.ndarray:
    shape = s.power.shape
    if s.valid_mask is None:
        return np.ones(shape, dtype=bool)
    m = np.asarray(s.valid_mask, dtype=bool)
    if m.ndim == 1 and m.size == shape[1]:
        m = np.broadcast_to(m, shape)
    if m.shape != shape:
        raise ValueError(f"{s.scan_id}: mask shape mismatch")
    return m


def preprocess(s: Scan, cfg: Config) -> tuple[np.ndarray, np.ndarray, dict]:
    """Normalize on frozen static source channels, not data-selected regions."""
    p = np.asarray(s.power, dtype=np.float64)
    if not np.isfinite(p).all() or np.any(p < 0):
        raise ValueError(f"{s.scan_id}: non-finite/missing or negative power is an input error")
    m = _input_mask(s)
    source = np.asarray(s.normalization_source_channels, dtype=np.int64)
    if (source.ndim != 1 or len(source) != cfg.carrier_count or
            len(np.unique(source)) != len(source)):
        raise ValueError(f"{s.scan_id}: unique frozen normalization core required")
    local = source - s.source_channel0
    margin = cfg.running_median_channels//2
    if local.min() < margin or local.max() >= p.shape[1] - margin:
        raise ValueError(f"{s.scan_id}: normalization core lacks filtering margin")
    core = np.where(m[:, local], p[:, local], np.nan)
    core_count = m[:, local].sum(axis=1)
    if np.any(core_count == 0):
        raise ValueError(f"{s.scan_id}: entirely masked normalization row")
    row_level = np.nanmedian(core, axis=1)
    if np.any(row_level <= 0) or not np.isfinite(row_level).all():
        raise ValueError(f"{s.scan_id}: invalid row power median")
    normalized = p / row_level[:, None]
    residual = normalized - median_filter(normalized, size=(1, cfg.running_median_channels),
                                           mode="nearest")
    center = np.nanmedian(np.where(m[:, local], residual[:, local], np.nan), axis=1)
    scale = 1.4826 * np.nanmedian(np.where(m[:, local],
                       np.abs(residual[:, local] - center[:, None]), np.nan), axis=1)
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError(f"{s.scan_id}: invalid empirical residual MAD")
    centered_core = residual[:, local] - center[:, None]
    winsorized = np.clip(centered_core, -5*scale[:, None], 5*scale[:, None])
    location = center + np.nanmean(np.where(m[:, local], winsorized, np.nan), axis=1)
    z = (residual - location[:, None]) / scale[:, None]
    return z, m, {"row_power_median": row_level.tolist(),
                  "row_residual_median": center.tolist(),
                  "row_winsorized_residual_location": location.tolist(),
                  "row_residual_MAD_scale": scale.tolist(),
                  "normalization_unmasked_counts": core_count.tolist(),
                  "normalization_source_channels": source.tolist()}


def _box_arrays(z: np.ndarray, mask: np.ndarray, cfg: Config) -> dict:
    # Prefix sums form four cached row-box arrays. Search needs one score
    # gather and one validity gather per row, rather than two prefix pairs.
    prefix = np.zeros((z.shape[0], z.shape[1] + 1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    bad = np.zeros(prefix.shape, dtype=np.int32)
    bad[:, 1:] = np.cumsum(~mask, axis=1, dtype=np.int32)
    return {width: (prefix[:, width:] - prefix[:, :-width],
                    (bad[:, width:] - bad[:, :-width]) == 0) for width in cfg.widths}


def _score_tile(boxes: dict, base: np.ndarray, times: np.ndarray,
                df_hz: float, drifts: np.ndarray, width: int,
                source_channel0: int) -> tuple[np.ndarray, np.ndarray]:
    box, unmasked = boxes[width]
    score = np.zeros((drifts.size, base.size), dtype=np.float64)
    valid = np.ones(score.shape, dtype=bool)
    radius = width//2
    for row, time in enumerate(times):
        # Round complete absolute-frequency mapping, not a separately rounded
        # base plus drift. Round ABSOLUTE SOURCE channel before subtracting
        # the loaded-channel offset; local parity can differ at exact half ties.
        center = (np.rint(base[None, :] + drifts[:, None]*time/df_hz).astype(np.int64)
                  - source_channel0)
        index = center-radius
        if index.min() < 0 or index.max() >= box.shape[1]:
            raise ValueError("A declared carrier/hypothesis lacks full decoded halo")
        score += box[row, index]
        valid &= unmasked[row, index]
    score /= np.sqrt(times.size * width)
    score[~valid] = -np.inf
    return score, valid


def search_scan(s: Scan, frequencies_hz: np.ndarray, times: np.ndarray,
                drifts: np.ndarray, cfg: Config) -> tuple[dict, tuple]:
    z, mask, normalization = preprocess(s, cfg)
    boxes = _box_arrays(z, mask, cfg)
    base = (frequencies_hz - s.fch1_hz)/s.df_hz
    # Include median-filter support outside every widest trajectory.
    margin = cfg.running_median_channels//2 + max(cfg.widths)//2
    extremes = np.concatenate([base + d*t/s.df_hz for d in (drifts[0], drifts[-1])
                               for t in (times[0], times[-1])])
    rounded_local = np.rint(extremes).astype(np.int64) - s.source_channel0
    if rounded_local.min() < margin or rounded_local.max() >= z.shape[1]-margin:
        raise ValueError(f"{s.scan_id}: full family lacks preprocessing/width halo")
    best = np.full(base.size, -np.inf)
    best_drift = np.full(base.size, np.nan)
    best_width = np.zeros(base.size, dtype=np.int16)
    valid_counts = np.zeros(base.size, dtype=np.int64)
    for width in cfg.widths:
        for start in range(0, len(drifts), cfg.drift_tile):
            d = drifts[start:start+cfg.drift_tile]
            for lo in range(0, len(base), cfg.carrier_tile):
                hi = min(lo+cfg.carrier_tile, len(base))
                scores, valid = _score_tile(boxes, base[lo:hi], times, s.df_hz, d, width, s.source_channel0)
                valid_counts[lo:hi] += valid.sum(axis=0)
                arg = scores.argmax(axis=0)
                value = scores[arg, np.arange(hi-lo)]
                improve = value > best[lo:hi]
                locations = np.arange(lo, hi)[improve]
                best[locations] = value[improve]
                best_drift[locations] = d[arg[improve]]
                best_width[locations] = width
    return ({"scan_id": s.scan_id, "role": s.role, "frequency_hz_at_tref": frequencies_hz.copy(),
            "maximum_robust_box_track_score": best, "winning_drift_hz_s": best_drift,
            "winning_width_channels": best_width, "valid_hypothesis_count": valid_counts,
            "total_hypothesis_count_per_carrier": len(drifts)*len(cfg.widths),
            "normalization": normalization, "scan_midpoint_from_tref_s": float(times.mean()),
            "scan_midpoint_span_s": float(times[-1]-times[0]),
            "scan_first_time_from_tref_s": float(times[0]),
            "scan_last_time_from_tref_s": float(times[-1]), "df_hz": float(s.df_hz)},
           (boxes, base, times, s.source_channel0))


def _restricted_off_witness(on: dict, off: dict, arrays: tuple,
                            drifts: np.ndarray, grid_step: float, cfg: Config) -> dict:
    """Search every compatible OFF template until a >=8 witness is found.

    Never uses only an OFF winning drift. Width, ascending drift-tile,
    ascending carrier-tile, then drift/carrier within that tile is the frozen
    witness traversal. Early stopping proves the existential veto only; no
    maximum or complete match count is claimed for a stopped family.
    """
    boxes, base, times, source_channel0 = arrays
    df = max(abs(off["df_hz"]), abs(on["df_hz"]))
    first = on["scan_first_time_from_tref_s"]
    last = on["scan_last_time_from_tref_s"]
    span = last-first
    frequencies = off["frequency_hz_at_tref"]
    checked = 0
    maximum_checked_score = -np.inf
    for width in cfg.widths:
        channel_tolerance = (on["width_channels"] + width)/2.0 + 2.0
        endpoint_tolerance = channel_tolerance*df
        slope_bound = 2*endpoint_tolerance/span
        allowed = drifts[np.abs(drifts - on["drift_hz_s"]) <= slope_bound]
        for start in range(0, len(allowed), cfg.drift_tile):
            ds = allowed[start:start+cfg.drift_tile]
            dd = ds-on["drift_hz_s"]
            lower = np.maximum(-endpoint_tolerance-dd*first, -endpoint_tolerance-dd*last)
            upper = np.minimum(endpoint_tolerance-dd*first, endpoint_tolerance-dd*last)
            lo = on["reference_frequency_hz"] + lower.min()
            hi = on["reference_frequency_hz"] + upper.max()
            indices = np.flatnonzero((frequencies >= lo) & (frequencies <= hi))
            for begin in range(0, len(indices), cfg.carrier_tile):
                ix = indices[begin:begin+cfg.carrier_tile]
                delta_frequency = frequencies[ix][None,:] - on["reference_frequency_hz"]
                first_error = delta_frequency+dd[:,None]*first
                last_error = delta_frequency+dd[:,None]*last
                compatible = ((np.abs(first_error) <= endpoint_tolerance) &
                              (np.abs(last_error) <= endpoint_tolerance))
                scores, valid = _score_tile(boxes, base[ix], times, off["df_hz"], ds, width, source_channel0)
                values = np.where(compatible & valid, scores, -np.inf)
                witness = np.flatnonzero(values.ravel() >= cfg.off_threshold)
                if len(witness):
                    flat = int(witness[0])
                    checked += int((compatible & valid).sum())
                    maximum_checked_score = max(maximum_checked_score, float(values.max()))
                    i, j = np.unravel_index(flat, values.shape)
                    k = int(ix[j])
                    return {"scan_id": off["scan_id"], "veto": True,
                            "checked_valid_compatible_templates": checked,
                            "family_exhausted": False,
                            "maximum_checked_score": maximum_checked_score,
                            "witness": {"reference_carrier_index": k,
                                        "reference_frequency_hz": float(frequencies[k]),
                                        "drift_hz_s": float(ds[i]), "width_channels": int(width),
                                        "OFF_robust_score": float(values[i,j]),
                                        "endpoint_tolerance_hz": float(endpoint_tolerance),
                                        "ON_first_endpoint_error_hz": float(first_error[i,j]),
                                        "ON_last_endpoint_error_hz": float(last_error[i,j]),
                                        "ON_first_time_from_tref_s": float(first),
                                        "ON_last_time_from_tref_s": float(last)}}
                checked += int((compatible & valid).sum())
                maximum_checked_score = max(maximum_checked_score, float(values.max()))
    return {"scan_id": off["scan_id"], "veto": False,
            "checked_valid_compatible_templates": checked, "family_exhausted": True,
            "maximum_checked_score": maximum_checked_score, "witness": None}


def classify_hits(maps: list[dict], off_arrays: dict[str, tuple],
                  drifts: np.ndarray, grid_step: float, cfg: Config) -> list[dict]:
    rows = []
    for a in maps:
        if a["role"] != "ON":
            continue
        for j in np.flatnonzero(a["maximum_robust_box_track_score"] >= cfg.on_threshold):
            rec = {"scan_id": a["scan_id"], "reference_carrier_index": int(j),
                   "reference_frequency_hz": float(a["frequency_hz_at_tref"][j]),
                   "drift_hz_s": float(a["winning_drift_hz_s"][j]),
                   "width_channels": int(a["winning_width_channels"][j]),
                   "ON_robust_score": float(a["maximum_robust_box_track_score"][j]),
                   "scan_midpoint_from_tref_s": a["scan_midpoint_from_tref_s"],
                   "scan_midpoint_span_s": a["scan_midpoint_span_s"],
                   "scan_first_time_from_tref_s": a["scan_first_time_from_tref_s"],
                   "scan_last_time_from_tref_s": a["scan_last_time_from_tref_s"],
                   "df_hz": a["df_hz"], "OFF_comparisons": []}
            for b in maps:
                if b["role"] == "OFF":
                    rec["OFF_comparisons"].append(_restricted_off_witness(
                        rec, b, off_arrays[b["scan_id"]], drifts, grid_step, cfg))
            rec["disposition"] = ("OFF_MATCHED" if any(v["veto"] for v in rec["OFF_comparisons"])
                                  else "SURVIVOR_EXPLORATORY")
            rows.append(rec)
    return rows


def search_cadence(scans: list[Scan], reference_frequencies_hz: np.ndarray,
                   cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    f = np.asarray(reference_frequencies_hz, dtype=np.float64)
    if f.ndim != 1 or f.size != cfg.carrier_count or not np.isfinite(f).all():
        raise ValueError("Complete finite declared reference-carrier family required")
    if len(np.unique(f)) != len(f):
        raise ValueError("Duplicate declared reference carriers")
    g = cadence_geometry(scans, cfg)
    if not np.allclose(np.diff(f), scans[0].df_hz, rtol=1e-6, atol=1e-6):
        raise ValueError("ON carriers must be consecutive native reference-source channels")
    cmax = max(cfg.widths) + 2.0
    dfmax = max(abs(s.df_hz) for s in scans)
    scan_spans = [float(t[-1]-t[0]) for t in g["times_from_tref_s"]]
    slope_max = 2*cmax*dfmax/min(scan_spans) + 2*g["drift_step_hz_s"]
    max_midpoint = max(abs(float(t.mean())) for t in g["times_from_tref_s"])
    off_halo = int(np.ceil((cmax*dfmax + slope_max*max_midpoint)/abs(scans[0].df_hz)))
    off_frequencies = f[0] + np.arange(-off_halo, len(f)+off_halo)*scans[0].df_hz
    g["OFF_reference_halo_channels"] = off_halo
    maps, off_arrays = [], {}
    for s, t in zip(scans, g["times_from_tref_s"]):
        frequencies = f if s.role == "ON" else off_frequencies
        result, arrays = search_scan(s, frequencies, t, g["drift_grid_hz_s"], cfg)
        maps.append(result)
        if s.role == "OFF":
            off_arrays[s.scan_id] = arrays
    hits = classify_hits(maps, off_arrays, g["drift_grid_hz_s"], g["drift_step_hz_s"], cfg)
    return {"score_definition": "row-MAD-standardized odd-box track sum/sqrt(Nrow*width); no calibrated significance",
            "geometry": g, "scan_maps": maps, "all_ON_threshold_carriers": hits,
            "surviving_ON_threshold_carrier_count": sum(h["disposition"] == "SURVIVOR_EXPLORATORY" for h in hits),
            "limitations": ["Fixed linear tracks only", "OFF bank includes frozen compatibility halo around the declared ON carrier band",
                            "Compatible OFF templates are rescanned; no joint track fit", "No sky false-alarm calibration"]}


def control_inputs(arrays: list[np.ndarray], contract: dict) -> tuple[list[Scan], np.ndarray]:
    """Adapt the separately frozen control generator without generating values."""
    g = contract["geometry"]
    first, stop = g["reference_source_channel_interval"]
    loaded_first, loaded_stop = g["loaded_source_channel_interval"]
    if stop-first != 4096 or len(arrays) != 6:
        raise ValueError("Frozen complete six-scan, 4096-carrier control required")
    scans = []
    for power, h in zip(arrays, g["scan_metadata"]):
        if np.asarray(power).shape != (h["nrows"], loaded_stop-loaded_first):
            raise ValueError("Control array lacks complete declared rows/channel context")
        scans.append(Scan(scan_id=h["scan_id"], role=h["role"].upper(), power=power,
                          tstart_mjd=h["tstart_mjd"], tsamp_s=h["tsamp_s"],
                          fch1_hz=h["fch1_hz"], df_hz=h["df_hz"],
                          source_channel0=loaded_first,
                          normalization_source_channels=np.arange(first, stop),
                          expected_nrows=h["nrows"]))
    h = g["scan_metadata"][0]
    frequencies = h["fch1_hz"] + np.arange(first, stop)*h["df_hz"]
    return scans, frequencies


def recovery_matches(result: dict, truth: dict) -> dict:
    """Gate localized recovery on every declared active ON scan, before/after OFF.

    Truth requires active_ON_scan_ids, reference_frequency_hz, drift_hz_s,
    and flux_by_scan[scan_id].injection_oracle_width_channels (or explicit
    oracle_width_by_scan). Only the frozen noise-free oracle widths are used;
    observed output never changes truth tolerances. Localize the same linear
    trajectory at both integration midpoint endpoints of each active ON scan.
    """
    active = list(truth["active_ON_scan_ids"])
    if not active or len(active) != len(set(active)):
        raise ValueError("Distinct nonempty active-ON truth identifiers required")
    by_scan = {}
    for scan_id in active:
        if "oracle_width_by_scan" in truth:
            oracle = truth["oracle_width_by_scan"][scan_id]
        else:
            oracle = truth["flux_by_scan"][scan_id]["injection_oracle_width_channels"]
        raw, final = [], []
        for h in result["all_ON_threshold_carriers"]:
            if h["scan_id"] != scan_id:
                continue
            tolerance = (2.0 + max(h["width_channels"], oracle)/2.0)*abs(h["df_hz"])
            delta_f = h["reference_frequency_hz"]-truth["reference_frequency_hz"]
            delta_d = h["drift_hz_s"]-truth["drift_hz_s"]
            first_error = delta_f+delta_d*h["scan_first_time_from_tref_s"]
            last_error = delta_f+delta_d*h["scan_last_time_from_tref_s"]
            if max(abs(first_error), abs(last_error)) <= tolerance:
                raw.append(h)
                if h["disposition"] == "SURVIVOR_EXPLORATORY":
                    final.append(h)
        by_scan[scan_id] = {"pre_OFF_localized_recovery": bool(raw),
                            "final_localized_recovery": bool(final),
                            "pre_OFF_localized_count": len(raw), "final_localized_count": len(final),
                            "injection_oracle_width_channels": int(oracle)}
    all_raw = all(v["pre_OFF_localized_recovery"] for v in by_scan.values())
    all_final = all(v["final_localized_recovery"] for v in by_scan.values())
    return {"per_active_ON_scan": by_scan,
            "pre_OFF_all_active_recovery": all_raw, "final_all_active_recovery": all_final,
            "pre_OFF_any_active_recovery": any(v["pre_OFF_localized_recovery"] for v in by_scan.values()),
            "final_any_active_recovery": any(v["final_localized_recovery"] for v in by_scan.values()),
            "pre_OFF_localized_recovery": all_raw, "final_localized_recovery": all_final}
