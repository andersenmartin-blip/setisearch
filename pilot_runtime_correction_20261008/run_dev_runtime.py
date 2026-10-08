#!/usr/bin/env python3
"""One once-only DEV_RUNTIME realization under correction 1.

This operational wrapper does not change or replay a scientific panel. Imports
of native scientific dependencies and RNG use occur only inside main(), after
the receipt, frozen definitions and immutable closed A record are checked.
The two new seeds are development evidence; they cannot reopen or repair A.
"""
from __future__ import annotations

import time
PROCESS_STARTED = time.monotonic()

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import traceback

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_CLAIMS = ROOT / "pilot_protocol_20261008/dev_runtime_correction_claims"
CANONICAL_OUTPUTS = ROOT / "results/radio_pilot_dev_runtime_20261008"
MAX_CPU = 1800.0
MAX_WALL = 1800.0
MAX_RSS = 4 * 1024**3
CPU_MARGIN = 15.0
WALL_MARGIN = 10.0

# Existing science and case banks are immutable, including the failed A record.
FROZEN = {
    "detector": "1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45",
    "dev_helpers": "d64aa962c585f536ea969fb09bcc6e16df4289f6fd4e69f396684b94bd995f49",
    "generator": "3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693",
    "contract": "44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c",
    "development_cases": "1f72ab1086a2220da1617aca6dadedc66a6d121359129c90db54ede294fd41df",
    "validation_a_cases": "1edb1ab43c0ff025662de6ce7f6bd5a00cb3c902e275fa5e38d56794c1b86ad1",
    "validation_b_cases": "93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c",
    "summarizer": "6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361",
    "runtime_cases": "2bef79ec3c17568243672c1ec65c9ca2baeb8066dcc4ab6842039f6d4f2a94d1",
    "a_summary": "6e270a49b9094eac26e4d02e152990869374c7f056dc4e0b63d61675d443f67c",
    "a_outcomes": "234c10b30162165e1d34c6e95a889c36e3bbb7796ac14b562f40754f14faed0c",
}
PATH_KEYS = tuple(FROZEN) + ("correction_ledger",)
A_FAILURE_IDS = {
    "SETI_RADIO_PILOT_20261008_VAL_A:single_row_transient:010",
    "SETI_RADIO_PILOT_20261008_VAL_A:single_row_transient:011",
}


def cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_utime + usage.ru_stime)


def snapshot() -> dict:
    return {"wall_s": time.monotonic() - PROCESS_STARTED,
            "cpu_s": cpu_seconds(),
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)}


