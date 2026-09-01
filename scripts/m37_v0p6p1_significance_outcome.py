#!/usr/bin/env python3
"""Restartable rank-p and final-outcome continuation for M37 Run 006."""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import m37_v0p6_primary as primary
import m37_v0p6p1_physical_disposition as physical_runner
from seti_repeater import capacity_v0p6p1 as capacity
from seti_repeater import null_artifact_v0p6 as null_artifact
from seti_repeater import outcome_v0p6p1 as outcome
from seti_repeater import physical_v0p6p1 as physical
from seti_repeater import search_v0p6 as core
from seti_repeater import significance_v0p6p1 as significance


SIGNIFICANCE_DIRECTORY = "significance"
SIGNIFICANCE_MANIFEST_PATH = "significance-manifest.json"
OUTCOME_PATH = "outcome.json"
PHYSICAL_MANIFEST_PATH = "physical-disposition-manifest.json"


def _sha256(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def _physical_manifest(
    run_root: Path, record: Mapping[str, Any]
) -> dict[str, Any]:
    receipt = record["artifacts"].get("physical_disposition")
    if not isinstance(receipt, Mapping):
        raise core.V0P6IncompleteError(
            "physical-disposition controller receipt is absent"
        )
    path = run_root / PHYSICAL_MANIFEST_PATH
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["file_sha256"]:
        raise core.V0P6IncompleteError(
            "physical-disposition manifest file identity changed"
        )
    manifest = primary._read_canonical(path)
    payload = dict(manifest)
    observed = payload.pop("manifest_sha256")
    if (
        _sha256(payload) != observed
        or observed != receipt["manifest_sha256"]
        or manifest["run_id"] != record["run_id"]
        or manifest["window_ids"] != list(core.M37_WINDOW_IDS)
        or manifest["window_count"] != len(core.M37_WINDOW_IDS)
        or manifest["total_final_record_count"] != 43_883
        or manifest["disposition_artifact_inventory_sha256"]
        != receipt["disposition_artifact_inventory_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "physical-disposition manifest ancestry changed"
        )
    return manifest


def _global_null(
    run_root: Path, record: Mapping[str, Any]
) -> null_artifact.GlobalNullArtifact:
    receipt = record["artifacts"].get("global_null")
    if not isinstance(receipt, Mapping):
        raise core.V0P6IncompleteError("global-null receipt is absent")
    return null_artifact.open_global_null_artifact(
        run_root / primary.GLOBAL_NULL_PATH,
        expected_file_sha256=receipt["file_sha256"],
        expected_threshold_certificate_sha256=receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )


def _physical_child(
    run_root: Path,
    record: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    opened = physical.open_m37_v0p6p1_physical_disposition_artifact(
        run_root / entry["relative_path"],
        profile,
        expected_file_sha256=entry["artifact_file_sha256"],
        expected_physical_disposition_certificate_sha256=entry[
            "physical_disposition_certificate_sha256"
        ],
        expected_run_id=record["run_id"],
        expected_window_id=entry["window_id"],
        expected_cache_run_manifest_file_sha256=record["artifacts"][
            "cache_manifest"
        ]["file_sha256"],
        expected_factor_bundle_manifest_sha256=record["bootstrap"][
            "factor_bundle_manifest_sha256"
        ],
        expected_on_retention_certificate_sha256=entry[
            "on_retention_certificate_sha256"
        ],
    )
    return opened.result["receiver_alias_result"]


def _existing_significance_expectations(path: Path) -> tuple[str, str]:
    raw = significance._read_artifact_bytes(
        path,
        capacity.open_m37_v0p6p1_capacity_amendment(
            primary.CAPACITY_AMENDMENT_PATH
        ),
    )
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            "existing significance child is invalid JSON"
        ) from error
    if core.canonical_json_bytes(result) != raw:
        raise core.V0P6ContractError(
            "existing significance child is not canonical JSON"
        )
    return hashlib.sha256(raw).hexdigest(), str(result["result_sha256"])


def _significance_child(
    run_root: Path,
    record: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    global_null: null_artifact.GlobalNullArtifact,
    window_id: str,
) -> significance.M37V0P6P1SignificanceArtifact:
    on_records, on_certificate = physical_runner._load_retention(
        run_root, record, window_id, "on", profile
    )
    on_certificate_sha256 = on_certificate["retention_certificate_sha256"]
    threshold_sha256 = global_null.threshold.certificate_sha256
    grid = core.make_m37_proxy_carrier_grid(window_id)
    path = run_root / SIGNIFICANCE_DIRECTORY / f"{window_id}.json"
    if path.exists() or Path(f"{path}.gz").exists():
        expected_file_sha256, expected_result_sha256 = (
            _existing_significance_expectations(path)
        )
        opened = significance.open_m37_v0p6p1_significance_artifact(
            path,
            profile,
            on_records,
            on_certificate,
            global_null.threshold,
            global_null.values,
            grid,
            expected_file_sha256=expected_file_sha256,
            expected_on_certificate_sha256=on_certificate_sha256,
            expected_threshold_certificate_sha256=threshold_sha256,
            expected_result_sha256=expected_result_sha256,
        )
    else:
        result = significance.evaluate_m37_v0p6p1_global_rank_significance(
            profile,
            on_records,
            on_certificate,
            global_null.threshold,
            global_null.values,
            grid,
            expected_on_certificate_sha256=on_certificate_sha256,
            expected_threshold_certificate_sha256=threshold_sha256,
        )
        receipt = significance.publish_m37_v0p6p1_significance_artifact(
            path,
            result,
            profile,
            on_records,
            on_certificate,
            global_null.threshold,
            global_null.values,
            grid,
            expected_on_certificate_sha256=on_certificate_sha256,
            expected_threshold_certificate_sha256=threshold_sha256,
            expected_result_sha256=result["result_sha256"],
        )
        opened = significance.open_m37_v0p6p1_significance_artifact(
            path,
            profile,
            on_records,
            on_certificate,
            global_null.threshold,
            global_null.values,
            grid,
            expected_file_sha256=receipt.file_sha256,
            expected_on_certificate_sha256=on_certificate_sha256,
            expected_threshold_certificate_sha256=threshold_sha256,
            expected_result_sha256=receipt.result_sha256,
        )
    del on_records, on_certificate
    gc.collect()
    return opened


def _significance_entry(
    opened: significance.M37V0P6P1SignificanceArtifact,
) -> dict[str, Any]:
    receipt = opened.receipt
    rank_counts = Counter(
        str(item["inclusive_null_exceedance_count"])
        for item in opened.result["evidence"]
    )
    return {
        "window_id": receipt.window_id,
        "relative_path": f"{SIGNIFICANCE_DIRECTORY}/{receipt.window_id}.json",
        "artifact_file_sha256": receipt.file_sha256,
        "artifact_file_nbytes": receipt.file_nbytes,
        "result_sha256": receipt.result_sha256,
        "significance_certificate_sha256": (
            receipt.significance_certificate_sha256
        ),
        "retention_certificate_sha256": (
            receipt.retention_certificate_sha256
        ),
        "threshold_certificate_sha256": (
            receipt.threshold_certificate_sha256
        ),
        "record_count": receipt.record_count,
        "scientifically_eligible_count": (
            receipt.scientifically_eligible_count
        ),
        "evidence_canonical_bytes": receipt.evidence_canonical_bytes,
        "inclusive_null_exceedance_counts": dict(sorted(rank_counts.items())),
    }


def _seal_significance_manifest(
    record: Mapping[str, Any],
    physical_manifest: Mapping[str, Any],
    global_null: null_artifact.GlobalNullArtifact,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    if [entry["window_id"] for entry in entries] != list(core.M37_WINDOW_IDS):
        raise core.V0P6IncompleteError(
            "significance children are missing or reordered"
        )
    rank_counts: Counter[str] = Counter()
    for entry in entries:
        rank_counts.update(entry["inclusive_null_exceedance_counts"])
    payload = {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6p1-significance-manifest-v1",
        "run_id": record["run_id"],
        "capacity_amendment_file_sha256": record["capacity_amendment"][
            "amendment_file_sha256"
        ],
        "physical_disposition_manifest_file_sha256": record["artifacts"][
            "physical_disposition"
        ]["file_sha256"],
        "physical_disposition_manifest_sha256": physical_manifest[
            "manifest_sha256"
        ],
        "physical_disposition_artifact_inventory_sha256": physical_manifest[
            "disposition_artifact_inventory_sha256"
        ],
        "threshold_certificate_sha256": (
            global_null.threshold.certificate_sha256
        ),
        "global_null_maxima_sha256": (
            global_null.threshold.global_null_maxima_sha256
        ),
        "window_ids": list(core.M37_WINDOW_IDS),
        "window_count": len(entries),
        "entries": entries,
        "significance_artifact_inventory_sha256": _sha256(entries),
        "total_record_count": sum(item["record_count"] for item in entries),
        "total_scientifically_eligible_count": sum(
            item["scientifically_eligible_count"] for item in entries
        ),
        "total_evidence_canonical_bytes": sum(
            item["evidence_canonical_bytes"] for item in entries
        ),
        "inclusive_null_exceedance_counts": dict(sorted(rank_counts.items())),
        "all_retained_on_records_evaluated_exactly_once": True,
        "truncation_permitted": False,
    }
    manifest = dict(payload)
    manifest["manifest_sha256"] = _sha256(payload)
    return manifest


def complete_significance(
    run_root: Path,
    record: dict[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    physical_manifest: Mapping[str, Any],
    global_null: null_artifact.GlobalNullArtifact,
) -> tuple[dict[str, Any], dict[str, Any]]:
    (run_root / SIGNIFICANCE_DIRECTORY).mkdir(exist_ok=True)
    entries: list[dict[str, Any]] = []
    for window_id in core.M37_WINDOW_IDS:
        opened = _significance_child(
            run_root, record, profile, global_null, window_id
        )
        entries.append(_significance_entry(opened))
        primary._emit_progress(
            "significance_window_complete",
            window_id=window_id,
            record_count=opened.receipt.record_count,
            scientifically_eligible_count=(
                opened.receipt.scientifically_eligible_count
            ),
        )
        del opened
        gc.collect()
    manifest = _seal_significance_manifest(
        record, physical_manifest, global_null, entries
    )
    path = run_root / SIGNIFICANCE_MANIFEST_PATH
    file_sha256 = primary._publish_or_verify(path, manifest)
    reopened = primary._read_canonical(path)
    if reopened != manifest or hashlib.sha256(path.read_bytes()).hexdigest() != (
        file_sha256
    ):
        raise core.V0P6IncompleteError(
            "significance manifest failed immutable reopening"
        )
    manifest_receipt = {
        "file_sha256": file_sha256,
        "manifest_sha256": manifest["manifest_sha256"],
        "significance_artifact_inventory_sha256": manifest[
            "significance_artifact_inventory_sha256"
        ],
        "threshold_certificate_sha256": manifest[
            "threshold_certificate_sha256"
        ],
        "total_record_count": manifest["total_record_count"],
        "total_scientifically_eligible_count": manifest[
            "total_scientifically_eligible_count"
        ],
        "total_evidence_canonical_bytes": manifest[
            "total_evidence_canonical_bytes"
        ],
        "window_count": manifest["window_count"],
    }
    if record["stage"] == "physical_disposition_complete":
        record = primary._advance(
            run_root,
            record,
            stage="significance_complete",
            artifact_sha256=file_sha256,
            metadata={
                "capacity_amendment_file_sha256": (
                    profile.amendment_file_sha256
                ),
                "significance_manifest_sha256": manifest[
                    "manifest_sha256"
                ],
                "significance_artifact_inventory_sha256": manifest[
                    "significance_artifact_inventory_sha256"
                ],
                "threshold_certificate_sha256": manifest[
                    "threshold_certificate_sha256"
                ],
                "global_null_maxima_sha256": manifest[
                    "global_null_maxima_sha256"
                ],
                "window_count": manifest["window_count"],
                "total_record_count": manifest["total_record_count"],
                "total_scientifically_eligible_count": manifest[
                    "total_scientifically_eligible_count"
                ],
            },
        )
        artifacts = dict(record["artifacts"])
        artifacts["significance"] = manifest_receipt
        record["artifacts"] = artifacts
        primary._write_controller(run_root, record)
    else:
        expected = record["artifacts"].get("significance")
        if expected != manifest_receipt:
            raise core.V0P6IncompleteError(
                "controller significance receipt changed"
            )
    return record, manifest


def _significance_for_outcome(
    run_root: Path,
    record: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    global_null: null_artifact.GlobalNullArtifact,
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    window_id = entry["window_id"]
    on_records, on_certificate = physical_runner._load_retention(
        run_root, record, window_id, "on", profile
    )
    opened = significance.open_m37_v0p6p1_significance_artifact(
        run_root / entry["relative_path"],
        profile,
        on_records,
        on_certificate,
        global_null.threshold,
        global_null.values,
        core.make_m37_proxy_carrier_grid(window_id),
        expected_file_sha256=entry["artifact_file_sha256"],
        expected_on_certificate_sha256=entry[
            "retention_certificate_sha256"
        ],
        expected_threshold_certificate_sha256=entry[
            "threshold_certificate_sha256"
        ],
        expected_result_sha256=entry["result_sha256"],
    )
    del on_records, on_certificate
    gc.collect()
    return opened.result


def complete_outcome(
    run_root: Path,
    record: dict[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    physical_manifest: Mapping[str, Any],
    significance_manifest: Mapping[str, Any],
    global_null: null_artifact.GlobalNullArtifact,
) -> tuple[dict[str, Any], outcome.M37V0P6P1OutcomeArtifact]:
    physical_by_window = {
        item["window_id"]: item for item in physical_manifest["entries"]
    }
    significance_by_window = {
        item["window_id"]: item for item in significance_manifest["entries"]
    }
    window_inputs: list[dict[str, Any]] = []
    for window_id in core.M37_WINDOW_IDS:
        physical_entry = physical_by_window[window_id]
        significance_entry = significance_by_window[window_id]
        alias_result = _physical_child(
            run_root, record, profile, physical_entry
        )
        significance_result = _significance_for_outcome(
            run_root, record, profile, global_null, significance_entry
        )
        window_inputs.append(
            {
                "window_id": window_id,
                "alias_result": alias_result,
                "significance_result": significance_result,
                "expected_alias_certificate_sha256": physical_entry[
                    "receiver_alias_certificate_sha256"
                ],
                "expected_significance_result_sha256": significance_entry[
                    "result_sha256"
                ],
                "expected_retention_certificate_sha256": physical_entry[
                    "on_retention_certificate_sha256"
                ],
            }
        )
        primary._emit_progress(
            "outcome_window_inputs_reopened",
            window_id=window_id,
            record_count=significance_entry["record_count"],
        )
        gc.collect()
    path = run_root / OUTCOME_PATH
    result = outcome.assemble_m37_v0p6p1_outcome(
        profile,
        window_inputs,
        expected_threshold_certificate_sha256=(
            global_null.threshold.certificate_sha256
        ),
    )
    if path.exists() or Path(f"{path}.gz").exists():
        raw = outcome._read_artifact_bytes(path, profile)
        if raw != core.canonical_json_bytes(result):
            raise core.V0P6IncompleteError(
                "existing outcome does not reproduce from upstream receipts"
            )
        opened = outcome.open_m37_v0p6p1_outcome_artifact(
            path,
            profile,
            expected_file_sha256=hashlib.sha256(raw).hexdigest(),
            expected_result_sha256=result["result_sha256"],
        )
    else:
        receipt = outcome.publish_m37_v0p6p1_outcome_artifact(
            path,
            result,
            profile,
            expected_result_sha256=result["result_sha256"],
        )
        opened = outcome.open_m37_v0p6p1_outcome_artifact(
            path,
            profile,
            expected_file_sha256=receipt.file_sha256,
            expected_result_sha256=receipt.result_sha256,
        )
    receipt_record = {
        key: value
        for key, value in opened.receipt.__dict__.items()
        if key != "path"
    }
    receipt_record["path"] = OUTCOME_PATH
    if record["stage"] == "significance_complete":
        record = primary._advance(
            run_root,
            record,
            stage="outcome_complete",
            artifact_sha256=opened.receipt.file_sha256,
            metadata={
                "capacity_amendment_file_sha256": (
                    profile.amendment_file_sha256
                ),
                "outcome_result_sha256": opened.receipt.result_sha256,
                "outcome_certificate_sha256": (
                    opened.receipt.outcome_certificate_sha256
                ),
                "threshold_certificate_sha256": (
                    opened.receipt.threshold_certificate_sha256
                ),
                "outcome_record_count": opened.receipt.outcome_record_count,
                "unresolved_candidate_count": (
                    opened.receipt.unresolved_candidate_count
                ),
                "global_search_state": opened.receipt.global_search_state,
                "global_outcome": opened.receipt.global_outcome,
            },
        )
        artifacts = dict(record["artifacts"])
        artifacts["outcome"] = receipt_record
        record["artifacts"] = artifacts
        primary._write_controller(run_root, record)
    else:
        expected = record["artifacts"].get("outcome")
        if expected != receipt_record:
            raise core.V0P6IncompleteError("controller outcome receipt changed")
    return record, opened


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    record = primary._status(args.run_root)
    if record["stage"] not in {
        "physical_disposition_complete",
        "significance_complete",
        "outcome_complete",
    }:
        raise core.V0P6IncompleteError(
            "significance/outcome requires complete physical disposition"
        )
    profile = capacity.validate_m37_v0p6p1_capacity_profile_record(
        record["capacity_amendment"]
    )
    physical_manifest = _physical_manifest(args.run_root, record)
    global_null = _global_null(args.run_root, record)
    record, significance_manifest = complete_significance(
        args.run_root,
        record,
        profile,
        physical_manifest,
        global_null,
    )
    record, opened = complete_outcome(
        args.run_root,
        record,
        profile,
        physical_manifest,
        significance_manifest,
        global_null,
    )
    print(core.canonical_json_bytes(primary._status(args.run_root)).decode())
    primary._emit_progress(
        "outcome_complete",
        global_outcome=opened.receipt.global_outcome,
        unresolved_candidate_count=opened.receipt.unresolved_candidate_count,
        outcome_record_count=opened.receipt.outcome_record_count,
    )


if __name__ == "__main__":
    main()
