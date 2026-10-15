#!/usr/bin/env python3
"""Prospective resource-only continuation. No original ledger writes or retries."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

CPU_CAP = 260000
CHILD_CPU = 600
CHILD_WALL = 1800
CHILD_AS = 1024 ** 3
METADATA = 1000
HISTORICAL_UNKNOWN = 90000
RESULT_CAP = 4 * 1024 ** 3
WORKSPACE_CAP = 8 * 1024 ** 3
MARGIN = 512 * 1024 ** 2
REQUIRED = {"output.json", "truth.json", "inputs.npz", "maps.npz", "case_definition.json", "admission.json"}

def require(value, message):
    if not value: raise ValueError(message)

def raw_json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()

def read(path): return json.loads(Path(path).read_bytes())

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1 << 20): h.update(block)
    return h.hexdigest()

def pin(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}

def verify_pin(value):
    path = Path(value["path"])
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == value["bytes"] and sha(path) == value["sha256"], "Pinned evidence changed: " + str(path))

def save(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if exclusive else path.with_name(path.name + ".tmp")
    with target.open("xb" if exclusive else "wb") as stream:
        stream.write(raw_json(value)); stream.flush(); os.fsync(stream.fileno())
    if not exclusive: target.replace(path)

def emit(value): print(json.dumps(value, sort_keys=True), flush=True)

def regular_bytes(root):
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink(): total += p.stat().st_size
        except FileNotFoundError: pass
    return total

def budget_admits(prior, charged, running):
    return prior + charged + (running + 1) * CHILD_CPU <= CPU_CAP

def safe_roots(stage, extension):
    stage, extension = stage.resolve(), extension.resolve()
    require(extension.parent == stage.parent and extension != stage, "Extension must be a separate sibling outside the frozen stage")
    return stage, extension

def closed_jobs(state, expected, *, stopped=False):
    require(state["status"] == ("STOPPED_RETAINED_NO_RETRY" if stopped else "COMPLETE"), "Original phase is not in the required closed state")
    require(not state["running"], "Original children remain running")
    jobs, remaining = state["jobs"], state["unsubmitted"]
    ids = [j["index"] for j in jobs]
    require(len(ids) == len(set(ids)) and len(remaining) == len(set(remaining)), "Duplicate phase identity")
    require(not set(ids) & set(remaining) and sorted(ids + remaining) == sorted(expected), "Original phase is not an exact closed/unsubmitted partition")
    if stopped:
        require(state.get("stop_reason") == "workspace_or_output_capacity_margin_exhausted", "Only an actual storage-capacity stop can admit this amendment")
        require(remaining, "No unsubmitted validation identities remain")
    else:
        require(not remaining, "Complete original phase has unsubmitted identities")
    for job in jobs:
        require(job["exit_code"] == 0 and job.get("wait4_reaped") is True, "Original attempt failed or was not reaped")
        require(0 <= job["whole_child_CPU_s"] <= CHILD_CPU and 0 <= job["wall_s"] <= CHILD_WALL and 0 <= job["peak_RSS_bytes"] <= CHILD_AS, "Original child resource receipt exceeds a preserved cap")
    charged = sum(j["whole_child_CPU_s"] for j in jobs)
    require(math.isclose(charged, state["charged_complete_child_CPU_s"], rel_tol=0, abs_tol=1e-7), "Original wait4 CPU sum differs")
    return jobs, charged

def closed_case(stage, index, case_id):
    folder = stage / "results/cases" / f"C{index:04d}"
    commit = read(folder / "COMMITTED.json")
    require(commit.get("status") == "COMPLETED_CASE_ONLY" and commit.get("data_integrity_ok") is True, "Primary case is not committed complete")
    require(commit["case_index"] == index and commit["case_id"] == case_id and commit["exposed"] is False, "Primary commit identity differs")
    manifest_path = folder / "artifact_manifest.json"
    require(sha(manifest_path) == commit["artifact_manifest_sha256"], "Committed primary manifest differs")
    manifest = read(manifest_path)
    require(REQUIRED <= manifest.keys(), "Committed primary artifacts are missing")
    for name, declaration in manifest.items():
        require(Path(name).name == name and name not in (".", ".."), "Unsafe primary manifest name")
        path = folder / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == declaration["bytes"] and sha(path) == declaration["sha256"], "Closed primary artifact differs")
    return {"index": index, "case_id": case_id, "COMMITTED": pin(folder / "COMMITTED.json"), "artifact_manifest": pin(manifest_path)}

def unclaimed_primary(stage, index):
    require(not (stage / "claims" / f"C{index:04d}.json").exists(), "Validation identity has already been claimed; no retry")
    require(not (stage / "results/cases" / f"C{index:04d}").exists(), "Validation result/partial folder already exists; no retry")

def unclaimed_qa(stage, index):
    require(not (stage / "claims" / f"QA_C{index:04d}.json").exists(), "QA identity has already been claimed; no retry")
    require(not (stage / "results/qa" / f"C{index:04d}.json").exists(), "QA receipt already exists; no retry")

def source_pins(stage):
    scope, go = read(stage / "SCOPE.json"), read(stage / "GO.json")
    require(go["status"] == "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK" and go["scope_sha256"] == sha(stage / "SCOPE.json"), "Original GO/frozen scope differs")
    require(scope["resources"]["aggregate_new_CPU_s_cap"] == CPU_CAP and scope["resources"]["metadata_and_delivery_reserved_CPU_s"] == METADATA, "Original 260000/1000 budget changed")
    require(scope["resources"]["per_case_CPU_s_cap"] == CHILD_CPU and scope["resources"]["per_case_wall_s_cap"] == CHILD_WALL and scope["resources"]["per_case_address_space_bytes_cap"] == CHILD_AS, "Frozen child caps differ")
    require(scope["resources"]["prior_original_90000_CPU_s_envelope_irreconcilable_historical_reservation_or_debit"] == HISTORICAL_UNKNOWN, "Historical unknown reservation was changed")
    require(scope["resources"]["new_output_payload_cap_bytes"] == 3 * 1024 ** 3 and scope["resources"]["workspace_cap_bytes"] == WORKSPACE_CAP and scope["resources"]["max_concurrent_workers"] == 8, "Original storage/concurrency scope differs")
    answer = [pin(stage / "SCOPE.json"), pin(stage / "GO.json")]
    for declaration in scope["code_pins"]:
        relative = Path(declaration["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe frozen source pin")
        observed = pin(stage / relative)
        require(observed["bytes"] == declaration["bytes"] and observed["sha256"] == declaration["sha256"], "Original frozen source differs")
        answer.append(observed)
    return answer

def admission_snapshot(stage, scheduler_path):
    """Metadata and artifact hashes only; never parse scientific output values."""
    pins = source_pins(stage)
    cases = read(stage / "case_bank.json")
    require(len(cases) == 205 and len({c["case_id"] for c in cases}) == 205, "Exact original 205-identity bank is required")
    calibration = [i for i,c in enumerate(cases) if c["family"] == "calibration"]
    validation = [i for i,c in enumerate(cases) if c["family"] != "calibration"]
    require(len(calibration) == 63 and len(validation) == 142, "Original panel census differs")
    require({p.name for p in stage.glob("*_RUN_STATE.json")} == {"PRIMARY_CALIBRATION_RUN_STATE.json", "PRIMARY_VALIDATION_RUN_STATE.json"}, "Original QA/exposed/other phase already attempted")
    cal_path, val_path = stage / "PRIMARY_CALIBRATION_RUN_STATE.json", stage / "PRIMARY_VALIDATION_RUN_STATE.json"
    cal_jobs, cal_cpu = closed_jobs(read(cal_path), calibration)
    val_state = read(val_path)
    val_jobs, val_cpu = closed_jobs(val_state, validation, stopped=True)
    scheduler = read(scheduler_path)
    require(scheduler["status"] == "STOPPED_RETAINED_NO_RETRY" and all(c["status"] == "CLOSED" for c in scheduler["commands"]), "Original external scheduler has not fully closed")
    require([c["action"] for c in scheduler["commands"]] == ["primary_calibration", "close_calibration", "primary_validation"] and [c["exit_code"] for c in scheduler["commands"]] == [0,0,1], "Original scheduler command closure differs")
    commits, claims = [], []
    for job in cal_jobs + val_jobs:
        index = job["index"]
        require(job["case_id"] == cases[index]["case_id"], "Original wait4 ledger case id differs from its frozen bank index")
        commits.append(closed_case(stage, index, cases[index]["case_id"]))
        claim_path = stage / "claims" / f"C{index:04d}.json"
        claim = read(claim_path)
        require(claim["status"] == "COMPLETED_CASE_ONLY" and claim["case_index"] == index and claim["case_id"] == cases[index]["case_id"], "Original claim closure differs")
        claims.append(pin(claim_path))
    require({p.name for p in (stage / "claims").iterdir()} == {Path(p["path"]).name for p in claims}, "Unexpected original claim/attempt exists")
    require({p.name for p in (stage / "results/cases").iterdir()} == {f"C{job['index']:04d}" for job in cal_jobs + val_jobs}, "Unexpected original result/partial attempt exists")
    require(not (stage / "results/qa").exists() or not list((stage / "results/qa").iterdir()), "Unexpected original QA attempt exists")
    for index in val_state["unsubmitted"]: unclaimed_primary(stage, index)
    for index in range(205): unclaimed_qa(stage, index)
    require(not (stage / "results/exposed").exists(), "Exposed work was already attempted")
    require(set(scheduler["primary_checkpoint_by_label"]) >= {f"C{j['index']:04d}" for j in cal_jobs + val_jobs}, "Original closed cases lack checkpoint references")
    original_summary = read(stage / "results/SUMMARY.json")
    require(original_summary.get("integrity_gate") is False and original_summary.get("joint_gate") is False and original_summary.get("qualified_SETI_detection") is False,
            "Original failed/incomplete SUMMARY must close before amendment admission")
    require(str(original_summary.get("status", "")).startswith("FAIL_CLOSED"), "Original failed SUMMARY status differs")
    original_summary_pin = pin(stage / "results/SUMMARY.json")
    pins += [pin(cal_path), pin(val_path), pin(scheduler_path), pin(stage / "results/CALIBRATION.json")]
    pins.append(original_summary_pin)
    return {"schema": "SETI_RESOURCE_EXTENSION_ADMISSION_SNAPSHOT_V1", "original_stage": str(stage.resolve()),
            "original_scheduler_state": str(scheduler_path.resolve()), "original_scope_sha256": sha(stage / "SCOPE.json"),
            "original_validation_state_sha256": sha(val_path), "original_pins": pins, "original_claim_pins": claims,
            "original_summary_pin": original_summary_pin,
            "original_closed_commits": sorted(commits, key=lambda r:r["index"]),
            "original_reaped_CPU_s": cal_cpu + val_cpu, "original_calibration_indices": calibration,
            "original_validation_closed_indices": sorted(j["index"] for j in val_jobs),
            "untouched_validation_unsubmitted_indices": sorted(val_state["unsubmitted"]),
            "independent_QA_indices_all_proven_unclaimed": list(range(205)),
            "original_execution_gate": False, "original_qualification": "FAIL_CLOSED",
            "exposed": {"status": "NOT_RUN_BLOCKED", "expected_bands": 9},
            "historical_unknown_CPU_reservation_s": HISTORICAL_UNKNOWN}

def verify_original(snapshot):
    for value in snapshot["original_pins"] + snapshot["original_claim_pins"]: verify_pin(value)
    for value in snapshot["original_closed_commits"]:
        verify_pin(value["COMMITTED"]); verify_pin(value["artifact_manifest"])

class Dispatcher:
    def __init__(self, stage, extension, scheduler_path, checkpoint_helper):
        self.stage, self.root = safe_roots(stage, extension)
        self.scheduler_path, self.helper_path = scheduler_path.resolve(), checkpoint_helper.resolve()
        self.checkpoint_root = self.root / "checkpoints"
        self.state_path = self.checkpoint_root / "SCHEDULER_STATE.json"
        self.stop_requested = False

    def admit(self):
        amendment_path, go_path, snapshot_path = self.root / "AMENDMENT.json", self.root / "GO.json", self.root / "ADMISSION_SNAPSHOT.json"
        amendment, go, self.snapshot = read(amendment_path), read(go_path), read(snapshot_path)
        require(amendment["status"] == "FROZEN_RESOURCE_ONLY_CONTINUATION", "Final public amendment is required")
        require(go["status"] == "ADMITTED_AFTER_EXACT_PUBLIC_AMENDMENT_READBACK" and go["amendment_sha256"] == sha(amendment_path) and go["public_exact_readback_verified"] is True, "Exact public amendment admission is required")
        require(isinstance(go["public_freeze_commit"], str) and len(go["public_freeze_commit"]) == 40, "Public immutable freeze commit is missing")
        require(amendment["admission_snapshot_sha256"] == sha(snapshot_path) and amendment["dispatcher_sha256"] == sha(Path(__file__)) and amendment["checkpoint_helper_sha256"] == sha(self.helper_path), "Amendment code/admission pins differ")
        require(amendment["original_scope_sha256"] == self.snapshot["original_scope_sha256"], "Amendment source scope binding differs")
        for field in ("only_original_unsubmitted_and_demonstrably_unclaimed_validation_identities_permitted", "original_case_ids_seeds_recipes_source_code_thresholds_and_scientific_gates_unchanged", "original_states_and_SUMMARY_not_overwritten_or_fabricated", "independent_QA_once_per_original_identity_only_after_all205_primary_commits"):
            require(amendment.get(field) is True, "Amendment preservation declaration differs: " + field)
        require(amendment.get("original_execution_gate") is False and amendment.get("original_qualification") == "FAIL_CLOSED" and amendment.get("exposed") == {"status": "NOT_RUN_BLOCKED", "expected_bands": 9}, "Amendment qualification/exposed preservation differs")
        require(amendment["resources"] == {"results_cap_bytes": RESULT_CAP, "workspace_cap_bytes": WORKSPACE_CAP, "capacity_guard_margin_bytes": MARGIN, "workers": 8, "per_child_CPU_s": CHILD_CPU, "per_child_wall_s": CHILD_WALL, "per_child_address_space_bytes": CHILD_AS, "aggregate_current_study_CPU_s": CPU_CAP, "metadata_reserved_CPU_s": METADATA, "historical_unknown_CPU_reservation_s": HISTORICAL_UNKNOWN}, "Only the declared storage amendment is admitted")
        require(admission_snapshot(self.stage, self.scheduler_path) == self.snapshot, "Original stopped admission evidence changed")
        require(not self.state_path.exists() and not list(self.root.glob("*_EXTENSION_RUN_STATE.json")), "Extension already has a once-only ledger; no resume or retry")
        self.cases = read(self.stage / "case_bank.json")
        self.extension_pins = [pin(p) for p in (amendment_path, go_path, snapshot_path, Path(__file__), self.helper_path)]
        spec = importlib.util.spec_from_file_location("resource_extension_checkpoint_helper", self.helper_path)
        self.helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.helper)
        original_scheduler = read(self.scheduler_path)
        self.primary_index = original_scheduler["primary_checkpoint_by_label"].copy()
        self.state = {"schema": "SETI_RESOURCE_EXTENSION_EXTERNAL_SCHEDULER_V1", "status": "STARTED_ONCE", "commands": [], "checkpoints": [],
                      "original_scope_sha256": self.snapshot["original_scope_sha256"], "amendment_sha256": sha(amendment_path),
                      "original_execution_gate": False, "original_qualification": "FAIL_CLOSED", "exposed": {"status": "NOT_RUN_BLOCKED", "expected_bands": 9}}
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
        save(self.state_path, self.state, exclusive=True)

    def checkpoint(self, phase, jobs, reason):
        sequence = len(self.state["checkpoints"]) + 1
        originals = [self.root / n for n in ("AMENDMENT.json", "GO.json", "ADMISSION_SNAPSHOT.json")]
        originals += list(self.root.glob("*_EXTENSION_RUN_STATE.json"))
        if (self.root / "UNION_LEDGER_GATE.json").exists(): originals.append(self.root / "UNION_LEDGER_GATE.json")
        for job in jobs:
            originals += [self.root / "logs" / f"{phase}_{job['index']:04d}.{suffix}.log" for suffix in ("stdout", "stderr")]
        originals += [Path(__file__)]
        receipt = self.helper.checkpoint(self.stage, self.checkpoint_root, "qa" if phase == "QA_EXTENSION" else "primary_validation", jobs, sequence,
                                        reason=reason, command_logs=originals, primary_checkpoint_index=self.primary_index, scheduler_state_path=self.state_path)
        self.state["checkpoints"].append(receipt)
        if phase == "PRIMARY_VALIDATION_EXTENSION":
            for job in jobs:
                self.primary_index[f"C{job['index']:04d}"] = {"path": receipt["path"], "sha256": receipt["sha256"], "bytes": receipt["bytes"], "sequence": sequence}
        save(self.state_path, self.state)

    def run_phase(self, phase, indices, prior_extension_CPU=0):
        verify_original(self.snapshot)
        for value in self.extension_pins: verify_pin(value)
        qa = phase == "QA_EXTENSION"
        if qa:
            for i, case in enumerate(self.cases): closed_case(self.stage, i, case["case_id"])
            for i in indices: unclaimed_qa(self.stage, i)
        else:
            for i in indices: unclaimed_primary(self.stage, i)
        path = self.root / (phase + "_RUN_STATE.json")
        initial = self.snapshot["original_reaped_CPU_s"] + METADATA + prior_extension_CPU
        state = {"schema": "SETI_RESOURCE_EXTENSION_PHASE_V1", "phase": phase, "status": "RUNNING", "jobs": [], "running": [], "unsubmitted": list(indices),
                 "original_scope_sha256": self.snapshot["original_scope_sha256"], "amendment_sha256": sha(self.root / "AMENDMENT.json"),
                 "initial_prior_charge_and_metadata_reservation_CPU_s": initial, "charged_complete_child_CPU_s": 0,
                 "aggregate_current_study_CPU_s_cap": CPU_CAP, "historical_unknown_CPU_reservation_s": HISTORICAL_UNKNOWN,
                 "per_live_child_reservation_CPU_s": CHILD_CPU}
        save(path, state, exclusive=True)
        record = {"action": phase, "status": "RUNNING", "phase_ledger": str(path)}
        self.state["commands"].append(record); save(self.state_path, self.state)
        running, pending_checkpoints = {}, []
        stop = False
        last_progress = 0
        logs = self.root / "logs"; logs.mkdir(exist_ok=True)
        try:
            while running or state["unsubmitted"]:
                if self.stop_requested: stop = True; state["stop_reason"] = "external_stop_requested_all_running_children_will_be_reaped"
                while not stop and state["unsubmitted"] and len(running) < 8:
                    if regular_bytes(self.stage.parent) >= WORKSPACE_CAP - MARGIN or regular_bytes(self.stage / "results") >= RESULT_CAP - MARGIN:
                        stop = True; state["stop_reason"] = "amended_workspace_or_output_capacity_margin_exhausted"; break
                    if not budget_admits(initial, state["charged_complete_child_CPU_s"], len(running)):
                        stop = True; state["stop_reason"] = "preserved_260000_CPU_reservation_capacity_exhausted"; break
                    index = state["unsubmitted"][0]
                    (unclaimed_qa if qa else unclaimed_primary)(self.stage, index)
                    claim = self.root / "dispatch_claims" / f"{phase}_C{index:04d}.json"
                    command = [sys.executable, str(self.stage / ("qa.py" if qa else "worker.py")), "--case-index", str(index), "--output-root", str(self.stage / "results")]
                    save(claim, {"status": "INTENT_BEFORE_SINGLE_LAUNCH", "index": index, "case_id": self.cases[index]["case_id"], "command": command}, exclusive=True)
                    stdout = (logs / f"{phase}_{index:04d}.stdout.log").open("xb")
                    stderr = (logs / f"{phase}_{index:04d}.stderr.log").open("xb")
                    proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True, env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
                    running[proc.pid] = (proc, index, time.monotonic(), stdout, stderr, command, claim)
                    state["running"].append({"pid": proc.pid, "index": index, "reserved_CPU_s": CHILD_CPU})
                    state["unsubmitted"].pop(0); save(path, state)
                for pid, (proc, index, started, stdout, stderr, command, claim) in list(running.items()):
                    waited, status, usage = os.wait4(pid, os.WNOHANG)
                    if not waited: continue
                    code = os.waitstatus_to_exitcode(status); proc.returncode = code
                    job = {"index": index, "case_id": self.cases[index]["case_id"], "exit_code": code, "whole_child_CPU_s": usage.ru_utime + usage.ru_stime,
                           "wall_s": time.monotonic() - started, "peak_RSS_bytes": usage.ru_maxrss * 1024, "wait4_reaped": True, "pid": pid, "command": command,
                           "exclusive_reservation_before_submit_CPU_s": CHILD_CPU}
                    state["jobs"].append(job); state["charged_complete_child_CPU_s"] += job["whole_child_CPU_s"]
                    state["running"] = [j for j in state["running"] if j["pid"] != pid]
                    del running[pid]
                    state["current_committed_or_live_reserved_CPU_s"] = initial + state["charged_complete_child_CPU_s"] + len(running) * CHILD_CPU
                    save(claim, {"status": "REAPED_ONCE", **job}); save(path, state)
                    stdout.close(); stderr.close()
                    if code != 0 or job["whole_child_CPU_s"] > CHILD_CPU or job["wall_s"] > CHILD_WALL or job["peak_RSS_bytes"] > CHILD_AS:
                        stop = True; state["stop_reason"] = "child_failure_or_resource_cap_no_retry"
                    else: pending_checkpoints.append(job)
                    emit({"event": "EXTENSION_CHILD_REAPED", "phase": phase, "index": index, "exit_code": code, "completed": len(state["jobs"]), "CPU_s": job["whole_child_CPU_s"]})
                while len(pending_checkpoints) >= 4 and not state.get("checkpoint_failure"):
                    try: self.checkpoint(phase, pending_checkpoints[:4], "four_closed_extension_results"); pending_checkpoints = pending_checkpoints[4:]
                    except BaseException as error:
                        stop = True; state["checkpoint_failure"] = str(error); state["stop_reason"] = "checkpoint_failure_no_further_submissions"; save(path, state)
                if stop and not running: break
                if time.monotonic() - last_progress >= 30:
                    emit({"event": "EXTENSION_PROGRESS", "phase": phase, "running": len(running), "completed": len(state["jobs"]), "unsubmitted": len(state["unsubmitted"])}); last_progress = time.monotonic()
                if running: time.sleep(.2)
        except BaseException as error:
            # Any unexpected exception stops submissions. Reap every already
            # launched child before reporting a closed stop; retain actual CPU.
            state["failure"] = {"type": type(error).__name__, "message": str(error)}
            state["stop_reason"] = "unexpected_dispatch_error_all_launched_children_drained"
            while running:
                for pid, (proc, index, started, stdout, stderr, command, claim) in list(running.items()):
                    waited, status, usage = os.wait4(pid, os.WNOHANG)
                    if not waited: continue
                    code = os.waitstatus_to_exitcode(status); proc.returncode = code
                    job = {"index": index, "case_id": self.cases[index]["case_id"], "exit_code": code,
                           "whole_child_CPU_s": usage.ru_utime + usage.ru_stime, "wall_s": time.monotonic() - started,
                           "peak_RSS_bytes": usage.ru_maxrss * 1024, "wait4_reaped": True, "pid": pid, "command": command,
                           "exclusive_reservation_before_submit_CPU_s": CHILD_CPU}
                    state["jobs"].append(job); state["charged_complete_child_CPU_s"] += job["whole_child_CPU_s"]
                    state["running"] = [j for j in state["running"] if j["pid"] != pid]
                    del running[pid]
                    for stream in (stdout, stderr):
                        try: stream.close()
                        except OSError as close_error: state.setdefault("retained_metadata_errors", []).append(str(close_error))
                    try: save(claim, {"status": "REAPED_ONCE", **job}); save(path, state)
                    except OSError as save_error: state.setdefault("retained_metadata_errors", []).append(str(save_error))
                if running: time.sleep(.2)
            state["status"] = "STOPPED_RETAINED_NO_RETRY"
            state["completed_UTC"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            state["current_committed_or_live_reserved_CPU_s"] = initial + state["charged_complete_child_CPU_s"]
            save(path, state)
            record.update(status="CLOSED", exit_code=1); save(self.state_path, self.state)
            raise
        state["status"] = "COMPLETE" if not state["unsubmitted"] and not state.get("checkpoint_failure") and all(j["exit_code"] == 0 and j["whole_child_CPU_s"] <= CHILD_CPU and j["wall_s"] <= CHILD_WALL and j["peak_RSS_bytes"] <= CHILD_AS for j in state["jobs"]) else "STOPPED_RETAINED_NO_RETRY"
        state["current_committed_or_live_reserved_CPU_s"] = initial + state["charged_complete_child_CPU_s"]
        state["completed_UTC"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save(path, state)
        record.update(status="CLOSED", exit_code=0 if state["status"] == "COMPLETE" else 1); save(self.state_path, self.state)
        if not state.get("checkpoint_failure"): self.checkpoint(phase, pending_checkpoints, "extension_phase_closed")
        require(state["status"] == "COMPLETE", "Extension phase stopped; no implicit retry or further phase")
        return state

    def union_gate(self, val, qa):
        verify_original(self.snapshot)
        for value in self.extension_pins: verify_pin(value)
        old = self.snapshot["original_validation_closed_indices"]
        val_jobs, val_cpu = closed_jobs(val, self.snapshot["untouched_validation_unsubmitted_indices"])
        qa_jobs, qa_cpu = closed_jobs(qa, list(range(205)))
        union = sorted(old + [j["index"] for j in val_jobs])
        require(len(union) == len(set(union)) == 142 and union == [i for i,c in enumerate(self.cases) if c["family"] != "calibration"], "Validation union is not exact and disjoint")
        primary = [closed_case(self.stage, i, case["case_id"]) for i,case in enumerate(self.cases)]
        qa_pins = []
        for i, case in enumerate(self.cases):
            path = self.stage / "results/qa" / f"C{i:04d}.json"
            receipt = read(path)
            require(receipt["status"] == "PASS" and receipt["case_index"] == i and receipt["case_id"] == case["case_id"] and receipt["exposed"] is False, "Independent QA closure identity differs")
            require(receipt.get("schema") == "SETI_SIXSCAN_COMPLETE_INDEPENDENT_QA_V1" and receipt.get("qa_sha256") == sha(self.stage / "qa.py"), "Independent QA schema/code binding differs")
            qa_claim = read(self.stage / "claims" / f"QA_C{i:04d}.json")
            require(qa_claim.get("status") == "PASS" and qa_claim.get("receipt_sha256") == sha(path) and qa_claim.get("resources") == receipt.get("resource_usage"), "Independent QA completion claim differs")
            require(receipt.get("worker_output_sha256") == receipt["output_sha256"], "Independent QA duplicate worker-output binding differs")
            require(receipt["scope_sha256"] == self.snapshot["original_scope_sha256"] and receipt["artifact_manifest_sha256"] == primary[i]["artifact_manifest"]["sha256"], "QA source binding differs")
            folder = self.stage / "results/cases" / f"C{i:04d}"
            require(receipt["output_sha256"] == sha(folder / "output.json") and receipt["truth_sha256"] == sha(folder / "truth.json"), "QA primary output/truth binding differs")
            qa_pins.append(pin(path))
        total = self.snapshot["original_reaped_CPU_s"] + val_cpu + qa_cpu + METADATA
        results_bytes, workspace_bytes = regular_bytes(self.stage / "results"), regular_bytes(self.stage.parent)
        require(total <= CPU_CAP and results_bytes <= RESULT_CAP and workspace_bytes <= WORKSPACE_CAP, "Union resource caps exceeded")
        return {"schema": "SETI_RESOURCE_EXTENSION_UNION_METADATA_GATE_V1", "metadata_integrity_gate": True,
                "original_scope_sha256": self.snapshot["original_scope_sha256"], "amendment_sha256": sha(self.root / "AMENDMENT.json"), "admission_snapshot_sha256": sha(self.root / "ADMISSION_SNAPSHOT.json"),
                "original_validation_state_sha256": self.snapshot["original_validation_state_sha256"], "original_execution_gate": False, "original_qualification": "FAIL_CLOSED",
                "primary_identity_count": 205, "independent_QA_identity_count": 205, "validation_union_indices": union,
                "original_and_extension_validation_disjoint": True, "primary_commit_pins": primary, "independent_QA_receipt_pins": qa_pins,
                "phase_state_pins": [pin(self.root / "PRIMARY_VALIDATION_EXTENSION_RUN_STATE.json"), pin(self.root / "QA_EXTENSION_RUN_STATE.json")],
                "resources": {"original_reaped_CPU_s": self.snapshot["original_reaped_CPU_s"], "extension_validation_CPU_s": val_cpu, "extension_QA_CPU_s": qa_cpu,
                              "metadata_reserved_CPU_s": METADATA, "combined_current_study_charge_CPU_s": total, "aggregate_current_study_CPU_s_cap": CPU_CAP,
                              "closed_results_bytes_at_gate": results_bytes, "closed_workspace_bytes_at_gate": workspace_bytes,
                              "results_cap_bytes": RESULT_CAP, "workspace_cap_bytes": WORKSPACE_CAP,
                              "historical_unknown_CPU_reservation_s": HISTORICAL_UNKNOWN, "historical_43200_ledger_preserved_no_reset_or_refund": True},
                "packaging_admission": {"schema": "SETI_RESOURCE_EXTENSION_PACKAGING_ADMISSION_V1", "terminal": True,
                                        "primary_case_ids": [case["case_id"] for case in self.cases], "qa_case_ids": [case["case_id"] for case in self.cases],
                                        "expected_case_ids": [case["case_id"] for case in self.cases], "metadata_integrity_gate": True,
                                        "original_qualification": "FAIL_CLOSED", "original_execution_gate": False, "exposed_real_bands_status": "BLOCKED"},
                "qualified_SETI_detection": False, "scientific_joint_gate_computed_here": False, "exposed": {"status": "NOT_RUN_BLOCKED", "expected_bands": 9}}

    def main(self):
        self.admit()
        for name in (signal.SIGTERM, signal.SIGINT): signal.signal(name, lambda *_: setattr(self, "stop_requested", True))
        try:
            val = self.run_phase("PRIMARY_VALIDATION_EXTENSION", self.snapshot["untouched_validation_unsubmitted_indices"])
            qa = self.run_phase("QA_EXTENSION", list(range(205)), val["charged_complete_child_CPU_s"])
            save(self.root / "UNION_LEDGER_GATE.json", self.union_gate(val, qa), exclusive=True)
            self.checkpoint("QA_EXTENSION", [], "union_metadata_gate_closed")
            self.state["status"] = "ALL_RESOURCE_EXTENSION_PHASES_CLOSED"
        except BaseException as error:
            self.state.update(status="RESOURCE_EXTENSION_STOPPED_RETAINED_NO_RETRY", failure={"type": type(error).__name__, "message": str(error)})
            save(self.state_path, self.state); raise
        save(self.state_path, self.state)
        emit({"event": "RESOURCE_EXTENSION_CLOSED", "state": str(self.state_path), "original_execution_gate": False, "exposed": "NOT_RUN_BLOCKED"})

def self_test():
    checks = []
    resource_job = {"index": 63, "exit_code": 0, "whole_child_CPU_s": 4., "wall_s": 5., "peak_RSS_bytes": 1000000, "wait4_reaped": True}
    state = {"status": "STOPPED_RETAINED_NO_RETRY", "stop_reason": "workspace_or_output_capacity_margin_exhausted", "running": [], "jobs": [resource_job], "unsubmitted": [64], "charged_complete_child_CPU_s": 4.}
    closed_jobs(state, [63,64], stopped=True); checks.append("closed_capacity_stop_exact_disjoint_partition")
    for changed in ({**state,"running":[{"pid":1}]}, {**state,"unsubmitted":[63,64]}, {**state,"stop_reason":"numerical_or_integrity_failure_no_further_submission"}):
        try: closed_jobs(changed, [63,64], stopped=True)
        except ValueError: pass
        else: raise AssertionError("Invalid original closure accepted")
    checks.append("live_children_overlap_and_noncapacity_failure_rejected")
    require(budget_admits(1000, 258400, 0) and not budget_admits(1000, 258401, 0), "Preserved CPU reservation boundary differs")
    checks.append("260000_budget_includes_metadata_measured_prior_and_live600_without_reset")
    require(HISTORICAL_UNKNOWN == 90000 and RESULT_CAP == 4294967296 and WORKSPACE_CAP == 8589934592, "Resource-only limits differ")
    checks.append("historical90000_and_4GiB_results_8GiB_workspace_preserved")
    with tempfile.TemporaryDirectory(prefix="seti_extension_metadata_fixture_") as temporary:
        stage = Path(temporary)
        (stage / "claims").mkdir()
        unclaimed_primary(stage,64); unclaimed_qa(stage,64)
        save(stage / "claims/C0064.json", {"fixture":"claimed"})
        try: unclaimed_primary(stage,64)
        except ValueError: pass
        else: raise AssertionError("Claimed primary was admitted")
        save(stage / "claims/QA_C0064.json", {"fixture":"claimed"})
        try: unclaimed_qa(stage,64)
        except ValueError: pass
        else: raise AssertionError("Claimed QA was admitted")
        checks.append("global_primary_and_QA_claims_prevent_any_retry")
        folder = stage / "results/cases/C0065"; folder.mkdir(parents=True)
        try: unclaimed_primary(stage,65)
        except ValueError: pass
        else: raise AssertionError("Partial case folder admitted")
        checks.append("even_uncommitted_partial_case_folder_blocks_dispatch")
        fixture_stage, fixture_root = stage / "fake_stage", stage / "fake_extension"
        fixture_stage.mkdir(); fixture_root.mkdir()
        (fixture_stage / "worker.py").write_text("import time\ntime.sleep(.02)\n")
        dispatcher = Dispatcher(fixture_stage, fixture_root, stage / "unused_scheduler.json", stage / "unused_helper.py")
        dispatcher.snapshot = {"original_pins": [], "original_claim_pins": [], "original_closed_commits": [], "original_reaped_CPU_s": 0, "original_scope_sha256": "TRANSPORT_FIXTURE"}
        dispatcher.extension_pins = []
        dispatcher.cases = [{"case_id": "TRANSPORT_FIXTURE_0"}, {"case_id": "TRANSPORT_FIXTURE_1"}]
        dispatcher.state = {"commands": [], "checkpoints": []}
        save(fixture_root / "AMENDMENT.json", {"fixture": True})
        save(dispatcher.state_path, dispatcher.state)
        actual_popen, launches = subprocess.Popen, []
        def fixture_popen(*args, **kwargs):
            if launches: raise OSError("Deliberate transport-fixture second-launch failure")
            child = actual_popen(*args, **kwargs); launches.append(child); return child
        subprocess.Popen = fixture_popen
        try:
            try: dispatcher.run_phase("PRIMARY_VALIDATION_EXTENSION", [0,1])
            except OSError: pass
            else: raise AssertionError("Fixture launch error did not stop")
        finally: subprocess.Popen = actual_popen
        drained = read(fixture_root / "PRIMARY_VALIDATION_EXTENSION_RUN_STATE.json")
        require(drained["status"] == "STOPPED_RETAINED_NO_RETRY" and not drained["running"] and len(drained["jobs"]) == 1 and drained["jobs"][0]["wait4_reaped"] is True, "Unexpected failure did not drain/reap prior launched child")
        require(launches[0].returncode == 0, "Fixture child remains unreaped")
        checks.append("unexpected_second_Popen_failure_drains_first_stub_child_and_retains_wait4_CPU")
        try: safe_roots(fixture_stage, fixture_stage)
        except ValueError: pass
        else: raise AssertionError("Frozen-stage snapshot destination was accepted")
        checks.append("shared_capture_and_dispatch_path_guard_rejects_frozen_stage_destination")
    emit({"schema":"SETI_RESOURCE_EXTENSION_METADATA_FIXTURE_V1","status":"PASS","checks":checks,"scientific_outcomes_read":False,"numerical_trials":0,"Library_uploads":0,"dispatcher_sha256":sha(Path(__file__))})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path); parser.add_argument("--extension-root",type=Path)
    parser.add_argument("--original-scheduler-state",type=Path); parser.add_argument("--checkpoint-helper",type=Path)
    parser.add_argument("--capture-admission",action="store_true"); parser.add_argument("--self-test",action="store_true")
    args = parser.parse_args()
    if args.self_test: self_test(); return 0
    require(args.stage and args.extension_root and args.original_scheduler_state, "Explicit stage/extension/original-scheduler paths required")
    args.stage, args.extension_root = safe_roots(args.stage, args.extension_root)
    if args.capture_admission:
        save(args.extension_root / "ADMISSION_SNAPSHOT.json", admission_snapshot(args.stage.resolve(), args.original_scheduler_state.resolve()), exclusive=True)
        return 0
    require(args.checkpoint_helper, "Pinned external checkpoint helper is required")
    Dispatcher(args.stage,args.extension_root,args.original_scheduler_state,args.checkpoint_helper).main()
    return 0

if __name__ == "__main__": raise SystemExit(main())
