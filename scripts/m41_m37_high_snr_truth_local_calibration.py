#!/usr/bin/env python3
"""Execute the separately frozen M41 higher-S/N truth-local calibration.

M41 reuses every coverage-repaired M40 v2 truth but creates 6,144 new trials
at 12 higher S/N levels.  M40 receipts remain immutable and are never adopted.
"""

from __future__ import annotations

import argparse
import functools
import gc
import gzip
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

M40_V2_PATH = SCRIPTS / "m40_m37_truth_local_calibration_v2.py"
M40_V2_SPEC = importlib.util.spec_from_file_location("m40_v2_for_m41", M40_V2_PATH)
if M40_V2_SPEC is None or M40_V2_SPEC.loader is None:
    raise RuntimeError("M40 v2 implementation is unavailable")
m40v2 = importlib.util.module_from_spec(M40_V2_SPEC)
M40_V2_SPEC.loader.exec_module(m40v2)
m40 = m40v2.m40
core = m40.core
completeness = m40.completeness


CONFIG_PATH = ROOT / "config/m41_m37_high_snr_truth_local_calibration.json"
M40_RESULT_ROOT = ROOT / "results_m40_m37_truth_local_calibration_v2"
M40_AGGREGATE_PATH = M40_RESULT_ROOT / m40v2.AGGREGATE_NAME
M40_LEDGER_PATH = M40_RESULT_ROOT / m40v2.LEDGER_NAME
M40_AGGREGATE_SHA256 = (
    "03e162aea769c2020df6509171217dbf32624e69b4a3ccad4ae159c85836f974"
)
M40_LEDGER_SHA256 = (
    "127a3ed5babcdd36385fe1d8cce1a2339b1702511820848c7103aab5a45fd22c"
)
M41_SNR_GRID = (
    48.0,
    56.0,
    64.0,
    72.0,
    80.0,
    88.0,
    96.0,
    112.0,
    128.0,
    160.0,
    192.0,
    256.0,
)
M41_NOISE_DERIVATION_LABEL = "m41-high-snr-independent-noise-v1"
EXPECTED_TRUTH_COUNT = 512
EXPECTED_LEVEL_COUNT = len(M41_SNR_GRID)
EXPECTED_TRIAL_COUNT = EXPECTED_TRUTH_COUNT * EXPECTED_LEVEL_COUNT
START_NAME = "calibration-start.json"
AGGREGATE_NAME = "calibration-aggregate.json"
LEDGER_NAME = "trial-ledger.jsonl.gz"
MAXIMUM_TRIAL_RECORD_BYTES = 16_384
MAXIMUM_TOTAL_RECORD_BYTES = 128_000_000

TRIAL_RECORD_FIELDS = (
    "artifact_type",
    "status",
    "start_sha256",
    "parent_m40_v2_aggregate_sha256",
    "source_run_id",
    "window_id",
    "trial_ordinal",
    "trial",
    "truth",
    "source_product_sha256s",
    "background_sha256",
    "noise_shift_channels",
    "injected_native_sha256",
    "adapter",
    "threshold",
    "score_recovered",
    "claim_boundary",
    "record_sha256",
)


class M41Plan(NamedTuple):
    extension_contract_sha256: str
    truth_inventory_sha256: str
    trial_inventory_sha256: str
    plan_sha256: str
    truths: tuple[Any, ...]
    trials: tuple[Any, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "status": "m41-post-m40-v2-higher-snr-extension",
            "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
            "parent_m40_v2_ledger_sha256": M40_LEDGER_SHA256,
            "extension_contract_sha256": self.extension_contract_sha256,
            "truth_inventory_sha256": self.truth_inventory_sha256,
            "trial_inventory_sha256": self.trial_inventory_sha256,
            "truth_count_per_snr_level": len(self.truths),
            "snr_grid": list(M41_SNR_GRID),
            "expected_trial_count": len(self.trials),
            "noise_derivation_label": M41_NOISE_DERIVATION_LABEL,
            "plan_sha256": self.plan_sha256,
        }


