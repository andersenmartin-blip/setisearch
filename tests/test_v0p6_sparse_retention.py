"""Synthetic sparse-retention and physical-disposition KATs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core
from seti_repeater.completeness_v0p6 import (
    M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
)
from seti_repeater.significance_v0p6 import (
    evaluate_global_rank_significance,
    validate_global_rank_significance,
)
from seti_repeater.alias_v0p6 import match_receiver_frame_aliases
from seti_repeater.sparse_replay_v0p6 import (
    SPARSE_LOCAL_KAT_GATHERS_SHA256,
    SPARSE_LOCAL_KAT_ISOLATED_MASKS_SHA256,
    SPARSE_LOCAL_KAT_MASKS_SHA256,
    SPARSE_LOCAL_KAT_PLAN_INVENTORY_SHA256,
    SPARSE_LOCAL_KAT_RECEIPT_SHA256,
    SPARSE_LOCAL_KAT_SCORES_SHA256,
    SPARSE_LOCAL_KAT_FIXTURE_SHA256,
    SPARSE_LOCAL_REFERENCE_STATUS,
    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
    SPARSE_LOCAL_REQUIRED_COVERAGE,
    SPARSE_LOCAL_REQUIRED_WIDTHS,
    SPARSE_RETENTION_REFERENCE_STATUS,
    SPARSE_PHYSICAL_REFERENCE_STATUS,
    SparseLocalReferenceKATReceipt,
    build_sparse_retention_reference_kat,
    make_local_score_index_set,
    seal_sparse_physical_reference_kat_receipt,
    seal_sparse_retention_off_rank_reference_kat_receipt,
    validate_sparse_physical_reference_kat_receipt,
    validate_sparse_retention_off_rank_reference_kat_receipt,
    validate_sparse_retention_reference_kat_product,
)


def _phase1_receipt() -> SparseLocalReferenceKATReceipt:
    return SparseLocalReferenceKATReceipt(
        status=SPARSE_LOCAL_REFERENCE_STATUS,
        fixture_sha256=SPARSE_LOCAL_KAT_FIXTURE_SHA256,
        plan_inventory_sha256=SPARSE_LOCAL_KAT_PLAN_INVENTORY_SHA256,
        covered_contracts=SPARSE_LOCAL_REQUIRED_COVERAGE,
        template_count=3,
        score_bin_count=41,
        epoch_count=3,
        spectral_widths=SPARSE_LOCAL_REQUIRED_WIDTHS,
        activity_subsets=SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
        gather_array_count=72,
        isolated_mask_array_count=24,
        mask_array_count=3,
        score_array_count=96,
        dense_gathers_sha256=SPARSE_LOCAL_KAT_GATHERS_SHA256,
        local_gathers_sha256=SPARSE_LOCAL_KAT_GATHERS_SHA256,
        dense_isolated_masks_sha256=SPARSE_LOCAL_KAT_ISOLATED_MASKS_SHA256,
        local_isolated_masks_sha256=SPARSE_LOCAL_KAT_ISOLATED_MASKS_SHA256,
        dense_masks_sha256=SPARSE_LOCAL_KAT_MASKS_SHA256,
        local_masks_sha256=SPARSE_LOCAL_KAT_MASKS_SHA256,
        dense_scores_sha256=SPARSE_LOCAL_KAT_SCORES_SHA256,
        local_scores_sha256=SPARSE_LOCAL_KAT_SCORES_SHA256,
        gather_bits_equal=True,
        mask_bytes_equal=True,
        score_bits_equal=True,
        production_equivalence_claimed=False,
        global_retention_equivalence_proven=False,
        receiver_alias_equivalence_proven=False,
        off_disposition_equivalence_proven=False,
        rank_p_equivalence_proven=False,
        production_receipt_ancestry_proven=False,
        production_feasibility_gate_changed=False,
        receipt_sha256=SPARSE_LOCAL_KAT_RECEIPT_SHA256,
    )


class SparseRetentionOffRankReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase1 = _phase1_receipt()
        cls.grid = core.make_proxy_carrier_grid(0.0005, 1.0, 20, 64)
        cls.bank = core.make_line_template_bank(
            count=3, expected_sha256=None
        )
        cls.null_maxima = np.asarray(
            [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            dtype="<f8",
        )
        cls.threshold = cls._make_threshold()
        cls.on_vectors, cls.on_masks = cls._make_on_arrays()
        cls.off_vectors, cls.off_masks = cls._make_off_arrays()
        cls.on_product, cls.on_records, cls.on_certificate, cls.on_dense_scores = (
            cls._make_product("on", cls.on_vectors, cls.on_masks)
        )
        (
            cls.off_product,
            cls.off_records,
            cls.off_certificate,
            cls.off_dense_scores,
        ) = cls._make_product("off", cls.off_vectors, cls.off_masks)
        cls.off_factors = np.asarray(
            [
                [1.0, 1.0, 1.0],
                [2.0, 2.0, 2.0],
                [4.0, 4.0, 4.0],
            ],
            dtype="<f8",
        )
        cls.dense_off_result = cls._match_off(
            cls.on_records, cls.off_records
        )
        cls.local_off_result = cls._match_off(
            cls.on_product.records(), cls.off_product.records()
        )
        cls.dense_rank_result = evaluate_global_rank_significance(
            cls.on_records,
            cls.on_certificate,
            cls.threshold,
            cls.null_maxima,
            cls.grid,
            cls.bank,
        )
        cls.local_rank_result = evaluate_global_rank_significance(
            cls.on_product.records(),
            cls.on_certificate,
            cls.threshold,
            cls.null_maxima,
            cls.grid,
            cls.bank,
        )
        cls.receipt = seal_sparse_retention_off_rank_reference_kat_receipt(
            phase1_receipt=cls.phase1,
            on_product=cls.on_product,
            off_product=cls.off_product,
            on_retention_certificate=cls.on_certificate,
            off_retention_certificate=cls.off_certificate,
            threshold_certificate=cls.threshold,
            global_null_maxima=cls.null_maxima,
            grid=cls.grid,
            template_bank=cls.bank,
            off_factor_matrix=cls.off_factors,
            window_order=("synthetic-sparse-phase2",),
            off_tolerance_hz=2.1,
            maximum_off_bucket_entries=10_000,
            maximum_off_exact_candidate_visits=1_000_000,
            dense_off_result=cls.dense_off_result,
            local_off_result=cls.local_off_result,
            dense_rank_result=cls.dense_rank_result,
            local_rank_result=cls.local_rank_result,
            scientific_p_ceiling=0.4,
        )
        cls.dense_adjacent_result = cls._make_adjacent_result(cls.on_records)
        cls.local_adjacent_result = cls._make_adjacent_result(
            cls.on_product.records()
        )
        cls.on_alias_factors = cls._make_alias_factors()
        cls.receiver_signatures = cls._make_receiver_signatures(
            cls.on_records
        )
        cls.dense_alias_result = cls._match_alias(
            cls.dense_off_result,
            cls.dense_adjacent_result,
        )
        cls.local_alias_result = cls._match_alias(
            cls.local_off_result,
            cls.local_adjacent_result,
        )
        cls.physical_receipt = cls._seal_physical()

    @classmethod
    def _make_threshold(cls):
        shifts = core.make_scramble_shift_table(
            cls.null_maxima.size,
            3,
            cls.grid.score_bin_count,
            seed=37_060_621,
            minimum_shift_bins=1,
        )
        calibration = core.CalibrationAccumulator.create(
            window_id="synthetic-sparse-phase2",
            score_bin_count=cls.grid.score_bin_count,
            template_count=len(cls.bank),
            template_bank_sha256_value=core.template_bank_sha256(cls.bank),
            factor_basis_sha256_value="1" * 64,
            factor_basis_labels_sha256_value="2" * 64,
            scan_inventory_sha256_value="3" * 64,
            factor_row_selection_sha256_value="4" * 64,
            factor_table_sha256_value="5" * 64,
            spectral_widths=SPARSE_LOCAL_REQUIRED_WIDTHS,
            activity_subsets=SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
            minimum_active_epoch_snr=3.0,
            stack_statistic="minimum_epoch",
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=core.scramble_table_sha256(shifts),
        )
        calibration_vectors = np.full(
            (3, cls.grid.score_bin_count), 4.0, dtype="<f4"
        )
        for template_index in range(len(cls.bank)):
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                core.update_calibration(
                    calibration,
                    calibration_vectors,
                    template_index=template_index,
                    width_index=width_index,
                    exclusion_mask=None,
                )
        calibration.null_maxima[:] = cls.null_maxima
        calibration._checkpoint_state()
        calibration.finalize()
        return core.calibrated_threshold(
            (calibration,),
            expected_window_ids=("synthetic-sparse-phase2",),
            reference_floor=50.0,
            quantile=0.0,
            scientific_p_ceiling=0.4,
        )

    @classmethod
    def _make_on_arrays(cls):
        vectors: dict[tuple[int, int], np.ndarray] = {}
        masks: dict[int, np.ndarray] = {
            template: np.zeros((3, cls.grid.score_bin_count), dtype=bool)
            for template in range(len(cls.bank))
        }
        locations = {0: (3, 4, 5, 6), 1: (15, 16), 2: (30, 31)}
        for template, mask in masks.items():
            mask[:, locations[template][-1]] = True
        for template_index in range(len(cls.bank)):
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                array = np.full(
                    (3, cls.grid.score_bin_count),
                    np.float32(4.0 + 0.01 * template_index),
                    dtype="<f4",
                )
                for location in locations[template_index]:
                    amplitude = np.float32(
                        65.0 + 5.0 * width_index + 3.0 * template_index
                    )
                    array[:, location] = amplitude
                if template_index == 0 and width_index == 0:
                    exact = np.float32(50.0) / np.float32(math.sqrt(2.0))
                    equal = np.float32(55.0) / np.float32(math.sqrt(2.0))
                    array[:, 3] = exact
                    array[:, 4] = equal
                    array[:, 5] = np.float32(100.0)
                vectors[(template_index, width_index)] = array
        return vectors, masks

    @classmethod
    def _make_off_arrays(cls):
        vectors: dict[tuple[int, int], np.ndarray] = {}
        masks: dict[int, np.ndarray] = {}
        for template_index in range(len(cls.bank)):
            if template_index == 0:
                masks[template_index] = np.array(
                    cls.on_masks[template_index], copy=True, order="C"
                )
            elif template_index == 1:
                masks[template_index] = np.ascontiguousarray(
                    np.roll(cls.on_masks[template_index], 1, axis=1),
                    dtype=bool,
                )
            else:
                masks[template_index] = np.zeros(
                    (3, cls.grid.score_bin_count), dtype=bool
                )
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                if template_index == 0:
                    array = np.array(
                        cls.on_vectors[(template_index, width_index)],
                        copy=True,
                        order="C",
                    )
                elif template_index == 1:
                    array = np.ascontiguousarray(
                        np.roll(
                            cls.on_vectors[(template_index, width_index)],
                            1,
                            axis=1,
                        ),
                        dtype="<f4",
                    )
                else:
                    array = np.full(
                        (3, cls.grid.score_bin_count), 2.0, dtype="<f4"
                    )
                vectors[(template_index, width_index)] = array
        return vectors, masks

    @classmethod
    def _dense_scores(cls, vectors, masks):
        result = {}
        for template_index in range(len(cls.bank)):
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS:
                    result[(template_index, width_index, subset)] = (
                        np.ascontiguousarray(
                            core.stack_hypothesis(
                                vectors[(template_index, width_index)],
                                subset,
                                minimum_active_epoch_snr=3.0,
                                stack_statistic="minimum_epoch",
                                exclusion_mask=masks[template_index],
                            ),
                            dtype="<f4",
                        )
                    )
        return result

    @classmethod
    def _make_product(cls, scan_kind, vectors, masks):
        ledger = core.ExhaustiveRetentionLedger(
            window_id="synthetic-sparse-phase2",
            scan_kind=scan_kind,
            grid=cls.grid,
            threshold_certificate=cls.threshold,
            maximum_records=10_000,
            template_bank=cls.bank,
            spectral_widths=SPARSE_LOCAL_REQUIRED_WIDTHS,
            activity_subsets=SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
            expected_template_bank_sha256=None,
            factor_basis_sha256="1" * 64,
            factor_basis_labels_sha256="2" * 64,
            scan_inventory_sha256="3" * 64,
            factor_row_selection_sha256=(
                "4" * 64 if scan_kind == "on" else "6" * 64
            ),
            factor_table_sha256="5" * 64,
            epoch_count=3,
            minimum_active_epoch_snr=3.0,
            stack_statistic="minimum_epoch",
        )
        for template_index, template in enumerate(cls.bank):
            for width_index, width in enumerate(
                SPARSE_LOCAL_REQUIRED_WIDTHS
            ):
                for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS:
                    ledger.add_hypothesis(
                        vectors[(template_index, width_index)],
                        subset,
                        template=template,
                        width_index=width_index,
                        width_channels=width,
                        exclusion_mask=masks[template_index],
                    )
        records = ledger.finalize()
        certificate = ledger.certificate()
        dense_scores = cls._dense_scores(vectors, masks)
        candidates = []
        for template_index in range(len(cls.bank)):
            selected = {0}
            selected.update(np.flatnonzero(masks[template_index].any(axis=0)))
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS:
                    selected.update(
                        np.flatnonzero(
                            dense_scores[
                                (template_index, width_index, subset)
                            ]
                            >= 50.0
                        )
                    )
            candidates.append(
                make_local_score_index_set(
                    cls.grid.score_bin_count, sorted(selected)
                )
            )
        local_vectors = {
            key: np.ascontiguousarray(
                array[:, candidates[key[0]].indices], dtype="<f4"
            )
            for key, array in vectors.items()
        }
        local_masks = {
            template: np.ascontiguousarray(
                masks[template][:, candidates[template].indices], dtype=bool
            )
            for template in range(len(cls.bank))
        }
        fixture_record = {
            "artifact_type": "v0p6-sparse-retention-off-rank-kat-v1",
            "window_id": "synthetic-sparse-phase2",
            "score_bin_count": cls.grid.score_bin_count,
            "template_count": len(cls.bank),
            "widths": list(SPARSE_LOCAL_REQUIRED_WIDTHS),
            "activity_subsets": [
                list(item) for item in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
            ],
            "threshold_snr": 50.0,
            "production_data_used": False,
        }
        fixture_sha256 = hashlib.sha256(
            core.canonical_json_bytes(fixture_record)
        ).hexdigest()
        product = build_sparse_retention_reference_kat(
            fixture_sha256=fixture_sha256,
            phase1_receipt=cls.phase1,
            dense_records=records,
            retention_certificate=certificate,
            grid=cls.grid,
            template_bank=cls.bank,
            candidate_indices=candidates,
            local_epoch_vectors=local_vectors,
            local_masks=local_masks,
            dense_scores=dense_scores,
        )
        return product, records, certificate, dense_scores

    @classmethod
    def _match_off(cls, on_records, off_records):
        return core.match_retained_off_tracks(
            on_records,
            cls.on_certificate,
            off_records,
            cls.off_certificate,
            cls.grid,
            cls.off_factors,
            window_order=("synthetic-sparse-phase2",),
            tolerance_hz=2.1,
            maximum_bucket_entries=10_000,
            maximum_exact_candidate_visits=1_000_000,
            template_bank=cls.bank,
        )

    @classmethod
    def _make_adjacent_result(cls, records):
        detached_records = json.loads(core.canonical_json_bytes(list(records)))
        evidence = []
        queries = []
        for record in detached_records:
            active = [
                int(epoch) for epoch in record["active_epochs_zero_based"]
            ]
            measurements = []
            matching = []
            for position, epoch in enumerate(active):
                veto = (
                    int(record["template_index"]) == 2
                    and int(record["spectral_width_index"]) == 0
                    and position == 0
                )
                snr = 6.0 if veto else 1.0 + 0.1 * epoch
                if veto:
                    matching.append(epoch)
                measurements.append(
                    {
                        "epoch_zero_based": epoch,
                        "paired_on_scan_label": f"epoch{epoch + 1}_on",
                        "paired_off_scan_label": f"epoch{epoch + 1}_off",
                        "snr": snr,
                        "meets_single_epoch_floor": veto,
                    }
                )
                queries.append(
                    {
                        "record_id": record["record_id"],
                        "epoch_zero_based": epoch,
                        "paired_off_scan_label": f"epoch{epoch + 1}_off",
                        "template_index": int(record["template_index"]),
                        "spectral_width_index": int(
                            record["spectral_width_index"]
                        ),
                        "proxy_carrier_index": int(
                            record["proxy_carrier_index"]
                        ),
                    }
                )
            evidence.append(
                {
                    "record_id": record["record_id"],
                    "template_index": int(record["template_index"]),
                    "spectral_width_index": int(
                        record["spectral_width_index"]
                    ),
                    "spectral_width_channels": int(
                        record["spectral_width_channels"]
                    ),
                    "proxy_carrier_index": int(
                        record["proxy_carrier_index"]
                    ),
                    "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
                    "active_epochs_zero_based": active,
                    "single_epoch_snr_floor": 5.5,
                    "comparison": (
                        "native_gathered_snr >= single_epoch_snr_floor"
                    ),
                    "exact_same_q_template_width": True,
                    "exclusion_mask_applied": False,
                    "frequency_neighborhood_hz": 0.0,
                    "paired_adjacent_off_measurements": measurements,
                    "matching_active_epochs_zero_based": matching,
                    "maximum_active_epoch_snr": max(
                        item["snr"] for item in measurements
                    ),
                    "vetoed": bool(matching),
                    "recommended_member_disposition": (
                        "rfi_veto_single_adjacent_off"
                        if matching
                        else "pending_receiver_alias_evaluation"
                    ),
                }
            )
        cache_inventory = []
        for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
            for epoch in range(3):
                cache_key = {
                    "artifact_type": "synthetic-adjacent-cache-oracle-v1",
                    "spectral_width_channels": width,
                    "epoch_zero_based": epoch,
                }
                cache_inventory.append(
                    {
                        "spectral_width_channels": width,
                        "epoch_zero_based": epoch,
                        "scan_label": f"epoch{epoch + 1}_off",
                        "cache_plan_sha256": hashlib.sha256(
                            core.canonical_json_bytes(
                                {**cache_key, "identity": "plan"}
                            )
                        ).hexdigest(),
                        "cache_payload_sha256": hashlib.sha256(
                            core.canonical_json_bytes(
                                {**cache_key, "identity": "payload"}
                            )
                        ).hexdigest(),
                    }
                )
        evidence_bytes = core.canonical_json_bytes(evidence)
        certificate = {
            "window_id": cls.on_certificate["window_id"],
            "contract": "exact paired adjacent OFF q/template/width native gather",
            "comparison": "any active-epoch S/N >= single_epoch_snr_floor",
            "single_epoch_snr_floor": 5.5,
            "exact_same_q_template_width": True,
            "exclusion_mask_applied": False,
            "frequency_neighborhood_hz": 0.0,
            "on_retention_certificate_sha256": cls.on_certificate[
                "retention_certificate_sha256"
            ],
            "on_records_sha256": cls.on_certificate["records_sha256"],
            "proxy_grid_sha256": cls.on_certificate["proxy_grid_sha256"],
            "template_bank_sha256": cls.on_certificate[
                "template_bank_sha256"
            ],
            "factor_basis_sha256": cls.on_certificate[
                "factor_basis_sha256"
            ],
            "factor_basis_labels_sha256": cls.on_certificate[
                "factor_basis_labels_sha256"
            ],
            "scan_inventory_sha256": cls.on_certificate[
                "scan_inventory_sha256"
            ],
            "on_factor_row_selection_sha256": cls.on_certificate[
                "factor_row_selection_sha256"
            ],
            "off_factor_row_selection_sha256": "7" * 64,
            "factor_table_sha256": cls.on_certificate[
                "factor_table_sha256"
            ],
            "cache_inventory": cache_inventory,
            "cache_inventory_sha256": hashlib.sha256(
                core.canonical_json_bytes(cache_inventory)
            ).hexdigest(),
            "cache_count": len(cache_inventory),
            "query_inventory_sha256": hashlib.sha256(
                core.canonical_json_bytes(queries)
            ).hexdigest(),
            "query_count": len(queries),
            "maximum_queries": len(queries),
            "input_record_count": len(evidence),
            "evidence_record_count": len(evidence),
            "maximum_records": len(evidence),
            "maximum_evidence_record_canonical_bytes": cls.on_certificate[
                "maximum_record_canonical_bytes"
            ],
            "maximum_evidence_canonical_bytes": 10_000_000,
            "evidence_canonical_bytes": len(evidence_bytes),
            "all_input_records_evaluated_exactly_once": True,
            "all_active_epoch_queries_evaluated_exactly_once": True,
            "truncation_permitted": False,
            "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        }
        certificate["single_adjacent_off_certificate_sha256"] = (
            hashlib.sha256(
                core.canonical_json_bytes(certificate)
            ).hexdigest()
        )
        return {"evidence": evidence, "certificate": certificate}

    @classmethod
    def _make_alias_factors(cls):
        carriers = {
            template: sorted(
                {
                    float(record["proxy_carrier_hz"])
                    for record in cls.on_records
                    if int(record["template_index"]) == template
                }
            )
            for template in range(3)
        }
        target_template_one_hz = carriers[0][0] + 21.0
        factors = np.asarray(
            [
                [1.0, 1.0, 1.0],
                [
                    target_template_one_hz / carriers[1][0],
                    target_template_one_hz / carriers[1][0],
                    target_template_one_hz / carriers[1][0],
                ],
                [1.3, 1.3, 1.3],
            ],
            dtype="<f8",
        )
        return factors

    @classmethod
    def _make_receiver_signatures(cls, records):
        result = {}
        for record in records:
            low_snr_control = (
                int(record["template_index"]) == 2
                and int(record["spectral_width_index"]) == 7
            )
            entries = []
            for epoch in record["active_epochs_zero_based"]:
                predicted_mhz = float(record["proxy_carrier_mhz"])
                peak_mhz = 0.0005
                entries.append(
                    {
                        "epoch_zero_based": int(epoch),
                        "predicted_mid_mhz": predicted_mhz,
                        "peak_frequency_mhz": peak_mhz,
                        "peak_snr": 4.0 if low_snr_control else 8.0,
                        "offset_from_prediction_hz": (
                            peak_mhz - predicted_mhz
                        )
                        * 1e6,
                    }
                )
            result[str(record["record_id"])] = entries
        return result

    @classmethod
    def _match_alias(cls, off_result, adjacent_result):
        return match_receiver_frame_aliases(
            off_result["records"],
            cls.on_certificate,
            cls.grid,
            cls.on_alias_factors,
            cls.receiver_signatures,
            off_match_certificate=off_result["certificate"],
            single_adjacent_off_evidence=adjacent_result["evidence"],
            single_adjacent_off_certificate=adjacent_result["certificate"],
            expected_off_match_certificate_sha256=off_result[
                "certificate"
            ]["off_match_certificate_sha256"],
            expected_single_adjacent_off_certificate_sha256=(
                adjacent_result["certificate"][
                    "single_adjacent_off_certificate_sha256"
                ]
            ),
            window_order=("synthetic-sparse-phase2",),
            track_tolerance_hz=20.0,
            local_half_width_hz=100.0,
            local_peak_snr_floor=5.5,
            minimum_shared_active_epochs=2,
            maximum_records=1_000,
            maximum_bucket_entries=100_000,
            maximum_identity_track_comparisons=100_000,
            maximum_distinct_candidate_visits_per_window=100_000,
            template_bank=cls.bank,
            expected_on_certificate_sha256=cls.on_certificate[
                "retention_certificate_sha256"
            ],
        )

    @classmethod
    def _seal_physical(cls, **overrides):
        arguments = {
            "phase2_receipt": cls.receipt,
            "on_product": cls.on_product,
            "on_retention_certificate": cls.on_certificate,
            "off_result": cls.local_off_result,
            "dense_adjacent_result": cls.dense_adjacent_result,
            "local_adjacent_result": cls.local_adjacent_result,
            "dense_alias_result": cls.dense_alias_result,
            "local_alias_result": cls.local_alias_result,
            "receiver_signatures": cls.receiver_signatures,
            "grid": cls.grid,
            "template_bank": cls.bank,
            "on_factor_matrix": cls.on_alias_factors,
            "window_order": ("synthetic-sparse-phase2",),
            "track_tolerance_hz": 20.0,
            "local_half_width_hz": 100.0,
            "local_peak_snr_floor": 5.5,
            "minimum_shared_active_epochs": 2,
            "maximum_records": 1_000,
            "maximum_bucket_entries": 100_000,
            "maximum_identity_track_comparisons": 100_000,
            "maximum_distinct_candidate_visits_per_window": 100_000,
        }
        arguments.update(overrides)
        return seal_sparse_physical_reference_kat_receipt(**arguments)

    def test_phase2_known_answer_is_exact_and_claim_limited(self):
        validate_sparse_retention_reference_kat_product(self.on_product)
        validate_sparse_retention_reference_kat_product(self.off_product)
        validate_sparse_retention_off_rank_reference_kat_receipt(self.receipt)
        self.assertEqual(self.receipt.status, SPARSE_RETENTION_REFERENCE_STATUS)
        self.assertTrue(self.receipt.global_retention_equivalence_proven)
        self.assertTrue(self.receipt.off_disposition_equivalence_proven)
        self.assertTrue(self.receipt.rank_p_equivalence_proven)
        self.assertFalse(self.receipt.adjacent_off_equivalence_proven)
        self.assertFalse(self.receipt.receiver_alias_equivalence_proven)
        self.assertFalse(self.receipt.production_receipt_ancestry_proven)
        self.assertFalse(self.receipt.complete_resource_envelope_proven)
        self.assertFalse(self.receipt.production_equivalence_claimed)
        self.assertFalse(self.receipt.production_feasibility_gate_changed)
        self.assertEqual(
            M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
            "mandatory-full-replay-benchmark-not-yet-passed",
        )
        self.assertGreater(self.on_product.omitted_score_cell_count, 0)
        self.assertLess(
            self.on_product.maximum_finite_omitted_score,
            self.on_product.threshold_snr,
        )
        self.assertEqual(self.on_records, self.on_product.records())
        self.assertEqual(self.off_records, self.off_product.records())
        self.assertEqual(self.dense_off_result, self.local_off_result)
        self.assertEqual(self.dense_rank_result, self.local_rank_result)
        self.assertTrue(all(count > 0 for _, count in self.receipt.off_disposition_counts))
        self.assertTrue(all(count > 0 for _, count in self.receipt.rank_p_relation_counts))
        self.assertEqual(
            self.on_product.product_sha256,
            "f0ed4bf233173bb4d783b40281776c83c3300443596183b4449268674a8a2915",
        )
        self.assertEqual(
            self.off_product.product_sha256,
            "2361c65ec692c6f32316283e599856ee55e9c76331f613c3319298adad52dbc2",
        )
        self.assertEqual(
            self.receipt.receipt_sha256,
            "1d70d05ac7b7888cf8071bcbe894bd67bae24fba87636c6c17945b982cf0ca09",
        )

    def test_rank_product_revalidates_against_exact_retention_ancestry(self):
        validated = validate_global_rank_significance(
            self.local_rank_result,
            self.on_product.records(),
            self.on_certificate,
            self.threshold,
            self.null_maxima,
            self.grid,
            self.bank,
        )
        self.assertEqual(validated, self.local_rank_result)

    def test_omitted_threshold_cell_and_local_bit_mutation_fail_closed(self):
        dense_scores = {
            key: np.array(value, copy=True, order="C")
            for key, value in self.on_dense_scores.items()
        }
        first_key = next(iter(dense_scores))
        dense_scores[first_key][1] = np.float32(50.0)
        candidates = []
        for template_index in range(len(self.bank)):
            selected = {0}
            selected.update(np.flatnonzero(self.on_masks[template_index].any(axis=0)))
            for width_index in range(len(SPARSE_LOCAL_REQUIRED_WIDTHS)):
                for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS:
                    selected.update(
                        np.flatnonzero(
                            self.on_dense_scores[
                                (template_index, width_index, subset)
                            ]
                            >= 50.0
                        )
                    )
            candidates.append(
                make_local_score_index_set(self.grid.score_bin_count, sorted(selected))
            )
        local_vectors = {
            key: np.ascontiguousarray(
                value[:, candidates[key[0]].indices], dtype="<f4"
            )
            for key, value in self.on_vectors.items()
        }
        local_masks = {
            template: np.ascontiguousarray(
                self.on_masks[template][:, candidates[template].indices],
                dtype=bool,
            )
            for template in range(len(self.bank))
        }
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "omitted an above-threshold"
        ):
            build_sparse_retention_reference_kat(
                fixture_sha256=self.on_product.fixture_sha256,
                phase1_receipt=self.phase1,
                dense_records=self.on_records,
                retention_certificate=self.on_certificate,
                grid=self.grid,
                template_bank=self.bank,
                candidate_indices=candidates,
                local_epoch_vectors=local_vectors,
                local_masks=local_masks,
                dense_scores=dense_scores,
            )

        changed_vectors = dict(local_vectors)
        changed = np.array(changed_vectors[(0, 0)], copy=True, order="C")
        changed[:, 0] = np.float32(9.0)
        changed_vectors[(0, 0)] = changed
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "local scores differ"
        ):
            build_sparse_retention_reference_kat(
                fixture_sha256=self.on_product.fixture_sha256,
                phase1_receipt=self.phase1,
                dense_records=self.on_records,
                retention_certificate=self.on_certificate,
                grid=self.grid,
                template_bank=self.bank,
                candidate_indices=candidates,
                local_epoch_vectors=changed_vectors,
                local_masks=local_masks,
                dense_scores=self.on_dense_scores,
            )

    def test_resealed_claim_and_downstream_mutations_fail_closed(self):
        forged = replace(
            self.receipt,
            receiver_alias_equivalence_proven=True,
            receipt_sha256="",
        )
        forged = replace(
            forged,
            receipt_sha256=hashlib.sha256(
                core.canonical_json_bytes(
                    forged.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "claim boundary"
        ):
            validate_sparse_retention_off_rank_reference_kat_receipt(forged)

        oversized = replace(
            self.on_product,
            full_score_cell_count=1_000_001,
            omitted_score_cell_count=(
                1_000_001 - self.on_product.local_score_cell_count
            ),
            product_sha256="",
        )
        oversized = replace(
            oversized,
            product_sha256=hashlib.sha256(
                core.canonical_json_bytes(
                    oversized.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "dimension inventory"
        ):
            validate_sparse_retention_reference_kat_product(oversized)

        changed_off = deepcopy(self.local_off_result)
        changed_off["records"][0]["member_disposition"] = (
            "pending_receiver_alias_evaluation"
        )
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "differs from the dense reference"
        ):
            seal_sparse_retention_off_rank_reference_kat_receipt(
                phase1_receipt=self.phase1,
                on_product=self.on_product,
                off_product=self.off_product,
                on_retention_certificate=self.on_certificate,
                off_retention_certificate=self.off_certificate,
                threshold_certificate=self.threshold,
                global_null_maxima=self.null_maxima,
                grid=self.grid,
                template_bank=self.bank,
                off_factor_matrix=self.off_factors,
                window_order=("synthetic-sparse-phase2",),
                off_tolerance_hz=2.1,
                maximum_off_bucket_entries=10_000,
                maximum_off_exact_candidate_visits=1_000_000,
                dense_off_result=self.dense_off_result,
                local_off_result=changed_off,
                dense_rank_result=self.dense_rank_result,
                local_rank_result=self.local_rank_result,
                scientific_p_ceiling=0.4,
            )

        changed_rank = deepcopy(self.local_rank_result)
        changed_rank["evidence"][0]["inclusive_global_rank_p"] = 0.0
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "differs from the dense reference"
        ):
            seal_sparse_retention_off_rank_reference_kat_receipt(
                phase1_receipt=self.phase1,
                on_product=self.on_product,
                off_product=self.off_product,
                on_retention_certificate=self.on_certificate,
                off_retention_certificate=self.off_certificate,
                threshold_certificate=self.threshold,
                global_null_maxima=self.null_maxima,
                grid=self.grid,
                template_bank=self.bank,
                off_factor_matrix=self.off_factors,
                window_order=("synthetic-sparse-phase2",),
                off_tolerance_hz=2.1,
                maximum_off_bucket_entries=10_000,
                maximum_off_exact_candidate_visits=1_000_000,
                dense_off_result=self.dense_off_result,
                local_off_result=self.local_off_result,
                dense_rank_result=self.dense_rank_result,
                local_rank_result=changed_rank,
                scientific_p_ceiling=0.4,
            )

    def test_phase3_known_answer_closes_adjacent_and_alias_only(self):
        validate_sparse_physical_reference_kat_receipt(
            self.physical_receipt
        )
        self.assertEqual(
            self.physical_receipt.status, SPARSE_PHYSICAL_REFERENCE_STATUS
        )
        self.assertTrue(
            self.physical_receipt.adjacent_off_equivalence_proven
        )
        self.assertTrue(
            self.physical_receipt.receiver_alias_equivalence_proven
        )
        self.assertTrue(
            self.physical_receipt.transitive_identity_component_proven
        )
        self.assertFalse(
            self.physical_receipt.production_receipt_ancestry_proven
        )
        self.assertFalse(
            self.physical_receipt.complete_resource_envelope_proven
        )
        self.assertFalse(self.physical_receipt.production_equivalence_claimed)
        self.assertFalse(
            self.physical_receipt.production_feasibility_gate_changed
        )
        self.assertFalse(self.physical_receipt.production_data_used)
        self.assertEqual(
            M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
            "mandatory-full-replay-benchmark-not-yet-passed",
        )
        self.assertEqual(
            set(dict(self.physical_receipt.final_disposition_counts)),
            {
                "rfi_veto_matched_off_same_hypothesis",
                "rfi_veto_local_off_track",
                "rfi_veto_single_adjacent_off",
                "rfi_veto_receiver_frame_alias",
                "pending_receiver_alias_evaluation",
            },
        )
        self.assertTrue(
            all(
                count > 0
                for _, count in self.physical_receipt.final_disposition_counts
            )
        )

    def test_phase3_dense_and_sparse_stage_products_are_byte_identical(self):
        self.assertEqual(
            core.canonical_json_bytes(self.dense_adjacent_result),
            core.canonical_json_bytes(self.local_adjacent_result),
        )
        self.assertEqual(
            core.canonical_json_bytes(self.dense_alias_result),
            core.canonical_json_bytes(self.local_alias_result),
        )

    def test_phase3_mutations_and_claim_expansion_fail_closed(self):
        changed_adjacent = deepcopy(self.local_adjacent_result)
        changed_adjacent["evidence"][0][
            "paired_adjacent_off_measurements"
        ][0]["snr"] = 5.5
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "differs from the dense reference"
        ):
            self._seal_physical(local_adjacent_result=changed_adjacent)

        changed_alias = deepcopy(self.local_alias_result)
        changed_alias["records"][0]["receiver_alias_evidence"][
            "matched"
        ] = not changed_alias["records"][0]["receiver_alias_evidence"][
            "matched"
        ]
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "differs from the dense reference"
        ):
            self._seal_physical(local_alias_result=changed_alias)

        forged = replace(
            self.physical_receipt,
            production_equivalence_claimed=True,
            receipt_sha256="",
        )
        forged = replace(
            forged,
            receipt_sha256=hashlib.sha256(
                core.canonical_json_bytes(
                    forged.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(core.V0P6IncompleteError, "claim boundary"):
            validate_sparse_physical_reference_kat_receipt(forged)


if __name__ == "__main__":
    unittest.main()
