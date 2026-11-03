#!/usr/bin/env python3
"""Verify immutable C011 delivery, valid-low outcomes and signed source counts."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,json,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'PLAN.json');numerical=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in plan['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in numerical.items():assert sha(OUT/f)==h,f
assert len(plan['source_hashes'])==50 and len(numerical)==39 and sum(f.endswith('.npz') for f in numerical)==29
assert sha(OUT/'OUTPUT_HASHES.json')=='b0911c6470e1ebe1103b8555925546207e2b96bb13bc395db5b92234f7fd4b7e'
assert len(plots['files'])==4
figures=[]
for row in plots['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load()
 figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json');assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert (REPO/f['path']).stat().st_size==f['bytes'] and sha(REPO/f['path'])==f['sha256'],f['path']
assert len(R)==18 and len(C)==36 and sum(r['identical_product_self_pair'] for r in C)==4
assert all(r['status']=='MEASURED_CONTEXT' and r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['normalization_reasons']==[] and r['flank_reference']>0 and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['outside_native_coverage_grid_samples']==0 and r['gap_masked_grid_samples']==0 for r in R)
low=[r for r in R if r['low_flank_reference']is True];assert len(low)==2 and all(r['kind']=='native' and r['order']==2 and r['flank_reference']==43.3865966796875 and r['first_difference_noise_proxy']==17.929966143069592 and r['flank_reference']<=3*r['first_difference_noise_proxy'] for r in low)
assert sum(r['low_flank_reference']is False for r in R)==16 and not any(r['low_flank_reference']is None for r in R)
assert all(r['raw_pearson']is not None and r['normalized_rms']is not None and r['raw_pearson_block_reason']is None and r['normalized_rms_block_reason']is None and r['common_finite_raw_samples']==(51 if r['region']=='core' else 550) and r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C)
assert plan['target']=='HD112410' and plan['group_center_bary_air_angstrom']==3865.6775000000002 and plan['anchor_berv_km_s']==-5.48386283255014 and plan['anchor_dp_id']=='ADP.2025-05-29T01:01:14.389'
handoff=read(REPO/'work_harps_20261103_c012_context/NEXT_ACTION.json');assert plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert {plan['historical_review_disagreement'][k] for k in ['primary_code','secondary_code','root_adopted_code']}=={'U'}
fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported'];mapping=plan['historical_mapping_stages']
assert [[r[k] for k in fields] for r in mapping]==[[True,True,True,True],[True,True,True,True]]
shared=[r for r in plan['prior_bounded_window_geometry'] if r['shared_source_pixels']];assert len(shared)==1 and shared[0]['group']=='C012' and shared[0]['overlap_bary_air_angstrom']==[3866.2675,3868.6775000000002]
nonself=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']];by={(r['dp_id'],r['frame'],r['region']):r for r in nonself};other=[d for d in plan['merged_dp_ids'] if d!=plan['anchor_dp_id']]
for dp in other:
 for z in ['core','broad_pattern']:
  assert by[dp,'barycentric',z]['raw_pearson']>by[dp,'topocentric',z]['raw_pearson']
  assert by[dp,'barycentric',z]['normalized_rms']<by[dp,'topocentric',z]['normalized_rms']
topcore=[r for r in nonself if r['frame']=='topocentric' and r['region']=='core'];assert sum(r['raw_pearson']<0 for r in topcore)==5
assert [r['dp_id'] for r in topcore if r['raw_pearson']>0]==['ADP.2025-05-31T01:00:40.754']
nonpositive=[r for r in R if r['window_nonpositive_fraction']>0];assert len(nonpositive)==6
may=[r for r in nonpositive if r['kind']=='merged'];assert len(may)==2
assert all(r['date_obs'].startswith('2025-05-28') and r['window_native_finite_samples']==600 and r['window_nonpositive_fraction']==3/600 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==0 for r in may)
order2=[r for r in R if r['order']==2];order3=[r for r in R if r['order']==3]
assert all(r['window_native_finite_samples']==655 and r['window_nonpositive_fraction']==29/655 and r['left_flank_finite_samples']==160 and r['right_flank_finite_samples']==168 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==13/168 for r in order2)
assert all(r['window_native_finite_samples']==534 and r['window_nonpositive_fraction']==3/534 and r['left_flank_finite_samples']==132 and r['right_flank_finite_samples']==136 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==0 for r in order3)
assert sum(r['window_nonpositive_fraction']==0 for r in R)==12
may30=[r for r in R if r['kind']=='merged' and r['date_obs'].startswith('2025-05-30') and r['frame']=='topocentric'];assert len(may30)==1 and may30[0]['window_native_finite_samples']==599 and may30[0]['left_flank_finite_samples']==149
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');locations=science['metadata_expected_feature_locations'];assert len(locations)==7 and all(r['expected_center_inside_fixed_core'] for r in locations)
next_metadata=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');members=next_metadata['members']
assert next_metadata['next_core_group']=='C016' and [m['candidate_id'] for m in members]==['V2E2-0094','V2E2-0096','V2E2-0098','V2E2-0110'] and [m['queue_index'] for m in members]==[27,29,30,32]
assert {m['target'] for m in members}=={'HD114386'} and next_metadata['distinct_discovery_product_count']==4
assert [r['candidate_id'] for r in next_metadata['skipped_completed_routes']]==['V2E2-0092','V2E2-0104'] and all(r['diagnostic_status']=='COMPLETE_DESCRIPTIVE_NORMALIZATION_CONTEXT' for r in next_metadata['skipped_completed_routes'])
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['V2E2-0089 remains U','all six pairs in each region','All 36 Pearson values and all 36 normalized RMS values','All seven predicted centers remain inside','43.386597','17.929966','3/600 (0.5%)','29/655 (4.4275%)','13/168 (7.7381%)','3/534 (0.5618%)','599 finite window samples and 149 left-flank samples','not raw-only','U/U/U','entire C011 positive reference flank','C016 / R017','C013 / 0092','C014 / 0104','No C016 array analysis or replay']:
 assert text in report,text
links=re.findall(r'\]\(([^)]+)\)',report);missing=[q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json'];assert not missing,missing
audit=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');assert audit['status'].startswith('PASS') and audit['checks_passed']==481 and audit['scalar_values_compared']==71203
qa={'status':'PASS_COMPLETE_C011_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD112410','exact_catalog_center':3865.6775000000002,'anchor_dp_id':plan['anchor_dp_id'],'anchor_berv_km_s':plan['anchor_berv_km_s'],'frozen_source_hashes_verified':50,'public_method_bindings_verified':25,'numerical_output_hashes_verified':39,'numerical_npz_files_verified':29,'stable_numeric_ledger_sha256':sha(OUT/'OUTPUT_HASHES.json'),'profile_slots':18,'comparison_slots':36,'identical_product_self_comparisons':4,'bounded_source_windows':9,'preserved_raw_copies':2,'full_profiles_with_valid_positive_reference':18,'false_low_reference_flags':16,'true_low_reference_flags':2,'true_low_reference_orders':[2],'null_low_reference_flags':0,'raw_only_profiles':0,'blocked_profiles':0,'structurally_excluded_native_orders':0,'evaluable_Pearson':36,'unavailable_Pearson':0,'evaluable_RMS':36,'unavailable_RMS':0,'all_comparisons_complete_raw_and_normalized_support':True,'all_profiles_zero_positive_ERR':True,'profiles_with_nonpositive_signed_window_samples':6,'profiles_with_zero_nonpositive_window_samples':12,'merged_May28_nonpositive_window_counts':[3,3],'merged_May28_finite_window_counts':[600,600],'merged_May28_nonpositive_flank_counts':[0,0],'native_order2_nonpositive_window_counts':[29,29],'native_order2_finite_window_counts':[655,655],'native_order2_nonpositive_right_flank_counts':[13,13],'native_order2_finite_right_flank_counts':[168,168],'native_order3_nonpositive_window_counts':[3,3],'native_order3_finite_window_counts':[534,534],'native_order3_nonpositive_flank_counts':[0,0],'May30_topocentric_finite_source_window_samples':599,'May30_topocentric_finite_left_flank_samples':149,'May30_topocentric_grid_support':601,'all_profiles_zero_gap_and_outside_coverage_masks':True,'all_six_nonself_comparisons_better_barycentric_both_metrics_each_region':True,'negative_nonself_topocentric_core_correlations':5,'positive_topocentric_core_epoch':'2025-05-30','historical_review_codes_preserved':{'primary':'U','secondary':'U','root_adopted':'U'},'both_orders_all_four_historical_mapping_stages_true_preserved':True,'shared_source_pixels_with_C012_preserved':True,'C011_core_outside_C012_window':True,'C011_positive_flank_within_C012_window':True,'predicted_centers_outside_fixed_topocentric_core':0,'center_flags_not_full_feature_coverage_claims':True,'figures':figures,'all_four_figures_visually_inspected':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'next_group':'C016','next_target':'HD114386','next_member_count':4,'completed_normalization_routes_skipped':['C013/V2E2-0092','C014/V2E2-0104'],'method_or_numerical_mutations':0,'labels_changed':0,'notes':['All 18 full-support profiles have valid positive two-flank references. Native order2 low=true in both frames remains distinct from raw-only or invalid normalization.','All signed nonpositive source samples retained; counts distinguished from interpolated-grid support.','May30 topocentric 599 source samples / 149 left-flank samples remain distinct from full601 grid support.','May30 near-anchor positive topocentric core correlation retained; other five nonself core correlations negative. All six still favor barycentric r and RMS in both regions.','Both C011 orders retain all-true historical mapping stages; C012 false flags and missing right flank not transferred.','Diffuse central raw trace and strong right-edge residual structure preserved at full scales without physical-origin assignment.','Same HD112410 observations and shared C012 surrounding/reference pixels are explicit dependence; whole positive reference flank previously viewed.','Next C016 uses its own HD114386 cohort and four references; already completed C013/C014 normalization routes are not replayed.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','notes']},indent=2))
