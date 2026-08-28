"""Fail-closed M37 extraction, normalization, and native-cache source chain.

The generic cache helpers in :mod:`seti_repeater.search_v0p6` deliberately
remain useful for synthetic and known-answer tests.  They are not a telescope
source boundary: a caller can choose both their normalized array and their
``source_sha256``.  This module is the production boundary for M37.

The chain has two immutable products.  ``M37ExtractedScanProduct`` binds the
exact published scan, remote identity, header, normative extraction interval,
header-derived native frequency axis, and the raw float32 payload.  It then
reverses the native HDF5 channel order exactly once to a canonical ascending
physical-frequency order.  ``M37NormalizedScanProduct`` derives normalization
inside its factory from those canonical raw values; caller-normalized values
are never accepted by a live production factory.

Normalization is row-local and anchored at canonical native channel zero.
Each complete 4096-channel block and the final short block are treated
independently.  Both the center and MAD use an exact float32 order statistic.
For even-length blocks the two middle float32 values are added in float32 and
then divided by float32 two.  Deviations, ``float32(1.4826) * MAD``, the
float32-tiny floor, subtraction, and division are all float32 operations.
This intentionally matches detector-v0.5's median/MAD semantics while making
the dtype, physical channel order, block origin, and terminal-block behavior
explicit.  The exact NumPy/Python runtime is part of the engine identity.

Importing this module performs no I/O and never opens a telescope product.
The final telescope payload hashes are prospective, product-specific values;
there are deliberately no constants pretending that those hashes are frozen.

Trust model: a live factory seal is an in-process integrity receipt.  It proves
that the exact supplied raw bytes were paired with the frozen metadata and
passed this factory; it is not cryptographic evidence that a remote server
supplied those bytes.  The production extractor must own the live factory call
immediately after its authenticated URL/size/ETag/header/hyperslab checks, and
publication must preserve the resulting receipt SHA independently.  A later
process therefore rehydrates only against that independently trusted SHA.

Resource model: the per-product cap is not a whole-workflow memory claim.  A
largest-window product owns 58,684,608 raw bytes, 7,335,576 frequency bytes,
and 58,684,608 normalized bytes (124,704,792 ndarray bytes total).  Three such
ON products own 374,114,376 bytes; three additional rolled normalized arrays
raise that to 550,168,200 bytes, already above the frozen 512-MiB live-ndarray
cap before caches or validation scratch.  Multi-scan consumers must call the
public working-set gate with every simultaneously live derived array and use a
scan-at-a-time/disk-backed design or fail closed.  The gate also accounts for
the raw-sized scratch used by each simultaneous normalization reproduction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import inspect
import json
import math
import platform
import sys
import weakref
from typing import Any, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


M37_SOURCE_ARTIFACT_SCHEMA_VERSION = 1
M37_EXTRACTED_SCAN_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_m37_extracted_scan"
)
M37_NORMALIZED_SCAN_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_m37_normalized_scan"
)

# Published metadata/preflight identities.  These bind only source metadata
# and extraction geometry; none is a telescope spectral-payload digest.
M37_BANK_PREFLIGHT_RESULT_SHA256 = (
    "d9a2ab193b592d4478abcd3d50227a2329f88aeb30e40e148480657b43f739ba"
)
M37_BANK_PREFLIGHT_MANIFEST_SHA256 = (
    "5ea5bd94112cee6a8f0b1c325d7b888bda4e93199d4361bdb39cebc528222a3a"
)
M37_BANK_PREFLIGHT_PROVENANCE_SHA256 = (
    "c62a597872db585abe5cbc7af66149d334688e766b85ea6b20d9ced9d8d5c140"
)
M37_SOURCE_SCAN_DEFINITIONS_SHA256 = (
    "7da8a430ecb342ca0b928174f2fe4b86c8b76df97f65adb27caeadfc782d1a33"
)
M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256 = (
    "681e5de8c2a31d9f8786009236f1db9ac413ad47ffc18226cbf2b4825027ad79"
)

M37_HDF5_EXTRACTOR_SOURCE_SHA256 = (
    "9a16f603dd60128297e4d98e4593d243a47773f1e95177b1cfa323fa296574f8"
)
M37_EXTRACTION_ENGINE = "m37_hdf5_hyperslab_attestation_v1"
M37_NORMALIZATION_ENGINE = "m37_float32_median_mad_blocks_v1"
M37_NORMALIZATION_BLOCK_CHANNELS = 4096
M37_NORMALIZATION_MAD_MULTIPLIER = np.float32(1.4826)
M37_NORMALIZATION_SCALE_FLOOR = np.float32(np.finfo(np.float32).tiny)

M37_SOURCE_INTEGRATION_COUNT = 16
M37_MAXIMUM_SOURCE_NATIVE_CHANNELS = 916_947
M37_MAXIMUM_SOURCE_RAW_NBYTES = 64 * 1024 * 1024
M37_MAXIMUM_SOURCE_FREQUENCY_NBYTES = 8 * 1024 * 1024
M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES = 140 * 1024 * 1024
M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES = (
    core.M37_LIVE_NDARRAY_CAP_BYTES
)
M37_MAXIMUM_SOURCE_ATTESTATIONS = 256
M37_MAXIMUM_SOURCE_ATTESTATION_BYTES = 4 * 1024 * 1024

_F4 = np.dtype("<f4")
_F8 = np.dtype("<f8")


# Exact source identities from the already-published M37 metadata-only
# configuration.  Keeping them in the implementation lets persisted products
# be revalidated without consulting a mutable config file.
_M37_SCAN_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "epoch": 1,
        "kind": "on",
        "label": "epoch1_on",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_50207_HIP84607_0021.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_767_089_155,
        "expected_etag": '"5a9ef622-2f8fa5203"',
        "expected_header": {
            "source_name": "HIP84607",
            "src_raj_hours": 17.294555833333337,
            "src_dej_deg": 29.22806,
            "tstart_mjd": 57470.581099537034,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
    {
        "epoch": 1,
        "kind": "off",
        "label": "epoch1_off",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_50537_HIP84607_OFF_0022.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_766_872_410,
        "expected_etag": '"5a9ef77d-2f8f7035a"',
        "expected_header": {
            "source_name": "HIP84607_OFF",
            "src_raj_hours": 17.294555833333337,
            "src_dej_deg": 31.228053333333342,
            "tstart_mjd": 57470.58491898148,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
    {
        "epoch": 2,
        "kind": "on",
        "label": "epoch2_on",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_50867_HIP84607_0023.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_768_071_820,
        "expected_etag": '"5a9ef852-2f909508c"',
        "expected_header": {
            "source_name": "HIP84607",
            "src_raj_hours": 17.29455527777778,
            "src_dej_deg": 29.22805916666666,
            "tstart_mjd": 57470.588738425926,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
    {
        "epoch": 2,
        "kind": "off",
        "label": "epoch2_off",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_51197_HIP84607_OFF_0024.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_766_750_881,
        "expected_etag": '"5a9ef8f2-2f8f528a1"',
        "expected_header": {
            "source_name": "HIP84607_OFF",
            "src_raj_hours": 17.294556111111113,
            "src_dej_deg": 31.22805166666666,
            "tstart_mjd": 57470.59255787037,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
    {
        "epoch": 3,
        "kind": "on",
        "label": "epoch3_on",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_51527_HIP84607_0025.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_766_340_869,
        "expected_etag": '"5a9ef989-2f8eee705"',
        "expected_header": {
            "source_name": "HIP84607",
            "src_raj_hours": 17.294554722222223,
            "src_dej_deg": 29.22806527777777,
            "tstart_mjd": 57470.59637731482,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
    {
        "epoch": 3,
        "kind": "off",
        "label": "epoch3_off",
        "format": "HDF5",
        "url": "https://bldata.berkeley.edu/pipeline/AGBT16A_999_104/holding/spliced_blc02030405_2bit_guppi_57470_51857_HIP84607_OFF_0026.gpuspec.0000.h5",
        "expected_remote_size_bytes": 12_766_914_547,
        "expected_etag": '"5a9efa27-2f8f7a7f3"',
        "expected_header": {
            "source_name": "HIP84607_OFF",
            "src_raj_hours": 17.29455527777778,
            "src_dej_deg": 31.22805916666666,
            "tstart_mjd": 57470.60019675926,
            "tsamp_s": 17.986224128,
            "dataset_shape": [16, 1, 264503296],
            "dataset_dtype": "float32",
            "fch1_mhz": 1876.46484375,
            "foff_mhz": -0.000002835503418452676,
        },
    },
)

_M37_EXTRACTION_INTERVALS: dict[str, tuple[int, int]] = {
    "m37_1400p5": (167_400_554, 168_317_500),
    "m37_1406p5": (165_284_527, 166_201_474),
    "m37_1412p5": (163_168_501, 164_085_448),
    "m37_1418p5": (161_052_475, 161_969_421),
    "m37_1425p0": (158_760_113, 159_677_059),
}

_SOURCE_FIELDS = (
    "epoch",
    "kind",
    "label",
    "format",
    "url",
    "expected_remote_size_bytes",
    "expected_etag",
    "expected_header",
)

_EXTRACTED_SEAL = object()
_NORMALIZED_SEAL = object()
_EXTRACTED_ATTESTATIONS: dict[
    int, tuple[weakref.ReferenceType[Any], bytes]
] = {}
_NORMALIZED_ATTESTATIONS: dict[
    int, tuple[weakref.ReferenceType[Any], bytes]
] = {}
_source_attestation_bytes = 0


def _sha256(value: Any, label: str) -> str:
    return core._frozen_sha256(value, label)


def _detached_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    try:
        result = json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            f"{label} is not canonical finite JSON"
        ) from error
    if not isinstance(result, dict):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    return result


def _source_records(
    scan_definitions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    try:
        return [
            {field: definition[field] for field in _SOURCE_FIELDS}
            for definition in scan_definitions
        ]
    except (KeyError, TypeError) as error:
        raise core.V0P6ContractError(
            "M37 source scan definitions have an invalid schema"
        ) from error


def validate_m37_source_scan_definitions(
    scan_definitions: Sequence[Mapping[str, Any]],
) -> None:
    """Require the exact published six-scan M37 source identity inventory."""
    core.m37_scan_indices_for_kind(scan_definitions, "on")
    records = _source_records(scan_definitions)
    digest = hashlib.sha256(core.canonical_json_bytes(records)).hexdigest()
    if digest != M37_SOURCE_SCAN_DEFINITIONS_SHA256:
        raise core.V0P6ContractError(
            "M37 source scan definitions changed from the published inventory"
        )
    if records != list(_M37_SCAN_SOURCES):
        raise core.V0P6ContractError(
            "M37 source scan definitions differ from the implementation record"
        )
    if core.scan_inventory_sha256(scan_definitions) != (
        core.M37_SCAN_INVENTORY_SHA256
    ):
        raise core.V0P6ContractError("M37 scan inventory identity changed")


def _validate_internal_geometry_inventory() -> None:
    if tuple(_M37_EXTRACTION_INTERVALS) != core.M37_WINDOW_IDS:
        raise core.V0P6ContractError("M37 extraction window order changed")
    records: list[dict[str, Any]] = []
    for window_id in core.M37_WINDOW_IDS:
        start, stop = _M37_EXTRACTION_INTERVALS[window_id]
        for source in _M37_SCAN_SOURCES:
            header = source["expected_header"]
            first = float(header["fch1_mhz"]) + start * float(
                header["foff_mhz"]
            )
            last = float(header["fch1_mhz"]) + (stop - 1) * float(
                header["foff_mhz"]
            )
            records.append(
                {
                    "window_id": window_id,
                    "scan_label": source["label"],
                    "channel_start": start,
                    "channel_stop": stop,
                    "channel_count": stop - start,
                    "frequency_low_mhz": min(first, last),
                    "frequency_high_mhz": max(first, last),
                    "channel_width_mhz": abs(float(header["foff_mhz"])),
                }
            )
    if hashlib.sha256(core.canonical_json_bytes(records)).hexdigest() != (
        M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256
    ):
        raise core.V0P6ContractError(
            "M37 normative extraction geometry inventory changed"
        )


def _scan_source(scan_label: str) -> tuple[int, dict[str, Any]]:
    matches = [
        (index, source)
        for index, source in enumerate(_M37_SCAN_SOURCES)
        if source["label"] == str(scan_label)
    ]
    if len(matches) != 1:
        raise core.V0P6ContractError("M37 extraction requires one known scan")
    return matches[0]


def m37_extraction_interval(window_id: str) -> tuple[int, int]:
    """Return one immutable normative native HDF5 channel interval."""
    key = str(window_id)
    if key not in _M37_EXTRACTION_INTERVALS:
        raise core.V0P6ContractError("M37 extraction received an unknown window")
    return _M37_EXTRACTION_INTERVALS[key]


def _source_definition_sha256(source: Mapping[str, Any]) -> str:
    return hashlib.sha256(core.canonical_json_bytes(dict(source))).hexdigest()


_EXTRACTION_CONTRACT = {
    "artifact_schema_version": M37_SOURCE_ARTIFACT_SCHEMA_VERSION,
    "engine": M37_EXTRACTION_ENGINE,
    "frozen_extractor_source_sha256": M37_HDF5_EXTRACTOR_SOURCE_SHA256,
    "frozen_extractor_source_path": "scripts/m37_v0p6_hdf5_extract.py",
    "remote_identity": "exact URL, Content-Length, and quoted ETag equality",
    "header_identity": "exact canonical finite JSON equality",
    "payload_dtype": "<f4",
    "payload_order": "C [integration, native HDF5 channel]",
    "frequency_axis_derivation": (
        "float64 fch1_mhz + arange(channel_start, channel_stop, dtype=float64) "
        "* float64 foff_mhz"
    ),
    "frequency_witness_comparison": "bit-identical float64 C-order bytes",
    "canonical_orientation": (
        "reverse raw values and derived frequency together exactly once when "
        "the header-native axis descends; store ascending physical frequency"
    ),
    "nonfinite_policy": "fail closed before receipt",
    "normative_bank_preflight_result_sha256": (
        M37_BANK_PREFLIGHT_RESULT_SHA256
    ),
    "normative_bank_preflight_manifest_sha256": (
        M37_BANK_PREFLIGHT_MANIFEST_SHA256
    ),
    "normative_bank_preflight_provenance_sha256": (
        M37_BANK_PREFLIGHT_PROVENANCE_SHA256
    ),
    "source_scan_definitions_sha256": M37_SOURCE_SCAN_DEFINITIONS_SHA256,
    "extraction_geometry_inventory_sha256": (
        M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256
    ),
}
M37_EXTRACTION_CONTRACT_SHA256 = hashlib.sha256(
    core.canonical_json_bytes(_EXTRACTION_CONTRACT)
).hexdigest()

_NORMALIZATION_CONTRACT = {
    "artifact_schema_version": M37_SOURCE_ARTIFACT_SCHEMA_VERSION,
    "engine": M37_NORMALIZATION_ENGINE,
    "input_orientation": "canonical ascending physical frequency",
    "input_dtype": "<f4",
    "output_dtype": "<f4",
    "array_order": "C [integration, canonical native channel]",
    "block_origin": 0,
    "block_channels": M37_NORMALIZATION_BLOCK_CHANNELS,
    "terminal_block": "one final nonempty block of remaining channels",
    "row_contract": "each integration row normalized independently",
    "median_order_statistic": "numpy.partition ascending float32",
    "odd_median": "middle float32 order statistic",
    "even_median": (
        "float32 add of the two middle float32 order statistics, then "
        "float32 divide by 2.0"
    ),
    "deviation": "float32 abs(section - center)",
    "mad_multiplier_float32": float(M37_NORMALIZATION_MAD_MULTIPLIER),
    "scale_floor_float32": float(M37_NORMALIZATION_SCALE_FLOOR),
    "scale": "float32 maximum(float32 multiplier * MAD, float32 tiny)",
    "output": "float32 (section - center) / scale",
    "nonfinite_policy": "fail closed before and after normalization",
    "caller_chunking": (
        "irrelevant; blocks are always anchored to canonical channel zero"
    ),
}
M37_NORMALIZATION_CONTRACT_SHA256 = hashlib.sha256(
    core.canonical_json_bytes(_NORMALIZATION_CONTRACT)
).hexdigest()
M37_NORMALIZATION_PARAMETERS_SHA256 = hashlib.sha256(
    core.canonical_json_bytes(
        {
            "block_channels": M37_NORMALIZATION_BLOCK_CHANNELS,
            "mad_multiplier_float32": float(
                M37_NORMALIZATION_MAD_MULTIPLIER
            ),
            "scale_floor_float32": float(M37_NORMALIZATION_SCALE_FLOOR),
            "canonical_axis": "ascending_physical_frequency",
        }
    )
).hexdigest()


def _runtime_identity_payload(contract_sha256: str) -> dict[str, Any]:
    return {
        "contract_sha256": contract_sha256,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_compiler": platform.python_compiler(),
        "numpy_version": np.__version__,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "byteorder": sys.byteorder,
        "float32_dtype": np.dtype(np.float32).str,
        "float64_dtype": np.dtype(np.float64).str,
    }


def _array_sha256(array: np.ndarray, dtype: np.dtype[Any]) -> str:
    view = np.asarray(array)
    if view.dtype != dtype or not view.flags.c_contiguous:
        raise core.V0P6ContractError("source array dtype/order changed")
    payload = memoryview(view).cast("B")
    try:
        return hashlib.sha256(payload).hexdigest()
    finally:
        payload.release()


def _immutable_array(
    values: np.ndarray,
    dtype: np.dtype[Any],
    shape: tuple[int, ...],
    label: str,
) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype != dtype:
        raise core.V0P6ContractError(f"{label} must have exact dtype {dtype.str}")
    if array.shape != shape or not array.flags.c_contiguous:
        raise core.V0P6ContractError(
            f"{label} must have the exact C-order extraction shape"
        )
    if not np.all(np.isfinite(array)):
        raise core.V0P6ContractError(f"{label} contains non-finite values")
    payload = array.tobytes(order="C")
    sealed = np.frombuffer(payload, dtype=dtype).reshape(shape)
    if sealed.flags.writeable:
        raise core.V0P6IncompleteError(f"{label} did not become read-only")
    return sealed


def _require_immutable_array(
    array: np.ndarray,
    dtype: np.dtype[Any],
    shape: tuple[int, ...],
    label: str,
) -> None:
    if (
        not isinstance(array, np.ndarray)
        or array.dtype != dtype
        or array.shape != shape
        or not array.flags.c_contiguous
        or array.flags.writeable
    ):
        raise core.V0P6IncompleteError(
            f"sealed {label} dtype, shape, order, or mutability changed"
        )
    root: Any = array
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    if not isinstance(getattr(root, "base", None), bytes):
        raise core.V0P6IncompleteError(
            f"sealed {label} is not backed by immutable bytes"
        )
    if not np.all(np.isfinite(array)):
        raise core.V0P6IncompleteError(f"sealed {label} became non-finite")


def _reversed_raw_sha256(canonical_raw: np.ndarray) -> str:
    hasher = hashlib.sha256()
    for row in canonical_raw:
        hasher.update(np.ascontiguousarray(row[::-1], dtype=_F4).tobytes())
    return hasher.hexdigest()


def _reversed_frequency_sha256(canonical_frequency: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(canonical_frequency[::-1], dtype=_F8).tobytes()
    ).hexdigest()


def _float32_median_rows(section: np.ndarray) -> np.ndarray:
    count = section.shape[1]
    lower = (count - 1) // 2
    upper = count // 2
    if lower == upper:
        partitioned = np.partition(section, lower, axis=1)
        return np.asarray(partitioned[:, lower], dtype=np.float32)
    partitioned = np.partition(section, (lower, upper), axis=1)
    total = np.add(
        partitioned[:, lower], partitioned[:, upper], dtype=np.float32
    )
    return np.divide(total, np.float32(2.0), dtype=np.float32)


def normalize_float32_blocks_v0p6(values: np.ndarray) -> np.ndarray:
    """Return the exact v0.6 block median/MAD normalization.

    This low-level function is a deterministic algorithm/KAT helper.  It does
    not attest source provenance and therefore must not be passed directly to
    a production M37 cache.  Production uses
    :func:`normalize_m37_extracted_scan`.
    """
    data = np.asarray(values)
    if (
        data.ndim != 2
        or data.dtype != _F4
        or not data.flags.c_contiguous
        or data.shape[0] < 1
        or data.shape[1] < 1
    ):
        raise core.V0P6ContractError(
            "normalization input must be a nonempty C-order <f4 matrix"
        )
    if data.nbytes > M37_MAXIMUM_SOURCE_RAW_NBYTES:
        raise core.V0P6CapacityError("normalization input byte cap exceeded")
    if not np.all(np.isfinite(data)):
        raise core.V0P6ContractError(
            "normalization input contains non-finite values"
        )
    normalized = np.empty(data.shape, dtype=np.float32, order="C")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for start in range(
            0, data.shape[1], M37_NORMALIZATION_BLOCK_CHANNELS
        ):
            stop = min(
                start + M37_NORMALIZATION_BLOCK_CHANNELS,
                data.shape[1],
            )
            section = data[:, start:stop]
            center = _float32_median_rows(section)
            deviations = np.abs(
                np.subtract(section, center[:, None], dtype=np.float32)
            )
            mad = _float32_median_rows(deviations)
            scaled_mad = np.multiply(
                M37_NORMALIZATION_MAD_MULTIPLIER,
                mad,
                dtype=np.float32,
            )
            scale = np.maximum(
                scaled_mad, M37_NORMALIZATION_SCALE_FLOOR
            ).astype(np.float32, copy=False)
            centered = np.subtract(
                section, center[:, None], dtype=np.float32
            )
            normalized[:, start:stop] = np.divide(
                centered, scale[:, None], dtype=np.float32
            )
    if not np.all(np.isfinite(normalized)):
        raise core.V0P6ContractError(
            "normalization produced non-finite float32 values"
        )
    return normalized


M37_NORMALIZATION_IMPLEMENTATION_SHA256 = hashlib.sha256(
    (
        inspect.getsource(_float32_median_rows)
        + "\n"
        + inspect.getsource(normalize_float32_blocks_v0p6)
    ).encode()
).hexdigest()
M37_NORMALIZATION_ENGINE_IDENTITY_SHA256 = hashlib.sha256(
    core.canonical_json_bytes(
        {
            **_runtime_identity_payload(M37_NORMALIZATION_CONTRACT_SHA256),
            "normalization_implementation_sha256": (
                M37_NORMALIZATION_IMPLEMENTATION_SHA256
            ),
        }
    )
).hexdigest()


@dataclass(frozen=True)
class M37ExtractedScanProduct:
    """Immutable canonical raw scan plus a live/trusted extraction receipt."""

    raw_values: np.ndarray = field(repr=False)
    frequency_mhz: np.ndarray = field(repr=False)
    window_id: str
    scan_label: str
    scan_kind: str
    epoch: int
    source_url: str
    expected_remote_size_bytes: int
    expected_etag: str
    expected_header_json: str
    expected_header_sha256: str
    source_scan_definition_sha256: str
    source_scan_definitions_sha256: str
    scan_inventory_sha256: str
    channel_start: int
    channel_stop: int
    geometry: core.NativeFrequencyGeometry
    original_axis_order: str
    canonical_axis_order: str
    original_raw_values_sha256: str
    original_frequency_mhz_sha256: str
    raw_values_sha256: str
    frequency_mhz_sha256: str
    raw_values_nbytes: int
    frequency_mhz_nbytes: int
    extraction_engine: str
    extraction_engine_identity_sha256: str
    extraction_contract_sha256: str
    extraction_geometry_inventory_sha256: str
    bank_preflight_result_sha256: str
    bank_preflight_manifest_sha256: str
    bank_preflight_provenance_sha256: str
    extraction_receipt_sha256: str
    _seal: object = field(repr=False, compare=False)
    _receipt: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class M37NormalizedScanProduct:
    """Immutable raw/frequency/normalized scan with complete source identity."""

    raw_values: np.ndarray = field(repr=False)
    frequency_mhz: np.ndarray = field(repr=False)
    normalized_values: np.ndarray = field(repr=False)
    window_id: str
    scan_label: str
    scan_kind: str
    epoch: int
    source_url: str
    expected_remote_size_bytes: int
    expected_etag: str
    expected_header_json: str
    expected_header_sha256: str
    source_scan_definition_sha256: str
    source_scan_definitions_sha256: str
    scan_inventory_sha256: str
    channel_start: int
    channel_stop: int
    geometry: core.NativeFrequencyGeometry
    original_axis_order: str
    canonical_axis_order: str
    original_raw_values_sha256: str
    original_frequency_mhz_sha256: str
    raw_values_sha256: str
    frequency_mhz_sha256: str
    normalized_values_sha256: str
    raw_values_nbytes: int
    frequency_mhz_nbytes: int
    normalized_values_nbytes: int
    extraction_engine: str
    extraction_engine_identity_sha256: str
    extraction_contract_sha256: str
    extraction_geometry_inventory_sha256: str
    extraction_receipt_sha256: str
    extraction_receipt_record_json: str
    normalization_engine: str
    normalization_engine_identity_sha256: str
    normalization_contract_sha256: str
    normalization_parameters_sha256: str
    normalization_block_channels: int
    normalization_mad_multiplier_float32: float
    normalization_scale_floor_float32: float
    bank_preflight_result_sha256: str
    bank_preflight_manifest_sha256: str
    bank_preflight_provenance_sha256: str
    product_sha256: str
    _seal: object = field(repr=False, compare=False)
    _receipt: object = field(repr=False, compare=False)

    @property
    def normalized(self) -> np.ndarray:
        """Compatibility spelling for consumers that expect ``normalized``."""
        return self.normalized_values


def _geometry_payload(geometry: core.NativeFrequencyGeometry) -> dict[str, Any]:
    return {
        "raw_zero_hz": float(geometry.raw_zero_hz),
        "channel_width_hz": float(geometry.channel_width_hz),
        "channel_count": core._strict_int(
            geometry.channel_count, "source native channel count"
        ),
    }


def _extracted_payload(product: M37ExtractedScanProduct) -> dict[str, Any]:
    return {
        "artifact_type": M37_EXTRACTED_SCAN_ARTIFACT_TYPE,
        "schema_version": M37_SOURCE_ARTIFACT_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_id": str(product.window_id),
        "scan_label": str(product.scan_label),
        "scan_kind": str(product.scan_kind),
        "epoch": core._strict_int(product.epoch, "source scan epoch"),
        "source_url": str(product.source_url),
        "expected_remote_size_bytes": core._strict_int(
            product.expected_remote_size_bytes, "source remote byte size"
        ),
        "expected_etag": str(product.expected_etag),
        "expected_header_json": str(product.expected_header_json),
        "expected_header_sha256": _sha256(
            product.expected_header_sha256, "source header identity"
        ),
        "source_scan_definition_sha256": _sha256(
            product.source_scan_definition_sha256,
            "source scan-definition identity",
        ),
        "source_scan_definitions_sha256": _sha256(
            product.source_scan_definitions_sha256,
            "source scan inventory identity",
        ),
        "scan_inventory_sha256": _sha256(
            product.scan_inventory_sha256, "factor scan inventory identity"
        ),
        "channel_start": core._strict_int(
            product.channel_start, "source channel start"
        ),
        "channel_stop": core._strict_int(
            product.channel_stop, "source channel stop"
        ),
        "geometry": _geometry_payload(product.geometry),
        "original_axis_order": str(product.original_axis_order),
        "canonical_axis_order": str(product.canonical_axis_order),
        "original_raw_values_sha256": _sha256(
            product.original_raw_values_sha256,
            "original raw source identity",
        ),
        "original_frequency_mhz_sha256": _sha256(
            product.original_frequency_mhz_sha256,
            "original frequency source identity",
        ),
        "raw_values_sha256": _sha256(
            product.raw_values_sha256, "canonical raw source identity"
        ),
        "frequency_mhz_sha256": _sha256(
            product.frequency_mhz_sha256,
            "canonical frequency source identity",
        ),
        "raw_values_shape": list(product.raw_values.shape),
        "raw_values_dtype": "<f4",
        "raw_values_nbytes": core._strict_int(
            product.raw_values_nbytes, "raw source byte count"
        ),
        "frequency_mhz_shape": list(product.frequency_mhz.shape),
        "frequency_mhz_dtype": "<f8",
        "frequency_mhz_nbytes": core._strict_int(
            product.frequency_mhz_nbytes, "frequency source byte count"
        ),
        "extraction_engine": str(product.extraction_engine),
        "extraction_engine_identity_sha256": _sha256(
            product.extraction_engine_identity_sha256,
            "extraction engine identity",
        ),
        "extraction_contract_sha256": _sha256(
            product.extraction_contract_sha256,
            "extraction contract identity",
        ),
        "extraction_geometry_inventory_sha256": _sha256(
            product.extraction_geometry_inventory_sha256,
            "extraction geometry inventory identity",
        ),
        "bank_preflight_result_sha256": _sha256(
            product.bank_preflight_result_sha256,
            "bank-preflight result identity",
        ),
        "bank_preflight_manifest_sha256": _sha256(
            product.bank_preflight_manifest_sha256,
            "bank-preflight manifest identity",
        ),
        "bank_preflight_provenance_sha256": _sha256(
            product.bank_preflight_provenance_sha256,
            "bank-preflight provenance identity",
        ),
        "maximum_raw_values_nbytes": M37_MAXIMUM_SOURCE_RAW_NBYTES,
        "maximum_frequency_mhz_nbytes": (
            M37_MAXIMUM_SOURCE_FREQUENCY_NBYTES
        ),
        "maximum_factory_live_ndarray_nbytes": (
            M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES
        ),
    }


def _extracted_record(product: M37ExtractedScanProduct) -> dict[str, Any]:
    return {
        "payload": _extracted_payload(product),
        "extraction_receipt_sha256": product.extraction_receipt_sha256,
    }


def extracted_scan_product_record(
    product: M37ExtractedScanProduct,
    *,
    expected_extraction_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Return the JSON-safe extraction receipt after live/trusted validation."""
    validate_m37_extracted_scan_product(
        product,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
    )
    return json.loads(core.canonical_json_bytes(_extracted_record(product)))


