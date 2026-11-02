"""Run independent raw reconstruction for every fixed remaining exposure."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,subprocess,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--products-dir',type=Path,required=True);args=parser.parse_args()
 plan=load(OUT/'PLAN.json');queue=load(OUT/'EXPOSURE_QUEUE.json');execution=load(OUT/'EXECUTION_SUMMARY.json')
 execution_hash=sha(OUT/'EXECUTION_SUMMARY.json');plan_hash=sha(OUT/'PLAN.json');audit_hash=sha(OUT/'audit_exposure.py')
 assert execution['status']=='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION' and execution['exposures']==20 and execution['records']==34 and execution['origin_assignments']==0
 assert len(execution['runs'])==len(plan['plans'])==len(queue['queue'])==20
 assert execution['plan_sha256']==plan_hash and sha(OUT/'run_remaining.py')==execution['runner_sha256']==plan['runner_sha256']
 coverage=collections.Counter();audits=[];max_errors=collections.defaultdict(float);max_poly=0.;review_ids=[]
 for spec,e,run in zip(plan['plans'],queue['queue'],execution['runs']):
  assert spec['index']==e['index']==run['index'] and spec['dp_id']==e['dp_id']==run['dp_id']
  pp=OUT/spec['plan'];exposure=pp.parent;assert sha(pp)==spec['sha256']
  summary=load(exposure/'RAW_REFERENCE_SUMMARY.json')
  assert summary['records_followed']==e['review_ids']==spec['review_ids'] and summary['current_code']=='M' and summary['origin_assignments']==0 and summary['coordinates_adjusted'] is False and summary['parent_dispositions_changed'] is False
  assert sha(exposure/'RAW_REFERENCE_SUMMARY.json')==run['summary_sha256']
  print('AUDIT_BEGIN',e['index'],e['dp_id'],flush=True)
  with (exposure/'independent_audit.log').open('w') as stream:
   subprocess.run([sys.executable,str(OUT/'audit_exposure.py'),'--products-dir',str(args.products_dir),'--exposure-dir',str(exposure)],check=True,stdout=stream,stderr=subprocess.STDOUT)
  ap=exposure/'RAW_NUMERICAL_AUDIT.json';a=load(ap)
  assert a['status']=='PASS' and a['mismatches']==[] and a['dp_id']==e['dp_id'] and a['review_ids']==e['review_ids'] and a['auditor_script_sha256']==audit_hash
  coverage.update(a['coverage']);review_ids.extend(e['review_ids'])
  for key,val in a['max_absolute_metric_errors'].items():max_errors[key]=max(max_errors[key],val)
  max_poly=max(max_poly,a['max_horner_vs_direct_power_column_error_pixels'])
  audits.append({'index':e['index'],'dp_id':e['dp_id'],'audit_path':str(ap.relative_to(OUT)),'audit_sha256':sha(ap),'coverage':a['coverage']})
  print('AUDIT_DONE',e['index'],a['coverage']['metrics_compared'],flush=True)
 assert len(review_ids)==len(set(review_ids))==34
 assert coverage['raw_pairs']==20 and coverage['orders']==1440 and coverage['reference_windows']==7200
 assert coverage['measured_windows']==execution['measured_windows'] and coverage['unavailable_windows']==execution['unavailable_reference_windows'] and coverage['prior_reference_windows']==execution['original_pearson_windows_verified']==640
 assert sha(OUT/'EXECUTION_SUMMARY.json')==execution_hash and sha(OUT/'PLAN.json')==plan_hash and sha(OUT/'audit_exposure.py')==audit_hash
 assert all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items())
 result={'schema':'SETI_MAPPING_REMAINING_NUMERICAL_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_INDEPENDENT_RAW_RECONSTRUCTION_ALL20','scope':'All20 fixed remaining M exposures; first completed exposure not repeated. No project analysis functions imported.','coverage':dict(coverage),'record_count':34,'review_ids':review_ids,'max_absolute_metric_errors':dict(max_errors),'max_horner_vs_direct_power_column_error_pixels':max_poly,'audits':audits,'plan_sha256':plan_hash,'execution_summary_sha256':execution_hash,'auditor_script_sha256':audit_hash,'audit_runner_sha256':sha(Path(__file__)),'all_M_labels_preserved':True,'source_hashes_unchanged':True,'limitations':['Independent arithmetic/raw-pixel reproduction shares NumPy/SciPy median filtering and Astropy decoding primitives.','This audit validates diagnostic calculations, not causal interpretation, physical origin, new acceptance gates or calibrated survey significance.','All controls share the selected M exposure population.']}
 (OUT/'NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['audits','review_ids','limitations','max_absolute_metric_errors']},indent=2))
if __name__=='__main__':main()
