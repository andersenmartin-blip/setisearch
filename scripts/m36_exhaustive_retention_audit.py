#!/usr/bin/env python3
"""Certify complete Milestone 36 retention above the frozen threshold.

This is a supplementary, fail-closed audit.  It deliberately does not modify
detector v0.5.0 or rerun its empirical null and completeness experiments.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import gzip
import hashlib
import importlib.metadata
import io
import json
import math
import platform
from pathlib import Path
from typing import Any, Iterable

import numpy as np

import seti_repeater
from seti_repeater import candidates as candidates_module
from seti_repeater import dedoppler as dedoppler_module
from seti_repeater import orbit as orbit_module
from seti_repeater import search as search_module
from seti_repeater import spectral as spectral_module
from seti_repeater.candidates import (
    annotate_local_off_vetoes,
    annotate_receiver_frame_aliases,
    apply_candidate_flags,
    build_single_epoch_rfi_mask,
    cluster_peaks,
    collect_hypothesis_peaks,
    detect_arithmetic_frequency_families,
)
from seti_repeater.orbit import make_location, make_target
from seti_repeater.search import (
    build_bank,
    evaluate_spectral_record,
    load_scan,
    make_rest_grid,
    make_subsets,
    make_templates,
    search_bank,
    search_spectral_bank,
)
from seti_repeater.spectral import make_spectral_bank, validate_widths


PHYSICAL_DISPOSITIONS = (
    "rfi_veto_off_source",
    "rfi_veto_local_off_source",
    "rfi_veto_single_adjacent_off",
    "rfi_veto_receiver_frame_alias",
)


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def json_safe(value: Any) -> Any:
    """Match detector JSON handling while rejecting ambiguous non-finite data."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def canonical_json_bytes(value: Any, *, pretty: bool = True) -> bytes:
    separators = None if pretty else (",", ":")
    return (
        json.dumps(
            json_safe(value),
            indent=2 if pretty else None,
            sort_keys=True,
            separators=separators,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def write_json(path: str | Path, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(value))


def verify_hash(path: str | Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise AssertionError(f"SHA-256 mismatch for {path}: {actual} != {expected}")


def verify_manifest_files(path: str | Path) -> None:
    for line in Path(path).read_text().splitlines():
        expected, filename = line.split(maxsplit=1)
        verify_hash(filename, expected)


def verify_environment(expected: dict[str, str]) -> None:
    observed = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "astropy": importlib.metadata.version("astropy"),
        "astropy_iers_data": importlib.metadata.version("astropy-iers-data"),
        "pyerfa": importlib.metadata.version("pyerfa"),
        "matplotlib": importlib.metadata.version("matplotlib"),
        "h5py": importlib.metadata.version("h5py"),
        "fsspec": importlib.metadata.version("fsspec"),
        "hdf5plugin": importlib.metadata.version("hdf5plugin"),
    }
    if observed != expected:
        raise AssertionError(
            f"frozen runtime mismatch: observed={observed}, expected={expected}"
        )


def verify_imported_detector(expected_version: str) -> None:
    expected_root = (Path.cwd() / "src" / "seti_repeater").resolve()
    modules = {
        "seti_repeater": seti_repeater,
        "candidates": candidates_module,
        "dedoppler": dedoppler_module,
        "orbit": orbit_module,
        "search": search_module,
        "spectral": spectral_module,
    }
    for name, module in modules.items():
        actual = Path(module.__file__).resolve()
        if actual.parent != expected_root:
            raise AssertionError(
                f"{name} imported from {actual}, not frozen repository {expected_root}"
            )
    if seti_repeater.__version__ != expected_version:
        raise AssertionError(
            f"detector version mismatch: {seti_repeater.__version__}"
        )


def interval_union_size(indices: list[int], radius: int, size: int) -> int:
    intervals: list[list[int]] = []
    for index in sorted(indices):
        left = max(0, index - radius)
        right = min(size - 1, index + radius)
        if intervals and left <= intervals[-1][1] + 1:
            intervals[-1][1] = max(intervals[-1][1], right)
        else:
            intervals.append([left, right])
    return sum(right - left + 1 for left, right in intervals)


def build_summary_only_inventory(summary: dict[str, Any]) -> dict[str, Any]:
    """Classify which hypotheses cannot be closed from the primary summary."""
    threshold = float(summary["global_result"]["operational_threshold_snr"])
    peak_cap = int(
        summary["candidate_reduction"]["settings"]["peaks_per_hypothesis"]
    )
    pool_size = peak_cap * 5
    widths = [
        int(value)
        for value in summary["search_dimensions"]["spectral_width_templates"]
    ]
    subsets = ((0, 1), (0, 2), (1, 2), (0, 1, 2))
    records: dict[tuple[Any, ...], list[tuple[float, int]]] = defaultdict(list)
    rest_bins: dict[str, int] = {}

    for window_id, window in summary["windows"].items():
        rest_bins[window_id] = int(window["rest_bins"])
        for cluster in window["candidate_reduction"]["clusters"]:
            if int(cluster["member_count"]) != len(cluster["top_members"]):
                raise AssertionError(
                    "primary top_members is truncated; summary-only inventory is invalid"
                )
            for record in cluster["top_members"]:
                key = (
                    window_id,
                    int(record["spectral_width_channels"]),
                    int(record["template_index"]),
                    tuple(
                        int(epoch) + 1
                        for epoch in record["active_epochs_zero_based"]
                    ),
                )
                records[key].append(
                    (float(record["snr"]), int(record["frequency_index"]))
                )

    categories: Counter[str] = Counter()
    unresolved: list[tuple[str, int, int, str, int]] = []
    details: list[dict[str, Any]] = []
    for window_id in summary["windows"]:
        for width in widths:
            radius = max(1, width // 2)
            for template_index in range(
                int(summary["search_dimensions"]["templates"])
            ):
                for subset_zero in subsets:
                    epochs = tuple(epoch + 1 for epoch in subset_zero)
                    selected = sorted(
                        records[(window_id, width, template_index, epochs)],
                        reverse=True,
                    )
                    count = len(selected)
                    if count == 0:
                        category = "safe_empty"
                        lowest_snr = None
                        union_size = 0
                    else:
                        lowest_snr = selected[-1][0]
                        union_size = interval_union_size(
                            [item[1] for item in selected],
                            radius,
                            rest_bins[window_id],
                        )
                        if lowest_snr < threshold:
                            category = "safe_lowest_below_threshold"
                        elif count < peak_cap and union_size < pool_size:
                            category = "safe_pigeonhole_pool_not_exhausted"
                        elif count == peak_cap:
                            category = "unresolved_explicit_top3"
                        else:
                            category = "unresolved_top15_pool"
                    categories[category] += 1
                    if category.startswith("unresolved_"):
                        row = (
                            window_id,
                            width,
                            template_index,
                            "".join(map(str, epochs)),
                            count,
                        )
                        unresolved.append(row)
                        details.append(
                            {
                                "window": window_id,
                                "width_channels": width,
                                "template_index": template_index,
                                "epochs_1_based": list(epochs),
                                "retained_count": count,
                                "lowest_retained_snr": lowest_snr,
                                "selected_neighborhood_union_channels": union_size,
                                "category": category,
                            }
                        )

    unresolved.sort()
    details.sort(
        key=lambda item: (
            item["window"],
            item["width_channels"],
            item["template_index"],
            item["epochs_1_based"],
            item["retained_count"],
        )
    )
    canonical_csv = "".join(
        f"{window},{width},{template},{epochs},{count}\n"
        for window, width, template, epochs, count in unresolved
    )
    by_window = Counter(row[0] for row in unresolved)
    by_width = Counter(str(row[1]) for row in unresolved)
    by_retained = Counter(str(row[4]) for row in unresolved)
    return {
        "schema_version": 1,
        "source": {
            "repository": "andersenmartin-blip/setisearch",
            "result_commit": "88db2596090e3a79620bff7e0e2c42dd63560431",
            "search_summary_path": "results_m36/search_summary.json",
        },
        "constants": {
            "operational_threshold_snr": threshold,
            "top_pool_size": pool_size,
            "peaks_per_hypothesis": peak_cap,
            "neighborhood_radius_channels": "max(1, width_channels // 2)",
        },
        "classification_order": [
            "count == 0 -> safe_empty",
            "lowest_retained_snr < threshold -> safe_lowest_below_threshold",
            (
                "count < 3 and selected_neighborhood_union_channels < 15 "
                "-> safe_pigeonhole_pool_not_exhausted"
            ),
            "count == 3 -> unresolved_explicit_top3",
            "otherwise -> unresolved_top15_pool",
        ],
        "counts": {
            "total_hypotheses": sum(categories.values()),
            "categories": dict(sorted(categories.items())),
            "unresolved_total": len(unresolved),
            "unresolved_by_window": dict(sorted(by_window.items())),
            "unresolved_by_width": dict(
                sorted(by_width.items(), key=lambda item: int(item[0]))
            ),
            "unresolved_by_retained_count": dict(
                sorted(by_retained.items(), key=lambda item: int(item[0]))
            ),
        },
        "canonical_tuple_columns": [
            "window",
            "width_channels",
            "template_index",
            "epochs_1_based_compact",
            "retained_count",
        ],
        "canonical_tuple_csv_sha256": hashlib.sha256(
            canonical_csv.encode()
        ).hexdigest(),
        "unresolved_tuples": [list(row) for row in unresolved],
        "unresolved_details": details,
    }


def stack_hypothesis(
    spectral_bank: np.ndarray,
    width_index: int,
    template_index: int,
    subset: tuple[int, ...],
    minimum_active_epoch_snr: float | None,
    stack_statistic: str,
    exclusion_mask: np.ndarray | None,
) -> np.ndarray:
    """Reproduce the frozen collector's score and eligibility vector."""
    active = spectral_bank[width_index, template_index, list(subset)]
    if stack_statistic == "sum":
        stack = np.sum(active, axis=0) / np.sqrt(len(subset))
    elif stack_statistic == "minimum_epoch":
        stack = np.sqrt(len(subset)) * np.min(active, axis=0)
    else:
        raise ValueError(f"Unknown stack statistic: {stack_statistic}")
    if minimum_active_epoch_snr is not None:
        stack = np.where(
            np.all(active >= minimum_active_epoch_snr, axis=0), stack, -np.inf
        )
    if exclusion_mask is not None:
        mask = exclusion_mask[width_index, template_index]
        if mask.ndim == 2:
            mask = np.any(mask[list(subset)], axis=0)
        stack = np.where(mask, -np.inf, stack)
    return np.nan_to_num(stack, nan=-np.inf)


def greedy_cover(
    scores: np.ndarray,
    threshold: float,
    separation_channels: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return eligible indices, selected representatives, and each cell's owner.

    Candidates are ordered by descending score and then ascending frequency
    index.  An owner is therefore always at least as strong as the cell it
    covers.  Coverage uses the same inclusive-distance convention as v0.5.
    """
    if separation_channels < 0:
        raise ValueError("separation_channels must be non-negative")
    eligible = np.flatnonzero(np.isfinite(scores) & (scores >= threshold))
    if eligible.size == 0:
        return eligible, np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    order = eligible[np.lexsort((eligible, -scores[eligible]))]
    owner_grid = np.full(scores.size, -1, dtype=np.int64)
    selected: list[int] = []
    for raw_index in order:
        index = int(raw_index)
        if owner_grid[index] >= 0:
            continue
        selected.append(index)
        lo = max(0, index - separation_channels)
        hi = min(scores.size, index + separation_channels + 1)
        local = owner_grid[lo:hi]
        local[local < 0] = index
    owners = owner_grid[eligible]
    if np.any(owners < 0):
        raise AssertionError("unaccounted above-threshold score cell")
    if np.any(scores[owners] < scores[eligible]):
        raise AssertionError("a score cell was assigned to a weaker representative")
    if np.any(np.abs(owners - eligible) > separation_channels):
        raise AssertionError("a score cell was assigned outside the frozen radius")
    return eligible, np.asarray(selected, dtype=np.int64), owners


def literal_tolerance_bins(rest_frequency_mhz: np.ndarray, tolerance_hz: float) -> int:
    df_hz = abs(float(rest_frequency_mhz[1] - rest_frequency_mhz[0])) * 1e6
    bins = int(math.floor((tolerance_hz + 1e-9) / df_hz))
    if bins * df_hz > tolerance_hz + 1e-6:
        raise AssertionError("literal tolerance radius exceeds requested Hz")
    if (bins + 1) * df_hz <= tolerance_hz - 1e-6:
        raise AssertionError("literal tolerance radius is not maximal")
    return bins


def cluster_all_records(records: list[dict[str, Any]], tolerance_hz: float) -> list[dict[str, Any]]:
    """Apply v0.5 frequency grouping while preserving every member."""
    if not records:
        return []
    tolerance_mhz = tolerance_hz / 1e6
    groups: list[list[dict[str, Any]]] = []
    for record in sorted(records, key=lambda item: item["frequency_mhz"]):
        if not groups:
            groups.append([record])
            continue
        prior_group = groups[-1]
        middle = len(prior_group) // 2
        if len(prior_group) % 2:
            center = float(prior_group[middle]["frequency_mhz"])
        else:
            center = float(
                (
                    float(prior_group[middle - 1]["frequency_mhz"])
                    + float(prior_group[middle]["frequency_mhz"])
                )
                / 2.0
            )
        if abs(float(record["frequency_mhz"]) - center) <= tolerance_mhz:
            groups[-1].append(record)
        else:
            groups.append([record])

    clusters: list[dict[str, Any]] = []
    for group in groups:
        members = sorted(
            group,
            key=lambda item: (
                -float(item["snr"]),
                int(item["frequency_index"]),
                str(item["audit_record_id"]),
            ),
        )
        best = members[0]
        frequencies = [float(item["frequency_mhz"]) for item in members]
        clusters.append(
            {
                "cluster_frequency_mhz": float(best["frequency_mhz"]),
                "max_snr": float(best["snr"]),
                "member_count": len(members),
                "member_ids": [item["audit_record_id"] for item in members],
                "distinct_template_count": len(
                    {int(item["template_index"]) for item in members}
                ),
                "distinct_spectral_widths": sorted(
                    {int(item["spectral_width_channels"]) for item in members}
                ),
                "distinct_activity_subsets": sorted(
                    {
                        "+".join(
                            str(int(epoch) + 1)
                            for epoch in item["active_epochs_zero_based"]
                        )
                        for item in members
                    }
                ),
                "frequency_span_hz": float(
                    (max(frequencies) - min(frequencies)) * 1e6
                ),
                "best_member_id": best["audit_record_id"],
                "_members": members,
            }
        )
    clusters.sort(
        key=lambda item: (-float(item["max_snr"]), float(item["cluster_frequency_mhz"]))
    )
    for cluster_index, cluster in enumerate(clusters):
        cluster["audit_cluster_index"] = cluster_index
        for member in cluster["_members"]:
            member["audit_cluster_index"] = cluster_index
    return clusters


def _stack_local(active: np.ndarray, statistic: str, floor: float | None) -> np.ndarray:
    if statistic == "sum":
        stack = np.sum(active, axis=0) / np.sqrt(active.shape[0])
    elif statistic == "minimum_epoch":
        stack = np.sqrt(active.shape[0]) * np.min(active, axis=0)
    else:
        raise ValueError(f"Unknown stack statistic: {statistic}")
    if floor is not None:
        stack = np.where(np.all(active >= floor, axis=0), stack, -np.inf)
    return stack


def best_local_recurrence(
    spectral_bank: np.ndarray,
    rest_frequency_mhz: np.ndarray,
    center_index: int,
    frequency_indices: np.ndarray,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
    minimum_active_epoch_snr: float | None,
    stack_statistic: str,
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for width_index, width in enumerate(spectral_widths):
        for template_index, (scale, phase) in enumerate(templates):
            for subset in subsets:
                active = spectral_bank[
                    width_index,
                    template_index,
                    list(subset),
                ][:, frequency_indices]
                stack = _stack_local(
                    active, stack_statistic, minimum_active_epoch_snr
                )
                if not np.any(np.isfinite(stack)):
                    continue
                local_offset = int(np.nanargmax(stack))
                frequency_index = int(frequency_indices[local_offset])
                record = {
                    "snr": float(stack[local_offset]),
                    "frequency_mhz": float(rest_frequency_mhz[frequency_index]),
                    "frequency_index": frequency_index,
                    "offset_from_candidate_hz": float(
                        (
                            rest_frequency_mhz[frequency_index]
                            - rest_frequency_mhz[center_index]
                        )
                        * 1e6
                    ),
                    "spectral_width_channels": int(width),
                    "spectral_width_index": int(width_index),
                    "template_index": int(template_index),
                    "projected_scale": float(scale),
                    "phase_offset_cycles": float(phase),
                    "active_epochs_zero_based": list(subset),
                    "epoch_values_at_frequency": [
                        float(value)
                        for value in spectral_bank[
                            width_index, template_index, :, frequency_index
                        ]
                    ],
                }
                if best is None or float(record["snr"]) > float(best["snr"]):
                    best = record
    return best


def same_candidate_track(
    spectral_bank: np.ndarray,
    record: dict[str, Any],
    single_epoch_snr_floor: float,
) -> dict[str, Any]:
    width_index = int(record["spectral_width_index"])
    template_index = int(record["template_index"])
    center_index = int(record["frequency_index"])
    active_epochs = [int(epoch) for epoch in record["active_epochs_zero_based"]]
    epoch_values = spectral_bank[width_index, template_index, :, center_index]
    matching = [
        epoch
        for epoch in active_epochs
        if float(epoch_values[epoch]) >= single_epoch_snr_floor
    ]
    return {
        "single_epoch_snr_floor": float(single_epoch_snr_floor),
        "epoch_values": [float(value) for value in epoch_values],
        "active_epochs_zero_based": active_epochs,
        "matching_active_epochs_zero_based": matching,
        "maximum_active_epoch_snr": float(
            max(epoch_values[epoch] for epoch in active_epochs)
        ),
    }


def receiver_alias_matches(
    left: dict[str, Any],
    right: dict[str, Any],
    tolerance_hz: float,
    minimum_shared_epochs: int,
    local_peak_snr_floor: float,
) -> list[dict[str, Any]]:
    left_by_epoch = {
        int(item["epoch_zero_based"]): item
        for item in left["receiver_frame_signature"]
    }
    right_by_epoch = {
        int(item["epoch_zero_based"]): item
        for item in right["receiver_frame_signature"]
    }
    matches = []
    for epoch in sorted(set(left_by_epoch) & set(right_by_epoch)):
        left_peak = left_by_epoch[epoch]
        right_peak = right_by_epoch[epoch]
        delta_hz = float(
            (
                float(right_peak["peak_frequency_mhz"])
                - float(left_peak["peak_frequency_mhz"])
            )
            * 1e6
        )
        if (
            float(left_peak["peak_snr"]) >= local_peak_snr_floor
            and float(right_peak["peak_snr"]) >= local_peak_snr_floor
            and abs(delta_hz) <= tolerance_hz
        ):
            matches.append(
                {
                    "epoch_zero_based": epoch,
                    "delta_hz": delta_hz,
                    "left_peak_snr": float(left_peak["peak_snr"]),
                    "right_peak_snr": float(right_peak["peak_snr"]),
                }
            )
    return matches if len(matches) >= minimum_shared_epochs else []


def local_frequency_indices(
    frequencies_mhz: np.ndarray,
    center_mhz: float,
    half_width_hz: float,
    ascending: bool | None = None,
) -> np.ndarray:
    """Return exact local-mask indices without scanning the full spectrum."""
    frequencies = np.asarray(frequencies_mhz)
    if frequencies.ndim != 1 or frequencies.size < 2:
        raise ValueError("frequency grid must be a one-dimensional vector")
    if ascending is None:
        ascending = bool(frequencies[-1] > frequencies[0])
        ordered_for_validation = frequencies if ascending else frequencies[::-1]
        if not np.all(np.diff(ordered_for_validation) > 0):
            raise ValueError("frequency grid must be strictly monotonic")
    ordered = frequencies if ascending else frequencies[::-1]
    half_width_mhz = half_width_hz / 1e6
    lower = center_mhz - half_width_mhz
    upper = center_mhz + half_width_mhz
    lo = max(0, int(np.searchsorted(ordered, lower, side="left")) - 1)
    hi = min(
        ordered.size,
        int(np.searchsorted(ordered, upper, side="right")) + 1,
    )
    ordered_indices = np.arange(lo, hi, dtype=np.int64)
    if ascending:
        indices = ordered_indices
    else:
        indices = np.sort(ordered.size - 1 - ordered_indices)
    exact = (
        np.abs((frequencies[indices] - center_mhz) * 1e6)
        <= half_width_hz
    )
    return indices[exact]


def build_receiver_frame_signature_indexed(
    cluster: dict[str, Any],
    scans: list[dict[str, Any]],
    config: dict[str, Any],
    local_half_width_hz: float,
    stationary_cache: dict[tuple[int, int], np.ndarray] | None = None,
    factor_cache: dict[tuple[int, float, float], np.ndarray] | None = None,
    frequency_direction_cache: dict[int, bool] | None = None,
    target=None,
    location=None,
) -> list[dict[str, Any]]:
    """Semantically identical indexed form of the frozen receiver signature."""
    from seti_repeater.orbit import celestial_frequency_factor
    from seti_repeater.spectral import normalized_boxcar

    best = cluster["best_hypothesis"]
    rest_mhz = float(best["frequency_mhz"])
    scale = float(best["projected_scale"])
    phase = float(best["phase_offset_cycles"])
    width = int(best["spectral_width_channels"])
    target = make_target(config["target"]) if target is None else target
    location = make_location(config["observatory"]) if location is None else location
    stationary_cache = {} if stationary_cache is None else stationary_cache
    factor_cache = {} if factor_cache is None else factor_cache
    frequency_direction_cache = (
        {} if frequency_direction_cache is None else frequency_direction_cache
    )
    signature = []
    for raw_epoch in best["active_epochs_zero_based"]:
        epoch = int(raw_epoch)
        scan = scans[epoch]
        factor_key = (epoch, scale, phase)
        if factor_key not in factor_cache:
            factor_cache[factor_key] = celestial_frequency_factor(
                scan["times"], scale, phase, target, location, config["orbit"]
            )[0]
        factor = factor_cache[factor_key]
        predicted_mid_mhz = float(np.mean(rest_mhz * factor))
        frequencies = scan["frequency_mhz"]
        frequency_key = id(frequencies)
        if frequency_key not in frequency_direction_cache:
            ascending = bool(frequencies[-1] > frequencies[0])
            ordered = frequencies if ascending else frequencies[::-1]
            if not np.all(np.diff(ordered) > 0):
                raise ValueError("frequency grid must be strictly monotonic")
            frequency_direction_cache[frequency_key] = ascending
        local_indices = local_frequency_indices(
            frequencies,
            predicted_mid_mhz,
            local_half_width_hz,
            frequency_direction_cache[frequency_key],
        )
        if local_indices.size == 0:
            raise ValueError("receiver-frame neighbourhood is outside the scan")
        stationary_key = (epoch, width)
        if stationary_key not in stationary_cache:
            filtered = normalized_boxcar(scan["normalized"], width)
            stationary_cache[stationary_key] = (
                np.sum(filtered, axis=0) / np.sqrt(filtered.shape[0])
            )
        stationary = stationary_cache[stationary_key]
        frequency_index = int(
            local_indices[np.nanargmax(stationary[local_indices])]
        )
        signature.append(
            {
                "epoch_zero_based": epoch,
                "predicted_mid_mhz": predicted_mid_mhz,
                "peak_frequency_mhz": float(frequencies[frequency_index]),
                "peak_snr": float(stationary[frequency_index]),
                "offset_from_prediction_hz": float(
                    (frequencies[frequency_index] - predicted_mid_mhz) * 1e6
                ),
            }
        )
    return signature


def assign_receiver_alias_witnesses(
    records: list[dict[str, Any]],
    cluster_by_member: dict[str, int],
    tolerance_hz: float,
    minimum_shared_epochs: int,
    local_peak_snr_floor: float,
) -> None:
    """Find one deterministic receiver-alias witness per member using 2-D bins."""
    if minimum_shared_epochs != 2:
        raise AssertionError("the frozen M36 receiver-alias rule requires two epochs")
    if tolerance_hz <= 0:
        raise ValueError("receiver alias tolerance must be positive")
    ordered_indices = sorted(
        range(len(records)), key=lambda index: records[index]["audit_record_id"]
    )
    qualified: dict[int, dict[int, dict[str, Any]]] = {}
    buckets: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
    for record_index in ordered_indices:
        signature = {
            int(item["epoch_zero_based"]): item
            for item in records[record_index]["receiver_frame_signature"]
            if float(item["peak_snr"]) >= local_peak_snr_floor
        }
        qualified[record_index] = signature
        epochs = sorted(signature)
        for left_position, left_epoch in enumerate(epochs):
            for right_epoch in epochs[left_position + 1 :]:
                left_cell = math.floor(
                    float(signature[left_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / tolerance_hz
                )
                right_cell = math.floor(
                    float(signature[right_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / tolerance_hz
                )
                buckets[
                    (left_epoch, right_epoch, left_cell, right_cell)
                ].append(record_index)

    for left_index in ordered_indices:
        left = records[left_index]
        signature = qualified[left_index]
        epochs = sorted(signature)
        seen: set[int] = set()
        witness: dict[str, Any] | None = None
        for left_position, left_epoch in enumerate(epochs):
            if witness is not None:
                break
            for right_epoch in epochs[left_position + 1 :]:
                left_cell = math.floor(
                    float(signature[left_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / tolerance_hz
                )
                right_cell = math.floor(
                    float(signature[right_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / tolerance_hz
                )
                for left_delta in (-1, 0, 1):
                    if witness is not None:
                        break
                    for right_delta in (-1, 0, 1):
                        bucket = buckets.get(
                            (
                                left_epoch,
                                right_epoch,
                                left_cell + left_delta,
                                right_cell + right_delta,
                            ),
                            [],
                        )
                        for candidate_index in bucket:
                            if candidate_index == left_index or candidate_index in seen:
                                continue
                            seen.add(candidate_index)
                            candidate = records[candidate_index]
                            if cluster_by_member[left["audit_record_id"]] == (
                                cluster_by_member[candidate["audit_record_id"]]
                            ):
                                continue
                            matches = receiver_alias_matches(
                                left,
                                candidate,
                                tolerance_hz,
                                minimum_shared_epochs,
                                local_peak_snr_floor,
                            )
                            if matches:
                                witness = {
                                    "other_record_id": candidate["audit_record_id"],
                                    "other_cluster_index": cluster_by_member[
                                        candidate["audit_record_id"]
                                    ],
                                    "matched_active_epochs": matches,
                                }
                                break
                        if witness is not None:
                            break
        left["receiver_frame_alias_witness"] = witness


def disposition_for_record(record: dict[str, Any], *, literal: bool) -> str:
    local_key = (
        "literal_20hz_local_off_diagnostics"
        if literal
        else "v0p5_rounded_local_off_diagnostics"
    )
    local = record[local_key]["best_local_recurrence"]
    threshold = float(record["audit_operational_threshold_snr"])
    if record["off_at_same_hypothesis_snr"] >= threshold:
        return "rfi_veto_off_source"
    if local is not None and float(local["snr"]) >= threshold:
        return "rfi_veto_local_off_source"
    if record[local_key]["same_candidate_track"][
        "matching_active_epochs_zero_based"
    ]:
        return "rfi_veto_single_adjacent_off"
    if record["receiver_frame_alias_witness"] is not None:
        return "rfi_veto_receiver_frame_alias"
    return "survives_for_followup"


class DeterministicGzipJsonl:
    def __init__(self, path: Path):
        self.path = path
        self._raw = path.open("wb")
        self._gzip = gzip.GzipFile(
            filename="", fileobj=self._raw, mode="wb", mtime=0
        )
        self._text = io.TextIOWrapper(self._gzip, encoding="utf-8", newline="\n")

    def write(self, value: Any) -> bytes:
        encoded = canonical_json_bytes(value, pretty=False)
        self._text.write(encoded.decode())
        return encoded

    def close(self) -> None:
        self._text.flush()
        self._text.detach()
        self._gzip.close()
        self._raw.close()

    def __enter__(self) -> "DeterministicGzipJsonl":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def write_gzip_json(path: Path, value: Any) -> None:
    with DeterministicGzipJsonl(path) as writer:
        writer.write(value)


def write_gzip_jsonl(path: Path, values: Iterable[Any]) -> None:
    with DeterministicGzipJsonl(path) as writer:
        for value in values:
            writer.write(value)


def assert_equal(label: str, actual: Any, expected: Any) -> None:
    if json_safe(actual) != expected:
        raise AssertionError(f"primary reproduction mismatch: {label}")


def reproduce_primary_window(
    config: dict[str, Any],
    published_window: dict[str, Any],
    scans_by_kind: dict[str, list[dict[str, Any]]],
    rest_grid: np.ndarray,
    on_bank: np.ndarray,
    off_bank: np.ndarray,
    on_spectral: np.ndarray,
    off_spectral: np.ndarray,
    on_mask: np.ndarray | None,
    off_mask: np.ndarray | None,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
    threshold: float,
) -> dict[str, Any]:
    search = config["search"]
    reporting = search["candidate_reporting"]
    minimum_active_epoch_snr = search.get("minimum_active_epoch_snr")
    stack_statistic = search.get("stack_statistic", "sum")
    width_one_index = spectral_widths.index(1)

    one_channel_best = search_bank(
        on_bank,
        rest_grid,
        templates,
        subsets,
        minimum_active_epoch_snr,
        stack_statistic,
        None if on_mask is None else on_mask[width_one_index],
    )
    on_best = search_spectral_bank(
        on_spectral,
        rest_grid,
        templates,
        subsets,
        spectral_widths,
        minimum_active_epoch_snr,
        stack_statistic,
        on_mask,
    )
    off_best = search_spectral_bank(
        off_spectral,
        rest_grid,
        templates,
        subsets,
        spectral_widths,
        minimum_active_epoch_snr,
        stack_statistic,
        off_mask,
    )
    on_best["off_at_same_hypothesis_snr"] = evaluate_spectral_record(
        off_spectral, on_best, minimum_active_epoch_snr, stack_statistic
    )
    assert_equal("rest_bins", int(rest_grid.size), published_window["rest_bins"])
    assert_equal("on_best", on_best, published_window["on_best"])
    assert_equal(
        "one_channel_regression_best",
        one_channel_best,
        published_window["one_channel_regression_best"],
    )
    assert_equal("off_global_best", off_best, published_window["off_global_best"])

    peak_records = collect_hypothesis_peaks(
        on_spectral,
        rest_grid,
        templates,
        subsets,
        spectral_widths,
        reporting["peaks_per_hypothesis"],
        reporting["snr_floor"],
        minimum_active_epoch_snr,
        stack_statistic,
        on_mask,
    )
    all_clusters = cluster_peaks(peak_records, reporting["cluster_tolerance_hz"])
    retained_clusters = all_clusters[: reporting["max_report_clusters"]]
    for cluster in retained_clusters:
        cluster["off_at_best_hypothesis_snr"] = evaluate_spectral_record(
            off_spectral,
            cluster["best_hypothesis"],
            minimum_active_epoch_snr,
            stack_statistic,
        )
    veto = search["candidate_veto_v0p5"]
    annotate_local_off_vetoes(
        retained_clusters,
        off_spectral,
        rest_grid,
        templates,
        subsets,
        spectral_widths,
        veto["local_off_tolerance_hz"],
        veto["single_epoch_snr_floor"],
        minimum_active_epoch_snr,
        stack_statistic,
    )
    annotate_receiver_frame_aliases(
        retained_clusters,
        scans_by_kind["on"],
        config,
        veto["receiver_local_half_width_hz"],
        veto["receiver_alias_tolerance_hz"],
        veto["receiver_alias_minimum_shared_epochs"],
        veto["single_epoch_snr_floor"],
    )
    families = detect_arithmetic_frequency_families(
        retained_clusters,
        reporting["family_spacing_tolerance_hz"],
        reporting["family_min_members"],
    )
    apply_candidate_flags(
        retained_clusters,
        families,
        threshold,
        reporting["template_multiplicity_flag"],
    )
    product = {
        "hypothesis_peak_count": len(peak_records),
        "cluster_count_before_report_limit": len(all_clusters),
        "reported_cluster_count": len(retained_clusters),
        "clusters": retained_clusters,
        "arithmetic_frequency_families": families,
        "candidate_veto_v0p5": veto,
    }
    assert_equal(
        "candidate_reduction", product, published_window["candidate_reduction"]
    )
    return {
        "rest_bins": int(rest_grid.size),
        "primary_hypothesis_peaks_reproduced": len(peak_records),
        "primary_clusters_reproduced": len(retained_clusters),
        "primary_candidate_reduction_exact": True,
        "primary_maxima_exact": True,
    }


def manifest_mapping(path: str | Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        logical = "/".join(Path(filename).parts[-3:])
        if logical in mapping:
            raise AssertionError(f"duplicate manifest path {logical}")
        mapping[logical] = digest
    return mapping


def verify_reextracted_data(manifest_path: str | Path, data_dir: str | Path) -> None:
    expected = manifest_mapping(manifest_path)
    actual: dict[str, str] = {}
    root = Path(data_dir)
    for path in sorted(root.glob("*/*.npz")):
        logical = "/".join(path.parts[-3:])
        actual[logical] = sha256(path)
    if len(expected) != 30 or actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        wrong = sorted(
            key for key in set(actual) & set(expected) if actual[key] != expected[key]
        )
        raise AssertionError(
            f"re-extracted data do not match primary manifest; "
            f"missing={missing}, extra={extra}, wrong={wrong}"
        )


def audit_window(
    config: dict[str, Any],
    spec: dict[str, Any],
    primary_summary: dict[str, Any],
    window: dict[str, Any],
    data_dir: Path,
    output_dir: Path,
    templates: list[tuple[float, float]],
    subsets: list[tuple[int, ...]],
    spectral_widths: tuple[int, ...],
) -> dict[str, Any]:
    window_id = window["id"]
    search = config["search"]
    reporting = search["candidate_reporting"]
    veto = search["candidate_veto_v0p5"]
    threshold = float(spec["audit"]["operational_threshold_snr"])
    minimum_active_epoch_snr = search.get("minimum_active_epoch_snr")
    stack_statistic = search.get("stack_statistic", "sum")

    scans_by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind in ("on", "off"):
        definitions = sorted(
            (scan for scan in config["scans"] if scan["kind"] == kind),
            key=lambda item: item["epoch"],
        )
        scans_by_kind[kind] = [
            load_scan(data_dir / window_id / f"{scan['label']}.npz")
            for scan in definitions
        ]

    first_scan = scans_by_kind["on"][0]
    channel_width_mhz = abs(
        float(first_scan["frequency_mhz"][1] - first_scan["frequency_mhz"][0])
    )
    rest_grid = make_rest_grid(window, channel_width_mhz)
    on_bank, _ = build_bank(
        scans_by_kind["on"],
        rest_grid,
        window["rest_center_mhz"],
        templates,
        config,
    )
    off_bank, _ = build_bank(
        scans_by_kind["off"],
        rest_grid,
        window["rest_center_mhz"],
        templates,
        config,
    )
    on_spectral = make_spectral_bank(on_bank, spectral_widths)
    off_spectral = make_spectral_bank(off_bank, spectral_widths)
    excision = search.get("rfi_excision")
    if excision:
        on_mask = build_single_epoch_rfi_mask(
            on_spectral,
            excision["single_epoch_strong_snr"],
            excision["other_epochs_below_snr"],
            excision["guard_channels"],
        )
        off_mask = build_single_epoch_rfi_mask(
            off_spectral,
            excision["single_epoch_strong_snr"],
            excision["other_epochs_below_snr"],
            excision["guard_channels"],
        )
    else:
        on_mask = off_mask = None

    reproduction = reproduce_primary_window(
        config,
        primary_summary["windows"][window_id],
        scans_by_kind,
        rest_grid,
        on_bank,
        off_bank,
        on_spectral,
        off_spectral,
        on_mask,
        off_mask,
        templates,
        subsets,
        spectral_widths,
        threshold,
    )

    literal_bins = literal_tolerance_bins(
        rest_grid, float(reporting["cluster_tolerance_hz"])
    )
    df_hz = abs(float(rest_grid[1] - rest_grid[0])) * 1e6
    records: list[dict[str, Any]] = []
    certificates: list[dict[str, Any]] = []
    total_score_cells = 0
    total_eligible = 0
    total_legacy = 0
    total_literal = 0
    ledger_path = output_dir / f"{window_id}_coverage_ledger.jsonl.gz"
    with DeterministicGzipJsonl(ledger_path) as ledger:
        for width_index, width in enumerate(spectral_widths):
            legacy_radius = max(1, int(width) // 2)
            for template_index, (scale, phase) in enumerate(templates):
                for subset in subsets:
                    hypothesis_id = (
                        f"{window_id}:w{int(width)}:t{template_index}:e"
                        + "".join(str(int(epoch) + 1) for epoch in subset)
                    )
                    scores = stack_hypothesis(
                        on_spectral,
                        width_index,
                        template_index,
                        subset,
                        minimum_active_epoch_snr,
                        stack_statistic,
                        on_mask,
                    )
                    total_score_cells += int(scores.size)
                    eligible, legacy_selected, legacy_owners = greedy_cover(
                        scores, threshold, legacy_radius
                    )
                    literal_eligible, literal_selected, literal_owners = greedy_cover(
                        scores, threshold, literal_bins
                    )
                    if not np.array_equal(eligible, literal_eligible):
                        raise AssertionError("NMS ledgers disagree on eligible score cells")
                    legacy_selected_set = {int(index) for index in legacy_selected}
                    literal_selected_set = {int(index) for index in literal_selected}
                    union_selected = sorted(
                        legacy_selected_set | literal_selected_set,
                        key=lambda index: (-float(scores[index]), index),
                    )
                    total_eligible += int(eligible.size)
                    total_legacy += int(legacy_selected.size)
                    total_literal += int(literal_selected.size)
                    certificate_hash = hashlib.sha256()
                    for position, raw_index in enumerate(eligible):
                        index = int(raw_index)
                        row = {
                            "hypothesis_id": hypothesis_id,
                            "frequency_index": index,
                            "frequency_mhz": float(rest_grid[index]),
                            "snr": float(scores[index]),
                            "legacy_nms": (
                                "selected"
                                if index in legacy_selected_set
                                else "suppressed"
                            ),
                            "legacy_owner_frequency_index": int(
                                legacy_owners[position]
                            ),
                            "literal_20hz_nms": (
                                "selected"
                                if index in literal_selected_set
                                else "suppressed"
                            ),
                            "literal_20hz_owner_frequency_index": int(
                                literal_owners[position]
                            ),
                        }
                        certificate_hash.update(ledger.write(row))
                    certificates.append(
                        {
                            "hypothesis_id": hypothesis_id,
                            "spectral_width_channels": int(width),
                            "spectral_width_index": int(width_index),
                            "template_index": int(template_index),
                            "projected_scale": float(scale),
                            "phase_offset_cycles": float(phase),
                            "active_epochs_zero_based": list(subset),
                            "score_cells_visited": int(scores.size),
                            "above_threshold_cells": int(eligible.size),
                            "legacy_radius_channels": legacy_radius,
                            "legacy_selected_peaks": int(legacy_selected.size),
                            "literal_20hz_radius_channels": literal_bins,
                            "literal_20hz_radius_hz": float(literal_bins * df_hz),
                            "literal_20hz_selected_peaks": int(
                                literal_selected.size
                            ),
                            "union_selected_peaks": len(union_selected),
                            "unaccounted_above_threshold_cells": 0,
                            "coverage_rows_sha256": certificate_hash.hexdigest(),
                        }
                    )
                    for index in union_selected:
                        selected_by = []
                        if index in legacy_selected_set:
                            selected_by.append("legacy_unbounded_nms")
                        if index in literal_selected_set:
                            selected_by.append("literal_20hz_nms")
                        record_id = f"{hypothesis_id}:f{index}"
                        records.append(
                            {
                                "audit_record_id": record_id,
                                "hypothesis_id": hypothesis_id,
                                "snr": float(scores[index]),
                                "frequency_mhz": float(rest_grid[index]),
                                "frequency_index": int(index),
                                "spectral_width_channels": int(width),
                                "spectral_width_index": int(width_index),
                                "template_index": int(template_index),
                                "projected_scale": float(scale),
                                "phase_offset_cycles": float(phase),
                                "active_epochs_zero_based": list(subset),
                                "epoch_values_at_frequency": [
                                    float(value)
                                    for value in on_spectral[
                                        width_index, template_index, :, index
                                    ]
                                ],
                                "selected_by": selected_by,
                                "audit_operational_threshold_snr": threshold,
                            }
                        )

    if len(certificates) != 672:
        raise AssertionError(f"expected 672 hypotheses in {window_id}")
    if total_score_cells != 672 * int(rest_grid.size):
        raise AssertionError("not every frozen score cell was visited")

    primary_above_members: dict[tuple[Any, ...], dict[str, Any]] = {}
    for primary_cluster in primary_summary["windows"][window_id][
        "candidate_reduction"
    ]["clusters"]:
        for member in primary_cluster["top_members"]:
            if float(member["snr"]) < threshold:
                continue
            key = (
                int(member["spectral_width_index"]),
                int(member["template_index"]),
                tuple(member["active_epochs_zero_based"]),
                int(member["frequency_index"]),
            )
            if key in primary_above_members:
                raise AssertionError("duplicate primary above-threshold member")
            primary_above_members[key] = member
    audit_by_key = {
        (
            int(record["spectral_width_index"]),
            int(record["template_index"]),
            tuple(record["active_epochs_zero_based"]),
            int(record["frequency_index"]),
        ): record
        for record in records
    }
    for key, member in primary_above_members.items():
        if key in audit_by_key:
            audit_by_key[key]["selected_by"].append(
                "primary_retained_above_threshold_crosswalk"
            )
            continue
        width_index, template_index, subset, frequency_index = key
        width = int(spectral_widths[width_index])
        scores = stack_hypothesis(
            on_spectral,
            width_index,
            template_index,
            subset,
            minimum_active_epoch_snr,
            stack_statistic,
            on_mask,
        )
        if float(scores[frequency_index]) != float(member["snr"]):
            raise AssertionError("primary tie crosswalk score does not reproduce")
        hypothesis_id = (
            f"{window_id}:w{width}:t{template_index}:e"
            + "".join(str(int(epoch) + 1) for epoch in subset)
        )
        record = {
            **member,
            "audit_record_id": f"{hypothesis_id}:f{frequency_index}",
            "hypothesis_id": hypothesis_id,
            "selected_by": ["primary_retained_above_threshold_crosswalk"],
            "audit_operational_threshold_snr": threshold,
        }
        records.append(record)
        audit_by_key[key] = record

    if len(records) > int(
        spec["audit"]["maximum_receiver_alias_records_per_window"]
    ):
        raise AssertionError(
            "record density exceeds the frozen receiver-alias capacity; "
            "audit is invalid and no record may be truncated"
        )
    clusters = cluster_all_records(records, reporting["cluster_tolerance_hz"])
    cluster_by_member = {
        member["audit_record_id"]: int(cluster["audit_cluster_index"])
        for cluster in clusters
        for member in cluster["_members"]
    }

    rounded_cache: dict[int, dict[str, Any] | None] = {}
    literal_cache: dict[int, dict[str, Any] | None] = {}
    rounded_bins = int(math.ceil(veto["local_off_tolerance_hz"] / df_hz))
    for record in records:
        center = int(record["frequency_index"])
        rounded_indices = np.arange(
            max(0, center - rounded_bins),
            min(rest_grid.size, center + rounded_bins + 1),
            dtype=np.int64,
        )
        literal_indices = np.arange(
            max(0, center - literal_bins),
            min(rest_grid.size, center + literal_bins + 1),
            dtype=np.int64,
        )
        if center not in rounded_cache:
            rounded_cache[center] = best_local_recurrence(
                off_spectral,
                rest_grid,
                center,
                rounded_indices,
                templates,
                subsets,
                spectral_widths,
                minimum_active_epoch_snr,
                stack_statistic,
            )
            literal_cache[center] = best_local_recurrence(
                off_spectral,
                rest_grid,
                center,
                literal_indices,
                templates,
                subsets,
                spectral_widths,
                minimum_active_epoch_snr,
                stack_statistic,
            )
        track = same_candidate_track(
            off_spectral, record, veto["single_epoch_snr_floor"]
        )
        record["off_at_same_hypothesis_snr"] = evaluate_spectral_record(
            off_spectral,
            record,
            minimum_active_epoch_snr,
            stack_statistic,
        )
        record["v0p5_rounded_local_off_diagnostics"] = {
            "configured_tolerance_hz": float(veto["local_off_tolerance_hz"]),
            "implemented_tolerance_bins": rounded_bins,
            "implemented_maximum_offset_hz": float(rounded_bins * df_hz),
            "best_local_recurrence": rounded_cache[center],
            "same_candidate_track": track,
        }
        record["literal_20hz_local_off_diagnostics"] = {
            "literal_tolerance_hz": float(veto["local_off_tolerance_hz"]),
            "literal_tolerance_bins": literal_bins,
            "literal_maximum_offset_hz": float(literal_bins * df_hz),
            "best_local_recurrence": literal_cache[center],
            "same_candidate_track": track,
        }
        record["receiver_frame_alias_witness"] = None

    stationary_cache: dict[tuple[int, int], np.ndarray] = {}
    factor_cache: dict[tuple[int, float, float], np.ndarray] = {}
    frequency_direction_cache: dict[int, bool] = {}
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    for record in records:
        record["receiver_frame_signature"] = build_receiver_frame_signature_indexed(
            {"best_hypothesis": record},
            scans_by_kind["on"],
            config,
            veto["receiver_local_half_width_hz"],
            stationary_cache,
            factor_cache,
            frequency_direction_cache,
            target,
            location,
        )

    assign_receiver_alias_witnesses(
        records,
        cluster_by_member,
        veto["receiver_alias_tolerance_hz"],
        veto["receiver_alias_minimum_shared_epochs"],
        veto["single_epoch_snr_floor"],
    )

    v0_counts: Counter[str] = Counter()
    literal_counts: Counter[str] = Counter()
    for record in records:
        record["v0p5_member_disposition"] = disposition_for_record(
            record, literal=False
        )
        record["literal_20hz_member_disposition"] = disposition_for_record(
            record, literal=True
        )
        v0_counts[record["v0p5_member_disposition"]] += 1
        literal_counts[record["literal_20hz_member_disposition"]] += 1

    primary_above_keys = set(primary_above_members)
    audit_keys = {
        (
            int(record["spectral_width_index"]),
            int(record["template_index"]),
            tuple(record["active_epochs_zero_based"]),
            int(record["frequency_index"]),
        )
        for record in records
    }
    if not primary_above_keys <= audit_keys:
        raise AssertionError("an above-threshold primary peak is absent from audit union")
    for record in records:
        key = (
            int(record["spectral_width_index"]),
            int(record["template_index"]),
            tuple(record["active_epochs_zero_based"]),
            int(record["frequency_index"]),
        )
        record["present_in_primary_retained_above_threshold_set"] = (
            key in primary_above_keys
        )

    cluster_rows = []
    unresolved_cluster_count = 0
    for cluster in clusters:
        members = cluster.pop("_members")
        member_dispositions = Counter(
            member["literal_20hz_member_disposition"] for member in members
        )
        unresolved = any(
            member["literal_20hz_member_disposition"]
            not in PHYSICAL_DISPOSITIONS
            for member in members
        )
        unresolved_cluster_count += int(unresolved)
        cluster["literal_20hz_member_dispositions"] = dict(
            sorted(member_dispositions.items())
        )
        cluster["all_members_physically_vetoed"] = not unresolved
        cluster_rows.append(cluster)

    records.sort(key=lambda item: str(item["audit_record_id"]))
    certificates.sort(key=lambda item: str(item["hypothesis_id"]))
    certificate_path = output_dir / f"{window_id}_hypothesis_certificates.json.gz"
    record_path = output_dir / f"{window_id}_audit_records.jsonl.gz"
    cluster_path = output_dir / f"{window_id}_clusters.json.gz"
    write_gzip_json(certificate_path, certificates)
    write_gzip_jsonl(record_path, records)
    write_gzip_json(cluster_path, cluster_rows)
    evidence_paths = (
        ledger_path,
        certificate_path,
        record_path,
        cluster_path,
    )
    maximum_file_bytes = int(spec["audit"]["maximum_single_output_file_bytes"])
    oversized = [
        path.name for path in evidence_paths if path.stat().st_size >= maximum_file_bytes
    ]
    if oversized:
        raise AssertionError(
            "audit evidence exceeds frozen publication capacity: "
            + ", ".join(oversized)
        )
    file_evidence = {
        path.name: {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in evidence_paths
    }
    result = {
        "window": window_id,
        "channel_width_hz": df_hz,
        "literal_20hz_radius_channels": literal_bins,
        "literal_20hz_radius_hz": float(literal_bins * df_hz),
        "rounded_v0p5_local_radius_channels": rounded_bins,
        "rounded_v0p5_local_radius_hz": float(rounded_bins * df_hz),
        "hypotheses_visited": len(certificates),
        "score_cells_visited": total_score_cells,
        "above_threshold_score_cells": total_eligible,
        "legacy_unbounded_nms_peaks": total_legacy,
        "literal_20hz_nms_peaks": total_literal,
        "audit_union_records": len(records),
        "primary_crosswalk_only_records": sum(
            item["selected_by"]
            == ["primary_retained_above_threshold_crosswalk"]
            for item in records
        ),
        "audit_clusters": len(cluster_rows),
        "primary_retained_above_threshold_records": len(primary_above_keys),
        "newly_exposed_union_records": sum(
            not item["present_in_primary_retained_above_threshold_set"]
            for item in records
        ),
        "v0p5_member_dispositions": dict(sorted(v0_counts.items())),
        "literal_20hz_member_dispositions": dict(sorted(literal_counts.items())),
        "unresolved_member_count": int(
            literal_counts.get("survives_for_followup", 0)
        ),
        "unresolved_cluster_count": unresolved_cluster_count,
        "unaccounted_above_threshold_cells": 0,
        "primary_reproduction": reproduction,
        "files": file_evidence,
    }
    write_json(output_dir / f"{window_id}_summary.json", result)
    del on_bank, off_bank, on_spectral, off_spectral, on_mask, off_mask
    del scans_by_kind, records, clusters
    gc.collect()
    return result


def run_inventory(args: argparse.Namespace) -> None:
    raw = Path(args.primary_summary).read_bytes()
    summary = json.loads(raw)
    inventory = build_summary_only_inventory(summary)
    inventory["source"]["search_summary_sha256"] = hashlib.sha256(raw).hexdigest()
    write_json(args.output, inventory)


def run_audit(args: argparse.Namespace) -> None:
    spec = load_json(args.spec)
    primary = spec["primary"]
    verify_imported_detector(primary["detector_version"])
    for path_key, hash_key in (
        ("config_path", "config_sha256"),
        ("search_summary_path", "search_summary_sha256"),
        ("data_manifest_path", "data_manifest_sha256"),
        ("results_manifest_path", "results_manifest_sha256"),
        ("summary_only_inventory_path", "summary_only_inventory_sha256"),
        ("provenance_path", "provenance_sha256"),
    ):
        verify_hash(primary[path_key], primary[hash_key])
    for path, expected in spec["source_code_hashes"].items():
        verify_hash(path, expected)
    verify_manifest_files(primary["results_manifest_path"])
    verify_environment(spec["environment"])
    config = load_json(primary["config_path"])
    primary_summary = load_json(primary["search_summary_path"])
    inventory = build_summary_only_inventory(primary_summary)
    inventory["source"]["search_summary_sha256"] = primary[
        "search_summary_sha256"
    ]
    if canonical_json_bytes(inventory) != Path(
        primary["summary_only_inventory_path"]
    ).read_bytes():
        raise AssertionError("summary-only inventory does not reproduce")
    if inventory["counts"]["unresolved_total"] != 195:
        raise AssertionError("frozen non-spectral unresolved count changed")
    verify_reextracted_data(primary["data_manifest_path"], args.data_dir)

    threshold = float(primary_summary["global_result"]["operational_threshold_snr"])
    if threshold != float(spec["audit"]["operational_threshold_snr"]):
        raise AssertionError("frozen operational threshold mismatch")
    templates = make_templates(config)
    subsets = make_subsets(3, config["search"]["minimum_active_epochs"])
    widths = validate_widths(config["search"]["spectral_widths_channels"])
    if (len(config["windows"]), len(templates), len(subsets), len(widths)) != (
        5,
        21,
        4,
        8,
    ):
        raise AssertionError("frozen search dimensions changed")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    windows = []
    for window in config["windows"]:
        print(f"Auditing all score cells in {window['id']}", flush=True)
        windows.append(
            audit_window(
                config,
                spec,
                primary_summary,
                window,
                Path(args.data_dir),
                output_dir,
                templates,
                subsets,
                widths,
            )
        )

    total_hypotheses = sum(item["hypotheses_visited"] for item in windows)
    total_score_cells = sum(item["score_cells_visited"] for item in windows)
    unresolved_members = sum(item["unresolved_member_count"] for item in windows)
    unresolved_clusters = sum(item["unresolved_cluster_count"] for item in windows)
    expected_score_cells = int(
        primary_summary["search_dimensions"]["approx_nominal_trials"]
    )
    if total_hypotheses != 3360 or total_score_cells != expected_score_cells:
        raise AssertionError("exhaustive search-space accounting failed")
    if any(item["unaccounted_above_threshold_cells"] != 0 for item in windows):
        raise AssertionError("coverage certificate is incomplete")
    if unresolved_members:
        outcome = "UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE"
    else:
        outcome = "PRIMARY_CADENCE_NULL_AFTER_COMPLETE_RETENTION_AUDIT"
    summary = {
        "schema_version": 1,
        "audit_name": "Milestone 36 exhaustive above-threshold retention audit",
        "audit_is_supplementary_to_primary": True,
        "outcome": outcome,
        "primary": primary,
        "frozen_operational_threshold_snr": threshold,
        "summary_only_boundary": inventory["counts"],
        "dimensions": {
            "windows": 5,
            "spectral_widths": list(widths),
            "templates": len(templates),
            "activity_subsets": len(subsets),
            "hypotheses": total_hypotheses,
            "score_cells": total_score_cells,
        },
        "totals": {
            "above_threshold_score_cells": sum(
                item["above_threshold_score_cells"] for item in windows
            ),
            "legacy_unbounded_nms_peaks": sum(
                item["legacy_unbounded_nms_peaks"] for item in windows
            ),
            "literal_20hz_nms_peaks": sum(
                item["literal_20hz_nms_peaks"] for item in windows
            ),
            "audit_union_records": sum(
                item["audit_union_records"] for item in windows
            ),
            "primary_crosswalk_only_records": sum(
                item["primary_crosswalk_only_records"] for item in windows
            ),
            "audit_clusters": sum(item["audit_clusters"] for item in windows),
            "newly_exposed_union_records": sum(
                item["newly_exposed_union_records"] for item in windows
            ),
            "unaccounted_above_threshold_cells": 0,
            "unresolved_member_count": unresolved_members,
            "unresolved_cluster_count": unresolved_clusters,
        },
        "stopping_rule": {
            "closure_requires_every_union_member_physical_veto": True,
            "physical_dispositions": list(PHYSICAL_DISPOSITIONS),
            "local_off_closure_uses_literal_maximum_hz": 20.0,
            "rounded_v0p5_local_result_reported_separately": True,
            "arithmetic_family_is_not_physical": True,
            "no_second_qualifying_hip48714_cadence": True,
        },
        "windows": windows,
        "interpretation_limits": [
            "The audit changes neither the primary empirical p-value nor its completeness calibration.",
            "A null outcome is limited to the frozen primary cadence, five windows, motion bank, recurrence model, and measured completeness.",
            "An unresolved member requires independent data; it is not a detection.",
            "Milestone 33 remains unresolved and Milestone 35 population/EIRP limitations remain unchanged.",
        ],
    }
    write_json(output_dir / "audit_summary.json", summary)
    print(json.dumps({"outcome": outcome, **summary["totals"]}, indent=2), flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--primary-summary", required=True)
    inventory.add_argument("--output", required=True)
    inventory.set_defaults(function=run_inventory)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--spec", required=True)
    audit.add_argument("--data-dir", required=True)
    audit.add_argument("--output-dir", required=True)
    audit.set_defaults(function=run_audit)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
