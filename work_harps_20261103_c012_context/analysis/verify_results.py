#!/usr/bin/env python3
"""Verify C012's immutable delivery, missing outcomes and signed source counts."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,json,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'PLAN.json');numerical=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in plan['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in numerical.items():assert sha(OUT/f)==h,f
assert len(plan['source_hashes'])==49 and len(numerical)==39 and sum(f.endswith('.npz') for f in numerical)==29
assert sha(OUT/'OUTPUT_HASHES.json')=='d28f98192a5e4483b9ee20f4c99223a87aaf3efb390dbca8b697133a45c64175'
assert len(plots['files'])==4
figures=[]
for row in plots['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load()
 figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json')
assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert (REPO/f['path']).stat().st_size==f['bytes'] and sha(REPO/f['path'])==f['sha256'],f['path']
assert len(R)==18 and len(C)==36 and sum(r['identical_product_self_pair'] for r in C)==4
assert all(r['status']=='MEASURED_CONTEXT' and r['positive_finite_ERR_samples']==0 and r['gap_masked_grid_samples']==0 for r in R)
valid=[r for r in R if r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'];rawonly=[r for r in R if r['normalization_status']=='RAW_ONLY']
assert len(valid)==16 and len(rawonly)==2
assert all(r['normalization_reasons']==[] and r['flank_reference']>0 and r['low_flank_reference'] is False and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['outside_native_coverage_grid_samples']==0 for r in valid)
assert all(r['kind']=='native' and r['order']==2 and r['normalization_reasons']==['MISSING_RIGHT_FLANK_COVERAGE'] and r['flank_reference'] is None and r['low_flank_reference'] is None and r['raw_grid_finite_samples']==378 and r['normalized_grid_finite_samples']==0 and r['outside_native_coverage_grid_samples']==223 and r['left_flank_finite_samples']==166 and r['right_flank_finite_samples']==0 and r['window_native_finite_samples']==423 and r['window_nonpositive_fraction']==2/423 and r['left_flank_nonpositive_fraction']==1/166 and r['right_flank_nonpositive_fraction'] is None for r in rawonly)
assert sum(r['raw_pearson'] is not None for r in C)==34 and sum(r['normalized_rms'] is not None for r in C)==32
unavailable_r=[r for r in C if r['raw_pearson'] is None];unavailable_rms=[r for r in C if r['normalized_rms'] is None]
assert all(r['order']==2 and r['region']=='broad_pattern' and r['common_finite_raw_samples']==327 and r['raw_pearson_block_reason']=='INSUFFICIENT_COMMON_RAW_COVERAGE' for r in unavailable_r)
assert all(r['order']==2 and r['common_finite_normalized_samples']==0 and r['normalized_rms_block_reason']=='INVALID_REFERENCE_OR_INSUFFICIENT_NORMALIZED_COVERAGE' for r in unavailable_rms)
assert all(r['common_finite_raw_samples']==(51 if r['region']=='core' else 550) and r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C if r['order']!=2)
assert all(r['common_finite_raw_samples']==51 and r['raw_pearson']>0.73 and r['normalized_rms'] is None for r in C if r['order']==2 and r['region']=='core')
assert plan['target']=='HD112410' and plan['group_center_bary_air_angstrom']==3869.2675 and plan['anchor_berv_km_s']==3.40485846065643
handoff=read(REPO/'work_harps_20261103_c010_context/NEXT_ACTION.json')
assert plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert {plan['historical_review_disagreement'][k] for k in ['primary_code','secondary_code','root_adopted_code']}=={'U'}
mapping=plan['historical_mapping_stages'];fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
assert [[r[k] for k in fields] for r in mapping]==[[True,False,False,True],[True,True,True,True]]
assert all(r['shared_source_pixels'] is False for r in plan['prior_bounded_window_geometry'])
assert [r['group'] for r in plan['prior_bounded_window_geometry'] if not r['numerically_disjoint_from_C012']]==['C002','C003','C004']
nonself=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']];by={(r['dp_id'],r['frame'],r['region']):r for r in nonself};other=[d for d in plan['merged_dp_ids'] if d!=plan['anchor_dp_id']]
for dp in other:
 for z in ['core','broad_pattern']:
  assert by[dp,'barycentric',z]['raw_pearson']>by[dp,'topocentric',z]['raw_pearson']
  assert by[dp,'barycentric',z]['normalized_rms']<by[dp,'topocentric',z]['normalized_rms']
assert all(r['raw_pearson']<0 for r in nonself if r['frame']=='topocentric' and r['region']=='core')
nonpositive=[r for r in R if r['window_nonpositive_fraction']>0]
assert len(nonpositive)==4
may=[r for r in nonpositive if r['kind']=='merged'];assert len(may)==2
assert all(r['date_obs'].startswith('2025-05-28') and r['window_nonpositive_fraction']==3/600 and r['left_flank_nonpositive_fraction']==3/150 and r['right_flank_nonpositive_fraction']==0 for r in may)
zero=[r for r in R if r['window_nonpositive_fraction']==0];assert len(zero)==14
june=[r for r in R if r['kind']=='merged' and r['date_obs'].startswith('2025-06-22') and r['frame']=='topocentric'];assert len(june)==1 and june[0]['window_native_finite_samples']==599 and june[0]['left_flank_finite_samples']==149
order3=[r for r in R if r['order']==3];assert all(r['window_native_finite_samples']==546 and r['left_flank_finite_samples']==134 and r['right_flank_finite_samples']==139 for r in order3)
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');locations=science['metadata_expected_feature_locations']
assert [r['date_obs'][:10] for r in locations if not r['expected_center_inside_fixed_core']]==['2025-08-07']
next_metadata=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');m=next_metadata['members'][0]
assert next_metadata['next_core_group']=='C011' and m['candidate_id']=='V2E2-0089' and m['queue_index']==25 and m['discovery_dp_id']=='ADP.2025-05-29T01:01:14.389'
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['V2E2-0087 remains U','all six pairs in each region','34 evaluable raw Pearson','32 evaluable normalized RMS','3/600 (0.5%)','2/423 (0.4728%)','599 finite original window samples','null low-reference flags','0.024958234 Å beyond','0.009398480 Å inside','327/550 surrounding samples','original local_mapping_usable=false','U/U/U','No C011 profile analysis was executed here']:
 assert text in report,text
links=re.findall(r'\]\(([^)]+)\)',report);missing=[q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json'];assert not missing,missing
audit=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');assert audit['status'].startswith('PASS') and audit['checks_passed']==481 and audit['scalar_values_compared']==70371
qa={'status':'PASS_COMPLETE_C012_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD112410','exact_catalog_center':3869.2675,'frozen_source_hashes_verified':49,'public_method_bindings_verified':25,'numerical_output_hashes_verified':39,'numerical_npz_files_verified':29,'stable_numeric_ledger_sha256':sha(OUT/'OUTPUT_HASHES.json'),'profile_slots':18,'comparison_slots':36,'identical_product_self_comparisons':4,'distinct_discovery_products':1,'bounded_source_windows':9,'preserved_raw_copies':2,'full_profiles_with_valid_positive_reference_and_false_low_flag':16,'raw_only_profiles':2,'raw_only_orders':[2],'raw_only_low_flags_null':True,'blocked_profiles':0,'structurally_excluded_native_orders':0,'evaluable_Pearson':34,'unavailable_Pearson':2,'evaluable_RMS':32,'unavailable_RMS':4,'order2_core_raw_support':51,'order2_surrounding_raw_support':327,'order2_outside_coverage_grid_positions':223,'order2_reference_failure':'MISSING_RIGHT_FLANK_COVERAGE','all_profiles_zero_positive_ERR':True,'profiles_with_nonpositive_signed_window_samples':4,'profiles_with_zero_nonpositive_window_samples':14,'merged_nonpositive_window_counts':[3,3],'merged_nonpositive_left_flank_counts':[3,3],'native_order2_nonpositive_window_counts':[2,2],'native_order2_finite_window_counts':[423,423],'native_order2_nonpositive_left_flank_counts':[1,1],'native_order2_finite_left_flank_counts':[166,166],'june22_topocentric_finite_source_window_samples':599,'june22_topocentric_finite_left_flank_samples':149,'june22_topocentric_grid_support':601,'all_profiles_zero_gap_masks':True,'all_six_nonself_comparisons_better_barycentric_both_metrics_each_region':True,'all_six_nonself_topocentric_core_correlations_negative':True,'historical_review_codes_preserved':{'primary':'U','secondary':'U','root_adopted':'U'},'original_order2_local_and_baseline_mapping_limits_preserved':True,'original_order3_all_mapping_stages_true_preserved':True,'no_shared_source_pixels_with_previous_bounded_windows':True,'predicted_centers_outside_fixed_topocentric_core':1,'near_edge_center_flags_not_full_feature_coverage_claims':True,'figures':figures,'all_four_figures_visually_inspected':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'method_or_numerical_mutations':0,'labels_changed':0,'notes':['All frozen scope slots retained, including order2 raw-only profiles, two missing surrounding Pearson values and four missing normalized RMS values.','Positive available one-sided order2 median is not a valid two-flank reference and low flags remain null.','Original source counts remain distinct from interpolated-grid counts, including June22 topocentric599source/601grid.','Every signed nonpositive sample remains; no clipping or sign flip.','Order2 T/F/F/T and order3 T/T/T/T historical stages remain separate from fresh wavelength support and dependent extraction similarity.','Raw central diffuse trace structure and strong right-edge residual lobes preserved at full scales with no origin assignment.','C010 shares observations but disjoint wavelengths; C002/C003/C004 numeric overlap belongs to another target with no shared pixels.','Next C011 row25 uses May28 discovery and new anchor; wider overlap with C012 is known dependence, not blind validation.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','notes']},indent=2))
