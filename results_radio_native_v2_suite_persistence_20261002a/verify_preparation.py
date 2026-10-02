#!/usr/bin/env python3
"""Independent blocked audit performed in the actual exact activation environment."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import types
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
HELPER = Path(__file__).parent/'prepare_snapshot.py'
FRESH_FREEZE = REPO/'config/radio_native_v2_suite_persistence_20261002a.runtime.json'


def read_bounded(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
            raise ValueError('Bounded sole-link verification bootstrap material required')
        raw = os.read(fd, maximum+1); after = os.fstat(fd)
        key = lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if len(raw) != before.st_size or key(before) != key(after) or key(after) != key(path.lstat()):
            raise ValueError('Verification bootstrap material changed during descriptor read')
        return raw
    finally: os.close(fd)


fresh_freeze_bootstrap = json.loads(read_bounded(FRESH_FREEZE, 16*1024**2))
helper = types.ModuleType('ledger_launch_preparation_helpers'); helper.__file__ = str(HELPER)
raw_helper = read_bounded(HELPER, 2*1024**2)
import hashlib
if hashlib.sha256(raw_helper).hexdigest() != fresh_freeze_bootstrap['input_sha256s'].get(
        str(HELPER.relative_to(REPO))):
    raise ValueError('Preparation helper differs from frozen dependency before source exec')
exec(compile(raw_helper, str(HELPER), 'exec'), helper.__dict__)
PLAN = REPO/helper.PLAN
FREEZE = REPO/helper.FREEZE

PREFLIGHT_BOOTSTRAP = r'''import hashlib,json,os,stat,sys,types
from pathlib import Path
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
 raise ValueError('Actual isolated no-site no-bytecode preflight required')
launcher_path,launcher_pin_json,plan_path,plan_pin_json,freeze_path,freeze_pin_json=sys.argv[1:]
wanted=json.loads(launcher_pin_json)
fd=os.open(launcher_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 before=os.fstat(fd)
 if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=2*1024**2:
  raise ValueError('Bounded sole-link independently frozen launcher source required')
 chunks=[];remaining=before.st_size+1
 while remaining:
  chunk=os.read(fd,min(65536,remaining))
  if not chunk:break
  chunks.append(chunk);remaining-=len(chunk)
 raw=b''.join(chunks);after=os.fstat(fd)
 key=lambda value:(value.st_dev,value.st_ino,value.st_mode,value.st_nlink,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
 if len(raw)!=before.st_size or key(before)!=key(after) or key(after)!=key(os.stat(launcher_path,follow_symlinks=False)):
  raise ValueError('Frozen launcher source changed before preflight exec')
 if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=wanted:
  raise ValueError('Independent frozen launcher source pin differs before exec')
finally:os.close(fd)
module=types.ModuleType('fresh_preparation_preflight_launcher');module.__file__=launcher_path
exec(compile(raw,launcher_path,'exec'),module.__dict__)
_,plan_raw=module.read_pinned(plan_path,expected=json.loads(plan_pin_json),maximum=16*1024**2,retain=True)
_,freeze_raw=module.read_pinned(freeze_path,expected=json.loads(freeze_pin_json),maximum=16*1024**2,retain=True)
plan=module._json(plan_raw);freeze=module._json(freeze_raw)
result=module.preflight(plan,freeze)
result['actual_preflight_argv']=list(sys.orig_argv)
result['actual_preflight_environment_keys']=sorted(os.environ)
result['actual_preflight_environment_sha256']=hashlib.sha256(module.canonical(dict(os.environ))).hexdigest()
result['fresh_process_no_preloaded_controlled_modules']=True
print(module.canonical(result).decode())
'''


def verify():
    launcher_expected_pin = {'bytes':len(read_bounded(REPO/helper.LAUNCHER, 2*1024**2)),
        'sha256':fresh_freeze_bootstrap['code_sha256s'][helper.LAUNCHER]}
    launcher, environment, _, _, bootstrap = helper.bootstrap_exact_environment(launcher_expected_pin)
    launcher.read_pinned(HELPER, expected={'bytes':len(raw_helper),
        'sha256':helper.hashlib.sha256(raw_helper).hexdigest()})
    plan, _ = environment.read_json(PLAN); freeze, _ = environment.read_json(FREEZE)
    if launcher_expected_pin != plan['code_files'][helper.LAUNCHER]:
        raise ValueError('Fresh plan and frozen launcher bootstrap pin disagree')
    exact = environment.expected_environment(plan, freeze)
    preflight_argv = [plan['runtime_executables']['python']['path'], '-I', '-S', '-B', '-c',
        PREFLIGHT_BOOTSTRAP, str(REPO/helper.LAUNCHER), helper.canonical(launcher_expected_pin).decode(),
        str(PLAN), helper.canonical(launcher.read_pinned(PLAN)[0]).decode(),
        str(FREEZE), helper.canonical(launcher.read_pinned(FREEZE)[0]).decode()]
    preflight_observation, preflight_stdout, preflight_stderr = launcher.observe_child(
        preflight_argv, exact, deadline_monotonic_ns=time.monotonic_ns()+180*10**9,
        stdout_cap=launcher.STDOUT_CAP, stderr_cap=launcher.STDERR_CAP)
    if (preflight_observation['exit_code'] != 0 or preflight_observation['reason'] is not None
            or not preflight_observation['direct_child_reaped'] or preflight_stderr):
        raise RuntimeError('Fresh actual preflight failed: '+preflight_stderr.decode('utf-8','replace'))
    fresh_preflight = json.loads(preflight_stdout)
    if (fresh_preflight['status'] != 'LOCAL_PREFLIGHT_RECOMPUTED'
            or fresh_preflight.get('fresh_process_no_preloaded_controlled_modules') is not True
            or fresh_preflight['actual_preflight_environment_keys'] != sorted(exact)):
        raise ValueError('Complete fresh actual exact-environment preflight proof required')
    code_pins = {relative:launcher.read_pinned(REPO/relative, maximum=2*1024**2)[0]
        for relative in freeze['repository_code_inventory']}
    if {relative:pin['sha256'] for relative, pin in code_pins.items()} != freeze['code_sha256s']:
        raise ValueError('Fresh frozen repository source bytes differ before audit imports')
    imports = helper.reviewed_imports(launcher, freeze, code_pins)
    import radio_native_v2_compact_preparation_audit as audit
    actual_fingerprints = audit.environment_fingerprints()
    if actual_fingerprints != freeze['environment_fingerprints']:
        raise ValueError('Independent audit actual environment differs from fresh freeze')
    if environment.expected_environment(plan, freeze) != dict(os.environ):
        raise ValueError('Independent audit must actually run in the fresh exact ten-value environment')
    actual_parent = environment.validate(plan, freeze, dict(os.environ))
    with tempfile.TemporaryDirectory(prefix='seti-ledger-launch-preparation-') as temporary:
        root = Path(temporary); code = root/'frozen-code'; derived = root/'derived'
        for relative in audit.fixture.CODE_FILES:
            destination = code/relative; destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((REPO/relative).read_bytes())
        derived.mkdir()
        for name, raw in audit.fixture.templates((REPO/audit.fixture.CODE_FILES[0]).read_text()).items():
            (derived/name).write_bytes(raw)
        result = audit.audit(plan, freeze, repo=REPO,
            materialized_code_root=code, derived_root=derived)
    with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('No Git/process allowed')):
        with mock.patch.object(audit.freezer.custody, 'bounded_inventory',
                side_effect=AssertionError('No activation alias scan allowed')):
            audit.freezer.validate_material_runtime_custody(freeze)
    argv = [plan['runtime_executables']['python']['path'], '-I', '-S', '-B',
        str(REPO/'scripts/radio_native_v2_activation_environment.py'),
        '--check-only', '--plan', str(PLAN), '--complete-freeze', str(FREEZE)]
    process = subprocess.run(argv, env=exact, capture_output=True, timeout=30)
    if process.returncode or process.stderr:
        raise RuntimeError('Exact parent checker failed: '+process.stderr.decode('utf-8', 'replace'))
    parent = json.loads(process.stdout)
    if not parent['isolated_no_site_no_bytecode'] or not parent['bounded_activation_platform_contract_verified']:
        raise ValueError('Actual isolated parent/platform check required')
    for key in ('spent_control_rearmed', 'source_worker_activation_receipt_delivery_complete',
            'one_invocation_spending_enforced', 'complete_resource_measurement_join_qualified'):
        if plan[key] is not False: raise ValueError('Preparation cannot claim actual completion: '+key)
    for key in ('source_worker_activation_receipt_delivery_prepared',
            'durable_one_invocation_spending_prepared', 'persistent_ledger_storage_accounting_prepared',
            'activation_environment_runtime_join_prepared', 'outer_control_termination_observer_prepared'):
        if plan[key] is not True: raise ValueError('Expected bounded preparation capability absent: '+key)
    if plan['execution_status'] != 'BLOCKED_PREPARATION_REVIEW':
        raise ValueError('Blocked preparation status required')
    return {'schema':'radio-native-v2-ledger-launch-preparation-verification-v1',
        'status':'PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED', 'audit':result,
        'audit_bootstrap':bootstrap, 'audit_import_policy':imports,
        'audit_actual_environment_fingerprints':actual_fingerprints,
        'actual_environment_fingerprints_equal_fresh_freeze':True,
        'fresh_actual_launch_preflight':fresh_preflight,
        'fresh_actual_launch_preflight_observation':preflight_observation,
        'fresh_actual_launch_preflight_stdout_pin':{'bytes':len(preflight_stdout),
            'sha256':hashlib.sha256(preflight_stdout).hexdigest()},
        'fresh_actual_launch_preflight_stderr_pin':{'bytes':len(preflight_stderr),
            'sha256':hashlib.sha256(preflight_stderr).hexdigest()},
        'audit_itself_actual_parent_check':actual_parent, 'actual_parent_check':parent,
        'actual_parent_checker_argv':argv, 'actual_parent_environment_keys':sorted(exact),
        'material_only_no_process_or_alias_scan_verified':True,
        'plan_file_pin':audit.pin(PLAN,sole_link=True), 'freeze_file_pin':audit.pin(FREEZE,sole_link=True),
        'runtime_paths':len(freeze['runtime_file_inventory']),
        'hardlink_groups':len(freeze['runtime_custody_manifest']['hardlink_groups']),
        'activation_only_paths':len(freeze['runtime_custody_manifest']['activation_only_paths']),
        'material_runtime_paths':freeze['runtime_custody_manifest']['material_runtime_paths'],
        'hardlink_alias_closure_paths':freeze['runtime_custody_manifest']['hardlink_alias_closure_paths'],
        'material_code_files':len(plan['code_files']), 'derived_files':len(plan['derived_code']),
        'protected_control_invocations':0, 'new_real_activation_markers_created':0,
        'persistent_ledger_created_or_consumed':False, 'large_inputs_generated':False,
        'scientific_cases_run':0, 'rng_draws':0, 'telescope_reads':0,
        'native_case_reservations':0, 'native_case_executions':0,
        'external_person_messages_sent':0, 'automatic_retry':False}


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, separators=(',', ':'), allow_nan=False))
