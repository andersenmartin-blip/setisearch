"""Offline guard tests; no network calls or science payload downloads."""
import concurrent.futures,contextlib,email.message,http.client,io,json,tempfile,urllib.error,urllib.request
from pathlib import Path
from transfer_guards import *
from acquire import make_receipt,download_product
from common import verify_native_identity,OUT,now,sha
passed=[]
def record(name):passed.append(name)
class ReadTrap:
 def __init__(self):self.reads=0;self.closed=False
 def read(self,*args):self.reads+=1;raise AssertionError('Rejected HTTP response body must not be read')
 def close(self):self.closed=True
for status in [301,302,303,307,308]:
 trap=ReadTrap();headers=email.message.Message();headers['Location']='https://example.invalid/other';opener=no_redirect_opener();req=urllib.request.Request('https://example.invalid/source')
 try:opener.error('http',req,trap,status,'Redirect',headers)
 except urllib.error.HTTPError as error:close_http_error(error)
 else:raise AssertionError('Redirect accepted')
 assert trap.reads==0 and trap.closed
record('all_five_redirect_statuses_rejected_without_body_read')
ledger=PayloadLedger(10);a=ledger.reserve(8);b=ledger.reserve(8);assert(a,b)==(8,2)
try:ledger.reserve(1)
except PayloadCapError:pass
else:raise AssertionError('Over-reservation accepted')
ledger.finish(a,8,False);ledger.finish(b,2,False);assert ledger.snapshot()['charged_payload_bytes']==10
record('concurrent_outstanding_reservations_cannot_exceed_cap')
class Broken:
 def __init__(self,error):self.error=error
 def read(self,n):raise self.error
for error,known in [(TimeoutError('unknown read progress'),0),(http.client.IncompleteRead(b'abc',8),3)]:
 ledger=PayloadLedger(8);attempt=dict(known_returned_payload_bytes=0,charged_payload_bytes=0)
 try:bounded_read(Broken(error),8,ledger,attempt)
 except type(error):pass
 assert ledger.snapshot()==dict(payload_cap_bytes=8,charged_payload_bytes=8,known_returned_payload_bytes=known,unknown_bytes_conservatively_charged=8-known,reserved_bytes=0)
 assert attempt['charged_payload_bytes']==8 and attempt['known_returned_payload_bytes']==known
record('unknown_and_partial_read_failures_charge_full_reservation')
ledger=PayloadLedger(67)
def worker():
 while True:
  attempt=dict(known_returned_payload_bytes=0,charged_payload_bytes=0)
  try:bounded_read(io.BytesIO(b'x'*9),9,ledger,attempt)
  except PayloadCapError:return
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:list(pool.map(lambda _:worker(),range(3)))
assert ledger.snapshot()['charged_payload_bytes']==67 and ledger.snapshot()['reserved_bytes']==0
record('three_workers_exhaust_exact_shared_cap_without_overshoot')
job=dict(dp_id='TEST',archive_id='TEST',raw_id='HARPS.TEST',url='https://example.invalid/TEST',filename='TEST.bin',kind='ANCILLARY',advertised_bytes=5,attempts=[dict(outcome='HEAD_SUCCESS')],source_date_obs='2026-01-01T00:00:00')
receipt=make_receipt(job);assert receipt['metadata_attempts']==job['attempts']and receipt['attempts']==[]
record('HEAD_attempts_preserved_separately_without_duplicate_keyword_error')
actual_jobs=json.loads((OUT/'JOBS.json').read_text()) if(OUT/'JOBS.json').exists()else[]
assert len(actual_jobs)<=64 and len({j['filename']for j in actual_jobs})==len(actual_jobs)
for actual in actual_jobs:
 receipt=make_receipt(actual)
 assert receipt['attempts']==[]and receipt['metadata_attempts']==actual['attempts']and receipt['archive_id']==actual['archive_id']
 assert receipt['advertised_bytes']==actual['advertised_bytes']and receipt['status']=='FAILED'
record('actual_frozen_JOBS_construct_valid_independent_payload_receipts_count_'+str(len(actual_jobs)))
class FakeResponse:
 status=200
 def __init__(self,data=b'abcde',error=None,wrong_length=False):self.data=io.BytesIO(data);self.error=error;self.closed=False;self.reads=0;self.headers={'Content-Length':'6'if wrong_length else'5','Content-Disposition':'attachment; filename="TEST.bin"'}
 def geturl(self):return job['url']
 def read(self,n):
  self.reads+=1
  if self.error:raise self.error
  return self.data.read(n)
 def __enter__(self):return self
 def __exit__(self,*args):self.closed=True
