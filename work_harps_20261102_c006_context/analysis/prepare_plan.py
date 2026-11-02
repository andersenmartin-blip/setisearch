#!/usr/bin/env python3
"""Assemble the prospective C006 plan from metadata, never science values."""
from pathlib import Path
import hashlib,json,datetime
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
old=REPO/'work_harps_20261102_c005_context'
p=read(old/'analysis/PLAN.json');inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
p['schema']='HARPS_C006_JOINT_PROFILE_CONTEXT_V1';p['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
p['scope']='All seven existing HD106515A spectra in the original extension02 cohort, not archive-wide completeness. Complete C006 group contains three U records spanning R006/R007, but two unique discovery products. Same exposure cohort as C003/C005; overlapping records and shared pixels are not independent observations.'
p['events']=inv['events'];p['merged_dp_ids']=[r['dp_id']for r in inv['merged_spectra']];p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO));p['group_center_bary_air_angstrom']=4310.455
p['accepted_event_centers_bary_air_angstrom']=[4310.585,4310.305,4310.605]
p['frames']['topocentric']='One fixed ct=cb/(1+BERVfirst/c); query barycentric wavelength (ct+x)*(1+BERVepoch/c). Equivalently native topocentric wavelength=ct+x. Both unique discovery products/order19 contexts share this anchor; no recentering. At large BERV differences later features may leave the fixed core, which then samples neighboring structure.'
p['grid']['core']='abs(x)<=0.400: 81 sampled centers [-0.40,+0.40]. Connected exact nominal union of all three original ±0.25 Å cores: extrema 4310.305 and 4310.605 Å, midpoint 4310.455 Å.'
p['grid']['broad_pattern']='0.400<abs(x)<=3: 520 sampled centers'
p['normalization']['structured_neighbor']='C007 catalog center4312.700 Å lies at+2.245 Å inside the positive C006 normalization flank. Retain this pre-known structure without masking; reference median is not line-free continuum. Future C007 analysis overlaps this broad window and shares exposure/pixel evidence.'
p['comparisons']['merged']='7 epochs × 2 unique fixed discovery references × 2 frames × 2 regions = 56 records, including 8 identical-product self-comparisons. 0042 and0043 share one product and do not duplicate the reference.'
p['comparisons']['native']='2 unique discovery/order19 pairs × 2 frames × 2 regions = 8 same-exposure native-to-merged records. No independent confirmation or physical flux ratio.'
p['comparisons']['minimum_common_core']=65;p['comparisons']['minimum_common_broad']=416
p['comparisons']['self_and_dependency_flags']='same_exposure and identical_product_self_pair explicit. Preserve all three event identities while deduplicating two product references. 0042/0043 overlap within the same exposure; one joint correlation is not independent proof for each constituent feature.'
p['slots']={'merged_profiles':14,'native_profiles':4,'all_profiles':18,'merged_comparisons':56,'native_comparisons':8,'all_comparisons':64,'identical_product_self_comparisons':8,'saved_raw_order_panels':3,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':9,'distinct_discovery_products':2,'discovery_records':3}
p['bounded_arrays']='Save nine pre-interpolation source windows with exact source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), source hashes, BERV and full-coordinate spacing. Analyze only union needed by both fixed-frame windows plus bracketing samples. Full merged coordinates locate slices; native coordinates derive from headers.'
p['headers']='Verify all seven merged and two unique native headers before flux access: exact hashes/identity, recorded metadata, numeric BERV, merged BARYCENT air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure one-row tables, native72×4096 shape and unchanged degree/order19 coefficients. Failed slots remain explicit. Header coordinate coverage does not establish flux or mapping quality.'
p['preserved_raw_context']='Copy all three exact event-specific stored raw/native NPZs, preserving0025/0042/0043 identities. Display original raw_cutout/raw_excess after release with separate full-value panel scales. 0042/0043 share exposure and overlapping pixels; no independent pixel count. Preserve primary, secondary, adopted reviews and all historical mapping flags. No new mapping/background fit.'
p['release_contract']['schema']='HARPS_C006_GROUP_RELEASE_V1'
p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']='Four figures: seven-epoch merged broad/core(raw/normalized,both frames),one page containing both unique native/order19 contexts,one page with all three historical event raw/excess pairs. Include all three catalog/discovery markers and R006/R007 labels. Retain signed flux, raw-only annotations and all finite values plus5percent bounds; shared merged frame and native raw frame limits; separate raw image extrema. No smoothing,clipping or favorable selection.'
p['limitations']=[
'Post-detection context of three correlated records and seven reused original-cohort exposures, not independent detections, new observing time or archive-wide completeness. All three U labels unchanged.',
'Two unique discovery products only:0042 and0043 share2022-12-31. Deduplicate reference/native product profiles; preserve separate record/raw histories. A joint-window correlation does not individually establish origin of neighboring features.',
'Discovery BERV values30.1380355615464 and30.3750612537025 km/s are near-matched. The other five epochs supply the59.6098131157401 km/s span, which is coordinate separation, not calibrated origin discrimination or survey sensitivity.',
'One fixed first-discovery topocentric anchor; features can leave the±0.400 Å core at large BERV separation. Such comparisons describe the anchor window and possibly neighboring structure, without recentering.',
'Fixed flank medians are reference levels, not proven quiet continua. C007 at4312.700 Å lies at+2.245 Å inside the positive flank; retain it. Future C007 shares window/pixel/exposure context. No fit of background,width,center,lag,RV or drift.',
'Fresh all144order header scans identify only order19 covering the original feature centers for both discovery products. Coordinate coverage does not establish finite/positive flux or usable normalization.',
'Historical0025 local_mapping_usable=false and baseline_mapping_verified=false remain despite true global/five-window diagnostics; coordinate coverage and shape agreement do not retrospectively promote local mapping.0042 separate off-trace feature retained. No new mapping validation or origin assignment.',
'Native BUNIT absent; native extracted units unspecified. Merged ADU and native scales differ; same-exposure extraction agreement is not an independent observation or physical flux ratio.',
'Positive ERR support and descriptive first-difference proxy do not supply formal SNR, calibrated significance, physical width, false-alarm rate or completeness.',
'All previous extraction, mapping, raw panels, event labels and epoch outputs unchanged. No original pipeline rerun.'
]
p['source_hashes']={}
paths=[HERE/'compare_group.py',HERE/'plot_group.py',HERE/'README.md',HERE/'prepare_plan.py',HERE/'synthetic_preflight.py',PHASE/'inputs/INPUT_INVENTORY.json',PHASE/'inputs/RESTORE_RECEIPT.json',PHASE/'inputs/restore_inputs.py',PHASE/'BASELINE_VERIFICATION.json',old/'NEXT_ACTION.json',old/'scientific_review/NEXT_STEP.md',old/'analysis/compare_group.py',old/'analysis/PLAN.json',old/'analysis/plot_group.py']
for name in ['input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']:
    f=PHASE/name
    if f.exists():paths.append(f)
for f in paths:p['source_hashes'][str(f.relative_to(REPO))]=sha(f)
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=[{'dp_id':r['dp_id'],'order':o}for r in inv['native_products']for o in r['covering_orders']]
p['excluded_native_order_pairs']=[];p['native_order_coverage']=inv['native_order_coverage'];p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']='All three event-specific histories cover order19 only; both unique products/order pairs included once. Fresh all72orders per header confirm scope. Preserve three raw panels and all historical mapping limitations; no structural exclusions.'
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']}for r in inv['saved_native_raw_cutouts']]
B={r['dp_id']:r['berv_km_s']for r in inv['merged_spectra']};cb=4310.455;c=299792.458;ct=cb/(1+p['anchor_berv_km_s']/c)
p['event_markers']=[{'event':e,'resolution_group':g,'center_bary_air_angstrom':w,'barycentric_offset_angstrom':w-cb,'discovery_topocentric_offset_angstrom':w/(1+B[inv['events'][e]]/c)-ct,'color':color}for e,g,w,color in [('V2E2-0025','R007',4310.585,'#b8292f'),('V2E2-0042','R006',4310.305,'#1b62b3'),('V2E2-0043','R007',4310.605,'#e68c1a')]]
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots']},indent=2))
