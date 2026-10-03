#!/usr/bin/env python3
"""Metadata-only v3 source/runtime preparation and focused tests; no activation.

Run with the exact ten-value public environment and Python -I -S -B. All repo
and NumPy Python imports below compile held source bytes, bypassing cached pyc.
Attempts are create-only. A passing suite/freeze/audit grants no execution,
public-preread, claim-origin, whole-lifetime, scientific or telescope authority.
"""
import argparse
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import shutil
import sys
import sysconfig
import time
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
RESULTS=Path(__file__).resolve().parent
TEST_MODULES=('test_radio_native_v3_public_claim','test_radio_native_v3_dispatch_spending',
    'test_radio_native_v3_custody_observation','test_radio_native_v3_successor',
    'test_radio_native_v3_phase_reference','test_radio_native_v3_caller_queue',
    'test_radio_native_v3_command_evidence_index','test_radio_native_v3_engineering_observer',
    'test_radio_native_v3_public_source_proof','test_radio_native_v3_terminal_reference',
    'test_radio_native_v3_terminal_capacity')
AUTHORITY={'execution_authorized':False,'activation_authorized':False,
    'public_immutable_execution_preread_verified':False,'public_claim_origin_qualified':False,
    'public_claim_publisher_qualified':False,'complete_execution_runtime_closure_qualified':False,
    'whole_control_lifetime_qualified':False,'missing_original_storage_accounted':False,
    'original_identity_continuity_proved':False,'native_case_reservations':0,
    'native_case_executions':0,'scientific_cases_run':0,'rng_draws':0,'telescope_reads':0,
    'new_protected_control_invocations':0,'real_f_marker_created':False,
    'real_f_journal_created':False,'real_f_public_claim_created':False}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def raw_pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def read_source(path):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>2*1024**2:raise ValueError('Bounded ordinary source required')
        raw=b''
        while True:
            block=os.read(fd,65536)
            if not block:break
            raw+=block
        after=os.fstat(fd);named=os.stat(str(path),follow_symlinks=False)
        fields=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if fields(before)!=fields(after) or fields(after)!=fields(named):raise ValueError('Source changed during held read')
        return raw
    finally:os.close(fd)


class HeldLoader(importlib.abc.Loader):
    def __init__(self,path,raw):self.path=str(path);self.raw=raw
    def create_module(self,spec):return None
    def exec_module(self,module):
        if read_source(self.path)!=self.raw:raise ValueError('Held import source changed')
        module.__file__=self.path
        exec(compile(self.raw,self.path,'exec'),module.__dict__)


class SourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self):self.imports={}
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='seti_repeater' or fullname.startswith('seti_repeater.'):
            stem=ROOT/'src'/Path(*fullname.split('.'))
        elif fullname.startswith(('radio_native_v2_','radio_native_v3_')):
            stem=ROOT/'scripts'/fullname
        elif fullname in TEST_MODULES:
            stem=ROOT/'tests'/fullname
        elif fullname=='numpy' or fullname.startswith('numpy.'):
            stem=Path(sysconfig.get_path('purelib'))/Path(*fullname.split('.'))
        else:return None
        package=(stem/'__init__.py').is_file();selected=stem/'__init__.py' if package else stem.with_suffix('.py')
        if not selected.is_file():return None
        raw=read_source(selected);self.imports[str(selected)]=raw_pin(raw)
        return importlib.util.spec_from_file_location(fullname,selected,
            loader=HeldLoader(selected,raw),submodule_search_locations=[str(stem)] if package else None)


def write(path,value):
    raw=canonical(value)+b'\n'
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return raw_pin(raw)