with tempfile.TemporaryDirectory(dir=OUT,prefix='offline_guards_')as root:
 root=Path(root);prod=root/'success';prod.mkdir();response=FakeResponse();ledger=PayloadLedger(20)
 receipt=download_product(job,ledger,{},prod,root,open_fn=lambda *_:response,validate_fn=lambda *_:None)
 assert receipt['status']=='DOWNLOADED'and len(receipt['attempts'])==1 and response.closed and (prod/'TEST.bin').read_bytes()==b'abcde'
 assert ledger.snapshot()['charged_payload_bytes']==5
 record('mock_successful_download_constructs_receipt_validates_and_renames')
 prod=root/'retry';prod.mkdir();responses=[FakeResponse(error=TimeoutError('unknown progress')),FakeResponse()];ledger=PayloadLedger(10)
 receipt=download_product(job,ledger,{},prod,root,open_fn=lambda *_:responses.pop(0),validate_fn=lambda *_:None)
 assert receipt['status']=='DOWNLOADED'and len(receipt['attempts'])==2 and ledger.snapshot()['charged_payload_bytes']==10 and ledger.snapshot()['known_returned_payload_bytes']==5
 record('mock_failed_read_and_retry_consume_conservative_shared_budget')
 prod=root/'reject';prod.mkdir();bad=[FakeResponse(wrong_length=True),FakeResponse(wrong_length=True)];queue=list(bad)
 receipt=download_product(job,PayloadLedger(20),{},prod,root,open_fn=lambda *_:queue.pop(0),validate_fn=lambda *_:None)
 assert receipt['status']=='FAILED'and len(receipt['attempts'])==2 and all(r.closed and r.reads==0 for r in bad)and not list(prod.iterdir())
 record('metadata_mismatch_closes_response_without_payload_read_or_partial_product')
 prod=root/'http_error';prod.mkdir();traps=[ReadTrap(),ReadTrap()];queue=list(traps)
 def error_open(*_):raise urllib.error.HTTPError(job['url'],500,'error',{},queue.pop(0))
 receipt=download_product(job,PayloadLedger(20),{},prod,root,open_fn=error_open,validate_fn=lambda *_:None)
 assert receipt['status']=='FAILED'and all(r.closed and r.reads==0 for r in traps)
 record('HTTPError_responses_closed_without_body_read')
for denied_status in [401,403]:
 with tempfile.TemporaryDirectory(dir=OUT,prefix='offline_denied_')as root:
  root=Path(root);prod=root/'denied';prod.mkdir();trap=ReadTrap();calls=[]
  def denied_open(*_):
   calls.append(1)
   raise urllib.error.HTTPError(job['url'],denied_status,'denied',{},trap)
  ledger=PayloadLedger(20)
  receipt=download_product(job,ledger,{},prod,root,open_fn=denied_open,validate_fn=lambda *_:None)
  assert receipt['status']=='FAILED'and len(calls)==1 and len(receipt['attempts'])==1 and trap.closed and trap.reads==0 and not list(prod.iterdir())and ledger.snapshot()['charged_payload_bytes']==0
record('HTTP401_and403_terminal_without_retry_body_read_or_partial_file')
import prepare_selection
original_head_opener=prepare_selection.no_redirect_opener
try:
 for denied_status in [401,403]:
  trap=ReadTrap();calls=[]
  class DeniedHeadOpener:
   def open(self,request,timeout):
    calls.append(request.get_method())
    raise urllib.error.HTTPError(job['url'],denied_status,'denied',{},trap)
  prepare_selection.no_redirect_opener=lambda:DeniedHeadOpener()
  result=prepare_selection.head(job)
  assert result['metadata_status']=='FAILED'and len(result['attempts'])==1 and calls==['HEAD']and trap.closed and trap.reads==0
finally:prepare_selection.no_redirect_opener=original_head_opener
record('HEAD_HTTP401_and403_terminal_without_retry_or_body_read')
header={'INSTRUME':'HARPS','DATE-OBS':job['source_date_obs'],'OBJECT':'HD 123','ESO DRS BERV':12.3};science={'OBJECT':'HD123','HIERARCH ESO DRS BERV':12.3}
assert verify_native_identity(header,'folder/HARPS.TEST_e2ds_A.fits',job,science)
for field,badvalue in [('INSTRUME','OTHER'),('DATE-OBS','OTHER'),('OBJECT','HD999'),('ESO DRS BERV',float('nan')),('ESO DRS BERV',15.0)]:
 bad={**header,field:badvalue}
 try:verify_native_identity(bad,'HARPS.TEST_e2ds_A.fits',job,science)
 except RuntimeError:pass
 else:raise AssertionError('Invalid native header accepted')
try:verify_native_identity(header,'OTHER_e2ds_A.fits',job,science)
except RuntimeError:pass
else:raise AssertionError('Wrong raw parent member accepted')
record('native_parent_instrument_target_date_BERV_identity_guards')
result=dict(created_utc=now(),tests_passed=len(passed),tests=passed,actual_frozen_jobs_verified=len(actual_jobs),jobs_file_present=(OUT/'JOBS.json').exists(),network_calls=0,science_payload_downloads=0,script_sha256=sha(Path(__file__)),guards_sha256=sha(OUT/'transfer_guards.py'),acquire_sha256=sha(OUT/'acquire.py'))
(OUT/'GUARD_TEST_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
