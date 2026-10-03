#!/usr/bin/env python3
"""Bounded cold-start preparation; never activate or run a protected control.

Reuse reviewed environment/import primitives, not the older helper's requirement
that c be absent. Both closed controls and their private spent journals are read
only. Every new output is exclusive, and all prior attempts are retained.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
import types
import unittest

REPO = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent
LEGACY = REPO/'results_radio_native_v2_control_integration_20261002a/prepare_snapshot.py'
PLAN = 'config/radio_native_v2_cold_driver_preparation_20261003a.plan.json'
FREEZE = 'config/radio_native_v2_cold_driver_preparation_20261003a.runtime.json'
PROTECTED = (
    'results_radio_native_v2_compact_control_20261002b',
    'results_radio_native_v2_compact_control_20261002c',
    '.radio-native-v2-invocation-ledger',
    '.radio-native-v2-invocation-ledger-20261002c',
)
AUTHORITY = dict(execution_authorized=False, scientific_execution_authorized=False,
    protected_control_invocations=0, new_real_activation_marker_created=False,
    persistent_real_ledger_created_or_consumed=False, large_inputs_generated=False,
    scientific_cases_run=0, telescope_reads=0, rng_draws=0, automatic_retry=False,
    spent_c_reused=False, new_activation_identity_prepared=False)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'


def pin(path):
    raw = Path(path).read_bytes()
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def stable_historical_pin(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    key = lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
        info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Sole-link regular historical file required')
        digest = hashlib.sha256(); count = 0
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            digest.update(raw); count += len(raw)
        after = os.fstat(fd)
        if key(before) != key(after) or key(after) != key(path.lstat()) or count != before.st_size:
            raise ValueError('Historical file changed during descriptor read')
        return {'bytes':count, 'sha256':digest.hexdigest()}, after
    finally: os.close(fd)


def held_source(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2*1024**2:
            raise ValueError('Bounded sole-link bootstrap source required')
        chunks = []; remaining = before.st_size+1
        while remaining:
            raw = os.read(fd, min(65536, remaining))
            if not raw: break
            chunks.append(raw); remaining -= len(raw)
        raw = b''.join(chunks); after = os.fstat(fd)
        key = lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if len(raw) != before.st_size or key(before) != key(after) or key(after) != key(path.lstat()):
            raise ValueError('Bootstrap source changed during held read')
        return raw
    finally: os.close(fd)


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())


def protected_state():
    result = {}
    for relative in PROTECTED:
        root = REPO/relative
        if not root.is_dir() or root.is_symlink():
            raise ValueError('Existing closed control or spent journal missing: '+relative)
        paths = [root, *sorted(root.rglob('*'))]
        entries = {}
        for path in paths:
            info = path.lstat()
            key = str(path.relative_to(REPO))
            if stat.S_ISDIR(info.st_mode):
                record = {'kind':'directory'}
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                checked, after = stable_historical_pin(path)
                if (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns) != (
                        after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                    raise ValueError('Historical file changed before descriptor read')
                record = {'kind':'file', **checked}
            else:
                raise ValueError('Unexpected alias/special historical path: '+key)
            record.update(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                links=info.st_nlink, size=info.st_size, mtime_ns=info.st_mtime_ns,
                ctime_ns=info.st_ctime_ns)
            entries[key] = record
        result[relative] = entries
    return result


def setup():
    helper = types.ModuleType('cold_preparation_legacy_primitives')
    helper.__file__ = str(LEGACY)
    # Legacy bootstrap loads source bytes and reexecutes into its exact ten-key
    # environment with -I -S -B; its historical c-absent validator is unused.
    raw = held_source(LEGACY)
    executed_legacy_pin = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
    exec(compile(raw, str(LEGACY), 'exec'), helper.__dict__)
    launcher, _, _, prior_freeze, bootstrap = helper.bootstrap_exact_environment()
    modules = (*helper.EXPECTED_TEST_MODULES,
        'test_radio_native_v2_cold_driver_admission',
        'test_radio_native_v2_observer_terminal_identity')
    paths = set(prior_freeze['repository_code_inventory']) | {
        'src/seti_repeater/prospective_source_metadata_radio.py',
        str(Path(__file__).relative_to(REPO)), str(LEGACY.relative_to(REPO)),
        *(f'tests/{name}.py' for name in modules)}
    paths.update(str(path.relative_to(REPO))
        for folder in ('scripts', 'src/seti_repeater')
        for path in (REPO/folder).rglob('*')
        if path.is_file() and '__pycache__' not in path.parts
        and path.suffix in ('.py','.js','.mjs','.cjs','.c','.h','.sh'))
    paths.update(str(path.relative_to(REPO)) for path in (REPO/'tests').glob('*.py'))
    pins = helper.current_source_pins(launcher, paths)
    if pins[str(LEGACY.relative_to(REPO))] != executed_legacy_pin:
        raise ValueError('Executed legacy bootstrap bytes differ from source snapshot')
    bootstrap['legacy_helper_executed_pin'] = executed_legacy_pin
    imports = helper.reviewed_imports(launcher, prior_freeze, pins)
    return helper, launcher, modules, paths, pins, bootstrap, imports


def suite(attempt):
    if (RESULTS/f'final-suite-attempt-{attempt}-summary.json').exists():
        raise FileExistsError('Existing attempt must be retained')
    started = time.monotonic()
    helper, launcher, modules, paths, initial, bootstrap, imports = setup()
    before = protected_state()
    write(RESULTS/f'suite-attempt-{attempt}-protected-before.json', before)
    class TestFinder:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'tests':
                spec = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
                spec.submodule_search_locations = [str(REPO/'tests')]
                return spec
            if fullname.startswith('tests.'):
                relative = fullname.replace('.', '/')+'.py'
            elif fullname.startswith('test_'):
                relative = 'tests/'+fullname+'.py'
            else:
                return None
            if relative not in initial:
                raise ImportError('Unreviewed test source: '+fullname)
            loader = launcher._PinnedSourceLoader(str(REPO/relative), initial[relative]['sha256'])
            return importlib.util.spec_from_loader(fullname, loader, is_package=False)
    finder = TestFinder(); sys.meta_path.insert(0, finder)
    os.environ['RUN_RUNTIME_CUSTODY_HOST_AUDIT'] = '1'
    try:
        tests = unittest.TestSuite()
        for name in modules:
            tests.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('tests.'+name)))
        result = unittest.TextTestRunner(verbosity=2).run(tests)
    finally:
        os.environ.pop('RUN_RUNTIME_CUSTODY_HOST_AUDIT', None)
        sys.meta_path.remove(finder)
    after = protected_state()
    write(RESULTS/f'suite-attempt-{attempt}-protected-after.json', after)
    final = helper.current_source_pins(launcher, paths)
    passed = result.wasSuccessful() and not result.skipped and initial == final and before == after
    summary = {'schema':'radio-native-v2-preparation-adjacent-suite-v2',
        'attempt':attempt, 'status':'PASSED' if passed else 'FAILED',
        'test_count':result.testsRun, 'failures':len(result.failures),
        'errors':len(result.errors), 'skipped':len(result.skipped),
        'seconds':round(time.monotonic()-started,6), 'test_modules':list(modules),
        'source_snapshot_unchanged':initial == final,
        'initial_source_and_test_pins':initial, 'source_and_test_pins':final,
        'protected_history_and_spent_journals_unchanged':before == after,
        'closed_b_and_c_remain_present_and_spent':True,
        'test_bootstrap':bootstrap, 'test_import_policy':imports,
        'legacy_c_absence_validator_not_used':True,
        'qualification_scope':'synthetic software preparation; no whole-control lifetime or science',
        **AUTHORITY}
    store = importlib.import_module('radio_native_v2_preparation_suite_store')
    store.record_attempt(RESULTS, attempt, canonical(summary))
    print(json.dumps({key:summary[key] for key in ('status','test_count','failures','errors','skipped','seconds','protected_history_and_spent_journals_unchanged')}))
    return 0 if passed else 1


def capture(attempt, suite_sha256):
    helper, launcher, modules, _, _, bootstrap, imports = setup()
    summary_path = RESULTS/f'final-suite-attempt-{attempt}-summary.json'
    store = importlib.import_module('radio_native_v2_preparation_suite_store')
    summary, selected = store.read_selected_summary(RESULTS, attempt, suite_sha256, REPO)
    if summary.get('test_modules') != list(modules):
        raise ValueError('Complete expected adjacent module set required')
    if summary.get('protected_history_and_spent_journals_unchanged') is not True:
        raise ValueError('Passing protected history observation required')
    if summary.get('closed_b_and_c_remain_present_and_spent') is not True:
        raise ValueError('Closed historical controls must remain present and spent')
    if any(summary.get(key) != value for key,value in AUTHORITY.items()):
        raise ValueError('Selected preparation must preserve all blocked authority fields')
    fixture = importlib.import_module('radio_native_v2_compact_eight_case_resource_fixture')
    freezer = importlib.import_module('radio_native_v2_runner_freeze')
    audit = importlib.import_module('radio_native_v2_compact_preparation_audit')
    plan = fixture.build_plan(REPO, invocation_repository_root=REPO)
    write(REPO/PLAN, plan)
    inputs = sorted({*(str(p.relative_to(REPO)) for p in (REPO/'tests').glob('*.py')),
        *fixture.HISTORICAL_INPUT_PATHS, PLAN, str(Path(__file__).relative_to(REPO)),
        str(LEGACY.relative_to(REPO)), str(summary_path.relative_to(REPO)),
        'results_radio_native_v2_control_activation_20261002c/public-c-spend-record-copy.json',
        'results_radio_native_v2_control_activation_20261002c/single-launch-terminal.json'})
    inputs = sorted(set(inputs) | {
        str(path.relative_to(REPO))
        for directory in (RESULTS, REPO/'results_radio_native_v2_cold_writer_diagnosis_20261003a')
        for path in directory.rglob('*') if path.is_file()})
    freeze = freezer.capture(REPO, inputs)
    verified = audit.audit(plan, freeze, repo=REPO)
    final_summary, final_selected = store.read_selected_summary(RESULTS, attempt, suite_sha256, REPO)
    if final_summary != summary or final_selected != selected:
        raise ValueError('Selected passing summary changed during capture/audit')
    for relative, expected in summary['source_and_test_pins'].items():
        if relative in freeze['code_sha256s']:
            observed = freeze['code_sha256s'][relative]
        elif relative in freeze['input_sha256s']:
            observed = freeze['input_sha256s'][relative]
        else:
            # Historical preparation paths from prior source inventory are
            # checked by selected-summary reread; material closure uses current
            # source inventory plus its explicitly registered inputs.
            continue
        if observed != expected['sha256']:
            raise ValueError('Fresh freeze differs from passing suite source: '+relative)
    write(REPO/FREEZE, freeze)
    report = {'schema':'radio-native-v2-cold-driver-blocked-preparation-v1',
        'status':'PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED',
        'plan':{'path':PLAN, **pin(REPO/PLAN)},
        'runtime':{'path':FREEZE, **pin(REPO/FREEZE)},
        'selected_suite':selected, 'capture_bootstrap':bootstrap, 'capture_import_policy':imports,
        'audit':verified, 'repository_code_files':len(freeze['code_sha256s']),
        'input_files':len(freeze['input_sha256s']), 'runtime_files':len(freeze['runtime_sha256s']),
        'material_files':len(plan['code_files']),
        'spent_c_journal_in_plan_is_historical_and_ineligible_for_activation':True,
        'future_distinct_identity_and_c_history_storage_join_still_required':True,
        **AUTHORITY}
    write(RESULTS/'fresh-blocked-preparation.json', report)
    print(json.dumps({key:report[key] for key in ('status','repository_code_files','input_files','runtime_files','material_files')}))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('suite','capture'))
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--suite-sha256')
    args = parser.parse_args()
    if not 1 <= args.attempt <= 1_000_000:
        raise ValueError('Distinct bounded attempt number required')
    if args.action == 'capture' and args.suite_sha256 is None:
        raise ValueError('Independent retained passing suite digest required for capture')
    raise SystemExit(suite(args.attempt) if args.action == 'suite' else capture(args.attempt, args.suite_sha256))
