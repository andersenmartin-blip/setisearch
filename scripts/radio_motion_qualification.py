"""Run only the new motion/exposure/design checks and retain their evidence."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_motion_2026-09-26'


def main():
    OUT.mkdir(exist_ok=True)
    commands=[
        [sys.executable,'-m','unittest','discover','-s','tests','-p','test_radio_motion.py','-v'],
        [sys.executable,'-m','unittest','discover','-s','tests','-p','test_radio_exposure.py','-v'],
        [sys.executable,'-m','unittest','discover','-s','tests','-p','test_radio_design.py','-v'],
        [sys.executable,'scripts/radio_motion_audit.py'],
        [sys.executable,'scripts/radio_prospective_design.py']]
    log=[]; results=[]; passed=0
    for command in commands:
        run=subprocess.run(command,cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=120)
        log += ['$ '+ ' '.join(command),run.stdout,run.stderr]
        results.append({'arguments':command[1:],'returncode':run.returncode})
        if run.returncode:
            (OUT/'qualification.log').write_text('\n'.join(log).rstrip()+'\n')
            raise RuntimeError('qualification command failed')
        if '-m' in command:
            match=re.search(r'Ran (\d+) tests? in',run.stderr)
            if match is None: raise RuntimeError('test count missing from unittest output')
            passed+=int(match.group(1))
    (OUT/'qualification.log').write_text('\n'.join(log).rstrip()+'\n')
    paths=[
        'src/seti_repeater/motion_radio.py','src/seti_repeater/exposure_radio.py',
        'scripts/radio_motion_audit.py','scripts/radio_prospective_design.py','scripts/radio_motion_qualification.py',
        'tests/test_radio_motion.py','tests/test_radio_exposure.py','tests/test_radio_design.py',
        'config/radio_hd1461_motion_audit_20260926.json',
        'config/radio_hd1461_source_preparation_20260926.json',
        'src/seti_repeater/pipeline_radio.py','src/seti_repeater/search_v0p6.py','src/seti_repeater/orbit.py',
        'src/seti_repeater/source_m43h.py','src/seti_repeater/transfer_m43g.py',
        'results_radio_restart_2026-09-26/astrometry/official_response.json']
    record={'schema':'radio-motion-qualification-v1','status':'PASS_ENGINEERING_ONLY',
        'new_tests_passed':passed,'commands':results,
        'pinned_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir())
                         if p.name in ('result.json','clock.json','phase_comparison.json.gz','prospective_design.json','exposure_profiles.json.gz')},
        'legacy_tests_rerun':False,'real_spectral_data_read':False,'source_network_requests':0,
        'motion_bank_qualified':False,'telescope_protocol_frozen':False,
        'development_correction':'An initial test incorrectly expected LOS acceleration for omega=-10 deg to approach the full vector bound within 10%. The physical bound calculation was unchanged; the saturation assertion now uses omega=90 deg at periastron, where LOS and acceleration align. All-phase sampled derivatives remain checked against the bound.'}
    (OUT/'qualification.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':record['status'],'new_tests_passed':passed,'source_network_requests':0}))


if __name__=='__main__':main()
