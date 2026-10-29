"""Run exactly the single six-scan AZ compute pool, preserving child byte logs."""
from pathlib import Path
import datetime,hashlib,json,os,sys
from capture_pool_az import run_capture_pool
W=Path(__file__).resolve().parent.parent;B=W/'work_az';E=B/'execution'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 E.mkdir(exist_ok=True);protocol=B/'PROTOCOL_BOUND_AZ.json';p=read(protocol)
 assert read(B/'ROOT_DETECTOR_RELEASE_AZ.json')['protocol_sha256']==sha(protocol)
 assert not (E/'SCAN_POOL_EXECUTION_AZ.json').exists()
 def guard():
  for rel,digest in p['source_sha256'].items():assert sha(W/rel)==digest,rel
 def closed(r):
  x=dict(r,actual_exit_code=r['exit_code'],protocol_sha256=sha(protocol));new(E/f"scan{r['scan']}_ACTUAL_EXIT.json",x)
  print(json.dumps(dict(scan=r['scan'],actual_exit_code=r['exit_code'])),flush=True)
 commands=[(j,[sys.executable,'-B','-u',str(B/'detector/run_av.py'),'scan',str(protocol),str(B/'results'),str(j)]) for j in range(6)]
 records=run_capture_pool(commands,E,max_workers=6,sample_interval=1.,guard=guard,on_closed=closed)
 assert len(records)==6 and all(r['exit_code']==0 for r in records)
 new(E/'SCAN_POOL_EXECUTION_AZ.json',dict(status='ALL_SIX_SCANS_CLOSED',exits=records,protocol_sha256=sha(protocol),single_heavy_compute_pool=True,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 print('ALL_SIX_SCANS_CLOSED',flush=True)
if __name__=='__main__':main()
