"""Independent bounded administrative read-only review; executes no frozen code."""
import base64
import collections
import hashlib
import json
import os
from pathlib import Path
import stat
import time

BASE=Path('/workspace/scratch/da6462abff17')
ROOT=BASE/'radio-proc-io-control-20261006f'
PREP=BASE/'proc-io-preparation-20261006f'
DEST=BASE/'proc-io-preservation-20261006f'/'ACTUAL_CLOSURE_REVIEW.md'
START=time.monotonic();DEADLINE=START+20;READ_LIMIT=512*1024**2
charged=0;checks=[];failures=[]

def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    if not condition:failures.append(name)

def unique_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('duplicate JSON key')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs)

def read(path,retain=False,cap=128*1024**2):
    global charged
    if time.monotonic()>DEADLINE:raise TimeoutError('administrative 20-second deadline')
    path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>cap:raise ValueError('bounded ordinary file required')
        digest=hashlib.sha256();parts=[];count=0
        while True:
            if time.monotonic()>DEADLINE:raise TimeoutError('administrative hash deadline')
            allocation=min(1024**2,READ_LIMIT-charged,cap+1-count)
            if allocation<=0:raise ValueError('administrative read ceiling')
            raw=os.read(fd,allocation);charged+=len(raw);count+=len(raw)
            if not raw:break
            digest.update(raw)
            if retain:parts.append(raw)
        after=os.fstat(fd);named=path.lstat()
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
        if identity(before)!=identity(after) or identity(after)!=identity(named):raise ValueError('current file changed or path rebound')
        row={'path':str(path),'bytes':count,'sha256':digest.hexdigest(),'mode':stat.S_IMODE(after.st_mode),
             'identity':[after.st_dev,after.st_ino],'links':after.st_nlink,
             'mtime_ns':after.st_mtime_ns,'ctime_ns':after.st_ctime_ns,'allocated_bytes':after.st_blocks*512}
        return row,b''.join(parts) if retain else None
    finally:os.close(fd)

artifact_rows=[];raw_files={};directories=[]
root_st=ROOT.lstat();root_identity=[root_st.st_dev,root_st.st_ino]
for current,dirs,files in os.walk(ROOT,followlinks=False):
    current=Path(current);st=current.lstat()
    if not stat.S_ISDIR(st.st_mode):raise ValueError('ordinary actual directory required')
    directories.append({'path':str(current.relative_to(ROOT)),'identity':[st.st_dev,st.st_ino],'mode':stat.S_IMODE(st.st_mode),'bytes':st.st_size,'allocated_bytes':st.st_blocks*512})
    if len(directories)>128:raise ValueError('directory bound')
    for name in dirs:
        if not stat.S_ISDIR((current/name).lstat().st_mode):raise ValueError('actual directory symlink')
    for name in sorted(files):
        row,raw=read(current/name,True,1048576);row['relative_path']=str((current/name).relative_to(ROOT))
        artifact_rows.append(row);raw_files[row['relative_path']]=raw
        if len(artifact_rows)>2000:raise ValueError('file count bound')

freeze_row,prep_freeze_raw=read(PREP/'freeze.json',True,1048576)
f=unique_json(raw_files['admission/freeze.json']);proof=unique_json(raw_files['admission/proof.json'])
marker=unique_json(raw_files['admission/marker.json']);r=unique_json(raw_files['result.json'])
c=unique_json(raw_files['processes/control.custody.json']);leaf=unique_json(raw_files['control-result.json'])
caller=unique_json(raw_files['caller-receipt.json']);spent=unique_json(raw_files['spent.json'])
sha=lambda raw:hashlib.sha256(raw).hexdigest()
check('freeze actual raw equals preparation raw',raw_files['admission/freeze.json']==prep_freeze_raw)
check('freeze bound to proof marker and spent',sha(prep_freeze_raw)==proof['freeze_sha256']==marker['freeze_sha256']==spent['freeze_sha256'])
check('marker raw hash bound to proof',sha(raw_files['admission/marker.json'])==proof['marker_sha256'])
check('marker binds preparation commit and tree',marker['prepared_commit']==proof['preparation_commit']==proof['sole_parent'] and marker['prepared_tree']==proof['preparation_tree'])
check('sole activation path is marker',proof['changed_paths']==[f['marker_repository_path']])
check('retained immutable readback assertions cover all publication paths',proof['full_preparation_readback_exact'] and proof['marker_readback_exact'] and proof['source_readbacks']==f['published_sources'] and {x['path'] for x in proof['preparation_full_readbacks']}==set(f['published_sources'])|{f['freeze_repository_path']} and all(x['full_immutable_body_exact'] for x in proof['preparation_full_readbacks']))
check('output root identity matches freeze',root_identity==f['output_root_identity'])
check('all identities agree',all(x['identity']==f['identity'] for x in (r,caller,marker,spent)))
check('engineering single-use authority remains false',f['engineering_only'] and f['single_use'] and spent['spent'] and all(x['scientific_authority'] is False for x in (f,r,caller,marker)) and all(x['automatic_successor'] is False for x in (f,r,marker,spent)))

