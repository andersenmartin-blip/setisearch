"""Metadata/saved-result continuity only. No arrays, network, selection freeze or execution."""
import collections,csv,datetime,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[1]
SOURCES={}
def load(p):
    data=p.read_bytes();SOURCES[str(p.relative_to(ROOT))]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    return json.loads(data)
def save(n,d): (HERE/n).write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def table(n,rows):
    with (HERE/n).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
pool=load(BASE/'metadata_search_v2/CANDIDATES.json')
schema=load(BASE/'metadata_search_v2/SCHEMA_CONTRACT.json')
science=load(BASE/'science_acquisition/PLAN.json')
headers=load(BASE/'header_acquisition_v2/EXTREME_SELECTION.json')
comparison=load(BASE/'prospective_comparison/results/SUMMARY.json')
metrics=load(BASE/'prospective_comparison/results/ALL_COMPARISON_MEASUREMENTS.json')
events=load(BASE/'prospective_comparison/EVENTS.json')
method=load(BASE/'prospective_comparison/PLAN.json')
prior=load(ROOT/'work_harps_20261101/v2/extension02/next_followup_20261102/HANDOFF.json')
used={r['dp_id'] for r in science['inputs']}
assert len(pool)==18 and len(used)==2
origin=datetime.datetime(1858,11,17,tzinfo=datetime.timezone.utc)
inventory=[]
for r in pool:
    m=r['metadata'];dt=origin+datetime.timedelta(days=float(m['t_min']))
    inventory.append(dict(dp_id=r['dp_id'],target=r['target'],raw_id=r['source_file_ids'][0],observation_utc_from_mjd=dt.isoformat(),year=dt.year,month=dt.month,metadata_average_snr=float(m['snr']),exptime_seconds=m['t_exptime'],public_release_utc=m['obs_release_date'],coordinate_separation_arcsec=r['coordinate_separation_arcsec'],n_obs=m['n_obs'],multi_ob=m['multi_ob'],used_in_completed_two_epoch_comparison=r['dp_id'] in used))
