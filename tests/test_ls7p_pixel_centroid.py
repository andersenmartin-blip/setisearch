import unittest

import numpy as np

from seti_repeater.tess_pixel_centroid import moments, additive_shift, cr_additions


class PixelCentroidAnswers(unittest.TestCase):
    def test_signed_flux_and_analytic_covariance(self):
        xy = np.array([[0., 0.], [2., 1.], [0., 3.]])
        f = np.array([4., 3., -1.]); e = np.array([2., 1., .5])
        m = moments(f, e, xy)
        np.testing.assert_allclose(m['center_xy'], [1., 0.], atol=1e-14)
        g = np.array([[-1., 0.], [1., 1.], [-1., 3.]])/6
        expected = g.T @ np.diag([4., 1., .25]) @ g
        np.testing.assert_allclose(m['covariance_xy'], expected, atol=1e-14)

    def test_flux_scale_and_coordinate_translation(self):
        xy = np.array([[0., 0.], [2., 1.], [0., 3.]])
        f = np.array([4., 3., 1.]); e = np.ones(3)
        a = moments(f, e, xy); b = moments(7*f, 7*e, xy+[1700., 560.])
        np.testing.assert_allclose(b['center_xy']-a['center_xy'], [1700., 560.], atol=1e-12)
        np.testing.assert_allclose(a['covariance_xy'], b['covariance_xy'], atol=1e-13)

    def test_exact_signed_addition(self):
        xy = np.array([[0., 0.], [2., 1.], [0., 3.]])
        f = np.array([4., 3., 1.]); d = np.array([.5, -.75, 1.25]); e = np.ones(3)
        actual = moments(f+d, e, xy)['center_xy']-moments(f, e, xy)['center_xy']
        np.testing.assert_allclose(additive_shift(f, d, xy), actual, atol=1e-14)

    def test_unknown_correlation_bound(self):
        xy = np.array([[0., 0.], [2., 1.], [0., 3.]])
        m = moments([4., 3., 1.], [2., 1., .5], xy)
        g = (xy-m['center_xy'])/8
        # Rank-one perfectly signed correlation attains the bound for each axis.
        for axis in range(2):
            v = np.array([2., 1., .5])*np.sign(g[:, axis])
            var = g[:, axis] @ np.outer(v, v) @ g[:, axis]
            self.assertAlmostEqual(var, m['correlation_unknown_bound_xy'][axis]**2)

    def test_binary32_rounding_bound(self):
        xy = np.array([[0., 0.], [2., 1.], [0., 3.]])
        f = np.array([1000.123456789, 327.325212, -3.3810113])
        ff = f.astype(np.float32).astype(float)
        actual = (f[:, None]*xy).sum(0)/f.sum()
        m = moments(ff, np.ones(3), xy)
        self.assertTrue(np.all(abs(actual-m['center_xy']) <= m['binary32_centroid_bound_xy']))

    def test_duplicate_cr_records_accumulate(self):
        records = [(100, 701, 301, 3.), (100, 701, 301, -1.), (101, 700, 300, 2.)]
        cube, count = cr_additions([100, 101], records, [700, 300], [2, 2])
        self.assertEqual(cube[0, 1, 1], 2.)
        self.assertEqual(count[0, 1, 1], 2)
        self.assertEqual(cube.sum(), 4.)
        with self.assertRaises(ValueError): cr_additions([100, 100], [], [700, 300], [2, 2])
        with self.assertRaises(ValueError): cr_additions([100], [(101, 700, 300, 1.)], [700, 300], [2, 2])

    def test_invalid_pixels_are_unavailable(self):
        xy = [[0., 0.], [1., 1.]]
        for f, e in [([np.nan, 1.], [1., 1.]), ([1., 1.], [1., 0.]), ([-2., 1.], [1., 1.])]:
            m = moments(f, e, xy)
            self.assertFalse(m['valid'])
            self.assertTrue(np.isnan(m['center_xy']).all())


if __name__ == '__main__': unittest.main()
