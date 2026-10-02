#!/usr/bin/env python3
"""Reproduce the prospective escape guard and adjacent regression evidence."""
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

OUT = Path(__file__).parent
PYTHON = str(Path(sys.executable).resolve())
PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002f.plan.json'
SUPERVISOR = REPO/'scripts/radio_native_v2_process_tree_supervisor.py'
MODULES = [
    'tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission',
    'tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization',
    'tests.test_radio_native_v2_compact_preparation_audit',
    'tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze',
]


def persist(name, value):
    fixture.write(OUT/name, value)
    return fixture.pin(OUT/name)


def main():
    started = time.monotonic()
    # The test parent needs the frozen local Node/Python runtime search path.
    # Every protected child still validates its exact minimal environment.
    environment = dict(os.environ)
    environment['PYTHONPATH'] = ':'.join(str(REPO/folder) for folder in ('scripts', 'src', 'tests'))
    argv = [PYTHON, '-B', '-m', 'unittest', '-v', *MODULES]
    test_start = time.monotonic()
    process = subprocess.run(argv, cwd=REPO, env=environment, capture_output=True, timeout=180)
    stdout_pin = persist('final-tests-stdout.log', process.stdout)
    stderr_pin = persist('final-tests-stderr.log', process.stderr)
    match = re.search(rb'Ran (\d+) tests in ([0-9.]+)s', process.stderr)
    if process.returncode or match is None:
        raise RuntimeError('Adjacent regression suite failed; retained logs are authoritative')
    test_summary = {
        'schema': 'radio-native-v2-escape-guard-test-summary-v1',
        'argv': argv, 'test_modules': MODULES, 'test_count': int(match.group(1)),
        'unittest_seconds': float(match.group(2)),
        'parent_observed_seconds': time.monotonic()-test_start,
        'exit_code': process.returncode,
        'logs': {'final-tests-stdout.log': stdout_pin, 'final-tests-stderr.log': stderr_pin},
        'retained_failed_path_control': {
            'reason': 'Minimal PATH intentionally omitted the frozen Node executable; 86 setup errors and one helper failure retained.',
            'stdout': fixture.pin(OUT/'failed-path-test-stdout.log'),
            'stderr': fixture.pin(OUT/'failed-path-test-stderr.log')},
        'full_size_source_generated': False, 'eight_input_resource_control_executed': False,
        'scientific_cases_run': 0, 'telescope_reads': 0,
    }
    persist('final-test-summary.json', fixture.canonical(test_summary)+b'\n')

    scope = OUT/'escape-guard-control'
    control_argv = [PYTHON, '-I', '-S', '-B', str(SUPERVISOR), '--probe', 'escape-guard',
        '--scope', str(scope), '--seconds', '3', '--output-bytes', '65536',
        '--reaped-children', '64']
    observed, _, _ = fixture.observe_process(control_argv, OUT, 'escape-guard-control',
        scope/'supervisor-identity.json', deadline=time.monotonic()+8)
    receipt = json.loads((scope/'subreaper-receipt.json').read_bytes())
    expected_operations = ['clone-namespace-flags', 'clone3', 'io-uring-setup',
        'process-vm-read', 'process-vm-write', 'ptrace', 'setns', 'unshare']
    if not (receipt['status'] == 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE'
            and receipt['complete_descendant_wait_chain_verified'] is True
            and receipt['subreaper_scope_reaped_to_echild'] is True
            and receipt['child_escape_guard_installed_before_exec'] is True
            and receipt['child_escape_guard_no_new_privileges'] is True
            and receipt['child_escape_guard_seccomp_filter'] is True
            and receipt['child_escape_guard_denied_operations'] == expected_operations
            and observed['reported_identity_verified'] is True
            and observed['direct_child_reaped'] is True
            and observed['exit_code'] == 0
            and observed['reason'] is None
            and receipt['supervisor_identity'] == {
                'procfs_pid': observed['bound_child_identity']['procfs_pid'],
                'namespace_pid': observed['bound_child_identity']['namespace_pid']}):
        raise RuntimeError('Escape-guard control or outer observation did not close exactly')
    summary = {
        'schema': 'radio-native-v2-escape-guard-verification-v1',
        'status': 'DESCENDANT_ESCAPE_GUARD_COMPONENT_VERIFIED_EXECUTION_BLOCKED',
        'plan': fixture.pin(PLAN), 'supervisor': fixture.pin(SUPERVISOR),
        'architecture': os.uname().machine,
        'guard': {'no_new_privileges': True, 'seccomp_filter': True,
            'installed_before_exec': True, 'inherited_across_fork_and_exec': True,
            'denied_operations': expected_operations},
        'kernel_subreaper_reached_terminal_echild': True,
        'complete_descendant_wait_chain_component_verified': True,
        'outer_supervisor_receipt_fsync_and_termination_observed': True,
        'outer_observation': fixture.pin(OUT/'escape-guard-control-observation.json'),
        'subreaper_receipt': fixture.pin(scope/'subreaper-receipt.json'),
        'observed_seconds_through_supervisor_termination': observed['elapsed_seconds'],
        'maximum_individual_process_rss_bytes': max(
            observed['peak_rss_bytes'], observed['observer_self_kernel_peak_rss_bytes'],
            receipt['maximum_individual_process_rss_bytes']),
        'procfs_descendant_escape_detection_complete': False,
        'complete_process_tree_qualified': False,
        'outer_final_report_fsync_and_termination_independently_observed': False,
        'complete_runtime_closure_qualified': False,
        'public_immutable_execution_preread_verified': False,
        'complete_resource_measurement_join_qualified': False,
        'activation_guard_complete': False,
        'execution_authorized': False, 'reservation_authorized': False,
        'scientific_execution_authorized': False,
        'large_source_generation_admitted': False, 'large_inputs_generated': False,
        'eight_input_resource_control_executed': False,
        'native_case_reservations': 0, 'native_case_executions': 0,
        'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'network_fetches': 0, 'actual_connector_calls': 0,
        'actual_functions_sdk_calls': 0, 'automatic_retry': False,
        'verification_elapsed_seconds': time.monotonic()-started,
    }
    persist('verification-summary.json', fixture.canonical(summary)+b'\n')
    print(json.dumps({'status': summary['status'], 'tests': test_summary['test_count'],
        'test_seconds': test_summary['unittest_seconds'],
        'control_seconds': observed['elapsed_seconds'],
        'maximum_individual_process_rss_bytes': summary['maximum_individual_process_rss_bytes']},
        sort_keys=True))


if __name__ == '__main__':
    main()
