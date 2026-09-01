"""Tests for the offline Milestone 38 completeness feasibility freeze."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m38_m37_completeness_feasibility.py"
CONFIG = ROOT / "config" / "m38_m37_completeness_feasibility.json"
SPEC = importlib.util.spec_from_file_location("m38_feasibility", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class M38CompletenessFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_reproduces_closed_gate_and_claim_boundary(self):
        result = AUDIT.build_feasibility_result(ROOT, self.config)
        self.assertEqual(
            result["status"],
            "feasibility_protocol_frozen_no_calibration_executed",
        )
        self.assertTrue(result["full_replay_gate"]["gate_closed"])
        self.assertEqual(result["full_replay_gate"]["trial_count"], 6144)
        self.assertEqual(
            result["full_replay_gate"]["score_cells_total"],
            13_670_713_589_760,
        )
        self.assertEqual(
            result["selected_path"]["selected_analysis"],
            "retrospective-truth-local-score-recovery-calibration",
        )
        self.assertFalse(
            result["selected_path"]["end_to_end_detector_completeness_claimed"]
        )
        self.assertEqual(result["claim_boundary"]["injection_trials_executed"], 0)
        self.assertFalse(result["claim_boundary"]["sensitivity_claimed"])
        self.assertFalse(result["claim_boundary"]["occurrence_rate_claimed"])
        self.assertTrue(
            result["certificate"]["synthetic_receipts_not_promoted_to_production"]
        )

    def test_rejects_trial_reduction_or_full_replay_promotion(self):
        changed = deepcopy(self.config)
        changed["frozen_full_replay_gate"]["trial_count"] = 512
        with self.assertRaisesRegex(ValueError, "trial count changed"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["existing_sparse_reference_receipts"][
            "production_equivalence_proven"
        ] = True
        with self.assertRaisesRegex(ValueError, "promoted to production"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["mandatory_execution_gates"][0] = "skip-source-rehydration"
        with self.assertRaisesRegex(ValueError, "execution gates changed"):
            AUDIT.validate_config(changed)

    def test_rejects_quantitative_or_end_to_end_claims(self):
        changed = deepcopy(self.config)
        changed["scope"]["quantitative_sensitivity_claim_permitted"] = True
        with self.assertRaisesRegex(ValueError, "must remain false"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["decision"]["end_to_end_detector_completeness_claimed"] = True
        with self.assertRaisesRegex(ValueError, "must remain false"):
            AUDIT.validate_config(changed)

    def test_rejects_input_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed = deepcopy(self.config)
            for item in changed["inputs"]:
                path = root / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / item["path"]).read_bytes())
            target = root / changed["inputs"][0]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "input hash changed"):
                AUDIT.validate_inputs(root, changed)

    def test_output_manifests_reproduce(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = AUDIT.write_outputs(ROOT, output, CONFIG)
            self.assertEqual(
                json.loads((output / "feasibility.json").read_text(encoding="utf-8")),
                result,
            )
            for manifest_name in ("INPUT_MANIFEST.sha256", "RESULTS_MANIFEST.sha256"):
                lines = (output / manifest_name).read_text(encoding="utf-8").splitlines()
                self.assertTrue(lines)
                for line in lines:
                    digest, relative = line.split("  ", 1)
                    base = ROOT if manifest_name.startswith("INPUT") else output
                    self.assertEqual(AUDIT.sha256_file(base / relative), digest)


if __name__ == "__main__":
    unittest.main()
