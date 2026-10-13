#!/usr/bin/env python3
"""Prospective fixed contexts with exact exposed-baseline reuse.

Prepare after selector freezes final tuples; run only with exact public GO
scope/code hashes. No source floats are read during metadata preparation.
"""
import argparse
import hashlib
import importlib.util
from importlib.metadata import version
import json
import math
from pathlib import Path
import resource
import signal
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
OLD_DRIVER = ROOT / 'next_dc/crossscan/driver.py'
OLD_SCOPE = ROOT / 'next_dc/crossscan/SCOPE.json'
OLD_MATRIX = ROOT / 'next_dc/crossscan/results/CONTEXT_PROFILES.json'
OLD_CROPS = ROOT / 'next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json'
OLD_QA = ROOT / 'next_dc/qa/context/QA_RECEIPT.json'
SELECTED = ROOT / 'on_cached/ranking/SELECTED_TOP9.json'
CURRENT_RAW = ROOT / 'on_cached/feasibility/RAW_RESTORATION_RECEIPT.json'
NORM_CENSUS = ROOT / 'on_cached/feasibility/ON_NORMALIZATION_DOMAIN_CENSUS.json'
DETECTOR = ROOT / 'seti_previous/analysis/new_visit_search/dependencies/detector.py'
MANIFEST = ROOT / 'seti_previous/analysis/s2017_next_native/source_manifest_v2.json'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
CHUNK, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DC = (178782208, 179830784, 180879360)
ATOL, RTOL = 1e-7, 1e-10


