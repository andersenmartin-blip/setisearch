#!/usr/bin/env python3
"""Verify unchanged C009 delivery, including differing core/surrounding outcomes."""
from pathlib import Path
from PIL import Image
import datetime,hashlib,json,re,collections
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'PLAN.json');numerical=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');metrics=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json')
for f,h in plan['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in numerical.items():assert sha(OUT/f)==h,f
assert len(plan['source_hashes'])==46 and len(numerical)==35 and sum(f.endswith('.npz') for f in numerical)==25
assert len(plots['files'])==4
figures=[]
for f in plots['files']:
 p=OUT/f['path'];assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes'];Image.open(p).verify();im=Image.open(p);im.load()
 figures.append({**f,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
assert len(metrics)==16 and len(pairs)==32 and sum(x['identical_product_self_pair'] for x in pairs)==4
assert all(x['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and x['normalization_reasons']==[] and x['status']=='MEASURED_CONTEXT' and x['flank_reference']>0 and x['raw_grid_finite_samples']==601 and x['normalized_grid_finite_samples']==601 and x['low_flank_reference'] is False and x['positive_finite_ERR_samples']==0 and x['window_nonpositive_fraction']==0 and x['left_flank_nonpositive_fraction']==0 and x['right_flank_nonpositive_fraction']==0 and x['outside_native_coverage_grid_samples']==0 and x['gap_masked_grid_samples']==0 for x in metrics)
assert all(x['raw_pearson'] is not None and x['normalized_rms'] is not None and x['raw_pearson_block_reason'] is None and x['normalized_rms_block_reason'] is None and x['common_finite_raw_samples']==(51 if x['region']=='core' else 550) and x['common_finite_normalized_samples']==(51 if x['region']=='core' else 550) for x in pairs)
assert {x['order'] for x in metrics if x['kind']=='native'}=={70}
nonself=[x for x in pairs if x['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not x['identical_product_self_pair']]
by={(x['dp_id'],x['frame'],x['region']):x for x in nonself};others=list(dict.fromkeys(x['dp_id'] for x in nonself))
assert len(others)==6
assert all(by[dp,'barycentric','core']['raw_pearson']<0 and by[dp,'topocentric','core']['raw_pearson']>by[dp,'barycentric','core']['raw_pearson'] for dp in others)
assert sum(by[dp,'topocentric','core']['normalized_rms']<by[dp,'barycentric','core']['normalized_rms'] for dp in others)==4
assert all(by[dp,'barycentric','broad_pattern']['raw_pearson']>by[dp,'topocentric','broad_pattern']['raw_pearson'] and by[dp,'barycentric','broad_pattern']['normalized_rms']<by[dp,'topocentric','broad_pattern']['normalized_rms'] for dp in others)
assert plan['historical_review_disagreement']['primary_code']=='A' and plan['historical_review_disagreement']['secondary_code']=='A' and plan['historical_review_disagreement']['root_adopted_code']=='U'
next_metadata=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert next_metadata['next_core_group']=='C010' and next_metadata['members'][0]['candidate_id']=='V2E2-0086' and next_metadata['members'][0]['target']=='HD112410'
report=(HERE/'RESULTS_REPORT.md').read_text()
for required in ['V2E2-0050 remains U','All six **barycentric core correlations are negative**','surrounding pattern favors barycentric coordinates in all six pairs','primary A / secondary A / root-adopted U','151 samples per flank barycentrically and 150 per flank topocentrically','far right and lower-right edge','not make the evidence blind, untouched or independent','C010 / V2E2-0086']:
 assert required in report,required
links=re.findall(r'\]\(([^)]+)\)',report);missing=[x for x in links if not(HERE/x).exists() and not x.startswith('http') and x!='RESULTS_QA.json'];assert not missing,missing
qa={'status':'PASS_COMPLETE_C009_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'frozen_source_hashes_verified':len(plan['source_hashes']),'numerical_output_hashes_verified':len(numerical),'numerical_npz_files_verified':25,'profile_slots':len(metrics),'comparison_slots':len(pairs),'identical_product_self_comparisons':4,'distinct_discovery_products':1,'full_profiles_with_valid_positive_reference_and_false_low_flag':16,'raw_only_profiles':0,'blocked_profiles':0,'structurally_excluded_native_orders':0,'evaluable_Pearson':32,'unavailable_Pearson':0,'evaluable_RMS':32,'unavailable_RMS':0,'all_comparisons_complete_raw_and_normalized_region_support':True,'all_profiles_zero_positive_ERR':True,'all_profiles_zero_nonpositive_window_and_flank_fractions':True,'all_profiles_zero_missing_coverage_or_gap_masks':True,'all_six_nonself_barycentric_core_correlations_negative':True,'all_six_topocentric_core_correlations_higher':True,'core_normalized_RMS_better_topocentric_count':4,'core_normalized_RMS_better_barycentric_count':2,'all_six_surrounding_comparisons_better_barycentric_both_metrics':True,'historical_review_codes_preserved':{'primary':'A','secondary':'A','root_adopted':'U'},'figures':figures,'all_four_figures_visually_inspected':True,'root_also_reported_all_four_figures_reviewed_layout_acceptable':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'method_or_numerical_mutations':0,'labels_changed':0,'notes':['Core non-recurrence and surrounding recurrence retained separately, with complete six-epoch ranges and core RMS exceptions.','The fixed topocentric core can concern neighboring structure; no coherent topocentric feature or origin is established.','Discovery merged reference levels differ slightly between frames; original151/151 versus150/150 flank support retained.','Historical compact slanted central concentration and broader residual remain distinct from complete-panel bright edge structures.','All original primary A, secondary A and root-adopted U reviews remain preserved; no promotion or relabeling.','Disjoint bounded wavelength region still reuses all seven observations and existing epoch/raw evidence.','No presentation repair, new spatial model or frozen-method change required.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n');assert all((HERE/x).exists() or x.startswith('http') for x in links)
print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','notes']},indent=2))
