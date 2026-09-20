"""Known-answer and leakage tests before opening LS8M's retained native inputs."""
import unittest
import numpy as np
from seti_repeater.cheops_residual_noise import (
    temporal, prepare, operator, model_result, correction_account, injections, spatial)

SIDE = np.r_[np.arange(12), np.arange(17, 29)]


def example_state():
    u = np.linspace(-2, 2, 31)
    x = np.column_stack([10 + u * u, np.sin(u), np.cos(1.3 * u), np.ones(len(u))])
    phase = np.sin(np.arange(24) * 0.7)
    side = phase[:, None] * (2 + 0.2 * u)[None, :]
    s2 = np.sum(side * side, axis=0) / 22
    return {'x': x, 'side': side, 's2': s2, 'variance': 1.1 * (s2 + np.median(s2)) / 2,
        'h': 1.1, 'df': 22, 'y': np.cos(u * 4), 'mask': np.ones(len(u), bool),
        'xy': np.column_stack([np.arange(len(u)), np.zeros(len(u))]), 'center': np.array([15., 0.])}


def synthetic_cube():
    yy, xx = np.indices((101, 101)); t = np.arange(29, dtype=float)
    p = 15000 * np.exp(-((xx - 50.3) ** 2 + (yy - 49.7) ** 2) / 180) + 200
    noise = 2 + (xx + 2 * yy) / 30
    cube = p[None, :, :] + t[:, None, None] * .02 + np.sin(t * 1.1)[:, None, None] * noise
    return t, cube, np.ones((101, 101), bool), [50.3, 49.7]


class ResidualNoiseTests(unittest.TestCase):
    def test_temporal_brightness_and_displacement_signed_known_answer(self):
        t = np.arange(29, dtype=float); yy, xx = np.indices((5, 6))
        base = 1e6 + 100 * xx + yy * yy
        cube = base[None] + t[:, None, None] * (0.3 + xx * .001)
        for sign in (-1, 1):
            pulse = sign * (.001 * base + .05 * (100 + 2 * yy))
            changed = cube.copy(); changed[14] += pulse
            event, side, _, _ = temporal(t, changed, SIDE, 14, np.ones(base.shape, bool))
            np.testing.assert_allclose(event, pulse.ravel(), atol=1e-9, rtol=1e-12)
            np.testing.assert_allclose(side, 0, atol=1e-9)

    def test_weighted_combined_recovers_signed_coefficients(self):
        state = example_state()
        for sign in (-1, 1):
            expected = sign * np.array([.001, .05, -.03, 7.])
            state['y'] = state['x'] @ expected
            result, residual, _ = model_result(state, [0, 1, 2, 3])
            np.testing.assert_allclose(result['coefficients'], expected, atol=1e-11)
            np.testing.assert_allclose(residual, 0, atol=1e-11)

    def test_target_never_sets_noise_weights_or_template(self):
        t, cube, valid, center = synthetic_cube()
        first = prepare(t, cube, SIDE, 14, valid, center)
        changed = cube.copy(); changed[14, 51, 49] += 1e8
        second = prepare(t, changed, SIDE, 14, valid, center)
        for key in ('x', 'variance', 's2', 'side', 'mask'):
            np.testing.assert_array_equal(first[key], second[key])
        self.assertGreater(np.max(np.abs(first['y'] - second['y'])), 9e7)

    def test_loso_held_value_never_enters_training(self):
        t, cube, valid, center = synthetic_cube(); held = 3; train = SIDE[SIDE != held]
        first = prepare(t, cube, train, held, valid, center)
        changed = cube.copy(); changed[held] += 9000; changed[14] -= 1e5
        second = prepare(t, changed, train, held, valid, center)
        for key in ('x', 'variance', 'side', 'mask'):
            np.testing.assert_array_equal(first[key], second[key])
        np.testing.assert_allclose(second['y'] - first['y'], 9000, atol=1e-8)

    def test_common_mode_aperture_noise_keeps_cross_pixel_covariance(self):
        state = example_state(); n = len(state['y'])
        state['side'] = np.tile(np.sin(np.arange(24))[:, None], (1, n))
        state['s2'] = np.sum(state['side'] ** 2, axis=0) / 22
        result, _, _ = model_result(state, [0, 1, 2, 3])
        self.assertAlmostEqual(result['aperture_correlation_sd_ratio'], np.sqrt(n), places=12)

    def test_paired_correction_keeps_negative_cross_term(self):
        cor = example_state(); cal = example_state(); cal['y'] = 2 * cor['y']
        account = correction_account(cal, cor)
        for metric in ('raw', 'weighted'):
            self.assertAlmostEqual(account[metric]['cal_over_cor'], 4, places=12)
            self.assertAlmostEqual(account[metric]['delta_over_cor'], 1, places=12)
            self.assertAlmostEqual(account[metric]['twice_cross_over_cor'], -4, places=12)
            self.assertLess(abs(account[metric]['closure_relative_error']), 1e-12)

    def test_compact_known_answer_and_fixed_signed_injections(self):
        state = example_state(); residual = np.zeros(len(state['y'])); residual[16] = -50
        result = spatial(state, residual)
        self.assertEqual(result['concentration']['raw']['top1_fraction'], 1)
        self.assertEqual(result['concentration']['raw']['maximum_xy'], [16, 0])
        controls = injections(state)
        self.assertEqual(len(controls), 16)
        for r in controls:
            self.assertLess(r['additive_linearity_max_error'], 1e-10)
            if r['expected_combined_coefficients'] is not None:
                np.testing.assert_allclose(r['pure_combined_coefficients'], r['expected_combined_coefficients'], atol=1e-10)
        for a, b in zip(controls[::2], controls[1::2]):
            self.assertEqual((a['sign'], b['sign']), (-1, 1))
            self.assertAlmostEqual(a['displacement_removal_retained_weighted_energy_fraction'], b['displacement_removal_retained_weighted_energy_fraction'], places=13)

    def test_zero_variance_fails_without_silent_floor_or_new_pixels(self):
        t, cube, valid, center = synthetic_cube()
        cube[:] = cube[0]
        with self.assertRaisesRegex(AssertionError, 'NO_POSITIVE_SIDEBAND_VARIANCE'):
            prepare(t, cube, SIDE, 14, valid, center)


if __name__ == '__main__':
    unittest.main()
