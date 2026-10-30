"""One fixed recovery attempt for original BJ batches10..12, in new directories.

Science sources and all twelve original plans remain unchanged. Original
batch10 and its failed qualification are retained. Logs are buffered while a
child runs and atomically published only after EOF and exact-child wait4.
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

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work_bj'
RECOVERY_PLAN=WORK/'recovery/TAIL_RECOVERY_PLAN_BJ_V2.json'
RECOVERY_PLAN_SHA='f9207d67c357e70d57e6d77cba35a77540dd8f276d4f4e6323b3f8548d4557b7'
ORIGINAL_PREREG='4c82703dd1a2de8da94b4411ace5cede2a77fa6f'
STDOUT_CAP=4194304

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
    log=folder/(label+'_BJ.log');actualpath=folder/(label+'_ACTUAL_EXIT_BJ.json')
    require(not log.exists() and not actualpath.exists(),'No capture overwrite')
    write(folder/(label+'_START_BJ.json'),{'schema':'SETI_BJ_ATOMIC_BUFFER_CAPTURE_START_V2',
          'started_utc':utc(),'batch':batch,'command':command,'prereg_github_commit':prereg,
          'original_science_prereg_github_commit':ORIGINAL_PREREG,
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
    receipt={'schema':'SETI_BJ_ACTUAL_'+label+'_EXIT_V2','batch':batch,
             'completed_utc':utc(),'command':command,'source_sha256':sha(script),
             'plan_sha256':sha(planpath),'prereg_github_commit':prereg,
             'original_science_prereg_github_commit':ORIGINAL_PREREG,
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

def gate_preserved_prefix(plan):
    require(sha(RECOVERY_PLAN)==RECOVERY_PLAN_SHA,'Frozen recovery plan differs')
    require(plan['schema']=='SETI_BJ_FIXED_TAIL_RECOVERY_PLAN_V2'
            and plan['original_prereg_github_commit']==ORIGINAL_PREREG
            and plan['recovery_batches']==[10,11,12],'Fixed recovery scope differs')
    require(sha(plan['original_start_path'])==plan['original_start_sha256']
            and sha(plan['original_stop_path'])==plan['original_stop_sha256'],'Original campaign evidence differs')
    stop=read(plan['original_stop_path'])
    require(stop['status']=='STOPPED_NO_NEXT_BATCH' and stop['completed_batches']==9
            and stop['prereg_github_commit']==ORIGINAL_PREREG
            and stop['batch_results']==plan['original_prefix_batch_results'],
            'Expected unchanged nine-batch prefix required')
    require([r['batch'] for r in stop['batch_results']]==list(range(1,10)),'Nine prefix identities differ')
    verify_pins(plan['preserved_prefix_and_input_sha256'])
    verify_pins(plan['preserved_failed_attempt_file_sha256'])
    for r in stop['batch_results']:
        search=read(r['search_actual_path']);auditactual=read(r['audit_actual_path'])
        audit=read(r['audit_result_path']);complete=read(r['complete_result_path'])
        require(search['actual_exit_code']==auditactual['actual_exit_code']==0
                and search['stdout_eof'] and search['child_wait_completed']
                and auditactual['stdout_eof'] and auditactual['child_wait_completed'],
                'Closed original prefix required')
        require(search['prereg_github_commit']==auditactual['prereg_github_commit']==ORIGINAL_PREREG
                and audit['status']=='PASS_CLOSED_BOUNDED_REAL_RESULTS'
                and complete['q_list']==list(range(25+(r['batch']-1)*8,33+(r['batch']-1)*8))
                and r['passing_flags']==0,'Original prefix audit/scope differs')
    return stop

def campaign(prereg):
    require(re.fullmatch(r'[0-9a-f]{40}',prereg) is not None,'Exact recovery prereg commit SHA required')
    plan=read(RECOVERY_PLAN);stop=gate_preserved_prefix(plan)
    wrapper=WORK/'bounded_search_bj.py';auditor=WORK/'review/audit_real_results_bj.py'
    startpath=WORK/'recovery/TAIL_RECOVERY_START_BJ_V2.json'
    completepath=WORK/'results/CAMPAIGN_COMPLETE_BJ_V2.json';stoppath=WORK/'results/CAMPAIGN_STOP_BJ_V2.json'
    require(not any(p.exists() for p in [startpath,completepath,stoppath]),'No recovery rerun/overwrite')
    for batch in (10,11,12):
        require(not any((WORK/folder/f'batch{batch:02d}_v2').exists()
                        for folder in ('results','execution','review')),'No existing recovery batch output')
    start=time.perf_counter();started=utc();tail=[]
    write(startpath,{'schema':'SETI_BJ_FIXED_TAIL_RECOVERY_START_V2','started_utc':started,
                    'recovery_prereg_github_commit':prereg,'original_prereg_github_commit':ORIGINAL_PREREG,
                    'recovery_runner_sha256':sha(__file__),'recovery_plan_sha256':RECOVERY_PLAN_SHA,
                    'fixed_recovery_batches':[10,11,12],'new_archive_requests':0,'automatic_retry':False})
    try:
        for batch in (10,11,12):
            gate_preserved_prefix(plan)
            planpath=WORK/'plans'/f'batch{batch:02d}.json';scope=read(planpath)
            out=WORK/'results'/f'batch{batch:02d}_v2'/'run'
            folder=WORK/'execution'/f'batch{batch:02d}_v2'
            auditfolder=WORK/'review'/f'batch{batch:02d}_v2'
            complete_result=out/'ALL_FROZEN_Q_COMPLETE.json';audit_result=auditfolder/'REAL_RESULT_AUDIT_BJ.json'
            event('RECOVERY_BATCH_STARTED',batch=batch,q_list=scope['core_q_list'])
            command=['timeout','--signal=TERM','--kill-after=5s','620s',sys.executable,'-B',str(wrapper),
                     '--plan',str(planpath),'--out',str(out),'--all-q']
            searchpath,actual=capture(command,folder,'SEARCH',wrapper,planpath,complete_result,prereg,batch)
            event('SEARCH_CLOSED',batch=batch,actual_exit_code=actual['actual_exit_code'],wall_seconds=actual['wall_seconds'])
            require_closed_actual(actual);complete=read(complete_result)
            require(complete['q_list']==scope['core_q_list']
                    and complete['status']=='ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE',
                    'All-eight recovery scope completion required')
            gate_preserved_prefix(plan)
            command=['timeout','--signal=TERM','--kill-after=5s','60s',sys.executable,'-B',str(auditor),
                     '--plan',str(planpath),'--out',str(out),'--actual',str(searchpath),'--receipt',str(audit_result)]
            auditpath,auditactual=capture(command,folder,'REAL_RESULT_AUDIT',auditor,planpath,audit_result,prereg,batch)
            event('AUDIT_CLOSED',batch=batch,actual_exit_code=auditactual['actual_exit_code'],wall_seconds=auditactual['wall_seconds'])
            require_closed_actual(auditactual);audit=read(audit_result)
            require(audit['status']=='PASS_CLOSED_BOUNDED_REAL_RESULTS'
                    and audit['plan_sha256']==actual['plan_sha256']==complete['plan_sha256']
                    and audit['complete_result_sha256']==actual['result_sha256']==sha(complete_result),
                    'Closed recovery audit binding differs')
            require_closed_actual(actual);gate_preserved_prefix(plan)
            passing=sum(r['all3ON_ge10_noOFF_rows'] for r in complete['q_results'])
            entry={'batch':batch,'q_list':scope['core_q_list'],'search_actual_path':str(searchpath),
                   'search_actual_sha256':sha(searchpath),'audit_actual_path':str(auditpath),
                   'audit_actual_sha256':sha(auditpath),'audit_result_path':str(audit_result),
                   'audit_result_sha256':sha(audit_result),'complete_result_path':str(complete_result),
                   'complete_result_sha256':sha(complete_result),'execution_prereg_github_commit':prereg,
                   'original_science_prereg_github_commit':ORIGINAL_PREREG,'attempt':'tail_recovery_v2',
                   'ON_catalog_rows':sum(r['ON_local_catalog_rows'] for r in complete['q_results']),
                   'passing_flags':passing,'total_track_trials':complete['total_track_trials']}
            write(folder/'BATCH_CLOSED_BJ.json',entry);tail.append(entry)
            require(passing==0,'Passing descriptive flag requires parent inspection; no next batch')
        results=stop['batch_results']+tail
        require([r['batch'] for r in results]==list(range(1,13))
                and sum(r['total_track_trials'] for r in results)==5196054528,'Effective twelve-batch count differs')
        gate_preserved_prefix(plan)
        original_start=read(plan['original_start_path']);completed=utc()
        wall=(datetime.fromisoformat(completed)-datetime.fromisoformat(original_start['started_utc'])).total_seconds()
        result={'schema':'SETI_BJ_FINITE_CAMPAIGN_COMPLETION_V2',
                'status':'ALL_TWELVE_BATCHES_SEARCHED_AND_AUDITED_WITH_TAIL_RECOVERY',
                'started_utc':original_start['started_utc'],'tail_started_utc':started,'completed_utc':completed,
                'wall_seconds':wall,'wall_seconds_measurement':'UTC elapsed from original campaign start; includes recovery interval.',
                'tail_wall_seconds':time.perf_counter()-start,
                'original_campaign_actual_wall_seconds':stop['wall_seconds'],
                'prereg_github_commit':ORIGINAL_PREREG,'original_prereg_github_commit':ORIGINAL_PREREG,
                'recovery_prereg_github_commit':prereg,'batch_results':results,'completed_batches':12,
                'q_list':list(range(25,121)),'total_track_trials':sum(r['total_track_trials'] for r in results),
                'original_stop_path':plan['original_stop_path'],'original_stop_sha256':plan['original_stop_sha256'],
                'original_start_path':plan['original_start_path'],'original_start_sha256':plan['original_start_sha256'],
                'superseded_original_batch10':plan['superseded_original_batch10'],
                'recovery_plan_path':str(RECOVERY_PLAN),'recovery_plan_sha256':RECOVERY_PLAN_SHA,
                'input_source_plan_sha256':plan['preserved_prefix_and_input_sha256'],
                'failed_attempt_existing_file_sha256':plan['preserved_failed_attempt_file_sha256'],
                'counting_rule':'Original batch10 retained as failed qualification; effective geometry counts recomputed batch10_v2 once.',
                'new_archive_requests':0,'background_science_jobs_running':False}
        write(completepath,result);event('CAMPAIGN_COMPLETE',completed_batches=12,total_track_trials=result['total_track_trials']);return 0
    except BaseException as exc:
        write(stoppath,{'schema':'SETI_BJ_FIXED_TAIL_RECOVERY_STOP_V2','status':'STOPPED_NO_NEXT_BATCH',
                       'completed_utc':utc(),'recovery_prereg_github_commit':prereg,
                       'original_prereg_github_commit':ORIGINAL_PREREG,'completed_tail_batches':len(tail),
                       'batch_results':tail,'reason':type(exc).__name__+': '+str(exc),
                       'tail_wall_seconds':time.perf_counter()-start,'new_archive_requests':0,
                       'background_science_jobs_running':False})
        event('RECOVERY_STOPPED',completed_tail_batches=len(tail),reason=type(exc).__name__+': '+str(exc));return 1

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prereg-commit',required=True)
    args=parser.parse_args();return campaign(args.prereg_commit)

if __name__=='__main__':sys.exit(main())