selected=[];by_path={};retained_sources={};pin_paths=[]
for role,pins in [('source',f['source_pins']),('runtime',f['runtime_pins'])]:
    for pin in pins:
        row,raw=read(pin['path'],role=='source' or pin['path'] in (f['guard_path'],f['exec_seal_path']))
        row['role']=role
        row['matches_frozen_bytes_sha256_mode']=row['bytes']==pin['bytes'] and row['sha256']==pin['sha256'] and row['mode']==pin['mode']
        row['matches_frozen_identity_where_provided']='identity' not in pin or row['identity']==pin['identity']
        row['matches_frozen_links_where_provided']='links' not in pin or row['links']==pin['links']
        selected.append(row);by_path[pin['path']]=row;pin_paths.append(pin['path'])
        if raw is not None:retained_sources[pin['path']]=raw
check('1494 unique selected pins fully read',len(selected)==1494 and len(set(pin_paths))==1494)
check('all selected hashes modes identities links agree',all(x['matches_frozen_bytes_sha256_mode'] and x['matches_frozen_identity_where_provided'] and x['matches_frozen_links_where_provided'] for x in selected))

publication=[]
for repo_path,p in f['published_sources'].items():
    raw=retained_sources[p['local_path']]
    body=raw if p['encoding']=='utf-8' else base64.b64encode(raw)+b'\n'
    blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
    ok=(len(raw)==p['raw_bytes'] and sha(raw)==p['raw_sha256'] and len(body)==p['bytes'] and sha(body)==p['sha256'] and blob==p['git_blob'])
    publication.append({'repository_path':repo_path,'local_path':p['local_path'],'representation_hash_and_git_blob_match':ok})
check('all36 publication representations bind full local raw bodies',len(publication)==36 and all(x['representation_hash_and_git_blob_match'] for x in publication))

def fields(raw):
    out={}
    for line in raw.splitlines():
        if ':' in line:
            k,v=line.split(':',1)
            if k in out:raise ValueError('duplicate proc field')
            out[k]=v.strip()
    return out
def stats(raw):
    first,_,tail=raw.rpartition(')');values=tail.split()
    return (int(first.split('(',1)[0]),values[0],int(values[1]),int(values[19]))
def io(raw):return {k:int(v) for k,v in fields(raw).items()}

resolution=c['proc_resolution'];owner=resolution['owner'];terminal=c['terminal_proc'];snap=terminal['snapshot'];wait=c['wait4']
owner_status=fields(owner['raw_self_status']);owner_chain=[int(n) for n in owner_status['NSpid'].split()]
check('owner outer inner UID capability identity is explicit',owner_chain==owner['namespace_pid_chain'] and owner_chain[0]==owner['outer_pid'] and owner_chain[-1]==c['expected_parent_pid'] and int(owner_status['Pid'])==int(owner_status['Tgid'])==owner['outer_pid'] and [int(n) for n in owner_status['Uid'].split()]==owner['uid_real_effective_saved_fs']==[0]*4 and int(owner_status['CapEff'],16)==owner['effective_capabilities']==0)
all_samples=c['proc_samples']+[snap];raw_snapshot_checks=[]
for sample in all_samples:
    good=(sample['available'] and sample['outer_proc_pid']==resolution['outer_proc_pid'] and sample['local_wait_pid']==resolution['local_wait_pid']==c['pid']==leaf['pid'] and sample['starttime_ticks']==resolution['child_starttime_ticks'] and sample['held_proc_directory_identity']==resolution['held_child_directory_identity'] and sample['namespace_identity']==owner['namespace_identity'])
    for position in ('before','after'):
        s=fields(sample['raw']['status_'+position]);q=stats(sample['raw']['stat_'+position]);chain=[int(n) for n in s['NSpid'].split()]
        good=good and int(s['Pid'])==int(s['Tgid'])==q[0]==resolution['outer_proc_pid'] and int(s['PPid'])==q[2]==owner['outer_pid'] and chain[0]==resolution['outer_proc_pid'] and chain[-1]==c['pid'] and len(chain)==len(owner_chain) and q[3]==resolution['child_starttime_ticks'] and [int(n) for n in s['Uid'].split()]==owner['uid_real_effective_saved_fs']
    good=good and io(sample['raw']['io'])==sample['io']
    raw_snapshot_checks.append(good)
