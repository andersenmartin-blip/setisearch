"""Retain new offline rehearsal-accounting qualification; never activate live."""
import base64
from datetime import date
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
OUT = ROOT/"results_radio_rehearsal_contract_2026-09-27"
CONFIG = "config/radio_rehearsal_contract_20260927.json"
OWN = [CONFIG, "src/seti_repeater/rehearsal_contract_radio.py",
       "scripts/radio_rehearsal_contract_qualification.py", "tests/test_radio_rehearsal_contract.py",
       "RADIO_REHEARSAL_CONTRACT_2026-09-27_PROTOCOL.md", "RADIO_REHEARSAL_CONTRACT_2026-09-27_RESULT.md"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_inputs(cfg):
    for path, expected in cfg["input_sha256"].items():
        if sha(ROOT/path) != expected:
            raise ValueError("preserved input changed: " + path)


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n")


def main():
    start = time.perf_counter()
    cfg = json.loads((ROOT/CONFIG).read_text())
    check_inputs(cfg)
    from seti_repeater import rehearsal_contract_radio as r
    original = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/resource_ledger_genesis.json").read_text())
    prepared = r.prepare(cfg, original)
    state = r.activation_state(prepared, today=date(2026, 9, 27))
    OUT.mkdir(exist_ok=True)
    write(OUT/"prepared_contract.json", prepared)
    write(OUT/"planned_model_genesis.json", prepared["model_genesis"])
    write(OUT/"planned_grant_genesis.json", prepared["grant_genesis"])
    # Keep every local qualification attempt, including failures, without overwriting.
    ordinal = 1
    while (OUT/f"qualification_{ordinal:02d}").exists():
        ordinal += 1
    attempt = OUT/f"qualification_{ordinal:02d}"
    attempt.mkdir()
    sys.path.insert(0, str(ROOT/"tests"))
    from test_radio_rehearsal_contract import RehearsalTests
    RehearsalTests.evidence = {}
    log = io.StringIO()
    with patch.object(socket, "socket", side_effect=AssertionError("network forbidden in offline qualification")):
        tested = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(RehearsalTests))
    (attempt/"qualification.log").write_text(log.getvalue())
    raw = r.encode(RehearsalTests.evidence)
    archive = attempt/"journal_evidence.json.gz"
    archive.write_bytes(gzip.compress(raw, mtime=0))
    decoded = json.loads(gzip.decompress(archive.read_bytes()))
    files = {name: {path: hashlib.sha256(base64.b64decode(value, validate=True)).hexdigest()
                   for path, value in case["files_base64"].items()} for name, case in decoded.items()}
    write(attempt/"evidence_integrity.json", {"archive_sha256": sha(archive),
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
        "retained_file_sha256": files, "all_archived_files_decoded": True})
    write(attempt/"test_result.json", {"tests_run": tested.testsRun,
        "failures": len(tested.failures), "errors": len(tested.errors), "passed": tested.wasSuccessful(),
        "implementation_sha256": {p: sha(ROOT/p) for p in OWN if p.endswith(".py")}})
    check_inputs(cfg)
    if not tested.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError("new journal qualification failed; attempt evidence retained")
    capabilities = json.loads((OUT/"connector_capabilities.json").read_text())
    parent = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/execution_envelope.json").read_text())
    runtime = {"python": platform.python_version(), "platform": platform.platform(),
        "implementation_sha256": {p: sha(ROOT/p) for p in OWN if p.endswith(".py")},
        "qualification_scope": "local journal fixtures and two actual child-process exits; no live adapter",
        "socket_creation_disabled": True, "elapsed_seconds": time.perf_counter()-start}
    write(OUT/"runtime.json", runtime)
    result = {"schema": "radio-github-rehearsal-preparation-result-v1",
        "status": "PROSPECTIVE_CONTRACT_AND_LOCAL_JOURNAL_COMPLETE",
        "source_commit": cfg["source_commit"], "contract_sha256": prepared["contract_sha256"],
        "new_tests_passed": tested.testsRun, "retained_qualification_attempts": ordinal,
        "passing_qualification_directory": str(attempt.relative_to(ROOT)),
        "journal_evidence_files": sum(len(value) for value in files.values()),
        "actual_child_process_crashes": 2, "real_ledger_api_requests": 0,
        "live_namespace_initialized": False, "remote_phase_grants_issued": 0,
        "telescope_requests": 0, "telescope_reservations": 0, "new_scientific_evaluations": 0,
        "fresh_24_case_panel_executed": False, "original_m43af_holdouts_opened": False,
        "published_synthetic_ledger_reset": False, "primary": "neighbor9",
        "parent_execution_envelope_sha256": parent["execution_envelope_sha256"],
        "parent_blockers_unchanged": parent["blockers"],
        "activation_state": state, "preserved_input_sha256": cfg["input_sha256"],
        "connector_observed_capabilities": capabilities["observed_capabilities"],
        "live_github_adapter_qualified": False, "predecode_wire_bound_proven": False,
        "transport_deadline_cancellation_proven": False, "global_journal_durability_proven": False,
        "planned_limits": cfg["total_limits"], "planned_limits_are_active_grants": False}
    write(OUT/"result.json", result)
    if all((ROOT/p).is_file() for p in OWN):
        paths = [ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_REHEARSAL_CONTRACT_2026-09-27.sha256").write_text(
            "".join(f"{sha(p)}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({k: result[k] for k in ("status", "new_tests_passed", "retained_qualification_attempts",
        "journal_evidence_files", "actual_child_process_crashes", "real_ledger_api_requests", "telescope_requests")}, indent=2))


if __name__ == "__main__":
    main()
