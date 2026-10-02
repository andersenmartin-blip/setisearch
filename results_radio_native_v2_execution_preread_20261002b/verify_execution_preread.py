#!/usr/bin/env python3
"""Build the fresh preread for the integrated marker-receipt preparation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
for folder in (REPO/'scripts',REPO/'src'):
    sys.path.insert(0,str(folder))
import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_worker_admission as admission

OUT=Path(__file__).parent
PLAN=REPO/'config/radio_native_v2_compact_eight_input_control_20261002j.plan.json'
FREEZE=REPO/'config/radio_native_v2_activation_environment_20261002d.runtime.json'
PREREAD=REPO/'config/radio_native_v2_execution_preread_20261002b.json'
OLD_PREREAD=REPO/'config/radio_native_v2_execution_preread_20261002a.json'
PREPARATION_COMMIT='25e9df222af79c677adc1ad247104fd6b0c4d68e'
PREPARATION_TREE='dcd3937ab8dbea11e895f5cfb47a94c8c6807e49'


def git(*args):
    return subprocess.check_output(['git','--no-replace-objects',*args],cwd=REPO,
        text=True,timeout=20).strip()


def pin(path):
    raw=path.read_bytes(); return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def main():
    started=time.monotonic()
    if git('rev-parse',PREPARATION_COMMIT+'^{tree}')!=PREPARATION_TREE:
        raise RuntimeError('Public integrated preparation tree differs')
    for path in (PLAN,FREEZE):
        relative=str(path.relative_to(REPO))
        if git('rev-parse',PREPARATION_COMMIT+':'+relative)!=git('hash-object',relative):
            raise RuntimeError('Public integrated preparation blob differs: '+relative)
    plan=json.loads(PLAN.read_bytes()); freeze=json.loads(FREEZE.read_bytes())
    if plan!=fixture.build_plan(REPO): raise RuntimeError('Current plan differs from integrated preparation')
    admission._validate_plan(plan); admission._validate_freeze(freeze)
    proof={'schema':fixture.PREREAD_SCHEMA,'namespace':fixture.NAMESPACE,
        'plan_sha256':hashlib.sha256(fixture.canonical(plan)).hexdigest(),
        'complete_freeze_sha256':hashlib.sha256(fixture.canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified':True,'engineering_control_admitted':True,
        'code_files_verified':plan['code_files'],'preparation_commit':PREPARATION_COMMIT,
        **fixture.AUTHORITY}
    if PREREAD.exists():
        if json.loads(PREREAD.read_bytes())!=proof: raise RuntimeError('Existing fresh preread differs')
    else: fixture.write(PREREAD,proof)
    old=json.loads(OLD_PREREAD.read_bytes())
    if old['plan_sha256']==proof['plan_sha256'] or old['complete_freeze_sha256']==proof['complete_freeze_sha256']:
        raise RuntimeError('Fresh preread did not separate from old plan/freeze')
    identities=[]
    for ordinal,case in enumerate(plan['cases']):
        if case['ordinal']!=ordinal or case['source_case_id']!=fixture.NAMESPACE+f'/case{ordinal:02d}':
            raise RuntimeError('Fixed ordered worker identity differs')
        identities.append({'ordinal':ordinal,'source_case_id':case['source_case_id'],
            'source_domain_hex':case['source_domain_hex'],'archive_prefix':case['archive_prefix']})
    negatives=[]
    for label,mutate in (('admission_false',lambda x:x.__setitem__('engineering_control_admitted',False)),
            ('changed_plan_pin',lambda x:x.__setitem__('plan_sha256','0'*64)),
            ('old_preparation_commit',lambda x:x.__setitem__('preparation_commit',old['preparation_commit']))):
        changed=copy.deepcopy(proof); mutate(changed)
        matches=(changed==proof)
        negatives.append({'label':label,'closed':not matches})
        if matches: raise RuntimeError('Negative preread mutation unexpectedly matches: '+label)
    summary={'schema':'radio-native-v2-execution-preread-result-v2',
        'status':'FRESH_EXECUTION_PREREAD_STRUCTURALLY_VERIFIED_PUBLICATION_PENDING',
        'plan':pin(PLAN),'complete_freeze':pin(FREEZE),'preread':pin(PREREAD),
        'public_preparation_commit':PREPARATION_COMMIT,'public_preparation_tree':PREPARATION_TREE,
        'public_preparation_plan_and_freeze_blobs_verified':True,
        'distinct_from_old_preread_plan_and_freeze':True,
        'fresh_preread_structure_verified':True,'fixed_eight_worker_identities_verified':True,
        'worker_identities':identities,'negative_checks':negatives,
        'worker_bundle_activation_receipt_join_deferred_until_marker':True,
        'activation_marker_created':False,'activation_public_readback_verified':False,
        'historical_preparation_contract_rewritten':False,
        'plan_execution_status':plan['execution_status'],'activation_guard_complete':False,
        'large_inputs_generated':False,'eight_input_resource_control_executed':False,
        'execution_authorized':False,'reservation_authorized':False,
        'scientific_execution_authorized':False,'native_case_reservations':0,
        'native_case_executions':0,'scientific_cases_run':0,'rng_draws':0,
        'telescope_reads':0,'network_fetches':0,'automatic_retry':False,
        'elapsed_seconds':time.monotonic()-started}
    fixture.write(OUT/'verification-summary.json',summary)
    print(json.dumps({'status':summary['status'],'preread':summary['preread'],
        'identities':len(identities),'negative_checks':len(negatives)},sort_keys=True))


if __name__=='__main__': main()
