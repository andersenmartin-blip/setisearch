"""Receipt-bound final outcome join for the detector-v0.6 M37 run.

The physical-veto product and the global rank-p product deliberately remain
separate upstream artifacts.  This module is the only place where they are
joined.  The join key is the raw retained-record ``record_id`` and the
significance evidence is additionally required to hash the exact retained
record reconstructed from the physical annotation.

Persisted upstream products are accepted only with independently supplied
SHA-256 receipts.  A completed outcome contains all five M37 windows or no
outcome is emitted.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from . import alias_v0p6 as alias_stage
from . import search_v0p6 as core
from . import significance_v0p6 as significance_stage


OUTCOME_ARTIFACT_TYPE = "seti_repeater.detector_v0p6_m37_final_outcome"
OUTCOME_SCHEMA_VERSION = 1

SCIENTIFIC_CANDIDATE_UNRESOLVED = "scientific_candidate_unresolved"
RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE = (
    "retained_but_not_scientifically_eligible"
)
GLOBAL_OPEN_UNRESOLVED = "open_unresolved_scientific_candidates"
GLOBAL_CLOSED_NO_UNRESOLVED = "closed_no_unresolved_scientific_candidates"

UNVETOED_PHYSICAL_DISPOSITION = "pending_receiver_alias_evaluation"
PHYSICAL_RFI_DISPOSITIONS = frozenset(
    {
        "rfi_veto_matched_off_same_hypothesis",
        "rfi_veto_local_off_track",
        "rfi_veto_single_adjacent_off",
        "rfi_veto_receiver_frame_alias",
    }
)
FINAL_DISPOSITIONS = frozenset(
    PHYSICAL_RFI_DISPOSITIONS
    | {
        SCIENTIFIC_CANDIDATE_UNRESOLVED,
        RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE,
    }
)

M37_MAXIMUM_OUTCOME_RECORDS = (
    len(core.M37_WINDOW_IDS) * core.M37_MAXIMUM_RECORDS_PER_WINDOW
)
M37_MAXIMUM_OUTCOME_CANONICAL_BYTES = (
    len(core.M37_WINDOW_IDS) * core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
)
_MAXIMUM_UPSTREAM_CERTIFICATE_CANONICAL_BYTES = 1_000_000

_WINDOW_INPUT_FIELDS = frozenset(
    {
        "window_id",
        "alias_result",
        "significance_result",
        "expected_alias_certificate_sha256",
        "expected_significance_result_sha256",
        "expected_retention_certificate_sha256",
    }
)
_ALIAS_RESULT_FIELDS = frozenset({"records", "certificate"})
_RANK_EVIDENCE_FIELDS = frozenset(
    {
        "significance_evidence_sha256",
        "retained_snr",
        "global_null_count",
        "inclusive_null_exceedance_count",
        "inclusive_global_rank_p",
        "scientific_empirical_p_ceiling",
        "scientifically_eligible",
    }
)
_RETENTION_SORT_KEY_FIELDS = frozenset(
    {
        "template_index",
        "spectral_width_index",
        "active_epochs_zero_based",
        "proxy_carrier_index",
    }
)
_OUTCOME_RECORD_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "window_id",
        "window_ordinal",
        "record_id",
        "retained_record_sha256",
        "alias_record_sha256",
        "retention_sort_key",
        "physical_disposition",
        "global_rank_p_evidence",
        "final_disposition",
    }
)
_OUTCOME_RECORD_FIELDS = _OUTCOME_RECORD_PAYLOAD_FIELDS | {
    "outcome_record_sha256"
}
_WINDOW_RECEIPT_FIELDS = frozenset(
    {
        "window_id",
        "window_ordinal",
        "retention_certificate_sha256",
        "alias_certificate_sha256",
        "receiver_signature_certificate_sha256",
        "alias_annotated_records_sha256",
        "retained_records_sha256",
        "significance_result_sha256",
        "significance_certificate_sha256",
        "significance_evidence_sha256",
        "record_count",
        "record_ids_sha256",
        "alias_record_sha256s_sha256",
        "significance_evidence_sha256s_sha256",
        "outcome_record_sha256s_sha256",
    }
)
_CERTIFICATE_PAYLOAD_FIELDS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "window_ids",
        "window_count",
        "window_order",
        "record_order",
        "join_key",
        "unvetoed_physical_disposition",
        "scientific_candidate_comparison",
        "scientific_empirical_p_ceiling",
        "threshold_certificate_sha256",
        "operational_threshold_snr",
        "global_null_maxima_sha256",
        "global_null_count",
        "template_bank_sha256",
        "template_count",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "on_factor_matrix_sha256",
        "factor_table_sha256",
        "window_receipts",
        "input_alias_record_count",
        "input_significance_evidence_count",
        "outcome_record_count",
        "maximum_records_per_window",
        "maximum_outcome_records",
        "outcome_record_ids_sha256",
        "outcome_item_sha256s_sha256",
        "outcome_records_sha256",
        "outcome_records_canonical_bytes",
        "maximum_outcome_canonical_bytes",
        "disposition_counts",
        "unresolved_candidate_count",
        "global_search_state",
        "unresolved_scientific_candidates",
        "global_outcome",
        "all_five_windows_present",
        "all_alias_records_joined_exactly_once",
        "all_significance_evidence_joined_exactly_once",
        "truncation_permitted",
    }
)
_CERTIFICATE_FIELDS = _CERTIFICATE_PAYLOAD_FIELDS | {
    "outcome_certificate_sha256"
}
_RESULT_FIELDS = frozenset({"records", "certificate", "result_sha256"})

_OUTCOME_RESULT_ATTESTATIONS: dict[str, bytes] = {}
_OUTCOME_RESULT_ATTESTATION_CAP = 1_024
_OUTCOME_RESULT_ATTESTATION_CAP_BYTES = 2 * (
    M37_MAXIMUM_OUTCOME_CANONICAL_BYTES
)
_outcome_attestation_bytes = 0


class M37ValidationError(core.V0P6IncompleteError):
    """Raised when a complete, receipt-bound M37 outcome cannot be proved."""


def _digest(value: Any, label: str) -> str:
    try:
        return core._frozen_sha256(value, label)
    except Exception as error:
        raise M37ValidationError(str(error)) from error


def _strict_int(value: Any, label: str) -> int:
    try:
        return core._strict_int(value, label)
    except Exception as error:
        raise M37ValidationError(str(error)) from error


def _canonical_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise M37ValidationError(f"{label} must be a mapping")
    try:
        detached = json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError, OverflowError) as error:
        raise M37ValidationError(
            f"{label} must be canonical finite JSON"
        ) from error
    if not isinstance(detached, dict):
        raise M37ValidationError(f"{label} must be a JSON object")
    return detached


def _canonical_sequence(value: Any, label: str) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise M37ValidationError(f"{label} must be a sequence")
    try:
        detached = json.loads(core.canonical_json_bytes(list(value)))
    except (TypeError, ValueError, OverflowError) as error:
        raise M37ValidationError(
            f"{label} must be canonical finite JSON"
        ) from error
    if not isinstance(detached, list):
        raise M37ValidationError(f"{label} must be a JSON array")
    return detached


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def _finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise M37ValidationError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise M37ValidationError(f"{label} must be a finite number")
    return result


def _retention_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    try:
        return core._retention_record_sort_key(record)
    except Exception as error:
        raise M37ValidationError("retained-record sort key is invalid") from error


def _reconstructed_retained_record(
    alias_record: Mapping[str, Any],
) -> dict[str, Any]:
    record = _canonical_mapping(alias_record, "physical alias record")
    for field in (
        "off_track_evidence",
        "single_adjacent_off_evidence",
        "receiver_alias_evidence",
    ):
        if field not in record:
            raise M37ValidationError(
                f"physical alias record lacks {field}"
            )
        record.pop(field)
    record["member_disposition"] = "pending_physical_veto_evaluation"
    return record


def _retention_sort_key_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "template_index": _strict_int(
            record.get("template_index"), "template index"
        ),
        "spectral_width_index": _strict_int(
            record.get("spectral_width_index"), "spectral-width index"
        ),
        "active_epochs_zero_based": [
            _strict_int(item, "activity epoch")
            for item in record.get("active_epochs_zero_based", [])
        ],
        "proxy_carrier_index": _strict_int(
            record.get("proxy_carrier_index"), "proxy-carrier index"
        ),
    }


def _final_disposition(physical_disposition: str, rank_p: float) -> str:
    if physical_disposition in PHYSICAL_RFI_DISPOSITIONS:
        return physical_disposition
    if physical_disposition != UNVETOED_PHYSICAL_DISPOSITION:
        raise M37ValidationError("physical disposition is not finalizable")
    if rank_p <= core.M37_SCIENTIFIC_P_CEILING:
        return SCIENTIFIC_CANDIDATE_UNRESOLVED
    return RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE


def _validate_alias_product(
    raw_result: Any,
    *,
    expected_certificate_sha256: str,
    window_id: str,
    window_ordinal: int,
    expected_retention_certificate_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = _canonical_mapping(raw_result, "receiver-alias result")
    if frozenset(result) != _ALIAS_RESULT_FIELDS:
        raise M37ValidationError("receiver-alias result schema changed")
    records = _canonical_sequence(result["records"], "receiver-alias records")
    sort_keys = [_retention_sort_key(record) for record in records]
    if sort_keys != sorted(sort_keys) or len(sort_keys) != len(set(sort_keys)):
        raise M37ValidationError(
            "receiver-alias records were duplicated or reordered from canonical retention order"
        )
    if len(records) > core.M37_MAXIMUM_RECORDS_PER_WINDOW:
        raise M37ValidationError("receiver-alias record capacity exceeded")
    try:
        certificate = alias_stage.validate_receiver_alias_result(
            records,
            result["certificate"],
            expected_certificate_sha256=expected_certificate_sha256,
        )
    except Exception as error:
        raise M37ValidationError(
            "receiver-alias product failed trusted validation"
        ) from error
    certificate = _canonical_mapping(
        certificate, "validated receiver-alias certificate"
    )
    if (
        str(certificate.get("window_id")) != window_id
        or _strict_int(certificate.get("window_ordinal"), "window ordinal")
        != window_ordinal
        or _strict_int(
            certificate.get("input_record_count"), "alias input record count"
        )
        != len(records)
        or _strict_int(
            certificate.get("maximum_records"), "alias record capacity"
        )
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or certificate.get("all_on_records_annotated_exactly_once") is not True
        or certificate.get("truncation_permitted") is not False
    ):
        raise M37ValidationError(
            "receiver-alias certificate is not an exact M37 window receipt"
        )
    if (
        _strict_int(
            certificate.get("on_integration_count"), "ON integration count"
        )
        != 48
        or _finite_float(
            certificate.get("track_tolerance_hz"), "alias track tolerance"
        )
        != alias_stage.M37_ALIAS_TRACK_TOLERANCE_HZ
        or _finite_float(
            certificate.get("local_receiver_half_width_hz"),
            "local receiver half-width",
        )
        != alias_stage.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        or _finite_float(
            certificate.get("local_peak_snr_floor"),
            "local receiver peak S/N floor",
        )
        != alias_stage.M37_RECEIVER_PEAK_SNR_FLOOR
        or _strict_int(
            certificate.get("minimum_shared_active_epochs"),
            "minimum shared active epochs",
        )
        != alias_stage.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        or _strict_int(
            certificate.get("maximum_bucket_entries"),
            "maximum alias bucket entries",
        )
        != core.M37_MAXIMUM_ALIAS_BUCKET_ENTRIES
        or _strict_int(
            certificate.get("maximum_distinct_candidate_visits_per_window"),
            "maximum alias candidate visits",
        )
        != core.M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
    ):
        raise M37ValidationError(
            "receiver-alias certificate uses non-M37 matching limits"
        )
    track_comparisons = _strict_int(
        certificate.get("alias_identity_track_comparisons"),
        "alias identity track comparisons",
    )
    track_comparison_cap = _strict_int(
        certificate.get("maximum_alias_identity_track_comparisons"),
        "maximum alias identity track comparisons",
    )
    if (
        certificate.get("alias_identity_track_comparison_definition")
        != (
            "candidate node pair surviving first-ON-time anchor pruning before "
            "literal all-ON-time track comparison"
        )
        or track_comparisons < 0
        or track_comparison_cap
        != alias_stage.M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        or track_comparisons > track_comparison_cap
    ):
        raise M37ValidationError(
            "receiver-alias identity comparison receipt violates its M37 cap"
        )
    if _digest(
        certificate.get("receiver_alias_certificate_sha256"),
        "receiver-alias certificate identity",
    ) != expected_certificate_sha256:
        raise M37ValidationError("receiver-alias certificate receipt mismatched")
    if _digest(
        certificate.get("on_retention_certificate_sha256"),
        "alias retention certificate identity",
    ) != expected_retention_certificate_sha256:
        raise M37ValidationError(
            "receiver-alias product binds a different retention certificate"
        )
    _digest(
        certificate.get("receiver_signature_certificate_sha256"),
        "receiver-signature certificate identity",
    )
    _digest(
        certificate.get("on_factor_matrix_sha256"),
        "ON factor-matrix identity",
    )
    return records, certificate


def _validate_significance_product(
    raw_result: Any,
    *,
    expected_result_sha256: str,
    expected_threshold_certificate_sha256: str,
    expected_retention_certificate_sha256: str,
    window_id: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    try:
        result = significance_stage._validate_result_envelope(
            raw_result,
            expected_result_sha256=expected_result_sha256,
        )
        significance_stage._validate_evidence_and_certificate(result)
    except Exception as error:
        raise M37ValidationError(
            "global rank-p product failed trusted validation"
        ) from error
    result = _canonical_mapping(result, "validated global rank-p result")
    certificate = _canonical_mapping(
        result["certificate"], "global rank-p certificate"
    )
    evidence = _canonical_sequence(
        result["evidence"], "global rank-p evidence"
    )
    if _digest(result["result_sha256"], "significance result identity") != (
        expected_result_sha256
    ):
        raise M37ValidationError("global rank-p result receipt mismatched")
    if (
        certificate.get("artifact_type")
        != significance_stage.SIGNIFICANCE_ARTIFACT_TYPE
        or certificate.get("schema_version")
        != significance_stage.SIGNIFICANCE_SCHEMA_VERSION
        or certificate.get("detector_version") != core.DETECTOR_VERSION
        or str(certificate.get("window_id")) != window_id
        or certificate.get("source_scan_kind") != "on"
        or certificate.get("threshold_window_ids")
        != list(core.M37_WINDOW_IDS)
        or certificate.get("global_null_shape") != [core.M37_SCRAMBLE_COUNT]
        or _strict_int(
            certificate.get("global_null_count"), "global null count"
        )
        != core.M37_SCRAMBLE_COUNT
        or _strict_int(certificate.get("template_count"), "template count")
        != core.M37_TEMPLATE_COUNT
        or _strict_int(
            certificate.get("input_record_count"),
            "significance input record count",
        )
        != len(evidence)
        or _strict_int(
            certificate.get("evidence_record_count"),
            "significance evidence count",
        )
        != len(evidence)
        or _strict_int(
            certificate.get("maximum_evidence_canonical_bytes"),
            "maximum significance evidence bytes",
        )
        != core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        or certificate.get("all_input_records_evaluated_exactly_once") is not True
        or certificate.get("truncation_permitted") is not False
    ):
        raise M37ValidationError(
            "global rank-p certificate is not an exact M37 window receipt"
        )
    if _finite_float(
        certificate.get("scientific_empirical_p_ceiling"),
        "scientific empirical-p ceiling",
    ) != core.M37_SCIENTIFIC_P_CEILING:
        raise M37ValidationError("scientific empirical-p ceiling changed")
    if _digest(
        certificate.get("retention_certificate_sha256"),
        "significance retention certificate identity",
    ) != expected_retention_certificate_sha256:
        raise M37ValidationError(
            "global rank-p product binds a different retention certificate"
        )
    if _digest(
        certificate.get("threshold_certificate_sha256"),
        "significance threshold certificate identity",
    ) != expected_threshold_certificate_sha256:
        raise M37ValidationError(
            "global rank-p product binds a different threshold certificate"
        )
    expected_identities = {
        "template_bank_sha256": core.M37_BANK_SHA256,
        "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
        "factor_basis_sha256": core.M37_FACTOR_BASIS_SHA256,
        "factor_basis_labels_sha256": core.M37_FACTOR_BASIS_LABELS_SHA256,
        "scan_inventory_sha256": core.M37_SCAN_INVENTORY_SHA256,
        "on_factor_row_selection_sha256": (
            core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        ),
    }
    for field, expected in expected_identities.items():
        if _digest(certificate.get(field), field.replace("_", "-")) != expected:
            raise M37ValidationError(
                f"global rank-p {field} is not the frozen M37 identity"
            )
    expected_grid_sha = core.proxy_carrier_grid_sha256(
        core.make_m37_proxy_carrier_grid(window_id)
    )
    if _digest(
        certificate.get("proxy_grid_sha256"), "proxy-grid identity"
    ) != expected_grid_sha:
        raise M37ValidationError(
            "global rank-p product binds a different M37 proxy grid"
        )
    return result, certificate, evidence


def _common_significance_identity(certificate: Mapping[str, Any]) -> dict[str, Any]:
    operational_threshold = _finite_float(
        certificate.get("operational_threshold_snr"), "operational threshold"
    )
    if operational_threshold < core.M37_THRESHOLD_REFERENCE_FLOOR_SNR:
        raise M37ValidationError("M37 operational threshold is below its floor")
    return {
        "threshold_certificate_sha256": _digest(
            certificate.get("threshold_certificate_sha256"),
            "threshold certificate identity",
        ),
        "operational_threshold_snr": operational_threshold,
        "global_null_maxima_sha256": _digest(
            certificate.get("global_null_maxima_sha256"),
            "global null-vector identity",
        ),
        "global_null_count": _strict_int(
            certificate.get("global_null_count"), "global null count"
        ),
        "template_bank_sha256": _digest(
            certificate.get("template_bank_sha256"), "template-bank identity"
        ),
        "template_count": _strict_int(
            certificate.get("template_count"), "template count"
        ),
        "experiment_contract_sha256": _digest(
            certificate.get("experiment_contract_sha256"),
            "experiment-contract identity",
        ),
        "analysis_contract_sha256": _digest(
            certificate.get("analysis_contract_sha256"),
            "analysis-contract identity",
        ),
        "factor_basis_sha256": _digest(
            certificate.get("factor_basis_sha256"), "factor-basis identity"
        ),
        "factor_basis_labels_sha256": _digest(
            certificate.get("factor_basis_labels_sha256"),
            "factor-basis-label identity",
        ),
        "scan_inventory_sha256": _digest(
            certificate.get("scan_inventory_sha256"),
            "scan-inventory identity",
        ),
        "on_factor_row_selection_sha256": _digest(
            certificate.get("on_factor_row_selection_sha256"),
            "ON factor-row selection identity",
        ),
        "factor_table_sha256": _digest(
            certificate.get("factor_table_sha256"), "factor-table identity"
        ),
    }


def _derive_m37_outcome(
    window_inputs: Sequence[Mapping[str, Any]],
    *,
    expected_threshold_certificate_sha256: str,
) -> dict[str, Any]:
    threshold_receipt = _digest(
        expected_threshold_certificate_sha256,
        "expected threshold certificate identity",
    )
    if isinstance(window_inputs, (str, bytes, bytearray)) or not isinstance(
        window_inputs, Sequence
    ):
        raise M37ValidationError("M37 outcome window inputs must be a sequence")
    if len(window_inputs) != len(core.M37_WINDOW_IDS):
        raise M37ValidationError("M37 outcome requires exactly five windows")
    inputs = list(window_inputs)

    outcome_records: list[dict[str, Any]] = []
    window_receipts: list[dict[str, Any]] = []
    disposition_counts = {name: 0 for name in sorted(FINAL_DISPOSITIONS)}
    common_identity: dict[str, Any] | None = None
    seen_global_ids: set[str] = set()
    seen_alias_receipts: set[str] = set()
    seen_significance_receipts: set[str] = set()
    seen_retention_receipts: set[str] = set()
    seen_receiver_signature_receipts: set[str] = set()
    common_on_factor_matrix_sha256: str | None = None

    for window_ordinal, expected_window_id in enumerate(core.M37_WINDOW_IDS):
        raw_item = inputs[window_ordinal]
        if not isinstance(raw_item, Mapping) or frozenset(raw_item) != (
            _WINDOW_INPUT_FIELDS
        ):
            raise M37ValidationError("M37 window-input schema changed")
        item = dict(raw_item)
        if str(item["window_id"]) != expected_window_id:
            raise M37ValidationError("M37 windows are missing, duplicated, or reordered")
        raw_alias_result = item["alias_result"]
        raw_significance_result = item["significance_result"]
        if not isinstance(raw_alias_result, Mapping) or frozenset(
            raw_alias_result
        ) != _ALIAS_RESULT_FIELDS:
            raise M37ValidationError("receiver-alias result schema changed")
        raw_alias_records = raw_alias_result.get("records")
        if isinstance(raw_alias_records, (str, bytes, bytearray)) or not isinstance(
            raw_alias_records, Sequence
        ):
            raise M37ValidationError("receiver-alias records must be a sequence")
        if len(raw_alias_records) > core.M37_MAXIMUM_RECORDS_PER_WINDOW:
            raise M37ValidationError("receiver-alias record capacity exceeded")
        if not isinstance(raw_significance_result, Mapping) or frozenset(
            raw_significance_result
        ) != significance_stage._RESULT_FIELDS:
            raise M37ValidationError("global rank-p result schema changed")
        raw_significance_evidence = raw_significance_result.get("evidence")
        if isinstance(
            raw_significance_evidence, (str, bytes, bytearray)
        ) or not isinstance(raw_significance_evidence, Sequence):
            raise M37ValidationError("global rank-p evidence must be a sequence")
        if len(raw_significance_evidence) > core.M37_MAXIMUM_RECORDS_PER_WINDOW:
            raise M37ValidationError("global rank-p evidence capacity exceeded")
        for product, records_or_evidence, label in (
            (raw_alias_result, raw_alias_records, "receiver-alias"),
            (
                raw_significance_result,
                raw_significance_evidence,
                "global rank-p",
            ),
        ):
            certificate = product.get("certificate")
            if not isinstance(certificate, Mapping):
                raise M37ValidationError(f"{label} certificate must be a mapping")
            try:
                certificate_size = len(core.canonical_json_bytes(dict(certificate)))
            except (TypeError, ValueError, OverflowError) as error:
                raise M37ValidationError(
                    f"{label} certificate must be canonical finite JSON"
                ) from error
            if certificate_size > _MAXIMUM_UPSTREAM_CERTIFICATE_CANONICAL_BYTES:
                raise M37ValidationError(
                    f"{label} certificate exceeds its byte capacity"
                )
            cumulative_bytes = 0
            for raw_record in records_or_evidence:
                try:
                    item_size = len(core.canonical_json_bytes(raw_record))
                except (TypeError, ValueError, OverflowError) as error:
                    raise M37ValidationError(
                        f"{label} item must be canonical finite JSON"
                    ) from error
                if item_size > core.M37_MAXIMUM_RECORD_CANONICAL_BYTES:
                    raise M37ValidationError(
                        f"{label} item exceeds its canonical-byte capacity"
                    )
                cumulative_bytes += item_size
                if cumulative_bytes > core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES:
                    raise M37ValidationError(
                        f"{label} inventory exceeds its canonical-byte capacity"
                    )
        alias_receipt = _digest(
            item["expected_alias_certificate_sha256"],
            "expected receiver-alias certificate identity",
        )
        significance_receipt = _digest(
            item["expected_significance_result_sha256"],
            "expected global rank-p result identity",
        )
        retention_receipt = _digest(
            item["expected_retention_certificate_sha256"],
            "expected ON retention certificate identity",
        )
        if (
            alias_receipt in seen_alias_receipts
            or significance_receipt in seen_significance_receipts
            or retention_receipt in seen_retention_receipts
        ):
            raise M37ValidationError("M37 window receipts are duplicated")
        seen_alias_receipts.add(alias_receipt)
        seen_significance_receipts.add(significance_receipt)
        seen_retention_receipts.add(retention_receipt)

        alias_records, alias_certificate = _validate_alias_product(
            item["alias_result"],
            expected_certificate_sha256=alias_receipt,
            window_id=expected_window_id,
            window_ordinal=window_ordinal,
            expected_retention_certificate_sha256=retention_receipt,
        )
        receiver_signature_receipt = _digest(
            alias_certificate.get("receiver_signature_certificate_sha256"),
            "receiver-signature certificate identity",
        )
        if receiver_signature_receipt in seen_receiver_signature_receipts:
            raise M37ValidationError(
                "M37 receiver-signature certificate receipt is duplicated"
            )
        seen_receiver_signature_receipts.add(receiver_signature_receipt)
        on_factor_matrix_sha256 = _digest(
            alias_certificate.get("on_factor_matrix_sha256"),
            "ON factor-matrix identity",
        )
        if common_on_factor_matrix_sha256 is None:
            common_on_factor_matrix_sha256 = on_factor_matrix_sha256
        elif on_factor_matrix_sha256 != common_on_factor_matrix_sha256:
            raise M37ValidationError(
                "M37 alias windows do not share one ON factor matrix"
            )
        _, significance_certificate, evidence = (
            _validate_significance_product(
                item["significance_result"],
                expected_result_sha256=significance_receipt,
                expected_threshold_certificate_sha256=threshold_receipt,
                expected_retention_certificate_sha256=retention_receipt,
                window_id=expected_window_id,
            )
        )
        observed_common = _common_significance_identity(significance_certificate)
        if common_identity is None:
            common_identity = observed_common
        elif observed_common != common_identity:
            raise M37ValidationError(
                "M37 windows do not share one threshold and analysis identity"
            )

        alias_ids = [
            _digest(record.get("record_id"), "alias record ID")
            for record in alias_records
        ]
        if len(alias_ids) != len(set(alias_ids)):
            raise M37ValidationError("receiver-alias records duplicate a retained ID")
        evidence_by_id: dict[str, dict[str, Any]] = {}
        for raw_evidence in evidence:
            evidence_item = _canonical_mapping(
                raw_evidence, "global rank-p evidence item"
            )
            record_id = _digest(evidence_item.get("record_id"), "rank-p record ID")
            if record_id in evidence_by_id:
                raise M37ValidationError("global rank-p evidence duplicates an ID")
            evidence_by_id[record_id] = evidence_item
        if set(alias_ids) != set(evidence_by_id) or len(alias_ids) != len(evidence):
            raise M37ValidationError(
                "physical and significance products do not cover identical record IDs"
            )
        if any(record_id in seen_global_ids for record_id in alias_ids):
            raise M37ValidationError("a retained record ID occurs in multiple windows")
        seen_global_ids.update(alias_ids)
        if len(outcome_records) + len(alias_records) > M37_MAXIMUM_OUTCOME_RECORDS:
            raise M37ValidationError("M37 outcome record capacity exceeded")

        alias_hashes: list[str] = []
        significance_hashes: list[str] = []
        outcome_hashes: list[str] = []
        reconstructed_retained_records: list[dict[str, Any]] = []
        for alias_record, record_id in zip(alias_records, alias_ids, strict=True):
            if str(alias_record.get("window_id")) != expected_window_id:
                raise M37ValidationError("alias record carries the wrong window ID")
            rank_item = evidence_by_id[record_id]
            reconstructed = _reconstructed_retained_record(alias_record)
            reconstructed_sha = _sha256_json(reconstructed)
            certified_retained_sha = _digest(
                rank_item.get("retained_record_sha256"),
                "rank-p retained-record identity",
            )
            if reconstructed_sha != certified_retained_sha:
                raise M37ValidationError(
                    "physical and rank-p products do not bind the same retained record"
                )
            reconstructed_retained_records.append(reconstructed)
            alias_snr = _finite_float(alias_record.get("snr"), "retained S/N")
            retained_snr = _finite_float(
                rank_item.get("retained_snr"), "rank-p retained S/N"
            )
            if alias_snr != retained_snr:
                raise M37ValidationError("physical and rank-p retained S/N differ")
            null_count = _strict_int(
                rank_item.get("global_null_count"), "evidence global null count"
            )
            exceedances = _strict_int(
                rank_item.get("inclusive_null_exceedance_count"),
                "inclusive null exceedance count",
            )
            rank_p = _finite_float(
                rank_item.get("inclusive_global_rank_p"), "inclusive global rank p"
            )
            evidence_ceiling = _finite_float(
                rank_item.get("scientific_empirical_p_ceiling"),
                "evidence empirical-p ceiling",
            )
            eligible = rank_item.get("scientifically_eligible")
            if (
                null_count != common_identity["global_null_count"]
                or evidence_ceiling != core.M37_SCIENTIFIC_P_CEILING
                or not isinstance(eligible, bool)
                or eligible != (rank_p <= core.M37_SCIENTIFIC_P_CEILING)
            ):
                raise M37ValidationError(
                    "rank-p evidence disagrees with the common M37 threshold"
                )
            physical_disposition = str(alias_record.get("member_disposition"))
            final_disposition = _final_disposition(physical_disposition, rank_p)
            disposition_counts[final_disposition] += 1
            alias_record_sha = _sha256_json(alias_record)
            significance_evidence_sha = _digest(
                rank_item.get("evidence_sha256"),
                "significance evidence identity",
            )
            payload = {
                "schema_version": OUTCOME_SCHEMA_VERSION,
                "window_id": expected_window_id,
                "window_ordinal": window_ordinal,
                "record_id": record_id,
                "retained_record_sha256": reconstructed_sha,
                "alias_record_sha256": alias_record_sha,
                "retention_sort_key": _retention_sort_key_payload(alias_record),
                "physical_disposition": physical_disposition,
                "global_rank_p_evidence": {
                    "significance_evidence_sha256": significance_evidence_sha,
                    "retained_snr": retained_snr,
                    "global_null_count": null_count,
                    "inclusive_null_exceedance_count": exceedances,
                    "inclusive_global_rank_p": rank_p,
                    "scientific_empirical_p_ceiling": evidence_ceiling,
                    "scientifically_eligible": eligible,
                },
                "final_disposition": final_disposition,
            }
            output_record = dict(payload)
            output_record["outcome_record_sha256"] = _sha256_json(payload)
            if len(core.canonical_json_bytes(output_record)) > (
                core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
            ):
                raise M37ValidationError(
                    "an M37 outcome record exceeds its canonical-byte capacity"
                )
            outcome_records.append(output_record)
            alias_hashes.append(alias_record_sha)
            significance_hashes.append(significance_evidence_sha)
            outcome_hashes.append(output_record["outcome_record_sha256"])

        retained_records_sha = _sha256_json(reconstructed_retained_records)
        if retained_records_sha != _digest(
            significance_certificate.get("source_records_sha256"),
            "significance source-record inventory identity",
        ):
            raise M37ValidationError(
                "joined records do not reproduce the retained-record inventory"
            )

        window_receipts.append(
            {
                "window_id": expected_window_id,
                "window_ordinal": window_ordinal,
                "retention_certificate_sha256": retention_receipt,
                "alias_certificate_sha256": alias_receipt,
                "receiver_signature_certificate_sha256": (
                    receiver_signature_receipt
                ),
                "alias_annotated_records_sha256": _digest(
                    alias_certificate.get("annotated_records_sha256"),
                    "alias annotated-record identity",
                ),
                "retained_records_sha256": retained_records_sha,
                "significance_result_sha256": significance_receipt,
                "significance_certificate_sha256": _digest(
                    significance_certificate.get(
                        "significance_certificate_sha256"
                    ),
                    "significance certificate identity",
                ),
                "significance_evidence_sha256": _digest(
                    significance_certificate.get("evidence_sha256"),
                    "significance evidence inventory identity",
                ),
                "record_count": len(alias_ids),
                "record_ids_sha256": _sha256_json(alias_ids),
                "alias_record_sha256s_sha256": _sha256_json(alias_hashes),
                "significance_evidence_sha256s_sha256": _sha256_json(
                    significance_hashes
                ),
                "outcome_record_sha256s_sha256": _sha256_json(outcome_hashes),
            }
        )

    assert common_identity is not None
    assert common_on_factor_matrix_sha256 is not None
    if common_identity["threshold_certificate_sha256"] != threshold_receipt:
        raise M37ValidationError("M37 threshold receipt changed during join")
    records_bytes = core.canonical_json_bytes(outcome_records)
    if len(records_bytes) > M37_MAXIMUM_OUTCOME_CANONICAL_BYTES:
        raise M37ValidationError("M37 outcome canonical-byte capacity exceeded")
    candidate_count = disposition_counts[SCIENTIFIC_CANDIDATE_UNRESOLVED]
    is_open = candidate_count > 0
    record_ids = [record["record_id"] for record in outcome_records]
    item_hashes = [record["outcome_record_sha256"] for record in outcome_records]
    certificate_payload = {
        "artifact_type": OUTCOME_ARTIFACT_TYPE,
        "schema_version": OUTCOME_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_ids": list(core.M37_WINDOW_IDS),
        "window_count": len(core.M37_WINDOW_IDS),
        "window_order": "M37_WINDOW_IDS order, no sorting or omission",
        "record_order": "canonical retention-record order within each window",
        "join_key": "exact lowercase retained-record record_id SHA-256",
        "unvetoed_physical_disposition": UNVETOED_PHYSICAL_DISPOSITION,
        "scientific_candidate_comparison": (
            "physical_unvetoed and inclusive_global_rank_p "
            "<= scientific_empirical_p_ceiling"
        ),
        "scientific_empirical_p_ceiling": core.M37_SCIENTIFIC_P_CEILING,
        **common_identity,
        "on_factor_matrix_sha256": common_on_factor_matrix_sha256,
        "window_receipts": window_receipts,
        "input_alias_record_count": len(outcome_records),
        "input_significance_evidence_count": len(outcome_records),
        "outcome_record_count": len(outcome_records),
        "maximum_records_per_window": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        "maximum_outcome_records": M37_MAXIMUM_OUTCOME_RECORDS,
        "outcome_record_ids_sha256": _sha256_json(record_ids),
        "outcome_item_sha256s_sha256": _sha256_json(item_hashes),
        "outcome_records_sha256": hashlib.sha256(records_bytes).hexdigest(),
        "outcome_records_canonical_bytes": len(records_bytes),
        "maximum_outcome_canonical_bytes": M37_MAXIMUM_OUTCOME_CANONICAL_BYTES,
        "disposition_counts": disposition_counts,
        "unresolved_candidate_count": candidate_count,
        "global_search_state": "open" if is_open else "closed",
        "unresolved_scientific_candidates": is_open,
        "global_outcome": (
            GLOBAL_OPEN_UNRESOLVED if is_open else GLOBAL_CLOSED_NO_UNRESOLVED
        ),
        "all_five_windows_present": True,
        "all_alias_records_joined_exactly_once": True,
        "all_significance_evidence_joined_exactly_once": True,
        "truncation_permitted": False,
    }
    certificate = dict(certificate_payload)
    certificate["outcome_certificate_sha256"] = _sha256_json(certificate_payload)
    result_payload = {"records": outcome_records, "certificate": certificate}
    result = dict(result_payload)
    result["result_sha256"] = _sha256_json(result_payload)
    return json.loads(core.canonical_json_bytes(result))


def _attest_result(result: dict[str, Any]) -> None:
    global _outcome_attestation_bytes
    digest = result["result_sha256"]
    encoded = core.canonical_json_bytes(result)
    if len(encoded) > M37_MAXIMUM_OUTCOME_CANONICAL_BYTES:
        raise M37ValidationError("M37 outcome result exceeds its byte capacity")
    prior = _OUTCOME_RESULT_ATTESTATIONS.get(digest)
    if prior is not None:
        if prior != encoded:
            raise M37ValidationError("M37 outcome digest collision")
        return
    if len(_OUTCOME_RESULT_ATTESTATIONS) >= _OUTCOME_RESULT_ATTESTATION_CAP:
        raise M37ValidationError("M37 outcome attestation count capacity exceeded")
    if _outcome_attestation_bytes + len(encoded) > (
        _OUTCOME_RESULT_ATTESTATION_CAP_BYTES
    ):
        raise M37ValidationError("M37 outcome attestation byte capacity exceeded")
    _OUTCOME_RESULT_ATTESTATIONS[digest] = encoded
    _outcome_attestation_bytes += len(encoded)


def assemble_m37_outcome(
    window_inputs: Sequence[Mapping[str, Any]],
    *,
    expected_threshold_certificate_sha256: str,
) -> dict[str, Any]:
    """Join exactly five trusted physical and rank-p M37 window products.

    Each window input must contain ``window_id``, ``alias_result``,
    ``significance_result`` and independent expected SHA-256 receipts for the
    alias certificate, significance result, and ON retention certificate.
    ``expected_threshold_certificate_sha256`` is the one common five-window
    threshold receipt.
    """
    try:
        result = _derive_m37_outcome(
            window_inputs,
            expected_threshold_certificate_sha256=(
                expected_threshold_certificate_sha256
            ),
        )
        _validate_outcome_payload(result)
        _attest_result(result)
        return result
    except M37ValidationError:
        raise
    except Exception as error:
        raise M37ValidationError("M37 outcome assembly failed closed") from error


def _validate_result_envelope(
    result: Mapping[str, Any],
    *,
    expected_result_sha256: str | None,
) -> dict[str, Any]:
    detached = _canonical_mapping(result, "M37 outcome result")
    if frozenset(detached) != _RESULT_FIELDS:
        raise M37ValidationError("M37 outcome result schema changed")
    observed = _digest(detached["result_sha256"], "M37 outcome result identity")
    payload = {
        "records": detached["records"],
        "certificate": detached["certificate"],
    }
    if _sha256_json(payload) != observed:
        raise M37ValidationError("M37 outcome result SHA-256 changed")
    if expected_result_sha256 is not None:
        expected = _digest(
            expected_result_sha256, "expected M37 outcome result identity"
        )
        if observed != expected:
            raise M37ValidationError("M37 outcome differs from trusted receipt")
    live_matches = (
        _OUTCOME_RESULT_ATTESTATIONS.get(observed)
        == core.canonical_json_bytes(detached)
    )
    trusted_matches = expected_result_sha256 is not None
    if not live_matches and not trusted_matches:
        raise M37ValidationError(
            "M37 outcome lacks a live or independently trusted receipt"
        )
    return detached


def _validate_outcome_payload(result: Mapping[str, Any]) -> None:
    records = result.get("records")
    certificate = result.get("certificate")
    if not isinstance(records, list) or not isinstance(certificate, dict):
        raise M37ValidationError("M37 outcome payload types are invalid")
    if frozenset(certificate) != _CERTIFICATE_FIELDS:
        raise M37ValidationError("M37 outcome certificate schema changed")
    certificate_payload = dict(certificate)
    certificate_digest = _digest(
        certificate_payload.pop("outcome_certificate_sha256"),
        "M37 outcome certificate identity",
    )
    if _sha256_json(certificate_payload) != certificate_digest:
        raise M37ValidationError("M37 outcome certificate SHA-256 changed")
    if frozenset(certificate_payload) != _CERTIFICATE_PAYLOAD_FIELDS:
        raise M37ValidationError("M37 outcome certificate payload changed")
    if (
        certificate["artifact_type"] != OUTCOME_ARTIFACT_TYPE
        or certificate["schema_version"] != OUTCOME_SCHEMA_VERSION
        or certificate["detector_version"] != core.DETECTOR_VERSION
        or certificate["window_ids"] != list(core.M37_WINDOW_IDS)
        or _strict_int(certificate["window_count"], "window count")
        != len(core.M37_WINDOW_IDS)
        or certificate["window_order"]
        != "M37_WINDOW_IDS order, no sorting or omission"
        or certificate["record_order"]
        != "canonical retention-record order within each window"
        or certificate["join_key"]
        != "exact lowercase retained-record record_id SHA-256"
        or certificate["unvetoed_physical_disposition"]
        != UNVETOED_PHYSICAL_DISPOSITION
        or certificate["scientific_candidate_comparison"]
        != (
            "physical_unvetoed and inclusive_global_rank_p "
            "<= scientific_empirical_p_ceiling"
        )
        or _finite_float(
            certificate["scientific_empirical_p_ceiling"],
            "scientific empirical-p ceiling",
        )
        != core.M37_SCIENTIFIC_P_CEILING
        or certificate["all_five_windows_present"] is not True
        or certificate["all_alias_records_joined_exactly_once"] is not True
        or certificate["all_significance_evidence_joined_exactly_once"] is not True
        or certificate["truncation_permitted"] is not False
    ):
        raise M37ValidationError("M37 outcome certificate semantics changed")
    if (
        _strict_int(
            certificate["maximum_records_per_window"],
            "maximum records per window",
        )
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or _strict_int(
            certificate["maximum_outcome_records"], "maximum outcome records"
        )
        != M37_MAXIMUM_OUTCOME_RECORDS
        or _strict_int(
            certificate["maximum_outcome_canonical_bytes"],
            "maximum outcome canonical bytes",
        )
        != M37_MAXIMUM_OUTCOME_CANONICAL_BYTES
        or len(records) > M37_MAXIMUM_OUTCOME_RECORDS
    ):
        raise M37ValidationError("M37 outcome capacity contract changed")
    for name in (
        "threshold_certificate_sha256",
        "global_null_maxima_sha256",
        "template_bank_sha256",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "on_factor_matrix_sha256",
        "factor_table_sha256",
        "outcome_record_ids_sha256",
        "outcome_item_sha256s_sha256",
        "outcome_records_sha256",
    ):
        _digest(certificate[name], name.replace("_", "-"))
    if (
        certificate["template_bank_sha256"] != core.M37_BANK_SHA256
        or _strict_int(certificate["template_count"], "template count")
        != core.M37_TEMPLATE_COUNT
        or certificate["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or certificate["factor_basis_sha256"] != core.M37_FACTOR_BASIS_SHA256
        or certificate["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or certificate["scan_inventory_sha256"]
        != core.M37_SCAN_INVENTORY_SHA256
        or certificate["on_factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or _strict_int(certificate["global_null_count"], "global null count")
        != core.M37_SCRAMBLE_COUNT
        or _finite_float(
            certificate["operational_threshold_snr"], "operational threshold"
        )
        < core.M37_THRESHOLD_REFERENCE_FLOOR_SNR
    ):
        raise M37ValidationError("M37 frozen analysis identity changed")

    receipts = certificate["window_receipts"]
    if not isinstance(receipts, list) or len(receipts) != len(core.M37_WINDOW_IDS):
        raise M37ValidationError("M37 window receipts are incomplete")
    record_cursor = 0
    global_ids: list[str] = []
    global_item_hashes: list[str] = []
    observed_counts = {name: 0 for name in sorted(FINAL_DISPOSITIONS)}
    seen_receipt_sets = [set(), set(), set(), set()]
    for ordinal, expected_window in enumerate(core.M37_WINDOW_IDS):
        receipt = receipts[ordinal]
        if not isinstance(receipt, dict) or frozenset(receipt) != (
            _WINDOW_RECEIPT_FIELDS
        ):
            raise M37ValidationError("M37 per-window receipt schema changed")
        if (
            str(receipt["window_id"]) != expected_window
            or _strict_int(receipt["window_ordinal"], "window ordinal") != ordinal
        ):
            raise M37ValidationError("M37 window receipts were reordered")
        receipt_digests = (
            _digest(
                receipt["retention_certificate_sha256"],
                "retention certificate identity",
            ),
            _digest(
                receipt["alias_certificate_sha256"],
                "receiver-alias certificate identity",
            ),
            _digest(
                receipt["significance_result_sha256"],
                "significance result identity",
            ),
            _digest(
                receipt["receiver_signature_certificate_sha256"],
                "receiver-signature certificate identity",
            ),
        )
        for digest_set, digest in zip(
            seen_receipt_sets, receipt_digests, strict=True
        ):
            if digest in digest_set:
                raise M37ValidationError("M37 per-window receipt is duplicated")
            digest_set.add(digest)
        for name in (
            "receiver_signature_certificate_sha256",
            "alias_annotated_records_sha256",
            "retained_records_sha256",
            "significance_certificate_sha256",
            "significance_evidence_sha256",
            "record_ids_sha256",
            "alias_record_sha256s_sha256",
            "significance_evidence_sha256s_sha256",
            "outcome_record_sha256s_sha256",
        ):
            _digest(receipt[name], name.replace("_", "-"))
        count = _strict_int(receipt["record_count"], "window record count")
        if count < 0 or count > core.M37_MAXIMUM_RECORDS_PER_WINDOW:
            raise M37ValidationError("M37 window record count exceeds capacity")
        window_records = records[record_cursor : record_cursor + count]
        if len(window_records) != count:
            raise M37ValidationError("M37 outcome dropped window records")
        record_cursor += count
        prior_sort_key: tuple[Any, ...] | None = None
        ids: list[str] = []
        alias_hashes: list[str] = []
        significance_hashes: list[str] = []
        item_hashes: list[str] = []
        for raw_record in window_records:
            if not isinstance(raw_record, dict) or frozenset(raw_record) != (
                _OUTCOME_RECORD_FIELDS
            ):
                raise M37ValidationError("M37 outcome-record schema changed")
            payload = dict(raw_record)
            item_digest = _digest(
                payload.pop("outcome_record_sha256"), "outcome record identity"
            )
            if frozenset(payload) != _OUTCOME_RECORD_PAYLOAD_FIELDS or (
                _sha256_json(payload) != item_digest
            ):
                raise M37ValidationError("M37 outcome-record SHA-256 changed")
            if (
                payload["schema_version"] != OUTCOME_SCHEMA_VERSION
                or str(payload["window_id"]) != expected_window
                or _strict_int(payload["window_ordinal"], "window ordinal")
                != ordinal
            ):
                raise M37ValidationError("M37 outcome record has wrong window")
            record_id = _digest(payload["record_id"], "outcome record ID")
            retained_sha = _digest(
                payload["retained_record_sha256"], "retained-record identity"
            )
            alias_sha = _digest(
                payload["alias_record_sha256"], "alias-record identity"
            )
            if not retained_sha or not alias_sha:
                raise M37ValidationError("M37 source record identity is missing")
            sort_key_payload = payload["retention_sort_key"]
            if not isinstance(sort_key_payload, dict) or frozenset(
                sort_key_payload
            ) != _RETENTION_SORT_KEY_FIELDS:
                raise M37ValidationError("retention sort-key schema changed")
            current_sort_key = _retention_sort_key(sort_key_payload)
            template_index, width_index, active_epochs, proxy_index = (
                current_sort_key
            )
            if (
                not 0 <= template_index < core.M37_TEMPLATE_COUNT
                or not 0 <= width_index < len(core.M37_SPECTRAL_WIDTHS)
                or active_epochs not in core.M37_ACTIVITY_SUBSETS
                or not 0 <= proxy_index <= 2 * core.M37_SCORE_HALF_BINS
            ):
                raise M37ValidationError("retention sort key is outside M37")
            if prior_sort_key is not None and current_sort_key <= prior_sort_key:
                raise M37ValidationError(
                    "M37 outcome records were duplicated or reordered"
                )
            prior_sort_key = current_sort_key
            rank_evidence = payload["global_rank_p_evidence"]
            if not isinstance(rank_evidence, dict) or frozenset(
                rank_evidence
            ) != _RANK_EVIDENCE_FIELDS:
                raise M37ValidationError("joined rank-p evidence schema changed")
            significance_sha = _digest(
                rank_evidence["significance_evidence_sha256"],
                "significance evidence identity",
            )
            retained_snr = _finite_float(
                rank_evidence["retained_snr"], "retained S/N"
            )
            null_count = _strict_int(
                rank_evidence["global_null_count"], "global null count"
            )
            exceedances = _strict_int(
                rank_evidence["inclusive_null_exceedance_count"],
                "inclusive null exceedance count",
            )
            rank_p = _finite_float(
                rank_evidence["inclusive_global_rank_p"],
                "inclusive global rank p",
            )
            ceiling = _finite_float(
                rank_evidence["scientific_empirical_p_ceiling"],
                "scientific empirical-p ceiling",
            )
            eligible = rank_evidence["scientifically_eligible"]
            expected_p = float((1 + exceedances) / (null_count + 1))
            if (
                null_count != core.M37_SCRAMBLE_COUNT
                or not 0 <= exceedances <= null_count
                or rank_p != expected_p
                or ceiling != core.M37_SCIENTIFIC_P_CEILING
                or retained_snr
                < _finite_float(
                    certificate["operational_threshold_snr"],
                    "operational threshold",
                )
                or not isinstance(eligible, bool)
                or eligible != (rank_p <= ceiling)
            ):
                raise M37ValidationError("joined rank-p evidence is inconsistent")
            physical = str(payload["physical_disposition"])
            expected_final = _final_disposition(physical, rank_p)
            final = str(payload["final_disposition"])
            if final != expected_final:
                raise M37ValidationError("final scientific disposition changed")
            observed_counts[final] += 1
            ids.append(record_id)
            alias_hashes.append(alias_sha)
            significance_hashes.append(significance_sha)
            item_hashes.append(item_digest)
            global_ids.append(record_id)
            global_item_hashes.append(item_digest)
        if len(ids) != len(set(ids)):
            raise M37ValidationError("M37 window outcome duplicates a record ID")
        expected_receipt_hashes = {
            "record_ids_sha256": _sha256_json(ids),
            "alias_record_sha256s_sha256": _sha256_json(alias_hashes),
            "significance_evidence_sha256s_sha256": _sha256_json(
                significance_hashes
            ),
            "outcome_record_sha256s_sha256": _sha256_json(item_hashes),
        }
        if any(receipt[name] != value for name, value in expected_receipt_hashes.items()):
            raise M37ValidationError("M37 per-window joined inventory changed")
    if record_cursor != len(records) or len(global_ids) != len(set(global_ids)):
        raise M37ValidationError("M37 outcome has extra or duplicated records")
    records_bytes = core.canonical_json_bytes(records)
    if (
        len(records_bytes) > M37_MAXIMUM_OUTCOME_CANONICAL_BYTES
        or _strict_int(
            certificate["outcome_records_canonical_bytes"],
            "outcome record byte count",
        )
        != len(records_bytes)
        or certificate["outcome_records_sha256"]
        != hashlib.sha256(records_bytes).hexdigest()
        or certificate["outcome_record_ids_sha256"] != _sha256_json(global_ids)
        or certificate["outcome_item_sha256s_sha256"]
        != _sha256_json(global_item_hashes)
    ):
        raise M37ValidationError("M37 outcome record inventory changed")
    count_fields = (
        "input_alias_record_count",
        "input_significance_evidence_count",
        "outcome_record_count",
    )
    if any(
        _strict_int(certificate[name], name.replace("_", "-")) != len(records)
        for name in count_fields
    ):
        raise M37ValidationError("M37 outcome counts are incomplete")
    if certificate["disposition_counts"] != observed_counts:
        raise M37ValidationError("M37 outcome disposition counts changed")
    candidate_count = observed_counts[SCIENTIFIC_CANDIDATE_UNRESOLVED]
    is_open = candidate_count > 0
    if (
        _strict_int(
            certificate["unresolved_candidate_count"],
            "unresolved candidate count",
        )
        != candidate_count
        or certificate["unresolved_scientific_candidates"] is not is_open
        or certificate["global_search_state"] != ("open" if is_open else "closed")
        or certificate["global_outcome"]
        != (GLOBAL_OPEN_UNRESOLVED if is_open else GLOBAL_CLOSED_NO_UNRESOLVED)
    ):
        raise M37ValidationError("M37 global open/closed state is inconsistent")


def validate_m37_outcome(
    result: Mapping[str, Any],
    *,
    expected_result_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a live outcome or a persisted outcome with a trusted receipt."""
    try:
        detached = _validate_result_envelope(
            result, expected_result_sha256=expected_result_sha256
        )
        if len(core.canonical_json_bytes(detached)) > (
            M37_MAXIMUM_OUTCOME_CANONICAL_BYTES
        ):
            raise M37ValidationError("M37 outcome result exceeds its byte capacity")
        _validate_outcome_payload(detached)
        return detached
    except M37ValidationError:
        raise
    except Exception as error:
        raise M37ValidationError("M37 outcome validation failed closed") from error


