"""Freeze C028 on its own six HD126093 epochs before current array values."""
from pathlib import Path
import copy
import csv
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT / 'work_harps_20261104_c020_context'
ORIGINAL = ROOT / 'work_harps_20261101/v2/extension02'
CB = 3864.5550000000003
BERV = 5.77068898867443
DP = 'ADP.2025-04-28T01:01:15.579'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def csvrows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    inventory = read(PHASE / 'inputs/INPUT_INVENTORY.json')
    handoff = read(PREVIOUS / 'NEXT_ACTION.json')
    prior = read(PREVIOUS / 'analysis/PLAN.json')
    state = read(PREVIOUS / 'CONTINUATION_STATE.json')
    assert inventory['target'] == 'HD126093' and inventory['events'] == {'V2E2-0260': DP}
    assert [r['dp_id'] for r in inventory['merged_spectra']] == [r['dp_id'] for r in handoff['existing_cohort_epochs']]
    assert len(inventory['merged_spectra']) == 6
    assert inventory['native_products'][0]['covering_orders'] == [2,3]
    assert len(inventory['saved_native_raw_cutouts']) == 2
    for row in inventory['mapping_records']:
        assert [row[k] for k in ['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']] == [True,False,False,True]
    p = {key:copy.deepcopy(prior[key]) for key in ['c_km_s','frames','grid','normalization','comparisons','release_contract']}
    ct = CB / (1+BERV/p['c_km_s'])
    p.update(schema='HARPS_C028_INDIVIDUAL_PROFILE_CONTEXT_V1',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='METHOD_FROZEN_BEFORE_ARRAY_VALUES', target='HD126093',
        scope='Original queue row62, C028/R029/V2E2-0260 at its exact catalog center. Six existing April–July2025 observations, own April27 discovery, own native orders2/3 and two original raw containers. No HD114783 reference, epoch count, mapping quality or scope is transferred.',
        events=inventory['events'], merged_dp_ids=[r['dp_id'] for r in inventory['merged_spectra']],
        discovery_dp_ids=[DP], inventory_path=str((PHASE/'inputs/INPUT_INVENTORY.json').relative_to(ROOT)),
        group_center_bary_air_angstrom=CB, accepted_event_centers_bary_air_angstrom=[CB],
        anchor_dp_id=DP, anchor_berv_km_s=BERV)
    p['frames']['topocentric'] = f'Own April27 2025 discovery BERV fixes anchor {ct!r} air Angstrom. Query (anchor+x)*(1+BERVepoch/c), with no fitted shift or recentering.'
    p['grid']['core'] = f'51 fixed centers, abs(x)<=0.25; exact original [{CB-.25!r},{CB+.25!r}] air Angstrom.'
    p['grid']['broad_pattern'] = f'550 surrounding centers, 0.25<abs(x)<=3; context [{CB-3!r},{CB+3!r}] air Angstrom.'
    p['normalization']['structured_neighbor'] = 'Retain every signed source sample in fixed1.5–3Angstrom flanks. Next C029 at3866.125Angstrom lies within this positive flank and broad window; part of its original core is in the flank. The next negative flank also intersects this original core. Keep overlap without masks or a line-free assumption. Shared products/pixels are dependent, not independent confirmations.'
    p['comparisons']['merged'] = '6 existing own-target epochs ×1 own April27 reference ×2 frames ×2 regions =24 rows, including4 labelled identical-product self rows.'
    p['comparisons']['native'] = '2 own covering native orders ×2 frames ×2 regions =8 same-exposure native-to-merged rows; dependent extraction agreement, not another observation or physical flux ratio.'
    p['comparisons']['self_and_dependency_flags'] = 'One fixed discovery reference, five other observations and five nonself observation relationships per frame/region. Original0260 epoch/raw evidence is already exposed. Four self rows add no recurrence evidence. Shared native orders use the same exposure.'
    p['slots'] = dict(merged_profiles=12,native_profiles=4,all_profiles=16,
        merged_comparisons=24,native_comparisons=8,all_comparisons=32,
        identical_product_self_comparisons=4,saved_raw_order_panels=2,
        structurally_excluded_native_order_pairs=0,expected_bounded_input_windows=8,
        distinct_discovery_products=1,discovery_records=1)
    p['historical_review_records'] = inventory['historical_raw_review_records']
    p['historical_review_disagreement'] = dict(primary_code='U',secondary_code='U',root_adopted_code='U',current_code='U',qualification='Original broad native features and diffuse trace-centered multi-row excess in both orders remain U/U/U. Photon-compatible morphology is descriptive and does not assign origin or qualify a laser.')
    p['historical_mapping_stages'] = inventory['mapping_records']
    p['skipped_completed_routes'] = dict(completed_original_routes=state['completed_original_routes'],exact_baseline_event_ids=state['completed_exact_baseline_route_ids'],proof_path=state['completed_baseline_route_proof_path'],qualification='Skip only the exact completed diagnoses, with physical U unchanged. Four bounded zero-selection HD135204 records are not archive-wide absence. All mapping and separate0235 spatial/background diagnoses remain closed.')
    p['completed_normalization_context'] = prior['completed_normalization_context']
    p['included_native_order_pairs'] = [{'dp_id':DP,'order':o} for o in [2,3]]
    p['excluded_native_order_pairs'] = []
    p['excluded_native_order_evidence'] = inventory['excluded_native_orders']
    p['native_order_coverage'] = inventory['native_order_coverage']
    p['native_fixed_frame_header_geometry'] = [{'dp_id':DP,'order':o,'fixed_frame_header_geometry':inventory['native_products'][0]['orders'][str(o)]['fixed_frame_header_geometry']} for o in [2,3]]
    p['preserved_event_raw_pairs'] = [{'event':'V2E2-0260','dp_id':DP,'order':o} for o in [2,3]]
    p['event_markers'] = [dict(event='V2E2-0260',resolution_group='R029',center_bary_air_angstrom=CB,barycentric_offset_angstrom=0.,discovery_topocentric_offset_angstrom=0.,color='#b8292f')]
    p['release_contract']['schema'] = 'HARPS_C028_GROUP_RELEASE_V1'
    p['plot_script_sha256'] = sha(HERE/'plot_group.py')
    p['plot_rules'] = 'Four fixed PNGs: all six merged broad/core curves in both frames; both own native orders; both full original raw/excess pairs. Same-quantity merged panels share y scales using all finite values plus5percent; native raw scales match across frames per order; original raw pairs use separate full scales. No smoothing, fitted variant, moved mask, contrast variant, crop, subtraction or registration.'
    p['bounded_arrays'] = 'Eight pre-interpolation windows retain original indices, signed flux, ERR, both wavelength representations and full-source spacing. Preserve sixteen frame profiles and two byte-exact original raw containers. No original epoch/raw pipeline is rerun.'
    p['headers'] = 'Verify all six own-target merged identities, units, dates, BERV and progenitors, plus the own April discovery native product. Fresh all72-order scan selects own orders2/3. Header geometry is separate from measured finite support and reference validity.'
    p['limitations'] = [
        'One unresolved event, six existing April–July2025 observations and previously exposed0260 epoch/raw evidence. No added observing time, blind or untouched-data validation, physical-origin assignment, qualified laser or calibrated survey null.',
        'Keep exact original3864.5550000000003air-Angstrom center and own April27 discovery BERV5.77068898867443km/s, fixed±0.25core and±3context. No fitted center,width,lag,stellarRV,drift,continuum,background or mask.',
        'Fresh all72native headers select own orders2/3. Header support does not establish finite values, valid positive references or adequate common samples. All partial,invalid,nonpositive,low,missing and blocked slots remain explicit.',
        'Original orders2/3 have global support, local/baseline failures and later five-window support. These stages are preserved separately. Existing broader native/raw morphology remains U/U/U; extraction agreement does not resolve it.',
        'The six observations span29.26984563734743km/s in BERV. Predicted coherent centers can leave the fixed topocentric core, which can then sample neighboring structure. Frame statistics are descriptive, not calibrated origin tests.',
        'Structured source flanks are not established line-free continua. Next C029 and current C028 share broad windows, portions of core/reference regions, observing products and native lineage. No source-pixel independence or masked neighbor variant is claimed.',
        'Merged ADU is uncalibrated and native BUNIT remains unspecified. Separate signed pooled references do not define physical native/merged flux ratios. ERR, first-difference proxies and low flags do not calibrate significance,false-alarm probability,sensitivity or linewidth.',
        'All previous exact diagnoses remain closed with physical labels unchanged. No HD114783 seven-epoch count, May reference, order19 scope, 59.073km/s span or quality outcome is transferred.',
        'Separate scalar arithmetic and fresh processes are run by the same assistant; no independent human or separate-agent review. Rubin stays limited feasibility with minimum50unmet.'
    ]
    queuebase = ORIGINAL/'unresolved_context_20261102'
    queue = csvrows(queuebase/'ACTION_QUEUE.csv')
    contexts = csvrows(queuebase/'EVENT_CONTEXT.csv')
    members = [r for r in queue if r['core_overlap_group']=='C029']
    assert min(int(r['queue_index']) for r in members)==63
    ids = {r['candidate_id'] for r in members}
    assert ids == {'V2E2-0261','V2E2-0266','V2E2-0272'}
    context = [r for r in contexts if r['candidate_id'] in ids]
    assert {float(r['center_bary_air_angstrom']) for r in context} == {3866.125}
    rawdir = ORIGINAL/'raw_followup_batch04'
    mapping = [r for r in read(rawdir/'NATIVE_MAPPING.json')['orders'] if r['review_id'] in ids]
    histories = {}
    for label,name,key in [('primary','PRIMARY_VISUAL_REVIEW.json','events'),('secondary','SECONDARY_VISUAL_REVIEW.json','records'),('comparison','REVIEW_COMPARISON.json','events')]:
        histories[label] = [r for r in read(rawdir/name)[key] if r['review_id'] in ids]
    histories['adopted'] = [r for r in csvrows(rawdir/'ADOPTED_DISPOSITIONS.csv') if r['review_id'] in ids]
    assert all(len(records)==3 for records in histories.values())
    nextcenter = 3866.125
    nextmeta = dict(schema='HARPS_C028_NEXT_C029_METADATA_V1',status='METADATA_HANDOFF_NOT_EXECUTED',
        selected_before_current_observed_values=True,
        selection='After closing this C028 diagnostic, the first unfinished original-queue route is C029 starting at row63. All three member records and own discovery references remain; group order is not a likelihood ranking.',
        core_overlap_group='C029',resolution_groups=['R030'],target='HD126093',events=sorted(ids),
        queue_rows=members,existing_context=context,
        existing_cohort_epochs=handoff['existing_cohort_epochs'],existing_cohort_epoch_count=6,
        center_bary_air_angstrom=nextcenter,
        own_discovery_dp_ids=list(dict.fromkeys(r['dp_id'] for r in members)),
        proposed_anchor_dp_id=members[0]['dp_id'],proposed_anchor_berv_km_s=BERV,
        proposed_topocentric_anchor_air_angstrom=nextcenter/(1+BERV/p['c_km_s']),
        berv_span_km_s=handoff['berv_span_km_s'],historical_mapping_stages=mapping,
        historical_review_records=histories,raw_source_directory=str(rawdir.relative_to(ROOT)),
        new_queries=0,new_array_reads=False,new_diagnostic_frozen=False,labels_unchanged=True,
        current_context_dependency=dict(current_center=CB,next_center=nextcenter,
            current_barycentric_window=[CB-3,CB+3],next_barycentric_window=[nextcenter-3,nextcenter+3],
            nominal_window_overlap_angstrom=min(CB+3,nextcenter+3)-max(CB-3,nextcenter-3),
            next_catalog_center_in_current_positive_reference_flank=True,
            current_core_in_next_negative_flank='PARTIAL_INTERSECTION_ONLY',
            next_core_in_current_positive_flank='PARTIAL_INTERSECTION_ONLY',
            same_six_observations=True,source_pixel_independence_claim=False,
            current_bounded_input_index_path=str((PHASE/'analysis/results/BOUNDED_INPUT_INDEX.json').relative_to(ROOT))),
        requirements='Three original C029 records and three own discovery references on the same six HD126093 observations. Preserve0261 off-trace compact deposit/possible blend separately from its broader centered component and all per-order mapping stages. Restore own discovery products and raw containers; freshly scan all72headers per product and freeze separate fixed geometry, normalization, comparisons and figures. Current/next source pixels and flanks overlap; no independence or blind validation. Do not copy0260 mapping/finite-support outcomes to the other records.')
    sources = [queuebase/name for name in ['ACTION_QUEUE.csv','EVENT_CONTEXT.csv','CORE_OVERLAP_GROUPS.csv']]
    sources += [rawdir/name for name in ['NATIVE_MAPPING.json','PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','REVIEW_COMPARISON.json','ADOPTED_DISPOSITIONS.csv']]
    sources += [ORIGINAL/'epoch_followup/INPUT_CHECKS.json']
    nextmeta['source_hashes'] = {str(path.relative_to(ROOT)):sha(path) for path in sources}
    write(PHASE/'scientific_review/NEXT_GROUP_METADATA.json',nextmeta)
    p['wavelength_dependency'] = dict(same_six_existing_observations_reused=True,
        original_0260_epoch_raw_evidence_already_exposed=True,
        prior_C020_different_target=True,prior_C020_observing_products_shared=False,
        next_C029_dependency=nextmeta['current_context_dependency'],
        next_route_selected_before_current_values=True,source_pixel_independence_claim=False)
    sources += [HERE/name for name in ['compare_group.py','plot_group.py','prepare_plan.py','synthetic_preflight.py']]
    sources += [PHASE/name for name in ['BASELINE_VERIFICATION.json','inputs/restore_inputs.py','inputs/INPUT_INVENTORY.json','inputs/RESTORE_RECEIPT.json','input_audit/audit_inputs.py','input_audit/INPUT_AUDIT.json','independent_audit/independent_math.py','independent_audit/audit_prospective.py','independent_audit/audit_actual.py','scientific_review/NEXT_GROUP_METADATA.json']]
    sources += [PREVIOUS/name for name in ['NEXT_ACTION.json','CONTINUATION_STATE.json','GROUP_CLOSURE.json','analysis/PLAN.json','analysis/compare_group.py','analysis/results/OUTPUT_HASHES.json','scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json']]
    p['source_hashes'] = {str(path.relative_to(ROOT)):sha(path) for path in sources}
    p['source_hashes'].update(inventory['source_hashes'])
    p['source_hashes'].update({r['path']:r['sha256'] for r in inventory['files']})
    write(HERE/'PLAN.json',p)
    print(json.dumps(dict(plan_sha256=sha(HERE/'PLAN.json'),source_bindings=len(p['source_hashes']),slots=p['slots'],next_group='C029',next_records=sorted(ids),next_dependency=nextmeta['current_context_dependency']),indent=2))


if __name__ == '__main__':
    main()
