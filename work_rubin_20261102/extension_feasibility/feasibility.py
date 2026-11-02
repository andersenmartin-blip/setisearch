"""Bounded metadata-only same-field extension feasibility; no science values."""
from pathlib import Path
import collections,concurrent.futures,csv,datetime,hashlib,json,math,socket,threading,time,urllib.error,urllib.parse,urllib.request
import numpy as np
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download=False
OUT=Path(__file__).resolve().parent;BASE=OUT.parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(),parse_int=str)
def dump(name,v):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def csvrows(p):return list(csv.DictReader(Path(p).open()))
def csvout(name,rs,keys=None):
 keys=keys or list(dict.fromkeys(k for r in rs for k in r))or['status']
 with(OUT/name).open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)
def exact(x):
 if not isinstance(x,str)or not x.isdigit()or not 0<int(x)<2**63:raise ValueError('Invalid exact positive64bitID')
 return x
def finite(x):
 try:return not isinstance(x,bool)and math.isfinite(float(x))
 except:return False
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class Budget:
 def __init__(self,total,per):self.total=total;self.per=per;self.charged=0;self.reserved=0;self.lock=threading.Lock()
 def reserve(self):
  with self.lock:
   if self.charged+self.reserved+self.per>self.total:return False
   self.reserved+=self.per;return True
 def close(self,n,unknown):
  with self.lock:
   self.reserved-=self.per;self.charged+=self.per if unknown else n;assert self.charged+self.reserved<=self.total

def load():
 p=json.loads((OUT/'PLAN.json').read_text())
 for f in p['frozen_sources']:assert sha(BASE/f['path'])==f['sha256'],f['path']
 assert p['script_sha256']==sha(Path(__file__))
 review=OUT/'independent_review/PREFLIGHT.json'
 assert review.exists(),'Independent preflight not yet recorded'
 r=json.loads(review.read_text());assert r.get('status','').startswith('PASS'),r
 assert r['plan_sha256']==sha(OUT/'PLAN.json')
 assert r['script_sha256']==sha(Path(__file__))
 assert p['analyzer_sha256']==sha(OUT/'analyze_metadata.py')
 return p

def request(job,limit,budget,allowed_keys,allowed_ids=None):
 logs=[]
 for attempt in range(1,3):
  started=json.loads((OUT/'CONE_STARTED.json').read_text())['utc']
  if (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(started)).total_seconds()>=7200:return {'job_id':job['job_id'],'status':'TWO_HOUR_DEADLINE_STOP','attempts':logs}
  if not budget.reserve():return {'job_id':job['job_id'],'status':'BUDGET_UNAVAILABLE','attempts':logs}
  record={'job_id':job['job_id'],'attempt':attempt,'started_utc':now(),'method':job['method'],'endpoint':job['endpoint'],'payload':job['payload']};body=b'';chunks=[];unknown=False;retry=False;error=None;status=None;rows=None
  try:
   if job['method']=='GET':url=job['endpoint']+'?'+urllib.parse.urlencode(job['payload']);req=urllib.request.Request(url,headers={'User-Agent':'Bounded Rubin metadata feasibility'})
   else:req=urllib.request.Request(job['endpoint'],data=json.dumps(job['payload']).encode(),method='POST',headers={'Content-Type':'application/json','User-Agent':'Bounded Rubin metadata feasibility'})
   try:response=urllib.request.build_opener(NoRedirect()).open(req,timeout=45)
   except urllib.error.HTTPError as e:response=e
   with response:
    status=response.status;record['headers']=dict(response.headers)
    if int(response.headers.get('Content-Length','0'))>=limit:raise ValueError('Declared response meets/exceeds cap; truncation stop')
    chunks=[];n=0
    while n<limit:
     block=response.read(min(65536,limit-n))
     if not block:break
     chunks.append(block);n+=len(block)
    body=b''.join(chunks)
    if len(body)>=limit:raise ValueError('Response meetsbytecap; truncation stop')
   if status!=200:error='HTTP'+str(status);retry=status in[500,502,503,504]
   else:
    rows=json.loads(body,parse_int=str)
    if not isinstance(rows,list):raise ValueError('Expected row list')
    for row in rows:
     if not isinstance(row,dict):raise ValueError('Nonobject row')
     unexpected=set(row)-set(allowed_keys)
     if unexpected:raise ValueError('Unexpected fields:'+','.join(sorted(unexpected)))
     oid=exact(row.get('r:diaObjectId'));exact(row.get('r:diaSourceId'))
     if allowed_ids is not None:
      if oid not in allowed_ids:raise ValueError('Out-of-request object')
      exact(row.get('r:visit'))
  except urllib.error.URLError as exc:error=repr(exc);unknown=True;retry=isinstance(exc.reason,(TimeoutError,socket.timeout,ConnectionResetError,ConnectionAbortedError,BrokenPipeError))
  except(TimeoutError,socket.timeout,ConnectionResetError,ConnectionAbortedError,BrokenPipeError)as exc:error=repr(exc);unknown=True;retry=True
  except Exception as exc:error=repr(exc);unknown=True;retry=False
  if chunks:body=b''.join(chunks)
  budget.close(len(body),unknown);record.update(http_status=status,complete=status==200 and error is None,error=error,bytes_saved=len(body),sha256=hashlib.sha256(body).hexdigest(),unknown_remaining_bytes=unknown,charged_bytes=limit if unknown else len(body))
  p=OUT/'attempts'/f'{job["job_id"]}_attempt{attempt:02}.body';p.parent.mkdir(exist_ok=True);p.write_bytes(body);record['path']=str(p.relative_to(OUT));dump(str(p.relative_to(OUT))+'.receipt.json',record);logs.append(record)
  print(job['job_id'],attempt,status,len(body),error,flush=True)
  if record['complete']:
   p=OUT/job['path'];p.parent.mkdir(exist_ok=True)
   with p.open('xb')as f:f.write(body)
   return {'job_id':job['job_id'],'status':'COMPLETE','rows':len(rows),'path':job['path'],'sha256':sha(p),'bytes':len(body),'returned_objects':sorted({r['r:diaObjectId']for r in rows},key=int),'attempts':logs}
  if not retry:break
 return {'job_id':job['job_id'],'status':'FAILED','attempts':logs}

