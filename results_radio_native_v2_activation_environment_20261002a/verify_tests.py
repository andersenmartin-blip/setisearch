#!/usr/bin/env python3
"""Run and retain the adjacent blocked-preparation regression suite."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'scripts'))
import radio_native_v2_compact_eight_case_resource_fixture as fixture

OUT = Path(__file__).parent
MODULES = ['tests.test_radio_native_v2_compact_eight_case_resource_fixture',
    'tests.test_radio_native_v2_worker_admission',
    'tests.test_radio_native_v2_process_tree_supervisor',
    'tests.test_radio_native_v2_resource_finalization',
    'tests.test_radio_native_v2_activation_environment',
    'tests.test_radio_native_v2_compact_preparation_audit',
    'tests.test_radio_native_v2_compact_run_verifier',
    'tests.test_radio_native_v2_runner_freeze']


def main():
    argv = [str(Path(sys.executable).resolve()), '-B', '-m', 'unittest', '-v', *MODULES]
    environment = dict(os.environ)
    environment['PYTHONPATH'] = ':'.join(str(REPO/folder) for folder in ('scripts', 'src', 'tests'))
    started = time.monotonic()
    process = subprocess.run(argv, cwd=REPO, env=environment, capture_output=True, timeout=180)
    fixture.write(OUT/'final-tests-stdout.log', process.stdout)
    fixture.write(OUT/'final-tests-stderr.log', process.stderr)
    match = re.search(rb'Ran (\d+) tests in ([0-9.]+)s', process.stderr)
    if process.returncode or match is None: raise RuntimeError('Final adjacent suite failed')
    summary = {'schema': 'radio-native-v2-activation-environment-test-summary-v1',
        'argv': argv, 'test_modules': MODULES, 'test_count': int(match.group(1)),
        'unittest_seconds': float(match.group(2)),
        'parent_observed_seconds': time.monotonic()-started, 'exit_code': process.returncode,
        'logs': {'stdout': fixture.pin(OUT/'final-tests-stdout.log'),
            'stderr': fixture.pin(OUT/'final-tests-stderr.log')},
        'large_source_generated': False, 'eight_input_resource_control_executed': False,
        'scientific_cases_run': 0, 'telescope_reads': 0}
    fixture.write(OUT/'final-test-summary.json', summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__': main()
