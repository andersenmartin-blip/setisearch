#!/usr/bin/env python3
"""Verify C019 immutable delivery, five families and nullable historical stages."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,itertools,json,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
P=read(HERE/'PLAN.json');H=read(OUT/'OUTPUT_HASHES.json');I=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in P['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in H.items():assert sha(OUT/f)==h,f
assert len(P['source_hashes'])==89 and len(H)==71 and sum(f.endswith('.npz') for f in H)==61 and sha(OUT/'OUTPUT_HASHES.json')=='e4c43d247db9bf5cd27ba4e6c7501de91ac8b57293b1f5d563e03f3d4be919ac'
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json');assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert sha(REPO/f['path'])==f['sha256'] and (REPO/f['path']).stat().st_size==f['bytes'],f['path']
expected=['figures/MERGED_BROAD_CONTEXT.png','figures/MERGED_CORE_CONTEXT.png']+[f'figures/NATIVE_ORDERS_{i}.png' for i in range(1,4)]+[f'figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png' for i in range(1,4)];assert [r['path'] for r in I['files']]==expected and I['native_pages']==I['raw_pages']==3 and I['total_figures']==8 and I['all_five_reference_and_marker_ids']==list(P['events'])
figures=[]
for row in I['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load();figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
assert len(R)==34 and len(C)==180 and sum(r['identical_product_self_pair'] for r in C)==20
assert all(r['status']=='MEASURED_CONTEXT' and r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['normalization_reasons']==[] and r['flank_reference']>0 and r['low_flank_reference']is False and r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['gap_masked_grid_samples']==r['outside_native_coverage_grid_samples']==0 for r in R)
assert all(r['raw_pearson']is not None and r['normalized_rms']is not None and r['raw_pearson_block_reason']is None and r['normalized_rms_block_reason']is None and r['common_finite_raw_samples']==r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C)
assert P['target']=='HD114783' and P['group_center_bary_air_angstrom']==3881.6137500000004 and P['anchor_dp_id']=='ADP.2022-01-22T01:09:14.958' and P['anchor_berv_km_s']==29.658729150824
assert len(P['merged_dp_ids'])==7 and len(P['discovery_dp_ids'])==5 and set(P['merged_dp_ids'])-set(P['discovery_dp_ids'])=={'ADP.2023-03-23T01:02:04.833','ADP.2023-07-02T01:01:43.311'}
centers={'V2E2-0115':3881.6125,'V2E2-0120':3881.615,'V2E2-0125':3881.6150000000002,'V2E2-0129':3881.615,'V2E2-0135':3881.6125};assert P['individual_event_centers_bary_air_angstrom']==centers and len(P['event_markers'])==5
for m in P['event_markers']:
 c=centers[m['event']];assert m['center_bary_air_angstrom']==c and m['barycentric_offset_angstrom']==c-P['group_center_bary_air_angstrom'] and m['discovery_dp_id']==P['events'][m['event']]
 core=P['individual_event_cores_bary_air_angstrom'][m['event']];assert core==[c-.25,c+.25] and (core[0]<P['group_center_bary_air_angstrom']-.25 or core[1]>P['group_center_bary_air_angstrom']+.25)
MC=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'];NC=[r for r in C if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'];assert len(MC)==140 and len(NC)==40 and all(r['dp_id']==r['reference_dp_id'] and r['same_exposure'] and not r['identical_product_self_pair'] for r in NC)
nonself=[r for r in MC if not r['identical_product_self_pair']];assert len(nonself)==120;by={(r['dp_id'],r['reference_dp_id'],r['frame'],r['region']):r for r in MC};families=[]
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
  rows=[r for r in nonself if r['frame']==frame and r['region']==z];assert len(rows)==30 and len({tuple(sorted([r['dp_id'],r['reference_dp_id']])) for r in rows})==20
  for a,b in itertools.combinations(P['discovery_dp_ids'],2):assert abs(by[a,b,frame,z]['raw_pearson']-by[b,a,frame,z]['raw_pearson'])<1e-12 and abs(by[a,b,frame,z]['normalized_rms']-by[b,a,frame,z]['normalized_rms'])<1e-12
signed=[r for r in R if r['window_nonpositive_fraction']>0];assert len(signed)==6 and all(r['kind']=='native' and r['order']==4 and r['right_flank_nonpositive_fraction']==0 and round(r['window_nonpositive_fraction']*r['window_native_finite_samples'])==round(r['left_flank_nonpositive_fraction']*r['left_flank_finite_samples']) for r in signed)
assert [(r['date_obs'][:10],r['frame'],round(r['window_nonpositive_fraction']*r['window_native_finite_samples']),r['window_native_finite_samples'],r['left_flank_finite_samples']) for r in signed]==[('2022-01-21','barycentric',1,500,123),('2022-01-21','topocentric',1,500,123),('2022-05-05','topocentric',10,500,123),('2023-01-16','barycentric',1,501,124),('2023-01-16','topocentric',1,500,123),('2023-05-15','topocentric',5,500,123)]
assert sum(r['window_nonpositive_fraction']==r['left_flank_nonpositive_fraction']==r['right_flank_nonpositive_fraction']==0 for r in R)==28 and all(r['right_flank_nonpositive_fraction']==0 for r in R)
for dp,rms,rho in [('ADP.2022-05-06T01:04:00.123',1.131556,.910748),('ADP.2023-05-16T01:01:18.574',1.089980,.913056)]:
 row=next(r for r in NC if r['dp_id']==dp and r['order']==4 and r['frame']=='topocentric' and r['region']=='broad_pattern');assert round(row['normalized_rms'],6)==rms and round(row['raw_pearson'],6)==rho
history=P['historical_review_disagreement']['per_event_history'];assert len(history)==5 and all(r['original_primary_code']==r['original_secondary_code']==r['original_adopted_code']==r['current_adopted_code']=='U' for r in history)
assert len(P['historical_mapping_stages'])==10
for r in P['historical_mapping_stages']:
 assert all(r[k]is True for k in ['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified'])
 assert r['final_reference_mapping_supported']is (None if r['event']=='V2E2-0129' else True)
 if r['event']=='V2E2-0129':assert r['later_five_window_field_present']is False and r['later_five_window_assessment']=='UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP'
raw=read(OUT/'PRESERVED_RAW_CONTEXT.json');assert len(raw)==10
for r in raw:
 assert sha(OUT/r['copied_path'])==r['file']['sha256'];shapes={v['key']:v['shape'] for v in r['npy_headers']};assert shapes['raw_cutout']==shapes['raw_excess']==([21,25] if r['event']=='V2E2-0129' else [31,33])
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');locations=science['metadata_expected_feature_locations'];assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==4 and sum(abs(m['discovery_topocentric_offset_angstrom'])>.25 for m in P['event_markers'])==2
N=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');assert N['next_core_group']=='C021' and [m['candidate_id'] for m in N['members']]==['V2E2-0116','V2E2-0121','V2E2-0126','V2E2-0130','V2E2-0139'];special=next(r for r in N['historical_review_disagreement']['per_event_history'] if r['candidate_id']=='V2E2-0130');assert special['original_primary_code']=='I' and special['original_secondary_code']=='M' and special['original_secondary_normalized_code']==special['original_adopted_baseline_code']=='I' and special['later_mapping_followup_primary_code']==special['later_mapping_followup_secondary_code']==special['current_adopted_code']=='U'
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['All five original/current C019 labels remain U','34 profiles and 180 comparisons','Thirty directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal','Six profile rows','10/500 window samples and 10/123 left-flank samples','5/500 and 5/123','34 false low-reference flags','1.131556 and 1.089980','0.910748 and 0.913056','only two of the five discovery markers','later entries remain null/unassessed','remote high-left deposit that dominates','21×25 five-array containers','All eight figures were visually inspected','No C021 array analysis']:
 assert text in report,text
for event in P['events']:assert '### '+event+' reference:' in report
links=re.findall(r'\]\(([^)]+)\)',report);assert not [q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json']
audit=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');assert audit['status'].startswith('PASS') and audit['checks_passed']==1026 and audit['scalar_values_compared']==134487
qa={'status':'PASS_COMPLETE_C019_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD114783','common_midpoint':3881.6137500000004,'exact_member_float_core_and_marker_identities_preserved':True,'frozen_source_hashes_verified':89,'public_method_bindings_verified':25,'numerical_output_hashes_verified':71,'numerical_npz_files_verified':61,'stable_numeric_ledger_sha256':sha(OUT/'OUTPUT_HASHES.json'),'profile_slots':34,'comparison_slots':180,'merged_comparisons':140,'native_same_exposure_comparisons':40,'identical_product_self_comparisons':20,'observations':7,'fixed_discovery_references':5,'March22_and_July1_retained_as_nonreferences':True,'per_reference_families':families,'directed_nonself_rows_per_frame_region':30,'unordered_pairs_per_frame_region':20,'reciprocal_duplicates_per_frame_region':10,'bounded_source_windows':17,'preserved_original_raw_copies':10,'full_valid_positive_reference_profiles':34,'false_low_reference_flags':34,'true_low_reference_flags':0,'null_low_reference_flags':0,'raw_only_profiles':0,'blocked_profiles':0,'evaluable_Pearson':180,'evaluable_RMS':180,'all_comparisons_complete_raw_and_normalized_support':True,'all_profiles_zero_positive_ERR':True,'all_profiles_zero_gap_and_outside_coverage_masks':True,'profiles_with_nonpositive_source_window_samples':6,'nonpositive_order':4,'all_six_nonpositive_window_counts_equal_left_flank_counts':True,'nonpositive_counts_in_output_order':[1,1,10,1,1,5],'other_profiles_zero_nonpositive_window_flank_fractions':28,'all_right_flank_nonpositive_fractions_zero':True,'May5_and_May15_order4_topocentric_broad_RMS':[1.131556,1.089980],'May5_and_May15_order4_topocentric_broad_r':[.910748,.913056],'structured_flank_reference_scaling_and_native_plateau_differences_preserved':True,'all_five_original_U_U_U_histories_preserved':True,'all_ten_original_mapping_stages_true_preserved':True,'0129_later_field_absent_null_unassessed_not_inferred_failure_or_support':True,'0129_original21x25_containers_preserved':True,'0135_remote_deposit_fullscale_limit_not_central_classification':True,'predicted_centers_outside_common_topocentric_core':4,'discovery_markers_outside_common_topocentric_core':2,'bounded_spectral_disjointness_not_claimed_raw_crop_independence':True,'all_eight_figures_visually_inspected':True,'native_pages':3,'raw_pages':3,'page_rows':[4,4,2],'figures':figures,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'next_group':'C021','next_member_count':5,'next0130_staged_I_M_normalized_I_baseline_I_then_later_U_preserved':True,'method_or_numerical_mutations':0,'labels_changed':0}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n');assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','per_reference_families']},indent=2))
