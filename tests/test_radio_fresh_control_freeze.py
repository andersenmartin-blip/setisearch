"""Prospective validation of the fresh recovery/RFI/null control freeze."""
import copy
import json
from pathlib import Path
from dataclasses import replace
import unittest

from seti_repeater import control_freeze_radio as freeze

ROOT = Path(__file__).resolve().parents[1]


class FreshControlFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config" /
            "radio_fresh_control_freeze_20260926.json").read_text())
        cls.panel = freeze.build(cls.config)

    def test_factorial_signal_and_matched_control_coverage_is_frozen(self):
        self.assertEqual(len(self.config["cases"]), 24)
        for kind in ("on_signal", "matched_on_off"):
            pairs = {(x["injection_width_channels"], x["total_digital_power"])
                     for x in self.config["cases"] if x["kind"] == kind}
            self.assertEqual(pairs, {(w, p) for w in freeze.WIDTHS
                                     for p in freeze.POWERS})

    def test_calibration_and_evaluation_identities_are_disjoint(self):
        items = self.config["calibration_identities"] + self.config["cases"]
        self.assertEqual(len({x["seed"] for x in items}), 27)
        self.assertEqual(len({x["source_identity_namespace"] for x in items}), 27)

    def test_broad_width_leakage_and_complete_accounting_are_zero_gates(self):
        gates = self.config["gates"]
        self.assertEqual(gates["broad_width_leakage"]["detector_width_channels"],
                         [65, 129])
        self.assertEqual(gates["broad_width_leakage"][
            "unassociated_final_members_each_width"], 0)
        self.assertTrue(gates["complete_member_cluster_partition"][
            "every_final_member_in_exactly_one_complete_cluster"])

    def test_tampering_and_duplicate_identity_are_refused(self):
        changed = copy.deepcopy(self.config)
        changed["cases"][1]["seed"] = changed["cases"][0]["seed"]
        with self.assertRaisesRegex(ValueError, "seeds are not disjoint"):
            freeze.build(changed)
        with self.assertRaisesRegex(ValueError, "freeze changed"):
            replace(self.panel, identity="0" * 64).validate()

    def test_freeze_is_unexecuted_and_has_no_access_authority(self):
        self.assertEqual(self.panel.record()["status"], "FROZEN_NOT_EXECUTABLE")
        self.assertFalse(self.panel.record()["spectral_access_authorized"])
        self.assertEqual(self.config["attempt_budgets"]["evaluation_runs"], 1)
        self.assertEqual(self.config["attempt_budgets"]["remedy_attempts_after_freeze"], 0)
        self.assertFalse(self.config["previous_failed_panel_rerun"])


if __name__ == "__main__":
    unittest.main()