def _normalized_payload(product: M37NormalizedScanProduct) -> dict[str, Any]:
    return {
        "artifact_type": M37_NORMALIZED_SCAN_ARTIFACT_TYPE,
        "schema_version": M37_SOURCE_ARTIFACT_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_id": str(product.window_id),
        "scan_label": str(product.scan_label),
        "scan_kind": str(product.scan_kind),
        "epoch": core._strict_int(product.epoch, "normalized scan epoch"),
        "source_url": str(product.source_url),
        "expected_remote_size_bytes": core._strict_int(
            product.expected_remote_size_bytes, "source remote byte size"
        ),
        "expected_etag": str(product.expected_etag),
        "expected_header_json": str(product.expected_header_json),
        "expected_header_sha256": _sha256(
            product.expected_header_sha256, "source header identity"
        ),
        "source_scan_definition_sha256": _sha256(
            product.source_scan_definition_sha256,
            "source scan-definition identity",
        ),
        "source_scan_definitions_sha256": _sha256(
            product.source_scan_definitions_sha256,
            "source scan inventory identity",
        ),
        "scan_inventory_sha256": _sha256(
            product.scan_inventory_sha256, "factor scan inventory identity"
        ),
        "channel_start": core._strict_int(
            product.channel_start, "source channel start"
        ),
        "channel_stop": core._strict_int(
            product.channel_stop, "source channel stop"
        ),
        "geometry": _geometry_payload(product.geometry),
        "original_axis_order": str(product.original_axis_order),
        "canonical_axis_order": str(product.canonical_axis_order),
        "original_raw_values_sha256": _sha256(
            product.original_raw_values_sha256,
            "original raw source identity",
        ),
        "original_frequency_mhz_sha256": _sha256(
            product.original_frequency_mhz_sha256,
            "original frequency source identity",
        ),
        "raw_values_sha256": _sha256(
            product.raw_values_sha256, "canonical raw source identity"
        ),
        "frequency_mhz_sha256": _sha256(
            product.frequency_mhz_sha256,
            "canonical frequency source identity",
        ),
        "normalized_values_sha256": _sha256(
            product.normalized_values_sha256,
            "normalized source identity",
        ),
        "raw_values_shape": list(product.raw_values.shape),
        "raw_values_dtype": "<f4",
        "raw_values_nbytes": core._strict_int(
            product.raw_values_nbytes, "raw source byte count"
        ),
        "frequency_mhz_shape": list(product.frequency_mhz.shape),
        "frequency_mhz_dtype": "<f8",
        "frequency_mhz_nbytes": core._strict_int(
            product.frequency_mhz_nbytes, "frequency source byte count"
        ),
        "normalized_values_shape": list(product.normalized_values.shape),
        "normalized_values_dtype": "<f4",
        "normalized_values_nbytes": core._strict_int(
            product.normalized_values_nbytes,
            "normalized source byte count",
        ),
        "extraction_engine": str(product.extraction_engine),
        "extraction_engine_identity_sha256": _sha256(
            product.extraction_engine_identity_sha256,
            "extraction engine identity",
        ),
        "extraction_contract_sha256": _sha256(
            product.extraction_contract_sha256,
            "extraction contract identity",
        ),
        "extraction_geometry_inventory_sha256": _sha256(
            product.extraction_geometry_inventory_sha256,
            "extraction geometry inventory identity",
        ),
        "extraction_receipt_sha256": _sha256(
            product.extraction_receipt_sha256,
            "extraction receipt identity",
        ),
        "extraction_receipt_record_json": str(
            product.extraction_receipt_record_json
        ),
        "normalization_engine": str(product.normalization_engine),
        "normalization_engine_identity_sha256": _sha256(
            product.normalization_engine_identity_sha256,
            "normalization engine identity",
        ),
        "normalization_contract_sha256": _sha256(
            product.normalization_contract_sha256,
            "normalization contract identity",
        ),
        "normalization_parameters_sha256": _sha256(
            product.normalization_parameters_sha256,
            "normalization parameters identity",
        ),
        "normalization_block_channels": core._strict_int(
            product.normalization_block_channels,
            "normalization block size",
        ),
        "normalization_mad_multiplier_float32": float(
            product.normalization_mad_multiplier_float32
        ),
        "normalization_scale_floor_float32": float(
            product.normalization_scale_floor_float32
        ),
        "bank_preflight_result_sha256": _sha256(
            product.bank_preflight_result_sha256,
            "bank-preflight result identity",
        ),
        "bank_preflight_manifest_sha256": _sha256(
            product.bank_preflight_manifest_sha256,
            "bank-preflight manifest identity",
        ),
        "bank_preflight_provenance_sha256": _sha256(
            product.bank_preflight_provenance_sha256,
            "bank-preflight provenance identity",
        ),
        "maximum_product_array_nbytes": (
            M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES
        ),
        "maximum_factory_live_ndarray_nbytes": (
            M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES
        ),
    }


