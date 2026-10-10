#!/usr/bin/env python3
"""One-shot independent source audit of twelve completed adjacent compacts.

Requires the exact acquisition, source, scope, independent static review and
public QA-code freeze pins plus root GO. Opens each compact once read-only,
checks compressed source bytes and decoded float32 row hashes, and performs no
HTTP, detector imports, score calculation, search, fitting or median calculation.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
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
BASE = 'analysis/s2017_next_native'
ACQUIRE = BASE + '/results/acquire'
OUT = BASE + '/results/source_review'
SCRIPT = BASE + '/qa_sources.py'
SCOPE = BASE + '/acquire_scope.json'
SOURCE = BASE + '/source_manifest_v2.json'
REVIEW = BASE + '/review/SOURCE_QA_STATIC_REVIEW.json'
LOCK = BASE + '/ACTIVE_FAMILY_FLOCK.lock'
PRIOR = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
SCOPE_SHA = '91392f8cfec0844fe0182d137496202d4f142b89814c91cd8b3f120a11fb920e'
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
DRIVER_SHA = '66c28eee043a02c138e29ac28ed4a38186ad17911f1553a050776b468d2525ba'
ACQUIRE_STATUS = 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
PASS = 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
NATIVES = (170, 172)
COUNT = 1048576
BODY = 597792529
BODY_CAP = 640 * 1024**2
CPU_CAP, WALL_CAP, RAM_CAP = 180, 1800, 4 * 1024**3
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
    'source_descriptors': 192, 'exact_range_records': 192, 'unique_source_ranges': 192,
    'durable_raw_sidecars': 192, 'compressed_source_chunks': 192, 'decoded_rows': 192}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for raw in iter(lambda: handle.read(1024**2), b''):
            h.update(raw)
    return h.hexdigest()


def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('utf8'))


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def confined(root, name):
    relative = Path(name)
    check(not relative.is_absolute() and '..' not in relative.parts, 'Relative confined path required')
    path = root / relative
    check(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Path outside frozen workspace or symlink')
    return path


def pinned_json(root, name, expected, pins):
    check(re.fullmatch('[0-9a-f]{64}', expected), 'Exact SHA256 required: ' + name)
    raw = confined(root, name).read_bytes()
    check(sha(raw) == expected, 'Pinned JSON differs: ' + name)
    pins[name] = {'sha256': expected, 'bytes': len(raw)}
    return json.loads(raw, object_pairs_hook=pairs)


def authenticate(root, name, pin, pins):
    path = confined(root, name)
    check(isinstance(pin['bytes'], int) and pin['bytes'] > 0
        and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'Invalid byte pin: ' + name)
    check(path.is_file() and path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'],
        'Authenticated file differs: ' + name)
    check(name not in pins or pins[name] == pin, 'Conflicting byte pin: ' + name)
    pins[name] = dict(pin)
    return path


def save_new(path, value):
    check(not path.exists(), 'Refuse receipt overwrite')
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    temporary.replace(path)


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def identity(record):
    return record['native_chunk_index'], record['scan_id'], record['time_row']


def source_contract(source, prior):
    check(source['schema'] == 'SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1'
        and source['status'] == 'PASS_EXACT192_FROZEN_SOURCE_DESCRIPTORS_METADATA_ONLY'
        and source['native_chunk_indices'] == list(NATIVES) and source['scan_order'] == list(SCANS)
        and source['spectral_values_read'] is False and source['spectral_payload_fetched'] is False
        and source['rows_per_scan'] == 16 and source['native_chunk_channels'] == COUNT
        and source['fch1_hz'] == 2802832031.25 and source['df_hz'] == -2.7939677238464355
        and source['tsamp_s'] == 18.253611008 and set(source['by_native_chunk']) == {'170', '172'},
        'Exact metadata-only adjacent source geometry required')
    sources, descriptors, ranges = {}, {}, {label: [] for label in SCANS}
    prior_items = {item['label']: item for item in prior['sources']}
    check(tuple(prior_items) == SCANS, 'Prior source order differs')
    total = 0
    for native in NATIVES:
        band = source['by_native_chunk'][str(native)]
        check(band['native_chunk_index'] == native
            and band['physical_channel_interval_half_open'] == [native * COUNT, (native + 1) * COUNT]
            and [item['label'] for item in band['sources']] == list(SCANS), 'Native source frame/order differs')
        subtotal, previous = 0, -math.inf
        anchor = min(item['current_header']['data_attributes']['tstart'] for item in band['sources'])
        for item in band['sources']:
            label, header = item['label'], item['current_header']
            sources[native, label] = item
            original = prior_items[label]
            check(all(item[key] == original[key] for key in ('url', 'etag', 'source_file_bytes', 'current_header')),
                'Adjacent descriptor changed immutable original source/header')
            check(item['role'] == ('on' if label.endswith('_on') else 'off')
                and item['url'].startswith('https://bldata.berkeley.edu/pipeline/AGBT17A_999_55/holding/')
                and re.fullmatch(r'"[^"\r\n]+"', item['etag']) and item['source_file_bytes'] > 0,
                'Source URL/strong ETag/size/role differs')
            attrs = header['data_attributes']
            check(header['dataset_shape'] == [16, 1, 359661568]
                and header['dataset_chunks'] == [1, 1, COUNT] and header['dtype_exact'] == '<f4'
                and header['dataset_dtype'] == 'float32' and len(header['hdf5_filters']) == 1
                and header['hdf5_filters'][0][:3] == [32008, 1, [0, 3, 4, 0, 2]]
                and attrs['fch1'] * 1e6 == source['fch1_hz'] and attrs['foff'] * 1e6 == source['df_hz']
                and attrs['tsamp'] == source['tsamp_s'] and attrs['nchans'] == 359661568,
                'Original dataset/grid/filter header differs')
            start = (attrs['tstart'] - anchor) * 86400
            check(math.isfinite(start) and start >= previous, 'Source times overlap or are unordered')
            previous = start + 16 * source['tsamp_s']
            check([row['time_row'] for row in item['chunks']] == list(range(16)), 'All16 ordered descriptors required')
            for row in item['chunks']:
                index, offset, size = row['time_row'], row['byte_offset'], row['stored_size']
                check(row['chunk_origin'] == [index, 0, native * COUNT] and row['filter_mask'] == 0
                    and row['decoded_size'] == COUNT * 4 and isinstance(size, int) and 0 < size <= COUNT * 4
                    and isinstance(offset, int) and 0 <= offset <= item['source_file_bytes'] - size
                    and row['byte_range'] == f'bytes={offset}-{offset + size - 1}', 'Source descriptor bounds differ')
                descriptors[native, label, index] = row
                ranges[label].append((offset, offset + size)); subtotal += size
            check(item['future_spectral_payload_bytes'] == sum(row['stored_size'] for row in item['chunks']),
                'Per-source payload sum differs')
        check(subtotal == band['total_future_spectral_payload_bytes'], 'Native payload total differs')
        total += subtotal
    for label, intervals in ranges.items():
        ordered = sorted(intervals)
        check(len(set(ordered)) == 32 and all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])),
            'Repeated or overlapping new source ranges')
        check(all(not (lo < row['byte_offset'] + row['stored_size'] and row['byte_offset'] < hi)
            for lo, hi in ordered for row in prior_items[label]['chunks']), 'Previously opened171 range repeated')
    check(len(descriptors) == 192 and total == source['total_future_spectral_payload_bytes'] == BODY,
        'Exact192 source descriptors/payload total required')
    return sources, descriptors


def acquisition_contract(acquired, scope, freeze):
    expected = {'schema': 'SETI_S2017_ADJACENT170_172_ACQUISITION_RECEIPT_V1', 'status': ACQUIRE_STATUS,
        'phase': 'acquire', 'scope_sha256': SCOPE_SHA, 'driver_sha256': DRIVER_SHA,
        'source_manifest_sha256': SOURCE_SHA, 'public_freeze_commit': freeze,
        'native_chunk_indices': list(NATIVES), 'new_telescope_HTTP_requests': 192,
        'new_telescope_BODY_bytes': BODY, 'reserved_BODY_upper_bound_bytes': BODY + 192,
        'source_range_count_authenticated': 192, 'complete_compact_files': 12, 'decoded_row_SHA256s': 192,
        'standalone_durable_raw_range_files': 192, 'repeated_source_GETs': 0, 'source_workers_max': 4,
        'HDF5_assembly_threads': 1, 'write_decode_interleaving': False,
        'all12_writers_closed_before_any_value_decode': True, 'source_worker_errors': [],
        'whole_original_telescope_MD5_verified': False, 'retry_resume_or_rerun_authorized': False,
        'scientific_search_run': False, 'qualified_sky_detection': False, 'OFF_veto_applied': False,
        'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'cost_DKK': 0,
        'CPU_cap_s': 180, 'wall_cap_s': 1800, 'memory_cap_bytes': 2 * 1024**3,
        'workspace_cap_bytes': 8 * 1024**3, 'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'}}
    check(all(acquired.get(key) == value for key, value in expected.items()), 'Actual COMPLETE acquisition contract differs')
    for key, upper in (('process_CPU_seconds_including_imports', 180), ('wall_seconds_including_imports', 1800),
            ('peak_RSS_bytes', 2 * 1024**3), ('workspace_allocated_bytes_after', 8 * 1024**3),
            ('acquisition_artifact_bytes', scope['acquisition_artifact_cap_bytes'])):
        check(isinstance(acquired[key], (int, float)) and math.isfinite(acquired[key])
            and 0 < acquired[key] <= upper, 'Measured acquisition cap exceeded: ' + key)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'expected-acquisition-sha256', 'acquisition-freeze-commit', 'qa-freeze-commit',
            'expected-qa-sha256', 'expected-static-review-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-complete-acquisition', action='store_true')
    args = parser.parse_args()
    check(args.root_go_after_complete_acquisition, 'Root GO after COMPLETE acquisition and static review required')
    check(all(re.fullmatch('[0-9a-f]{40}', value) for value in
        (args.acquisition_freeze_commit, args.qa_freeze_commit)), 'Actual public40-hex freeze commits required')
    root = Path(args.root).resolve(); pins = {}
    authenticate(root, SCRIPT, {'sha256': args.expected_qa_sha256, 'bytes': Path(__file__).stat().st_size}, pins)
    check(Path(__file__).resolve() == confined(root, SCRIPT), 'QA script path differs')
    scope = pinned_json(root, SCOPE, SCOPE_SHA, pins)
    check(scope['schema'] == 'SETI_S2017_ADJACENT170_172_ACQUISITION_SCOPE_V1'
        and scope['source_manifest_path'] == SOURCE and scope['driver_sha256'] == DRIVER_SHA
        and scope['family_lock_path'] == LOCK and scope['output_stage'] == ACQUIRE
        and scope['exact_expected_payload_BODY_bytes'] == BODY and scope['reserved_payload_BODY_upper_bound_bytes'] == BODY + 192
        and scope['expected_compact_files'] == 12 and scope['expected_raw_sidecars'] == 192,
        'Exact frozen acquisition scope required')
    for name, pin in scope['pinned_metadata_and_code'].items():
        check(Path(name).suffix.lower() not in ('.h5', '.hdf5', '.npz', '.npy'), 'Metadata preflight may not open power files')
        authenticate(root, name, pin, pins)
    source = pinned_json(root, SOURCE, SOURCE_SHA, pins)
    prior = pinned_json(root, PRIOR, scope['pinned_metadata_and_code'][PRIOR]['sha256'], pins)
    sources, descriptors = source_contract(source, prior)
    reviewed = pinned_json(root, REVIEW, args.expected_static_review_sha256, pins)
    check(reviewed['status'] == 'PASS_INDEPENDENT_STATIC_SOURCE_QA_NO_VALUES'
        and reviewed['qa_script_sha256'] == args.expected_qa_sha256, 'Independent static source-QA PASS required')
    acquired = pinned_json(root, ACQUIRE + '/ACQUISITION_RESULT.json', args.expected_acquisition_sha256, pins)
    acquisition_contract(acquired, scope, args.acquisition_freeze_commit)
    for package, version in VERSIONS.items():
        check(importlib.metadata.version(package) == version, 'Runtime package differs: ' + package)
    out = confined(root, OUT); out.mkdir(parents=True, exist_ok=False)
    lock_handle = None
    def deadline(signum, frame):
        raise TimeoutError('Frozen source QA CPU/wall limit reached')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        lock_handle = confined(root, LOCK).open('a+b')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage = confined(root, ACQUIRE)
        for name in ('INPUT_PINS.json', 'SOURCE_BODY_LEDGER.json'):
            path = stage / name
            authenticate(root, ACQUIRE + '/' + name, {'sha256': digest(path), 'bytes': path.stat().st_size}, pins)
        inputs = pinned_json(root, ACQUIRE + '/INPUT_PINS.json', pins[ACQUIRE + '/INPUT_PINS.json']['sha256'], pins)
        check(inputs == {'scope_sha256': SCOPE_SHA, 'public_freeze_commit': args.acquisition_freeze_commit,
            'pinned_metadata_and_code': scope['pinned_metadata_and_code']}, 'Acquisition INPUT_PINS differs')
        ledger = pinned_json(root, ACQUIRE + '/SOURCE_BODY_LEDGER.json', pins[ACQUIRE + '/SOURCE_BODY_LEDGER.json']['sha256'], pins)
        check(all(ledger.get(key) == value for key, value in {'schema': 'SETI_S2017_ADJACENT170_172_SOURCE_BODY_LEDGER_V1',
            'requests_attempted': 192, 'BODY_bytes_received': BODY, 'BODY_reserved_upper_bound_bytes': BODY + 192,
            'BODY_cap_bytes': BODY_CAP, 'HTTP_request_cap': 192, 'complete': True}.items()), 'Completed exact source ledger differs')
        guard = ledger['completion_resource_guard']
        check(guard['status'] == 'PASS_BEFORE_COMPLETE' and all(guard[key] == acquired[key] for key in
            ('process_CPU_seconds_including_imports', 'wall_seconds_including_imports', 'peak_RSS_bytes', 'acquisition_artifact_bytes'))
            and guard['workspace_allocated_bytes'] == acquired['workspace_allocated_bytes_after'], 'Actual completion resource guard differs')
        keys = [(native, label, row) for native in NATIVES for label in SCANS for row in range(16)]
        requests, raw_records = acquired['value_read_requests'], acquired['raw_range_records']
        check([identity(record) for record in requests] == keys and [identity(record) for record in raw_records] == keys,
            'Exactly192 unique ordered source request/raw records required')
        expected_files = {'INPUT_PINS.json', 'SOURCE_BODY_LEDGER.json', 'ACQUISITION_RESULT.json'}
        raw_map = {}
        for request, record, key in zip(requests, raw_records, keys):
            native, label, index = key; item, descriptor = sources[native, label], descriptors[key]
            size, offset = descriptor['stored_size'], descriptor['byte_offset']
            raw_name = f'raw_ranges/native{native}_{label}_row{index:02d}.raw.bin'
            check(request['attempt'] == 1 and request['status'] == 'PASS_EXACT_SOURCE_RANGE'
                and request['http_status'] == 206 and request['request_url'] == request['response_url'] == item['url']
                and request['expected_etag'] == item['etag'] and request['source_file_bytes'] == item['source_file_bytes']
                and request['request_range'] == descriptor['byte_range'] and request['body_bytes_received'] == size
                and request['standalone_raw_path'] == raw_name and request['standalone_raw_fsynced'] is True,
                'Exact one-shot source request provenance differs')
            headers = request['request_headers']; response = request['response_headers']
            check(headers['Range'] == descriptor['byte_range'] and headers['If-Match'] == item['etag']
                and headers['Accept-Encoding'] == 'identity' and response['ETag'] == item['etag']
                and response['Content-Range'] == f'bytes {offset}-{offset + size - 1}/{item["source_file_bytes"]}'
                and response['Content-Length'] == str(size)
                and (response['Content-Encoding'] or 'identity').lower() == 'identity'
                and math.isfinite(request['wall_s']) and request['wall_s'] > 0, 'Exact request/response headers differ')
            check(record['path'] == raw_name and record['stored_size'] == size and record['filter_mask'] == 0
                and record['original_source_chunk_origin'] == descriptor['chunk_origin']
                and record['source_range'] == descriptor['byte_range'] and record['fsync_before_HDF5'] is True
                and record['origin'] == 'NEW_PREVIOUSLY_UNATTEMPTED_EXACT_SOURCE_RANGE'
                and record['raw_sha256'] == request['raw_sha256'] == record['compact_raw_roundtrip_sha256'],
                'Durable raw range mapping/roundtrip differs')
            authenticate(root, ACQUIRE + '/' + raw_name, {'sha256': record['raw_sha256'], 'bytes': size}, pins)
            expected_files.add(raw_name); raw_map[key] = record
        file_records, pipeline_records = acquired['decoded_files'], acquired['local_pipeline_records']
        file_keys = [(native, label) for native in NATIVES for label in SCANS]
        check([(record['native_chunk_index'], record['scan_id']) for record in file_records] == file_keys
            and [(record['native_chunk_index'], record['scan_id']) for record in pipeline_records] == file_keys,
            'Exactly12 ordered compact/pipeline records required')
        check(set(acquired['decoded_row_progress']) == {f'native{native}_{label}' for native, label in file_keys},
            'Decoded row progress inventory differs')
        import numpy as np
        import h5py
        import hdf5plugin  # registers the public bitshuffle decoder; no custom codec
        check(h5py.version.hdf5_version == '1.14.6' and h5py.h5z.filter_avail(32008)
            and h5py.h5z.get_filter_info(32008) & h5py.h5z.FILTER_CONFIG_DECODE_ENABLED, 'HDF5 public decoder unavailable')
        compact_pins = {}; checked_raw = checked_decoded = 0
        for record, pipeline, (native, label) in zip(file_records, pipeline_records, file_keys):
            name = f'native{native}_{label}.compact.h5'; item = sources[native, label]
            check(record['array_file'] == name and record['shape'] == [16, 1, COUNT]
                and record['source_channel0'] == native * COUNT
                and [row['time_row'] for row in record['decoded_rows']] == list(range(16))
                and record['decoded_rows'] == acquired['decoded_row_progress'][f'native{native}_{label}'],
                'Compact decoded-row geometry/progress differs')
            pin = {'sha256': record['file_sha256'], 'bytes': record['bytes']}
            path = authenticate(root, ACQUIRE + '/' + name, pin, pins)
            compact_pins[ACQUIRE + '/' + name] = pin; expected_files.add(name)
            with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
                check(set(handle) == {'data'} and len(handle.attrs) == 0, 'Compact root schema differs')
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.chunks == (1, 1, COUNT) and data.dtype.str == '<f4'
                    and data.id.get_num_chunks() == 16, 'Compact float32/chunk/allocation geometry differs')
                check(set(data.attrs) == {'original_source_frequency_chunk_origin', 'original_source_url', 'original_source_etag'}
                    and int(data.attrs['original_source_frequency_chunk_origin']) == native * COUNT
                    and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'],
                    'Compact original source provenance/header mapping differs')
                plist = data.id.get_create_plist(); check(plist.get_nfilters() == 1, 'One source filter required')
                actual = plist.get_filter(0)
                current = [actual[0], actual[1], list(actual[2]), actual[3].decode('utf8', 'replace')]
                original = item['current_header']['hdf5_filters'][0]
                check(pipeline['original_filter'] == original and pipeline['current_filter'] == current
                    and pipeline['prefix_identity_claim'] is False and pipeline['semantic_parameters_preserved'] is True
                    and current[:2] == original[:2] and current[2][2:] == original[2][2:], 'Compact filter pipeline differs')
                for row in record['decoded_rows']:
                    index = row['time_row']; raw_record = raw_map[native, label, index]
                    mask, compressed = data.id.read_direct_chunk((index, 0, 0))
                    check(mask == 0 and len(compressed) == raw_record['stored_size']
                        and sha(compressed) == raw_record['raw_sha256'], 'Compressed compact source chunk differs')
                    checked_raw += 1
                    values = data[index, 0, :]
                    check(values.shape == (COUNT,) and values.dtype.str == '<f4'
                        and row['decoded_bytes'] == values.nbytes == COUNT * 4
                        and np.isfinite(values).all() and (values >= 0).all()
                        and sha(values.tobytes(order='C')) == row['decoded_sha256'], 'Decoded native float32 row differs')
                    checked_decoded += 1
        check(checked_raw == checked_decoded == 192 and len(compact_pins) == 12, 'Source QA actual counts differ')
        inventory = {path.relative_to(stage).as_posix() for path in stage.rglob('*') if path.is_file()}
        check(inventory == expected_files and len(inventory) == 207, 'Acquisition output inventory changed or incomplete')
        for name, pin in tuple(pins.items()):
            authenticate(root, name, pin, pins)
        use = measured(started)
        check(use['process_CPU_seconds_including_imports'] <= CPU_CAP and use['wall_seconds_including_imports'] <= WALL_CAP
            and use['peak_RSS_bytes'] <= RAM_CAP, 'Measured source QA resource cap exceeded')
        result = {'schema': 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1', 'status': PASS,
            'counts': COUNTS, 'acquisition_receipt_sha256': args.expected_acquisition_sha256,
            'source_manifest_sha256': SOURCE_SHA, 'scope_sha256': SCOPE_SHA, 'driver_sha256': DRIVER_SHA,
            'public_freeze_commit': args.acquisition_freeze_commit, 'qa_public_freeze_commit': args.qa_freeze_commit,
            'qa_script_sha256': args.expected_qa_sha256, 'static_review_sha256': args.expected_static_review_sha256,
            'source_range_raw_record_sha256': canonical_sha(acquired['raw_range_records']),
            'decoded_file_row_record_sha256': canonical_sha(acquired['decoded_files']),
            'source_range_request_record_sha256': canonical_sha(acquired['value_read_requests']),
            'record_digest_method': "SHA256(UTF8(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)))",
            'compact_input_byte_pins': compact_pins, 'all_input_byte_pins': pins,
            'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version},
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, **use,
            'compact_files_opened_once_read_only': 12, 'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
            'detector_or_score_rerun': False, 'medians_recomputed': False, 'qualified_sky_detection': False,
            'OFF_veto_applied': False, 'calibrated_SNR_FAP': False, 'whole_original_telescope_MD5_verified': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'retry_resume_or_rerun_authorized': False, 'cost_DKK': 0,
            'limitations': ['Checks saved adjacent source bytes and decoded row identity only.',
                'Earlier native171 values and results were known before adjacent170/172 selection.',
                'No new visit, independent replication, sky qualification, OFF veto or calibrated FAP.',
                'Root may remove raw sidecars only after independently verified durable RAW archive; compact pins remain.']}
        save_new(out / 'QA_RECEIPT.json', result)
        print(json.dumps({'status': PASS, 'counts': COUNTS, **use}), flush=True)
    except BaseException as error:
        failure = {'schema': 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_FAILURE_V1',
            'status': 'INCOMPLETE_SOURCE_QA_PRESERVE_OUTPUTS_NO_RERUN', 'error_type': type(error).__name__,
            'error': str(error), 'acquisition_receipt_sha256': args.expected_acquisition_sha256,
            'qa_script_sha256': args.expected_qa_sha256, **measured(started)}
        save_new(out / 'FAILURE_RECEIPT.json', failure)
        raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:
            lock_handle.close()


if __name__ == '__main__':
    main()
