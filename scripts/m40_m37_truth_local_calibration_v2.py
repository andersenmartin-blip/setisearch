#!/usr/bin/env python3
"""Execute the coverage-repaired 6,144-trial M40 calibration.

M40 v1 stopped fail-closed after a metadata audit proved that 16 of its 512
continuous truth tracks leave the exact native background.  V2 keeps every
motion, width, activity and S/N stratum, but reallocates all carrier indices
with the original permutation inside one common, coverage-proved interval.
No v1 score receipt is adopted.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import gzip
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

ABORT_SCRIPT_PATH = SCRIPTS / "m40_m37_native_coverage_abort.py"
ABORT_SPEC = importlib.util.spec_from_file_location("m40_abort", ABORT_SCRIPT_PATH)
if ABORT_SPEC is None or ABORT_SPEC.loader is None:
    raise RuntimeError("M40 coverage-abort implementation is unavailable")
abortdiag = importlib.util.module_from_spec(ABORT_SPEC)
ABORT_SPEC.loader.exec_module(abortdiag)
m40 = abortdiag.m40
core = m40.core
completeness = m40.completeness


CONFIG_PATH = ROOT / "config/m40_m37_truth_local_calibration_v2.json"
ABORT_RESULT_PATH = (
    ROOT / "results_m40_m37_truth_local_calibration" / abortdiag.ABORT_NAME
)
START_NAME = "calibration-start.json"
AGGREGATE_NAME = "calibration-aggregate.json"
LEDGER_NAME = "trial-ledger.jsonl.gz"
EXPECTED_COMMON_SAFE_INDEX_START = 78_748
EXPECTED_COMMON_SAFE_INDEX_STOP_INCLUSIVE = 611_204
EXPECTED_COMMON_SAFE_INDEX_COUNT = 532_457
EXPECTED_TRIAL_COUNT = 6_144
EXPECTED_TRUTH_COUNT = 512
EXPECTED_LEVEL_COUNT = 12
MAXIMUM_TRIAL_RECORD_BYTES = 16_384
MAXIMUM_TOTAL_RECORD_BYTES = 128_000_000


class CoverageRepairedPlan(NamedTuple):
    allocation_contract_sha256: str
    truth_inventory_sha256: str
    trial_inventory_sha256: str
    plan_sha256: str
    truths: tuple[Any, ...]
    trials: tuple[Any, ...]
    carrier_indices: tuple[int, ...]
    source_geometry_sha256: str

    def as_record(self) -> dict[str, Any]:
        return {
            "status": "m40-v2-coverage-repaired-prospective-allocation",
            "base_plan_sha256": completeness.M37_COMPLETENESS_PLAN_SHA256,
            "allocation_contract_sha256": self.allocation_contract_sha256,
            "truth_inventory_sha256": self.truth_inventory_sha256,
            "trial_inventory_sha256": self.trial_inventory_sha256,
            "truth_count_per_snr_level": len(self.truths),
            "snr_grid": list(completeness.M37_COMPLETENESS_SNR_GRID),
            "expected_trial_count": len(self.trials),
            "common_safe_proxy_index_start": (
                EXPECTED_COMMON_SAFE_INDEX_START
            ),
            "common_safe_proxy_index_stop_inclusive": (
                EXPECTED_COMMON_SAFE_INDEX_STOP_INCLUSIVE
            ),
            "common_safe_proxy_index_count": EXPECTED_COMMON_SAFE_INDEX_COUNT,
            "source_geometry_sha256": self.source_geometry_sha256,
            "plan_sha256": self.plan_sha256,
        }


def _load_config() -> dict[str, Any]:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.V0P6ContractError("M40 v2 config must be an object")
    return value


def _truth_at_index(truth: Any, index: int, grid: Any) -> Any:
    carrier_index = core._strict_int(index, "M40 v2 carrier index")
    q_hz = float(grid.score_hz[carrier_index])
    partial = replace(
        truth,
        truth_id="",
        proxy_carrier_index=carrier_index,
        proxy_carrier_lattice_index=(
            carrier_index - core.M37_SCORE_HALF_BINS
        ),
        proxy_carrier_hz=q_hz,
        proxy_carrier_mhz=q_hz / 1e6,
    )
    return replace(
        partial,
        truth_id=m40.sha256_json(partial.as_record(include_identity=False)),
    )


def _safe_index_interval(
    truth: Any,
    runtime: Mapping[str, Any],
    source_geometries: Mapping[str, Mapping[str, Any]],
) -> tuple[int, int]:
    half = truth.spectral_width_channels // 2
    lower_hz = -math.inf
    upper_hz = math.inf
    for epoch in truth.active_epochs_zero_based:
        label = runtime["on_labels"][epoch]
        geometry = source_geometries[label]["geometry"]
        factors = core.template_factors_from_basis(
            runtime["bundle"].basis,
            {
                "coefficient_x": truth.coefficient_x,
                "coefficient_y": truth.coefficient_y,
            },
            scan_label=label,
        )
        lower_hz = max(
            lower_hz,
            float(
                np.max(
                    (
                        geometry["raw_zero_hz"]
                        + (half - 0.499999999) * geometry["channel_width_hz"]
                    )
                    / factors
                )
            ),
        )
        upper_hz = min(
            upper_hz,
            float(
                np.min(
                    (
                        geometry["raw_zero_hz"]
                        + (
                            geometry["channel_count"]
                            - half
                            - 0.500000001
                        )
                        * geometry["channel_width_hz"]
                    )
                    / factors
                )
            ),
        )
    grid = runtime["grid"]
    margin = completeness.M37_COMPLETENESS_CARRIER_MARGIN_BINS
    lower = max(
        margin,
        int(np.searchsorted(grid.score_hz, lower_hz, side="left")),
    )
    upper = min(
        grid.score_bin_count - margin - 1,
        int(np.searchsorted(grid.score_hz, upper_hz, side="right") - 1),
    )
    while lower <= upper:
        candidate = _truth_at_index(truth, lower, grid)
        if abortdiag._truth_coverage(
            candidate,
            runtime["bundle"],
            source_geometries,
            runtime["on_labels"],
        )["covered"]:
            break
        lower += 1
    while upper >= lower:
        candidate = _truth_at_index(truth, upper, grid)
        if abortdiag._truth_coverage(
            candidate,
            runtime["bundle"],
            source_geometries,
            runtime["on_labels"],
        )["covered"]:
            break
        upper -= 1
    if lower > upper:
        raise core.V0P6CoverageError(
            f"M40 v2 truth {truth.truth_ordinal} has no safe carrier interval"
        )
    return lower, upper


def make_v2_plan(run_root: Path, runtime: Mapping[str, Any]) -> CoverageRepairedPlan:
    base = completeness.make_m37_prospective_completeness_plan()
    source_items = tuple(
        abortdiag._source_geometry(run_root, label)
        for label in runtime["on_labels"]
    )
    source_geometry_sha256 = m40.sha256_json(list(source_items))
    source_geometries = {item["scan_label"]: item for item in source_items}
    safe_intervals = tuple(
        _safe_index_interval(truth, runtime, source_geometries)
        for truth in base.truths
    )
    common_start = max(item[0] for item in safe_intervals)
    common_stop = min(item[1] for item in safe_intervals)
    common_count = common_stop - common_start + 1
    if (
        common_start,
        common_stop,
        common_count,
    ) != (
        EXPECTED_COMMON_SAFE_INDEX_START,
        EXPECTED_COMMON_SAFE_INDEX_STOP_INCLUSIVE,
        EXPECTED_COMMON_SAFE_INDEX_COUNT,
    ):
        raise core.V0P6IncompleteError(
            "M40 v2 common-safe interval changed: "
            f"observed={(common_start, common_stop, common_count)}"
        )
    if math.gcd(completeness.M37_COMPLETENESS_CARRIER_STEP, common_count) != 1:
        raise core.V0P6ContractError("M40 v2 carrier permutation is not injective")
    offset = completeness.M37_COMPLETENESS_MASTER_SEED % common_count
    carrier_indices = tuple(
        common_start
        + (
            offset
            + ordinal * completeness.M37_COMPLETENESS_CARRIER_STEP
        )
        % common_count
        for ordinal in range(EXPECTED_TRUTH_COUNT)
    )
    if len(set(carrier_indices)) != EXPECTED_TRUTH_COUNT:
        raise core.V0P6IncompleteError("M40 v2 carrier allocation has duplicates")
    allocation_contract = {
        "artifact_type": "m40-v2-native-coverage-repaired-allocation-v1",
        "base_allocation_contract_sha256": base.allocation_contract_sha256,
        "base_plan_sha256": base.plan_sha256,
        "v1_abort_sha256": json.loads(
            ABORT_RESULT_PATH.read_text(encoding="utf-8")
        )["abort_sha256"],
        "repair_scope": "replace-all-512-proxy-carriers-no-v1-score-adoption",
        "selection_inputs": "geometry-and-factor-metadata-only",
        "common_safe_proxy_index_start": common_start,
        "common_safe_proxy_index_stop_inclusive": common_stop,
        "common_safe_proxy_index_count": common_count,
        "carrier_offset_rule": "master_seed modulo common_safe_proxy_index_count",
        "carrier_step": completeness.M37_COMPLETENESS_CARRIER_STEP,
        "master_seed": completeness.M37_COMPLETENESS_MASTER_SEED,
        "source_geometry_sha256": source_geometry_sha256,
        "coverage_comparison": (
            "every rounded native center in every active integration leaves "
            "width//2 channels on both sides"
        ),
    }
    allocation_sha256 = m40.sha256_json(allocation_contract)
    truths = tuple(
        _truth_at_index(truth, carrier_indices[truth.truth_ordinal], runtime["grid"])
        for truth in base.truths
    )
    for truth in truths:
        completeness._validate_completeness_truth(truth)
        coverage = abortdiag._truth_coverage(
            truth,
            runtime["bundle"],
            source_geometries,
            runtime["on_labels"],
        )
        if coverage["covered"] is not True:
            raise core.V0P6CoverageError(
                f"M40 v2 allocated uncovered truth {truth.truth_ordinal}"
            )
    truth_sha256 = m40.sha256_json(
        [truth.as_record() for truth in truths]
    )
    trials = tuple(
        completeness._trial_for(allocation_sha256, truth, level_index)
        for level_index in range(EXPECTED_LEVEL_COUNT)
        for truth in truths
    )
    trial_sha256 = m40.sha256_json([trial.as_record() for trial in trials])
    plan_without_sha = {
        "status": "m40-v2-coverage-repaired-prospective-allocation",
        "base_plan_sha256": base.plan_sha256,
        "allocation_contract_sha256": allocation_sha256,
        "truth_inventory_sha256": truth_sha256,
        "trial_inventory_sha256": trial_sha256,
        "truth_count_per_snr_level": len(truths),
        "snr_grid": list(completeness.M37_COMPLETENESS_SNR_GRID),
        "expected_trial_count": len(trials),
        "common_safe_proxy_index_start": common_start,
        "common_safe_proxy_index_stop_inclusive": common_stop,
        "common_safe_proxy_index_count": common_count,
        "source_geometry_sha256": source_geometry_sha256,
    }
    return CoverageRepairedPlan(
        allocation_contract_sha256=allocation_sha256,
        truth_inventory_sha256=truth_sha256,
        trial_inventory_sha256=trial_sha256,
        plan_sha256=m40.sha256_json(plan_without_sha),
        truths=truths,
        trials=trials,
        carrier_indices=carrier_indices,
        source_geometry_sha256=source_geometry_sha256,
    )


def _validate_static_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if (
        config.get("artifact_type")
        != "m40-m37-truth-local-calibration-v2-config-v1"
        or config.get("status")
        != "execution-ready-after-v1-native-coverage-abort"
        or config.get("source_run_id") != m40.EXPECTED_RUN_ID
        or config.get("background_window") != m40.EXPECTED_WINDOW_ID
    ):
        raise core.V0P6ContractError("M40 v2 config scope changed")
    upstream = config.get("upstream_files")
    if not isinstance(upstream, list) or not upstream:
        raise core.V0P6IncompleteError("M40 v2 upstream inventory is empty")
    seen: set[str] = set()
    for item in upstream:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise core.V0P6ContractError("M40 v2 upstream entry changed")
        relative = str(item["path"])
        if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise core.V0P6ContractError("M40 v2 upstream path changed")
        seen.add(relative)
        if m40.sha256_file(ROOT / relative) != item["sha256"]:
            raise core.V0P6IncompleteError(
                f"M40 v2 upstream hash changed: {relative}"
            )
    abort = m40._read_canonical(ABORT_RESULT_PATH)
    abort_identity = dict(abort)
    observed_abort = abort_identity.pop("abort_sha256", None)
    if (
        observed_abort != m40.sha256_json(abort_identity)
        or abort.get("status") != "M40_V1_ABORTED_NO_CALIBRATION_CURVE"
        or abort.get("calibration_aggregate_permitted") is not False
        or abort.get("calibration_curve_produced") is not False
        or config.get("v1_abort", {}).get("abort_sha256") != observed_abort
        or config.get("v1_abort", {}).get("abort_file_sha256")
        != m40.sha256_file(ABORT_RESULT_PATH)
        or config.get("v1_abort", {}).get("v1_scores_adopted") is not False
    ):
        raise core.V0P6IncompleteError("M40 v1 abort boundary changed")
    if config.get("frozen_threshold") != {
        "operational_threshold_snr": 126.20158386230469,
        "threshold_certificate_sha256": (
            "d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71"
        ),
        "comparison": "finite best truth-local score >= operational threshold",
        "threshold_reestimated_after_injection": False,
    }:
        raise core.V0P6IncompleteError("M40 v2 threshold changed")
    return abort


def _validate_plan_config(config: Mapping[str, Any], plan: CoverageRepairedPlan) -> None:
    if config.get("frozen_repaired_trial_inventory") != plan.as_record():
        raise core.V0P6IncompleteError("M40 v2 repaired plan changed")
    if config.get("execution_contract") != {
        "authorization_flag": "--authorize-calibration-injections",
        "trial_order": "level-index-major-then-truth-ordinal",
        "shard_assignment": "trial-ordinal-modulo-shard-count",
        "per_trial_publication": "immutable-canonical-json",
        "cache_lifetime": "ephemeral-one-epoch-width-at-a-time",
        "two_pass_mask_recomputed": True,
        "missing_duplicate_or_extra_trial_policy": "stop-no-aggregate",
        "v1_score_receipt_adoption": "forbidden",
        "maximum_trial_record_canonical_bytes": MAXIMUM_TRIAL_RECORD_BYTES,
        "maximum_total_trial_record_canonical_bytes": MAXIMUM_TOTAL_RECORD_BYTES,
    }:
        raise core.V0P6IncompleteError("M40 v2 execution contract changed")
    if config.get("claim_boundary") != {
        "endpoint": "conditional-pointwise-truth-local-score-recovery",
        "interpolation_permitted": False,
        "physical_veto_survival_calibrated": False,
        "global_false_positive_field_replayed": False,
        "end_to_end_detector_completeness_claimed": False,
        "occurrence_rate_claimed": False,
        "technosignature_claimed": False,
    }:
        raise core.V0P6IncompleteError("M40 v2 claim boundary changed")


def _source_inventory() -> list[dict[str, Any]]:
    paths = (
        Path(__file__).resolve(),
        M40_PATH := SCRIPTS / "m40_m37_truth_local_calibration.py",
        ABORT_SCRIPT_PATH,
        m40.M39_PATH,
        m40.m39.REHYDRATE_PATH,
        ROOT / "src/seti_repeater/truth_local_v0p6.py",
        ROOT / "src/seti_repeater/completeness_v0p6.py",
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": m40.sha256_file(path),
            "nbytes": path.stat().st_size,
        }
        for path in paths
    ]


def initialize(run_root: Path, output_root: Path) -> dict[str, Any]:
    config = _load_config()
    abort = _validate_static_config(config)
    m40._validate_m39_qualification(config)
    runtime = m40._runtime_context(run_root, config)
    plan = make_v2_plan(run_root, runtime)
    _validate_plan_config(config, plan)
    sources = _source_inventory()
    schema = {
        "artifact_type": "m40-v2-trial-result-schema-v1",
        "base_trial_artifact_type": (
            "m40-m37-conditional-truth-local-trial-result-v1"
        ),
        "canonical_top_level_fields": list(m40.TRIAL_RECORD_FIELDS),
        "record_identity_field": "record_sha256",
        "recovery_comparison": config["frozen_threshold"]["comparison"],
    }
    record: dict[str, Any] = {
        "artifact_type": "m40-m37-truth-local-calibration-v2-start-v1",
        "status": "initialized-no-m40-v2-injection-executed",
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "config_sha256": m40.sha256_file(CONFIG_PATH),
        "config_canonical_sha256": m40.sha256_json(config),
        "v1_abort_sha256": abort["abort_sha256"],
        "v1_completed_trial_count": abort["completed_trial_count_before_stop"],
        "v1_score_receipts_adopted": 0,
        "m39_qualification_certificate_sha256": config["m39_qualification"][
            "certificate_sha256"
        ],
        "plan": plan.as_record(),
        "source_inventory": sources,
        "source_inventory_sha256": m40.sha256_json(sources),
        "trial_result_schema": schema,
        "trial_result_schema_sha256": m40.sha256_json(schema),
        "frozen_threshold": config["frozen_threshold"],
        "execution_contract": config["execution_contract"],
        "claim_boundary": config["claim_boundary"],
        "m40_v2_injection_trials_executed": 0,
    }
    record["start_sha256"] = m40.sha256_json(record)
    m40._publish_json(output_root / START_NAME, record)
    return record


def _validate_start(
    output_root: Path,
    config: Mapping[str, Any],
    plan: CoverageRepairedPlan,
) -> dict[str, Any]:
    start = m40._read_canonical(output_root / START_NAME)
    identity = dict(start)
    observed = identity.pop("start_sha256", None)
    sources = _source_inventory()
    if (
        observed != m40.sha256_json(identity)
        or start.get("status") != "initialized-no-m40-v2-injection-executed"
        or start.get("config_sha256") != m40.sha256_file(CONFIG_PATH)
        or start.get("config_canonical_sha256") != m40.sha256_json(config)
        or start.get("plan") != plan.as_record()
        or start.get("source_inventory") != sources
        or start.get("source_inventory_sha256") != m40.sha256_json(sources)
        or start.get("v1_score_receipts_adopted") != 0
        or start.get("m40_v2_injection_trials_executed") != 0
    ):
        raise core.V0P6IncompleteError("M40 v2 pre-execution freeze changed")
    return start


def execute_trials(
    run_root: Path,
    output_root: Path,
    *,
    authorized: bool,
    shard_index: int = 0,
    shard_count: int = 1,
    trial_ordinal: int | None = None,
) -> dict[str, Any]:
    if authorized is not True:
        raise RuntimeError(
            "M40 v2 calibration injections are not authorized; no trial executed"
        )
    shard = core._strict_int(shard_index, "M40 v2 shard index")
    count = core._strict_int(shard_count, "M40 v2 shard count")
    if count < 1 or count > EXPECTED_TRIAL_COUNT or not 0 <= shard < count:
        raise core.V0P6ContractError("M40 v2 shard selection is invalid")
    config = _load_config()
    _validate_static_config(config)
    m40._validate_m39_qualification(config)
    runtime = m40._runtime_context(run_root, config)
    plan = make_v2_plan(run_root, runtime)
    _validate_plan_config(config, plan)
    start = _validate_start(output_root, config, plan)
    if trial_ordinal is None:
        selected = [
            (ordinal, trial)
            for ordinal, trial in enumerate(plan.trials)
            if ordinal % count == shard
        ]
    else:
        ordinal = core._strict_int(trial_ordinal, "M40 v2 trial ordinal")
        if not 0 <= ordinal < len(plan.trials) or ordinal % count != shard:
            raise core.V0P6ContractError("M40 v2 trial is outside its shard")
        selected = [(ordinal, plan.trials[ordinal])]
    completed = 0
    recovered = 0
    for ordinal, trial in selected:
        record = m40.run_trial(
            run_root, output_root, ordinal, trial, runtime, start, config
        )
        completed += 1
        recovered += int(record["score_recovered"])
    return {
        "artifact_type": "m40-v2-shard-execution-summary-v1",
        "status": "selected-trials-complete",
        "shard_index": shard,
        "shard_count": count,
        "selected_trial_count": len(selected),
        "completed_trial_count": completed,
        "recovered_trial_count": recovered,
        "start_sha256": start["start_sha256"],
    }


def _gzip_jsonl(records: Sequence[Mapping[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", fileobj=buffer, mode="wb", compresslevel=9, mtime=0
    ) as handle:
        for record in records:
            handle.write(core.canonical_json_bytes(dict(record)))
            handle.write(b"\n")
    return buffer.getvalue()


def aggregate(run_root: Path, output_root: Path) -> dict[str, Any]:
    config = _load_config()
    _validate_static_config(config)
    m40._validate_m39_qualification(config)
    runtime = m40._runtime_context(run_root, config)
    plan = make_v2_plan(run_root, runtime)
    _validate_plan_config(config, plan)
    start = _validate_start(output_root, config, plan)
    expected_paths = {
        m40._trial_path(output_root, trial) for trial in plan.trials
    }
    present_paths = set((output_root / "trials").glob("level-*/*.json"))
    if present_paths != expected_paths:
        missing = len(expected_paths - present_paths)
        extra = len(present_paths - expected_paths)
        raise core.V0P6IncompleteError(
            f"M40 v2 ledger is incomplete or expanded: missing={missing}, extra={extra}"
        )
    records: list[dict[str, Any]] = []
    total_bytes = 0
    for ordinal, trial in enumerate(plan.trials):
        record = m40._read_canonical(m40._trial_path(output_root, trial))
        m40._validate_trial_record(record, trial, ordinal, start, config)
        total_bytes += len(core.canonical_json_bytes(record))
        if total_bytes > MAXIMUM_TOTAL_RECORD_BYTES:
            raise core.V0P6CapacityError("M40 v2 total trial-record cap exceeded")
        records.append(record)
    ledger_payload = _gzip_jsonl(records)
    ledger_sha256 = m40._publish_bytes(output_root / LEDGER_NAME, ledger_payload)
    levels = []
    for level_index, snr in enumerate(completeness.M37_COMPLETENESS_SNR_GRID):
        selected = [
            record
            for record in records
            if record["trial"]["level_index"] == level_index
        ]
        if len(selected) != EXPECTED_TRUTH_COUNT:
            raise core.V0P6IncompleteError("M40 v2 per-level inventory changed")
        recovered = sum(bool(record["score_recovered"]) for record in selected)
        low, high = completeness.wilson_interval_95(recovered, len(selected))
        finite_scores = [
            float(record["adapter"]["best_truth_local_score_snr"])
            for record in selected
            if record["adapter"]["best_truth_local_score_snr"] is not None
            and math.isfinite(
                float(record["adapter"]["best_truth_local_score_snr"])
            )
        ]
        levels.append(
            {
                "level_index": level_index,
                "ideal_single_epoch_snr": snr,
                "trials": len(selected),
                "recovered": recovered,
                "recovery_fraction": recovered / len(selected),
                "wilson_95_low": low,
                "wilson_95_high": high,
                "finite_best_score_count": len(finite_scores),
                "maximum_best_truth_local_score_snr": (
                    None if not finite_scores else max(finite_scores)
                ),
                "record_inventory_sha256": m40.sha256_json(
                    [record["record_sha256"] for record in selected]
                ),
            }
        )
    aggregate_record: dict[str, Any] = {
        "artifact_type": (
            "m40-m37-conditional-truth-local-calibration-aggregate-v2"
        ),
        "status": "complete",
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "start_sha256": start["start_sha256"],
        "v1_abort_sha256": start["v1_abort_sha256"],
        "v1_score_receipts_adopted": 0,
        "coverage_repaired_plan": plan.as_record(),
        "trial_count": len(records),
        "truth_count_per_level": EXPECTED_TRUTH_COUNT,
        "snr_level_count": EXPECTED_LEVEL_COUNT,
        "recovered_trial_count": sum(
            bool(record["score_recovered"]) for record in records
        ),
        "levels": levels,
        "trial_record_inventory_sha256": m40.sha256_json(
            [record["record_sha256"] for record in records]
        ),
        "trial_record_canonical_bytes": total_bytes,
        "ledger_path": LEDGER_NAME,
        "ledger_sha256": ledger_sha256,
        "ledger_nbytes": len(ledger_payload),
        "frozen_threshold": config["frozen_threshold"],
        "claim_boundary": config["claim_boundary"],
        "pointwise_only_no_interpolation": True,
        "randomized_background_condition_required": True,
        "downstream_survival_assumption_required_for_sensitivity_transport": True,
    }
    aggregate_record["aggregate_sha256"] = m40.sha256_json(aggregate_record)
    m40._publish_json(output_root / AGGREGATE_NAME, aggregate_record)
    return aggregate_record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--run-shard", action="store_true")
    mode.add_argument("--trial-ordinal", type=int)
    mode.add_argument("--aggregate", action="store_true")
    mode.add_argument("--print-plan", action="store_true")
    parser.add_argument("--authorize-calibration-injections", action="store_true")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    arguments = parser.parse_args()
    run_root = arguments.run_root.resolve()
    output_root = arguments.output_root.resolve()
    if arguments.print_plan:
        config = _load_config() if CONFIG_PATH.exists() else None
        if config is not None:
            _validate_static_config(config)
        runtime = m40._runtime_context(
            run_root,
            config if config is not None else m40._load_config(),
        )
        result = make_v2_plan(run_root, runtime).as_record()
    elif arguments.initialize:
        result = initialize(run_root, output_root)
    elif arguments.aggregate:
        result = aggregate(run_root, output_root)
    else:
        result = execute_trials(
            run_root,
            output_root,
            authorized=arguments.authorize_calibration_injections,
            shard_index=arguments.shard_index,
            shard_count=arguments.shard_count,
            trial_ordinal=arguments.trial_ordinal,
        )
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
