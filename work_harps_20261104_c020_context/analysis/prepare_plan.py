"""Freeze own-May C020 context, source dependence and the next unfinished route."""
from pathlib import Path
import copy,csv,datetime,hashlib,json
HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OLD=ROOT/'work_harps_20261104_c023_context'
CB=4303.13
BERV=-17.1985506565257
DP='ADP.2023-05-16T01:01:18.574'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    inv=read(PHASE/'inputs/INPUT_INVENTORY.json');handoff=read(OLD/'NEXT_ACTION.json');base=read(OLD/'analysis/PLAN.json')
    assert inv['target']=='HD114783' and inv['events']=={'V2E2-0136':DP}
    assert [r['dp_id'] for r in inv['merged_spectra']]==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
    assert inv['native_products'][0]['covering_orders']==[19] and len(inv['saved_native_raw_cutouts'])==1
    ct=CB/(1+BERV/299792.458)
    p={k:copy.deepcopy(base[k]) for k in ['c_km_s','frames','grid','normalization','comparisons','release_contract']}
    p.update(schema='HARPS_C020_INDIVIDUAL_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='METHOD_FROZEN_BEFORE_ARRAY_VALUES',target='HD114783',scope='Original queue row53, singleton C020/R021/V2E2-0136. Own May15 2023 discovery, seven existing January2022–July2023 observations, sole covering native order19 and its original raw container. Retain the broad native peak, nearby secondary structure and diffuse raw ambiguity; no new observing time or independent validation.',events=inv['events'],merged_dp_ids=[r['dp_id'] for r in inv['merged_spectra']],discovery_dp_ids=[DP],inventory_path=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(ROOT)),group_center_bary_air_angstrom=CB,accepted_event_centers_bary_air_angstrom=[CB],anchor_dp_id=DP,anchor_berv_km_s=BERV)
    p['frames']['topocentric']=f'Own May15 2023 discovery BERV fixes anchor {ct!r} air Angstrom. Query (anchor+x)*(1+BERVepoch/c); no fitted shift or recentering. No prior February/January reference is transferred.'
    p['grid']['core']='51 fixed centers, abs(x)<=0.25; exact original [4302.88,4303.38] air Angstrom.'
    p['grid']['broad_pattern']='550 fixed surrounding centers, 0.25<abs(x)<=3; context [4300.13,4306.13] air Angstrom.'
    p['normalization']['structured_neighbor']='Retain signed samples in fixed1.5–3Angstrom flanks without masks or a line-free claim. Nominal barycentric windows are disjoint from C021, but different fixed anchors expand the selected both-frame source unions; a July overlap and any interpolation-bracket sharing must be retained and audited from source indices.'
    p['comparisons']['merged']='7 existing own-target epochs ×1 own May15 reference ×2 frames ×2 regions =28 rows, including4 labelled identical-product self rows.'
    p['comparisons']['native']='1 own native covering order ×2 frames ×2 regions =4 same-exposure native-to-merged rows; dependent extraction agreement, not another observation or a physical flux ratio.'
    p['comparisons']['self_and_dependency_flags']='One reference, six other epochs and six nonself observation relationships per frame/region. All observations and original0136 epoch/raw evidence are already exposed; four self rows add no recurrence evidence.'
    p['slots']={'merged_profiles':14,'native_profiles':2,'all_profiles':16,'merged_comparisons':28,'native_comparisons':4,'all_comparisons':32,'identical_product_self_comparisons':4,'saved_raw_order_panels':1,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':8,'distinct_discovery_products':1,'discovery_records':1}
    p['historical_review_records']=inv['historical_raw_review_records']
    p['historical_review_disagreement']={'primary_code':'U','secondary_code':'U','root_adopted_code':'U','current_code':'U','qualification':'Original broad rounded native peak, secondary nearby rise and weak diffuse raw enhancement remain U/U/U. No C023 asymmetric morphology or February reference is transferred.'}
    p['historical_mapping_stages']=inv['mapping_records'];p['skipped_completed_routes']=base['skipped_completed_routes'];p['completed_normalization_context']=base['completed_normalization_context']
    p['included_native_order_pairs']=[{'dp_id':DP,'order':19}];p['excluded_native_order_pairs']=[];p['excluded_native_order_evidence']=inv['excluded_native_orders'];p['native_order_coverage']=inv['native_order_coverage']
    p['native_fixed_frame_header_geometry']=[{'dp_id':DP,'order':19,'fixed_frame_header_geometry':inv['native_products'][0]['orders']['19']['fixed_frame_header_geometry']}]
    p['preserved_event_raw_pairs']=[{'event':'V2E2-0136','dp_id':DP,'order':19}]
    p['event_markers']=[{'event':'V2E2-0136','resolution_group':'R021','center_bary_air_angstrom':CB,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':0.,'color':'#b8292f'}]
    p['release_contract']['schema']='HARPS_C020_GROUP_RELEASE_V1';p['plot_script_sha256']=sha(HERE/'plot_group.py')
    p['plot_rules']='Four fixed figures: all seven merged broad/core curves in both frames, own order19 and original full raw/excess pair. Matched same-quantity merged y scales, matched native raw scales, all finite values plus5percent margin and separate full raw-image scales. No fitted variant, smoothing, mask, alternate contrast, crop, subtraction or registration.'
    p['bounded_arrays']='Eight pre-interpolation source windows preserve exact indices, signed flux, ERR, both wavelength representations and full-source median spacing. Save sixteen profiles and the exact original raw container; no old pipeline replay.'
    p['headers']='Verify all seven own-target merged identities/units/dates/BERV/progenitors and one May discovery native product. Freshly scan all72order headers and retain own order19 coverage. Geometry is separate from finite flux, positive reference and common support.'
    p['limitations']=[
        'One unresolved record and seven reused observations; original0136 epoch/raw values were already exposed. No new observing time, blind or untouched-data validation, physical-origin assignment, qualified laser or calibrated survey null.',
        'Exact original4303.13Å center and±0.25core, fixed±3context and own May15 2023 BERV-17.1985506565257km/s. No fitted center,width,lag,stellarRV,drift,continuum,background or mask.',
        'Fresh all72native headers select own order19. Header support does not establish finite flux, reference validity or adequate common samples; preserve all partial,invalid,nonpositive,low,missing or blocked slots.',
        'All four original/later order19 mapping stages are true. Mapping support and same-exposure extraction agreement do not classify the broad native peak or diffuse raw enhancement; current U/U/U stays.',
        'Nominal C020/C021 barycentric windows are disjoint, but the both-frame source unions overlap for July2023 and interpolation brackets can add sharing. Audit exact source-index overlap against preserved C021 metadata after the run; no source-pixel independence claim or mask follows.',
        'The same January2022–July2023 cohort spans59.073251754930496km/s in BERV. A fixed topocentric core can sample neighboring structure when a predicted coherent center leaves it. Geometry and frame statistics are descriptive, not calibrated origin tests.',
        'Signed pooled flanks retain structured source samples and are not established line-free continua. Native BUNIT is unspecified, merged units are uncalibrated ADU and their relative divisors are not physical flux ratios.',
        'ERR and first-difference/low-reference proxies do not calibrate formal significance, false-alarm probability, sensitivity or linewidth.',
        'Completed mapping,normalization,baseline/May-quality and spatial routes stay closed. Skipped exact baseline diagnostics remain physically U, including four HD135204 records with no new selected epoch; no archive-wide absence claim.',
        'Separate scalar formulas and fresh processes are run by the same assistant; no independent human or separate-agent review is claimed. Rubin remains limited feasibility with minimum50unmet.'
    ]
    prior=[];paths=[];unions=[]
    for dirname in ['work_harps_20261104_c017_context','work_harps_20261103_c018_context','work_harps_20261103_c019_context','work_harps_20261103_c021_context','work_harps_20261103_c022_context','work_harps_20261104_c023_context']:
        f=ROOT/dirname/'analysis/PLAN.json';q=read(f);center=q['group_center_bary_air_angstrom'];window=[center-3,center+3];assert window[1]<CB-3 or window[0]>CB+3
        prior.append({'plan_path':str(f.relative_to(ROOT)),'nominal_barycentric_window':window,'nominal_window_disjoint':True,'same_observing_products':True,'source_pixel_independence_claim':False});paths.append(f)
        if 'c021_' in dirname:
            priorct=center/(1+q['anchor_berv_km_s']/p['c_km_s'])
            for epoch in inv['merged_spectra']:
                factor=1+epoch['berv_km_s']/p['c_km_s'];current=[min(CB-3,(ct-3)*factor),max(CB+3,(ct+3)*factor)];previous=[min(center-3,(priorct-3)*factor),max(center+3,(priorct+3)*factor)]
                unions.append({'dp_id':epoch['dp_id'],'current_source_union_angstrom':current,'prior_C021_source_union_angstrom':previous,'gap_before_interpolation_brackets_angstrom':previous[0]-current[1],'coordinate_overlap_width_angstrom':max(0.,min(current[1],previous[1])-max(current[0],previous[0]))})
    depfile=ROOT/'work_harps_20261103_c021_context/analysis/results/BOUNDED_INPUT_INDEX.json';paths.append(depfile)
    p['wavelength_dependency']={'same_seven_observing_products':True,'original_0136_epoch_raw_evidence_already_exposed':True,'prior_nominal_window_geometry':prior,'C021_source_union_geometry':unions,'C021_bounded_input_index_path':str(depfile.relative_to(ROOT)),'actual_source_index_sharing_audit_required':True,'prior_C021_array_values_to_read':0}
    queuebase=ROOT/'work_harps_20261101/v2/extension02/unresolved_context_20261102';queue=list(csv.DictReader((queuebase/'ACTION_QUEUE.csv').open()));contexts=list(csv.DictReader((queuebase/'EVENT_CONTEXT.csv').open()))
    bp=ROOT/'work_harps_20261102_berv_followup/prospective_comparison';mp=ROOT/'work_harps_20261102_may_quality/comparison'
    bids={r['candidate_id'] for r in read(bp/'EVENTS.json')};mids={r['candidate_id'] for r in read(mp/'EVENTS.json')};assert bids==mids and len(bids)==10
    assert read(bp/'results/SUMMARY.json')['status']=='COMPLETE_FIXED_DESCRIPTIVE_COMPARISON' and read(mp/'results/SUMMARY.json')['status']=='COMPLETE_FIXED_DESCRIPTIVE_COMPARISON'
    skipped=[r for r in queue if r['candidate_id'] in bids and r['primary_evidence_route']=='FRAME_BASELINE_CONTEXT'];assert len(skipped)==10
    proof_paths=[bp/'PLAN.json',bp/'EVENTS.json',bp/'results/SUMMARY.json',mp/'PLAN.json',mp/'EVENTS.json',mp/'results/SUMMARY.json']
    skipproof={'schema':'HARPS_C020_COMPLETED_ROUTE_SKIP_PROOF_V1','status':'EXACT_BOUNDED_BASELINE_DIAGNOSTICS_ALREADY_COMPLETE','skip_selection_not_from_C020_values':True,'skipped_rows':skipped,'event_ids':sorted(bids),'source_hashes':{str(f.relative_to(ROOT)):sha(f) for f in proof_paths},'qualification':'Skip only these exact completed FRAME_BASELINE_CONTEXT diagnostics, not physical U issues or future distinct evidence. Six HD122640 records have closed BERV and separate May-quality comparisons. Four HD135204 records retained no new selected epoch under bounded filters; zero rows are not archive-wide absence. The separate0235 spatial/background diagnostic is also closed.'}
    write(PHASE/'scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json',skipproof);paths+=proof_paths
    remaining=[r for r in queue if r['core_overlap_group'] not in {f'C{i:03d}' for i in range(1,24)} and r['candidate_id'] not in bids];first=min(remaining,key=lambda r:int(r['queue_index']))
    assert first['core_overlap_group']=='C028' and first['queue_index']=='62'
    members=[r for r in queue if r['core_overlap_group']=='C028'];ctx=[r for r in contexts if r['candidate_id'] in {m['candidate_id'] for m in members}];assert len(members)==len(ctx)==1 and ctx[0]['candidate_id']=='V2E2-0260'
    checksfile=ROOT/'work_harps_20261101/v2/extension02/epoch_followup/INPUT_CHECKS.json';epochs=[r for r in read(checksfile) if r['target']=='HD126093'];assert len(epochs)==6
    cbnext=float(ctx[0]['center_bary_air_angstrom']);nextdp=members[0]['dp_id'];nextberv=next(r['berv_km_s'] for r in epochs if r['dp_id']==nextdp)
    rawdir=ROOT/'work_harps_20261101/v2/extension02/raw_followup_batch04';rawmap=read(rawdir/'NATIVE_MAPPING.json');nextmapping=[r for r in rawmap['orders'] if r['review_id']=='V2E2-0260']
    nextmeta={'schema':'HARPS_C020_NEXT_UNFINISHED_ROUTE_METADATA_V1','status':'METADATA_HANDOFF_NOT_EXECUTED','selected_before_current_observed_values':True,'selection':'After C020 all C001–C023 exact routes are complete. Skip the ten exact previously completed baseline diagnostics; the first unfinished route is C028 row62 on a different star.','core_overlap_group':'C028','resolution_groups':['R029'],'target':'HD126093','events':['V2E2-0260'],'queue_rows':members,'existing_context':ctx,'existing_cohort_epochs':[{k:r[k] for k in ['dp_id','date_obs','mjd_obs','berv_km_s','sha256']} for r in epochs],'existing_cohort_epoch_count':6,'center_bary_air_angstrom':cbnext,'own_discovery_dp_id':nextdp,'own_discovery_berv_km_s':nextberv,'proposed_topocentric_anchor_air_angstrom':cbnext/(1+nextberv/p['c_km_s']),'berv_span_km_s':max(r['berv_km_s'] for r in epochs)-min(r['berv_km_s'] for r in epochs),'historical_mapping_stages':nextmapping,'raw_source_directory':str(rawdir.relative_to(ROOT)),'completed_route_skip_proof':str((PHASE/'scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json').relative_to(ROOT)),'new_queries':0,'new_array_reads':False,'new_diagnostic_frozen':False,'labels_unchanged':True,'requirements':'Different target HD126093, six April–July2025 observations and own April27 discovery. Preserve exact original3864.5550000000003Å center. Do not transfer HD114783 seven-epoch counts,May reference,order19 scope,59.073km/s span or any quality outcome. Restore own batch04 raw/native evidence and freshly scan72headers before a separate fixed source-only/synthetic freeze. Original0260 epoch/raw evidence is already exposed; no blind validation or added observing time.','source_hashes':{str((queuebase/n).relative_to(ROOT)):sha(queuebase/n) for n in ['ACTION_QUEUE.csv','EVENT_CONTEXT.csv','CORE_OVERLAP_GROUPS.csv']}}
    for name in ['NATIVE_MAPPING.json','PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','REVIEW_COMPARISON.json','ADOPTED_DISPOSITIONS.csv']:nextmeta['source_hashes'][str((rawdir/name).relative_to(ROOT))]=sha(rawdir/name)
    nextmeta['source_hashes'][str(checksfile.relative_to(ROOT))]=sha(checksfile)
    write(PHASE/'scientific_review/NEXT_GROUP_METADATA.json',nextmeta)
    paths+=[HERE/n for n in ['compare_group.py','plot_group.py','prepare_plan.py','synthetic_preflight.py']]+[PHASE/n for n in ['BASELINE_VERIFICATION.json','inputs/restore_inputs.py','inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','input_audit/audit_inputs.py','input_audit/INPUT_AUDIT.json','independent_audit/independent_math.py','independent_audit/audit_prospective.py','independent_audit/audit_actual.py','scientific_review/NEXT_GROUP_METADATA.json','scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json']]+[OLD/'NEXT_ACTION.json',OLD/'analysis/compare_group.py',OLD/'analysis/PLAN.json']
    p['source_hashes']={str(f.relative_to(ROOT)):sha(f) for f in paths};p['source_hashes'].update(inv['source_hashes']);p['source_hashes'].update(nextmeta['source_hashes']);p['source_hashes'].update({r['path']:r['sha256'] for r in inv['files']})
    write(HERE/'PLAN.json',p);print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'source_bindings':len(p['source_hashes']),'slots':p['slots'],'completed_baseline_rows_skipped':len(skipped),'next_group':'C028','next_target':'HD126093','next_epochs':len(epochs),'C021_coordinate_overlap':unions},indent=2))

if __name__=='__main__':main()
