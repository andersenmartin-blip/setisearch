"""Restartable HTTP range store without a remote-sized sparse file.

The M37 archive objects are roughly 12.7 GB each, while the authorized M39
window needs only a small set of HDF5 metadata and chunk ranges.  Some scratch
filesystems charge sparse extents as fully allocated storage.  This module
therefore persists each admitted HTTP range as an immutable content-addressed
blob and presents the collection as a seekable, read-only file object.

Every response remains bound to the preregistered URL, size, ETag and exact
``Content-Range``.  A canonical checkpoint binds remote offsets to blob
digests, and reopening verifies every referenced blob before it is trusted.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import http_range_v0p6 as transport


CHECKPOINT_ARTIFACT = "seti_repeater.m37_immutable_http_range_store"
USER_AGENT = "setisearch-m39-v0p6-range-store/1.0"


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
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while publishing immutable range data")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


class ImmutableRangeStore:
    """Seekable remote view backed only by downloaded immutable range blobs."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        identity: transport.RemoteIdentity,
        *,
        workers: int = transport.DEFAULT_WORKERS,
        timeout: float = 90.0,
        retries: int = transport.MAXIMUM_RETRIES,
        validate_checkpoint_payloads: bool = True,
    ) -> None:
        if not isinstance(identity, transport.RemoteIdentity):
            raise TypeError("identity must be RemoteIdentity")
        if (
            isinstance(workers, bool)
            or not isinstance(workers, int)
            or workers < 1
            or workers > transport.MAXIMUM_WORKERS
        ):
            raise ValueError("range worker count is outside the frozen bound")
        self.root = Path(os.path.abspath(os.fspath(root)))
        if not self.root.parent.is_dir():
            raise FileNotFoundError(self.root.parent)
        self.root.mkdir(exist_ok=True)
        self.blob_root = self.root / "blobs"
        self.blob_root.mkdir(exist_ok=True)
        self.checkpoint_path = self.root / "ranges.json"
        self.identity = identity
        self.workers = workers
        self.timeout = float(timeout)
        self.retries = int(retries)
        if self.timeout <= 0.0 or self.retries < 1:
            raise ValueError("range timeout and retry count must be positive")
        self._lock = threading.RLock()
        self._position = 0
        self._closed = False
        self._segments: list[dict[str, Any]] = []
        self._covered: tuple[transport.ByteRange, ...] = ()
        if self.checkpoint_path.exists():
            self._load_checkpoint(validate_checkpoint_payloads)
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
    def covered_ranges(self) -> tuple[transport.ByteRange, ...]:
        with self._lock:
            return self._covered

    def _blob_path(self, digest: str) -> Path:
        return self.blob_root / f"{digest}.range"

    def _checkpoint_record(self) -> dict[str, Any]:
        segments = sorted(
            self._segments, key=lambda item: (item["start"], item["stop"])
        )
        basis = {
            "artifact_type": CHECKPOINT_ARTIFACT,
            "schema_version": 1,
            "remote": self.identity.record(),
            "segments": segments,
        }
        return {
            **basis,
            "checkpoint_sha256": _sha256_bytes(_canonical_json_bytes(basis)),
        }

    def _publish_checkpoint(self) -> None:
        _write_atomic(
            self.checkpoint_path,
            _canonical_json_bytes(self._checkpoint_record()),
        )

    def _load_checkpoint(self, validate_payloads: bool) -> None:
        raw = self.checkpoint_path.read_bytes()
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("range-store checkpoint is invalid JSON") from error
        if _canonical_json_bytes(record) != raw:
            raise RuntimeError("range-store checkpoint is not canonical JSON")
        checksum = record.get("checkpoint_sha256")
        basis = {
            key: value for key, value in record.items()
            if key != "checkpoint_sha256"
        }
        if checksum != _sha256_bytes(_canonical_json_bytes(basis)):
            raise RuntimeError("range-store checkpoint identity changed")
        if (
            record.get("artifact_type") != CHECKPOINT_ARTIFACT
            or record.get("schema_version") != 1
            or record.get("remote") != self.identity.record()
            or not isinstance(record.get("segments"), list)
        ):
            raise RuntimeError("range-store remote identity or schema changed")
        intervals: list[transport.ByteRange] = []
        segments: list[dict[str, Any]] = []
        for item in record["segments"]:
            if not isinstance(item, Mapping) or set(item) != {
                "sha256", "start", "stop"
            }:
                raise RuntimeError("range-store segment schema changed")
            interval = transport.ByteRange(int(item["start"]), int(item["stop"]))
            if interval.stop > self.identity.size:
                raise RuntimeError("range-store segment exceeds remote size")
            digest = str(item["sha256"])
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise RuntimeError("range-store segment digest is invalid")
            blob = self._blob_path(digest)
            if not blob.is_file() or blob.stat().st_size != interval.length:
                raise RuntimeError("range-store blob is missing or has changed size")
            if validate_payloads and hashlib.sha256(blob.read_bytes()).hexdigest() != digest:
                raise RuntimeError("range-store blob digest changed")
            intervals.append(interval)
            segments.append(
                {"start": interval.start, "stop": interval.stop, "sha256": digest}
            )
        merged = transport._merge_ranges(intervals)
        if sum(item.length for item in intervals) != sum(
            item.length for item in merged
        ):
            raise RuntimeError("range-store segments overlap")
        self._segments = segments
        self._covered = merged

    def _request(self, interval: transport.ByteRange) -> bytes:
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
                match = transport._CONTENT_RANGE.fullmatch(content_range)
                expected = (interval.start, interval.stop - 1, self.identity.size)
                observed = (
                    tuple(int(value) for value in match.groups()) if match else None
                )
                if (
                    status != 206
                    or observed != expected
                    or etag != self.identity.etag
                    or len(payload) != interval.length
                ):
                    raise RuntimeError(
                        "HTTP range response identity or extent changed"
                    )
                return payload
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                RuntimeError,
            ) as error:
                last_error = error
                if attempt + 1 < self.retries:
                    time.sleep(min(2.0 ** attempt, 8.0))
        raise RuntimeError("HTTP range request exhausted its retry budget") from last_error

    def _commit(self, interval: transport.ByteRange, payload: bytes) -> None:
        if len(payload) != interval.length:
            raise RuntimeError("range payload length changed before commit")
        digest = _sha256_bytes(payload)
        with self._lock:
            missing = transport._subtract_covered(interval, self._covered)
            if not missing:
                return
            if missing != (interval,):
                raise RuntimeError("concurrent HTTP range commits overlapped")
            blob = self._blob_path(digest)
            if blob.exists():
                if blob.stat().st_size != len(payload) or _sha256_bytes(
                    blob.read_bytes()
                ) != digest:
                    raise RuntimeError("existing immutable range blob changed")
            else:
                _write_atomic(blob, payload)
            self._segments.append(
                {"start": interval.start, "stop": interval.stop, "sha256": digest}
            )
            self._covered = transport._merge_ranges((*self._covered, interval))
            self._publish_checkpoint()

    def prefetch(self, ranges: Iterable[transport.ByteRange]) -> None:
        requested = transport._merge_ranges(ranges)
        for item in requested:
            if item.stop > self.identity.size:
                raise ValueError("requested byte range exceeds remote size")
        with self._lock:
            missing = tuple(
                gap
                for item in requested
                for gap in transport._subtract_covered(item, self._covered)
            )
        if not missing:
            return

        def fetch(
            interval: transport.ByteRange,
        ) -> tuple[transport.ByteRange, bytes]:
            return interval, self._request(interval)

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for interval, payload in pool.map(fetch, missing):
                self._commit(interval, payload)

    def _ensure(self, interval: transport.ByteRange) -> None:
        with self._lock:
            missing = transport._subtract_covered(interval, self._covered)
        for gap in missing:
            stop = min(
                self.identity.size,
                max(
                    gap.stop,
                    gap.start + transport.ON_DEMAND_READ_AHEAD_BYTES,
                ),
            )
            self.prefetch((transport.ByteRange(gap.start, stop),))

    def _read_covered(self, interval: transport.ByteRange) -> bytes:
        pieces: list[bytes] = []
        cursor = interval.start
        for item in sorted(
            self._segments, key=lambda value: (value["start"], value["stop"])
        ):
            start = int(item["start"])
            stop = int(item["stop"])
            if stop <= cursor:
                continue
            if start > cursor:
                break
            take_stop = min(stop, interval.stop)
            offset = cursor - start
            length = take_stop - cursor
            with self._blob_path(str(item["sha256"])).open("rb") as handle:
                handle.seek(offset)
                payload = handle.read(length)
            if len(payload) != length:
                raise OSError("short read from immutable range blob")
            pieces.append(payload)
            cursor = take_stop
            if cursor >= interval.stop:
                break
        if cursor != interval.stop:
            raise OSError("range-store checkpoint does not cover requested read")
        return b"".join(pieces)

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed range store")
        stop = (
            self.identity.size
            if size is None or size < 0
            else min(self.identity.size, self._position + int(size))
        )
        if stop <= self._position:
            return b""
        interval = transport.ByteRange(self._position, stop)
        self._ensure(interval)
        payload = self._read_covered(interval)
        self._position = stop
        return payload

    def readinto(self, buffer: Any) -> int:
        payload = self.read(len(buffer))
        memoryview(buffer)[:len(payload)] = payload
        return len(payload)

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed range store")
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
        return None

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> "ImmutableRangeStore":
        if self._closed:
            raise ValueError("range store is closed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
