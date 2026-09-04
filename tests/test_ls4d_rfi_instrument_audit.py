"""Independent oracles for the retrospective audit; historical code is frozen."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ls4d_rfi_instrument_audit import center_selected_channels, level_step_counterexample, verified_json


class LS4DAuditTests(unittest.TestCase):
    def test_channel_centers_handle_both_frequency_orders(self):
        descending = {"fch1_mhz": 10.0, "foff_mhz": -1.0, "nchans": 11}
        ascending = {"fch1_mhz": 0.0, "foff_mhz": 1.0, "nchans": 11}
        self.assertEqual(center_selected_channels(descending, 3.2, 6.8).tolist(), [4, 5, 6])
        self.assertEqual(center_selected_channels(ascending, 3.2, 6.8).tolist(), [4, 5, 6])
        self.assertEqual(center_selected_channels(descending, 4.0, 6.0).tolist(), [4, 5, 6])

    def test_changed_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            path.write_text('{}')
            with self.assertRaises(ValueError):
                verified_json(path, '0' * 64)

    def test_constant_plateau_can_pass_historical_morphology_rule(self):
        config = json.loads((ROOT / "config/ls4c_lhs1140_x_htr_followup.json").read_text())
        result = level_step_counterexample(config)
        self.assertFalse(result["injected_subsecond_pulses"])
        self.assertTrue(result["comparison"]["diffraction_structure_supported"])


if __name__ == "__main__":
    unittest.main()
