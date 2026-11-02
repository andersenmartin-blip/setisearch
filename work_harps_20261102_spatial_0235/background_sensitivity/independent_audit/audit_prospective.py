"""Focused source/synthetic review; never loads observational arrays."""
import ast,datetime,hashlib,importlib.util,json,math
from pathlib import Path
import sys,tempfile
from unittest.mock import patch
import numpy as np
import independent_math as ref
OUT=Path(__file__).resolve().parent;B=OUT.parent;ROOT=B.parents[1]
checks=[];scalars=0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ck(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
def same(a,b):
 global scalars
 if isinstance(b,dict):return set(a)==set(b)and all(same(a[k],v)for k,v in b.items())
 if isinstance(b,(str,bool))or b is None:return a==b
 if isinstance(b,list)and b and isinstance(b[0],dict):return len(a)==len(b)and all(same(x,y)for x,y in zip(a,b))
 aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float);scalars+=aa.size
 return aa.shape==bb.shape and np.allclose(aa,bb,rtol=2e-10,atol=2e-10,equal_nan=True)
def function(path,name):return next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)and n.name==name)
def main():
 plan=read(B/'PLAN.json');code=B/'run_sensitivity.py';old=B.parent/'analysis'
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Bound source '+p)
 ck(plan['estimators']==['negative_side','positive_side']and plan['input_limits']['new_native_pixels']==plan['input_limits']['raw_FITS_reads']==0,'Exactly two backgrounds on saved footprint')
 original=function(old/'measure_spatial.py','window_metrics');new=function(code,'window_metrics');new.args.args.pop()
 for node in ast.walk(new):
  if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id=='fit_row':node.args.pop()
 ck(ast.dump(original)==ast.dump(new),'Original aggregation unchanged except explicit estimator forwarding')
 spec=importlib.util.spec_from_file_location('sensitivity_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
 train,windows=ref.partition();ck(prod.coordinates()==(train,windows),'Exact unchanged232/88/11 row partition')
 rows=sorted(set(train)|set(sum(windows.values(),[])));idx={r:i for i,r in enumerate(rows)}
 centers={r:2300.23+.0007*r for r in rows}
 strips={r:[40+.01*r+230*math.exp(-.5*((round(centers[r])+j-centers[r])/1.45)**2)+.25*math.sin(j+r)+(6 if j>=9 else 0)for j in range(-12,13)]for r in rows}
 strips[0][17]+=25;raw=np.array([strips[r]for r in rows]);cc=np.array([centers[r]for r in rows])
 for estimator,side in [('negative_side',-1),('positive_side',1)]:
  t,disp,detail=prod.train(raw,cc,train,idx,estimator);rt,rd,rdi=ref.templates(strips,centers,train,side)
  ck(same(t,rt['pooled'])and same(disp,rd)and same(detail,rdi['pooled']),'Independent signed training '+estimator)
  for name,rr in windows.items():
   metrics,records,arrays=prod.window_metrics(name,rr,raw,cc,t,idx,estimator);rm,rrs,ra=ref.window(name,rr,strips,centers,rt['pooled'],side)
   ck(same(metrics,rm)and same(records,rrs),'Independent window/rows '+estimator+'/'+name)
   ck(same(arrays['model'],[x[2]for x in ra])and same(arrays['residual'],[x[3]for x in ra]),'Independent model/residual '+estimator+'/'+name)
  bad=np.full_like(raw,20.);bt,bd,bdetail=prod.train(bad,cc,train,idx,estimator)
  ck(bt is None and len(bd)==232 and all(r['status']=='UNUSABLE'for r in bd)and bdetail['status']=='BLOCKED_INSUFFICIENT_TRAINING','All invalid training retained '+estimator)
  try:prod.row_geometry(np.ones(25),2300.,estimator)
  except ValueError:ck(True,'Non-three-pixel side rejected '+estimator)
  else:raise AssertionError('Integer geometry accepted')
 with patch.object(sys,'argv',['run_sensitivity.py']),patch.object(prod.np,'load',side_effect=AssertionError('Observational load before explicit execute')):
  try:prod.main()
  except SystemExit:ck(True,'Default refuses before array loading')
  else:raise AssertionError('Default execution permitted')
 # Temporary publication records exercise guards without requests or array reads.
 with tempfile.TemporaryDirectory(prefix='release_fixture_',dir=OUT)as temporary:
  tmp=Path(temporary);required=[B/'PLAN.json',code,B/'README.md']
  rec=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)
  fp=tmp/'freeze.json';fp.write_text(json.dumps({'files':{str(p.relative_to(ROOT)):rec(p)for p in required}}))
  pub=tmp/'publication.json';pub.write_text(json.dumps({'status':'PASS_EXACT_REMOTE_READBACK','commit':'a'*40,'files':[rec(p)for p in [fp,*required]]}))
  release=dict(schema='HARPS_SPATIAL0235_BACKGROUND_SENSITIVITY_RELEASE_V1',approved=True,publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(B/'PLAN.json'),script_sha256=sha(code),freeze_path=str(fp.relative_to(ROOT)),freeze_sha256=sha(fp),publication_receipt_path=str(pub.relative_to(ROOT)),publication_receipt_sha256=sha(pub))
  rp=tmp/'release.json';rp.write_text(json.dumps(release));prod.validate(rp);ck(True,'Exact synthetic release contract accepted')
  for key,bad in [('approved',False),('publication_readback_verified',False),('publication_commit','bad'),('plan_sha256','0'*64),('script_sha256','0'*64),('freeze_sha256','0'*64),('publication_receipt_sha256','0'*64)]:
   rp.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(rp)
   except ValueError:ck(True,'Release guard rejects '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Source preserved '+p)
 report={'status':'PASS_FOCUSED_PROSPECTIVE_BACKGROUND_SENSITIVITY_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'synthetic_scalar_values_compared':scalars,'check_labels':checks,'plan_sha256':sha(B/'PLAN.json'),'script_sha256':sha(code),'independent_helper_sha256':sha(OUT/'independent_math.py'),'audit_script_sha256':sha(Path(__file__)),'observational_arrays_loaded':0,'raw_FITS_reads':0,'network_requests':0,'scope':'Exactly negative-side and positive-side three-pixel medians; same232 training rows,one pooled template per estimator,all18 windows/198 row slots; original window aggregation unchanged.','source_review_findings':['Both outer medians are retained independently of selected background.','Both estimators and failures are retained; no best-estimator selection.','Exact selected-NPZ/source hashes and public freeze/readback are required before explicit execution.','Blocked windows retain all11 blocked row placeholders and raw/coordinate maps.','Control comparisons remain descriptive; no probability, significance or origin classifier.'],'limitation':'Actual reconstruction waits for root completed-run signal; this preflight uses only metadata, source bytes and analytic synthetic pixels.'}
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))
if __name__=='__main__':main()
