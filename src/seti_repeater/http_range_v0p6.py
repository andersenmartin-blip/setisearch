"""Restartable, identity-bound sparse HTTP range mirrors for M37 HDF5.

Only byte ranges whose response identity and ``Content-Range`` exactly match
the preregistered remote object are admitted.  Every committed segment is
hashed, fsynced and recorded in a canonical checkpoint, so interrupted runs
resume without treating sparse holes as downloaded zero bytes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_WORKERS = 6
MAXIMUM_WORKERS = 16
ON_DEMAND_READ_AHEAD_BYTES = 4 * 1024 * 1024
HDF5_METADATA_PREFIX_BYTES = 64 * 1024 * 1024
MAXIMUM_RETRIES = 5
USER_AGENT = "setisearch-m37-v0p6-range/1.0"
CHECKPOINT_ARTIFACT = "seti_repeater.m37_sparse_http_mirror"
RANGE_PLAN_ARTIFACT = "seti_repeater.m37_hdf5_range_plan"
_CONTENT_RANGE = re.compile(r"^bytes ([0-9]+)-([0-9]+)/([0-9]+)$")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_atomic(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(temporary, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while publishing range checkpoint")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@dataclass(frozen=True, order=True)
class ByteRange:
    """Half-open byte interval ``[start, stop)``."""

    start: int
    stop: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.start, bool)
            or isinstance(self.stop, bool)
            or not isinstance(self.start, int)
            or not isinstance(self.stop, int)
            or self.start < 0
            or self.stop <= self.start
        ):
            raise ValueError("byte range must be a nonempty nonnegative interval")

    @property
    def length(self) -> int:
        return self.stop - self.start


@dataclass(frozen=True)
class RemoteIdentity:
    url: str
    size: int
    etag: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.url, str)
            or not self.url.startswith(("http://", "https://"))
            or isinstance(self.size, bool)
            or not isinstance(self.size, int)
            or self.size < 1
            or not isinstance(self.etag, str)
            or not self.etag
        ):
            raise ValueError("remote identity is incomplete")

    def record(self) -> dict[str, Any]:
        return {"etag": self.etag, "size": self.size, "url": self.url}


def remote_identity(url: str, *, timeout: float = 90.0) -> RemoteIdentity:
    """Read the exact size/ETag identity without fetching a payload."""
    request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        size_value = response.headers.get("Content-Length")
        etag = response.headers.get("ETag")
        accepts = str(response.headers.get("Accept-Ranges", ""))
    if size_value is None or etag is None or "bytes" not in accepts.lower():
        raise RuntimeError("remote object lacks exact size, ETag, or byte ranges")
    return RemoteIdentity(url=url, size=int(size_value), etag=str(etag))


def _merge_ranges(ranges: Iterable[ByteRange]) -> tuple[ByteRange, ...]:
    ordered = sorted(ranges)
    merged: list[ByteRange] = []
    for item in ordered:
        if merged and item.start <= merged[-1].stop:
            merged[-1] = ByteRange(merged[-1].start, max(merged[-1].stop, item.stop))
        else:
            merged.append(item)
    return tuple(merged)


def _subtract_covered(item: ByteRange, covered: Sequence[ByteRange]) -> tuple[ByteRange, ...]:
    cursor = item.start
    missing: list[ByteRange] = []
    for segment in covered:
        if segment.stop <= cursor:
            continue
        if segment.start >= item.stop:
            break
        if segment.start > cursor:
            missing.append(ByteRange(cursor, min(segment.start, item.stop)))
        cursor = max(cursor, segment.stop)
        if cursor >= item.stop:
            break
    if cursor < item.stop:
        missing.append(ByteRange(cursor, item.stop))
    return tuple(missing)


class SparseRangeMirror:
    """Seekable file object backed by a restartable local sparse mirror."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        identity: RemoteIdentity,
        *,
        workers: int = DEFAULT_WORKERS,
        timeout: float = 90.0,
        retries: int = MAXIMUM_RETRIES,
        validate_checkpoint_payloads: bool = True,
    ) -> None:
        if not isinstance(identity, RemoteIdentity):
            raise TypeError("identity must be RemoteIdentity")
        if (
            isinstance(workers, bool)
            or not isinstance(workers, int)
            or workers < 1
            or workers > MAXIMUM_WORKERS
        ):
            raise ValueError("range worker count is outside the frozen bound")
        self.path = Path(os.path.abspath(os.fspath(path)))
        self.checkpoint_path = self.path.with_suffix(self.path.suffix + ".ranges.json")
        self.identity = identity
        self.workers = workers
        self.timeout = float(timeout)
        self.retries = int(retries)
        if self.timeout <= 0.0 or self.retries < 1:
            raise ValueError("range timeout and retry count must be positive")
        if not self.path.parent.is_dir():
            raise FileNotFoundError(self.path.parent)
        self._lock = threading.RLock()
        self._position = 0
        self._closed = False
        self._segments: list[dict[str, Any]] = []
        self._covered: tuple[ByteRange, ...] = ()
        flags = os.O_RDWR | os.O_CREAT
        self._descriptor = os.open(self.path, flags, 0o600)
        if os.fstat(self._descriptor).st_size == 0:
            os.ftruncate(self._descriptor, identity.size)
            os.fsync(self._descriptor)
        elif os.fstat(self._descriptor).st_size != identity.size:
            os.close(self._descriptor)
            raise RuntimeError("sparse mirror size differs from remote identity")
        if self.checkpoint_path.exists():
            self._load_checkpoint(validate_checkpoint_payloads)
        elif any(os.pread(self._descriptor, 1, 0)):
            os.close(self._descriptor)
            raise RuntimeError("uncheckpointed sparse mirror is not admissible")
        else:
            self._publish_checkpoint()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def downloaded_bytes(self) -> int:
        with self._lock:
            return sum(item.length for item in self._covered)

    @property
    def covered_ranges(self) -> tuple[ByteRange, ...]:
        with self._lock:
            return self._covered

    def _checkpoint_record(self) -> dict[str, Any]:
        segments = sorted(self._segments, key=lambda item: (item["start"], item["stop"]))
        basis = {
            "artifact_type": CHECKPOINT_ARTIFACT,
            "schema_version": 1,
            "remote": self.identity.record(),
            "segments": segments,
        }
        return {**basis, "checkpoint_sha256": _sha256_bytes(_canonical_json_bytes(basis))}

    def _publish_checkpoint(self) -> None:
        _write_atomic(self.checkpoint_path, _canonical_json_bytes(self._checkpoint_record()))

    def _load_checkpoint(self, validate_payloads: bool) -> None:
        raw = self.checkpoint_path.read_bytes()
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("range checkpoint is invalid JSON") from error
        if _canonical_json_bytes(record) != raw:
            raise RuntimeError("range checkpoint is not canonical JSON")
        checksum = record.get("checkpoint_sha256")
        basis = {key: value for key, value in record.items() if key != "checkpoint_sha256"}
        if checksum != _sha256_bytes(_canonical_json_bytes(basis)):
            raise RuntimeError("range checkpoint identity changed")
        if (
            record.get("artifact_type") != CHECKPOINT_ARTIFACT
            or record.get("schema_version") != 1
            or record.get("remote") != self.identity.record()
            or not isinstance(record.get("segments"), list)
        ):
            raise RuntimeError("range checkpoint remote identity or schema changed")
        segments: list[dict[str, Any]] = []
        intervals: list[ByteRange] = []
        for item in record["segments"]:
            if not isinstance(item, Mapping) or set(item) != {"sha256", "start", "stop"}:
                raise RuntimeError("range checkpoint segment schema changed")
            interval = ByteRange(int(item["start"]), int(item["stop"]))
            if interval.stop > self.identity.size:
                raise RuntimeError("range checkpoint exceeds remote size")
            digest = str(item["sha256"])
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise RuntimeError("range checkpoint segment digest is invalid")
            if validate_payloads:
                payload = os.pread(self._descriptor, interval.length, interval.start)
                if len(payload) != interval.length or _sha256_bytes(payload) != digest:
                    raise RuntimeError("range checkpoint payload digest changed")
            intervals.append(interval)
            segments.append({"start": interval.start, "stop": interval.stop, "sha256": digest})
        merged = _merge_ranges(intervals)
        if sum(item.length for item in intervals) != sum(item.length for item in merged):
            raise RuntimeError("range checkpoint segments overlap")
        self._segments = segments
        self._covered = merged

    def _request(self, interval: ByteRange) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            request = Request(
                self.identity.url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Range": f"bytes={interval.start}-{interval.stop - 1}",
                    "If-Range": self.identity.etag,
                    "Accept-Encoding": "identity",
                },
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    status = int(getattr(response, "status", response.getcode()))
                    content_range = str(response.headers.get("Content-Range", ""))
                    etag = response.headers.get("ETag")
                    payload = response.read()
                match = _CONTENT_RANGE.fullmatch(content_range)
                expected = (interval.start, interval.stop - 1, self.identity.size)
                observed = tuple(int(value) for value in match.groups()) if match else None
                if (
                    status != 206
                    or observed != expected
                    or etag != self.identity.etag
                    or len(payload) != interval.length
                ):
                    raise RuntimeError("HTTP range response identity or extent changed")
                return payload
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as error:
                last_error = error
                if attempt + 1 < self.retries:
                    time.sleep(min(2.0 ** attempt, 8.0))
        raise RuntimeError("HTTP range request exhausted its retry budget") from last_error

    def _commit(self, interval: ByteRange, payload: bytes) -> None:
        digest = _sha256_bytes(payload)
        with self._lock:
            missing = _subtract_covered(interval, self._covered)
            if not missing:
                return
            if missing != (interval,):
                raise RuntimeError("concurrent HTTP range commits overlapped")
            written = os.pwrite(self._descriptor, payload, interval.start)
            if written != len(payload):
                raise OSError("short write into sparse range mirror")
            os.fsync(self._descriptor)
            self._segments.append(
                {"start": interval.start, "stop": interval.stop, "sha256": digest}
            )
            self._covered = _merge_ranges((*self._covered, interval))
            self._publish_checkpoint()

    def prefetch(self, ranges: Iterable[ByteRange]) -> None:
        """Fetch all currently missing portions concurrently and checkpoint them."""
        requested = _merge_ranges(ranges)
        for item in requested:
            if item.stop > self.identity.size:
                raise ValueError("requested byte range exceeds remote size")
        with self._lock:
            missing = tuple(
                gap
                for item in requested
                for gap in _subtract_covered(item, self._covered)
            )
        if not missing:
            return

        def fetch(interval: ByteRange) -> tuple[ByteRange, bytes]:
            return interval, self._request(interval)

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for interval, payload in pool.map(fetch, missing):
                self._commit(interval, payload)

    def _ensure(self, interval: ByteRange) -> None:
        with self._lock:
            missing = _subtract_covered(interval, self._covered)
        for gap in missing:
            stop = min(self.identity.size, max(gap.stop, gap.start + ON_DEMAND_READ_AHEAD_BYTES))
            self.prefetch((ByteRange(gap.start, stop),))

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed sparse mirror")
        if size is None or size < 0:
            stop = self.identity.size
        else:
            stop = min(self.identity.size, self._position + int(size))
        if stop <= self._position:
            return b""
        interval = ByteRange(self._position, stop)
        self._ensure(interval)
        payload = os.pread(self._descriptor, interval.length, interval.start)
        if len(payload) != interval.length:
            raise OSError("short read from sparse range mirror")
        self._position = stop
        return payload

    def readinto(self, buffer: Any) -> int:
        payload = self.read(len(buffer))
        memoryview(buffer)[: len(payload)] = payload
        return len(payload)

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed sparse mirror")
        if whence == os.SEEK_SET:
            position = int(offset)
        elif whence == os.SEEK_CUR:
            position = self._position + int(offset)
        elif whence == os.SEEK_END:
            position = self.identity.size + int(offset)
        else:
            raise ValueError("invalid seek origin")
        if position < 0:
            raise ValueError("negative seek position")
        self._position = position
        return position

    def tell(self) -> int:
        return self._position

    def readable(self) -> bool:
        return not self._closed

    def seekable(self) -> bool:
        return not self._closed

    def flush(self) -> None:
        if not self._closed:
            os.fsync(self._descriptor)

    def close(self) -> None:
        if self._closed:
            return
        os.close(self._descriptor)
        self._closed = True

    def __enter__(self) -> "SparseRangeMirror":
        if self._closed:
            raise ValueError("sparse mirror is closed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def discover_hdf5_chunk_ranges(
    dataset: Any,
    channel_intervals: Sequence[tuple[int, int]],
) -> tuple[ByteRange, ...]:
    """Return exact allocated chunk byte extents for rank-3 M37 hyperslabs."""
    if len(dataset.shape) != 3 or dataset.chunks is None:
        raise RuntimeError("M37 dataset is not a rank-3 chunked dataset")
    if tuple(dataset.chunks[:2]) != (1, 1):
        raise RuntimeError("M37 dataset time/beam chunk geometry changed")
    width = int(dataset.chunks[2])
    ranges: set[ByteRange] = set()
    for start, stop in channel_intervals:
        if start < 0 or stop <= start or stop > int(dataset.shape[2]):
            raise ValueError("HDF5 channel interval is outside the dataset")
        first = start // width
        last = (stop - 1) // width
        for integration in range(int(dataset.shape[0])):
            for chunk_index in range(first, last + 1):
                info = dataset.id.get_chunk_info_by_coord(
                    (integration, 0, chunk_index * width)
                )
                byte_offset = int(info.byte_offset)
                byte_size = int(info.size)
                if byte_offset < 0 or byte_size < 1:
                    raise RuntimeError("M37 HDF5 chunk is unallocated")
                ranges.add(ByteRange(byte_offset, byte_offset + byte_size))
    return tuple(sorted(ranges))


