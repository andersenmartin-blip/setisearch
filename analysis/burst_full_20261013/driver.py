"""Prospective remaining-domain ON burst dual maxima.

Metadata preparation/check-only import no numerical libraries or source arrays.
Every numerical shard requires exact prospective public freeze and root GO.
The original score traversal stores unrestricted and best DC-untouched hypotheses;
no old pilot, failed scope, or acquisition is rerun. Outputs never overwrite.
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

BASE = 'seti_burst_full'
PILOT = 'seti_burst_on'
DETECTOR = 'burst_previous/analysis/new_visit_search/dependencies/detector.py'
MIDPOINT = 'burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'burst_previous/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
PINS = {DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
        ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        ACQ_ADJACENT: '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e',
        PILOT + '/SCOPE.json': 'd57760f51fc34c853591a077f2732b2aba1da21b1dae950ed27bedc0fb36cdce',
        PILOT + '/driver.py': 'ca3f3c24a2b9da77d99fb50a63c74ffc85b4bea6122f5d675ddb95a09ef26587',
        PILOT + '/freeze.json': '90b2295de2b3a93b0fe4704e6a8eda9eea5b2ec637a79ff5ae6e8f49b0085b55',
        PILOT + '/ROOT_GO.json': 'dcde81c439be58a39924082e3d4bb7f05a3bc486a3b4a162ed1c18088da40aed',
        PILOT + '/qa_results/QA_RECEIPT.json': 'a2a5c70e2718a11508e3c4d1948ecd1cbd6446096265af2adda56784dd7b897d'}
SCANS = {'on20170428_epoch1_HIP98505': ('epoch1_on', 'HIP98505'),
         'on20170428_epoch2_HIP98505': ('epoch2_on', 'HIP98505'),
         'on20170428_epoch3_HIP98505': ('epoch3_on', 'HIP98505')}
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 178257920
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
QS = tuple(4 + 8 * k for k in range(32))
PILOT_DOMAINS = tuple((native, q) for native in (170, 171, 172) for q in QS)
FULL_DOMAINS = tuple((native, q) for native in (170, 171, 172)
                     for q in range(256) if (native, q) not in ((170, 0), (172, 255)))
DOMAINS = tuple(key for key in FULL_DOMAINS if key not in PILOT_DOMAINS)
JOBS = {f'full20170428_epoch{epoch}_HIP98505_shard{shard:02d}':
        (f'epoch{epoch}_on', 'HIP98505', f'on20170428_epoch{epoch}_HIP98505', shard)
        for epoch in (1, 2, 3) for shard in range(7)}
STARTS = (0, 2, 4, 6, 8, 10, 12)
DC_CHANNELS = (178782208, 179830784, 180879360)
CAPS = {'CPU_cap_s_per_job': 600, 'wall_cap_s_per_job': 900,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3,
        'job_output_budget_bytes': 50 * 1024**2, 'total_output_budget_bytes': 21 * 50 * 1024**2,
        'workspace_cap_bytes': 8 * 1024**3}
MAP_FIELDS = ('frequency_hz_at_window_reference', 'maximum_robust_box_track_score',
              'winning_drift_hz_s', 'winning_drift_grid_index', 'winning_window_start_row',
              'winning_width_channels', 'valid_hypothesis_count', 'source_reference_channels',
              'drift_grid_hz_s', 'DC_clean_maximum_robust_box_track_score',
              'DC_clean_winning_drift_hz_s', 'DC_clean_winning_drift_grid_index',
              'DC_clean_winning_window_start_row', 'DC_clean_winning_width_channels',
              'DC_clean_valid_hypothesis_count')


def job_domains(job):
    return DOMAINS[JOBS[job][3] * 96:(JOBS[job][3] + 1) * 96]


def counts_for_job(job):
    domains = job_domains(job)
    dc_cores = sum(q in (127, 128) for _, q in domains)
    empty = sum(q == 128 for _, q in domains)
    n = len(domains)
    return {'maps': n, 'carrier_maximum_records': n * CORE,
            'valid_hypothesis_records': n * CORE * 2226,
            'normalization_records': n, 'score_audit_queries': n * 5,
            'score_audit_raw_power_cells': n * 5 * 4 * 503,
            'DC_affected_raw_full_core_crops': dc_cores,
            'expected_DC_clean_EMPTY_carriers': empty, 'decoded_rows_verified': 48,
            'expected_output_files_including_receipt': n * 7 + dc_cores + 3}


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
    require(len(FULL_DOMAINS) == 766 and len(DOMAINS) == 670 and len(PILOT_DOMAINS) == 96,
            'Exact complement of unchanged pilot domains required')
    return {'schema': 'SETI_S2017_FULL_ON_DUAL_BURST4_REMAINING_SCOPE_V1',
        'jobs': {job: {'scan_id': scan, 'primary_target': target, 'primary_scan_id': primary,
                      'shard_index': shard, 'original_acquisition_role': 'ON',
                      'domains': [{'native_chunk_index': n, 'core_q': q} for n, q in job_domains(job)],
                      'expected_counts': counts_for_job(job)}
                 for job, (scan, target, primary, shard) in JOBS.items()},
        'ON_scan_count': 3, 'same_target': 'HIP98505', 'independent_visits': 1,
        'remaining_domains_per_ON_scan': 670, 'reused_pilot_domains_per_ON_scan': 96,
        'complete_domains_per_ON_scan_after_merge': 766,
        'remaining_core_domains': [{'native_chunk_index': n, 'core_q': q,
                                  'reference_channel_interval_half_open': [n * COUNT + q * CORE,
                                                                            n * COUNT + (q + 1) * CORE]}
                                 for n, q in DOMAINS],
        'reused_pilot_domains': [{'native_chunk_index': n, 'core_q': q} for n, q in PILOT_DOMAINS],
        'domain_rule': 'native170q1..255; native171q0..255; native172q0..254; exclude pilot q4+8k k0..31 eachnative; ascending(native,q), consecutive96core shards',
        'new_maps': 2010, 'new_carrier_maximum_records': 2010 * CORE,
        'new_valid_hypothesis_records': 2010 * CORE * 2226,
        'source_rows_per_scan': 16, 'core_channels': CORE, 'halo_channels': HALO,
        'window_length_rows': 4, 'window_start_rows': list(STARTS), 'widths_channels': [1, 3],
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79},
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'valid_hypotheses_per_carrier': 2226,
        'preprocessing': 'unchanged detector.preprocess and _box_arrays on all16rows once/core; core4096 raw medians plus501 median residual/MAD/winsorized location',
        'normalization': 'all4096 static declared core channels; full16row original normalization; no DC masking in preprocessing',
        'reference_time': 'each winning window own first source row integration midpoint',
        'window_times_s': [0, TSAMP, 2 * TSAMP, 3 * TSAMP],
        'score_equation': 'sum of selected4 row standardized width-box terms / sqrt(4*width)',
        'rounding': 'np.rint complete absolute source mapping before subtracting raw crop origin',
        'winning_tie_order': 'window start ascending; width1 before3; drift index ascending; strict greater update independently for unrestricted and DC_clean maxima',
        'frozen_DC_source_channels': list(DC_CHANNELS),
        'DC_clean_condition': 'For each original hypothesis, reject from DC_clean maximum iff any chosen4row inclusive widthbox touches any frozen DC channel. Unrestricted scores unchanged. Every clean nonwinning alternative is retained as eligible in same original score traversal.',
        'DC_geometry_cache': 'Eligibility depends on(relative4rowtimes,carrier,drift,width) and is independent of absolute start row. Cache159x4096 perwidth once on affectedq127/q128 cores. Other cores are prospectively far enough; every valid hypothesis is clean and updates clean winner together with unrestricted winner.',
        'DC_affected_core_q': [127, 128], 'DC_affected_core_count_total': 18,
        'DC_clean_EMPTY_definition': 'No admissible original width/drift/window hypothesis; score=-inf float64, drift=nan float64, winningindex/window/width=-1 int16, admissiblecount=0 int64; expected only exact frozen DC reference channels.',
        'DC_clean_EMPTY_channels_per_ON_scan': list(DC_CHANNELS), 'expected_DC_clean_EMPTY_carriers_total': 9,
        'map_npz_fields': list(MAP_FIELDS), 'map_NPZ_budget_bytes': 340 * 1024,
        'normalization_JSON_budget_bytes': 4000,
        'audit_positions_per_core': ['unrestricted_first', 'unrestricted_midpoint', 'unrestricted_last',
                                     'unrestricted_core_max', 'DC_clean_core_max'],
        'score_audit_queries_total': 2010 * 5, 'score_audit_raw_power_cells_total': 2010 * 5 * 4 * 503,
        'audit_raw_shape': [4, 503], 'audit_raw_offsets_inclusive': [-251, 251],
        'audit_NPZ_fields': ['raw_power', 'absolute_time_rows', 'rounded_absolute_centers', 'standardized_row_box_sums'],
        'audit_NPZ_budget_bytes': 11000, 'audit_score_ATOL': 1e-7, 'audit_score_RTOL': 1e-10,
        'DC_full_crop_shape': [16, CORE + 2 * HALO], 'DC_full_crop_dtype': '<f4',
        'DC_full_crop_NPZ_fields': ['raw_power_full16x12096', 'absolute_time_rows', 'source_channel_interval_half_open'],
        'DC_full_crop_NPZ_budget_bytes': 800 * 1024,
        'other_JSON_total_budget_bytes': 4 * 1024**2,
        'shard_rankings_or_TOP3_context': False, 'later_global_merge_required': True,
        'pilot_maps_rerun': False, 'pilot_clean_equals_unrestricted_by_frozen_geometry': True,
        'new_bandwidth_or_observation': False, 'exposed_data_exploratory': True,
        'blind_validation': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'protected2016_data_opened': False, 'injection_arrays_opened': False,
        'previous_outputs_modified': False, 'new_telescope_HTTP_requests': 0, 'cost_DKK': 0,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', **CAPS}


def contract(root, scope):
    require(all(scope.get(k) == v for k, v in method_contract().items()), 'Frozen full dual method/resource differs')
    pins = {}
    for rec in scope['text_code_pins']:
        path = confined(root, rec['path'])
        require(path.suffix in ('.py', '.json', '.md', '.txt') and byte_pin(root, path) == rec,
                'Text/code pin differs')
        pins[rec['path']] = rec['sha256']
    require(all(pins.get(path) == sha for path, sha in PINS.items()), 'Original source/pilot/detector pins differ')
    require(pins.get(BASE + '/driver.py') == digest(Path(__file__).resolve()), 'Full driver self pin differs')
    require(scope['source_compacts'] == source_records(root)
            == read_json(root / PILOT / 'SCOPE.json')['source_compacts'], 'Authenticated reused source records differ')
    for primary, (scan, target) in SCANS.items():
        rec = read_json(root / PILOT / 'results' / primary / 'EXECUTION_RECEIPT.json')
        require(rec['status'] == 'COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
                and rec['scan_id'] == scan and rec['counts']['maps'] == 96,
                'Reused pilot must remain complete')
        manifest = read_json(root / PILOT / 'results' / primary / 'MAPS.json')
        require(manifest['scan_id'] == scan and len(manifest['records']) == 96
                and [(r['native_chunk_index'], r['core_q']) for r in manifest['records']] == list(PILOT_DOMAINS),
                'Pilot map identity/domain differs')
    require(len(scope['pilot_map_manifests']) == 3
            and all(byte_pin(root, confined(root, p['path'])) == p for p in scope['pilot_map_manifests']),
            'Exact pilot map manifest pins required')


def source_records(root):
    midpoint, adjacent = read_json(root / MIDPOINT), read_json(root / ADJACENT)
    acquisitions = {171: read_json(root / ACQ171), 170: read_json(root / ACQ_ADJACENT),
                    172: read_json(root / ACQ_ADJACENT)}
    result = []
    for scan, target in SCANS.values():
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
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008),
            'Supported bitshuffle decoder required')
    detector = module('full_on_unchanged_detector', root / DETECTOR)
    scan_id, target, primary, shard = JOBS[job]
    domains = job_domains(job)
    records = [r for r in scope['source_compacts'] if r['scan_id'] == scan_id]
    require([r['native_chunk_index'] for r in records] == [170, 171, 172], 'Own authenticated source triplet required')
    source_pins = [byte_pin(root, confined(root, rec['path'])) for rec in records]
    require(all(pin['bytes'] == rec['bytes'] and pin['sha256'] == rec['sha256']
                for rec, pin in zip(records, source_pins)), 'All source compacts require pin before any payload opening')
    power = np.empty((16, 3 * COUNT), dtype='<f4')
    for rec in records:
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
                        and hashlib.sha256(values.tobytes()).hexdigest() == row['decoded_sha256'],
                        'Decoded float32 row differs')
                power[row['time_row'], offset:offset + COUNT] = values
    header = records[0]['original_header']
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 159), np.arange(4) * TSAMP
    require(drifts[79] == 0., 'Central drift must be exact zero')
    maps, audits = [], []
    clean_empty_total, clean_valid_total, clean_alternative_total = 0, 0, 0

    def selected_tuple(native, q, value, index, winner_kind):
        prefix = 'DC_clean_' if winner_kind == 'DC_clean' else ''
        start = int(value[prefix + 'winning_window_start_row'][index])
        score = float(value[prefix + 'maximum_robust_box_track_score'][index])
        require(start in STARTS and np.isfinite(score), 'EMPTY tuple cannot be audited')
        width = int(value[prefix + 'winning_width_channels'][index])
        drift = float(value[prefix + 'winning_drift_hz_s'][index])
        fref = float(value['frequency_hz_at_window_reference'][index])
        centers = np.rint((fref - FCH1) / DF + drift * times / DF).astype(np.int64)
        radius = width // 2
        touched = np.abs(centers[:, None] - np.asarray(DC_CHANNELS)[None, :]) <= radius
        result = {'primary_id': job, 'primary_scan_id': primary, 'primary_target': target, 'scan_id': scan_id,
                  'original_acquisition_role': 'ON', 'winner_kind': winner_kind,
                  'native_chunk_index': native, 'core_q': q, 'map_id': '%s_native%d_q%03d' % (scan_id, native, q),
                  'carrier_index_in_core': int(index), 'source_reference_channel': int(value['source_reference_channels'][index]),
                  'frequency_hz_at_window_reference': fref, 'window_start_row': start, 'window_length_rows': 4,
                  'window_source_rows': list(range(start, start + 4)),
                  'reference_time_mjd': header['tstart'] + (start + .5) * TSAMP / 86400,
                  'drift_grid_index': int(value[prefix + 'winning_drift_grid_index'][index]),
                  'drift_hz_s': drift, 'width_channels': width, 'score': score,
                  'rounded_absolute_centers': centers.tolist(),
                  'width_box_source_channels_inclusive': [[int(c - radius), int(c + radius)] for c in centers],
                  'frozen_DC_source_channels': list(DC_CHANNELS),
                  'eligible_DC_untouched': bool(not touched.any()),
                  'rows_intersecting_any_frozen_DC': int(touched.any(axis=1).sum()),
                  'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touched.any(axis=1)).tolist(),
                  'valid_hypothesis_count': int(value[prefix + 'valid_hypothesis_count'][index])}
        require(winner_kind != 'DC_clean' or result['eligible_DC_untouched'], 'Selected clean winner contacts DC')
        return result

    def audit(kind, native, q, value, index, winner_kind, boxes, crop0, normalization):
        chosen = selected_tuple(native, q, value, index, winner_kind)
        rows = np.arange(chosen['window_start_row'], chosen['window_start_row'] + 4, dtype=np.int64)
        centers = np.asarray(chosen['rounded_absolute_centers'], dtype=np.int64)
        sums = boxes[chosen['width_channels']][0][rows, centers - crop0 - chosen['width_channels'] // 2]
        absolute = centers[:, None] + np.arange(-251, 252)[None, :]
        require(absolute.min() >= C0 and absolute.max() < C0 + 3 * COUNT, 'Audit leaves authenticated triplet')
        require(np.isclose(sums.sum() / np.sqrt(4 * chosen['width_channels']), chosen['score'], atol=1e-7, rtol=1e-10),
                'Winning fourrow arithmetic differs')
        query_id = 'native%d_q%03d_%s' % (native, q, kind)
        capsule = store_npz(np, root, out / (query_id + '_raw4x503.npz'),
                            {'raw_power': power[rows[:, None], absolute - C0], 'absolute_time_rows': rows,
                             'rounded_absolute_centers': centers, 'standardized_row_box_sums': sums}, 11000)
        audits.append({'query_id': query_id, 'query_kind': kind, 'winner_kind': winner_kind,
                       'native_chunk_index': native, 'core_q': q, 'map_id': chosen['map_id'],
                       'selected_tuple': chosen, 'normalization': normalization, 'capsule': capsule})

    for native, q in domains:
        first = native * COUNT + q * CORE
        channels = np.arange(first, first + CORE, dtype=np.int64)
        frequencies, crop0 = FCH1 + DF * channels, first - HALO
        crop = power[:, crop0 - C0:first + CORE + HALO - C0].astype(np.float64)
        require(crop.shape == (16, CORE + 2 * HALO), 'Full16row contiguous crop required')
        scan = detector.Scan(scan_id, 'ON', crop, header['tstart'], TSAMP, FCH1, DF, crop0, channels)
        z, mask, normalization = detector.preprocess(scan, cfg)
        require(mask.all(), 'Original no-mask preprocessing required')
        boxes = detector._box_arrays(z, mask, cfg)
        base = (frequencies - FCH1) / DF
        best = np.full(CORE, -np.inf, dtype=np.float64)
        winning_start = np.full(CORE, -1, dtype=np.int16)
        winning_width = np.zeros(CORE, dtype=np.int16)
        winning_drift_index = np.full(CORE, -1, dtype=np.int16)
        winning_drift = np.full(CORE, np.nan, dtype=np.float64)
        valid_count = np.zeros(CORE, dtype=np.int64)
        clean_best = np.full(CORE, -np.inf, dtype=np.float64)
        clean_start = np.full(CORE, -1, dtype=np.int16)
        clean_width = np.full(CORE, -1, dtype=np.int16)
        clean_drift_index = np.full(CORE, -1, dtype=np.int16)
        clean_drift = np.full(CORE, np.nan, dtype=np.float64)
        clean_count = np.zeros(CORE, dtype=np.int64)
        affected = q in (127, 128)
        allowed = {}
        if affected:
            for width in (1, 3):
                clean = np.ones((159, CORE), dtype=bool)
                for t in times:
                    centers = np.rint(base[None, :] + drifts[:, None] * t / DF).astype(np.int64)
                    for dc in DC_CHANNELS:
                        clean &= np.abs(centers - dc) > width // 2
                allowed[width] = clean
        else:
            require(min(abs(int(channels[0]) - dc) for dc in DC_CHANNELS) > 80
                    and min(abs(int(channels[-1]) - dc) for dc in DC_CHANNELS) > 80,
                    'Nonaffected domain must have prospective complete support distance')
        # Traversal and unrestricted score arithmetic are the original scientific tie order.
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
                        if affected:
                            admissible = valid & allowed[width][begin:begin + len(ds), lo:hi]
                            clean_count[lo:hi] += admissible.sum(axis=0)
                            clean_scores = np.where(admissible, scores, -np.inf)
                            clean_arg = clean_scores.argmax(axis=0)
                            clean_values = clean_scores[clean_arg, np.arange(hi - lo)]
                            clean_improve = clean_values > clean_best[lo:hi]
                            clean_locations = np.arange(lo, hi)[clean_improve]
                            clean_best[clean_locations] = clean_values[clean_improve]
                            clean_start[clean_locations] = start_row
                            clean_width[clean_locations] = width
                            clean_drift_index[clean_locations] = begin + clean_arg[clean_improve]
                            clean_drift[clean_locations] = ds[clean_arg[clean_improve]]
                        else:
                            clean_count[lo:hi] += valid.sum(axis=0)
                            clean_best[locations] = values[improve]
                            clean_start[locations] = start_row
                            clean_width[locations] = width
                            clean_drift_index[locations] = begin + arg[improve]
                            clean_drift[locations] = ds[arg[improve]]
        require(np.all(valid_count == 2226) and np.isfinite(best).all()
                and np.isin(winning_start, STARTS).all() and np.isin(winning_width, (1, 3)).all(),
                'Complete original family required')
        empty = clean_count == 0
        expected_empty = np.isin(channels, DC_CHANNELS)
        require(np.array_equal(empty, expected_empty) and np.isneginf(clean_best[empty]).all()
                and np.isnan(clean_drift[empty]).all() and (clean_start[empty] == -1).all()
                and (clean_width[empty] == -1).all() and (clean_drift_index[empty] == -1).all()
                and np.isfinite(clean_best[~empty]).all() and (clean_count <= valid_count).all()
                and (clean_best[~empty] <= best[~empty]).all(), 'Exact clean admissibility/EMPTY contract differs')
        if not affected:
            require(np.array_equal(clean_best, best) and np.array_equal(clean_count, valid_count)
                    and np.array_equal(clean_start, winning_start) and np.array_equal(clean_width, winning_width)
                    and np.array_equal(clean_drift_index, winning_drift_index)
                    and np.array_equal(clean_drift, winning_drift), 'Unaffected original/clean maxima must be identical')
        clean_empty_total += int(empty.sum())
        clean_valid_total += int(clean_count.sum())
        clean_alternative_total += int(((clean_best != best) | (clean_start != winning_start)
                                      | (clean_width != winning_width) | (clean_drift_index != winning_drift_index)).sum())
        value = {'frequency_hz_at_window_reference': frequencies, 'maximum_robust_box_track_score': best,
                 'winning_drift_hz_s': winning_drift, 'winning_drift_grid_index': winning_drift_index,
                 'winning_window_start_row': winning_start, 'winning_width_channels': winning_width,
                 'valid_hypothesis_count': valid_count, 'source_reference_channels': channels, 'drift_grid_hz_s': drifts,
                 'DC_clean_maximum_robust_box_track_score': clean_best, 'DC_clean_winning_drift_hz_s': clean_drift,
                 'DC_clean_winning_drift_grid_index': clean_drift_index, 'DC_clean_winning_window_start_row': clean_start,
                 'DC_clean_winning_width_channels': clean_width, 'DC_clean_valid_hypothesis_count': clean_count}
        map_id = '%s_native%d_q%03d' % (scan_id, native, q)
        map_pin = store_npz(np, root, out / (map_id + '.npz'), value, 340 * 1024)
        compact = dict(normalization)
        require(compact.pop('normalization_source_channels') == channels.tolist(), 'Normalization interval differs')
        compact['normalization_source_channel_interval_half_open'] = [first, first + CORE]
        norm_path = out / (map_id + '_normalization.json')
        save(norm_path, compact)
        norm_pin = byte_pin(root, norm_path)
        require(norm_pin['bytes'] <= 4000, 'Normalization budget exceeded')
        record = {'map_id': map_id, 'scan_id': scan_id, 'primary_id': job, 'primary_scan_id': primary,
                  'original_acquisition_role': 'ON', 'native_chunk_index': native, 'core_q': q, **map_pin,
                  'normalization': norm_pin, 'reference_channel_interval_half_open': [first, first + CORE],
                  'loaded_channel_interval_half_open': [crop0, first + CORE + HALO],
                  'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 2226,
                  'combined_window_start_rows': list(STARTS), 'DC_affected_core': affected,
                  'DC_clean_EMPTY_count': int(empty.sum()), 'DC_clean_valid_hypothesis_records': int(clean_count.sum())}
        if affected:
            record['DC_full_raw_core_crop'] = store_npz(np, root, out / (map_id + '_raw16x12096.npz'),
                {'raw_power_full16x12096': power[:, crop0 - C0:first + CORE + HALO - C0].copy(),
                 'absolute_time_rows': np.arange(16, dtype=np.int64),
                 'source_channel_interval_half_open': np.asarray([crop0, first + CORE + HALO], dtype=np.int64)}, 800 * 1024)
        maps.append(record)
        raw_max = int(np.lexsort((channels, -best))[0])
        clean_max = int(np.lexsort((channels, -clean_best))[0])
        for kind, index in (('first', 0), ('midpoint', 2048), ('last', 4095), ('core_max', raw_max)):
            audit(kind, native, q, value, index, 'unrestricted', boxes, crop0, norm_pin)
        audit('clean_core_max', native, q, value, clean_max, 'DC_clean', boxes, crop0, norm_pin)
        del z, mask, boxes, window_boxes, scan, crop, allowed
        output_guard(root, out, workspace=len(maps) % 16 == 0)
        if len(maps) % 8 == 0:
            print(json.dumps({'job': job, 'completed_dual_maps': len(maps), 'expected': len(domains)}), flush=True)
    counts = counts_for_job(job)
    require(len(maps) == counts['maps'] and len(audits) == counts['score_audit_queries']
            and clean_empty_total == counts['expected_DC_clean_EMPTY_carriers'], 'Frozen shard count differs')
    save(out / 'MAPS.json', {'schema': 'SETI_FULL_ON_DUAL_BURST4_MAPS_V1', 'primary_id': job,
                           'primary_scan_id': primary, 'scan_id': scan_id, 'records': maps})
    save(out / 'SCORE_AUDITS.json', {'schema': 'SETI_FULL_ON_DUAL_BURST4_SCORE_AUDITS_V1', 'primary_id': job,
                                   'primary_scan_id': primary, 'scan_id': scan_id, 'records': audits})
    for rec, pin in zip(records, source_pins):
        offset = rec['source_channel0'] - C0
        for row in rec['decoded_rows']:
            require(hashlib.sha256(power[row['time_row'], offset:offset + COUNT].tobytes()).hexdigest()
                    == row['decoded_sha256'], 'Loaded decoded row changed')
        require(byte_pin(root, confined(root, rec['path'])) == pin, 'Raw compact byte pin changed')
    return {'counts': counts, 'DC_clean_EMPTY_carriers': clean_empty_total,
            'DC_clean_valid_hypothesis_records': clean_valid_total,
            'carrier_tuples_differing_between_clean_and_unrestricted': clean_alternative_total,
            'source_compact_pre_and_post_pins': source_pins, 'decoded_source_rows': records,
            'decoded_row_SHA_checks_before': 48, 'decoded_row_SHA_checks_after': 48,
            'original_scan_tstart_mjd': header['tstart'],
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
        print(json.dumps({'status': 'PASS_METADATA_ONLY_FULL_ON_DUAL_BURST4_SCOPE_NO_NUMERICAL_IMPORT_OR_SOURCE_ARRAYS',
                          'job': args.job, 'scope': byte_pin(root, scope_path), 'counts': counts_for_job(args.job),
                          'installed_package_versions': runtime_versions()}))
        return
    require(args.run and digest(scope_path) == args.scope_sha256, 'Root --run and exact scope SHA required')
    freeze_path = confined(root, args.freeze)
    require(args.freeze_sha256 and digest(freeze_path) == args.freeze_sha256, 'Exact public freeze hash required before source payload opening')
    freeze = read_json(freeze_path)
    require(freeze['status'] == 'PASS_PUBLIC_FREEZE_FULL_ON_DUAL_BURST4_SCOPE_READBACK'
            and freeze['scope_sha256'] == args.scope_sha256
            and freeze['driver_sha256'] == digest(Path(__file__).resolve())
            and isinstance(freeze.get('public_commit'), str) and len(freeze['public_commit']) == 40,
            'Public readback freeze/science code differs')
    go_path = confined(root, args.root_go)
    require(args.root_go_sha256 and digest(go_path) == args.root_go_sha256, 'Exact reviewed root GO hash required')
    go = read_json(go_path)
    require(go['status'] == 'GO_2010_NEW_FULL_ON_DUAL_BURST4_MAPS' and go['scope_sha256'] == args.scope_sha256
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
        require(len(pins) == counts_for_job(args.job)['expected_output_files_including_receipt'] - 1,
                'Frozen per-shard dual maps/audits/crops/JSON inventory differs')
        receipt = {'schema': 'SETI_FULL_ON_DUAL_BURST4_SHARD_EXECUTION_V1',
            'status': 'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY',
            'primary_id': args.job, 'scan_id': JOBS[args.job][0], 'primary_target': JOBS[args.job][1],
            'primary_scan_id': JOBS[args.job][2], 'shard_index': JOBS[args.job][3],
            'original_acquisition_role': 'ON', 'scope_sha256': args.scope_sha256,
            'driver_sha256': digest(Path(__file__).resolve()), 'root_GO_pin': byte_pin(root, go_path),
            'public_freeze_pin': byte_pin(root, freeze_path), 'public_freeze_commit': freeze['public_commit'],
            **result, 'output_byte_pins': pins, 'science_slot': slot,
            'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, **CAPS,
            'source_bytes_unchanged': True, 'detector_family_new': False, 'ON_subject_application_new': False,
            'newly_searched_remaining_domains': True, 'per_hypothesis_DC_clean_maximum_new': True, 'new_telescope_HTTP_requests': 0,
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
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_FULL_ON_DUAL_BURST4_SHARD_EXECUTION_V1',
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