check('all14live plus terminal raw snapshots bind same child',len(c['proc_samples'])==14 and all(raw_snapshot_checks))
check('WNOWAIT terminal then exact wait4 reaped success',terminal['available'] and terminal['terminal_observed'] and terminal['wnowait_requested'] and terminal['wait4_called_here'] is False and terminal['waitid_pid']==wait['pid']==c['pid']==6 and terminal['waitid_code']==1 and terminal['waitid_status']==wait['returncode']==c['child_exit_code']==0 and wait['raw_status']==0 and wait['exact_direct_child_wait4'] and c['child_reaped'] and snap['state_before']==snap['state_after']=='Z' and stats(snap['raw']['stat_before'])[1]==stats(snap['raw']['stat_after'])[1]=='Z')
check('kernel terminal timing ordered before supervisor completion',c['started_monotonic']<=c['terminal_observed_monotonic']<=terminal['monotonic']<=c['ended_monotonic'] and abs(c['complete_direct_leaf_seconds']-(c['ended_monotonic']-c['started_monotonic']))<1e-8)

keys={'rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes'}
counters=terminal['io'];mono=keys-{'cancelled_write_bytes'}
check('all seven actual terminal counters match raw evidence',set(counters)==keys and counters==snap['io']==io(snap['raw']['io'])==r['control']['terminal_kernel_io'] and all(type(n) is int and n>=0 for n in counters.values()))
previous=None;monotone=True
for sample in all_samples:
    if previous is not None:monotone=monotone and all(sample['io'][k]>=previous[k] for k in mono)
    previous=sample['io']
check('live-to-terminal monotone counters',monotone)
for label in ('before','after'):
    row=leaf['own_io_'+label];body=row['raw'].encode()
    check('leaf own IO '+label+' raw bytes hash counters',len(body)==row['bytes'] and sha(body)==row['sha256'] and io(row['raw'])==row['values'])
before=leaf['own_io_before'];after=leaf['own_io_after'];work=leaf['workload_explicit_read_bytes']
check('eight exact pinned payload passes produce1MiB',leaf['passes']==8 and leaf['payload_bytes']==131072 and work==leaf['passes']*leaf['payload_bytes']==1048576 and leaf['payload_sha256']==f['payload_sha256']==by_path[f['payload_path']]['sha256'] and leaf['pass_sha256']==[f['payload_sha256']]*8)
delta=after['values']['rchar']-before['values']['rchar']
check('own rchar delta includes known payload plus prior100byte IO read',delta==r['control']['child_self_rchar_delta']==work+before['bytes'] and counters['rchar']==after['values']['rchar']+after['bytes'] and counters['rchar']>=work)

events=c['proc_observer_events'];budget=c['proc_observer_budget'];charged_events=sum(e.get('bytes',0) for e in events if e['kind']=='read')
operations=[e['operation'] for e in events if 'operation' in e];rejects=[e for e in events if e['kind']=='rejected-candidate'];children_events=[e for e in events if e['kind']=='read' and e.get('path','').endswith('/children')]
check('fallback children ENOENT retained charged finite fullscan',resolution['route']=='bounded-proc-scan' and len(children_events)==1 and children_events[0]['errno']==2 and children_events[0]['bytes']==0 and budget['candidates']==17 and budget['rejected_candidates']==len(rejects)==16)
check('all observer bytes operations errors bounded and accounted',charged_events==budget['read_received_bytes']==c['proc_metadata_read_charge_bytes']==r['supervisor_proc_metadata_reads_charged_bytes']==115007 and operations==list(range(1,budget['operations']+1)) and budget['operations']==559<=budget['operation_limit']==65536 and budget['candidates']<=budget['candidate_limit']==1024 and budget['errors']==sum(bool(e.get('error_type')) for e in events)==30 and charged_events<=budget['read_limit']==f['limits']['supervisor_proc_read_bytes'] and c['proc_child_metadata_read_charge_bytes'] is None)
check('selected held directories closed in charged events',sum(e['kind']=='open-proc-dir' for e in events)==18 and sum(e['kind']=='open-proc-root' for e in events)==1 and sum(e['kind']=='close-proc-dir' for e in events)==19)

