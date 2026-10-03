#!/usr/bin/env python3
"""Capture tested joint b/c history and distinct d sources; keep output logs outside frozen inputs.

This preparation creates no marker, ledger or invocation. Both historical scopes
and spent journals remain closed. A complete independent audit runs again after
persisting the distinct plan/runtime files, with exact selected suite pins.

"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import types

REPO = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent
PLAN = 'config/radio_native_v2_joint_history_preparation_20261003a.plan.json'
FREEZE = 'config/radio_native_v2_joint_history_preparation_20261003a.runtime.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'


def write(path, value):
    with path.open('xb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())


def pin(path):
    raw = path.read_bytes()
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def main(attempt, suite_sha256):
    helper_path = RESULTS/'verify_checkpoint.py'
    # Bootstrap stable held bytes without importing cached source bytecode.
    fd = os.open(helper_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd); raw = b''
        if before.st_nlink != 1 or not 0 < before.st_size <= 2*1024**2:
            raise ValueError('Bounded sole-link preparation helper required')
        while len(raw) <= before.st_size:
            chunk = os.read(fd, 65536)
            if not chunk: break
            raw += chunk
        after = os.fstat(fd)
        identity = lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if len(raw) != before.st_size or identity(before) != identity(after) or identity(after) != identity(helper_path.lstat()):
            raise ValueError('Preparation helper changed during held read')
    finally: os.close(fd)
    module = types.ModuleType('held_tested_preparation_helper'); module.__file__ = str(helper_path)
    exec(compile(raw, str(helper_path), 'exec'), module.__dict__)
    _, launcher, modules, _, current_pins, bootstrap, imports = module.setup()
    if current_pins[str(helper_path.relative_to(REPO))] != {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:
        raise ValueError('Executed preparation helper differs from tested snapshot')
    store = importlib.import_module('radio_native_v2_preparation_suite_store')
    summary, selected = store.read_selected_summary(RESULTS, attempt, suite_sha256, REPO)
    if summary.get('test_modules') != list(modules):
        raise ValueError('Complete expected passing module set required')
    for name in ('source_snapshot_unchanged','protected_history_and_spent_journals_unchanged',
            'closed_b_and_c_remain_present_and_spent',
            'new_d_marker_ledger_scope_and_launch_config_absence_checked_before_and_after'):
        if summary.get(name) is not True:
            raise ValueError('Required passing preparation observation absent: '+name)
    if any(summary.get(key) != value for key,value in module.AUTHORITY.items()):
        raise ValueError('All blocked authority fields must remain unchanged')
    fixture = importlib.import_module('radio_native_v2_compact_eight_case_resource_fixture')
    freezer = importlib.import_module('radio_native_v2_runner_freeze')
    audit = importlib.import_module('radio_native_v2_compact_preparation_audit')
    plan = fixture.build_plan(REPO, invocation_repository_root=REPO)
    write(REPO/PLAN, plan)
    inputs = {*(str(path.relative_to(REPO)) for path in (REPO/'tests').glob('*.py')),
        *fixture.HISTORICAL_INPUT_PATHS, PLAN,
        str(module.LEGACY.relative_to(REPO)), str(helper_path.relative_to(REPO)),
        str(Path(__file__).relative_to(REPO)),
        'results_radio_native_v2_control_activation_20261002c/public-c-spend-record-copy.json',
        'results_radio_native_v2_control_activation_20261002c/single-launch-terminal.json'}
    # Every selected tested source is explicitly frozen, even if the generic
    # repository inventory excludes historical wrapper locations.
    inputs.update(summary['source_and_test_pins'])
    for directory in (RESULTS,):
        inputs.update(str(path.relative_to(REPO)) for path in directory.rglob('*') if path.is_file())
    # The caller redirects stdout/stderr outside these evidence directories.
    # Refuse any active output inode in the input set, even through an alias.
    active = {(os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in (1,2)}
    for relative in inputs:
        info = (REPO/relative).lstat()
        if (info.st_dev,info.st_ino) in active:
            raise ValueError('Active output log cannot be a frozen input: '+relative)
    freeze = freezer.capture(REPO, sorted(inputs))
    first_audit = audit.audit(plan, freeze, repo=REPO)
    final_summary, final_selected = store.read_selected_summary(RESULTS, attempt, suite_sha256, REPO)
    if final_summary != summary or final_selected != selected:
        raise ValueError('Selected suite changed during capture')
    for relative, expected in summary['source_and_test_pins'].items():
        observed = freeze['code_sha256s'].get(relative, freeze['input_sha256s'].get(relative))
        if observed != expected['sha256']:
            raise ValueError('Freeze differs from tested source: '+relative)
    write(REPO/FREEZE, freeze)
    # Independently rebuild all local inventories after persisted output. This
    # detects mutable input/log mistakes before a successful record is written.
    persisted_plan = json.loads((REPO/PLAN).read_text())
    persisted_freeze = json.loads((REPO/FREEZE).read_text())
    final_audit = audit.audit(persisted_plan, persisted_freeze, repo=REPO)
    if final_audit != first_audit:
        raise ValueError('Persisted snapshot differs from initial independent audit')
    store.read_selected_summary(RESULTS, attempt, suite_sha256, REPO)
    report = {'schema':'radio-native-v2-joint-history-final-blocked-preparation-v1',
        'status':'PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED',
        'plan':{'path':PLAN, **pin(REPO/PLAN)}, 'runtime':{'path':FREEZE, **pin(REPO/FREEZE)},
        'selected_suite':selected, 'test_count':summary['test_count'],
        'capture_bootstrap':bootstrap, 'capture_import_policy':imports,
        'audit':final_audit, 'persisted_snapshot_independently_reaudited':True,
        'active_stdout_stderr_not_frozen_inputs':True,
        'separately_reviewed_metadata_adapter':{'path':str(Path(__file__).relative_to(REPO)), **pin(Path(__file__))},
        'production_and_test_sources_equal_selected_passing_suite':True,
        'repository_code_files':len(freeze['code_sha256s']),
        'input_files':len(freeze['input_sha256s']), 'runtime_files':len(freeze['runtime_sha256s']),
        'material_files':len(plan['code_files']),
        'distinct_d_identity_prepared_without_marker_ledger_or_invocation':True,
        'both_historical_scopes_and_spent_journals_in_mandatory_live_accounting':True,
        'fresh_immutable_preread_and_separate_activation_still_required':True,
        'original_historical_spend_identity_continuity_qualified':False,
        'actual_live_historical_admission_currently_refused':True,
        **module.AUTHORITY}
    write(RESULTS/'final-blocked-preparation.json', report)
    print(json.dumps({key:report[key] for key in ('status','repository_code_files','input_files','runtime_files','material_files')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--suite-sha256', required=True)
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    main(args.attempt, args.suite_sha256)
