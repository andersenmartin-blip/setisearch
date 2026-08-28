"""Aggregate, restartable inventories for detector-v0.6 native caches."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
from typing import Any, Mapping, Sequence

from . import native_cache_v0p6 as disk_cache
from . import search_v0p6 as core


M37_SCAN_LABELS = (
    "epoch1_on",
    "epoch1_off",
    "epoch2_on",
    "epoch2_off",
    "epoch3_on",
    "epoch3_off",
)
M37_SCAN_KINDS = {
    "epoch1_on": "on",
    "epoch1_off": "off",
    "epoch2_on": "on",
    "epoch2_off": "off",
    "epoch3_on": "on",
    "epoch3_off": "off",
}
_HEX = frozenset("0123456789abcdef")
_MAXIMUM_MANIFEST_BYTES = 64 * 1024 * 1024


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise core.V0P6ContractError(f"{label} is not a lowercase SHA-256")
    return value


def _strict_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise core.V0P6ContractError(f"{label} must be an exact integer")
    return value


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise core.V0P6ContractError("cache logical path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise core.V0P6ContractError("cache logical path escapes the run root")
    canonical = path.as_posix()
    if canonical != value:
        raise core.V0P6ContractError("cache logical path is not canonical")
    return canonical


@dataclass(frozen=True)
class CacheManifestEntry:
    window_id: str
    scan_label: str
    scan_kind: str
    width_channels: int
    relative_path: str
    plan_sha256: str
    cache_manifest_sha256: str
    payload_sha256: str
    payload_nbytes: int
    file_nbytes: int
    source_sha256: str
    plan_record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "scan_label": self.scan_label,
            "scan_kind": self.scan_kind,
            "width_channels": self.width_channels,
            "relative_path": self.relative_path,
            "plan_sha256": self.plan_sha256,
            "cache_manifest_sha256": self.cache_manifest_sha256,
            "payload_sha256": self.payload_sha256,
            "payload_nbytes": self.payload_nbytes,
            "file_nbytes": self.file_nbytes,
            "source_sha256": self.source_sha256,
            "plan_record": self.plan_record,
        }


@dataclass(frozen=True)
class CacheRunManifestReceipt:
    file_sha256: str
    inventory_sha256: str
    factor_bundle_manifest_sha256: str
    entry_count: int
    payload_nbytes: int
    file_nbytes: int


@dataclass(frozen=True)
class CacheRunManifest:
    run_id: str
    entries: tuple[CacheManifestEntry, ...]
    receipt: CacheRunManifestReceipt


def make_cache_manifest_entry(
    relative_path: str,
    plan: core.NativeFilterCachePlan,
    receipt: disk_cache.NativeFilterCacheReceipt,
) -> CacheManifestEntry:
    core.validate_native_filter_cache_plan(plan)
    if not isinstance(receipt, disk_cache.NativeFilterCacheReceipt):
        raise core.V0P6ContractError("cache entry lacks a publication receipt")
    if (
        receipt.plan_sha256 != plan.plan_sha256
        or receipt.payload_nbytes != plan.payload_nbytes
        or receipt.file_nbytes != disk_cache.HEADER_SIZE + plan.payload_nbytes
    ):
        raise core.V0P6IncompleteError("cache entry receipt and plan differ")
    return CacheManifestEntry(
        window_id=plan.window_id,
        scan_label=plan.scan_label,
        scan_kind=plan.scan_kind,
        width_channels=plan.width_channels,
        relative_path=_relative_path(relative_path),
        plan_sha256=plan.plan_sha256,
        cache_manifest_sha256=_sha256(
            receipt.manifest_sha256, "cache manifest identity"
        ),
        payload_sha256=_sha256(receipt.payload_sha256, "cache payload identity"),
        payload_nbytes=plan.payload_nbytes,
        file_nbytes=receipt.file_nbytes,
        source_sha256=plan.source_sha256,
        plan_record=core._native_filter_cache_plan_payload(plan),
    )


def _validate_entry(record: Mapping[str, Any]) -> CacheManifestEntry:
    required = {
        "window_id",
        "scan_label",
        "scan_kind",
        "width_channels",
        "relative_path",
        "plan_sha256",
        "cache_manifest_sha256",
        "payload_sha256",
        "payload_nbytes",
        "file_nbytes",
        "source_sha256",
        "plan_record",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise core.V0P6ContractError("cache-run entry schema changed")
    plan_sha256 = _sha256(record["plan_sha256"], "cache plan identity")
    plan = core.native_filter_cache_plan_from_record(
        record["plan_record"], expected_plan_sha256=plan_sha256
    )
    entry = CacheManifestEntry(
        window_id=str(record["window_id"]),
        scan_label=str(record["scan_label"]),
        scan_kind=str(record["scan_kind"]),
        width_channels=_strict_int(record["width_channels"], "cache width"),
        relative_path=_relative_path(record["relative_path"]),
        plan_sha256=plan_sha256,
        cache_manifest_sha256=_sha256(
            record["cache_manifest_sha256"], "cache manifest identity"
        ),
        payload_sha256=_sha256(record["payload_sha256"], "cache payload identity"),
        payload_nbytes=_strict_int(record["payload_nbytes"], "cache payload bytes"),
        file_nbytes=_strict_int(record["file_nbytes"], "cache file bytes"),
        source_sha256=_sha256(record["source_sha256"], "cache source identity"),
        plan_record=dict(record["plan_record"]),
    )
    if (
        entry.window_id != plan.window_id
        or entry.scan_label != plan.scan_label
        or entry.scan_kind != plan.scan_kind
        or entry.width_channels != plan.width_channels
        or entry.payload_nbytes != plan.payload_nbytes
        or entry.file_nbytes != disk_cache.HEADER_SIZE + plan.payload_nbytes
        or entry.source_sha256 != plan.source_sha256
        or entry.as_record() != dict(record)
    ):
        raise core.V0P6IncompleteError("cache-run entry and plan differ")
    return entry


def _expected_key(entry: CacheManifestEntry) -> tuple[str, str, int]:
    return entry.window_id, entry.scan_label, entry.width_channels


def m37_cache_keys() -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (window_id, scan_label, width)
        for window_id in core.M37_WINDOW_IDS
        for scan_label in M37_SCAN_LABELS
        for width in core.M37_SPECTRAL_WIDTHS
    )


def _atomic_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError("cache-run manifest parent is absent")
    if path.exists():
        raise FileExistsError(path)
    temporary = path.parent / (
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while publishing cache-run manifest")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise FileExistsError(path) from None
        temporary.unlink()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def publish_cache_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[CacheManifestEntry],
    *,
    run_id: str,
    factor_bundle_manifest_sha256: str,
    expected_keys: Sequence[tuple[str, str, int]],
) -> CacheRunManifestReceipt:
    entries = tuple(entries)
    if not isinstance(run_id, str) or not run_id:
        raise core.V0P6ContractError("cache-run manifest run ID is invalid")
    expected = tuple((str(a), str(b), _strict_int(c, "expected cache width")) for a, b, c in expected_keys)
    if tuple(_expected_key(entry) for entry in entries) != expected:
        raise core.V0P6IncompleteError("cache-run inventory is missing, duplicated, or reordered")
    if len({entry.relative_path for entry in entries}) != len(entries):
        raise core.V0P6IncompleteError("cache-run paths are duplicated")
    records = []
    for entry in entries:
        records.append(_validate_entry(entry.as_record()).as_record())
    inventory_sha256 = hashlib.sha256(core.canonical_json_bytes(records)).hexdigest()
    payload_nbytes = sum(entry.payload_nbytes for entry in entries)
    record = {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6-cache-run-manifest-v1",
        "detector_version": core.DETECTOR_VERSION,
        "run_id": run_id,
        "factor_bundle_manifest_sha256": _sha256(
            factor_bundle_manifest_sha256, "factor-bundle manifest identity"
        ),
        "entry_count": len(entries),
        "payload_nbytes": payload_nbytes,
        "inventory_sha256": inventory_sha256,
        "entries": records,
    }
    payload = core.canonical_json_bytes(record)
    if len(payload) > _MAXIMUM_MANIFEST_BYTES:
        raise core.V0P6CapacityError("cache-run manifest exceeds its byte cap")
    _atomic_publish(Path(path), payload)
    return CacheRunManifestReceipt(
        file_sha256=hashlib.sha256(payload).hexdigest(),
        inventory_sha256=inventory_sha256,
        factor_bundle_manifest_sha256=record["factor_bundle_manifest_sha256"],
        entry_count=len(entries),
        payload_nbytes=payload_nbytes,
        file_nbytes=len(payload),
    )


def publish_m37_cache_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[CacheManifestEntry],
    *,
    run_id: str,
    factor_bundle_manifest_sha256: str,
) -> CacheRunManifestReceipt:
    return publish_cache_run_manifest(
        path,
        entries,
        run_id=run_id,
        factor_bundle_manifest_sha256=factor_bundle_manifest_sha256,
        expected_keys=m37_cache_keys(),
    )


def open_cache_run_manifest(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_keys: Sequence[tuple[str, str, int]],
) -> CacheRunManifest:
    manifest_path = Path(path)
    raw = manifest_path.read_bytes()
    if len(raw) > _MAXIMUM_MANIFEST_BYTES:
        raise core.V0P6CapacityError("cache-run manifest exceeds its byte cap")
    file_sha256 = hashlib.sha256(raw).hexdigest()
    if file_sha256 != _sha256(expected_file_sha256, "expected cache-run manifest"):
        raise core.V0P6IncompleteError("cache-run manifest file identity changed")
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError("cache-run manifest is invalid JSON") from error
    if core.canonical_json_bytes(record) != raw or not isinstance(record, dict):
        raise core.V0P6ContractError("cache-run manifest is not canonical JSON")
    required = {
        "schema_version",
        "artifact_type",
        "detector_version",
        "run_id",
        "factor_bundle_manifest_sha256",
        "entry_count",
        "payload_nbytes",
        "inventory_sha256",
        "entries",
    }
    if set(record) != required or (
        record["schema_version"] != 1
        or record["artifact_type"] != "m37-detector-v0p6-cache-run-manifest-v1"
        or record["detector_version"] != core.DETECTOR_VERSION
    ):
        raise core.V0P6ContractError("cache-run manifest schema changed")
    factor_digest = _sha256(
        expected_factor_bundle_manifest_sha256,
        "expected factor-bundle manifest identity",
    )
    if record["factor_bundle_manifest_sha256"] != factor_digest:
        raise core.V0P6IncompleteError("cache-run factor-bundle ancestry changed")
    if not isinstance(record["entries"], list):
        raise core.V0P6ContractError("cache-run entries are invalid")
    entries = tuple(_validate_entry(item) for item in record["entries"])
    expected = tuple((str(a), str(b), _strict_int(c, "expected cache width")) for a, b, c in expected_keys)
    if tuple(_expected_key(entry) for entry in entries) != expected:
        raise core.V0P6IncompleteError("cache-run inventory is missing, duplicated, or reordered")
    if len({entry.relative_path for entry in entries}) != len(entries):
        raise core.V0P6IncompleteError("cache-run paths are duplicated")
    records = [entry.as_record() for entry in entries]
    inventory_sha256 = hashlib.sha256(core.canonical_json_bytes(records)).hexdigest()
    payload_nbytes = sum(entry.payload_nbytes for entry in entries)
    if (
        record["entry_count"] != len(entries)
        or record["payload_nbytes"] != payload_nbytes
        or record["inventory_sha256"] != inventory_sha256
    ):
        raise core.V0P6IncompleteError("cache-run aggregate accounting changed")
    receipt = CacheRunManifestReceipt(
        file_sha256=file_sha256,
        inventory_sha256=inventory_sha256,
        factor_bundle_manifest_sha256=factor_digest,
        entry_count=len(entries),
        payload_nbytes=payload_nbytes,
        file_nbytes=len(raw),
    )
    return CacheRunManifest(run_id=record["run_id"], entries=entries, receipt=receipt)


def verify_cache_run_files(
    root: str | os.PathLike[str], manifest: CacheRunManifest
) -> str:
    """Open and fully hash-verify every cache one at a time."""
    root_path = Path(root).resolve()
    verified: list[dict[str, Any]] = []
    for entry in manifest.entries:
        candidate = (root_path / entry.relative_path).resolve()
        if root_path not in candidate.parents:
            raise core.V0P6ContractError("cache path escapes the run root")
        plan = core.native_filter_cache_plan_from_record(
            entry.plan_record, expected_plan_sha256=entry.plan_sha256
        )
        with disk_cache.open_native_filter_cache(
            candidate,
            expected_plan=plan,
            expected_plan_sha256=entry.plan_sha256,
            expected_manifest_sha256=entry.cache_manifest_sha256,
        ) as handle:
            if handle.payload_sha256 != entry.payload_sha256:
                raise core.V0P6IncompleteError("cache payload receipt changed")
        verified.append(
            {
                "relative_path": entry.relative_path,
                "plan_sha256": entry.plan_sha256,
                "cache_manifest_sha256": entry.cache_manifest_sha256,
                "payload_sha256": entry.payload_sha256,
            }
        )
    return hashlib.sha256(core.canonical_json_bytes(verified)).hexdigest()
