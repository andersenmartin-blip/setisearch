#!/usr/bin/env python3
"""External once-only phase runner and closed-result transport checkpoints.

This file does not implement or change the numerical experiment.  The frozen
coordinator alone launches numerical workers.  Checkpoint archives are local
transport artifacts until the supervising root agent saves them durably.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

PHASES = ("primary_calibration", "primary_validation", "qa", "exposed", "qa_exposed")
EVERY = 4
REQUIRED_CASE_FILES = {"output.json", "truth.json", "inputs.npz", "maps.npz", "case_definition.json", "admission.json"}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def atomic_json(path, value, *, exclusive=False):
    data = json_bytes(value)
    if exclusive:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


def phase_indices(root, phase):
    bank = read(root / "case_bank.json")
    if phase == "primary_calibration":
        return [i for i, row in enumerate(bank) if row["family"] == "calibration"]
    if phase == "primary_validation":
        return [i for i, row in enumerate(bank) if row["family"] != "calibration"]
    if phase == "qa":
        return list(range(len(bank)))
    return list(range(9))


def stage_admission(root, workers):
    scope_bytes = (root / "SCOPE.json").read_bytes()
    scope, go = json.loads(scope_bytes), read(root / "GO.json")
    require(go["status"] == "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK", "Public freeze admission is required")
    require(go["scope_sha256"] == digest(scope_bytes), "GO scope hash differs")
    for pin in scope["code_pins"]:
        relative = Path(pin["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe frozen pin path")
        data = (root / relative).read_bytes()
        require(len(data) == pin["bytes"] and digest(data) == pin["sha256"], "Frozen pin differs: " + str(relative))
    require(1 <= workers <= scope["resources"]["max_concurrent_workers"], "Worker count exceeds the frozen scope")
    require(len(phase_indices(root, "primary_calibration")) == 63, "Exactly 63 calibration cases")
    require(len(phase_indices(root, "primary_validation")) == 142, "Exactly 142 validation cases")
    require(len(phase_indices(root, "qa")) == 205, "Exactly 205 independent QA cases")
    real = read(root / "real_baselines.json")
    require(len(real if isinstance(real, list) else real["cases"]) == 9, "Exactly nine exposed bands")
    return scope, digest(scope_bytes)


def closed_producer_payload(root, index, exposed):
    """Read only artifacts covered by a complete producer commit and manifest."""
    label = ("R" if exposed else "C") + f"{index:04d}"
    folder = root / "results" / ("exposed" if exposed else "cases") / label
    commit_path = folder / "COMMITTED.json"
    commit_bytes = commit_path.read_bytes()
    commit = json.loads(commit_bytes)
    require(commit.get("status") == "COMPLETED_CASE_ONLY" and commit.get("data_integrity_ok") is True, "Producer is not complete: " + label)
    require(commit["case_index"] == index and commit["exposed"] == exposed, "Producer commit index differs")
    manifest_bytes = (folder / "artifact_manifest.json").read_bytes()
    require(digest(manifest_bytes) == commit["artifact_manifest_sha256"], "Committed artifact manifest differs")
    manifest = json.loads(manifest_bytes)
    require(REQUIRED_CASE_FILES <= manifest.keys(), "Required complete artifacts are missing")
    payload = []
    for name, pin in sorted(manifest.items()):
        require(Path(name).name == name and name not in (".", ".."), "Unsafe producer manifest member")
        path = folder / name
        require(path.is_file() and not path.is_symlink(), "Producer artifact must be a regular file")
        require(path.stat().st_size == pin["bytes"], "Producer artifact length differs: " + name)
        payload.append((path, pin["sha256"], pin["bytes"], "closed_producer_artifact"))
    payload += [(folder / "artifact_manifest.json", digest(manifest_bytes), len(manifest_bytes), "closed_producer_manifest"),
                (commit_path, digest(commit_bytes), len(commit_bytes), "closed_producer_commit")]
    return payload, commit


def closed_qa_payload(root, index, exposed, scope_sha):
    label = ("R" if exposed else "C") + f"{index:04d}"
    path = root / "results" / "qa" / (label + ".json")
    data = path.read_bytes()
    receipt = json.loads(data)
    require(receipt.get("status") == "PASS", "QA is not a closed PASS: " + label)
    require(receipt["case_index"] == index and receipt["exposed"] == exposed, "QA identity differs")
    require(receipt["scope_sha256"] == scope_sha, "QA scope differs")
    # Producer arrays were archived by earlier phases.  Recheck receipt bindings;
    # do not duplicate all scientific arrays for every QA checkpoint.
    _, commit = closed_producer_payload(root, index, exposed)
    require(receipt["artifact_manifest_sha256"] == commit["artifact_manifest_sha256"], "QA producer binding differs")
    folder = root / "results" / ("exposed" if exposed else "cases") / label
    for field, name in (("output_sha256", "output.json"), ("truth_sha256", "truth.json")):
        require(receipt[field] == digest((folder / name).read_bytes()), "QA artifact binding differs: " + field)
    return [(path, digest(data), len(data), "closed_independent_QA_receipt")]


def frozen_snapshot(root):
    scope = read(root / "SCOPE.json")
    names = {pin["path"] for pin in scope["code_pins"]} | {"SCOPE.json", "GO.json"}
    if (root / "SCOPE_REVIEW.json").exists():
        names.add("SCOPE_REVIEW.json")
    return [root / name for name in sorted(names)]


def stream_sha(stream):
    hasher = hashlib.sha256()
    size = 0
    while block := stream.read(1024 * 1024):
        hasher.update(block)
        size += len(block)
    return hasher.hexdigest(), size


def checkpoint(root, destination, phase, jobs, sequence, *, reason, command_logs=(), primary_checkpoint_index=None, scheduler_state_path=None, announce=True):
    """Create one verified delta archive; never read an uncommitted case array."""
    scope_sha = digest((root / "SCOPE.json").read_bytes())
    destination.mkdir(parents=True, exist_ok=True)
    name = f"CHECKPOINT_{sequence:04d}_{phase}_{reason}.zip"
    final = destination / name
    partial = destination / (name + ".partial")
    require(not final.exists() and not partial.exists(), "Checkpoint path already used")
    payload = []
    producer_references = {}
    exposed = phase in ("exposed", "qa_exposed")
    for job in jobs:
        require(job["exit_code"] == 0 and job.get("wait4_reaped") is True, "Only successful reaped jobs can supply complete result payloads")
        index = job["index"]
        if phase in ("qa", "qa_exposed"):
            payload.extend(closed_qa_payload(root, index, exposed, scope_sha))
            label = ("R" if exposed else "C") + f"{index:04d}"
            require(primary_checkpoint_index is not None and label in primary_checkpoint_index,
                    "QA transport must reference an earlier closed producer checkpoint")
            folder = root / "results" / ("exposed" if exposed else "cases") / label
            commit_bytes = (folder / "COMMITTED.json").read_bytes()
            manifest_bytes = (folder / "artifact_manifest.json").read_bytes()
            producer_references[label] = {"producer_checkpoint": primary_checkpoint_index[label],
                                          "COMMITTED_sha256": digest(commit_bytes),
                                          "artifact_manifest_sha256": digest(manifest_bytes),
                                          "artifact_pins": json.loads(manifest_bytes),
                                          "producer_payload_not_duplicated_in_QA_archive": True}
        else:
            closed, _ = closed_producer_payload(root, index, exposed)
            payload.extend(closed)
        for suffix in ("stdout.log", "stderr.log"):
            path = root / "logs" / f"{phase}_{index:04d}.{suffix}"
            if path.exists():
                data = path.read_bytes()
                payload.append((path, digest(data), len(data), "closed_reaped_child_log"))
    snapshots = []
    for path in frozen_snapshot(root):
        snapshots.append((path.relative_to(root).as_posix(), path.read_bytes(), "frozen_source_or_admission"))
    for path in sorted(root.glob("*_RUN_STATE.json")):
        snapshots.append((path.relative_to(root).as_posix(), path.read_bytes(), "authoritative_coordinator_state_snapshot_at_capture"))
    for path in sorted((root / "claims").glob("*.json")) if (root / "claims").exists() else []:
        snapshots.append((path.relative_to(root).as_posix(), path.read_bytes(), "claim_snapshot_may_be_live_not_a_completion_assertion"))
    for filename in ("CALIBRATION.json", "SUMMARY.json", "EXPOSED_SUMMARY.json", "CASE_RESULTS.csv", "CALIBRATED_HITS.csv"):
        path = root / "results" / filename
        if path.exists():
            snapshots.append((path.relative_to(root).as_posix(), path.read_bytes(), "closed_summary_or_table_snapshot"))
    for path in command_logs:
        if path.exists():
            snapshots.append(("_external_logs/" + path.name, path.read_bytes(), "external_command_log_snapshot_may_be_live"))
    if scheduler_state_path is not None and scheduler_state_path.exists():
        snapshots.append(("_external_scheduler/SCHEDULER_STATE.json", scheduler_state_path.read_bytes(), "external_scheduler_state_before_this_checkpoint_receipt"))
    snapshots.append(("_checkpoint_tools/durable_scheduler.py", Path(__file__).read_bytes(), "external_non_numerical_scheduler"))
    entries = {}
    with zipfile.ZipFile(partial, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for path, expected_sha, expected_bytes, classification in payload:
            arcname = root.name + "/" + path.relative_to(root).as_posix()
            require(arcname not in entries, "Duplicate archive name")
            archive.write(path, arcname)
            entries[arcname] = {"sha256": expected_sha, "bytes": expected_bytes, "classification": classification}
        for relative, data, classification in snapshots:
            arcname = root.name + "/" + relative
            require(arcname not in entries, "Duplicate snapshot name")
            archive.writestr(arcname, data)
            entries[arcname] = {"sha256": digest(data), "bytes": len(data), "classification": classification}
        manifest = {"schema": "SETI_CLOSED_RESULT_DELTA_CHECKPOINT_V1", "phase": phase, "reason": reason,
                    "sequence": sequence, "stage": root.name, "scope_sha256": scope_sha,
                    "captured_UTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "new_complete_job_indices": [job["index"] for job in jobs],
                    "complete_result_arrays_only_from_COMMITTED_manifest_verified_cases": True,
                    "coordinator_and_claim_snapshots_may_include_live_claims": True,
                    "no_local_archive_alone_proves_remote_persistence": True,
                    "referenced_closed_producer_payloads": producer_references,
                    "members": entries}
        archive.writestr("CHECKPOINT_MANIFEST.json", json_bytes(manifest))
    with zipfile.ZipFile(partial) as archive:
        require(set(archive.namelist()) == set(entries) | {"CHECKPOINT_MANIFEST.json"}, "Checkpoint member census differs")
        for arcname, pin in entries.items():
            with archive.open(arcname) as stream:
                observed_sha, observed_bytes = stream_sha(stream)
            require(observed_sha == pin["sha256"] and observed_bytes == pin["bytes"], "Checkpoint readback differs: " + arcname)
        require(json.loads(archive.read("CHECKPOINT_MANIFEST.json")) == manifest, "Checkpoint manifest readback differs")
    partial.replace(final)
    with final.open("rb") as stream:
        archive_sha, archive_bytes = stream_sha(stream)
    receipt = {"event": "DURABLE_UPLOAD_REQUEST", "path": str(final), "bytes": archive_bytes,
               "sha256": archive_sha, "phase": phase, "sequence": sequence, "reason": reason,
               "new_complete_job_indices": manifest["new_complete_job_indices"],
               "local_archive_readback_verified": True, "remote_persistence_confirmed": False}
    atomic_json(destination / (name + ".receipt.json"), receipt, exclusive=True)
    if announce:
        emit(receipt)
    return receipt


def command_for(root, action, workers):
    if action in PHASES:
        return [sys.executable, str(root / "coordinator.py"), "--root", str(root), "--phase", action, "--workers", str(workers)]
    command = [sys.executable, str(root / "summarize.py"), "--root", str(root)]
    if action == "close_calibration":
        command.append("--calibration-only")
    elif action == "close_exposed":
        command.append("--exposed")
    else:
        require(action == "close_synthetic", "Unknown scheduler action")
    return command


class Runner:
    def __init__(self, root, destination, workers):
        self.root, self.destination, self.workers = root, destination, workers
        self.state_path = destination / "SCHEDULER_STATE.json"
        self.state = {"schema": "SETI_EXTERNAL_ONCE_ONLY_PHASE_RUNNER_V1", "status": "STARTED_ONCE", "stage": str(root),
                      "started_UTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "commands": [], "checkpoints": [],
                      "primary_checkpoint_by_label": {},
                      "numerical_workers_owned_only_by_frozen_coordinator": True, "automatic_retry_or_resume": False}

    def save(self):
        atomic_json(self.state_path, self.state)

    def capture(self, phase, jobs, reason, logs):
        receipt = checkpoint(self.root, self.destination, phase, jobs, len(self.state["checkpoints"]) + 1,
                             reason=reason, command_logs=logs, primary_checkpoint_index=self.state["primary_checkpoint_by_label"],
                             scheduler_state_path=self.state_path)
        self.state["checkpoints"].append(receipt)
        if phase in ("primary_calibration", "primary_validation", "exposed"):
            for job in jobs:
                label = ("R" if phase == "exposed" else "C") + f"{job['index']:04d}"
                self.state["primary_checkpoint_by_label"][label] = {
                    "path": receipt["path"], "sha256": receipt["sha256"], "bytes": receipt["bytes"],
                    "sequence": receipt["sequence"], "remote_persistence_confirmed": False}
        self.save()

    def run_action(self, action):
        _, scope_sha = stage_admission(self.root, self.workers)
        require(scope_sha == self.state["scope_sha256"], "Frozen scope changed after scheduler admission")
        command = command_for(self.root, action, self.workers)
        stdout_path = self.destination / (action + ".stdout.log")
        stderr_path = self.destination / (action + ".stderr.log")
        record = {"action": action, "command": command, "status": "CLAIMED_BEFORE_LAUNCH"}
        self.state["commands"].append(record)
        self.save()
        archived = set()
        checkpoint_error = None
        last_progress = 0
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                                    env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
            record.update(status="RUNNING", pid=proc.pid)
            self.save()
            emit({"event": "ACTION_STARTED", "action": action, "pid": proc.pid, "command": command})
            while proc.poll() is None:
                if action in PHASES and checkpoint_error is None:
                    state_path = self.root / (action.upper() + "_RUN_STATE.json")
                    if state_path.exists():
                        phase_state = read(state_path)
                        if time.monotonic() - last_progress >= 30:
                            emit({"event": "PHASE_PROGRESS", "phase": action, "completed": len(phase_state["jobs"]),
                                  "running": len(phase_state["running"]), "unsubmitted": len(phase_state["unsubmitted"]),
                                  "charged_complete_child_CPU_s": phase_state["charged_complete_child_CPU_s"]})
                            last_progress = time.monotonic()
                        eligible = [job for job in phase_state["jobs"] if job["exit_code"] == 0 and job["index"] not in archived]
                        while len(eligible) >= EVERY:
                            group = eligible[:EVERY]
                            try:
                                self.capture(action, group, "four_closed_results", (stdout_path, stderr_path))
                                archived.update(job["index"] for job in group)
                                eligible = eligible[EVERY:]
                            except BaseException as error:
                                checkpoint_error = {"type": type(error).__name__, "message": str(error)}
                                emit({"event": "CHECKPOINT_FAILURE_NO_FURTHER_PHASES", "action": action, "failure": checkpoint_error,
                                      "current_coordinator_will_be_allowed_to_close_without_an_implicit_retry": True})
                                break
                time.sleep(5)
        record.update(exit_code=proc.returncode, status="CLOSED", checkpoint_failure=checkpoint_error)
        self.save()
        if action in PHASES:
            phase_state = read(self.root / (action.upper() + "_RUN_STATE.json"))
            eligible = [job for job in phase_state["jobs"] if job["exit_code"] == 0 and job["index"] not in archived]
            if checkpoint_error is None:
                while len(eligible) > EVERY:
                    self.capture(action, eligible[:EVERY], "four_closed_results", (stdout_path, stderr_path))
                    eligible = eligible[EVERY:]
                self.capture(action, eligible, "phase_closed", (stdout_path, stderr_path))
            require(proc.returncode == 0, "Frozen coordinator failed; no further phase will be launched")
            expected = phase_indices(self.root, action)
            require(phase_state["status"] == "COMPLETE" and not phase_state["running"] and not phase_state["unsubmitted"], "Coordinator phase did not close completely")
            require(sorted(job["index"] for job in phase_state["jobs"]) == expected and all(job["exit_code"] == 0 for job in phase_state["jobs"]), "Closed phase case census differs")
        require(checkpoint_error is None, "Checkpoint failure retained; no further phase will be launched")
        require(proc.returncode == 0, "Summarizer failed; no further phase will be launched")
        if action in ("close_calibration", "close_synthetic", "close_exposed"):
            phase = {"close_calibration": "primary_calibration", "close_synthetic": "qa", "close_exposed": "qa_exposed"}[action]
            self.capture(phase, [], action + "_summary", (stdout_path, stderr_path))
        emit({"event": "ACTION_COMPLETE", "action": action, "exit_code": proc.returncode})

    def main(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        require(not self.state_path.exists(), "Once-only scheduler state exists; no implicit rerun or resume")
        require(not list(self.root.glob("*_RUN_STATE.json")), "Numerical phase state already exists; refusing a second scheduler")
        require(not (self.root / "claims").exists(), "Numerical claims already exist; refusing a second scheduler")
        require(not (self.root / "results").exists(), "Result directory already exists; refusing a second scheduler")
        _, scope_sha = stage_admission(self.root, self.workers)
        self.state["scope_sha256"] = scope_sha
        atomic_json(self.state_path, self.state, exclusive=True)
        try:
            for action in ("primary_calibration", "close_calibration", "primary_validation", "qa", "close_synthetic"):
                self.run_action(action)
            synthetic = read(self.root / "results/SUMMARY.json")
            require(synthetic.get("integrity_gate") is True, "Synthetic integrity gate failed; exposed data remain closed")
            for action in ("exposed", "qa_exposed", "close_exposed"):
                self.run_action(action)
            require(read(self.root / "results/EXPOSED_SUMMARY.json").get("integrity_gate") is True, "Exposed integrity gate failed")
            self.state["status"] = "ALL_FROZEN_PHASES_CLOSED"
            self.save()
            emit({"event": "ALL_PHASES_CLOSED", "state": str(self.state_path), "checkpoint_count": len(self.state["checkpoints"])})
        except BaseException as error:
            self.state.update(status="STOPPED_RETAINED_NO_RETRY", failure={"type": type(error).__name__, "message": str(error)})
            self.save()
            emit({"event": "STOPPED_RETAINED_NO_RETRY", "failure": self.state["failure"], "state": str(self.state_path)})
            raise


def self_test():
    """Small transport fixtures only: no scientific arrays, RNG, or case runs."""
    checks = []
    with tempfile.TemporaryDirectory(prefix="seti_scheduler_fixture_") as temporary:
        base = Path(temporary)
        root, target = base / "fixture_stage", base / "checkpoints"
        root.mkdir()
        atomic_json(root / "SCOPE.json", {"code_pins": [], "resources": {"max_concurrent_workers": 8}})
        atomic_json(root / "GO.json", {"status": "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK", "scope_sha256": digest((root / "SCOPE.json").read_bytes())})
        atomic_json(root / "case_bank.json", [{"family": "calibration" if i < 63 else "null"} for i in range(205)])
        atomic_json(root / "real_baselines.json", [{} for _ in range(9)])
        stage_admission(root, 4)
        checks.append("admission_and_63_142_205_9_census")
        stage_admission(root, 8)
        try:
            stage_admission(root, 9)
        except ValueError:
            checks.append("worker_count_uses_frozen_scope_cap_8_and_rejects_9")
        else:
            raise AssertionError("Worker cap was not enforced")
        folder = root / "results/cases/C0000"
        folder.mkdir(parents=True)
        for name in REQUIRED_CASE_FILES:
            (folder / name).write_bytes(b"TRANSPORT_FIXTURE_ONLY\n")
        manifest = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in folder.iterdir()}
        atomic_json(folder / "artifact_manifest.json", manifest)
        commit = {"status": "COMPLETED_CASE_ONLY", "data_integrity_ok": True, "case_index": 0, "exposed": False,
                  "artifact_manifest_sha256": digest((folder / "artifact_manifest.json").read_bytes())}
        atomic_json(folder / "COMMITTED.json", commit)
        partial = root / "results/cases/C0001"
        partial.mkdir()
        (partial / "inputs.npz").write_bytes(b"LIVE_PARTIAL_MUST_NOT_BE_ARCHIVED")
        atomic_json(root / "PRIMARY_CALIBRATION_RUN_STATE.json", {"running": [{"index": 1}], "jobs": [{"index": 0, "exit_code": 0, "wait4_reaped": True}]})
        (root / "claims").mkdir()
        atomic_json(root / "claims/C0001.json", {"status": "CLAIMED_NOT_COMPLETE"})
        receipt = checkpoint(root, target, "primary_calibration", [{"index": 0, "exit_code": 0, "wait4_reaped": True}], 1, reason="fixture", announce=False)
        with zipfile.ZipFile(receipt["path"]) as archive:
            members = archive.namelist()
            require(not any("cases/C0001" in name for name in members), "Fixture partial case leaked")
            require(any("claims/C0001.json" in name for name in members), "Live claim snapshot is missing")
            checks.extend(("closed_manifest_bytes_roundtrip", "live_partial_arrays_excluded", "live_claim_snapshot_labelled"))
        qa_path = root / "results/qa/C0000.json"
        qa_path.parent.mkdir()
        atomic_json(qa_path, {"status": "PASS", "case_index": 0, "exposed": False,
                             "scope_sha256": digest((root / "SCOPE.json").read_bytes()),
                             "artifact_manifest_sha256": commit["artifact_manifest_sha256"],
                             "output_sha256": digest((folder / "output.json").read_bytes()),
                             "truth_sha256": digest((folder / "truth.json").read_bytes())})
        # The prior local ZIP can disappear after a verified remote save.  Its
        # receipt remains sufficient for a later QA transport reference.
        Path(receipt["path"]).unlink()
        qa_receipt = checkpoint(root, target, "qa", [{"index": 0, "exit_code": 0, "wait4_reaped": True}], 2,
                                reason="fixture_QA", announce=False, primary_checkpoint_index={"C0000": receipt})
        with zipfile.ZipFile(qa_receipt["path"]) as archive:
            require(not any("/cases/" in name for name in archive.namelist()), "QA duplicated producer case arrays")
            require("C0000" in json.loads(archive.read("CHECKPOINT_MANIFEST.json"))["referenced_closed_producer_payloads"], "QA producer reference absent")
            checks.extend(("QA_references_producer_without_array_duplication", "removed_local_checkpoint_ZIP_tolerated_via_receipt"))
        (folder / "inputs.npz").write_bytes(b"MODIFIED")
        try:
            checkpoint(root, target, "primary_calibration", [{"index": 0, "exit_code": 0, "wait4_reaped": True}], 3, reason="reject_tamper", announce=False)
        except ValueError:
            checks.append("changed_committed_payload_rejected")
        else:
            raise AssertionError("Modified payload was accepted")
        try:
            checkpoint(root, target, "primary_calibration", [{"index": 1, "exit_code": 0, "wait4_reaped": True}], 4, reason="reject_partial", announce=False)
        except FileNotFoundError:
            checks.append("uncommitted_case_rejected")
        else:
            raise AssertionError("Uncommitted case was accepted")
        require("--calibration-only" in command_for(root, "close_calibration", 4), "Calibration sequence command differs")
        require("--exposed" in command_for(root, "close_exposed", 4), "Exposed sequence command differs")
        require("--workers" in command_for(root, "qa", 4), "QA command must use frozen coordinator")
        checks.append("phase_commands_use_only_coordinator_and_summarizer")
    result = {"schema": "SETI_EXTERNAL_SCHEDULER_TRANSPORT_SELFTEST_V1", "status": "PASS", "checks": checks,
              "scientific_arrays_or_numerical_trials_created": False, "scheduler_sha256": digest(Path(__file__).read_bytes())}
    emit(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--checkpoints", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.root is not None and args.checkpoints is not None, "Both --root and --checkpoints are required")
    Runner(args.root.resolve(), args.checkpoints.resolve(), args.workers).main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
