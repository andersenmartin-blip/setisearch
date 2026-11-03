#!/usr/bin/env python3
"""Freeze C011 metadata and sources without interpreting observed arrays."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent
OLD=REPO/'work_harps_20261103_c012_context'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
handoff=read(OLD/'NEXT_ACTION.json');inv=read(PHASE/'inputs/INPUT_INVENTORY.json');p=read(OLD/'analysis/PLAN.json')
CB=3865.6775000000002;ANCHOR='ADP.2025-05-29T01:01:14.389';BERV=-5.48386283255014
included=[{'dp_id':r['dp_id'],'order':o} for r in inv['native_products'] for o in r['covering_orders']]
raw_count=len(inv['saved_native_raw_cutouts']);native_count=len(included)
p.update(schema='HARPS_C011_INDIVIDUAL_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target='HD112410',status='METHOD_FROZEN_BEFORE_ARRAY_VALUES')
p['scope']=('Singleton C011 / R012 record V2E2-0089 on HD112410 at exact catalog center '
 '3865.6775000000002 Angstrom, selected by original queue row 25 after C012 row 24. Retain '
 'its own seven existing April–August 2025 cohort epochs and sole May 28 discovery reference, '
 'which replaces C012 April reference. C011 core lies outside C012 window but wider windows '
 'overlap on the same observations; reused surrounding/reference pixels and existing original '
 'epoch/raw evidence make this dependent post-detection context, not blind or new observing evidence.')
p['historical_review_disagreement']=handoff['historical_review_disagreement'];p['historical_mapping_stages']=inv['mapping_records']
p['events']=inv['events'];p['merged_dp_ids']=[r['dp_id'] for r in inv['merged_spectra']];p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO));p['group_center_bary_air_angstrom']=CB;p['accepted_event_centers_bary_air_angstrom']=[CB]
p['anchor_dp_id']=ANCHOR;p['anchor_berv_km_s']=BERV
p['frames']['topocentric']=('One fixed ct=cb/(1+BERVdiscovery/c), anchored to V2E2-0089 observed '
 'on 2025-05-28 with BERV -5.48386283255014 km/s. Query barycentric wavelength '
 '(ct+x)*(1+BERVepoch/c), equivalent to native topocentric wavelength ct+x. Recompute '
 'from exact C011 center and May discovery; do not transfer C012 April reference or numeric anchor.')
p['grid']['core']=('abs(x)<=0.25: 51 sampled centers [-0.25,+0.25]. Exact original core '
 '[3865.4275000000002,3865.9275000000002] Angstrom; not a fitted physical linewidth.')
p['grid']['broad_pattern']='0.25<abs(x)<=3: 550 sampled centers.'
p['normalization']['structured_neighbor']=('Retain every fixed-flank source sample and spectral '
 'structure without masks or an assumed line-free region. C011 wider window overlaps C012 '
 'on the same seven HD112410 observing products, and original C011 epoch/raw evidence exists. '
 'Pooled medians are descriptive reference levels, not fitted or established line-free continua.')
p['comparisons']['merged']='7 target-specific epochs × 1 fixed May discovery reference × 2 frames × 2 regions = 28 records, including 4 identical-product self rows.'
p['comparisons']['native']=f'{native_count} native covering-order contexts × 2 frames × 2 regions = {4*native_count} same-exposure native-to-merged records; shared extraction is dependent, not another observation or a physical flux ratio.'
p['comparisons']['minimum_common_core']=41;p['comparisons']['minimum_common_broad']=440
p['comparisons']['self_and_dependency_flags']=('Retain same_exposure and identical_product_self_pair '
 'flags, one fixed May 28 discovery, all seven reused HD112410 products and same-target '
 'C012 wider-window pixel overlap. Different reference identity does not add observations.')
p['slots']={'merged_profiles':14,'native_profiles':2*native_count,'all_profiles':14+2*native_count,'merged_comparisons':28,'native_comparisons':4*native_count,'all_comparisons':28+4*native_count,'identical_product_self_comparisons':4,'saved_raw_order_panels':raw_count,'structurally_excluded_native_order_pairs':len(inv['excluded_native_orders']),'expected_bounded_input_windows':7+native_count,'distinct_discovery_products':1,'discovery_records':1}
p['bounded_arrays']=(f'Save {7+native_count} pre-interpolation source windows with exact indices, '
 'original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native '
 'errors), source hashes, BERV and full-source spacing. Read only the union needed by both '
 'fixed-frame windows plus brackets; no extrapolation or original-pipeline replay.')
p['headers']=('Check all seven HD112410 merged headers and the May discovery native header '
 'before new flux access: exact identities/hashes/metadata, numeric BERV, merged barycentric-air '
 'Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native 72×4096 shape and '
 'fresh polynomial coefficients for each selected order. Geometric support, finite flux, '
 'reference validity and historical mapping reliability remain distinct.')
p['preserved_raw_context']=('Copy exact historical V2E2-0089 raw/native NPZ panels and display '
 'original raw_cutout/raw_excess after release at separate full scales. Preserve primary U, '
 'secondary U and adopted U reviews, and true global/local/baseline/later five-window stages '
 'for both original covering orders. Do not transfer C012 order 2 local/baseline failures. '
 'No new registration, subtraction, spatial model, pixel statistic or origin claim.')
p['release_contract']['schema']='HARPS_C011_GROUP_RELEASE_V1';p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']=('Four fixed figures: all seven merged epochs in broad/core signed and scaled '
 'views in both frames, every retained native order and both original raw/excess pairs. '
 'The 0089/R012 marker denotes catalog/discovery coordinates, not fitted peaks. Retain '
 'raw-only reasons, any low/invalid reference and partial support. Same-quantity merged '
 'scales match across frames; native raw scales match across frames per order. Every finite '
 'value remains with 5 percent margins; raw images use separate full extrema. No smoothing, '
 'clipping, favorable epoch selection or contrast variant.')
p['limitations']=[
 'Post-detection context of one U record and seven reused HD112410 exposures; V2E2-0089 remains U. No new observing time, independent detection or archive-wide completeness.',
 'C011 original core is outside C012 window, but their broader same-target windows overlap over [3866.2675,3868.6775000000002] Angstrom, width 2.4100000000003092 Angstrom. Same observations and reused surrounding/reference pixels are dependence, not blind or independent wavelength validation. C010 window is disjoint.',
 'The discovery is May 28 2025, ADP.2025-05-29T01:01:14.389, with BERV -5.48386283255014 km/s. Use its wavelength-specific anchor, not C012 April reference/anchor. The same seven April–August 2025 epochs span 21.30284860830273 km/s; this gives coordinate separation, not calibrated origin discrimination.',
 'Fixed topocentric core is not recentered on other epochs. A coherent catalog center can approach or leave the original ±0.25 Angstrom core; fixed comparisons can describe neighboring structure.',
 'All fixed-flank structure remains in pooled medians; reference levels are not established line-free continua. No fitted width, center, lag, stellar RV, drift, background, continuum, masks or moved flanks.',
 'Fresh all-72-order header geometry determines selected native orders and context/flank support. Catalog-center coverage is distinct from finite flux, valid positive normalization and common support. Preserve missing/insufficient/nonpositive/raw-only outcomes and explicit reasons rather than transferring C012 outcomes.',
 'Both original covering orders retain true global-grid, local_mapping_usable, baseline_mapping_verified and later five-window support. C012 order 2 original local/baseline false flags do not apply to C011. Historical mapping support is not physical-origin evidence.',
 'Primary, secondary and adopted reviews remain U/U/U for broad native structure and diffuse trace-associated enhancement. No morphology, frame correlation or same-exposure extraction agreement changes the adopted disposition or qualifies a laser candidate.',
 'Native BUNIT absent: native extracted units unspecified and distinct from merged ADU. Shared same-exposure native/merged extraction is dependent, not another observation or a physical flux ratio.',
 'Missing/limited ERR support and descriptive first-difference proxies do not establish formal uncertainty, significance, physical linewidth, false-alarm rate, sensitivity or a qualified survey null.',
 'Earlier extractions, mapping, raw panels, votes, classifications, original epoch outputs and completed contexts remain immutable.'
]
paths=[HERE/n for n in ['compare_group.py','plot_group.py','README.md','prepare_plan.py','synthetic_preflight.py']]
paths += [PHASE/n for n in ['inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','inputs/restore_inputs.py','BASELINE_VERIFICATION.json','input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']]
paths += [OLD/n for n in ['NEXT_ACTION.json','scientific_review/NEXT_STEP.md','analysis/compare_group.py','analysis/PLAN.json','analysis/plot_group.py']]
prior=[]
for number in list(range(1,11))+[12]:
 f=REPO/(('work_harps_20261102_' if number<=8 else 'work_harps_20261103_')+f'c{number:03d}_context/analysis/PLAN.json')
 q=read(f);center=q['group_center_bary_air_angstrom'];window=[center+x for x in q['grid']['window_angstrom']]
 target=q.get('target','HD106515A');disjoint=window[1]<CB-3 or window[0]>CB+3
 overlap=[max(window[0],CB-3),min(window[1],CB+3)] if not disjoint else None
 shared=target=='HD112410' and not disjoint
 prior.append({'group':f'C{number:03d}','target':target,'window_bary_air_angstrom':window,'numerically_disjoint_from_C011':disjoint,'overlap_bary_air_angstrom':overlap,'shared_source_pixels':shared,'dependency_note':('Same HD112410 observing products and overlapping surrounding/reference pixels; original C011 core outside prior window.' if shared else 'Same HD112410 observing products but disjoint wavelength windows.' if target=='HD112410' else 'Different target and observations; numeric wavelength overlap shares no source pixels.'),'plan_path':str(f.relative_to(REPO))});paths.append(f)
p['prior_bounded_window_geometry']=prior
p['source_hashes']={str(f.relative_to(REPO)):sha(f) for f in paths}
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=included;p['excluded_native_order_pairs']=[];p['native_order_coverage']=inv['native_order_coverage'];p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']=('Use fresh all-order header scan against exact original center; '
 'retain every original covering order and declared exclusion. Do not inherit C012 partial '
 'coverage, missing-flank or raw mapping outcomes. Coordinate support does not establish flux quality.')
p['native_fixed_frame_header_geometry']=[{'dp_id':r['dp_id'],'order':o,'fixed_frame_header_geometry':r['orders'][str(o)]['fixed_frame_header_geometry']} for r in inv['native_products'] for o in r['covering_orders']]
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']} for r in inv['saved_native_raw_cutouts']]
B={r['dp_id']:r['berv_km_s'] for r in inv['merged_spectra']};c=p['c_km_s'];ct=CB/(1+BERV/c)
p['event_markers']=[{'event':e,'resolution_group':'R012','center_bary_air_angstrom':CB,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':CB/(1+B[dp]/c)-ct,'color':'#b8292f'} for e,dp in inv['events'].items()]
assert inv['target']=='HD112410' and p['events']=={'V2E2-0089':ANCHOR}
assert p['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert p['anchor_dp_id']==p['discovery_dp_ids'][0] and B[ANCHOR]==BERV
assert max(B.values())-min(B.values())==handoff['berv_span_km_s']
assert included==[{'dp_id':ANCHOR,'order':2},{'dp_id':ANCHOR,'order':3}] and raw_count==2 and not p['excluded_native_order_evidence']
assert [r['group'] for r in prior if r['shared_source_pixels']]==['C012']
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots'],'anchor_air_angstrom':ct},indent=2))
