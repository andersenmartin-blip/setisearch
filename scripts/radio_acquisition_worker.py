#!/usr/bin/env python3
"""Connector-backed reservation demonstration; telescope HTTP is always mocked.

The parent answers one JSON-line RPC at a time using the authorized GitHub
connector. read fetches branch HEAD then the ledger at that exact commit.
publish appends one reservation using a commit with that HEAD as parent and
a non-forced ref update. A fresh read must confirm publication before HTTP.
No credential, token, shell command or arbitrary URL is accepted over stdin.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
import termios
from unittest.mock import patch
from seti_repeater import acquisition_radio as acquisition
from seti_repeater import transport_radio as transport
from seti_repeater import http_range_v0p6 as ranges

LOCATION = {"kind": "github", "repository": "andersenmartin-blip/setisearch",
            "branch": "m43-support-qualification",
            "path": "results_radio_acquisition_2026-09-26/published_fixture_ledger.json"}
SESSION = {"max_requests": 3, "max_bytes": 100, "max_seconds": 30}
URL = "https://fixture.invalid/synthetic-object.h5"


class ConnectorStore:
    def __init__(self, location):
        self.location, self.sequence = dict(location), 0

    def rpc(self, action, payload):
        self.sequence += 1
        print(json.dumps({"rpc": action, "sequence": self.sequence, "location": self.location, **payload}), flush=True)
        line = sys.stdin.readline()
        if not line:
            raise OSError("publication controller disconnected")
        reply = json.loads(line)
        if reply.get("sequence") != self.sequence or reply.get("ok") is not True:
            raise OSError("publication controller rejected request: "+str(reply.get("error", "invalid reply")))
        return reply

    def read(self):
        reply = self.rpc("read", {})
        if not re.fullmatch("[0-9a-f]{40}", reply["revision"]):
            raise ValueError("immutable Git revision required")
        document = json.loads(reply["content"])
        acquisition.validate_ledger(document, acquisition.digest(document))
        return acquisition.Checkpoint(document, reply["revision"], self.location)

    def publish(self, expected_revision, expected_sha256, document):
        reply = self.rpc("publish", {"expected_revision": expected_revision,
            "expected_ledger_sha256": expected_sha256, "document": document})
        if not re.fullmatch("[0-9a-f]{40}", reply["revision"]):
            raise ValueError("publication commit identity required")


class FixtureResponse(io.BytesIO):
    def __init__(self, data, status, headers):
        super().__init__(data)
        self.status, self.headers = status, headers

    def geturl(self):
        return URL


def main():
    if sys.stdin.isatty():
        settings = termios.tcgetattr(sys.stdin.fileno())
        settings[3] &= ~(termios.ECHO | termios.ECHONL)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, settings)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--mode", choices=("crash", "complete", "exhausted"), required=True)
    args = parser.parse_args()
    store = ConnectorStore(LOCATION)
    before = store.read()
    calls = []
    try:
        budget = acquisition.start_session(store, expected_revision=before.revision,
            expected_ledger_sha256=before.sha256, session_limits=SESSION, directory=args.directory/"session")
    except ValueError as error:
        if args.mode != "exhausted" or "cumulative reservation budget exhausted" not in str(error):
            raise
        print(json.dumps({"event": "expected_budget_stop", "reason": str(error),
                          "source_http_calls": 0, "telescope_requests": 0}), flush=True)
        return
    if args.mode == "exhausted":
        raise AssertionError("exhausted ledger unexpectedly issued a session")
    budget.bind_scope({"domain": "synthetic-HTTP", "scan": "fixture", "window": "fixture", "url": URL})
    def fake(request, timeout):
        # This assertion executes inside the actual transport's network boundary.
        replay = acquisition.read_journal(budget.journal.path, expected_head=budget.journal.head,
                                          expected_reservation=budget.reservation)
        assert replay["reserved_attempts"] == len(calls)+1
        calls.append(request.get_method())
        if request.get_method() == "HEAD":
            return FixtureResponse(b"", 200, {"Content-Length": "1000", "ETag": '"fixture"', "Accept-Ranges": "bytes"})
        return FixtureResponse(b"abcd", 206, {"Content-Length": "4", "ETag": '"fixture"',
            "Content-Range": "bytes 10-13/1000", "Content-Encoding": "identity"})
    with patch.object(transport, "open_response", side_effect=fake):
        identity = transport.live_identity(URL, budget)
        with transport.RadioMirror(args.directory/"mirror", identity, budget) as mirror:
            assert mirror._request(ranges.ByteRange(10, 14)) == b"abcd"
    if args.mode == "complete":
        budget.close("completed")
    report = {"event": "fixture_complete", "mode": args.mode, "budget": budget.record(),
              "journal_path": str(budget.journal.path), "mocked_http_calls": calls, "telescope_requests": 0}
    print(json.dumps(report), flush=True)
    if args.mode == "crash":
        os._exit(73)  # no Python finally/destructor/session-end event


if __name__ == "__main__":
    main()
