"""Read-only metadata/code preflight; never opens science FITS arrays."""
from pathlib import Path
import ast,collections,datetime,hashlib,json,subprocess,tempfile,shutil
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];V2=ROOT/'work_harps_20261101/v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def main():
 checks=[]
 def check(name,value):checks.append({'name':name,'pass':bool(value)})
 plan=load(OUT/'PLAN.json');queue=load(OUT/'EXPOSURE_QUEUE.json');req=load(OUT/'REQUIRED_INPUTS.json');state=load(ROOT/queue['source_state']);prior=load(ROOT/plan['reference_prior_plan'])
 oldscript=(V2/'extension02/mapping_followup_20261102/diagnose_raw_reference.py').read_text();newscript=(OUT/'diagnose_exposure.py').read_text();runner=(OUT/'run_remaining.py').read_text()
 for script in [oldscript,newscript,runner]:ast.parse(script)
 check('syntax_valid',True)
 check('frozen_script_runner_and_input_hashes',sha(OUT/'diagnose_exposure.py')==plan['exposure_script_sha256'] and sha(OUT/'run_remaining.py')==plan['runner_sha256'] and sha(OUT/'EXPOSURE_QUEUE.json')==plan['queue_sha256'] and sha(OUT/'REQUIRED_INPUTS.json')==plan['required_inputs_sha256'])
 check('prior_fixed_plan_hash',sha(ROOT/plan['reference_prior_plan'])==plan['reference_prior_plan_sha256'])
 check('all_frozen_source_hashes',all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items()))
 check('queue_source_state_hash',sha(ROOT/queue['source_state'])==queue['source_state_sha256'])
 done=load(V2/'extension02/mapping_followup_20261102/RAW_REFERENCE_SUMMARY.json')['dp_id'];current=state['followup_queues']['mapping_limited']['records'];remaining=[r for r in current if r['dp_id']!=done]
 expected_dps=list(dict.fromkeys(r['dp_id'] for r in remaining))
 check('exact_stable_remaining_queue',len(current)==35 and len(remaining)==34 and len(expected_dps)==20 and expected_dps==[e['dp_id'] for e in queue['queue']] and queue['completed_exposure_not_repeated']==done)
 expected_by_dp={dp:[r['review_id'] for r in remaining if r['dp_id']==dp] for dp in expected_dps}
 check('exact_per_exposure_record_ids',all(e['review_ids']==expected_by_dp[e['dp_id']] for e in queue['queue']))
 fixed_keys=['orders','reference_windows_half_open','candidate_exclusion_half_width','minimum_samples','median_highpass_width','raw_aperture_offsets','spatial_offsets','subwindow_length','subwindow_minimum_unmasked_samples','robust_metric','no_origin_assignment','no_original_mutation']
 all_plan_ok=True;all_products_ok=True;all_masks_ok=True;all_ref_ok=True;all_scope_ok=True;baseline_windows=0;manifest_products={}
 for spec,e in zip(plan['plans'],queue['queue']):
  p=load(OUT/spec['plan']);all_plan_ok &= sha(OUT/spec['plan'])==spec['sha256'] and spec['index']==e['index'] and p['dp_id']==spec['dp_id']==e['dp_id'] and p['review_ids']==spec['review_ids']==e['review_ids'] and p['script_sha256']==plan['exposure_script_sha256'] and p['products']==e['products'] and p['source_hashes']==plan['source_hashes']
  all_plan_ok &= all(p[k]==prior[k] for k in fixed_keys)
  md=load(ROOT/e['original_mapping']);refs=load(ROOT/e['reference_audit'])['reference_audit'];sp=next(x for x in md['spectra'] if x['dp_id']==e['dp_id'])
  all_masks_ok &= sp['status']=='REGISTERED' and sorted({r['review_id'] for r in md['orders'] if r['dp_id']==e['dp_id']})==e['candidate_exclusion_ids']==p['candidate_exclusion_ids']
  ref_orders={r['order'] for r in refs if r['dp_id']==e['dp_id']};wanted_orders={r['order'] for r in md['orders'] if r['dp_id']==e['dp_id'] and r['review_id'] in e['review_ids']}
  all_ref_ok &= bool(ref_orders) and wanted_orders.issubset(ref_orders)
  baseline_windows+=sum(len(r['windows']) for r in refs if r['dp_id']==e['dp_id'])
  all_scope_ok &= p['orders']==list(range(72)) and p['previous_reference_audit']==e['reference_audit'] and p['original_mapping']==e['original_mapping']
  manifest=load((ROOT/e['original_mapping']).parent/'products/MANIFEST.json')['products'];actual=[r for r in manifest if r['dp_id']==e['dp_id']]
  all_products_ok &= len(actual)==len(e['products'])==2 and {r['kind'] for r in actual}=={'RAW','ANCILLARY'} and all(all(next(r for r in actual if r['kind']==v['kind'])[k]==v[k] for k in v) for v in e['products'])
  for product in e['products']:manifest_products[product['relative_path']]=product
 check('twenty_frozen_plans_exact_identity_and_methods',all_plan_ok and len(plan['plans'])==20)
 check('forty_exact_manifest_products',all_products_ok and len(manifest_products)==40)
 check('complete_original_candidate_masks',all_masks_ok)
 check('all_M_covering_orders_have_prior_baselines',all_ref_ok)
 check('all72_orders_no_control_selection',all_scope_ok)
 def get_def(text,name):return ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name))
 check('helper_functions_byte_identical',all(get_def(oldscript,n)==get_def(newscript,n) for n in ['digest','save','corr','winsor','hp']))
 check('numerical_analysis_block_byte_identical',oldscript[oldscript.index("degree=int(header"):oldscript.index('    summary=dict(status=')]==newscript[newscript.index("degree=int(header"):newscript.index('    summary=dict(status=')])
 check('raw_loading_identity_and_candidate_guard_byte_identical',oldscript[oldscript.index('    product_path=lambda'):oldscript.index("    degree=int(header")]==newscript[newscript.index('    product_path=lambda'):newscript.index("    degree=int(header")])
 # Independently resolve every archive identity and member against original checkpoints.
 old_archive_path=V2/'triage_batch02/INPUT_CHECKPOINTS.json';initial_archive_path=V2/'extension02/raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json'
 archives={a['filename']:a for a in state['input_archives']}
 for a in load(old_archive_path)['parts']:archives[a['filename']]=a
 for a in load(initial_archive_path)['parts']:
  archives[a['filename']]=dict(archives[a['filename']],**a)
 archive_ok=True;members_seen=[]
 for a in req['archives']:
  original=archives[a['filename']]
  archive_ok &= all(a[k]==original[k] for k in ['filename','bytes','sha256','library_file_id','file_id'])
  memberlist=original.get('members',original.get('products',[]));by_path={m.get('path',m.get('relative_path')):m for m in memberlist}
  for member in a['required_members']:
   path=member['relative_path'];existing=by_path[path];canonical=manifest_products[path]
   archive_ok &= existing['bytes']==member['bytes']==canonical['bytes'] and existing['sha256']==member['sha256']==canonical['sha256'] and all(member[k]==canonical[k] for k in ['dp_id','kind'])
   members_seen.append(path)
 check('exact_archive_metadata_and_members',archive_ok and len(members_seen)==len(set(members_seen))==40 and set(members_seen)==set(manifest_products))
 check('archive_and_product_totals',len(req['archives'])==req['archive_count']==17 and sum(a['bytes'] for a in req['archives'])==req['archive_bytes']==1968315495 and sum(p['bytes'] for p in manifest_products.values())==req['required_product_bytes']==529060468 and req['required_products']==40)
 check('no_raw_network_or_partial_inputs',req['raw_network_fetches_allowed'] is False and req['known_partial_or_remnant_members_allowed'] is False and all('.part' not in p for p in members_seen))
 check('runner_selfhash_guard',"sha(Path(__file__))==plan['runner_sha256']" in runner)
 check('runner_stops_on_child_failure',"if r.returncode:raise RuntimeError" in runner and "zip(plan['plans'],queue['queue'])" in runner)
 check('no_existing_output_markers',not any((OUT/spec['plan']).parent.joinpath('RAW_REFERENCE_DIAGNOSTICS.json').exists() for spec in plan['plans']))
 # Exercise missing and length-mismatch guards without any science-array reads.
 scratch=Path(tempfile.mkdtemp(prefix='preflight_guard_',dir=OUT))
 try:
  args=['python3',str(OUT/'run_remaining.py'),'--products-dir',str(scratch)]
  absent=subprocess.run(args,capture_output=True,text=True)
  check('missing_input_guard_exercised',absent.returncode!=0 and 'Required input missing:' in absent.stderr)
  first=queue['queue'][0]['products'][0];(scratch/Path(first['relative_path']).name).write_bytes(b'x')
  changed=subprocess.run(args,capture_output=True,text=True)
  check('changed_length_guard_exercised',changed.returncode!=0 and 'Input hash/length mismatch:' in changed.stderr)
 finally:shutil.rmtree(scratch)
 result={'schema':'SETI_MAPPING_REMAINING_PREFLIGHT_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checks_passed':sum(c['pass'] for c in checks),'checks_total':len(checks),'checks':checks,'coverage':{'remaining_records':34,'remaining_exposures':20,'canonical_products':40,'archives':17,'planned_orders':1440,'planned_windows':7200,'previous_reference_windows_to_reproduce':baseline_windows},'reviewed_hashes':{'PLAN.json':sha(OUT/'PLAN.json'),'diagnose_exposure.py':sha(OUT/'diagnose_exposure.py'),'run_remaining.py':sha(OUT/'run_remaining.py'),'EXPOSURE_QUEUE.json':sha(OUT/'EXPOSURE_QUEUE.json'),'REQUIRED_INPUTS.json':sha(OUT/'REQUIRED_INPUTS.json')},'additional_archive_provenance_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [old_archive_path,initial_archive_path]},'auditor_script_sha256':sha(Path(__file__)),'raw_FITS_arrays_read':0,'limitations':['Metadata/code and negative input-guard preflight only; raw numerical execution and independent audit remain required.','Prior one-exposure diagnostic informed this extension; all metrics remain descriptive and no acceptance gates or M codes are changed.','Runner is fresh-run-only and stops on failure; resumption after partial completion requires an explicit preserved-output continuation.']}
 (OUT/'PREFLIGHT_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','reviewed_hashes','additional_archive_provenance_hashes','limitations']},indent=2));print([c for c in checks if not c['pass']])
if __name__=='__main__':main()
