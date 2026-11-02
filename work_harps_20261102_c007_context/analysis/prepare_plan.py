#!/usr/bin/env python3
"""Assemble the C007 plan from bound metadata, without observational values."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PHASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
old=REPO/'work_harps_20261102_c006_context'
p=read(old/'analysis/PLAN.json')
inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
p['schema']='HARPS_C007_INDIVIDUAL_PROFILE_CONTEXT_V1'
p['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
p['scope']='Singleton V2E2-0026 / C007 / R008 on HD106515A, with all seven existing original-cohort epochs and one fixed discovery reference. C007 core was already visible in completed C006 positive reference flank. This is overlapping post-detection context, not blind or independent validation, new observing time or archive-wide completeness.'
p['events']=inv['events']
p['merged_dp_ids']=[r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom']=4312.7
p['accepted_event_centers_bary_air_angstrom']=[4312.7]
p['frames']['topocentric']='One fixed ct = cb/(1+BERVdiscovery/c); query barycentric wavelength (ct+x)*(1+BERVepoch/c). Equivalently native topocentric wavelength = ct+x. The unique reference and native order use that anchor, with no recentering. Later features can leave the fixed core, which then samples neighboring structure.'
p['grid']['core']='abs(x)<=0.25: 51 sampled centers [-0.25,+0.25], preserving the original singleton core at 4312.450–4312.950 Angstrom.'
p['grid']['broad_pattern']='0.25<abs(x)<=3: 550 sampled centers.'
p['normalization']['structured_neighbor']='Completed C006 centers 4310.305–4310.605 Angstrom lie at offsets -2.395 through -2.095 Angstrom inside C007 negative reference flank. Their original cores are retained without masks. These reference medians are not line-free continua. C007 core was already visible in C006 positive flank; shared window values and exposures are not independent validation.'
p['comparisons']['merged']='7 epochs × 1 fixed discovery reference × 2 frames × 2 regions = 28 records, including 4 identical-product self-comparisons.'
p['comparisons']['native']='1 discovery/order 19 pair × 2 frames × 2 regions = 4 same-exposure native-to-merged records. Shared extraction is not independent confirmation or a physical flux ratio.'
p['comparisons']['minimum_common_core']=41
p['comparisons']['minimum_common_broad']=440
p['comparisons']['self_and_dependency_flags']='same_exposure and identical_product_self_pair flags are explicit. One discovery product and one catalog record; all seven exposures and overlapping wavelength samples are shared with earlier contexts.'
p['slots']={'merged_profiles':14,'native_profiles':2,'all_profiles':16,'merged_comparisons':28,'native_comparisons':4,'all_comparisons':32,'identical_product_self_comparisons':4,'saved_raw_order_panels':1,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':8,'distinct_discovery_products':1,'discovery_records':1}
p['bounded_arrays']='Save eight pre-interpolation source windows with exact source indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), source hashes, BERV and full-coordinate spacing. Read only the union required by both fixed-frame windows plus bracketing samples. Full merged coordinates locate slices; native coordinates derive from headers. Already seen overlap with C006 remains explicit.'
p['headers']='Verify all seven merged and one native headers before new flux access: exact hashes and identity, recorded metadata, numeric BERV, merged BARYCENT air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure one-row tables, native 72×4096 shape and unchanged degree/order 19 coefficients. Failed slots remain explicit. Header coordinate coverage does not establish flux or mapping quality.'
p['preserved_raw_context']='Copy the exact V2E2-0026 stored raw/native NPZ. Display original raw_cutout/raw_excess after release using separate full panel scales. Preserve all historical primary, secondary, adopted and mapping-stage qualifications. No new raw mapping, background fit or independent pixel claim.'
p['release_contract']['schema']='HARPS_C007_GROUP_RELEASE_V1'
p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']='Four figures: seven-epoch merged broad/core context with signed and normalized flux in both frames; one native order 19 context; one historical raw/excess pair. Preserve the singleton event/discovery coordinate and R008 label. All finite values retained, no smoothing or clipping; merged frame limits and native raw frame limits match, with 5 percent margins. Historical raw image scales use separate full extrema.'
p['limitations']=[
 'Post-detection context of one U record and seven reused original-cohort exposures; no new observing time, independent detection or archive-wide completeness. The U label is unchanged.',
 'The C007 core lies entirely in completed C006 positive normalization flank. Queue selection preceded C006 results, but subsequent interpretation of overlapping flux is not blind or independent. No old pipeline replay.',
 'One fixed discovery reference observed on 2022-01-05. All six other target epochs are retained. Total BERV span 59.6098131157401 km/s is coordinate separation, not calibrated origin discrimination or survey sensitivity.',
 'One fixed first-discovery topocentric anchor: a later feature may leave the ±0.25 Angstrom core. Those comparisons describe the anchor window, potentially sampling neighboring structure, without recentering.',
 'Fixed reference flanks contain known structure: C006 centers at C007 offsets -2.395 to -2.095 Angstrom remain inside the negative flank. Reference medians are not fitted line-free continua. No masks, alternative flanks, fitted widths, centers, lags, RV, drift or background.',
 'Fresh 72-order header scan confirms only order 19 covers the original feature center. Coordinate coverage does not establish finite or positive flux, valid normalization or local detector mapping.',
 'Historical V2E2-0026 local_mapping_usable=false and baseline_mapping_verified=false remain alongside true global and later five-window diagnostics. Fresh coverage or native/merged shape agreement does not retroactively validate that local raw mapping. No origin assignment.',
 'Native BUNIT absent; native extracted units unspecified. Merged ADU and native scales differ. Same-exposure extraction agreement is not an independent observation or physical flux ratio.',
 'ERR support and descriptive first-difference proxies do not supply a formal error model, calibrated significance, physical width, false-alarm rate, completeness or qualified null.',
 'All previous extraction, raw panels, mapping stages, event labels and epoch outputs remain unchanged.'
]
p['source_hashes']={}
paths=[HERE/n for n in ['compare_group.py','plot_group.py','README.md','prepare_plan.py','synthetic_preflight.py']]
paths += [PHASE/n for n in ['inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','inputs/restore_inputs.py','BASELINE_VERIFICATION.json','input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']]
paths += [old/n for n in ['NEXT_ACTION.json','scientific_review/NEXT_STEP.md','analysis/compare_group.py','analysis/PLAN.json','analysis/plot_group.py']]
for f in paths:p['source_hashes'][str(f.relative_to(REPO))]=sha(f)
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=[{'dp_id':r['dp_id'],'order':o} for r in inv['native_products'] for o in r['covering_orders']]
p['excluded_native_order_pairs']=[]
p['native_order_coverage']=inv['native_order_coverage']
p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']='The single event history and fresh 72-order header scan cover order 19 only. Retain one unique product/order pair and one raw panel with all original mapping stages; no structural exclusions.'
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']} for r in inv['saved_native_raw_cutouts']]
p['event_markers']=[{'event':'V2E2-0026','resolution_group':'R008','center_bary_air_angstrom':4312.7,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':0.,'color':'#b8292f'}]
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots']},indent=2))
