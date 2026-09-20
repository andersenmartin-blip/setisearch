"""Prospective mixed-duration, cadence, leakage and independent known answers."""
import json
import unittest
import numpy as np
from seti_repeater.cheops_duration_noise import (
    layout, training_rows, temporal, prepare, describe, boundary_account, injections)
from seti_repeater.cheops_three_sum_noise import prepare as legacy_prepare
from ls8u_audit import reconstruct, description, boundary


def cube_example(duration, cadence):
    yy, xx = np.indices((101, 101)); n = 28 + duration
    t = np.arange(n, dtype=float) * cadence
    p = 15000 * np.exp(-((xx - 50.3) ** 2 + (yy - 49.7) ** 2) / 180) + 200
    cube = p[None] + t[:, None, None] * .002
    cube += np.sin(np.arange(n) * .7)[:, None, None] * (2 + xx / 40 + yy / 20)
    cube += np.cos(np.arange(n) * 1.3)[:, None, None] * (1 + (xx % 7) / 8)
    return t, cube, np.ones((101, 101), bool), [50.3, 49.7]


class DurationNoiseTests(unittest.TestCase):
    def test_both_durations_signed_brightness_gradient_compact_and_guards(self):
        yy, xx = np.indices((5, 6)); profile = 1e6 + 100 * xx + yy ** 2
        compact = np.zeros_like(profile); compact[2, 3] = 17
        for d, cadence in ((1, 49), (3, 42)):
            side, event, _ = layout(d); t = np.arange(28 + d) * cadence
            base = profile[None] + t[:, None, None] * (.3 + .001 * xx)
            guards = np.setdiff1d(np.arange(28 + d), np.r_[side, event])
            for signal in (.001 * profile, .05 * (100 + 2 * yy), compact):
                for sign in (-1, 1):
                    cube = base.copy(); cube[event] += sign * signal; cube[guards] += 1e8
                    y, residual, _, w, _ = temporal(t, cube, side, event, np.ones(profile.shape, bool))
                    np.testing.assert_allclose(y, d * sign * signal.ravel(), atol=2e-9, rtol=1e-11)
                    np.testing.assert_allclose(residual, 0, atol=2e-9)
                    self.assertAlmostEqual(w.sum(), 0, places=14)
                    self.assertAlmostEqual(w @ t, 0, places=10)

    def test_exact_iid_prediction_includes_duration_squared_baseline_term(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, _ = cube_example(d, cadence); side, event, _ = layout(d)
            _, _, _, w, projection = temporal(t, cube, side, event, common)
            expected = d + d * d / 24 + np.sum(t[event] - t[side].mean()) ** 2 / np.sum((t[side] - t[side].mean()) ** 2)
            self.assertAlmostEqual(w @ w, expected, places=14)
            self.assertAlmostEqual(np.trace(projection), 22, places=13)

    def test_cadence_specific_gaps_psd_and_explicit_quadratic_form(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, _ = layout(d)
            # 0.6 cadence is valid; 1.6 cadence is a gap, even though both are <90 s.
            t[4:] -= .4 * cadence; t[20:] += .6 * cadence
            state = prepare(t, cube, side, event, common, center, cadence)
            w = state['row_weights']; corr = state['correlation']
            self.assertGreater(np.linalg.eigvalsh(corr)[0], 0)
            expected = sum(w[i] * w[j] * corr[i, j] for i in range(len(t)) for j in range(len(t)))
            self.assertAlmostEqual(state['h'], expected, places=12)
            self.assertEqual(state['temporal']['cadence_segments'], 2)
            self.assertNotEqual(corr[3, 4], 0)
            self.assertEqual(corr[19, 20], 0)
            self.assertEqual(corr[18, 20], 0)
            self.assertLess(abs(state['temporal']['rho_lag1']), 2 / 3)
            self.assertLess(abs(state['temporal']['rho_lag2']), 1 / 3)

    def test_native_event_cannot_set_template_noise_or_covariance(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, _ = layout(d)
            first = prepare(t, cube, side, event, common, center, cadence)
            cube[event, 51, 49] += 1e7
            second = prepare(t, cube, side, event, common, center, cadence)
            for key in ('x', 'side', 's2', 'variance', 'correlation', 'row_weights', 'mask'):
                np.testing.assert_array_equal(first[key], second[key])
            self.assertGreater(np.max(second['y'] - first['y']), d * .99e7)

    def test_all_24_single_and_8_triple_held_targets_exclude_guards(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, blocks = layout(d)
            self.assertEqual(len(blocks), 24 // d)
            np.testing.assert_array_equal(np.concatenate(blocks), side)
            for block in blocks:
                train = training_rows(side, block)
                self.assertTrue(all(abs(i - j) > 2 for i in train for j in block))
                self.assertFalse(np.intersect1d(train, event).size)
                first = prepare(t, cube, train, block, common, center, cadence)
                changed = cube.copy(); changed[np.setdiff1d(np.arange(28 + d), train)] += 9000
                second = prepare(t, changed, train, block, common, center, cadence)
                for key in ('x', 'side', 'variance', 'correlation', 'mask'):
                    np.testing.assert_array_equal(first[key], second[key])
                np.testing.assert_allclose(second['y'] - first['y'], d * 9000, atol=1e-8)

    def test_independent_long_double_reconstruction_both_durations_and_gaps(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, blocks = layout(d)
            t[4:] -= .4 * cadence; t[20:] += .6 * cadence
            for train, target in ((side, event), (training_rows(side, blocks[2]), blocks[2])):
                a = prepare(t, cube, train, target, common, center, cadence)
                b = reconstruct(t, cube, train.tolist(), target.tolist(), common, center, cadence)
                for key in ('y', 'side', 'x', 's2', 'variance', 'correlation', 'row_weights'):
                    np.testing.assert_allclose(a[key], b[key], atol=1e-7, rtol=2e-8)
                aa, _ = describe(a); bb, _ = description(b)
                for name in aa['models']:
                    np.testing.assert_allclose(aa['models'][name]['coefficients'], bb['models'][name]['coefficients'], atol=1e-8, rtol=2e-8)
                    self.assertAlmostEqual(aa['models'][name]['weighted_residual_to_sideband_ratio'], bb['models'][name]['weighted_residual_to_sideband_ratio'], places=7)

    def test_boundary_signed_identity_and_independent_json_serialization(self):
        c0 = np.array([[True, True, False], [False, False, False]])
        c1 = np.array([[False, True, True], [False, False, False]])
        cal = np.array([[10., -20., 5.], [0., 0., 0.]])
        cor = np.array([[5., -20., -7.], [0., 0., 0.]])
        maps = {'CAL': cal, 'COR': cor, 'DELTA': cor - cal}
        a = boundary_account(maps, [c0, c1]); b = boundary(maps, [c0, c1])
        self.assertEqual(json.loads(json.dumps(a, allow_nan=False)), json.loads(json.dumps(b, allow_nan=False)))
        self.assertEqual(a['products']['COR']['difference_flux_adu'], -12)
        self.assertEqual(a['products']['CAL']['difference_flux_adu'], -5)
        for product in a['products'].values():
            for measure in ('flux_adu', 'energy_adu2'):
                self.assertEqual(product['closure_relative_' + measure], 0)

    def test_signed_controls_recover_duration_coefficients_and_record_loss(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, _ = layout(d)
            records = injections(prepare(t, cube, side, event, common, center, cadence))
            self.assertEqual(len(records), 16)
            for r in records:
                self.assertEqual(r['exposures'], d)
                self.assertLess(r['additive_linearity_max_error'], 1e-9)
                if r['expected_combined_coefficients'] is not None:
                    np.testing.assert_allclose(r['pure_combined_coefficients'], r['expected_combined_coefficients'], atol=1e-9)
                self.assertTrue(np.isfinite(r['displacement_removal_retained_weighted_energy_fraction']))
            for minus, plus in zip(records[::2], records[1::2]):
                self.assertAlmostEqual(minus['displacement_removal_retained_weighted_energy_fraction'], plus['displacement_removal_retained_weighted_energy_fraction'], places=12)

    def test_zero_variance_fails_without_floor_or_mask_change(self):
        for d, cadence in ((1, 49), (3, 42)):
            t, cube, common, center = cube_example(d, cadence); side, event, _ = layout(d)
            cube[:] = cube[0]
            with self.assertRaisesRegex(AssertionError, 'NO_POSITIVE_SIDEBAND_VARIANCE'):
                prepare(t, cube, side, event, common, center, cadence)

    def test_legacy_three_row_60_second_model_is_unchanged(self):
        t, cube, common, center = cube_example(3, 60); side, event, _ = layout(3)
        new = prepare(t, cube, side, event, common, center, 60)
        old = legacy_prepare(t, cube, side, event, common, center)
        for key in old:
            if key == 'temporal':
                info = new[key].copy(); self.assertEqual(info.pop('cadence_seconds'), 60.)
                self.assertEqual(info, old[key])
            else:
                np.testing.assert_array_equal(new[key], old[key])


if __name__ == '__main__':
    unittest.main()