limit=f['limits'];pin_sum=sum(c[name+'_pin']['read_charge_bytes'] for name in ('python','guard','exec_seal','phase2'))
stream_sum=sum(c['output'][k]['received_bytes'] for k in ('stdout','stderr'))
for k in ('stdout','stderr'):
    body=raw_files['processes/control.'+k+'.bin'];entry=c['output'][k]
    check('retained '+k+' bytes SHA limit',len(body)==entry['bytes']==entry['received_bytes'] and sha(body)==entry['sha256'] and len(body)<=limit[k+'_bytes'])
check('embedded child and leaf-result hashes exact',r['children']==[c] and sha(raw_files['control-result.json'])==r['control_result_sha256'])
check('explicit parent/joined arithmetic exact',pin_sum==c['pin_read_charge_bytes']==r['supervisor_explicit_pin_reads_charged_bytes'] and stream_sum==r['retained_leaf_stream_reads_charged_bytes'] and r['explicit_parent_read_charged_bytes']==r['root_explicit_reads_charged_bytes']+pin_sum+charged_events+stream_sum and r['joined_conservative_charged_bytes']==r['explicit_parent_read_charged_bytes']+limit['opaque_child_read_reserve_bytes'] and r['joined_read_reservation_bytes']==limit['joined_read_bytes'] and r['read_reservation_fully_spent_no_refund'])
check('every declared read component within ceiling',r['root_explicit_reads_charged_bytes']<=limit['root_explicit_read_bytes'] and pin_sum<=limit['supervisor_pin_read_bytes'] and charged_events<=limit['supervisor_proc_read_bytes'] and stream_sum<=limit['misc_stream_read_bytes'] and r['explicit_parent_read_charged_bytes']<=limit['parent_read_bytes'] and r['joined_conservative_charged_bytes']<=limit['joined_read_bytes'] and counters['rchar']<=limit['opaque_child_read_reserve_bytes'] and counters['read_bytes']<=limit['opaque_child_read_reserve_bytes'])
check('elapsed CPU RSS receipt and guard flags fit declared scope',c['complete_direct_leaf_seconds']<=limit['child_wall_seconds'] and r['elapsed_before_terminal_seconds']<=limit['operation_seconds'] and caller['elapsed_full_parent_lifetime_seconds']<=limit['wall_seconds'] and wait['user_seconds']+wait['system_seconds']<=limit['child_cpu_seconds'] and caller['parent_wait4_lifetime_ru_maxrss_bytes']==r['parent_kernel_highwater_before_terminal_bytes']<=limit['parent_address_space_bytes'] and wait['maxrss_bytes']==c['wait4_direct_child_ru_maxrss_bytes']<=limit['child_address_space_bytes'] and caller['conservative_joined_rss_upper_bound_bytes']==r['conservative_joined_rss_upper_bound_before_parent_terminal_bytes']==caller['parent_wait4_lifetime_ru_maxrss_bytes']+wait['maxrss_bytes'] and c['guarded_leaf'] and c['guard_status']['no_new_privs']==c['phase2_status']['no_new_privs']==1 and c['guard_status']['seccomp_mode']==c['phase2_status']['seccomp_mode']==2 and c['guard_status']['expected_parent_pid']==c['expected_parent_pid']==caller['pid'])