def sha256_json(value: Any) -> str:
    return m40.sha256_json(value)


def sha256_file(path: Path) -> str:
    return m40.sha256_file(path)


def _load_config() -> dict[str, Any]:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.V0P6ContractError("M41 config must be an object")
    return value


def _truth_from_record(record: Mapping[str, Any]) -> Any:
    values = dict(record)
    if values.pop("truth_track_contract", None) != "Y_i(u,q) = q * F_u_i":
        raise core.V0P6IncompleteError("M40 v2 truth-track contract changed")
    active = values.get("active_epochs_zero_based")
    if not isinstance(active, list):
        raise core.V0P6ContractError("M40 v2 truth activity is invalid")
    values["active_epochs_zero_based"] = tuple(active)
    truth = completeness.CompletenessTruth(**values)
    completeness._validate_completeness_truth(truth)
    return truth


@functools.lru_cache(maxsize=1)
def _published_m40_truths() -> tuple[Any, ...]:
    aggregate = m40._read_canonical(M40_AGGREGATE_PATH)
    identity = dict(aggregate)
    observed = identity.pop("aggregate_sha256", None)
    if (
        observed != sha256_json(identity)
        or observed != M40_AGGREGATE_SHA256
        or aggregate.get("status") != "complete"
        or aggregate.get("trial_count") != m40v2.EXPECTED_TRIAL_COUNT
        or aggregate.get("truth_count_per_level") != EXPECTED_TRUTH_COUNT
        or aggregate.get("recovered_trial_count") != 0
        or aggregate.get("v1_score_receipts_adopted") != 0
        or aggregate.get("ledger_sha256") != M40_LEDGER_SHA256
        or sha256_file(M40_LEDGER_PATH) != M40_LEDGER_SHA256
    ):
        raise core.V0P6IncompleteError("published M40 v2 aggregate changed")

    truths: list[Any | None] = [None] * EXPECTED_TRUTH_COUNT
    record_hashes: list[str] = []
    record_count = 0
    with gzip.open(M40_LEDGER_PATH, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise core.V0P6ContractError("M40 v2 ledger record is invalid")
            record_identity = dict(record)
            record_sha256 = record_identity.pop("record_sha256", None)
            if (
                record_sha256 != sha256_json(record_identity)
                or record.get("trial_ordinal") != record_count
                or record.get("start_sha256") != aggregate["start_sha256"]
                or record.get("score_recovered") is not False
            ):
                raise core.V0P6IncompleteError("M40 v2 ledger identity changed")
            truth_ordinal = record_count % EXPECTED_TRUTH_COUNT
            if record.get("truth", {}).get("truth_ordinal") != truth_ordinal:
                raise core.V0P6IncompleteError("M40 v2 truth order changed")
            truth = _truth_from_record(record["truth"])
            if truths[truth_ordinal] is None:
                truths[truth_ordinal] = truth
            elif truths[truth_ordinal] != truth:
                raise core.V0P6IncompleteError("M40 v2 truth changed across levels")
            record_hashes.append(str(record_sha256))
            record_count += 1
    if (
        record_count != m40v2.EXPECTED_TRIAL_COUNT
        or any(item is None for item in truths)
        or sha256_json(record_hashes)
        != aggregate["trial_record_inventory_sha256"]
    ):
        raise core.V0P6IncompleteError("M40 v2 ledger inventory changed")
    result = tuple(item for item in truths if item is not None)
    expected_truth_sha256 = m40v2._load_config()[
        "frozen_repaired_trial_inventory"
    ]["truth_inventory_sha256"]
    if sha256_json([item.as_record() for item in result]) != expected_truth_sha256:
        raise core.V0P6IncompleteError("M40 v2 truth inventory changed")
    return result


def _trial_for(
    extension_contract_sha256: str,
    truth: Any,
    level_index: int,
) -> Any:
    index = core._strict_int(level_index, "M41 level index")
    if not 0 <= index < EXPECTED_LEVEL_COUNT:
        raise core.V0P6ContractError("M41 level index is invalid")
    snr = M41_SNR_GRID[index]
    noise_seed = completeness._seed64(
        M40_AGGREGATE_SHA256,
        M41_NOISE_DERIVATION_LABEL,
        index,
        snr,
        truth.truth_ordinal,
    )
    key = {
        "artifact_type": "m41-high-snr-trial-identity-v1",
        "extension_contract_sha256": extension_contract_sha256,
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "truth_id": truth.truth_id,
        "level_index": index,
        "ideal_single_epoch_snr": snr,
        "noise_seed": noise_seed,
    }
    return completeness.CompletenessTrial(
        trial_id=sha256_json(key),
        level_index=index,
        ideal_single_epoch_snr=snr,
        noise_seed=noise_seed,
        truth=truth,
    )


@functools.lru_cache(maxsize=1)
def make_plan() -> M41Plan:
    truths = _published_m40_truths()
    truth_sha256 = sha256_json([truth.as_record() for truth in truths])
    contract = {
        "artifact_type": "m41-post-m40-v2-higher-snr-extension-contract-v1",
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "parent_m40_v2_ledger_sha256": M40_LEDGER_SHA256,
        "truth_inventory_sha256": truth_sha256,
        "truth_reuse": "all-512-m40-v2-truths-byte-identical",
        "snr_grid": list(M41_SNR_GRID),
        "noise_derivation": (
            "uint64-big-endian-first-8-bytes-of-sha256-canonical-json"
        ),
        "noise_derivation_label": M41_NOISE_DERIVATION_LABEL,
        "m40_score_receipts_adopted": 0,
        "two_pass_mask_recomputed": True,
        "threshold_reestimated": False,
    }
    extension_sha256 = sha256_json(contract)
    trials = tuple(
        _trial_for(extension_sha256, truth, level_index)
        for level_index in range(EXPECTED_LEVEL_COUNT)
        for truth in truths
    )
    trial_sha256 = sha256_json([trial.as_record() for trial in trials])
    plan_without_sha = {
        "status": "m41-post-m40-v2-higher-snr-extension",
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "parent_m40_v2_ledger_sha256": M40_LEDGER_SHA256,
        "extension_contract_sha256": extension_sha256,
        "truth_inventory_sha256": truth_sha256,
        "trial_inventory_sha256": trial_sha256,
        "truth_count_per_snr_level": len(truths),
        "snr_grid": list(M41_SNR_GRID),
        "expected_trial_count": len(trials),
        "noise_derivation_label": M41_NOISE_DERIVATION_LABEL,
    }
    return M41Plan(
        extension_contract_sha256=extension_sha256,
        truth_inventory_sha256=truth_sha256,
        trial_inventory_sha256=trial_sha256,
        plan_sha256=sha256_json(plan_without_sha),
        truths=truths,
        trials=trials,
    )


def validate_config(config: Mapping[str, Any], plan: M41Plan) -> None:
    if (
        config.get("artifact_type")
        != "m41-m37-high-snr-truth-local-calibration-config-v1"
        or config.get("status") != "pre-execution-freeze-post-m40-v2"
        or config.get("source_run_id") != m40.EXPECTED_RUN_ID
        or config.get("background_window") != m40.EXPECTED_WINDOW_ID
    ):
        raise core.V0P6ContractError("M41 config scope changed")
    upstream = config.get("upstream_files")
    if not isinstance(upstream, list) or not upstream:
        raise core.V0P6IncompleteError("M41 upstream inventory is empty")
    seen: set[str] = set()
    for item in upstream:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise core.V0P6ContractError("M41 upstream entry changed")
        relative = str(item["path"])
        if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise core.V0P6ContractError("M41 upstream path changed")
        seen.add(relative)
        if sha256_file(ROOT / relative) != item["sha256"]:
            raise core.V0P6IncompleteError(f"M41 upstream hash changed: {relative}")
    if config.get("parent_m40_v2") != {
        "status": "complete",
        "aggregate_sha256": M40_AGGREGATE_SHA256,
        "aggregate_file_sha256": sha256_file(M40_AGGREGATE_PATH),
        "ledger_sha256": M40_LEDGER_SHA256,
        "trial_count": 6144,
        "recovered_trial_count": 0,
        "maximum_tested_snr": 40.0,
        "maximum_finite_score_snr": 70.08597564697266,
        "score_receipts_adopted": 0,
    }:
        raise core.V0P6IncompleteError("M41 parent M40 v2 boundary changed")
    if config.get("frozen_trial_inventory") != plan.as_record():
        raise core.V0P6IncompleteError("M41 frozen trial inventory changed")
    if config.get("frozen_threshold") != {
        "operational_threshold_snr": 126.20158386230469,
        "threshold_certificate_sha256": (
            "d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71"
        ),
        "comparison": "finite best truth-local score >= operational threshold",
        "threshold_reestimated_after_injection": False,
    }:
        raise core.V0P6IncompleteError("M41 threshold changed")
    if config.get("execution_contract") != {
        "authorization_flag": "--authorize-calibration-injections",
        "trial_order": "level-index-major-then-truth-ordinal",
        "shard_assignment": "trial-ordinal-modulo-shard-count",
        "per_trial_publication": "immutable-canonical-json",
        "cache_lifetime": "ephemeral-one-epoch-width-at-a-time",
        "two_pass_mask_recomputed": True,
        "missing_duplicate_or_extra_trial_policy": "stop-no-aggregate",
        "m40_score_receipt_adoption": "forbidden",
        "maximum_trial_record_canonical_bytes": MAXIMUM_TRIAL_RECORD_BYTES,
        "maximum_total_trial_record_canonical_bytes": MAXIMUM_TOTAL_RECORD_BYTES,
    }:
        raise core.V0P6IncompleteError("M41 execution contract changed")
    if config.get("claim_boundary") != {
        "endpoint": "conditional-pointwise-truth-local-score-recovery",
        "post_m40_adaptive_extension": True,
        "interpolation_permitted": False,
        "physical_veto_survival_calibrated": False,
        "global_false_positive_field_replayed": False,
        "end_to_end_detector_completeness_claimed": False,
        "occurrence_rate_claimed": False,
        "technosignature_claimed": False,
    }:
        raise core.V0P6IncompleteError("M41 claim boundary changed")


def _runtime_context(run_root: Path, plan: M41Plan) -> dict[str, Any]:
    m40_config = m40v2._load_config()
    m40v2._validate_static_config(m40_config)
    m40._validate_m39_qualification(m40_config)
    runtime = m40._runtime_context(run_root, m40_config)
    parent = m40v2.make_v2_plan(run_root, runtime)
    m40v2._validate_plan_config(m40_config, parent)
    if tuple(item.as_record() for item in parent.truths) != tuple(
        item.as_record() for item in plan.truths
    ):
        raise core.V0P6IncompleteError("M41 runtime truths differ from M40 v2")
    return runtime


def _source_inventory() -> list[dict[str, Any]]:
    paths = (
        Path(__file__).resolve(),
        M40_V2_PATH,
        SCRIPTS / "m40_m37_truth_local_calibration.py",
        m40.M39_PATH,
        m40.m39.REHYDRATE_PATH,
        ROOT / "src/seti_repeater/truth_local_v0p6.py",
        ROOT / "src/seti_repeater/completeness_v0p6.py",
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "nbytes": path.stat().st_size,
        }
        for path in paths
    ]