def watchdog(_signum, _frame):
    raise TimeoutError("DEV_RUNTIME whole-job watchdog reached; no retry or redraw")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_json(path: Path, value) -> None:
    """Replace atomically, requiring file and directory durability."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)
    fsync_directory(path.parent)


def flush_output(path: Path) -> None:
    """The unchanged shared writer is followed by explicit durability checks."""
    for item in sorted(path.iterdir()):
        if not item.is_file():
            raise ValueError("Unexpected non-file output in single-case package")
        with item.open("rb") as f:
            os.fsync(f.fileno())
    fsync_directory(path)


def check_panel(cases: list[dict], panel: str, count: int) -> tuple[set, set]:
    if len(cases) != count or any(c.get("panel") != panel for c in cases):
        raise ValueError(f"Complete frozen {panel} bank of {count} required")
    ids = {c["case_id"] for c in cases}
    seeds = {c["seed_sha256"] for c in cases}
    if len(ids) != count or len(seeds) != count:
        raise ValueError(f"Duplicate {panel} identity or seed")
    for case in cases:
        identity = case["case_id"]
        if (f"_{panel}:" not in identity or
                hashlib.sha256(identity.encode("ascii")).hexdigest() != case["seed_sha256"]):
            raise ValueError(f"Invalid {panel} identity/full-SHA256 seed binding")
    return ids, seeds


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load pinned module {path}")
    module = importlib.util.module_from_spec(spec)
    # The dataclass-based detector requires its own module registered.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require_margin() -> dict:
    observed = snapshot()
    if (observed["wall_s"] >= MAX_WALL - WALL_MARGIN or
            observed["cpu_s"] >= MAX_CPU - CPU_MARGIN or
            observed["peak_rss_bytes"] > MAX_RSS):
        raise TimeoutError("No remaining DEV_RUNTIME whole-job resource margin")
    return observed


def main() -> int:
    # Arm before argument parsing, admission hashes, imports, or any writes.
    # Never re-arm either clock. Process CPU includes interpreter startup.
    signal.signal(signal.SIGALRM, watchdog)
    signal.signal(signal.SIGPROF, watchdog)
    signal.setitimer(signal.ITIMER_REAL,
                     max(0.001, MAX_WALL - WALL_MARGIN - (time.monotonic() - PROCESS_STARTED)))
    signal.setitimer(signal.ITIMER_PROF,
                     max(0.001, MAX_CPU - CPU_MARGIN - cpu_seconds()))
    # Hard memory containment is operational; the original scientific code
    # and its numerical definitions remain byte-for-byte pinned.
    resource.setrlimit(resource.RLIMIT_AS, (MAX_RSS, MAX_RSS))
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                     "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"

    parser = argparse.ArgumentParser(description="One admitted once-only DEV_RUNTIME case")
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--claim-directory", type=Path, default=CANONICAL_CLAIMS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.claim_directory.resolve() != CANONICAL_CLAIMS.resolve():
        raise ValueError("DEV_RUNTIME uses its one canonical exclusive claim scope")
    freeze = json.loads(args.admission.read_text())
    if (freeze.get("status") != "ADMITTED_DEV_RUNTIME_ONLY" or
            not re.fullmatch(r"[0-9a-f]{40}", freeze.get("public_commit_sha", "")) or
            freeze.get("scientific_change") is not False or
            freeze.get("correction_number") != 1):
        raise ValueError("Published correction 1 DEV_RUNTIME-only admission required")
    declared_claims = Path(freeze["claim_directory"])
    if not declared_claims.is_absolute():
        declared_claims = args.admission.resolve().parent / declared_claims
    if declared_claims.resolve() != CANONICAL_CLAIMS.resolve():
        raise ValueError("Receipt claim directory differs from canonical scope")

    paths = {}
    for key in PATH_KEYS:
        p = Path(freeze["paths"][key])
        paths[key] = p.resolve() if p.is_absolute() else (args.admission.resolve().parent / p).resolve()
    paths["runner"] = Path(__file__).resolve()
    observed_hashes = {key: digest(p) for key, p in paths.items()}
    for key, value in observed_hashes.items():
        if freeze["sha256"].get(key) != value:
            raise ValueError(f"Published {key} SHA256 differs; no realization generated")
        if key in FROZEN and value != FROZEN[key]:
            raise ValueError(f"Immutable scientific/A/DEV_RUNTIME binding changed: {key}")

    banks = {key: json.loads(paths[key].read_text()) for key in (
        "development_cases", "validation_a_cases", "validation_b_cases", "runtime_cases")}
    identity_sets = [check_panel(banks[key], panel, count) for key, panel, count in (
        ("development_cases", "DEV", 24), ("validation_a_cases", "VAL_A", 142),
        ("validation_b_cases", "VAL_B", 142), ("runtime_cases", "DEV_RUNTIME", 2))]
    for i in range(len(identity_sets)):
        for j in range(i + 1, len(identity_sets)):
            if identity_sets[i][0] & identity_sets[j][0] or identity_sets[i][1] & identity_sets[j][1]:
                raise ValueError("Frozen banks overlap in identity or full seed")
    runtime_cases = banks["runtime_cases"]
    allowed = freeze.get("allowed_case_ids", [])
    if len(allowed) != 2 or set(allowed) != identity_sets[-1][0]:
        raise ValueError("Exactly the two new development identities must be admitted")
    selected = [(index, c) for index, c in enumerate(runtime_cases) if c["case_id"] == args.case]
    if len(selected) != 1:
        raise ValueError("One exact new DEV_RUNTIME identity required")
    index, case = selected[0]
    if args.output != (CANONICAL_OUTPUTS / f"case_{index:03d}").resolve():
        raise ValueError("Canonical DEV_RUNTIME output location required")
    if args.output.exists():
        raise FileExistsError("Existing case output refused; no replay/overwrite")
    excluded = {"case_id", "panel", "seed_sha256"}
    for fresh, old in zip(runtime_cases, banks["validation_a_cases"][128:130]):
        if ({k: v for k, v in fresh.items() if k not in excluded} !=
                {k: v for k, v in old.items() if k not in excluded}):
            raise ValueError("DEV_RUNTIME laws differ from frozen A128/129")

    contract = json.loads(paths["contract"].read_text())
    interval = contract["geometry"]["reference_source_channel_interval"]
    if interval[1] - interval[0] != 4096 or len(contract["geometry"]["scan_metadata"]) != 6:
        raise ValueError("Unchanged 4096 carriers and all six scans required")
    # Load only the source-only summarizer before any native imports or RNG.
    summarizer = load_module(paths["summarizer"], "frozen_dev_runtime_summarizer")
    a_outcomes = json.loads(paths["a_outcomes"].read_text())
    a_summary = json.loads(paths["a_summary"].read_text())
    recomputed_a = summarizer.summarize(banks["validation_a_cases"], a_outcomes, "VAL_A")
    if recomputed_a != a_summary or recomputed_a["scientific_gate"] != "FAIL_CLOSED":
        raise ValueError("Exact immutable closed A FAIL_CLOSED summary required")
    if (recomputed_a["case_count_observed"] != 142 or recomputed_a["missing_case_ids"] or
            set(recomputed_a["failed_case_ids"]) != A_FAILURE_IDS or
            recomputed_a["checks"]["complete_and_integrity"] is not False or
            any(not value for key, value in recomputed_a["checks"].items() if key != "complete_and_integrity")):
        raise ValueError("Closed A must retain precisely the original two resource failures")
    failed_a = [o for o in a_outcomes if o["case_id"] in A_FAILURE_IDS]
    if len(failed_a) != 2 or any(o.get("failure", {}).get("type") != "TimeoutError" for o in failed_a):
        raise ValueError("Original A128/A129 watchdog failures must remain preserved")

    budget = freeze["budget"]
    if (float(budget["exclusive_cpu_allocation_seconds"]) != MAX_CPU or
            float(budget["max_wall_seconds_per_job"]) != MAX_WALL or
            int(budget["max_rss_bytes"]) != MAX_RSS or
            float(budget["remaining_cpu_seconds"]) < MAX_CPU):
        raise ValueError("One full exclusive 1800 CPU/wall-second, 4GiB partition required")
    require_margin()
    CANONICAL_CLAIMS.mkdir(parents=True, exist_ok=True)
    claim_path = CANONICAL_CLAIMS / (hashlib.sha256(args.case.encode("ascii")).hexdigest() + ".json")
    claim = {"case_id": args.case, "panel": "DEV_RUNTIME", "status": "CLAIMED_BEFORE_ARRAY_GENERATION",
             "first_claim_utc": datetime.now(timezone.utc).isoformat(),
             "public_commit_sha": freeze["public_commit_sha"],
             "admission_SHA256": digest(args.admission), "output_directory": str(args.output),
             "exclusive_cpu_allocation_seconds": MAX_CPU, "no_retry_or_redraw": True,
             "correction_number": 1, "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY"}
    # Claim is never deleted, including if its fsync or a later write fails.
    with claim_path.open("x") as f:
        json.dump(claim, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    fsync_directory(CANONICAL_CLAIMS)

    outcome = {"case_id": args.case, "panel": "DEV_RUNTIME", "family": case["family"],
               "data_integrity_ok": False, "all_active_on_recovered": False,
               "any_localized_on_recovered": False, "pre_OFF_all_active_recovery": False,
               "pre_OFF_any_active_recovery": False, "survivor_count": 0, "failure": None}
    committed = False
    try:
        args.output.mkdir(parents=True)
        fsync_directory(args.output.parent)
        durable_json(args.output / "admission.json", {"freeze_receipt": freeze,
                     "observed_SHA256": observed_hashes, "selected_case_id": args.case,
                     "synthetic": True, "panel": "DEV_RUNTIME", "closed_A_prerequisite": recomputed_a,
                     "case_claim": claim, "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY"})
        durable_json(args.output / "case_definition.json", case)
        # Native imports belong to this guarded, claimed, admitted job.
        import numpy as np
        import scipy
        if np.__version__ != "2.3.5" or scipy.__version__ != "1.17.0" or sys.platform != "linux":
            raise ValueError("Pinned NumPy/SciPy/Linux environment required")
        detector = load_module(paths["detector"], "detector")
        helpers = load_module(paths["dev_helpers"], "frozen_runtime_dev_helpers")
        generator = load_module(paths["generator"], "frozen_runtime_generator")
        require_margin()
        arrays, truth = generator.generate_case(case, contract)
        durable_json(args.output / "truth.json", truth)
        durable_json(args.output / "synthetic_array_hashes.json", [
            {"scan_id": h["scan_id"], "shape": list(a.shape), "dtype": str(a.dtype),
             "C_order_bytes_SHA256": hashlib.sha256(a.tobytes(order="C")).hexdigest()}
            for a, h in zip(arrays, contract["geometry"]["scan_metadata"])])
        scans, frequencies = detector.control_inputs(arrays, contract)
        require_margin()
        result = detector.search_cadence(scans, frequencies, detector.Config())
        helpers.save_result(args.output, result)
        recovery = detector.recovery_matches(result, truth)
        durable_json(args.output / "localized_recovery.json", helpers.clean_json(recovery))
        outcome.update(all_active_on_recovered=recovery["final_all_active_recovery"],
                       any_localized_on_recovered=recovery["final_any_active_recovery"],
                       pre_OFF_all_active_recovery=recovery["pre_OFF_all_active_recovery"],
                       pre_OFF_any_active_recovery=recovery["pre_OFF_any_active_recovery"],
                       data_integrity_ok=True,
                       survivor_count=result["surviving_ON_threshold_carrier_count"],
                       ON_threshold_carrier_count=len(result["all_ON_threshold_carriers"]))
        expected = {f"scan_{i:02d}_full_map.npz" for i in range(6)} | {
            "geometry_arrays.npz", "geometry.json", "scan_map_metadata.json",
            "all_ON_threshold_carriers.json", "detector_summary.json", "truth.json",
            "synthetic_array_hashes.json", "localized_recovery.json"}
        if not expected.issubset({p.name for p in args.output.iterdir() if p.is_file()}):
            raise ValueError("Original complete shared-helper output set missing")
        flush_output(args.output)
        measured = require_margin()
        outcome.update(measured)
        durable_json(args.output / "outcome.json", outcome)
        durable_json(args.output / "outcomes.json", [outcome])
        durable_json(args.output / "resource_receipt.json", {**measured, "caps_passed": True,
                     "measurement_scope": "startup through scientific outputs and first durability flush; controller charges whole reaped job",
                     "caps": {"wall_s": MAX_WALL, "cpu_s_available": MAX_CPU,
                              "exclusive_cpu_allocation_seconds": MAX_CPU, "peak_rss_bytes": MAX_RSS},
                     "watchdog_margins": {"wall_s": WALL_MARGIN, "cpu_s": CPU_MARGIN}})
        durable_json(args.output / "single_case_status.json", {
            "status": "CLOSED_PENDING_DURABLE_COMMIT", "panel": "DEV_RUNTIME", "case_id": args.case,
            "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY", "no_retry_or_redraw": True,
            "A_remains_FAIL_CLOSED": True, "VAL_B_values_generated": False})
        # No success word is written to the canonical claim; the marker below
        # is the sole success authority, bound to the flushed artifact manifest.
        claim.update(status="CLOSED_RECEIPT_CHECK_REQUIRED", **measured)
        durable_json(claim_path, claim)
        manifest = {f.name: {"SHA256": digest(f), "size_bytes": f.stat().st_size}
                    for f in sorted(args.output.iterdir()) if f.is_file()}
        durable_json(args.output / "artifact_manifest.json", manifest)
        flush_output(args.output)
        for name, binding in manifest.items():
            if digest(args.output / name) != binding["SHA256"]:
                raise ValueError("Output hash differs after durability flush")
        measured_at_commit = require_margin()
        marker = {"status": "COMPLETED_CASE_ONLY", "panel": "DEV_RUNTIME", "case_id": args.case,
                  "artifact_manifest_SHA256": digest(args.output / "artifact_manifest.json"),
                  "caps_passed": True, "measured_before_commit": measured_at_commit,
                  "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY", "science_unchanged": True,
                  "no_retry_or_redraw": True, "A_remains_FAIL_CLOSED": True,
                  "VAL_B_values_generated": False}
        durable_json(args.output / "COMMITTED.json", marker)
        require_margin()
        # Both cancellation calls remain inside the protected finalization.
        # A watchdog between them still enters the failure path and removes
        # the marker. No output or hash operation follows their cancellation.
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
        committed = True
    except BaseException as exc:
        # Timeout/write/fsync/hash failures cannot leave a success marker. If
        # the machine itself prevents cleanup, the nonzero exit is authoritative.
        outcome.update(data_integrity_ok=False,
                       failure={"type": type(exc).__name__, "message": str(exc)}, **snapshot())
        try:
            marker_path = args.output / "COMMITTED.json"
            if marker_path.exists():
                marker_path.unlink()
                fsync_directory(args.output)
            if args.output.is_dir():
                durable_json(args.output / "outcome.json", outcome)
                durable_json(args.output / "outcomes.json", [outcome])
                durable_json(args.output / "single_case_status.json", {
                    "status": "FAILED_CLOSED", "case_id": args.case, "panel": "DEV_RUNTIME",
                    "scientific_gate": "NOT_EVALUATED_DEVELOPMENT_ONLY", "no_retry_or_redraw": True,
                    "A_remains_FAIL_CLOSED": True, "VAL_B_values_generated": False})
                durable_json(args.output / "resource_receipt.json", {**snapshot(), "caps_passed": False,
                             "failure": outcome["failure"], "whole_job_controller_charge_required": True})
                with (args.output / "failure_traceback.txt").open("w") as f:
                    f.write(traceback.format_exc())
                    f.flush()
                    os.fsync(f.fileno())
                fsync_directory(args.output)
            claim.update(status="FAILED_CLOSED", failure=outcome["failure"], **snapshot())
            durable_json(claim_path, claim)
        except BaseException:
            # Missing/undurable receipts are never zero-cost or successful.
            pass
    finally:
        # Timers cover every attempted scientific/output/hash/fsync write.
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.setitimer(signal.ITIMER_PROF, 0)
    return 0 if committed else 1


if __name__ == "__main__":
    raise SystemExit(main())
