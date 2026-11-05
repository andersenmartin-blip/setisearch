"""Audit routing coverage from frozen metadata; never replay scientific arrays."""
from pathlib import Path
import argparse,csv,hashlib,json
HERE=Path(__file__).resolve().parent;PHASE=HERE.parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def build(after_run=False):
 prior_path=ROOT/'work_harps_20261105_c035_context/CONTINUATION_STATE.json';prior=read(prior_path);qpath=ROOT/'work_harps_20261101/v2/extension02/unresolved_context_20261102/ACTION_QUEUE.csv';queue=list(csv.DictReader(qpath.open(newline='')))
 proof_path=ROOT/prior['completed_baseline_route_proof_path'];assert sha(proof_path)==prior['completed_baseline_route_proof_sha256'];proof=read(proof_path);assert proof['status']=='EXACT_BOUNDED_BASELINE_DIAGNOSTICS_ALREADY_COMPLETE'
 skip=set(prior['completed_exact_baseline_route_ids']);assert skip==set(proof['event_ids']) and len(skip)==10
 proof_rows={r['candidate_id']:r for r in proof['skipped_rows']};completed=set(prior['completed_original_routes']);assert 'C037' not in completed
 assert len(queue)==len({r['candidate_id'] for r in queue})==90 and len({r['core_overlap_group'] for r in queue})==37
 records=[];counts={'prior_completed_diagnostic_rows':0,'exact_prior_baseline_rows':0,'current_C037_rows':0,'uncovered_rows':0}
 for row in queue:
  group=row['core_overlap_group'];event=row['candidate_id']
  if group in completed:kind='PRIOR_COMPLETED_BOUNDED_DIAGNOSTIC';counts['prior_completed_diagnostic_rows']+=1;source=str(prior_path.relative_to(ROOT))
  elif event in skip:
   assert proof_rows[event]==row;kind='EXACT_PRIOR_BASELINE_DIAGNOSTIC';counts['exact_prior_baseline_rows']+=1;source=str(proof_path.relative_to(ROOT))
  elif group=='C037' and event=='V2E2-0319' and row['queue_index']=='90':kind='CURRENT_C037_COMPLETED' if after_run else 'CURRENT_C037_PENDING';counts['current_C037_rows']+=1;source='work_harps_20261105_c037_context/independent_audit/NUMERICAL_AUDIT.json'
  else:counts['uncovered_rows']+=1;raise AssertionError('Uncovered original route '+event)
  records.append(dict(queue_index=int(row['queue_index']),candidate_id=event,target=row['target'],dp_id=row['dp_id'],core_overlap_group=group,diagnostic_routing_status=kind,source_metadata_path=source,physical_code_unchanged=row['current_code_unchanged']))
 assert counts==dict(prior_completed_diagnostic_rows=79,exact_prior_baseline_rows=10,current_C037_rows=1,uncovered_rows=0)
 if after_run:
  summary=read(PHASE/'analysis/results/SUMMARY.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT' and audit['status']=='PASS_SEPARATE_C037_NUMERICAL_RECONSTRUCTION';assert summary['events']==['V2E2-0319'] and summary['labels_changed']==summary['origin_assignments']==0
 return dict(schema='HARPS_ORIGINAL_90_ROUTE_COVERAGE_V1',status='COMPLETE_ORIGINAL_BOUNDED_CONTEXT_QUEUE' if after_run else 'PROSPECTIVE_ALL_ROUTES_COVERED_IF_C037_PASSES',after_current_observed_run=after_run,original_queue_rows=90,unique_original_event_ids=90,original_core_groups=37,completed_explicit_groups_after_current=len(completed)+1,counts=counts,remaining_original_routes_after_current=[],records=records,queue_path=str(qpath.relative_to(ROOT)),queue_sha256=sha(qpath),prior_state_path=str(prior_path.relative_to(ROOT)),prior_state_sha256=sha(prior_path),exact_baseline_proof_path=str(proof_path.relative_to(ROOT)),exact_baseline_proof_sha256=sha(proof_path),audit_script_sha256=sha(Path(__file__)),prior_scientific_array_values_reread=0,classification_changes=0,qualification='This verifies original-queue routing coverage against the source-bound completion state and exact prior-baseline proof. It does not independently re-review all prior science, resolve physical U, add observing time or establish calibrated sensitivity or a survey null.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--after-current-run',action='store_true');a=ap.parse_args();d=build(a.after_current_run);p=HERE/('ORIGINAL_QUEUE_CLOSURE.json' if a.after_current_run else 'QUEUE_COVERAGE_PREFLIGHT.json')
 with p.open('x' if a.after_current_run else 'w') as f:json.dump(d,f,indent=2);f.write('\n')
 print(json.dumps({k:d[k] for k in ['status','original_queue_rows','original_core_groups','completed_explicit_groups_after_current','counts','remaining_original_routes_after_current','classification_changes']},indent=2))
if __name__=='__main__':main()
