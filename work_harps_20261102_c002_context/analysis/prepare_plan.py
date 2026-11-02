#!/usr/bin/env python3
"""Assemble C002's prospective plan from exact metadata, not flux values."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE = HERE.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
old = REPO / 'work_harps_20261102_c004_context'
p = read(old / 'analysis/PLAN.json')
inv = read(PHASE / 'inputs/INPUT_INVENTORY.json')
p['schema'] = 'HARPS_C002_INDIVIDUAL_PROFILE_CONTEXT_V1'
p['created_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
p['scope'] = ('Singleton C002 / R002 record V2E2-0033 on HD106515A at 3868.6025 Angstrom, '
              'chosen by original queue row 10. Retain all seven existing cohort epochs and the one '
              'fixed May 2022 discovery reference. Its original core was already visible in completed '
              'C003 surrounding context; the broader window overlaps C003 and C004. This is '
              'post-detection context, not blind or independent validation or new observing time.')
p['events'] = inv['events']
p['merged_dp_ids'] = [r['dp_id'] for r in inv['merged_spectra']]
p['discovery_dp_ids'] = list(dict.fromkeys(inv['events'].values()))
p['inventory_path'] = str((PHASE / 'inputs/INPUT_INVENTORY.json').relative_to(REPO))
p['group_center_bary_air_angstrom'] = 3868.6025
p['accepted_event_centers_bary_air_angstrom'] = [3868.6025]
p['anchor_dp_id'] = 'ADP.2022-05-08T01:01:37.876'
p['anchor_berv_km_s'] = -18.8907517532076
p['frames']['topocentric'] = ('One fixed ct = cb/(1+BERVdiscovery/c), anchored to V2E2-0033 '
    'observed on 2022-05-07 with BERV -18.8907517532076 km/s. Query barycentric wavelength '
    '(ct+x)*(1+BERVepoch/c), equivalent to native topocentric wavelength ct+x. No inherited '
    'March or January anchor and no recentering. Other features may leave the fixed core.')
p['grid']['core'] = ('abs(x)<=0.25: 51 sampled centers [-0.25,+0.25]. The original core is '
                    '3868.3525–3868.8525 Angstrom; it is not a fitted linewidth.')
p['grid']['broad_pattern'] = '0.25<abs(x)<=3: 550 sampled centers.'
p['grid']['interpolation'] = ('Linear without extrapolation; mask brackets >1.51 times the '
    'median full-source barycentric wavelength step. Save selected source points plus one '
    'bracket on each side and the exact full-source spacing.')
p['normalization']['structured_neighbor'] = ('The original C002 core was visible between C003 core '
    'and negative reference flank. C003 original core union 3869.495–3870.0075 Angstrom lies in '
    'C002 surroundings, between its core and positive flank, ending 0.095 Angstrom before that '
    'flank. It is not inside a C002 reference flank. Portions of both C002 flanks overlap the '
    'already-seen C003 context; retain all structure without masks. Fixed medians are reference '
    'levels, not established line-free continua.')
p['comparisons']['merged'] = ('7 epochs × 1 fixed discovery reference × 2 frames × 2 regions = '
                            '28 records, including 4 identical-product self-comparisons.')
p['comparisons']['native'] = ('2 discovery covering orders × 2 frames × 2 regions = 8 '
    'same-exposure native-to-merged records. Shared extraction is not independent confirmation '
    'or a physical flux ratio. Keep invalid reference or insufficient support outcomes explicit.')
p['comparisons']['minimum_common_core'] = 41
p['comparisons']['minimum_common_broad'] = 440
p['comparisons']['self_and_dependency_flags'] = ('same_exposure and identical_product_self_pair '
    'flags are explicit. One fixed discovery reference is retained. The two native orders share '
    'one exposure; earlier wavelength contexts and all seven epochs are dependent.')
p['slots'] = {'merged_profiles': 14, 'native_profiles': 4, 'all_profiles': 18,
    'merged_comparisons': 28, 'native_comparisons': 8, 'all_comparisons': 36,
    'identical_product_self_comparisons': 4, 'saved_raw_order_panels': 2,
    'structurally_excluded_native_order_pairs': 0, 'expected_bounded_input_windows': 9,
    'distinct_discovery_products': 1, 'discovery_records': 1}
p['bounded_arrays'] = ('Save nine pre-interpolation source windows with exact indices, '
    'original-frame and barycentric wavelengths, signed flux, ERR (NaN for unavailable native '
    'errors), source hashes, BERV and full-source spacing. Read only the available union required '
    'by both fixed-frame windows plus brackets. Full merged coordinates locate slices; native '
    'coordinates derive from headers. Do not extend any partial order coverage. Preserve C003 '
    'and C004 window dependence.')
p['headers'] = ('Check all seven merged headers and the one discovery native header before new '
    'flux access: exact identity/hash, recorded metadata, numeric BERV, merged BARYCENT air '
    'Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native 72×4096 shape and '
    'unchanged degree/order 2 and 3 coefficients. Failed slots remain explicit; coordinate '
    'coverage is distinct from signed flux quality, reference validity and mapping reliability.')
p['preserved_raw_context'] = ('Copy both exact historical V2E2-0033 raw/native NPZs, orders 2 '
    'and 3. Display original raw_cutout/raw_excess after release using separate full scales. '
    'Preserve all primary, secondary, adopted and mapping stages. In particular, order 2 '
    'local/baseline failures remain; no new registration, subtraction, detector model or '
    'independent pixel claim.')
p['release_contract']['schema'] = 'HARPS_C002_GROUP_RELEASE_V1'
p['plot_script_sha256'] = sha(HERE / 'plot_group.py')
p['plot_rules'] = ('Four figures: all seven merged broad/core profiles with signed and normalized '
    'flux in both frames; both native order contexts; both historical raw/excess pairs. One '
    '0033/R002 catalog/discovery marker, not a fitted peak. Keep every raw-only annotation and '
    'partial support; no smoothing, clipping or favorable selection. Matching merged-frame and '
    'native raw-frame scales retain every finite value with 5 percent margins. Raw panels use '
    'separate full extrema. Historical order 2 mapping failures remain explicit.')
p['limitations'] = [
    'Post-detection context of one U record and seven reused original-cohort exposures; no new observing time, independent detection or archive-wide completeness. V2E2-0033 remains U.',
    'The C002 original core was already visible in completed C003 surrounding spectrum, between its negative flank and core. Selection by original queue row 10 preceded C004 values but does not make subsequent interpretation blind or independent.',
    'The C002 window overlaps C003 over 3866.75125–3871.6025 Angstrom (4.85125 Angstrom) and C004 over 3869.245–3871.6025 Angstrom (2.3575 Angstrom). Its original core lies outside the C004 window. All seven observing products are reused.',
    'The sole fixed discovery reference is observed on 2022-05-07 with BERV -18.8907517532076 km/s. Use its anchor, not the earlier March or January anchors. The seven-epoch BERV span 59.6098131157401 km/s is coordinate separation, not calibrated origin discrimination.',
    'The fixed topocentric core is not recentered on other features. A coherent center can leave the original ±0.25 Angstrom core; those comparisons may describe neighboring structure.',
    'C003 original core union lies in C002 surroundings between its core and positive flank, not inside the reference flank. Retain every known neighboring structure. Fixed pooled medians are reference levels, not line-free continua. No fitted widths, centers, lags, RV, drift, background, masks or moved flanks.',
    'Fresh 72-order header scan and original event centers determine both covering orders. Do not inherit C003/C004 order exclusions or flux quality. Covering the feature center need not provide both flanks, adequate common support or positive signed references.',
    'Order 2 ends at fixed offsets +1.1609411974559407 Angstrom barycentric and +1.161014356180658 Angstrom topocentric. The whole positive reference flank is absent in both frames. At most 417 total grid centers and 366 surrounding centers have geometric support; retain raw-only normalization and the unchanged 440-sample surrounding Pearson gate. Core raw Pearson remains conditional on finite nonconstant support. This is missing coverage, not a measured nonpositive two-flank reference.',
    'Order 2 retains historical local_mapping_usable=false and baseline_mapping_verified=false, alongside true global and later five-window diagnostics. Order 3 historical stages are true. Coordinate support and native/merged similarity cannot retroactively validate order 2 raw mapping.',
    'Native BUNIT absent; native extracted units unspecified. Merged ADU and native scales differ; same-exposure extraction agreement is not independent confirmation or a physical flux ratio.',
    'ERR coverage and descriptive first-difference proxies do not establish a formal uncertainty model, significance, physical linewidth, false-alarm rate, sensitivity or qualified null.',
    'All previous extraction, mapping, raw panels, labels, epoch outputs and completed contexts remain unchanged.'
]
p['source_hashes'] = {}
paths = [HERE / n for n in ['compare_group.py', 'plot_group.py', 'README.md',
                            'prepare_plan.py', 'synthetic_preflight.py']]
paths += [PHASE / n for n in ['inputs/INPUT_INVENTORY.json', 'inputs/RESTORE_RECEIPT.json',
    'inputs/restore_inputs.py', 'BASELINE_VERIFICATION.json', 'input_audit/INPUT_AUDIT.json',
    'input_audit/audit_inputs.py']]
paths += [old / n for n in ['NEXT_ACTION.json', 'scientific_review/NEXT_STEP.md',
                            'analysis/compare_group.py', 'analysis/PLAN.json', 'analysis/plot_group.py']]
paths += [REPO / 'work_harps_20261102_c003_context/analysis/PLAN.json']
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
p['native_order_selection'] = ('Historical orders 2 and 3 are retained after a fresh all-72-order '
    'header check against the original topocentric feature center. Both are covering orders; '
    'there are no structural exclusions. Partial window/flank support, signed values and '
    'mapping qualifications remain distinct and explicit.')
p['native_fixed_frame_header_geometry'] = [{'dp_id': r['dp_id'], 'order': order,
    'fixed_frame_header_geometry': r['orders'][str(order)]['fixed_frame_header_geometry']}
    for r in inv['native_products'] for order in r['covering_orders']]
p['preserved_event_raw_pairs'] = [{'event': r['event'], 'dp_id': inv['events'][r['event']],
    'order': r['order']} for r in inv['saved_native_raw_cutouts']]
B = {r['dp_id']: r['berv_km_s'] for r in inv['merged_spectra']}
cb = p['group_center_bary_air_angstrom']
c = p['c_km_s']
ct = cb / (1 + p['anchor_berv_km_s'] / c)
p['event_markers'] = [{'event': event, 'resolution_group': 'R002',
    'center_bary_air_angstrom': cb, 'barycentric_offset_angstrom': 0.,
    'discovery_topocentric_offset_angstrom': cb / (1 + B[dp] / c) - ct,
    'color': '#b8292f'} for event, dp in inv['events'].items()]
assert p['events'] == {'V2E2-0033': 'ADP.2022-05-08T01:01:37.876'}
assert p['anchor_dp_id'] == p['discovery_dp_ids'][0] and B[p['anchor_dp_id']] == p['anchor_berv_km_s']
assert p['included_native_order_pairs'] == [
    {'dp_id': p['anchor_dp_id'], 'order': 2}, {'dp_id': p['anchor_dp_id'], 'order': 3}]
assert len(p['preserved_event_raw_pairs']) == 2 and not p['excluded_native_order_evidence']
(HERE / 'PLAN.json').write_text(json.dumps(p, indent=2, allow_nan=False) + '\n')
print(json.dumps({'plan_sha256': sha(HERE / 'PLAN.json'), 'sources': len(p['source_hashes']),
                 'slots': p['slots'], 'anchor_berv_km_s': p['anchor_berv_km_s']}, indent=2))
