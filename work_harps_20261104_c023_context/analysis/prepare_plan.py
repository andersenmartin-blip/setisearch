"""Freeze C023 singleton metadata, exact sources and next queue route before flux."""
from pathlib import Path
import copy,csv,datetime,hashlib,json
HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OLD=ROOT/'work_harps_20261104_c017_context'
CB=5944.965
BERV=26.6810328154809
DP='ADP.2022-02-06T01:07:28.382'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    inv=read(PHASE/'inputs/INPUT_INVENTORY.json');handoff=read(OLD/'NEXT_ACTION.json')
    base=read(OLD/'analysis/PLAN.json');ct=CB/(1+BERV/299792.458)
    assert inv['events']=={'V2E2-0122':DP} and inv['target']=='HD114783'
    assert [r['dp_id'] for r in inv['merged_spectra']]==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
    assert inv['native_products'][0]['covering_orders']==[57] and len(inv['saved_native_raw_cutouts'])==1
    p={k:copy.deepcopy(base[k]) for k in ['c_km_s','frames','grid','normalization','comparisons','release_contract']}
    p.update(schema='HARPS_C023_INDIVIDUAL_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='METHOD_FROZEN_BEFORE_ARRAY_VALUES',target='HD114783',scope='Original queue row41, singleton C023/R024/V2E2-0122. Seven already exposed January2022–July2023 epochs, one own February5 discovery, sole covering native order57 and its original raw container. Preserve the previous asymmetric raw/flat-topped native ambiguity. No observing time or independent validation is added.',events=inv['events'],merged_dp_ids=[r['dp_id'] for r in inv['merged_spectra']],discovery_dp_ids=[DP],inventory_path=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(ROOT)),group_center_bary_air_angstrom=CB,accepted_event_centers_bary_air_angstrom=[CB],anchor_dp_id=DP,anchor_berv_km_s=BERV)
    p['frames']['topocentric']=f'Own February5 discovery fixes one exact anchor {ct!r} air Angstrom. Query (anchor+x)*(1+BERVepoch/c); no shift, width or recentering is fitted.'
    p['grid']['core']='51 fixed grid centers, abs(x)<=0.25, original [5944.715,5945.215] air Angstrom.'
    p['grid']['broad_pattern']='550 fixed surrounding grid centers, 0.25<abs(x)<=3, context [5941.965,5947.965] air Angstrom.'
    p['normalization']['structured_neighbor']='Retain every signed original sample in fixed 1.5–3Angstrom flanks without masks or line-free assumptions. C023 is spectrally disjoint from recent same-target blue/order19 contexts, but all seven observations and original0122 epoch/raw evidence are reused.'
    p['comparisons']['merged']='7 own-target epochs ×1 fixed February5 discovery ×2 frames ×2 regions =28 rows, including4 labelled identical-product self rows.'
    p['comparisons']['native']='1 covering native order ×2 frames ×2 regions =4 same-exposure native-to-merged rows; this is dependent extraction agreement, not another observation or a physical flux ratio.'
    p['comparisons']['self_and_dependency_flags']='One fixed reference, six other epochs and six distinct nonself observation relationships per frame/region. All seven target observations are already exposed. Four identical-product self rows contribute no recurrence evidence.'
    p['slots']={'merged_profiles':14,'native_profiles':2,'all_profiles':16,'merged_comparisons':28,'native_comparisons':4,'all_comparisons':32,'identical_product_self_comparisons':4,'saved_raw_order_panels':1,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':8,'distinct_discovery_products':1,'discovery_records':1}
    p['historical_review_records']=inv['historical_raw_review_records']
    p['historical_review_disagreement']={'primary_code':'U','secondary_code':'U','root_adopted_code':'U','current_code':'U','qualification':'Both original reviews retain asymmetric raw/native structure with possible charge/photon mixtures. No physical origin was confirmed; no blanket inheritance from C017 is allowed.'}
    p['historical_mapping_stages']=inv['mapping_records']
    p['skipped_completed_routes']=base['skipped_completed_routes']
    p['completed_normalization_context']=base['completed_normalization_context']
    p['included_native_order_pairs']=[{'dp_id':DP,'order':57}]
    p['excluded_native_order_pairs']=[];p['excluded_native_order_evidence']=inv['excluded_native_orders']
    p['native_order_coverage']=inv['native_order_coverage']
    p['native_fixed_frame_header_geometry']=[{'dp_id':DP,'order':57,'fixed_frame_header_geometry':inv['native_products'][0]['orders']['57']['fixed_frame_header_geometry']}]
    p['preserved_event_raw_pairs']=[{'event':'V2E2-0122','dp_id':DP,'order':57}]
    p['event_markers']=[{'event':'V2E2-0122','resolution_group':'R024','center_bary_air_angstrom':CB,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':0.,'color':'#b8292f'}]
    p['release_contract']['schema']='HARPS_C023_GROUP_RELEASE_V1'
    p['plot_script_sha256']=sha(HERE/'plot_group.py')
    p['plot_rules']='Four fixed figures: all seven merged broad/core profiles in both frames, own native order57 and the original full raw/excess pair. Shared same-quantity merged y limits; native raw y limits match across frames. All finite values plus5percent margin, separate full raw-image scales, no alternate crop, contrast, mask, smoothing, background or fitting.'
    p['bounded_arrays']='Eight pre-interpolation windows with exact source indices, original/barycentric wavelengths, signed flux and ERR. Retain full-source median spacing and immutable hashes; save sixteen derived profiles and one original byte-exact raw container. No old pipeline replay.'
    p['headers']='Verify own seven merged identities, air wavelength/ADU conventions, dates/BERV/progenitors and single-exposure tables. Freshly scan all72 native headers and sole order57 geometry before flux. Header geometry does not establish finite flux, reference positivity or support.'
    p['limitations']=[
        'One unresolved record and seven reused observations, with original0122 epoch/raw evidence already exposed. No new observing time, untouched-data validation, physical origin, laser qualification or calibrated survey null.',
        'Original center5944.965Å and core±0.25Å; fixed±3Å context and own February5 anchor5944.43595503388Å. No fitted center,width,lag,stellarRV,drift,continuum,background or mask.',
        'Fresh native all72-order headers determine sole order57 scope. Geometry does not establish finite flux, reference quality or common support; every invalid,missing,partial,nonpositive,low or blocked slot remains.',
        'All four historical order57 mapping stages are true. Mapping support and same-exposure extraction similarity do not resolve the asymmetric raw/native morphology or assign origin.',
        'Original primary/secondary/adopted U/U/U is retained for a flat-topped/asymmetric native enhancement and irregular multi-row raw excess, with a possible charge/photon mixture. No new pixel statistic, crop, subtraction or registration is introduced.',
        'Same seven January2022–July2023 observations span59.073251754930496km/s in BERV; fixed topocentric windows can sample neighboring structure when a predicted coherent center leaves the core. Frame agreement is descriptive, not calibrated origin discrimination.',
        'Native BUNIT remains unspecified and merged spectra use uncalibrated ADU. Signed pooled references retain all structure and are not established line-free continua. No physical native/merged flux ratio follows.',
        'ERR, first-difference proxies and low-reference flags do not calibrate formal significance, false-alarm probability, sensitivity or linewidth.',
        'Completed context,35mapping and C013/C014 normalization routes remain closed; Rubin stays limited feasibility with minimum50unmet.',
        'Separate scalar formulas and fresh processes are executed by the same assistant; no separate-agent or human review is claimed.'
    ]
    previous=[];paths=[]
    for dirname in ['work_harps_20261104_c017_context','work_harps_20261103_c018_context','work_harps_20261103_c019_context','work_harps_20261103_c021_context','work_harps_20261103_c022_context']:
        f=ROOT/dirname/'analysis/PLAN.json';q=read(f);center=q['group_center_bary_air_angstrom'];window=[center-3,center+3]
        disjoint=window[1]<CB-3 or window[0]>CB+3;assert disjoint
        previous.append({'path':str(f.relative_to(ROOT)),'target':'HD114783','window_air_angstrom':window,'spectrally_disjoint':True,'same_observing_products':True,'shared_bounded_source_pixels':False});paths.append(f)
    p['wavelength_dependency']={'prior_same_target_contexts':previous,'same_seven_observing_products':True,'original_0122_epoch_raw_evidence_already_exposed':True,'independent_new_observations':0}
    queuebase=ROOT/'work_harps_20261101/v2/extension02/unresolved_context_20261102'
    queue=list(csv.DictReader((queuebase/'ACTION_QUEUE.csv').open()));contexts=list(csv.DictReader((queuebase/'EVENT_CONTEXT.csv').open()))
    completed={f'C{i:03d}' for i in range(1,20)}|{'C021','C022','C023'}
    first=min([r for r in queue if r['core_overlap_group'] not in completed],key=lambda r:int(r['queue_index']))
    assert first['core_overlap_group']=='C020' and first['queue_index']=='53'
    members=[r for r in queue if r['core_overlap_group']=='C020'];ids={r['candidate_id'] for r in members};ctx=[r for r in contexts if r['candidate_id'] in ids]
    assert len(members)==len(ctx)==1 and ids=={'V2E2-0136'}
    cbnext=float(ctx[0]['center_bary_air_angstrom']);nextdp=members[0]['dp_id'];epochs=handoff['existing_cohort_epochs'];nextberv=next(r['berv_km_s'] for r in epochs if r['dp_id']==nextdp)
    nextmeta={'schema':'HARPS_C023_NEXT_FIXED_QUEUE_METADATA_V1','status':'METADATA_HANDOFF_NOT_EXECUTED','selected_before_current_observed_values':True,'selection':'First unfinished original route after C023 is C020 row53; numeric group order does not set queue order. Completed C013/C014 normalization routes remain skipped.','core_overlap_group':'C020','target':'HD114783','events':['V2E2-0136'],'queue_rows':members,'existing_context':ctx,'existing_cohort_epochs':epochs,'center_bary_air_angstrom':cbnext,'own_discovery_dp_id':nextdp,'own_discovery_berv_km_s':nextberv,'proposed_topocentric_anchor_air_angstrom':cbnext/(1+nextberv/299792.458),'new_queries':0,'new_array_reads':False,'new_diagnostic_frozen':False,'labels_unchanged':True,'requirements':'Use own May15 discovery and exact4303.13Å singleton center; freshly scan72own native headers and preserve source-specific raw/mapping/review history. Do not transfer C023 February reference,order57 scope or quality. Same seven observations and old0136 evidence are reused. Freeze a separate fixed analysis before new observed arithmetic.','source_hashes':{str((queuebase/n).relative_to(ROOT)):sha(queuebase/n) for n in ['ACTION_QUEUE.csv','EVENT_CONTEXT.csv','CORE_OVERLAP_GROUPS.csv']}}
    write(PHASE/'scientific_review/NEXT_GROUP_METADATA.json',nextmeta)
    paths += [HERE/n for n in ['compare_group.py','plot_group.py','prepare_plan.py','synthetic_preflight.py']]+[PHASE/n for n in ['BASELINE_VERIFICATION.json','inputs/restore_inputs.py','inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','input_audit/audit_inputs.py','input_audit/INPUT_AUDIT.json','independent_audit/independent_math.py','independent_audit/audit_prospective.py','independent_audit/audit_actual.py','scientific_review/NEXT_GROUP_METADATA.json']]+[OLD/'NEXT_ACTION.json',OLD/'analysis/compare_group.py',OLD/'analysis/PLAN.json']
    p['source_hashes']={str(f.relative_to(ROOT)):sha(f) for f in paths};p['source_hashes'].update(inv['source_hashes']);p['source_hashes'].update(nextmeta['source_hashes']);p['source_hashes'].update({r['path']:r['sha256'] for r in inv['files']})
    write(HERE/'PLAN.json',p)
    print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'source_bindings':len(p['source_hashes']),'slots':p['slots'],'next_group':'C020'},indent=2))

if __name__=='__main__':main()