def cone():
 plan=load();assert not(OUT/'CONE_STARTED.json').exists();dump('CONE_STARTED.json',{'utc':now(),'plan_sha256':sha(OUT/'PLAN.json')})
 job=plan['cone_job'];limit=3000000;budget=Budget(6000000,limit)
 result=request(job,limit,budget,plan['cone_allowed_response_keys']);result.update(charged_bytes=budget.charged,reserved_bytes=budget.reserved)
 if result['status']=='COMPLETE':
  rs=read(OUT/result['path']);n=len(rs);unique=len({r['r:diaObjectId']for r in rs})
  invalid=[];center_ra=math.radians(float(job['payload']['ra']));center_dec=math.radians(float(job['payload']['dec']))
  for r in rs:
   if not finite(r.get('r:ra'))or not finite(r.get('r:dec'))or not 0<=float(r['r:ra'])<360 or not -90<=float(r['r:dec'])<=90:invalid.append({'object_id':r['r:diaObjectId'],'reason':'INVALID_RA_DEC'});continue
   a=math.radians(float(r['r:ra']));d=math.radians(float(r['r:dec']));h=math.sin((d-center_dec)/2)**2+math.cos(d)*math.cos(center_dec)*math.sin((a-center_ra)/2)**2;sep=math.degrees(2*math.asin(math.sqrt(min(1,max(0,h)))))
   if sep>1+1e-9:invalid.append({'object_id':r['r:diaObjectId'],'reason':'OUTSIDE_FROZEN_ONE_DEGREE_FIELD','recomputed_separation_deg':sep})
  if invalid:result['status']='CONE_COORDINATE_VALIDATION_STOP';result['invalid_cone_coordinates']=invalid
  elif n>=5000 or unique>=5000 or n==100:result['status']='TRUNCATION_OR_N_SEMANTIC_LIMIT_STOP';result['stop_reason']='Reached5000row/objectcap or exactlyn100ambiguoussemantics'
  elif n!=unique:result['status']='REPEATED_OBJECT_IN_CONE_STOP';result['stop_reason']='No posthocrepresentative-selection rule'
  else:
   prior=csvrows(BASE/'access_pilot/DEVELOPMENT_SELECTION.csv')+csvrows(BASE/'access_pilot/MAIN_METADATA_CANDIDATES_UNMATCHED.csv');ids={r['r:diaObjectId']for r in prior};ra=np.deg2rad([float(r['r:ra'])for r in prior]);dec=np.deg2rad([float(r['r:dec'])for r in prior]);allout=[];pending=[]
   for r in sorted(rs,key=lambda x:int(x['r:diaObjectId'])):
    reasons=[];near=[]
    if r['r:diaObjectId']in ids:reasons.append('EXACT_INITIAL433_ID')
    if not finite(r.get('r:ra'))or not finite(r.get('r:dec')):reasons.append('INVALID_POSITION')
    else:
     a=math.radians(float(r['r:ra']));d=math.radians(float(r['r:dec']));h=np.sin((d-dec)/2)**2+np.cos(d)*np.cos(dec)*np.sin((a-ra)/2)**2;sep=np.rad2deg(2*np.arcsin(np.sqrt(np.clip(h,0,1))))*3600
     near=[prior[i]['r:diaObjectId']for i in np.where(sep<=2)[0]]
     if near:reasons.append('WITHIN_2_ARCSEC_INITIAL433_POSITION')
    out={**r,'near_initial_ids':';'.join(near),'exclusion_reasons':';'.join(reasons),'selected_for_history':False}
    allout.append(out)
    if not reasons:pending.append(out)
   chosen=pending[:1000]
   for i,r in enumerate(chosen,1):r.update(selected_for_history=True,history_selection_index=i)
   for r in pending[1000:]:r['exclusion_reasons']='BEYOND_FROZEN1000_ID_HISTORY_CAP'
   csvout('CONE_DISPOSITIONS.csv',allout);csvout('HISTORY_SELECTION.csv',chosen)
   result.update(initial433_exact_overlap=sum('EXACT_INITIAL433_ID'in r['exclusion_reasons']for r in allout),position_overlap=sum(bool(r['near_initial_ids'])for r in allout),new_distinct_eligible_pool=len(pending),history_selected=len(chosen),history_omitted_by_cap=max(0,len(pending)-1000))
   cols=','.join(plan['history_columns']);jobs=[]
   for start in range(0,len(chosen),100):
    selection=[r['r:diaObjectId']for r in chosen[start:start+100]];index=start//100+1
    jobs.append({'job_id':f'history_{index:02}','method':'POST','endpoint':'https://api.lsst.fink-portal.org/api/v1/sources','payload':{'diaObjectId':','.join(selection),'columns':cols,'output-format':'json'},'path':f'metadata/history_{index:02}.json','object_ids':selection})
   dump('HISTORY_JOBS.json',jobs);dump('HISTORY_SELECTION_FREEZE.json',{'utc':now(),'selection_sha256':sha(OUT/'HISTORY_SELECTION.csv'),'jobs_sha256':sha(OUT/'HISTORY_JOBS.json'),'ids':[r['r:diaObjectId']for r in chosen],'no_main_science_selection':True,'no_Gaia_or_flux_requested':True})
 dump('CONE_RESULT.json',result)

