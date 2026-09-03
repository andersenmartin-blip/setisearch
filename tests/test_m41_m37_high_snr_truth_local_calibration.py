"""Tests for the post-M40 higher-S/N truth-local calibration freeze."""

from __future__ import annotations

from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m41_m37_high_snr_truth_local_calibration.py"
CONFIG = ROOT / "config/m41_m37_high_snr_truth_local_calibration.json"
M40_LEDGER = (
    ROOT / "results_m40_m37_truth_local_calibration_v2/trial-ledger.jsonl.gz"
)
PUBLISHED = ROOT / "results_m41_m37_high_snr_truth_local_calibration"
SPEC = importlib.util.spec_from_file_location("m41_calibration_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M41 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M41)


class M41HighSnrTruthLocalCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.plan = M41.make_plan()

    def _adapter(self, score):
        result = {
            "artifact_type": "m39-truth-local-score-result-v1",
            "status": M41.m40.TRUTH_LOCAL_ADAPTER_STATUS,
            "window_id": M41.m40.EXPECTED_WINDOW_ID,
            "template_count": M41.core.M37_TEMPLATE_COUNT,
            "cache_count": 24,
            "candidate_score_cell_count": 1 if score is not None else 0,
            "best_truth_local_score_snr": score,
            "two_pass_mask_recomputed": True,
            "global_false_positive_field_replayed": False,
            "physical_veto_survival_calibrated": False,
            "production_equivalence_proven": False,
        }
        result["result_sha256"] = M41.sha256_json(result)
        return result

    def _record(self, score):
        start = {"start_sha256": "1" * 64}
        return M41.make_trial_record(
            self.plan.trials[0],
            0,
            start,
            self.config,
            self._adapter(score),
            source_product_sha256s=("2" * 64, "3" * 64, "4" * 64),
            background_sha256="5" * 64,
            noise_shift_channels=(10, 20, 30),
            injected_native_sha256="6" * 64,
        )

    def test_config_and_plan_freeze_exact_extension(self):
        M41.validate_config(self.config, self.plan)
        self.assertEqual(
            list(M41.M41_SNR_GRID),
            [48.0, 56.0, 64.0, 72.0, 80.0, 88.0,
             96.0, 112.0, 128.0, 160.0, 192.0, 256.0],
        )
        self.assertEqual(len(self.plan.truths), 512)
        self.assertEqual(len(self.plan.trials), 6144)
        self.assertEqual(
            self.plan.extension_contract_sha256,
            "aa276fe74fad022992882df544cdfb34a675368b666d0a08f1e24cdb175fc944",
        )
        self.assertEqual(
            self.plan.trial_inventory_sha256,
            "b32f881c1887565292034804f6d58d1e4204ed9b935cd1a5979022d3a0592302",
        )
        self.assertEqual(
            self.plan.plan_sha256,
            "ff82d8ff704f28eecafc23f0a7725f9c093838ae62ceeda94adc0ef8155fd98a",
        )

    def test_every_m40_v2_truth_is_reused_at_every_level(self):
        expected = [truth.as_record() for truth in self.plan.truths]
        for level_index in range(len(M41.M41_SNR_GRID)):
            begin = level_index * 512
            observed = [
                trial.truth.as_record()
                for trial in self.plan.trials[begin : begin + 512]
            ]
            self.assertEqual(observed, expected)

    def test_m41_trial_and_noise_identities_are_new_and_unique(self):
        m40_ids = set()
        with gzip.open(M40_LEDGER, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    m40_ids.add(json.loads(line)["trial"]["trial_id"])
        m41_ids = {trial.trial_id for trial in self.plan.trials}
        noise_seeds = {trial.noise_seed for trial in self.plan.trials}
        self.assertEqual(len(m40_ids), 6144)
        self.assertEqual(len(m41_ids), 6144)
        self.assertEqual(len(noise_seeds), 6144)
        self.assertTrue(m40_ids.isdisjoint(m41_ids))

    def test_authorization_gate_precedes_runtime_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                M41.execute_trials(missing, missing, authorized=False)

    def test_published_start_freezes_zero_m41_trials(self):
        start = M41._validate_start(PUBLISHED, self.config, self.plan)
        self.assertEqual(
            start["status"], "initialized-no-m41-injection-executed"
        )
        self.assertEqual(start["m41_injection_trials_executed"], 0)
        self.assertEqual(start["m40_score_receipts_adopted"], 0)
        self.assertEqual(
            start["start_sha256"],
            "f2b9198cf25df9503e2f53ed99ab3098ddbb8e7af0689206d143cfd97276facd",
        )

    def test_inclusive_threshold_and_record_identity(self):
        threshold = self.config["frozen_threshold"][
            "operational_threshold_snr"
        ]
        recovered = self._record(threshold)
        missed = self._record(threshold - 1e-9)
        absent = self._record(None)
        self.assertTrue(recovered["score_recovered"])
        self.assertFalse(missed["score_recovered"])
        self.assertFalse(absent["score_recovered"])
        identity = dict(recovered)
        observed = identity.pop("record_sha256")
        self.assertEqual(observed, M41.sha256_json(identity))

    def test_mutated_parent_or_grid_fails_closed(self):
        changed = deepcopy(self.config)
        changed["parent_m40_v2"]["recovered_trial_count"] = 1
        with self.assertRaisesRegex(
            M41.core.V0P6IncompleteError, "parent M40 v2 boundary"
        ):
            M41.validate_config(changed, self.plan)

        changed = deepcopy(self.config)
        changed["frozen_trial_inventory"]["snr_grid"][-1] = 320.0
        with self.assertRaisesRegex(
            M41.core.V0P6IncompleteError, "trial inventory"
        ):
            M41.validate_config(changed, self.plan)

    def test_deterministic_gzip_ledger(self):
        records = [self._record(None), self._record(126.20158386230469)]
        first = M41._gzip_jsonl(records)
        second = M41._gzip_jsonl(records)
        self.assertEqual(first, second)
        self.assertEqual(first[:2], b"\x1f\x8b")


if __name__ == "__main__":
    unittest.main()
