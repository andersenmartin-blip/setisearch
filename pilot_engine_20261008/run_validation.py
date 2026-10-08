#!/usr/bin/env python3
"""One fresh VAL_A case under a new, immutable, explicit admission.

Operational wrapper only. The detector, generator, law, thresholds, source
geometry and case banks remain exactly as frozen before DEV. No VAL arrays
are created while preparing or importing this file.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import traceback

PROCESS_STARTED = time.monotonic()

import numpy as np
import scipy
from detector import Config, control_inputs, recovery_matches, search_cadence
from run_dev import (cpu_seconds, digest, load_module, peak_rss_bytes, save_result,
                     snapshot, timeout_handler, write_json)


# Scientific and shared-output bindings published before the first DEV array.
# Changing one requires a separate scientific decision; this wrapper cannot
# admit that change by merely accepting another caller-supplied hash.
FROZEN = {
    "detector": "1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45",
    "dev_helpers": "d64aa962c585f536ea969fb09bcc6e16df4289f6fd4e69f396684b94bd995f49",
    "generator": "3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693",
    "contract": "44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c",
    "cases": "1edb1ab43c0ff025662de6ce7f6bd5a00cb3c902e275fa5e38d56794c1b86ad1",
    "development_cases": "1f72ab1086a2220da1617aca6dadedc66a6d121359129c90db54ede294fd41df",
    "validation_b_cases": "93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c",
    "summarizer": "6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361",
}


def check_panel(cases: list[dict], panel: str, expected_count: int) -> tuple[set, set]:
    if len(cases) != expected_count or any(c["panel"] != panel for c in cases):
        raise ValueError(f"Complete frozen {panel} case bank required")
    ids = {c["case_id"] for c in cases}
    seeds = {c["seed_sha256"] for c in cases}
    if len(ids) != len(cases) or len(seeds) != len(cases):
        raise ValueError(f"Duplicate {panel} identities or seeds")
    for c in cases:
        if f"_{panel}:" not in c["case_id"] or hashlib.sha256(c["case_id"].encode("ascii")).hexdigest() != c["seed_sha256"]:
            raise ValueError(f"Invalid {panel} identity/seed binding")
    return ids, seeds


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one admitted fresh VAL_A case only")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--development-cases", type=Path, required=True)
    parser.add_argument("--validation-b-cases", type=Path, required=True)
    parser.add_argument("--development-outcomes", type=Path, required=True)
    parser.add_argument("--development-summary", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--summarizer", type=Path, required=True)
    parser.add_argument("--freeze-receipt", type=Path, required=True)
    parser.add_argument("--claim-directory", type=Path, required=True)
    parser.add_argument("--case", required=True, help="One exact untouched VAL_A identity")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = json.loads(args.freeze_receipt.read_text())
    if (freeze.get("status") != "ADMITTED_VALIDATION_A_ONLY" or
            not re.fullmatch(r"[0-9a-f]{40}", freeze.get("public_commit_sha", "")) or
            freeze.get("development_readiness") != "COMPLETE_DEV_REVIEWED_SAME_SCIENCE"):
        raise ValueError("Published VAL_A admission after reviewed complete DEV required")
    paths = {"detector": Path(__file__).with_name("detector.py"),
             "dev_helpers": Path(__file__).with_name("run_dev.py"),
             "runner": Path(__file__), "generator": args.generator,
             "contract": args.contract, "cases": args.cases,
             "development_cases": args.development_cases,
             "validation_b_cases": args.validation_b_cases,
             "development_outcomes": args.development_outcomes,
             "development_summary": args.development_summary,
             "summarizer": args.summarizer}
    observed_hashes = {key: digest(path) for key, path in paths.items()}
    for key, value in observed_hashes.items():
        if freeze["sha256"].get(key) != value:
            raise ValueError(f"Published {key} SHA256 differs; no validation generated")
        if key in FROZEN and value != FROZEN[key]:
            raise ValueError(f"Scientific/shared frozen {key} changed after DEV")
    if np.__version__ != "2.3.5" or scipy.__version__ != "1.17.0" or sys.platform != "linux":
        raise ValueError("Pinned NumPy/SciPy/Linux environment required")
    cases = json.loads(args.cases.read_text())
    dev_cases = json.loads(args.development_cases.read_text())
    b_cases = json.loads(args.validation_b_cases.read_text())
    identities = [check_panel(cases, "VAL_A", 142), check_panel(dev_cases, "DEV", 24),
                  check_panel(b_cases, "VAL_B", 142)]
    for i in range(3):
        for j in range(i+1, 3):
            if identities[i][0] & identities[j][0] or identities[i][1] & identities[j][1]:
                raise ValueError("DEV/VAL_A/VAL_B identities or seeds overlap")
    selected = [c for c in cases if c["case_id"] == args.case]
    if len(selected) != 1 or args.case not in set(freeze["allowed_case_ids"]):
        raise ValueError("Exactly one existing, admitted VAL_A case required")
    case = selected[0]
    contract = json.loads(args.contract.read_text())
    if (contract["geometry"]["reference_source_channel_interval"][1] -
            contract["geometry"]["reference_source_channel_interval"][0]) != 4096:
        raise ValueError("All 4096 declared ON carriers required")

    summarizer = load_module(args.summarizer, "frozen_validation_summarizer")
    dev_outcomes = json.loads(args.development_outcomes.read_text())
    saved_dev = json.loads(args.development_summary.read_text())
    recomputed_dev = summarizer.summarize(dev_cases, dev_outcomes, "DEV")
    if not recomputed_dev["complete"] or recomputed_dev["case_count_observed"] != 24:
        raise ValueError("All 24 distinct successful DEV records required before fresh validation")
    if any(saved_dev.get(key) != value for key, value in recomputed_dev.items()):
        raise ValueError("Saved complete DEV summary disagrees with its frozen outcomes")

    budget = freeze["budget"]
    max_wall = min(1800.0, float(budget["max_wall_seconds_per_job"]))
    max_rss = min(4*1024**3, int(budget["max_rss_bytes"]))
    exclusive_cpu = float(budget["exclusive_cpu_allocation_seconds"])
    if exclusive_cpu > 250 or exclusive_cpu <= 10:
        raise ValueError("A bounded exclusive allocation of at most 250 CPU seconds is required")
    cpu_available = min(exclusive_cpu, float(budget["remaining_cpu_seconds"]), 12*3600.0)
    if min(max_wall, cpu_available) <= 10 or peak_rss_bytes() > max_rss:
        raise ValueError("No resource margin to begin an untouched VAL_A case")
    if args.output.exists():
        raise FileExistsError("Existing output refused; no repeat or overwrite")
    args.claim_directory.mkdir(parents=True, exist_ok=True)
    claim_path = args.claim_directory / (hashlib.sha256(args.case.encode("ascii")).hexdigest() + ".json")
    claim = {"case_id": args.case, "status": "CLAIMED_BEFORE_ARRAY_GENERATION",
             "first_claim_utc": datetime.now(timezone.utc).isoformat(),
             "public_commit_sha": freeze["public_commit_sha"],
             "admission_SHA256": digest(args.freeze_receipt), "output_directory": str(args.output.resolve()),
             "exclusive_cpu_allocation_seconds": exclusive_cpu}
    # O_EXCL prevents the same identity being exposed twice, including from
    # concurrent processes using different output directories. Claims survive
    # all failures and never authorize redraws or VAL_B execution.
    with claim_path.open("x") as f:
        json.dump(claim, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    args.output.mkdir(parents=True)
    write_json(args.output / "admission.json", {"freeze_receipt": freeze,
               "observed_SHA256": observed_hashes, "selected_case_id": case["case_id"],
               "numpy": np.__version__, "scipy": scipy.__version__, "python": sys.version,
               "synthetic": True, "panel": "VAL_A", "complete_DEV_prerequisite": recomputed_dev,
               "case_claim": claim, "scientific_gate": "NOT_EVALUATED_SINGLE_CASE"})
    write_json(args.output / "case_definition.json", case)
    generator = load_module(args.generator, "frozen_validation_generator")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.signal(signal.SIGPROF, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, max(1.0, max_wall-(time.monotonic()-PROCESS_STARTED)-10))
    signal.setitimer(signal.ITIMER_PROF, max(1.0, cpu_available-cpu_seconds()-5))
    outcome = {"case_id": args.case, "panel": "VAL_A", "family": case["family"],
               "data_integrity_ok": False, "all_active_on_recovered": False,
               "any_localized_on_recovered": False, "pre_OFF_all_active_recovery": False,
               "pre_OFF_any_active_recovery": False, "survivor_count": 0, "failure": None}
    failed = False
    try:
        arrays, truth = generator.generate_case(case, contract)
        write_json(args.output / "truth.json", truth)
        write_json(args.output / "synthetic_array_hashes.json", [
            {"scan_id": h["scan_id"], "shape": list(a.shape), "dtype": str(a.dtype),
             "C_order_bytes_SHA256": hashlib.sha256(a.tobytes(order="C")).hexdigest()}
            for a, h in zip(arrays, contract["geometry"]["scan_metadata"])])
        scans, frequencies = control_inputs(arrays, contract)
        if peak_rss_bytes() > max_rss:
            raise MemoryError("RSS exceeded before scientific detector")
        result = search_cadence(scans, frequencies, Config())
        save_result(args.output, result)
        if truth["active_ON_scan_ids"]:
            recovery = recovery_matches(result, truth)
            write_json(args.output / "localized_recovery.json", recovery)
            outcome.update(all_active_on_recovered=recovery["final_all_active_recovery"],
                           any_localized_on_recovered=recovery["final_any_active_recovery"],
                           pre_OFF_all_active_recovery=recovery["pre_OFF_all_active_recovery"],
                           pre_OFF_any_active_recovery=recovery["pre_OFF_any_active_recovery"])
        else:
            write_json(args.output / "localized_recovery.json",
                       {"recovery_applicable": False, "reason": "No active ON signal in frozen truth"})
        if peak_rss_bytes() > max_rss:
            raise MemoryError("Admitted RSS exceeded")
        outcome.update(data_integrity_ok=True,
                       survivor_count=result["surviving_ON_threshold_carrier_count"],
                       ON_threshold_carrier_count=len(result["all_ON_threshold_carriers"]))
    except Exception as exc:
        outcome["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        (args.output / "failure_traceback.txt").write_text(traceback.format_exc())
        failed = True
    finally:
        # Retain failures; never repeat a claimed realization or switch banks.
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
        measured = snapshot(PROCESS_STARTED, 0.0)
        caps_passed = measured["wall_s"] <= max_wall and measured["cpu_s"] <= cpu_available and measured["peak_rss_bytes"] <= max_rss
        if not caps_passed:
            failed = True
            outcome["data_integrity_ok"] = False
            if outcome["failure"] is None:
                outcome["failure"] = {"type": "ResourceLimit", "message": "Measured whole job exceeded admitted cap"}
        outcome.update(measured)
        write_json(args.output / "outcome.json", outcome)
        write_json(args.output / "outcomes.json", [outcome])
        write_json(args.output / "resource_receipt.json", {**measured, "caps_passed": caps_passed,
                   "caps": {"wall_s": max_wall, "cpu_s_available": cpu_available,
                            "exclusive_cpu_allocation_seconds": exclusive_cpu, "peak_rss_bytes": max_rss}})
        write_json(args.output / "single_case_status.json", {
            "status": "FAILED_CLOSED" if failed else "COMPLETED_CASE_ONLY",
            "case_id": args.case, "panel": "VAL_A", "complete_panel_gate_evaluated": False,
            "no_retry_or_redraw": True, "VAL_B_values_generated": False})
        claim.update(status="FAILED_CLOSED" if failed else "COMPLETED_CASE_ONLY",
                     whole_job_cpu_s=measured["cpu_s"], whole_job_wall_s=measured["wall_s"])
        write_json(claim_path, claim)
        manifest = {f.name: {"SHA256": digest(f), "size_bytes": f.stat().st_size}
                    for f in sorted(args.output.iterdir()) if f.is_file()}
        write_json(args.output / "artifact_manifest.json", manifest)
    print(json.dumps({key: outcome.get(key) for key in (
        "case_id", "data_integrity_ok", "all_active_on_recovered", "pre_OFF_all_active_recovery",
        "survivor_count", "wall_s", "cpu_s", "peak_rss_bytes", "failure")}), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
