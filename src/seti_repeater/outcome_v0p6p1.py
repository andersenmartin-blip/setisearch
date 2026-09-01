"""Capacity-only final M37 outcome join for the v0.6.1 amendment."""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Mapping, Sequence

from . import capacity_v0p6p1 as capacity_profile
from . import outcome_v0p6 as outcome
from . import search_v0p6 as core


M37_V0P6P1_MAXIMUM_OUTCOME_RECORDS = (
    len(core.M37_WINDOW_IDS)
    * capacity_profile.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
)
M37_V0P6P1_MAXIMUM_OUTCOME_CANONICAL_BYTES = (
    capacity_profile.M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES_TOTAL
)
M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES = (
    M37_V0P6P1_MAXIMUM_OUTCOME_CANONICAL_BYTES + 16_777_216
)


@dataclass(frozen=True)
class M37V0P6P1OutcomeArtifactReceipt:
    path: str
    file_sha256: str
    result_sha256: str
    outcome_certificate_sha256: str
    threshold_certificate_sha256: str
    outcome_record_count: int
    unresolved_candidate_count: int
    global_search_state: str
    global_outcome: str
    outcome_records_canonical_bytes: int
    file_nbytes: int


@dataclass(frozen=True)
class M37V0P6P1OutcomeArtifact:
    result: dict[str, Any]
    receipt: M37V0P6P1OutcomeArtifactReceipt


def _profile(
    value: capacity_profile.M37V0P6P1CapacityProfile,
) -> capacity_profile.M37V0P6P1CapacityProfile:
    if not isinstance(value, capacity_profile.M37V0P6P1CapacityProfile):
        raise outcome.M37ValidationError(
            "outcome v0.6.1 requires the frozen capacity profile"
        )
    return capacity_profile.validate_m37_v0p6p1_capacity_profile_record(
        value.as_record()
    )


def _outcome_capacity(
    profile: capacity_profile.M37V0P6P1CapacityProfile,
) -> outcome.M37OutcomeCapacity:
    profile = _profile(profile)
    return outcome.M37OutcomeCapacity(
        maximum_records_per_window=profile.maximum_records_per_window,
        maximum_record_canonical_bytes=(
            profile.maximum_record_canonical_bytes
        ),
        maximum_evidence_canonical_bytes_per_window=(
            profile.maximum_retention_evidence_canonical_bytes_per_window
        ),
        maximum_alias_bucket_entries_per_window=(
            profile.maximum_alias_bucket_entries_per_window
        ),
        maximum_alias_distinct_candidate_visits_per_window=(
            profile.maximum_alias_distinct_candidate_visits_per_window
        ),
        maximum_alias_identity_track_comparisons_per_window=(
            profile.maximum_alias_identity_track_comparisons_per_window
        ),
        maximum_outcome_records=M37_V0P6P1_MAXIMUM_OUTCOME_RECORDS,
        maximum_outcome_canonical_bytes=(
            M37_V0P6P1_MAXIMUM_OUTCOME_CANONICAL_BYTES
        ),
    )


def assemble_m37_v0p6p1_outcome(
    profile: capacity_profile.M37V0P6P1CapacityProfile,
    window_inputs: Sequence[Mapping[str, Any]],
    *,
    expected_threshold_certificate_sha256: str,
) -> dict[str, Any]:
    """Join all five amended physical and unchanged rank-p products."""
    result = outcome._assemble_m37_outcome_with_capacity(
        window_inputs,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        capacity=_outcome_capacity(profile),
    )
    return validate_m37_v0p6p1_outcome(
        result,
        profile,
        expected_result_sha256=result["result_sha256"],
    )


def validate_m37_v0p6p1_outcome(
    result: Mapping[str, Any],
    profile: capacity_profile.M37V0P6P1CapacityProfile,
    *,
    expected_result_sha256: str,
) -> dict[str, Any]:
    validated = outcome._validate_m37_outcome_with_capacity(
        result,
        expected_result_sha256=expected_result_sha256,
        capacity=_outcome_capacity(profile),
    )
    certificate = validated["certificate"]
    if (
        certificate["maximum_records_per_window"]
        != capacity_profile.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
        or certificate["maximum_outcome_records"]
        != M37_V0P6P1_MAXIMUM_OUTCOME_RECORDS
        or certificate["maximum_outcome_canonical_bytes"]
        != M37_V0P6P1_MAXIMUM_OUTCOME_CANONICAL_BYTES
        or certificate["outcome_record_count"] != len(validated["records"])
    ):
        raise outcome.M37ValidationError(
            "outcome result differs from the M37 v0.6.1 capacity contract"
        )
    return validated


