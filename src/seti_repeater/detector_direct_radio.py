"""Direct-table downstream detector adapter, separate from detector_m43u.

All numerical mask, retention, OFF, receiver-alias and rank kernels are reused.
Only ancestry selection is new: it is supplied by DirectFactorContract and no
legacy two-column FactorBasis is constructed or accepted.
"""
import hashlib
import numpy as np

from . import search_v0p6 as core
from .adjacent_v0p6 import _finalize_single_adjacent_off_result
from .alias_v0p6 import match_receiver_frame_aliases
from .detector_m43u import checked_vectors, digest
from .mask_m43u import build_mask, validate_binding
from .significance_v0p6 import evaluate_global_rank_significance

SCHEMA = "radio-direct-downstream-diagnostic-v1"


def _ledger(context, kind, threshold, widths):
    c, f = context, context.factor_contract
    return core.ExhaustiveRetentionLedger(
        window_id=c.window, scan_kind=kind, grid=c.grid,
        threshold_certificate=threshold, maximum_records=c.maximum_records,
        template_bank=f.bank, spectral_widths=widths,
        activity_subsets=core.M37_ACTIVITY_SUBSETS,
        expected_template_bank_sha256=core.template_bank_sha256(f.bank),
        factor_basis_sha256=f.factors.identity,
        factor_basis_labels_sha256=f.labels_sha256,
        scan_inventory_sha256=core.scan_inventory_sha256(c.scans),
        factor_row_selection_sha256=f.row_selection_sha256(kind),
        factor_table_sha256=f.factor_table_sha256, epoch_count=3,
        minimum_active_epoch_snr=3., stack_statistic="sum",
        maximum_record_canonical_bytes=16384,
        maximum_evidence_canonical_bytes=128_000_000)


def calibrate(context, store, shifts, minimum_shift_bins, progress=lambda message: None):
    context.validate(); f = context.factor_contract
    widths = core.M37_SPECTRAL_WIDTHS
    acc = core.CalibrationAccumulator.create(
        window_id=context.window, score_bin_count=context.grid.score_bin_count,
        template_count=len(f.bank),
        template_bank_sha256_value=core.template_bank_sha256(f.bank),
        factor_basis_sha256_value=f.factors.identity,
        factor_basis_labels_sha256_value=f.labels_sha256,
        scan_inventory_sha256_value=core.scan_inventory_sha256(context.scans),
        factor_row_selection_sha256_value=f.row_selection_sha256("on"),
        factor_table_sha256_value=f.factor_table_sha256,
        spectral_widths=widths, activity_subsets=core.M37_ACTIVITY_SUBSETS,
        minimum_active_epoch_snr=3., stack_statistic="sum",
        scramble_shifts=shifts, minimum_shift_bins=minimum_shift_bins,
        expected_scramble_sha256=core.scramble_table_sha256(shifts))
    for t in range(len(f.bank)):
        arrays = {w: checked_vectors(store, "on", t, w, context.grid) for w in widths}
        mask = build_mask(arrays.__getitem__, "neighbor9")[:, context.grid.score_slice]
        for wi, width in enumerate(widths):
            core.update_calibration(acc, arrays[width][:, context.grid.score_slice],
                                    template_index=t, width_index=wi, exclusion_mask=mask)
        progress(f"direct calibration template {t+1}/{len(f.bank)}")
    return acc, acc.finalize()


