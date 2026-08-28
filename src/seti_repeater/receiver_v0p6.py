"""Provenance-bound receiver-frame signatures for detector v0.6.

The receiver-alias classifier consumes one stationary-peak signature for each
active epoch of every retained ON record.  This module is the production
factory for those signatures: callers provide the exact sealed native-filter
caches used by retention, never arbitrary peak values.

For a retained ``(q, template, width)`` member and one ON scan, the predicted
receiver midpoint is the left-to-right float64 mean of ``q * factor_i``.  All
native receiver channels whose *literal stored-MHz* offset is inclusively
within the local window are evaluated.  Their already-boxcar-filtered values
are accumulated across integrations in ascending order in float32 and divided
by ``float32(sqrt(N))``.  The largest value wins, with the lowest receiver
frequency (and therefore the lowest native index) breaking exact ties.

Importing this module does not open telescope files.  Both in-memory caches
and already-validated read-only disk-cache handles are accepted.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


RECEIVER_SIGNATURE_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_receiver_frame_signatures"
)
RECEIVER_SIGNATURE_SCHEMA_VERSION = 1
M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ = 100.0
M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR = 5.5
M37_MAXIMUM_RECEIVER_SIGNATURE_QUERIES = (
    3 * core.M37_MAXIMUM_RECORDS_PER_WINDOW
)
M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS = (
    core.M37_MAXIMUM_ALIAS_NEIGHBOR_VISITS
)

_PREDICTED_MIDPOINT_CONTRACT = (
    "left-to-right float64 sum(proxy_carrier_hz * factor_i) / integration_count"
)
_LOCAL_WINDOW_COMPARISON = (
    "abs((native_frequency_mhz - predicted_mid_mhz) * 1e6) "
    "<= local_receiver_half_width_hz"
)
_PEAK_STATISTIC_CONTRACT = (
    "ascending-integration float32 sum of native-boxcar cache values / "
    "float32(sqrt(integration_count))"
)
_TIE_BREAK_CONTRACT = (
    "maximum peak_snr then lowest native frequency then lowest raw channel index"
)
_SIGNATURE_SORT_ORDER = "record_id ascending; epoch_zero_based ascending"
_CACHE_SORT_ORDER = (
    "spectral_width_index ascending; epoch_zero_based ascending"
)

_RESULT_ATTESTATIONS: dict[str, bytes] = {}
_RESULT_ATTESTATION_CAP = 1_024

_SIGNATURE_ENTRY_FIELDS = frozenset(
    {
        "epoch_zero_based",
        "predicted_mid_mhz",
        "peak_frequency_mhz",
        "peak_snr",
        "offset_from_prediction_hz",
    }
)

_CACHE_INVENTORY_FIELDS = frozenset(
    {
        "spectral_width_index",
        "spectral_width_channels",
        "epoch_zero_based",
        "scan_label",
        "source_sha256",
        "cache_plan_sha256",
        "cache_payload_sha256",
        "integration_count",
        "raw_zero_hz",
        "native_channel_width_hz",
        "native_channel_count",
        "raw_center_start",
        "raw_center_stop",
    }
)

_CERTIFICATE_PAYLOAD_FIELDS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "window_id",
        "source_scan_kind",
        "signature_sort_order",
        "cache_inventory_sort_order",
        "filter_coordinate",
        "predicted_midpoint_contract",
        "local_window_comparison",
        "local_receiver_half_width_hz",
        "peak_statistic_contract",
        "native_accumulator_dtype",
        "tie_break_contract",
        "downstream_peak_snr_comparison",
        "local_peak_snr_floor",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "template_count",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "factor_table_sha256",
        "spectral_widths",
        "on_scan_labels",
        "epoch_count",
        "cache_inventory",
        "cache_inventory_sha256",
        "cache_provenance_inventory_sha256",
        "cache_count",
        "query_inventory_sha256",
        "query_count",
        "maximum_queries",
        "local_channel_visit_definition",
        "local_channel_visits",
        "minimum_local_channels_per_query",
        "maximum_local_channels_per_query",
        "maximum_local_channel_visits",
        "input_record_count",
        "signature_record_count",
        "maximum_records",
        "maximum_signature_record_canonical_bytes",
        "maximum_evidence_canonical_bytes",
        "receiver_signature_product_canonical_bytes",
        "receiver_signature_product_sha256",
        "receiver_signatures_mapping_canonical_bytes",
        "receiver_signatures_mapping_sha256",
        "all_input_records_signed_exactly_once",
        "all_active_epoch_queries_evaluated_exactly_once",
        "complete_width_by_on_scan_cache_inventory",
        "truncation_permitted",
    }
)
_CERTIFICATE_FIELDS = _CERTIFICATE_PAYLOAD_FIELDS | {
    "receiver_signature_certificate_sha256"
}
_RESULT_FIELDS = frozenset(
    {"receiver_signatures", "certificate", "result_sha256"}
)


def _canonical_mapping(value: Any, label: str) -> dict[str, Any]:
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


def _finite_json_number(value: Any, label: str) -> float:
    """Require a JSON numeric scalar without accepting bools or strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    return converted


def _inventory_items(value: Any, label: str) -> list[tuple[Any, Any]]:
    if isinstance(value, Mapping):
        return list(value.items())
    if isinstance(value, (str, bytes)):
        raise core.V0P6ContractError(f"{label} must be a mapping or pair sequence")
    try:
        raw_items = list(value)
    except TypeError as error:
        raise core.V0P6ContractError(
            f"{label} must be a mapping or pair sequence"
        ) from error
    items: list[tuple[Any, Any]] = []
    for item in raw_items:
        if isinstance(item, (str, bytes)):
            raise core.V0P6ContractError(f"{label} entry must be a pair")
        try:
            pair = tuple(item)
        except TypeError as error:
            raise core.V0P6ContractError(
                f"{label} entry must be a pair"
            ) from error
        if len(pair) != 2:
            raise core.V0P6ContractError(f"{label} entry must be a pair")
        items.append((pair[0], pair[1]))
    return items


