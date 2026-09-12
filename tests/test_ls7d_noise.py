import unittest
import numpy as np
from seti_repeater.tess_noise_diagnostic import (
    sideband_differences, covariance_accounting, decompose_noise,
)


class NoiseAccountingTests(unittest.TestCase):
    def test_never_bridge_sideband_gap(self):
        a = np.arange(6.)[:, None]
        b = a+10000
        d, layout = sideband_differences([a, b], 2)
        np.testing.assert_array_equal(d, np.full((4, 1), 2.))
        self.assertEqual(layout["unused_tail_samples_per_side"], [0, 0])

    def test_block_tails_are_explicit(self):
        d, layout = sideband_differences([np.arange(11.)[:, None]]*2, 3)
        self.assertEqual(layout["unused_tail_samples_per_side"], [2, 2])
        np.testing.assert_array_equal(d, np.full((4, 1), 3.))

    def test_perfect_common_mode_doubles_variance_ratio(self):
        d = np.array([-2., -1., 1., 2.])
        r = covariance_accounting(np.column_stack([d, d]))
        self.assertAlmostEqual(r["covariance_sum_to_diagonal_variance_ratio"], 2.)

    def test_anticorrelation_cancels_aperture(self):
        d = np.array([-2., -1., 1., 2.])
        r = covariance_accounting(np.column_stack([d, -d]))
        self.assertEqual(r["scalar_variance"], 0.)
        self.assertIsNone(r["diagonal_to_projected_sigma_ratio"])
        self.assertAlmostEqual(r["cross_variance"], -r["diagonal_variance"])

    def test_covariance_against_manual_known_answer(self):
        d = np.array([[1., 2.], [3., 4.], [5., 0.]])
        r = covariance_accounting(d)
        np.testing.assert_allclose(r["covariance"], [[2., -1.], [-1., 2.]])
        self.assertEqual(r["scalar_variance"], 2.)

    def test_pixel_permutation_and_units(self):
        d = np.array([[1., 2., -4.], [3., 4., 1.], [5., 0., 2.], [-1., 3., 9.]])
        original = covariance_accounting(d)
        changed = covariance_accounting(10*d[:, ::-1])
        self.assertAlmostEqual(changed["scalar_variance"], 100*original["scalar_variance"])
        self.assertAlmostEqual(changed["diagonal_to_projected_sigma_ratio"], original["diagonal_to_projected_sigma_ratio"])

    def test_error_floor_and_covariance_are_separate(self):
        t = np.arange(60.)
        x = np.column_stack([np.sin(t), np.cos(1.7*t)])
        r = decompose_noise([x, x+100], [x, x+100], [np.full_like(x, 50.)]*2, [True, True], 1.)
        self.assertEqual(r["supplied_dominant_aperture_pixels"], 2)
        self.assertAlmostEqual(r["quadrature_ls7c_sigma"], np.sqrt(5000.))
        self.assertLess(r["factorization_absolute_error"], 1e-10)

    def test_invalid_differences_fail(self):
        with self.assertRaises(ValueError):
            sideband_differences([np.array([[1.], [np.nan]])])
        with self.assertRaises(ValueError):
            covariance_accounting(np.ones((1, 2)))


if __name__ == "__main__":
    unittest.main()
