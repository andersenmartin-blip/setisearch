"""Tests for the ledger-only M42 support and mask diagnostic."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m42_m41_support_mask_diagnostic.py"
CONFIG = ROOT / "config/m42_m41_support_mask_diagnostic.json"
SPEC = importlib.util.spec_from_file_location("m42_support_diagnostic", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M42 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M42)


class M42SupportMaskDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_config_freezes_ledger_only_claim_boundary(self):
        M42.validate_config(self.config)
        self.assertEqual(self.config["analysis_base_commit"], M42.EXPECTED_BASE_COMMIT)
        self.assertEqual(
            self.config["diagnostic"]["group_fields"], list(M42.GROUP_FIELDS)
        )
        for key in (
            "new_spectral_access",
            "new_injections",
            "threshold_change",
            "unsupported_truth_removal",
            "interpolation_permitted",
            "end_to_end_completeness_claimed",
            "sensitivity_transport_claimed",
            "occurrence_rate_claimed",
            "technosignature_claimed",
        ):
            self.assertFalse(self.config["claim_boundary"][key])

    def test_reassembles_exact_m41_ledger(self):
        transport = M42.load_json(M42.M41_TRANSPORT)
        payload = M42.reconstruct_ledger(ROOT, transport)
        self.assertEqual(len(payload), M42.EXPECTED_LEDGER_NBYTES)
        self.assertEqual(
            M42.hashlib.sha256(payload).hexdigest(), M42.EXPECTED_LEDGER_SHA256
        )

    def test_mutated_transport_or_claim_fails_closed(self):
        changed = deepcopy(self.config)
        changed["claim_boundary"]["unsupported_truth_removal"] = True
        with self.assertRaisesRegex(M42.M41.core.V0P6IncompleteError, "must remain false"):
            M42.validate_config(changed)

        transport = M42.load_json(M42.M41_TRANSPORT)
        transport["parts"][0]["nbytes"] += 1
        with self.assertRaisesRegex(M42.M41.core.V0P6IncompleteError, "part size"):
            M42.reconstruct_ledger(ROOT, transport)

    def test_complete_nested_diagnostic(self):
        result = M42.build_diagnostic(ROOT, self.config)
        self.assertEqual(result["status"], "complete-ledger-only-diagnostic")
        self.assertEqual(result["trial_count"], 6144)
        support = result["truth_support"]
        self.assertEqual(support["candidate_supported_truth_count"], 98)
        self.assertEqual(support["candidate_unsupported_truth_count"], 414)
        self.assertEqual(support["frozen_endpoint_recovery_ceiling_count"], 98)
        self.assertFalse(support["fifty_percent_recovery_structurally_reachable"])
        self.assertEqual(
            [level["recovered"] for level in result["levels"]],
            [0, 0, 0, 2, 7, 11, 27, 37, 40, 43, 46, 46],
        )
        highest = result["highest_snr_cross_section"]
        self.assertEqual(highest["ideal_single_epoch_snr"], 256.0)
        self.assertEqual(highest["candidate_supported"], 98)
        self.assertEqual(highest["finite_post_mask"], 49)
        self.assertEqual(highest["recovered"], 46)
        self.assertFalse(result["decision"]["further_snr_extension_supported"])
        for rows in result["group_diagnostics_at_snr_256"].values():
            self.assertEqual(sum(row["truths"] for row in rows), 512)
            self.assertEqual(sum(row["candidate_supported"] for row in rows), 98)
            self.assertEqual(sum(row["snr_256_finite"] for row in rows), 49)
            self.assertEqual(sum(row["snr_256_recovered"] for row in rows), 46)

    def test_output_manifests_reproduce(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = M42.write_outputs(ROOT, output, CONFIG)
            self.assertEqual(
                json.loads((output / "diagnostic.json").read_text(encoding="utf-8")),
                result,
            )
            for name in ("INPUT_MANIFEST.sha256", "RESULTS_MANIFEST.sha256"):
                lines = (output / name).read_text(encoding="utf-8").splitlines()
                self.assertTrue(lines)
                for line in lines:
                    digest, relative = line.split("  ", 1)
                    base = ROOT if name.startswith("INPUT") else output
                    self.assertEqual(M42.sha256_file(base / relative), digest)


if __name__ == "__main__":
    unittest.main()
