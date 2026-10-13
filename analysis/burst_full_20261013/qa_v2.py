"""Independent QA of saved unrestricted/DC-clean four-row burst maxima.

Metadata-only admission and synthetic tests are separate from telescope-value
audits. No producer or detector is imported. The independent implementation
uses direct501 medians and its own prefix/frame traversal for DC-affected cores.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE, METADATA, RAW = 'seti_burst_full', 'burst_previous', 'seti_raw'
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CHUNK, CORE, HALO, BAND0 = 1048576, 4096, 4000, 170 * 1048576
STARTS, WIDTHS, DRIFT_COUNT = (0, 2, 4, 6, 8, 10, 12), (1, 3), 159
ON_SCANS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
NATIVES, DC_CHANNELS = (170, 171, 172), (178782208, 179830784, 180879360)
DC_DOMAINS = tuple((native, q) for native in NATIVES for q in (127, 128))
PILOT_DOMAINS = tuple((native, 4 + 8 * k) for native in NATIVES for k in range(32))
ALL_DOMAINS = tuple((native, q) for native in NATIVES for q in range(256)
                    if not (native == 170 and q == 0) and not (native == 172 and q == 255))
DOMAINS = tuple(key for key in ALL_DOMAINS if key not in set(PILOT_DOMAINS))
JOBS = {f'full20170428_epoch{epoch}_HIP98505_shard{shard:02d}':
        (f'epoch{epoch}_on', DOMAINS[96 * shard:96 * (shard + 1)])
        for epoch in (1, 2, 3) for shard in range(7)}
MIDPOINT = METADATA + '/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = METADATA + '/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = METADATA + '/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQADJ = METADATA + '/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, MEMORY_CAP, OUTPUT_CAP = 600, 900, 2 * 1024**3, 8 * 1024**2


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
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key')
        value[key] = item
    return value


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined relative path required')
    return path


def create_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b, equal_nan=True), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def independent_dual_max(z, frequencies, crop0, drift_grid, times, dc_channels,
                         fch1=FCH1, df=DF, starts=STARTS, widths=WIDTHS):
    """Own prefix/frame enumeration; only sixteen-row standardized terms input.

    No producer cache or producer numerical function is called. Both maxima
    use window/width/drift ascending and strict-greater updates. EMPTY retains
    score -inf, index/start/width -1 and valid count0.
    """
    z = np.asarray(z, dtype=np.float64)
    frequencies, drift_grid, times = [np.asarray(value, dtype=np.float64)
                                     for value in (frequencies, drift_grid, times)]
    require(z.ndim == 2 and z.shape[0] == 16 and np.isfinite(z).all(), 'Finite sixteen-row standardized terms required')
    require(frequencies.ndim == drift_grid.ndim == times.ndim == 1 and len(times) == 4
            and times[0] == 0 and np.isfinite(frequencies).all() and np.isfinite(drift_grid).all()
            and np.isfinite(times).all() and df != 0, 'Independent family input differs')
    carriers = len(frequencies)
    prefix = np.concatenate((np.zeros((16, 1), dtype=np.float64), np.cumsum(z, axis=1)), axis=1)
    def blank():
        return {'score': np.full(carriers, -np.inf, dtype=np.float64),
                'drift_grid_index': np.full(carriers, -1, dtype=np.int16),
                'window_start_row': np.full(carriers, -1, dtype=np.int16),
                'width_channels': np.full(carriers, -1, dtype=np.int16),
                'valid_hypothesis_count': np.zeros(carriers, dtype=np.int64)}
    result = {'raw': blank(), 'clean': blank()}
    base = (frequencies - fch1) / df
    dc = np.asarray(dc_channels, dtype=np.int64)
    for start in starts:
        require(0 <= start <= 12, 'Window outside sixteen rows')
        for width in widths:
            require(width in (1, 3), 'Unknown box width')
            radius = width // 2
            for di, drift in enumerate(drift_grid):
                centers = np.rint(base[:, None] + drift * times[None, :] / df).astype(np.int64)
                lower, upper = centers - crop0 - radius, centers - crop0 + radius + 1
                valid = ((lower >= 0) & (upper <= z.shape[1])).all(axis=1)
                touching = np.zeros(carriers, dtype=bool)
                for channel in dc:
                    touching |= ((centers - radius <= channel) & (centers + radius >= channel)).any(axis=1)
                terms = np.zeros(carriers, dtype=np.float64)
                for row in range(4):
                    left = np.clip(lower[:, row], 0, z.shape[1])
                    right = np.clip(upper[:, row], 0, z.shape[1])
                    terms += prefix[start + row, right] - prefix[start + row, left]
                score = terms / np.sqrt(4 * width)
                for kind, admitted in (('raw', valid), ('clean', valid & ~touching)):
                    value = result[kind]
                    value['valid_hypothesis_count'] += admitted
                    improve = admitted & (score > value['score'])
                    value['score'][improve] = score[improve]
                    value['drift_grid_index'][improve] = di
                    value['window_start_row'][improve] = start
                    value['width_channels'][improve] = width
    return result


def independent_clean_counts(frequencies, drift_grid, times):
    """Geometry-only census, independent of scores and saved winning tuples."""
    base = (frequencies - FCH1) / DF
    count = np.zeros(len(frequencies), dtype=np.int64)
    for width in WIDTHS:
        radius = width // 2
        for drift in drift_grid:
            centers = np.rint(base[:, None] + drift * times[None, :] / DF).astype(np.int64)
            touched = np.zeros(len(frequencies), dtype=bool)
            for dc in DC_CHANNELS:
                touched |= ((centers - radius <= dc) & (centers + radius >= dc)).any(axis=1)
            count += ~touched
    return count * len(STARTS)


def independent_normal(raw):
    """All4096/full16 core normalization by direct501 batched medians."""
    require(raw.shape == (16, CORE + 2 * HALO) and raw.dtype == np.dtype('<f4'), 'Raw16x12096 crop differs')
    level = np.median(raw[:, HALO:HALO + CORE].astype(np.float64), axis=1)
    residual = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        power = raw[row, HALO - 250:HALO + CORE + 250].astype(np.float64) / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(power, 501)
        for begin in range(0, CORE, 256):
            stop = min(begin + 256, CORE)
            residual[row, begin:stop] = power[250 + begin:250 + stop] - np.median(windows[begin:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    require(np.all(level > 0) and np.all(scale > 0), 'Independent normalization scales invalid')
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def independent_standardized_region(raw, normal, margin=81):
    """Standardized terms on core±81 channels, direct501 median arithmetic."""
    length = CORE + 2 * margin
    result = np.empty((16, length), dtype=np.float64)
    for row in range(16):
        power = raw[row, HALO - margin - 250:HALO + CORE + margin + 250].astype(np.float64) / normal['row_power_median'][row]
        windows = np.lib.stride_tricks.sliding_window_view(power, 501)
        for begin in range(0, length, 256):
            stop = min(begin + 256, length)
            medians = np.median(windows[begin:stop], axis=1)
            result[row, begin:stop] = (power[250 + begin:250 + stop] - medians -
                                       normal['row_winsorized_residual_location'][row]) / normal['row_residual_MAD_scale'][row]
    return result


def scalar_rows(raw, normal, width, absolute_rows):
    require(raw.shape == (4, 503) and raw.dtype == np.dtype('<f4') and width in WIDTHS, 'Raw503 query differs')
    ratio = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[absolute_rows, None]
    columns = list(range(251 - width // 2, 252 + width // 2))
    median = np.column_stack([np.median(ratio[:, c - 250:c + 251], axis=1) for c in columns])
    standardized = (ratio[:, columns] - median - np.asarray(normal['row_winsorized_residual_location'])[absolute_rows, None]) / np.asarray(normal['row_residual_MAD_scale'])[absolute_rows, None]
    rows = standardized.sum(axis=1)
    return rows, float(rows.sum() / np.sqrt(4 * width))


def run(root, args, declarations):
    started, pins, locks = time.monotonic(), {}, []
    out = root / BASE / 'qa_results'
    created_output = False
    counts = {'maps': 0, 'carrier_winners': 0, 'raw_valid_hypothesis_records': 0,
              'clean_valid_hypothesis_records': 0, 'clean_EMPTY_carriers': 0,
              'scalar_queries': 0, 'scalar_raw_power_cells': 0,
              'raw_core_row_medians': 0, 'source_compacts': 0, 'source_decoded_rows': 0,
              'DC_full501_normalization_cores': 0, 'DC_full501_normalization_rows': 0,
              'independent_dual_remax_cores': 0, 'independent_dual_remax_carriers': 0,
              'independent_dual_remax_raw_hypotheses': 0,
              'independent_dual_remax_clean_hypotheses': 0,
              'far_DC_geometric_proof_cores': 0, 'raw_clean_identical_eligible_winners': 0,
              'raw_clean_differing_winners': 0}
    remax_reports = []
    max_normal_error = max_row_error = max_scalar_error = max_remax_error = 0.0

    def loaded(path, pin=None):
        raw = path.read_bytes()
        current = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        require(pin is None or current == {k: pin[k] for k in ('bytes', 'sha256')}, 'Input pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        require(name not in pins or pins[name] == current, 'Input changed: ' + name)
        pins[name] = current
        return raw

    def metadata(path, sha=None):
        raw = loaded(path)
        require(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Metadata SHA differs: ' + str(path))
        return decode(raw)

    def archive(pin):
        raw = loaded(confined(root, pin['path']), pin)
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            require(len(values.files) == len(set(values.files)), 'Duplicate NPZ member')
            return {key: values[key] for key in values.files}

    def alarm(signum, frame):
        raise TimeoutError('Independent full dual QA resource cap')

    try:
        go = metadata(root / BASE / 'QA_ROOT_GO.json', args.root_go_sha256)
        require(go['status'] == 'GO_INDEPENDENT_FULL_ON_DUAL_BURST4_QA'
                and go['scope_sha256'] == args.scope_sha256 and go['qa_sha256'] == args.qa_sha256
                and go['primary_receipt_sha256s'] == declarations
                and go['CPU_cap_s'] == CPU_CAP and go['wall_cap_s'] == WALL_CAP
                and go['memory_cap_bytes'] == MEMORY_CAP and go['output_cap_bytes'] == OUTPUT_CAP,
                'Separate root QA GO differs')
        require(all(re.fullmatch('[0-9a-f]{40}', go[k]) for k in
                    ('primary_public_freeze_commit', 'qa_public_freeze_commit')), 'Exact public freeze identities required')
        signal.signal(signal.SIGALRM, alarm)
        signal.signal(signal.SIGXCPU, alarm)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
        signal.alarm(WALL_CAP)
        for name in ('SLOT0.lock', 'SLOT1.lock', 'QA.lock'):
            handle = (root / BASE / name).open('a+b')
            locks.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        loaded(Path(__file__).resolve())
        scope = metadata(root / BASE / 'SCOPE.json', args.scope_sha256)
        require(scope['schema'] == 'SETI_S2017_FULL_ON_DUAL_BURST4_REMAINING_SCOPE_V1'
                and scope['window_start_rows'] == list(STARTS) and scope['window_length_rows'] == 4
                and scope['widths_channels'] == list(WIDTHS)
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79}
                and scope['core_channels'] == CORE and scope['halo_channels'] == HALO
                and scope['new_maps'] == 2010 and scope['remaining_domains_per_ON_scan'] == 670
                and scope['reused_pilot_domains_per_ON_scan'] == 96
                and scope['complete_domains_per_ON_scan_after_merge'] == 766
                and [(v['native_chunk_index'], v['core_q']) for v in scope['remaining_core_domains']] == list(DOMAINS)
                and [(v['native_chunk_index'], v['core_q']) for v in scope['reused_pilot_domains']] == list(PILOT_DOMAINS)
                and scope['frozen_DC_source_channels'] == list(DC_CHANNELS)
                and scope['DC_affected_core_q'] == [127, 128] and scope['DC_affected_core_count_total'] == 18
                and scope['expected_DC_clean_EMPTY_carriers_total'] == 9
                and scope['pilot_maps_rerun'] is False and scope['protected2016_data_opened'] is False
                and scope['injection_arrays_opened'] is False and scope['independent_visits'] == 1,
                'Frozen scientific hypothesis/coverage scope differs')
        require(set(scope['jobs']) == set(JOBS), 'Exact21 shards required')
        for job, (scan, domains) in JOBS.items():
            declaration = scope['jobs'][job]
            require(declaration['scan_id'] == scan and declaration['primary_target'] == 'HIP98505'
                    and declaration['original_acquisition_role'] == 'ON'
                    and [(v['native_chunk_index'], v['core_q']) for v in declaration['domains']] == list(domains),
                    'Shard domain order differs')
        driver_path = root / BASE / 'driver.py'
        require(digest(driver_path) == go['driver_sha256'], 'Producer code differs')
        loaded(driver_path)
        admission = go['primary_admission_pins']
        require(set(admission) == {BASE + '/ROOT_GO.json', BASE + '/freeze.json'}, 'Producer admission pin set differs')
        original_admission = {name: decode(loaded(confined(root, name), pin)) for name, pin in admission.items()}
        producer_go, freeze = original_admission[BASE + '/ROOT_GO.json'], original_admission[BASE + '/freeze.json']
        require(producer_go['status'] == 'GO_2010_NEW_FULL_ON_DUAL_BURST4_MAPS'
                and producer_go['scope_sha256'] == args.scope_sha256
                and producer_go['driver_sha256'] == go['driver_sha256']
                and producer_go['freeze_sha256'] == admission[BASE + '/freeze.json']['sha256']
                and freeze['status'] == 'PASS_PUBLIC_FREEZE_FULL_ON_DUAL_BURST4_SCOPE_READBACK'
                and freeze['scope_sha256'] == args.scope_sha256 and freeze['driver_sha256'] == go['driver_sha256']
                and freeze['public_commit'] == go['primary_public_freeze_commit']
                and freeze['new_maps_executed_yet'] == 0, 'Original prospective producer admission differs')
        for record in freeze['files']:
            raw = loaded(confined(root, record['path']))
            blob = hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()
            require(record['exact'] is True and blob == record['git_blob_sha'], 'Public producer readback byte identity differs')
        text_pins = {pin['path']: pin for pin in scope['text_code_pins']}
        require(len(text_pins) == len(scope['text_code_pins']), 'Duplicate text/code pins')
        for name, pin in text_pins.items():
            loaded(confined(root, name), pin)
        require({MIDPOINT, ADJACENT, ACQ171, ACQADJ}.issubset(text_pins), 'Missing original source metadata pins')
        synthetic_pin = go['synthetic_receipt_pin']
        synthetic = decode(loaded(confined(root, synthetic_pin['path']), synthetic_pin))
        require(synthetic['status'] == 'PASS_INDEPENDENT_DUAL_MAX_SYNTHETIC_REGRESSIONS'
                and synthetic['qa_sha256'] == args.qa_sha256
                and synthetic['test_sha256'] == go['synthetic_test_sha256']
                and synthetic['source_values_read'] is False, 'Independent synthetic regression not PASS')
        test_name = go['synthetic_test_path']
        require(test_name.startswith(BASE + '/') and Path(test_name).suffix == '.py', 'Synthetic test path outside reviewed namespace')
        test_path = confined(root, test_name)
        require(digest(test_path) == go['synthetic_test_sha256'], 'Synthetic test code differs')
        loaded(test_path)
        midpoint, adjacent = metadata(root / MIDPOINT), metadata(root / ADJACENT)
        acq171, acqadj = metadata(root / ACQ171), metadata(root / ACQADJ)
        sources = {(s['native_chunk_index'], s['scan_id']): s for s in scope['source_compacts']}
        require(len(sources) == len(scope['source_compacts']) == 9
                and set(sources) == {(native, scan) for native in NATIVES for scan in ON_SCANS}, 'Exact9 ON source compacts required')
        for (native, scan), source in sources.items():
            manifest = midpoint if native == 171 else adjacent['by_native_chunk'][str(native)]
            identity = next(v for v in manifest['sources'] if v['label'] == scan)
            original = next(v for v in midpoint['sources'] if v['label'] == scan)
            acquisition = acq171 if native == 171 else acqadj
            records = [r for r in acquisition['decoded_files'] if r['scan_id'] == scan
                       and (native == 171 or r['native_chunk_index'] == native)]
            require(len(records) == 1, 'Unique original source acquisition required')
            record = records[0]
            acquisition_name = ACQ171 if native == 171 else ACQADJ
            path = Path(RAW) / Path(acquisition_name).relative_to(METADATA).parent / record['array_file']
            require(source['path'] == path.as_posix() and source['bytes'] == record['bytes']
                    and source['sha256'] == record['file_sha256'] and source['shape'] == record['shape'] == [16, 1, CHUNK]
                    and source['source_channel0'] == record['source_channel0'] == native * CHUNK
                    and source['decoded_rows'] == record['decoded_rows']
                    and [v['time_row'] for v in record['decoded_rows']] == list(range(16))
                    and source['original_header'] == identity['current_header']['data_attributes']
                    and identity['current_header'] == original['current_header']
                    and source['original_source_url'] == identity['url'] == original['url']
                    and source['original_source_etag'] == identity['etag'] == original['etag']
                    and source['original_acquisition_role'] == 'ON' and identity['role'] == 'on'
                    and source['original_header']['source_name'] == 'HIP98505'
                    and source['original_header']['fch1'] * 1e6 == FCH1
                    and source['original_header']['foff'] * 1e6 == DF and source['original_header']['tsamp'] == TSAMP,
                    'Source identity/decoded-row declaration differs')
        receipts = {}
        for job, (scan, domains) in JOBS.items():
            receipt = metadata(root / BASE / 'results' / job / 'EXECUTION_RECEIPT.json', declarations[job])
            expected = scope['jobs'][job]['expected_counts']
            require(receipt['status'] == 'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY'
                    and receipt['primary_id'] == job and receipt['scan_id'] == scan
                    and receipt['scope_sha256'] == args.scope_sha256 and receipt['driver_sha256'] == go['driver_sha256']
                    and receipt['original_acquisition_role'] == 'ON'
                    and receipt['counts'] == expected and expected['maps'] == len(domains)
                    and expected['score_audit_queries'] == len(domains) * 5
                    and receipt['decoded_row_SHA_checks_before'] == receipt['decoded_row_SHA_checks_after'] == 48
                    and receipt['source_bytes_unchanged'] is True and receipt['per_hypothesis_DC_clean_maximum_new'] is True
                    and receipt['qualified_SETI_detection'] is False and receipt['calibrated_SNR_FAP'] is False
                    and receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0,
                    'Completed full dual producer receipt differs')
            require(receipt['root_GO_pin'] == {'path': BASE + '/ROOT_GO.json',
                        **{k: admission[BASE + '/ROOT_GO.json'][k] for k in ('bytes', 'sha256')}}
                    and receipt['public_freeze_pin'] == {'path': BASE + '/freeze.json',
                        **{k: admission[BASE + '/freeze.json'][k] for k in ('bytes', 'sha256')}}
                    and receipt['public_freeze_commit'] == go['primary_public_freeze_commit'], 'Producer receipt admission pins differ')
            own = [sources[n, scan] for n in NATIVES]
            require(receipt['source_compact_pre_and_post_pins'] == [{k: s[k] for k in ('path', 'bytes', 'sha256')} for s in own]
                    and receipt['decoded_source_rows'] == own
                    and 0 < receipt['process_CPU_seconds'] <= 600 and 0 < receipt['wall_seconds'] <= 900
                    and 0 < receipt['peak_RSS_bytes'] <= MEMORY_CAP, 'Source/resource receipt evidence differs')
            receipts[job] = receipt
        global np
        import numpy as np
        import h5py
        import hdf5plugin
        require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Supported bitshuffle codec unavailable')
        runtime = {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
                   **{n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}}
        require(all(r['runtime_versions'] == runtime for r in receipts.values()), 'Producer/QA runtime differs')
        drifts, times = np.linspace(-4., 4., 159), np.arange(4) * TSAMP
        require(drifts[79] == 0., 'Exact zero drift differs')
        raw_schema = {'frequency_hz_at_window_reference': ('<f8', (CORE,)),
                      'maximum_robust_box_track_score': ('<f8', (CORE,)), 'winning_drift_hz_s': ('<f8', (CORE,)),
                      'winning_drift_grid_index': ('<i2', (CORE,)), 'winning_window_start_row': ('<i2', (CORE,)),
                      'winning_width_channels': ('<i2', (CORE,)), 'valid_hypothesis_count': ('<i8', (CORE,)),
                      'source_reference_channels': ('<i8', (CORE,)), 'drift_grid_hz_s': ('<f8', (159,))}
        clean_schema = {('DC_clean_' + k): value for k, value in raw_schema.items()
                        if k not in ('frequency_hz_at_window_reference', 'source_reference_channels', 'drift_grid_hz_s')}
        norm_fields = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                       'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channel_interval_half_open'}
        out.mkdir(exist_ok=False)
        created_output = True
        create_json(out / 'INPUT_ADMISSION.json', {'status': 'EXACT21_COMPLETE_SHARDS_AND_SYNTHETIC_QA_ADMITTED',
                    'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256,
                    'root_go_sha256': args.root_go_sha256, 'primary_receipt_sha256s': declarations})
        for scan in ON_SCANS:
            power = np.empty((16, 3 * CHUNK), dtype='<f4')
            for native in NATIVES:
                source = sources[native, scan]
                path = confined(root, source['path'])
                require(path.stat().st_size == source['bytes'] and digest(path) == source['sha256'], 'Whole raw compact SHA differs')
                pins[source['path']] = {k: source[k] for k in ('bytes', 'sha256')}
                with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
                    data = handle['data']
                    require(data.shape == (16, 1, CHUNK) and data.dtype == np.dtype('<f4')
                            and int(data.attrs['original_source_frequency_chunk_origin']) == native * CHUNK
                            and data.attrs['original_source_url'] == source['original_source_url']
                            and data.attrs['original_source_etag'] == source['original_source_etag'], 'Compact HDF5 provenance differs')
                    for declaration in source['decoded_rows']:
                        row = data[declaration['time_row'], 0, :]
                        require(declaration['decoded_bytes'] == CHUNK * 4 and np.isfinite(row).all() and np.all(row >= 0)
                                and hashlib.sha256(row.tobytes()).hexdigest() == declaration['decoded_sha256'], 'Decoded source row SHA differs')
                        offset = (native - 170) * CHUNK
                        power[declaration['time_row'], offset:offset + CHUNK] = row
                        counts['source_decoded_rows'] += 1
                counts['source_compacts'] += 1
            header = sources[171, scan]['original_header']
            scan_empty_channels = []
            for job, (jobscan, domains) in JOBS.items():
                if jobscan != scan:
                    continue
                jobdir = root / BASE / 'results' / job
                maps, audits = metadata(jobdir / 'MAPS.json'), metadata(jobdir / 'SCORE_AUDITS.json')
                primary = 'on20170428_epoch%s_HIP98505' % scan[5]
                for inventory, schema in ((maps, 'SETI_FULL_ON_DUAL_BURST4_MAPS_V1'), (audits, 'SETI_FULL_ON_DUAL_BURST4_SCORE_AUDITS_V1')):
                    require(inventory['schema'] == schema and inventory['primary_id'] == job
                            and inventory['scan_id'] == scan and inventory['primary_scan_id'] == primary, 'Output inventory identity differs')
                require([(v['native_chunk_index'], v['core_q']) for v in maps['records']] == list(domains), 'Saved shard domains differ')
                infos, job_clean_valid, job_empty, job_differing = {}, 0, 0, 0
                for declaration in maps['records']:
                    native, q = declaration['native_chunk_index'], declaration['core_q']
                    key, core0 = (native, q), native * CHUNK + q * CORE
                    channels = np.arange(core0, core0 + CORE, dtype=np.int64)
                    map_id = '%s_native%d_q%03d' % (scan, native, q)
                    require(declaration['path'] == (jobdir / (map_id + '.npz')).relative_to(root).as_posix()
                            and declaration['map_id'] == map_id and declaration['primary_id'] == job
                            and declaration['scan_id'] == scan and declaration['primary_scan_id'] == primary
                            and declaration['original_acquisition_role'] == 'ON'
                            and declaration['reference_channel_interval_half_open'] == [core0, core0 + CORE]
                            and declaration['loaded_channel_interval_half_open'] == [core0 - HALO, core0 + CORE + HALO]
                            and declaration['searched_carriers'] == CORE and declaration['valid_hypotheses_per_carrier'] == 2226
                            and declaration['combined_window_start_rows'] == list(STARTS)
                            and declaration['DC_affected_core'] is (key in DC_DOMAINS), 'Map support/geometry declaration differs')
                    value = archive(declaration)
                    require(set(value) == set(raw_schema) | set(clean_schema), 'Dual-map fields differ')
                    for field, (dtype, shape) in {**raw_schema, **clean_schema}.items():
                        require(value[field].dtype == np.dtype(dtype) and value[field].shape == shape, 'Dual-map dtype/shape differs')
                        if field in raw_schema:
                            require(np.isfinite(value[field]).all(), 'Unrestricted map nonfinite')
                    equal(value['source_reference_channels'], channels, 'Physical carrier channels differ')
                    equal(value['frequency_hz_at_window_reference'], FCH1 + DF * channels, 'Carrier frequencies differ')
                    equal(value['drift_grid_hz_s'], drifts, 'Drift grid differs')
                    equal(value['valid_hypothesis_count'], np.full(CORE, 2226), 'Unrestricted support count differs')
                    if key in DC_DOMAINS:
                        admissible = independent_clean_counts(value['frequency_hz_at_window_reference'], drifts, times)
                    else:
                        distance = min(min(abs(core0 - dc), abs(core0 + CORE - 1 - dc)) for dc in DC_CHANNELS)
                        require(distance > 80 and not any(core0 <= dc < core0 + CORE for dc in DC_CHANNELS), 'Far-DC all-hypothesis geometric proof fails')
                        admissible = np.full(CORE, 2226, dtype=np.int64)
                        counts['far_DC_geometric_proof_cores'] += 1
                    equal(value['DC_clean_valid_hypothesis_count'], admissible, 'Independent DC admissibility count differs')
                    empty = admissible == 0
                    equal(empty, np.isin(channels, DC_CHANNELS), 'Exact forced EMPTY carrier identities differ')
                    scan_empty_channels.extend(channels[empty].tolist())
                    require(np.isneginf(value['DC_clean_maximum_robust_box_track_score'][empty]).all()
                            and np.isnan(value['DC_clean_winning_drift_hz_s'][empty]).all()
                            and all((value['DC_clean_' + field][empty] == -1).all() for field in
                                    ('winning_drift_grid_index', 'winning_window_start_row', 'winning_width_channels'))
                            and np.isfinite(value['DC_clean_maximum_robust_box_track_score'][~empty]).all()
                            and np.isfinite(value['DC_clean_winning_drift_hz_s'][~empty]).all(), 'EMPTY sentinels or nonempty finite values differ')
                    for prefix, admitted in (('', np.ones(CORE, dtype=bool)), ('DC_clean_', ~empty)):
                        indices = value[prefix + 'winning_drift_grid_index'][admitted]
                        require((indices >= 0).all() and (indices < 159).all()
                                and np.isin(value[prefix + 'winning_window_start_row'][admitted], STARTS).all()
                                and np.isin(value[prefix + 'winning_width_channels'][admitted], WIDTHS).all(), 'Winning tuple outside frozen family')
                        equal(value[prefix + 'winning_drift_hz_s'][admitted], drifts[indices], 'Winning drift/index differs')
                    require((value['DC_clean_maximum_robust_box_track_score'][~empty] <= value['maximum_robust_box_track_score'][~empty]).all(), 'Clean maximum exceeds unrestricted maximum')
                    base = (value['frequency_hz_at_window_reference'] - FCH1) / DF
                    rawcenters = np.rint(base[:, None] + value['winning_drift_hz_s'][:, None] * times[None, :] / DF).astype(np.int64)
                    touching = np.zeros(CORE, dtype=bool)
                    for dc in DC_CHANNELS:
                        touching |= (np.abs(rawcenters - dc) <= value['winning_width_channels'][:, None] // 2).any(axis=1)
                    for field in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_drift_grid_index',
                                  'winning_window_start_row', 'winning_width_channels'):
                        equal(value['DC_clean_' + field][~touching], value[field][~touching], 'Eligible unrestricted winner not identical clean winner')
                    if key not in DC_DOMAINS:
                        require(not touching.any(), 'Far-DC saved winner touches DC')
                    cleancenters = np.rint(base[~empty, None] + value['DC_clean_winning_drift_hz_s'][~empty, None] * times[None, :] / DF).astype(np.int64)
                    for dc in DC_CHANNELS:
                        require(not (np.abs(cleancenters - dc) <= value['DC_clean_winning_width_channels'][~empty, None] // 2).any(), 'Saved clean winner touches DC')
                    normal_pin = declaration['normalization']
                    require(normal_pin['path'] == (jobdir / (map_id + '_normalization.json')).relative_to(root).as_posix(), 'Normal path differs')
                    normal = decode(loaded(confined(root, normal_pin['path']), normal_pin))
                    require(set(normal) == norm_fields, 'Normal schema differs')
                    equal(normal['normalization_source_channel_interval_half_open'], [core0, core0 + CORE], 'Normal core coordinates differ')
                    equal(normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normal unmasked counts differ')
                    for field in norm_fields - {'normalization_unmasked_counts', 'normalization_source_channel_interval_half_open'}:
                        require(np.asarray(normal[field]).shape == (16,) and np.isfinite(normal[field]).all(), 'Normal parameter shape/finite differs')
                    require(np.all(np.asarray(normal['row_power_median']) > 0) and np.all(np.asarray(normal['row_residual_MAD_scale']) > 0), 'Normal scale nonpositive')
                    offset = core0 - BAND0
                    equal(np.median(power[:, offset:offset + CORE].astype(np.float64), axis=1), normal['row_power_median'], 'Independent raw4096 core row median differs')
                    if key in DC_DOMAINS:
                        crop_pin = declaration['DC_full_raw_core_crop']
                        require(crop_pin['path'] == (jobdir / (map_id + '_raw16x12096.npz')).relative_to(root).as_posix(), 'DC raw crop path differs')
                        crop = archive(crop_pin)
                        require(set(crop) == {'raw_power_full16x12096', 'absolute_time_rows', 'source_channel_interval_half_open'}
                                and crop['raw_power_full16x12096'].dtype == np.dtype('<f4')
                                and crop['raw_power_full16x12096'].shape == (16, 12096)
                                and crop['absolute_time_rows'].dtype == np.dtype('<i8')
                                and crop['source_channel_interval_half_open'].dtype == np.dtype('<i8'), 'DC full raw crop schema differs')
                        equal(crop['absolute_time_rows'], np.arange(16, dtype=np.int64), 'DC crop rows differ')
                        equal(crop['source_channel_interval_half_open'], [core0 - HALO, core0 + CORE + HALO], 'DC crop physical support differs')
                        raw = crop['raw_power_full16x12096']
                        equal(raw.view(np.uint32), power[:, offset - HALO:offset + CORE + HALO].view(np.uint32), 'DC crop source bits differ')
                        independent = independent_normal(raw)
                        normal_errors = {}
                        for field, expected in independent.items():
                            near(normal[field], expected, 'Independent DC full501 normalization differs')
                            normal_errors[field] = float(np.max(np.abs(np.asarray(normal[field]) - expected)))
                            max_normal_error = max(max_normal_error, normal_errors[field])
                        z = independent_standardized_region(raw, independent)
                        expected = independent_dual_max(z, value['frequency_hz_at_window_reference'], core0 - 81, drifts, times, DC_CHANNELS)
                        score_errors = {}
                        for kind, prefix in (('raw', ''), ('clean', 'DC_clean_')):
                            winner = expected[kind]
                            admitted = winner['valid_hypothesis_count'] > 0
                            near(value[prefix + 'maximum_robust_box_track_score'][admitted], winner['score'][admitted], 'Independent exhaustive dual maximum score differs')
                            score_errors[kind] = float(np.max(np.abs(value[prefix + 'maximum_robust_box_track_score'][admitted] - winner['score'][admitted])))
                            max_remax_error = max(max_remax_error, score_errors[kind])
                            for source_field, expected_field in (('winning_drift_grid_index', 'drift_grid_index'),
                                                                 ('winning_window_start_row', 'window_start_row'),
                                                                 ('winning_width_channels', 'width_channels'),
                                                                 ('valid_hypothesis_count', 'valid_hypothesis_count')):
                                equal(value[prefix + source_field], winner[expected_field], 'Independent exhaustive dual winning tuple/count differs')
                            require(np.isneginf(value[prefix + 'maximum_robust_box_track_score'][~admitted]).all(), 'Independent EMPTY score differs')
                        remax_reports.append({'scan_id': scan, 'native_chunk_index': native, 'core_q': q,
                                              'normalization_absolute_differences': normal_errors,
                                              'maximum_score_absolute_differences': score_errors,
                                              'raw_hypotheses': int(expected['raw']['valid_hypothesis_count'].sum()),
                                              'clean_hypotheses': int(expected['clean']['valid_hypothesis_count'].sum()),
                                              'clean_EMPTY_carriers': int(empty.sum()), 'all4096_carrier_tuples_match': True})
                        counts['DC_full501_normalization_cores'] += 1
                        counts['DC_full501_normalization_rows'] += 16
                        counts['independent_dual_remax_cores'] += 1
                        counts['independent_dual_remax_carriers'] += CORE
                        counts['independent_dual_remax_raw_hypotheses'] += int(expected['raw']['valid_hypothesis_count'].sum())
                        counts['independent_dual_remax_clean_hypotheses'] += int(expected['clean']['valid_hypothesis_count'].sum())
                        del z, expected, crop, raw
                    else:
                        require('DC_full_raw_core_crop' not in declaration, 'Unexpected far-DC raw crop')
                    differing = (value['DC_clean_maximum_robust_box_track_score'] != value['maximum_robust_box_track_score'])
                    for field in ('winning_drift_grid_index', 'winning_window_start_row', 'winning_width_channels'):
                        differing |= value['DC_clean_' + field] != value[field]
                    require(declaration['DC_clean_EMPTY_count'] == int(empty.sum())
                            and declaration['DC_clean_valid_hypothesis_records'] == int(admissible.sum()), 'Map declared clean census differs')
                    infos[key] = {'arrays': value, 'normal': normal, 'record': declaration,
                                  'raw_max': int(np.lexsort((channels, -value['maximum_robust_box_track_score']))[0]),
                                  'clean_max': int(np.lexsort((channels, -value['DC_clean_maximum_robust_box_track_score']))[0])}
                    job_clean_valid += int(admissible.sum())
                    job_empty += int(empty.sum())
                    job_differing += int(differing.sum())
                    counts['maps'] += 1
                    counts['carrier_winners'] += CORE
                    counts['raw_valid_hypothesis_records'] += int(value['valid_hypothesis_count'].sum())
                    counts['clean_valid_hypothesis_records'] += int(admissible.sum())
                    counts['clean_EMPTY_carriers'] += int(empty.sum())
                    counts['raw_core_row_medians'] += 16
                    counts['raw_clean_identical_eligible_winners'] += int((~touching).sum())
                    counts['raw_clean_differing_winners'] += int(differing.sum())
                def tuple_record(key, index, winner_kind):
                    native, q = key
                    info = infos[key]
                    value = info['arrays']
                    prefix = 'DC_clean_' if winner_kind == 'DC_clean' else ''
                    start = int(value[prefix + 'winning_window_start_row'][index])
                    drift = float(value[prefix + 'winning_drift_hz_s'][index])
                    width = int(value[prefix + 'winning_width_channels'][index])
                    frequency = float(value['frequency_hz_at_window_reference'][index])
                    centers = np.rint((frequency - FCH1) / DF + drift * times / DF).astype(np.int64)
                    touched = np.column_stack([np.abs(centers - dc) <= width // 2 for dc in DC_CHANNELS])
                    return {'primary_id': job, 'primary_scan_id': primary, 'primary_target': 'HIP98505', 'scan_id': scan,
                            'original_acquisition_role': 'ON', 'winner_kind': winner_kind,
                            'native_chunk_index': native, 'core_q': q, 'map_id': info['record']['map_id'],
                            'carrier_index_in_core': int(index), 'source_reference_channel': int(value['source_reference_channels'][index]),
                            'frequency_hz_at_window_reference': frequency, 'window_start_row': start,
                            'window_length_rows': 4, 'window_source_rows': list(range(start, start + 4)),
                            'reference_time_mjd': header['tstart'] + (start + .5) * TSAMP / 86400,
                            'drift_grid_index': int(value[prefix + 'winning_drift_grid_index'][index]),
                            'drift_hz_s': drift, 'width_channels': width,
                            'score': float(value[prefix + 'maximum_robust_box_track_score'][index]),
                            'rounded_absolute_centers': centers.tolist(),
                            'width_box_source_channels_inclusive': [[int(c - width // 2), int(c + width // 2)] for c in centers],
                            'frozen_DC_source_channels': list(DC_CHANNELS), 'eligible_DC_untouched': bool(not touched.any()),
                            'rows_intersecting_any_frozen_DC': int(touched.any(axis=1).sum()),
                            'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touched.any(axis=1)).tolist(),
                            'valid_hypothesis_count': int(value[prefix + 'valid_hypothesis_count'][index])}
                require(len(audits['records']) == len(domains) * 5, 'Per-shard scalar query census differs')
                expected_queries = {(n, q, kind) for n, q in domains for kind in ('first', 'midpoint', 'last', 'core_max', 'clean_core_max')}
                seen_queries = set()
                for query in audits['records']:
                    key, kind = (query['native_chunk_index'], query['core_q']), query['query_kind']
                    query_key = key + (kind,)
                    require(query_key in expected_queries and query_key not in seen_queries, 'Unexpected or duplicate scalar audit')
                    seen_queries.add(query_key)
                    info = infos[key]
                    winner_kind = 'DC_clean' if kind == 'clean_core_max' else 'unrestricted'
                    index = {'first': 0, 'midpoint': 2048, 'last': 4095,
                             'core_max': info['raw_max'], 'clean_core_max': info['clean_max']}[kind]
                    expected_tuple = tuple_record(key, index, winner_kind)
                    query_id = 'native%d_q%03d_%s' % (key[0], key[1], kind)
                    require(query['selected_tuple'] == expected_tuple and query['winner_kind'] == winner_kind
                            and query['query_id'] == query_id and query['map_id'] == expected_tuple['map_id']
                            and query['normalization'] == info['record']['normalization']
                            and query['capsule']['path'] == (jobdir / (query_id + '_raw4x503.npz')).relative_to(root).as_posix(), 'Deterministic scalar tuple/identity differs')
                    capsule = archive(query['capsule'])
                    fields = {'raw_power': ('<f4', (4, 503)), 'absolute_time_rows': ('<i8', (4,)),
                              'rounded_absolute_centers': ('<i8', (4,)), 'standardized_row_box_sums': ('<f8', (4,))}
                    require(set(capsule) == set(fields), 'Scalar capsule fields differ')
                    for field, (dtype, shape) in fields.items():
                        require(capsule[field].dtype == np.dtype(dtype) and capsule[field].shape == shape
                                and np.isfinite(capsule[field]).all(), 'Scalar capsule dtype/shape/finite differs')
                    absolute_rows = np.arange(expected_tuple['window_start_row'], expected_tuple['window_start_row'] + 4, dtype=np.int64)
                    centers = np.asarray(expected_tuple['rounded_absolute_centers'], dtype=np.int64)
                    indexes = centers[:, None] - BAND0 + np.arange(-251, 252)[None, :]
                    require(indexes.min() >= 0 and indexes.max() < 3 * CHUNK, 'Scalar capsule source support outside triplet')
                    raw = power[absolute_rows[:, None], indexes]
                    equal(capsule['absolute_time_rows'], absolute_rows, 'Scalar absolute rows differ')
                    equal(capsule['rounded_absolute_centers'], centers, 'Scalar trajectory rounding differs')
                    equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Scalar capsule source bits differ')
                    rows, score = scalar_rows(raw, info['normal'], expected_tuple['width_channels'], absolute_rows)
                    near(capsule['standardized_row_box_sums'], rows, 'Independent scalar501 row arithmetic differs')
                    near(expected_tuple['score'], score, 'Independent scalar501 queried score differs')
                    max_row_error = max(max_row_error, float(np.max(np.abs(capsule['standardized_row_box_sums'] - rows))))
                    max_scalar_error = max(max_scalar_error, abs(expected_tuple['score'] - score))
                    counts['scalar_queries'] += 1
                    counts['scalar_raw_power_cells'] += 4 * 503
                require(seen_queries == expected_queries, 'Scalar matrix incomplete')
                receipt = receipts[job]
                require(receipt['DC_clean_EMPTY_carriers'] == job_empty
                        and receipt['DC_clean_valid_hypothesis_records'] == job_clean_valid
                        and receipt['carrier_tuples_differing_between_clean_and_unrestricted'] == job_differing, 'Shard terminal clean census differs')
                output_pins = receipt['output_byte_pins']
                names = {p['path'] for p in output_pins}
                require(len(names) == len(output_pins) == scope['jobs'][job]['expected_counts']['expected_output_files_including_receipt'] - 1, 'Closed shard output count differs')
                observed = {name for name in pins if name.startswith(jobdir.relative_to(root).as_posix() + '/') and not name.endswith('/EXECUTION_RECEIPT.json')}
                actual = {p.relative_to(root).as_posix() for p in jobdir.iterdir() if p.is_file()}
                require(names == observed and actual == names | {jobdir.relative_to(root).as_posix() + '/EXECUTION_RECEIPT.json'}, 'Closed shard output inventory differs')
                for pin in output_pins:
                    require(pins[pin['path']] == {k: pin[k] for k in ('bytes', 'sha256')}, 'Terminal shard output byte pin differs')
                del infos
                print('PASS_INDEPENDENT_SAVED_FULL_DUAL_SHARD', job, flush=True)
            require(sorted(scan_empty_channels) == list(DC_CHANNELS), 'Exactly3 forced DC EMPTYs required per ON scan')
            del power
        require(counts['maps'] == 2010 and counts['carrier_winners'] == 2010 * CORE
                and counts['raw_valid_hypothesis_records'] == 2010 * CORE * 2226
                and counts['clean_EMPTY_carriers'] == 9 and counts['scalar_queries'] == 10050
                and counts['scalar_raw_power_cells'] == 10050 * 4 * 503
                and counts['raw_core_row_medians'] == 2010 * 16
                and counts['source_compacts'] == 9 and counts['source_decoded_rows'] == 144
                and counts['DC_full501_normalization_cores'] == counts['independent_dual_remax_cores'] == 18
                and counts['DC_full501_normalization_rows'] == 18 * 16
                and counts['independent_dual_remax_carriers'] == 18 * CORE
                and counts['independent_dual_remax_raw_hypotheses'] == 18 * CORE * 2226
                and counts['far_DC_geometric_proof_cores'] == 2010 - 18, 'Independent full dual census incomplete')
        for name, pin in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during QA: ' + name)
        usage = {'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(usage['process_CPU_seconds'] <= CPU_CAP and usage['wall_seconds'] <= WALL_CAP
                and usage['peak_RSS_bytes'] <= MEMORY_CAP, 'QA measured resource bounds exceeded')
        receipt = {'schema': 'SETI_FULL_ON_DUAL_BURST4_INDEPENDENT_QA_V1',
                   'status': 'PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY',
                   'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256, 'driver_sha256': go['driver_sha256'],
                   'root_go_sha256': args.root_go_sha256, 'primary_receipt_sha256s': declarations,
                   'primary_public_freeze_commit': go['primary_public_freeze_commit'],
                   'qa_public_freeze_commit': go['qa_public_freeze_commit'],
                   'synthetic_test_sha256': go['synthetic_test_sha256'], 'synthetic_receipt_pin': synthetic_pin,
                   'counts': counts, 'DC_independent_remax_reports': remax_reports,
                   'max_full501_normalization_absolute_difference': max_normal_error,
                   'max_scalar_row_absolute_difference': max_row_error, 'max_scalar_score_absolute_difference': max_scalar_error,
                   'max_independent_dual_remax_score_absolute_difference': max_remax_error,
                   'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                   'input_byte_pins': pins, 'runtime_versions': runtime, **usage,
                   'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP, 'output_cap_bytes': OUTPUT_CAP,
                   'producer_imported': False, 'detector_imported': False,
                   'all2010_detector_grids_independently_remaximized': False,
                   'all18_DC_affected_core_grids_independently_remaximized': True,
                   'all_remaining_1992_cores_clean_equals_raw_proven_by_geometry': True,
                   'pilot_maps_opened_or_rerun': False, 'new_telescope_HTTP_requests': 0,
                   'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
                   'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
                   'limitations': ['Complete independent dual maximization is restricted to18 DC-affected cores; other cores receive census, raw-core median and five scalar score audits with full-family geometric DC proof.',
                                   'Scalar scores on non-DC cores are conditional on saved MAD/winsorized locations; their raw4096 medians are independently recomputed.',
                                   'Full766 per-scan global rankings require a separate merge with unchanged96 pilot maps; no ranking or sky-origin claim is made here.',
                                   'Three ON scan positions belong to one exposed historical visit; empirical scores are not calibrated SNR/FAP.']}
        create_json(out / 'QA_RECEIPT.json', receipt)
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= OUTPUT_CAP, 'QA output cap exceeded')
        print(receipt['status'], flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            create_json(out / 'QA_FAILURE.json', {'status': 'FAIL_INDEPENDENT_FULL_DUAL_QA',
                        'error_type': type(error).__name__, 'message': str(error), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)
        for handle in locks:
            handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--check-only', action='store_true')
    for name in ('scope-sha256', 'qa-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    parser.add_argument('--primary-receipt', action='append', default=[])
    args = parser.parse_args()
    if args.check_only:
        require(len(ALL_DOMAINS) == 766 and len(PILOT_DOMAINS) == 96 and len(DOMAINS) == 670
                and set(DOMAINS).isdisjoint(PILOT_DOMAINS) and set(DOMAINS) | set(PILOT_DOMAINS) == set(ALL_DOMAINS), 'Remaining domain partition differs')
        require(len(JOBS) == 21 and all(len(v[1]) == (94 if job.endswith('06') else 96) for job, v in JOBS.items()), 'Shard census differs')
        require(set(DC_DOMAINS).issubset(DOMAINS) and len(DC_DOMAINS) == 6, 'DC affected core census differs')
        print(json.dumps({'status': 'PASS_TEXT_ONLY_FULL_DUAL_QA_INTERFACE', 'maps': 2010,
                          'scalar_queries': 10050, 'DC_full_rem_max_cores': 18,
                          'source_compacts': 9, 'source_decoded_rows': 144,
                          'source_values_read': False, 'numerical_modules_imported': False}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact reviewed SHA256s required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'QA source differs')
    declarations = {}
    for declaration in args.primary_receipt:
        job, sha = declaration.split('=', 1)
        require(job in JOBS and job not in declarations and re.fullmatch('[0-9a-f]{64}', sha), 'Unique exact producer receipt required')
        declarations[job] = sha
    require(set(declarations) == set(JOBS), 'Exactly21 completed producer receipts required')
    run(Path(args.root).resolve(), args, declarations)


if __name__ == '__main__':
    main()
