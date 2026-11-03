#!/usr/bin/env python3
"""Freeze C016 joint metadata and sources before observational array access."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent
OLD=REPO/'work_harps_20261103_c011_context'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
handoff=read(OLD/'NEXT_ACTION.json');inv=read(PHASE/'inputs/INPUT_INVENTORY.json');p=read(OLD/'analysis/PLAN.json')
CB=4303.7875;ANCHOR='ADP.2022-03-08T01:01:37.348';BERV=19.1606928163471
CENTERS={'V2E2-0094':4303.785,'V2E2-0096':4303.785,'V2E2-0098':4303.785,'V2E2-0110':4303.79}
included=[{'dp_id':r['dp_id'],'order':o} for r in inv['native_products'] for o in r['covering_orders']]
raw_count=len(inv['saved_native_raw_cutouts']);native_count=len(included);reference_count=len(set(inv['events'].values()))
p.update(schema='HARPS_C016_JOINT_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target='HD114386',status='METHOD_FROZEN_BEFORE_ARRAY_VALUES')
p['scope']=('Joint C016 / R017 group V2E2-0094/0096/0098/0110 on HD114386, selected by '
 'original unfinished queue row 27 and retaining all original members at rows 27/29/30/32. '
 'Keep own seven January 2022–August 2023 epochs and all four distinct fixed discovery references. '
 'The exact group midpoint 4303.7875 Angstrom follows catalog extrema, not fitted peaks; exact '
 'member centers/cores and all discovery markers remain explicit. This changes target from '
 'HD112410. Original epoch/raw and completed other-wavelength normalization evidence already '
 'exist; no blind, untouched, independent-data or new observing-time claim.')
p['historical_review_disagreement']=handoff['historical_review_disagreement'];p['historical_mapping_stages']=inv['mapping_records']
p['events']=inv['events'];p['merged_dp_ids']=[r['dp_id'] for r in inv['merged_spectra']];p['discovery_dp_ids']=list(dict.fromkeys(inv['events'].values()))
p['inventory_path']=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(REPO));p['group_center_bary_air_angstrom']=CB
p['accepted_event_centers_bary_air_angstrom']=list(dict.fromkeys(CENTERS.values()));p['individual_event_centers_bary_air_angstrom']=CENTERS
p['individual_event_cores_bary_air_angstrom']={e:[center-.25,center+.25] for e,center in CENTERS.items()}
p['common_core_member_relation']=('Comparisons use the unchanged common midpoint ±0.25 Angstrom core '
 '[4303.5375,4304.0375], with 51 centers. It is not the union of member-original cores: '
 '4303.785-centered original cores extend 0.0025 Angstrom below it; the 4303.79-centered '
 'original core extends0.0025 Angstrom above it. Keep exact individual markers/core bounds; '
 'do not claim whole original-member-core coverage or widen the common comparison mask.')
p['anchor_dp_id']=ANCHOR;p['anchor_berv_km_s']=BERV
p['frames']['topocentric']=('One common fixed ct=group_center/(1+BERVanchor/c), using first '
 'original-queue discovery V2E2-0094 observed 2022-03-07, BERV 19.1606928163471 km/s. '
 'Query barycentric wavelength(ct+x)*(1+BERVepoch/c), equivalent to native topocentric '
 'wavelengthct+x. Retain all four discovery references and exact catalog/discovery markers '
 'separately; coordinate anchor is not a favorable-reference selection.')
p['grid']['core']=('abs(x)<=0.25:51 sampled centers[-0.25,+0.25] in fixed common core '
 '[4303.5375,4304.0375]Angstrom, distinct from exact individual original cores; no fitted linewidth.')
p['grid']['broad_pattern']='0.25<abs(x)<=3:550 sampled centers around fixed common midpoint.'
p['normalization']['structured_neighbor']=('Retain every fixed-flank source sample and spectral '
 'structure without masks or assumed line-free regions. Original C016 epoch/raw evidence '
 'and same-target observations already exist. Pooled medians are descriptive levels, '
 'not fitted or established line-free continua; no quality outcome is inherited from C011.')
p['comparisons']['merged']=f'7 own-target epochs × {reference_count} distinct fixed discovery references × 2frames × 2regions = {28*reference_count} records, including {4*reference_count} identical-product self rows. Retain every reference, every cross-discovery direction and every dependency flag.'
p['comparisons']['native']=f'{native_count} native covering-order contexts × 2frames × 2regions = {4*native_count} same-exposure native-to-merged records. Native profiles compare only with their own-exposure merged product, not all four discovery references; shared extraction is dependent.'
p['comparisons']['per_reference_nonself_accounting']='Six other epochs per reference and frame/region. Four references yield 24 ordered nonself rows per frame/region reusing seven observations; reciprocal cross-discovery rows are dependent,not 24 independent epochs.'
p['comparisons']['minimum_common_core']=41;p['comparisons']['minimum_common_broad']=440
p['comparisons']['self_and_dependency_flags']=('Retain same_exposure and identical_product_self_pair '
 'flags for all four fixed references and seven reused HD114386 products. Cross-discovery '
 'pairs and both directional rows are dependent; multiple reference comparisons are not '
 'independent detections or additional observations.')
p['slots']={'merged_profiles':14,'native_profiles':2*native_count,'all_profiles':14+2*native_count,'merged_comparisons':28*reference_count,'native_comparisons':4*native_count,'all_comparisons':28*reference_count+4*native_count,'identical_product_self_comparisons':4*reference_count,'saved_raw_order_panels':raw_count,'structurally_excluded_native_order_pairs':len(inv['excluded_native_orders']),'expected_bounded_input_windows':7+native_count,'distinct_discovery_products':reference_count,'discovery_records':len(inv['events'])}
p['bounded_arrays']=(f'Save{7+native_count} pre-interpolation source windows with exact indices, '
 'original-frame and barycentric wavelengths,signed flux,ERR(NaN for unavailable native '
 'errors),source hashes,BERV and full-source spacing. Read only union needed by both '
 'fixed-frame windows plus brackets; no extrapolation or original-pipeline replay.')
p['headers']=('Check all seven HD114386 merged headers and each of four discovery native '
 'headers before flux access:exact identities/hashes/metadata,numeric BERV,merged '
 'barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables,native '
 '72×4096 shape and freshly recorded selected-order polynomial coefficients. Geometric '
 'support,finite flux,reference validity and historical mapping reliability remain distinct.')
p['preserved_raw_context']=('Copy all four exact event-specific historical order 19 raw/native '
 'NPZs for 0094/0096/0098/0110 and display original raw_cutout/raw_excess after release '
 'at separate full scales. Preserve all primary/secondary/adopted U reviews and each '
 'historical global/local/baseline/later-five-window stage,true in these four contexts. '
 'Do not transfer separate 0092 registration discrepancy or C011 quality outcomes. '
 'No new registration,subtraction,spatial model,pixel statistic or origin claim.')
p['release_contract']['schema']='HARPS_C016_GROUP_RELEASE_V1';p['plot_script_sha256']=sha(HERE/'plot_group.py')
p['plot_rules']=('Four complete figures:all seven merged epochs in broad/core signed and '
 'scaled views in both frames,all four discovery-native contexts,and all four raw/excess '
 'pairs. Retain all four exact member/discovery markers and ID-labeled reference epochs; '
 'three barycentric markers coincide at -0.0025 Angstrom and 0110 at +0.0025 Angstrom. '
 'Markers outside common core remain explicit in metadata,legend and broad view. '
 'Retain raw-only reasons,any low/invalid reference and partial support. Same-quantity '
 'merged scales match across frames; native raw scales match across frames per source. '
 'Every finite value remains with 5 percent margins; raw images use separate full extrema. '
 'No smoothing,clipping,favorable reference/epoch selection or contrast variant.')
p['skipped_completed_routes']=handoff['skipped_completed_routes'];p['completed_normalization_context']=handoff['completed_normalization_context']
p['limitations']=[
 'Four unresolved U events and seven reused HD114386 exposures; no new observing time,independent detections,archive-wide completeness or physical-origin assignments.',
 'Target/cohort changes from HD112410 to HD114386. Use own January 2022–August 2023 seven epochs, four distinct discovery references and BERV span 51.572001697156 km/s; no prior target products,May 2025 reference,numeric anchor or quality outcomes transferred.',
 'Common midpoint 4303.7875Angstrom derives from exact catalog extrema 4303.785/4303.79. Its fixed ±0.25 common core is not the union of individual original cores; each member-original core extends0.0025Angstrom outside one common edge. Preserve all member centers/core bounds and markers without fitted changes.',
 'One common fixed topocentric anchor uses first queue discovery observed 2022-03-07 BERV 19.1606928163471 km/s. All four references remain in every merged comparison. Fixed anchor is not recentered on later epochs; coherent catalog centers may leave the core,which may then describe neighboring structure.',
 'BERV span is coordinate separation,not calibrated origin discrimination. All-reference cross-discovery rows,both directional pairs,self rows and native/merged extraction agreement are dependent rather than extra observing evidence.',
 'All fixed-flank structure remains in pooled medians; reference levels are not established line-free continua. No fitted width,center,lag,stellarRV,drift,background,continuum,masks or moved flanks.',
 'Fresh all 72 order headers per discovery determine native scope and context/core/flank support. Coordinate coverage does not establish finite flux,positive references,false low flags or usable statistics; every invalid/missing outcome retains a slot and reason.',
 'All four original order 19 contexts retain true global-grid,local,baseline and later-five-window support. Preserve these historical stages without transferring a different event/wavelength registration discrepancy or treating mapping support as origin evidence.',
 'All historical primary/secondary/adopted reviews remain U for broad rounded native structure,neighboring shoulders and weak diffuse trace-associated excess. No current morphology,correlation or extraction agreement promotes a record or qualifies a laser candidate.',
 'Native extracted units are unspecified when BUNIT absent,distinct from merged ADU. ERR support and descriptive first-difference/low-reference proxies do not establish formal uncertainty,significance,physical linewidth,false-alarm rate,sensitivity or a qualified survey null.',
 'C016 bounded window is disjoint from completed C001–C012 group windows,but original C016 epoch/raw and same HD114386 other-wavelength normalization evidence already exist. This is not blind,untouched or independent-data validation.',
 'Completed NORMALIZATION_CONTEXT routes 0092/C013 row 26 and 0104/C014 row 31 remain complete and U; they are skipped rather than replayed. Their separate raw-window registration qualification remains local to that evidence. All earlier outputs and classifications remain immutable.'
]
paths=[HERE/n for n in ['compare_group.py','plot_group.py','README.md','prepare_plan.py','synthetic_preflight.py']]
paths += [PHASE/n for n in ['inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','inputs/restore_inputs.py','BASELINE_VERIFICATION.json','input_audit/INPUT_AUDIT.json','input_audit/audit_inputs.py']]
paths += [OLD/n for n in ['NEXT_ACTION.json','scientific_review/NEXT_STEP.md','analysis/compare_group.py','analysis/PLAN.json','analysis/plot_group.py']]
prior=[]
for number in range(1,13):
 f=REPO/(('work_harps_20261102_' if number<=8 else 'work_harps_20261103_')+f'c{number:03d}_context/analysis/PLAN.json')
 q=read(f);center=q['group_center_bary_air_angstrom'];window=[center+x for x in q['grid']['window_angstrom']]
 target=q.get('target','HD106515A');disjoint=window[1]<CB-3 or window[0]>CB+3
 assert disjoint and target!='HD114386'
 prior.append({'group':f'C{number:03d}','target':target,'window_bary_air_angstrom':window,'numerically_disjoint_from_C016':True,'shared_source_pixels':False,'dependency_note':'Different target/observing products and disjoint bounded wavelength window; original same-target epoch/raw evidence remains prior evidence.','plan_path':str(f.relative_to(REPO))});paths.append(f)
p['prior_bounded_window_geometry']=prior
for path in handoff['prospective_next_group_metadata']['source_sha256']:
 if '/normalization_context_20261102/' in path:paths.append(REPO/path)
p['source_hashes']={str(f.relative_to(REPO)):sha(f) for f in paths}
for f in inv['files']:p['source_hashes'][f['path']]=f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs']=included;p['excluded_native_order_pairs']=[];p['native_order_coverage']=inv['native_order_coverage'];p['excluded_native_order_evidence']=inv['excluded_native_orders']
p['native_order_selection']=('Fresh all-order header scan at each exact original event center '
 'determines all covering orders in each discovery. Retain every original covering order '
 'and declared exclusion; no scope,missing-flank,low-reference or mapping outcome inherited '
 'from previous targets. Header support remains distinct from flux quality.')
p['native_fixed_frame_header_geometry']=[{'dp_id':r['dp_id'],'order':o,'fixed_frame_header_geometry':r['orders'][str(o)]['fixed_frame_header_geometry']} for r in inv['native_products'] for o in r['covering_orders']]
p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':inv['events'][r['event']],'order':r['order']} for r in inv['saved_native_raw_cutouts']]
B={r['dp_id']:r['berv_km_s'] for r in inv['merged_spectra']};c=p['c_km_s'];ct=CB/(1+BERV/c)
colors=['#b8292f','#3568a8','#df7b20','#8156a6']
p['event_markers']=[{'event':e,'resolution_group':'R017','discovery_dp_id':dp,'center_bary_air_angstrom':CENTERS[e],'barycentric_offset_angstrom':CENTERS[e]-CB,'discovery_topocentric_offset_angstrom':CENTERS[e]/(1+B[dp]/c)-ct,'color':colors[i]} for i,(e,dp) in enumerate(inv['events'].items())]
assert inv['target']=='HD114386' and list(p['events'])==list(CENTERS)
assert p['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert p['discovery_dp_ids']==handoff['distinct_discovery_products'] and p['anchor_dp_id']==p['discovery_dp_ids'][0] and B[ANCHOR]==BERV
assert max(B.values())-min(B.values())==handoff['berv_span_km_s']==51.572001697156
assert included==[{'dp_id':dp,'order':19} for dp in p['discovery_dp_ids']] and raw_count==4 and reference_count==4 and not p['excluded_native_order_evidence']
assert len(p['event_markers'])==4 and len(p['individual_event_cores_bary_air_angstrom'])==4
(HERE/'PLAN.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'sources':len(p['source_hashes']),'slots':p['slots'],'anchor_air_angstrom':ct},indent=2))
