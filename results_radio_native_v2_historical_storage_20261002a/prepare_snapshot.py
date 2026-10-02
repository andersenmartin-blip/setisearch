#!/usr/bin/env python3
"""Fresh blocked snapshot captured inside the actual exact activation environment.

The prior p plan/freeze supply bootstrap executable/NumPy paths only.
Their environment fingerprints are not reused as current evidence. The registered
33-file material control remains b; standalone historical/candidate components
are preparation inputs only. Imports follow an exact -I -S -B reexec.
No protected control, ledger, marker, source generator or telescope is invoked.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO/'results_radio_native_v2_historical_storage_20261002a'
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261002q.plan.json'
FREEZE = 'config/radio_native_v2_historical_storage_20261002a.runtime.json'
PRIOR_PLAN = 'config/radio_native_v2_compact_eight_input_control_20261002p.plan.json'
PRIOR_FREEZE = 'config/radio_native_v2_suite_persistence_20261002a.runtime.json'
LAUNCHER = 'scripts/radio_native_v2_compact_control_launch.py'
SUITE_STORE = 'scripts/radio_native_v2_preparation_suite_store.py'
SUITE_STORE_PIN = {'bytes': 9380, 'sha256': '3f6edc5221a698942e2ce24ccba2d953d04d8ece770855511bf6d7c08c3af472'}
WRAPPERS = tuple('results_radio_native_v2_historical_storage_20261002a/'+name for name in
    ('prepare_snapshot.py', 'verify_preparation.py', 'run_adjacent_suite.py'))


EXPECTED_TEST_MODULES = (
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
    'test_radio_native_v2_preparation_suite_store',
    'test_radio_native_v2_historical_storage',
    'test_radio_native_v2_prospective_spending',
    'test_radio_native_v2_historical_spending_join',
)

# Explicitly include sources absent from the prior repository inventory before
# installing the held-byte repository loader or importing any new tests.
PREPARATION_ONLY_COMPONENTS = (
    'scripts/radio_native_v2_historical_storage.py',
    'scripts/radio_native_v2_prospective_spending.py',
)
NEW_TEST_INPUTS = (
    'tests/test_radio_native_v2_historical_storage.py',
    'tests/test_radio_native_v2_prospective_spending.py',
    'tests/test_radio_native_v2_historical_spending_join.py',
)
EXTRA_REVIEWED_SOURCE_PATHS = (*PREPARATION_ONLY_COMPONENTS, *NEW_TEST_INPUTS)
HISTORICAL_INPUT_PATHS = (
    'results_radio_native_v2_historical_storage_20261002a/historical-scope-manifest.json',
    'results_radio_native_v2_historical_storage_20261002a/historical-scope-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/historical-ledger-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/historical-ledger-manifest.json',
    'results_radio_native_v2_historical_storage_20261002a/historical-ledger-spend-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-result.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json',
    'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-observation-result.json',
    'results_radio_native_v2_historical_storage_20261002a/historical-input-public-readback.json',
    'results_radio_native_v2_historical_storage_20261002a/observe_historical_storage.py',
    'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py',
    'results_radio_native_v2_compact_control_20261002b/activation-receipt.json',
    'results_radio_native_v2_compact_control_20261002b/invocation-spending.json',
    'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json',
    'results_radio_native_v2_fresh_activation_20261002c_candidate/control_activation_candidate.py',
    'results_radio_native_v2_fresh_activation_20261002c_candidate/candidate-test-attempt-2-result.json',
)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def checked_launcher(expected_pin=None):
    # Directly execute this reviewed source, avoiding an unchecked repository
    # pyc before the launcher can enforce its independent bootstrap literals.
    path = REPO/LAUNCHER
    raw = path.read_bytes()
    if not 0 < len(raw) <= 2*1024**2:
        raise ValueError('Bounded reviewed preparation launcher source required')
    observed_pin = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
    if expected_pin is not None and observed_pin != expected_pin:
        raise ValueError('Preparation launcher differs from actual frozen pin before exec')
    module = types.ModuleType('preparation_checked_launcher'); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    # Establish its own stable descriptor pin after loading; source snapshots
    # and the fresh complete freeze also bind this dependency independently.
    pin, observed = module.read_pinned(path, maximum=2*1024**2, retain=True)
    if observed != raw: raise ValueError('Preparation launcher changed during source load')
    return module, pin


def bootstrap_exact_environment(launcher_expected_pin=None):
    launcher, launcher_pin = checked_launcher(launcher_expected_pin)
    environment = launcher._source_module('radio_native_v2_activation_environment',
        'scripts/radio_native_v2_activation_environment.py')
    prior_plan, prior_plan_pin = environment.read_json(REPO/PRIOR_PLAN)
    prior_freeze, prior_freeze_pin = environment.read_json(REPO/PRIOR_FREEZE)
    exact = environment.expected_environment(prior_plan, prior_freeze)
    if len(exact) != 10: raise ValueError('Exact ten-value activation environment required')
    python = prior_plan['runtime_executables']['python']
    expected_python = {'bytes':python['bytes'], 'sha256':python['sha256']}
    launcher.read_pinned(python['path'], expected=expected_python, sole_link=False)
    flags = bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)
    if (dict(os.environ) != exact or not flags
            or str(Path(sys.executable).resolve()) != python['path']
            or list(sys.orig_argv[1:4]) != ['-I', '-S', '-B']):
        os.execve(python['path'], [python['path'], '-I', '-S', '-B',
            str(Path(sys.argv[0]).absolute()), *sys.argv[1:]], exact)
    if dict(os.environ) != exact or len(os.environ) != 10:
        raise ValueError('Actual capture/audit environment must have exactly ten keys')
    proof = {'schema':'radio-native-v2-historical-storage-preparation-bootstrap-v1',
        'actual_argv':list(sys.orig_argv), 'actual_environment_keys':sorted(os.environ),
        'actual_environment_sha256':hashlib.sha256(canonical(dict(os.environ))).hexdigest(),
        'actual_isolated_no_site_no_bytecode':flags,
        'actual_python_path':python['path'], 'actual_python_pin':expected_python,
        'checked_launcher_source_pin':launcher_pin,
        'bootstrap_prior_plan':{'path':PRIOR_PLAN, **prior_plan_pin},
        'bootstrap_prior_freeze':{'path':PRIOR_FREEZE, **prior_freeze_pin},
        'prior_snapshot_used_for_paths_only':True,
        'prior_ambient_environment_fingerprints_reused':False,
        'secret_bearing_ambient_environment_inherited':False,
        'ambient_environment_values_recorded':False,
        'protected_control_or_spend_called':False}
    return launcher, environment, prior_plan, prior_freeze, proof


def current_source_pins(launcher, relatives):
    return {relative:launcher.read_pinned(REPO/relative, maximum=2*1024**2)[0]
        for relative in sorted(set(relatives))}


def reviewed_imports(launcher, freeze, code_pins):
    """Same pinned fresh-source NumPy/repository loader as the real launcher."""
    for path, digest in freeze['runtime_sha256s'].items():
        if launcher.read_pinned(path, sole_link=False)[0]['sha256'] != digest:
            raise ValueError('Bootstrap runtime changed before no-site NumPy import')
    roots = [path[:-len('/numpy/__init__.py')] for path in freeze['runtime_sha256s']
        if path.endswith('/numpy/__init__.py')]
    if len(roots) != 1: raise ValueError('Unique pinned no-site NumPy import root required')
    numpy_site = launcher._absolute(roots[0]); directory = launcher._directory(numpy_site)
    os.close(directory)
    # The prior runtime supplies immutable installed runtime bytes only. Current
    # repository sources come from the current reviewed passing-suite snapshot
    # (or, for the suite itself, its initial source observation), never old code.
    source_freeze = {'runtime_sha256s':freeze['runtime_sha256s'],
        'code_sha256s':{relative:pin['sha256'] for relative, pin in code_pins.items()
            if relative.startswith(('scripts/', 'src/'))}}
    for relative, expected in launcher.BOOTSTRAP_SOURCE_PINS.items():
        if type(expected) is not dict or code_pins.get(relative) != expected:
            raise ValueError('Reviewed preparation bootstrap differs from launcher literal: '+relative)
    finder = launcher._PinnedPreflightFinder(source_freeze, numpy_site)
    sys.meta_path.insert(0, finder)
    sys.path[:0] = [str(REPO), str(REPO/'scripts'), str(REPO/'src'), str(REPO/'tests')]
    sys.path.append(numpy_site)
    return {'numpy_site_path_derived_from_pinned_runtime':numpy_site,
        'numpy_repository_imports_use_launcher_pinned_source_loader':True,
        'numpy_repository_source_imports_bypass_cached_bytecode':True,
        'explicit_no_site_numpy_import_root':True}


def write_new(relative, value):
    path = REPO/relative
    with path.open('xb') as stream:
        raw = canonical(value)+b'\n'; position = 0
        while position < len(raw):
            written = stream.write(raw[position:])
            if written <= 0: raise OSError('Incomplete exclusive preparation write')
            position += written
        stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


def main():
    launcher, environment, prior_plan, prior_freeze, bootstrap = bootstrap_exact_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite-attempt', type=int, required=True)
    parser.add_argument('--suite-sha256', required=True)
    args = parser.parse_args()
    # The first selection read is bounded and pinned before any repository import.
    relative = SUITE_STORE
    pin, raw_store = launcher.read_pinned(REPO/relative, expected=SUITE_STORE_PIN, maximum=2*1024**2, retain=True)
    suite_store = types.ModuleType('preparation_suite_store'); suite_store.__file__ = str(REPO/relative)
    exec(compile(raw_store, suite_store.__file__, 'exec'), suite_store.__dict__)
    tests, selected_pin = suite_store.read_selected_summary(RESULTS, args.suite_attempt, args.suite_sha256, REPO)
    if tests['source_and_test_pins'].get(relative) != pin:
        raise ValueError('Suite store differs from selected passing-suite source pin')
    if tests.get('test_modules') != list(EXPECTED_TEST_MODULES):
        raise ValueError('All eighteen declared test modules required for capture')
    if (tests['status'] != 'PASSED' or tests['failures'] or tests['errors'] or tests['skipped']
            or tests.get('source_snapshot_unchanged') is not True):
        raise ValueError('Complete recorded passing suite without skips required before snapshot')
    if current_source_pins(launcher, tests['source_and_test_pins']) != tests['source_and_test_pins']:
        raise ValueError('Reviewed source/test changed after passing suite')
    imports = reviewed_imports(launcher, prior_freeze, tests['source_and_test_pins'])
    import radio_native_v2_compact_eight_case_resource_fixture as fixture
    import radio_native_v2_runner_freeze as freezer
    plan = fixture.build_plan(REPO)
    if canonical(plan) != canonical(prior_plan):
        raise ValueError('Registered b material plan must remain byte-identical to prior p preparation')
    if set(PREPARATION_ONLY_COMPONENTS) & set(plan['code_files']):
        raise ValueError('Standalone candidate components must not enter registered material control')
    write_new(PLAN, plan)
    inputs = sorted({PLAN, *WRAPPERS, *NEW_TEST_INPUTS, *HISTORICAL_INPUT_PATHS,
        'tests/test_radio_native_v2_compact_preparation_audit.py',
        'tests/test_radio_native_v2_compact_run_verifier.py',
        'tests/test_radio_native_v2_runner_freeze.py',
        'tests/test_prospective_source_metadata_radio.py',
        'tests/test_radio_native_v2_preparation_suite_store.py',
        str((RESULTS/selected_pin['path']).relative_to(REPO)),
        'results_radio_hd189733_metadata_preparation_20261002a/evidence_pins.json',
        'results_radio_hd189733_metadata_preparation_20261002a/evidence_origin.json',
        'results_radio_hd189733_metadata_preparation_20261002a/output_pins.json',
        'results_radio_hd189733_metadata_preparation_20261002a/prospective_wrapper.json',
        'results_radio_hd189733_metadata_preparation_20261002a/admission_matrix.json',
        'results_radio_hd189733_metadata_preparation_20261002a/provenance_rebinding.json',
        *[path for path in json.loads((REPO/'results_radio_hd189733_metadata_preparation_20261002a/evidence_pins.json').read_bytes()) if path.endswith('.json')],
        *(path for path in fixture.CODE_FILES if path.startswith('tests/'))})
    freeze = freezer.capture(REPO, inputs)
    if freeze['environment_fingerprints'] != freezer.environment_fingerprints():
        raise ValueError('Actual exact-environment capture fingerprints differ')
    if environment.expected_environment(plan, freeze) != dict(os.environ):
        raise ValueError('Fresh snapshot activation environment differs from actual capture')
    environment.validate(plan, freeze, dict(os.environ))
    write_new(FREEZE, freeze)
    print(canonical({'schema':'radio-native-v2-historical-storage-preparation-capture-v1',
        'status':'FRESH_BLOCKED_PREPARATION_CREATED', 'plan':PLAN, 'complete_freeze':FREEZE,
        'selected_suite_attempt':args.suite_attempt, 'selected_suite_raw_pin':selected_pin,
        'shared_suite_alias_used':False, 'selected_complete_module_count':len(EXPECTED_TEST_MODULES),
        'preparation_only_component_paths':list(PREPARATION_ONLY_COMPONENTS),
        'historical_input_paths':list(HISTORICAL_INPUT_PATHS),
        'registered_material_plan_equals_prior_p':True,
        'standalone_components_registered_for_execution':False,
        'candidate_lifetime_or_execution_admitted':False,
        'verification_is_machine_self_review_not_independent_human_review':True,
        'capture_bootstrap':bootstrap, 'capture_import_policy':imports,
        'capture_actual_environment_fingerprints':freeze['environment_fingerprints'],
        'actual_environment_fingerprints_equal_fresh_freeze':True,
        'protected_control_invoked':False, 'new_activation_marker_created':False,
        'persistent_ledger_created_or_consumed':False, 'large_inputs_generated':False}).decode())


if __name__ == '__main__':
    main()
