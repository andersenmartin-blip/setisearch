"""Read-only closure audit and refusal checks; never generate a large source."""
import hashlib
import json
from pathlib import Path
import subprocess
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

OUT = Path(__file__).parent
PLAN = 'config/radio_native_v2_compact_eight_input_control_20261001d.plan.json'
FREEZE = 'config/radio_native_v2_source_worker_integration_20261001b.runtime.json'
INPUTS = [PLAN, *(path for path in fixture.CODE_FILES if path.startswith('tests/')),
    'tests/test_radio_native_v2_compact_preparation_audit.py',
    str(Path(__file__).relative_to(REPO))]


def exact_file(relative, value):
    path=REPO/relative; raw=fixture.canonical(value)
    if path.exists():
        if path.read_bytes()!=raw: raise RuntimeError('Existing output differs; preserve historical evidence: '+relative)
    else: fixture.write(path,raw)
    return raw


def refusal(argv, case_root, label):
    before=sorted(str(path.relative_to(case_root)) for path in case_root.rglob('*'))
    process=subprocess.run(argv,capture_output=True,timeout=20,env=fixture.CHILD_ENVIRONMENT)
    after=sorted(str(path.relative_to(case_root)) for path in case_root.rglob('*'))
    if process.returncode==0 or b'BLOCKED_PREPARATION_REVIEW' not in process.stderr or before!=after:
        raise RuntimeError('Worker/refusal did not close before side effects: '+label)
    fixture.write(OUT/(label+'-stderr.log'),process.stderr)
    return {'label':label,'returncode':process.returncode,'stdout_bytes':len(process.stdout),
        'stderr':fixture.pin(OUT/(label+'-stderr.log')),
        'no_scope_entries_created_or_removed':before==after,
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
        fixture.write(OUT/'local-structural-check.json',{'synthetic_unverified_public_claim_fixture':True,
            'retained_material_scope_was_temporary':True,'worker_check':local,
            'independent_supervisor_check':supervisor_check,**fixture.AUTHORITY})
    probe=OUT/'independent-tiny-orphan'; probe.mkdir()
    observed,_,_=fixture.observe_process([plan['runtime_executables']['python']['path'],'-I','-S','-B',
        str(REPO/'scripts/radio_native_v2_process_tree_supervisor.py'),'--probe','orphan',
        '--scope',str(probe/'dedicated-probe')],probe,'outer',
        probe/'dedicated-probe'/'supervisor-identity.json',deadline=time.monotonic()+5)
    receipt=fixture.small_json(probe/'dedicated-probe'/'subreaper-receipt.json')
    if receipt['status']!='ENGINEERING_SUBREAPER_SCOPE_COMPLETE' or receipt['subreaper_scope_reaped_to_echild'] is not True:
        raise RuntimeError('Tiny orphan subreaper control did not complete')
    joined={'schema':'radio-native-v2-tiny-orphan-outer-observation-v1',
        'tiny_probe_only':True,'large_preparation_worker_was_not_launched':True,
        'root_supervisor_receipt_fsync_and_termination_observed':observed['direct_child_reaped'],
        'subreaper_scope_reaped_to_echild':receipt['subreaper_scope_reaped_to_echild'],
        'reaped_process_count':receipt['reaped_process_count'],
        'elapsed_seconds_through_supervisor_termination':observed['elapsed_seconds'],
        'maximum_individual_process_rss_bytes':max(observed['peak_rss_bytes'],receipt['maximum_individual_process_rss_bytes']),
        'measurement_and_disposition_receipts_are_separate':receipt['measurements_fsynced_before_disposition'],
        'complete_descendant_wait_chain_verified':False,'full_source_worker_measurement_qualified':False,
        'whole_original_run_storage_and_time_joined':False,**fixture.AUTHORITY}
    fixture.write(probe/'joined-small-test.json',joined)
    summary={'schema':'radio-native-v2-source-worker-integration-review-v1',
        'status':'SOURCE_WORKER_LINKED_EXECUTION_BLOCKED',
        'plan':fixture.pin(REPO/PLAN),'original_local_freeze':fixture.pin(REPO/FREEZE),
        'repository_code_files':len(freeze['repository_code_inventory']),
        'frozen_input_files':len(freeze['input_file_inventory']),
        'original_runtime_files':len(freeze['runtime_file_inventory']),
        'runtime_and_supplement_union_files':result['runtime_and_supplement_union_files'],
        'synthetic_unverified_public_claim_fixture_used':True,
        'source_worker_refusal_checks':rows,
        'independently_observed_tiny_orphan_control':joined,
        'local_supplied_claims_checked_without_execution_admission':True,
        'public_immutable_execution_preread_verified':False,
        'eight_input_resource_control_executed':False,
        'complete_pipeline_integration_qualified':False,
        'all_original_execution_blockers_closed':False,
        'preparation_audit_and_refusal_seconds':time.monotonic()-started,**fixture.AUTHORITY}
    fixture.write(OUT/'verification-summary.json',summary)
    print(json.dumps({key:summary[key] for key in ('status','repository_code_files',
        'original_runtime_files','runtime_and_supplement_union_files','preparation_audit_and_refusal_seconds')},sort_keys=True))
