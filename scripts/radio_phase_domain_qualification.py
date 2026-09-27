"""Archive new domain/convention checks, including failures, without network."""
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

from seti_repeater import phase_domain_radio as domain

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/radio_phase_domain_20260927.json"
OUT = ROOT/"results_radio_phase_domain_2026-09-27"
SOURCES = ["src/seti_repeater/phase_domain_radio.py", "tests/test_radio_phase_domain.py",
           "scripts/radio_phase_domain_qualification.py"]
OWN = [CONFIG, *SOURCES, "RADIO_PHASE_DOMAIN_2026-09-27_PROTOCOL.md", "RADIO_PHASE_DOMAIN_2026-09-27_RESULT.md"]


def sha(data): return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n")


def verify(cfg):
    for path, expected in cfg["input_sha256"].items():
        if sha((ROOT/path).read_bytes()) != expected:
            raise ValueError("immutable input changed: " + path)


def main():
    start = time.perf_counter()
    cfg = json.loads((ROOT/CONFIG).read_text())
    verify(cfg)
    OUT.mkdir(exist_ok=True)
    n = 1
    while (OUT/f"qualification_{n:02d}").exists(): n += 1
    attempt = OUT/f"qualification_{n:02d}"; attempt.mkdir()
    snapshot = {p: (ROOT/p).read_text() for p in [CONFIG, *SOURCES]}
    (attempt/"source_snapshot.json.gz").write_bytes(gzip.compress(json.dumps(snapshot, sort_keys=True).encode(), mtime=0))
    sys.path.insert(0, str(ROOT/"tests"))
    suite = unittest.defaultTestLoader.loadTestsFromName("test_radio_phase_domain")
    if suite.countTestCases() > cfg["offline_budget"]["new_test_limit"]:
        raise ValueError("test budget exceeded")
    log = io.StringIO()
    with patch.object(socket, "socket", side_effect=AssertionError("offline only")):
        tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (attempt/"qualification.log").write_text(log.getvalue())
    write(attempt/"test_result.json", {"tests_run":tested.testsRun, "passed":tested.wasSuccessful(),
          "errors":len(tested.errors), "failures":len(tested.failures)})
    write(attempt/"runtime.json", {"python":platform.python_version(), "platform":platform.platform(),
        "socket_creation_disabled":True, "elapsed_seconds":time.perf_counter()-start,
        "source_sha256":{p:sha(s.encode()) for p,s in snapshot.items()}})
    verify(cfg)
    if not tested.wasSuccessful():
        print(log.getvalue()); raise RuntimeError("failure retained; no domain approval")
    audit = domain.audit_contract(cfg)
    write(OUT/"contract_audit.json", audit)
    examples = {"equal_mass_edge_on":domain.projected_axes(1000, 1, 1),
        "small_mass_face_on":domain.projected_axes(1000, .001, 0),
        "large_mass_half_projection":domain.projected_axes(1000, 100, .5)}
    if len(examples) > cfg["offline_budget"]["geometry_examples_limit"]:
        raise ValueError("retained example budget exceeded")
    write(OUT/"axis_identity_examples.json", examples)
    parent = json.loads((ROOT/"results_radio_execution_envelope_2026-09-27/execution_envelope.json").read_text())
    result = {"schema":"radio-phase-domain-result-v1", "status":"CONDITIONAL_CONVENTIONS_DECLARED_PHYSICAL_MODEL_BLOCKED",
        "source_commit":cfg["source_commit"], "contract_sha256":audit["contract_sha256"],
        "new_tests_passed":tested.testsRun, "retained_qualification_attempts":n,
        "passing_directory":str(attempt.relative_to(ROOT)), "retained_axis_examples":len(examples),
        "parent_blockers_unchanged":parent["blockers"], "parent_execution_envelope_sha256":parent["execution_envelope_sha256"],
        "input_sha256":cfg["input_sha256"], "primary":"neighbor9", "joint_probability":None,
        "physical_model_qualified":False, "source_membership_established":False,
        "new_metadata_requests":0, "telescope_requests":0, "spectral_values_opened":False,
        "templates_added":0, "scientific_trials_added":0, "fresh_24_case_panel_executed":False,
        "old_coverage_witness_or_phase_sweep_rerun":False, "original_m43af_holdouts_opened":False,
        "synthetic_ledger_reset":False, "telescope_reservations":0}
    write(OUT/"result.json", result)
    if all((ROOT/p).is_file() for p in OWN):
        paths = [ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_PHASE_DOMAIN_2026-09-27.sha256").write_text(
            "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({k:result[k] for k in ("status", "new_tests_passed", "contract_sha256", "telescope_requests")}, indent=2))


if __name__ == "__main__": main()
