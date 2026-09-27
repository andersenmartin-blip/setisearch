"""Retain covering-count calculus and scalar derivative oracles; no grid."""
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

from seti_repeater import motion_covering_radio as covering
from seti_repeater.phase_domain_radio import contract_identity
from radio_covering_oracle import scalar_derivatives

ROOT=Path(__file__).resolve().parents[1]
CONFIG="config/radio_motion_covering_20260927.json"
OUT=ROOT/"results_radio_motion_covering_2026-09-27"
SOURCES=["src/seti_repeater/motion_covering_radio.py","scripts/radio_covering_oracle.py",
         "scripts/radio_motion_covering_qualification.py","tests/test_radio_motion_covering.py"]
OWN=[CONFIG,*SOURCES,"RADIO_MOTION_COVERING_2026-09-27_PROTOCOL.md","RADIO_MOTION_COVERING_2026-09-27_RESULT.md"]


def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(p,value):p.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")


def verify(cfg):
    for p,h in cfg["input_sha256"].items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError("immutable input changed: "+p)
    if contract_identity(read("config/radio_phase_domain_20260927.json"))!=cfg["domain_sha256"]:
        raise ValueError("domain declaration identity changed")


def main():
    start=time.perf_counter();cfg=read(CONFIG);verify(cfg)
    OUT.mkdir(exist_ok=True);n=1
    while (OUT/f"qualification_{n:02d}").exists():n+=1
    attempt=OUT/f"qualification_{n:02d}";attempt.mkdir()
    snapshot={p:(ROOT/p).read_text() for p in [CONFIG,*SOURCES]}
    (attempt/"source_snapshot.json.gz").write_bytes(gzip.compress(json.dumps(snapshot,sort_keys=True).encode(),mtime=0))
    sys.path.insert(0,str(ROOT/"tests"));suite=unittest.defaultTestLoader.loadTestsFromName("test_radio_motion_covering")
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
    if len(cfg["oracle_points"])!=cfg["budgets"]["retained_oracle_points"]:raise ValueError("oracle budget differs")
    env=covering.sensitivity_envelope(read("config/radio_phase_domain_20260927.json"),cfg["reception_extent_seconds"],cfg["reference_hz"])
    layout=cfg["hypothetical_factor_layout"]
    count=covering.sufficient_cover_count(env,cfg["reporting_center_tolerance_hz"],layout["clock_rows"],layout["clock_samples_per_row"])
    oracles=[{"coordinates":p,**scalar_derivatives(p,cfg["reception_extent_seconds"],cfg["reference_hz"])} for p in cfg["oracle_points"]]
    write(OUT/"sensitivity_envelope.json",env);write(OUT/"sufficient_cover_count.json",count);write(OUT/"scalar_derivative_oracles.json",oracles)
    parent=read("results_radio_execution_envelope_2026-09-27/execution_envelope.json")
    result={"schema":"radio-motion-covering-result-v1","status":"LOOSE_SUFFICIENT_COVER_COUNTED_NO_BANK_ADOPTED",
        "source_commit":cfg["source_commit"],"new_tests_passed":tested.testsRun,"retained_qualification_attempts":n,
        "passing_directory":str(attempt.relative_to(ROOT)),"scalar_derivative_points":len(oracles),"partial_derivatives_per_point":6,
        "input_sha256":cfg["input_sha256"],"parent_blockers_unchanged":parent["blockers"],
        "parent_execution_envelope_sha256":parent["execution_envelope_sha256"],"product_nodes":count["product_nodes"],
        "count_is_necessary_lower_bound":False,"runtime_measured":False,"numeric_interval_certificate":False,
        "total_physical_error_hz":None,"physical_model_qualified":False,"primary":"neighbor9",
        "telescope_requests":0,"new_metadata_requests":0,"templates_added":0,"scientific_trials_added":0,
        "telescope_reservations":0,"fresh_24_case_panel_executed":False,"original_m43af_holdouts_opened":False,
        "old_coverage_witness_or_phase_sweep_rerun":False,"synthetic_ledger_reset":False}
    write(OUT/"result.json",result)
    if all((ROOT/p).is_file() for p in OWN):
        paths=[ROOT/p for p in OWN]+sorted(p for p in OUT.rglob("*") if p.is_file())
        (ROOT/"RESULTS_MANIFEST_RADIO_MOTION_COVERING_2026-09-27.sha256").write_text(
            "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({"new_tests":tested.testsRun,"attempt":n,"sufficient_cover":count,
        "sensitivity_hz_per_unit":{k:v["proper_frequency_lipschitz_hz_per_unit"] for k,v in env["parameters"].items()}},indent=2))


if __name__=="__main__":main()
