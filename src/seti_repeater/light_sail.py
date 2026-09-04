"""Deterministic helpers for the LS1 broadband light-sail leakage search.

This module is deliberately separate from the frozen narrowband detector.  It
models only a prospective search template: short, broadband excess power near
a projected conjunction of two transiting planets.  Scores produced here are
screening statistics, not calibrated significances or technosignature claims.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


AU_PER_SOLAR_RADIUS = 0.00465047


@dataclass(frozen=True)
class CircularTransitPlanet:
    """Minimal circular, edge-on transit ephemeris used for archive ranking."""

    name: str
    period_days: float
    transit_midpoint_bjd: float
    semimajor_axis_au: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CircularTransitPlanet":
        return cls(
            name=str(value["name"]),
            period_days=float(value["period_days"]),
            transit_midpoint_bjd=float(value["transit_midpoint_bjd"]),
            semimajor_axis_au=float(value["semimajor_axis_au"]),
        )

    def validate(self) -> None:
        if not self.name or not math.isfinite(self.period_days) or self.period_days <= 0:
            raise ValueError("planet period and name must be valid")
        if not math.isfinite(self.transit_midpoint_bjd):
            raise ValueError("planet transit midpoint must be finite")
        if not math.isfinite(self.semimajor_axis_au) or self.semimajor_axis_au <= 0:
            raise ValueError("planet semimajor axis must be positive")


def circular_projected_coordinate_au(
    bjd: float, planet: CircularTransitPlanet
) -> float:
    """Return the signed sky-plane coordinate for a circular edge-on orbit.

    Transit midpoint is defined to have zero projected coordinate.  A common
    nodal line is assumed for all planets; this is a ranking approximation,
    not a fitted three-dimensional orbit.
    """

    planet.validate()
    if not math.isfinite(bjd):
        raise ValueError("BJD must be finite")
    phase_cycles = (bjd - planet.transit_midpoint_bjd) / planet.period_days
    return planet.semimajor_axis_au * math.sin(2.0 * math.pi * phase_cycles)


def projected_pair_separation_stellar_radii(
    bjd: float,
    first: CircularTransitPlanet,
    second: CircularTransitPlanet,
    stellar_radius_solar: float,
) -> float:
    """Projected one-dimensional separation in stellar radii."""

    if not math.isfinite(stellar_radius_solar) or stellar_radius_solar <= 0:
        raise ValueError("stellar radius must be positive")
    first_x = circular_projected_coordinate_au(bjd, first)
    second_x = circular_projected_coordinate_au(bjd, second)
    return abs(first_x - second_x) / (stellar_radius_solar * AU_PER_SOLAR_RADIUS)


def rank_cadences(
    cadences: Iterable[Mapping[str, Any]],
    first: CircularTransitPlanet,
    second: CircularTransitPlanet,
    stellar_radius_solar: float,
) -> list[dict[str, Any]]:
    """Rank cadence reference times by approximate projected separation."""

    records: list[dict[str, Any]] = []
    for cadence in cadences:
        cadence_id = str(cadence["cadence_id"])
        start_mjd = float(cadence["first_on_tstart_mjd"])
        duration_s = float(cadence["first_on_duration_s"])
        if not cadence_id or not math.isfinite(start_mjd) or duration_s <= 0:
            raise ValueError("cadence ranking input is invalid")
        reference_bjd = start_mjd + 2_400_000.5 + duration_s / (2.0 * 86_400.0)
        first_x = circular_projected_coordinate_au(reference_bjd, first)
        second_x = circular_projected_coordinate_au(reference_bjd, second)
        records.append(
            {
                "cadence_id": cadence_id,
                "first_on_tstart_mjd": start_mjd,
                "reference_bjd_utc_approximation": reference_bjd,
                "first_projected_coordinate_au": first_x,
                "second_projected_coordinate_au": second_x,
                "projected_pair_separation_stellar_radii": abs(first_x - second_x)
                / (stellar_radius_solar * AU_PER_SOLAR_RADIUS),
            }
        )
    records.sort(
        key=lambda item: (
            item["projected_pair_separation_stellar_radii"],
            item["first_on_tstart_mjd"],
            item["cadence_id"],
        )
    )
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
    return records


def _robust_location_scale(
    values: np.ndarray, axis: int
) -> tuple[np.ndarray, np.ndarray]:
    location = np.nanmedian(values, axis=axis)
    expanded = np.expand_dims(location, axis=axis)
    scale = 1.4826 * np.nanmedian(np.abs(values - expanded), axis=axis)
    return location, scale


def _coarse_normalized_spectrum(
    data: np.ndarray,
    base_bin_channels: int,
    clip_low: float,
    clip_high: float,
    minimum_valid_fraction: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Robustly normalize native channels and average fixed coarse bins."""

    if data.ndim != 2 or data.shape[0] < 8:
        raise ValueError("dynamic spectrum must be a time-by-frequency matrix")
    if base_bin_channels < 1 or data.shape[1] < base_bin_channels:
        raise ValueError("base frequency bin is outside the supplied spectrum")
    if not 0.0 < minimum_valid_fraction <= 1.0:
        raise ValueError("minimum valid fraction must lie in (0, 1]")
    complete_bins = data.shape[1] // base_bin_channels
    coarse = np.full((data.shape[0], complete_bins), np.nan, dtype=np.float32)
    valid_fraction = np.zeros(complete_bins, dtype=np.float32)
    for index in range(complete_bins):
        start = index * base_bin_channels
        stop = start + base_bin_channels
        block = np.asarray(data[:, start:stop], dtype=np.float32)
        finite_fraction = np.mean(np.isfinite(block), axis=0)
        location, scale = _robust_location_scale(block, axis=0)
        good = (
            (finite_fraction >= minimum_valid_fraction)
            & np.isfinite(location)
            & np.isfinite(scale)
            & (scale > np.finfo(np.float32).eps)
        )
        valid_fraction[index] = float(np.mean(good))
        if valid_fraction[index] < minimum_valid_fraction:
            continue
        normalized = (block[:, good] - location[good]) / scale[good]
        normalized = np.clip(normalized, clip_low, clip_high)
        coarse[:, index] = np.nanmean(normalized, axis=1, dtype=np.float32)
    return coarse, valid_fraction


