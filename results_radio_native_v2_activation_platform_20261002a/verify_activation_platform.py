#!/usr/bin/env python3
"""Freeze and verify the bounded secret-free activation platform contract."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
for folder in (REPO/'src', REPO/'scripts'):
    sys.path.insert(0, str(folder))
import radio_native_v2_activation_environment as activation
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_runner_freeze as freezer

OUT = Path(__file__).parent
PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002i.plan.json'
FREEZE = REPO/'config/radio_native_v2_activation_environment_20261002c.runtime.json'
SELF = str(Path(__file__).relative_to(REPO))
MODULES = ['tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission',
    'tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization',
    'tests.test_radio_native_v2_activation_environment',
    'tests.test_radio_native_v2_compact_preparation_audit',
    'tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze']
INPUTS = [str(PLAN.relative_to(REPO)),
    *(path for path in fixture.CODE_FILES if path.startswith('tests/')),
    'tests/test_radio_native_v2_compact_preparation_audit.py', SELF]


def persist(name, value):
    fixture.write(OUT/name, value)
    return fixture.pin(OUT/name)


def main():
    started = time.monotonic()
    plan = json.loads(PLAN.read_bytes())
    if plan != fixture.build_plan(REPO):
        raise RuntimeError('Saved plan differs from exact current platform build')
    freeze = freezer.capture(REPO, INPUTS)
    fixture.write(FREEZE, freeze)
    environment = activation.expected_environment(plan, freeze)
    python = plan['runtime_executables']['python']['path']
    argv = [python, '-I', '-S', '-B',
        str(REPO/'scripts/radio_native_v2_activation_environment.py'),
        '--check-only', '--plan', str(PLAN), '--complete-freeze', str(FREEZE)]
    process = subprocess.run(argv, cwd=REPO, env=environment,
        capture_output=True, timeout=60)
    parent_pin = persist('parent-check-stdout.json', process.stdout)
    stderr_pin = persist('parent-check-stderr.log', process.stderr)
    if process.returncode or process.stderr:
        raise RuntimeError('Exact activation platform check failed')
    receipt = json.loads(process.stdout)
    expected_platform = plan['activation_platform_contract']
    if not (receipt['bounded_activation_platform_contract_verified'] is True
            and receipt['bounded_activation_platform'] == expected_platform
            and receipt['operating_system_kernel_bytes_frozen'] is False
            and receipt['complete_parent_environment_frozen'] is True
            and receipt['environment'] == environment
            and receipt['observed_argv'] == argv
            and receipt['isolated_no_site_no_bytecode'] is True
            and receipt['activation_guard_complete'] is False):
        raise RuntimeError('Activation platform receipt differs from exact blocked contract')

    test_environment = dict(os.environ)
    test_environment['PYTHONPATH'] = ':'.join(str(REPO/folder) for folder in ('scripts', 'src', 'tests'))
    test_argv = [python, '-B', '-m', 'unittest', '-v', *MODULES]
    test_started = time.monotonic()
    tests = subprocess.run(test_argv, cwd=REPO, env=test_environment,
        capture_output=True, timeout=180)
    stdout_pin = persist('final-tests-stdout.log', tests.stdout)
    test_stderr_pin = persist('final-tests-stderr.log', tests.stderr)
    match = re.search(rb'Ran (\d+) tests in ([0-9.]+)s', tests.stderr)
    if tests.returncode or match is None:
        raise RuntimeError('Activation platform adjacent suite failed')
    test_summary = {'schema': 'radio-native-v2-activation-platform-test-summary-v1',
        'argv': test_argv, 'test_modules': MODULES, 'test_count': int(match.group(1)),
        'unittest_seconds': float(match.group(2)),
        'parent_observed_seconds': time.monotonic()-test_started,
        'exit_code': tests.returncode,
        'logs': {'stdout': stdout_pin, 'stderr': test_stderr_pin},
        'large_source_generated': False, 'eight_input_resource_control_executed': False,
        'scientific_cases_run': 0, 'telescope_reads': 0}
    persist('final-test-summary.json', fixture.canonical(test_summary)+b'\n')
    summary = {'schema': 'radio-native-v2-activation-platform-result-v1',
        'status': 'BOUNDED_ACTIVATION_PLATFORM_VERIFIED_EXECUTION_BLOCKED',
        'plan': fixture.pin(PLAN), 'complete_freeze': fixture.pin(FREEZE),
        'parent_check': parent_pin, 'parent_stderr': stderr_pin,
        'activation_platform_contract_sha256':
            __import__('hashlib').sha256(fixture.canonical(expected_platform)).hexdigest(),
        'bounded_activation_platform_contract_verified': True,
        'secret_bearing_values_included': False,
        'operating_system_kernel_bytes_frozen': False,
        'activation_time_exact_recheck_required': True,
        'complete_parent_environment_frozen': True,
        'repository_code_files': len(freeze['repository_code_inventory']),
        'frozen_inputs': len(freeze['input_file_inventory']),
        'runtime_files': len(freeze['runtime_file_inventory']),
        'outer_final_report_lifetime_component_verified': True,
        'public_immutable_execution_preread_verified': False,
        'activation_guard_complete': False,
        'execution_authorized': False, 'reservation_authorized': False,
        'scientific_execution_authorized': False,
        'large_source_generation_admitted': False, 'large_inputs_generated': False,
        'eight_input_resource_control_executed': False,
        'native_case_reservations': 0, 'native_case_executions': 0,
        'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'network_fetches': 0, 'actual_connector_calls': 0,
        'actual_functions_sdk_calls': 0, 'automatic_retry': False,
        'elapsed_seconds': time.monotonic()-started}
    persist('verification-summary.json', fixture.canonical(summary)+b'\n')
    print(json.dumps({'status': summary['status'], 'tests': test_summary['test_count'],
        'test_seconds': test_summary['unittest_seconds'],
        'freeze_sha256': summary['complete_freeze']['sha256'],
        'platform_sha256': summary['activation_platform_contract_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
