"""Compact reporting from closed BP evidence; no computation of new scores."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'execution/BP_FIXED24_V1'


def main():
    terminal=json.loads((RUN/'TERMINAL.json').read_text())
    plan=json.loads((ROOT/'BP_FIXED24_PLAN.json').read_text())
    cases=[];current_comparisons=0;legacy_comparisons=0;old_guard_failures=0
    maximum_error=0.;maximum_rss=0;global_calibrations=0;local_calibrations=0
    all_records=[]
    for entry in terminal['case_receipts']:
        folder=RUN/entry['case_id'];receipt=json.loads((folder/'ACTUAL_RECEIPT.json').read_text())
        result_path=folder/'payload/RESULT.json'
        if not result_path.exists():
            c=next(c for c in plan['cases'] if c['id']==entry['case_id'])
            cases.append(dict(id=c['id'],kind=c['kind'],amplitude=c.get('amplitude'),rate_index=c.get('rate_index'),intrinsic_width=c.get('intrinsic_width'),status='NOT_COMPLETED_AFTER_RSS_STOP',capture_status=receipt['status'],actual_exit_code=receipt['actual_exit_code'],gate_reasons=receipt['reasons']))
            all_records.extend(dict(scan_summary=json.loads(p.read_text())) for p in sorted((folder/'payload').glob('scan*/RESULT.json')))
            maximum_rss=max(maximum_rss,receipt['resources']['max_child_RSS_bytes'] or 0)
            continue
        result=json.loads(result_path.read_text())
        c=result['case'];all_records.extend(result.get('records',[]))
        cases.append(dict(id=c['id'],kind=c['kind'],amplitude=c.get('amplitude'),
          rate_index=c.get('rate_index'),intrinsic_width=c.get('intrinsic_width'),
          status=result['status'],capture_status=receipt['status'],actual_exit_code=receipt['actual_exit_code'],
          current_truth_recovered=result.get('current_truth_recovered'),legacy_truth_recovered=result.get('legacy_truth_recovered'),
          current_flags=result.get('current_flags'),legacy_flags=result.get('legacy_flags'),
          gate_reasons=result.get('gate_reasons',[])))
        maximum_rss=max(maximum_rss,receipt['resources']['max_child_RSS_bytes'] or 0)
    for rec in all_records:
        s=rec['scan_summary'];current_comparisons+=s['current_oracle_comparisons']
        legacy_comparisons+=s['legacy_staged_comparisons'];old_guard_failures+=s['legacy_original_guard_FAILs']
        maximum_error=max(maximum_error,max(o['current_abs_error'] for o in s['oracles']))
        global_calibrations+=sum(x['method']=='legacy_global' for x in s['calibrations'])
        local_calibrations+=sum(x['method']=='current_local' for x in s['calibrations'])
    summary=dict(schema='SETI_BP_FIXED24_SUMMARY_V1',status=terminal['status'],
      preregistration_commit='ee9ff94abfaa56055f947036b80133393cf209f8',
      started_cases=terminal['completed_cases'],passed_cases=terminal['passed_cases'],
      scan_method_pairs=len(all_records),current_scalar_comparisons=current_comparisons,
      legacy_staged_comparisons=legacy_comparisons,legacy_original_guard_FAILs=old_guard_failures,
      maximum_current_absolute_error=maximum_error,legacy_global_calibrations=global_calibrations,
      current_local_calibrations=local_calibrations,maximum_child_RSS_bytes=maximum_rss,
      wall_seconds=terminal['wall_seconds'],total_cpu_seconds=terminal['total_cpu_seconds'],
      cases=cases,base_arrays=len(list((RUN/'bases').glob('seed*/scan*.npy'))),
      requested_random_variates=sum(json.loads(p.read_text())['requested_variates'] for p in (RUN/'bases').glob('seed*/scan*.json')),
      primitive_RNG_draw_count=None,primitive_RNG_draw_count_note='Variable-consumption samplers; all48 before/after states preserved.',
      source_unit_tests_passed=22,astronomical_powers_opened=0,new_observations=0,new_archive_requests=0,new_coverage_credit=0,
      old_HIP45688_M_raw_sum_failures=24,old_HIP45688_M_full_QA=False,
      full839_controls_completed=False,DATA_admission_completed=False,
      independent_review=json.loads((ROOT/'review/RESULT_REVIEW_BP.json').read_text()),
      scope='Limited five-rate five-q paired synthetic controls. Association is the prospective BP target-physical-q policy. No astronomical sensitivity/FAP/flux/EIRP qualification.',
      next_step='Separately implement and preregister the full839 paired stage with exactly the same association policy, then separate DATA admission and search.')
    with (ROOT/'SUMMARY_BP.json').open('x') as f:json.dump(summary,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['cases','independent_review']},indent=2))


if __name__=='__main__':main()
