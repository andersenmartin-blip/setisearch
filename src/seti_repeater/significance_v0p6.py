"""Deterministic global rank-p evidence for detector-v0.6 retention.

This module deliberately leaves the hash-bound retained ON records untouched.
It emits a separate evidence item for every raw retained record ID and binds the
complete result to the retention, threshold, null-vector, grid, and template
bank identities.  No function in this module opens or reads spectral data.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


SIGNIFICANCE_ARTIFACT_TYPE = "seti_repeater.detector_v0p6_global_rank_p"
SIGNIFICANCE_SCHEMA_VERSION = 1
INCLUSIVE_NULL_COMPARISON = "null_maximum_snr >= retained_on_snr"
INCLUSIVE_RANK_P_DEFINITION = (
    "(1 + inclusive_null_exceedance_count) / (global_null_count + 1)"
)
SCIENTIFIC_ELIGIBILITY_COMPARISON = (
    "retained_at_operational_threshold and inclusive_global_rank_p "
    "<= scientific_empirical_p_ceiling"
)
EVIDENCE_SORT_ORDER = "record_id ascending lowercase SHA-256"

_SIGNIFICANCE_RESULT_ATTESTATIONS: dict[str, bytes] = {}
_SIGNIFICANCE_RESULT_ATTESTATION_CAP = 1_024

_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "record_id",
        "retained_record_sha256",
        "retained_snr",
        "global_null_count",
        "inclusive_null_comparison",
        "inclusive_null_exceedance_count",
        "inclusive_rank_p_definition",
        "inclusive_global_rank_p",
        "scientific_empirical_p_ceiling",
        "scientific_eligibility_comparison",
        "scientifically_eligible",
        "evidence_sha256",
    }
)

_CERTIFICATE_PAYLOAD_FIELDS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "window_id",
        "source_scan_kind",
        "evidence_sort_order",
        "inclusive_null_comparison",
        "inclusive_rank_p_definition",
        "scientific_eligibility_comparison",
        "scientific_eligibility_requires_retained_operational_threshold",
        "retention_certificate_sha256",
        "threshold_certificate_sha256",
        "source_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "template_count",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "factor_table_sha256",
        "threshold_window_ids",
        "global_null_shape",
        "global_null_dtype_encoding",
        "global_null_maxima_sha256",
        "global_null_count",
        "operational_threshold_snr",
        "scientific_empirical_p_ceiling",
        "input_record_count",
        "evidence_record_count",
        "record_ids_sha256",
        "evidence_item_sha256s_sha256",
        "evidence_sha256",
        "evidence_canonical_bytes",
        "maximum_evidence_canonical_bytes",
        "all_input_records_evaluated_exactly_once",
        "truncation_permitted",
    }
)
_CERTIFICATE_FIELDS = _CERTIFICATE_PAYLOAD_FIELDS | {
    "significance_certificate_sha256"
}
_RESULT_FIELDS = frozenset({"evidence", "certificate", "result_sha256"})


def _canonical_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    try:
        return json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            f"{label} is not canonical finite JSON"
        ) from error


def _canonical_template_bank(
    template_bank: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    try:
        bank = json.loads(core.canonical_json_bytes(list(template_bank)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "significance template bank is not canonical finite JSON"
        ) from error
    if not bank:
        raise core.V0P6ContractError(
            "significance requires a non-empty template bank"
        )
    for ordinal, template in enumerate(bank):
        if not isinstance(template, dict) or core._strict_int(
            template.get("template_index"), "template index"
        ) != ordinal:
            raise core.V0P6ContractError(
                "significance template bank is not in canonical index order"
            )
    return tuple(bank)


def _validated_null_maxima(
    global_null_maxima: np.ndarray,
    threshold_certificate: core.ThresholdCertificate,
) -> np.ndarray:
    raw = np.asarray(global_null_maxima)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.floating):
        raise core.V0P6ContractError(
            "global null maxima must be a one-dimensional float vector"
        )
    expected_count = core._strict_int(
        threshold_certificate.global_null_count, "global null count"
    )
    if raw.shape != (expected_count,):
        raise core.V0P6IncompleteError(
            "global null maxima shape/count differs from the threshold certificate"
        )
    values = np.asarray(raw, dtype=np.float64, order="C")
    if not np.all(np.isfinite(values)):
        raise core.V0P6ContractError("global null maxima must all be finite")
    observed_sha256 = core.float64_vector_sha256(values)
    if observed_sha256 != threshold_certificate.global_null_maxima_sha256:
        raise core.V0P6IncompleteError(
            "global null maxima SHA-256 differs from the threshold certificate"
        )

    threshold = float(threshold_certificate.operational_threshold_snr)
    exceedances = int(np.count_nonzero(values >= threshold))
    if exceedances != core._strict_int(
        threshold_certificate.inclusive_null_exceedances_at_threshold,
        "threshold inclusive exceedance count",
    ):
        raise core.V0P6IncompleteError(
            "global null maxima do not reproduce the threshold exceedance count"
        )
    rank_p = float((1 + exceedances) / (expected_count + 1))
    if rank_p != float(threshold_certificate.inclusive_rank_p_at_threshold):
        raise core.V0P6IncompleteError(
            "global null maxima do not reproduce the threshold rank p-value"
        )
    empirical = float(
        np.quantile(
            values,
            float(threshold_certificate.empirical_quantile),
            method="higher",
        )
    )
    if empirical != float(
        threshold_certificate.empirical_higher_quantile_snr
    ):
        raise core.V0P6IncompleteError(
            "global null maxima do not reproduce the certified higher quantile"
        )
    return values


def _validated_inputs(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    template_bank: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str | None,
    expected_threshold_certificate_sha256: str | None,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    np.ndarray,
    tuple[dict[str, Any], ...],
]:
    core.validate_threshold_certificate(
        threshold_certificate,
        expected_certificate_sha256=expected_threshold_certificate_sha256,
    )
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if cert["scan_kind"] != "on":
        raise core.V0P6ContractError(
            "global rank-p significance requires an ON retention product"
        )

    threshold_sha256 = threshold_certificate.certificate_sha256
    if cert["threshold_certificate_sha256"] != threshold_sha256:
        raise core.V0P6ContractError(
            "retention and threshold certificate identities differ"
        )
    if str(cert["window_id"]) not in threshold_certificate.window_ids:
        raise core.V0P6ContractError(
            "retention window is absent from the global threshold inventory"
        )
    shared_contract = (
        ("experiment_contract_sha256", "experiment_contract_sha256"),
        ("factor_basis_sha256", "factor_basis_sha256"),
        ("factor_basis_labels_sha256", "factor_basis_labels_sha256"),
        ("scan_inventory_sha256", "scan_inventory_sha256"),
        ("factor_table_sha256", "factor_table_sha256"),
        ("analysis_contract_sha256", "analysis_contract_sha256"),
    )
    for retention_field, threshold_field in shared_contract:
        if cert[retention_field] != getattr(
            threshold_certificate, threshold_field
        ):
            raise core.V0P6ContractError(
                f"retention and threshold {retention_field} differ"
            )
    if cert["factor_row_selection_sha256"] != (
        threshold_certificate.calibration_factor_row_selection_sha256
    ):
        raise core.V0P6ContractError(
            "retention ON rows differ from the threshold calibration rows"
        )
    if float(cert["operational_threshold_snr"]) != float(
        threshold_certificate.operational_threshold_snr
    ):
        raise core.V0P6ContractError(
            "retention and threshold operational S/N differ"
        )

    bank = _canonical_template_bank(template_bank)
    bank_sha256 = core.template_bank_sha256(list(bank))
    if bank_sha256 != cert["template_bank_sha256"]:
        raise core.V0P6ContractError(
            "significance template bank differs from retention"
        )
    values = _validated_null_maxima(
        global_null_maxima, threshold_certificate
    )
    reconstructed_experiment = core.hypothesis_contract_sha256(
        score_bin_count=grid.score_bin_count,
        epoch_count=core._strict_int(cert["epoch_count"], "epoch count"),
        template_count=len(bank),
        template_bank_sha256_value=bank_sha256,
        spectral_widths=cert["spectral_widths"],
        activity_subsets=cert["activity_subsets"],
        minimum_active_epoch_snr=cert["minimum_active_epoch_snr"],
        stack_statistic=cert["stack_statistic"],
        scramble_count=values.size,
    )
    if reconstructed_experiment != cert["experiment_contract_sha256"]:
        raise core.V0P6ContractError(
            "grid/bank/template/null dimensions do not reproduce the experiment contract"
        )

    records = core._validated_retained_records(
        on_records,
        cert,
        grid,
        expected_kind="on",
        expected_template_count=len(bank),
        template_bank=bank,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    identifiers = [str(record["record_id"]) for record in records]
    if len(identifiers) != len(set(identifiers)):
        raise core.V0P6IncompleteError(
            "retained ON record IDs are not unique"
        )
    return records, cert, values, bank


def _evidence_item(
    record: Mapping[str, Any],
    null_maxima: np.ndarray,
    scientific_p_ceiling: float,
) -> dict[str, Any]:
    score = float(record["snr"])
    exceedances = int(np.count_nonzero(null_maxima >= score))
    rank_p = float((1 + exceedances) / (null_maxima.size + 1))
    payload = {
        "schema_version": SIGNIFICANCE_SCHEMA_VERSION,
        "record_id": str(record["record_id"]),
        "retained_record_sha256": hashlib.sha256(
            core.canonical_json_bytes(dict(record))
        ).hexdigest(),
        "retained_snr": score,
        "global_null_count": int(null_maxima.size),
        "inclusive_null_comparison": INCLUSIVE_NULL_COMPARISON,
        "inclusive_null_exceedance_count": exceedances,
        "inclusive_rank_p_definition": INCLUSIVE_RANK_P_DEFINITION,
        "inclusive_global_rank_p": rank_p,
        "scientific_empirical_p_ceiling": scientific_p_ceiling,
        "scientific_eligibility_comparison": (
            SCIENTIFIC_ELIGIBILITY_COMPARISON
        ),
        "scientifically_eligible": bool(rank_p <= scientific_p_ceiling),
    }
    item = dict(payload)
    item["evidence_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(payload)
    ).hexdigest()
    return item


def _derive_global_rank_significance(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    template_bank: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str | None,
    expected_threshold_certificate_sha256: str | None,
) -> dict[str, Any]:
    records, cert, null_maxima, bank = _validated_inputs(
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        template_bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    ceiling = float(threshold_certificate.scientific_empirical_p_ceiling)
    evidence = sorted(
        (
            _evidence_item(record, null_maxima, ceiling)
            for record in records
        ),
        key=lambda item: item["record_id"],
    )
    record_ids = [item["record_id"] for item in evidence]
    evidence_item_sha256s = [item["evidence_sha256"] for item in evidence]
    evidence_bytes = core.canonical_json_bytes(evidence)
    evidence_cap = cert["maximum_evidence_canonical_bytes"]
    if evidence_cap is not None and len(evidence_bytes) > core._strict_int(
        evidence_cap, "significance evidence-byte capacity"
    ):
        raise core.V0P6CapacityError(
            "global rank-p evidence exceeds the frozen evidence-byte capacity"
        )

    certificate_payload = {
        "artifact_type": SIGNIFICANCE_ARTIFACT_TYPE,
        "schema_version": SIGNIFICANCE_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_id": str(cert["window_id"]),
        "source_scan_kind": "on",
        "evidence_sort_order": EVIDENCE_SORT_ORDER,
        "inclusive_null_comparison": INCLUSIVE_NULL_COMPARISON,
        "inclusive_rank_p_definition": INCLUSIVE_RANK_P_DEFINITION,
        "scientific_eligibility_comparison": (
            SCIENTIFIC_ELIGIBILITY_COMPARISON
        ),
        "scientific_eligibility_requires_retained_operational_threshold": True,
        "retention_certificate_sha256": cert[
            "retention_certificate_sha256"
        ],
        "threshold_certificate_sha256": (
            threshold_certificate.certificate_sha256
        ),
        "source_records_sha256": cert["records_sha256"],
        "proxy_grid_sha256": cert["proxy_grid_sha256"],
        "template_bank_sha256": cert["template_bank_sha256"],
        "template_count": len(bank),
        "experiment_contract_sha256": cert[
            "experiment_contract_sha256"
        ],
        "analysis_contract_sha256": cert["analysis_contract_sha256"],
        "factor_basis_sha256": cert["factor_basis_sha256"],
        "factor_basis_labels_sha256": cert[
            "factor_basis_labels_sha256"
        ],
        "scan_inventory_sha256": cert["scan_inventory_sha256"],
        "on_factor_row_selection_sha256": cert[
            "factor_row_selection_sha256"
        ],
        "factor_table_sha256": cert["factor_table_sha256"],
        "threshold_window_ids": list(threshold_certificate.window_ids),
        "global_null_shape": [int(null_maxima.size)],
        "global_null_dtype_encoding": "little-endian float64",
        "global_null_maxima_sha256": (
            threshold_certificate.global_null_maxima_sha256
        ),
        "global_null_count": int(null_maxima.size),
        "operational_threshold_snr": float(
            threshold_certificate.operational_threshold_snr
        ),
        "scientific_empirical_p_ceiling": ceiling,
        "input_record_count": len(records),
        "evidence_record_count": len(evidence),
        "record_ids_sha256": hashlib.sha256(
            core.canonical_json_bytes(record_ids)
        ).hexdigest(),
        "evidence_item_sha256s_sha256": hashlib.sha256(
            core.canonical_json_bytes(evidence_item_sha256s)
        ).hexdigest(),
        "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "evidence_canonical_bytes": len(evidence_bytes),
        "maximum_evidence_canonical_bytes": evidence_cap,
        "all_input_records_evaluated_exactly_once": True,
        "truncation_permitted": False,
    }
    certificate = dict(certificate_payload)
    certificate["significance_certificate_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(certificate_payload)
    ).hexdigest()
    result_payload = {
        "evidence": evidence,
        "certificate": certificate,
    }
    result = dict(result_payload)
    result["result_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(result_payload)
    ).hexdigest()
    return json.loads(core.canonical_json_bytes(result))


def evaluate_global_rank_significance(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    template_bank: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str | None = None,
    expected_threshold_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Emit one deterministic inclusive global-rank-p item per retained ID."""
    result = _derive_global_rank_significance(
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        template_bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    digest = result["result_sha256"]
    encoded = core.canonical_json_bytes(result)
    existing = _SIGNIFICANCE_RESULT_ATTESTATIONS.get(digest)
    if existing is not None and existing != encoded:
        raise core.V0P6IncompleteError(
            "global rank-p result digest collision"
        )
    if existing is None and len(_SIGNIFICANCE_RESULT_ATTESTATIONS) >= (
        _SIGNIFICANCE_RESULT_ATTESTATION_CAP
    ):
        raise core.V0P6CapacityError(
            "global rank-p result attestation capacity exceeded"
        )
    _SIGNIFICANCE_RESULT_ATTESTATIONS[digest] = encoded
    return result


def _validate_result_envelope(
    result: Mapping[str, Any],
    *,
    expected_result_sha256: str | None,
) -> dict[str, Any]:
    detached = _canonical_mapping(result, "global rank-p result")
    if frozenset(detached) != _RESULT_FIELDS:
        raise core.V0P6ContractError(
            "global rank-p result fields do not match the schema"
        )
    observed_digest = core._frozen_sha256(
        detached["result_sha256"], "global rank-p result identity"
    )
    payload = {
        "evidence": detached["evidence"],
        "certificate": detached["certificate"],
    }
    if hashlib.sha256(core.canonical_json_bytes(payload)).hexdigest() != (
        observed_digest
    ):
        raise core.V0P6IncompleteError("global rank-p result SHA-256 changed")
    expected_digest = (
        None
        if expected_result_sha256 is None
        else core._frozen_sha256(
            expected_result_sha256, "expected global rank-p result identity"
        )
    )
    live_matches = (
        _SIGNIFICANCE_RESULT_ATTESTATIONS.get(observed_digest)
        == core.canonical_json_bytes(detached)
    )
    trusted_matches = expected_digest == observed_digest
    if not live_matches and not trusted_matches:
        raise core.V0P6ContractError(
            "global rank-p result lacks a live or independently trusted attestation"
        )
    return detached


def _validate_evidence_and_certificate(result: dict[str, Any]) -> None:
    evidence = result["evidence"]
    certificate = result["certificate"]
    if not isinstance(evidence, list) or not isinstance(certificate, dict):
        raise core.V0P6ContractError(
            "global rank-p result evidence/certificate types are invalid"
        )
    if frozenset(certificate) != _CERTIFICATE_FIELDS:
        raise core.V0P6ContractError(
            "global rank-p certificate fields do not match the schema"
        )
    certificate_payload = dict(certificate)
    certificate_digest = core._frozen_sha256(
        certificate_payload.pop("significance_certificate_sha256"),
        "global rank-p certificate identity",
    )
    if hashlib.sha256(
        core.canonical_json_bytes(certificate_payload)
    ).hexdigest() != certificate_digest:
        raise core.V0P6IncompleteError(
            "global rank-p certificate SHA-256 changed"
        )
    if frozenset(certificate_payload) != _CERTIFICATE_PAYLOAD_FIELDS:
        raise core.V0P6ContractError(
            "global rank-p certificate payload does not match the schema"
        )
    schema_version = core._strict_int(
        certificate["schema_version"], "significance schema version"
    )
    template_count = core._strict_int(
        certificate["template_count"], "significance template count"
    )
    global_null_count = core._strict_int(
        certificate["global_null_count"], "significance global null count"
    )
    global_null_shape = certificate["global_null_shape"]
    if not isinstance(global_null_shape, list) or len(global_null_shape) != 1:
        raise core.V0P6ContractError(
            "global rank-p null shape is not a one-axis JSON shape"
        )
    global_null_shape_count = core._strict_int(
        global_null_shape[0], "significance global null shape"
    )
    operational_threshold = core._finite_json_number(
        certificate["operational_threshold_snr"],
        "significance operational threshold",
    )
    scientific_p_ceiling = core._finite_json_number(
        certificate["scientific_empirical_p_ceiling"],
        "significance scientific p-value ceiling",
    )
    evidence_byte_cap = certificate["maximum_evidence_canonical_bytes"]
    if evidence_byte_cap is not None:
        evidence_byte_cap = core._strict_int(
            evidence_byte_cap, "significance evidence-byte capacity"
        )
    if (
        template_count < 1
        or global_null_count < 1
        or global_null_shape_count != global_null_count
        or not 0.0 < scientific_p_ceiling <= 1.0
        or (evidence_byte_cap is not None and evidence_byte_cap < 1)
    ):
        raise core.V0P6ContractError(
            "global rank-p certificate numeric values are invalid"
        )
    if (
        certificate["artifact_type"] != SIGNIFICANCE_ARTIFACT_TYPE
        or schema_version != SIGNIFICANCE_SCHEMA_VERSION
        or certificate["source_scan_kind"] != "on"
        or certificate["evidence_sort_order"] != EVIDENCE_SORT_ORDER
        or certificate["inclusive_null_comparison"]
        != INCLUSIVE_NULL_COMPARISON
        or certificate["inclusive_rank_p_definition"]
        != INCLUSIVE_RANK_P_DEFINITION
        or certificate["scientific_eligibility_comparison"]
        != SCIENTIFIC_ELIGIBILITY_COMPARISON
        or certificate[
            "scientific_eligibility_requires_retained_operational_threshold"
        ]
        is not True
        or certificate["all_input_records_evaluated_exactly_once"] is not True
        or certificate["truncation_permitted"] is not False
        or certificate["global_null_dtype_encoding"]
        != "little-endian float64"
    ):
        raise core.V0P6ContractError(
            "global rank-p certificate semantics changed"
        )

    expected_count = core._strict_int(
        certificate["evidence_record_count"], "significance evidence count"
    )
    input_count = core._strict_int(
        certificate["input_record_count"], "significance input record count"
    )
    if expected_count < 0 or input_count != expected_count or len(evidence) != (
        expected_count
    ):
        raise core.V0P6IncompleteError(
            "global rank-p evidence count is incomplete"
        )
    ids: list[str] = []
    item_hashes: list[str] = []
    for raw_item in evidence:
        item = _canonical_mapping(raw_item, "global rank-p evidence item")
        if frozenset(item) != _EVIDENCE_FIELDS:
            raise core.V0P6ContractError(
                "global rank-p evidence fields do not match the schema"
            )
        item_digest = core._frozen_sha256(
            item.pop("evidence_sha256"), "global rank-p evidence identity"
        )
        if hashlib.sha256(core.canonical_json_bytes(item)).hexdigest() != (
            item_digest
        ):
            raise core.V0P6IncompleteError(
                "global rank-p evidence SHA-256 changed"
            )
        record_id = core._frozen_sha256(
            item["record_id"], "retained ON record identity"
        )
        core._frozen_sha256(
            item["retained_record_sha256"], "retained ON record bytes"
        )
        item_schema_version = core._strict_int(
            item["schema_version"], "significance evidence schema version"
        )
        if (
            item_schema_version != SIGNIFICANCE_SCHEMA_VERSION
            or item["inclusive_null_comparison"]
            != INCLUSIVE_NULL_COMPARISON
            or item["inclusive_rank_p_definition"]
            != INCLUSIVE_RANK_P_DEFINITION
            or item["scientific_eligibility_comparison"]
            != SCIENTIFIC_ELIGIBILITY_COMPARISON
            or not isinstance(item["scientifically_eligible"], bool)
        ):
            raise core.V0P6ContractError(
                "global rank-p evidence semantics changed"
            )
        null_count = core._strict_int(
            item["global_null_count"], "evidence global null count"
        )
        exceedances = core._strict_int(
            item["inclusive_null_exceedance_count"],
            "evidence inclusive exceedance count",
        )
        score = core._finite_json_number(
            item["retained_snr"], "significance retained S/N"
        )
        rank_p = core._finite_json_number(
            item["inclusive_global_rank_p"],
            "significance inclusive global rank p-value",
        )
        ceiling = core._finite_json_number(
            item["scientific_empirical_p_ceiling"],
            "significance evidence scientific p-value ceiling",
        )
        if (
            null_count != global_null_count
            or not 0 <= exceedances <= null_count
            or score < operational_threshold
            or ceiling != scientific_p_ceiling
        ):
            raise core.V0P6ContractError(
                "global rank-p evidence numeric values are invalid"
            )
        expected_p = float((1 + exceedances) / (null_count + 1))
        if rank_p != expected_p or bool(
            item["scientifically_eligible"]
        ) != bool(expected_p <= ceiling):
            raise core.V0P6ContractError(
                "global rank-p evidence calculation changed"
            )
        ids.append(record_id)
        item_hashes.append(item_digest)

    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise core.V0P6IncompleteError(
            "global rank-p evidence IDs are duplicated or not canonically sorted"
        )
    if hashlib.sha256(core.canonical_json_bytes(ids)).hexdigest() != (
        certificate["record_ids_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "global rank-p evidence record-ID inventory changed"
        )
    if hashlib.sha256(core.canonical_json_bytes(item_hashes)).hexdigest() != (
        certificate["evidence_item_sha256s_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "global rank-p evidence item inventory changed"
        )
    evidence_bytes = core.canonical_json_bytes(evidence)
    evidence_byte_count = core._strict_int(
        certificate["evidence_canonical_bytes"],
        "significance evidence byte count",
    )
    if (
        hashlib.sha256(evidence_bytes).hexdigest()
        != certificate["evidence_sha256"]
        or len(evidence_bytes) != evidence_byte_count
        or (
            evidence_byte_cap is not None
            and evidence_byte_count > evidence_byte_cap
        )
    ):
        raise core.V0P6IncompleteError(
            "global rank-p aggregate evidence identity changed"
        )


def validate_global_rank_significance(
    result: Mapping[str, Any],
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    template_bank: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str | None = None,
    expected_threshold_certificate_sha256: str | None = None,
    expected_result_sha256: str | None = None,
) -> dict[str, Any]:
    """Fail closed unless a significance result exactly reproduces upstream."""
    detached = _validate_result_envelope(
        result, expected_result_sha256=expected_result_sha256
    )
    _validate_evidence_and_certificate(detached)
    expected = _derive_global_rank_significance(
        on_records,
        on_certificate,
        threshold_certificate,
        global_null_maxima,
        grid,
        template_bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_threshold_certificate_sha256=(
            expected_threshold_certificate_sha256
        ),
    )
    expected_ids = [item["record_id"] for item in expected["evidence"]]
    observed_ids = [item["record_id"] for item in detached["evidence"]]
    if observed_ids != expected_ids:
        raise core.V0P6IncompleteError(
            "global rank-p evidence does not cover every retained ON record exactly once"
        )
    if core.canonical_json_bytes(detached) != core.canonical_json_bytes(expected):
        raise core.V0P6IncompleteError(
            "global rank-p result does not reproduce from its sealed inputs"
        )
    return detached


def _require_m37_contract(
    cert: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
) -> None:
    window_id = str(cert["window_id"])
    if window_id not in core.M37_WINDOW_IDS:
        raise core.V0P6ContractError(
            "M37 significance received an unknown window identity"
        )
    expected_grid = core.make_m37_proxy_carrier_grid(window_id)
    if core.proxy_carrier_grid_sha256(grid) != core.proxy_carrier_grid_sha256(
        expected_grid
    ):
        raise core.V0P6ContractError(
            "M37 significance did not receive the exact window q grid"
        )
    expected_hypotheses = (
        core.M37_TEMPLATE_COUNT
        * len(core.M37_SPECTRAL_WIDTHS)
        * len(core.M37_ACTIVITY_SUBSETS)
    )
    if (
        threshold_certificate.window_ids != core.M37_WINDOW_IDS
        or threshold_certificate.global_null_count != core.M37_SCRAMBLE_COUNT
        or null_maxima.shape != (core.M37_SCRAMBLE_COUNT,)
        or threshold_certificate.scramble_table_sha256s
        != core.M37_SCRAMBLE_TABLE_SHA256S
        or threshold_certificate.experiment_contract_sha256
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or threshold_certificate.factor_basis_sha256
        != core.M37_FACTOR_BASIS_SHA256
        or threshold_certificate.factor_basis_labels_sha256
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or threshold_certificate.scan_inventory_sha256
        != core.M37_SCAN_INVENTORY_SHA256
        or threshold_certificate.calibration_factor_row_selection_sha256
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or threshold_certificate.calibration_execution_engines
        != (core.M37_CALIBRATION_EXECUTION_ENGINE,) * len(core.M37_WINDOW_IDS)
        or len(
            set(threshold_certificate.calibration_execution_identity_sha256s)
        )
        != 1
        or threshold_certificate.reference_floor_snr
        != core.M37_THRESHOLD_REFERENCE_FLOOR_SNR
        or threshold_certificate.empirical_quantile
        != core.M37_THRESHOLD_QUANTILE
        or threshold_certificate.scientific_empirical_p_ceiling
        != core.M37_SCIENTIFIC_P_CEILING
        or cert["template_bank_sha256"] != core.M37_BANK_SHA256
        or cert["factor_basis_sha256"] != core.M37_FACTOR_BASIS_SHA256
        or cert["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or cert["scan_inventory_sha256"] != core.M37_SCAN_INVENTORY_SHA256
        or cert["factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or cert["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or tuple(cert["spectral_widths"]) != core.M37_SPECTRAL_WIDTHS
        or tuple(tuple(item) for item in cert["activity_subsets"])
        != core.M37_ACTIVITY_SUBSETS
        or core._strict_int(cert["epoch_count"], "M37 epoch count") != 3
        or core._strict_int(
            cert["expected_hypotheses"], "M37 hypothesis count"
        )
        != expected_hypotheses
        or core._strict_int(
            cert["hypotheses_replayed"], "M37 replayed hypothesis count"
        )
        != expected_hypotheses
        or core._strict_int(
            cert["expected_score_cells"], "M37 score-cell count"
        )
        != expected_hypotheses * grid.score_bin_count
        or core._strict_int(
            cert["score_cells_replayed"], "M37 replayed score-cell count"
        )
        != expected_hypotheses * grid.score_bin_count
        or cert["minimum_active_epoch_snr"]
        != core.M37_MINIMUM_ACTIVE_EPOCH_SNR
        or cert["stack_statistic"] != "minimum_epoch"
        or cert["require_epoch_vector_product"] is not True
        or cert["require_mask_product"] is not True
        or core._strict_int(
            cert["maximum_records"], "M37 retention capacity"
        )
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or core._strict_int(
            cert["maximum_record_canonical_bytes"],
            "M37 record-byte capacity",
        )
        != core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
        or core._strict_int(
            cert["maximum_evidence_canonical_bytes"],
            "M37 evidence-byte capacity",
        )
        != core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
    ):
        raise core.V0P6IncompleteError(
            "global rank-p pass received a non-canonical M37 contract"
        )


def evaluate_m37_global_rank_significance(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str | None = None,
    expected_threshold_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Run the non-configurable five-window, 256-null M37 rank-p pass."""
    core.validate_threshold_certificate(
        threshold_certificate,
        expected_certificate_sha256=expected_threshold_certificate_sha256,
    )
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    raw_nulls = np.asarray(global_null_maxima)
    _require_m37_contract(cert, threshold_certificate, raw_nulls, grid)
    return evaluate_global_rank_significance(
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
    )


def validate_m37_global_rank_significance(
    result: Mapping[str, Any],
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    threshold_certificate: core.ThresholdCertificate,
    global_null_maxima: np.ndarray,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str | None = None,
    expected_threshold_certificate_sha256: str | None = None,
    expected_result_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate an M37 result and every upstream M37 dimension gate."""
    core.validate_threshold_certificate(
        threshold_certificate,
        expected_certificate_sha256=expected_threshold_certificate_sha256,
    )
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    raw_nulls = np.asarray(global_null_maxima)
    _require_m37_contract(cert, threshold_certificate, raw_nulls, grid)
    return validate_global_rank_significance(
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


# Concise aliases for callers that use "compute" rather than "evaluate".
compute_global_rank_significance = evaluate_global_rank_significance
compute_m37_global_rank_significance = evaluate_m37_global_rank_significance
validate_significance_result = validate_global_rank_significance


__all__ = [
    "EVIDENCE_SORT_ORDER",
    "INCLUSIVE_NULL_COMPARISON",
    "INCLUSIVE_RANK_P_DEFINITION",
    "SCIENTIFIC_ELIGIBILITY_COMPARISON",
    "SIGNIFICANCE_ARTIFACT_TYPE",
    "SIGNIFICANCE_SCHEMA_VERSION",
    "compute_global_rank_significance",
    "compute_m37_global_rank_significance",
    "evaluate_global_rank_significance",
    "evaluate_m37_global_rank_significance",
    "validate_global_rank_significance",
    "validate_m37_global_rank_significance",
    "validate_significance_result",
]
