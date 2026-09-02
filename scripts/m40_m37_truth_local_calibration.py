#!/usr/bin/env python3
"""Execute the frozen 6,144-trial M40 truth-local calibration.

The command has three fail-closed phases: publish a deterministic start
certificate before any M40 injection, execute immutable per-trial restart
records (optionally in modulo shards), and aggregate only the exact complete
ledger. Filter caches are ephemeral and exist one epoch/width at a time.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import gc
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

from seti_repeater import completeness_v0p6 as completeness
from seti_repeater import search_v0p6 as core
from seti_repeater.truth_local_v0p6 import (
    TRUTH_LOCAL_ADAPTER_STATUS,
    evaluate_truth_local_scores,
    plan_truth_local_template_scores_interval,
)


M39_PATH = SCRIPTS / "m39_m37_real_anchor_equivalence.py"
M39_SPEC = importlib.util.spec_from_file_location("m39_anchor", M39_PATH)
if M39_SPEC is None or M39_SPEC.loader is None:
    raise RuntimeError("M39 anchor implementation is unavailable")
m39 = importlib.util.module_from_spec(M39_SPEC)
M39_SPEC.loader.exec_module(m39)


CONFIG_PATH = ROOT / "config/m40_m37_truth_local_calibration.json"
START_NAME = "calibration-start.json"
AGGREGATE_NAME = "calibration-aggregate.json"
LEDGER_NAME = "trial-ledger.jsonl.gz"
EXPECTED_RUN_ID = "m37-v0p6p1-primary-006"
EXPECTED_WINDOW_ID = "m37_1412p5"
EXPECTED_TRIAL_COUNT = 6_144
EXPECTED_TRUTH_COUNT = 512
EXPECTED_LEVEL_COUNT = 12
MAXIMUM_TRIAL_RECORD_BYTES = 16_384
MAXIMUM_TOTAL_RECORD_BYTES = 128_000_000

TRIAL_RECORD_FIELDS = (
    "artifact_type",
    "status",
    "start_sha256",
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


def sha256_json(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _emit(event: str, **values: Any) -> None:
    print(
        core.canonical_json_bytes(
            {"event": event, "monotonic_seconds": time.monotonic(), **values}
        ).decode(),
        flush=True,
    )


def _publish_bytes(path: Path, payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    if path.exists():
        if path.read_bytes() != payload:
            raise core.V0P6IncompleteError(
                f"existing immutable M40 artifact differs: {path}"
            )
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while publishing M40 artifact")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise core.V0P6IncompleteError(
                f"concurrent immutable M40 artifact differs: {path}"
            )
    finally:
        temporary.unlink(missing_ok=True)
    return digest


def _publish_json(path: Path, value: Mapping[str, Any]) -> str:
    return _publish_bytes(path, core.canonical_json_bytes(dict(value)))


def _read_canonical(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(f"invalid M40 JSON: {path}") from error
    if not isinstance(value, dict) or core.canonical_json_bytes(value) != raw:
        raise core.V0P6ContractError(f"non-canonical M40 JSON: {path}")
    return value


def _load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise core.V0P6ContractError("M40 config must be an object")
    return value


def _all_trials() -> tuple[Any, ...]:
    plan = completeness.make_m37_prospective_completeness_plan()
    completeness.validate_m37_completeness_plan(plan)
    trials = tuple(completeness.iter_m37_completeness_trials(plan))
    if len(trials) != EXPECTED_TRIAL_COUNT:
        raise core.V0P6IncompleteError("M40 trial inventory count changed")
    return trials


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("artifact_type") != (
        "m40-m37-conditional-truth-local-calibration-config-v1"
    ):
        raise core.V0P6ContractError("M40 config type changed")
    if (
        config.get("status") != "execution-ready-after-m39-qualification"
        or config.get("source_run_id") != EXPECTED_RUN_ID
        or config.get("background_window") != EXPECTED_WINDOW_ID
    ):
        raise core.V0P6ContractError("M40 scope changed")
    upstream = config.get("upstream_files")
    if not isinstance(upstream, list) or len(upstream) != 7:
        raise core.V0P6IncompleteError("M40 upstream inventory changed")
    seen: set[str] = set()
    for item in upstream:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise core.V0P6ContractError("M40 upstream entry changed")
        relative = str(item["path"])
        if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise core.V0P6ContractError("M40 upstream path changed")
        seen.add(relative)
        if sha256_file(ROOT / relative) != item["sha256"]:
            raise core.V0P6IncompleteError(f"M40 upstream hash changed: {relative}")

    qualification = config.get("m39_qualification")
    if not isinstance(qualification, dict) or qualification != {
        "status": "qualification_complete_calibration_authorized",
        "certificate_sha256": (
            "68da73b539b02210ebd3923b61bace3d07158ea7fce434602be44aff98acaaa5"
        ),
        "rehydration_completion_sha256": (
            "e99da4c94f85cbebf5146b19aeea63fcfd73f68adbc5be55a183365055c39b47"
        ),
        "anchor_aggregate_sha256": (
            "504291fce04d9665c024e5de27f09b400ee0667c4e2934e6d3cc1dba39ef1fb2"
        ),
        "all_6144_calibration_trials_authorized": True,
    }:
        raise core.V0P6IncompleteError("M39 qualification gate changed")

    plan = completeness.make_m37_prospective_completeness_plan()
    frozen = config.get("frozen_trial_inventory")
    if not isinstance(frozen, dict) or frozen != {
        "truth_count": EXPECTED_TRUTH_COUNT,
        "snr_grid": list(completeness.M37_COMPLETENESS_SNR_GRID),
        "trial_count": EXPECTED_TRIAL_COUNT,
        "truth_inventory_sha256": plan.truth_inventory_sha256,
        "trial_inventory_sha256": plan.trial_inventory_sha256,
        "plan_sha256": plan.plan_sha256,
    }:
        raise core.V0P6IncompleteError("M40 frozen trial inventory changed")
    threshold = config.get("frozen_threshold")
    if not isinstance(threshold, dict) or threshold != {
        "operational_threshold_snr": 126.20158386230469,
        "threshold_certificate_sha256": (
            "d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71"
        ),
        "comparison": "finite best truth-local score >= operational threshold",
        "threshold_reestimated_after_injection": False,
    }:
        raise core.V0P6IncompleteError("M40 frozen threshold changed")
    execution = config.get("execution_contract")
    if not isinstance(execution, dict) or execution != {
        "authorization_flag": "--authorize-calibration-injections",
        "trial_order": "level-index-major-then-truth-ordinal",
        "shard_assignment": "trial-ordinal-modulo-shard-count",
        "per_trial_publication": "immutable-canonical-json",
        "cache_lifetime": "ephemeral-one-epoch-width-at-a-time",
        "two_pass_mask_recomputed": True,
        "missing_duplicate_or_extra_trial_policy": "stop-no-aggregate",
        "maximum_trial_record_canonical_bytes": MAXIMUM_TRIAL_RECORD_BYTES,
        "maximum_total_trial_record_canonical_bytes": MAXIMUM_TOTAL_RECORD_BYTES,
    }:
        raise core.V0P6IncompleteError("M40 execution contract changed")
    boundary = config.get("claim_boundary")
    if not isinstance(boundary, dict) or boundary != {
        "endpoint": "conditional-pointwise-truth-local-score-recovery",
        "interpolation_permitted": False,
        "physical_veto_survival_calibrated": False,
        "global_false_positive_field_replayed": False,
        "end_to_end_detector_completeness_claimed": False,
        "occurrence_rate_claimed": False,
        "technosignature_claimed": False,
    }:
        raise core.V0P6IncompleteError("M40 claim boundary changed")


def _validate_m39_qualification(config: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / "results_m39_m37_truth_local_qualification/qualification.json"
    qualification = _read_canonical(path)
    expected = config["m39_qualification"]
    if (
        qualification.get("status") != expected["status"]
        or qualification.get("certificate", {}).get("certificate_sha256")
        != expected["certificate_sha256"]
        or qualification.get("source_cache_readiness", {}).get(
            "rehydration_completion_sha256"
        )
        != expected["rehydration_completion_sha256"]
        or qualification.get("anchor_equivalence_readiness", {}).get(
            "aggregate_sha256"
        )
        != expected["anchor_aggregate_sha256"]
        or qualification.get("gates", {}).get(
            "all_6144_calibration_trials_authorized"
        )
        is not True
        or qualification.get("claim_boundary", {}).get(
            "injection_trials_executed"
        )
        != 0
    ):
        raise core.V0P6IncompleteError("published M39 qualification changed")
    return qualification


def _validate_m39_run(run_root: Path, config: Mapping[str, Any]) -> None:
    completion = _read_canonical(run_root / m39.rehydrate.COMPLETION)
    aggregate = _read_canonical(run_root / m39.AGGREGATE_PATH)
    expected = config["m39_qualification"]
    if (
        completion.get("status") != "complete"
        or completion.get("completion_sha256")
        != expected["rehydration_completion_sha256"]
        or completion.get("all_six_sources_verified") is not True
        or completion.get("all_48_caches_verified") is not True
        or aggregate.get("status") != "passed"
        or aggregate.get("aggregate_sha256")
        != expected["anchor_aggregate_sha256"]
        or aggregate.get("all_6144_calibration_trials_authorized") is not True
        or aggregate.get("calibration_trials_executed") != 0
    ):
        raise core.V0P6IncompleteError("local M39 execution receipts changed")


def _source_inventory() -> list[dict[str, Any]]:
    paths = (
        Path(__file__).resolve(),
        M39_PATH,
        m39.REHYDRATE_PATH,
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


def initialize(
    run_root: Path,
    output_root: Path,
    *,
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    config = _load_config(config_path)
    validate_config(config)
    qualification = _validate_m39_qualification(config)
    _validate_m39_run(run_root, config)
    plan = completeness.make_m37_prospective_completeness_plan()
    sources = _source_inventory()
    schema = {
        "artifact_type": "m40-trial-result-schema-v1",
        "canonical_top_level_fields": list(TRIAL_RECORD_FIELDS),
        "record_identity_field": "record_sha256",
        "recovery_comparison": config["frozen_threshold"]["comparison"],
    }
    record = {
        "artifact_type": "m40-m37-truth-local-calibration-start-v1",
        "status": "initialized-no-m40-injection-executed",
        "source_run_id": EXPECTED_RUN_ID,
        "window_id": EXPECTED_WINDOW_ID,
        "config_sha256": sha256_file(config_path),
        "config_canonical_sha256": sha256_json(config),
        "m39_qualification_certificate_sha256": qualification["certificate"][
            "certificate_sha256"
        ],
        "m39_rehydration_completion_sha256": config["m39_qualification"][
            "rehydration_completion_sha256"
        ],
        "m39_anchor_aggregate_sha256": config["m39_qualification"][
            "anchor_aggregate_sha256"
        ],
        "plan_sha256": plan.plan_sha256,
        "truth_inventory_sha256": plan.truth_inventory_sha256,
        "trial_inventory_sha256": plan.trial_inventory_sha256,
        "truth_count": len(plan.truths),
        "trial_count": plan.expected_trial_count,
        "snr_grid": list(completeness.M37_COMPLETENESS_SNR_GRID),
        "frozen_threshold": config["frozen_threshold"],
        "execution_contract": config["execution_contract"],
        "claim_boundary": config["claim_boundary"],
        "source_inventory": sources,
        "source_inventory_sha256": sha256_json(sources),
        "trial_result_schema": schema,
        "trial_result_schema_sha256": sha256_json(schema),
        "m40_injection_trials_executed": 0,
    }
    record["start_sha256"] = sha256_json(record)
    _publish_json(output_root / START_NAME, record)
    return record


def _validate_start(
    output_root: Path, config: Mapping[str, Any]
) -> dict[str, Any]:
    start = _read_canonical(output_root / START_NAME)
    identity = dict(start)
    observed = identity.pop("start_sha256", None)
    if observed != sha256_json(identity):
        raise core.V0P6IncompleteError("M40 start identity changed")
    current_sources = _source_inventory()
    if (
        start.get("status") != "initialized-no-m40-injection-executed"
        or start.get("source_run_id") != EXPECTED_RUN_ID
        or start.get("window_id") != EXPECTED_WINDOW_ID
        or start.get("config_sha256") != sha256_file(CONFIG_PATH)
        or start.get("config_canonical_sha256") != sha256_json(config)
        or start.get("source_inventory") != current_sources
        or start.get("source_inventory_sha256") != sha256_json(current_sources)
        or start.get("trial_count") != EXPECTED_TRIAL_COUNT
        or start.get("m40_injection_trials_executed") != 0
    ):
        raise core.V0P6IncompleteError("M40 pre-execution freeze changed")
    return start


def _frequency_axis_mhz(bundle: Any, scan_label: str) -> np.ndarray:
    definitions = [
        item for item in bundle.scans if str(item["label"]) == scan_label
    ]
    if len(definitions) != 1:
        raise core.V0P6IncompleteError("M40 scan definition changed")
    header = definitions[0]["expected_header"]
    start, stop = m39.rehydrate.source.m37_extraction_interval(
        EXPECTED_WINDOW_ID
    )
    frequency = np.ascontiguousarray(
        (
            float(header["fch1_mhz"])
            + np.arange(start, stop, dtype="<f8") * float(header["foff_mhz"])
        )[::-1],
        dtype="<f8",
    )
    frequency.setflags(write=False)
    return frequency


class EphemeralInjectedCacheOpener:
    """Build exactly one in-memory injected epoch/width cache per open."""

    def __init__(self, injected: Any, bundle: Any, grid: Any) -> None:
        self.injected = injected
        self.bundle = bundle
        self.grid = grid
        self.frequency = {
            scan.scan_label: _frequency_axis_mhz(bundle, scan.scan_label)
            for scan in injected.scans
        }
        self.open_count = 0

    @contextmanager
    def open(self, epoch: int, width: int):
        epoch_index = core._strict_int(epoch, "M40 cache epoch")
        if epoch_index not in (0, 1, 2):
            raise core.V0P6ContractError("M40 cache epoch changed")
        width_value = core._strict_widths((width,))[0]
        if width_value not in core.M37_SPECTRAL_WIDTHS:
            raise core.V0P6ContractError("M40 cache width changed")
        scan = self.injected.scans[epoch_index]
        plan = core.plan_m37_native_filter_cache(
            scan.geometry,
            self.bundle.basis,
            self.bundle.table,
            self.bundle.scans,
            self.grid,
            width_value,
            window_id=EXPECTED_WINDOW_ID,
            scan_label=scan.scan_label,
            source_sha256=scan.scan_sha256,
        )
        cache = core.build_native_filter_cache(
            scan.normalized, self.frequency[scan.scan_label], plan
        )
        self.open_count += 1
        try:
            yield cache
        finally:
            del cache


def _runtime_context(run_root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    _validate_m39_run(run_root, config)
    bundle = m39.rehydrate.open_bundle(run_root)
    on_labels = ("epoch1_on", "epoch2_on", "epoch3_on")
    product_sha256s, extraction_sha256s = m39._source_receipts(
        run_root, on_labels
    )
    factor_matrices = tuple(
        np.ascontiguousarray(
            core.factor_table_for_scan(bundle.table, bundle.basis, label),
            dtype="<f8",
        )
        for label in on_labels
    )
    return {
        "bundle": bundle,
        "on_labels": on_labels,
        "product_sha256s": product_sha256s,
        "extraction_sha256s": extraction_sha256s,
        "grid": core.make_m37_proxy_carrier_grid(EXPECTED_WINDOW_ID),
        "factor_matrices": factor_matrices,
        "distance_matrix": np.ascontiguousarray(
            np.concatenate(factor_matrices, axis=1), dtype="<f8"
        ),
    }


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
        raise core.V0P6IncompleteError("M40 trial record schema changed")
    identity = dict(record)
    observed = identity.pop("record_sha256", None)
    if observed != sha256_json(identity):
        raise core.V0P6IncompleteError("M40 trial record identity changed")
    if len(core.canonical_json_bytes(record)) > MAXIMUM_TRIAL_RECORD_BYTES:
        raise core.V0P6CapacityError("M40 trial record byte cap exceeded")
    adapter = record.get("adapter")
    if not isinstance(adapter, dict):
        raise core.V0P6ContractError("M40 adapter result is missing")
    adapter_identity = dict(adapter)
    adapter_sha = adapter_identity.pop("result_sha256", None)
    if adapter_sha != sha256_json(adapter_identity):
        raise core.V0P6IncompleteError("M40 adapter result identity changed")
    boundary = config["claim_boundary"]
    if (
        record.get("artifact_type")
        != "m40-m37-conditional-truth-local-trial-result-v1"
        or record.get("status") != "complete"
        or record.get("start_sha256") != start["start_sha256"]
        or record.get("source_run_id") != EXPECTED_RUN_ID
        or record.get("window_id") != EXPECTED_WINDOW_ID
        or record.get("trial_ordinal") != ordinal
        or record.get("trial") != trial.as_record()
        or record.get("truth") != trial.truth.as_record()
        or record.get("threshold") != config["frozen_threshold"]
        or record.get("claim_boundary") != boundary
        or record.get("score_recovered")
        is not _score_recovered(
            adapter, config["frozen_threshold"]["operational_threshold_snr"]
        )
        or adapter.get("status") != TRUTH_LOCAL_ADAPTER_STATUS
        or adapter.get("window_id") != EXPECTED_WINDOW_ID
        or adapter.get("template_count") != core.M37_TEMPLATE_COUNT
        or adapter.get("cache_count") != 24
        or adapter.get("two_pass_mask_recomputed") is not True
        or adapter.get("global_false_positive_field_replayed") is not False
        or adapter.get("physical_veto_survival_calibrated") is not False
        or adapter.get("production_equivalence_proven") is not False
    ):
        raise core.V0P6IncompleteError("M40 trial record content changed")


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
        core._frozen_sha256(item, "M40 source product identity")
        for item in source_product_sha256s
    ]
    shifts = [
        core._strict_int(item, "M40 native noise shift")
        for item in noise_shift_channels
    ]
    if len(sources) != 3 or len(shifts) != 3 or any(item < 0 for item in shifts):
        raise core.V0P6IncompleteError("M40 source/noise inventory changed")
    adapter_record = json.loads(core.canonical_json_bytes(dict(adapter)))
    record = {
        "artifact_type": "m40-m37-conditional-truth-local-trial-result-v1",
        "status": "complete",
        "start_sha256": core._frozen_sha256(
            start["start_sha256"], "M40 start identity"
        ),
        "source_run_id": EXPECTED_RUN_ID,
        "window_id": EXPECTED_WINDOW_ID,
        "trial_ordinal": core._strict_int(ordinal, "M40 trial ordinal"),
        "trial": trial.as_record(),
        "truth": trial.truth.as_record(),
        "source_product_sha256s": sources,
        "background_sha256": core._frozen_sha256(
            background_sha256, "M40 background identity"
        ),
        "noise_shift_channels": shifts,
        "injected_native_sha256": core._frozen_sha256(
            injected_native_sha256, "M40 injected identity"
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
        record = _read_canonical(path)
        _validate_trial_record(record, trial, ordinal, start, config)
        _emit("m40_trial_complete", trial_ordinal=ordinal, restart_hit=True)
        return record
    started = time.monotonic()
    bundle = runtime["bundle"]
    on_labels = runtime["on_labels"]
    background = completeness.seal_m37_native_trial_background(
        trial,
        m39._product_stream(run_root, bundle.scans, on_labels),
        factor_basis=bundle.basis,
        factor_table=bundle.table,
        expected_product_sha256s=runtime["product_sha256s"],
        expected_extraction_receipt_sha256s=runtime["extraction_sha256s"],
        context={
            "milestone": 40,
            "trial_ordinal": ordinal,
            "start_sha256": start["start_sha256"],
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
    plans = plan_truth_local_template_scores_interval(
        runtime["grid"],
        runtime["distance_matrix"],
        trial.truth.proxy_carrier_hz,
        truth_factors,
        tolerance_hz=completeness.M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
    )
    opener = EphemeralInjectedCacheOpener(injected, bundle, runtime["grid"])
    adapter = evaluate_truth_local_scores(
        plans,
        runtime["grid"],
        runtime["factor_matrices"],
        opener.open,
        expected_scan_labels=on_labels,
        expected_source_sha256s=tuple(
            scan.scan_sha256 for scan in injected.scans
        ),
        window_id=EXPECTED_WINDOW_ID,
    )
    if opener.open_count != 24:
        raise core.V0P6IncompleteError("M40 ephemeral cache inventory changed")
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
    _publish_json(path, record)
    _emit(
        "m40_trial_complete",
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
            "M40 calibration injections are not authorized; no trial executed"
        )
    shard = core._strict_int(shard_index, "M40 shard index")
    count = core._strict_int(shard_count, "M40 shard count")
    if count < 1 or count > EXPECTED_TRIAL_COUNT or not 0 <= shard < count:
        raise core.V0P6ContractError("M40 shard selection is invalid")
    config = _load_config()
    validate_config(config)
    _validate_m39_qualification(config)
    start = _validate_start(output_root, config)
    trials = _all_trials()
    if trial_ordinal is None:
        selected = [
            (ordinal, trial)
            for ordinal, trial in enumerate(trials)
            if ordinal % count == shard
        ]
    else:
        ordinal = core._strict_int(trial_ordinal, "M40 trial ordinal")
        if not 0 <= ordinal < len(trials):
            raise core.V0P6ContractError("M40 trial ordinal is invalid")
        if ordinal % count != shard:
            raise core.V0P6ContractError("M40 trial is outside its shard")
        selected = [(ordinal, trials[ordinal])]
    runtime = _runtime_context(run_root, config)
    completed = 0
    recovered = 0
    for ordinal, trial in selected:
        record = run_trial(
            run_root, output_root, ordinal, trial, runtime, start, config
        )
        completed += 1
        recovered += int(record["score_recovered"])
    return {
        "artifact_type": "m40-shard-execution-summary-v1",
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


def aggregate(output_root: Path) -> dict[str, Any]:
    config = _load_config()
    validate_config(config)
    _validate_m39_qualification(config)
    start = _validate_start(output_root, config)
    trials = _all_trials()
    expected_paths = {
        _trial_path(output_root, trial) for trial in trials
    }
    present_paths = set((output_root / "trials").glob("level-*/*.json"))
    if present_paths != expected_paths:
        missing = len(expected_paths - present_paths)
        extra = len(present_paths - expected_paths)
        raise core.V0P6IncompleteError(
            f"M40 ledger is incomplete or expanded: missing={missing}, extra={extra}"
        )
    records: list[dict[str, Any]] = []
    total_bytes = 0
    for ordinal, trial in enumerate(trials):
        record = _read_canonical(_trial_path(output_root, trial))
        _validate_trial_record(record, trial, ordinal, start, config)
        total_bytes += len(core.canonical_json_bytes(record))
        if total_bytes > MAXIMUM_TOTAL_RECORD_BYTES:
            raise core.V0P6CapacityError("M40 total trial-record cap exceeded")
        records.append(record)
    ledger_payload = _gzip_jsonl(records)
    ledger_sha256 = _publish_bytes(output_root / LEDGER_NAME, ledger_payload)
    levels = []
    for level_index, snr in enumerate(completeness.M37_COMPLETENESS_SNR_GRID):
        selected = [
            record
            for record in records
            if record["trial"]["level_index"] == level_index
        ]
        if len(selected) != EXPECTED_TRUTH_COUNT:
            raise core.V0P6IncompleteError("M40 per-level inventory changed")
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
                "record_inventory_sha256": sha256_json(
                    [record["record_sha256"] for record in selected]
                ),
            }
        )
    aggregate_record = {
        "artifact_type": "m40-m37-conditional-truth-local-calibration-aggregate-v1",
        "status": "complete",
        "source_run_id": EXPECTED_RUN_ID,
        "window_id": EXPECTED_WINDOW_ID,
        "start_sha256": start["start_sha256"],
        "trial_count": len(records),
        "truth_count_per_level": EXPECTED_TRUTH_COUNT,
        "snr_level_count": EXPECTED_LEVEL_COUNT,
        "recovered_trial_count": sum(
            bool(record["score_recovered"]) for record in records
        ),
        "levels": levels,
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
    _publish_json(output_root / AGGREGATE_NAME, aggregate_record)
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
    parser.add_argument("--authorize-calibration-injections", action="store_true")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    arguments = parser.parse_args()
    run_root = arguments.run_root.resolve()
    output_root = arguments.output_root.resolve()
    if arguments.initialize:
        result = initialize(run_root, output_root)
    elif arguments.aggregate:
        result = aggregate(output_root)
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
