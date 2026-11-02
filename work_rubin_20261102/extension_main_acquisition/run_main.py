#!/usr/bin/env python3
"""Apply the published fixed detector to all acquired main IDs; no network."""
import collections,csv,datetime,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
METHOD=ROOT/'method_review'
OUT=ROOT/'extension_main_analysis'
sys.path.insert(0,str(METHOD))
import detector
sys.path.insert(0,str(HERE))
import acquire_main

def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def table(name,rows):
    with (OUT/name).open('w',newline='') as f:
        fields=list(rows[0]) if rows else ['object_id','stream','measurement_id']
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)

def main():
    plan=acquire_main.load_plan();release=acquire_main.validate_release(plan)
    freeze=json.loads((METHOD/'METHOD_FREEZE.json').read_text())
    if detector.sha(METHOD/'METHOD_FREEZE.json')!=release['method_sha256']:raise ValueError('Method release hash mismatch')
    for name,digest in freeze['source_hashes'].items():
        if detector.sha(METHOD/name)!=digest:raise ValueError('Frozen method changed:'+name)
    cfg=json.loads((METHOD/'CONFIG.json').read_text())
    manifest=json.loads((HERE/'MANIFEST.json').read_text())
    if manifest['publication_commit']!=release['publication_commit']:raise ValueError('Acquisition release mismatch')
    ids=plan['selected_ids'];allowed=set(ids);OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'STARTED.json').open('x') as f:json.dump({'started_utc':acquire_main.now(),'release':release,'wrapper_sha256':detector.sha(Path(__file__))},f,indent=2)
    stream_results={};eligibility=[];all_hits=[];raw_hashes={}
    for stream,api_stream in [('sources','sources'),('forced','fp')]:
        rows=[];origins=[];object_transfer={};jobs=[j for j in manifest['jobs'] if j['job_id'].startswith(api_stream+'_')]
        for job in jobs:
            for oid in job['object_ids']:object_transfer[oid]=job['status']
            if job['status']!='COMPLETE':continue
            path=HERE/job['canonical_path'];digest=detector.sha(path)
            if digest!=job['sha256'] or path.stat().st_size!=job['bytes']:raise ValueError('Canonical payload mismatch')
            data=detector.read(path)
            if not all(r['r:diaObjectId'] in allowed for r in data):raise ValueError('Foreign object')
            raw_hashes[str(path.relative_to(ROOT))]=digest
            rows.extend(data);origins.extend({'raw_path':str(path.relative_to(ROOT)),'raw_row_index':i} for i in range(len(data)))
        normal,duplicates=detector.normalize(rows,stream,cfg)
        for r in normal:r.update(origins[r['source_row_index']])
        scored=detector.score(normal,cfg)
        hits=[r for r in scored if r['hit']]
        all_hits.extend(hits)
        dump(stream.upper()+'_NORMALIZED.json',normal)
        dump(stream.upper()+'_SCORED.json',scored)
        dump(stream.upper()+'_DUPLICATES.json',duplicates)
        dump(stream.upper()+'_TRIGGERS.json',hits)
        summary=detector.summarize(normal,scored,duplicates)
        summary.update(raw_rows=len(rows),api_jobs=len(jobs),complete_api_jobs=sum(j['status']=='COMPLETE' for j in jobs),selected_objects=len(ids))
        stream_results[stream]=summary
        for oid in ids:
            all_obj=[r for r in normal if r['object_id']==oid];window=[r for r in scored if r['object_id']==oid]
            evaluable=[r for r in window if r['status']=='NUMERICALLY_EVALUABLE']
            qualified=[r for r in evaluable if not r['requires_quality_and_image_review']]
            transfer=object_transfer.get(oid,'JOB_MISSING')
            if transfer!='COMPLETE':status='ACQUISITION_'+transfer
            elif not all_obj:status='EMPTY_API_OBJECT'
            elif not window:status='NO_OCTOBER_MEASUREMENTS'
            elif evaluable:status='NUMERICALLY_EVALUABLE_QUALITY_REVIEW_REQUIRED' if len(qualified)<len(evaluable) else 'NUMERICALLY_EVALUABLE_NO_RECORDED_QUALITY_NOTE'
            elif all(r['status']=='EXCLUDED_QUALITY_OR_NUMERIC' for r in window):status='ALL_WINDOW_MEASUREMENTS_QUALITY_OR_NUMERIC_EXCLUDED'
            else:status='NO_USABLE_PRIOR_BASELINE'
            eligibility.append({'selection_index':ids.index(oid)+1,'object_id':oid,'stream':stream,'availability_status':transfer,
                                'eligibility_status':status,'raw_unique_measurements':len(all_obj),
                                'admitted_measurements':sum(not r['exclusion_reasons'] for r in all_obj),
                                'october_measurements':len(window),'numerically_evaluable_measurements':len(evaluable),
                                'numerically_evaluable_without_quality_notes':len(qualified),'trigger_rows':sum(r['hit'] for r in window),
                                'window_status_counts':json.dumps(dict(collections.Counter(r['status'] for r in window)),sort_keys=True),
                                'all_history_exclusion_reason_counts':json.dumps(dict(collections.Counter(x for r in all_obj for x in r['exclusion_reasons'])),sort_keys=True),
                                'window_baseline_failure_counts':json.dumps(dict(collections.Counter(r.get('baseline_failure','') for r in window if r['status']=='NO_USABLE_BASELINE')),sort_keys=True),
                                'quality_note_counts':json.dumps(dict(collections.Counter(x for r in all_obj for x in r['quality_notes'])),sort_keys=True),
                                'physical_origin_classification':'NOT_PERFORMED'})
    assert len(eligibility)==2*len(ids)
    table('OBJECT_ELIGIBILITY.csv',eligibility);dump('ALL_TRIGGERS.json',all_hits)
    # Fixed cutout association: exact source identity or same object+visit+detector+band.
    src=detector.read(OUT/'SOURCES_NORMALIZED.json');sources_bykey=collections.defaultdict(list)
    for r in src:sources_bykey[(r['object_id'],r['visit'],r['detector'],r['band'])].append(r)
    requests=[]
    for hit in all_hits:
        matches=[hit] if hit['stream']=='sources' else sources_bykey[(hit['object_id'],hit['visit'],hit['detector'],hit['band'])]
        request={'trigger_object_id':hit['object_id'],'trigger_stream':hit['stream'],'trigger_measurement_id':hit['measurement_id'],
                 'visit':hit['visit'],'detector':hit['detector'],'band':hit['band'],'time_mjd_tai':hit['time_mjd_tai'],
                 'matching_source_ids':[r['measurement_id'] for r in matches],
                 'cutout_status':'EXACT_SOURCE_ID_AVAILABLE' if len(matches)==1 else 'NO_EXACT_SOURCE_COUNTERPART' if not matches else 'AMBIGUOUS_EXACT_SOURCE_COUNTERPART',
                 'nearest_substitution_allowed':False}
        requests.append(request)
    dump('CUTOUT_ASSOCIATIONS.json',requests)
    summary={'schema':'RUBIN_MAIN_FIXED_SCREEN_SUMMARY_V1','completed_utc':acquire_main.now(),'status':'FIXED_SCREEN_COMPLETE_WITH_QUALITY_LIMITATIONS',
             'selected_main_objects':len(ids),'stream_summaries':stream_results,'total_trigger_rows_across_separate_streams':len(all_hits),
             'trigger_rows_not_independent_events':True,'all_selected_accounted_in_both_streams':True,
             'raw_input_hashes':raw_hashes,'config_sha256':detector.sha(METHOD/'CONFIG.json'),'detector_sha256':detector.sha(METHOD/'detector.py'),
             'method_freeze_sha256':detector.sha(METHOD/'METHOD_FREEZE.json'),'wrapper_sha256':detector.sha(Path(__file__)),
             'main_selection_sha256':plan['selection_sha256'],'publication_commit':release['publication_commit'],
             'main_flux_read_before_method_publication':False,'threshold_tuning_after_main':False,
             'qualified_pilot_status':'NOT_ESTABLISHED_BY_NUMERICAL_SCREEN_ALONE','cutout_review_status':'PENDING_FOR_ALL_TRIGGER_ROWS',
             'limitations':['No new observingtime or independent telescopeobservation.','Source and forceddenominators remainseparate. Samephysicalvisit can appear inboth.','Missingwithdrawal and forcedqualityflags remainunknown.','180day archivalbaseline can be separated bylonggaps and doesnot establishlocalquiescence.','Scores are conservative descriptive deficits, not calibratedGaussian significance.']}
    dump('SUMMARY.json',summary)
    hashes={str(p.relative_to(OUT)):detector.sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='OUTPUT_HASHES.json'}
    dump('OUTPUT_HASHES.json',hashes)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
