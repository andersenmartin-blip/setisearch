"""Run frozen shards once, with at most two concurrent child processes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime, hashlib, json, os, subprocess, sys, threading, time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
STOP=threading.Event()
LOCK=threading.Lock()

def event(value):
    value['time_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with LOCK:
        with (BASE/'QUEUE_EVENTS.jsonl').open('a') as f:
            f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
        print(json.dumps(value),flush=True)

def worker(job):
    if STOP.is_set():return {'job':job,'status':'NOT_ENTERED_AFTER_QUEUE_STOP'}
    args=json.loads((BASE/'PRIMARY_ARGS.json').read_text())
    logfile=BASE/(job+'.log')
    event({'job':job,'status':'ENTERED'})
    with logfile.open('x') as f:
        try:
            child=subprocess.run([sys.executable,str(BASE/'driver.py'),*args,'--job',job],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=930)
            code=child.returncode
        except subprocess.TimeoutExpired:code=-999
    path=BASE/'results'/job/'EXECUTION_RECEIPT.json'
    if code or not path.exists():
        STOP.set();value={'job':job,'status':'STOP_FAILED_SHARD_NO_RETRY','exit_code':code,'log':str(logfile.relative_to(ROOT))};event(value);return value
    receipt=json.loads(path.read_text())
    if receipt['status']!='COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY':
        STOP.set();value={'job':job,'status':'STOP_NONCOMPLETE_RECEIPT_NO_RETRY','exit_code':code};event(value);return value
    value={'job':job,'status':'COMPLETE','maps':receipt['counts']['maps'],'CPU_seconds':receipt['process_CPU_seconds'],'wall_seconds':receipt['wall_seconds'],'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest()};event(value);return value

def main():
    assert not (BASE/'QUEUE_EVENTS.jsonl').exists() and not (BASE/'QUEUE_RECEIPT.json').exists()
    jobs=json.loads((BASE/'PRIMARY_JOBS.json').read_text())
    jobs.sort(key=lambda j:(int(j.rsplit('shard',1)[1]),int(j.split('epoch',1)[1][0])))
    started=time.monotonic();event({'status':'QUEUE_STARTED','jobs':jobs,'max_concurrent':2,'automatic_retries':0})
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(worker,jobs))
    status='PASS_ALL21_SHARDS2010_NEW_MAPS' if all(r['status']=='COMPLETE' for r in results) else 'STOPPED_WITH_PRESERVED_FAILURE_NO_RETRY'
    receipt={'status':status,'jobs':results,'maps':sum(r.get('maps',0) for r in results),'wall_seconds':time.monotonic()-started,'max_concurrent':2,'automatic_retries':0}
    with (BASE/'QUEUE_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    event({'status':status,'maps':receipt['maps']})
    if status!='PASS_ALL21_SHARDS2010_NEW_MAPS':sys.exit(1)

if __name__=='__main__':main()
