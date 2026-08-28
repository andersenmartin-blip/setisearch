"""Phase-2 synthetic retention, OFF-disposition and rank-p KATs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
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
    SparseLocalReferenceKATReceipt,
    build_sparse_retention_reference_kat,
    make_local_score_index_set,
    seal_sparse_retention_off_rank_reference_kat_receipt,
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


if __name__ == "__main__":
    unittest.main()
