"""Run thirty-two frozen native172 safe-core batches with atomic child-output capture.

No retry, overwrite, network or detached child after closure. A search/audit
failure, changed pin or passing descriptive flag stops the finite campaign.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_bn'
STDOUT_CAP=4194304
BATCHES=([list(range(start,start+8)) for start in range(1,121,8)]
         + [list(range(121,128))]
         + [list(range(start,start+8)) for start in range(129,249,8)]
         + [list(range(249,255))])

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())
def utc():return datetime.now(timezone.utc).isoformat()
def require(value,message):
    if not value:raise ValueError(message)
def event(name,**values):print(json.dumps({'event':name,**values}),flush=True)

def publish_bytes(path,data):
    """Same-directory tempfile plus exclusive atomic hard-link publication."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists(),'No overwrite: '+str(path))
    descriptor,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.link(temporary,path)
        temporary.unlink()
        folder=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(folder)
        finally:os.close(folder)
        require(path.stat().st_size==len(data) and sha(path)==hashlib.sha256(data).hexdigest(),
                'Atomic publication bytes differ')
    finally:
        if temporary.exists():temporary.unlink()

def write(path,value):
    publish_bytes(path,(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())

def verify_pins(pins):
    for path,digest in pins.items():require(sha(path)==digest,'Preserved evidence changed: '+path)

def capture(command,folder,label,script,planpath,result,prereg,batch):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    log=folder/(label+'_BN.log');actualpath=folder/(label+'_ACTUAL_EXIT_BN.json')
    require(not log.exists() and not actualpath.exists(),'No capture overwrite')
    write(folder/(label+'_START_BN.json'),{'schema':'SETI_BN_ATOMIC_BUFFER_CAPTURE_START_V2',
          'started_utc':utc(),'batch':batch,'command':command,'prereg_github_commit':prereg,
          'source_sha256':sha(script),'plan_sha256':sha(planpath),
          'final_log_published_only_after_child_wait':True,'maximum_stdout_buffer_bytes':STDOUT_CAP})
    observed=hashlib.sha256();count=0;start=time.perf_counter();child=None;usage=None;code=None
    capture_error=None;stdout_eof=False;wait_completed=False;buffer=bytearray();fully_preserved=True
    def append(chunk,retain=True):
        nonlocal count,fully_preserved
        count+=len(chunk);observed.update(chunk)
        if retain and len(buffer)+len(chunk)<=STDOUT_CAP:buffer.extend(chunk)
        else:
            fully_preserved=False
            if retain:raise MemoryError('Four MiB stdout capture cap exceeded; no next batch')
    try:
        child=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,start_new_session=True)
        while True:
            chunk=child.stdout.read1(65536)
            if not chunk:stdout_eof=True;break
            append(chunk)
    except BaseException as exc:
        capture_error=type(exc).__name__+': '+str(exc)
        if child is not None:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            while True:
                chunk=child.stdout.read1(65536)
                if not chunk:stdout_eof=True;break
                append(chunk,retain=False)
    if child is not None:
        pid,status,usage=os.wait4(child.pid,0)
        require(pid==child.pid,'Reaped child identity differs')
        code=os.waitstatus_to_exitcode(status);child.returncode=code;wait_completed=True
        child.stdout.close()
    # The final log pathname has not existed at any time while the child ran.
    publish_bytes(log,buffer)
    receipt={'schema':'SETI_BN_ACTUAL_'+label+'_EXIT_V2','batch':batch,
             'completed_utc':utc(),'command':command,'source_sha256':sha(script),
             'plan_sha256':sha(planpath),'prereg_github_commit':prereg,
             'actual_exit_code':code,'child_pid':child.pid if child is not None else None,
             'stdout_eof':stdout_eof,'child_wait_completed':wait_completed,
             'wait_method':'os.wait4 exact child','capture_error':capture_error,
             'wall_seconds':time.perf_counter()-start,
             'child_user_cpu_seconds':usage.ru_utime if usage is not None else None,
             'child_system_cpu_seconds':usage.ru_stime if usage is not None else None,
             'max_child_RSS_KiB':usage.ru_maxrss if usage is not None else None,
             'log_path':str(log),'log_bytes':log.stat().st_size,'log_sha256':sha(log),
             'observed_stdout_bytes':count,'observed_stdout_sha256':observed.hexdigest(),
             'stdout_fully_preserved':fully_preserved,'maximum_stdout_buffer_bytes':STDOUT_CAP,
             'final_log_published_only_after_child_wait':True,
             'result_path':str(result),'result_sha256':sha(result) if Path(result).is_file() else None,
             'new_archive_requests':0}
    write(actualpath,receipt);return actualpath,receipt

