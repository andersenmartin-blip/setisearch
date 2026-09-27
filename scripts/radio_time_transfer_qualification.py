"""Persist bounded scalar timing evidence and every attempted qualification."""
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

from seti_repeater.phase_domain_radio import contract_identity
from seti_repeater import time_transfer_radio as transfer

ROOT=Path(__file__).resolve().parents[1]
CONFIG="config/radio_time_transfer_20260927.json"
OUT=ROOT/"results_radio_time_transfer_2026-09-27"
SOURCES=["src/seti_repeater/time_transfer_radio.py", "tests/test_radio_time_transfer.py",
         "scripts/radio_time_transfer_qualification.py"]
OWN=[CONFIG,*SOURCES,"RADIO_TIME_TRANSFER_2026-09-27_PROTOCOL.md","RADIO_TIME_TRANSFER_2026-09-27_RESULT.md"]


def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(p,value):p.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")


def verify(cfg):
    for path,h in cfg["input_sha256"].items():
        if sha((ROOT/path).read_bytes())!=h:raise ValueError("immutable input changed: "+path)
    if contract_identity(read("config/radio_phase_domain_20260927.json"))!=cfg["phase_domain_canonical_sha256"]:
        raise ValueError("domain declaration identity changed")


def main():
    start=time.perf_counter();cfg=read(CONFIG);verify(cfg)
    OUT.mkdir(exist_ok=True);n=1
    while (OUT/f"qualification_{n:02d}").exists():n+=1
    attempt=OUT/f"qualification_{n:02d}";attempt.mkdir()
    snapshot={p:(ROOT/p).read_text() for p in [CONFIG,*SOURCES]}
    (attempt/"source_snapshot.json.gz").write_bytes(gzip.compress(json.dumps(snapshot,sort_keys=True).encode(),mtime=0))
    sys.path.insert(0,str(ROOT/"tests"))
    suite=unittest.defaultTestLoader.loadTestsFromName("test_radio_time_transfer")
    if suite.countTestCases()>cfg["budgets"]["new_tests_limit"]:raise ValueError("test budget exceeded")
    log=io.StringIO()
    with patch.object(socket,"socket",side_effect=AssertionError("offline only")):
        tested=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (attempt/"qualification.log").write_text(log.getvalue())
    write(attempt/"test_result.json",{"tests_run":tested.testsRun,"passed":tested.wasSuccessful(),
        "errors":len(tested.errors),"failures":len(tested.failures)})
    write(attempt/"runtime.json",{"python":platform.python_version(),"platform":platform.platform(),
        "socket_creation_disabled":True,"elapsed_seconds":time.perf_counter()-start,
        "source_sha256":{p:sha(s.encode()) for p,s in snapshot.items()}})
    verify(cfg)
    if not tested.wasSuccessful():print(log.getvalue());raise RuntimeError("failed attempt retained")
    if len(cfg["cases"])!=cfg["budgets"]["retained_scalar_endpoints"]:raise ValueError("case budget mismatch")
    domain=read("config/radio_phase_domain_20260927.json")
    bounds=transfer.conditional_error_bounds(domain,cfg["reception_extent_seconds"],cfg["reference_hz"])
    endpoints={case["id"]:transfer.compare_scalar_models(domain,cfg["reception_extent_seconds"],case["parameters"],cfg["reference_hz"]) for case in cfg["cases"]}
    write(OUT/"conditional_bounds.json",bounds);write(OUT/"scalar_endpoints.json",endpoints)
    parent=read("results_radio_execution_envelope_2026-09-27/execution_envelope.json")
    result={"schema":"radio-time-transfer-result-v1","status":"CONDITIONAL_TIME_DOPPLER_TERMS_BOUNDED_FULL_PHYSICS_BLOCKED",
        "source_commit":cfg["source_commit"],"new_tests_passed":tested.testsRun,"retained_qualification_attempts":n,
        "passing_directory":str(attempt.relative_to(ROOT)),"scalar_equation_endpoints":len(endpoints),
        "source_domain_sha256":cfg["phase_domain_canonical_sha256"],"input_sha256":cfg["input_sha256"],
        "parent_blockers_unchanged":parent["blockers"],"parent_execution_envelope_sha256":parent["execution_envelope_sha256"],
        "total_physical_error_hz":None,"physical_model_qualified":False,"numeric_interval_certificate":False,
        "primary":"neighbor9","telescope_requests":0,"new_metadata_requests":0,"templates_added":0,
        "scientific_trials_added":0,"telescope_reservations":0,"fresh_24_case_panel_executed":False,
        "original_m43af_holdouts_opened":False,"old_coverage_witness_or_phase_sweep_rerun":False,"synthetic_ledger_reset":False}
    write(OUT/"result.json",result)
    if all((ROOT/p).is_file() for p in OWN):
        paths=[ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_TIME_TRANSFER_2026-09-27.sha256").write_text(
            "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({"tests":tested.testsRun,"attempt":n,"bounds":bounds,"endpoints":{k:v["combined_emitter_difference_hz"] for k,v in endpoints.items()}},indent=2))


if __name__=="__main__":main()
