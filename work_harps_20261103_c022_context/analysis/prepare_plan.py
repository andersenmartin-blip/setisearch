#!/usr/bin/env python3
"""Freeze C022 metadata and source custody before observed-array access."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE = HERE.parent
OLD = REPO / 'work_harps_20261103_c021_context'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
handoff = read(OLD / 'NEXT_ACTION.json')
inv = read(PHASE / 'inputs/INPUT_INVENTORY.json')
p = read(OLD / 'analysis/PLAN.json')
CB = 4312.241249999999
ANCHOR = 'ADP.2022-01-22T01:09:14.958'
BERV = 29.658729150824
members = handoff['prospective_next_group_metadata']['members']
CENTERS = {r['candidate_id']: r['center_bary_air_angstrom'] for r in members}
included = [{'dp_id': r['dp_id'], 'order': o} for r in inv['native_products'] for o in r['covering_orders']]
native_count = len(included)
raw_count = len(inv['saved_native_raw_cutouts'])
reference_count = len(set(inv['events'].values()))
p.update(schema='HARPS_C022_JOINT_PROFILE_CONTEXT_V1',
         created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         status='METHOD_FROZEN_BEFORE_ARRAY_VALUES', target='HD114783')
p['scope'] = ('Joint C022/R023 retains all three original HD114783 members0117/0127/0131 at queue rows36/45/49. '
              'Same seven January2022-July2023 observations, with January21/May5 2022 andJanuary16 2023 fixed references. '
              'Exact catalog-extrema midpoint4312.241249999999Angstrom is not fitted. Preserve original floats/cores/markers, '
              'all failed original local/baseline stages and0131 staged reviews. C021 already exposed this core on the same '
              'source pixels; shared structured flanks, original evidence and completed follow-up add no blind,untouched,independent-data or observing-time claim.')
p['historical_review_disagreement'] = handoff['historical_review_disagreement']
p['historical_mapping_stages'] = inv['mapping_records']
p['completed_mapping_followup_dependency'] = handoff['completed_mapping_followup_dependency']
p['events'] = inv['events']
p['merged_dp_ids'] = [r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids'] = list(dict.fromkeys(inv['events'].values()))
p['inventory_path'] = str((PHASE / 'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom'] = CB
p['accepted_event_centers_bary_air_angstrom'] = list(dict.fromkeys(CENTERS.values()))
p['individual_event_centers_bary_air_angstrom'] = CENTERS
p['individual_event_cores_bary_air_angstrom'] = {e: [c-.25, c+.25] for e, c in CENTERS.items()}
p['common_core_member_relation'] = ('Fixed common midpoint +/-0.25Angstrom metric core[4311.991249999999,4312.491249999999], '
                                    '51centers,is not the union of original member cores. Preserve exact4312.245 and4312.237499999999 '
                                    'centers/cores and up-to0.00375Angstrom edge extensions without post-value expansion or whole-original-core containment/linewidth claim.')
p['anchor_dp_id'] = ANCHOR
p['anchor_berv_km_s'] = BERV
p['frames']['topocentric'] = ('One common ct=group_midpoint/(1+BERVanchor/c),from first queue0117 observed2022-01-21 '
                              'BERV29.658729150824km/s,giving4311.814678415948Angstrom. Query barycentric wavelength(ct+x)*(1+BERVepoch/c). '
                              'All three reference identities remain; coordinate anchor is not favorable-reference selection. '
                              'Each marker uses own exact center/discovery BERV,not a fitted peak or group midpoint.')
p['grid']['core'] = 'abs(x)<=0.25:51centers in fixed common[4311.991249999999,4312.491249999999]Angstrom core,distinct from original-core union or physical linewidth.'
p['grid']['broad_pattern'] = '0.25<abs(x)<=3:550surrounding centers in fixed common[4309.241249999999,4315.241249999999]Angstrom window.'
p['normalization']['structured_neighbor'] = ('Retain every fixed-flank signed source sample and spectral structure without masks or assumed line-free regions. '
    'C022 full core lies inside priorC021 positive reference flank,and priorC021 full core lies inside C022 negative reference flank. '
    'The same seven observations reuse3.585000000000946Angstrom of bounded source pixels. Medians remain descriptive reference levels; '
    'no new masks,moved flanks,fitted continua,independent-data claim or prior quality outcome transfer.')
p['comparisons']['merged'] = (f'7 epochs x{reference_count} fixed references x2frames x2regions ={28*reference_count} merged records,'
                              f'including{4*reference_count} self rows. Retain all three exact January21/May5/January16 references and reciprocal pairs.')
p['comparisons']['native'] = (f'{native_count} native discovery/order19 sources x2frames x2regions ={4*native_count} '
                              'own-same-exposure native-to-merged records; native profiles do not compare with all references,shared extraction is dependent.')
p['comparisons']['per_reference_nonself_accounting'] = ('Each reference has six other epochs;18 directed nonself rows per frame/region '
    'represent15 unordered exposure pairs and3 reciprocal reference duplicates over seven observations. February5 2022 andMarch22/May15/July1 2023 remain nonreferences,not dropped epochs.')
p['comparisons']['minimum_common_core'] = 41
p['comparisons']['minimum_common_broad'] = 440
p['comparisons']['self_and_dependency_flags'] = ('Retain exact source/reference identities,same_exposure and identical_product_self_pair flags; '
    'repeated references,reciprocal pairs,self rows and shared extraction remain dependent rather than added observations.')
p['slots'] = {'merged_profiles': 14, 'native_profiles': 2*native_count, 'all_profiles': 14+2*native_count,
              'merged_comparisons': 28*reference_count, 'native_comparisons': 4*native_count,
              'all_comparisons': 28*reference_count+4*native_count, 'identical_product_self_comparisons': 4*reference_count,
              'saved_raw_order_panels': raw_count, 'structurally_excluded_native_order_pairs': len(inv['excluded_native_orders']),
              'expected_bounded_input_windows': 7+native_count, 'distinct_discovery_products': reference_count,
              'discovery_records': len(inv['events'])}
p['bounded_arrays'] = (f'Save{7+native_count} pre-interpolation windows with exact indices,original-frame/barycentric coordinates,signed flux,ERR'
    '(NaN when native unavailable),source hashes,BERV and full-source spacing. Read only union required by both fixed frames plus brackets; '
    'no extrapolation or original-pipeline replay. Overlapping priorC021 source indices remain reused evidence.')
p['headers'] = ('Check all seven merged/three native headers before flux access:exact identities/hashes/metadata,numeric BERV,merged barycentric-air '
    'Angstrom/ADU unique WAVE/FLUX/ERR single-exposure tables,native72x4096 shape and fresh selected-order polynomial coefficients. '
    'Fresh all72-order scan in every discovery. Geometric support,finite flux,reference validity and historical mapping remain separate.')
p['preserved_raw_context'] = ('Copy all three exact ORIGINAL event/order19 NPZs,including0131 original smaller five-array container,not later wider replacements. '
    'Two batch03 originals0117/0127 retainU/U/U;0131 originallyI/M-normalized-I/baseline-I,then completed unchanged-coordinate separate reviewsU/U/currentU. '
    'Original local/baseline false for allthree;global/later support true. Older0131 baseline usesmapping_verified,batch03 explicitbaseline_mapping_verified; '
    'source-specific coordinates/provenance retained. Later support does not repair original failures. No transfer of C021 mixed mapping or0130/0129 '
    'histories,no replay,new crop,contrast,registration,subtraction,spatialmodel,pixelstatistic or origin assignment.')
p['release_contract']['schema'] = 'HARPS_C022_GROUP_RELEASE_V1'
p['plot_script_sha256'] = sha(HERE / 'plot_group.py')
p['plot_rules'] = ('Four complete figures:two merged broad/core views with seven epochs/three exact member markers;one native page and one originalraw page '
    'with three rows each. Bind source order and pagination. Preserve exact original floats/cores/coincident marker identities;out-of-core markers remain '
    'in broad view/legend/metadata. Retain any raw-only/low/invalid outcome and partial support. Same-quantity merged scales match across frames;native '
    'raw scales match per source. All finite values retain5percent margin;raw scales use full separate extrema. No smoothing,clipping,favorable selection or contrast variants.')
p['skipped_completed_routes'] = handoff['skipped_completed_routes']
p['completed_normalization_context'] = handoff['completed_normalization_context']
p['prior_C021_shared_structured_flank_dependency'] = handoff['wavelength_dependency']
p['joint_reference_dependence'] = handoff['joint_reference_dependence']
p['limitations'] = [
    'Three current U records and seven reused HD114783 observations add no observing time,independent detections,archive-wide completeness or origin assignment.',
    'Exact4312.245/4312.237499999999 centers and midpoint4312.241249999999 remain separate. Fixed common +/-0.25 core is not original-core union;edge differences up to0.00375Angstrom remain without fitted shifts or post-value expansion.',
    'Own first-queue January21 anchor4311.814678415948/BERV29.658729150824 is fixed. Same seven epochs span59.073251754930496km/s;displaced features/neighboring structure can enter/leave fixed core. Span is coordinate geometry,not calibrated origin discrimination.',
    'Three fixed references areJanuary21/May5 2022 andJanuary16 2023. Eighteen directed nonself rows per frame/region represent15 unordered pairs with3 reciprocal duplicates over seven observations,not independent added epochs. Shared extractions/self rows remain dependent.',
    'Fixed signed pooled flank medians retain all spectral structure,not established line-free continua. No fitted width,center,lag,stellarRV,drift,background,continuum,masks or moved flanks.',
    'Fresh all72-order scans in three native products establish covering orders and common geometry. No inherited C021 scope or reference-quality outcome. Every invalid/missing/nonpositive/low outcome retains slot/reason.',
    'All original global/later support true;all three original local/baseline stages false. Preserve explicit batch03 baseline fields versus0131 originalmapping_verified. Later support does not rewrite original failures.',
    'Two original batch03 review chainsU/U/U;0131 originallyprimaryI,secondaryMnormalizedI,adoptedbaselineI,then completed unchanged-coordinate laterU/U/currentU. Do not transfer0130/0129 histories or flatten original stages to blanketU.',
    'Preserve0131 exact original smaller container separately from completed later wider diagnosis. No replay of mapping/normalization,new registration,subtraction,detector model,pixelstatistic or origin classifier.',
    'Native extracted units unspecified when BUNIT absent,distinct from mergedADU. ERR support and first-difference/low-reference proxies do not establish formal uncertainty,significance,linewidth,false-alarm rate,sensitivity or qualified survey null.',
    'C022 and priorC021 share the same seven observations and3.585000000000946Angstrom of bounded spectral source pixels. Full C022 core is inside priorC021 positive reference flank;full C021 core is inside C022 negative reference flank. Current core already exposed in prior broad context;no blind,untouched or independent-validation claim. Complete original raw crops remain separate without inferred equality or independence.',
    'C018/C019 bounded blue windows are disjoint while observations/native lineage are reused. C006/C007 numeric overlap uses different target observations and shares no source pixels. Spectral disjointness does not establish independence of observations or whole raw crops.',
    'All prior classifications/results and completed mapping/normalization diagnoses remain immutable and are not replayed. Mapping-supported morphology/frame agreement cannot qualify a laser candidate.'
]
paths = [HERE / n for n in ['compare_group.py', 'plot_group.py', 'README.md', 'prepare_plan.py', 'synthetic_preflight.py']]
paths += [PHASE / n for n in ['inputs/INPUT_INVENTORY.json', 'inputs/README.md', 'inputs/RESTORE_RECEIPT.json', 'inputs/restore_inputs.py',
                              'BASELINE_VERIFICATION.json', 'input_audit/INPUT_AUDIT.json', 'input_audit/audit_inputs.py']]
paths += [OLD / n for n in ['NEXT_ACTION.json', 'scientific_review/NEXT_STEP.md', 'analysis/compare_group.py',
                            'analysis/PLAN.json', 'analysis/plot_group.py', 'inputs/INPUT_INVENTORY.json',
                            'analysis/results/BOUNDED_INPUT_INDEX.json']]
prior = []
for number in list(range(1, 13)) + [15, 16, 18, 19, 21]:
    f = REPO / (('work_harps_20261102_' if number <= 8 else 'work_harps_20261103_') + f'c{number:03d}_context/analysis/PLAN.json')
    q = read(f)
    center = q['group_center_bary_air_angstrom']
    window = [center+x for x in q['grid']['window_angstrom']]
    target = q.get('target', 'HD106515A')
    disjoint = window[1] < CB-3 or window[0] > CB+3
    shared = target == 'HD114783' and not disjoint
    if target == 'HD114783':
        assert shared is (number == 21)
    note = ('Same seven observations;direct reused spectral pixels and reciprocal whole-core-in-reference-flank dependence with C021.'
            if shared else 'Same target/observations but disjoint bounded spectral window;full raw-crop independence not asserted.'
            if target == 'HD114783' else 'Different target/observations;numeric overlap shares no source pixels.')
    prior.append({'group': f'C{number:03d}', 'target': target, 'window_bary_air_angstrom': window,
                  'numerically_disjoint_from_C022': disjoint, 'shared_source_pixels': shared,
                  'dependency_note': note, 'plan_path': str(f.relative_to(REPO))})
    paths.append(f)
p['prior_bounded_window_geometry'] = prior
for path in handoff['source_hashes']:
    if '/normalization_context_20261102/' in path or '/mapping_followup/' in path:
        paths.append(REPO / path)
p['source_hashes'] = {str(f.relative_to(REPO)): sha(f) for f in paths}
for f in inv['files']:
    p['source_hashes'][f['path']] = f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs'] = included
p['excluded_native_order_pairs'] = []
p['native_order_coverage'] = inv['native_order_coverage']
p['excluded_native_order_evidence'] = inv['excluded_native_orders']
p['native_order_selection'] = ('Fresh all-order scan at exact original event coordinates/BERV determines every covering order and common-frame geometry. '
    'Retain every covering order/exclusion;do not transfer prior quality/mapping outcomes. Fresh confirmed soleorder19 in allthree products.')
p['native_fixed_frame_header_geometry'] = [
    {'dp_id': r['dp_id'], 'order': o, 'fixed_frame_header_geometry': r['orders'][str(o)]['fixed_frame_header_geometry']}
    for r in inv['native_products'] for o in r['covering_orders']]
p['preserved_event_raw_pairs'] = [{'event': r['event'], 'dp_id': inv['events'][r['event']], 'order': r['order']}
                                  for r in inv['saved_native_raw_cutouts']]
p['plot_pagination'] = {'merged_figures': 2, 'native_rows_per_page': 4, 'native_pages': (native_count+3)//4,
                        'native_contexts': native_count, 'raw_rows_per_page': 4, 'raw_pages': (raw_count+3)//4,
                        'raw_contexts': raw_count, 'total_figures': 2+(native_count+3)//4+(raw_count+3)//4,
                        'native_source_order': included, 'raw_panel_order': p['preserved_event_raw_pairs']}
B = {r['dp_id']: r['berv_km_s'] for r in inv['merged_spectra']}
c = p['c_km_s']
ct = CB/(1+BERV/c)
colors = ['#b8292f', '#df7b20', '#8156a6']
p['event_markers'] = [{'event': e, 'resolution_group': 'R023', 'discovery_dp_id': dp,
                       'center_bary_air_angstrom': CENTERS[e], 'barycentric_offset_angstrom': CENTERS[e]-CB,
                       'discovery_topocentric_offset_angstrom': CENTERS[e]/(1+B[dp]/c)-ct, 'color': colors[i]}
                      for i, (e, dp) in enumerate(inv['events'].items())]
assert inv['target'] == 'HD114783' and list(p['events']) == list(CENTERS)
assert p['merged_dp_ids'] == [r['dp_id'] for r in handoff['existing_cohort_epochs']]
assert p['discovery_dp_ids'] == handoff['distinct_discovery_products']
assert p['anchor_dp_id'] == p['discovery_dp_ids'][0] and B[ANCHOR] == BERV
assert max(B.values())-min(B.values()) == handoff['berv_span_km_s'] == 59.073251754930496
assert p['discovery_dp_ids'] == ['ADP.2022-01-22T01:09:14.958', 'ADP.2022-05-06T01:04:00.123', 'ADP.2023-01-17T01:07:48.581']
assert included == [{'dp_id': dp, 'order': 19} for dp in p['discovery_dp_ids']]
assert raw_count == reference_count == 3 and not p['excluded_native_order_evidence']
assert all([r[k] for k in ['original_grid_mapping_usable', 'original_local_mapping_usable',
                          'original_baseline_mapping_verified', 'final_reference_mapping_supported']]
           == [True, False, False, True] for r in p['historical_mapping_stages'])
assert p['prior_C021_shared_structured_flank_dependency']['overlap_width_angstrom'] == 3.585000000000946
(HERE / 'PLAN.json').write_text(json.dumps(p, indent=2, allow_nan=False) + '\n')
print(json.dumps({'plan_sha256': sha(HERE / 'PLAN.json'), 'sources': len(p['source_hashes']),
                  'slots': p['slots'], 'anchor_air_angstrom': ct}, indent=2))
