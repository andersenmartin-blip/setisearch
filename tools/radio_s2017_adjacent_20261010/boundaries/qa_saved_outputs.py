"""Independent saved-output and native-source QA for two S2017 boundary jobs.

No detector import, search, score recomputation, fit, track optimization or HTTP.
After actual COMPLETE jobs and root GO, saved maxima reconstruct exact top20,
all fixed patches/arithmetic are checked,18 distinct compact sources are read
once,288 unique decoded rows are authenticated,192 full joined float32 row
median occurrences and192 ON core float64 medians are recomputed, and222912
saved raw-patch occurrences are compared bitwise with physical native cells.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
PAIRS = {'pair170_171': (170, 171), 'pair171_172': (171, 172)}
NATIVE, JOINED, CORE, HALO = 1048576, 2097152, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, RAM_CAP = 120, 1800, 2 * 1024**3
BASE = 'analysis/s2017_next_native/boundaries'
STAGE = BASE + '/results'
NEW_SOURCE = 'analysis/s2017_next_native/source_manifest_v2.json'
NEW_ACQ = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
NEW_SOURCE_QA = 'analysis/s2017_next_native/results/source_review/QA_RECEIPT.json'
NEW_SOURCE_QA_CODE = 'analysis/s2017_next_native/qa_sources.py'
PRIOR_SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
PRIOR_ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
PRIOR_QA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
PRIOR_FULL_QA = 'analysis/s2017_full_band/results/review/QA_RECEIPT.json'
PRIOR_SHAS = {
    PRIOR_SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    PRIOR_ACQ: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    PRIOR_QA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f',
    PRIOR_FULL_QA: 'e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f'}
DEP_SHAS = {'detector': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'gap': 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58',
    'reader': '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
FULLNORM = 'median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)'
SEARCH_STATUS = 'COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'
SOURCE_STATUS = 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
SOURCE_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12, 'source_descriptors': 192,
    'exact_range_records': 192, 'unique_source_ranges': 192, 'durable_raw_sidecars': 192,
    'compressed_source_chunks': 192, 'decoded_rows': 192}
EXPECTED_COUNTS = {'pair_families': 2, 'maps': 12, 'map_normalization_records': 12,
    'carrier_maximum_records': 49152, 'valid_hypothesis_records': 77168640,
    'top20_entries': 120, 'patches': 18, 'scan_profiles': 108, 'time_row_occurrences': 1728,
    'retained_raw_patch_cells': 222912, 'distinct_compact_files': 18, 'distinct_decoded_rows': 288,
    'search_compact_file_occurrences': 24, 'search_decoded_row_occurrences': 384,
    'joined_full_float32_row_median_occurrences_recomputed': 192,
    'ON_core_float64_row_medians_recomputed': 192, 'raw_cells_bitwise_checked': 222912}
QA_SCHEMA = 'SETI_S2017_TWO_JOINED_BOUNDARIES_SAVED_OUTPUT_AND_FULL_SOURCE_QA_V1'
QA_STATUS = 'PASS12_S2017_JOINED_MAPS18_FIXED_PROFILES192_JOINED_MEDIANS_AND222912_BITWISE_SOURCE_CELLS'


def check(condition, message):
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


def unique_fields(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field: ' + key)
        result[key] = value
    return result


def confined(root, name):
    relative = Path(name)
    check(not relative.is_absolute() and '..' not in relative.parts, 'Confined relative path required')
    path = root / relative
    check(path.resolve().is_relative_to(root), 'Path escapes frozen root: ' + str(name))
    return path


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target)


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def same(actual, expected, message):
    check(actual.shape == expected.shape and np.array_equal(actual, expected), message)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    for name in ('expected-qa-sha256', 'qa-freeze-commit', 'expected-driver-sha256', 'search-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    for pair in PAIRS:
        parser.add_argument('--' + pair + '-scope-sha256', required=True)
        parser.add_argument('--' + pair + '-receipt-sha256', required=True)
    parser.add_argument('--root-go-after-numerics', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    own_path, own_sha = Path(__file__).resolve(), digest(__file__)
    check(args.root_go_after_numerics and own_sha == args.expected_qa_sha256
        and re.fullmatch('[0-9a-f]{64}', args.expected_driver_sha256)
        and re.fullmatch('[0-9a-f]{40}', args.qa_freeze_commit)
        and re.fullmatch('[0-9a-f]{40}', args.search_freeze_commit),
        'Exact QA/code freezes and actual root GO required')
    expected_scope_shas = {pair: getattr(args, pair + '_scope_sha256') for pair in PAIRS}
    expected_receipt_shas = {pair: getattr(args, pair + '_receipt_sha256') for pair in PAIRS}
    check(all(re.fullmatch('[0-9a-f]{64}', value) for value in (*expected_scope_shas.values(), *expected_receipt_shas.values())),
          'Exact public scope and root-admitted actual COMPLETE receipt SHAs required')
    counts = {name: 0 for name in EXPECTED_COUNTS}
    cache, pins, scopes, results, pair_data, input_compacts, buffers = {}, {}, {}, {}, {}, {}, []
    review = root / STAGE / 'review'
    lock, created = None, False
    def deadline(signum, frame):
        raise TimeoutError('Frozen joined saved-output QA CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))

    def read_bytes(path, declared=None):
        path = Path(path)
        key = path.relative_to(root).as_posix()
        if key not in cache:
            raw = path.read_bytes()
            cache[key] = raw
            pins[key] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if declared is not None:
            check(pins[key] == declared, 'Saved byte pin differs: ' + key)
        return cache[key]

    def read_json(path, declared=None):
        return json.loads(read_bytes(path, declared), object_pairs_hook=unique_fields)

    def npz(out, record):
        raw = read_bytes(confined(out, record['path']), {'sha256': record['sha256'], 'bytes': record['bytes']})
        with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
            check(len(archive.files) == len(set(archive.files)), 'Duplicate NPZ archive field')
            return {name: archive[name] for name in archive.files}

    try:
        # QA owns source-family EX. Science jobs retain SH until every output
        # and source readback finishes, so partial jobs cannot be audited here.
        lock = (root / 'analysis/s2017_next_native/ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        review.mkdir(parents=True, exist_ok=False)
        created = True
        for pair, chunks in PAIRS.items():
            scope_path = root / BASE / 'scopes' / (pair + '.json')
            scope = read_json(scope_path)
            check(pins[scope_path.relative_to(root).as_posix()]['sha256'] == expected_scope_shas[pair],
                  'Public pair scope differs')
            check(scope['schema'] == 'SETI_S2017_TWO_NEW_JOINED_BOUNDARIES_V1'
                and scope['pair_id'] == pair and scope['source_chunk_ids'] == list(chunks)
                and scope['driver_sha256'] == args.expected_driver_sha256
                and scope['joined_reference_core_q'] == [255, 256]
                and scope['native_reference_cores'] == [[chunks[0], 255], [chunks[1], 0]]
                and scope['native_channel_count'] == NATIVE and scope['joined_channel_count'] == JOINED
                and scope['source_channel0'] == chunks[0] * NATIVE
                and scope['scan_order'] == list(SCANS) and scope['rows_per_scan'] == 16
                and scope['fch1_hz'] == FCH1 and scope['df_hz'] == DF and scope['tsamp_s'] == TSAMP
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
                and scope['widths_channels'] == [1, 3] and scope['valid_hypotheses_per_carrier'] == 1570
                and scope['core_channel_count'] == CORE and scope['crop_halo_channels'] == HALO
                and scope['joined_profile_normalization'] == FULLNORM
                and scope['profile_shift_channels'] == 0 and scope['profile_halfwidth_channels'] == 64
                and scope['runtime_package_versions'] == VERSIONS and scope['hdf5_version'] == '1.14.6'
                and scope['output_stage'] == STAGE + '/' + pair + '/measurement', 'Frozen joined geometry differs')
            for name, pin in scope['pinned_metadata_code_and_prerequisites'].items():
                check(Path(name).suffix.lower() not in ('.h5', '.hdf5', '.npz', '.npy'), 'Prevalue metadata pins cannot decode power')
                read_bytes(confined(root, name), pin)
            check(scope['unchanged_dependency_SHA256s'] == DEP_SHAS
                and all(scope['pinned_metadata_code_and_prerequisites'][scope['code_paths'][key]]['sha256'] == sha
                        for key, sha in DEP_SHAS.items()), 'Original scientific dependency byte pins differ')
            for name, sha in PRIOR_SHAS.items():
                check(scope['pinned_metadata_code_and_prerequisites'][name]['sha256'] == sha,
                      'Original native171 source QA identity changed')
            out = confined(root, scope['output_stage'])
            result_path = out / 'EXECUTION_RECEIPT.json'
            result = read_json(result_path)
            check(pins[result_path.relative_to(root).as_posix()]['sha256'] == expected_receipt_shas[pair],
                  'Root-admitted actual COMPLETE receipt differs')
            check(result['status'] == SEARCH_STATUS and result['pair_id'] == pair
                and result['source_chunk_ids'] == list(chunks) and result['source_channel0'] == chunks[0] * NATIVE
                and result['source_channel_count'] == JOINED and result['fixed_pair_q'] == [255, 256]
                and result['scope_sha256'] == expected_scope_shas[pair]
                and result['driver_sha256'] == args.expected_driver_sha256
                and result['public_freeze_commit'] == args.search_freeze_commit
                and result['compact_files_verified'] == 12 and result['decoded_rows_verified'] == 192
                and result['runtime_versions'] == {**VERSIONS, 'HDF5': '1.14.6'}
                and result['top20_entries'] == 60,
                'Actual complete joined execution contract differs')
            for field, cap in (('process_CPU_seconds_including_imports', 180), ('wall_seconds_including_imports', 1800),
                               ('peak_RSS_bytes', 2 * 1024**3)):
                check(0 < result[field] <= cap, 'Actual search resource bound differs: ' + field)
            for field, value in (('CPU_cap_s', 180), ('wall_cap_s', 1800), ('memory_cap_bytes', 2 * 1024**3),
                ('memory_cap_bytes_aggregate', 4 * 1024**3), ('science_jobs_max', 2),
                ('new_telescope_HTTP_requests', 0), ('new_telescope_BODY_bytes', 0), ('cost_DKK', 0),
                ('one_historical_visit', True), ('independent_or_blind_validation', False),
                ('qualified_SETI_detection', False), ('calibrated_SNR_FAP', False),
                ('original_A_B_status', 'FAIL_CLOSED_UNCHANGED')):
                check(result[field] == value, 'Descriptive result contract differs: ' + field)
            check(result['science_slot_index'] in (0, 1), 'Unknown common science slot')
            inputs = read_json(out / 'INPUT_PINS.json')
            check(inputs['scope_sha256'] == expected_scope_shas[pair]
                and inputs['driver_sha256'] == args.expected_driver_sha256
                and inputs['public_freeze_commit'] == args.search_freeze_commit and inputs['pair_id'] == pair
                and inputs['science_slot_index'] == result['science_slot_index']
                and inputs['pinned_metadata_code_and_prerequisites'] == scope['pinned_metadata_code_and_prerequisites']
                and inputs['compact_records_by_native_chunk'] == scope['compact_records_by_native_chunk']
                and inputs['compact_directories_by_native_chunk'] == scope['compact_directories_by_native_chunk'],
                'Actual numerical input provenance differs')
            scopes[pair], results[pair] = scope, result
        read_bytes(root / BASE / 'driver.py')
        check(pins[BASE + '/driver.py']['sha256'] == args.expected_driver_sha256, 'Actual searched driver code changed')
        for package, version in VERSIONS.items():
            check(importlib.metadata.version(package) == version, 'Runtime differs: ' + package)
        new_source = read_json(root / NEW_SOURCE)
        old_source = read_json(root / PRIOR_SOURCE)
        new_acq, old_acq = read_json(root / NEW_ACQ), read_json(root / PRIOR_ACQ)
        source_qa, old_qa = read_json(root / NEW_SOURCE_QA), read_json(root / PRIOR_QA)
        full_qa = read_json(root / PRIOR_FULL_QA)
        check(new_source['schema'] == 'SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1'
            and set(new_source['by_native_chunk']) == {'170', '172'}, 'Only admitted adjacent source bands allowed')
        check(new_acq['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
            and new_acq['source_manifest_sha256'] == pins[NEW_SOURCE]['sha256']
            and new_acq['new_telescope_HTTP_requests'] == 192 and new_acq['new_telescope_BODY_bytes'] == 597792529
            and new_acq['reserved_BODY_upper_bound_bytes'] == 597792721
            and new_acq['source_range_count_authenticated'] == 192
            and new_acq['complete_compact_files'] == 12 and new_acq['decoded_row_SHA256s'] == 192
            and [(r['native_chunk_index'], r['scan_id']) for r in new_acq['decoded_files']]
                == [(chunk, scan) for chunk in (170, 172) for scan in SCANS], 'Actual complete192-row adjacent acquisition required')
        check(source_qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
            and source_qa['status'] == SOURCE_STATUS and source_qa['counts'] == SOURCE_COUNTS
            and source_qa['acquisition_receipt_sha256'] == pins[NEW_ACQ]['sha256']
            and source_qa['source_manifest_sha256'] == pins[NEW_SOURCE]['sha256']
            and source_qa['scope_sha256'] == new_acq['scope_sha256']
            and source_qa['driver_sha256'] == new_acq['driver_sha256']
            and source_qa['public_freeze_commit'] == new_acq['public_freeze_commit']
            and source_qa['qa_script_sha256'] == pins[NEW_SOURCE_QA_CODE]['sha256']
            and source_qa['compact_input_byte_pins'] == {NEW_ACQ.rsplit('/', 1)[0] + '/' + record['array_file']:
                {'sha256': record['file_sha256'], 'bytes': record['bytes']} for record in new_acq['decoded_files']}
            and source_qa['source_range_raw_record_sha256'] == canonical_sha(new_acq['raw_range_records'])
            and source_qa['decoded_file_row_record_sha256'] == canonical_sha(new_acq['decoded_files'])
            and source_qa['source_range_request_record_sha256'] == canonical_sha(new_acq['value_read_requests'])
            and source_qa['runtime_versions'] == {**VERSIONS, 'HDF5': '1.14.6'}
            and source_qa['detector_or_score_rerun'] is False
            and source_qa['new_telescope_HTTP_requests'] == 0 and source_qa['new_telescope_BODY_bytes'] == 0,
            'Actual adjacent-source QA PASS required')
        check(old_acq['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
            and old_acq['source_manifest_sha256'] == PRIOR_SHAS[PRIOR_SOURCE]
            and old_acq['complete_compact_files'] == 6 and old_acq['decoded_row_SHA256s'] == 96
            and old_qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
            and old_qa['acquisition_receipt_sha256'] == PRIOR_SHAS[PRIOR_ACQ]
            and old_qa['counts']['decoded_rows'] == 96 and old_qa['counts']['compact_files'] == 6
            and full_qa['status'] == 'PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS',
            'Actual original171 acquisition/full-row source QA and saved extension QA required')
        sources = {**new_source['by_native_chunk'], '171': old_source}
        records = {str(chunk): [record for record in new_acq['decoded_files']
                               if record['native_chunk_index'] == chunk] for chunk in (170, 172)}
        records['171'] = [{**record, 'native_chunk_index': 171} for record in old_acq['decoded_files']]
        directories = {'170': NEW_ACQ.rsplit('/', 1)[0], '172': NEW_ACQ.rsplit('/', 1)[0], '171': PRIOR_ACQ.rsplit('/', 1)[0]}
        for chunk in (170, 171, 172):
            source = sources[str(chunk)]
            check(source['native_chunk_index'] == chunk
                and source['physical_channel_interval_half_open'] == [chunk * NATIVE, (chunk + 1) * NATIVE]
                and [item['label'] for item in source['sources']] == list(SCANS)
                and [item['role'].upper() for item in source['sources']] == ['ON', 'OFF'] * 3,
                'Actual native source/scan metadata differs')
            check([record['scan_id'] for record in records[str(chunk)]] == list(SCANS), 'Six source compact records required')
            for record, item in zip(records[str(chunk)], source['sources']):
                header = item['current_header']
                check(header['dataset_shape'] == [16, 1, 359661568] and header['dataset_chunks'] == [1, 1, NATIVE]
                    and header['dtype_exact'] == '<f4' and record['shape'] == [16, 1, NATIVE]
                    and record['source_channel0'] == chunk * NATIVE
                    and [row['time_row'] for row in record['decoded_rows']] == list(range(16)), 'Full native metadata shape differs')
                input_compacts[(chunk, record['scan_id'])] = (record, item, directories[str(chunk)])
        for pair, chunks in PAIRS.items():
            scope, result = scopes[pair], results[pair]
            check(scope['compact_records_by_native_chunk'] == records
                and scope['compact_directories_by_native_chunk'] == directories
                and result['new_acquisition_receipt_sha256'] == pins[NEW_ACQ]['sha256']
                and result['new_source_QA_receipt_sha256'] == pins[NEW_SOURCE_QA]['sha256']
                and result['prior171_source_QA_receipt_sha256'] == PRIOR_SHAS[PRIOR_QA], 'Search/source-QA provenance differs')
            expected_proof = [{'native_chunk_index': chunk, 'scan_id': record['scan_id'],
                'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16}
                for chunk in chunks for record in records[str(chunk)]]
            check(result['verified_source_inputs'] == expected_proof, 'Exactly all192 search decoded-row occurrences required')
            for a, b in zip(sources[str(chunks[0])]['sources'], sources[str(chunks[1])]['sources']):
                check(all(a[key] == b[key] for key in ('label', 'role', 'url', 'etag', 'source_file_bytes', 'current_header')),
                      'Pair original physical source/header identities differ')
            counts['search_compact_file_occurrences'] += 12
            counts['search_decoded_row_occurrences'] += 192
        global np
        import numpy as np
        drift_grid = np.linspace(-4.0, 4.0, 785)
        offsets = np.arange(-64, 65)
        map_schema = {'frequency_hz_at_tref': '<f8', 'maximum_robust_box_track_score': '<f8',
            'winning_drift_hz_s': '<f8', 'winning_width_channels': '<i2', 'valid_hypothesis_count': '<i8',
            'source_reference_channels': '<i8', 'drift_grid_hz_s': '<f8'}
        for pair, chunks in PAIRS.items():
            left, right = chunks
            c0, out = left * NATIVE, root / STAGE / pair / 'measurement'
            result, scope = results[pair], scopes[pair]
            expected_names = {'EXECUTION_RECEIPT.json', 'INPUT_PINS.json', 'DRIFT_CHECKPOINT.json',
                'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json', 'NORMALIZATION.json'}
            expected_names.update(f'{scan}_tile_{tile:02d}_{suffix}' for scan in ONS for tile in (0, 1)
                                  for suffix in ('all_carriers.npz', 'normalization.json'))
            expected_names.update(f'profiles/{scan}_visit20170428_Sband_{pair}_rank_{rank:02d}.npz'
                                  for scan in ONS for rank in (1, 2, 3))
            check({path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()} == expected_names,
                  'Exactly27 complete saved files required: ' + pair)
            headers = {item['label']: item['current_header']['data_attributes'] for item in sources[str(left)]['sources']}
            anchor = min(header['tstart'] for header in headers.values())
            previous_end = -math.inf
            for scan in SCANS:
                header = headers[scan]
                check(header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP,
                      'Actual source physical frame differs')
                start = (header['tstart'] - anchor) * 86400
                check(start >= previous_end, 'Actual scan time order overlaps')
                previous_end = start + 16 * TSAMP
            check(result['MJD_anchor'] == anchor, 'Actual source MJD anchor differs')
            summary = result['search_summary']
            for key, value in (('completed_ON_maps', 6), ('cores_per_ON', 2), ('carriers_per_ON', 8192),
                ('ON_carrier_maximum_records', 24576), ('correlated_drift_width_combinations', 38584320),
                ('searched_joined_q', [255, 256]), ('drift_grid_count', 785), ('widths_channels', [1, 3]),
                ('reference_core_intervals_half_open', [[c0 + q * CORE, c0 + (q + 1) * CORE] for q in (255, 256)])):
                check(summary[key] == value, 'Saved search geometry differs: ' + key)
            own_times = np.arange(16) * TSAMP
            mismatch = float((drift_grid[1] - drift_grid[0]) * own_times[-1] / (2 * abs(DF)))
            check(summary['half_grid_mismatch_channels'] == mismatch and mismatch <= .5 + 1e-12,
                  'Actual785-grid half-channel mismatch differs')
            old = [171 * NATIVE + CORE, 172 * NATIVE - CORE]
            check(scope['previously_searched_native171_reference_interval_half_open'] == old
                and all(max(c0 + q * CORE, old[0]) >= min(c0 + (q + 1) * CORE, old[1]) for q in (255, 256)),
                'New carrier cores overlap searched171 interiors')
            checkpoint = read_json(out / 'DRIFT_CHECKPOINT.json')
            check(checkpoint['pair_id'] == pair and checkpoint['fixed_pair_q'] == [255, 256]
                and checkpoint['complete'] is True and checkpoint['completed_ON_maps'] == 6
                and checkpoint['expected_ON_maps'] == 6, 'Complete six-map checkpoint required')
            entries = checkpoint['receipts']
            check([(record['scan_id'], record['tile_index'], record['reference_core_q']) for record in entries]
                == [(scan, tile, q) for scan in ONS for tile, q in enumerate((255, 256))], 'Exact checkpoint order differs')
            saved, core_norms = {scan: [] for scan in ONS}, {}
            for record in entries:
                scan, q = record['scan_id'], record['reference_core_q']
                channels = np.arange(c0 + q * CORE, c0 + (q + 1) * CORE)
                check(record['reference_channel_interval_half_open'] == [int(channels[0]), int(channels[-1]) + 1]
                    and record['searched_carriers'] == CORE and record['valid_hypotheses_per_carrier'] == 1570,
                    'Map declaration interval/count differs')
                norm = read_json(confined(out, record['normalization_path']),
                    {'sha256': record['normalization_sha256'], 'bytes': record['normalization_bytes']})
                check(set(norm) == {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                    'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'},
                    'Saved map normalization schema differs')
                same(np.asarray(norm['normalization_source_channels']), channels, 'Map normalization carrier core differs')
                same(np.asarray(norm['normalization_unmasked_counts']), np.full(16, CORE), 'All16 core masks differ')
                for field in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                    values = np.asarray(norm[field])
                    check(values.shape == (16,) and np.isfinite(values).all(), 'Normalization row geometry differs')
                    if field in ('row_power_median', 'row_residual_MAD_scale'):
                        check((values > 0).all(), 'Positive normalization median/scale required')
                core_norms[(scan, q)] = np.asarray(norm['row_power_median'])
                values = npz(out, record)
                check(set(values) == set(map_schema), 'Saved map array schema differs')
                for field, dtype in map_schema.items():
                    check(values[field].dtype == np.dtype(dtype), 'Map precision differs: ' + field)
                same(values['source_reference_channels'], channels, 'Physical carrier channels differ')
                same(values['frequency_hz_at_tref'], FCH1 + DF * channels, 'Negative-df source frequency map differs')
                same(values['drift_grid_hz_s'], drift_grid, 'Exact785 drift grid differs')
                same(values['valid_hypothesis_count'], np.full(CORE, 1570), 'All two-width hypotheses must be present')
                for field in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_width_channels'):
                    check(values[field].shape == (CORE,) and np.isfinite(values[field]).all(), 'Saved maximum geometry differs')
                check(np.isin(values['winning_drift_hz_s'], drift_grid).all()
                    and np.isin(values['winning_width_channels'], (1, 3)).all(), 'Winner lies outside frozen hypotheses')
                saved[scan].append(values)
                counts['maps'] += 1
                counts['map_normalization_records'] += 1
                counts['carrier_maximum_records'] += CORE
                counts['valid_hypothesis_records'] += CORE * 1570
            tops = read_json(out / 'DRIFT_TOP20.json')
            check(set(tops) == set(ONS), 'Top20 origin scans differ')
            for scan in ONS:
                channels = np.concatenate([values['source_reference_channels'] for values in saved[scan]])
                scores = np.concatenate([values['maximum_robust_box_track_score'] for values in saved[scan]])
                drifts = np.concatenate([values['winning_drift_hz_s'] for values in saved[scan]])
                widths = np.concatenate([values['winning_width_channels'] for values in saved[scan]])
                chosen = []
                for index in np.lexsort((channels, -scores)):
                    index = int(index)
                    if all(abs(int(channels[index]) - int(channels[other])) > 3 for other in chosen):
                        chosen.append(index)
                    if len(chosen) == 20:
                        break
                expected = []
                for rank, index in enumerate(chosen, 1):
                    q = 255 + index // CORE
                    expected.append({'track_id': f'{scan}_visit20170428_Sband_{pair}_rank_{rank:02d}',
                        'family': 'S2017_joined_boundary', 'pair_id': pair, 'originating_scan': scan,
                        'originating_role': 'ON', 'display_rank': rank,
                        'source_reference_channel': int(channels[index]),
                        'reference_frequency_hz': float(FCH1 + DF * int(channels[index])),
                        'reference_seconds_from_anchor': float((headers[scan]['tstart'] - anchor) * 86400 + .5 * TSAMP),
                        'drift_hz_s': float(drifts[index]), 'width_channels': int(widths[index]),
                        'maximum_robust_box_track_score': float(scores[index]), 'reference_core_tile': index // CORE,
                        'reference_core_q': q, 'source_native_chunk_index': left if q == 255 else right,
                        'source_native_core_q': 255 if q == 255 else 0, 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'})
                check(len(expected) == 20 and tops[scan] == expected, 'Exact top20 rank/ties/suppression/coordinates differ')
                counts['top20_entries'] += 20
            fullnorm = read_json(out / 'NORMALIZATION.json')
            norm_sha = pins[(out / 'NORMALIZATION.json').relative_to(root).as_posix()]['sha256']
            top_sha = pins[(out / 'DRIFT_TOP20.json').relative_to(root).as_posix()]['sha256']
            profile_summary = result['fixed_profile_summary']
            check(profile_summary['profile_count'] == 9 and profile_summary['all_rows_retained'] == 16
                and profile_summary['plot_count'] == 0
                and profile_summary['shift_frequency_drift_width_optimization_applied'] is False
                and profile_summary['source_top20_sha256'] == top_sha
                and profile_summary['saved_normalization_sha256'] == norm_sha
                and result['saved_normalization_sha256'] == norm_sha
                and fullnorm['method'] == FULLNORM and fullnorm['raw_dtype'] == '<f4'
                and fullnorm['source_channel0'] == c0 and fullnorm['source_channel_count'] == JOINED
                and fullnorm['source_chunk_ids'] == list(chunks), 'Joined normalization/profile selection binding differs')
            rowmedians = np.asarray([fullnorm['row_power_medians'][scan] for scan in SCANS])
            check(rowmedians.shape == (6, 16) and np.isfinite(rowmedians).all() and (rowmedians > 0).all(),
                  'All192 joined median declarations must be finite and positive')
            records_saved = read_json(out / 'FIXED_TOP3_PROFILES.json')
            check(len(records_saved) == 9
                and [record['selected_track'] for record in records_saved] == [track for scan in ONS for track in tops[scan][:3]],
                'Exact fixed top3 identities differ')
            for record in records_saved:
                track = record['selected_track']
                values = npz(out, record['patch'])
                schema = {'raw_power': ('<f4', (6, 16, 129)), 'row_normalized_power': ('<f8', (6, 16, 129)),
                    'saved_full_chunk_row_medians': ('<f8', (6, 16)), 'frozen_source_channel_centers': ('<i8', (6, 16)),
                    'source_channel_offsets': ('<i8', (129,)), 'times_seconds_from_reference': ('<f8', (6, 16)),
                    'center_row_normalized_power': ('<f8', (6, 16)), 'fixed_flank_median_row_normalized_power': ('<f8', (6, 16)),
                    'center_minus_flank_each_row': ('<f8', (6, 16)), 'mean_fixed_track_frequency_profile': ('<f8', (6, 129)),
                    'scans': ('<U10', (6,)), 'df_hz': ('<f8', ()), 'source_channel0': ('<i8', ()),
                    'reference_frequency_hz': ('<f8', ()), 'drift_hz_s': ('<f8', ()), 'width_channels': ('<i8', ()),
                    'fixed_source_channel_shift': ('<i8', ())}
                check(set(values) == set(schema), 'Complete patch array schema differs')
                for field, (dtype, shape) in schema.items():
                    check(values[field].dtype == np.dtype(dtype) and values[field].shape == shape,
                          'Patch precision/shape differs: ' + field)
                raw = values['raw_power']
                check(np.isfinite(raw).all() and (raw >= 0).all(), 'Raw patch must be finite and nonnegative')
                same(values['scans'], np.asarray(SCANS), 'Patch scan order differs')
                same(values['source_channel_offsets'], offsets, 'Patch frequency offsets differ')
                same(values['saved_full_chunk_row_medians'], rowmedians, 'Patch joined row-median identity differs')
                for field, value in (('df_hz', DF), ('source_channel0', c0),
                    ('reference_frequency_hz', track['reference_frequency_hz']), ('drift_hz_s', track['drift_hz_s']),
                    ('width_channels', track['width_channels']), ('fixed_source_channel_shift', 0)):
                    check(values[field].item() == value, 'Fixed patch scalar differs: ' + field)
                dt = np.asarray([(headers[scan]['tstart'] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                                 - track['reference_seconds_from_anchor'] for scan in SCANS])
                centers = np.rint((track['reference_frequency_hz'] - FCH1) / DF
                                  + track['drift_hz_s'] * dt / DF).astype(np.int64)
                same(values['times_seconds_from_reference'], dt, 'Actual source time coordinates differ')
                same(values['frozen_source_channel_centers'], centers, 'Physical np.rint channel centers differ')
                check(centers.min() - 64 >= c0 and centers.max() + 64 < c0 + JOINED,
                      'Fixed profile lacks complete joined support')
                normalized = raw.astype(np.float64) / rowmedians[:, :, None]
                baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
                radius = track['width_channels'] // 2
                center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
                residual = center - baseline
                mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
                for field, expected in (('row_normalized_power', normalized),
                    ('fixed_flank_median_row_normalized_power', baseline), ('center_row_normalized_power', center),
                    ('center_minus_flank_each_row', residual), ('mean_fixed_track_frequency_profile', mean_profile)):
                    same(values[field], expected, 'Exact saved patch arithmetic differs: ' + field)
                check(record['fixed_frequency_shift_channels'] == 0
                    and record['fixed_flank_offsets'] == 'absolute channel offset > 3 within +/-64'
                    and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                    and len(record['scan_profiles']) == 6, 'Fixed descriptive profile contract differs')
                for i, profile in enumerate(record['scan_profiles']):
                    expected = {'scan_id': SCANS[i], 'mean_center_minus_flank': float(residual[i].mean()),
                        'median_center_minus_flank': float(np.median(residual[i])),
                        'positive_rows': int(np.count_nonzero(residual[i] > 0)),
                        'first_eight_mean_center_minus_flank': float(residual[i, :8].mean()),
                        'last_eight_mean_center_minus_flank': float(residual[i, 8:].mean()),
                        'all_16_center_minus_flank_rows': residual[i].tolist(),
                        'all_16_raw_width_mean_power': raw[i, :, 64-radius:65+radius].mean(axis=1).tolist(),
                        'frozen_source_channel_centers': centers[i].tolist()}
                    check(profile == expected, 'All16 saved scan summary/arithmetic values differ')
                buffers.append({'pair': pair, 'raw': raw, 'indices': centers[:, :, None] + offsets,
                                'filled': np.zeros(raw.shape, dtype=bool)})
                counts['patches'] += 1
                counts['scan_profiles'] += 6
                counts['time_row_occurrences'] += 96
                counts['retained_raw_patch_cells'] += raw.size
            pair_data[pair] = {'rowmedians': rowmedians, 'core_norms': core_norms}
            counts['pair_families'] += 1
            print('PASS_SAVED_S2017_JOINED_MAPS_RANKS_AND_FIXED_PROFILE_ARITHMETIC', pair, flush=True)
        # Full power arrays are streamed by scan: three64MiB native arrays,
        # one128MiB joined array and its median temporary, then released.
        import h5py
        import hdf5plugin  # Register the exact previously qualified filter.
        check(h5py.version.hdf5_version == '1.14.6', 'Actual HDF5 runtime differs')
        check(len(input_compacts) == 18, 'Exactly18 unique native compact files required')
        for scan_index, scan in enumerate(SCANS):
            powers = {}
            for chunk in (170, 171, 172):
                record, item, directory_name = input_compacts[(chunk, scan)]
                directory = confined(root, directory_name)
                leaf = Path(record['array_file'])
                check(leaf.name == str(leaf) and not leaf.is_absolute(), 'Single native compact filename required')
                path = confined(directory, str(leaf))
                before = {'sha256': digest(path), 'bytes': path.stat().st_size}
                check(before == {'sha256': record['file_sha256'], 'bytes': record['bytes']}, 'Compact full-file byte pin differs')
                pins[path.relative_to(root).as_posix()] = before
                with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                    data = handle['data']
                    check(data.shape == (16, 1, NATIVE) and data.dtype.str == '<f4'
                        and int(data.attrs['original_source_frequency_chunk_origin']) == chunk * NATIVE
                        and data.attrs['original_source_url'] == item['url']
                        and data.attrs['original_source_etag'] == item['etag'], 'Compact physical source/header identity differs')
                    power = data[:, 0, :]
                check(np.isfinite(power).all() and (power >= 0).all(), 'Full native source must be finite and nonnegative')
                for row_index, row in enumerate(record['decoded_rows']):
                    check(row['time_row'] == row_index and row['decoded_bytes'] == NATIVE * 4
                        and hashlib.sha256(power[row_index].tobytes(order='C')).hexdigest() == row['decoded_sha256'],
                        'Full native decoded row SHA differs')
                    counts['distinct_decoded_rows'] += 1
                for buffer in buffers:
                    if chunk not in PAIRS[buffer['pair']]:
                        continue
                    indices = buffer['indices'][scan_index]
                    where = np.nonzero((indices >= chunk * NATIVE) & (indices < (chunk + 1) * NATIVE))
                    observed = power[where[0], indices[where] - chunk * NATIVE]
                    retained = buffer['raw'][scan_index][where]
                    check(not buffer['filled'][scan_index][where].any(), 'Patch occurrence audited more than once')
                    check(np.array_equal(observed.view(np.uint32), retained.view(np.uint32)),
                          'Saved float32 raw cells differ bitwise from physical native source')
                    buffer['filled'][scan_index][where] = True
                    counts['raw_cells_bitwise_checked'] += observed.size
                powers[chunk] = power
                counts['distinct_compact_files'] += 1
            for pair, chunks in PAIRS.items():
                joined = np.concatenate([powers[chunk] for chunk in chunks], axis=1)
                check(joined.shape == (16, JOINED) and joined.dtype == np.dtype('<f4'), 'Joined full rawfloat32 shape differs')
                rowmedians = np.median(joined, axis=1).astype(np.float64)
                same(rowmedians, pair_data[pair]['rowmedians'][scan_index], 'Recomputed full2097152-channel float32 row median differs')
                counts['joined_full_float32_row_median_occurrences_recomputed'] += 16
                if scan in ONS:
                    for q in (255, 256):
                        median = np.median(joined[:, q * CORE:(q + 1) * CORE].astype(np.float64), axis=1)
                        same(median, pair_data[pair]['core_norms'][(scan, q)], 'Recomputed float64 ON core row median differs')
                        counts['ON_core_float64_row_medians_recomputed'] += 16
                del joined, rowmedians
            del powers, power
            print('AUTHENTICATED_S2017_THREE_NATIVE_SOURCES_BOTH_JOINED_MEDIANS_AND_PATCH_CELLS', scan, flush=True)
        check(all(buffer['filled'].all() for buffer in buffers), 'Every fixed raw-cell occurrence must be authenticated')
        check(counts == EXPECTED_COUNTS, 'Incomplete exact saved/source QA inventory: ' + str(counts))
        for name, pin in pins.items():
            path = confined(root, name)
            check(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during QA: ' + name)
        check(digest(own_path) == own_sha, 'QA script changed during execution')
        use = measured(started)
        check(0 < use['process_CPU_seconds_including_imports'] <= CPU_CAP
            and 0 < use['wall_seconds_including_imports'] <= WALL_CAP and 0 < use['peak_RSS_bytes'] <= RAM_CAP,
            'Actual QA exceeded declared resource caps')
        receipt = {'schema': QA_SCHEMA, 'status': QA_STATUS, 'qa_script_sha256': own_sha,
            'qa_public_freeze_commit': args.qa_freeze_commit, 'search_public_freeze_commit': args.search_freeze_commit,
            'driver_sha256': args.expected_driver_sha256, 'scope_SHA256s': expected_scope_shas,
            'pair_execution_receipt_SHA256s': expected_receipt_shas, 'counts': counts,
            'all_input_byte_pins': pins, 'new_acquisition_receipt_sha256': pins[NEW_ACQ]['sha256'],
            'new_source_QA_receipt_sha256': pins[NEW_SOURCE_QA]['sha256'],
            'prior171_acquisition_receipt_sha256': PRIOR_SHAS[PRIOR_ACQ],
            'prior171_source_QA_receipt_sha256': PRIOR_SHAS[PRIOR_QA],
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'detector_or_score_rerun': False, 'fixed_track_optimization_applied': False,
            'joined_full_row_medians_recomputed_from_native_sources': True,
            'ON_core_row_medians_recomputed_from_native_sources': True,
            'native_value_read_passes_per_distinct_compact': 1, 'compressed_sidecars_reopened': False,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'one_historical_visit': True, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'limitations': ['Saved maxima/ranks are audited; detector scores and full MAD/median-filter preprocessing are not rerun.',
                'Rawsource unique288 rows cover384 pair input-row occurrences because native171 is shared.',
                'Joined row medians are recomputed on all2097152 rawfloat32 channels, separately for each pair.',
                'Source compressed-range authenticity comes from actual prior/new sourceQA; redundant rawbins need not remain after archival.',
                'This QA establishes output/source integrity, not calibrated significance, source origin, sensitivity or independent visits.'], **use}
        save(review / 'QA_RECEIPT.json', receipt)
        print(json.dumps({'status': QA_STATUS, 'counts': counts, **use}), flush=True)
    except BaseException as exc:
        if created:
            save(review / 'QA_FAILURE_RECEIPT.json', {'schema': QA_SCHEMA,
                'status': 'FAIL_S2017_JOINED_SAVED_OUTPUT_QA_PRESERVE_OUTPUTS_NO_RETRY',
                'error_type': type(exc).__name__, 'error': str(exc), 'partial_counts': counts,
                'qa_script_sha256': own_sha, 'detector_or_score_rerun': False, **measured(started)})
        raise
    finally:
        signal.alarm(0)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    main()
