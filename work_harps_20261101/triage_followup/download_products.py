"""Bounded public download of the ten original-hit raw and ancillary products."""
from pathlib import Path
import csv,json,hashlib,urllib.request,time,concurrent.futures,threading,datetime
BASE=Path(__file__).resolve().parent.parent;OUT=BASE/'triage_followup/products';OUT.mkdir(parents=True,exist_ok=True)
total=0;lock=threading.Lock();cap=500_000_000
def get(r):
 global total
 p=OUT/r['filename'];receipt=dict(**r,attempts=[])
 for timeout in [20,60]:
  start=time.monotonic()
  try:
   with urllib.request.urlopen(r['url'],timeout=timeout) as h:
    blocks=[];size=0
    while True:
     block=h.read(1048576)
     if not block:break
     size+=len(block)
     with lock:
      total+=len(block)
      if total>cap:raise RuntimeError('Total500MBcap')
     if size>30_000_000:raise RuntimeError('File30MBcap')
     blocks.append(block)
   data=b''.join(blocks);p.write_bytes(data)
   receipt.update(status='DOWNLOADED',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),relative_path=str(p.relative_to(BASE)),magic_hex=data[:8].hex())
   receipt['attempts'].append(dict(timeout=timeout,outcome='SUCCESS',seconds=time.monotonic()-start));break
  except Exception as e:
   receipt['attempts'].append(dict(timeout=timeout,outcome='FAILED',error=repr(e)));receipt['status']='FAILED'
 (OUT/(r['filename']+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:receipt[k] for k in ['filename','status']}),flush=True)
 return receipt
jobs=[]
hits=list(csv.DictReader((BASE/'production/HIT_DISPOSITIONS.csv').open()))
for hit in hits:
 raw=json.loads(hit['raw_progenitor_ids'])[0]
 jobs.append(dict(hit_id=hit['hit_id'],dp_id=hit['dp_id'],kind='RAW',url='https://dataportal.eso.org/dataPortal/file/'+raw,filename=raw.replace(':','_')+'.fits.Z'))
for r in csv.DictReader((BASE/'triage_followup/ancillary_metadata.csv').open()):
 if r['extension']=='TAR':
  hit=next(h for h in hits if h['dp_id']==r['product_id'])
  jobs.append(dict(hit_id=hit['hit_id'],dp_id=r['product_id'],kind='ANCILLARY',url=r['access_url'],filename=r['archive_id'].replace(':','_')+'.tar'))
assert len(jobs)==20
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:res=list(pool.map(get,jobs))
(OUT/'MANIFEST.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),total_transferred_bytes=total,products=res),indent=2)+'\n')