def _rolling_sum(values: np.ndarray, width: int, axis: int) -> np.ndarray:
    if width < 1 or width > values.shape[axis]:
        raise ValueError("rolling width is outside the array")
    moved = np.moveaxis(values, axis, 0)
    padded = np.concatenate(
        [np.zeros_like(moved[:1]), np.cumsum(moved, axis=0, dtype=np.float64)],
        axis=0,
    )
    result = padded[width:] - padded[:-width]
    return np.moveaxis(result, 0, axis)


def _interval_overlap_fraction(
    first_start: float,
    first_stop: float,
    second_start: float,
    second_stop: float,
) -> float:
    intersection = max(0.0, min(first_stop, second_stop) - max(first_start, second_start))
    denominator = min(first_stop - first_start, second_stop - second_start)
    return intersection / denominator if denominator > 0.0 else 0.0


def _nonmaximum_suppression(
    events: Sequence[dict[str, Any]], maximum_events: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: (-item["score"], item["frequency_start_mhz"])):
        duplicate = False
        for accepted in selected:
            frequency_overlap = _interval_overlap_fraction(
                event["frequency_start_mhz"],
                event["frequency_stop_mhz"],
                accepted["frequency_start_mhz"],
                accepted["frequency_stop_mhz"],
            )
            time_overlap = _interval_overlap_fraction(
                event["time_start_s"],
                event["time_stop_s"],
                accepted["time_start_s"],
                accepted["time_stop_s"],
            )
            if frequency_overlap >= 0.8 and time_overlap >= 0.5:
                duplicate = True
                break
        if not duplicate:
            selected.append(event)
            if len(selected) == maximum_events:
                break
    return selected


