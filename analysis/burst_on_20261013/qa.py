"""Independent saved-map QA for three HIP98505 four-row burst scans.

Import and --check-only are metadata-only. Numerical execution requires a
separate exact root GO after all three producer receipts are COMPLETE. Neither
producer nor detector is imported; saved winners are audited without rerunning
the seven-window/drift/width maximization.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

BASE = 'seti_burst_on'
RAW = 'seti_raw'
METADATA = 'burst_previous'
READER = METADATA + '/analysis/new_visit_search/dependencies/standard_reader.py'
READER_SHA = '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'
MIDPOINT = METADATA + '/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = METADATA + '/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = METADATA + '/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = METADATA + '/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
JOBS = {'on20170428_epoch1_HIP98505': 'epoch1_on',
        'on20170428_epoch2_HIP98505': 'epoch2_on',
        'on20170428_epoch3_HIP98505': 'epoch3_on'}
NATIVES = (170, 171, 172)
CHUNK, CORE, HALO, C0 = 1048576, 4096, 4000, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DOMAINS = tuple((native, 4 + 8 * k) for native in NATIVES for k in range(32))
STARTS = (0, 2, 4, 6, 8, 10, 12)
DC_CHANNELS = tuple(native * CHUNK + CHUNK // 2 for native in NATIVES)
BURST_ROWS, DRIFTS, VALID_COUNT = 4, 159, 2226
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP = 600, 900, 2 * 1024**3, 4 * 1024**2
EXPECTED = {'maps': 288, 'carrier_maxima': 288 * CORE,
            'valid_hypothesis_records': 288 * CORE * VALID_COUNT,
            'core_row_medians': 288 * 16, 'score_audit_queries': 1170,
            'raw_power_cells': 1170 * BURST_ROWS * 503, 'independent_scores': 1170,
            'source_compacts': 9, 'source_decoded_rows': 144,
            'raw_top20_entries': 60, 'raw_top3_entries': 9,
            'dc_top20_entries': 60, 'dc_top3_entries': 9,
            'dc_winning_tuple_geometries': 288 * CORE}
NORM_FIELDS = {'row_power_median', 'row_residual_median',
               'row_winsorized_residual_location', 'row_residual_MAD_scale',
               'normalization_unmasked_counts', 'normalization_source_channel_interval_half_open'}
MAP_SCHEMA = {'frequency_hz_at_window_reference': ('<f8', (CORE,)),
              'maximum_robust_box_track_score': ('<f8', (CORE,)),
              'winning_drift_hz_s': ('<f8', (CORE,)),
              'winning_width_channels': ('<i2', (CORE,)),
              'winning_window_start_row': ('<i2', (CORE,)),
              'winning_drift_grid_index': ('<i2', (CORE,)),
              'valid_hypothesis_count': ('<i8', (CORE,)),
              'source_reference_channels': ('<i8', (CORE,)),
              'drift_grid_hz_s': ('<f8', (DRIFTS,))}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    item = Path(name)
    require(not item.is_absolute() and '..' not in item.parts, 'Relative input required')
    path = root / item
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined input')
    return path


def create_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def arrays_equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b), message)


def arrays_near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def centers_for(frequency, drift):
    times = np.arange(BURST_ROWS) * TSAMP
    return np.rint((frequency - FCH1) / DF + drift * times / DF).astype(np.int64)


def independent_rows(raw, normal, width, absolute_rows):
    """Four-row direct501 medians, independently of producer filtering/prefixes."""
    require(raw.shape == (BURST_ROWS, 503) and raw.dtype == np.dtype('<f4'), 'Raw4x503 differs')
    require(width in (1, 3), 'Unknown width')
    ratio = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[absolute_rows, None]
    columns = list(range(251 - width // 2, 252 + width // 2))
    medians = np.column_stack([np.median(ratio[:, column - 250:column + 251], axis=1)
                              for column in columns])
    standardized = (ratio[:, columns] - medians - np.asarray(
        normal['row_winsorized_residual_location'])[absolute_rows, None]) / np.asarray(
        normal['row_residual_MAD_scale'])[absolute_rows, None]
    rows = standardized.sum(axis=1)
    return rows, float(rows.sum() / np.sqrt(BURST_ROWS * width))


def independent_full_normalization(joined, channel0):
    """Direct sliding-window medians on all4096 core channels/all16 rows.

    Each partition batch has at most256x501 values. No detector/scipy calls and
    no large duplicated sliding-window array are required.
    """
    offset = channel0 - C0
    power = joined[:, offset - 250:offset + CORE + 250].astype(np.float64)
    require(power.shape == (16, CORE + 500), 'Core501 raw support differs')
    levels = np.median(power[:, 250:250 + CORE], axis=1)
    residual = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        ratio = power[row] / levels[row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, 501)
        for begin in range(0, CORE, 256):
            stop = min(begin + 256, CORE)
            residual[row, begin:stop] = ratio[250 + begin:250 + stop] - np.median(windows[begin:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    return {'row_power_median': levels, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def dc_geometry(centers, width):
    lower, upper = centers - width // 2, centers + width // 2
    touched = np.column_stack([(lower <= dc) & (upper >= dc) for dc in DC_CHANNELS])
    guard = min(int(np.minimum(np.abs(lower - dc), np.abs(upper - dc)).min())
                if not np.any((lower <= dc) & (upper >= dc)) else int(
                    (np.abs(centers - dc) - width // 2).min()) for dc in DC_CHANNELS)
    return {'rounded_absolute_centers': centers.tolist(),
            'width_box_source_channels_inclusive': np.column_stack((lower, upper)).tolist(),
            'frozen_DC_source_channels': list(DC_CHANNELS),
            'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touched.any(axis=1)).tolist(),
            'rows_intersecting_any_frozen_DC': int(touched.any(axis=1).sum()),
            'touch_counts_by_frozen_DC': {str(dc): int(touched[:, k].sum()) for k, dc in enumerate(DC_CHANNELS)},
            'eligible_DC_untouched': bool(not touched.any()),
            'minimum_DC_width_box_distance_channels': guard}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--check-only', action='store_true')
    for name in ('scope-sha256', 'qa-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    parser.add_argument('--primary-receipt', action='append', default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    if args.check_only:
        require(len(DOMAINS) == len(set(DOMAINS)) == 96, 'Domain census differs')
        require(all(0 < q < 255 for _, q in DOMAINS), 'Interior halos required')
        require(min(n * CHUNK + q * CORE - HALO for n, q in DOMAINS) >= C0
                and max(n * CHUNK + (q + 1) * CORE + HALO for n, q in DOMAINS) <= C0 + 3 * CHUNK,
                'Crop support outside raw triplet')
        print(json.dumps({'status': 'PASS_METADATA_ONLY_INDEPENDENT_ON_BURST4_QA_INTERFACE',
                          'expected_counts': EXPECTED, 'source_values_read': False,
                          'full501_normalization_minimum': 'all distinct rawTOP3/DC-awareTOP3 selected cores; all16 rows',
                          'scope_present': (root / BASE / 'SCOPE.json').exists()}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact SHA256s required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'Reviewed QA bytes differ')
    declared = {}
    for value in args.primary_receipt:
        key, sha = value.split('=', 1)
        require(key in JOBS and key not in declared and re.fullmatch('[0-9a-f]{64}', sha), 'Unique exact receipt required')
        declared[key] = sha
    require(set(declared) == set(JOBS), 'Exactly three COMPLETE producer receipts required')
    run(root, args, declared)


def run(root, args, declared):
    started = time.monotonic()
    pins, locks, retained = {}, [], []
    counts = {key: 0 for key in EXPECTED}
    out = root / BASE / 'qa_results'
    created_output = False
    selected_all, normalization_cores = {}, []
    max_row_difference = max_score_difference = max_normal_difference = 0.0

    def loaded(path, declaration=None):
        raw = path.read_bytes()
        pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        require(declaration is None or pin == {k: declaration[k] for k in ('bytes', 'sha256')}, 'Byte pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        require(name not in pins or pins[name] == pin, 'Input changed: ' + name)
        pins[name] = pin
        return raw

    def metadata(path, sha=None):
        raw = loaded(path)
        require(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Metadata SHA differs: ' + str(path))
        return read_json(raw)

    def archive(declaration):
        raw = loaded(confined(root, declaration['path']), declaration)
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            require(len(values.files) == len(set(values.files)), 'Duplicate NPZ members')
            return {key: values[key] for key in values.files}

    def alarm(signum, frame):
        raise TimeoutError('Independent QA resource cap')

    try:
        go = metadata(root / BASE / 'QA_ROOT_GO.json', args.root_go_sha256)
        require(go['status'] == 'GO_INDEPENDENT_SAVED_ON_BURST4_QA'
                and go['qa_sha256'] == args.qa_sha256 and go['primary_scope_sha256'] == args.scope_sha256
                and go['primary_receipt_sha256s'] == declared and go['CPU_cap_s'] == CPU_CAP
                and go['wall_cap_s'] == WALL_CAP and go['memory_cap_bytes'] == RAM_CAP
                and go['output_cap_bytes'] == OUTPUT_CAP, 'Separate QA root GO differs')
        require(all(re.fullmatch('[0-9a-f]{40}', go[k]) for k in
                    ('primary_public_freeze_commit', 'qa_public_freeze_commit')), 'Exact public freeze IDs required')
        signal.signal(signal.SIGALRM, alarm)
        signal.signal(signal.SIGXCPU, alarm)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
        signal.alarm(WALL_CAP)
        for name in ('SLOT0.lock', 'SLOT1.lock', 'ACTIVE_QA_FLOCK.lock'):
            handle = (root / BASE / name).open('a+b')
            locks.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        scope = metadata(root / BASE / 'SCOPE.json', args.scope_sha256)
        require(scope['widths_channels'] == [1, 3]
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': DRIFTS, 'exact_zero_index': 79}
                and [(v['native_chunk_index'], v['core_q']) for v in scope['core_domains']] == list(DOMAINS)
                and scope['window_start_rows'] == list(STARTS) and scope['window_length_rows'] == BURST_ROWS
                and scope['core_channels'] == CORE and scope['halo_channels'] == HALO
                and scope['masks'] is None and scope['data_selected_exclusions'] == []
                and scope['source_acquisition_roles_changed'] is False
                and scope['protected2016_data_opened'] is False and scope['injection_arrays_opened'] is False,
                'Frozen scope differs')
        require(scope['frozen_DC_source_channels'] == list(DC_CHANNELS)
                and scope['secondary_DC_cached_winner_filter'] is True
                and scope['original_independent_visits'] == 1
                and scope['ON_scan_positions_are_independent_visits'] is False, 'DC/visit declarations differ')
        driver_path = root / BASE / 'driver.py'
        require(digest(driver_path) == go['primary_driver_sha256'], 'Producer source differs')
        loaded(driver_path)
        loaded(Path(__file__).resolve())
        admission = go['primary_admission_pins']
        require(set(admission) == {BASE + '/ROOT_GO.json', BASE + '/freeze.json'}, 'Admission pin set differs')
        originals = {name: read_json(loaded(confined(root, name), pin)) for name, pin in admission.items()}
        primary_go, freeze = originals[BASE + '/ROOT_GO.json'], originals[BASE + '/freeze.json']
        require(primary_go['status'] == 'GO_288_NEW_ON_BURST4_COMBINED_MAPS'
                and primary_go['scope_sha256'] == args.scope_sha256
                and primary_go['driver_sha256'] == go['primary_driver_sha256']
                and primary_go['freeze_sha256'] == admission[BASE + '/freeze.json']['sha256']
                and freeze['status'] == 'PASS_PUBLIC_FREEZE_ON_BURST4_SCOPE_READBACK'
                and freeze['scope_sha256'] == args.scope_sha256
                and freeze['driver_sha256'] == go['primary_driver_sha256']
                and freeze['public_commit'] == go['primary_public_freeze_commit']
                and freeze['new_maps_executed_yet'] == 0, 'Prospective public admission differs')
        for declaration in freeze['files']:
            raw = loaded(confined(root, declaration['path']))
            blob = hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()
            require(declaration['exact'] is True and blob == declaration['git_blob_sha'], 'Public freeze bytes differ')
        text_pins = {pin['path']: pin for pin in scope['text_code_pins']}
        require(len(text_pins) == len(scope['text_code_pins']), 'Duplicate scope pins')
        for name, pin in text_pins.items():
            loaded(confined(root, name), pin)
        for name in (MIDPOINT, ADJACENT, ACQ171, ACQ_ADJACENT):
            require(name in text_pins, 'Missing scientific metadata pin: ' + name)
        loaded(root / READER)
        require(pins[READER]['sha256'] == READER_SHA, 'Independent HDF reader differs')
        original, adjacent = metadata(root / MIDPOINT), metadata(root / ADJACENT)
        acq_original, acq_adjacent = metadata(root / ACQ171), metadata(root / ACQ_ADJACENT)
        sources, identities = {}, {}
        for native in NATIVES:
            manifest = original if native == 171 else adjacent['by_native_chunk'][str(native)]
            for identity in manifest['sources']:
                if identity['label'] in JOBS.values():
                    identities[native, identity['label']] = identity
            records = acq_original['decoded_files'] if native == 171 else [
                value for value in acq_adjacent['decoded_files'] if value['native_chunk_index'] == native]
            records = [value for value in records if value['scan_id'] in JOBS.values()]
            require(len(records) == 3 and {v['scan_id'] for v in records} == set(JOBS.values()), 'Three ON sources required')
            for record in records:
                scan = record['scan_id']
                identity = identities[native, scan]
                head = identity['current_header']['data_attributes']
                require(identity['role'] == 'on' and head['source_name'] == 'HIP98505'
                        and identity['current_header'] == identities.get((171, scan), identity)['current_header']
                        and head['fch1'] * 1e6 == FCH1 and head['foff'] * 1e6 == DF and head['tsamp'] == TSAMP
                        and record['shape'] == [16, 1, CHUNK] and record['source_channel0'] == native * CHUNK
                        and [r['time_row'] for r in record['decoded_rows']] == list(range(16)), 'Source geometry/identity differs')
                prefix = Path(RAW) / Path(ACQ171 if native == 171 else ACQ_ADJACENT).relative_to(METADATA).parent
                path = confined(root, (prefix / record['array_file']).as_posix())
                pin = {'path': path.relative_to(root).as_posix(), 'bytes': record['bytes'], 'sha256': record['file_sha256']}
                sources[native, scan] = (path, pin, record, identity)
        require(len(sources) == 9, 'Exact9 ON source census required')
        for scan in JOBS.values():
            require(all(identities[n, scan]['current_header'] == identities[171, scan]['current_header']
                        and identities[n, scan]['url'] == identities[171, scan]['url']
                        and identities[n, scan]['etag'] == identities[171, scan]['etag'] for n in NATIVES),
                    'Across-native ON source identities differ')
        declared_sources = {(v['native_chunk_index'], v['scan_id']): v for v in scope['source_compacts']}
        require(set(declared_sources) == set(sources), 'Scope source census differs')
        for key, (_, pin, record, identity) in sources.items():
            declaration = declared_sources[key]
            require(all(declaration[k] == pin[k] for k in ('path', 'bytes', 'sha256'))
                    and declaration['decoded_rows'] == record['decoded_rows']
                    and declaration['original_header'] == identity['current_header']['data_attributes']
                    and declaration['original_source_url'] == identity['url']
                    and declaration['original_source_etag'] == identity['etag']
                    and declaration['original_acquisition_role'] == 'ON', 'Scope compact declaration differs')
        receipts = {}
        for job, scan in JOBS.items():
            receipt = metadata(root / BASE / 'results' / job / 'EXECUTION_RECEIPT.json', declared[job])
            require(receipt['status'].startswith('COMPLETE_96_NEW_ON_BURST4')
                    and receipt['primary_id'] == job and receipt['scan_id'] == scan
                    and receipt['scope_sha256'] == args.scope_sha256
                    and receipt['driver_sha256'] == go['primary_driver_sha256']
                    and receipt['original_acquisition_role'] == 'ON'
                    and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED'
                    and receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0
                    and receipt['counts'] == scope['expected_counts_per_target']
                    and receipt['counts']['maps'] == 96 and receipt['counts']['score_audit_queries'] == 390
                    and receipt['decoded_row_SHA_checks_before'] == receipt['decoded_row_SHA_checks_after'] == 48
                    and receipt['source_bytes_unchanged'] is True
                    and receipt['qualified_SETI_detection'] is False and receipt['calibrated_SNR_FAP'] is False,
                    'Producer COMPLETE receipt differs')
            require(receipt['root_GO_pin'] == {'path': BASE + '/ROOT_GO.json',
                                              **{k: admission[BASE + '/ROOT_GO.json'][k] for k in ('bytes', 'sha256')}}
                    and receipt['public_freeze_pin'] == {'path': BASE + '/freeze.json',
                                              **{k: admission[BASE + '/freeze.json'][k] for k in ('bytes', 'sha256')}}
                    and receipt['public_freeze_commit'] == go['primary_public_freeze_commit'],
                    'Producer admission receipt differs')
            own = [sources[n, scan] for n in NATIVES]
            require(receipt['source_compact_pre_and_post_pins'] == [v[1] for v in own]
                    and receipt['decoded_source_row_checks'] == [
                        {'source': v[1], 'decoded_rows': v[2]['decoded_rows'], 'rows_verified': 16} for v in own],
                    'Producer raw-row evidence differs')
            receipts[job] = receipt
        global np
        import numpy as np
        spec = importlib.util.spec_from_file_location('independent_on_reader', root / READER)
        reader = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reader
        spec.loader.exec_module(reader)
        h5py, _, _ = reader.current_codecs()
        runtime = {'Python': sys.version.split()[0],
                   **{n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'h5py', 'hdf5plugin')},
                   'HDF5': h5py.version.hdf5_version}
        require(all(r['runtime_versions'] == runtime for r in receipts.values()), 'Runtime differs')
        drift_grid = np.linspace(-4., 4., DRIFTS)
        require(drift_grid[79] == 0., 'Zero drift differs')
        powers = {}
        for key, (path, pin, record, identity) in sorted(sources.items()):
            stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
            retained.append((path, stream, os.fstat(stream.fileno())))
            h = hashlib.sha256()
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
            require(os.fstat(stream.fileno()).st_size == pin['bytes'] and h.hexdigest() == pin['sha256'], 'Raw compact SHA differs')
            pins[pin['path']] = {k: pin[k] for k in ('bytes', 'sha256')}
            stream.seek(0)
            with h5py.File(stream, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                require(data.shape == (16, 1, CHUNK) and data.dtype == np.dtype('<f4')
                        and int(data.attrs['original_source_frequency_chunk_origin']) == key[0] * CHUNK
                        and data.attrs['original_source_url'] == identity['url']
                        and data.attrs['original_source_etag'] == identity['etag'], 'Raw compact identity differs')
                power = data[:, 0, :]
            require(np.isfinite(power).all() and (power >= 0).all(), 'Invalid raw power')
            for row in record['decoded_rows']:
                require(row['decoded_bytes'] == CHUNK * 4
                        and hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'], 'Decoded row SHA differs')
                counts['source_decoded_rows'] += 1
            powers[key] = power
            counts['source_compacts'] += 1
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        create_json(out / 'INPUT_ADMISSION.json', {'status': 'NINE_SOURCE_COMPACTS_AND_THREE_COMPLETE_RECEIPTS_ADMITTED',
                    'qa_sha256': args.qa_sha256, 'root_go_sha256': args.root_go_sha256,
                    'primary_receipt_sha256s': declared, 'source_compacts': 9, 'decoded_source_rows': 144})
        # Saved-array and scalar QA continues below. No maximization is performed.
        for job, scan in JOBS.items():
            jobdir = root / BASE / 'results' / job
            maps, audits = metadata(jobdir / 'MAPS.json'), metadata(jobdir / 'SCORE_AUDITS.json')
            tops = {name: metadata(jobdir / (name + '.json')) for name in
                    ('TOP20', 'TOP3', 'DC_AWARE_TOP20', 'DC_AWARE_TOP3')}
            for value in (maps, audits, *tops.values()):
                require(value['primary_id'] == job and value['scan_id'] == scan, 'Output scan identity differs')
            require(maps['schema'] == 'SETI_ON_BURST4_COMBINED_MAPS_V1'
                    and audits['schema'] == 'SETI_ON_BURST4_SCORE_AUDITS_V1', 'Inventory schema differs')
            require([(v['native_chunk_index'], v['core_q']) for v in maps['records']] == list(DOMAINS), 'Exact96 maps differ')
            joined = np.concatenate([powers[n, scan] for n in NATIVES], axis=1)
            infos, blocks, channel_blocks, eligible_blocks = {}, [], [], []
            head = identities[171, scan]['current_header']['data_attributes']
            for declaration in maps['records']:
                native, q = declaration['native_chunk_index'], declaration['core_q']
                key, channel0 = (native, q), native * CHUNK + q * CORE
                channels = np.arange(channel0, channel0 + CORE, dtype=np.int64)
                map_id = '%s_native%d_q%03d' % (scan, native, q)
                require(declaration['reference_channel_interval_half_open'] == [channel0, channel0 + CORE]
                        and declaration['loaded_channel_interval_half_open'] == [channel0 - HALO, channel0 + CORE + HALO]
                        and declaration['map_id'] == map_id
                        and declaration['path'] == (jobdir / (map_id + '.npz')).relative_to(root).as_posix()
                        and declaration['searched_carriers'] == CORE and declaration['valid_hypotheses_per_carrier'] == VALID_COUNT
                        and declaration['combined_window_start_rows'] == list(STARTS)
                        and declaration['original_acquisition_role'] == 'ON', 'Map source support differs')
                value = archive(declaration)
                normal_pin = declaration['normalization']
                require(normal_pin['path'] == (jobdir / (map_id + '_normalization.json')).relative_to(root).as_posix(), 'Normal path differs')
                normal = read_json(loaded(confined(root, normal_pin['path']), normal_pin))
                require(set(value) == set(MAP_SCHEMA) and set(normal) == NORM_FIELDS, 'Map/normal fields differ')
                for field, (dtype, shape) in MAP_SCHEMA.items():
                    require(value[field].dtype == np.dtype(dtype) and value[field].shape == shape
                            and np.isfinite(value[field]).all(), 'Map shape/dtype differs: ' + field)
                arrays_equal(value['source_reference_channels'], channels, 'Map channels differ')
                arrays_equal(value['frequency_hz_at_window_reference'], FCH1 + DF * channels, 'Map frequencies differ')
                arrays_equal(value['drift_grid_hz_s'], drift_grid, 'Map drift grid differs')
                arrays_equal(value['valid_hypothesis_count'], np.full(CORE, VALID_COUNT), 'Map support census differs')
                require(np.isin(value['winning_width_channels'], (1, 3)).all()
                        and np.isin(value['winning_window_start_row'], STARTS).all()
                        and (value['winning_drift_grid_index'] >= 0).all() and (value['winning_drift_grid_index'] < DRIFTS).all(),
                        'Winning tuple outside scope')
                arrays_equal(value['winning_drift_hz_s'], drift_grid[value['winning_drift_grid_index']], 'Map drift/index differs')
                arrays_equal(normal['normalization_source_channel_interval_half_open'], [channel0, channel0 + CORE], 'Normal core differs')
                arrays_equal(normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normal counts differ')
                for field in NORM_FIELDS - {'normalization_source_channel_interval_half_open', 'normalization_unmasked_counts'}:
                    require(np.asarray(normal[field]).shape == (16,) and np.isfinite(normal[field]).all(), 'Normal array differs')
                require(np.all(np.asarray(normal['row_power_median']) > 0) and np.all(np.asarray(normal['row_residual_MAD_scale']) > 0), 'Normal scales invalid')
                offset = channel0 - C0
                arrays_equal(np.median(joined[:, offset:offset + CORE].astype(np.float64), axis=1), normal['row_power_median'], 'Raw4096 median differs')
                times = np.arange(4) * TSAMP
                centers = np.rint((value['frequency_hz_at_window_reference'][:, None] - FCH1) / DF
                                  + value['winning_drift_hz_s'][:, None] * times[None, :] / DF).astype(np.int64)
                halfwidth = value['winning_width_channels'][:, None] // 2
                touched = np.zeros(CORE, dtype=bool)
                for dc in DC_CHANNELS:
                    touched |= ((centers - halfwidth <= dc) & (centers + halfwidth >= dc)).any(axis=1)
                infos[key] = {'arrays': value, 'normal': normal, 'record': declaration,
                              'order': np.lexsort((channels, -value['maximum_robust_box_track_score']))}
                blocks.append(value['maximum_robust_box_track_score'])
                channel_blocks.append(channels)
                eligible_blocks.append(~touched)
                counts['maps'] += 1
                counts['carrier_maxima'] += CORE
                counts['valid_hypothesis_records'] += int(value['valid_hypothesis_count'].sum())
                counts['core_row_medians'] += 16
                counts['dc_winning_tuple_geometries'] += CORE

            def tuple_record(key, index, rank=None):
                native, q = key
                info = infos[key]
                value = info['arrays']
                start = int(value['winning_window_start_row'][index])
                frequency = float(value['frequency_hz_at_window_reference'][index])
                drift = float(value['winning_drift_hz_s'][index])
                width = int(value['winning_width_channels'][index])
                result = {'primary_id': job, 'primary_target': 'HIP98505', 'scan_id': scan,
                          'original_acquisition_role': 'ON', 'native_chunk_index': native, 'core_q': q,
                          'map_id': info['record']['map_id'], 'carrier_index_in_core': int(index),
                          'source_reference_channel': int(value['source_reference_channels'][index]),
                          'frequency_hz_at_window_reference': frequency,
                          'reference_time_mjd': head['tstart'] + (start + .5) * TSAMP / 86400,
                          'window_start_row': start, 'window_length_rows': 4,
                          'window_source_rows': list(range(start, start + 4)),
                          'drift_grid_index': int(value['winning_drift_grid_index'][index]),
                          'drift_hz_s': drift, 'width_channels': width,
                          'score': float(value['maximum_robust_box_track_score'][index]),
                          **dc_geometry(centers_for(frequency, drift), width)}
                if rank is not None:
                    result['rank'] = rank
                return result

            all_scores, all_channels, all_eligible = np.concatenate(blocks), np.concatenate(channel_blocks), np.concatenate(eligible_blocks)
            require(len(all_channels) == len(np.unique(all_channels)) == 96 * CORE, 'Pooled domain overlap/census differs')
            geometry_counts = {'all_cached_winner_carriers': int(len(all_channels)),
                               'eligible_DC_untouched_carriers': int(all_eligible.sum()),
                               'DC_contacting_cached_winner_carriers': int((~all_eligible).sum()),
                               'DC_row_box_membership_checks': 96 * CORE * 4 * len(DC_CHANNELS)}
            require(geometry_counts == receipts[job]['DC_geometry_counts']
                    and geometry_counts['DC_contacting_cached_winner_carriers'] == 0,
                    'Independent DC census differs')
            order = np.lexsort((all_channels, -all_scores))
            selected = {}
            for family, dc_aware in (('raw', False), ('dc_aware', True)):
                records = []
                for position in order:
                    if dc_aware and not all_eligible[position]:
                        continue
                    channel = int(all_channels[position])
                    if any(abs(channel - r['source_reference_channel']) <= 3 for r in records):
                        continue
                    mapindex, index = divmod(int(position), CORE)
                    records.append(tuple_record(DOMAINS[mapindex], index, len(records) + 1))
                    if len(records) == 20:
                        break
                require(len(records) == 20, 'Pooled TOP20 incomplete')
                prefix = 'DC_AWARE_' if dc_aware else ''
                for size in ('TOP20', 'TOP3'):
                    inventory = tops[prefix + size]
                    require(inventory['schema'] == 'SETI_ON_BURST4_SCAN_GLOBAL_RANKS_V1'
                            and inventory['original_acquisition_role'] == 'ON'
                            and inventory['DC_aware_cached_winner_selection'] is dc_aware
                            and inventory['selection_rule'] == scope['DC_aware_ranking' if dc_aware else 'target_ranking']
                            and inventory['DC_geometry_counts'] == geometry_counts, 'Ranking contract differs')
                require(tops[prefix + 'TOP20']['records'] == records
                        and tops[prefix + 'TOP3']['records'] == records[:3], 'Independent ranking differs: ' + family)
                selected[family] = records
                counts[('dc' if dc_aware else 'raw') + '_top20_entries'] += 20
                counts[('dc' if dc_aware else 'raw') + '_top3_entries'] += 3
            selected_all[job] = {family: records[:3] for family, records in selected.items()}
            selected_cores = sorted({(r['native_chunk_index'], r['core_q']) for records in selected.values() for r in records[:3]})
            for key in selected_cores:
                independent = independent_full_normalization(joined, key[0] * CHUNK + key[1] * CORE)
                normal = infos[key]['normal']
                differences = {}
                for field, expected in independent.items():
                    arrays_near(normal[field], expected, 'Independent full501 normal differs: ' + field)
                    differences[field] = float(np.max(np.abs(np.asarray(normal[field]) - expected)))
                    max_normal_difference = max(max_normal_difference, differences[field])
                normalization_cores.append({'primary_id': job, 'native_chunk_index': key[0], 'core_q': key[1],
                                            'all16_rows': True, 'max_absolute_differences': differences})
            query_keys = {(n, q, kind) for n, q in DOMAINS for kind in ('first', 'midpoint', 'last', 'core_max')}
            seen, global_seen = set(), {'raw': set(), 'dc_aware': set()}
            require(len(audits['records']) == 390, 'Audit390 census differs')
            for query in audits['records']:
                key, kind = (query['native_chunk_index'], query['core_q']), query['query_kind']
                require(key in infos and query['normalization'] == infos[key]['record']['normalization'], 'Audit normal/domain differs')
                if kind in ('global_top3', 'DC_aware_global_top3'):
                    family = 'raw' if kind == 'global_top3' else 'dc_aware'
                    rank = query['selected_tuple']['rank']
                    require(rank in (1, 2, 3) and rank not in global_seen[family], 'Duplicate global rank')
                    global_seen[family].add(rank)
                    expected_tuple = selected[family][rank - 1]
                    expected_query_id = ('global_top%02d' if family == 'raw' else 'dc_global_top%02d') % rank
                else:
                    query_key = key + (kind,)
                    require(query_key in query_keys and query_key not in seen, 'Unexpected percore audit')
                    seen.add(query_key)
                    index = {'first': 0, 'midpoint': 2048, 'last': 4095, 'core_max': int(infos[key]['order'][0])}[kind]
                    expected_tuple = tuple_record(key, index)
                    expected_query_id = 'native%d_q%03d_%s' % (key[0], key[1], kind)
                require(query['selected_tuple'] == expected_tuple and query['map_id'] == expected_tuple['map_id']
                        and query['query_id'] == expected_query_id
                        and query['capsule']['path'] == (jobdir / (expected_query_id + '_raw4x503.npz')).relative_to(root).as_posix(),
                        'Saved deterministic capsule tuple/identity differs')
                capsule = archive(query['capsule'])
                require(set(capsule) == {'raw_power', 'rounded_absolute_centers', 'standardized_row_box_sums', 'absolute_time_rows'}, 'Capsule fields differ')
                for field, dtype, shape in (('raw_power', '<f4', (4, 503)), ('rounded_absolute_centers', '<i8', (4,)),
                                           ('standardized_row_box_sums', '<f8', (4,)), ('absolute_time_rows', '<i8', (4,))):
                    require(capsule[field].dtype == np.dtype(dtype) and capsule[field].shape == shape
                            and np.isfinite(capsule[field]).all(), 'Capsule precision/shape differs')
                absolute_rows = expected_tuple['window_start_row'] + np.arange(4, dtype=np.int64)
                centers = centers_for(expected_tuple['frequency_hz_at_window_reference'], expected_tuple['drift_hz_s'])
                indexes = centers[:, None] - C0 + np.arange(-251, 252)[None, :]
                require(indexes.min() >= 0 and indexes.max() < 3 * CHUNK, 'Capsule support outside sources')
                raw = joined[absolute_rows[:, None], indexes]
                arrays_equal(capsule['absolute_time_rows'], absolute_rows, 'Capsule absolute rows differ')
                arrays_equal(capsule['rounded_absolute_centers'], centers, 'Capsule rounding differs')
                arrays_equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Capsule raw bits differ')
                rows, score = independent_rows(raw, infos[key]['normal'], expected_tuple['width_channels'], absolute_rows)
                arrays_near(capsule['standardized_row_box_sums'], rows, 'Independent scalar row arithmetic differs')
                arrays_near(expected_tuple['score'], score, 'Independent scalar score differs')
                max_row_difference = max(max_row_difference, float(np.max(np.abs(capsule['standardized_row_box_sums'] - rows))))
                max_score_difference = max(max_score_difference, abs(score - expected_tuple['score']))
                counts['score_audit_queries'] += 1
                counts['independent_scores'] += 1
                counts['raw_power_cells'] += raw.size
            require(seen == query_keys and all(v == {1, 2, 3} for v in global_seen.values()), 'Audit matrix incomplete')
            declarations = receipts[job]['output_byte_pins']
            names = {v['path'] for v in declarations}
            require(len(names) == len(declarations) == 588, 'Closed output inventory differs')
            observed = {name for name in pins if name.startswith(jobdir.relative_to(root).as_posix() + '/')
                        and not name.endswith('/EXECUTION_RECEIPT.json')}
            actual = {p.relative_to(root).as_posix() for p in jobdir.rglob('*') if p.is_file()}
            require(names == observed and actual == names | {jobdir.relative_to(root).as_posix() + '/EXECUTION_RECEIPT.json'}, 'Output closure differs')
            for declaration in declarations:
                require(pins[declaration['path']] == {k: declaration[k] for k in ('bytes', 'sha256')}, 'Closed output byte pin differs')
            del joined, infos, all_scores, all_channels, all_eligible, order, blocks, channel_blocks, eligible_blocks
            print('PASS_INDEPENDENT_SAVED_ON_BURST4_SCAN', job, flush=True)
        require(counts == EXPECTED, 'Independent census incomplete')
        for path, stream, before in retained:
            after, current = os.fstat(stream.fileno()), path.stat(follow_symlinks=False)
            require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
                    (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    and (current.st_dev, current.st_ino) == (before.st_dev, before.st_ino), 'Retained source identity changed')
        for name, pin in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during QA: ' + name)
        usage = {'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
                and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Resource bounds exceeded')
        receipt = {'schema': 'SETI_ON_BURST4_SAVED_INDEPENDENT_QA_V1',
                   'status': 'PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN',
                   'counts': counts, 'qa_sha256': args.qa_sha256, 'primary_scope_sha256': args.scope_sha256,
                   'primary_driver_sha256': go['primary_driver_sha256'], 'primary_receipt_sha256s': declared,
                   'root_go_sha256': args.root_go_sha256,
                   'primary_public_freeze_commit': go['primary_public_freeze_commit'],
                   'qa_public_freeze_commit': go['qa_public_freeze_commit'],
                   'selected_top3': selected_all, 'full501_independently_recomputed_cores': normalization_cores,
                   'full501_independent_core_count': len(normalization_cores),
                   'full501_independent_row_count': len(normalization_cores) * 16,
                   'full501_independent_residual_cells': len(normalization_cores) * 16 * CORE,
                   'input_byte_pins': pins, 'runtime_versions': runtime,
                   'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                   'max_row_sum_arithmetic_absolute_difference': max_row_difference,
                   'max_score_arithmetic_absolute_difference': max_score_difference,
                   'max_full501_normalization_absolute_difference': max_normal_difference,
                   'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, 'output_cap_bytes': OUTPUT_CAP,
                   **usage, 'detector_imported': False, 'producer_imported': False, 'full_grid_recomputed': False,
                   'raw_core_row_medians_independently_recomputed': True,
                   'full_core_MAD_location_independently_recomputed_for_all_selected_TOP3_cores': True,
                   'DC_geometry_checked_for_all_saved_winning_tuples': True,
                   'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
                   'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
                   'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
                   'limitations': ['Saved winners are audited without independent exhaustive maximization or tie-order validation.',
                                   'All audit scores use saved fullcore normalization; all selected raw/DC-awareTOP3 core normalizations independently recomputed.',
                                   'DC-aware ranking rejects only cached winning boxes touching a known DC center in the selected four rows; discarded secondary hypotheses are not searched.',
                                   'Three chronological ON scans are one visit of HIP98505, not three independent nights.',
                                   'Empirical robust box-track scores are not calibrated SNR/FAP; no sky-origin claim or OFF veto is made.']}
        create_json(out / 'QA_RECEIPT.json', receipt)
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= OUTPUT_CAP, 'QA output cap exceeded')
        print(receipt['status'], flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            create_json(out / 'QA_FAILURE.json', {'status': 'FAIL_INDEPENDENT_ON_BURST4_QA',
                        'error_type': type(error).__name__, 'message': str(error), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started, 'detector_imported': False, 'full_grid_recomputed': False})
        raise
    finally:
        signal.alarm(0)
        for handle in locks:
            handle.close()
        for _, stream, _ in retained:
            stream.close()


if __name__ == '__main__':
    main()
