"""Independent injection, association and design checks for the LS4G study."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from ls4g_synthetic_recovery import background_pair, build_trial, cell_specs, inject, truth_matches, verify_manifest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/ls4g_synthetic_recovery.json").read_text())


class LS4GTests(unittest.TestCase):
    def test_half_open_injection_has_expected_discrete_support(self):
        x = np.zeros(10)
        truth = inject(x, [.003], .003, 4., .001)
        np.testing.assert_array_equal(x, [0, 4, 4, 4, 0, 0, 0, 0, 0, 0])
        self.assertEqual(truth[0]["samples"], 3)
        self.assertAlmostEqual(truth[0]["center_s"], .0025)

    def test_truth_matching_rejects_unrelated_and_duplicate_peaks(self):
        truth = [{"center_s": 10., "width_s": .01}, {"center_s": 20., "width_s": .01}]
        pulses = [{"peak_time_s": t} for t in [2., 10.001, 10.002, 30.]]
        self.assertEqual(truth_matches(pulses, truth, .01, .001), {0})
        self.assertEqual(truth_matches(pulses, [], .01, .001), set())

    def test_variance_stress_preserves_off_and_reference_and_same_truth(self):
        white, times = background_pair(114700, "white", CONFIG)
        stressed, other_times = background_pair(114700, "on_variance_x4", CONFIG)
        self.assertEqual(times, other_times)
        np.testing.assert_array_equal(white[1], stressed[1])
        np.testing.assert_array_equal(white[0, :30000], stressed[0, :30000])
        np.testing.assert_array_equal(white[0, 70000:], stressed[0, 70000:])
        np.testing.assert_allclose(stressed[0, 30000:70000] - 100, 2 * (white[0, 30000:70000] - 100), atol=2e-14)

    def test_control_pulse_is_added_only_to_selected_scan_region(self):
        base = np.zeros((2, CONFIG["sample_count"]))
        spec = {"kind": "control", "location": "off", "width_s": .012, "amplitude_sigma": 4.}
        pair, truth, control = build_trial(base, CONFIG["pulse_times_s"], spec, CONFIG)
        self.assertEqual(np.count_nonzero(pair[0]), 72)
        self.assertEqual(np.count_nonzero(pair[1]), 12)
        self.assertEqual(len(truth), 6)
        self.assertEqual(control[0]["samples"], 12)
        self.assertFalse(base.any())

    def test_grid_has_unique_cells_and_nonduplicated_nulls(self):
        specs = list(cell_specs(CONFIG))
        self.assertEqual(len(specs), 141)
        self.assertEqual(len({json.dumps(x, sort_keys=True) for x in specs}), 141)
        self.assertEqual(sum(x["kind"] == "null" for x in specs), 3)
        self.assertEqual(len(specs) * len(CONFIG["seeds"]), 1692)

    def test_freeze_rejects_modified_dependency(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "input").write_text("changed")
            (root / "freeze").write_text("0" * 64 + "  input\n")
            with self.assertRaisesRegex(ValueError, "freeze mismatch"):
                verify_manifest(root / "freeze", root)


if __name__ == "__main__":
    unittest.main()
