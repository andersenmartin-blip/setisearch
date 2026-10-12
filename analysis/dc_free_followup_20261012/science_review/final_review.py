#!/usr/bin/env python3
"""Review saved selection/context JSON only; no power reads or new ranking."""
import json
import hashlib
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'next_dc'
OUT=Path(__file__).resolve().parent
PINS={}
def read(name):
    path=BASE/name
    raw=path.read_bytes()
    PINS[str(path.relative_to(ROOT))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return json.loads(raw)

selection=read('ranking/SELECTED_TOP9.json')
context=read('crossscan/results/CONTEXT_PROFILES.json')
selection_qa=read('qa/selection/QA_RECEIPT.json')
context_qa=read('qa/context/QA_RECEIPT.json')
crops=read('qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json')
execution=read('crossscan/results/EXECUTION_RECEIPT.json')
root_scope=read('ROOT_SCOPE.json')
assert selection_qa['status']=='PASS' and selection_qa['mismatches']==0
assert context_qa['status']=='PASS_INDEPENDENT_FULLRAW_NORMALIZATION_AND54_FIXED_CONTEXTS'
assert not context_qa['mismatches']
assert context_qa['fullcore_normalization_independently_recomputed'] is True
assert root_scope['original_AB']=='FAIL_CLOSED'
assert root_scope['protected_2016_holdouts']=='CLOSED'
assert root_scope['new_telescope_requests']==0
counts=selection['counts']
assert counts['stored_core_winners']==2289
assert counts['excluded_by_DC_contact']==15
assert counts['eligible_DC_untouched']==2274
assert counts['selected_records']==9
assert len(context['profiles'])==54
profiles=context['profiles']
own=[p for p in profiles if p['is_own_primary_scan']]
assert len(own)==9

# Exact physical score-box and normalizing-core geometry, not an association search.
def physical_key(p):
    rec=p['selected_original_record']
    return (p['context_scan_id'],p['width_channels'],tuple(p['rounded_absolute_centers']),
            rec['native_chunk_index'],rec['core_q'])
physical_groups=defaultdict(list)
by_template=defaultdict(list)
for p in profiles:
    physical_groups[physical_key(p)].append(p['profile_id'])
    by_template[p['template_id']].append(p)
assert len(physical_groups)==48
template_groups=defaultdict(list)
for name,ps in by_template.items():
    signature=tuple(sorted(physical_key(p) for p in ps))
    template_groups[signature].append(name)
assert len(template_groups)==8
shared_groups=[names for names in template_groups.values() if len(names)>1]
assert shared_groups==[['HIP97319_rank1','HIP97461_rank1']]
shared_names=set(shared_groups[0])
common=by_template[shared_groups[0][0]]
scan_order=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
common_by_scan={p['context_scan_id']:p for p in common}
common_record=common[0]['selected_original_record']
assert common_record['reference_source_channel']==179970594
assert abs(common_record['drift_hz_s'])<1e-12
other_templates=[p for p in profiles if p['template_id'] not in shared_names]
other_own=[p for p in other_templates if p['is_own_primary_scan']]
other_context=[p for p in other_templates if not p['is_own_primary_scan']]
assert len(other_templates)==42 and len(other_own)==7 and len(other_context)==35
dc_contacts=sum(len(p['DC_contact_rows_any_frozen_center']) for p in profiles)
assert dc_contacts==0
positive_rows=[p['positive_row_count'] for p in own]
max_fraction=[p['positive_row_contribution_max_fraction'] for p in own]
effective_rows=[p['positive_contribution_effective_rows'] for p in own]
assert min(positive_rows)==14 and max(positive_rows)==16
assert max(max_fraction)<0.19
assert len(context['normalization_records'])==48
assert context['existing_full16_normalizations_used']==24
assert context['new_full16_normalizations']==24
assert crops['crop_count']==48 and crops['bytes']==37247328
assert context_qa['counts']['preserved_normalization_crops']==48
assert context_qa['counts']['preserved_normalization_crop_bytes']==37247328
assert context_qa['counts']['distinct_fullcore_normalization_queries']==48
crop_shapes=sorted({tuple(c['shape']) for c in crops['crops']})
assert crop_shapes==[(16,12096)]
script_bytes=Path(__file__).read_bytes()
PINS[str(Path(__file__).resolve().relative_to(ROOT))]={'bytes':len(script_bytes),
    'sha256':hashlib.sha256(script_bytes).hexdigest()}

review={
 'schema':'SETI_DC_UNTOUCHED_NEW_PHASE_FINAL_SCIENTIFIC_REVIEW_V1',
 'status':'PASS_SAVED_RESULTS_AND_LIMITED_EXPLORATORY_INTERPRETATION',
 'input_pins':PINS,
 'activity':'Saved JSON scalar/geometry review only. No raw power, cached score arrays, detector grid, eligibility query or new ranking executed.',
 'selection_counts':counts,
 'physical_denominators':{
    'selected_logical_records':9,'own_primary_logical_profiles':9,
    'selected_distinct_physical_measurement_templates':8,
    'fixed_logical_context_profiles':54,'distinct_physical_context_score_boxes':48,
    'duplicate_logical_contexts':6,
    'total_nonown_logical_profiles':45,
    'shared_line_logical_profiles':12,'shared_line_distinct_physical_profiles':6,
    'remaining_template_count':7,'remaining_own_profiles':7,'remaining_nonown_profiles':35,
    'independent_source_or_visit_count_not_established':True},
 'shared_near_zero_drift_template':{
    'selected_in':shared_groups[0],
    'source_channel':common_record['reference_source_channel'],
    'frequency_MHz':common_record['frequency_hz_at_own_first_midpoint']/1e6,
    'nominal_drift_Hz_s':common_record['drift_hz_s'],
    'same_physical_measurement_geometry_all6scans':True,
    'fixed_context_scores':[{'scan_id':s,'target':common_by_scan[s]['context_target'],
        'original_role':common_by_scan[s]['original_acquisition_role'],
        'score':common_by_scan[s]['fixed_robust_box_track_score']} for s in scan_order],
    'interpretation':'The same nominal stationary frequency template has positive fixed scores in all six historical pointings and is selected in two original OFF-star scans. This favors a common interference or instrumental explanation over an excess restricted to one target. It does not prove terrestrial RFI or identify a specific hardware cause; no formal qualified OFF veto is asserted.'},
 'remaining7_templates':{
    'own_score_min':min(p['fixed_robust_box_track_score'] for p in other_own),
    'own_score_max':max(p['fixed_robust_box_track_score'] for p in other_own),
    'other5_per_template_context_count':len(other_context),
    'other_context_score_min':min(p['fixed_robust_box_track_score'] for p in other_context),
    'other_context_score_max':max(p['fixed_robust_box_track_score'] for p in other_context),
    'interpretation':'Seven additional exposed winning templates show own-primary excesses without strong recurrence on their transported fixed paths in the five other scans. They remain unconfirmed selections. Post-selection correlated noise, time-variable interference and other artifacts remain possible; lack of fixed-path recurrence does not establish a sky source or rule out an intermittent signal.'},
 'own_primary_row_distribution':{
    'positive_rows_min':min(positive_rows),'positive_rows_max':max(positive_rows),
    'largest_positive_row_mass_fraction_min':min(max_fraction),
    'largest_positive_row_mass_fraction_max':max(max_fraction),
    'positive_effective_rows_min':min(effective_rows),'positive_effective_rows_max':max(effective_rows),
    'interpretation':'The saved score mass is spread over multiple rows and is not dominated by one positive row. This rejects a single-row-dominated explanation for these scores only; it is not an independent coherence, significance or origin test.'},
 'transported_context_DC_contact_rows':dc_contacts,
 'normalization_and_numerical_QA':{
    'selection_QA_status':selection_qa['status'],
    'context_QA_status':context_qa['status'],
    'all48_fullcore_normalizations_independently_recomputed':True,
    'saved_full16_constants_reused_in_producer':24,
    'new_full16_normalizations_in_producer':24,
    'not_merely_conditional_on_saved_normalization_in_this_new_QA_scope':True,
    'maximum_errors':context_qa['max_absolute_errors'],
    'raw_normalization_crops_preserved':48,
    'raw_normalization_crop_shape':list(crop_shapes[0]),
    'raw_normalization_crop_total_bytes':37247328,
    'precision_wording':'Fullcore row medians/MAD scales match exactly; largest winsorized-location difference3.382710778154774e-17. Fixed-score reproduction differs up to1.7763568394002505e-15; original own-score linkage up to1.2434497875801753e-14. Do not report1e-17 as the maximum error across all score checks.'},
 'limitations':[
    'The9selected records represent8distinct physical measurement templates, not9independent detections or8independent physical sources.',
    'All6context scans belong to one historical visit and include different target pointings; no independent repeated visit of any selected star was established.',
    'The eligibility/ranking was newly declared on previously exposed core maxima, not a blind discovery test.',
    'Only winning core tuples were eligible. Discarded or retained cores can hide other carrier maxima and lower-ranked width/drift hypotheses.',
    'Exact noncontact with three known DCbins does not imply freedom from other RFI or instrumental effects.',
    'Fixed box-track scores are not calibrated SNR, false-alarm probabilities, sensitivity, flux or EIRP.',
    'No formal detection threshold, qualified sky detection, automatic OFF veto, A/B qualification or protected2016holdout opening follows.',
    'Numerical QA establishes reproducibility of the disclosed preprocessing and scores, not astrophysical origin.'
 ],
 'next_science_priority':{
    'action':'Freeze a new streaming inspection of all previously saved per-carrier maximum arrays across the same2289target/core domains; annotate the saved winning width/drift path at each carrier for frozen DC contact and rank retained carrier winners without recalculating the detector grid.',
    'reason':'This can recover exposed clean carrier maxima concealed by a DC-contacting or different overall core winner and can reveal multiple useful templates inside a retained core.',
    'scope_size':'Up to2289x4096=9375744existing carrier maxima; these are correlated maxima, not9375744independent tests.',
    'ranking_and_geometry_rules':'Freeze source hashes, exact original rounding/time convention, own-window DC eligibility, stable tie order and descriptive alias grouping before selecting new raw profiles. Preserve original scores and never adapt the filter after power inspection.',
    'raw_followup':'Analyze only a small predetermined number of the newly selected carrier templates with full501halos and fixed six-scan paths using existing restored2017raw data; independently verify numerical results.',
    'remaining_incompleteness':'If a carrier winning hypothesis touches DC, another clean width/drift hypothesis at that same carrier remains hidden. Recovering that requires a separate new detector evaluation, which this cached-map phase must not imply.',
    'no_new_telescope_HTTP_requests':True,'no_new_observation_or_coverage':True,
    'not_executed_by_this_review':True},
 'limits_preserved':{'original_AB':'FAIL_CLOSED_UNCHANGED','protected2016':'CLOSED',
     'closed2019transport':'UNCHANGED','new_telescope_requests':0,
     'new_detector_grid':False,'qualified_SETI_detection':False,'calibrated_SNR_FAP':False},
 'remaining_corrections':[]
}
(OUT/'FINAL_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'physical_templates':8,'physical_profiles':48,
    'remaining7_other_context_count':35,'remaining7_other_score_range':[
        review['remaining7_templates']['other_context_score_min'],
        review['remaining7_templates']['other_context_score_max']]},indent=2))
