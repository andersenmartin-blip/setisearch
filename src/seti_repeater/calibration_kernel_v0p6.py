"""Verified native kernel for the frozen M37 null-calibration statistic.

The wrapper is intentionally strict: it never coerces an input array, never
allocates rolled score grids, and refuses to execute if the C source, ABI, or
algorithm identity differs from the reviewed implementation.  Compilation is
local and lazy so an installed package does not need to contain a prebuilt,
platform-specific shared object.
"""

from __future__ import annotations

from ctypes import (
    CDLL,
    POINTER,
    c_char_p,
    c_double,
    c_float,
    c_int,
    c_int64,
    c_size_t,
    c_uint8,
)
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from typing import Final

import numpy as np

from .search_v0p6 import M37_LIVE_NDARRAY_CAP_BYTES, V0P6ContractError


class CalibrationKernelUnavailableError(RuntimeError):
    """Raised when the reviewed native implementation cannot be loaded."""


class CalibrationKernelContractError(V0P6ContractError):
    """Raised before the ABI is called when an array contract is violated."""


_ROOT: Final = Path(__file__).resolve().parent
_SOURCE: Final = _ROOT / "calibration_kernel_v0p6.c"
_EXPECTED_C_SOURCE_SHA256: Final = (
    "ec05a98d21bb89b9011a14d91c6e7f048dbb748b2d5cd3aac5c15561571c1457"
)
_ABI_TAG: Final = "seti-repeater-m37-null-maxima-abi-v1"
_EXPECTED_ABI_SHA256: Final = (
    "6ffddd3681d5fa1c1024339322073934c9baa2c3902a2bb4f9f060bd8570784d"
)
_ALGORITHM_SPEC: Final = """seti-repeater M37 null-scramble maxima algorithm v1
input: C-contiguous native float32[3,q] finite vectors
mask: C-contiguous bool[3,q], rolled with its epoch
shifts: C-contiguous native int64[n,3], positive np.roll semantics
subsets: (0,1),(0,2),(1,2),(0,1,2), in that order
statistic: float32 minimum_epoch times float32 sqrt(active-count)
floor: every active epoch >= float32(3.0)
mask: reject when any active epoch is masked
nonfinite score: replace with negative infinity
output: float64[n] exact promotion of each float32 cross-subset maximum
parallelism: one independent scramble per OpenMP iteration
"""
_EXPECTED_ALGORITHM_SHA256: Final = (
    "50c45eb3c8fa3e28fdc25e63e45356b7ad7f31995fd44b11eb0a82ef5f7accae"
)
_COMPILER_FLAGS: Final = (
    "-O3",
    "-std=c11",
    "-march=native",
    "-fopenmp",
    "-fPIC",
    "-shared",
    "-fno-fast-math",
    "-ffp-contract=off",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Wpedantic",
)
_MAX_EXPLICIT_THREADS: Final = 1_024
_MINIMUM_FINITE_OUTPUT: Final = float.fromhex("0x1.0f876c0000000p+2")


@dataclass(frozen=True)
class CalibrationKernelIdentity:
    """Runtime attestation for the exact source/toolchain/shared object."""

    source_sha256: str
    abi_tag: str
    abi_sha256: str
    algorithm_sha256: str
    compiler_path: str
    compiler_sha256: str
    compiler_version: str
    compiler_flags: tuple[str, ...]
    library_sha256: str
    openmp_version: int
    openmp_max_threads: int
    identity_sha256: str


_LOAD_LOCK = threading.Lock()
_LOADED_LIBRARY: CDLL | None = None
_LOADED_IDENTITY: CalibrationKernelIdentity | None = None
_BUILD_DIRECTORY: tempfile.TemporaryDirectory[str] | None = None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validated_source_bytes() -> bytes:
    try:
        payload = _SOURCE.read_bytes()
    except OSError as error:
        raise CalibrationKernelUnavailableError(
            f"M37 calibration kernel source is unavailable: {_SOURCE}"
        ) from error
    digest = _sha256(payload)
    if digest != _EXPECTED_C_SOURCE_SHA256:
        raise CalibrationKernelUnavailableError(
            "M37 calibration kernel source SHA-256 changed: "
            f"{digest} != {_EXPECTED_C_SOURCE_SHA256}"
        )
    algorithm_digest = _sha256(_ALGORITHM_SPEC.encode("utf-8"))
    if algorithm_digest != _EXPECTED_ALGORITHM_SHA256:
        raise CalibrationKernelUnavailableError(
            "M37 calibration algorithm specification SHA-256 changed"
        )
    if _sha256(_ABI_TAG.encode("ascii")) != _EXPECTED_ABI_SHA256:
        raise CalibrationKernelUnavailableError(
            "M37 calibration ABI tag SHA-256 changed"
        )
    return payload