def canonical_m37_outcome_bytes(
    result: Mapping[str, Any],
    *,
    expected_result_sha256: str | None = None,
) -> bytes:
    """Return canonical JSON bytes after live/trusted outcome validation."""
    validated = validate_m37_outcome(
        result, expected_result_sha256=expected_result_sha256
    )
    return core.canonical_json_bytes(validated)


def rehydrate_m37_outcome(
    payload: bytes | bytearray,
    *,
    expected_result_sha256: str,
) -> dict[str, Any]:
    """Parse canonical persisted JSON and require its independent receipt."""
    if not isinstance(payload, (bytes, bytearray)):
        raise M37ValidationError("persisted M37 outcome must be bytes")
    raw = bytes(payload)
    if len(raw) > M37_MAXIMUM_OUTCOME_CANONICAL_BYTES:
        raise M37ValidationError("persisted M37 outcome exceeds its byte capacity")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise M37ValidationError("persisted M37 outcome is not valid JSON") from error
    if core.canonical_json_bytes(decoded) != raw:
        raise M37ValidationError("persisted M37 outcome is not canonical JSON")
    return validate_m37_outcome(
        decoded, expected_result_sha256=expected_result_sha256
    )


# Concise caller-facing aliases.
join_m37_outcomes = assemble_m37_outcome
build_m37_outcome = assemble_m37_outcome
orchestrate_m37_outcome = assemble_m37_outcome


__all__ = [
    "FINAL_DISPOSITIONS",
    "GLOBAL_CLOSED_NO_UNRESOLVED",
    "GLOBAL_OPEN_UNRESOLVED",
    "M37ValidationError",
    "M37_MAXIMUM_OUTCOME_CANONICAL_BYTES",
    "M37_MAXIMUM_OUTCOME_RECORDS",
    "OUTCOME_ARTIFACT_TYPE",
    "OUTCOME_SCHEMA_VERSION",
    "PHYSICAL_RFI_DISPOSITIONS",
    "RETAINED_NOT_SCIENTIFICALLY_ELIGIBLE",
    "SCIENTIFIC_CANDIDATE_UNRESOLVED",
    "UNVETOED_PHYSICAL_DISPOSITION",
    "assemble_m37_outcome",
    "build_m37_outcome",
    "canonical_m37_outcome_bytes",
    "join_m37_outcomes",
    "orchestrate_m37_outcome",
    "rehydrate_m37_outcome",
    "validate_m37_outcome",
]
