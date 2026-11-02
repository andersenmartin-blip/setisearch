"""Independent two-estimator reconstruction using the exact saved pixel matrix."""
import argparse,csv,datetime,hashlib,json,math
from pathlib import Path
import numpy as np
import independent_math as ref
OUT=Path(__file__).resolve().parent;B=OUT.parent;ROOT=B.parents[1];RESULT=B/'results'
checks=[];differences=[];scalars=0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ck(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
def same(a,b,label,kind='metric'):
 global scalars
 if isinstance(b,dict):
  if set(a)!=set(b):return False
  return all(same(a[k],v,label+'/'+k,kind)for k,v in b.items())
 if isinstance(b,(str,bool))or b is None:return a==b
 if isinstance(b,list)and b and isinstance(b[0],dict):return len(a)==len(b)and all(same(x,y,label+'/'+str(i),kind)for i,(x,y)in enumerate(zip(a,b)))
 aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float);scalars+=aa.size
 if aa.shape!=bb.shape or not np.allclose(aa,bb,rtol=5e-10,atol=5e-9,equal_nan=True):return False
 valid=np.isfinite(aa)&np.isfinite(bb);error=float(np.max(np.abs(aa[valid]-bb[valid])))if valid.any()else 0.
 differences.append(dict(name=label,kind=kind,scalar_values=int(aa.size),maximum_absolute_difference=error));return True
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorized-after-root-run',action='store_true');args=parser.parse_args()
 if not args.authorized_after_root_run:raise SystemExit('Root completed-run signal and flag required before saved observational arrays.')
 plan=read(B/'PLAN.json');release=read(B/'ROOT_RELEASE.json');summary=read(RESULT/'SUMMARY.json');output_hashes=read(RESULT/'OUTPUT_HASHES.json')
 ck(release['schema']=='HARPS_SPATIAL0235_BACKGROUND_SENSITIVITY_RELEASE_V1'and release['approved']is True and release['publication_readback_verified']is True,'Released exact phase')
 ck(release['plan_sha256']==sha(B/'PLAN.json')and release['script_sha256']==sha(B/'run_sensitivity.py')and summary['release_sha256']==sha(B/'ROOT_RELEASE.json'),'Release/plan/code/result bindings')
 ck(sha(ROOT/release['freeze_path'])==release['freeze_sha256']and sha(ROOT/release['publication_receipt_path'])==release['publication_receipt_sha256'],'Published freeze/receipt bindings')
 ck(read(ROOT/release['publication_receipt_path'])['commit']==release['publication_commit'],'Publication commit identity')
 for name,digest in plan['source_hashes'].items():ck(sha(ROOT/name)==digest,'Bound source '+name)
 for name,digest in output_hashes.items():ck(sha(RESULT/name)==digest,'Production result '+name)
 oldroot=B.parent/'analysis/results';oldhashes=read(oldroot/'OUTPUT_HASHES.json')
 for name,digest in oldhashes.items():ck(sha(oldroot/name)==digest,'Original result before audit '+name)
 input_path=ROOT/plan['selected_pixels_path'];input_hash=sha(input_path)
 training,windows=ref.partition();allrows=sorted(set(training)|set(sum(windows.values(),[])))
 with np.load(input_path,allow_pickle=False)as saved:
  ck(np.array_equal(saved['relative_raw_rows'],allrows)and np.array_equal(saved['absolute_raw_rows'],np.array(allrows)+3139)and np.array_equal(saved['training_relative_rows'],training),'Unchanged saved row partition')
  raw=saved['raw_adu'].copy();centers_array=saved['trace_columns'].copy();cols=saved['stitched_columns'].copy()
  ck(raw.shape==(331,25)and np.array_equal(cols,np.rint(centers_array).astype(int)[:,None]+np.arange(-12,13))and np.array_equal(saved['chip2_columns'],cols-2048+50),'Exact unchanged8275-pixel geometry')
 strips={r:raw[i].tolist()for i,r in enumerate(allrows)};centers={r:float(centers_array[i])for i,r in enumerate(allrows)};column_map={r:cols[i].tolist()for i,r in enumerate(allrows)}
 wanted_metrics=[];wanted_rows=[];wanted_arrays={};wanted_templates={};wanted_details={};wanted_dispositions={}
 for estimator,side in [('negative_side',-1),('positive_side',1)]:
  templates,dispositions,details=ref.templates(strips,centers,training,side);template=templates.get('pooled')
  wanted_templates[estimator]=template;wanted_details[estimator]=details['pooled'];wanted_dispositions[estimator]=dispositions
  for name,rr in windows.items():
   d=[[c-centers[r]for c in column_map[r]]for r in rr]
   maps=dict(raw=[strips[r]for r in rr],true_crossdisp_offsets=d,fit_mask=[[abs(x)<=8 for x in row]for row in d],background_mask=[[9<=abs(x)<=12 and side*x>0 for x in row]for row in d],negative_background_mask=[[-12<=x<=-9 for x in row]for row in d],positive_background_mask=[[9<=x<=12 for x in row]for row in d],relative_raw_rows=rr,absolute_raw_rows=[r+3139 for r in rr],trace_columns=[centers[r]for r in rr],stitched_columns=[column_map[r]for r in rr],chip2_columns=[[x-2048+50 for x in column_map[r]]for r in rr])
   try:
    if template is None:raise ValueError(details['pooled']['status'])
    metric,rows,arrays=ref.window(name,rr,strips,centers,template,side)
    wanted_metrics.append(dict(estimator=estimator,template='pooled',status='MEASURED_DESCRIPTIVE',**metric))
    wanted_rows.extend(dict(estimator=estimator,template='pooled',status='MEASURED_DESCRIPTIVE',**r)for r in rows)
    maps.update(model=[a[2]for a in arrays],residual=[a[3]for a in arrays])
   except ValueError as error:
    wanted_metrics.append(dict(estimator=estimator,template='pooled',window=name,status='BLOCKED',reason=str(error),center_relative_raw_row=rr[len(rr)//2],rows=len(rr)))
    wanted_rows.extend(dict(estimator=estimator,template='pooled',window=name,relative_raw_row=r,status='BLOCKED',reason=str(error))for r in rr)
    maps.update(model=np.full((11,25),np.nan),residual=np.full((11,25),np.nan))
   for key,value in maps.items():wanted_arrays[estimator+'__'+name+'__'+key]=value
 recorded_templates=read(RESULT/'TEMPLATES.json')
 ck(same(recorded_templates['templates'],wanted_templates,'Templates','template')and same(recorded_templates['details'],wanted_details,'Template details','training'),'Independent both pooled templates/support')
 recorded_dispositions=read(RESULT/'TRAINING_DISPOSITIONS.json')
 ck(same(recorded_dispositions,wanted_dispositions,'Training dispositions','training'),'All464 training dispositions')
 recorded_metrics=read(RESULT/'WINDOW_METRICS.json')
 ck(len(recorded_metrics)==18 and same(recorded_metrics,wanted_metrics,'Window metrics','window_metric'),'All18 independently reconstructed windows')
 with (RESULT/'ROW_METRICS.csv').open(newline='')as f:recorded_rows=list(csv.DictReader(f))
 ck(len(recorded_rows)==198,'All198 row records retained')
 for actual,expected in zip(recorded_rows,wanted_rows):
  converted={k:actual[k]if isinstance(v,str)else float(actual[k])for k,v in expected.items()}
  ck(same(converted,expected,'Row '+expected['estimator']+'/'+expected['window']+'/'+str(expected['relative_raw_row']),'row_metric'),'Independent row '+expected['estimator']+'/'+str(expected['relative_raw_row']))
 with np.load(RESULT/'SPATIAL_ARRAYS.npz',allow_pickle=False)as saved:
  ck(set(saved.files)==set(wanted_arrays),'Every model/residual/mask/map array accounted for')
  for name,value in wanted_arrays.items():ck(same(saved[name],value,'Array '+name,'array_'+name.split('__')[-1]),'Independent array '+name)
 original={r['window']:r for r in read(ROOT/plan['original_window_metrics_path'])if r['template']=='pooled'}
 comparison=[]
 for r in wanted_metrics:
  numeric={k:dict(original_pooled_two_sided=v,one_sided=r.get(k),difference=r[k]-v if isinstance(r.get(k),(int,float))and not isinstance(r.get(k),bool)else None)for k,v in original[r['window']].items()if isinstance(v,(int,float))and not isinstance(v,bool)}
  comparison.append(dict(estimator=r['estimator'],window=r['window'],status=r['status'],metrics=numeric))
 ck(same(read(RESULT/'ORIGINAL_POOLED_COMPARISON.json'),comparison,'Original comparison','comparison'),'All18 original-pooled differences')
 empirical=[]
 for estimator in ['negative_side','positive_side']:
  target=next(r for r in wanted_metrics if r['estimator']==estimator and r['window']=='TARGET');controls=[next(r for r in wanted_metrics if r['estimator']==estimator and r['window']==name)for name in list(windows)[1:]]
  keys=[k for k,v in original['TARGET'].items()if (v is None or isinstance(v,(int,float))and not isinstance(v,bool))and k not in {'center_relative_raw_row','rows','fit_pixels','on_trace_pixels','off_trace_pixels'}]
  for key in keys:
   value=target.get(key);context=[dict(window=r['window'],status=r['status'],value=r.get(key))for r in controls];valid=[x['value']for x in context if isinstance(x['value'],(int,float))]
   empirical.append(dict(estimator=estimator,metric=key,target=value,controls=context,controls_available=len(valid),controls_at_least_target=sum(v>=value for v in valid)if isinstance(value,(int,float))else None,meaning='Eight coordinate-selected local controls; descriptive context, no significance or classification.'))
 ck(same(read(RESULT/'EMPIRICAL_CONTEXT.json'),empirical,'Empirical context','empirical'),'Every control value and count reconstructed')
 ck(summary['estimators']==['negative_side','positive_side']and summary['window_records']==18 and summary['row_records']==198 and summary['training_rows_per_estimator']==232 and summary['background_pixels_per_estimator_per_row']==3,'Exact bounded summary accounting')
 ck(summary['reused_unique_native_pixels']==8275 and summary['new_native_pixels_read']==0 and summary['classification']=='U'and summary['classification_changed']is False and summary['origin_assignments']==0,'No new pixels or classification changes')
 for name,digest in plan['source_hashes'].items():ck(sha(ROOT/name)==digest,'Source unchanged '+name)
 for name,digest in output_hashes.items():ck(sha(RESULT/name)==digest,'Sensitivity output unchanged '+name)
 for name,digest in oldhashes.items():ck(sha(oldroot/name)==digest,'Original output unchanged '+name)
 ck(sha(input_path)==input_hash,'Selected pixel artifact unchanged')
 maxima={kind:max(r['maximum_absolute_difference']for r in differences if r['kind']==kind)for kind in sorted({r['kind']for r in differences})}
 report=dict(status='PASS_INDEPENDENT_BACKGROUND_SENSITIVITY_RECONSTRUCTION',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=len(checks),scalar_values_compared=scalars,training_dispositions_reconstructed=464,pooled_templates_reconstructed=2,window_records_reconstructed=18,row_records_reconstructed=198,array_records_reconstructed=len(wanted_arrays),raw_FITS_reads=0,new_native_pixels_read=0,reused_unique_native_pixels=8275,production_functions_imported=False,network_requests=0,original_scientific_outputs_unchanged=True,original_classification='U',classification_changed=False,check_labels=checks,maximum_absolute_differences_by_kind=maxima,source_hashes={str(p.relative_to(ROOT)):sha(p)for p in [B/'PLAN.json',B/'ROOT_RELEASE.json',RESULT/'OUTPUT_HASHES.json',input_path,OUT/'independent_math.py']},audit_script_sha256=sha(Path(__file__)),limitations=['Independent arithmetic check of two predeclared estimators on the same observed pixels; no independent detection or calibrated uncertainty.','Both outcomes retained without preferred-background selection; residual fractions and control counts are descriptive, not probabilities or physical-origin assignments.'])
 with (OUT/'NUMERICAL_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 with (OUT/'NUMERICAL_DIFFERENCES.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=['name','kind','scalar_values','maximum_absolute_difference']);w.writeheader();w.writerows(differences)
 print(json.dumps({k:v for k,v in report.items()if k not in ['check_labels','source_hashes']},indent=2))
if __name__=='__main__':main()
