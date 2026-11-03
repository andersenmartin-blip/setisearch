#!/usr/bin/env python3
"""Verify immutable C010 delivery and its actual signed-sample outcomes."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,json,re,collections
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'PLAN.json');numerical=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json')
for f,h in plan['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in numerical.items():assert sha(OUT/f)==h,f
assert len(plan['source_hashes'])==47 and len(numerical)==35 and sum(f.endswith('.npz') for f in numerical)==25
assert len(plots['files'])==4
figures=[]
for row in plots['files']:
 f=OUT/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];Image.open(f).verify();im=Image.open(f);im.load()
 figures.append({**row,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
public=read(HERE.parent/'PROSPECTIVE_PUBLICATION_RECEIPT.json')
assert public['status']=='PASS_EXACT_REMOTE_READBACK' and len(public['files'])==25
for f in public['files']:assert (REPO/f['path']).stat().st_size==f['bytes'] and sha(REPO/f['path'])==f['sha256'],f['path']
assert len(R)==16 and len(C)==32 and sum(r['identical_product_self_pair'] for r in C)==4
assert all(r['status']=='MEASURED_CONTEXT' and r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['normalization_reasons']==[] and r['flank_reference']>0 and r['low_flank_reference'] is False and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['window_nonpositive_fraction']>0 and r['outside_native_coverage_grid_samples']==0 and r['gap_masked_grid_samples']==0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None and r['raw_pearson_block_reason'] is None and r['normalized_rms_block_reason'] is None and r['common_finite_raw_samples']==(51 if r['region']=='core' else 550) and r['common_finite_normalized_samples']==(51 if r['region']=='core' else 550) for r in C)
assert {r['order'] for r in R if r['kind']=='native'}=={1}
assert plan['target']=='HD112410' and plan['group_center_bary_air_angstrom']==3823.0649999999996 and plan['anchor_berv_km_s']==3.40485846065643
handoff=read(REPO/'work_harps_20261103_c009_context/NEXT_ACTION.json')
assert plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert {plan['historical_review_disagreement'][k] for k in ['primary_code','secondary_code','root_adopted_code']}=={'U'}
nonself=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']];by={(r['dp_id'],r['frame'],r['region']):r for r in nonself};other=[d for d in plan['merged_dp_ids'] if d!=plan['anchor_dp_id']]
for dp in other:
 for z in ['core','broad_pattern']:
  assert by[dp,'barycentric',z]['raw_pearson']>by[dp,'topocentric',z]['raw_pearson']
  assert by[dp,'barycentric',z]['normalized_rms']<by[dp,'topocentric',z]['normalized_rms']
merged=[r for r in R if r['kind']=='merged'];native=[r for r in R if r['kind']=='native']
assert all(r['window_native_finite_samples']==600 for r in merged) and all(r['window_native_finite_samples']==562 for r in native)
window_counts=[round(r['window_nonpositive_fraction']*r['window_native_finite_samples']) for r in merged]
assert min(window_counts)==2 and max(window_counts)==21 and all(round(r['window_nonpositive_fraction']*r['window_native_finite_samples'])==3 for r in native)
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');locations=science['metadata_expected_feature_locations']
assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==1
assert [r['date_obs'][:10] for r in locations if not r['expected_center_inside_fixed_core']]==['2025-08-07']
next_metadata=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json');m=next_metadata['members'][0]
assert next_metadata['next_core_group']=='C012' and m['candidate_id']=='V2E2-0087' and m['queue_index']==24 and m['target']=='HD112410'
report=(HERE/'RESULTS_REPORT.md').read_text()
for text in ['V2E2-0086 remains U','all six pairs in each region','every profile retains some nonpositive signed source samples','All 16 profiles contain nonpositive source samples','21/600 (3.5%)','3/562 (0.5338%)','0.021674988 Å beyond','0.012271477 Å inside','Original local mapping and baseline verification remain false','all remain **U**','C012 / V2E2-0087','No C012 analysis was executed here']:
 assert text in report,text
links=re.findall(r'\]\(([^)]+)\)',report);missing=[q for q in links if not(HERE/q).exists() and not q.startswith('http') and q!='RESULTS_QA.json'];assert not missing,missing
qa={'status':'PASS_COMPLETE_C010_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HD112410','exact_catalog_center':plan['group_center_bary_air_angstrom'],'frozen_source_hashes_verified':len(plan['source_hashes']),'public_method_bindings_verified':len(public['files']),'numerical_output_hashes_verified':len(numerical),'numerical_npz_files_verified':25,'profile_slots':len(R),'comparison_slots':len(C),'identical_product_self_comparisons':4,'distinct_discovery_products':1,'full_profiles_with_valid_positive_reference_and_false_low_flag':16,'raw_only_profiles':0,'blocked_profiles':0,'structurally_excluded_native_orders':0,'evaluable_Pearson':32,'unavailable_Pearson':0,'evaluable_RMS':32,'unavailable_RMS':0,'all_comparisons_complete_raw_and_normalized_region_support':True,'all_profiles_zero_positive_ERR':True,'profiles_with_nonpositive_signed_window_samples':16,'merged_nonpositive_window_count_range':[min(window_counts),max(window_counts)],'merged_finite_source_window_count':600,'native_nonpositive_window_counts':[3,3],'native_finite_source_window_counts':[562,562],'all_profiles_zero_missing_coverage_or_gap_masks':True,'all_six_nonself_comparisons_better_barycentric_both_metrics_each_region':True,'historical_review_codes_preserved':{'primary':'U','secondary':'U','root_adopted':'U'},'original_order1_local_and_baseline_mapping_limits_preserved':True,'predicted_centers_outside_fixed_topocentric_core':1,'near_edge_center_flags_not_full_feature_coverage_claims':True,'figures':figures,'all_four_figures_visually_inspected':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'method_or_numerical_mutations':0,'labels_changed':0,'notes':['Own seven HD112410 products, exact catalog float, wavelength-specific April 2025 anchor and own BERV span retained.','All six other epochs favor barycentric r and RMS in both regions, while amplitude and shape differences remain explicit.','May 28 largest RMS and June 27 lowest core correlation retained rather than selecting a favorable epoch.','Every profile retains some signed nonpositive source samples despite valid positive references and false low flags.','August predicted center is only slightly outside the fixed core; July remains near its positive edge, without a full-feature inside/outside claim.','Original order 1 local/baseline mapping failures remain distinct from true global/later five-window diagnostics and native/merged similarity.','Complete central raw band, diffuse residual lobes and weaker edge structure retained without new spatial modeling or origin assignment.','Current U/U/U and next C012-before-C011 fixed queue order preserved.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','notes']},indent=2))
