"""LS4E geometry, detrending, event matching and failure-mode oracles."""
import json
from pathlib import Path
import unittest
import numpy as np

from seti_repeater.light_sail_residual import channel_indices, detrend_region, matched_pulses, residual_metrics, pulse_clusters, compare_residuals

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "config/ls4e_residual_qualification.json").read_text())["settings"]


class LS4EResidualTests(unittest.TestCase):
    def test_known_lhs1140_band_excludes_both_extra_centers(self):
        indices = channel_indices(12076.28173828125, -0.3662109375, 11264, 9379.380619049072, 9383.307445526123)
        self.assertEqual(indices.tolist(), list(range(7354, 7365)))

    def test_both_axis_orders_and_exact_edges(self):
        self.assertEqual(channel_indices(10, -1, 11, 3.2, 6.8).tolist(), [4, 5, 6])
        self.assertEqual(channel_indices(0, 1, 11, 4, 6).tolist(), [4, 5, 6])
        self.assertEqual(channel_indices(0, 1, 11, -5, 2).tolist(), [0, 1, 2])

    def test_invalid_frequency_intervals_fail_closed(self):
        for args in [(10, 0, 11, 4, 6), (10, -1, 11, 6, 4), (10, -1, 11, 20, 25), (10, -1, 11, 4, 4), (float('nan'), 1, 11, 4, 6)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                channel_indices(*args)

    def test_affine_baseline_removed_including_partial_final_tile(self):
        values = 17 + np.arange(10003) * 0.003
        np.testing.assert_allclose(detrend_region(values, 2000), 0, atol=2e-14)

    def test_close_blocks_are_one_event(self):
        events = pulse_clusters(np.array([9., 12., 10., 11.]), np.array([1., 1.1, 1.2, 4.]), 8, .6)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["peak_time_s"], 1.1)

    def test_cross_scale_match_cannot_count_same_event_twice(self):
        left = [{"peak_time_s": x} for x in [1., 1.02, 4.]]
        right = [{"peak_time_s": x} for x in [1.01, 4.01]]
        self.assertEqual(matched_pulses(left, right, .03), 2)

    def test_bad_series_and_degenerate_noise_fail_closed(self):
        for values in [np.ones(120000), np.full(120000, np.nan), np.ones((20, 20))]:
            with self.assertRaises(ValueError):
                residual_metrics(values, .001, 30, 70, SETTINGS)

    def test_mismatched_banks_fail_closed(self):
        rng = np.random.default_rng(8801)
        metrics = residual_metrics(rng.normal(size=120000), .001, 30, 70, SETTINGS)
        bad = {**metrics, "scales": metrics["scales"][:-1]}
        with self.assertRaises(ValueError):
            compare_residuals(metrics, bad, SETTINGS)


if __name__ == "__main__":
    unittest.main()
