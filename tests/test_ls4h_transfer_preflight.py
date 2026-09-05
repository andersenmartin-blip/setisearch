"""Analytic oracles and failure boundaries for the LS4H adapter preflight."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np

from ls4h_transfer_preflight import check_partitions, geometry, integrated_boxes, match_catalog, quantize, time_adapter_check

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/ls4h_transfer_preflight.json").read_text())
MEDIUM = json.loads((ROOT / "config/ls4b_lhs1140_x_light_sail.json").read_text())["expected_filterbank_header"]
HTR = json.loads((ROOT / "config/ls4c_lhs1140_x_htr_followup.json").read_text())["expected_filterbank_header"]


class LS4HTests(unittest.TestCase):
    def test_fractional_edge_integration_has_exact_analytic_area(self):
        values = integrated_boxes(3, 1., [(.25, 1.25, 4.)])
        np.testing.assert_array_equal(values, [3., 1., 0.])
        self.assertEqual(values.sum(), 4.)

    def test_short_pulse_is_diluted_not_promoted_to_whole_bin(self):
        values = integrated_boxes(2, 1., [(.4, .412, 10.)])
        np.testing.assert_allclose(values, [.12, 0.], atol=1e-14)

    def test_out_of_support_pulse_cannot_be_silently_clipped(self):
        for boxes in [[(-.1, .1, 1.)], [(1.9, 2.1, 1.)], [(1., 1., 1.)]]:
            with self.assertRaises(ValueError):
                integrated_boxes(2, 1., boxes)

    def test_native_counts_expose_tail_without_padding(self):
        grid = geometry(MEDIUM, HTR)
        self.assertEqual(grid["time_group_factor"], 3072)
        self.assertEqual(grid["frequency_group_factor"], 128)
        self.assertEqual(grid["common_medium_samples"], 272)
        self.assertEqual(grid["common_htr_samples"], 835584)
        self.assertEqual(grid["unused_htr_samples"], 2048)
        self.assertEqual(grid["maximum_frequency_center_error_mhz"], 0.)

    def test_shifted_frequency_centers_and_noninteger_time_ratio_rejected(self):
        shifted = {**HTR, "fch1_mhz": HTR["fch1_mhz"] + .01}
        with self.assertRaisesRegex(ValueError, "frequency centers"):
            geometry(MEDIUM, shifted)
        with self.assertRaisesRegex(ValueError, "noninteger"):
            geometry(MEDIUM, {**HTR, "tsamp_s": .00035})

    def test_native_analytic_rebinning_conserves_known_signal_area(self):
        result = time_adapter_check(MEDIUM, HTR, CONFIG["analytic_adapter_example"], geometry(MEDIUM, HTR))
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["expected_area"], 32.72, places=10)
        self.assertFalse(result["physical_instrument_response_verified"])

    def test_identical_bytes_do_not_determine_increment_response(self):
        self.assertEqual(quantize(100.1, 0., 255.), 100)
        self.assertEqual(quantize(100.9, 0., 255.), 100)
        self.assertEqual(quantize(100.3, 0., 255.), 100)
        self.assertEqual(quantize(101.1, 0., 255.), 101)
        self.assertEqual(quantize(-3., 0., 255.), 0)
        self.assertEqual(quantize(300., 0., 255.), 255)

    def test_development_cannot_share_reserved_off_control(self):
        config = deepcopy(CONFIG)
        next(s for s in config["scans"] if s["label"] == "A1")["adjacent_off_labels"] = ["C1"]
        with self.assertRaisesRegex(ValueError, "OFF control"):
            check_partitions(config)
        self.assertTrue(check_partitions(CONFIG)["scan_groups_disjoint"])

    def test_catalog_source_size_and_duplicate_identity_fail_closed(self):
        rows = []
        for scan in CONFIG["scans"]:
            for product in ("medium_resolution", "high_time_resolution"):
                rows.append({"url": scan[product]["url"], "size": scan[product]["expected_size_bytes"],
                             "target": scan["expected_source_name"], "mjd": scan["expected_tstart_mjd"], "id": len(rows)})
        self.assertEqual(match_catalog({"data": rows}, CONFIG)["matched_product_count"], 12)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            match_catalog({"data": rows + [rows[0]]}, CONFIG)
        rows[0] = {**rows[0], "size": rows[0]["size"] + 1}
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            match_catalog({"data": rows}, CONFIG)


if __name__ == '__main__':
    unittest.main()
