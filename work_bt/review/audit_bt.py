"""Independent frozen BT archive/process/semantic review; no production runs.

This reviewer neither imports the BT worker nor uses its ZIP verification.
A04 endpoints are checked with the earlier independent BP review helper.
"""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
HELPER='work_bp/review/audit_results.py'
HELPER_SHA='6f7036aa4f11cd3d56f0ec498015dfa0f3b4b1bb88537e1f65ebd353465d1f65'
STATES=('PASS','UNSUPPORTED','THREE_ON_FAIL','OFF_VETO')
START=time.monotonic()

def check(ok,message):
    if not ok:raise ValueError(message)
    if time.monotonic()-START>118:raise TimeoutError('Independent BT review118second limit')

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def pairs(items):
    out={}
    for key,value in items:
        check(key not in out,'Duplicate JSON key');out[key]=value
    return out

def bad_constant(value):raise ValueError('Nonfinite JSON constant '+value)
def loads(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad_constant)
def read(path):return loads(Path(path).read_bytes())
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def ident(info):
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)

def safe_name(name):
    check(isinstance(name,str) and name and '\\' not in name and '\x00' not in name,'Unsafe member name')
    path=PurePosixPath(name)
    check(not path.is_absolute() and str(path)==name and all(p not in ('','.','..') for p in name.split('/')),'Unsafe member path')
    return name

def pin_checks(pins):
    seen=set()
    for pin in pins:
        name=safe_name(pin['path']);check(name not in seen,'Duplicate pin');seen.add(name)
        p=REPO/name;s=p.stat(follow_symlinks=False)
        check(stat.S_ISREG(s.st_mode) and p.resolve()==p.absolute(),'Unsafe source/input pin')
        check(s.st_size==pin['bytes'] and sha(p)==pin['sha256'],'Changed pin '+name)

def archive_members(path,declared):
    """Validate every member's CRC, expanded byte count and SHA independently."""
    path=Path(path);before=path.stat(follow_symlinks=False)
    check(stat.S_ISREG(before.st_mode) and path.resolve()==path.absolute(),'Unsafe archive')
    check(before.st_size<=512<<20,'Archive exceeds cap')
    names=[safe_name(item['path']) for item in declared]
    check(names==sorted(names) and len(names)==len(set(names)) and 0<len(names)<=100,'Invalid manifest membership')
    check('ARCHIVE_MANIFEST.json' not in names,'Reserved member name')
    check(all(set(x)=={'path','bytes','sha256'} and isinstance(x['bytes'],int) and not isinstance(x['bytes'],bool) and 0<=x['bytes']<=256<<20 for x in declared),'Invalid manifest receipts')
    check(sum(x['bytes'] for x in declared)<=512<<20,'Expanded archive exceeds cap')
    verified=[]
    with path.open('rb') as raw:
        check(ident(os.fstat(raw.fileno()))==ident(before),'Archive descriptor mismatch')
        with zipfile.ZipFile(raw) as z:
            infos=z.infolist();actual=[safe_name(i.filename) for i in infos]
            check(len(actual)==len(set(actual)) and set(actual)==set(names)|{'ARCHIVE_MANIFEST.json'},'Archive membership differs')
            for info in infos:
                mode=info.external_attr>>16
                check(info.orig_filename==info.filename and not info.is_dir() and stat.S_IFMT(mode) in (0,stat.S_IFREG),'Nonregular/ambiguous member')
                check(not info.flag_bits&1 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'Encrypted/unsupported member')
            expected_manifest=canonical(dict(schema='SETI_BT_ARCHIVE_MANIFEST_V1',members=declared))
            check(z.getinfo('ARCHIVE_MANIFEST.json').file_size==len(expected_manifest),'Manifest size')
            check(z.read('ARCHIVE_MANIFEST.json')==expected_manifest,'Manifest bytes')
            for item in declared:
                info=z.getinfo(item['path']);check(info.file_size==item['bytes'],'ZIP expanded size')
                h=hashlib.sha256();n=0
                with z.open(info) as source:
                    while True:
                        data=source.read(1<<20)
                        if not data:break
                        n+=len(data);check(n<=item['bytes'],'Member exceeds receipt');h.update(data)
                actual_item=dict(path=item['path'],bytes=n,sha256=h.hexdigest())
                check(actual_item==item,'Expanded member hash/size differs');verified.append(actual_item)
        raw.seek(0);digest=hashlib.file_digest(raw,'sha256').hexdigest()
        check(ident(os.fstat(raw.fileno()))==ident(before),'Archive changed during verification')
    check(ident(path.stat())==ident(before),'Archive pathname changed')
    return dict(bytes=before.st_size,sha256=digest,members=verified,all_member_CRCs_verified=True)

