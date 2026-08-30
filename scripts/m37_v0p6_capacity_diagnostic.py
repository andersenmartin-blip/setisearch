#!/usr/bin/env python3
"""Reproduce and seal the first M37 retention-capacity overflow."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

import m37_v0p6_primary as primary
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import null_artifact_v0p6 as null_artifact
from seti_repeater import run_state_v0p6 as state
from seti_repeater import search_v0p6 as core


def _open_global_null(root: Path, record: dict[str, Any]):
    receipt = record["artifacts"]["global_null"]
    return null_artifact.open_global_null_artifact(
        root / primary.GLOBAL_NULL_PATH,
        expected_file_sha256=receipt["file_sha256"],
        expected_threshold_certificate_sha256=receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )


def diagnose(root: Path, window_id: str, kind: str) -> dict[str, Any]:
    record = primary._status(root)
    if record["stage"] != "threshold_complete":
        raise core.V0P6IncompleteError(
            "capacity diagnostic requires the threshold-complete run"
        )
    bundle = primary._bundle(root, record)
    manifest = primary._open_manifest(root, record, bundle)
    global_null = _open_global_null(root, record)
    validator = native_cache.NativeFilterCacheValidationCache()
    threshold = global_null.threshold.operational_threshold_snr
    retained_count = 0
    hypotheses_complete = 0

    for template_index, template in enumerate(bundle.template_bank):
        products, mask = primary._template_products(
            root,
            manifest,
            bundle,
            validator,
            window_id=window_id,
            kind=kind,
            template_index=template_index,
        )
        try:
            for width_index, width in enumerate(core.M37_SPECTRAL_WIDTHS):
                for subset in core.M37_ACTIVITY_SUBSETS:
                    score = core.stack_hypothesis(
                        products[width].values,
                        subset,
                        minimum_active_epoch_snr=(
                            core.M37_MINIMUM_ACTIVE_EPOCH_SNR
                        ),
                        stack_statistic="minimum_epoch",
                        exclusion_mask=mask.values,
                    )
                    eligible = np.flatnonzero(
                        np.isfinite(score) & (score >= threshold)
                    )
                    hypothesis_count = int(eligible.size)
                    cumulative = retained_count + hypothesis_count
                    if cumulative > core.M37_MAXIMUM_RECORDS_PER_WINDOW:
                        basis = {
                            "artifact_type": (
                                "m37-detector-v0p6-retention-capacity-failure-v1"
                            ),
                            "run_id": record["run_id"],
                            "window_id": window_id,
                            "scan_kind": kind,
                            "failure_outcome": "M37_INVALID_NO_CONCLUSION",
                            "failure_message": (
                                "above-threshold retention exceeds the frozen "
                                "per-window capacity"
                            ),
                            "truncation_permitted": False,
                            "threshold_adaptation_permitted": False,
                            "operational_threshold_snr": threshold,
                            "maximum_records_per_window": (
                                core.M37_MAXIMUM_RECORDS_PER_WINDOW
                            ),
                            "records_before_failing_hypothesis": retained_count,
                            "records_in_failing_hypothesis": hypothesis_count,
                            "cumulative_record_lower_bound": cumulative,
                            "first_failing_hypothesis": {
                                "template_index": template_index,
                                "line_index": int(template["line_index"]),
                                "width_index": width_index,
                                "width_channels": width,
                                "active_epochs_zero_based": list(subset),
                            },
                            "hypotheses_complete_before_failure": (
                                hypotheses_complete
                            ),
                            "score_cells_examined_through_failure": (
                                (hypotheses_complete + 1)
                                * core.make_m37_proxy_carrier_grid(
                                    window_id
                                ).score_bin_count
                            ),
                            "failing_hypothesis_maximum_snr": float(
                                np.nanmax(score)
                            ),
                            "threshold_certificate_sha256": (
                                global_null.threshold.certificate_sha256
                            ),
                            "global_null_file_sha256": (
                                global_null.receipt.file_sha256
                            ),
                            "cache_run_manifest_file_sha256": record[
                                "artifacts"
                            ]["cache_manifest"]["file_sha256"],
                            "factor_bundle_manifest_sha256": (
                                bundle.receipt.manifest_sha256
                            ),
                            "diagnostic_orchestrator_sha256": hashlib.sha256(
                                Path(__file__).read_bytes()
                            ).hexdigest(),
                            "proxy_grid_sha256": core.proxy_carrier_grid_sha256(
                                core.make_m37_proxy_carrier_grid(window_id)
                            ),
                        }
                        basis["evidence_sha256"] = hashlib.sha256(
                            core.canonical_json_bytes(basis)
                        ).hexdigest()
                        path = root / "retention-capacity-failure.json"
                        file_sha256 = primary._publish_or_verify(path, basis)
                        return {
                            "evidence": basis,
                            "file_sha256": file_sha256,
                            "path": path,
                        }
                    retained_count = cumulative
                    hypotheses_complete += 1
        finally:
            del products, mask
    raise core.V0P6IncompleteError(
        "capacity diagnostic did not reproduce the production overflow"
    )


def invalidate(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    record = primary._status(root)
    evidence = result["evidence"]
    journal = state.invalidate_m37_run_journal(
        root / "run.journal.jsonl",
        expected_head_sha256=record["journal_head_sha256"],
        evidence_sha256=result["file_sha256"],
        reason_code="retention-capacity-overflow",
        metadata={
            "spectral_access_authorized": True,
            "spectral_dataset_values_read": True,
            "failure_outcome": evidence["failure_outcome"],
            "window_id": evidence["window_id"],
            "scan_kind": evidence["scan_kind"],
            "maximum_records_per_window": evidence[
                "maximum_records_per_window"
            ],
            "cumulative_record_lower_bound": evidence[
                "cumulative_record_lower_bound"
            ],
        },
    )
    updated = dict(record)
    updated["stage"] = journal.stage
    updated["journal_head_sha256"] = journal.head_sha256
    artifacts = dict(updated["artifacts"])
    artifacts["retention_capacity_failure"] = {
        "file_sha256": result["file_sha256"],
        "evidence_sha256": evidence["evidence_sha256"],
        "failure_outcome": evidence["failure_outcome"],
    }
    updated["artifacts"] = artifacts
    primary._write_controller(root, updated)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--window-id", default="m37_1418p5")
    parser.add_argument("--scan-kind", choices=("on", "off"), default="on")
    parser.add_argument("--invalidate", action="store_true")
    args = parser.parse_args()
    result = diagnose(args.run_root, args.window_id, args.scan_kind)
    output = invalidate(args.run_root, result) if args.invalidate else result["evidence"]
    print(core.canonical_json_bytes(output).decode(), flush=True)


if __name__ == "__main__":
    main()
