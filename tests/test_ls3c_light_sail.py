"""Tests for the prospectively frozen HD 63433 LS3C screen."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/ls3c_hd63433_light_sail.json"
LS1_CONFIG = ROOT / "config/ls1_hd219134_light_sail.json"
SYNTHETIC_SCRIPT = ROOT / "scripts/ls3c_synthetic_validation.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("ls3c_synthetic", SYNTHETIC_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SYNTHETIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNTHETIC)


class LS3CLightSailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.ls1 = json.loads(LS1_CONFIG.read_text(encoding="utf-8"))

    def test_freeze_is_prospective_for_spectral_values(self):
        boundary = self.config["freeze_boundary"]
        self.assertTrue(boundary["hdf5_metadata_read_before_freeze"])
        self.assertFalse(boundary["medium_resolution_values_read_before_freeze"])
        self.assertFalse(boundary["high_time_resolution_values_read_before_freeze"])
        self.assertFalse(self.config["claim_boundary"]["technosignature_claimed"])

    def test_detector_parameters_are_exactly_inherited_from_ls1(self):
        detector = {key: value for key, value in self.config["medium_resolution_screen"].items() if key != "implementation"}
        self.assertEqual(detector, self.ls1["medium_resolution_screen"])

    def test_sequence_is_complete_abacad_with_full_htr(self):
        sequence = self.config["selected_sequence"]
        self.assertEqual([item["label"] for item in sequence], ["A1", "B1", "A2", "C1", "A3", "D1"])
        self.assertEqual([item["role"] for item in sequence], ["ON", "OFF", "ON", "OFF", "ON", "OFF"])
        self.assertTrue(all(item["medium_resolution"]["expected_size_bytes"] > 0 for item in sequence))
        self.assertTrue(all(item["high_time_resolution"]["expected_size_bytes"] > 0 for item in sequence))

    def test_geometry_improves_on_ls1_and_ls2(self):
        geometry = self.config["geometry"]
        self.assertLess(geometry["nominal_projected_separation_stellar_radii"], geometry["ls1_selected_separation_stellar_radii"])
        self.assertLess(geometry["nominal_projected_separation_stellar_radii"], geometry["ls2_selected_separation_stellar_radii"])
        self.assertIn("ranking metric", geometry["interpretation_limit"])

    def test_inherited_synthetic_injection_is_recovered(self):
        result = SYNTHETIC.run_validation()
        self.assertTrue(result["recovered"])
        self.assertEqual(result["artifact_type"], "seti_repeater.ls3c_synthetic_validation")
        self.assertEqual(result["inherited_detector"], "LS1 unchanged")


if __name__ == "__main__":
    unittest.main()
