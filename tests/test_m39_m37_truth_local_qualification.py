"""Tests for the fail-closed Milestone 39 qualification."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m39_m37_truth_local_qualification.py"
CONFIG = ROOT / "config" / "m39_m37_truth_local_qualification.json"
PUBLISHED = ROOT / "results_m39_m37_truth_local_qualification" / "qualification.json"
SPEC = importlib.util.spec_from_file_location("m39_qualification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class M39TruthLocalQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_config_freezes_scope_inventory_adapter_and_anchors(self):
        AUDIT.validate_config(self.config)
        self.assertEqual(
            len(self.config["real_m37_anchor_inventory"]),
            3,
        )
        self.assertEqual(
            self.config["frozen_completeness_inventory"]["trial_count"],
            6144,
        )
        self.assertFalse(
            self.config["truth_local_adapter"]["production_equivalence_proven"]
        )

    def test_missing_source_run_stops_before_factor_and_anchor_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = AUDIT.build_qualification_result(
                ROOT,
                Path(temporary),
                self.config,
            )
        self.assertEqual(
            result["status"],
            "qualification_started_factor_bundle_pending",
        )
        self.assertFalse(result["factor_bundle_gate"]["passed"])
        self.assertEqual(result["anchor_plan_records"], [])
        self.assertEqual(result["claim_boundary"]["injection_trials_executed"], 0)
        self.assertFalse(result["gates"]["all_6144_calibration_trials_authorized"])

    def test_rejects_scope_trial_or_adapter_promotion(self):
        changed = deepcopy(self.config)
        changed["scope"]["quantitative_sensitivity_claim_permitted"] = True
        with self.assertRaisesRegex(ValueError, "must remain false"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["frozen_completeness_inventory"]["trial_count"] = 512
        with self.assertRaisesRegex(ValueError, "trial count changed"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["truth_local_adapter"]["production_equivalence_proven"] = True
        with self.assertRaisesRegex(ValueError, "must remain false"):
            AUDIT.validate_config(changed)

    def test_rejects_anchor_mutation_or_global_proof(self):
        changed = deepcopy(self.config)
        changed["real_m37_anchor_inventory"][0]["trial_id"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "anchor trial changed"):
            AUDIT.validate_config(changed)

        changed = deepcopy(self.config)
        changed["anchor_equivalence_contract"][
            "anchor_success_is_global_equivalence_proof"
        ] = True
        with self.assertRaisesRegex(ValueError, "promoted to global proof"):
            AUDIT.validate_config(changed)

    def test_rejects_input_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for item in self.config["inputs"]:
                target = root / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / item["path"]).read_bytes())
            first = root / self.config["inputs"][0]["path"]
            first.write_bytes(first.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "input hash changed"):
                AUDIT.validate_inputs(root, self.config)

    def test_completed_rehydration_and_anchor_receipts_open_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary)
            source = self.config["source_run_artifacts"]
            window = self.config["scope"]["background_window"]
            for label in source["required_scan_labels"]:
                path = run_root / "sources" / window / f"{label}.product.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}")
                for width in source["required_spectral_widths"]:
                    sidecar = (
                        run_root
                        / "caches"
                        / window
                        / label
                        / f"width-{width}.json"
                    )
                    sidecar.parent.mkdir(parents=True, exist_ok=True)
                    sidecar.write_text("{}")
            source_manifest = run_root / source["required_source_manifest_path"]
            cache_manifest = run_root / source["required_cache_manifest_path"]
            source_manifest.write_bytes(b"source")
            cache_manifest.write_bytes(b"cache")
            completion = {
                "status": "complete",
                "run_id": AUDIT.EXPECTED_SOURCE_RUN_ID,
                "window_id": window,
                "source_product_count": 6,
                "cache_entry_count": 48,
                "all_six_sources_verified": True,
                "all_48_caches_verified": True,
                "source_manifest_sha256": AUDIT.sha256_file(source_manifest),
                "cache_manifest_file_sha256": AUDIT.sha256_file(cache_manifest),
                "source_deep_verification_sha256": "a" * 64,
                "cache_deep_verification_sha256": "b" * 64,
            }
            completion["completion_sha256"] = AUDIT.sha256_json(completion)
            (run_root / "m39-rehydration-completion.json").write_bytes(
                AUDIT.core.canonical_json_bytes(completion)
            )
            readiness = AUDIT._source_cache_readiness(run_root, self.config)
            self.assertTrue(readiness["deep_hash_verification_executed"])

            anchor_results = []
            for anchor in self.config["real_m37_anchor_inventory"]:
                result = {
                    "anchor_id": anchor["anchor_id"],
                    "trial_id": anchor["trial_id"],
                    "equivalence_passed": True,
                    "comparison": {"passed": True},
                    "candidate_proxy_cell_count": 1,
                }
                result["result_sha256"] = AUDIT.sha256_json(result)
                destination = (
                    run_root / "anchors" / anchor["anchor_id"] / "result.json"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(AUDIT.core.canonical_json_bytes(result))
                anchor_results.append(result)
            aggregate = {
                "status": "passed",
                "run_id": AUDIT.EXPECTED_SOURCE_RUN_ID,
                "window_id": window,
                "anchor_count": 3,
                "passed_anchor_count": 3,
                "all_required_comparisons_passed": True,
                "anchor_success_is_global_equivalence_proof": False,
                "all_6144_calibration_trials_authorized": True,
                "anchors": [
                    {
                        "anchor_id": item["anchor_id"],
                        "result_sha256": item["result_sha256"],
                    }
                    for item in anchor_results
                ],
            }
            aggregate["aggregate_sha256"] = AUDIT.sha256_json(aggregate)
            (run_root / "m39-anchor-equivalence.json").write_bytes(
                AUDIT.core.canonical_json_bytes(aggregate)
            )
            anchor_readiness = AUDIT._anchor_equivalence_readiness(
                run_root, self.config
            )
            self.assertTrue(anchor_readiness["equivalence_passed"])
            self.assertTrue(
                anchor_readiness["all_6144_calibration_trials_authorized"]
            )

    def test_published_result_opens_only_the_calibration_gate(self):
        result = json.loads(PUBLISHED.read_text(encoding="utf-8"))
        self.assertEqual(
            result["status"],
            "qualification_complete_calibration_authorized",
        )
        self.assertTrue(result["factor_bundle_gate"]["passed"])
        self.assertTrue(result["source_cache_readiness"]["inventory_present"])
        self.assertTrue(
            result["gates"]["real_m37_exhaustive_anchor_equivalence_passed"]
        )
        self.assertTrue(result["gates"]["all_6144_calibration_trials_authorized"])
        self.assertEqual(result["claim_boundary"]["real_anchor_trials_executed"], 3)
        self.assertEqual(result["claim_boundary"]["injection_trials_executed"], 0)
        self.assertFalse(result["claim_boundary"]["recovery_fraction_reported"])
        self.assertFalse(result["claim_boundary"]["sensitivity_claimed"])
        self.assertFalse(result["claim_boundary"]["occurrence_rate_claimed"])
        self.assertFalse(result["claim_boundary"]["technosignature_claimed"])
        self.assertEqual(
            result["anchor_plan_records"][0]["candidate_proxy_cell_count"],
            0,
        )

    def test_output_manifests_reproduce_without_spectral_artifacts(self):
        with tempfile.TemporaryDirectory() as run_temporary, tempfile.TemporaryDirectory() as output_temporary:
            output = Path(output_temporary)
            result = AUDIT.write_outputs(
                ROOT,
                Path(run_temporary),
                output,
                CONFIG,
            )
            self.assertEqual(
                json.loads((output / "qualification.json").read_text(encoding="utf-8")),
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