def range_plan_record(
    identity: RemoteIdentity,
    *,
    dataset_shape: Sequence[int],
    dataset_chunks: Sequence[int],
    channel_intervals: Sequence[tuple[int, int]],
    ranges: Sequence[ByteRange],
) -> dict[str, Any]:
    basis = {
        "artifact_type": RANGE_PLAN_ARTIFACT,
        "schema_version": 1,
        "remote": identity.record(),
        "dataset_shape": [int(item) for item in dataset_shape],
        "dataset_chunks": [int(item) for item in dataset_chunks],
        "channel_intervals": [[int(start), int(stop)] for start, stop in channel_intervals],
        "ranges": [[item.start, item.stop] for item in ranges],
        "range_count": len(ranges),
        "payload_nbytes": sum(item.length for item in ranges),
    }
    return {**basis, "range_plan_sha256": _sha256_bytes(_canonical_json_bytes(basis))}


def publish_range_plan(path: str | os.PathLike[str], record: Mapping[str, Any]) -> str:
    """Publish one immutable canonical range plan, or verify an exact restart."""
    destination = Path(path)
    payload = _canonical_json_bytes(dict(record))
    digest = _sha256_bytes(payload)
    if destination.exists():
        if destination.read_bytes() != payload:
            raise RuntimeError("existing HDF5 range plan differs from restart")
        return digest
    _write_atomic(destination, payload)
    return digest
