"""At most8 raw+8 ancillary downloads after root verifies code/selection publication."""
import argparse,concurrent.futures,threading,time,urllib.request,os,tarfile,io,subprocess
from common import *
p=argparse.ArgumentParser();p.add_argument('--published-commit',required=True);p.add_argument('--published-freeze-sha256',required=True);args=p.parse_args()
plan=verify_plan();freeze=verify_freeze();proof=publication(args.published_commit,args.published_freeze_sha256)
require(not(OUT/'products/MANIFEST.json').exists()and not(OUT/'DOWNLOAD_STARTED.json').exists(),'Acquisition already started; no implicit restart or replacement')
jobs=read('JOBS.json');require(len(jobs)<=16 and len({j['dp_id']for j in jobs})<=8,'Product cap exceeded');require(all(j['metadata_status']=='VERIFIED'for j in jobs),'Unverified product metadata')
cap=plan['acquisition_bounds']['payload_cap_bytes'];require(sum(j['advertised_bytes']for j in jobs)<=cap,'Preflight payload estimate exceeds cap')
(OUT/'products').mkdir(exist_ok=True);dump('DOWNLOAD_STARTED.json',dict(started_utc=now(),publication=proof,payload_cap_bytes=cap,workers=3,max_attempts=2))
lock=threading.Lock();returned=0;reserved=0;started=time.monotonic()
def get(job):
 global returned,reserved
 receipt=dict(**job,attempts=[],status='FAILED');path=OUT/'products'/job['filename'];part=path.with_name(path.name+'.part')
 require(not path.exists()and not part.exists(),'Existing product cannot be replaced')
 for timeout in [20,60]:
  began=time.monotonic();n=0
  try:
   with urllib.request.urlopen(job['url'],timeout=timeout)as response:
    require(response.status==200 and response.geturl()==job['url'],'Unexpected product status/redirect')
    require(int(response.headers.get('Content-Length','-1'))==job['advertised_bytes'],'Changed product length since metadata freeze')
    require(job['archive_id']in response.headers.get('Content-Disposition',''),'Changed archive identity')
    with part.open('xb')as stream:
     while n<job['advertised_bytes']:
      with lock:
       allowance=min(1048576,job['advertised_bytes']-n,cap-returned-reserved)
       require(allowance>0,'GLOBAL_PAYLOAD_CAP_EXHAUSTED');reserved+=allowance
      try:block=response.read(allowance)
      except Exception as error:
       partial=getattr(error,'partial',b'');partial=partial if isinstance(partial,bytes)else b''
       with lock:reserved-=allowance;returned+=len(partial);require(returned<=cap,'Payload ledger overflow')
       n+=len(partial);raise
      with lock:reserved-=allowance;returned+=len(block);require(returned<=cap,'Payload ledger overflow')
      n+=len(block);require(bool(block),'Truncated response');stream.write(block)
   require(n==job['advertised_bytes'],'Payload size mismatch')
   # Verify container and metadata before making a product usable. All payload values remain uninspected here.
   from astropy.io import fits
   if job['kind']=='RAW':
    require(part.read_bytes()[:2]in[b'\x1f\x9d',b'\x1f\x8b'],'Unrecognized compressed raw magic')
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(part)],check=True,capture_output=True).stdout),memmap=False)as h:
     require(h[0].header['ARCFILE'].removesuffix('.fits')==job['raw_id'],'Raw ARCFILE mismatch');require(h[0].header['DATE-OBS']==job['source_date_obs'],'Raw DATE mismatch');require(h[0].header['INSTRUME']=='HARPS','Wrong instrument');require(len(h)>=3,'Raw extensions missing')
   else:
    with tarfile.open(part)as archive:
     members=[m for m in archive if m.name.endswith('_e2ds_A.fits')];require(len(members)==1,'Missing/ambiguous e2ds_A')
     with fits.open(io.BytesIO(archive.extractfile(members[0]).read()),memmap=False)as h:require(h[0].header['DATE-OBS']==job['source_date_obs'],'Ancillary DATE mismatch')
   digest=sha(part);part.rename(path);receipt.update(status='DOWNLOADED',bytes=n,sha256=digest,relative_path=str(path.relative_to(BASE)),metadata_check='PASS_RAW_OR_NATIVE_ID_DATE_AND_CONTAINER');receipt['attempts'].append(dict(outcome='SUCCESS',timeout_seconds=timeout,returned_payload_bytes=n,elapsed_seconds=time.monotonic()-began));break
  except Exception as e:
   if part.exists():part.unlink()
   receipt['attempts'].append(dict(outcome='FAILED',timeout_seconds=timeout,returned_payload_bytes=n,elapsed_seconds=time.monotonic()-began,error=repr(e)))
   if 'GLOBAL_PAYLOAD_CAP_EXHAUSTED'in str(e):break
 dump('products/'+job['filename']+'.json',receipt);print(job['dp_id'],job['kind'],receipt['status'],flush=True);return receipt
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:results=list(pool.map(get,jobs))
verify_freeze();require(returned<=cap,'Payload cap exceeded')
dump('products/MANIFEST.json',dict(created_utc=now(),publication=proof,total_returned_payload_bytes=returned,payload_cap_bytes=cap,reserved_bytes_final=reserved,elapsed_seconds=time.monotonic()-started,products=results,replacements=0))
print('COMPLETE',sum(r['status']=='DOWNLOADED'for r in results),len(results),returned)
