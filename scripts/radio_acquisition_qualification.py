#!/usr/bin/env python3
"""Run local acquisition tests and audit retained publication-demo evidence.

Reproduction makes no GitHub mutations and no telescope requests. The original
publication demonstration used the separately recorded controller/worker runs.
"""
import io
import json
from pathlib import Path
import platform
import sys
import unittest
from seti_repeater import acquisition_radio as acquisition
from seti_repeater import source_radio
from seti_repeater import source_m43h as rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results_radio_acquisition_2026-09-26"
PINS = ["src/seti_repeater/acquisition_radio.py", "scripts/radio_acquisition_fixture.py",
        "scripts/radio_acquisition_worker.py", "scripts/radio_acquisition_controller.js",
        "scripts/radio_acquisition_qualification.py", "tests/test_radio_acquisition.py",
        "config/radio_acquisition_engineering_20260926.json", *source_radio.IMPLEMENTATION_PATHS]


def read(name):
    return json.loads((OUT/name).read_text())


def write(name, value):
    path = OUT/name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")
    if json.loads(path.read_text()) != value:
        raise ValueError("written evidence changed")


def audit_publication():
    cfg = json.loads((ROOT/"config/radio_acquisition_engineering_20260926.json").read_text())
    demo = read("publication_demo.json")
    transcript = read("publication_transcript.json")
    ledger = read("published_fixture_ledger.json")
    genesis = read("fixture_genesis.json")
    expected = acquisition.genesis(rows.file_hash(ROOT/"config/radio_acquisition_engineering_20260926.json"),
                                   acquisition.digest(cfg["source_inventory"]), cfg["total_limits"])
    assert genesis == expected
    cases = {c["mode"]: c for c in demo["cases"]}
    assert cases["crash"]["exit_code"] == 73 and cases["complete"]["exit_code"] == 0
    assert cases["exhausted"]["exit_code"] == 0
    assert cases["exhausted"]["result"]["event"] == "expected_budget_stop"
    assert cases["exhausted"]["result"]["source_http_calls"] == 0
    replayed = {}
    for index, mode in enumerate(("crash", "complete")):
        result = cases[mode]["result"]
        replay = acquisition.read_journal(OUT/("process_"+mode+".journal.jsonl"),
            expected_head=result["budget"]["journal_head_sha256"], expected_reservation=ledger["reservations"][index])
        assert replay["closed"] is (mode == "complete")
        assert (replay["reserved_attempts"], replay["reserved_bytes"], replay["accepted_bytes"]) == (2, 5, 4)
        assert result["mocked_http_calls"] == ["HEAD", "GET"] and result["telescope_requests"] == 0
        replayed[mode] = {k: v for k, v in replay.items() if k != "events"}
    state = acquisition.validate_ledger(ledger, cases["complete"]["result"]["budget"]["ledger_sha256"])
    assert state["charged_limits"] == cfg["total_limits"]
    assert all(value == 0 for value in state["remaining_limits"].values())
    prior_document = genesis
    prior_revision = demo["engineering_freeze_commit"]
    publications = []
    for worker in transcript["workers"]:
        for exchange in worker["exchanges"]:
            request, reply = exchange["request"], exchange["reply"]
            assert reply["ok"] is True and request["sequence"] == reply["sequence"]
            if request["rpc"] == "read":
                assert json.loads(reply["content"]) == prior_document
                assert reply["revision"] == prior_revision
            else:
                assert request["rpc"] == "publish" and worker["mode"] != "exhausted"
                assert request["expected_revision"] == prior_revision
                assert request["expected_ledger_sha256"] == acquisition.digest(prior_document)
                assert request["document"]["reservations"][:-1] == prior_document["reservations"]
                assert reply["revision"] != prior_revision
                prior_document, prior_revision = request["document"], reply["revision"]
                acquisition.validate_ledger(prior_document, acquisition.digest(prior_document))
                publications.append(prior_revision)
    assert prior_document == ledger and prior_revision == demo["final_revision"]
    assert len(publications) == 2 and demo["stale_publication_refusal"]["published"] is False
    return {"status": "RETAINED_PUBLICATION_DEMO_AUDIT_PASS", "separate_processes": 3,
            "confirmed_reservation_commits": publications, "journal_replays": replayed,
            "cumulative": state, "mocked_source_requests": 4, "accepted_fixture_bytes": 8,
            "telescope_requests": 0, "new_network_requests_by_this_audit": 0}


def main():
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT/"tests"))
    import test_radio_acquisition as tests
    tests.EVIDENCE.clear()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    (OUT/"test.log").write_text(stream.getvalue())
    write("local_test_evidence.json", tests.EVIDENCE)
    audit = audit_publication()
    write("publication_audit.json", audit)
    contract = "config/radio_hd1461_source_preparation_20260926.json"
    _, readiness = source_radio.load_contract(ROOT, contract, rows.file_hash(ROOT/contract))
    assert readiness["status"] == "BLOCKED"
    write("source_readiness.json", readiness)
    report = {"status": "ACQUISITION_CONTINUITY_CHECKS_PASS" if result.wasSuccessful() else "FAIL",
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "python": platform.python_version(), "platform": sys.platform,
              "publication_audit": audit, "source_readiness": readiness["status"],
              "telescope_requests": 0, "scientific_detector_or_source_qualification": False,
              "implementation_sha256": {p: rows.file_hash(ROOT/p) for p in PINS},
              "evidence_sha256": {p.name: rows.file_hash(p) for p in sorted(OUT.iterdir())
                                  if p.is_file() and p.name != "qualification.json"}}
    write("qualification.json", report)
    print(stream.getvalue(), end="")
    print(json.dumps({k: report[k] for k in ("status", "tests_run", "failures", "errors", "source_readiness", "telescope_requests")}))
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
