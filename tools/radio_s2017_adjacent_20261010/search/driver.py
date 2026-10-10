"""Frozen zero-download adjacent S2017 native170/172 search, one disjoint job.

Import, scope preparation and --check-only open metadata/code/receipts only.
Actual science requires complete192-range acquisition, actual independent
sourceQA PASS, prospective public freeze/readback and root GO. All q1..254
are new reference carriers in each native. Prior171 outputs stay unchanged.
Numerical detector.search_scan and gap.fixed_profiles are unchanged imports.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
COUNT, CORE, HALO = 1048576, 4096, 4000
NATIVE_CHUNKS = (170, 172)
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP = 1000, 1800
PROCESS_RAM_CAP, AGGREGATE_RAM_CAP, MAX_JOBS = 2 * 1024**3, 4 * 1024**3, 2
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
UNCHANGED_DEPENDENCY_SHAS = {
    'detector': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'gap': 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58',
    'reader': '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}
BASE = 'analysis/s2017_next_native'
STAGE = BASE + '/results/search'
ACQUIRE_STAGE = BASE + '/results/acquire'
ACQUIRE_SCOPE = BASE + '/acquire_scope.json'
SOURCE_QA_PATH = BASE + '/results/source_review/QA_RECEIPT.json'
SOURCE_QA_SCRIPT = BASE + '/qa_sources.py'
SOURCE_PATH = BASE + '/source_manifest_v2.json'
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
ACTIVATION_SHAS = {
    BASE + '/ACTIVATION_SCOPE.json': '838d03d55a3b7a5a8593cf426d8fcb15b2dfb07404812b60b051fdd214efa6cc',
    BASE + '/ACTIVATION_SCOPE_V2.json': '69d2883e044eafba286b8cc9fe28f96f8e737737d125a560505a66a6d86dd30c'}
SELECTION_SHA = '689662401dd48ba1a2a65569815cc80c63fed875eaddfda06abb63cd67afa840'
FULLNORM = 'full1048576-channel row median computed on raw float32, then profile float64 promotion'
SAFE_Q = tuple(range(1, 255))
BATCHES = {'batch01': SAFE_Q[:85], 'batch02': SAFE_Q[85:170], 'batch03': SAFE_Q[170:]}
JOBS = {f'native{native}_{batch}': {'native_chunk_index': native, 'batch_id': batch, 'qs': qs}
        for native in NATIVE_CHUNKS for batch, qs in BATCHES.items()}
SOURCE_QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
    'source_descriptors': 192, 'exact_range_records': 192, 'unique_source_ranges': 192,
    'durable_raw_sidecars': 192, 'compressed_source_chunks': 192, 'decoded_rows': 192}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Relative confined path required')
    path = root / relative
    require(path.resolve().is_relative_to(root), 'Path outside frozen workspace')
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_pins(root, scope):
    for name, pin in scope['pinned_metadata_code_and_prerequisites'].items():
        path = confined(root, name)
        require(path.suffix.lower() not in ('.h5', '.hdf5', '.npy', '.npz'), 'Preflight may not open power files')
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Frozen file differs: ' + name)


def prerequisite_contract(root, scope):
    gates = scope['prerequisites']
    expected_paths = {'acquisition': ACQUIRE_STAGE + '/ACQUISITION_RESULT.json',
        'source_QA': SOURCE_QA_PATH}
    values = {}
    for key, expected in expected_paths.items():
        gate = gates[key]
        require(gate['path'] == expected and re.fullmatch('[0-9a-f]{64}', gate['sha256']), 'Wrong prerequisite path/SHA')
        path = confined(root, gate['path'])
        require(digest(path) == gate['sha256'], 'Actual reviewed prerequisite changed: ' + key)
        values[key] = json.loads(path.read_bytes())
        require(values[key]['status'] == gate['status'], 'Actual reviewed prerequisite status changed')
    acquisition, qa = (values[key] for key in expected_paths)
    acquisition_scope = json.loads(confined(root, ACQUIRE_SCOPE).read_bytes())
    acquisition_scope_sha = digest(root / ACQUIRE_SCOPE)
    source_sha = digest(confined(root, scope['source_manifest_path']))
    require(source_sha == SOURCE_SHA, 'Exact corrected V2 metadata source required')
    freeze = acquisition['public_freeze_commit']
    require(re.fullmatch('[0-9a-f]{40}', freeze), 'Actual acquisition public freeze commit required')
    require(acquisition['schema'] == 'SETI_S2017_ADJACENT170_172_ACQUISITION_RECEIPT_V1'
        and acquisition['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
        and acquisition['scope_sha256'] == acquisition_scope_sha
        and acquisition['driver_sha256'] == digest(confined(root, BASE + '/acquire_driver.py'))
        and acquisition['source_manifest_sha256'] == source_sha
        and acquisition['new_telescope_HTTP_requests'] == 192
        and acquisition['source_range_count_authenticated'] == 192
        and acquisition['new_telescope_BODY_bytes'] == 597792529
        and acquisition['reserved_BODY_upper_bound_bytes'] == 597792721
        and acquisition['complete_compact_files'] == 12 and acquisition['decoded_row_SHA256s'] == 192
        and acquisition['standalone_durable_raw_range_files'] == 192
        and acquisition['repeated_source_GETs'] == 0
        and [(record['native_chunk_index'], record['scan_id']) for record in acquisition['decoded_files']]
            == [(native, label) for native in NATIVE_CHUNKS for label in SCANS],
        'Actual COMPLETE aggregate192-range/192-row acquisition required before every search job')
    require(acquisition_scope['source_manifest_path'] == SOURCE_PATH
        and acquisition_scope['root_activation_path'] == BASE + '/ACTIVATION_SCOPE_V2.json'
        and acquisition_scope['pinned_metadata_and_code'][SOURCE_PATH]['sha256'] == source_sha,
        'Actual acquisition scope does not bind selected source metadata')
    for record in acquisition['decoded_files']:
        native, label = record['native_chunk_index'], record['scan_id']
        require(record['array_file'] == f'native{native}_{label}.compact.h5'
            and record['shape'] == [16, 1, COUNT] and record['source_channel0'] == native * COUNT
            and record['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', record['file_sha256'])
            and [row['time_row'] for row in record['decoded_rows']] == list(range(16))
            and all(row['decoded_bytes'] == COUNT * 4
                    and re.fullmatch('[0-9a-f]{64}', row['decoded_sha256'])
                    for row in record['decoded_rows']), 'All192 authenticated decoded-row records required')
    raw_records = acquisition['raw_range_records']
    require([(row['native_chunk_index'], row['scan_id'], row['time_row']) for row in raw_records]
        == [(native, label, index) for native in NATIVE_CHUNKS for label in SCANS for index in range(16)]
        and all(row['filter_mask'] == 0 and row['fsync_before_HDF5'] is True
                and re.fullmatch('[0-9a-f]{64}', row['raw_sha256'])
                and row['compact_raw_roundtrip_sha256'] == row['raw_sha256']
                for row in raw_records), 'All192 source raw-record SHA/closed-compact proofs required')
    require(qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
        and qa['status'] == 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
        and qa['acquisition_receipt_sha256'] == gates['acquisition']['sha256']
        and qa['source_manifest_sha256'] == source_sha
        and qa['scope_sha256'] == acquisition_scope_sha
        and qa['driver_sha256'] == acquisition['driver_sha256']
        and qa['public_freeze_commit'] == freeze
        and qa['counts'] == SOURCE_QA_COUNTS
        and qa['qa_script_sha256'] == digest(confined(root, SOURCE_QA_SCRIPT))
        and qa['compact_input_byte_pins'] == {
            ACQUIRE_STAGE + '/' + record['array_file']: {'sha256': record['file_sha256'], 'bytes': record['bytes']}
            for record in acquisition['decoded_files']}
        and qa['source_range_raw_record_sha256'] == canonical_sha(acquisition['raw_range_records'])
        and qa['decoded_file_row_record_sha256'] == canonical_sha(acquisition['decoded_files'])
        and qa['source_range_request_record_sha256'] == canonical_sha(acquisition['value_read_requests'])
        and qa['detector_or_score_rerun'] is False
        and qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0,
        'Actual independent192-row compressed/decoded source provenance QA PASS required')
    return acquisition


def contract(root, scope):
    job_id = scope['job_id']
    require(job_id in JOBS, 'Unknown frozen disjoint adjacent-native job')
    job = JOBS[job_id]
    native, batch, qs = job['native_chunk_index'], job['batch_id'], list(job['qs'])
    c0 = native * COUNT
    expected = {'schema': 'SETI_S2017_ADJACENT_SAFE_INTERIOR_SEARCH_V1', 'job_id': job_id,
        'native_chunk_index': native, 'batch_id': batch, 'core_q_indices': qs,
        'scan_order': list(SCANS), 'rows_per_scan': 16, 'native_chunk_count': 343,
        'source_channel_interval_half_open': [c0, c0 + COUNT],
        'excluded_previously_searched_q': [], 'excluded_edge_q': [0, 255],
        'core_channel_count': CORE, 'crop_halo_channels': HALO,
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}, 'widths_channels': [1, 3],
        'valid_hypotheses_per_carrier': 1570, 'search_ON_maps': 3 * len(qs),
        'rank_count_per_ON_per_job': 20, 'display_suppression_channels': 3,
        'top20_selection_domain': 'all saved carrier maxima from all cores of this native/job, separately for each ON',
        'fixed_profile_ranks_per_ON_per_job': 3, 'expected_fixed_profiles': 9,
        'profile_shift_channels': 0, 'profile_halfwidth_channels': 64,
        'fixed_profile_normalization': FULLNORM, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
        'memory_cap_bytes_per_process': PROCESS_RAM_CAP, 'memory_cap_bytes_aggregate': AGGREGATE_RAM_CAP,
        'simultaneous_search_jobs_max': MAX_JOBS, 'runtime_package_versions': VERSIONS,
        'hdf5_version': '1.14.6', 'output_stage': STAGE + '/' + job_id,
        'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
        'new_visit': False, 'new_acquisition_by_search': False, 'independent_tests_claimed': False,
        'prior_native171_search_rerun': False, 'retry_resume_or_rerun_authorized': False,
        'blind_independent_confirmation': False, 'OFF_veto_applied': False,
        'qualified_sky_detection': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'source_manifest_path': SOURCE_PATH}
    require(all(scope.get(key) == value for key, value in expected.items()), 'Scope differs from implemented adjacent job')
    require(digest(__file__) == scope['driver_sha256'], 'Driver differs from prospective public freeze')
    check_pins(root, scope)
    require(scope['root_activation_SHA256s'] == ACTIVATION_SHAS
        and all(digest(confined(root, path)) == sha for path, sha in ACTIVATION_SHAS.items()),
        'Exact original ascending adjacency selection and corrected V2 activation required')
    for path in ACTIVATION_SHAS:
        activation = json.loads(confined(root, path).read_bytes())
        require(activation['selection_canonical_sha256'] == SELECTION_SHA
            and canonical_sha(activation['selection']) == SELECTION_SHA
            and activation['selection']['native_chunks'] == list(NATIVE_CHUNKS)
            and activation['selection']['safe_q_indices'] == list(SAFE_Q)
            and activation['selection']['full_safe_partitions'] == [list(qs) for qs in BATCHES.values()],
            'Fixed ascending before-values selection differs')
    require(scope['unchanged_original_dependency_SHA256s'] == UNCHANGED_DEPENDENCY_SHAS
        and set(scope['code_paths']) == set(UNCHANGED_DEPENDENCY_SHAS)
        and all(digest(confined(root, scope['code_paths'][key])) == sha
                for key, sha in UNCHANGED_DEPENDENCY_SHAS.items()),
        'Detector, fixed profiles, and codec reader must remain byte-for-byte unchanged')
    acquisition = prerequisite_contract(root, scope)
    manifest = json.loads(confined(root, SOURCE_PATH).read_bytes())
    require(manifest['schema'] == 'SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1'
        and manifest['native_chunk_indices'] == list(NATIVE_CHUNKS)
        and manifest['spectral_values_read'] is manifest['spectral_payload_fetched'] is False
        and manifest['total_future_spectral_payload_bytes'] == 597792529,
        'Frozen pre-value adjacent source metadata required')
    aggregate_payload = 0
    for other_native in NATIVE_CHUNKS:
        unit = manifest['by_native_chunk'][str(other_native)]
        unit_payload = 0
        require(unit['native_chunk_index'] == other_native
            and unit['physical_channel_interval_half_open'] == [other_native * COUNT, (other_native + 1) * COUNT]
            and [item['label'] for item in unit['sources']] == list(SCANS), 'Aggregate native source geometry differs')
        for item in unit['sources']:
            rows = item['chunks']
            require([row['time_row'] for row in rows] == list(range(16)), 'Every source needs16 new row descriptors')
            subtotal = 0
            for row in rows:
                offset, size = row['byte_offset'], row['stored_size']
                require(row['chunk_origin'] == [row['time_row'], 0, other_native * COUNT]
                    and row['filter_mask'] == 0 and row['decoded_size'] == COUNT * 4
                    and 0 < size <= COUNT * 4 and 0 <= offset < offset + size <= item['source_file_bytes']
                    and row['byte_range'] == f'bytes={offset}-{offset+size-1}', 'Exact new payload descriptor differs')
                subtotal += size
            require(item['future_spectral_payload_bytes'] == subtotal, 'Per-source payload ledger differs')
            unit_payload += subtotal
        require(unit_payload == unit['total_future_spectral_payload_bytes'], 'Per-native payload ledger differs')
        aggregate_payload += unit_payload
    require(aggregate_payload == 597792529, 'Aggregate192-range payload ledger differs')
    source = manifest['by_native_chunk'][str(native)]
    require(source['native_chunk_index'] == native
        and source['physical_channel_interval_half_open'] == [c0, c0 + COUNT]
        and [item['label'] for item in source['sources']] == list(SCANS)
        and [item['role'].upper() for item in source['sources']] == ['ON', 'OFF'] * 3,
        'Wrong native/scans/roles in selected source subset')
    anchor = min(item['current_header']['data_attributes']['tstart'] for item in source['sources'])
    times, previous_end = [], -math.inf
    for item in source['sources']:
        header, attrs, rows = item['current_header'], item['current_header']['data_attributes'], item['chunks']
        require(header['dataset_shape'] == [16, 1, 359661568] and header['dataset_chunks'] == [1, 1, COUNT]
            and header['dtype_exact'] == '<f4' and attrs['fch1'] * 1e6 == FCH1
            and attrs['foff'] * 1e6 == DF and attrs['tsamp'] == TSAMP
            and [row['time_row'] for row in rows] == list(range(16))
            and all(row['chunk_origin'] == [row['time_row'], 0, c0] for row in rows),
            'Verified source geometry/grid/physical descriptors differ')
        start = (attrs['tstart'] - anchor) * 86400
        require(start >= previous_end, 'Actual scan times overlap or are unordered')
        previous_end = start + 16 * TSAMP
        times.extend(start + (row + .5) * TSAMP for row in range(16))
    max_profile_displacement = math.ceil(4 * (max(times) - min(times)) / abs(DF)) + 64
    require(max_profile_displacement < CORE and 2 * math.ceil(4 * 15 * TSAMP / abs(DF)) + 1 == 785,
        'Fixed six-scan profiles or drift family lack full native support')
    require(all(1 <= q <= 254 for q in qs), 'Edge or nonfrozen core admitted')
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Runtime version differs: ' + package)
    return source, float(anchor), acquisition


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def search(root, scope, source, anchor, acquisition, out):
    import numpy as np
    reader = load_module('s2017_extension_reader', confined(root, scope['code_paths']['reader']))
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'HDF5 version differs')
    arrays, verified = {}, []
    native, c0 = scope['native_chunk_index'], scope['native_chunk_index'] * COUNT
    acquire = root / ACQUIRE_STAGE
    selected_files = [record for record in acquisition['decoded_files'] if record['native_chunk_index'] == native]
    require([record['scan_id'] for record in selected_files] == list(SCANS), 'Six canonical source records per native required')
    for record in selected_files:
        label = record['scan_id']
        require(record['array_file'] == f'native{native}_{label}.compact.h5' and record['shape'] == [16, 1, COUNT]
            and record['source_channel0'] == c0
            and [row['time_row'] for row in record['decoded_rows']] == list(range(16)), 'Compact row/frame metadata differs')
        path = confined(acquire, record['array_file'])
        require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'], 'Compact file pin differs')
        item = next(item for item in source['sources'] if item['label'] == label)
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                and int(data.attrs['original_source_frequency_chunk_origin']) == c0
                and data.attrs['original_source_url'] == item['url']
                and data.attrs['original_source_etag'] == item['etag'], 'Compact source identity differs')
            values = data[:, 0, :]
        require(np.isfinite(values).all() and (values >= 0).all(), 'Invalid full native power')
        for row in record['decoded_rows']:
            require(row['decoded_bytes'] == COUNT * 4 and
                hashlib.sha256(values[row['time_row']].tobytes(order='C')).hexdigest() == row['decoded_sha256'],
                'Authenticated full-native decoded row SHA differs')
        arrays[label] = values
        verified.append({'scan_id': label, 'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
    normalization = {'source_channel0': c0, 'count': COUNT,
        'row_power_medians': {label: np.median(arrays[label], axis=1).tolist() for label in SCANS},
        'method': FULLNORM, 'raw_dtype': '<f4'}
    save(out / 'NORMALIZATION.json', normalization)
    detector = load_module('s2017_extension_unchanged_detector', confined(root, scope['code_paths']['detector']))
    cfg = detector.Config(widths=(1, 3))
    drifts, dt = np.linspace(-4.0, 4.0, 785), np.arange(16) * TSAMP
    mismatch = float((drifts[1] - drifts[0]) * dt[-1] / (2 * abs(DF)))
    require(mismatch <= .5 + 1e-12, 'Own drift grid exceeds half-channel mismatch')
    qs, tops, receipts = scope['core_q_indices'], {}, []
    for label in ONS:
        header = next(item['current_header']['data_attributes'] for item in source['sources'] if item['label'] == label)
        columns = {'channels': [], 'scores': [], 'drifts': [], 'widths': [], 'qs': []}
        for q in qs:
            first, crop0, cropstop = c0 + q * CORE, q * CORE - HALO, (q + 1) * CORE + HALO
            channels = np.arange(first, first + CORE)
            frequencies = FCH1 + DF * channels
            scan = detector.Scan(label, 'ON', arrays[label][:, crop0:cropstop], header['tstart'], TSAMP,
                FCH1, DF, c0 + crop0, channels)
            result, _ = detector.search_scan(scan, frequencies, dt, drifts, cfg)
            score = result['maximum_robust_box_track_score']
            require(np.isfinite(score).all() and np.all(result['valid_hypothesis_count'] == 1570), 'Incomplete ON core map')
            numeric = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
            numeric.update(source_reference_channels=channels, drift_grid_hz_s=drifts)
            path = out / (label + '_q%03d_all_carriers.npz' % q)
            np.savez(path, **numeric)
            normalization_path = out / (label + '_q%03d_normalization.json' % q)
            save(normalization_path, result['normalization'])
            receipts.append({'scan_id': label, 'core_q': q, 'path': path.name,
                'sha256': digest(path), 'bytes': path.stat().st_size, 'searched_carriers': CORE,
                'valid_hypotheses_per_carrier': 1570,
                'reference_channel_interval_half_open': [first, first + CORE],
                'normalization': {'path': normalization_path.name, 'sha256': digest(normalization_path),
                                  'bytes': normalization_path.stat().st_size}})
            for key, value in (('channels', channels), ('scores', score), ('drifts', result['winning_drift_hz_s']),
                ('widths', result['winning_width_channels']), ('qs', np.full(CORE, q, dtype=np.int16))):
                columns[key].append(value)
            save(out / 'DRIFT_CHECKPOINT.json', {'completed_ON_maps': len(receipts), 'expected_ON_maps': 3 * len(qs),
                'complete': len(receipts) == 3 * len(qs), 'receipts': receipts})
            print('SEARCHED_S2017_NEW_ADJACENT_INTERIOR_CORE', scope['job_id'], label, q, flush=True)
        columns = {key: np.concatenate(value) for key, value in columns.items()}
        chosen = []
        for index in np.lexsort((columns['channels'], -columns['scores'])):
            index = int(index)
            if all(abs(int(columns['channels'][index]) - int(columns['channels'][other])) > 3 for other in chosen):
                chosen.append(index)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Incomplete global per-batch top20')
        reference = (header['tstart'] - anchor) * 86400 + .5 * TSAMP
        tops[label] = [{'track_id': label + '_visit20170428_Sband_' + scope['job_id'] + '_rank_%02d' % rank,
            'family': 'S2017_adjacent_safe_interior_' + scope['job_id'],
            'originating_scan': label, 'originating_role': 'ON', 'display_rank': rank,
            'source_reference_channel': int(columns['channels'][index]),
            'reference_frequency_hz': float(FCH1 + DF * columns['channels'][index]),
            'reference_seconds_from_anchor': float(reference), 'drift_hz_s': float(columns['drifts'][index]),
            'width_channels': int(columns['widths'][index]),
            'maximum_robust_box_track_score': float(columns['scores'][index]),
            'reference_core_tile': int(columns['qs'][index]), 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'}
            for rank, index in enumerate(chosen, 1)]
        save(out / 'DRIFT_TOP20.json', tops)
        del columns
    gap = load_module('s2017_extension_unchanged_profiles', confined(root, scope['code_paths']['gap']))
    gap.ROOT, gap.np = root, np
    gap.FCH1, gap.DF, gap.TSAMP, gap.C0, gap.COUNT = FCH1, DF, TSAMP, c0, COUNT
    gap.NORMALIZATION_PATH = (out / 'NORMALIZATION.json').relative_to(root).as_posix()
    profiles = gap.fixed_profiles(arrays, source, normalization, tops, anchor, out)
    require(profiles['profile_count'] == 9, 'Incomplete fixed nine-profile batch family')
    for record in selected_files:
        require(digest(confined(acquire, record['array_file'])) == record['file_sha256'], 'Native input changed during search')
    return {'verified_inputs': verified, 'MJD_anchor': anchor,
        'acquisition_receipt_sha256': scope['prerequisites']['acquisition']['sha256'],
        'source_QA_receipt_sha256': scope['prerequisites']['source_QA']['sha256'],
        'native_chunk_index': native,
        'search_summary': {'completed_ON_maps': len(receipts), 'cores_per_ON': len(qs),
            'carriers_per_ON': len(qs) * CORE, 'ON_carrier_maximum_records': 3 * len(qs) * CORE,
            'correlated_drift_width_combinations': 3 * len(qs) * CORE * 1570,
            'drift_grid_count': 785, 'widths_channels': [1, 3], 'half_grid_mismatch_channels': mismatch,
            'bandwidth_per_ON_hz': len(qs) * CORE * abs(DF), 'native_chunk_fraction_searched': len(qs) * CORE / COUNT,
            'score_definition': 'unchanged row-MAD-standardized odd-box track sum/sqrt(Nrow*width)',
            'normalization': 'unchanged separate4096-carrier core per map and501-channel filter',
            'reference_time': 'each ON first integration midpoint; actual header epochs for fixed six-scan profiles'},
        'fixed_profile_summary': profiles, 'top20_entries': 60,
        'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version}}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual prospective public freeze commit required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_scope_sha256)
        and digest(args.scope) == args.expected_scope_sha256, 'Frozen scope SHA differs')
    scope = json.loads(Path(args.scope).read_bytes())
    require(Path(args.scope).resolve() == root / BASE / 'search/scopes' / (scope['job_id'] + '.json'),
            'Wrong frozen batch scope path')
    source, anchor, acquisition = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_CODE_PREREQUISITES_ONLY_NO_VALUES_NO_HTTP',
            'job_id': scope['job_id'], 'scope_sha256': args.expected_scope_sha256,
            'cores_per_ON': len(scope['core_q_indices']), 'new_telescope_HTTP_requests': 0}))
        return
    require(args.root_go_after_review, 'Root prospective review, public readback, and GO required')
    stage = root / STAGE
    stage.mkdir(parents=True, exist_ok=True)
    out = confined(root, scope['output_stage'])
    handles, slot_index, receipt = [], None, None
    def deadline(signum, frame):
        raise TimeoutError('Frozen extension CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (PROCESS_RAM_CAP, PROCESS_RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        # Retained lock files are intentional; kernel ownership is released on close.
        batch_lock = (stage / (scope['job_id'] + '_ACTIVE_FLOCK.lock')).open('a+b')
        handles.append(batch_lock)
        fcntl.flock(batch_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_lock = (root / BASE / 'ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        handles.append(source_lock)
        fcntl.flock(source_lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        for i in range(MAX_JOBS):
            slot = (root / BASE / ('ACTIVE_SCIENCE_SLOT_%d_FLOCK.lock' % i)).open('a+b')
            try:
                fcntl.flock(slot.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                slot.close()
            else:
                handles.append(slot)
                slot_index = i
                break
        require(slot_index is not None, 'At most two extension jobs admitted; no hidden waiting or extra memory')
        out.mkdir(parents=True, exist_ok=False)
        receipt = {'status': 'IN_PROGRESS', 'phase': 'previously_unsearched_adjacent_native_job',
            'job_id': scope['job_id'], 'native_chunk_index': scope['native_chunk_index'],
            'batch_id': scope['batch_id'], 'scope_sha256': args.expected_scope_sha256,
            'driver_sha256': digest(__file__), 'public_freeze_commit': args.freeze_commit,
            'source_manifest_sha256': digest(confined(root, scope['source_manifest_path'])),
            'core_q_indices': scope['core_q_indices'], 'simultaneous_job_slot': slot_index,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes_per_process': PROCESS_RAM_CAP,
            'memory_cap_bytes_aggregate': AGGREGATE_RAM_CAP, 'simultaneous_search_jobs_max': MAX_JOBS,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'new_visit': False, 'new_acquisition_by_search': False, 'prior_native171_search_rerun': False,
            'independent_tests_claimed': False, 'qualified_sky_detection': False, 'OFF_veto_applied': False,
            'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'retry_resume_or_rerun_authorized': False, 'limitations': scope['limitations']}
        save(out / 'INPUT_PINS.json', {'scope_sha256': args.expected_scope_sha256,
            'public_freeze_commit': args.freeze_commit, 'pins': scope['pinned_metadata_code_and_prerequisites']})
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        summary = search(root, scope, source, anchor, acquisition, out)
        check_pins(root, scope)
        require(digest(args.scope) == args.expected_scope_sha256, 'Frozen scope changed during execution')
        use = measured(started)
        require(use['process_CPU_seconds_including_imports'] <= CPU_CAP and use['wall_seconds_including_imports'] <= WALL_CAP
            and use['peak_RSS_bytes'] <= PROCESS_RAM_CAP, 'Measured process resource cap exceeded')
        receipt.update(summary, **use, status='COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'job_id': scope['job_id'], **use}), flush=True)
    except BaseException as error:
        if receipt is not None:
            receipt.update(status='INCOMPLETE_ADJACENT_JOB_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
                error_type=type(error).__name__, error=str(error), **measured(started))
            save(out / 'EXECUTION_RECEIPT.json', receipt)
            save(out / 'FAILURE_RECEIPT.json', receipt)
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
