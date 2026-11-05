"""Freeze C033 geometry, inherited numerical rules and the next original route.

Read metadata and file hashes only. Do not decode observational arrays.
"""
from pathlib import Path
import copy, csv, datetime, hashlib, json

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
PREV=ROOT/'work_harps_20261105_c031_context'
ORIG=ROOT/'work_harps_20261101/v2/extension02'
CB=3880.35
BERV=5.77068898867443

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def rows(p):
    with p.open(newline='')as f:return list(csv.DictReader(f))

def main():
    inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
    handoff=read(PREV/'NEXT_ACTION.json')
    prior=read(PREV/'PUBLIC_CONTINUATION_STATE.json')
    base=read(PREV/'analysis/PLAN.json')
    events={r['candidate_id']:r['dp_id']for r in handoff['queue_rows']}
    context={r['candidate_id']:r for r in handoff['existing_context']}
    centers=[float(context[e]['center_bary_air_angstrom'])for e in events]
    refs=list(dict.fromkeys(events.values()))
    assert inv['events']==events and len(events)==len(refs)==4
    assert CB==(min(centers)+max(centers))/2
    assert len(inv['merged_spectra'])==6 and len(inv['native_products'])==4
    assert len(inv['all_order_header_scan'])==288 and len(inv['saved_native_raw_cutouts'])==8
    assert all(n['covering_orders']==[3,4]for n in inv['native_products'])
    p={k:copy.deepcopy(base[k])for k in ['c_km_s','frames','grid','normalization','comparisons','release_contract','completed_normalization_context']}
    ct=CB/(1+BERV/p['c_km_s'])
    p.update(schema='HARPS_C033_JOINT_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='METHOD_FROZEN_BEFORE_CURRENT_ARRAY_VALUES',target='HD126093',scope='C033/R035, four original records and four own discovery references on six existing observations. Common midpoint geometry preserves every original member core; two match and two differ. Eight native product/order windows and eight original raw containers.',events=events,merged_dp_ids=[r['dp_id']for r in inv['merged_spectra']],discovery_dp_ids=refs,inventory_path=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(ROOT)),group_center_bary_air_angstrom=CB,accepted_event_centers_bary_air_angstrom=centers,anchor_dp_id=refs[0],anchor_berv_km_s=BERV)
    p['frames']['topocentric']=f'First-queue April 27 discovery fixes common anchor {ct!r} air Angstrom; query(anchor+x)*(1+BERVepoch/c). Preserve all four own discovery references and their BERV. No fitted recentering.'
    p['grid']['core']=f'51 fixed centers abs(x)<=0.25 around metadata midpoint {CB!r}. Common core {[CB-.25,CB+.25]!r} differs from original-core union {[min(centers)-.25,max(centers)+.25]!r}. Comparisons apply only to common core.'
    p['grid']['broad_pattern']='550 fixed surrounding centers 0.25<abs(x)<=3. Original member-core edges outside common core belong to surrounding context. No fitted exclusion or masks.'
    p['normalization']['structured_neighbor']='Signed original samples in fixed 1.5–3 Angstrom flanks stay unmasked. Header endpoint coverage, finite source support, positive pooled reference and interpolated comparison support are distinct. Missing/insufficient flanks retain raw-only profiles; valid partial flanks are not extrapolated. No line-free continuum claim.'
    p['comparisons']['merged']='6 epochs ×4 own discovery references ×2 frames ×2 regions =96 rows, including16 labeled identical-product self rows.'
    p['comparisons']['native']='8 native product/order pairs ×2 frames ×2 regions =32 same-exposure native-to-own-merged rows.'
    p['comparisons']['self_and_dependency_flags']='Per frame/region20 directed nonself rows are14 unordered observation relationships with6 reciprocal discovery pairs. Six observations total; four discoveries and dependent native extraction add no independent confirmation.'
    p['slots']=dict(merged_profiles=12,native_profiles=16,all_profiles=28,merged_comparisons=96,native_comparisons=32,all_comparisons=128,identical_product_self_comparisons=16,saved_raw_order_panels=8,structurally_excluded_native_order_pairs=0,expected_bounded_input_windows=14,distinct_discovery_products=4,discovery_records=4)
    p['historical_review_records']=inv['historical_raw_review_records']
    p['historical_review_disagreement']=dict(all_four_original_primary_secondary_adopted_U=True,event_specific_secondary_contamination_cautions={r['review_id']:r['contamination_or_blend_caution']for r in inv['historical_raw_review_records']['secondary']},event_specific_additional_uncertainty={r['review_id']:r['additional_uncertainty']for r in inv['historical_raw_review_records']['secondary']},qualification='All original mapping stages are true.0274 retains its own secondary possible compact off-trace deposit/blend caution distinct from the broad centered feature; no caution is transferred to other records.')
    p['historical_mapping_stages']=inv['mapping_records']
    p['skipped_completed_routes']=dict(completed_original_routes=prior['completed_original_routes'],exact_baseline_event_ids=prior['completed_exact_baseline_route_ids'],proof_path=prior['completed_baseline_route_proof_path'],qualification='Every exact completed diagnosis stays closed despite physical U.')
    p['included_native_order_pairs']=[{'dp_id':dp,'order':o}for dp in refs for o in [3,4]]
    p['excluded_native_order_pairs']=[]
    p['excluded_native_order_evidence']=inv['excluded_native_orders']
    p['native_order_coverage']=inv['native_order_coverage']
    p['native_fixed_frame_header_geometry']=[{'dp_id':n['dp_id'],'order':o,'fixed_frame_header_geometry':n['orders'][str(o)]['fixed_frame_header_geometry']}for n in inv['native_products']for o in [3,4]]
    p['preserved_event_raw_pairs']=[{'event':e,'dp_id':dp,'order':o}for e,dp in events.items()for o in [3,4]]
    epochs={r['dp_id']:r for r in inv['merged_spectra']}
    p['event_markers']=[]
    for(e,dp),color in zip(events.items(),['#b8292f','#d99800','#6c3c9c','#147d92']):
        center=float(context[e]['center_bary_air_angstrom']);factor=1+epochs[dp]['berv_km_s']/p['c_km_s'];offset=center-CB
        p['event_markers'].append(dict(event=e,dp_id=dp,resolution_group=context[e]['resolution_group'],center_bary_air_angstrom=center,original_core_bary_air_angstrom=[center-.25,center+.25],barycentric_offset_angstrom=offset,discovery_topocentric_offset_angstrom=center/factor-ct,member_core_half_width_bary_angstrom=.25,member_core_half_width_topo_angstrom=.25/factor,common_core_covers_original_member_core=abs(offset)<1e-12,original_core_inside_broad_context=CB-3<=center-.25 and center+.25<=CB+3,color=color))
    assert sum(m['common_core_covers_original_member_core']for m in p['event_markers'])==2 and all(m['original_core_inside_broad_context']for m in p['event_markers'])
    p['member_core_support_rule']='For every one of 28 fixed profiles and4 original members report only nominal/finite raw/finite normalized grid counts in original member core. Barycentric: center_i-CB ±0.25. Topocentric: center_i/(1+BERVdiscovery_i/c)-CT ±0.25/(1+BERVdiscovery_i/c). Count centers outside common abs(x)<=0.25. No per-member fit,correlation,significance or classification. Discovery-core markers are not fitted locations in other epochs.'
    p['release_contract']=dict(schema='HARPS_C033_GROUP_RELEASE_V1',file='ROOT_RELEASE.json',required_fields=['publication_commit','publication_readback_verified','plan_sha256','script_sha256','inventory_path','inventory_sha256'],policy='Exact public method commit and Git blob/content verification before current observed arithmetic;no archive network queries;one-shot output refuses overwrite;all sources and release hashes rechecked.')
    p['plot_script_sha256']=sha(HERE/'plot_group.py')
    p['plot_pagination']=dict(native_pairs=8,native_rows_per_page=4,native_pages=2,raw_pairs=8,raw_rows_per_page=4,raw_pages=2,total_figures=6)
    p['plot_rules']='Six fixed PNGs: merged broad and core,both frames;two native pages;two original raw pages. All four original/discovery markers and faint original-core boundaries. Same-quantity merged ylimits match across frames,all finite values plus5percent; native raw scales match across frames per order; original raw panels retain full pixels and separate scales. Fixed input order;no fitted variant,smoothing,mask,contrast variant,crop,background or registration.'
    p['bounded_arrays']='14 pre-interpolation source windows retain original indices,signed flux,ERR,both wavelength representations and full-source spacing.28 profiles and8 byte-exact original raw containers. No replay of old extraction,registration or epoch pipelines.'
    p['headers']='Fresh72-order scan on each of4 native products:288 header-order records. Eight native product/order windows selected by own original center coverage. Preserve partial broad-window and flank support,including missing/invalid/low/raw-only/blocked outcomes. Fixed41/440 common-support gates do not change.'
    p['wavelength_dependency']=dict(same_six_existing_observations_reused=True,original_C033_epoch_raw_values_already_exposed=True,all_original_member_cores_inside_C031_broad_window=handoff['all_next_original_member_cores_inside_current_broad_window'],prior_C031_bounded_input_index_path=str((PREV/'analysis/results/BOUNDED_INPUT_INDEX.json').relative_to(ROOT)),prior_C031_array_values_to_read=0,actual_source_index_sharing_audit_required=True,nominal_barycentric_window_overlap_angstrom=handoff['current_next_nominal_window_overlap_angstrom'],source_pixel_independence_claim=False)
    p['limitations']=['Four U records,four own discovery references and six existing observations. Earlier C033 epoch/raw values are exposed. No added observing time,blind validation,physical origin,qualified laser or calibrated survey null.', 'Common metadata midpoint3880.35 with fixed ±0.25 air Angstrom core matches two original cores and differs from the other two. Preserve all original centers,bounds and112 profile/member support records. No full-original-core-union correlation.', 'Own April anchor and own epoch BERVs. No fitted center,width,lag,stellar RV,drift,continuum,background or mask. Topocentric fixed windows can sample neighboring structure.', 'Fresh all72-order scan per discovery gives288 header-order records and eight selected product/order windows in orders3/4. Preserve any partial,nonfinite,nonpositive,low,raw-only or blocked outcomes without transferring C031 quality.', 'All eight original global/local/baseline/later mapping stages are true. Four U/U/U chains remain.0274 has its own secondary possible compact off-trace deposit/blend caution distinct from the broad trace-centered component; no inter-event transfer or origin assignment.', 'Per frame/region20 directed nonself rows are14 unordered relationships with6 reciprocal discovery pairs among six observations. Same-exposure native/merged extraction and references are dependent.', 'Nine physical source IDs overlap C031 and five native/order sources are additional reused products/orders. Actual source-index intersection is audited separately including zero intersections; no prior C031 array reads. Reused exposures and earlier C033 evidence preclude blind validation even when windows are disjoint.', 'Signed structured flanks are not calibrated continua. Uncalibrated merged ADU and unspecified native units use separate divisors. ERR/noise proxies/low flags do not calibrate significance,false-alarm probability,sensitivity or linewidth.', 'Completed exact diagnoses stay closed despite U. Rubin remains limited feasibility,minimum50 unmet. Separate scalar formulas and visual review are by the same assistant;no independent human or separate-agent review.']
    qb=ORIG/'unresolved_context_20261102';queue=rows(qb/'ACTION_QUEUE.csv');all_context=rows(qb/'EVENT_CONTEXT.csv')
    excluded=set(prior['completed_original_routes'])|{'C033'};skip=set(prior['completed_exact_baseline_route_ids'])
    first=min((r for r in queue if r['core_overlap_group']not in excluded and r['candidate_id']not in skip),key=lambda r:int(r['queue_index']))
    group=first['core_overlap_group'];members=[r for r in queue if r['core_overlap_group']==group];ids={r['candidate_id']for r in members};ctx=[r for r in all_context if r['candidate_id']in ids]
    cs=[float(r['center_bary_air_angstrom'])for r in ctx];mid=(min(cs)+max(cs))/2
    assert group=='C034'and first['queue_index']=='73'
    rd=ORIG/'raw_followup_batch04'
    hist={label:[r for r in read(rd/name)[key]if r['review_id']in ids]for label,name,key in [('primary','PRIMARY_VISUAL_REVIEW.json','events'),('secondary','SECONDARY_VISUAL_REVIEW.json','records'),('comparison','REVIEW_COMPARISON.json','events')]}
    hist['adopted']=[r for r in rows(rd/'ADOPTED_DISPOSITIONS.csv')if r['review_id']in ids]
    nxt=dict(schema='HARPS_C033_NEXT_C034_METADATA_V1',status='METADATA_HANDOFF_NOT_EXECUTED',selected_before_current_observed_values=True,selection='First unfinished original queue route after C033,ordered by original queue_index,not group number or current numerical outcomes.',core_overlap_group=group,resolution_groups=sorted({r['resolution_group']for r in members}),target=first['target'],events=[r['candidate_id']for r in members],queue_rows=members,existing_context=ctx,existing_cohort_epochs=handoff['existing_cohort_epochs'],existing_cohort_epoch_count=6,own_discovery_dp_ids=list(dict.fromkeys(r['dp_id']for r in members)),original_centers_bary_air_angstrom=cs,proposed_group_midpoint_air_angstrom=mid,original_member_core_bounds=[[c-.25,c+.25]for c in cs],proposed_common_core_edge_displacements_angstrom=[c-mid for c in cs],proposed_anchor_dp_id=members[0]['dp_id'],proposed_anchor_berv_km_s=epochs[members[0]['dp_id']]['berv_km_s'],berv_span_km_s=handoff['berv_span_km_s'],historical_mapping_stages=[r for r in read(rd/'NATIVE_MAPPING.json')['orders']if r['review_id']in ids],historical_review_records=hist,raw_source_directory=str(rd.relative_to(ROOT)),current_next_nominal_window_overlap_angstrom=max(0,min(CB+3,mid+3)-max(CB-3,mid-3)),all_next_original_member_cores_inside_current_broad_window=all(CB-3<=c-.25 and c+.25<=CB+3 for c in cs),next_original_cores_intersect_current_positive_flank=any(max(CB+1.5,c-.25)<=min(CB+3,c+.25)for c in cs),source_pixel_independence_claim=False,new_array_reads=False,new_queries=0,new_diagnostic_frozen=False,labels_unchanged=True,requirements='Restore own native and original event/order raw sources;fresh all72-order headers per product. Freeze own common/member geometry and retain partial/invalid/low/raw-only cases. No transferred quality,mapping stages or morphology. Shared pixels and exposures remain dependent.')
    sources=[qb/n for n in ['ACTION_QUEUE.csv','EVENT_CONTEXT.csv','CORE_OVERLAP_GROUPS.csv']]+[rd/n for n in ['NATIVE_MAPPING.json','PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','REVIEW_COMPARISON.json','ADOPTED_DISPOSITIONS.csv']]+[ORIG/'epoch_followup/INPUT_CHECKS.json']
    nxt['source_hashes']={str(f.relative_to(ROOT)):sha(f)for f in sources}
    write(PHASE/'scientific_review/NEXT_GROUP_METADATA.json',nxt)
    sources += [HERE/n for n in ['prepare_plan.py','compare_group.py','plot_group.py','synthetic_preflight.py']]+[PHASE/n for n in ['BASELINE_VERIFICATION.json','PUBLICATION_AUTHORIZATION.json','C031_INTEGRATION_RECEIPT.json','inputs/restore_inputs.py','inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','input_audit/audit_inputs.py','input_audit/INPUT_AUDIT.json','independent_audit/independent_math.py','independent_audit/audit_prospective.py','independent_audit/audit_actual.py','scientific_review/NEXT_GROUP_METADATA.json']]+[PREV/n for n in ['PUBLIC_CONTINUATION_STATE.json','NEXT_ACTION.json','GROUP_CLOSURE.json','analysis/PLAN.json','analysis/compare_group.py','analysis/results/OUTPUT_HASHES.json','analysis/results/BOUNDED_INPUT_INDEX.json']]
    p['source_hashes']={str(f.relative_to(ROOT)):sha(f)for f in sources}
    p['source_hashes'].update(inv['source_hashes'])
    p['source_hashes'].update({f['path']:f['sha256']for f in inv['files']})
    write(HERE/'PLAN.json',p)
    print(json.dumps(dict(plan_sha256=sha(HERE/'PLAN.json'),source_bindings=len(p['source_hashes']),slots=p['slots'],next_group=group,next_records=len(ctx),next_discoveries=len(nxt['own_discovery_dp_ids']),next_midpoint=mid),indent=2))

if __name__=='__main__':main()
