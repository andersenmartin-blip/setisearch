"""Run twelve frozen descriptive batches, each followed by a closed-result audit.

No retry, overwrite, network access or detached child. A failed child, failed
audit, changed pin or passing descriptive flag stops the finite campaign.
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
import time

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_bj'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())

def utc():return datetime.now(timezone.utc).isoformat()

def require(value,message):
    if not value:raise ValueError(message)

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())

def event(name,**values):print(json.dumps({'event':name,**values}),flush=True)

def verify_pins(pins):
    for path,digest in pins.items():require(sha(path)==digest,'Frozen source/input/plan changed: '+path)

def capture(command,folder,label,script,planpath,result,prereg,batch):
    """Preserve merged stdout through EOF and reap the exact child with rusage."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    log=folder/(label+'_BJ.log');actualpath=folder/(label+'_ACTUAL_EXIT_BJ.json')
    write(folder/(label+'_START_BJ.json'),{'schema':'SETI_BJ_CAPTURE_START_V1',
          'started_utc':utc(),'batch':batch,'command':command,'prereg_github_commit':prereg,
          'source_sha256':sha(script),'plan_sha256':sha(planpath)})
    observed=hashlib.sha256();count=0;start=time.perf_counter();child=None;usage=None;code=None
    capture_error=None;stdout_eof=False;wait_completed=False
    with log.open('xb') as stream:
        def append(chunk):
            nonlocal count
            count+=len(chunk);observed.update(chunk);stream.write(chunk);stream.flush()
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
                    append(chunk)
        if child is not None:
            pid,status,usage=os.wait4(child.pid,0)
            require(pid==child.pid,'Reaped child identity differs')
            code=os.waitstatus_to_exitcode(status);child.returncode=code;wait_completed=True
            child.stdout.close()
        stream.flush();os.fsync(stream.fileno())
    receipt={'schema':'SETI_BJ_ACTUAL_'+label+'_EXIT_V1','batch':batch,
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
             'result_path':str(result),'result_sha256':sha(result) if Path(result).is_file() else None,
             'new_archive_requests':0}
    write(actualpath,receipt)
    return actualpath,receipt

def require_closed_actual(receipt):
    require(receipt['capture_error'] is None and receipt['actual_exit_code']==0
            and receipt['stdout_eof'] is True and receipt['child_wait_completed'] is True,
            'Child did not close successfully; no next batch')
    require(receipt['log_sha256']==receipt['observed_stdout_sha256']
            and receipt['log_bytes']==receipt['observed_stdout_bytes'],
            'Observed/log output identity differs')

def require_audit_gate(actual,audit,complete):
    require_closed_actual(actual)
    require(audit['status']=='PASS_CLOSED_BOUNDED_REAL_RESULTS','Result audit did not pass')
    require(audit['plan_sha256']==actual['plan_sha256']==complete['plan_sha256'],
            'Audit/complete/actual plan differs')
    require(Path(actual['result_path']).name=='ALL_FROZEN_Q_COMPLETE.json',
            'Search completion result required')
    require(audit['complete_result_sha256']==actual['result_sha256']==sha(actual['result_path']),
            'Completion binding differs')

