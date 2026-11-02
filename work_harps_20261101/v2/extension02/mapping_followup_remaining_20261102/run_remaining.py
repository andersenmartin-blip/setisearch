"""Sequential fixed-queue runner. Stops on any missing/changed pair; no replacements."""
from pathlib import Path
import argparse,subprocess,sys,json,hashlib,datetime
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--products-dir',type=Path,required=True);args=parser.parse_args()
 plan=json.loads((OUT/'PLAN.json').read_text());queue=json.loads((OUT/'EXPOSURE_QUEUE.json').read_text())
 assert sha(Path(__file__))==plan['runner_sha256']
 assert sha(OUT/'EXPOSURE_QUEUE.json')==plan['queue_sha256']
 assert sha(OUT/'REQUIRED_INPUTS.json')==plan['required_inputs_sha256']
 assert sha(OUT/'diagnose_exposure.py')==plan['exposure_script_sha256']
 for p,h in plan['source_hashes'].items():assert sha(ROOT/p)==h,p
 assert len(plan['plans'])==len(queue['queue'])==20
 runs=[]
 for spec,exposure in zip(plan['plans'],queue['queue']):
  assert spec['index']==exposure['index'] and spec['dp_id']==exposure['dp_id']
  pp=OUT/spec['plan'];assert sha(pp)==spec['sha256']
  # Fresh run only; no guessing whether partial output was fully completed.
  if (pp.parent/'RAW_REFERENCE_DIAGNOSTICS.json').exists():raise RuntimeError('Refusing overwrite of existing exposure output')
  for prod in exposure['products']:
   p=args.products_dir/Path(prod['relative_path']).name
   if not p.is_file():raise RuntimeError('Required input missing: '+str(p))
   if p.stat().st_size!=prod['bytes'] or sha(p)!=prod['sha256']:raise RuntimeError('Input hash/length mismatch: '+str(p))
  print('BEGIN',exposure['index'],exposure['dp_id'],flush=True)
  with (pp.parent/'run.log').open('w') as log:
   r=subprocess.run([sys.executable,str(OUT/'diagnose_exposure.py'),'--products-dir',str(args.products_dir),'--output-dir',str(pp.parent)],stdout=log,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError('Exposure execution failed: '+exposure['dp_id'])
  s=json.loads((pp.parent/'RAW_REFERENCE_SUMMARY.json').read_text())
  assert s['status']=='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION' and s['dp_id']==exposure['dp_id'] and s['orders']==72
  assert s['records_followed']==exposure['review_ids'] and s['current_code']=='M' and s['origin_assignments']==0
  runs.append(dict(index=exposure['index'],dp_id=exposure['dp_id'],summary_path=str((pp.parent/'RAW_REFERENCE_SUMMARY.json').relative_to(OUT)),summary_sha256=sha(pp.parent/'RAW_REFERENCE_SUMMARY.json'),measured_windows=s['measured_windows'],unavailable_reference_windows=s['unavailable_reference_windows'],original_pearson_windows_verified=s['original_pearson_windows_verified']))
  print('DONE',exposure['index'],s['measured_windows'],flush=True)
 for p,h in plan['source_hashes'].items():assert sha(ROOT/p)==h,p
 summary=dict(schema='SETI_MAPPING_REMAINING_EXECUTION_V1',status='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exposures=len(runs),records=34,orders=len(runs)*72,reference_windows=len(runs)*360,measured_windows=sum(r['measured_windows'] for r in runs),unavailable_reference_windows=sum(r['unavailable_reference_windows'] for r in runs),original_pearson_windows_verified=sum(r['original_pearson_windows_verified'] for r in runs),origin_assignments=0,all_M_labels_unchanged=True,runs=runs,plan_sha256=sha(OUT/'PLAN.json'),runner_sha256=sha(Path(__file__)))
 (OUT/'EXECUTION_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
