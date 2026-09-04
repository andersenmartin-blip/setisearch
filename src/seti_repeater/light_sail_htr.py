"""High-time-resolution follow-up metrics for LS1 Stage 1 survivors."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np


def _location_scale(values: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size < 8:
        raise ValueError("too few finite reference samples")
    location = float(np.median(finite))
    scale = float(1.4826 * np.median(np.abs(finite - location)))
    if not math.isfinite(scale) or scale <= np.finfo(np.float64).eps:
        raise ValueError("reference scale is not positive")
    return location, scale


def _block_means(values: np.ndarray, samples: int) -> tuple[np.ndarray, np.ndarray]:
    if samples < 1:
        raise ValueError("block size must be positive")
    complete = len(values) // samples
    if complete < 1:
        raise ValueError("block size exceeds time series")
    trimmed = np.asarray(values[: complete * samples], dtype=np.float64)
    blocks = trimmed.reshape(complete, samples)
    return np.nanmean(blocks, axis=1), np.arange(complete, dtype=np.int64) * samples


def evaluate_timeseries(
    values: np.ndarray,
    sample_time_s: float,
    envelope_start_s: float,
    envelope_stop_s: float,
    pulse_width_s: Sequence[float],
    *,
    reference_guard_s: float,
    pulse_score_threshold: float,
) -> dict[str, Any]:
    """Evaluate one frequency-collapsed HTR series against its own baseline.

    Metrics are robust screening scores.  Serial correlation and the maximized
    template bank mean that they must not be interpreted as Gaussian sigma.
    """

    series = np.asarray(values, dtype=np.float64)
    if series.ndim != 1 or len(series) < 32:
        raise ValueError("HTR input must be a one-dimensional time series")
    if not math.isfinite(sample_time_s) or sample_time_s <= 0:
        raise ValueError("sample time must be positive")
    total_s = len(series) * sample_time_s
    start = max(0.0, float(envelope_start_s))
    stop = min(total_s, float(envelope_stop_s))
    if stop <= start:
        raise ValueError("candidate envelope does not overlap HTR scan")
    times = (np.arange(len(series), dtype=np.float64) + 0.5) * sample_time_s
    inside = (times >= start) & (times < stop)
    reference = (times < start - reference_guard_s) | (times >= stop + reference_guard_s)
    if np.sum(inside) < 8 or np.sum(reference) < 32:
        raise ValueError("candidate or reference interval is too short")
    location, scale = _location_scale(series[reference])
    normalized = (series - location) / scale
    envelope_score = float(np.nanmean(normalized[inside]) * math.sqrt(np.sum(inside)))
    scale_records: list[dict[str, Any]] = []
    for width_s in pulse_width_s:
        samples = max(1, int(round(float(width_s) / sample_time_s)))
        means, starts = _block_means(series, samples)
        centers = (starts + samples / 2.0) * sample_time_s
        block_inside = (centers >= start) & (centers < stop)
        block_reference = (centers < start - reference_guard_s) | (
            centers >= stop + reference_guard_s
        )
        block_location, block_scale = _location_scale(means[block_reference])
        scores = (means - block_location) / block_scale
        inside_scores = scores[block_inside & np.isfinite(scores)]
        reference_scores = scores[block_reference & np.isfinite(scores)]
        if inside_scores.size < 1:
            raise ValueError("pulse template has no candidate block")
        scale_records.append(
            {
                "requested_width_s": float(width_s),
                "width_samples": samples,
                "effective_width_s": samples * sample_time_s,
                "inside_block_count": int(inside_scores.size),
                "reference_block_count": int(reference_scores.size),
                "maximum_inside_score": float(np.max(inside_scores)),
                "maximum_reference_score": float(np.max(reference_scores)),
                "inside_blocks_at_threshold": int(
                    np.sum(inside_scores >= pulse_score_threshold)
                ),
            }
        )
    return {
        "sample_count": len(series),
        "sample_time_s": sample_time_s,
        "duration_s": total_s,
        "envelope_start_s": start,
        "envelope_stop_s": stop,
        "envelope_sample_count": int(np.sum(inside)),
        "reference_sample_count": int(np.sum(reference)),
        "touches_scan_start": start <= sample_time_s,
        "touches_scan_end": stop >= total_s - sample_time_s,
        "envelope_mean_screening_score": envelope_score,
        "pulse_scales": scale_records,
    }


def compare_on_off(
    on: dict[str, Any],
    off: dict[str, Any],
    *,
    envelope_on_threshold: float,
    envelope_off_veto_threshold: float,
    pulse_score_threshold: float,
    minimum_on_off_pulse_margin: float,
    required_subsecond_scales: int,
) -> dict[str, Any]:
    """Apply frozen HTR confirmation and adjacent-OFF rules."""

    on_envelope = float(on["envelope_mean_screening_score"])
    off_envelope = float(off["envelope_mean_screening_score"])
    adjacent_off_veto = off_envelope >= envelope_off_veto_threshold
    envelope_confirmed = (
        on_envelope >= envelope_on_threshold
        and on_envelope > off_envelope
        and not adjacent_off_veto
    )
    if len(on["pulse_scales"]) != len(off["pulse_scales"]):
        raise ValueError("ON and OFF pulse banks differ")
    supported_scales: list[dict[str, Any]] = []
    for on_scale, off_scale in zip(on["pulse_scales"], off["pulse_scales"], strict=True):
        if on_scale["requested_width_s"] != off_scale["requested_width_s"]:
            raise ValueError("ON and OFF pulse templates differ")
        if float(on_scale["requested_width_s"]) >= 1.0:
            continue
        margin = float(on_scale["maximum_inside_score"]) - float(
            off_scale["maximum_inside_score"]
        )
        if (
            float(on_scale["maximum_inside_score"]) >= pulse_score_threshold
            and margin >= minimum_on_off_pulse_margin
        ):
            supported_scales.append(
                {
                    "requested_width_s": on_scale["requested_width_s"],
                    "on_maximum_inside_score": on_scale["maximum_inside_score"],
                    "off_maximum_inside_score": off_scale["maximum_inside_score"],
                    "on_off_score_margin": margin,
                }
            )
    diffraction_supported = envelope_confirmed and len(supported_scales) >= required_subsecond_scales
    if adjacent_off_veto:
        disposition = "rejected-adjacent-off-htr-envelope"
    elif not envelope_confirmed:
        disposition = "not-confirmed-in-htr-envelope"
    elif diffraction_supported:
        disposition = "htr-structure-candidate-independent-observation-required"
    else:
        disposition = "htr-envelope-confirmed-without-required-subsecond-structure"
    return {
        "adjacent_off_htr_veto": adjacent_off_veto,
        "htr_envelope_confirmed": envelope_confirmed,
        "supported_subsecond_scale_count": len(supported_scales),
        "supported_subsecond_scales": supported_scales,
        "diffraction_structure_supported": diffraction_supported,
        "disposition": disposition,
    }
