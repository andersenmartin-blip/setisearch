#!/usr/bin/env python3
"""Create distinct blocked preparation JSON only after the recorded suite passes."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'src')]
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_runner_freeze as freezer

RESULTS = REPO/'results_radio_native_v2_admission_spending_20261002a'
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261002m.plan.json'
FREEZE = 'config/radio_native_v2_admission_spending_20261002a.runtime.json'


def write_new(relative, value):
    path = REPO/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(fixture.canonical(value)+b'\n')


if __name__ == '__main__':
    tests = json.loads((RESULTS/'final-suite-summary.json').read_bytes())
    if (tests['status'] != 'PASSED' or tests['failures'] or tests['errors'] or tests['skipped']
            or tests.get('source_snapshot_unchanged') is not True):
        raise ValueError('Complete recorded passing suite without skips required before snapshot')
    for relative, expected in tests['source_and_test_pins'].items():
        if fixture.pin(REPO/relative) != expected:
            raise ValueError('Reviewed source/test changed after passing suite: '+relative)
    write_new(PLAN, fixture.build_plan(REPO))
    inputs = sorted({PLAN,
        'results_radio_native_v2_admission_spending_20261002a/prepare_snapshot.py',
        'results_radio_native_v2_admission_spending_20261002a/verify_preparation.py',
        'results_radio_native_v2_admission_spending_20261002a/run_adjacent_suite.py',
        'tests/test_radio_native_v2_compact_preparation_audit.py',
        'tests/test_radio_native_v2_compact_run_verifier.py',
        'tests/test_radio_native_v2_runner_freeze.py',
        *(path for path in fixture.CODE_FILES if path.startswith('tests/'))})
    write_new(FREEZE, freezer.capture(REPO, inputs))
    print(fixture.canonical({'status':'FRESH_BLOCKED_PREPARATION_CREATED',
        'plan':PLAN,'complete_freeze':FREEZE,'protected_control_invoked':False,
        'new_activation_marker_created':False}).decode())