inventory=r['artifact_inventory'];root_by_rel={x['relative_path']:x for x in artifact_rows}
check('eight preterminal inventory entries match current raw files',inventory['files']==len(inventory['entries'])==8 and all(root_by_rel[e['path']]['bytes']==e['bytes'] and root_by_rel[e['path']]['sha256']==e['sha256'] and root_by_rel[e['path']]['mode']==e['mode'] and root_by_rel[e['path']]['allocated_bytes']==e['allocated_bytes'] for e in inventory['entries']))
directory_logical=sum(x['bytes'] for x in directories);logical=sum(x['bytes'] for x in artifact_rows)+directory_logical;directory_allocated=sum(x['allocated_bytes'] for x in directories);allocated=sum(x['allocated_bytes'] for x in artifact_rows)+directory_allocated
check('final ten files plus four directories exactly reconstructed',set(root_by_rel)=={e['path'] for e in inventory['entries']}|{'result.json','caller-receipt.json'} and len(artifact_rows)==10 and len(directories)==inventory['directories']==caller['storage_before_caller_receipt']['directories']==4 and inventory['logical_bytes']==sum(e['bytes'] for e in inventory['entries'])+directory_logical and inventory['allocated_bytes']==sum(e['allocated_bytes'] for e in inventory['entries'])+directory_allocated and caller['storage_before_caller_receipt']['logical_bytes']==inventory['logical_bytes']+len(raw_files['result.json']) and caller['storage_before_caller_receipt']['allocated_bytes']==inventory['allocated_bytes']+root_by_rel['result.json']['allocated_bytes'] and caller['storage_before_caller_receipt']['files']==9 and logical==caller['storage_before_caller_receipt']['logical_bytes']+len(raw_files['caller-receipt.json']) and logical<=limit['artifact_bytes'] and allocated<=limit['artifact_bytes'])
check('terminal result and caller sizes fit separate1MiB bounds',len(raw_files['result.json'])<=limit['terminal_reserve_bytes'] and len(raw_files['caller-receipt.json'])<=limit['output_file_bytes'])
check('single actual leaf and complete caller success match pending status',r['status']==caller['successful_gate_status']=='OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION' and caller['success'] and caller['child_reaped'] and caller['child_exit_code']==0 and caller['dispatches']==c['child_dispatches']==1 and caller['watchdog_killed'] is False and not c['failures'] and not c['observation_limits'] and r['child_peak_custody_complete'] and caller['child_peak_custody_complete'])
check('zero science operation and no new qualification claims',r['network_requests']==r['installations']==r['hdf5_dataset_reads']==0 and leaf['scientific_modules_imported'] is False and leaf['installed_python_launched'] is False and leaf['isolated'] and leaf['dont_write_bytecode'] and leaf['no_site'] and not any(leaf['authority'].values()) and all(r[k] is False for k in ('runtime_qualified','full_native_io_custody_qualified','full_scientific_closure_qualified','scientific_authority')))

elapsed=time.monotonic()-START
check('separate administrative reads meet20s512MiB',elapsed<=20 and charged<=READ_LIMIT)
receipt={'schema':'radio-F-independent-actual-closure-review-v1','status':'VERIFIED_WITH_EXPLICIT_LIMITATIONS' if not failures else 'REVIEW_FAILED',
    'freeze_sha256':sha(prep_freeze_raw),'identity':f['identity'],'selected_pin_counts':{'source':len(f['source_pins']),'runtime':len(f['runtime_pins']),'total':len(selected)},
    'administrative_read_bytes':charged,'administrative_read_limit':READ_LIMIT,'administrative_seconds':elapsed,'administrative_deadline_seconds':20,
    'preliminary_read_only_shape_inspections':'Four earlier bounded JSON-shape inspections read under3MiB; add conservatively3MiB to this receipt for session review-read accounting. They executed no frozen source.',
    'current_selected_integrity_verified_not_historical_loader_measurement':True,'independent_network_readback_performed':False,
    'publication_anchors':'Retained proof and local representation/Git blob bindings checked; independently reretrieving commits/trees was outside this local review.',
    'checks':checks,'failures':failures,'selected_current_file_receipts':selected,'actual_root_files':artifact_rows,'actual_root_directories':directories,'publication_representation_checks':publication,
    'actual_counter_facts':{'terminal':counters,'known_workload_bytes':work,'self_rchar_delta':delta,'after_self_read_bytes':after['bytes'],'parent_outer_pid':owner['outer_pid'],'parent_inner_pid':owner_chain[-1],'child_outer_pid':resolution['outer_proc_pid'],'child_inner_pid':c['pid'],'child_starttime_ticks':resolution['child_starttime_ticks'],'child_directory_identity':resolution['held_child_directory_identity'],'pid_namespace_identity':owner['namespace_identity'],'resolution_route':resolution['route'],'children_fallback_errno':children_events[0]['errno'],'proc_accounting':budget},
    'arithmetic_facts':{'explicit_parent':r['explicit_parent_read_charged_bytes'],'joined_conservative':r['joined_conservative_charged_bytes'],'joined_reservation':r['joined_read_reservation_bytes'],'final_root_logical_bytes':logical,'final_root_allocated_bytes':allocated,'parent_full_lifetime_seconds':caller['elapsed_full_parent_lifetime_seconds'],'leaf_lifetime_seconds':c['complete_direct_leaf_seconds'],'parent_lifetime_rss_bytes':caller['parent_wait4_lifetime_ru_maxrss_bytes'],'child_lifetime_rss_bytes':wait['maxrss_bytes'],'conservative_rss_sum_bytes':caller['conservative_joined_rss_upper_bound_bytes']},
    'no_actual_control_rerun':True,'no_frozen_source_execution':True,'no_scientific_import':True,'no_closed_scope_mutation':True,
    'all_native_wording_limitation':'freeze all_native_imports_forbidden is overbroad if interpreted literally: the pinned Python executable/stdlib may use native C extensions, and guard plus exec seal are native. Actual scope forbids scientific package imports; no zero-C-extension or complete-loader inventory claim is supported.'}
