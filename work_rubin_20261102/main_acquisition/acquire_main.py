#!/usr/bin/env python3
"""Acquire frozen Rubin identities only after root's matching publication release."""
import concurrent.futures,csv,datetime,hashlib,json,socket,threading,time,urllib.error,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def exact_id(value):
    if not isinstance(value,str) or not value.isdigit() or not 0<int(value)<2**63:
        raise ValueError(f'Invalid exact positive64bit identity: {value!r}')
    return value

def validate_rows(data,allowed,endpoint):
    rows=json.loads(data,parse_int=str)
    if not isinstance(rows,list):raise ValueError('Expected JSON row list')
    key='r:diaForcedSourceId' if endpoint.endswith('/fp') else 'r:diaSourceId'
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Expected row object')
        if exact_id(row.get('r:diaObjectId')) not in allowed:raise ValueError('Out-of-selection object')
        exact_id(row.get(key));exact_id(row.get('r:visit'))
    return rows

def load_plan():
    plan=json.loads((P/'PLAN.json').read_text())
    if sha(P/plan['selection_snapshot'])!=plan['selection_sha256']:raise ValueError('Selection hash mismatch')
    with (P/plan['selection_snapshot']).open() as f:selection=list(csv.DictReader(f))
    ids=[exact_id(r['diaObjectId']) for r in selection]
    if ids!=plan['selected_ids'] or len(set(ids))!=len(ids) or len(ids)!=plan['objects']:raise ValueError('Selection mismatch')
    for stream in ('sources','fp'):
        jobs=[j for j in plan['jobs'] if j['endpoint'].endswith('/'+stream)]
        if [i for j in jobs for i in j['object_ids']]!=ids:raise ValueError('Job coverage differs')
        for j in jobs:
            if j['payload']['diaObjectId']!=','.join(j['object_ids']):raise ValueError('Request identity mismatch')
            if j['endpoint']!='https://api.lsst.fink-portal.org/api/v1/'+stream:raise ValueError('Unapproved endpoint')
            if Path(j['canonical_path']).is_absolute() or '..' in Path(j['canonical_path']).parts:raise ValueError('Unsafe output path')
    return plan

def validate_release(plan):
    release=json.loads((P/'ROOT_RELEASE.json').read_text())
    if release.get('publication_readback_verified') is not True:raise ValueError('Root publication readback missing')
    for key,value in [('selection_sha256',plan['selection_sha256']),('acquisition_plan_sha256',sha(P/'PLAN.json')),('acquisition_script_sha256',sha(Path(__file__)))]:
        if release.get(key)!=value:raise ValueError('Release mismatch:'+key)
    if len(release.get('publication_commit',''))!=40 or len(release.get('method_sha256',''))!=64:raise ValueError('Publication/method hashes missing')
    method=P/release.get('method_path','../method_review/MAIN_METHOD_FREEZE.json')
    if not method.is_file() or sha(method)!=release['method_sha256']:raise ValueError('Frozen method file mismatch')
    return release

class Budget:
    def __init__(self,total,request_limit):self.total=total;self.request_limit=request_limit;self.charged=0;self.reserved=0;self.lock=threading.Lock()
    def reserve(self):
        with self.lock:
            if self.charged+self.reserved+self.request_limit>self.total:return False
            self.reserved+=self.request_limit;return True
    def close(self,bytes_read,unknown):
        with self.lock:
            self.reserved-=self.request_limit
            self.charged+=self.request_limit if unknown else bytes_read
            assert self.charged+self.reserved<=self.total
            return self.charged

