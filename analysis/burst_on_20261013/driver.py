"""Prospective HIP98505 ON four-row burst pilot; import/check-only read text metadata.

One combined maximum per carrier over seven windows, widths1/3 and159drifts.
Full16row preprocessing is unchanged and runs once per declared core. Only root
invokes --run after exact scope and reviewed GO; no source acquisition occurs.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'seti_burst_on'
DETECTOR = 'burst_previous/analysis/new_visit_search/dependencies/detector.py'
MIDPOINT = 'burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'burst_previous/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
RESTORED = 'burst_previous/analysis/RESTORATION_RECEIPT_20261011.json'
PREVIOUS = 'burst_previous/analysis/burst4_20261011'
PINS = {DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
        ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        ACQ_ADJACENT: '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e',
        PREVIOUS + '/driver.py': '5cda139f404a29fa96659e46237bad2978588920da019198ba3e21009cea1d84',
        PREVIOUS + '/scope.json': '7352992e3f31e92267b12618cbe3a0d4c02fd022760a97ae30f0aeaf1a65da41'}
JOBS = {'on20170428_epoch1_HIP98505': ('epoch1_on', 'HIP98505'),
        'on20170428_epoch2_HIP98505': ('epoch2_on', 'HIP98505'),
        'on20170428_epoch3_HIP98505': ('epoch3_on', 'HIP98505')}
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 178257920
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
QS = tuple(4 + 8 * k for k in range(32))
DOMAINS = tuple((native, q) for native in (170, 171, 172) for q in QS)
STARTS = (0, 2, 4, 6, 8, 10, 12)
DC_CHANNELS = (178782208, 179830784, 180879360)
CAPS = {'CPU_cap_s_per_job': 600, 'wall_cap_s_per_job': 900,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3,
        'job_output_budget_bytes': 50 * 1024**2, 'total_output_budget_bytes': 150 * 1024**2,
        'workspace_cap_bytes': 8 * 1024**3}
COUNTS = {'maps': 96, 'carrier_maximum_records': 393216,
          'valid_hypothesis_records': 875298816, 'normalization_records': 96,
          'score_audit_queries': 390, 'score_audit_raw_power_cells': 784680,
          'DC_row_box_membership_checks': 4718592,
          'DC_aware_TOP20_entries': 20, 'DC_aware_TOP3_entries': 3,
          'TOP20_entries': 20, 'TOP3_entries': 3, 'decoded_rows_verified': 48}
MAP_FIELDS = ('frequency_hz_at_window_reference', 'maximum_robust_box_track_score',
              'winning_drift_hz_s', 'winning_drift_grid_index', 'winning_window_start_row',
              'winning_width_channels', 'valid_hypothesis_count', 'source_reference_channels',
              'drift_grid_hz_s')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Relative confined path required')
    return path


def byte_pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def method_contract():
    return {'schema': 'SETI_S2017_ON_BURST4_SEVEN_WINDOW_COMBINED_MAP_SCOPE_V1',
        'jobs': {job: {'scan_id': scan, 'primary_target': target, 'original_acquisition_role': 'ON'}
                 for job, (scan, target) in JOBS.items()},
        'core_domains': [{'native_chunk_index': n, 'core_q': q,
                         'reference_channel_interval_half_open': [n * COUNT + q * CORE, n * COUNT + (q + 1) * CORE]}
                        for n, q in DOMAINS],
        'q_selection': 'q=4+8*k; k0..31; uniform fixed frequency sampling across all three natives',
        'total_maps': 288, 'maps_per_target': 96, 'maps_per_ON_scan': 96,
        'legacy_target_key_explanation': 'maps_per_target and expected_counts_per_target retained for prior interface; here they mean each original ON scan/job, never pooled across same HIP98505 target',
        'core_channels': CORE, 'halo_channels': HALO,
        'source_rows_per_scan': 16, 'window_length_rows': 4, 'window_start_rows': list(STARTS),
        'windows_per_core': 7, 'widths_channels': [1, 3],
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79},
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'valid_hypotheses_per_carrier': 2226,
        'total_carrier_maximum_records': 1179648, 'total_valid_hypothesis_records': 2625896448,
        'preprocessing': 'unchanged detector.preprocess plus _box_arrays on all16rows once per core',
        'normalization': 'all4096 declared core channels; unchanged16row median/MAD/winsorized location',
        'reference_time': 'each candidate window own first source row integration midpoint',
        'window_times_s': [0, TSAMP, 2 * TSAMP, 3 * TSAMP],
        'score_equation': 'sum of selected4 row standardized width-box terms / sqrt(4*width)',
        'rounding': 'np.rint complete absolute source mapping before subtracting raw crop origin',
        'winning_tie_order': 'window start ascending; width1 before3; drift index ascending; strict greater update',
        'target_ranking': 'all96 combined carrier maps per original ON scan/job, never pooled by target; score descending then absolute channel ascending; greedy distance>3; TOP3=first3TOP20',
        'map_npz_fields': list(MAP_FIELDS),
        'audit_carrier_indices': [0, 2048, 4095, 'core_max'], 'extra_global_TOP3_audits': 3, 'extra_DC_aware_TOP3_audits': 3,
        'audit_raw_shape': [4, 503], 'audit_raw_offsets_inclusive': [-251, 251],
        'audit_NPZ_fields': ['raw_power', 'absolute_time_rows', 'rounded_absolute_centers', 'standardized_row_box_sums'],
        'audit_score_ATOL': 1e-7, 'audit_score_RTOL': 1e-10,
        'map_NPZ_budget_bytes': 190 * 1024, 'normalization_JSON_budget_bytes': 4000,
        'audit_NPZ_budget_bytes': 11000, 'other_JSON_total_budget_bytes': 4 * 1024**2,
        'expected_counts_per_target': COUNTS, 'total_score_audit_queries': 1170,
        'total_score_audit_raw_power_cells': 2354040, **CAPS,
        'masks': None, 'geometric_veto': False, 'data_selected_exclusions': [],
        'known_stationary_core_128_selected': False,
        'novelty': 'same frozen burst duration/window/drift family newly applied to three HIP98505 ON scans; preceding burst application was three other-star OFF scans',
        'original_independent_visits': 1, 'ON_scan_positions_are_independent_visits': False,
        'frozen_DC_source_channels': list(DC_CHANNELS),
        'DC_aware_ranking': 'all96 cached winning carrier maps per ON scan; reject a winner iff any chosen4row inclusive width box touches any frozen DC channel; retain score/drift/window/width; order and distance>3 suppression unchanged; no nonwinning hypotheses recovered',
        'DC_contact_definition': 'np.rint complete absolute frequency+drift*t/DF at chosen4row relative times; abs(center-DC)<=width//2 including edges',
        'secondary_DC_cached_winner_filter': True,
        'DC_geometry_preoutcome': {'minimum_reference_distance_to_DC_channels': 12289,
                                  'maximum_fourrow_drift_displacement_channels': 79,
                                  'maximum_width_radius_channels': 1,
                                  'all_selected_domains_prospectively_DC_clean': True},
        'exposed_data_exploratory': True, 'blind_validation': False,
        'new_bandwidth_or_observation': False, 'source_acquisition_roles_changed': False,
        'protected2016_data_opened': False, 'injection_arrays_opened': False,
        'previous_outputs_modified': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'new_telescope_HTTP_requests': 0, 'cost_DKK': 0}


def source_records(root):
    midpoint, adjacent = read_json(root / MIDPOINT), read_json(root / ADJACENT)
    acquisitions = {171: read_json(root / ACQ171), 170: read_json(root / ACQ_ADJACENT),
                    172: read_json(root / ACQ_ADJACENT)}
    result = []
    for scan, target in JOBS.values():
        original = next(s for s in midpoint['sources'] if s['label'] == scan)
        header = original['current_header']['data_attributes']
        require(original['role'] == 'on' and header['source_name'] == target
                and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP,
                'Original HIP98505 ON primary header differs')
        for native in (170, 171, 172):
            items = midpoint['sources'] if native == 171 else adjacent['by_native_chunk'][str(native)]['sources']
            item = next(s for s in items if s['label'] == scan)
            require(item['current_header'] == original['current_header'] and item['url'] == original['url']
                    and item['etag'] == original['etag'] and item['role'] == 'on', 'Across-band immutable source identity differs')
            rec = next(r for r in acquisitions[native]['decoded_files']
                       if r['scan_id'] == scan and (native == 171 or r['native_chunk_index'] == native))
            require(rec['source_channel0'] == native * COUNT and rec['shape'] == [16, 1, COUNT]
                    and [r['time_row'] for r in rec['decoded_rows']] == list(range(16))
                    and all(r['decoded_bytes'] == COUNT * 4 for r in rec['decoded_rows']), 'Original compact geometry/rows differ')
            parent = Path('seti_raw') / Path(ACQ171 if native == 171 else ACQ_ADJACENT).relative_to('burst_previous').parent
            result.append({'native_chunk_index': native, 'scan_id': scan, 'primary_target': target,
                'original_acquisition_role': 'ON', 'path': (parent / rec['array_file']).as_posix(),
                'bytes': rec['bytes'], 'sha256': rec['file_sha256'], 'source_channel0': rec['source_channel0'],
                'shape': rec['shape'], 'decoded_rows': rec['decoded_rows'], 'original_header': header,
                'original_source_url': item['url'], 'original_source_etag': item['etag'],
                'original_source_file_bytes': item['source_file_bytes'],
                'original_header_full': item['current_header'],
                'metadata_acquisition_path': ACQ171 if native == 171 else ACQ_ADJACENT})
    return result


def contract(root, scope):
    require(all(scope.get(k) == v for k, v in method_contract().items()), 'Frozen scientific/resource method differs')
    pins = {}
    for rec in scope['text_code_pins']:
        path = confined(root, rec['path'])
        require(path.suffix in ('.py', '.json', '.md', '.txt') and byte_pin(root, path) == rec, 'Text/code pin differs')
        pins[rec['path']] = rec['sha256']
    require(all(pins.get(path) == sha for path, sha in PINS.items()), 'Original metadata/detector pins differ')
    require(pins.get(BASE + '/driver.py') == digest(Path(__file__).resolve()), 'Burst driver self pin differs')
    require(scope['source_compacts'] == source_records(root), 'Exact nine source declarations differ')
    require(read_json(root / RESTORED)['status'] == 'PASS_EXACT18_COMPACTS_288_DECODED_ROWS', 'Completed original restoration required')
    previous = read_json(root / PREVIOUS / 'scope.json')
    require(all(v['original_acquisition_role'] == 'OFF' for v in previous['jobs'].values())
            and not set(JOBS).intersection(previous['jobs'])
            and previous['window_start_rows'] == list(STARTS)
            and previous['core_domains'] == scope['core_domains'],
            'Preceding scope must be unchanged distinct OFF application; same method/new ON subject required')


def workspace_bytes(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                info = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = info.st_dev, info.st_ino
            if key not in seen:
                seen.add(key)
                total += info.st_blocks * 512
    return total


def output_guard(root, out, workspace=False):
    require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= CAPS['job_output_budget_bytes'], '50MiB job output cap exceeded')
    if workspace:
        require(workspace_bytes(root) <= CAPS['workspace_cap_bytes'], '8GiB workspace cap exceeded')


def store_npz(np, root, path, values, bound):
    with path.open('xb') as stream:
        np.savez(stream, **values)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_size <= bound, 'Prospective NPZ output bound exceeded')
    return byte_pin(root, path)


def runtime_versions():
    return {'Python': sys.version.split()[0],
            **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}}


def run(root, scope, job, out):
    import numpy as np
    import h5py
    import hdf5plugin
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Supported bitshuffle decoder required')
    detector = module('on_burst4_unchanged_detector', root / DETECTOR)
    scan_id, target = JOBS[job]
    records = [r for r in scope['source_compacts'] if r['scan_id'] == scan_id]
    require([r['native_chunk_index'] for r in records] == [170, 171, 172], 'Own contiguous source triplet required')
    # Authenticate every compact byte pin before opening any source payload.
    source_pins = [byte_pin(root, confined(root, rec['path'])) for rec in records]
    require(all(pin['bytes'] == rec['bytes'] and pin['sha256'] == rec['sha256']
                for rec, pin in zip(records, source_pins)), 'Whole compact pin differs before payload opening')
    power = np.empty((16, 3 * COUNT), dtype='<f4')
    row_checks = []
    for rec, pin in zip(records, source_pins):
        path = confined(root, rec['path'])
        offset = rec['source_channel0'] - C0
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == rec['source_channel0']
                    and data.attrs['original_source_url'] == rec['original_source_url']
                    and data.attrs['original_source_etag'] == rec['original_source_etag'], 'Actual compact provenance differs')
            for row in rec['decoded_rows']:
                values = data[row['time_row'], 0, :]
                require(np.isfinite(values).all() and (values >= 0).all()
                        and hashlib.sha256(values.tobytes()).hexdigest() == row['decoded_sha256'], 'Decoded float32 source row differs')
                power[row['time_row'], offset:offset + COUNT] = values
        row_checks.append({'source': pin, 'decoded_rows': rec['decoded_rows'], 'rows_verified': 16})
    header = records[0]['original_header']
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 159), np.arange(4) * TSAMP
    require(drifts[79] == 0., 'Central drift must be exact zero')
    maps, audits, saved, row_sums, dc_eligibility = [], [], {}, {}, {}

    def selected_tuple(native, q, value, index, rank=None):
        start = int(value['winning_window_start_row'][index])
        result = {'primary_id': job, 'primary_target': target, 'scan_id': scan_id, 'original_acquisition_role': 'ON',
                  'native_chunk_index': native, 'core_q': q, 'map_id': '%s_native%d_q%03d' % (scan_id, native, q),
                  'carrier_index_in_core': int(index), 'source_reference_channel': int(value['source_reference_channels'][index]),
                  'frequency_hz_at_window_reference': float(value['frequency_hz_at_window_reference'][index]),
                  'window_start_row': start, 'window_length_rows': 4, 'window_source_rows': list(range(start, start + 4)),
                  'reference_time_mjd': header['tstart'] + (start + .5) * TSAMP / 86400,
                  'drift_grid_index': int(value['winning_drift_grid_index'][index]),
                  'drift_hz_s': float(value['winning_drift_hz_s'][index]),
                  'width_channels': int(value['winning_width_channels'][index]),
                  'score': float(value['maximum_robust_box_track_score'][index])}
        centers = np.rint((result['frequency_hz_at_window_reference'] - FCH1) / DF
                          + result['drift_hz_s'] * times / DF).astype(np.int64)
        radius = result['width_channels'] // 2
        touched = np.abs(centers[:, None] - np.asarray(DC_CHANNELS)[None, :]) <= radius
        result.update({'rounded_absolute_centers': centers.tolist(),
                       'width_box_source_channels_inclusive': [[int(c - radius), int(c + radius)] for c in centers],
                       'frozen_DC_source_channels': list(DC_CHANNELS),
                       'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touched.any(axis=1)).tolist(),
                       'rows_intersecting_any_frozen_DC': int(touched.any(axis=1).sum()),
                       'touch_counts_by_frozen_DC': {str(c): int(touched[:, k].sum()) for k, c in enumerate(DC_CHANNELS)},
                       'eligible_DC_untouched': bool(not touched.any()),
                       'minimum_DC_width_box_distance_channels': int((np.abs(centers[:, None] - np.asarray(DC_CHANNELS)[None, :]) - radius).min())})
        if rank is not None:
            result['rank'] = rank
        return result

    def audit(query_id, kind, native, q, value, index, sums, normalization, rank=None):
        chosen = selected_tuple(native, q, value, index, rank)
        rows = np.arange(chosen['window_start_row'], chosen['window_start_row'] + 4, dtype=np.int64)
        centers = np.rint((chosen['frequency_hz_at_window_reference'] - FCH1) / DF
                          + chosen['drift_hz_s'] * times / DF).astype(np.int64)
        absolute = centers[:, None] + np.arange(-251, 252)[None, :]
        require(absolute.min() >= C0 and absolute.max() < C0 + 3 * COUNT, 'Audit leaves authenticated raw triplet')
        raw = power[rows[:, None], absolute - C0]
        require(np.isclose(sums.sum() / np.sqrt(4 * chosen['width_channels']), chosen['score'], atol=1e-7, rtol=1e-10),
                'Cached winning four-row box arithmetic differs')
        capsule = store_npz(np, root, out / (query_id + '_raw4x503.npz'),
                            {'raw_power': raw, 'absolute_time_rows': rows, 'rounded_absolute_centers': centers,
                             'standardized_row_box_sums': sums}, 11000)
        audits.append({'query_id': query_id, 'query_kind': kind, 'native_chunk_index': native, 'core_q': q,
                       'map_id': chosen['map_id'], 'selected_tuple': chosen, 'normalization': normalization, 'capsule': capsule})

    for native, q in DOMAINS:
        first = native * COUNT + q * CORE
        channels = np.arange(first, first + CORE, dtype=np.int64)
        frequencies, crop0 = FCH1 + DF * channels, first - HALO
        crop = power[:, crop0 - C0:first + CORE + HALO - C0].astype(np.float64)
        require(crop.shape == (16, CORE + 2 * HALO), 'Complete16row contiguous core crop required')
        scan = detector.Scan(scan_id, 'ON', crop, header['tstart'], TSAMP, FCH1, DF, crop0, channels)
        z, mask, normalization = detector.preprocess(scan, cfg)
        require(mask.all(), 'No source masking allowed')
        boxes = detector._box_arrays(z, mask, cfg)
        base = (frequencies - FCH1) / DF
        best = np.full(CORE, -np.inf, dtype=np.float64)
        winning_start = np.full(CORE, -1, dtype=np.int16)
        winning_width = np.zeros(CORE, dtype=np.int16)
        winning_drift_index = np.full(CORE, -1, dtype=np.int16)
        winning_drift = np.full(CORE, np.nan, dtype=np.float64)
        valid_count = np.zeros(CORE, dtype=np.int64)
        # Traversal is the scientific tie order: start, width, ascending drift.
        for start_row in STARTS:
            window_boxes = {w: (box[0][start_row:start_row + 4], box[1][start_row:start_row + 4])
                            for w, box in boxes.items()}
            for width in (1, 3):
                for begin in range(0, 159, cfg.drift_tile):
                    ds = drifts[begin:begin + cfg.drift_tile]
                    for lo in range(0, CORE, cfg.carrier_tile):
                        hi = min(lo + cfg.carrier_tile, CORE)
                        scores, valid = detector._score_tile(window_boxes, base[lo:hi], times, DF, ds, width, crop0)
                        valid_count[lo:hi] += valid.sum(axis=0)
                        arg = scores.argmax(axis=0)
                        values = scores[arg, np.arange(hi - lo)]
                        improve = values > best[lo:hi]
                        locations = np.arange(lo, hi)[improve]
                        best[locations] = values[improve]
                        winning_start[locations] = start_row
                        winning_width[locations] = width
                        winning_drift_index[locations] = begin + arg[improve]
                        winning_drift[locations] = ds[arg[improve]]
        require(np.all(valid_count == 2226) and np.isfinite(best).all()
                and np.isin(winning_start, STARTS).all() and np.isin(winning_width, (1, 3)).all(),
                'Complete combined seven-window family required')
        value = {'frequency_hz_at_window_reference': frequencies,
                 'maximum_robust_box_track_score': best, 'winning_drift_hz_s': winning_drift,
                 'winning_drift_grid_index': winning_drift_index, 'winning_window_start_row': winning_start,
                 'winning_width_channels': winning_width, 'valid_hypothesis_count': valid_count,
                 'source_reference_channels': channels, 'drift_grid_hz_s': drifts}
        map_id = '%s_native%d_q%03d' % (scan_id, native, q)
        map_pin = store_npz(np, root, out / (map_id + '.npz'), value, 190 * 1024)
        compact = dict(normalization)
        require(compact.pop('normalization_source_channels') == channels.tolist(), 'Normalization core interval differs')
        compact['normalization_source_channel_interval_half_open'] = [first, first + CORE]
        norm_path = out / (map_id + '_normalization.json')
        save(norm_path, compact)
        norm_pin = byte_pin(root, norm_path)
        require(norm_pin['bytes'] <= 4000, 'Compact full16row normalization budget exceeded')
        maps.append({'map_id': map_id, 'scan_id': scan_id, 'primary_id': job, 'original_acquisition_role': 'ON',
                     'native_chunk_index': native, 'core_q': q, **map_pin, 'normalization': norm_pin,
                     'reference_channel_interval_half_open': [first, first + CORE],
                     'loaded_channel_interval_half_open': [crop0, first + CORE + HALO],
                     'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 2226,
                     'combined_window_start_rows': list(STARTS)})
        centers = np.rint(base[:, None] + winning_drift[:, None] * times[None, :] / DF).astype(np.int64)
        sums = np.empty((CORE, 4), dtype=np.float64)
        for width in (1, 3):
            chosen = winning_width == width
            for row in range(4):
                sums[chosen, row] = boxes[width][0][winning_start[chosen] + row,
                                                   centers[chosen, row] - crop0 - width // 2]
        saved[native, q], row_sums[native, q] = value, sums
        radii = winning_width // 2
        touches = np.abs(centers[:, :, None] - np.asarray(DC_CHANNELS)[None, None, :]) <= radii[:, None, None]
        dc_eligibility[native, q] = ~touches.any(axis=(1, 2))
        maximum = int(np.lexsort((channels, -best))[0])
        for kind, index in (('first', 0), ('midpoint', 2048), ('last', 4095), ('core_max', maximum)):
            audit('native%d_q%03d_%s' % (native, q, kind), kind, native, q, value, index, sums[index], norm_pin)
        del z, mask, boxes, window_boxes, scan, crop, centers
        output_guard(root, out, workspace=len(maps) % 16 == 0)
        if len(maps) % 8 == 0:
            print(json.dumps({'job': job, 'completed_combined_maps': len(maps), 'expected': 96}), flush=True)
    channels = np.concatenate([saved[key]['source_reference_channels'] for key in DOMAINS])
    scores = np.concatenate([saved[key]['maximum_robust_box_track_score'] for key in DOMAINS])
    eligibility = np.concatenate([dc_eligibility[key] for key in DOMAINS])
    ordered = np.lexsort((channels, -scores))

    def rank_cached_winners(dc_aware):
        selected = []
        for position in ordered:
            if dc_aware and not eligibility[position]:
                continue
            channel = int(channels[position])
            if any(abs(channel - old['source_reference_channel']) <= 3 for old in selected):
                continue
            map_index, carrier = divmod(int(position), CORE)
            native, q = DOMAINS[map_index]
            selected.append(selected_tuple(native, q, saved[native, q], carrier, len(selected) + 1))
            if len(selected) == 20:
                break
        require(len(selected) == 20, 'ON-global96map TOP20 incomplete')
        return selected

    selected, dc_selected = rank_cached_winners(False), rank_cached_winners(True)
    geometry_counts = {'all_cached_winner_carriers': int(len(channels)),
                       'eligible_DC_untouched_carriers': int(eligibility.sum()),
                       'DC_contacting_cached_winner_carriers': int((~eligibility).sum()),
                       'DC_row_box_membership_checks': COUNTS['DC_row_box_membership_checks']}
    require(geometry_counts['DC_contacting_cached_winner_carriers'] == 0,
            'Uniform q4+8k fourrow geometry unexpectedly touches frozen DC')
    for name, records_out, dc_aware in (('TOP20.json', selected, False), ('TOP3.json', selected[:3], False),
                                        ('DC_AWARE_TOP20.json', dc_selected, True),
                                        ('DC_AWARE_TOP3.json', dc_selected[:3], True)):
        save(out / name, {'schema': 'SETI_ON_BURST4_SCAN_GLOBAL_RANKS_V1', 'primary_id': job,
                          'scan_id': scan_id, 'original_acquisition_role': 'ON',
                          'selection_rule': scope['DC_aware_ranking' if dc_aware else 'target_ranking'],
                          'DC_aware_cached_winner_selection': dc_aware, 'DC_geometry_counts': geometry_counts,
                          'records': records_out})
    for group, selections in (('global_top3', selected[:3]), ('DC_aware_global_top3', dc_selected[:3])):
        for chosen in selections:
            native, q, index = chosen['native_chunk_index'], chosen['core_q'], chosen['carrier_index_in_core']
            norm = next(m['normalization'] for m in maps if (m['native_chunk_index'], m['core_q']) == (native, q))
            query_id = ('dc_global_top%02d' if group.startswith('DC') else 'global_top%02d') % chosen['rank']
            audit(query_id, group, native, q, saved[native, q], index,
                  row_sums[native, q][index], norm, chosen['rank'])
    require(len(maps) == 96 and len(audits) == 390, 'Frozen map/audit count differs')
    save(out / 'MAPS.json', {'schema': 'SETI_ON_BURST4_COMBINED_MAPS_V1', 'primary_id': job, 'scan_id': scan_id, 'records': maps})
    save(out / 'SCORE_AUDITS.json', {'schema': 'SETI_ON_BURST4_SCORE_AUDITS_V1', 'primary_id': job, 'scan_id': scan_id, 'records': audits})
    for rec, pin in zip(records, source_pins):
        offset = rec['source_channel0'] - C0
        for row in rec['decoded_rows']:
            require(hashlib.sha256(power[row['time_row'], offset:offset + COUNT].tobytes()).hexdigest()
                    == row['decoded_sha256'], 'Loaded source row changed during burst pilot')
        require(byte_pin(root, confined(root, rec['path'])) == pin, 'Original source compact changed')
    return {'counts': COUNTS, 'DC_geometry_counts': geometry_counts, 'source_compact_pre_and_post_pins': source_pins,
            'decoded_source_row_checks': row_checks, 'decoded_row_SHA_checks_before': 48,
            'decoded_row_SHA_checks_after': 48, 'original_scan_tstart_mjd': header['tstart'],
            'runtime_versions': {**runtime_versions(), 'HDF5': h5py.version.hdf5_version}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--scope', default=BASE + '/SCOPE.json')
    p.add_argument('--scope-sha256')
    p.add_argument('--freeze', default=BASE + '/freeze.json')
    p.add_argument('--freeze-sha256')
    p.add_argument('--root-go', default=BASE + '/ROOT_GO.json')
    p.add_argument('--root-go-sha256')
    p.add_argument('--job', choices=tuple(JOBS), required=True)
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    root, scope_path = args.root.resolve(), args.root.resolve() / args.scope
    scope_path = confined(root, args.scope)
    scope = read_json(scope_path)
    contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_ON_BURST4_SCOPE_NO_NUMERICAL_IMPORT_OR_SOURCE_ARRAYS',
                          'job': args.job, 'scope': byte_pin(root, scope_path), 'counts': COUNTS,
                          'installed_package_versions': runtime_versions()}))
        return
    require(args.run and digest(scope_path) == args.scope_sha256, 'Root --run and exact scope SHA required')
    freeze_path = confined(root, args.freeze)
    require(args.freeze_sha256 and digest(freeze_path) == args.freeze_sha256, 'Exact public freeze hash required before source payload opening')
    freeze = read_json(freeze_path)
    require(freeze['status'] == 'PASS_PUBLIC_FREEZE_ON_BURST4_SCOPE_READBACK'
            and freeze['scope_sha256'] == args.scope_sha256
            and freeze['driver_sha256'] == digest(Path(__file__).resolve())
            and isinstance(freeze.get('public_commit'), str) and len(freeze['public_commit']) == 40,
            'Public readback freeze/science code differs')
    go_path = confined(root, args.root_go)
    require(args.root_go_sha256 and digest(go_path) == args.root_go_sha256, 'Exact reviewed root GO hash required')
    go = read_json(go_path)
    require(go['status'] == 'GO_288_NEW_ON_BURST4_COMBINED_MAPS' and go['scope_sha256'] == args.scope_sha256
            and go['driver_sha256'] == digest(Path(__file__).resolve())
            and go['freeze_sha256'] == args.freeze_sha256
            and all(go.get(k) == v for k, v in CAPS.items()), 'Root GO scientific/resource contract differs')
    require(workspace_bytes(root) + CAPS['total_output_budget_bytes'] <= CAPS['workspace_cap_bytes'], '8GiB prospective workspace bound exceeded')
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (600, 601))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('900s burst pilot wall cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(900)
    locks, out = [], None
    try:
        for slot in range(2):
            handle = (root / BASE / ('SLOT%d.lock' % slot)).open('a+b')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locks.append(handle)
                break
            except BlockingIOError:
                handle.close()
        else:
            raise BlockingIOError('Both burst2GiB slots occupied')
        handle = (root / BASE / (args.job + '.lock')).open('a+b')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(handle)
        destination = root / BASE / 'results' / args.job
        destination.mkdir(parents=True, exist_ok=False)
        out = destination
        result = run(root, scope, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256
                and digest(freeze_path) == args.freeze_sha256, 'Scope/rootGO changed during pilot')
        pins = [byte_pin(root, path) for path in sorted(out.iterdir()) if path.is_file()]
        require(len(pins) == 588, '96maps+96normalizations+390capsules+6JSON inventory differs')
        receipt = {'schema': 'SETI_ON_BURST4_PRIMARY_EXECUTION_V1',
            'status': 'COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY',
            'primary_id': args.job, 'scan_id': JOBS[args.job][0], 'primary_target': JOBS[args.job][1],
            'original_acquisition_role': 'ON', 'scope_sha256': args.scope_sha256,
            'driver_sha256': digest(Path(__file__).resolve()), 'root_GO_pin': byte_pin(root, go_path),
            'public_freeze_pin': byte_pin(root, freeze_path), 'public_freeze_commit': freeze['public_commit'],
            **result, 'output_byte_pins': pins, 'science_slot': slot,
            'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, **CAPS,
            'source_bytes_unchanged': True, 'detector_family_new': False, 'ON_subject_application_new': True, 'new_telescope_HTTP_requests': 0,
            'new_telescope_BODY_bytes': 0, 'cost_DKK': 0, 'new_bandwidth_or_observation': False,
            'geometric_veto': False, 'exposed_data_exploratory': True, 'blind_validation': False,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
        require(receipt['process_CPU_seconds'] <= 600 and receipt['wall_seconds'] <= 900
                and receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Measured burst job resource cap exceeded')
        receipt_bytes = len((json.dumps(receipt, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        auxiliaries = sum(path.stat().st_size for path in out.glob('*.json') if not path.name.endswith('_normalization.json'))
        require(auxiliaries + receipt_bytes <= 4 * 1024**2
                and sum(path.stat().st_size for path in out.iterdir()) + receipt_bytes <= CAPS['job_output_budget_bytes'],
                'Final burst output budget exceeded')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        output_guard(root, out, workspace=True)
    except BaseException as exc:
        if out is not None and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_ON_BURST4_PRIMARY_EXECUTION_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'primary_id': args.job,
                'failure_type': type(exc).__name__, 'failure': str(exc), 'scope_sha256': args.scope_sha256,
                'new_telescope_HTTP_requests': 0})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(locks):
            handle.close()


if __name__ == '__main__':
    main()