def initialize(run_root: Path, output_root: Path) -> dict[str, Any]:
    config = _load_config()
    plan = make_plan()
    validate_config(config, plan)
    _runtime_context(run_root, plan)
    sources = _source_inventory()
    schema = {
        "artifact_type": "m41-trial-result-schema-v1",
        "canonical_top_level_fields": list(TRIAL_RECORD_FIELDS),
        "record_identity_field": "record_sha256",
        "recovery_comparison": config["frozen_threshold"]["comparison"],
    }
    record: dict[str, Any] = {
        "artifact_type": "m41-m37-high-snr-truth-local-calibration-start-v1",
        "status": "initialized-no-m41-injection-executed",
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "config_sha256": sha256_file(CONFIG_PATH),
        "config_canonical_sha256": sha256_json(config),
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "parent_m40_v2_ledger_sha256": M40_LEDGER_SHA256,
        "m40_score_receipts_adopted": 0,
        "plan": plan.as_record(),
        "source_inventory": sources,
        "source_inventory_sha256": sha256_json(sources),
        "trial_result_schema": schema,
        "trial_result_schema_sha256": sha256_json(schema),
        "frozen_threshold": config["frozen_threshold"],
        "execution_contract": config["execution_contract"],
        "claim_boundary": config["claim_boundary"],
        "m41_injection_trials_executed": 0,
    }
    record["start_sha256"] = sha256_json(record)
    m40._publish_json(output_root / START_NAME, record)
    return record


