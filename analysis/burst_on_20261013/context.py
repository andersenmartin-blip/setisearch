"""Fixed six-scan context of the nine saved HIP98505 ON burst winners.

Import/preflight/preparation open text and byte streams only. Numerical execution
requires the frozen CONTEXT_SCOPE hash and an explicit root GO. Frequencies,
drifts, widths, source rows and normalization cores stay fixed; there is no fit,
search, reranking or telescope acquisition in this context stage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'seti_burst_on'
DETECTOR = 'burst_previous/analysis/new_visit_search/dependencies/detector.py'
MIDPOINT = 'burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'burst_previous/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
PINS = {DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
        ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        ACQ_ADJACENT: '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e'}
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ORIGINS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
JOBS = ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505', 'on20170428_epoch3_HIP98505')
COUNT, CORE, HALO, BAND0 = 1048576, 4096, 4000, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, MEMORY_CAP = 600, 900, 2 * 1024**3
ATOL, RTOL = 1e-7, 1e-10
RESULT_STATUS = 'COMPLETE_NINE_ON_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root), 'Confined relative path required')
    return path


def pin(root, path):
    return {'path': Path(path).relative_to(root).as_posix(), 'bytes': Path(path).stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def source_metadata(root):
    """Read full original headers/decoded-row pins; never open HDF5 here."""
    for name, sha in PINS.items():
        require(digest(confined(root, name)) == sha, 'Original metadata/detector pin differs: ' + name)
    midpoint, adjacent = read(root / MIDPOINT), read(root / ADJACENT)
    acquisitions = {171: read(root / ACQ171), 170: read(root / ACQ_ADJACENT),
                    172: read(root / ACQ_ADJACENT)}
    sources, headers = [], {}
    for native in (170, 171, 172):
        manifest = midpoint if native == 171 else adjacent['by_native_chunk'][str(native)]
        require([item['label'] for item in manifest['sources']] == list(SCANS), 'Six source order differs')
        for item in manifest['sources']:
            label = item['label']
            original = next(s for s in midpoint['sources'] if s['label'] == label)
            header = item['current_header']['data_attributes']
            role = 'ON' if label.endswith('_on') else 'OFF'
            require(item['current_header'] == original['current_header'] and
                    item['url'] == original['url'] and item['etag'] == original['etag'] and
                    item['role'].upper() == role and header['fch1'] * 1e6 == FCH1 and
                    header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP,
                    'Across-band full source header/URL/ETag/original acquisition role differs')
            if role == 'ON':
                require(header['source_name'] == 'HIP98505', 'ON target differs')
            headers[label] = header
            candidates = [r for r in acquisitions[native]['decoded_files']
                          if r['scan_id'] == label and (native == 171 or r['native_chunk_index'] == native)]
            require(len(candidates) == 1, 'Unique source compact record required')
            record = candidates[0]
            require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == native * COUNT and
                    [r['time_row'] for r in record['decoded_rows']] == list(range(16)) and
                    all(r['decoded_bytes'] == COUNT * 4 for r in record['decoded_rows']),
                    'Source compact shape/channel/decoded-row pins differ')
            metadata_path = ACQ171 if native == 171 else ACQ_ADJACENT
            parent = Path('seti_raw') / Path(metadata_path).relative_to('burst_previous').parent
            source_path = (parent / record['array_file']).as_posix()
            confined(root, source_path)
            sources.append({'native_chunk_index': native, 'scan_id': label, 'path': source_path,
                            'bytes': record['bytes'], 'sha256': record['file_sha256'],
                            'shape': record['shape'], 'source_channel0': record['source_channel0'],
                            'decoded_rows': record['decoded_rows'],
                            'original_acquisition_role': role, 'original_header': header,
                            'original_header_full': item['current_header'],
                            'original_source_url': item['url'], 'original_source_etag': item['etag'],
                            'original_source_file_bytes': item['source_file_bytes'],
                            'metadata_acquisition_path': metadata_path})
    previous = -math.inf
    for label in SCANS:
        require(headers[label]['tstart'] >= previous, 'Original cadence chronology/integration gaps differ')
        previous = headers[label]['tstart'] + 16 * TSAMP / 86400
    require(len(sources) == 18, 'Exactly18 complete original source compacts required')
    return sources, headers


def validate_tracks(tops, headers, primary_scope):
    selected = []
    admitted = {(d['native_chunk_index'], d['core_q']) for d in primary_scope['core_domains']}
    for origin, job, top in zip(ORIGINS, JOBS, tops):
        require(top['scan_id'] == origin and len(top['records']) == 3, 'Exactly three selected ON winners required')
        for rank, track in enumerate(top['records'], 1):
            require(track['scan_id'] == origin and track['primary_id'] == job and
                    track['primary_target'] == 'HIP98505' and track['original_acquisition_role'] == 'ON' and
                    track['rank'] == rank and track['eligible_DC_untouched'] is True,
                    'Saved DC-aware ON track identity/rank/eligibility differs')
            native, q, index = (track[k] for k in ('native_chunk_index', 'core_q', 'carrier_index_in_core'))
            require((native, q) in admitted and type(index) is int and 0 <= index < CORE,
                    'Selected frozen carrier/core outside primary scope')
            r0 = track['window_start_row']
            require(type(r0) is int and r0 in range(0, 13, 2) and track['window_length_rows'] == 4 and
                    track['window_source_rows'] == list(range(r0, r0 + 4)), 'Selected source window differs')
            channel = native * COUNT + q * CORE + index
            require(track['source_reference_channel'] == channel and
                    track['frequency_hz_at_window_reference'] == FCH1 + DF * channel and
                    track['reference_time_mjd'] == headers[origin]['tstart'] + (r0 + .5) * TSAMP / 86400,
                    'Selected carrier/frequency/first-window-midpoint epoch differs')
            di = track['drift_grid_index']
            require(type(di) is int and 0 <= di <= 158 and
                    math.isclose(track['drift_hz_s'], -4 + di * 8 / 158, rel_tol=0, abs_tol=2e-15) and
                    track['width_channels'] in (1, 3) and math.isfinite(track['score']),
                    'Selected frozen drift/width/score differs')
            selected.append(track)
    require(len(selected) == 9 and len({(t['scan_id'], t['rank']) for t in selected}) == 9,
            'Nine distinct saved ON primary selections required')
    return selected


def prepare(root, qa_code):
    """Bind actual completed primary selections and full six-scan source metadata."""
    sources, headers = source_metadata(root)
    producer_scope, producer_driver = BASE + '/SCOPE.json', BASE + '/driver.py'
    primary_scope = read(root / producer_scope)
    require(primary_scope['total_maps'] == 288 and primary_scope['maps_per_target'] == 96 and
            primary_scope['window_start_rows'] == list(range(0, 13, 2)) and primary_scope['window_length_rows'] == 4 and
            primary_scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79} and
            primary_scope['masks'] is None and primary_scope['geometric_veto'] is False and
            primary_scope['new_bandwidth_or_observation'] is False and
            all(j['original_acquisition_role'] == 'ON' for j in primary_scope['jobs'].values()),
            'Actual prospective ON burst contract differs')
    inputs = [*PINS, producer_scope, producer_driver, BASE + '/context.py', qa_code]
    dirs, tops = [], []
    for origin, job in zip(ORIGINS, JOBS):
        folder = BASE + '/results/' + job
        dirs.append(folder)
        receipt_path = folder + '/EXECUTION_RECEIPT.json'
        receipt = read(root / receipt_path)
        require(receipt['status'] == 'COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY' and
                receipt['counts']['maps'] == 96 and receipt['scan_id'] == origin,
                'Completed96 ON burst maps per selected origin required')
        require(receipt['driver_sha256'] == digest(root / producer_driver) and
                receipt['scope_sha256'] == digest(root / producer_scope), 'Actual primary producer/scope differs')
        output_pins = {r['path']: r for r in receipt['output_byte_pins']}
        inputs.append(receipt_path)
        for name in ('DC_AWARE_TOP3.json', 'DC_AWARE_TOP20.json', 'TOP3.json'):
            path = folder + '/' + name
            require(output_pins.get(path) == pin(root, root / path), 'Actual selected list not bound by receipt')
            inputs.append(path)
        top = read(root / folder / 'DC_AWARE_TOP3.json')
        require(top['records'] == read(root / folder / 'DC_AWARE_TOP20.json')['records'][:3],
                'Saved DC-aware TOP3 differs from firstthree TOP20')
        tops.append(top)
        for track in top['records']:
            path = folder + '/' + track['map_id'] + '_normalization.json'
            require(output_pins.get(path) == pin(root, root / path), 'Selected full16 normalization not bound by receipt')
            inputs.append(path)
    tracks = validate_tracks(tops, headers, primary_scope)
    for source in sources:
        require(pin(root, root / source['path']) == {k: source[k] for k in ('path', 'bytes', 'sha256')},
                'Original full compact byte pin differs')
    return {'schema': 'SETI_ON_BURST4_FIXED_SIX_SCAN_CONTEXT_SCOPE_V1',
            'status': 'PREPARED_FROM_ACTUAL_COMPLETED_ON_DC_AWARE_TOP3',
            'producer_scope': producer_scope, 'producer_driver': producer_driver,
            'primary_dirs': dirs, 'selected_list_filename': 'DC_AWARE_TOP3.json',
            'selected_tracks': tracks, 'source_compacts': sources,
            'input_pins': [pin(root, root / name) for name in dict.fromkeys(inputs)],
            'context_code_sha256': digest(Path(__file__)), 'context_qa_code': qa_code,
            'context_qa_code_sha256': digest(root / qa_code),
            'scan_order': list(SCANS), 'primary_origins': list(ORIGINS),
            'context_profiles': 54, 'origin_primary_score_matches': 9,
            'raw_normalization_crop_shape': [16, CORE + 2 * HALO],
            'normalization_core_channels': CORE, 'normalization_halo_channels': HALO,
            'running_median_channels': 501, 'raw_profile_shape': [16, 503],
            'normalization': 'same origin4096channels in every scan; full16row preprocessing; no local reestimate of trajectory',
            'reference': 'each selected primary window first integration midpoint; actual source starts and gaps',
            'transport_equation': '(context_tstart-origin_tstart)*86400+(row-window_start_row)*tsamp',
            'rounding': 'np.rint complete absolute carrier+drift*time/DF before crop offset subtraction',
            'fixed_four_row_support': 'same selected local window_start_row:r0+4 in every context scan',
            'full16_support': 'all source rows0..15; unchanged selected carrier/drift/width',
            'four_row_denominator': 'sqrt(4*width)', 'full16_denominator': 'sqrt(16*width)',
            'full16_score_is_primary_score_match': False,
            'score_match_ATOL': ATOL, 'score_match_RTOL': RTOL,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
            'output_budget_bytes': 96 * 1024**2,
            'new_fit_or_detector_grid': False, 'new_observation': False, 'new_reference_frequency_coverage': False,
            'source_acquisition_roles_changed': False, 'mask_or_veto_applied': False,
            'protected2016_data_opened': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'interpretation': 'Post-selection fixed context in one historical visit; six scans of four directions. Three HIP98505 ON scan positions are repeats within this visit; not independent visits. Long-gap extrapolation of the frozen four-row drift has no refit and cannot exclude other context origins.'}


def run(root, scope, out):
    import numpy as np
    import h5py
    import hdf5plugin
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008),
            'Supported bitshuffle codec unavailable')
    spec = importlib.util.spec_from_file_location('on_burst_fixed_context_detector', root / DETECTOR)
    detector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = detector
    spec.loader.exec_module(detector)
    selected, sources = scope['selected_tracks'], scope['source_compacts']
    headers = {s['scan_id']: s['original_header'] for s in sources}
    rows, cfg = np.arange(16), detector.Config(widths=(1, 3))
    profiles, crops, verified = [], [], []
    for label in SCANS:
        power = np.empty((16, 3 * COUNT), dtype='<f4')
        for source in (s for s in sources if s['scan_id'] == label):
            require(pin(root, root / source['path']) == {k: source[k] for k in ('path', 'bytes', 'sha256')},
                    'Original compact pin differs at execution')
            with h5py.File(root / source['path'], 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4' and
                        int(data.attrs['original_source_frequency_chunk_origin']) == source['source_channel0'] and
                        data.attrs['original_source_url'] == source['original_source_url'] and
                        data.attrs['original_source_etag'] == source['original_source_etag'], 'Compact HDF5 provenance differs')
                offset = source['source_channel0'] - BAND0
                for declaration in source['decoded_rows']:
                    values = data[declaration['time_row'], 0, :]
                    require(np.isfinite(values).all() and (values >= 0).all() and
                            hashlib.sha256(values.tobytes()).hexdigest() == declaration['decoded_sha256'],
                            'Full decoded source-row pin differs')
                    power[declaration['time_row'], offset:offset + COUNT] = values
            verified.append({'path': source['path'], 'native_chunk_index': source['native_chunk_index'],
                             'scan_id': label, 'file_sha256': source['sha256'], 'decoded_rows_verified': 16})
        cache = {}
        for track in selected:
            native, q, origin, width = (track[k] for k in ('native_chunk_index', 'core_q', 'scan_id', 'width_channels'))
            core0 = native * COUNT + q * CORE
            crop0, cropstop = core0 - HALO, core0 + CORE + HALO
            key = (native, q)
            if key not in cache:
                channels = np.arange(core0, core0 + CORE, dtype=np.int64)
                raw = power[:, crop0 - BAND0:cropstop - BAND0].copy()
                require(raw.shape == (16, 12096), 'Exact full16 raw normalization crop required')
                scan = detector.Scan(label, 'ON' if label.endswith('_on') else 'OFF', raw,
                                     headers[label]['tstart'], TSAMP, FCH1, DF, crop0, channels)
                z, mask, normalization = detector.preprocess(scan, cfg)
                require(mask.all(), 'No context mask is admitted')
                crop_id = f'{label}_native{native}_q{q:03d}'
                crop_path = out / (crop_id + '_raw12096.npz')
                with crop_path.open('xb') as stream:
                    np.savez(stream, raw_power=raw, source_channel0=np.int64(crop0),
                             normalization_source_channels=channels, absolute_time_rows=rows)
                norm_path = out / (crop_id + '_normalization.json')
                save(norm_path, normalization)
                source = next(s for s in sources if s['scan_id'] == label and s['native_chunk_index'] == native)
                crop_record = {'crop_id': crop_id, 'scan_id': label, 'native_chunk_index': native, 'core_q': q,
                               'source_channel_interval_half_open': [crop0, cropstop],
                               'normalization_source_channel_interval_half_open': [core0, core0 + CORE],
                               'raw_crop': pin(root, crop_path), 'normalization': pin(root, norm_path),
                               'source_compact_path': source['path'], 'source_compact_sha256': source['sha256'],
                               'original_decoded_rows': source['decoded_rows']}
                crops.append(crop_record)
                cache[key] = (z, mask, normalization, crop_record)
            z, mask, normalization, crop_record = cache[key]
            if origin == label:
                folder = scope['primary_dirs'][ORIGINS.index(origin)]
                primary_norm = read(root / folder / (track['map_id'] + '_normalization.json'))
                compact = dict(normalization)
                require(compact.pop('normalization_source_channels') == list(range(core0, core0 + CORE)),
                        'Frozen core source interval differs')
                compact['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                require(compact == primary_norm, 'Own full16 normalization differs from saved primary')
            r0 = track['window_start_row']
            window_rows = np.arange(r0, r0 + 4)
            # Avoid subtracting rounded window-midpoint MJD; own rows match primary exactly.
            times = ((headers[label]['tstart'] - headers[origin]['tstart']) * 86400 +
                     (rows - r0) * TSAMP)
            base = (track['frequency_hz_at_window_reference'] - FCH1) / DF
            centers = np.rint(base + track['drift_hz_s'] * times / DF).astype(np.int64)
            local = centers - crop0
            require(np.all(local - 251 >= 0) and np.all(local + 251 < CORE + 2 * HALO),
                    'Frozen track lacks full503/filter support within unchanged normalization crop')
            box = local[:, None] + np.arange(-(width // 2), width // 2 + 1)[None, :]
            require(mask[rows[:, None], box].all(), 'Fixed context box unexpectedly masked')
            terms = z[rows[:, None], box].sum(axis=1, dtype=np.float64)
            contribution16 = terms / np.sqrt(16 * width)
            contribution4 = np.zeros(16, dtype=np.float64)
            contribution4[window_rows] = terms[window_rows] / np.sqrt(4 * width)
            score4 = float(terms[window_rows].sum(dtype=np.float64) / np.sqrt(4 * width))
            score16 = float(terms.sum(dtype=np.float64) / np.sqrt(16 * width))
            require(math.isfinite(score4) and math.isfinite(score16), 'Nonfinite fixed score')
            own = origin == label
            if own:
                require(math.isclose(score4, track['score'], abs_tol=ATOL, rel_tol=RTOL), 'Own saved primary score differs')
            profile_id = f"{origin}_rank{track['rank']}_{label}"
            capsule = power[rows[:, None], centers[:, None] - BAND0 + np.arange(-251, 252)[None, :]].copy()
            capsule_path = out / (profile_id + '_raw503.npz')
            with capsule_path.open('xb') as stream:
                np.savez(stream, raw_power=capsule, rounded_absolute_centers=centers,
                         times_from_primary_reference_s=times, absolute_time_rows=rows,
                         row_standardized_box_sum=terms, window_source_rows=window_rows,
                         row_four_row_score_contribution=contribution4, row_full16_score_contribution=contribution16)
            positive4, positive16 = np.maximum(contribution4, 0), np.maximum(contribution16, 0)
            total4, total16 = float(positive4.sum()), float(positive16.sum())
            dominant4, dominant16 = int(np.argmax(positive4)), int(np.argmax(positive16))
            profiles.append({'profile_id': profile_id, 'selected_track': track,
                             'context_scan_id': label, 'context_target': headers[label]['source_name'],
                             'original_acquisition_role': 'ON' if label.endswith('_on') else 'OFF',
                             'reference_time_mjd': track['reference_time_mjd'],
                             'times_from_primary_reference_s': times.tolist(),
                             'row_midpoint_mjd': [headers[label]['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)],
                             'rounded_absolute_centers': centers.tolist(),
                             'rounded_center_frequency_hz': (FCH1 + DF * centers).tolist(),
                             'row_standardized_box_sum': terms.tolist(), 'window_source_rows': window_rows.tolist(),
                             'row_four_row_score_contribution': contribution4.tolist(),
                             'row_full16_score_contribution': contribution16.tolist(),
                             'fixed_four_row_score': score4, 'fixed_full16_score': score16,
                             'origin_primary_score': track['score'] if own else None,
                             'origin_primary_score_difference': score4 - track['score'] if own else None,
                             'positive_row_contribution_max_fraction': float(positive4[dominant4] / total4) if total4 else None,
                             'dominant_positive_row': dominant4 if total4 else None,
                             'full16_positive_row_contribution_max_fraction': float(positive16[dominant16] / total16) if total16 else None,
                             'full16_dominant_positive_row': dominant16 if total16 else None,
                             'normalization_crop_id': crop_record['crop_id'], 'raw_capsule': pin(root, capsule_path),
                             'raw_normalization_crop': crop_record['raw_crop'], 'normalization': crop_record['normalization']})
            print('CONTEXT', profile_id, f'four={score4:.8g}', f'full16={score16:.8g}', flush=True)
        del power, cache
    profiles.sort(key=lambda p: (ORIGINS.index(p['selected_track']['scan_id']),
                                 p['selected_track']['rank'], SCANS.index(p['context_scan_id'])))
    require(len(profiles) == 54 and sum(p['origin_primary_score'] is not None for p in profiles) == 9,
            'Expected54 profiles and9 own primary score matches')
    matrix = {'schema': 'SETI_ON_BURST4_FIXED_SIX_SCAN_CONTEXT_PROFILES_V1', 'status': RESULT_STATUS,
              'selected_tracks': selected, 'profiles': profiles, 'normalization_crops': crops,
              'source_compacts': sources, 'source_verification': verified,
              'counts': {'selected_tracks': 9, 'context_profiles': 54, 'origin_score_matches': 9,
                         'source_files_verified': 18, 'source_rows_verified': 288,
                         'raw503_profile_cells': 54 * 16 * 503, 'raw_normalization_crops': len(crops),
                         'raw_normalization_crop_cells': len(crops) * 16 * 12096,
                         'four_row_scores': 54, 'full16_scores': 54, 'row_box_terms': 864},
              'selection_after_primary_search': True, 'new_fit_or_detector_grid': False,
              'new_observation': False, 'ON_scan_positions_are_independent_visits': False,
              'source_acquisition_roles_changed': False, 'ON_OFF_veto_applied': False,
              'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'interpretation': scope['interpretation']}
    save(out / 'CONTEXT_PROFILES.json', matrix)
    return matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', '--check-only', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--qa-code', default=BASE + '/context_qa.py')
    parser.add_argument('--scope', default=BASE + '/CONTEXT_SCOPE.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--root-go')
    parser.add_argument('--root-go-sha256')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.preflight:
        sources, _ = source_metadata(root)
        print(json.dumps({'status': 'PASS_TEXT_ONLY_FIXED_ON_CONTEXT_INTERFACE',
                          'context_code_sha256': digest(Path(__file__)), 'source_compacts_declared': len(sources),
                          'source_rows_declared': 288, 'numerical_modules_imported': False,
                          'source_values_opened': False, 'raw_output_values_opened': False}))
        return
    scope_path = confined(root, args.scope)
    if args.prepare:
        scope = prepare(root, args.qa_code)
        save(scope_path, scope)
        print(json.dumps({'status': scope['status'], 'scope_pin': pin(root, scope_path)}))
        return
    require(args.scope_sha256 and digest(scope_path) == args.scope_sha256, 'Exact prepared context scope hash required')
    scope = read(scope_path)
    require(scope['context_code_sha256'] == digest(Path(__file__)), 'Frozen context code differs')
    checks = [*scope['input_pins'], *[{k: s[k] for k in ('path', 'bytes', 'sha256')} for s in scope['source_compacts']]]
    for expected in checks:
        require(pin(root, confined(root, expected['path'])) == expected, 'Frozen context prerequisite pin differs')
    require(args.root_go and args.root_go_sha256, 'Exact reviewed root context GO required')
    go_path = confined(root, args.root_go)
    require(digest(go_path) == args.root_go_sha256, 'Exact reviewed root context GO hash differs')
    go = read(go_path)
    require(go['status'] == 'GO_FIXED_ON_BURST4_CONTEXT54' and
            go['context_scope_sha256'] == args.scope_sha256 and
            go['context_code_sha256'] == scope['context_code_sha256'], 'Root context GO/scope/code differs')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Fixed context wall cap900s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL_CAP)
    started, cpu0 = time.monotonic(), time.process_time()
    out = root / BASE / 'context_results'
    out.mkdir(exist_ok=False)
    try:
        matrix = run(root, scope, out)
        for expected in checks:
            require(pin(root, root / expected['path']) == expected, 'Frozen input changed during context execution')
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256,
                'Context scope/rootGO changed during execution')
        import h5py
        measured = {'wall_seconds': time.monotonic() - started, 'CPU_seconds': time.process_time() - cpu0,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(measured['wall_seconds'] <= WALL_CAP and measured['CPU_seconds'] <= CPU_CAP and
                measured['peak_RSS_bytes'] <= MEMORY_CAP, 'Measured context resource cap exceeded')
        require(sum(p.stat().st_size for p in out.iterdir()) <= scope['output_budget_bytes'], 'Context output budget exceeded')
        save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_ON_BURST4_FIXED_CONTEXT_EXECUTION_V1',
             'status': matrix['status'], 'context_scope_sha256': args.scope_sha256,
             'context_code_sha256': scope['context_code_sha256'], 'root_GO_pin': pin(root, go_path),
             'counts': matrix['counts'], 'origin_score_match_ATOL': ATOL, 'origin_score_match_RTOL': RTOL,
             'runtime_versions': {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
                                  **{n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}},
             **measured, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
             'output_pins': [pin(root, p) for p in sorted(out.iterdir()) if p.is_file()],
             'new_telescope_HTTP_requests': 0, 'new_observation': False, 'new_fit_or_detector_grid': False,
             'source_acquisition_roles_changed': False, 'source_bytes_unchanged': True,
             'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False})
    except BaseException as exc:
        if not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY',
                 'context_scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
