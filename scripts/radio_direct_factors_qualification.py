"""Reproduce and pin the direct-bank engineering package only."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_direct_factors_2026-09-26'


def main():
    OUT.mkdir(exist_ok=True)
    commands=[[sys.executable,'-m','unittest','discover','-s','tests','-p','test_radio_direct_factors.py','-v'],
              [sys.executable,'scripts/radio_direct_factors_fixture.py']]
    logs=[];count=0
    for command in commands:
        run=subprocess.run(command,cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=180)
        logs+=['$ '+' '.join(command),run.stdout,run.stderr]
        (OUT/'qualification.log').write_text('\n'.join(logs).rstrip()+'\n')
        if run.returncode:raise RuntimeError('direct-factor qualification failed')
        match=re.search(r'Ran (\d+) tests? in',run.stderr)
        if match:count+=int(match.group(1))
    paths=['src/seti_repeater/factors_radio.py','src/seti_repeater/motion_radio.py','src/seti_repeater/exposure_radio.py',
        'scripts/radio_direct_factors_fixture.py','scripts/radio_direct_factors_qualification.py','scripts/m43g_reference.py',
        'tests/test_radio_direct_factors.py','config/radio_direct_factors_engineering_20260926.json',
        'config/radio_hd1461_motion_audit_20260926.json','config/radio_motion_requirements_20260926.txt',
        'results_radio_motion_2026-09-26/result.json','results_radio_motion_2026-09-26/clock.json',
        'results_radio_motion_2026-09-26/prospective_design.json']
    record={'schema':'radio-direct-factor-test-qualification-v1','new_tests_passed':count,
        'pinned_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.name!='qualification.json'},
        'scientific_evaluation':False,'closed_legacy_panels_rerun':False,'telescope_values_opened':False}
    (OUT/'qualification.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'new_tests_passed':count,'status':'PASS_ENGINEERING_ONLY'}))


if __name__=='__main__':main()
