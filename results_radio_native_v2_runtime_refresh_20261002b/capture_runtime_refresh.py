#!/usr/bin/env python3
"""Refresh the blocked runtime freeze after the final-report lifetime change."""
import json
from pathlib import Path
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
PLAN = REPO/'config/radio_native_v2_compact_eight_input_control_20261002h.plan.json'
FREEZE = REPO/'config/radio_native_v2_activation_environment_20261002b.runtime.json'
SELF = str(Path(__file__).relative_to(REPO))
INPUTS = [str(PLAN.relative_to(REPO)),
    *(path for path in fixture.CODE_FILES if path.startswith('tests/')),
    'tests/test_radio_native_v2_compact_preparation_audit.py',
    'results_radio_native_v2_final_report_lifetime_20261002a/verify_final_report_lifetime.py',
    SELF]


def main():
    started = time.monotonic()
    plan = json.loads(PLAN.read_bytes())
    if plan != fixture.build_plan(REPO):
        raise RuntimeError('Saved plan differs from exact current prospective build')
    freeze = freezer.capture(REPO, INPUTS)
    fixture.write(FREEZE, freeze)
    environment = activation.expected_environment(plan, freeze)
    python = plan['runtime_executables']['python']['path']
    argv = [python, '-I', '-S', '-B',
        str(REPO/'scripts/radio_native_v2_activation_environment.py'),
        '--check-only', '--plan', str(PLAN), '--complete-freeze', str(FREEZE)]
    process = subprocess.run(argv, cwd=REPO, env=environment,
        capture_output=True, timeout=60)
    fixture.write(OUT/'parent-check-stdout.json', process.stdout)
    fixture.write(OUT/'parent-check-stderr.log', process.stderr)
    if process.returncode or process.stderr:
        raise RuntimeError('Exact refreshed activation parent check failed')
    receipt = json.loads(process.stdout)
    if not (receipt['complete_parent_environment_frozen'] is True
            and receipt['secret_bearing_ambient_environment_inherited'] is False
            and receipt['environment'] == environment
            and receipt['observed_argv'] == argv
            and receipt['isolated_no_site_no_bytecode'] is True
            and receipt['activation_guard_complete'] is False):
        raise RuntimeError('Refreshed activation parent receipt differs')
    summary = {'schema': 'radio-native-v2-runtime-refresh-result-v1',
        'status': 'CURRENT_CODE_RUNTIME_FREEZE_REFRESHED_EXECUTION_BLOCKED',
        'plan': fixture.pin(PLAN), 'complete_freeze': fixture.pin(FREEZE),
        'parent_check': fixture.pin(OUT/'parent-check-stdout.json'),
        'parent_stderr': fixture.pin(OUT/'parent-check-stderr.log'),
        'frozen_inputs': len(freeze['input_file_inventory']),
        'repository_code_files': len(freeze['repository_code_inventory']),
        'runtime_files': len(freeze['runtime_file_inventory']),
        'complete_parent_environment_frozen': True,
        'secret_bearing_ambient_environment_inherited': False,
        'outer_final_report_lifetime_component_verified': True,
        'complete_runtime_closure_qualified': False,
        'operating_system_kernel_frozen': False,
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
    fixture.write(OUT/'verification-summary.json', summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
