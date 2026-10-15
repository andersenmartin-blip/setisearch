#!/usr/bin/env python3
"""Once-only checkpoint transport watcher. No numerical work or implicit retries."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def read(path):
    # Ready receipts/ACKs are created exclusively before their short JSON write
    # completes. Retry that read window only; never retry a Library mutation.
    deadline = time.monotonic() + 1.0
    while True:
        try:
            return json.loads(path.read_bytes())
        except json.JSONDecodeError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(.05, remaining))


def sha(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def save(path, value, exclusive=False):
    if exclusive:
        with path.open("xb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
    else:
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


class Watcher:
    def __init__(self, batch_root, scheduler_state, helper, record_script, directory_id,
                 *, start_batch=2, batch_size=20, poll_s=5, state_name="UPLOAD_WATCHER_STATE.json"):
        self.root = batch_root.resolve()
        self.scheduler_state = scheduler_state.resolve()
        self.helper, self.record_script = helper.resolve(), record_script.resolve()
        self.directory_id = directory_id
        self.batch_size, self.poll_s = batch_size, poll_s
        self.state_path = self.root / state_name
        self.identity_path = self.root / "SAVED_CHECKPOINT_INDEX_IDENTITY.json"
        self.state = {"schema": "SETI_ONCE_ONLY_CHECKPOINT_UPLOAD_WATCHER_V1", "status": "STARTED_ONCE",
                      "watcher_pid": os.getpid(), "batch_root": str(self.root), "helper": str(self.helper),
                      "record_script": str(self.record_script), "directory_id": directory_id,
                      "next_batch": start_batch, "attempts": [], "completed_batches": [],
                      "no_retry_or_replay_if_any_attempt_unknown_or_failed": True,
                      "scientific_code_or_trial_state_modified": False}

    def persist(self):
        save(self.state_path, self.state)

    def preflight(self):
        require(self.root.is_dir(), "Checkpoint/batch root is missing")
        require(self.helper.is_file() and self.record_script.is_file(), "Explicit helper and recorder paths are required")
        require(1 <= self.batch_size <= 20, "Ordered batches must contain at most 20 files")
        require(not self.state_path.exists(), "Once-only watcher state exists; no implicit restart")
        existing_batches = set()
        for path in self.root.glob("UPLOAD_BATCH_*"):
            match = re.match(r"UPLOAD_BATCH_(\d+)_", path.name)
            if match:
                existing_batches.add(int(match.group(1)))
        for batch in sorted(existing_batches):
            stem = f"UPLOAD_BATCH_{batch:04d}"
            closure = self.root / (stem + "_ACK.json")
            if not closure.is_file():
                # A human-operated earlier batch is complete only when every
                # ordered successful result already has its exact checkpoint
                # ACK. A bare request/result never authorizes replay.
                result = self.root / (stem + "_RESULT.json")
                require(result.is_file(), "Existing upload request has no result/ACK; unknown outcome must be reconciled: " + stem)
                rows = read(result).get("results")
                require(isinstance(rows, list) and 1 <= len(rows) <= 20, "Existing batch result is incomplete: " + stem)
                request = self.root / (stem + "_REQUEST.json")
                if request.exists():
                    expected = read(request)["uploads"]
                    require(len(expected) == len(rows) and all(item["local_path"] == row["local_path"] and item["purpose"] == row["purpose"] for item, row in zip(expected, rows)), "Existing batch order differs")
                sequences = []
                for row in rows:
                    require(row.get("status") == "succeeded" and row.get("local_metadata_applied") is True and row.get("purpose") == "create_library_file", "Existing batch contains an unresolved item")
                    local = Path(row["local_path"])
                    require(local.parent == self.root, "Existing batch path differs")
                    receipt = read(self.root / (local.name + ".receipt.json"))
                    ack_path = self.root / "SAVED_ACKS" / f"{receipt['sequence']:04d}.json"
                    require(ack_path.exists(), "Existing batch request has no checkpoint ACK; halt without replay")
                    ack = read(ack_path)
                    require(ack["library_file_id"] == row["library_file_id"] and ack["file_id"] == row["file_id"] and ack["current_version_number"] == row["current_version_number"], "Existing batch checkpoint ACK identity differs")
                    require(ack["archive_sha256"] == receipt["sha256"] and ack["archive_bytes"] == receipt["bytes"], "Existing batch archive pin differs")
                    sequences.append(receipt["sequence"])
                save(closure, {"batch": batch, "status": "MANUAL_ARCHIVES_ACKED_INDEX_WILL_BE_SAVED_BY_WATCHER",
                               "checkpoint_sequences": sequences, "archive_result_sha256": sha(result),
                               "adopted_without_any_upload_or_replay": True}, exclusive=True)
        self.state["next_batch"] = max([self.state["next_batch"]] + [batch + 1 for batch in existing_batches])
        for request in sorted(self.root.glob("INDEX_SAVE_*_REQUEST.json")):
            closure = request.with_name(request.name.replace("_REQUEST.json", "_ACK.json"))
            require(closure.is_file(), "Existing index request has no final ACK; unknown outcome must be reconciled: " + request.name)
        # An index identity must be explicitly retained across subsequent saves;
        # never create a second Library index if connected metadata already exists.
        if not self.identity_path.exists() and (self.root / "SAVED_CHECKPOINT_INDEX.json").exists():
            try:
                previous_id = os.getxattr(self.root / "SAVED_CHECKPOINT_INDEX.json", "user.library-file-id")
            except (OSError, AttributeError):
                previous_id = b""
            require(not previous_id, "Index has connected identity without a saved identity receipt; do not create a duplicate")
        save(self.state_path, self.state, exclusive=True)

    def receipts_and_acks(self):
        receipts = []
        seen = set()
        for path in self.root.glob("CHECKPOINT_*.zip.receipt.json"):
            receipt = read(path)
            sequence = receipt["sequence"]
            require(isinstance(sequence, int) and sequence > 0 and sequence not in seen, "Duplicate or invalid checkpoint sequence")
            seen.add(sequence)
            local = Path(receipt["path"])
            require(local.is_absolute() and local.parent == self.root, "Checkpoint path escapes the batch root")
            require(path.name == local.name + ".receipt.json", "Checkpoint receipt filename differs")
            require(receipt.get("local_archive_readback_verified") is True, "Checkpoint archive was not verified")
            receipt["_receipt_sha256"] = sha(path)
            receipts.append(receipt)
        receipts.sort(key=lambda item: item["sequence"])
        require([receipt["sequence"] for receipt in receipts] == list(range(1, len(receipts) + 1)),
                "Checkpoint receipt sequence has a gap; halt before any upload")
        acks = {}
        for path in sorted((self.root / "SAVED_ACKS").glob("*.json")) if (self.root / "SAVED_ACKS").exists() else []:
            ack = read(path)
            require(ack["sequence"] not in acks and ack["save_status"] == "succeeded", "Invalid or duplicate checkpoint ACK")
            acks[ack["sequence"]] = ack
        for receipt in receipts:
            if receipt["sequence"] in acks:
                ack = acks[receipt["sequence"]]
                require(ack["archive_sha256"] == receipt["sha256"] and ack["archive_bytes"] == receipt["bytes"], "Saved ACK differs from checkpoint archive pin")
                require(ack["original_local_receipt_sha256"] == receipt["_receipt_sha256"], "Saved ACK receipt binding differs")
        require(set(acks) <= {receipt["sequence"] for receipt in receipts}, "Saved ACK has no local checkpoint receipt")
        return receipts, acks

    def subprocess_once(self, stem, command, request):
        request_path = self.root / (stem + "_REQUEST.json")
        result_path = self.root / (stem + "_RESULT.json")
        stderr_path = self.root / (stem + "_STDERR.log")
        launch_path = self.root / (stem + "_LAUNCH.json")
        for path in (request_path, result_path, stderr_path, launch_path):
            require(not path.exists(), "Attempt path already exists; never replay: " + path.name)
        save(request_path, request, exclusive=True)
        attempt = {"stem": stem, "command": command, "request": str(request_path), "result": str(result_path),
                   "stderr": str(stderr_path), "status": "CLAIMED_BEFORE_LAUNCH", "request_sha256": sha(request_path)}
        self.state["attempts"].append(attempt)
        self.persist()
        with result_path.open("xb") as result, stderr_path.open("xb") as stderr:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=result, stderr=stderr, start_new_session=True)
            attempt.update(status="RUNNING", pid=proc.pid)
            save(launch_path, {**attempt, "watcher_pid": os.getpid()}, exclusive=True)
            self.persist()
            emit({"event": "UPLOAD_ATTEMPT_STARTED", "stem": stem, "pid": proc.pid})
            require(proc.stdin is not None, "One-shot stdin is required")
            proc.stdin.write(encoded(request))
            proc.stdin.close()
            while proc.poll() is None:
                time.sleep(self.poll_s)
        attempt.update(status="PROCESS_CLOSED", exit_code=proc.returncode, result_sha256=sha(result_path), stderr_sha256=sha(stderr_path))
        self.persist()
        require(proc.returncode == 0, "Upload helper returned nonzero; no retry or replay: " + stem)
        response = read(result_path)
        rows = response.get("results")
        require(isinstance(rows, list) and len(rows) == len(request["uploads"]), "Helper result count differs; outcome unresolved")
        for expected, row in zip(request["uploads"], rows):
            require(row.get("local_path") == expected["local_path"] and row.get("purpose") == expected["purpose"], "Helper order/path/purpose differs")
            require(row.get("status") == "succeeded" and row.get("local_metadata_applied") is True,
                    "Upload item failed or lacks local metadata; no retry or replay")
            require(isinstance(row.get("library_file_id"), str) and isinstance(row.get("file_id"), str), "Upload identity is missing")
            require(isinstance(row.get("current_version_number"), int), "Upload version is missing")
        return result_path, rows

    def save_index(self, batch, *, initial=False):
        path = self.root / "SAVED_CHECKPOINT_INDEX.json"
        require(path.is_file(), "Recorder did not produce the cumulative index")
        pin = sha(path)
        if self.identity_path.exists():
            identity = read(self.identity_path)
            item = {"local_path": str(path), "purpose": "replace_library_file", "library_file_id": identity["library_file_id"],
                    "expected_current_version": identity["current_version_number"],
                    "version_reason": "Persist cumulative SETI checkpoint index after archive batch " + str(batch)}
        else:
            identity = None
            item = {"local_path": str(path), "purpose": "create_library_file", "directory_id": self.directory_id,
                    "library_artifact_type": "other"}
        stem = ("INDEX_SAVE_INITIAL_" if initial else "INDEX_SAVE_") + f"{batch:04d}"
        result_path, rows = self.subprocess_once(stem, [sys.executable, str(self.helper)], {"uploads": [item]})
        row = rows[0]
        require(sha(path) == pin, "Cumulative index changed during its save")
        if identity is not None:
            require(row["library_file_id"] == identity["library_file_id"], "Index identity changed during replacement")
            require(row["current_version_number"] > identity["current_version_number"], "Index version did not advance")
        saved = {"library_file_id": row["library_file_id"], "file_id": row["file_id"],
                 "current_version_number": row["current_version_number"], "path": row["path"],
                 "local_index_sha256": pin, "result_path": str(result_path), "result_sha256": sha(result_path)}
        save(self.identity_path, saved)
        save(self.root / (stem + "_ACK.json"), saved, exclusive=True)
        return saved

    def archive_batch(self, receipts):
        batch = self.state["next_batch"]
        require(receipts and len(receipts) <= 20, "Invalid archive batch size")
        items = []
        for receipt in receipts:
            path = Path(receipt["path"])
            require(path.is_file() and not path.is_symlink(), "Pending checkpoint archive is missing or symlinked")
            require(path.stat().st_size == receipt["bytes"] and sha(path) == receipt["sha256"], "Pending checkpoint archive pin differs")
            items.append({"local_path": str(path), "purpose": "create_library_file", "directory_id": self.directory_id,
                          "library_artifact_type": "other"})
        stem = f"UPLOAD_BATCH_{batch:04d}"
        result_path, rows = self.subprocess_once(stem, [sys.executable, str(self.helper)], {"uploads": items})
        # This existing recorder owns ACK/index creation. Its invocation is also
        # exclusive and retained; do not manually synthesize replacement ACKs.
        record_stdout = self.root / (stem + "_RECORD_STDOUT.json")
        record_stderr = self.root / (stem + "_RECORD_STDERR.log")
        with record_stdout.open("xb") as stdout, record_stderr.open("xb") as stderr:
            proc = subprocess.Popen([sys.executable, str(self.record_script), str(result_path)], stdout=stdout, stderr=stderr)
            self.state["record_script_pid"] = proc.pid
            self.persist()
            while proc.poll() is None:
                time.sleep(self.poll_s)
        require(proc.returncode == 0, "Checkpoint recorder failed; retain evidence and stop")
        _, acks = self.receipts_and_acks()
        require(all(receipt["sequence"] in acks for receipt in receipts), "Recorder did not ACK every saved archive")
        saved_index = self.save_index(batch)
        closure = {"batch": batch, "checkpoint_sequences": [receipt["sequence"] for receipt in receipts],
                   "archive_result": str(result_path), "archive_result_sha256": sha(result_path), "saved_index": saved_index,
                   "status": "ARCHIVES_ACKED_AND_CUMULATIVE_INDEX_SAVED"}
        save(self.root / (stem + "_ACK.json"), closure, exclusive=True)
        self.state["completed_batches"].append(closure)
        self.state["next_batch"] += 1
        self.persist()
        emit({"event": "ARCHIVE_BATCH_SAVED", "batch": batch, "checkpoint_sequences": closure["checkpoint_sequences"],
              "index_library_file_id": saved_index["library_file_id"], "index_version": saved_index["current_version_number"]})

    def main(self):
        self.preflight()
        try:
            _, initial_acks = self.receipts_and_acks()
            if initial_acks and not self.identity_path.exists():
                self.state["initial_cumulative_index_save"] = self.save_index(self.state["next_batch"], initial=True)
                self.persist()
            while True:
                receipts, acks = self.receipts_and_acks()
                pending = [receipt for receipt in receipts if receipt["sequence"] not in acks]
                if pending:
                    self.archive_batch(pending[:self.batch_size])
                    continue
                scheduler = read(self.scheduler_state)
                if scheduler["status"] in ("ALL_FROZEN_PHASES_CLOSED", "STOPPED_RETAINED_NO_RETRY"):
                    expected = {receipt["sequence"] for receipt in scheduler.get("checkpoints", [])}
                    require(expected <= set(acks), "Terminal scheduler has an unacknowledged checkpoint")
                    if acks and not self.identity_path.exists():
                        self.save_index(self.state["next_batch"])
                    self.state.update(status="ALL_READY_CHECKPOINTS_SAVED", scheduler_terminal_status=scheduler["status"], saved_checkpoint_count=len(acks))
                    self.persist()
                    emit({"event": "ALL_READY_CHECKPOINTS_SAVED", "count": len(acks), "scheduler_status": scheduler["status"]})
                    return
                time.sleep(self.poll_s)
        except BaseException as error:
            self.state.update(status="STOPPED_UNKNOWN_OR_FAILED_UPLOAD_NO_RETRY", failure={"type": type(error).__name__, "message": str(error)})
            self.persist()
            emit({"event": "UPLOAD_WATCHER_STOPPED_NO_RETRY", "failure": self.state["failure"]})
            raise


def self_test():
    checks = []
    with tempfile.TemporaryDirectory(prefix="seti_upload_transport_fixture_") as temporary:
        root = Path(temporary)
        import threading
        incomplete_json = root / "incomplete_json_fixture.json"
        incomplete_json.write_bytes(b"")
        def finish_fixture_json():
            time.sleep(.05)
            incomplete_json.write_text('{"fixture": "complete"}\n')
        writer = threading.Thread(target=finish_fixture_json)
        writer.start()
        require(read(incomplete_json) == {"fixture": "complete"}, "Short incomplete JSON read was not retried")
        writer.join()
        checks.append("short_exclusive_creation_JSON_window_read_retry_only")
        helper = root / "fixture_helper.py"
        helper.write_text('import json,sys\np=json.load(sys.stdin);r=[]\nfor x in p["uploads"]:\n r.append({"local_path":x["local_path"],"purpose":x["purpose"],"status":"succeeded","local_metadata_applied":True,"library_file_id":x.get("library_file_id","fixture_index" if x["local_path"].endswith("SAVED_CHECKPOINT_INDEX.json") else "fixture_archive_"+x["local_path"].split("/")[-1]),"file_id":"fixture_file","path":"/fixture/"+x["local_path"].split("/")[-1],"current_version_number":x.get("expected_current_version",-1)+1})\njson.dump({"results":r},sys.stdout)\n')
        recorder = Path(__file__).resolve().parents[1] / "record_sixscan_checkpoint_upload.py"
        batch_root = root / "success"
        batch_root.mkdir()
        receipts = []
        for sequence in (1, 2):
            archive = batch_root / f"CHECKPOINT_{sequence:04d}_fixture.zip"
            archive.write_bytes(b"TRANSPORT_FIXTURE_NO_SCIENTIFIC_ARRAYS\n")
            receipt = {"sequence": sequence, "phase": "fixture", "new_complete_job_indices": [sequence], "path": str(archive),
                       "sha256": sha(archive), "bytes": archive.stat().st_size, "local_archive_readback_verified": True}
            save(batch_root / (archive.name + ".receipt.json"), receipt)
            receipts.append(receipt)
        scheduler = batch_root / "SCHEDULER_STATE.json"
        save(scheduler, {"status": "ALL_FROZEN_PHASES_CLOSED", "checkpoints": receipts})
        watcher = Watcher(batch_root, scheduler, helper, recorder, "fixture_directory", batch_size=1, poll_s=.01)
        watcher.main()
        identity = read(batch_root / "SAVED_CHECKPOINT_INDEX_IDENTITY.json")
        require(identity["library_file_id"] == "fixture_index" and identity["current_version_number"] == 1, "Index identity/version not retained")
        require(len(list((batch_root / "SAVED_ACKS").glob("*.json"))) == 2, "Fixture archive ACK count differs")
        require(read(batch_root / "INDEX_SAVE_0003_REQUEST.json")["uploads"][0]["expected_current_version"] == 0, "Replacement lacks expected version")
        checks += ["ordered_archive_batches_start_at_2", "archive_request_result_stderr_PID_retained", "recorder_ACKs_and_cumulative_index", "index_created_once_then_same_identity_expected_version_replacement", "terminal_scheduler_and_all_ACKs_close_watcher"]
        try:
            Watcher(batch_root, scheduler, helper, recorder, "fixture_directory", poll_s=.01).main()
        except ValueError:
            checks.append("second_watcher_start_rejected")
        else:
            raise AssertionError("Repeated watcher was accepted")
        manual = root / "manual"
        manual.mkdir()
        archive = manual / "CHECKPOINT_0001_fixture.zip"
        archive.write_bytes(b"MANUALLY_SAVED_TRANSPORT_FIXTURE")
        manual_receipt = {"sequence": 1, "phase": "fixture", "new_complete_job_indices": [], "path": str(archive),
                          "sha256": sha(archive), "bytes": archive.stat().st_size, "local_archive_readback_verified": True}
        save(manual / (archive.name + ".receipt.json"), manual_receipt)
        manual_result = manual / "UPLOAD_BATCH_0002_RESULT.json"
        save(manual_result, {"results": [{"local_path": str(archive), "purpose": "create_library_file", "status": "succeeded",
                                          "local_metadata_applied": True, "library_file_id": "fixture_manual_archive",
                                          "file_id": "fixture_file", "path": "/fixture/manual.zip", "current_version_number": 0}]})
        subprocess.run([sys.executable, str(recorder), str(manual_result)], check=True, capture_output=True)
        manual_scheduler = manual / "SCHEDULER_STATE.json"
        save(manual_scheduler, {"status": "ALL_FROZEN_PHASES_CLOSED", "checkpoints": [manual_receipt]})
        Watcher(manual, manual_scheduler, helper, recorder, "fixture_directory", poll_s=.01).main()
        require(read(manual / "UPLOAD_WATCHER_STATE.json")["next_batch"] == 3, "Did not advance beyond existing manual batch 2")
        require((manual / "INDEX_SAVE_INITIAL_0003_ACK.json").exists(), "Initial existing cumulative index was not saved")
        require(not (manual / "UPLOAD_BATCH_0003_REQUEST.json").exists(), "Already ACKed manual archive was uploaded again")
        checks += ["completed_manual_batch_2_adopted_without_replay_next_batch_3", "existing_cumulative_index_saved_before_new_archive_batch"]
        unknown = root / "unknown"
        unknown.mkdir()
        save(unknown / "UPLOAD_BATCH_0002_REQUEST.json", {"uploads": []})
        try:
            Watcher(unknown, scheduler, helper, recorder, "fixture_directory", poll_s=.01).main()
        except ValueError:
            checks.append("existing_unknown_request_halts_before_upload")
        else:
            raise AssertionError("Unknown previous upload was replayed")
        gap_root = root / "sequence_gap"
        gap_root.mkdir()
        gap_archive = gap_root / "CHECKPOINT_0002_fixture.zip"
        gap_archive.write_bytes(b"SEQUENCE_GAP_TRANSPORT_FIXTURE")
        save(gap_root / (gap_archive.name + ".receipt.json"), {
            "sequence": 2, "phase": "fixture", "new_complete_job_indices": [], "path": str(gap_archive),
            "sha256": sha(gap_archive), "bytes": gap_archive.stat().st_size, "local_archive_readback_verified": True})
        try:
            Watcher(gap_root, scheduler, helper, recorder, "fixture_directory", poll_s=.01).main()
        except ValueError as error:
            require("sequence has a gap" in str(error), "Gap rejected for an unexpected reason")
            require(not list(gap_root.glob("UPLOAD_BATCH_*_REQUEST.json")), "Sequence gap triggered an upload")
            require(not list(gap_root.glob("INDEX_SAVE_*_REQUEST.json")), "Sequence gap triggered an index save")
            checks.append("checkpoint_sequence_gap_halts_before_archive_or_index_upload")
        else:
            raise AssertionError("Checkpoint sequence gap was accepted")
        failure_helper = root / "fixture_failure_helper.py"
        failure_helper.write_text('import json,sys\np=json.load(sys.stdin);json.dump({"results":[{"local_path":x["local_path"],"purpose":x["purpose"],"status":"failed","local_metadata_applied":False} for x in p["uploads"]]},sys.stdout)\n')
        failed_root = root / "failed"
        failed_root.mkdir()
        archive = failed_root / "CHECKPOINT_0001_fixture.zip"
        archive.write_bytes(b"TRANSPORT_ONLY")
        receipt = {"sequence": 1, "phase": "fixture", "new_complete_job_indices": [], "path": str(archive), "sha256": sha(archive),
                   "bytes": archive.stat().st_size, "local_archive_readback_verified": True}
        save(failed_root / (archive.name + ".receipt.json"), receipt)
        try:
            Watcher(failed_root, scheduler, failure_helper, recorder, "fixture_directory", poll_s=.01).main()
        except ValueError:
            require(read(failed_root / "UPLOAD_WATCHER_STATE.json")["status"] == "STOPPED_UNKNOWN_OR_FAILED_UPLOAD_NO_RETRY", "Failure state absent")
            require(not (failed_root / "UPLOAD_BATCH_0002_ACK.json").exists(), "Failed upload was ACKed")
            checks.append("per_item_failure_stops_without_ACK_retry_or_index_save")
        else:
            raise AssertionError("Failed item was accepted")
    result = {"status": "PASS", "schema": "SETI_UPLOAD_WATCHER_TRANSPORT_FIXTURE_V1", "checks": checks,
              "real_library_uploads": 0, "numerical_trials": 0, "watcher_sha256": sha(Path(__file__))}
    emit(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", type=Path)
    parser.add_argument("--scheduler-state", type=Path)
    parser.add_argument("--helper", type=Path)
    parser.add_argument("--record-script", type=Path)
    parser.add_argument("--directory-id")
    parser.add_argument("--start-batch", type=int, default=2)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(all((args.batch_root, args.scheduler_state, args.helper, args.record_script, args.directory_id)), "All explicit transport paths and directory-id are required")
    Watcher(args.batch_root, args.scheduler_state, args.helper, args.record_script, args.directory_id, start_batch=args.start_batch).main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
