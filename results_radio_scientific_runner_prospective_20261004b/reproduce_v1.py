"""Read-only v1 review with the original explicitly token-built test fixture.

No scientific admission is claimed; the fixture is copied from v1's own test.
Only temporary tiny child processes and their synthetic evidence are created.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'results_radio_scientific_runner_prospective_20261004a')]
from test_bounded_scientific_runner import RunnerTests


def reproduce():
    fixture = RunnerTests()
    fixture.setUp()
    try:
        raw, pin = fixture.spec(fixture.success_code())
        first = fixture.run_spec(raw, pin, name='original-identity-first').record()
        second = fixture.run_spec(raw, pin, name='original-identity-second').record()
        empty = fixture.envelope(live_clock_record={
            'checked_before_and_after_every_loader_attempt': True,
            'nondecreasing_integer_observations': []})
        raw_empty, pin_empty = fixture.spec(fixture.success_code(empty))
        result_empty = fixture.run_spec(raw_empty, pin_empty, name='empty-clock').record()
        return {
            'schema': 'radio-runner-v1-concrete-gap-review-v1',
            'fixture_domain': 'original-v1-token-built-synthetic-unit-fixture',
            'duplicate_dispatch': {
                'dispatch_identity': first['dispatch_identity'],
                'same_spec': first['spec_sha256'] == second['spec_sha256'],
                'first_status': first['status'], 'second_status': second['status'],
                'different_destination_bypasses_one_shot': second['status'] == 'QUALIFIED'},
            'empty_per_load_clock': {
                'status': result_empty['status'],
                'observations': result_empty['child_result']['live_clock_record'][
                    'nondecreasing_integer_observations'],
                'empty_clock_accepted': result_empty['status'] == 'QUALIFIED'},
            'scientific_execution_authorized': False,
            'telescope_values_opened': False,
            'v1_source_modified': False}
    finally:
        fixture.tearDown()


if __name__ == '__main__':
    print(json.dumps(reproduce(), sort_keys=True, separators=(',', ':')))