unused=[r for r in inventory if not r['used_in_completed_two_epoch_comparison']]
may=sorted([r for r in unused if (r['year'],r['month'])==(2017,5)],key=lambda r:(-r['metadata_average_snr'],r['dp_id']))
assert len(unused)==16 and len(may)==9
assert all(math.isfinite(r['metadata_average_snr']) and r['metadata_average_snr']>0 for r in may)
chosen=may[0];assert chosen['dp_id']=='ADP.2017-05-21T01:01:50.278' and chosen['metadata_average_snr']==77.8
for r in unused:r['provisional_quality_followup']=r['dp_id']==chosen['dp_id']
table('UNUSED_METADATA_POOL.csv',unused)
used_may=next(r for r in inventory if r['used_in_completed_two_epoch_comparison'] and r['month']==5)
may_metrics=[r for r in metrics if r['dp_id']==used_may['dp_id']]
jan_blue=[r for r in metrics if r['dp_id'].startswith('ADP.2018') and r['frame']=='barycentric' and r['candidate_id']!='V2E2-0235']
assert len(may_metrics)==12 and sum(r['local_continuum_low'] for r in may_metrics)==10
assert len(jan_blue)==5 and comparison['measured_profiles']==24 and comparison['U_labels_changed']==0
event_rows=[dict(candidate_id=r['candidate_id'],target=r['target'],center_bary_air_angstrom=r['fitted_center_bary_air_angstrom'],discovery_dp_id=r['discovery_dp_id'],discovery_input_sha256=r['discovery_input_sha256'],current_code='U') for r in events]
assert len(event_rows)==10
current_path=ROOT/'work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv'
data=current_path.read_bytes();SOURCES[str(current_path.relative_to(ROOT))]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
current=list(csv.DictReader(data.decode().splitlines()));codes={r['review_id']:r['current_code'] for r in current}
assert all(codes[r['candidate_id']]=='U' for r in event_rows)
counts=dict(collections.Counter(r['current_code'] for r in current));assert counts=={'U':185,'A':403,'O':46,'M':35}
table('PRESERVED_TEN_EVENT_QUEUE.csv',event_rows)
source_candidate=next(r for r in pool if r['dp_id']==chosen['dp_id'])
handoff={
 'schema':'HARPS_NEXT_POSTHOC_QUALITY_CONTEXT_HANDOFF_V1',
 'status':'PROVISIONAL_FUTURE_PHASE_ONLY_NO_FREEZE_OR_EXECUTION',
 'this_task':{'new_requests':0,'new_science_arrays_read':0,'classifier_changes':0,'current_scope_expansion':False},
 'completed_fixed_run':{'status':comparison['status'],'queue_events':10,'HD122640_events_measured':6,'HD135204_no_new_epoch_events':4,'new_archival_payloads':2,'event_epoch_pairs':12,'profiles':24,'all_results_retained':True,'main_survey_exposures_unchanged':300,'current_V2_records':669,'current_codes':dict(counts,N=0),'pool_products':18,'used_pool_products':2,'unused_pool_products':16},
 'known_result_context':{'HD122640_verified_BERV_span_km_s':headers['target_summary']['HD122640']['combined_span_km_s'],'HD135204_verified_BERV_span_km_s':headers['target_summary']['HD135204']['combined_span_km_s'],'May_used_product':used_may['dp_id'],'May_used_metadata_average_snr':used_may['metadata_average_snr'],'May_low_continuum_profiles':10,'May_total_profiles':12,'January_five_blue_barycentric_correlations_min':min(r['correlation_to_discovery'] for r in jan_blue),'January_five_blue_barycentric_correlations_max':max(r['correlation_to_discovery'] for r in jan_blue),'isolated_5548_event':'V2E2-0235','origin_assignment':'NONE; all 10 remain U'},
 'proposed_next_phase':{
   'name':'POSTHOC_METADATA_QUALITY_FOLLOWUP',
   'motivation':'The completed May2017 large-displacement reference was low-continuum in 10 of 12 profiles. This new quality-focused question is motivated after observing that result; it is explicitly posthoc, not an extension or replacement of the completed fixed two-epoch run.',
   'deterministic_provisional_selection':'Among unused saved HD122640 metadata candidates observed in May2017, select highest finite positive ObsCore snr; tie lexicographically smallest dp_id. No line flux, local correlation or unseen spectrum is inspected for this choice.',
   'candidate':source_candidate,
   'metadata_inventory_row':chosen,
   'pool_eligible_for_rule':9,
   'unused_May_snr_range':[min(r['metadata_average_snr'] for r in may),max(r['metadata_average_snr'] for r in may)],
   'SNR_definition':schema['ivoa.ObsCore']['snr']['description'],
   'SNR_limitation':'Average spectrum metadata SNR is neither local blue continuum quality nor a calibrated error or promised sensitivity gain. Higher average SNR does not guarantee useful 3866–3881 Angstrom profiles or repeatability. Candidate BERV, mode, units and array quality are not yet verified.',
   'first_action_next_continue':'Prepare and independently review a new exact one-product header/optional-payload/comparison protocol; freeze and publish it prospectively before any new header or array access. This handoff itself is not that freeze.',
   'provisional_bounds_to_freeze':{'header_products_max':1,'header_attempts':1,'header_timeout_seconds':30,'header_response_bytes':524288,'payload_products_max':1,'payload_attempts':1,'payload_timeout_seconds':60,'payload_response_bytes':16777216,'retries':0,'redirects':0,'new_profiles_max':12,'new_full_spectrum_search':False},
   'header_then_payload_gate':'Use the already documented header route and inherited identity/provenance/mode/representation checks. Verify finite recorded BERV and its intended large displacement from each HD122640 discovery epoch before releasing an optional payload. Freeze the exact BERV benchmark prospectively; this is a quality-reference study, so extending the already known 40.36348 km/s range is not required. No candidate substitution after failure.',
   'future_comparison_scope':'All six preserved HD122640 events, both inherited frames, one additional archival epoch: 12 slots. Include V2E2-0235 as well as all five blue records. Retain blocked/low-continuum outcomes and both completed references. Keep all ten queue IDs, including the four HD135204 no-new-epoch records.',
   'method':'Reuse frozen centers, windows, normalization, background and descriptive metrics. Do not optimize shifts/widths, relabel, promote a detection, replace the low-quality reference or refit a classifier.',
   'stop':'Any identity/representation/BERV/transfer failure is an explicit stopped or blocked future phase; no automatic next-best May candidate, new target query or iterative quality-selection loop.'
 },
 'HD135204_route':'No eligible rows under the completed exact public/single-exposure/date/name-coordinate/provenance query. Four U remain; this is not proof of no other observations in the full archive. No additional query is proposed in this handoff.',
 'do_not_repeat':{'current_comparison':'Completed 24 profiles / 12 pairs; do not reopen or expand that fixed run.','mapping':prior['do_not_repeat']['mapping'],'normalization':prior['do_not_repeat']['normalization'],'original_epoch_pipeline':prior['do_not_repeat']['epoch_pipeline'],'Rubin':prior['do_not_repeat']['Rubin'],'metadata_and_header_routes':'All original failures/amendments are preserved. Do not rerun previous queries, header batches or payload acquisition to obtain this handoff.'},
 'files':{'unused_pool':'UNUSED_METADATA_POOL.csv','queue':'PRESERVED_TEN_EVENT_QUEUE.csv','source_hashes':'SOURCE_HASHES.json','independent_metadata_check':'INDEPENDENT_CHECK.json'}
}
save('HANDOFF.json',handoff)
selfdata=Path(__file__).read_bytes();SOURCES[str(Path(__file__).relative_to(ROOT))]={'sha256':hashlib.sha256(selfdata).hexdigest(),'bytes':len(selfdata)}
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==r['sha256'] for p,r in SOURCES.items())
save('SOURCE_HASHES.json',SOURCES)
save('PRESERVATION_CHECK.json',{'status':'PASS','source_files_unchanged':len(SOURCES),'all10_current_U_preserved':True,'all185U_35M_preserved':True,'new_arrays_read':0,'new_requests':0,'current_scope_expanded':False})
print('Handoff complete:16unused,9May,provisionalMaySNR77.8; no arrays/requests/freeze.')
