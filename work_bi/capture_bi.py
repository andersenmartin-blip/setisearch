"""Capture a bounded BI child through EOF and wait, preserving real exit status."""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['search','audit']);p.add_argument('--prereg-commit',required=True);a=p.parse_args()
    if a.mode=='search':
        label='SEARCH';folder=ROOT/'work_bi/execution';script=ROOT/'work_bi/bounded_search_bi.py'
        command=['timeout','--signal=TERM','--kill-after=5s','620s',sys.executable,'-B',str(script),'--plan',str(ROOT/'work_bi/PLAN_BI.json'),'--out',str(ROOT/'work_bi/results/run'),'--all-q']
        result=ROOT/'work_bi/results/run/ALL_FROZEN_Q_COMPLETE.json'
    else:
        label='REAL_RESULT_AUDIT';folder=ROOT/'work_bi/review';script=folder/'audit_real_results_bi.py'
        command=['timeout','--signal=TERM','--kill-after=5s','60s',sys.executable,'-B',str(script),'--plan',str(ROOT/'work_bi/PLAN_BI.json'),'--out',str(ROOT/'work_bi/results/run'),'--actual',str(ROOT/'work_bi/execution/SEARCH_ACTUAL_EXIT_BI.json'),'--receipt',str(folder/'REAL_RESULT_AUDIT_BI.json')]
        result=folder/'REAL_RESULT_AUDIT_BI.json'
    folder.mkdir(parents=True,exist_ok=True);log=folder/(label+'_BI.log');actual=folder/(label+'_ACTUAL_EXIT_BI.json')
    write(folder/(label+'_START_BI.json'),{'command':command,'started_utc':datetime.now(timezone.utc).isoformat(),'prereg_github_commit':a.prereg_commit,'source_sha256':digest(script),'plan_sha256':digest(ROOT/'work_bi/PLAN_BI.json')})
    prior=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter();observed=hashlib.sha256();n=0
    with log.open('xb') as stream:
        child=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        while True:
            chunk=child.stdout.read(65536)
            if not chunk:break
            n+=len(chunk);observed.update(chunk);stream.write(chunk);stream.flush()
        code=child.wait()
    end=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt={'schema':'SETI_BI_ACTUAL_'+label+'_EXIT_V1','completed_utc':datetime.now(timezone.utc).isoformat(),'command':command,'source_sha256':digest(script),'plan_sha256':digest(ROOT/'work_bi/PLAN_BI.json'),'prereg_github_commit':a.prereg_commit,'actual_exit_code':code,'child_pid':child.pid,'stdout_eof':True,'child_wait_completed':True,'wall_seconds':time.perf_counter()-start,'child_user_cpu_seconds':end.ru_utime-prior.ru_utime,'child_system_cpu_seconds':end.ru_stime-prior.ru_stime,'max_child_RSS_KiB':end.ru_maxrss,'log_path':str(log),'log_bytes':log.stat().st_size,'log_sha256':digest(log),'observed_stdout_bytes':n,'observed_stdout_sha256':observed.hexdigest(),'result_path':str(result),'result_sha256':digest(result) if result.exists() else None,'new_archive_requests':0}
    write(actual,receipt);print(json.dumps(receipt),flush=True)
    return code
if __name__=='__main__':sys.exit(main())
