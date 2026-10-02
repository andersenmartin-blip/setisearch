#!/usr/bin/env python3
"""Retain bounded machine-agent test and read-only original b observations."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
MODULES = ('scripts/radio_native_v2_historical_observation.py',
    'scripts/radio_native_v2_compact_eight_case_resource_fixture.py',
    'scripts/radio_native_v2_historical_storage.py',
    'tests/test_radio_native_v2_historical_observation.py',
    'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def pin(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, raw):
    with path.open('xb') as target:
        target.write(raw); target.flush(); os.fsync(target.fileno())


initial = {path: pin(REPO / path) for path in MODULES}
targets = ['tests.test_radio_native_v2_historical_observation'] + [
    'tests.test_radio_native_v2_compact_eight_case_resource_fixture.CompactEightPreparationTests.' + name
    for name in ('test_workload_storage_charges_all_history_and_reservations_to_future_cases',
        'test_workload_storage_cannot_skip_history_or_use_missing_future_case_roots',
        'test_workload_storage_external_share_can_close_an_otherwise_small_scope')]
argv = [sys.executable, '-B', '-m', 'unittest', *targets, '-v']
env = dict(os.environ); env['PYTHONPATH'] = str(REPO / 'scripts')
test = subprocess.run(argv, cwd=REPO, env=env, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, timeout=30, check=False)
write(OUT / 'ledger-review-integration-tests.stdout.log', test.stdout)
write(OUT / 'ledger-review-integration-tests.stderr.log', test.stderr)
source = REPO / MODULES[0]
spec = importlib.util.spec_from_file_location('retained_readonly_history_adapter_probe', source)
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
root = helper.ORIGINAL_REPOSITORY_ROOT
scope = root + '/results_radio_native_v2_compact_control_20261002c'
plan = {'invocation_repository_root': root,
    'invocation_ledger_root': root + '/.radio-native-v2-invocation-ledger-20261002c',
    'historical_storage_inputs': helper.HISTORICAL_INPUT_PINS,
    'code_files': {**helper.HISTORICAL_INPUT_PINS,
        helper.STORAGE_SOURCE: helper.STORAGE_IMPLEMENTATION_PIN}}
freeze = {'input_sha256s': {path: wanted['sha256']
    for path, wanted in helper.HISTORICAL_INPUT_PINS.items()}}
_, historical_scope, historical_ledger = helper.observe_historical_storage(str(REPO),
    plan=plan, freeze=freeze, repository_root=root, execution_scope=scope)
write(OUT / 'ledger-review-live-b-scope-observation.json', canonical(historical_scope) + b'\n')
write(OUT / 'ledger-review-live-b-ledger-observation.json', canonical(historical_ledger) + b'\n')
final = {path: pin(REPO / path) for path in MODULES}
result = {'schema': 'seti-control-integration-ledger-agent-evidence-v1',
    'reviewer': 'machine_agent_ledger_review', 'independent_human_review_claimed': False,
    'test_count': 15, 'test_exit_code': test.returncode, 'test_argv': argv,
    'initial_source_pins': initial, 'final_source_pins': final,
    'source_bytes_unchanged_during_probe': initial == final,
    'historical_input_pins': helper.HISTORICAL_INPUT_PINS,
    'historical_input_map_sha256': helper.HISTORICAL_INPUT_MAP_SHA256,
    'minimal_adapter_plan': plan, 'minimal_adapter_input_freeze': freeze,
    'production_complete_freeze_authenticated': False,
    'production_control_admission_claimed': False, 'point_in_time_read_only_observation': True,
    'historical_scope_entry_count': historical_scope['entry_count'],
    'historical_scope_logical_bytes': historical_scope['logical_bytes'],
    'historical_ledger_entry_count': historical_ledger['entry_count'],
    'historical_ledger_logical_bytes': historical_ledger['logical_bytes'],
    'c_journal_accessed': False, 'invocation_consumed': False,
    'activation_marker_written': False, 'control_executed': False,
    'lifetime_accounting_proved': False, 'whole_control_qualified': False,
    'artifacts': {path.name: pin(path) for path in (
        OUT / 'ledger-review-integration-tests.stdout.log',
        OUT / 'ledger-review-integration-tests.stderr.log',
        OUT / 'ledger-review-live-b-scope-observation.json',
        OUT / 'ledger-review-live-b-ledger-observation.json')}}
write(OUT / 'ledger-review-integration-evidence.json', canonical(result) + b'\n')
print(canonical({'test_exit_code': test.returncode,
    'source_bytes_unchanged_during_probe': initial == final,
    'historical_scope_entry_count': historical_scope['entry_count'],
    'historical_ledger_entry_count': historical_ledger['entry_count']}).decode())
if test.returncode or initial != final: raise SystemExit(1)
