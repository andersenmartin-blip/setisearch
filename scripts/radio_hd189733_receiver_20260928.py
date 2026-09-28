#!/usr/bin/env python3
"""One bounded receiver-bank qualification and fresh identity reservation; no spectra."""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

import numpy as np

from seti_repeater import receiver_bank_radio as r

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_hd189733_receiver_2026-09-28"
SOURCE = "config/radio_hd189733_source_preparation_20260927.json"
DESIGN = "results_radio_hd189733_geometry_2026-09-27/window_geometry.json"
SOURCE_SHA = "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"
DESIGN_SHA = "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"


def save(name, value):
    with (OUT / name).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def digest_file(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def inventory():
    """Configuration identifiers only: never open held-out input payloads."""
    identifiers, seeds, files = set(), set(), {}
    def walk(x):
        if isinstance(x, dict):
            for k,v in x.items():
                if "seed" in k and type(v) is int: seeds.add(v)
                if "namespace" in k and isinstance(v, str): identifiers.add(v)
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    for p in sorted((ROOT / "config").glob("*.json")):
        b = p.read_bytes()
        try: x = json.loads(b)
        except (ValueError, UnicodeDecodeError): continue
        files[str(p.relative_to(ROOT))] = hashlib.sha256(b).hexdigest()
        walk(x)
    return identifiers, seeds, files


def main():
    started = time.monotonic()
    OUT.mkdir(exist_ok=False)
    paths = [SOURCE, DESIGN, "RADIO_HD189733_RECEIVER_2026-09-28_SCOPE.md",
             "src/seti_repeater/receiver_bank_radio.py", "src/seti_repeater/window_identity_radio_v2.py",
             "scripts/radio_hd189733_receiver_20260928.py", "tests/test_radio_receiver_bank.py",
             "config/radio_fresh_control_freeze_20260926.json", "src/seti_repeater/pipeline_radio.py",
             "src/seti_repeater/search_v0p6.py", "src/seti_repeater/factors_radio.py",
             "results_radio_alternate_2026-09-27/source_qualification.json"]
    save("input_pins.json", {p:digest_file(p) for p in paths})
    args = ((ROOT/SOURCE).read_bytes(), SOURCE_SHA, (ROOT/DESIGN).read_bytes(), DESIGN_SHA)
    source, design, binding, rows = r.inputs(*args)
    banks, checks = [], []
    for w in design["windows"]:
        b = r.build(*args, w["role"])
        C = Q(w["proposed_first_on_midpoint_carrier_center_hz"])
        max_error = Q(0)
        # Independent exact-rational oracle over all 23,328 factors in each role.
        for index,j in enumerate(range(-40,41)):
            for i,row in enumerate(rows):
                for k,t in enumerate(row):
                    exact = 1 + Q(j,10)*t/C
                    error = abs(Q(float(b.factors[index,i,k]))-exact)*C
                    max_error = max(max_error,error)
        # Account for max supported carrier relative to C and two additional
        # binary64 roundings (carrier construction and frequency multiplication).
        df = abs(Q(source["scans"][0]["expected_header"]["foff_mhz"]))*10**6
        full_error = max_error*(C+49*df)/C + Q(1,2**21)
        assert full_error <= Q(1,10000), "Fixed arithmetic tolerance failed"
        coverage = r.coverage(*args, w["role"])
        assert coverage["continuous_linear_family_contained_at_width_129"]
        assert coverage["full_support_and_receiver_neighborhood_inside_extraction"]
        banks.append({**b.record(), "bank_identity":b.identity})
        checks.append({"role":w["role"], "factor_comparisons":81*96*3,
                       "max_center_equivalent_error_hz":r.ratio_record(max_error),
                       "supported_carrier_arithmetic_bound_hz":r.ratio_record(full_error),
                       "conditional_containment":coverage})
    save("bank_records.json", banks)
    save("arithmetic_and_containment.json", checks)
    old = json.loads((ROOT/"config/radio_fresh_control_freeze_20260926.json").read_text())
    namespaces, seeds, files = inventory()
    records = []
    def identity(role, index, recipe):
        ns = f"radio-hd189733-receiver-20260928-{role}-{index:02d}"
        seed = int(r.sha(ns.encode())[:16],16)
        assert ns not in namespaces and seed not in seeds
        assert all(x["seed"] != seed and x["namespace"] != ns for x in records)
        rec = {"role":role,"index":index,"namespace":ns,"seed":seed,
               "recipe":recipe,"source_contract_sha256":SOURCE_SHA,
               "receiver_bank_identities":[b["bank_identity"] for b in banks],
               "outcomes_may_select_settings":False,"executed":False}
        rec["identity"] = r.sha(r.canonical(rec))
        records.append(rec)
    for i,rate in enumerate([-3.95,-1.95,-0.05,0.05,1.95,3.95]):
        identity("development",i,{"rate_label_hz_s":rate,"source_domain":"synthetic-only",
                   "renderer_frozen":False,"purpose":"reserved off-grid boundary development"})
    for i in range(3): identity("calibration",i,{"kind":"noise_only","renderer_frozen":False})
    for i,case in enumerate(old["cases"]):
        recipe = {k:v for k,v in case.items() if k not in ("seed","source_identity_namespace","outcomes_may_select_settings")}
        recipe.update({"rate_label_hz_s":[-4,-2,0,2,4][i%5],"carrier_offset_channels":0,
                       "activity_patterns":old["activity_patterns"],"renderer_frozen":False})
        identity("evaluation",i,recipe)
    assert len(records) == 33
    panel = {"schema":"radio-hd189733-receiver-control-reservation-v1",
             "status":"IDENTITIES_RESERVED_NOT_EXECUTABLE", "primary":"neighbor9",
             "source_contract_sha256":SOURCE_SHA,"window_binding_sha256":binding["contract_sha256"],
             "identities":records,"gates":old["gates"],"association_rule":old["association_rule"],
             "attempt_ceilings":{"development_cases":6, "calibration_realizations":3,
                 "evaluation_cases":24,"evaluation_runs":1,"remedy_attempts":0,"pilot_runs":0},
             "executed_counts":{"development_cases":0,"calibration_realizations":0,
                 "evaluation_cases":0,"evaluation_runs":0,"pilot_runs":0},
             "old_unexecuted_panel":"archived inactive; prospective allocation transferred, not doubled",
             "old_panel_sha256":digest_file("config/radio_fresh_control_freeze_20260926.json"),
             "statistical_independence_from_identity_uniqueness_claimed":False,
             "spectral_access_authorized":False,"scientific_evaluation_authorized":False}
    save("control_identity_reservation.json",panel)
    save("prior_config_identifier_inventory.json",{"config_sha256":files,
        "prior_integer_seeds":sorted(seeds),"prior_namespaces":sorted(namespaces),
        "new_identity_count":33,"new_identity_seed_collisions":0,
        "input_payloads_read":False})
    run = subprocess.run([sys.executable,"-m","unittest","discover","-s","tests",
        "-p","test_radio_receiver_bank.py","-v"], cwd=ROOT,capture_output=True,text=True,timeout=120)
    (OUT/"new_tests.log").write_text(run.stdout+run.stderr)
    assert run.returncode == 0, "New tests failed; preserve this attempt"
    match = re.search(r"Ran (\d+) tests",run.stderr)
    assert match and int(match[1]) <= 20
    pins = json.loads((ROOT/"results_radio_alternate_2026-09-27/source_qualification.json").read_text())["old_frozen_input_pins_unchanged"]
    for path,expected in pins.items():
        actual = subprocess.check_output(["git","show","HEAD:"+path],cwd=ROOT)
        assert hashlib.sha256(actual).hexdigest() == expected
        if (ROOT/path).exists(): assert digest_file(path) == expected
    save("invariants.json",{"old_pins_verified":pins,"new_source_preparation_sha256":SOURCE_SHA,
        "widened_window_design_sha256":DESIGN_SHA,"legacy_numerical_modules_modified":False,
        "exhausted_ledger_reopened":False,"old_telescope_genesis_activated":False,
        "reserved_holdout_payloads_opened":False,"external_messages_sent":0})
    score_bytes = 2*81*8*3*99*4
    result = {"schema":"radio-hd189733-receiver-qualification-v1",
        "status":"RECEIVER_BANK_ARITHMETIC_AND_GEOMETRY_QUALIFIED_ONLY",
        "primary":"neighbor9","templates_per_role":81,"score_carriers_per_role":81,
        "support_carriers_per_role":99,"widths":list(r.WIDTHS),
        "exact_factor_comparisons":3*81*96*3,"new_tests_passed":int(match[1]),
        "fresh_development_calibration_evaluation_identities":[6,3,24],
        "factor_table_bytes_all_roles":3*81*96*3*8,"score_store_bytes_per_role":score_bytes,
        "modelled_pipeline_owned_bytes_per_role":6*16*65536*4+(3*16*65536*4+96*65536+4*1024**2)+3*score_bytes+81*99*64,
        "runtime":{"python":platform.python_version(),"numpy":np.__version__},
        "qualification_wall_seconds":time.monotonic()-started,
        "codec_or_detector_runtime_benchmarked":False,"actual_source_physical_completeness_claimed":False,
        "receiver_ephemeris_conversion_performed":False,"scientific_trials":0,
        "new_telescope_requests":0,"telescope_spectral_values_opened":False,
        "development_spectral_cases_executed":0,"calibration_cases_executed":0,"evaluation_cases_executed":0,
        "spectral_access_authorized":False,
        "remaining":["receiver-specific downstream numeric adapter and calibration transfer",
          "fresh control rendering freeze and full recovery/RFI/null result",
          "source-specific codec/runtime receipt handoff",
          "integrated prospective execution protocol and cumulative resource/attempt ledger"]}
    save("result.json",result)
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
