"""Inert finite scope writer from actual closed typed-plan JSON, without cache reads.

No imports of the worker/parser/cache loader; no HTTP or binary source access.
The runtime worker independently authenticates the complete cache and pointer
proof before any request. Source generation is root-only and create-only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
FAMILY='radio_visit2019_typed_completion_20261010'
TOOLS='tools/'+FAMILY
RESULTS='results/'+FAMILY
LOADER='tools/radio_visit2019_blc66_metadata_20261010/cache_admission.py'
BINDING='tools/radio_visit2019_blc66_headers_20261010/proofs/OWNER_GUARD_SOURCE_BINDING.json'


def require(test,message):
    if not test:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def path(name):
    p=Path(name)
    require(p.parts and not p.is_absolute() and '..' not in p.parts,'Canonical repository-relative metadata path required')
    p=ROOT/p
    require(p.resolve()==p and not p.is_symlink(),'Canonical regular metadata input required')
    return p


def read_json_pin(pin):
    require(set(pin)=={'path','bytes','sha256'} and type(pin['bytes']) is int and 0 <= pin['bytes'] <= 4194304
            and re.fullmatch(r'[0-9a-f]{64}',pin['sha256']) and pin['path'].endswith('.json'),'Exact bounded JSON pin required')
    raw=path(pin['path']).read_bytes();require(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'Metadata pin changed')
    return json.loads(raw)


def file_pin(name):
    require(Path(name).suffix in ('.py','.json','.md'),'Only UTF8 source/metadata dependency pins are allowed')
    raw=path(name).read_bytes();require(len(raw)<=4194304,'Bounded source/metadata dependency required');raw.decode('utf-8')
    return {'path':name,'bytes':len(raw),'sha256':sha(raw)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--expected-config-sha256',required=True)
    p.add_argument('--root-go-source-only-scope',action='store_true');args=p.parse_args()
    require(args.root_go_source_only_scope and re.fullmatch(r'[0-9a-f]{64}',args.expected_config_sha256),'Exact root metadata-only scope GO required')
    config_path=Path(args.config).resolve();require(config_path.is_relative_to(ROOT) and config_path.suffix=='.json','ROOT metadata config required')
    raw=config_path.read_bytes();require(len(raw)<=4194304 and sha(raw)==args.expected_config_sha256,'Config pin changed');config=json.loads(raw)
    round_id=config['round_id'];require(re.fullmatch(r'round_[0-9]{2}',round_id) and 1<=int(round_id[-2:])<=16,'Finite new round identity required')
    plan=read_json_pin(config['planner_result_pin']);execution=read_json_pin(config['planner_execution_pin']);parent=read_json_pin(config['planner_scope_pin'])
    require(plan['status']=='INCOMPLETE_TYPED_METADATA_FRAGMENTS'
            and execution['status']=='COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION'
            and execution['PLAN_RESULT_sha256']==config['planner_result_pin']['sha256']
            and execution['scope_sha256']==plan['scope_sha256']==config['planner_scope_pin']['sha256']
            and execution['resource_caps_satisfied'] is execution['all_input_end_readbacks_exact'] is True
            and plan['HTTP_requests']==execution['HTTP_requests']==0
            and plan['spectral_values_read'] is execution['spectral_values_read'] is False,
            'Only a closed clean actual typed metadata plan may form a transport scope')
    manifest=read_json_pin(config['cache_admission']['source_manifest_pin'])
    require(len(manifest['files'])==len(plan['sources'])==6,'Exact six source frame required')
    sources=[];number=0;body=0
    for identity,saved in zip(manifest['files'],plan['sources']):
        require(identity['source_id']==saved['source_id'] and saved['status'] in ('INCOMPLETE_TYPED_METADATA_FRAGMENTS','COMPLETE_SUPPORTED_HEADER_STRUCTURE')
                and not saved['invalid'] and not saved['unsupported'],'Any invalid/unsupported source blocks scope generation')
        requests=[]
        for proposal in saved['missing_metadata_fragments']:
            a,n=proposal['offset'],proposal['length'];require(type(a) is int and a>=0 and type(n) is int and 0<n<=65536
                    and proposal['source_id']==identity['source_id'] and proposal['payload_pointer'] is False
                    and proposal['HTTP_authorized'] is False and proposal['typed_parent_evidence'],'Typed metadata proposal required')
            number+=1;body+=n;requests.append({'request_id':f'R{number:03d}_{identity["source_id"]}','proposal':proposal})
        sources.append({k:identity[k] for k in ('source_id','url','ordered_index')}|{'requests':requests})
    require(0<number<=96 and 0<body<=1048576,'Finite nonempty BODY/request caps fail')
    required=[TOOLS+'/'+x for x in ('fetch_typed_round.py','launch_once.py','prepare_scope.py','METHOD.md','FIELD_SCHEMA.json','SOURCE_ONLY_REVIEW.json')]+[LOADER,BINDING]
    deps={name:file_pin(name) for name in required}
    for pin in config.get('additional_dependency_pins',[]):
        actual=file_pin(pin['path']);require(actual==pin,'Additional source/metadata pin changed');deps[pin['path']]=pin
    require(config['owner_binding_pin']==deps[BINDING],'Owner binding differs')
    scope={'schema':'SETI_VISIT2019_FIXED_TYPED_METADATA_FETCH_SCOPE_V1','stage_id':FAMILY,'round_id':round_id,
           'status':'PROSPECTIVE_FIXED_TYPED_METADATA_ONLY_NOT_EXECUTED','wrapper_path':TOOLS+'/fetch_typed_round.py',
           'wrapper_sha256':deps[TOOLS+'/fetch_typed_round.py']['sha256'],
           'output_directory':RESULTS+'/'+round_id,'root_admission_path':RESULTS+'/'+round_id+'_ROOT_ADMISSION.json',
           'cache_admission':config['cache_admission'],'sources':sources,'owner_binding_pin':config['owner_binding_pin'],
           'prior_attempted_request_pins':config['prior_attempted_request_pins'],'pinned_dependency_files':deps,
           'limits':{'CPU_seconds':20,'wall_seconds':300,'memory_bytes':536870912,'output_bytes':33554432,
                     'shared_workspace_bytes':12884901888,'application_BODY_cap_bytes':body,'maximum_GET_requests':96,
                     'HEAD_requests':0,'retries':0,'redirects':0,'metadata_followup_requests':0},
           'source_values_admission':'BLOCKED_PROTECTED_REGISTRY_UNRESOLVED','native_acquisition_admission':'BLOCKED',
           'independent_validation_admission':'BLOCKED','geometry':None,'midpoint':None,'cost_DKK':0,
           'source_generation_config_pin':{'path':str(config_path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)},
           'declared_requests':number,'requires_exact_public_scope_freeze_root_admission_and_GO':True}
    for key in ('planner_scope_pin','planner_result_pin','planner_execution_pin','planner_worker_pin','planner_parser_pin'):scope[key]=config[key]
    output=ROOT/TOOLS/'scopes';output.mkdir(exist_ok=True)
    target=output/(round_id+'.json');scope_raw=(json.dumps(scope,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    require(len(scope_raw)<=2097152,'Scope serialization cap exceeded')
    with target.open('xb') as h:h.write(scope_raw);h.flush();os.fsync(h.fileno())
    fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps({'path':str(target.relative_to(ROOT)),'bytes':len(scope_raw),'sha256':sha(scope_raw),'requests':number,'BODY_reserved_bytes_proposed':body,'HTTP_requests':0}))

if __name__=='__main__':main()
