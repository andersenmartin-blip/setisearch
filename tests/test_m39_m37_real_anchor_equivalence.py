"""Contract tests for the M39 real-data anchor runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m39_m37_real_anchor_equivalence.py"
SPEC = importlib.util.spec_from_file_location("m39_anchor", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
m39 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m39)


class M39AnchorRunnerTests(unittest.TestCase):
    def test_authorization_gate_precedes_run_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "absent"
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                m39.execute(root, authorized=False)
            self.assertFalse(root.exists())

    def test_required_comparison_includes_bits_mask_and_full_inventory(self):
        hypothesis = {
            "template_index": 2,
            "spectral_width_index": 7,
            "activity_subset_index": 3,
            "proxy_carrier_index": 41,
        }
        adapter = {
            "best_truth_local_score_snr": float(np.float32(12.5)),
            "best_hypothesis": hypothesis,
            "mask_inventory_sha256": "a" * 64,
            "score_inventory_sha256": "b" * 64,
            "candidate_score_cell_count": 9,
        }
        reference = {
            "best_truth_local_score_float32_bits": int(
                np.float32(12.5).view(np.uint32)
            ),
            "best_hypothesis": hypothesis,
            "mask_inventory_sha256": "a" * 64,
            "score_inventory_sha256": "b" * 64,
            "candidate_score_cell_count": 9,
        }
        comparison = m39._comparison(adapter, reference)
        self.assertTrue(comparison["passed"])
        self.assertEqual(len(comparison["checks"]), 8)
        changed = dict(reference)
        changed["score_inventory_sha256"] = "c" * 64
        self.assertFalse(m39._comparison(adapter, changed)["passed"])

    def test_empty_array_inventory_is_hashable(self):
        digest = m39._array_inventory_sha256(
            {(0, 0, 0): np.empty(0, dtype="<f4")}
        )
        self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
