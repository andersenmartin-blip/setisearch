"""Read-only closure audit and refusal checks; never generate a large source."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
for folder in (REPO/'src', REPO/'scripts'):
    if str(folder) not in sys.path: sys.path.insert(0,str(folder))

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_runner_freeze as freezer
import radio_native_v2_compact_preparation_audit as auditor
import radio_native_v2_worker_admission as admission
import radio_native_v2_resource_finalization as finalizer

OUT = Path(__file__).parent
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261001e.plan.json'
FREEZE = 'config/radio_native_v2_whole_worker_integration_20261001a.runtime.json'
INPUTS = [PLAN, *(path for path in fixture.CODE_FILES if path.startswith('tests/')),
    'tests/test_radio_native_v2_compact_preparation_audit.py',
    str(Path(__file__).relative_to(REPO))]


def exact_file(relative, value):
    path=REPO/relative; raw=fixture.canonical(value)
    if path.exists():
        if path.read_bytes()!=raw: raise RuntimeError('Existing output differs; preserve historical evidence: '+relative)
    else: fixture.write(path,raw)
    return raw


def retained_snapshot(root):
    result={}
    for path in itertools.chain((root,),root.rglob('*')):
        if len(result)>=32768: raise ValueError('Bounded refusal inventory required')
        info=path.lstat()
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ValueError('Only regular files/directories allowed in refusal fixture')
        row={'device':info.st_dev,'inode':info.st_ino,'mode':info.st_mode,
            'nlink':info.st_nlink,'bytes':info.st_size,'allocated_bytes':info.st_blocks*512,
            'mtime_ns':info.st_mtime_ns,'ctime_ns':info.st_ctime_ns}
        if stat.S_ISREG(info.st_mode): row['pin']=fixture.pin(path)
        result[str(path.relative_to(root))]=row
    return result


def refusal(argv, case_root, label):
    before=retained_snapshot(case_root)
    process=subprocess.run(argv,capture_output=True,timeout=20,env=fixture.CHILD_ENVIRONMENT)
    after=retained_snapshot(case_root)
    if process.returncode==0 or b'BLOCKED_PREPARATION_REVIEW' not in process.stderr or before!=after:
        raise RuntimeError('Worker/refusal did not close before side effects: '+label)
    fixture.write(OUT/(label+'-stderr.log'),process.stderr)
    return {'label':label,'returncode':process.returncode,'stdout_bytes':len(process.stdout),
        'stderr':fixture.pin(OUT/(label+'-stderr.log')),
        'no_scope_entries_created_or_removed':before==after,
        'retained_material_bytes_identity_and_allocation_unchanged':before==after,
        'large_source_created':(case_root/'deterministic-source.bin').exists(),
        'preparation_identity_created':(case_root/'preparation-identity.json').exists(),
        'supervisor_scope_created':(case_root/'preparation-supervisor').exists()}


if __name__=='__main__':
    started=time.monotonic()
    plan=fixture.build_plan(REPO); exact_file(PLAN,plan)
    freeze=freezer.capture(REPO,INPUTS); exact_file(FREEZE,freeze)
    with tempfile.TemporaryDirectory(prefix='seti-source-admission-readonly-') as directory:
        scope=Path(directory)/'whole'; case_root=scope/'cases'/'case03'; case_root.mkdir(parents=True)
        fixture.copy_code(REPO,case_root/'frozen-code',plan['code_files'])
        derived=case_root/'derived'; derived.mkdir()
        for name,raw in fixture.templates((REPO/fixture.CODE_FILES[0]).read_text()).items():
            fixture.write(derived/name,raw)
        result=auditor.audit(plan,freeze,repo=REPO,
            materialized_code_root=case_root/'frozen-code',derived_root=derived)
        exact_file(str((OUT/'independent-preparation-audit.json').relative_to(REPO)),result)
        # Deliberately synthetic claims exercise the local structural checker.
        # They are not published admission evidence. The placeholder commit
        # has no verified immutable publication; every execution gate stays shut.
        synthetic_preread={'schema':fixture.PREREAD_SCHEMA,'namespace':fixture.NAMESPACE,
            'plan_sha256':hashlib.sha256(fixture.canonical(plan)).hexdigest(),
            'complete_freeze_sha256':hashlib.sha256(fixture.canonical(freeze)).hexdigest(),
            'public_immutable_readback_verified':True,'engineering_control_admitted':True,
            'code_files_verified':plan['code_files'],'preparation_commit':'0'*40,**fixture.AUTHORITY}
        bundle=admission.build_admission_bundle(plan,freeze,synthetic_preread,execution_scope=scope,ordinal=3)
        bundle_path=case_root/'worker-admission.json'; fixture.write(bundle_path,admission.bundle_bytes(bundle))
        digest=fixture.pin(bundle_path)['sha256']
        argv=admission.expected_worker_argv(bundle,bundle_path,ordinal=3,expected_bundle_sha256=digest)
        local=admission.validate_worker_admission(bundle_path,ordinal=3,argv=argv,
            environment=fixture.CHILD_ENVIRONMENT,expected_bundle_sha256=digest)
        supervisor=case_root/'frozen-code'/'scripts/radio_native_v2_process_tree_supervisor.py'
        base=[plan['runtime_executables']['python']['path'],'-I','-S','-B',str(supervisor)]
        common=['--admission-bundle',str(bundle_path),'--bundle-sha256',digest,'--ordinal','3']
        checked=subprocess.run([*base,'--admission-check-only',*common],
            capture_output=True,timeout=20,env=fixture.CHILD_ENVIRONMENT)
        if checked.returncode!=0 or checked.stderr:
            raise RuntimeError('Independent read-only supervisor admission check failed: '+checked.stderr.decode())
        supervisor_check=json.loads(checked.stdout)
        if supervisor_check['structural_admission']['publication_claim_independently_verified'] is not False:
            raise RuntimeError('A supplied claim must not become verified public admission')
        rows=[refusal(argv,case_root,'derived-worker-blocked'),
            refusal([*base,'--admitted-prepare-worker',*common,'--scope',str(case_root/'preparation-supervisor')],
                case_root,'supervisor-dispatch-blocked')]
        # Derived Node entrypoints repeat the closed global gate before options,
        # identity or scientific source writes; these are refusal controls only.
        node=plan['runtime_executables']['node']['path']
        rows.extend([
            refusal([node,str(derived/'fresh-caller.js'),'--caller',str(case_root),str(bundle_path),digest],case_root,'node-caller-blocked'),
            refusal([node,str(derived/'lossless-helper.js'),'--resource-project',str(case_root/'missing-project-options.json'),str(bundle_path),digest],case_root,'node-project-blocked'),
            refusal([node,str(derived/'lossless-helper.js'),'--resource-verify-retained',str(case_root/'missing-verify-options.json'),str(bundle_path),digest],case_root,'node-retained-verifier-blocked')])
        fixture.write(OUT/'local-structural-check.json' ,{'synthetic_unverified_public_claim_fixture':True,
            'retained_material_scope_was_temporary':True,'worker_check':local,
            'independent_supervisor_check':supervisor_check,**fixture.AUTHORITY})
    # A separate fresh whole scope checks the V2 control metadata and the fixed
    # measurement driver without launching its protected control worker.
    with tempfile.TemporaryDirectory(prefix='seti-whole-control-readonly-') as directory:
        scope=Path(directory)/'whole'; scope.mkdir()
        fixture.copy_code(REPO,scope/'frozen-code',plan['code_files'])
        (scope/'derived').mkdir()
        for name,raw in fixture.templates((REPO/fixture.CODE_FILES[0]).read_text()).items():
            fixture.write(scope/'derived'/name,raw)
        for name,value in [('plan.json',plan),('complete-freeze.json',freeze),('public-preread.json',synthetic_preread)]:
            fixture.write(scope/name,value)
        inputs={key:fixture.phase_file(scope/name) for key,name in [('plan_json','plan.json'),('freeze_json','complete-freeze.json'),('preread_json','public-preread.json')]}
        bundle=admission.build_role_admission_bundle(plan,freeze,synthetic_preread,role='control',execution_scope=scope,phase_inputs=inputs)
        bundle_path=scope/'control-admission.json'; fixture.write(bundle_path,admission.bundle_bytes(bundle))
        digest=fixture.pin(bundle_path)['sha256']
        argv=admission.expected_worker_argv(bundle,bundle_path,role='control',ordinal=None,expected_bundle_sha256=digest)
        whole_local=admission.validate_worker_admission(bundle_path,role='control',ordinal=None,argv=argv,environment=fixture.CHILD_ENVIRONMENT,expected_bundle_sha256=digest)
        driver=scope/'frozen-code'/'scripts/radio_native_v2_resource_finalization.py'
        driver_argv=[plan['runtime_executables']['python']['path'],'-I','-S','-B',str(driver),'--admitted-whole-control-driver','--admission-bundle',str(bundle_path),'--bundle-sha256',digest,'--scope',str(scope),'--admission-start-monotonic-ns',str(time.monotonic_ns())]
        rows.append(refusal(driver_argv,scope,'outer-measurement-driver-blocked'))
        fixture.write(OUT/'whole-control-structural-check.json',{'synthetic_unverified_public_claim_fixture':True,'retained_material_scope_was_temporary':True,'worker_check':whole_local,**fixture.AUTHORITY})
    tiny=[]
    for name in ('orphan','rss-handshake','stdout-passthrough'):
        probe=OUT/('independent-tiny-'+name); probe.mkdir()
        observed,stdout,_=fixture.observe_process([plan['runtime_executables']['python']['path'],'-I','-S','-B',str(REPO/'scripts/radio_native_v2_process_tree_supervisor.py'),'--probe',name,'--scope',str(probe/'dedicated-probe')],probe,'outer',probe/'dedicated-probe'/'supervisor-identity.json',deadline=time.monotonic()+5,pipe_output=True)
        receipt=fixture.small_json(probe/'dedicated-probe'/'subreaper-receipt.json')
        if receipt['status']!='ENGINEERING_SUBREAPER_SCOPE_COMPLETE' or receipt['subreaper_scope_reaped_to_echild'] is not True:
            raise RuntimeError('Tiny subreaper control did not complete: '+name)
        if name=='stdout-passthrough' and stdout!=b'tiny exact forwarded output\n':
            raise RuntimeError('Exact bounded tiny stdout passthrough differs')
        joined={'schema':'radio-native-v2-tiny-outer-observation-v2','probe':name,'tiny_probe_only':True,'large_preparation_worker_was_not_launched':True,
            'root_supervisor_receipt_fsync_and_termination_observed':observed['direct_child_reaped'],
            'subreaper_scope_reaped_to_echild':receipt['subreaper_scope_reaped_to_echild'],'reaped_process_count':receipt['reaped_process_count'],
            'elapsed_seconds_through_supervisor_termination':observed['elapsed_seconds'],
            'maximum_individual_process_rss_bytes':max(observed['peak_rss_bytes'],observed['observer_self_kernel_peak_rss_bytes'],receipt['maximum_individual_process_rss_bytes']),
            'bounded_stdout_bytes':len(stdout),'bounded_stdout_sha256':hashlib.sha256(stdout).hexdigest(),
            'caller_rss_accessor_checked':name=='rss-handshake','exact_stdout_passthrough_checked':name=='stdout-passthrough',
            'measurement_and_disposition_receipts_are_separate':receipt['measurements_fsynced_before_disposition'],
            'complete_descendant_wait_chain_verified':False,'full_source_worker_measurement_qualified':False,'whole_original_run_storage_and_time_joined':False,**fixture.AUTHORITY}
        fixture.write(probe/'joined-small-test.json',joined); tiny.append(joined)
    summary={'schema':'radio-native-v2-whole-worker-integration-review-v1',
        'status':'SEVEN_WORKER_ROLES_LINKED_EXECUTION_BLOCKED',
        'plan':fixture.pin(REPO/PLAN),'original_local_freeze':fixture.pin(REPO/FREEZE),
        'repository_code_files':len(freeze['repository_code_inventory']),
        'frozen_input_files':len(freeze['input_file_inventory']),
        'original_runtime_files':len(freeze['runtime_file_inventory']),
        'runtime_and_supplement_union_files':result['runtime_and_supplement_union_files'],
        'synthetic_unverified_public_claim_fixture_used':True,
        'source_worker_refusal_checks':rows,
        'independently_observed_tiny_controls':tiny,
        'seven_worker_role_dispatch_paths_present':True,
        'integration_scope':'prospective source wiring, local structural checks and refusal controls only',
        'runtime_integration_verified':False,'whole_driver_status_policy':'PENDING_FINAL_MEASUREMENT_JOIN',
        'final_report_fsync_and_termination_independently_observed':False,
        'local_supplied_claims_checked_without_execution_admission':True,
        'public_immutable_execution_preread_verified':False,
        'eight_input_resource_control_executed':False,
        'complete_pipeline_integration_qualified':False,
        'all_original_execution_blockers_closed':False,
        'preparation_audit_and_refusal_seconds':time.monotonic()-started,**fixture.AUTHORITY}
    fixture.write(OUT/'verification-summary.json',summary)
    print(json.dumps({key:summary[key] for key in ('status','repository_code_files',
        'original_runtime_files','runtime_and_supplement_union_files','preparation_audit_and_refusal_seconds')},sort_keys=True))
