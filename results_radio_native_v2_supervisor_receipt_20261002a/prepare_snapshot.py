#!/usr/bin/env python3
"""Fresh blocked snapshot captured inside the actual exact activation environment.

The historical m plan/freeze supply bootstrap executable/NumPy paths only.
Their ambient environment fingerprints are deliberately NOT reused as current
evidence. Fixture/freezer/audit imports occur after an exact -I -S -B reexec.
No protected control, ledger, marker, source generator or telescope is invoked.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO/'results_radio_native_v2_supervisor_receipt_20261002a'
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261002o.plan.json'
FREEZE = 'config/radio_native_v2_supervisor_receipt_20261002a.runtime.json'
PRIOR_PLAN = 'config/radio_native_v2_compact_eight_input_control_20261002n.plan.json'
PRIOR_FREEZE = 'config/radio_native_v2_ledger_launch_20261002a.runtime.json'
LAUNCHER = 'scripts/radio_native_v2_compact_control_launch.py'
WRAPPERS = tuple('results_radio_native_v2_supervisor_receipt_20261002a/'+name for name in
    ('prepare_snapshot.py', 'verify_preparation.py', 'run_adjacent_suite.py'))


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
    proof = {'schema':'radio-native-v2-ledger-launch-preparation-bootstrap-v1',
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
    # The m runtime supplies immutable installed runtime bytes only. Current
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
    launcher, environment, _, prior_freeze, bootstrap = bootstrap_exact_environment()
    tests, _ = environment.read_json(RESULTS/'final-suite-summary.json')
    if (tests['status'] != 'PASSED' or tests['failures'] or tests['errors'] or tests['skipped']
            or tests.get('source_snapshot_unchanged') is not True):
        raise ValueError('Complete recorded passing suite without skips required before snapshot')
    if current_source_pins(launcher, tests['source_and_test_pins']) != tests['source_and_test_pins']:
        raise ValueError('Reviewed source/test changed after passing suite')
    imports = reviewed_imports(launcher, prior_freeze, tests['source_and_test_pins'])
    import radio_native_v2_compact_eight_case_resource_fixture as fixture
    import radio_native_v2_runner_freeze as freezer
    plan = fixture.build_plan(REPO)
    write_new(PLAN, plan)
    inputs = sorted({PLAN, *WRAPPERS,
        'tests/test_radio_native_v2_compact_preparation_audit.py',
        'tests/test_radio_native_v2_compact_run_verifier.py',
        'tests/test_radio_native_v2_runner_freeze.py',
        'tests/test_prospective_source_metadata_radio.py',
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
    print(canonical({'schema':'radio-native-v2-ledger-launch-preparation-capture-v1',
        'status':'FRESH_BLOCKED_PREPARATION_CREATED', 'plan':PLAN, 'complete_freeze':FREEZE,
        'capture_bootstrap':bootstrap, 'capture_import_policy':imports,
        'capture_actual_environment_fingerprints':freeze['environment_fingerprints'],
        'actual_environment_fingerprints_equal_fresh_freeze':True,
        'protected_control_invoked':False, 'new_activation_marker_created':False,
        'persistent_ledger_created_or_consumed':False, 'large_inputs_generated':False}).decode())


if __name__ == '__main__':
    main()
