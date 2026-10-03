"""Independent bounded semantic review of the frozen strict journal reader.

No session or budget is constructed, no store is published, and no request is
dispatched. The checkpoint and events are fresh in-memory engineering test
values. Every witness uses an honestly recomputed SHA256 chain; saved witnesses
and reports are read-only audit evidence, not executable reservation authority.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
MAX_FILE_BYTES = 64 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def pin(path):
    data = Path(path).read_bytes()
    return {"path": str(Path(path).resolve()), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def save(path, data):
    if not 0 < len(data) <= MAX_FILE_BYTES:
        raise ValueError("independent audit artifact bound exceeded")
    with path.open("xb") as handle:
        written = handle.write(data)
        if written != len(data):
            raise OSError("short audit evidence write")
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.read_bytes() != data:
        raise AssertionError("audit evidence readback differs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--trusted-store-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    store_path = Path(args.store).resolve()
    store_before = pin(store_path)
    if store_before["sha256"] != args.trusted_store_sha256:
        raise ValueError("strict candidate module differs from independent pin")
    socket_attempts = []

    def deny_socket(event, arguments):
        if event.startswith("socket."):
            socket_attempts.append(event)
            raise RuntimeError("socket denied in independent strict review")

    sys.addaudithook(deny_socket)
    spec = importlib.util.spec_from_file_location("independently_pinned_session_store", store_path)
    store = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = store
    spec.loader.exec_module(store)
    acquisition = store.acquisition
    original_before = pin(acquisition.__file__)
    genesis = acquisition.genesis("3" * 64, "4" * 64,
        {"max_requests": 100, "max_bytes": 1000, "max_seconds": 120})
    reservation = {
        "ordinal": 0, "session_id": "a972db9b-c3f8-45c8-bc69-6ff5e0ab0a41",
        "prior_ledger_sha256": acquisition.digest(genesis),
        "reserved_limits": {"max_requests": 10, "max_bytes": 100, "max_seconds": 60},
        "created_utc": "2026-10-03T19:00:00+00:00",
    }
    document = copy.deepcopy(genesis)
    document["reservations"].append(reservation)
    checkpoint = acquisition.Checkpoint(document, "engineering-sqlite:1", {
        "kind": "local-engineering-sqlite", "path": "/candidate-read-only-store.invalid",
        "store_id": "096f5a7f-b101-4fbf-b1f1-74d037f9654e"})
    scope = {"scan": "epoch1_on", "window": "calibration",
             "url": "https://epoch1_on.invalid/source.h5",
             "source_definition_sha256": "5" * 64, "extraction": [0, 2]}
    base = [
        {"type": "session_start", "reservation": reservation,
         "ledger_sha256": checkpoint.sha256, "publication_revision": checkpoint.revision,
         "publication_location": checkpoint.location},
        {"type": "scope", "scope": scope},
        {"type": "reserve", "attempt": 1, "reserved_bytes": 5, "elapsed_seconds": 1.0},
        {"type": "accepted_body", "attempt": 1, "bytes": 4},
        {"type": "session_end", "outcome": "completed", "elapsed_seconds": 2.0},
    ]
    cases = [("positive_semantic_baseline", copy.deepcopy(base), "canonical", "ACCEPT")]

    def changed(name, mutate, mode="canonical", expected="REFUSE"):
        events = copy.deepcopy(base)
        mutate(events)
        cases.append((name, events, mode, expected))

    changed("bool_attempt_alias", lambda events: events[2].update(attempt=True))
    changed("negative_reserve_time", lambda events: events[2].update(elapsed_seconds=-100))
    changed("over_cap_end_time", lambda events: events[-1].update(elapsed_seconds=9999))
    changed("positive_time_regression", lambda events: events[-1].update(elapsed_seconds=0.5))
    changed("unbound_start_metadata", lambda events: events[0].update(
        ledger_sha256="bad", publication_location={"kind": "github"}))
    changed("unbound_real_service_scope", lambda events: events[1].update(
        scope={"url": "https://example.org/telescope.h5"}))
    changed("extra_reserve_field", lambda events: events[2].update(extra="x"))
    changed("noncanonical_whitespace", lambda events: None, "whitespace")
    changed("noncanonical_crlf", lambda events: None, "crlf")
    changed("duplicate_json_field", lambda events: None, "duplicate")
    changed("torn_tail", lambda events: None, "torn")
    changed("completed_without_any_requests", lambda events: events.__setitem__(
        slice(None), [events[0], events[-1]]))
    changed("floating_body_count_alias", lambda events: events[3].update(bytes=4.0))
    changed("body_double_accept", lambda events: events.insert(4, copy.deepcopy(events[3])))
    changed("events_after_close", lambda events: events.append(copy.deepcopy(events[2])))

    def pending(events):
        events.insert(-1, {"type": "reserve", "attempt": 2,
                           "reserved_bytes": 2, "elapsed_seconds": 1.5})

    changed("completed_pending_get", pending)

    def superseded(events):
        pending(events)
        events.insert(-1, {"type": "reserve", "attempt": 3,
                           "reserved_bytes": 0, "elapsed_seconds": 1.6})

    changed("completed_superseded_pending_get", superseded)

    def error_pending(events):
        pending(events)
        events[-1]["outcome"] = "error"

    changed("closed_error_pending_get_remains_evidence", error_pending, expected="ACCEPT")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    save(output / "independent-checkpoint.json", canonical({
        "document": checkpoint.document, "revision": checkpoint.revision,
        "location": checkpoint.location}))
    save(output / "independent-reservation.json", canonical(reservation))
    save(output / "independent-scopes.json", canonical([scope]))
    results = []
    for ordinal, (name, events, mode, expected) in enumerate(cases):
        head, lines = acquisition.ZERO, []
        for index, event in enumerate(events):
            record = {"index": index, "previous_sha256": head, "event": event}
            record["sha256"] = acquisition.digest(record)
            head = record["sha256"]
            line = (json.dumps(record, sort_keys=True, separators=(", ", ": ")).encode()
                    if mode == "whitespace" else acquisition.encode(record))
            if mode == "duplicate" and index == 0:
                line = line.replace(b'"index":0', b'"index":0,"index":0', 1)
            lines.append(line)
        payload = (b"\r\n" if mode == "crlf" else b"\n").join(lines)
        payload += b"\r\n" if mode == "crlf" else b"\n"
        if mode == "torn":
            payload = payload[:-1]
        witness = output / f"{ordinal:02d}_{name}.jsonl"
        save(witness, payload)
        try:
            result = store.strict_read_journal(witness, expected_checkpoint=checkpoint,
                expected_reservation=reservation, expected_head=head, ordered_scopes=[scope],
                require_closed=True)
            observed, error = "ACCEPT", None
        except Exception as exception:
            observed, error, result = "REFUSE", repr(exception), None
        results.append({"ordinal": ordinal, "case": name, "expected": expected,
                        "observed": observed, "pass": expected == observed,
                        "witness": pin(witness), "expected_head": head,
                        "error": error, "result": result})
    store_after = pin(store_path)
    original_after = pin(acquisition.__file__)
    report = {
        "schema": "radio-session-independent-strict-replay-review-v1",
        "status": "PASS" if all(r["pass"] for r in results) else "FAILED",
        "probe": pin(__file__), "store_before": store_before, "store_after": store_after,
        "original_before": original_before, "original_after": original_after,
        "reviewed_module_bytes_unchanged": store_before == store_after and original_before == original_after,
        "case_count": len(results), "cases": results,
        "socket_attempts": socket_attempts, "source_session_created": False,
        "reservation_published": False, "request_permission_restored": False,
        "telescope_reads": 0, "controls_invoked": False, "scientific_admission": False,
        "scope": "bounded semantic replay of invented in-memory engineering values",
        "limitations": ["No hosted durability or source/receiver execution is qualified by this review.",
                        "Hostile concurrent filesystem ownership and complete resource lifetime remain outside scope."]}
    save(output / "result.json", canonical(report) + b"\n")
    print(json.dumps({"status": report["status"], "case_count": len(results),
                      "passed": sum(r["pass"] for r in results),
                      "result": str(output / "result.json")}))
    if not report["reviewed_module_bytes_unchanged"] or socket_attempts or report["status"] != "PASS":
        raise AssertionError("independent strict replay review failed")


if __name__ == "__main__":
    main()
