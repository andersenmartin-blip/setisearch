#!/usr/bin/env python3
"""Independently rebuild frozen DEV injection controls, without production imports."""
import collections
import copy
import datetime
import json
import math
from pathlib import Path
import independent_science as audit


def main():
    base = Path(__file__).resolve().parent.parent
    method = base/'method_review'
    cfg = audit.load(method/'CONFIG.json')
    freeze = audit.load(method/'METHOD_FREEZE.json')
    plan = audit.load(method/'RECOVERY_PLAN.json')
    reported = audit.load(method/'RECOVERY_RESULTS.json')
    checks = audit.Checks()
    for relative, expected_hash in freeze['source_hashes'].items():
        checks.equal(audit.digest(method/relative), expected_hash, 'frozen_source/' + relative)
    for relative, expected_hash in freeze['development_input_hashes'].items():
        checks.equal(audit.digest(base.parent/relative), expected_hash, 'preserved_dev_input/' + relative)
    initial = audit.load(method/'attempts/initial_before_technical_fixes/RECOVERY_PLAN.json')
    checks.equal(plan['cases'], initial['cases'], 'unchanged_36_initial_cases')
    checks.equal(len(plan['cases']), 36, 'control_count')
    coordinates = [(r['object_id'],r['band'],r['center_mjd_tai'])for r in plan['cases']]
    checks.equal(len(set(coordinates)),36,'distinct_control_centers')
    raw = audit.load(base/'access_pilot/raw/development_sources.json', raw=True)
    supp = {r['r:diaSourceId']:r for r in audit.load(base/'access_pilot/metadata/development_quality_supplement.json',raw=True)}
    raw = [dict(r,**supp.get(r['r:diaSourceId'],{}))for r in raw]
    norm, original_scores, duplicates = audit.calculate(raw,'sources',cfg)
    checks.equal(audit.load(method/'DEVELOPMENT_SOURCES_NORMALIZED.json'),norm,'final_dev_normalized')
    checks.equal(audit.load(method/'DEVELOPMENT_SOURCES_SCORED.json'),original_scores,'final_dev_scored')
    oldhits = {r['measurement_id']for r in original_scores if r['hit']}
    checks.equal(sorted(oldhits),reported['control_original_hits'],'unchanged_control_hits')
    norm_index = {r['measurement_id']:r for r in norm}
    results = []
    alpha_error = 0.0
    for case, actual in zip(plan['cases'],reported['cases']):
        changed = copy.deepcopy(raw)
        changed_by_id = {r['r:diaSourceId']:r for r in changed}
        center = case['center_mjd_tai']
        event_half = case['duration_seconds']/(2*86400)
        begin,finish = center-event_half,center+event_half
        affected=[]
        for row in norm:
            if row['object_id']!=case['object_id'] or row['band']!=case['band']:
                continue
            exposure = row['exposure_seconds']
            time = row['time_mjd_tai']
            if exposure is None:
                fraction = float(begin<=time<finish)
                integration = 'MIDPOINT_APPROXIMATION_EXPOSURE_DURATION_UNAVAILABLE'
            else:
                width=exposure/86400
                left=time-width/2
                right=time+width/2
                clipped_left=begin if begin>left else left
                clipped_right=finish if finish<right else right
                overlap=clipped_right-clipped_left
                fraction=min(1.0,max(0.0,overlap)/width)
                integration='KNOWN_EXPOSURE_FRACTION'
                # Independent closed form measures floating-point cancellation,
                # not a different adopted injection placement or selection.
                geometric=max(0.0,min(width,2*event_half,width/2+event_half-abs(time-center)))/width
                alpha_error=max(alpha_error,abs(fraction-geometric))
            if fraction==0:
                continue
            loss=case['injection_baseline_njy']*(1-pow(10,-0.4*case['depth_mag']))*fraction
            changed_by_id[row['measurement_id']]['r:scienceFlux']=row['flux_njy']-loss
            affected.append({'measurement_id':row['measurement_id'],'overlap_fraction':fraction,
                             'integration_method':integration,'subtracted_njy':loss,
                             'quality_admitted':not row['exclusion_reasons']})
        _, scored, _ = audit.calculate(changed,'sources',cfg)
        affected_ids={r['measurement_id']for r in affected}
        new_hits=[r['measurement_id']for r in scored if r['hit'] and r['measurement_id']in affected_ids and r['measurement_id']not in oldhits]
        evaluable=[r for r in scored if r['measurement_id']in affected_ids and r['status']=='NUMERICALLY_EVALUABLE']
        status=('NO_SAMPLED_EXPOSURE'if not affected else'SAMPLED_BUT_NOT_EVALUABLE'if not evaluable else'RECOVERED'if new_hits else'SAMPLED_EVALUABLE_MISSED')
        expected=dict(case,status=status,recovered=bool(new_hits),affected_measurements=affected,
                      sampled_exposures=len(affected),evaluable_impacted_visits=len(evaluable),
                      new_recovered_hit_ids=new_hits,confounded_original_hit_ids=sorted(affected_ids&oldhits),
                      target_band_scored_rows=[r for r in scored if r['object_id']==case['object_id']and r['band']==case['band']])
        checks.equal(actual,expected,case['case_id'])
        # Original measurement errors and all nonflux fields remain unchanged.
        for original,altered in zip(raw,changed):
            checks.equal({k:v for k,v in original.items()if k!='r:scienceFlux'},
                         {k:v for k,v in altered.items()if k!='r:scienceFlux'},case['case_id']+'/fixed_error_metadata/'+original['r:diaSourceId'])
        results.append(expected)
    counts=dict(collections.Counter(r['status']for r in results))
    checks.equal(reported['status_counts'],counts,'aggregate_status')
    checks.equal(reported['recovered'],sum(r['recovered']for r in results),'aggregate_recovery')
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_INDEPENDENT_36_RECOVERY_RECONSTRUCTIONS'if not checks.failures else'FAIL',
            'comparisons':checks.count,'floating_comparisons':checks.numeric,
            'maximum_absolute_numeric_difference':checks.max_abs,
            'maximum_exposure_fraction_difference_alternative_closed_form':alpha_error,
            'failures':checks.failures,'control_cases':len(results),'status_counts':counts,
            'unchanged_control_hits':len(oldhits),
            'affected_missing_exposure_duration':sum(a['integration_method'].startswith('MIDPOINT')for r in results for a in r['affected_measurements']),
            'config_sha256':audit.digest(method/'CONFIG.json'),'method_freeze_sha256':audit.digest(method/'METHOD_FREEZE.json'),
            'recovery_plan_sha256':audit.digest(method/'RECOVERY_PLAN.json'),'recovery_results_sha256':audit.digest(method/'RECOVERY_RESULTS.json'),
            'audit_script_sha256':audit.digest(Path(__file__)),'scalar_detector_sha256':audit.digest(Path(audit.__file__)),
            'method':'Separate scalar implementation; raw direct-science flux injections, unchanged errors and metadata, all36 fixed positions and outputs rebuilt. No production imports.',
            'limits':['Conditional detector response only; not upstream alert completeness or survey sensitivity.',
                      'Longest-gap challenges are not random-phase sampling or a duty-cycle estimate.',
                      'Repeated objects and overlapping injection intervals are dependent; centers alone are distinct.',
                      'Fixed quoted errors preserve empirical residuals and do not resimulate photon noise.']}
    (Path(__file__).resolve().parent/'RECOVERY_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if checks.failures:
        raise SystemExit(1)


if __name__=='__main__':
    main()
