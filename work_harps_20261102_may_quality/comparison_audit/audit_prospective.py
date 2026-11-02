"""Prospective one-product May comparison guards; no new observational arrays/network."""
from pathlib import Path
import ast,copy,datetime,hashlib,importlib.util,io,json,math,shutil,sys,tempfile
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];B=R/'work_harps_20261102_may_quality';P=B/'comparison';O=Path(__file__).resolve().parent;PRIOR=R/'work_harps_20261102_berv_followup/prospective_comparison'
checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def function(path,name):return ast.dump(next(x for x in ast.parse(path.read_text()).body if isinstance(x,ast.FunctionDef)and x.name==name),include_attributes=False)
def main():
 start={'plan':sha(P/'PLAN.json'),'code':sha(P/'compare_verified_epoch.py')};plan=read(P/'PLAN.json');prior=read(PRIOR/'PLAN.json')
 for rel,digest in plan['source_hashes'].items():ck(sha(R/rel)==digest,'Bound source '+rel)
 ck(plan['frames']==prior['frames']and plan['sampling']==prior['sampling']and plan['implementation']==prior['implementation'],'Inherited frames/profile/correlation/statistics unchanged')
 ck(function(P/'compare_verified_epoch.py','inspect_payload_headers')==function(PRIOR/'compare_verified_epochs.py','inspect_payload_headers'),'Previously audited complete header-before-data function unchanged')
 ck(function(P/'compare_verified_epoch.py','verified_original_module')==function(PRIOR/'compare_verified_epochs.py','verified_original_module'),'Original method import/hash verifier unchanged; guarded original main not invoked')
 oldast=ast.parse((PRIOR/'compare_verified_epochs.py').read_text());newast=ast.parse((P/'compare_verified_epoch.py').read_text())
 oldmain=next(n for n in oldast.body if isinstance(n,ast.FunctionDef)and n.name=='main');newmain=next(n for n in newast.body if isinstance(n,ast.FunctionDef)and n.name=='main')
 def processing_loop(tree):return next(n for n in tree.body if isinstance(n,ast.For)and isinstance(n.target,ast.Tuple)and[x.id for x in n.target.elts]==['item','inspection'])
 ck(ast.dump(processing_loop(oldmain),include_attributes=False)==ast.dump(processing_loop(newmain),include_attributes=False),'Entire frame/profile/metric/correlation processing loop unchanged')
 events=read(P/'EVENTS.json');ids=['V2E2-0229','V2E2-0231','V2E2-0234','V2E2-0235','V2E2-0236','V2E2-0237','V2E2-0303','V2E2-0305','V2E2-0308','V2E2-0309'];ck([e['candidate_id']for e in events]==ids==plan['preserved_queue_ids'],'Exact10 preserved queue IDs')
 ck(sum(e['target']=='HD122640'for e in events)==6 and plan['expected_profile_slots']==12 and plan['HD135204_new_epoch_slots']==0,'Exact6x2 slots and4 uncovered records')
 ck(plan['header_displacement_gate']['absolute_delta_km_s_at_least']==10*299792.458/115000,'Ten-resolution-element per-discovery BERV prerequisite frozen')
 receipt=read(P/'EXISTING_REFERENCE_RECEIPT.json');ck(len(receipt['restored'])==20,'Exactly20 preserved discovery references')
 for ref in receipt['restored']:ck(sha(P/ref['path'])==ref['sha256']==sha(PRIOR/ref['path']),'Copied reference byte identity '+ref['path'])
 spec=importlib.util.spec_from_file_location('may_runner_guard_review',P/'compare_verified_epoch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 method,reference=m.verified_original_module();ck(method.C==299792.458 and len(method.X)==201,'Frozen method constants; no original main call')
 with tempfile.TemporaryDirectory(prefix='synthetic_',dir=O)as td:
  d=Path(td);rel=lambda p:str(p.relative_to(R));dp='ADP.2017-05-21T01:01:50.278';raw='HARPS.2017-05-20T02:21:45.847';body=d/'body';body.write_bytes(b'SYNTHETIC HEADER ONLY');hreceipt=d/'receipt';write(hreceipt,{'synthetic':True});payload=d/'payload';payload.write_bytes(b'SIMPLE  = SYNTHETIC NOT OBSERVATIONAL');preceipt=d/'payloadreceipt';write(preceipt,{'synthetic':True})
  header={'target':'HD122640','dp_id':dp,'job_index':0,'body_path':body.name,'body_sha256':sha(body),'receipt_path':hreceipt.name,'receipt_sha256':sha(hreceipt),'inspection':{'status':'PASS_RECORDED_BERV','berv_km_s':-10.,'raw_progenitor_ids':[raw],'primary_header':{}}}
  selected={'target':'HD122640','dp_id':dp,'berv_km_s':-10.,'header_result_job_index':0,'source_file_ids':[raw]}
  inp={'target':'HD122640','dp_id':dp,'status':'COMPLETE','local_path':rel(payload),'bytes':payload.stat().st_size,'sha256':sha(payload),'acquisition_receipt_path':rel(preceipt),'acquisition_receipt_sha256':sha(preceipt)}
  def fixture(h=None,s=None,i=None,extra=None,extra_headers=None,extra_selected=None):
   h=copy.deepcopy(header if h is None else h);s=copy.deepcopy(selected if s is None else s);i=copy.deepcopy(inp if i is None else i)
   hp=d/'HEADERS.json';write(hp,{'results':[h]+(extra_headers or [])});sp=d/'SELECT.json';write(sp,{'selected':[s]+(extra_selected or []),'header_results_sha256':sha(hp)});ap=d/'ACQUIRE.json';write(ap,{'inputs':[i]})
   release={'schema':'HARPS_MAY_QUALITY_COMPARISON_RELEASE_V1','publication_commit':'a'*40,'publication_readback_verified':True,'comparison_script_sha256':sha(P/'compare_verified_epoch.py'),'prospective_plan_sha256':sha(P/'PLAN.json'),'candidate_path':plan['candidate_path'],'candidate_sha256':plan['candidate_sha256'],'inputs':[i]}
   for key,path in [('selection',sp),('header_results',hp),('acquisition_manifest',ap)]:release[key+'_path']=rel(path);release[key+'_sha256']=sha(path)
   if extra:release.update(extra)
   rp=d/'RELEASE.json';write(rp,release);return rp
  rp=fixture();_,inputs,_=m.validate_release(rp);ck(len(inputs)==1 and inputs[0]['dp_id']==dp,'Exact single prospective candidate release accepted')
  def reject(path,label):
   try:m.validate_release(path)
   except (ValueError,KeyError):ck(True,label)
   else:raise AssertionError('Accepted invalid release '+label)
  for key,value in [('schema','HARPS_BERV_COMPARISON_RELEASE_V1'),('publication_readback_verified',False),('publication_commit','bad'),('comparison_script_sha256','0'*64),('prospective_plan_sha256','0'*64),('candidate_sha256','0'*64),('selection_sha256','0'*64),('header_results_sha256','0'*64),('acquisition_manifest_sha256','0'*64)]:reject(fixture(extra={key:value}),'Reject release '+key)
  reject(fixture(extra_headers=[header]),'Reject duplicate header slot');reject(fixture(extra_selected=[selected]),'Reject expanded candidate selection')
  for field,value in [('target','HD135204'),('dp_id','ADP.2017-05-23T01:01:52.459'),('source_file_ids',['HARPS.WRONG'])]:
   s=copy.deepcopy(selected);s[field]=value;reject(fixture(s=s),'Reject selected '+field)
  for status in ['FAILED','NOT_ATTEMPTED']:
   i=dict(inp,status=status,reason='synthetic acquisition failure');_,got,_=m.validate_release(fixture(i=i));ck(got[0]['status']==status,'Retain selected failed status '+status)
  reject(fixture(i=dict(inp,status='UNKNOWN')),'Reject unknown acquired status')
  reject(fixture(i=dict(inp,bytes=True)),'Reject boolean acquired byte count');reject(fixture(i=dict(inp,sha256='0'*64)),'Reject changed acquired bytes');reject(fixture(i=dict(inp,acquisition_receipt_sha256='0'*64)),'Reject changed acquired receipt')
  for value in [True,float('nan'),float('inf')]:
   h=copy.deepcopy(header);h['inspection']['berv_km_s']=value;reject(fixture(h=h),'Reject nonnumeric/nonfinite recorded BERV '+str(value))
  threshold=10*299792.458/115000;low=min(e['discovery_berv_km_s']for e in events if e['target']=='HD122640')-threshold;high=max(e['discovery_berv_km_s']for e in events if e['target']=='HD122640')+threshold
  for value,shouldpass,label in [(low,True,'inclusive negative-side boundary'),(low-1e-6,True,'above displacement lower side'),(low+1e-6,False,'one discovery below lower-side requirement'),(high+1e-6,True,'above displacement upper side'),(high-1e-6,False,'one discovery below upper-side requirement')]:
   h=copy.deepcopy(header);h['inspection']['berv_km_s']=value;s=dict(selected,berv_km_s=value);rp=fixture(h=h,s=s)
   if shouldpass:m.validate_release(rp);ck(True,'BERV gate '+label)
   else:reject(rp,'BERV gate '+label)
  h=copy.deepcopy(header);h['inspection']['raw_progenitor_ids']=['HARPS.2017-05-22T05:20:05.415'];reject(fixture(h=h),'Reject previous May raw exposure substitution')
  # All-blocked execution of the new wrapper: no FITS open or synthetic science data.
  run=d/'blocked';run.mkdir();shutil.copy(P/'EVENTS.json',run/'EVENTS.json');shutil.copy(P/'PLAN.json',run/'PLAN.json');shutil.copytree(P/'inputs',run/'inputs');rp=run/'RELEASE.json';write(rp,{'synthetic':True});blocked=dict(inp,status='NOT_ATTEMPTED',reason='synthetic stop')
  with patch.object(m,'HERE',run),patch.object(m,'verified_original_module',return_value=(method,reference)),patch.object(m,'validate_release',return_value=({'synthetic':True},[blocked],{})),patch.object(m.fits,'open',side_effect=AssertionError('Blocked input must not open FITS')),patch.object(sys,'argv',['audit','--release',str(rp)]),patch('sys.stdout',new=io.StringIO()):m.main()
  summary=read(run/'results/SUMMARY.json');er=read(run/'results/EVENT_RESULTS.json');rows=read(run/'results/ALL_COMPARISON_MEASUREMENTS.json')
  ck(summary['status']=='ALL_SELECTED_SLOTS_BLOCKED_NO_NEW_COMPARISON'and summary['frame_slots']==summary['blocked_profiles']==12 and summary['measured_profiles']==0,'All12 selected blocked slots remain explicit without claimed science')
  ck(summary['events']==10 and summary['discovery_references_reused']==20 and len(er)==10,'All10 records20references retained')
  ck([e['candidate_id']for e in er if all(e['frames'][f]['selected_epoch_slots']==0 for f in ['barycentric','topocentric'])]==ids[6:],'Exact4 HD135204 uncovered records retained')
  ck(summary['phase']=='POST_HOC_MAY_QUALITY_FOLLOWUP'and summary['prior_24_profile_run_replaced']is False and summary['original100_rerun']is False,'Distinct posthoc phase without old-run replacement')
  ck(summary['origin_assignments']==summary['repeat_classifications']==summary['U_labels_changed']==0 and all(r['classification_changed']is False for r in rows),'No classifier or label changes')
 ck(start=={'plan':sha(P/'PLAN.json'),'code':sha(P/'compare_verified_epoch.py')},'Reviewed code/plan stable throughout audit')
 for rel,digest in plan['source_hashes'].items():ck(sha(R/rel)==digest,'Preserved source after audit '+rel)
 result={'status':'PASS_PROSPECTIVE_SINGLE_MAY_COMPARISON_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'check_labels':checks,'comparison_plan_sha256':start['plan'],'comparison_script_sha256':start['code'],'exact_candidate':plan['exact_candidate'],'source_hashes_verified':len(plan['source_hashes']),'cached_reference_profiles_verified':20,'network_requests':0,'new_observational_arrays_read':0,'old_comparisons_rerun':False,'synthetic_case':'Blocked one-product execution only; no synthetic FITS array was read.','independent_math_sha256':sha(O/'independent_math.py'),'audit_script_sha256':sha(Path(__file__)),'limitations':['Actual header, acquisition manifest, publication release and new payload compatibility remain to be verified when produced.','Actual numerical reconstruction is prepared separately and must wait for root comparison release and completed run.','Posthoc quality selection and geometric BERV threshold are not an origin classifier or sensitivity calibration.']}
 with(O/'PROSPECTIVE_COMPARISON_AUDIT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in result.items()if k!='check_labels'},indent=2))
if __name__=='__main__':main()