def _normalise_cache_inventory(
    caches_by_width: Any,
    widths: tuple[int, ...],
    on_labels: tuple[str, ...],
) -> dict[int, dict[str, Any]]:
    normalised: dict[int, dict[str, Any]] = {}
    for raw_width, raw_scans in _inventory_items(
        caches_by_width, "receiver-signature cache inventory"
    ):
        width = core._strict_int(raw_width, "cache spectral width")
        if width in normalised:
            raise core.V0P6IncompleteError(
                "receiver-signature cache inventory repeats a width"
            )
        scans: dict[str, Any] = {}
        for raw_label, cache in _inventory_items(
            raw_scans, "receiver-signature scan-cache inventory"
        ):
            if not isinstance(raw_label, str) or not raw_label:
                raise core.V0P6ContractError(
                    "receiver-signature cache label must be a non-empty string"
                )
            if raw_label in scans:
                raise core.V0P6IncompleteError(
                    "receiver-signature cache inventory repeats a scan label"
                )
            scans[raw_label] = cache
        normalised[width] = scans
    if set(normalised) != set(widths):
        raise core.V0P6IncompleteError(
            "receiver-signature cache width inventory is incomplete or has extras"
        )
    expected_labels = set(on_labels)
    for width in widths:
        if set(normalised[width]) != expected_labels:
            raise core.V0P6IncompleteError(
                "receiver-signature ON scan-cache inventory is incomplete or has extras"
            )
    return normalised


