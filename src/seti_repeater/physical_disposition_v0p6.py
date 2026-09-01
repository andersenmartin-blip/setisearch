"""Persist the complete detector-v0.6 physical-disposition join.

The receiver-signature and single-adjacent-OFF payloads are produced under a
shared resource envelope, while retained-OFF matching and receiver-alias
classification are separate deterministic stages.  This module joins their
complete payloads without rewriting any upstream evidence and publishes one
independently reopenable, window-scoped artifact.

Importing this module does not open telescope data or artifact files.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Mapping

from . import alias_v0p6 as alias
from . import physical_resource_v0p6 as physical
from . import search_v0p6 as core


PHYSICAL_DISPOSITION_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_complete_physical_disposition"
)
PHYSICAL_DISPOSITION_SCHEMA_VERSION = 1
PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES = (
    physical.PHYSICAL_EVIDENCE_EXECUTION_ARTIFACT_MAXIMUM_BYTES
    + 2 * core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
    + 16_777_216
)
_CERTIFICATE_FIELDS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "run_id",
        "window_id",
        "cache_run_manifest_file_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "physical_evidence_execution_result_sha256",
        "physical_resource_envelope_sha256",
        "receiver_result_sha256",
        "receiver_signature_certificate_sha256",
        "receiver_signature_product_sha256",
        "single_adjacent_off_certificate_sha256",
        "single_adjacent_off_evidence_sha256",
        "off_match_certificate_sha256",
        "off_annotated_records_sha256",
        "receiver_alias_certificate_sha256",
        "final_annotated_records_sha256",
        "final_disposition_counts",
        "input_record_count",
        "all_inputs_share_one_on_retention_ancestry",
        "all_input_records_receive_one_final_disposition",
        "upstream_evidence_rewritten",
        "truncation_permitted",
        "physical_disposition_certificate_sha256",
    }
)
_RESULT_FIELDS = frozenset(
    {
        "physical_evidence_execution_result",
        "off_match_result",
        "receiver_alias_result",
        "certificate",
    }
)


@dataclass(frozen=True)
class PhysicalDispositionArtifactReceipt:
    file_sha256: str
    physical_disposition_certificate_sha256: str
    physical_evidence_execution_result_sha256: str
    physical_resource_envelope_sha256: str
    off_match_certificate_sha256: str
    receiver_alias_certificate_sha256: str
    final_annotated_records_sha256: str
    run_id: str
    window_id: str
    cache_run_manifest_file_sha256: str
    factor_bundle_manifest_sha256: str
    on_retention_certificate_sha256: str
    file_nbytes: int


@dataclass(frozen=True)
class PhysicalDispositionArtifact:
    result: dict[str, Any]
    receipt: PhysicalDispositionArtifactReceipt


def _detached_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    try:
        detached = json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            f"{label} is not canonical finite JSON"
        ) from error
    if not isinstance(detached, dict):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    return detached


def _sha256(value: Any, label: str) -> str:
    return core._frozen_sha256(value, label)


def _validate_joined_payloads(
    physical_result: Mapping[str, Any],
    off_result: Mapping[str, Any],
    alias_result: Mapping[str, Any],
    *,
    expected_physical_evidence_execution_result_sha256: str,
    expected_off_match_certificate_sha256: str,
    expected_receiver_alias_certificate_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    evidence = physical.validate_physical_evidence_execution_result(
        physical_result,
        expected_execution_result_sha256=(
            expected_physical_evidence_execution_result_sha256
        ),
    )
    detached_off = _detached_mapping(off_result, "retained-OFF result")
    if set(detached_off) != {"records", "certificate"}:
        raise core.V0P6ContractError("retained-OFF result schema changed")
    off_certificate = core.validate_off_match_result(
        detached_off["records"],
        detached_off["certificate"],
        expected_certificate_sha256=expected_off_match_certificate_sha256,
    )
    detached_alias = _detached_mapping(
        alias_result, "receiver-alias result"
    )
    if set(detached_alias) != {"records", "certificate"}:
        raise core.V0P6ContractError("receiver-alias result schema changed")
    alias_certificate = alias.validate_receiver_alias_result(
        detached_alias["records"],
        detached_alias["certificate"],
        expected_certificate_sha256=(
            expected_receiver_alias_certificate_sha256
        ),
    )

    envelope = evidence["resource_envelope"]
    receiver_certificate = evidence["receiver_result"]["certificate"]
    adjacent_certificate = evidence["adjacent_result"]["certificate"]
    off_records_sha256 = hashlib.sha256(
        core.canonical_json_bytes(detached_off["records"])
    ).hexdigest()
    if (
        off_certificate["window_id"] != envelope["window_id"]
        or alias_certificate["window_id"] != envelope["window_id"]
        or off_certificate["on_retention_certificate_sha256"]
        != envelope["on_retention_certificate_sha256"]
        or alias_certificate["on_retention_certificate_sha256"]
        != envelope["on_retention_certificate_sha256"]
        or off_certificate["on_records_sha256"] != envelope["on_records_sha256"]
        or alias_certificate["off_match_certificate_sha256"]
        != off_certificate["off_match_certificate_sha256"]
        or alias_certificate["input_off_annotated_records_sha256"]
        != off_records_sha256
        or alias_certificate["single_adjacent_off_certificate_sha256"]
        != envelope["single_adjacent_off_certificate_sha256"]
        or alias_certificate["single_adjacent_off_evidence_sha256"]
        != envelope["adjacent_evidence_sha256"]
        or adjacent_certificate["evidence_sha256"]
        != envelope["adjacent_evidence_sha256"]
        or alias_certificate["receiver_signature_product_sha256"]
        != receiver_certificate["receiver_signature_product_sha256"]
        or alias_certificate.get("receiver_signature_certificate_sha256")
        != envelope["receiver_signature_certificate_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition inputs do not share one complete ancestry"
        )
    disposition_counts = alias_certificate["disposition_counts"]
    if (
        not isinstance(disposition_counts, dict)
        or sum(disposition_counts.values()) != len(detached_alias["records"])
        or len(detached_alias["records"]) != off_certificate["on_record_count"]
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition final record inventory is incomplete"
        )
    return evidence, detached_off, detached_alias


def seal_physical_disposition_result(
    physical_evidence_execution_result: Mapping[str, Any],
    off_match_result: Mapping[str, Any],
    receiver_alias_result: Mapping[str, Any],
    *,
    expected_physical_evidence_execution_result_sha256: str,
    expected_off_match_certificate_sha256: str,
    expected_receiver_alias_certificate_sha256: str,
) -> dict[str, Any]:
    """Join all complete physical evidence into one final disposition."""
    evidence, off_result, alias_result = _validate_joined_payloads(
        physical_evidence_execution_result,
        off_match_result,
        receiver_alias_result,
        expected_physical_evidence_execution_result_sha256=(
            expected_physical_evidence_execution_result_sha256
        ),
        expected_off_match_certificate_sha256=(
            expected_off_match_certificate_sha256
        ),
        expected_receiver_alias_certificate_sha256=(
            expected_receiver_alias_certificate_sha256
        ),
    )
    envelope = evidence["resource_envelope"]
    off_certificate = off_result["certificate"]
    alias_certificate = alias_result["certificate"]
    certificate = {
        "artifact_type": PHYSICAL_DISPOSITION_ARTIFACT_TYPE,
        "schema_version": PHYSICAL_DISPOSITION_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "run_id": envelope["run_id"],
        "window_id": envelope["window_id"],
        "cache_run_manifest_file_sha256": envelope[
            "cache_run_manifest_file_sha256"
        ],
        "factor_bundle_manifest_sha256": envelope[
            "factor_bundle_manifest_sha256"
        ],
        "on_retention_certificate_sha256": envelope[
            "on_retention_certificate_sha256"
        ],
        "on_records_sha256": envelope["on_records_sha256"],
        "physical_evidence_execution_result_sha256": evidence[
            "execution_result_sha256"
        ],
        "physical_resource_envelope_sha256": envelope[
            "resource_envelope_sha256"
        ],
        "receiver_result_sha256": envelope["receiver_result_sha256"],
        "receiver_signature_certificate_sha256": envelope[
            "receiver_signature_certificate_sha256"
        ],
        "receiver_signature_product_sha256": alias_certificate[
            "receiver_signature_product_sha256"
        ],
        "single_adjacent_off_certificate_sha256": envelope[
            "single_adjacent_off_certificate_sha256"
        ],
        "single_adjacent_off_evidence_sha256": envelope[
            "adjacent_evidence_sha256"
        ],
        "off_match_certificate_sha256": off_certificate[
            "off_match_certificate_sha256"
        ],
        "off_annotated_records_sha256": alias_certificate[
            "input_off_annotated_records_sha256"
        ],
        "receiver_alias_certificate_sha256": alias_certificate[
            "receiver_alias_certificate_sha256"
        ],
        "final_annotated_records_sha256": alias_certificate[
            "annotated_records_sha256"
        ],
        "final_disposition_counts": alias_certificate["disposition_counts"],
        "input_record_count": alias_certificate["input_record_count"],
        "all_inputs_share_one_on_retention_ancestry": True,
        "all_input_records_receive_one_final_disposition": True,
        "upstream_evidence_rewritten": False,
        "truncation_permitted": False,
    }
    certificate["physical_disposition_certificate_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(certificate)
    ).hexdigest()
    result = {
        "physical_evidence_execution_result": evidence,
        "off_match_result": off_result,
        "receiver_alias_result": alias_result,
        "certificate": certificate,
    }
    return validate_physical_disposition_result(
        result,
        expected_physical_disposition_certificate_sha256=certificate[
            "physical_disposition_certificate_sha256"
        ],
    )


def validate_physical_disposition_result(
    result: Mapping[str, Any],
    *,
    expected_physical_disposition_certificate_sha256: str,
) -> dict[str, Any]:
    """Validate every payload and every cross-stage identity in the join."""
    detached = _detached_mapping(result, "physical-disposition result")
    if set(detached) != _RESULT_FIELDS:
        raise core.V0P6ContractError(
            "physical-disposition result schema changed"
        )
    certificate = detached["certificate"]
    if not isinstance(certificate, dict) or set(certificate) != _CERTIFICATE_FIELDS:
        raise core.V0P6ContractError(
            "physical-disposition certificate schema changed"
        )
    observed_sha256 = _sha256(
        certificate.pop("physical_disposition_certificate_sha256"),
        "physical-disposition certificate identity",
    )
    if (
        hashlib.sha256(core.canonical_json_bytes(certificate)).hexdigest()
        != observed_sha256
        or observed_sha256
        != _sha256(
            expected_physical_disposition_certificate_sha256,
            "expected physical-disposition certificate identity",
        )
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition certificate identity changed"
        )
    certificate["physical_disposition_certificate_sha256"] = observed_sha256
    for name in (
        "cache_run_manifest_file_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "physical_evidence_execution_result_sha256",
        "physical_resource_envelope_sha256",
        "receiver_result_sha256",
        "receiver_signature_certificate_sha256",
        "receiver_signature_product_sha256",
        "single_adjacent_off_certificate_sha256",
        "single_adjacent_off_evidence_sha256",
        "off_match_certificate_sha256",
        "off_annotated_records_sha256",
        "receiver_alias_certificate_sha256",
        "final_annotated_records_sha256",
    ):
        _sha256(certificate[name], name.replace("_", " "))
    if (
        certificate["artifact_type"] != PHYSICAL_DISPOSITION_ARTIFACT_TYPE
        or certificate["schema_version"] != PHYSICAL_DISPOSITION_SCHEMA_VERSION
        or certificate["detector_version"] != core.DETECTOR_VERSION
        or not isinstance(certificate["run_id"], str)
        or not certificate["run_id"]
        or not isinstance(certificate["window_id"], str)
        or not certificate["window_id"]
        or certificate["all_inputs_share_one_on_retention_ancestry"] is not True
        or certificate["all_input_records_receive_one_final_disposition"]
        is not True
        or certificate["upstream_evidence_rewritten"] is not False
        or certificate["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "physical-disposition certificate semantics changed"
        )
    evidence, off_result, alias_result = _validate_joined_payloads(
        detached["physical_evidence_execution_result"],
        detached["off_match_result"],
        detached["receiver_alias_result"],
        expected_physical_evidence_execution_result_sha256=certificate[
            "physical_evidence_execution_result_sha256"
        ],
        expected_off_match_certificate_sha256=certificate[
            "off_match_certificate_sha256"
        ],
        expected_receiver_alias_certificate_sha256=certificate[
            "receiver_alias_certificate_sha256"
        ],
    )
    envelope = evidence["resource_envelope"]
    receiver_certificate = evidence["receiver_result"]["certificate"]
    adjacent_certificate = evidence["adjacent_result"]["certificate"]
    off_certificate = off_result["certificate"]
    alias_certificate = alias_result["certificate"]
    exact = {
        "run_id": envelope["run_id"],
        "window_id": envelope["window_id"],
        "cache_run_manifest_file_sha256": envelope[
            "cache_run_manifest_file_sha256"
        ],
        "factor_bundle_manifest_sha256": envelope[
            "factor_bundle_manifest_sha256"
        ],
        "on_retention_certificate_sha256": envelope[
            "on_retention_certificate_sha256"
        ],
        "on_records_sha256": envelope["on_records_sha256"],
        "physical_evidence_execution_result_sha256": evidence[
            "execution_result_sha256"
        ],
        "physical_resource_envelope_sha256": envelope[
            "resource_envelope_sha256"
        ],
        "receiver_result_sha256": envelope["receiver_result_sha256"],
        "receiver_signature_certificate_sha256": envelope[
            "receiver_signature_certificate_sha256"
        ],
        "receiver_signature_product_sha256": receiver_certificate[
            "receiver_signature_product_sha256"
        ],
        "single_adjacent_off_certificate_sha256": adjacent_certificate[
            "single_adjacent_off_certificate_sha256"
        ],
        "single_adjacent_off_evidence_sha256": adjacent_certificate[
            "evidence_sha256"
        ],
        "off_match_certificate_sha256": off_certificate[
            "off_match_certificate_sha256"
        ],
        "off_annotated_records_sha256": alias_certificate[
            "input_off_annotated_records_sha256"
        ],
        "receiver_alias_certificate_sha256": alias_certificate[
            "receiver_alias_certificate_sha256"
        ],
        "final_annotated_records_sha256": alias_certificate[
            "annotated_records_sha256"
        ],
        "final_disposition_counts": alias_certificate["disposition_counts"],
        "input_record_count": alias_certificate["input_record_count"],
    }
    if any(certificate[name] != value for name, value in exact.items()):
        raise core.V0P6IncompleteError(
            "physical-disposition certificate differs from its payloads"
        )
    return detached


def validate_m37_physical_disposition_result(
    result: Mapping[str, Any],
    *,
    expected_physical_disposition_certificate_sha256: str,
) -> dict[str, Any]:
    """Apply the exact M37 contracts to the complete joined payload."""
    validated = validate_physical_disposition_result(
        result,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    physical.validate_m37_physical_evidence_execution_result(
        validated["physical_evidence_execution_result"],
        expected_execution_result_sha256=validated["certificate"][
            "physical_evidence_execution_result_sha256"
        ],
    )
    cert = validated["receiver_alias_result"]["certificate"]
    if (
        validated["certificate"]["window_id"] not in core.M37_WINDOW_IDS
        or cert["window_ordinal"]
        != core.M37_WINDOW_IDS.index(validated["certificate"]["window_id"])
        or cert["track_tolerance_hz"] != alias.M37_ALIAS_TRACK_TOLERANCE_HZ
        or cert["local_receiver_half_width_hz"]
        != alias.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        or cert["local_peak_snr_floor"]
        != alias.M37_RECEIVER_PEAK_SNR_FLOOR
        or cert["minimum_shared_active_epochs"]
        != alias.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        or cert["maximum_records"] != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or cert["maximum_bucket_entries"]
        != core.M37_MAXIMUM_ALIAS_BUCKET_ENTRIES
        or cert["maximum_alias_identity_track_comparisons"]
        != alias.M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        or cert["maximum_distinct_candidate_visits_per_window"]
        != core.M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
    ):
        raise core.V0P6ContractError(
            "physical disposition differs from the M37 alias contract"
        )
    return validated


def _atomic_read_only_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError(
            "physical-disposition artifact parent directory is absent"
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
                raise OSError("short write while publishing physical disposition")
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


def _receipt(
    raw: bytes, result: Mapping[str, Any]
) -> PhysicalDispositionArtifactReceipt:
    cert = result["certificate"]
    return PhysicalDispositionArtifactReceipt(
        file_sha256=hashlib.sha256(raw).hexdigest(),
        physical_disposition_certificate_sha256=cert[
            "physical_disposition_certificate_sha256"
        ],
        physical_evidence_execution_result_sha256=cert[
            "physical_evidence_execution_result_sha256"
        ],
        physical_resource_envelope_sha256=cert[
            "physical_resource_envelope_sha256"
        ],
        off_match_certificate_sha256=cert["off_match_certificate_sha256"],
        receiver_alias_certificate_sha256=cert[
            "receiver_alias_certificate_sha256"
        ],
        final_annotated_records_sha256=cert[
            "final_annotated_records_sha256"
        ],
        run_id=cert["run_id"],
        window_id=cert["window_id"],
        cache_run_manifest_file_sha256=cert[
            "cache_run_manifest_file_sha256"
        ],
        factor_bundle_manifest_sha256=cert[
            "factor_bundle_manifest_sha256"
        ],
        on_retention_certificate_sha256=cert[
            "on_retention_certificate_sha256"
        ],
        file_nbytes=len(raw),
    )


def publish_physical_disposition_artifact(
    path: str | os.PathLike[str],
    result: Mapping[str, Any],
    *,
    expected_physical_disposition_certificate_sha256: str,
    maximum_artifact_bytes: int = PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES,
) -> PhysicalDispositionArtifactReceipt:
    """Atomically publish one complete physical-disposition result."""
    maximum_artifact_bytes = core._strict_int(
        maximum_artifact_bytes,
        "physical-disposition artifact byte capacity",
    )
    if maximum_artifact_bytes < 1:
        raise core.V0P6ContractError(
            "physical-disposition artifact byte capacity must be positive"
        )
    validated = validate_physical_disposition_result(
        result,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    payload = core.canonical_json_bytes(validated)
    if len(payload) > maximum_artifact_bytes:
        raise core.V0P6CapacityError(
            "physical-disposition artifact exceeds its byte cap"
        )
    _atomic_read_only_publish(Path(path), payload)
    return _receipt(payload, validated)


def publish_m37_physical_disposition_artifact(
    path: str | os.PathLike[str],
    result: Mapping[str, Any],
    *,
    expected_physical_disposition_certificate_sha256: str,
) -> PhysicalDispositionArtifactReceipt:
    validated = validate_m37_physical_disposition_result(
        result,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    return publish_physical_disposition_artifact(
        path,
        validated,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )


def open_physical_disposition_artifact(
    path: str | os.PathLike[str],
    *,
    expected_file_sha256: str,
    expected_physical_disposition_certificate_sha256: str,
    expected_run_id: str,
    expected_window_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_certificate_sha256: str,
    maximum_artifact_bytes: int = PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES,
) -> PhysicalDispositionArtifact:
    """Reopen a complete result against independent identity roots."""
    maximum_artifact_bytes = core._strict_int(
        maximum_artifact_bytes,
        "physical-disposition artifact byte capacity",
    )
    if maximum_artifact_bytes < 1:
        raise core.V0P6ContractError(
            "physical-disposition artifact byte capacity must be positive"
        )
    artifact_path = Path(path)
    if artifact_path.is_file():
        stream = artifact_path.open("rb")
    else:
        compressed_path = Path(f"{artifact_path}.gz")
        if not compressed_path.is_file():
            raise FileNotFoundError(artifact_path)
        stream = gzip.open(compressed_path, "rb")
    with stream:
        raw = stream.read(maximum_artifact_bytes + 1)
    if len(raw) > maximum_artifact_bytes:
        raise core.V0P6CapacityError(
            "physical-disposition artifact exceeds its byte cap"
        )
    if hashlib.sha256(raw).hexdigest() != _sha256(
        expected_file_sha256, "expected physical-disposition file identity"
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition file identity changed"
        )
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "physical-disposition artifact is invalid JSON"
        ) from error
    if core.canonical_json_bytes(parsed) != raw:
        raise core.V0P6ContractError(
            "physical-disposition artifact is not canonical JSON"
        )
    validated = validate_physical_disposition_result(
        parsed,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    cert = validated["certificate"]
    if (
        not isinstance(expected_run_id, str)
        or not expected_run_id
        or not isinstance(expected_window_id, str)
        or not expected_window_id
        or cert["run_id"] != expected_run_id
        or cert["window_id"] != expected_window_id
        or cert["cache_run_manifest_file_sha256"]
        != _sha256(
            expected_cache_run_manifest_file_sha256,
            "expected cache-run manifest file identity",
        )
        or cert["factor_bundle_manifest_sha256"]
        != _sha256(
            expected_factor_bundle_manifest_sha256,
            "expected factor-bundle manifest identity",
        )
        or cert["on_retention_certificate_sha256"]
        != _sha256(
            expected_on_retention_certificate_sha256,
            "expected ON-retention certificate identity",
        )
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition artifact ancestry changed"
        )
    return PhysicalDispositionArtifact(
        result=validated,
        receipt=_receipt(raw, validated),
    )


def open_m37_physical_disposition_artifact(
    path: str | os.PathLike[str],
    **kwargs: Any,
) -> PhysicalDispositionArtifact:
    opened = open_physical_disposition_artifact(path, **kwargs)
    validate_m37_physical_disposition_result(
        opened.result,
        expected_physical_disposition_certificate_sha256=(
            opened.receipt.physical_disposition_certificate_sha256
        ),
    )
    return opened
