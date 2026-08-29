"""Restartable run inventory for per-window physical resource artifacts.

The physical resource artifact is intentionally window-scoped.  This module
joins an independently ordered window inventory under one run, cache manifest,
factor bundle and ON-retention inventory, and reopens every child file before
returning a trusted run-level receipt.

Importing this module does not open telescope data or artifact files.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
from typing import Any, Mapping, Sequence

from . import physical_resource_v0p6 as physical
from . import search_v0p6 as core


PHYSICAL_RESOURCE_RUN_MANIFEST_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_physical_resource_run_manifest"
)
PHYSICAL_RESOURCE_RUN_MANIFEST_SCHEMA_VERSION = 1
PHYSICAL_RESOURCE_RUN_MANIFEST_MAXIMUM_BYTES = 4_194_304
_HEX = frozenset("0123456789abcdef")
_ENTRY_FIELDS = frozenset(
    {
        "window_id",
        "relative_path",
        "artifact_file_sha256",
        "resource_envelope_sha256",
        "on_retention_certificate_sha256",
        "artifact_file_nbytes",
        "maximum_process_mapped_bytes",
        "aggregate_peak_mapped_bytes",
        "aggregate_peak_handle_count",
        "aggregate_batch_count",
        "aggregate_opened_cache_count",
    }
)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "detector_version",
        "run_id",
        "window_ids",
        "window_count",
        "cache_run_manifest_file_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_inventory_sha256",
        "resource_artifact_inventory_sha256",
        "maximum_process_mapped_bytes",
        "maximum_window_peak_mapped_bytes",
        "maximum_window_peak_handle_count",
        "total_batch_count",
        "total_opened_cache_count",
        "total_artifact_file_nbytes",
        "entries",
        "manifest_sha256",
    }
)


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


def _window_ids(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise core.V0P6ContractError("resource-run window inventory is invalid")
    result = tuple(values)
    if (
        not result
        or any(not isinstance(value, str) or not value for value in result)
        or len(set(result)) != len(result)
    ):
        raise core.V0P6ContractError("resource-run window inventory is invalid")
    return result


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise core.V0P6ContractError("resource artifact path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise core.V0P6ContractError(
            "resource artifact path escapes the run root"
        )
    canonical = path.as_posix()
    if canonical != value:
        raise core.V0P6ContractError(
            "resource artifact path is not canonical"
        )
    return canonical


@dataclass(frozen=True)
class PhysicalResourceRunEntry:
    window_id: str
    relative_path: str
    artifact_file_sha256: str
    resource_envelope_sha256: str
    on_retention_certificate_sha256: str
    artifact_file_nbytes: int
    maximum_process_mapped_bytes: int
    aggregate_peak_mapped_bytes: int
    aggregate_peak_handle_count: int
    aggregate_batch_count: int
    aggregate_opened_cache_count: int

    def as_record(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "relative_path": self.relative_path,
            "artifact_file_sha256": self.artifact_file_sha256,
            "resource_envelope_sha256": self.resource_envelope_sha256,
            "on_retention_certificate_sha256": (
                self.on_retention_certificate_sha256
            ),
            "artifact_file_nbytes": self.artifact_file_nbytes,
            "maximum_process_mapped_bytes": (
                self.maximum_process_mapped_bytes
            ),
            "aggregate_peak_mapped_bytes": self.aggregate_peak_mapped_bytes,
            "aggregate_peak_handle_count": self.aggregate_peak_handle_count,
            "aggregate_batch_count": self.aggregate_batch_count,
            "aggregate_opened_cache_count": self.aggregate_opened_cache_count,
        }


@dataclass(frozen=True)
class PhysicalResourceRunManifestReceipt:
    file_sha256: str
    manifest_sha256: str
    resource_artifact_inventory_sha256: str
    on_retention_inventory_sha256: str
    run_id: str
    cache_run_manifest_file_sha256: str
    factor_bundle_manifest_sha256: str
    window_count: int
    maximum_process_mapped_bytes: int
    maximum_window_peak_mapped_bytes: int
    maximum_window_peak_handle_count: int
    total_batch_count: int
    total_opened_cache_count: int
    total_artifact_file_nbytes: int
    file_nbytes: int


@dataclass(frozen=True)
class PhysicalResourceRunManifest:
    entries: tuple[PhysicalResourceRunEntry, ...]
    artifacts: tuple[physical.PhysicalResourceArtifact, ...]
    receipt: PhysicalResourceRunManifestReceipt


def _entry_from_artifact(
    relative_path: str,
    artifact: physical.PhysicalResourceArtifact,
) -> PhysicalResourceRunEntry:
    if not isinstance(artifact, physical.PhysicalResourceArtifact):
        raise core.V0P6ContractError(
            "resource-run entry lacks an opened artifact"
        )
    if not isinstance(
        artifact.receipt, physical.PhysicalResourceArtifactReceipt
    ):
        raise core.V0P6ContractError(
            "resource-run entry lacks an artifact receipt"
        )
    validated = physical.validate_physical_resource_envelope(
        artifact.envelope,
        expected_envelope_sha256=(
            artifact.receipt.resource_envelope_sha256
        ),
    )
    raw = core.canonical_json_bytes(validated)
    receipt = artifact.receipt
    if (
        receipt.file_sha256 != hashlib.sha256(raw).hexdigest()
        or receipt.file_nbytes != len(raw)
        or receipt.run_id != validated["run_id"]
        or receipt.window_id != validated["window_id"]
        or receipt.cache_run_manifest_file_sha256
        != validated["cache_run_manifest_file_sha256"]
        or receipt.factor_bundle_manifest_sha256
        != validated["factor_bundle_manifest_sha256"]
        or receipt.on_retention_certificate_sha256
        != validated["on_retention_certificate_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "resource artifact and receipt differ"
        )
    return PhysicalResourceRunEntry(
        window_id=receipt.window_id,
        relative_path=_relative_path(relative_path),
        artifact_file_sha256=receipt.file_sha256,
        resource_envelope_sha256=receipt.resource_envelope_sha256,
        on_retention_certificate_sha256=(
            receipt.on_retention_certificate_sha256
        ),
        artifact_file_nbytes=receipt.file_nbytes,
        maximum_process_mapped_bytes=validated[
            "maximum_process_mapped_bytes"
        ],
        aggregate_peak_mapped_bytes=validated[
            "aggregate_peak_mapped_bytes"
        ],
        aggregate_peak_handle_count=validated[
            "aggregate_peak_handle_count"
        ],
        aggregate_batch_count=validated["aggregate_batch_count"],
        aggregate_opened_cache_count=validated[
            "aggregate_opened_cache_count"
        ],
    )


def make_physical_resource_run_entry(
    relative_path: str,
    artifact: physical.PhysicalResourceArtifact,
) -> PhysicalResourceRunEntry:
    """Bind one canonical relative path to one opened child artifact."""
    return _entry_from_artifact(relative_path, artifact)


def _validate_entry(record: Mapping[str, Any]) -> PhysicalResourceRunEntry:
    if not isinstance(record, Mapping) or set(record) != _ENTRY_FIELDS:
        raise core.V0P6ContractError("resource-run entry schema changed")
    window_id = record["window_id"]
    if not isinstance(window_id, str) or not window_id:
        raise core.V0P6ContractError("resource-run window ID is invalid")
    entry = PhysicalResourceRunEntry(
        window_id=window_id,
        relative_path=_relative_path(record["relative_path"]),
        artifact_file_sha256=_sha256(
            record["artifact_file_sha256"], "resource artifact file identity"
        ),
        resource_envelope_sha256=_sha256(
            record["resource_envelope_sha256"],
            "resource envelope identity",
        ),
        on_retention_certificate_sha256=_sha256(
            record["on_retention_certificate_sha256"],
            "ON-retention certificate identity",
        ),
        artifact_file_nbytes=_strict_int(
            record["artifact_file_nbytes"], "resource artifact bytes"
        ),
        maximum_process_mapped_bytes=_strict_int(
            record["maximum_process_mapped_bytes"],
            "resource mapped-byte cap",
        ),
        aggregate_peak_mapped_bytes=_strict_int(
            record["aggregate_peak_mapped_bytes"],
            "resource mapped-byte peak",
        ),
        aggregate_peak_handle_count=_strict_int(
            record["aggregate_peak_handle_count"],
            "resource handle peak",
        ),
        aggregate_batch_count=_strict_int(
            record["aggregate_batch_count"], "resource batch count"
        ),
        aggregate_opened_cache_count=_strict_int(
            record["aggregate_opened_cache_count"],
            "resource opened-cache count",
        ),
    )
    if (
        entry.artifact_file_nbytes <= 0
        or entry.artifact_file_nbytes
        > physical.PHYSICAL_RESOURCE_ARTIFACT_MAXIMUM_BYTES
        or entry.maximum_process_mapped_bytes <= 0
        or entry.aggregate_peak_mapped_bytes < 0
        or entry.aggregate_peak_mapped_bytes
        > entry.maximum_process_mapped_bytes
        or entry.aggregate_peak_handle_count < 0
        or entry.aggregate_batch_count < 0
        or entry.aggregate_opened_cache_count < 0
        or entry.as_record() != dict(record)
    ):
        raise core.V0P6IncompleteError(
            "resource-run entry accounting changed"
        )
    return entry


def _entry_sequence(
    entries: Sequence[PhysicalResourceRunEntry],
) -> tuple[PhysicalResourceRunEntry, ...]:
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        raise core.V0P6ContractError("resource-run entries are invalid")
    validated: list[PhysicalResourceRunEntry] = []
    for entry in entries:
        if not isinstance(entry, PhysicalResourceRunEntry):
            raise core.V0P6ContractError(
                "resource-run entry lacks a validated receipt"
            )
        validated.append(_validate_entry(entry.as_record()))
    return tuple(validated)


def on_retention_inventory_sha256(
    entries: Sequence[PhysicalResourceRunEntry],
) -> str:
    """Hash the ordered per-window ON-retention ancestry."""
    validated = _entry_sequence(entries)
    inventory = [
        {
            "window_id": entry.window_id,
            "on_retention_certificate_sha256": (
                entry.on_retention_certificate_sha256
            ),
        }
        for entry in validated
    ]
    return hashlib.sha256(core.canonical_json_bytes(inventory)).hexdigest()


def _validated_entries(
    entries: Sequence[PhysicalResourceRunEntry],
    expected_window_ids: Sequence[str],
) -> tuple[PhysicalResourceRunEntry, ...]:
    expected = _window_ids(expected_window_ids)
    validated = _entry_sequence(entries)
    if tuple(entry.window_id for entry in validated) != expected:
        raise core.V0P6IncompleteError(
            "resource-run window inventory is missing, duplicated, or reordered"
        )
    if len({entry.relative_path for entry in validated}) != len(validated):
        raise core.V0P6IncompleteError(
            "resource-run artifact paths are duplicated"
        )
    return validated


def _candidate_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative_path).resolve()
    if resolved_root not in candidate.parents:
        raise core.V0P6ContractError(
            "resource artifact path escapes the run root"
        )
    return candidate


def _open_child(
    root: Path,
    entry: PhysicalResourceRunEntry,
    *,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    require_m37: bool,
) -> physical.PhysicalResourceArtifact:
    opener = (
        physical.open_m37_physical_resource_artifact
        if require_m37
        else physical.open_physical_resource_artifact
    )
    artifact = opener(
        _candidate_path(root, entry.relative_path),
        expected_file_sha256=entry.artifact_file_sha256,
        expected_envelope_sha256=entry.resource_envelope_sha256,
        expected_run_id=expected_run_id,
        expected_cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_certificate_sha256=(
            entry.on_retention_certificate_sha256
        ),
    )
    if _entry_from_artifact(entry.relative_path, artifact) != entry:
        raise core.V0P6IncompleteError(
            "resource-run entry and child artifact differ"
        )
    return artifact


def _aggregate_record(
    entries: tuple[PhysicalResourceRunEntry, ...],
    *,
    run_id: str,
    cache_run_manifest_file_sha256: str,
    factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not run_id or len(run_id) > 128:
        raise core.V0P6ContractError("resource-run ID is invalid")
    records = [entry.as_record() for entry in entries]
    retention_sha256 = on_retention_inventory_sha256(entries)
    if retention_sha256 != _sha256(
        expected_on_retention_inventory_sha256,
        "expected ON-retention inventory identity",
    ):
        raise core.V0P6IncompleteError(
            "resource-run ON-retention inventory changed"
        )
    caps = {entry.maximum_process_mapped_bytes for entry in entries}
    if len(caps) != 1:
        raise core.V0P6IncompleteError(
            "resource-run windows do not share one mapped-byte cap"
        )
    record = {
        "schema_version": PHYSICAL_RESOURCE_RUN_MANIFEST_SCHEMA_VERSION,
        "artifact_type": PHYSICAL_RESOURCE_RUN_MANIFEST_ARTIFACT_TYPE,
        "detector_version": core.DETECTOR_VERSION,
        "run_id": run_id,
        "window_ids": [entry.window_id for entry in entries],
        "window_count": len(entries),
        "cache_run_manifest_file_sha256": _sha256(
            cache_run_manifest_file_sha256,
            "cache-run manifest file identity",
        ),
        "factor_bundle_manifest_sha256": _sha256(
            factor_bundle_manifest_sha256,
            "factor-bundle manifest identity",
        ),
        "on_retention_inventory_sha256": retention_sha256,
        "resource_artifact_inventory_sha256": hashlib.sha256(
            core.canonical_json_bytes(records)
        ).hexdigest(),
        "maximum_process_mapped_bytes": next(iter(caps)),
        "maximum_window_peak_mapped_bytes": max(
            entry.aggregate_peak_mapped_bytes for entry in entries
        ),
        "maximum_window_peak_handle_count": max(
            entry.aggregate_peak_handle_count for entry in entries
        ),
        "total_batch_count": sum(
            entry.aggregate_batch_count for entry in entries
        ),
        "total_opened_cache_count": sum(
            entry.aggregate_opened_cache_count for entry in entries
        ),
        "total_artifact_file_nbytes": sum(
            entry.artifact_file_nbytes for entry in entries
        ),
        "entries": records,
    }
    record["manifest_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(record)
    ).hexdigest()
    return record


def _receipt(
    raw: bytes, record: Mapping[str, Any]
) -> PhysicalResourceRunManifestReceipt:
    return PhysicalResourceRunManifestReceipt(
        file_sha256=hashlib.sha256(raw).hexdigest(),
        manifest_sha256=record["manifest_sha256"],
        resource_artifact_inventory_sha256=record[
            "resource_artifact_inventory_sha256"
        ],
        on_retention_inventory_sha256=record[
            "on_retention_inventory_sha256"
        ],
        run_id=record["run_id"],
        cache_run_manifest_file_sha256=record[
            "cache_run_manifest_file_sha256"
        ],
        factor_bundle_manifest_sha256=record[
            "factor_bundle_manifest_sha256"
        ],
        window_count=record["window_count"],
        maximum_process_mapped_bytes=record[
            "maximum_process_mapped_bytes"
        ],
        maximum_window_peak_mapped_bytes=record[
            "maximum_window_peak_mapped_bytes"
        ],
        maximum_window_peak_handle_count=record[
            "maximum_window_peak_handle_count"
        ],
        total_batch_count=record["total_batch_count"],
        total_opened_cache_count=record["total_opened_cache_count"],
        total_artifact_file_nbytes=record["total_artifact_file_nbytes"],
        file_nbytes=len(raw),
    )


def _atomic_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError(
            "resource-run manifest parent directory is absent"
        )
    if path.exists():
        raise FileExistsError(path)
    temporary = path.parent / (
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError(
                    "short write while publishing resource-run manifest"
                )
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise FileExistsError(path) from None
        temporary.unlink()
        parent_descriptor = os.open(
            path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def publish_physical_resource_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[PhysicalResourceRunEntry],
    *,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> PhysicalResourceRunManifestReceipt:
    """Publish a complete ordered run inventory after reopening every child."""
    validated = _validated_entries(entries, expected_window_ids)
    manifest_path = Path(path)
    for entry in validated:
        _open_child(
            manifest_path.parent,
            entry,
            expected_run_id=expected_run_id,
            expected_cache_run_manifest_file_sha256=(
                expected_cache_run_manifest_file_sha256
            ),
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            require_m37=False,
        )
    record = _aggregate_record(
        validated,
        run_id=expected_run_id,
        cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )
    payload = core.canonical_json_bytes(record)
    if len(payload) > PHYSICAL_RESOURCE_RUN_MANIFEST_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "resource-run manifest exceeds its byte cap"
        )
    _atomic_publish(manifest_path, payload)
    return _receipt(payload, record)


def publish_m37_physical_resource_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[PhysicalResourceRunEntry],
    *,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> PhysicalResourceRunManifestReceipt:
    """Publish only a complete exact-M37 five-window child inventory."""
    validated = _validated_entries(entries, core.M37_WINDOW_IDS)
    manifest_path = Path(path)
    for entry in validated:
        _open_child(
            manifest_path.parent,
            entry,
            expected_run_id=expected_run_id,
            expected_cache_run_manifest_file_sha256=(
                expected_cache_run_manifest_file_sha256
            ),
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            require_m37=True,
        )
    return publish_physical_resource_run_manifest(
        manifest_path,
        validated,
        expected_window_ids=core.M37_WINDOW_IDS,
        expected_run_id=expected_run_id,
        expected_cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )


def _parse_manifest(
    raw: bytes,
    *,
    expected_manifest_sha256: str,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> tuple[dict[str, Any], tuple[PhysicalResourceRunEntry, ...]]:
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "resource-run manifest is invalid JSON"
        ) from error
    if (
        not isinstance(record, dict)
        or core.canonical_json_bytes(record) != raw
        or set(record) != _MANIFEST_FIELDS
        or record["schema_version"]
        != PHYSICAL_RESOURCE_RUN_MANIFEST_SCHEMA_VERSION
        or record["artifact_type"]
        != PHYSICAL_RESOURCE_RUN_MANIFEST_ARTIFACT_TYPE
        or record["detector_version"] != core.DETECTOR_VERSION
    ):
        raise core.V0P6ContractError(
            "resource-run manifest schema or canonical form changed"
        )
    observed_manifest_sha256 = _sha256(
        record["manifest_sha256"], "resource-run manifest identity"
    )
    unsealed = dict(record)
    unsealed.pop("manifest_sha256")
    if (
        hashlib.sha256(core.canonical_json_bytes(unsealed)).hexdigest()
        != observed_manifest_sha256
        or observed_manifest_sha256
        != _sha256(
            expected_manifest_sha256,
            "expected resource-run manifest identity",
        )
    ):
        raise core.V0P6IncompleteError(
            "resource-run manifest identity changed"
        )
    if not isinstance(record["entries"], list):
        raise core.V0P6ContractError("resource-run entries are invalid")
    entries = tuple(_validate_entry(item) for item in record["entries"])
    expected_windows = _window_ids(expected_window_ids)
    if tuple(entry.window_id for entry in entries) != expected_windows:
        raise core.V0P6IncompleteError(
            "resource-run window inventory is missing, duplicated, or reordered"
        )
    if len({entry.relative_path for entry in entries}) != len(entries):
        raise core.V0P6IncompleteError(
            "resource-run artifact paths are duplicated"
        )
    reconstructed = _aggregate_record(
        entries,
        run_id=expected_run_id,
        cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )
    if reconstructed != record:
        raise core.V0P6IncompleteError(
            "resource-run aggregate accounting or ancestry changed"
        )
    return record, entries


def open_physical_resource_run_manifest(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_manifest_sha256: str,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> PhysicalResourceRunManifest:
    """Reopen a run manifest and fully verify every referenced child file."""
    manifest_path = Path(path)
    with manifest_path.open("rb") as stream:
        raw = stream.read(PHYSICAL_RESOURCE_RUN_MANIFEST_MAXIMUM_BYTES + 1)
    if len(raw) > PHYSICAL_RESOURCE_RUN_MANIFEST_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "resource-run manifest exceeds its byte cap"
        )
    if hashlib.sha256(raw).hexdigest() != _sha256(
        expected_file_sha256, "expected resource-run manifest file identity"
    ):
        raise core.V0P6IncompleteError(
            "resource-run manifest file identity changed"
        )
    record, entries = _parse_manifest(
        raw,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_window_ids=expected_window_ids,
        expected_run_id=expected_run_id,
        expected_cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )
    artifacts = tuple(
        _open_child(
            manifest_path.parent,
            entry,
            expected_run_id=expected_run_id,
            expected_cache_run_manifest_file_sha256=(
                expected_cache_run_manifest_file_sha256
            ),
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            require_m37=False,
        )
        for entry in entries
    )
    return PhysicalResourceRunManifest(
        entries=entries,
        artifacts=artifacts,
        receipt=_receipt(raw, record),
    )


def open_m37_physical_resource_run_manifest(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_manifest_sha256: str,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> PhysicalResourceRunManifest:
    """Reopen a manifest and enforce exact M37 semantics on all five children."""
    manifest = open_physical_resource_run_manifest(
        path,
        expected_file_sha256=expected_file_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_window_ids=core.M37_WINDOW_IDS,
        expected_run_id=expected_run_id,
        expected_cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )
    for artifact in manifest.artifacts:
        physical.validate_m37_physical_resource_envelope(
            artifact.envelope,
            expected_envelope_sha256=(
                artifact.receipt.resource_envelope_sha256
            ),
        )
    return manifest
