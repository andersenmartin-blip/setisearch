"""One parent-owned byte-stream capture; no retries or science logic."""
from pathlib import Path
import datetime,hashlib,json,os,sys,time
from capture_pool_az import run_capture_pool,CapturePoolFailure
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main(review=False):
 args=sys.argv[1:];name,receipt=args[:2];args=args[2:]
 result=args.pop(0) if review else None
 assert args.pop(0)=='--' and args
 p=Path(receipt).resolve();p.parent.mkdir(parents=True,exist_ok=True)
 folder=p.parent/(p.stem+'_capture');assert not p.exists() and not folder.exists()
 started=utc();clock=time.monotonic();failure=None
 try:records=run_capture_pool([(0,args)],folder,max_workers=1,sample_interval=.1)
 except CapturePoolFailure as exc:records=exc.records;failure=exc.failure
 assert len(records)==1,'Exactly one closed child record is required'
 child=records[0];code=child['exit_code']
 if failure is not None and code==0:code=1
 log=Path(child['log']);assert sha(log)==child['log_sha256'] and log.stat().st_size==child['log_bytes']
 record=dict(child,phase=name,actual_exit_code=code,child_actual_exit_code=child['exit_code'],command=args,cwd=str(Path.cwd()),started_utc=started,completed_utc=utc(),wall_seconds=time.monotonic()-clock,automatic_retry=False,capture_failure=failure,background_jobs_running=False)
 if result is not None:
  resultpath=Path(result).resolve();record.update(result_path=str(resultpath),result_sha256=sha(resultpath) if resultpath.is_file() else None)
 with p.open('x') as f:json.dump(record,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(record),flush=True);print(log.read_text(errors='replace')[-5000:],flush=True)
 return code