def require_closed_actual(actual):
    require(actual['capture_error'] is None and actual['actual_exit_code']==0
            and actual['stdout_eof'] is True and actual['child_wait_completed'] is True,
            'Child did not close successfully; no next batch')
    require(actual['stdout_fully_preserved'] is True
            and actual['log_sha256']==actual['observed_stdout_sha256']==sha(actual['log_path'])
            and actual['log_bytes']==actual['observed_stdout_bytes']==Path(actual['log_path']).stat().st_size,
            'Captured/published stdout identity differs')

def campaign(prereg):
    require(re.fullmatch(r'[0-9a-f]{40}',prereg) is not None,'Exact prereg commit SHA required')
    wrapper=WORK/'bounded_search_bn.py';auditor=WORK/'review/audit_real_results_bn.py'
    plans=[WORK/'plans'/f'batch{i:02d}.json' for i in range(1,33)]
    pins={str(p):sha(p) for p in [Path(__file__).resolve(),wrapper,auditor,*plans]}
    def pin(path,digest):
        require(path not in pins or pins[path]==digest,'Conflicting frozen pins: '+path)
        pins[path]=digest
    for qs,planpath in zip(BATCHES,plans):
        plan=read(planpath)
        require(plan['schema']=='S2017_BN_LOCAL_Q_ESS_V1' and plan['core_q_list']==qs,
                'Frozen batch admission differs')
        require(plan['new_archive_requests_authorized']==0 and 128 not in qs,
                'Archive/DC scope differs')
        require(plan['expected_track_trials']==len(qs)*54125568
                and plan['expected_selected_scalar_sum_checks']==len(qs)*216
                and plan['expected_shared_kernel_calibration_vectors']==len(qs)*72,
                'Frozen variable batch counts differ')
        require(plan['source_sha256'][str(wrapper)]==sha(wrapper),'Wrapper plan binding differs')
        for path,digest in plan['source_sha256'].items():pin(path,digest)
        pin(plan['dataset_manifest_path'],plan['dataset_manifest_sha256'])
        pin(plan['prior_completed_delivery_path'],plan['prior_completed_delivery_sha256'])
        pin(plan['prior_completed_campaign_path'],plan['prior_completed_campaign_sha256'])
        pin(plan['prepared_adjacent_receipt_path'],plan['prepared_adjacent_receipt_sha256'])
        for scope in plan['scans']:pin(scope['path'],scope['input_sha256'])
    verify_pins(pins)
    startpath=WORK/'execution/CAMPAIGN_START_BN.json'
    completepath=WORK/'results/CAMPAIGN_COMPLETE_BN.json'
    stoppath=WORK/'results/CAMPAIGN_STOP_BN.json'
    require(not any(p.exists() for p in (startpath,completepath,stoppath)),'No campaign rerun or overwrite')
    for number in range(1,33):
        require(not any((WORK/folder/f'batch{number:02d}').exists()
                        for folder in ('results','execution','review')),'No existing batch output permitted')
    start=time.perf_counter();started=utc();results=[]
    allq=[q for qs in BATCHES for q in qs]
    require(allq==list(range(1,128))+list(range(129,255)) and len(allq)==253 and len(BATCHES)==32,
            'Native172 safe q1..127 and q129..254 geometry differs')
    write(startpath,{'schema':'SETI_BN_FINITE_CAMPAIGN_START_V1','started_utc':started,
          'prereg_github_commit':prereg,'frozen_batch_count':32,'frozen_q_list':allq,
          'input_source_plan_sha256':pins,'per_search_timeout_seconds':620,
          'per_search_wrapper_alarm_seconds':600,'per_audit_timeout_seconds':60,
          'maximum_stdout_buffer_bytes':STDOUT_CAP,'retry_authorized':False,
          'excluded_q':[0,128,255],'new_archive_requests':0})
    try:
        for number,(qs,planpath) in enumerate(zip(BATCHES,plans),1):
            verify_pins(pins);plan=read(planpath)
            out=WORK/'results'/f'batch{number:02d}'/'run'
            folder=WORK/'execution'/f'batch{number:02d}'
            auditfolder=WORK/'review'/f'batch{number:02d}'
            complete_result=out/'ALL_FROZEN_Q_COMPLETE.json'
            audit_result=auditfolder/'REAL_RESULT_AUDIT_BN.json'
            event('BATCH_STARTED',batch=number,q_list=qs)
            command=['timeout','--signal=TERM','--kill-after=5s','620s',sys.executable,'-B',str(wrapper),
                     '--plan',str(planpath),'--out',str(out),'--all-q']
            searchpath,actual=capture(command,folder,'SEARCH',wrapper,planpath,complete_result,prereg,number)
            event('SEARCH_CLOSED',batch=number,actual_exit_code=actual['actual_exit_code'],wall_seconds=actual['wall_seconds'])
            require_closed_actual(actual);complete=read(complete_result)
            require(complete['q_list']==qs and complete['plan_sha256']==sha(planpath)
                    and complete['status']=='ALL_FROZEN_BATCH_SEARCHES_AND_TRIAGE_COMPLETE'
                    and complete['total_track_trials']==len(qs)*54125568,
                    'Full frozen batch completion required')
            verify_pins(pins)
            command=['timeout','--signal=TERM','--kill-after=5s','60s',sys.executable,'-B',str(auditor),
                     '--plan',str(planpath),'--out',str(out),'--actual',str(searchpath),'--receipt',str(audit_result)]
            auditpath,auditactual=capture(command,folder,'REAL_RESULT_AUDIT',auditor,planpath,audit_result,prereg,number)
            event('AUDIT_CLOSED',batch=number,actual_exit_code=auditactual['actual_exit_code'],wall_seconds=auditactual['wall_seconds'])
            require_closed_actual(auditactual);audit=read(audit_result)
            require(audit['status']=='PASS_CLOSED_BOUNDED_REAL_RESULTS'
                    and audit['plan_sha256']==actual['plan_sha256']==auditactual['plan_sha256']==complete['plan_sha256']
                    and audit['complete_result_sha256']==actual['result_sha256']==sha(complete_result)
                    and auditactual['result_sha256']==sha(audit_result),
                    'Closed audit/result binding differs')
            require(audit['fixed_scalar_sum_comparisons']==len(qs)*216
                    and audit['shared_kernel_calibration_vector_replays']==len(qs)*72,
                    'Variable batch audit counts differ')
            require_closed_actual(actual);verify_pins(pins)
            scans=[]
            for q in qs:
                searchfile=out/f'q{q:03d}'/'SIX_SCAN_SEARCH_COMPLETE.json'
                require(sha(searchfile)==audit['input_and_artifact_sha256'][str(searchfile)],
                        'Audited q summary changed before status publication')
                scans.extend(read(searchfile)['scans'])
            maximum={str(width):{role:max(ws['maximum_local_ess'] for s in scans if s['role']==role
                        for ws in s['width_searches'] if ws['width_channels']==width)
                        for role in ('ON','OFF')} for width in (1,3,9,33)}
            passing=sum(r['all3ON_ge10_noOFF_rows'] for r in complete['q_results'])
            entry={'batch':number,'q_list':qs,'plan_path':str(planpath),'plan_sha256':sha(planpath),
              'execution_prereg_github_commit':prereg,'search_actual_path':str(searchpath),
              'search_actual_sha256':sha(searchpath),'audit_actual_path':str(auditpath),
              'audit_actual_sha256':sha(auditpath),'audit_result_path':str(audit_result),
              'audit_result_sha256':sha(audit_result),'complete_result_path':str(complete_result),
              'complete_result_sha256':sha(complete_result),'actual_search_exit_code':actual['actual_exit_code'],
              'actual_audit_exit_code':auditactual['actual_exit_code'],
              'ON_catalog_rows':sum(r['ON_local_catalog_rows'] for r in complete['q_results']),
              'OFF_catalog_rows':sum(s['local_hits'] for s in scans if s['role']=='OFF'),
              'passing_flags':passing,'total_track_trials':complete['total_track_trials'],
              'forced_measurement_slots':sum(r['forced_measurement_slots'] for r in complete['q_results']),
              'supported_forced_measurements':sum(r['supported_slots'] for r in complete['q_results']),
              'unsupported_forced_slots':sum(r['unsupported_slots'] for r in complete['q_results']),
              'fixed_scalar_sum_comparisons':audit['fixed_scalar_sum_comparisons'],
              'shared_kernel_calibration_vector_replays':audit['shared_kernel_calibration_vector_replays'],
              'maximum_scalar_sum_error':audit['maximum_scalar_sum_error'],
              'maximum_replayed_calibration_error':audit['maximum_replayed_calibration_error'],
              'maximum_local_ESS_by_width':maximum,
              'search_wall_seconds':actual['wall_seconds'],'audit_wall_seconds':auditactual['wall_seconds'],
              'search_user_cpu_seconds':actual['child_user_cpu_seconds'],
              'search_system_cpu_seconds':actual['child_system_cpu_seconds'],
              'audit_user_cpu_seconds':auditactual['child_user_cpu_seconds'],
              'audit_system_cpu_seconds':auditactual['child_system_cpu_seconds']}
            write(folder/'BATCH_CLOSED_BN.json',entry);results.append(entry)
            event('BATCH_CLOSED',**entry)
            require(passing==0,'Passing descriptive flag requires parent inspection; no next batch')
        require(len(results)==32 and sum(r['total_track_trials'] for r in results)==13693768704,
                'Final thirty-two-batch count differs')
        verify_pins(pins)
        result={'schema':'SETI_BN_FINITE_CAMPAIGN_COMPLETION_V1',
          'status':'ALL_THIRTY_TWO_BATCHES_SEARCHED_AND_AUDITED','started_utc':started,'completed_utc':utc(),
          'wall_seconds':time.perf_counter()-start,'prereg_github_commit':prereg,
          'batch_results':results,'completed_batches':32,'q_list':allq,
          'native_chunk_index':172,'native_channel_start':180355072,
          'carrier_channels':253*4096,'scan_band_searches':253*6,
          'technical_channel_bin_bandwidth_Hz':253*4096*2.7939677238464355,
          'new_independent_observations':0,'new_unique_archive_ID_credit':0,
          'qualification':'Expanded descriptive reanalysis of retained native172 from one historical visit; no original-search or new-observation credit.',
          'total_track_trials':sum(r['total_track_trials'] for r in results),
          'input_source_plan_sha256':pins,'excluded_q':[0,128,255],
          'new_archive_requests':0,'background_science_jobs_running':False}
        write(completepath,result);event('CAMPAIGN_COMPLETE',completed_batches=32,
          total_track_trials=result['total_track_trials']);return 0
    except BaseException as exc:
        write(stoppath,{'schema':'SETI_BN_FINITE_CAMPAIGN_STOP_V1','status':'STOPPED_NO_NEXT_BATCH',
          'completed_utc':utc(),'prereg_github_commit':prereg,'completed_batches':len(results),
          'batch_results':results,'reason':type(exc).__name__+': '+str(exc),
          'wall_seconds':time.perf_counter()-start,'new_archive_requests':0,
          'background_science_jobs_running':False})
        event('CAMPAIGN_STOPPED',completed_batches=len(results),reason=type(exc).__name__+': '+str(exc));return 1

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prereg-commit',required=True)
    args=parser.parse_args();return campaign(args.prereg_commit)

if __name__=='__main__':sys.exit(main())


