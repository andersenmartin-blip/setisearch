"""Tests for the sealed M40 v1 abort and coverage-repaired v2 freeze."""

from __future__ import annotations

from copy import deepcopy
import gzip
import importlib.util
import json
import math
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ABORT_SCRIPT = ROOT / "scripts/m40_m37_native_coverage_abort.py"
V2_SCRIPT = ROOT / "scripts/m40_m37_truth_local_calibration_v2.py"
V2_CONFIG = ROOT / "config/m40_m37_truth_local_calibration_v2.json"
RESULT_ROOT = ROOT / "results_m40_m37_truth_local_calibration"
V2_RESULT_ROOT = ROOT / "results_m40_m37_truth_local_calibration_v2"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ABORT = _load("m40_abort_test", ABORT_SCRIPT)
V2 = _load("m40_v2_test", V2_SCRIPT)


class M40CoverageRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(V2_CONFIG.read_text(encoding="utf-8"))
        cls.abort = ABORT.m40._read_canonical(
            RESULT_ROOT / ABORT.ABORT_NAME
        )
        cls.audit = ABORT.m40._read_canonical(
            RESULT_ROOT / ABORT.AUDIT_NAME
        )

    def test_v1_abort_is_canonical_hash_bound_and_has_no_curve(self):
        identity = dict(self.abort)
        observed = identity.pop("abort_sha256")
        self.assertEqual(observed, ABORT.m40.sha256_json(identity))
        self.assertEqual(
            self.abort["status"], "M40_V1_ABORTED_NO_CALIBRATION_CURVE"
        )
        self.assertEqual(self.abort["completed_trial_count_before_stop"], 156)
        self.assertFalse(self.abort["calibration_aggregate_permitted"])
        self.assertFalse(self.abort["calibration_curve_produced"])
        self.assertTrue(self.abort["partial_records_are_diagnostic_only"])

    def test_native_audit_checks_all_truths_and_freezes_16_failures(self):
        identity = dict(self.audit)
        observed = identity.pop("audit_sha256")
        self.assertEqual(observed, ABORT.m40.sha256_json(identity))
        self.assertEqual(self.audit["truth_count"], 512)
        self.assertEqual(self.audit["covered_truth_count"], 496)
        self.assertEqual(
            tuple(self.audit["uncovered_truth_ordinals"]),
            ABORT.EXPECTED_INVALID_TRUTH_ORDINALS,
        )
        self.assertEqual(self.audit["spectral_payloads_opened"], 0)
        self.assertEqual(self.audit["injections_executed_by_audit"], 0)

    def test_v2_static_config_binds_abort_threshold_and_claim_boundary(self):
        V2._validate_static_config(self.config)
        self.assertFalse(self.config["v1_abort"]["v1_scores_adopted"])
        self.assertEqual(
            self.config["frozen_threshold"]["operational_threshold_snr"],
            126.20158386230469,
        )
        self.assertFalse(
            self.config["claim_boundary"]["interpolation_permitted"]
        )
        self.assertFalse(
            self.config["claim_boundary"]["technosignature_claimed"]
        )

    def test_published_v2_start_freezes_zero_v2_trials_and_no_adoption(self):
        start = V2.m40._read_canonical(V2_RESULT_ROOT / V2.START_NAME)
        identity = dict(start)
        observed = identity.pop("start_sha256")
        self.assertEqual(observed, V2.m40.sha256_json(identity))
        self.assertEqual(
            start["status"], "initialized-no-m40-v2-injection-executed"
        )
        self.assertEqual(start["m40_v2_injection_trials_executed"], 0)
        self.assertEqual(start["v1_score_receipts_adopted"], 0)
        self.assertEqual(
            start["start_sha256"],
            "a0c81a88563fa55c15d123cc3de087abe71a23a78252f2f042e652f24c7dee92",
        )

    def test_published_v2_aggregate_and_ledger_are_complete(self):
        aggregate = V2.m40._read_canonical(
            V2_RESULT_ROOT / V2.AGGREGATE_NAME
        )
        identity = dict(aggregate)
        observed = identity.pop("aggregate_sha256")
        self.assertEqual(observed, V2.m40.sha256_json(identity))
        self.assertEqual(
            observed,
            "03e162aea769c2020df6509171217dbf32624e69b4a3ccad4ae159c85836f974",
        )
        self.assertEqual(aggregate["status"], "complete")
        self.assertEqual(aggregate["trial_count"], 6144)
        self.assertEqual(aggregate["snr_level_count"], 12)
        self.assertEqual(aggregate["truth_count_per_level"], 512)
        self.assertEqual(aggregate["recovered_trial_count"], 0)
        self.assertEqual(aggregate["v1_score_receipts_adopted"], 0)
        self.assertTrue(aggregate["pointwise_only_no_interpolation"])
        self.assertEqual(len(aggregate["levels"]), 12)
        self.assertTrue(
            all(level["recovered"] == 0 for level in aggregate["levels"])
        )
        self.assertEqual(
            aggregate["levels"][-1]["maximum_best_truth_local_score_snr"],
            70.08597564697266,
        )

        ledger_path = V2_RESULT_ROOT / aggregate["ledger_path"]
        self.assertEqual(
            V2.m40.sha256_file(ledger_path), aggregate["ledger_sha256"]
        )
        record_hashes = []
        ordinals = []
        with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                record_identity = dict(record)
                record_sha256 = record_identity.pop("record_sha256")
                self.assertEqual(
                    record_sha256, V2.m40.sha256_json(record_identity)
                )
                record_hashes.append(record_sha256)
                ordinals.append(record["trial_ordinal"])
                self.assertFalse(record["score_recovered"])
        self.assertEqual(ordinals, list(range(6144)))
        self.assertEqual(len(set(record_hashes)), 6144)
        self.assertEqual(
            V2.m40.sha256_json(record_hashes),
            aggregate["trial_record_inventory_sha256"],
        )

    def test_v2_common_interval_and_permutation_are_injective(self):
        frozen = self.config["frozen_repaired_trial_inventory"]
        self.assertEqual(frozen["truth_count_per_snr_level"], 512)
        self.assertEqual(frozen["expected_trial_count"], 6144)
        self.assertEqual(
            frozen["common_safe_proxy_index_start"],
            V2.EXPECTED_COMMON_SAFE_INDEX_START,
        )
        self.assertEqual(
            frozen["common_safe_proxy_index_stop_inclusive"],
            V2.EXPECTED_COMMON_SAFE_INDEX_STOP_INCLUSIVE,
        )
        count = frozen["common_safe_proxy_index_count"]
        self.assertEqual(count, V2.EXPECTED_COMMON_SAFE_INDEX_COUNT)
        self.assertEqual(
            math.gcd(V2.completeness.M37_COMPLETENESS_CARRIER_STEP, count),
            1,
        )
        offset = V2.completeness.M37_COMPLETENESS_MASTER_SEED % count
        indices = {
            V2.EXPECTED_COMMON_SAFE_INDEX_START
            + (
                offset
                + ordinal * V2.completeness.M37_COMPLETENESS_CARRIER_STEP
            )
            % count
            for ordinal in range(512)
        }
        self.assertEqual(len(indices), 512)

    def test_v2_authorization_gate_precedes_run_access(self):
        missing = ROOT / "does-not-exist"
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            V2.execute_trials(missing, missing, authorized=False)

    def test_v2_mutated_abort_or_trial_count_fails(self):
        changed = deepcopy(self.config)
        changed["v1_abort"]["v1_scores_adopted"] = True
        with self.assertRaisesRegex(
            V2.core.V0P6IncompleteError, "abort boundary"
        ):
            V2._validate_static_config(changed)

        changed = deepcopy(self.config)
        changed["frozen_repaired_trial_inventory"]["expected_trial_count"] = 5952
        fake = V2.CoverageRepairedPlan(
            allocation_contract_sha256="0" * 64,
            truth_inventory_sha256="1" * 64,
            trial_inventory_sha256="2" * 64,
            plan_sha256="3" * 64,
            truths=tuple(range(512)),
            trials=tuple(range(6144)),
            carrier_indices=tuple(range(512)),
            source_geometry_sha256="4" * 64,
        )
        with self.assertRaisesRegex(V2.core.V0P6IncompleteError, "plan changed"):
            V2._validate_plan_config(changed, fake)

    @unittest.skipUnless(
        os.environ.get("M40_M39_RUN_ROOT"),
        "requires the rehydrated M39 execution root",
    )
    def test_v2_reconstructs_exact_coverage_proved_plan(self):
        run_root = Path(os.environ["M40_M39_RUN_ROOT"])
        runtime = V2.m40._runtime_context(run_root, self.config)
        plan = V2.make_v2_plan(run_root, runtime)
        V2._validate_plan_config(self.config, plan)
        self.assertEqual(plan.as_record(), self.config["frozen_repaired_trial_inventory"])
        self.assertEqual(len(plan.truths), 512)
        self.assertEqual(len(plan.trials), 6144)


if __name__ == "__main__":
    unittest.main()
