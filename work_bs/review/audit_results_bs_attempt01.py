"""Independent read-only verification of the three frozen BS trial artifacts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import time

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'work_bs'
OUT=ROOT/'review/REVIEW_RESULTS_BS.json'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())

def check(value,message):
    if not value:raise AssertionError(message)

def metadata(s):
    return dict(device=s.st_dev,inode=s.st_ino,size=s.st_size,mode=stat.S_IMODE(s.st_mode),
                mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,nlink=s.st_nlink)

def encoded(stream,index):
    record={'schema':'BS_ARTIFICIAL_FILE_FIXTURE_V1','stream':stream,'index':index,
            'status':'OFF_VETO' if index%3==0 else 'THREE_ON_FAIL',
            'payload':'0123456789abcdef'*118+'0123456789ab'}
    return (json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def inspect_stream(path,stream):
    before=metadata(path.stat());n=size=tail=0;digest=hashlib.sha256();prefix=True
    with path.open('rb') as f:
        check(metadata(os.fstat(f.fileno()))==before,'Opened stream identity mismatch')
        for line in f:
            digest.update(line);size+=len(line)
            expected=encoded(stream,n)
            if line.endswith(b'\n'):
                prefix=prefix and line==expected;n+=1
            else:
                prefix=prefix and expected.startswith(line);tail=len(line)
        check(metadata(os.fstat(f.fileno()))==before,'Descriptor mutated during review')
    check(metadata(path.stat())==before,'Path changed during review')
    return dict(path=str(path.relative_to(ROOT)),bytes=size,sha256=digest.hexdigest(),
                complete_records=n,partial_record_bytes=tail,exact_fixture_prefix=prefix,identity=before)

def pins_valid(plan):
    for item in plan['source_pins']+plan['historical_pins']:
        p=REPO/item['path']
        check(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Changed pin '+item['path'])

def main():
    check(not OUT.exists(),'Independent result review already exists')
    started=time.monotonic();plan=read(ROOT/'BS_FILE_STABILITY_PLAN.json')
    freeze=read(ROOT/'PUBLIC_FREEZE_RECEIPT_BS.json')
    check(sha(ROOT/'BS_FILE_STABILITY_PLAN.json')==freeze['plan_sha256'],'Plan freeze digest')
    check(freeze['before_execution'] and freeze['exact_readback_verified'],'Freeze receipt flags')
    pins_valid(plan)
    check([t['id'] for t in plan['trials']]==['bq_serial','br_serial','br_overlap'],'Fixed trial identities')
    root=ROOT/'execution'/plan['execution_identity']
    check({p.name for p in root.iterdir() if p.is_dir()}=={t['id'] for t in plan['trials']},'Extra trial directory')
    expected=[]
    for stream in range(2):
        h=hashlib.sha256();size=0
        for n in range(45000):
            raw=encoded(stream,n);h.update(raw);size+=len(raw)
        expected.append(dict(stream=stream,records=45000,bytes=size,sha256=h.hexdigest()))
    check(expected==plan['expected_streams'],'Independent prospective fixture hash reconstruction')
    trials=[];files_rehashed=bytes_rehashed=0
    for trial in plan['trials']:
        folder=root/trial['id'];terminal=read(folder/'TERMINAL_BS.json')
        receipt=read(folder/'ACTUAL_RECEIPT.json');result=read(folder/'payload/RESULT.json')
        monitor=read(folder/'payload/FILE_MONITOR.json')
        audit_raw=(folder/'PYTHON_AUDIT.jsonl').read_bytes();audit=[json.loads(l) for l in audit_raw.splitlines()]
        check(terminal['trial']==trial['id'] and terminal['plan_sha256']==freeze['plan_sha256'],'Terminal binding')
        check(terminal['public_freeze_commit']==freeze['public_commit_sha'],'Freeze commit binding')
        names={p.as_posix() for p in [x.relative_to(folder) for x in folder.rglob('*') if x.is_file()] if p.name!='TERMINAL_BS.json'}
        declared={item['path'] for item in terminal['files']}
        check(names==declared,'Final inventory file identities changed: '+trial['id'])
        for item in terminal['files']:
            p=folder/item['path'];check(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Final inventory content mismatch '+str(p))
            files_rehashed+=1;bytes_rehashed+=item['bytes']
        check(sha(folder/'ACTUAL_RECEIPT.json')==terminal['capture_receipt_sha256'],'Capture receipt binding')
        check(receipt['status']==terminal['capture_status'] and receipt['actual_exit_code']==terminal['actual_exit_code'],'Actual process outcome binding')
        check(receipt['child_wait_completed'] and receipt['natural_stdout_eof'] and receipt['stdout_eof'] and not receipt['killed'],'Actual child closure')
        check(receipt['descendant_cleanup_completed'] and receipt['remaining_live_descendants']==[],'Owned process cleanup')
        check(receipt['source_pins_verified_before'] and receipt['source_pins_verified_after'] and terminal['source_and_historical_pins_verified_after'],'Historical pin checks')
        check(sha(folder/'payload/RESULT.json')==receipt['result_sha256'],'RESULT binding')
        check(sha(folder/'payload/FILE_MONITOR.json')==result['monitor']['sha256'],'Monitor binding')
        check(sha(folder/'STDOUT.log')==receipt['log_sha256']==receipt['observed_stdout_sha256'],'Actual stdout bytes')
        stdout_last=json.loads((folder/'STDOUT.log').read_text().splitlines()[-1])
        check(stdout_last==receipt['terminal_stdout_json'] and stdout_last['status']==result['status'],'Terminal stdout binding')
        check(audit[0]['event']=='BS_PYTHON_AUDIT_START' and audit[-1]['event']=='BS_PYTHON_AUDIT_END','Complete audit brackets')
        check(audit[-1]['diagnostic_return_code']==receipt['actual_exit_code'] and audit[-1]['exception'] is None,'Audit exit binding')
        check(audit[-1]['recorded_operation_events']==len(audit)-2,'Audit event count')
        check(audit[-1]['bytes_before_footer']==sum(len(x) for x in audit_raw.splitlines(keepends=True)[:-1]),'Audit byte count')
        check(monitor['complete'] and not monitor['monitor_errors'] and monitor['dropped_events']==0 and monitor['inotify_available'],'Monitor completeness')
        check(result['writer']==trial['writer'] and result['records_per_stream']==45000 and result['pace_ms_per_1000_records']==trial['pace_ms'],'Fixed fixture execution parameters')
        streams=[]
        for i in range(2):
            detail=result['streams'][i];stream=inspect_stream(folder/'payload/payload'/detail['path'],i)
            check(stream['exact_fixture_prefix'] and stream['complete_records']==45000 and stream['partial_record_bytes']==0,'Complete exact fixture records')
            for key in ('bytes','sha256'):
                check(stream[key]==expected[i][key]==detail['writer_receipt'][key]==detail['expected'][key],'Expected/writer/file content binding')
            check(detail['status']=='PASS','Per-stream compute verification failed')
            check(detail['initial_independent_check']==detail['final_independent_check'],'Child start/end check binding')
            check(stream['identity']==detail['final_independent_check']['identity'],'File identity changed since child')
            streams.append(stream)
        pass_trial=trial['id']!='br_serial'
        check((terminal['status']=='PASS')==pass_trial and (result['status']=='PASS')==pass_trial,'Expected retained terminal statuses')
        check(receipt['actual_exit_code']==(0 if pass_trial else 2),'Actual exit code')
        if pass_trial:
            check(not monitor['violations'] and terminal['final_inventory_matches_manifests'],'Passing trial closure')
            check(len(terminal['parent_stream_verification'])==2,'Passing parent verification')
        else:
            check(len(monitor['violations'])==1 and monitor['violations'][0]['kind']=='PATH_REPLACED','Expected serial BR anomaly')
            check(not terminal['final_inventory_matches_manifests'],'No false effective PASS')
        check(terminal['wall_seconds_including_parent_closure']<=120 and terminal['cpu_seconds_including_parent_closure']<=90,'Time caps')
        check(receipt['resources']['max_child_RSS_bytes']<=512<<20 and sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())<=384<<20,'RSS/storage caps')
        unusual=[e for e in monitor['inotify_events'] if e['name'] and e['name'] not in ['fixture_0.jsonl','fixture_1.jsonl','.fixture_0.jsonl.pending','.fixture_1.jsonl.pending']]
        trials.append(dict(id=trial['id'],status=terminal['status'],actual_exit_code=receipt['actual_exit_code'],
            exact_wait_natural_EOF_cleanup=True,terminal_sha256=sha(folder/'TERMINAL_BS.json'),
            result_sha256=receipt['result_sha256'],monitor_sha256=result['monitor']['sha256'],
            audit_events=len(audit)-2,inotify_events=len(monitor['inotify_events']),
            monitor_samples=len(monitor['samples']),monitor_violations=monitor['violations'],
            unexpected_inotify_names=sorted(set(e['name'] for e in unusual)),
            streams=streams,wall_seconds=terminal['wall_seconds_including_parent_closure'],
            CPU_seconds=terminal['cpu_seconds_including_parent_closure'],max_RSS_bytes=receipt['resources']['max_child_RSS_bytes']))
    serial=root/'br_serial';monitor=read(serial/'payload/FILE_MONITOR.json')
    violation=monitor['violations'][0];name='.fixture_0.jsonl.pending'
    orphan=inspect_stream(serial/'payload/payload'/name,0)
    extra_path=next(p for p in (serial/'payload/payload').iterdir() if p.name.startswith('.fixture_0.jsonl.') and p.name!=name)
    extra=inspect_stream(extra_path,0)
    check(orphan['complete_records']==45000 and orphan['exact_fixture_prefix'],'Recreated pending content')
    check(orphan['identity']['inode']!=trials[1]['streams'][0]['identity']['inode'],'Orphan is a different inode')
    events=monitor['inotify_events'];deletes=[e for e in events if e['name']==name and e['mask']&0x200]
    recreated=[e for e in events if e['name']==name and e['mask']&0x80]
    check(len(deletes)==1 and len(recreated)==1 and deletes[0]['elapsed_seconds']<recreated[0]['elapsed_seconds'],'Pending deletion followed by reappearance')
    simultaneous=next(s for s in monitor['samples'] if name in s['paths'] and s['paths'][name]['inode']==violation['after']['inode'])
    check(any(x['inode']==violation['before']['inode'] for x in simultaneous['held_descriptors']),'Original inode remained held')
    check(simultaneous['paths']['fixture_0.jsonl']['inode']==violation['before']['inode'],'Original final remained visible')
    witness=read(root/'OVERLAP_WITNESS.json');first=witness['first']['files'][0];last=witness['last']['files'][0]
    nbytes=first['fd_after']['bytes'];h=hashlib.sha256()
    with (root/'br_overlap/payload/payload/fixture_0.jsonl').open('rb') as f:
        remaining=nbytes
        while remaining:
            b=f.read(min(1<<20,remaining));check(bool(b),'Witness prefix missing');h.update(b);remaining-=len(b)
    check(h.hexdigest()==first['read_sha256'],'Witness initial prefix matches final stream')
    check(last['read_sha256']==expected[0]['sha256'],'Witness completed first stream binding')
    check(first['fd_after']['inode']==last['fd_after']['inode'],'Witness saw same inode across publication')
    check(witness['last']['monotonic_ns']-witness['first']['monotonic_ns']>=6000000000,'Witness six-second separation')
    check(sum(p.stat().st_size for p in root.rglob('*') if p.is_file())<=1<<30,'Phase storage cap')
    pins_valid(plan)
    report=dict(schema='SETI_BS_INDEPENDENT_RESULT_REVIEW_V1',status='PASS_INDEPENDENT_EVIDENCE_REVIEW',
        BS_integrity_outcome='TWO_PASS_ONE_FAIL_PATH_RECREATION',historical_control_status='23_CONTROLS_PASS_A04_PAIR_CLOSURE_BLOCKED',
        source_pins_verified=len(plan['source_pins']),historical_pins_verified=len(plan['historical_pins']),
        frozen_plan_sha256=freeze['plan_sha256'],public_freeze_commit=freeze['public_commit_sha'],
        independent_expected_streams=expected,files_rehashed=files_rehashed,bytes_rehashed=bytes_rehashed,
        complete_fixture_streams_verified=6,complete_fixture_records_verified=270000,trials=trials,
        recreated_pending=orphan,additional_temporary_prefix=extra,
        event_sequence=dict(original_pending_delete=deletes[0],pending_reappeared_move_to=recreated[0],
                            changed_inode_held_fd_sample=simultaneous),
        witness=dict(sha256=sha(root/'OVERLAP_WITNESS.json'),initial_prefix_bytes=nbytes,initial_prefix_verified=True,
                     complete_final_first_stream_verified=True,same_inode=True),
        conclusions=[
            'BR serial contains a real recreated pending pathname after normal publication and unlink. Its new inode coexists with the original final inode and held descriptor; this is not ordinary hard-link bookkeeping.',
            'Recreated pending has complete expected stream0 content, so the BS anomaly differs from BQ/BR truncated final evidence. Both BR-serial final streams remain complete but the preregistered integrity trial correctly fails.',
            'Inotify retained temporary names and .rsync-tmp directory events near recreation; this is consistent with copy/reconciliation activity, but no responsible process or exact platform mechanism is established.',
            'Python audit records expected writer operations and no matching unexpected recreation. It has no native/external syscall coverage and cannot independently attribute the mutation.',
            'Failure in serial BR and success in overlapped BR do not support concurrent tool execution as a necessary or sufficient cause. Yield/poll, pacing, load and workspace mechanisms remain uncontrolled possibilities.',
            'A separately preregistered deterministic stage in an isolated tmpfs working directory with one uninterrupted execution is a reasonable mitigation experiment, not a proven repair. Preserve stable exported bytes with source/destination hashes and maintain caps.',
            'No A04 retry or qualification is performed by BS. Prior failed identities and23/24status remain unchanged.'
        ],operations=dict(historical_execution_mutations=0,new_science_trials=0,new_RNG_calls=0,new_scan_scores=0),
        reviewer_source_sha256=sha(Path(__file__)),completed_utc=datetime.now(timezone.utc).isoformat(),
        wall_seconds=time.monotonic()-started)
    with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(status=report['status'],report_sha256=sha(OUT),bytes_rehashed=bytes_rehashed,
                         extra_prefix_records=extra['complete_records'],extra_partial_bytes=extra['partial_record_bytes'],
                         extra_exact_prefix=extra['exact_fixture_prefix'],wall_seconds=report['wall_seconds'])))

if __name__=='__main__':main()
