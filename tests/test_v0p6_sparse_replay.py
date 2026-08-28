"""Known-answer tests for the non-production sparse/local reference layer."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import math
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core
from seti_repeater.adjacent_v0p6 import (
    gather_filtered_native_at_score_indices,
)
from seti_repeater.completeness_v0p6 import (
    M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
)
from seti_repeater.sparse_replay_v0p6 import (
    SPARSE_LOCAL_FIXTURE_ARTIFACT_TYPE,
    SPARSE_LOCAL_REFERENCE_STATUS,
    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
    SPARSE_LOCAL_REQUIRED_WIDTHS,
    build_local_two_pass_template_mask,
    clipped_score_index_closure,
    make_local_score_index_set,
    plan_truth_local_template_scores,
    seal_sparse_local_reference_kat_receipt,
    validate_local_score_index_set,
    validate_sparse_local_reference_kat_receipt,
    validate_truth_local_template_plans,
)


def _frequency_axis(channel_count: int) -> np.ndarray:
    return np.arange(channel_count, dtype="<f8") / 1e6


def _cache(
    normalized: np.ndarray,
    geometry: core.NativeFrequencyGeometry,
    grid: core.ProxyCarrierGrid,
    factor_table: np.ndarray,
    width: int,
    epoch: int,
):
    plan = core.plan_native_filter_cache(
        geometry,
        factor_table,
        grid,
        width,
        window_id="synthetic-sparse-reference",
        scan_label=f"epoch{epoch + 1}_on",
        scan_kind="on",
        source_sha256=hashlib.sha256(
            np.ascontiguousarray(normalized, dtype="<f4").tobytes()
        ).hexdigest(),
        factor_basis_sha256_value="1" * 64,
        factor_basis_labels_sha256_value="2" * 64,
        scan_inventory_sha256_value="3" * 64,
        factor_scan_selection_sha256_value=hashlib.sha256(
            f"epoch-{epoch}".encode()
        ).hexdigest(),
        template_bank_sha256_value="4" * 64,
    )
    return core.build_native_filter_cache(
        normalized, _frequency_axis(geometry.channel_count), plan
    )


class LocalIndexAndPlanningTests(unittest.TestCase):
    def test_exact_index_set_and_coordinate_closure(self):
        index_set = make_local_score_index_set(
            65, [64, 0, 10, 9, 20, 40, 39, 10]
        )
        np.testing.assert_array_equal(
            index_set.indices, [0, 9, 10, 20, 39, 40, 64]
        )
        self.assertEqual(
            index_set.runs,
            ((0, 1), (9, 11), (20, 21), (39, 41), (64, 65)),
        )
        closure = clipped_score_index_closure(index_set, guard_bins=9)
        self.assertEqual(closure.runs, ((0, 50), (55, 65)))
        self.assertFalse(closure.indices.flags.writeable)
        validate_local_score_index_set(closure)

        for invalid in ([1.0], [True], [True, 2], [-1], [65], [[1]]):
            with self.subTest(invalid=invalid):
                with self.assertRaises(core.V0P6ContractError):
                    make_local_score_index_set(65, invalid)
        with self.assertRaises(core.V0P6IncompleteError):
            validate_local_score_index_set(
                replace(index_set, runs=((0, 65),))
            )

    def test_literal_inclusive_twenty_hz_oracle_and_hard_cap(self):
        grid = core.make_proxy_carrier_grid(0.0005, 1.0, 32, 64)
        factors = np.ones((1, 2), dtype="<f8")
        truth = np.ones(2, dtype="<f8")
        plans = plan_truth_local_template_scores(
            grid, factors, 500.0, truth, tolerance_hz=20.0
        )
        np.testing.assert_array_equal(
            plans[0].candidate_indices.indices,
            np.arange(12, 53, dtype="<i8"),
        )
        self.assertEqual(plans[0].maximum_track_distances_hz[0], 20.0)
        self.assertEqual(plans[0].maximum_track_distances_hz[-1], 20.0)
        validate_truth_local_template_plans(
            plans, grid, factors, 500.0, truth, tolerance_hz=20.0
        )

        narrower = plan_truth_local_template_scores(
            grid,
            factors,
            500.0,
            truth,
            tolerance_hz=np.nextafter(20.0, -np.inf),
        )
        np.testing.assert_array_equal(
            narrower[0].candidate_indices.indices,
            np.arange(13, 52, dtype="<i8"),
        )
        with self.assertRaises(core.V0P6CapacityError):
            plan_truth_local_template_scores(
                grid,
                factors,
                500.0,
                truth,
                maximum_distance_cells=129,
            )
        with self.assertRaises(core.V0P6ContractError):
            plan_truth_local_template_scores(
                grid,
                factors,
                500.0,
                truth,
                maximum_distance_cells=2_000_001,
            )
        with self.assertRaises(core.V0P6ContractError):
            plan_truth_local_template_scores(
                grid,
                [[True, 1.0]],
                500.0,
                [1.0, 1.0],
            )
        with self.assertRaises(core.V0P6ContractError):
            plan_truth_local_template_scores(
                grid,
                np.ones((1, 2), dtype="<f4"),
                500.0,
                truth,
            )

    def test_truth_distance_oracle_fails_closed_on_float64_overflow(self):
        grid = core.make_proxy_carrier_grid(0.0005, 1.0, 1, 1)
        factors = np.full((1, 1), 1e308, dtype="<f8")
        truth = np.ones(1, dtype="<f8")
        with self.assertRaises(core.V0P6ContractError):
            plan_truth_local_template_scores(
                grid, factors, 500.0, truth
            )

        factors = np.ones((1, 1), dtype="<f8")
        truth = np.full(1, 1e308, dtype="<f8")
        with self.assertRaises(core.V0P6ContractError):
            plan_truth_local_template_scores(
                grid, factors, 1e308, truth
            )

    def test_half_bin_ties_are_preserved_by_sparse_gather(self):
        geometry = core.NativeFrequencyGeometry(0.0, 1.0, 1024)
        grid = core.make_proxy_carrier_grid(0.0005, 1.0, 4, 64)
        below = np.nextafter(1.001, -np.inf)
        above = np.nextafter(1.001, np.inf)
        factor_table = np.asarray(
            [[below], [1.001], [above]], dtype="<f8"
        )
        data = np.zeros((1, 1024), dtype="<f4")
        data[0, 500] = 5.0
        data[0, 501] = 7.0
        cache = _cache(data, geometry, grid, factor_table, 1, 0)
        center = grid.score_half_bins
        requested = grid.score_hz[center] * factor_table[:, 0]
        np.testing.assert_array_equal(
            core.nearest_native_indices(geometry, requested), [500, 500, 501]
        )
        for row, expected in zip(factor_table, (5.0, 5.0, 7.0), strict=True):
            dense = core.gather_filtered_native(cache, row, grid)
            local = gather_filtered_native_at_score_indices(
                cache, row, grid, [center]
            )
            np.testing.assert_array_equal(local.view(np.uint32), dense[[center]].view(np.uint32))
            self.assertEqual(float(local[0]), expected)


class LocalMaskTests(unittest.TestCase):
    def test_coordinate_aware_width_or_and_clipped_guard(self):
        score_count = 65
        candidates = make_local_score_index_set(
            score_count, [0, 8, 9, 20, 21, 31, 55, 64]
        )
        dense_by_width: dict[int, np.ndarray] = {}
        peak_indices = (0, 9, 19, 29, 39, 49, 55, 64)
        for ordinal, (width, peak) in enumerate(
            zip(SPARSE_LOCAL_REQUIRED_WIDTHS, peak_indices, strict=True)
        ):
            values = np.full((3, score_count), 2.0, dtype="<f4")
            epoch = ordinal % 3
            values[epoch, peak] = np.float32(10.0)
            if ordinal == 1:
                values[(epoch + 1) % 3, peak] = np.nextafter(
                    np.float32(3.0), np.float32(-np.inf)
                )
            if ordinal == 2:
                # Strict other-epoch comparison: equality to three prevents
                # this otherwise strong cell from being isolated.
                values[(epoch + 1) % 3, peak] = np.float32(3.0)
            dense_by_width[width] = values

        dense = core.build_m37_two_pass_template_mask(
            lambda width: dense_by_width[width]
        )

        def factory(width, selected):
            return np.ascontiguousarray(
                dense_by_width[width][:, selected], dtype="<f4"
            )

        local = build_local_two_pass_template_mask(factory, candidates)
        np.testing.assert_array_equal(local, dense[:, candidates.indices])
        self.assertTrue(np.any(local[:, 0]))
        self.assertTrue(np.any(local[:, -1]))

        def nonfinite_factory(width, selected):
            result = np.ascontiguousarray(
                dense_by_width[width][:, selected], dtype="<f4"
            )
            result[0, 0] = np.nan
            return result

        with self.assertRaises(core.V0P6ContractError):
            build_local_two_pass_template_mask(nonfinite_factory, candidates)


class SparseDenseReferenceReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry = core.NativeFrequencyGeometry(0.0, 1.0, 1024)
        # The exact-truth template reaches both score-grid endpoints at the
        # inclusive 20-Hz boundary.
        cls.grid = core.make_proxy_carrier_grid(0.0005, 1.0, 20, 64)
        cls.factor_table = np.asarray(
            [
                [1.0, 1.0],
                [1.001, 1.002],
                [1.01, 1.005],
            ],
            dtype="<f8",
        )
        cls.distance_factor_table = np.concatenate(
            [cls.factor_table] * 3, axis=1
        )
        cls.truth_factors = np.ones(6, dtype="<f8")
        cls.plans = plan_truth_local_template_scores(
            cls.grid,
            cls.distance_factor_table,
            500.0,
            cls.truth_factors,
            tolerance_hz=20.0,
        )
        cls.caches: dict[tuple[int, int], object] = {}
        cls.native_by_epoch: dict[int, np.ndarray] = {}
        native_index = np.arange(1024, dtype=np.int64)
        for epoch in range(3):
            rows = np.stack(
                [
                    4.0
                    + (
                        (
                            native_index * (epoch + 3)
                            + (integration + 1) * 7
                            + epoch * 11
                            + 37_060_613
                        )
                        % 29
                        - 14
                    )
                    * 0.01
                    for integration in range(2)
                ],
                axis=0,
            ).astype("<f4")
            # Rolling an endpoint-marked row places a literal circular seam
            # beneath the central q region. Width 129 crosses that seam.
            rows[:, 0] += np.float32(14.0 + epoch)
            rows[:, -1] -= np.float32(7.0 + epoch)
            rows[0] = np.roll(rows[0], 500 + epoch)
            rows[1] = np.roll(rows[1], 501 - epoch)
            rows = np.ascontiguousarray(rows, dtype="<f4")
            cls.native_by_epoch[epoch] = rows
            for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
                cls.caches[(epoch, width)] = _cache(
                    rows,
                    cls.geometry,
                    cls.grid,
                    cls.factor_table,
                    width,
                    epoch,
                )

    def _derive_reference(self):
        dense_gathers: dict[tuple[int, int, int], np.ndarray] = {}
        local_gathers: dict[tuple[int, int, int], np.ndarray] = {}
        dense_isolated_masks: dict[tuple[int, int], np.ndarray] = {}
        local_isolated_masks: dict[tuple[int, int], np.ndarray] = {}
        mask_input_vectors: dict[tuple[int, int], np.ndarray] = {}
        dense_masks: dict[int, np.ndarray] = {}
        local_masks: dict[int, np.ndarray] = {}
        dense_scores: dict[
            tuple[int, int, tuple[int, ...]], np.ndarray
        ] = {}
        local_scores: dict[
            tuple[int, int, tuple[int, ...]], np.ndarray
        ] = {}

        for plan in self.plans:
            template = plan.template_index
            dependency = plan.mask_dependency_indices.indices
            candidates = plan.candidate_indices.indices
            dense_by_width: dict[int, np.ndarray] = {}
            local_dependency_by_width: dict[int, np.ndarray] = {}
            local_candidate_by_width: dict[int, np.ndarray] = {}
            for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
                materialized = np.ascontiguousarray(
                    np.stack(
                        [
                            core.materialized_reference_gather(
                                self.native_by_epoch[epoch],
                                _frequency_axis(self.geometry.channel_count),
                                self.geometry,
                                self.factor_table[template],
                                self.grid,
                                width,
                            )
                            for epoch in range(3)
                        ],
                        axis=0,
                    ),
                    dtype="<f4",
                )
                cached = np.ascontiguousarray(
                    np.stack(
                        [
                            core.gather_filtered_native(
                                self.caches[(epoch, width)],
                                self.factor_table[template],
                                self.grid,
                                chunk_bins=7,
                            )
                            for epoch in range(3)
                        ],
                        axis=0,
                    ),
                    dtype="<f4",
                )
                np.testing.assert_array_equal(
                    cached.view(np.uint32), materialized.view(np.uint32)
                )
                dense = materialized
                local_dependency = np.ascontiguousarray(
                    np.stack(
                        [
                            gather_filtered_native_at_score_indices(
                                self.caches[(epoch, width)],
                                self.factor_table[template],
                                self.grid,
                                dependency,
                                chunk_bins=3,
                            )
                            for epoch in range(3)
                        ],
                        axis=0,
                    ),
                    dtype="<f4",
                )
                local_candidate = np.ascontiguousarray(
                    np.stack(
                        [
                            gather_filtered_native_at_score_indices(
                                self.caches[(epoch, width)],
                                self.factor_table[template],
                                self.grid,
                                candidates[::-1],
                                chunk_bins=2,
                            )[::-1]
                            for epoch in range(3)
                        ],
                        axis=0,
                    ),
                    dtype="<f4",
                )
                np.testing.assert_array_equal(
                    local_dependency.view(np.uint32),
                    dense[:, dependency].view(np.uint32),
                )
                np.testing.assert_array_equal(
                    local_candidate.view(np.uint32),
                    dense[:, candidates].view(np.uint32),
                )
                dense_by_width[width] = dense
                local_dependency_by_width[width] = local_dependency
                local_candidate_by_width[width] = local_candidate
                for epoch in range(3):
                    key = (template, width, epoch)
                    dense_gathers[key] = np.ascontiguousarray(
                        dense[epoch, dependency], dtype="<f4"
                    )
                    local_gathers[key] = np.ascontiguousarray(
                        local_dependency[epoch], dtype="<f4"
                    )

            mask_dense_by_width: dict[int, np.ndarray] = {}
            mask_local_by_width: dict[int, np.ndarray] = {}
            for width_ordinal, width in enumerate(
                SPARSE_LOCAL_REQUIRED_WIDTHS
            ):
                witness_ordinal = (
                    template * len(SPARSE_LOCAL_REQUIRED_WIDTHS)
                    + width_ordinal
                )
                witness_epoch = witness_ordinal % 3
                witness_q = 12 + witness_ordinal // 3
                mask_vectors = np.full(
                    (3, self.grid.score_bin_count), 2.0, dtype="<f4"
                )
                mask_vectors[witness_epoch, witness_q] = np.float32(
                    10.0 + 0.125 * witness_ordinal
                )
                local_mask_vectors = np.ascontiguousarray(
                    mask_vectors[:, dependency], dtype="<f4"
                )
                dense_isolated = core.isolated_single_epoch_mask(
                    mask_vectors,
                    core.M37_RFI_STRONG_SNR,
                    core.M37_RFI_OTHER_EPOCHS_BELOW_SNR,
                )
                local_isolated = core.isolated_single_epoch_mask(
                    local_mask_vectors,
                    core.M37_RFI_STRONG_SNR,
                    core.M37_RFI_OTHER_EPOCHS_BELOW_SNR,
                )
                np.testing.assert_array_equal(
                    local_isolated, dense_isolated[:, dependency]
                )
                self.assertEqual(int(np.count_nonzero(dense_isolated)), 1)
                mask_dense_by_width[width] = mask_vectors
                mask_local_by_width[width] = local_mask_vectors
                mask_input_vectors[(template, width)] = mask_vectors
                dense_isolated_masks[(template, width)] = (
                    np.ascontiguousarray(
                        dense_isolated[:, dependency], dtype=bool
                    )
                )
                local_isolated_masks[(template, width)] = (
                    np.ascontiguousarray(local_isolated, dtype=bool)
                )

            dense_mask = core.build_m37_two_pass_template_mask(
                lambda width: mask_dense_by_width[width]
            )

            def vector_factory(width, selected):
                np.testing.assert_array_equal(selected, dependency)
                return mask_local_by_width[width]

            local_mask = build_local_two_pass_template_mask(
                vector_factory, plan.candidate_indices
            )
            np.testing.assert_array_equal(local_mask, dense_mask[:, candidates])
            dense_masks[template] = np.ascontiguousarray(
                dense_mask[:, candidates], dtype=bool
            )
            local_masks[template] = np.ascontiguousarray(
                local_mask, dtype=bool
            )

            for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
                for subset in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS:
                    dense_score = core.stack_hypothesis(
                        dense_by_width[width],
                        subset,
                        minimum_active_epoch_snr=3.0,
                        stack_statistic="minimum_epoch",
                        exclusion_mask=dense_mask,
                    )[candidates]
                    local_score = core.stack_hypothesis(
                        local_candidate_by_width[width],
                        subset,
                        minimum_active_epoch_snr=3.0,
                        stack_statistic="minimum_epoch",
                        exclusion_mask=local_mask,
                    )
                    np.testing.assert_array_equal(
                        local_score.view(np.uint32), dense_score.view(np.uint32)
                    )
                    score_key = (template, width, subset)
                    dense_scores[score_key] = np.ascontiguousarray(
                        dense_score, dtype="<f4"
                    )
                    local_scores[score_key] = np.ascontiguousarray(
                        local_score, dtype="<f4"
                    )

        fixture = {
            "artifact_type": SPARSE_LOCAL_FIXTURE_ARTIFACT_TYPE,
            "seed": 37_060_613,
            "native_channel_count": 1024,
            "integration_count_per_epoch": 2,
            "distance_integration_count": 6,
            "template_count": int(self.factor_table.shape[0]),
            "score_bin_count": self.grid.score_bin_count,
            "support_bin_count": self.grid.support_bin_count,
            "widths": list(SPARSE_LOCAL_REQUIRED_WIDTHS),
            "activity_subsets": [
                list(item) for item in SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
            ],
            "truth_proxy_carrier_hz": 500.0,
            "tolerance_hz": 20.0,
            "guard_bins": 9,
            "proxy_grid_sha256": core.proxy_carrier_grid_sha256(self.grid),
            "factor_table_sha256": core.factor_table_sha256(
                self.factor_table
            ),
            "distance_factor_table_sha256": core.factor_table_sha256(
                self.distance_factor_table
            ),
            "truth_factors_sha256": core.float64_vector_sha256(
                self.truth_factors
            ),
            "native_epoch_sha256s": [
                core.float32_array_sha256(self.native_by_epoch[epoch])
                for epoch in range(3)
            ],
            "mask_input_sha256s": [
                {
                    "template_index": template,
                    "width_channels": width,
                    "sha256": core.float32_array_sha256(
                        mask_input_vectors[(template, width)]
                    ),
                }
                for template in range(3)
                for width in SPARSE_LOCAL_REQUIRED_WIDTHS
            ],
            "contains_circular_roll_seam": True,
            "seam_witness": {
                "epoch_zero_based": 0,
                "integration_index": 0,
                "roll_shift": 500,
                "seam_native_index": 500,
                "score_index": self.grid.score_half_bins,
                "mapped_native_center": 500,
                "width_channels": 129,
                "filter_interval_half_open": [436, 565],
            },
            "half_bin_tie_witness": {
                "score_index": self.grid.score_half_bins,
                "requested_native_coordinate": 500.5,
                "mapped_native_index": 500,
            },
            "score_endpoint_witness": {
                "template_index": 0,
                "left_score_index": 0,
                "right_score_index": self.grid.score_bin_count - 1,
                "maximum_track_distances_hz": [20.0, 20.0],
            },
            "closure_witness": {
                "score_bin_count": self.grid.score_bin_count,
                "guard_bins": 9,
                "input_indices": [0, 9, 10, 20, 39, 40],
                "expected_runs": [[0, 41]],
            },
            "production_data_used": False,
        }
        receipt = seal_sparse_local_reference_kat_receipt(
            fixture,
            self.plans,
            dense_gathers=dense_gathers,
            local_gathers=local_gathers,
            dense_isolated_masks=dense_isolated_masks,
            local_isolated_masks=local_isolated_masks,
            dense_masks=dense_masks,
            local_masks=local_masks,
            dense_scores=dense_scores,
            local_scores=local_scores,
        )
        artifacts = {
            "fixture": fixture,
            "dense_gathers": dense_gathers,
            "local_gathers": local_gathers,
            "dense_isolated_masks": dense_isolated_masks,
            "local_isolated_masks": local_isolated_masks,
            "mask_input_vectors": mask_input_vectors,
            "dense_masks": dense_masks,
            "local_masks": local_masks,
            "dense_scores": dense_scores,
            "local_scores": local_scores,
        }
        return receipt, artifacts

    def test_full_synthetic_sparse_core_is_bit_identical_and_claim_limited(self):
        receipt, _ = self._derive_reference()
        validate_sparse_local_reference_kat_receipt(receipt)
        self.assertEqual(receipt.status, SPARSE_LOCAL_REFERENCE_STATUS)
        self.assertFalse(receipt.production_equivalence_claimed)
        self.assertFalse(receipt.global_retention_equivalence_proven)
        self.assertFalse(receipt.receiver_alias_equivalence_proven)
        self.assertFalse(receipt.off_disposition_equivalence_proven)
        self.assertFalse(receipt.rank_p_equivalence_proven)
        self.assertFalse(receipt.production_receipt_ancestry_proven)
        self.assertFalse(receipt.production_feasibility_gate_changed)
        self.assertEqual(
            receipt.fixture_sha256,
            "b3ec37255a43219a7bc6bb84d4e22df60a98458910c02262096b69c72817fcc1",
        )
        self.assertEqual(
            receipt.plan_inventory_sha256,
            "02fbcb46e7766fe042563f284cdb18ab1e84f6aafd2b16e873aa64356b96f66d",
        )
        self.assertEqual(
            receipt.dense_gathers_sha256,
            "7b6fbf3f72a5409e3b3948b565827e67183fdf53a608a4c0020e10b6b9ee2a1a",
        )
        self.assertEqual(
            receipt.dense_isolated_masks_sha256,
            "4bc200300fc341a613459068c51f76e2d02fb8e1145ca24044cee452fdee2a23",
        )
        self.assertEqual(
            receipt.dense_masks_sha256,
            "e04f3bc8d0e354fad5246f6c7c76796ef7d3e2780b0f05bb59df7b875a3a9eae",
        )
        self.assertEqual(
            receipt.dense_scores_sha256,
            "8f051405840dad8d8cc0c45cdd001ac573b5b2df40928e5c85f779ebc40e8aab",
        )
        self.assertEqual(
            receipt.receipt_sha256,
            "32e9208579e435be0cefa72c13e579c8020ec361f23fa9650e9adbf25cfe9201",
        )
        self.assertEqual(receipt.gather_array_count, 72)
        self.assertEqual(receipt.isolated_mask_array_count, 24)
        self.assertEqual(receipt.mask_array_count, 3)
        self.assertEqual(receipt.score_array_count, 96)
        self.assertEqual(
            M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
            "mandatory-full-replay-benchmark-not-yet-passed",
        )

    def test_receipt_fails_closed_on_byte_or_claim_substitution(self):
        receipt, artifacts = self._derive_reference()
        with self.assertRaises(core.V0P6IncompleteError):
            validate_sparse_local_reference_kat_receipt(
                replace(receipt, production_equivalence_claimed=True)
            )
        with self.assertRaises(core.V0P6ContractError):
            validate_sparse_local_reference_kat_receipt(
                replace(receipt, receipt_sha256=int("7" * 64))
            )
        with self.assertRaises(core.V0P6ContractError):
            validate_sparse_local_reference_kat_receipt(
                replace(receipt, template_count=True)
            )
        with self.assertRaises(core.V0P6ContractError):
            validate_sparse_local_reference_kat_receipt(
                replace(
                    receipt,
                    spectral_widths=(
                        True,
                        *SPARSE_LOCAL_REQUIRED_WIDTHS[1:],
                    ),
                )
            )
        changed = {
            key: np.array(item, copy=True)
            for key, item in artifacts["local_scores"].items()
        }
        first_score_key = next(iter(changed))
        changed[first_score_key].view(np.uint32)[0] ^= np.uint32(1)
        with self.assertRaises(core.V0P6IncompleteError):
            seal_sparse_local_reference_kat_receipt(
                artifacts["fixture"],
                self.plans,
                dense_gathers=artifacts["dense_gathers"],
                local_gathers=artifacts["local_gathers"],
                dense_isolated_masks=artifacts["dense_isolated_masks"],
                local_isolated_masks=artifacts["local_isolated_masks"],
                dense_masks=artifacts["dense_masks"],
                local_masks=artifacts["local_masks"],
                dense_scores=artifacts["dense_scores"],
                local_scores=changed,
            )

        bad_fixture = dict(artifacts["fixture"])
        bad_fixture["native_channel_count"] = True
        with self.assertRaises(core.V0P6ContractError):
            seal_sparse_local_reference_kat_receipt(
                bad_fixture,
                self.plans,
                dense_gathers=artifacts["dense_gathers"],
                local_gathers=artifacts["local_gathers"],
                dense_isolated_masks=artifacts["dense_isolated_masks"],
                local_isolated_masks=artifacts["local_isolated_masks"],
                dense_masks=artifacts["dense_masks"],
                local_masks=artifacts["local_masks"],
                dense_scores=artifacts["dense_scores"],
                local_scores=artifacts["local_scores"],
            )

        extra_fixture = dict(artifacts["fixture"])
        extra_fixture["production_equivalence_claimed"] = False
        with self.assertRaises(core.V0P6IncompleteError):
            seal_sparse_local_reference_kat_receipt(
                extra_fixture,
                self.plans,
                dense_gathers=artifacts["dense_gathers"],
                local_gathers=artifacts["local_gathers"],
                dense_isolated_masks=artifacts["dense_isolated_masks"],
                local_isolated_masks=artifacts["local_isolated_masks"],
                dense_masks=artifacts["dense_masks"],
                local_masks=artifacts["local_masks"],
                dense_scores=artifacts["dense_scores"],
                local_scores=artifacts["local_scores"],
            )

        duplicated_epoch_gathers = {
            key: np.array(
                artifacts["dense_gathers"][(key[0], key[1], 0)],
                copy=True,
            )
            for key in artifacts["dense_gathers"]
        }
        with self.assertRaises(core.V0P6IncompleteError):
            seal_sparse_local_reference_kat_receipt(
                artifacts["fixture"],
                self.plans,
                dense_gathers=duplicated_epoch_gathers,
                local_gathers=duplicated_epoch_gathers,
                dense_isolated_masks=artifacts["dense_isolated_masks"],
                local_isolated_masks=artifacts["local_isolated_masks"],
                dense_masks=artifacts["dense_masks"],
                local_masks=artifacts["local_masks"],
                dense_scores=artifacts["dense_scores"],
                local_scores=artifacts["local_scores"],
            )

        with self.assertRaises(core.V0P6IncompleteError):
            seal_sparse_local_reference_kat_receipt(
                artifacts["fixture"],
                (),
                dense_gathers={},
                local_gathers={},
                dense_isolated_masks={},
                local_isolated_masks={},
                dense_masks={},
                local_masks={},
                dense_scores={},
                local_scores={},
            )


if __name__ == "__main__":
    unittest.main()
