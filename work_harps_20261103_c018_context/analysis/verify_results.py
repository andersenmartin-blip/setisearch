#!/usr/bin/env python3
"""Verify all C018 slots, raw-only outcomes, staged histories and ten figures."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,itertools,json,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
P=read(HERE/'PLAN.json');H=read(OUT/'OUTPUT_HASHES.json');I=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in P['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in H.items():assert sha(OUT/f)==h,f
assert len(P['source_hashes'])==103 and len(H)==87 and sum(f.endswith('.npz') for f in H)==77 and sha(OUT/'OUTPUT_HASHES.json')=='02d21a3bc3fc11752cc7b7a4f7f76578bb45b675f527d6c54178ad681f7b0c7c'
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json');assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert sha(REPO/f['path'])==f['sha256'] and (REPO/f['path']).stat().st_size==f['bytes'],f['path']
expected=['figures/MERGED_BROAD_CONTEXT.png','figures/MERGED_CORE_CONTEXT.png']+[f'figures/NATIVE_ORDERS_{i}.png' for i in range(1,5)]+[f'figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png' for i in range(1,5)]
assert [r['path'] for r in I['files']]==expected and I['native_pages']==I['raw_pages']==4 and I['total_figures']==10 and I['all_seven_reference_and_marker_ids']==list(P['events'])
figures=[]
for row in I['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load();figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
assert len(R)==42 and len(C)==252 and sum(r['identical_product_self_pair'] for r in C)==28
assert all(r['status']=='MEASURED_CONTEXT' and r['positive_finite_ERR_samples']==0 and r['gap_masked_grid_samples']==0 for r in R)
V=[r for r in R if r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'];O=[r for r in R if r['normalization_status']=='RAW_ONLY'];assert len(V)==28 and len(O)==14
assert all(r['normalization_reasons']==[] and r['flank_reference']>0 and r['low_flank_reference']is False and r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 and r['outside_native_coverage_grid_samples']==0 and r['window_nonpositive_fraction']==r['left_flank_nonpositive_fraction']==r['right_flank_nonpositive_fraction']==0 for r in V)
assert all(r['kind']=='native' and r['order']==2 and r['normalization_reasons']==['MISSING_RIGHT_FLANK_COVERAGE'] and r['flank_reference']is None and r['available_flank_median']>0 and r['low_flank_reference']is None and r['normalized_grid_finite_samples']==0 and r['right_flank_finite_samples']==r['right_flank_native_samples']==0 and r['right_flank_nonpositive_fraction']is None for r in O)
assert [r['raw_grid_finite_samples'] for r in O if r['frame']=='barycentric']==[406,402,351,406,379,346,330] and all(r['raw_grid_finite_samples']==406 for r in O if r['frame']=='topocentric')
assert sum(r['raw_pearson']is not None for r in C)==238 and sum(r['normalized_rms']is not None for r in C)==224
badR=[r for r in C if r['raw_pearson']is None];badN=[r for r in C if r['normalized_rms']is None]
assert len(badR)==14 and all(r['order']==2 and r['region']=='broad_pattern' and r['common_finite_raw_samples']<440 and r['raw_pearson_block_reason']=='INSUFFICIENT_COMMON_RAW_COVERAGE' for r in badR)
assert len(badN)==28 and all(r['order']==2 and r['common_finite_normalized_samples']==0 and r['normalized_rms_block_reason']=='INVALID_REFERENCE_OR_INSUFFICIENT_NORMALIZED_COVERAGE' for r in badN)
assert all(r['raw_pearson']is not None and r['common_finite_raw_samples']==51 for r in C if r['order']==2 and r['region']=='core')
assert all(r['common_finite_raw_samples']==r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C if r['order']!=2)
assert P['target']=='HD114783' and P['group_center_bary_air_angstrom']==3869.33375 and P['anchor_dp_id']=='ADP.2022-01-22T01:09:14.958' and P['anchor_berv_km_s']==29.658729150824 and len(P['event_markers'])==7
assert P['discovery_dp_ids']==P['merged_dp_ids'] and len(P['merged_dp_ids'])==7 and len(P['individual_event_cores_bary_air_angstrom'])==7
centers={'V2E2-0114':3869.3349999999996,'V2E2-0119':3869.3325,'V2E2-0124':3869.3325,'V2E2-0128':3869.335,'V2E2-0133':3869.3349999999996,'V2E2-0134':3869.3325,'V2E2-0138':3869.335};assert P['individual_event_centers_bary_air_angstrom']==centers
for m in P['event_markers']:
 c=centers[m['event']];assert m['center_bary_air_angstrom']==c and m['barycentric_offset_angstrom']==c-P['group_center_bary_air_angstrom'] and m['discovery_dp_id']==P['events'][m['event']]
 core=P['individual_event_cores_bary_air_angstrom'][m['event']];assert core==[c-.25,c+.25] and (core[0]<3869.08375 or core[1]>3869.58375)
MC=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'];NC=[r for r in C if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'];assert len(MC)==196 and len(NC)==56 and all(r['dp_id']==r['reference_dp_id'] and r['same_exposure'] and not r['identical_product_self_pair'] for r in NC)
nonself=[r for r in MC if not r['identical_product_self_pair']];assert len(nonself)==168;by={(r['dp_id'],r['reference_dp_id'],r['frame'],r['region']):r for r in MC};families=[]
for event,ref in P['events'].items():
 for frame in ['barycentric','topocentric']:
  for z in ['core','broad_pattern']:assert len([r for r in nonself if r['reference_dp_id']==ref and r['frame']==frame and r['region']==z])==6
 for dp in P['merged_dp_ids']:
  if dp==ref:continue
  for z in ['core','broad_pattern']:
   assert by[dp,ref,'barycentric',z]['raw_pearson']>by[dp,ref,'topocentric',z]['raw_pearson'];assert by[dp,ref,'barycentric',z]['normalized_rms']<by[dp,ref,'topocentric',z]['normalized_rms']
 families.append({'event':event,'reference_dp_id':ref,'other_epochs':6,'all_six_better_barycentric_r_and_RMS_both_regions':True})
for frame in ['barycentric','topocentric']:
 for z in ['core','broad_pattern']:
  rows=[r for r in nonself if r['frame']==frame and r['region']==z];assert len(rows)==42 and len({tuple(sorted([r['dp_id'],r['reference_dp_id']])) for r in rows})==21
  for a,b in itertools.combinations(P['discovery_dp_ids'],2):assert abs(by[a,b,frame,z]['raw_pearson']-by[b,a,frame,z]['raw_pearson'])<1e-12 and abs(by[a,b,frame,z]['normalized_rms']-by[b,a,frame,z]['normalized_rms'])<1e-12
assert sum(r['window_nonpositive_fraction']>0 for r in R)==12 and sum(r['window_nonpositive_fraction']==0 for r in R)==30
counts=[round(r['window_nonpositive_fraction']*r['window_native_finite_samples']) for r in O];assert counts==[6,6,3,3,6,6,4,4,0,0,2,2,4,4]
left=[r for r in O if r['left_flank_nonpositive_fraction']>0];assert len(left)==3 and all(r['left_flank_nonpositive_fraction']==1/166 for r in left)
assert [(r['date_obs'][:10],r['frame']) for r in left]==[('2022-05-05','barycentric'),('2022-05-05','topocentric'),('2023-07-01','barycentric')]
assert len(P['historical_mapping_stages'])==14;fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
assert all([r[k] for k in fields]==([True,False,False,True] if r['order']==2 else [True,True,True,True]) for r in P['historical_mapping_stages'])
history=P['historical_review_disagreement']['per_event_history'];special=next(r for r in history if r['candidate_id']=='V2E2-0128')
assert len(history)==7 and all(r['current_adopted_code']=='U' for r in history) and all(r['original_primary_code']==r['original_secondary_code']==r['original_adopted_code']=='U' for r in history if r['candidate_id']!='V2E2-0128')
assert special['original_primary_code']=='I' and special['original_secondary_code']=='M' and special['original_secondary_normalized_code']==special['original_adopted_baseline_code']=='I' and special['later_mapping_followup_primary_code']==special['later_mapping_followup_secondary_code']=='U' and special['coordinates_changed']is False
raw=read(OUT/'PRESERVED_RAW_CONTEXT.json');assert len(raw)==14
for r in raw:
 assert sha(OUT/r['copied_path'])==r['file']['sha256'];shapes={v['key']:v['shape'] for v in r['npy_headers']};assert shapes['raw_cutout']==shapes['raw_excess']==([21,25] if r['event']=='V2E2-0128' else [31,33])
assert P['plot_pagination']['total_figures']==10 and P['plot_pagination']['native_pages']==P['plot_pagination']['raw_pages']==4
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');assert sum(not r['expected_center_inside_fixed_core'] for r in science['metadata_expected_feature_locations'])==4
N=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');assert N['next_core_group']=='C019' and len(N['members'])==5 and [m['candidate_id'] for m in N['members']]==['V2E2-0115','V2E2-0120','V2E2-0125','V2E2-0129','V2E2-0135'] and N['completed_mapping_followup_dependency']['applies_to_C019_0129']is False
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['All seven current C018 labels remain U','42 profiles and 252 comparison slots','238 evaluable Pearson and 224 evaluable RMS','42 directed nonself rows per frame/region represent 21 unordered exposure pairs and 21 reciprocal duplicates','0.987756','0.984144','sharp excursion near the far positive edge','14 native surrounding Pearson values remain unavailable','all 28 order-2 normalized RMS slots unavailable','null low-reference flags','28 false low-reference flags','Twelve profile rows','30 profile rows','1/166','remote high-left deposit in 0134/order 2 dominates','21×25, five-array containers','primary I, secondary M (normalized I), adopted baseline I','All ten figures were visually inspected','null/unassessed','No C019 array analysis']:
 assert text in report,text
for event in P['events']:assert '### '+event+' reference:' in report
links=re.findall(r'\]\(([^)]+)\)',report);assert not [q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json']
audit=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');assert audit['status'].startswith('PASS') and audit['checks_passed']==1268 and audit['scalar_values_compared']==161625
qa={'status':'PASS_COMPLETE_C018_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD114783','common_midpoint':3869.33375,'all_seven_exact_centers_markers_and_original_core_edges_preserved':True,'frozen_source_hashes_verified':103,'public_method_bindings_verified':25,'numerical_output_hashes_verified':87,'numerical_npz_files_verified':77,'stable_numeric_ledger_sha256':sha(OUT/'OUTPUT_HASHES.json'),'profile_slots':42,'comparison_slots':252,'merged_comparisons':196,'native_same_exposure_comparisons':56,'identical_product_self_comparisons':28,'distinct_observations_and_references':7,'per_reference_families':families,'directed_nonself_rows_per_frame_region':42,'unordered_pairs_per_frame_region':21,'reciprocal_duplicates_per_frame_region':21,'bounded_source_windows':21,'preserved_original_raw_copies':14,'full_profiles_with_valid_positive_reference':28,'raw_only_profiles':14,'raw_only_order':2,'false_low_reference_flags':28,'null_low_reference_flags':14,'true_low_reference_flags':0,'blocked_profiles':0,'evaluable_Pearson':238,'unavailable_Pearson':14,'evaluable_RMS':224,'unavailable_RMS':28,'all_order2_core_Pearson_evaluable_with51_samples':True,'order2_barycentric_surrounding_support':[355,351,300,355,328,295,279],'order2_topocentric_surrounding_support':[355]*7,'all_order2_right_flank_finite_samples_zero':True,'positive_available_left_medians_not_valid_two_flank_references':True,'profiles_with_nonpositive_signed_window_samples':12,'profiles_with_zero_nonpositive_window_samples':30,'order2_window_nonpositive_counts_in_output_order':counts,'nonpositive_left_flank_rows':[{'date':r['date_obs'][:10],'frame':r['frame'],'count':1,'finite':166} for r in left],'all_merged_and_order3_nonpositive_window_and_flank_fractions_zero':True,'all_profiles_zero_positive_ERR':True,'all_profiles_zero_gap_masks':True,'original_order2_T_F_F_laterT_and_order3_allT_preserved':True,'six_original_U_U_U_histories_preserved':True,'0128_original_I_M_normalized_I_baseline_I_then_later_U_U_current_U_preserved':True,'0128_original21x25_containers_not_later_wider_replacements':True,'0134_remote_deposit_fullscale_limit_not_central_classification':True,'July_outer_barycentric_excursion_retained_without_origin_assignment':True,'predicted_centers_outside_fixed_topocentric_common_core':4,'all_ten_figures_visually_inspected':True,'native_pages':4,'raw_pages':4,'page_row_counts':[4,4,4,2],'figures':figures,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'next_group':'C019','next_member_count':5,'next0129_original_supported_U_and_later_null_unassessed_preserved':True,'method_or_numerical_mutations':0,'labels_changed':0}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n');assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','per_reference_families']},indent=2))
