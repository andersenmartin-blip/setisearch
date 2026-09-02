"""Resource-bounded truth-local score evaluation for detector v0.6.

This module implements only the score-recovery endpoint selected by M38.  It
does not run retention, physical vetoes, the global false-positive field, or
an occurrence-rate analysis.  Production use remains gated on real-data
anchor equivalence against the exhaustive M37 window replay.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from typing import Any, Callable, ContextManager, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core
from .adjacent_v0p6 import gather_filtered_native_at_score_indices
from .sparse_replay_v0p6 import (
    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
    SPARSE_LOCAL_REQUIRED_WIDTHS,
    TruthLocalTemplatePlan,
    _finite_json_number,
    _seal_float64,
    _validate_truth_local_template_plan,
    build_local_two_pass_template_mask,
    clipped_score_index_closure,
    make_local_score_index_set,
)


TRUTH_LOCAL_ADAPTER_STATUS = (
    "m39-truth-local-score-adapter-real-anchor-equivalence-pending"
)
TRUTH_LOCAL_INTERVAL_PADDING_BINS = 4
TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS = 1_000_000
TRUTH_LOCAL_MAXIMUM_LOCAL_ARRAY_BYTES = 64 * 1024 * 1024
TRUTH_LOCAL_MAXIMUM_MAPPED_CACHE_BYTES = core.M37_LIVE_NDARRAY_CAP_BYTES


def _sha256(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def _sha256_array(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    if array.size == 0:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def _validate_planner_inputs(
    grid: core.ProxyCarrierGrid,
    template_factor_matrix: np.ndarray,
    truth_proxy_carrier_hz: float,
    truth_factors: np.ndarray,
    *,
    tolerance_hz: float,
    guard_bins: int,
    maximum_distance_cells: int,
) -> tuple[np.ndarray, np.ndarray, float, float, int, int]:
    factors = template_factor_matrix
    truth = truth_factors
    if not isinstance(factors, np.ndarray) or not isinstance(truth, np.ndarray):
        raise core.V0P6ContractError(
            "truth-local factors must be explicit float64 ndarrays"
        )
    if (
        factors.ndim != 2
        or factors.dtype != np.dtype("<f8")
        or truth.ndim != 1
        or truth.dtype != np.dtype("<f8")
        or factors.shape[1] != truth.size
        or factors.shape[0] < 1
        or truth.size < 1
        or not factors.flags.c_contiguous
        or not truth.flags.c_contiguous
        or not np.all(np.isfinite(factors))
        or not np.all(np.isfinite(truth))
        or np.any(factors <= 0.0)
        or np.any(truth <= 0.0)
    ):
        raise core.V0P6ContractError(
            "truth-local factors must be finite positive C-order float64 arrays"
        )
    if (
        not isinstance(grid, core.ProxyCarrierGrid)
        or grid.score_hz.dtype != np.dtype("<f8")
        or grid.score_hz.ndim != 1
        or grid.score_hz.shape != (grid.score_bin_count,)
        or not np.all(np.isfinite(grid.score_hz))
        or np.any(np.diff(grid.score_hz) <= 0.0)
    ):
        raise core.V0P6ContractError("truth-local proxy grid is invalid")
    truth_q = _finite_json_number(truth_proxy_carrier_hz, "truth carrier")
    tolerance = _finite_json_number(tolerance_hz, "truth tolerance")
    guard = core._strict_int(guard_bins, "local mask guard")
    maximum = core._strict_int(
        maximum_distance_cells, "truth-local distance-cell cap"
    )
    if (
        truth_q <= 0.0
        or tolerance < 0.0
        or guard < 0
        or maximum < 1
        or maximum > TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS
    ):
        raise core.V0P6ContractError("truth-local planner parameters are invalid")
    return factors, truth, truth_q, tolerance, guard, maximum


def plan_truth_local_template_scores_interval(
    grid: core.ProxyCarrierGrid,
    template_factor_matrix: np.ndarray,
    truth_proxy_carrier_hz: float,
    truth_factors: np.ndarray,
    *,
    tolerance_hz: float = 20.0,
    guard_bins: int = core.M37_RFI_GUARD_Q_BINS,
    maximum_distance_cells: int = TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS,
) -> tuple[TruthLocalTemplatePlan, ...]:
    """Plan exact local cells from intersected positive-factor intervals.

    The materialized reference evaluates every ``(template, q, integration)``
    distance cell.  Positive factors instead imply one closed q interval per
    integration.  Their intersection bounds the only possible candidates.
    A fixed four-bin outward search pad is then filtered with the exact dense
    binary64 distance expression, preserving inclusive boundary semantics.
    """

    factors, truth, truth_q, tolerance, guard, maximum = _validate_planner_inputs(
        grid,
        template_factor_matrix,
        truth_proxy_carrier_hz,
        truth_factors,
        tolerance_hz=tolerance_hz,
        guard_bins=guard_bins,
        maximum_distance_cells=maximum_distance_cells,
    )
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            truth_track = np.float64(truth_q) * truth
    except FloatingPointError as error:
        raise core.V0P6ContractError(
            "truth-local truth track overflowed float64"
        ) from error
    if not np.all(np.isfinite(truth_track)):
        raise core.V0P6ContractError("truth-local truth track is non-finite")

    grid_digest = core.proxy_carrier_grid_sha256(grid)
    truth_digest = core.float64_vector_sha256(truth)
    score_hz = grid.score_hz
    evaluated_cells = 0
    plans: list[TruthLocalTemplatePlan] = []
    for template_index, row in enumerate(factors):
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                lower_hz = float(np.max((truth_track - tolerance) / row))
                upper_hz = float(np.min((truth_track + tolerance) / row))
        except FloatingPointError as error:
            raise core.V0P6ContractError(
                "truth-local interval calculation overflowed float64"
            ) from error
        if not math.isfinite(lower_hz) or not math.isfinite(upper_hz):
            raise core.V0P6ContractError(
                "truth-local interval calculation produced non-finite values"
            )

        if lower_hz <= upper_hz:
            left = max(
                0,
                int(np.searchsorted(score_hz, lower_hz, side="left"))
                - TRUTH_LOCAL_INTERVAL_PADDING_BINS,
            )
            right = min(
                grid.score_bin_count,
                int(np.searchsorted(score_hz, upper_hz, side="right"))
                + TRUTH_LOCAL_INTERVAL_PADDING_BINS,
            )
            bounded = np.arange(left, right, dtype="<i8")
        else:
            bounded = np.empty(0, dtype="<i8")
        evaluated_cells += int(bounded.size) * int(truth.size)
        if evaluated_cells > maximum:
            raise core.V0P6CapacityError(
                "truth-local interval planner exceeded its distance-cell cap"
            )
        try:
            with np.errstate(over="raise", invalid="raise"):
                distances = np.max(
                    np.abs(
                        score_hz[bounded, None] * row[None, :]
                        - truth_track[None, :]
                    ),
                    axis=1,
                ) if bounded.size else np.empty(0, dtype="<f8")
        except FloatingPointError as error:
            raise core.V0P6ContractError(
                "truth-local distance verification overflowed float64"
            ) from error
        if not np.all(np.isfinite(distances)):
            raise core.V0P6ContractError(
                "truth-local distance verification produced non-finite values"
            )
        accepted = distances <= tolerance
        selected = np.ascontiguousarray(bounded[accepted], dtype="<i8")
        selected_distances = np.ascontiguousarray(distances[accepted], dtype="<f8")
        candidate_set = make_local_score_index_set(
            grid.score_bin_count, selected
        )
        dependency_set = clipped_score_index_closure(
            candidate_set, guard_bins=guard
        )
        sealed_distances, distance_digest = _seal_float64(selected_distances)
        partial = TruthLocalTemplatePlan(
            template_index=template_index,
            proxy_grid_sha256=grid_digest,
            template_factors_sha256=core.float64_vector_sha256(row),
            truth_factors_sha256=truth_digest,
            truth_proxy_carrier_hz=truth_q,
            tolerance_hz=tolerance,
            guard_bins=guard,
            candidate_indices=candidate_set,
            mask_dependency_indices=dependency_set,
            maximum_track_distances_hz=sealed_distances,
            maximum_track_distances_sha256=distance_digest,
            plan_sha256="",
        )
        plan = replace(
            partial,
            plan_sha256=_sha256(partial.as_record(include_identity=False)),
        )
        _validate_truth_local_template_plan(plan)
        plans.append(plan)
    return tuple(plans)


def _array_inventory_sha256(
    arrays: Mapping[tuple[Any, ...], np.ndarray],
) -> str:
    records = []
    for key in sorted(arrays):
        array = np.ascontiguousarray(arrays[key])
        records.append(
            {
                "key": list(key),
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "sha256": _sha256_array(array),
            }
        )
    return _sha256(records)


def evaluate_truth_local_scores(
    plans: Sequence[TruthLocalTemplatePlan],
    grid: core.ProxyCarrierGrid,
    factor_matrices_by_epoch: Sequence[np.ndarray],
    cache_opener: Callable[[int, int], ContextManager[Any]],
    *,
    expected_scan_labels: Sequence[str],
    expected_source_sha256s: Sequence[str],
    window_id: str,
    maximum_local_array_bytes: int = TRUTH_LOCAL_MAXIMUM_LOCAL_ARRAY_BYTES,
    maximum_mapped_cache_bytes: int = TRUTH_LOCAL_MAXIMUM_MAPPED_CACHE_BYTES,
) -> dict[str, Any]:
    """Evaluate the conditional truth-local score from injected cache ancestry.

    Caches are opened one epoch/width at a time.  Only local gather vectors,
    their mask closure, and truth-associated score cells remain resident.
    """

    local_plans = tuple(plans)
    if not local_plans or tuple(item.template_index for item in local_plans) != tuple(
        range(len(local_plans))
    ):
        raise core.V0P6IncompleteError(
            "truth-local plan inventory is empty, duplicated, or reordered"
        )
    for item in local_plans:
        _validate_truth_local_template_plan(item)
        if item.proxy_grid_sha256 != core.proxy_carrier_grid_sha256(grid):
            raise core.V0P6IncompleteError("truth-local plan grid changed")
    matrices = tuple(factor_matrices_by_epoch)
    labels = tuple(str(item) for item in expected_scan_labels)
    source_digests = tuple(
        core._frozen_sha256(item, "injected source identity")
        for item in expected_source_sha256s
    )
    if len(matrices) != 3 or len(labels) != 3 or len(source_digests) != 3:
        raise core.V0P6ContractError(
            "truth-local adapter requires exactly three ON epochs"
        )
    integration_counts: list[int] = []
    for matrix in matrices:
        if (
            not isinstance(matrix, np.ndarray)
            or matrix.dtype != np.dtype("<f8")
            or matrix.ndim != 2
            or matrix.shape[0] != len(local_plans)
            or not matrix.flags.c_contiguous
            or not np.all(np.isfinite(matrix))
            or np.any(matrix <= 0.0)
        ):
            raise core.V0P6ContractError(
                "truth-local epoch factors must be finite C-order float64 matrices"
            )
        integration_counts.append(int(matrix.shape[1]))
    local_cap = core._strict_int(maximum_local_array_bytes, "local array-byte cap")
    mapped_cap = core._strict_int(
        maximum_mapped_cache_bytes, "mapped cache-byte cap"
    )
    if local_cap < 1 or mapped_cap < 1:
        raise core.V0P6ContractError("truth-local resource caps must be positive")

    dependency_vectors: dict[tuple[int, int], np.ndarray] = {}
    cache_inventory: list[dict[str, Any]] = []
    maximum_mapped = 0
    local_array_bytes = 0
    for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
        per_template = {
            item.template_index: np.empty(
                (3, item.mask_dependency_indices.indices.size), dtype="<f4"
            )
            for item in local_plans
        }
        for epoch in range(3):
            with cache_opener(epoch, width) as cache:
                cache_plan, _ = core._cache_values_for_gather(cache)
                if (
                    cache_plan.window_id != str(window_id)
                    or cache_plan.scan_kind != "on"
                    or cache_plan.scan_label != labels[epoch]
                    or cache_plan.width_channels != width
                    or cache_plan.integration_count != integration_counts[epoch]
                    or cache_plan.source_sha256 != source_digests[epoch]
                ):
                    raise core.V0P6IncompleteError(
                        "truth-local cache ancestry differs from the injected source"
                    )
                maximum_mapped = max(maximum_mapped, cache_plan.payload_nbytes)
                if maximum_mapped > mapped_cap:
                    raise core.V0P6CapacityError(
                        "truth-local mapped-cache byte cap exceeded"
                    )
                cache_inventory.append(
                    {
                        "epoch": epoch,
                        "scan_label": labels[epoch],
                        "width_channels": width,
                        "plan_sha256": cache_plan.plan_sha256,
                        "source_sha256": cache_plan.source_sha256,
                        "payload_nbytes": cache_plan.payload_nbytes,
                        "payload_sha256": str(cache.payload_sha256),
                    }
                )
                for item in local_plans:
                    selected = item.mask_dependency_indices.indices
                    if selected.size:
                        per_template[item.template_index][epoch] = (
                            gather_filtered_native_at_score_indices(
                                cache,
                                matrices[epoch][item.template_index],
                                grid,
                                selected,
                            )
                        )
        for template_index, values in per_template.items():
            sealed = np.ascontiguousarray(values, dtype="<f4")
            dependency_vectors[(template_index, width)] = sealed
            local_array_bytes += sealed.nbytes
            if local_array_bytes > local_cap:
                raise core.V0P6CapacityError(
                    "truth-local resident local-array byte cap exceeded"
                )

    masks: dict[tuple[int], np.ndarray] = {}
    scores: dict[tuple[int, int, int], np.ndarray] = {}
    best: tuple[float, int, int, int, int] | None = None
    score_cells = 0
    for item in local_plans:
        candidates = item.candidate_indices.indices
        dependency = item.mask_dependency_indices.indices

        def vector_factory(width: int, selected: np.ndarray) -> np.ndarray:
            if not np.array_equal(selected, dependency):
                raise core.V0P6IncompleteError(
                    "truth-local mask dependency coordinates changed"
                )
            return dependency_vectors[(item.template_index, width)]

        mask = np.ascontiguousarray(
            build_local_two_pass_template_mask(
                vector_factory, item.candidate_indices
            ),
            dtype=bool,
        )
        masks[(item.template_index,)] = mask
        local_array_bytes += mask.nbytes
        if local_array_bytes > local_cap:
            raise core.V0P6CapacityError(
                "truth-local resident local-array byte cap exceeded"
            )
        positions = np.searchsorted(dependency, candidates)
        if candidates.size and (
            np.any(positions >= dependency.size)
            or not np.array_equal(dependency[positions], candidates)
        ):
            raise core.V0P6IncompleteError(
                "truth-local candidates are absent from their mask closure"
            )
        for width_index, width in enumerate(SPARSE_LOCAL_REQUIRED_WIDTHS):
            vectors = np.ascontiguousarray(
                dependency_vectors[(item.template_index, width)][:, positions],
                dtype="<f4",
            )
            for subset_index, subset in enumerate(
                SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
            ):
                score = np.ascontiguousarray(
                    core.stack_hypothesis(
                        vectors,
                        subset,
                        minimum_active_epoch_snr=3.0,
                        stack_statistic="minimum_epoch",
                        exclusion_mask=mask,
                    ),
                    dtype="<f4",
                )
                scores[(item.template_index, width_index, subset_index)] = score
                local_array_bytes += score.nbytes
                score_cells += score.size
                if local_array_bytes > local_cap:
                    raise core.V0P6CapacityError(
                        "truth-local resident local-array byte cap exceeded"
                    )
                for ordinal, raw_value in enumerate(score):
                    value = float(raw_value)
                    if not math.isfinite(value):
                        continue
                    candidate = (
                        value,
                        item.template_index,
                        width_index,
                        subset_index,
                        int(candidates[ordinal]),
                    )
                    if best is None or value > best[0]:
                        best = candidate

    plan_records = [item.as_record() for item in local_plans]
    result = {
        "artifact_type": "m39-truth-local-score-result-v1",
        "status": TRUTH_LOCAL_ADAPTER_STATUS,
        "window_id": str(window_id),
        "template_count": len(local_plans),
        "spectral_widths": list(SPARSE_LOCAL_REQUIRED_WIDTHS),
        "activity_subsets": [
            list(item) for item in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
        ],
        "candidate_score_cell_count": score_cells,
        "mask_dependency_vector_cell_count": sum(
            int(item.mask_dependency_indices.indices.size)
            * len(SPARSE_LOCAL_REQUIRED_WIDTHS)
            * 3
            for item in local_plans
        ),
        "cache_count": len(cache_inventory),
        "maximum_mapped_cache_bytes_observed": maximum_mapped,
        "maximum_mapped_cache_bytes": mapped_cap,
        "local_array_bytes_observed": local_array_bytes,
        "maximum_local_array_bytes": local_cap,
        "plan_inventory_sha256": _sha256(plan_records),
        "cache_inventory_sha256": _sha256(cache_inventory),
        "mask_inventory_sha256": _array_inventory_sha256(masks),
        "score_inventory_sha256": _array_inventory_sha256(scores),
        "best_truth_local_score_snr": None if best is None else best[0],
        "best_hypothesis": None
        if best is None
        else {
            "template_index": best[1],
            "spectral_width_index": best[2],
            "spectral_width_channels": SPARSE_LOCAL_REQUIRED_WIDTHS[best[2]],
            "activity_subset_index": best[3],
            "active_epochs_zero_based": list(
                SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS[best[3]]
            ),
            "proxy_carrier_index": best[4],
            "proxy_carrier_hz": float(grid.score_hz[best[4]]),
        },
        "two_pass_mask_recomputed": True,
        "global_false_positive_field_replayed": False,
        "physical_veto_survival_calibrated": False,
        "production_equivalence_proven": False,
    }
    result["result_sha256"] = _sha256(result)
    return result
