"""Finite-exposure tests with analytic and independent midpoint quadrature cases."""
import unittest
import numpy as np
from seti_repeater.exposure_radio import linear_exposure_profile as profile, add_linear_exposure


class ExposureTests(unittest.TestCase):
    def test_stationary_and_exact_boundary(self):
        p = profile(100, 40, 40, 0); self.assertEqual(p[40], 1.)
        p = profile(100, 40.5, 40.5, 0)
        np.testing.assert_array_equal(p[40:42], [.5,.5])
        p = profile(100, 40, 40, 3)
        np.testing.assert_array_equal(p[39:42], np.full(3,1/3))

    def test_sweep_and_reversal(self):
        p = profile(100, 20.5, 40.5, 0)
        np.testing.assert_array_equal(p[21:41], np.full(20,1/20))
        np.testing.assert_array_equal(p,profile(100,40.5,20.5,0))
        self.assertAlmostEqual(p.sum(),1.,places=14)

    def test_finite_width_against_independent_time_quadrature(self):
        channels=np.arange(100); left=channels-.5; right=channels+.5
        for a,b,w in [(20.2,42.7,3.),(40.1,40.100001,1.),(30.,31.,17.),(60.2,38.1,.25)]:
            # Midpoint quadrature, directly intersecting intervals at each time.
            expected=np.zeros(100)
            count=40000
            for start in range(0,count,1000):
                centers=a+(b-a)*(np.arange(start,start+1000)+.5)/count
                overlap=np.maximum(0,np.minimum(right,centers[:,None]+w/2)
                                    -np.maximum(left,centers[:,None]-w/2))/w
                expected += overlap.sum(axis=0)/count
            np.testing.assert_allclose(profile(100,a,b,w),expected,rtol=0,atol=2e-8)

    def test_support_and_numeric_failures_are_not_truncated(self):
        for args in [(100,0,0,3),(100,80,101,0),(100,20,30,-1),(100,20,np.inf,1)]:
            with self.assertRaises(ValueError): profile(*args)

    def test_raw_injection_before_normalization_preserves_input(self):
        raw=np.full((3,100),100.,dtype='<f4'); original=raw.copy()
        added=add_linear_exposure(raw,[20,21,22],[30,31,32],intrinsic_width_channels=3,total_power=50.)
        np.testing.assert_array_equal(raw,original)
        np.testing.assert_allclose((added-raw).sum(axis=1),50.,atol=1e-4,rtol=0)
        self.assertEqual(added.dtype,np.dtype('<f4'))


if __name__=='__main__': unittest.main()