def _compiler_identity() -> tuple[str, str, str]:
    compiler = shutil.which("cc")
    if compiler is None:
        raise CalibrationKernelUnavailableError(
            "a C/OpenMP toolchain named 'cc' is required"
        )
    compiler_path = str(Path(compiler).resolve())
    try:
        compiler_sha256 = _sha256(Path(compiler_path).read_bytes())
        completed = subprocess.run(
            [compiler_path, "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CalibrationKernelUnavailableError(
            "the C/OpenMP compiler identity could not be verified"
        ) from error
    first_line = completed.stdout.splitlines()
    if not first_line:
        raise CalibrationKernelUnavailableError(
            "the C/OpenMP compiler returned no version identity"
        )
    return compiler_path, compiler_sha256, first_line[0]


def _configure_library(library: CDLL) -> None:
    for name in (
        "m37_calibration_kernel_abi",
        "m37_calibration_kernel_source_sha256",
        "m37_calibration_kernel_algorithm_sha256",
    ):
        function = getattr(library, name)
        function.argtypes = []
        function.restype = c_char_p
    library.m37_calibration_kernel_openmp_version.argtypes = []
    library.m37_calibration_kernel_openmp_version.restype = c_int
    library.m37_calibration_kernel_max_threads.argtypes = []
    library.m37_calibration_kernel_max_threads.restype = c_int
    function = library.m37_calibration_null_maxima
    function.argtypes = [
        POINTER(c_float),
        POINTER(c_uint8),
        POINTER(c_int64),
        c_size_t,
        c_size_t,
        c_int,
        POINTER(c_double),
    ]
    function.restype = c_int


def _decoded_tag(library: CDLL, function_name: str) -> str:
    raw = getattr(library, function_name)()
    if raw is None:
        raise CalibrationKernelUnavailableError(
            f"native library returned a null {function_name} identity"
        )
    try:
        return raw.decode("ascii")
    except (AttributeError, UnicodeDecodeError) as error:
        raise CalibrationKernelUnavailableError(
            f"native library returned an invalid {function_name} identity"
        ) from error


def _require_identity_tags(
    abi_tag: str,
    source_sha256: str,
    algorithm_sha256: str,
) -> None:
    if abi_tag != _ABI_TAG:
        raise CalibrationKernelUnavailableError(
            f"native calibration ABI changed: {abi_tag!r} != {_ABI_TAG!r}"
        )
    if _sha256(abi_tag.encode("ascii")) != _EXPECTED_ABI_SHA256:
        raise CalibrationKernelUnavailableError(
            "native calibration ABI hash changed"
        )
    if source_sha256 != _EXPECTED_C_SOURCE_SHA256:
        raise CalibrationKernelUnavailableError(
            "native calibration source identity changed"
        )
    if algorithm_sha256 != _EXPECTED_ALGORITHM_SHA256:
        raise CalibrationKernelUnavailableError(
            "native calibration algorithm identity changed"
        )


def _identity_digest(payload: dict[str, object]) -> str:
    return _sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    )


def _validate_runtime_identity(identity: CalibrationKernelIdentity) -> None:
    payload = asdict(identity)
    claimed_digest = payload.pop("identity_sha256")
    if _identity_digest(payload) != claimed_digest:
        raise CalibrationKernelUnavailableError(
            "in-memory calibration-kernel identity changed"
        )
    _require_identity_tags(
        identity.abi_tag,
        identity.source_sha256,
        identity.algorithm_sha256,
    )
    if (
        identity.abi_sha256 != _EXPECTED_ABI_SHA256
        or identity.compiler_flags != _COMPILER_FLAGS
        or len(identity.compiler_sha256) != 64
        or len(identity.library_sha256) != 64
        or identity.openmp_version < 201_107
        or identity.openmp_max_threads < 1
    ):
        raise CalibrationKernelUnavailableError(
            "in-memory calibration-kernel runtime identity changed"
        )