def _validate_start(
    output_root: Path,
    config: Mapping[str, Any],
    plan: M41Plan,
) -> dict[str, Any]:
    start = m40._read_canonical(output_root / START_NAME)
    identity = dict(start)
    observed = identity.pop("start_sha256", None)
    sources = _source_inventory()
    if (
        observed != sha256_json(identity)
        or start.get("status") != "initialized-no-m41-injection-executed"
        or start.get("config_sha256") != sha256_file(CONFIG_PATH)
        or start.get("config_canonical_sha256") != sha256_json(config)
        or start.get("parent_m40_v2_aggregate_sha256") != M40_AGGREGATE_SHA256
        or start.get("parent_m40_v2_ledger_sha256") != M40_LEDGER_SHA256
        or start.get("m40_score_receipts_adopted") != 0
        or start.get("plan") != plan.as_record()
        or start.get("source_inventory") != sources
        or start.get("source_inventory_sha256") != sha256_json(sources)
        or start.get("m41_injection_trials_executed") != 0
    ):
        raise core.V0P6IncompleteError("M41 pre-execution freeze changed")
    return start


def _trial_path(output_root: Path, trial: Any) -> Path:
    return (
        output_root
        / "trials"
        / f"level-{trial.level_index:02d}"
        / f"truth-{trial.truth.truth_ordinal:03d}.json"
    )


