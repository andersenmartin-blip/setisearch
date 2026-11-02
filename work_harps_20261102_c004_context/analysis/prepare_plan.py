#!/usr/bin/env python3
"""Assemble C004's prospective plan from exact metadata, not flux values."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
old=REPO/'work_harps_20261102_c007_context'
p=read(old/'analysis/PLAN.json');inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
p['schema']='HARPS_C004_JOINT_PROFILE_CONTEXT_V1'
p['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
p['scope']='All three C004 / R004 records V2E2-0028/0045/0052 on HD106515A at 3872.245 Angstrom, retaining seven existing cohort epochs and all three unique discovery references. The original core was already visible in C003 positive reference flank: overlapping post-detection context, not blind or independent validation or new observing time.'
p['events']=inv['events'];p['merged_dp_ids']=[r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom']=3872.245;p['accepted_event_centers_bary_air_angstrom']=[3872.245]*3
p['anchor_dp_id']='ADP.2022-03-08T01:01:37.342';p['anchor_berv_km_s']=10.77158288517
p['frames']['topocentric']='One fixed ct = cb/(1+BERVfirstC004discovery/c), anchored to V2E2-0028 observed on 2022-03-07 with BERV 10.77158288517 km/s. Query barycentric wavelength (ct+x)*(1+BERVepoch/c), equivalent to native topocentric wavelength ct+x. All three references share this anchor; no January-anchor inheritance or recentering. Later features may leave the fixed core.'
p['grid']['core']='abs(x)<=0.25: 51 sampled centers [-0.25,+0.25]. All three original cores coincide at 3871.995–3872.495 Angstrom.'
p['grid']['broad_pattern']='0.25<abs(x)<=3: 550 sampled centers.'
p['normalization']['structured_neighbor']='C003 original core union 3869.495–3870.0075 Angstrom lies fully in C004 negative reference flank 3869.245–3870.745 Angstrom. Retain that known structure without masks. C004 original core was visible in C003 positive flank; shared window values and observing products are not independent validation. Reference medians are not line-free continua.'
p['comparisons']['merged']='7 epochs × 3 unique fixed discovery references × 2 frames × 2 regions = 84 records, including 12 identical-product self-comparisons.'
p['comparisons']['native']='3 unique discovery/order 3 pairs × 2 frames × 2 regions = 12 same-exposure native-to-merged records. Shared extraction is not independent confirmation or a physical flux ratio.'
p['comparisons']['minimum_common_core']=41;p['comparisons']['minimum_common_broad']=440
p['comparisons']['self_and_dependency_flags']='same_exposure and identical_product_self_pair flags are explicit. All three record identities and unique reference products retained. Reversed discovery pairs, shared epochs and prior C003 window overlap are dependent.'
p['slots']={'merged_profiles':14,'native_profiles':6,'all_profiles':20,'merged_comparisons':84,'native_comparisons':12,'all_comparisons':96,'identical_product_self_comparisons':12,'saved_raw_order_panels':3,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':10,'distinct_discovery_products':3,'discovery_records':3}
p['bounded_arrays']='Save ten pre-interpolation source windows with exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native errors), source hashes, BERV and full-source spacing. Read only the union required by both fixed-frame windows plus brackets. Full merged coordinates locate slices; native coordinates derive from headers. Preserve known C003 overlap.'
p['headers']='Check all seven merged and three native headers before new flux access: exact identity/hash, recorded metadata, numeric BERV, merged BARYCENT air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native 72×4096 shape and unchanged degree/order 3 coefficients. Failed slots remain explicit; coordinate coverage is distinct from flux quality and mapping reliability.'
p['preserved_raw_context']='Copy the three exact V2E2-0028/0045/0052 historical raw/native NPZs. Display original raw_cutout/raw_excess after release using separate full scales. Preserve all primary, secondary, adopted and mapping stages; no new registration, subtraction, detector model or independent pixel claim.'
p['release_contract']['schema']='HARPS_C004_GROUP_RELEASE_V1'
p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']='Four figures: all seven merged broad/core profiles with signed and normalized flux in both frames; all three native order 3 contexts; all three historical raw/excess pairs. All three R004 catalog centers coincide barycentrically, but discovery topocentric markers differ with BERV and retain identities/colors. Markers are not fitted peaks. No smoothing/clipping or favorable selection; matching merged frame and native raw limits retain every finite value with 5 percent margins. Raw image panels use separate full extrema.'
p['limitations']=[
 'Post-detection context of three U records and seven reused original-cohort exposures; no new observing time, independent detections or archive-wide completeness. All three U labels unchanged.',
 'The C004 original core lies entirely inside completed C003 positive reference flank. Queue selection preceded C007 results, but these flux values were already seen in C003. This is not blind or independent validation; no old pipeline replay.',
 'All three distinct discovery references fixed before new interpretation. First C004 discovery is 2022-03-07, BERV 10.77158288517 km/s; do not inherit January 2022 anchor. The seven-epoch BERV span 59.6098131157401 km/s is coordinate separation, not calibrated origin discrimination.',
 'The single fixed topocentric anchor is not recentered on later features. A coherent center may leave the ±0.25 Angstrom core, causing comparisons to describe neighboring structure.',
 'Known C003 core structure lies in the C004 negative reference flank. Fixed pooled medians are reference levels, not fitted line-free continua. No masks, moved flanks, fitted widths/centers/lags/RV/drift/background.',
 'Fresh all-216-order header scan identifies only order 3 covering each original feature center. Do not transfer C003 order 2 coverage limitations to this wavelength. Coordinate coverage does not establish finite or positive flux or usable normalization.',
 'Historical global/local/baseline/five-window mapping flags are true for all three records, but remain historical diagnostics rather than new mapping or physical-origin validation. All prior raw reviews and panels remain exact.',
 'Native BUNIT absent; native extracted units unspecified. Merged ADU and native scales differ; same-exposure extraction agreement is not independent confirmation or a physical flux ratio.',
 'ERR support and descriptive first-difference proxies do not establish a formal uncertainty model, significance, physical linewidth, false-alarm rate, sensitivity or qualified null.',
 'All previous extraction, mapping, raw panels, record labels and epoch outputs remain unchanged.'
]
p['source_hashes']={}
paths=[HERE/n for n in ['compare_group.py','plot_group.py','README.md','prepare_plan.py','synthetic_preflight.py']]
paths += [PHASE/n for n in ['inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','inputs/restore_inputs.py','BASELINE_VERIFICATION.json','input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']]
paths += [old/n for n in ['NEXT_ACTION.json','scientific_review/NEXT_STEP.md','analysis/compare_group.py','analysis/PLAN.json','analysis/plot_group.py']]
paths += [REPO/'work_harps_20261102_c003_context/analysis/PLAN.json']
for f in paths:p['source_hashes'][str(f.relative_to(REPO))]=sha(f)
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=[{'dp_id':r['dp_id'],'order':o} for r in inv['native_products'] for o in r['covering_orders']]
p['excluded_native_order_pairs']=[];p['native_order_coverage']=inv['native_order_coverage'];p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']='All three event histories and fresh 216-order scan identify order 3 only. Retain all three unique product/order pairs and raw panels, preserving original mapping stages. No structural exclusions.'
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']} for r in inv['saved_native_raw_cutouts']]
B={r['dp_id']:r['berv_km_s'] for r in inv['merged_spectra']};cb=p['group_center_bary_air_angstrom'];c=p['c_km_s'];ct=cb/(1+p['anchor_berv_km_s']/c)
p['event_markers']=[{'event':event,'resolution_group':'R004','center_bary_air_angstrom':cb,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':cb/(1+B[dp]/c)-ct,'color':color} for (event,dp),color in zip(inv['events'].items(),['#b8292f','#1b62b3','#e68c1a'])]
assert p['anchor_dp_id']==p['discovery_dp_ids'][0] and B[p['anchor_dp_id']]==p['anchor_berv_km_s']
assert len(p['included_native_order_pairs'])==3 and all(x['order']==3 for x in p['included_native_order_pairs'])
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots'],'anchor_berv_km_s':p['anchor_berv_km_s']},indent=2))
