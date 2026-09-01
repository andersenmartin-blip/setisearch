"""Capacity-only M37 v0.6.1 global rank-p continuation.

The scientific rank-p calculation remains the detector-v0.6 implementation.
This adapter admits only the sealed post-contact capacity profile and keeps the
original v0.6 M37 entry points unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Mapping, Sequence

import numpy as np

from . import capacity_v0p6p1 as capacity
from . import physical_v0p6p1 as physical
from . import search_v0p6 as core
from . import significance_v0p6 as significance


M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES = (
    capacity.M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES + 16_777_216
)


@dataclass(frozen=True)
class M37V0P6P1SignificanceArtifactReceipt:
    path: str
    file_sha256: str
    result_sha256: str
    significance_certificate_sha256: str
    retention_certificate_sha256: str
    threshold_certificate_sha256: str
    window_id: str
    record_count: int
    scientifically_eligible_count: int
    evidence_canonical_bytes: int
    file_nbytes: int


@dataclass(frozen=True)
class M37V0P6P1SignificanceArtifact:
    result: dict[str, Any]
    receipt: M37V0P6P1SignificanceArtifactReceipt


def _profile(
    value: capacity.M37V0P6P1CapacityProfile,
) -> capacity.M37V0P6P1CapacityProfile:
    if not isinstance(value, capacity.M37V0P6P1CapacityProfile):
        raise core.V0P6ContractError(
            "significance v0.6.1 requires the frozen capacity profile"
        )
    return capacity.validate_m37_v0p6p1_capacity_profile_record(
        value.as_record()
    )


def _require_contract(
    profile: capacity.M37V0P6P1CapacityProfile,
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str,
    expected_threshold_certificate_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    cert = physical.validate_m37_v0p6p1_retention_certificate(
        on_certificate,
        profile,
        expected_kind="on",
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    core.validate_threshold_certificate(
        threshold_certificate,
        expected_certificate_sha256=expected_threshold_certificate_sha256,
    )
    significance._require_m37_contract(
        cert,
        threshold_certificate,
        np.asarray(global_null_maxima),
        grid,
        maximum_records_per_window=profile.maximum_records_per_window,
        maximum_record_canonical_bytes=(
            profile.maximum_record_canonical_bytes
        ),
        maximum_evidence_canonical_bytes=(
            profile.maximum_retention_evidence_canonical_bytes_per_window
        ),
    )
    return cert


def evaluate_m37_v0p6p1_global_rank_significance(
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str,
    expected_threshold_certificate_sha256: str,
) -> dict[str, Any]:
    """Evaluate unchanged inclusive M37 rank-p under amended capacities."""
    _require_contract(
        profile,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    result = significance.evaluate_global_rank_significance(
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        core.make_line_template_bank(),
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    return validate_m37_v0p6p1_global_rank_significance(
        result,
        profile,
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        expected_result_sha256=result["result_sha256"],
    )


def validate_m37_v0p6p1_global_rank_significance(
    result: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str,
    expected_threshold_certificate_sha256: str,
    expected_result_sha256: str,
) -> dict[str, Any]:
    """Reproduce every rank-p item from the amended sealed inputs."""
    profile = _profile(profile)
    cert = _require_contract(
        profile,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    validated = significance.validate_global_rank_significance(
        result,
        on_records,
        cert,
        threshold_certificate,
        global_null_maxima,
        grid,
        core.make_line_template_bank(),
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        expected_result_sha256=expected_result_sha256,
    )
    certificate = validated["certificate"]
    if (
        certificate["window_id"] != cert["window_id"]
        or certificate["input_record_count"] != len(on_records)
        or certificate["evidence_record_count"] != len(on_records)
        or certificate["maximum_evidence_canonical_bytes"]
        != profile.maximum_retention_evidence_canonical_bytes_per_window
        or certificate["retention_certificate_sha256"]
        != expected_on_certificate_sha256
        or certificate["threshold_certificate_sha256"]
        != expected_threshold_certificate_sha256
    ):
        raise core.V0P6IncompleteError(
            "significance result differs from the M37 v0.6.1 contract"
        )
    return validated


def _atomic_read_only_publish(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir():
        raise core.V0P6ContractError(
            "significance artifact parent directory is absent"
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
                raise OSError("short significance artifact write")
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


def _artifact_receipt(
    path: Path, raw: bytes, result: Mapping[str, Any]
) -> M37V0P6P1SignificanceArtifactReceipt:
    certificate = result["certificate"]
    evidence = result["evidence"]
    return M37V0P6P1SignificanceArtifactReceipt(
        path=str(path.absolute()),
        file_sha256=hashlib.sha256(raw).hexdigest(),
        result_sha256=result["result_sha256"],
        significance_certificate_sha256=certificate[
            "significance_certificate_sha256"
        ],
        retention_certificate_sha256=certificate[
            "retention_certificate_sha256"
        ],
        threshold_certificate_sha256=certificate[
            "threshold_certificate_sha256"
        ],
        window_id=certificate["window_id"],
        record_count=len(evidence),
        scientifically_eligible_count=sum(
            item["scientifically_eligible"] for item in evidence
        ),
        evidence_canonical_bytes=certificate[
            "evidence_canonical_bytes"
        ],
        file_nbytes=len(raw),
    )


def publish_m37_v0p6p1_significance_artifact(
    path: str | os.PathLike[str],
    result: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str,
    expected_threshold_certificate_sha256: str,
    expected_result_sha256: str,
) -> M37V0P6P1SignificanceArtifactReceipt:
    validated = validate_m37_v0p6p1_global_rank_significance(
        result,
        profile,
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        expected_result_sha256=expected_result_sha256,
    )
    raw = core.canonical_json_bytes(validated)
    if len(raw) > M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "M37 v0.6.1 significance artifact exceeds its byte cap"
        )
    destination = Path(path)
    _atomic_read_only_publish(destination, raw)
    return _artifact_receipt(destination, raw, validated)


def _read_artifact_bytes(
    path: Path, profile: capacity.M37V0P6P1CapacityProfile
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
                "compressed significance artifact exceeds its byte cap"
            )
        with gzip.open(compressed, "rb") as stream:
            raw = stream.read(
                M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES + 1
            )
    if len(raw) > M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES:
        raise core.V0P6CapacityError(
            "M37 v0.6.1 significance artifact exceeds its byte cap"
        )
    return raw


def open_m37_v0p6p1_significance_artifact(
    path: str | os.PathLike[str],
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_file_sha256: str,
    expected_on_certificate_sha256: str,
    expected_threshold_certificate_sha256: str,
    expected_result_sha256: str,
) -> M37V0P6P1SignificanceArtifact:
    profile = _profile(profile)
    artifact_path = Path(path)
    raw = _read_artifact_bytes(artifact_path, profile)
    if hashlib.sha256(raw).hexdigest() != core._frozen_sha256(
        expected_file_sha256, "expected significance artifact identity"
    ):
        raise core.V0P6IncompleteError(
            "significance artifact file identity changed"
        )
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "significance artifact is invalid JSON"
        ) from error
    if core.canonical_json_bytes(result) != raw:
        raise core.V0P6ContractError(
            "significance artifact is not canonical JSON"
        )
    validated = validate_m37_v0p6p1_global_rank_significance(
        result,
        profile,
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
        expected_result_sha256=expected_result_sha256,
    )
    return M37V0P6P1SignificanceArtifact(
        result=validated,
        receipt=_artifact_receipt(artifact_path, raw, validated),
    )


__all__ = [
    "M37V0P6P1SignificanceArtifact",
    "M37V0P6P1SignificanceArtifactReceipt",
    "M37_V0P6P1_SIGNIFICANCE_ARTIFACT_MAXIMUM_BYTES",
    "evaluate_m37_v0p6p1_global_rank_significance",
    "open_m37_v0p6p1_significance_artifact",
    "publish_m37_v0p6p1_significance_artifact",
    "validate_m37_v0p6p1_global_rank_significance",
]
