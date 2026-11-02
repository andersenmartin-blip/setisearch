"""At most one raw + one ancillary downloads after root verifies code/selection publication."""
import argparse,concurrent.futures,time,tarfile,io,subprocess,urllib.error
from transfer_guards import PayloadLedger,bounded_read,no_redirect_opener,close_http_error,PayloadCapError
from common import *

def open_no_redirect(url,timeout):return no_redirect_opener().open(url,timeout=timeout)

def make_receipt(job):
 # HEAD metadata already contains attempts; preserve it separately from payload attempts.
 return {**job,'metadata_attempts':job.get('attempts',[]),'attempts':[],'status':'FAILED'}

def validate_product(path,job,science_header):
 from astropy.io import fits
 if job['kind']=='RAW':
  with path.open('rb')as stream:magic=stream.read(2)
  require(magic in[b'\x1f\x9d',b'\x1f\x8b'],'Unrecognized compressed raw magic')
  with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(path)],check=True,capture_output=True).stdout),memmap=False)as h:
   require(h[0].header['ARCFILE'].removesuffix('.fits')==job['raw_id'],'Raw ARCFILE mismatch')
   require(h[0].header['DATE-OBS']==job['source_date_obs'],'Raw DATE mismatch')
   require(h[0].header['INSTRUME']=='HARPS','Wrong instrument');require(len(h)>=3,'Raw extensions missing')
 else:
  with tarfile.open(path)as archive:
   members=[m for m in archive if m.name.endswith('_e2ds_A.fits')];require(len(members)==1,'Missing/ambiguous e2ds_A')
   with fits.open(io.BytesIO(archive.extractfile(members[0]).read()),memmap=False)as h:
    verify_native_identity(h[0].header,members[0].name,job,science_header)

def download_product(job,ledger,science_header,product_dir,base,open_fn=open_no_redirect,validate_fn=validate_product):
 receipt=make_receipt(job);path=product_dir/job['filename'];part=path.with_name(path.name+'.part')
 require(not path.exists()and not part.exists(),'Existing product cannot be replaced')
 for timeout in [20,60]:
  began=time.monotonic();n=0;attempt=dict(timeout_seconds=timeout,known_returned_payload_bytes=0,charged_payload_bytes=0)
  try:
   with open_fn(job['url'],timeout)as response:
    require(response.status==200 and response.geturl()==job['url'],'Unexpected product status/redirect')
    require(int(response.headers.get('Content-Length','-1'))==job['advertised_bytes'],'Changed product length since metadata freeze')
    require(job['archive_id']in response.headers.get('Content-Disposition',''),'Changed archive identity')
    with part.open('xb')as stream:
     while n<job['advertised_bytes']:
      block=bounded_read(response,min(1048576,job['advertised_bytes']-n),ledger,attempt)
      n+=len(block);require(bool(block),'Truncated response');stream.write(block)
   require(n==job['advertised_bytes'],'Payload size mismatch');validate_fn(part,job,science_header)
   digest=sha(part);part.rename(path)
   receipt.update(status='DOWNLOADED',bytes=n,sha256=digest,relative_path=str(path.relative_to(base)),metadata_check='PASS_RAW_OR_NATIVE_ID_DATE_AND_CONTAINER')
   attempt.update(outcome='SUCCESS',elapsed_seconds=time.monotonic()-began);receipt['attempts'].append(attempt);break
  except Exception as error:
   close_http_error(error)
   if part.exists():part.unlink()
   attempt.update(outcome='FAILED',elapsed_seconds=time.monotonic()-began,error=repr(error));receipt['attempts'].append(attempt)
   if isinstance(error,PayloadCapError)or(isinstance(error,urllib.error.HTTPError)and error.code in(401,403)):break
 return receipt

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--published-commit',required=True);parser.add_argument('--published-freeze-sha256',required=True);args=parser.parse_args()
 plan=verify_plan();verify_freeze();proof=publication(args.published_commit,args.published_freeze_sha256)
 require(not(OUT/'products/MANIFEST.json').exists()and not(OUT/'DOWNLOAD_STARTED.json').exists(),'Acquisition already started; no implicit restart or replacement')
 jobs=read('JOBS.json');bounds=plan['acquisition_bounds']
 require(len(jobs)<=bounds['max_raw_products']+bounds['max_ancillary_products']and len({j['dp_id']for j in jobs})<=plan['selection_rule']['max_unique_exposures'],'Product cap exceeded')
 require(sum(j['kind']=='RAW'for j in jobs)<=bounds['max_raw_products']and sum(j['kind']=='ANCILLARY'for j in jobs)<=bounds['max_ancillary_products'],'Per-kind product cap exceeded')
 require(len({j['filename']for j in jobs})==len(jobs),'Repeated product filename')
 for dp in {j['dp_id']for j in jobs}:require(sorted(j['kind']for j in jobs if j['dp_id']==dp)==['ANCILLARY','RAW'],'Incomplete or repeated product pair')
 require(all(j['url']=='https://dataportal.eso.org/dataPortal/file/'+j['archive_id']and isinstance(j['advertised_bytes'],int)and j['advertised_bytes']>0 for j in jobs),'Unexpected frozen URL or byte count')
 require(all(j['metadata_status']=='VERIFIED'for j in jobs),'Unverified product metadata')
 cap=plan['acquisition_bounds']['payload_cap_bytes'];require(sum(j['advertised_bytes']for j in jobs)<=cap,'Preflight payload estimate exceeds cap')
 science={r['dp_id']:r['primary_header']for r in json.loads((EXT/'acquisition/DOWNLOAD_MANIFEST.json').read_text())}
 # Validate job receipt construction and file paths before the one-shot acquisition marker.
 product_dir=OUT/'products'
 for job in jobs:
  make_receipt(job);require(not(product_dir/job['filename']).exists()and not(product_dir/(job['filename']+'.part')).exists(),'Existing product cannot be replaced')
 product_dir.mkdir(exist_ok=True);dump('DOWNLOAD_STARTED.json',dict(started_utc=now(),publication=proof,payload_cap_bytes=cap,workers=1,max_attempts=2,ledger='Failed reads consume their full reserved allowance; known-returned and charged bytes are separate.'))
 ledger=PayloadLedger(cap);started=time.monotonic()
 def get(job):
  receipt=download_product(job,ledger,science[job['dp_id']],product_dir,BASE)
  dump('products/'+job['filename']+'.json',receipt);print(job['dp_id'],job['kind'],receipt['status'],flush=True);return receipt
 with concurrent.futures.ThreadPoolExecutor(max_workers=1)as pool:results=list(pool.map(get,jobs))
 verify_freeze();totals=ledger.snapshot();require(totals['charged_payload_bytes']<=cap and totals['reserved_bytes']==0,'Payload ledger invariant failed')
 dump('products/MANIFEST.json',dict(created_utc=now(),publication=proof,**totals,elapsed_seconds=time.monotonic()-started,products=results,replacements=0))
 print('COMPLETE',sum(r['status']=='DOWNLOADED'for r in results),len(results),totals)
if __name__=='__main__':main()