def _normalized_record(product: M37NormalizedScanProduct) -> dict[str, Any]:
    return {
        "payload": _normalized_payload(product),
        "product_sha256": product.product_sha256,
    }


def normalized_scan_product_record(
    product: M37NormalizedScanProduct,
    *,
    expected_product_sha256: str | None = None,
    expected_extraction_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Return the JSON-safe normalized product receipt after validation."""
    validate_m37_normalized_scan_product(
        product,
        expected_product_sha256=expected_product_sha256,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
    )
    return json.loads(core.canonical_json_bytes(_normalized_record(product)))


def m37_source_working_set_accounting(
    products: Sequence[M37NormalizedScanProduct],
    *,
    additional_live_ndarray_nbytes: int,
    simultaneous_normalization_reproductions: int = 1,
    expected_product_sha256s: Sequence[str | None] | None = None,
    expected_extraction_receipt_sha256s: Sequence[str | None] | None = None,
) -> dict[str, Any]:
    """Account a declared simultaneous source-product ndarray working set.

    Product inventory entries are counted as separate resident ownership even
    if a caller repeats the same Python object; this conservative rule avoids
    using aliasing as an undocumented resource optimization.  ``additional``
    must include every simultaneously live consumer array (rolls, injection
    buffers, caches, and scratch not owned by these products).  The function
    adds one raw-sized normalization reproduction scratch per requested
    simultaneous validation and fails closed above 512 MiB.
    """
    if isinstance(products, (str, bytes)):
        raise core.V0P6ContractError(
            "source working-set products must be a product sequence"
        )
    inventory = tuple(products)
    additional = core._strict_int(
        additional_live_ndarray_nbytes,
        "additional source-consumer ndarray bytes",
    )
    reproductions = core._strict_int(
        simultaneous_normalization_reproductions,
        "simultaneous normalization reproductions",
    )
    if additional < 0 or reproductions < 0:
        raise core.V0P6ContractError(
            "source working-set byte/count inputs must be non-negative"
        )
    if reproductions > len(inventory):
        raise core.V0P6ContractError(
            "normalization reproduction count exceeds product inventory"
        )
    if expected_product_sha256s is None:
        product_receipts: tuple[str | None, ...] = (None,) * len(inventory)
    else:
        product_receipts = tuple(expected_product_sha256s)
    if expected_extraction_receipt_sha256s is None:
        extraction_receipts: tuple[str | None, ...] = (None,) * len(inventory)
    else:
        extraction_receipts = tuple(
            expected_extraction_receipt_sha256s
        )
    if len(product_receipts) != len(inventory) or len(
        extraction_receipts
    ) != len(inventory):
        raise core.V0P6ContractError(
            "source working-set receipt inventory length changed"
        )
    entries: list[dict[str, Any]] = []
    scratch_candidates: list[int] = []
    resident = 0
    for ordinal, (product, product_receipt, extraction_receipt) in enumerate(
        zip(
            inventory,
            product_receipts,
            extraction_receipts,
            strict=True,
        )
    ):
        validate_m37_normalized_scan_product(
            product,
            expected_product_sha256=product_receipt,
            expected_extraction_receipt_sha256=extraction_receipt,
            verify_arrays=False,
        )
        owned = (
            product.raw_values_nbytes
            + product.frequency_mhz_nbytes
            + product.normalized_values_nbytes
        )
        resident += owned
        scratch_candidates.append(product.raw_values_nbytes)
        entries.append(
            {
                "inventory_ordinal": ordinal,
                "window_id": product.window_id,
                "scan_label": product.scan_label,
                "product_sha256": product.product_sha256,
                "raw_values_nbytes": product.raw_values_nbytes,
                "frequency_mhz_nbytes": product.frequency_mhz_nbytes,
                "normalized_values_nbytes": product.normalized_values_nbytes,
                "owned_ndarray_nbytes": owned,
            }
        )
    scratch = sum(
        sorted(scratch_candidates, reverse=True)[:reproductions]
    )
    total = resident + additional + scratch
    record = {
        "accounting_contract": (
            "declared distinct product ownership + all additional live "
            "consumer ndarrays + largest simultaneous raw-sized "
            "normalization reproduction scratch"
        ),
        "product_inventory": entries,
        "product_count": len(entries),
        "resident_product_ndarray_nbytes": resident,
        "additional_live_ndarray_nbytes": additional,
        "simultaneous_normalization_reproductions": reproductions,
        "normalization_reproduction_scratch_nbytes": scratch,
        "peak_live_ndarray_nbytes": total,
        "maximum_live_ndarray_nbytes": (
            M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES
        ),
        "within_live_ndarray_cap": total
        <= M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES,
        "truncation_permitted": False,
    }
    record["accounting_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(record)
    ).hexdigest()
    if not record["within_live_ndarray_cap"]:
        raise core.V0P6CapacityError(
            "declared source working set exceeds the frozen 512-MiB "
            "live-ndarray cap"
        )
    return record


def _register_attestation(
    registry: dict[int, tuple[weakref.ReferenceType[Any], bytes]],
    product: Any,
    receipt: object,
    encoded: bytes,
    label: str,
) -> None:
    global _source_attestation_bytes
    if len(registry) >= M37_MAXIMUM_SOURCE_ATTESTATIONS:
        raise core.V0P6CapacityError(f"{label} attestation count cap exceeded")
    if _source_attestation_bytes + len(encoded) > (
        M37_MAXIMUM_SOURCE_ATTESTATION_BYTES
    ):
        raise core.V0P6CapacityError(f"{label} attestation byte cap exceeded")
    key = id(receipt)

    def discard(reference: weakref.ReferenceType[Any]) -> None:
        global _source_attestation_bytes
        current = registry.get(key)
        if current is not None and current[0] is reference:
            registry.pop(key, None)
            _source_attestation_bytes -= len(current[1])

    reference = weakref.ref(product, discard)
    registry[key] = (reference, encoded)
    _source_attestation_bytes += len(encoded)


def _attestation_matches(
    registry: dict[int, tuple[weakref.ReferenceType[Any], bytes]],
    product: Any,
    encoded: bytes,
) -> bool:
    attestation = registry.get(id(product._receipt))
    if attestation is None or attestation[0]() is not product:
        return False
    if attestation[1] != encoded:
        raise core.V0P6IncompleteError("source factory attestation changed")
    return True


def _validate_source_metadata(
    product: M37ExtractedScanProduct | M37NormalizedScanProduct,
) -> tuple[dict[str, Any], np.ndarray]:
    _validate_internal_geometry_inventory()
    scan_index, source = _scan_source(product.scan_label)
    start, stop = _M37_EXTRACTION_INTERVALS.get(
        str(product.window_id), (-1, -1)
    )
    header_bytes = core.canonical_json_bytes(source["expected_header"])
    geometry = core.native_geometry_from_extraction(
        fch1_mhz=float(source["expected_header"]["fch1_mhz"]),
        foff_mhz=float(source["expected_header"]["foff_mhz"]),
        channel_start=start,
        channel_stop=stop,
    )
    expected_frequency_original = (
        float(source["expected_header"]["fch1_mhz"])
        + np.arange(start, stop, dtype=np.float64)
        * float(source["expected_header"]["foff_mhz"])
    )
    expected_frequency = np.ascontiguousarray(
        expected_frequency_original[::-1], dtype=_F8
    )
    if (
        product.window_id not in core.M37_WINDOW_IDS
        or product.scan_kind != source["kind"]
        or product.epoch != source["epoch"]
        or product.source_url != source["url"]
        or product.expected_remote_size_bytes
        != source["expected_remote_size_bytes"]
        or product.expected_etag != source["expected_etag"]
        or product.expected_header_json != header_bytes.decode()
        or product.expected_header_sha256
        != hashlib.sha256(header_bytes).hexdigest()
        or product.source_scan_definition_sha256
        != _source_definition_sha256(source)
        or product.source_scan_definitions_sha256
        != M37_SOURCE_SCAN_DEFINITIONS_SHA256
        or product.scan_inventory_sha256 != core.M37_SCAN_INVENTORY_SHA256
        or product.channel_start != start
        or product.channel_stop != stop
        or product.geometry != geometry
        or product.original_axis_order
        != "header_native_descending_frequency"
        or product.canonical_axis_order != "ascending_physical_frequency"
        or product.extraction_engine != M37_EXTRACTION_ENGINE
        or product.extraction_engine_identity_sha256
        != M37_EXTRACTION_ENGINE_IDENTITY_SHA256
        or product.extraction_contract_sha256
        != M37_EXTRACTION_CONTRACT_SHA256
        or product.extraction_geometry_inventory_sha256
        != M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256
        or product.bank_preflight_result_sha256
        != M37_BANK_PREFLIGHT_RESULT_SHA256
        or product.bank_preflight_manifest_sha256
        != M37_BANK_PREFLIGHT_MANIFEST_SHA256
        or product.bank_preflight_provenance_sha256
        != M37_BANK_PREFLIGHT_PROVENANCE_SHA256
        or scan_index != core.M37_SCAN_ROLE_ORDER.index(
            (product.epoch, product.scan_kind, product.scan_label)
        )
    ):
        raise core.V0P6ContractError(
            "normalized source metadata differs from the exact M37 contract"
        )
    expected_shape = (M37_SOURCE_INTEGRATION_COUNT, stop - start)
    _require_immutable_array(
        product.raw_values, _F4, expected_shape, "canonical raw values"
    )
    _require_immutable_array(
        product.frequency_mhz,
        _F8,
        (stop - start,),
        "canonical frequency axis",
    )
    if not np.array_equal(product.frequency_mhz, expected_frequency):
        raise core.V0P6IncompleteError(
            "canonical frequency axis differs from the exact header derivation"
        )
    if (
        product.raw_values_nbytes != product.raw_values.nbytes
        or product.frequency_mhz_nbytes != product.frequency_mhz.nbytes
        or product.raw_values_nbytes > M37_MAXIMUM_SOURCE_RAW_NBYTES
        or product.frequency_mhz_nbytes
        > M37_MAXIMUM_SOURCE_FREQUENCY_NBYTES
        or _array_sha256(product.raw_values, _F4)
        != product.raw_values_sha256
        or _array_sha256(product.frequency_mhz, _F8)
        != product.frequency_mhz_sha256
        or _reversed_raw_sha256(product.raw_values)
        != product.original_raw_values_sha256
        or _reversed_frequency_sha256(product.frequency_mhz)
        != product.original_frequency_mhz_sha256
        or hashlib.sha256(
            np.ascontiguousarray(expected_frequency_original, dtype=_F8).tobytes()
        ).hexdigest()
        != product.original_frequency_mhz_sha256
    ):
        raise core.V0P6IncompleteError(
            "raw/frequency source bytes or resource accounting changed"
        )
    return source, expected_frequency_original


def attest_m37_extracted_scan(
    raw_values: np.ndarray,
    frequency_mhz_witness: np.ndarray | None,
    scan_definitions: Sequence[Mapping[str, Any]],
    *,
    window_id: str,
    scan_label: str,
    observed_url: str,
    observed_remote_size_bytes: int,
    observed_etag: str,
    observed_header: Mapping[str, Any],
    channel_start: int,
    channel_stop: int,
) -> M37ExtractedScanProduct:
    """Attest one exact raw M37 HDF5 hyperslab without normalizing it.

    ``raw_values`` must be in the HDF5 header-native channel order.  The
    frequency axis is always derived internally; ``frequency_mhz_witness`` is
    optional and, when present, is only a bit-identical equality witness.
    Extraction and runtime engine identities are internal constants, not
    caller strings.  This seal is an in-process byte-integrity receipt; the
    extractor invocation and independently persisted receipt SHA are the
    authority for remote origin (see the module trust model).
    """
    validate_m37_source_scan_definitions(scan_definitions)
    _validate_internal_geometry_inventory()
    scan_index, source = _scan_source(scan_label)
    window_id = str(window_id)
    if window_id not in _M37_EXTRACTION_INTERVALS:
        raise core.V0P6ContractError("M37 extraction received an unknown window")
    expected_start, expected_stop = _M37_EXTRACTION_INTERVALS[window_id]
    start = core._strict_int(channel_start, "observed extraction channel start")
    stop = core._strict_int(channel_stop, "observed extraction channel stop")
    observed_size = core._strict_int(
        observed_remote_size_bytes, "observed remote byte size"
    )
    observed_header_record = _detached_mapping(
        observed_header, "observed HDF5 header"
    )
    if (
        str(observed_url) != source["url"]
        or observed_size != source["expected_remote_size_bytes"]
        or str(observed_etag) != source["expected_etag"]
        or observed_header_record != source["expected_header"]
        or start != expected_start
        or stop != expected_stop
        or scan_index >= len(scan_definitions)
        or _source_records(scan_definitions)[scan_index] != source
    ):
        raise core.V0P6ContractError(
            "observed extraction identity differs from the exact M37 source"
        )
    header = source["expected_header"]
    expected_frequency_original = (
        float(header["fch1_mhz"])
        + np.arange(start, stop, dtype=np.float64)
        * float(header["foff_mhz"])
    )
    if expected_frequency_original[0] <= expected_frequency_original[-1]:
        raise core.V0P6ContractError(
            "M37 header-native extraction axis is no longer descending"
        )
    if frequency_mhz_witness is not None:
        witness = np.asarray(frequency_mhz_witness)
        if (
            witness.dtype != _F8
            or witness.shape != expected_frequency_original.shape
            or not witness.flags.c_contiguous
            or not np.array_equal(witness, expected_frequency_original)
        ):
            raise core.V0P6ContractError(
                "frequency witness differs from the exact header-derived axis"
            )
    raw_original = np.asarray(raw_values)
    expected_shape = (
        M37_SOURCE_INTEGRATION_COUNT,
        expected_frequency_original.size,
    )
    if raw_original.nbytes > M37_MAXIMUM_SOURCE_RAW_NBYTES:
        raise core.V0P6CapacityError("raw extraction byte cap exceeded")
    raw_original = _immutable_array(
        raw_original, _F4, expected_shape, "raw extracted values"
    )
    original_raw_digest = _array_sha256(raw_original, _F4)
    original_frequency_digest = hashlib.sha256(
        np.ascontiguousarray(expected_frequency_original, dtype=_F8).tobytes()
    ).hexdigest()
    canonical_raw = _immutable_array(
        np.ascontiguousarray(raw_original[:, ::-1], dtype=_F4),
        _F4,
        expected_shape,
        "canonical raw values",
    )
    canonical_frequency = _immutable_array(
        np.ascontiguousarray(expected_frequency_original[::-1], dtype=_F8),
        _F8,
        (expected_frequency_original.size,),
        "canonical frequency axis",
    )
    header_bytes = core.canonical_json_bytes(header)
    geometry = core.native_geometry_from_extraction(
        fch1_mhz=float(header["fch1_mhz"]),
        foff_mhz=float(header["foff_mhz"]),
        channel_start=start,
        channel_stop=stop,
    )
    receipt = object()
    partial = M37ExtractedScanProduct(
        raw_values=canonical_raw,
        frequency_mhz=canonical_frequency,
        window_id=window_id,
        scan_label=str(scan_label),
        scan_kind=str(source["kind"]),
        epoch=int(source["epoch"]),
        source_url=str(source["url"]),
        expected_remote_size_bytes=int(source["expected_remote_size_bytes"]),
        expected_etag=str(source["expected_etag"]),
        expected_header_json=header_bytes.decode(),
        expected_header_sha256=hashlib.sha256(header_bytes).hexdigest(),
        source_scan_definition_sha256=_source_definition_sha256(source),
        source_scan_definitions_sha256=M37_SOURCE_SCAN_DEFINITIONS_SHA256,
        scan_inventory_sha256=core.M37_SCAN_INVENTORY_SHA256,
        channel_start=start,
        channel_stop=stop,
        geometry=geometry,
        original_axis_order="header_native_descending_frequency",
        canonical_axis_order="ascending_physical_frequency",
        original_raw_values_sha256=original_raw_digest,
        original_frequency_mhz_sha256=original_frequency_digest,
        raw_values_sha256=_array_sha256(canonical_raw, _F4),
        frequency_mhz_sha256=_array_sha256(canonical_frequency, _F8),
        raw_values_nbytes=canonical_raw.nbytes,
        frequency_mhz_nbytes=canonical_frequency.nbytes,
        extraction_engine=M37_EXTRACTION_ENGINE,
        extraction_engine_identity_sha256=(
            M37_EXTRACTION_ENGINE_IDENTITY_SHA256
        ),
        extraction_contract_sha256=M37_EXTRACTION_CONTRACT_SHA256,
        extraction_geometry_inventory_sha256=(
            M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256
        ),
        bank_preflight_result_sha256=M37_BANK_PREFLIGHT_RESULT_SHA256,
        bank_preflight_manifest_sha256=M37_BANK_PREFLIGHT_MANIFEST_SHA256,
        bank_preflight_provenance_sha256=(
            M37_BANK_PREFLIGHT_PROVENANCE_SHA256
        ),
        extraction_receipt_sha256="",
        _seal=_EXTRACTED_SEAL,
        _receipt=receipt,
    )
    digest = hashlib.sha256(
        core.canonical_json_bytes(_extracted_payload(partial))
    ).hexdigest()
    product = M37ExtractedScanProduct(
        **{**partial.__dict__, "extraction_receipt_sha256": digest}
    )
    encoded = core.canonical_json_bytes(_extracted_record(product))
    _register_attestation(
        _EXTRACTED_ATTESTATIONS,
        product,
        receipt,
        encoded,
        "extraction receipt",
    )
    validate_m37_extracted_scan_product(product)
    return product


M37_EXTRACTION_FACTORY_IMPLEMENTATION_SHA256 = hashlib.sha256(
    (
        inspect.getsource(_immutable_array)
        + "\n"
        + inspect.getsource(_validate_source_metadata)
        + "\n"
        + inspect.getsource(attest_m37_extracted_scan)
    ).encode()
).hexdigest()
M37_EXTRACTION_ENGINE_IDENTITY_SHA256 = hashlib.sha256(
    core.canonical_json_bytes(
        {
            **_runtime_identity_payload(M37_EXTRACTION_CONTRACT_SHA256),
            "frozen_extractor_source_sha256": (
                M37_HDF5_EXTRACTOR_SOURCE_SHA256
            ),
            "extraction_factory_implementation_sha256": (
                M37_EXTRACTION_FACTORY_IMPLEMENTATION_SHA256
            ),
        }
    )
).hexdigest()


def validate_m37_extracted_scan_product(
    product: M37ExtractedScanProduct,
    *,
    expected_extraction_receipt_sha256: str | None = None,
) -> M37ExtractedScanProduct:
    """Validate an extracted product using a live or trusted receipt SHA."""
    if not isinstance(product, M37ExtractedScanProduct) or (
        product._seal is not _EXTRACTED_SEAL
    ):
        raise core.V0P6ContractError(
            "M37 extraction input is not a sealed extraction product"
        )
    _validate_source_metadata(product)
    payload = _extracted_payload(product)
    observed = hashlib.sha256(core.canonical_json_bytes(payload)).hexdigest()
    if observed != product.extraction_receipt_sha256:
        raise core.V0P6IncompleteError("extraction receipt identity changed")
    encoded = core.canonical_json_bytes(_extracted_record(product))
    live = _attestation_matches(
        _EXTRACTED_ATTESTATIONS, product, encoded
    )
    trusted = False
    if expected_extraction_receipt_sha256 is not None:
        trusted = observed == _sha256(
            expected_extraction_receipt_sha256,
            "independently trusted extraction receipt",
        )
    if not live and not trusted:
        raise core.V0P6ContractError(
            "extraction product lacks a live or independently trusted receipt"
        )
    return product


def normalize_m37_extracted_scan(
    extracted: M37ExtractedScanProduct,
    *,
    expected_extraction_receipt_sha256: str | None = None,
) -> M37NormalizedScanProduct:
    """Normalize inside the factory from one attested canonical raw product."""
    validate_m37_extracted_scan_product(
        extracted,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
    )
    normalized_mutable = normalize_float32_blocks_v0p6(extracted.raw_values)
    normalized = _immutable_array(
        normalized_mutable,
        _F4,
        extracted.raw_values.shape,
        "normalized values",
    )
    product_array_nbytes = (
        extracted.raw_values.nbytes
        + extracted.frequency_mhz.nbytes
        + normalized.nbytes
    )
    if product_array_nbytes > M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES:
        raise core.V0P6CapacityError(
            "normalized source product array-byte cap exceeded"
        )
    # Copy raw/frequency into this product's own immutable backing bytes.  It
    # remains valid after the extraction product is released or persisted.
    raw = _immutable_array(
        extracted.raw_values,
        _F4,
        extracted.raw_values.shape,
        "normalized-product raw values",
    )
    frequency = _immutable_array(
        extracted.frequency_mhz,
        _F8,
        extracted.frequency_mhz.shape,
        "normalized-product frequency axis",
    )
    extraction_record_json = core.canonical_json_bytes(
        _extracted_record(extracted)
    ).decode()
    receipt = object()
    partial = M37NormalizedScanProduct(
        raw_values=raw,
        frequency_mhz=frequency,
        normalized_values=normalized,
        window_id=extracted.window_id,
        scan_label=extracted.scan_label,
        scan_kind=extracted.scan_kind,
        epoch=extracted.epoch,
        source_url=extracted.source_url,
        expected_remote_size_bytes=extracted.expected_remote_size_bytes,
        expected_etag=extracted.expected_etag,
        expected_header_json=extracted.expected_header_json,
        expected_header_sha256=extracted.expected_header_sha256,
        source_scan_definition_sha256=(
            extracted.source_scan_definition_sha256
        ),
        source_scan_definitions_sha256=(
            extracted.source_scan_definitions_sha256
        ),
        scan_inventory_sha256=extracted.scan_inventory_sha256,
        channel_start=extracted.channel_start,
        channel_stop=extracted.channel_stop,
        geometry=extracted.geometry,
        original_axis_order=extracted.original_axis_order,
        canonical_axis_order=extracted.canonical_axis_order,
        original_raw_values_sha256=extracted.original_raw_values_sha256,
        original_frequency_mhz_sha256=(
            extracted.original_frequency_mhz_sha256
        ),
        raw_values_sha256=extracted.raw_values_sha256,
        frequency_mhz_sha256=extracted.frequency_mhz_sha256,
        normalized_values_sha256=_array_sha256(normalized, _F4),
        raw_values_nbytes=raw.nbytes,
        frequency_mhz_nbytes=frequency.nbytes,
        normalized_values_nbytes=normalized.nbytes,
        extraction_engine=extracted.extraction_engine,
        extraction_engine_identity_sha256=(
            extracted.extraction_engine_identity_sha256
        ),
        extraction_contract_sha256=extracted.extraction_contract_sha256,
        extraction_geometry_inventory_sha256=(
            extracted.extraction_geometry_inventory_sha256
        ),
        extraction_receipt_sha256=extracted.extraction_receipt_sha256,
        extraction_receipt_record_json=extraction_record_json,
        normalization_engine=M37_NORMALIZATION_ENGINE,
        normalization_engine_identity_sha256=(
            M37_NORMALIZATION_ENGINE_IDENTITY_SHA256
        ),
        normalization_contract_sha256=M37_NORMALIZATION_CONTRACT_SHA256,
        normalization_parameters_sha256=(
            M37_NORMALIZATION_PARAMETERS_SHA256
        ),
        normalization_block_channels=M37_NORMALIZATION_BLOCK_CHANNELS,
        normalization_mad_multiplier_float32=float(
            M37_NORMALIZATION_MAD_MULTIPLIER
        ),
        normalization_scale_floor_float32=float(
            M37_NORMALIZATION_SCALE_FLOOR
        ),
        bank_preflight_result_sha256=extracted.bank_preflight_result_sha256,
        bank_preflight_manifest_sha256=(
            extracted.bank_preflight_manifest_sha256
        ),
        bank_preflight_provenance_sha256=(
            extracted.bank_preflight_provenance_sha256
        ),
        product_sha256="",
        _seal=_NORMALIZED_SEAL,
        _receipt=receipt,
    )
    digest = hashlib.sha256(
        core.canonical_json_bytes(_normalized_payload(partial))
    ).hexdigest()
    product = M37NormalizedScanProduct(
        **{**partial.__dict__, "product_sha256": digest}
    )
    encoded = core.canonical_json_bytes(_normalized_record(product))
    _register_attestation(
        _NORMALIZED_ATTESTATIONS,
        product,
        receipt,
        encoded,
        "normalized source product",
    )
    validate_m37_normalized_scan_product(product)
    return product


def _expected_extraction_record_from_normalized(
    product: M37NormalizedScanProduct,
) -> dict[str, Any]:
    synthetic = M37ExtractedScanProduct(
        raw_values=product.raw_values,
        frequency_mhz=product.frequency_mhz,
        window_id=product.window_id,
        scan_label=product.scan_label,
        scan_kind=product.scan_kind,
        epoch=product.epoch,
        source_url=product.source_url,
        expected_remote_size_bytes=product.expected_remote_size_bytes,
        expected_etag=product.expected_etag,
        expected_header_json=product.expected_header_json,
        expected_header_sha256=product.expected_header_sha256,
        source_scan_definition_sha256=(
            product.source_scan_definition_sha256
        ),
        source_scan_definitions_sha256=(
            product.source_scan_definitions_sha256
        ),
        scan_inventory_sha256=product.scan_inventory_sha256,
        channel_start=product.channel_start,
        channel_stop=product.channel_stop,
        geometry=product.geometry,
        original_axis_order=product.original_axis_order,
        canonical_axis_order=product.canonical_axis_order,
        original_raw_values_sha256=product.original_raw_values_sha256,
        original_frequency_mhz_sha256=(
            product.original_frequency_mhz_sha256
        ),
        raw_values_sha256=product.raw_values_sha256,
        frequency_mhz_sha256=product.frequency_mhz_sha256,
        raw_values_nbytes=product.raw_values_nbytes,
        frequency_mhz_nbytes=product.frequency_mhz_nbytes,
        extraction_engine=product.extraction_engine,
        extraction_engine_identity_sha256=(
            product.extraction_engine_identity_sha256
        ),
        extraction_contract_sha256=product.extraction_contract_sha256,
        extraction_geometry_inventory_sha256=(
            product.extraction_geometry_inventory_sha256
        ),
        bank_preflight_result_sha256=product.bank_preflight_result_sha256,
        bank_preflight_manifest_sha256=(
            product.bank_preflight_manifest_sha256
        ),
        bank_preflight_provenance_sha256=(
            product.bank_preflight_provenance_sha256
        ),
        extraction_receipt_sha256=product.extraction_receipt_sha256,
        _seal=_EXTRACTED_SEAL,
        _receipt=object(),
    )
    return _extracted_record(synthetic)


def validate_m37_normalized_scan_product(
    product: M37NormalizedScanProduct,
    *,
    expected_product_sha256: str | None = None,
    expected_extraction_receipt_sha256: str | None = None,
    verify_arrays: bool = True,
) -> M37NormalizedScanProduct:
    """Validate a live product or one backed by independent trusted digests.

    When ``verify_arrays`` is true (the production default), the normalization
    is recomputed from the attested raw float32 bytes and compared bit for bit.
    Cache planning/building always uses this full mode.
    """
    if not isinstance(product, M37NormalizedScanProduct) or (
        product._seal is not _NORMALIZED_SEAL
    ):
        raise core.V0P6ContractError(
            "M37 cache source is not a sealed normalized-scan product"
        )
    _validate_source_metadata(product)
    expected_shape = (
        M37_SOURCE_INTEGRATION_COUNT,
        product.channel_stop - product.channel_start,
    )
    _require_immutable_array(
        product.normalized_values,
        _F4,
        expected_shape,
        "normalized values",
    )
    if (
        product.normalized_values_nbytes != product.normalized_values.nbytes
        or product.raw_values_nbytes
        + product.frequency_mhz_nbytes
        + product.normalized_values_nbytes
        > M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES
        or product.normalization_engine != M37_NORMALIZATION_ENGINE
        or product.normalization_engine_identity_sha256
        != M37_NORMALIZATION_ENGINE_IDENTITY_SHA256
        or product.normalization_contract_sha256
        != M37_NORMALIZATION_CONTRACT_SHA256
        or product.normalization_parameters_sha256
        != M37_NORMALIZATION_PARAMETERS_SHA256
        or product.normalization_block_channels
        != M37_NORMALIZATION_BLOCK_CHANNELS
        or product.normalization_mad_multiplier_float32
        != float(M37_NORMALIZATION_MAD_MULTIPLIER)
        or product.normalization_scale_floor_float32
        != float(M37_NORMALIZATION_SCALE_FLOOR)
    ):
        raise core.V0P6ContractError(
            "normalization engine, parameters, or resource contract changed"
        )
    observed_normalized_digest = _array_sha256(
        product.normalized_values, _F4
    )
    if observed_normalized_digest != product.normalized_values_sha256:
        raise core.V0P6IncompleteError("normalized source values changed")
    if verify_arrays:
        reproduced = normalize_float32_blocks_v0p6(product.raw_values)
        if (
            _array_sha256(reproduced, _F4)
            != product.normalized_values_sha256
            or not np.array_equal(reproduced, product.normalized_values)
        ):
            raise core.V0P6IncompleteError(
                "normalized values do not reproduce from attested raw bytes"
            )
    expected_extraction_record = _expected_extraction_record_from_normalized(
        product
    )
    try:
        embedded_extraction_record = json.loads(
            product.extraction_receipt_record_json
        )
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "embedded extraction receipt is not valid JSON"
        ) from error
    if (
        core.canonical_json_bytes(embedded_extraction_record)
        != product.extraction_receipt_record_json.encode()
        or embedded_extraction_record != expected_extraction_record
    ):
        raise core.V0P6IncompleteError(
            "embedded extraction receipt differs from normalized source"
        )
    observed_extraction_digest = hashlib.sha256(
        core.canonical_json_bytes(expected_extraction_record["payload"])
    ).hexdigest()
    if observed_extraction_digest != product.extraction_receipt_sha256:
        raise core.V0P6IncompleteError(
            "normalized product extraction receipt identity changed"
        )
    if expected_extraction_receipt_sha256 is not None and (
        observed_extraction_digest
        != _sha256(
            expected_extraction_receipt_sha256,
            "independently trusted extraction receipt",
        )
    ):
        raise core.V0P6ContractError(
            "normalized product differs from the trusted extraction receipt"
        )
    payload = _normalized_payload(product)
    observed_product_digest = hashlib.sha256(
        core.canonical_json_bytes(payload)
    ).hexdigest()
    if observed_product_digest != product.product_sha256:
        raise core.V0P6IncompleteError("normalized product identity changed")
    encoded = core.canonical_json_bytes(_normalized_record(product))
    live = _attestation_matches(
        _NORMALIZED_ATTESTATIONS, product, encoded
    )
    trusted = False
    if expected_product_sha256 is not None:
        trusted = observed_product_digest == _sha256(
            expected_product_sha256,
            "independently trusted normalized product",
        )
    if not live and not trusted:
        raise core.V0P6ContractError(
            "normalized product lacks a live or independently trusted receipt"
        )
    return product


def rehydrate_m37_extracted_scan_product(
    raw_values: np.ndarray,
    frequency_mhz_witness: np.ndarray | None,
    scan_definitions: Sequence[Mapping[str, Any]],
    receipt_record: Mapping[str, Any],
    *,
    expected_extraction_receipt_sha256: str,
) -> M37ExtractedScanProduct:
    """Rehydrate persisted raw bytes only against an independent receipt SHA."""
    record = _detached_mapping(receipt_record, "extraction receipt record")
    expected_digest = _sha256(
        expected_extraction_receipt_sha256,
        "independently trusted extraction receipt",
    )
    if set(record) != {"payload", "extraction_receipt_sha256"} or (
        record.get("extraction_receipt_sha256") != expected_digest
    ):
        raise core.V0P6ContractError(
            "persisted extraction record differs from its trusted receipt"
        )
    payload = _detached_mapping(record["payload"], "extraction receipt payload")
    if hashlib.sha256(core.canonical_json_bytes(payload)).hexdigest() != (
        expected_digest
    ):
        raise core.V0P6ContractError(
            "persisted extraction payload differs from its trusted receipt"
        )
    try:
        header = json.loads(payload["expected_header_json"])
    except (KeyError, TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "persisted extraction header is invalid"
        ) from error
    product = attest_m37_extracted_scan(
        raw_values,
        frequency_mhz_witness,
        scan_definitions,
        window_id=payload["window_id"],
        scan_label=payload["scan_label"],
        observed_url=payload["source_url"],
        observed_remote_size_bytes=payload["expected_remote_size_bytes"],
        observed_etag=payload["expected_etag"],
        observed_header=header,
        channel_start=payload["channel_start"],
        channel_stop=payload["channel_stop"],
    )
    if _extracted_record(product) != record or (
        product.extraction_receipt_sha256 != expected_digest
    ):
        raise core.V0P6IncompleteError(
            "rehydrated extraction does not reproduce the trusted record"
        )
    return product


def rehydrate_m37_normalized_scan_product(
    raw_values: np.ndarray,
    frequency_mhz_witness: np.ndarray | None,
    normalized_values_witness: np.ndarray,
    scan_definitions: Sequence[Mapping[str, Any]],
    extraction_receipt_record: Mapping[str, Any],
    product_record: Mapping[str, Any],
    *,
    expected_extraction_receipt_sha256: str,
    expected_product_sha256: str,
) -> M37NormalizedScanProduct:
    """Rehydrate cross-process arrays by recomputing normalization internally."""
    expected_product_digest = _sha256(
        expected_product_sha256, "independently trusted normalized product"
    )
    persisted_product_record = _detached_mapping(
        product_record, "normalized product record"
    )
    if set(persisted_product_record) != {"payload", "product_sha256"} or (
        persisted_product_record.get("product_sha256")
        != expected_product_digest
    ):
        raise core.V0P6ContractError(
            "persisted normalized record differs from its trusted receipt"
        )
    if hashlib.sha256(
        core.canonical_json_bytes(persisted_product_record["payload"])
    ).hexdigest() != expected_product_digest:
        raise core.V0P6ContractError(
            "persisted normalized payload differs from its trusted receipt"
        )
    extracted = rehydrate_m37_extracted_scan_product(
        raw_values,
        frequency_mhz_witness,
        scan_definitions,
        extraction_receipt_record,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
    )
    product = normalize_m37_extracted_scan(
        extracted,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
    )
    witness = np.asarray(normalized_values_witness)
    if (
        witness.dtype != _F4
        or witness.shape != product.normalized_values.shape
        or not witness.flags.c_contiguous
        or _array_sha256(witness, _F4) != product.normalized_values_sha256
        or not np.array_equal(witness, product.normalized_values)
    ):
        raise core.V0P6IncompleteError(
            "persisted normalized values do not reproduce from raw bytes"
        )
    if _normalized_record(product) != persisted_product_record or (
        product.product_sha256 != expected_product_digest
    ):
        raise core.V0P6IncompleteError(
            "rehydrated normalization does not reproduce the trusted record"
        )
    return product


def _plan_from_validated_product(
    product: M37NormalizedScanProduct,
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    width: int,
) -> core.NativeFilterCachePlan:
    validate_m37_source_scan_definitions(scan_definitions)
    width = core._strict_widths((width,))[0]
    if width not in core.M37_SPECTRAL_WIDTHS:
        raise core.V0P6ContractError(
            "production M37 cache width is outside the frozen width bank"
        )
    return core.plan_m37_native_filter_cache(
        product.geometry,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        width,
        window_id=product.window_id,
        scan_label=product.scan_label,
        source_sha256=product.product_sha256,
    )


def plan_m37_production_native_filter_cache(
    product: M37NormalizedScanProduct,
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    width: int,
    *,
    expected_product_sha256: str | None = None,
    expected_extraction_receipt_sha256: str | None = None,
) -> core.NativeFilterCachePlan:
    """Plan an M37 cache only from a live/trusted normalized-scan product."""
    validate_m37_normalized_scan_product(
        product,
        expected_product_sha256=expected_product_sha256,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
        verify_arrays=True,
    )
    return _plan_from_validated_product(
        product,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        width,
    )


def build_m37_production_native_filter_cache(
    product: M37NormalizedScanProduct,
    plan: core.NativeFilterCachePlan,
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    expected_product_sha256: str | None = None,
    expected_extraction_receipt_sha256: str | None = None,
) -> core.NativeFilterCache:
    """Revalidate provenance and normalize-from-raw before native boxcar.

    All planning inputs are repeated so this function can recompute and compare
    the complete plan.  Passing generic normalized/frequency arrays in place
    of ``product`` fails before any boxcar is evaluated.
    """
    validate_m37_normalized_scan_product(
        product,
        expected_product_sha256=expected_product_sha256,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
        verify_arrays=True,
    )
    expected_plan = _plan_from_validated_product(
        product,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        plan.width_channels,
    )
    if plan != expected_plan or plan.source_sha256 != product.product_sha256:
        raise core.V0P6ContractError(
            "production native-cache plan differs from the normalized source"
        )
    # Full reproduction immediately before the native-axis boxcar closes the
    # gap between planning and execution, including any illicit array swap.
    validate_m37_normalized_scan_product(
        product,
        expected_product_sha256=expected_product_sha256,
        expected_extraction_receipt_sha256=(
            expected_extraction_receipt_sha256
        ),
        verify_arrays=True,
    )
    return core.build_native_filter_cache(
        product.normalized_values,
        product.frequency_mhz,
        plan,
    )
