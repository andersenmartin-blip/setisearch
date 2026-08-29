"""Restartable run inventory for complete physical-disposition artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
from typing import Any, Mapping, Sequence

from . import physical_disposition_v0p6 as disposition
from . import search_v0p6 as core


PHYSICAL_DISPOSITION_RUN_MANIFEST_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_physical_disposition_run_manifest"
)
PHYSICAL_DISPOSITION_RUN_MANIFEST_SCHEMA_VERSION = 1
PHYSICAL_DISPOSITION_RUN_MANIFEST_MAXIMUM_BYTES = 4_194_304
_ENTRY_FIELDS = frozenset(
    {
        "window_id",
        "relative_path",
        "artifact_file_sha256",
        "physical_disposition_certificate_sha256",
        "physical_evidence_execution_result_sha256",
        "physical_resource_envelope_sha256",
        "off_match_certificate_sha256",
        "receiver_alias_certificate_sha256",
        "final_annotated_records_sha256",
        "on_retention_certificate_sha256",
        "final_disposition_counts",
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
        "artifact_type",
        "schema_version",
        "detector_version",
        "run_id",
        "window_ids",
        "window_count",
        "cache_run_manifest_file_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_inventory_sha256",
        "disposition_artifact_inventory_sha256",
        "final_disposition_counts",
        "total_final_record_count",
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
    return core._frozen_sha256(value, label)


def _strict_int(value: Any, label: str) -> int:
    return core._strict_int(value, label)


def _window_ids(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise core.V0P6ContractError(
            "physical-disposition run window inventory is invalid"
        )
    result = tuple(values)
    if (
        not result
        or any(not isinstance(value, str) or not value for value in result)
        or len(set(result)) != len(result)
    ):
        raise core.V0P6ContractError(
            "physical-disposition run window inventory is invalid"
        )
    return result


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise core.V0P6ContractError(
            "physical-disposition artifact path is invalid"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise core.V0P6ContractError(
            "physical-disposition artifact path escapes the run root"
        )
    if path.as_posix() != value:
        raise core.V0P6ContractError(
            "physical-disposition artifact path is not canonical"
        )
    return value


def _counts(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or not value:
        raise core.V0P6ContractError(
            "physical-disposition count inventory is invalid"
        )
    result: dict[str, int] = {}
    for key, count in sorted(value.items()):
        if not isinstance(key, str) or not key:
            raise core.V0P6ContractError(
                "physical-disposition count key is invalid"
            )
        exact = _strict_int(count, f"{key} disposition count")
        if exact < 0:
            raise core.V0P6ContractError(
                "physical-disposition count is negative"
            )
        result[key] = exact
    return result


@dataclass(frozen=True)
class PhysicalDispositionRunEntry:
    window_id: str
    relative_path: str
    artifact_file_sha256: str
    physical_disposition_certificate_sha256: str
    physical_evidence_execution_result_sha256: str
    physical_resource_envelope_sha256: str
    off_match_certificate_sha256: str
    receiver_alias_certificate_sha256: str
    final_annotated_records_sha256: str
    on_retention_certificate_sha256: str
    final_disposition_counts: dict[str, int]
    artifact_file_nbytes: int
    maximum_process_mapped_bytes: int
    aggregate_peak_mapped_bytes: int
    aggregate_peak_handle_count: int
    aggregate_batch_count: int
    aggregate_opened_cache_count: int

    def as_record(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in (
                "window_id",
                "relative_path",
                "artifact_file_sha256",
                "physical_disposition_certificate_sha256",
                "physical_evidence_execution_result_sha256",
                "physical_resource_envelope_sha256",
                "off_match_certificate_sha256",
                "receiver_alias_certificate_sha256",
                "final_annotated_records_sha256",
                "on_retention_certificate_sha256",
                "final_disposition_counts",
                "artifact_file_nbytes",
                "maximum_process_mapped_bytes",
                "aggregate_peak_mapped_bytes",
                "aggregate_peak_handle_count",
                "aggregate_batch_count",
                "aggregate_opened_cache_count",
            )
        }


@dataclass(frozen=True)
class PhysicalDispositionRunManifestReceipt:
    file_sha256: str
    manifest_sha256: str
    disposition_artifact_inventory_sha256: str
    on_retention_inventory_sha256: str
    run_id: str
    cache_run_manifest_file_sha256: str
    factor_bundle_manifest_sha256: str
    window_count: int
    total_final_record_count: int
    maximum_process_mapped_bytes: int
    maximum_window_peak_mapped_bytes: int
    maximum_window_peak_handle_count: int
    total_batch_count: int
    total_opened_cache_count: int
    total_artifact_file_nbytes: int
    file_nbytes: int


@dataclass(frozen=True)
class PhysicalDispositionRunManifest:
    entries: tuple[PhysicalDispositionRunEntry, ...]
    artifacts: tuple[disposition.PhysicalDispositionArtifact, ...]
    receipt: PhysicalDispositionRunManifestReceipt


def _entry_from_artifact(
    relative_path: str,
    artifact: disposition.PhysicalDispositionArtifact,
) -> PhysicalDispositionRunEntry:
    if not isinstance(artifact, disposition.PhysicalDispositionArtifact):
        raise core.V0P6ContractError(
            "disposition-run entry lacks an opened artifact"
        )
    receipt = artifact.receipt
    validated = disposition.validate_physical_disposition_result(
        artifact.result,
        expected_physical_disposition_certificate_sha256=(
            receipt.physical_disposition_certificate_sha256
        ),
    )
    raw = core.canonical_json_bytes(validated)
    cert = validated["certificate"]
    envelope = validated["physical_evidence_execution_result"][
        "resource_envelope"
    ]
    if (
        hashlib.sha256(raw).hexdigest() != receipt.file_sha256
        or len(raw) != receipt.file_nbytes
        or receipt.run_id != cert["run_id"]
        or receipt.window_id != cert["window_id"]
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition artifact and receipt differ"
        )
    return PhysicalDispositionRunEntry(
        window_id=receipt.window_id,
        relative_path=_relative_path(relative_path),
        artifact_file_sha256=receipt.file_sha256,
        physical_disposition_certificate_sha256=(
            receipt.physical_disposition_certificate_sha256
        ),
        physical_evidence_execution_result_sha256=(
            receipt.physical_evidence_execution_result_sha256
        ),
        physical_resource_envelope_sha256=(
            receipt.physical_resource_envelope_sha256
        ),
        off_match_certificate_sha256=receipt.off_match_certificate_sha256,
        receiver_alias_certificate_sha256=(
            receipt.receiver_alias_certificate_sha256
        ),
        final_annotated_records_sha256=(
            receipt.final_annotated_records_sha256
        ),
        on_retention_certificate_sha256=(
            receipt.on_retention_certificate_sha256
        ),
        final_disposition_counts=_counts(cert["final_disposition_counts"]),
        artifact_file_nbytes=receipt.file_nbytes,
        maximum_process_mapped_bytes=envelope["maximum_process_mapped_bytes"],
        aggregate_peak_mapped_bytes=envelope["aggregate_peak_mapped_bytes"],
        aggregate_peak_handle_count=envelope["aggregate_peak_handle_count"],
        aggregate_batch_count=envelope["aggregate_batch_count"],
        aggregate_opened_cache_count=envelope["aggregate_opened_cache_count"],
    )


def make_physical_disposition_run_entry(
    relative_path: str,
    artifact: disposition.PhysicalDispositionArtifact,
) -> PhysicalDispositionRunEntry:
    return _entry_from_artifact(relative_path, artifact)


def _validate_entry(value: Mapping[str, Any]) -> PhysicalDispositionRunEntry:
    if not isinstance(value, Mapping) or set(value) != _ENTRY_FIELDS:
        raise core.V0P6ContractError("disposition-run entry schema changed")
    if not isinstance(value["window_id"], str) or not value["window_id"]:
        raise core.V0P6ContractError("disposition-run window ID is invalid")
    result = PhysicalDispositionRunEntry(
        window_id=value["window_id"],
        relative_path=_relative_path(value["relative_path"]),
        artifact_file_sha256=_sha256(
            value["artifact_file_sha256"], "disposition artifact file identity"
        ),
        physical_disposition_certificate_sha256=_sha256(
            value["physical_disposition_certificate_sha256"],
            "physical-disposition certificate identity",
        ),
        physical_evidence_execution_result_sha256=_sha256(
            value["physical_evidence_execution_result_sha256"],
            "physical-evidence execution identity",
        ),
        physical_resource_envelope_sha256=_sha256(
            value["physical_resource_envelope_sha256"],
            "physical-resource envelope identity",
        ),
        off_match_certificate_sha256=_sha256(
            value["off_match_certificate_sha256"], "OFF-match identity"
        ),
        receiver_alias_certificate_sha256=_sha256(
            value["receiver_alias_certificate_sha256"],
            "receiver-alias identity",
        ),
        final_annotated_records_sha256=_sha256(
            value["final_annotated_records_sha256"],
            "final annotated-record identity",
        ),
        on_retention_certificate_sha256=_sha256(
            value["on_retention_certificate_sha256"],
            "ON-retention certificate identity",
        ),
        final_disposition_counts=_counts(value["final_disposition_counts"]),
        artifact_file_nbytes=_strict_int(
            value["artifact_file_nbytes"], "disposition artifact bytes"
        ),
        maximum_process_mapped_bytes=_strict_int(
            value["maximum_process_mapped_bytes"], "mapped-byte cap"
        ),
        aggregate_peak_mapped_bytes=_strict_int(
            value["aggregate_peak_mapped_bytes"], "mapped-byte peak"
        ),
        aggregate_peak_handle_count=_strict_int(
            value["aggregate_peak_handle_count"], "mapped-handle peak"
        ),
        aggregate_batch_count=_strict_int(
            value["aggregate_batch_count"], "batch count"
        ),
        aggregate_opened_cache_count=_strict_int(
            value["aggregate_opened_cache_count"], "opened-cache count"
        ),
    )
    if (
        result.artifact_file_nbytes < 1
        or result.maximum_process_mapped_bytes < 1
        or result.aggregate_peak_mapped_bytes < 0
        or result.aggregate_peak_mapped_bytes
        > result.maximum_process_mapped_bytes
        or min(
            result.aggregate_peak_handle_count,
            result.aggregate_batch_count,
            result.aggregate_opened_cache_count,
        )
        < 0
    ):
        raise core.V0P6IncompleteError(
            "disposition-run entry accounting is invalid"
        )
    return result


def on_retention_inventory_sha256(
    entries: Sequence[PhysicalDispositionRunEntry],
) -> str:
    return hashlib.sha256(
        core.canonical_json_bytes(
            [
                {
                    "window_id": entry.window_id,
                    "on_retention_certificate_sha256": (
                        entry.on_retention_certificate_sha256
                    ),
                }
                for entry in entries
            ]
        )
    ).hexdigest()


def _artifact_inventory_sha256(
    entries: Sequence[PhysicalDispositionRunEntry],
) -> str:
    return hashlib.sha256(
        core.canonical_json_bytes([entry.as_record() for entry in entries])
    ).hexdigest()


def _aggregate_counts(
    entries: Sequence[PhysicalDispositionRunEntry],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in entries:
        for name, count in entry.final_disposition_counts.items():
            result[name] = result.get(name, 0) + count
    return dict(sorted(result.items()))


def _seal_manifest(
    entries: Sequence[PhysicalDispositionRunEntry],
    *,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> dict[str, Any]:
    windows = _window_ids(expected_window_ids)
    if not isinstance(expected_run_id, str) or not expected_run_id:
        raise core.V0P6ContractError("disposition-run ID is invalid")
    cache_sha = _sha256(
        expected_cache_run_manifest_file_sha256,
        "expected cache-run manifest file identity",
    )
    factor_sha = _sha256(
        expected_factor_bundle_manifest_sha256,
        "expected factor-bundle manifest identity",
    )
    retention_sha = _sha256(
        expected_on_retention_inventory_sha256,
        "expected ON-retention inventory identity",
    )
    exact_entries = tuple(_validate_entry(entry.as_record()) for entry in entries)
    if tuple(entry.window_id for entry in exact_entries) != windows:
        raise core.V0P6IncompleteError(
            "disposition-run window inventory is missing, duplicated, or reordered"
        )
    if len({entry.relative_path for entry in exact_entries}) != len(exact_entries):
        raise core.V0P6IncompleteError(
            "disposition-run repeats an artifact path"
        )
    if on_retention_inventory_sha256(exact_entries) != retention_sha:
        raise core.V0P6IncompleteError(
            "disposition-run ON-retention inventory changed"
        )
    counts = _aggregate_counts(exact_entries)
    manifest = {
        "artifact_type": PHYSICAL_DISPOSITION_RUN_MANIFEST_ARTIFACT_TYPE,
        "schema_version": PHYSICAL_DISPOSITION_RUN_MANIFEST_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "run_id": expected_run_id,
        "window_ids": list(windows),
        "window_count": len(windows),
        "cache_run_manifest_file_sha256": cache_sha,
        "factor_bundle_manifest_sha256": factor_sha,
        "on_retention_inventory_sha256": retention_sha,
        "disposition_artifact_inventory_sha256": (
            _artifact_inventory_sha256(exact_entries)
        ),
        "final_disposition_counts": counts,
        "total_final_record_count": sum(counts.values()),
        "maximum_process_mapped_bytes": max(
            entry.maximum_process_mapped_bytes for entry in exact_entries
        ),
        "maximum_window_peak_mapped_bytes": max(
            entry.aggregate_peak_mapped_bytes for entry in exact_entries
        ),
        "maximum_window_peak_handle_count": max(
            entry.aggregate_peak_handle_count for entry in exact_entries
        ),
        "total_batch_count": sum(
            entry.aggregate_batch_count for entry in exact_entries
        ),
        "total_opened_cache_count": sum(
            entry.aggregate_opened_cache_count for entry in exact_entries
        ),
        "total_artifact_file_nbytes": sum(
            entry.artifact_file_nbytes for entry in exact_entries
        ),
        "entries": [entry.as_record() for entry in exact_entries],
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(manifest)
    ).hexdigest()
    return manifest


def _validate_manifest(
    value: Mapping[str, Any],
    *,
    expected_manifest_sha256: str,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> tuple[dict[str, Any], tuple[PhysicalDispositionRunEntry, ...]]:
    if not isinstance(value, Mapping) or set(value) != _MANIFEST_FIELDS:
        raise core.V0P6ContractError("disposition-run manifest schema changed")
    detached = json.loads(core.canonical_json_bytes(dict(value)))
    observed = _sha256(
        detached.pop("manifest_sha256"), "disposition-run manifest identity"
    )
    if (
        hashlib.sha256(core.canonical_json_bytes(detached)).hexdigest()
        != observed
        or observed
        != _sha256(
            expected_manifest_sha256,
            "expected disposition-run manifest identity",
        )
    ):
        raise core.V0P6IncompleteError(
            "disposition-run manifest identity changed"
        )
    detached["manifest_sha256"] = observed
    records = detached["entries"]
    if not isinstance(records, list):
        raise core.V0P6ContractError("disposition-run entries are invalid")
    entries = tuple(_validate_entry(record) for record in records)
    reproduced = _seal_manifest(
        entries,
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
    if reproduced != detached:
        raise core.V0P6IncompleteError(
            "disposition-run manifest does not reproduce"
        )
    return detached, entries


def _atomic_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError(
            "disposition-run manifest parent directory is absent"
        )
    temporary = path.parent / f".{path.name}.tmp-{secrets.token_hex(8)}"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o400,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while publishing disposition run")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temporary, path)
        directory_descriptor = os.open(
            path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _receipt(raw: bytes, manifest: Mapping[str, Any]) -> PhysicalDispositionRunManifestReceipt:
    return PhysicalDispositionRunManifestReceipt(
        file_sha256=hashlib.sha256(raw).hexdigest(),
        manifest_sha256=manifest["manifest_sha256"],
        disposition_artifact_inventory_sha256=manifest[
            "disposition_artifact_inventory_sha256"
        ],
        on_retention_inventory_sha256=manifest[
            "on_retention_inventory_sha256"
        ],
        run_id=manifest["run_id"],
        cache_run_manifest_file_sha256=manifest[
            "cache_run_manifest_file_sha256"
        ],
        factor_bundle_manifest_sha256=manifest[
            "factor_bundle_manifest_sha256"
        ],
        window_count=manifest["window_count"],
        total_final_record_count=manifest["total_final_record_count"],
        maximum_process_mapped_bytes=manifest["maximum_process_mapped_bytes"],
        maximum_window_peak_mapped_bytes=manifest[
            "maximum_window_peak_mapped_bytes"
        ],
        maximum_window_peak_handle_count=manifest[
            "maximum_window_peak_handle_count"
        ],
        total_batch_count=manifest["total_batch_count"],
        total_opened_cache_count=manifest["total_opened_cache_count"],
        total_artifact_file_nbytes=manifest["total_artifact_file_nbytes"],
        file_nbytes=len(raw),
    )


def publish_physical_disposition_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[PhysicalDispositionRunEntry],
    **expected: Any,
) -> PhysicalDispositionRunManifestReceipt:
    manifest = _seal_manifest(entries, **expected)
    payload = core.canonical_json_bytes(manifest)
    if len(payload) > PHYSICAL_DISPOSITION_RUN_MANIFEST_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "disposition-run manifest exceeds its byte cap"
        )
    _atomic_publish(Path(path), payload)
    return _receipt(payload, manifest)


def publish_m37_physical_disposition_run_manifest(
    path: str | os.PathLike[str],
    entries: Sequence[PhysicalDispositionRunEntry],
    **expected: Any,
) -> PhysicalDispositionRunManifestReceipt:
    expected = dict(expected)
    expected["expected_window_ids"] = core.M37_WINDOW_IDS
    return publish_physical_disposition_run_manifest(path, entries, **expected)


def open_physical_disposition_run_manifest(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_manifest_sha256: str,
    expected_window_ids: Sequence[str],
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> PhysicalDispositionRunManifest:
    manifest_path = Path(path)
    with manifest_path.open("rb") as stream:
        raw = stream.read(PHYSICAL_DISPOSITION_RUN_MANIFEST_MAXIMUM_BYTES + 1)
    if len(raw) > PHYSICAL_DISPOSITION_RUN_MANIFEST_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "disposition-run manifest exceeds its byte cap"
        )
    if hashlib.sha256(raw).hexdigest() != _sha256(
        expected_file_sha256, "expected disposition-run file identity"
    ):
        raise core.V0P6IncompleteError(
            "disposition-run manifest file identity changed"
        )
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "disposition-run manifest is invalid JSON"
        ) from error
    if core.canonical_json_bytes(parsed) != raw:
        raise core.V0P6ContractError(
            "disposition-run manifest is not canonical JSON"
        )
    manifest, entries = _validate_manifest(
        parsed,
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
    artifacts = []
    for entry in entries:
        artifact = disposition.open_physical_disposition_artifact(
            manifest_path.parent / entry.relative_path,
            expected_file_sha256=entry.artifact_file_sha256,
            expected_physical_disposition_certificate_sha256=(
                entry.physical_disposition_certificate_sha256
            ),
            expected_run_id=expected_run_id,
            expected_window_id=entry.window_id,
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
                "disposition-run child differs from its entry"
            )
        artifacts.append(artifact)
    return PhysicalDispositionRunManifest(
        entries=entries,
        artifacts=tuple(artifacts),
        receipt=_receipt(raw, manifest),
    )


def open_m37_physical_disposition_run_manifest(
    path: str | os.PathLike[str],
    **expected: Any,
) -> PhysicalDispositionRunManifest:
    expected = dict(expected)
    expected["expected_window_ids"] = core.M37_WINDOW_IDS
    opened = open_physical_disposition_run_manifest(path, **expected)
    for artifact in opened.artifacts:
        disposition.validate_m37_physical_disposition_result(
            artifact.result,
            expected_physical_disposition_certificate_sha256=(
                artifact.receipt.physical_disposition_certificate_sha256
            ),
        )
    return opened
