"""Persist exact conditional Taylor remainder certificate; no polynomial bank."""
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

from seti_repeater.temporal_majorant_radio import temporal_remainder_certificate

ROOT=Path(__file__).resolve().parents[1]
CONFIG="config/radio_temporal_majorant_20260927.json"
OUT=ROOT/"results_radio_temporal_majorant_2026-09-27"
SOURCES=["src/seti_repeater/temporal_majorant_radio.py","tests/test_radio_temporal_majorant.py",
         "scripts/radio_temporal_majorant_qualification.py"]
OWN=[CONFIG,*SOURCES,"RADIO_TEMPORAL_MAJORANT_2026-09-27_PROTOCOL.md","RADIO_TEMPORAL_MAJORANT_2026-09-27_RESULT.md"]


def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(p,value):p.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")


def verify(cfg):
    for p,h in cfg["input_sha256"].items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError("immutable input changed: "+p)


def main():
    start=time.perf_counter();cfg=read(CONFIG);verify(cfg)
    if len(cfg["orders"])!=cfg["budgets"]["degree_count"]:raise ValueError("degree budget differs")
    OUT.mkdir(exist_ok=True);n=1
    while (OUT/f"qualification_{n:02d}").exists():n+=1
    attempt=OUT/f"qualification_{n:02d}";attempt.mkdir()
    snapshot={p:(ROOT/p).read_text() for p in [CONFIG,*SOURCES]}
    (attempt/"source_snapshot.json.gz").write_bytes(gzip.compress(json.dumps(snapshot,sort_keys=True).encode(),mtime=0))
    sys.path.insert(0,str(ROOT/"tests"));suite=unittest.defaultTestLoader.loadTestsFromName("test_radio_temporal_majorant")
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
    if not tested.wasSuccessful():print(log.getvalue());raise RuntimeError("failed run retained")
    certificate=temporal_remainder_certificate(read("config/radio_phase_domain_20260927.json"),cfg)
    write(OUT/"remainder_certificate.json",certificate)
    parent=read("results_radio_execution_envelope_2026-09-27/execution_envelope.json")
    result={"schema":"radio-temporal-majorant-result-v1","status":"CONDITIONAL_TEMPORAL_REMAINDERS_CERTIFIED_NO_BANK",
        "source_commit":cfg["source_commit"],"new_tests_passed":tested.testsRun,"retained_qualification_attempts":n,
        "passing_directory":str(attempt.relative_to(ROOT)),"degrees_assessed":cfg["orders"],
        "degrees_within_reporting_tolerance":[r["degree"] for r in certificate["degrees"] if r["within_reporting_tolerance"]],
        "input_sha256":cfg["input_sha256"],"parent_blockers_unchanged":parent["blockers"],
        "parent_execution_envelope_sha256":parent["execution_envelope_sha256"],"conditional_rational_arithmetic_certified":True,
        "formal_theorem_prover_verification":False,"total_physical_error_hz":None,"physical_model_qualified":False,
        "primary":"neighbor9","telescope_requests":0,"new_metadata_requests":0,"templates_added":0,
        "polynomial_tracks_generated":0,"scientific_trials_added":0,"telescope_reservations":0,
        "fresh_24_case_panel_executed":False,"original_m43af_holdouts_opened":False,"synthetic_ledger_reset":False}
    write(OUT/"result.json",result)
    if all((ROOT/p).is_file() for p in OWN):
        paths=[ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_TEMPORAL_MAJORANT_2026-09-27.sha256").write_text(
            "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({"new_tests":tested.testsRun,"attempt":n,"remainders":[{k:r[k] for k in ("degree","remainder_hz_outward_decimal","within_reporting_tolerance")} for r in certificate["degrees"]],"certificate_bytes":(OUT/"remainder_certificate.json").stat().st_size},indent=2))


if __name__=="__main__":main()
