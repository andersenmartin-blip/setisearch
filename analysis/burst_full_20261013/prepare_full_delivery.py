"""Prepare full delivery extension pins only after actual scientific QA PASS.

Source-only --check-only reads no result metadata or numerical payload. --run
requires exact public source freeze/root GO, reads admitted JSON/Markdown, and
hashes explicitly permitted artifact bytes without NPZ/PDF decoding. It never
imports the producer, detector, helpers, NumPy, HDF5 or reporting libraries.
The final PDF is optional so the first/final ZIP can precede archive replay.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

BASE,PILOT='seti_burst_full','seti_burst_on'
ROOTS=(BASE,PILOT)
ALLOWED={'.py','.json','.md','.txt','.npz','.csv','.png','.pdf','.jsonl'}
PILOT_CLOSED_DIRS=('results','qa_results','context_results','context_qa_results','report_dependencies')
FULL_CLOSED_DIRS=('qa_results','aggregate_results','aggregate_qa_results','context_results','context_qa_results',
                  'report_results','report_dependencies','delivery')
FORBIDDEN_PARTS={'__pycache__','archive','archives','tmp','temp','temporary','fresh_saved_replay','saved_replay_results',
                 'context_portable_replay','context_saved_replay','portable_replay','replay_fresh','fresh_replay'}
MAIN_STATUS='PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY'
GLOBAL_STATUS='PASS_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
CONTEXT_STATUS='PASS54_FULL_BAND_CLEAN_TOP9_FIXED_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS_AND_DC_DIAGNOSTICS'
AGGREGATE_STATUS='COMPLETE_GLOBAL_3_ON_SCANS_766_CORES_EACH_RAW700_SPACED100_TOP3_DUAL_WINNERS'
CONTEXT_EXECUTION_STATUS='COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
SCIENCE_STATUS='COMPLETE_AUTHENTICATED_FULL_ON_SCIENTIFIC_REVIEW_NO_QUALIFIED_SETI_DETECTION'
CPU_CAP,WALL_CAP,MEMORY_CAP,OUTPUT_CAP=180,600,1024**3,16*1024**2


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def unique_pairs(items):
    result={}
    for key,value in items:
        require(key not in result,'Duplicate JSON key');result[key]=value
    return result


def read(path):
    return json.loads(Path(path).read_bytes(),object_pairs_hook=unique_pairs,
                      parse_constant=lambda v:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root,name):
    p=Path(name)
    require(not p.is_absolute() and '..' not in p.parts,'Safe relative research path required')
    path=root/p
    require(path.resolve().is_relative_to(root) and not path.is_symlink(),'Unconfined/symlink path')
    return path


def pin(root,path):
    return {'path':Path(path).relative_to(root).as_posix(),'bytes':Path(path).stat().st_size,'sha256':digest(path)}


def allowed_name(name):
    p=Path(name)
    return (bool(p.parts) and p.parts[0] in ROOTS and p.suffix in ALLOWED
            and not any(part in FORBIDDEN_PARTS or part.startswith('fresh_') for part in p.parts)
            and not (p.parts[0]==BASE and len(p.parts)>1 and p.parts[1]=='results'))


def save(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    require(len(raw)<=OUTPUT_CAP,'Delivery manifest output cap exceeded')
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def prepare(root,args):
    started,cpu0=time.monotonic(),time.process_time()
    code_path=Path(__file__).resolve();code_sha=digest(code_path)
    freeze_path=confined(root,BASE+'/FULL_DELIVERY_BUILDER_FREEZE.json')
    require(args.freeze_sha256 and digest(freeze_path)==args.freeze_sha256,'Exact public builder source freeze required')
    freeze=read(freeze_path)
    require(freeze['status']=='PASS_PUBLIC_FREEZE_FULL_DELIVERY_BUILDER_READBACK'
            and freeze['code_sha256']==code_sha and re.fullmatch('[0-9a-f]{40}',freeze['public_commit']),
            'Public source-only builder freeze differs')
    go_path=confined(root,args.go)
    require(args.go_sha256 and digest(go_path)==args.go_sha256,'Exact root delivery-preparation GO required')
    go=read(go_path)
    require(go['status']=='GO_PREPARE_FULL_BURST_DELIVERY_PINS_AFTER_SCIENCE_QA'
            and go['code_sha256']==code_sha and go['freeze_sha256']==args.freeze_sha256
            and (go['CPU_cap_s'],go['wall_cap_s'],go['memory_cap_bytes'],go['output_cap_bytes'])
                ==(CPU_CAP,WALL_CAP,MEMORY_CAP,OUTPUT_CAP),'Root builder scientific/resource admission differs')
    admitted={p['path']:p for p in go['input_pins']}
    require(len(admitted)==len(go['input_pins']),'Duplicate admitted metadata pins')
    checked={}
    def bound(name):
        require(name in admitted,'Root GO must pin every consumed scientific metadata input: '+name)
        path=confined(root,name)
        require(Path(name).suffix in ('.json','.md','.py','.txt') and pin(root,path)==admitted[name],
                'Admitted scientific metadata byte pin differs: '+name)
        checked[name]=admitted[name];return path
    def loaded(name):return read(bound(name))
    replay_name=BASE+'/REPLAY_SCOPE.json';replay=loaded(replay_name)
    require(replay['schema']=='SETI_NEW2010_PORTABLE_SAVED_REPLAY_SCOPE_V1'
            and replay['status']=='READY_SAVED_DATA_REPLAY','Exact NEW2010 base replay closure required')
    base={p['path']:p for p in replay['file_pins']}
    require(len(base)==len(replay['file_pins']),'Duplicate base replay closure pins')
    main_name=BASE+'/qa_results/QA_RECEIPT.json';main=loaded(main_name)
    global_name=BASE+'/aggregate_qa_results/QA_RECEIPT.json';global_qa=loaded(global_name)
    context_name=BASE+'/context_qa_results/QA_RECEIPT.json';context_qa=loaded(context_name)
    aggregate_name=BASE+'/aggregate_results/EXECUTION_RECEIPT.json';aggregate=loaded(aggregate_name)
    execution_name=BASE+'/context_results/EXECUTION_RECEIPT.json';execution=loaded(execution_name)
    require(main['status']==MAIN_STATUS and main['counts']['maps']==2010
            and main['counts']['scalar_queries']==10050 and main['counts']['independent_dual_remax_cores']==18
            and main['counts']['clean_EMPTY_carriers']==9,'Actual original main QA not full PASS')
    require(global_qa['status']==GLOBAL_STATUS and global_qa['mismatch_count']==0
            and global_qa['map_count']==2298 and global_qa['totalcarriers']==9412608
            and global_qa['full_map_census_exact'] is True and global_qa['pilot288unchanged'] is True
            and global_qa['aggregate_receipt_sha256']==admitted[aggregate_name]['sha256'],
            'Actual independent global QA/census not exact PASS')
    require(aggregate['status']==AGGREGATE_STATUS and aggregate['counts']['maps']==2298
            and aggregate['counts']['new_maps']==2010 and aggregate['counts']['pilot_maps_reused']==288
            and aggregate['counts']['carrier_references']==9412608,'Completed full2298 aggregate census differs')
    require(context_qa['status']==CONTEXT_STATUS and context_qa['portable_saved_crop_replay'] is False
            and context_qa['original_HDF5_compacts_opened'] is True
            and context_qa['counts']['context_profiles']==54 and context_qa['counts']['origin_score_matches']==9
            and context_qa['context_receipt_sha256']==admitted[execution_name]['sha256']
            and context_qa['primary_qa_receipt_sha256']==admitted[main_name]['sha256']
            and context_qa['aggregate_qa_receipt_sha256']==admitted[global_name]['sha256'],
            'Actual original-source context QA/9 own matches not PASS')
    require(execution['status']==CONTEXT_EXECUTION_STATUS and execution['counts']['context_profiles']==54
            and execution['counts']['origin_score_matches']==9,'Completed context/own-match census differs')
    report_name=go['science_results_path'];report_path=bound(report_name)
    require(Path(report_name).name=='RESULTS.md' and report_path.stat().st_size>0,'Final science RESULTS.md required')
    science_name=go['science_review_path'];science=loaded(science_name)
    require(science['status']==SCIENCE_STATUS and science['all_three_actual_QA_pass'] is True
            and science['counts']['new_maps']==2010 and science['counts']['unchanged_pilot_maps']==288
            and science['counts']['maps_total']==2298 and science['counts']['reference_carriers_total']==9412608
            and science['counts']['selected_clean_tracks']==9 and science['counts']['context_profiles']==54
            and science['counts']['origin_ON']==9 and science['qualified_SETI_detection'] is False,
            'Actual completed final science review differs')
    require(science['QA_receipts']=={'main':admitted[main_name],'global':admitted[global_name],'context':admitted[context_name]},
            'Final science review must bind same three actual QA PASS receipts')
    files={};roles={};directories=[]
    def add(name,role,expected=None):
        require(allowed_name(name),'Artifact outside approved research namespaces/extensions: '+name)
        path=confined(root,name);p=pin(root,path)
        require(expected is None or p==expected,'Declared artifact/source pin differs: '+name)
        if name in base:
            require(base[name]==p,'Artifact conflicts with immutable base replay closure');return
        require(name not in files or files[name]==p,'Conflicting extra file pins')
        files[name]=p;roles.setdefault(name,set()).add(role)
    # Pilot direct code/metadata files are a closed research surface. Logs,
    # lockfiles, archives and caches fail the exact extension/path allowlist.
    for path in sorted((root/PILOT).iterdir()):
        if path.is_file() and allowed_name(path.relative_to(root).as_posix()):
            add(path.relative_to(root).as_posix(),'closed_pilot_root_code_metadata')
    approved_directories=[PILOT+'/'+name for name in PILOT_CLOSED_DIRS]+go['approved_full_directories']
    allowed_directories={PILOT+'/'+name for name in PILOT_CLOSED_DIRS}|{BASE+'/'+name for name in FULL_CLOSED_DIRS}
    require(len(approved_directories)==len(set(approved_directories))
            and set(approved_directories).issubset(allowed_directories),'Explicit stable closed directories required')
    for name in approved_directories:
        parent=confined(root,name);require(parent.is_dir(),'Approved closed artifact directory missing: '+name)
        directories.append(name)
        for current,dirs,items in os.walk(parent,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d not in FORBIDDEN_PARTS and not d.startswith('fresh_'))
            for item in sorted(items):
                path=Path(current)/item;relative=path.relative_to(root).as_posix()
                if allowed_name(relative):add(relative,'closed_artifact_directory:'+name)
    for path in (code_path,freeze_path,go_path):
        add(path.relative_to(root).as_posix(),'builder_source_public_freeze_root_admission')
    for name in go['approved_root_files']:
        require(len(Path(name).parts)==2 and Path(name).parts[0] in ROOTS,'Approved direct research-root file required')
        add(name,'root_approved_code_metadata')
    for name in checked:
        if name in base:require(pin(root,confined(root,name))==base[name],'Base admitted metadata changed')
        else:add(name,'actual_scientific_gate_or_results',checked[name])
    # Bind every actual report/review dependency even if inherited from the
    # base replay closure. No imports or broad filesystem searches occur.
    dependencies=[]
    for p in go['bound_report_review_dependency_pins']:
        name=p['path'];path=confined(root,name)
        require(name in base or allowed_name(name),'Report/review dependency outside research closure')
        require(pin(root,path)==p,'Bound report/review dependency differs')
        dependencies.append(p)
        if name not in base:add(name,'bound_report_review_dependency',p)
    for p in science['input_pins_verified']:
        require(p['path'] in base or allowed_name(p['path']),'Final review consumed undeclared external dependency')
        path=confined(root,p['path']);require(pin(root,path)==p,'Actual final science review dependency differs')
        if p['path'] not in base:add(p['path'],'actual_final_science_review_input',p)
    optional=[]
    for declaration in go.get('optional_final_PDF_pins',[]):
        name=declaration['path'];require(allowed_name(name) and Path(name).suffix=='.pdf','Optional PDF path outside exact research allowlist')
        path=confined(root,name)
        if path.is_file():
            require(pin(root,path)==declaration,'Optional existing final PDF pin differs')
            add(name,'optional_existing_final_PDF',declaration);optional.append(declaration)
    # Every closed pilot map and normalization must be present either in base
    # metadata or this extension. New2010 primary files remain base-only.
    merged={**base,**files};pilot_maps=0
    for epoch in (1,2,3):
        parent=f'{PILOT}/results/on20170428_epoch{epoch}_HIP98505'
        manifest=read(confined(root,parent+'/MAPS.json'))
        require(len(manifest['records'])==96,'Exact pilot map census differs')
        for record in manifest['records']:
            for p in ({k:record[k] for k in ('path','bytes','sha256')},record['normalization']):
                require(merged.get(p['path'])==p,'Full extension omits/conflicts with pilot map/normalization')
            pilot_maps+=1
    require(pilot_maps==288,'All288 pilot maps required')
    for record in aggregate['output_pins']+execution['output_pins']:
        require(merged.get(record['path'])==record,'Full extension omits/conflicts with completed global/context output')
    for name in files:require(pin(root,confined(root,name))==files[name],'Extra artifact changed during closure preparation')
    for name,p in checked.items():require(pin(root,confined(root,name))==p,'Scientific gate changed during closure preparation')
    require(digest(code_path)==code_sha and digest(freeze_path)==args.freeze_sha256 and digest(go_path)==args.go_sha256,
            'Builder source/freeze/GO changed during preparation')
    usage={'process_CPU_seconds':time.process_time()-cpu0,'wall_seconds':time.monotonic()-started,
           'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    require(usage['process_CPU_seconds']<=CPU_CAP and usage['wall_seconds']<=WALL_CAP and usage['peak_RSS_bytes']<=MEMORY_CAP,
            'Delivery preparation measured cap exceeded')
    manifest={'schema':'SETI_FULL_BURST_EXTENDED_DELIVERY_EXTRA_PINS_V1','status':'READY_FULL_DELIVERY_EXTENSIONS',
        'pilot_maps':288,'new_maps':2010,'total_maps':2298,'reference_carriers':9412608,'context_profiles':54,'own_score_matches':9,
        'files':[files[n] for n in sorted(files)],'file_roles':{n:sorted(roles[n]) for n in sorted(roles)},
        'base_replay_scope_pin':admitted[replay_name],'base_replay_closure_bytes':replay['complete_new2010_closure_bytes'],
        'extra_payload_bytes':sum(p['bytes'] for p in files.values()),'stable_closed_directories':directories,
        'actual_scientific_gate_pins':list(checked.values()),'report_review_dependency_pins':dependencies,
        'science_results_pin':admitted[report_name],'science_review_pin':admitted[science_name],
        'optional_final_PDFs_included':optional,'final_PDF_required_before_archive':False,
        'archive_saved_replay_PASS_required_before_preparation':False,
        'builder_code_sha256':code_sha,'builder_public_freeze_sha256':args.freeze_sha256,'root_go_sha256':args.go_sha256,**usage,
        'numerical_payloads_decoded':False,'source_HDF5_files_opened':False,'producer_or_helper_imported':False,
        'new2010_primary_results_duplicated_in_extras':False,'new_telescope_HTTP_requests':0,
        'scientific_replay_claim':'Extra full scientific delivery bytes included and hashed. Existing portable numerical replay remains NEW2010 scalar/18DC only.',
        'hash_cycle_policy':'Final PDF and archive replay readback receipts may be saved separately after the one archive; no second archive build is required.'}
    output=confined(root,args.output);require(output.parent==root/BASE,'Fresh manifest must be direct full research-root file')
    save(output,manifest);print(json.dumps({'status':manifest['status'],'output':pin(root,output),
        'extra_payload_bytes':manifest['extra_payload_bytes'],'extra_files':len(files),'pilot_maps':288}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--check-only',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--go',default=BASE+'/FULL_DELIVERY_PREPARE_GO.json');p.add_argument('--go-sha256');p.add_argument('--freeze-sha256')
    p.add_argument('--output',default=BASE+'/FULL_DELIVERY_EXTRA_PINS.json')
    args=p.parse_args()
    if args.check_only:
        print(json.dumps({'status':'PASS_SOURCE_ONLY_FULL_DELIVERY_BUILDER_INTERFACE','required_actual_QA':['main2010','global2298','context54_own9'],
            'pilot_maps':288,'base_new_maps':2010,'optional_final_PDF':True,'no_archive_replay_dependency':True,
            'numeric_payloads_read_or_decoded':False,'external_imports':False,
            'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,'output_cap_bytes':OUTPUT_CAP}));return
    require(args.run,'Explicit root run required')
    def alarm(signum,frame):raise TimeoutError('Full delivery preparation cap')
    signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGXCPU,alarm)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP));signal.alarm(WALL_CAP)
    try:prepare(args.root.resolve(),args)
    finally:signal.alarm(0)


if __name__=='__main__':main()
