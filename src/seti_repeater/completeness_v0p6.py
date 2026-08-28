"""Prospective, provisional completeness machinery for detector v0.6.

This module freezes an implementation candidate for a future M37 v0.6
preregistration.  The constants are *prospective and provisional* until that
preregistration is published; they are not represented as historical M37
facts.  In particular, an injection is added to normalized native float32
spectra before any native boxcar or proxy-carrier gather.  No q-domain signal
injection API is provided.

The orchestration is data-source agnostic.  A production adapter must rebuild
the two-pass masks from each injected native product, run the exact operational
detector at the already-frozen final threshold, and finish the exact physical
disposition passes.  This module enforces receipts for that ordering and keeps
an exhaustive, fail-closed trial ledger; it does not open telescope files.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
import operator
from typing import Any, Iterable, Mapping, Protocol, Sequence

import numpy as np

from . import search_v0p6 as core
from .spectral import normalized_boxcar
from .search_v0p6 import (
    FILTER_COORDINATE,
    M37_ACTIVITY_SUBSETS,
    M37_BANK_SHA256,
    M37_CALIBRATION_EXECUTION_ENGINE,
    M37_DIRECTION,
    M37_EXPERIMENT_CONTRACT_SHA256,
    M37_FACTOR_BASIS_LABELS_SHA256,
    M37_FACTOR_BASIS_SHA256,
    M37_FACTOR_ROW_SELECTION_SHA256S,
    M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES,
    M37_MAXIMUM_RECORDS_PER_WINDOW,
    M37_RFI_GUARD_Q_BINS,
    M37_RFI_OTHER_EPOCHS_BELOW_SNR,
    M37_RFI_STRONG_SNR,
    M37_SCAN_INVENTORY_SHA256,
    M37_SCORE_HALF_BINS,
    M37_SCIENTIFIC_P_CEILING,
    M37_SCRAMBLE_COUNT,
    M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
    M37_SCRAMBLE_TABLE_SHA256S,
    M37_SPECTRAL_WIDTHS,
    M37_TEMPLATE_COUNT,
    M37_THRESHOLD_QUANTILE,
    M37_THRESHOLD_REFERENCE_FLOOR_SNR,
    M37_WINDOW_IDS,
    FactorBasis,
    NativeFrequencyGeometry,
    TemplateFactorTable,
    ThresholdCertificate,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6CoverageError,
    V0P6IncompleteError,
    canonical_json_bytes,
    factor_table_sha256,
    make_line_template_bank,
    make_m37_proxy_carrier_grid,
    template_factors_from_basis,
    validate_factor_basis,
    validate_template_factor_table,
    validate_threshold_certificate,
)


# Prospective/provisional values pending publication of an M37 v0.6
# preregistration.  These values must not be described as retrospectively
# preregistered or as results from telescope data.
M37_COMPLETENESS_STATUS = (
    "prospective_provisional_pending_preregistration_publication"
)
M37_COMPLETENESS_SNR_GRID = (
    4.0,
    5.0,
    6.0,
    7.0,
    8.0,
    10.0,
    12.0,
    16.0,
    20.0,
    24.0,
    32.0,
    40.0,
)
M37_COMPLETENESS_TRUTHS_PER_LEVEL = 512
M37_COMPLETENESS_MASTER_SEED = 372_120_260_827
M37_COMPLETENESS_BACKGROUND_WINDOW = "m37_1412p5"
M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ = 20.0
M37_COMPLETENESS_WILSON_Z_95 = 1.959963984540054
M37_COMPLETENESS_CARRIER_MARGIN_BINS = 256
M37_COMPLETENESS_CARRIER_STEP = 104_729
M37_COMPLETENESS_RADIAL_STRATA = 16
M37_COMPLETENESS_PHASE_STRATA = 32
M37_COMPLETENESS_ALLOCATION_VERSION = (
    "m37-v0.6-prospective-completeness-continuous-disk-allocation-v2"
)
M37_COMPLETENESS_SEED_DERIVATION = (
    "uint64-big-endian-first-8-bytes-of-sha256-canonical-json"
)
M37_COMPLETENESS_JITTER_DERIVATION = (
    "top-53-bits-of-sha256-canonical-json-divided-by-2**53"
)
M37_COMPLETENESS_INJECTION_MODEL = (
    "native-nearest-channel-odd-width-L2-boxcar-match-v1"
)
M37_COMPLETENESS_INJECTION_STAGE = (
    "normalized-native-float32-before-native-boxcar-before-q-gather"
)
M37_COMPLETENESS_NOISE_SELECTION = (
    "per-ON-scan-positive-native-channel-np.roll-from-trial-noise-seed-v1"
)
M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT = (
    "trusted-runner-one-shot-normalized-product-iterator; one product "
    "validated and released at a time; current roll and immutable scan copy "
    "both charged; preloaded three-product inventories forbidden-v1"
)
M37_COMPLETENESS_MASK_WORKING_SET_ACCOUNTING_CONTRACT = (
    "ledger-owned retained background+injected native arrays, shared "
    "truth-factor/basis/table arrays, proxy-grid owner arrays + exactly one "
    "caller-supplied cache payload, or one template's eight epoch products "
    "and mask, + conservative factory scratch; trusted runner releases "
    "every prior payload-v2"
)
M37_COMPLETENESS_SYNTHETIC_MASK_WORKING_SET_ACCOUNTING_CONTRACT = (
    "synthetic-known-answer owns only retained background+injected native "
    "arrays; no production cache/mask working-set claim-v1"
)

# Exhaustion/capacity failures invalidate a run.  No cap permits truncation.
M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL = 536_870_912
M37_COMPLETENESS_M37_BACKGROUND_PROJECTED_PEAK_BYTES = 418_203_096
M37_COMPLETENESS_PRELOADED_THREE_SOURCE_ROLL_BYTES = 550_168_200
M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL = 100_000
M37_COMPLETENESS_MAXIMUM_TRIAL_RECORD_CANONICAL_BYTES = 16_384
M37_COMPLETENESS_MAXIMUM_TOTAL_CANONICAL_BYTES = 128_000_000
M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS = (
    M37_TEMPLATE_COUNT * len(M37_SPECTRAL_WIDTHS)
)
M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS = M37_TEMPLATE_COUNT
M37_COMPLETENESS_MAXIMUM_DISPOSITION_EVIDENCE_BYTES = (
    M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
)
M37_COMPLETENESS_MAXIMUM_DETECTOR_RECORDS = M37_MAXIMUM_RECORDS_PER_WINDOW
M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL = (
    M37_TEMPLATE_COUNT
    * len(M37_SPECTRAL_WIDTHS)
    * len(M37_ACTIVITY_SUBSETS)
    * (2 * M37_SCORE_HALF_BINS + 1)
)
M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL = (
    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
    * M37_COMPLETENESS_TRUTHS_PER_LEVEL
    * len(M37_COMPLETENESS_SNR_GRID)
)
M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS = (
    "mandatory-full-replay-benchmark-not-yet-passed"
)

# Filled with literal known-answer digests below after the allocation payload
# was independently generated.  Validators always require these exact values.
M37_COMPLETENESS_ALLOCATION_CONTRACT_SHA256 = (
    "80a287eba2c202e575b13ac100d519ab0e220f519a5dfdd881b088189ac4dba7"
)
M37_COMPLETENESS_TRUTH_INVENTORY_SHA256 = (
    "0c96a4f1b0d09be3e40048a85cf0fbbd48b3ad1352c7224bfef25523cae42f60"
)
M37_COMPLETENESS_TRIAL_INVENTORY_SHA256 = (
    "c15e656295d3c40f179a2df58e0eff2b6d9129b2550311c3a7c5825579f3176a"
)
M37_COMPLETENESS_PLAN_SHA256 = (
    "ea83e1c588b78e02e4378036b122890cf286d63d9deb7f45210e7fe8a0ec92dc"
)


def _strict_int(value: Any, label: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise V0P6ContractError(f"{label} must be an integer, not boolean")
    try:
        return int(operator.index(value))
    except TypeError as error:
        raise V0P6ContractError(f"{label} must be an exact integer") from error


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256 = _sha256(
    {
        "artifact_type": "m37-completeness-source-streaming-contract-v1",
        "contract": M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT,
    }
)


def _frozen_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise V0P6ContractError(
            f"{label} must be an exact lowercase SHA-256 string"
        )
    digest = value
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise V0P6ContractError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _float32_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values, dtype="<f4")
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def _float64_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values, dtype="<f8")
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def _seed64(*parts: Any) -> int:
    digest = hashlib.sha256(canonical_json_bytes(list(parts))).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _jitter01(*parts: Any) -> float:
    """Return a dependency-free deterministic binary64 value in ``[0, 1)``."""
    digest = hashlib.sha256(canonical_json_bytes(list(parts))).digest()
    mantissa = int.from_bytes(digest[:8], byteorder="big", signed=False) >> 11
    return mantissa / float(1 << 53)


def _nearest_line_assignment(
    coefficient_x: float,
    coefficient_y: float,
) -> tuple[int, int, float, float]:
    """Return canonical nearest-line template data for a disk truth.

    Exact midpoint ties go to the larger signed line index, matching the
    frozen bank-preflight rule.  The final clamp is normative at the two
    disk-edge strips.
    """
    projection = (
        float(coefficient_x) * M37_DIRECTION[0]
        + float(coefficient_y) * M37_DIRECTION[1]
    )
    half = (M37_TEMPLATE_COUNT - 1) // 2
    line_index = math.floor(M37_TEMPLATE_COUNT * projection / 2.0 + 0.5)
    line_index = min(half, max(-half, line_index))
    template_index = 0 if line_index == 0 else (
        2 * line_index - 1 if line_index > 0 else -2 * line_index
    )
    return (
        template_index,
        line_index,
        2.0 * line_index / M37_TEMPLATE_COUNT,
        projection,
    )


def _allocation_contract_payload() -> dict[str, Any]:
    return {
        "status": M37_COMPLETENESS_STATUS,
        "allocation_version": M37_COMPLETENESS_ALLOCATION_VERSION,
        "snr_grid": list(M37_COMPLETENESS_SNR_GRID),
        "truths_per_level": M37_COMPLETENESS_TRUTHS_PER_LEVEL,
        "master_seed": M37_COMPLETENESS_MASTER_SEED,
        "seed_derivation": M37_COMPLETENESS_SEED_DERIVATION,
        "background_window": M37_COMPLETENESS_BACKGROUND_WINDOW,
        "template_count": M37_TEMPLATE_COUNT,
        "template_bank_sha256": M37_BANK_SHA256,
        "spectral_widths": list(M37_SPECTRAL_WIDTHS),
        "activity_subsets": [list(item) for item in M37_ACTIVITY_SUBSETS],
        "carrier_score_bin_count": 2 * M37_SCORE_HALF_BINS + 1,
        "carrier_margin_bins": M37_COMPLETENESS_CARRIER_MARGIN_BINS,
        "carrier_step": M37_COMPLETENESS_CARRIER_STEP,
        "continuous_truth_allocation": {
            "domain": "coefficient_x**2 + coefficient_y**2 <= 1",
            "radial_strata": M37_COMPLETENESS_RADIAL_STRATA,
            "phase_strata": M37_COMPLETENESS_PHASE_STRATA,
            "one_truth_per_radial_phase_cell": True,
            "radial_coordinate": (
                "sqrt((radial_stratum+jitter_r)/radial_strata)"
            ),
            "phase_coordinate_cycles": (
                "(phase_stratum+jitter_phase)/phase_strata"
            ),
            "jitter_derivation": M37_COMPLETENESS_JITTER_DERIVATION,
            "nearest_template_assignment": (
                "projection-on-M37_DIRECTION; floor(93*projection/2+0.5); "
                "clamp-to-[-46,46]"
            ),
            "nearest_template_midpoint_tie_rule": (
                "larger-signed-line-index"
            ),
            "truth_factors": (
                "FactorBasis.baseline + FactorBasis.orbital @ "
                "[coefficient_x,coefficient_y]"
            ),
            "nuisance_latin_rotation": {
                "combo": "(phase_stratum + 5*radial_stratum) % 32",
                "spectral_width_index": "combo % 8",
                "activity_subset_index": "combo // 8",
                "contract": (
                    "all 32 width/activity pairs once per radial stratum; "
                    "each pair in 16 distinct phase strata"
                ),
            },
        },
        "truth_track_contract": "Y_i(u,q) = q * F_u_i",
        "injection_model": M37_COMPLETENESS_INJECTION_MODEL,
        "injection_stage": M37_COMPLETENESS_INJECTION_STAGE,
        "noise_selection": {
            "contract": M37_COMPLETENESS_NOISE_SELECTION,
            "source": (
                "factory-attested-m37_1412p5-normalized-ON-products"
            ),
            "scan_labels": ["epoch1_on", "epoch2_on", "epoch3_on"],
            "minimum_shift_channels": M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
            "shift_seed": (
                "sha256(master-seed, contract-label, trial-noise-seed, "
                "trial-id, epoch, normalized-source-product-sha256)"
            ),
            "shift_interval": (
                "[minimum_shift, channel_count-minimum_shift)"
            ),
            "caller_supplied_selected_background_permitted": False,
        },
        "filter_coordinate": FILTER_COORDINATE,
        "recovery_tolerance_hz": M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
        "wilson_z_95": M37_COMPLETENESS_WILSON_Z_95,
        "threshold_summary_rule": (
            "first-tested-grid-level-at-or-above-target; no interpolation"
        ),
        "capacity_contract": {
            "maximum_live_native_bytes_per_trial": (
                M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
            ),
            "maximum_injection_writes_per_trial": (
                M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL
            ),
            "maximum_trial_record_canonical_bytes": (
                M37_COMPLETENESS_MAXIMUM_TRIAL_RECORD_CANONICAL_BYTES
            ),
            "maximum_total_canonical_bytes": (
                M37_COMPLETENESS_MAXIMUM_TOTAL_CANONICAL_BYTES
            ),
            "expected_mask_source_products": (
                M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS
            ),
            "expected_template_masks": (
                M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS
            ),
            "maximum_detector_records": (
                M37_COMPLETENESS_MAXIMUM_DETECTOR_RECORDS
            ),
            "maximum_disposition_evidence_bytes": (
                M37_COMPLETENESS_MAXIMUM_DISPOSITION_EVIDENCE_BYTES
            ),
            "full_replay_score_cells_per_trial": (
                M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
            ),
            "full_replay_score_cells_total": (
                M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL
            ),
            "production_feasibility_status": (
                M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS
            ),
            "production_gate": (
                "bit-identical sparse/local replay with frozen reference KAT "
                "or passed mandatory full-replay benchmark"
            ),
            "truncation_permitted": False,
        },
    }


@dataclass(frozen=True)
class CompletenessTruth:
    """One preallocated physical truth, reused at every S/N grid level."""

    truth_ordinal: int
    truth_id: str
    window_id: str
    template_index: int
    line_index: int
    line_coefficient: float
    coefficient_x: float
    coefficient_y: float
    direction_projection: float
    projected_scale: float
    phase_cycles: float
    radial_stratum_index: int
    phase_stratum_index: int
    spectral_width_index: int
    spectral_width_channels: int
    activity_subset_index: int
    active_epochs_zero_based: tuple[int, ...]
    proxy_carrier_index: int
    proxy_carrier_lattice_index: int
    proxy_carrier_hz: float
    proxy_carrier_mhz: float
    truth_seed: int

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "truth_ordinal": self.truth_ordinal,
            "window_id": self.window_id,
            "template_index": self.template_index,
            "line_index": self.line_index,
            "line_coefficient": self.line_coefficient,
            "coefficient_x": self.coefficient_x,
            "coefficient_y": self.coefficient_y,
            "direction_projection": self.direction_projection,
            "projected_scale": self.projected_scale,
            "phase_cycles": self.phase_cycles,
            "radial_stratum_index": self.radial_stratum_index,
            "phase_stratum_index": self.phase_stratum_index,
            "spectral_width_index": self.spectral_width_index,
            "spectral_width_channels": self.spectral_width_channels,
            "activity_subset_index": self.activity_subset_index,
            "active_epochs_zero_based": list(self.active_epochs_zero_based),
            "proxy_carrier_index": self.proxy_carrier_index,
            "proxy_carrier_lattice_index": self.proxy_carrier_lattice_index,
            "proxy_carrier_hz": self.proxy_carrier_hz,
            "proxy_carrier_mhz": self.proxy_carrier_mhz,
            "truth_seed": self.truth_seed,
            "truth_track_contract": "Y_i(u,q) = q * F_u_i",
        }
        if include_identity:
            record["truth_id"] = self.truth_id
        return record


def _validate_completeness_truth(truth: CompletenessTruth) -> None:
    if not isinstance(truth, CompletenessTruth):
        raise V0P6ContractError("completeness truth has an invalid type")
    if truth.truth_id != _sha256(truth.as_record(include_identity=False)):
        raise V0P6IncompleteError("completeness truth identity changed")
    ordinal = _strict_int(truth.truth_ordinal, "truth ordinal")
    radial_stratum = _strict_int(
        truth.radial_stratum_index, "truth radial stratum"
    )
    phase_stratum = _strict_int(
        truth.phase_stratum_index, "truth phase stratum"
    )
    if (
        not 0 <= ordinal < M37_COMPLETENESS_TRUTHS_PER_LEVEL
        or not 0 <= radial_stratum < M37_COMPLETENESS_RADIAL_STRATA
        or not 0 <= phase_stratum < M37_COMPLETENESS_PHASE_STRATA
        or ordinal
        != radial_stratum * M37_COMPLETENESS_PHASE_STRATA + phase_stratum
    ):
        raise V0P6ContractError("truth disk-stratum identity is invalid")
    nuisance_combo = (
        phase_stratum + 5 * radial_stratum
    ) % (len(M37_SPECTRAL_WIDTHS) * len(M37_ACTIVITY_SUBSETS))
    expected_width_index = nuisance_combo % len(M37_SPECTRAL_WIDTHS)
    expected_activity_index = nuisance_combo // len(M37_SPECTRAL_WIDTHS)
    if (
        _strict_int(truth.spectral_width_index, "truth width index")
        != expected_width_index
        or truth.spectral_width_channels
        != M37_SPECTRAL_WIDTHS[expected_width_index]
        or _strict_int(truth.activity_subset_index, "truth activity index")
        != expected_activity_index
        or truth.active_epochs_zero_based
        != M37_ACTIVITY_SUBSETS[expected_activity_index]
    ):
        raise V0P6IncompleteError("truth nuisance Latin allocation changed")
    values = (
        truth.line_coefficient,
        truth.coefficient_x,
        truth.coefficient_y,
        truth.direction_projection,
        truth.projected_scale,
        truth.phase_cycles,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise V0P6ContractError("truth coefficient geometry is non-finite")
    radius_squared = (
        truth.coefficient_x * truth.coefficient_x
        + truth.coefficient_y * truth.coefficient_y
    )
    if not 0.0 <= radius_squared <= 1.0 + 4e-15:
        raise V0P6ContractError("truth coefficient is outside the unit disk")
    if abs(math.sqrt(radius_squared) - truth.projected_scale) > 2e-15:
        raise V0P6IncompleteError("truth projected scale changed")
    lower_area = radial_stratum / M37_COMPLETENESS_RADIAL_STRATA
    upper_area = (radial_stratum + 1) / M37_COMPLETENESS_RADIAL_STRATA
    if not lower_area <= truth.projected_scale**2 < upper_area:
        raise V0P6IncompleteError("truth left its uniform-area radial stratum")
    lower_phase = phase_stratum / M37_COMPLETENESS_PHASE_STRATA
    upper_phase = (phase_stratum + 1) / M37_COMPLETENESS_PHASE_STRATA
    if not lower_phase <= truth.phase_cycles < upper_phase:
        raise V0P6IncompleteError("truth left its phase stratum")
    observed_phase = math.atan2(
        truth.coefficient_y, truth.coefficient_x
    ) / (2.0 * math.pi) % 1.0
    phase_error = abs(observed_phase - truth.phase_cycles)
    phase_error = min(phase_error, 1.0 - phase_error)
    if phase_error > 2e-15:
        raise V0P6IncompleteError("truth phase and Cartesian coefficient disagree")
    assignment = _nearest_line_assignment(
        truth.coefficient_x, truth.coefficient_y
    )
    if (
        truth.template_index,
        truth.line_index,
        truth.line_coefficient,
        truth.direction_projection,
    ) != assignment:
        raise V0P6IncompleteError("truth nearest-line association changed")


@dataclass(frozen=True)
class CompletenessPlan:
    """Immutable prospective M37 allocation, independent of a final threshold."""

    status: str
    allocation_contract_sha256: str
    truth_inventory_sha256: str
    trial_inventory_sha256: str
    plan_sha256: str
    truths: tuple[CompletenessTruth, ...] = field(repr=False)

    @property
    def expected_trial_count(self) -> int:
        return len(self.truths) * len(M37_COMPLETENESS_SNR_GRID)

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allocation_contract_sha256": self.allocation_contract_sha256,
            "truth_inventory_sha256": self.truth_inventory_sha256,
            "trial_inventory_sha256": self.trial_inventory_sha256,
            "truth_count_per_snr_level": len(self.truths),
            "snr_grid": list(M37_COMPLETENESS_SNR_GRID),
            "expected_trial_count": self.expected_trial_count,
            "plan_sha256": self.plan_sha256,
        }


@dataclass(frozen=True)
class CompletenessTrial:
    """One truth/SNR/noise realization in the exhaustive trial inventory."""

    trial_id: str
    level_index: int
    ideal_single_epoch_snr: float
    noise_seed: int
    truth: CompletenessTruth

    def as_record(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "level_index": self.level_index,
            "ideal_single_epoch_snr": self.ideal_single_epoch_snr,
            "noise_seed": self.noise_seed,
            "truth_id": self.truth.truth_id,
            "truth_ordinal": self.truth.truth_ordinal,
        }


def _make_truths() -> tuple[CompletenessTruth, ...]:
    bank = make_line_template_bank()
    grid = make_m37_proxy_carrier_grid(M37_COMPLETENESS_BACKGROUND_WINDOW)
    score_count = grid.score_bin_count
    margin = M37_COMPLETENESS_CARRIER_MARGIN_BINS
    span = score_count - 2 * margin
    if span < M37_COMPLETENESS_TRUTHS_PER_LEVEL or math.gcd(
        M37_COMPLETENESS_CARRIER_STEP, span
    ) != 1:
        raise V0P6ContractError("prospective carrier allocation is not injective")
    if (
        M37_COMPLETENESS_RADIAL_STRATA
        * M37_COMPLETENESS_PHASE_STRATA
        != M37_COMPLETENESS_TRUTHS_PER_LEVEL
    ):
        raise V0P6ContractError(
            "continuous disk strata do not equal the truth inventory"
        )
    carrier_offset = M37_COMPLETENESS_MASTER_SEED % span
    truths: list[CompletenessTruth] = []
    for ordinal in range(M37_COMPLETENESS_TRUTHS_PER_LEVEL):
        radial_stratum = ordinal // M37_COMPLETENESS_PHASE_STRATA
        phase_stratum = ordinal % M37_COMPLETENESS_PHASE_STRATA
        radial_jitter = _jitter01(
            M37_COMPLETENESS_MASTER_SEED,
            "continuous-disk-radial-jitter",
            radial_stratum,
            phase_stratum,
        )
        phase_jitter = _jitter01(
            M37_COMPLETENESS_MASTER_SEED,
            "continuous-disk-phase-jitter",
            radial_stratum,
            phase_stratum,
        )
        projected_scale = math.sqrt(
            (radial_stratum + radial_jitter)
            / M37_COMPLETENESS_RADIAL_STRATA
        )
        phase_cycles = (
            phase_stratum + phase_jitter
        ) / M37_COMPLETENESS_PHASE_STRATA
        angle = 2.0 * math.pi * phase_cycles
        coefficient_x = projected_scale * math.cos(angle)
        coefficient_y = projected_scale * math.sin(angle)
        (
            template_index,
            line_index,
            line_coefficient,
            direction_projection,
        ) = _nearest_line_assignment(coefficient_x, coefficient_y)
        template = bank[template_index]
        if (
            int(template["line_index"]) != line_index
            or float(template["line_coefficient"]) != line_coefficient
        ):
            raise V0P6IncompleteError(
                "continuous truth association disagrees with the frozen bank"
            )
        nuisance_combo = (
            phase_stratum + 5 * radial_stratum
        ) % (
            len(M37_SPECTRAL_WIDTHS) * len(M37_ACTIVITY_SUBSETS)
        )
        width_index = nuisance_combo % len(M37_SPECTRAL_WIDTHS)
        activity_index = nuisance_combo // len(M37_SPECTRAL_WIDTHS)
        proxy_index = margin + (
            carrier_offset + ordinal * M37_COMPLETENESS_CARRIER_STEP
        ) % span
        q_hz = float(grid.score_hz[proxy_index])
        partial = CompletenessTruth(
            truth_ordinal=ordinal,
            truth_id="",
            window_id=M37_COMPLETENESS_BACKGROUND_WINDOW,
            template_index=template_index,
            line_index=line_index,
            line_coefficient=line_coefficient,
            coefficient_x=coefficient_x,
            coefficient_y=coefficient_y,
            direction_projection=direction_projection,
            projected_scale=projected_scale,
            phase_cycles=phase_cycles,
            radial_stratum_index=radial_stratum,
            phase_stratum_index=phase_stratum,
            spectral_width_index=width_index,
            spectral_width_channels=M37_SPECTRAL_WIDTHS[width_index],
            activity_subset_index=activity_index,
            active_epochs_zero_based=M37_ACTIVITY_SUBSETS[activity_index],
            proxy_carrier_index=proxy_index,
            proxy_carrier_lattice_index=proxy_index - M37_SCORE_HALF_BINS,
            proxy_carrier_hz=q_hz,
            proxy_carrier_mhz=q_hz / 1e6,
            truth_seed=_seed64(
                M37_COMPLETENESS_MASTER_SEED,
                "truth",
                ordinal,
            ),
        )
        truths.append(
            replace(
                partial,
                truth_id=_sha256(partial.as_record(include_identity=False)),
            )
        )
    return tuple(truths)


def _trial_for(
    allocation_contract_sha256: str,
    truth: CompletenessTruth,
    level_index: int,
) -> CompletenessTrial:
    snr = M37_COMPLETENESS_SNR_GRID[level_index]
    noise_seed = _seed64(
        M37_COMPLETENESS_MASTER_SEED,
        "noise",
        level_index,
        truth.truth_ordinal,
    )
    key = {
        "allocation_contract_sha256": allocation_contract_sha256,
        "truth_id": truth.truth_id,
        "level_index": level_index,
        "ideal_single_epoch_snr": snr,
        "noise_seed": noise_seed,
    }
    return CompletenessTrial(
        trial_id=_sha256(key),
        level_index=level_index,
        ideal_single_epoch_snr=snr,
        noise_seed=noise_seed,
        truth=truth,
    )


def _make_plan(*, enforce_known_answers: bool) -> CompletenessPlan:
    allocation_digest = _sha256(_allocation_contract_payload())
    truths = _make_truths()
    truth_digest = _sha256([item.as_record() for item in truths])
    trials = [
        _trial_for(allocation_digest, truth, level_index).as_record()
        for level_index in range(len(M37_COMPLETENESS_SNR_GRID))
        for truth in truths
    ]
    trial_digest = _sha256(trials)
    plan_record = {
        "status": M37_COMPLETENESS_STATUS,
        "allocation_contract_sha256": allocation_digest,
        "truth_inventory_sha256": truth_digest,
        "trial_inventory_sha256": trial_digest,
        "truth_count_per_snr_level": len(truths),
        "snr_grid": list(M37_COMPLETENESS_SNR_GRID),
        "expected_trial_count": len(trials),
    }
    plan = CompletenessPlan(
        status=M37_COMPLETENESS_STATUS,
        allocation_contract_sha256=allocation_digest,
        truth_inventory_sha256=truth_digest,
        trial_inventory_sha256=trial_digest,
        plan_sha256=_sha256(plan_record),
        truths=truths,
    )
    if enforce_known_answers:
        expected = (
            M37_COMPLETENESS_ALLOCATION_CONTRACT_SHA256,
            M37_COMPLETENESS_TRUTH_INVENTORY_SHA256,
            M37_COMPLETENESS_TRIAL_INVENTORY_SHA256,
            M37_COMPLETENESS_PLAN_SHA256,
        )
        observed = (
            plan.allocation_contract_sha256,
            plan.truth_inventory_sha256,
            plan.trial_inventory_sha256,
            plan.plan_sha256,
        )
        if observed != expected:
            raise V0P6IncompleteError(
                "prospective M37 completeness allocation identities changed"
            )
    return plan


def make_m37_prospective_completeness_plan() -> CompletenessPlan:
    """Build the provisional 512-by-12 M37 completeness allocation."""
    plan = _make_plan(enforce_known_answers=True)
    validate_m37_completeness_plan(plan)
    return plan


def validate_m37_completeness_plan(plan: CompletenessPlan) -> None:
    """Reconstruct every truth and trial identity and require literal hashes."""
    if not isinstance(plan, CompletenessPlan):
        raise V0P6ContractError("completeness plan has an invalid type")
    expected = _make_plan(enforce_known_answers=False)
    if plan != expected or plan.as_record() != expected.as_record():
        raise V0P6IncompleteError("prospective completeness plan changed")
    if len(plan.truths) != M37_COMPLETENESS_TRUTHS_PER_LEVEL:
        raise V0P6IncompleteError("truth inventory is incomplete")
    for truth in plan.truths:
        _validate_completeness_truth(truth)
    cells = {
        (item.radial_stratum_index, item.phase_stratum_index)
        for item in plan.truths
    }
    expected_cells = {
        (radial, phase)
        for radial in range(M37_COMPLETENESS_RADIAL_STRATA)
        for phase in range(M37_COMPLETENESS_PHASE_STRATA)
    }
    if cells != expected_cells:
        raise V0P6IncompleteError(
            "continuous truth inventory does not cover every disk stratum"
        )
    bank_coefficients = {
        (float(item["coefficient_x"]), float(item["coefficient_y"]))
        for item in make_line_template_bank()
    }
    if any(
        (item.coefficient_x, item.coefficient_y) in bank_coefficients
        for item in plan.truths
    ):
        raise V0P6IncompleteError(
            "continuous truth inventory contains an exact bank member"
        )
    if set(item.spectral_width_channels for item in plan.truths) != set(
        M37_SPECTRAL_WIDTHS
    ):
        raise V0P6IncompleteError("truth inventory does not cover all widths")
    if set(item.active_epochs_zero_based for item in plan.truths) != set(
        M37_ACTIVITY_SUBSETS
    ):
        raise V0P6IncompleteError("truth inventory does not cover all activities")
    nuisance_pairs = {
        (width_index, activity_index)
        for width_index in range(len(M37_SPECTRAL_WIDTHS))
        for activity_index in range(len(M37_ACTIVITY_SUBSETS))
    }
    for radial_stratum in range(M37_COMPLETENESS_RADIAL_STRATA):
        observed_pairs = {
            (item.spectral_width_index, item.activity_subset_index)
            for item in plan.truths
            if item.radial_stratum_index == radial_stratum
        }
        if observed_pairs != nuisance_pairs:
            raise V0P6IncompleteError(
                "a radial stratum does not cover every nuisance pair"
            )
    for width_index, activity_index in nuisance_pairs:
        matching = [
            item
            for item in plan.truths
            if item.spectral_width_index == width_index
            and item.activity_subset_index == activity_index
        ]
        if (
            {item.radial_stratum_index for item in matching}
            != set(range(M37_COMPLETENESS_RADIAL_STRATA))
            or len({item.phase_stratum_index for item in matching})
            != M37_COMPLETENESS_RADIAL_STRATA
        ):
            raise V0P6IncompleteError(
                "a nuisance pair is phase-confounded with disk strata"
            )
    if len(set(item.proxy_carrier_index for item in plan.truths)) != len(
        plan.truths
    ):
        raise V0P6IncompleteError("truth carrier allocation contains duplicates")


def iter_m37_completeness_trials(
    plan: CompletenessPlan,
) -> tuple[CompletenessTrial, ...]:
    """Return the canonical level-major exhaustive trial sequence."""
    validate_m37_completeness_plan(plan)
    trials = tuple(
        _trial_for(plan.allocation_contract_sha256, truth, level_index)
        for level_index in range(len(M37_COMPLETENESS_SNR_GRID))
        for truth in plan.truths
    )
    if _sha256([item.as_record() for item in trials]) != plan.trial_inventory_sha256:
        raise V0P6IncompleteError("trial inventory changed during reconstruction")
    return trials


@dataclass(frozen=True)
class FrozenOperationalThreshold:
    """A digest-bound final threshold used unchanged for every injection."""

    operational_threshold_snr: float
    threshold_certificate_sha256: str
    experiment_contract_sha256: str
    factor_table_sha256: str
    analysis_contract_sha256: str
    source_kind: str
    threshold_identity_sha256: str

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "operational_threshold_snr": self.operational_threshold_snr,
            "threshold_certificate_sha256": self.threshold_certificate_sha256,
            "experiment_contract_sha256": self.experiment_contract_sha256,
            "factor_table_sha256": self.factor_table_sha256,
            "analysis_contract_sha256": self.analysis_contract_sha256,
            "source_kind": self.source_kind,
            "inclusive_comparison": "finite score >= operational threshold",
            "threshold_reestimated_after_injection": False,
        }
        if include_identity:
            record["threshold_identity_sha256"] = self.threshold_identity_sha256
        return record


def _freeze_operational_threshold(
    operational_threshold_snr: float,
    threshold_certificate_sha256: str,
    experiment_contract_sha256: str,
    factor_table_sha256: str,
    analysis_contract_sha256: str,
    source_kind: str,
) -> FrozenOperationalThreshold:
    threshold = float(operational_threshold_snr)
    if not math.isfinite(threshold):
        raise V0P6ContractError("operational threshold must be finite")
    partial = FrozenOperationalThreshold(
        operational_threshold_snr=threshold,
        threshold_certificate_sha256=_frozen_sha256(
            threshold_certificate_sha256, "threshold-certificate identity"
        ),
        experiment_contract_sha256=_frozen_sha256(
            experiment_contract_sha256, "experiment-contract identity"
        ),
        factor_table_sha256=_frozen_sha256(
            factor_table_sha256, "factor-table identity"
        ),
        analysis_contract_sha256=_frozen_sha256(
            analysis_contract_sha256, "analysis-contract identity"
        ),
        source_kind=str(source_kind),
        threshold_identity_sha256="",
    )
    if partial.source_kind not in {
        "synthetic-known-answer-adapter",
        "m37-factory-attested-threshold-certificate",
    }:
        raise V0P6ContractError("frozen threshold source kind is invalid")
    return replace(
        partial,
        threshold_identity_sha256=_sha256(
            partial.as_record(include_identity=False)
        ),
    )


def freeze_operational_threshold(
    operational_threshold_snr: float,
    threshold_certificate_sha256: str,
    experiment_contract_sha256: str,
    factor_table_sha256: str,
    analysis_contract_sha256: str,
) -> FrozenOperationalThreshold:
    """Seal a threshold identity for a synthetic/known-answer adapter."""
    return _freeze_operational_threshold(
        operational_threshold_snr,
        threshold_certificate_sha256,
        experiment_contract_sha256,
        factor_table_sha256,
        analysis_contract_sha256,
        "synthetic-known-answer-adapter",
    )


def validate_frozen_threshold(threshold: FrozenOperationalThreshold) -> None:
    if not isinstance(threshold, FrozenOperationalThreshold):
        raise V0P6ContractError("frozen threshold has an invalid type")
    expected = _freeze_operational_threshold(
        threshold.operational_threshold_snr,
        threshold.threshold_certificate_sha256,
        threshold.experiment_contract_sha256,
        threshold.factor_table_sha256,
        threshold.analysis_contract_sha256,
        threshold.source_kind,
    )
    if threshold != expected:
        raise V0P6IncompleteError("frozen threshold identity changed")


_M37_ATTESTED_THRESHOLD_IDENTITIES: set[str] = set()
_M37_ATTESTED_THRESHOLD_IDENTITY_CAP = 64

_ATTESTED_FACTOR_PROVENANCE: set[tuple[str, str, str, str]] = set()
_ATTESTED_FACTOR_PROVENANCE_CAP = 64


def _validate_and_attest_factor_provenance(
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
) -> None:
    """Validate basis/table bytes and fully derive each new provenance once."""
    if not isinstance(factor_basis, FactorBasis) or not isinstance(
        factor_table, TemplateFactorTable
    ):
        raise V0P6ContractError("factor provenance has an invalid type")
    validate_factor_basis(factor_basis)
    if (
        factor_table.factors.flags.writeable
        or factor_table.template_bank_sha256 != M37_BANK_SHA256
        or factor_table.factor_basis_sha256 != factor_basis.basis_sha256
        or factor_table.factor_basis_labels_sha256 != factor_basis.labels_sha256
        or factor_table_sha256(factor_table.factors)
        != factor_table.factor_table_sha256
    ):
        raise V0P6IncompleteError("sealed factor-table provenance changed")
    identity = (
        factor_basis.basis_sha256,
        factor_basis.labels_sha256,
        factor_table.template_bank_sha256,
        factor_table.factor_table_sha256,
    )
    if identity not in _ATTESTED_FACTOR_PROVENANCE:
        validate_template_factor_table(
            factor_table,
            factor_basis,
            make_line_template_bank(),
            expected_template_bank_sha256=M37_BANK_SHA256,
        )
        if len(_ATTESTED_FACTOR_PROVENANCE) >= (
            _ATTESTED_FACTOR_PROVENANCE_CAP
        ):
            raise V0P6CapacityError("factor-provenance attestation cap exceeded")
        _ATTESTED_FACTOR_PROVENANCE.add(identity)


def freeze_m37_operational_threshold(
    certificate: ThresholdCertificate,
) -> FrozenOperationalThreshold:
    """Bind completeness to a live, factory-attested final M37 threshold."""
    validate_threshold_certificate(certificate)
    if (
        certificate.window_ids != M37_WINDOW_IDS
        or certificate.experiment_contract_sha256
        != M37_EXPERIMENT_CONTRACT_SHA256
        or certificate.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or certificate.factor_basis_labels_sha256
        != M37_FACTOR_BASIS_LABELS_SHA256
        or certificate.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
        or certificate.calibration_factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or certificate.scramble_table_sha256s
        != M37_SCRAMBLE_TABLE_SHA256S
        or certificate.global_null_count != M37_SCRAMBLE_COUNT
        or certificate.reference_floor_snr
        != M37_THRESHOLD_REFERENCE_FLOOR_SNR
        or certificate.empirical_quantile != M37_THRESHOLD_QUANTILE
        or certificate.scientific_empirical_p_ceiling
        != M37_SCIENTIFIC_P_CEILING
        or certificate.calibration_execution_engines
        != (M37_CALIBRATION_EXECUTION_ENGINE,) * len(M37_WINDOW_IDS)
        or len(certificate.calibration_execution_identity_sha256s)
        != len(M37_WINDOW_IDS)
        or len(set(certificate.calibration_execution_identity_sha256s)) != 1
    ):
        raise V0P6ContractError("threshold certificate is not the final M37 one")
    threshold = _freeze_operational_threshold(
        certificate.operational_threshold_snr,
        certificate.certificate_sha256,
        certificate.experiment_contract_sha256,
        certificate.factor_table_sha256,
        certificate.analysis_contract_sha256,
        "m37-factory-attested-threshold-certificate",
    )
    if threshold.threshold_identity_sha256 not in _M37_ATTESTED_THRESHOLD_IDENTITIES:
        if len(_M37_ATTESTED_THRESHOLD_IDENTITIES) >= (
            _M37_ATTESTED_THRESHOLD_IDENTITY_CAP
        ):
            raise V0P6CapacityError("M37 threshold attestation cap exceeded")
        _M37_ATTESTED_THRESHOLD_IDENTITIES.add(
            threshold.threshold_identity_sha256
        )
    return threshold


@dataclass(frozen=True)
class NativeBackgroundScan:
    """One immutable logical ON scan supplied to a streaming trial."""

    scan_label: str
    epoch_index: int
    normalized: np.ndarray = field(repr=False, compare=False)
    geometry: NativeFrequencyGeometry
    truth_factors: np.ndarray = field(repr=False, compare=False)
    truth: CompletenessTruth = field(repr=False, compare=False)
    factor_basis: FactorBasis = field(repr=False, compare=False)
    factor_table: TemplateFactorTable = field(repr=False, compare=False)
    truth_id: str
    truth_template_index: int
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    template_bank_sha256: str
    factor_table_sha256: str
    normalized_sha256: str
    truth_factors_sha256: str
    scan_sha256: str

    def identity_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "scan_label": self.scan_label,
            "epoch_index": self.epoch_index,
            "normalized_shape": list(self.normalized.shape),
            "normalized_dtype": "<f4",
            "normalized_sha256": self.normalized_sha256,
            "geometry": {
                "raw_zero_hz": self.geometry.raw_zero_hz,
                "channel_width_hz": self.geometry.channel_width_hz,
                "channel_count": self.geometry.channel_count,
            },
            "truth_factors_shape": list(self.truth_factors.shape),
            "truth_factors_dtype": "<f8",
            "truth_factors_sha256": self.truth_factors_sha256,
            "truth_id": self.truth_id,
            "truth_template_index": self.truth_template_index,
            "factor_basis_sha256": self.factor_basis_sha256,
            "factor_basis_labels_sha256": self.factor_basis_labels_sha256,
            "template_bank_sha256": self.template_bank_sha256,
            "factor_table_sha256": self.factor_table_sha256,
        }
        if include_identity:
            record["scan_sha256"] = self.scan_sha256
        return record


def seal_native_background_scan(
    scan_label: str,
    epoch_index: int,
    normalized: np.ndarray,
    geometry: NativeFrequencyGeometry,
    *,
    truth: CompletenessTruth,
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
) -> NativeBackgroundScan:
    """Seal native values and derive the continuous truth track from a basis.

    Callers cannot supply a factor vector.  The vector is reproduced as
    ``baseline + orbital @ [truth.coefficient_x, truth.coefficient_y]`` from
    the sealed factor basis, while the detector's canonical 93-row factor
    table is independently validated against that same basis.
    """
    label = str(scan_label)
    epoch = _strict_int(epoch_index, "epoch index")
    if not label or epoch not in (0, 1, 2):
        raise V0P6ContractError("native scan label/epoch is invalid")
    if not isinstance(geometry, NativeFrequencyGeometry):
        raise V0P6ContractError("native scan geometry has an invalid type")
    _validate_completeness_truth(truth)
    _validate_and_attest_factor_provenance(factor_basis, factor_table)
    values_bytes = np.ascontiguousarray(normalized, dtype="<f4").tobytes()
    values = np.frombuffer(values_bytes, dtype="<f4").reshape(
        np.asarray(normalized).shape
    )
    derived_factors = template_factors_from_basis(
        factor_basis,
        {
            "coefficient_x": truth.coefficient_x,
            "coefficient_y": truth.coefficient_y,
        },
        scan_label=label,
    )
    factors_bytes = np.ascontiguousarray(derived_factors, dtype="<f8").tobytes()
    factors = np.frombuffer(factors_bytes, dtype="<f8")
    if values.ndim != 2 or values.shape[1] != geometry.channel_count:
        raise V0P6ContractError(
            "normalized native scan does not match its geometry"
        )
    if factors.shape != (values.shape[0],):
        raise V0P6ContractError("truth-factor count does not match integrations")
    if not np.all(np.isfinite(values)):
        raise V0P6ContractError("normalized native scan contains non-finite data")
    if not np.all(np.isfinite(factors)) or np.any(factors <= 0.0):
        raise V0P6ContractError("truth factors must be finite and positive")
    partial = NativeBackgroundScan(
        scan_label=label,
        epoch_index=epoch,
        normalized=values,
        geometry=geometry,
        truth_factors=factors,
        truth=truth,
        factor_basis=factor_basis,
        factor_table=factor_table,
        truth_id=truth.truth_id,
        truth_template_index=truth.template_index,
        factor_basis_sha256=factor_basis.basis_sha256,
        factor_basis_labels_sha256=factor_basis.labels_sha256,
        template_bank_sha256=factor_table.template_bank_sha256,
        factor_table_sha256=factor_table.factor_table_sha256,
        normalized_sha256=hashlib.sha256(values_bytes).hexdigest(),
        truth_factors_sha256=hashlib.sha256(factors_bytes).hexdigest(),
        scan_sha256="",
    )
    return replace(
        partial,
        scan_sha256=_sha256(partial.identity_record(include_identity=False)),
    )


def validate_native_background_scan(scan: NativeBackgroundScan) -> None:
    if not isinstance(scan, NativeBackgroundScan):
        raise V0P6ContractError("native background scan has an invalid type")
    if not isinstance(scan.geometry, NativeFrequencyGeometry):
        raise V0P6ContractError("native scan geometry has an invalid type")
    if (
        scan.normalized.dtype != np.dtype("<f4")
        or scan.normalized.flags.writeable
        or not scan.normalized.flags.c_contiguous
        or scan.truth_factors.dtype != np.dtype("<f8")
        or scan.truth_factors.flags.writeable
        or not scan.truth_factors.flags.c_contiguous
        or scan.normalized.ndim != 2
        or scan.normalized.shape[1] != scan.geometry.channel_count
        or scan.truth_factors.shape != (scan.normalized.shape[0],)
    ):
        raise V0P6IncompleteError("sealed native scan layout changed")
    if _float32_sha256(scan.normalized) != scan.normalized_sha256 or (
        _float64_sha256(scan.truth_factors) != scan.truth_factors_sha256
    ):
        raise V0P6IncompleteError("sealed native scan payload changed")
    if not np.all(np.isfinite(scan.normalized)) or not np.all(
        np.isfinite(scan.truth_factors) & (scan.truth_factors > 0.0)
    ):
        raise V0P6ContractError("sealed native scan payload is invalid")
    _validate_completeness_truth(scan.truth)
    _validate_and_attest_factor_provenance(
        scan.factor_basis, scan.factor_table
    )
    expected_factors = template_factors_from_basis(
        scan.factor_basis,
        {
            "coefficient_x": scan.truth.coefficient_x,
            "coefficient_y": scan.truth.coefficient_y,
        },
        scan_label=scan.scan_label,
    )
    if (
        scan.truth_id != scan.truth.truth_id
        or scan.truth_template_index != scan.truth.template_index
        or scan.factor_basis_sha256 != scan.factor_basis.basis_sha256
        or scan.factor_basis_labels_sha256 != scan.factor_basis.labels_sha256
        or scan.template_bank_sha256 != M37_BANK_SHA256
        or scan.template_bank_sha256
        != scan.factor_table.template_bank_sha256
        or scan.factor_table_sha256 != scan.factor_table.factor_table_sha256
        or not np.array_equal(scan.truth_factors, expected_factors)
    ):
        raise V0P6IncompleteError(
            "sealed continuous truth factors do not reproduce from the basis"
        )
    if (
        not isinstance(scan.scan_label, str)
        or not scan.scan_label
        or _strict_int(scan.epoch_index, "epoch index") not in (0, 1, 2)
        or not isinstance(scan.geometry, NativeFrequencyGeometry)
        or scan.scan_sha256
        != _sha256(scan.identity_record(include_identity=False))
    ):
        raise V0P6IncompleteError("sealed native scan identity changed")


@dataclass(frozen=True)
class NativeTrialBackground:
    """Exactly three ON scans plus a digest for opaque operational context."""

    trial_id: str
    noise_seed: int
    scans: tuple[NativeBackgroundScan, ...]
    source_kind: str
    source_product_sha256s: tuple[str, ...]
    noise_shift_channels: tuple[int, ...]
    noise_selection_sha256: str
    scan_inventory_sha256: str
    source_working_set_accounting_sha256s: tuple[str, ...]
    source_working_set_contract_sha256: str
    maximum_live_native_bytes_observed: int
    maximum_live_native_bytes_per_trial: int
    truth_id: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    template_bank_sha256: str
    factor_table_sha256: str
    context_sha256: str
    background_sha256: str
    context: Any = field(default=None, repr=False, compare=False)

    def identity_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "trial_id": self.trial_id,
            "noise_seed": self.noise_seed,
            "scan_sha256s": [scan.scan_sha256 for scan in self.scans],
            "source_kind": self.source_kind,
            "source_product_sha256s": list(self.source_product_sha256s),
            "noise_shift_channels": list(self.noise_shift_channels),
            "noise_selection_sha256": self.noise_selection_sha256,
            "scan_inventory_sha256": self.scan_inventory_sha256,
            "source_working_set_accounting_sha256s": list(
                self.source_working_set_accounting_sha256s
            ),
            "source_working_set_contract_sha256": (
                self.source_working_set_contract_sha256
            ),
            "maximum_live_native_bytes_observed": (
                self.maximum_live_native_bytes_observed
            ),
            "maximum_live_native_bytes_per_trial": (
                self.maximum_live_native_bytes_per_trial
            ),
            "truth_id": self.truth_id,
            "factor_basis_sha256": self.factor_basis_sha256,
            "factor_basis_labels_sha256": self.factor_basis_labels_sha256,
            "template_bank_sha256": self.template_bank_sha256,
            "factor_table_sha256": self.factor_table_sha256,
            "context_sha256": self.context_sha256,
        }
        if include_identity:
            record["background_sha256"] = self.background_sha256
        return record


_M37_BACKGROUND_ATTESTATIONS: dict[str, bytes] = {}
_M37_BACKGROUND_ATTESTATION_CAP = 8_192


def _seal_native_trial_background(
    trial: CompletenessTrial,
    scans: Sequence[NativeBackgroundScan],
    *,
    source_kind: str,
    source_product_sha256s: Sequence[str],
    noise_shift_channels: Sequence[int],
    noise_selection_sha256: str,
    scan_inventory_sha256: str,
    source_working_set_accounting_sha256s: Sequence[str],
    source_working_set_contract_sha256: str,
    maximum_live_native_bytes_observed: int,
    context_sha256: str,
    context: Any,
) -> NativeTrialBackground:
    scans = tuple(scans)
    source_digests = tuple(
        _frozen_sha256(item, "background source-product identity")
        for item in source_product_sha256s
    )
    shifts = tuple(
        _strict_int(item, "background noise shift")
        for item in noise_shift_channels
    )
    accounting_digests = tuple(
        _frozen_sha256(item, "source working-set accounting identity")
        for item in source_working_set_accounting_sha256s
    )
    if (
        len(scans) != 3
        or len(source_digests) != 3
        or len(shifts) != 3
        or len(accounting_digests) != 3
    ):
        raise V0P6IncompleteError("a completeness background needs three ON scans")
    maximum_live = _strict_int(
        maximum_live_native_bytes_observed,
        "background maximum live native bytes",
    )
    if (
        maximum_live < 0
        or maximum_live
        > M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
    ):
        raise V0P6CapacityError(
            "background native working-set accounting exceeds its cap"
        )
    for scan in scans:
        validate_native_background_scan(scan)
    if tuple(scan.epoch_index for scan in scans) != (0, 1, 2):
        raise V0P6IncompleteError("background ON epochs changed or reordered")
    if any(
        scan.truth_id != trial.truth.truth_id
        or scan.truth != trial.truth
        or scan.truth_template_index != trial.truth.template_index
        for scan in scans
    ):
        raise V0P6ContractError("background selected the wrong continuous truth")
    provenance = {
        (
            scan.factor_basis_sha256,
            scan.factor_basis_labels_sha256,
            scan.template_bank_sha256,
            scan.factor_table_sha256,
        )
        for scan in scans
    }
    if len(provenance) != 1:
        raise V0P6ContractError("background scans disagree on factor provenance")
    basis_sha, labels_sha, bank_sha, table_sha = next(iter(provenance))
    partial = NativeTrialBackground(
        trial_id=_frozen_sha256(trial.trial_id, "trial identity"),
        noise_seed=_strict_int(trial.noise_seed, "noise seed"),
        scans=scans,
        source_kind=str(source_kind),
        source_product_sha256s=source_digests,
        noise_shift_channels=shifts,
        noise_selection_sha256=_frozen_sha256(
            noise_selection_sha256, "noise-selection identity"
        ),
        scan_inventory_sha256=_frozen_sha256(
            scan_inventory_sha256, "background scan-inventory identity"
        ),
        source_working_set_accounting_sha256s=accounting_digests,
        source_working_set_contract_sha256=_frozen_sha256(
            source_working_set_contract_sha256,
            "source streaming working-set contract identity",
        ),
        maximum_live_native_bytes_observed=maximum_live,
        maximum_live_native_bytes_per_trial=(
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        ),
        truth_id=trial.truth.truth_id,
        factor_basis_sha256=basis_sha,
        factor_basis_labels_sha256=labels_sha,
        template_bank_sha256=bank_sha,
        factor_table_sha256=table_sha,
        context_sha256=_frozen_sha256(
            context_sha256, "background context identity"
        ),
        background_sha256="",
        context=context,
    )
    return replace(
        partial,
        background_sha256=_sha256(
            partial.identity_record(include_identity=False)
        ),
    )


def seal_native_trial_background(
    trial: CompletenessTrial,
    scans: Sequence[NativeBackgroundScan],
    *,
    context_sha256: str,
    context: Any = None,
) -> NativeTrialBackground:
    """Seal an explicit non-production background used by known answers."""
    scans_tuple = tuple(scans)
    selection = {
        "artifact_type": "synthetic-known-answer-background-selection-v1",
        "trial_id": trial.trial_id,
        "noise_seed": trial.noise_seed,
        "scan_sha256s": [scan.scan_sha256 for scan in scans_tuple],
        "noise_shift_channels": [0, 0, 0],
    }
    synthetic_working_set_records = tuple(
        {
            "artifact_type": "synthetic-background-working-set-v1",
            "scan_label": scan.scan_label,
            "scan_sha256": scan.scan_sha256,
            "live_native_bytes": scan.normalized.nbytes,
        }
        for scan in scans_tuple
    )
    return _seal_native_trial_background(
        trial,
        scans_tuple,
        source_kind="synthetic-known-answer-background-v1",
        source_product_sha256s=tuple(
            scan.normalized_sha256 for scan in scans_tuple
        ),
        noise_shift_channels=(0, 0, 0),
        noise_selection_sha256=_sha256(selection),
        scan_inventory_sha256=_sha256(
            [scan.scan_label for scan in scans_tuple]
        ),
        source_working_set_accounting_sha256s=tuple(
            _sha256(record) for record in synthetic_working_set_records
        ),
        source_working_set_contract_sha256=_sha256(
            {
                "artifact_type": (
                    "synthetic-known-answer-background-working-set-v1"
                ),
                "production_permitted": False,
            }
        ),
        maximum_live_native_bytes_observed=sum(
            scan.normalized.nbytes for scan in scans_tuple
        ),
        context_sha256=context_sha256,
        context=context,
    )


def seal_m37_native_trial_background(
    trial: CompletenessTrial,
    normalized_scan_products: Iterable[Any],
    *,
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    expected_product_sha256s: Sequence[str] | None = None,
    expected_extraction_receipt_sha256s: Sequence[str] | None = None,
    context: Any = None,
) -> NativeTrialBackground:
    """Build the only production background from attested M37 scan products.

    The factory applies one deterministic, seed-bound circular native-channel
    noise shift per ON epoch.  Callers cannot supply selected background bits,
    labels, geometry, or shifts.
    """
    try:
        from .source_v0p6 import (
            M37NormalizedScanProduct,
            m37_source_working_set_accounting,
            validate_m37_normalized_scan_product,
        )
    except ImportError as error:
        raise V0P6ContractError(
            "strict M37 normalized-scan factory is unavailable"
        ) from error

    _validate_completeness_truth(trial.truth)
    if trial.truth.window_id != M37_COMPLETENESS_BACKGROUND_WINDOW:
        raise V0P6ContractError("M37 completeness selected another window")
    _validate_and_attest_factor_provenance(factor_basis, factor_table)
    expected_products = (
        (None,) * 3
        if expected_product_sha256s is None
        else tuple(expected_product_sha256s)
    )
    expected_extractions = (
        (None,) * 3
        if expected_extraction_receipt_sha256s is None
        else tuple(expected_extraction_receipt_sha256s)
    )
    if len(expected_products) != 3 or len(expected_extractions) != 3:
        raise V0P6IncompleteError(
            "M37 normalized-scan trusted receipt inventory is incomplete"
        )
    expected_labels = ("epoch1_on", "epoch2_on", "epoch3_on")
    scans: list[NativeBackgroundScan] = []
    shifts: list[int] = []
    selection_items: list[dict[str, Any]] = []
    source_product_sha256s: list[str] = []
    try:
        product_iterator = iter(normalized_scan_products)
    except TypeError as error:
        raise V0P6ContractError(
            "M37 normalized sources must be a streaming iterable"
        ) from error
    if product_iterator is not normalized_scan_products:
        raise V0P6ContractError(
            "M37 normalized sources must be a trusted one-shot iterator; "
            "preloaded sequences violate the source working-set contract "
            "(three exact products + three rolls = 550,168,200 bytes > "
            "512 MiB)"
        )
    working_set_sha256s: list[str] = []
    maximum_live_native_bytes_observed = 0
    factor_provenance_ndarray_bytes = (
        factor_basis.times_mjd.nbytes
        + factor_basis.baseline.nbytes
        + factor_basis.orbital.nbytes
        + factor_table.factors.nbytes
    )
    for epoch, (expected_product, expected_extraction) in enumerate(
        zip(expected_products, expected_extractions, strict=True)
    ):
        try:
            candidate = next(product_iterator)
        except StopIteration as error:
            raise V0P6IncompleteError(
                "M37 normalized ON source inventory ended early"
            ) from error
        if not isinstance(candidate, M37NormalizedScanProduct):
            raise V0P6IncompleteError(
                "M37 background source is not a normalized-scan product"
            )
        retained_scan_bytes = sum(
            item.normalized.nbytes + item.truth_factors.nbytes
            for item in scans
        )
        # Both the current np.roll result and the independent immutable scan
        # copy exist while sealing.  The public source gate additionally
        # charges the raw-sized full-normalization verification scratch.
        accounting = m37_source_working_set_accounting(
            (candidate,),
            additional_live_ndarray_nbytes=(
                retained_scan_bytes
                + 2 * candidate.normalized_values_nbytes
                + factor_provenance_ndarray_bytes
                # derived vector, immutable vector, and arithmetic scratch
                + 4 * candidate.normalized_values.shape[0] * 8
            ),
            simultaneous_normalization_reproductions=1,
            expected_product_sha256s=(expected_product,),
            expected_extraction_receipt_sha256s=(expected_extraction,),
        )
        if accounting["maximum_live_ndarray_nbytes"] != (
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        ):
            raise V0P6ContractError(
                "source and completeness live-byte caps disagree"
            )
        maximum_live_native_bytes_observed = max(
            maximum_live_native_bytes_observed,
            _strict_int(
                accounting["peak_live_ndarray_nbytes"],
                "source working-set peak",
            ),
        )
        working_set_sha256s.append(
            _frozen_sha256(
                accounting["accounting_sha256"],
                "source working-set accounting identity",
            )
        )
        product = validate_m37_normalized_scan_product(
            candidate,
            expected_product_sha256=expected_product,
            expected_extraction_receipt_sha256=expected_extraction,
            verify_arrays=True,
        )
        if (
            product.window_id != M37_COMPLETENESS_BACKGROUND_WINDOW
            or product.scan_label != expected_labels[epoch]
            or product.scan_kind != "on"
            or _strict_int(product.epoch, "source epoch") != epoch + 1
            or product.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
        ):
            raise V0P6ContractError(
                "normalized source is not the exact m37_1412p5 ON inventory"
            )
        channel_count = _strict_int(
            product.geometry.channel_count, "normalized source channel count"
        )
        minimum = core.M37_SCRAMBLE_MINIMUM_SHIFT_BINS
        span = channel_count - 2 * minimum
        if span < 1:
            raise V0P6CoverageError(
                "M37 source is too short for the frozen noise selection"
            )
        shift = minimum + _seed64(
            M37_COMPLETENESS_MASTER_SEED,
            "native-noise-circular-shift-v1",
            trial.noise_seed,
            trial.trial_id,
            epoch,
            product.product_sha256,
        ) % span
        selected_values = np.roll(
            product.normalized_values, shift, axis=1
        )
        scan = seal_native_background_scan(
            product.scan_label,
            epoch,
            selected_values,
            product.geometry,
            truth=trial.truth,
            factor_basis=factor_basis,
            factor_table=factor_table,
        )
        scans.append(scan)
        source_product_sha256s.append(product.product_sha256)
        shifts.append(shift)
        selection_items.append(
            {
                "epoch_zero_based": epoch,
                "scan_label": product.scan_label,
                "source_product_sha256": product.product_sha256,
                "source_normalized_sha256": product.normalized_values_sha256,
                "noise_seed": trial.noise_seed,
                "native_channel_shift": shift,
                "selection": "np.roll(axis=1)-positive-shift",
            }
        )
        # Prevent this consumer from retaining the yielded product/roll into
        # the next iteration.  The one-shot producer is part of the trusted
        # execution contract and must likewise release each yielded product.
        del selected_values
        del product
        del candidate
    try:
        next(product_iterator)
    except StopIteration:
        pass
    else:
        raise V0P6IncompleteError(
            "M37 normalized ON source inventory has extra products"
        )
    if maximum_live_native_bytes_observed != (
        M37_COMPLETENESS_M37_BACKGROUND_PROJECTED_PEAK_BYTES
    ):
        raise V0P6ContractError(
            "M37 scan-at-a-time background projected peak changed from "
            "418,203,096 bytes"
        )
    selection_payload = {
        "artifact_type": "m37-completeness-native-noise-selection-v1",
        "trial_id": trial.trial_id,
        "noise_seed": trial.noise_seed,
        "window_id": M37_COMPLETENESS_BACKGROUND_WINDOW,
        "minimum_shift_channels": core.M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
        "source_streaming_execution_contract_sha256": (
            M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256
        ),
        "source_working_set_accounting_sha256s": working_set_sha256s,
        "maximum_live_native_bytes_observed": (
            maximum_live_native_bytes_observed
        ),
        "maximum_live_native_bytes_per_trial": (
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        ),
        "items": selection_items,
    }
    selection_sha = _sha256(selection_payload)
    background = _seal_native_trial_background(
        trial,
        scans,
        source_kind="m37-factory-normalized-seed-selected-background-v1",
        source_product_sha256s=tuple(source_product_sha256s),
        noise_shift_channels=tuple(shifts),
        noise_selection_sha256=selection_sha,
        scan_inventory_sha256=M37_SCAN_INVENTORY_SHA256,
        source_working_set_accounting_sha256s=tuple(
            working_set_sha256s
        ),
        source_working_set_contract_sha256=(
            M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256
        ),
        maximum_live_native_bytes_observed=(
            maximum_live_native_bytes_observed
        ),
        context_sha256=_sha256(
            {
                "noise_selection_sha256": selection_sha,
                "source_product_sha256s": list(source_product_sha256s),
                "source_working_set_accounting_sha256s": (
                    working_set_sha256s
                ),
                "source_working_set_contract_sha256": (
                    M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256
                ),
                "maximum_live_native_bytes_observed": (
                    maximum_live_native_bytes_observed
                ),
            }
        ),
        context=context,
    )
    encoded = canonical_json_bytes(background.identity_record())
    existing = _M37_BACKGROUND_ATTESTATIONS.get(
        background.background_sha256
    )
    if existing is not None and existing != encoded:
        raise V0P6IncompleteError("M37 background digest collision")
    if existing is None and len(_M37_BACKGROUND_ATTESTATIONS) >= (
        _M37_BACKGROUND_ATTESTATION_CAP
    ):
        raise V0P6CapacityError("M37 background attestation cap exceeded")
    _M37_BACKGROUND_ATTESTATIONS[background.background_sha256] = encoded
    validate_native_trial_background(background, trial)
    return background


def validate_native_trial_background(
    background: NativeTrialBackground,
    trial: CompletenessTrial,
    *,
    expected_background_sha256: str | None = None,
) -> None:
    if not isinstance(background, NativeTrialBackground):
        raise V0P6ContractError("native trial background has an invalid type")
    if background.trial_id != trial.trial_id or (
        background.noise_seed != trial.noise_seed
    ):
        raise V0P6IncompleteError("background belongs to a different trial")
    if len(background.scans) != 3 or tuple(
        scan.epoch_index for scan in background.scans
    ) != (0, 1, 2):
        raise V0P6IncompleteError("background scan inventory changed")
    if any(
        scan.truth_id != trial.truth.truth_id
        or scan.truth != trial.truth
        or scan.truth_template_index != trial.truth.template_index
        or scan.factor_basis_sha256 != background.factor_basis_sha256
        or scan.factor_basis_labels_sha256
        != background.factor_basis_labels_sha256
        or scan.template_bank_sha256 != background.template_bank_sha256
        or scan.factor_table_sha256 != background.factor_table_sha256
        for scan in background.scans
    ):
        raise V0P6IncompleteError("background truth/factor provenance changed")
    if (
        background.truth_id != trial.truth.truth_id
        or background.template_bank_sha256 != M37_BANK_SHA256
    ):
        raise V0P6IncompleteError("background truth/bank identity changed")
    for scan in background.scans:
        validate_native_background_scan(scan)
    if background.background_sha256 != _sha256(
        background.identity_record(include_identity=False)
    ):
        raise V0P6IncompleteError("background identity changed")
    for digest in background.source_product_sha256s:
        _frozen_sha256(digest, "background source-product identity")
    for digest in background.source_working_set_accounting_sha256s:
        _frozen_sha256(digest, "source working-set accounting identity")
    _frozen_sha256(
        background.source_working_set_contract_sha256,
        "source working-set contract identity",
    )
    _frozen_sha256(
        background.noise_selection_sha256, "background noise selection"
    )
    maximum_live = _strict_int(
        background.maximum_live_native_bytes_observed,
        "background maximum live native bytes",
    )
    maximum_per_trial = _strict_int(
        background.maximum_live_native_bytes_per_trial,
        "background maximum live-native-byte cap",
    )
    if (
        len(background.source_product_sha256s) != 3
        or len(background.noise_shift_channels) != 3
        or len(background.source_working_set_accounting_sha256s) != 3
        or maximum_per_trial
        != M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        or maximum_live < sum(
            scan.normalized.nbytes for scan in background.scans
        )
        or maximum_live > maximum_per_trial
        or background.source_kind not in {
            "synthetic-known-answer-background-v1",
            "m37-factory-normalized-seed-selected-background-v1",
        }
    ):
        raise V0P6IncompleteError("background source inventory changed")
    if background.source_kind == (
        "m37-factory-normalized-seed-selected-background-v1"
    ):
        expected = (
            None
            if expected_background_sha256 is None
            else _frozen_sha256(
                expected_background_sha256,
                "expected M37 background identity",
            )
        )
        live = _M37_BACKGROUND_ATTESTATIONS.get(
            background.background_sha256
        ) == canonical_json_bytes(background.identity_record())
        if not live and expected != background.background_sha256:
            raise V0P6ContractError(
                "M37 background lacks a live or trusted source receipt"
            )
        if any(
            scan.geometry.channel_count
            <= 2 * core.M37_SCRAMBLE_MINIMUM_SHIFT_BINS
            for scan in background.scans
        ):
            raise V0P6CoverageError(
                "M37 background is too short for frozen noise selection"
            )
        if (
            background.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
            or len(set(background.source_product_sha256s)) != 3
            or background.source_working_set_contract_sha256
            != M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256
            or tuple(scan.scan_label for scan in background.scans)
            != ("epoch1_on", "epoch2_on", "epoch3_on")
            or background.noise_shift_channels
            != tuple(
                core.M37_SCRAMBLE_MINIMUM_SHIFT_BINS
                + _seed64(
                    M37_COMPLETENESS_MASTER_SEED,
                    "native-noise-circular-shift-v1",
                    trial.noise_seed,
                    trial.trial_id,
                    epoch,
                    source_sha,
                )
                % (
                    scan.geometry.channel_count
                    - 2 * core.M37_SCRAMBLE_MINIMUM_SHIFT_BINS
                )
                for epoch, (scan, source_sha) in enumerate(
                    zip(
                        background.scans,
                        background.source_product_sha256s,
                        strict=True,
                    )
                )
            )
        ):
            raise V0P6ContractError(
                "M37 background inventory/noise selection changed"
            )


@dataclass(frozen=True)
class InjectedNativeScan:
    scan_label: str
    epoch_index: int
    normalized: np.ndarray = field(repr=False, compare=False)
    geometry: NativeFrequencyGeometry
    truth_factors: np.ndarray = field(repr=False, compare=False)
    truth: CompletenessTruth = field(repr=False, compare=False)
    factor_basis: FactorBasis = field(repr=False, compare=False)
    factor_table: TemplateFactorTable = field(repr=False, compare=False)
    truth_id: str
    truth_template_index: int
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    template_bank_sha256: str
    factor_table_sha256: str
    observed_truth_hz_sha256: str
    normalized_sha256: str
    injection_write_count: int
    scan_sha256: str

    def identity_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "scan_label": self.scan_label,
            "epoch_index": self.epoch_index,
            "normalized_shape": list(self.normalized.shape),
            "normalized_dtype": "<f4",
            "normalized_sha256": self.normalized_sha256,
            "geometry": {
                "raw_zero_hz": self.geometry.raw_zero_hz,
                "channel_width_hz": self.geometry.channel_width_hz,
                "channel_count": self.geometry.channel_count,
            },
            "truth_factors_sha256": _float64_sha256(self.truth_factors),
            "truth_id": self.truth_id,
            "truth_template_index": self.truth_template_index,
            "factor_basis_sha256": self.factor_basis_sha256,
            "factor_basis_labels_sha256": self.factor_basis_labels_sha256,
            "template_bank_sha256": self.template_bank_sha256,
            "factor_table_sha256": self.factor_table_sha256,
            "observed_truth_hz_sha256": self.observed_truth_hz_sha256,
            "injection_write_count": self.injection_write_count,
        }
        if include_identity:
            record["scan_sha256"] = self.scan_sha256
        return record


@dataclass(frozen=True)
class InjectedNativeTrial:
    """Sealed native product that must feed mask pass one and filtering."""

    trial_id: str
    background_sha256: str
    scans: tuple[InjectedNativeScan, ...]
    injection_stage: str
    injection_model: str
    injected_native_sha256: str
    context_sha256: str
    background: NativeTrialBackground = field(repr=False, compare=False)
    context: Any = field(default=None, repr=False, compare=False)

    def identity_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "trial_id": self.trial_id,
            "background_sha256": self.background_sha256,
            "scan_sha256s": [scan.scan_sha256 for scan in self.scans],
            "injection_stage": self.injection_stage,
            "injection_model": self.injection_model,
            "filter_coordinate": FILTER_COORDINATE,
            "context_sha256": self.context_sha256,
        }
        if include_identity:
            record["injected_native_sha256"] = self.injected_native_sha256
        return record


def inject_native_before_filter(
    background: NativeTrialBackground,
    trial: CompletenessTrial,
) -> InjectedNativeTrial:
    """Inject ``q*F`` into normalized float32 spectra before native filtering.

    For an odd truth width ``w`` and ``N`` integrations, ``w`` nearest native
    channels receive ``SNR/sqrt(N*w)``.  Consequently the width-``w`` L2
    boxcar followed by the fixed integration sum/sqrt(N) has the requested
    ideal S/N at the exact truth track in a zero background.
    """
    validate_native_trial_background(background, trial)
    width = trial.truth.spectral_width_channels
    half = width // 2
    active = set(trial.truth.active_epochs_zero_based)
    injected: list[InjectedNativeScan] = []
    total_writes = 0
    input_bytes = sum(scan.normalized.nbytes for scan in background.scans)
    expected_writes = sum(
        scan.normalized.shape[0] * width
        for scan in background.scans
        if scan.epoch_index in active
    )
    if 2 * input_bytes > M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL:
        raise V0P6CapacityError("completeness native live-byte cap exceeded")
    if expected_writes > M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL:
        raise V0P6CapacityError("completeness injection-write cap exceeded")
    for scan in background.scans:
        values = np.array(scan.normalized, dtype="<f4", order="C", copy=True)
        observed_hz = np.asarray(
            np.float64(trial.truth.proxy_carrier_hz) * scan.truth_factors,
            dtype="<f8",
        )
        coordinates = (
            observed_hz - np.float64(scan.geometry.raw_zero_hz)
        ) / np.float64(scan.geometry.channel_width_hz)
        if not np.all(np.isfinite(coordinates)):
            raise V0P6ContractError("truth track produced non-finite channels")
        centers = np.rint(coordinates).astype(np.int64)
        writes = 0
        if scan.epoch_index in active:
            if int(np.min(centers)) < half or int(np.max(centers)) >= (
                values.shape[1] - half
            ):
                raise V0P6CoverageError(
                    "native background does not cover the injected truth width"
                )
            amplitude = np.float32(
                trial.ideal_single_epoch_snr
                / math.sqrt(values.shape[0] * width)
            )
            for row, center in enumerate(centers):
                values[row, center - half : center + half + 1] += amplitude
            writes = values.shape[0] * width
            total_writes += writes
        if not np.all(np.isfinite(values)):
            raise V0P6ContractError("native injection produced non-finite values")
        payload_bytes = values.tobytes()
        sealed = np.frombuffer(payload_bytes, dtype="<f4").reshape(values.shape)
        partial = InjectedNativeScan(
            scan_label=scan.scan_label,
            epoch_index=scan.epoch_index,
            normalized=sealed,
            geometry=scan.geometry,
            truth_factors=scan.truth_factors,
            truth=scan.truth,
            factor_basis=scan.factor_basis,
            factor_table=scan.factor_table,
            truth_id=scan.truth_id,
            truth_template_index=scan.truth_template_index,
            factor_basis_sha256=scan.factor_basis_sha256,
            factor_basis_labels_sha256=scan.factor_basis_labels_sha256,
            template_bank_sha256=scan.template_bank_sha256,
            factor_table_sha256=scan.factor_table_sha256,
            observed_truth_hz_sha256=_float64_sha256(observed_hz),
            normalized_sha256=hashlib.sha256(payload_bytes).hexdigest(),
            injection_write_count=writes,
            scan_sha256="",
        )
        injected.append(
            replace(
                partial,
                scan_sha256=_sha256(
                    partial.identity_record(include_identity=False)
                ),
            )
        )
    live_bytes = input_bytes + sum(item.normalized.nbytes for item in injected)
    if live_bytes > M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL:
        raise V0P6CapacityError("completeness native live-byte cap exceeded")
    if total_writes > M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL:
        raise V0P6CapacityError("completeness injection-write cap exceeded")
    partial_product = InjectedNativeTrial(
        trial_id=trial.trial_id,
        background_sha256=background.background_sha256,
        scans=tuple(injected),
        injection_stage=M37_COMPLETENESS_INJECTION_STAGE,
        injection_model=M37_COMPLETENESS_INJECTION_MODEL,
        injected_native_sha256="",
        context_sha256=background.context_sha256,
        background=background,
        context=background.context,
    )
    product = replace(
        partial_product,
        injected_native_sha256=_sha256(
            partial_product.identity_record(include_identity=False)
        ),
    )
    validate_injected_native_trial(product, trial)
    return product


def validate_injected_native_trial(
    injected: InjectedNativeTrial,
    trial: CompletenessTrial,
) -> None:
    if not isinstance(injected, InjectedNativeTrial):
        raise V0P6ContractError("injected native product has an invalid type")
    validate_native_trial_background(injected.background, trial)
    if injected.trial_id != trial.trial_id or len(injected.scans) != 3:
        raise V0P6IncompleteError("injected native trial inventory changed")
    if injected.background_sha256 != injected.background.background_sha256:
        raise V0P6IncompleteError("injected product belongs to another background")
    if tuple(scan.epoch_index for scan in injected.scans) != (0, 1, 2):
        raise V0P6IncompleteError("injected native ON epochs changed or reordered")
    if (
        injected.injection_stage != M37_COMPLETENESS_INJECTION_STAGE
        or injected.injection_model != M37_COMPLETENESS_INJECTION_MODEL
    ):
        raise V0P6ContractError("native injection stage/model changed")
    active = set(trial.truth.active_epochs_zero_based)
    expected_total_writes = 0
    live_bytes = 0
    for scan, source_scan in zip(
        injected.scans, injected.background.scans, strict=True
    ):
        if not isinstance(scan.geometry, NativeFrequencyGeometry):
            raise V0P6ContractError("injected scan geometry has an invalid type")
        if (
            scan.normalized.dtype != np.dtype("<f4")
            or scan.normalized.flags.writeable
            or not scan.normalized.flags.c_contiguous
            or scan.truth_factors.dtype != np.dtype("<f8")
            or scan.truth_factors.flags.writeable
            or not scan.truth_factors.flags.c_contiguous
            or scan.normalized.ndim != 2
            or scan.normalized.shape[1] != scan.geometry.channel_count
            or scan.truth_factors.shape != (scan.normalized.shape[0],)
            or not np.all(np.isfinite(scan.normalized))
        ):
            raise V0P6IncompleteError("injected native scan layout changed")
        _validate_completeness_truth(scan.truth)
        _validate_and_attest_factor_provenance(
            scan.factor_basis, scan.factor_table
        )
        expected_factors = template_factors_from_basis(
            scan.factor_basis,
            {
                "coefficient_x": trial.truth.coefficient_x,
                "coefficient_y": trial.truth.coefficient_y,
            },
            scan_label=scan.scan_label,
        )
        if (
            scan.scan_label != source_scan.scan_label
            or scan.epoch_index != source_scan.epoch_index
            or scan.geometry != source_scan.geometry
            or scan.truth != trial.truth
            or scan.truth_id != trial.truth.truth_id
            or scan.truth_template_index != trial.truth.template_index
            or scan.factor_basis_sha256 != scan.factor_basis.basis_sha256
            or scan.factor_basis_labels_sha256 != scan.factor_basis.labels_sha256
            or scan.template_bank_sha256 != M37_BANK_SHA256
            or scan.template_bank_sha256
            != scan.factor_table.template_bank_sha256
            or scan.factor_table_sha256 != scan.factor_table.factor_table_sha256
            or scan.factor_table_sha256 != injected.scans[0].factor_table_sha256
            or not np.array_equal(scan.truth_factors, expected_factors)
        ):
            raise V0P6IncompleteError(
                "injected continuous truth factor derivation changed"
            )
        expected_observed = np.asarray(
            np.float64(trial.truth.proxy_carrier_hz) * scan.truth_factors,
            dtype="<f8",
        )
        if _float64_sha256(expected_observed) != (
            scan.observed_truth_hz_sha256
        ):
            raise V0P6IncompleteError("injected Y_i=q*F_i track changed")
        if _float32_sha256(scan.normalized) != scan.normalized_sha256:
            raise V0P6IncompleteError("injected native values changed")
        expected_values = np.array(
            source_scan.normalized, dtype="<f4", order="C", copy=True
        )
        coordinates = (
            expected_observed - np.float64(scan.geometry.raw_zero_hz)
        ) / np.float64(scan.geometry.channel_width_hz)
        if not np.all(np.isfinite(coordinates)):
            raise V0P6ContractError("truth track produced non-finite channels")
        centers = np.rint(coordinates).astype(np.int64)
        half = trial.truth.spectral_width_channels // 2
        if scan.epoch_index in active:
            if int(np.min(centers)) < half or int(np.max(centers)) >= (
                expected_values.shape[1] - half
            ):
                raise V0P6CoverageError(
                    "native background does not cover the injected truth width"
                )
            amplitude = np.float32(
                trial.ideal_single_epoch_snr
                / math.sqrt(
                    expected_values.shape[0]
                    * trial.truth.spectral_width_channels
                )
            )
            for row, center in enumerate(centers):
                expected_values[
                    row, center - half : center + half + 1
                ] += amplitude
        if not np.array_equal(scan.normalized, expected_values):
            raise V0P6IncompleteError(
                "injected native values do not reproduce from the background"
            )
        live_bytes += scan.normalized.nbytes
        expected_writes = (
            scan.normalized.shape[0] * trial.truth.spectral_width_channels
            if scan.epoch_index in active
            else 0
        )
        if scan.injection_write_count != expected_writes:
            raise V0P6IncompleteError("injection write accounting changed")
        expected_total_writes += expected_writes
        if scan.scan_sha256 != _sha256(
            scan.identity_record(include_identity=False)
        ):
            raise V0P6IncompleteError("injected native scan identity changed")
    if expected_total_writes > M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL:
        raise V0P6CapacityError("completeness injection-write cap exceeded")
    if 2 * live_bytes > M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL:
        raise V0P6CapacityError("completeness native live-byte cap exceeded")
    if injected.injected_native_sha256 != _sha256(
        injected.identity_record(include_identity=False)
    ):
        raise V0P6IncompleteError("injected native product identity changed")


@dataclass(frozen=True)
class MaskReplayReceipt:
    """Factory receipt for the exact post-injection two-pass mask replay."""

    trial_id: str
    source_injected_native_sha256: str
    source_kind: str
    mask_inventory_sha256: str
    epoch_product_inventory_sha256: str
    cache_provenance_inventory_sha256: str
    injected_scan_sha256s: tuple[str, ...]
    native_filter_cache_count: int
    maximum_live_native_bytes_observed: int
    maximum_live_native_bytes_per_trial: int
    source_epoch_product_count: int
    template_mask_count: int
    recomputed_after_injection: bool
    receipt_sha256: str
    payload: Any = field(default=None, repr=False, compare=False)

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "trial_id": self.trial_id,
            "source_injected_native_sha256": (
                self.source_injected_native_sha256
            ),
            "source_kind": self.source_kind,
            "mask_inventory_sha256": self.mask_inventory_sha256,
            "epoch_product_inventory_sha256": (
                self.epoch_product_inventory_sha256
            ),
            "cache_provenance_inventory_sha256": (
                self.cache_provenance_inventory_sha256
            ),
            "injected_scan_sha256s": list(self.injected_scan_sha256s),
            "native_filter_cache_count": self.native_filter_cache_count,
            "maximum_live_native_bytes_observed": (
                self.maximum_live_native_bytes_observed
            ),
            "maximum_live_native_bytes_per_trial": (
                self.maximum_live_native_bytes_per_trial
            ),
            "source_epoch_product_count": self.source_epoch_product_count,
            "template_mask_count": self.template_mask_count,
            "recomputed_after_injection": self.recomputed_after_injection,
            "mask_rule": "all-eight-width OR then fixed q dilation per template",
            "working_set_accounting_contract": (
                M37_COMPLETENESS_MASK_WORKING_SET_ACCOUNTING_CONTRACT
                if self.source_kind == "m37-live-mask-product-replay-v1"
                else (
                    M37_COMPLETENESS_SYNTHETIC_MASK_WORKING_SET_ACCOUNTING_CONTRACT
                )
            ),
            "spectral_widths": list(M37_SPECTRAL_WIDTHS),
            "strong_snr": M37_RFI_STRONG_SNR,
            "other_epochs_below_snr": M37_RFI_OTHER_EPOCHS_BELOW_SNR,
            "guard_q_bins": M37_RFI_GUARD_Q_BINS,
            "pass_two_must_consume_this_exact_inventory": True,
        }
        if include_identity:
            record["receipt_sha256"] = self.receipt_sha256
        return record


_MASK_REPLAY_RECEIPT_ATTESTATIONS: dict[str, bytes] = {}
_MASK_REPLAY_RECEIPT_ATTESTATION_CAP = 8_192


def _template_mask_replay_live_bytes(
    base_live_native_bytes: int,
    epoch_product_nbytes: Sequence[int],
    mask_product_nbytes: int,
) -> int:
    """Conservatively charge one materialized template-mask replay stage."""
    base = _strict_int(base_live_native_bytes, "mask-replay base bytes")
    epoch_bytes = tuple(
        _strict_int(item, "mask-replay epoch-product bytes")
        for item in epoch_product_nbytes
    )
    mask_bytes = _strict_int(mask_product_nbytes, "mask-product bytes")
    if base < 0 or mask_bytes < 0 or not epoch_bytes or any(
        item < 0 for item in epoch_bytes
    ):
        raise V0P6ContractError(
            "mask-replay byte accounting inputs must be non-negative"
        )
    # build_two_pass_template_mask may simultaneously own float32 safe/sort
    # arrays, argmax/boolean intermediates, the accumulated OR, and dilation
    # output.  Six largest epoch-vector payloads plus four mask payloads is a
    # conservative bound on that implementation's ndarray scratch.
    scratch = 6 * max(epoch_bytes) + 4 * mask_bytes
    return base + sum(epoch_bytes) + mask_bytes + scratch


def _attest_mask_replay_receipt(
    partial: MaskReplayReceipt,
) -> MaskReplayReceipt:
    receipt = replace(
        partial,
        receipt_sha256=_sha256(partial.as_record(include_identity=False)),
    )
    encoded = canonical_json_bytes(receipt.as_record())
    existing = _MASK_REPLAY_RECEIPT_ATTESTATIONS.get(receipt.receipt_sha256)
    if existing is not None and existing != encoded:
        raise V0P6IncompleteError("mask-replay receipt digest collision")
    if existing is None and len(_MASK_REPLAY_RECEIPT_ATTESTATIONS) >= (
        _MASK_REPLAY_RECEIPT_ATTESTATION_CAP
    ):
        raise V0P6CapacityError("mask-replay receipt attestation cap exceeded")
    _MASK_REPLAY_RECEIPT_ATTESTATIONS[receipt.receipt_sha256] = encoded
    return receipt


class M37MaskReplayLedger:
    """Stream the exact cache -> epoch product -> mask provenance chain.

    The ledger keeps only small identities.  Native caches and the eight epoch
    products for one template may be released as soon as they have been added.
    Every cache payload is independently rebuilt from the injected float32
    scan, so a valid-looking plan or caller supplied payload digest is not an
    attestation.
    """

    def __init__(
        self,
        injected: InjectedNativeTrial,
        trial: CompletenessTrial,
        scan_definitions: Sequence[Mapping[str, Any]],
    ) -> None:
        validate_injected_native_trial(injected, trial)
        core.validate_m37_factor_basis_scan_inventory(
            injected.scans[0].factor_basis, scan_definitions
        )
        on_indices = core.m37_scan_indices_for_kind(scan_definitions, "on")
        self._on_labels = tuple(
            str(scan_definitions[index]["label"]) for index in on_indices
        )
        if (
            injected.trial_id != trial.trial_id
            or trial.truth.window_id != M37_COMPLETENESS_BACKGROUND_WINDOW
            or tuple(scan.scan_label for scan in injected.scans)
            != self._on_labels
            or any(
                scan.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
                or scan.factor_basis_labels_sha256
                != M37_FACTOR_BASIS_LABELS_SHA256
                or scan.template_bank_sha256 != M37_BANK_SHA256
                for scan in injected.scans
            )
        ):
            raise V0P6ContractError(
                "M37 mask replay did not receive the exact injected ON scans"
            )
        self.injected = injected
        self.trial = trial
        self.scan_definitions = tuple(scan_definitions)
        self._grid = make_m37_proxy_carrier_grid(
            M37_COMPLETENESS_BACKGROUND_WINDOW
        )
        self._cache_provenance: dict[
            int, tuple[tuple[str, ...], tuple[str, ...]]
        ] = {}
        self._pending_cache_provenance: dict[
            int, dict[str, tuple[str, str]]
        ] = {}
        self._epoch_products: dict[tuple[int, int], str] = {}
        self._mask_products: dict[int, str] = {}
        self._invalid = False
        self._sealed = False
        basis = injected.scans[0].factor_basis
        factor_table = injected.scans[0].factor_table
        self._base_live_native_bytes = (
            sum(
                scan.normalized.nbytes
                for scan in injected.background.scans
            )
            + sum(scan.normalized.nbytes for scan in injected.scans)
            + sum(
                scan.truth_factors.nbytes
                for scan in injected.background.scans
            )
            + basis.times_mjd.nbytes
            + basis.baseline.nbytes
            + basis.orbital.nbytes
            + factor_table.factors.nbytes
            # score_hz/score_mhz are views of these two support owners.
            + self._grid.support_hz.nbytes
            + self._grid.support_mhz.nbytes
        )
        self._maximum_live_native_bytes_observed = (
            self._base_live_native_bytes
        )
        if self._base_live_native_bytes > (
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        ):
            raise V0P6CapacityError(
                "mask replay starts above the native live-byte cap"
            )

    def _fail(self, message: str) -> None:
        self._invalid = True
        raise V0P6IncompleteError(message)

    def add_native_filter_cache(
        self,
        width_channels: int,
        scan_label: str,
        cache: Any,
    ) -> None:
        """Validate and forget one scan/width injected native cache."""
        if self._invalid:
            raise V0P6IncompleteError("M37 mask-replay ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("M37 mask-replay ledger is sealed")
        try:
            width = core._strict_widths((width_channels,))[0]
            if width not in M37_SPECTRAL_WIDTHS:
                self._fail("mask replay received an unknown spectral width")
            width_index = M37_SPECTRAL_WIDTHS.index(width)
            label = str(scan_label)
            if label not in self._on_labels:
                self._fail("mask replay cache has an unknown ON label")
            pending = self._pending_cache_provenance.setdefault(
                width_index, {}
            )
            if width_index in self._cache_provenance or label in pending:
                self._fail("mask replay repeated a native cache")
            injected_by_label = {
                scan.scan_label: scan for scan in self.injected.scans
            }
            plan, values = core._cache_values_for_gather(cache)
            scan = injected_by_label[label]
            expected_plan = core.plan_m37_native_filter_cache(
                scan.geometry,
                scan.factor_basis,
                scan.factor_table,
                self.scan_definitions,
                self._grid,
                width,
                window_id=M37_COMPLETENESS_BACKGROUND_WINDOW,
                scan_label=label,
                source_sha256=scan.normalized_sha256,
            )
            if plan != expected_plan:
                self._fail("native-cache plan differs from the injection")
            chunk_centers = 32_768
            half = width // 2
            scratch_bytes = 4 * (chunk_centers + 2 * half) * 4
            live_bytes = (
                self._base_live_native_bytes
                + values.nbytes
                + scratch_bytes
            )
            self._maximum_live_native_bytes_observed = max(
                self._maximum_live_native_bytes_observed, live_bytes
            )
            if live_bytes > M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL:
                raise V0P6CapacityError(
                    "mask-replay native-cache live-byte cap exceeded"
                )
            reproduced_digest = hashlib.sha256()
            for row in range(plan.integration_count):
                for local_start in range(
                    0, values.shape[1], chunk_centers
                ):
                    local_stop = min(
                        local_start + chunk_centers, values.shape[1]
                    )
                    raw_start = plan.raw_center_start + local_start
                    raw_stop = plan.raw_center_start + local_stop
                    source = scan.normalized[
                        row : row + 1,
                        raw_start - half : raw_stop + half,
                    ]
                    filtered = normalized_boxcar(source, width)
                    if half:
                        reproduced = np.asarray(
                            filtered[0, half:-half], dtype="<f4"
                        )
                    else:
                        reproduced = np.asarray(filtered[0], dtype="<f4")
                    observed = values[row, local_start:local_stop]
                    if not np.array_equal(reproduced, observed):
                        self._fail(
                            "native-cache bits do not reproduce from injection"
                        )
                    reproduced_digest.update(
                        np.ascontiguousarray(reproduced, dtype="<f4").tobytes()
                    )
            if reproduced_digest.hexdigest() != cache.payload_sha256:
                self._fail("native-cache payload digest changed")
            pending[label] = (plan.plan_sha256, cache.payload_sha256)
            if set(pending) == set(self._on_labels):
                self._cache_provenance[width_index] = (
                    tuple(pending[item][0] for item in self._on_labels),
                    tuple(pending[item][1] for item in self._on_labels),
                )
                self._pending_cache_provenance.pop(width_index, None)
        except (V0P6CapacityError, V0P6ContractError, V0P6IncompleteError):
            self._invalid = True
            raise

    def add_template_mask(
        self,
        template_index: int,
        epoch_products_by_width: Mapping[int, core.EpochVectorProduct],
        mask_product: core.MaskProduct,
    ) -> None:
        """Validate one template's eight products and exact width-OR mask."""
        if self._invalid:
            raise V0P6IncompleteError("M37 mask-replay ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("M37 mask-replay ledger is sealed")
        try:
            template = _strict_int(template_index, "mask template index")
            if not 0 <= template < M37_TEMPLATE_COUNT:
                self._fail("mask replay template index is out of range")
            if template in self._mask_products:
                self._fail("mask replay repeated a template mask")
            if set(epoch_products_by_width) != set(M37_SPECTRAL_WIDTHS):
                self._fail("mask replay omitted an epoch-product width")
            if set(self._cache_provenance) != set(
                range(len(M37_SPECTRAL_WIDTHS))
            ):
                self._fail("mask replay must validate all caches first")
            ordered: list[core.EpochVectorProduct] = []
            for width_index, width in enumerate(M37_SPECTRAL_WIDTHS):
                product = epoch_products_by_width[width]
                core.validate_epoch_vector_product(product)
                plans, payloads = self._cache_provenance[width_index]
                if (
                    product.window_id != M37_COMPLETENESS_BACKGROUND_WINDOW
                    or product.scan_kind != "on"
                    or product.template_index != template
                    or product.width_channels != width
                    or product.proxy_grid_sha256
                    != core.proxy_carrier_grid_sha256(self._grid)
                    or product.factor_basis_sha256
                    != M37_FACTOR_BASIS_SHA256
                    or product.factor_basis_labels_sha256
                    != M37_FACTOR_BASIS_LABELS_SHA256
                    or product.factor_row_selection_sha256
                    != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
                    or product.template_bank_sha256 != M37_BANK_SHA256
                    or product.factor_table_sha256
                    != self.injected.scans[0].factor_table_sha256
                    or product.cache_plan_sha256s != plans
                    or product.cache_payload_sha256s != payloads
                ):
                    self._fail(
                        "epoch product does not descend from injected caches"
                    )
                self._epoch_products[(template, width_index)] = (
                    product.product_sha256
                )
                ordered.append(product)
            core.validate_mask_product(mask_product)
            live_bytes = _template_mask_replay_live_bytes(
                self._base_live_native_bytes,
                tuple(item.values.nbytes for item in ordered),
                mask_product.values.nbytes,
            )
            self._maximum_live_native_bytes_observed = max(
                self._maximum_live_native_bytes_observed, live_bytes
            )
            if live_bytes > (
                M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
            ):
                raise V0P6CapacityError(
                    "mask-replay template-product live-byte cap exceeded"
                )
            expected_values = core.build_m37_two_pass_template_mask(
                lambda width: epoch_products_by_width[width].values
            )
            if (
                mask_product.window_id != M37_COMPLETENESS_BACKGROUND_WINDOW
                or mask_product.scan_kind != "on"
                or mask_product.template_index != template
                or mask_product.factor_table_sha256
                != self.injected.scans[0].factor_table_sha256
                or mask_product.source_epoch_product_sha256s
                != tuple(item.product_sha256 for item in ordered)
                or not np.array_equal(mask_product.values, expected_values)
            ):
                self._fail(
                    "mask product does not reproduce from all eight widths"
                )
            self._mask_products[template] = mask_product.product_sha256
        except (V0P6CapacityError, V0P6ContractError, V0P6IncompleteError):
            self._invalid = True
            raise

    def finalize(self) -> MaskReplayReceipt:
        if self._invalid:
            raise V0P6IncompleteError("M37 mask-replay ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("M37 mask-replay ledger is sealed")
        if self._pending_cache_provenance or set(self._cache_provenance) != set(
            range(len(M37_SPECTRAL_WIDTHS))
        ) or set(self._mask_products) != set(range(M37_TEMPLATE_COUNT)):
            self._invalid = True
            raise V0P6IncompleteError("M37 mask replay is incomplete")
        expected_epoch_keys = {
            (template, width)
            for template in range(M37_TEMPLATE_COUNT)
            for width in range(len(M37_SPECTRAL_WIDTHS))
        }
        if set(self._epoch_products) != expected_epoch_keys:
            self._invalid = True
            raise V0P6IncompleteError(
                "M37 epoch-product replay inventory is incomplete"
            )
        self._sealed = True
        receipt = _attest_mask_replay_receipt(
            MaskReplayReceipt(
                trial_id=self.injected.trial_id,
                source_injected_native_sha256=(
                    self.injected.injected_native_sha256
                ),
                source_kind="m37-live-mask-product-replay-v1",
                mask_inventory_sha256=core._mask_product_inventory_sha256(
                    self._mask_products
                ),
                epoch_product_inventory_sha256=(
                    core._epoch_product_inventory_sha256(
                        self._epoch_products
                    )
                ),
                cache_provenance_inventory_sha256=(
                    core._cache_provenance_inventory_sha256(
                        self._cache_provenance
                    )
                ),
                injected_scan_sha256s=tuple(
                    scan.scan_sha256 for scan in self.injected.scans
                ),
                native_filter_cache_count=(
                    len(M37_SPECTRAL_WIDTHS) * 3
                ),
                maximum_live_native_bytes_observed=(
                    self._maximum_live_native_bytes_observed
                ),
                maximum_live_native_bytes_per_trial=(
                    M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
                ),
                source_epoch_product_count=len(self._epoch_products),
                template_mask_count=len(self._mask_products),
                recomputed_after_injection=True,
                receipt_sha256="",
            )
        )
        validate_mask_replay_receipt(receipt, self.injected)
        return receipt


def seal_mask_replay_receipt(
    replay: M37MaskReplayLedger,
) -> MaskReplayReceipt:
    """Finalize a streaming replay; free mask hashes are not accepted."""
    if not isinstance(replay, M37MaskReplayLedger):
        raise V0P6ContractError(
            "mask receipt requires a factory M37 mask-replay ledger"
        )
    return replay.finalize()


def make_synthetic_mask_replay_receipt(
    injected: InjectedNativeTrial,
    trial: CompletenessTrial,
) -> MaskReplayReceipt:
    """Derive a small explicit non-production known-answer receipt."""
    validate_injected_native_trial(injected, trial)
    source = {
        "artifact_type": "synthetic-known-answer-mask-replay-v1",
        "trial_id": trial.trial_id,
        "injected_native_sha256": injected.injected_native_sha256,
        "scan_sha256s": [scan.scan_sha256 for scan in injected.scans],
        "mask_rule": "deterministic-test-adapter-no-free-input-hashes",
    }
    source_sha = _sha256(source)
    return _attest_mask_replay_receipt(
        MaskReplayReceipt(
            trial_id=trial.trial_id,
            source_injected_native_sha256=injected.injected_native_sha256,
            source_kind="synthetic-known-answer-derived-mask-replay-v1",
            mask_inventory_sha256=_sha256(["mask", source_sha]),
            epoch_product_inventory_sha256=_sha256(["epoch", source_sha]),
            cache_provenance_inventory_sha256=_sha256(["cache", source_sha]),
            injected_scan_sha256s=tuple(
                scan.scan_sha256 for scan in injected.scans
            ),
            native_filter_cache_count=len(M37_SPECTRAL_WIDTHS) * 3,
            maximum_live_native_bytes_observed=sum(
                scan.normalized.nbytes
                for scan in (*injected.background.scans, *injected.scans)
            ),
            maximum_live_native_bytes_per_trial=(
                M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
            ),
            source_epoch_product_count=(
                M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS
            ),
            template_mask_count=M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS,
            recomputed_after_injection=True,
            receipt_sha256="",
        )
    )


def validate_mask_replay_receipt(
    receipt: MaskReplayReceipt,
    injected: InjectedNativeTrial,
    *,
    expected_receipt_sha256: str | None = None,
) -> None:
    if not isinstance(receipt, MaskReplayReceipt):
        raise V0P6ContractError("mask replay receipt has an invalid type")
    observed_live_bytes = _strict_int(
        receipt.maximum_live_native_bytes_observed,
        "mask-replay maximum live native bytes",
    )
    live_byte_cap = _strict_int(
        receipt.maximum_live_native_bytes_per_trial,
        "mask-replay live-native-byte cap",
    )
    retained_native_bytes = sum(
        scan.normalized.nbytes
        for scan in (*injected.background.scans, *injected.scans)
    )
    if (
        receipt.trial_id != injected.trial_id
        or receipt.source_injected_native_sha256
        != injected.injected_native_sha256
        or receipt.source_epoch_product_count
        != M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS
        or receipt.native_filter_cache_count != len(M37_SPECTRAL_WIDTHS) * 3
        or receipt.template_mask_count
        != M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS
        or receipt.recomputed_after_injection is not True
        or receipt.injected_scan_sha256s
        != tuple(scan.scan_sha256 for scan in injected.scans)
        or live_byte_cap
        != M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        or observed_live_bytes < retained_native_bytes
        or observed_live_bytes > live_byte_cap
        or receipt.source_kind not in {
            "m37-live-mask-product-replay-v1",
            "synthetic-known-answer-derived-mask-replay-v1",
        }
    ):
        raise V0P6IncompleteError(
            "two-pass mask replay is incomplete or bound to another injection"
        )
    for value, label in (
        (receipt.mask_inventory_sha256, "mask-inventory identity"),
        (
            receipt.epoch_product_inventory_sha256,
            "epoch-product inventory identity",
        ),
        (
            receipt.cache_provenance_inventory_sha256,
            "cache-provenance inventory identity",
        ),
    ):
        _frozen_sha256(value, label)
    if receipt.receipt_sha256 != _sha256(
        receipt.as_record(include_identity=False)
    ):
        raise V0P6IncompleteError("mask replay receipt changed")
    expected = (
        None
        if expected_receipt_sha256 is None
        else _frozen_sha256(
            expected_receipt_sha256, "expected mask-replay receipt identity"
        )
    )
    live = _MASK_REPLAY_RECEIPT_ATTESTATIONS.get(receipt.receipt_sha256) == (
        canonical_json_bytes(receipt.as_record())
    )
    if not live and expected != receipt.receipt_sha256:
        raise V0P6ContractError(
            "mask replay lacks a live or independently trusted receipt"
        )


@dataclass(frozen=True)
class TrialEvaluation:
    """Artifact-derived detector, physical-veto, and rank-p outcome."""

    trial_id: str
    injected_native_sha256: str
    mask_replay_receipt_sha256: str
    threshold_identity_sha256: str
    source_kind: str
    best_truth_associated_snr: float | None
    truth_match_maximum_track_distance_hz: float | None
    detector_passed: bool
    truth_matched: bool
    physical_vetoed: bool
    physical_disposition: str | None
    inclusive_global_rank_p: float | None
    scientifically_eligible: bool | None
    recovered: bool
    final_disposition: str
    selected_record_id: str | None
    selected_template_index: int | None
    selected_spectral_width_index: int | None
    selected_activity_subset_index: int | None
    selected_proxy_carrier_index: int | None
    detector_record_count: int
    detector_score_cells_replayed: int
    disposition_evidence_canonical_bytes: int
    detector_receipt_sha256: str
    disposition_receipt_sha256: str
    significance_result_sha256: str
    evaluation_sha256: str

    def as_record(self, *, include_identity: bool = True) -> dict[str, Any]:
        record = {
            "trial_id": self.trial_id,
            "injected_native_sha256": self.injected_native_sha256,
            "mask_replay_receipt_sha256": self.mask_replay_receipt_sha256,
            "threshold_identity_sha256": self.threshold_identity_sha256,
            "source_kind": self.source_kind,
            "best_truth_associated_snr": self.best_truth_associated_snr,
            "truth_match_maximum_track_distance_hz": (
                self.truth_match_maximum_track_distance_hz
            ),
            "detector_passed": self.detector_passed,
            "truth_matched": self.truth_matched,
            "physical_vetoed": self.physical_vetoed,
            "physical_disposition": self.physical_disposition,
            "inclusive_global_rank_p": self.inclusive_global_rank_p,
            "scientifically_eligible": self.scientifically_eligible,
            "recovered": self.recovered,
            "final_disposition": self.final_disposition,
            "selected_record_id": self.selected_record_id,
            "selected_template_index": self.selected_template_index,
            "selected_spectral_width_index": (
                self.selected_spectral_width_index
            ),
            "selected_activity_subset_index": (
                self.selected_activity_subset_index
            ),
            "selected_proxy_carrier_index": self.selected_proxy_carrier_index,
            "detector_record_count": self.detector_record_count,
            "detector_score_cells_replayed": (
                self.detector_score_cells_replayed
            ),
            "disposition_evidence_canonical_bytes": (
                self.disposition_evidence_canonical_bytes
            ),
            "detector_receipt_sha256": self.detector_receipt_sha256,
            "disposition_receipt_sha256": self.disposition_receipt_sha256,
            "significance_result_sha256": self.significance_result_sha256,
            "recovery_rule": (
                "retained-track-distance<=20Hz AND no-physical-veto AND "
                "separate-global-rank-p-eligible"
            ),
        }
        if include_identity:
            record["evaluation_sha256"] = self.evaluation_sha256
        return record


_TRIAL_EVALUATION_ATTESTATIONS: dict[str, bytes] = {}
_TRIAL_EVALUATION_ATTESTATION_CAP = 8_192


def _attest_trial_evaluation(partial: TrialEvaluation) -> TrialEvaluation:
    evaluation = replace(
        partial,
        evaluation_sha256=_sha256(
            partial.as_record(include_identity=False)
        ),
    )
    encoded = canonical_json_bytes(evaluation.as_record())
    existing = _TRIAL_EVALUATION_ATTESTATIONS.get(
        evaluation.evaluation_sha256
    )
    if existing is not None and existing != encoded:
        raise V0P6IncompleteError("trial-evaluation digest collision")
    if existing is None and len(_TRIAL_EVALUATION_ATTESTATIONS) >= (
        _TRIAL_EVALUATION_ATTESTATION_CAP
    ):
        raise V0P6CapacityError("trial-evaluation attestation cap exceeded")
    _TRIAL_EVALUATION_ATTESTATIONS[evaluation.evaluation_sha256] = encoded
    return evaluation


def _derive_trial_evaluation(
    trial: CompletenessTrial,
    injected: InjectedNativeTrial,
    mask_receipt: MaskReplayReceipt,
    threshold: FrozenOperationalThreshold,
    *,
    source_kind: str,
    selected_record: Mapping[str, Any] | None,
    selected_distance_hz: float | None,
    physical_disposition: str | None,
    rank_p: float | None,
    scientifically_eligible: bool | None,
    detector_record_count: int,
    detector_score_cells_replayed: int,
    disposition_evidence_canonical_bytes: int,
    detector_receipt_sha256: str,
    disposition_receipt_sha256: str,
    significance_result_sha256: str,
) -> TrialEvaluation:
    validate_injected_native_trial(injected, trial)
    validate_mask_replay_receipt(mask_receipt, injected)
    validate_frozen_threshold(threshold)
    record_count = _strict_int(detector_record_count, "detector record count")
    score_cells = _strict_int(
        detector_score_cells_replayed, "detector score-cell count"
    )
    evidence_bytes = _strict_int(
        disposition_evidence_canonical_bytes,
        "disposition evidence byte count",
    )
    if not 0 <= record_count <= M37_COMPLETENESS_MAXIMUM_DETECTOR_RECORDS:
        raise V0P6CapacityError("per-trial detector record cap exceeded")
    if not 0 <= evidence_bytes <= (
        M37_COMPLETENESS_MAXIMUM_DISPOSITION_EVIDENCE_BYTES
    ):
        raise V0P6CapacityError("per-trial disposition evidence cap exceeded")
    if score_cells < 1 or (
        str(source_kind) == "m37-concrete-operational-artifacts-v1"
        and score_cells
        != M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
    ):
        raise V0P6IncompleteError(
            "detector score-cell replay accounting is incomplete"
        )
    if selected_record is None:
        if any(
            item is not None
            for item in (
                selected_distance_hz,
                physical_disposition,
                rank_p,
                scientifically_eligible,
            )
        ):
            raise V0P6ContractError(
                "unmatched trial has invented downstream evidence"
            )
        score = None
        distance = None
        selected_id = None
        selected = (None, None, None, None)
        physical_vetoed = False
        disposition = "below_operational_threshold"
        recovered = False
    else:
        record = json.loads(canonical_json_bytes(dict(selected_record)))
        score = float(record["snr"])
        distance = float(selected_distance_hz)
        if (
            not math.isfinite(score)
            or score < threshold.operational_threshold_snr
            or not math.isfinite(distance)
            or not 0.0 <= distance
            <= M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ
        ):
            raise V0P6ContractError(
                "selected retained record does not satisfy recovery association"
            )
        selected_id = _frozen_sha256(
            record["record_id"], "selected retained-record identity"
        )
        try:
            activity_index = M37_ACTIVITY_SUBSETS.index(
                tuple(
                    _strict_int(item, "selected activity epoch")
                    for item in record["active_epochs_zero_based"]
                )
            )
        except (KeyError, ValueError) as error:
            raise V0P6ContractError(
                "selected record has an unknown activity subset"
            ) from error
        selected = (
            _strict_int(record["template_index"], "selected template_index"),
            _strict_int(
                record["spectral_width_index"],
                "selected spectral_width_index",
            ),
            activity_index,
            _strict_int(
                record["proxy_carrier_index"],
                "selected proxy_carrier_index",
            ),
        )
        if (
            not 0 <= selected[0] < M37_TEMPLATE_COUNT
            or not 0 <= selected[1] < len(M37_SPECTRAL_WIDTHS)
            or not 0 <= selected[2] < len(M37_ACTIVITY_SUBSETS)
            or not 0 <= selected[3] < 2 * M37_SCORE_HALF_BINS + 1
        ):
            raise V0P6ContractError("selected hypothesis identity is out of range")
        physical = str(physical_disposition)
        physical_vetoed = physical.startswith("rfi_veto_")
        if not isinstance(scientifically_eligible, bool):
            raise V0P6ContractError(
                "matched trial lacks separate rank-p eligibility evidence"
            )
        p_value = float(rank_p)
        if not math.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            raise V0P6ContractError("matched trial rank-p is invalid")
        if physical_vetoed:
            disposition = physical
        elif scientifically_eligible:
            disposition = "scientific_candidate_unresolved"
        else:
            disposition = "retained_but_not_scientifically_eligible"
        recovered = bool(not physical_vetoed and scientifically_eligible)
        physical_disposition = physical
        rank_p = p_value
    partial = TrialEvaluation(
        trial_id=trial.trial_id,
        injected_native_sha256=injected.injected_native_sha256,
        mask_replay_receipt_sha256=mask_receipt.receipt_sha256,
        threshold_identity_sha256=threshold.threshold_identity_sha256,
        source_kind=str(source_kind),
        best_truth_associated_snr=score,
        truth_match_maximum_track_distance_hz=distance,
        detector_passed=selected_record is not None,
        truth_matched=selected_record is not None,
        physical_vetoed=physical_vetoed,
        physical_disposition=physical_disposition,
        inclusive_global_rank_p=rank_p,
        scientifically_eligible=scientifically_eligible,
        recovered=recovered,
        final_disposition=disposition,
        selected_record_id=selected_id,
        selected_template_index=selected[0],
        selected_spectral_width_index=selected[1],
        selected_activity_subset_index=selected[2],
        selected_proxy_carrier_index=selected[3],
        detector_record_count=record_count,
        detector_score_cells_replayed=score_cells,
        disposition_evidence_canonical_bytes=evidence_bytes,
        detector_receipt_sha256=_frozen_sha256(
            detector_receipt_sha256, "detector replay identity"
        ),
        disposition_receipt_sha256=_frozen_sha256(
            disposition_receipt_sha256, "physical-disposition identity"
        ),
        significance_result_sha256=_frozen_sha256(
            significance_result_sha256, "rank-p result identity"
        ),
        evaluation_sha256="",
    )
    return _attest_trial_evaluation(partial)


def seal_trial_evaluation(
    trial: CompletenessTrial,
    injected: InjectedNativeTrial,
    mask_receipt: MaskReplayReceipt,
    threshold: FrozenOperationalThreshold,
    *,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    receiver_alias_records: Sequence[Mapping[str, Any]],
    receiver_alias_certificate: Mapping[str, Any],
    significance_result: Mapping[str, Any],
    threshold_certificate: ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    expected_on_certificate_sha256: str | None = None,
    expected_alias_certificate_sha256: str | None = None,
    expected_significance_result_sha256: str | None = None,
    expected_threshold_certificate_sha256: str | None = None,
) -> TrialEvaluation:
    """Derive recovery from concrete production artifacts, never free fields."""
    from .alias_v0p6 import validate_receiver_alias_result
    from .significance_v0p6 import validate_m37_global_rank_significance

    validate_injected_native_trial(injected, trial)
    validate_mask_replay_receipt(mask_receipt, injected)
    core.validate_threshold_certificate(
        threshold_certificate,
        expected_certificate_sha256=expected_threshold_certificate_sha256,
    )
    if freeze_m37_operational_threshold(threshold_certificate) != threshold:
        raise V0P6ContractError(
            "evaluation threshold differs from the M37 threshold artifact"
        )
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    retained = core._validated_retained_records(
        on_records,
        cert,
        grid,
        expected_kind="on",
        expected_template_count=M37_TEMPLATE_COUNT,
        template_bank=make_line_template_bank(),
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if (
        cert["window_id"] != M37_COMPLETENESS_BACKGROUND_WINDOW
        or cert["threshold_certificate_sha256"]
        != threshold_certificate.certificate_sha256
        or cert["factor_table_sha256"] != threshold.factor_table_sha256
        or cert["mask_product_inventory_sha256"]
        != mask_receipt.mask_inventory_sha256
        or cert["epoch_product_inventory_sha256"]
        != mask_receipt.epoch_product_inventory_sha256
        or cert["cache_provenance_inventory_sha256"]
        != mask_receipt.cache_provenance_inventory_sha256
        or mask_receipt.source_kind != "m37-live-mask-product-replay-v1"
    ):
        raise V0P6IncompleteError(
            "retention does not consume the attested injected mask replay"
        )
    try:
        detached_alias_records = json.loads(
            canonical_json_bytes(list(receiver_alias_records))
        )
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(
            "receiver-alias records are not canonical finite JSON"
        ) from error
    alias_cert = validate_receiver_alias_result(
        detached_alias_records,
        receiver_alias_certificate,
        expected_certificate_sha256=expected_alias_certificate_sha256,
    )
    significance = validate_m37_global_rank_significance(
        significance_result,
        retained,
        cert,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        expected_result_sha256=expected_significance_result_sha256,
    )
    if (
        alias_cert["window_id"] != M37_COMPLETENESS_BACKGROUND_WINDOW
        or alias_cert["on_retention_certificate_sha256"]
        != cert["retention_certificate_sha256"]
        or significance["certificate"]["retention_certificate_sha256"]
        != cert["retention_certificate_sha256"]
    ):
        raise V0P6IncompleteError(
            "physical/rank-p artifacts belong to another retention replay"
        )
    alias_by_id = {
        str(record["record_id"]): record for record in detached_alias_records
    }
    rank_by_id = {
        str(item["record_id"]): item for item in significance["evidence"]
    }
    retained_ids = {str(record["record_id"]) for record in retained}
    if set(alias_by_id) != retained_ids or set(rank_by_id) != retained_ids:
        raise V0P6IncompleteError(
            "physical/rank-p evidence does not cover retention exactly once"
        )
    factor_table = injected.scans[0].factor_table
    factor_basis = injected.scans[0].factor_basis
    candidate_factors = np.concatenate(
        [
            core.factor_table_for_scan(
                factor_table, factor_basis, scan.scan_label
            )
            for scan in injected.scans
        ],
        axis=1,
    )
    truth_factors = np.concatenate(
        [scan.truth_factors for scan in injected.scans]
    )
    matches: list[tuple[float, float, str, dict[str, Any]]] = []
    for record in retained:
        template_index = _strict_int(
            record["template_index"], "retained template index"
        )
        q_hz = float(record["proxy_carrier_hz"])
        distance = float(
            np.max(
                np.abs(
                    q_hz * candidate_factors[template_index]
                    - trial.truth.proxy_carrier_hz * truth_factors
                )
            )
        )
        if distance <= M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ:
            matches.append(
                (-float(record["snr"]), distance, str(record["record_id"]), record)
            )
    matches.sort(key=lambda item: (item[0], item[1], item[2]))
    selected_record = None if not matches else matches[0][3]
    selected_distance = None if not matches else matches[0][1]
    if selected_record is None:
        physical = None
        rank_p = None
        eligible = None
    else:
        record_id = str(selected_record["record_id"])
        physical = str(alias_by_id[record_id]["member_disposition"])
        rank_p = float(rank_by_id[record_id]["inclusive_global_rank_p"])
        eligible = bool(rank_by_id[record_id]["scientifically_eligible"])
    evidence_bytes = (
        0
        if selected_record is None
        else len(canonical_json_bytes(alias_by_id[str(selected_record["record_id"])]))
        + len(canonical_json_bytes(rank_by_id[str(selected_record["record_id"])]))
    )
    return _derive_trial_evaluation(
        trial,
        injected,
        mask_receipt,
        threshold,
        source_kind="m37-concrete-operational-artifacts-v1",
        selected_record=selected_record,
        selected_distance_hz=selected_distance,
        physical_disposition=physical,
        rank_p=rank_p,
        scientifically_eligible=eligible,
        detector_record_count=len(retained),
        detector_score_cells_replayed=_strict_int(
            cert["score_cells_replayed"], "retention score-cell count"
        ),
        disposition_evidence_canonical_bytes=evidence_bytes,
        detector_receipt_sha256=cert["retention_certificate_sha256"],
        disposition_receipt_sha256=alias_cert[
            "receiver_alias_certificate_sha256"
        ],
        significance_result_sha256=significance["result_sha256"],
    )


def make_synthetic_trial_evaluation(
    trial: CompletenessTrial,
    injected: InjectedNativeTrial,
    mask_receipt: MaskReplayReceipt,
    threshold: FrozenOperationalThreshold,
) -> TrialEvaluation:
    """Derive a deterministic non-production known answer from native bits."""
    validate_injected_native_trial(injected, trial)
    validate_mask_replay_receipt(mask_receipt, injected)
    active = set(trial.truth.active_epochs_zero_based)
    epoch_scores: list[float] = []
    for scan in injected.scans:
        if scan.epoch_index not in active:
            continue
        observed = np.asarray(
            trial.truth.proxy_carrier_hz * scan.truth_factors,
            dtype=np.float64,
        )
        centers = np.rint(
            (observed - scan.geometry.raw_zero_hz)
            / scan.geometry.channel_width_hz
        ).astype(np.int64)
        filtered = normalized_boxcar(
            scan.normalized, trial.truth.spectral_width_channels
        )
        accumulator = np.float32(0.0)
        for row, center in enumerate(centers):
            accumulator = np.float32(
                accumulator + np.float32(filtered[row, center])
            )
        epoch_scores.append(
            float(accumulator / np.float32(math.sqrt(filtered.shape[0])))
        )
    score = min(epoch_scores)
    selected: dict[str, Any] | None
    if score >= threshold.operational_threshold_snr:
        selected = {
            "record_id": _sha256(
                {
                    "trial_id": trial.trial_id,
                    "synthetic_record": True,
                }
            ),
            "snr": score,
            "template_index": trial.truth.template_index,
            "spectral_width_index": trial.truth.spectral_width_index,
            "active_epochs_zero_based": list(
                trial.truth.active_epochs_zero_based
            ),
            "proxy_carrier_index": trial.truth.proxy_carrier_index,
        }
        distance = 0.0
        physical = "pending_receiver_alias_evaluation"
        rank_p = 1.0 / (M37_SCRAMBLE_COUNT + 1.0)
        eligible = rank_p <= M37_SCIENTIFIC_P_CEILING
    else:
        selected = None
        distance = None
        physical = None
        rank_p = None
        eligible = None
    source_sha = _sha256(
        {
            "trial_id": trial.trial_id,
            "injected_native_sha256": injected.injected_native_sha256,
            "mask_replay_receipt_sha256": mask_receipt.receipt_sha256,
            "score": score,
        }
    )
    return _derive_trial_evaluation(
        trial,
        injected,
        mask_receipt,
        threshold,
        source_kind="synthetic-known-answer-native-replay-v1",
        selected_record=selected,
        selected_distance_hz=distance,
        physical_disposition=physical,
        rank_p=rank_p,
        scientifically_eligible=eligible,
        detector_record_count=int(selected is not None),
        detector_score_cells_replayed=1,
        disposition_evidence_canonical_bytes=0,
        detector_receipt_sha256=_sha256(["detector", source_sha]),
        disposition_receipt_sha256=_sha256(["physical", source_sha]),
        significance_result_sha256=_sha256(["rank-p", source_sha]),
    )


def validate_trial_evaluation(
    evaluation: TrialEvaluation,
    trial: CompletenessTrial,
    injected: InjectedNativeTrial,
    mask_receipt: MaskReplayReceipt,
    threshold: FrozenOperationalThreshold,
    *,
    expected_evaluation_sha256: str | None = None,
) -> None:
    if not isinstance(evaluation, TrialEvaluation):
        raise V0P6ContractError("trial evaluation has an invalid type")
    if (
        evaluation.trial_id != trial.trial_id
        or evaluation.injected_native_sha256 != injected.injected_native_sha256
        or evaluation.mask_replay_receipt_sha256 != mask_receipt.receipt_sha256
        or evaluation.threshold_identity_sha256
        != threshold.threshold_identity_sha256
        or evaluation.evaluation_sha256
        != _sha256(evaluation.as_record(include_identity=False))
    ):
        raise V0P6IncompleteError("trial evaluation identity changed")
    expected_digest = (
        None
        if expected_evaluation_sha256 is None
        else _frozen_sha256(
            expected_evaluation_sha256,
            "expected trial-evaluation identity",
        )
    )
    live = _TRIAL_EVALUATION_ATTESTATIONS.get(
        evaluation.evaluation_sha256
    ) == canonical_json_bytes(evaluation.as_record())
    if not live and expected_digest != evaluation.evaluation_sha256:
        raise V0P6ContractError(
            "trial evaluation lacks a live or independently trusted receipt"
        )
    if evaluation.source_kind not in {
        "m37-concrete-operational-artifacts-v1",
        "synthetic-known-answer-native-replay-v1",
    }:
        raise V0P6ContractError("trial evaluation source kind changed")
    matched = evaluation.selected_record_id is not None
    if (
        evaluation.detector_passed is not matched
        or evaluation.truth_matched is not matched
        or (evaluation.final_disposition.startswith("rfi_veto_"))
        is not evaluation.physical_vetoed
        or evaluation.recovered
        is not bool(
            matched
            and not evaluation.physical_vetoed
            and evaluation.scientifically_eligible is True
        )
    ):
        raise V0P6IncompleteError("trial evaluation semantics changed")
    for digest, label in (
        (evaluation.detector_receipt_sha256, "detector receipt"),
        (evaluation.disposition_receipt_sha256, "physical receipt"),
        (evaluation.significance_result_sha256, "rank-p receipt"),
    ):
        _frozen_sha256(digest, label)


class CompletenessDataSource(Protocol):
    def load_background(self, trial: CompletenessTrial) -> NativeTrialBackground:
        """Return a seed-bound, complete three-ON-scan background."""


class CompletenessOperationalPipeline(Protocol):
    def recompute_two_pass_masks(
        self,
        injected: InjectedNativeTrial,
        trial: CompletenessTrial,
    ) -> MaskReplayReceipt:
        """Recompute all first-pass products/masks after native injection."""

    def evaluate_exact_operational_pipeline(
        self,
        injected: InjectedNativeTrial,
        masks: MaskReplayReceipt,
        threshold: FrozenOperationalThreshold,
        trial: CompletenessTrial,
    ) -> TrialEvaluation:
        """Run the exact detector and every physical disposition pass."""


def wilson_interval_95(successes: int, total: int) -> tuple[float, float]:
    successes = _strict_int(successes, "Wilson success count")
    total = _strict_int(total, "Wilson trial count")
    if total < 1 or not 0 <= successes <= total:
        raise V0P6ContractError("Wilson counts are invalid")
    z = M37_COMPLETENESS_WILSON_Z_95
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def _threshold_crossing_summary(
    levels: Sequence[Mapping[str, Any]], target: float, field_name: str
) -> dict[str, Any]:
    prior: float | None = None
    for level in levels:
        if float(level[field_name]) >= target:
            return {
                "target_recovery_fraction": target,
                "criterion": field_name,
                "reached": True,
                "previous_tested_snr": prior,
                "first_tested_snr_at_or_above_target": float(
                    level["ideal_single_epoch_snr"]
                ),
                "observed_fraction_at_crossing": float(
                    level["recovery_fraction"]
                ),
                "wilson_lower_at_crossing": float(
                    level["wilson_95_interval"][0]
                ),
                "interpolation_permitted": False,
            }
        prior = float(level["ideal_single_epoch_snr"])
    return {
        "target_recovery_fraction": target,
        "criterion": field_name,
        "reached": False,
        "previous_tested_snr": prior,
        "first_tested_snr_at_or_above_target": None,
        "observed_fraction_at_crossing": None,
        "wilson_lower_at_crossing": None,
        "interpolation_permitted": False,
    }


class CompletenessLedger:
    """Exhaustive per-trial ledger; any duplicate/cap failure poisons it."""

    def __init__(
        self,
        plan: CompletenessPlan,
        threshold: FrozenOperationalThreshold,
    ) -> None:
        validate_m37_completeness_plan(plan)
        validate_frozen_threshold(threshold)
        self.plan = plan
        self.threshold = threshold
        self._expected = {
            trial.trial_id: trial for trial in iter_m37_completeness_trials(plan)
        }
        if len(self._expected) != plan.expected_trial_count:
            raise V0P6IncompleteError("expected trial IDs are not unique")
        self._records: dict[str, dict[str, Any]] = {}
        self._canonical_bytes = 0
        self._invalid = False
        self._sealed = False

    def _fail(self, message: str, error_type: type[Exception]) -> None:
        self._invalid = True
        raise error_type(message)

    def add_trial(
        self,
        trial: CompletenessTrial,
        background: NativeTrialBackground,
        injected: InjectedNativeTrial,
        mask_receipt: MaskReplayReceipt,
        evaluation: TrialEvaluation,
    ) -> None:
        if self._invalid:
            raise V0P6IncompleteError("completeness ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("completeness ledger is sealed")
        try:
            expected = self._expected.get(trial.trial_id)
            if expected is None or trial != expected:
                self._fail(
                    "trial is outside the prospective inventory",
                    V0P6IncompleteError,
                )
            if trial.trial_id in self._records:
                self._fail("duplicate completeness trial", V0P6IncompleteError)
            validate_native_trial_background(background, trial)
            if background.factor_table_sha256 != self.threshold.factor_table_sha256:
                self._fail(
                    "background factor table differs from the frozen threshold",
                    V0P6ContractError,
                )
            if self.threshold.source_kind == (
                "m37-factory-attested-threshold-certificate"
            ) and (
                background.source_kind
                != "m37-factory-normalized-seed-selected-background-v1"
                or background.scan_inventory_sha256
                != M37_SCAN_INVENTORY_SHA256
                or background.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
                or background.factor_basis_labels_sha256
                != M37_FACTOR_BASIS_LABELS_SHA256
                or background.template_bank_sha256 != M37_BANK_SHA256
            ):
                self._fail(
                    "production background lacks canonical M37 factor provenance",
                    V0P6ContractError,
                )
            validate_injected_native_trial(injected, trial)
            if injected.background_sha256 != background.background_sha256:
                self._fail(
                    "injection is bound to another background",
                    V0P6IncompleteError,
                )
            validate_mask_replay_receipt(mask_receipt, injected)
            validate_trial_evaluation(
                evaluation,
                trial,
                injected,
                mask_receipt,
                self.threshold,
            )
            if self.threshold.source_kind == (
                "m37-factory-attested-threshold-certificate"
            ) and (
                mask_receipt.source_kind != "m37-live-mask-product-replay-v1"
                or evaluation.source_kind
                != "m37-concrete-operational-artifacts-v1"
            ):
                self._fail(
                    "production trial used synthetic replay evidence",
                    V0P6ContractError,
                )
            record = {
                **trial.as_record(),
                **trial.truth.as_record(),
                "plan_sha256": self.plan.plan_sha256,
                "background_sha256": background.background_sha256,
                "background_context_sha256": background.context_sha256,
                "background_source_kind": background.source_kind,
                "background_source_product_sha256s": list(
                    background.source_product_sha256s
                ),
                "background_noise_shift_channels": list(
                    background.noise_shift_channels
                ),
                "background_noise_selection_sha256": (
                    background.noise_selection_sha256
                ),
                "background_scan_inventory_sha256": (
                    background.scan_inventory_sha256
                ),
                "background_source_working_set_accounting_sha256s": list(
                    background.source_working_set_accounting_sha256s
                ),
                "background_source_working_set_contract_sha256": (
                    background.source_working_set_contract_sha256
                ),
                "background_maximum_live_native_bytes_observed": (
                    background.maximum_live_native_bytes_observed
                ),
                "background_maximum_live_native_bytes_per_trial": (
                    background.maximum_live_native_bytes_per_trial
                ),
                "factor_basis_sha256": background.factor_basis_sha256,
                "factor_basis_labels_sha256": (
                    background.factor_basis_labels_sha256
                ),
                "template_bank_sha256": background.template_bank_sha256,
                "factor_table_sha256": background.factor_table_sha256,
                "background_scan_sha256s": [
                    scan.scan_sha256 for scan in background.scans
                ],
                "injected_native_sha256": injected.injected_native_sha256,
                "injected_scans": [
                    scan.identity_record() for scan in injected.scans
                ],
                "injection_stage": injected.injection_stage,
                "injection_model": injected.injection_model,
                "mask_replay_receipt_sha256": mask_receipt.receipt_sha256,
                "mask_inventory_sha256": mask_receipt.mask_inventory_sha256,
                "epoch_product_inventory_sha256": (
                    mask_receipt.epoch_product_inventory_sha256
                ),
                "cache_provenance_inventory_sha256": (
                    mask_receipt.cache_provenance_inventory_sha256
                ),
                "mask_replay": mask_receipt.as_record(),
                "threshold_identity_sha256": (
                    self.threshold.threshold_identity_sha256
                ),
                "evaluation": evaluation.as_record(),
            }
            record["canonical_bytes"] = 0
            while True:
                encoded_size = len(canonical_json_bytes(record))
                if record["canonical_bytes"] == encoded_size:
                    break
                record["canonical_bytes"] = encoded_size
            if encoded_size > (
                M37_COMPLETENESS_MAXIMUM_TRIAL_RECORD_CANONICAL_BYTES
            ):
                self._fail(
                    "completeness trial record byte cap exceeded",
                    V0P6CapacityError,
                )
            next_total = self._canonical_bytes + encoded_size
            if next_total > M37_COMPLETENESS_MAXIMUM_TOTAL_CANONICAL_BYTES:
                self._fail(
                    "completeness total evidence byte cap exceeded",
                    V0P6CapacityError,
                )
            self._records[trial.trial_id] = json.loads(
                canonical_json_bytes(record)
            )
            self._canonical_bytes = next_total
        except (V0P6CapacityError, V0P6ContractError, V0P6IncompleteError):
            self._invalid = True
            raise

    def finalize(self) -> dict[str, Any]:
        if self._invalid:
            raise V0P6IncompleteError("completeness ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("completeness ledger is already sealed")
        if set(self._records) != set(self._expected):
            self._invalid = True
            missing = len(set(self._expected) - set(self._records))
            raise V0P6IncompleteError(
                f"completeness inventory is incomplete ({missing} trials missing)"
            )
        trials = iter_m37_completeness_trials(self.plan)
        records = [self._records[trial.trial_id] for trial in trials]
        levels: list[dict[str, Any]] = []
        for level_index, snr in enumerate(M37_COMPLETENESS_SNR_GRID):
            level_records = [
                record
                for record in records
                if int(record["level_index"]) == level_index
            ]
            if len(level_records) != M37_COMPLETENESS_TRUTHS_PER_LEVEL:
                self._invalid = True
                raise V0P6IncompleteError("S/N-level inventory is incomplete")
            recovered = sum(
                bool(record["evaluation"]["recovered"])
                for record in level_records
            )
            low, high = wilson_interval_95(recovered, len(level_records))
            levels.append(
                {
                    "level_index": level_index,
                    "ideal_single_epoch_snr": snr,
                    "trials": len(level_records),
                    "recovered": recovered,
                    "recovery_fraction": recovered / len(level_records),
                    "wilson_95_interval": [low, high],
                }
            )
        threshold_summaries = _summaries_for_levels(levels)
        records_digest = _sha256(records)
        detector_score_cells_replayed = sum(
            _strict_int(
                record["evaluation"]["detector_score_cells_replayed"],
                "detector score-cell count",
            )
            for record in records
        )
        production_replay = self.threshold.source_kind == (
            "m37-factory-attested-threshold-certificate"
        )
        if production_replay and detector_score_cells_replayed != (
            M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL
        ):
            self._invalid = True
            raise V0P6IncompleteError(
                "production completeness did not replay every score cell"
            )
        result = {
            "status": M37_COMPLETENESS_STATUS,
            "scientific_status": (
                "prospective-provisional-output-not-yet-preregistered"
            ),
            "plan": self.plan.as_record(),
            "threshold": self.threshold.as_record(),
            "background_window": M37_COMPLETENESS_BACKGROUND_WINDOW,
            "truth_track_contract": "Y_i(u,q) = q * F_u_i",
            "injection_stage": M37_COMPLETENESS_INJECTION_STAGE,
            "noise_selection_contract": M37_COMPLETENESS_NOISE_SELECTION,
            "filter_coordinate": FILTER_COORDINATE,
            "two_pass_masks_recomputed_with_each_injection": True,
            "exact_detector_and_disposition_replay_required": True,
            "truncation_permitted": False,
            "expected_trial_count": self.plan.expected_trial_count,
            "completed_trial_count": len(records),
            "canonical_trial_record_bytes": self._canonical_bytes,
            "execution_work": {
                "execution_mode": (
                    "full-exhaustive-observed-score-replay"
                    if production_replay
                    else "synthetic-known-answer-native-replay"
                ),
                "score_cells_per_production_trial": (
                    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
                ),
                "expected_full_production_score_cells": (
                    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL
                ),
                "detector_score_cells_replayed": (
                    detector_score_cells_replayed
                ),
                "production_feasibility_status": (
                    M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS
                ),
            },
            "levels": levels,
            "threshold_summaries": threshold_summaries,
            "trials": records,
            "trials_sha256": records_digest,
        }
        certificate = {
            "plan_sha256": self.plan.plan_sha256,
            "threshold_identity_sha256": (
                self.threshold.threshold_identity_sha256
            ),
            "trial_inventory_sha256": self.plan.trial_inventory_sha256,
            "trials_sha256": records_digest,
            "completed_trial_count": len(records),
            "detector_score_cells_replayed": detector_score_cells_replayed,
            "production_feasibility_status": (
                M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS
            ),
            "all_trials_accounted_exactly_once": True,
            "truncation_permitted": False,
        }
        certificate["completeness_certificate_sha256"] = _sha256(certificate)
        result["certificate"] = certificate
        self._sealed = True
        validate_completeness_result(result, self.plan, self.threshold)
        return json.loads(canonical_json_bytes(result))


def _summaries_for_levels(levels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    enriched = []
    for level in levels:
        item = dict(level)
        item["wilson_95_interval_lower"] = float(
            item["wilson_95_interval"][0]
        )
        enriched.append(item)
    return {
        "point_estimate_50_percent": _threshold_crossing_summary(
            enriched, 0.5, "recovery_fraction"
        ),
        "point_estimate_90_percent": _threshold_crossing_summary(
            enriched, 0.9, "recovery_fraction"
        ),
        "wilson_lower_50_percent": _threshold_crossing_summary(
            enriched, 0.5, "wilson_95_interval_lower"
        ),
        "wilson_lower_90_percent": _threshold_crossing_summary(
            enriched, 0.9, "wilson_95_interval_lower"
        ),
    }


def _validate_detached_trial_record(
    record: Mapping[str, Any],
    trial: CompletenessTrial,
    plan: CompletenessPlan,
    threshold: FrozenOperationalThreshold,
) -> None:
    expected_allocation = {**trial.as_record(), **trial.truth.as_record()}
    if any(record.get(key) != value for key, value in expected_allocation.items()):
        raise V0P6IncompleteError("trial allocation evidence changed")
    if (
        record.get("plan_sha256") != plan.plan_sha256
        or record.get("factor_table_sha256") != threshold.factor_table_sha256
        or record.get("template_bank_sha256") != M37_BANK_SHA256
        or record.get("threshold_identity_sha256")
        != threshold.threshold_identity_sha256
        or record.get("injection_stage") != M37_COMPLETENESS_INJECTION_STAGE
        or record.get("injection_model") != M37_COMPLETENESS_INJECTION_MODEL
    ):
        raise V0P6IncompleteError("trial upstream identity changed")
    for key in ("factor_basis_sha256", "factor_basis_labels_sha256"):
        _frozen_sha256(record.get(key), f"trial {key}")
    if threshold.source_kind == (
        "m37-factory-attested-threshold-certificate"
    ) and (
        record.get("factor_basis_sha256") != M37_FACTOR_BASIS_SHA256
        or record.get("factor_basis_labels_sha256")
        != M37_FACTOR_BASIS_LABELS_SHA256
    ):
        raise V0P6IncompleteError("trial M37 factor-basis provenance changed")
    for key in (
        "background_sha256",
        "background_context_sha256",
        "background_noise_selection_sha256",
        "background_scan_inventory_sha256",
        "background_source_working_set_contract_sha256",
        "injected_native_sha256",
        "mask_replay_receipt_sha256",
        "mask_inventory_sha256",
        "epoch_product_inventory_sha256",
        "cache_provenance_inventory_sha256",
    ):
        _frozen_sha256(record.get(key), f"trial {key}")
    background_scans = record.get("background_scan_sha256s")
    if not isinstance(background_scans, list) or len(background_scans) != 3:
        raise V0P6IncompleteError("trial background scan inventory changed")
    for digest in background_scans:
        _frozen_sha256(digest, "background scan identity")
    source_products = record.get("background_source_product_sha256s")
    source_working_sets = record.get(
        "background_source_working_set_accounting_sha256s"
    )
    shifts = record.get("background_noise_shift_channels")
    background_live = _strict_int(
        record.get("background_maximum_live_native_bytes_observed"),
        "background maximum live native bytes",
    )
    background_cap = _strict_int(
        record.get("background_maximum_live_native_bytes_per_trial"),
        "background maximum live-native-byte cap",
    )
    if (
        not isinstance(source_products, list)
        or len(source_products) != 3
        or not isinstance(source_working_sets, list)
        or len(source_working_sets) != 3
        or not isinstance(shifts, list)
        or len(shifts) != 3
        or background_live < 0
        or background_cap
        != M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        or background_live > background_cap
        or record.get("background_source_kind") not in {
            "synthetic-known-answer-background-v1",
            "m37-factory-normalized-seed-selected-background-v1",
        }
    ):
        raise V0P6IncompleteError("trial background source inventory changed")
    for digest in source_products:
        _frozen_sha256(digest, "background source-product identity")
    for digest in source_working_sets:
        _frozen_sha256(digest, "background source working-set identity")
    for shift in shifts:
        if _strict_int(shift, "background noise shift") < 0:
            raise V0P6ContractError("background noise shift is negative")
    if threshold.source_kind == (
        "m37-factory-attested-threshold-certificate"
    ) and (
        record.get("background_source_kind")
        != "m37-factory-normalized-seed-selected-background-v1"
        or record.get("background_scan_inventory_sha256")
        != M37_SCAN_INVENTORY_SHA256
        or record.get("background_source_working_set_contract_sha256")
        != M37_COMPLETENESS_SOURCE_STREAMING_EXECUTION_CONTRACT_SHA256
    ):
        raise V0P6IncompleteError("trial production background source changed")
    injected_scans = record.get("injected_scans")
    if not isinstance(injected_scans, list) or len(injected_scans) != 3:
        raise V0P6IncompleteError("trial injected scan inventory changed")
    expected_writes = 0
    background_native_bytes = 0
    for epoch, scan in enumerate(injected_scans):
        if not isinstance(scan, dict):
            raise V0P6ContractError("injected scan evidence is not a record")
        scan_copy = dict(scan)
        observed_scan_sha = _frozen_sha256(
            scan_copy.pop("scan_sha256"), "injected scan identity"
        )
        if observed_scan_sha != _sha256(scan_copy):
            raise V0P6IncompleteError("injected scan evidence changed")
        if (
            scan.get("epoch_index") != epoch
            or scan.get("truth_id") != trial.truth.truth_id
            or scan.get("truth_template_index") != trial.truth.template_index
            or scan.get("factor_basis_sha256")
            != record.get("factor_basis_sha256")
            or scan.get("factor_basis_labels_sha256")
            != record.get("factor_basis_labels_sha256")
            or scan.get("template_bank_sha256") != M37_BANK_SHA256
            or scan.get("factor_table_sha256") != threshold.factor_table_sha256
            or scan.get("normalized_dtype") != "<f4"
        ):
            raise V0P6IncompleteError("injected scan contract changed")
        for key in (
            "normalized_sha256",
            "truth_factors_sha256",
            "observed_truth_hz_sha256",
        ):
            _frozen_sha256(scan.get(key), f"injected scan {key}")
        shape = scan.get("normalized_shape")
        if (
            not isinstance(shape, list)
            or len(shape) != 2
            or any(_strict_int(item, "native shape") < 1 for item in shape)
        ):
            raise V0P6IncompleteError("injected scan shape changed")
        writes = _strict_int(scan.get("injection_write_count"), "injection writes")
        background_native_bytes += shape[0] * shape[1] * 4
        required_writes = (
            shape[0] * trial.truth.spectral_width_channels
            if epoch in trial.truth.active_epochs_zero_based
            else 0
        )
        if writes != required_writes:
            raise V0P6IncompleteError("injection write accounting changed")
        expected_writes += writes
    if expected_writes > M37_COMPLETENESS_MAXIMUM_INJECTION_WRITES_PER_TRIAL:
        raise V0P6CapacityError("completeness injection-write cap exceeded")
    if background_live < background_native_bytes:
        raise V0P6IncompleteError(
            "background source working-set peak omits retained native scans"
        )

    mask = record.get("mask_replay")
    if not isinstance(mask, dict):
        raise V0P6IncompleteError("trial mask replay evidence is absent")
    mask_copy = dict(mask)
    mask_receipt_sha = _frozen_sha256(
        mask_copy.pop("receipt_sha256"), "mask replay receipt"
    )
    mask_live = _strict_int(
        mask.get("maximum_live_native_bytes_observed"),
        "mask-replay maximum live native bytes",
    )
    mask_cap = _strict_int(
        mask.get("maximum_live_native_bytes_per_trial"),
        "mask-replay live-native-byte cap",
    )
    expected_mask_working_set_contract = (
        M37_COMPLETENESS_MASK_WORKING_SET_ACCOUNTING_CONTRACT
        if mask.get("source_kind") == "m37-live-mask-product-replay-v1"
        else M37_COMPLETENESS_SYNTHETIC_MASK_WORKING_SET_ACCOUNTING_CONTRACT
    )
    if (
        mask_receipt_sha != _sha256(mask_copy)
        or mask_receipt_sha != record["mask_replay_receipt_sha256"]
        or mask.get("trial_id") != trial.trial_id
        or mask.get("source_injected_native_sha256")
        != record["injected_native_sha256"]
        or mask.get("source_kind") not in {
            "m37-live-mask-product-replay-v1",
            "synthetic-known-answer-derived-mask-replay-v1",
        }
        or mask.get("mask_inventory_sha256") != record["mask_inventory_sha256"]
        or mask.get("epoch_product_inventory_sha256")
        != record["epoch_product_inventory_sha256"]
        or mask.get("cache_provenance_inventory_sha256")
        != record["cache_provenance_inventory_sha256"]
        or mask.get("injected_scan_sha256s")
        != [item["scan_sha256"] for item in injected_scans]
        or mask.get("native_filter_cache_count")
        != len(M37_SPECTRAL_WIDTHS) * 3
        or mask_cap
        != M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        or mask_live < 2 * background_native_bytes
        or mask_live > mask_cap
        or mask.get("source_epoch_product_count")
        != M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS
        or mask.get("template_mask_count")
        != M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS
        or mask.get("spectral_widths") != list(M37_SPECTRAL_WIDTHS)
        or mask.get("strong_snr") != M37_RFI_STRONG_SNR
        or mask.get("other_epochs_below_snr")
        != M37_RFI_OTHER_EPOCHS_BELOW_SNR
        or mask.get("guard_q_bins") != M37_RFI_GUARD_Q_BINS
        or mask.get("working_set_accounting_contract")
        != expected_mask_working_set_contract
        or mask.get("recomputed_after_injection") is not True
        or mask.get("pass_two_must_consume_this_exact_inventory") is not True
    ):
        raise V0P6IncompleteError("trial mask replay evidence changed")
    for key in (
        "epoch_product_inventory_sha256",
        "cache_provenance_inventory_sha256",
    ):
        _frozen_sha256(mask.get(key), f"mask replay {key}")

    evaluation = record.get("evaluation")
    if not isinstance(evaluation, dict):
        raise V0P6IncompleteError("trial evaluation evidence is absent")
    evaluation_copy = dict(evaluation)
    evaluation_sha = _frozen_sha256(
        evaluation_copy.pop("evaluation_sha256"), "trial evaluation identity"
    )
    if evaluation_sha != _sha256(evaluation_copy):
        raise V0P6IncompleteError("trial evaluation evidence changed")
    if (
        evaluation.get("trial_id") != trial.trial_id
        or evaluation.get("injected_native_sha256")
        != record["injected_native_sha256"]
        or evaluation.get("mask_replay_receipt_sha256") != mask_receipt_sha
        or evaluation.get("threshold_identity_sha256")
        != threshold.threshold_identity_sha256
    ):
        raise V0P6IncompleteError("trial evaluation upstream identity changed")
    score_value = evaluation.get("best_truth_associated_snr")
    score = None if score_value is None else float(score_value)
    if score is not None and not math.isfinite(score):
        raise V0P6ContractError("trial evaluation score is non-finite")
    selected_record_id = evaluation.get("selected_record_id")
    matched = selected_record_id is not None
    if matched:
        _frozen_sha256(selected_record_id, "selected retained-record identity")
    detector_passed = matched
    distance_value = evaluation.get("truth_match_maximum_track_distance_hz")
    distance = None if distance_value is None else float(distance_value)
    if distance is not None and (not math.isfinite(distance) or distance < 0.0):
        raise V0P6ContractError("trial truth distance is invalid")
    truth_matched = (
        matched
        and score is not None
        and score >= threshold.operational_threshold_snr
        and distance is not None
        and distance <= M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ
    )
    physical = evaluation.get("physical_disposition")
    disposition = str(evaluation.get("final_disposition"))
    vetoed = truth_matched and isinstance(physical, str) and (
        physical.startswith("rfi_veto_")
    )
    rank_value = evaluation.get("inclusive_global_rank_p")
    rank_p = None if rank_value is None else float(rank_value)
    eligible = evaluation.get("scientifically_eligible")
    if truth_matched:
        if (
            not isinstance(physical, str)
            or not isinstance(eligible, bool)
            or rank_p is None
            or not math.isfinite(rank_p)
            or not 0.0 <= rank_p <= 1.0
        ):
            raise V0P6IncompleteError(
                "matched evaluation lacks physical/rank-p evidence"
            )
    elif any(item is not None for item in (physical, rank_p, eligible)):
        raise V0P6IncompleteError(
            "unmatched evaluation invented physical/rank-p evidence"
        )
    recovered = truth_matched and not vetoed and eligible is True
    if not truth_matched:
        expected_disposition = "below_operational_threshold"
    elif vetoed:
        expected_disposition = physical
    elif eligible:
        expected_disposition = "scientific_candidate_unresolved"
    else:
        expected_disposition = "retained_but_not_scientifically_eligible"
    if (
        evaluation.get("detector_passed") is not detector_passed
        or evaluation.get("truth_matched") is not truth_matched
        or evaluation.get("physical_vetoed") is not vetoed
        or evaluation.get("recovered") is not recovered
        or disposition != expected_disposition
        or evaluation.get("source_kind") not in {
            "m37-concrete-operational-artifacts-v1",
            "synthetic-known-answer-native-replay-v1",
        }
    ):
        raise V0P6IncompleteError("trial recovery semantics changed")
    selected = (
        evaluation.get("selected_template_index"),
        evaluation.get("selected_spectral_width_index"),
        evaluation.get("selected_activity_subset_index"),
        evaluation.get("selected_proxy_carrier_index"),
    )
    if truth_matched != all(item is not None for item in selected):
        raise V0P6IncompleteError("trial selected hypothesis accounting changed")
    record_count = _strict_int(
        evaluation.get("detector_record_count"), "detector record count"
    )
    score_cells = _strict_int(
        evaluation.get("detector_score_cells_replayed"),
        "detector score-cell count",
    )
    evidence_bytes = _strict_int(
        evaluation.get("disposition_evidence_canonical_bytes"),
        "disposition evidence bytes",
    )
    if not 0 <= record_count <= M37_COMPLETENESS_MAXIMUM_DETECTOR_RECORDS:
        raise V0P6CapacityError("per-trial detector record cap exceeded")
    if score_cells < 1 or (
        evaluation.get("source_kind")
        == "m37-concrete-operational-artifacts-v1"
        and score_cells
        != M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
    ):
        raise V0P6IncompleteError(
            "trial detector score-cell accounting changed"
        )
    if not 0 <= evidence_bytes <= (
        M37_COMPLETENESS_MAXIMUM_DISPOSITION_EVIDENCE_BYTES
    ):
        raise V0P6CapacityError("per-trial disposition evidence cap exceeded")
    _frozen_sha256(evaluation.get("detector_receipt_sha256"), "detector receipt")
    _frozen_sha256(
        evaluation.get("disposition_receipt_sha256"), "disposition receipt"
    )
    _frozen_sha256(
        evaluation.get("significance_result_sha256"), "rank-p result"
    )
    encoded_size = len(canonical_json_bytes(record))
    if record.get("canonical_bytes") != encoded_size or encoded_size > (
        M37_COMPLETENESS_MAXIMUM_TRIAL_RECORD_CANONICAL_BYTES
    ):
        raise V0P6CapacityError("trial canonical-byte accounting changed")


def validate_completeness_result(
    result: Mapping[str, Any],
    plan: CompletenessPlan,
    threshold: FrozenOperationalThreshold,
) -> dict[str, Any]:
    """Independently validate exact inventory, aggregates, and result hashes."""
    validate_m37_completeness_plan(plan)
    validate_frozen_threshold(threshold)
    try:
        detached = json.loads(canonical_json_bytes(dict(result)))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError("completeness result is not finite JSON") from error
    required = {
        "status",
        "plan",
        "threshold",
        "levels",
        "threshold_summaries",
        "trials",
        "trials_sha256",
        "certificate",
        "expected_trial_count",
        "completed_trial_count",
        "canonical_trial_record_bytes",
        "execution_work",
        "truncation_permitted",
    }
    if not required <= set(detached):
        raise V0P6IncompleteError("completeness result lacks required evidence")
    if (
        detached["status"] != M37_COMPLETENESS_STATUS
        or detached["plan"] != plan.as_record()
        or detached["threshold"] != threshold.as_record()
        or detached["truncation_permitted"] is not False
        or detached["expected_trial_count"] != plan.expected_trial_count
        or detached["completed_trial_count"] != plan.expected_trial_count
        or detached.get("noise_selection_contract")
        != M37_COMPLETENESS_NOISE_SELECTION
    ):
        raise V0P6IncompleteError("completeness result contract changed")
    records = detached["trials"]
    if not isinstance(records, list) or len(records) != plan.expected_trial_count:
        raise V0P6IncompleteError("completeness result trial inventory is incomplete")
    expected_trials = iter_m37_completeness_trials(plan)
    expected_ids = [trial.trial_id for trial in expected_trials]
    observed_ids = [str(record.get("trial_id")) for record in records]
    if observed_ids != expected_ids or len(set(observed_ids)) != len(observed_ids):
        raise V0P6IncompleteError("completeness result trials changed or duplicated")
    if detached["trials_sha256"] != _sha256(records):
        raise V0P6IncompleteError("completeness trial records changed")
    for record, trial in zip(records, expected_trials, strict=True):
        _validate_detached_trial_record(record, trial, plan, threshold)
    canonical_bytes = sum(len(canonical_json_bytes(item)) for item in records)
    if (
        detached["canonical_trial_record_bytes"] != canonical_bytes
        or canonical_bytes > M37_COMPLETENESS_MAXIMUM_TOTAL_CANONICAL_BYTES
    ):
        raise V0P6CapacityError("completeness evidence-byte accounting changed")
    observed_score_cells = sum(
        _strict_int(
            item["evaluation"]["detector_score_cells_replayed"],
            "detector score-cell count",
        )
        for item in records
    )
    production_replay = threshold.source_kind == (
        "m37-factory-attested-threshold-certificate"
    )
    expected_work = {
        "execution_mode": (
            "full-exhaustive-observed-score-replay"
            if production_replay
            else "synthetic-known-answer-native-replay"
        ),
        "score_cells_per_production_trial": (
            M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL
        ),
        "expected_full_production_score_cells": (
            M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL
        ),
        "detector_score_cells_replayed": observed_score_cells,
        "production_feasibility_status": (
            M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS
        ),
    }
    if detached["execution_work"] != expected_work or (
        production_replay
        and observed_score_cells
        != M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL
    ):
        raise V0P6IncompleteError("completeness execution-work accounting changed")
    levels = detached["levels"]
    if not isinstance(levels, list) or len(levels) != len(
        M37_COMPLETENESS_SNR_GRID
    ):
        raise V0P6IncompleteError("completeness level inventory changed")
    for index, (level, snr) in enumerate(
        zip(levels, M37_COMPLETENESS_SNR_GRID, strict=True)
    ):
        relevant = records[
            index
            * M37_COMPLETENESS_TRUTHS_PER_LEVEL : (index + 1)
            * M37_COMPLETENESS_TRUTHS_PER_LEVEL
        ]
        recovered = sum(bool(item["evaluation"]["recovered"]) for item in relevant)
        low, high = wilson_interval_95(recovered, len(relevant))
        expected_level = {
            "level_index": index,
            "ideal_single_epoch_snr": snr,
            "trials": len(relevant),
            "recovered": recovered,
            "recovery_fraction": recovered / len(relevant),
            "wilson_95_interval": [low, high],
        }
        if level != expected_level:
            raise V0P6IncompleteError("completeness aggregate changed")
    if detached["threshold_summaries"] != _summaries_for_levels(levels):
        raise V0P6IncompleteError("completeness threshold summary changed")
    certificate = dict(detached["certificate"])
    observed_certificate_sha = _frozen_sha256(
        certificate.pop("completeness_certificate_sha256"),
        "completeness-certificate identity",
    )
    if observed_certificate_sha != _sha256(certificate):
        raise V0P6IncompleteError("completeness certificate changed")
    if (
        certificate.get("plan_sha256") != plan.plan_sha256
        or certificate.get("threshold_identity_sha256")
        != threshold.threshold_identity_sha256
        or certificate.get("trial_inventory_sha256")
        != plan.trial_inventory_sha256
        or certificate.get("trials_sha256") != detached["trials_sha256"]
        or certificate.get("completed_trial_count") != plan.expected_trial_count
        or certificate.get("detector_score_cells_replayed")
        != observed_score_cells
        or certificate.get("production_feasibility_status")
        != M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS
        or certificate.get("all_trials_accounted_exactly_once") is not True
        or certificate.get("truncation_permitted") is not False
    ):
        raise V0P6IncompleteError("completeness certificate contract changed")
    return detached


def run_streaming_completeness(
    plan: CompletenessPlan,
    threshold: FrozenOperationalThreshold,
    data_source: CompletenessDataSource,
    pipeline: CompletenessOperationalPipeline,
) -> dict[str, Any]:
    """Run all 6,144 trials serially (including synthetic known answers)."""
    ledger = CompletenessLedger(plan, threshold)
    for trial in iter_m37_completeness_trials(plan):
        background = data_source.load_background(trial)
        injected = inject_native_before_filter(background, trial)
        masks = pipeline.recompute_two_pass_masks(injected, trial)
        validate_mask_replay_receipt(masks, injected)
        evaluation = pipeline.evaluate_exact_operational_pipeline(
            injected,
            masks,
            threshold,
            trial,
        )
        ledger.add_trial(trial, background, injected, masks, evaluation)
    return ledger.finalize()


def run_streaming_m37_completeness(
    plan: CompletenessPlan,
    threshold: FrozenOperationalThreshold,
    data_source: CompletenessDataSource,
    pipeline: CompletenessOperationalPipeline,
) -> dict[str, Any]:
    """Run a production M37 replay only from a live-attested final threshold."""
    validate_m37_completeness_plan(plan)
    validate_frozen_threshold(threshold)
    if (
        threshold.source_kind
        != "m37-factory-attested-threshold-certificate"
        or threshold.experiment_contract_sha256
        != M37_EXPERIMENT_CONTRACT_SHA256
        or threshold.threshold_identity_sha256
        not in _M37_ATTESTED_THRESHOLD_IDENTITIES
    ):
        raise V0P6ContractError(
            "production M37 completeness requires a live-attested final threshold"
        )
    if M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS != (
        "passed-full-replay-benchmark-or-bit-identical-sparse-reference-kat"
    ):
        raise V0P6IncompleteError(
            "production completeness is feasibility-gated: the mandatory "
            "13,670,713,589,760-score-cell full-replay benchmark has not "
            "passed and no bit-identical sparse/local reference KAT exists"
        )
    return run_streaming_completeness(plan, threshold, data_source, pipeline)
