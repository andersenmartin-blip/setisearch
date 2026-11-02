"""Exact header-plan reconciliation and network-free transport/control review."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,sys,tempfile,urllib.parse
from unittest.mock import patch
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];H=OUT.parent/'header_acquisition';M=OUT.parent/'metadata_search_v2'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(H/'PLAN.json');metadata_audit=read(OUT/'METADATA_V2_RESULT_AUDIT.json');scientific=read(OUT/'HEADER_CODE_REVIEW.json');checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
check('No header requests or release yet',not(H/'REQUEST_STARTED.json').exists() and not(H/'ROOT_RELEASE.json').exists() and not(H/'HEADER_RESULTS.json').exists())
check('Independent metadata results passed',metadata_audit['status']=='PASS_INDEPENDENT_AMENDED_METADATA_RESULTS')
for record in plan['inputs']:
    path=Path(record['path']);check('Portable input '+str(path),not path.is_absolute() and (ROOT/path).resolve().is_relative_to(ROOT))
    check('Exact input hash '+str(path),sha(ROOT/path)==record['sha256'])
for name,digest in plan['code_hashes'].items():check('Exact current code '+name,sha(H/name)==digest)
check('Scientific synthetic tests passed',scientific['cases_passed']==scientific['cases_total']==78 and not scientific['failed_cases'])
for name in ['header_tools.py','select_extremes.py']:check('Synthetic-reviewed scientific code unchanged '+name,scientific['inputs']['scientific_code_hashes'][name]==sha(H/name))
check('Exact independent latest-month IDs',[r['dp_id'] for r in plan['jobs']]==[r['dp_id'] for r in metadata_audit['independent_latest_calendar_month_number_choices']])
check('Exact month-number order',[r['month_number'] for r in plan['jobs']]==[1,5])
check('Actual two jobs only, one target',len(plan['jobs'])==2 and {r['target'] for r in plan['jobs']}=={'HD122640'})
candidates={r['dp_id']:r for r in read(M/'CANDIDATES.json')}
for job in plan['jobs']:
    original=candidates[job['dp_id']]
    check('Full exact selected metadata '+job['dp_id'],job['metadata']==original['metadata'] and job['source_file_ids']==original['source_file_ids'])
    check('Only exact text-header endpoint '+job['dp_id'],job['url']=='https://archive.eso.org/hdr?'+urllib.parse.urlencode({'DpId':job['dp_id']}))
check('Frozen request bounds',plan['limits']=={'max_jobs':24,'max_jobs_per_target':12,'timeout_seconds':30,'max_response_bytes':524288,'max_total_response_bytes':12582912,'attempts_per_job':1,'retries':0,'redirects':0})
check('No science arrays',plan['spectral_arrays_allowed'] is False and plan['primary_only_parser'] is True)
check('Root-directed strict descriptive gate',plan['payload_readiness_gate']['comparison']=='strictly greater than' and plan['payload_readiness_gate']['combined_span_km_s_threshold']==299792.458/115000)
baseline=read(OUT/'STATE_BASELINE_AUDIT.json')
for target,data in plan['existing_berv_benchmark'].items():
    source=baseline['targets'][target]
    check('All-existing300 BERV context '+target,data['existing_exposures']==source['epochs'] and data['minimum_berv_km_s']==source['berv_min_km_s'] and data['maximum_berv_km_s']==source['berv_max_km_s'])
draft=read(H/'drafts/before_relative_paths/PLAN.json')
check('Portability fix preserved exact jobs and scientific gates',all(plan[k]==draft[k] for k in plan if k not in ['created_utc','inputs','code_hashes']))

sys.path.insert(0,str(H))
spec=importlib.util.spec_from_file_location('header_fetch_under_review',H/'fetch_headers.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Response:
    def __init__(self,body=b'header',status=200,chunks=None):self.body=body;self.status=status;self.headers={'Content-Type':'text/plain'};self.chunks=chunks
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):
        if self.chunks is not None:
            if not self.chunks:return b''
            item=self.chunks.pop(0)
            if isinstance(item,Exception):raise item
            return item
        item,self.body=self.body[:n],self.body[n:];return item
def transport(name,response,cap=12582912,expected_complete=True,expected_error=False,expected_body=None):
    calls=[];timers=[]
    class Opener:
        def open(self,request,timeout):
            calls.append((request.full_url,timeout));return response
    with patch.object(mod.urllib.request,'build_opener',return_value=Opener()),patch.object(mod.signal,'signal'),patch.object(mod.signal,'setitimer',side_effect=lambda *args:timers.append(args)):
        body,receipt=mod.request_header(plan['jobs'][0],plan['limits'],cap)
    check(name+' single request',calls==[(plan['jobs'][0]['url'],30)])
    check(name+' full deadline armed and cleared',timers[0][1]==30 and timers[-1][1]==0)
    check(name+' bounded read',len(body)<=min(524288,cap))
    check(name+' completion/error disposition',receipt['complete']==expected_complete and bool(receipt['error'])==expected_error)
    check(name+' exact body hash',receipt['body_sha256']==hashlib.sha256(body).hexdigest())
    if expected_body is not None:check(name+' preserved bytes',body==expected_body)
transport('Valid small response',Response(),expected_body=b'header')
transport('Exact per-header cap',Response(b'x'*524288),expected_complete=False,expected_error=True,expected_body=b'x'*524288)
transport('Remaining aggregate budget caps read',Response(b'x'*101),cap=100,expected_complete=False,expected_error=True,expected_body=b'x'*100)
transport('HTTP failure never retried',Response(b'denied',403),expected_complete=True,expected_error=True,expected_body=b'denied')
transport('Redirect never followed',Response(b'redirect',302),expected_complete=True,expected_error=True)
transport('Partial bytes preserved on timeout',Response(chunks=[b'partial',TimeoutError('synthetic')]),expected_complete=False,expected_error=True,expected_body=b'partial')
check('Redirect handler denies follow',mod.NoRedirect().redirect_request(None,None,302,'',{},'https://invalid.example.test/never') is None)

def control(name,mode,expected_calls=0):
    with tempfile.TemporaryDirectory(prefix='header_control_',dir=OUT) as directory:
        mod.HERE=Path(directory)
        p=copy.deepcopy(plan)
        if mode=='absolute':p['inputs'][0]['path']=str(ROOT/p['inputs'][0]['path'])
        if mode=='escape':p['inputs'][0]['path']='../outside-repository'
        (mod.HERE/'PLAN.json').write_text(json.dumps(p))
        for filename in p['code_hashes']:(mod.HERE/filename).write_bytes((H/filename).read_bytes())
        if mode!='no-release':(mod.HERE/'ROOT_RELEASE.json').write_text(json.dumps({'approved':True,'plan_sha256':sha(mod.HERE/'PLAN.json'),'code_hashes':p['code_hashes']}))
        calls=[]
        def request(job,limits,remaining):
            calls.append(job['dp_id'])
            return b'header',{'http_status':403 if mode=='canary-http' else 200,'complete':True,'error':'denied' if mode=='canary-http' else None,'response_headers':{'Content-Type':'text/plain'}}
        def parse(body,mime):
            if mode=='canary-format':raise mod.HeaderError('synthetic format')
            return {},{'primary_only':True}
        with patch.object(mod,'request_header',side_effect=request),patch.object(mod,'parse_header_response',side_effect=parse),patch.object(mod,'check_identity',return_value={'status':'PENDING_MODE_COMPATIBILITY' if mode=='canary-validation' else 'PASS_RECORDED_BERV'}):
            try:mod.main();error=None
            except (ValueError,FileNotFoundError) as exc:error=exc
        check(name+' correct request count',len(calls)==expected_calls)
        if mode in ['no-release','absolute','escape']:check(name+' failed before marker',error is not None and not(mod.HERE/'REQUEST_STARTED.json').exists())
        else:
            results=read(mod.HERE/'HEADER_RESULTS.json')
            check(name+' all jobs explicitly accounted',len(results['results'])==2 and results['requests_attempted']==expected_calls)
            if expected_calls==1:check(name+' later job not requested',results['results'][1]['status']=='NOT_REQUESTED_BATCH_STOPPED')
            with patch.object(mod,'request_header',side_effect=request):
                try:mod.main()
                except FileExistsError:check(name+' replay blocked',True)
                else:check(name+' replay blocked',False)
control('No release','no-release')
control('Absolute input path rejected','absolute')
control('Escaping input path rejected','escape')
control('Canary HTTP failure halts batch','canary-http',1)
control('Canary format failure halts batch','canary-format',1)
control('Canary identity/mode failure halts batch','canary-validation',1)
control('Successful bounded two-job flow','success',2)
mod.HERE=H
check('No actual header marker after synthetic tests',not(H/'REQUEST_STARTED.json').exists() and not(H/'HEADER_RESULTS.json').exists())
report={'status':'PASS_FINAL_EXACT_HEADER_PLAN_PREFLIGHT','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'plan_sha256':sha(H/'PLAN.json'),'code_hashes':plan['code_hashes'],
        'exact_job_ids':[r['dp_id'] for r in plan['jobs']],'actual_fixed_jobs':2,'absolute_ceiling_jobs':24,
        'input_hashes':plan['inputs'],'metadata_result_audit_sha256':sha(OUT/'METADATA_V2_RESULT_AUDIT.json'),
        'scientific_code_review_sha256':sha(OUT/'HEADER_CODE_REVIEW.json'),'auditor_script_sha256':sha(Path(__file__)),
        'network_requests_by_review':0,'actual_headers_read':0,'science_arrays_read':0,'labels_changed':0,
        'limitations':['Header rendering remains to be tested by the frozen canary. Unexpected format stops without a payload fallback.',
                      'BERV ranges describe only passing inspected headers, not all archive observations.',
                      'Combined span>c/R is a prospective operational displacement gate, not origin classification or statistical power.',
                      'Units, air/vacuum convention and full event-window compatibility remain pending separate payload-header checks before any arrays.'],
        'release_state':'No remaining independent preflight blocker. Exact-byte publication/root release required before these two header requests.'}
(OUT/'HEADER_PLAN_PREFLIGHT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'plan_sha256':report['plan_sha256']}))
