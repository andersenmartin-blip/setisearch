"""Offline qualification and retained evidence for the injected v2 backend."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_github_v2_2026-09-27"
CONFIG = "config/radio_github_v2_engineering_20260927.json"
OWN = [CONFIG, "src/seti_repeater/github_role_radio.py",
       "scripts/radio_github_v2_fixture.py", "scripts/radio_github_v2_qualification.py",
       "tests/test_radio_github_v2.py", "RADIO_GITHUB_V2_2026-09-27_PROTOCOL.md",
       "RADIO_GITHUB_V2_2026-09-27_RESULT.md"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_inputs(cfg):
    for path, expected in cfg["input_sha256"].items():
        if sha(ROOT/path) != expected:
            raise ValueError("preserved input differs: " + path)


def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def main():
    start = time.perf_counter()
    cfg = json.loads((ROOT/CONFIG).read_text())
    check_inputs(cfg)
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT/"tests"))
    from test_radio_github_v2 import RemoteTests
    from seti_repeater import github_role_radio as remote
    if remote.LIMITS != cfg["per_operation_limits"]:
        raise ValueError("fixed service-operation limits changed")
    RemoteTests.evidence = {}
    log = io.StringIO()
    with patch.object(socket, "socket", side_effect=AssertionError("network forbidden in fixture qualification")):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RemoteTests)
        tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (OUT/"qualification.log").write_text(log.getvalue())
    evidence = RemoteTests.evidence
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    (OUT/"service_evidence.json.gz").write_bytes(gzip.compress(payload, mtime=0))
    if not tested.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError("new remote-boundary qualification failed; evidence retained")
    decoded = json.loads(gzip.decompress((OUT/"service_evidence.json.gz").read_bytes()))
    object_count = 0
    for case in decoded.values():
        for service in case["services"]:
            for obj in service["git_objects"]:
                raw = base64.b64decode(obj["content_base64"], validate=True)
                identity = hashlib.sha1(obj["type"].encode()+b" "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                if identity != obj["sha"]:
                    raise ValueError("archived Git object failed integrity check")
                object_count += 1
    write("evidence_integrity.json", {"archive_sha256": sha(OUT/"service_evidence.json.gz"),
        "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
        "archived_git_objects_verified": object_count, "all_passed": True})
    summaries = {}
    for name, value in evidence.items():
        services, clients = value["services"], value["clients"]
        if any(s["git_remotes"] or s["real_network_requests"] for s in services):
            raise ValueError("fixture was not isolated")
        calls = [c for s in services for c in s["calls"]]
        updates = [c for c in calls if c["method"] == "PATCH"]
        if any(c["body"].get("force") is not False for c in updates):
            raise ValueError("fixture attempted a force update")
        summaries[name] = {"isolated_git_repositories": len(services), "service_calls": len(calls),
            "reference_update_attempts": len(updates),
            "successful_update_responses": sum(c.get("status") == 200 for c in updates),
            "client_confirmations": sum(len(c["receipts"]) for c in clients),
            "stopped_clients": sum(c["stopped"] for c in clients),
            "retained_git_objects": sum(len(s["git_objects"]) for s in services),
            "exception_responses": sum("raised" in c for c in calls), "passed": True}
    write("case_summary.json", summaries)
    runtime = {"python": platform.python_version(), "platform": platform.platform(),
        "git": subprocess.check_output(["git", "--version"], text=True).strip(),
        "implementation_sha256": {p: sha(ROOT/p) for p in OWN if p.endswith(".py")},
        "service_model": "local bare Git object databases; no remotes or HTTP transport",
        "randomness": "fresh UUID4 per publication attempt; race winner and commit IDs may vary across replays"}
    write("runtime.json", runtime)
    parent = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/execution_envelope.json").read_text())
    result = {"schema": "radio-github-v2-fixture-qualification-v1",
        "status": "INJECTED_GITHUB_V2_BOUNDARY_PASS", "qualification_scope": "ISOLATED_SERVICE_FIXTURES_ONLY",
        "source_commit": cfg["source_commit"], "new_tests_passed": tested.testsRun,
        "execution_status": "BLOCKED", "primary": "neighbor9",
        "parent_execution_envelope_sha256": parent["execution_envelope_sha256"],
        "parent_blockers_unchanged": parent["blockers"],
        "preserved_input_sha256": cfg["input_sha256"],
        "isolated_git_repositories": sum(v["isolated_git_repositories"] for v in summaries.values()),
        "simulated_service_calls": sum(v["service_calls"] for v in summaries.values()),
        "simulated_reference_update_attempts": sum(v["reference_update_attempts"] for v in summaries.values()),
        "fixture_client_confirmations": sum(v["client_confirmations"] for v in summaries.values()),
        "unsafe_baseline_scope": "two success responses for one identical commit in local Git-backed service; no protected client used",
        "retained_evidence_uncompressed_bytes": len(payload),
        "retained_evidence_compressed_bytes": (OUT/"service_evidence.json.gz").stat().st_size,
        "per_operation_limits": cfg["per_operation_limits"],
        "real_ledger_api_requests": 0, "telescope_requests": 0, "telescope_values_opened": False,
        "network_budget_issued": False, "telescope_namespace_activated": False,
        "prospective_telescope_reservations": 0, "published_synthetic_ledger_reset": False,
        "live_github_v2_backend_qualified": False, "http_adapter_implemented": False,
        "fresh_24_case_panel_executed": False, "new_scientific_evaluations": 0,
        "original_m43af_holdouts_opened": False, "offline_wall_seconds": time.perf_counter()-start}
    write("result.json", result)
    check_inputs(cfg)
    paths = [ROOT/p for p in OWN]+sorted(p for p in OUT.iterdir() if p.is_file())
    if all(p.is_file() for p in paths):
        (ROOT/"RESULTS_MANIFEST_RADIO_GITHUB_V2_2026-09-27.sha256").write_text(
            "".join(f"{sha(p)}  {p.relative_to(ROOT)}\n" for p in paths))
    else:
        print("Protocol/report not yet present; manifest deliberately not emitted")
    print(json.dumps({k: result[k] for k in ("status", "new_tests_passed", "isolated_git_repositories",
        "simulated_service_calls", "simulated_reference_update_attempts", "fixture_client_confirmations",
        "retained_evidence_compressed_bytes", "telescope_requests")}, indent=2))


if __name__ == "__main__":
    main()
