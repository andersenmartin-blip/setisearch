#!/usr/bin/env python3
"""Run all fourteen bounded modules, retaining attempts and checking fresh sources."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import types
import unittest

REPO = Path(__file__).resolve().parents[1]
HELPER = Path(__file__).parent/'prepare_snapshot.py'
helper = types.ModuleType('ledger_launch_suite_helpers'); helper.__file__ = str(HELPER)
raw_helper = HELPER.read_bytes()
if not 0 < len(raw_helper) <= 2*1024**2: raise ValueError('Bounded reviewed preparation helper required')
exec(compile(raw_helper, str(HELPER), 'exec'), helper.__dict__)
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
    'test_radio_native_v2_compact_control_launch',
    'test_prospective_source_metadata_radio',
)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if args.attempt < 1: raise ValueError('Positive distinct test attempt required')
    destination = Path(__file__).parent/f'final-suite-attempt-{args.attempt}-summary.json'
    if destination.exists(): raise ValueError('Existing suite attempt must be retained; choose a distinct attempt')
    bootstrap = None; imports = None; initial_pins = {}; pins = {}; result = None
    test_finder = None; host_audit_enabled = False; imports_complete = False
    infrastructure_failure = None; failure_frames = []; stage = 'exact_environment_bootstrap'
    started = time.monotonic()
    try:
        launcher, _, _, prior_freeze, bootstrap = helper.bootstrap_exact_environment()
        launcher.read_pinned(HELPER, expected={'bytes':len(raw_helper),
            'sha256':hashlib.sha256(raw_helper).hexdigest()})
        paths = set(prior_freeze['repository_code_inventory']) | {helper.LAUNCHER, *helper.WRAPPERS,
            'src/seti_repeater/prospective_source_metadata_radio.py',
            *(f'tests/{name}.py' for name in MODULES)}
        stage = 'initial_reviewed_source_snapshot'
        initial_pins = helper.current_source_pins(launcher, paths)
        stage = 'pinned_runtime_and_repository_import_bootstrap'
        imports = helper.reviewed_imports(launcher, prior_freeze, initial_pins)
        # Extend only test imports with the same held-byte source loader. The
        # NumPy/repository finder is exactly the launcher's implementation.
        class TestFinder:
            def find_spec(self, fullname, path=None, target=None):
                if fullname != 'tests' and not fullname.startswith('tests.'): return None
                if fullname == 'tests':
                    spec = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
                    spec.submodule_search_locations = [str(REPO/'tests')]
                    return spec
                relative = fullname.replace('.', '/')+'.py'
                if relative not in initial_pins: raise ImportError('Reviewed test source absent: '+fullname)
                loader = launcher._PinnedSourceLoader(str(REPO/relative), initial_pins[relative]['sha256'])
                return importlib.util.spec_from_loader(fullname, loader, is_package=False)
        test_finder = TestFinder(); sys.meta_path.insert(0, test_finder)
        os.environ['RUN_RUNTIME_CUSTODY_HOST_AUDIT'] = '1'; host_audit_enabled = True
        stage = 'all_fourteen_test_module_imports'
        import importlib
        suite = unittest.TestSuite()
        for name in MODULES:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('tests.'+name)))
        import radio_native_v2_compact_eight_case_resource_fixture as fixture
        paths.update(fixture.CODE_FILES)
        expanded_pins = helper.current_source_pins(launcher, paths)
        if any(expanded_pins[path] != pin for path, pin in initial_pins.items()):
            raise ValueError('Reviewed source changed during test import')
        initial_pins = expanded_pins
        imports_complete = True; stage = 'complete_test_suite'
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        stage = 'final_reviewed_source_snapshot'
        pins = helper.current_source_pins(launcher, paths)
    except BaseException as failure:
        # Retain a bounded failure disposition even when bootstrap, source
        # loading, imports or the runner fail before a unittest result exists.
        # Raw exception/environment values are left out of public metadata.
        infrastructure_failure = type(failure).__name__
        traceback = failure.__traceback__
        while traceback is not None and len(failure_frames) < 12:
            code = traceback.tb_frame.f_code
            failure_frames.append({'source_path':code.co_filename[:4096],
                'function':code.co_name[:128], 'line':traceback.tb_lineno})
            traceback = traceback.tb_next
    finally:
        if host_audit_enabled: os.environ.pop('RUN_RUNTIME_CUSTODY_HOST_AUDIT', None)
        if test_finder is not None and test_finder in sys.meta_path: sys.meta_path.remove(test_finder)
    elapsed = time.monotonic()-started
    unchanged = bool(initial_pins) and initial_pins == pins
    passed = (infrastructure_failure is None and result is not None
        and result.wasSuccessful() and not result.skipped and unchanged)
    summary = {'schema':'radio-native-v2-ledger-launch-preparation-adjacent-suite-v1',
        'status':'PASSED' if passed else 'FAILED', 'attempt':args.attempt,
        'requested_suite_argv':list(sys.argv),
        'test_count':result.testsRun if result is not None else 0,
        'failures':len(result.failures) if result is not None else 0,
        'errors':(len(result.errors) if result is not None else 0)+int(infrastructure_failure is not None),
        'skipped':len(result.skipped) if result is not None else 0,
        'seconds':round(elapsed,6), 'test_modules':list(MODULES),
        'host_runtime_audit_explicitly_enabled':host_audit_enabled,
        'host_audit_key_added_only_within_test_scope':host_audit_enabled,
        'test_bootstrap':bootstrap, 'test_import_policy':imports,
        'test_sources_imported_from_reviewed_bytes_without_pyc':imports_complete,
        'infrastructure_error_type':infrastructure_failure,
        'infrastructure_error_phase':stage if infrastructure_failure is not None else None,
        'infrastructure_error_source_frames':failure_frames,
        'infrastructure_raw_exception_or_environment_values_recorded':False,
        'source_and_test_pins':pins, 'initial_source_and_test_pins':initial_pins,
        'source_snapshot_unchanged':unchanged, 'protected_control_invocations':0,
        'large_source_generation_performed':False, 'new_real_activation_marker_created':False,
        'persistent_real_ledger_created_or_consumed':False,
        'scientific_cases_run':0, 'telescope_reads':0, 'rng_draws':0}
    raw = helper.canonical(summary)+b'\n'
    with destination.open('xb') as stream: stream.write(raw)
    if passed:
        with (Path(__file__).parent/'final-suite-summary.json').open('xb') as stream: stream.write(raw)
    print(raw.decode(), end='')
    raise SystemExit(not passed)


if __name__ == '__main__':
    main()
