"""Export visually reviewed descriptive findings and cross-stage coverage; no status mutation."""
from pathlib import Path
import json,csv,hashlib,collections,datetime
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]; OLD=OUT.parent/'epoch64_followup'
def readcsv(p): return list(csv.DictReader(p.open()))
def writecsv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(p,obj): p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
groups=json.loads((OUT/'GROUP_RESULTS.json').read_text()); rows=readcsv(OUT/'ALL_EPOCH_MEASUREMENTS.csv')
original={r['review_id']:r for r in readcsv(ROOT/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv')}
mapping_path=ROOT/'v2/mapping43_followup/FOLLOWUP_DISPOSITIONS.csv';mapping={r['review_id']:r for r in readcsv(mapping_path)}
selected={rid for g in groups for rid in g['member_ids']}; assert len(selected)==31
assert selected=={rid for rid,r in mapping.items() if r['followup_status']=='UNRESOLVED_SPECTRAL_FEATURE'}
reasons={};events=[];summary=[];visual={}
for i,g in enumerate(groups):
    gid=g['group_id'];f=g['frames'];r=[v for v in rows if v['group_id']==gid and v['frame']=='barycentric']
    duration=max(float(v['mjd_obs']) for v in r)-min(float(v['mjd_obs']) for v in r)
    span=max(float(v['berv_km_s']) for v in r)-min(float(v['berv_km_s']) for v in r)
    reason='Broad central peak and neighboring troughs repeat in all selected epochs, including exposures without the original unresolved hit. This is persistent spectral structure; physical emission versus an absorption window and line identity remain undetermined.'
    if gid=='N02': reason+=' Despite its blue wavelength, the profile aligns strongly in barycentric coordinates and poorly in topocentric coordinates; wavelength proximity to reported calibration ghosts alone is insufficient to assign that mechanism.'
    if gid=='N06': reason+=' Seven epochs are clustered in two nights and only two span the later month, so pairwise correlations are dominated by short separations. The later two epochs retain barycentric leave-one-out correlation above 0.88 but have negative topocentric correlations; this favors barycentric persistence while limiting the independent temporal baseline.'
    if gid in ['N07','N08','N09']: reason+=' Both frames have high median correlation over a small BERV span; persistence is better established than frame discrimination.'
    if gid=='N08': reason+=' A localized single-epoch spike outside the shared core is retained; it does not erase the repeated broad core.'
    finding='PERSISTENT_BARYCENTRIC_SPECTRAL_STRUCTURE'; reasons[gid]=reason
    visual[gid]={'followup_finding':finding,'reason':reason,'viewed_figures':[f'figures/OVERVIEW_{i//4+1:02d}.png']+(['figures/N06.png'] if gid=='N06' else []),'origin_disposition_changed':False}
    summary.append({'group_id':gid,'target':g['target'],'center_bary_air_angstrom':g['center_bary_air_angstrom'],'center_reference_topocentric_air_angstrom':g['center_topocentric_air_angstrom'],'newly_unresolved_events':len(g['member_ids']),'selected_epochs':g['epoch_count'],'duration_days':duration,'berv_span_km_s':span,'barycentric_pairwise_median_r':f['barycentric']['pairwise_correlation_summary']['median'],'topocentric_pairwise_median_r':f['topocentric']['pairwise_correlation_summary']['median'],'barycentric_LOO_min_r':f['barycentric']['leave_one_out_correlation_summary']['min'],'broad3_signed_amplitude_median':f['barycentric']['broad3_amplitude_summary']['median'],'followup_finding':finding})
    for rid in g['member_ids']:
        m=mapping[rid]
        events.append({'review_id':rid,'group_id':gid,'target':g['target'],'original_exposure':g['reference_dp_id'] if len(g['member_ids'])==1 else m['dp_id'],'original_cumulative_status_preserved':m['prior_followup_status'],'mapping_followup_status_preserved':m['followup_status'],'selected_epochs':g['epoch_count'],'followup_finding':finding,'barycentric_pairwise_median_r':f['barycentric']['pairwise_correlation_summary']['median'],'topocentric_pairwise_median_r':f['topocentric']['pairwise_correlation_summary']['median'],'evidence':reason,'origin_confirmed':False})
events.sort(key=lambda r:r['review_id']);writecsv(OUT/'EVENT_FOLLOWUP.csv',events);writecsv(OUT/'GROUP_SUMMARY.csv',summary)
dump(OUT/'VISUAL_INTERPRETATION.json',{'method':'All 15 groups visually inspected on four complete two-frame overview pages; N06 additionally inspected as a detailed figure. Findings are descriptive, not preregistered significance thresholds.','groups':visual})
dump(OUT/'SELECTION_PROVENANCE.json',{'mapping_dispositions_path':str(mapping_path.relative_to(ROOT)),'sha256':sha(mapping_path),'event_count':31,'selected_ids':sorted(selected),'all_31_confirmed_newly_unresolved':True,'frozen_plan_unchanged':True,'note':'Parent supplied the 31 newly-unresolved IDs before the expanded extraction. The final mapping CSV is now cross-checked without modifying the already-frozen comparison plan or original tables.'})
s=json.loads((OUT/'SUMMARY.json').read_text())
dump(OUT/'FOLLOWUP_SUMMARY.json',{'newly_unresolved_events':31,'epoch_followup_event_counts':{'PERSISTENT_BARYCENTRIC_SPECTRAL_STRUCTURE':31},'group_counts':{'PERSISTENT_BARYCENTRIC_SPECTRAL_STRUCTURE':15},'total_selected_input_exposures':63,'group_epoch_pairs':162,'all_profiles_complete':True,'all_original_statuses_preserved':True,'visual_review_complete':True,'numerical_audit':'PASSED: 18 profiles in a fresh process','new_main_observation_credit':0,'important_exception':'N06/V2-0139 has only nine epochs clustered into three nights; pairwise median alone overstates the independent temporal information. Later-epoch leave-one-out profiles favor barycentric alignment.'})
# Explicit event × all-selected-epoch exports retain the fixed shared group center.
for folder in [OLD,OUT]:
    gs=json.loads((folder/'GROUPS.json').read_text()); mm=readcsv(folder/'ALL_EPOCH_MEASUREMENTS.csv');ge={g['group_id']:g for g in gs};expanded=[]
    for r in mm:
        for rid in ge[r['group_id']]['member_ids']:
            expanded.append({'review_id':rid,'event_center_bary_air_angstrom':ge[r['group_id']]['member_centers_bary_air_angstrom'][ge[r['group_id']]['member_ids'].index(rid)],'measurement_uses_group_center':True,**r})
    writecsv(folder/'EVENT_ALL_EPOCH_MEASUREMENTS.csv',expanded)
    assert len({r['review_id'] for r in expanded})==len({rid for g in gs for rid in g['member_ids']})
# Cross-stage union is metadata-only; original group centers and profiles stay unchanged.
old_events=readcsv(OLD/'EVENT_FOLLOWUP.csv');combined=[]
for stage,ee in [('epoch64_followup',old_events),('epoch31_followup',events)]:
    for e in ee:
        combined.append({'review_id':e['review_id'],'stage':stage,'group_id':e['group_id'],'target':e['target'],'original_exposure':e['original_exposure'],'original_cumulative_status_preserved':e.get('original_cumulative_status_preserved',e.get('original_unresolved_status_preserved')),'latest_origin_status_preserved':'UNRESOLVED_SPECTRAL_FEATURE','selected_epochs':e['selected_epochs'],'followup_finding':e['followup_finding'],'barycentric_pairwise_median_r':e['barycentric_pairwise_median_r'],'topocentric_pairwise_median_r':e['topocentric_pairwise_median_r'],'origin_confirmed':False})
assert len(combined)==95 and len({e['review_id'] for e in combined})==95
combined.sort(key=lambda r:r['review_id']);writecsv(OUT/'COMBINED_95_EVENT_FOLLOWUP.csv',combined)
inputs=[json.loads((folder/'INPUT_MANIFEST.json').read_text()) for folder in [OLD,OUT]]
unique={r['dp_id']:r for data in inputs for r in data};all_groups=json.loads((OLD/'GROUPS.json').read_text())+json.loads((OUT/'GROUPS.json').read_text())
centers=[]
for g in all_groups:
    for rid,lam in zip(g['member_ids'],g['member_centers_bary_air_angstrom']):centers.append({'review_id':rid,'target':g['target'],'bary_air_angstrom':lam,'measured_group':g['group_id']})
union=[]
for target in sorted({r['target'] for r in centers}):
    for r in sorted([r for r in centers if r['target']==target],key=lambda r:(r['bary_air_angstrom'],r['review_id'])):
        if not union or union[-1]['target']!=target or r['bary_air_angstrom']-union[-1]['first_center']>.1:
            union.append({'union_metadata_group':f'U{len(union)+1:02d}','target':target,'first_center':r['bary_air_angstrom'],'member_ids':[],'measured_group_ids':[]})
        union[-1]['member_ids'].append(r['review_id'])
        if r['measured_group'] not in union[-1]['measured_group_ids']:union[-1]['measured_group_ids'].append(r['measured_group'])
dump(OUT/'COMBINED_95_METADATA_GROUPS.json',{'purpose':'Metadata-only overlap accounting, using the same maximum span 0.10 Angstrom rule. No flux was re-extracted or correlations recomputed for these union groups.','groups':union})
dump(OUT/'COMBINED_95_SUMMARY.json',{'events':95,'finding_counts':dict(collections.Counter(e['followup_finding'] for e in combined)),'distinct_targets':len({e['target'] for e in combined}),'unique_selected_input_exposures':len(unique),'cohort_exposure_counts':dict(collections.Counter(r['cohort'] for r in unique.values())),'separately_frozen_measured_groups':len(all_groups),'metadata_union_groups':len(union),'measured_group_epoch_pairs':307+162,'frame_profiles':614+324,'explicit_event_epoch_frame_rows':1400+676,'pair_count_warning':'The 43 separately frozen groups overlap in wavelength; 469 group-epoch pairs are not 469 independent observations. Union metadata groups were not remeasured.','all_origin_statuses_preserved':True,'new_main_observation_credit':0})
print('reports complete',len(events),len(unique),len(union))
