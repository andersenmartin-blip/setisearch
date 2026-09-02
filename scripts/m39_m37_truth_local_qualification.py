#!/usr/bin/env python3
"""Start M39 with a fail-closed truth-local qualification certificate.

This command reads compact M37 metadata and, when available, the immutable
Run 006 factor bundle.  It never opens a spectral source product, executes an
injection, or treats an anchor as passed.  Real-anchor execution is a later
explicitly authorized stage after the 1412.5 MHz source/cache inventory is
rehydrated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from seti_repeater import factor_bundle_v0p6 as factor_io
from seti_repeater import search_v0p6 as core
from seti_repeater.completeness_v0p6 import (
    M37_COMPLETENESS_BACKGROUND_WINDOW,
    M37_COMPLETENESS_PLAN_SHA256,
    M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
    M37_COMPLETENESS_SNR_GRID,
    M37_COMPLETENESS_TRIAL_INVENTORY_SHA256,
    M37_COMPLETENESS_TRUTH_INVENTORY_SHA256,
    iter_m37_completeness_trials,
    make_m37_prospective_completeness_plan,
    validate_m37_completeness_plan,
)
from seti_repeater.truth_local_v0p6 import (
    TRUTH_LOCAL_ADAPTER_STATUS,
    TRUTH_LOCAL_INTERVAL_PADDING_BINS,
    TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS,
    TRUTH_LOCAL_MAXIMUM_LOCAL_ARRAY_BYTES,
    TRUTH_LOCAL_MAXIMUM_MAPPED_CACHE_BYTES,
    plan_truth_local_template_scores_interval,
)


EXPECTED_ARTIFACT_TYPE = "m39-m37-truth-local-qualification-plan-v1"
EXPECTED_ANALYSIS_BASE_COMMIT = "1a4b34714cdec531c5c48a226ac652fad14eadf5"
EXPECTED_STATUS = "qualification-started-source-rehydration-pending"
EXPECTED_SOURCE_RUN_ID = "m37-v0p6p1-primary-006"
EXPECTED_ANALYSIS = "retrospective-truth-local-score-recovery-calibration"
EXPECTED_ENDPOINT = "conditional-pointwise-score-recovery-only"
EXPECTED_STOPPING_RULE = (
    "stop-after-factor-and-adapter-qualification-until-source-cache-"
    "rehydration-and-real-anchor-equivalence"
)
EXPECTED_ANCHORS = (
    (
        "no-local-cell-low-snr-upper-carrier-width-1-pair-01",
        0,
        0,
        "0a881efe1b850bdd10148a8b9884a01e9723a5a3f89ef81ba628fc9df06f7566",
    ),
    (
        "mid-snr-lower-carrier-width-129-pair-02",
        5,
        15,
        "abbb4a04f925d314cff412d6025f9b707cb3014c758d71bb6b17063c0d98b2fa",
    ),
    (
        "high-snr-interior-carrier-width-129-all-epochs",
        11,
        31,
        "d8234f5a814067464f85408855b301fc4d9528742ec1310bbb5d5d856f325eb4",
    ),
)
EXPECTED_COMPARISONS = (
    "best-truth-local-score-float32-bits",
    "best-template-index",
    "best-spectral-width-index",
    "best-activity-subset-index",
    "best-proxy-carrier-index",
    "two-pass-mask-candidate-bits",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def sha256_array(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain one JSON object")
    return value


def _digest(value: Any, label: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        f"{label} must be a lowercase SHA-256",
    )
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
    require(scope.get("analysis") == EXPECTED_ANALYSIS, "analysis changed")
    require(scope.get("endpoint") == EXPECTED_ENDPOINT, "endpoint changed")
    for key in (
        "detector_or_threshold_changes_permitted",
        "calibration_trials_permitted_before_anchor_equivalence",
        "physical_veto_survival_claim_permitted",
        "global_false_positive_replay_claim_permitted",
        "quantitative_sensitivity_claim_permitted",
        "occurrence_rate_claim_permitted",
    ):
        require(scope.get(key) is False, f"{key} must remain false")

    inputs = config.get("inputs")
    require(isinstance(inputs, list) and len(inputs) == 5, "input inventory changed")
    paths: list[str] = []
    for item in inputs:
        require(isinstance(item, Mapping), "input entry must be an object")
        path = item.get("path")
        require(isinstance(path, str) and path, "input path is invalid")
        paths.append(path)
        _digest(item.get("sha256"), "input identity")
    require(len(paths) == len(set(paths)), "input paths are duplicated")

    source = config.get("source_run_artifacts")
    require(isinstance(source, Mapping), "source-run artifacts are missing")
    for key in (
        "factor_bundle_file_sha256",
        "factor_bundle_manifest_sha256",
        "factor_table_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "analysis_contract_sha256",
        "source_metadata_sha256",
    ):
        _digest(source.get(key), key)
    require(source.get("factor_bundle_path") == "factor_bundle.v0p6", "factor path changed")
    require(
        tuple(source.get("required_scan_labels", ()))
        == (
            "epoch1_on",
            "epoch1_off",
            "epoch2_on",
            "epoch2_off",
            "epoch3_on",
            "epoch3_off",
        ),
        "source scan inventory changed",
    )
    require(
        tuple(source.get("required_spectral_widths", ())) == core.M37_SPECTRAL_WIDTHS,
        "source width inventory changed",
    )
    require(
        source.get("required_source_manifest_path") == "m39-source-manifest.json"
        and source.get("required_cache_manifest_path") == "m39-cache-manifest.v0p6",
        "source/cache manifest paths changed",
    )

    plan = make_m37_prospective_completeness_plan()
    validate_m37_completeness_plan(plan)
    inventory = config.get("frozen_completeness_inventory")
    require(isinstance(inventory, Mapping), "completeness inventory is missing")
    require(inventory.get("truth_count") == len(plan.truths), "truth count changed")
    require(tuple(inventory.get("snr_grid", ())) == M37_COMPLETENESS_SNR_GRID, "S/N grid changed")
    require(inventory.get("trial_count") == plan.expected_trial_count, "trial count changed")
    require(
        inventory.get("truth_inventory_sha256") == M37_COMPLETENESS_TRUTH_INVENTORY_SHA256,
        "truth inventory changed",
    )
    require(
        inventory.get("trial_inventory_sha256") == M37_COMPLETENESS_TRIAL_INVENTORY_SHA256,
        "trial inventory changed",
    )
    require(inventory.get("plan_sha256") == M37_COMPLETENESS_PLAN_SHA256, "plan changed")

    adapter = config.get("truth_local_adapter")
    require(isinstance(adapter, Mapping), "adapter contract is missing")
    require(adapter.get("source_path") == "src/seti_repeater/truth_local_v0p6.py", "adapter path changed")
    require(adapter.get("source_sha256") == inputs[3]["sha256"], "adapter hashes disagree")
    require(adapter.get("status") == TRUTH_LOCAL_ADAPTER_STATUS, "adapter status changed")
    require(adapter.get("recovery_tolerance_hz") == M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ, "recovery tolerance changed")
    require(adapter.get("interval_padding_bins") == TRUTH_LOCAL_INTERVAL_PADDING_BINS, "interval padding changed")
    require(adapter.get("maximum_distance_cells") == TRUTH_LOCAL_MAXIMUM_DISTANCE_CELLS, "distance-cell cap changed")
    require(adapter.get("maximum_local_array_bytes") == TRUTH_LOCAL_MAXIMUM_LOCAL_ARRAY_BYTES, "local-array cap changed")
    require(adapter.get("maximum_mapped_cache_bytes") == TRUTH_LOCAL_MAXIMUM_MAPPED_CACHE_BYTES, "mapped-cache cap changed")
    require(adapter.get("recomputes_two_pass_mask") is True, "two-pass mask was disabled")
    for key in (
        "physical_veto_survival_calibrated",
        "global_false_positive_field_replayed",
        "production_equivalence_proven",
    ):
        require(adapter.get(key) is False, f"{key} must remain false")

    trials = {
        (trial.level_index, trial.truth.truth_ordinal): trial
        for trial in iter_m37_completeness_trials(plan)
    }
    anchors = config.get("real_m37_anchor_inventory")
    require(isinstance(anchors, list) and len(anchors) == len(EXPECTED_ANCHORS), "anchor inventory changed")
    for record, expected in zip(anchors, EXPECTED_ANCHORS, strict=True):
        require(isinstance(record, Mapping), "anchor entry must be an object")
        anchor_id, level_index, truth_ordinal, trial_id = expected
        require(record.get("anchor_id") == anchor_id, "anchor identity changed")
        require(record.get("level_index") == level_index, "anchor level changed")
        require(record.get("truth_ordinal") == truth_ordinal, "anchor truth changed")
        require(record.get("trial_id") == trial_id, "anchor trial changed")
        trial = trials[(level_index, truth_ordinal)]
        require(record.get("truth_id") == trial.truth.truth_id, "anchor truth identity changed")
        require(record.get("ideal_single_epoch_snr") == trial.ideal_single_epoch_snr, "anchor S/N changed")
        require(record.get("spectral_width_channels") == trial.truth.spectral_width_channels, "anchor width changed")
        require(tuple(record.get("active_epochs_zero_based", ())) == trial.truth.active_epochs_zero_based, "anchor activity changed")
        require(record.get("proxy_carrier_index") == trial.truth.proxy_carrier_index, "anchor carrier changed")

    equivalence = config.get("anchor_equivalence_contract")
    require(isinstance(equivalence, Mapping), "anchor equivalence contract is missing")
    require(
        equivalence.get("reference")
        == "exhaustive-operational-replay-of-the-complete-m37_1412p5-window",
        "anchor reference changed",
    )
    require(tuple(equivalence.get("required_comparisons", ())) == EXPECTED_COMPARISONS, "anchor comparisons changed")
    require(equivalence.get("all_anchors_must_pass") is True, "partial anchor success was enabled")
    require(equivalence.get("mismatch_policy") == "stop-no-calibration-trials", "anchor mismatch policy changed")
    require(equivalence.get("anchor_success_is_global_equivalence_proof") is False, "anchors were promoted to global proof")
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
            {
                "path": relative.as_posix(),
                "sha256": observed,
                "nbytes": path.stat().st_size,
            }
        )
    return inventory


def _factor_bundle_gate(
    run_root: Path,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], factor_io.FactorBundle | None]:
    source = config["source_run_artifacts"]
    bootstrap_path = run_root / "bootstrap.json"
    bundle_path = run_root / source["factor_bundle_path"]
    if not bootstrap_path.is_file() or not bundle_path.is_file():
        return {
            "passed": False,
            "reason": "m37-run-bootstrap-or-factor-bundle-absent",
            "bootstrap_present": bootstrap_path.is_file(),
            "factor_bundle_present": bundle_path.is_file(),
        }, None
    bootstrap = load_json(bootstrap_path)
    require(bootstrap.get("run_id") == EXPECTED_SOURCE_RUN_ID, "factor run ID changed")
    for config_key, bootstrap_key in (
        ("factor_bundle_file_sha256", "factor_bundle_file_sha256"),
        ("factor_bundle_manifest_sha256", "factor_bundle_manifest_sha256"),
        ("factor_table_sha256", "factor_table_sha256"),
        ("analysis_contract_sha256", "analysis_contract_sha256"),
        ("source_metadata_sha256", "source_metadata_sha256"),
    ):
        require(source[config_key] == bootstrap.get(bootstrap_key), f"bootstrap {bootstrap_key} changed")
    bundle = factor_io.open_m37_factor_bundle(
        bundle_path,
        expected_manifest_sha256=source["factor_bundle_manifest_sha256"],
        expected_file_sha256=source["factor_bundle_file_sha256"],
        expected_factor_table_sha256=source["factor_table_sha256"],
    )
    receipt = bundle.receipt
    require(receipt.factor_basis_sha256 == source["factor_basis_sha256"], "factor basis changed")
    require(receipt.factor_basis_labels_sha256 == source["factor_basis_labels_sha256"], "factor labels changed")
    require(receipt.analysis_contract_sha256 == source["analysis_contract_sha256"], "analysis contract changed")
    require(receipt.source_metadata_sha256 == source["source_metadata_sha256"], "source metadata changed")
    return {
        "passed": True,
        "reason": None,
        "bootstrap_sha256": sha256_file(bootstrap_path),
        "factor_bundle_file_sha256": receipt.file_sha256,
        "factor_bundle_manifest_sha256": receipt.manifest_sha256,
        "factor_table_sha256": receipt.factor_table_sha256,
        "factor_basis_sha256": receipt.factor_basis_sha256,
        "factor_basis_labels_sha256": receipt.factor_basis_labels_sha256,
        "analysis_contract_sha256": receipt.analysis_contract_sha256,
        "source_metadata_sha256": receipt.source_metadata_sha256,
        "file_nbytes": receipt.file_nbytes,
    }, bundle


def _truth_factors(bundle: factor_io.FactorBundle, truth: Any) -> np.ndarray:
    pieces = tuple(
        core.template_factors_from_basis(
            bundle.basis,
            {
                "coefficient_x": truth.coefficient_x,
                "coefficient_y": truth.coefficient_y,
            },
            scan_label=label,
        )
        for label in ("epoch1_on", "epoch2_on", "epoch3_on")
    )
    result = np.ascontiguousarray(np.concatenate(pieces), dtype="<f8")
    result.setflags(write=False)
    return result


def _anchor_plans(
    config: Mapping[str, Any],
    bundle: factor_io.FactorBundle,
) -> tuple[list[dict[str, Any]], str]:
    completeness = make_m37_prospective_completeness_plan()
    trials = {
        (trial.level_index, trial.truth.truth_ordinal): trial
        for trial in iter_m37_completeness_trials(completeness)
    }
    matrix = core.factor_matrix_for_kind(bundle.table, bundle.basis, bundle.scans, "on")
    grid = core.make_m37_proxy_carrier_grid(M37_COMPLETENESS_BACKGROUND_WINDOW)
    records: list[dict[str, Any]] = []
    for anchor in config["real_m37_anchor_inventory"]:
        trial = trials[(anchor["level_index"], anchor["truth_ordinal"])]
        truth_factors = _truth_factors(bundle, trial.truth)
        plans = plan_truth_local_template_scores_interval(
            grid,
            matrix,
            trial.truth.proxy_carrier_hz,
            truth_factors,
            tolerance_hz=M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
        )
        assigned = plans[trial.truth.template_index].candidate_indices.indices
        candidate_count = sum(
            item.candidate_indices.indices.size for item in plans
        )
        plan_records = [item.as_record() for item in plans]
        records.append(
            {
                "anchor_id": anchor["anchor_id"],
                "trial_id": trial.trial_id,
                "truth_id": trial.truth.truth_id,
                "truth_factor_sha256": core.float64_vector_sha256(truth_factors),
                "template_factor_matrix_sha256": sha256_array(matrix),
                "template_plan_inventory_sha256": sha256_json(plan_records),
                "template_plan_count": len(plans),
                "candidate_proxy_cell_count": candidate_count,
                "mask_dependency_proxy_cell_count": sum(
                    item.mask_dependency_indices.indices.size for item in plans
                ),
                "candidate_distance_cell_count": (
                    candidate_count * truth_factors.size
                ),
                "truth_local_candidate_exists": candidate_count > 0,
                "assigned_truth_cell_planned": (
                    trial.truth.proxy_carrier_index in assigned
                ),
                "real_spectral_anchor_executed": False,
                "equivalence_passed": False,
            }
        )
    return records, sha256_json(records)


def _source_cache_readiness(run_root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    source = config["source_run_artifacts"]
    window = config["scope"]["background_window"]
    labels = tuple(source["required_scan_labels"])
    widths = tuple(source["required_spectral_widths"])
    source_receipts = tuple(
        run_root / "sources" / window / f"{label}.product.json"
        for label in labels
    )
    cache_sidecars = tuple(
        run_root / "caches" / window / label / f"width-{width}.json"
        for label in labels
        for width in widths
    )
    source_manifest = run_root / source["required_source_manifest_path"]
    cache_manifest = run_root / source["required_cache_manifest_path"]
    completion_path = run_root / "m39-rehydration-completion.json"
    present_source_receipts = sum(path.is_file() for path in source_receipts)
    present_cache_sidecars = sum(path.is_file() for path in cache_sidecars)
    complete = (
        source_manifest.is_file()
        and cache_manifest.is_file()
        and present_source_receipts == len(source_receipts)
        and present_cache_sidecars == len(cache_sidecars)
    )
    deep_verified = False
    completion_sha256 = None
    source_deep_verification_sha256 = None
    cache_deep_verification_sha256 = None
    if complete and completion_path.is_file():
        completion = load_json(completion_path)
        claimed = completion.get("completion_sha256")
        basis = {
            key: value for key, value in completion.items()
            if key != "completion_sha256"
        }
        require(claimed == sha256_json(basis), "rehydration completion identity changed")
        require(completion.get("status") == "complete", "rehydration is incomplete")
        require(completion.get("run_id") == EXPECTED_SOURCE_RUN_ID, "rehydration run changed")
        require(completion.get("window_id") == window, "rehydration window changed")
        require(completion.get("source_product_count") == len(source_receipts), "rehydration source count changed")
        require(completion.get("cache_entry_count") == len(cache_sidecars), "rehydration cache count changed")
        require(completion.get("all_six_sources_verified") is True, "source deep verification failed")
        require(completion.get("all_48_caches_verified") is True, "cache deep verification failed")
        require(completion.get("source_manifest_sha256") == sha256_file(source_manifest), "source manifest identity changed")
        require(completion.get("cache_manifest_file_sha256") == sha256_file(cache_manifest), "cache manifest identity changed")
        deep_verified = True
        completion_sha256 = claimed
        source_deep_verification_sha256 = completion.get("source_deep_verification_sha256")
        cache_deep_verification_sha256 = completion.get("cache_deep_verification_sha256")
    return {
        "inventory_present": complete,
        "deep_hash_verification_executed": deep_verified,
        "required_source_product_count": len(source_receipts),
        "present_source_product_receipt_count": present_source_receipts,
        "required_cache_sidecar_count": len(cache_sidecars),
        "present_cache_sidecar_count": present_cache_sidecars,
        "source_manifest_present": source_manifest.is_file(),
        "cache_manifest_present": cache_manifest.is_file(),
        "rehydration_completion_present": completion_path.is_file(),
        "rehydration_completion_sha256": completion_sha256,
        "source_deep_verification_sha256": source_deep_verification_sha256,
        "cache_deep_verification_sha256": cache_deep_verification_sha256,
        "spectral_values_read_by_this_audit": False,
    }


def _anchor_equivalence_readiness(
    run_root: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    aggregate_path = run_root / "m39-anchor-equivalence.json"
    anchors = tuple(config["real_m37_anchor_inventory"])
    result_paths = tuple(
        run_root / "anchors" / anchor["anchor_id"] / "result.json"
        for anchor in anchors
    )
    present = sum(path.is_file() for path in result_paths)
    result_inventory: list[dict[str, Any]] = []
    passed = False
    aggregate_sha256 = None
    calibration_authorized = False
    if aggregate_path.is_file() and present == len(result_paths):
        aggregate = load_json(aggregate_path)
        claimed = aggregate.get("aggregate_sha256")
        basis = {
            key: value for key, value in aggregate.items()
            if key != "aggregate_sha256"
        }
        require(claimed == sha256_json(basis), "anchor aggregate identity changed")
        require(aggregate.get("status") == "passed", "anchor aggregate did not pass")
        require(aggregate.get("run_id") == EXPECTED_SOURCE_RUN_ID, "anchor run changed")
        require(aggregate.get("background_window", aggregate.get("window_id")) == M37_COMPLETENESS_BACKGROUND_WINDOW, "anchor window changed")
        require(aggregate.get("anchor_count") == len(anchors), "anchor aggregate count changed")
        require(aggregate.get("passed_anchor_count") == len(anchors), "not all anchors passed")
        require(aggregate.get("all_required_comparisons_passed") is True, "required anchor comparison failed")
        require(aggregate.get("anchor_success_is_global_equivalence_proof") is False, "anchors were promoted to global proof")
        aggregate_entries = {
            item["anchor_id"]: item for item in aggregate["anchors"]
        }
        for anchor, path in zip(anchors, result_paths, strict=True):
            result = load_json(path)
            claimed_result = result.get("result_sha256")
            result_basis = {
                key: value for key, value in result.items()
                if key != "result_sha256"
            }
            require(claimed_result == sha256_json(result_basis), "anchor result identity changed")
            require(result.get("anchor_id") == anchor["anchor_id"], "anchor result order changed")
            require(result.get("trial_id") == anchor["trial_id"], "anchor result trial changed")
            require(result.get("equivalence_passed") is True, "anchor equivalence failed")
            require(result.get("comparison", {}).get("passed") is True, "anchor comparisons failed")
            require(
                aggregate_entries[anchor["anchor_id"]]["result_sha256"]
                == claimed_result,
                "anchor aggregate/result identity changed",
            )
            result_inventory.append(
                {
                    "anchor_id": anchor["anchor_id"],
                    "result_sha256": claimed_result,
                    "candidate_proxy_cell_count": result[
                        "candidate_proxy_cell_count"
                    ],
                }
            )
        passed = True
        aggregate_sha256 = claimed
        calibration_authorized = (
            aggregate.get("all_6144_calibration_trials_authorized") is True
        )
    return {
        "aggregate_present": aggregate_path.is_file(),
        "required_anchor_count": len(result_paths),
        "present_anchor_result_count": present,
        "restartable_runner_complete": passed,
        "equivalence_passed": passed,
        "all_6144_calibration_trials_authorized": (
            passed and calibration_authorized
        ),
        "aggregate_sha256": aggregate_sha256,
        "result_inventory": result_inventory,
        "result_inventory_sha256": (
            sha256_json(result_inventory) if result_inventory else None
        ),
        "anchor_success_is_global_equivalence_proof": False,
    }


def build_qualification_result(
    repo_root: Path,
    run_root: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    validate_config(config)
    inputs = validate_inputs(repo_root, config)
    factor_gate, bundle = _factor_bundle_gate(run_root, config)
    source_readiness = _source_cache_readiness(run_root, config)
    anchor_readiness = _anchor_equivalence_readiness(run_root, config)
    anchor_plans: list[dict[str, Any]] = []
    anchor_plan_inventory_sha256: str | None = None
    if bundle is not None:
        anchor_plans, anchor_plan_inventory_sha256 = _anchor_plans(config, bundle)
        passed_ids = {
            item["anchor_id"] for item in anchor_readiness["result_inventory"]
        }
        for record in anchor_plans:
            if record["anchor_id"] in passed_ids:
                record["real_spectral_anchor_executed"] = True
                record["equivalence_passed"] = True
        anchor_plan_inventory_sha256 = sha256_json(anchor_plans)

    outcome = load_json(repo_root / "results_m37_v0p6p1_primary_006/outcome-summary.json")
    require(outcome.get("run_id") == EXPECTED_SOURCE_RUN_ID, "outcome run changed")
    require(outcome["claim_boundary"]["measured_completeness_complete"] is False, "M37 already reports measured completeness")
    require(outcome["outcome"]["unresolved_candidate_count"] == 0, "M37 unresolved outcome changed")

    status = (
        "qualification_started_factor_bundle_pending"
        if not factor_gate["passed"]
        else "qualification_started_source_rehydration_pending"
        if not source_readiness["deep_hash_verification_executed"]
        else "qualification_started_real_anchor_execution_pending"
        if not anchor_readiness["equivalence_passed"]
        else "qualification_complete_calibration_authorized"
    )
    config_record = json.loads(core.canonical_json_bytes(dict(config)))
    result = {
        "artifact_type": "m39-m37-truth-local-qualification-result-v1",
        "status": status,
        "source_run_id": EXPECTED_SOURCE_RUN_ID,
        "background_window": M37_COMPLETENESS_BACKGROUND_WINDOW,
        "config_sha256": sha256_json(config_record),
        "inputs": inputs,
        "m37_boundary": {
            "unresolved_candidate_count": 0,
            "measured_completeness_complete": False,
            "operational_threshold_snr": outcome["threshold"]["operational_threshold_snr"],
            "threshold_certificate_sha256": outcome["threshold"]["threshold_certificate_sha256"],
        },
        "frozen_completeness_inventory": config_record["frozen_completeness_inventory"],
        "factor_bundle_gate": factor_gate,
        "truth_local_adapter": config_record["truth_local_adapter"],
        "source_cache_readiness": source_readiness,
        "anchor_equivalence_readiness": anchor_readiness,
        "real_m37_anchor_inventory": config_record["real_m37_anchor_inventory"],
        "anchor_plan_records": anchor_plans,
        "anchor_plan_inventory_sha256": anchor_plan_inventory_sha256,
        "anchor_equivalence_contract": config_record["anchor_equivalence_contract"],
        "gates": {
            "compact_factor_ancestry_hash_verified": factor_gate["passed"],
            "adapter_source_and_output_schema_frozen": True,
            "source_and_cache_ancestry_hash_verified": source_readiness["deep_hash_verification_executed"],
            "restartable_real_anchor_runner_complete": anchor_readiness["restartable_runner_complete"],
            "real_m37_exhaustive_anchor_equivalence_passed": anchor_readiness["equivalence_passed"],
            "all_6144_calibration_trials_authorized": anchor_readiness["all_6144_calibration_trials_authorized"],
        },
        "claim_boundary": {
            "spectral_values_read_by_this_audit": False,
            "spectral_values_read_by_rehydration": source_readiness["deep_hash_verification_executed"],
            "injection_trials_executed": 0,
            "real_anchor_trials_executed": len(anchor_readiness["result_inventory"]),
            "recovery_fraction_reported": False,
            "sensitivity_claimed": False,
            "physical_veto_survival_calibrated": False,
            "global_false_positive_field_replayed": False,
            "occurrence_rate_claimed": False,
            "technosignature_claimed": False,
        },
        "next_required_stage": (
            "rehydrate-and-hash-verify-m37_1412p5-source-products-and-caches"
            if factor_gate["passed"] and not source_readiness["deep_hash_verification_executed"]
            else "rehydrate-m37-factor-bundle"
            if not factor_gate["passed"]
            else "execute-predeclared-real-m37-exhaustive-anchor-comparisons"
            if not anchor_readiness["equivalence_passed"]
            else "execute-frozen-6144-trial-conditional-truth-local-calibration"
        ),
        "stopping_rule": EXPECTED_STOPPING_RULE,
    }
    result["certificate"] = {
        "config_sha256": result["config_sha256"],
        "input_inventory_sha256": sha256_json(inputs),
        "factor_bundle_gate_passed": factor_gate["passed"],
        "anchor_plan_inventory_sha256": anchor_plan_inventory_sha256,
        "no_spectral_read_by_this_audit": True,
        "no_calibration_injection_executed": True,
        "real_anchor_equivalence_passed": anchor_readiness["equivalence_passed"],
        "anchor_aggregate_sha256": anchor_readiness["aggregate_sha256"],
        "no_quantitative_claim": True,
    }
    result["certificate"]["certificate_sha256"] = sha256_json(result["certificate"])
    return json.loads(core.canonical_json_bytes(result))


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_outputs(
    repo_root: Path,
    run_root: Path,
    output_dir: Path,
    config_path: Path,
) -> dict[str, Any]:
    config = load_json(config_path)
    result = build_qualification_result(repo_root, run_root, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "qualification.json"
    atomic_write(result_path, core.canonical_json_bytes(result))

    copied_results: list[Path] = []
    if result["source_cache_readiness"]["deep_hash_verification_executed"]:
        destination = output_dir / "rehydration-completion.json"
        atomic_write(
            destination,
            core.canonical_json_bytes(
                load_json(run_root / "m39-rehydration-completion.json")
            ),
        )
        copied_results.append(destination)
    if result["anchor_equivalence_readiness"]["equivalence_passed"]:
        aggregate_destination = output_dir / "anchor-equivalence.json"
        atomic_write(
            aggregate_destination,
            core.canonical_json_bytes(
                load_json(run_root / "m39-anchor-equivalence.json")
            ),
        )
        copied_results.append(aggregate_destination)
        for anchor in config["real_m37_anchor_inventory"]:
            destination = output_dir / "anchors" / f"{anchor['anchor_id']}.json"
            atomic_write(
                destination,
                core.canonical_json_bytes(
                    load_json(
                        run_root
                        / "anchors"
                        / anchor["anchor_id"]
                        / "result.json"
                    )
                ),
            )
            copied_results.append(destination)

    input_manifest = output_dir / "INPUT_MANIFEST.sha256"
    input_lines = [f"{item['sha256']}  {item['path']}" for item in result["inputs"]]
    atomic_write(input_manifest, ("\n".join(input_lines) + "\n").encode("utf-8"))
    result_lines = [
        f"{sha256_file(path)}  {path.relative_to(output_dir).as_posix()}"
        for path in (result_path, input_manifest, *copied_results)
    ]
    atomic_write(
        output_dir / "RESULTS_MANIFEST.sha256",
        ("\n".join(result_lines) + "\n").encode("utf-8"),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--m37-run-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/m39_m37_truth_local_qualification.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_m39_m37_truth_local_qualification"),
    )
    arguments = parser.parse_args()
    repo_root = arguments.repo_root.resolve()
    run_root = arguments.m37_run_root.resolve()
    config_path = arguments.config if arguments.config.is_absolute() else repo_root / arguments.config
    output_dir = arguments.output_dir if arguments.output_dir.is_absolute() else repo_root / arguments.output_dir
    result = write_outputs(repo_root, run_root, output_dir, config_path)
    print(
        json.dumps(
            {
                "status": result["status"],
                "certificate_sha256": result["certificate"]["certificate_sha256"],
                "next_required_stage": result["next_required_stage"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