def exact_inventory(folder,terminal):
    expected={item['path']:item for item in terminal['files']}
    check(len(expected)==len(terminal['files']),'Duplicate terminal file')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='TERMINAL_BT.json'}
    check(actual==set(expected),'Post-terminal inventory paths changed')
    size=0
    for name,item in expected.items():
        safe_name(name);p=folder/name
        check(not p.is_symlink() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Post-terminal evidence changed '+name)
        size+=item['bytes']
    return len(expected),size

def fixture_line(stream,index):
    value={'schema':'BS_ARTIFICIAL_FILE_FIXTURE_V1','stream':stream,'index':index,
           'status':'OFF_VETO' if index%3==0 else 'THREE_ON_FAIL',
           'payload':'0123456789abcdef'*118+'0123456789ab'}
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def check_bindings(z,result,plan,kind):
    binding=loads(z.read('BT_SOURCE_INPUT_BINDINGS.json'))
    keys=['source_pins_before','source_pins_after','input_pins_before','input_pins_after',
          'source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after']
    check(binding=={key:result[key] for key in keys},'Inner/outer source-input bindings differ')
    for key in keys[4:]:check(binding[key] is True,'Incomplete source/input pin verification')
    br=read(REPO/'work_br/BR_POSTPROCESSING_PLAN.json')
    expected={x['path']:x for x in br['source_pins']}
    bt_sources={x['path']:x for x in plan['source_pins']}
    for name in ['work_bs/diagnostic.py','work_br/closed_association.py','work_br/stream_closure.py','work_br/BR_POSTPROCESSING_PLAN.json']:
        check(name in bt_sources,'Fixed worker source not frozen');expected[name]=bt_sources[name]
    sources=[expected[name] for name in sorted(expected)]
    inputs=br['input_pins'] if kind=='a04' else []
    check(binding['source_pins_before']==binding['source_pins_after']==sources,'Frozen source bindings differ')
    check(binding['input_pins_before']==binding['input_pins_after']==inputs,'Frozen input bindings differ')
    check(result['final_pins_verified_after_export'] and result['final_source_pins_after_export']==sources
          and result['final_input_pins_after_export']==inputs,'Export fence pin bindings')

def review_fixture(z,plan):
    inner=loads(z.read('RESULT.json'));monitor=loads(z.read('FILE_MONITOR.json'))
    check(inner['status']=='PASS' and inner['writer']=='br' and inner['records_per_stream']==45000,'Wrong fixture computation')
    check(monitor['complete'] and not monitor['violations'] and not monitor['monitor_errors'] and monitor['dropped_events']==0,'Fixture monitor did not qualify')
    check(hashlib.sha256(z.read('FILE_MONITOR.json')).hexdigest()==inner['monitor']['sha256'],'Fixture monitor receipt')
    total=0;streams=[]
    for expected in plan['expected_fixture_streams']:
        stream=expected['stream'];h=hashlib.sha256();size=0;n=0
        with z.open('payload/fixture_'+str(stream)+'.jsonl') as source:
            for line in source:
                check(line==fixture_line(stream,n),'Exact fixture record differs')
                h.update(line);size+=len(line);n+=1
        check(n==45000==expected['records'] and size==expected['bytes'] and h.hexdigest()==expected['sha256'],'Prospective fixture byte/hash/count')
        detail=inner['streams'][stream]
        check(detail['status']=='PASS' and detail['writer_receipt']['records']==n,'Fixture writer closure')
        for key,value in [('bytes',size),('sha256',h.hexdigest())]:
            check(detail['expected'][key]==detail['writer_receipt'][key]==value,'Fixture receipt differs')
        check(detail['initial_independent_check']==detail['final_independent_check'],'Fixture changed between inner checks')
        streams.append(dict(stream=stream,records=n,bytes=size,sha256=h.hexdigest()));total+=n
    check(total==90000,'Complete two-stream fixture required')
    return dict(records_verified=total,streams=streams,inotify_available=monitor['inotify_available'],
                monitor_violations=0,status='PASS_ISOLATED_FIXTURE')

def load_scores(identity):
    import numpy as np
    results=[];scores=[]
    for scan in range(6):
        folder=REPO/'work_bp/execution/BP_FIXED24_V1'/identity/'payload'/('scan'+str(scan))
        result=read(folder/'RESULT.json')
        check(result['status']=='PASS' and result['scan_index']==scan,'Invalid saved scan identity')
        check(sha(folder/'arrays.npz')==result['evidence']['arrays.npz']['sha256'],'Saved score archive differs')
        with np.load(folder/'arrays.npz',allow_pickle=False) as z:scores.append({key:z[key] for key in z.files if key.endswith('_score')})
        results.append(result)
    return results,scores

def review_a04(z,plan):
    inner=loads(z.read('ASSESSMENT.json'));closure=loads(z.read('BT_CLOSURE_CHECK.json'))
    check(inner['status']=='PASS' and inner['output_bindings_verified'] and closure['effective_status']=='PASS','A04 computation/closure failed')
    check(inner['child_stream_closure']['effective_status']=='PASS' and inner['child_stream_closure']['verification']==closure['verification'],'A04 closure fences differ')
    check(inner['BP_terminal_status_preserved']=='FAIL' and inner['BP_passed_cases_preserved']==23 and inner['BQ_effective_failure_preserved'],'Historical failures changed')
    for key in ('RNG_calls','new_scan_scores','astronomical_powers_opened','new_archive_requests'):check(inner[key]==0,'Unexpected computation '+key)
    check(sha(REPO/HELPER)==HELPER_SHA,'Independent endpoint helper changed')
    check(any(x['path']==HELPER and x['sha256']==HELPER_SHA for x in plan['source_pins']),'Independent helper not prospectively pinned')
    spec=importlib.util.spec_from_file_location('bt_independent_bp_helper',REPO/HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    scan_results,scores=load_scores('A04');_,baseline=load_scores('N04')
    case=plan['A04_case'];check(case==read(REPO/'work_bp/BP_FIXED24_PLAN.json')['cases'][-1],'A04 case changed')
    methods={};total=truth_count=0
    for method in ('current','legacy'):
        saved=inner['method_results'][method];prediction=plan['expected_A04_streams'][method]
        counts={key:0 for key in STATES};n=size=0;h=hashlib.sha256()
        with z.open(method+'_associations.jsonl') as stream:
            for scan in (0,2,4):
                for candidate in scan_results[scan]['hits'][method]:
                    line=stream.readline();check(line and line.endswith(b'\n'),'A04 truncated record')
                    record=loads(line);expected=helper.independently_force(scores,method,candidate)
                    check(record==expected,'Independent A04 endpoint mismatch')
                    counts[record['status']]+=1;n+=1;size+=len(line);h.update(line)
            check(stream.read(1)==b'','A04 extra association records')
        declared=saved['association_stream']
        check(n==prediction['records']==declared['records']==saved['source_ON_hits'],'A04 association counts')
        check(size==prediction['bytes']==declared['bytes'] and h.hexdigest()==prediction['sha256']==declared['sha256'],'A04 stream predictions')
        check(declared['complete'] and counts==saved['association_counts'] and saved['flags']==counts['PASS']==0,'A04 status/flag counts')
        truth=[];candidates=helper.truth_candidates(case)
        check(len(candidates)==len(saved['truth']),'A04 truth count')
        for candidate,record in zip(candidates,saved['truth']):
            a=helper.independently_force(scores,method,candidate);b=helper.independently_force(baseline,method,candidate)
            expected=dict(injected=a,uninjected=b,recovery_credit=a['flag'] and b['supported'] and not b['flag'])
            check(record==expected,'A04 truth endpoint mismatch');truth.append(expected);truth_count+=1
        recovered=any(t['recovery_credit'] for t in truth)
        off=any(t['injected']['supported'] and t['injected']['OFF_veto'] for t in truth)
        three_fail=bool(truth) and all(t['injected']['supported'] and not t['injected']['three_ON_pass'] for t in truth)
        check(saved['truth_recovered']==recovered and saved['truth_any_supported_OFF_veto']==off
              and saved['truth_all_supported_fail_three_ON']==three_fail,'A04 truth summaries')
        methods[method]=dict(records=n,bytes=size,sha256=h.hexdigest(),association_counts=counts,
                            truth_recovered=recovered,supported_truth_OFF_veto=off,all_truth_supported_three_ON_rejection=three_fail)
        total+=n
    current=methods['current']
    check(current['association_counts']['PASS']==0 and (current['supported_truth_OFF_veto'] or current['all_truth_supported_three_ON_rejection']),'Original A04 gate not satisfied')
    return dict(status='PASS_ISOLATED_A04',records_verified=total,truth_endpoints_recomputed=truth_count,
                methods=methods,independent_helper_sha256=HELPER_SHA,A04_pair_qualified=True,
                prior_complete_stream_hashes_used_as_predictions_only=True)

def audit(kind):
    plan_path=ROOT/'BT_ISOLATED_PLAN.json';plan=read(plan_path);freeze=read(ROOT/'PUBLIC_FREEZE_RECEIPT_BT.json')
    plan_hash=sha(plan_path);check(plan_hash==freeze['plan_sha256'] and freeze['before_execution'] and freeze['exact_readback_verified'],'BT public freeze')
    check(any(x['path']=='work_bt/review/audit_bt.py' and x['sha256']==sha(Path(__file__)) for x in plan['source_pins']),'Auditor source not frozen')
    pins=plan['source_pins']+plan['historical_pins'];pin_checks(pins)
    folder=ROOT/'execution/BT_ISOLATED_V1'/kind;terminal_path=folder/'TERMINAL_BT.json'
    terminal=read(terminal_path);terminal_hash=sha(terminal_path);receipt=read(folder/'ACTUAL_RECEIPT.json');result=read(folder/'payload/RESULT.json')
    check(terminal['status']=='PASS' and terminal['capture_status']=='PASS' and terminal['actual_exit_code']==0,'BT terminal failed')
    check(terminal['kind']==kind and terminal['plan_sha256']==plan_hash and terminal['public_freeze_commit']==freeze['public_commit_sha'],'Terminal plan binding')
    check(terminal['archive_verified'] and terminal['final_inventory_matches_manifests'] and terminal['source_and_input_pins_verified_after'],'Parent verification incomplete')
    files,size=exact_inventory(folder,terminal)
    check(receipt['status']=='PASS' and receipt['actual_exit_code']==0 and receipt['reasons']==[] and receipt['capture_error'] is None,'Actual capture failed')
    for key in ['child_wait_completed','stdout_eof','natural_stdout_eof','stdout_fully_preserved','descendant_cleanup_completed','source_pins_verified_before','source_pins_verified_after','process_namespace_mapping_verified']:
        check(receipt[key] is True,'Missing actual process proof '+key)
    check(not receipt['killed'] and receipt['remaining_live_descendants']==[],'Process cleanup failed')
    log=(folder/'STDOUT.log').read_bytes();check(len(log)==receipt['log_bytes']==receipt['observed_stdout_bytes'],'Stdout byte count')
    check(hashlib.sha256(log).hexdigest()==receipt['log_sha256']==receipt['observed_stdout_sha256'],'Stdout digest')
    result_hash=sha(folder/'payload/RESULT.json');footer=loads(log.splitlines()[-1])
    check(footer==receipt['terminal_stdout_json'] and footer['event']=='GATE_TERMINAL_EOF' and footer['status']=='PASS'
          and footer['result_sha256']==receipt['result_sha256']==result_hash,'Bound terminal result')
    check(result['status']=='PASS' and result['kind']==kind and not result['errors'],'Worker computation failed')
    check(result['execution_identity']=='BT_TMPFS_'+kind.upper()+'_V1','New isolated identity')
    check(result['isolation']['filesystem_type_hex']=='0x01021994' and result['isolation']['exclusive'],'Verified tmpfs isolation absent')
    for key in ['new_RNG_calls','new_scan_scores','astronomical_powers_opened']:check(result[key]==terminal[key]==0,'Unexpected science operation')
    archive_path=folder/'payload/EVIDENCE.zip';checked=archive_members(archive_path,result['archive']['members'])
    check(checked['sha256']==result['archive']['sha256']==terminal['archive_verification']['sha256'] and checked['bytes']==result['archive']['bytes'],'Outer archive bindings')
    expected_names=({'RESULT.json','FILE_MONITOR.json','payload/fixture_0.jsonl','payload/fixture_1.jsonl','BT_SOURCE_INPUT_BINDINGS.json'} if kind=='fixture' else {'ASSESSMENT.json','BT_CLOSURE_CHECK.json','current_associations.jsonl','legacy_associations.jsonl','BT_SOURCE_INPUT_BINDINGS.json'})
    check({x['path'] for x in checked['members']}==expected_names,'Unexpected archived evidence')
    with zipfile.ZipFile(archive_path) as z:
        check_bindings(z,result,plan,kind)
        semantic=review_fixture(z,plan) if kind=='fixture' else review_a04(z,plan)
    if kind=='a04':
        fixture=read(ROOT/'review/FIXTURE_REVIEW_BT.json');gate=terminal['independent_fixture_gate']
        check(fixture['status']=='PASS_ISOLATED_FIXTURE' and fixture['records_verified']==90000 and fixture['plan_sha256']==plan_hash,'Independent prerequisite failed')
        check(gate['sha256']==sha(ROOT/'review/FIXTURE_REVIEW_BT.json'),'Fixture gate changed')
        check(fixture['terminal_sha256']==sha(ROOT/'execution/BT_ISOLATED_V1/fixture/TERMINAL_BT.json')
              and fixture['archive_sha256']==sha(ROOT/'execution/BT_ISOLATED_V1/fixture/payload/EVIDENCE.zip'),'Fixture evidence changed after gate')
    caps=plan['caps'][kind];resources=receipt['resources']
    check(resources['max_child_RSS_bytes']<=caps['rss_bytes'] and resources['peak_tree_RSS_bytes']<=caps['rss_bytes'],'RSS cap')
    check(terminal['wall_seconds_including_parent']<=caps['wall_seconds'] and terminal['cpu_seconds_including_parent']<=caps['cpu_seconds'],'Parent-inclusive time cap')
    check(size+terminal_path.stat().st_size<=caps['stored_bytes'] and terminal['group_stored_bytes_after_parent']<=plan['phase_storage_cap_bytes'],'Storage caps')
    pin_checks(pins);check(sha(terminal_path)==terminal_hash and sha(archive_path)==checked['sha256'],'Evidence changed during review')
    check(exact_inventory(folder,terminal)==(files,size),'Inventory changed during review')
    return dict(schema='SETI_BT_INDEPENDENT_REVIEW_V1',kind=kind,**semantic,
        plan_sha256=plan_hash,terminal_sha256=terminal_hash,archive_sha256=checked['sha256'],
        archive_bytes=checked['bytes'],archive_members=checked['members'],all_member_CRCs_verified=True,
        actual_exit_code=0,exact_wait=True,natural_EOF=True,cleanup_complete=True,
        postterminal_inventory_exact=True,evidence_files_rehashed=files,evidence_bytes_rehashed=size,
        source_pins_verified=len(plan['source_pins']),historical_pins_verified=len(plan['historical_pins']),
        reviewer_source_sha256=sha(Path(__file__)),original_failures_preserved=result['original_statuses_preserved'],
        new_RNG_calls=0,new_scan_scores=0,astronomical_powers_opened=0,
        resources=resources,wall_seconds=time.monotonic()-START,completed_utc=datetime.now(timezone.utc).isoformat(),
        qualification='New isolated identity only; previous BP/BQ/BR/BS failures remain. No full839,DATAadmission,astronomical,FAP or sensitivity qualification.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['fixture','a04'],required=True);args=parser.parse_args()
    out=ROOT/'review'/('FIXTURE_REVIEW_BT.json' if args.kind=='fixture' else 'A04_REVIEW_BT.json')
    if out.exists():raise FileExistsError('Independent review identity already exists')
    try:report=audit(args.kind);code=0
    except BaseException as exc:
        report=dict(schema='SETI_BT_INDEPENDENT_REVIEW_V1',kind=args.kind,status='FAIL_INDEPENDENT_REVIEW',
                    exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
                    wall_seconds=time.monotonic()-START,reviewer_source_sha256=sha(Path(__file__)));code=2
    with out.open('xb') as f:f.write(canonical(report));f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(status=report['status'],path=str(out),sha256=sha(out),records_verified=report.get('records_verified'))),flush=True)
    return code

if __name__=='__main__':sys.exit(main())