def history():
 plan=load();c=json.loads((OUT/'CONE_RESULT.json').read_text());assert c['status']=='COMPLETE',c['status'];freeze=json.loads((OUT/'HISTORY_SELECTION_FREEZE.json').read_text());assert sha(OUT/'HISTORY_SELECTION.csv')==freeze['selection_sha256'];assert sha(OUT/'HISTORY_JOBS.json')==freeze['jobs_sha256']
 jobs=json.loads((OUT/'HISTORY_JOBS.json').read_text());assert len(jobs)<=10;assert[j for x in jobs for j in x['object_ids']]==freeze['ids'];assert len(freeze['ids'])<=1000
 assert not(OUT/'HISTORY_STARTED.json').exists();dump('HISTORY_STARTED.json',{'utc':now(),'freeze_sha256':sha(OUT/'HISTORY_SELECTION_FREEZE.json')})
 budget=Budget(20000000,4000000)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda j:request(j,4000000,budget,plan['history_columns'],set(j['object_ids'])),jobs))
 dump('HISTORY_MANIFEST.json',{'utc':now(),'jobs':results,'charged_bytes':budget.charged,'reserved_bytes':budget.reserved,'all_jobs_complete':all(x['status']=='COMPLETE'for x in results),'selection_replacement':False})

if __name__=='__main__':
 import sys
 if sys.argv[1]=='cone':cone()
 elif sys.argv[1]=='history':history()
 else:raise ValueError('Use cone or history')