def execute(context, store, calibration_binding, calibration, threshold,
            receiver_factory, progress=lambda message: None):
    context.validate(); f = context.factor_contract; grid = context.grid
    validate_binding(calibration_binding, "neighbor9", calibration, threshold)
    widths = core.M37_SPECTRAL_WIDTHS
    expected = {(kind, t, w) for kind in ("on", "off")
                for t in range(len(f.bank)) for w in widths}
    if set(store.expected_ids) != expected:
        raise ValueError("direct score store inventory incomplete or contains extras")
    ids = dict(store.expected_ids)
    def get(kind, t, width):
        return checked_vectors(store, kind, t, width, grid, ids[kind, t, width])
    root = digest([[kind, t, w, ids[kind, t, w]] for kind, t, w in sorted(expected)])
    core.validate_threshold_certificate(threshold)
    if threshold.global_null_maxima_sha256 != core.float64_vector_sha256(calibration.null_maxima):
        raise ValueError("direct frozen threshold/null mismatch")

    masks = {}; mask_hashes = {}; mask_counts = {}
    for kind in ("on", "off"):
        for t in range(len(f.bank)):
            arrays = {w: get(kind, t, w) for w in widths}
            mask = build_mask(arrays.__getitem__, "neighbor9")[:, grid.score_slice]
            frozen = np.frombuffer(np.ascontiguousarray(mask).tobytes(), dtype=bool).reshape(mask.shape)
            masks[kind, t] = frozen
            mask_hashes[f"{kind}:{t}"] = hashlib.sha256(frozen.tobytes()).hexdigest()
            mask_counts[f"{kind}:{t}"] = int(frozen.sum())

    ledgers = {kind: _ledger(context, kind, threshold, widths) for kind in ("on", "off")}
    records = {}; certs = {}
    for kind in ("on", "off"):
        for t, template in enumerate(f.bank):
            for wi, width in enumerate(widths):
                values = get(kind, t, width)[:, grid.score_slice]
                for subset in core.M37_ACTIVITY_SUBSETS:
                    ledgers[kind].add_hypothesis(values, subset, template=template,
                                                 width_index=wi, width_channels=width,
                                                 exclusion_mask=masks[kind, t])
        records[kind] = ledgers[kind].finalize()
        certs[kind] = ledgers[kind].certificate()
        progress(f"{kind}: {len(records[kind])} direct diagnostic members")

    off_factors = f.matrix_for_kind("off")
    on_factors = f.matrix_for_kind("on")
    matched = core.match_retained_off_tracks(
        records["on"], certs["on"], records["off"], certs["off"], grid,
        off_factors, window_order=(context.window,), tolerance_hz=20.,
        maximum_bucket_entries=context.maximum_records,
        maximum_exact_candidate_visits=5_000_000, template_bank=f.bank)
    on_labels = tuple(context.scans[i]["label"] for i in core.m37_scan_indices_for_kind(context.scans, "on"))
    off_labels = tuple(context.scans[i]["label"] for i in core.m37_scan_indices_for_kind(context.scans, "off"))
    measured = {}; queries = []; plans = []; cache_inventory = []
    for width in widths:
        for epoch, label in enumerate(off_labels):
            payload = hashlib.sha256()
            for t in range(len(f.bank)):
                payload.update(np.ascontiguousarray(get("off", t, width)[epoch, grid.score_slice]).tobytes())
            plan = {"schema": "radio-direct-integrated-off-vector-cache-v1",
                    "scan": label, "width": width, "input_root": root,
                    "direct_factor_contract_sha256": f.identity,
                    "grid_sha256": core.proxy_carrier_grid_sha256(grid),
                    "template_count": len(f.bank),
                    "payload_layout": "template-major little-endian float32 score carriers"}
            plans.append(plan)
            cache_inventory.append({"spectral_width_channels": width,
                "epoch_zero_based": epoch, "scan_label": label,
                "cache_plan_sha256": digest(plan),
                "cache_payload_sha256": payload.hexdigest()})
    for ordinal, record in enumerate(records["on"]):
        t = record["template_index"]; width = record["spectral_width_channels"]
        q = record["proxy_carrier_index"]
        values = get("off", t, width)[:, grid.score_slice]
        for epoch in record["active_epochs_zero_based"]:
            measured[ordinal, epoch] = np.float32(values[epoch, q])
            queries.append({"record_id": record["record_id"],
                "epoch_zero_based": epoch, "paired_off_scan_label": off_labels[epoch],
                "template_index": t, "spectral_width_index": record["spectral_width_index"],
                "proxy_carrier_index": q})
    adjacent = _finalize_single_adjacent_off_result(
        cert=certs["on"], records=records["on"], measured=measured,
        on_labels=on_labels, off_labels=off_labels, floor=5.5,
        cache_inventory=cache_inventory, query_inventory=queries,
        factor_basis=None, scan_definitions=context.scans,
        maximum_records=context.maximum_records, maximum_queries=3*context.maximum_records,
        maximum_evidence_canonical_bytes=128_000_000,
        off_factor_row_selection_sha256_value=f.row_selection_sha256("off"))

    signatures, receiver_receipt = receiver_factory(records["on"], f.bank)
    if set(signatures) != {r["record_id"] for r in records["on"]}:
        raise ValueError("direct receiver query inventory differs")
    if receiver_receipt["signatures_sha256"] != digest(signatures):
        raise ValueError("direct receiver signature receipt changed")
    aliases = match_receiver_frame_aliases(
        matched["records"], certs["on"], grid, on_factors, signatures,
        off_match_certificate=matched["certificate"],
        single_adjacent_off_evidence=adjacent["evidence"],
        single_adjacent_off_certificate=adjacent["certificate"],
        expected_off_match_certificate_sha256=matched["certificate"]["off_match_certificate_sha256"],
        expected_single_adjacent_off_certificate_sha256=adjacent["certificate"]["single_adjacent_off_certificate_sha256"],
        window_order=(context.window,), track_tolerance_hz=20., local_half_width_hz=100.,
        local_peak_snr_floor=5.5, minimum_shared_active_epochs=2,
        maximum_records=context.maximum_records, maximum_bucket_entries=context.maximum_records,
        maximum_identity_track_comparisons=5_000_000,
        maximum_distinct_candidate_visits_per_window=5_000_000,
        template_bank=f.bank)
    rank = evaluate_global_rank_significance(records["on"], certs["on"], threshold,
                                             calibration.null_maxima, grid, f.bank)
    rank_by_id = {x["record_id"]: x for x in rank["evidence"]}
    if set(rank_by_id) != {x["record_id"] for x in aliases["records"]}:
        raise ValueError("direct final-stage record identities disagree")
    decisions = []
    for record in aliases["records"]:
        template = f.bank[record["template_index"]]
        decisions.append({"record_id": record["record_id"],
            "direct_template_index": template["template_index"],
            "projected_scale": template["projected_scale"],
            "phase_cycles": template["phase_cycles"],
            "physical_disposition": record["member_disposition"],
            "passes_evaluated_physical_vetoes": record["member_disposition"] == "pending_receiver_alias_evaluation",
            "inclusive_rank_p": rank_by_id[record["record_id"]]["inclusive_global_rank_p"],
            "meets_diagnostic_rank_cut": rank_by_id[record["record_id"]]["scientifically_eligible"],
            "scientific_candidate": False})
    result = {"schema": SCHEMA, "purpose": "direct-factor downstream engineering",
        "factor_provider_kind": "literal-midpoint-table-not-factor-basis",
        "direct_factor_contract_sha256": f.identity,
        "legacy_certificate_slot_mapping": f.record()["legacy_certificate_slot_mapping"],
        "mask_policy": "neighbor9", "calibration_binding": calibration_binding,
        "input_inventory_sha256": root,
        "catalogue_sha256": core.template_bank_sha256(f.bank),
        "factor_table_sha256": f.factor_table_sha256,
        "mask_sha256s": mask_hashes, "masked_cell_counts": mask_counts,
        "null_maxima": calibration.null_maxima.tolist(), "null_count": len(calibration.null_maxima),
        "threshold": threshold.as_record(), "retained": records,
        "retention_certificates": certs, "off_track": matched,
        "adjacent_off": adjacent, "off_vector_cache_plans": plans,
        "receiver_signatures": signatures, "receiver_receipt": receiver_receipt,
        "receiver_alias": aliases, "rank": rank, "decisions": decisions,
        "scientific_candidate_selection_authorized": False,
        "fresh_null_calibration": True, "native_injection_recovery_measured": False}
    result["result_sha256"] = digest(result)
    return result
