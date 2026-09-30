#!/usr/bin/env python3
"""Prepare and freeze fresh native-v2 metadata; deliberately cannot execute."""
import argparse
import hashlib
import json
import subprocess

from radio_receiver_adapter_common import ROOT,PINS,context
from seti_repeater import native_v2_parent_radio as parent
from seti_repeater import whole_cadence_journal_radio as journal
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_runtime_radio import capture

BASE='results_radio_native_v2_preparation_2026-09-30'
OUT=ROOT/BASE
SCOPE='RADIO_NATIVE_V2_PREPARATION_2026-09-30_SCOPE.md'
PROPOSAL='config/radio_whole_cadence_null_proposal_20260928.json'
OLD_PLANS='results_radio_native_chain_engineering_2026-09-29/plans.json'


def write(name,value):
    journal.durable_write(OUT/name,canonical(value))


def metadata_inventory(paths):
    query=''.join('HEAD:'+path+'\n' for path in paths).encode()
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,input=query)
    offset=0;inventory=[];seeds=set();identities=set();documents={}
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if 'seed' in key.lower() and type(item) is int:seeds.add(item)
                if 'identity' in key.lower() and isinstance(item,str):identities.add(item)
                walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    for path in paths:
        end=raw.index(b'\n',offset);header=raw[offset:end].split();offset=end+1
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Missing pinned metadata: '+path)
        size=int(header[2]);data=raw[offset:offset+size];offset+=size+1
        value=json.loads(data);walk(value);documents[path]=value
        inventory.append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    if offset!=len(raw):raise ValueError('Grouped metadata read framing differs')
    return inventory,seeds,identities,documents


def prepare():
    if not OUT.is_dir():raise ValueError('Precreated preparation evidence directory required')
    c=context('validation');plans=[parent.make_plan(c,i) for i in range(parent.CASE_COUNT)]
    config_paths=sorted(filter(None,subprocess.check_output(
        ['git','ls-files','-z','--','config/*.json'],cwd=ROOT).decode().split('\0')))
    paths=config_paths+[OLD_PLANS]
    inventory,seeds,identities,documents=metadata_inventory(paths)
    reserved=documents[PROPOSAL]['cases'];old_plans=documents[OLD_PLANS]
    forbidden=reserved+[plan['case'] for plan in old_plans]
    for plan in plans:
        parent.validate_plan(c,plan,forbidden)
        if plan['case']['seed'] in seeds or plan['case']['identity'] in identities:
            raise ValueError('Historical metadata seed/identity collision')
    if len({p['case']['seed'] for p in plans})!=8 or len({p['case']['identity'] for p in plans})!=8:
        raise ValueError('Fresh plan identities must be unique')
    cases=[parent.case_binding(plan) for plan in plans]
    configs=[parent.physical_config(case) for case in cases]
    allocation={'schema':'radio-native-v2-preparation-allocation-v1','namespace':parent.NAMESPACE,
        'mode':'PREPARED_NOT_RESERVED','cases':cases,'caps':parent.caps(),
        'milliseconds_per_case':parent.CASE_MILLISECONDS,'artifact_bytes_per_case':parent.CASE_BYTES,
        'checkpoint_limit':parent.CHECKPOINT_LIMIT,'physical_max_files':parent.PHYSICAL_MAX_FILES,
        'all_eight_must_be_reserved_before_first_draw':True,'currently_reserved':False,
        'restart_or_refund_authorized':False,'scientific_allocation_charged':False}
    write('plans.json',plans);write('identity_inventory.json',{'metadata_files':inventory,
        'historical_seed_count':len(seeds),'historical_identity_count':len(identities),
        'reserved_scientific_cases':len(reserved),'closed_native_cases':len(old_plans),
        'new_engineering_cases':len(plans),'collisions':[],'holdout_values_opened':False,
        'random_independence_inferred':False})
    write('allocation.json',allocation);write('physical_configs.json',configs)
    write('artifact_groups.json',parent.physical_case.multi_policy(configs,max_files=parent.PHYSICAL_MAX_FILES))
    write('bounds.json',parent.record());write('journal_model.json',parent.worst_case_journal_model())
    recipe={'schema':'radio-native-v2-manifest-recipe-v1','namespace':parent.NAMESPACE,
        'allocation_sha256':digest(allocation),'cases':cases,'caps':parent.caps(),
        'required_artifacts':list(parent.REQUIRED_ARTIFACTS),
        'physical_configs_sha256':digest(configs),
        'artifact_groups_sha256':digest(parent.physical_case.multi_policy(configs,max_files=parent.PHYSICAL_MAX_FILES)),
        'execution_binding':'REQUIRES_COMPLETE_RUNNER_AND_BROKER_RUNTIME_FREEZE',
        'reservation_authorized':False,'rng_authorized':False}
    write('manifest_recipe.json',recipe)
    inputs=[*PINS,PROPOSAL,SCOPE,BASE+'/plans.json',BASE+'/identity_inventory.json',
        BASE+'/allocation.json',BASE+'/physical_configs.json',BASE+'/artifact_groups.json',
        BASE+'/bounds.json',BASE+'/journal_model.json',BASE+'/manifest_recipe.json',
        'tests/test_radio_native_v2_parent.py',BASE+'/preflight_tests.log']
    freeze=capture(ROOT,inputs);write('preparation_runtime_freeze.json',freeze)
    result={'schema':'radio-native-v2-preparation-result-v1','status':'PREPARED_NOT_EXECUTABLE',
        'namespace':parent.NAMESPACE,'case_count':8,'plan_sha256s':[p['plan_sha256'] for p in plans],
        'case_identities':[p['case']['identity'] for p in plans],
        'preparation_runtime_freeze_sha256':digest(freeze),
        'repository_python_files':len(freeze['code_sha256s']),
        'runtime_files':len(freeze['runtime_sha256s']),'reservation_authorized':False,
        'rng_authorized':False,'new_random_values':0,'telescope_values_opened':False,
        'missing_gate':'PUBLICATION_DURING_EXECUTION_BROKER_AND_COMPLETE_RUNNER_FREEZE'}
    write('result.json',result)
    return result


def run():
    raise ValueError('PREPARED_NOT_EXECUTABLE: broker and complete public runner freeze required')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    print(json.dumps(prepare() if args.action=='prepare' else run(),sort_keys=True,indent=2))