def check(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def checked(declaration):
    path = ROOT / declaration['path']
    check(pin(path) == declaration, 'Frozen input pin differs: ' + declaration['path'])
    return path


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def geometry(track, headers):
    import numpy as np
    vectors = []
    for scan in SCANS:
        origin = track.get('reference_origin_scan_id', track['scan_id'])
        original_times = np.asarray(track.get('original_origin_row_times_from_reference_s', (np.arange(16) * TSAMP).tolist()), dtype=np.float64)
        elapsed = (headers[scan]['tstart'] - headers[origin]['tstart']) * 86400 + original_times
        centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                          + track['drift_hz_s'] * elapsed / DF).astype(np.int64)
        vectors.append(centers.tolist())
    key = {'native_chunk_index': track['native_chunk_index'], 'core_q': track['core_q'],
           'width_channels': track['width_channels'], 'six_scan_rounded_absolute_centers': vectors}
    raw_geometry = {'width_channels': track['width_channels'], 'six_scan_rounded_absolute_centers': vectors}
    key['raw_geometry_id'] = hashlib.sha256(json.dumps(raw_geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return hashlib.sha256(json.dumps(key, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), key


def prepare():
    old_scope, old_matrix, crops = read(OLD_SCOPE), read(OLD_MATRIX), read(OLD_CROPS)
    headers = old_scope['headers']
    selection = read(SELECTED)
    tracks = selection['records']
    check(len(tracks) <= 9 and len({(t['scan_id'], t['exploratory_selection_rank']) for t in tracks}) == len(tracks),
          'Unique frozen selected logical identities required')
    census=read(NORM_CENSUS)
    check(census['status']=='PASS_ALL2298_EXACT_ORIGINAL4096_PHYSICAL_CORE_NORMALIZATIONS'
          and census['counts']['ON_map_normalizations']==2298 and census['counts']['mismatching_records']==0,
          'Original ON normalization-domain census has not passed')
    pins = {p.relative_to(ROOT).as_posix(): pin(p) for p in (OLD_DRIVER, OLD_SCOPE, OLD_MATRIX, OLD_CROPS, OLD_QA, SELECTED, CURRENT_RAW, NORM_CENSUS, DETECTOR, MANIFEST, BASE / 'PROSPECTIVE_CONTRACT.json')}
    for p in old_matrix['profiles']:
        for field in ('raw_capsule', 'normalization'):
            checked(p[field]); pins[p[field]['path']] = p[field]
    for c in crops['crops']:
        checked(c['crop']); pins[c['crop']['path']] = c['crop']
    source_records=read(CURRENT_RAW)['sources']
    check(len(source_records)==18, 'Current restored source identity count differs')
    for source in source_records:
        path = ROOT / source['restored_path']
        actual = pin(path)
        check(actual['bytes'] == source['bytes'] and actual['sha256'] == source['sha256'], 'Restored source pin differs')
        pins[actual['path']] = actual
    baseline = {}
    for t in old_matrix['frozen_selected_records']:
        key, value = geometry(t, headers)
        template = t['primary_target'] + '_rank' + str(t['exploratory_selection_rank'])
        baseline.setdefault(key, {'physical_geometry': value, 'logical_template_ids': []})['logical_template_ids'].append(template)
    check(len(baseline) == 8 and len(old_matrix['profiles']) == 54 and len(crops['crops']) == 48, 'Exposed baseline contract differs')
    new, logical, seen = [], [], set()
    for t in tracks:
        check(t['width_channels'] in (1, 3) and t['native_chunk_index'] in (170, 171, 172), 'Original template outside frozen family')
        check(t['original_acquisition_role'] == 'ON', 'Original ON role changed')
        check(t['reference_origin_scan_id']==t['scan_id'] and t['original_origin_row_times_from_reference_s']==[row*TSAMP for row in range(16)], 'Original direct-ON reference/time vector differs')
        check(t['reference_time_mjd'] == headers[t['scan_id']]['tstart'] + TSAMP / (2 * 86400),
              'Original own-first-midpoint reference differs')
        core0 = t['native_chunk_index'] * CHUNK + t['core_q'] * CORE
        check(170 * CHUNK <= core0 - HALO and core0 + CORE + HALO <= 173 * CHUNK, 'Original static crop lacks outer source support')
        checked(t['map_pin']); pins[t['map_pin']['path']] = t['map_pin']
        checked(t['normalization_pin']);pins[t['normalization_pin']['path']]=t['normalization_pin']
        key, value = geometry(t, headers)
        own_centers = value['six_scan_rounded_absolute_centers'][SCANS.index(t['scan_id'])]
        check(all(abs(center - dc) > t['width_channels'] // 2 for center in own_centers for dc in DC),
              'Selector final original box is not DC-untouched')
        template = t['scan_id'] + '_rank' + str(t['exploratory_selection_rank'])
        if key not in baseline and key not in seen:
            new.append({'physical_template_id': key, 'canonical_track': t, 'physical_geometry': value})
            seen.add(key)
        logical.append({'template_id': template, 'selected_original_record': t, 'physical_template_id': key,
                        'raw_geometry_id': value['raw_geometry_id'],
                        'physical_geometry': value, 'reuse_baseline': key in baseline,
                        'baseline_template_ids': baseline[key]['logical_template_ids'] if key in baseline else []})
    scope = {'schema': 'SETI_ON_CACHED_FIXED_CONTEXT_SCOPE_V1', 'status': 'FROZEN_BEFORE_NEW_SOURCE_FLOAT_QUERIES',
        'driver_sha256': sha(Path(__file__)), 'input_byte_pins': pins, 'headers': headers,
        'source_records': source_records, 'selected_logical_templates': logical,
        'new_physical_templates': new, 'exposed_baseline_templates': baseline,
        'counts': {'selected_logical_templates': len(logical), 'selected_logical_profiles': len(logical) * 6,
                   'reused_baseline_logical_templates': sum(x['reuse_baseline'] for x in logical),
                   'new_distinct_physical_templates': len(new), 'new_distinct_fixed_profile_queries': len(new) * 6,
                   'selected_distinct_raw_template_geometries': len({x['raw_geometry_id'] for x in logical}),
                   'selected_distinct_normalized_template_geometries': len({x['physical_template_id'] for x in logical}),
                   'exposed_baseline_logical_profiles_imported': 54, 'exposed_baseline_physical_profiles': 48,
                   'prior_raw_normalization_crops': 48},
        'resource_limits': {'CPU_seconds': 600, 'wall_seconds': 900, 'RAM_bytes': 2147483648},
        'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
        'physical_reuse_rule': read(BASE / 'PROSPECTIVE_CONTRACT.json')['physical_template_reuse_identity'],
        'raw_geometry_rule': 'Original width plus exact allsix scan16-row center vectors, independent of referenceepoch or normalizationcore; normalized-score reuse additionally requires identical native/q original4096core and pinned normalization terms',
        'normalization': 'All2298 original ON family domains metadata-verified4096core/full16, including3 inline q128 dictionaries; retain exact same native/q normalization domain. Reuse pinned fullsamecore crop and normalization where available, otherwise original detector.preprocess4096/501 rule once per new unique core/scan, preserve raw12096 crop',
        'reference_time_rule': 'Selected original reference_origin_scan_id and exact16 original_origin_row_times_from_reference_s; transported dt=(context.tstart-origin.tstart)*86400+original vector; own vector never obtained by MJD subtraction',
        'transport_convention_is_new_fixed_context_rule': True,
        'transport_is_not_claimed_bitwise_replay_of_prior_gap_fixed_profiles': True,
        'own_score_check': 'Original per-carrier map scalar maximum_robust_box_track_score[carrier] and matching drift/width/source_reference_channel; compare direct or exactly reused own context score without detector reoptimization',
        'new_detector_grid': False, 'new_mask_or_veto': False, 'new_telescope_requests': 0, 'cost_DKK': 0,
        'independent_sky_confirmation': False, 'calibrated_SNR_or_FAP': False, 'qualified_SETI_detection': False}
    save(BASE / 'SCOPE.json', scope)
    print(json.dumps({'scope_sha256': sha(BASE / 'SCOPE.json'), 'driver_sha256': scope['driver_sha256'], 'counts': scope['counts']}))


def run(args):
    check(sha(BASE / 'SCOPE.json') == args.scope_sha256 and sha(Path(__file__)) == args.driver_sha256, 'Scope/code GO hashes differ')
    scope = read(BASE / 'SCOPE.json')
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600)); resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648)); signal.alarm(900)
    started, cpu = time.monotonic(), time.process_time()
    import numpy as np
    for declaration in scope['input_byte_pins'].values(): checked(declaration)
    out = BASE / 'results'; out.mkdir(exist_ok=False)
    old_matrix, crop_manifest = read(OLD_MATRIX), read(OLD_CROPS)
    save(out / 'EXPOSED_BASELINE.json', {'source_matrix_pin': pin(OLD_MATRIX), 'baseline': old_matrix,
                                       'recomputed_scores': 0, 'new_source_float_queries': 0})
    physical_profiles = {}
    for key, declaration in scope['exposed_baseline_templates'].items():
        ids = declaration['logical_template_ids']
        physical_profiles[key] = {scan: next(p for p in old_matrix['profiles'] if p['template_id'] == ids[0] and p['context_scan_id'] == scan) for scan in SCANS}
    old_crops = {(c['scan_id'], c['native_chunk_index'], c['core_q']): c for c in crop_manifest['crops']}
    old_norms = {(p['context_scan_id'], p['selected_original_record']['native_chunk_index'], p['selected_original_record']['core_q']): p['normalization'] for p in old_matrix['profiles']}
    new_crops, new_norms, source_proof, computations = [], [], [], []
    new_normalization_count, reused_crop_count = 0, 0
    if scope['new_physical_templates']:
        import h5py, hdf5plugin
        check(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Original decoder unavailable')
        old_helper = load_module(OLD_DRIVER, 'prior_fixed_context_helpers')
        detector = old_helper.module(old_helper.DETECTOR)
        cfg = detector.Config(widths=(1, 3))
        check(cfg.running_median_channels == 501 and cfg.carrier_count == CORE, 'Original normalization constants differ')
        _, original_items = old_helper.header_metadata()
        for scan in SCANS:
            needs_new_source = any((scan, t['canonical_track']['native_chunk_index'], t['canonical_track']['core_q']) not in old_crops for t in scope['new_physical_templates'])
            joined = None
            if needs_new_source:
                pieces = []
                for native in (170, 171, 172):
                    item = next(r for r in scope['source_records'] if r['scan_id'] == scan and r['native_chunk_index'] == native)
                    with h5py.File(ROOT / item['restored_path'], 'r', rdcc_nbytes=8 * 1024 ** 2) as handle:
                        dataset = handle['data']
                        check(dataset.shape == (16, 1, CHUNK) and dataset.dtype.str == '<f4'
                              and int(dataset.attrs['original_source_frequency_chunk_origin']) == native * CHUNK
                              and dataset.attrs['original_source_url'] == original_items[scan]['url']
                              and dataset.attrs['original_source_etag'] == original_items[scan]['etag'], 'Source physical provenance differs')
                        values = dataset[:, 0, :]
                    check(np.isfinite(values).all() and (values >= 0).all(), 'Invalid source power')
                    for row in item['decoded_rows']:
                        check(hashlib.sha256(values[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'], 'Original full decoded row differs')
                    pieces.append(values)
                    source_proof.append({'native_chunk_index': native, 'scan_id': scan, 'source_pin': pin(ROOT / item['restored_path']), 'decoded_rows_verified': 16})
                joined = np.concatenate(pieces, axis=1); del pieces, values
            cache = {}
            for template in scope['new_physical_templates']:
                t, pid = template['canonical_track'], template['physical_template_id']
                native, q, width = t['native_chunk_index'], t['core_q'], t['width_channels']
                key = scan, native, q
                core0, crop0 = native * CHUNK + q * CORE, native * CHUNK + q * CORE - HALO
                if key not in cache:
                    if key in old_crops:
                        crop_declaration = old_crops[key]
                        with np.load(checked(crop_declaration['crop']), allow_pickle=False) as data: rawcrop = data['raw_power'].copy()
                        check(hashlib.sha256(rawcrop.tobytes()).hexdigest() == crop_declaration['raw_float32_sha256'], 'Existing rawcrop body hash differs')
                        norm = read(checked(old_norms[key])); norm_pin = old_norms[key]
                        provenance = {'kind': 'PINNED_PREVIOUS_FULLCORE_CROP_AND_NORMALIZATION', 'raw_crop': crop_declaration['crop'], 'normalization': norm_pin}
                        reused_crop_count += 1
                    else:
                        rawcrop = joined[:, crop0 - 170 * CHUNK:crop0 - 170 * CHUNK + CORE + 2 * HALO].copy()
                        check(rawcrop.shape == (16, 12096) and rawcrop.dtype.str == '<f4', 'New static rawcrop geometry differs')
                        raw_path = out / ('%s_native%d_q%03d_crop12096.npz' % (scan, native, q))
                        with raw_path.open('xb') as stream:
                            np.savez(stream, raw_power=rawcrop, absolute_source_channel_interval_half_open=np.asarray([crop0, crop0 + 12096], dtype=np.int64),
                                     normalization_source_channel_interval_half_open=np.asarray([core0, core0 + CORE], dtype=np.int64), source_rows=np.arange(16, dtype=np.int64),
                                     tstart_mjd=np.asarray(scope['headers'][scan]['tstart']), tsamp_s=np.asarray(TSAMP))
                        declaration = {'scan_id': scan, 'native_chunk_index': native, 'core_q': q, 'shape': [16, 12096],
                            'crop': pin(raw_path), 'absolute_source_channel_interval_half_open': [crop0, crop0 + 12096],
                            'normalization_source_channel_interval_half_open': [core0, core0 + CORE],
                            'raw_float32_sha256': hashlib.sha256(rawcrop.tobytes()).hexdigest(),
                            'raw_float32_source_row_sha256': [hashlib.sha256(rawcrop[row].tobytes()).hexdigest() for row in range(16)]}
                        new_crops.append(declaration)
                        scan_object = detector.Scan(scan, 'ON' if scan.endswith('_on') else 'OFF', rawcrop, scope['headers'][scan]['tstart'], TSAMP, FCH1, DF, crop0, np.arange(core0, core0 + CORE, dtype=np.int64))
                        norm_started = time.process_time(); z, mask, norm = detector.preprocess(scan_object, cfg); norm_cpu = time.process_time() - norm_started
                        check(mask.all(), 'Unexpected static mask'); del z, mask
                        norm = {k: v for k, v in norm.items() if k != 'normalization_source_channels'}
                        norm['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                        norm_path = out / ('%s_native%d_q%03d_normalization.json' % (scan, native, q)); save(norm_path, norm); norm_pin = pin(norm_path)
                        provenance = {'kind': 'NEW_ORIGINAL_STATIC_FULL16_PREPROCESS', 'raw_crop': declaration['crop'], 'normalization': norm_pin, 'CPU_seconds': norm_cpu}
                        new_normalization_count += 1; new_norms.append(provenance)
                    cache[key] = rawcrop, norm, norm_pin, provenance
                rawcrop, norm, norm_pin, provenance = cache[key]
                centers = np.asarray(template['physical_geometry']['six_scan_rounded_absolute_centers'][SCANS.index(scan)], dtype=np.int64)
                indices = centers[:, None] - crop0 + np.arange(-251, 252)[None, :]
                check(indices.min() >= 0 and indices.max() < 12096, 'Frozen transported track lacks503 raw support')
                raw = rawcrop[np.arange(16)[:, None], indices].copy()
                terms, cells = [], []
                for row in range(16):
                    normalized = raw[row].astype(np.float64) / norm['row_power_median'][row]
                    pixel = [(normalized[i] - float(np.median(normalized[i - 250:i + 251])) - norm['row_winsorized_residual_location'][row]) / norm['row_residual_MAD_scale'][row] for i in range(251 - width // 2, 252 + width // 2)]
                    cells.append(pixel); terms.append(float(np.asarray(pixel, dtype=np.float64).sum(dtype=np.float64)))
                terms = np.asarray(terms, dtype=np.float64); contribution = terms / math.sqrt(16 * width); score = float(terms.sum(dtype=np.float64) / math.sqrt(16 * width))
                profile_id = pid[:16] + '_' + scan
                cap = out / (profile_id + '_raw503.npz')
                elapsed = (scope['headers'][scan]['tstart'] - scope['headers'][t['reference_origin_scan_id']]['tstart']) * 86400 + np.asarray(t['original_origin_row_times_from_reference_s'],dtype=np.float64)
                with cap.open('xb') as stream: np.savez(stream, raw_power=raw, rounded_absolute_centers=centers, standardized_row_box_sums=terms, row_score_contribution=contribution, standardized_original_box_cells=np.asarray(cells, dtype=np.float64), times_from_primary_reference_s=elapsed, source_rows=np.arange(16, dtype=np.int64))
                positive = np.maximum(contribution, 0.); total = float(positive.sum())
                contacts = np.abs(centers[:, None] - np.asarray(DC)[None, :]) <= width // 2
                record = {'physical_template_id': pid, 'profile_id': profile_id, 'context_scan_id': scan,
                    'raw_geometry_id': template['physical_geometry']['raw_geometry_id'],
                    'canonical_selected_original_record': t, 'times_from_primary_reference_s': elapsed.tolist(),
                    'row_midpoint_mjd': [scope['headers'][scan]['tstart'] + (row + .5) * TSAMP / 86400 for row in range(16)],
                    'context_target': scope['headers'][scan]['source_name'], 'original_acquisition_role': 'ON' if scan.endswith('_on') else 'OFF',
                    'rounded_absolute_centers': centers.tolist(), 'width_channels': width, 'row_standardized_box_sum': terms.tolist(),
                    'row_score_contribution': contribution.tolist(), 'fixed_robust_box_track_score': score,
                    'positive_row_count': int((positive > 0).sum()), 'positive_row_contribution_max_fraction': float(positive.max()/total) if total else None,
                    'DC_contact_rows_any_frozen_center': np.flatnonzero(np.any(contacts, axis=1)).tolist(),
                    'raw_capsule': pin(cap), 'normalization': norm_pin, 'normalization_provenance': provenance,
                    'query_disposition': 'NEW_FIXED_QUERY', 'independent_sky_confirmation': False,
                    'same_target_ON_scan_within_one_visit': scan.endswith('_on')}
                physical_profiles.setdefault(pid, {})[scan] = record; computations.append(record)
            del cache, joined
    selected_profiles, own_checks = [], []
    map_cache = {}
    for logical in scope['selected_logical_templates']:
        t, pid = logical['selected_original_record'], logical['physical_template_id']
        map_key = t['map_pin']['path']
        if map_key not in map_cache:
            with np.load(checked(t['map_pin']), allow_pickle=False) as values:
                map_cache[map_key] = {k: values[k].copy() for k in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_width_channels', 'source_reference_channels')}
        original = map_cache[map_key]; index = t['carrier_index_in_core']
        check(original['maximum_robust_box_track_score'][index] == t['score'] and original['winning_drift_hz_s'][index] == t['drift_hz_s']
              and int(original['winning_width_channels'][index]) == t['width_channels'] and int(original['source_reference_channels'][index]) == t['reference_source_channel'], 'Original per-carrier tuple differs')
        own = physical_profiles[pid][t['scan_id']]
        original_norm=read(checked(t['normalization_pin']));query_norm=read(checked(own['normalization']))
        for field in ('row_power_median','row_residual_median','row_winsorized_residual_location','row_residual_MAD_scale'):
            check(np.allclose(np.asarray(query_norm[field]),np.asarray(original_norm[field]),atol=ATOL,rtol=RTOL),'Own original normalization metadata differs: '+field)
        check(math.isclose(own['fixed_robust_box_track_score'], t['score'], abs_tol=ATOL, rel_tol=RTOL), 'Own direct/reused score differs from original per-carrier scalar')
        own_checks.append({'template_id': logical['template_id'], 'map_pin': t['map_pin'], 'carrier_index_in_core': index,
                           'original_score': t['score'], 'fixed_own_score': own['fixed_robust_box_track_score'],
                           'absolute_difference': abs(own['fixed_robust_box_track_score'] - t['score']), 'reused_score': logical['reuse_baseline']})
        for scan in SCANS:
            source = physical_profiles[pid][scan]
            elapsed = (scope['headers'][scan]['tstart'] - scope['headers'][t['reference_origin_scan_id']]['tstart']) * 86400 + np.asarray(t['original_origin_row_times_from_reference_s'],dtype=np.float64)
            selected_profiles.append({'template_id': logical['template_id'], 'selected_original_record': t,
                'physical_template_id': pid, 'context_scan_id': scan, 'times_from_primary_reference_s': elapsed.tolist(),
                'raw_geometry_id': logical['raw_geometry_id'],
                'source_fixed_profile': source, 'query_disposition': 'HASH_PINNED_BASELINE_REUSE' if logical['reuse_baseline'] else 'NEW_FIXED_QUERY_OR_CURRENT_LOGICAL_ALIAS',
                'baseline_matrix_pin': pin(OLD_MATRIX) if logical['reuse_baseline'] else None,
                'previous_raw_capsule_reference_metadata_retained': logical['reuse_baseline'], 'independent_sky_confirmation': False,
                'same_target_ON_scan_within_one_visit': scan.endswith('_on')})
    save(out / 'CONTEXT_PROFILES.json', {'schema': 'SETI_ON_CACHED_REUSE_AND_NEW_FIXED_CONTEXTS_V1', 'selected_profiles': selected_profiles,
        'new_physical_profiles': computations, 'own_per_carrier_score_checks': own_checks, 'exposed_baseline_matrix_pin': pin(OLD_MATRIX),
        'new_normalization_crops': new_crops, 'new_normalizations': new_norms, 'source_decoded_row_proof': source_proof,
        'new_distinct_fixed_profile_queries': len(computations), 'new_full16_normalizations': new_normalization_count,
        'prior_raw_normalization_crop_queries_reused': reused_crop_count, 'new_detector_grid': False, 'new_mask_or_veto': False,
        'new_telescope_requests': 0, 'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False})
    for declaration in scope['input_byte_pins'].values(): checked(declaration)
    receipt = {'schema': 'SETI_ON_CACHED_FIXED_CONTEXT_EXECUTION_V1', 'status': 'COMPLETE_SELECTED_FIXED_CONTEXTS_WITH_EXACT_REUSE',
        'scope_sha256': args.scope_sha256, 'driver_sha256': args.driver_sha256, 'counts': scope['counts'],
        'new_distinct_fixed_profile_queries': len(computations), 'new_full16_normalizations': new_normalization_count,
        'new_raw_normalization_crops': len(new_crops), 'prior_raw_normalization_crop_queries_reused': reused_crop_count,
        'new_source_decoded_rows_verified': sum(p['decoded_rows_verified'] for p in source_proof),
        'source_proof_if_reused': pin(OLD_QA), 'own_per_carrier_score_checks': own_checks,
        'original_input_bytes_unchanged': True, 'input_byte_pins': scope['input_byte_pins'], 'output_byte_pins': [pin(p) for p in sorted(out.iterdir())],
        'resource_use': {'CPU_seconds': time.process_time() - cpu, 'wall_seconds': time.monotonic() - started, 'max_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024},
        'new_detector_grid': False, 'new_mask_or_veto': False, 'new_telescope_requests': 0, 'cost_DKK': 0,
        'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False}
    save(out / 'EXECUTION_RECEIPT.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('input_byte_pins', 'output_byte_pins', 'own_per_carrier_score_checks')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prepare', action='store_true'); parser.add_argument('--run', action='store_true')
    parser.add_argument('--scope-sha256'); parser.add_argument('--driver-sha256'); args = parser.parse_args()
    check(args.prepare != args.run, 'Choose metadata prepare or exact admitted run')
    prepare() if args.prepare else run(args)
