"""Bounded in-memory witnesses for unchanged acquisition journal replay.

This script imports the frozen source modules with bytecode writes disabled.
Path.read_bytes is patched only for one nonexistent journal path; no source,
session store, runtime or scientific inputs are changed. Recomputed honest
chains show semantic acceptance, not a hash bypass. Persisted witnesses are
audit artifacts and grant no request, retry, scientific or control authority.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
MAX_WITNESS_BYTES = 64 * 1024
MAX_LINE_BYTES = 16 * 1024
MAX_EVENTS = 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def file_pin(path):
    payload = path.read_bytes()
    return {"path": str(path), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def write_exclusive(path, payload):
    with path.open("xb") as stream:
        offset = 0
        while offset < len(payload):
            written = stream.write(payload[offset:])
            if not written:
                raise OSError("short audit artifact write")
            offset += written
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.read_bytes() != payload:
        raise OSError("audit artifact readback differs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    sys.path.insert(0, str(root / "src"))
    socket_attempts = []

    def deny_socket(event, arguments):
        if event.startswith("socket."):
            socket_attempts.append(event)
            raise RuntimeError("socket operation denied in replay audit")

    sys.addaudithook(deny_socket)
    from seti_repeater import acquisition_radio as acquisition

    dependencies = sorted({Path(module.__file__).resolve()
                           for name, module in list(sys.modules.items())
                           if name.startswith("seti_repeater")
                           and getattr(module, "__file__", None)})
    before = [file_pin(path) for path in dependencies]
    reservation = {
        "ordinal": 0,
        "session_id": "a972db9b-c3f8-45c8-bc69-6ff5e0ab0a41",
        "prior_ledger_sha256": "1" * 64,
        "reserved_limits": {"max_requests": 10, "max_bytes": 100,
                            "max_seconds": 60},
        "created_utc": "2026-10-03T19:00:00+00:00",
    }
    base = [
        {"type": "session_start", "reservation": reservation,
         "ledger_sha256": "2" * 64, "publication_revision": "valid",
         "publication_location": {"kind": "local-engineering"}},
        {"type": "scope", "scope": {
            "scan": "epoch1_on", "window": "calibration",
            "url": "https://epoch1_on.invalid/source.h5",
            "source_definition_sha256": "3" * 64,
            "extraction": [0, 2]}},
        {"type": "reserve", "attempt": 1, "reserved_bytes": 5,
         "elapsed_seconds": 1.0},
        {"type": "accepted_body", "attempt": 1, "bytes": 4},
        {"type": "session_end", "outcome": "completed",
         "elapsed_seconds": 2.0},
    ]
    cases = [("baseline", copy.deepcopy(base), False)]
    changed = copy.deepcopy(base)
    changed[2]["attempt"] = True
    changed[3]["attempt"] = True
    cases.append(("bool_attempt_alias", changed, False))
    changed = copy.deepcopy(base)
    changed[2]["elapsed_seconds"] = -100
    changed[4]["elapsed_seconds"] = 9999
    cases.append(("negative_reserve_and_over_cap_end_time", changed, False))
    changed = copy.deepcopy(base)
    changed[0]["publication_location"] = {"kind": "github"}
    changed[0]["ledger_sha256"] = "bad"
    cases.append(("unbound_session_start_metadata", changed, False))
    changed = copy.deepcopy(base)
    changed[1]["scope"] = {"url": "https://example.org/telescope.h5"}
    cases.append(("unbound_scope", changed, False))
    changed = copy.deepcopy(base)
    changed[2]["extra"] = "x"
    cases.append(("extra_reserve_field", changed, False))
    cases.append(("noncanonical_whitespace", copy.deepcopy(base), True))
    cases.append(("completed_without_any_requests",
                  [copy.deepcopy(base[0]), copy.deepcopy(base[-1])], False))
    output.mkdir(parents=True, exist_ok=False)
    results = []
    mocked_path = Path("/candidate-read-only-journal.invalid")
    for ordinal, (name, events, noncanonical) in enumerate(cases):
        head = acquisition.ZERO
        lines = []
        if not 0 < len(events) <= MAX_EVENTS:
            raise ValueError("audit event bound exceeded")
        for index, event in enumerate(events):
            record = {"index": index, "previous_sha256": head, "event": event}
            record["sha256"] = acquisition.digest(record)
            head = record["sha256"]
            line = (json.dumps(record, sort_keys=True,
                               separators=(", ", ": "), allow_nan=False).encode()
                    if noncanonical else acquisition.encode(record))
            if len(line) > MAX_LINE_BYTES:
                raise ValueError("audit line bound exceeded")
            lines.append(line)
        payload = b"\n".join(lines) + b"\n"
        if len(payload) > MAX_WITNESS_BYTES:
            raise ValueError("audit witness bound exceeded")
        path = output / f"{ordinal:02d}_{name}.jsonl"
        write_exclusive(path, payload)

        def read_only_witness(self):
            if self != mocked_path:
                raise ValueError("unexpected filesystem read in replay witness")
            return payload

        try:
            with patch.object(Path, "read_bytes", read_only_witness):
                result = acquisition.read_journal(
                    mocked_path, expected_head=head,
                    expected_reservation=reservation)
            disposition = "ACCEPT"
            error = None
        except BaseException as exception:
            result = None
            disposition = "REFUSE"
            error = repr(exception)
        results.append({
            "ordinal": ordinal, "case": name, "witness": file_pin(path),
            "expected_head": head,
            "expected_reservation": copy.deepcopy(reservation),
            "original_replay_disposition": disposition,
            "original_replay_result": result, "error": error,
            "candidate_strict_stage_replay_expected": (
                "ACCEPT_IF_EXTERNAL_BINDINGS_MATCH" if name == "baseline" else "REFUSE"),
            "honestly_recomputed_chain": True,
        })
    after = [file_pin(path) for path in dependencies]
    if before != after:
        raise AssertionError("frozen imported source files changed")
    if socket_attempts:
        raise AssertionError("unexpected socket attempt")
    if any(case["original_replay_disposition"] != "ACCEPT" for case in results):
        raise AssertionError("original acceptance witness did not reproduce")
    report = {
        "schema": "radio-source-session-original-replay-audit-v1",
        "status": "PASS", "authority": "synthetic in-memory audit only",
        "probe": file_pin(Path(__file__).resolve()),
        "original_module": file_pin(Path(acquisition.__file__).resolve()),
        "imported_source_files_before": before,
        "imported_source_files_after": after,
        "source_file_bytes_unchanged": True,
        "case_count": len(results), "cases": results,
        "bounds": {"max_witness_bytes": MAX_WITNESS_BYTES,
                   "max_line_bytes": MAX_LINE_BYTES, "max_events": MAX_EVENTS},
        "socket_attempts": socket_attempts,
        "scientific_execution_authorized": False,
        "execution_restart_authorized": False, "control_activation": False,
        "telescope_reads": 0, "runtime_modifications": 0,
        "limitations": [
            "Read-only replay is evidence validation, not execution permission.",
            "Semantic witnesses do not bypass a SHA256 chain; their chains are recomputed.",
            "No real network, hostile filesystem, resource lifetime or hosted transport was tested.",
        ],
    }
    write_exclusive(output / "result.json", canonical(report) + b"\n")
    print(json.dumps({"status": report["status"], "cases": len(results),
                      "result": str(output / "result.json"),
                      "original_module_sha256": report["original_module"]["sha256"]}))


if __name__ == "__main__":
    main()
