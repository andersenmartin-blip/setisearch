"""Tests for the fail-closed M40 conditional calibration runner."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m40_m37_truth_local_calibration.py"
CONFIG = ROOT / "config/m40_m37_truth_local_calibration.json"
PUBLISHED = ROOT / "results_m40_m37_truth_local_calibration"
SPEC = importlib.util.spec_from_file_location("m40_calibration", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M40 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M40)


class M40TruthLocalCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.trials = M40._all_trials()

    def _adapter(self, score):
        result = {
            "artifact_type": "m39-truth-local-score-result-v1",
            "status": M40.TRUTH_LOCAL_ADAPTER_STATUS,
            "window_id": M40.EXPECTED_WINDOW_ID,
            "template_count": M40.core.M37_TEMPLATE_COUNT,
            "cache_count": 24,
            "best_truth_local_score_snr": score,
            "two_pass_mask_recomputed": True,
            "global_false_positive_field_replayed": False,
            "physical_veto_survival_calibrated": False,
            "production_equivalence_proven": False,
        }
        result["result_sha256"] = M40.sha256_json(result)
        return result

    def _record(self, score):
        start = {"start_sha256": "1" * 64}
        return M40.make_trial_record(
            self.trials[0],
            0,
            start,
            self.config,
            self._adapter(score),
            source_product_sha256s=("2" * 64, "3" * 64, "4" * 64),
            background_sha256="5" * 64,
            noise_shift_channels=(10, 20, 30),
            injected_native_sha256="6" * 64,
        )

    def test_config_freezes_exact_inventory_threshold_and_claims(self):
        M40.validate_config(self.config)
        self.assertEqual(len(self.trials), 6144)
        self.assertEqual(
            self.config["frozen_threshold"]["operational_threshold_snr"],
            126.20158386230469,
        )
        self.assertFalse(
            self.config["claim_boundary"]["interpolation_permitted"]
        )
        self.assertFalse(
            self.config["claim_boundary"]["occurrence_rate_claimed"]
        )

    def test_authorization_gate_precedes_run_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                M40.execute_trials(
                    missing, missing, authorized=False
                )

    def test_modulo_shards_partition_every_trial_once(self):
        selected = [
            [ordinal for ordinal in range(6144) if ordinal % 6 == shard]
            for shard in range(6)
        ]
        self.assertTrue(all(len(items) == 1024 for items in selected))
        flattened = [item for items in selected for item in items]
        self.assertEqual(sorted(flattened), list(range(6144)))

    def test_inclusive_threshold_and_no_score_boundary(self):
        threshold = self.config["frozen_threshold"][
            "operational_threshold_snr"
        ]
        self.assertTrue(self._record(threshold)["score_recovered"])
        self.assertFalse(self._record(None)["score_recovered"])
        self.assertFalse(self._record(threshold - 1e-9)["score_recovered"])

    def test_trial_record_hash_and_claim_mutations_fail(self):
        record = self._record(None)
        start = {"start_sha256": "1" * 64}
        changed = deepcopy(record)
        changed["claim_boundary"]["technosignature_claimed"] = True
        changed["record_sha256"] = M40.sha256_json(
            {key: value for key, value in changed.items() if key != "record_sha256"}
        )
        with self.assertRaisesRegex(M40.core.V0P6IncompleteError, "content changed"):
            M40._validate_trial_record(
                changed, self.trials[0], 0, start, self.config
            )

        changed = deepcopy(record)
        changed["adapter"]["best_truth_local_score_snr"] = 999.0
        changed["record_sha256"] = M40.sha256_json(
            {key: value for key, value in changed.items() if key != "record_sha256"}
        )
        with self.assertRaisesRegex(M40.core.V0P6IncompleteError, "adapter result identity"):
            M40._validate_trial_record(
                changed, self.trials[0], 0, start, self.config
            )

    def test_trial_reduction_and_threshold_change_fail(self):
        changed = deepcopy(self.config)
        changed["frozen_trial_inventory"]["trial_count"] = 512
        with self.assertRaisesRegex(M40.core.V0P6IncompleteError, "trial inventory"):
            M40.validate_config(changed)
        changed = deepcopy(self.config)
        changed["frozen_threshold"]["operational_threshold_snr"] = 40.0
        with self.assertRaisesRegex(M40.core.V0P6IncompleteError, "threshold"):
            M40.validate_config(changed)

    def test_deterministic_gzip_ledger(self):
        records = [self._record(None), self._record(126.20158386230469)]
        first = M40._gzip_jsonl(records)
        second = M40._gzip_jsonl(records)
        self.assertEqual(first, second)
        self.assertEqual(first[:2], b"\x1f\x8b")

    def test_published_start_freezes_zero_executed_trials(self):
        start = M40._validate_start(PUBLISHED, self.config)
        self.assertEqual(
            start["status"], "initialized-no-m40-injection-executed"
        )
        self.assertEqual(start["trial_count"], 6144)
        self.assertEqual(start["m40_injection_trials_executed"], 0)
        self.assertEqual(
            start["start_sha256"],
            "17c578e3bcc09565c76adee509607f2bd82c663c56015e5c5cdde91170e9d1a9",
        )


if __name__ == "__main__":
    unittest.main()
