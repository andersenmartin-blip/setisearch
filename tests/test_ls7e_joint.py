import unittest
import numpy as np

from seti_repeater.tess_joint_spatial import event_difference, training_covariance, FitBank


class JointSpatialTests(unittest.TestCase):
    def test_actual_event_minus_reference_and_guard(self):
        x = np.full((200, 4), 7.)
        x[90:92] += np.arange(4)
        x[85:90] = 1e8
        d, ref = event_difference(x, 90, 92)
        np.testing.assert_array_equal(d, np.arange(4))
        np.testing.assert_array_equal(ref, np.full(4, 7.))
        with self.assertRaises(ValueError):
            event_difference(x, 50, 52)

    def test_excluded_background_cannot_change_covariance(self):
        rs = [{"anchor": a, "width": 2, "sample_id": str(a), "normalized_delta": [a, -a, a % 2, a % 3]} for a in range(6)]
        c, meta = training_covariance(rs, 0, 2, .05)
        rs[0]["normalized_delta"] = [1e80]*4
        np.testing.assert_array_equal(c, training_covariance(rs, 0, 2, .05)[0])
        self.assertNotIn(0, meta["training_anchors"])
        self.assertGreater(np.linalg.eigvalsh(c).min(), 0.)

    def test_known_anticorrelation_retained(self):
        rs = [{"anchor": 1, "width": 2, "sample_id": str(a), "normalized_delta": [a, -a]} for a in (-2, -1, 1, 2)]
        c, _ = training_covariance(rs, 0, 2, .05)
        self.assertAlmostEqual(c.sum()/np.trace(c), .05, places=8)

    def test_exact_star_plus_sparse_pixel(self):
        p = np.array([0., .1, .2, .3, .25, .15, 0., 0.])
        y = 300*p+11
        y[-1] += 70
        fit = FitBank(np.eye(8), [p], True).fit(y)
        self.assertAlmostEqual(fit["amplitude"], 300)
        self.assertAlmostEqual(fit["background"], 11)
        self.assertEqual(fit["sparse_pixel"], 7)
        self.assertAlmostEqual(fit["sparse_amplitude"], 70)
        self.assertLess(fit["chi2"], 1e-20)
        self.assertAlmostEqual(fit["objective"], 9)

    def test_nonnegative_amplitude(self):
        p = np.arange(8.)/28
        fit = FitBank(np.eye(8), [p], False).fit(7-100*p)
        self.assertEqual(fit["amplitude"], 0.)

    def test_gls_matches_whitened_least_squares(self):
        rng = np.random.default_rng(782)
        z = rng.normal(size=(8, 8)); c = z@z.T+np.eye(8)
        p = np.arange(1., 9.); p /= p.sum()
        y = 100*p+5+rng.normal(size=8)
        f = FitBank(c, [p], False).fit(y)
        l = np.linalg.cholesky(c)
        a = np.column_stack((p, np.ones(8)))
        b = np.linalg.lstsq(np.linalg.solve(l, a), np.linalg.solve(l, y), rcond=None)[0]
        r = np.linalg.solve(l, y-a@b)
        self.assertAlmostEqual(f["amplitude"], b[0])
        self.assertAlmostEqual(f["background"], b[1])
        self.assertAlmostEqual(f["chi2"], r@r)

    def test_pixel_permutation_and_flux_units(self):
        rng = np.random.default_rng(42)
        z = rng.normal(size=(8, 8)); c = z@z.T+np.eye(8)
        p = np.arange(1., 9.)/36; y = 100*p+5
        y[2] += 90
        f = FitBank(c, [p], True).fit(y)
        q = [5, 1, 6, 2, 4, 3, 0, 7]
        g = FitBank(100*c[np.ix_(q, q)], [p[q]], True).fit(10*y[q])
        self.assertAlmostEqual(g["amplitude"], 10*f["amplitude"])
        self.assertAlmostEqual(g["objective"], f["objective"])
        self.assertEqual(q[g["sparse_pixel"]], f["sparse_pixel"])

    def test_null_and_uniform_have_no_source_score(self):
        p = np.arange(8.)/28
        f = FitBank(np.eye(8), [p], True).fit(np.full(8, 33.))
        self.assertLess(f["amplitude_noise_score"], 1e-10)
        self.assertLess(f["objective"], 1e-20)


if __name__ == '__main__':
    unittest.main()
