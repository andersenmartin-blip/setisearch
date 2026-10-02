#!/usr/bin/env python3
"""Run the twelve relevant engineering test modules, including the explicit host audit."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import unittest

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO/'scripts'), str(REPO/'src'), str(REPO/'tests')]
MODULES = (
    'test_radio_native_v2_compact_eight_case_resource_fixture',
    'test_radio_native_v2_worker_admission',
    'test_radio_native_v2_process_tree_supervisor',
    'test_radio_native_v2_resource_finalization',
    'test_radio_native_v2_activation_environment',
    'test_radio_native_v2_compact_preparation_audit',
    'test_radio_native_v2_compact_run_verifier',
    'test_radio_native_v2_runner_freeze',
    'test_radio_native_v2_control_activation',
    'test_radio_native_v2_runtime_custody',
    'test_radio_native_v2_invocation_spending',
    'test_radio_native_v2_source_receipt',
)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if args.attempt < 1:
        raise ValueError('Positive distinct test attempt required')
    os.environ['RUN_RUNTIME_CUSTODY_HOST_AUDIT'] = '1'
    suite = unittest.TestSuite()
    for name in MODULES:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('tests.'+name)))
    import radio_native_v2_compact_eight_case_resource_fixture as fixture
    paths = {*fixture.CODE_FILES,
        'scripts/radio_native_v2_compact_preparation_audit.py',
        'scripts/radio_native_v2_runner_freeze.py',
        *(f'tests/{name}.py' for name in MODULES)}
    def source_pins():
        return {relative:{'bytes':len((REPO/relative).read_bytes()),
            'sha256':hashlib.sha256((REPO/relative).read_bytes()).hexdigest()}
            for relative in sorted(paths)}
    initial_pins = source_pins()
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed = time.monotonic()-started
    pins = {}
    for relative in sorted(paths):
        raw = (REPO/relative).read_bytes()
        pins[relative] = {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    unchanged = initial_pins == pins
    passed = result.wasSuccessful() and not result.skipped and unchanged
    summary = {'schema':'radio-native-v2-admission-spending-preparation-adjacent-suite-v1',
        'status':'PASSED' if passed else 'FAILED', 'attempt':args.attempt,
        'test_count':result.testsRun, 'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'seconds':round(elapsed,6),
        'test_modules':list(MODULES),'host_runtime_audit_explicitly_enabled':True,
        'source_and_test_pins':pins,'initial_source_and_test_pins':initial_pins,
        'source_snapshot_unchanged':unchanged,'protected_control_invocations':0,
        'large_source_generation_performed':False,'new_real_activation_marker_created':False,
        'scientific_cases_run':0,'telescope_reads':0,'rng_draws':0}
    raw = (json.dumps(summary,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    destination = Path(__file__).parent/f'final-suite-attempt-{args.attempt}-summary.json'
    with destination.open('xb') as stream:
        stream.write(raw)
    if passed:
        with (Path(__file__).parent/'final-suite-summary.json').open('xb') as stream:
            stream.write(raw)
    print(raw.decode(),end='')
    raise SystemExit(not passed)