def acquire(job,plan,budget):
    limit=plan['limits']['maximum_response_bytes'];receipts=[];rows=[]
    for attempt in range(1,plan['limits']['maximum_attempts_per_job']+1):
        if not budget.reserve():
            return {'job_id':job['job_id'],'status':'BUDGET_NOT_AVAILABLE','object_ids':job['object_ids'],'attempts':receipts}
        start=now();clock=time.monotonic();chunks=[];size=0;status=None;headers={};error=None;unknown=False;retry=False
        body=json.dumps(job['payload']).encode();request=urllib.request.Request(job['endpoint'],data=body,method='POST',headers={'Content-Type':'application/json','User-Agent':'Bounded Rubin archival science sample'})
        try:
            try:response=urllib.request.urlopen(request,timeout=plan['limits']['timeout_seconds'])
            except urllib.error.HTTPError as exc:response=exc
            with response:
                status=response.status;headers=dict(response.headers)
                content_length=int(headers.get('Content-Length','0'))
                if content_length>limit:raise ValueError('Declared response exceeds fixed byte limit')
                while size<limit:
                    chunk=response.read(min(65536,limit-size))
                    if not chunk:break
                    chunks.append(chunk);size+=len(chunk)
                if size==limit:raise ValueError('Response filled byte limit; completeness unknown')
            if status!=200:
                error=f'HTTP {status}';retry=status in (500,502,503,504)
            else:rows=validate_rows(b''.join(chunks),set(job['object_ids']),job['endpoint'])
        except (TimeoutError,socket.timeout,urllib.error.URLError,ConnectionError) as exc:
            error=repr(exc);unknown=True;retry=True
        except Exception as exc:
            error=repr(exc);unknown=True;retry=False
        charge=budget.close(size,unknown)
        payload=b''.join(chunks);path=P/'attempts'/f'{job["job_id"]}_attempt{attempt:02}.body';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
        receipt={'job_id':job['job_id'],'attempt':attempt,'started_utc':start,'elapsed_seconds':time.monotonic()-clock,'endpoint':job['endpoint'],'payload':job['payload'],'http_status':status,'headers':headers,'bytes_saved':len(payload),'sha256':sha(path),'path':str(path.relative_to(P)),'complete':status==200 and error is None,'error':error,'unknown_remaining_response_bytes':unknown,'charged_bytes':limit if unknown else len(payload),'total_charged_at_completion':charge}
        path.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
        print(json.dumps({k:receipt[k] for k in ('job_id','attempt','http_status','bytes_saved','complete','error')}),flush=True)
        if receipt['complete']:
            canonical=P/job['canonical_path'];canonical.parent.mkdir(parents=True,exist_ok=True)
            with canonical.open('xb') as f:f.write(payload)
            return {'job_id':job['job_id'],'status':'COMPLETE','object_ids':job['object_ids'],'returned_objects':sorted({r['r:diaObjectId'] for r in rows},key=int),'rows':len(rows),'canonical_path':job['canonical_path'],'sha256':sha(canonical),'bytes':len(payload),'attempts':receipts}
        if not retry:break
        time.sleep(1)
    return {'job_id':job['job_id'],'status':'FAILED','object_ids':job['object_ids'],'attempts':receipts}

def main():
    plan=load_plan();release=validate_release(plan)
    with (P/'STARTED.json').open('x') as f:json.dump({'started_utc':now(),'plan_sha256':sha(P/'PLAN.json'),'release':release},f,indent=2)
    budget=Budget(plan['limits']['total_returned_byte_budget'],plan['limits']['maximum_response_bytes'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=plan['limits']['maximum_workers']) as pool:
        results=list(pool.map(lambda job:acquire(job,plan,budget),plan['jobs']))
    manifest={'schema':'RUBIN_MAIN_ACQUISITION_MANIFEST_V1','completed_utc':now(),'objects_selected':plan['objects'],'jobs':results,'charged_bytes':budget.charged,'reserved_bytes':budget.reserved,'all_jobs_complete':all(r['status']=='COMPLETE' for r in results),'new_selection_or_replacement':False,'scientific_analysis_run':False,'publication_commit':release['publication_commit']}
    (P/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    availability=[]
    for oid in plan['selected_ids']:
        record={'diaObjectId':oid}
        for stream in ('sources','fp'):
            result=next(r for r in results if r['job_id'].startswith(stream+'_') and oid in r['object_ids'])
            record[stream+'_status']='RETURNED' if oid in result.get('returned_objects',[]) else 'EMPTY_FOR_OBJECT' if result['status']=='COMPLETE' else result['status']
        availability.append(record)
    with (P/'OBJECT_AVAILABILITY.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,list(availability[0]));w.writeheader();w.writerows(availability)
    print(json.dumps({k:v for k,v in manifest.items() if k!='jobs'},indent=2))

if __name__=='__main__':main()
