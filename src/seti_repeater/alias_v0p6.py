"""Deterministic receiver-frame alias classification for detector v0.6.

The retained-search record is the scientific unit of evidence, but receiver
aliases must not be inferred between two width/subset realizations of the same
physical ON-time track.  This module therefore constructs a normative identity
partition before inspecting stationary receiver-frame peaks:

* unique ``(template_index, proxy_carrier_index)`` tracks are vertices;
* vertices are joined when their literal maximum ON-time distance is at most
  the configured tolerance; and
* connected components, including transitive connections, are alias
  identities independent of spectral width and activity subset.

Stationary signatures are supplied separately from retention records so the
retention certificate remains an exact receipt for the unannotated detector
output.  A signature entry has the frozen schema used by the M37 wrapper::

    {
        "epoch_zero_based": 0,
        "predicted_mid_mhz": 1400.5,
        "peak_frequency_mhz": 1400.500001,
        "peak_snr": 8.0,
        "offset_from_prediction_hz": 1.0,
    }

There must be exactly one entry for every active epoch of the record.  The
literal offset is recomputed from the two MHz values and must be within the
local receiver window; caller-supplied offset evidence must agree exactly.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .search_v0p6 import (
    M37_ACTIVITY_SUBSETS,
    M37_BANK_SHA256,
    M37_EXPERIMENT_CONTRACT_SHA256,
    M37_FACTOR_BASIS_LABELS_SHA256,
    M37_FACTOR_BASIS_SHA256,
    M37_FACTOR_ROW_SELECTION_SHA256S,
    M37_MAXIMUM_ALIAS_BUCKET_ENTRIES,
    M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS,
    M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES,
    M37_MAXIMUM_RECORD_CANONICAL_BYTES,
    M37_MAXIMUM_RECORDS_PER_WINDOW,
    M37_MINIMUM_ACTIVE_EPOCH_SNR,
    M37_SCAN_INVENTORY_SHA256,
    M37_SCORE_HALF_BINS,
    M37_SPECTRAL_WIDTHS,
    M37_TEMPLATE_COUNT,
    M37_WINDOW_IDS,
    FactorBasis,
    ProxyCarrierGrid,
    TemplateFactorTable,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6IncompleteError,
    _frozen_sha256,
    _retention_record_sort_key,
    _strict_int,
    _validated_retained_records,
    canonical_json_bytes,
    factor_matrix_for_kind,
    factor_table_sha256,
    make_line_template_bank,
    make_m37_proxy_carrier_grid,
    proxy_carrier_grid_sha256,
    validate_factor_basis,
    validate_m37_factor_basis_scan_inventory,
    validate_retention_certificate,
    validate_template_factor_table,
)


M37_ALIAS_TRACK_TOLERANCE_HZ = 20.0
M37_RECEIVER_LOCAL_HALF_WIDTH_HZ = 100.0
M37_RECEIVER_PEAK_SNR_FLOOR = 5.5
M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS = 2
M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS = 5_000_000
_RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS = 2


_RECEIVER_ALIAS_CERTIFICATE_ATTESTATIONS: dict[str, bytes] = {}
_RECEIVER_ALIAS_CERTIFICATE_ATTESTATION_CAP = 1_024


_ALLOWED_OFF_INPUT_DISPOSITIONS = frozenset(
    {
        "rfi_veto_matched_off_same_hypothesis",
        "rfi_veto_local_off_track",
        "pending_receiver_alias_evaluation",
    }
)
_ALLOWED_FINAL_DISPOSITIONS = frozenset(
    _ALLOWED_OFF_INPUT_DISPOSITIONS
    | {"rfi_veto_single_adjacent_off", "rfi_veto_receiver_frame_alias"}
)

# Exact schema emitted by ExhaustiveRetentionLedger.  Post-retention veto
# stages may add evidence fields, so reconstruct the certified base record
# rather than trusting the mutable annotations.
_RETENTION_RECORD_FIELDS = frozenset(
    {
        "record_id",
        "record_key",
        "window_id",
        "scan_kind",
        "snr",
        "proxy_carrier_hz",
        "proxy_carrier_mhz",
        "proxy_carrier_index",
        "proxy_carrier_lattice_index",
        "q_offset_bin",
        "spectral_width_channels",
        "spectral_width_index",
        "template_index",
        "line_index",
        "line_coefficient",
        "projected_scale",
        "phase_offset_cycles",
        "active_epochs_zero_based",
        "epoch_values_at_proxy_carrier",
        "epoch_value_is_finite",
        "operational_threshold_snr",
        "minimum_active_epoch_snr",
        "stack_statistic",
        "threshold_certificate_sha256",
        "epoch_vector_product_sha256",
        "mask_product_sha256",
        "filter_coordinate",
        "member_disposition",
    }
)


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))
        self._rank = [0] * size

    def find(self, index: int) -> int:
        parent = self._parent[index]
        while parent != index:
            grandparent = self._parent[parent]
            self._parent[index] = grandparent
            index = parent
            parent = grandparent
        return index

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        left_rank = self._rank[left_root]
        right_rank = self._rank[right_root]
        if left_rank < right_rank:
            left_root, right_root = right_root, left_root
        self._parent[right_root] = left_root
        if left_rank == right_rank:
            self._rank[left_root] += 1


def _detached_json(value: Any, label: str) -> Any:
    try:
        return json.loads(canonical_json_bytes(value))
    except (TypeError, ValueError) as error:
        raise V0P6ContractError(f"{label} is not canonical finite JSON") from error


def _finite_json_number(value: Any, label: str) -> float:
    """Require a JSON numeric scalar without accepting bools or strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V0P6ContractError(f"{label} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise V0P6ContractError(f"{label} must be a finite JSON number")
    return converted


def _stable_record_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (*_retention_record_sort_key(record), str(record["record_id"]))


def _validated_annotated_records(
    records: Sequence[Mapping[str, Any]],
    retention_certificate: Mapping[str, Any],
    grid: ProxyCarrierGrid,
    *,
    template_count: int,
    template_bank: Sequence[Mapping[str, Any]] | None,
    expected_certificate_sha256: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate annotations and recover the exact certified ON base product."""
    annotated = _detached_json(list(records), "annotated retained-record product")
    if not isinstance(annotated, list):
        raise V0P6ContractError("annotated retained-record product must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    base_records: list[dict[str, Any]] = []
    for item in annotated:
        if not isinstance(item, dict):
            raise V0P6ContractError("annotated retained record must be an object")
        record_id = str(item.get("record_id", ""))
        if not record_id or record_id in by_id:
            raise V0P6IncompleteError(
                "annotated retained product has a missing or duplicate record ID"
            )
        disposition = item.get("member_disposition")
        if disposition not in _ALLOWED_OFF_INPUT_DISPOSITIONS:
            raise V0P6ContractError(
                "receiver-alias input has not completed the prior OFF stages"
            )
        if "receiver_alias_evidence" in item:
            raise V0P6ContractError("receiver-alias stage cannot be replayed in place")
        base = {
            name: item[name]
            for name in _RETENTION_RECORD_FIELDS
            if name in item
        }
        base["member_disposition"] = "pending_physical_veto_evaluation"
        base_records.append(base)
        by_id[record_id] = item

    certified = _validated_retained_records(
        base_records,
        retention_certificate,
        grid,
        expected_kind="on",
        expected_template_count=template_count,
        template_bank=template_bank,
        expected_certificate_sha256=expected_certificate_sha256,
    )
    certified_ids = {str(item["record_id"]) for item in certified}
    if certified_ids != set(by_id):
        raise V0P6IncompleteError(
            "annotated records differ from the certified ON retention inventory"
        )
    ordered = [by_id[str(item["record_id"])] for item in certified]
    return ordered, certified


def _validate_off_match_receipt(
    annotated: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    retention_certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str,
) -> dict[str, Any]:
    """Validate the exact OFF-annotated bytes against a trusted receipt."""
    expected = _frozen_sha256(
        expected_certificate_sha256, "expected OFF-match certificate identity"
    )
    from .search_v0p6 import validate_off_match_result

    validate_off_match_result(
        annotated,
        certificate,
        expected_certificate_sha256=expected,
    )
    cert = _detached_json(dict(certificate), "OFF-match certificate")
    required = {
        "window_id",
        "contract",
        "inclusive_comparison",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "on_record_count",
        "all_on_records_annotated_exactly_once",
        "disposition_counts",
        "annotated_records_sha256",
        "truncation_permitted",
        "off_match_certificate_sha256",
    }
    if not required <= set(cert):
        raise V0P6ContractError("OFF-match certificate lacks required identities")
    observed = _frozen_sha256(
        cert.pop("off_match_certificate_sha256"),
        "OFF-match certificate identity",
    )
    calculated = hashlib.sha256(canonical_json_bytes(cert)).hexdigest()
    if observed != calculated:
        raise V0P6IncompleteError("OFF-match certificate SHA-256 changed")
    if observed != expected:
        raise V0P6ContractError("OFF-match certificate differs from trusted receipt")
    cert["off_match_certificate_sha256"] = observed
    retention_sha = _frozen_sha256(
        retention_certificate["retention_certificate_sha256"],
        "ON retention certificate identity",
    )
    input_sha = hashlib.sha256(canonical_json_bytes(list(annotated))).hexdigest()
    if (
        cert["contract"] != "literal maximum OFF-time track distance in Hz"
        or cert["inclusive_comparison"]
        != "maximum_track_distance_hz <= tolerance_hz"
        or str(cert["window_id"]) != str(retention_certificate["window_id"])
        or cert["on_retention_certificate_sha256"] != retention_sha
        or cert["on_records_sha256"] != retention_certificate["records_sha256"]
        or _strict_int(cert["on_record_count"], "OFF-match ON-record count")
        != len(annotated)
        or cert["annotated_records_sha256"] != input_sha
        or cert["all_on_records_annotated_exactly_once"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise V0P6IncompleteError(
            "OFF-match receipt does not bind the exact alias input"
        )
    observed_counts = {
        name: 0 for name in sorted(_ALLOWED_OFF_INPUT_DISPOSITIONS)
    }
    for record in annotated:
        disposition = record["member_disposition"]
        if disposition not in observed_counts:
            raise V0P6ContractError("OFF-match disposition is invalid")
        if not isinstance(record.get("off_track_evidence"), dict):
            raise V0P6IncompleteError("OFF-track evidence is missing")
        observed_counts[disposition] += 1
    if cert["disposition_counts"] != observed_counts:
        raise V0P6IncompleteError("OFF-match disposition counts changed")
    return cert


def _validate_single_adjacent_receipt(
    evidence: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    retention_certificate: Mapping[str, Any],
    certified_records: Sequence[Mapping[str, Any]],
    *,
    expected_certificate_sha256: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Validate exhaustive adjacent-OFF evidence and its trusted receipt."""
    from .adjacent_v0p6 import validate_single_adjacent_off_result

    expected = _frozen_sha256(
        expected_certificate_sha256,
        "expected single-adjacent-OFF certificate identity",
    )
    validate_single_adjacent_off_result(
        evidence,
        certificate,
        expected_certificate_sha256=expected,
    )
    cert = _detached_json(dict(certificate), "single-adjacent-OFF certificate")
    required = {
        "window_id",
        "contract",
        "comparison",
        "single_epoch_snr_floor",
        "exact_same_q_template_width",
        "exclusion_mask_applied",
        "frequency_neighborhood_hz",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "input_record_count",
        "evidence_record_count",
        "evidence_canonical_bytes",
        "all_input_records_evaluated_exactly_once",
        "all_active_epoch_queries_evaluated_exactly_once",
        "truncation_permitted",
        "evidence_sha256",
        "single_adjacent_off_certificate_sha256",
    }
    if not required <= set(cert):
        raise V0P6ContractError(
            "single-adjacent-OFF certificate lacks required identities"
        )
    observed = _frozen_sha256(
        cert.pop("single_adjacent_off_certificate_sha256"),
        "single-adjacent-OFF certificate identity",
    )
    calculated = hashlib.sha256(canonical_json_bytes(cert)).hexdigest()
    if observed != calculated:
        raise V0P6IncompleteError(
            "single-adjacent-OFF certificate SHA-256 changed"
        )
    if observed != expected:
        raise V0P6ContractError(
            "single-adjacent-OFF certificate differs from trusted receipt"
        )
    cert["single_adjacent_off_certificate_sha256"] = observed
    detached = _detached_json(
        list(evidence), "single-adjacent-OFF evidence product"
    )
    if not isinstance(detached, list):
        raise V0P6ContractError("single-adjacent-OFF evidence must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for item in detached:
        if not isinstance(item, dict):
            raise V0P6ContractError(
                "single-adjacent-OFF evidence record must be an object"
            )
        record_id = str(item.get("record_id", ""))
        if not record_id or record_id in by_id:
            raise V0P6IncompleteError(
                "single-adjacent-OFF evidence repeats a record ID"
            )
        by_id[record_id] = item
    ordered: list[dict[str, Any]] = []
    certified_ids = {str(record["record_id"]) for record in certified_records}
    if set(by_id) != certified_ids:
        raise V0P6IncompleteError(
            "single-adjacent-OFF evidence does not cover the retained inventory"
        )
    floor = _finite_json_number(
        cert["single_epoch_snr_floor"], "adjacent single-epoch S/N floor"
    )
    if (
        not math.isfinite(floor)
        or cert["contract"]
        != "exact paired adjacent OFF q/template/width native gather"
        or cert["comparison"]
        != "any active-epoch S/N >= single_epoch_snr_floor"
        or cert["exact_same_q_template_width"] is not True
        or cert["exclusion_mask_applied"] is not False
        or _finite_json_number(
            cert["frequency_neighborhood_hz"],
            "adjacent frequency neighborhood",
        )
        != 0.0
        or str(cert["window_id"]) != str(retention_certificate["window_id"])
        or cert["on_retention_certificate_sha256"]
        != retention_certificate["retention_certificate_sha256"]
        or cert["on_records_sha256"] != retention_certificate["records_sha256"]
        or cert["proxy_grid_sha256"] != retention_certificate["proxy_grid_sha256"]
        or _strict_int(cert["input_record_count"], "adjacent input-record count")
        != len(certified_records)
        or _strict_int(cert["evidence_record_count"], "adjacent evidence count")
        != len(certified_records)
        or cert["all_input_records_evaluated_exactly_once"] is not True
        or cert["all_active_epoch_queries_evaluated_exactly_once"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise V0P6IncompleteError(
            "single-adjacent-OFF receipt does not bind the retained product"
        )

    for record in certified_records:
        record_id = str(record["record_id"])
        item = by_id[record_id]
        active_epochs = tuple(
            _strict_int(epoch, "active epoch")
            for epoch in record["active_epochs_zero_based"]
        )
        if (
            _strict_int(item.get("template_index"), "adjacent template index")
            != int(record["template_index"])
            or _strict_int(
                item.get("spectral_width_index"), "adjacent spectral-width index"
            )
            != int(record["spectral_width_index"])
            or _strict_int(
                item.get("spectral_width_channels"), "adjacent spectral width"
            )
            != int(record["spectral_width_channels"])
            or _strict_int(
                item.get("proxy_carrier_index"), "adjacent proxy-carrier index"
            )
            != int(record["proxy_carrier_index"])
            or _finite_json_number(
                item.get("proxy_carrier_hz"), "adjacent proxy carrier"
            )
            != float(record["proxy_carrier_hz"])
            or tuple(item.get("active_epochs_zero_based", ())) != active_epochs
            or _finite_json_number(
                item.get("single_epoch_snr_floor"),
                "adjacent evidence single-epoch S/N floor",
            )
            != floor
            or item.get("comparison")
            != "native_gathered_snr >= single_epoch_snr_floor"
            or item.get("exact_same_q_template_width") is not True
            or item.get("exclusion_mask_applied") is not False
            or _finite_json_number(
                item.get("frequency_neighborhood_hz"),
                "adjacent evidence frequency neighborhood",
            )
            != 0.0
        ):
            raise V0P6ContractError(
                "single-adjacent-OFF evidence identity changed"
            )
        measurements = item.get("paired_adjacent_off_measurements")
        if not isinstance(measurements, list) or len(measurements) != len(
            active_epochs
        ):
            raise V0P6IncompleteError(
                "single-adjacent-OFF measurements are incomplete"
            )
        measured_by_epoch: dict[int, bool] = {}
        measured_snrs: list[float] = []
        for measurement in measurements:
            if not isinstance(measurement, dict):
                raise V0P6ContractError("adjacent-OFF measurement is malformed")
            epoch = _strict_int(
                measurement.get("epoch_zero_based"), "adjacent measurement epoch"
            )
            snr = _finite_json_number(
                measurement.get("snr"), "adjacent measurement S/N"
            )
            meets = measurement.get("meets_single_epoch_floor")
            if (
                epoch in measured_by_epoch
                or epoch not in active_epochs
                or not math.isfinite(snr)
                or not isinstance(meets, bool)
                or meets != (snr >= floor)
                or not str(measurement.get("paired_on_scan_label", ""))
                or not str(measurement.get("paired_off_scan_label", ""))
            ):
                raise V0P6ContractError(
                    "single-adjacent-OFF measurement semantics changed"
                )
            measured_by_epoch[epoch] = meets
            measured_snrs.append(snr)
        if tuple(sorted(measured_by_epoch)) != tuple(sorted(active_epochs)):
            raise V0P6IncompleteError(
                "single-adjacent-OFF measurement epochs are incomplete"
            )
        matching_epochs = tuple(
            _strict_int(epoch, "matching adjacent epoch")
            for epoch in item.get("matching_active_epochs_zero_based", ())
        )
        expected_matching = tuple(
            epoch for epoch in active_epochs if measured_by_epoch[epoch]
        )
        vetoed = item.get("vetoed")
        expected_disposition = (
            "rfi_veto_single_adjacent_off"
            if expected_matching
            else "pending_receiver_alias_evaluation"
        )
        if (
            matching_epochs != expected_matching
            or not isinstance(vetoed, bool)
            or vetoed != bool(expected_matching)
            or _finite_json_number(
                item.get("maximum_active_epoch_snr"),
                "adjacent maximum active-epoch S/N",
            )
            != max(measured_snrs)
            or item.get("recommended_member_disposition") != expected_disposition
        ):
            raise V0P6ContractError(
                "single-adjacent-OFF veto evidence is inconsistent"
            )
        ordered.append(item)
    evidence_bytes = canonical_json_bytes(ordered)
    if (
        hashlib.sha256(evidence_bytes).hexdigest() != cert["evidence_sha256"]
        or len(evidence_bytes)
        != _strict_int(
            cert["evidence_canonical_bytes"], "adjacent evidence byte count"
        )
    ):
        raise V0P6IncompleteError("single-adjacent-OFF evidence bytes changed")
    return by_id, cert


def _validate_signatures(
    records: Sequence[Mapping[str, Any]],
    receiver_signatures: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    local_half_width_hz: float,
) -> tuple[dict[str, tuple[dict[str, Any], ...]], str]:
    if not isinstance(receiver_signatures, Mapping):
        raise V0P6ContractError("receiver signatures must be keyed by record ID")
    if any(not isinstance(key, str) for key in receiver_signatures):
        raise V0P6ContractError("receiver-signature keys must be record-ID strings")
    keys = set(receiver_signatures)
    record_ids = {str(item["record_id"]) for item in records}
    if keys != record_ids or len(keys) != len(receiver_signatures):
        raise V0P6IncompleteError(
            "receiver signatures do not cover the exact retained-record inventory"
        )

    normalized: dict[str, tuple[dict[str, Any], ...]] = {}
    product: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record["record_id"])
        raw_entries = receiver_signatures[record_id]
        if isinstance(raw_entries, (str, bytes)):
            raise V0P6ContractError("receiver signature must be a sequence of objects")
        try:
            entries = list(raw_entries)
        except TypeError as error:
            raise V0P6ContractError(
                "receiver signature must be a sequence of objects"
            ) from error
        active_epochs = tuple(
            _strict_int(item, "active epoch")
            for item in record["active_epochs_zero_based"]
        )
        by_epoch: dict[int, dict[str, Any]] = {}
        for raw in entries:
            if not isinstance(raw, Mapping):
                raise V0P6ContractError("receiver signature entry must be an object")
            required = {
                "epoch_zero_based",
                "predicted_mid_mhz",
                "peak_frequency_mhz",
                "peak_snr",
                "offset_from_prediction_hz",
            }
            if set(raw) != required:
                raise V0P6ContractError("receiver signature entry schema changed")
            epoch = _strict_int(raw["epoch_zero_based"], "signature epoch")
            if epoch in by_epoch:
                raise V0P6IncompleteError("receiver signature repeats an epoch")
            predicted_mhz = _finite_json_number(
                raw["predicted_mid_mhz"], "receiver predicted midpoint"
            )
            peak_mhz = _finite_json_number(
                raw["peak_frequency_mhz"], "receiver peak frequency"
            )
            peak_snr = _finite_json_number(
                raw["peak_snr"], "receiver peak S/N"
            )
            stated_offset_hz = _finite_json_number(
                raw["offset_from_prediction_hz"],
                "receiver offset from prediction",
            )
            values = (predicted_mhz, peak_mhz, peak_snr, stated_offset_hz)
            if not all(math.isfinite(value) for value in values):
                raise V0P6ContractError("receiver signature contains non-finite evidence")
            if not math.isfinite(predicted_mhz * 1e6) or not math.isfinite(
                peak_mhz * 1e6
            ):
                raise V0P6ContractError(
                    "receiver signature overflows its literal Hz coordinate"
                )
            literal_offset_hz = float((peak_mhz - predicted_mhz) * 1e6)
            if stated_offset_hz != literal_offset_hz:
                raise V0P6ContractError(
                    "receiver signature offset does not reproduce literally"
                )
            if abs(literal_offset_hz) > local_half_width_hz:
                raise V0P6ContractError(
                    "receiver peak lies outside the frozen local window"
                )
            by_epoch[epoch] = {
                "epoch_zero_based": epoch,
                "predicted_mid_mhz": predicted_mhz,
                "peak_frequency_mhz": peak_mhz,
                "peak_snr": peak_snr,
                "offset_from_prediction_hz": literal_offset_hz,
            }
        if tuple(sorted(by_epoch)) != tuple(sorted(active_epochs)):
            raise V0P6IncompleteError(
                "receiver signature does not cover the exact active epochs"
            )
        canonical_entries = tuple(by_epoch[epoch] for epoch in sorted(by_epoch))
        normalized[record_id] = canonical_entries
        product.append(
            {"record_id": record_id, "receiver_frame_signature": canonical_entries}
        )
    product.sort(key=lambda item: item["record_id"])
    return normalized, hashlib.sha256(canonical_json_bytes(product)).hexdigest()


def _build_alias_identity_partition(
    records: Sequence[Mapping[str, Any]],
    factors: np.ndarray,
    tolerance_hz: float,
    maximum_track_comparisons: int,
) -> tuple[dict[tuple[int, int], str], dict[str, Any]]:
    """Return connected-component identities for unique retained ON tracks."""
    maximum_track_comparisons = _strict_int(
        maximum_track_comparisons,
        "alias identity track-comparison capacity",
    )
    if maximum_track_comparisons < 1:
        raise V0P6ContractError(
            "alias identity track-comparison capacity must be positive"
        )
    node_keys = sorted(
        {
            (
                _strict_int(item["template_index"], "template index"),
                _strict_int(item["proxy_carrier_index"], "proxy-carrier index"),
            )
            for item in records
        }
    )
    if not node_keys:
        partition: list[dict[str, Any]] = []
        digest = hashlib.sha256(canonical_json_bytes(partition)).hexdigest()
        return {}, {
            "node_count": 0,
            "component_count": 0,
            "edge_count": 0,
            "track_comparisons": 0,
            "maximum_track_comparisons": maximum_track_comparisons,
            "maximum_anchor_pruning_roundoff_guard_hz": 0.0,
            "partition": partition,
            "partition_sha256": digest,
        }

    by_record_key = {
        (
            int(record["template_index"]),
            int(record["proxy_carrier_index"]),
        ): float(record["proxy_carrier_hz"])
        for record in records
    }
    tracks: list[np.ndarray] = []
    anchored: list[tuple[float, tuple[int, int], int]] = []
    maximum_guard = 0.0
    for node_index, key in enumerate(node_keys):
        template_index, _ = key
        q_hz = np.float64(by_record_key[key])
        track = np.asarray(q_hz * factors[template_index], dtype=np.float64)
        if not np.all(np.isfinite(track)):
            raise V0P6ContractError("alias identity produced a non-finite ON track")
        tracks.append(track)
        anchored.append((float(track[0]), key, node_index))
    anchored.sort(key=lambda item: (item[0], item[1]))
    anchors = np.asarray([item[0] for item in anchored], dtype=np.float64)

    union = _DisjointSet(len(node_keys))
    edge_count = 0
    track_comparisons = 0
    for ordered_index, (anchor, _, node_index) in enumerate(anchored):
        scale = max(abs(anchor), abs(tolerance_hz), 1.0)
        guard = 4.0 * float(np.spacing(np.float64(scale)))
        if not math.isfinite(guard):
            raise V0P6ContractError("alias anchor roundoff guard is non-finite")
        maximum_guard = max(maximum_guard, guard)
        upper = float(
            np.nextafter(
                np.float64(anchor) + np.float64(tolerance_hz) + guard,
                np.inf,
            )
        )
        stop = int(np.searchsorted(anchors, upper, side="right"))
        left_track = tracks[node_index]
        for candidate_position in range(ordered_index + 1, stop):
            track_comparisons += 1
            if track_comparisons > maximum_track_comparisons:
                raise V0P6CapacityError(
                    "alias identity track-comparison capacity exceeded"
                )
            candidate_index = anchored[candidate_position][2]
            delta = np.abs(left_track - tracks[candidate_index])
            if not np.all(np.isfinite(delta)):
                raise V0P6ContractError("alias identity distance became non-finite")
            if float(np.max(delta)) <= tolerance_hz:
                union.union(node_index, candidate_index)
                edge_count += 1

    members_by_root: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for node_index, key in enumerate(node_keys):
        members_by_root[union.find(node_index)].append(key)
    ordered_components = sorted(
        (sorted(members) for members in members_by_root.values()),
        key=lambda members: members[0],
    )
    component_by_node: dict[tuple[int, int], str] = {}
    partition: list[dict[str, Any]] = []
    for ordinal, members in enumerate(ordered_components):
        component_sha = hashlib.sha256(
            canonical_json_bytes([[template, proxy] for template, proxy in members])
        ).hexdigest()
        for key in members:
            component_by_node[key] = component_sha
        partition.append(
            {
                "component_ordinal": ordinal,
                "component_sha256": component_sha,
                "members": [
                    {"template_index": template, "proxy_carrier_index": proxy}
                    for template, proxy in members
                ],
            }
        )
    partition_sha = hashlib.sha256(canonical_json_bytes(partition)).hexdigest()
    return component_by_node, {
        "node_count": len(node_keys),
        "component_count": len(ordered_components),
        "edge_count": edge_count,
        "track_comparisons": track_comparisons,
        "maximum_track_comparisons": maximum_track_comparisons,
        "maximum_anchor_pruning_roundoff_guard_hz": maximum_guard,
        "partition": partition,
        "partition_sha256": partition_sha,
    }


def _literal_alias_matches(
    left: Mapping[int, Mapping[str, Any]],
    right: Mapping[int, Mapping[str, Any]],
    *,
    tolerance_hz: float,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for epoch in sorted(set(left) & set(right)):
        left_peak = left[epoch]
        right_peak = right[epoch]
        delta_hz = float(
            (
                float(right_peak["peak_frequency_mhz"])
                - float(left_peak["peak_frequency_mhz"])
            )
            * 1e6
        )
        if abs(delta_hz) <= tolerance_hz:
            matches.append(
                {
                    "epoch_zero_based": epoch,
                    "delta_hz": delta_hz,
                    "left_peak_snr": float(left_peak["peak_snr"]),
                    "right_peak_snr": float(right_peak["peak_snr"]),
                }
            )
    return matches


def _receiver_witness(
    record: Mapping[str, Any],
    component_sha256: str,
    matches: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "record_id": str(record["record_id"]),
        "snr": float(record["snr"]),
        "template_index": _strict_int(record["template_index"], "template index"),
        "spectral_width_index": _strict_int(
            record["spectral_width_index"], "spectral-width index"
        ),
        "active_epochs_zero_based": [
            _strict_int(item, "active epoch")
            for item in record["active_epochs_zero_based"]
        ],
        "proxy_carrier_index": _strict_int(
            record["proxy_carrier_index"], "proxy-carrier index"
        ),
        "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
        "alias_identity_component_sha256": component_sha256,
        "matched_active_epochs": list(matches),
    }


def match_receiver_frame_aliases(
    records: Sequence[Mapping[str, Any]],
    on_retention_certificate: Mapping[str, Any],
    grid: ProxyCarrierGrid,
    on_factor_matrix: np.ndarray,
    receiver_signatures: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    off_match_certificate: Mapping[str, Any],
    single_adjacent_off_evidence: Sequence[Mapping[str, Any]],
    single_adjacent_off_certificate: Mapping[str, Any],
    expected_off_match_certificate_sha256: str,
    expected_single_adjacent_off_certificate_sha256: str,
    window_order: Sequence[str],
    track_tolerance_hz: float,
    local_half_width_hz: float,
    local_peak_snr_floor: float,
    minimum_shared_active_epochs: int,
    maximum_records: int,
    maximum_bucket_entries: int,
    maximum_identity_track_comparisons: int,
    maximum_distinct_candidate_visits_per_window: int,
    template_bank: Sequence[Mapping[str, Any]] | None = None,
    expected_on_certificate_sha256: str | None = None,
    receiver_signature_certificate_sha256: str | None = None,
    expected_receiver_signature_product_sha256: str | None = None,
) -> dict[str, Any]:
    """Classify retained ON members using cross-identity receiver aliases.

    Candidate visits are distinct records reached for each left record by the
    signature buckets, excluding only that left record.  The frozen capacity
    is their cumulative per-window total, measured before same-component and
    literal-match rejection.
    """
    on_cert = validate_retention_certificate(
        on_retention_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if on_cert["scan_kind"] != "on":
        raise V0P6ContractError("receiver-alias stage requires an ON retention product")
    windows = tuple(str(item) for item in window_order)
    if not windows or len(set(windows)) != len(windows):
        raise V0P6ContractError("receiver-alias window order is invalid")
    try:
        window_ordinal = windows.index(str(on_cert["window_id"]))
    except ValueError as error:
        raise V0P6ContractError(
            "retention window is absent from receiver-alias order"
        ) from error

    track_tolerance_hz = float(track_tolerance_hz)
    local_half_width_hz = float(local_half_width_hz)
    local_peak_snr_floor = float(local_peak_snr_floor)
    minimum_shared_active_epochs = _strict_int(
        minimum_shared_active_epochs, "minimum shared active epochs"
    )
    maximum_records = _strict_int(maximum_records, "receiver-alias record capacity")
    maximum_bucket_entries = _strict_int(
        maximum_bucket_entries, "receiver-alias bucket-entry capacity"
    )
    maximum_identity_track_comparisons = _strict_int(
        maximum_identity_track_comparisons,
        "alias identity track-comparison capacity",
    )
    maximum_distinct_candidate_visits_per_window = _strict_int(
        maximum_distinct_candidate_visits_per_window,
        "receiver-alias candidate-visit capacity",
    )
    if (
        not math.isfinite(track_tolerance_hz)
        or track_tolerance_hz <= 0.0
        or not math.isfinite(local_half_width_hz)
        or local_half_width_hz <= 0.0
        or not math.isfinite(local_peak_snr_floor)
    ):
        raise V0P6ContractError("receiver-alias thresholds must be finite and valid")
    if minimum_shared_active_epochs < 2:
        raise V0P6ContractError("receiver alias requires at least two shared epochs")
    if min(
        maximum_records,
        maximum_bucket_entries,
        maximum_identity_track_comparisons,
        maximum_distinct_candidate_visits_per_window,
    ) < 1:
        raise V0P6ContractError("receiver-alias capacities must be positive")
    factors = np.asarray(on_factor_matrix)
    if factors.ndim != 2 or not np.issubdtype(factors.dtype, np.floating):
        raise V0P6ContractError("ON alias factors must be a floating matrix")
    if factors.shape[0] < 1 or factors.shape[1] < 1:
        raise V0P6ContractError("ON alias factor matrix must be non-empty")
    if not np.all(np.isfinite(factors)) or np.any(factors <= 0.0):
        raise V0P6ContractError("ON alias factors must be finite and positive")
    factors = np.array(factors, dtype=np.float64, order="C", copy=True)
    factors.setflags(write=False)
    factor_digest = factor_table_sha256(factors)

    annotated, certified = _validated_annotated_records(
        records,
        on_cert,
        grid,
        template_count=int(factors.shape[0]),
        template_bank=template_bank,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if len(annotated) > maximum_records:
        raise V0P6CapacityError("receiver-alias input-record capacity exceeded")
    validated_off_certificate = _validate_off_match_receipt(
        annotated,
        off_match_certificate,
        on_cert,
        expected_certificate_sha256=expected_off_match_certificate_sha256,
    )
    adjacent_by_id, validated_adjacent_certificate = (
        _validate_single_adjacent_receipt(
            single_adjacent_off_evidence,
            single_adjacent_off_certificate,
            on_cert,
            certified,
            expected_certificate_sha256=(
                expected_single_adjacent_off_certificate_sha256
            ),
        )
    )
    normalized_signatures, signature_product_sha = _validate_signatures(
        certified,
        receiver_signatures,
        local_half_width_hz=local_half_width_hz,
    )
    signature_certificate_sha: str | None = None
    if receiver_signature_certificate_sha256 is not None:
        signature_certificate_sha = _frozen_sha256(
            receiver_signature_certificate_sha256,
            "receiver-signature certificate identity",
        )
    if expected_receiver_signature_product_sha256 is not None and (
        signature_product_sha
        != _frozen_sha256(
            expected_receiver_signature_product_sha256,
            "expected receiver-signature product identity",
        )
    ):
        raise V0P6ContractError(
            "receiver signatures differ from their upstream product receipt"
        )
    component_by_node, partition_evidence = _build_alias_identity_partition(
        certified,
        factors,
        track_tolerance_hz,
        maximum_identity_track_comparisons,
    )
    component_ordinals = {
        str(item["component_sha256"]): int(item["component_ordinal"])
        for item in partition_evidence["partition"]
    }

    ordered_indices = sorted(
        range(len(certified)), key=lambda index: _stable_record_key(certified[index])
    )
    qualified: dict[int, dict[int, dict[str, Any]]] = {}
    buckets: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
    bucket_entry_count = 0
    for record_index in ordered_indices:
        record_id = str(certified[record_index]["record_id"])
        signature = {
            int(item["epoch_zero_based"]): item
            for item in normalized_signatures[record_id]
            if float(item["peak_snr"]) >= local_peak_snr_floor
        }
        qualified[record_index] = signature
        epochs = sorted(signature)
        for left_position, left_epoch in enumerate(epochs):
            for right_epoch in epochs[left_position + 1 :]:
                left_cell = math.floor(
                    float(signature[left_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / track_tolerance_hz
                )
                right_cell = math.floor(
                    float(signature[right_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / track_tolerance_hz
                )
                buckets[(left_epoch, right_epoch, left_cell, right_cell)].append(
                    record_index
                )
                bucket_entry_count += 1
                if bucket_entry_count > maximum_bucket_entries:
                    raise V0P6CapacityError(
                        "receiver-alias bucket-entry capacity exceeded"
                    )
    for bucket in buckets.values():
        bucket.sort(key=lambda index: _stable_record_key(certified[index]))

    input_sha = hashlib.sha256(canonical_json_bytes(annotated)).hexdigest()
    annotated_by_id = {str(item["record_id"]): item for item in annotated}
    total_distinct_candidate_visits = 0
    maximum_observed_visits = 0
    disposition_counts = {name: 0 for name in sorted(_ALLOWED_FINAL_DISPOSITIONS)}
    result_records: list[dict[str, Any]] = []
    for left_index in ordered_indices:
        left = certified[left_index]
        left_signature = qualified[left_index]
        epochs = sorted(left_signature)
        candidate_indices: set[int] = set()
        for left_position, left_epoch in enumerate(epochs):
            for right_epoch in epochs[left_position + 1 :]:
                left_cell = math.floor(
                    float(left_signature[left_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / track_tolerance_hz
                )
                right_cell = math.floor(
                    float(left_signature[right_epoch]["peak_frequency_mhz"])
                    * 1e6
                    / track_tolerance_hz
                )
                # Two cells are required for literal completeness at a rare
                # floating boundary: independent MHz->Hz rounding can place
                # two peaks with a reproduced separation of exactly one
                # tolerance in cells N-1 and N+1.
                neighbor_deltas = range(
                    -_RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS,
                    _RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS + 1,
                )
                for left_delta in neighbor_deltas:
                    for right_delta in range(
                        -_RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS,
                        _RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS + 1,
                    ):
                        candidate_indices.update(
                            buckets.get(
                                (
                                    left_epoch,
                                    right_epoch,
                                    left_cell + left_delta,
                                    right_cell + right_delta,
                                ),
                                (),
                            )
                        )
        candidate_indices.discard(left_index)
        distinct_visits = len(candidate_indices)
        total_distinct_candidate_visits += distinct_visits
        if total_distinct_candidate_visits > (
            maximum_distinct_candidate_visits_per_window
        ):
            raise V0P6CapacityError(
                "receiver-alias per-window distinct candidate-visit capacity exceeded"
            )
        maximum_observed_visits = max(maximum_observed_visits, distinct_visits)

        left_node = (int(left["template_index"]), int(left["proxy_carrier_index"]))
        left_component = component_by_node[left_node]
        matches_by_candidate: list[
            tuple[dict[str, Any], str, list[dict[str, Any]]]
        ] = []
        for candidate_index in sorted(
            candidate_indices, key=lambda index: _stable_record_key(certified[index])
        ):
            candidate = certified[candidate_index]
            candidate_node = (
                int(candidate["template_index"]),
                int(candidate["proxy_carrier_index"]),
            )
            candidate_component = component_by_node[candidate_node]
            if candidate_component == left_component:
                continue
            literal_matches = _literal_alias_matches(
                left_signature,
                qualified[candidate_index],
                tolerance_hz=track_tolerance_hz,
            )
            if len(literal_matches) >= minimum_shared_active_epochs:
                matches_by_candidate.append(
                    (candidate, candidate_component, literal_matches)
                )
        matches_by_candidate.sort(
            key=lambda item: (-float(item[0]["snr"]), _stable_record_key(item[0]))
        )

        record_id = str(left["record_id"])
        evidence = {
            "alias_identity_component_ordinal": component_ordinals[left_component],
            "alias_identity_component_sha256": left_component,
            "receiver_signature_sha256": hashlib.sha256(
                canonical_json_bytes(list(normalized_signatures[record_id]))
            ).hexdigest(),
            "qualified_signature_epoch_count": len(left_signature),
            "distinct_candidate_visits_before_rejection": distinct_visits,
            "matched_cross_component_record_count": len(matches_by_candidate),
            "matched": bool(matches_by_candidate),
            "best_receiver_alias_witness": (
                None
                if not matches_by_candidate
                else _receiver_witness(*matches_by_candidate[0])
            ),
        }
        evidence["receiver_alias_evidence_sha256"] = hashlib.sha256(
            canonical_json_bytes(evidence)
        ).hexdigest()
        source = annotated_by_id[record_id]
        output = _detached_json(source, "annotated retained record")
        adjacent_evidence = _detached_json(
            adjacent_by_id[record_id], "single-adjacent-OFF evidence record"
        )
        output["single_adjacent_off_evidence"] = adjacent_evidence
        off_disposition = output["member_disposition"]
        if off_disposition in {
            "rfi_veto_matched_off_same_hypothesis",
            "rfi_veto_local_off_track",
        }:
            prior_disposition = off_disposition
        else:
            prior_disposition = adjacent_evidence[
                "recommended_member_disposition"
            ]
        output["member_disposition"] = prior_disposition
        output["receiver_alias_evidence"] = evidence
        if (
            output["member_disposition"] == "pending_receiver_alias_evaluation"
            and matches_by_candidate
        ):
            output["member_disposition"] = "rfi_veto_receiver_frame_alias"
        disposition_counts[output["member_disposition"]] += 1
        result_records.append(output)

    result_records.sort(key=_retention_record_sort_key)
    encoded_sizes = [len(canonical_json_bytes(item)) for item in result_records]
    record_cap = _strict_int(
        on_cert["maximum_record_canonical_bytes"],
        "canonical record-byte capacity",
    )
    if any(size > record_cap for size in encoded_sizes):
        raise V0P6CapacityError(
            "receiver-alias annotation exceeds the record-byte capacity"
        )
    evidence_cap = on_cert["maximum_evidence_canonical_bytes"]
    if evidence_cap is not None and sum(encoded_sizes) > _strict_int(
        evidence_cap, "canonical evidence-byte capacity"
    ):
        raise V0P6CapacityError(
            "receiver-alias annotations exceed the evidence-byte capacity"
        )
    result_sha = hashlib.sha256(canonical_json_bytes(result_records)).hexdigest()
    certificate = {
        "window_id": str(on_cert["window_id"]),
        "window_ordinal": window_ordinal,
        "contract": (
            "cross-component stationary receiver peaks in at least two "
            "common active ON epochs"
        ),
        "identity_partition_contract": (
            "connected components of unique (template_index, proxy_carrier_index) "
            "under literal maximum ON-time track distance"
        ),
        "track_comparison": "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz",
        "track_tolerance_hz": track_tolerance_hz,
        "on_integration_count": int(factors.shape[1]),
        "on_factor_matrix_sha256": factor_digest,
        "local_receiver_half_width_hz": local_half_width_hz,
        "local_peak_snr_comparison": "peak_snr >= local_peak_snr_floor",
        "local_peak_snr_floor": local_peak_snr_floor,
        "peak_separation_comparison": "abs(delta_hz) <= track_tolerance_hz",
        "minimum_shared_active_epochs": minimum_shared_active_epochs,
        "on_retention_certificate_sha256": on_cert[
            "retention_certificate_sha256"
        ],
        "off_match_certificate_sha256": validated_off_certificate[
            "off_match_certificate_sha256"
        ],
        "single_adjacent_off_certificate_sha256": (
            validated_adjacent_certificate[
                "single_adjacent_off_certificate_sha256"
            ]
        ),
        "input_off_annotated_records_sha256": input_sha,
        "single_adjacent_off_evidence_sha256": (
            validated_adjacent_certificate["evidence_sha256"]
        ),
        "receiver_signature_product_sha256": signature_product_sha,
        "alias_identity_partition_sha256": partition_evidence["partition_sha256"],
        "alias_identity_node_count": partition_evidence["node_count"],
        "alias_identity_component_count": partition_evidence["component_count"],
        "alias_identity_edge_count": partition_evidence["edge_count"],
        "alias_identity_track_comparison_definition": (
            "candidate node pair surviving first-ON-time anchor pruning before "
            "literal all-ON-time track comparison"
        ),
        "alias_identity_track_comparisons": partition_evidence[
            "track_comparisons"
        ],
        "maximum_alias_identity_track_comparisons": partition_evidence[
            "maximum_track_comparisons"
        ],
        "alias_identity_anchor_pruning_roundoff_guard": (
            "4 * spacing(max(abs(left_anchor_hz), tolerance_hz, 1.0))"
        ),
        "maximum_alias_identity_anchor_pruning_roundoff_guard_hz": (
            partition_evidence["maximum_anchor_pruning_roundoff_guard_hz"]
        ),
        "input_record_count": len(certified),
        "maximum_records": maximum_records,
        "bucket_entry_definition": (
            "sum C(k, 2) over records, where k is the number of active "
            "signature epochs with peak_snr >= local_peak_snr_floor"
        ),
        "bucket_entries": bucket_entry_count,
        "maximum_bucket_entries": maximum_bucket_entries,
        "bucket_neighbor_cell_radius": _RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS,
        "candidate_visit_definition": (
            "cumulative per-window sum of distinct other records reached for "
            "each left record before identity and literal-match rejection"
        ),
        "total_distinct_candidate_visits": total_distinct_candidate_visits,
        "maximum_distinct_candidate_visits_observed_per_left": (
            maximum_observed_visits
        ),
        "maximum_distinct_candidate_visits_per_window": (
            maximum_distinct_candidate_visits_per_window
        ),
        "all_on_records_annotated_exactly_once": True,
        "disposition_counts": disposition_counts,
        "annotated_records_sha256": result_sha,
        "truncation_permitted": False,
    }
    if signature_certificate_sha is not None:
        certificate["receiver_signature_certificate_sha256"] = (
            signature_certificate_sha
        )
    certificate["receiver_alias_certificate_sha256"] = hashlib.sha256(
        canonical_json_bytes(certificate)
    ).hexdigest()
    result = {
        "records": _detached_json(result_records, "receiver-alias records"),
        "certificate": _detached_json(certificate, "receiver-alias certificate"),
    }
    alias_certificate_sha = certificate["receiver_alias_certificate_sha256"]
    encoded_certificate = canonical_json_bytes(result["certificate"])
    existing_attestation = _RECEIVER_ALIAS_CERTIFICATE_ATTESTATIONS.get(
        alias_certificate_sha
    )
    if existing_attestation is not None and existing_attestation != encoded_certificate:
        raise V0P6IncompleteError("receiver-alias certificate digest collision")
    if (
        existing_attestation is None
        and len(_RECEIVER_ALIAS_CERTIFICATE_ATTESTATIONS)
        >= _RECEIVER_ALIAS_CERTIFICATE_ATTESTATION_CAP
    ):
        raise V0P6CapacityError(
            "receiver-alias certificate attestation capacity exceeded"
        )
    _RECEIVER_ALIAS_CERTIFICATE_ATTESTATIONS[
        alias_certificate_sha
    ] = encoded_certificate
    validate_receiver_alias_result(result["records"], result["certificate"])
    return result


def validate_receiver_alias_result(
    records: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate deterministic result and per-record evidence hashes."""
    detached_records = _detached_json(list(records), "receiver-alias records")
    detached_records.sort(key=_retention_record_sort_key)
    cert = _detached_json(dict(certificate), "receiver-alias certificate")
    required = {
        "window_id",
        "window_ordinal",
        "contract",
        "identity_partition_contract",
        "track_comparison",
        "track_tolerance_hz",
        "on_integration_count",
        "on_factor_matrix_sha256",
        "local_receiver_half_width_hz",
        "local_peak_snr_comparison",
        "local_peak_snr_floor",
        "peak_separation_comparison",
        "minimum_shared_active_epochs",
        "input_record_count",
        "maximum_records",
        "off_match_certificate_sha256",
        "single_adjacent_off_certificate_sha256",
        "input_off_annotated_records_sha256",
        "single_adjacent_off_evidence_sha256",
        "bucket_entries",
        "maximum_bucket_entries",
        "bucket_neighbor_cell_radius",
        "bucket_entry_definition",
        "candidate_visit_definition",
        "total_distinct_candidate_visits",
        "maximum_distinct_candidate_visits_observed_per_left",
        "maximum_distinct_candidate_visits_per_window",
        "on_retention_certificate_sha256",
        "receiver_signature_product_sha256",
        "alias_identity_partition_sha256",
        "alias_identity_node_count",
        "alias_identity_component_count",
        "alias_identity_edge_count",
        "alias_identity_track_comparison_definition",
        "alias_identity_track_comparisons",
        "maximum_alias_identity_track_comparisons",
        "alias_identity_anchor_pruning_roundoff_guard",
        "maximum_alias_identity_anchor_pruning_roundoff_guard_hz",
        "disposition_counts",
        "annotated_records_sha256",
        "all_on_records_annotated_exactly_once",
        "truncation_permitted",
        "receiver_alias_certificate_sha256",
    }
    allowed = required | {"receiver_signature_certificate_sha256"}
    if not required <= set(cert) or not set(cert) <= allowed:
        raise V0P6ContractError("receiver-alias certificate schema changed")
    observed_certificate_sha = _frozen_sha256(
        cert.pop("receiver_alias_certificate_sha256"),
        "receiver-alias certificate identity",
    )
    calculated_certificate_sha = hashlib.sha256(canonical_json_bytes(cert)).hexdigest()
    if observed_certificate_sha != calculated_certificate_sha:
        raise V0P6IncompleteError("receiver-alias certificate SHA-256 changed")
    if expected_certificate_sha256 is not None and observed_certificate_sha != (
        _frozen_sha256(
            expected_certificate_sha256,
            "expected receiver-alias certificate identity",
        )
    ):
        raise V0P6ContractError("receiver-alias certificate differs from receipt")
    cert["receiver_alias_certificate_sha256"] = observed_certificate_sha
    live_attestation_matches = (
        _RECEIVER_ALIAS_CERTIFICATE_ATTESTATIONS.get(observed_certificate_sha)
        == canonical_json_bytes(cert)
    )
    trusted_digest_matches = (
        expected_certificate_sha256 is not None
        and observed_certificate_sha == str(expected_certificate_sha256)
    )
    if not live_attestation_matches and not trusted_digest_matches:
        raise V0P6ContractError(
            "receiver-alias certificate lacks a live or trusted receipt"
        )
    for name in (
        "on_retention_certificate_sha256",
        "on_factor_matrix_sha256",
        "off_match_certificate_sha256",
        "single_adjacent_off_certificate_sha256",
        "input_off_annotated_records_sha256",
        "single_adjacent_off_evidence_sha256",
        "receiver_signature_product_sha256",
        "alias_identity_partition_sha256",
        "annotated_records_sha256",
    ):
        _frozen_sha256(cert[name], name.replace("_", "-"))
    if "receiver_signature_certificate_sha256" in cert:
        _frozen_sha256(
            cert["receiver_signature_certificate_sha256"],
            "receiver-signature certificate identity",
        )
    if (
        cert["contract"]
        != (
            "cross-component stationary receiver peaks in at least two "
            "common active ON epochs"
        )
        or cert["identity_partition_contract"]
        != (
            "connected components of unique (template_index, proxy_carrier_index) "
            "under literal maximum ON-time track distance"
        )
        or cert["track_comparison"]
        != "max_i(abs(q * F_v_i - r * F_w_i)) <= tolerance_hz"
        or cert["local_peak_snr_comparison"]
        != "peak_snr >= local_peak_snr_floor"
        or cert["peak_separation_comparison"]
        != "abs(delta_hz) <= track_tolerance_hz"
        or cert["alias_identity_anchor_pruning_roundoff_guard"]
        != "4 * spacing(max(abs(left_anchor_hz), tolerance_hz, 1.0))"
        or cert["alias_identity_track_comparison_definition"]
        != (
            "candidate node pair surviving first-ON-time anchor pruning before "
            "literal all-ON-time track comparison"
        )
        or cert["candidate_visit_definition"]
        != (
            "cumulative per-window sum of distinct other records reached for "
            "each left record before identity and literal-match rejection"
        )
        or _strict_int(
            cert["bucket_neighbor_cell_radius"], "alias bucket-neighbor radius"
        )
        != _RECEIVER_BUCKET_NEIGHBOR_CELL_RADIUS
    ):
        raise V0P6ContractError("receiver-alias certificate semantics changed")
    window_ordinal = _strict_int(cert["window_ordinal"], "window ordinal")
    integration_count = _strict_int(
        cert["on_integration_count"], "ON integration count"
    )
    minimum_shared = _strict_int(
        cert["minimum_shared_active_epochs"], "minimum shared active epochs"
    )
    track_tolerance = _finite_json_number(
        cert["track_tolerance_hz"], "receiver-alias track tolerance"
    )
    local_half_width = _finite_json_number(
        cert["local_receiver_half_width_hz"],
        "receiver-alias local half width",
    )
    local_snr_floor = _finite_json_number(
        cert["local_peak_snr_floor"], "receiver-alias local peak floor"
    )
    maximum_guard = _finite_json_number(
        cert["maximum_alias_identity_anchor_pruning_roundoff_guard_hz"],
        "receiver-alias maximum anchor-pruning guard",
    )
    if (
        not str(cert["window_id"])
        or window_ordinal < 0
        or integration_count < 1
        or minimum_shared < 2
        or not math.isfinite(track_tolerance)
        or track_tolerance <= 0.0
        or not math.isfinite(local_half_width)
        or local_half_width <= 0.0
        or not math.isfinite(local_snr_floor)
        or not math.isfinite(maximum_guard)
        or maximum_guard < 0.0
    ):
        raise V0P6ContractError("receiver-alias certificate thresholds are invalid")
    count = _strict_int(cert["input_record_count"], "receiver-alias record count")
    maximum_records = _strict_int(
        cert["maximum_records"], "receiver-alias record capacity"
    )
    bucket_entries = _strict_int(cert["bucket_entries"], "alias bucket entries")
    bucket_cap = _strict_int(
        cert["maximum_bucket_entries"], "alias bucket-entry capacity"
    )
    visits = _strict_int(
        cert["maximum_distinct_candidate_visits_observed_per_left"],
        "alias candidate visits",
    )
    visit_cap = _strict_int(
        cert["maximum_distinct_candidate_visits_per_window"],
        "alias candidate-visit capacity",
    )
    total_visits = _strict_int(
        cert["total_distinct_candidate_visits"],
        "total alias candidate visits",
    )
    node_count = _strict_int(cert["alias_identity_node_count"], "alias node count")
    component_count = _strict_int(
        cert["alias_identity_component_count"], "alias component count"
    )
    edge_count = _strict_int(cert["alias_identity_edge_count"], "alias edge count")
    identity_comparisons = _strict_int(
        cert["alias_identity_track_comparisons"],
        "alias identity track comparisons",
    )
    identity_comparison_cap = _strict_int(
        cert["maximum_alias_identity_track_comparisons"],
        "alias identity track-comparison capacity",
    )
    if (
        count < 0
        or maximum_records < 1
        or count != len(detached_records)
        or count > maximum_records
        or bucket_entries < 0
        or bucket_cap < 1
        or bucket_entries > bucket_cap
        or visits < 0
        or visits > max(count - 1, 0)
        or visit_cap < 1
        or total_visits < visits
        or total_visits > visit_cap
        or node_count < 0
        or node_count > count
        or component_count < 0
        or component_count > node_count
        or (node_count == 0) != (component_count == 0)
        or edge_count < 0
        or edge_count > node_count * (node_count - 1) // 2
        or identity_comparisons < edge_count
        or identity_comparison_cap < 1
        or identity_comparisons > identity_comparison_cap
        or identity_comparisons > node_count * (node_count - 1) // 2
        or cert["all_on_records_annotated_exactly_once"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise V0P6IncompleteError("receiver-alias certificate counts are inconsistent")
    if hashlib.sha256(canonical_json_bytes(detached_records)).hexdigest() != cert[
        "annotated_records_sha256"
    ]:
        raise V0P6IncompleteError("receiver-alias annotated records changed")
    seen_ids: set[str] = set()
    observed_disposition_counts = {
        name: 0 for name in sorted(_ALLOWED_FINAL_DISPOSITIONS)
    }
    reconstructed_off_records: list[dict[str, Any]] = []
    adjacent_evidence_records: list[dict[str, Any]] = []
    observed_total_visits = 0
    observed_maximum_visits = 0
    component_by_node: dict[tuple[int, int], tuple[int, str]] = {}
    for record in detached_records:
        record_id = str(record.get("record_id", ""))
        if not record_id or record_id in seen_ids:
            raise V0P6IncompleteError("receiver-alias result repeats a record ID")
        seen_ids.add(record_id)
        evidence = record.get("receiver_alias_evidence")
        if not isinstance(evidence, dict):
            raise V0P6IncompleteError("receiver-alias evidence is missing")
        observed = _frozen_sha256(
            evidence.pop("receiver_alias_evidence_sha256"),
            "receiver-alias evidence identity",
        )
        calculated = hashlib.sha256(canonical_json_bytes(evidence)).hexdigest()
        if observed != calculated:
            raise V0P6IncompleteError("receiver-alias evidence SHA-256 changed")
        evidence["receiver_alias_evidence_sha256"] = observed
        adjacent_evidence = record.get("single_adjacent_off_evidence")
        if not isinstance(adjacent_evidence, dict):
            raise V0P6IncompleteError(
                "single-adjacent-OFF evidence is missing from alias result"
            )
        adjacent_evidence_records.append(adjacent_evidence)
        evidence_required = {
            "alias_identity_component_ordinal",
            "alias_identity_component_sha256",
            "receiver_signature_sha256",
            "qualified_signature_epoch_count",
            "distinct_candidate_visits_before_rejection",
            "matched_cross_component_record_count",
            "matched",
            "best_receiver_alias_witness",
            "receiver_alias_evidence_sha256",
        }
        if set(evidence) != evidence_required:
            raise V0P6ContractError("receiver-alias evidence schema changed")
        component_ordinal = _strict_int(
            evidence["alias_identity_component_ordinal"],
            "alias component ordinal",
        )
        _frozen_sha256(
            evidence["alias_identity_component_sha256"],
            "alias component identity",
        )
        _frozen_sha256(
            evidence["receiver_signature_sha256"],
            "receiver signature identity",
        )
        qualified_count = _strict_int(
            evidence["qualified_signature_epoch_count"],
            "qualified signature epoch count",
        )
        record_visits = _strict_int(
            evidence["distinct_candidate_visits_before_rejection"],
            "record candidate visits",
        )
        match_count = _strict_int(
            evidence["matched_cross_component_record_count"],
            "cross-component alias match count",
        )
        matched = evidence["matched"]
        witness = evidence["best_receiver_alias_witness"]
        if (
            component_ordinal < 0
            or component_ordinal >= component_count
            or qualified_count < 0
            or record_visits < 0
            or record_visits > max(count - 1, 0)
            or match_count < 0
            or not isinstance(matched, bool)
            or matched != (match_count > 0)
            or matched != (witness is not None)
        ):
            raise V0P6ContractError("receiver-alias evidence counts are invalid")
        observed_total_visits += record_visits
        observed_maximum_visits = max(observed_maximum_visits, record_visits)
        node_key = (
            _strict_int(record["template_index"], "template index"),
            _strict_int(record["proxy_carrier_index"], "proxy-carrier index"),
        )
        component_identity = (
            component_ordinal,
            str(evidence["alias_identity_component_sha256"]),
        )
        prior_component_identity = component_by_node.get(node_key)
        if prior_component_identity is not None and (
            prior_component_identity != component_identity
        ):
            raise V0P6ContractError(
                "width/subset records disagree on alias identity"
            )
        component_by_node[node_key] = component_identity
        if witness is not None:
            if not isinstance(witness, dict):
                raise V0P6ContractError("receiver-alias witness is malformed")
            witness_component = _frozen_sha256(
                witness["alias_identity_component_sha256"],
                "witness alias component identity",
            )
            if (
                str(witness.get("record_id", "")) == record_id
                or witness_component == evidence["alias_identity_component_sha256"]
            ):
                raise V0P6ContractError("receiver-alias witness is not cross-component")
            matched_epochs = witness.get("matched_active_epochs")
            if not isinstance(matched_epochs, list) or len(matched_epochs) < minimum_shared:
                raise V0P6ContractError("receiver-alias witness has too few epochs")
            seen_epochs: set[int] = set()
            for item in matched_epochs:
                if not isinstance(item, dict):
                    raise V0P6ContractError("receiver-alias epoch evidence is malformed")
                epoch = _strict_int(item["epoch_zero_based"], "matched epoch")
                delta_hz = _finite_json_number(
                    item["delta_hz"], "receiver-alias witness separation"
                )
                left_peak_snr = _finite_json_number(
                    item["left_peak_snr"], "receiver-alias left peak S/N"
                )
                right_peak_snr = _finite_json_number(
                    item["right_peak_snr"], "receiver-alias right peak S/N"
                )
                if (
                    epoch in seen_epochs
                    or not all(
                        math.isfinite(value)
                        for value in (delta_hz, left_peak_snr, right_peak_snr)
                    )
                    or abs(delta_hz) > track_tolerance
                    or left_peak_snr < local_snr_floor
                    or right_peak_snr < local_snr_floor
                ):
                    raise V0P6ContractError(
                        "receiver-alias matched-epoch evidence is invalid"
                    )
                seen_epochs.add(epoch)
        off_evidence = record.get("off_track_evidence")
        if not isinstance(off_evidence, dict):
            raise V0P6IncompleteError("OFF-track evidence is missing from alias result")
        try:
            same_off = off_evidence["same_hypothesis"]["matched"]
            local_off = off_evidence["local_track"]["matched"]
        except (KeyError, TypeError) as error:
            raise V0P6ContractError("OFF-track evidence is malformed") from error
        if not isinstance(same_off, bool) or not isinstance(local_off, bool):
            raise V0P6ContractError("OFF-track match flags are not boolean")
        off_disposition = (
            "rfi_veto_matched_off_same_hypothesis"
            if same_off
            else (
                "rfi_veto_local_off_track"
                if local_off
                else "pending_receiver_alias_evaluation"
            )
        )
        reconstructed = _detached_json(record, "receiver-alias result record")
        reconstructed.pop("receiver_alias_evidence")
        reconstructed.pop("single_adjacent_off_evidence")
        reconstructed["member_disposition"] = off_disposition
        reconstructed_off_records.append(reconstructed)

        adjacent_vetoed = adjacent_evidence.get("vetoed")
        adjacent_recommendation = adjacent_evidence.get(
            "recommended_member_disposition"
        )
        if not isinstance(adjacent_vetoed, bool) or adjacent_recommendation != (
            "rfi_veto_single_adjacent_off"
            if adjacent_vetoed
            else "pending_receiver_alias_evaluation"
        ):
            raise V0P6ContractError(
                "single-adjacent-OFF disposition evidence is inconsistent"
            )
        expected_disposition = off_disposition
        if off_disposition == "pending_receiver_alias_evaluation":
            if adjacent_vetoed:
                expected_disposition = "rfi_veto_single_adjacent_off"
            elif matched:
                expected_disposition = "rfi_veto_receiver_frame_alias"
        disposition = record.get("member_disposition")
        if disposition not in observed_disposition_counts:
            raise V0P6ContractError("receiver-alias result disposition is invalid")
        if disposition != expected_disposition:
            raise V0P6ContractError(
                "receiver-alias result violates OFF/adjacent/alias precedence"
            )
        observed_disposition_counts[disposition] += 1
    reconstructed_off_records.sort(key=_retention_record_sort_key)
    if hashlib.sha256(canonical_json_bytes(reconstructed_off_records)).hexdigest() != (
        cert["input_off_annotated_records_sha256"]
    ):
        raise V0P6IncompleteError(
            "prior OFF disposition or evidence changed under its receipt"
        )
    if hashlib.sha256(canonical_json_bytes(adjacent_evidence_records)).hexdigest() != (
        cert["single_adjacent_off_evidence_sha256"]
    ):
        raise V0P6IncompleteError(
            "single-adjacent-OFF evidence changed under its receipt"
        )
    if (
        observed_total_visits != total_visits
        or observed_maximum_visits != visits
        or len(component_by_node) != node_count
    ):
        raise V0P6IncompleteError(
            "receiver-alias visit or identity inventory changed"
        )
    members_by_component: dict[tuple[int, str], list[tuple[int, int]]] = (
        defaultdict(list)
    )
    for node, component_identity in component_by_node.items():
        members_by_component[component_identity].append(node)
    if len(members_by_component) != component_count or {
        ordinal for ordinal, _ in members_by_component
    } != set(range(component_count)):
        raise V0P6IncompleteError(
            "receiver-alias component ordinals are incomplete"
        )
    reconstructed_partition: list[dict[str, Any]] = []
    for (ordinal, component_sha), members in sorted(members_by_component.items()):
        members.sort()
        if component_sha != hashlib.sha256(
            canonical_json_bytes(
                [[template, proxy] for template, proxy in members]
            )
        ).hexdigest():
            raise V0P6IncompleteError(
                "receiver-alias component identity does not reproduce"
            )
        reconstructed_partition.append(
            {
                "component_ordinal": ordinal,
                "component_sha256": component_sha,
                "members": [
                    {"template_index": template, "proxy_carrier_index": proxy}
                    for template, proxy in members
                ],
            }
        )
    if hashlib.sha256(
        canonical_json_bytes(reconstructed_partition)
    ).hexdigest() != cert["alias_identity_partition_sha256"]:
        raise V0P6IncompleteError(
            "receiver-alias identity partition changed under its receipt"
        )
    if cert["disposition_counts"] != observed_disposition_counts:
        raise V0P6IncompleteError("receiver-alias disposition counts changed")
    return cert


def match_m37_receiver_frame_aliases(
    records: Sequence[Mapping[str, Any]],
    on_retention_certificate: Mapping[str, Any],
    factor_basis: FactorBasis,
    factor_table: TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    receiver_signature_result: Mapping[str, Any],
    *,
    off_match_certificate: Mapping[str, Any],
    single_adjacent_off_evidence: Sequence[Mapping[str, Any]],
    single_adjacent_off_certificate: Mapping[str, Any],
    expected_off_match_certificate_sha256: str,
    expected_single_adjacent_off_certificate_sha256: str,
    expected_receiver_signature_certificate_sha256: str,
    expected_on_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Apply the frozen non-configurable M37 receiver-frame alias stage."""
    from .receiver_v0p6 import validate_receiver_signature_result

    validated_receiver_result = validate_receiver_signature_result(
        receiver_signature_result,
        expected_certificate_sha256=(
            expected_receiver_signature_certificate_sha256
        ),
    )
    receiver_signatures = validated_receiver_result["receiver_signatures"]
    receiver_certificate = validated_receiver_result["certificate"]
    validate_factor_basis(factor_basis)
    cert = validate_retention_certificate(
        on_retention_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    window_id = str(cert["window_id"])
    if window_id not in M37_WINDOW_IDS:
        raise V0P6ContractError("M37 alias matcher received an unknown window")
    expected_hypotheses = (
        M37_TEMPLATE_COUNT * len(M37_SPECTRAL_WIDTHS) * len(M37_ACTIVITY_SUBSETS)
    )
    expected_score_cells = expected_hypotheses * (2 * M37_SCORE_HALF_BINS + 1)
    if (
        cert["scan_kind"] != "on"
        or cert["proxy_grid_sha256"]
        != proxy_carrier_grid_sha256(make_m37_proxy_carrier_grid(window_id))
        or cert["experiment_contract_sha256"] != M37_EXPERIMENT_CONTRACT_SHA256
        or cert["template_bank_sha256"] != M37_BANK_SHA256
        or cert["factor_basis_sha256"] != M37_FACTOR_BASIS_SHA256
        or cert["factor_basis_labels_sha256"]
        != M37_FACTOR_BASIS_LABELS_SHA256
        or cert["scan_inventory_sha256"] != M37_SCAN_INVENTORY_SHA256
        or cert["factor_row_selection_sha256"]
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or tuple(cert["spectral_widths"]) != M37_SPECTRAL_WIDTHS
        or tuple(tuple(item) for item in cert["activity_subsets"])
        != M37_ACTIVITY_SUBSETS
        or cert["epoch_count"] != 3
        or cert["minimum_active_epoch_snr"] != M37_MINIMUM_ACTIVE_EPOCH_SNR
        or cert["stack_statistic"] != "minimum_epoch"
        or cert["require_epoch_vector_product"] is not True
        or cert["require_mask_product"] is not True
        or cert["maximum_records"] != M37_MAXIMUM_RECORDS_PER_WINDOW
        or cert["maximum_record_canonical_bytes"]
        != M37_MAXIMUM_RECORD_CANONICAL_BYTES
        or cert["maximum_evidence_canonical_bytes"]
        != M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        or cert["expected_hypotheses"] != expected_hypotheses
        or cert["expected_score_cells"] != expected_score_cells
    ):
        raise V0P6ContractError(
            "retention certificate violates the M37 receiver-alias contract"
        )
    bank = make_line_template_bank()
    validate_template_factor_table(
        factor_table,
        factor_basis,
        bank,
        expected_template_bank_sha256=M37_BANK_SHA256,
    )
    if (
        factor_basis.basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_basis.labels_sha256 != M37_FACTOR_BASIS_LABELS_SHA256
        or factor_table.factor_basis_sha256 != M37_FACTOR_BASIS_SHA256
        or factor_table.template_bank_sha256 != M37_BANK_SHA256
        or cert["factor_table_sha256"] != factor_table.factor_table_sha256
    ):
        raise V0P6ContractError("alias matcher did not receive the sealed M37 factors")
    validate_m37_factor_basis_scan_inventory(factor_basis, scan_definitions)
    factors = factor_matrix_for_kind(
        factor_table, factor_basis, scan_definitions, "on"
    )
    if factors.shape != (M37_TEMPLATE_COUNT, 48):
        raise V0P6ContractError("M37 ON factor matrix must have shape [93, 48]")
    receiver_certificate_sha = _frozen_sha256(
        receiver_certificate["receiver_signature_certificate_sha256"],
        "receiver-signature certificate identity",
    )
    if (
        receiver_certificate_sha
        != _frozen_sha256(
            expected_receiver_signature_certificate_sha256,
            "expected receiver-signature certificate identity",
        )
        or receiver_certificate["window_id"] != window_id
        or receiver_certificate["on_retention_certificate_sha256"]
        != cert["retention_certificate_sha256"]
        or receiver_certificate["on_records_sha256"] != cert["records_sha256"]
        or receiver_certificate["proxy_grid_sha256"]
        != cert["proxy_grid_sha256"]
        or receiver_certificate["template_bank_sha256"] != M37_BANK_SHA256
        or receiver_certificate["template_count"] != M37_TEMPLATE_COUNT
        or receiver_certificate["factor_basis_sha256"]
        != M37_FACTOR_BASIS_SHA256
        or receiver_certificate["factor_basis_labels_sha256"]
        != M37_FACTOR_BASIS_LABELS_SHA256
        or receiver_certificate["scan_inventory_sha256"]
        != M37_SCAN_INVENTORY_SHA256
        or receiver_certificate["on_factor_row_selection_sha256"]
        != M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or receiver_certificate["factor_table_sha256"]
        != factor_table.factor_table_sha256
        or tuple(receiver_certificate["spectral_widths"])
        != M37_SPECTRAL_WIDTHS
        or receiver_certificate["epoch_count"] != 3
        or receiver_certificate["local_receiver_half_width_hz"]
        != M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        or receiver_certificate["local_peak_snr_floor"]
        != M37_RECEIVER_PEAK_SNR_FLOOR
    ):
        raise V0P6ContractError(
            "receiver-signature receipt violates the M37 alias contract"
        )
    return match_receiver_frame_aliases(
        records,
        on_retention_certificate,
        make_m37_proxy_carrier_grid(window_id),
        factors,
        receiver_signatures,
        off_match_certificate=off_match_certificate,
        single_adjacent_off_evidence=single_adjacent_off_evidence,
        single_adjacent_off_certificate=single_adjacent_off_certificate,
        expected_off_match_certificate_sha256=(
            expected_off_match_certificate_sha256
        ),
        expected_single_adjacent_off_certificate_sha256=(
            expected_single_adjacent_off_certificate_sha256
        ),
        window_order=M37_WINDOW_IDS,
        track_tolerance_hz=M37_ALIAS_TRACK_TOLERANCE_HZ,
        local_half_width_hz=M37_RECEIVER_LOCAL_HALF_WIDTH_HZ,
        local_peak_snr_floor=M37_RECEIVER_PEAK_SNR_FLOOR,
        minimum_shared_active_epochs=M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS,
        maximum_records=M37_MAXIMUM_RECORDS_PER_WINDOW,
        maximum_bucket_entries=M37_MAXIMUM_ALIAS_BUCKET_ENTRIES,
        maximum_identity_track_comparisons=(
            M37_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        ),
        maximum_distinct_candidate_visits_per_window=(
            M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
        ),
        template_bank=bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        receiver_signature_certificate_sha256=receiver_certificate_sha,
        expected_receiver_signature_product_sha256=(
            receiver_certificate["receiver_signature_product_sha256"]
        ),
    )
