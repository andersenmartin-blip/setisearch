"""Prospective known-answer, leakage and covariance tests for LS8P."""
import unittest
import numpy as np
from seti_repeater.cheops_three_sum_noise import (
    SIDE, EVENT, BLOCKS, training_rows, temporal, covariance, prepare, describe,
    boundary_account, injections)
from ls8p_audit import reconstruct, description


def cube_example():
    yy, xx = np.indices((101, 101)); t = np.arange(31, dtype=float) * 60
    p = 15000 * np.exp(-((xx - 50.3) ** 2 + (yy - 49.7) ** 2) / 180) + 200
    cube = p[None] + t[:, None, None] * .002
    cube += np.sin(np.arange(31) * .7)[:, None, None] * (2 + xx / 40 + yy / 20)
    cube += np.cos(np.arange(31) * 1.3)[:, None, None] * (1 + (xx % 7) / 8)
    return t, cube, np.ones((101, 101), bool), [50.3, 49.7]


class ThreeSumNoiseTests(unittest.TestCase):
    def test_three_exposure_brightness_displacement_compact_both_signs(self):
        t = np.arange(31, dtype=float) * 60; yy, xx = np.indices((5, 6))
        profile = 1e6 + 100 * xx + yy ** 2
        base = profile[None] + t[:, None, None] * (.3 + .001 * xx)
        compact = np.zeros_like(profile); compact[2, 3] = 17
        for signal in (.001 * profile, .05 * (100 + 2 * yy), compact):
            for sign in (-1, 1):
                cube = base.copy(); cube[EVENT] += sign * signal
                cube[[12, 13, 17, 18]] += 1e8
                event, side, _, weights, _ = temporal(t, cube, SIDE, EVENT, np.ones(profile.shape, bool))
                np.testing.assert_allclose(event, 3 * sign * signal.ravel(), atol=2e-9, rtol=1e-11)
                np.testing.assert_allclose(side, 0, atol=2e-9)
                self.assertAlmostEqual(weights.sum(), 0, places=14)
                self.assertAlmostEqual(weights @ t, 0, places=10)

    def test_iid_sum_prediction_variance_includes_nine_over_n(self):
        t, cube, common, _ = cube_example()
        _, _, _, weights, projection = temporal(t, cube, SIDE, EVENT, common)
        expected = 3 + 9 / 24 + (np.sum(t[EVENT] - t[SIDE].mean())) ** 2 / np.sum((t[SIDE] - t[SIDE].mean()) ** 2)
        self.assertAlmostEqual(weights @ weights, expected, places=14)
        self.assertAlmostEqual(np.trace(projection), 22, places=13)

    def test_correlated_propagation_psd_and_exact_quadratic_form(self):
        t, cube, common, center = cube_example()
        for times in (t, t + np.where(np.arange(31) >= 20, 3000, 0)):
            state = prepare(times, cube, SIDE, EVENT, common, center)
            w = state['row_weights']; R = state['correlation']
            self.assertGreater(np.linalg.eigvalsh(R)[0], 0)
            expected = sum(w[i] * w[j] * R[i, j] for i in range(31) for j in range(31))
            self.assertAlmostEqual(state['h'], expected, places=12)
            self.assertLess(abs(state['temporal']['rho_lag1']), 2 / 3)
            self.assertLess(abs(state['temporal']['rho_lag2']), 1 / 3)
            if times[20] - times[19] > 90: self.assertEqual(R[19, 20], 0)

    def test_event_cannot_set_template_noise_or_covariance(self):
        t, cube, common, center = cube_example(); first = prepare(t, cube, SIDE, EVENT, common, center)
        cube[EVENT, 51, 49] += 1e7
        second = prepare(t, cube, SIDE, EVENT, common, center)
        for key in ('x', 'side', 's2', 'variance', 'correlation', 'row_weights', 'mask'):
            np.testing.assert_array_equal(first[key], second[key])
        self.assertGreater(np.max(second['y'] - first['y']), 2.9e7)

    def test_all_eight_held_blocks_and_guards_are_excluded(self):
        t, cube, common, center = cube_example()
        for block in BLOCKS:
            train = training_rows(block)
            self.assertTrue(all(abs(i - j) > 2 for i in train for j in block))
            first = prepare(t, cube, train, block, common, center)
            changed = cube.copy(); changed[np.setdiff1d(np.arange(31), train)] += 9000
            second = prepare(t, changed, train, block, common, center)
            for key in ('x', 'side', 'variance', 'correlation', 'mask'):
                np.testing.assert_array_equal(first[key], second[key])
            np.testing.assert_allclose(second['y'] - first['y'], 27000, atol=1e-8)

    def test_independent_long_double_reconstruction(self):
        t, cube, common, center = cube_example(); t[20:] += 3000
        for train, target in ((SIDE, EVENT), (training_rows(BLOCKS[2]), BLOCKS[2])):
            first = prepare(t, cube, train, target, common, center)
            second = reconstruct(t, cube, train.tolist(), target.tolist(), common, center)
            for key in ('y', 'side', 'x', 's2', 'variance', 'correlation', 'row_weights'):
                np.testing.assert_allclose(first[key], second[key], atol=1e-7, rtol=2e-8)
            a, _ = describe(first); b, _ = description(second)
            for name in a['models']:
                np.testing.assert_allclose(a['models'][name]['coefficients'], b['models'][name]['coefficients'], atol=1e-8, rtol=2e-8)
                self.assertAlmostEqual(a['models'][name]['weighted_residual_to_sideband_ratio'], b['models'][name]['weighted_residual_to_sideband_ratio'], places=7)

    def test_exact_boundary_flux_and_energy_identity_with_signed_defects(self):
        c0 = np.array([[True, True, False], [False, False, False]])
        c1 = np.array([[False, True, True], [False, False, False]])
        cal = np.array([[10., -20., 5.], [0., 0., 0.]])
        cor = np.array([[5., -20., -7.], [0., 0., 0.]])
        result = boundary_account({'CAL': cal, 'COR': cor, 'DELTA': cor - cal}, [c0, c1])
        self.assertEqual(result['products']['COR']['difference_flux_adu'], -12)
        self.assertEqual(result['products']['CAL']['difference_flux_adu'], -5)
        for product in result['products'].values():
            for measure in ('flux_adu', 'energy_adu2'):
                self.assertEqual(product['closure_relative_' + measure], 0)

    def test_signed_controls_recover_three_row_coefficients_and_record_loss(self):
        t, cube, common, center = cube_example()
        records = injections(prepare(t, cube, SIDE, EVENT, common, center))
        self.assertEqual(len(records), 16)
        for record in records:
            self.assertEqual(record['exposures'], 3)
            self.assertLess(record['additive_linearity_max_error'], 1e-9)
            if record['expected_combined_coefficients'] is not None:
                np.testing.assert_allclose(record['pure_combined_coefficients'], record['expected_combined_coefficients'], atol=1e-9)
            self.assertTrue(np.isfinite(record['displacement_removal_retained_weighted_energy_fraction']))
        for minus, plus in zip(records[::2], records[1::2]):
            self.assertAlmostEqual(minus['displacement_removal_retained_weighted_energy_fraction'], plus['displacement_removal_retained_weighted_energy_fraction'], places=12)

    def test_zero_variance_fails_without_floor_or_mask_change(self):
        t, cube, common, center = cube_example(); cube[:] = cube[0]
        with self.assertRaisesRegex(AssertionError, 'NO_POSITIVE_SIDEBAND_VARIANCE'):
            prepare(t, cube, SIDE, EVENT, common, center)


if __name__ == '__main__':
    unittest.main()