def _compile_and_load() -> tuple[CDLL, CalibrationKernelIdentity]:
    global _BUILD_DIRECTORY

    source_payload = _validated_source_bytes()
    compiler_path, compiler_sha256, compiler_version = _compiler_identity()
    build_directory = tempfile.TemporaryDirectory(
        prefix="seti-repeater-m37-calibration-"
    )
    build_root = Path(build_directory.name)
    source_copy = build_root / "calibration_kernel_v0p6.c"
    library_path = build_root / "calibration_kernel_v0p6.so"
    try:
        source_copy.write_bytes(source_payload)
        command = [
            compiler_path,
            *_COMPILER_FLAGS,
            (
                "-DM37_CALIBRATION_SOURCE_SHA256="
                f"\"{_EXPECTED_C_SOURCE_SHA256}\""
            ),
            (
                "-DM37_CALIBRATION_ALGORITHM_SHA256="
                f"\"{_EXPECTED_ALGORITHM_SHA256}\""
            ),
            str(source_copy),
            "-o",
            str(library_path),
            "-lm",
        ]
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.stderr.strip():
            raise CalibrationKernelUnavailableError(
                "the reviewed C source compiled with unexpected diagnostics: "
                + completed.stderr.strip()
            )
        library_payload = library_path.read_bytes()
        library = CDLL(str(library_path))
        _configure_library(library)
        abi_tag = _decoded_tag(library, "m37_calibration_kernel_abi")
        source_sha256 = _decoded_tag(
            library, "m37_calibration_kernel_source_sha256"
        )
        algorithm_sha256 = _decoded_tag(
            library, "m37_calibration_kernel_algorithm_sha256"
        )
        _require_identity_tags(abi_tag, source_sha256, algorithm_sha256)
        openmp_version = int(library.m37_calibration_kernel_openmp_version())
        openmp_max_threads = int(library.m37_calibration_kernel_max_threads())
        if openmp_version < 201_107 or openmp_max_threads < 1:
            raise CalibrationKernelUnavailableError(
                "native calibration library lacks a usable OpenMP runtime"
            )
        partial: dict[str, object] = {
            "source_sha256": source_sha256,
            "abi_tag": abi_tag,
            "abi_sha256": _EXPECTED_ABI_SHA256,
            "algorithm_sha256": algorithm_sha256,
            "compiler_path": compiler_path,
            "compiler_sha256": compiler_sha256,
            "compiler_version": compiler_version,
            "compiler_flags": _COMPILER_FLAGS,
            "library_sha256": _sha256(library_payload),
            "openmp_version": openmp_version,
            "openmp_max_threads": openmp_max_threads,
        }
        identity = CalibrationKernelIdentity(
            **partial,
            identity_sha256=_identity_digest(partial),
        )
    except CalibrationKernelUnavailableError:
        build_directory.cleanup()
        raise
    except (OSError, subprocess.SubprocessError) as error:
        build_directory.cleanup()
        raise CalibrationKernelUnavailableError(
            "the reviewed C/OpenMP calibration library could not be built or loaded"
        ) from error
    _BUILD_DIRECTORY = build_directory
    return library, identity


def _library_and_identity() -> tuple[CDLL, CalibrationKernelIdentity]:
    global _LOADED_LIBRARY, _LOADED_IDENTITY

    # Rechecking the tiny source on every entry makes post-load source changes
    # fail closed too; the actual native image lives in a private temp directory.
    _validated_source_bytes()
    if _LOADED_LIBRARY is None or _LOADED_IDENTITY is None:
        with _LOAD_LOCK:
            if _LOADED_LIBRARY is None or _LOADED_IDENTITY is None:
                _LOADED_LIBRARY, _LOADED_IDENTITY = _compile_and_load()
    _validate_runtime_identity(_LOADED_IDENTITY)
    return _LOADED_LIBRARY, _LOADED_IDENTITY


def calibration_kernel_identity() -> CalibrationKernelIdentity:
    """Return the attested runtime/toolchain identity, compiling if needed."""
    _, identity = _library_and_identity()
    return identity


def _require_exact_array(
    value: object,
    *,
    name: str,
    dtype: np.dtype,
    ndim: int,
) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise CalibrationKernelContractError(f"{name} must be a NumPy array")
    if value.dtype != dtype or not value.dtype.isnative:
        raise CalibrationKernelContractError(
            f"{name} must have exact native dtype {dtype}"
        )
    if value.ndim != ndim:
        raise CalibrationKernelContractError(
            f"{name} must have exactly {ndim} dimensions"
        )
    if not value.flags.c_contiguous or not value.flags.aligned:
        raise CalibrationKernelContractError(
            f"{name} must be aligned and C-contiguous"
        )
    return value


def _require_live_array_cap(arrays: tuple[np.ndarray, ...]) -> int:
    live_bytes = sum(int(array.nbytes) for array in arrays)
    if live_bytes > M37_LIVE_NDARRAY_CAP_BYTES:
        raise CalibrationKernelContractError(
            "calibration kernel live-array budget exceeds the frozen "
            f"{M37_LIVE_NDARRAY_CAP_BYTES}-byte cap"
        )
    return live_bytes


