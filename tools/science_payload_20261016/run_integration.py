#!/usr/bin/env python3
"""Freeze then once-only run two guarded engineering semantic-integration jobs.

No scientific admission, case bank, RNG or old study main is implemented.
The freeze command is a source/scope operation only.  The run command requires
the exact frozen output path, a fresh ledger and an exclusive identity claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
WORKSPACE = SOURCE.parent
sys.path.insert(0, str(HERE))
from integration import IDENTITY, MODE, PAYLOAD_CAP
from phase_budget import PhaseLedger, plan_budget

SOURCE_NAMES = (
    "tools/science_payload_20261016/integration.py",
    "tools/science_payload_20261016/run_integration.py",
    "tools/science_payload_20261016/payload.py",
    "tools/science_payload_20261016/phase_budget.py",
    "tools/whole_child_guard_20261015/guard.py",
    "tools/bounded_payload_20261015/payload_store.py",
    "tools/fullcase_payload_20261015/array_adapter.py",
    "tools/fullcase_payload_20261015/runtime.py",
    "tools/fullcase_payload_20261015/SOURCE_PINS.json",
    "analysis/sixscan_burst_20261015/worker.py",
    "analysis/sixscan_burst_20261015/detector.py",
    "analysis/sixscan_burst_20261015/qa.py",
    "analysis/sixscan_burst_20261015/summarize.py",
    "analysis/sixscan_burst_20261015/contract.json")
GUARD_SHA = "d02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492"
MIB = 1024 ** 2
SLOT_OVERHEAD = 256 * 1024
METADATA_RESERVE = 256 * 1024
OUTPUT_LIMIT = 72 * MIB
CPU_LIMIT = 500


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    encoded = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    require(len(encoded) <= METADATA_RESERVE // 2, "Runner metadata file exceeds bound")
    with Path(path).open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        import os
        os.fsync(stream.fileno())


def regular_bytes(root):
    root = Path(root)
    if not root.exists(): return 0
    total = 0
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Symlink in engineering output")
        if path.is_file(): total += path.stat().st_size
    return total


def path_bytes(path):
    path = Path(path)
    if path.is_dir(): return regular_bytes(path)
    return path.stat().st_size if path.exists() else 0


def source_pins():
    return [{"path": name, "bytes": (SOURCE / name).stat().st_size, "sha256": sha(SOURCE / name)}
            for name in SOURCE_NAMES]


def identity_claim_path():
    return WORKSPACE / "work" / "SETI_ENGINEERING_ONCE_CLAIMS_2026-10-16" / (IDENTITY + ".json")


def freeze(scope_path, output_root):
    scope_path, output_root = Path(scope_path).resolve(), Path(output_root).resolve()
    require(not output_root.exists(), "Fresh integration output root required")
    require(not identity_claim_path().exists(), "Engineering identity already attempted; no rerun")
    require(scope_path.parent.is_dir(), "Scope parent must already exist")
    require(sha(SOURCE / "tools/whole_child_guard_20261015/guard.py") == GUARD_SHA,
            "Previously tested guard bytes differ")
    scope = {"schema": "SETI_SEMANTIC_INTEGRATION_ENGINEERING_FREEZE_V1", "mode": MODE,
       "identity": IDENTITY, "output_root": str(output_root), "source_pins": source_pins(),
       "producer_cpu_s": 240, "verifier_cpu_s": 240, "whole_child_wall_s": 600,
       "whole_child_address_space_bytes": 1024 ** 3,
       "payload_cap_bytes": PAYLOAD_CAP, "output_limit_bytes": OUTPUT_LIMIT,
       "metadata_reserved_CPU_s": 20, "aggregate_CPU_s_reserved": CPU_LIMIT,
       "primary_payload_and_receipt_cap_bytes": 66 * MIB,
       "qa_report_cap_bytes": 2 * MIB, "per_slot_log_receipt_overhead_bytes": SLOT_OVERHEAD,
       "controlled_Python_stdout_and_stderr_cap_bytes_each": 64 * 1024,
       "native_log_quota": "POST_REAP_ACCEPTANCE_ONLY_NOT_GENERIC_HARD_WRITER_QUOTA",
       "metadata_reserve_bytes": METADATA_RESERVE,
       "actual_detector_full_search": False, "raw_fixture_shape": [6, 16, 12096],
       "controlled_retained_carriers_per_scan": 2,
       "not_a_study_admission": True, "RNG_or_old_main_calls": 0,
       "old_scientific_identities_or_admissions_reused": False,
       "qualified_SETI_detection": False, "original_A_B": "FAIL_CLOSED"}
    save(scope_path, scope)
    return {"scope": str(scope_path), "sha256": sha(scope_path), "status": "FROZEN_ENGINEERING_ONLY"}


def load_guard():
    path = SOURCE / "tools/whole_child_guard_20261015/guard.py"
    require(sha(path) == GUARD_SHA, "Pinned process guard differs")
    spec = importlib.util.spec_from_file_location("semantic_integration_pinned_guard", path)
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    return guard


def run(scope_path):
    scope_path = Path(scope_path).resolve(); scope = json.loads(scope_path.read_text())
    require(scope.get("schema") == "SETI_SEMANTIC_INTEGRATION_ENGINEERING_FREEZE_V1", "Unknown frozen scope")
    require(scope["mode"] == MODE and scope["identity"] == IDENTITY, "Engineering mode/identity required")
    require(scope["source_pins"] == source_pins(), "Frozen source bytes changed before launch")
    require(scope["aggregate_CPU_s_reserved"] == CPU_LIMIT and scope["output_limit_bytes"] == OUTPUT_LIMIT,
            "Frozen integration bounds differ")
    root = Path(scope["output_root"])
    require(not root.exists() and root.parent.is_dir(), "Exclusive fresh output root required")
    disk = shutil.disk_usage(root.parent).free
    plan = plan_budget(primary_count=1, primary_bound_bytes=66 * MIB, primary_cpu_s=240,
        qa_count=1, qa_bound_bytes=2 * MIB, qa_cpu_s=240,
        exposed_count=0, exposed_bound_bytes=1, exposed_cpu_s=240,
        exposed_qa_count=0, exposed_qa_bound_bytes=1, exposed_qa_cpu_s=240,
        metadata_reserve_bytes=METADATA_RESERVE, metadata_cpu_s=20,
        log_receipt_overhead_bytes=SLOT_OVERHEAD, output_limit_bytes=OUTPUT_LIMIT,
        disk_headroom_bytes=disk, cpu_limit_s=CPU_LIMIT, mode=MODE)
    require(plan["admitted"], "Whole producer+QA phase reservation does not fit")
    guard = load_guard()
    claim = identity_claim_path(); claim.parent.mkdir(parents=True, exist_ok=True)
    save(claim, {"identity": IDENTITY, "scope_sha256": sha(scope_path), "output_root": str(root),
                 "status": "CLAIMED_ONCE_BEFORE_NUMERICAL_CHILD_IMPORTS", "no_retry": True})
    root.mkdir()
    save(root / "FROZEN_SCOPE.json", scope)
    ledger = PhaseLedger.create(root / "ledger", plan)
    limits = guard.policy(240, 600, 1024 ** 3)
    state = {"status": "RUNNING_ENGINEERING_ONLY", "identity": IDENTITY, "scope_sha256": sha(scope_path),
       "mode": MODE, "producer": None, "verifier": None, "scientific_admission": False,
       "qualified_SETI_detection": False, "original_A_B": "FAIL_CLOSED"}
    for phase, command, attempt, payload_path, extra in (
        ("primary", [sys.executable, str(HERE / "integration.py"), "produce", "--folder", str(root / "fixture")],
         "producer", root / "fixture" / "payload", root / "fixture" / "PRODUCER.json"),
        ("qa", [sys.executable, str(HERE / "integration.py"), "verify", "--folder", str(root / "fixture"),
                "--report", str(root / "SEMANTIC_VERIFICATION.json")],
         "verifier", root / "SEMANTIC_VERIFICATION.json", None)):
        phase_claim = ledger.claim(phase, IDENTITY + "_" + phase)
        receipt = None
        try:
            receipt = guard.run_once(command, root / attempt, limits)
            # Primary's plan includes its bounded 2MiB producer side receipt.
            # Guard files and bounded child logs consume the per-slot overhead.
            payload_size = path_bytes(payload_path)
            if extra is not None and extra.exists(): payload_size += extra.stat().st_size
            log_size = regular_bytes(root / attempt)
            event = ledger.complete(phase_claim["claim_id"], receipt=receipt,
                                    payload_bytes=payload_size, log_receipt_bytes=log_size)
            state[attempt] = {"receipt": receipt, "payload_bytes": payload_size,
                              "log_receipt_bytes": log_size, "accepted": event["data"]["accepted"]}
            if not event["data"]["accepted"]:
                state["status"] = "STOPPED_RETAINED_NO_RETRY"
                break
        except BaseException as error:
            # A launcher/parent error also permanently consumes this claim.
            if ledger.snapshot()["pending"]:
                failed_payload_size = path_bytes(payload_path)
                if extra is not None and extra.exists(): failed_payload_size += extra.stat().st_size
                ledger.partial_error(phase_claim["claim_id"], error=repr(error), receipt=receipt,
                                     payload_bytes=failed_payload_size,
                                     log_receipt_bytes=regular_bytes(root / attempt))
            state["status"] = "STOPPED_RETAINED_NO_RETRY"
            state["parent_error"] = {"type": type(error).__name__, "message": str(error)[:512]}
            break
    try:
        if state["status"] == "RUNNING_ENGINEERING_ONLY":
            report = json.loads((root / "SEMANTIC_VERIFICATION.json").read_text())
            require(report["status"] == "PASS_ENGINEERING_SEMANTICS_ONLY", "Verifier semantic pass missing")
            require(scope["source_pins"] == source_pins(), "Frozen sources changed during integration")
            state["status"] = "PASS_GUARDED_ENGINEERING_SEMANTICS_ONLY"
            state["verification_sha256"] = sha(root / "SEMANTIC_VERIFICATION.json")
        state["actual_output_bytes_before_final_receipt"] = regular_bytes(root)
        require(state["actual_output_bytes_before_final_receipt"] + METADATA_RESERVE <= OUTPUT_LIMIT,
                "Actual bounded execution output reservation exceeded")
    except BaseException as error:
        state["status"] = "STOPPED_RETAINED_NO_RETRY"
        state["finalization_error"] = {"type": type(error).__name__, "message": str(error)[:512]}
    try:
        ledger.close()
        state["phase_ledger_snapshot"] = ledger.snapshot()
    except BaseException as error:
        state["status"] = "STOPPED_RETAINED_NO_RETRY"
        state["ledger_finalization_error"] = {"type": type(error).__name__, "message": str(error)[:512]}
    save(root / "INTEGRATION_RESULT.json", state)
    return state


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    freeze_parser = sub.add_parser("freeze"); freeze_parser.add_argument("--scope", type=Path, required=True)
    freeze_parser.add_argument("--output-root", type=Path, required=True)
    run_parser = sub.add_parser("run"); run_parser.add_argument("--scope", type=Path, required=True)
    args = ap.parse_args()
    if args.command == "freeze": result = freeze(args.scope, args.output_root)
    else:
        state = run(args.scope)
        result = {"status": state["status"], "identity": IDENTITY,
                  "scientific_admission": False, "qualified_SETI_detection": False}
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["status"] in ("FROZEN_ENGINEERING_ONLY", "PASS_GUARDED_ENGINEERING_SEMANTICS_ONLY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
