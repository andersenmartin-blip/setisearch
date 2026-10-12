#!/usr/bin/env python3
"""Six fixed-scan raw contexts for nine frozen original core-max templates.

No frequency/drift/width search, veto, source acquisition or classification.
Uses existing full16 normalization when available, otherwise original static
preprocess on the same4096 core and4000 halo; records every new normalization.
"""
import argparse
import hashlib
import importlib.util
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
PREVIOUS = ROOT / 'seti_previous'
RESTORATION = ROOT / 'next_dc/feasibility/RAW_RESTORATION_RECEIPT.json'
MANIFEST = PREVIOUS / 'analysis/s2017_next_native/source_manifest_v2.json'
SELECTED = ROOT / 'next_dc/ranking/SELECTED_TOP9.json'
DETECTOR = PREVIOUS / 'analysis/new_visit_search/dependencies/detector.py'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
CHUNK, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
ATOL, RTOL = 1e-7, 1e-10


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    check(not path.exists(), 'No rerun/overwrite allowed: ' + str(path))
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def module(path):
    spec = importlib.util.spec_from_file_location('fixed_original_preprocess', path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def header_metadata():
    manifest = read(MANIFEST)
    items = manifest['by_native_chunk']['170']['sources']
    check([x['label'] for x in items] == list(SCANS), 'Original scan sequence differs')
    headers = {x['label']: x['current_header']['data_attributes'] for x in items}
    for scan, h in headers.items():
        check(h['fch1'] * 1e6 == FCH1 and h['foff'] * 1e6 == DF and h['tsamp'] == TSAMP,
              'Original frequency/time header differs')
    return headers, {x['label']: x for x in items}


def old_norm(track, scan):
    if scan.endswith('_on'):
        return None
    primary = {'epoch1_off': 'primary20170428_HIP97319', 'epoch2_off': 'primary20170428_HIP97461',
               'epoch3_off': 'primary20170428_HIP97663'}[scan]
    check(track['phase'] in ('central171', 'adjacent512'), 'Unknown selected source phase')
    folder = 'analysis/s2017_control_targets_20261011_v2' if track['phase'] == 'central171' else 'analysis/off_adjacent_20261011'
    audits = read(PREVIOUS / folder / 'results' / primary / 'SCORE_AUDITS.json')
    native, q = track['native_chunk_index'], track['core_q']
    matches = [r for r in audits['records'] if r['query_kind'] == 'core_max'
               and r['selected_tuple'].get('native_chunk_index', 171) == native and r['core_q'] == q]
    check(len(matches) == 1, 'Original samecore OFF normalization missing/ambiguous')
    declaration = matches[0]['normalization']
    path = PREVIOUS / declaration['path']
    actual = pin(path)
    check(actual['bytes'] == declaration['bytes'] and actual['sha256'] == declaration['sha256'],
          'Original samecore normalization pin differs')
    return actual


def prepare():
    selection, restoration = read(SELECTED), read(RESTORATION)
    tracks = selection['records']
    check(len(tracks) == 9 and len({(t['primary_target'], t['exploratory_selection_rank']) for t in tracks}) == 9,
          'Exactly nine bound frozen records required')
    check(all(t['eligible_DC_untouched'] and t['rows_intersecting_any_frozen_DC'] == 0
              and t['width_channels'] in (1, 3) for t in tracks), 'Selected original ownboxes are not DC-untouched')
    headers, _ = header_metadata()
    pins = {p.relative_to(ROOT).as_posix(): pin(p) for p in (SELECTED, RESTORATION, MANIFEST, DETECTOR)}
    sources = restoration['restored_sources']
    check(len(sources) == 18 and len({(x['native_chunk_index'], x['scan_id']) for x in sources}) == 18,
          'Exactly eighteen recorded raw sources required')
    for item in sources:
        path = ROOT / item['restored_path']
        actual = pin(path)
        check(actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], 'Restored raw compact pin differs')
        check(item['shape'] == [16, 1, CHUNK] and item['source_channel0'] == item['native_chunk_index'] * CHUNK,
              'Original source physical geometry differs')
        pins[actual['path']] = actual
    profile_jobs = []
    for track in tracks:
        template = track['primary_target'] + '_rank' + str(track['exploratory_selection_rank'])
        origin, native, q = track['scan_id'], track['native_chunk_index'], track['core_q']
        check(native in (170, 171, 172) and 0 <= q < 256, 'Invalid original native/core')
        crop0 = native * CHUNK + q * CORE - HALO
        check(170 * CHUNK <= crop0 and crop0 + CORE + 2 * HALO <= 173 * CHUNK,
              'Original core4000halo outside available contiguous band')
        original_norm = PREVIOUS / track['normalization']['path']
        actual = pin(original_norm)
        check(actual['sha256'] == track['normalization']['sha256'] and actual['bytes'] == track['normalization']['bytes'],
              'Frozen original normalization pin differs')
        capsule = ROOT / track['capsule_path']
        actual_cap = pin(capsule)
        check(actual_cap['sha256'] == track['capsule_sha256'], 'Frozen original raw503 capsule pin differs')
        pins[actual_cap['path']] = actual_cap
        for scan in SCANS:
            norm = old_norm(track, scan)
            if norm:
                pins[norm['path']] = norm
            profile_jobs.append({'profile_id': template + '_' + scan, 'template_id': template,
                                 'context_scan_id': scan, 'native_chunk_index': native, 'core_q': q,
                                 'existing_normalization': norm, 'origin_scan_id': origin})
    scope = {'schema': 'SETI_DC_UNTOUCHED_NINE_TUPLES_FIXED_SIX_SCAN_SCOPE_V1',
        'status': 'FROZEN_BEFORE_NEW_POWER_QUERIES', 'frozen_selected_records': tracks, 'profile_jobs': profile_jobs,
        'input_byte_pins': pins, 'source_records': sources, 'headers': headers, 'driver_sha256': sha(Path(__file__)),
        'counts': {'selected_templates': 9, 'fixed_scan_profiles': 54, 'physical_source_compacts': 18,
                   'physical_source_rows': 288, 'raw503_profile_cells': 434592, 'original_ownscore_matches': 9},
        'constants': {'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP, 'chunk': CHUNK, 'core': CORE, 'halo': HALO},
        'track_rule': 'Preserve selected original frequency/drift/width and ownfirstmidpoint reference; times=(context.tstart-origin.tstart)*86400+row*tsamp; centers=rint((frequency-fch1)/df+drift*times/df)',
        'normalization_rule': 'Use exact pinned samecore full16 normalization for OFF scans; ON missing norms compute original detector.preprocess on full4096core and4000halo, once per scan/native/core. No frequency/width/drift optimization.',
        'direct_score_rule': 'Each original-width cell: raw/row_level - exact501 median, minus saved or newly original-rule fullcore location, divided byMAD; sum over16rows and originalwidth divided bysqrt(16*width).',
        'morphology': 'Raw129 center-relative cells per row; center/median symmetric offsets16..64, raw peak offset over129; original-box positive row concentration and contribution time series; no statistical threshold or classifier',
        'scope_limits': {'CPU_seconds': 600, 'wall_seconds': 900, 'RAM_bytes': 2147483648},
        'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL}, 'new_detector_grid': False,
        'new_mask_or_veto': False, 'new_reranking': False, 'new_telescope_requests': 0, 'cost_DKK': 0,
        'independent_repeat_of_primary_target': False, 'qualified_SETI_detection': False,
        'calibrated_SNR_or_FAP': False,
        'interpretation': 'Exploratory fixed contexts from one historical visit. Original selected primaries were OFF; HIP98505 ON pointings and other OFF targets are different directions, not repeat confirmations of primary targets. Crossscan boxes can contact DC after extrapolation; annotate geometry without veto or adapting tuples.'}
    save(BASE / 'SCOPE.json', scope)
    print(json.dumps({'scope_sha256': sha(BASE / 'SCOPE.json'), 'driver_sha256': scope['driver_sha256'],
                      'jobs': len(profile_jobs), 'existing_norm_jobs': sum(j['existing_normalization'] is not None for j in profile_jobs),
                      'new_normalization_jobs_upper_bound': sum(j['existing_normalization'] is None for j in profile_jobs)}))


def run(args):
    check(sha(BASE / 'SCOPE.json') == args.scope_sha256 and sha(Path(__file__)) == args.driver_sha256, 'Scope/code admission differs')
    scope = read(BASE / 'SCOPE.json')
    check(scope['driver_sha256'] == args.driver_sha256, 'Frozen driver differs')
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    signal.alarm(900)
    begun, cpu0 = time.monotonic(), time.process_time()
    import numpy as np
    import h5py
    import hdf5plugin
    check(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Original bitshuffle decoder unavailable')
    for rel, expected in scope['input_byte_pins'].items():
        check(pin(ROOT / rel) == expected, 'Frozen input changed: ' + rel)
    detector = module(DETECTOR)
    cfg = detector.Config(widths=(1, 3))
    check(cfg.running_median_channels == 501 and cfg.carrier_count == CORE, 'Original preprocess constants differ')
    out = BASE / 'results'
    check(not out.exists(), 'No spectral rerun/overwrite')
    out.mkdir()
    records, verification, normalizations, physical_geometry = [], [], [], {}
    maximum_own_box_difference, maximum_own_score_difference = 0., 0.
    new_norm_count, old_norm_count = 0, 0
    _, items = header_metadata()
    for scan in SCANS:
        pieces = []
        for native in (170, 171, 172):
            item = next(s for s in scope['source_records'] if s['scan_id'] == scan and s['native_chunk_index'] == native)
            path = ROOT / item['restored_path']
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024 ** 2) as handle:
                data = handle['data']
                check(data.shape == (16, 1, CHUNK) and data.dtype.str == '<f4'
                      and int(data.attrs['original_source_frequency_chunk_origin']) == native * CHUNK
                      and data.attrs['original_source_url'] == items[scan]['url']
                      and data.attrs['original_source_etag'] == items[scan]['etag'], 'Original compact identity differs')
                values = data[:, 0, :]
            check(np.isfinite(values).all() and (values >= 0).all(), 'Invalid authenticated source power')
            for declared in item['decoded_rows']:
                row = declared['time_row']
                check(declared['decoded_bytes'] == CHUNK * 4 and hashlib.sha256(values[row].tobytes()).hexdigest() == declared['decoded_sha256'],
                      'Original decoded source-row hash differs')
            pieces.append(values)
            verification.append({'scan_id': scan, 'native_chunk_index': native, 'source_file_sha256': item['sha256'],
                                 'decoded_rows_verified': 16})
        joined = np.concatenate(pieces, axis=1)
        del pieces, values
        cache = {}
        for track in scope['frozen_selected_records']:
            native, q, width, origin = (track[k] for k in ('native_chunk_index', 'core_q', 'width_channels', 'scan_id'))
            template = track['primary_target'] + '_rank' + str(track['exploratory_selection_rank'])
            job = next(j for j in scope['profile_jobs'] if j['template_id'] == template and j['context_scan_id'] == scan)
            key = native, q
            core0, crop0 = native * CHUNK + q * CORE, native * CHUNK + q * CORE - HALO
            if key not in cache:
                norm_path = out / ('native%d_q%03d_%s_normalization.json' % (native, q, scan))
                if job['existing_normalization']:
                    norm = read(ROOT / job['existing_normalization']['path'])
                    provenance = {'kind': 'PINNED_EXISTING_SAMECORE_FULL16', 'source_pin': job['existing_normalization']}
                    old_norm_count += 1
                else:
                    crop = joined[:, crop0 - 170 * CHUNK:crop0 - 170 * CHUNK + CORE + 2 * HALO]
                    h = scope['headers'][scan]
                    original_scan = detector.Scan(scan, 'ON' if scan.endswith('_on') else 'OFF', crop,
                        h['tstart'], TSAMP, FCH1, DF, crop0, np.arange(core0, core0 + CORE, dtype=np.int64))
                    norm_cpu = time.process_time()
                    z, mask, norm = detector.preprocess(original_scan, cfg)
                    check(mask.all(), 'Unexpected original default mask')
                    provenance = {'kind': 'NEW_ORIGINAL_STATIC_FULL16_PREPROCESS', 'CPU_seconds': time.process_time() - norm_cpu,
                                  'core0': core0, 'halo_channels_each_side': HALO, 'original_detector_sha256': sha(DETECTOR)}
                    new_norm_count += 1
                    del z, mask, crop
                check(norm['normalization_unmasked_counts'] == [CORE] * 16, 'Normalization core masks differ')
                domain = norm.get('normalization_source_channel_interval_half_open')
                if domain is None:
                    check(norm['normalization_source_channels'] == list(range(core0, core0 + CORE)), 'Normalized source domain differs')
                else:
                    check(domain == [core0, core0 + CORE], 'Normalized interval differs')
                compact = {k: v for k, v in norm.items() if k != 'normalization_source_channels'}
                compact['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                save(norm_path, compact)
                cache[key] = compact, provenance, pin(norm_path)
                normalizations.append({'scan_id': scan, 'native_chunk_index': native, 'core_q': q,
                                       'provenance': provenance, 'new_normalization': pin(norm_path)})
            norm, provenance, norm_pin = cache[key]
            times = (scope['headers'][scan]['tstart'] - scope['headers'][origin]['tstart']) * 86400 + np.arange(16) * TSAMP
            centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF + track['drift_hz_s'] * times / DF).astype(np.int64)
            local = centers - crop0
            check((local - 251 >= 0).all() and (local + 251 < CORE + 2 * HALO).all(), 'Fixed extrapolated track lacks original503 halo support')
            raw = joined[np.arange(16)[:, None], centers[:, None] - 170 * CHUNK + np.arange(-251, 252)[None, :]].copy()
            check(raw.shape == (16, 503) and raw.dtype.str == '<f4', 'Raw503 extraction differs')
            terms, cell_z = [], []
            for row in range(16):
                normalized = raw[row].astype(np.float64) / norm['row_power_median'][row]
                cells = [(normalized[index] - float(np.median(normalized[index - 250:index + 251]))
                          - norm['row_winsorized_residual_location'][row]) / norm['row_residual_MAD_scale'][row]
                         for index in range(251 - width // 2, 252 + width // 2)]
                cell_z.append(cells)
                terms.append(float(np.asarray(cells, dtype=np.float64).sum(dtype=np.float64)))
            terms = np.asarray(terms, dtype=np.float64)
            contribution = terms / math.sqrt(16 * width)
            score = float(terms.sum(dtype=np.float64) / math.sqrt(16 * width))
            own = scan == origin
            if own:
                with np.load(ROOT / track['capsule_path'], allow_pickle=False) as old:
                    check(np.array_equal(centers, old['rounded_absolute_centers'])
                          and np.array_equal(raw.view(np.uint32), old['raw_power'].view(np.uint32)), 'Own raw capsule/source bits differ')
                    difference = float(np.max(np.abs(terms - old['standardized_row_box_sums'])))
                    check(np.allclose(terms, old['standardized_row_box_sums'], atol=ATOL, rtol=RTOL), 'Own original box arithmetic differs')
                    maximum_own_box_difference = max(maximum_own_box_difference, difference)
                check(math.isclose(score, track['score'], abs_tol=ATOL, rel_tol=RTOL), 'Own original selected score differs')
                maximum_own_score_difference = max(maximum_own_score_difference, abs(score - track['score']))
            profile = job['profile_id']
            capsule_path = out / (profile + '_raw503.npz')
            raw_patch = raw[:, 187:316].copy()
            with capsule_path.open('xb') as stream:
                np.savez(stream, raw_power=raw, rounded_absolute_centers=centers, times_from_primary_reference_s=times,
                         standardized_row_box_sums=terms, row_score_contribution=contribution,
                         standardized_original_box_cells=np.asarray(cell_z, dtype=np.float64))
            patch_rows = []
            for row in range(16):
                center = float(raw_patch[row, 64])
                flanks = np.concatenate((raw_patch[row, :49], raw_patch[row, 80:])).astype(np.float64)
                flank = float(np.median(flanks))
                check(flank > 0, 'Nonpositive raw symmetric flank level')
                patch_rows.append({'source_row': row, 'raw_center_power': center, 'symmetric98_flank_median': flank,
                    'center_over_symmetric98_flank_median': center / flank,
                    'maximum_raw_patch_offset_from_track_center': int(np.argmax(raw_patch[row])) - 64})
            positive = np.maximum(contribution, 0.)
            total_positive = float(positive.sum())
            concentration = {str(n): float(np.sort(positive)[-n:].sum() / total_positive) if total_positive else None for n in (1, 2, 4)}
            dc = np.asarray([178782208, 179830784, 180879360])
            contacts = np.abs(centers[:, None] - dc[None, :]) <= width // 2
            geometry_key = (scan, width, tuple(int(c) for c in centers))
            canonical_profile = physical_geometry.setdefault(geometry_key, profile)
            records.append({'profile_id': profile, 'template_id': template, 'selected_original_record': track,
                'context_scan_id': scan, 'context_target': scope['headers'][scan]['source_name'],
                'original_acquisition_role': 'ON' if scan.endswith('_on') else 'OFF', 'is_own_primary_scan': own,
                'times_from_primary_reference_s': times.tolist(),
                'row_midpoint_mjd': [scope['headers'][scan]['tstart'] + (row + .5) * TSAMP / 86400 for row in range(16)],
                'rounded_absolute_centers': centers.tolist(), 'width_channels': width,
                'row_standardized_box_sum': terms.tolist(), 'row_score_contribution': contribution.tolist(),
                'fixed_robust_box_track_score': score, 'original_selected_score': track['score'] if own else None,
                'positive_row_contribution_max_fraction': concentration['1'], 'positive_row_topN_fractions': concentration,
                'positive_row_count': int((positive > 0).sum()),
                'positive_contribution_effective_rows': total_positive ** 2 / float((positive ** 2).sum()) if total_positive else None,
                'raw129_centered_patch_metrics': patch_rows,
                'DC_contact_rows_any_frozen_center': np.flatnonzero(np.any(contacts, axis=1)).tolist(),
                'raw_capsule': pin(capsule_path), 'normalization': norm_pin, 'normalization_provenance': provenance,
                'canonical_profile_for_same_physical_original_box_geometry': canonical_profile,
                'duplicates_another_logical_profile_physical_geometry': canonical_profile != profile,
                'independent_repeat_of_primary_target': False})
        del joined, cache
    check(len(records) == 54 and sum(r['is_own_primary_scan'] for r in records) == 9, 'Fixed profile counts differ')
    save(out / 'CONTEXT_PROFILES.json', {'schema': 'SETI_DC_UNTOUCHED_FIXED54_CONTEXT_PROFILES_V1',
        'status': 'COMPLETE_NINE_FROZEN_TUPLES54_FIXED_PROFILES', 'profiles': records, 'frozen_selected_records': scope['frozen_selected_records'],
        'source_verification': verification, 'normalization_records': normalizations,
        'distinct_physical_original_box_profile_geometries': len(physical_geometry),
        'duplicate_logical_profiles_with_same_physical_geometry': len(records) - len(physical_geometry),
        'new_full16_normalizations': new_norm_count, 'existing_full16_normalizations_used': old_norm_count,
        'distinct_physical_original_box_profile_geometries': len(physical_geometry),
        'duplicate_logical_profiles_with_same_physical_geometry': len(records) - len(physical_geometry),
        'new_detector_grid': False, 'new_mask_or_veto': False, 'new_telescope_requests': 0,
        'independent_repeat_of_primary_target': False, 'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False})
    for rel, expected in scope['input_byte_pins'].items():
        check(pin(ROOT / rel) == expected, 'Original frozen inputs changed at close')
    output_pins = [pin(p) for p in sorted(out.iterdir())]
    receipt = {'schema': 'SETI_DC_UNTOUCHED_FIXED54_CROSSSCAN_EXECUTION_V1', 'status': 'COMPLETE54_FIXED_PROFILES',
        'scope_sha256': args.scope_sha256, 'driver_sha256': args.driver_sha256, 'counts': scope['counts'],
        'new_full16_normalizations': new_norm_count, 'existing_full16_normalizations_used': old_norm_count,
        'max_own_box_absolute_difference': maximum_own_box_difference, 'max_own_score_absolute_difference': maximum_own_score_difference,
        'source_verification': verification, 'normalization_records': normalizations,
        'original_inputs_unchanged': True, 'input_byte_pins': scope['input_byte_pins'], 'output_byte_pins': output_pins,
        'runtime': {'Python': sys.version.split()[0], 'numpy': np.__version__, 'h5py': h5py.__version__, 'hdf5plugin': version('hdf5plugin')},
        'resource_use': {'CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - begun,
                         'max_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024},
        'new_detector_grid': False, 'new_mask_or_veto': False, 'new_telescope_requests': 0,
        'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False}
    save(out / 'EXECUTION_RECEIPT.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('source_verification', 'normalization_records', 'input_byte_pins', 'output_byte_pins')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--driver-sha256')
    args = parser.parse_args()
    check(args.prepare != args.run, 'Choose metadata preparation or pinned admitted run')
    prepare() if args.prepare else run(args)
