import unittest
import numpy as np
from ls6a_scan_end import summarize_coarse


class ScanEndDiagnosticTests(unittest.TestCase):
    def test_shared_linear_drift(self):
        data = np.tile(np.arange(56.)[:, None], (1, 64))
        result = summarize_coarse(data, 1.)
        self.assertAlmostEqual(result['unit_common_trace_energy_reduction'], 1.)
        self.assertAlmostEqual(result['linear_fit']['r_squared'], 1.)
        self.assertAlmostEqual(result['linear_fit']['coefficient'], 1.)
        self.assertEqual(result['tail_comparisons'][0]['positive_bin_count'], 64)

    def test_localized_step_is_not_common(self):
        data = np.zeros((56, 64)); data[-7:, 5] = 1.
        result = summarize_coarse(data, 1.)
        self.assertAlmostEqual(result['unit_common_trace_energy_reduction'], 0.)
        self.assertEqual(result['tail_comparisons'][0]['positive_bin_count'], 1)
        self.assertEqual(result['tail_comparisons'][0]['median_mean_difference'], 0.)

    def test_negative_tail_and_invalid_bin(self):
        data = np.zeros((56, 64)); data[-7:] = -2.; data[:, 3] = np.nan
        result = summarize_coarse(data, 1.)
        tail = result['tail_comparisons'][0]
        self.assertEqual(len(result['valid_bin_indices']), 63)
        self.assertEqual(tail['positive_bin_count'], 0)
        self.assertAlmostEqual(tail['step_fit']['coefficient'], -2.)
        self.assertAlmostEqual(tail['step_fit']['r_squared'], 1.)
