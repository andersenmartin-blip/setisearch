"""Synthetic truth-local replay references for detector-v0.6.

This module proves only a deliberately narrow numerical statement: selected
native gathers, coordinate-aware two-pass masks, and pointwise hypothesis
scores can reproduce their dense synthetic references bit for bit.  It is not
a production completeness implementation.  In particular, it does not prove
that exhaustive retention, OFF dispositions, receiver-alias connected
components, or their transitive dependencies are local.

Every materialized truth-distance oracle has a hard cell cap so the reference
planner cannot accidentally be applied to the full M37 grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


SPARSE_LOCAL_REFERENCE_STATUS = (
    "synthetic-truth-local-reference-global-equivalence-unproven"
)
SPARSE_LOCAL_FIXTURE_ARTIFACT_TYPE = (
    "m37-v0p6-synthetic-sparse-local-reference-fixture-v1"
)
SPARSE_LOCAL_MAXIMUM_DISTANCE_CELLS = 2_000_000
SPARSE_LOCAL_REQUIRED_WIDTHS = core.M37_SPECTRAL_WIDTHS
SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS = core.M37_ACTIVITY_SUBSETS
SPARSE_LOCAL_REQUIRED_EPOCH_COUNT = 3
SPARSE_LOCAL_REQUIRED_COVERAGE = (
    "all-eight-widths",
    "all-three-epochs",
    "all-four-activity-subsets",
    "nearest-native-half-bin-ties",
    "circular-roll-seam",
    "score-grid-endpoints",
    "overlapping-and-touching-closures",
    "clipped-plus-minus-nine-mask-closure",
    "inclusive-twenty-hz-boundary",
)
_SPARSE_LOCAL_KAT_SEED = 37_060_613
_SPARSE_LOCAL_KAT_NATIVE_CHANNEL_COUNT = 1_024
_SPARSE_LOCAL_KAT_INTEGRATION_COUNT_PER_EPOCH = 2
_SPARSE_LOCAL_KAT_DISTANCE_INTEGRATION_COUNT = 6
_SPARSE_LOCAL_KAT_TEMPLATE_COUNT = 3
_SPARSE_LOCAL_KAT_SCORE_BIN_COUNT = 41
_SPARSE_LOCAL_KAT_SUPPORT_BIN_COUNT = 169
_SPARSE_LOCAL_KAT_TRUTH_PROXY_CARRIER_HZ = 500.0
_SPARSE_LOCAL_KAT_PROXY_GRID_SHA256 = (
    "5c13bf44c1f849ac023e7f915490012e27cd661590bb43ef3e525d8ceabf827f"
)
SPARSE_LOCAL_KAT_FIXTURE_SHA256 = (
    "b3ec37255a43219a7bc6bb84d4e22df60a98458910c02262096b69c72817fcc1"
)
SPARSE_LOCAL_KAT_PLAN_INVENTORY_SHA256 = (
    "02fbcb46e7766fe042563f284cdb18ab1e84f6aafd2b16e873aa64356b96f66d"
)
SPARSE_LOCAL_KAT_GATHERS_SHA256 = (
    "7b6fbf3f72a5409e3b3948b565827e67183fdf53a608a4c0020e10b6b9ee2a1a"
)
SPARSE_LOCAL_KAT_ISOLATED_MASKS_SHA256 = (
    "4bc200300fc341a613459068c51f76e2d02fb8e1145ca24044cee452fdee2a23"
)
SPARSE_LOCAL_KAT_MASKS_SHA256 = (
    "e04f3bc8d0e354fad5246f6c7c76796ef7d3e2780b0f05bb59df7b875a3a9eae"
)
SPARSE_LOCAL_KAT_SCORES_SHA256 = (
    "8f051405840dad8d8cc0c45cdd001ac573b5b2df40928e5c85f779ebc40e8aab"
)
SPARSE_LOCAL_KAT_RECEIPT_SHA256 = (
    "32e9208579e435be0cefa72c13e579c8020ec361f23fa9650e9adbf25cfe9201"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _frozen_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise core.V0P6ContractError(
            f"{label} must be an exact lowercase SHA-256 string"
        )
    return value


def _finite_json_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    return converted


def _runs_for_indices(indices: np.ndarray) -> tuple[tuple[int, int], ...]:
    if indices.size == 0:
        return ()
    runs: list[tuple[int, int]] = []
    start = int(indices[0])
    prior = start
    for raw in indices[1:]:
        current = int(raw)
        if current != prior + 1:
            runs.append((start, prior + 1))
            start = current
        prior = current
    runs.append((start, prior + 1))
    return tuple(runs)


@dataclass(frozen=True)
class LocalScoreIndexSet:
    """Immutable, sorted score indices plus coordinate-preserving runs."""

    score_bin_count: int
    indices: np.ndarray = field(repr=False, compare=False)
    runs: tuple[tuple[int, int], ...]
    indices_sha256: str
    set_sha256: str

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "score_bin_count": self.score_bin_count,
            "index_count": int(self.indices.size),
            "indices_dtype": "<i8",
            "indices_sha256": self.indices_sha256,
            "runs": [list(item) for item in self.runs],
        }
        if include_identity:
            record["set_sha256"] = self.set_sha256
        return record


def make_local_score_index_set(
    score_bin_count: int,
    indices: Sequence[int] | np.ndarray,
) -> LocalScoreIndexSet:
    """Canonicalize exact integer indices without accepting floats or bools."""
    count = core._strict_int(score_bin_count, "score-bin count")
    if count < 1:
        raise core.V0P6ContractError("score-bin count must be positive")
    if isinstance(indices, np.ndarray):
        if indices.ndim != 1:
            raise core.V0P6ContractError(
                "local score indices must be one-dimensional"
            )
        original = tuple(indices)
    else:
        try:
            original = tuple(indices)
        except TypeError as error:
            raise core.V0P6ContractError(
                "local score indices must be an iterable of exact integers"
            ) from error
    exact = np.empty(len(original), dtype="<i8")
    # Validate before NumPy conversion.  Otherwise a mixed Python sequence
    # such as [True, 2] is silently promoted to int64 and loses its bool type.
    for ordinal, value in enumerate(original):
        exact[ordinal] = core._strict_int(value, "local score index")
    exact = np.unique(exact)
    if exact.size and (
        int(exact[0]) < 0 or int(exact[-1]) >= count
    ):
        raise core.V0P6ContractError("local score index is outside the grid")
    payload = np.ascontiguousarray(exact, dtype="<i8").tobytes()
    sealed = np.frombuffer(payload, dtype="<i8")
    runs = _runs_for_indices(sealed)
    partial = LocalScoreIndexSet(
        score_bin_count=count,
        indices=sealed,
        runs=runs,
        indices_sha256=_sha256_bytes(payload),
        set_sha256="",
    )
    result = replace(
        partial,
        set_sha256=_sha256_bytes(
            core.canonical_json_bytes(partial.as_record(include_identity=False))
        ),
    )
    validate_local_score_index_set(result)
    return result


def validate_local_score_index_set(index_set: LocalScoreIndexSet) -> None:
    if not isinstance(index_set, LocalScoreIndexSet):
        raise core.V0P6ContractError("local index set has an invalid type")
    count = core._strict_int(index_set.score_bin_count, "score-bin count")
    array = index_set.indices
    if (
        count < 1
        or not isinstance(array, np.ndarray)
        or array.ndim != 1
        or array.dtype != np.dtype("<i8")
        or array.flags.writeable
        or not array.flags.c_contiguous
    ):
        raise core.V0P6IncompleteError("local index-set layout changed")
    root: Any = array
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    if not isinstance(getattr(root, "base", None), bytes):
        raise core.V0P6IncompleteError("local index set is not immutable")
    if array.size and (
        int(array[0]) < 0
        or int(array[-1]) >= count
        or np.any(np.diff(array) <= 0)
    ):
        raise core.V0P6IncompleteError("local indices are not sorted and unique")
    for run in index_set.runs:
        if not isinstance(run, tuple) or len(run) != 2:
            raise core.V0P6IncompleteError("local coordinate run type changed")
        core._strict_int(run[0], "local run start")
        core._strict_int(run[1], "local run stop")
    if index_set.runs != _runs_for_indices(array):
        raise core.V0P6IncompleteError("local coordinate runs changed")
    observed_indices = _sha256_bytes(memoryview(array).cast("B"))
    if observed_indices != _frozen_sha256(
        index_set.indices_sha256, "local index identity"
    ):
        raise core.V0P6IncompleteError("local index bytes changed")
    observed_set = _sha256_bytes(
        core.canonical_json_bytes(index_set.as_record(include_identity=False))
    )
    if observed_set != _frozen_sha256(index_set.set_sha256, "local set identity"):
        raise core.V0P6IncompleteError("local index-set identity changed")


def clipped_score_index_closure(
    indices: LocalScoreIndexSet,
    *,
    guard_bins: int,
) -> LocalScoreIndexSet:
    """Dilate runs in original q coordinates, clip edges, and never wrap."""
    validate_local_score_index_set(indices)
    guard = core._strict_int(guard_bins, "local mask guard")
    if guard < 0:
        raise core.V0P6ContractError("local mask guard must be non-negative")
    expanded: list[tuple[int, int]] = []
    for start, stop in indices.runs:
        left = max(0, start - guard)
        right = min(indices.score_bin_count, stop + guard)
        if expanded and left <= expanded[-1][1]:
            expanded[-1] = (expanded[-1][0], max(expanded[-1][1], right))
        else:
            expanded.append((left, right))
    if not expanded:
        return make_local_score_index_set(indices.score_bin_count, [])
    materialized = np.concatenate(
        [np.arange(start, stop, dtype="<i8") for start, stop in expanded]
    )
    return make_local_score_index_set(indices.score_bin_count, materialized)


@dataclass(frozen=True)
class TruthLocalTemplatePlan:
    """Small materialized truth-distance plan for one template."""

    template_index: int
    proxy_grid_sha256: str
    template_factors_sha256: str
    truth_factors_sha256: str
    truth_proxy_carrier_hz: float
    tolerance_hz: float
    guard_bins: int
    candidate_indices: LocalScoreIndexSet
    mask_dependency_indices: LocalScoreIndexSet
    maximum_track_distances_hz: np.ndarray = field(repr=False, compare=False)
    maximum_track_distances_sha256: str
    plan_sha256: str

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "template_index": self.template_index,
            "proxy_grid_sha256": self.proxy_grid_sha256,
            "template_factors_sha256": self.template_factors_sha256,
            "truth_factors_sha256": self.truth_factors_sha256,
            "truth_proxy_carrier_hz": self.truth_proxy_carrier_hz,
            "tolerance_hz": self.tolerance_hz,
            "guard_bins": self.guard_bins,
            "candidate_indices": self.candidate_indices.as_record(),
            "mask_dependency_indices": self.mask_dependency_indices.as_record(),
            "maximum_track_distances_shape": [
                int(self.maximum_track_distances_hz.size)
            ],
            "maximum_track_distances_dtype": "<f8",
            "maximum_track_distances_sha256": (
                self.maximum_track_distances_sha256
            ),
        }
        if include_identity:
            record["plan_sha256"] = self.plan_sha256
        return record


def _seal_float64(values: np.ndarray) -> tuple[np.ndarray, str]:
    payload = np.ascontiguousarray(values, dtype="<f8").tobytes()
    return np.frombuffer(payload, dtype="<f8"), _sha256_bytes(payload)


def _validate_truth_local_template_plan(plan: TruthLocalTemplatePlan) -> None:
    if not isinstance(plan, TruthLocalTemplatePlan):
        raise core.V0P6ContractError("truth-local plan has an invalid type")
    template = core._strict_int(plan.template_index, "template index")
    guard = core._strict_int(plan.guard_bins, "local mask guard")
    truth_q = _finite_json_number(plan.truth_proxy_carrier_hz, "truth carrier")
    tolerance = _finite_json_number(plan.tolerance_hz, "truth tolerance")
    if template < 0 or guard < 0 or truth_q <= 0.0 or tolerance < 0.0:
        raise core.V0P6ContractError("truth-local plan parameters are invalid")
    for digest, label in (
        (plan.proxy_grid_sha256, "proxy grid"),
        (plan.template_factors_sha256, "template factors"),
        (plan.truth_factors_sha256, "truth factors"),
        (plan.maximum_track_distances_sha256, "truth distances"),
        (plan.plan_sha256, "truth-local plan"),
    ):
        _frozen_sha256(digest, label)
    validate_local_score_index_set(plan.candidate_indices)
    validate_local_score_index_set(plan.mask_dependency_indices)
    expected_dependency = clipped_score_index_closure(
        plan.candidate_indices, guard_bins=guard
    )
    if expected_dependency.as_record() != plan.mask_dependency_indices.as_record():
        raise core.V0P6IncompleteError("truth-local mask dependency changed")
    distances = plan.maximum_track_distances_hz
    if (
        not isinstance(distances, np.ndarray)
        or distances.dtype != np.dtype("<f8")
        or distances.ndim != 1
        or distances.size != plan.candidate_indices.indices.size
        or distances.flags.writeable
        or not distances.flags.c_contiguous
        or not np.all(np.isfinite(distances))
        or np.any(distances < 0.0)
        or np.any(distances > tolerance)
    ):
        raise core.V0P6IncompleteError("truth-local distance evidence changed")
    root: Any = distances
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    if not isinstance(getattr(root, "base", None), bytes):
        raise core.V0P6IncompleteError("truth-local distances are not immutable")
    if _sha256_bytes(memoryview(distances).cast("B")) != (
        plan.maximum_track_distances_sha256
    ):
        raise core.V0P6IncompleteError("truth-local distance bytes changed")
    if _sha256_bytes(
        core.canonical_json_bytes(plan.as_record(include_identity=False))
    ) != plan.plan_sha256:
        raise core.V0P6IncompleteError("truth-local plan identity changed")


def plan_truth_local_template_scores(
    grid: core.ProxyCarrierGrid,
    template_factor_matrix: np.ndarray,
    truth_proxy_carrier_hz: float,
    truth_factors: np.ndarray,
    *,
    tolerance_hz: float = 20.0,
    guard_bins: int = core.M37_RFI_GUARD_Q_BINS,
    maximum_distance_cells: int = SPARSE_LOCAL_MAXIMUM_DISTANCE_CELLS,
) -> tuple[TruthLocalTemplatePlan, ...]:
    """Build a capped, fully materialized distance oracle for small KATs."""
    # Exact ndarray types are part of this reference boundary.  Converting a
    # mixed Python sequence first could erase bool/string substitutions.
    if not isinstance(template_factor_matrix, np.ndarray) or not isinstance(
        truth_factors, np.ndarray
    ):
        raise core.V0P6ContractError(
            "truth-local factors must be explicit float64 ndarrays"
        )
    factors = template_factor_matrix
    truth = truth_factors
    if (
        factors.ndim != 2
        or factors.dtype != np.dtype("<f8")
        or truth.ndim != 1
        or truth.dtype != np.dtype("<f8")
        or factors.shape[1] != truth.size
        or factors.shape[0] < 1
        or truth.size < 1
        or not np.all(np.isfinite(factors))
        or not np.all(np.isfinite(truth))
        or np.any(factors <= 0.0)
        or np.any(truth <= 0.0)
    ):
        raise core.V0P6ContractError(
            "truth-local factors must be finite positive native float64 arrays"
        )
    truth_q = _finite_json_number(truth_proxy_carrier_hz, "truth carrier")
    tolerance = _finite_json_number(tolerance_hz, "truth tolerance")
    guard = core._strict_int(guard_bins, "local mask guard")
    maximum = core._strict_int(maximum_distance_cells, "distance-cell cap")
    if (
        truth_q <= 0.0
        or tolerance < 0.0
        or guard < 0
        or maximum < 1
        or maximum > SPARSE_LOCAL_MAXIMUM_DISTANCE_CELLS
    ):
        raise core.V0P6ContractError("truth-local planner parameters are invalid")
    cells = factors.shape[0] * grid.score_bin_count * truth.size
    if cells > maximum:
        raise core.V0P6CapacityError(
            f"truth-local materialized oracle would evaluate {cells} cells"
        )
    grid_digest = core.proxy_carrier_grid_sha256(grid)
    truth_digest = core.float64_vector_sha256(truth)
    try:
        with np.errstate(over="raise", invalid="raise"):
            truth_track = np.float64(truth_q) * truth
    except FloatingPointError as error:
        raise core.V0P6ContractError(
            "truth-local truth track overflowed float64"
        ) from error
    if not np.all(np.isfinite(truth_track)):
        raise core.V0P6ContractError("truth-local truth track is non-finite")
    plans: list[TruthLocalTemplatePlan] = []
    for template_index, row in enumerate(factors):
        try:
            with np.errstate(over="raise", invalid="raise"):
                distances = np.max(
                    np.abs(
                        grid.score_hz[:, None] * row[None, :]
                        - truth_track[None, :]
                    ),
                    axis=1,
                )
        except FloatingPointError as error:
            raise core.V0P6ContractError(
                "truth-local distance oracle overflowed float64"
            ) from error
        if not np.all(np.isfinite(distances)):
            raise core.V0P6ContractError(
                "truth-local distance oracle produced non-finite values"
            )
        selected = np.flatnonzero(distances <= tolerance).astype("<i8")
        candidate_set = make_local_score_index_set(grid.score_bin_count, selected)
        dependency_set = clipped_score_index_closure(
            candidate_set, guard_bins=guard
        )
        sealed_distances, distance_digest = _seal_float64(distances[selected])
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
            plan_sha256=_sha256_bytes(
                core.canonical_json_bytes(partial.as_record(include_identity=False))
            ),
        )
        _validate_truth_local_template_plan(plan)
        plans.append(plan)
    return tuple(plans)


def validate_truth_local_template_plans(
    plans: Sequence[TruthLocalTemplatePlan],
    grid: core.ProxyCarrierGrid,
    template_factor_matrix: np.ndarray,
    truth_proxy_carrier_hz: float,
    truth_factors: np.ndarray,
    *,
    tolerance_hz: float = 20.0,
    guard_bins: int = core.M37_RFI_GUARD_Q_BINS,
    maximum_distance_cells: int = SPARSE_LOCAL_MAXIMUM_DISTANCE_CELLS,
) -> None:
    expected = plan_truth_local_template_scores(
        grid,
        template_factor_matrix,
        truth_proxy_carrier_hz,
        truth_factors,
        tolerance_hz=tolerance_hz,
        guard_bins=guard_bins,
        maximum_distance_cells=maximum_distance_cells,
    )
    if len(plans) != len(expected):
        raise core.V0P6IncompleteError("truth-local template inventory changed")
    for observed, reference in zip(plans, expected, strict=True):
        _validate_truth_local_template_plan(observed)
        if observed.as_record() != reference.as_record() or not np.array_equal(
            observed.maximum_track_distances_hz,
            reference.maximum_track_distances_hz,
        ):
            raise core.V0P6IncompleteError("truth-local template plan changed")


def build_local_two_pass_template_mask(
    vector_factory: Callable[[int, np.ndarray], np.ndarray],
    candidate_indices: LocalScoreIndexSet,
    *,
    widths: Sequence[int] = SPARSE_LOCAL_REQUIRED_WIDTHS,
    strong_snr: float = core.M37_RFI_STRONG_SNR,
    other_epochs_below_snr: float = core.M37_RFI_OTHER_EPOCHS_BELOW_SNR,
    guard_bins: int = core.M37_RFI_GUARD_Q_BINS,
) -> np.ndarray:
    """Return a local mask using original q coordinates, never compressed gaps."""
    validate_local_score_index_set(candidate_indices)
    widths = core._strict_widths(widths)
    strong = _finite_json_number(strong_snr, "strong single-epoch threshold")
    other = _finite_json_number(
        other_epochs_below_snr, "other-epoch ceiling"
    )
    guard = core._strict_int(guard_bins, "local mask guard")
    if strong <= other or guard < 0:
        raise core.V0P6ContractError("local mask thresholds or guard are invalid")
    dependency = clipped_score_index_closure(
        candidate_indices, guard_bins=guard
    )
    combined: np.ndarray | None = None
    for width in widths:
        vectors = vector_factory(width, dependency.indices)
        if (
            not isinstance(vectors, np.ndarray)
            or vectors.dtype != np.dtype("<f4")
            or vectors.shape
            != (
                SPARSE_LOCAL_REQUIRED_EPOCH_COUNT,
                dependency.indices.size,
            )
            or not vectors.flags.c_contiguous
            or not np.all(np.isfinite(vectors))
        ):
            raise core.V0P6ContractError(
                "local vector factory must return finite C-order float32 [3,n]"
            )
        current = core.isolated_single_epoch_mask(vectors, strong, other)
        combined = current if combined is None else (combined | current)
    assert combined is not None
    result = np.zeros(
        (SPARSE_LOCAL_REQUIRED_EPOCH_COUNT, candidate_indices.indices.size),
        dtype=bool,
    )
    for ordinal, raw_index in enumerate(candidate_indices.indices):
        index = int(raw_index)
        left = int(np.searchsorted(dependency.indices, index - guard, side="left"))
        right = int(
            np.searchsorted(dependency.indices, index + guard, side="right")
        )
        if right > left:
            result[:, ordinal] = np.any(combined[:, left:right], axis=1)
    return result


def _keyed_array_inventory_sha256(
    arrays: Mapping[Any, np.ndarray],
    ordered_keys: Sequence[Any],
) -> str:
    inventory: list[dict[str, Any]] = []
    for key in ordered_keys:
        array = arrays[key]
        inventory.append(
            {
                "key": list(key) if isinstance(key, tuple) else key,
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "sha256": _sha256_bytes(memoryview(array).cast("B")),
            }
        )
    return _sha256_bytes(core.canonical_json_bytes(inventory))


def _canonical_gather_key(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, tuple) or len(value) != 3:
        raise core.V0P6ContractError(
            "sparse KAT gather keys must be (template,width,epoch) tuples"
        )
    return (
        core._strict_int(value[0], "gather template"),
        core._strict_int(value[1], "gather width"),
        core._strict_int(value[2], "gather epoch"),
    )


def _canonical_width_mask_key(value: Any) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise core.V0P6ContractError(
            "sparse KAT width-mask keys must be (template,width) tuples"
        )
    return (
        core._strict_int(value[0], "width-mask template"),
        core._strict_int(value[1], "width-mask width"),
    )


def _canonical_score_key(
    value: Any,
) -> tuple[int, int, tuple[int, ...]]:
    if not isinstance(value, tuple) or len(value) != 3:
        raise core.V0P6ContractError(
            "sparse KAT score keys must be (template,width,subset) tuples"
        )
    if not isinstance(value[2], tuple):
        raise core.V0P6ContractError(
            "sparse KAT score-key subsets must be tuples"
        )
    return (
        core._strict_int(value[0], "score template"),
        core._strict_int(value[1], "score width"),
        core.canonical_activity_subsets((value[2],))[0],
    )


def _require_exact_mapping_keys(
    arrays: Mapping[Any, np.ndarray],
    expected_keys: Sequence[Any],
    key_factory: Callable[[Any], Any],
    label: str,
) -> None:
    if not isinstance(arrays, Mapping):
        raise core.V0P6ContractError(
            f"sparse KAT {label} inventory must be a mapping"
        )
    observed = tuple(key_factory(key) for key in arrays)
    if len(observed) != len(set(observed)) or set(observed) != set(expected_keys):
        raise core.V0P6IncompleteError(
            f"sparse KAT {label} label inventory is incomplete or substituted"
        )


@dataclass(frozen=True)
class SparseLocalReferenceKATReceipt:
    """Receipt for equal synthetic arrays; never a production certificate."""

    status: str
    fixture_sha256: str
    plan_inventory_sha256: str
    covered_contracts: tuple[str, ...]
    template_count: int
    score_bin_count: int
    epoch_count: int
    spectral_widths: tuple[int, ...]
    activity_subsets: tuple[tuple[int, ...], ...]
    gather_array_count: int
    isolated_mask_array_count: int
    mask_array_count: int
    score_array_count: int
    dense_gathers_sha256: str
    local_gathers_sha256: str
    dense_isolated_masks_sha256: str
    local_isolated_masks_sha256: str
    dense_masks_sha256: str
    local_masks_sha256: str
    dense_scores_sha256: str
    local_scores_sha256: str
    gather_bits_equal: bool
    mask_bytes_equal: bool
    score_bits_equal: bool
    production_equivalence_claimed: bool
    global_retention_equivalence_proven: bool
    receiver_alias_equivalence_proven: bool
    off_disposition_equivalence_proven: bool
    rank_p_equivalence_proven: bool
    production_receipt_ancestry_proven: bool
    production_feasibility_gate_changed: bool
    receipt_sha256: str

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "status": self.status,
            "fixture_sha256": self.fixture_sha256,
            "plan_inventory_sha256": self.plan_inventory_sha256,
            "covered_contracts": list(self.covered_contracts),
            "template_count": self.template_count,
            "score_bin_count": self.score_bin_count,
            "epoch_count": self.epoch_count,
            "spectral_widths": list(self.spectral_widths),
            "activity_subsets": [list(item) for item in self.activity_subsets],
            "gather_array_count": self.gather_array_count,
            "isolated_mask_array_count": self.isolated_mask_array_count,
            "mask_array_count": self.mask_array_count,
            "score_array_count": self.score_array_count,
            "dense_gathers_sha256": self.dense_gathers_sha256,
            "local_gathers_sha256": self.local_gathers_sha256,
            "dense_isolated_masks_sha256": (
                self.dense_isolated_masks_sha256
            ),
            "local_isolated_masks_sha256": (
                self.local_isolated_masks_sha256
            ),
            "dense_masks_sha256": self.dense_masks_sha256,
            "local_masks_sha256": self.local_masks_sha256,
            "dense_scores_sha256": self.dense_scores_sha256,
            "local_scores_sha256": self.local_scores_sha256,
            "gather_bits_equal": self.gather_bits_equal,
            "mask_bytes_equal": self.mask_bytes_equal,
            "score_bits_equal": self.score_bits_equal,
            "production_equivalence_claimed": self.production_equivalence_claimed,
            "global_retention_equivalence_proven": (
                self.global_retention_equivalence_proven
            ),
            "receiver_alias_equivalence_proven": (
                self.receiver_alias_equivalence_proven
            ),
            "off_disposition_equivalence_proven": (
                self.off_disposition_equivalence_proven
            ),
            "rank_p_equivalence_proven": self.rank_p_equivalence_proven,
            "production_receipt_ancestry_proven": (
                self.production_receipt_ancestry_proven
            ),
            "production_feasibility_gate_changed": (
                self.production_feasibility_gate_changed
            ),
        }
        if include_identity:
            record["receipt_sha256"] = self.receipt_sha256
        return record


def seal_sparse_local_reference_kat_receipt(
    fixture: Mapping[str, Any],
    plans: Sequence[TruthLocalTemplatePlan],
    *,
    dense_gathers: Mapping[tuple[int, int, int], np.ndarray],
    local_gathers: Mapping[tuple[int, int, int], np.ndarray],
    dense_isolated_masks: Mapping[tuple[int, int], np.ndarray],
    local_isolated_masks: Mapping[tuple[int, int], np.ndarray],
    dense_masks: Mapping[int, np.ndarray],
    local_masks: Mapping[int, np.ndarray],
    dense_scores: Mapping[tuple[int, int, tuple[int, ...]], np.ndarray],
    local_scores: Mapping[tuple[int, int, tuple[int, ...]], np.ndarray],
) -> SparseLocalReferenceKATReceipt:
    """Seal one exact label-keyed synthetic dense/local KAT inventory."""
    try:
        fixture_record = json.loads(core.canonical_json_bytes(dict(fixture)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError("sparse KAT fixture is not finite JSON") from error
    plans = tuple(plans)
    if not plans:
        raise core.V0P6IncompleteError("sparse KAT plan inventory is empty")
    for plan in plans:
        _validate_truth_local_template_plan(plan)
    if tuple(plan.template_index for plan in plans) != tuple(range(len(plans))):
        raise core.V0P6IncompleteError(
            "sparse KAT template plans are duplicated or reordered"
        )
    score_count = plans[0].candidate_indices.score_bin_count
    if any(
        plan.candidate_indices.score_bin_count != score_count
        or plan.mask_dependency_indices.score_bin_count != score_count
        or plan.proxy_grid_sha256 != plans[0].proxy_grid_sha256
        for plan in plans
    ):
        raise core.V0P6IncompleteError("sparse KAT plan grids disagree")
    required_fixture = {
        "artifact_type",
        "seed",
        "native_channel_count",
        "integration_count_per_epoch",
        "distance_integration_count",
        "template_count",
        "score_bin_count",
        "support_bin_count",
        "widths",
        "activity_subsets",
        "truth_proxy_carrier_hz",
        "tolerance_hz",
        "guard_bins",
        "proxy_grid_sha256",
        "factor_table_sha256",
        "distance_factor_table_sha256",
        "truth_factors_sha256",
        "native_epoch_sha256s",
        "mask_input_sha256s",
        "contains_circular_roll_seam",
        "seam_witness",
        "half_bin_tie_witness",
        "score_endpoint_witness",
        "closure_witness",
        "production_data_used",
    }
    if set(fixture_record) != required_fixture:
        raise core.V0P6IncompleteError("sparse KAT fixture is incomplete")
    native_count = core._strict_int(
        fixture_record["native_channel_count"], "fixture native-channel count"
    )
    seed = core._strict_int(fixture_record["seed"], "fixture seed")
    integration_count = core._strict_int(
        fixture_record["integration_count_per_epoch"],
        "fixture integration count",
    )
    distance_integration_count = core._strict_int(
        fixture_record["distance_integration_count"],
        "fixture distance-integration count",
    )
    fixture_templates = core._strict_int(
        fixture_record["template_count"], "fixture template count"
    )
    fixture_score_count = core._strict_int(
        fixture_record["score_bin_count"], "fixture score-bin count"
    )
    support_count = core._strict_int(
        fixture_record["support_bin_count"], "fixture support-bin count"
    )
    fixture_guard = core._strict_int(
        fixture_record["guard_bins"], "fixture mask guard"
    )
    try:
        fixture_widths = core._strict_widths(fixture_record["widths"])
        fixture_subsets = core.canonical_activity_subsets(
            fixture_record["activity_subsets"]
        )
        fixture_grid_sha256 = _frozen_sha256(
            fixture_record["proxy_grid_sha256"], "fixture proxy grid"
        )
        fixture_factor_table_sha256 = _frozen_sha256(
            fixture_record["factor_table_sha256"], "fixture factor table"
        )
        fixture_distance_factor_table_sha256 = _frozen_sha256(
            fixture_record["distance_factor_table_sha256"],
            "fixture distance-factor table",
        )
        fixture_truth_factors_sha256 = _frozen_sha256(
            fixture_record["truth_factors_sha256"],
            "fixture truth factors",
        )
        native_epoch_sha256s = tuple(
            _frozen_sha256(item, "fixture native epoch")
            for item in fixture_record["native_epoch_sha256s"]
        )
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "sparse KAT fixture dimensions are invalid"
        ) from error
    if (
        fixture_record["artifact_type"] != SPARSE_LOCAL_FIXTURE_ARTIFACT_TYPE
        or seed != _SPARSE_LOCAL_KAT_SEED
        or native_count != _SPARSE_LOCAL_KAT_NATIVE_CHANNEL_COUNT
        or integration_count != _SPARSE_LOCAL_KAT_INTEGRATION_COUNT_PER_EPOCH
        or distance_integration_count
        != _SPARSE_LOCAL_KAT_DISTANCE_INTEGRATION_COUNT
        or distance_integration_count
        != integration_count * SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or fixture_templates != _SPARSE_LOCAL_KAT_TEMPLATE_COUNT
        or fixture_templates != len(plans)
        or fixture_score_count != _SPARSE_LOCAL_KAT_SCORE_BIN_COUNT
        or fixture_score_count != score_count
        or support_count != _SPARSE_LOCAL_KAT_SUPPORT_BIN_COUNT
        or fixture_guard != core.M37_RFI_GUARD_Q_BINS
        or _finite_json_number(
            fixture_record["truth_proxy_carrier_hz"], "fixture truth carrier"
        )
        != _SPARSE_LOCAL_KAT_TRUTH_PROXY_CARRIER_HZ
        or _finite_json_number(
            fixture_record["tolerance_hz"], "fixture truth tolerance"
        )
        != 20.0
        or fixture_widths != SPARSE_LOCAL_REQUIRED_WIDTHS
        or fixture_subsets != SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
        or fixture_grid_sha256 != _SPARSE_LOCAL_KAT_PROXY_GRID_SHA256
        or fixture_grid_sha256 != plans[0].proxy_grid_sha256
        or fixture_truth_factors_sha256 != plans[0].truth_factors_sha256
        or len(native_epoch_sha256s) != SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or len(set(native_epoch_sha256s))
        != SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or fixture_factor_table_sha256
        == fixture_distance_factor_table_sha256
        or fixture_record["contains_circular_roll_seam"] is not True
        or fixture_record["production_data_used"] is not False
    ):
        raise core.V0P6IncompleteError("sparse KAT fixture contract changed")

    mask_input_records = fixture_record["mask_input_sha256s"]
    if not isinstance(mask_input_records, list):
        raise core.V0P6ContractError(
            "sparse KAT mask-input identities must be a list"
        )
    mask_input_keys: list[tuple[int, int]] = []
    mask_input_digests: list[str] = []
    for record in mask_input_records:
        if not isinstance(record, dict) or set(record) != {
            "template_index",
            "width_channels",
            "sha256",
        }:
            raise core.V0P6ContractError(
                "sparse KAT mask-input identity schema changed"
            )
        mask_input_keys.append(
            (
                core._strict_int(
                    record["template_index"], "mask-input template"
                ),
                core._strict_int(
                    record["width_channels"], "mask-input width"
                ),
            )
        )
        mask_input_digests.append(
            _frozen_sha256(record["sha256"], "mask-input vector")
        )
    expected_mask_input_keys = [
        (template, width)
        for template in range(len(plans))
        for width in SPARSE_LOCAL_REQUIRED_WIDTHS
    ]
    if (
        mask_input_keys != expected_mask_input_keys
        or len(set(mask_input_digests)) != len(expected_mask_input_keys)
    ):
        raise core.V0P6IncompleteError(
            "sparse KAT mask-input identity inventory changed"
        )

    seam = fixture_record["seam_witness"]
    tie = fixture_record["half_bin_tie_witness"]
    endpoint = fixture_record["score_endpoint_witness"]
    closure = fixture_record["closure_witness"]
    if not all(isinstance(item, dict) for item in (seam, tie, endpoint, closure)):
        raise core.V0P6ContractError("sparse KAT witnesses must be records")
    if (
        set(seam)
        != {
            "epoch_zero_based",
            "integration_index",
            "roll_shift",
            "seam_native_index",
            "score_index",
            "mapped_native_center",
            "width_channels",
            "filter_interval_half_open",
        }
        or set(tie)
        != {
            "score_index",
            "requested_native_coordinate",
            "mapped_native_index",
        }
        or set(endpoint)
        != {
            "template_index",
            "left_score_index",
            "right_score_index",
            "maximum_track_distances_hz",
        }
        or set(closure)
        != {
            "score_bin_count",
            "guard_bins",
            "input_indices",
            "expected_runs",
        }
    ):
        raise core.V0P6ContractError(
            "sparse KAT witness field inventory changed"
        )
    try:
        seam_epoch = core._strict_int(seam["epoch_zero_based"], "seam epoch")
        seam_integration = core._strict_int(
            seam["integration_index"], "seam integration"
        )
        seam_shift = core._strict_int(seam["roll_shift"], "seam roll shift")
        seam_index = core._strict_int(seam["seam_native_index"], "seam index")
        seam_q = core._strict_int(seam["score_index"], "seam score index")
        seam_center = core._strict_int(
            seam["mapped_native_center"], "seam mapped center"
        )
        seam_width = core._strict_int(seam["width_channels"], "seam width")
        seam_interval = tuple(
            core._strict_int(item, "seam filter endpoint")
            for item in seam["filter_interval_half_open"]
        )
        tie_q = core._strict_int(tie["score_index"], "tie score index")
        tie_mapped = core._strict_int(tie["mapped_native_index"], "tie mapping")
        tie_coordinate = _finite_json_number(
            tie["requested_native_coordinate"], "tie coordinate"
        )
        endpoint_template = core._strict_int(
            endpoint["template_index"], "endpoint template"
        )
        endpoint_left = core._strict_int(
            endpoint["left_score_index"], "left endpoint"
        )
        endpoint_right = core._strict_int(
            endpoint["right_score_index"], "right endpoint"
        )
        endpoint_distances = tuple(
            _finite_json_number(item, "endpoint distance")
            for item in endpoint["maximum_track_distances_hz"]
        )
        closure_count = core._strict_int(
            closure["score_bin_count"], "closure score-bin count"
        )
        closure_guard = core._strict_int(closure["guard_bins"], "closure guard")
        closure_input = make_local_score_index_set(
            closure_count, closure["input_indices"]
        )
        closure_expected_runs = tuple(
            tuple(core._strict_int(value, "closure run endpoint") for value in run)
            for run in closure["expected_runs"]
        )
    except (KeyError, TypeError) as error:
        raise core.V0P6ContractError("sparse KAT witness schema is incomplete") from error
    endpoint_plan = plans[endpoint_template] if 0 <= endpoint_template < len(plans) else None
    endpoint_distance_by_q = (
        {
            int(q_index): float(distance)
            for q_index, distance in zip(
                endpoint_plan.candidate_indices.indices,
                endpoint_plan.maximum_track_distances_hz,
                strict=True,
            )
        }
        if endpoint_plan is not None
        else {}
    )
    observed_endpoint_distances = (
        endpoint_distance_by_q.get(endpoint_left),
        endpoint_distance_by_q.get(endpoint_right),
    )
    if (
        not 0 <= seam_epoch < SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or not 0 <= seam_integration < integration_count
        or seam_shift != seam_index
        or not 0 <= seam_q < score_count
        or not 0 <= seam_center < native_count
        or seam_width != max(SPARSE_LOCAL_REQUIRED_WIDTHS)
        or len(seam_interval) != 2
        or seam_interval
        != (
            seam_center - seam_width // 2,
            seam_center + seam_width // 2 + 1,
        )
        or seam_interval[0] < 0
        or seam_interval[1] > native_count
        or not seam_interval[0] <= seam_index - 1 < seam_index < seam_interval[1]
        or not seam_interval[0] <= seam_center < seam_interval[1]
        or seam_q != score_count // 2
        or tie_q != score_count // 2
        or tie_coordinate != 500.5
        or tie_coordinate - math.floor(tie_coordinate) != 0.5
        or tie_mapped != round(tie_coordinate)
        or tie_mapped % 2 != 0
        or not 0 <= endpoint_template < len(plans)
        or endpoint_left != 0
        or endpoint_right != score_count - 1
        or endpoint_distances != (20.0, 20.0)
        or observed_endpoint_distances != endpoint_distances
        or endpoint_left
        not in plans[endpoint_template].candidate_indices.indices
        or endpoint_right
        not in plans[endpoint_template].candidate_indices.indices
        or closure_count != score_count
        or closure_guard != core.M37_RFI_GUARD_Q_BINS
        or tuple(int(item) for item in closure_input.indices)
        != (0, 9, 10, 20, 39, 40)
        or closure_expected_runs != ((0, score_count),)
        or clipped_score_index_closure(
            closure_input, guard_bins=closure_guard
        ).runs
        != closure_expected_runs
    ):
        raise core.V0P6IncompleteError("sparse KAT witness contract changed")
    covered = SPARSE_LOCAL_REQUIRED_COVERAGE
    gather_keys = tuple(
        (template, width, epoch)
        for template in range(len(plans))
        for width in SPARSE_LOCAL_REQUIRED_WIDTHS
        for epoch in range(SPARSE_LOCAL_REQUIRED_EPOCH_COUNT)
    )
    isolated_mask_keys = tuple(
        (template, width)
        for template in range(len(plans))
        for width in SPARSE_LOCAL_REQUIRED_WIDTHS
    )
    mask_keys = tuple(range(len(plans)))
    score_keys = tuple(
        (template, width, subset)
        for template in range(len(plans))
        for width in SPARSE_LOCAL_REQUIRED_WIDTHS
        for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
    )
    _require_exact_mapping_keys(
        dense_gathers, gather_keys, _canonical_gather_key, "dense gather"
    )
    _require_exact_mapping_keys(
        local_gathers, gather_keys, _canonical_gather_key, "local gather"
    )
    _require_exact_mapping_keys(
        dense_isolated_masks,
        isolated_mask_keys,
        _canonical_width_mask_key,
        "dense isolated-mask",
    )
    _require_exact_mapping_keys(
        local_isolated_masks,
        isolated_mask_keys,
        _canonical_width_mask_key,
        "local isolated-mask",
    )
    _require_exact_mapping_keys(
        dense_masks,
        mask_keys,
        lambda key: core._strict_int(key, "mask template"),
        "dense final-mask",
    )
    _require_exact_mapping_keys(
        local_masks,
        mask_keys,
        lambda key: core._strict_int(key, "mask template"),
        "local final-mask",
    )
    _require_exact_mapping_keys(
        dense_scores, score_keys, _canonical_score_key, "dense score"
    )
    _require_exact_mapping_keys(
        local_scores, score_keys, _canonical_score_key, "local score"
    )

    groups = (
        (dense_gathers, local_gathers, gather_keys, "gather"),
        (
            dense_isolated_masks,
            local_isolated_masks,
            isolated_mask_keys,
            "isolated-mask",
        ),
        (dense_masks, local_masks, mask_keys, "mask"),
        (dense_scores, local_scores, score_keys, "score"),
    )
    observed_payload_hashes: dict[str, set[str]] = {
        label: set() for _, _, _, label in groups
    }
    for dense, local, keys, label in groups:
        for key in keys:
            left = dense[key]
            right = local[key]
            if not isinstance(left, np.ndarray) or not isinstance(
                right, np.ndarray
            ):
                raise core.V0P6ContractError(
                    f"sparse KAT {label} arrays must be explicit ndarrays"
                )
            left_array = np.asarray(left)
            right_array = np.asarray(right)
            template = key[0] if isinstance(key, tuple) else key
            if label == "gather":
                expected_shape = (
                    plans[template].mask_dependency_indices.indices.size,
                )
            elif label == "isolated-mask":
                expected_shape = (
                    SPARSE_LOCAL_REQUIRED_EPOCH_COUNT,
                    plans[template].mask_dependency_indices.indices.size,
                )
            elif label == "mask":
                expected_shape = (
                    SPARSE_LOCAL_REQUIRED_EPOCH_COUNT,
                    plans[template].candidate_indices.indices.size,
                )
            else:
                expected_shape = (
                    plans[template].candidate_indices.indices.size,
                )
            expected_dtype = (
                np.dtype(bool)
                if label in {"isolated-mask", "mask"}
                else np.dtype("<f4")
            )
            if (
                left_array.dtype != right_array.dtype
                or left_array.dtype != expected_dtype
                or left_array.shape != right_array.shape
                or left_array.shape != expected_shape
                or not left_array.flags.c_contiguous
                or not right_array.flags.c_contiguous
                or (
                    label == "gather"
                    and (
                        not np.all(np.isfinite(left_array))
                        or not np.all(np.isfinite(right_array))
                        or np.all(left_array == left_array.flat[0])
                    )
                )
                or (
                    label == "score"
                    and (
                        np.any(np.isnan(left_array))
                        or np.any(np.isnan(right_array))
                        or np.any(np.isposinf(left_array))
                        or np.any(np.isposinf(right_array))
                        or not np.any(np.isfinite(left_array))
                        or not np.any(np.isneginf(left_array))
                    )
                )
                or (
                    label in {"isolated-mask", "mask"}
                    and (
                        not np.any(left_array)
                        or not np.any(~left_array)
                    )
                )
                or left_array.tobytes() != right_array.tobytes()
            ):
                raise core.V0P6IncompleteError(
                    f"sparse KAT {label} bytes differ from dense reference"
                )
            observed_payload_hashes[label].add(
                _sha256_bytes(memoryview(left_array).cast("B"))
            )
    if any(
        len(observed_payload_hashes[label]) != len(keys)
        for _, _, keys, label in groups
    ):
        raise core.V0P6IncompleteError(
            "sparse KAT contains duplicated relabelled array payloads"
        )
    dense_gather_digest = _keyed_array_inventory_sha256(
        dense_gathers, gather_keys
    )
    local_gather_digest = _keyed_array_inventory_sha256(
        local_gathers, gather_keys
    )
    dense_isolated_mask_digest = _keyed_array_inventory_sha256(
        dense_isolated_masks, isolated_mask_keys
    )
    local_isolated_mask_digest = _keyed_array_inventory_sha256(
        local_isolated_masks, isolated_mask_keys
    )
    dense_mask_digest = _keyed_array_inventory_sha256(dense_masks, mask_keys)
    local_mask_digest = _keyed_array_inventory_sha256(local_masks, mask_keys)
    dense_score_digest = _keyed_array_inventory_sha256(
        dense_scores, score_keys
    )
    local_score_digest = _keyed_array_inventory_sha256(
        local_scores, score_keys
    )
    plan_inventory = _sha256_bytes(
        core.canonical_json_bytes([plan.as_record() for plan in plans])
    )
    partial = SparseLocalReferenceKATReceipt(
        status=SPARSE_LOCAL_REFERENCE_STATUS,
        fixture_sha256=_sha256_bytes(core.canonical_json_bytes(fixture_record)),
        plan_inventory_sha256=plan_inventory,
        covered_contracts=covered,
        template_count=len(plans),
        score_bin_count=score_count,
        epoch_count=SPARSE_LOCAL_REQUIRED_EPOCH_COUNT,
        spectral_widths=SPARSE_LOCAL_REQUIRED_WIDTHS,
        activity_subsets=SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
        gather_array_count=len(gather_keys),
        isolated_mask_array_count=len(isolated_mask_keys),
        mask_array_count=len(mask_keys),
        score_array_count=len(score_keys),
        dense_gathers_sha256=dense_gather_digest,
        local_gathers_sha256=local_gather_digest,
        dense_isolated_masks_sha256=dense_isolated_mask_digest,
        local_isolated_masks_sha256=local_isolated_mask_digest,
        dense_masks_sha256=dense_mask_digest,
        local_masks_sha256=local_mask_digest,
        dense_scores_sha256=dense_score_digest,
        local_scores_sha256=local_score_digest,
        gather_bits_equal=True,
        mask_bytes_equal=True,
        score_bits_equal=True,
        production_equivalence_claimed=False,
        global_retention_equivalence_proven=False,
        receiver_alias_equivalence_proven=False,
        off_disposition_equivalence_proven=False,
        rank_p_equivalence_proven=False,
        production_receipt_ancestry_proven=False,
        production_feasibility_gate_changed=False,
        receipt_sha256="",
    )
    receipt = replace(
        partial,
        receipt_sha256=_sha256_bytes(
            core.canonical_json_bytes(partial.as_record(include_identity=False))
        ),
    )
    validate_sparse_local_reference_kat_receipt(receipt)
    return receipt


def validate_sparse_local_reference_kat_receipt(
    receipt: SparseLocalReferenceKATReceipt,
) -> None:
    if not isinstance(receipt, SparseLocalReferenceKATReceipt):
        raise core.V0P6ContractError("sparse KAT receipt has an invalid type")
    if (
        receipt.status != SPARSE_LOCAL_REFERENCE_STATUS
        or receipt.covered_contracts != SPARSE_LOCAL_REQUIRED_COVERAGE
        or receipt.gather_bits_equal is not True
        or receipt.mask_bytes_equal is not True
        or receipt.score_bits_equal is not True
        or receipt.production_equivalence_claimed is not False
        or receipt.global_retention_equivalence_proven is not False
        or receipt.receiver_alias_equivalence_proven is not False
        or receipt.off_disposition_equivalence_proven is not False
        or receipt.rank_p_equivalence_proven is not False
        or receipt.production_receipt_ancestry_proven is not False
        or receipt.production_feasibility_gate_changed is not False
    ):
        raise core.V0P6IncompleteError("sparse KAT claim boundary changed")
    template_count = core._strict_int(receipt.template_count, "KAT template count")
    score_count = core._strict_int(receipt.score_bin_count, "KAT score-bin count")
    epoch_count = core._strict_int(receipt.epoch_count, "KAT epoch count")
    gather_count = core._strict_int(
        receipt.gather_array_count, "KAT gather-array count"
    )
    isolated_mask_count = core._strict_int(
        receipt.isolated_mask_array_count,
        "KAT isolated-mask-array count",
    )
    mask_count = core._strict_int(receipt.mask_array_count, "KAT mask-array count")
    score_array_count = core._strict_int(
        receipt.score_array_count, "KAT score-array count"
    )
    try:
        receipt_widths = core._strict_widths(receipt.spectral_widths)
        receipt_subsets = core.canonical_activity_subsets(
            receipt.activity_subsets
        )
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "sparse KAT receipt label inventory is invalid"
        ) from error
    if (
        template_count != _SPARSE_LOCAL_KAT_TEMPLATE_COUNT
        or score_count != _SPARSE_LOCAL_KAT_SCORE_BIN_COUNT
        or epoch_count != SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or receipt_widths != SPARSE_LOCAL_REQUIRED_WIDTHS
        or receipt_subsets != SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
        or gather_count
        != template_count
        * len(SPARSE_LOCAL_REQUIRED_WIDTHS)
        * SPARSE_LOCAL_REQUIRED_EPOCH_COUNT
        or isolated_mask_count
        != template_count * len(SPARSE_LOCAL_REQUIRED_WIDTHS)
        or mask_count != template_count
        or score_array_count
        != template_count
        * len(SPARSE_LOCAL_REQUIRED_WIDTHS)
        * len(SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS)
    ):
        raise core.V0P6IncompleteError("sparse KAT dimension inventory changed")
    for name in (
        "fixture_sha256",
        "plan_inventory_sha256",
        "dense_gathers_sha256",
        "local_gathers_sha256",
        "dense_isolated_masks_sha256",
        "local_isolated_masks_sha256",
        "dense_masks_sha256",
        "local_masks_sha256",
        "dense_scores_sha256",
        "local_scores_sha256",
        "receipt_sha256",
    ):
        _frozen_sha256(getattr(receipt, name), name.replace("_", " "))
    if (
        receipt.dense_gathers_sha256 != receipt.local_gathers_sha256
        or receipt.dense_isolated_masks_sha256
        != receipt.local_isolated_masks_sha256
        or receipt.dense_masks_sha256 != receipt.local_masks_sha256
        or receipt.dense_scores_sha256 != receipt.local_scores_sha256
    ):
        raise core.V0P6IncompleteError("sparse KAT equality identities changed")
    expected = _sha256_bytes(
        core.canonical_json_bytes(receipt.as_record(include_identity=False))
    )
    if expected != receipt.receipt_sha256:
        raise core.V0P6IncompleteError("sparse KAT receipt identity changed")
    if (
        receipt.fixture_sha256 != SPARSE_LOCAL_KAT_FIXTURE_SHA256
        or receipt.plan_inventory_sha256
        != SPARSE_LOCAL_KAT_PLAN_INVENTORY_SHA256
        or receipt.dense_gathers_sha256
        != SPARSE_LOCAL_KAT_GATHERS_SHA256
        or receipt.dense_isolated_masks_sha256
        != SPARSE_LOCAL_KAT_ISOLATED_MASKS_SHA256
        or receipt.dense_masks_sha256 != SPARSE_LOCAL_KAT_MASKS_SHA256
        or receipt.dense_scores_sha256 != SPARSE_LOCAL_KAT_SCORES_SHA256
        or receipt.receipt_sha256 != SPARSE_LOCAL_KAT_RECEIPT_SHA256
    ):
        raise core.V0P6IncompleteError(
            "sparse KAT receipt is not the pinned known answer"
        )
