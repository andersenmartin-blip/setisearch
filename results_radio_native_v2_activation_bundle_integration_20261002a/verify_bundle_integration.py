#!/usr/bin/env python3
"""Freeze and verify the integrated one-control activation receipt interface."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
for folder in (REPO/'src',REPO/'scripts'):
    sys.path.insert(0,str(folder))
import radio_native_v2_activation_environment as environment_check
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_runner_freeze as freezer

OUT=Path(__file__).parent
PLAN=REPO/'config/radio_native_v2_compact_eight_input_control_20261002j.plan.json'
FREEZE=REPO/'config/radio_native_v2_activation_environment_20261002d.runtime.json'
PREREAD=REPO/'config/radio_native_v2_execution_preread_20261002a.json'
SELF=str(Path(__file__).relative_to(REPO))
MODULES=['tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission','tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization','tests.test_radio_native_v2_activation_environment',
    'tests.test_radio_native_v2_compact_preparation_audit','tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze','tests.test_radio_native_v2_control_activation']
INPUTS=[str(PLAN.relative_to(REPO)),
    *(path for path in fixture.CODE_FILES if path.startswith('tests/')),
    'tests/test_radio_native_v2_compact_preparation_audit.py',SELF]


def pin(path):
    raw=path.read_bytes(); return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def save(path,raw):
    path=Path(path)
    if path.exists():
        if path.read_bytes()!=raw: raise RuntimeError('Existing evidence differs: '+str(path))
    else: fixture.write(path,raw)
    return pin(path)


def main():
    started=time.monotonic(); plan=fixture.build_plan(REPO)
    if plan['execution_status']!='BLOCKED_PREPARATION_REVIEW' or plan['activation_guard_complete'] is not False:
        raise RuntimeError('Historical plan was rewritten or activation claimed')
    save(PLAN,fixture.canonical(plan)+b'\n')
    freeze=freezer.capture(REPO,INPUTS); save(FREEZE,fixture.canonical(freeze)+b'\n')
    python=plan['runtime_executables']['python']['path']
    exact_environment=environment_check.expected_environment(plan,freeze)
    check_argv=[python,'-I','-S','-B',str(REPO/'scripts/radio_native_v2_activation_environment.py'),
        '--check-only','--plan',str(PLAN),'--complete-freeze',str(FREEZE)]
    checked=subprocess.run(check_argv,cwd=REPO,env=exact_environment,capture_output=True,timeout=60)
    checked_stdout=save(OUT/'parent-check-stdout.json',checked.stdout)
    checked_stderr=save(OUT/'parent-check-stderr.log',checked.stderr)
    if checked.returncode or checked.stderr: raise RuntimeError('Exact parent/platform check failed')
    parent=json.loads(checked.stdout)
    if (parent.get('bounded_activation_platform_contract_verified') is not True
            or parent.get('activation_guard_complete') is not False
            or parent.get('public_immutable_execution_preread_verified') is not False):
        raise RuntimeError('Exact blocked parent/platform receipt differs')

    test_environment=dict(os.environ)
    test_environment['PYTHONPATH']=':'.join(str(REPO/folder) for folder in ('scripts','src','tests'))
    suite_argv=[python,'-B','-m','unittest','-v',*MODULES]
    suite=subprocess.run(suite_argv,cwd=REPO,env=test_environment,capture_output=True,timeout=240)
    suite_stdout=save(OUT/'tests-stdout.log',suite.stdout); suite_stderr=save(OUT/'tests-stderr.log',suite.stderr)
    match=re.search(rb'Ran (\d+) tests in ([0-9.]+)s',suite.stderr)
    if suite.returncode or match is None: raise RuntimeError('Integrated activation bundle suite failed')

    scope=OUT/'must-remain-absent'; readback=OUT/'absent-activation-readback.json'
    if scope.exists() or readback.exists(): raise RuntimeError('Negative pre-marker paths must start absent')
    negative_argv=[python,'-I','-S','-B',str(REPO/'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'),
        '--run','--scope',str(scope),'--plan',str(PLAN),'--complete-freeze',str(FREEZE),
        '--preread',str(PREREAD),'--activation-readback',str(readback)]
    negative=subprocess.run(negative_argv,cwd=REPO,capture_output=True,timeout=30,env=fixture.CHILD_ENVIRONMENT)
    negative_stdout=save(OUT/'pre-marker-stdout.log',negative.stdout)
    negative_stderr=save(OUT/'pre-marker-stderr.log',negative.stderr)
    if negative.returncode==0 or scope.exists() or readback.exists():
        raise RuntimeError('Missing public marker/readback did not close before scope creation')

    summary={'schema':'radio-native-v2-activation-bundle-integration-result-v1',
        'status':'ACTIVATION_RECEIPT_INTEGRATED_NEW_PREPARATION_BLOCKED',
        'plan':pin(PLAN),'complete_freeze':pin(FREEZE),
        'parent_check':checked_stdout,'parent_stderr':checked_stderr,
        'tests':{'count':int(match.group(1)),'seconds':float(match.group(2)),
            'argv':suite_argv,'stdout':suite_stdout,'stderr':suite_stderr},
        'pre_marker_refusal':{'exit_code':negative.returncode,'argv':negative_argv,
            'stdout':negative_stdout,'stderr':negative_stderr,
            'scope_created':False,'readback_path_created':False},
        'repository_code_files':len(freeze['repository_code_inventory']),
        'frozen_inputs':len(freeze['input_file_inventory']),
        'runtime_files':len(freeze['runtime_file_inventory']),
        'outer_runner_integration_complete':True,'worker_bundle_integration_complete':True,
        'activation_marker_created':False,'public_preparation_readback_verified':False,
        'fresh_execution_preread_required':True,'historical_preparation_contract_rewritten':False,
        'large_inputs_generated':False,'eight_input_resource_control_executed':False,
        'execution_authorized':False,'reservation_authorized':False,
        'scientific_execution_authorized':False,'native_case_reservations':0,
        'native_case_executions':0,'scientific_cases_run':0,'rng_draws':0,
        'telescope_reads':0,'network_fetches':0,'automatic_retry':False,
        'elapsed_seconds':time.monotonic()-started}
    save(OUT/'verification-summary.json',fixture.canonical(summary)+b'\n')
    print(json.dumps({'status':summary['status'],'tests':summary['tests']['count'],
        'plan_sha256':summary['plan']['sha256'],'freeze_sha256':summary['complete_freeze']['sha256'],
        'pre_marker_exit':negative.returncode},sort_keys=True))


if __name__=='__main__': main()
