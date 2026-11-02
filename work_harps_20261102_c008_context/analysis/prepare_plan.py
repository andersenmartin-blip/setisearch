#!/usr/bin/env python3
"""Assemble C008's prospective plan from exact metadata, not observed arrays."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE = HERE.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
old = REPO / 'work_harps_20261102_c002_context'
p = read(old / 'analysis/PLAN.json')
inv = read(PHASE / 'inputs/INPUT_INVENTORY.json')
p['schema'] = 'HARPS_C008_INDIVIDUAL_PROFILE_CONTEXT_V1'
p['created_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
p['scope'] = ('Singleton C008 / R009 record V2E2-0047 on HD106515A at 5182.005 Angstrom, '
    'chosen by original queue row 17. Retain all seven existing cohort epochs and the one '
    'fixed March 2023 discovery reference. The bounded wavelength window is disjoint from '
    'completed C001–C007 contexts, but original epoch/raw evidence and the same seven observing '
    'products already exist. This is not blind, untouched or independent observing evidence.')
p['events'] = inv['events']
p['merged_dp_ids'] = [r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids'] = list(dict.fromkeys(inv['events'].values()))
p['inventory_path'] = str((PHASE / 'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom'] = 5182.005
p['accepted_event_centers_bary_air_angstrom'] = [5182.005]
p['anchor_dp_id'] = 'ADP.2023-03-23T01:02:04.831'
p['anchor_berv_km_s'] = 3.26509772194068
p['frames']['topocentric'] = ('One fixed ct = cb/(1+BERVdiscovery/c), anchored to V2E2-0047 '
    'observed on 2023-03-22 with BERV 3.26509772194068 km/s. Query barycentric wavelength '
    '(ct+x)*(1+BERVepoch/c), equivalent to native topocentric wavelength ct+x. No inherited '
    'May 2022, March 2022 or January anchor and no recentering. Other features may leave the core.')
p['grid']['core'] = ('abs(x)<=0.25: 51 sampled centers [-0.25,+0.25]. The original core is '
                    '5181.755–5182.255 Angstrom; it is not a fitted linewidth.')
p['grid']['broad_pattern'] = '0.25<abs(x)<=3: 550 sampled centers.'
p['normalization']['structured_neighbor'] = ('Use the complete fixed flanks without masks or '
    'an assumed line-free region. This wavelength window is separate from C001–C007 bounded '
    'windows, but previous event/epoch/raw evidence exists. Any surrounding structure remains '
    'in the pooled median. Fixed reference levels are not fitted or established line-free continua.')
p['comparisons']['merged'] = ('7 epochs × 1 fixed discovery reference × 2 frames × 2 regions = '
                            '28 records, including 4 identical-product self-comparisons.')
p['comparisons']['native'] = ('1 discovery covering order × 2 frames × 2 regions = 4 '
    'same-exposure native-to-merged records. Shared extraction is not independent confirmation '
    'or a physical flux ratio. Keep invalid references or insufficient support explicit.')
p['comparisons']['minimum_common_core'] = 41
p['comparisons']['minimum_common_broad'] = 440
p['comparisons']['self_and_dependency_flags'] = ('same_exposure and identical_product_self_pair '
    'flags are explicit. Retain the one fixed March 2023 reference and all seven reused epochs. '
    'A distinct bounded wavelength region and same-exposure native extraction do not supply '
    'independent observations or detections.')
p['slots'] = {'merged_profiles': 14, 'native_profiles': 2, 'all_profiles': 16,
    'merged_comparisons': 28, 'native_comparisons': 4, 'all_comparisons': 32,
    'identical_product_self_comparisons': 4, 'saved_raw_order_panels': 1,
    'structurally_excluded_native_order_pairs': 0, 'expected_bounded_input_windows': 8,
    'distinct_discovery_products': 1, 'discovery_records': 1}
p['bounded_arrays'] = ('Save eight pre-interpolation source windows with exact indices, '
    'original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native '
    'errors), source hashes, BERV and full-source spacing. Read only the available union required '
    'by both fixed-frame windows plus brackets. Full merged coordinates locate slices; native '
    'coordinates derive from headers. No extrapolation or new original-pipeline run.')
p['headers'] = ('Check all seven merged headers and the discovery native header before new '
    'flux access: exact identity/hash, recorded metadata, numeric BERV, merged BARYCENT air '
    'Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native 72×4096 shape and '
    'unchanged degree/order 43 coefficients. Failed slots remain explicit; coordinate '
    'coverage is distinct from flux quality, reference validity and mapping reliability.')
p['preserved_raw_context'] = ('Copy the exact historical V2E2-0047 order 43 raw/native NPZ. '
    'Display original raw_cutout/raw_excess after release using separate full scales. Preserve '
    'all primary, secondary, adopted and distinct historical mapping stages. No new registration, '
    'subtraction, detector model or independent pixel claim.')
p['release_contract']['schema'] = 'HARPS_C008_GROUP_RELEASE_V1'
p['plot_script_sha256'] = sha(HERE / 'plot_group.py')
p['plot_rules'] = ('Four figures: all seven merged broad/core profiles with signed and normalized '
    'flux in both frames; the native order 43 context; the historical raw/excess pair. One '
    '0047/R009 catalog/discovery marker, not a fitted peak. Keep any raw-only annotations, low '
    'reference outcomes and partial support; no smoothing, clipping or favorable selection. '
    'Matching merged-frame and native raw-frame scales retain every finite value with '
    '5 percent margins. Raw panels use separate full extrema.')
p['limitations'] = [
    'Post-detection context of one U record and seven reused original-cohort exposures; no new observing time, independent detection or archive-wide completeness. V2E2-0047 remains U.',
    'The fixed C008 wavelength window 5179.005–5185.005 Angstrom is disjoint from completed C001–C007 bounded contexts. Original event/epoch/raw evidence and all seven observations were already used. Distinct wavelength context does not imply blind, untouched or independent evidence.',
    'The sole fixed discovery reference is observed on 2023-03-22 with BERV 3.26509772194068 km/s. Do not inherit any earlier anchor. The seven-epoch BERV span 59.6098131157401 km/s is coordinate separation, not calibrated origin discrimination.',
    'The fixed topocentric core is not recentered on other epochs. A coherent center can leave the original ±0.25 Angstrom core, causing comparisons to describe neighboring structure in the anchor window.',
    'All fixed flank structure remains in the pooled medians. These are reference levels, not line-free continua. No fitted widths, centers, lags, RV, drift, background, masks or moved flanks.',
    'Fresh 72-order header scan identifies order 43 alone as covering the original feature center. Both ±3 Angstrom windows and flanks lie inside its header endpoints, but geometric coverage is not a guarantee of finite flux, positive references, false low flags or usable comparisons.',
    'Historical global/local/baseline/five-window mapping stages are true for order 43 and are retained distinctly. They are existing diagnostics, not new mapping or origin validation.',
    'Native BUNIT absent; native extracted units unspecified. Merged ADU and native scales differ; same-exposure extraction agreement is not independent confirmation or a physical flux ratio.',
    'ERR coverage and descriptive first-difference proxies do not establish a formal uncertainty model, significance, physical linewidth, false-alarm rate, sensitivity or qualified null.',
    'All prior extraction, mapping, raw panels, labels, epoch outputs and completed contexts remain unchanged.'
]
p['source_hashes'] = {}
paths = [HERE / n for n in ['compare_group.py', 'plot_group.py', 'README.md',
                            'prepare_plan.py', 'synthetic_preflight.py']]
paths += [PHASE / n for n in ['inputs/INPUT_INVENTORY.json', 'inputs/RESTORE_RECEIPT.json',
    'inputs/restore_inputs.py', 'BASELINE_VERIFICATION.json', 'input_audit/INPUT_AUDIT.json',
    'input_audit/audit_inputs.py']]
paths += [old / n for n in ['NEXT_ACTION.json', 'scientific_review/NEXT_STEP.md',
                            'analysis/compare_group.py', 'analysis/PLAN.json', 'analysis/plot_group.py']]
prior_windows = []
for number in range(1, 8):
    f = REPO / f'work_harps_20261102_c{number:03d}_context/analysis/PLAN.json'
    q = read(f)
    center = q['group_center_bary_air_angstrom']
    window = [center + x for x in q['grid']['window_angstrom']]
    assert window[1] < 5179.005 or window[0] > 5185.005
    prior_windows.append({'group': f'C{number:03d}', 'window_bary_air_angstrom': window,
                          'disjoint_from_C008': True, 'plan_path': str(f.relative_to(REPO))})
    paths.append(f)
p['prior_bounded_window_geometry'] = prior_windows
for f in paths:
    p['source_hashes'][str(f.relative_to(REPO))] = sha(f)
for f in inv['files']:
    p['source_hashes'][f['path']] = f['sha256']
p['source_hashes'].update(inv['source_hashes'])
p['included_native_order_pairs'] = [{'dp_id': r['dp_id'], 'order': o}
    for r in inv['native_products'] for o in r['covering_orders']]
p['excluded_native_order_pairs'] = []
p['native_order_coverage'] = inv['native_order_coverage']
p['excluded_native_order_evidence'] = inv['excluded_native_orders']
p['native_order_selection'] = ('Historical order 43 alone is retained after the fresh all-72-order '
    'header check against the original topocentric feature center. No structural exclusions. '
    'Both full frame windows fit inside this order; flux quality and normalization remain '
    'unmeasured until release, separately from historical mapping stages.')
p['native_fixed_frame_header_geometry'] = [{'dp_id': r['dp_id'], 'order': order,
    'fixed_frame_header_geometry': r['orders'][str(order)]['fixed_frame_header_geometry']}
    for r in inv['native_products'] for order in r['covering_orders']]
p['preserved_event_raw_pairs'] = [{'event': r['event'], 'dp_id': inv['events'][r['event']],
    'order': r['order']} for r in inv['saved_native_raw_cutouts']]
B = {r['dp_id']: r['berv_km_s'] for r in inv['merged_spectra']}
cb = p['group_center_bary_air_angstrom']
c = p['c_km_s']
ct = cb / (1 + p['anchor_berv_km_s'] / c)
p['event_markers'] = [{'event': event, 'resolution_group': 'R009',
    'center_bary_air_angstrom': cb, 'barycentric_offset_angstrom': 0.,
    'discovery_topocentric_offset_angstrom': cb / (1 + B[dp] / c) - ct,
    'color': '#b8292f'} for event, dp in inv['events'].items()]
assert p['events'] == {'V2E2-0047': 'ADP.2023-03-23T01:02:04.831'}
assert p['anchor_dp_id'] == p['discovery_dp_ids'][0] and B[p['anchor_dp_id']] == p['anchor_berv_km_s']
assert p['included_native_order_pairs'] == [{'dp_id': p['anchor_dp_id'], 'order': 43}]
assert len(p['preserved_event_raw_pairs']) == 1 and not p['excluded_native_order_evidence']
(HERE / 'PLAN.json').write_text(json.dumps(p, indent=2, allow_nan=False) + '\n')
print(json.dumps({'plan_sha256': sha(HERE / 'PLAN.json'), 'sources': len(p['source_hashes']),
                 'slots': p['slots'], 'anchor_berv_km_s': p['anchor_berv_km_s']}, indent=2))
