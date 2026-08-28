"""Aggregate resource ownership for detector-v0.6 physical evidence.

Receiver-frame signatures and single-adjacent-OFF evidence both consume the
same run-level native-cache inventory.  This module executes those stages in
strict sequence, seals each width stream after all mappings have closed, and
joins their evidence, retention, cache-manifest and factor-bundle ancestry in
one independently verifiable receipt.

Importing this module does not open telescope data or cache files.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from . import adjacent_v0p6 as adjacent
from . import cache_manifest_v0p6 as run_cache
from . import cache_stream_v0p6 as cache_stream
from . import receiver_v0p6 as receiver
from . import search_v0p6 as core


PHYSICAL_RESOURCE_ENVELOPE_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_physical_evidence_resource_envelope"
)
PHYSICAL_RESOURCE_ENVELOPE_SCHEMA_VERSION = 1
_STREAM_EXECUTION_ORDER = (
    "receiver_frame_signatures",
    "single_adjacent_off",
)
_STREAM_EXECUTION_MODE = (
    "strictly sequential; seal receiver stream after complete handle closure "
    "before opening adjacent-OFF stream"
)

_COMMON_EVIDENCE_FIELDS = (
    "window_id",
    "on_retention_certificate_sha256",
    "on_records_sha256",
    "proxy_grid_sha256",
    "template_bank_sha256",
    "factor_basis_sha256",
    "factor_basis_labels_sha256",
    "scan_inventory_sha256",
    "on_factor_row_selection_sha256",
    "factor_table_sha256",
)

_ENVELOPE_FIELDS = frozenset(
    {
        "artifact_type",
        "schema_version",
        "detector_version",
        "run_id",
        "window_id",
        "cache_run_manifest_file_sha256",
        "cache_run_inventory_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "factor_table_sha256",
        "spectral_widths",
        "receiver_result_sha256",
        "receiver_signature_certificate_sha256",
        "receiver_cache_identity_sha256",
        "adjacent_evidence_sha256",
        "single_adjacent_off_certificate_sha256",
        "adjacent_cache_identity_sha256",
        "receiver_stream_resource_certificate",
        "adjacent_stream_resource_certificate",
        "stream_resource_certificate_inventory_sha256",
        "stream_execution_order",
        "stream_execution_mode",
        "maximum_process_mapped_bytes",
        "aggregate_peak_mapped_bytes",
        "aggregate_peak_handle_count",
        "aggregate_batch_count",
        "aggregate_opened_cache_count",
        "all_streams_use_same_mapped_byte_cap",
        "no_stream_overlap",
        "all_handles_closed_before_stage_handoff",
        "evidence_cache_receipts_match_stream_receipts",
        "truncation_permitted",
        "resource_envelope_sha256",
    }
)


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


def _stream_cache_identities(
    certificate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for batch in certificate["batch_inventory"]:
        width = core._strict_int(
            batch["spectral_width_channels"], "stream cache width"
        )
        for cache_receipt in batch["cache_receipts"]:
            identities.append(
                {
                    "spectral_width_channels": width,
                    "scan_label": cache_receipt["scan_label"],
                    "source_sha256": cache_receipt["source_sha256"],
                    "cache_plan_sha256": cache_receipt[
                        "cache_plan_sha256"
                    ],
                    "cache_payload_sha256": cache_receipt[
                        "cache_payload_sha256"
                    ],
                }
            )
    return identities


def _receiver_cache_identities(
    certificate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "spectral_width_channels": item["spectral_width_channels"],
            "scan_label": item["scan_label"],
            "source_sha256": item["source_sha256"],
            "cache_plan_sha256": item["cache_plan_sha256"],
            "cache_payload_sha256": item["cache_payload_sha256"],
        }
        for item in certificate["cache_inventory"]
    ]


def _adjacent_cache_identities(
    certificate: Mapping[str, Any],
    stream_certificate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    stream_sources = {
        (
            item["spectral_width_channels"],
            item["scan_label"],
            item["cache_plan_sha256"],
            item["cache_payload_sha256"],
        ): item["source_sha256"]
        for item in _stream_cache_identities(stream_certificate)
    }
    identities: list[dict[str, Any]] = []
    for item in certificate["cache_inventory"]:
        key = (
            item["spectral_width_channels"],
            item["scan_label"],
            item["cache_plan_sha256"],
            item["cache_payload_sha256"],
        )
        if key not in stream_sources:
            raise core.V0P6IncompleteError(
                "adjacent evidence cache receipts differ from the stream"
            )
        identities.append(
            {
                "spectral_width_channels": item[
                    "spectral_width_channels"
                ],
                "scan_label": item["scan_label"],
                "source_sha256": stream_sources[key],
                "cache_plan_sha256": item["cache_plan_sha256"],
                "cache_payload_sha256": item["cache_payload_sha256"],
            }
        )
    return identities


def _cache_identity_sha256(items: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(core.canonical_json_bytes(list(items))).hexdigest()


def _validate_stream_pair(
    receiver_stream: Mapping[str, Any],
    adjacent_stream: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    receiver_cert = cache_stream.validate_stream_resource_certificate(
        receiver_stream
    )
    adjacent_cert = cache_stream.validate_stream_resource_certificate(
        adjacent_stream
    )
    common = (
        "run_id",
        "cache_run_manifest_file_sha256",
        "cache_run_inventory_sha256",
        "factor_bundle_manifest_sha256",
        "window_id",
        "spectral_widths",
        "maximum_mapped_bytes",
    )
    if any(receiver_cert[name] != adjacent_cert[name] for name in common):
        raise core.V0P6IncompleteError(
            "physical resource streams do not share one ancestry and cap"
        )
    if (
        receiver_cert["scan_kind"] != "on"
        or adjacent_cert["scan_kind"] != "off"
        or set(receiver_cert["scan_labels"]).intersection(
            adjacent_cert["scan_labels"]
        )
        or len(receiver_cert["scan_labels"])
        != len(adjacent_cert["scan_labels"])
    ):
        raise core.V0P6ContractError(
            "physical resource stream roles or scan inventories changed"
        )
    return receiver_cert, adjacent_cert


def _seal_physical_resource_envelope(
    receiver_result: Mapping[str, Any],
    receiver_stream_resource_certificate: Mapping[str, Any],
    adjacent_result: Mapping[str, Any],
    adjacent_stream_resource_certificate: Mapping[str, Any],
    *,
    expected_on_retention_certificate_sha256: str,
) -> dict[str, Any]:
    """Seal already-completed sequential stages into one resource root."""
    receiver_input = _detached_mapping(
        receiver_result, "receiver-signature result"
    )
    adjacent_input = _detached_mapping(
        adjacent_result, "single-adjacent-OFF result"
    )
    receiver_certificate = receiver_input.get("certificate")
    adjacent_certificate = adjacent_input.get("certificate")
    if not isinstance(receiver_certificate, dict) or not isinstance(
        adjacent_certificate, dict
    ):
        raise core.V0P6ContractError(
            "physical evidence results lack their certificates"
        )
    receiver_certificate_sha256 = core._frozen_sha256(
        receiver_certificate.get("receiver_signature_certificate_sha256"),
        "receiver-signature certificate identity",
    )
    adjacent_certificate_sha256 = core._frozen_sha256(
        adjacent_certificate.get("single_adjacent_off_certificate_sha256"),
        "single-adjacent-OFF certificate identity",
    )
    receiver_validated = receiver.validate_receiver_signature_result(
        receiver_input,
        expected_certificate_sha256=receiver_certificate_sha256,
    )
    adjacent_validated = adjacent.validate_single_adjacent_off_result(
        adjacent_input.get("evidence", []),
        adjacent_certificate,
        expected_certificate_sha256=adjacent_certificate_sha256,
    )
    receiver_resource, adjacent_resource = _validate_stream_pair(
        receiver_stream_resource_certificate,
        adjacent_stream_resource_certificate,
    )

    expected_retention = core._frozen_sha256(
        expected_on_retention_certificate_sha256,
        "expected ON-retention certificate identity",
    )
    if any(
        receiver_certificate[name] != adjacent_validated[name]
        for name in _COMMON_EVIDENCE_FIELDS
    ) or receiver_certificate["on_retention_certificate_sha256"] != (
        expected_retention
    ):
        raise core.V0P6IncompleteError(
            "physical evidence products do not share one ON-retention ancestry"
        )

    receiver_result_sha256 = core._frozen_sha256(
        receiver_validated["result_sha256"],
        "receiver-signature result identity",
    )
    adjacent_evidence_sha256 = core._frozen_sha256(
        adjacent_validated["evidence_sha256"],
        "single-adjacent-OFF evidence identity",
    )
    if (
        receiver_resource["evidence_artifact_type"]
        != receiver.RECEIVER_SIGNATURE_ARTIFACT_TYPE
        or receiver_resource["evidence_sha256"]
        != receiver_result_sha256
        or adjacent_resource["evidence_artifact_type"]
        != adjacent.SINGLE_ADJACENT_OFF_EVIDENCE_ARTIFACT_TYPE
        or adjacent_resource["evidence_sha256"]
        != adjacent_evidence_sha256
        or receiver_resource["window_id"]
        != receiver_certificate["window_id"]
        or tuple(receiver_resource["spectral_widths"])
        != tuple(receiver_certificate["spectral_widths"])
        or receiver_resource["scan_labels"]
        != receiver_certificate["on_scan_labels"]
    ):
        raise core.V0P6IncompleteError(
            "physical evidence identities differ from their stream receipts"
        )

    receiver_stream_identities = _stream_cache_identities(receiver_resource)
    adjacent_stream_identities = _stream_cache_identities(adjacent_resource)
    receiver_evidence_identities = _receiver_cache_identities(
        receiver_certificate
    )
    adjacent_evidence_identities = _adjacent_cache_identities(
        adjacent_validated, adjacent_resource
    )
    if (
        receiver_evidence_identities != receiver_stream_identities
        or adjacent_evidence_identities != adjacent_stream_identities
    ):
        raise core.V0P6IncompleteError(
            "physical evidence cache receipts differ from streamed caches"
        )
    receiver_cache_sha256 = _cache_identity_sha256(
        receiver_stream_identities
    )
    adjacent_cache_sha256 = _cache_identity_sha256(
        adjacent_stream_identities
    )
    resource_certificate_inventory = [
        receiver_resource["stream_resource_certificate_sha256"],
        adjacent_resource["stream_resource_certificate_sha256"],
    ]
    payload = {
        "artifact_type": PHYSICAL_RESOURCE_ENVELOPE_ARTIFACT_TYPE,
        "schema_version": PHYSICAL_RESOURCE_ENVELOPE_SCHEMA_VERSION,
        "detector_version": core.DETECTOR_VERSION,
        "run_id": receiver_resource["run_id"],
        "window_id": receiver_resource["window_id"],
        "cache_run_manifest_file_sha256": receiver_resource[
            "cache_run_manifest_file_sha256"
        ],
        "cache_run_inventory_sha256": receiver_resource[
            "cache_run_inventory_sha256"
        ],
        "factor_bundle_manifest_sha256": receiver_resource[
            "factor_bundle_manifest_sha256"
        ],
        "on_retention_certificate_sha256": expected_retention,
        "on_records_sha256": receiver_certificate["on_records_sha256"],
        "proxy_grid_sha256": receiver_certificate["proxy_grid_sha256"],
        "template_bank_sha256": receiver_certificate[
            "template_bank_sha256"
        ],
        "factor_basis_sha256": receiver_certificate[
            "factor_basis_sha256"
        ],
        "factor_basis_labels_sha256": receiver_certificate[
            "factor_basis_labels_sha256"
        ],
        "scan_inventory_sha256": receiver_certificate[
            "scan_inventory_sha256"
        ],
        "on_factor_row_selection_sha256": receiver_certificate[
            "on_factor_row_selection_sha256"
        ],
        "factor_table_sha256": receiver_certificate[
            "factor_table_sha256"
        ],
        "spectral_widths": receiver_resource["spectral_widths"],
        "receiver_result_sha256": receiver_result_sha256,
        "receiver_signature_certificate_sha256": (
            receiver_certificate_sha256
        ),
        "receiver_cache_identity_sha256": receiver_cache_sha256,
        "adjacent_evidence_sha256": adjacent_evidence_sha256,
        "single_adjacent_off_certificate_sha256": (
            adjacent_certificate_sha256
        ),
        "adjacent_cache_identity_sha256": adjacent_cache_sha256,
        "receiver_stream_resource_certificate": receiver_resource,
        "adjacent_stream_resource_certificate": adjacent_resource,
        "stream_resource_certificate_inventory_sha256": hashlib.sha256(
            core.canonical_json_bytes(resource_certificate_inventory)
        ).hexdigest(),
        "stream_execution_order": list(_STREAM_EXECUTION_ORDER),
        "stream_execution_mode": _STREAM_EXECUTION_MODE,
        "maximum_process_mapped_bytes": receiver_resource[
            "maximum_mapped_bytes"
        ],
        "aggregate_peak_mapped_bytes": max(
            receiver_resource["peak_mapped_bytes"],
            adjacent_resource["peak_mapped_bytes"],
        ),
        "aggregate_peak_handle_count": max(
            receiver_resource["peak_handle_count"],
            adjacent_resource["peak_handle_count"],
        ),
        "aggregate_batch_count": (
            receiver_resource["batch_count"]
            + adjacent_resource["batch_count"]
        ),
        "aggregate_opened_cache_count": (
            receiver_resource["opened_cache_count"]
            + adjacent_resource["opened_cache_count"]
        ),
        "all_streams_use_same_mapped_byte_cap": True,
        "no_stream_overlap": True,
        "all_handles_closed_before_stage_handoff": True,
        "evidence_cache_receipts_match_stream_receipts": True,
        "truncation_permitted": False,
    }
    envelope = json.loads(core.canonical_json_bytes(payload))
    envelope["resource_envelope_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(payload)
    ).hexdigest()
    validate_physical_resource_envelope(
        envelope,
        expected_envelope_sha256=envelope["resource_envelope_sha256"],
    )
    return envelope


def validate_physical_resource_envelope(
    envelope: Mapping[str, Any],
    *,
    expected_envelope_sha256: str,
) -> dict[str, Any]:
    """Validate a persisted aggregate receipt against its root digest."""
    detached = _detached_mapping(envelope, "physical resource envelope")
    if frozenset(detached) != _ENVELOPE_FIELDS:
        raise core.V0P6ContractError(
            "physical resource envelope fields differ from the schema"
        )
    observed_sha256 = core._frozen_sha256(
        detached.pop("resource_envelope_sha256"),
        "physical resource envelope identity",
    )
    expected_sha256 = core._frozen_sha256(
        expected_envelope_sha256,
        "expected physical resource envelope identity",
    )
    if observed_sha256 != hashlib.sha256(
        core.canonical_json_bytes(detached)
    ).hexdigest():
        raise core.V0P6IncompleteError(
            "physical resource envelope identity changed"
        )
    if observed_sha256 != expected_sha256:
        raise core.V0P6ContractError(
            "physical resource envelope differs from its trusted receipt"
        )
    detached["resource_envelope_sha256"] = observed_sha256
    receiver_resource, adjacent_resource = _validate_stream_pair(
        detached["receiver_stream_resource_certificate"],
        detached["adjacent_stream_resource_certificate"],
    )
    for name in (
        "cache_run_manifest_file_sha256",
        "cache_run_inventory_sha256",
        "factor_bundle_manifest_sha256",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "factor_table_sha256",
        "receiver_result_sha256",
        "receiver_signature_certificate_sha256",
        "receiver_cache_identity_sha256",
        "adjacent_evidence_sha256",
        "single_adjacent_off_certificate_sha256",
        "adjacent_cache_identity_sha256",
        "stream_resource_certificate_inventory_sha256",
    ):
        core._frozen_sha256(detached[name], name.replace("_", " "))
    if (
        detached["artifact_type"]
        != PHYSICAL_RESOURCE_ENVELOPE_ARTIFACT_TYPE
        or core._strict_int(
            detached["schema_version"],
            "physical resource envelope schema version",
        )
        != PHYSICAL_RESOURCE_ENVELOPE_SCHEMA_VERSION
        or detached["detector_version"] != core.DETECTOR_VERSION
        or detached["stream_execution_order"]
        != list(_STREAM_EXECUTION_ORDER)
        or detached["stream_execution_mode"] != _STREAM_EXECUTION_MODE
        or detached["all_streams_use_same_mapped_byte_cap"] is not True
        or detached["no_stream_overlap"] is not True
        or detached["all_handles_closed_before_stage_handoff"] is not True
        or detached["evidence_cache_receipts_match_stream_receipts"]
        is not True
        or detached["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "physical resource envelope semantics changed"
        )
    if not isinstance(detached["run_id"], str) or not detached["run_id"]:
        raise core.V0P6ContractError(
            "physical resource envelope run ID is invalid"
        )
    if not isinstance(detached["window_id"], str) or not detached[
        "window_id"
    ]:
        raise core.V0P6ContractError(
            "physical resource envelope window ID is invalid"
        )
    widths = tuple(core._strict_widths(detached["spectral_widths"]))
    resource_inventory = [
        receiver_resource["stream_resource_certificate_sha256"],
        adjacent_resource["stream_resource_certificate_sha256"],
    ]
    shared_resource_fields = {
        "run_id": receiver_resource["run_id"],
        "window_id": receiver_resource["window_id"],
        "cache_run_manifest_file_sha256": receiver_resource[
            "cache_run_manifest_file_sha256"
        ],
        "cache_run_inventory_sha256": receiver_resource[
            "cache_run_inventory_sha256"
        ],
        "factor_bundle_manifest_sha256": receiver_resource[
            "factor_bundle_manifest_sha256"
        ],
    }
    if any(
        detached[name] != value
        for name, value in shared_resource_fields.items()
    ):
        raise core.V0P6IncompleteError(
            "physical resource envelope ancestry changed"
        )
    receiver_cache_sha256 = _cache_identity_sha256(
        _stream_cache_identities(receiver_resource)
    )
    adjacent_cache_sha256 = _cache_identity_sha256(
        _stream_cache_identities(adjacent_resource)
    )
    maximum_bytes = core._strict_int(
        detached["maximum_process_mapped_bytes"],
        "physical resource mapped-byte cap",
    )
    aggregate_peak_bytes = core._strict_int(
        detached["aggregate_peak_mapped_bytes"],
        "physical resource peak mapped bytes",
    )
    aggregate_peak_handles = core._strict_int(
        detached["aggregate_peak_handle_count"],
        "physical resource peak handle count",
    )
    if (
        widths != tuple(receiver_resource["spectral_widths"])
        or detached["receiver_result_sha256"]
        != receiver_resource["evidence_sha256"]
        or detached["adjacent_evidence_sha256"]
        != adjacent_resource["evidence_sha256"]
        or receiver_resource["evidence_artifact_type"]
        != receiver.RECEIVER_SIGNATURE_ARTIFACT_TYPE
        or adjacent_resource["evidence_artifact_type"]
        != adjacent.SINGLE_ADJACENT_OFF_EVIDENCE_ARTIFACT_TYPE
        or detached["receiver_cache_identity_sha256"]
        != receiver_cache_sha256
        or detached["adjacent_cache_identity_sha256"]
        != adjacent_cache_sha256
        or hashlib.sha256(
            core.canonical_json_bytes(resource_inventory)
        ).hexdigest()
        != detached["stream_resource_certificate_inventory_sha256"]
        or maximum_bytes != receiver_resource["maximum_mapped_bytes"]
        or aggregate_peak_bytes
        != max(
            receiver_resource["peak_mapped_bytes"],
            adjacent_resource["peak_mapped_bytes"],
        )
        or aggregate_peak_bytes > maximum_bytes
        or aggregate_peak_handles
        != max(
            receiver_resource["peak_handle_count"],
            adjacent_resource["peak_handle_count"],
        )
        or core._strict_int(
            detached["aggregate_batch_count"],
            "physical resource aggregate batch count",
        )
        != receiver_resource["batch_count"] + adjacent_resource["batch_count"]
        or core._strict_int(
            detached["aggregate_opened_cache_count"],
            "physical resource aggregate cache count",
        )
        != receiver_resource["opened_cache_count"]
        + adjacent_resource["opened_cache_count"]
    ):
        raise core.V0P6IncompleteError(
            "physical resource envelope accounting changed"
        )
    return json.loads(core.canonical_json_bytes(detached))


def execute_physical_evidence_streams(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_stream: cache_stream.CacheWidthStream,
    off_stream: cache_stream.CacheWidthStream,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    local_receiver_half_width_hz: float,
    local_receiver_peak_snr_floor: float,
    single_adjacent_off_snr_floor: float,
    maximum_records: int,
    maximum_receiver_queries: int,
    maximum_receiver_local_channel_visits: int,
    maximum_signature_record_canonical_bytes: int,
    maximum_adjacent_queries: int,
    maximum_evidence_canonical_bytes: int,
    expected_on_retention_certificate_sha256: str,
    adjacent_chunk_bins: int = 131_072,
) -> dict[str, Any]:
    """Execute generic physical streams in the only permitted order."""
    if not isinstance(on_stream, cache_stream.CacheWidthStream) or not isinstance(
        off_stream, cache_stream.CacheWidthStream
    ):
        raise core.V0P6ContractError(
            "physical evidence execution requires CacheWidthStream instances"
        )
    receiver_result = receiver.build_receiver_frame_signatures_streaming(
        on_records,
        on_certificate,
        on_stream.open_width,
        scan_definitions,
        factor_basis,
        factor_table,
        template_bank,
        grid,
        local_half_width_hz=local_receiver_half_width_hz,
        local_peak_snr_floor=local_receiver_peak_snr_floor,
        maximum_records=maximum_records,
        maximum_queries=maximum_receiver_queries,
        maximum_local_channel_visits=(
            maximum_receiver_local_channel_visits
        ),
        maximum_signature_record_canonical_bytes=(
            maximum_signature_record_canonical_bytes
        ),
        maximum_evidence_canonical_bytes=maximum_evidence_canonical_bytes,
        expected_on_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
    )
    receiver_resource = on_stream.seal(
        evidence_artifact_type=receiver.RECEIVER_SIGNATURE_ARTIFACT_TYPE,
        evidence_sha256=receiver_result["result_sha256"],
    )
    adjacent_result = adjacent.evaluate_single_adjacent_off_veto_streaming(
        on_records,
        on_certificate,
        off_stream.open_width,
        scan_definitions,
        factor_basis,
        factor_table,
        template_bank,
        grid,
        single_epoch_snr_floor=single_adjacent_off_snr_floor,
        maximum_records=maximum_records,
        maximum_queries=maximum_adjacent_queries,
        maximum_evidence_canonical_bytes=maximum_evidence_canonical_bytes,
        expected_on_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
        chunk_bins=adjacent_chunk_bins,
    )
    adjacent_resource = off_stream.seal(
        evidence_artifact_type=(
            adjacent.SINGLE_ADJACENT_OFF_EVIDENCE_ARTIFACT_TYPE
        ),
        evidence_sha256=adjacent_result["certificate"]["evidence_sha256"],
    )
    envelope = _seal_physical_resource_envelope(
        receiver_result,
        receiver_resource,
        adjacent_result,
        adjacent_resource,
        expected_on_retention_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
    )
    result_payload = {
        "receiver_result": receiver_result,
        "adjacent_result": adjacent_result,
        "resource_envelope": envelope,
    }
    result = json.loads(core.canonical_json_bytes(result_payload))
    result["execution_result_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(result_payload)
    ).hexdigest()
    return result


def execute_m37_physical_evidence_streams(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_stream: cache_stream.CacheWidthStream,
    off_stream: cache_stream.CacheWidthStream,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_retention_certificate_sha256: str,
    adjacent_chunk_bins: int = 131_072,
) -> dict[str, Any]:
    """Execute the non-configurable M37 physical resource stage."""
    if not isinstance(on_stream, cache_stream.CacheWidthStream) or not isinstance(
        off_stream, cache_stream.CacheWidthStream
    ):
        raise core.V0P6ContractError(
            "M37 physical evidence execution requires CacheWidthStream instances"
        )
    receiver_result = receiver.build_m37_receiver_frame_signatures_streaming(
        on_records,
        on_certificate,
        on_stream.open_width,
        scan_definitions,
        factor_basis,
        factor_table,
        grid,
        expected_on_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
    )
    receiver_resource = on_stream.seal(
        evidence_artifact_type=receiver.RECEIVER_SIGNATURE_ARTIFACT_TYPE,
        evidence_sha256=receiver_result["result_sha256"],
    )
    adjacent_result = adjacent.evaluate_m37_single_adjacent_off_veto_streaming(
        on_records,
        on_certificate,
        off_stream.open_width,
        scan_definitions,
        factor_basis,
        factor_table,
        grid,
        expected_on_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
        chunk_bins=adjacent_chunk_bins,
    )
    adjacent_resource = off_stream.seal(
        evidence_artifact_type=(
            adjacent.SINGLE_ADJACENT_OFF_EVIDENCE_ARTIFACT_TYPE
        ),
        evidence_sha256=adjacent_result["certificate"]["evidence_sha256"],
    )
    envelope = _seal_physical_resource_envelope(
        receiver_result,
        receiver_resource,
        adjacent_result,
        adjacent_resource,
        expected_on_retention_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
    )
    result_payload = {
        "receiver_result": receiver_result,
        "adjacent_result": adjacent_result,
        "resource_envelope": envelope,
    }
    result = json.loads(core.canonical_json_bytes(result_payload))
    result["execution_result_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(result_payload)
    ).hexdigest()
    validate_m37_physical_resource_envelope(
        result["resource_envelope"],
        expected_envelope_sha256=result["resource_envelope"][
            "resource_envelope_sha256"
        ],
    )
    return result


def validate_m37_physical_resource_envelope(
    envelope: Mapping[str, Any],
    *,
    expected_envelope_sha256: str,
) -> dict[str, Any]:
    """Apply the exact M37 widths, scans and 512-MiB cap."""
    validated = validate_physical_resource_envelope(
        envelope, expected_envelope_sha256=expected_envelope_sha256
    )
    on_labels = [
        label
        for label in run_cache.M37_SCAN_LABELS
        if run_cache.M37_SCAN_KINDS[label] == "on"
    ]
    off_labels = [
        label
        for label in run_cache.M37_SCAN_LABELS
        if run_cache.M37_SCAN_KINDS[label] == "off"
    ]
    if (
        validated["window_id"] not in core.M37_WINDOW_IDS
        or tuple(validated["spectral_widths"])
        != core.M37_SPECTRAL_WIDTHS
        or validated["proxy_grid_sha256"]
        != core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(validated["window_id"])
        )
        or validated["template_bank_sha256"] != core.M37_BANK_SHA256
        or validated["factor_basis_sha256"]
        != core.M37_FACTOR_BASIS_SHA256
        or validated["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or validated["scan_inventory_sha256"]
        != core.M37_SCAN_INVENTORY_SHA256
        or validated["on_factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or validated["maximum_process_mapped_bytes"]
        != core.M37_LIVE_NDARRAY_CAP_BYTES
        or validated["receiver_stream_resource_certificate"]["scan_labels"]
        != on_labels
        or validated["adjacent_stream_resource_certificate"]["scan_labels"]
        != off_labels
    ):
        raise core.V0P6ContractError(
            "physical resource envelope differs from the M37 contract"
        )
    return validated
