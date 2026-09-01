#!/usr/bin/env python3
"""Reproduce the offline M38 decision for M37 completeness feasibility."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from seti_repeater.completeness_v0p6 import (
    M37_COMPLETENESS_BACKGROUND_WINDOW,
    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL,
    M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL,
    M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
    make_m37_prospective_completeness_plan,
    validate_m37_completeness_plan,
)
from seti_repeater.search_v0p6 import canonical_json_bytes
from seti_repeater.sparse_replay_v0p6 import (
    SPARSE_LOCAL_KAT_RECEIPT_SHA256,
    SPARSE_PHYSICAL_REFERENCE_RECEIPT_SHA256,
    SPARSE_RETENTION_REFERENCE_RECEIPT_SHA256,
)


EXPECTED_ARTIFACT_TYPE = "m38-m37-completeness-feasibility-plan-v1"
EXPECTED_ANALYSIS_BASE_COMMIT = "c3d05125064ff179abfc9f556bd1ee8a3b63337b"
EXPECTED_STATUS = "retrospective-feasibility-freeze-before-calibration-execution"
EXPECTED_SOURCE_RUN_ID = "m37-v0p6p1-primary-006"
EXPECTED_ANALYSIS = "retrospective-truth-local-score-recovery-calibration"
EXPECTED_TRIAL_INVENTORY = (
    "reuse-the-existing-512-truth-by-12-snr-allocation-without-removal"
)
EXPECTED_ENDPOINT = (
    "truth-local-score-at-or-above-frozen-threshold-after-native-injection-"
    "and-recomputed-two-pass-mask"
)
EXPECTED_INTERPRETATION = "conditional-score-recovery-sensitivity-only"
EXPECTED_STOPPING_RULE = (
    "stop-after-feasibility-certificate-no-spectral-read-no-injection-result"
)
EXPECTED_GATES = (
    "rehydrate-and-hash-verify-the-m37-1412p5-native-source-and-factor-artifacts",
    "implement-a-restartable-production-truth-local-adapter-with-bounded-resource-receipts",
    "pass-real-m37-anchor-trials-against-the-exhaustive-operational-window-replay",
    "freeze-the-production-adapter-and-output-schema-before-running-the-6144-trial-ledger",
    "account-for-every-preallocated-trial-exactly-once-with-no-truncation",
    "report-only-pointwise-score-recovery-with-explicit-background-distribution-and-downstream-survival-conditions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def validate_config(config: Mapping[str, Any]) -> None:
    require(config.get("artifact_type") == EXPECTED_ARTIFACT_TYPE, "config type changed")
    require(
        config.get("analysis_base_commit") == EXPECTED_ANALYSIS_BASE_COMMIT,
        "analysis base commit changed",
    )
    require(config.get("status") == EXPECTED_STATUS, "config status changed")
    scope = config.get("scope")
    require(isinstance(scope, Mapping), "scope is missing")
    require(scope.get("source_run_id") == EXPECTED_SOURCE_RUN_ID, "source run changed")
    require(
        scope.get("background_window") == M37_COMPLETENESS_BACKGROUND_WINDOW,
        "background window changed",
    )
    for key in (
        "detector_or_threshold_changes_permitted",
        "new_spectral_access_during_feasibility_audit",
        "quantitative_sensitivity_claim_permitted",
        "occurrence_rate_claim_permitted",
    ):
        require(scope.get(key) is False, f"{key} must remain false")

    inputs = config.get("inputs")
    require(isinstance(inputs, list) and len(inputs) == 4, "input inventory changed")
    paths = [item.get("path") for item in inputs if isinstance(item, Mapping)]
    require(len(paths) == len(set(paths)) == 4, "input paths are invalid or duplicated")
    for item in inputs:
        require(isinstance(item, Mapping), "input entry must be an object")
        digest = item.get("sha256")
        require(
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest),
            "input SHA-256 is invalid",
        )

    replay = config.get("frozen_full_replay_gate")
    require(isinstance(replay, Mapping), "full-replay gate is missing")
    plan = make_m37_prospective_completeness_plan()
    validate_m37_completeness_plan(plan)
    require(replay.get("trial_count") == plan.expected_trial_count, "trial count changed")
    require(
        replay.get("score_cells_per_trial")
        == M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL,
        "per-trial replay work changed",
    )
    require(
        replay.get("score_cells_total")
        == M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL,
        "total replay work changed",
    )
    require(
        replay.get("production_feasibility_status")
        == M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
        "production feasibility status changed",
    )
    require(replay.get("truncation_permitted") is False, "truncation was enabled")
    require(
        replay.get("silent_trial_reduction_permitted") is False,
        "silent trial reduction was enabled",
    )

    receipts = config.get("existing_sparse_reference_receipts")
    require(isinstance(receipts, Mapping), "sparse receipt inventory is missing")
    expected_receipts = {
        "phase_1_truth_local_masks_and_scores_sha256": SPARSE_LOCAL_KAT_RECEIPT_SHA256,
        "phase_2_retention_off_rank_sha256": SPARSE_RETENTION_REFERENCE_RECEIPT_SHA256,
        "phase_3_adjacent_off_receiver_alias_sha256": (
            SPARSE_PHYSICAL_REFERENCE_RECEIPT_SHA256
        ),
    }
    for key, expected in expected_receipts.items():
        require(receipts.get(key) == expected, f"{key} changed")
    require(
        receipts.get("production_equivalence_proven") is False,
        "synthetic receipts were promoted to production evidence",
    )

    decision = config.get("decision")
    require(isinstance(decision, Mapping), "decision is missing")
    require(decision.get("full_exhaustive_replay_selected") is False, "full replay selected")
    require(decision.get("selected_analysis") == EXPECTED_ANALYSIS, "analysis changed")
    require(
        decision.get("trial_inventory") == EXPECTED_TRIAL_INVENTORY,
        "trial inventory description changed",
    )
    require(decision.get("recovery_endpoint") == EXPECTED_ENDPOINT, "endpoint changed")
    require(
        decision.get("interpretation") == EXPECTED_INTERPRETATION,
        "interpretation changed",
    )
    for key in (
        "end_to_end_detector_completeness_claimed",
        "physical_veto_survival_calibrated",
        "global_false-positive-field_replayed",
    ):
        require(decision.get(key) is False, f"{key} must remain false")
    gates = config.get("mandatory_execution_gates")
    require(
        isinstance(gates, list) and tuple(gates) == EXPECTED_GATES,
        "mandatory execution gates changed",
    )
    require(config.get("stopping_rule") == EXPECTED_STOPPING_RULE, "stopping rule changed")


def validate_inputs(repo_root: Path, config: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for item in config["inputs"]:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe input path")
        path = repo_root / relative
        require(path.is_file(), f"missing input: {relative}")
        observed = sha256_file(path)
        require(observed == item["sha256"], f"input hash changed: {relative}")
        inventory.append(
            {"path": relative.as_posix(), "sha256": observed, "nbytes": path.stat().st_size}
        )
    return inventory


def build_feasibility_result(repo_root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    validate_config(config)
    inputs = validate_inputs(repo_root, config)
    outcome = load_json(repo_root / "results_m37_v0p6p1_primary_006/outcome-summary.json")
    controller = load_json(repo_root / "results_m37_v0p6p1_primary_006/run-controller.json")
    plan = make_m37_prospective_completeness_plan()
    validate_m37_completeness_plan(plan)

    require(outcome.get("run_id") == EXPECTED_SOURCE_RUN_ID, "outcome run changed")
    require(outcome["journal"]["stage"] == "outcome_complete", "M37 is not outcome-complete")
    require(
        outcome["outcome"]["global_outcome"]
        == "closed_no_unresolved_scientific_candidates",
        "M37 global outcome changed",
    )
    require(outcome["outcome"]["unresolved_candidate_count"] == 0, "M37 has unresolved candidates")
    require(outcome["claim_boundary"]["measured_completeness_complete"] is False, "M37 already reports completeness")
    require(controller.get("run_id") == EXPECTED_SOURCE_RUN_ID, "controller run changed")
    require(controller.get("stage") == "outcome_complete", "controller stage changed")
    require(
        controller["artifacts"]["outcome"]["outcome_certificate_sha256"]
        == outcome["outcome"]["certificate_sha256"],
        "controller/outcome certificate mismatch",
    )

    config_record = json.loads(canonical_json_bytes(dict(config)))
    result = {
        "artifact_type": "m38-m37-completeness-feasibility-result-v1",
        "status": "feasibility_protocol_frozen_no_calibration_executed",
        "source_run_id": EXPECTED_SOURCE_RUN_ID,
        "config_sha256": sha256_json(config_record),
        "inputs": inputs,
        "m37_boundary": {
            "stage": "outcome_complete",
            "global_outcome": "closed_no_unresolved_scientific_candidates",
            "unresolved_candidate_count": 0,
            "measured_completeness_complete": False,
            "operational_threshold_snr": outcome["threshold"]["operational_threshold_snr"],
            "threshold_certificate_sha256": outcome["threshold"]["threshold_certificate_sha256"],
        },
        "full_replay_gate": {
            "trial_count": plan.expected_trial_count,
            "score_cells_per_trial": M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_PER_TRIAL,
            "score_cells_total": M37_COMPLETENESS_FULL_REPLAY_SCORE_CELLS_TOTAL,
            "work_multiplier_vs_one_window_replay": plan.expected_trial_count,
            "production_feasibility_status": M37_COMPLETENESS_PRODUCTION_FEASIBILITY_STATUS,
            "gate_closed": True,
            "truncation_permitted": False,
        },
        "selected_path": {
            **config_record["decision"],
            "background_window": M37_COMPLETENESS_BACKGROUND_WINDOW,
            "expected_trial_count": plan.expected_trial_count,
            "truth_inventory_sha256": plan.truth_inventory_sha256,
            "trial_inventory_sha256": plan.trial_inventory_sha256,
            "plan_sha256": plan.plan_sha256,
        },
        "existing_sparse_reference_receipts": config_record[
            "existing_sparse_reference_receipts"
        ],
        "mandatory_execution_gates": config_record["mandatory_execution_gates"],
        "claim_boundary": {
            "spectral_values_read_by_this_audit": False,
            "injection_trials_executed": 0,
            "recovery_fraction_reported": False,
            "sensitivity_claimed": False,
            "occurrence_rate_claimed": False,
            "technosignature_claimed": False,
        },
        "next_required_stage": (
            "production truth-local adapter and real-M37 exhaustive anchor equivalence"
        ),
        "stopping_rule": EXPECTED_STOPPING_RULE,
    }
    result["certificate"] = {
        "config_sha256": result["config_sha256"],
        "input_inventory_sha256": sha256_json(inputs),
        "full_replay_gate_preserved": True,
        "synthetic_receipts_not_promoted_to_production": True,
        "no_spectral_read": True,
        "no_quantitative_claim": True,
    }
    result["certificate"]["certificate_sha256"] = sha256_json(result["certificate"])
    return json.loads(canonical_json_bytes(result))


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_outputs(repo_root: Path, output_dir: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    result = build_feasibility_result(repo_root, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "feasibility.json"
    atomic_write(result_path, canonical_json_bytes(result))

    input_lines = [f"{item['sha256']}  {item['path']}" for item in result["inputs"]]
    input_manifest = output_dir / "INPUT_MANIFEST.sha256"
    atomic_write(input_manifest, ("\n".join(input_lines) + "\n").encode("utf-8"))

    result_files = (result_path, input_manifest)
    result_lines = [
        f"{sha256_file(path)}  {path.relative_to(output_dir).as_posix()}"
        for path in result_files
    ]
    atomic_write(
        output_dir / "RESULTS_MANIFEST.sha256",
        ("\n".join(result_lines) + "\n").encode("utf-8"),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/m38_m37_completeness_feasibility.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_m38_m37_completeness_feasibility"),
    )
    arguments = parser.parse_args()
    repo_root = arguments.repo_root.resolve()
    config_path = arguments.config
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    output_dir = arguments.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    result = write_outputs(repo_root, output_dir, config_path)
    print(json.dumps({
        "status": result["status"],
        "certificate_sha256": result["certificate"]["certificate_sha256"],
        "next_required_stage": result["next_required_stage"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