def _atomic_read_only_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise outcome.M37ValidationError(
            "outcome artifact parent directory is absent"
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
                raise OSError("short outcome artifact write")
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


def _receipt(
    path: Path, raw: bytes, result: Mapping[str, Any]
) -> M37V0P6P1OutcomeArtifactReceipt:
    certificate = result["certificate"]
    return M37V0P6P1OutcomeArtifactReceipt(
        path=str(path.absolute()),
        file_sha256=hashlib.sha256(raw).hexdigest(),
        result_sha256=result["result_sha256"],
        outcome_certificate_sha256=certificate[
            "outcome_certificate_sha256"
        ],
        threshold_certificate_sha256=certificate[
            "threshold_certificate_sha256"
        ],
        outcome_record_count=certificate["outcome_record_count"],
        unresolved_candidate_count=certificate[
            "unresolved_candidate_count"
        ],
        global_search_state=certificate["global_search_state"],
        global_outcome=certificate["global_outcome"],
        outcome_records_canonical_bytes=certificate[
            "outcome_records_canonical_bytes"
        ],
        file_nbytes=len(raw),
    )


def publish_m37_v0p6p1_outcome_artifact(
    path: str | os.PathLike[str],
    result: Mapping[str, Any],
    profile: capacity_profile.M37V0P6P1CapacityProfile,
    *,
    expected_result_sha256: str,
) -> M37V0P6P1OutcomeArtifactReceipt:
    validated = validate_m37_v0p6p1_outcome(
        result,
        profile,
        expected_result_sha256=expected_result_sha256,
    )
    raw = core.canonical_json_bytes(validated)
    if len(raw) > M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "M37 v0.6.1 outcome artifact exceeds its byte cap"
        )
    destination = Path(path)
    _atomic_read_only_publish(destination, raw)
    return _receipt(destination, raw, validated)


def _read_artifact_bytes(
    path: Path, profile: capacity_profile.M37V0P6P1CapacityProfile
) -> bytes:
    if path.is_file():
        raw = path.read_bytes()
    else:
        compressed = Path(f"{path}.gz")
        if not compressed.is_file():
            raise FileNotFoundError(path)
        if (
            compressed.stat().st_size
            > profile.maximum_single_compressed_output_file_bytes
        ):
            raise core.V0P6CapacityError(
                "compressed outcome artifact exceeds its byte cap"
            )
        with gzip.open(compressed, "rb") as stream:
            raw = stream.read(M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES + 1)
    if len(raw) > M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "M37 v0.6.1 outcome artifact exceeds its byte cap"
        )
    return raw


def open_m37_v0p6p1_outcome_artifact(
    path: str | os.PathLike[str],
    profile: capacity_profile.M37V0P6P1CapacityProfile,
    *,
    expected_file_sha256: str,
    expected_result_sha256: str,
) -> M37V0P6P1OutcomeArtifact:
    profile = _profile(profile)
    artifact_path = Path(path)
    raw = _read_artifact_bytes(artifact_path, profile)
    if hashlib.sha256(raw).hexdigest() != core._frozen_sha256(
        expected_file_sha256, "expected outcome artifact identity"
    ):
        raise outcome.M37ValidationError("outcome artifact identity changed")
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise outcome.M37ValidationError(
            "outcome artifact is invalid JSON"
        ) from error
    if core.canonical_json_bytes(decoded) != raw:
        raise outcome.M37ValidationError(
            "outcome artifact is not canonical JSON"
        )
    validated = validate_m37_v0p6p1_outcome(
        decoded,
        profile,
        expected_result_sha256=expected_result_sha256,
    )
    return M37V0P6P1OutcomeArtifact(
        result=validated,
        receipt=_receipt(artifact_path, raw, validated),
    )


__all__ = [
    "M37V0P6P1OutcomeArtifact",
    "M37V0P6P1OutcomeArtifactReceipt",
    "M37_V0P6P1_MAXIMUM_OUTCOME_CANONICAL_BYTES",
    "M37_V0P6P1_MAXIMUM_OUTCOME_RECORDS",
    "M37_V0P6P1_OUTCOME_ARTIFACT_MAXIMUM_BYTES",
    "assemble_m37_v0p6p1_outcome",
    "open_m37_v0p6p1_outcome_artifact",
    "publish_m37_v0p6p1_outcome_artifact",
    "validate_m37_v0p6p1_outcome",
]
