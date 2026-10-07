import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "voyager_posthoc", ROOT / "scripts/radio_reference_voyager_posthoc_review_20261007.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
RESULT_ROOT = ROOT / "results_radio_reference_voyager_20261007"
CONFIG = ROOT / "config/radio_reference_voyager_20261007.json"


class VoyagerPosthocReviewTests(unittest.TestCase):
    def test_retained_manifest_verifies(self):
        self.assertEqual(MODULE.verify_manifest(RESULT_ROOT), 8)

    def test_retained_dat_has_three_rows(self):
        rows = MODULE.parse_dat(RESULT_ROOT / "Voyager1.single_coarse.fine_res.dat")
        self.assertEqual([row["top_hit"] for row in rows], [1, 2, 3])

    def test_upstream_scalar_rule_has_relative_component(self):
        self.assertTrue(MODULE.np_isclose_scalar(245.709610, 245.707984))
        self.assertFalse(abs(245.709610 - 245.707984) <= 0.001)

    def test_audit_preserves_original_failure(self):
        result = MODULE.audit(RESULT_ROOT, CONFIG)
        self.assertEqual(result["status"], "REVIEW_COMPLETE_ORIGINAL_RUN_REMAINS_FAILED_CLOSED")
        self.assertEqual(result["original_absolute_snr_gate_failures"], 1)
        self.assertEqual(result["upstream_np_isclose_frequency_failures"], 0)
        self.assertEqual(result["upstream_np_isclose_snr_failures"], 0)
        self.assertFalse(result["analysis_replayed"])
        self.assertFalse(result["authority_change"])

    def test_manifest_corruption_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "item").write_text("changed")
            (root / "SHA256SUMS").write_text("0" * 64 + "  item\n")
            with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                MODULE.verify_manifest(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
