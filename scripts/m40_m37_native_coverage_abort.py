#!/usr/bin/env python3
"""Seal the fail-closed M40 v1 native-coverage abort.

This diagnostic reads only frozen geometry/factor metadata plus already
published trial receipts.  It does not open a spectral payload, execute an
injection, or produce a calibration estimate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

M40_PATH = SCRIPTS / "m40_m37_truth_local_calibration.py"
M40_SPEC = importlib.util.spec_from_file_location("m40_v1", M40_PATH)
if M40_SPEC is None or M40_SPEC.loader is None:
    raise RuntimeError("M40 v1 implementation is unavailable")
m40 = importlib.util.module_from_spec(M40_SPEC)
M40_SPEC.loader.exec_module(m40)


AUDIT_NAME = "native-coverage-audit.json"
ABORT_NAME = "execution-abort.json"
EXPECTED_INVALID_TRUTH_ORDINALS = (
    143,
    150,
    193,
    207,
    214,
    293,
    307,
    371,
    386,
    407,
    435,
    450,
    464,
    471,
    486,
    499,
)


def _source_geometry(run_root: Path, label: str) -> dict[str, Any]:
    path = (
        run_root
        / "sources"
        / m40.EXPECTED_WINDOW_ID
        / f"{label}.product.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = value.get("normalized_product", {}).get("payload", {})
    geometry = payload.get("geometry")
    if not isinstance(geometry, dict) or set(geometry) != {
        "raw_zero_hz",
        "channel_width_hz",
        "channel_count",
    }:
        raise m40.core.V0P6ContractError(
            f"M40 source geometry is invalid: {path}"
        )
    if value.get("product_sha256") != payload.get("product_sha256", value.get("product_sha256")):
        # Older sidecars bind the product identity outside the payload.  This
        # branch rejects only an explicit disagreement.
        raise m40.core.V0P6IncompleteError("M40 source-product identity changed")
    return {
        "scan_label": label,
        "product_sha256": value["product_sha256"],
        "geometry": geometry,
    }


def _truth_coverage(
    truth: Any,
    bundle: Any,
    source_geometries: Mapping[str, Mapping[str, Any]],
    on_labels: tuple[str, ...],
) -> dict[str, Any]:
    half = int(truth.spectral_width_channels) // 2
    active = set(truth.active_epochs_zero_based)
    epochs: list[dict[str, Any]] = []
    covered = True
    for epoch, label in enumerate(on_labels):
        factors = m40.core.template_factors_from_basis(
            bundle.basis,
            {
                "coefficient_x": truth.coefficient_x,
                "coefficient_y": truth.coefficient_y,
            },
            scan_label=label,
        )
        geometry = source_geometries[label]["geometry"]
        coordinates = (
            np.float64(truth.proxy_carrier_hz) * factors
            - np.float64(geometry["raw_zero_hz"])
        ) / np.float64(geometry["channel_width_hz"])
        centers = np.rint(coordinates).astype(np.int64)
        minimum = int(np.min(centers))
        maximum = int(np.max(centers))
        epoch_covered = minimum >= half and maximum < (
            int(geometry["channel_count"]) - half
        )
        if epoch in active:
            epochs.append(
                {
                    "epoch_zero_based": epoch,
                    "scan_label": label,
                    "minimum_center_channel": minimum,
                    "maximum_center_channel": maximum,
                    "minimum_permitted_center_channel": half,
                    "maximum_permitted_center_channel": (
                        int(geometry["channel_count"]) - half - 1
                    ),
                    "covered": epoch_covered,
                }
            )
            covered = covered and epoch_covered
    return {
        "truth_ordinal": truth.truth_ordinal,
        "truth_id": truth.truth_id,
        "proxy_carrier_index": truth.proxy_carrier_index,
        "proxy_carrier_hz": truth.proxy_carrier_hz,
        "spectral_width_channels": truth.spectral_width_channels,
        "active_epochs_zero_based": list(truth.active_epochs_zero_based),
        "covered": covered,
        "active_epoch_coverage": epochs,
    }


def seal_abort(
    run_root: Path,
    trial_root: Path,
    result_root: Path,
) -> dict[str, Any]:
    config = m40._load_config()
    m40.validate_config(config)
    m40._validate_m39_qualification(config)
    start = m40._validate_start(trial_root, config)
    runtime = m40._runtime_context(run_root, config)
    trials = m40._all_trials()
    truths = tuple(trials[index].truth for index in range(m40.EXPECTED_TRUTH_COUNT))
    source_items = tuple(
        _source_geometry(run_root, label) for label in runtime["on_labels"]
    )
    source_geometries = {item["scan_label"]: item for item in source_items}
    coverage = [
        _truth_coverage(
            truth,
            runtime["bundle"],
            source_geometries,
            runtime["on_labels"],
        )
        for truth in truths
    ]
    invalid = tuple(
        item["truth_ordinal"] for item in coverage if item["covered"] is False
    )
    if invalid != EXPECTED_INVALID_TRUTH_ORDINALS:
        raise m40.core.V0P6IncompleteError(
            "M40 native-coverage failure inventory changed"
        )
    audit: dict[str, Any] = {
        "artifact_type": "m40-m37-native-coverage-audit-v1",
        "status": "failed-16-of-512-truths-outside-native-coverage",
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "start_sha256": start["start_sha256"],
        "plan_sha256": start["plan_sha256"],
        "truth_inventory_sha256": start["truth_inventory_sha256"],
        "source_geometry": list(source_items),
        "source_geometry_sha256": m40.sha256_json(list(source_items)),
        "coverage_contract": (
            "for every active epoch and integration, round((q*F-raw_zero_hz)/"
            "channel_width_hz) must leave width//2 native channels on both sides"
        ),
        "truth_count": len(coverage),
        "covered_truth_count": sum(item["covered"] for item in coverage),
        "uncovered_truth_count": len(invalid),
        "uncovered_truth_ordinals": list(invalid),
        "coverage": coverage,
        "coverage_inventory_sha256": m40.sha256_json(coverage),
        "spectral_payloads_opened": 0,
        "injections_executed_by_audit": 0,
    }
    audit["audit_sha256"] = m40.sha256_json(audit)
    result_root.mkdir(parents=True, exist_ok=True)
    m40._publish_json(result_root / AUDIT_NAME, audit)

    expected_paths = {m40._trial_path(trial_root, trial) for trial in trials}
    present_paths = set((trial_root / "trials").glob("level-*/*.json"))
    extra = present_paths - expected_paths
    if extra:
        raise m40.core.V0P6IncompleteError("M40 v1 partial ledger has extra trials")
    inventory: list[dict[str, Any]] = []
    level_counts = [0] * m40.EXPECTED_LEVEL_COUNT
    recovered = 0
    invalid_set = set(invalid)
    for ordinal, trial in enumerate(trials):
        path = m40._trial_path(trial_root, trial)
        if not path.exists():
            continue
        record = m40._read_canonical(path)
        m40._validate_trial_record(record, trial, ordinal, start, config)
        if trial.truth.truth_ordinal in invalid_set:
            raise m40.core.V0P6IncompleteError(
                "an uncovered M40 truth unexpectedly produced a trial record"
            )
        inventory.append(
            {
                "trial_ordinal": ordinal,
                "relative_path": path.relative_to(trial_root).as_posix(),
                "record_sha256": record["record_sha256"],
            }
        )
        level_counts[trial.level_index] += 1
        recovered += int(record["score_recovered"])
    abort: dict[str, Any] = {
        "artifact_type": "m40-m37-truth-local-calibration-execution-abort-v1",
        "status": "M40_V1_ABORTED_NO_CALIBRATION_CURVE",
        "failure_code": "native-truth-coverage-preflight-omission",
        "failure_message": (
            "16 frozen continuous truths leave the exact native 1412.5 MHz "
            "background in at least one active epoch"
        ),
        "source_run_id": m40.EXPECTED_RUN_ID,
        "window_id": m40.EXPECTED_WINDOW_ID,
        "start_sha256": start["start_sha256"],
        "config_sha256": start["config_sha256"],
        "runner_sha256": m40.sha256_file(M40_PATH),
        "native_coverage_audit_sha256": audit["audit_sha256"],
        "native_coverage_audit_file_sha256": m40.sha256_file(
            result_root / AUDIT_NAME
        ),
        "truth_count": m40.EXPECTED_TRUTH_COUNT,
        "covered_truth_count": len(coverage) - len(invalid),
        "uncovered_truth_count": len(invalid),
        "uncovered_truth_ordinals": list(invalid),
        "scheduled_trial_count": m40.EXPECTED_TRIAL_COUNT,
        "structurally_covered_trial_count": (
            (len(coverage) - len(invalid)) * m40.EXPECTED_LEVEL_COUNT
        ),
        "structurally_uncovered_trial_count": (
            len(invalid) * m40.EXPECTED_LEVEL_COUNT
        ),
        "completed_trial_count_before_stop": len(inventory),
        "missing_trial_count_at_stop": m40.EXPECTED_TRIAL_COUNT - len(inventory),
        "completed_trial_count_by_level": level_counts,
        "score_recovered_count_in_partial_records": recovered,
        "partial_record_inventory_sha256": m40.sha256_json(inventory),
        "partial_records_are_diagnostic_only": True,
        "calibration_aggregate_permitted": False,
        "calibration_curve_produced": False,
        "threshold_reestimated": False,
        "spectral_payloads_opened_by_abort_diagnostic": 0,
        "injections_executed_by_abort_diagnostic": 0,
        "required_continuation": (
            "new separately frozen coverage-proved protocol and output root; "
            "the v1 start, partial receipts, and abort remain immutable"
        ),
        "claim_boundary": config["claim_boundary"],
    }
    abort["abort_sha256"] = m40.sha256_json(abort)
    m40._publish_json(result_root / ABORT_NAME, abort)
    return abort


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    args = parser.parse_args()
    record = seal_abort(args.run_root, args.trial_root, args.result_root)
    print(m40.core.canonical_json_bytes(record).decode(), flush=True)


if __name__ == "__main__":
    main()
