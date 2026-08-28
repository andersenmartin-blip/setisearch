from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
import unittest

import numpy as np

from seti_repeater.completeness_v0p6 import (
    CompletenessLedger,
    M37_COMPLETENESS_ALLOCATION_CONTRACT_SHA256,
    M37_COMPLETENESS_BACKGROUND_WINDOW,
    M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS,
    M37_COMPLETENESS_EXPECTED_TEMPLATE_MASKS,
    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL,
    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL,
    M37_COMPLETENESS_MASTER_SEED,
    M37_COMPLETENESS_M37_BACKGROUND_PROJECTED_PEAK_BYTES,
    M37_COMPLETENESS_MAXIMUM_DETECTOR_RECORDS,
    M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL,
    M37_COMPLETENESS_PLAN_SHA256,
    M37_COMPLETENESS_PHASE_STRATA,
    M37_COMPLETENESS_RADIAL_STRATA,
    M37_COMPLETENESS_SNR_GRID,
    M37_COMPLETENESS_STATUS,
    M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
    M37_COMPLETENESS_PRELOADED_THREE_SOURCE_ROLL_BYTES,
    M37_COMPLETENESS_TRIAL_INVENTORY_SHA256,
    M37_COMPLETENESS_TRUTH_INVENTORY_SHA256,
    M37_COMPLETENESS_TRUTHS_PER_LEVEL,
    freeze_operational_threshold,
    inject_native_before_filter,
    iter_m37_completeness_trials,
    make_m37_prospective_completeness_plan,
    make_synthetic_mask_replay_receipt,
    make_synthetic_trial_evaluation,
    run_streaming_completeness,
    run_streaming_m37_completeness,
    seal_mask_replay_receipt,
    seal_m37_native_trial_background,
    seal_native_background_scan,
    seal_native_trial_background,
    seal_trial_evaluation,
    validate_completeness_result,
    validate_injected_native_trial,
    validate_m37_completeness_plan,
    validate_native_background_scan,
    validate_trial_evaluation,
    wilson_interval_95,
)
from seti_repeater.search_v0p6 import (
    M37_ACTIVITY_SUBSETS,
    M37_BANK_SHA256,
    M37_DIRECTION,
    M37_SPECTRAL_WIDTHS,
    M37_TEMPLATE_COUNT,
    NativeFrequencyGeometry,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6CoverageError,
    V0P6IncompleteError,
    canonical_json_bytes,
    make_factor_basis_from_arrays,
    make_line_template_bank,
    make_template_factor_table,
    template_factors_from_basis,
)
from seti_repeater.spectral import normalized_boxcar


CONTEXT_SHA256 = "4" * 64
DETECTOR_RECEIPT_SHA256 = "5" * 64
DISPOSITION_RECEIPT_SHA256 = "6" * 64

SYNTHETIC_FACTOR_BASIS = make_factor_basis_from_arrays(
    np.array([1.0, 2.0, 3.0], dtype=np.float64),
    tuple(
        {
            "scan_index": epoch,
            "scan_label": f"epoch{epoch + 1}_on",
            "integration_index": 0,
        }
        for epoch in range(3)
    ),
    np.ones(3, dtype=np.float64),
    np.array(
        [
            [1.0e-11, -2.0e-11],
            [-1.5e-11, 0.5e-11],
            [2.0e-11, 1.0e-11],
        ],
        dtype=np.float64,
    ),
    expected_sha256=None,
)
SYNTHETIC_FACTOR_TABLE = make_template_factor_table(
    SYNTHETIC_FACTOR_BASIS,
    make_line_template_bank(),
    expected_template_bank_sha256=M37_BANK_SHA256,
)
FACTOR_TABLE_SHA256 = SYNTHETIC_FACTOR_TABLE.factor_table_sha256


def synthetic_threshold(value: float = 7.0):
    return freeze_operational_threshold(
        value,
        "1" * 64,
        "2" * 64,
        FACTOR_TABLE_SHA256,
        "7" * 64,
    )