def _validate_inputs(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    template_bank: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str | None,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    tuple[int, ...],
    tuple[Mapping[str, Any], ...],
    tuple[str, ...],
    tuple[np.ndarray, ...],
]:
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if cert["scan_kind"] != "on":
        raise core.V0P6ContractError(
            "receiver signatures require an ON retention product"
        )
    if cert["require_epoch_vector_product"] is not True:
        raise core.V0P6ContractError(
            "receiver signatures require cache-provenance-bound retention"
        )
    core.validate_factor_basis(factor_basis)
    core.validate_factor_basis_scan_inventory(factor_basis, scan_definitions)
    core.validate_template_factor_table(
        factor_table,
        factor_basis,
        template_bank,
        expected_template_bank_sha256=cert["template_bank_sha256"],
    )
    scan_digest = core.scan_inventory_sha256(scan_definitions)
    if (
        core.proxy_carrier_grid_sha256(grid) != cert["proxy_grid_sha256"]
        or factor_basis.basis_sha256 != cert["factor_basis_sha256"]
        or factor_basis.labels_sha256
        != cert["factor_basis_labels_sha256"]
        or scan_digest != cert["scan_inventory_sha256"]
        or core.factor_row_selection_sha256(
            factor_basis, scan_definitions, "on"
        )
        != cert["factor_row_selection_sha256"]
        or factor_table.factor_table_sha256 != cert["factor_table_sha256"]
        or factor_table.template_bank_sha256 != cert["template_bank_sha256"]
    ):
        raise core.V0P6ContractError(
            "retention and receiver-signature factor contracts differ"
        )
    template_count = int(factor_table.factors.shape[0])
    records = core._validated_retained_records(
        on_records,
        cert,
        grid,
        expected_kind="on",
        expected_template_count=template_count,
        template_bank=template_bank,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    widths = tuple(core._strict_widths(cert["spectral_widths"]))
    on_indices = core.m37_scan_indices_for_kind(scan_definitions, "on")
    definitions = tuple(scan_definitions[index] for index in on_indices)
    labels = tuple(str(item["label"]) for item in definitions)
    scan_tables = tuple(
        core.factor_table_for_scan(factor_table, factor_basis, label)
        for label in labels
    )
    if len(definitions) != core._strict_int(
        cert["epoch_count"], "retention epoch count"
    ):
        raise core.V0P6ContractError(
            "receiver-signature ON scans do not match the retention epochs"
        )
    return cert, records, widths, definitions, labels, scan_tables


def _validate_caches(
    raw_caches: Any,
    widths: tuple[int, ...],
    definitions: tuple[Mapping[str, Any], ...],
    labels: tuple[str, ...],
    scan_tables: tuple[np.ndarray, ...],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    cert: Mapping[str, Any],
) -> tuple[
    dict[int, dict[str, Any]],
    dict[tuple[int, str], np.ndarray],
    list[dict[str, Any]],
]:
    caches = _normalise_cache_inventory(raw_caches, widths, labels)
    values_by_key: dict[tuple[int, str], np.ndarray] = {}
    inventory: list[dict[str, Any]] = []
    provenance: dict[int, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    grid_digest = core.proxy_carrier_grid_sha256(grid)
    scan_digest = core.scan_inventory_sha256(scan_definitions)
    for width_index, width in enumerate(widths):
        plan_digests: list[str] = []
        payload_digests: list[str] = []
        for epoch, (definition, label, scan_table) in enumerate(
            zip(definitions, labels, scan_tables, strict=True)
        ):
            cache = caches[width][label]
            plan, values = core._cache_values_for_gather(cache)
            expected_count = core._strict_int(
                definition["expected_header"]["dataset_shape"][0],
                "integration count",
            )
            expected_factor_row_digests = tuple(
                core.float64_vector_sha256(row) for row in scan_table
            )
            if (
                plan.window_id != str(cert["window_id"])
                or plan.scan_label != label
                or plan.scan_kind != "on"
                or plan.width_channels != width
                or plan.integration_count != expected_count
                or plan.proxy_grid_sha256 != grid_digest
                or plan.factor_basis_sha256 != factor_basis.basis_sha256
                or plan.factor_basis_labels_sha256
                != factor_basis.labels_sha256
                or plan.scan_inventory_sha256 != scan_digest
                or plan.factor_scan_selection_sha256
                != core.factor_scan_selection_sha256(
                    factor_basis, scan_definitions, label
                )
                or plan.template_bank_sha256
                != factor_table.template_bank_sha256
                or plan.factor_table_sha256
                != core.factor_table_sha256(scan_table)
                or tuple(plan.factor_row_sha256s)
                != expected_factor_row_digests
            ):
                raise core.V0P6ContractError(
                    "receiver-signature cache identity differs from retention"
                )
            payload_digest = core._frozen_sha256(
                cache.payload_sha256, "receiver-signature cache payload"
            )
            values_by_key[(width, label)] = values
            plan_digests.append(plan.plan_sha256)
            payload_digests.append(payload_digest)
            inventory.append(
                {
                    "spectral_width_index": width_index,
                    "spectral_width_channels": width,
                    "epoch_zero_based": epoch,
                    "scan_label": label,
                    "source_sha256": plan.source_sha256,
                    "cache_plan_sha256": plan.plan_sha256,
                    "cache_payload_sha256": payload_digest,
                    "integration_count": plan.integration_count,
                    "raw_zero_hz": float(plan.geometry.raw_zero_hz),
                    "native_channel_width_hz": float(
                        plan.geometry.channel_width_hz
                    ),
                    "native_channel_count": plan.geometry.channel_count,
                    "raw_center_start": plan.raw_center_start,
                    "raw_center_stop": plan.raw_center_stop,
                }
            )
        provenance[width_index] = (
            tuple(plan_digests),
            tuple(payload_digests),
        )
    observed_provenance = core._cache_provenance_inventory_sha256(provenance)
    if observed_provenance != cert["cache_provenance_inventory_sha256"]:
        raise core.V0P6IncompleteError(
            "receiver-signature cache provenance differs from retention"
        )
    return caches, values_by_key, inventory


def _predicted_midpoint_hz(q_hz: float, factors: np.ndarray) -> float:
    total = 0.0
    for factor in factors:
        total += q_hz * float(factor)
    midpoint = total / factors.size
    if not math.isfinite(midpoint):
        raise core.V0P6ContractError(
            "receiver predicted midpoint is non-finite"
        )
    return midpoint


def _local_raw_indices(
    plan: core.NativeFilterCachePlan,
    predicted_mid_mhz: float,
    local_half_width_hz: float,
) -> tuple[np.ndarray, np.ndarray]:
    geometry = plan.geometry
    predicted_hz = predicted_mid_mhz * 1e6
    # The two-channel margin makes the arithmetic bounding interval strictly
    # wider than the literal comparison, including exact boundary channels.
    raw_lower = math.floor(
        (predicted_hz - local_half_width_hz - geometry.raw_zero_hz)
        / geometry.channel_width_hz
    ) - 2
    raw_upper = math.ceil(
        (predicted_hz + local_half_width_hz - geometry.raw_zero_hz)
        / geometry.channel_width_hz
    ) + 2
    start = max(0, raw_lower)
    stop = min(geometry.channel_count, raw_upper + 1)
    candidates = np.arange(start, stop, dtype=np.int64)
    frequencies_mhz = np.asarray(
        (
            geometry.raw_zero_hz
            + candidates.astype(np.float64) * geometry.channel_width_hz
        )
        / 1e6,
        dtype=np.float64,
    )
    offsets_hz = np.asarray(
        (frequencies_mhz - predicted_mid_mhz) * 1e6,
        dtype=np.float64,
    )
    selected = np.abs(offsets_hz) <= local_half_width_hz
    raw_indices = candidates[selected]
    selected_frequencies = frequencies_mhz[selected]
    if raw_indices.size < 1:
        raise core.V0P6CoverageError(
            "receiver local window contains no native channel"
        )
    if (
        int(raw_indices[0]) < plan.raw_center_start
        or int(raw_indices[-1]) >= plan.raw_center_stop
    ):
        raise core.V0P6CoverageError(
            "native filter cache does not cover the complete receiver local window"
        )
    return raw_indices, selected_frequencies


def _measure_peak(
    values: np.ndarray,
    plan: core.NativeFilterCachePlan,
    raw_indices: np.ndarray,
) -> tuple[int, np.float32]:
    positions = raw_indices - plan.raw_center_start
    accumulator = np.zeros(raw_indices.size, dtype=np.dtype("<f4"))
    for integration_index in range(plan.integration_count):
        np.add(
            accumulator,
            values[integration_index, positions],
            out=accumulator,
        )
    np.divide(
        accumulator,
        np.float32(math.sqrt(plan.integration_count)),
        out=accumulator,
    )
    if not np.all(np.isfinite(accumulator)):
        raise core.V0P6IncompleteError(
            "receiver local peak statistic is non-finite"
        )
    # raw_indices and the native frequencies are strictly ascending, so the
    # first maximum implements both frozen tie breakers.
    winner = int(np.argmax(accumulator))
    return winner, np.float32(accumulator[winner])


def _derive_receiver_signatures(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_caches_by_width: Any,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    local_half_width_hz: float,
    local_peak_snr_floor: float,
    maximum_records: int,
    maximum_queries: int,
    maximum_local_channel_visits: int,
    maximum_signature_record_canonical_bytes: int,
    maximum_evidence_canonical_bytes: int,
    expected_on_certificate_sha256: str | None,
) -> dict[str, Any]:
    maximum_records = core._strict_int(
        maximum_records, "receiver-signature record capacity"
    )
    maximum_queries = core._strict_int(
        maximum_queries, "receiver-signature query capacity"
    )
    maximum_local_channel_visits = core._strict_int(
        maximum_local_channel_visits,
        "receiver-signature local-channel-visit capacity",
    )
    maximum_signature_record_canonical_bytes = core._strict_int(
        maximum_signature_record_canonical_bytes,
        "receiver-signature per-record byte capacity",
    )
    maximum_evidence_canonical_bytes = core._strict_int(
        maximum_evidence_canonical_bytes,
        "receiver-signature evidence-byte capacity",
    )
    if (
        maximum_records < 0
        or maximum_queries < 0
        or maximum_local_channel_visits < 0
        or maximum_signature_record_canonical_bytes < 1
        or maximum_evidence_canonical_bytes < 1
    ):
        raise core.V0P6ContractError(
            "receiver-signature capacities are invalid"
        )
    local_half_width_hz = float(local_half_width_hz)
    local_peak_snr_floor = float(local_peak_snr_floor)
    if (
        not math.isfinite(local_half_width_hz)
        or local_half_width_hz <= 0.0
        or not math.isfinite(local_peak_snr_floor)
    ):
        raise core.V0P6ContractError(
            "receiver-signature thresholds must be finite and valid"
        )

    (
        cert,
        records,
        widths,
        definitions,
        labels,
        scan_tables,
    ) = _validate_inputs(
        on_records,
        on_certificate,
        factor_basis,
        factor_table,
        scan_definitions,
        template_bank,
        grid,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
    )
    if len(records) > maximum_records:
        raise core.V0P6CapacityError(
            "receiver-signature record capacity exceeded"
        )
    caches, values_by_key, cache_inventory = _validate_caches(
        on_caches_by_width,
        widths,
        definitions,
        labels,
        scan_tables,
        scan_definitions,
        factor_basis,
        factor_table,
        grid,
        cert,
    )

    query_count = sum(
        len(
            core.canonical_activity_subsets(
                (record["active_epochs_zero_based"],)
            )[0]
        )
        for record in records
    )
    if query_count > maximum_queries:
        raise core.V0P6CapacityError(
            "receiver-signature query capacity exceeded"
        )

    signatures: dict[str, list[dict[str, Any]]] = {}
    product: list[dict[str, Any]] = []
    query_inventory: list[dict[str, Any]] = []
    total_visits = 0
    minimum_query_visits: int | None = None
    maximum_query_visits = 0
    for record in records:
        record_id = str(record["record_id"])
        if record_id in signatures:
            raise core.V0P6IncompleteError(
                "receiver-signature input repeats a retained record ID"
            )
        width_index = core._strict_int(
            record["spectral_width_index"], "spectral-width index"
        )
        width = widths[width_index]
        template_index = core._strict_int(
            record["template_index"], "template index"
        )
        q_index = core._strict_int(
            record["proxy_carrier_index"], "proxy-carrier index"
        )
        q_hz = float(record["proxy_carrier_hz"])
        active_epochs = core.canonical_activity_subsets(
            (record["active_epochs_zero_based"],)
        )[0]
        entries: list[dict[str, Any]] = []
        for epoch in active_epochs:
            label = labels[epoch]
            cache = caches[width][label]
            plan = cache.plan
            values = values_by_key[(width, label)]
            factors = scan_tables[epoch][template_index]
            if core.float64_vector_sha256(factors) not in plan.factor_row_sha256s:
                raise core.V0P6ContractError(
                    "receiver query factor is absent from its cache plan"
                )
            predicted_mid_hz = _predicted_midpoint_hz(q_hz, factors)
            predicted_mid_mhz = float(predicted_mid_hz / 1e6)
            raw_indices, frequencies_mhz = _local_raw_indices(
                plan, predicted_mid_mhz, local_half_width_hz
            )
            channel_visits = int(raw_indices.size)
            if total_visits + channel_visits > maximum_local_channel_visits:
                raise core.V0P6CapacityError(
                    "receiver-signature local-channel-visit capacity exceeded"
                )
            total_visits += channel_visits
            minimum_query_visits = (
                channel_visits
                if minimum_query_visits is None
                else min(minimum_query_visits, channel_visits)
            )
            maximum_query_visits = max(maximum_query_visits, channel_visits)
            winner, peak_snr = _measure_peak(values, plan, raw_indices)
            peak_frequency_mhz = float(frequencies_mhz[winner])
            literal_offset_hz = float(
                (peak_frequency_mhz - predicted_mid_mhz) * 1e6
            )
            if abs(literal_offset_hz) > local_half_width_hz:
                raise core.V0P6IncompleteError(
                    "selected receiver peak escaped the inclusive local window"
                )
            entries.append(
                {
                    "epoch_zero_based": epoch,
                    "predicted_mid_mhz": predicted_mid_mhz,
                    "peak_frequency_mhz": peak_frequency_mhz,
                    "peak_snr": float(peak_snr),
                    "offset_from_prediction_hz": literal_offset_hz,
                }
            )
            query_inventory.append(
                {
                    "record_id": record_id,
                    "epoch_zero_based": epoch,
                    "scan_label": label,
                    "template_index": template_index,
                    "spectral_width_index": width_index,
                    "spectral_width_channels": width,
                    "proxy_carrier_index": q_index,
                    "proxy_carrier_hz": q_hz,
                    "predicted_mid_mhz": predicted_mid_mhz,
                    "first_local_raw_channel_index": int(raw_indices[0]),
                    "last_local_raw_channel_index": int(raw_indices[-1]),
                    "local_channel_count": channel_visits,
                }
            )
        item = {
            "record_id": record_id,
            "receiver_frame_signature": entries,
        }
        if len(core.canonical_json_bytes(item)) > (
            maximum_signature_record_canonical_bytes
        ):
            raise core.V0P6CapacityError(
                "receiver signature record exceeds its byte capacity"
            )
        signatures[record_id] = entries
        product.append(item)

    product.sort(key=lambda item: item["record_id"])
    signatures = {key: signatures[key] for key in sorted(signatures)}
    product_bytes = core.canonical_json_bytes(product)
    mapping_bytes = core.canonical_json_bytes(signatures)
    if len(product_bytes) > maximum_evidence_canonical_bytes:
        raise core.V0P6CapacityError(
            "receiver signature product exceeds its evidence-byte capacity"
        )
    if len(signatures) != len(records) or len(query_inventory) != query_count:
        raise core.V0P6IncompleteError(
            "receiver-signature replay did not cover every input query"
        )

    cache_inventory_bytes = core.canonical_json_bytes(cache_inventory)
    query_inventory_bytes = core.canonical_json_bytes(query_inventory)
    certificate_payload = {
        "artifact_type": RECEIVER_SIGNATURE_ARTIFACT_TYPE,
        "schema_version": RECEIVER_SIGNATURE_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "window_id": str(cert["window_id"]),
        "source_scan_kind": "on",
        "signature_sort_order": _SIGNATURE_SORT_ORDER,
        "cache_inventory_sort_order": _CACHE_SORT_ORDER,
        "filter_coordinate": core.FILTER_COORDINATE,
        "predicted_midpoint_contract": _PREDICTED_MIDPOINT_CONTRACT,
        "local_window_comparison": _LOCAL_WINDOW_COMPARISON,
        "local_receiver_half_width_hz": local_half_width_hz,
        "peak_statistic_contract": _PEAK_STATISTIC_CONTRACT,
        "native_accumulator_dtype": "<f4",
        "tie_break_contract": _TIE_BREAK_CONTRACT,
        "downstream_peak_snr_comparison": (
            "peak_snr >= local_peak_snr_floor"
        ),
        "local_peak_snr_floor": local_peak_snr_floor,
        "on_retention_certificate_sha256": cert[
            "retention_certificate_sha256"
        ],
        "on_records_sha256": cert["records_sha256"],
        "proxy_grid_sha256": cert["proxy_grid_sha256"],
        "template_bank_sha256": cert["template_bank_sha256"],
        "template_count": int(factor_table.factors.shape[0]),
        "factor_basis_sha256": cert["factor_basis_sha256"],
        "factor_basis_labels_sha256": cert[
            "factor_basis_labels_sha256"
        ],
        "scan_inventory_sha256": cert["scan_inventory_sha256"],
        "on_factor_row_selection_sha256": cert[
            "factor_row_selection_sha256"
        ],
        "factor_table_sha256": cert["factor_table_sha256"],
        "spectral_widths": list(widths),
        "on_scan_labels": list(labels),
        "epoch_count": len(labels),
        "cache_inventory": cache_inventory,
        "cache_inventory_sha256": hashlib.sha256(
            cache_inventory_bytes
        ).hexdigest(),
        "cache_provenance_inventory_sha256": cert[
            "cache_provenance_inventory_sha256"
        ],
        "cache_count": len(cache_inventory),
        "query_inventory_sha256": hashlib.sha256(
            query_inventory_bytes
        ).hexdigest(),
        "query_count": query_count,
        "maximum_queries": maximum_queries,
        "local_channel_visit_definition": (
            "one candidate native receiver channel evaluated for one retained "
            "record active-epoch query"
        ),
        "local_channel_visits": total_visits,
        "minimum_local_channels_per_query": (
            0 if minimum_query_visits is None else minimum_query_visits
        ),
        "maximum_local_channels_per_query": maximum_query_visits,
        "maximum_local_channel_visits": maximum_local_channel_visits,
        "input_record_count": len(records),
        "signature_record_count": len(signatures),
        "maximum_records": maximum_records,
        "maximum_signature_record_canonical_bytes": (
            maximum_signature_record_canonical_bytes
        ),
        "maximum_evidence_canonical_bytes": (
            maximum_evidence_canonical_bytes
        ),
        "receiver_signature_product_canonical_bytes": len(product_bytes),
        "receiver_signature_product_sha256": hashlib.sha256(
            product_bytes
        ).hexdigest(),
        "receiver_signatures_mapping_canonical_bytes": len(mapping_bytes),
        "receiver_signatures_mapping_sha256": hashlib.sha256(
            mapping_bytes
        ).hexdigest(),
        "all_input_records_signed_exactly_once": True,
        "all_active_epoch_queries_evaluated_exactly_once": True,
        "complete_width_by_on_scan_cache_inventory": True,
        "truncation_permitted": False,
    }
    certificate = dict(certificate_payload)
    certificate["receiver_signature_certificate_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(certificate_payload)
    ).hexdigest()
    result_payload = {
        "receiver_signatures": signatures,
        "certificate": certificate,
    }
    result = dict(result_payload)
    result["result_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(result_payload)
    ).hexdigest()
    return json.loads(core.canonical_json_bytes(result))


def build_receiver_frame_signatures(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_caches_by_width: Any,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    local_half_width_hz: float,
    local_peak_snr_floor: float,
    maximum_records: int,
    maximum_queries: int,
    maximum_local_channel_visits: int,
    maximum_signature_record_canonical_bytes: int,
    maximum_evidence_canonical_bytes: int,
    expected_on_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Build and attest the complete receiver-signature result."""
    result = _derive_receiver_signatures(
        on_records,
        on_certificate,
        on_caches_by_width,
        scan_definitions,
        factor_basis,
        factor_table,
        template_bank,
        grid,
        local_half_width_hz=local_half_width_hz,
        local_peak_snr_floor=local_peak_snr_floor,
        maximum_records=maximum_records,
        maximum_queries=maximum_queries,
        maximum_local_channel_visits=maximum_local_channel_visits,
        maximum_signature_record_canonical_bytes=(
            maximum_signature_record_canonical_bytes
        ),
        maximum_evidence_canonical_bytes=maximum_evidence_canonical_bytes,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
    )
    certificate_digest = result["certificate"][
        "receiver_signature_certificate_sha256"
    ]
    encoded = core.canonical_json_bytes(result)
    existing = _RESULT_ATTESTATIONS.get(certificate_digest)
    if existing is not None and existing != encoded:
        raise core.V0P6IncompleteError(
            "receiver-signature certificate digest collision"
        )
    if existing is None and len(_RESULT_ATTESTATIONS) >= _RESULT_ATTESTATION_CAP:
        raise core.V0P6CapacityError(
            "receiver-signature result attestation capacity exceeded"
        )
    _RESULT_ATTESTATIONS[certificate_digest] = encoded
    validate_receiver_signature_result(result)
    return result


def validate_receiver_signature_result(
    result: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a live result or a persisted result with a trusted digest."""
    detached = _canonical_mapping(result, "receiver-signature result")
    if frozenset(detached) != _RESULT_FIELDS:
        raise core.V0P6ContractError(
            "receiver-signature result fields do not match the schema"
        )
    result_digest = core._frozen_sha256(
        detached["result_sha256"], "receiver-signature result identity"
    )
    result_payload = {
        "receiver_signatures": detached["receiver_signatures"],
        "certificate": detached["certificate"],
    }
    if hashlib.sha256(core.canonical_json_bytes(result_payload)).hexdigest() != (
        result_digest
    ):
        raise core.V0P6IncompleteError(
            "receiver-signature result SHA-256 changed"
        )
    signatures = detached["receiver_signatures"]
    certificate = detached["certificate"]
    if not isinstance(signatures, dict) or not isinstance(certificate, dict):
        raise core.V0P6ContractError(
            "receiver-signature result payload types are invalid"
        )
    if frozenset(certificate) != _CERTIFICATE_FIELDS:
        raise core.V0P6ContractError(
            "receiver-signature certificate fields do not match the schema"
        )
    certificate_payload = dict(certificate)
    certificate_digest = core._frozen_sha256(
        certificate_payload.pop("receiver_signature_certificate_sha256"),
        "receiver-signature certificate identity",
    )
    if hashlib.sha256(
        core.canonical_json_bytes(certificate_payload)
    ).hexdigest() != certificate_digest:
        raise core.V0P6IncompleteError(
            "receiver-signature certificate SHA-256 changed"
        )
    expected_digest = (
        None
        if expected_certificate_sha256 is None
        else core._frozen_sha256(
            expected_certificate_sha256,
            "expected receiver-signature certificate identity",
        )
    )
    live_matches = (
        _RESULT_ATTESTATIONS.get(certificate_digest)
        == core.canonical_json_bytes(detached)
    )
    trusted_matches = expected_digest == certificate_digest
    if not live_matches and not trusted_matches:
        raise core.V0P6ContractError(
            "receiver-signature result lacks a live or independently trusted receipt"
        )
    if frozenset(certificate_payload) != _CERTIFICATE_PAYLOAD_FIELDS:
        raise core.V0P6ContractError(
            "receiver-signature certificate payload schema changed"
        )
    if (
        certificate["artifact_type"] != RECEIVER_SIGNATURE_ARTIFACT_TYPE
        or certificate["schema_version"] != RECEIVER_SIGNATURE_SCHEMA_VERSION
        or certificate["detector_version"] != core.DETECTOR_VERSION
        or certificate["source_scan_kind"] != "on"
        or certificate["signature_sort_order"] != _SIGNATURE_SORT_ORDER
        or certificate["cache_inventory_sort_order"] != _CACHE_SORT_ORDER
        or certificate["filter_coordinate"] != core.FILTER_COORDINATE
        or certificate["predicted_midpoint_contract"]
        != _PREDICTED_MIDPOINT_CONTRACT
        or certificate["local_window_comparison"]
        != _LOCAL_WINDOW_COMPARISON
        or certificate["peak_statistic_contract"]
        != _PEAK_STATISTIC_CONTRACT
        or certificate["native_accumulator_dtype"] != "<f4"
        or certificate["tie_break_contract"] != _TIE_BREAK_CONTRACT
        or certificate["downstream_peak_snr_comparison"]
        != "peak_snr >= local_peak_snr_floor"
        or certificate["local_channel_visit_definition"]
        != (
            "one candidate native receiver channel evaluated for one retained "
            "record active-epoch query"
        )
        or certificate["all_input_records_signed_exactly_once"] is not True
        or certificate[
            "all_active_epoch_queries_evaluated_exactly_once"
        ]
        is not True
        or certificate["complete_width_by_on_scan_cache_inventory"] is not True
        or certificate["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "receiver-signature certificate semantics changed"
        )
    if not str(certificate["window_id"]):
        raise core.V0P6ContractError(
            "receiver-signature certificate has no window identity"
        )
    for name in (
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "factor_table_sha256",
        "cache_inventory_sha256",
        "cache_provenance_inventory_sha256",
        "query_inventory_sha256",
        "receiver_signature_product_sha256",
        "receiver_signatures_mapping_sha256",
    ):
        core._frozen_sha256(certificate[name], name.replace("_", "-"))
    local_half_width = _finite_json_number(
        certificate["local_receiver_half_width_hz"],
        "receiver-signature local half width",
    )
    local_peak_floor = _finite_json_number(
        certificate["local_peak_snr_floor"],
        "receiver-signature local peak floor",
    )
    if (
        not math.isfinite(local_half_width)
        or local_half_width <= 0.0
        or not math.isfinite(local_peak_floor)
    ):
        raise core.V0P6ContractError(
            "receiver-signature certificate thresholds are invalid"
        )
    widths = tuple(core._strict_widths(certificate["spectral_widths"]))
    labels = certificate["on_scan_labels"]
    if (
        not isinstance(labels, list)
        or any(not isinstance(item, str) or not item for item in labels)
        or len(labels) != len(set(labels))
    ):
        raise core.V0P6ContractError(
            "receiver-signature ON scan-label inventory is invalid"
        )
    epoch_count = core._strict_int(
        certificate["epoch_count"], "receiver-signature epoch count"
    )
    template_count = core._strict_int(
        certificate["template_count"], "receiver-signature template count"
    )
    if epoch_count != len(labels) or epoch_count < 1 or template_count < 1:
        raise core.V0P6ContractError(
            "receiver-signature dimensions are invalid"
        )

    cache_inventory = certificate["cache_inventory"]
    if not isinstance(cache_inventory, list):
        raise core.V0P6ContractError(
            "receiver-signature cache inventory is not a list"
        )
    expected_cache_keys = [
        (width_index, epoch)
        for width_index in range(len(widths))
        for epoch in range(epoch_count)
    ]
    observed_cache_keys: list[tuple[int, int]] = []
    for item in cache_inventory:
        if not isinstance(item, dict) or frozenset(item) != _CACHE_INVENTORY_FIELDS:
            raise core.V0P6ContractError(
                "receiver-signature cache-inventory schema changed"
            )
        width_index = core._strict_int(
            item["spectral_width_index"], "cache spectral-width index"
        )
        epoch = core._strict_int(
            item["epoch_zero_based"], "cache epoch"
        )
        if (
            not 0 <= width_index < len(widths)
            or core._strict_int(
                item["spectral_width_channels"], "cache spectral width"
            )
            != widths[width_index]
            or not 0 <= epoch < epoch_count
            or item["scan_label"] != labels[epoch]
        ):
            raise core.V0P6ContractError(
                "receiver-signature cache-inventory identity changed"
            )
        for name in (
            "source_sha256",
            "cache_plan_sha256",
            "cache_payload_sha256",
        ):
            core._frozen_sha256(item[name], "cache inventory identity")
        integration_count = core._strict_int(
            item["integration_count"], "cache integration count"
        )
        channel_count = core._strict_int(
            item["native_channel_count"], "native channel count"
        )
        raw_start = core._strict_int(
            item["raw_center_start"], "cache raw start"
        )
        raw_stop = core._strict_int(
            item["raw_center_stop"], "cache raw stop"
        )
        numeric = (
            _finite_json_number(
                item["raw_zero_hz"], "cache raw-zero frequency"
            ),
            _finite_json_number(
                item["native_channel_width_hz"],
                "cache native channel width",
            ),
        )
        if (
            integration_count < 1
            or channel_count < 2
            or raw_start < 0
            or raw_stop <= raw_start
            or raw_stop > channel_count
            or not all(math.isfinite(value) for value in numeric)
            or numeric[1] <= 0.0
        ):
            raise core.V0P6ContractError(
                "receiver-signature cache geometry is invalid"
            )
        observed_cache_keys.append((width_index, epoch))
    if observed_cache_keys != expected_cache_keys:
        raise core.V0P6IncompleteError(
            "receiver-signature cache inventory is incomplete or reordered"
        )
    cache_bytes = core.canonical_json_bytes(cache_inventory)
    if hashlib.sha256(cache_bytes).hexdigest() != certificate[
        "cache_inventory_sha256"
    ]:
        raise core.V0P6IncompleteError(
            "receiver-signature cache inventory SHA-256 changed"
        )

    count = core._strict_int(
        certificate["input_record_count"], "receiver-signature input count"
    )
    signature_count = core._strict_int(
        certificate["signature_record_count"],
        "receiver-signature record count",
    )
    maximum_records = core._strict_int(
        certificate["maximum_records"], "receiver-signature record capacity"
    )
    query_count = core._strict_int(
        certificate["query_count"], "receiver-signature query count"
    )
    maximum_queries = core._strict_int(
        certificate["maximum_queries"], "receiver-signature query capacity"
    )
    visits = core._strict_int(
        certificate["local_channel_visits"], "local-channel visit count"
    )
    minimum_visits = core._strict_int(
        certificate["minimum_local_channels_per_query"],
        "minimum local-channel count",
    )
    maximum_visits_per_query = core._strict_int(
        certificate["maximum_local_channels_per_query"],
        "maximum local-channel count",
    )
    visit_cap = core._strict_int(
        certificate["maximum_local_channel_visits"],
        "local-channel visit capacity",
    )
    cache_count = core._strict_int(
        certificate["cache_count"], "receiver-signature cache count"
    )
    record_byte_cap = core._strict_int(
        certificate["maximum_signature_record_canonical_bytes"],
        "receiver-signature per-record byte capacity",
    )
    evidence_cap = core._strict_int(
        certificate["maximum_evidence_canonical_bytes"],
        "receiver-signature evidence-byte capacity",
    )
    if (
        count < 0
        or signature_count != count
        or count != len(signatures)
        or maximum_records < count
        or maximum_records < 0
        or query_count < 0
        or maximum_queries < query_count
        or maximum_queries < 0
        or visits < 0
        or visit_cap < visits
        or visit_cap < 0
        or minimum_visits < 0
        or maximum_visits_per_query < minimum_visits
        or cache_count != len(cache_inventory)
        or cache_count != len(widths) * epoch_count
        or record_byte_cap < 1
        or evidence_cap < 1
        or (query_count == 0)
        != (minimum_visits == 0 and maximum_visits_per_query == 0)
        or (
            query_count > 0
            and not (
                query_count * minimum_visits
                <= visits
                <= query_count * maximum_visits_per_query
            )
        )
    ):
        raise core.V0P6IncompleteError(
            "receiver-signature certificate counts are inconsistent"
        )

    product: list[dict[str, Any]] = []
    observed_queries = 0
    for record_id in sorted(signatures):
        if not isinstance(record_id, str):
            raise core.V0P6ContractError(
                "receiver-signature keys must be record-ID strings"
            )
        core._frozen_sha256(record_id, "receiver-signature record identity")
        entries = signatures[record_id]
        if not isinstance(entries, list):
            raise core.V0P6ContractError(
                "receiver signature must be a list"
            )
        observed_epochs: list[int] = []
        canonical_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict) or frozenset(entry) != (
                _SIGNATURE_ENTRY_FIELDS
            ):
                raise core.V0P6ContractError(
                    "receiver signature entry schema changed"
                )
            epoch = core._strict_int(
                entry["epoch_zero_based"], "receiver-signature epoch"
            )
            predicted_mhz = _finite_json_number(
                entry["predicted_mid_mhz"], "receiver predicted midpoint"
            )
            peak_mhz = _finite_json_number(
                entry["peak_frequency_mhz"], "receiver peak frequency"
            )
            peak_snr = _finite_json_number(
                entry["peak_snr"], "receiver peak S/N"
            )
            stated_offset = _finite_json_number(
                entry["offset_from_prediction_hz"],
                "receiver offset from prediction",
            )
            if (
                not 0 <= epoch < epoch_count
                or not all(
                    math.isfinite(value)
                    for value in (
                        predicted_mhz,
                        peak_mhz,
                        peak_snr,
                        stated_offset,
                    )
                )
            ):
                raise core.V0P6ContractError(
                    "receiver signature entry is invalid"
                )
            literal_offset = float((peak_mhz - predicted_mhz) * 1e6)
            if stated_offset != literal_offset or abs(literal_offset) > (
                local_half_width
            ):
                raise core.V0P6ContractError(
                    "receiver signature literal offset is invalid"
                )
            observed_epochs.append(epoch)
            canonical_entries.append(entry)
        if observed_epochs != sorted(set(observed_epochs)):
            raise core.V0P6IncompleteError(
                "receiver signature epochs are duplicated or reordered"
            )
        observed_queries += len(entries)
        item = {
            "record_id": record_id,
            "receiver_frame_signature": canonical_entries,
        }
        if len(core.canonical_json_bytes(item)) > record_byte_cap:
            raise core.V0P6CapacityError(
                "receiver signature record exceeds its byte capacity"
            )
        product.append(item)
    if observed_queries != query_count:
        raise core.V0P6IncompleteError(
            "receiver-signature query count differs from its product"
        )
    product_bytes = core.canonical_json_bytes(product)
    mapping_bytes = core.canonical_json_bytes(signatures)
    product_length = core._strict_int(
        certificate["receiver_signature_product_canonical_bytes"],
        "receiver-signature product byte count",
    )
    mapping_length = core._strict_int(
        certificate["receiver_signatures_mapping_canonical_bytes"],
        "receiver-signature mapping byte count",
    )
    if (
        len(product_bytes) != product_length
        or hashlib.sha256(product_bytes).hexdigest()
        != certificate["receiver_signature_product_sha256"]
        or len(mapping_bytes) != mapping_length
        or hashlib.sha256(mapping_bytes).hexdigest()
        != certificate["receiver_signatures_mapping_sha256"]
        or product_length > evidence_cap
    ):
        raise core.V0P6IncompleteError(
            "receiver-signature product bytes changed"
        )
    return detached


def build_m37_receiver_frame_signatures(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_caches_by_width: Any,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Build the non-configurable M37 receiver-signature product."""
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    window_id = str(cert["window_id"])
    if window_id not in core.M37_WINDOW_IDS:
        raise core.V0P6ContractError(
            "M37 receiver signatures received an unknown window"
        )
    expected_hypotheses = (
        core.M37_TEMPLATE_COUNT
        * len(core.M37_SPECTRAL_WIDTHS)
        * len(core.M37_ACTIVITY_SUBSETS)
    )
    expected_score_cells = expected_hypotheses * (
        2 * core.M37_SCORE_HALF_BINS + 1
    )
    if (
        cert["scan_kind"] != "on"
        or cert["proxy_grid_sha256"]
        != core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        )
        or cert["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or cert["template_bank_sha256"] != core.M37_BANK_SHA256
        or cert["factor_basis_sha256"]
        != core.M37_FACTOR_BASIS_SHA256
        or cert["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or cert["scan_inventory_sha256"]
        != core.M37_SCAN_INVENTORY_SHA256
        or cert["factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or tuple(cert["spectral_widths"]) != core.M37_SPECTRAL_WIDTHS
        or tuple(tuple(item) for item in cert["activity_subsets"])
        != core.M37_ACTIVITY_SUBSETS
        or cert["epoch_count"] != 3
        or cert["minimum_active_epoch_snr"]
        != core.M37_MINIMUM_ACTIVE_EPOCH_SNR
        or cert["stack_statistic"] != "minimum_epoch"
        or cert["require_epoch_vector_product"] is not True
        or cert["require_mask_product"] is not True
        or cert["maximum_records"]
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or cert["maximum_record_canonical_bytes"]
        != core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
        or cert["maximum_evidence_canonical_bytes"]
        != core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        or cert["expected_hypotheses"] != expected_hypotheses
        or cert["expected_score_cells"] != expected_score_cells
    ):
        raise core.V0P6ContractError(
            "retention certificate violates the M37 receiver-signature contract"
        )
    core.validate_m37_factor_basis_scan_inventory(
        factor_basis, scan_definitions
    )
    bank = core.make_line_template_bank()
    core.validate_template_factor_table(
        factor_table,
        factor_basis,
        bank,
        expected_template_bank_sha256=core.M37_BANK_SHA256,
    )
    if (
        factor_table.factor_table_sha256 != cert["factor_table_sha256"]
        or factor_table.factors.shape != (core.M37_TEMPLATE_COUNT, 96)
        or core.proxy_carrier_grid_sha256(grid)
        != cert["proxy_grid_sha256"]
    ):
        raise core.V0P6ContractError(
            "M37 receiver signatures did not receive the frozen factors/grid"
        )
    return build_receiver_frame_signatures(
        on_records,
        cert,
        on_caches_by_width,
        scan_definitions,
        factor_basis,
        factor_table,
        bank,
        grid,
        local_half_width_hz=M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ,
        local_peak_snr_floor=M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR,
        maximum_records=core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        maximum_queries=M37_MAXIMUM_RECEIVER_SIGNATURE_QUERIES,
        maximum_local_channel_visits=(
            M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS
        ),
        maximum_signature_record_canonical_bytes=(
            core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
        ),
        maximum_evidence_canonical_bytes=(
            core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        ),
        expected_on_certificate_sha256=expected_on_certificate_sha256,
    )
