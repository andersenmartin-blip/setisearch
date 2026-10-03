#!/usr/bin/env python3
"""Read-only F source-shape sizing and original source-pin recheck.

This compiles held source bytes and evaluates the existing bounded synthetic
capacity expressions. It does not capture a freeze, run a test suite, activate,
consume a preclaim, launch a control, or open any historical private journal.
Only the two fixed, create-only operator result files are written.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import sysconfig
import types

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent
PREPARATION = RESULTS/'execution-preparation-attempt-1'
SUITE = ROOT/'results_radio_native_v2_archive_contract_20261003a/suite-attempt-2-summary.json'
CONSTRUCTOR = 'src/seti_repeater/prospective_source_metadata_radio.py'
CONSTRUCTOR_PIN = {'bytes':31819, 'sha256':'2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360'}
F_NAMES = (
    'config/radio_native_v3_control_activation_20261003f.activate.json',
    'config/radio_native_v3_control_spent_20261003f.claim.json',
    '.radio-native-v3-invocation-ledger-20261003f',
    'results_radio_native_v3_predispatch_20261003f',
    'results_radio_native_v3_compact_eight_input_control_20261003f')
AUTHORITY = {'execution_authorized':False,'activation_authorized':False,
    'scientific_execution_authorized':False,'complete_resource_measurement_join_qualified':False,
    'actual_retained_storage_measured':False,'protected_control_invocations':0,
    'scientific_cases_run':0,'telescope_reads':0,'rng_draws':0,'test_suites_rerun':0}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def read(path, maximum=16*1024**2):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:
            raise ValueError('Bounded ordinary metadata/source file required')
        raw=b''
        while True:
            block=os.read(fd,65536)
            if not block:break
            raw+=block
            if len(raw)>maximum:raise ValueError('Read bound exceeded')
        after=os.fstat(fd);named=os.stat(str(path),follow_symlinks=False)
        fields=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if fields(before)!=fields(after) or fields(after)!=fields(named):
            raise ValueError('File changed during stable nofollow read')
        return raw
    finally:os.close(fd)


def absent():
    return {name:not os.path.lexists(ROOT/name) for name in F_NAMES}


def write(name,value):
    path=RESULTS/name;raw=canonical(value)+b'\n'
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(fd)
    finally:os.close(fd)
    return {'path':str(path),**pin(raw)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-results',action='store_true')
    args=parser.parse_args()
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError('Exact Python -I -S -B required')
    absence_before=absent()
    if not all(absence_before.values()):raise ValueError('F protected paths must be absent')
    tracked={}
    def held(path):
        raw=read(path);tracked[str(path.relative_to(ROOT))]=pin(raw);return raw
    plan_raw=held(PREPARATION/'plan.json');plan=json.loads(plan_raw)
    freeze_raw=held(PREPARATION/'complete-freeze.json');freeze=json.loads(freeze_raw)
    suite_raw=held(SUITE);suite=json.loads(suite_raw)
    original=suite['source_and_test_pins']
    if len(original)!=1190:raise ValueError('Original1190 pin inventory differs')
    actual_original={name:pin(read(ROOT/name)) for name in sorted(original)}
    mismatch_original=[name for name in original if actual_original[name]!=original[name]]
    if mismatch_original:raise ValueError('Original1190 source/test bytes differ: '+repr(mismatch_original))
    constructor_raw=held(ROOT/CONSTRUCTOR)
    if pin(constructor_raw)!=CONSTRUCTOR_PIN:raise ValueError('Original constructor raw pin differs')
    constructor_tree=ast.parse(constructor_raw)
    literals={n.targets[0].id:ast.literal_eval(n.value) for n in constructor_tree.body
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
        and n.targets[0].id in ('MISSING_FIELDS','STATUS','AUTHORITY_FIELDS','COUNTER_FIELDS')}
    if len(literals['MISSING_FIELDS'])!=11 or literals['STATUS']!='PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED':
        raise ValueError('Permanent scientific constructor blocked contract differs')
    qualifier_path=RESULTS/'qualify-successor-execution-preparation.py'
    qualifier=types.ModuleType('held_capacity_qualifier');qualifier.__file__=str(qualifier_path)
    exec(compile(held(qualifier_path),str(qualifier_path),'exec'),qualifier.__dict__)
    sys.path.extend((str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'tests'),sysconfig.get_path('purelib')))
    finder=qualifier.SourceFinder();sys.meta_path.insert(0,finder)
    def module(name):
        path=ROOT/'scripts'/('radio_native_v3_'+name+'.py')
        value=types.ModuleType('held_capacity_'+name);value.__file__=str(path)
        exec(compile(held(path),str(path),'exec'),value.__dict__)
        return value
    model_path=ROOT/'tests/test_radio_native_v3_terminal_capacity.py'
    model=types.ModuleType('held_capacity_model');model.__file__=str(model_path)
    model.__dict__['module']=module
    tree=ast.parse(held(model_path));tree.body=[n for n in tree.body
        if not (isinstance(n,ast.FunctionDef) and n.name=='module')]
    exec(compile(tree,str(model_path),'exec'),model.__dict__)
    # Replace the legacy model's path fixture with the actual fresh F plan.
    model.PRIOR_PLAN_PATH=PREPARATION/'plan.json';model.PRIOR_PLAN=plan
    model.PYTHON=plan['runtime_executables']['python']['path']
    model.NODE=plan['runtime_executables']['node']['path']
    selected=sorted(model.C.CODE_FILES)
    if len(selected)!=66 or set(selected)!=set(plan['code_files']):
        raise ValueError('Exact admitted66 code membership differs from fresh plan')
    for name in selected:
        if pin(held(ROOT/name))!=plan['code_files'][name]:
            raise ValueError('Selected source pin differs: '+name)
    repositories=freeze['code_sha256s'];inputs=freeze['input_sha256s']
    if (len(repositories),len(inputs),len(set(repositories)|set(inputs)),len(set(repositories)&set(inputs)))!=(964,40,1004,0):
        raise ValueError('Actual fresh freeze964/40/1004/0 selection differs')
    freeze_recheck={name:pin(read(ROOT/name)) for name in sorted(set(repositories)|set(inputs))}
    if any(freeze_recheck[name]['sha256']!=sha for name,sha in {**repositories,**inputs}.items()):
        raise ValueError('Fresh complete freeze repository/input source hash differs')
    terminal=model.terminal_model();case=model.case_model()
    if case['fresh_derived_source_pins']!=plan['derived_code']:
        raise ValueError('Fresh model derived code differs from actual plan')
    derived=sum(row['bytes'] for row in case['fresh_derived_source_pins'].values())
    if derived!=74035:raise ValueError('Actual fresh derived74035 total differs')
    margins={'case_bytes':case['case_cap_bytes']-case['complete_allocated_bytes'],
        'whole_eight_cases_bytes':case['whole_cap_bytes']-case['whole_eight_cases_bound_bytes'],
        'terminal_allocated_bytes':model.F.METADATA_RESERVATION_BYTES-terminal['terminal_allocated_bytes'],
        'per_envelope_bytes':{k:case['unchanged_per_envelope_cap_bytes']-v
            for k,v in case['per_envelope_bounds'].items()},
        'fixture_stdout_bytes':model.L.STDOUT_CAP-terminal['fixture_stdout_bytes'],
        'launcher_stdout_bytes':model.O.STDOUT_CAP-terminal['launcher_stdout_bytes']}
    if any(v<0 for k,v in margins.items() if k!='per_envelope_bytes') or any(v<0 for v in margins['per_envelope_bytes'].values()):
        raise ValueError('Current fixed source-shape estimate exceeds a resource cap')
    # Recheck every held/imported source and all original pins after sizing.
    tracked.update({str(Path(name).relative_to(ROOT)):value for name,value in finder.imports.items()
        if Path(name).is_relative_to(ROOT)})
    if any(pin(read(ROOT/name))!=value for name,value in tracked.items()):
        raise ValueError('Held source/input changed during sizing')
    if any(pin(read(ROOT/name))!=value for name,value in actual_original.items()):
        raise ValueError('Original1190 source/test changed during sizing')
    if any(pin(read(ROOT/name))!=value for name,value in freeze_recheck.items()):
        raise ValueError('Freeze repository/input changed during sizing')
    absence_after=absent()
    if absence_after!=absence_before:raise ValueError('F protected absence changed')
    self_pin=pin(read(Path(__file__)))
    common={'operator_helper_raw_pin':self_pin,'f_protected_state_absent_before':absence_before,
        'f_protected_state_absent_after':absence_after,**AUTHORITY}
    capacity={'schema':'radio-native-v3-prospective-f-capacity-source-shape-v1',
        'status':'CONDITIONAL_FIXED_SOURCE_SHAPE_FITS_ORIGINAL_CAPS',
        'namespace':plan['namespace'],'method':'held-source-existing-AST-expressions-with-bounded-synthetic-metadata',
        'old_model_regeneration_path':'tests/test_radio_native_v3_terminal_capacity.py:terminal_model/case_model; override legacy PRIOR_PLAN with raw-pinned fresh F plan',
        'source_pins_at_model_construction':tracked,'actual_frozen_repository_code_count':964,
        'actual_frozen_input_count':40,'actual_frozen_union_count':1004,'actual_frozen_overlap_count':0,
        'actual_frozen_source_input_raw_pins':freeze_recheck,'admitted_canonical_code_count':66,
        'nonadmitted_v3f_census_count':sum(name.startswith('scripts/radio_native_v3f_') for name in repositories),
        'fresh_derived_source_total_bytes':derived,'case':case,'terminal':terminal,'margins':margins,
        'capacity_proved_unconditionally':False,'current_control_executed':False,
        'postgraph_source_helpers_recalculated':True,'source_and_input_raw_pins_unchanged':True,**common}
    original_receipt={'schema':'radio-native-original1190-raw-pin-recheck-v1',
        'status':'ORIGINAL1190_RAW_PINS_UNCHANGED','suite_summary_raw_pin':pin(suite_raw),
        'original_source_test_file_count':len(original),'source_and_test_pins':actual_original,
        'mismatch_count':0,'constructor_path':CONSTRUCTOR,'constructor_raw_pin':CONSTRUCTOR_PIN,
        'constructor_constant_status':literals['STATUS'],'constructor_missing_required_fields':list(literals['MISSING_FIELDS']),
        'constructor_missing_required_field_count':11,
        'scientific_blocked_check_scope':'unchanged raw-pinned permanent constructor contract; no new certificate or telescope runtime admission is asserted',**common}
    if args.write_results:
        outputs=[write('prospective-capacity-model.json',capacity),
            write('original1190-raw-pin-recheck.json',original_receipt)]
        print(canonical({'outputs':outputs,'margins':margins,'admitted_code_count':66,
            'derived_bytes':derived,'original1190_mismatch_count':0,**AUTHORITY}).decode())
    else:
        print(canonical({'capacity':capacity,'original1190':original_receipt}).decode())


if __name__=='__main__':main()