def _score_recovered(adapter: Mapping[str, Any], threshold: float) -> bool:
    score = adapter.get("best_truth_local_score_snr")
    return bool(
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and math.isfinite(float(score))
        and float(score) >= threshold
    )


def _validate_trial_record(
    record: Mapping[str, Any],
    trial: Any,
    ordinal: int,
    start: Mapping[str, Any],
    config: Mapping[str, Any],
) -> None:
    if set(record) != set(TRIAL_RECORD_FIELDS):
        raise core.V0P6IncompleteError("M41 trial record schema changed")
    identity = dict(record)
    observed = identity.pop("record_sha256", None)
    if observed != sha256_json(identity):
        raise core.V0P6IncompleteError("M41 trial record identity changed")
    if len(core.canonical_json_bytes(record)) > MAXIMUM_TRIAL_RECORD_BYTES:
        raise core.V0P6CapacityError("M41 trial record byte cap exceeded")
    adapter = record.get("adapter")
    if not isinstance(adapter, dict):
        raise core.V0P6ContractError("M41 adapter result is missing")
    adapter_identity = dict(adapter)
    adapter_sha256 = adapter_identity.pop("result_sha256", None)
    if adapter_sha256 != sha256_json(adapter_identity):
        raise core.V0P6IncompleteError("M41 adapter result identity changed")
    if (
        record.get("artifact_type")
        != "m41-m37-high-snr-truth-local-trial-result-v1"
        or record.get("status") != "complete"
        or record.get("start_sha256") != start["start_sha256"]
        or record.get("parent_m40_v2_aggregate_sha256") != M40_AGGREGATE_SHA256
        or record.get("source_run_id") != m40.EXPECTED_RUN_ID
        or record.get("window_id") != m40.EXPECTED_WINDOW_ID
        or record.get("trial_ordinal") != ordinal
        or record.get("trial") != trial.as_record()
        or record.get("truth") != trial.truth.as_record()
        or record.get("threshold") != config["frozen_threshold"]
        or record.get("claim_boundary") != config["claim_boundary"]
        or record.get("score_recovered")
        is not _score_recovered(
            adapter, config["frozen_threshold"]["operational_threshold_snr"]
        )
        or adapter.get("status") != m40.TRUTH_LOCAL_ADAPTER_STATUS
        or adapter.get("window_id") != m40.EXPECTED_WINDOW_ID
        or adapter.get("template_count") != core.M37_TEMPLATE_COUNT
        or adapter.get("cache_count") != 24
        or adapter.get("two_pass_mask_recomputed") is not True
        or adapter.get("global_false_positive_field_replayed") is not False
        or adapter.get("physical_veto_survival_calibrated") is not False
        or adapter.get("production_equivalence_proven") is not False
    ):
        raise core.V0P6IncompleteError("M41 trial record content changed")