def campaign(prereg):
    require(re.fullmatch(r'[0-9a-f]{40}',prereg) is not None,'Exact prereg commit SHA required')
    wrapper=WORK/'bounded_search_bj.py';auditor=WORK/'review/audit_real_results_bj.py'
    plans=[WORK/'plans'/f'batch{i:02d}.json' for i in range(1,13)]
    pins={str(p):sha(p) for p in [Path(__file__).resolve(),wrapper,auditor,*plans]}
    for batch,planpath in enumerate(plans,1):
        plan=read(planpath);start=25+(batch-1)*8
        require(plan['core_q_list']==list(range(start,start+8)),'Frozen batch admission differs')
        require(plan['schema']=='S2017_BJ_LOCAL_Q_ESS_V1','Frozen schema differs')
        require(plan['new_archive_requests_authorized']==0,'No new archive request permitted')
        require(plan['source_sha256'][str(wrapper)]==sha(wrapper),'Wrapper plan pin differs')
        for path,digest in plan['source_sha256'].items():
            require(path not in pins or pins[path]==digest,'Conflicting source pins');pins[path]=digest
        pins[plan['dataset_manifest_path']]=plan['dataset_manifest_sha256']
        pins[plan['prior_completed_delivery_path']]=plan['prior_completed_delivery_sha256']
        for scope in plan['scans']:
            require(scope['path'] not in pins or pins[scope['path']]==scope['input_sha256'],
                    'Conflicting compact input pins')
            pins[scope['path']]=scope['input_sha256']
    verify_pins(pins)
    startpath=WORK/'execution/CAMPAIGN_START_BJ.json'
    completepath=WORK/'results/CAMPAIGN_COMPLETE_BJ.json'
    stoppath=WORK/'results/CAMPAIGN_STOP_BJ.json'
    require(not any(p.exists() for p in [startpath,completepath,stoppath]),'No rerun or overwrite')
    for batch in range(1,13):
        require(not (WORK/'results'/f'batch{batch:02d}').exists(),'No existing batch output permitted')
        require(not (WORK/'execution'/f'batch{batch:02d}').exists(),'No existing batch capture permitted')
        require(not (WORK/'review'/f'batch{batch:02d}').exists(),'No existing batch audit permitted')
    start=time.perf_counter();started=utc();results=[]
    write(startpath,{'schema':'SETI_BJ_FINITE_CAMPAIGN_START_V1','started_utc':started,
                    'prereg_github_commit':prereg,'frozen_batch_count':12,
                    'frozen_q_list':list(range(25,121)),'input_source_plan_sha256':pins,
                    'per_search_timeout_seconds':620,'per_search_wrapper_alarm_seconds':600,
                    'per_audit_timeout_seconds':60,'retry_authorized':False,'new_archive_requests':0})
    try:
        for batch,planpath in enumerate(plans,1):
            verify_pins(pins);plan=read(planpath)
            out=WORK/'results'/f'batch{batch:02d}'/'run'
            capturefolder=WORK/'execution'/f'batch{batch:02d}'
            auditfolder=WORK/'review'/f'batch{batch:02d}'
            complete_result=out/'ALL_FROZEN_Q_COMPLETE.json'
            audit_result=auditfolder/'REAL_RESULT_AUDIT_BJ.json'
            event('BATCH_STARTED',batch=batch,q_list=plan['core_q_list'])
            command=['timeout','--signal=TERM','--kill-after=5s','620s',sys.executable,'-B',
                     str(wrapper),'--plan',str(planpath),'--out',str(out),'--all-q']
            searchpath,actual=capture(command,capturefolder,'SEARCH',wrapper,planpath,
                                     complete_result,prereg,batch)
            event('SEARCH_CLOSED',batch=batch,actual_exit_code=actual['actual_exit_code'],
                  wall_seconds=actual['wall_seconds'])
            require_closed_actual(actual)
            complete=read(complete_result)
            require(complete['q_list']==plan['core_q_list']
                    and complete['status']=='ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE',
                    'All-eight batch completion required')
            verify_pins(pins)
            command=['timeout','--signal=TERM','--kill-after=5s','60s',sys.executable,'-B',
                     str(auditor),'--plan',str(planpath),'--out',str(out),'--actual',str(searchpath),
                     '--receipt',str(audit_result)]
            auditpath,auditactual=capture(command,capturefolder,'REAL_RESULT_AUDIT',auditor,
                                         planpath,audit_result,prereg,batch)
            event('AUDIT_CLOSED',batch=batch,actual_exit_code=auditactual['actual_exit_code'],
                  wall_seconds=auditactual['wall_seconds'])
            require_closed_actual(auditactual);audit=read(audit_result)
            require_audit_gate(actual,audit,complete)
            verify_pins(pins)
            passing=sum(r['all3ON_ge10_noOFF_rows'] for r in complete['q_results'])
            entry={'batch':batch,'q_list':plan['core_q_list'],'search_actual_path':str(searchpath),
                   'search_actual_sha256':sha(searchpath),'audit_actual_path':str(auditpath),
                   'audit_actual_sha256':sha(auditpath),'audit_result_path':str(audit_result),
                   'audit_result_sha256':sha(audit_result),'complete_result_path':str(complete_result),
                   'complete_result_sha256':sha(complete_result),
                   'ON_catalog_rows':sum(r['ON_local_catalog_rows'] for r in complete['q_results']),
                   'passing_flags':passing,'total_track_trials':complete['total_track_trials']}
            write(capturefolder/'BATCH_CLOSED_BJ.json',entry);results.append(entry)
            require(passing==0,'Passing descriptive flag requires parent inspection; no next batch')
        require(len(results)==12 and sum(r['total_track_trials'] for r in results)==5196054528,
                'Finite campaign count differs')
        verify_pins(pins)
        result={'schema':'SETI_BJ_FINITE_CAMPAIGN_COMPLETION_V1',
                'status':'ALL_TWELVE_BATCHES_SEARCHED_AND_AUDITED','started_utc':started,
                'completed_utc':utc(),'wall_seconds':time.perf_counter()-start,
                'prereg_github_commit':prereg,'batch_results':results,'completed_batches':12,
                'q_list':list(range(25,121)),'total_track_trials':sum(r['total_track_trials'] for r in results),
                'input_source_plan_sha256':pins,'new_archive_requests':0,
                'background_science_jobs_running':False}
        write(completepath,result);event('CAMPAIGN_COMPLETE',completed_batches=12,
                                       total_track_trials=result['total_track_trials']);return 0
    except BaseException as exc:
        write(stoppath,{'schema':'SETI_BJ_FINITE_CAMPAIGN_STOP_V1','status':'STOPPED_NO_NEXT_BATCH',
                       'completed_utc':utc(),'prereg_github_commit':prereg,'completed_batches':len(results),
                       'batch_results':results,'reason':type(exc).__name__+': '+str(exc),
                       'wall_seconds':time.perf_counter()-start,'new_archive_requests':0,
                       'background_science_jobs_running':False})
        event('CAMPAIGN_STOPPED',completed_batches=len(results),reason=type(exc).__name__+': '+str(exc))
        return 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prereg-commit',required=True)
    args=parser.parse_args();return campaign(args.prereg_commit)

if __name__=='__main__':sys.exit(main())
