"""Prepare fixed C017 metadata and the next original-queue handoff, before flux."""
from pathlib import Path
import copy, csv, datetime, hashlib, json
HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OLD=ROOT/'work_harps_20261103_c022_context'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    inv=read(PHASE/'inputs/INPUT_INVENTORY.json')
    handoff=read(OLD/'NEXT_ACTION.json')
    base=read(ROOT/'work_harps_20261103_c015_context/analysis/PLAN.json')
    cb=3868.175; berv=26.6810328154809; dp='ADP.2022-02-06T01:07:28.382'; ct=cb/(1+berv/299792.458)
    assert inv['target']=='HD114783' and inv['events']=={'V2E2-0118':dp}
    assert [r['dp_id'] for r in inv['merged_spectra']]==[r['dp_id'] for r in handoff['existing_cohort_epochs']]
    assert inv['native_products'][0]['covering_orders']==[2,3] and len(inv['saved_native_raw_cutouts'])==2
    p={k:copy.deepcopy(base[k]) for k in ['c_km_s','frames','grid','normalization','comparisons','release_contract']}
    p.update(schema='HARPS_C017_INDIVIDUAL_PROFILE_CONTEXT_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='METHOD_FROZEN_BEFORE_ARRAY_VALUES',target='HD114783',scope='Original queue row 37, singleton C017/R018/V2E2-0118. Seven already exposed January2022–July2023 target epochs, one own February5 discovery reference, both native orders and their original raw containers. Post-detection descriptive context; no new observing time or independent validation.',events=inv['events'],merged_dp_ids=[r['dp_id'] for r in inv['merged_spectra']],discovery_dp_ids=[dp],inventory_path=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(ROOT)),group_center_bary_air_angstrom=cb,accepted_event_centers_bary_air_angstrom=[cb],anchor_dp_id=dp,anchor_berv_km_s=berv)
    p['frames']['topocentric']=f'One fixed own February5 anchor {ct!r} air Angstrom, exact original center/(1+BERVdiscovery/c). Query (anchor+x)*(1+BERVepoch/c); never recenter or fit a shift.'
    p['grid']['core']='51 fixed centers, abs(x)<=0.25; exact original [3867.925,3868.425] air Angstrom.'
    p['grid']['broad_pattern']='550 fixed surrounding centers, 0.25<abs(x)<=3; original context [3865.175,3871.175] air Angstrom.'
    p['normalization']['structured_neighbor']='Keep all signed samples in fixed 1.5–3 Angstrom flanks without masks or a line-free assumption. This C017 window shares pixels with C018; neither central core intersects the other reference flanks.'
    p['comparisons']['merged']='7 own-target epochs ×1 own February discovery ×2 frames ×2 regions =28 rows; four explicitly marked identical-product self rows.'
    p['comparisons']['native']='2 covering orders ×2 frames ×2 regions =8 same-exposure native-to-merged rows; shared extraction, not independent observations or physical flux ratios.'
    p['comparisons']['self_and_dependency_flags']='One fixed reference, six other epochs; six distinct nonself observation relationships per frame/region, zero reciprocal-reference duplicates. All seven observations were used in earlier target analyses.'
    p['slots']={'merged_profiles':14,'native_profiles':4,'all_profiles':18,'merged_comparisons':28,'native_comparisons':8,'all_comparisons':36,'identical_product_self_comparisons':4,'saved_raw_order_panels':2,'structurally_excluded_native_order_pairs':0,'expected_bounded_input_windows':9,'distinct_discovery_products':1,'discovery_records':1}
    p['historical_review_disagreement']=handoff['historical_review_disagreement']
    p['historical_mapping_stages']=inv['mapping_records']
    p['wavelength_dependency']=handoff['wavelength_dependency']
    p['skipped_completed_routes']=handoff['skipped_completed_routes']
    p['completed_normalization_context']=handoff['completed_normalization_context']
    p['included_native_order_pairs']=[{'dp_id':dp,'order':o} for o in [2,3]]
    p['excluded_native_order_pairs']=[]
    p['excluded_native_order_evidence']=inv['excluded_native_orders']
    p['native_order_coverage']=inv['native_order_coverage']
    p['native_fixed_frame_header_geometry']=[{'dp_id':dp,'order':o,'fixed_frame_header_geometry':inv['native_products'][0]['orders'][str(o)]['fixed_frame_header_geometry']} for o in [2,3]]
    p['preserved_event_raw_pairs']=[{'event':r['event'],'dp_id':dp,'order':r['order']} for r in inv['saved_native_raw_cutouts']]
    p['event_markers']=[{'event':'V2E2-0118','resolution_group':'R018','center_bary_air_angstrom':cb,'barycentric_offset_angstrom':0.,'discovery_topocentric_offset_angstrom':0.,'color':'#b8292f'}]
    p['release_contract']['schema']='HARPS_C017_GROUP_RELEASE_V1'
    p['plot_script_sha256']=sha(HERE/'plot_group.py')
    p['plot_rules']='Four fixed figures: seven-epoch broad and core profiles in both frames with shared same-quantity y ranges; both native orders; both original full raw/excess panels. Every finite value is retained with 5% margin, missing/invalid/low-reference outcomes labelled. No alternate crop, contrast, mask, fit, background or subtraction.'
    p['bounded_arrays']='Nine pre-interpolation windows: source indices, original/barycentric wavelengths, signed flux and ERR; preserve full-source median spacing and source identity. Save all 18 derived profiles and two original byte-exact NPZs. No prior pipeline replay.'
    p['headers']='All seven merged identities, air wavelength/ADU convention, dates/BERV/progenitors and single-exposure tables; native72×4096 plus all72 wavelength headers, both selected orders and their independent geometric support. Header support is distinct from measured finite flux and reference quality.'
    p['limitations']=[
        'One unresolved event and seven reused observations; no new observing time, untouched-data validation, calibrated origin discrimination or physical-origin assignment.',
        'Exact original 3868.175 air-Angstrom center and fixed original core retained; own February5 discovery BERV 26.6810328154809 km/s and anchor3867.830769460069. No peak, width, lag, stellarRV, drift, continuum, background or masks are fitted.',
        'C017 shares source pixels with C018 over4.8412500000004 Angstrom. Both central cores were already exposed in each other surrounding contexts; neither core intersects the other fixed reference flanks. Other same-target windows C019/C021/C022 are disjoint but share observations.',
        'Seven January2022–July2023 epochs span59.073251754930496 km/s in BERV. Fixed topocentric windows may include neighboring structure when a predicted coherent center leaves the core; geometry is not a calibrated origin test.',
        'Order2 retains globaltrue/original-localfalse/original-baselinefalse/latertrue; order3 retains all four true. Later support does not repair original failures; no registration or mapping statistic is newly computed.',
        'Header geometry does not establish finite flux, valid positive reference, absence of low flags or adequate common support. Preserve every partial, missing, nonpositive, low or blocked slot.',
        'Original primary/secondary/adopted U/U/U and exact original raw containers remain; no new pixel statistic, subtraction, classification or origin claim.',
        'Native BUNIT is unspecified; merged spectra are uncalibrated ADU. Same-exposure extraction agreement is dependent, not another observation or a physical flux ratio.',
        'Signed pooled flanks retain all structure and are not established line-free continua. ERR and first-difference proxies do not establish formal significance, sensitivity, false-alarm probability, linewidth or a qualified survey null.',
        'All completed groups,35mapping diagnoses and C013/C014 normalization routes remain closed. Rubin stays a limited feasibility study with minimum50 unmet.',
        'Separate scalar numerical implementations are run by the same assistant; no independent human or separate-agent review is claimed.'
    ]
    basequeue=ROOT/'work_harps_20261101/v2/extension02/unresolved_context_20261102'
    queue=list(csv.DictReader((basequeue/'ACTION_QUEUE.csv').open()))
    completed={f'C{i:03d}' for i in range(1,20)}|{'C021','C022'}
    remaining=[r for r in queue if r['core_overlap_group'] not in completed]
    first=min(remaining,key=lambda r:int(r['queue_index']))
    assert first['core_overlap_group']=='C023' and first['queue_index']=='41'
    members=[r for r in queue if r['core_overlap_group']=='C023']
    context=list(csv.DictReader((basequeue/'EVENT_CONTEXT.csv').open()))
    rows=[r for r in context if r['candidate_id'] in {r['candidate_id'] for r in members}]
    assert len(rows)==len(members)==1 and rows[0]['candidate_id']=='V2E2-0122'
    nextmeta={'schema':'HARPS_C017_NEXT_FIXED_QUEUE_METADATA_V1','status':'METADATA_HANDOFF_NOT_EXECUTED','selected_before_current_observed_values':True,'selection':'First unfinished original route after completion of C017; C023 row41 precedes C020 row53. Completed C013/C014 normalization routes remain skipped.','core_overlap_group':'C023','target':'HD114783','events':['V2E2-0122'],'queue_rows':members,'existing_context':rows,'existing_cohort_epochs':handoff['existing_cohort_epochs'],'center_bary_air_angstrom':5944.965,'own_discovery_dp_id':dp,'own_discovery_berv_km_s':berv,'proposed_topocentric_anchor_air_angstrom':5944.965/(1+berv/299792.458),'new_queries':0,'new_array_reads':False,'new_diagnostic_frozen':False,'labels_unchanged':True,'requirements':'Restore own original raw/native evidence; freshly scan72orders for exact5944.965 center and fixed±3context. Preserve original mapping/review stages, fixed numerical helpers and all quality outcomes. Freeze separately before observed C023 values. Spectral window is disjoint from C017/C018/C019/C021/C022; same seven observations are dependent reused data.','source_hashes':{str((basequeue/n).relative_to(ROOT)):sha(basequeue/n) for n in ['ACTION_QUEUE.csv','EVENT_CONTEXT.csv','CORE_OVERLAP_GROUPS.csv']}}
    write(PHASE/'scientific_review/NEXT_GROUP_METADATA.json',nextmeta)
    paths=[HERE/n for n in ['compare_group.py','plot_group.py','prepare_plan.py','synthetic_preflight.py']]+[PHASE/n for n in ['BASELINE_VERIFICATION.json','inputs/restore_inputs.py','inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','input_audit/audit_inputs.py','input_audit/INPUT_AUDIT.json','independent_audit/independent_math.py','independent_audit/audit_prospective.py','independent_audit/audit_actual.py','scientific_review/NEXT_GROUP_METADATA.json']]+[OLD/'NEXT_ACTION.json',OLD/'scientific_review/NEXT_STEP.md',ROOT/'work_harps_20261103_c015_context/analysis/compare_group.py']
    p['source_hashes']={str(x.relative_to(ROOT)):sha(x) for x in paths}
    p['source_hashes'].update(inv['source_hashes'])
    p['source_hashes'].update(nextmeta['source_hashes'])
    p['source_hashes'].update({r['path']:r['sha256'] for r in inv['files']})
    write(HERE/'PLAN.json',p)
    print(json.dumps({'plan_sha256':sha(HERE/'PLAN.json'),'source_bindings':len(p['source_hashes']),'slots':p['slots'],'next_group':'C023'},indent=2))

if __name__=='__main__': main()
