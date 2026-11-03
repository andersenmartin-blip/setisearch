#!/usr/bin/env python3
"""Freeze C012 metadata and sources without interpreting observed arrays."""
from pathlib import Path
import datetime, hashlib, json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PHASE=HERE.parent
OLD=REPO/'work_harps_20261103_c010_context'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
handoff=read(OLD/'NEXT_ACTION.json')
inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
p=read(OLD/'analysis/PLAN.json')
CB=3869.2675
ANCHOR='ADP.2025-04-30T01:01:50.866'
BERV=3.40485846065643
included=[{'dp_id':r['dp_id'],'order':o} for r in inv['native_products'] for o in r['covering_orders']]
raw_count=len(inv['saved_native_raw_cutouts'])
native_count=len(included)
p.update(schema='HARPS_C012_INDIVIDUAL_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target='HD112410')
p['status']='METHOD_FROZEN_BEFORE_ARRAY_VALUES'
p['scope']=('Singleton C012 / R013 record V2E2-0087 on HD112410 at exact catalog center '
 '3869.2675 Angstrom, chosen by original queue row 24. Retain its own seven existing '
 'April–August 2025 cohort epochs and sole April 2025 discovery reference. C010 shares those '
 'same HD112410 exposures but its wavelength window is disjoint. No HD106515A '
 'products, numeric anchor or BERV span is transferred. Original epoch/raw evidence already '
 'exists; this is not blind, untouched or independent new observing evidence.')
p['historical_review_disagreement']=handoff['historical_review_disagreement']
p['historical_mapping_stages']=inv['mapping_records']
p['events']=inv['events']
p['merged_dp_ids']=[r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom']=CB
p['accepted_event_centers_bary_air_angstrom']=[CB]
p['anchor_dp_id']=ANCHOR
p['anchor_berv_km_s']=BERV
p['frames']['topocentric']=('One fixed ct=cb/(1+BERVdiscovery/c), anchored to V2E2-0087 observed '
 'on 2025-04-29 with BERV 3.40485846065643 km/s. Query barycentric wavelength '
 '(ct+x)*(1+BERVepoch/c), equivalent to native topocentric wavelength ct+x. Recompute from '
 'the exact C012 center; no HD106515A numeric anchor is reused and no recentering occurs.')
p['grid']['core']=('abs(x)<=0.25: 51 sampled centers [-0.25,+0.25]. Exact original core '
 '[3869.0175,3869.5175] Angstrom; not a fitted physical linewidth.')
p['grid']['broad_pattern']='0.25<abs(x)<=3: 550 sampled centers.'
p['normalization']['structured_neighbor']=('Retain every fixed-flank sample and any structured '
 'spectrum without masks or an assumed line-free region. This is a new target-specific bounded '
 'window, but original HD112410 event/epoch/raw evidence exists. Pooled medians are descriptive '
 'reference levels, not fitted or established line-free continua.')
p['comparisons']['merged']='7 target-specific epochs × 1 fixed reference × 2 frames × 2 regions = 28 records, including 4 identical-product self rows.'
p['comparisons']['native']=f'{native_count} native covering-order context(s) × 2 frames × 2 regions = {4*native_count} same-exposure native-to-merged records; shared extraction is dependent, not another observation or a physical flux ratio.'
p['comparisons']['minimum_common_core']=41
p['comparisons']['minimum_common_broad']=440
p['comparisons']['self_and_dependency_flags']=('Retain same_exposure and identical_product_self_pair '
 'flags, one fixed April 2025 discovery and all seven reused HD112410 products. A different '
 'wavelength window or same-target context does not erase the existing original epoch/raw evidence.')
p['slots']={'merged_profiles':14,'native_profiles':2*native_count,'all_profiles':14+2*native_count,
 'merged_comparisons':28,'native_comparisons':4*native_count,'all_comparisons':28+4*native_count,
 'identical_product_self_comparisons':4,'saved_raw_order_panels':raw_count,
 'structurally_excluded_native_order_pairs':len(inv['excluded_native_orders']),
 'expected_bounded_input_windows':7+native_count,'distinct_discovery_products':1,'discovery_records':1}
p['bounded_arrays']=(f'Save {7+native_count} pre-interpolation source windows with exact indices, '
 'original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native '
 'errors), source hashes, BERV and full-source spacing. Read only the union needed by both '
 'fixed-frame windows plus brackets; no extrapolation or original-pipeline replay.')
p['headers']=('Check all seven HD112410 merged headers and the April 2025 native header before '
 'new flux access: exact identities/hashes/metadata, numeric BERV, merged barycentric-air '
 'Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native 72×4096 shape and '
 'freshly recorded polynomial coefficients for every selected order. Geometric support, '
 'finite flux, reference validity and historical mapping reliability remain distinct.')
p['preserved_raw_context']=('Copy the exact historical V2E2-0087 raw/native NPZ panel(s) and '
 'display original raw_cutout/raw_excess after release at separate full scales. Preserve '
 'primary U, secondary U and adopted U reviews and each mapping stage, including original '
 'order 2 local/baseline failures alongside true global/later five-window diagnostics; '
 'order 3 retains true at every historical stage. '
 'No new registration, subtraction, spatial model, pixel statistic or origin claim.')
p['release_contract']['schema']='HARPS_C012_GROUP_RELEASE_V1'
p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']=('Four fixed figures: all seven target-specific merged epochs in broad/core '
 'signed and scaled views in both frames, every retained native order, and every original '
 'raw/excess pair. The 0087/R013 marker is the catalog/discovery coordinate, not a fitted peak. '
 'Keep raw-only reasons, low/invalid references and partial support visible. Same-quantity '
 'merged scales match across frames; native raw scales match across frames per order. '
 'Every finite value remains with 5 percent margins; raw images use separate full extrema. '
 'No smoothing, clipping, favorable epoch choice or contrast variant.')
p['limitations']=[
 'Post-detection context of one U record and seven reused HD112410 exposures. No new observing time, independent detection or archive-wide completeness; V2E2-0087 remains U.',
 'The own seven HD112410 exposures are shared with C010, while the C012 window is disjoint from C010. The exact center is 3869.2675 Angstrom. Numeric overlap with HD106515A C002/C003/C004 windows shares no observations or source pixels. Recompute the new wavelength-specific anchor; original epoch/profile and raw evidence for 0087 already exist.',
 'The sole discovery is observed on 2025-04-29 with BERV 3.40485846065643 km/s. Its own seven April–August 2025 epochs span 21.30284860830273 km/s. That span is coordinate separation, not calibrated origin discrimination.',
 'The fixed topocentric core is not recentered on other epochs. A coherent catalog center can leave the original ±0.25 Angstrom core, so a fixed-window comparison may describe neighboring structure.',
 'All fixed-flank structure remains in pooled medians; they are reference levels, not line-free continua. No fitted width, center, lag, stellar RV, drift, background, continuum, masks or moved flanks.',
 'Fresh all-72-order header geometry determines covering native orders and each context/flank support. Covering the catalog center is distinct from finite flux, valid positive normalization and adequate common support; missing outcomes retain explicit slots/reasons.',
 'Historical order 2 global-grid and later five-window diagnostics are true, while original local_mapping_usable and baseline_mapping_verified are false. Order 3 retains true at every historical stage. Preserve those stages distinctly; later support does not retroactively repair original raw registration limits.',
 'All historical primary, secondary and adopted reviews retain U for broad enhancement shared by orders 2 and 3, noisier order 2, smoother order 3 and trace-associated raw structure. No morphology, frame correlation or extraction agreement silently changes the adopted disposition.',
 'Native BUNIT is absent and extracted units are unspecified. Merged ADU and native scales differ; shared same-exposure extraction is not independent confirmation or a physical flux ratio.',
 'Missing/limited ERR support and descriptive first-difference proxies do not establish formal uncertainty, significance, physical linewidth, false-alarm rate, sensitivity or a qualified survey null.',
 'All earlier extractions, mapping, raw panels, votes, classifications, original epoch outputs and completed contexts remain unchanged.'
]
paths=[HERE/n for n in ['compare_group.py','plot_group.py','README.md','prepare_plan.py','synthetic_preflight.py']]
paths += [PHASE/n for n in ['inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','inputs/restore_inputs.py','BASELINE_VERIFICATION.json','input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']]
paths += [OLD/n for n in ['NEXT_ACTION.json','scientific_review/NEXT_STEP.md','analysis/compare_group.py','analysis/PLAN.json','analysis/plot_group.py']]
prior=[]
for number in range(1,11):
 f=REPO/(('work_harps_20261102_' if number<=8 else 'work_harps_20261103_')+f'c{number:03d}_context/analysis/PLAN.json')
 q=read(f);center=q['group_center_bary_air_angstrom'];window=[center+x for x in q['grid']['window_angstrom']]
 target=q.get('target','HD106515A');disjoint=window[1]<CB-3 or window[0]>CB+3
 if target=='HD112410':assert disjoint
 prior.append({'group':f'C{number:03d}','target':target,'window_bary_air_angstrom':window,'numerically_disjoint_from_C012':disjoint,'shared_source_pixels':False,'dependency_note':('Same HD112410 observations reused; wavelength windows disjoint.' if target=='HD112410' else 'Different target and observations; numeric wavelength overlap does not share source pixels.'),'plan_path':str(f.relative_to(REPO))});paths.append(f)
p['prior_bounded_window_geometry']=prior
p['source_hashes']={str(f.relative_to(REPO)):sha(f) for f in paths}
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=included
p['excluded_native_order_pairs']=[]
p['native_order_coverage']=inv['native_order_coverage']
p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']=('Use the newly inventoried all-order header scan against the exact '
 'original feature center. Keep all original covering orders and declared structural exclusions '
 'without inheriting the earlier target scope or treating coordinate coverage as flux quality.')
p['native_fixed_frame_header_geometry']=[{'dp_id':r['dp_id'],'order':o,'fixed_frame_header_geometry':r['orders'][str(o)]['fixed_frame_header_geometry']} for r in inv['native_products'] for o in r['covering_orders']]
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']} for r in inv['saved_native_raw_cutouts']]
B={r['dp_id']:r['berv_km_s'] for r in inv['merged_spectra']};c=p['c_km_s'];ct=CB/(1+BERV/c)
p['event_markers']=[{'event':e,'resolution_group':'R013','center_bary_air_angstrom':CB,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':CB/(1+B[dp]/c)-ct,'color':'#b8292f'} for e,dp in inv['events'].items()]
assert inv['target']=='HD112410'
assert p['events']=={'V2E2-0087':ANCHOR}
assert p['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert p['anchor_dp_id']==p['discovery_dp_ids'][0] and B[ANCHOR]==BERV
assert max(B.values())-min(B.values())==handoff['berv_span_km_s']
assert included==[{'dp_id':ANCHOR,'order':2},{'dp_id':ANCHOR,'order':3}]
assert raw_count==2 and not p['excluded_native_order_evidence']
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots'],'anchor_air_angstrom':ct},indent=2))
