"""Independent one-epoch HARPS12-profile reconstruction; no production function imports.
Run only after root confirms comparison release and completed production run.
"""
from pathlib import Path
import argparse,csv,datetime,hashlib,json,math,statistics
import numpy as np
from astropy.io import fits
from independent_math import reconstruct,correlation,stats
R=Path(__file__).resolve().parents[2];B=R/'work_harps_20261102_may_quality';A=B/'acquisition';P=B/'comparison';RESULT=P/'results';OUT=Path(__file__).resolve().parent
C=299792.458;X=np.arange(201,dtype=float)/100-1;CORE=np.abs(X)<=.250000001;SIDE=np.abs(X)>=.599999999
checks=[];scalar_count=0;errors=[]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def ck(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
def close(actual,expected,label,atol=2e-9):
 global scalar_count
 if actual is None or expected is None:ck(actual is None and expected is None,label);scalar_count+=1;return
 aa=np.asarray(actual,dtype=float);bb=np.asarray(expected,dtype=float);ck(aa.shape==bb.shape,label+' shape');scalar_count+=aa.size
 ck(np.allclose(aa,bb,rtol=2e-9,atol=atol,equal_nan=True),label)
 finite=np.isfinite(aa)&np.isfinite(bb);error=float(np.max(np.abs(aa[finite]-bb[finite])))if finite.any()else 0.
 errors.append({'name':label,'scalar_values':aa.size,'max_absolute_difference':error})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorized-after-comparison-run',action='store_true');args=parser.parse_args()
 if not args.authorized_after_comparison_run:raise SystemExit('Root runner-complete confirmation and explicit flag required before science-array reads.')
 ck((RESULT/'SUMMARY.json').exists(),'Completed production summary exists')
 release=read(P/'COMPARISON_RELEASE.json');summary=read(RESULT/'SUMMARY.json');manifest=read(A/'ACQUISITION_MANIFEST.json');events=read(P/'EVENTS.json');rows=read(RESULT/'ALL_COMPARISON_MEASUREMENTS.json');event_results=read(RESULT/'EVENT_RESULTS.json');hashes=read(RESULT/'OUTPUT_HASHES.json');plan=read(P/'PLAN.json')
 ck(summary['status']=='COMPLETE_FIXED_DESCRIPTIVE_COMPARISON','Production completed selected comparison slots')
 ck(summary['phase']=='POST_HOC_MAY_QUALITY_FOLLOWUP'and summary['prior_24_profile_run_replaced']is False,'Separate post-hoc phase preserves prior comparison')
 ck(release['schema']=='HARPS_MAY_QUALITY_COMPARISON_RELEASE_V1','Correct phase release schema')
 ck(len(manifest['inputs'])==1 and manifest['inputs'][0]['dp_id']=='ADP.2017-05-21T01:01:50.278'and manifest['inputs'][0]['target']=='HD122640'and manifest['inputs'][0]['status']=='COMPLETE','Exact one fixed acquired input')
 ck([e['candidate_id']for e in events]==['V2E2-0229','V2E2-0231','V2E2-0234','V2E2-0235','V2E2-0236','V2E2-0237','V2E2-0303','V2E2-0305','V2E2-0308','V2E2-0309'],'Exact ten preserved identities')
 ck(release['publication_readback_verified']is True and release['prospective_plan_sha256']==sha(P/'PLAN.json')and release['comparison_script_sha256']==sha(P/'compare_verified_epoch.py'),'Root comparison code/plan release bound')
 ck(release['acquisition_manifest_sha256']==sha(A/'ACQUISITION_MANIFEST.json')and release['inputs']==manifest['inputs'],'Exact released acquired inputs')
 ck(summary['release_sha256']==sha(P/'COMPARISON_RELEASE.json'),'Result release hash')
 for name,digest in hashes.items():ck(sha(RESULT/name)==digest,'Production output hash '+name)
 for name,digest in plan['source_hashes'].items():ck(sha(R/name)==digest,'Original/frozen scientific source '+name)
 source_hashes={str(OUT/'independent_math.py'):sha(OUT/'independent_math.py'),str(P/'COMPARISON_RELEASE.json'):sha(P/'COMPARISON_RELEASE.json'),str(A/'ACQUISITION_MANIFEST.json'):sha(A/'ACQUISITION_MANIFEST.json'),str(RESULT/'OUTPUT_HASHES.json'):sha(RESULT/'OUTPUT_HASHES.json')}
 ck(len(events)==10 and len(rows)==12 and len(event_results)==10,'Exact10events12new profiles10summaries')
 expected={(ev['candidate_id'],item['dp_id'],frame)for item in manifest['inputs']for ev in events if ev['target']==item['target']for frame in ['barycentric','topocentric']};actual={(r['candidate_id'],r['dp_id'],r['frame'])for r in rows};ck(actual==expected and len(actual)==len(rows),'Every selected event/epoch/frame exactly once')
 data={};native_summary=[]
 for item in manifest['inputs']:
  p=R/item['local_path'];ck(sha(p)==item['sha256'],'Exact new payload bytes before independent arrays '+item['dp_id']);source_hashes[str(p)]=sha(p)
  with fits.open(p,memmap=False)as hd:
   w=np.array(hd[1].data['WAVE'][0],dtype=float);f=np.array(hd[1].data['FLUX'][0],dtype=float);e=np.array(hd[1].data['ERR'][0],dtype=float);berv=hd[0].header['ESO DRS BERV']
  ck(w.ndim==1 and w.shape==f.shape==e.shape and np.isfinite(w).all()and(np.diff(w)>0).all(),'Native array integrity '+item['dp_id']);data[item['dp_id']]=(w,f,e,berv)
  native_summary.append({'dp_id':item['dp_id'],'samples':len(w),'finite_flux':int(np.isfinite(f).sum()),'finite_positive_ERR':int((np.isfinite(e)&(e>0)).sum())})
 rebuilt=[]
 for row in rows:
  ev=next(e for e in events if e['candidate_id']==row['candidate_id']);w,f,e,berv=data[row['dp_id']];center=ev['fitted_center_bary_air_angstrom'];scale=1.
  if row['frame']=='topocentric':center/=1+ev['discovery_berv_km_s']/C;scale=1+berv/C
  arrays,metrics=reconstruct(w,f,e,center,scale);tag=row['candidate_id']+' '+row['dp_id']+' '+row['frame']
  ck(row['status']=='MEASURED_DESCRIPTIVE_CONTEXT'and row['original_classification']=='U'and row['classification_changed']is False,'Descriptive U status '+tag)
  ck(row['source_dp_id']==ev['discovery_dp_id']and row['source_berv_km_s']==ev['discovery_berv_km_s'],'Discovery identity '+tag)
  saved=RESULT/row['profile_path'];ck(sha(saved)==row['profile_sha256'],'Saved new profile hash '+tag)
  with np.load(saved,allow_pickle=False)as archive:
   ck(set(archive.files)==set(arrays),'Exact six saved profile arrays '+tag)
   for name,value_ in arrays.items():close(archive[name],value_,name+' '+tag,atol=2e-8 if name=='raw_flux'else 2e-9)
  for key,value_ in metrics.items():
   if isinstance(value_,(bool,str,int)):ck(row[key]==value_,'Metric '+key+' '+tag)
   else:close(row[key],value_,'Metric '+key+' '+tag)
  ref=ev['discovery_profiles'][row['frame']];refpath=P/'inputs'/ref['profile_path'];ck(sha(refpath)==ref['profile_sha256'],'Original reference hash '+tag)
  with np.load(refpath,allow_pickle=False)as archive:reference=archive['residual'].copy()
  corr=correlation(reference,arrays['residual']);close(row['correlation_to_discovery'],corr,'Independent core correlation '+tag)
  delta=berv-ev['discovery_berv_km_s'];close(row['berv_delta_from_source_km_s'],delta,'Signed BERV displacement '+tag);close(row['source_epoch_displacement_resolution_elements'],abs(delta)/C*115000,'Resolution displacement '+tag)
  rebuilt.append(dict(candidate_id=row['candidate_id'],frame=row['frame'],correlation=corr,**metrics))
 uncovered=[]
 for ev,result in zip(events,event_results):
  ck(result['candidate_id']==ev['candidate_id']and result['origin_assignment']=='NOT_PERFORMED'and result['original_classification']=='U','Event identity/no origin '+ev['candidate_id'])
  covered=False
  for frame in ['barycentric','topocentric']:
   group=[r for r in rebuilt if r['candidate_id']==ev['candidate_id']and r['frame']==frame];got=result['frames'][frame];covered|=bool(group)
   ck(got['selected_epoch_slots']==got['measured_epochs']==len(group)and got['blocked_epochs']==0,'Exact event/frame coverage '+ev['candidate_id']+frame)
   for outkey,inkey in [('correlation_to_discovery','correlation'),('narrow_amplitude','narrow_amplitude'),('broad3_amplitude','broad3_amplitude'),('integrated_excess','core_flux_integral_over_linear_background')]:
    want=stats([r[inkey]for r in group])
    for key,v in want.items():close(got[outkey][key],v,'Summary '+ev['candidate_id']+frame+outkey+key)
   ck(got['low_continuum_count']==sum(r['local_continuum_low']for r in group),'Low continuum summary '+ev['candidate_id']+frame)
  if not covered:uncovered.append(ev['candidate_id'])
 ck(uncovered==['V2E2-0303','V2E2-0305','V2E2-0308','V2E2-0309'],'Exact four uncovered HD135204 events retained')
 ck(summary['events_with_measured_new_profiles']==6 and summary['new_epoch_products_measured']==1 and summary['frame_slots']==summary['measured_profiles']==12 and summary['blocked_profiles']==0 and summary['discovery_references_reused']==20,'Final actual profile/event/product counts')
 ck(summary['origin_assignments']==summary['repeat_classifications']==summary['U_labels_changed']==0,'No classification or origin changes')
 for name,digest in plan['source_hashes'].items():ck(sha(R/name)==digest,'Frozen sources and prior closed comparison unchanged '+name)
 for path,digest in source_hashes.items():ck(sha(Path(path))==digest,'Independent-audit source unchanged '+path)
 for name,digest in hashes.items():ck(sha(RESULT/name)==digest,'Production result unchanged '+name)
 report={'status':'PASS_INDEPENDENT_ACTUAL_NUMERICAL_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'scalar_values_compared':scalar_count,'check_labels':checks,'new_profiles_recomputed':12,'events_with_new_profiles':6,'uncovered_events':uncovered,'new_input_products_read':1,'native_inputs':native_summary,'production_functions_imported':False,'network_requests':0,'source_hashes':source_hashes,'audit_script_sha256':sha(Path(__file__)),'independent_math_sha256':sha(OUT/'independent_math.py'),'prior_comparisons_recomputed':False,'phase':'POST_HOC_MAY_QUALITY_FOLLOWUP','maximum_absolute_differences_by_kind':{kind:max((r['max_absolute_difference']for r in errors if r['name'].startswith(kind)),default=0.)for kind in ['offset_air_angstrom','requested_bary_air_angstrom','raw_flux','normalized_flux','linear_background','residual','Metric','Independent core correlation','Summary']},'limitations':['Independent arithmetic reconstruction only: no origin assignment, repeat classification, calibrated significance or completeness estimate.','One post-hoc quality-selected archival input covers6 queued records from3 discovery exposures; records and nearby centers remain correlated. The prior24-profile run is not recomputed or replaced.','Original discovery/profile methods, normalization and unweighted error limitations are inherited unchanged.']}
 with (OUT/'NUMERICAL_AUDIT.json').open('x')as file:json.dump(report,file,indent=2);file.write('\n')
 with (OUT/'NUMERICAL_DIFFERENCES.csv').open('x',newline='')as file:w=csv.DictWriter(file,fieldnames=['name','scalar_values','max_absolute_difference']);w.writeheader();w.writerows(errors)
 print(json.dumps({k:v for k,v in report.items()if k not in ['check_labels','source_hashes']},indent=2))
if __name__=='__main__':main()