def make_trial_record(
    trial: Any,
    ordinal: int,
    start: Mapping[str, Any],
    config: Mapping[str, Any],
    adapter: Mapping[str, Any],
    *,
    source_product_sha256s: Sequence[str],
    background_sha256: str,
    noise_shift_channels: Sequence[int],
    injected_native_sha256: str,
) -> dict[str, Any]:
    sources = [
        core._frozen_sha256(item, "M41 source product identity")
        for item in source_product_sha256s
    ]
    shifts = [
        core._strict_int(item, "M41 native noise shift")
        for item in noise_shift_channels
    ]
    if len(sources) != 3 or len(shifts) != 3 or any(item < 0 for item in shifts):
        raise core.V0P6IncompleteError("M41 source/noise inventory changed")
    adapter_record = json.loads(core.canonical_json_bytes(dict(adapter)))
    record: dict[str, Any] = {
        "artifact_type": "m41-m37-high-snr-truth-local-trial-result-v1",
        "status": "complete",
        "start_sha256": core._frozen_sha256(
            start["start_sha256"], "M41 start identity"
        ),
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "trial_ordinal": core._strict_int(ordinal, "M41 trial ordinal"),
        "trial": trial.as_record(),
        "truth": trial.truth.as_record(),
        "source_product_sha256s": sources,
        "background_sha256": core._frozen_sha256(
            background_sha256, "M41 background identity"
        ),
        "noise_shift_channels": shifts,
        "injected_native_sha256": core._frozen_sha256(
            injected_native_sha256, "M41 injected identity"
        ),
        "adapter": adapter_record,
        "threshold": config["frozen_threshold"],
        "score_recovered": _score_recovered(
            adapter_record,
            config["frozen_threshold"]["operational_threshold_snr"],
        ),
        "claim_boundary": config["claim_boundary"],
    }
    record["record_sha256"] = sha256_json(record)
    _validate_trial_record(record, trial, ordinal, start, config)
    return record