def _validate_output(output: np.ndarray) -> None:
    if np.any(np.isnan(output)) or np.any(np.isposinf(output)):
        raise CalibrationKernelUnavailableError(
            "native calibration kernel returned NaN or positive infinity"
        )
    finite = np.isfinite(output)
    if np.any(output[finite] < _MINIMUM_FINITE_OUTPUT):
        raise CalibrationKernelUnavailableError(
            "native calibration output lies below the frozen two-epoch floor"
        )
    if np.any(output[finite] != output[finite].astype(np.float32).astype(np.float64)):
        raise CalibrationKernelUnavailableError(
            "native calibration output is not an exact float32 promotion"
        )


def m37_null_scramble_maxima(
    epoch_vectors: np.ndarray,
    exclusion_mask: np.ndarray,
    scramble_shifts: np.ndarray,
    *,
    thread_count: int | None = None,
    out: np.ndarray | None = None,
) -> np.ndarray:
    """Compute one maximum per scramble for the frozen M37 score contract.

    Positive shifts have exactly ``np.roll(row, shift)`` semantics.  Negative
    infinity is a valid result when every cell is masked or below the floor;
    NaN and positive infinity always fail closed.
    """
    vectors = _require_exact_array(
        epoch_vectors,
        name="epoch vectors",
        dtype=np.dtype(np.float32),
        ndim=2,
    )
    mask = _require_exact_array(
        exclusion_mask,
        name="exclusion mask",
        dtype=np.dtype(np.bool_),
        ndim=2,
    )
    shifts = _require_exact_array(
        scramble_shifts,
        name="scramble shifts",
        dtype=np.dtype(np.int64),
        ndim=2,
    )
    if vectors.shape[0] != 3 or vectors.shape[1] < 1:
        raise CalibrationKernelContractError(
            "epoch vectors must have shape [3, positive-q]"
        )
    if mask.shape != vectors.shape:
        raise CalibrationKernelContractError(
            "exclusion mask must have the epoch-vector shape"
        )
    if shifts.shape[0] < 1 or shifts.shape[1] != 3:
        raise CalibrationKernelContractError(
            "scramble shifts must have shape [positive-n, 3]"
        )
    q = int(vectors.shape[1])
    scramble_count = int(shifts.shape[0])
    if out is None:
        output = np.empty(scramble_count, dtype=np.float64)
    else:
        output = _require_exact_array(
            out,
            name="output",
            dtype=np.dtype(np.float64),
            ndim=1,
        )
        if output.shape != (scramble_count,) or not output.flags.writeable:
            raise CalibrationKernelContractError(
                "output must be writable with one cell per scramble"
            )
    _require_live_array_cap((vectors, mask, shifts, output))
    if not np.all(np.isfinite(vectors)):
        raise CalibrationKernelContractError(
            "epoch vectors must contain only finite float32 values"
        )
    if np.any(shifts < 0) or np.any(shifts >= q):
        raise CalibrationKernelContractError(
            "every scramble shift must lie in [0, q)"
        )
    if any(
        np.shares_memory(output, item)
        for item in (vectors, mask, shifts)
    ):
        raise CalibrationKernelContractError(
            "output must not overlap an input array"
        )

    library, identity = _library_and_identity()
    if thread_count is None:
        threads = min(
            identity.openmp_max_threads,
            scramble_count,
            _MAX_EXPLICIT_THREADS,
        )
    else:
        if (
            isinstance(thread_count, (bool, np.bool_))
            or not isinstance(thread_count, (int, np.integer))
        ):
            raise CalibrationKernelContractError(
                "thread count must be an exact integer"
            )
        threads = int(thread_count)
        if threads < 1 or threads > _MAX_EXPLICIT_THREADS:
            raise CalibrationKernelContractError(
                f"thread count must lie in [1, {_MAX_EXPLICIT_THREADS}]"
            )
    output.fill(np.nan)
    status = int(
        library.m37_calibration_null_maxima(
            vectors.ctypes.data_as(POINTER(c_float)),
            mask.ctypes.data_as(POINTER(c_uint8)),
            shifts.ctypes.data_as(POINTER(c_int64)),
            q,
            scramble_count,
            threads,
            output.ctypes.data_as(POINTER(c_double)),
        )
    )
    if status != 0:
        output.fill(np.nan)
        raise CalibrationKernelUnavailableError(
            f"native calibration kernel failed closed with status {status}"
        )
    _validate_output(output)
    return output


__all__ = [
    "CalibrationKernelContractError",
    "CalibrationKernelIdentity",
    "CalibrationKernelUnavailableError",
    "calibration_kernel_identity",
    "m37_null_scramble_maxima",
]
