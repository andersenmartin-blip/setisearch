"""Independent administrative read-only G closure checks; base stdlib only.

Never imports or executes frozen G sources, installed/native packages, HDF5,
normalizers, producers, detector code, scientific cases or a child process.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import time

WORK = Path('/workspace/scratch/22a9db7a6f52')
G = WORK/'codec16-G'
A = G/'admission'
R = WORK/'radio-codec16-control-20261006g'
START = time.monotonic()
READS = 0
CHECKS = {}
CHECK_DIGEST = hashlib.sha256()
LIMIT = 2*1024**3


def check(name, condition):
    category=name.split(' /',1)[0]
    CHECKS[category]=CHECKS.get(category,0)+1
    CHECK_DIGEST.update((name+':'+str(bool(condition))+'\n').encode())
    if not condition:
        raise ValueError(name)


def metadata(st):
    return dict(bytes=st.st_size, mode=st.st_mode, device=st.st_dev,
                inode=st.st_ino, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)


def read(path, expected=None, keep=True):
    global READS
    path=Path(path)
    check('canonical ordinary read '+str(path), path.is_absolute() and path.resolve()==path)
    fd=os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        check('regular input '+str(path),stat.S_ISREG(before.st_mode))
        if expected is not None:
            check('expected metadata '+str(path),metadata(before)=={k:expected[k] for k in metadata(before)})
        check('administrative read bound',READS+before.st_size<=LIMIT)
        digest=hashlib.sha256(); parts=[]; total=0
        while True:
            if time.monotonic()-START>60:raise TimeoutError('administrative review deadline')
            chunk=os.read(fd,1024**2)
            if not chunk:break
            total+=len(chunk);READS+=len(chunk);digest.update(chunk)
            if keep:parts.append(chunk)
        check('held and named stable '+str(path),metadata(before)==metadata(os.fstat(fd))==metadata(path.lstat()) and total==before.st_size)
        if expected is not None:check('full sha256 '+str(path),digest.hexdigest()==expected['sha256'])
        return (b''.join(parts) if keep else None),dict(path=str(path),bytes=total,sha256=digest.hexdigest())
    finally:
        os.close(fd)


def parse(raw):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def doc(path):
    raw,pin=read(path)
    return parse(raw),pin


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def inventory(root,excluded=()):
    out=[]
    for path in (root,*root.rglob('*')):
        if path in excluded:continue
        st=path.lstat()
        check('ordinary storage entry '+str(path),stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode))
        out.append(dict(path=str(path),bytes=st.st_size,allocated_bytes=st.st_blocks*512,
                        mode=st.st_mode,identity=[st.st_dev,st.st_ino]))
    return out


def status(raw):
    return {k:v.strip() for line in raw.splitlines() if ':' in line for k,v in [line.split(':',1)]}


def procstat(raw):
    rest=raw[raw.rfind(')')+2:].split()
    return dict(pid=int(raw.split(' ',1)[0]),state=rest[0],ppid=int(rest[1]),start=int(rest[19]))


def main():
    cfg,cp=doc(A/'config.json');proof,pp=doc(A/'preread-proof.json')
    outer,op=doc(R/'outer-result.json');leaf,lp=doc(R/'leaf.custody.json')
    caller,cap=doc(A/'caller-receipt.json');args,argp=doc(A/'launcher-arguments.json')
    receipt,rp=doc(R/'controlled/codec16-receipt.json');spent,sp=doc(A/'spent.json')
    pub,pubp=doc(A/'publication-proof.json');index,ip=doc(A/'publication-index.json')
    roles=cfg['roles'];pins=cfg['pinned_files'];bud=cfg['budgets']
    check('one successful whole gate caller',caller['one_gate_dispatch'] is True and caller['exit_code']==0 and caller['exact_wait4'] is True and caller['parent_reaped'] is True and caller['expected_gate_pid']==caller['waited_pid']==caller['wnowait_pid'] and caller['loop_failure'] is None and not caller['watchdog_kill'] and not caller['caller_stream_ceiling_exceeded'] and caller['elapsed_complete_gate_seconds']<=bud['parent_wall_seconds'])
    check('config proof caller bindings',outer['config_sha256']==cp['sha256']==proof['config_sha256']==caller['config_sha256']==args['config']['sha256'] and outer['preread_proof_sha256']==pp['sha256']==args['preread_proof']['sha256'] and caller['publication_proof_sha256']==pubp['sha256']==args['publication_proof']['sha256'])
    manifest_sha=hashlib.sha256(canonical(pins)).hexdigest()
    check('full preread exact manifest',proof['readback']==pins and proof['all_reads_complete'] is True and proof['read_bytes']==sum(p['bytes'] for p in pins) and proof['pinned_files_sha256']==manifest_sha)
    check('all2638 sorted unique pins',len(pins)==2638 and pins==sorted(pins,key=lambda p:p['path']) and len({p['path'] for p in pins})==2638)
    for root in map(Path,cfg['inventory_roots']):
        observed=set()
        for p in root.rglob('*'):
            st=p.lstat();check('ordinary inventory '+str(p),stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode))
            if stat.S_ISREG(st.st_mode):observed.add(str(p))
        check('complete inventory path set '+str(root),observed=={p['path'] for p in pins if Path(p['path']).is_relative_to(root)})
    rehashed=sum(p['bytes'] for p in pins)
    for p in pins:read(p['path'],p,keep=False)
    check('prepost full selected manifest',outer['complete_manifest_snapshots']==[dict(phase=phase,complete=True,files=len(pins),bytes_read=rehashed,manifest_sha256=manifest_sha) for phase in ('PRE','POST')])
    check('spent marker binds exact preread',spent['config_sha256']==cp['sha256'] and spent['preread_proof_sha256']==pp['sha256'] and spent['pre_snapshot']==outer['complete_manifest_snapshots'][0] and spent['scope_id']==outer['scope_id']==cfg['scope_id'] and spent['scientific_authority'] is False)
    check('one guarded reaped installed child',leaf['status']=='GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY' and leaf['child_dispatches']==outer['child_dispatches']==1 and leaf['child_reaped'] is True and leaf['guarded_leaf'] is True and leaf['child_exit_code']==0 and leaf['failures']==[] and leaf['guard_status']['descendants_denied'] is True and leaf['phase2_status']['exec_denied'] is True)
    terminal=leaf['terminal_proc'];resolution=leaf['proc_resolution'];wait=leaf['wait4'];snap=terminal['snapshot']
    check('wnowait before exact child wait4',terminal['available'] is True and terminal['terminal_observed'] is True and terminal['wnowait_requested'] is True and terminal['wait4_called_here'] is False and terminal['waitid_pid']==leaf['pid']==wait['pid']==resolution['local_wait_pid']==6 and terminal['waitid_code']==1 and terminal['waitid_status']==0 and wait['returncode']==0 and wait['exact_direct_child_wait4'] is True and terminal['monotonic']<leaf['ended_monotonic'])
    all_samples=leaf['proc_samples']+[snap]
    for sample in all_samples:
        check('sample child identity',sample['local_wait_pid']==6 and sample['outer_proc_pid']==resolution['outer_proc_pid'] and sample['starttime_ticks']==resolution['child_starttime_ticks'] and sample['held_proc_directory_identity']==resolution['held_child_directory_identity'] and sample['namespace_identity']==resolution['owner']['namespace_identity'])
        for side in ('before','after'):
            s=status(sample['raw']['status_'+side]);t=procstat(sample['raw']['stat_'+side])
            check('raw namespace and stat binding',list(map(int,s['NSpid'].split()))==[resolution['outer_proc_pid'],6] and int(s['PPid'])==resolution['owner']['outer_pid'] and t['pid']==resolution['outer_proc_pid'] and t['ppid']==resolution['owner']['outer_pid'] and t['start']==resolution['child_starttime_ticks'])
        io={k:int(v) for k,v in status(sample['raw']['io']).items()}
        check('all seven raw exact IO counters',io==sample['io'] and len(io)==7 and all(type(v) is int and v>=0 for v in io.values()))
    check('terminal zombie both sides',procstat(snap['raw']['stat_before'])['state']==procstat(snap['raw']['stat_after'])['state']=='Z' and terminal['io']==snap['io'])
    proc_bytes=sum(e.get('bytes',0) for e in leaf['proc_observer_events'] if e['kind']=='read')
    check('proc exact received byte sum',proc_bytes==leaf['proc_metadata_read_charge_bytes']==leaf['proc_observer_budget']['read_received_bytes'])
    check('bounded fallback retained',resolution['route']=='bounded-proc-scan' and leaf['proc_observer_budget']['candidates']==17 and leaf['proc_observer_budget']['rejected_candidates']==16 and leaf['proc_observer_budget']['operations']<=leaf['proc_observer_budget']['operation_limit'] and proc_bytes<=bud['proc_metadata_read_bytes'])
    for channel,info in leaf['output'].items():
        raw,p=read(info['path']);check('retained '+channel+' hash',p['bytes']==info['bytes'] and p['sha256']==info['sha256'] and info['bytes']<=info['received_bytes']<=bud['stream_each_bytes'])
    check('compact outer links exact custody',outer['supervisor_result']['raw_custody_pin']==lp and outer['supervisor_result']['raw_proc_live_samples_count']==len(leaf['proc_samples']) and outer['supervisor_result']['terminal_proc']==terminal)
    plan,_=doc(roles['plan']);dispatch,dp=doc(roles['dispatch']);scope,scopep=doc(roles['scope'])
    check('partial codec receipt identity',outer['status']=='CONTROLLED_CODEC16_PARTIAL_HANDOFF_OBSERVED' and outer['controlled_codec_receipt']['bytes']==rp['bytes'] and outer['controlled_codec_receipt']['sha256']==rp['sha256'] and receipt['status']=='OBSERVED_ENGINEERING_ONLY' and receipt['rows'] and [row['row'] for row in receipt['rows']]==list(range(16)) and receipt['handoffs_observed']==1 and receipt['complete_codec_handoffs_required']==12)
    check('leaf runtime dispatch scope metadata',receipt['scope']==plan['scope'] and receipt['runtime']==plan['runtime_basis']['versions'] and receipt['dispatch_sha256']==dp['sha256'] and receipt['outer_supervisor_scope_sha256']==scopep['sha256'] and receipt['receiver_context_sha256']==plan['scope']['receiver_context_sha256'] and receipt['receiver_bank_sha256']==plan['scope']['receiver_bank_sha256'])
    check('raw convention handoff rows',receipt['handoff']['raw_row_sha256s']==[row['native_descending_sha256'] for row in receipt['rows']] and receipt['handoff']['normalized_row_sha256s']==[row['normalized_sha256'] for row in receipt['rows']] and all(row['retained_legacy_compressed_bytes_verified'] is True and row['selected_cells']==65536 for row in receipt['rows']))
    hdfpins=[]
    for info in receipt['hdf5_files']:
        _,p=read(R/'controlled'/info['name'],keep=False);hdfpins.append(p)
        check('whole HDF file stable sha',p['bytes']==info['bytes'] and p['sha256']==info['sha256'] and p['bytes']<=bud['file_bytes'])
    stream_reads=sum(v['received_bytes'] for v in leaf['output'].values())
    components=dict(config=cp['bytes'],preread=pp['bytes'],prepost=2*rehashed,supervisor_pins=leaf['pin_read_charge_bytes'],proc=proc_bytes,streams=stream_reads,guard_reserved=4096,custody_reread=lp['bytes'],receipt=rp['bytes'],hdf_outputs=sum(p['bytes'] for p in hdfpins))
    check('exact explicit parent read arithmetic',sum(components.values())==outer['parent_explicit_read_charge_bytes']<=bud['parent_read_bytes'])
    check('child reservation unchanged bounded',outer['opaque_child_read_reservation_bytes']==leaf['opaque_child_read_reserve_bytes']==bud['child_read_reserve_bytes'])
    check('actual time cpu rss within child bound',leaf['complete_direct_leaf_seconds']<=bud['child_wall_seconds'] and wait['user_seconds']+wait['system_seconds']<=bud['child_cpu_seconds'] and 0<wait['maxrss_bytes']<=bud['child_address_space_bytes'])
    before=inventory(R,excluded=(R/'outer-result.json',));final=inventory(R)
    def sums(entries):return sum(x['bytes'] for x in entries),sum(x['allocated_bytes'] for x in entries)
    marker=inventory(A/'spent.json')
    before_log,before_alloc=sums(before+marker);final_log,final_alloc=sums(final+marker)
    check('preouter storage inventory exact',before_log==outer['artifact_snapshot_before_outer_record']['logical_bytes'] and before_alloc==outer['artifact_snapshot_before_outer_record']['allocated_bytes_snapshot'])
    check('final logical allocated bounded',max(final_log,final_alloc)<=bud['artifact_bytes'])
    for k in ('scientific_authority','scientific_readiness','complete_codec_certificate_issued','full_native_graph_qualified','full_native_io_custody','historical_runtime_loader_continuous_custody'):
        check('false qualification '+k,outer[k] is False)
    check('no archive spectral values',outer['archive_spectral_values_read']==0 and receipt['telescope_provenance'] is False and receipt['archive_payload_verified'] is False and receipt['scientific_allocation_charged'] is False and receipt['rng_draws']==receipt['network_requests']==0)
    for item in index:
        raw,p=read(item['local_path'])
        check('publication raw body pin',p['bytes']==item['raw_bytes'] and p['sha256']==item['raw_sha256'])
        representation=raw if item['representation']=='utf-8' else base64.b64encode(raw)+b'\n'
        blob=hashlib.sha1(b'blob '+str(len(representation)).encode()+b'\0'+representation).hexdigest()
        check('publication representation Git blob',blob==item['git_blob'] and len(representation)==item['representation_bytes'])
    marker_raw,markerpin=read(A/'ACTIVATION.json')
    check('marker only activation retained exact',pub['activation_marker_only_verified'] is True and pub['sole_parent']==pub['preparation_commit'] and pub['changed_paths']==['results_radio_codec16_control_20261006g/admission/ACTIVATION.json'] and marker_raw.decode()==pub['activation_complete_body'] and hashlib.sha1(b'blob '+str(len(marker_raw)).encode()+b'\0'+marker_raw).hexdigest()==pub['activation_git_blob'])
    elapsed=time.monotonic()-START
    result=dict(schema='radio-codec16-independent-actual-review-v1',status='VERIFIED_CONTROLLED_PARTIAL_HANDOFF',checks_passed=sum(CHECKS.values()),failures=[],checks_by_category=CHECKS,assertion_transcript_sha256=CHECK_DIGEST.hexdigest(),all2638selectedpins_fully_rehashed=True,selected_full_rehash_bytes=rehashed,config_sha256=cp['sha256'],preread_sha256=pp['sha256'],frozen_manifest_sha256=manifest_sha,outer_result_pin=op,raw_custody_pin=lp,codec_receipt_pin=rp,caller_pin=cap,hdf_file_pins=hdfpins,parent_read_components=components,parent_explicit_reads=sum(components.values()),opaque_child_reservation=bud['child_read_reserve_bytes'],conservative_joined_reads=sum(components.values())+bud['child_read_reserve_bytes'],actual_live_samples=len(leaf['proc_samples']),same_child=dict(local=6,outer=resolution['outer_proc_pid'],starttime=resolution['child_starttime_ticks'],namespace=resolution['owner']['namespace_identity']),terminal_kernel_io=terminal['io'],leaf_seconds=leaf['complete_direct_leaf_seconds'],whole_gate_seconds=caller['elapsed_complete_gate_seconds'],gate_wait4_rss=caller['gate_peak_rss_bytes'],leaf_wait4_rss=wait['maxrss_bytes'],conservative_rss_sum=caller['gate_peak_rss_bytes']+wait['maxrss_bytes'],final_storage_logical_including_external_marker=final_log,final_storage_allocated_including_external_marker=final_alloc,final_storage_entries=final+marker,publication_representations_checked=len(index),independent_remote_refetch_performed=False,no_native_HDF5_normalizer_producer_or_frozen_source_execution=True,no_control_rerun=True,scientific_certificate_issued=False,normalization_hashes_not_reproduced_by_this_review=True,administrative_read_bytes=READS,administrative_seconds=elapsed,administrative_read_limit=LIMIT,administrative_deadline_seconds=60,preliminary_shape_inspections_additional_conservative_bytes=8*1024**2)
    out=G/'closed/actual-review.json'
    with out.open('xb') as stream:stream.write(canonical(result))
    print(json.dumps({k:result[k] for k in ('status','checks_passed','selected_full_rehash_bytes','parent_explicit_reads','conservative_joined_reads','final_storage_logical_including_external_marker','final_storage_allocated_including_external_marker','administrative_read_bytes','administrative_seconds')},sort_keys=True))


if __name__=='__main__':main()
