"""Atomic, validated, read-only native-filter caches for detector v0.6.

The artifact format is intentionally small and rigid: a fixed 64-KiB header
followed by one C-order little-endian float32 payload.  Opening a cache always
requires identities supplied independently of the file, validates the full
payload exactly once, and then exposes an O(1)-checked read-only mmap for the
hot gather path.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import mmap
import operator
import os
from pathlib import Path
import stat
import struct
import tempfile
import threading
from typing import Any, Mapping

import numpy as np

from . import search_v0p6 as core


MAGIC = b"SETI-V06-NFC\0\0\0\0"
assert len(MAGIC) == 16

SCHEMA_VERSION = 1
HEADER_SIZE = 65_536
HASH_BLOCK_SIZE = 8 * 1_024 * 1_024
ARTIFACT_TYPE = "seti_repeater.native_filter_cache"
ALGORITHM = "float32-native-boxcar-sliding-sum-v1"

_PREFIX_SIZE = 64
_PAYLOAD_DTYPE = np.dtype("<f4")
_MANIFEST_KEYS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "track_contract",
        "filter_contract",
        "algorithm",
        "plan_sha256",
        "plan",
        "payload",
        "file_nbytes",
    }
)
_PAYLOAD_KEYS = frozenset(
    {
        "offset_bytes",
        "dtype",
        "order",
        "shape",
        "nbytes",
        "sha256",
    }
)


@dataclass(frozen=True)
class NativeFilterCacheReceipt:
    """External identities required to reopen one published cache."""

    path: str
    manifest_sha256: str
    plan_sha256: str
    payload_sha256: str
    payload_nbytes: int
    file_nbytes: int


def _exact_int(value: Any, label: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise core.V0P6ContractError(f"{label} must be an integer, not boolean")
    try:
        return int(operator.index(value))
    except TypeError as error:
        raise core.V0P6ContractError(f"{label} must be an exact integer") from error


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise core.V0P6ContractError(
            f"{label} must be a lowercase SHA-256 digest string"
        )
    digest = value
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise core.V0P6ContractError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return digest


def _manifest_for(
    plan: core.NativeFilterCachePlan,
    payload_sha256: str,
) -> dict[str, Any]:
    core.validate_native_filter_cache_plan(plan)
    payload_sha256 = _sha256(payload_sha256, "cache payload identity")
    file_nbytes = HEADER_SIZE + plan.payload_nbytes
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "track_contract": core.TRACK_CONTRACT,
        "filter_contract": core.FILTER_COORDINATE,
        "algorithm": ALGORITHM,
        "plan_sha256": plan.plan_sha256,
        "plan": core._native_filter_cache_plan_payload(plan),
        "payload": {
            "offset_bytes": HEADER_SIZE,
            "dtype": "<f4",
            "order": "C",
            "shape": list(plan.payload_shape),
            "nbytes": plan.payload_nbytes,
            "sha256": payload_sha256,
        },
        "file_nbytes": file_nbytes,
    }


def _header_for(manifest_bytes: bytes, manifest_sha256: str) -> bytes:
    manifest_sha256 = _sha256(manifest_sha256, "cache manifest identity")
    if not manifest_bytes or len(manifest_bytes) > HEADER_SIZE - _PREFIX_SIZE:
        raise core.V0P6CapacityError(
            "native filter cache manifest does not fit the fixed header"
        )
    header = bytearray(HEADER_SIZE)
    header[0:16] = MAGIC
    struct.pack_into("<I", header, 16, SCHEMA_VERSION)
    struct.pack_into("<I", header, 20, len(manifest_bytes))
    header[24:56] = bytes.fromhex(manifest_sha256)
    # Bytes 56:64 and all unused header bytes deliberately remain zero.
    header[_PREFIX_SIZE : _PREFIX_SIZE + len(manifest_bytes)] = manifest_bytes
    return bytes(header)


def _write_all(file_descriptor: int, values: memoryview) -> None:
    remaining = values
    try:
        while remaining:
            written = os.write(file_descriptor, remaining)
            if written <= 0:
                raise OSError("short write while publishing native filter cache")
            remaining = remaining[written:]
    finally:
        remaining.release()


def _pwrite_all(file_descriptor: int, values: bytes, offset: int) -> None:
    view = memoryview(values)
    try:
        while view:
            written = os.pwrite(file_descriptor, view, offset)
            if written <= 0:
                raise OSError("short header write while publishing cache")
            offset += written
            view = view[written:]
    finally:
        view.release()


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_native_filter_cache(
    path: str | os.PathLike[str],
    cache: core.NativeFilterCache,
) -> NativeFilterCacheReceipt:
    """Publish ``cache`` atomically without ever replacing an existing path.

    A hidden temporary inode is created in the destination directory.  The
    payload is streamed once while its hash and finiteness are checked, the
    completed file is fsynced, and ``link(2)`` performs the no-overwrite commit.
    """
    if not isinstance(cache, core.NativeFilterCache):
        raise core.V0P6ContractError(
            "publication requires an in-memory NativeFilterCache"
        )
    plan = cache.plan
    core.validate_native_filter_cache_plan(plan)
    expected_payload_sha256 = _sha256(
        cache.payload_sha256, "in-memory cache payload identity"
    )
    values = np.asarray(cache.values)
    if values.flags.writeable:
        raise core.V0P6IncompleteError(
            "in-memory native filter cache is not sealed read-only"
        )
    if (
        values.dtype != _PAYLOAD_DTYPE
        or not values.flags.c_contiguous
        or values.shape != plan.payload_shape
        or values.nbytes != plan.payload_nbytes
    ):
        raise core.V0P6ContractError(
            "in-memory native filter cache does not match its <f4 C-order plan"
        )

    final_path = Path(os.path.abspath(os.fspath(path)))
    parent = final_path.parent
    if not parent.is_dir():
        raise core.V0P6ContractError(
            "native filter cache destination directory does not exist"
        )

    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{final_path.name}.", suffix=".tmp", dir=parent
    )
    temporary_path = Path(temporary_name)
    linked = False
    payload_hasher = hashlib.sha256()
    try:
        fcntl.flock(temporary_fd, fcntl.LOCK_EX)
        os.lseek(temporary_fd, HEADER_SIZE, os.SEEK_SET)
        flat = values.reshape(-1)
        elements_per_block = HASH_BLOCK_SIZE // _PAYLOAD_DTYPE.itemsize
        for start in range(0, flat.size, elements_per_block):
            stop = min(start + elements_per_block, flat.size)
            block_values = flat[start:stop]
            if not np.all(np.isfinite(block_values)):
                raise core.V0P6ContractError(
                    "native filter cache payload contains non-finite values"
                )
            block = memoryview(block_values).cast("B")
            payload_hasher.update(block)
            _write_all(temporary_fd, block)

        payload_sha256 = payload_hasher.hexdigest()
        if payload_sha256 != expected_payload_sha256:
            raise core.V0P6IncompleteError(
                "in-memory native filter cache payload SHA-256 changed"
            )
        manifest = _manifest_for(plan, payload_sha256)
        manifest_bytes = core.canonical_json_bytes(manifest)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        header = _header_for(manifest_bytes, manifest_sha256)
        _pwrite_all(temporary_fd, header, 0)
        expected_file_nbytes = HEADER_SIZE + plan.payload_nbytes
        if os.fstat(temporary_fd).st_size != expected_file_nbytes:
            raise core.V0P6IncompleteError(
                "published native filter cache has an unexpected file size"
            )
        os.fchmod(temporary_fd, 0o444)
        os.fsync(temporary_fd)
        os.close(temporary_fd)
        temporary_fd = -1

        # Reopen through the production verifier before the atomic link is
        # allowed to make this inode visible at its final name.
        with open_native_filter_cache(
            temporary_path,
            expected_plan=plan,
            expected_plan_sha256=plan.plan_sha256,
            expected_manifest_sha256=manifest_sha256,
        ):
            pass

        # Hard-link publication is atomic and fails with FileExistsError when
        # the destination already exists.  Unlike replace(), it cannot clobber.
        os.link(temporary_path, final_path, follow_symlinks=False)
        linked = True
        _fsync_directory(parent)
        temporary_path.unlink()
        _fsync_directory(parent)
        return NativeFilterCacheReceipt(
            path=str(final_path),
            manifest_sha256=manifest_sha256,
            plan_sha256=plan.plan_sha256,
            payload_sha256=payload_sha256,
            payload_nbytes=plan.payload_nbytes,
            file_nbytes=expected_file_nbytes,
        )
    finally:
        if temporary_fd >= 0:
            os.close(temporary_fd)
        if temporary_path.exists():
            temporary_path.unlink()
            if linked:
                _fsync_directory(parent)


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise core.V0P6ContractError(
                f"native filter cache manifest repeats key {key!r}"
            )
        result[key] = value
    return result


def _read_exact(file_descriptor: int, count: int, offset: int = 0) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.pread(file_descriptor, remaining, offset)
        if not chunk:
            raise core.V0P6IncompleteError(
                "native filter cache ended before its fixed header"
            )
        chunks.append(chunk)
        offset += len(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _parse_header(
    header: bytes,
    *,
    expected_manifest_sha256: str,
) -> tuple[Mapping[str, Any], str]:
    if len(header) != HEADER_SIZE:
        raise core.V0P6IncompleteError("native filter cache header is incomplete")
    if header[0:16] != MAGIC:
        raise core.V0P6ContractError("native filter cache magic is invalid")
    schema_version = struct.unpack_from("<I", header, 16)[0]
    if schema_version != SCHEMA_VERSION:
        raise core.V0P6ContractError(
            "native filter cache prefix schema version is unsupported"
        )
    manifest_length = struct.unpack_from("<I", header, 20)[0]
    if manifest_length < 1 or manifest_length > HEADER_SIZE - _PREFIX_SIZE:
        raise core.V0P6ContractError(
            "native filter cache manifest length is invalid"
        )
    if header[56:64] != b"\0" * 8:
        raise core.V0P6ContractError(
            "native filter cache reserved prefix bytes are nonzero"
        )
    manifest_end = _PREFIX_SIZE + manifest_length
    if any(header[manifest_end:]):
        raise core.V0P6ContractError(
            "native filter cache header padding is nonzero"
        )
    embedded_sha256 = header[24:56].hex()
    if embedded_sha256 != expected_manifest_sha256:
        raise core.V0P6ContractError(
            "cache manifest SHA-256 differs from the independently supplied identity"
        )
    manifest_bytes = header[_PREFIX_SIZE:manifest_end]
    observed_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if observed_sha256 != expected_manifest_sha256:
        raise core.V0P6IncompleteError(
            "native filter cache manifest bytes changed"
        )
    try:
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                core.V0P6ContractError(
                    f"native filter cache manifest contains {value}"
                )
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "native filter cache manifest is not valid canonical JSON"
        ) from error
    if not isinstance(manifest, dict):
        raise core.V0P6ContractError(
            "native filter cache manifest must be a JSON object"
        )
    try:
        canonical = core.canonical_json_bytes(manifest)
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "native filter cache manifest cannot be canonicalized"
        ) from error
    if canonical != manifest_bytes:
        raise core.V0P6ContractError(
            "native filter cache manifest bytes are not canonical JSON"
        )
    return manifest, observed_sha256


def _validate_manifest(
    manifest: Mapping[str, Any],
    *,
    expected_plan: core.NativeFilterCachePlan,
    expected_plan_sha256: str,
    observed_file_nbytes: int,
) -> str:
    if frozenset(manifest) != _MANIFEST_KEYS:
        raise core.V0P6ContractError(
            "native filter cache manifest fields do not match schema 1"
        )
    exact_scalars = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "track_contract": core.TRACK_CONTRACT,
        "filter_contract": core.FILTER_COORDINATE,
        "algorithm": ALGORITHM,
        "plan_sha256": expected_plan_sha256,
        "file_nbytes": HEADER_SIZE + expected_plan.payload_nbytes,
    }
    for key, expected in exact_scalars.items():
        observed = manifest[key]
        if type(observed) is not type(expected) or observed != expected:
            raise core.V0P6ContractError(
                f"native filter cache manifest field {key!r} changed"
            )
    expected_plan_payload = core._native_filter_cache_plan_payload(expected_plan)
    if core.canonical_json_bytes(manifest["plan"]) != core.canonical_json_bytes(
        expected_plan_payload
    ):
        raise core.V0P6ContractError(
            "native filter cache embedded plan differs from the expected plan"
        )
    payload = manifest["payload"]
    if not isinstance(payload, dict) or frozenset(payload) != _PAYLOAD_KEYS:
        raise core.V0P6ContractError(
            "native filter cache payload manifest fields do not match schema 1"
        )
    expected_payload = {
        "offset_bytes": HEADER_SIZE,
        "dtype": "<f4",
        "order": "C",
        "shape": list(expected_plan.payload_shape),
        "nbytes": expected_plan.payload_nbytes,
        "sha256": _sha256(payload["sha256"], "manifest payload identity"),
    }
    if core.canonical_json_bytes(payload) != core.canonical_json_bytes(
        expected_payload
    ):
        raise core.V0P6ContractError(
            "native filter cache payload fields changed"
        )
    payload_sha256 = expected_payload["sha256"]
    expected_file_nbytes = HEADER_SIZE + expected_plan.payload_nbytes
    if observed_file_nbytes != expected_file_nbytes:
        raise core.V0P6IncompleteError(
            "native filter cache file size differs from its expected plan"
        )
    return payload_sha256


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(metadata.st_nlink),
        int(metadata.st_uid),
        int(metadata.st_gid),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(metadata.st_ctime_ns),
    )


def _validate_payload_stream(
    mapping: mmap.mmap,
    *,
    payload_nbytes: int,
    expected_payload_sha256: str,
) -> None:
    """Hash and check every payload float in one sequential pass."""
    hasher = hashlib.sha256()
    payload_stop = HEADER_SIZE + payload_nbytes
    for start in range(HEADER_SIZE, payload_stop, HASH_BLOCK_SIZE):
        stop = min(start + HASH_BLOCK_SIZE, payload_stop)
        block = memoryview(mapping)[start:stop]
        try:
            hasher.update(block)
            values = np.frombuffer(block, dtype=_PAYLOAD_DTYPE)
            try:
                if not np.all(np.isfinite(values)):
                    raise core.V0P6IncompleteError(
                        "native filter cache payload contains non-finite values"
                    )
            finally:
                del values
        finally:
            block.release()
    if hasher.hexdigest() != expected_payload_sha256:
        raise core.V0P6IncompleteError(
            "native filter cache payload SHA-256 changed"
        )


class DiskNativeFilterCache:
    """Validated read-only mmap with O(1) identity checks before each gather."""

    def __init__(
        self,
        *,
        path: Path,
        plan: core.NativeFilterCachePlan,
        manifest_sha256: str,
        payload_sha256: str,
        file_descriptor: int,
        mapping: mmap.mmap,
        values: np.ndarray,
        stat_signature: tuple[int, ...],
        arena: NativeFilterCacheArena | None,
    ) -> None:
        self.path = path
        self.plan = plan
        self.manifest_sha256 = manifest_sha256
        self.payload_sha256 = payload_sha256
        self._file_descriptor = file_descriptor
        self._mapping = mapping
        self._values: np.ndarray | None = values
        self._stat_signature = stat_signature
        self._arena = arena
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _values_for_gather(self) -> np.ndarray:
        """Return the mmap after constant-time fd/path stat validation."""
        if self._closed or self._values is None:
            raise core.V0P6IncompleteError("native filter cache handle is closed")
        try:
            descriptor_metadata = os.fstat(self._file_descriptor)
            path_metadata = os.stat(self.path, follow_symlinks=False)
        except OSError as error:
            raise core.V0P6IncompleteError(
                "native filter cache path or descriptor is no longer available"
            ) from error
        if (
            not stat.S_ISREG(descriptor_metadata.st_mode)
            or _stat_signature(descriptor_metadata) != self._stat_signature
            or _stat_signature(path_metadata) != self._stat_signature
        ):
            raise core.V0P6IncompleteError(
                "native filter cache stat identity changed after validation"
            )
        return self._values

    def close(self) -> None:
        """Close the mmap and release any arena reservation."""
        if self._closed:
            return
        mapping = self._mapping
        self._values = None
        try:
            mapping.close()
        except BufferError as error:
            self._values = np.ndarray(
                shape=self.plan.payload_shape,
                dtype=_PAYLOAD_DTYPE,
                buffer=mapping,
                offset=HEADER_SIZE,
                order="C",
            )
            self._values.setflags(write=False)
            raise core.V0P6IncompleteError(
                "native filter cache values are still borrowed by a gather"
            ) from error
        os.close(self._file_descriptor)
        self._closed = True
        if self._arena is not None:
            arena = self._arena
            self._arena = None
            arena._release(self)

    def __enter__(self) -> DiskNativeFilterCache:
        if self._closed:
            raise core.V0P6IncompleteError("native filter cache handle is closed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class NativeFilterCacheArena:
    """Bound the total payload bytes mapped by a group of cache handles."""

    def __init__(self, maximum_mapped_bytes: int) -> None:
        maximum = _exact_int(maximum_mapped_bytes, "maximum mapped bytes")
        if maximum < 1:
            raise core.V0P6ContractError(
                "maximum mapped bytes must be positive"
            )
        self.maximum_mapped_bytes = maximum
        self._mapped_bytes = 0
        self._handles: set[DiskNativeFilterCache] = set()
        self._closed = False
        self._lock = threading.RLock()

    @property
    def mapped_bytes(self) -> int:
        with self._lock:
            return self._mapped_bytes

    @property
    def handle_count(self) -> int:
        with self._lock:
            return len(self._handles)

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def _reserve(self, payload_nbytes: int) -> None:
        payload_nbytes = _exact_int(payload_nbytes, "mapped payload byte count")
        with self._lock:
            if self._closed:
                raise core.V0P6IncompleteError(
                    "native filter cache arena is closed"
                )
            if self._mapped_bytes + payload_nbytes > self.maximum_mapped_bytes:
                raise core.V0P6CapacityError(
                    "native filter cache arena byte cap would be exceeded"
                )
            self._mapped_bytes += payload_nbytes

    def _adopt(self, handle: DiskNativeFilterCache) -> None:
        with self._lock:
            if self._closed:
                raise core.V0P6IncompleteError(
                    "native filter cache arena closed during open"
                )
            self._handles.add(handle)

    def _cancel_reservation(self, payload_nbytes: int) -> None:
        with self._lock:
            self._mapped_bytes -= payload_nbytes
            if self._mapped_bytes < 0:
                raise AssertionError("native cache arena reservation underflow")

    def _release(self, handle: DiskNativeFilterCache) -> None:
        with self._lock:
            if handle in self._handles:
                self._handles.remove(handle)
                self._mapped_bytes -= handle.plan.payload_nbytes
            if self._mapped_bytes < 0:
                raise AssertionError("native cache arena reservation underflow")

    def close(self) -> None:
        with self._lock:
            if self._closed and not self._handles:
                return
            self._closed = True
            handles = tuple(self._handles)
        for handle in handles:
            handle.close()

    def __enter__(self) -> NativeFilterCacheArena:
        with self._lock:
            if self._closed:
                raise core.V0P6IncompleteError(
                    "native filter cache arena is closed"
                )
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def open_native_filter_cache(
    path: str | os.PathLike[str],
    *,
    expected_plan: core.NativeFilterCachePlan,
    expected_plan_sha256: str,
    expected_manifest_sha256: str,
    arena: NativeFilterCacheArena | None = None,
) -> DiskNativeFilterCache:
    """Open, fully validate once, and mmap one published cache read-only."""
    core.validate_native_filter_cache_plan(expected_plan)
    expected_plan_sha256 = _sha256(
        expected_plan_sha256, "independently supplied cache-plan identity"
    )
    expected_manifest_sha256 = _sha256(
        expected_manifest_sha256, "independently supplied cache-manifest identity"
    )
    if expected_plan.plan_sha256 != expected_plan_sha256:
        raise core.V0P6ContractError(
            "expected plan differs from the independently supplied plan SHA-256"
        )
    if arena is not None and not isinstance(arena, NativeFilterCacheArena):
        raise core.V0P6ContractError(
            "cache arena must be a NativeFilterCacheArena"
        )

    payload_nbytes = expected_plan.payload_nbytes
    reservation_active = False
    if arena is not None:
        arena._reserve(payload_nbytes)
        reservation_active = True

    cache_path = Path(os.path.abspath(os.fspath(path)))
    file_descriptor = -1
    mapping: mmap.mmap | None = None
    handle: DiskNativeFilterCache | None = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        file_descriptor = os.open(cache_path, flags)
        fcntl.flock(file_descriptor, fcntl.LOCK_SH)
        initial_metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(initial_metadata.st_mode):
            raise core.V0P6ContractError(
                "native filter cache path must name a regular file"
            )
        if initial_metadata.st_mode & (
            stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        ):
            raise core.V0P6ContractError(
                "native filter cache must have no write permission bits"
            )
        path_metadata = os.stat(cache_path, follow_symlinks=False)
        if _stat_signature(path_metadata) != _stat_signature(initial_metadata):
            raise core.V0P6IncompleteError(
                "native filter cache path changed while it was opened"
            )

        header = _read_exact(file_descriptor, HEADER_SIZE)
        manifest, manifest_sha256 = _parse_header(
            header,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        payload_sha256 = _validate_manifest(
            manifest,
            expected_plan=expected_plan,
            expected_plan_sha256=expected_plan_sha256,
            observed_file_nbytes=initial_metadata.st_size,
        )
        mapping = mmap.mmap(file_descriptor, 0, access=mmap.ACCESS_READ)
        _validate_payload_stream(
            mapping,
            payload_nbytes=payload_nbytes,
            expected_payload_sha256=payload_sha256,
        )

        final_metadata = os.fstat(file_descriptor)
        final_path_metadata = os.stat(cache_path, follow_symlinks=False)
        signature = _stat_signature(initial_metadata)
        if (
            _stat_signature(final_metadata) != signature
            or _stat_signature(final_path_metadata) != signature
        ):
            raise core.V0P6IncompleteError(
                "native filter cache changed during full validation"
            )
        values = np.ndarray(
            shape=expected_plan.payload_shape,
            dtype=_PAYLOAD_DTYPE,
            buffer=mapping,
            offset=HEADER_SIZE,
            order="C",
        )
        values.setflags(write=False)
        handle = DiskNativeFilterCache(
            path=cache_path,
            plan=expected_plan,
            manifest_sha256=manifest_sha256,
            payload_sha256=payload_sha256,
            file_descriptor=file_descriptor,
            mapping=mapping,
            values=values,
            stat_signature=signature,
            arena=arena,
        )
        del values
        if arena is not None:
            arena._adopt(handle)
            reservation_active = False
        file_descriptor = -1
        mapping = None
        return handle
    except Exception:
        if handle is not None:
            handle._arena = None
            try:
                handle.close()
            except Exception:
                pass
            file_descriptor = -1
            mapping = None
        else:
            if mapping is not None:
                mapping.close()
            if file_descriptor >= 0:
                os.close(file_descriptor)
        if reservation_active and arena is not None:
            arena._cancel_reservation(payload_nbytes)
        raise
