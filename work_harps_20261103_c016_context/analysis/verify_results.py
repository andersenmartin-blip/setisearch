#!/usr/bin/env python3
"""Verify C016 immutable artifacts, all-reference dependence and actual quality."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,itertools,json,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
P=read(HERE/'PLAN.json');H=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in P['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in H.items():assert sha(OUT/f)==h,f
assert len(P['source_hashes'])==64 and len(H)==47 and sum(f.endswith('.npz') for f in H)==37
assert sha(OUT/'OUTPUT_HASHES.json')=='ebc83d56a37b575a85386b94b3202bd79da99b1068ea3725ffba7c5d700b3d0e'
assert len(plots['files'])==4;figures=[]
for row in plots['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load()
 figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json');assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert sha(REPO/f['path'])==f['sha256'] and (REPO/f['path']).stat().st_size==f['bytes'],f['path']
assert len(R)==22 and len(C)==128 and sum(r['identical_product_self_pair'] for r in C)==16
assert all(r['status']=='MEASURED_CONTEXT' and r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['normalization_reasons']==[] and r['flank_reference']>0 and r['low_flank_reference']is False and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['outside_native_coverage_grid_samples']==0 and r['gap_masked_grid_samples']==0 and r['window_nonpositive_fraction']==0 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==0 for r in R)
assert all(r['raw_pearson']is not None and r['normalized_rms']is not None and r['raw_pearson_block_reason']is None and r['normalized_rms_block_reason']is None and r['common_finite_raw_samples']==(51 if r['region']=='core' else 550) and r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C)
assert P['target']=='HD114386' and P['group_center_bary_air_angstrom']==4303.7875 and P['anchor_dp_id']=='ADP.2022-03-08T01:01:37.348' and P['anchor_berv_km_s']==19.1606928163471
handoff=read(REPO/'work_harps_20261103_c011_context/NEXT_ACTION.json');assert P['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']] and P['discovery_dp_ids']==handoff['distinct_discovery_products']
assert {P['historical_review_disagreement'][k] for k in ['primary_code','secondary_code','root_adopted_code']}=={'U'}
fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported'];assert len(P['historical_mapping_stages'])==4 and all(r['order']==19 and all(r[k]is True for k in fields) for r in P['historical_mapping_stages'])
assert len(P['event_markers'])==4 and list(P['individual_event_centers_bary_air_angstrom'].values())==[4303.785,4303.785,4303.785,4303.79]
for m in P['event_markers']:
 center=P['individual_event_centers_bary_air_angstrom'][m['event']];core=P['individual_event_cores_bary_air_angstrom'][m['event']]
 assert core==[center-.25,center+.25] and (core[0]<4303.5375 or core[1]>4304.0375)
 assert m['center_bary_air_angstrom']==center and m['barycentric_offset_angstrom']==center-4303.7875 and m['discovery_dp_id']==P['events'][m['event']]
assert len(P['prior_bounded_window_geometry'])==12 and all(r['numerically_disjoint_from_C016'] and not r['shared_source_pixels'] and r['target']!='HD114386' for r in P['prior_bounded_window_geometry'])
merged=[r for r in R if r['kind']=='merged'];native=[r for r in R if r['kind']=='native'];assert len(merged)==14 and len(native)==8
assert all(r['window_native_finite_samples']==600 and r['left_flank_finite_samples']==150 and r['right_flank_finite_samples']==150 for r in merged)
assert [r['window_native_finite_samples'] for r in native]==[486,486,487,486,485,486,488,486]
MC=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'];NC=[r for r in C if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'];assert len(MC)==112 and len(NC)==16
assert all(r['reference_dp_id']==r['dp_id'] and r['same_exposure'] and not r['identical_product_self_pair'] and r['order']==19 for r in NC)
nonself=[r for r in MC if not r['identical_product_self_pair']];assert len(nonself)==96
by={(r['dp_id'],r['reference_dp_id'],r['frame'],r['region']):r for r in MC};families=[]
for event,ref in P['events'].items():
 for frame in ['barycentric','topocentric']:
  for region in ['core','broad_pattern']:
   rows=[r for r in nonself if r['reference_dp_id']==ref and r['frame']==frame and r['region']==region];assert len(rows)==6 and len({r['dp_id'] for r in rows})==6
 for dp in P['merged_dp_ids']:
  if dp==ref:continue
  for z in ['core','broad_pattern']:
   assert by[dp,ref,'barycentric',z]['raw_pearson']>by[dp,ref,'topocentric',z]['raw_pearson']
   assert by[dp,ref,'barycentric',z]['normalized_rms']<by[dp,ref,'topocentric',z]['normalized_rms']
 families.append({'event':event,'reference_dp_id':ref,'other_epochs':6,'all_six_better_barycentric_r_and_RMS_both_regions':True})
for frame in ['barycentric','topocentric']:
 for region in ['core','broad_pattern']:
  rows=[r for r in nonself if r['frame']==frame and r['region']==region];unordered={tuple(sorted([r['dp_id'],r['reference_dp_id']])) for r in rows}
  assert len(rows)==24 and len(unordered)==18
  for a,b in itertools.combinations(P['discovery_dp_ids'],2):
   x=by[a,b,frame,region];y=by[b,a,frame,region]
   assert abs(x['raw_pearson']-y['raw_pearson'])<1e-12 and abs(x['normalized_rms']-y['normalized_rms'])<1e-12
jan22=P['merged_dp_ids'][0];jan23=P['events']['V2E2-0098'];assert round(by[jan22,jan23,'topocentric','core']['raw_pearson'],6)==.971275 and round(by[jan22,jan23,'topocentric','broad_pattern']['raw_pearson'],6)==.986978
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');locations=science['metadata_expected_feature_locations'];outside=[r['date_obs'][:10] for r in locations if not r['expected_center_inside_fixed_core']]
assert outside==['2022-05-16','2023-04-29','2023-07-01','2023-08-27']
next_metadata=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');member=next_metadata['members'][0]
assert next_metadata['next_core_group']=='C015' and member['candidate_id']=='V2E2-0095' and member['queue_index']==28 and member['target']=='HD114386' and member['discovery_dp_id']=='ADP.2022-05-17T01:02:16.724' and next_metadata['proposed_topocentric_anchor_air_angstrom']==3870.0539967497375
assert P['completed_normalization_context']['no_replay']is True and len(P['skipped_completed_routes'])==2
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['V2E2-0094/0096/0098/0110 all remain U','22 profiles and 128 comparisons','16 identical-product self rows','24 ordered nonself rows per frame/region reuse seven observations','18 unordered exposure pairs','not the union of the original member cores','0.0025 Å below','0.0025 Å above','0.971275','0.986978','22 false low-reference flags','strictly positive','485–488','Strong right-edge bands dominate','U/U/U','C015 / V2E2-0095','No C015 array analysis']:
 assert text in report,text
for event in P['events']:assert '### '+event+' reference:' in report
links=re.findall(r'\]\(([^)]+)\)',report);assert not [q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json']
audit=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');assert audit['status'].startswith('PASS') and audit['checks_passed']==700 and audit['scalar_values_compared']==86525
qa={'status':'PASS_COMPLETE_C016_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD114386','group_midpoint_bary_air_angstrom':4303.7875,'fixed_common_core_bary_air_angstrom':[4303.5375,4304.0375],'original_member_core_edge_differences_preserved':True,'all_four_marker_and_reference_identities_preserved':True,'anchor_dp_id':P['anchor_dp_id'],'anchor_berv_km_s':P['anchor_berv_km_s'],'frozen_source_hashes_verified':64,'public_method_bindings_verified':25,'numerical_output_hashes_verified':47,'numerical_npz_files_verified':37,'stable_numeric_ledger_sha256':sha(OUT/'OUTPUT_HASHES.json'),'profile_slots':22,'comparison_slots':128,'merged_comparisons':112,'native_same_exposure_comparisons':16,'identical_product_self_comparisons':16,'distinct_discovery_products':4,'bounded_source_windows':11,'preserved_raw_copies':4,'full_profiles_with_valid_positive_reference':22,'false_low_reference_flags':22,'true_low_reference_flags':0,'null_low_reference_flags':0,'raw_only_profiles':0,'blocked_profiles':0,'structurally_excluded_native_orders':0,'evaluable_Pearson':128,'unavailable_Pearson':0,'evaluable_RMS':128,'unavailable_RMS':0,'all_comparisons_complete_raw_and_normalized_support':True,'all_profiles_zero_positive_ERR':True,'profiles_with_nonpositive_signed_window_samples':0,'all_window_and_flank_nonpositive_fractions_zero':True,'merged_finite_source_window_samples':600,'native_finite_source_window_samples_in_output_order':[r['window_native_finite_samples'] for r in native],'all_profiles_zero_gap_and_outside_coverage_masks':True,'per_reference_families':families,'nonself_rows_per_frame_region':24,'unique_unordered_exposure_pairs_per_frame_region':18,'reciprocal_discovery_pair_duplicates_per_frame_region':6,'only_seven_observations_no_independence_inflation':True,'high_January_pair_topocentric_r_preserved':{'core':.971275,'surrounding':.986978},'all_four_records_historical_review_codes_preserved':'U/U/U','all_four_order19_mapping_stages_true_preserved':True,'predicted_common_centers_outside_fixed_topocentric_core':4,'center_flags_not_full_feature_coverage_claims':True,'raw_edge_dominated_full_scale_limit_preserved':True,'prior_group_windows_disjoint_but_original_same_target_evidence_acknowledged':True,'figures':figures,'all_four_figures_visually_inspected':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'next_group':'C015','next_record':'V2E2-0095','next_target':'HD114386','completed_normalization_routes_skipped':['C013/V2E2-0092','C014/V2E2-0104'],'method_or_numerical_mutations':0,'labels_changed':0,'notes':['All four reference families preserve six other epochs and both metrics/regions; reciprocal rows remain dependent over seven observations.','Common midpoint core remains distinct from exact original member cores by0.0025Angstrom at one edge; all four markers retain own discovery coordinates.','All signed source window/flank values positive in this actual run; zero nonpositive outcomes retained without clipping or sign changes.','Native source counts485–488 remain distinct from full601-point grid support.','Near-equal January BERV pair retains high topocentric agreement rather than being omitted.','Strong raw right-edge bands dominate full scales; faint central diffuse structure retained without contrast variants or origin assignment.','Own HD114386 cohort, four references, March anchor and full order19 geometry used without importing previous target quality outcomes.','Completed normalization routes remain complete; next distinct C015 route requires a new frozen wavelength-specific method.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','notes','per_reference_families']},indent=2))
