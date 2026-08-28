"""Persistent global-null vectors bound to detector-v0.6 thresholds."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Mapping

import numpy as np

from . import search_v0p6 as core


_HEX = frozenset("0123456789abcdef")
_MAXIMUM_ARTIFACT_BYTES = 4_194_304


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise core.V0P6ContractError(f"{label} is not a lowercase SHA-256")
    return value


def _atomic_read_only_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError("global-null parent directory is absent")
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
                raise OSError("short write while publishing global-null artifact")
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


@dataclass(frozen=True)
class GlobalNullArtifactReceipt:
    file_sha256: str
    threshold_certificate_sha256: str
    global_null_maxima_sha256: str
    global_null_count: int
    file_nbytes: int


@dataclass(frozen=True)
class GlobalNullArtifact:
    threshold: core.ThresholdCertificate
    values: np.ndarray
    receipt: GlobalNullArtifactReceipt
    metadata: dict[str, Any]


def _record(
    threshold: core.ThresholdCertificate,
    values: np.ndarray,
    *,
    metadata: Mapping[str, Any],
    spectral_dataset_values_read: bool,
) -> dict[str, Any]:
    core.validate_threshold_certificate(threshold)
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size < 1 or not np.all(np.isfinite(vector)):
        raise core.V0P6ContractError("global-null vector must be finite and non-empty")
    vector = np.ascontiguousarray(vector, dtype="<f8")
    vector_digest = core.float64_vector_sha256(vector)
    if (
        vector.size != threshold.global_null_count
        or vector_digest != threshold.global_null_maxima_sha256
    ):
        raise core.V0P6IncompleteError(
            "global-null vector differs from its threshold certificate"
        )
    try:
        detached_metadata = json.loads(core.canonical_json_bytes(dict(metadata)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "global-null metadata is not canonical finite JSON"
        ) from error
    if not isinstance(detached_metadata, dict):
        raise core.V0P6ContractError("global-null metadata must be a mapping")
    return {
        "schema_version": 1,
        "artifact_type": "detector-v0p6-global-null-vector-v1",
        "detector_version": core.DETECTOR_VERSION,
        "spectral_dataset_values_read": spectral_dataset_values_read,
        "threshold_certificate_sha256": threshold.certificate_sha256,
        "threshold_certificate": threshold.as_record(),
        "global_null_count": int(vector.size),
        "global_null_maxima_sha256": vector_digest,
        "global_null_maxima": [float(item) for item in vector],
        "metadata": detached_metadata,
    }


def publish_global_null_artifact(
    path: str | os.PathLike[str],
    threshold: core.ThresholdCertificate,
    values: np.ndarray,
    *,
    metadata: Mapping[str, Any],
    spectral_dataset_values_read: bool,
) -> GlobalNullArtifactReceipt:
    if not isinstance(spectral_dataset_values_read, bool):
        raise core.V0P6ContractError("spectral-read flag must be boolean")
    record = _record(
        threshold,
        values,
        metadata=metadata,
        spectral_dataset_values_read=spectral_dataset_values_read,
    )
    payload = core.canonical_json_bytes(record)
    if len(payload) > _MAXIMUM_ARTIFACT_BYTES:
        raise core.V0P6CapacityError("global-null artifact exceeds its byte cap")
    destination = Path(path)
    _atomic_read_only_publish(destination, payload)
    return GlobalNullArtifactReceipt(
        file_sha256=hashlib.sha256(payload).hexdigest(),
        threshold_certificate_sha256=record["threshold_certificate_sha256"],
        global_null_maxima_sha256=record["global_null_maxima_sha256"],
        global_null_count=record["global_null_count"],
        file_nbytes=len(payload),
    )


def publish_m37_global_null_artifact(
    path: str | os.PathLike[str],
    threshold: core.ThresholdCertificate,
    values: np.ndarray,
    *,
    metadata: Mapping[str, Any],
) -> GlobalNullArtifactReceipt:
    core.validate_threshold_certificate(threshold)
    if (
        threshold.window_ids != core.M37_WINDOW_IDS
        or threshold.global_null_count != core.M37_SCRAMBLE_COUNT
        or threshold.experiment_contract_sha256
        != core.M37_EXPERIMENT_CONTRACT_SHA256
    ):
        raise core.V0P6IncompleteError("global-null threshold is not the M37 contract")
    return publish_global_null_artifact(
        path,
        threshold,
        values,
        metadata=metadata,
        spectral_dataset_values_read=True,
    )


def open_global_null_artifact(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_threshold_certificate_sha256: str,
    require_spectral_dataset_values_read: bool | None = None,
) -> GlobalNullArtifact:
    artifact_path = Path(path)
    raw = artifact_path.read_bytes()
    if len(raw) > _MAXIMUM_ARTIFACT_BYTES:
        raise core.V0P6CapacityError("global-null artifact exceeds its byte cap")
    file_digest = hashlib.sha256(raw).hexdigest()
    if file_digest != _sha256(expected_file_sha256, "expected global-null file"):
        raise core.V0P6IncompleteError("global-null file identity changed")
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError("global-null artifact is invalid JSON") from error
    if core.canonical_json_bytes(record) != raw or not isinstance(record, dict):
        raise core.V0P6ContractError("global-null artifact is not canonical JSON")
    required = {
        "schema_version",
        "artifact_type",
        "detector_version",
        "spectral_dataset_values_read",
        "threshold_certificate_sha256",
        "threshold_certificate",
        "global_null_count",
        "global_null_maxima_sha256",
        "global_null_maxima",
        "metadata",
    }
    if set(record) != required:
        raise core.V0P6ContractError("global-null artifact schema changed")
    if (
        record["schema_version"] != 1
        or record["artifact_type"] != "detector-v0p6-global-null-vector-v1"
        or record["detector_version"] != core.DETECTOR_VERSION
        or not isinstance(record["spectral_dataset_values_read"], bool)
    ):
        raise core.V0P6IncompleteError("global-null artifact contract changed")
    if require_spectral_dataset_values_read is not None and record[
        "spectral_dataset_values_read"
    ] is not require_spectral_dataset_values_read:
        raise core.V0P6IncompleteError("global-null spectral-read provenance changed")
    expected_threshold = _sha256(
        expected_threshold_certificate_sha256,
        "expected threshold certificate",
    )
    if record["threshold_certificate_sha256"] != expected_threshold:
        raise core.V0P6IncompleteError("global-null threshold identity changed")
    threshold = core.threshold_certificate_from_record(
        record["threshold_certificate"],
        expected_certificate_sha256=expected_threshold,
    )
    values = np.asarray(record["global_null_maxima"], dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise core.V0P6ContractError("global-null vector is invalid")
    values = np.ascontiguousarray(values, dtype="<f8")
    vector_digest = core.float64_vector_sha256(values)
    if (
        isinstance(record["global_null_count"], bool)
        or not isinstance(record["global_null_count"], int)
        or record["global_null_count"] != values.size
        or vector_digest
        != _sha256(record["global_null_maxima_sha256"], "global-null vector")
        or vector_digest != threshold.global_null_maxima_sha256
        or values.size != threshold.global_null_count
    ):
        raise core.V0P6IncompleteError("global-null vector accounting changed")
    values.setflags(write=False)
    metadata = record["metadata"]
    if not isinstance(metadata, dict):
        raise core.V0P6ContractError("global-null metadata is invalid")
    receipt = GlobalNullArtifactReceipt(
        file_sha256=file_digest,
        threshold_certificate_sha256=expected_threshold,
        global_null_maxima_sha256=vector_digest,
        global_null_count=int(values.size),
        file_nbytes=len(raw),
    )
    return GlobalNullArtifact(
        threshold=threshold,
        values=values,
        receipt=receipt,
        metadata=metadata,
    )