def search_broadband_events(
    data: np.ndarray,
    frequency_mhz: np.ndarray,
    sample_time_s: float,
    *,
    base_bin_channels: int,
    spectral_width_bins: Sequence[int],
    duration_s: Sequence[float],
    minimum_score: float,
    maximum_events: int,
    clip_low: float = -6.0,
    clip_high: float = 12.0,
    minimum_valid_fraction: float = 0.8,
) -> dict[str, Any]:
    """Search a dynamic spectrum for short broadband boxcar excesses.

    Each native frequency channel is centered and scaled over time before
    averaging.  Fixed spectral and temporal boxcars are then scored after a
    second robust time normalization.  The method intentionally preserves
    time-local broadband power while suppressing persistent bandpass shape.
    """

    values = np.asarray(data, dtype=np.float32)
    frequencies = np.asarray(frequency_mhz, dtype=np.float64)
    if values.ndim != 2 or frequencies.ndim != 1 or values.shape[1] != len(frequencies):
        raise ValueError("data and frequency geometry disagree")
    if not math.isfinite(sample_time_s) or sample_time_s <= 0:
        raise ValueError("sample time must be positive")
    if maximum_events < 1 or not math.isfinite(minimum_score):
        raise ValueError("event retention settings are invalid")
    if frequencies[0] > frequencies[-1]:
        frequencies = frequencies[::-1].copy()
        values = values[:, ::-1].copy()
    coarse, valid_fraction = _coarse_normalized_spectrum(
        values,
        base_bin_channels,
        clip_low,
        clip_high,
        minimum_valid_fraction,
    )
    complete_channels = coarse.shape[1] * base_bin_channels
    base_start = frequencies[:complete_channels:base_bin_channels]
    base_stop = frequencies[base_bin_channels - 1 : complete_channels : base_bin_channels]
    all_events: list[dict[str, Any]] = []
    evaluated_templates = 0
    for spectral_width in spectral_width_bins:
        if spectral_width < 1 or spectral_width > coarse.shape[1]:
            raise ValueError("spectral template width is outside coarse spectrum")
        valid = np.isfinite(coarse).astype(np.float32)
        filled = np.nan_to_num(coarse, nan=0.0)
        sums = _rolling_sum(filled, spectral_width, axis=1)
        counts = _rolling_sum(valid, spectral_width, axis=1)
        spectral = np.divide(
            sums,
            counts,
            out=np.full_like(sums, np.nan, dtype=np.float64),
            where=counts >= spectral_width * minimum_valid_fraction,
        )
        location, scale = _robust_location_scale(spectral, axis=0)
        good_bands = np.isfinite(scale) & (scale > np.finfo(np.float64).eps)
        normalized = np.divide(
            spectral - location[np.newaxis, :],
            scale[np.newaxis, :],
            out=np.full_like(spectral, np.nan),
            where=good_bands[np.newaxis, :],
        )
        for requested_duration in duration_s:
            duration_samples = max(1, int(round(float(requested_duration) / sample_time_s)))
            if duration_samples > values.shape[0]:
                raise ValueError("time template exceeds scan duration")
            finite = np.isfinite(normalized).astype(np.float64)
            scores = _rolling_sum(np.nan_to_num(normalized, nan=0.0), duration_samples, 0)
            score_counts = _rolling_sum(finite, duration_samples, 0)
            scores = np.divide(
                scores,
                np.sqrt(float(duration_samples)),
                out=np.full_like(scores, np.nan),
                where=score_counts == duration_samples,
            )
            evaluated_templates += scores.shape[1]
            safe_scores = np.where(np.isfinite(scores), scores, -np.inf)
            maxima = np.max(safe_scores, axis=0)
            starts = np.argmax(safe_scores, axis=0)
            for band_index in np.flatnonzero(maxima >= minimum_score):
                start_sample = int(starts[band_index])
                all_events.append(
                    {
                        "score": float(maxima[band_index]),
                        "frequency_start_mhz": float(base_start[band_index]),
                        "frequency_stop_mhz": float(
                            base_stop[band_index + spectral_width - 1]
                        ),
                        "time_start_s": start_sample * sample_time_s,
                        "time_stop_s": (start_sample + duration_samples) * sample_time_s,
                        "spectral_width_bins": int(spectral_width),
                        "duration_samples": duration_samples,
                        "requested_duration_s": float(requested_duration),
                    }
                )
    retained = _nonmaximum_suppression(all_events, maximum_events)
    return {
        "ntime": int(values.shape[0]),
        "native_channel_count": int(values.shape[1]),
        "complete_native_channel_count": int(complete_channels),
        "base_frequency_bin_count": int(coarse.shape[1]),
        "valid_base_frequency_bin_count": int(np.sum(np.isfinite(coarse).all(axis=0))),
        "evaluated_band_duration_templates": int(evaluated_templates),
        "precluster_event_count": len(all_events),
        "retained_event_count": len(retained),
        "retention_truncated": len(retained) == maximum_events and len(all_events) > len(retained),
        "events": retained,
    }


def frequency_overlap_fraction(first: Mapping[str, Any], second: Mapping[str, Any]) -> float:
    return _interval_overlap_fraction(
        float(first["frequency_start_mhz"]),
        float(first["frequency_stop_mhz"]),
        float(second["frequency_start_mhz"]),
        float(second["frequency_stop_mhz"]),
    )


def apply_abacad_veto(
    scans: Sequence[Mapping[str, Any]],
    *,
    on_threshold: float,
    off_threshold: float,
    minimum_frequency_overlap: float,
) -> list[dict[str, Any]]:
    """Apply the frozen adjacent-OFF frequency-coincidence veto."""

    by_label = {str(scan["label"]): scan for scan in scans}
    candidates: list[dict[str, Any]] = []
    for scan in scans:
        if scan["role"] != "ON":
            continue
        adjacent = [by_label[label] for label in scan["adjacent_off_labels"]]
        for event in scan["search"]["events"]:
            if float(event["score"]) < on_threshold:
                continue
            vetoes: list[dict[str, Any]] = []
            for off_scan in adjacent:
                for off_event in off_scan["search"]["events"]:
                    overlap = frequency_overlap_fraction(event, off_event)
                    if float(off_event["score"]) >= off_threshold and overlap >= minimum_frequency_overlap:
                        vetoes.append(
                            {
                                "off_label": off_scan["label"],
                                "off_score": float(off_event["score"]),
                                "frequency_overlap_fraction": overlap,
                            }
                        )
            candidates.append(
                {
                    "on_label": scan["label"],
                    "event": dict(event),
                    "adjacent_off_vetoes": vetoes,
                    "survives_adjacent_off_veto": not vetoes,
                }
            )
    candidates.sort(key=lambda item: -float(item["event"]["score"]))
    return candidates