def absence():
    names=('config/radio_native_v3_control_activation_20261003f.activate.json',
        'config/radio_native_v3_control_spent_20261003f.claim.json',
        '.radio-native-v3-invocation-ledger-20261003f',
        'results_radio_native_v3_predispatch_20261003f',
        'results_radio_native_v3_compact_eight_input_control_20261003f')
    return {name:not os.path.lexists(ROOT/name) for name in names}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True)
    parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError('Exact -I -S -B required')
    if not 1<=args.attempt<=9999:raise ValueError('Bounded fresh attempt number required')
    runtime_dirs=[]
    for executable in (sys.executable,shutil.which('node'),shutil.which('git'),'/usr/bin/x','/bin/x'):
        directory=str(Path(executable).resolve().parent) if executable not in ('/usr/bin/x','/bin/x') else str(Path(executable).parent)
        if directory not in runtime_dirs:runtime_dirs.append(directory)
    expected={'PATH':':'.join(runtime_dirs),'LANG':'C','LC_ALL':'C','HOME':'/nonexistent',
        'PYTHONSAFEPATH':'1','PYTHONNOUSERSITE':'1','GIT_CONFIG_NOSYSTEM':'1',
        'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_NO_LAZY_FETCH':'1'}
    if dict(os.environ)!=expected:raise ValueError('Exact ten-value public environment required')
    sys.path.extend((str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests'),sysconfig.get_path('purelib')))
    finder=SourceFinder();sys.meta_path.insert(0,finder)
    scope=RESULTS/('execution-preparation-attempt-'+str(args.attempt))
    if args.preflight_only:
        plan=json.loads((scope/'plan.json').read_bytes());freeze=json.loads((scope/'complete-freeze.json').read_bytes())
        path=ROOT/'scripts/radio_native_v3_compact_control_launch.py';raw=read_source(path)
        launcher=types.ModuleType('held_metadata_launcher');launcher.__file__=str(path)
        exec(compile(raw,str(path),'exec'),launcher.__dict__)
        result=launcher.preflight(plan,freeze)
        write(scope/'launcher-preflight.json',{'launcher_source_pin':raw_pin(raw),'preflight':result,**AUTHORITY})
        print(canonical({'status':'READ_ONLY_LAUNCHER_PREFLIGHT_PASSED','attempt':args.attempt,**AUTHORITY}).decode());return
    if not all(absence().values()):raise ValueError('Real f artifacts unexpectedly present')
    scope.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    import radio_native_v3_compact_eight_case_resource_fixture as fixture
    plan=fixture.build_plan(ROOT);plan_pin=write(scope/'plan.json',plan)
    initial={path:fixture.pin(ROOT/path) for path in fixture.CODE_FILES}
    tests=unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(tests)
    with (scope/'focused-suite.log').open('x') as f:f.write(log.getvalue())
    summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skips':len(result.skipped),'successful':result.wasSuccessful(),'modules':list(TEST_MODULES),
        'test_process_isolated_no_site_no_bytecode':True,'public_environment':expected,
        'synthetic_temporary_claims_only':True,**AUTHORITY}
    write(scope/'focused-suite-summary.json',summary)
    if not result.wasSuccessful():raise ValueError('Focused preparation suite failed; attempt retained')
    # The observer/supervisor tests require a cold single-threaded parent.
    # NumPy's import-time BLAS pool belongs to the later metadata freeze,
    # so import it only after those actual child-lifetime tests have closed.
    import radio_native_v3_runner_freeze as freezer
    import radio_native_v3_compact_preparation_audit as audit
    input_paths=[path for path in fixture.CODE_FILES if path.startswith('tests/') or path in plan['historical_storage_inputs']]
    input_paths.extend((str((scope/'plan.json').relative_to(ROOT)),str(Path(__file__).resolve().relative_to(ROOT))))
    input_paths.append(str((RESULTS/'qualify-guarded-execution-preparation.py').relative_to(ROOT)))
    freeze=freezer.capture(ROOT,input_paths);freeze_pin=write(scope/'complete-freeze.json',freeze)
    audited=audit.audit(plan,freeze,repo=ROOT);audit_pin=write(scope/'preparation-audit.json',audited)
    after={path:fixture.pin(ROOT/path) for path in fixture.CODE_FILES}
    if initial!=after or not all(absence().values()):raise ValueError('Selected source preservation or f absence failed')
    write(scope/'held-import-source-pins.json',finder.imports)
    output={'schema':'radio-native-v3-portable-preparation-result-v1','status':'CURRENT_ROOT_PREPARATION_VERIFIED_EXECUTION_BLOCKED',
        'attempt':args.attempt,'elapsed_seconds':time.monotonic()-started,'plan_pin':plan_pin,
        'complete_freeze_pin':freeze_pin,'preparation_audit_pin':audit_pin,'suite':summary,
        'repository_code_files':len(freeze['repository_code_inventory']),'input_files':len(freeze['input_file_inventory']),
        'runtime_files':len(freeze['runtime_file_inventory']),'selected_material_files':len(after),
        'source_and_test_pins':after,'bootstrap_source_pins':{
            'fixture':{name:getattr(fixture,name) for name in ('WORKER_ADMISSION_IMPLEMENTATION_PIN','CONTROL_ACTIVATION_IMPLEMENTATION_PIN',
                'INVOCATION_SPENDING_IMPLEMENTATION_PIN','HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN','PUBLIC_CLAIM_IMPLEMENTATION_PIN')},
            'launcher':__import__('radio_native_v3_compact_control_launch').BOOTSTRAP_SOURCE_PINS},
        'derived_pins':plan['derived_code'],'real_f_absence':absence(),**AUTHORITY}
    write(scope/'preparation-result.json',output)
    print(canonical({key:output[key] for key in ('status','attempt','elapsed_seconds','repository_code_files','input_files','runtime_files','selected_material_files')}).decode())


if __name__=='__main__':main()
