"""Retain typed-boundary/ownership findings without live ledger activation."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import socket
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results_radio_connector_2026-09-27"
CONFIG = "config/radio_connector_20260927.json"
SOURCES = ["src/seti_repeater/connector_rehearsal_radio.py", "scripts/radio_connector_fixture.py",
           "scripts/radio_connector_qualification.py", "tests/test_radio_connector.py"]
OWN = [CONFIG, *SOURCES, "RADIO_CONNECTOR_2026-09-27_PROTOCOL.md", "RADIO_CONNECTOR_2026-09-27_RESULT.md"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n")


def check_inputs(cfg):
    for path, expected in cfg["input_sha256"].items():
        if sha((ROOT/path).read_bytes()) != expected:
            raise ValueError("frozen input changed: "+path)


def main():
    start = time.perf_counter()
    cfg = json.loads((ROOT/CONFIG).read_text())
    check_inputs(cfg)
    OUT.mkdir(exist_ok=True)
    n = 1
    while (OUT/f"qualification_{n:02d}").exists(): n += 1
    attempt = OUT/f"qualification_{n:02d}"
    attempt.mkdir()
    sources = {path: (ROOT/path).read_text() for path in SOURCES}
    (attempt/"source_snapshot.json.gz").write_bytes(gzip.compress(json.dumps(sources,sort_keys=True).encode(), mtime=0))
    sys.path.insert(0, str(ROOT/"tests"))
    from test_radio_connector import ConnectorTests
    ConnectorTests.evidence = {}
    log = io.StringIO()
    with patch.object(socket, "socket", side_effect=AssertionError("network forbidden during fixtures")):
        tested = unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConnectorTests))
    (attempt/"qualification.log").write_text(log.getvalue())
    evidence = ConnectorTests.evidence
    raw = json.dumps(evidence,sort_keys=True,separators=(",", ":"),allow_nan=False).encode()
    archive = attempt/"integration_evidence.json.gz"
    archive.write_bytes(gzip.compress(raw,mtime=0))
    recovered = json.loads(gzip.decompress(archive.read_bytes()))
    objects, journals = 0, 0
    for case in recovered.values():
        for payload in case["journal_files_base64"].values():
            base64.b64decode(payload,validate=True)
            journals += 1
        for service in case["services"]:
            if service["git_remotes"] or service["real_network_requests"]:
                raise ValueError("fixture used a remote")
            for obj in service["git_objects"]:
                data = base64.b64decode(obj["content_base64"],validate=True)
                identity = hashlib.sha1(obj["type"].encode()+b" "+str(len(data)).encode()+b"\0"+data).hexdigest()
                if identity != obj["sha"]: raise ValueError("Git object integrity failure")
                objects += 1
    runtime = {"python": platform.python_version(), "platform": platform.platform(),
        "source_sha256": {p:sha(s.encode()) for p,s in sources.items()}, "socket_creation_disabled": True,
        "elapsed_seconds": time.perf_counter()-start}
    write(attempt/"runtime.json", runtime)
    write(attempt/"test_result.json", {"tests_run": tested.testsRun, "passed": tested.wasSuccessful(),
        "failures": len(tested.failures), "errors": len(tested.errors)})
    write(attempt/"evidence_integrity.json", {"archive_sha256":sha(archive.read_bytes()),
        "uncompressed_sha256":sha(raw), "git_objects_verified":objects, "journal_files_retained":journals})
    check_inputs(cfg)
    if not tested.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError("integration qualification failed; all evidence retained")
    counters = {}
    for name, case in evidence.items():
        counters[name] = {"isolated_git_repositories":len(case["services"]),
            "simulated_connector_calls":sum(len(s["tool_calls"]) for s in case["services"]),
            "confirmed_model_appends":sum(len(s["receipts"]) for s in case["stores"]),
            "passed":True}
    write(OUT/"case_summary.json", counters)
    parent = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/execution_envelope.json").read_text())
    observation = json.loads((OUT/"observed_commit_tool_result.json").read_text())
    result = {"schema":"radio-typed-connector-integration-result-v1",
        "status":"OFFLINE_INTEGRATION_PASS_LIVE_BOOTSTRAP_BLOCKED", "source_commit":cfg["source_commit"],
        "new_tests_passed":tested.testsRun, "retained_qualification_attempts":n,
        "passing_directory":str(attempt.relative_to(ROOT)), "git_objects_verified":objects,
        "journal_files_retained":journals,
        "simulated_connector_calls":sum(v["simulated_connector_calls"] for v in counters.values()),
        "negative_bootstrap_baseline_calls":174,
        "confirmed_model_appends":sum(v["confirmed_model_appends"] for v in counters.values()),
        "input_sha256":cfg["input_sha256"], "parent_blockers_unchanged":parent["blockers"],
        "parent_execution_envelope_sha256":parent["execution_envelope_sha256"],
        "independent_admission_authority_live_available":False,
        "bootstrap_accounting_pass":False, "http_transport_qualified":False,
        "hard_transport_deadline_proven":False, "predecode_wire_bound_proven":False,
        "live_namespace_activated":False, "remote_live_grants_issued":0,
        "real_ledger_api_requests":0, "public_project_commit_metadata_reads":1,
        "observed_tool_envelope_canonical_utf8_bytes":len(json.dumps(observation["tool_result"],sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()),
        "telescope_requests":0, "new_scientific_evaluations":0, "source_permissions_issued":0,
        "primary":"neighbor9", "fresh_24_case_panel_executed":False, "original_m43af_holdouts_opened":False,
        "synthetic_ledger_reset":False}
    write(OUT/"result.json", result)
    if all((ROOT/p).is_file() for p in OWN):
        files=[ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_CONNECTOR_2026-09-27.sha256").write_text(
            "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n" for p in files))
    print(json.dumps({k:result[k] for k in ("status","new_tests_passed","retained_qualification_attempts",
        "simulated_connector_calls","confirmed_model_appends","git_objects_verified","journal_files_retained")},indent=2))


if __name__ == "__main__":
    main()
