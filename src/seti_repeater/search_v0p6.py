"""Prospective detector-v0.6 primitives for direct proxy-carrier tracks.

This module is deliberately separate from :mod:`seti_repeater.search`, which
remains the frozen detector-v0.5 implementation.  The v0.6 track contract is

    observed_frequency_i(q) = q * factor_i

and every spectral boxcar is applied on the native receiver-channel axis
*before* values are gathered onto the proxy-carrier (``q``) lattice.

The functions here are data-source agnostic.  Importing the module never opens
a telescope file, and the small materialized reference path has an explicit
cell cap so it cannot accidentally be used for the production grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from importlib import resources
import json
import math
import operator
import weakref
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from .spectral import normalized_boxcar, validate_widths


DETECTOR_VERSION = "0.6.0-development"
TRACK_CONTRACT = "P_v_i(q) = q * F_v_i"
FILTER_COORDINATE = "native_raw_channel_axis_before_q_track_gather"
PROXY_CARRIER_AXIS_LABEL = "proxy_carrier_mhz"
M37_TEMPLATE_COUNT = 93
M37_BANK_SHA256 = (
    "8b0c5488944133db9bf500f7ed108971f42ef4d29ce36aa67f9a89ffac3a2d63"
)
M37_FACTOR_BASIS_SHA256 = (
    "492d2fe31d8cbe14968c9ce0296e898f42bf298540310f3f06a74ec8c971c143"
)
M37_FACTOR_BASIS_LABELS_SHA256 = (
    "5e5afd59424d48978148e7aafb3715e2c957c7495610dc98a7f99b44dfe59aee"
)
M37_SCAN_INVENTORY_SHA256 = (
    "d7fc931d0a058a561ab07a921d5bcc996b4020caa75085b40c1c37dee3227a93"
)
M37_FACTOR_ROW_SELECTION_SHA256S = {
    "on": "6643d1a0f6265172b995c9084e7b595fe74f35722b6d5e475e811d8c237f85c4",
    "off": "d70c1f8351fe0e2fc70bf4e11267c119dcbd3fc02bcf890206fbd11ae9c5eedc",
}
M37_FACTOR_SCAN_SELECTION_SHA256S = {
    "epoch1_on": "920a50d61492b0ad2c2a20cc6d986d7d468fb99fdff3380df168b21d18f47a62",
    "epoch1_off": "d7ecd241de0c985bf2d573eef9a0061049094ea64043869b2e896e4fc39ef5b1",
    "epoch2_on": "9c5fa5e37ee4b2322bcb90e49f3b65a9d630b1cf25c2bd0babbfa61234b722ab",
    "epoch2_off": "330ce5323c3123c3224d9e7f00c03e6ca14de456e562176a62c7df0a01efc898",
    "epoch3_on": "8f1251e0222e08021f9b4ec1c5d318001f0c211aedf96b2ba2da08f7e7545857",
    "epoch3_off": "a6f39681a66deb97eee6a20c2e7c50d38f2062112d8240e926cd370f6d342a99",
}
M37_DIRECTION = (-0.6558897197989564, 0.75485672512209)
M37_DIRECTION_PHASE_CYCLES = 0.3638531880461531
M37_SCIENTIFIC_P_CEILING = 0.01
M37_WINDOW_IDS = (
    "m37_1400p5",
    "m37_1406p5",
    "m37_1412p5",
    "m37_1418p5",
    "m37_1425p0",
)
M37_WINDOW_CENTERS_MHZ = (1400.5, 1406.5, 1412.5, 1418.5, 1425.0)
M37_CHANNEL_WIDTH_HZ = 2.835503418452676
M37_SCORE_HALF_BINS = 373_832
M37_SUPPORT_GUARD_BINS = 64
M37_SPECTRAL_WIDTHS = (1, 3, 5, 9, 17, 33, 65, 129)
M37_ACTIVITY_SUBSETS = ((0, 1), (0, 2), (1, 2), (0, 1, 2))
M37_MINIMUM_ACTIVE_EPOCH_SNR = 3.0
M37_RFI_STRONG_SNR = 10.0
M37_RFI_OTHER_EPOCHS_BELOW_SNR = 3.0
M37_RFI_GUARD_Q_BINS = 9
M37_SCRAMBLE_COUNT = 256
M37_SCRAMBLE_MASTER_SEED = 3_720_260_827
M37_SCRAMBLE_MINIMUM_SHIFT_BINS = 4_096
M37_SCRAMBLE_TABLE_SHA256S = (
    "25f8e158cf7f4ff989a07f8cc60dfa2bd16f1aa9c3e0fbbe53e47cd8f071a0e8",
    "370f75da221e40eea7dfe57eb6056b458e4804e1d45bbddf1f5ce170b7c90902",
    "5d628741a20bfc7945248434c475ae9bb32b7b84359e129c26b297a8318bd0bf",
    "2f79f70b66be3ec260d6a9d8edfe59d77b544ef65f8d7f0960406eb0e0d0845c",
    "ecda3b480ac32d58bb8e0adba9262154ee343b04c2a00ef69d65ff9c695aee6d",
)
M37_SCRAMBLE_TABLES_SHA256 = (
    "35f4cf42c2f1359ad582ddc9299fb73de2daf092e8189fc88ba716ad3ea139eb"
)
M37_SCRAMBLE_RESOURCE_NAMES = tuple(
    f"data/m37_scrambles/{window_id}_scramble_i64le.bin"
    for window_id in M37_WINDOW_IDS
)
M37_EXPERIMENT_CONTRACT_SHA256 = (
    "fe80c31623e89ae7f9091a277044683df4372fde2bfe8d8da71d0d1c9d9db11c"
)
M37_THRESHOLD_REFERENCE_FLOOR_SNR = 7.0
M37_THRESHOLD_QUANTILE = 0.99
M37_MAXIMUM_RECORDS_PER_WINDOW = 10_000
M37_MAXIMUM_RECORD_CANONICAL_BYTES = 6_144
M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES = 96_000_000
M37_LIVE_NDARRAY_CAP_BYTES = 536_870_912
M37_OFF_TRACK_TOLERANCE_HZ = 20.0
M37_MAXIMUM_ALIAS_BUCKET_ENTRIES = 30_000
M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS = 5_000_000
M37_MAXIMUM_OFF_BUCKET_ENTRIES = 30_000
M37_MAXIMUM_OFF_EXACT_CANDIDATE_VISITS = 5_000_000
M37_CALIBRATION_EXECUTION_ENGINE = "m37_native_openmp_v1"
M37_CALIBRATION_THREAD_COUNT = 8
PYTHON_CALIBRATION_EXECUTION_ENGINE = "python_reference_v1"


class V0P6ContractError(ValueError):
    """Raised when a caller violates a frozen detector-v0.6 contract."""


class V0P6CoverageError(RuntimeError):
    """Raised when native extraction support cannot cover a requested track."""


class V0P6CapacityError(RuntimeError):
    """Raised when exhaustive evidence cannot be retained without truncation."""


class V0P6IncompleteError(RuntimeError):
    """Raised when a supposedly exhaustive pass is missing or duplicated."""


def _strict_int(value: Any, label: str) -> int:
    """Return an integer identity without silently truncating floats or bools."""
    if isinstance(value, (bool, np.bool_)):
        raise V0P6ContractError(f"{label} must be an integer, not boolean")
    try:
        return int(operator.index(value))
    except TypeError as error:
        raise V0P6ContractError(f"{label} must be an exact integer") from error


def _finite_json_number(value: Any, label: str) -> float:
    """Require a finite JSON number without coercing strings or booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V0P6ContractError(f"{label} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise V0P6ContractError(f"{label} must be a finite JSON number")
    return converted


def _strict_widths(widths: Iterable[Any]) -> tuple[int, ...]:
    values = tuple(
        _strict_int(width, "spectral width") for width in widths
    )
    try:
        return validate_widths(values)
    except ValueError as error:
        raise V0P6ContractError(str(error)) from error


def _scoring_contract(
    minimum_active_epoch_snr: float | None,
    stack_statistic: str,
) -> tuple[float | None, str]:
    statistic = str(stack_statistic)
    if statistic not in {"sum", "minimum_epoch"}:
        raise V0P6ContractError(f"unknown stack statistic: {statistic}")
    if minimum_active_epoch_snr is None:
        floor = None
    else:
        floor = float(minimum_active_epoch_snr)
        if not math.isfinite(floor):
            raise V0P6ContractError("active-epoch S/N floor must be finite")
    return floor, statistic


def canonical_json_bytes(value: Any) -> bytes:
    """Return the compact canonical JSON representation used for v0.6 hashes."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


PYTHON_CALIBRATION_EXECUTION_IDENTITY_SHA256 = hashlib.sha256(
    canonical_json_bytes(
        {
            "engine": PYTHON_CALIBRATION_EXECUTION_ENGINE,
            "roll_semantics": "numpy.roll positive shift",
            "score_function": "stack_hypothesis",
            "maximum_reduction": "scramble then activity-subset order",
            "output_dtype": "float64 exact promotion of float32 maxima",
        }
    )
).hexdigest()


def _frozen_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise V0P6ContractError(f"{label} must be a lowercase SHA-256 digest")
    digest = value
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise V0P6ContractError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def hypothesis_contract_sha256(
    *,
    score_bin_count: int,
    epoch_count: int,
    template_count: int,
    template_bank_sha256_value: str,
    spectral_widths: Iterable[int],
    activity_subsets: Iterable[Sequence[int]],
    minimum_active_epoch_snr: float | None,
    stack_statistic: str,
    scramble_count: int,
) -> str:
    """Hash the experiment dimensions shared by every calibration window."""
    score_bin_count = _strict_int(score_bin_count, "score-bin count")
    epoch_count = _strict_int(epoch_count, "epoch count")
    template_count = _strict_int(template_count, "template count")
    scramble_count = _strict_int(scramble_count, "scramble count")
    if min(score_bin_count, epoch_count, template_count, scramble_count) < 1:
        raise V0P6ContractError("hypothesis-contract dimensions must be positive")
    widths = _strict_widths(spectral_widths)
    activity = canonical_activity_subsets(activity_subsets)
    if max(epoch for subset in activity for epoch in subset) >= epoch_count:
        raise V0P6ContractError("activity subset is outside the epoch inventory")
    floor, statistic = _scoring_contract(
        minimum_active_epoch_snr, stack_statistic
    )
    payload = {
        "score_bin_count": score_bin_count,
        "epoch_count": epoch_count,
        "template_count": template_count,
        "template_bank_sha256": _frozen_sha256(
            template_bank_sha256_value, "template-bank identity"
        ),
        "spectral_widths": list(widths),
        "activity_subsets": [list(subset) for subset in activity],
        "minimum_active_epoch_snr": floor,
        "stack_statistic": statistic,
        "scramble_count": scramble_count,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def factorized_analysis_contract_sha256(
    hypothesis_contract_sha256_value: str,
    factor_basis_sha256_value: str,
    factor_basis_labels_sha256_value: str,
    scan_inventory_sha256_value: str,
    factor_table_sha256_value: str,
) -> str:
    """Bind score dimensions to the exact basis and factor-table values."""
    payload = {
        "hypothesis_contract_sha256": _frozen_sha256(
            hypothesis_contract_sha256_value, "hypothesis-contract identity"
        ),
        "factor_basis_sha256": _frozen_sha256(
            factor_basis_sha256_value, "factor-basis identity"
        ),
        "factor_basis_labels_sha256": _frozen_sha256(
            factor_basis_labels_sha256_value, "factor-basis labels identity"
        ),
        "scan_inventory_sha256": _frozen_sha256(
            scan_inventory_sha256_value, "scan-inventory identity"
        ),
        "factor_table_sha256": _frozen_sha256(
            factor_table_sha256_value, "factor-table identity"
        ),
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def make_line_template_bank(
    count: int = M37_TEMPLATE_COUNT,
    direction: Sequence[float] = M37_DIRECTION,
    direction_phase_cycles: float = M37_DIRECTION_PHASE_CYCLES,
    expected_sha256: str | None = M37_BANK_SHA256,
) -> list[dict[str, Any]]:
    """Build the canonical centered odd line bank used by M37.

    Canonical order is ``0,+1,-1,+2,-2,...``.  A non-M37 count or direction
    may be used by synthetic tests by passing ``expected_sha256=None``.
    """
    count = _strict_int(count, "template-bank count")
    if count < 1 or count % 2 != 1:
        raise V0P6ContractError("the centered line-bank count must be positive and odd")
    vector = np.asarray(direction, dtype=np.float64)
    if vector.shape != (2,) or not np.all(np.isfinite(vector)):
        raise V0P6ContractError("bank direction must contain two finite coefficients")
    norm = float(np.linalg.norm(vector))
    if abs(norm - 1.0) > 2e-15:
        raise V0P6ContractError(f"bank direction is not unit length: {norm}")
    vector = vector / norm
    observed_phase = math.atan2(float(vector[1]), float(vector[0])) / (
        2.0 * math.pi
    ) % 1.0
    if abs(observed_phase - float(direction_phase_cycles)) > 2e-15:
        raise V0P6ContractError("bank direction and direction phase disagree")

    half = (count - 1) // 2
    line_indices = [0] + [value for m in range(1, half + 1) for value in (m, -m)]
    records: list[dict[str, Any]] = []
    for template_index, line_index in enumerate(line_indices):
        coefficient = 2.0 * line_index / count
        coefficient_vector = coefficient * vector
        records.append(
            {
                "template_index": template_index,
                "line_index": line_index,
                "line_coefficient": coefficient,
                "coefficient_x": float(coefficient_vector[0]),
                "coefficient_y": float(coefficient_vector[1]),
                "projected_scale": abs(coefficient),
                "phase_cycles": (
                    0.0
                    if line_index == 0
                    else (
                        float(direction_phase_cycles)
                        if line_index > 0
                        else (float(direction_phase_cycles) + 0.5) % 1.0
                    )
                ),
            }
        )
    digest = hashlib.sha256(canonical_json_bytes(records)).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise V0P6ContractError(
            f"template-bank SHA-256 changed: {digest} != {expected_sha256}"
        )
    return records


def template_bank_sha256(records: Sequence[dict[str, Any]]) -> str:
    """Hash template records in their existing order."""
    return hashlib.sha256(canonical_json_bytes(list(records))).hexdigest()


@dataclass(frozen=True)
class ProxyCarrierGrid:
    """A normative score lattice plus a non-scored support guard."""

    center_mhz: float
    channel_width_hz: float
    score_half_bins: int
    support_guard_bins: int
    support_hz: np.ndarray = field(repr=False)
    score_hz: np.ndarray = field(repr=False)
    support_mhz: np.ndarray = field(repr=False)
    score_mhz: np.ndarray = field(repr=False)

    @property
    def score_bin_count(self) -> int:
        return 2 * self.score_half_bins + 1

    @property
    def support_bin_count(self) -> int:
        return self.score_bin_count + 2 * self.support_guard_bins

    @property
    def score_slice(self) -> slice:
        guard = self.support_guard_bins
        return slice(guard, self.support_bin_count - guard if guard else None)


def make_proxy_carrier_grid(
    center_mhz: float,
    channel_width_hz: float,
    score_half_bins: int,
    support_guard_bins: int,
) -> ProxyCarrierGrid:
    """Construct ``q[k] = center + k*df`` without cumulative drift."""
    center_mhz = float(center_mhz)
    channel_width_hz = float(channel_width_hz)
    score_half_bins = _strict_int(score_half_bins, "score half-bins")
    support_guard_bins = _strict_int(
        support_guard_bins, "support guard-bins"
    )
    if not math.isfinite(center_mhz):
        raise V0P6ContractError("proxy-carrier center must be finite")
    if not math.isfinite(channel_width_hz) or channel_width_hz <= 0.0:
        raise V0P6ContractError("proxy-carrier channel width must be positive")
    if score_half_bins < 0 or support_guard_bins < 0:
        raise V0P6ContractError("proxy-carrier half sizes must be non-negative")
    support_half = score_half_bins + support_guard_bins
    lattice_indices = np.arange(-support_half, support_half + 1, dtype=np.int64)
    support_hz = center_mhz * 1e6 + lattice_indices * channel_width_hz
    support_hz = np.asarray(support_hz, dtype=np.float64)
    support_mhz = np.asarray(support_hz / 1e6, dtype=np.float64)
    guard = support_guard_bins
    score_slice = slice(guard, support_mhz.size - guard if guard else None)
    score_hz = support_hz[score_slice]
    score_mhz = support_mhz[score_slice]
    if score_mhz.size != 2 * score_half_bins + 1:
        raise AssertionError("proxy-carrier score-grid size is inconsistent")
    support_mhz.setflags(write=False)
    score_mhz.setflags(write=False)
    support_hz.setflags(write=False)
    score_hz.setflags(write=False)
    return ProxyCarrierGrid(
        center_mhz=center_mhz,
        channel_width_hz=channel_width_hz,
        score_half_bins=score_half_bins,
        support_guard_bins=support_guard_bins,
        support_hz=support_hz,
        score_hz=score_hz,
        support_mhz=support_mhz,
        score_mhz=score_mhz,
    )


def make_m37_proxy_carrier_grid(window_id: str) -> ProxyCarrierGrid:
    """Build one exact M37 score/support lattice from its frozen identity."""
    window_id = str(window_id)
    try:
        index = M37_WINDOW_IDS.index(window_id)
    except ValueError as error:
        raise V0P6ContractError("unknown M37 window identity") from error
    return make_proxy_carrier_grid(
        M37_WINDOW_CENTERS_MHZ[index],
        M37_CHANNEL_WIDTH_HZ,
        M37_SCORE_HALF_BINS,
        M37_SUPPORT_GUARD_BINS,
    )


def proxy_carrier_grid_sha256(grid: ProxyCarrierGrid) -> str:
    """Hash every scalar and both Hz/MHz arrays in a proxy-grid contract."""
    payload = {
        "center_mhz": float(grid.center_mhz),
        "channel_width_hz": float(grid.channel_width_hz),
        "score_half_bins": _strict_int(grid.score_half_bins, "score half-bins"),
        "support_guard_bins": _strict_int(
            grid.support_guard_bins, "support guard-bins"
        ),
        "support_hz_sha256": float64_vector_sha256(grid.support_hz),
        "score_hz_sha256": float64_vector_sha256(grid.score_hz),
        "support_mhz_sha256": float64_vector_sha256(grid.support_mhz),
        "score_mhz_sha256": float64_vector_sha256(grid.score_mhz),
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class NativeFrequencyGeometry:
    """Frozen ascending native-channel affine geometry in Hz."""

    raw_zero_hz: float
    channel_width_hz: float
    channel_count: int

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.raw_zero_hz)):
            raise V0P6ContractError("native raw zero must be finite")
        if (
            not math.isfinite(float(self.channel_width_hz))
            or float(self.channel_width_hz) <= 0.0
        ):
            raise V0P6ContractError("native channel width must be positive")
        channel_count = _strict_int(self.channel_count, "native channel count")
        if channel_count < 2:
            raise V0P6ContractError("native geometry requires at least two channels")


def native_geometry_from_extraction(
    *,
    fch1_mhz: float,
    foff_mhz: float,
    channel_start: int,
    channel_stop: int,
) -> NativeFrequencyGeometry:
    """Reproduce the preflight's exact header-affine extraction geometry."""
    fch1_mhz = float(fch1_mhz)
    foff_mhz = float(foff_mhz)
    channel_start = _strict_int(channel_start, "extraction channel start")
    channel_stop = _strict_int(channel_stop, "extraction channel stop")
    if channel_start < 0 or channel_stop <= channel_start:
        raise V0P6ContractError("native extraction channel interval is invalid")
    endpoints_mhz = (
        fch1_mhz + channel_start * foff_mhz,
        fch1_mhz + (channel_stop - 1) * foff_mhz,
    )
    return NativeFrequencyGeometry(
        raw_zero_hz=min(endpoints_mhz) * 1e6,
        channel_width_hz=abs(foff_mhz) * 1e6,
        channel_count=channel_stop - channel_start,
    )


def _native_grid_parameters(frequency_mhz: np.ndarray) -> tuple[float, float]:
    frequency = np.asarray(frequency_mhz, dtype=np.float64)
    if frequency.ndim != 1 or frequency.size < 2:
        raise V0P6ContractError("native frequency grid must be one-dimensional")
    if not np.all(np.isfinite(frequency)):
        raise V0P6ContractError("native frequency grid contains non-finite values")
    steps = np.diff(frequency)
    df_mhz = float(steps[0])
    if df_mhz == 0.0 or np.any(np.signbit(steps) != np.signbit(df_mhz)):
        raise V0P6ContractError("native frequency grid must be strictly monotonic")
    tolerance = max(abs(df_mhz) * 1e-7, 8.0 * np.finfo(np.float64).eps)
    if float(np.max(np.abs(steps - df_mhz))) > tolerance:
        raise V0P6ContractError("native frequency grid must be uniformly spaced")
    return float(frequency[0]), df_mhz


def nearest_native_indices(
    geometry: NativeFrequencyGeometry,
    requested_hz: np.ndarray,
) -> np.ndarray:
    """Map Hz frequencies with the frozen nearest-even ``rint`` rule."""
    requested = np.asarray(requested_hz, dtype=np.float64)
    if not np.all(np.isfinite(requested)):
        raise V0P6ContractError("requested track contains non-finite frequencies")
    return np.rint(
        (requested - float(geometry.raw_zero_hz))
        / float(geometry.channel_width_hz)
    ).astype(np.int64)


def _validate_gather_inputs(
    normalized: np.ndarray,
    frequency_mhz: np.ndarray,
    geometry: NativeFrequencyGeometry,
    factors: np.ndarray,
    grid: ProxyCarrierGrid,
    width: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    data = np.asarray(normalized, dtype=np.float32)
    frequency = np.asarray(frequency_mhz, dtype=np.float64)
    factor = np.asarray(factors, dtype=np.float64)
    width = _strict_widths((width,))[0]
    if data.ndim != 2 or data.shape[1] != frequency.size:
        raise V0P6ContractError(
            "normalized data must have [integration, native_channel] axes"
        )
    if not np.all(np.isfinite(data)):
        raise V0P6ContractError("normalized native data must be finite")
    if factor.shape != (data.shape[0],):
        raise V0P6ContractError("factor count must equal the integration count")
    if not np.all(np.isfinite(factor)) or np.any(factor <= 0.0):
        raise V0P6ContractError("all track factors must be finite and positive")
    if grid.support_mhz.shape != (grid.support_bin_count,):
        raise V0P6ContractError("proxy-carrier support grid has an invalid shape")
    _, df_mhz = _native_grid_parameters(frequency)
    if not math.isclose(
        float(geometry.channel_width_hz),
        grid.channel_width_hz,
        rel_tol=1e-7,
        abs_tol=1e-9,
    ):
        raise V0P6ContractError(
            "native and proxy-carrier channel widths do not match"
        )
    if df_mhz < 0.0:
        # Freeze one physical summation order irrespective of archive axis
        # direction: raw data and its coordinate are reversed together once.
        data = data[:, ::-1]
        frequency = frequency[::-1].copy()
    if frequency.size != int(geometry.channel_count):
        raise V0P6ContractError(
            "native frequency array does not match the frozen channel count"
        )
    observed_low_hz = float(frequency[0]) * 1e6
    observed_high_hz = float(frequency[-1]) * 1e6
    expected_high_hz = float(geometry.raw_zero_hz) + (
        int(geometry.channel_count) - 1
    ) * float(geometry.channel_width_hz)
    endpoint_tolerance_hz = max(
        2e-7,
        4.0 * math.ulp(float(geometry.raw_zero_hz)),
        4.0 * math.ulp(expected_high_hz),
    )
    if not math.isclose(
        observed_low_hz,
        float(geometry.raw_zero_hz),
        rel_tol=0.0,
        abs_tol=endpoint_tolerance_hz,
    ) or not math.isclose(
        observed_high_hz,
        expected_high_hz,
        rel_tol=0.0,
        abs_tol=endpoint_tolerance_hz,
    ):
        raise V0P6ContractError(
            "native frequency array endpoints do not match frozen Hz geometry"
        )
    return data, frequency, factor, width


def _require_filter_coverage(
    indices: np.ndarray,
    native_channel_count: int,
    half_width: int,
    integration_index: int,
) -> None:
    minimum = int(np.min(indices))
    maximum = int(np.max(indices))
    if minimum < half_width or maximum >= native_channel_count - half_width:
        raise V0P6CoverageError(
            "native extraction does not cover filtered q track: "
            f"integration={integration_index}, mapped=[{minimum},{maximum}], "
            f"allowed=[{half_width},{native_channel_count - half_width - 1}]"
        )


def _require_injective_q_mapping(
    indices: np.ndarray,
    integration_index: int,
    prior_index: int | None = None,
) -> int:
    """Require a strict q-to-raw mapping, including across chunk boundaries."""
    mapped = np.asarray(indices, dtype=np.int64)
    if mapped.ndim != 1 or mapped.size == 0:
        raise V0P6ContractError("q-to-raw mapping chunk must be non-empty")
    if prior_index is None:
        differences = np.diff(mapped)
    else:
        differences = np.diff(
            np.concatenate((np.asarray([prior_index], dtype=np.int64), mapped))
        )
    if np.any(differences <= 0):
        raise V0P6ContractError(
            "q-to-raw nearest-channel mapping is not injective and monotonic: "
            f"integration={integration_index}"
        )
    if np.any(~np.isin(np.abs(differences), (1, 2))):
        raise V0P6ContractError(
            "q-to-raw mapping step is outside the frozen {1,2} contract: "
            f"integration={integration_index}"
        )
    return int(mapped[-1])


def float32_array_sha256(values: np.ndarray) -> str:
    """Hash a C-order array with canonical little-endian float32 bytes."""
    array = np.asarray(values)
    if not np.issubdtype(array.dtype, np.floating):
        raise V0P6ContractError("hashed cache payload must be floating point")
    payload = np.ascontiguousarray(array, dtype="<f4").tobytes()
    return hashlib.sha256(payload).hexdigest()


def factor_table_sha256(values: np.ndarray) -> str:
    """Hash a finite [template, integration] factor table as ``<f8``."""
    array = np.asarray(values)
    if array.ndim != 2 or not np.issubdtype(array.dtype, np.floating):
        raise V0P6ContractError("factor table must be a floating matrix")
    if not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise V0P6ContractError("factor table must be finite and positive")
    return hashlib.sha256(
        np.ascontiguousarray(array, dtype="<f8").tobytes()
    ).hexdigest()


@dataclass(frozen=True)
class NativeFilterCachePlan:
    """Frozen native-center interval for one scan/window/width cache."""

    geometry: NativeFrequencyGeometry
    window_id: str
    scan_label: str
    scan_kind: str
    source_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    scan_inventory_sha256: str
    factor_scan_selection_sha256: str
    template_bank_sha256: str
    width_channels: int
    integration_count: int
    raw_center_start: int
    raw_center_stop: int
    proxy_grid_sha256: str
    factor_table_sha256: str
    factor_row_sha256s: tuple[str, ...]
    payload_shape: tuple[int, int]
    payload_nbytes: int
    plan_sha256: str


@dataclass(frozen=True)
class NativeFilterCache:
    """Read-only in-memory view matching an atomic on-disk cache payload."""

    plan: NativeFilterCachePlan
    values: np.ndarray = field(repr=False)
    payload_sha256: str


def _native_filter_cache_plan_payload(
    plan: NativeFilterCachePlan,
) -> dict[str, Any]:
    return {
        "window_id": str(plan.window_id),
        "scan_label": str(plan.scan_label),
        "scan_kind": str(plan.scan_kind),
        "source_sha256": _frozen_sha256(plan.source_sha256, "cache source"),
        "factor_basis_sha256": _frozen_sha256(
            plan.factor_basis_sha256, "factor-basis identity"
        ),
        "factor_basis_labels_sha256": _frozen_sha256(
            plan.factor_basis_labels_sha256, "factor-basis labels identity"
        ),
        "scan_inventory_sha256": _frozen_sha256(
            plan.scan_inventory_sha256, "scan-inventory identity"
        ),
        "factor_scan_selection_sha256": _frozen_sha256(
            plan.factor_scan_selection_sha256,
            "factor scan-selection identity",
        ),
        "template_bank_sha256": _frozen_sha256(
            plan.template_bank_sha256, "template-bank identity"
        ),
        "raw_zero_hz": float(plan.geometry.raw_zero_hz),
        "native_channel_width_hz": float(plan.geometry.channel_width_hz),
        "native_channel_count": _strict_int(
            plan.geometry.channel_count, "native channel count"
        ),
        "width_channels": _strict_widths((plan.width_channels,))[0],
        "integration_count": _strict_int(
            plan.integration_count, "integration count"
        ),
        "raw_center_start": _strict_int(
            plan.raw_center_start, "raw center start"
        ),
        "raw_center_stop": _strict_int(plan.raw_center_stop, "raw center stop"),
        "proxy_grid_sha256": _frozen_sha256(
            plan.proxy_grid_sha256, "proxy-grid identity"
        ),
        "factor_table_sha256": _frozen_sha256(
            plan.factor_table_sha256, "factor-table identity"
        ),
        "factor_row_sha256s": [
            _frozen_sha256(item, "factor-row identity")
            for item in plan.factor_row_sha256s
        ],
        "payload_shape": [
            _strict_int(item, "cache payload dimension")
            for item in plan.payload_shape
        ],
        "payload_dtype": "<f4",
        "payload_nbytes": _strict_int(
            plan.payload_nbytes, "cache payload byte count"
        ),
    }


def validate_native_filter_cache_plan(plan: NativeFilterCachePlan) -> None:
    """Recompute every derived cache-plan field and its canonical digest."""
    payload = _native_filter_cache_plan_payload(plan)
    if not payload["window_id"] or not payload["scan_label"]:
        raise V0P6ContractError("cache window/scan identities must be non-empty")
    if payload["scan_kind"] not in {"on", "off"}:
        raise V0P6ContractError("cache scan kind must be 'on' or 'off'")
    start = payload["raw_center_start"]
    stop = payload["raw_center_stop"]
    count = payload["native_channel_count"]
    half_width = payload["width_channels"] // 2
    if start < half_width or stop <= start or stop > count - half_width:
        raise V0P6CoverageError("cache plan has an invalid native-center interval")
    expected_shape = (payload["integration_count"], stop - start)
    if tuple(payload["payload_shape"]) != expected_shape:
        raise V0P6ContractError("cache plan payload shape is inconsistent")
    expected_nbytes = math.prod(expected_shape) * np.dtype("<f4").itemsize
    if payload["payload_nbytes"] != expected_nbytes:
        raise V0P6ContractError("cache plan payload byte count is inconsistent")
    if not payload["factor_row_sha256s"]:
        raise V0P6ContractError("cache plan lacks factor-row identities")
    observed = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if observed != plan.plan_sha256:
        raise V0P6ContractError("native filter cache plan SHA-256 changed")


def native_filter_cache_plan_from_record(
    record: Mapping[str, Any],
    *,
    expected_plan_sha256: str,
) -> NativeFilterCachePlan:
    """Rehydrate a persisted cache plan against an independent digest.

    Cache manifests already carry the complete plan payload.  This strict
    constructor turns that canonical JSON record back into the typed plan
    needed by the disk verifier without trusting a process-local object.
    """
    if not isinstance(record, Mapping):
        raise V0P6ContractError("native filter cache plan record is not a mapping")
    try:
        detached = json.loads(canonical_json_bytes(dict(record)))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(
            "native filter cache plan record is not canonical finite JSON"
        ) from error
    expected_fields = {
        "window_id",
        "scan_label",
        "scan_kind",
        "source_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "factor_scan_selection_sha256",
        "template_bank_sha256",
        "raw_zero_hz",
        "native_channel_width_hz",
        "native_channel_count",
        "width_channels",
        "integration_count",
        "raw_center_start",
        "raw_center_stop",
        "proxy_grid_sha256",
        "factor_table_sha256",
        "factor_row_sha256s",
        "payload_shape",
        "payload_dtype",
        "payload_nbytes",
    }
    if set(detached) != expected_fields:
        raise V0P6ContractError("native filter cache plan record schema changed")
    if detached["payload_dtype"] != "<f4":
        raise V0P6ContractError("native filter cache plan dtype changed")
    expected_digest = _frozen_sha256(
        expected_plan_sha256, "expected native filter cache plan identity"
    )
    observed_digest = hashlib.sha256(canonical_json_bytes(detached)).hexdigest()
    if observed_digest != expected_digest:
        raise V0P6IncompleteError(
            "native filter cache plan differs from its independent identity"
        )
    raw_zero_hz = _finite_json_number(
        detached["raw_zero_hz"], "native raw-zero frequency"
    )
    channel_width_hz = _finite_json_number(
        detached["native_channel_width_hz"], "native channel width"
    )
    if channel_width_hz <= 0.0:
        raise V0P6ContractError("native channel width must be positive")
    geometry = NativeFrequencyGeometry(
        raw_zero_hz=raw_zero_hz,
        channel_width_hz=channel_width_hz,
        channel_count=_strict_int(
            detached["native_channel_count"], "native channel count"
        ),
    )
    shape_record = detached["payload_shape"]
    if not isinstance(shape_record, list) or len(shape_record) != 2:
        raise V0P6ContractError("native filter cache payload shape changed")
    rows = detached["factor_row_sha256s"]
    if not isinstance(rows, list):
        raise V0P6ContractError("native filter cache factor-row inventory changed")
    plan = NativeFilterCachePlan(
        geometry=geometry,
        window_id=str(detached["window_id"]),
        scan_label=str(detached["scan_label"]),
        scan_kind=str(detached["scan_kind"]),
        source_sha256=_frozen_sha256(detached["source_sha256"], "cache source"),
        factor_basis_sha256=_frozen_sha256(
            detached["factor_basis_sha256"], "factor-basis identity"
        ),
        factor_basis_labels_sha256=_frozen_sha256(
            detached["factor_basis_labels_sha256"],
            "factor-basis labels identity",
        ),
        scan_inventory_sha256=_frozen_sha256(
            detached["scan_inventory_sha256"], "scan-inventory identity"
        ),
        factor_scan_selection_sha256=_frozen_sha256(
            detached["factor_scan_selection_sha256"],
            "factor scan-selection identity",
        ),
        template_bank_sha256=_frozen_sha256(
            detached["template_bank_sha256"], "template-bank identity"
        ),
        width_channels=_strict_int(detached["width_channels"], "spectral width"),
        integration_count=_strict_int(
            detached["integration_count"], "integration count"
        ),
        raw_center_start=_strict_int(
            detached["raw_center_start"], "raw center start"
        ),
        raw_center_stop=_strict_int(
            detached["raw_center_stop"], "raw center stop"
        ),
        proxy_grid_sha256=_frozen_sha256(
            detached["proxy_grid_sha256"], "proxy-grid identity"
        ),
        factor_table_sha256=_frozen_sha256(
            detached["factor_table_sha256"], "factor-table identity"
        ),
        factor_row_sha256s=tuple(
            _frozen_sha256(item, "factor-row identity") for item in rows
        ),
        payload_shape=tuple(
            _strict_int(item, "cache payload dimension") for item in shape_record
        ),
        payload_nbytes=_strict_int(
            detached["payload_nbytes"], "cache payload byte count"
        ),
        plan_sha256=expected_digest,
    )
    validate_native_filter_cache_plan(plan)
    if _native_filter_cache_plan_payload(plan) != detached:
        raise V0P6IncompleteError(
            "rehydrated native filter cache plan changed its canonical record"
        )
    return plan


def plan_native_filter_cache(
    geometry: NativeFrequencyGeometry,
    template_factor_table: np.ndarray,
    grid: ProxyCarrierGrid,
    width: int,
    *,
    window_id: str,
    scan_label: str,
    scan_kind: str,
    source_sha256: str,
    factor_basis_sha256_value: str,
    factor_basis_labels_sha256_value: str,
    scan_inventory_sha256_value: str,
    factor_scan_selection_sha256_value: str,
    template_bank_sha256_value: str,
) -> NativeFilterCachePlan:
    """Plan a synthetic/reference native cache for every template.

    This data-source-agnostic helper intentionally accepts a caller-supplied
    source digest.  Telescope-backed M37 production must instead use
    ``source_v0p6.plan_m37_production_native_filter_cache``, which derives the
    digest from a validated normalized-scan product.
    """
    width = _strict_widths((width,))[0]
    factors = np.asarray(template_factor_table, dtype=np.float64)
    if factors.ndim != 2 or factors.shape[0] < 1 or factors.shape[1] < 1:
        raise V0P6ContractError(
            "cache planning needs a [template, integration] factor table"
        )
    factor_digest = factor_table_sha256(factors)
    if float(np.min(factors)) < 1.0 or float(np.max(factors)) >= 2.0:
        raise V0P6ContractError(
            "cache planning requires the frozen injective {1,2}-step factor range"
        )
    endpoints_hz = np.stack(
        (
            grid.support_hz[0] * factors,
            grid.support_hz[-1] * factors,
        ),
        axis=-1,
    )
    endpoint_indices = nearest_native_indices(geometry, endpoints_hz)
    raw_start = int(np.min(endpoint_indices))
    raw_stop = int(np.max(endpoint_indices)) + 1
    half_width = width // 2
    _require_filter_coverage(
        np.asarray([raw_start, raw_stop - 1], dtype=np.int64),
        geometry.channel_count,
        half_width,
        -1,
    )
    payload_shape = (int(factors.shape[1]), raw_stop - raw_start)
    payload_nbytes = math.prod(payload_shape) * np.dtype("<f4").itemsize
    grid_digest = proxy_carrier_grid_sha256(grid)
    row_digests = tuple(float64_vector_sha256(row) for row in factors)
    partial = NativeFilterCachePlan(
        geometry=geometry,
        window_id=str(window_id),
        scan_label=str(scan_label),
        scan_kind=str(scan_kind).lower(),
        source_sha256=_frozen_sha256(source_sha256, "cache source"),
        factor_basis_sha256=_frozen_sha256(
            factor_basis_sha256_value, "factor-basis identity"
        ),
        factor_basis_labels_sha256=_frozen_sha256(
            factor_basis_labels_sha256_value, "factor-basis labels identity"
        ),
        scan_inventory_sha256=_frozen_sha256(
            scan_inventory_sha256_value, "scan-inventory identity"
        ),
        factor_scan_selection_sha256=_frozen_sha256(
            factor_scan_selection_sha256_value,
            "factor scan-selection identity",
        ),
        template_bank_sha256=_frozen_sha256(
            template_bank_sha256_value, "template-bank identity"
        ),
        width_channels=width,
        integration_count=int(factors.shape[1]),
        raw_center_start=raw_start,
        raw_center_stop=raw_stop,
        proxy_grid_sha256=grid_digest,
        factor_table_sha256=factor_digest,
        factor_row_sha256s=row_digests,
        payload_shape=payload_shape,
        payload_nbytes=payload_nbytes,
        plan_sha256="",
    )
    payload = _native_filter_cache_plan_payload(partial)
    plan = NativeFilterCachePlan(
        **{
            **partial.__dict__,
            "plan_sha256": hashlib.sha256(
                canonical_json_bytes(payload)
            ).hexdigest(),
        }
    )
    validate_native_filter_cache_plan(plan)
    return plan


def plan_m37_native_filter_cache(
    geometry: NativeFrequencyGeometry,
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    grid: ProxyCarrierGrid,
    width: int,
    *,
    window_id: str,
    scan_label: str,
    source_sha256: str,
) -> NativeFilterCachePlan:
    """Plan a synthetic/reference cache with canonical M37 factor contracts.

    This helper preserves compact synthetic tests and therefore still accepts
    ``source_sha256``.  It is not the production source boundary; use
    ``source_v0p6.plan_m37_production_native_filter_cache`` for telescope data.
    """
    validate_m37_factor_basis_scan_inventory(factor_basis, scan_definitions)
    validate_template_factor_table(
        factor_table,
        factor_basis,
        make_line_template_bank(),
        expected_template_bank_sha256=M37_BANK_SHA256,
    )
    if proxy_carrier_grid_sha256(grid) != proxy_carrier_grid_sha256(
        make_m37_proxy_carrier_grid(window_id)
    ):
        raise V0P6ContractError("cache plan did not receive the M37 q grid")
    label = str(scan_label)
    matches = [
        definition
        for definition in scan_definitions
        if str(definition["label"]) == label
    ]
    if len(matches) != 1:
        raise V0P6ContractError("M37 cache plan requires one known scan")
    definition = matches[0]
    scan_kind = str(definition["kind"]).lower()
    scan_factors = factor_table_for_scan(factor_table, factor_basis, label)
    return plan_native_filter_cache(
        geometry,
        scan_factors,
        grid,
        width,
        window_id=window_id,
        scan_label=label,
        scan_kind=scan_kind,
        source_sha256=source_sha256,
        factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
        factor_scan_selection_sha256_value=(
            M37_FACTOR_SCAN_SELECTION_SHA256S[label]
        ),
        template_bank_sha256_value=M37_BANK_SHA256,
    )


def build_native_filter_cache(
    normalized: np.ndarray,
    frequency_mhz: np.ndarray,
    plan: NativeFilterCachePlan,
) -> NativeFilterCache:
    """Apply one native float32 boxcar for synthetic/reference inputs.

    The generic array API does not attest extraction or normalization.
    Telescope-backed M37 production must use
    ``source_v0p6.build_m37_production_native_filter_cache``.
    """
    validate_native_filter_cache_plan(plan)
    data = np.asarray(normalized, dtype=np.float32)
    frequency = np.asarray(frequency_mhz, dtype=np.float64)
    if data.ndim != 2 or data.shape != (
        plan.integration_count,
        plan.geometry.channel_count,
    ):
        raise V0P6ContractError("cache source shape changed from its plan")
    _, df_mhz = _native_grid_parameters(frequency)
    if df_mhz < 0.0:
        data = data[:, ::-1]
        frequency = frequency[::-1].copy()
    expected_high_hz = plan.geometry.raw_zero_hz + (
        plan.geometry.channel_count - 1
    ) * plan.geometry.channel_width_hz
    if (
        not math.isclose(
            float(frequency[0]) * 1e6,
            plan.geometry.raw_zero_hz,
            rel_tol=0.0,
            abs_tol=2e-7,
        )
        or not math.isclose(
            float(frequency[-1]) * 1e6,
            expected_high_hz,
            rel_tol=0.0,
            abs_tol=2e-7,
        )
    ):
        raise V0P6ContractError("cache source frequency geometry changed")
    filtered = normalized_boxcar(data, plan.width_channels)
    values = np.array(
        filtered[:, plan.raw_center_start : plan.raw_center_stop],
        dtype=np.float32,
        order="C",
        copy=True,
    )
    if values.shape != plan.payload_shape or values.nbytes != plan.payload_nbytes:
        raise V0P6ContractError("native filter cache payload shape changed")
    if not np.all(np.isfinite(values)):
        raise V0P6ContractError("native filter cache contains non-finite values")
    digest = float32_array_sha256(values)
    values.setflags(write=False)
    return NativeFilterCache(plan=plan, values=values, payload_sha256=digest)


def _cache_values_for_gather(
    cache: Any,
) -> tuple[NativeFilterCachePlan, np.ndarray]:
    """Validate a reference cache or an already-verified disk-cache handle."""
    if isinstance(cache, NativeFilterCache):
        plan = cache.plan
        validate_native_filter_cache_plan(plan)
        if cache.values.flags.writeable or (
            float32_array_sha256(cache.values) != cache.payload_sha256
        ):
            raise V0P6IncompleteError("sealed native filter cache changed")
        values = cache.values
    else:
        # Lazy import avoids a module-import cycle: the disk format imports
        # this module's frozen plan and hashing primitives.
        from .native_cache_v0p6 import DiskNativeFilterCache

        if not isinstance(cache, DiskNativeFilterCache):
            raise V0P6ContractError("unknown native filter cache handle")
        plan = cache.plan
        validate_native_filter_cache_plan(plan)
        _frozen_sha256(cache.payload_sha256, "cache-payload identity")
        values = cache._values_for_gather()
    if (
        values.flags.writeable
        or values.dtype != np.dtype("<f4")
        or not values.flags.c_contiguous
        or values.shape != plan.payload_shape
        or values.nbytes != plan.payload_nbytes
    ):
        raise V0P6IncompleteError("native filter cache payload layout changed")
    return plan, values


def gather_filtered_native(
    cache: Any,
    factors: np.ndarray,
    grid: ProxyCarrierGrid,
    *,
    chunk_bins: int = 131_072,
    return_support: bool = False,
) -> np.ndarray:
    """Gather an already-native-filtered cache without re-running a boxcar."""
    plan, cache_values = _cache_values_for_gather(cache)
    if proxy_carrier_grid_sha256(grid) != plan.proxy_grid_sha256:
        raise V0P6ContractError("cache and proxy-grid identities differ")
    factor = np.asarray(factors, dtype=np.float64)
    if factor.shape != (plan.integration_count,):
        raise V0P6ContractError("factor count does not match the filter cache")
    if not np.all(np.isfinite(factor)) or np.any(factor <= 0.0):
        raise V0P6ContractError("all track factors must be finite and positive")
    if float64_vector_sha256(factor) not in plan.factor_row_sha256s:
        raise V0P6ContractError(
            "requested factor row is absent from the planned template table"
        )
    chunk_bins = _strict_int(chunk_bins, "q-gather chunk size")
    if chunk_bins < 1:
        raise V0P6ContractError("q-gather chunk size must be positive")
    accumulator = np.zeros(grid.support_bin_count, dtype=np.float32)
    for integration_index in range(plan.integration_count):
        prior_index: int | None = None
        for start in range(0, grid.support_bin_count, chunk_bins):
            stop = min(start + chunk_bins, grid.support_bin_count)
            indices = nearest_native_indices(
                plan.geometry,
                grid.support_hz[start:stop] * float(factor[integration_index]),
            )
            prior_index = _require_injective_q_mapping(
                indices, integration_index, prior_index
            )
            if (
                int(np.min(indices)) < plan.raw_center_start
                or int(np.max(indices)) >= plan.raw_center_stop
            ):
                raise V0P6CoverageError(
                    "native filter cache does not cover the requested q track"
                )
            local_indices = indices - plan.raw_center_start
            accumulator[start:stop] += cache_values[
                integration_index, local_indices
            ]
    accumulator /= np.float32(math.sqrt(plan.integration_count))
    if return_support:
        return accumulator
    return np.asarray(accumulator[grid.score_slice], dtype=np.float32)


def native_filter_then_q_gather(
    normalized: np.ndarray,
    frequency_mhz: np.ndarray,
    geometry: NativeFrequencyGeometry,
    factors: np.ndarray,
    grid: ProxyCarrierGrid,
    width: int,
    *,
    chunk_bins: int = 131_072,
    return_support: bool = False,
) -> np.ndarray:
    """Synthetic/reference wrapper: filter, gather, integrate, and crop.

    Production orchestration uses :func:`build_native_filter_cache` followed
    by :func:`gather_filtered_native` so each native width is filtered once.
    Only q mapping is chunked and the integration accumulation order is fixed.
    """
    data, frequency, factor, width = _validate_gather_inputs(
        normalized, frequency_mhz, geometry, factors, grid, width
    )
    chunk_bins = _strict_int(chunk_bins, "q-gather chunk size")
    if chunk_bins < 1:
        raise V0P6ContractError("q-gather chunk size must be positive")
    filtered_native = normalized_boxcar(data, width)
    accumulator = np.zeros(grid.support_bin_count, dtype=np.float32)
    half_width = width // 2
    for integration_index in range(data.shape[0]):
        row_factor = float(factor[integration_index])
        prior_index: int | None = None
        for start in range(0, grid.support_bin_count, chunk_bins):
            stop = min(start + chunk_bins, grid.support_bin_count)
            requested_hz = grid.support_hz[start:stop] * row_factor
            indices = nearest_native_indices(geometry, requested_hz)
            prior_index = _require_injective_q_mapping(
                indices, integration_index, prior_index
            )
            _require_filter_coverage(
                indices, frequency.size, half_width, integration_index
            )
            accumulator[start:stop] += filtered_native[integration_index, indices]
    accumulator /= np.float32(math.sqrt(data.shape[0]))
    if return_support:
        return accumulator
    return np.asarray(accumulator[grid.score_slice], dtype=np.float32)


def materialized_reference_gather(
    normalized: np.ndarray,
    frequency_mhz: np.ndarray,
    geometry: NativeFrequencyGeometry,
    factors: np.ndarray,
    grid: ProxyCarrierGrid,
    width: int,
    *,
    maximum_mapping_cells: int = 2_000_000,
    return_support: bool = False,
) -> np.ndarray:
    """Small fully materialized reference for known-answer validation only."""
    data, frequency, factor, width = _validate_gather_inputs(
        normalized, frequency_mhz, geometry, factors, grid, width
    )
    cells = data.shape[0] * grid.support_bin_count
    maximum_mapping_cells = _strict_int(
        maximum_mapping_cells, "materialized mapping-cell capacity"
    )
    if maximum_mapping_cells < 1:
        raise V0P6ContractError(
            "materialized mapping-cell capacity must be positive"
        )
    if cells > maximum_mapping_cells:
        raise V0P6CapacityError(
            f"materialized reference mapping would allocate {cells} cells"
        )
    requested_hz = factor[:, None] * grid.support_hz[None, :]
    indices = nearest_native_indices(geometry, requested_hz)
    half_width = width // 2
    for integration_index in range(data.shape[0]):
        _require_injective_q_mapping(
            indices[integration_index], integration_index
        )
        _require_filter_coverage(
            indices[integration_index],
            frequency.size,
            half_width,
            integration_index,
        )
    filtered_native = normalized_boxcar(data, width)
    gathered = np.take_along_axis(filtered_native, indices, axis=1)
    integrated = np.sum(gathered, axis=0, dtype=np.float32)
    integrated /= np.float32(math.sqrt(data.shape[0]))
    if return_support:
        return integrated
    return np.asarray(integrated[grid.score_slice], dtype=np.float32)


@dataclass(frozen=True)
class FactorLabel:
    """One row identity in the all-scan Cartesian factor basis."""

    scan_index: int
    scan_label: str
    integration_index: int

    def as_record(self) -> dict[str, Any]:
        return {
            "scan_index": self.scan_index,
            "scan_label": self.scan_label,
            "integration_index": self.integration_index,
        }


@dataclass(frozen=True)
class FactorBasis:
    """Read-only Cartesian factor basis certified before spectral access."""

    times_mjd: np.ndarray = field(repr=False)
    labels: tuple[FactorLabel, ...]
    baseline: np.ndarray = field(repr=False)
    orbital: np.ndarray = field(repr=False)
    basis_sha256: str
    labels_sha256: str


def factor_basis_sha256(
    times_mjd: np.ndarray,
    baseline: np.ndarray,
    orbital: np.ndarray,
) -> str:
    """Reproduce the frozen all-scan ``<f8`` factor-basis digest."""
    arrays = (
        np.asarray(times_mjd),
        np.asarray(baseline),
        np.asarray(orbital),
    )
    if arrays[0].ndim != 1 or arrays[1].shape != arrays[0].shape:
        raise V0P6ContractError("factor times and baseline must be equal vectors")
    if arrays[2].shape != (arrays[0].size, 2) or arrays[0].size < 1:
        raise V0P6ContractError("orbital factor basis must have shape [row, 2]")
    if any(not np.issubdtype(item.dtype, np.floating) for item in arrays):
        raise V0P6ContractError("factor-basis arrays must be floating point")
    if any(not np.all(np.isfinite(item)) for item in arrays):
        raise V0P6ContractError("factor-basis arrays must be finite")
    payload = b"".join(
        np.ascontiguousarray(item, dtype="<f8").tobytes() for item in arrays
    )
    return hashlib.sha256(payload).hexdigest()


def make_factor_basis_from_arrays(
    times_mjd: np.ndarray,
    labels: Sequence[FactorLabel | Mapping[str, Any]],
    baseline: np.ndarray,
    orbital: np.ndarray,
    *,
    expected_sha256: str | None,
    expected_labels_sha256: str | None = None,
) -> FactorBasis:
    """Validate and seal a basis constructed by metadata-only astronomy code."""
    times = np.array(times_mjd, dtype=np.float64, order="C", copy=True)
    base = np.array(baseline, dtype=np.float64, order="C", copy=True)
    orbit = np.array(orbital, dtype=np.float64, order="C", copy=True)
    digest = factor_basis_sha256(times, base, orbit)
    if expected_sha256 is not None and digest != _frozen_sha256(
        expected_sha256, "factor-basis identity"
    ):
        raise V0P6ContractError("factor-basis SHA-256 changed")
    if times.size > 1 and np.any(np.diff(times) <= 0.0):
        raise V0P6ContractError("factor-basis times must be strictly increasing")
    if np.any(base <= 0.0):
        raise V0P6ContractError("factor-basis baseline must remain positive")

    normalized_labels: list[FactorLabel] = []
    for raw_label in labels:
        if isinstance(raw_label, FactorLabel):
            label = FactorLabel(
                scan_index=_strict_int(raw_label.scan_index, "scan index"),
                scan_label=str(raw_label.scan_label),
                integration_index=_strict_int(
                    raw_label.integration_index, "integration index"
                ),
            )
        elif isinstance(raw_label, Mapping) and set(raw_label) == {
            "scan_index",
            "scan_label",
            "integration_index",
        }:
            label = FactorLabel(
                scan_index=_strict_int(raw_label["scan_index"], "scan index"),
                scan_label=str(raw_label["scan_label"]),
                integration_index=_strict_int(
                    raw_label["integration_index"], "integration index"
                ),
            )
        else:
            raise V0P6ContractError("factor-basis label has an invalid schema")
        if not label.scan_label:
            raise V0P6ContractError("factor-basis scan label must be non-empty")
        normalized_labels.append(label)
    if len(normalized_labels) != times.size:
        raise V0P6ContractError("factor-basis labels do not match its row count")

    expected_scan_index = 0
    expected_integration_index = 0
    current_scan_label: str | None = None
    for label in normalized_labels:
        if label.scan_index == expected_scan_index + 1:
            if expected_integration_index == 0:
                raise V0P6ContractError("factor-basis scan group is empty")
            expected_scan_index += 1
            expected_integration_index = 0
            current_scan_label = None
        if label.scan_index != expected_scan_index:
            raise V0P6ContractError(
                "factor-basis scan indices must form contiguous ordered groups"
            )
        if label.integration_index != expected_integration_index:
            raise V0P6ContractError(
                "factor-basis integration indices must start at zero and be sequential"
            )
        if current_scan_label is None:
            current_scan_label = label.scan_label
        elif label.scan_label != current_scan_label:
            raise V0P6ContractError("factor-basis label changed within a scan")
        expected_integration_index += 1
    group_labels = [
        label.scan_label
        for label in normalized_labels
        if label.integration_index == 0
    ]
    if len(group_labels) != len(set(group_labels)):
        raise V0P6ContractError("factor-basis scan labels must be unique")

    records = [label.as_record() for label in normalized_labels]
    labels_digest = hashlib.sha256(canonical_json_bytes(records)).hexdigest()
    if expected_sha256 == M37_FACTOR_BASIS_SHA256 and (
        expected_labels_sha256 is None
    ):
        expected_labels_sha256 = M37_FACTOR_BASIS_LABELS_SHA256
    if expected_labels_sha256 is not None and labels_digest != _frozen_sha256(
        expected_labels_sha256, "factor-basis labels identity"
    ):
        raise V0P6ContractError("factor-basis labels SHA-256 changed")
    for item in (times, base, orbit):
        item.setflags(write=False)
    return FactorBasis(
        times_mjd=times,
        labels=tuple(normalized_labels),
        baseline=base,
        orbital=orbit,
        basis_sha256=digest,
        labels_sha256=labels_digest,
    )


def make_factor_basis_from_metadata(
    upstream: Mapping[str, Any],
    *,
    expected_sha256: str = M37_FACTOR_BASIS_SHA256,
    expected_labels_sha256: str | None = M37_FACTOR_BASIS_LABELS_SHA256,
) -> FactorBasis:
    """Construct the frozen basis using metadata only and lazy Astropy imports."""
    from astropy.time import Time

    from .orbit import (
        DAY_S,
        celestial_frequency_factor,
        make_location,
        make_target,
    )

    values = []
    labels: list[dict[str, Any]] = []
    scans = upstream.get("scans")
    if not isinstance(scans, Sequence) or not scans:
        raise V0P6ContractError("factor metadata lacks a scan inventory")
    m37_scan_indices_for_kind(scans, "on")
    for scan_index, scan in enumerate(scans):
        header = scan["expected_header"]
        count = _strict_int(header["dataset_shape"][0], "integration count")
        scan_times = Time(
            float(header["tstart_mjd"])
            + (np.arange(count) + 0.5) * float(header["tsamp_s"]) / DAY_S,
            format="mjd",
            scale="utc",
        )
        values.extend(scan_times)
        labels.extend(
            {
                "scan_index": scan_index,
                "scan_label": scan["label"],
                "integration_index": integration_index,
            }
            for integration_index in range(count)
        )
    times = Time(values)
    target = make_target(upstream["target"])
    location = make_location(upstream["observatory"])
    baseline = celestial_frequency_factor(
        times, 0.0, 0.0, target, location, upstream["orbit"]
    )[0]
    phase_zero = celestial_frequency_factor(
        times, 1.0, 0.0, target, location, upstream["orbit"]
    )[0]
    phase_quarter = celestial_frequency_factor(
        times, 1.0, 0.25, target, location, upstream["orbit"]
    )[0]
    orbital = np.column_stack(
        (phase_zero - baseline, phase_quarter - baseline)
    )
    basis = make_factor_basis_from_arrays(
        times.utc.mjd,
        labels,
        baseline,
        orbital,
        expected_sha256=expected_sha256,
        expected_labels_sha256=expected_labels_sha256,
    )
    return basis


def template_factors_from_basis(
    basis: FactorBasis,
    template: Mapping[str, Any],
    *,
    scan_label: str | None = None,
) -> np.ndarray:
    """Evaluate ``baseline + orbital @ [coefficient_x, coefficient_y]``."""
    validate_factor_basis(basis)
    try:
        coefficient = np.array(
            [template["coefficient_x"], template["coefficient_y"]],
            dtype=np.float64,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V0P6ContractError("template lacks finite Cartesian coefficients") from error
    if coefficient.shape != (2,) or not np.all(np.isfinite(coefficient)):
        raise V0P6ContractError("template lacks finite Cartesian coefficients")
    factor = np.asarray(
        basis.baseline + basis.orbital @ coefficient,
        dtype=np.float64,
    )
    if not np.all(np.isfinite(factor)) or np.any(factor <= 0.0):
        raise V0P6ContractError("template basis produced invalid factors")
    if scan_label is not None:
        scan_label = str(scan_label)
        rows = np.fromiter(
            (label.scan_label == scan_label for label in basis.labels),
            dtype=bool,
            count=len(basis.labels),
        )
        if not np.any(rows):
            raise V0P6ContractError("scan label is absent from the factor basis")
        factor = factor[rows]
    factor = np.array(factor, dtype=np.float64, order="C", copy=True)
    factor.setflags(write=False)
    return factor


def validate_factor_basis(basis: FactorBasis) -> None:
    """Verify all sealed basis arrays and label identities without astronomy calls."""
    if any(
        item.flags.writeable
        for item in (basis.times_mjd, basis.baseline, basis.orbital)
    ) or factor_basis_sha256(
        basis.times_mjd, basis.baseline, basis.orbital
    ) != basis.basis_sha256:
        raise V0P6IncompleteError("sealed factor-basis identity changed")
    if hashlib.sha256(
        canonical_json_bytes([label.as_record() for label in basis.labels])
    ).hexdigest() != basis.labels_sha256:
        raise V0P6IncompleteError("sealed factor-basis labels changed")


@dataclass(frozen=True)
class TemplateFactorTable:
    """Read-only factors for every frozen template and all basis rows."""

    factors: np.ndarray = field(repr=False)
    template_bank_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    factor_table_sha256: str


def make_template_factor_table(
    basis: FactorBasis,
    template_bank: Sequence[dict[str, Any]],
    *,
    expected_template_bank_sha256: str,
) -> TemplateFactorTable:
    """Materialize only the small metadata-derived [template, basis-row] table."""
    bank = json.loads(canonical_json_bytes(list(template_bank)))
    bank_digest = template_bank_sha256(bank)
    if bank_digest != _frozen_sha256(
        expected_template_bank_sha256, "template-bank identity"
    ):
        raise V0P6ContractError("factor table's template-bank identity changed")
    for expected_index, template in enumerate(bank):
        if _strict_int(template.get("template_index"), "template index") != expected_index:
            raise V0P6ContractError(
                "factor-table templates must be in canonical sequential order"
            )
    factors = np.stack(
        [template_factors_from_basis(basis, template) for template in bank],
        axis=0,
    )
    factors = np.array(factors, dtype=np.float64, order="C", copy=True)
    digest = factor_table_sha256(factors)
    factors.setflags(write=False)
    return TemplateFactorTable(
        factors=factors,
        template_bank_sha256=bank_digest,
        factor_basis_sha256=basis.basis_sha256,
        factor_basis_labels_sha256=basis.labels_sha256,
        factor_table_sha256=digest,
    )


def validate_template_factor_table(
    table: TemplateFactorTable,
    basis: FactorBasis,
    template_bank: Sequence[dict[str, Any]],
    *,
    expected_template_bank_sha256: str,
) -> None:
    """Recompute every factor from its sealed basis and canonical bank."""
    validate_factor_basis(basis)
    bank = json.loads(canonical_json_bytes(list(template_bank)))
    bank_digest = template_bank_sha256(bank)
    expected_bank_digest = _frozen_sha256(
        expected_template_bank_sha256, "template-bank identity"
    )
    if bank_digest != expected_bank_digest:
        raise V0P6ContractError("factor-table validation bank identity changed")
    if (
        table.template_bank_sha256 != bank_digest
        or table.factor_basis_sha256 != basis.basis_sha256
        or table.factor_basis_labels_sha256 != basis.labels_sha256
        or table.factors.flags.writeable
        or factor_table_sha256(table.factors) != table.factor_table_sha256
    ):
        raise V0P6IncompleteError("sealed template factor-table identity changed")
    expected = np.stack(
        [
            np.asarray(
                basis.baseline
                + basis.orbital
                @ np.asarray(
                    [template["coefficient_x"], template["coefficient_y"]],
                    dtype=np.float64,
                ),
                dtype=np.float64,
            )
            for template in bank
        ],
        axis=0,
    )
    if expected.shape != table.factors.shape or not np.array_equal(
        expected, table.factors
    ):
        raise V0P6IncompleteError(
            "template factors do not reproduce from the sealed basis and bank"
        )


def factor_table_for_scan(
    table: TemplateFactorTable,
    basis: FactorBasis,
    scan_label: str,
) -> np.ndarray:
    """Select one scan's factor columns while preserving template order."""
    validate_factor_basis(basis)
    if table.factors.flags.writeable or (
        factor_table_sha256(table.factors) != table.factor_table_sha256
    ):
        raise V0P6IncompleteError("sealed template factor table changed")
    if (
        table.factor_basis_sha256 != basis.basis_sha256
        or table.factor_basis_labels_sha256 != basis.labels_sha256
    ):
        raise V0P6ContractError("factor table and basis identities differ")
    label = str(scan_label)
    rows = np.fromiter(
        (item.scan_label == label for item in basis.labels),
        dtype=bool,
        count=len(basis.labels),
    )
    if not np.any(rows):
        raise V0P6ContractError("scan label is absent from the factor table")
    selected = np.array(
        table.factors[:, rows], dtype=np.float64, order="C", copy=True
    )
    selected.setflags(write=False)
    return selected


M37_SCAN_ROLE_ORDER = (
    (1, "on", "epoch1_on"),
    (1, "off", "epoch1_off"),
    (2, "on", "epoch2_on"),
    (2, "off", "epoch2_off"),
    (3, "on", "epoch3_on"),
    (3, "off", "epoch3_off"),
)


def m37_scan_indices_for_kind(
    scan_definitions: Sequence[Mapping[str, Any]],
    kind: str,
) -> tuple[int, int, int]:
    """Validate the frozen ABABAB role inventory and select ON or OFF rows."""
    try:
        observed = tuple(
            (
                _strict_int(scan["epoch"], "scan epoch"),
                str(scan["kind"]).lower(),
                str(scan["label"]),
            )
            for scan in scan_definitions
        )
        integration_counts = tuple(
            _strict_int(
                scan["expected_header"]["dataset_shape"][0],
                "integration count",
            )
            for scan in scan_definitions
        )
    except (KeyError, IndexError, TypeError) as error:
        raise V0P6ContractError("M37 scan inventory has an invalid schema") from error
    if observed != M37_SCAN_ROLE_ORDER:
        raise V0P6ContractError("M37 scan roles/order changed from frozen ABABAB")
    if integration_counts != (16,) * len(M37_SCAN_ROLE_ORDER):
        raise V0P6ContractError("M37 requires exactly 16 integrations per scan")
    kind = str(kind).lower()
    if kind not in {"on", "off"}:
        raise V0P6ContractError("scan kind must be 'on' or 'off'")
    return tuple(
        index for index, (_, role, _) in enumerate(observed) if role == kind
    )  # type: ignore[return-value]


def factor_matrix_for_kind(
    table: TemplateFactorTable,
    basis: FactorBasis,
    scan_definitions: Sequence[Mapping[str, Any]],
    kind: str,
) -> np.ndarray:
    """Return canonical [template, all-kind-integration] factors for M37."""
    scan_indices = m37_scan_indices_for_kind(scan_definitions, kind)
    validate_factor_basis_scan_inventory(basis, scan_definitions)
    pieces = tuple(
        factor_table_for_scan(
            table,
            basis,
            str(scan_definitions[scan_index]["label"]),
        )
        for scan_index in scan_indices
    )
    matrix = np.array(
        np.concatenate(pieces, axis=1),
        dtype=np.float64,
        order="C",
        copy=True,
    )
    expected_columns = sum(
        _strict_int(
            scan_definitions[scan_index]["expected_header"]["dataset_shape"][0],
            "integration count",
        )
        for scan_index in scan_indices
    )
    if matrix.shape != (table.factors.shape[0], expected_columns):
        raise V0P6ContractError("kind factor matrix has the wrong dimensions")
    if not np.all(np.isfinite(matrix)) or np.any(matrix <= 0.0):
        raise V0P6ContractError("kind factor matrix must be finite and positive")
    matrix.setflags(write=False)
    return matrix


def validate_factor_basis_scan_inventory(
    basis: FactorBasis,
    scan_definitions: Sequence[Mapping[str, Any]],
) -> None:
    """Bind every basis row to the frozen scan label and integration index."""
    expected: list[FactorLabel] = []
    for scan_index, definition in enumerate(scan_definitions):
        count = _strict_int(
            definition["expected_header"]["dataset_shape"][0],
            "integration count",
        )
        expected.extend(
            FactorLabel(scan_index, str(definition["label"]), integration_index)
            for integration_index in range(count)
        )
    if tuple(expected) != basis.labels:
        raise V0P6ContractError(
            "factor-basis rows do not match the frozen scan inventory"
        )


def scan_inventory_sha256(
    scan_definitions: Sequence[Mapping[str, Any]],
) -> str:
    """Hash the exact six-scan M37 roles, counts, and factor-row ranges."""
    m37_scan_indices_for_kind(scan_definitions, "on")
    records: list[dict[str, Any]] = []
    row_start = 0
    for scan_index, definition in enumerate(scan_definitions):
        count = _strict_int(
            definition["expected_header"]["dataset_shape"][0],
            "integration count",
        )
        records.append(
            {
                "scan_index": scan_index,
                "epoch": _strict_int(definition["epoch"], "scan epoch"),
                "scan_kind": str(definition["kind"]).lower(),
                "scan_label": str(definition["label"]),
                "integration_count": count,
                "factor_row_start": row_start,
                "factor_row_stop": row_start + count,
            }
        )
        row_start += count
    return hashlib.sha256(canonical_json_bytes(records)).hexdigest()


def factor_row_selection_sha256(
    basis: FactorBasis,
    scan_definitions: Sequence[Mapping[str, Any]],
    kind: str,
) -> str:
    """Hash the ordered factor rows selected for one ON/OFF search product."""
    scan_indices = m37_scan_indices_for_kind(scan_definitions, kind)
    validate_factor_basis(basis)
    validate_factor_basis_scan_inventory(basis, scan_definitions)
    selected_scan_indices = set(scan_indices)
    row_indices = [
        row_index
        for row_index, label in enumerate(basis.labels)
        if label.scan_index in selected_scan_indices
    ]
    payload = {
        "factor_basis_sha256": basis.basis_sha256,
        "factor_basis_labels_sha256": basis.labels_sha256,
        "scan_inventory_sha256": scan_inventory_sha256(scan_definitions),
        "scan_kind": str(kind).lower(),
        "factor_row_indices": row_indices,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def factor_scan_selection_sha256(
    basis: FactorBasis,
    scan_definitions: Sequence[Mapping[str, Any]],
    scan_label: str,
) -> str:
    """Hash the exact factor rows selected for one named M37 scan."""
    m37_scan_indices_for_kind(scan_definitions, "on")
    validate_factor_basis(basis)
    validate_factor_basis_scan_inventory(basis, scan_definitions)
    label = str(scan_label)
    matches = [
        (scan_index, definition)
        for scan_index, definition in enumerate(scan_definitions)
        if str(definition["label"]) == label
    ]
    if len(matches) != 1:
        raise V0P6ContractError("factor scan selection requires one known scan")
    scan_index, definition = matches[0]
    row_indices = [
        row_index
        for row_index, factor_label in enumerate(basis.labels)
        if factor_label.scan_index == scan_index
    ]
    payload = {
        "factor_basis_sha256": basis.basis_sha256,
        "factor_basis_labels_sha256": basis.labels_sha256,
        "scan_inventory_sha256": scan_inventory_sha256(scan_definitions),
        "scan_kind": str(definition["kind"]).lower(),
        "scan_label": label,
        "scan_index": scan_index,
        "factor_row_indices": row_indices,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def validate_m37_factor_basis_scan_inventory(
    basis: FactorBasis,
    scan_definitions: Sequence[Mapping[str, Any]],
) -> None:
    """Require the exact 96-row M37 ABABAB label-to-factor partition."""
    m37_scan_indices_for_kind(scan_definitions, "on")
    validate_factor_basis(basis)
    validate_factor_basis_scan_inventory(basis, scan_definitions)
    if (
        basis.basis_sha256 != M37_FACTOR_BASIS_SHA256
        or basis.labels_sha256 != M37_FACTOR_BASIS_LABELS_SHA256
        or len(basis.labels) != 96
        or scan_inventory_sha256(scan_definitions)
        != M37_SCAN_INVENTORY_SHA256
        or factor_row_selection_sha256(basis, scan_definitions, "on")
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or factor_row_selection_sha256(basis, scan_definitions, "off")
        != M37_FACTOR_ROW_SELECTION_SHA256S["off"]
        or any(
            factor_scan_selection_sha256(
                basis, scan_definitions, scan_label
            )
            != expected_digest
            for scan_label, expected_digest in (
                M37_FACTOR_SCAN_SELECTION_SHA256S.items()
            )
        )
    ):
        raise V0P6ContractError("factor basis is not the canonical 96-row M37 basis")


_EPOCH_VECTOR_PRODUCT_SEAL = object()
_EPOCH_VECTOR_PRODUCT_REGISTRY: dict[
    int,
    tuple[
        weakref.ReferenceType[Any], bytes, weakref.ReferenceType[np.ndarray]
    ],
] = {}


@dataclass(frozen=True)
class EpochVectorProduct:
    """Immutable, provenance-bound three-epoch vector product."""

    values: np.ndarray = field(repr=False)
    window_id: str
    scan_kind: str
    template_index: int
    width_channels: int
    proxy_grid_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    factor_row_selection_sha256: str
    template_bank_sha256: str
    factor_table_sha256: str
    cache_plan_sha256s: tuple[str, ...]
    cache_payload_sha256s: tuple[str, ...]
    values_sha256: str
    product_sha256: str
    _seal: object = field(repr=False, compare=False)
    _receipt: object = field(repr=False, compare=False)

    def __array__(
        self, dtype: np.dtype[Any] | None = None, copy: bool | None = None
    ) -> np.ndarray:
        array = np.asarray(self.values, dtype=dtype)
        if copy:
            return array.copy()
        return array


def _epoch_vector_product_payload(
    product: EpochVectorProduct,
) -> dict[str, Any]:
    return {
        "window_id": str(product.window_id),
        "scan_kind": str(product.scan_kind),
        "template_index": _strict_int(
            product.template_index, "template index"
        ),
        "width_channels": _strict_widths((product.width_channels,))[0],
        "proxy_grid_sha256": _frozen_sha256(
            product.proxy_grid_sha256, "proxy-grid identity"
        ),
        "factor_basis_sha256": _frozen_sha256(
            product.factor_basis_sha256, "factor-basis identity"
        ),
        "factor_basis_labels_sha256": _frozen_sha256(
            product.factor_basis_labels_sha256, "factor-basis labels identity"
        ),
        "factor_row_selection_sha256": _frozen_sha256(
            product.factor_row_selection_sha256,
            "factor-row selection identity",
        ),
        "template_bank_sha256": _frozen_sha256(
            product.template_bank_sha256, "template-bank identity"
        ),
        "factor_table_sha256": _frozen_sha256(
            product.factor_table_sha256, "factor-table identity"
        ),
        "cache_plan_sha256s": [
            _frozen_sha256(item, "cache-plan identity")
            for item in product.cache_plan_sha256s
        ],
        "cache_payload_sha256s": [
            _frozen_sha256(item, "cache-payload identity")
            for item in product.cache_payload_sha256s
        ],
        "values_shape": [
            _strict_int(item, "epoch-vector dimension")
            for item in product.values.shape
        ],
        "values_dtype": "<f4",
        "values_sha256": _frozen_sha256(
            product.values_sha256, "epoch-vector identity"
        ),
    }


def validate_epoch_vector_product(
    product: EpochVectorProduct,
    *,
    verify_values: bool = True,
) -> None:
    """Validate a factory-sealed epoch product and, by default, its values."""
    if not isinstance(product, EpochVectorProduct) or (
        product._seal is not _EPOCH_VECTOR_PRODUCT_SEAL
    ):
        raise V0P6ContractError("epoch vectors are not a sealed product")
    attestation = _EPOCH_VECTOR_PRODUCT_REGISTRY.get(id(product._receipt))
    if (
        attestation is None
        or attestation[0]() is not product
        or attestation[2]() is not product.values
    ):
        raise V0P6ContractError(
            "epoch vectors do not carry a live factory receipt"
        )
    if product.scan_kind not in {"on", "off"} or not product.window_id:
        raise V0P6ContractError("epoch-vector scan/window identity is invalid")
    if (
        product.values.ndim != 2
        or product.values.shape[0] != 3
        or product.values.dtype != np.dtype("<f4")
        or product.values.flags.writeable
        or not product.values.flags.c_contiguous
    ):
        raise V0P6IncompleteError("sealed epoch-vector values are invalid")
    if verify_values and not np.all(np.isfinite(product.values)):
        raise V0P6IncompleteError("sealed epoch-vector values are non-finite")
    root: Any = product.values
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    if not isinstance(getattr(root, "base", None), bytes):
        raise V0P6IncompleteError(
            "epoch-vector values are not backed by immutable bytes"
        )
    if verify_values:
        values_view = memoryview(product.values).cast("B")
        try:
            observed_values_sha256 = hashlib.sha256(values_view).hexdigest()
        finally:
            values_view.release()
        if observed_values_sha256 != product.values_sha256:
            raise V0P6IncompleteError("sealed epoch-vector values changed")
    if len(product.cache_plan_sha256s) != 3 or len(
        product.cache_payload_sha256s
    ) != 3:
        raise V0P6ContractError("epoch-vector cache inventory is incomplete")
    observed = hashlib.sha256(
        canonical_json_bytes(_epoch_vector_product_payload(product))
    ).hexdigest()
    if observed != product.product_sha256:
        raise V0P6IncompleteError("epoch-vector product identity changed")
    attested_record = {
        "payload": _epoch_vector_product_payload(product),
        "product_sha256": product.product_sha256,
    }
    if canonical_json_bytes(attested_record) != attestation[1]:
        raise V0P6IncompleteError("epoch-vector factory attestation changed")


def _seal_epoch_vector_product(
    values: np.ndarray,
    *,
    window_id: str,
    scan_kind: str,
    template_index: int,
    width_channels: int,
    grid_sha256: str,
    factor_basis_sha256_value: str,
    factor_basis_labels_sha256_value: str,
    factor_row_selection_sha256_value: str,
    template_bank_sha256_value: str,
    factor_table_sha256_value: str,
    cache_plan_sha256s: Sequence[str],
    cache_payload_sha256s: Sequence[str],
) -> EpochVectorProduct:
    array = np.asarray(values)
    if array.ndim != 2 or array.shape[0] != 3 or (
        not np.issubdtype(array.dtype, np.floating)
    ):
        raise V0P6ContractError("epoch vectors must have three floating rows")
    if not np.all(np.isfinite(array)):
        raise V0P6ContractError("epoch-vector product cannot contain non-finite data")
    payload_bytes = np.ascontiguousarray(array, dtype="<f4").tobytes()
    sealed = np.frombuffer(payload_bytes, dtype="<f4").reshape(array.shape)
    values_digest = hashlib.sha256(payload_bytes).hexdigest()
    receipt = object()
    partial = EpochVectorProduct(
        values=sealed,
        window_id=str(window_id),
        scan_kind=str(scan_kind).lower(),
        template_index=_strict_int(template_index, "template index"),
        width_channels=_strict_widths((width_channels,))[0],
        proxy_grid_sha256=_frozen_sha256(grid_sha256, "proxy-grid identity"),
        factor_basis_sha256=_frozen_sha256(
            factor_basis_sha256_value, "factor-basis identity"
        ),
        factor_basis_labels_sha256=_frozen_sha256(
            factor_basis_labels_sha256_value, "factor-basis labels identity"
        ),
        factor_row_selection_sha256=_frozen_sha256(
            factor_row_selection_sha256_value,
            "factor-row selection identity",
        ),
        template_bank_sha256=_frozen_sha256(
            template_bank_sha256_value, "template-bank identity"
        ),
        factor_table_sha256=_frozen_sha256(
            factor_table_sha256_value, "factor-table identity"
        ),
        cache_plan_sha256s=tuple(cache_plan_sha256s),
        cache_payload_sha256s=tuple(cache_payload_sha256s),
        values_sha256=values_digest,
        product_sha256="",
        _seal=_EPOCH_VECTOR_PRODUCT_SEAL,
        _receipt=receipt,
    )
    product = EpochVectorProduct(
        **{
            **partial.__dict__,
            "product_sha256": hashlib.sha256(
                canonical_json_bytes(_epoch_vector_product_payload(partial))
            ).hexdigest(),
        }
    )
    registry_key = id(receipt)
    attested_bytes = canonical_json_bytes(
        {
            "payload": _epoch_vector_product_payload(product),
            "product_sha256": product.product_sha256,
        }
    )

    def discard_epoch_product_receipt(
        reference: weakref.ReferenceType[Any],
        *,
        key: int = registry_key,
    ) -> None:
        current = _EPOCH_VECTOR_PRODUCT_REGISTRY.get(key)
        if current is not None and current[0] is reference:
            _EPOCH_VECTOR_PRODUCT_REGISTRY.pop(key, None)

    _EPOCH_VECTOR_PRODUCT_REGISTRY[registry_key] = (
        weakref.ref(product, discard_epoch_product_receipt),
        attested_bytes,
        weakref.ref(product.values),
    )
    validate_epoch_vector_product(product)
    return product


def native_geometry_for_scan(scan: dict[str, Any]) -> NativeFrequencyGeometry:
    """Load frozen affine geometry from an extracted scan's metadata."""
    metadata = scan.get("metadata")
    if not isinstance(metadata, dict):
        raise V0P6ContractError("scan is missing extraction metadata")
    header = metadata.get("header")
    if not isinstance(header, dict):
        raise V0P6ContractError("scan metadata is missing the native header")
    required = ("fch1", "foff")
    if any(key not in header for key in required) or any(
        key not in metadata for key in ("channel_start", "channel_stop")
    ):
        raise V0P6ContractError("scan metadata lacks affine extraction geometry")
    return native_geometry_from_extraction(
        fch1_mhz=float(header["fch1"]),
        foff_mhz=float(header["foff"]),
        channel_start=int(metadata["channel_start"]),
        channel_stop=int(metadata["channel_stop"]),
    )


def build_epoch_vectors(
    caches_by_label: Mapping[str, Any],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    template_index: int,
    grid: ProxyCarrierGrid,
    width_channels: int,
    *,
    window_id: str,
    kind: str,
    chunk_bins: int = 131_072,
) -> np.ndarray:
    """Build three ON/OFF vectors only from sealed factor and filter caches."""
    scan_indices = m37_scan_indices_for_kind(scan_definitions, kind)
    validate_factor_basis_scan_inventory(factor_basis, scan_definitions)
    validate_factor_basis(factor_basis)
    template_index = _strict_int(template_index, "template index")
    width_channels = _strict_widths((width_channels,))[0]
    if template_index < 0 or template_index >= factor_table.factors.shape[0]:
        raise V0P6ContractError("template index is outside the factor table")
    vectors = np.empty((3, grid.score_bin_count), dtype=np.float32)
    for epoch, scan_index in enumerate(scan_indices):
        definition = scan_definitions[scan_index]
        label = str(definition["label"])
        if label not in caches_by_label:
            raise V0P6IncompleteError(f"native filter cache is missing: {label}")
        cache = caches_by_label[label]
        expected_count = _strict_int(
            definition["expected_header"]["dataset_shape"][0],
            "integration count",
        )
        scan_factor_table = factor_table_for_scan(
            factor_table, factor_basis, label
        )
        factor = scan_factor_table[template_index]
        if factor.size != expected_count or cache.plan.integration_count != expected_count:
            raise V0P6ContractError("factor-basis scan slice has the wrong size")
        if (
            cache.plan.window_id != str(window_id)
            or cache.plan.scan_label != label
            or cache.plan.scan_kind != str(kind).lower()
            or cache.plan.width_channels != width_channels
            or cache.plan.factor_basis_sha256 != factor_basis.basis_sha256
            or cache.plan.factor_basis_labels_sha256
            != factor_basis.labels_sha256
            or cache.plan.scan_inventory_sha256
            != scan_inventory_sha256(scan_definitions)
            or cache.plan.factor_scan_selection_sha256
            != factor_scan_selection_sha256(
                factor_basis, scan_definitions, label
            )
            or cache.plan.template_bank_sha256
            != factor_table.template_bank_sha256
            or cache.plan.factor_table_sha256
            != factor_table_sha256(scan_factor_table)
        ):
            raise V0P6ContractError(
                "native filter cache identity differs from the requested search"
            )
        vectors[epoch] = gather_filtered_native(
            cache,
            factor,
            grid,
            chunk_bins=chunk_bins,
        )
    return vectors


def build_epoch_vector_product(
    caches_by_label: Mapping[str, Any],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    template_bank: Sequence[dict[str, Any]],
    template_index: int,
    grid: ProxyCarrierGrid,
    width_channels: int,
    *,
    window_id: str,
    kind: str,
    expected_template_bank_sha256: str,
    chunk_bins: int = 131_072,
) -> EpochVectorProduct:
    """Build and seal production vectors with all cache/factor identities."""
    validate_template_factor_table(
        factor_table,
        factor_basis,
        template_bank,
        expected_template_bank_sha256=expected_template_bank_sha256,
    )
    scan_indices = m37_scan_indices_for_kind(scan_definitions, kind)
    selected_caches = tuple(
        caches_by_label[str(scan_definitions[index]["label"])]
        for index in scan_indices
    )
    values = build_epoch_vectors(
        caches_by_label,
        scan_definitions,
        factor_basis,
        factor_table,
        template_index,
        grid,
        width_channels,
        window_id=window_id,
        kind=kind,
        chunk_bins=chunk_bins,
    )
    return _seal_epoch_vector_product(
        values,
        window_id=window_id,
        scan_kind=kind,
        template_index=template_index,
        width_channels=width_channels,
        grid_sha256=proxy_carrier_grid_sha256(grid),
        factor_basis_sha256_value=factor_basis.basis_sha256,
        factor_basis_labels_sha256_value=factor_basis.labels_sha256,
        factor_row_selection_sha256_value=factor_row_selection_sha256(
            factor_basis, scan_definitions, kind
        ),
        template_bank_sha256_value=factor_table.template_bank_sha256,
        factor_table_sha256_value=factor_table.factor_table_sha256,
        cache_plan_sha256s=tuple(
            cache.plan.plan_sha256 for cache in selected_caches
        ),
        cache_payload_sha256s=tuple(
            cache.payload_sha256 for cache in selected_caches
        ),
    )


def build_m37_epoch_vector_product(
    caches_by_label: Mapping[str, Any],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    template_index: int,
    grid: ProxyCarrierGrid,
    width_channels: int,
    *,
    window_id: str,
    kind: str,
    chunk_bins: int = 131_072,
) -> EpochVectorProduct:
    """Build one non-configurable M37 provenance-bound epoch product."""
    if proxy_carrier_grid_sha256(grid) != proxy_carrier_grid_sha256(
        make_m37_proxy_carrier_grid(window_id)
    ):
        raise V0P6ContractError("epoch product did not receive the M37 q grid")
    validate_m37_factor_basis_scan_inventory(factor_basis, scan_definitions)
    product = build_epoch_vector_product(
        caches_by_label,
        scan_definitions,
        factor_basis,
        factor_table,
        make_line_template_bank(),
        template_index,
        grid,
        width_channels,
        window_id=window_id,
        kind=kind,
        expected_template_bank_sha256=M37_BANK_SHA256,
        chunk_bins=chunk_bins,
    )
    if product.factor_row_selection_sha256 != M37_FACTOR_ROW_SELECTION_SHA256S[
        str(kind).lower()
    ]:
        raise V0P6ContractError("epoch product selected the wrong M37 factor rows")
    return product


def isolated_single_epoch_mask(
    epoch_vectors: np.ndarray,
    strong_snr: float,
    other_epochs_below_snr: float,
) -> np.ndarray:
    """Return isolated-epoch flags for one template/width on the q axis."""
    vectors = np.asarray(epoch_vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] < 2:
        raise V0P6ContractError("epoch vectors must have at least two epochs")
    strong_snr = float(strong_snr)
    other_epochs_below_snr = float(other_epochs_below_snr)
    if not math.isfinite(strong_snr) or not math.isfinite(
        other_epochs_below_snr
    ):
        raise V0P6ContractError("single-epoch mask thresholds must be finite")
    if strong_snr <= other_epochs_below_snr:
        raise V0P6ContractError(
            "strong single-epoch threshold must exceed the other-epoch ceiling"
        )
    safe = np.nan_to_num(
        vectors, nan=-np.inf, posinf=-np.inf, neginf=-np.inf
    )
    ordered = np.sort(safe, axis=0)
    isolated = (ordered[-1] >= strong_snr) & (
        ordered[-2] < other_epochs_below_snr
    )
    strongest = np.argmax(safe, axis=0)
    mask = np.zeros_like(vectors, dtype=bool)
    for epoch in range(vectors.shape[0]):
        mask[epoch] = isolated & (strongest == epoch)
    return mask


def dilate_q_mask(mask: np.ndarray, guard_bins: int) -> np.ndarray:
    """Dilate a q-coordinate mask with clipped (never wrapped) edges."""
    source = np.asarray(mask, dtype=bool)
    if source.ndim != 2:
        raise V0P6ContractError("q mask must have [epoch, q] axes")
    guard_bins = _strict_int(guard_bins, "mask guard")
    if guard_bins < 0:
        raise V0P6ContractError("mask guard must be non-negative")
    result = source.copy()
    for offset in range(1, guard_bins + 1):
        result[:, offset:] |= source[:, :-offset]
        result[:, :-offset] |= source[:, offset:]
    return result


def build_two_pass_template_mask(
    vector_factory: Callable[[int], np.ndarray],
    widths: Iterable[int],
    *,
    strong_snr: float,
    other_epochs_below_snr: float,
    guard_bins: int,
) -> np.ndarray:
    """First-pass OR mask across widths for one orbital template."""
    widths = _strict_widths(widths)
    combined: np.ndarray | None = None
    for width in widths:
        vectors = np.asarray(vector_factory(width), dtype=np.float32)
        current = isolated_single_epoch_mask(
            vectors, strong_snr, other_epochs_below_snr
        )
        if combined is None:
            combined = current
        elif current.shape != combined.shape:
            raise V0P6ContractError("vector factory changed shape between widths")
        else:
            combined |= current
    assert combined is not None
    return dilate_q_mask(combined, guard_bins)


def build_m37_two_pass_template_mask(
    vector_factory: Callable[[int], np.ndarray],
) -> np.ndarray:
    """Apply the non-configurable M37 width-OR and ±9-q-bin RFI rule."""
    return build_two_pass_template_mask(
        vector_factory,
        M37_SPECTRAL_WIDTHS,
        strong_snr=M37_RFI_STRONG_SNR,
        other_epochs_below_snr=M37_RFI_OTHER_EPOCHS_BELOW_SNR,
        guard_bins=M37_RFI_GUARD_Q_BINS,
    )


_MASK_PRODUCT_SEAL = object()
_MASK_PRODUCT_REGISTRY: dict[
    int,
    tuple[
        weakref.ReferenceType[Any], bytes, weakref.ReferenceType[np.ndarray]
    ],
] = {}


@dataclass(frozen=True)
class MaskProduct:
    """Immutable two-pass template mask bound to all source widths."""

    values: np.ndarray = field(repr=False)
    window_id: str
    scan_kind: str
    template_index: int
    proxy_grid_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    factor_row_selection_sha256: str
    template_bank_sha256: str
    factor_table_sha256: str
    source_epoch_product_sha256s: tuple[str, ...]
    spectral_widths: tuple[int, ...]
    strong_snr: float
    other_epochs_below_snr: float
    guard_bins: int
    values_sha256: str
    product_sha256: str
    _seal: object = field(repr=False, compare=False)
    _receipt: object = field(repr=False, compare=False)


def _mask_product_payload(product: MaskProduct) -> dict[str, Any]:
    return {
        "window_id": str(product.window_id),
        "scan_kind": str(product.scan_kind),
        "template_index": _strict_int(
            product.template_index, "template index"
        ),
        "proxy_grid_sha256": _frozen_sha256(
            product.proxy_grid_sha256, "proxy-grid identity"
        ),
        "factor_basis_sha256": _frozen_sha256(
            product.factor_basis_sha256, "factor-basis identity"
        ),
        "factor_basis_labels_sha256": _frozen_sha256(
            product.factor_basis_labels_sha256, "factor-basis labels identity"
        ),
        "factor_row_selection_sha256": _frozen_sha256(
            product.factor_row_selection_sha256,
            "factor-row selection identity",
        ),
        "template_bank_sha256": _frozen_sha256(
            product.template_bank_sha256, "template-bank identity"
        ),
        "factor_table_sha256": _frozen_sha256(
            product.factor_table_sha256, "factor-table identity"
        ),
        "source_epoch_product_sha256s": [
            _frozen_sha256(item, "source epoch-product identity")
            for item in product.source_epoch_product_sha256s
        ],
        "spectral_widths": list(_strict_widths(product.spectral_widths)),
        "strong_snr": float(product.strong_snr),
        "other_epochs_below_snr": float(product.other_epochs_below_snr),
        "guard_bins": _strict_int(product.guard_bins, "mask guard"),
        "values_shape": [
            _strict_int(item, "mask dimension") for item in product.values.shape
        ],
        "values_dtype": "bool-u1",
        "values_sha256": _frozen_sha256(
            product.values_sha256, "mask values identity"
        ),
    }


def validate_mask_product(
    product: MaskProduct,
    *,
    verify_values: bool = True,
) -> None:
    """Validate a sealed two-pass mask and, by default, its exact bits."""
    if not isinstance(product, MaskProduct) or product._seal is not _MASK_PRODUCT_SEAL:
        raise V0P6ContractError("exclusion mask is not a sealed product")
    attestation = _MASK_PRODUCT_REGISTRY.get(id(product._receipt))
    if (
        attestation is None
        or attestation[0]() is not product
        or attestation[2]() is not product.values
    ):
        raise V0P6ContractError(
            "exclusion mask does not carry a live factory receipt"
        )
    if (
        product.scan_kind not in {"on", "off"}
        or not product.window_id
        or product.values.ndim != 2
        or product.values.shape[0] != 3
        or product.values.dtype != np.dtype(bool)
        or product.values.flags.writeable
        or not product.values.flags.c_contiguous
    ):
        raise V0P6IncompleteError("sealed mask-product values are invalid")
    root: Any = product.values
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    if not isinstance(getattr(root, "base", None), bytes):
        raise V0P6IncompleteError("mask-product values are not immutable")
    if verify_values:
        view = memoryview(product.values).cast("B")
        try:
            observed_values_sha256 = hashlib.sha256(view).hexdigest()
        finally:
            view.release()
        if observed_values_sha256 != product.values_sha256:
            raise V0P6IncompleteError("sealed mask-product values changed")
    if len(product.source_epoch_product_sha256s) != len(
        product.spectral_widths
    ):
        raise V0P6ContractError("mask source-width inventory is incomplete")
    numeric = (product.strong_snr, product.other_epochs_below_snr)
    if not all(math.isfinite(float(item)) for item in numeric) or (
        float(product.strong_snr) <= float(product.other_epochs_below_snr)
    ):
        raise V0P6ContractError("mask-product thresholds are invalid")
    if _strict_int(product.guard_bins, "mask guard") < 0:
        raise V0P6ContractError("mask-product guard is invalid")
    observed = hashlib.sha256(
        canonical_json_bytes(_mask_product_payload(product))
    ).hexdigest()
    if observed != product.product_sha256:
        raise V0P6IncompleteError("mask-product identity changed")
    attested_record = {
        "payload": _mask_product_payload(product),
        "product_sha256": product.product_sha256,
    }
    if canonical_json_bytes(attested_record) != attestation[1]:
        raise V0P6IncompleteError("mask-product factory attestation changed")


def build_m37_mask_product(
    epoch_products_by_width: Mapping[int, EpochVectorProduct],
) -> MaskProduct:
    """Build the non-configurable M37 width-OR and ±9-q mask product."""
    if set(epoch_products_by_width) != set(M37_SPECTRAL_WIDTHS):
        raise V0P6IncompleteError("M37 mask requires all eight width products")
    products = tuple(
        epoch_products_by_width[width] for width in M37_SPECTRAL_WIDTHS
    )
    for width, product in zip(M37_SPECTRAL_WIDTHS, products, strict=True):
        validate_epoch_vector_product(product)
        if product.width_channels != width:
            raise V0P6ContractError("mask source product has the wrong width")
    identity = (
        products[0].window_id,
        products[0].scan_kind,
        products[0].template_index,
        products[0].proxy_grid_sha256,
        products[0].factor_basis_sha256,
        products[0].factor_basis_labels_sha256,
        products[0].factor_row_selection_sha256,
        products[0].template_bank_sha256,
        products[0].factor_table_sha256,
        products[0].values.shape,
    )
    for product in products[1:]:
        if (
            product.window_id,
            product.scan_kind,
            product.template_index,
            product.proxy_grid_sha256,
            product.factor_basis_sha256,
            product.factor_basis_labels_sha256,
            product.factor_row_selection_sha256,
            product.template_bank_sha256,
            product.factor_table_sha256,
            product.values.shape,
        ) != identity:
            raise V0P6ContractError("mask source epoch products disagree")
    if (
        identity[4] != M37_FACTOR_BASIS_SHA256
        or identity[5] != M37_FACTOR_BASIS_LABELS_SHA256
        or identity[6]
        != M37_FACTOR_ROW_SELECTION_SHA256S[str(identity[1]).lower()]
        or identity[7] != M37_BANK_SHA256
    ):
        raise V0P6ContractError("mask source products are not canonical M37 products")
    values = build_m37_two_pass_template_mask(
        lambda width: epoch_products_by_width[width].values
    )
    payload_bytes = np.ascontiguousarray(values, dtype=np.bool_).tobytes()
    sealed = np.frombuffer(payload_bytes, dtype=np.bool_).reshape(values.shape)
    values_digest = hashlib.sha256(payload_bytes).hexdigest()
    receipt = object()
    partial = MaskProduct(
        values=sealed,
        window_id=identity[0],
        scan_kind=identity[1],
        template_index=identity[2],
        proxy_grid_sha256=identity[3],
        factor_basis_sha256=identity[4],
        factor_basis_labels_sha256=identity[5],
        factor_row_selection_sha256=identity[6],
        template_bank_sha256=identity[7],
        factor_table_sha256=identity[8],
        source_epoch_product_sha256s=tuple(
            product.product_sha256 for product in products
        ),
        spectral_widths=M37_SPECTRAL_WIDTHS,
        strong_snr=M37_RFI_STRONG_SNR,
        other_epochs_below_snr=M37_RFI_OTHER_EPOCHS_BELOW_SNR,
        guard_bins=M37_RFI_GUARD_Q_BINS,
        values_sha256=values_digest,
        product_sha256="",
        _seal=_MASK_PRODUCT_SEAL,
        _receipt=receipt,
    )
    product = MaskProduct(
        **{
            **partial.__dict__,
            "product_sha256": hashlib.sha256(
                canonical_json_bytes(_mask_product_payload(partial))
            ).hexdigest(),
        }
    )
    registry_key = id(receipt)
    attested_bytes = canonical_json_bytes(
        {
            "payload": _mask_product_payload(product),
            "product_sha256": product.product_sha256,
        }
    )

    def discard_mask_product_receipt(
        reference: weakref.ReferenceType[Any],
        *,
        key: int = registry_key,
    ) -> None:
        current = _MASK_PRODUCT_REGISTRY.get(key)
        if current is not None and current[0] is reference:
            _MASK_PRODUCT_REGISTRY.pop(key, None)

    _MASK_PRODUCT_REGISTRY[registry_key] = (
        weakref.ref(product, discard_mask_product_receipt),
        attested_bytes,
        weakref.ref(product.values),
    )
    validate_mask_product(product)
    return product


def canonical_activity_subsets(
    subsets: Iterable[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    """Validate ordered, unique, strictly increasing activity subsets."""
    result = tuple(
        tuple(_strict_int(epoch, "activity epoch") for epoch in subset)
        for subset in subsets
    )
    if not result or len(set(result)) != len(result):
        raise V0P6ContractError("activity subsets must be non-empty and unique")
    for subset in result:
        if not subset or any(left >= right for left, right in zip(subset, subset[1:])):
            raise V0P6ContractError(
                "activity subsets must be non-empty and strictly increasing"
            )
        if subset[0] < 0:
            raise V0P6ContractError("activity epochs must be non-negative")
    return result


def make_hypothesis_inventory(
    template_count: int,
    spectral_widths: Iterable[int],
    subsets: Iterable[Sequence[int]],
) -> frozenset[tuple[int, int, tuple[int, ...]]]:
    """Return the exact template/width/subset key inventory for one window."""
    template_count = _strict_int(template_count, "template count")
    if template_count < 1:
        raise V0P6ContractError("hypothesis inventory requires templates")
    widths = _strict_widths(spectral_widths)
    activity = canonical_activity_subsets(subsets)
    return frozenset(
        (template_index, width_index, subset)
        for template_index in range(template_count)
        for width_index in range(len(widths))
        for subset in activity
    )


def stack_hypothesis(
    epoch_vectors: np.ndarray,
    subset: Sequence[int],
    *,
    minimum_active_epoch_snr: float | None,
    stack_statistic: str,
    exclusion_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Return one complete v0.6 hypothesis score vector."""
    vectors = np.asarray(epoch_vectors, dtype=np.float32)
    if vectors.ndim != 2:
        raise V0P6ContractError("epoch vectors must have [epoch, q] axes")
    active_indices = canonical_activity_subsets((subset,))[0]
    if max(active_indices) >= vectors.shape[0]:
        raise V0P6ContractError("activity subset is out of range")
    active = vectors[list(active_indices)]
    minimum_active_epoch_snr, stack_statistic = _scoring_contract(
        minimum_active_epoch_snr, stack_statistic
    )
    if stack_statistic == "sum":
        score = np.sum(active, axis=0, dtype=np.float32)
        score /= np.float32(math.sqrt(len(active_indices)))
    elif stack_statistic == "minimum_epoch":
        score = np.min(active, axis=0).astype(np.float32, copy=False)
        score = score * np.float32(math.sqrt(len(active_indices)))
    if minimum_active_epoch_snr is not None:
        score = np.where(
            np.all(active >= minimum_active_epoch_snr, axis=0),
            score,
            -np.inf,
        )
    if exclusion_mask is not None:
        mask = np.asarray(exclusion_mask, dtype=bool)
        if mask.shape == vectors.shape:
            mask = np.any(mask[list(active_indices)], axis=0)
        elif mask.shape != (vectors.shape[1],):
            raise V0P6ContractError("exclusion mask has incompatible dimensions")
        score = np.where(mask, -np.inf, score)
    return np.nan_to_num(
        np.asarray(score, dtype=np.float32),
        nan=-np.inf,
        posinf=-np.inf,
        neginf=-np.inf,
    )


def make_scramble_shift_table(
    scramble_count: int,
    epoch_count: int,
    score_bin_count: int,
    *,
    seed: int,
    minimum_shift_bins: int,
) -> np.ndarray:
    """Create a deterministic table shared by every width and template."""
    scramble_count = _strict_int(scramble_count, "scramble count")
    epoch_count = _strict_int(epoch_count, "epoch count")
    score_bin_count = _strict_int(score_bin_count, "score-bin count")
    minimum_shift_bins = _strict_int(
        minimum_shift_bins, "minimum scramble shift"
    )
    if scramble_count < 1 or epoch_count < 2:
        raise V0P6ContractError("scramble table requires scrambles and two epochs")
    if minimum_shift_bins < 1 or score_bin_count <= 2 * minimum_shift_bins:
        raise V0P6ContractError("score grid is too short for the scramble guard")
    rng = np.random.default_rng(_strict_int(seed, "scramble seed"))
    table = np.zeros((scramble_count, epoch_count), dtype=np.int64)
    table[:, 1:] = rng.integers(
        minimum_shift_bins,
        score_bin_count - minimum_shift_bins,
        size=(scramble_count, epoch_count - 1),
        dtype=np.int64,
    )
    return table


def scramble_table_sha256(table: np.ndarray) -> str:
    """Hash a shift table with an explicit little-endian int64 encoding."""
    array = np.asarray(table)
    if array.ndim != 2 or not np.issubdtype(array.dtype, np.integer):
        raise V0P6ContractError("scramble table must be a two-dimensional integer array")
    payload = np.asarray(array, dtype="<i8", order="C").tobytes()
    return hashlib.sha256(payload).hexdigest()


def float64_vector_sha256(values: np.ndarray) -> str:
    """Hash a one-dimensional float vector as canonical little-endian float64."""
    array = np.asarray(values)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.floating):
        raise V0P6ContractError("hashed null maxima must be a float vector")
    if not np.all(np.isfinite(array)):
        raise V0P6ContractError("hashed null maxima must all be finite")
    payload = np.asarray(array, dtype="<f8", order="C").tobytes()
    return hashlib.sha256(payload).hexdigest()


def _raw_float64_vector_sha256(values: np.ndarray) -> str:
    """Hash a float vector including infinities for mutable replay checkpoints."""
    array = np.asarray(values)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.floating):
        raise V0P6ContractError("calibration maxima must be a float vector")
    return hashlib.sha256(
        np.asarray(array, dtype="<f8", order="C").tobytes()
    ).hexdigest()


def validate_scramble_shift_table(
    table: np.ndarray,
    *,
    epoch_count: int,
    score_bin_count: int,
    minimum_shift_bins: int,
    expected_sha256: str | None = None,
) -> np.ndarray:
    """Validate an explicit frozen shift table without invoking an RNG."""
    shifts = np.asarray(table)
    epoch_count = _strict_int(epoch_count, "epoch count")
    score_bin_count = _strict_int(score_bin_count, "score-bin count")
    minimum_shift_bins = _strict_int(
        minimum_shift_bins, "minimum scramble shift"
    )
    if shifts.ndim != 2 or shifts.shape[1] != epoch_count:
        raise V0P6ContractError("scramble table has the wrong epoch dimension")
    if shifts.shape[0] < 1:
        raise V0P6ContractError("scramble table must contain at least one scramble")
    if not np.issubdtype(shifts.dtype, np.integer):
        raise V0P6ContractError("scramble table must contain integers")
    shifts = np.asarray(shifts, dtype=np.int64)
    if np.any(shifts[:, 0] != 0):
        raise V0P6ContractError("scramble epoch zero must remain unshifted")
    if np.any(shifts[:, 1:] < minimum_shift_bins) or np.any(
        shifts[:, 1:] >= score_bin_count - minimum_shift_bins
    ):
        raise V0P6ContractError("scramble shift violates the frozen edge guard")
    digest = scramble_table_sha256(shifts)
    if expected_sha256 is not None and digest != expected_sha256:
        raise V0P6ContractError(
            f"scramble-table SHA-256 changed: {digest} != {expected_sha256}"
        )
    return shifts


def generate_m37_scramble_tables_for_preregistration() -> tuple[np.ndarray, ...]:
    """Generate source-candidate tables; production must load published arrays.

    The preregistration workflow reruns this under pinned NumPy, publishes the
    explicit arrays, and validates the digests below.  The search runner must
    never regenerate them from these provenance seeds.
    """
    return tuple(
        make_scramble_shift_table(
            M37_SCRAMBLE_COUNT,
            3,
            2 * M37_SCORE_HALF_BINS + 1,
            seed=M37_SCRAMBLE_MASTER_SEED + window_index,
            minimum_shift_bins=M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
        )
        for window_index in range(len(M37_WINDOW_IDS))
    )


def _decode_m37_scramble_resource(
    payload: bytes,
    *,
    expected_sha256: str,
    resource_name: str,
) -> np.ndarray:
    """Decode one canonical little-endian table only after a byte-hash gate."""
    if not isinstance(payload, bytes):
        raise V0P6ContractError("scramble resource payload must be immutable bytes")
    expected_sha256 = _frozen_sha256(
        expected_sha256, "scramble resource identity"
    )
    resource_name = str(resource_name)
    if not resource_name:
        raise V0P6ContractError("scramble resource name must be non-empty")
    expected_bytes = M37_SCRAMBLE_COUNT * 3 * np.dtype("<i8").itemsize
    if len(payload) != expected_bytes:
        raise V0P6ContractError(
            f"M37 scramble resource {resource_name!r} has {len(payload)} bytes; "
            f"expected {expected_bytes}"
        )
    observed_sha256 = hashlib.sha256(payload).hexdigest()
    if observed_sha256 != expected_sha256:
        raise V0P6ContractError(
            f"M37 scramble resource {resource_name!r} SHA-256 changed: "
            f"{observed_sha256} != {expected_sha256}"
        )
    table = np.frombuffer(payload, dtype="<i8").reshape(M37_SCRAMBLE_COUNT, 3)
    return np.asarray(table, dtype=np.int64, order="C").copy()


def load_m37_scramble_tables() -> tuple[np.ndarray, ...]:
    """Load the five committed tables without regenerating them from seeds."""
    package_root = resources.files("seti_repeater")
    tables = []
    for resource_name, expected_sha256 in zip(
        M37_SCRAMBLE_RESOURCE_NAMES,
        M37_SCRAMBLE_TABLE_SHA256S,
        strict=True,
    ):
        try:
            payload = package_root.joinpath(resource_name).read_bytes()
        except (FileNotFoundError, IsADirectoryError, OSError) as exc:
            raise V0P6ContractError(
                f"required M37 scramble resource is unavailable: {resource_name}"
            ) from exc
        tables.append(
            _decode_m37_scramble_resource(
                payload,
                expected_sha256=expected_sha256,
                resource_name=resource_name,
            )
        )
    return validate_m37_scramble_tables(tables)


def validate_m37_scramble_tables(
    tables: Sequence[np.ndarray],
) -> tuple[np.ndarray, ...]:
    """Validate the five explicit tables and their aggregate byte identity."""
    if len(tables) != len(M37_WINDOW_IDS):
        raise V0P6ContractError("M37 requires exactly five scramble tables")
    validated = []
    for table, expected_digest in zip(
        tables, M37_SCRAMBLE_TABLE_SHA256S, strict=True
    ):
        item = validate_scramble_shift_table(
            table,
            epoch_count=3,
            score_bin_count=2 * M37_SCORE_HALF_BINS + 1,
            minimum_shift_bins=M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
            expected_sha256=expected_digest,
        ).copy()
        if item.shape != (M37_SCRAMBLE_COUNT, 3):
            raise V0P6ContractError("M37 scramble-table dimensions changed")
        item.setflags(write=False)
        validated.append(item)
    aggregate = np.asarray(np.stack(validated, axis=0), dtype="<i8", order="C")
    if hashlib.sha256(aggregate.tobytes()).hexdigest() != M37_SCRAMBLE_TABLES_SHA256:
        raise V0P6ContractError("aggregate M37 scramble-table SHA-256 changed")
    return tuple(validated)


def _epoch_product_inventory_sha256(
    inventory: Mapping[tuple[int, int], str],
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            [
                [template_index, width_index, digest]
                for (template_index, width_index), digest in sorted(
                    inventory.items()
                )
            ]
        )
    ).hexdigest()


def _cache_provenance_inventory_sha256(
    inventory: Mapping[
        int, tuple[tuple[str, ...], tuple[str, ...]]
    ],
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            [
                [width_index, list(plan_digests), list(payload_digests)]
                for width_index, (plan_digests, payload_digests) in sorted(
                    inventory.items()
                )
            ]
        )
    ).hexdigest()


def _mask_product_inventory_sha256(inventory: Mapping[int, str]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            [
                [template_index, digest]
                for template_index, digest in sorted(inventory.items())
            ]
        )
    ).hexdigest()


_RETENTION_RECORD_CHAIN_INITIAL_SHA256 = hashlib.sha256(
    canonical_json_bytes(
        {
            "artifact_type": "seti_repeater.retention_record_chain",
            "schema_version": 1,
        }
    )
).hexdigest()


def _advance_retention_record_chain(
    initial_sha256: str,
    records: Iterable[Mapping[str, Any]],
) -> str:
    """Extend an append-only record receipt without rehashing prior records."""
    state = bytes.fromhex(
        _frozen_sha256(initial_sha256, "retention record-chain identity")
    )
    for record in records:
        state = hashlib.sha256(state + canonical_json_bytes(dict(record))).digest()
    return state.hex()


@dataclass
class CalibrationAccumulator:
    """Fail-closed streaming maxima with an exact hypothesis inventory."""

    window_id: str
    score_bin_count: int
    template_count: int
    template_bank_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    scan_inventory_sha256: str
    factor_row_selection_sha256: str
    factor_table_sha256: str
    spectral_widths: tuple[int, ...]
    activity_subsets: tuple[tuple[int, ...], ...]
    minimum_active_epoch_snr: float | None
    stack_statistic: str
    experiment_contract_sha256: str
    analysis_contract_sha256: str
    expected_hypothesis_keys: frozenset[tuple[int, int, tuple[int, ...]]]
    scramble_shifts: np.ndarray = field(repr=False)
    scramble_table_sha256: str
    null_maxima: np.ndarray
    require_provenance_products: bool = False
    required_execution_engine: str = PYTHON_CALIBRATION_EXECUTION_ENGINE
    execution_engine_identity_sha256: str | None = None
    observed_maximum: float = -math.inf
    observed_score_cells: int = 0
    null_score_cells: int = 0
    null_maxima_sha256: str | None = None
    _visited_hypothesis_keys: set[tuple[int, int, tuple[int, ...]]] = field(
        default_factory=set, init=False, repr=False
    )
    _invalid: bool = field(default=False, init=False, repr=False)
    _sealed: bool = field(default=False, init=False, repr=False)
    _state_sha256: str = field(default="", init=False, repr=False)
    _epoch_product_by_template_width: dict[tuple[int, int], str] = field(
        default_factory=dict, init=False, repr=False
    )
    _cache_provenance_by_width: dict[
        int, tuple[tuple[str, ...], tuple[str, ...]]
    ] = field(default_factory=dict, init=False, repr=False)
    _mask_product_by_template: dict[int, str] = field(
        default_factory=dict, init=False, repr=False
    )

    @classmethod
    def create(
        cls,
        *,
        window_id: str,
        score_bin_count: int,
        template_count: int,
        template_bank_sha256_value: str,
        factor_basis_sha256_value: str,
        factor_basis_labels_sha256_value: str,
        scan_inventory_sha256_value: str,
        factor_row_selection_sha256_value: str,
        factor_table_sha256_value: str,
        spectral_widths: Iterable[int],
        activity_subsets: Iterable[Sequence[int]],
        minimum_active_epoch_snr: float | None,
        stack_statistic: str,
        scramble_shifts: np.ndarray,
        minimum_shift_bins: int,
        expected_scramble_sha256: str,
        require_provenance_products: bool = False,
        required_execution_engine: str = PYTHON_CALIBRATION_EXECUTION_ENGINE,
    ) -> "CalibrationAccumulator":
        score_bin_count = _strict_int(score_bin_count, "score-bin count")
        window_id = str(window_id)
        if not window_id:
            raise V0P6ContractError("calibration window identity must be non-empty")
        template_count = _strict_int(template_count, "template count")
        template_bank_digest = _frozen_sha256(
            template_bank_sha256_value, "template-bank identity"
        )
        factor_basis_digest = _frozen_sha256(
            factor_basis_sha256_value, "factor-basis identity"
        )
        factor_basis_labels_digest = _frozen_sha256(
            factor_basis_labels_sha256_value, "factor-basis labels identity"
        )
        scan_inventory_digest = _frozen_sha256(
            scan_inventory_sha256_value, "scan-inventory identity"
        )
        factor_row_selection_digest = _frozen_sha256(
            factor_row_selection_sha256_value,
            "factor-row selection identity",
        )
        factor_table_digest = _frozen_sha256(
            factor_table_sha256_value, "factor-table identity"
        )
        widths = _strict_widths(spectral_widths)
        activity = canonical_activity_subsets(activity_subsets)
        floor, statistic = _scoring_contract(
            minimum_active_epoch_snr, stack_statistic
        )
        keys = make_hypothesis_inventory(template_count, widths, activity)
        if score_bin_count < 1:
            raise V0P6ContractError(
                "calibration requires a score grid and hypothesis inventory"
            )
        raw_shifts = np.asarray(scramble_shifts)
        if raw_shifts.ndim != 2:
            raise V0P6ContractError(
                "scramble table must be a two-dimensional integer array"
            )
        expected_scramble_sha256 = _frozen_sha256(
            expected_scramble_sha256, "scramble-table identity"
        )
        shifts = validate_scramble_shift_table(
            raw_shifts,
            epoch_count=int(raw_shifts.shape[1]),
            score_bin_count=score_bin_count,
            minimum_shift_bins=minimum_shift_bins,
            expected_sha256=expected_scramble_sha256,
        ).copy()
        if max(epoch for subset in activity for epoch in subset) >= shifts.shape[1]:
            raise V0P6ContractError(
                "activity subset references an epoch absent from the scramble table"
            )
        shifts.setflags(write=False)
        experiment_digest = hypothesis_contract_sha256(
            score_bin_count=score_bin_count,
            epoch_count=shifts.shape[1],
            template_count=template_count,
            template_bank_sha256_value=template_bank_digest,
            spectral_widths=widths,
            activity_subsets=activity,
            minimum_active_epoch_snr=floor,
            stack_statistic=statistic,
            scramble_count=shifts.shape[0],
        )
        analysis_digest = factorized_analysis_contract_sha256(
            experiment_digest,
            factor_basis_digest,
            factor_basis_labels_digest,
            scan_inventory_digest,
            factor_table_digest,
        )
        if not isinstance(require_provenance_products, (bool, np.bool_)):
            raise V0P6ContractError(
                "calibration provenance requirement must be boolean"
            )
        execution_engine = str(required_execution_engine)
        if execution_engine not in {
            PYTHON_CALIBRATION_EXECUTION_ENGINE,
            M37_CALIBRATION_EXECUTION_ENGINE,
        }:
            raise V0P6ContractError(
                "calibration execution engine is not recognized"
            )
        accumulator = cls(
            window_id=window_id,
            score_bin_count=score_bin_count,
            template_count=template_count,
            template_bank_sha256=template_bank_digest,
            factor_basis_sha256=factor_basis_digest,
            factor_basis_labels_sha256=factor_basis_labels_digest,
            scan_inventory_sha256=scan_inventory_digest,
            factor_row_selection_sha256=factor_row_selection_digest,
            factor_table_sha256=factor_table_digest,
            spectral_widths=widths,
            activity_subsets=activity,
            minimum_active_epoch_snr=floor,
            stack_statistic=statistic,
            experiment_contract_sha256=experiment_digest,
            analysis_contract_sha256=analysis_digest,
            expected_hypothesis_keys=keys,
            scramble_shifts=shifts,
            scramble_table_sha256=expected_scramble_sha256,
            null_maxima=np.full(shifts.shape[0], -np.inf, dtype=np.float64),
            require_provenance_products=bool(require_provenance_products),
            required_execution_engine=execution_engine,
        )
        accumulator._checkpoint_state()
        return accumulator

    def _state_digest(self) -> str:
        visited = [
            [template_index, width_index, list(subset)]
            for template_index, width_index, subset in sorted(
                self._visited_hypothesis_keys
            )
        ]
        payload = {
            "window_id": str(self.window_id),
            "experiment_contract_sha256": _frozen_sha256(
                self.experiment_contract_sha256,
                "calibration experiment-contract identity",
            ),
            "analysis_contract_sha256": _frozen_sha256(
                self.analysis_contract_sha256,
                "calibration analysis-contract identity",
            ),
            "factor_row_selection_sha256": _frozen_sha256(
                self.factor_row_selection_sha256,
                "calibration factor-row selection identity",
            ),
            "scramble_table_sha256": _frozen_sha256(
                self.scramble_table_sha256,
                "calibration scramble-table identity",
            ),
            "require_provenance_products": bool(
                self.require_provenance_products
            ),
            "required_execution_engine": str(
                self.required_execution_engine
            ),
            "execution_engine_identity_sha256": (
                None
                if self.execution_engine_identity_sha256 is None
                else _frozen_sha256(
                    self.execution_engine_identity_sha256,
                    "calibration execution-engine identity",
                )
            ),
            "null_maxima_sha256": _raw_float64_vector_sha256(self.null_maxima),
            "observed_maximum_hex": float(self.observed_maximum).hex(),
            "observed_score_cells": _strict_int(
                self.observed_score_cells, "observed score-cell count"
            ),
            "null_score_cells": _strict_int(
                self.null_score_cells, "null score-cell count"
            ),
            "visited_hypothesis_keys": visited,
            "epoch_product_inventory_sha256": (
                _epoch_product_inventory_sha256(
                    self._epoch_product_by_template_width
                )
            ),
            "cache_provenance_inventory_sha256": (
                _cache_provenance_inventory_sha256(
                    self._cache_provenance_by_width
                )
            ),
            "mask_product_inventory_sha256": (
                _mask_product_inventory_sha256(
                    self._mask_product_by_template
                )
            ),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def _checkpoint_state(self) -> None:
        self._state_sha256 = self._state_digest()

    def _require_replay_integrity(self) -> None:
        reconstructed_contract = hypothesis_contract_sha256(
            score_bin_count=self.score_bin_count,
            epoch_count=self.scramble_shifts.shape[1],
            template_count=self.template_count,
            template_bank_sha256_value=self.template_bank_sha256,
            spectral_widths=self.spectral_widths,
            activity_subsets=self.activity_subsets,
            minimum_active_epoch_snr=self.minimum_active_epoch_snr,
            stack_statistic=self.stack_statistic,
            scramble_count=self.scramble_shifts.shape[0],
        )
        if reconstructed_contract != self.experiment_contract_sha256:
            self._invalidate("calibration experiment contract changed")
        reconstructed_analysis_contract = factorized_analysis_contract_sha256(
            reconstructed_contract,
            self.factor_basis_sha256,
            self.factor_basis_labels_sha256,
            self.scan_inventory_sha256,
            self.factor_table_sha256,
        )
        if reconstructed_analysis_contract != self.analysis_contract_sha256:
            self._invalidate("calibration factorized analysis contract changed")
        if not isinstance(self.require_provenance_products, bool):
            self._invalidate("calibration provenance requirement changed")
        if self.required_execution_engine not in {
            PYTHON_CALIBRATION_EXECUTION_ENGINE,
            M37_CALIBRATION_EXECUTION_ENGINE,
        }:
            self._invalidate("calibration execution engine changed")
        if self.execution_engine_identity_sha256 is not None:
            try:
                _frozen_sha256(
                    self.execution_engine_identity_sha256,
                    "calibration execution-engine identity",
                )
            except V0P6ContractError:
                self._invalidate("calibration execution-engine identity changed")
        if (
            self.scramble_shifts.flags.writeable
            or scramble_table_sha256(self.scramble_shifts)
            != self.scramble_table_sha256
        ):
            self._invalidate("calibration's frozen scramble table changed")
        try:
            observed_state = self._state_digest()
        except (TypeError, ValueError, V0P6ContractError) as error:
            self._invalidate("calibration replay state became invalid")
            raise AssertionError("unreachable") from error
        if observed_state != self._state_sha256:
            self._invalidate("calibration replay state changed outside the updater")

    def _invalidate(self, message: str) -> None:
        if self.null_maxima.flags.writeable:
            self.null_maxima.fill(-np.inf)
        else:
            self.null_maxima = np.full_like(self.null_maxima, -np.inf)
        self.observed_maximum = -math.inf
        self._epoch_product_by_template_width.clear()
        self._cache_provenance_by_width.clear()
        self._mask_product_by_template.clear()
        self.execution_engine_identity_sha256 = None
        self._invalid = True
        self._state_sha256 = ""
        raise V0P6IncompleteError(message)

    def finalize(self) -> dict[str, Any]:
        if self._invalid:
            raise V0P6IncompleteError("calibration accumulator is invalid")
        if self._sealed:
            raise V0P6ContractError("calibration accumulator is already sealed")
        self._require_replay_integrity()
        reconstructed = make_hypothesis_inventory(
            self.template_count, self.spectral_widths, self.activity_subsets
        )
        if reconstructed != self.expected_hypothesis_keys:
            self._invalidate("calibration's frozen hypothesis inventory changed")
        if self._visited_hypothesis_keys != set(self.expected_hypothesis_keys):
            missing = len(
                set(self.expected_hypothesis_keys) - self._visited_hypothesis_keys
            )
            extra = len(
                self._visited_hypothesis_keys - set(self.expected_hypothesis_keys)
            )
            self._invalidate(
                f"calibration hypothesis inventory mismatch: missing={missing}, extra={extra}"
            )
        expected_observed = len(self.expected_hypothesis_keys) * self.score_bin_count
        expected_null = expected_observed * self.null_maxima.size
        if (
            self.observed_score_cells != expected_observed
            or self.null_score_cells != expected_null
        ):
            self._invalidate("calibration score-cell accounting is incomplete")
        if self.require_provenance_products:
            expected_product_keys = {
                (template_index, width_index)
                for template_index in range(self.template_count)
                for width_index in range(len(self.spectral_widths))
            }
            if (
                set(self._epoch_product_by_template_width)
                != expected_product_keys
                or set(self._cache_provenance_by_width)
                != set(range(len(self.spectral_widths)))
                or set(self._mask_product_by_template)
                != set(range(self.template_count))
            ):
                self._invalidate(
                    "calibration provenance inventory is incomplete"
                )
        if (
            not math.isfinite(self.observed_maximum)
            or not np.all(np.isfinite(self.null_maxima))
        ):
            self._invalidate("calibration maxima are not finite")
        if self.execution_engine_identity_sha256 is None:
            self._invalidate("calibration execution engine was never attested")
        self.null_maxima_sha256 = float64_vector_sha256(self.null_maxima)
        self.null_maxima.setflags(write=False)
        self._sealed = True
        return {
            "window_id": self.window_id,
            "hypotheses_evaluated": len(self._visited_hypothesis_keys),
            "observed_score_cells": self.observed_score_cells,
            "null_score_cells": self.null_score_cells,
            "scramble_count": self.null_maxima.size,
            "scramble_table_sha256": self.scramble_table_sha256,
            "null_maxima_sha256": self.null_maxima_sha256,
            "experiment_contract_sha256": self.experiment_contract_sha256,
            "factor_basis_sha256": self.factor_basis_sha256,
            "factor_basis_labels_sha256": self.factor_basis_labels_sha256,
            "scan_inventory_sha256": self.scan_inventory_sha256,
            "factor_row_selection_sha256": self.factor_row_selection_sha256,
            "factor_table_sha256": self.factor_table_sha256,
            "analysis_contract_sha256": self.analysis_contract_sha256,
            "require_provenance_products": self.require_provenance_products,
            "execution_engine": self.required_execution_engine,
            "execution_engine_identity_sha256": (
                self.execution_engine_identity_sha256
            ),
            "epoch_product_inventory_sha256": (
                _epoch_product_inventory_sha256(
                    self._epoch_product_by_template_width
                )
            ),
            "cache_provenance_inventory_sha256": (
                _cache_provenance_inventory_sha256(
                    self._cache_provenance_by_width
                )
            ),
            "mask_product_inventory_sha256": (
                _mask_product_inventory_sha256(
                    self._mask_product_by_template
                )
            ),
            "sealed": True,
        }


def _register_calibration_execution_engine(
    accumulator: CalibrationAccumulator,
    engine: str,
    identity_sha256: str,
) -> None:
    engine = str(engine)
    identity = _frozen_sha256(
        identity_sha256, "calibration execution-engine identity"
    )
    if accumulator.required_execution_engine != engine:
        accumulator._invalidate(
            "calibration used an execution engine outside its frozen contract"
        )
    prior = accumulator.execution_engine_identity_sha256
    if prior is not None and prior != identity:
        accumulator._invalidate(
            "calibration execution-engine identity changed between hypotheses"
        )
    accumulator.execution_engine_identity_sha256 = identity


def update_calibration(
    accumulator: CalibrationAccumulator,
    epoch_vectors: np.ndarray,
    *,
    template_index: int,
    width_index: int,
    exclusion_mask: np.ndarray | None,
) -> None:
    """Update maxima for one width/template without retaining score arrays."""
    vectors = np.asarray(epoch_vectors, dtype=np.float32)
    if accumulator._invalid:
        raise V0P6IncompleteError("calibration accumulator is invalid")
    if accumulator._sealed:
        raise V0P6ContractError("calibration accumulator is already sealed")
    accumulator._require_replay_integrity()
    shifts = accumulator.scramble_shifts
    if vectors.ndim != 2:
        raise V0P6ContractError("epoch vectors must have [epoch, q] axes")
    if vectors.shape[1] != accumulator.score_bin_count:
        raise V0P6ContractError("epoch vectors do not match calibration score grid")
    if shifts.shape != (accumulator.null_maxima.size, vectors.shape[0]):
        raise V0P6ContractError("scramble table shape does not match accumulator/epochs")
    nfreq = vectors.shape[1]
    if np.any(shifts < 0) or np.any(shifts >= nfreq):
        raise V0P6ContractError("scramble shift lies outside the q grid")
    if exclusion_mask is not None:
        mask = np.asarray(exclusion_mask, dtype=bool)
        if mask.shape != vectors.shape:
            raise V0P6ContractError("calibration mask must have [epoch, q] axes")
    else:
        mask = None

    activity = accumulator.activity_subsets
    keys = {
        (
            _strict_int(template_index, "template index"),
            _strict_int(width_index, "spectral-width index"),
            subset,
        )
        for subset in activity
    }
    unexpected = keys - set(accumulator.expected_hypothesis_keys)
    duplicated = keys & accumulator._visited_hypothesis_keys
    if unexpected or duplicated:
        accumulator._invalidate(
            "calibration received an unexpected or duplicate hypothesis key"
        )
    _register_calibration_execution_engine(
        accumulator,
        PYTHON_CALIBRATION_EXECUTION_ENGINE,
        PYTHON_CALIBRATION_EXECUTION_IDENTITY_SHA256,
    )

    for subset in activity:
        score = stack_hypothesis(
            vectors,
            subset,
            minimum_active_epoch_snr=accumulator.minimum_active_epoch_snr,
            stack_statistic=accumulator.stack_statistic,
            exclusion_mask=mask,
        )
        accumulator.observed_maximum = max(
            accumulator.observed_maximum, float(np.max(score))
        )
        accumulator.observed_score_cells += nfreq

    rolled_vectors = np.empty_like(vectors)
    rolled_mask = None if mask is None else np.empty_like(mask)
    for scramble_index, epoch_shifts in enumerate(shifts):
        for epoch, shift in enumerate(epoch_shifts):
            rolled_vectors[epoch] = np.roll(vectors[epoch], int(shift))
            if rolled_mask is not None:
                rolled_mask[epoch] = np.roll(mask[epoch], int(shift))
        maximum = -math.inf
        for subset in activity:
            score = stack_hypothesis(
                rolled_vectors,
                subset,
                minimum_active_epoch_snr=accumulator.minimum_active_epoch_snr,
                stack_statistic=accumulator.stack_statistic,
                exclusion_mask=rolled_mask,
            )
            maximum = max(maximum, float(np.max(score)))
            accumulator.null_score_cells += nfreq
        accumulator.null_maxima[scramble_index] = max(
            float(accumulator.null_maxima[scramble_index]), maximum
        )
    accumulator._visited_hypothesis_keys.update(keys)
    accumulator._checkpoint_state()


def _update_m37_native_calibration(
    accumulator: CalibrationAccumulator,
    epoch_vectors: np.ndarray,
    *,
    template_index: int,
    width_index: int,
    exclusion_mask: np.ndarray,
) -> None:
    """Transactional M37 update using the reviewed bit-identical C kernel."""
    vectors = np.asarray(epoch_vectors)
    mask = np.asarray(exclusion_mask)
    if accumulator._invalid:
        raise V0P6IncompleteError("calibration accumulator is invalid")
    if accumulator._sealed:
        raise V0P6ContractError("calibration accumulator is already sealed")
    accumulator._require_replay_integrity()
    shifts = accumulator.scramble_shifts
    if (
        vectors.dtype != np.dtype(np.float32)
        or not vectors.dtype.isnative
        or vectors.ndim != 2
        or not vectors.flags.c_contiguous
        or not vectors.flags.aligned
        or vectors.shape != (3, accumulator.score_bin_count)
        or not np.all(np.isfinite(vectors))
    ):
        raise V0P6ContractError(
            "M37 native calibration requires finite native float32 [3,q] vectors"
        )
    if (
        mask.dtype != np.dtype(bool)
        or not mask.dtype.isnative
        or mask.shape != vectors.shape
        or not mask.flags.c_contiguous
        or not mask.flags.aligned
    ):
        raise V0P6ContractError(
            "M37 native calibration requires a native contiguous [3,q] mask"
        )
    if shifts.shape != (accumulator.null_maxima.size, 3):
        raise V0P6ContractError(
            "scramble table shape does not match the M37 native kernel"
        )
    nfreq = vectors.shape[1]
    if np.any(shifts < 0) or np.any(shifts >= nfreq):
        raise V0P6ContractError("scramble shift lies outside the q grid")

    template = _strict_int(template_index, "template index")
    width = _strict_int(width_index, "spectral-width index")
    keys = {
        (template, width, subset) for subset in accumulator.activity_subsets
    }
    if (
        keys - set(accumulator.expected_hypothesis_keys)
        or keys & accumulator._visited_hypothesis_keys
    ):
        accumulator._invalidate(
            "calibration received an unexpected or duplicate hypothesis key"
        )

    # Lazy import avoids a module cycle: the wrapper imports only the frozen
    # resource cap and error type from this module.
    from .calibration_kernel_v0p6 import (
        calibration_kernel_identity,
        m37_null_scramble_maxima,
    )

    kernel_identity = calibration_kernel_identity()
    if kernel_identity.openmp_max_threads < M37_CALIBRATION_THREAD_COUNT:
        raise V0P6ContractError(
            "M37 calibration runtime does not provide the frozen thread count"
        )
    invocation_identity = hashlib.sha256(
        canonical_json_bytes(
            {
                "execution_engine": M37_CALIBRATION_EXECUTION_ENGINE,
                "kernel_identity_sha256": kernel_identity.identity_sha256,
                "thread_count": M37_CALIBRATION_THREAD_COUNT,
            }
        )
    ).hexdigest()
    hypothesis_null_maxima = m37_null_scramble_maxima(
        vectors,
        mask,
        shifts,
        thread_count=M37_CALIBRATION_THREAD_COUNT,
    )

    observed_maximum = -math.inf
    for subset in accumulator.activity_subsets:
        score = stack_hypothesis(
            vectors,
            subset,
            minimum_active_epoch_snr=accumulator.minimum_active_epoch_snr,
            stack_statistic=accumulator.stack_statistic,
            exclusion_mask=mask,
        )
        observed_maximum = max(observed_maximum, float(np.max(score)))

    _register_calibration_execution_engine(
        accumulator,
        M37_CALIBRATION_EXECUTION_ENGINE,
        invocation_identity,
    )
    accumulator.observed_maximum = max(
        accumulator.observed_maximum, observed_maximum
    )
    accumulator.observed_score_cells += (
        nfreq * len(accumulator.activity_subsets)
    )
    accumulator.null_score_cells += (
        nfreq
        * len(accumulator.activity_subsets)
        * accumulator.null_maxima.size
    )
    np.maximum(
        accumulator.null_maxima,
        hypothesis_null_maxima,
        out=accumulator.null_maxima,
    )
    accumulator._visited_hypothesis_keys.update(keys)
    accumulator._checkpoint_state()


def update_m37_calibration(
    accumulator: CalibrationAccumulator,
    epoch_product: EpochVectorProduct,
    *,
    exclusion_mask: MaskProduct,
) -> None:
    """Update M37 calibration only from a provenance-bound ON product."""
    validate_epoch_vector_product(epoch_product)
    validate_mask_product(exclusion_mask)
    if (
        epoch_product.scan_kind != "on"
        or epoch_product.window_id != accumulator.window_id
        or epoch_product.proxy_grid_sha256
        != proxy_carrier_grid_sha256(
            make_m37_proxy_carrier_grid(accumulator.window_id)
        )
        or epoch_product.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or epoch_product.factor_basis_labels_sha256
        != M37_FACTOR_BASIS_LABELS_SHA256
        or epoch_product.factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or epoch_product.template_bank_sha256 != M37_BANK_SHA256
        or epoch_product.factor_basis_sha256
        != accumulator.factor_basis_sha256
        or epoch_product.factor_table_sha256
        != accumulator.factor_table_sha256
        or accumulator.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
        or accumulator.factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or accumulator.template_bank_sha256 != M37_BANK_SHA256
        or accumulator.spectral_widths != M37_SPECTRAL_WIDTHS
        or accumulator.activity_subsets != M37_ACTIVITY_SUBSETS
        or accumulator.minimum_active_epoch_snr
        != M37_MINIMUM_ACTIVE_EPOCH_SNR
        or accumulator.stack_statistic != "minimum_epoch"
        or exclusion_mask.window_id != epoch_product.window_id
        or exclusion_mask.scan_kind != "on"
        or exclusion_mask.template_index != epoch_product.template_index
        or exclusion_mask.proxy_grid_sha256
        != epoch_product.proxy_grid_sha256
        or exclusion_mask.factor_basis_sha256
        != epoch_product.factor_basis_sha256
        or exclusion_mask.factor_basis_labels_sha256
        != epoch_product.factor_basis_labels_sha256
        or exclusion_mask.factor_row_selection_sha256
        != epoch_product.factor_row_selection_sha256
        or exclusion_mask.template_bank_sha256
        != epoch_product.template_bank_sha256
        or exclusion_mask.factor_table_sha256
        != epoch_product.factor_table_sha256
        or epoch_product.product_sha256
        not in exclusion_mask.source_epoch_product_sha256s
        or exclusion_mask.spectral_widths != M37_SPECTRAL_WIDTHS
        or exclusion_mask.strong_snr != M37_RFI_STRONG_SNR
        or exclusion_mask.other_epochs_below_snr
        != M37_RFI_OTHER_EPOCHS_BELOW_SNR
        or exclusion_mask.guard_bins != M37_RFI_GUARD_Q_BINS
    ):
        raise V0P6ContractError(
            "M37 calibration and epoch-vector identities differ"
        )
    try:
        width_index = M37_SPECTRAL_WIDTHS.index(epoch_product.width_channels)
    except ValueError as error:
        raise V0P6ContractError("epoch product has a non-M37 width") from error
    product_key = (epoch_product.template_index, width_index)
    prior_product = accumulator._epoch_product_by_template_width.get(product_key)
    if prior_product is not None and prior_product != epoch_product.product_sha256:
        accumulator._invalidate(
            "calibration hypothesis used a different epoch product"
        )
    cache_provenance = (
        epoch_product.cache_plan_sha256s,
        epoch_product.cache_payload_sha256s,
    )
    prior_cache = accumulator._cache_provenance_by_width.get(width_index)
    if prior_cache is not None and prior_cache != cache_provenance:
        accumulator._invalidate(
            "calibration templates used different cache provenance"
        )
    prior_mask = accumulator._mask_product_by_template.get(
        epoch_product.template_index
    )
    if prior_mask is not None and prior_mask != exclusion_mask.product_sha256:
        accumulator._invalidate("calibration widths used different masks")
    _update_m37_native_calibration(
        accumulator,
        epoch_product.values,
        template_index=epoch_product.template_index,
        width_index=width_index,
        exclusion_mask=exclusion_mask.values,
    )
    accumulator._epoch_product_by_template_width[product_key] = (
        epoch_product.product_sha256
    )
    accumulator._cache_provenance_by_width[width_index] = cache_provenance
    accumulator._mask_product_by_template[epoch_product.template_index] = (
        exclusion_mask.product_sha256
    )
    accumulator._checkpoint_state()


def make_m37_calibration(
    window_id: str,
    explicit_scramble_table: np.ndarray,
    *,
    factor_table_sha256_value: str,
) -> CalibrationAccumulator:
    """Create one non-configurable M37 calibration accumulator."""
    window_id = str(window_id)
    try:
        window_index = M37_WINDOW_IDS.index(window_id)
    except ValueError as error:
        raise V0P6ContractError("unknown M37 calibration window") from error
    table = validate_scramble_shift_table(
        explicit_scramble_table,
        epoch_count=3,
        score_bin_count=2 * M37_SCORE_HALF_BINS + 1,
        minimum_shift_bins=M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
        expected_sha256=M37_SCRAMBLE_TABLE_SHA256S[window_index],
    )
    accumulator = CalibrationAccumulator.create(
        window_id=window_id,
        score_bin_count=2 * M37_SCORE_HALF_BINS + 1,
        template_count=M37_TEMPLATE_COUNT,
        template_bank_sha256_value=M37_BANK_SHA256,
        factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
        factor_row_selection_sha256_value=(
            M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        ),
        factor_table_sha256_value=factor_table_sha256_value,
        spectral_widths=M37_SPECTRAL_WIDTHS,
        activity_subsets=M37_ACTIVITY_SUBSETS,
        minimum_active_epoch_snr=M37_MINIMUM_ACTIVE_EPOCH_SNR,
        stack_statistic="minimum_epoch",
        scramble_shifts=table,
        minimum_shift_bins=M37_SCRAMBLE_MINIMUM_SHIFT_BINS,
        expected_scramble_sha256=M37_SCRAMBLE_TABLE_SHA256S[window_index],
        require_provenance_products=True,
        required_execution_engine=M37_CALIBRATION_EXECUTION_ENGINE,
    )
    if accumulator.experiment_contract_sha256 != M37_EXPERIMENT_CONTRACT_SHA256:
        raise V0P6ContractError("M37 experiment-contract SHA-256 changed")
    return accumulator


def _validated_global_null_maxima(
    calibrations: Sequence[CalibrationAccumulator],
    *,
    expected_window_ids: Sequence[str],
) -> np.ndarray:
    """Return immutable per-scramble maxima after all global identity gates."""
    calibrations = tuple(calibrations)
    expected_window_ids = tuple(str(item) for item in expected_window_ids)
    if not expected_window_ids or len(set(expected_window_ids)) != len(
        expected_window_ids
    ):
        raise V0P6ContractError("global calibration window inventory is invalid")
    if tuple(item.window_id for item in calibrations) != expected_window_ids:
        raise V0P6IncompleteError("global calibration window order/inventory changed")
    if any(item._invalid or not item._sealed for item in calibrations):
        raise V0P6IncompleteError("global threshold requires sealed calibrations")
    for item in calibrations:
        item._require_replay_integrity()
        reconstructed_contract = hypothesis_contract_sha256(
            score_bin_count=item.score_bin_count,
            epoch_count=item.scramble_shifts.shape[1],
            template_count=item.template_count,
            template_bank_sha256_value=item.template_bank_sha256,
            spectral_widths=item.spectral_widths,
            activity_subsets=item.activity_subsets,
            minimum_active_epoch_snr=item.minimum_active_epoch_snr,
            stack_statistic=item.stack_statistic,
            scramble_count=item.scramble_shifts.shape[0],
        )
        if reconstructed_contract != item.experiment_contract_sha256:
            raise V0P6IncompleteError("sealed calibration contract changed")
        if factorized_analysis_contract_sha256(
            reconstructed_contract,
            item.factor_basis_sha256,
            item.factor_basis_labels_sha256,
            item.scan_inventory_sha256,
            item.factor_table_sha256,
        ) != item.analysis_contract_sha256:
            raise V0P6IncompleteError(
                "sealed calibration factorized contract changed"
            )
        if (
            item.scramble_shifts.flags.writeable
            or scramble_table_sha256(item.scramble_shifts)
            != item.scramble_table_sha256
        ):
            raise V0P6IncompleteError("sealed scramble-table identity changed")
        if item.null_maxima.flags.writeable:
            raise V0P6IncompleteError("sealed null maxima unexpectedly remain mutable")
        if (
            item.null_maxima_sha256 is None
            or float64_vector_sha256(item.null_maxima) != item.null_maxima_sha256
        ):
            raise V0P6IncompleteError("sealed null-maxima identity changed")
    scramble_counts = {item.null_maxima.size for item in calibrations}
    if len(scramble_counts) != 1:
        raise V0P6IncompleteError("window scramble counts do not match")
    if len({item.experiment_contract_sha256 for item in calibrations}) != 1:
        raise V0P6IncompleteError(
            "calibration windows do not share one frozen experiment contract"
        )
    if len({item.analysis_contract_sha256 for item in calibrations}) != 1:
        raise V0P6IncompleteError(
            "calibration windows do not share one factorized analysis contract"
        )
    if len({item.factor_row_selection_sha256 for item in calibrations}) != 1:
        raise V0P6IncompleteError(
            "calibration factor-row selections differ between windows"
        )
    if len({item.require_provenance_products for item in calibrations}) != 1:
        raise V0P6IncompleteError(
            "calibration provenance requirements differ between windows"
        )
    if (
        len({item.required_execution_engine for item in calibrations}) != 1
        or any(
            item.execution_engine_identity_sha256 is None
            for item in calibrations
        )
        or len(
            {
                item.execution_engine_identity_sha256
                for item in calibrations
            }
        )
        != 1
    ):
        raise V0P6IncompleteError(
            "calibration execution-engine identities differ between windows"
        )
    if len(calibrations) > 1 and len(
        {item.scramble_table_sha256 for item in calibrations}
    ) != len(calibrations):
        raise V0P6IncompleteError(
            "every calibration window must use a distinct scramble table"
        )
    values = np.max(
        np.stack([item.null_maxima for item in calibrations], axis=0), axis=0
    )
    values.setflags(write=False)
    return values


def empirical_global_pvalue(
    calibrations: Sequence[CalibrationAccumulator],
    *,
    expected_window_ids: Sequence[str],
    score: float,
) -> float:
    """Return ``(1 + # null maxima >= score) / (N + 1)``."""
    score = float(score)
    if not math.isfinite(score):
        return 1.0
    values = _validated_global_null_maxima(
        calibrations, expected_window_ids=expected_window_ids
    )
    return float((1 + np.count_nonzero(values >= score)) / (values.size + 1))


_THRESHOLD_CERTIFICATE_REGISTRY: dict[
    int, tuple[weakref.ReferenceType[Any], bytes]
] = {}


@dataclass(frozen=True)
class ThresholdCertificate:
    """Immutable calibration-to-retention handoff."""

    window_ids: tuple[str, ...]
    experiment_contract_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    scan_inventory_sha256: str
    calibration_factor_row_selection_sha256: str
    factor_table_sha256: str
    analysis_contract_sha256: str
    calibration_epoch_product_inventory_sha256s: tuple[str, ...]
    calibration_cache_provenance_inventory_sha256s: tuple[str, ...]
    calibration_mask_product_inventory_sha256s: tuple[str, ...]
    calibration_execution_engines: tuple[str, ...]
    calibration_execution_identity_sha256s: tuple[str, ...]
    scramble_table_sha256s: tuple[str, ...]
    null_maxima_sha256s: tuple[str, ...]
    global_null_maxima_sha256: str
    reference_floor_snr: float
    empirical_quantile: float
    empirical_higher_quantile_snr: float
    operational_threshold_snr: float
    global_null_count: int
    inclusive_null_exceedances_at_threshold: int
    inclusive_rank_p_at_threshold: float
    scientific_empirical_p_ceiling: float
    certificate_sha256: str
    _receipt: object = field(repr=False, compare=False)

    def as_record(self) -> dict[str, Any]:
        return {
            "window_ids": list(self.window_ids),
            "experiment_contract_sha256": self.experiment_contract_sha256,
            "factor_basis_sha256": self.factor_basis_sha256,
            "factor_basis_labels_sha256": self.factor_basis_labels_sha256,
            "scan_inventory_sha256": self.scan_inventory_sha256,
            "calibration_factor_row_selection_sha256": (
                self.calibration_factor_row_selection_sha256
            ),
            "factor_table_sha256": self.factor_table_sha256,
            "analysis_contract_sha256": self.analysis_contract_sha256,
            "calibration_epoch_product_inventory_sha256s": list(
                self.calibration_epoch_product_inventory_sha256s
            ),
            "calibration_cache_provenance_inventory_sha256s": list(
                self.calibration_cache_provenance_inventory_sha256s
            ),
            "calibration_mask_product_inventory_sha256s": list(
                self.calibration_mask_product_inventory_sha256s
            ),
            "calibration_execution_engines": list(
                self.calibration_execution_engines
            ),
            "calibration_execution_identity_sha256s": list(
                self.calibration_execution_identity_sha256s
            ),
            "scramble_table_sha256s": list(self.scramble_table_sha256s),
            "null_maxima_sha256s": list(self.null_maxima_sha256s),
            "global_null_maxima_sha256": self.global_null_maxima_sha256,
            "reference_floor_snr": self.reference_floor_snr,
            "empirical_quantile": self.empirical_quantile,
            "empirical_higher_quantile_snr": (
                self.empirical_higher_quantile_snr
            ),
            "operational_threshold_snr": self.operational_threshold_snr,
            "global_null_count": self.global_null_count,
            "inclusive_null_exceedances_at_threshold": (
                self.inclusive_null_exceedances_at_threshold
            ),
            "inclusive_rank_p_at_threshold": self.inclusive_rank_p_at_threshold,
            "scientific_empirical_p_ceiling": (
                self.scientific_empirical_p_ceiling
            ),
            "scientific_eligibility_requires_rank_p": True,
            "certificate_sha256": self.certificate_sha256,
        }

    def __getitem__(self, key: str) -> Any:
        return self.as_record()[key]


def validate_threshold_certificate(
    certificate: ThresholdCertificate,
    *,
    expected_certificate_sha256: str | None = None,
) -> None:
    """Validate a live certificate or one bound to an independent digest."""
    if not isinstance(certificate, ThresholdCertificate):
        raise V0P6ContractError("threshold certificate has an invalid type")
    attestation = _THRESHOLD_CERTIFICATE_REGISTRY.get(
        id(certificate._receipt)
    )
    has_live_attestation = (
        attestation is not None and attestation[0]() is certificate
    )
    if not has_live_attestation and expected_certificate_sha256 is None:
        if attestation is not None:
            raise V0P6ContractError(
                "threshold certificate does not carry its live factory receipt"
            )
        raise V0P6ContractError(
            "threshold certificate lacks a live or trusted attestation"
        )
    record = certificate.as_record()
    if has_live_attestation and canonical_json_bytes(record) != attestation[1]:
        raise V0P6ContractError("threshold factory attestation changed")
    observed_digest = _frozen_sha256(
        record.pop("certificate_sha256"), "threshold-certificate identity"
    )
    expected_digest = hashlib.sha256(canonical_json_bytes(record)).hexdigest()
    if observed_digest != expected_digest:
        raise V0P6ContractError("threshold certificate SHA-256 changed")
    if expected_certificate_sha256 is not None and observed_digest != (
        _frozen_sha256(
            expected_certificate_sha256,
            "expected threshold-certificate identity",
        )
    ):
        raise V0P6ContractError(
            "threshold certificate differs from its independently supplied identity"
        )
    _frozen_sha256(
        certificate.experiment_contract_sha256, "experiment-contract identity"
    )
    _frozen_sha256(certificate.factor_basis_sha256, "factor-basis identity")
    _frozen_sha256(
        certificate.factor_basis_labels_sha256,
        "factor-basis labels identity",
    )
    _frozen_sha256(certificate.scan_inventory_sha256, "scan-inventory identity")
    _frozen_sha256(
        certificate.calibration_factor_row_selection_sha256,
        "calibration factor-row selection identity",
    )
    _frozen_sha256(certificate.factor_table_sha256, "factor-table identity")
    expected_analysis_contract = factorized_analysis_contract_sha256(
        certificate.experiment_contract_sha256,
        certificate.factor_basis_sha256,
        certificate.factor_basis_labels_sha256,
        certificate.scan_inventory_sha256,
        certificate.factor_table_sha256,
    )
    if certificate.analysis_contract_sha256 != expected_analysis_contract:
        raise V0P6ContractError("threshold factorized analysis contract changed")
    _frozen_sha256(
        certificate.global_null_maxima_sha256, "global-null identity"
    )
    if (
        not certificate.window_ids
        or any(not str(item) for item in certificate.window_ids)
        or len(set(certificate.window_ids)) != len(certificate.window_ids)
        or len(certificate.window_ids)
        != len(certificate.scramble_table_sha256s)
        or len(certificate.window_ids) != len(certificate.null_maxima_sha256s)
    ):
        raise V0P6ContractError("threshold certificate window inventory changed")
    provenance_inventories = (
        certificate.calibration_epoch_product_inventory_sha256s,
        certificate.calibration_cache_provenance_inventory_sha256s,
        certificate.calibration_mask_product_inventory_sha256s,
        certificate.calibration_execution_identity_sha256s,
    )
    if any(
        len(items) != len(certificate.window_ids)
        for items in provenance_inventories
    ):
        raise V0P6ContractError(
            "threshold calibration-provenance inventory changed"
        )
    for digest in (
        item for items in provenance_inventories for item in items
    ):
        _frozen_sha256(digest, "calibration-provenance inventory")
    if (
        len(certificate.calibration_execution_engines)
        != len(certificate.window_ids)
        or any(
            engine not in {
                PYTHON_CALIBRATION_EXECUTION_ENGINE,
                M37_CALIBRATION_EXECUTION_ENGINE,
            }
            for engine in certificate.calibration_execution_engines
        )
    ):
        raise V0P6ContractError(
            "threshold calibration execution-engine inventory changed"
        )
    global_null_count = _strict_int(
        certificate.global_null_count, "global null count"
    )
    exceedance_count = _strict_int(
        certificate.inclusive_null_exceedances_at_threshold,
        "threshold exceedance count",
    )
    if global_null_count < 1:
        raise V0P6ContractError("threshold certificate has no null realizations")
    (
        reference_floor_snr,
        empirical_quantile,
        empirical_higher_quantile_snr,
        operational_threshold_snr,
        inclusive_rank_p_at_threshold,
        scientific_empirical_p_ceiling,
    ) = (
        _finite_json_number(value, f"threshold certificate {name}")
        for name, value in (
            ("reference floor", certificate.reference_floor_snr),
            ("empirical quantile", certificate.empirical_quantile),
            (
                "empirical higher quantile",
                certificate.empirical_higher_quantile_snr,
            ),
            ("operational threshold", certificate.operational_threshold_snr),
            (
                "inclusive rank p-value",
                certificate.inclusive_rank_p_at_threshold,
            ),
            (
                "scientific p-value ceiling",
                certificate.scientific_empirical_p_ceiling,
            ),
        )
    )
    if not 0.0 <= empirical_quantile <= 1.0:
        raise V0P6ContractError("threshold certificate quantile is invalid")
    if not 0.0 < scientific_empirical_p_ceiling <= 1.0:
        raise V0P6ContractError("threshold certificate p ceiling is invalid")
    if exceedance_count < 0 or exceedance_count > global_null_count:
        raise V0P6ContractError("threshold certificate exceedance count is invalid")
    expected_p = (1 + exceedance_count) / (global_null_count + 1)
    if inclusive_rank_p_at_threshold != expected_p:
        raise V0P6ContractError("threshold certificate rank p-value changed")
    if operational_threshold_snr != max(
        reference_floor_snr, empirical_higher_quantile_snr
    ):
        raise V0P6ContractError("threshold certificate operational rule changed")
    for digest in (
        *certificate.scramble_table_sha256s,
        *certificate.null_maxima_sha256s,
    ):
        _frozen_sha256(digest, "threshold upstream identity")


def threshold_certificate_from_record(
    record: Mapping[str, Any],
    *,
    expected_certificate_sha256: str,
) -> ThresholdCertificate:
    """Rehydrate a persisted threshold handoff using an independent digest."""
    if not isinstance(record, Mapping):
        raise V0P6ContractError("threshold certificate record must be a mapping")
    try:
        detached = json.loads(canonical_json_bytes(dict(record)))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(
            "threshold certificate record is not canonical finite JSON"
        ) from error
    expected_fields = frozenset(ThresholdCertificate.__dataclass_fields__) - {
        "_receipt"
    }
    expected_fields = expected_fields | {
        "scientific_eligibility_requires_rank_p"
    }
    if frozenset(detached) != expected_fields:
        raise V0P6ContractError(
            "threshold certificate record fields do not match the schema"
        )
    if detached["scientific_eligibility_requires_rank_p"] is not True:
        raise V0P6ContractError(
            "threshold certificate scientific eligibility rule changed"
        )
    expected_digest = _frozen_sha256(
        expected_certificate_sha256,
        "expected threshold-certificate identity",
    )
    if detached["certificate_sha256"] != expected_digest:
        raise V0P6ContractError(
            "threshold certificate differs from its independently supplied identity"
        )
    receipt = object()
    certificate = ThresholdCertificate(
        window_ids=tuple(detached["window_ids"]),
        experiment_contract_sha256=detached["experiment_contract_sha256"],
        factor_basis_sha256=detached["factor_basis_sha256"],
        factor_basis_labels_sha256=detached[
            "factor_basis_labels_sha256"
        ],
        scan_inventory_sha256=detached["scan_inventory_sha256"],
        calibration_factor_row_selection_sha256=detached[
            "calibration_factor_row_selection_sha256"
        ],
        factor_table_sha256=detached["factor_table_sha256"],
        analysis_contract_sha256=detached["analysis_contract_sha256"],
        calibration_epoch_product_inventory_sha256s=tuple(
            detached["calibration_epoch_product_inventory_sha256s"]
        ),
        calibration_cache_provenance_inventory_sha256s=tuple(
            detached["calibration_cache_provenance_inventory_sha256s"]
        ),
        calibration_mask_product_inventory_sha256s=tuple(
            detached["calibration_mask_product_inventory_sha256s"]
        ),
        calibration_execution_engines=tuple(
            detached["calibration_execution_engines"]
        ),
        calibration_execution_identity_sha256s=tuple(
            detached["calibration_execution_identity_sha256s"]
        ),
        scramble_table_sha256s=tuple(detached["scramble_table_sha256s"]),
        null_maxima_sha256s=tuple(detached["null_maxima_sha256s"]),
        global_null_maxima_sha256=detached["global_null_maxima_sha256"],
        reference_floor_snr=detached["reference_floor_snr"],
        empirical_quantile=detached["empirical_quantile"],
        empirical_higher_quantile_snr=detached[
            "empirical_higher_quantile_snr"
        ],
        operational_threshold_snr=detached["operational_threshold_snr"],
        global_null_count=detached["global_null_count"],
        inclusive_null_exceedances_at_threshold=detached[
            "inclusive_null_exceedances_at_threshold"
        ],
        inclusive_rank_p_at_threshold=detached[
            "inclusive_rank_p_at_threshold"
        ],
        scientific_empirical_p_ceiling=detached[
            "scientific_empirical_p_ceiling"
        ],
        certificate_sha256=detached["certificate_sha256"],
        _receipt=receipt,
    )
    validate_threshold_certificate(
        certificate,
        expected_certificate_sha256=expected_digest,
    )
    registry_key = id(receipt)

    def discard_threshold_certificate_receipt(
        reference: weakref.ReferenceType[Any],
        *,
        key: int = registry_key,
    ) -> None:
        current = _THRESHOLD_CERTIFICATE_REGISTRY.get(key)
        if current is not None and current[0] is reference:
            _THRESHOLD_CERTIFICATE_REGISTRY.pop(key, None)

    _THRESHOLD_CERTIFICATE_REGISTRY[registry_key] = (
        weakref.ref(certificate, discard_threshold_certificate_receipt),
        canonical_json_bytes(certificate.as_record()),
    )
    validate_threshold_certificate(certificate)
    return certificate


def calibrated_threshold(
    calibrations: Sequence[CalibrationAccumulator],
    *,
    expected_window_ids: Sequence[str],
    reference_floor: float,
    quantile: float = 0.99,
    scientific_p_ceiling: float = M37_SCIENTIFIC_P_CEILING,
) -> ThresholdCertificate:
    """Freeze the higher empirical quantile and apply a non-adaptive floor."""
    calibrations = tuple(calibrations)
    if not 0.0 <= float(quantile) <= 1.0:
        raise V0P6ContractError("threshold quantile must lie in [0, 1]")
    scientific_p_ceiling = float(scientific_p_ceiling)
    if not 0.0 < scientific_p_ceiling <= 1.0:
        raise V0P6ContractError("scientific empirical-p ceiling must lie in (0, 1]")
    values = _validated_global_null_maxima(
        calibrations, expected_window_ids=expected_window_ids
    )
    empirical = float(np.quantile(values, float(quantile), method="higher"))
    reference_floor = float(reference_floor)
    if not math.isfinite(reference_floor):
        raise V0P6ContractError("threshold reference floor must be finite")
    operational = max(reference_floor, empirical)
    exceedances = int(np.count_nonzero(values >= operational))
    record = {
        "window_ids": list(str(item) for item in expected_window_ids),
        "experiment_contract_sha256": calibrations[0].experiment_contract_sha256,
        "factor_basis_sha256": calibrations[0].factor_basis_sha256,
        "factor_basis_labels_sha256": (
            calibrations[0].factor_basis_labels_sha256
        ),
        "scan_inventory_sha256": calibrations[0].scan_inventory_sha256,
        "calibration_factor_row_selection_sha256": (
            calibrations[0].factor_row_selection_sha256
        ),
        "factor_table_sha256": calibrations[0].factor_table_sha256,
        "analysis_contract_sha256": calibrations[0].analysis_contract_sha256,
        "calibration_epoch_product_inventory_sha256s": [
            _epoch_product_inventory_sha256(
                item._epoch_product_by_template_width
            )
            for item in calibrations
        ],
        "calibration_cache_provenance_inventory_sha256s": [
            _cache_provenance_inventory_sha256(
                item._cache_provenance_by_width
            )
            for item in calibrations
        ],
        "calibration_mask_product_inventory_sha256s": [
            _mask_product_inventory_sha256(item._mask_product_by_template)
            for item in calibrations
        ],
        "calibration_execution_engines": [
            item.required_execution_engine for item in calibrations
        ],
        "calibration_execution_identity_sha256s": [
            str(item.execution_engine_identity_sha256)
            for item in calibrations
        ],
        "scramble_table_sha256s": [
            item.scramble_table_sha256 for item in calibrations
        ],
        "null_maxima_sha256s": [
            str(item.null_maxima_sha256) for item in calibrations
        ],
        "global_null_maxima_sha256": float64_vector_sha256(values),
        "reference_floor_snr": reference_floor,
        "empirical_quantile": float(quantile),
        "empirical_higher_quantile_snr": empirical,
        "operational_threshold_snr": operational,
        "global_null_count": int(values.size),
        "inclusive_null_exceedances_at_threshold": exceedances,
        "inclusive_rank_p_at_threshold": float(
            (1 + exceedances) / (values.size + 1)
        ),
        "scientific_empirical_p_ceiling": scientific_p_ceiling,
        "scientific_eligibility_requires_rank_p": True,
    }
    digest = hashlib.sha256(canonical_json_bytes(record)).hexdigest()
    receipt = object()
    certificate = ThresholdCertificate(
        window_ids=tuple(record["window_ids"]),
        experiment_contract_sha256=record["experiment_contract_sha256"],
        factor_basis_sha256=record["factor_basis_sha256"],
        factor_basis_labels_sha256=record[
            "factor_basis_labels_sha256"
        ],
        scan_inventory_sha256=record["scan_inventory_sha256"],
        calibration_factor_row_selection_sha256=record[
            "calibration_factor_row_selection_sha256"
        ],
        factor_table_sha256=record["factor_table_sha256"],
        analysis_contract_sha256=record["analysis_contract_sha256"],
        calibration_epoch_product_inventory_sha256s=tuple(
            record["calibration_epoch_product_inventory_sha256s"]
        ),
        calibration_cache_provenance_inventory_sha256s=tuple(
            record["calibration_cache_provenance_inventory_sha256s"]
        ),
        calibration_mask_product_inventory_sha256s=tuple(
            record["calibration_mask_product_inventory_sha256s"]
        ),
        calibration_execution_engines=tuple(
            record["calibration_execution_engines"]
        ),
        calibration_execution_identity_sha256s=tuple(
            record["calibration_execution_identity_sha256s"]
        ),
        scramble_table_sha256s=tuple(record["scramble_table_sha256s"]),
        null_maxima_sha256s=tuple(record["null_maxima_sha256s"]),
        global_null_maxima_sha256=record["global_null_maxima_sha256"],
        reference_floor_snr=record["reference_floor_snr"],
        empirical_quantile=record["empirical_quantile"],
        empirical_higher_quantile_snr=record[
            "empirical_higher_quantile_snr"
        ],
        operational_threshold_snr=record["operational_threshold_snr"],
        global_null_count=record["global_null_count"],
        inclusive_null_exceedances_at_threshold=record[
            "inclusive_null_exceedances_at_threshold"
        ],
        inclusive_rank_p_at_threshold=record[
            "inclusive_rank_p_at_threshold"
        ],
        scientific_empirical_p_ceiling=record[
            "scientific_empirical_p_ceiling"
        ],
        certificate_sha256=digest,
        _receipt=receipt,
    )
    registry_key = id(receipt)

    def discard_threshold_certificate_receipt(
        reference: weakref.ReferenceType[Any],
        *,
        key: int = registry_key,
    ) -> None:
        current = _THRESHOLD_CERTIFICATE_REGISTRY.get(key)
        if current is not None and current[0] is reference:
            _THRESHOLD_CERTIFICATE_REGISTRY.pop(key, None)

    _THRESHOLD_CERTIFICATE_REGISTRY[registry_key] = (
        weakref.ref(certificate, discard_threshold_certificate_receipt),
        canonical_json_bytes(certificate.as_record()),
    )
    validate_threshold_certificate(certificate)
    return certificate


def finalize_m37_threshold(
    calibrations: Sequence[CalibrationAccumulator],
) -> ThresholdCertificate:
    """Combine exactly five M37 windows with the frozen threshold rule."""
    calibrations = tuple(calibrations)
    if tuple(item.window_id for item in calibrations) != M37_WINDOW_IDS:
        raise V0P6IncompleteError("M37 calibration windows changed or reordered")
    if tuple(
        item.scramble_table_sha256 for item in calibrations
    ) != M37_SCRAMBLE_TABLE_SHA256S:
        raise V0P6IncompleteError("M37 scramble-table inventory changed")
    if any(
        item.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or item.factor_basis_labels_sha256
        != M37_FACTOR_BASIS_LABELS_SHA256
        or item.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
        or item.factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or item.require_provenance_products is not True
        or item.required_execution_engine
        != M37_CALIBRATION_EXECUTION_ENGINE
        or item.execution_engine_identity_sha256 is None
        for item in calibrations
    ):
        raise V0P6IncompleteError("M37 calibration provenance contract changed")
    certificate = calibrated_threshold(
        calibrations,
        expected_window_ids=M37_WINDOW_IDS,
        reference_floor=M37_THRESHOLD_REFERENCE_FLOOR_SNR,
        quantile=M37_THRESHOLD_QUANTILE,
        scientific_p_ceiling=M37_SCIENTIFIC_P_CEILING,
    )
    if (
        certificate.experiment_contract_sha256
        != M37_EXPERIMENT_CONTRACT_SHA256
        or certificate.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or certificate.factor_basis_labels_sha256
        != M37_FACTOR_BASIS_LABELS_SHA256
        or certificate.scan_inventory_sha256 != M37_SCAN_INVENTORY_SHA256
        or certificate.calibration_factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or certificate.calibration_execution_engines
        != (M37_CALIBRATION_EXECUTION_ENGINE,) * len(M37_WINDOW_IDS)
    ):
        raise V0P6IncompleteError("M37 threshold experiment contract changed")
    return certificate


_RETENTION_CERTIFICATE_ATTESTATIONS: dict[str, bytes] = {}
_RETENTION_CERTIFICATE_ATTESTATION_CAP = 1_024


@dataclass
class ExhaustiveRetentionLedger:
    """Fail-closed, all-cell retention after a frozen threshold is known."""

    window_id: str
    scan_kind: str
    grid: ProxyCarrierGrid
    threshold_certificate: ThresholdCertificate
    maximum_records: int
    template_bank: Sequence[dict[str, Any]]
    spectral_widths: Sequence[int]
    activity_subsets: Sequence[Sequence[int]]
    expected_template_bank_sha256: str | None
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    scan_inventory_sha256: str
    factor_row_selection_sha256: str
    factor_table_sha256: str
    epoch_count: int
    minimum_active_epoch_snr: float | None
    stack_statistic: str
    require_epoch_vector_product: bool = False
    require_mask_product: bool = False
    threshold: float = field(init=False)
    maximum_record_canonical_bytes: int = 6_144
    maximum_evidence_canonical_bytes: int | None = 96_000_000
    _records: list[dict[str, Any]] = field(default_factory=list, init=False)
    _hypotheses: set[tuple[int, int, tuple[int, ...]]] = field(
        default_factory=set, init=False
    )
    _score_cells: int = field(default=0, init=False)
    _canonical_record_bytes: int = field(default=0, init=False)
    _invalid: bool = field(default=False, init=False)
    _sealed: bool = field(default=False, init=False)
    _bank_by_index: tuple[dict[str, Any], ...] = field(
        default_factory=tuple, init=False, repr=False
    )
    _expected_hypothesis_keys: frozenset[
        tuple[int, int, tuple[int, ...]]
    ] = field(default_factory=frozenset, init=False, repr=False)
    _template_bank_digest: str = field(default="", init=False, repr=False)
    _experiment_contract_sha256: str = field(default="", init=False, repr=False)
    _analysis_contract_sha256: str = field(default="", init=False, repr=False)
    _ledger_contract_sha256: str = field(default="", init=False, repr=False)
    _record_chain_sha256: str = field(
        default=_RETENTION_RECORD_CHAIN_INITIAL_SHA256,
        init=False,
        repr=False,
    )
    _replay_state_sha256: str = field(default="", init=False, repr=False)
    _certificate_bytes: bytes | None = field(default=None, init=False, repr=False)
    _validated_epoch_product_objects: weakref.WeakValueDictionary[
        int, EpochVectorProduct
    ] = field(
        default_factory=weakref.WeakValueDictionary, init=False, repr=False
    )
    _epoch_product_by_template_width: dict[tuple[int, int], str] = field(
        default_factory=dict, init=False, repr=False
    )
    _cache_provenance_by_width: dict[
        int, tuple[tuple[str, ...], tuple[str, ...]]
    ] = field(default_factory=dict, init=False, repr=False)
    _validated_mask_product_objects: weakref.WeakValueDictionary[
        int, MaskProduct
    ] = field(
        default_factory=weakref.WeakValueDictionary, init=False, repr=False
    )
    _mask_product_by_template: dict[int, str] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.window_id = str(self.window_id)
        if not self.window_id:
            raise V0P6ContractError("retention window identity must be non-empty")
        self.scan_kind = str(self.scan_kind).lower()
        if self.scan_kind not in {"on", "off"}:
            raise V0P6ContractError("retention scan kind must be 'on' or 'off'")
        if not isinstance(self.require_epoch_vector_product, (bool, np.bool_)):
            raise V0P6ContractError(
                "epoch-vector provenance requirement must be boolean"
            )
        self.require_epoch_vector_product = bool(
            self.require_epoch_vector_product
        )
        if not isinstance(self.require_mask_product, (bool, np.bool_)):
            raise V0P6ContractError("mask-product requirement must be boolean")
        self.require_mask_product = bool(self.require_mask_product)
        self.factor_basis_sha256 = _frozen_sha256(
            self.factor_basis_sha256, "retention factor-basis identity"
        )
        self.factor_basis_labels_sha256 = _frozen_sha256(
            self.factor_basis_labels_sha256,
            "retention factor-basis labels identity",
        )
        self.scan_inventory_sha256 = _frozen_sha256(
            self.scan_inventory_sha256, "retention scan-inventory identity"
        )
        self.factor_row_selection_sha256 = _frozen_sha256(
            self.factor_row_selection_sha256,
            "retention factor-row selection identity",
        )
        self.factor_table_sha256 = _frozen_sha256(
            self.factor_table_sha256, "retention factor-table identity"
        )
        validate_threshold_certificate(self.threshold_certificate)
        self.threshold = float(
            self.threshold_certificate.operational_threshold_snr
        )
        self.maximum_records = _strict_int(
            self.maximum_records, "retention record capacity"
        )
        if not math.isfinite(self.threshold):
            raise V0P6ContractError("retention threshold must be finite")
        if self.maximum_records < 0:
            raise V0P6ContractError("retention capacity must be non-negative")

        try:
            bank = json.loads(canonical_json_bytes(list(self.template_bank)))
        except (TypeError, ValueError) as error:
            raise V0P6ContractError(
                "template bank is not canonical finite JSON"
            ) from error
        if not bank:
            raise V0P6ContractError("retention requires a non-empty template bank")
        required_template_fields = {
            "template_index",
            "line_index",
            "line_coefficient",
            "projected_scale",
            "phase_cycles",
        }
        for expected_index, template in enumerate(bank):
            if not isinstance(template, dict) or not required_template_fields <= set(
                template
            ):
                raise V0P6ContractError(
                    "template bank record lacks required v0.6 fields"
                )
            if (
                _strict_int(template["template_index"], "template index")
                != expected_index
            ):
                raise V0P6ContractError(
                    "template bank indices must be sequential in canonical order"
                )
            for name in (
                "line_coefficient",
                "projected_scale",
                "phase_cycles",
            ):
                if not math.isfinite(float(template[name])):
                    raise V0P6ContractError(
                        f"template bank contains non-finite {name}"
                    )
        digest = template_bank_sha256(bank)
        if (
            self.expected_template_bank_sha256 is not None
            and digest != str(self.expected_template_bank_sha256)
        ):
            raise V0P6ContractError(
                "retention template-bank SHA-256 does not match the frozen bank"
            )
        self._bank_by_index = tuple(bank)
        self.template_bank = self._bank_by_index
        self._template_bank_digest = digest
        self.spectral_widths = _strict_widths(self.spectral_widths)
        self.activity_subsets = canonical_activity_subsets(self.activity_subsets)
        self.epoch_count = _strict_int(self.epoch_count, "retention epoch count")
        if self.epoch_count < 1 or max(
            epoch for subset in self.activity_subsets for epoch in subset
        ) >= self.epoch_count:
            raise V0P6ContractError(
                "retention activity subsets exceed the frozen epoch inventory"
            )
        (
            self.minimum_active_epoch_snr,
            self.stack_statistic,
        ) = _scoring_contract(
            self.minimum_active_epoch_snr, self.stack_statistic
        )
        self._expected_hypothesis_keys = make_hypothesis_inventory(
            len(self._bank_by_index), self.spectral_widths, self.activity_subsets
        )
        self._experiment_contract_sha256 = hypothesis_contract_sha256(
            score_bin_count=self.grid.score_bin_count,
            epoch_count=self.epoch_count,
            template_count=len(self._bank_by_index),
            template_bank_sha256_value=self._template_bank_digest,
            spectral_widths=self.spectral_widths,
            activity_subsets=self.activity_subsets,
            minimum_active_epoch_snr=self.minimum_active_epoch_snr,
            stack_statistic=self.stack_statistic,
            scramble_count=self.threshold_certificate.global_null_count,
        )
        if (
            self._experiment_contract_sha256
            != self.threshold_certificate.experiment_contract_sha256
        ):
            raise V0P6ContractError(
                "retention and threshold experiment contracts differ"
            )
        self._analysis_contract_sha256 = factorized_analysis_contract_sha256(
            self._experiment_contract_sha256,
            self.factor_basis_sha256,
            self.factor_basis_labels_sha256,
            self.scan_inventory_sha256,
            self.factor_table_sha256,
        )
        if (
            self.factor_basis_sha256
            != self.threshold_certificate.factor_basis_sha256
            or self.factor_basis_labels_sha256
            != self.threshold_certificate.factor_basis_labels_sha256
            or self.scan_inventory_sha256
            != self.threshold_certificate.scan_inventory_sha256
            or self.factor_table_sha256
            != self.threshold_certificate.factor_table_sha256
            or self._analysis_contract_sha256
            != self.threshold_certificate.analysis_contract_sha256
        ):
            raise V0P6ContractError(
                "retention and threshold factor contracts differ"
            )
        if self.scan_kind == "on" and self.factor_row_selection_sha256 != (
            self.threshold_certificate.calibration_factor_row_selection_sha256
        ):
            raise V0P6ContractError(
                "retention and calibration factor-row selections differ"
            )
        if self.window_id not in self.threshold_certificate.window_ids:
            raise V0P6ContractError(
                "retention window is absent from the threshold certificate"
            )

        self.maximum_record_canonical_bytes = _strict_int(
            self.maximum_record_canonical_bytes,
            "canonical record-byte capacity",
        )
        if self.maximum_record_canonical_bytes < 1:
            raise V0P6ContractError("canonical record-byte cap must be positive")
        if self.maximum_evidence_canonical_bytes is not None:
            self.maximum_evidence_canonical_bytes = _strict_int(
                self.maximum_evidence_canonical_bytes,
                "canonical evidence-byte capacity",
            )
            if self.maximum_evidence_canonical_bytes < 1:
                raise V0P6ContractError(
                    "canonical evidence-byte cap must be positive"
                )
        self._ledger_contract_sha256 = self._current_contract_sha256()
        self._checkpoint_replay_state()

    def _replay_state_digest(self) -> str:
        hypotheses = [
            [template_index, width_index, list(subset)]
            for template_index, width_index, subset in sorted(self._hypotheses)
        ]
        payload = {
            "hypotheses": hypotheses,
            "score_cells": _strict_int(
                self._score_cells, "retention score-cell count"
            ),
            "canonical_record_bytes": _strict_int(
                self._canonical_record_bytes, "canonical retained-record bytes"
            ),
            "record_count": len(self._records),
            "record_chain_sha256": _frozen_sha256(
                self._record_chain_sha256, "retention record-chain identity"
            ),
            "epoch_product_inventory_sha256": _epoch_product_inventory_sha256(
                self._epoch_product_by_template_width
            ),
            "cache_provenance_inventory_sha256": (
                _cache_provenance_inventory_sha256(
                    self._cache_provenance_by_width
                )
            ),
            "mask_product_inventory_sha256": _mask_product_inventory_sha256(
                self._mask_product_by_template
            ),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def _checkpoint_replay_state(self) -> None:
        self._replay_state_sha256 = self._replay_state_digest()

    def _require_replay_state(self) -> None:
        try:
            observed = self._replay_state_digest()
        except (TypeError, ValueError, V0P6ContractError) as error:
            self._invalidate(
                "retention replay state became invalid",
                V0P6IncompleteError,
            )
            raise AssertionError("unreachable") from error
        if observed != self._replay_state_sha256:
            self._invalidate(
                "retention replay state changed outside the updater",
                V0P6IncompleteError,
            )

    def _current_contract_sha256(self) -> str:
        validate_threshold_certificate(self.threshold_certificate)
        current_bank = json.loads(
            canonical_json_bytes(list(self.template_bank))
        )
        payload = {
            "window_id": str(self.window_id),
            "scan_kind": str(self.scan_kind),
            "proxy_grid_sha256": proxy_carrier_grid_sha256(self.grid),
            "threshold_certificate_sha256": (
                self.threshold_certificate.certificate_sha256
            ),
            "threshold": float(self.threshold),
            "maximum_records": _strict_int(
                self.maximum_records, "retention record capacity"
            ),
            "template_bank_sha256": template_bank_sha256(current_bank),
            "expected_template_bank_sha256": self.expected_template_bank_sha256,
            "factor_basis_sha256": _frozen_sha256(
                self.factor_basis_sha256, "retention factor-basis identity"
            ),
            "factor_basis_labels_sha256": _frozen_sha256(
                self.factor_basis_labels_sha256,
                "retention factor-basis labels identity",
            ),
            "scan_inventory_sha256": _frozen_sha256(
                self.scan_inventory_sha256,
                "retention scan-inventory identity",
            ),
            "factor_row_selection_sha256": _frozen_sha256(
                self.factor_row_selection_sha256,
                "retention factor-row selection identity",
            ),
            "factor_table_sha256": _frozen_sha256(
                self.factor_table_sha256, "retention factor-table identity"
            ),
            "spectral_widths": list(_strict_widths(self.spectral_widths)),
            "activity_subsets": [
                list(item)
                for item in canonical_activity_subsets(self.activity_subsets)
            ],
            "epoch_count": _strict_int(
                self.epoch_count, "retention epoch count"
            ),
            "experiment_contract_sha256": self._experiment_contract_sha256,
            "analysis_contract_sha256": self._analysis_contract_sha256,
            "minimum_active_epoch_snr": _scoring_contract(
                self.minimum_active_epoch_snr, self.stack_statistic
            )[0],
            "stack_statistic": _scoring_contract(
                self.minimum_active_epoch_snr, self.stack_statistic
            )[1],
            "require_epoch_vector_product": bool(
                self.require_epoch_vector_product
            ),
            "require_mask_product": bool(self.require_mask_product),
            "maximum_record_canonical_bytes": _strict_int(
                self.maximum_record_canonical_bytes,
                "canonical record-byte capacity",
            ),
            "maximum_evidence_canonical_bytes": (
                None
                if self.maximum_evidence_canonical_bytes is None
                else _strict_int(
                    self.maximum_evidence_canonical_bytes,
                    "canonical evidence-byte capacity",
                )
            ),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def _require_contract(self) -> None:
        try:
            observed = self._current_contract_sha256()
        except (TypeError, ValueError, V0P6ContractError) as error:
            self._invalidate(
                "retention's frozen contract became invalid",
                V0P6IncompleteError,
            )
            raise AssertionError("unreachable") from error
        if observed != self._ledger_contract_sha256:
            self._invalidate(
                "retention's frozen contract changed during replay",
                V0P6IncompleteError,
            )
        self._require_replay_state()

    def _invalidate(
        self,
        message: str,
        error_type: type[Exception] = V0P6CapacityError,
    ) -> None:
        self._records.clear()
        self._hypotheses.clear()
        self._score_cells = 0
        self._canonical_record_bytes = 0
        self._record_chain_sha256 = _RETENTION_RECORD_CHAIN_INITIAL_SHA256
        self._replay_state_sha256 = ""
        self._validated_epoch_product_objects.clear()
        self._epoch_product_by_template_width.clear()
        self._cache_provenance_by_width.clear()
        self._validated_mask_product_objects.clear()
        self._mask_product_by_template.clear()
        self._invalid = True
        raise error_type(message)

    def add_hypothesis(
        self,
        epoch_vectors: np.ndarray | EpochVectorProduct,
        subset: Sequence[int],
        *,
        template: dict[str, Any],
        width_index: int,
        width_channels: int,
        exclusion_mask: np.ndarray | MaskProduct | None,
    ) -> None:
        if self._invalid:
            raise V0P6CapacityError("retention ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("retention ledger is already sealed")
        self._require_contract()
        product: EpochVectorProduct | None
        if isinstance(epoch_vectors, EpochVectorProduct):
            cached_product = self._validated_epoch_product_objects.get(
                id(epoch_vectors)
            )
            validate_epoch_vector_product(
                epoch_vectors,
                verify_values=cached_product is not epoch_vectors,
            )
            self._validated_epoch_product_objects[id(epoch_vectors)] = (
                epoch_vectors
            )
            product = epoch_vectors
            vectors = epoch_vectors.values
        else:
            product = None
            if self.require_epoch_vector_product:
                self._invalidate(
                    "retention requires provenance-bound epoch vectors",
                    V0P6IncompleteError,
                )
            vectors = np.asarray(epoch_vectors, dtype=np.float32)
        if vectors.shape != (self.epoch_count, self.grid.score_bin_count):
            self._invalidate(
                "retention epoch-vector shape changed",
                V0P6IncompleteError,
            )
        mask_product: MaskProduct | None
        if isinstance(exclusion_mask, MaskProduct):
            cached_mask = self._validated_mask_product_objects.get(
                id(exclusion_mask)
            )
            validate_mask_product(
                exclusion_mask,
                verify_values=cached_mask is not exclusion_mask,
            )
            self._validated_mask_product_objects[id(exclusion_mask)] = (
                exclusion_mask
            )
            mask_product = exclusion_mask
            mask_values: np.ndarray | None = exclusion_mask.values
        else:
            mask_product = None
            if self.require_mask_product:
                self._invalidate(
                    "retention requires a provenance-bound mask product",
                    V0P6IncompleteError,
                )
            mask_values = (
                None
                if exclusion_mask is None
                else np.asarray(exclusion_mask, dtype=bool)
            )
        if mask_values is not None and mask_values.shape != vectors.shape:
            self._invalidate(
                "retention mask must have the exact [epoch, q] shape",
                V0P6IncompleteError,
            )
        try:
            subset_tuple = canonical_activity_subsets((subset,))[0]
            template_index = _strict_int(
                template["template_index"], "template index"
            )
            width_index = _strict_int(width_index, "spectral-width index")
            width_channels = _strict_int(width_channels, "spectral width")
        except (KeyError, TypeError, ValueError, V0P6ContractError) as error:
            self._invalidate(
                "retention received a malformed hypothesis key",
                V0P6IncompleteError,
            )
            raise AssertionError("unreachable") from error
        key = (template_index, width_index, subset_tuple)
        if key not in self._expected_hypothesis_keys:
            self._invalidate(
                f"unexpected retention hypothesis: {key}",
                V0P6IncompleteError,
            )
        if key in self._hypotheses:
            self._invalidate(
                f"duplicate retention hypothesis: {key}",
                V0P6IncompleteError,
            )
        canonical_template = self._bank_by_index[template_index]
        try:
            template_matches = canonical_json_bytes(template) == canonical_json_bytes(
                canonical_template
            )
        except (TypeError, ValueError):
            template_matches = False
        if not template_matches:
            self._invalidate(
                "retention template record does not match the frozen bank",
                V0P6IncompleteError,
            )
        if width_channels != self.spectral_widths[width_index]:
            self._invalidate(
                "retention width index/channels do not match the frozen widths",
                V0P6IncompleteError,
            )
        if product is not None and (
            product.window_id != self.window_id
            or product.scan_kind != self.scan_kind
            or product.template_index != template_index
            or product.width_channels != width_channels
            or product.proxy_grid_sha256 != proxy_carrier_grid_sha256(self.grid)
            or product.factor_basis_sha256 != self.factor_basis_sha256
            or product.factor_basis_labels_sha256
            != self.factor_basis_labels_sha256
            or product.factor_row_selection_sha256
            != self.factor_row_selection_sha256
            or product.template_bank_sha256 != self._template_bank_digest
            or product.factor_table_sha256 != self.factor_table_sha256
        ):
            self._invalidate(
                "epoch-vector provenance differs from the retention contract",
                V0P6IncompleteError,
            )
        if product is not None:
            product_key = (template_index, width_index)
            prior_product_sha256 = self._epoch_product_by_template_width.get(
                product_key
            )
            if prior_product_sha256 is not None and (
                prior_product_sha256 != product.product_sha256
            ):
                self._invalidate(
                    "retention subsets used different epoch-vector products",
                    V0P6IncompleteError,
                )
            self._epoch_product_by_template_width[product_key] = (
                product.product_sha256
            )
            cache_provenance = (
                product.cache_plan_sha256s,
                product.cache_payload_sha256s,
            )
            prior_cache_provenance = self._cache_provenance_by_width.get(
                width_index
            )
            if prior_cache_provenance is not None and (
                prior_cache_provenance != cache_provenance
            ):
                self._invalidate(
                    "retention templates used different cache provenance",
                    V0P6IncompleteError,
                )
            self._cache_provenance_by_width[width_index] = cache_provenance
        if mask_product is not None:
            if (
                product is None
                or mask_product.window_id != self.window_id
                or mask_product.scan_kind != self.scan_kind
                or mask_product.template_index != template_index
                or mask_product.proxy_grid_sha256
                != proxy_carrier_grid_sha256(self.grid)
                or mask_product.factor_basis_sha256
                != self.factor_basis_sha256
                or mask_product.factor_basis_labels_sha256
                != self.factor_basis_labels_sha256
                or mask_product.factor_row_selection_sha256
                != self.factor_row_selection_sha256
                or mask_product.template_bank_sha256
                != self._template_bank_digest
                or mask_product.factor_table_sha256
                != self.factor_table_sha256
                or mask_product.spectral_widths != tuple(self.spectral_widths)
                or mask_product.strong_snr != M37_RFI_STRONG_SNR
                or mask_product.other_epochs_below_snr
                != M37_RFI_OTHER_EPOCHS_BELOW_SNR
                or mask_product.guard_bins != M37_RFI_GUARD_Q_BINS
                or product.product_sha256
                not in mask_product.source_epoch_product_sha256s
            ):
                self._invalidate(
                    "mask-product provenance differs from retention",
                    V0P6IncompleteError,
                )
            prior_mask_sha256 = self._mask_product_by_template.get(
                template_index
            )
            if prior_mask_sha256 is not None and (
                prior_mask_sha256 != mask_product.product_sha256
            ):
                self._invalidate(
                    "retention hypotheses used different template masks",
                    V0P6IncompleteError,
                )
            self._mask_product_by_template[template_index] = (
                mask_product.product_sha256
            )
        score = stack_hypothesis(
            vectors,
            subset_tuple,
            minimum_active_epoch_snr=self.minimum_active_epoch_snr,
            stack_statistic=self.stack_statistic,
            exclusion_mask=mask_values,
        )
        if score.shape != (self.grid.score_bin_count,):
            raise V0P6ContractError("hypothesis score vector does not match q grid")
        eligible = np.flatnonzero(np.isfinite(score) & (score >= self.threshold))
        if len(self._records) + eligible.size > self.maximum_records:
            self._invalidate(
                "above-threshold retention exceeds the frozen per-window capacity"
            )
        additions: list[dict[str, Any]] = []
        for raw_frequency_index in eligible:
            frequency_index = int(raw_frequency_index)
            lattice_index = frequency_index - self.grid.score_half_bins
            record_key = {
                "window_id": self.window_id,
                "scan_kind": self.scan_kind,
                "template_index": template_index,
                "line_index": int(canonical_template["line_index"]),
                "spectral_width_index": width_index,
                "active_epochs_zero_based": list(subset_tuple),
                "q_offset_bin": lattice_index,
            }
            record = {
                "record_id": hashlib.sha256(
                    canonical_json_bytes(record_key)
                ).hexdigest(),
                "record_key": record_key,
                "window_id": self.window_id,
                "scan_kind": self.scan_kind,
                "snr": float(score[frequency_index]),
                "proxy_carrier_hz": float(
                    self.grid.score_hz[frequency_index]
                ),
                "proxy_carrier_mhz": float(
                    self.grid.score_hz[frequency_index] / 1e6
                ),
                "proxy_carrier_index": frequency_index,
                "proxy_carrier_lattice_index": lattice_index,
                "q_offset_bin": lattice_index,
                "spectral_width_channels": width_channels,
                "spectral_width_index": width_index,
                "template_index": template_index,
                "line_index": int(canonical_template["line_index"]),
                "line_coefficient": float(canonical_template["line_coefficient"]),
                "projected_scale": float(canonical_template["projected_scale"]),
                "phase_offset_cycles": float(canonical_template["phase_cycles"]),
                "active_epochs_zero_based": list(subset_tuple),
                "epoch_values_at_proxy_carrier": [
                    float(value) if math.isfinite(float(value)) else None
                    for value in vectors[:, frequency_index]
                ],
                "epoch_value_is_finite": [
                    bool(math.isfinite(float(value)))
                    for value in vectors[:, frequency_index]
                ],
                "operational_threshold_snr": self.threshold,
                "minimum_active_epoch_snr": self.minimum_active_epoch_snr,
                "stack_statistic": self.stack_statistic,
                "threshold_certificate_sha256": (
                    self.threshold_certificate.certificate_sha256
                ),
                "epoch_vector_product_sha256": (
                    None if product is None else product.product_sha256
                ),
                "mask_product_sha256": (
                    None
                    if mask_product is None
                    else mask_product.product_sha256
                ),
                "filter_coordinate": FILTER_COORDINATE,
                "member_disposition": "pending_physical_veto_evaluation",
            }
            encoded_size = len(canonical_json_bytes(record))
            if encoded_size > self.maximum_record_canonical_bytes:
                self._invalidate(
                    "retained record exceeds the frozen canonical byte cap"
                )
            additions.append(record)
        addition_bytes = sum(len(canonical_json_bytes(item)) for item in additions)
        if (
            self.maximum_evidence_canonical_bytes is not None
            and self._canonical_record_bytes + addition_bytes
            > self.maximum_evidence_canonical_bytes
        ):
            self._invalidate(
                "retained records exceed the frozen canonical evidence byte cap"
            )
        next_record_chain = _advance_retention_record_chain(
            self._record_chain_sha256, additions
        )
        self._records.extend(additions)
        self._canonical_record_bytes += addition_bytes
        self._hypotheses.add(key)
        self._score_cells += score.size
        self._record_chain_sha256 = next_record_chain
        self._checkpoint_replay_state()

    def finalize(self) -> list[dict[str, Any]]:
        if self._invalid:
            raise V0P6CapacityError("retention ledger is invalid")
        if self._sealed:
            raise V0P6ContractError("retention ledger is already sealed")
        self._require_contract()
        self._require_replay_state()
        if _advance_retention_record_chain(
            _RETENTION_RECORD_CHAIN_INITIAL_SHA256, self._records
        ) != self._record_chain_sha256:
            self._invalidate(
                "retained record bytes changed outside the ledger",
                V0P6IncompleteError,
            )
        if self._hypotheses != set(self._expected_hypothesis_keys):
            self._invalidate(
                "retention replay did not visit the exact hypothesis inventory",
                V0P6IncompleteError,
            )
        if self.require_epoch_vector_product:
            expected_product_keys = {
                (template_index, width_index)
                for template_index in range(len(self._bank_by_index))
                for width_index in range(len(self.spectral_widths))
            }
            if set(self._epoch_product_by_template_width) != expected_product_keys or (
                set(self._cache_provenance_by_width)
                != set(range(len(self.spectral_widths)))
            ):
                self._invalidate(
                    "retention epoch-vector provenance inventory is incomplete",
                    V0P6IncompleteError,
                )
        if self.require_mask_product and set(
            self._mask_product_by_template
        ) != set(range(len(self._bank_by_index))):
            self._invalidate(
                "retention mask-product inventory is incomplete",
                V0P6IncompleteError,
            )
        epoch_inventory_sha256 = _epoch_product_inventory_sha256(
            self._epoch_product_by_template_width
        )
        cache_inventory_sha256 = _cache_provenance_inventory_sha256(
            self._cache_provenance_by_width
        )
        mask_inventory_sha256 = _mask_product_inventory_sha256(
            self._mask_product_by_template
        )
        if self.scan_kind == "on":
            threshold_window_index = self.threshold_certificate.window_ids.index(
                self.window_id
            )
            if (
                epoch_inventory_sha256
                != self.threshold_certificate.calibration_epoch_product_inventory_sha256s[
                    threshold_window_index
                ]
                or cache_inventory_sha256
                != self.threshold_certificate.calibration_cache_provenance_inventory_sha256s[
                    threshold_window_index
                ]
                or mask_inventory_sha256
                != self.threshold_certificate.calibration_mask_product_inventory_sha256s[
                    threshold_window_index
                ]
            ):
                self._invalidate(
                    "retention replay provenance differs from calibration",
                    V0P6IncompleteError,
                )
        expected_score_cells = (
            len(self._expected_hypothesis_keys) * self.grid.score_bin_count
        )
        if self._score_cells != expected_score_cells:
            self._invalidate(
                "retention replay did not evaluate every expected score cell",
                V0P6IncompleteError,
            )
        self._records.sort(
            key=lambda item: (
                int(item["template_index"]),
                int(item["spectral_width_index"]),
                tuple(item["active_epochs_zero_based"]),
                int(item["proxy_carrier_index"]),
            )
        )
        identifiers = [item["record_id"] for item in self._records]
        if len(identifiers) != len(set(identifiers)):
            self._invalidate(
                "retention replay produced duplicate record identifiers",
                V0P6IncompleteError,
            )
        self._sealed = True
        certificate = {
                "window_id": self.window_id,
                "scan_kind": self.scan_kind,
                "axis_label": PROXY_CARRIER_AXIS_LABEL,
                "proxy_grid_sha256": proxy_carrier_grid_sha256(self.grid),
                "filter_coordinate": FILTER_COORDINATE,
                "threshold_comparison": "finite score >= operational threshold",
                "operational_threshold_snr": self.threshold,
                "minimum_active_epoch_snr": self.minimum_active_epoch_snr,
                "stack_statistic": self.stack_statistic,
                "require_epoch_vector_product": bool(
                    self.require_epoch_vector_product
                ),
                "require_mask_product": bool(self.require_mask_product),
                "epoch_count": self.epoch_count,
                "experiment_contract_sha256": (
                    self._experiment_contract_sha256
                ),
                "analysis_contract_sha256": self._analysis_contract_sha256,
                "threshold_certificate_sha256": (
                    self.threshold_certificate.certificate_sha256
                ),
                "ledger_contract_sha256": self._ledger_contract_sha256,
                "template_bank_sha256": self._template_bank_digest,
                "factor_basis_sha256": self.factor_basis_sha256,
                "factor_basis_labels_sha256": (
                    self.factor_basis_labels_sha256
                ),
                "scan_inventory_sha256": self.scan_inventory_sha256,
                "factor_row_selection_sha256": (
                    self.factor_row_selection_sha256
                ),
                "factor_table_sha256": self.factor_table_sha256,
                "spectral_widths": list(self.spectral_widths),
                "activity_subsets": [
                    list(item) for item in self.activity_subsets
                ],
                "expected_hypotheses": len(self._expected_hypothesis_keys),
                "expected_score_cells": expected_score_cells,
                "hypotheses_replayed": len(self._hypotheses),
                "score_cells_replayed": self._score_cells,
                "retained_record_count": len(self._records),
                "maximum_records": self.maximum_records,
                "maximum_record_canonical_bytes": (
                    self.maximum_record_canonical_bytes
                ),
                "canonical_record_bytes": self._canonical_record_bytes,
                "epoch_product_inventory_sha256": epoch_inventory_sha256,
                "cache_provenance_inventory_sha256": cache_inventory_sha256,
                "mask_product_inventory_sha256": mask_inventory_sha256,
                "maximum_evidence_canonical_bytes": (
                    self.maximum_evidence_canonical_bytes
                ),
                "truncation_permitted": False,
                "records_sha256": hashlib.sha256(
                    canonical_json_bytes(self._records)
                ).hexdigest(),
            }
        certificate["retention_certificate_sha256"] = hashlib.sha256(
            canonical_json_bytes(certificate)
        ).hexdigest()
        self._certificate_bytes = canonical_json_bytes(certificate)
        existing_attestation = _RETENTION_CERTIFICATE_ATTESTATIONS.get(
            certificate["retention_certificate_sha256"]
        )
        if existing_attestation is not None and (
            existing_attestation != self._certificate_bytes
        ):
            self._invalidate(
                "retention certificate digest collision",
                V0P6IncompleteError,
            )
        if existing_attestation is None and len(
            _RETENTION_CERTIFICATE_ATTESTATIONS
        ) >= _RETENTION_CERTIFICATE_ATTESTATION_CAP:
            self._invalidate(
                "retention certificate attestation capacity exceeded",
                V0P6CapacityError,
            )
        _RETENTION_CERTIFICATE_ATTESTATIONS[
            certificate["retention_certificate_sha256"]
        ] = self._certificate_bytes
        return json.loads(canonical_json_bytes(self._records))

    def certificate(self) -> dict[str, Any]:
        if not self._sealed or self._invalid:
            raise V0P6ContractError("retention ledger must be valid and sealed")
        assert self._certificate_bytes is not None
        return json.loads(self._certificate_bytes)


def make_m37_retention_ledger(
    window_id: str,
    scan_kind: str,
    threshold_certificate: ThresholdCertificate,
    template_bank: Sequence[dict[str, Any]],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
) -> ExhaustiveRetentionLedger:
    """Create a retention ledger with no configurable scientific M37 knobs."""
    normalized_kind = str(scan_kind).lower()
    if normalized_kind not in M37_FACTOR_ROW_SELECTION_SHA256S:
        raise V0P6ContractError("M37 retention scan kind must be ON or OFF")
    validate_threshold_certificate(threshold_certificate)
    validate_template_factor_table(
        factor_table,
        factor_basis,
        template_bank,
        expected_template_bank_sha256=M37_BANK_SHA256,
    )
    if (
        factor_basis.basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_basis.labels_sha256 != M37_FACTOR_BASIS_LABELS_SHA256
        or factor_table.factors.shape[0] != M37_TEMPLATE_COUNT
        or factor_table.template_bank_sha256 != M37_BANK_SHA256
        or factor_table.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_table_sha256(factor_table.factors)
        != factor_table.factor_table_sha256
    ):
        raise V0P6ContractError("factor table is not the sealed M37 table")
    if threshold_certificate.window_ids != M37_WINDOW_IDS:
        raise V0P6ContractError("threshold certificate is not the five-window M37 one")
    if (
        threshold_certificate.experiment_contract_sha256
        != M37_EXPERIMENT_CONTRACT_SHA256
        or threshold_certificate.factor_basis_sha256
        != M37_FACTOR_BASIS_SHA256
        or threshold_certificate.factor_basis_labels_sha256
        != M37_FACTOR_BASIS_LABELS_SHA256
        or threshold_certificate.scan_inventory_sha256
        != M37_SCAN_INVENTORY_SHA256
        or threshold_certificate.calibration_factor_row_selection_sha256
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or threshold_certificate.scramble_table_sha256s
        != M37_SCRAMBLE_TABLE_SHA256S
        or threshold_certificate.global_null_count != M37_SCRAMBLE_COUNT
        or threshold_certificate.reference_floor_snr
        != M37_THRESHOLD_REFERENCE_FLOOR_SNR
        or threshold_certificate.empirical_quantile != M37_THRESHOLD_QUANTILE
        or threshold_certificate.scientific_empirical_p_ceiling
        != M37_SCIENTIFIC_P_CEILING
    ):
        raise V0P6ContractError("threshold certificate violates the M37 contract")
    return ExhaustiveRetentionLedger(
        window_id=window_id,
        scan_kind=normalized_kind,
        grid=make_m37_proxy_carrier_grid(window_id),
        threshold_certificate=threshold_certificate,
        maximum_records=M37_MAXIMUM_RECORDS_PER_WINDOW,
        template_bank=template_bank,
        spectral_widths=M37_SPECTRAL_WIDTHS,
        activity_subsets=M37_ACTIVITY_SUBSETS,
        expected_template_bank_sha256=M37_BANK_SHA256,
        factor_basis_sha256=M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256=M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256=M37_SCAN_INVENTORY_SHA256,
        factor_row_selection_sha256=(
            M37_FACTOR_ROW_SELECTION_SHA256S[normalized_kind]
        ),
        factor_table_sha256=factor_table.factor_table_sha256,
        epoch_count=3,
        minimum_active_epoch_snr=M37_MINIMUM_ACTIVE_EPOCH_SNR,
        stack_statistic="minimum_epoch",
        require_epoch_vector_product=True,
        require_mask_product=True,
        maximum_record_canonical_bytes=M37_MAXIMUM_RECORD_CANONICAL_BYTES,
        maximum_evidence_canonical_bytes=M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES,
    )


def validate_retention_certificate(
    certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a certificate using a live or independently trusted receipt."""
    try:
        record = json.loads(canonical_json_bytes(dict(certificate)))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(
            "retention certificate is not canonical finite JSON"
        ) from error
    required = {
        "window_id",
        "scan_kind",
        "axis_label",
        "proxy_grid_sha256",
        "filter_coordinate",
        "threshold_comparison",
        "operational_threshold_snr",
        "minimum_active_epoch_snr",
        "stack_statistic",
        "require_epoch_vector_product",
        "require_mask_product",
        "threshold_certificate_sha256",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "ledger_contract_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "factor_row_selection_sha256",
        "factor_table_sha256",
        "spectral_widths",
        "activity_subsets",
        "epoch_count",
        "expected_hypotheses",
        "expected_score_cells",
        "hypotheses_replayed",
        "score_cells_replayed",
        "retained_record_count",
        "maximum_records",
        "maximum_record_canonical_bytes",
        "canonical_record_bytes",
        "epoch_product_inventory_sha256",
        "cache_provenance_inventory_sha256",
        "mask_product_inventory_sha256",
        "maximum_evidence_canonical_bytes",
        "truncation_permitted",
        "records_sha256",
        "retention_certificate_sha256",
    }
    if not required <= set(record):
        raise V0P6ContractError("retention certificate lacks required identities")
    observed_digest = _frozen_sha256(
        record.pop("retention_certificate_sha256"),
        "retention-certificate identity",
    )
    expected_digest = hashlib.sha256(canonical_json_bytes(record)).hexdigest()
    if observed_digest != expected_digest:
        raise V0P6ContractError("retention certificate SHA-256 changed")
    record["retention_certificate_sha256"] = observed_digest
    expected_digest = (
        None
        if expected_certificate_sha256 is None
        else _frozen_sha256(
            expected_certificate_sha256,
            "expected retention-certificate identity",
        )
    )
    live_attestation_matches = (
        _RETENTION_CERTIFICATE_ATTESTATIONS.get(observed_digest)
        == canonical_json_bytes(record)
    )
    trusted_digest_matches = expected_digest == observed_digest
    if not live_attestation_matches and not trusted_digest_matches:
        raise V0P6ContractError(
            "retention certificate lacks a live or trusted attestation"
        )
    if not str(record["window_id"]):
        raise V0P6ContractError("retention certificate has no window identity")
    if record["scan_kind"] not in {"on", "off"}:
        raise V0P6ContractError("retention certificate scan kind is invalid")
    if (
        record["axis_label"] != PROXY_CARRIER_AXIS_LABEL
        or record["filter_coordinate"] != FILTER_COORDINATE
        or record["threshold_comparison"]
        != "finite score >= operational threshold"
        or record["truncation_permitted"] is not False
    ):
        raise V0P6ContractError("retention certificate semantics changed")
    for name in (
        "proxy_grid_sha256",
        "threshold_certificate_sha256",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "ledger_contract_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "factor_row_selection_sha256",
        "factor_table_sha256",
        "records_sha256",
        "epoch_product_inventory_sha256",
        "cache_provenance_inventory_sha256",
        "mask_product_inventory_sha256",
    ):
        _frozen_sha256(record[name], name.replace("_", "-"))
    if factorized_analysis_contract_sha256(
        record["experiment_contract_sha256"],
        record["factor_basis_sha256"],
        record["factor_basis_labels_sha256"],
        record["scan_inventory_sha256"],
        record["factor_table_sha256"],
    ) != record["analysis_contract_sha256"]:
        raise V0P6ContractError(
            "retention factorized analysis contract changed"
        )
    count = _strict_int(record["retained_record_count"], "retained record count")
    maximum = _strict_int(record["maximum_records"], "retention record capacity")
    epoch_count = _strict_int(record["epoch_count"], "retention epoch count")
    if count < 0 or maximum < count or epoch_count < 1:
        raise V0P6ContractError("retention certificate counts are inconsistent")
    expected_hypotheses = _strict_int(
        record["expected_hypotheses"], "expected hypothesis count"
    )
    expected_cells = _strict_int(
        record["expected_score_cells"], "expected score-cell count"
    )
    if (
        expected_hypotheses < 1
        or expected_cells < 1
        or _strict_int(
            record["hypotheses_replayed"], "replayed hypothesis count"
        )
        != expected_hypotheses
        or _strict_int(record["score_cells_replayed"], "replayed score cells")
        != expected_cells
    ):
        raise V0P6IncompleteError("retention certificate replay is incomplete")
    _finite_json_number(
        record["operational_threshold_snr"],
        "retention certificate operational threshold",
    )
    minimum_active_epoch_snr = record["minimum_active_epoch_snr"]
    if minimum_active_epoch_snr is not None:
        _finite_json_number(
            minimum_active_epoch_snr,
            "retention certificate active-epoch S/N floor",
        )
    _scoring_contract(
        minimum_active_epoch_snr, record["stack_statistic"]
    )
    if not isinstance(record["require_epoch_vector_product"], bool):
        raise V0P6ContractError(
            "retention epoch-vector provenance flag is invalid"
        )
    if not isinstance(record["require_mask_product"], bool):
        raise V0P6ContractError("retention mask-product flag is invalid")
    widths = _strict_widths(record["spectral_widths"])
    subsets = canonical_activity_subsets(record["activity_subsets"])
    if max(epoch for subset in subsets for epoch in subset) >= epoch_count:
        raise V0P6ContractError("retention certificate subset is out of range")
    if _strict_int(
        record["maximum_record_canonical_bytes"],
        "canonical record-byte capacity",
    ) < 1:
        raise V0P6ContractError("retention record-byte capacity is invalid")
    evidence_cap = record["maximum_evidence_canonical_bytes"]
    if evidence_cap is not None and _strict_int(
        evidence_cap, "canonical evidence-byte capacity"
    ) < 1:
        raise V0P6ContractError("retention evidence-byte capacity is invalid")
    canonical_record_bytes = _strict_int(
        record["canonical_record_bytes"], "canonical retained-record bytes"
    )
    if canonical_record_bytes < 0 or (
        evidence_cap is not None
        and canonical_record_bytes > _strict_int(
            evidence_cap, "canonical evidence-byte capacity"
        )
    ):
        raise V0P6ContractError("retention canonical byte count is invalid")
    record["spectral_widths"] = list(widths)
    record["activity_subsets"] = [list(item) for item in subsets]
    return record


def _retention_record_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _strict_int(record["template_index"], "template index"),
        _strict_int(record["spectral_width_index"], "spectral-width index"),
        tuple(
            _strict_int(item, "activity epoch")
            for item in record["active_epochs_zero_based"]
        ),
        _strict_int(record["proxy_carrier_index"], "proxy-carrier index"),
    )


def _validate_retained_record_json_numeric_types(
    record: Mapping[str, Any],
) -> None:
    """Reject coercible non-JSON numerics in a persisted retention record."""
    for name in (
        "proxy_carrier_index",
        "proxy_carrier_lattice_index",
        "q_offset_bin",
        "spectral_width_channels",
        "spectral_width_index",
        "template_index",
        "line_index",
    ):
        _strict_int(record[name], name.replace("_", " "))
    canonical_activity_subsets((record["active_epochs_zero_based"],))
    for name in (
        "snr",
        "proxy_carrier_hz",
        "proxy_carrier_mhz",
        "line_coefficient",
        "projected_scale",
        "phase_offset_cycles",
        "operational_threshold_snr",
    ):
        _finite_json_number(record[name], name.replace("_", " "))
    minimum_active_epoch_snr = record["minimum_active_epoch_snr"]
    if minimum_active_epoch_snr is not None:
        _finite_json_number(
            minimum_active_epoch_snr, "minimum active-epoch S/N"
        )
    epoch_values = record["epoch_values_at_proxy_carrier"]
    if not isinstance(epoch_values, list):
        raise V0P6ContractError("retained epoch values must be a JSON array")
    for value in epoch_values:
        if value is not None:
            _finite_json_number(value, "retained epoch value")

    record_key = record["record_key"]
    if not isinstance(record_key, Mapping):
        raise V0P6ContractError("retained record key must be an object")
    for name in (
        "template_index",
        "line_index",
        "spectral_width_index",
        "q_offset_bin",
    ):
        _strict_int(record_key[name], f"record-key {name.replace('_', ' ')}")
    canonical_activity_subsets((record_key["active_epochs_zero_based"],))


def _validated_retained_records(
    records: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    grid: ProxyCarrierGrid,
    *,
    expected_kind: str,
    expected_template_count: int,
    template_bank: Sequence[Mapping[str, Any]] | None = None,
    expected_certificate_sha256: str | None = None,
) -> list[dict[str, Any]]:
    """Validate a complete retained-record product and its exact q identities."""
    cert = validate_retention_certificate(
        certificate,
        expected_certificate_sha256=expected_certificate_sha256,
    )
    expected_kind = str(expected_kind).lower()
    expected_template_count = _strict_int(
        expected_template_count, "template count"
    )
    if cert["scan_kind"] != expected_kind:
        raise V0P6ContractError("retention product has the wrong scan kind")
    if proxy_carrier_grid_sha256(grid) != cert["proxy_grid_sha256"]:
        raise V0P6ContractError("retention product has the wrong proxy grid")
    try:
        detached = json.loads(canonical_json_bytes(list(records)))
        detached.sort(key=_retention_record_sort_key)
    except (KeyError, TypeError, ValueError, V0P6ContractError) as error:
        raise V0P6ContractError("retained record has a malformed identity") from error
    if len(detached) != _strict_int(
        cert["retained_record_count"], "retained record count"
    ):
        raise V0P6IncompleteError("retained record count differs from certificate")
    if hashlib.sha256(canonical_json_bytes(detached)).hexdigest() != cert[
        "records_sha256"
    ]:
        raise V0P6IncompleteError("retained record bytes differ from certificate")
    if sum(len(canonical_json_bytes(item)) for item in detached) != _strict_int(
        cert["canonical_record_bytes"], "canonical retained-record bytes"
    ):
        raise V0P6IncompleteError("retained record byte count differs from certificate")

    widths = tuple(_strict_widths(cert["spectral_widths"]))
    subsets = canonical_activity_subsets(cert["activity_subsets"])
    epoch_count = _strict_int(cert["epoch_count"], "retention epoch count")
    expected_hypotheses = expected_template_count * len(widths) * len(subsets)
    expected_score_cells = expected_hypotheses * grid.score_bin_count
    if (
        _strict_int(cert["expected_hypotheses"], "expected hypothesis count")
        != expected_hypotheses
        or _strict_int(cert["hypotheses_replayed"], "replayed hypothesis count")
        != expected_hypotheses
        or _strict_int(cert["expected_score_cells"], "expected score-cell count")
        != expected_score_cells
        or _strict_int(cert["score_cells_replayed"], "replayed score-cell count")
        != expected_score_cells
    ):
        raise V0P6IncompleteError(
            "retention certificate does not cover the reconstructed inventory"
        )
    threshold = float(cert["operational_threshold_snr"])
    seen_ids: set[str] = set()
    seen_scientific_keys: set[
        tuple[int, int, tuple[int, ...], int]
    ] = set()
    canonical_bank: tuple[dict[str, Any], ...] | None = None
    if template_bank is not None:
        try:
            detached_bank = json.loads(
                canonical_json_bytes(list(template_bank))
            )
        except (TypeError, ValueError) as error:
            raise V0P6ContractError("retention validation bank is invalid") from error
        if (
            len(detached_bank) != expected_template_count
            or template_bank_sha256(detached_bank) != cert["template_bank_sha256"]
        ):
            raise V0P6ContractError(
                "retention validation bank differs from its certificate"
            )
        canonical_bank = tuple(detached_bank)
    record_byte_cap = _strict_int(
        cert["maximum_record_canonical_bytes"],
        "canonical record-byte capacity",
    )
    for record in detached:
        try:
            _validate_retained_record_json_numeric_types(record)
        except (KeyError, TypeError, V0P6ContractError) as error:
            raise V0P6ContractError(
                "retained record has invalid JSON numeric types"
            ) from error
        if len(canonical_json_bytes(record)) > record_byte_cap:
            raise V0P6CapacityError(
                "retained record exceeds its canonical byte capacity"
            )
        template_index = _strict_int(record["template_index"], "template index")
        width_index = _strict_int(
            record["spectral_width_index"], "spectral-width index"
        )
        proxy_index = _strict_int(
            record["proxy_carrier_index"], "proxy-carrier index"
        )
        subset = canonical_activity_subsets(
            (record["active_epochs_zero_based"],)
        )[0]
        if not 0 <= template_index < expected_template_count:
            raise V0P6ContractError("retained template index is out of range")
        if not 0 <= width_index < len(widths) or (
            _strict_int(record["spectral_width_channels"], "spectral width")
            != widths[width_index]
        ):
            raise V0P6ContractError("retained spectral-width identity changed")
        if subset not in subsets or max(subset) >= epoch_count:
            raise V0P6ContractError("retained activity-subset identity changed")
        if not 0 <= proxy_index < grid.score_bin_count:
            raise V0P6ContractError("retained proxy-carrier index is out of range")
        lattice_index = proxy_index - grid.score_half_bins
        q_hz = float(grid.score_hz[proxy_index])
        if (
            str(record["window_id"]) != str(cert["window_id"])
            or str(record["scan_kind"]).lower() != expected_kind
            or _strict_int(record["proxy_carrier_lattice_index"], "q index")
            != lattice_index
            or _strict_int(record["q_offset_bin"], "q offset") != lattice_index
            or float(record["proxy_carrier_hz"]) != q_hz
            or float(record["proxy_carrier_mhz"]) != q_hz / 1e6
        ):
            raise V0P6ContractError("retained proxy-carrier identity changed")
        score = float(record["snr"])
        if not math.isfinite(score) or score < threshold:
            raise V0P6ContractError("retained score violates its threshold")
        if (
            float(record["operational_threshold_snr"]) != threshold
            or record["minimum_active_epoch_snr"]
            != cert["minimum_active_epoch_snr"]
            or record["stack_statistic"] != cert["stack_statistic"]
            or record["threshold_certificate_sha256"]
            != cert["threshold_certificate_sha256"]
            or record["filter_coordinate"] != FILTER_COORDINATE
            or record["member_disposition"]
            != "pending_physical_veto_evaluation"
        ):
            raise V0P6ContractError("retained scoring identity changed")
        product_digest = record["epoch_vector_product_sha256"]
        if cert["require_epoch_vector_product"]:
            _frozen_sha256(product_digest, "epoch-vector product identity")
        elif product_digest is not None:
            _frozen_sha256(product_digest, "epoch-vector product identity")
        mask_digest = record["mask_product_sha256"]
        if cert["require_mask_product"]:
            _frozen_sha256(mask_digest, "mask-product identity")
        elif mask_digest is not None:
            _frozen_sha256(mask_digest, "mask-product identity")
        if len(record["epoch_values_at_proxy_carrier"]) != epoch_count or len(
            record["epoch_value_is_finite"]
        ) != epoch_count:
            raise V0P6ContractError("retained epoch evidence is incomplete")
        evidence = np.full((epoch_count, 1), np.nan, dtype=np.float32)
        for epoch_index, (value, finite_flag) in enumerate(
            zip(
                record["epoch_values_at_proxy_carrier"],
                record["epoch_value_is_finite"],
                strict=True,
            )
        ):
            if not isinstance(finite_flag, bool):
                raise V0P6ContractError(
                    "retained epoch finite flag is not boolean"
                )
            if finite_flag:
                if isinstance(value, bool) or value is None or not math.isfinite(
                    float(value)
                ):
                    raise V0P6ContractError(
                        "retained epoch value/finite flag is inconsistent"
                    )
                evidence[epoch_index, 0] = np.float32(value)
            elif value is not None:
                raise V0P6ContractError(
                    "retained non-finite epoch evidence must be null"
                )
        reproduced_score = float(
            stack_hypothesis(
                evidence,
                subset,
                minimum_active_epoch_snr=cert["minimum_active_epoch_snr"],
                stack_statistic=cert["stack_statistic"],
                exclusion_mask=None,
            )[0]
        )
        if reproduced_score != score:
            raise V0P6ContractError(
                "retained score does not reproduce from its epoch evidence"
            )
        if canonical_bank is not None:
            canonical_template = canonical_bank[template_index]
            if (
                _strict_int(record["line_index"], "line index")
                != _strict_int(canonical_template["line_index"], "line index")
                or float(record["line_coefficient"])
                != float(canonical_template["line_coefficient"])
                or float(record["projected_scale"])
                != float(canonical_template["projected_scale"])
                or float(record["phase_offset_cycles"])
                != float(canonical_template["phase_cycles"])
            ):
                raise V0P6ContractError(
                    "retained template metadata differs from the frozen bank"
                )
        record_key = {
            "window_id": str(cert["window_id"]),
            "scan_kind": expected_kind,
            "template_index": template_index,
            "line_index": _strict_int(record["line_index"], "line index"),
            "spectral_width_index": width_index,
            "active_epochs_zero_based": list(subset),
            "q_offset_bin": lattice_index,
        }
        if canonical_json_bytes(record["record_key"]) != canonical_json_bytes(
            record_key
        ):
            raise V0P6ContractError("retained record key changed")
        record_id = _frozen_sha256(record["record_id"], "retained record identity")
        if record_id != hashlib.sha256(canonical_json_bytes(record_key)).hexdigest():
            raise V0P6ContractError("retained record ID does not match its key")
        if record_id in seen_ids:
            raise V0P6IncompleteError("retained product contains duplicate record IDs")
        seen_ids.add(record_id)
        scientific_key = (template_index, width_index, subset, lattice_index)
        if scientific_key in seen_scientific_keys:
            raise V0P6IncompleteError(
                "retained product contains duplicate scientific keys"
            )
        seen_scientific_keys.add(scientific_key)
    return detached


def _off_witness(
    record: Mapping[str, Any],
    distance_hz: float,
) -> dict[str, Any]:
    return {
        "record_id": str(record["record_id"]),
        "window_id": str(record["window_id"]),
        "snr": float(record["snr"]),
        "template_index": _strict_int(record["template_index"], "template index"),
        "spectral_width_index": _strict_int(
            record["spectral_width_index"], "spectral-width index"
        ),
        "active_epochs_zero_based": [
            _strict_int(item, "activity epoch")
            for item in record["active_epochs_zero_based"]
        ],
        "proxy_carrier_index": _strict_int(
            record["proxy_carrier_index"], "proxy-carrier index"
        ),
        "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
        "maximum_track_distance_hz": float(distance_hz),
    }


def match_retained_off_tracks(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    off_records: Sequence[Mapping[str, Any]],
    off_certificate: Mapping[str, Any],
    grid: ProxyCarrierGrid,
    off_factor_matrix: np.ndarray,
    *,
    window_order: Sequence[str],
    tolerance_hz: float,
    maximum_bucket_entries: int,
    maximum_exact_candidate_visits: int,
    template_bank: Sequence[Mapping[str, Any]] | None = None,
    expected_on_certificate_sha256: str | None = None,
    expected_off_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Exhaustively classify retained ON members against retained OFF tracks."""
    on_cert = validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    off_cert = validate_retention_certificate(
        off_certificate,
        expected_certificate_sha256=expected_off_certificate_sha256,
    )
    comparable_fields = (
        "window_id",
        "proxy_grid_sha256",
        "threshold_certificate_sha256",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "factor_table_sha256",
        "spectral_widths",
        "activity_subsets",
        "epoch_count",
        "operational_threshold_snr",
        "minimum_active_epoch_snr",
        "stack_statistic",
        "require_epoch_vector_product",
        "require_mask_product",
    )
    if any(on_cert[name] != off_cert[name] for name in comparable_fields):
        raise V0P6ContractError("ON and OFF retention contracts differ")
    windows = tuple(str(item) for item in window_order)
    if not windows or len(set(windows)) != len(windows):
        raise V0P6ContractError("OFF matcher window order is invalid")
    try:
        window_index = windows.index(str(on_cert["window_id"]))
    except ValueError as error:
        raise V0P6ContractError("retention window is absent from matcher order") from error
    tolerance_hz = float(tolerance_hz)
    maximum_bucket_entries = _strict_int(
        maximum_bucket_entries, "OFF bucket-entry capacity"
    )
    maximum_exact_candidate_visits = _strict_int(
        maximum_exact_candidate_visits, "OFF candidate-visit capacity"
    )
    if not math.isfinite(tolerance_hz) or tolerance_hz <= 0.0:
        raise V0P6ContractError("OFF track tolerance must be finite and positive")
    if maximum_bucket_entries < 1 or maximum_exact_candidate_visits < 1:
        raise V0P6ContractError("OFF matcher capacities must be positive")

    factors = np.asarray(off_factor_matrix)
    if factors.ndim != 2 or not np.issubdtype(factors.dtype, np.floating):
        raise V0P6ContractError("OFF factors must be a floating matrix")
    if factors.shape[0] < 1 or factors.shape[1] < 1:
        raise V0P6ContractError("OFF factor matrix must be non-empty")
    if not np.all(np.isfinite(factors)) or np.any(factors <= 0.0):
        raise V0P6ContractError("OFF factors must be finite and positive")
    factors = np.array(factors, dtype=np.float64, order="C", copy=True)
    factors.setflags(write=False)
    factor_digest = factor_table_sha256(factors)
    template_count = int(factors.shape[0])
    on_items = _validated_retained_records(
        on_records,
        on_cert,
        grid,
        expected_kind="on",
        expected_template_count=template_count,
        template_bank=template_bank,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    off_items = _validated_retained_records(
        off_records,
        off_cert,
        grid,
        expected_kind="off",
        expected_template_count=template_count,
        template_bank=template_bank,
        expected_certificate_sha256=expected_off_certificate_sha256,
    )

    subsets = canonical_activity_subsets(on_cert["activity_subsets"])
    subset_ordinals = {subset: index for index, subset in enumerate(subsets)}

    def stable_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
        subset = tuple(int(item) for item in record["active_epochs_zero_based"])
        return (
            window_index,
            int(record["template_index"]),
            int(record["spectral_width_index"]),
            subset_ordinals[subset],
            int(record["proxy_carrier_index"]),
            str(record["record_id"]),
        )

    def witness_priority(
        item: tuple[dict[str, Any], float],
    ) -> tuple[Any, ...]:
        record, _ = item
        return (-float(record["snr"]), stable_key(record))

    buckets: list[list[tuple[float, tuple[Any, ...], dict[str, Any], np.ndarray]]]
    buckets = [[] for _ in range(template_count)]
    exact_by_key: dict[tuple[Any, ...], tuple[dict[str, Any], np.ndarray]] = {}
    for record in off_items:
        template_index = int(record["template_index"])
        q_hz = np.float64(record["proxy_carrier_hz"])
        track = np.asarray(q_hz * factors[template_index], dtype=np.float64)
        if not np.all(np.isfinite(track)):
            raise V0P6ContractError("OFF record produced a non-finite track")
        buckets[template_index].append(
            (float(track[0]), stable_key(record), record, track)
        )
        exact_key = (
            template_index,
            int(record["proxy_carrier_index"]),
            int(record["spectral_width_index"]),
            tuple(record["active_epochs_zero_based"]),
        )
        if exact_key in exact_by_key:
            raise V0P6IncompleteError(
                "OFF retention contains a duplicate same-hypothesis key"
            )
        exact_by_key[exact_key] = (record, track)
    maximum_observed_bucket_entries = max(
        (len(bucket) for bucket in buckets), default=0
    )
    if maximum_observed_bucket_entries > maximum_bucket_entries:
        raise V0P6CapacityError("OFF track bucket-entry capacity exceeded")
    indexed_buckets: list[
        tuple[
            tuple[tuple[float, tuple[Any, ...], dict[str, Any], np.ndarray], ...],
            np.ndarray,
        ]
    ] = []
    for bucket in buckets:
        bucket.sort(key=lambda item: (item[0], item[1]))
        anchors = np.fromiter(
            (item[0] for item in bucket), dtype=np.float64, count=len(bucket)
        )
        anchors.setflags(write=False)
        indexed_buckets.append((tuple(bucket), anchors))

    exact_candidate_visits = 0
    annotated: list[dict[str, Any]] = []
    disposition_counts = {
        "rfi_veto_matched_off_same_hypothesis": 0,
        "rfi_veto_local_off_track": 0,
        "pending_receiver_alias_evaluation": 0,
    }
    maximum_anchor_roundoff_guard_hz = 0.0
    for on_record in on_items:
        on_template = int(on_record["template_index"])
        on_q_hz = np.float64(on_record["proxy_carrier_hz"])
        on_track = np.asarray(on_q_hz * factors[on_template], dtype=np.float64)
        if not np.all(np.isfinite(on_track)):
            raise V0P6ContractError("ON record produced a non-finite OFF-time track")
        anchor_scale = max(
            abs(float(on_track[0])), abs(tolerance_hz), 1.0
        )
        anchor_guard = 4.0 * float(np.spacing(np.float64(anchor_scale)))
        if not math.isfinite(anchor_guard):
            raise V0P6ContractError("OFF anchor roundoff guard is non-finite")
        maximum_anchor_roundoff_guard_hz = max(
            maximum_anchor_roundoff_guard_hz, anchor_guard
        )
        lower = float(
            np.nextafter(
                on_track[0] - np.float64(tolerance_hz) - anchor_guard,
                -np.inf,
            )
        )
        upper = float(
            np.nextafter(
                on_track[0] + np.float64(tolerance_hz) + anchor_guard,
                np.inf,
            )
        )
        local_matches: list[tuple[dict[str, Any], float]] = []
        on_subset = tuple(int(item) for item in on_record["active_epochs_zero_based"])
        exact_key = (
            on_template,
            int(on_record["proxy_carrier_index"]),
            int(on_record["spectral_width_index"]),
            on_subset,
        )
        exact_matches: list[tuple[dict[str, Any], float]] = []
        if exact_key in exact_by_key:
            exact_record, exact_track = exact_by_key[exact_key]
            exact_distance = float(np.max(np.abs(on_track - exact_track)))
            if not math.isfinite(exact_distance):
                raise V0P6ContractError(
                    "same-hypothesis OFF distance became non-finite"
                )
            exact_matches.append((exact_record, exact_distance))
        for bucket, anchors in indexed_buckets:
            if not bucket:
                continue
            start = int(np.searchsorted(anchors, lower, side="left"))
            stop = int(np.searchsorted(anchors, upper, side="right"))
            for _, _, off_record, off_track in bucket[start:stop]:
                exact_candidate_visits += 1
                if exact_candidate_visits > maximum_exact_candidate_visits:
                    raise V0P6CapacityError(
                        "OFF exact candidate-visit capacity exceeded"
                    )
                delta = np.abs(on_track - off_track)
                if not np.all(np.isfinite(delta)):
                    raise V0P6ContractError("OFF track distance became non-finite")
                distance = float(np.max(delta))
                if distance <= tolerance_hz:
                    match = (off_record, distance)
                    local_matches.append(match)
        local_matches.sort(key=witness_priority)
        exact_matches.sort(key=witness_priority)
        if exact_matches:
            disposition = "rfi_veto_matched_off_same_hypothesis"
        elif local_matches:
            disposition = "rfi_veto_local_off_track"
        else:
            disposition = "pending_receiver_alias_evaluation"
        disposition_counts[disposition] += 1
        result_record = json.loads(canonical_json_bytes(on_record))
        result_record["off_track_evidence"] = {
            "contract": "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz",
            "tolerance_hz": tolerance_hz,
            "off_integration_count": int(factors.shape[1]),
            "off_factor_matrix_sha256": factor_digest,
            "same_hypothesis": {
                "matched": bool(exact_matches),
                "matched_off_record_count": len(exact_matches),
                "best_off_witness": (
                    None
                    if not exact_matches
                    else _off_witness(*exact_matches[0])
                ),
            },
            "local_track": {
                "matched": bool(local_matches),
                "matched_off_record_count": len(local_matches),
                "best_off_witness": (
                    None
                    if not local_matches
                    else _off_witness(*local_matches[0])
                ),
            },
        }
        result_record["member_disposition"] = disposition
        annotated.append(result_record)

    record_cap = _strict_int(
        on_cert["maximum_record_canonical_bytes"],
        "canonical record-byte capacity",
    )
    encoded_sizes = [len(canonical_json_bytes(item)) for item in annotated]
    if any(size > record_cap for size in encoded_sizes):
        raise V0P6CapacityError("OFF annotation exceeds the record-byte capacity")
    evidence_cap = on_cert["maximum_evidence_canonical_bytes"]
    if evidence_cap is not None and sum(encoded_sizes) > _strict_int(
        evidence_cap, "canonical evidence-byte capacity"
    ):
        raise V0P6CapacityError("OFF annotations exceed the evidence-byte capacity")
    annotated.sort(key=_retention_record_sort_key)
    result_sha = hashlib.sha256(canonical_json_bytes(annotated)).hexdigest()
    result_certificate = {
        "window_id": str(on_cert["window_id"]),
        "contract": "literal maximum OFF-time track distance in Hz",
        "inclusive_comparison": "maximum_track_distance_hz <= tolerance_hz",
        "same_hypothesis_key_fields": [
            "template_index",
            "proxy_carrier_index",
            "spectral_width_index",
            "active_epochs_zero_based",
        ],
        "local_track_comparison_scope": "all retained OFF templates",
        "disposition_precedence": [
            "rfi_veto_matched_off_same_hypothesis",
            "rfi_veto_local_off_track",
            "pending_receiver_alias_evaluation",
        ],
        "best_witness_order": [
            "snr descending",
            "window_order index ascending",
            "template_index ascending",
            "spectral_width_index ascending",
            "activity_subset ordinal ascending",
            "proxy_carrier_index ascending",
            "record_id ascending",
        ],
        "annotated_record_order": [
            "template_index ascending",
            "spectral_width_index ascending",
            "active_epochs_zero_based lexicographic ascending",
            "proxy_carrier_index ascending",
        ],
        "tolerance_hz": tolerance_hz,
        "off_integration_count": int(factors.shape[1]),
        "off_factor_matrix_sha256": factor_digest,
        "factor_basis_sha256": on_cert["factor_basis_sha256"],
        "factor_basis_labels_sha256": on_cert[
            "factor_basis_labels_sha256"
        ],
        "scan_inventory_sha256": on_cert["scan_inventory_sha256"],
        "on_factor_row_selection_sha256": on_cert[
            "factor_row_selection_sha256"
        ],
        "off_factor_row_selection_sha256": off_cert[
            "factor_row_selection_sha256"
        ],
        "factor_table_sha256": on_cert["factor_table_sha256"],
        "on_retention_certificate_sha256": on_cert[
            "retention_certificate_sha256"
        ],
        "off_retention_certificate_sha256": off_cert[
            "retention_certificate_sha256"
        ],
        "on_records_sha256": on_cert["records_sha256"],
        "off_records_sha256": off_cert["records_sha256"],
        "on_record_count": len(on_items),
        "off_record_count": len(off_items),
        "indexed_bucket_count": sum(bool(bucket) for bucket in buckets),
        "maximum_bucket_entries_observed": maximum_observed_bucket_entries,
        "maximum_bucket_entries": maximum_bucket_entries,
        "exact_candidate_visits": exact_candidate_visits,
        "maximum_exact_candidate_visits": maximum_exact_candidate_visits,
        "anchor_pruning_roundoff_guard": (
            "4 * spacing(max(abs(on_anchor_hz), tolerance_hz, 1.0))"
        ),
        "maximum_anchor_pruning_roundoff_guard_hz": (
            maximum_anchor_roundoff_guard_hz
        ),
        "all_on_records_annotated_exactly_once": True,
        "disposition_counts": disposition_counts,
        "annotated_records_sha256": result_sha,
        "maximum_annotated_record_canonical_bytes": record_cap,
        "maximum_annotated_evidence_canonical_bytes": evidence_cap,
        "annotated_evidence_canonical_bytes": sum(encoded_sizes),
        "truncation_permitted": False,
    }
    result_certificate["off_match_certificate_sha256"] = hashlib.sha256(
        canonical_json_bytes(result_certificate)
    ).hexdigest()
    result = {
        "records": json.loads(canonical_json_bytes(annotated)),
        "certificate": json.loads(canonical_json_bytes(result_certificate)),
    }
    validate_off_match_result(result["records"], result["certificate"])
    return result


def validate_off_match_result(
    records: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a persisted OFF-match result and its disposition semantics."""
    try:
        detached = json.loads(canonical_json_bytes(list(records)))
        cert = json.loads(canonical_json_bytes(dict(certificate)))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(
            "OFF-match result is not canonical finite JSON"
        ) from error
    if not isinstance(detached, list) or not all(
        isinstance(item, dict) for item in detached
    ):
        raise V0P6ContractError("OFF-match records must be a list of objects")
    required_certificate_fields = {
        "window_id",
        "contract",
        "inclusive_comparison",
        "same_hypothesis_key_fields",
        "local_track_comparison_scope",
        "disposition_precedence",
        "best_witness_order",
        "annotated_record_order",
        "tolerance_hz",
        "off_integration_count",
        "off_factor_matrix_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "off_factor_row_selection_sha256",
        "factor_table_sha256",
        "on_retention_certificate_sha256",
        "off_retention_certificate_sha256",
        "on_records_sha256",
        "off_records_sha256",
        "on_record_count",
        "off_record_count",
        "indexed_bucket_count",
        "maximum_bucket_entries_observed",
        "maximum_bucket_entries",
        "exact_candidate_visits",
        "maximum_exact_candidate_visits",
        "anchor_pruning_roundoff_guard",
        "maximum_anchor_pruning_roundoff_guard_hz",
        "all_on_records_annotated_exactly_once",
        "disposition_counts",
        "annotated_records_sha256",
        "maximum_annotated_record_canonical_bytes",
        "maximum_annotated_evidence_canonical_bytes",
        "annotated_evidence_canonical_bytes",
        "truncation_permitted",
        "off_match_certificate_sha256",
    }
    if frozenset(cert) != frozenset(required_certificate_fields):
        raise V0P6ContractError(
            "OFF-match certificate fields do not match the schema"
        )
    observed_certificate_sha256 = _frozen_sha256(
        cert.pop("off_match_certificate_sha256"),
        "OFF-match certificate identity",
    )
    calculated_certificate_sha256 = hashlib.sha256(
        canonical_json_bytes(cert)
    ).hexdigest()
    if observed_certificate_sha256 != calculated_certificate_sha256:
        raise V0P6IncompleteError("OFF-match certificate SHA-256 changed")
    if expected_certificate_sha256 is not None and (
        observed_certificate_sha256
        != _frozen_sha256(
            expected_certificate_sha256,
            "expected OFF-match certificate identity",
        )
    ):
        raise V0P6ContractError(
            "OFF-match certificate differs from its independently supplied identity"
        )
    cert["off_match_certificate_sha256"] = observed_certificate_sha256
    for name in (
        "off_factor_matrix_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "off_factor_row_selection_sha256",
        "factor_table_sha256",
        "on_retention_certificate_sha256",
        "off_retention_certificate_sha256",
        "on_records_sha256",
        "off_records_sha256",
        "annotated_records_sha256",
    ):
        _frozen_sha256(cert[name], name.replace("_", "-"))
    expected_same_key = [
        "template_index",
        "proxy_carrier_index",
        "spectral_width_index",
        "active_epochs_zero_based",
    ]
    expected_precedence = [
        "rfi_veto_matched_off_same_hypothesis",
        "rfi_veto_local_off_track",
        "pending_receiver_alias_evaluation",
    ]
    expected_witness_order = [
        "snr descending",
        "window_order index ascending",
        "template_index ascending",
        "spectral_width_index ascending",
        "activity_subset ordinal ascending",
        "proxy_carrier_index ascending",
        "record_id ascending",
    ]
    expected_record_order = [
        "template_index ascending",
        "spectral_width_index ascending",
        "active_epochs_zero_based lexicographic ascending",
        "proxy_carrier_index ascending",
    ]
    tolerance_hz = _finite_json_number(
        cert["tolerance_hz"], "OFF-match tolerance"
    )
    maximum_guard = _finite_json_number(
        cert["maximum_anchor_pruning_roundoff_guard_hz"],
        "OFF-match maximum anchor-pruning roundoff guard",
    )
    if (
        tolerance_hz <= 0.0
        or maximum_guard < 0.0
        or cert["contract"]
        != "literal maximum OFF-time track distance in Hz"
        or cert["inclusive_comparison"]
        != "maximum_track_distance_hz <= tolerance_hz"
        or cert["same_hypothesis_key_fields"] != expected_same_key
        or cert["local_track_comparison_scope"]
        != "all retained OFF templates"
        or cert["disposition_precedence"] != expected_precedence
        or cert["best_witness_order"] != expected_witness_order
        or cert["annotated_record_order"] != expected_record_order
        or cert["anchor_pruning_roundoff_guard"]
        != "4 * spacing(max(abs(on_anchor_hz), tolerance_hz, 1.0))"
        or cert["all_on_records_annotated_exactly_once"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise V0P6ContractError("OFF-match certificate semantics changed")
    on_count = _strict_int(cert["on_record_count"], "ON record count")
    off_count = _strict_int(cert["off_record_count"], "OFF record count")
    bucket_count = _strict_int(
        cert["indexed_bucket_count"], "OFF indexed-bucket count"
    )
    bucket_observed = _strict_int(
        cert["maximum_bucket_entries_observed"],
        "OFF observed bucket entries",
    )
    bucket_cap = _strict_int(
        cert["maximum_bucket_entries"], "OFF bucket-entry capacity"
    )
    candidate_visits = _strict_int(
        cert["exact_candidate_visits"], "OFF candidate visits"
    )
    candidate_visit_cap = _strict_int(
        cert["maximum_exact_candidate_visits"],
        "OFF candidate-visit capacity",
    )
    integration_count = _strict_int(
        cert["off_integration_count"], "OFF integration count"
    )
    record_byte_cap = _strict_int(
        cert["maximum_annotated_record_canonical_bytes"],
        "OFF annotated record-byte capacity",
    )
    evidence_byte_cap = cert["maximum_annotated_evidence_canonical_bytes"]
    if evidence_byte_cap is not None:
        evidence_byte_cap = _strict_int(
            evidence_byte_cap, "OFF annotated evidence-byte capacity"
        )
    if (
        on_count != len(detached)
        or min(on_count, off_count, bucket_count, bucket_observed, candidate_visits)
        < 0
        or min(bucket_cap, candidate_visit_cap, integration_count, record_byte_cap)
        < 1
        or bucket_count > _strict_int(
            cert["off_record_count"], "OFF record count"
        )
        or bucket_observed > bucket_cap
        or candidate_visits > candidate_visit_cap
        or (evidence_byte_cap is not None and evidence_byte_cap < 1)
    ):
        raise V0P6IncompleteError("OFF-match certificate counts are inconsistent")
    detached.sort(key=_retention_record_sort_key)
    if hashlib.sha256(canonical_json_bytes(detached)).hexdigest() != cert[
        "annotated_records_sha256"
    ]:
        raise V0P6IncompleteError("OFF-match annotated records changed")

    witness_fields = {
        "record_id",
        "window_id",
        "snr",
        "template_index",
        "spectral_width_index",
        "active_epochs_zero_based",
        "proxy_carrier_index",
        "proxy_carrier_hz",
        "maximum_track_distance_hz",
    }

    def validated_witness(
        witness: Any,
        *,
        require_zero_distance: bool,
    ) -> None:
        if not isinstance(witness, dict) or frozenset(witness) != witness_fields:
            raise V0P6ContractError("OFF witness fields do not match the schema")
        _frozen_sha256(witness["record_id"], "OFF witness record identity")
        if not isinstance(witness["window_id"], str) or not witness["window_id"]:
            raise V0P6ContractError("OFF witness window identity is invalid")
        _strict_int(witness["template_index"], "OFF witness template index")
        _strict_int(
            witness["spectral_width_index"], "OFF witness spectral-width index"
        )
        canonical_activity_subsets((witness["active_epochs_zero_based"],))
        _strict_int(
            witness["proxy_carrier_index"], "OFF witness proxy-carrier index"
        )
        _, _, distance = (
            _finite_json_number(value, f"OFF witness {label}")
            for label, value in (
                ("S/N", witness["snr"]),
                ("proxy carrier", witness["proxy_carrier_hz"]),
                (
                    "maximum track distance",
                    witness["maximum_track_distance_hz"],
                ),
            )
        )
        if distance < 0.0 or distance > tolerance_hz or (
            require_zero_distance and distance != 0.0
        ):
            raise V0P6ContractError("OFF witness distance violates its contract")

    seen_ids: set[str] = set()
    observed_dispositions = {name: 0 for name in expected_precedence}
    total_record_bytes = 0
    for record in detached:
        try:
            _validate_retained_record_json_numeric_types(record)
        except (KeyError, TypeError, V0P6ContractError) as error:
            raise V0P6ContractError(
                "OFF-match retained record has invalid JSON numeric types"
            ) from error
        record_id = _frozen_sha256(
            record.get("record_id"), "retained ON record identity"
        )
        if record_id in seen_ids:
            raise V0P6IncompleteError("OFF-match result repeats a record ID")
        seen_ids.add(record_id)
        evidence = record.get("off_track_evidence")
        if not isinstance(evidence, dict) or frozenset(evidence) != {
            "contract",
            "tolerance_hz",
            "off_integration_count",
            "off_factor_matrix_sha256",
            "same_hypothesis",
            "local_track",
        }:
            raise V0P6ContractError("OFF-track evidence fields changed")
        evidence_tolerance_hz = _finite_json_number(
            evidence["tolerance_hz"], "OFF-track evidence tolerance"
        )
        if (
            evidence["contract"]
            != "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz"
            or evidence_tolerance_hz != tolerance_hz
            or _strict_int(
                evidence["off_integration_count"], "OFF integration count"
            )
            != integration_count
            or evidence["off_factor_matrix_sha256"]
            != cert["off_factor_matrix_sha256"]
        ):
            raise V0P6ContractError("OFF-track evidence contract changed")
        matches: dict[str, tuple[bool, int]] = {}
        for name, require_zero in (
            ("same_hypothesis", True),
            ("local_track", False),
        ):
            section = evidence[name]
            if not isinstance(section, dict) or frozenset(section) != {
                "matched",
                "matched_off_record_count",
                "best_off_witness",
            }:
                raise V0P6ContractError("OFF match-section schema changed")
            matched = section["matched"]
            count = _strict_int(
                section["matched_off_record_count"],
                f"{name} OFF match count",
            )
            if (
                not isinstance(matched, bool)
                or count < 0
                or matched != (count > 0)
                or (count == 0) != (section["best_off_witness"] is None)
            ):
                raise V0P6IncompleteError("OFF match-section counts changed")
            if count:
                validated_witness(
                    section["best_off_witness"],
                    require_zero_distance=require_zero,
                )
            matches[name] = (matched, count)
        if matches["same_hypothesis"][0]:
            expected_disposition = expected_precedence[0]
        elif matches["local_track"][0]:
            expected_disposition = expected_precedence[1]
        else:
            expected_disposition = expected_precedence[2]
        if record.get("member_disposition") != expected_disposition:
            raise V0P6ContractError("OFF-match disposition precedence changed")
        observed_dispositions[expected_disposition] += 1
        size = len(canonical_json_bytes(record))
        if size > record_byte_cap:
            raise V0P6CapacityError("OFF-match annotated record exceeds its byte cap")
        total_record_bytes += size
    if cert["disposition_counts"] != observed_dispositions:
        raise V0P6IncompleteError("OFF-match disposition counts changed")
    if total_record_bytes != _strict_int(
        cert["annotated_evidence_canonical_bytes"],
        "OFF annotated evidence byte count",
    ) or (evidence_byte_cap is not None and total_record_bytes > evidence_byte_cap):
        raise V0P6CapacityError("OFF-match annotated evidence exceeds its byte cap")
    return cert


def match_m37_retained_off_tracks(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    off_records: Sequence[Mapping[str, Any]],
    off_certificate: Mapping[str, Any],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str | None = None,
    expected_off_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Apply the non-configurable M37 same/local retained-OFF veto pass."""
    validate_factor_basis(factor_basis)
    on_cert = validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    off_cert = validate_retention_certificate(
        off_certificate,
        expected_certificate_sha256=expected_off_certificate_sha256,
    )
    for cert, expected_kind in ((on_cert, "on"), (off_cert, "off")):
        expected_window = str(cert["window_id"])
        if expected_window not in M37_WINDOW_IDS:
            raise V0P6ContractError("M37 OFF matcher received an unknown window")
        expected_hypotheses = (
            M37_TEMPLATE_COUNT
            * len(M37_SPECTRAL_WIDTHS)
            * len(M37_ACTIVITY_SUBSETS)
        )
        expected_score_cells = expected_hypotheses * (
            2 * M37_SCORE_HALF_BINS + 1
        )
        if (
            cert["scan_kind"] != expected_kind
            or cert["proxy_grid_sha256"]
            != proxy_carrier_grid_sha256(
                make_m37_proxy_carrier_grid(expected_window)
            )
            or cert["experiment_contract_sha256"]
            != M37_EXPERIMENT_CONTRACT_SHA256
            or cert["template_bank_sha256"] != M37_BANK_SHA256
            or cert["factor_basis_sha256"] != M37_FACTOR_BASIS_SHA256
            or cert["factor_basis_labels_sha256"]
            != M37_FACTOR_BASIS_LABELS_SHA256
            or cert["scan_inventory_sha256"] != M37_SCAN_INVENTORY_SHA256
            or cert["factor_row_selection_sha256"]
            != M37_FACTOR_ROW_SELECTION_SHA256S[expected_kind]
            or tuple(cert["spectral_widths"]) != M37_SPECTRAL_WIDTHS
            or tuple(tuple(item) for item in cert["activity_subsets"])
            != M37_ACTIVITY_SUBSETS
            or cert["epoch_count"] != 3
            or cert["minimum_active_epoch_snr"]
            != M37_MINIMUM_ACTIVE_EPOCH_SNR
            or cert["stack_statistic"] != "minimum_epoch"
            or cert["require_epoch_vector_product"] is not True
            or cert["require_mask_product"] is not True
            or cert["maximum_records"] != M37_MAXIMUM_RECORDS_PER_WINDOW
            or cert["maximum_record_canonical_bytes"]
            != M37_MAXIMUM_RECORD_CANONICAL_BYTES
            or cert["maximum_evidence_canonical_bytes"]
            != M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
            or cert["expected_hypotheses"] != expected_hypotheses
            or cert["expected_score_cells"] != expected_score_cells
        ):
            raise V0P6ContractError(
                "retention certificate violates the M37 OFF-match contract"
            )
    validate_template_factor_table(
        factor_table,
        factor_basis,
        make_line_template_bank(),
        expected_template_bank_sha256=M37_BANK_SHA256,
    )
    if (
        factor_basis.basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_basis.labels_sha256 != M37_FACTOR_BASIS_LABELS_SHA256
        or factor_table.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_table.template_bank_sha256 != M37_BANK_SHA256
        or factor_table.factors.shape[0] != M37_TEMPLATE_COUNT
        or on_cert["factor_basis_sha256"] != factor_basis.basis_sha256
        or off_cert["factor_basis_sha256"] != factor_basis.basis_sha256
        or on_cert["factor_table_sha256"]
        != factor_table.factor_table_sha256
        or off_cert["factor_table_sha256"]
        != factor_table.factor_table_sha256
    ):
        raise V0P6ContractError("OFF matcher did not receive the sealed M37 factors")
    validate_m37_factor_basis_scan_inventory(factor_basis, scan_definitions)
    factors = factor_matrix_for_kind(
        factor_table, factor_basis, scan_definitions, "off"
    )
    if factors.shape != (M37_TEMPLATE_COUNT, 48):
        raise V0P6ContractError("M37 OFF factor matrix must have shape [93, 48]")
    return match_retained_off_tracks(
        on_records,
        on_certificate,
        off_records,
        off_certificate,
        make_m37_proxy_carrier_grid(str(on_cert["window_id"])),
        factors,
        window_order=M37_WINDOW_IDS,
        tolerance_hz=M37_OFF_TRACK_TOLERANCE_HZ,
        maximum_bucket_entries=M37_MAXIMUM_OFF_BUCKET_ENTRIES,
        maximum_exact_candidate_visits=(
            M37_MAXIMUM_OFF_EXACT_CANDIDATE_VISITS
        ),
        template_bank=make_line_template_bank(),
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_off_certificate_sha256=expected_off_certificate_sha256,
    )
