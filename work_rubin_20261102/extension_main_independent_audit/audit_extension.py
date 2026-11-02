#!/usr/bin/env python3
"""Audit the separate Rubin extension using the unchanged scalar implementation."""
import argparse,collections,csv,datetime,hashlib,json,math,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'independent_main_audit'))
from independent_science import RUBIN,load,digest,number,date_index,calculate,Checks
HERE=Path(__file__).resolve().parent
import independent_science

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=RUBIN/'extension_main_analysis')
    args = parser.parse_args()
    checks = Checks()
    method = RUBIN/'method_review'
    cfg = load(method/'CONFIG.json')
    acquire = RUBIN/'extension_main_acquisition'
    plan = load(acquire/'PLAN.json')
    manifest = load(acquire/'MANIFEST.json')
    release = load(acquire/'ROOT_RELEASE.json')
    method_path = acquire/release['method_path']
    freeze = load(method_path)
    checks.equal(digest(method_path), release['method_sha256'], 'release/method_hash')
    for name, expected in freeze['source_hashes'].items():
        checks.equal(digest(method/name), expected, 'frozen_method_source/' + name)
    for name, expected in freeze['development_input_hashes'].items():
        checks.equal(digest(RUBIN.parent/name), expected, 'unchanged_development_input/' + name)
    checks.equal(digest(acquire/'PLAN.json'), release['acquisition_plan_sha256'], 'release/acquisition_plan_hash')
    checks.equal(digest(acquire/'acquire_main.py'), release['acquisition_script_sha256'], 'release/acquisition_script_hash')
    preflight=load(HERE/'PREFLIGHT.json')
    checks.equal(digest(acquire/'PLAN.json'),preflight['plan_sha256'],'independent_preflight_plan')
    checks.equal(digest(acquire/'MAIN_SELECTION_FROZEN.csv'),preflight['selection_sha256'],'independent_preflight_selection')
    for name,expected in plan['code_hashes'].items():
        checks.equal(digest(acquire/name),expected,'extension_frozen_code/'+name)
    for name,expected in load(RUBIN/'main_analysis/OUTPUT_HASHES.json').items():
        checks.equal(digest(RUBIN/'main_analysis'/name),expected,'original_main_outputs_preserved/'+name)
    selection = list(csv.DictReader((acquire/'MAIN_SELECTION_FROZEN.csv').open()))
    selected = [r['diaObjectId'] for r in selection]
    checks.equal(selected, plan['selected_ids'], 'exact_selection_order')
    checks.equal(len(selected), plan['objects'], 'frozen_selection_size')
    checks.equal(len(set(selected)), len(selected), 'selection_unique_dia')
    checks.equal(len({r['matched_gaia_source_id'] for r in selection}),len(selected),'selection_unique_gaia')
    checks.equal(digest(acquire/'MAIN_SELECTION_FROZEN.csv'), plan['selection_sha256'], 'selection_hash')
    checks.equal(manifest['publication_commit'], release['publication_commit'], 'acquisition_publication_commit')
    development = list(csv.DictReader((RUBIN/'access_pilot/DEVELOPMENT_SELECTION.csv').open()))
    checks.equal(sorted(set(selected) & {r['r:diaObjectId'] for r in development}), [], 'development_id_exclusion')
    rows = {'sources': [], 'forced': []}
    origins = {'sources': [], 'forced': []}
    availability = {'sources': {}, 'forced': {}}
    inputs = {}
    for job in manifest['jobs']:
        stream = 'sources' if job['job_id'].startswith('sources_') else 'forced'
        for identity in job['object_ids']:
            availability[stream][identity] = job['status']
        if job['status'] != 'COMPLETE':
            continue
        path = acquire/job['canonical_path']
        checks.equal(digest(path), job['sha256'], 'raw_hash/' + job['job_id'])
        payload = load(path, raw=True)
        checks.equal(len(payload), job['rows'], 'raw_rows/' + job['job_id'])
        checks.equal(sorted({r['r:diaObjectId'] for r in payload}-set(job['object_ids'])), [], 'job_id_scope/' + job['job_id'])
        rows[stream].extend(payload)
        origins[stream].extend({'raw_path':str(path.relative_to(RUBIN)), 'raw_row_index':i} for i in range(len(payload)))
        inputs[str(path.relative_to(RUBIN))] = digest(path)
    summaries = {}
    all_expected_hits = []
    all_normal = {}
    expected_eligibility = []
    reported_summary=load(args.results/'SUMMARY.json')
    for stream, raw in rows.items():
        normal, scored, duplicates = calculate(raw, stream, cfg)
        # Independently map the first canonical occurrence back to its raw file.
        for record in normal + scored:
            record.update(origins[stream][record['source_row_index']])
        all_normal[stream] = normal
        prefix = stream.upper()
        checks.equal(load(args.results/(prefix+'_NORMALIZED.json')), normal, stream+'/normalized')
        checks.equal(load(args.results/(prefix+'_SCORED.json')), scored, stream+'/scored')
        checks.equal(load(args.results/(prefix+'_DUPLICATES.json')), duplicates, stream+'/duplicates')
        hits = [r for r in scored if r['hit']]
        checks.equal(load(args.results/(prefix+'_TRIGGERS.json')),hits,stream+'/complete_trigger_list')
        all_expected_hits.extend(hits)
        evaluable = [r for r in scored if r['status']=='NUMERICALLY_EVALUABLE']
        summaries[stream] = {
            'raw_rows': len(raw), 'unique_measurements': len(normal),
            'objects_returned': len({r['object_id'] for r in normal}),
            'selected_objects_not_returned': sorted(set(selected)-{r['object_id'] for r in normal}, key=int),
            'october_rows': len(scored),
            'status_counts': dict(collections.Counter(r['status'] for r in scored)),
            'evaluable_objects': len({r['object_id'] for r in evaluable}),
            'evaluable_measurements': len(evaluable),
            'trigger_measurements': sum(r['hit'] for r in scored),
            'trigger_objects': len({r['object_id'] for r in scored if r['hit']}),
            'long_gap_evaluable_measurements': sum(r['long_baseline_gap'] for r in evaluable),
            'fully_quality_vetted_objects': len({r['object_id'] for r in evaluable if not r['requires_quality_and_image_review']}),
        }
        expected_summary={
            'input_unique_measurements':len(normal),'input_objects':len({r['object_id']for r in normal}),
            'admitted_measurements':sum(not r['exclusion_reasons']for r in normal),
            'explicit_or_unknown_quality_exclusions':dict(collections.Counter(x for r in normal for x in r['exclusion_reasons'])),
            'quality_note_counts':dict(collections.Counter(x for r in normal for x in r['quality_notes'])),
            'duplicate_rows':len(duplicates),'primary_window_measurements':len(scored),
            'primary_window_objects':len({r['object_id']for r in scored}),
            'status_counts':dict(collections.Counter(r['status']for r in scored)),
            'numerically_evaluable_objects':len({r['object_id']for r in evaluable}),
            'numerically_evaluable_visits':len(evaluable),'hits':len(hits),
            'long_gap_evaluable_visits':sum(r['long_baseline_gap']for r in evaluable),
            'fully_quality_vetted_evaluable_objects':len({r['object_id']for r in evaluable if not r['requires_quality_and_image_review']}),
            'local_quiescence_established':False,'global_false_alarm_rate_calibrated':False,
            'raw_rows':len(raw),'api_jobs':sum(j['job_id'].startswith(('sources_'if stream=='sources'else'fp_'))for j in manifest['jobs']),
            'complete_api_jobs':sum(j['job_id'].startswith(('sources_'if stream=='sources'else'fp_'))and j['status']=='COMPLETE'for j in manifest['jobs']),
            'selected_objects':len(selected)}
        checks.equal(reported_summary['stream_summaries'][stream],expected_summary,stream+'/summary')
        for selection_index, identity in enumerate(selected,1):
            history=[r for r in normal if r['object_id']==identity]
            window=[r for r in scored if r['object_id']==identity]
            numeric=[r for r in window if r['status']=='NUMERICALLY_EVALUABLE']
            qualified=[r for r in numeric if not r['requires_quality_and_image_review']]
            transfer=availability[stream].get(identity,'JOB_MISSING')
            if transfer!='COMPLETE':
                status='ACQUISITION_'+transfer
            elif not history:
                status='EMPTY_API_OBJECT'
            elif not window:
                status='NO_OCTOBER_MEASUREMENTS'
            elif numeric:
                status='NUMERICALLY_EVALUABLE_QUALITY_REVIEW_REQUIRED' if len(qualified)<len(numeric) else 'NUMERICALLY_EVALUABLE_NO_RECORDED_QUALITY_NOTE'
            elif all(r['status']=='EXCLUDED_QUALITY_OR_NUMERIC' for r in window):
                status='ALL_WINDOW_MEASUREMENTS_QUALITY_OR_NUMERIC_EXCLUDED'
            else:
                status='NO_USABLE_PRIOR_BASELINE'
            expected_eligibility.append({
                'selection_index':str(selection_index),'object_id':identity,'stream':stream,
                'availability_status':transfer,'eligibility_status':status,
                'raw_unique_measurements':str(len(history)),
                'admitted_measurements':str(sum(not r['exclusion_reasons'] for r in history)),
                'october_measurements':str(len(window)),
                'numerically_evaluable_measurements':str(len(numeric)),
                'numerically_evaluable_without_quality_notes':str(len(qualified)),
                'trigger_rows':str(sum(r['hit'] for r in window)),
                'window_status_counts':json.dumps(dict(collections.Counter(r['status'] for r in window)),sort_keys=True),
                'all_history_exclusion_reason_counts':json.dumps(dict(collections.Counter(x for r in history for x in r['exclusion_reasons'])),sort_keys=True),
                'window_baseline_failure_counts':json.dumps(dict(collections.Counter(r.get('baseline_failure','') for r in window if r['status']=='NO_USABLE_BASELINE')),sort_keys=True),
                'quality_note_counts':json.dumps(dict(collections.Counter(x for r in history for x in r['quality_notes'])),sort_keys=True),
                'physical_origin_classification':'NOT_PERFORMED'})
    checks.equal(load(args.results/'ALL_TRIGGERS.json'),all_expected_hits,'all_triggers_preserved_separate_streams')
    checks.equal(reported_summary['selected_main_objects'],len(selected),'summary_selected_main_objects')
    checks.equal(reported_summary['total_trigger_rows_across_separate_streams'],len(all_expected_hits),'summary_all_triggers')
    checks.equal(reported_summary['raw_input_hashes'],inputs,'summary_raw_provenance')
    actual_eligibility=list(csv.DictReader((args.results/'OBJECT_ELIGIBILITY.csv').open()))
    checks.equal(actual_eligibility,expected_eligibility,'all_selected_x2_eligibility_rows')
    associations=[]
    for hit in all_expected_hits:
        counterparts=[hit] if hit['stream']=='sources' else [r for r in all_normal['sources'] if all(r[k]==hit[k]for k in ('object_id','visit','detector','band'))]
        associations.append({'trigger_object_id':hit['object_id'],'trigger_stream':hit['stream'],
                             'trigger_measurement_id':hit['measurement_id'],'visit':hit['visit'],
                             'detector':hit['detector'],'band':hit['band'],'time_mjd_tai':hit['time_mjd_tai'],
                             'matching_source_ids':[r['measurement_id']for r in counterparts],
                             'cutout_status':'EXACT_SOURCE_ID_AVAILABLE' if len(counterparts)==1 else 'NO_EXACT_SOURCE_COUNTERPART'if not counterparts else 'AMBIGUOUS_EXACT_SOURCE_COUNTERPART',
                             'nearest_substitution_allowed':False})
    checks.equal(load(args.results/'CUTOUT_ASSOCIATIONS.json'),associations,'exact_cutout_associations')
    for relative, expected in load(args.results/'OUTPUT_HASHES.json').items():
        checks.equal(digest(args.results/relative),expected,'production_output_hash/'+relative)
    metadata_ids=set()
    metadata_paths=sorted((RUBIN/'extension_feasibility/metadata').glob('history_[0-9][0-9].json'))
    for path in metadata_paths:
        for record in load(path,raw=True):
            if record['r:diaObjectId']in set(selected):
                metadata_ids.add(record['r:diaSourceId'])
    acquired_ids={r['r:diaSourceId']for r in rows['sources']}
    history_comparison={
        'earlier_metadata_files':len(metadata_paths),
        'selected_source_ids_in_earlier_metadata':len(metadata_ids),
        'selected_source_ids_in_main_acquisition':len(acquired_ids),
        'metadata_source_ids_absent_from_main':sorted(metadata_ids-acquired_ids,key=int),
        'main_source_ids_absent_from_earlier_metadata':sorted(acquired_ids-metadata_ids,key=int),
        'interpretation':'Descriptive service-snapshot comparison; no equivalence to all telescope observations or global completeness.'}
    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'PASS_INDEPENDENT_EXTENSION_ARITHMETIC_AND_COVERAGE' if not checks.failures else 'FAIL',
        'implementation': 'Independent scalar Python statistics, math.hypot, and ERFA taiutc; no production imports or network calls.',
        'comparisons': checks.count, 'floating_comparisons': checks.numeric,
        'maximum_absolute_numeric_difference': checks.max_abs, 'failures': checks.failures,
        'summaries': summaries, 'input_hashes': inputs,
        'metadata_history_comparison':history_comparison,
        'config_sha256': digest(method/'CONFIG.json'),
        'method_freeze_sha256': digest(method_path),
        'audit_script_sha256': digest(Path(__file__)),
        'scalar_detector_sha256':digest(Path(independent_science.__file__)),
        'limits': ['Reproducing arithmetic does not validate physical origin.',
                   'Long reference gaps do not establish local quiescence.',
                   'Missing withdrawal state and forced quality flags remain unresolved.',
                   'No completeness, calibrated false alarm rate, or sensitivity is inferred.'],
    }
    (HERE/'AUDIT.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','summaries')}, indent=2))
    if checks.failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
