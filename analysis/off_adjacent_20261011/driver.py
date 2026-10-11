"""New original-OFF 170/171/172 maps using the unchanged detector.

Import and --check-only read text only. Numerical work requires --run plus the
exact prospective scope hash. Each target is ranked once over all 512 cores.
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

BASE = 'analysis/off_adjacent_20261011'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
MIDPOINT = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
FEASIBILITY = 'continuation_20261011/metadata/control_target_adjacent_feasibility/NEXT_QUEUE_FEASIBILITY.json'
PINS = {
    DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
    ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
}
JOBS = {'primary20170428_HIP97319': ('epoch1_off', 'HIP97319'),
        'primary20170428_HIP97461': ('epoch2_off', 'HIP97461'),
        'primary20170428_HIP97663': ('epoch3_off', 'HIP97663')}
CORE, HALO, COUNT, C0 = 4096, 4000, 1048576, 178257920
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DOMAINS = tuple([(170, q) for q in range(1, 256)] + [(171, 0), (171, 255)]
                + [(172, q) for q in range(255)])
CAPS = {'CPU_cap_s_per_job': 1800, 'wall_cap_s_per_job': 1800,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3,
        'job_output_budget_bytes': 200 * 1024**2,
        'total_output_budget_bytes': 600 * 1024**2}
COUNTS = {'maps': 512, 'carrier_maximum_records': 2097152,
          'valid_hypothesis_records': 3292528640, 'normalization_records': 512,
          'score_audit_queries': 2051, 'score_audit_raw_power_cells': 16506448,
          'TOP20_entries': 20, 'TOP3_entries': 3, 'decoded_rows_verified': 48}


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
    return json.loads(Path(path).read_bytes(),
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Relative confined path required')
    return path


def byte_pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False,
                                 allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def method_contract():
    return {'schema': 'SETI_ORIGINAL_OFF_ADJACENT_GLOBAL512_SCOPE_V1',
        'jobs': {job: {'scan_id': scan, 'primary_target': target,
                      'original_acquisition_role': 'OFF'} for job, (scan, target) in JOBS.items()},
        'core_domains': [{'native_chunk_index': n, 'core_q': q,
                         'reference_channel_interval_half_open':
                         [n * COUNT + q * CORE, n * COUNT + (q + 1) * CORE]}
                        for n, q in DOMAINS],
        'total_new_maps': 1536, 'cores_per_target': 512,
        'core_channels': CORE, 'halo_channels': HALO, 'rows_per_scan': 16,
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'widths_channels': [1, 3], 'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785},
        'valid_hypotheses_per_carrier': 1570,
        'reference_time': 'each primary own first integration midpoint',
        'rounding_rule': 'np.rint complete absolute source channel mapping before subtracting crop0',
        'normalization_method': 'unchanged detector float64 core median/MAD/winsorized location',
        'normalization_channels': 'all4096 declared reference core channels; contiguous interval metadata',
        'running_median_channels': 501, 'masks': None, 'data_selected_exclusions': [],
        'ranking_rule': 'all512 new core carrier maxima per target; score descending, absolute channel ascending; greedy distance>3; one TOP20 and first3 TOP3',
        'audit_carrier_indices': [0, 2048, 4095, 'core_max'], 'audit_capsule_shape': [16, 503],
        'audit_offsets_inclusive': [-251, 251], 'extra_global_TOP3_audits': 3,
        'audit_score_ATOL': 1e-7, 'audit_score_RTOL': 1e-10,
        'map_NPZ_budget_bytes': 181000, 'normalization_JSON_budget_bytes': 4000,
        'audit_NPZ_budget_bytes': 34000, 'other_JSON_total_budget_bytes': 10 * 1024**2,
        'expected_counts_per_target': COUNTS, **CAPS,
        'novelty': 'new originalOFF/native/core detector families from existing real observations',
        'excluded_outer_cores': [[170, 0], [172, 255]],
        'excluded_prior_native171': 'all q1..254 including prior injection baselines64/128/192',
        'new_observation_visit': False, 'independent_blind_replication': False,
        'OFF_veto_applied': False, 'qualified_SETI_detection': False,
        'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
        'new_telescope_HTTP_requests': 0, 'cost_DKK': 0}


def source_records(root):
    """Derive all immutable OFF source declarations from original text records."""
    midpoint, adjacent = read_json(root / MIDPOINT), read_json(root / ADJACENT)
    acquisitions = {171: read_json(root / ACQ171), 170: read_json(root / ACQ_ADJACENT),
                    172: read_json(root / ACQ_ADJACENT)}
    result = []
    for scan, target in JOBS.values():
        original = next(s for s in midpoint['sources'] if s['label'] == scan)
        header = original['current_header']['data_attributes']
        require(original['role'] == 'off' and header['source_name'] == target
                and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF
                and header['tsamp'] == TSAMP, 'Original OFF header differs')
        for native in (170, 171, 172):
            items = midpoint['sources'] if native == 171 else adjacent['by_native_chunk'][str(native)]['sources']
            item = next(s for s in items if s['label'] == scan)
            require(item['current_header'] == original['current_header']
                    and item['url'] == original['url'] and item['etag'] == original['etag']
                    and item['role'] == 'off', 'Across-band source identity/header differs')
            rec = next(r for r in acquisitions[native]['decoded_files']
                       if r['scan_id'] == scan and (native == 171 or r['native_chunk_index'] == native))
            require(rec['source_channel0'] == native * COUNT and rec['shape'] == [16, 1, COUNT]
                    and [r['time_row'] for r in rec['decoded_rows']] == list(range(16)),
                    'Original compact geometry/rows differ')
            parent = Path(ACQ171 if native == 171 else ACQ_ADJACENT).parent
            result.append({'native_chunk_index': native, 'scan_id': scan, 'primary_target': target,
                           'original_acquisition_role': 'OFF', 'path': (parent / rec['array_file']).as_posix(),
                           'bytes': rec['bytes'], 'sha256': rec['file_sha256'],
                           'source_channel0': rec['source_channel0'], 'shape': rec['shape'],
                           'decoded_rows': rec['decoded_rows'], 'original_header': header,
                           'original_source_url': item['url'], 'original_source_etag': item['etag']})
    return result


def contract(root, scope):
    require(all(scope.get(k) == v for k, v in method_contract().items()), 'Prospective scientific/resource scope differs')
    for rec in scope['text_code_pins']:
        path = confined(root, rec['path'])
        require(path.suffix in ('.py', '.json', '.md', '.txt') and byte_pin(root, path) == rec,
                'Text/code byte pin differs: ' + rec['path'])
    pins = {r['path']: r['sha256'] for r in scope['text_code_pins']}
    require(all(pins.get(path) == sha for path, sha in PINS.items()), 'Original text/dependency identities differ')
    require(pins.get(BASE + '/driver.py') == digest(Path(__file__).resolve()), 'Driver self pin differs')
    require(scope['source_compacts'] == source_records(root), 'Source declarations differ from original manifests/acquisitions')
    feasibility = read_json(root / FEASIBILITY)
    require(feasibility['next_queue']['total_new_maps'] == 1536
            and feasibility['next_queue']['new_cores_per_target'] == 512, 'Novelty/domain evidence differs')


def store_npz(np, root, path, values, bound):
    with path.open('xb') as stream:
        np.savez(stream, **values)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_size <= bound, 'NPZ output bound exceeded')
    return byte_pin(root, path)


def runtime_versions():
    result = {'Python': sys.version.split()[0]}
    for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin'):
        result[name] = importlib.metadata.version(name)
    return result


def output_guard(out):
    require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= CAPS['job_output_budget_bytes'],
            '200MiB job output cap exceeded')


def run(root, scope, job, out):
    import numpy as np
    import h5py
    import hdf5plugin
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008),
            'Supported bitshuffle decoder required')
    detector = module('off_adjacent_original_detector', root / DETECTOR)
    scan_id, target = JOBS[job]
    records = [r for r in scope['source_compacts'] if r['scan_id'] == scan_id]
    require([r['native_chunk_index'] for r in records] == [170, 171, 172], 'Complete own contiguous triplet required')
    power = np.empty((16, 3 * COUNT), dtype='<f4')
    source_pins, row_checks = [], []
    for record in records:
        path = confined(root, record['path'])
        pin = byte_pin(root, path)
        require(pin['bytes'] == record['bytes'] and pin['sha256'] == record['sha256'], 'Whole compact source pin differs')
        source_pins.append(pin)
        offset = record['source_channel0'] - C0
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == record['source_channel0']
                    and data.attrs['original_source_url'] == record['original_source_url']
                    and data.attrs['original_source_etag'] == record['original_source_etag'], 'Actual compact provenance differs')
            for row in record['decoded_rows']:
                values = data[row['time_row'], 0, :]
                require(values.dtype.str == '<f4' and np.isfinite(values).all() and np.all(values >= 0)
                        and hashlib.sha256(values.tobytes()).hexdigest() == row['decoded_sha256'],
                        'Decoded float32 source row differs')
                power[row['time_row'], offset:offset + COUNT] = values
        row_checks.append({'source': pin, 'decoded_rows': record['decoded_rows'], 'rows_verified': 16})
    header = records[0]['original_header']
    reference_mjd = header['tstart'] + TSAMP / (2 * 86400)
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 785), np.arange(16) * TSAMP
    maps, audits, saved, row_sums = [], [], {}, {}

    def tuple_record(native, q, result, index, rank=None):
        value = {'primary_id': job, 'primary_target': target, 'scan_id': scan_id,
                 'original_acquisition_role': 'OFF', 'native_chunk_index': native, 'core_q': q,
                 'map_id': '%s_native%d_q%03d' % (scan_id, native, q),
                 'carrier_index_in_core': int(index),
                 'reference_source_channel': int(result['source_reference_channels'][index]),
                 'frequency_hz_at_own_first_midpoint': float(result['frequency_hz_at_tref'][index]),
                 'reference_time_mjd': reference_mjd,
                 'drift_grid_index': int(np.flatnonzero(drifts == result['winning_drift_hz_s'][index])[0]),
                 'drift_hz_s': float(result['winning_drift_hz_s'][index]),
                 'width_channels': int(result['winning_width_channels'][index]),
                 'score': float(result['maximum_robust_box_track_score'][index])}
        if rank is not None:
            value['rank'] = rank
        return value

    def audit(query_id, kind, native, q, result, index, sums, normalization, rank=None):
        selected = tuple_record(native, q, result, index, rank)
        centers = np.rint((selected['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                          + selected['drift_hz_s'] * times / DF).astype(np.int64)
        absolute = centers[:, None] + np.arange(-251, 252)[None, :]
        require(absolute.min() >= C0 and absolute.max() < C0 + 3 * COUNT, 'Raw503 capsule outside acquired triplet')
        raw = power[np.arange(16)[:, None], absolute - C0]
        require(np.isclose(sums.sum() / np.sqrt(16 * selected['width_channels']), selected['score'],
                           atol=1e-7, rtol=1e-10), 'Cached row boxes differ from winning score')
        capsule = store_npz(np, root, out / (query_id + '_raw503.npz'),
                            {'raw_power': raw, 'rounded_absolute_centers': centers,
                             'standardized_row_box_sums': sums}, 34000)
        audits.append({'query_id': query_id, 'query_kind': kind, 'native_chunk_index': native,
                       'core_q': q, 'map_id': selected['map_id'], 'selected_tuple': selected,
                       'normalization': normalization, 'capsule': capsule})

    for native, q in DOMAINS:
        first = native * COUNT + q * CORE
        channels = np.arange(first, first + CORE, dtype=np.int64)
        crop0 = first - HALO
        crop = power[:, crop0 - C0:first + CORE + HALO - C0].astype(np.float64)
        require(crop.shape == (16, CORE + 2 * HALO), 'Full contiguous raw crop required')
        scan = detector.Scan(scan_id, 'OFF', crop, header['tstart'], TSAMP, FCH1, DF, crop0, channels)
        result, arrays = detector.search_scan(scan, FCH1 + DF * channels, times, drifts, cfg)
        require(result['role'] == 'OFF' and np.all(result['valid_hypothesis_count'] == 1570)
                and np.isfinite(result['maximum_robust_box_track_score']).all(), 'Complete 4096carrier family required')
        result['source_reference_channels'] = channels
        map_id = '%s_native%d_q%03d' % (scan_id, native, q)
        archive = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
        archive['drift_grid_hz_s'] = drifts
        map_pin = store_npz(np, root, out / (map_id + '.npz'), archive, 181000)
        normalization = dict(result['normalization'])
        require(normalization.pop('normalization_source_channels') == channels.tolist(), 'Normalization interval differs')
        normalization['normalization_source_channel_interval_half_open'] = [first, first + CORE]
        norm_path = out / (map_id + '_normalization.json')
        save(norm_path, normalization)
        norm_pin = byte_pin(root, norm_path)
        require(norm_pin['bytes'] <= 4000, 'Compact row-normalization budget exceeded')
        maps.append({'map_id': map_id, 'scan_id': scan_id, 'primary_id': job,
                     'original_acquisition_role': 'OFF', 'native_chunk_index': native, 'core_q': q,
                     **map_pin, 'normalization': norm_pin,
                     'reference_channel_interval_half_open': [first, first + CORE],
                     'loaded_channel_interval_half_open': [crop0, first + CORE + HALO],
                     'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 1570})
        # Look up the already searched winning tuple in detector box arrays.
        sums = np.empty((CORE, 16), dtype=np.float64)
        centers = np.rint(arrays[1][:, None] + result['winning_drift_hz_s'][:, None]
                          * times[None, :] / DF).astype(np.int64)
        for width in (1, 3):
            chosen = result['winning_width_channels'] == width
            for row in range(16):
                sums[chosen, row] = arrays[0][width][0][row, centers[chosen, row] - crop0 - width // 2]
        row_sums[native, q] = sums
        saved[native, q] = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
        maximum = int(np.lexsort((channels, -result['maximum_robust_box_track_score']))[0])
        for kind, index in (('first', 0), ('midpoint', 2048), ('last', 4095), ('core_max', maximum)):
            audit('native%d_q%03d_%s' % (native, q, kind), kind, native, q, result, index, sums[index], norm_pin)
        del result, arrays, scan, crop, centers
        output_guard(out)
        if len(maps) % 16 == 0:
            print(json.dumps({'job': job, 'completed_core_maps': len(maps), 'expected': 512}), flush=True)

    flat_channels = np.concatenate([saved[key]['source_reference_channels'] for key in DOMAINS])
    flat_scores = np.concatenate([saved[key]['maximum_robust_box_track_score'] for key in DOMAINS])
    selected = []
    for index in np.lexsort((flat_channels, -flat_scores)):
        channel = int(flat_channels[index])
        if any(abs(channel - old['reference_source_channel']) <= 3 for old in selected):
            continue
        map_index, carrier = divmod(int(index), CORE)
        native, q = DOMAINS[map_index]
        selected.append(tuple_record(native, q, saved[native, q], carrier, len(selected) + 1))
        if len(selected) == 20:
            break
    require(len(selected) == 20, 'Target-global TOP20 incomplete')
    for name, values in (('TOP20.json', selected), ('TOP3.json', selected[:3])):
        save(out / name, {'schema': 'SETI_ORIGINAL_OFF_TARGET_GLOBAL512_RANKS_V1', 'primary_id': job,
             'scan_id': scan_id, 'original_acquisition_role': 'OFF', 'reference_time_mjd': reference_mjd,
             'selection_rule': scope['ranking_rule'], 'records': values})
    for chosen in selected[:3]:
        native, q, index = chosen['native_chunk_index'], chosen['core_q'], chosen['carrier_index_in_core']
        audit('global_top%02d' % chosen['rank'], 'global_top3', native, q, saved[native, q], index,
              row_sums[native, q][index], next(r['normalization'] for r in maps
                                            if (r['native_chunk_index'], r['core_q']) == (native, q)), chosen['rank'])
    require(len(maps) == 512 and len(audits) == 2051, 'Prospective map/audit count differs')
    save(out / 'MAPS.json', {'schema': 'SETI_ORIGINAL_OFF_ADJACENT_MAPS_V1', 'primary_id': job,
                            'scan_id': scan_id, 'records': maps})
    save(out / 'SCORE_AUDITS.json', {'schema': 'SETI_ORIGINAL_OFF_ADJACENT_SCORE_AUDITS_V1',
                                   'primary_id': job, 'scan_id': scan_id, 'records': audits})
    for record, pin in zip(records, source_pins):
        offset = record['source_channel0'] - C0
        for row in record['decoded_rows']:
            require(hashlib.sha256(power[row['time_row'], offset:offset + COUNT].tobytes()).hexdigest()
                    == row['decoded_sha256'], 'Decoded source row changed during search')
        require(byte_pin(root, confined(root, record['path'])) == pin, 'Source compact changed during search')
    return {'counts': COUNTS, 'source_compact_pre_and_post_pins': source_pins,
            'decoded_source_row_checks': row_checks, 'decoded_row_SHA_checks_before': 48,
            'decoded_row_SHA_checks_after': 48, 'own_primary_reference_time_mjd': reference_mjd,
            'runtime_versions': {**runtime_versions(), 'HDF5': h5py.version.hdf5_version}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/scope.json')
    parser.add_argument('--job', choices=tuple(JOBS), required=True)
    parser.add_argument('--scope-sha256')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    scope = read_json(scope_path)
    contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_TEXT_ONLY_SCOPE_NO_NUMERICAL_IMPORT_OR_SOURCE_OPEN',
                          'job': args.job, 'scope': byte_pin(root, scope_path), 'counts': COUNTS,
                          'installed_package_versions': runtime_versions()}))
        return
    require(args.run and args.scope_sha256 == digest(scope_path), 'Explicit --run and exact scope SHA256 required')
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1801))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('1800s wall cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    locks, out = [], None
    try:
        for slot in range(2):
            lock = (root / BASE / ('SLOT%d.lock' % slot)).open('a+b')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locks.append(lock)
                break
            except BlockingIOError:
                lock.close()
        else:
            raise BlockingIOError('Both 2GiB science slots occupied')
        job_lock = (root / BASE / (args.job + '.lock')).open('a+b')
        fcntl.flock(job_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(job_lock)
        target = root / BASE / 'results' / args.job
        target.mkdir(parents=True, exist_ok=False)
        out = target
        result = run(root, scope, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256, 'Prospective scope changed during search')
        pins = [byte_pin(root, p) for p in sorted(out.iterdir()) if p.is_file()]
        require(len(pins) == 3079, '512maps+512normalizations+2051capsules+4JSON inventory differs')
        receipt = {'schema': 'SETI_ORIGINAL_OFF_ADJACENT_EXECUTION_V1',
                   'status': 'COMPLETE_512_NEW_ORIGINAL_OFF_MAPS_EXPLORATORY_ONLY',
                   'primary_id': args.job, 'scan_id': JOBS[args.job][0], 'primary_target': JOBS[args.job][1],
                   'original_acquisition_role': 'OFF', 'scope_sha256': args.scope_sha256,
                   'driver_sha256': digest(Path(__file__).resolve()), **result,
                   'output_byte_pins': pins, 'science_slot': slot,
                   'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
                   'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, **CAPS,
                   'source_bytes_unchanged': True, 'detector_search_repeated': False,
                   'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
                   'new_observation_visit': False, 'qualified_SETI_detection': False,
                   'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
        require(receipt['process_CPU_seconds'] <= 1800 and receipt['wall_seconds'] <= 1800
                and receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Actual process resource cap exceeded')
        auxiliary = sum(p.stat().st_size for p in out.glob('*.json') if not p.name.endswith('_normalization.json'))
        size = len((json.dumps(receipt, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        require(auxiliary + size <= 10 * 1024**2, '10MiB auxiliary JSON cap exceeded')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        output_guard(out)
    except BaseException as exc:
        if out is not None and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_ORIGINAL_OFF_ADJACENT_EXECUTION_V1',
                 'status': 'INCOMPLETE_PRESERVED', 'primary_id': args.job, 'failure_type': type(exc).__name__,
                 'failure': str(exc), 'scope_sha256': args.scope_sha256, 'new_telescope_HTTP_requests': 0})
        raise
    finally:
        signal.alarm(0)
        for lock in reversed(locks):
            lock.close()


if __name__ == '__main__':
    main()
