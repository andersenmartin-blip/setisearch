#!/usr/bin/env python3
"""Exercise the fixed final-report writer and retain its independent wait4 join."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
for folder in (REPO/'scripts', REPO/'src'):
    sys.path.insert(0, str(folder))
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_resource_finalization as finalization

OUT = Path(__file__).parent
PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002h.plan.json'
FINALIZER = REPO/'scripts/radio_native_v2_resource_finalization.py'
MODULES = [
    'tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission',
    'tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization',
    'tests.test_radio_native_v2_activation_environment',
    'tests.test_radio_native_v2_compact_preparation_audit',
    'tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze',
]


def persist(name, value):
    fixture.write(OUT/name, value)
    return fixture.pin(OUT/name)


def main():
    started = time.monotonic()
    plan = json.loads(PLAN.read_bytes())
    if plan != fixture.build_plan(REPO):
        raise RuntimeError('Saved plan differs from the exact current prospective build')
    environment = dict(os.environ)
    environment['PYTHONPATH'] = ':'.join(str(REPO/folder) for folder in ('scripts', 'src', 'tests'))
    test_argv = [str(Path(sys.executable).resolve()), '-B', '-m', 'unittest', '-v', *MODULES]
    test_started = time.monotonic()
    process = subprocess.run(test_argv, cwd=REPO, env=environment,
        capture_output=True, timeout=180)
    stdout_pin = persist('final-tests-stdout.log', process.stdout)
    stderr_pin = persist('final-tests-stderr.log', process.stderr)
    match = re.search(rb'Ran (\d+) tests in ([0-9.]+)s', process.stderr)
    if process.returncode or match is None:
        raise RuntimeError('Adjacent final-report regression suite failed')
    test_summary = {'schema': 'radio-native-v2-final-report-lifetime-test-summary-v1',
        'argv': test_argv, 'test_modules': MODULES, 'test_count': int(match.group(1)),
        'unittest_seconds': float(match.group(2)),
        'parent_observed_seconds': time.monotonic()-test_started,
        'exit_code': process.returncode,
        'logs': {'stdout': stdout_pin, 'stderr': stderr_pin},
        'large_source_generated': False, 'eight_input_resource_control_executed': False,
        'scientific_cases_run': 0, 'telescope_reads': 0}
    persist('final-test-summary.json', fixture.canonical(test_summary)+b'\n')

    scope = OUT/'final-report-control'
    scope.mkdir(mode=0o700, exist_ok=False)
    report_input = {'schema': finalization.SCHEMA+'-final-report-input',
        'scope': str(scope), 'status': 'PENDING_FINAL_MEASUREMENT_JOIN',
        'control_kind': 'TINY_FINAL_REPORT_LIFETIME_ONLY',
        'complete_resource_measurement_join_qualified': False,
        'final_reporting_process_termination_covered': False,
        'final_disposition_persisted': False, **finalization.AUTHORITY}
    fixture.write(scope/finalization.FINAL_INPUT_NAME, report_input)
    input_pin = fixture.pin(scope/finalization.FINAL_INPUT_NAME)
    python = plan['runtime_executables']['python']['path']
    writer_argv = [python, '-I', '-S', '-B', str(FINALIZER),
        '--persist-final-report', '--scope', str(scope),
        '--input-bytes', str(input_pin['bytes']), '--input-sha256', input_pin['sha256']]
    observed, stdout, stderr = fixture.observe_process(writer_argv, scope,
        'final-report-writer', scope/finalization.FINAL_WRITER_IDENTITY_NAME,
        deadline=time.monotonic()+10, pipe_output=True)
    if stdout or stderr:
        raise RuntimeError('Fixed final-report writer emitted unexpected output')
    report_pin = fixture.pin(scope/finalization.FINAL_NAME)
    observation_pin = fixture.pin(scope/finalization.FINAL_WRITER_OBSERVATION_NAME)
    joined = finalization.join_final_report_lifetime(scope,
        expected_input_pin=input_pin, expected_report_pin=report_pin,
        expected_writer_observation_pin=observation_pin,
        expected_writer_argv=writer_argv)
    if not (joined['outer_report_fsync_and_termination_independently_observed'] is True
            and joined['final_reporting_process_termination_covered'] is True
            and joined['final_disposition_persisted'] is True
            and joined['complete_resource_measurement_join_qualified'] is False
            and joined['terminal_observer_own_future_termination_covered'] is False):
        raise RuntimeError('Final-report lifetime join did not retain its exact boundary')
    summary = {'schema': 'radio-native-v2-final-report-lifetime-result-v1',
        'status': 'FINAL_REPORT_WRITER_LIFETIME_COMPONENT_VERIFIED_EXECUTION_BLOCKED',
        'plan': fixture.pin(PLAN), 'finalizer': fixture.pin(FINALIZER),
        'input': input_pin, 'persisted_report': report_pin,
        'writer_observation': observation_pin,
        'writer_identity': fixture.pin(scope/finalization.FINAL_WRITER_IDENTITY_NAME),
        'writer_observed_seconds': observed['elapsed_seconds'],
        'maximum_individual_process_rss_bytes': max(observed['peak_rss_bytes'],
            observed['observer_self_kernel_peak_rss_bytes']),
        'report_file_and_parent_directory_fsynced_before_writer_return': True,
        'report_writer_complete_lifetime_wait4_observed': True,
        'outer_report_fsync_and_termination_independently_observed': True,
        'terminal_observer_own_future_termination_covered': False,
        'complete_resource_measurement_join_qualified': False,
        'complete_runtime_closure_qualified': False,
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
        'verification_elapsed_seconds': time.monotonic()-started}
    persist('verification-summary.json', fixture.canonical(summary)+b'\n')
    print(json.dumps({'status': summary['status'], 'tests': test_summary['test_count'],
        'test_seconds': test_summary['unittest_seconds'],
        'writer_seconds': observed['elapsed_seconds'],
        'maximum_individual_process_rss_bytes': summary['maximum_individual_process_rss_bytes']},
        sort_keys=True))


if __name__ == '__main__':
    main()
