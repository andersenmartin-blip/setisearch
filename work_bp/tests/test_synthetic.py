"""Deterministic BP generator geometry tests: no random samples or search scores."""
import importlib.util
import math
from pathlib import Path
import unittest

import numpy as np

_SPEC = importlib.util.spec_from_file_location('bp_synthetic_test', Path(__file__).resolve().parents[1] / 'synthetic.py')
s = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(s)


class SyntheticGeometryTests(unittest.TestCase):
    def test_recipe_inventory(self):
        cases = s.cases()
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({c['id'] for c in cases}), 24)
        self.assertEqual(sum(c['kind'] == 'null' for c in cases), 8)
        positives = [c for c in cases if c['kind'] == 'positive']
        self.assertEqual(len(positives), 12)
        self.assertEqual(sum(c['amplitude'] == 256 for c in positives), 6)
        self.assertTrue(all(c['active_scans'] == [0, 2, 4] for c in positives))

    def test_stationary_integer_center(self):
        channels, weights = s.integrated_channel_weights(100.0, 1, 0)
        np.testing.assert_array_equal(channels, [100])
        np.testing.assert_array_equal(weights, [1.0])

    def test_stationary_half_channel(self):
        channels, weights = s.integrated_channel_weights(100.5, 1, 0)
        np.testing.assert_array_equal(channels, [100, 101])
        np.testing.assert_array_equal(weights, [0.5, 0.5])

    def test_static_wide_profile(self):
        channels, weights = s.integrated_channel_weights(100.0, 9, 0)
        np.testing.assert_array_equal(channels, np.arange(96, 105))
        np.testing.assert_array_equal(weights, np.full(9, 1.0 / 9.0))

    def test_drift_mass_and_sign_symmetry(self):
        for center in (100.0, 100.5, s.REFERENCE_CHANNEL, s.REFERENCE_CHANNEL + 0.123456789):
            for width in (1, 9):
                for rate_index in (0, 419, 629, 838):
                    drift = float(s.RATES[rate_index]) / s.DF * s.DT
                    c1, w1 = s.integrated_channel_weights(center, width, drift)
                    c2, w2 = s.integrated_channel_weights(center, width, -drift)
                    np.testing.assert_array_equal(c1, c2)
                    np.testing.assert_array_equal(w1, w2)
                    self.assertLessEqual(abs(math.fsum(w1.tolist()) - 1), 256 * np.finfo(float).eps)
                    self.assertTrue(np.all(w1 > 0))

    def test_moving_profile_independent_midpoint_quadrature(self):
        # A dense deterministic time quadrature is independent of breakpoint
        # integration. Its finite-grid error is explicitly looser than roundoff.
        center, width, drift = 123.456, 9.0, -26.133
        channels, weights = s.integrated_channel_weights(center, width, drift)
        sample_centers = center + (np.arange(20000) + 0.5 - 10000) / 20000 * drift
        reference = []
        for channel in channels:
            overlap = np.maximum(0.0, np.minimum(sample_centers + width / 2, channel + 0.5)
                                 - np.maximum(sample_centers - width / 2, channel - 0.5))
            reference.append(float(np.mean(overlap) / width))
        np.testing.assert_allclose(weights, reference, rtol=0, atol=2e-8)

    def test_truth_propagates_known_scan_gap(self):
        case = next(c for c in s.cases() if c['kind'] == 'positive' and c['rate_index'] == 838)
        g0, g4 = s.truth_geometry(case, 0), s.truth_geometry(case, 4)
        expected = float(s.RATES[838]) / s.DF * ((s.HEADER_MJD[4] - s.HEADER_MJD[0]) * 86400)
        self.assertAlmostEqual(g4['reference_center'] - g0['reference_center'], expected, places=9)
        self.assertEqual(g0['reference_center'], s.REFERENCE_CHANNEL)
        self.assertTrue(g4['injection_present'])
        self.assertFalse(s.truth_geometry(case, 1)['injection_present'])

    def test_sparse_one_rounding_and_bound(self):
        base = np.array([[128.0, 128.0, 32768.0, 1.0]], dtype='<f4')
        old = base.copy()
        rows = np.array([0, 0, 0], dtype=np.int64)
        channels = np.array([0, 2, 3], dtype=np.int64)
        delta = np.array([0.000003, 0.001, 256.23456789], dtype=np.float64)
        rounded, receipt = s._add_sparse(base, rows, channels, delta)
        expected = (old[rows, channels].astype(np.float64) + delta).astype(np.float32)
        np.testing.assert_array_equal(rounded, expected)
        self.assertTrue(receipt['quantization_bound_pass'])
        self.assertLessEqual(receipt['sum_absolute_rounding_error'], receipt['sum_rounding_error_bound'])
        self.assertEqual(base[0, 1], old[0, 1])

    def test_duplicate_sparse_pixel_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Repeated'):
            s._add_sparse(np.ones((1, 2), dtype='<f4'), np.array([0, 0]), np.array([1, 1]), np.array([1.0, 1.0]))

    def test_invalid_geometry_rejected(self):
        for geometry in ((1, 0, 0), (1, -1, 0), (float('nan'), 1, 0), (1, 1, float('inf'))):
            with self.assertRaises(ValueError):
                s.integrated_channel_weights(*geometry)


if __name__ == '__main__':
    unittest.main()
