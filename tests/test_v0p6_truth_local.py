"""Qualification tests for the M39 truth-local score adapter."""

from __future__ import annotations

from contextlib import nullcontext
import hashlib
import math
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core
from seti_repeater.sparse_replay_v0p6 import (
    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS,
    SPARSE_LOCAL_REQUIRED_WIDTHS,
    plan_truth_local_template_scores,
)
from seti_repeater.truth_local_v0p6 import (
    TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS,
    evaluate_truth_local_scores,
    plan_truth_local_template_scores_interval,
)


def _frequency_axis(channel_count: int) -> np.ndarray:
    return np.arange(channel_count, dtype="<f8") / 1e6


def _source_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(values, dtype="<f4").tobytes()
    ).hexdigest()


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
        window_id="synthetic-m39-anchor",
        scan_label=f"epoch{epoch + 1}_on",
        scan_kind="on",
        source_sha256=_source_sha256(normalized),
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


class IntervalPlannerTests(unittest.TestCase):
    def test_matches_materialized_reference_including_boundaries(self):
        grid = core.make_proxy_carrier_grid(0.0005, 1.0, 32, 64)
        factors = np.asarray(
            [
                [1.0, 1.0, 1.0],
                [1.0002, 1.0004, 1.0006],
                [1.003, 1.002, 1.001],
            ],
            dtype="<f8",
            order="C",
        )
        truth = np.asarray([1.0, 1.0, 1.0], dtype="<f8", order="C")
        for tolerance in (20.0, np.nextafter(20.0, -np.inf), 0.0):
            with self.subTest(tolerance=tolerance):
                dense = plan_truth_local_template_scores(
                    grid,
                    factors,
                    500.0,
                    truth,
                    tolerance_hz=tolerance,
                )
                interval = plan_truth_local_template_scores_interval(
                    grid,
                    factors,
                    500.0,
                    truth,
                    tolerance_hz=tolerance,
                )
                self.assertEqual(
                    [item.as_record() for item in interval],
                    [item.as_record() for item in dense],
                )
                for left, right in zip(interval, dense, strict=True):
                    np.testing.assert_array_equal(
                        left.maximum_track_distances_hz,
                        right.maximum_track_distances_hz,
                    )

    def test_m37_scale_planning_avoids_the_materialized_oracle(self):
        grid = core.make_m37_proxy_carrier_grid("m37_1412p5")
        integrations = np.arange(48, dtype=np.float64)
        factors = np.ascontiguousarray(
            np.stack(
                [
                    1.0001
                    + template * 1e-7
                    + integrations * 1e-9
                    for template in range(core.M37_TEMPLATE_COUNT)
                ],
                axis=0,
            ),
            dtype="<f8",
        )
        truth = np.ascontiguousarray(
            1.00025 + integrations * 1.3e-9, dtype="<f8"
        )
        with self.assertRaises(core.V0P6CapacityError):
            plan_truth_local_template_scores(
                grid,
                factors,
                1_412_500_000.0,
                truth,
            )
        plans = plan_truth_local_template_scores_interval(
            grid,
            factors,
            1_412_500_000.0,
            truth,
            maximum_distance_cells=TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS,
        )
        self.assertEqual(len(plans), core.M37_TEMPLATE_COUNT)
        self.assertLessEqual(
            sum(
                item.mask_dependency_indices.indices.size * truth.size
                for item in plans
            ),
            TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS,
        )


class TruthLocalScoreAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = core.NativeFrequencyGeometry(0.0, 1.0, 1024)
        cls.grid = core.make_proxy_carrier_grid(0.0005, 1.0, 20, 64)
        cls.factor_matrices = tuple(
            np.ascontiguousarray(
                np.asarray(
                    [
                        [1.0 + epoch * 1e-4, 1.0 + epoch * 2e-4],
                        [1.001 + epoch * 1e-4, 1.002 + epoch * 2e-4],
                        [1.006 + epoch * 1e-4, 1.004 + epoch * 2e-4],
                    ],
                    dtype="<f8",
                )
            )
            for epoch in range(3)
        )
        distance_matrix = np.ascontiguousarray(
            np.concatenate(cls.factor_matrices, axis=1), dtype="<f8"
        )
        cls.truth_factors = np.ones(6, dtype="<f8")
        cls.plans = plan_truth_local_template_scores_interval(
            cls.grid,
            distance_matrix,
            500.0,
            cls.truth_factors,
        )
        native_index = np.arange(1024, dtype=np.int64)
        cls.native = tuple(
            np.ascontiguousarray(
                np.stack(
                    [
                        4.0
                        + (
                            (
                                native_index * (epoch + 3)
                                + (integration + 1) * 11
                            )
                            % 31
                            - 15
                        )
                        * 0.02
                        for integration in range(2)
                    ],
                    axis=0,
                ),
                dtype="<f4",
            )
            for epoch in range(3)
        )
        cls.caches = {
            (epoch, width): _cache(
                cls.native[epoch],
                cls.geometry,
                cls.grid,
                cls.factor_matrices[epoch],
                width,
                epoch,
            )
            for width in SPARSE_LOCAL_REQUIRED_WIDTHS
            for epoch in range(3)
        }

    def _open(self, epoch: int, width: int):
        return nullcontext(self.caches[(epoch, width)])

    def _dense_best(self):
        best = None
        for plan in self.plans:
            template = plan.template_index
            candidates = plan.candidate_indices.indices
            dense_by_width = {}
            for width in SPARSE_LOCAL_REQUIRED_WIDTHS:
                dense_by_width[width] = np.ascontiguousarray(
                    np.stack(
                        [
                            core.gather_filtered_native(
                                self.caches[(epoch, width)],
                                self.factor_matrices[epoch][template],
                                self.grid,
                            )
                            for epoch in range(3)
                        ],
                        axis=0,
                    ),
                    dtype="<f4",
                )
            mask = core.build_m37_two_pass_template_mask(
                lambda width: dense_by_width[width]
            )
            for width_index, width in enumerate(SPARSE_LOCAL_REQUIRED_WIDTHS):
                for subset_index, subset in enumerate(
                    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS
                ):
                    score = core.stack_hypothesis(
                        dense_by_width[width],
                        subset,
                        minimum_active_epoch_snr=3.0,
                        stack_statistic="minimum_epoch",
                        exclusion_mask=mask,
                    )[candidates]
                    for ordinal, raw_value in enumerate(score):
                        value = float(raw_value)
                        if not math.isfinite(value):
                            continue
                        candidate = (
                            value,
                            template,
                            width_index,
                            subset_index,
                            int(candidates[ordinal]),
                        )
                        if best is None or value > best[0]:
                            best = candidate
        return best

    def test_local_score_is_bit_identical_to_dense_replay(self):
        result = evaluate_truth_local_scores(
            self.plans,
            self.grid,
            self.factor_matrices,
            self._open,
            expected_scan_labels=("epoch1_on", "epoch2_on", "epoch3_on"),
            expected_source_sha256s=tuple(
                _source_sha256(item) for item in self.native
            ),
            window_id="synthetic-m39-anchor",
        )
        dense = self._dense_best()
        self.assertIsNotNone(dense)
        assert dense is not None
        self.assertEqual(
            np.float32(result["best_truth_local_score_snr"]).view(np.uint32),
            np.float32(dense[0]).view(np.uint32),
        )
        self.assertEqual(
            result["best_hypothesis"],
            {
                "template_index": dense[1],
                "spectral_width_index": dense[2],
                "spectral_width_channels": SPARSE_LOCAL_REQUIRED_WIDTHS[dense[2]],
                "activity_subset_index": dense[3],
                "active_epochs_zero_based": list(
                    SPARSE_LOCAL_REQUIRED_ACTIVITY_SUBSETS[dense[3]]
                ),
                "proxy_carrier_index": dense[4],
                "proxy_carrier_hz": float(self.grid.score_hz[dense[4]]),
            },
        )
        self.assertFalse(result["production_equivalence_proven"])
        self.assertFalse(result["physical_veto_survival_calibrated"])

    def test_source_ancestry_mismatch_fails_closed(self):
        changed = list(_source_sha256(item) for item in self.native)
        changed[1] = "f" * 64
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "cache ancestry"
        ):
            evaluate_truth_local_scores(
                self.plans,
                self.grid,
                self.factor_matrices,
                self._open,
                expected_scan_labels=(
                    "epoch1_on",
                    "epoch2_on",
                    "epoch3_on",
                ),
                expected_source_sha256s=changed,
                window_id="synthetic-m39-anchor",
            )

    def test_zero_candidate_inventory_hashes_and_returns_no_best(self):
        distance_matrix = np.ascontiguousarray(
            np.concatenate(self.factor_matrices, axis=1), dtype="<f8"
        )
        plans = plan_truth_local_template_scores_interval(
            self.grid,
            distance_matrix,
            9_000.0,
            self.truth_factors,
        )
        self.assertEqual(
            sum(item.candidate_indices.indices.size for item in plans), 0
        )
        result = evaluate_truth_local_scores(
            plans,
            self.grid,
            self.factor_matrices,
            self._open,
            expected_scan_labels=("epoch1_on", "epoch2_on", "epoch3_on"),
            expected_source_sha256s=tuple(
                _source_sha256(item) for item in self.native
            ),
            window_id="synthetic-m39-anchor",
        )
        self.assertEqual(result["candidate_score_cell_count"], 0)
        self.assertIsNone(result["best_truth_local_score_snr"])
        self.assertIsNone(result["best_hypothesis"])
        self.assertRegex(result["mask_inventory_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["score_inventory_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
