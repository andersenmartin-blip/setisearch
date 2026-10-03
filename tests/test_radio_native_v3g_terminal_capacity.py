"""Metadata-only prospective capacity model; never execute a control or recipe.

Source dictionary expressions are evaluated with synthetic bounded metadata.
The estimates are conditional on the explicitly stated fixed output widths;
they are neither actual retained inventories nor execution qualification.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import stat
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MIB = 1024**2
BLOCK = 4096
WIDE = (1 << 63)-1


def module(name):
    path = ROOT/'scripts'/('radio_native_v3g_'+name+'.py')
    spec = importlib.util.spec_from_file_location('capacity_'+name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = module('resource_finalization')
C = module('compact_eight_case_resource_fixture')
L = module('compact_control_launch')
O = module('engineering_observer')
S = module('process_tree_supervisor')
W = module('worker_admission')
V = module('compact_run_verifier')
PRIOR_PLAN_PATH = ROOT/'results_radio_native_v3_portable_custody_20261003a/preparation-attempt-3/plan.json'
PRIOR_PLAN = json.loads(PRIOR_PLAN_PATH.read_bytes())
PYTHON = PRIOR_PLAN['runtime_executables']['python']['path']
NODE = PRIOR_PLAN['runtime_executables']['node']['path']


def wire(value):
    return len(F.canonical(value))+1


def blocks(count):
    return ((count+BLOCK-1)//BLOCK)*BLOCK


def expression(owner, function, *, target=None, call=None, index=-1):
    """Select a real source expression without executing its enclosing API."""
    tree = ast.parse(Path(owner.__file__).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    selected = []
    for child in ast.walk(node):
        if target and isinstance(child, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == target for t in child.targets):
            selected.append(child.value)
        elif call and isinstance(child, ast.Call) and ast.unparse(child.func) == call:
            selected.append(child.args[0])
        elif not target and not call and isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
            selected.append(child.value)
        elif not target and not call and isinstance(child, ast.Return) and isinstance(child.value, ast.Tuple) and isinstance(child.value.elts[0],ast.Dict):
            selected.append(child.value.elts[0])
    return selected[index]


def evaluate(owner, function, values, **selection):
    expr = expression(owner, function, **selection)
    return eval(compile(ast.Expression(expr), owner.__file__, 'eval'), owner.__dict__, values)


def pin(count=2*MIB):
    return {'bytes':count, 'sha256':'f'*64}


def inventory(scope, *, saturate=False):
    rows = [{'path':'.','kind':'directory','bytes':BLOCK,'allocated_bytes':BLOCK,
        'device':1,'inode':1}]
    rows += [{'path':f'cases/case{i:02d}','kind':'directory','bytes':BLOCK,
        'allocated_bytes':BLOCK,'device':1,'inode':i+2} for i in range(8)]
    if saturate:
        rows += [{'path':f'cases/case{i:02d}/metadata-capacity-placeholder','kind':'file',
            'bytes':185*MIB,'allocated_bytes':185*MIB,'device':1,'inode':i+20} for i in range(8)]
        rows += [{'path':'shared-capacity-placeholder','kind':'file','bytes':32*MIB,
            'allocated_bytes':32*MIB,'device':1,'inode':99}]
    return {'scope':str(scope),'rows':rows,'entry_count':len(rows),
        'logical_bytes':sum(r['bytes'] for r in rows),
        'allocated_bytes':sum(r['allocated_bytes'] for r in rows)}


def external_inventory(scope):
    """31 real archival metadata rows plus seven prospective rows.

    Only the selected archival files/directories are read. Future journal and
    bootstrap rows use their exact source paths and wide synthetic stat values;
    no current claim, marker or journal is opened or created.
    """
    rows = []; components = []
    for index, (role, count) in enumerate(zip(F.EXTERNAL_STORAGE_ROLES,(15,16,3,4))):
        if role in F.ARCHIVE_STORAGE_ROLES:
            root = ROOT/('results_radio_native_v3_portable_custody_20261003a/'+
                ('archival-b-metadata' if index==0 else 'archival-c-metadata'))
            files={ROOT/name for name in C.HISTORICAL_INPUT_PATHS
                if (ROOT/name).is_relative_to(root)}
            directories={root}
            for path in files:
                directories.update(parent for parent in path.parents if parent.is_relative_to(root))
            group=[]
            for path in sorted(directories|files):
                info=path.lstat();kind='file' if path in files else 'directory'
                if path.resolve()!=path or not (stat.S_ISREG(info.st_mode) if kind=='file' else stat.S_ISDIR(info.st_mode)):
                    raise ValueError('Actual archival metadata path kind/alias differs')
                row={'component':role,'path':str(path),'kind':kind,
                    'bytes':info.st_size,'allocated_bytes':info.st_blocks*512,
                    'device':info.st_dev,'inode':info.st_ino,'mode':stat.S_IMODE(info.st_mode),
                    'nlink':info.st_nlink,'uid':info.st_uid,'gid':info.st_gid,
                    'mtime_ns':info.st_mtime_ns,'ctime_ns':info.st_ctime_ns}
                if kind=='file':row['raw_pin']=C.pin(path)
                after=path.lstat()
                if (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)!=(
                        after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                    raise ValueError('Archival metadata changed during sizing read')
                group.append(row)
            if len(group)!=count:raise ValueError('Exact selected archival metadata row count differs')
            root=str(root)
        else:
            root=(PRIOR_PLAN['invocation_ledger_root'] if role=='current_ledger'
                else str((ROOT/PRIOR_PLAN['current_public_claim_path']).parent))
            names=(['spent-'+'f'*64+'.json','dispatch-'+'f'*64+'.json'] if role=='current_ledger'
                else [Path(PRIOR_PLAN['current_public_claim_path']).name,
                    Path(L.CONFIG_PATH).name,Path(O.CAPSULE_PATH).name])
            group=[]
            for ordinal in range(count):
                kind='directory' if ordinal==0 else 'file'
                size=BLOCK if kind=='directory' else 65536
                row={'component':role,'path':root if ordinal==0 else root+'/'+names[ordinal-1],
                    'kind':kind,'bytes':size,'allocated_bytes':blocks(size),
                    'device':WIDE,'inode':100+index*32+ordinal,
                    'mode':0o700 if kind=='directory' else 0o400,'nlink':1,
                    'uid':WIDE,'gid':WIDE,'mtime_ns':WIDE,'ctime_ns':WIDE}
                if kind=='file' and role!='current_ledger':row['raw_pin']=pin(size)
                group.append(row)
        rows.extend(group)
        components.append({'role':role,'observation_role':F.EXTERNAL_STORAGE_OBSERVATION_ROLES[role],
            'root':root,'observation_sha256':'f'*64,'entry_count':len(group),
            'logical_bytes':sum(r['bytes'] for r in group),
            'allocated_bytes':sum(r['allocated_bytes'] for r in group)})
    return {'schema':F.EXTERNAL_STORAGE_SCHEMA,'components':components,'rows':rows,
        'logical_bytes':sum(r['bytes'] for r in rows),
        'allocated_bytes':sum(r['allocated_bytes'] for r in rows),'entry_count':len(rows),
        'charged_once':True,'read_only':True,'execution_authorized':False,
        'whole_control_qualified':False,'lifetime_accounting_proved':False,
        'current_control_scope':str(scope),'missing_original_storage_accounted':False,
        'original_identity_continuity_proved':False,'selected_archival_metadata_only':True}


def source_observation(scope, limit):
    sample = {'at_epoch_ms':WIDE,'rss_bytes':512*MIB,'kernel_vm_hwm_bytes':512*MIB}
    samples = [sample]*limit
    argv = [PYTHON,'-I','-S','-B',str(scope/'frozen-code'/F.SELF),
        '--admitted-whole-control-driver','--admission-bundle',str(scope/'control-admission.json'),
        '--bundle-sha256','f'*64,'--scope',str(scope),
        '--admission-start-monotonic-ns',str(WIDE)]
    usage = types.SimpleNamespace(ru_maxrss=512*MIB//1024)
    resource = types.SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:usage)
    os = types.SimpleNamespace(readlink=lambda _:'2147483647')
    values = dict(label='measurement-driver',argv=argv,executable_pin=pin(64*MIB),
        monotonic_start_ns=WIDE,monotonic_end_ns=WIDE,resource=resource,os=os,
        proc_pid=2147483647,start=WIDE,end=WIDE,wait4_peak=512*MIB,measured=512*MIB,
        sample_count=WIDE,status=0,reason=None,bound_identity={'procfs_pid':2147483647,
            'namespace_pid':2147483647,'procfs_start_ticks':str(WIDE),
            'namespace_pid_chain':[2147483647]*64},
        reported_identity_verified=True,samples=samples,sample_retention_limit=limit,
        observed_output_bytes={'stdout':65536,'stderr':65536},pipe_output=True)
    return evaluate(C,'observe_process',values,target='result')


def terminal_model():
    scope = ROOT/O.SCOPE_NAME
    external = external_inventory(scope)
    storage = F.allocate_storage(inventory(scope,saturate=True),external_inventory=external)
    cases = [{'ordinal':i,'source_case_id':'f'*64,'exclusive_seconds':599.9999999999999,
        'calls':64,'request_bytes':48*MIB,'response_bytes':64*MIB} for i in range(8)]
    timing = F.allocate_elapsed(cases,4800)
    totals = {'calls':512,'request_bytes':384*MIB,'response_bytes':512*MIB}
    argv = source_observation(scope,64)['observed_argv']
    pending = evaluate(F,'capture_pending_measurements',dict(scope=scope,start=WIDE,completed=WIDE,
        worker_path=scope/'worker-result.json',worker_pin=pin(),runner_path=scope/F.RUNNER_OBSERVATION_NAME,
        runner_pin=pin(),subreaper_path=scope/'whole-control-supervisor/subreaper-receipt.json',
        subreaper_pin=pin(),expected_runner_argv=argv,inventory=inventory(scope),
        storage=storage,timing=timing,totals=totals,peak=512*MIB,
        complete_material_peaks=True,complete_descendant_chain=True))
    # The real base-inventory helper hashes metadata only, not any payload.
    disposition = evaluate(F,'join_final_measurements',{},target='result')
    disposition.update(evaluate(F,'join_final_measurements',dict(scope=scope,pending_pin=pin(),
        driver_pin=pin(),complete_descendant_chain=True,complete_material_peaks=True,
        peak=512*MIB,storage=storage,timing=timing,totals=totals,external=external,
        join_completed=WIDE,synthetic=False,complete_join=True,pending_reasons=[]),call='result.update',index=0))
    observed = source_observation(scope,C.TERMINAL_OBSERVATION_SAMPLE_LIMIT)
    resource = types.SimpleNamespace(RUSAGE_SELF=0,
        getrusage=lambda _:types.SimpleNamespace(ru_maxrss=512*MIB//1024))
    report_input = evaluate(C,'run_control',dict(finalizer=F.__dict__,scope=scope,
        pin=lambda _:pin(),disposition=disposition,observed=observed,resource=resource),target='report_input')
    gate = evaluate(F,'check_final_report_material_scope',dict(scope=scope,
        material_counts={'code':len(C.CODE_FILES),'derived':6},
        plan={'runtime_executables':{'python':{'path':PYTHON}}}))
    report = evaluate(F,'_persist_checked_final_report',dict(report_input=report_input,
        mode='ACTIVATION_BOUND_MATERIAL',observed_input_pin=pin(),gate=gate),target='report')
    joined = evaluate(F,'join_final_report_lifetime',dict(report=report,report_pin=pin(),
        identity_pin=pin(),observation_pin=pin(),writer_start=WIDE,writer_end=WIDE,
        writer_peak=512*MIB,synthetic=False,tiny=False,storage=storage))
    reference = F.final_report_join_reference(joined)
    result = evaluate(L,'_launch_control_once',dict(scope=scope,read_pinned=lambda _:(pin(),None),
        worker_pin=pin(),observation={'exit_code':0},summary=joined,anchor=WIDE,
        elapsed=timing,peak=512*MIB,storage=storage),target='result')
    # Exact canonical SHA is necessary for the real completion helper.
    raw = F.canonical(result)+b'\n'
    completion = F.launcher_completion_reference(result,{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    # Bound the external replay's compact scalars/pins without running replay.
    replay = evaluate(O,'replay_launcher',dict(retained_pin=pin(),worker_pin=pin(),
        report_pin=pin(),writer_pin=pin()))
    outer = evaluate(O,'run_observer',dict(scope=scope,capsule_pin=pin(),config_pin=pin(),
        stdout_pin=pin(),stderr_pin=pin(),observation_pin=pin(),replay=replay,
        observation={'maximum_observed_individual_rss_bytes':512*MIB},resource=resource,
        anchor=WIDE,elapsed=timing,storage=storage),target='result')
    lengths = {
        F.PENDING_NAME:wire(pending),F.DRIVER_IDENTITY_NAME:1024,
        F.DRIVER_OBSERVATION_NAME:wire(observed),F.FINAL_INPUT_NAME:wire(report_input),
        F.FINAL_WRITER_IDENTITY_NAME:1024,F.FINAL_WRITER_OBSERVATION_NAME:wire(observed),
        F.FINAL_WRITER_STDOUT_NAME:0,F.FINAL_WRITER_STDERR_NAME:C.LOG_LIMIT,
        F.FINAL_NAME:wire(report),L.STDOUT_NAME:wire(reference),L.STDERR_NAME:L.STDERR_CAP,
        L.OBSERVATION_NAME:L.OBSERVATION_CAP,L.DISPOSITION_NAME:wire(result),
        L.PREFLIGHT_NAME:L.PREFLIGHT_CAP,L.FAILURE_NAME:8192,
        O.STDOUT_NAME:wire(completion),O.STDERR_NAME:O.STDERR_CAP,
        O.OBSERVATION_NAME:O.OBSERVATION_CAP,O.DISPOSITION_NAME:wire(outer),O.FAILURE_NAME:O.FAILURE_CAP}
    return {'scope':str(scope),'terminal_file_lengths':lengths,
        'terminal_logical_bytes':sum(lengths.values()),
        'terminal_allocated_bytes':sum(blocks(n) for n in lengths.values()),
        'terminal_directory_growth_reserved_separately':F.DIRECTORY_RESERVATION_BYTES,
        'fixture_stdout_bytes':wire(reference),'launcher_stdout_bytes':wire(completion),
        'joined_full_summary_bytes':wire(joined),'retained_external_inventory_bytes':wire(external),
        'retained_external_reference_bytes':wire(F.external_storage_reference(external)),
        'external_components_sizing':external['components'],
        'observed_archival_file_rows':sum(row['kind']=='file' and row['component'] in F.ARCHIVE_STORAGE_ROLES for row in external['rows']),
        'observed_archival_directory_rows':sum(row['kind']=='directory' and row['component'] in F.ARCHIVE_STORAGE_ROLES for row in external['rows']),
        'allocation_bytes':wire(storage),'case_observation_2048_bytes':wire(source_observation(scope,2048)),
        'terminal_observation_64_bytes':wire(observed)}


def receipt_bound(scope, role, command_width=0):
    """Use every original dynamic-field allowance, including 64 reap rows.

    Evaluate the actual structural receipt source expression so fixed booleans
    and status strings retain their exact widths. Phase pins use the complete
    allowed key inventory. This is a serialization estimate, not an admission.
    """
    root=scope/'cases/case00'
    label='command-tail' if command_width else 'command-37'
    path=root/('worker-admission.json' if role=='prepare' else
        (label if role=='command' else role)+'-admission.json')
    layout_values=dict(root=str(root),role=role,ordinal=0,label=label if role=='command' else None)
    layout_values['receipt']=evaluate(W,'worker_role_layout',layout_values,target='receipt')
    layout_values['bundle_name']=evaluate(W,'worker_role_layout',layout_values,target='bundle_name')
    layout=evaluate(W,'worker_role_layout',layout_values)
    checked_layout={key:layout[key] for key in S.ADMITTED_LAYOUT_KEYS}
    phase_fields={}
    if role!='prepare':
        phase_fields={key:False for key in S.STRUCTURAL_PHASE_KEYS}
        phase_fields['phase_input_pins']={key:pin() for key in S.PHASE_PIN_KEYS}
    if role=='command':
        phase_fields['command_binding']={'kind':'pinned_caller_tail','terminal_ordinal':38,
            'payload_bytes':47616,'complete_client_binding_independently_recovered':True}
    bundle={key:'f'*64 for key in ('plan_sha256','complete_freeze_sha256','public_preread_sha256')}
    bundle['public_preread']={'preparation_commit':'f'*40}
    structural=evaluate(W,'_validate_worker_admission',dict(role=role,ordinal=0,
        plan=PRIOR_PLAN,bundle=bundle,bundle_path=str(path),expected_bundle_sha256='f'*64,
        custody_sha256='f'*64,running_caller=False,layout=layout,loaded_self=pin(),phase=phase_fields))
    argv=[PYTHON,'-I','-S','-B',str(root/'frozen-code'/C.SELF),
        '--exec-command-child',str(root),label,'x'*command_width,str(path),'f'*64]
    attestation={'schema':S.SCHEMA+'-admitted-worker-check','role':role,'ordinal':0,
        'argv':argv,'bundle_path':str(path),'bundle_sha256':'f'*64,**checked_layout,
        'supervisor_python_path':PYTHON,'structural_admission':structural,
        'materialized_fixture_execution_status':C.EXECUTION_STATUS,
        'independent_immutable_publication_join_complete':False,
        'activation_evidence_reference':{'schema':S.SCHEMA+'-activation-evidence-reference-v1',
            'execution_scope':str(scope),'repository_root':str(ROOT),
            'canonical_input_pins':{key:pin(16*MIB) for key in
                ('activation_receipt','plan','freeze','preread','execution_scope','invocation_spending','repository_root')},
            'full_activation_evidence_persisted':False,'reference_is_execution_authority':False},**S.AUTHORITY}
    controls=S.admitted_role_controls(role,119.99999999999999 if role=='command' else 599.9999999999999)
    if role=='prepare':
        controls={'schema':S.SCHEMA+'-admitted-prepare-controls','seconds':599.9999999999999,
            'output_bytes':S.MAX_OUTPUT_BYTES,'reaped_children':S.MAX_REAPED_CHILDREN,
            'case_storage_bytes':S.CASE_STORAGE_BYTES,'rss_bytes':S.MAX_RSS_BYTES,'worker_role':role}
        S.validate_admitted_prepare_controls(controls)
    fixed=S._receipt_fixed_fields(controls,pin(),pin(),
        {'kind':'admission-bound-prepare-worker' if role=='prepare' else 'admission-bound-role-worker',
            'bundle_sha256':'f'*64,'role':role,'ordinal':0},attestation,root,
        S.CASE_STORAGE_BYTES,True)
    return wire(fixed)+sum(len(S.canonical(key))+2+maximum
        for key,maximum in S.RUNTIME_FIELD_JSON_LIMITS.items())


def full_tail_command_bytes(scope):
    """Exact source quote rule and option order, with maximal encoded payload.

    Only a bounded synthetic metadata shell string is made; no payload or
    generated case data exists and the command is never executed.
    """
    root=scope/'cases/case00'
    args=[PYTHON,'-I','-S','-B','-c',W.TAIL_BOOTSTRAP,
        str(root/'frozen-code/scripts/radio_native_v2_caller_tail.py'),'f'*64,
        '--destination',str(root/'caller-tail.json'),'--payload-base64','X'*(62*1024),
        '--expected-bytes','47616','--expected-sha256','f'*64,
        '--client-sha256','f'*64,'--terminal-ordinal','38']
    command=' '.join("'"+str(item).replace("'","'\\''")+"'" for item in args)
    return {'utf8_bytes':len(command.encode()),
        'json_content_bytes':len(S.canonical(command))-2}


def case_directory_paths():
    paths={'.','frozen-code','derived','public-evidence','command-observations',
        'store','store/items','store/items/request-000001'}
    for name in C.CODE_FILES:
        for part in Path(name).parents:
            if str(part)!='.': paths.add('frozen-code/'+str(part))
    for label in ['preparation','caller','lossless-project','lossless-verify-retained']+[
            'command-'+str(i) for i in range(38)]+['command-tail']:
        paths.add(label+'-supervisor')
    return sorted(paths)


def case_model():
    """Conditional fixed-shape estimate with unchanged runtime quota gates."""
    terminal=terminal_model(); scope=Path(terminal['scope'])
    reader=receipt_bound(scope,'command',1024)
    tail_widths=full_tail_command_bytes(scope)
    tail_width=tail_widths['json_content_bytes']
    tail=receipt_bound(scope,'command',tail_width)
    prepare=receipt_bound(scope,'prepare')
    phase=max(receipt_bound(scope,role) for role in
        ('caller','lossless-project','lossless-verify-retained'))
    # 43 independent supervisors, two envelopes each; public prep receipt once.
    receipts=2*(38*blocks(reader)+blocks(tail)+3*blocks(phase)+blocks(prepare))+blocks(prepare)
    code=sum(blocks((ROOT/path).stat().st_size) for path in C.CODE_FILES)
    # Include this test prospectively if the parent has not added it yet.
    own='tests/test_radio_native_v3g_terminal_capacity.py'
    if own not in C.CODE_FILES: code+=blocks((ROOT/own).stat().st_size)
    fresh_derived=C.templates((ROOT/C.CODE_FILES[0]).read_text(),ROOT)
    derived=sum(blocks(len(raw)) for raw in fresh_derived.values())
    # 45 = 43 originals + independently retained caller/preparation copies.
    observations=45*blocks(terminal['case_observation_2048_bytes']+2048)+blocks(tail_width)
    # 41 small references plus one original fixed tail command (<=62 KiB).
    references=41*blocks(W.MAX_SMALL_PHASE_REFERENCE_BYTES)+blocks(W.MAX_TAIL_PHASE_REFERENCE_BYTES)
    shared_dirs=len({str(parent) for name in C.CODE_FILES for parent in Path(name).parents
        if str(parent)!='.'})+7
    shared_terms={'frozen_code':code,'derived_code':derived,
        'scope_contexts_and_two_full_whole_role_bundles':3*W.MAX_FULL_BUNDLE_BYTES,
        'external_archive_journal_claim':F.MAX_EXTERNAL_RETAINED_STORAGE_BYTES,
        'remaining_shared_root_files':C.SHARED_METADATA_GROUP_BYTES,
        'whole_control_and_verifier_supervisor_envelopes':4*S.RECEIPT_RESERVATION_BYTES,
        'compact_verifier_plan_eight_cases_receipt_failure':11*V.SMALL_FILE_BYTES,
        'measurement_driver_stderr_outside_terminal_names':C.LOG_LIMIT,
        'fixed_shared_directories':shared_dirs*BLOCK,
        'terminal_files':F.METADATA_RESERVATION_BYTES,
        'terminal_directory_growth':F.DIRECTORY_RESERVATION_BYTES,
        'retained_external_snapshot':blocks(F.MAX_RETAINED_STORAGE_SNAPSHOT_BYTES)}
    shared=sum(shared_terms.values())
    categories={'deterministic_payload':26*MIB,'source_wire':W.MAX_SOURCE_WIRE_BYTES,
        'raw_full_transcript':W.MAX_FULL_TRANSCRIPT_BYTES,'full_preparation_context':W.MAX_FULL_BUNDLE_BYTES,
        'frozen_code':code,'derived_code':derived,'phase_references':references,
        'original_and_public_process_observations':observations,
        'supervisor_envelopes_and_public_preparation_copy':receipts,
        'other_fixed_success_metadata_projection_logs_and_padding':C.CASE_OTHER_METADATA_BUDGET_BYTES,
        'fixed_case_directory_allocation':len(case_directory_paths())*BLOCK,
        'case_directory_growth_allowance':65536,'shared_current_and_external_allocation':(shared+7)//8}
    return {'allocated_categories':categories,'complete_allocated_bytes':sum(categories.values()),
        'case_cap_bytes':F.LIMITS['case_storage_bytes'],
        'whole_cap_bytes':F.LIMITS['run_storage_bytes'],
        'whole_eight_cases_bound_bytes':sum(categories.values())*8,
        'per_envelope_bounds':{'reader':reader,'tail':tail,'preparation':prepare,'phase':phase},
        'unchanged_per_envelope_cap_bytes':S.RECEIPT_RESERVATION_BYTES,
        'generic_receipt_cap_sum_bytes':87*S.RECEIPT_RESERVATION_BYTES,
        'maximum_full_tail_command_bytes':tail_widths['utf8_bytes'],
        'maximum_tail_command_json_content_bytes':tail_width,
        'maximum_tail_base64_bytes':62*1024,
        'fixed_case_directory_paths':case_directory_paths(),
        'whole_shared_allocated_categories':shared_terms,
        'fresh_derived_source_pins':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            for name,raw in fresh_derived.items()},
        'conditional_assumptions':[
            'Fixed source wire <=36 MiB and raw full transcript <=108 MiB; prospective allowances, not measured output sizes.',
            'One full case preparation context <=2 MiB and complete shared context bundles <=2 MiB each after fresh recapture.',
            '38 exact reader commands <=1024 UTF-8 bytes each; maximal tail command includes all fixed quoted argv overhead beyond its 62 KiB base64 component.',
            'Other fixed successful case metadata, lossless projection, retained logs and block padding together <=1.75 MiB.',
            'Current external archive/journal/claim allocation <=2 MiB; fixed metadata serialization uses 38 synthetic rows.',
            'Ordinary non-sparse file allocation rounds to 4096 bytes; separate directory allowance charged.',
            'These source-shaped estimates do not replace live authenticated storage_inventory/allocate_storage checks.']}


class TerminalCapacityTests(unittest.TestCase):
    def test_terminal_sample_limit_keeps_case_limit_and_full_peak_tracking(self):
        self.assertEqual(C.OBSERVATION_SAMPLE_LIMIT,2048)
        self.assertEqual(C.TERMINAL_OBSERVATION_SAMPLE_LIMIT,64)
        source = ast.unparse(ast.parse(Path(C.__file__).read_text()))
        self.assertIn('peak = max(peak, sample[',source)
        self.assertIn('wait4_peak = usage.ru_maxrss * 1024',source)
        function = next(n for n in ast.parse(Path(C.__file__).read_text()).body
            if isinstance(n,ast.FunctionDef) and n.name=='run_control')
        calls = [n for n in ast.walk(function) if isinstance(n,ast.Call)
            and isinstance(n.func,ast.Name) and n.func.id=='observe_process']
        self.assertEqual(len(calls),2)
        for call in calls:
            self.assertEqual(ast.unparse(next(k.value for k in call.keywords
                if k.arg=='sample_retention_limit')),'TERMINAL_OBSERVATION_SAMPLE_LIMIT')

    def test_all_terminal_names_and_allocated_blocks_fit_fixed_shape(self):
        model = terminal_model()
        self.assertEqual(set(model['terminal_file_lengths']),set(F.FINAL_METADATA_NAMES))
        self.assertEqual(len(F.FINAL_METADATA_NAMES),20)
        self.assertLessEqual(model['terminal_allocated_bytes'],F.METADATA_RESERVATION_BYTES)
        self.assertEqual(F.METADATA_RESERVATION_BYTES,256*1024)
        self.assertEqual(F.DIRECTORY_RESERVATION_BYTES,65536)

    def test_compact_terminal_wires_fit_both_original_pipe_caps(self):
        model = terminal_model()
        self.assertLess(model['fixture_stdout_bytes'],L.STDOUT_CAP)
        self.assertLess(model['launcher_stdout_bytes'],O.STDOUT_CAP)
        self.assertEqual((L.STDOUT_CAP,O.STDOUT_CAP),(65536,65536))

    def test_external_inventory_is_retained_once_and_exact_reference_mutation_closed(self):
        scope=ROOT/'capacity-model-control'; external=external_inventory(scope)
        storage=F.allocate_storage(inventory(scope),external_inventory=external)
        self.assertNotIn('rows',storage['external_ledger_storage'])
        self.assertLess(wire(storage['external_ledger_storage']),1024)
        self.assertTrue(F.verify_external_storage_reference(storage['external_ledger_storage'],external))
        external['rows'][1]['mtime_ns']-=1
        with self.assertRaises(ValueError):
            F.verify_external_storage_reference(storage['external_ledger_storage'],external)

    def test_external_capacity_checks_wire_and_both_storage_totals(self):
        scope=ROOT/'capacity-model-control'; external=external_inventory(scope)
        self.assertEqual(F.MAX_EXTERNAL_RETAINED_STORAGE_BYTES,2*MIB)
        self.assertEqual(F.MAX_RETAINED_STORAGE_SNAPSHOT_BYTES,32768)
        self.assertEqual(F.prepare_retained_storage_snapshot(external,scope=scope),external)
        for field in ('bytes','allocated_bytes'):
            excessive=json.loads(F.canonical(external))
            row=next(r for r in excessive['rows'] if r['component']==F.EXTERNAL_STORAGE_ROLES[0] and r['kind']=='file')
            component=excessive['components'][0]
            row[field]+=2*MIB
            total='logical_bytes' if field=='bytes' else 'allocated_bytes'
            component[total]+=2*MIB; excessive[total]+=2*MIB
            if field=='bytes': row['raw_pin']['bytes']=row[field]
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'2MiB retained external'):
                F.prepare_retained_storage_snapshot(excessive,scope=scope)
        actual=wire(external)
        with mock.patch.object(F,'MAX_RETAINED_STORAGE_SNAPSHOT_BYTES',actual):
            self.assertEqual(F.prepare_retained_storage_snapshot(external,scope=scope),external)
        with mock.patch.object(F,'MAX_RETAINED_STORAGE_SNAPSHOT_BYTES',actual-1):
            with self.assertRaisesRegex(ValueError,'32KiB retained external'):
                F.prepare_retained_storage_snapshot(external,scope=scope)

    def test_phase_capacity_descriptors_and_actual_reader_limits(self):
        self.assertEqual((W.MAX_FULL_BUNDLE_BYTES,W.MAX_SOURCE_WIRE_BYTES,W.MAX_FULL_TRANSCRIPT_BYTES),
            (2*MIB,36*MIB,108*MIB))
        for label,filename,maximum in (('preparation_bundle','worker-admission.json',2*MIB),
                ('source_wire','store/items/request-000001/part',36*MIB),
                ('caller_transcript','caller-result.json',108*MIB),
                ('verifier source','caller-result.json',108*MIB)):
            path=str(ROOT/'capacity-model-control'/filename)
            descriptor={'path':path,**pin(maximum)}
            W._file_descriptor(descriptor,path,label)
            descriptor['bytes']=maximum+1
            with self.subTest(label=label),self.assertRaisesRegex(ValueError,'Fixed engineering capacity'):
                W._file_descriptor(descriptor,path,label)
            descriptor['bytes']=maximum
            with mock.patch.object(W,'read_pinned_file',return_value=(pin(maximum),None)) as reader:
                W._phase_file(descriptor)
                self.assertEqual(reader.call_args.kwargs['maximum'],maximum)

    def test_stable_core_ignores_only_dynamic_current_allocation(self):
        joined={'immutable':{'sha256':'f'*64},
            'storage_after_report_writer_lifetime_with_final_reservation':{'changed':1}}
        original=F.final_report_join_core(joined)
        joined['storage_after_report_writer_lifetime_with_final_reservation']={'changed':2}
        self.assertEqual(F.final_report_join_core(joined),original)
        joined['immutable']['sha256']='e'*64
        self.assertNotEqual(F.final_report_join_core(joined),original)

    def test_individual_caps_cannot_be_misreported_as_aggregate_proof(self):
        outer_caps=(L.STDOUT_CAP+L.STDERR_CAP+L.OBSERVATION_CAP+L.PREFLIGHT_CAP+
            L.DISPOSITION_CAP+8192+O.STDOUT_CAP+O.STDERR_CAP+O.OBSERVATION_CAP+
            O.DISPOSITION_CAP+O.FAILURE_CAP)
        self.assertGreater(outer_caps,F.METADATA_RESERVATION_BYTES)

    def test_fixed_case_bound_includes_full_2048_samples_and_all_receipts(self):
        model=case_model()
        self.assertLessEqual(max(model['per_envelope_bounds'].values()),S.RECEIPT_RESERVATION_BYTES)
        self.assertLessEqual(model['complete_allocated_bytes'],F.LIMITS['case_storage_bytes'])
        self.assertLessEqual(model['whole_eight_cases_bound_bytes'],F.LIMITS['run_storage_bytes'])
        self.assertGreater(model['allocated_categories']['original_and_public_process_observations'],8*MIB)
        self.assertGreater(model['allocated_categories']['supervisor_envelopes_and_public_preparation_copy'],4*MIB)


if __name__ == '__main__':
    unittest.main()