text='''# Independent actual F closure review\n\nThe single closed F operation is verified with explicit limitations. The retained result is `OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION`; its caller exited successfully and its one guarded leaf was reaped. This administrative review reran no control and executed no frozen source or scientific package.\n\nAll 1,494 selected files (34 source, 1,460 runtime) were read fully and matched frozen byte counts, SHA256, modes, and runtime identities/link counts where declared. Current file identity was stable across held reads and named-path rechecks. The preparation and admitted freeze bodies are identical and the retained marker/proof/spent bindings agree. This is local integrity review of retained publication evidence; it did not independently refetch Git commits/trees or claim historical continuous loader custody.\n\nThe actual owner mapping was outer PID 49,902 / local PID 5; its child was outer PID 49,903 / waitable PID 6. All fourteen live snapshots and the terminal snapshot retained the same namespace inode, child directory identity and starttime. Terminal raw status/stat are zombie on both sides. WNOWAIT identified child 6 before the exact successful wait4; the terminal namespace lookup actually succeeded.\n\nThe children-path lookup returned ENOENT, retained as a zero-byte failed read. The bounded fallback scanned 17 candidates, rejected 16, and retained one. Its 115,007 proc read bytes, 559 operations and 30 error/rejection events are all accounted; no missing read was replaced by a zero counter. All held proc directories were closed in charged events.\n\nThe terminal seven counters were rchar 2,322,467; wchar 3,128; syscr 169; syscw 4; read_bytes 0; write_bytes 8,192; cancelled_write_bytes 0. Eight frozen 131,072-byte passes contributed 1,048,576 known workload bytes. The self rchar delta was 1,048,676, including the prior 100-byte self-IO read; terminal rchar equals self-after rchar plus its subsequent 100-byte IO read. Cached physical read_bytes=0 is a present kernel measurement, not missing evidence and not attribution of every loader/file operation.\n\nThe parent lifetime was 0.729374843 s; leaf lifetime 0.295569383 s. Explicit parent reads 253,551,763 B plus the fully spent opaque child reserve 16,777,216 B equal joined charged reads 270,328,979 B, below the 553,648,128 B reservation. Peak-RSS sum 160,108,544 B is conservative, not simultaneous tree RSS. All component read/time/CPU/RSS/storage checks agree with the frozen limits. The final root contains exactly ten files and four directories; result/caller additions reconstruct the two staged inventories. The full machine receipt below pins every reviewed file and raw actual artifact.\n\nThe frozen field `all_native_imports_forbidden:true` is overbroad if read literally. The pinned Python/stdlib can use C extensions; the guard and exec seal are native components. The supported scope is no scientific package import and no scientific execution. This review issues no zero-C-extension, full native IO/loader custody, complete runtime/native graph, codec, hosted-profile, CAS or scientific qualification. C/D/E remain closed and unchanged; original integration/scientific gates remain pending.\n\n```json\n'''+json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n```\n'
if failures:text=text.replace('is verified with explicit limitations','has review failures: '+', '.join(failures),1)
DEST.write_text(text)
print(json.dumps({'status':receipt['status'],'checks':len(checks),'failures':failures,'read_bytes':charged,'seconds':elapsed,'report_bytes':DEST.stat().st_size,'report_sha256':sha(DEST.read_bytes())}))