def synthetic_background(trial, *, channel_count: int = 161):
    center = channel_count // 2
    geometry = NativeFrequencyGeometry(
        raw_zero_hz=trial.truth.proxy_carrier_hz - center,
        channel_width_hz=1.0,
        channel_count=channel_count,
    )
    scans = []
    for epoch in range(3):
        scans.append(
            seal_native_background_scan(
                f"epoch{epoch + 1}_on",
                epoch,
                np.zeros((1, channel_count), dtype=np.float32),
                geometry,
                truth=trial.truth,
                factor_basis=SYNTHETIC_FACTOR_BASIS,
                factor_table=SYNTHETIC_FACTOR_TABLE,
            )
        )
    return seal_native_trial_background(
        trial,
        scans,
        context_sha256=CONTEXT_SHA256,
    )


def synthetic_artifacts(trial, threshold=None):
    if threshold is None:
        threshold = synthetic_threshold()
    background = synthetic_background(trial)
    injected = inject_native_before_filter(background, trial)
    masks = make_synthetic_mask_replay_receipt(injected, trial)
    evaluation = make_synthetic_trial_evaluation(
        trial, injected, masks, threshold
    )
    return background, injected, masks, evaluation


class SyntheticDataSource:
    def load_background(self, trial):
        return synthetic_background(trial)


class SyntheticOperationalPipeline:
    def recompute_two_pass_masks(self, injected, trial):
        return make_synthetic_mask_replay_receipt(injected, trial)

    def evaluate_exact_operational_pipeline(
        self, injected, masks, threshold, trial
    ):
        return make_synthetic_trial_evaluation(
            trial, injected, masks, threshold
        )


class ProspectiveAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_m37_prospective_completeness_plan()

    def test_literal_known_answers_and_complete_coverage(self):
        plan = self.plan
        self.assertEqual(M37_COMPLETENESS_MASTER_SEED, 372_120_260_827)
        self.assertEqual(
            M37_COMPLETENESS_SNR_GRID,
            (4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 16.0, 20.0, 24.0, 32.0, 40.0),
        )
        self.assertEqual(plan.status, M37_COMPLETENESS_STATUS)
        self.assertIn("provisional", plan.status)
        self.assertEqual(
            plan.allocation_contract_sha256,
            M37_COMPLETENESS_ALLOCATION_CONTRACT_SHA256,
        )
        self.assertEqual(plan.truth_inventory_sha256, M37_COMPLETENESS_TRUTH_INVENTORY_SHA256)
        self.assertEqual(plan.trial_inventory_sha256, M37_COMPLETENESS_TRIAL_INVENTORY_SHA256)
        self.assertEqual(plan.plan_sha256, M37_COMPLETENESS_PLAN_SHA256)
        self.assertEqual(len(plan.truths), M37_COMPLETENESS_TRUTHS_PER_LEVEL)
        self.assertEqual(plan.expected_trial_count, 6_144)
        self.assertEqual(
            M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL,
            2_225_051_040,
        )
        self.assertEqual(
            M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL,
            13_670_713_589_760,
        )
        self.assertEqual(
            M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
            "mandatory-full-replay-benchmark-not-yet-passed",
        )
        self.assertEqual(
            M37_COMPLETENESS_M37_BACKGROUND_PROJECTED_PEAK_BYTES,
            418_203_096,
        )
        self.assertEqual(
            M37_COMPLETENESS_PRELOADED_THREE_SOURCE_ROLL_BYTES,
            550_168_200,
        )
        self.assertLess(
            M37_COMPLETENESS_M37_BACKGROUND_PROJECTED_PEAK_BYTES,
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL,
        )
        self.assertGreater(
            M37_COMPLETENESS_PRELOADED_THREE_SOURCE_ROLL_BYTES,
            M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL,
        )
        self.assertEqual(
            {item.spectral_width_channels for item in plan.truths},
            set(M37_SPECTRAL_WIDTHS),
        )
        self.assertEqual(
            {item.active_epochs_zero_based for item in plan.truths},
            set(M37_ACTIVITY_SUBSETS),
        )
        self.assertEqual(len({item.proxy_carrier_index for item in plan.truths}), 512)
        pairs = [
            (item.spectral_width_channels, item.active_epochs_zero_based)
            for item in plan.truths
        ]
        self.assertEqual(
            {pair: pairs.count(pair) for pair in set(pairs)},
            {
                (width, subset): 16
                for subset in M37_ACTIVITY_SUBSETS
                for width in M37_SPECTRAL_WIDTHS
            },
        )
        expected_pairs = {
            (width, subset)
            for subset in M37_ACTIVITY_SUBSETS
            for width in M37_SPECTRAL_WIDTHS
        }
        for radial in range(M37_COMPLETENESS_RADIAL_STRATA):
            self.assertEqual(
                {
                    (
                        truth.spectral_width_channels,
                        truth.active_epochs_zero_based,
                    )
                    for truth in plan.truths
                    if truth.radial_stratum_index == radial
                },
                expected_pairs,
            )
        for pair in expected_pairs:
            matching = [
                truth
                for truth in plan.truths
                if (
                    truth.spectral_width_channels,
                    truth.active_epochs_zero_based,
                )
                == pair
            ]
            self.assertEqual(
                {truth.radial_stratum_index for truth in matching},
                set(range(M37_COMPLETENESS_RADIAL_STRATA)),
            )
            self.assertEqual(
                len({truth.phase_stratum_index for truth in matching}),
                M37_COMPLETENESS_RADIAL_STRATA,
            )
        bank = make_line_template_bank()
        bank_coefficients = {
            (template["coefficient_x"], template["coefficient_y"])
            for template in bank
        }
        self.assertEqual(
            {
                (truth.radial_stratum_index, truth.phase_stratum_index)
                for truth in plan.truths
            },
            {
                (radial, phase)
                for radial in range(M37_COMPLETENESS_RADIAL_STRATA)
                for phase in range(M37_COMPLETENESS_PHASE_STRATA)
            },
        )
        self.assertEqual(
            {
                radial: sum(
                    truth.radial_stratum_index == radial
                    for truth in plan.truths
                )
                for radial in range(M37_COMPLETENESS_RADIAL_STRATA)
            },
            {radial: M37_COMPLETENESS_PHASE_STRATA for radial in range(16)},
        )
        self.assertEqual(
            {
                phase: sum(
                    truth.phase_stratum_index == phase
                    for truth in plan.truths
                )
                for phase in range(M37_COMPLETENESS_PHASE_STRATA)
            },
            {phase: M37_COMPLETENESS_RADIAL_STRATA for phase in range(32)},
        )
        for truth in plan.truths:
            template = bank[truth.template_index]
            self.assertEqual(truth.line_coefficient, template["line_coefficient"])
            self.assertNotIn(
                (truth.coefficient_x, truth.coefficient_y), bank_coefficients
            )
            radius_squared = truth.coefficient_x**2 + truth.coefficient_y**2
            self.assertLessEqual(radius_squared, 1.0 + 4e-15)
            self.assertAlmostEqual(
                math.sqrt(radius_squared), truth.projected_scale, places=14
            )
            self.assertGreaterEqual(
                radius_squared,
                truth.radial_stratum_index / M37_COMPLETENESS_RADIAL_STRATA,
            )
            self.assertLess(
                radius_squared,
                (truth.radial_stratum_index + 1)
                / M37_COMPLETENESS_RADIAL_STRATA,
            )
            self.assertGreaterEqual(
                truth.phase_cycles,
                truth.phase_stratum_index / M37_COMPLETENESS_PHASE_STRATA,
            )
            self.assertLess(
                truth.phase_cycles,
                (truth.phase_stratum_index + 1)
                / M37_COMPLETENESS_PHASE_STRATA,
            )
            self.assertAlmostEqual(
                truth.direction_projection,
                truth.coefficient_x * M37_DIRECTION[0]
                + truth.coefficient_y * M37_DIRECTION[1],
                places=15,
            )
            self.assertEqual(truth.window_id, M37_COMPLETENESS_BACKGROUND_WINDOW)

    def test_reproducible_trials_and_seed_inventory(self):
        again = make_m37_prospective_completeness_plan()
        self.assertEqual(self.plan, again)
        left = iter_m37_completeness_trials(self.plan)
        right = iter_m37_completeness_trials(again)
        self.assertEqual(left, right)
        self.assertEqual(len(left), 6_144)
        self.assertEqual(len({item.trial_id for item in left}), 6_144)
        self.assertEqual(len({item.noise_seed for item in left}), 6_144)

    def test_plan_mutation_fails_closed(self):
        changed_truth = replace(
            self.plan.truths[0],
            proxy_carrier_index=self.plan.truths[0].proxy_carrier_index + 1,
        )
        changed = replace(
            self.plan,
            truths=(changed_truth, *self.plan.truths[1:]),
        )
        with self.assertRaises(V0P6IncompleteError):
            validate_m37_completeness_plan(changed)


class NativeInjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan = make_m37_prospective_completeness_plan()
        # Ordinal one has the three-channel truth width.
        cls.trial = iter_m37_completeness_trials(plan)[1]

    def test_injection_is_native_prefilter_and_known_answer(self):
        background = synthetic_background(self.trial)
        injected = inject_native_before_filter(background, self.trial)
        width = self.trial.truth.spectral_width_channels
        self.assertEqual(width, 3)
        center = injected.scans[0].geometry.channel_count // 2
        expected_amplitude = self.trial.ideal_single_epoch_snr / math.sqrt(width)
        np.testing.assert_allclose(
            injected.scans[0].normalized[0, center - 1 : center + 2],
            expected_amplitude,
            rtol=1e-7,
        )
        filtered = normalized_boxcar(injected.scans[0].normalized, width)
        self.assertAlmostEqual(
            float(filtered[0, center]),
            self.trial.ideal_single_epoch_snr,
            places=6,
        )
        self.assertEqual(
            float(
                normalized_boxcar(background.scans[0].normalized, width)[
                    0, center
                ]
            ),
            0.0,
        )
        self.assertTrue(np.all(injected.scans[2].normalized == 0.0))
        self.assertIn("before-native-boxcar", injected.injection_stage)

    def test_truth_factors_are_continuous_basis_derivations(self):
        background = synthetic_background(self.trial)
        for scan in background.scans:
            expected = template_factors_from_basis(
                SYNTHETIC_FACTOR_BASIS,
                {
                    "coefficient_x": self.trial.truth.coefficient_x,
                    "coefficient_y": self.trial.truth.coefficient_y,
                },
                scan_label=scan.scan_label,
            )
            np.testing.assert_array_equal(scan.truth_factors, expected)
            self.assertEqual(
                scan.factor_table_sha256,
                SYNTHETIC_FACTOR_TABLE.factor_table_sha256,
            )
            self.assertEqual(
                scan.factor_basis_sha256,
                SYNTHETIC_FACTOR_BASIS.basis_sha256,
            )

        scan = background.scans[0]
        forged_factors = np.array(scan.truth_factors, copy=True)
        forged_factors[0] = np.nextafter(forged_factors[0], np.inf)
        forged_factors.setflags(write=False)
        forged = replace(
            scan,
            truth_factors=forged_factors,
            truth_factors_sha256=hashlib.sha256(
                np.ascontiguousarray(forged_factors, dtype="<f8").tobytes()
            ).hexdigest(),
            scan_sha256="",
        )
        forged = replace(
            forged,
            scan_sha256=hashlib.sha256(
                canonical_json_bytes(
                    forged.identity_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "do not reproduce"):
            validate_native_background_scan(forged)

    def test_native_product_is_reproducible_and_track_bound(self):
        first = inject_native_before_filter(synthetic_background(self.trial), self.trial)
        second = inject_native_before_filter(synthetic_background(self.trial), self.trial)
        self.assertEqual(first.injected_native_sha256, second.injected_native_sha256)
        self.assertEqual(
            [item.observed_truth_hz_sha256 for item in first.scans],
            [item.observed_truth_hz_sha256 for item in second.scans],
        )
        validate_injected_native_trial(first, self.trial)

    def test_background_and_injected_mutations_fail(self):
        background = synthetic_background(self.trial)
        altered_values = np.array(background.scans[0].normalized, copy=True)
        altered_values[0, 0] = 1.0
        forged_scan = replace(background.scans[0], normalized=altered_values)
        with self.assertRaises(V0P6IncompleteError):
            validate_native_background_scan(forged_scan)
        injected = inject_native_before_filter(background, self.trial)
        forged_injected = replace(
            injected,
            scans=(replace(injected.scans[0], injection_write_count=0), *injected.scans[1:]),
        )
        with self.assertRaises(V0P6IncompleteError):
            validate_injected_native_trial(forged_injected, self.trial)

        altered_injection = np.array(injected.scans[0].normalized, copy=True)
        altered_injection[0, 0] = 1.0
        altered_injection.setflags(write=False)
        forged_scan = replace(
            injected.scans[0],
            normalized=altered_injection,
            normalized_sha256=hashlib.sha256(
                np.ascontiguousarray(altered_injection, dtype="<f4").tobytes()
            ).hexdigest(),
            scan_sha256="",
        )
        forged_scan = replace(
            forged_scan,
            scan_sha256=hashlib.sha256(
                canonical_json_bytes(
                    forged_scan.identity_record(include_identity=False)
                )
            ).hexdigest(),
        )
        forged_product = replace(
            injected,
            scans=(forged_scan, *injected.scans[1:]),
            injected_native_sha256="",
        )
        forged_product = replace(
            forged_product,
            injected_native_sha256=hashlib.sha256(
                canonical_json_bytes(
                    forged_product.identity_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "do not reproduce"):
            validate_injected_native_trial(forged_product, self.trial)

    def test_missing_native_support_fails(self):
        trial = self.trial
        geometry = NativeFrequencyGeometry(
            raw_zero_hz=trial.truth.proxy_carrier_hz,
            channel_width_hz=1.0,
            channel_count=3,
        )
        scans = [
            seal_native_background_scan(
                f"epoch{epoch + 1}_on",
                epoch,
                np.zeros((1, 3), dtype=np.float32),
                geometry,
                truth=trial.truth,
                factor_basis=SYNTHETIC_FACTOR_BASIS,
                factor_table=SYNTHETIC_FACTOR_TABLE,
            )
            for epoch in range(3)
        ]
        background = seal_native_trial_background(
            trial, scans, context_sha256=CONTEXT_SHA256
        )
        with self.assertRaises(V0P6CoverageError):
            inject_native_before_filter(background, trial)

    def test_strict_m37_background_rejects_unattested_source_substitution(self):
        with self.assertRaisesRegex(V0P6ContractError, "one-shot"):
            seal_m37_native_trial_background(
                self.trial,
                (object(), object(), object()),
                factor_basis=SYNTHETIC_FACTOR_BASIS,
                factor_table=SYNTHETIC_FACTOR_TABLE,
            )
        with self.assertRaises(V0P6IncompleteError):
            seal_m37_native_trial_background(
                self.trial,
                iter((object(), object(), object())),
                factor_basis=SYNTHETIC_FACTOR_BASIS,
                factor_table=SYNTHETIC_FACTOR_TABLE,
            )


class RecoveryAndLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = make_m37_prospective_completeness_plan()
        cls.trials = iter_m37_completeness_trials(cls.plan)
        cls.threshold = synthetic_threshold()

    def test_inclusive_threshold_and_twenty_hz_boundaries(self):
        trial = self.trials[3 * M37_COMPLETENESS_TRUTHS_PER_LEVEL]
        threshold = synthetic_threshold(7.0)
        background = synthetic_background(trial)
        injected = inject_native_before_filter(background, trial)
        masks = make_synthetic_mask_replay_receipt(injected, trial)
        derived = make_synthetic_trial_evaluation(
            trial, injected, masks, threshold
        )
        self.assertTrue(derived.recovered)
        self.assertEqual(
            derived.final_disposition, "scientific_candidate_unresolved"
        )
        self.assertLessEqual(
            derived.truth_match_maximum_track_distance_hz, 20.0
        )
        validate_trial_evaluation(
            derived, trial, injected, masks, threshold
        )

        # Rehashing freely chosen physical/rank-p fields cannot manufacture a
        # factory receipt, even when every local boolean is made self-consistent.
        forged = replace(
            derived,
            physical_disposition="rfi_veto_local_off_track",
            physical_vetoed=True,
            recovered=False,
            final_disposition="rfi_veto_local_off_track",
            evaluation_sha256="",
        )
        forged = replace(
            forged,
            evaluation_sha256=hashlib.sha256(
                canonical_json_bytes(
                    forged.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaises(V0P6ContractError):
            validate_trial_evaluation(
                forged, trial, injected, masks, threshold
            )

        import seti_repeater.completeness_v0p6 as completeness

        encoded = completeness._TRIAL_EVALUATION_ATTESTATIONS.pop(
            derived.evaluation_sha256
        )
        try:
            with self.assertRaises(V0P6ContractError):
                validate_trial_evaluation(
                    derived, trial, injected, masks, threshold
                )
            validate_trial_evaluation(
                derived,
                trial,
                injected,
                masks,
                threshold,
                expected_evaluation_sha256=derived.evaluation_sha256,
            )
        finally:
            completeness._TRIAL_EVALUATION_ATTESTATIONS[
                derived.evaluation_sha256
            ] = encoded

    def test_mask_inventory_and_capacity_fail_closed(self):
        trial = self.trials[0]
        background = synthetic_background(trial)
        injected = inject_native_before_filter(background, trial)
        with self.assertRaises(V0P6ContractError):
            seal_mask_replay_receipt(injected)
        good_masks = make_synthetic_mask_replay_receipt(injected, trial)
        bad_masks = replace(
            good_masks,
            source_epoch_product_count=(
                M37_COMPLETENESS_EXPECTED_MASK_SOURCE_PRODUCTS - 1
            ),
            receipt_sha256="",
        )
        bad_masks = replace(
            bad_masks,
            receipt_sha256=hashlib.sha256(
                canonical_json_bytes(
                    bad_masks.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        from seti_repeater.completeness_v0p6 import validate_mask_replay_receipt

        with self.assertRaises(V0P6IncompleteError):
            validate_mask_replay_receipt(bad_masks, injected)

        over_cap = replace(
            good_masks,
            maximum_live_native_bytes_observed=(
                M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL + 1
            ),
            receipt_sha256="",
        )
        over_cap = replace(
            over_cap,
            receipt_sha256=hashlib.sha256(
                canonical_json_bytes(
                    over_cap.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaises(V0P6IncompleteError):
            validate_mask_replay_receipt(over_cap, injected)

        numeric_digest = replace(
            good_masks,
            mask_inventory_sha256=int("7" * 64),
            receipt_sha256="",
        )
        numeric_digest = replace(
            numeric_digest,
            receipt_sha256=hashlib.sha256(
                canonical_json_bytes(
                    numeric_digest.as_record(include_identity=False)
                )
            ).hexdigest(),
        )
        with self.assertRaises(V0P6ContractError):
            validate_mask_replay_receipt(numeric_digest, injected)

        # A trusted digest is the explicit cross-process boundary.  Without
        # it, clearing the live receipt makes the exact same artifact invalid.
        import seti_repeater.completeness_v0p6 as completeness

        encoded = completeness._MASK_REPLAY_RECEIPT_ATTESTATIONS.pop(
            good_masks.receipt_sha256
        )
        try:
            with self.assertRaises(V0P6ContractError):
                validate_mask_replay_receipt(good_masks, injected)
            validate_mask_replay_receipt(
                good_masks,
                injected,
                expected_receipt_sha256=good_masks.receipt_sha256,
            )
        finally:
            completeness._MASK_REPLAY_RECEIPT_ATTESTATIONS[
                good_masks.receipt_sha256
            ] = encoded

    def test_template_mask_stage_accounts_retained_arrays_and_scratch(self):
        import seti_repeater.completeness_v0p6 as completeness

        base = 400_000_000
        epoch_payloads = (8_000_000,) * len(M37_SPECTRAL_WIDTHS)
        mask_payload = 2_000_000
        peak = completeness._template_mask_replay_live_bytes(
            base, epoch_payloads, mask_payload
        )
        self.assertEqual(
            peak,
            base
            + sum(epoch_payloads)
            + mask_payload
            + 6 * max(epoch_payloads)
            + 4 * mask_payload,
        )
        self.assertGreater(peak, base + 50_000_000 + 1_000_000)
        self.assertLess(
            peak, M37_COMPLETENESS_MAXIMUM_LIVE_NATIVE_BYTES_PER_TRIAL
        )

    def test_duplicate_and_incomplete_ledgers_are_permanently_invalid(self):
        trial = self.trials[0]
        artifacts = synthetic_artifacts(trial, self.threshold)
        ledger = CompletenessLedger(self.plan, self.threshold)
        ledger.add_trial(trial, *artifacts)
        with self.assertRaises(V0P6IncompleteError):
            ledger.add_trial(trial, *artifacts)
        with self.assertRaises(V0P6IncompleteError):
            ledger.finalize()
        incomplete = CompletenessLedger(self.plan, self.threshold)
        with self.assertRaises(V0P6IncompleteError):
            incomplete.finalize()

    def test_production_wrapper_rejects_synthetic_threshold_receipt(self):
        with self.assertRaises(V0P6ContractError):
            run_streaming_m37_completeness(
                self.plan,
                self.threshold,
                SyntheticDataSource(),
                SyntheticOperationalPipeline(),
            )

    def test_wilson_known_answers(self):
        low, high = wilson_interval_95(512, 512)
        self.assertAlmostEqual(high, 1.0)
        self.assertAlmostEqual(low, 0.9925530242771171)
        zero_low, zero_high = wilson_interval_95(0, 512)
        self.assertEqual(zero_low, 0.0)
        self.assertAlmostEqual(zero_high, 1.0 - low)


class FullSyntheticInventoryTests(unittest.TestCase):
    def test_full_streaming_inventory_summaries_and_mutation_detection(self):
        plan = make_m37_prospective_completeness_plan()
        threshold = synthetic_threshold(7.0)
        result = run_streaming_completeness(
            plan,
            threshold,
            SyntheticDataSource(),
            SyntheticOperationalPipeline(),
        )
        self.assertEqual(result["completed_trial_count"], 6_144)
        self.assertTrue(result["certificate"]["all_trials_accounted_exactly_once"])
        self.assertFalse(result["truncation_permitted"])
        self.assertEqual([item["recovered"] for item in result["levels"][:3]], [0, 0, 0])
        self.assertEqual([item["recovered"] for item in result["levels"][3:]], [512] * 9)
        summaries = result["threshold_summaries"]
        self.assertEqual(
            summaries["point_estimate_50_percent"]["first_tested_snr_at_or_above_target"],
            7.0,
        )
        self.assertEqual(
            summaries["point_estimate_90_percent"]["first_tested_snr_at_or_above_target"],
            7.0,
        )
        validate_completeness_result(result, plan, threshold)
        mutated = json.loads(json.dumps(result))
        mutated["trials"][0]["evaluation"]["recovered"] = True
        with self.assertRaises(V0P6IncompleteError):
            validate_completeness_result(mutated, plan, threshold)


if __name__ == "__main__":
    unittest.main()