def run_trial(
    run_root: Path,
    output_root: Path,
    ordinal: int,
    trial: Any,
    runtime: Mapping[str, Any],
    start: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    path = _trial_path(output_root, trial)
    if path.exists():
        record = m40._read_canonical(path)
        _validate_trial_record(record, trial, ordinal, start, config)
        m40._emit("m41_trial_complete", trial_ordinal=ordinal, restart_hit=True)
        return record
    started = time.monotonic()
    bundle = runtime["bundle"]
    on_labels = runtime["on_labels"]
    background = completeness.seal_m37_native_trial_background(
        trial,
        m40.m39._product_stream(run_root, bundle.scans, on_labels),
        factor_basis=bundle.basis,
        factor_table=bundle.table,
        expected_product_sha256s=runtime["product_sha256s"],
        expected_extraction_receipt_sha256s=runtime["extraction_sha256s"],
        context={
            "milestone": 41,
            "trial_ordinal": ordinal,
            "start_sha256": start["start_sha256"],
            "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        },
    )
    injected = completeness.inject_native_before_filter(background, trial)
    truth_factors = np.ascontiguousarray(
        np.concatenate(
            tuple(
                core.template_factors_from_basis(
                    bundle.basis,
                    {
                        "coefficient_x": trial.truth.coefficient_x,
                        "coefficient_y": trial.truth.coefficient_y,
                    },
                    scan_label=label,
                )
                for label in on_labels
            )
        ),
        dtype="<f8",
    )
    plans = m40.plan_truth_local_template_scores_interval(
        runtime["grid"],
        runtime["distance_matrix"],
        trial.truth.proxy_carrier_hz,
        truth_factors,
        tolerance_hz=completeness.M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
    )
    opener = m40.EphemeralInjectedCacheOpener(injected, bundle, runtime["grid"])
    adapter = m40.evaluate_truth_local_scores(
        plans,
        runtime["grid"],
        runtime["factor_matrices"],
        opener.open,
        expected_scan_labels=on_labels,
        expected_source_sha256s=tuple(scan.scan_sha256 for scan in injected.scans),
        window_id=m40.EXPECTED_WINDOW_ID,
    )
    if opener.open_count != 24:
        raise core.V0P6IncompleteError("M41 ephemeral cache inventory changed")
    record = make_trial_record(
        trial,
        ordinal,
        start,
        config,
        adapter,
        source_product_sha256s=background.source_product_sha256s,
        background_sha256=background.background_sha256,
        noise_shift_channels=background.noise_shift_channels,
        injected_native_sha256=injected.injected_native_sha256,
    )
    m40._publish_json(path, record)
    m40._emit(
        "m41_trial_complete",
        trial_ordinal=ordinal,
        level_index=trial.level_index,
        truth_ordinal=trial.truth.truth_ordinal,
        score_recovered=record["score_recovered"],
        elapsed_seconds=time.monotonic() - started,
        restart_hit=False,
    )
    del opener, injected, background
    gc.collect()
    return record


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
            "M41 calibration injections are not authorized; no trial executed"
        )
    shard = core._strict_int(shard_index, "M41 shard index")
    count = core._strict_int(shard_count, "M41 shard count")
    if count < 1 or count > EXPECTED_TRIAL_COUNT or not 0 <= shard < count:
        raise core.V0P6ContractError("M41 shard selection is invalid")
    config = _load_config()
    plan = make_plan()
    validate_config(config, plan)
    runtime = _runtime_context(run_root, plan)
    start = _validate_start(output_root, config, plan)
    if trial_ordinal is None:
        selected = [
            (ordinal, trial)
            for ordinal, trial in enumerate(plan.trials)
            if ordinal % count == shard
        ]
    else:
        ordinal = core._strict_int(trial_ordinal, "M41 trial ordinal")
        if not 0 <= ordinal < len(plan.trials) or ordinal % count != shard:
            raise core.V0P6ContractError("M41 trial is outside its shard")
        selected = [(ordinal, plan.trials[ordinal])]
    completed = 0
    recovered = 0
    for ordinal, trial in selected:
        record = run_trial(
            run_root, output_root, ordinal, trial, runtime, start, config
        )
        completed += 1
        recovered += int(record["score_recovered"])
    return {
        "artifact_type": "m41-shard-execution-summary-v1",
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


def _first_level(levels: Sequence[Mapping[str, Any]], target: float) -> float | None:
    for level in levels:
        if float(level["recovery_fraction"]) >= target:
            return float(level["ideal_single_epoch_snr"])
    return None


def aggregate(run_root: Path, output_root: Path) -> dict[str, Any]:
    config = _load_config()
    plan = make_plan()
    validate_config(config, plan)
    _runtime_context(run_root, plan)
    start = _validate_start(output_root, config, plan)
    expected_paths = {_trial_path(output_root, trial) for trial in plan.trials}
    present_paths = set((output_root / "trials").glob("level-*/*.json"))
    if present_paths != expected_paths:
        raise core.V0P6IncompleteError(
            "M41 ledger is incomplete or expanded: "
            f"missing={len(expected_paths - present_paths)}, "
            f"extra={len(present_paths - expected_paths)}"
        )
    records: list[dict[str, Any]] = []
    total_bytes = 0
    for ordinal, trial in enumerate(plan.trials):
        record = m40._read_canonical(_trial_path(output_root, trial))
        _validate_trial_record(record, trial, ordinal, start, config)
        total_bytes += len(core.canonical_json_bytes(record))
        if total_bytes > MAXIMUM_TOTAL_RECORD_BYTES:
            raise core.V0P6CapacityError("M41 total trial-record cap exceeded")
        records.append(record)
    ledger_payload = _gzip_jsonl(records)
    ledger_sha256 = m40._publish_bytes(output_root / LEDGER_NAME, ledger_payload)
    levels: list[dict[str, Any]] = []
    for level_index, snr in enumerate(M41_SNR_GRID):
        selected = [
            record
            for record in records
            if record["trial"]["level_index"] == level_index
        ]
        if len(selected) != EXPECTED_TRUTH_COUNT:
            raise core.V0P6IncompleteError("M41 per-level inventory changed")
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
                "truth_local_candidate_nonempty_count": sum(
                    int(record["adapter"]["candidate_score_cell_count"] > 0)
                    for record in selected
                ),
                "finite_best_score_count": len(finite_scores),
                "maximum_best_truth_local_score_snr": (
                    None if not finite_scores else max(finite_scores)
                ),
                "recovered": recovered,
                "recovery_fraction": recovered / len(selected),
                "wilson_95_low": low,
                "wilson_95_high": high,
                "record_inventory_sha256": sha256_json(
                    [record["record_sha256"] for record in selected]
                ),
            }
        )
    summary = {
        "first_tested_snr_with_any_recovery": _first_level(levels, 1 / 512),
        "first_tested_snr_at_or_above_50_percent": _first_level(levels, 0.5),
        "first_tested_snr_at_or_above_90_percent": _first_level(levels, 0.9),
        "interpolation_performed": False,
    }
    aggregate_record: dict[str, Any] = {
        "artifact_type": "m41-m37-high-snr-truth-local-calibration-aggregate-v1",
        "status": "complete",
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "start_sha256": start["start_sha256"],
        "parent_m40_v2_aggregate_sha256": M40_AGGREGATE_SHA256,
        "parent_m40_v2_ledger_sha256": M40_LEDGER_SHA256,
        "m40_score_receipts_adopted": 0,
        "plan": plan.as_record(),
        "trial_count": len(records),
        "truth_count_per_level": EXPECTED_TRUTH_COUNT,
        "snr_level_count": EXPECTED_LEVEL_COUNT,
        "recovered_trial_count": sum(
            bool(record["score_recovered"]) for record in records
        ),
        "levels": levels,
        "transition_summary": summary,
        "trial_record_inventory_sha256": sha256_json(
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
    aggregate_record["aggregate_sha256"] = sha256_json(aggregate_record)
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
        result = make_plan().as_record()
        if CONFIG_PATH.exists():
            validate_config(_load_config(), make_plan())
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
