"""Physical-disposition continuation for the M37 v0.6.1 amendment.

The v0.6.1 protocol changes resource ceilings only.  This module keeps the
frozen M37 physical tests and precedence rules, while admitting the single
capacity profile sealed after Run 004.  The original v0.6 wrappers remain
unchanged and continue to reject amended retention products.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from . import adjacent_v0p6 as adjacent
from . import alias_v0p6 as alias
from . import cache_manifest_v0p6 as cache_manifest
from . import capacity_v0p6p1 as capacity
from . import physical_disposition_v0p6 as disposition
from . import physical_disposition_manifest_v0p6 as disposition_manifest
from . import physical_resource_v0p6 as physical
from . import receiver_v0p6 as receiver
from . import search_v0p6 as core


M37_V0P6P1_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS = (
    5 * receiver.M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS
)
M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES = (
    4 * capacity.M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES
    + 2 * 16_777_216
)


def _profile(
    value: capacity.M37V0P6P1CapacityProfile,
) -> capacity.M37V0P6P1CapacityProfile:
    if not isinstance(value, capacity.M37V0P6P1CapacityProfile):
        raise core.V0P6ContractError(
            "physical v0.6.1 stage requires the frozen capacity profile"
        )
    return capacity.validate_m37_v0p6p1_capacity_profile_record(
        value.as_record()
    )


def validate_m37_v0p6p1_retention_certificate(
    certificate: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_kind: str,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate an amended ledger without weakening any science field."""
    profile = _profile(profile)
    if expected_kind not in {"on", "off"}:
        raise core.V0P6ContractError("retention kind must be ON or OFF")
    cert = core.validate_retention_certificate(
        certificate,
        expected_certificate_sha256=expected_certificate_sha256,
    )
    window_id = str(cert["window_id"])
    expected_hypotheses = (
        core.M37_TEMPLATE_COUNT
        * len(core.M37_SPECTRAL_WIDTHS)
        * len(core.M37_ACTIVITY_SUBSETS)
    )
    expected_score_cells = expected_hypotheses * (
        2 * core.M37_SCORE_HALF_BINS + 1
    )
    if (
        window_id not in core.M37_WINDOW_IDS
        or cert["scan_kind"] != expected_kind
        or cert["proxy_grid_sha256"]
        != core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        )
        or cert["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or cert["template_bank_sha256"] != core.M37_BANK_SHA256
        or cert["factor_basis_sha256"] != core.M37_FACTOR_BASIS_SHA256
        or cert["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or cert["scan_inventory_sha256"] != core.M37_SCAN_INVENTORY_SHA256
        or cert["factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S[expected_kind]
        or tuple(cert["spectral_widths"]) != core.M37_SPECTRAL_WIDTHS
        or tuple(tuple(item) for item in cert["activity_subsets"])
        != core.M37_ACTIVITY_SUBSETS
        or cert["epoch_count"] != 3
        or cert["minimum_active_epoch_snr"]
        != core.M37_MINIMUM_ACTIVE_EPOCH_SNR
        or cert["stack_statistic"] != "minimum_epoch"
        or cert["require_epoch_vector_product"] is not True
        or cert["require_mask_product"] is not True
        or cert["maximum_records"] != profile.maximum_records_per_window
        or cert["maximum_record_canonical_bytes"]
        != profile.maximum_record_canonical_bytes
        or cert["maximum_evidence_canonical_bytes"]
        != profile.maximum_retention_evidence_canonical_bytes_per_window
        or cert["expected_hypotheses"] != expected_hypotheses
        or cert["hypotheses_replayed"] != expected_hypotheses
        or cert["expected_score_cells"] != expected_score_cells
        or cert["score_cells_replayed"] != expected_score_cells
        or cert["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "retention certificate violates the M37 v0.6.1 contract"
        )
    return cert


def _validate_scientific_inputs(
    certificate: Mapping[str, Any],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_kind: str,
    expected_certificate_sha256: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cert = validate_m37_v0p6p1_retention_certificate(
        certificate,
        profile,
        expected_kind=expected_kind,
        expected_certificate_sha256=expected_certificate_sha256,
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
        factor_basis.basis_sha256 != core.M37_FACTOR_BASIS_SHA256
        or factor_basis.labels_sha256 != core.M37_FACTOR_BASIS_LABELS_SHA256
        or factor_table.factor_basis_sha256 != core.M37_FACTOR_BASIS_SHA256
        or factor_table.template_bank_sha256 != core.M37_BANK_SHA256
        or factor_table.factor_table_sha256 != cert["factor_table_sha256"]
        or factor_table.factors.shape
        != (core.M37_TEMPLATE_COUNT, len(factor_basis.labels))
        or core.proxy_carrier_grid_sha256(grid)
        != cert["proxy_grid_sha256"]
    ):
        raise core.V0P6ContractError(
            "physical v0.6.1 stage did not receive the sealed M37 factors"
        )
    return cert, bank


def execute_m37_v0p6p1_physical_evidence_streams(
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    on_stream: Any,
    off_stream: Any,
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_retention_certificate_sha256: str,
    adjacent_chunk_bins: int = 131_072,
) -> dict[str, Any]:
    """Execute unchanged M37 physical evidence with amended ceilings."""
    profile = _profile(profile)
    _, bank = _validate_scientific_inputs(
        on_certificate,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        profile,
        expected_kind="on",
        expected_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
    )
    result = physical.execute_physical_evidence_streams(
        on_records,
        on_certificate,
        on_stream,
        off_stream,
        scan_definitions,
        factor_basis,
        factor_table,
        bank,
        grid,
        local_receiver_half_width_hz=(
            receiver.M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ
        ),
        local_receiver_peak_snr_floor=(
            receiver.M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR
        ),
        single_adjacent_off_snr_floor=(
            adjacent.M37_SINGLE_ADJACENT_OFF_SNR_FLOOR
        ),
        maximum_records=profile.maximum_records_per_window,
        maximum_receiver_queries=(
            profile.maximum_adjacent_or_receiver_queries_per_window
        ),
        maximum_receiver_local_channel_visits=(
            M37_V0P6P1_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS
        ),
        maximum_signature_record_canonical_bytes=(
            profile.maximum_record_canonical_bytes
        ),
        maximum_adjacent_queries=(
            profile.maximum_adjacent_or_receiver_queries_per_window
        ),
        maximum_evidence_canonical_bytes=(
            profile.maximum_retention_evidence_canonical_bytes_per_window
        ),
        expected_on_retention_certificate_sha256=(
            expected_on_retention_certificate_sha256
        ),
        adjacent_chunk_bins=adjacent_chunk_bins,
    )
    return validate_m37_v0p6p1_physical_evidence_execution_result(
        result,
        profile,
        expected_execution_result_sha256=result["execution_result_sha256"],
    )


def validate_m37_v0p6p1_physical_resource_envelope(
    envelope: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_envelope_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    validated = physical.validate_physical_resource_envelope(
        envelope, expected_envelope_sha256=expected_envelope_sha256
    )
    on_labels = [
        label
        for label in cache_manifest.M37_SCAN_LABELS
        if cache_manifest.M37_SCAN_KINDS[label] == "on"
    ]
    off_labels = [
        label
        for label in cache_manifest.M37_SCAN_LABELS
        if cache_manifest.M37_SCAN_KINDS[label] == "off"
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
        != profile.maximum_live_ndarray_bytes
        or validated["receiver_stream_resource_certificate"][
            "scan_labels"
        ]
        != on_labels
        or validated["adjacent_stream_resource_certificate"][
            "scan_labels"
        ]
        != off_labels
    ):
        raise core.V0P6ContractError(
            "physical resource envelope differs from M37 v0.6.1"
        )
    return validated


def validate_m37_v0p6p1_physical_evidence_execution_result(
    result: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_execution_result_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    validated = physical.validate_physical_evidence_execution_result(
        result,
        expected_execution_result_sha256=expected_execution_result_sha256,
    )
    envelope = validated["resource_envelope"]
    validate_m37_v0p6p1_physical_resource_envelope(
        envelope,
        profile,
        expected_envelope_sha256=envelope["resource_envelope_sha256"],
    )
    receiver_certificate = validated["receiver_result"]["certificate"]
    adjacent_certificate = validated["adjacent_result"]["certificate"]
    if (
        receiver_certificate["local_receiver_half_width_hz"]
        != receiver.M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ
        or receiver_certificate["local_peak_snr_floor"]
        != receiver.M37_RECEIVER_SIGNATURE_PEAK_SNR_FLOOR
        or receiver_certificate["maximum_records"]
        != profile.maximum_records_per_window
        or receiver_certificate["maximum_queries"]
        != profile.maximum_adjacent_or_receiver_queries_per_window
        or receiver_certificate["maximum_local_channel_visits"]
        != M37_V0P6P1_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS
        or receiver_certificate[
            "maximum_signature_record_canonical_bytes"
        ]
        != profile.maximum_record_canonical_bytes
        or receiver_certificate["maximum_evidence_canonical_bytes"]
        != profile.maximum_retention_evidence_canonical_bytes_per_window
        or adjacent_certificate["single_epoch_snr_floor"]
        != adjacent.M37_SINGLE_ADJACENT_OFF_SNR_FLOOR
        or adjacent_certificate["maximum_records"]
        != profile.maximum_records_per_window
        or adjacent_certificate["maximum_queries"]
        != profile.maximum_adjacent_or_receiver_queries_per_window
        or adjacent_certificate["maximum_evidence_canonical_bytes"]
        != profile.maximum_retention_evidence_canonical_bytes_per_window
    ):
        raise core.V0P6ContractError(
            "physical evidence execution differs from M37 v0.6.1"
        )
    return validated


def match_m37_v0p6p1_retained_off_tracks(
    profile: capacity.M37V0P6P1CapacityProfile,
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    off_records: Sequence[Mapping[str, Any]],
    off_certificate: Mapping[str, Any],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    *,
    expected_on_certificate_sha256: str,
    expected_off_certificate_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    on_cert = validate_m37_v0p6p1_retention_certificate(
        on_certificate,
        profile,
        expected_kind="on",
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    off_cert = validate_m37_v0p6p1_retention_certificate(
        off_certificate,
        profile,
        expected_kind="off",
        expected_certificate_sha256=expected_off_certificate_sha256,
    )
    if on_cert["window_id"] != off_cert["window_id"]:
        raise core.V0P6ContractError(
            "amended ON and OFF ledgers use different windows"
        )
    grid = core.make_m37_proxy_carrier_grid(on_cert["window_id"])
    _, bank = _validate_scientific_inputs(
        on_certificate,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        profile,
        expected_kind="on",
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    off_factors = core.factor_matrix_for_kind(
        factor_table, factor_basis, scan_definitions, "off"
    )
    if off_factors.shape != (core.M37_TEMPLATE_COUNT, 48):
        raise core.V0P6ContractError(
            "M37 v0.6.1 OFF factor matrix must have shape [93, 48]"
        )
    return core.match_retained_off_tracks(
        on_records,
        on_certificate,
        off_records,
        off_certificate,
        grid,
        off_factors,
        window_order=core.M37_WINDOW_IDS,
        tolerance_hz=core.M37_OFF_TRACK_TOLERANCE_HZ,
        maximum_bucket_entries=(
            profile.maximum_off_bucket_entries_per_window
        ),
        maximum_exact_candidate_visits=(
            profile.maximum_off_exact_candidate_visits_per_window
        ),
        template_bank=bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        expected_off_certificate_sha256=expected_off_certificate_sha256,
    )


def match_m37_v0p6p1_receiver_frame_aliases(
    profile: capacity.M37V0P6P1CapacityProfile,
    records: Sequence[Mapping[str, Any]],
    on_retention_certificate: Mapping[str, Any],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    scan_definitions: Sequence[Mapping[str, Any]],
    receiver_signature_result: Mapping[str, Any],
    *,
    off_match_certificate: Mapping[str, Any],
    single_adjacent_off_evidence: Sequence[Mapping[str, Any]],
    single_adjacent_off_certificate: Mapping[str, Any],
    expected_off_match_certificate_sha256: str,
    expected_single_adjacent_off_certificate_sha256: str,
    expected_receiver_signature_certificate_sha256: str,
    expected_on_certificate_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    receiver_result = receiver.validate_receiver_signature_result(
        receiver_signature_result,
        expected_certificate_sha256=(
            expected_receiver_signature_certificate_sha256
        ),
    )
    receiver_certificate = receiver_result["certificate"]
    cert = validate_m37_v0p6p1_retention_certificate(
        on_retention_certificate,
        profile,
        expected_kind="on",
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    grid = core.make_m37_proxy_carrier_grid(cert["window_id"])
    _, bank = _validate_scientific_inputs(
        on_retention_certificate,
        factor_basis,
        factor_table,
        scan_definitions,
        grid,
        profile,
        expected_kind="on",
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    on_factors = core.factor_matrix_for_kind(
        factor_table, factor_basis, scan_definitions, "on"
    )
    if (
        on_factors.shape != (core.M37_TEMPLATE_COUNT, 48)
        or receiver_certificate["window_id"] != cert["window_id"]
        or receiver_certificate["on_retention_certificate_sha256"]
        != cert["retention_certificate_sha256"]
        or receiver_certificate["on_records_sha256"]
        != cert["records_sha256"]
        or receiver_certificate["proxy_grid_sha256"]
        != cert["proxy_grid_sha256"]
        or receiver_certificate["template_bank_sha256"]
        != core.M37_BANK_SHA256
        or receiver_certificate["factor_basis_sha256"]
        != core.M37_FACTOR_BASIS_SHA256
        or receiver_certificate["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or receiver_certificate["scan_inventory_sha256"]
        != core.M37_SCAN_INVENTORY_SHA256
        or receiver_certificate["on_factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or receiver_certificate["factor_table_sha256"]
        != factor_table.factor_table_sha256
        or tuple(receiver_certificate["spectral_widths"])
        != core.M37_SPECTRAL_WIDTHS
        or receiver_certificate["epoch_count"] != 3
        or receiver_certificate["local_receiver_half_width_hz"]
        != alias.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        or receiver_certificate["local_peak_snr_floor"]
        != alias.M37_RECEIVER_PEAK_SNR_FLOOR
    ):
        raise core.V0P6ContractError(
            "receiver-signature receipt violates M37 v0.6.1"
        )
    receiver_certificate_sha = core._frozen_sha256(
        receiver_certificate["receiver_signature_certificate_sha256"],
        "receiver-signature certificate identity",
    )
    return alias.match_receiver_frame_aliases(
        records,
        on_retention_certificate,
        grid,
        on_factors,
        receiver_result["receiver_signatures"],
        off_match_certificate=off_match_certificate,
        single_adjacent_off_evidence=single_adjacent_off_evidence,
        single_adjacent_off_certificate=single_adjacent_off_certificate,
        expected_off_match_certificate_sha256=(
            expected_off_match_certificate_sha256
        ),
        expected_single_adjacent_off_certificate_sha256=(
            expected_single_adjacent_off_certificate_sha256
        ),
        window_order=core.M37_WINDOW_IDS,
        track_tolerance_hz=alias.M37_ALIAS_TRACK_TOLERANCE_HZ,
        local_half_width_hz=alias.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ,
        local_peak_snr_floor=alias.M37_RECEIVER_PEAK_SNR_FLOOR,
        minimum_shared_active_epochs=(
            alias.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        ),
        maximum_records=profile.maximum_records_per_window,
        maximum_bucket_entries=(
            profile.maximum_alias_bucket_entries_per_window
        ),
        maximum_identity_track_comparisons=(
            profile.maximum_alias_identity_track_comparisons_per_window
        ),
        maximum_distinct_candidate_visits_per_window=(
            profile.maximum_alias_distinct_candidate_visits_per_window
        ),
        template_bank=bank,
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        receiver_signature_certificate_sha256=receiver_certificate_sha,
        expected_receiver_signature_product_sha256=(
            receiver_certificate["receiver_signature_product_sha256"]
        ),
    )


def validate_m37_v0p6p1_physical_disposition_result(
    result: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_physical_disposition_certificate_sha256: str,
) -> dict[str, Any]:
    profile = _profile(profile)
    validated = disposition.validate_physical_disposition_result(
        result,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    validate_m37_v0p6p1_physical_evidence_execution_result(
        validated["physical_evidence_execution_result"],
        profile,
        expected_execution_result_sha256=validated["certificate"][
            "physical_evidence_execution_result_sha256"
        ],
    )
    cert = validated["receiver_alias_result"]["certificate"]
    window_id = validated["certificate"]["window_id"]
    if (
        window_id not in core.M37_WINDOW_IDS
        or cert["window_ordinal"] != core.M37_WINDOW_IDS.index(window_id)
        or cert["track_tolerance_hz"]
        != alias.M37_ALIAS_TRACK_TOLERANCE_HZ
        or cert["local_receiver_half_width_hz"]
        != alias.M37_RECEIVER_LOCAL_HALF_WIDTH_HZ
        or cert["local_peak_snr_floor"]
        != alias.M37_RECEIVER_PEAK_SNR_FLOOR
        or cert["minimum_shared_active_epochs"]
        != alias.M37_RECEIVER_MINIMUM_SHARED_ACTIVE_EPOCHS
        or cert["maximum_records"] != profile.maximum_records_per_window
        or cert["maximum_bucket_entries"]
        != profile.maximum_alias_bucket_entries_per_window
        or cert["maximum_alias_identity_track_comparisons"]
        != profile.maximum_alias_identity_track_comparisons_per_window
        or cert["maximum_distinct_candidate_visits_per_window"]
        != profile.maximum_alias_distinct_candidate_visits_per_window
    ):
        raise core.V0P6ContractError(
            "physical disposition differs from M37 v0.6.1"
        )
    return validated


def seal_m37_v0p6p1_physical_disposition_result(
    profile: capacity.M37V0P6P1CapacityProfile,
    physical_evidence_execution_result: Mapping[str, Any],
    off_match_result: Mapping[str, Any],
    receiver_alias_result: Mapping[str, Any],
    *,
    expected_physical_evidence_execution_result_sha256: str,
    expected_off_match_certificate_sha256: str,
    expected_receiver_alias_certificate_sha256: str,
) -> dict[str, Any]:
    result = disposition.seal_physical_disposition_result(
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
    return validate_m37_v0p6p1_physical_disposition_result(
        result,
        profile,
        expected_physical_disposition_certificate_sha256=result[
            "certificate"
        ]["physical_disposition_certificate_sha256"],
    )


def publish_m37_v0p6p1_physical_disposition_artifact(
    path: Any,
    result: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_physical_disposition_certificate_sha256: str,
) -> disposition.PhysicalDispositionArtifactReceipt:
    profile = _profile(profile)
    validated = validate_m37_v0p6p1_physical_disposition_result(
        result,
        profile,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
    )
    return disposition.publish_physical_disposition_artifact(
        path,
        validated,
        expected_physical_disposition_certificate_sha256=(
            expected_physical_disposition_certificate_sha256
        ),
        maximum_artifact_bytes=(
            M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES
        ),
    )


def open_m37_v0p6p1_physical_disposition_artifact(
    path: Any,
    profile: capacity.M37V0P6P1CapacityProfile,
    **expected: Any,
) -> disposition.PhysicalDispositionArtifact:
    profile = _profile(profile)
    artifact_path = Path(path)
    compressed_path = Path(f"{artifact_path}.gz")
    if (
        not artifact_path.is_file()
        and compressed_path.is_file()
        and compressed_path.stat().st_size
        > profile.maximum_single_compressed_output_file_bytes
    ):
        raise core.V0P6CapacityError(
            "compressed physical-disposition artifact exceeds its byte cap"
        )
    opened = disposition.open_physical_disposition_artifact(
        path,
        maximum_artifact_bytes=(
            M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES
        ),
        **expected,
    )
    validate_m37_v0p6p1_physical_disposition_result(
        opened.result,
        profile,
        expected_physical_disposition_certificate_sha256=(
            opened.receipt.physical_disposition_certificate_sha256
        ),
    )
    return opened


def publish_m37_v0p6p1_physical_disposition_run_manifest(
    path: Any,
    entries: Sequence[
        disposition_manifest.PhysicalDispositionRunEntry
    ],
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> disposition_manifest.PhysicalDispositionRunManifestReceipt:
    """Validate all amended children before publishing the run inventory."""
    profile = _profile(profile)
    entries = tuple(entries)
    if tuple(entry.window_id for entry in entries) != core.M37_WINDOW_IDS:
        raise core.V0P6IncompleteError(
            "v0.6.1 disposition windows are missing or reordered"
        )
    parent = Path(path).parent
    for entry in entries:
        opened = open_m37_v0p6p1_physical_disposition_artifact(
            parent / entry.relative_path,
            profile,
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
        reproduced = disposition_manifest.make_physical_disposition_run_entry(
            entry.relative_path, opened
        )
        if reproduced != entry:
            raise core.V0P6IncompleteError(
                "v0.6.1 disposition child differs from its run entry"
            )
    return disposition_manifest.publish_physical_disposition_run_manifest(
        path,
        entries,
        expected_window_ids=core.M37_WINDOW_IDS,
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


def open_m37_v0p6p1_physical_disposition_run_manifest(
    path: Any,
    profile: capacity.M37V0P6P1CapacityProfile,
    **expected: Any,
) -> disposition_manifest.PhysicalDispositionRunManifest:
    profile = _profile(profile)
    expected = dict(expected)
    expected["expected_window_ids"] = core.M37_WINDOW_IDS
    opened = disposition_manifest.open_physical_disposition_run_manifest(
        path,
        maximum_child_artifact_bytes=(
            M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES
        ),
        **expected,
    )
    for artifact in opened.artifacts:
        validate_m37_v0p6p1_physical_disposition_result(
            artifact.result,
            profile,
            expected_physical_disposition_certificate_sha256=(
                artifact.receipt.physical_disposition_certificate_sha256
            ),
        )
    return opened


def advance_m37_v0p6p1_physical_disposition_from_manifest(
    journal_path: Any,
    profile: capacity.M37V0P6P1CapacityProfile,
    *,
    expected_head_sha256: str,
    manifest_path: Any,
    expected_manifest_file_sha256: str,
    expected_manifest_sha256: str,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> Any:
    """Advance the journal only after reopening all five amended children."""
    from . import run_state_v0p6 as state

    profile = _profile(profile)
    current = state.read_m37_run_journal(
        journal_path, expected_head_sha256=expected_head_sha256
    )
    if current.run_id != expected_run_id:
        raise core.V0P6IncompleteError(
            "v0.6.1 disposition run differs from the journal"
        )
    opened = open_m37_v0p6p1_physical_disposition_run_manifest(
        manifest_path,
        profile,
        expected_file_sha256=expected_manifest_file_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
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
    receipt = opened.receipt
    return state.advance_m37_run_journal(
        journal_path,
        expected_head_sha256=current.head_sha256,
        stage="physical_disposition_complete",
        artifact_sha256=receipt.file_sha256,
        metadata={
            "spectral_access_authorized": True,
            "spectral_dataset_values_read": True,
            "capacity_amendment_file_sha256": (
                profile.amendment_file_sha256
            ),
            "physical_disposition_manifest_sha256": (
                receipt.manifest_sha256
            ),
            "disposition_artifact_inventory_sha256": (
                receipt.disposition_artifact_inventory_sha256
            ),
            "on_retention_inventory_sha256": (
                receipt.on_retention_inventory_sha256
            ),
            "cache_run_manifest_file_sha256": (
                receipt.cache_run_manifest_file_sha256
            ),
            "factor_bundle_manifest_sha256": (
                receipt.factor_bundle_manifest_sha256
            ),
            "window_count": receipt.window_count,
            "total_final_record_count": receipt.total_final_record_count,
            "maximum_process_mapped_bytes": (
                receipt.maximum_process_mapped_bytes
            ),
            "maximum_window_peak_mapped_bytes": (
                receipt.maximum_window_peak_mapped_bytes
            ),
            "maximum_window_peak_handle_count": (
                receipt.maximum_window_peak_handle_count
            ),
            "total_batch_count": receipt.total_batch_count,
            "total_opened_cache_count": receipt.total_opened_cache_count,
        },
    )
