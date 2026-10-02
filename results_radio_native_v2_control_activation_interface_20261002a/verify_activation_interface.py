#!/usr/bin/env python3
"""Verify the isolated marker component plus the adjacent blocked suite."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
OUT=Path(__file__).parent
SOURCE=REPO/'scripts/radio_native_v2_control_activation.py'
TEST=REPO/'tests/test_radio_native_v2_control_activation.py'
PROTOCOL=REPO/'config/radio_native_v2_control_activation_transition_20261002a.protocol.json'
PUBLIC_TRANSITION_COMMIT='dc80aa9faf2eb5c26162d3fb3a3c636c82cd385b'
PUBLIC_TRANSITION_TREE='00f6bb8d8f61e47778c6dda90693ca03a814c7d1'
MODULES=['tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission',
    'tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization',
    'tests.test_radio_native_v2_activation_environment',
    'tests.test_radio_native_v2_compact_preparation_audit',
    'tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze',
    'tests.test_radio_native_v2_control_activation']


def pin(path):
    raw=path.read_bytes(); return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def git(*args):
    return subprocess.check_output(['git','--no-replace-objects',*args],cwd=REPO,
        text=True,timeout=20).strip()


def save(name,raw):
    path=OUT/name
    with path.open('xb') as target: target.write(raw)
    return pin(path)


def main():
    started=time.monotonic()
    if git('rev-parse',PUBLIC_TRANSITION_COMMIT+'^{tree}')!=PUBLIC_TRANSITION_TREE:
        raise RuntimeError('Public transition tree differs')
    relative=str(PROTOCOL.relative_to(REPO))
    if git('rev-parse',PUBLIC_TRANSITION_COMMIT+':'+relative)!=git('hash-object',relative):
        raise RuntimeError('Public transition protocol blob differs')
    isolated=subprocess.run([sys.executable,'-I','-S','-B',str(TEST)],cwd=REPO,
        capture_output=True,timeout=30)
    isolated_stdout=save('isolated-tests-stdout.log',isolated.stdout)
    isolated_stderr=save('isolated-tests-stderr.log',isolated.stderr)
    isolated_match=re.search(rb'Ran (\d+) tests in ([0-9.]+)s',isolated.stderr)
    if isolated.returncode or isolated_match is None or int(isolated_match.group(1))!=4:
        raise RuntimeError('Isolated marker component tests failed')
    environment=dict(os.environ)
    environment['PYTHONPATH']=':'.join(str(REPO/folder) for folder in ('scripts','src','tests'))
    suite=subprocess.run([sys.executable,'-B','-m','unittest','-v',*MODULES],cwd=REPO,
        env=environment,capture_output=True,timeout=240)
    suite_stdout=save('adjacent-tests-stdout.log',suite.stdout)
    suite_stderr=save('adjacent-tests-stderr.log',suite.stderr)
    suite_match=re.search(rb'Ran (\d+) tests in ([0-9.]+)s',suite.stderr)
    if suite.returncode or suite_match is None:
        raise RuntimeError('Adjacent activation-interface suite failed')
    summary={'schema':'radio-native-v2-control-activation-interface-result-v1',
        'status':'MARKER_PROOF_COMPONENT_VERIFIED_NOT_INTEGRATED_EXECUTION_BLOCKED',
        'source':pin(SOURCE),'test_source':pin(TEST),'transition_protocol':pin(PROTOCOL),
        'public_transition_protocol_blob_verified':True,
        'isolated_tests':{'count':int(isolated_match.group(1)),
            'seconds':float(isolated_match.group(2)),'stdout':isolated_stdout,'stderr':isolated_stderr},
        'adjacent_tests':{'count':int(suite_match.group(1)),
            'seconds':float(suite_match.group(2)),'stdout':suite_stdout,'stderr':suite_stderr,
            'modules':MODULES},
        'outer_runner_integration_complete':False,
        'worker_bundle_integration_complete':False,
        'activation_marker_created':False,'large_inputs_generated':False,
        'eight_input_resource_control_executed':False,'execution_authorized':False,
        'reservation_authorized':False,'scientific_execution_authorized':False,
        'native_case_reservations':0,'native_case_executions':0,
        'scientific_cases_run':0,'rng_draws':0,'telescope_reads':0,
        'network_fetches':0,'automatic_retry':False,
        'elapsed_seconds':time.monotonic()-started}
    save('verification-summary.json',json.dumps(summary,sort_keys=True,separators=(',',':')).encode()+b'\n')
    print(json.dumps({'status':summary['status'],'isolated_tests':summary['isolated_tests']['count'],
        'adjacent_tests':summary['adjacent_tests']['count']},sort_keys=True))


if __name__=='__main__': main()
