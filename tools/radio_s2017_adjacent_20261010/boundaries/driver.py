"""Source-only preparation for two previously unsearched S2017 joined boundaries.

Import and --check-only read code/metadata/receipt JSON only. No HTTP operation
exists in this driver. A separately published scope, actual complete acquisition
and source QA, exact public readback, and root GO precede any scientific values.
The detector and gap.fixed_profiles numerical functions remain byte-identical.
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
PAIRS = {'pair170_171': (170, 171), 'pair171_172': (171, 172)}
COUNT, JOINED, CORE, HALO, QS = 1048576, 2097152, 4096, 4000, (255, 256)
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, MEMORY_CAP = 180, 1800, 2 * 1024**3
AGGREGATE_MEMORY_CAP, MAX_SCIENCE_JOBS = 4 * 1024**3, 2
SOURCE_LOCK = 'analysis/s2017_next_native/ACTIVE_FAMILY_FLOCK.lock'
SCIENCE_LOCKS = tuple('analysis/s2017_next_native/ACTIVE_SCIENCE_SLOT_%d_FLOCK.lock' % slot for slot in range(2))
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
DEPENDENCY_SHAS = {
    'detector': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'gap': 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58',
    'reader': '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}
BASE = 'analysis/s2017_next_native/boundaries'
STAGE = BASE + '/results'
NEW_SOURCE = 'analysis/s2017_next_native/source_manifest_v2.json'
NEW_ACQUISITION = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
NEW_ACQUISITION_SCOPE = 'analysis/s2017_next_native/acquire_scope.json'
NEW_ACQUISITION_DRIVER = 'analysis/s2017_next_native/acquire_driver.py'
NEW_SOURCE_QA = 'analysis/s2017_next_native/results/source_review/QA_RECEIPT.json'
NEW_SOURCE_QA_CODE = 'analysis/s2017_next_native/qa_sources.py'
NEW_SOURCE_QA_STATUS = 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
NEW_SOURCE_QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
    'source_descriptors': 192, 'exact_range_records': 192, 'unique_source_ranges': 192,
    'durable_raw_sidecars': 192, 'compressed_source_chunks': 192, 'decoded_rows': 192}
PRIOR_SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
PRIOR_ACQUISITION = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
PRIOR_SOURCE_QA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
PRIOR_FULL_QA = 'analysis/s2017_full_band/results/review/QA_RECEIPT.json'
PRIOR_FIXED_PINS = {
    PRIOR_SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    PRIOR_ACQUISITION: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    PRIOR_SOURCE_QA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f',
    PRIOR_FULL_QA: 'e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f'}
JOINED_NORM = 'median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)'


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
        ensure_ascii=True, allow_nan=False).encode('utf8')).hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target)


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Confined relative path required')
    result = root / relative
    require(result.resolve().is_relative_to(root), 'Frozen path leaves workspace')
    return result


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_pins(root, scope):
    for name, pin in scope['pinned_metadata_code_and_prerequisites'].items():
        path = confined(root, name)
        require(path.suffix.lower() not in ('.h5', '.hdf5', '.npz', '.npy'),
                'Prevalue pins may contain only metadata/code/receipt files')
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'],
                'Frozen metadata/code/receipt differs: ' + name)


def source_contract(source, chunk):
    require(source['native_chunk_index'] == chunk
        and source['physical_channel_interval_half_open'] == [chunk * COUNT, (chunk + 1) * COUNT]
        and [item['label'] for item in source['sources']] == list(SCANS)
        and [item['role'].upper() for item in source['sources']] == ['ON', 'OFF'] * 3,
        'Actual native interval, six scans or alternating roles differ')
    for item in source['sources']:
        head, attrs = item['current_header'], item['current_header']['data_attributes']
        require(head['dataset_shape'] == [16, 1, 359661568]
            and head['dataset_chunks'] == [1, 1, COUNT] and head['dtype_exact'] == '<f4'
            and attrs['fch1'] * 1e6 == FCH1 and attrs['foff'] * 1e6 == DF
            and attrs['tsamp'] == TSAMP and len(item['chunks']) == 16,
            'Actual source header/frame differs')
        for i, row in enumerate(item['chunks']):
            require(row['time_row'] == i and row['chunk_origin'] == [i, 0, chunk * COUNT]
                and row['decoded_size'] == COUNT * 4 and row['filter_mask'] == 0
                and row['stored_size'] > 0 and row['byte_offset'] >= 0
                and row['byte_offset'] + row['stored_size'] <= item['source_file_bytes']
                and row['byte_range'] == f"bytes={row['byte_offset']}-{row['byte_offset']+row['stored_size']-1}",
                'Source byte/row descriptor differs')


def record_contract(records, chunks):
    expected = [(chunk, label) for chunk in chunks for label in SCANS]
    require([(record['native_chunk_index'], record['scan_id']) for record in records] == expected,
            'Require exactly the frozen ordered native compact files')
    for record in records:
        chunk = record['native_chunk_index']
        require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == chunk * COUNT
            and [row['time_row'] for row in record['decoded_rows']] == list(range(16))
            and all(row['decoded_bytes'] == COUNT * 4 and re.fullmatch('[0-9a-f]{64}', row['decoded_sha256'])
                    for row in record['decoded_rows'])
            and re.fullmatch('[0-9a-f]{64}', record['file_sha256']) and record['bytes'] > 0,
            'Frozen compact full-row identities differ')


def admission(root, scope):
    pins = scope['pinned_metadata_code_and_prerequisites']
    require(all(pins.get(name, {}).get('sha256') == sha for name, sha in PRIOR_FIXED_PINS.items()),
            'Original native171 actual source/search QA pins must be preserved')
    prior = json.loads(confined(root, PRIOR_ACQUISITION).read_bytes())
    prior_qa = json.loads(confined(root, PRIOR_SOURCE_QA).read_bytes())
    full_qa = json.loads(confined(root, PRIOR_FULL_QA).read_bytes())
    require(prior['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
        and prior['complete_compact_files'] == 6 and prior['decoded_row_SHA256s'] == 96
        and prior['source_manifest_sha256'] == PRIOR_FIXED_PINS[PRIOR_SOURCE]
        and prior['total_cumulative_telescope_HTTP_requests'] == 96,
        'Actual original native171 complete acquisition required')
    require(prior_qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and prior_qa['acquisition_receipt_sha256'] == PRIOR_FIXED_PINS[PRIOR_ACQUISITION]
        and prior_qa['counts']['decoded_rows'] == 96 and prior_qa['counts']['compact_files'] == 6
        and prior_qa['counts']['native_row_medians_recomputed'] == 96
        and prior_qa['detector_or_score_rerun'] is False,
        'Actual original native171 full-row/source QA required')
    require(full_qa['status'] == 'PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS'
        and full_qa['counts']['maps'] == 759 and full_qa['counts']['raw_cells_bitwise_checked'] == 334368,
        'Actual prior safe-interior extension must stay complete')
    manifest = json.loads(confined(root, NEW_SOURCE).read_bytes())
    require(manifest['schema'] == 'SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1'
        and set(manifest['by_native_chunk']) == {'170', '172'}, 'Exactly fixed new170/172 source metadata required')
    acquired = json.loads(confined(root, NEW_ACQUISITION).read_bytes())
    acquire_scope = json.loads(confined(root, NEW_ACQUISITION_SCOPE).read_bytes())
    require(acquire_scope['schema'] == 'SETI_S2017_ADJACENT170_172_ACQUISITION_SCOPE_V1'
        and acquire_scope['native_chunk_indices'] == [170, 172]
        and acquire_scope['source_manifest_path'] == NEW_SOURCE
        and acquire_scope['output_stage'] == NEW_ACQUISITION.rsplit('/', 1)[0]
        and acquire_scope['family_lock_path'] == SOURCE_LOCK
        and acquire_scope['driver_sha256'] == pins[NEW_ACQUISITION_DRIVER]['sha256']
        and acquire_scope['exact_expected_payload_BODY_bytes'] == 597792529
        and acquire_scope['reserved_payload_BODY_upper_bound_bytes'] == 597792721,
        'Exact separately frozen adjacent acquisition contract required')
    require(acquired['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
        and acquired['source_manifest_sha256'] == pins[NEW_SOURCE]['sha256']
        and acquired['scope_sha256'] == pins[NEW_ACQUISITION_SCOPE]['sha256']
        and acquired['driver_sha256'] == pins[NEW_ACQUISITION_DRIVER]['sha256']
        and acquired['new_telescope_HTTP_requests'] == 192
        and acquired['new_telescope_BODY_bytes'] == 597792529
        and acquired['reserved_BODY_upper_bound_bytes'] == 597792721
        and acquired['source_range_count_authenticated'] == 192
        and acquired['complete_compact_files'] == 12 and acquired['decoded_row_SHA256s'] == 192
        and re.fullmatch('[0-9a-f]{40}', acquired['public_freeze_commit']),
        'Actual new adjacent-source COMPLETE acquisition required')
    record_contract(acquired['decoded_files'], (170, 172))
    gate = scope['new_source_QA']
    require(gate['path'] == NEW_SOURCE_QA and gate['status'] == NEW_SOURCE_QA_STATUS
        and gate['expected_acquisition_receipt_sha256'] == pins[NEW_ACQUISITION]['sha256']
        and gate['expected_source_manifest_sha256'] == pins[NEW_SOURCE]['sha256'],
        'Actual reviewed new source-QA binding required')
    qa = json.loads(confined(root, gate['path']).read_bytes())
    require(qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
        and qa['status'] == NEW_SOURCE_QA_STATUS and qa['counts'] == NEW_SOURCE_QA_COUNTS
        and qa['acquisition_receipt_sha256'] == pins[NEW_ACQUISITION]['sha256']
        and qa['source_manifest_sha256'] == pins[NEW_SOURCE]['sha256']
        and qa['scope_sha256'] == acquired['scope_sha256']
        and qa['driver_sha256'] == acquired['driver_sha256']
        and qa['public_freeze_commit'] == acquired['public_freeze_commit']
        and qa['qa_script_sha256'] == pins[NEW_SOURCE_QA_CODE]['sha256']
        and qa['compact_input_byte_pins'] == {NEW_ACQUISITION.rsplit('/', 1)[0] + '/' + record['array_file']:
            {'sha256': record['file_sha256'], 'bytes': record['bytes']} for record in acquired['decoded_files']}
        and qa['source_range_raw_record_sha256'] == canonical_sha(acquired['raw_range_records'])
        and qa['decoded_file_row_record_sha256'] == canonical_sha(acquired['decoded_files'])
        and qa['source_range_request_record_sha256'] == canonical_sha(acquired['value_read_requests'])
        and qa['runtime_versions'] == {**VERSIONS, 'HDF5': '1.14.6'}
        and qa['detector_or_score_rerun'] is False
        and qa['new_telescope_HTTP_requests'] == 0 and qa['new_telescope_BODY_bytes'] == 0,
        'Source-QA must directly bind actual acquisition and source manifest')
    sources = {str(chunk): manifest['by_native_chunk'][str(chunk)] for chunk in (170, 172)}
    sources['171'] = json.loads(confined(root, PRIOR_SOURCE).read_bytes())
    records = {str(chunk): [record for record in acquired['decoded_files']
                           if record['native_chunk_index'] == chunk] for chunk in (170, 172)}
    records['171'] = [{**record, 'native_chunk_index': 171} for record in prior['decoded_files']]
    record_contract(records['171'], (171,))
    directories = {'170': NEW_ACQUISITION.rsplit('/', 1)[0], '172': NEW_ACQUISITION.rsplit('/', 1)[0],
                   '171': PRIOR_ACQUISITION.rsplit('/', 1)[0]}
    require(scope['compact_records_by_native_chunk'] == records
        and scope['compact_directories_by_native_chunk'] == directories,
        'Actual frozen compact file/row contexts differ')
    return sources, records, directories


def contract(root, scope):
    pair = scope['pair_id']
    require(pair in PAIRS, 'Unknown fixed joined pair')
    chunks = PAIRS[pair]
    expected = {'schema': 'SETI_S2017_TWO_NEW_JOINED_BOUNDARIES_V1', 'pair_id': pair,
        'source_chunk_ids': list(chunks), 'native_channel_count': COUNT, 'joined_channel_count': JOINED,
        'source_channel0': chunks[0] * COUNT, 'joined_reference_core_q': list(QS),
        'native_reference_cores': [[chunks[0], 255], [chunks[1], 0]],
        'rows_per_scan': 16, 'scan_order': list(SCANS), 'origin_scan_order': list(ONS),
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785},
        'widths_channels': [1, 3], 'valid_hypotheses_per_carrier': 1570,
        'core_channel_count': CORE, 'crop_halo_channels': HALO,
        'expected_ON_maps': 6, 'carriers_per_ON': 8192, 'expected_fixed_profiles': 9,
        'rank_count_per_ON': 20, 'display_suppression_channels': 3,
        'top20_selection_domain': 'both joined boundary reference cores, separately for each ON',
        'fixed_profile_ranks_per_ON': 3,
        'profile_halfwidth_channels': 64, 'profile_shift_channels': 0,
        'joined_profile_normalization': JOINED_NORM, 'CPU_cap_s': CPU_CAP,
        'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
        'memory_cap_bytes_aggregate': AGGREGATE_MEMORY_CAP, 'science_jobs_max': MAX_SCIENCE_JOBS,
        'shared_family_lock': SOURCE_LOCK, 'shared_science_slot_locks': list(SCIENCE_LOCKS),
        'output_stage': STAGE + '/' + pair + '/measurement', 'runtime_package_versions': VERSIONS,
        'hdf5_version': '1.14.6', 'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
        'cost_DKK': 0, 'previous_native171_safe_interiors_rerun': False,
        'retry_resume_or_rerun_authorized': False, 'old_protected_native_chunks_not_read': [156, 159],
        'original_receipts_scopes_or_statuses_modified': False, 'one_historical_visit': True,
        'independent_or_blind_validation': False, 'OFF_veto_applied': False,
        'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
        'expected_counts': {'maps': 6, 'carrier_maximum_records': 24576,
            'correlated_drift_width_combinations': 38584320, 'top20_entries': 60,
            'patches': 9, 'scan_profiles': 54, 'raw_patch_cell_occurrences': 111456,
            'native_compact_files': 12, 'native_decoded_rows': 192}}
    require(all(scope.get(key) == value for key, value in expected.items()), 'Scope differs from fixed joined family')
    require(digest(__file__) == scope['driver_sha256'], 'Driver differs from frozen scope')
    check_pins(root, scope)
    exact_code_paths = {'detector': BASE + '/dependencies/detector.py',
        'gap': BASE + '/dependencies/gap_search.py', 'reader': BASE + '/dependencies/standard_reader.py'}
    require(scope['unchanged_dependency_SHA256s'] == DEPENDENCY_SHAS
        and scope['code_paths'] == exact_code_paths
        and all(digest(confined(root, scope['code_paths'][key])) == sha for key, sha in DEPENDENCY_SHAS.items()),
        'Scientific dependency copies must remain byte-identical')
    sources, records, directories = admission(root, scope)
    left, right = (sources[str(chunk)] for chunk in chunks)
    for chunk in chunks:
        source_contract(sources[str(chunk)], chunk)
    for a, b in zip(left['sources'], right['sources']):
        require(all(a[key] == b[key] for key in ('label', 'role', 'url', 'etag', 'source_file_bytes', 'current_header')),
                'Joined six-scan physical source/header identities differ')
    require(left['physical_channel_interval_half_open'][1] == right['physical_channel_interval_half_open'][0],
            'Joined native source intervals must be contiguous')
    anchor = float(min(item['current_header']['data_attributes']['tstart'] for item in left['sources']))
    previous_end, times = -math.inf, []
    for item in left['sources']:
        start = (item['current_header']['data_attributes']['tstart'] - anchor) * 86400
        require(start >= previous_end, 'Actual scans must remain chronological and nonoverlapping')
        previous_end = start + 16 * TSAMP
        times.extend(start + (row + .5) * TSAMP for row in range(16))
    require(math.ceil(4 * (max(times) - min(times)) / abs(DF)) + 64 < CORE
        and 2 * math.ceil(4 * 15 * TSAMP / abs(DF)) + 1 == 785,
        'Joined fixed six-scan profiles or drift grid lack support')
    old = [171 * COUNT + CORE, 172 * COUNT - CORE]
    require(scope['previously_searched_native171_reference_interval_half_open'] == old
        and all(not max(chunks[0] * COUNT + q * CORE, old[0])
                    < min(chunks[0] * COUNT + (q + 1) * CORE, old[1]) for q in QS),
        'A new boundary core overlaps previously searched native171 reference carriers')
    for name, version in VERSIONS.items():
        require(importlib.metadata.version(name) == version, 'Package differs: ' + name)
    return sources, records, directories, anchor


def run_search(root, scope, sources, records, directories, anchor, out):
    import numpy as np
    reader = load_module('s2017_joined_standard_reader', confined(root, scope['code_paths']['reader']))
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'HDF5 version differs')
    chunks = PAIRS[scope['pair_id']]
    source0 = chunks[0] * COUNT
    arrays = {label: np.empty((16, JOINED), dtype=np.float32) for label in SCANS}
    verified = []
    for side, chunk in enumerate(chunks):
        directory = confined(root, directories[str(chunk)])
        for record in records[str(chunk)]:
            label = record['scan_id']
            path = confined(directory, record['array_file'])
            identity = next(item for item in sources[str(chunk)]['sources'] if item['label'] == label)
            require(path.parent == directory and path.stat().st_size == record['bytes']
                and digest(path) == record['file_sha256'], 'Frozen compact source differs')
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == chunk * COUNT
                    and data.attrs['original_source_url'] == identity['url']
                    and data.attrs['original_source_etag'] == identity['etag'], 'Compact native source frame differs')
                values = data[:, 0, :]
            require(np.isfinite(values).all() and (values >= 0).all(), 'Invalid compact power')
            for row in record['decoded_rows']:
                require(hashlib.sha256(values[row['time_row']].tobytes(order='C')).hexdigest()
                        == row['decoded_sha256'], 'Full-native decoded row SHA differs')
            arrays[label][:, side * COUNT:(side + 1) * COUNT] = values
            del values
            verified.append({'native_chunk_index': chunk, 'scan_id': label,
                'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
    normalization = {'source_channel0': source0, 'source_channel_count': JOINED,
        'source_chunk_ids': list(chunks), 'raw_dtype': '<f4', 'method': JOINED_NORM,
        'row_power_medians': {label: np.median(arrays[label], axis=1).astype(np.float64).tolist() for label in SCANS}}
    require(all(np.isfinite(values).all() and (np.asarray(values) > 0).all()
                for values in normalization['row_power_medians'].values()), 'Invalid joined profile denominator')
    save(out / 'NORMALIZATION.json', normalization)
    detector = load_module('s2017_joined_unchanged_detector', confined(root, scope['code_paths']['detector']))
    cfg = detector.Config(widths=(1, 3))
    drifts, dt = np.linspace(-4.0, 4.0, 785), np.arange(16) * TSAMP
    mismatch = float((drifts[1] - drifts[0]) * dt[-1] / (2 * abs(DF)))
    require(mismatch <= .5 + 1e-12, 'Actual drift half-grid mismatch exceeds half channel')
    tops, receipts = {}, []
    for label in ONS:
        header = next(item['current_header']['data_attributes'] for item in sources[str(chunks[0])]['sources']
                      if item['label'] == label)
        columns = {'channels': [], 'scores': [], 'drifts': [], 'widths': [], 'qs': []}
        for tile, q in enumerate(QS):
            first, crop0, cropstop = source0 + q * CORE, q * CORE - HALO, (q + 1) * CORE + HALO
            channels = np.arange(first, first + CORE)
            scan = detector.Scan(label, 'ON', arrays[label][:, crop0:cropstop], header['tstart'], TSAMP,
                                 FCH1, DF, source0 + crop0, channels)
            result, _ = detector.search_scan(scan, FCH1 + DF * channels, dt, drifts, cfg)
            scores = result['maximum_robust_box_track_score']
            require(np.isfinite(scores).all() and np.all(result['valid_hypothesis_count'] == 1570),
                    'Incomplete fixed joined core map')
            numeric = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
            numeric.update(source_reference_channels=channels, drift_grid_hz_s=drifts)
            path = out / (label + '_tile_%02d_all_carriers.npz' % tile)
            np.savez(path, **numeric)
            norm_path = out / (label + '_tile_%02d_normalization.json' % tile)
            save(norm_path, result['normalization'])
            receipts.append({'scan_id': label, 'tile_index': tile, 'reference_core_q': q,
                'reference_channel_interval_half_open': [first, first + CORE],
                'path': path.name, 'sha256': digest(path), 'bytes': path.stat().st_size,
                'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 1570,
                'normalization_path': norm_path.name, 'normalization_sha256': digest(norm_path),
                'normalization_bytes': norm_path.stat().st_size})
            for key, value in (('channels', channels), ('scores', scores), ('drifts', result['winning_drift_hz_s']),
                ('widths', result['winning_width_channels']), ('qs', np.full(CORE, q, dtype=np.int16))):
                columns[key].append(value)
            save(out / 'DRIFT_CHECKPOINT.json', {'pair_id': scope['pair_id'], 'fixed_pair_q': list(QS),
                'completed_ON_maps': len(receipts), 'expected_ON_maps': 6, 'complete': len(receipts) == 6,
                'receipts': receipts})
            print('SEARCHED_NEW_S2017_JOINED_BOUNDARY_CORE', scope['pair_id'], label, q, flush=True)
        columns = {key: np.concatenate(value) for key, value in columns.items()}
        chosen = []
        for index in np.lexsort((columns['channels'], -columns['scores'])):
            index = int(index)
            if all(abs(int(columns['channels'][index]) - int(columns['channels'][other])) > 3 for other in chosen):
                chosen.append(index)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Incomplete joined top20 family')
        reference = (header['tstart'] - anchor) * 86400 + .5 * TSAMP
        tops[label] = [{'track_id': label + '_visit20170428_Sband_' + scope['pair_id'] + '_rank_%02d' % rank,
            'family': 'S2017_joined_boundary', 'pair_id': scope['pair_id'],
            'originating_scan': label, 'originating_role': 'ON', 'display_rank': rank,
            'source_reference_channel': int(columns['channels'][index]),
            'reference_frequency_hz': float(FCH1 + DF * columns['channels'][index]),
            'reference_seconds_from_anchor': float(reference), 'drift_hz_s': float(columns['drifts'][index]),
            'width_channels': int(columns['widths'][index]),
            'maximum_robust_box_track_score': float(columns['scores'][index]),
            'reference_core_tile': QS.index(int(columns['qs'][index])),
            'reference_core_q': int(columns['qs'][index]),
            'source_native_chunk_index': chunks[0] if int(columns['qs'][index]) == 255 else chunks[1],
            'source_native_core_q': 255 if int(columns['qs'][index]) == 255 else 0,
            'status': 'EXPLORATORY_RANK_UNCLASSIFIED'} for rank, index in enumerate(chosen, 1)]
        save(out / 'DRIFT_TOP20.json', tops)
        del columns
    gap = load_module('s2017_joined_unchanged_profiles', confined(root, scope['code_paths']['gap']))
    gap.ROOT, gap.np = root, np
    gap.FCH1, gap.DF, gap.TSAMP, gap.C0, gap.COUNT = FCH1, DF, TSAMP, source0, JOINED
    gap.NORMALIZATION_PATH = (out / 'NORMALIZATION.json').relative_to(root).as_posix()
    profiles = gap.fixed_profiles(arrays, sources[str(chunks[0])], normalization, tops, anchor, out)
    require(profiles['profile_count'] == 9 and len(receipts) == 6, 'Incomplete joined output family')
    profiles.update(row_normalization_context=JOINED_NORM,
        time_profile_units='width-mean raw power/joined-pair row median minus fixed flank median',
        mean_profile_units='mean track-aligned joined-row-normalized power minus each row fixed flank median')
    for chunk in chunks:
        for record in records[str(chunk)]:
            path = confined(confined(root, directories[str(chunk)]), record['array_file'])
            require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'],
                    'Native compact source changed during joined search')
    return {'verified_source_inputs': verified, 'compact_files_verified': 12, 'decoded_rows_verified': 192,
        'MJD_anchor': anchor, 'saved_normalization_sha256': digest(out / 'NORMALIZATION.json'),
        'search_summary': {'completed_ON_maps': len(receipts), 'cores_per_ON': 2, 'carriers_per_ON': 8192,
            'ON_carrier_maximum_records': 24576, 'correlated_drift_width_combinations': 38584320,
            'searched_joined_q': list(QS), 'reference_core_intervals_half_open':
                [[source0 + q * CORE, source0 + (q + 1) * CORE] for q in QS],
            'drift_grid_count': 785, 'widths_channels': [1, 3], 'half_grid_mismatch_channels': mismatch,
            'bandwidth_per_ON_hz': 8192 * abs(DF), 'joined_channel_fraction_searched': 8192 / JOINED,
            'score_definition': 'unchanged row-MAD standardized odd-box track sum/sqrt(Nrow*width)',
            'normalization': 'unchanged4096-carrier core with501-channel filter; separate per map',
            'reference_time': 'each ON first integration midpoint; actual headers for all fixed scan profiles'},
        'fixed_profile_summary': profiles, 'top20_entries': 60, 'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version}}


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def partial_counts(out):
    counts = {'completed_ON_maps': 0, 'completed_profiles': 0}
    if (out / 'DRIFT_CHECKPOINT.json').is_file():
        counts['completed_ON_maps'] = json.loads((out / 'DRIFT_CHECKPOINT.json').read_bytes())['completed_ON_maps']
    if (out / 'FIXED_TOP3_PROFILES.json').is_file():
        counts['completed_profiles'] = len(json.loads((out / 'FIXED_TOP3_PROFILES.json').read_bytes()))
    return counts


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual public prospective freeze commit required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_scope_sha256)
        and digest(args.scope) == args.expected_scope_sha256, 'Frozen scope SHA differs')
    scope = json.loads(Path(args.scope).read_bytes())
    require(Path(args.scope).resolve() == root / BASE / 'scopes' / (scope['pair_id'] + '.json'),
            'Exact frozen joined-pair scope path required')
    sources, records, directories, anchor = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_CODE_ACTUAL_ACQUISITION_QA_NO_VALUES_NO_HTTP',
            'pair_id': scope['pair_id'], 'scope_sha256': args.expected_scope_sha256,
            'expected_ON_maps': 6, 'expected_fixed_profiles': 9}))
        return
    require(args.root_go_after_review, 'Root prospective review, exact public readback and GO required')
    handles, slot_index, created = [], None, False
    out = confined(root, scope['output_stage'])
    def deadline(signum, frame):
        raise TimeoutError('Frozen joined boundary CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        pair_lock = confined(root, BASE + '/' + scope['pair_id'] + '_ACTIVE_FLOCK.lock').open('a+b')
        handles.append(pair_lock)
        fcntl.flock(pair_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_lock = confined(root, scope['shared_family_lock']).open('a+b')
        handles.append(source_lock)
        fcntl.flock(source_lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        for index, name in enumerate(SCIENCE_LOCKS):
            candidate = confined(root, name).open('a+b')
            try:
                fcntl.flock(candidate.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                candidate.close()
                continue
            handles.append(candidate)
            slot_index = index
            break
        require(slot_index is not None, 'Both common2GiB science slots already occupied')
        out.mkdir(parents=True, exist_ok=False)
        created = True
        save(out / 'INPUT_PINS.json', {'schema': scope['schema'], 'pair_id': scope['pair_id'],
            'scope_sha256': args.expected_scope_sha256, 'driver_sha256': digest(__file__),
            'public_freeze_commit': args.freeze_commit,
            'pinned_metadata_code_and_prerequisites': scope['pinned_metadata_code_and_prerequisites'],
            'compact_records_by_native_chunk': scope['compact_records_by_native_chunk'],
            'compact_directories_by_native_chunk': directories, 'science_slot_index': slot_index})
        # Recheck the complete metadata admission while holding source-family
        # ownership, before the first scientific package or compact value read.
        sources, records, directories, anchor = contract(root, scope)
        result = run_search(root, scope, sources, records, directories, anchor, out)
        check_pins(root, scope)
        require(digest(args.scope) == args.expected_scope_sha256
            and digest(__file__) == scope['driver_sha256'], 'Frozen scope/driver changed during execution')
        use = measured(started)
        require(use['process_CPU_seconds_including_imports'] <= CPU_CAP
            and use['wall_seconds_including_imports'] <= WALL_CAP and use['peak_RSS_bytes'] <= MEMORY_CAP,
            'Measured execution exceeded frozen joined bounds')
        receipt = {'status': 'COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY',
            'pair_id': scope['pair_id'], 'source_chunk_ids': scope['source_chunk_ids'],
            'source_channel0': scope['source_channel0'], 'source_channel_count': JOINED,
            'fixed_pair_q': list(QS), 'scope_sha256': args.expected_scope_sha256,
            'driver_sha256': digest(__file__), 'public_freeze_commit': args.freeze_commit,
            'new_acquisition_receipt_sha256': scope['pinned_metadata_code_and_prerequisites'][NEW_ACQUISITION]['sha256'],
            'new_source_QA_receipt_sha256': scope['pinned_metadata_code_and_prerequisites'][scope['new_source_QA']['path']]['sha256'],
            'prior171_source_QA_receipt_sha256': PRIOR_FIXED_PINS[PRIOR_SOURCE_QA],
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
            'science_slot_index': slot_index, 'science_jobs_max': MAX_SCIENCE_JOBS,
            'memory_cap_bytes_aggregate': AGGREGATE_MEMORY_CAP,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
            'cost_DKK': 0, 'one_historical_visit': True, 'independent_or_blind_validation': False,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'limitations': scope['limitations'], **result, **use}
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        print(json.dumps({key: receipt[key] for key in ('status', 'pair_id', *use)}), flush=True)
    except BaseException as exc:
        # Never overwrite an existing namespace or a prior terminal receipt.
        if created and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_S2017_JOINED_BOUNDARY_PRESERVE_OUTPUTS_NO_RETRY',
                'pair_id': scope['pair_id'], 'error_type': type(exc).__name__, 'error': str(exc),
                'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
                **partial_counts(out), **measured(started)})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
