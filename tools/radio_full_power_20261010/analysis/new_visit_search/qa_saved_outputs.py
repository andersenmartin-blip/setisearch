"""Independently audit completed frozen S2017 outputs against acquired sources.

No network, detector, score calculation, optimization, or new selection search.
Top20 is reconstructed only from saved maxima. Each of six native HDF5 files
is opened once;96 compressed chunks and96 decoded rows are authenticated, and
111456 saved raw-patch occurrences are compared bitwise at physical indices.
Run only after root reviews an actual COMPLETE search receipt and supplies GO.
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
COUNT, CHUNK, Q, CORE, HALO = 1048576, 171, 128, 4096, 4000
C0, FIRST = CHUNK * COUNT, CHUNK * COUNT + Q * CORE
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, RAM_CAP = 180, 1800, 4 * 1024**3
BODY_CAP, BODY_BYTES, RESERVED_BODY = 512 * 1024**2, 298238620, 298238716
BASE_SCOPE_SHA = '4fbbf3f3c82aad866a08d864bf3232662549f7d0d93c01dff21655f8513aa468'
BASE_DRIVER_SHA = 'e6c2c54dedb6b70a2997a62b03ded523a1915940c2dae16fcc5d3d3c8ffe57dd'
ORIGINAL_FAILURE_SHA = '37e2fcdb66dfe4187dd6a43f067879cdc4e6cf3bfb7dae6c877cb0fcafdf33f6'
SCOPE_SHA = 'a93d6dda3f813b84be2452928fe42be76b6de3cb96cf4f85c9beda47adc9ea86'
DRIVER_SHA = 'ca9c3890a8be325061e62c03b05aa795a582fc7d10012f0a565d8779920e6bf6'
FREEZE = 'e8ada3c888d1f07b33d25dccb9f7ddc0c7d23995'
STAGE = 'analysis/new_visit_recovery/results'
FULLNORM = 'full1048576-channel row median computed on raw float32, then profile float64 promotion'
EXPECTED_COUNTS = {'maps': 3, 'map_normalization_records': 3, 'carrier_maximum_records': 12288,
    'valid_hypothesis_records': 19292160, 'top20_entries': 60, 'patches': 9,
    'scan_profiles': 54, 'time_row_occurrences': 864, 'retained_raw_patch_cells': 111456,
    'compact_files': 6, 'compressed_source_chunks': 96, 'decoded_rows': 96,
    'durable_raw_sidecars': 96, 'preserved_prior_decoded_rows_matched': 26,
    'native_row_medians_recomputed': 96, 'ON_core_row_medians_recomputed': 48,
    'raw_cells_bitwise_checked': 111456}


def check(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            hasher.update(block)
    return hasher.hexdigest()


def save_new(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    check(not path.exists(), 'Refuse receipt overwrite: ' + str(path))
    with temporary.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def confined(root, name):
    relative = Path(name)
    check(not relative.is_absolute() and '..' not in relative.parts, 'Require relative path: ' + str(name))
    path = root / relative
    check(path.resolve().is_relative_to(root), 'Path escapes root: ' + str(name))
    return path


def same(actual, expected, label):
    check(actual.shape == expected.shape and np.array_equal(actual, expected), label)


def use(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_including_imports': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit',
                 'acquisition-receipt', 'expected-acquisition-sha256',
                 'search-receipt', 'expected-search-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-complete-search', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    check(args.root_go_after_complete_search, 'Actual complete search review and root GO required')
    check(args.expected_scope_sha256 == SCOPE_SHA and args.freeze_commit == FREEZE,
          'Exact frozen scope and actual public freeze commit required')
    for value in (args.expected_acquisition_sha256, args.expected_search_sha256):
        check(re.fullmatch('[0-9a-f]{64}', value), 'Root-reviewed complete receipt SHA256 required')
    check(Path(args.scope).resolve() == root / 'analysis/new_visit_recovery/scope.json', 'Wrong fixed scope path')
    acquire = root / STAGE / 'acquire'
    out = root / STAGE / 'search'
    check(Path(args.acquisition_receipt).resolve() == acquire / 'ACQUISITION_RESULT.json', 'Wrong acquisition stage')
    check(Path(args.search_receipt).resolve() == out / 'EXECUTION_RECEIPT.json', 'Wrong search stage')
    # A second invocation preserves the first QA result or failure rather than replacing it.
    review = root / STAGE / 'review'
    review.mkdir(parents=True, exist_ok=False)
    counts = {name: 0 for name in EXPECTED_COUNTS}
    pins, buffers, map_normalizations = {}, [], {}
    own_path, lock_handle = Path(__file__).resolve(), None
    own_sha = digest(own_path)

    def deadline(signum, frame):
        raise TimeoutError('S2017 QA CPU/wall deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))

    def read_bytes(path, declared=None, expected_sha=None):
        path = Path(path)
        raw = path.read_bytes()
        pin = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if declared is not None:
            check(pin == declared, 'Exact saved bytes differ: ' + str(path))
        if expected_sha is not None:
            check(pin['sha256'] == expected_sha, 'Root-reviewed receipt/scope bytes differ: ' + str(path))
        key = str(path.absolute())
        check(key not in pins or pins[key] == pin, 'Previously read input changed: ' + key)
        pins[key] = pin
        return raw

    def read_json(path, declared=None, expected_sha=None):
        return json.loads(read_bytes(path, declared, expected_sha))

    def npz(record):
        raw = read_bytes(confined(out, record['path']), {'sha256': record['sha256'], 'bytes': record['bytes']})
        with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
            check(len(archive.files) == len(set(archive.files)), 'Duplicate NPZ fields')
            return {name: archive[name] for name in archive.files}

    try:
        # File existence is harmless. Kernel ownership excludes acquire/search/QA overlap.
        lock_handle = (root / STAGE / 'ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        scope = read_json(args.scope, expected_sha=SCOPE_SHA)
        check(scope['schema'] == 'SETI_NEW_S2017_RETAINED27_UNATTEMPTED69_CORE128_V1'
              and scope['driver_sha256'] == DRIVER_SHA and scope['output_stage'] == STAGE,
              'Require frozen S2017 family')
        prior_file_pins = {}
        for name, pin in scope['pinned_metadata_and_code'].items():
            if Path(name).suffix.lower() == '.h5':
                prior_file_pins[name] = pin
                continue
            check(Path(name).suffix.lower() not in ('.hdf5', '.npy', '.npz', '.bin'), 'Unexpected power pin in metadata contract')
            read_bytes(confined(root, name), declared=pin)
        check(set(prior_file_pins) == {'analysis/new_visit_search/results/acquire/' + scan + '.compact.h5' for scan in SCANS},
              'Only the six unchanged original partial HDF5 files may be checksum-pinned')
        base = read_json(root / 'analysis/new_visit_search/scope.json', expected_sha=BASE_SCOPE_SHA)
        check(base['driver_sha256'] == BASE_DRIVER_SHA, 'Original frozen driver identity differs')
        for name, pin in base['pinned_metadata_and_code'].items():
            read_bytes(confined(root, name), declared=pin)
        check(scope['unchanged_original_dependency_SHA256s'] == base['unchanged_original_dependency_SHA256s']
              and all(scope[key] == base[key] for key in ('scan_order', 'rows_per_scan', 'native_chunk_index',
                  'native_chunk_count', 'source_channel_interval_half_open', 'core_q', 'core_interval_half_open',
                  'crop_interval_half_open', 'fch1_hz', 'df_hz', 'tsamp_s', 'drift_grid', 'widths_channels',
                  'core_channel_count', 'crop_halo_channels', 'search_ON_maps', 'valid_hypotheses_per_carrier',
                  'rank_count_per_ON', 'display_suppression_channels', 'fixed_profile_ranks_per_ON',
                  'expected_fixed_profiles', 'profile_shift_channels', 'profile_halfwidth_channels',
                  'fixed_profile_normalization', 'source_manifest_path')), 'Recovery changes frozen scientific geometry')
        for role in ('detector', 'gap', 'reader'):
            check(scope['pinned_metadata_and_code'][scope['code_paths'][role]]['sha256']
                  == base['unchanged_original_dependency_SHA256s'][role], 'Recovery scientific dependency changed')
        check(scope['reused_source_ranges'] == 27 and scope['previously_unattempted_source_ranges'] == 69
              and scope['original_received_BODY_bytes'] == 83845205
              and scope['original_reserved_BODY_upper_bound_bytes'] == 83845232
              and scope['exact_remaining_payload_BODY_bytes'] == 214393415
              and scope['remaining_reserved_BODY_upper_bound_bytes'] == 214393484,
              'Corrected continuation request partition differs')
        original = read_json(confined(root, scope['original_acquisition_receipt']), expected_sha=ORIGINAL_FAILURE_SHA)
        check(original['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY'
              and original['phase'] == 'acquire' and original['scope_sha256'] == BASE_SCOPE_SHA
              and original['driver_sha256'] == BASE_DRIVER_SHA
              and original['public_freeze_commit'] == scope['original_source_selection_public_freeze_commit']
              and scope['original_source_selection_scope_sha256'] == BASE_SCOPE_SHA
              and scope['source_values_already_opened_in_original_failed_family'] is True
              and scope['previously_decoded_rows'] == 26 and scope['scientific_search_previously_run'] is False
              and scope['original_failed_family_preserved'] is True
              and scope['repeated_source_GETs_authorized'] == 0 and scope['received_original_payloads_lost'] == 0,
              'Original failed acquisition must remain unchanged, with no prior search')
        inventory = read_json(confined(root, scope['retained_raw_inventory']))
        check(inventory['total_retained_received_chunks'] == 27 and inventory['received_chunks_lost'] == 0,
              'All27 prior received ranges must have retained source provenance')
        for package, version in scope['runtime_package_versions'].items():
            check(importlib.metadata.version(package) == version, 'Runtime differs: ' + package)
        source = read_json(confined(root, scope['source_manifest_path']))
        check(source['native_chunk_index'] == CHUNK
              and source['physical_channel_interval_half_open'] == [C0, C0 + COUNT]
              and source['spectral_values_read'] is False and source['spectral_payload_fetched'] is False,
              'Prospective physical source selection differs')
        items = source['sources']
        check([item['label'] for item in items] == list(SCANS)
              and [item['role'].upper() for item in items] == ['ON', 'OFF'] * 3, 'Six source scan identities differ')
        headers = {item['label']: item['current_header']['data_attributes'] for item in items}
        anchor = float(min(header['tstart'] for header in headers.values()))
        previous_end, total_source_bytes = -math.inf, 0
        descriptors = {}
        for item in items:
            header, attributes = item['current_header'], headers[item['label']]
            check(header['dataset_shape'] == [16, 1, 359661568]
                  and header['dataset_chunks'] == [1, 1, COUNT]
                  and header['dataset_dtype'] == 'float32' and header['dtype_exact'] == '<f4'
                  and len(header['hdf5_filters']) == 1
                  and header['hdf5_filters'][0][:3] == [32008, 1, [0, 3, 4, 0, 2]], 'Physical source filter/shape differs')
            check(attributes['fch1'] * 1e6 == FCH1 and attributes['foff'] * 1e6 == DF
                  and attributes['tsamp'] == TSAMP and attributes['nchans'] == 359661568, 'Physical S-band grid differs')
            check(item['url'].startswith('https://bldata.berkeley.edu/pipeline/AGBT17A_999_55/holding/')
                  and re.fullmatch(r'"[^"\r\n]+"', item['etag']) and item['source_file_bytes'] > 0,
                  'Prospective source URL/strong ETag/size differs')
            start = (attributes['tstart'] - anchor) * 86400
            check(math.isfinite(start) and start >= previous_end, 'Actual chronological scan times overlap')
            previous_end = start + 16 * TSAMP
            check([row['time_row'] for row in item['chunks']] == list(range(16)), 'Every physical native row required')
            for row in item['chunks']:
                offset, size = row['byte_offset'], row['stored_size']
                check(row['chunk_origin'] == [row['time_row'], 0, C0] and row['filter_mask'] == 0
                      and row['decoded_size'] == COUNT * 4 and 0 < size <= COUNT * 4
                      and offset >= 0 and offset + size <= item['source_file_bytes']
                      and row['byte_range'] == f'bytes={offset}-{offset+size-1}', 'Physical source range differs')
                descriptors[(item['label'], row['time_row'])] = (item, row)
                total_source_bytes += size
        check(total_source_bytes == BODY_BYTES and total_source_bytes + 96 == RESERVED_BODY <= BODY_CAP,
              'Exact96 source ranges differ from payload budget')
        acquisition = read_json(args.acquisition_receipt, expected_sha=args.expected_acquisition_sha256)
        result = read_json(args.search_receipt, expected_sha=args.expected_search_sha256)
        # All executable/metadata contracts are already authenticated. Verify
        # unchanged prior file bytes by streaming hash only, without HDF5 opens.
        for name, declared in prior_file_pins.items():
            path = confined(root, name)
            pin = {'sha256': digest(path), 'bytes': path.stat().st_size}
            check(pin == declared, 'Original partial source bytes changed')
            pins[str(path.absolute())] = pin
        for record, phase, status, cpu_cap in (
            (acquisition, 'acquire', 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY', 180),
            (result, 'search', 'COMPLETE_NEW_S2017_THREE_CORE_MAPS_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY', 120)):
            check(record['status'] == status and record['phase'] == phase
                  and record['scope_sha256'] == SCOPE_SHA and record['driver_sha256'] == DRIVER_SHA
                  and record['public_freeze_commit'] == args.freeze_commit
                  and record['source_manifest_sha256'] == scope['pinned_metadata_and_code'][scope['source_manifest_path']]['sha256'],
                  'Exact same-family COMPLETE receipt required: ' + phase)
            for name, expected in (('CPU_cap_s', cpu_cap), ('wall_cap_s', WALL_CAP), ('memory_cap_bytes', RAM_CAP),
                ('new_visit', True), ('same_frequency_replication_of_old_Lband_cases', False),
                ('blind_source_selection_before_original_value_opening', True),
                ('source_values_already_opened_in_original_failed_family', True),
                ('previously_decoded_rows', 26), ('scientific_search_previously_run', False), ('qualified_sky_detection', False),
                ('OFF_veto_applied', False), ('calibrated_SNR_FAP', False), ('original_A_B_status', 'FAIL_CLOSED_UNCHANGED'),
                ('retry_resume_or_rerun_authorized', False), ('cost_DKK', 0), ('limitations', scope['limitations'])):
                check(record[name] == expected, 'Exploratory receipt contract differs: ' + phase + '/' + name)
            for name, cap in (('process_CPU_seconds_including_imports', cpu_cap),
                              ('wall_seconds_including_imports', WALL_CAP), ('peak_RSS_bytes', RAM_CAP)):
                check(0 < record[name] <= cap, 'Completed resource guard differs: ' + phase + '/' + name)
            inputs = read_json(root / STAGE / phase / 'INPUT_PINS.json')
            check(inputs == {'scope_sha256': SCOPE_SHA, 'public_freeze_commit': args.freeze_commit,
                             'pinned_metadata_and_code': scope['pinned_metadata_and_code']}, 'Numerical input pins differ')
        expected_acquire_names = {'ACQUISITION_RESULT.json', 'INPUT_PINS.json', 'SOURCE_BODY_LEDGER.json'}
        expected_acquire_names.update(scan + '.compact.h5' for scan in SCANS)
        expected_acquire_names.update('raw_ranges/' + scan + '_row%02d.raw.bin' % row for scan in SCANS for row in range(16))
        check({p.relative_to(acquire).as_posix() for p in acquire.rglob('*') if p.is_file()} == expected_acquire_names,
              'Require exactly105 complete acquisition files with no failure or temporary output')
        expected_output_names = {'EXECUTION_RECEIPT.json', 'INPUT_PINS.json', 'NORMALIZATION.json',
                                 'DRIFT_CHECKPOINT.json', 'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json'}
        expected_output_names.update(scan + '_core128_all_carriers.npz' for scan in ONS)
        expected_output_names.update('profiles/' + scan + '_visit20170428_Sband_core128_rank_%02d.npz' % rank
                                     for scan in ONS for rank in (1, 2, 3))
        check({p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} == expected_output_names,
              'Require exactly18 complete search files with no failure or temporary output')
        check(acquisition['new_telescope_HTTP_requests'] == 69
              and acquisition['new_telescope_BODY_bytes'] == 214393415
              and acquisition['total_cumulative_telescope_HTTP_requests'] == 96
              and acquisition['cumulative_telescope_BODY_bytes'] == BODY_BYTES
              and acquisition['cumulative_reserved_BODY_upper_bound_bytes'] == RESERVED_BODY
              and acquisition['source_range_count_authenticated'] == 96
              and acquisition['reused_original_source_ranges'] == 27 and acquisition['repeated_source_GETs'] == 0
              and acquisition['standalone_durable_raw_range_files'] == 96
              and acquisition['complete_compact_files'] == 6 and acquisition['decoded_row_SHA256s'] == 96
              and acquisition['whole_original_telescope_MD5_verified'] is False
              and acquisition['source_workers_max'] == 6 and acquisition['HDF5_assembly_threads'] == 1
              and acquisition['write_decode_interleaving'] is False
              and acquisition['previous26_decoded_row_SHA256s_match'] is True
              and acquisition['source_worker_errors'] == [], 'Complete corrected acquisition accounting differs')
        ledger = read_json(acquire / 'SOURCE_BODY_LEDGER.json')
        for field, expected in (('new_requests_attempted', 69), ('new_BODY_bytes_received', 214393415),
            ('new_BODY_reserved_upper_bound_bytes', 214393484), ('original_requests_attempted', 27),
            ('original_BODY_bytes_received', 83845205), ('original_BODY_reserved_upper_bound_bytes', 83845232),
            ('cumulative_requests_attempted', 96), ('cumulative_BODY_bytes_received', BODY_BYTES),
            ('cumulative_BODY_reserved_upper_bound_bytes', RESERVED_BODY), ('BODY_cap_bytes', BODY_CAP), ('complete', True)):
            check(ledger[field] == expected, 'Corrected source BODY ledger differs: ' + field)
        check(ledger['completion_resource_guard'] == {'status': 'PASS_BEFORE_COMPLETE',
              **{key: acquisition[key] for key in ('process_CPU_seconds_including_imports', 'wall_seconds_including_imports', 'peak_RSS_bytes')}},
              'Completed source resource guard differs')
        old_requests, new_requests = original['value_read_requests'], acquisition['value_read_requests']
        old_keys = {(request['scan_id'], request['time_row']) for request in old_requests}
        new_keys = {(request['scan_id'], request['time_row']) for request in new_requests}
        check(len(old_requests) == len(old_keys) == 27 and len(new_requests) == len(new_keys) == 69
              and not old_keys.intersection(new_keys) and old_keys.union(new_keys) == set(descriptors),
              'Exactly27 prior and69 previously unattempted source requests required, with no repeat')
        check({tuple(key) for key in scope['reused_range_keys']} == old_keys
              and len(scope['reused_range_keys']) == 27
              and {tuple(key) for key in scope['unattempted_range_keys']} == new_keys
              and len(scope['unattempted_range_keys']) == 69, 'Request provenance differs from public frozen partition')
        check(sum(request['body_bytes_received'] for request in old_requests) == 83845205
              and sum(request['body_bytes_received'] for request in new_requests) == 214393415,
              'Exact received bytes in source request partition differ')
        request_map = {}
        for request in old_requests + new_requests:
            key = (request['scan_id'], request['time_row'])
            item, row = descriptors[key]
            response = request['response_headers']
            agent = 'SETI-S2017-frozen-midpoint-once/1' if key in old_keys else 'SETI-S2017-retained27-unattempted69-once/1'
            check(request['attempt'] == 1 and request['status'] == 'PASS_EXACT_SOURCE_RANGE'
                  and request['request_range'] == row['byte_range'] and request['expected_etag'] == item['etag']
                  and request['request_headers'] == {'Range': row['byte_range'], 'If-Match': item['etag'],
                      'Accept-Encoding': 'identity', 'User-Agent': agent}
                  and request['http_status'] == 206 and request['response_url'] == item['url']
                  and response['ETag'] == item['etag']
                  and response['Content-Range'] == f'bytes {row["byte_offset"]}-{row["byte_offset"]+row["stored_size"]-1}/{item["source_file_bytes"]}'
                  and response['Content-Length'] == str(row['stored_size'])
                  and (response.get('Content-Encoding') or 'identity').lower() == 'identity'
                  and request['body_bytes_received'] == row['stored_size']
                  and re.fullmatch('[0-9a-f]{64}', request['raw_sha256']), 'Actual physical source HTTP provenance differs')
            if 'compact_raw_roundtrip_sha256' in request:
                check(request['compact_raw_roundtrip_sha256'] == request['raw_sha256'], 'Prior raw roundtrip SHA differs')
            request_map[key] = request
        raw_records = acquisition['raw_range_records']
        check([(record['scan_id'], record['time_row']) for record in raw_records]
              == [(scan, row) for scan in SCANS for row in range(16)], 'Exactly96 durable raw range records required')
        indexed_old = {(entry['scan_id'], row['row']) for entry in inventory['records'] for row in entry['allocated_rows']}
        suffix_old = {(entry['scan_id'], entry['row']) for entry in inventory['unindexed_matching_source_bytes']}
        check(len(indexed_old) == 26 and len(suffix_old) == 1 and not indexed_old.intersection(suffix_old)
              and indexed_old.union(suffix_old) == old_keys, 'Prior indexed26 plus unindexed1 provenance differs')
        check([entry['scan_id'] for entry in inventory['records']] == list(SCANS), 'Preserved prior file scan order differs')
        for entry in inventory['records']:
            pin = prior_file_pins['analysis/new_visit_search/results/acquire/' + entry['scan_id'] + '.compact.h5']
            check(entry['file_sha256'] == pin['sha256'] and entry['file_bytes'] == pin['bytes']
                  and entry['shape'] == [16, 1, COUNT], 'Prior inventory file identity differs')
            for row in entry['allocated_rows']:
                key = (entry['scan_id'], row['row'])
                check(row['filter_mask'] == 0 and row['matches_received_SHA'] is True
                      and row['declared_decoded_row'] is True
                      and row['stored_bytes'] == descriptors[key][1]['stored_size']
                      and row['raw_sha256'] == request_map[key]['raw_sha256']
                      and 0 <= row['byte_offset'] <= entry['file_bytes'] - row['stored_bytes'],
                      'Prior indexed raw row provenance differs')
        for suffix in inventory['unindexed_matching_source_bytes']:
            key = (suffix['scan_id'], suffix['row'])
            pin = prior_file_pins['analysis/new_visit_search/results/acquire/' + suffix['scan_id'] + '.compact.h5']
            check(suffix['matches_exact_received_source_SHA256'] is True
                  and suffix['native_chunk_index_entry_present'] is False
                  and suffix['stored_size'] == descriptors[key][1]['stored_size']
                  and suffix['raw_sha256'] == request_map[key]['raw_sha256']
                  and 0 <= suffix['local_raw_byte_offset'] <= pin['bytes'] - suffix['stored_size'],
                  'Prior unindexed raw suffix provenance differs')
        check({(scan, row['time_row']) for scan, rows in original['decoded_row_progress'].items() for row in rows}
              == indexed_old, 'Exactly the26 original decoded rows must match preserved indexed source rows')
        raw_map = {}
        for record in raw_records:
            key = (record['scan_id'], record['time_row'])
            item, row = descriptors[key]
            expected_path = 'raw_ranges/' + record['scan_id'] + '_row%02d.raw.bin' % record['time_row']
            origin = ('REUSED_ORIGINAL_INDEXED_COMPACT_SOURCE_BYTES_NO_HTTP' if key in indexed_old else
                      'REUSED_ORIGINAL_UNINDEXED_EXACT_SOURCE_SUFFIX_NO_HTTP' if key in suffix_old else
                      'NEW_PREVIOUSLY_UNATTEMPTED_EXACT_SOURCE_RANGE')
            check(record['path'] == expected_path and record['stored_size'] == row['stored_size']
                  and record['filter_mask'] == 0 and record['original_source_chunk_origin'] == row['chunk_origin']
                  and record['source_range'] == row['byte_range'] and record['origin'] == origin
                  and record['fsync_before_HDF5'] is True
                  and record['raw_sha256'] == record['compact_raw_roundtrip_sha256'] == request_map[key]['raw_sha256'],
                  'Durable raw sidecar physical source identity differs')
            path = confined(acquire, record['path'])
            pin = {'sha256': digest(path), 'bytes': path.stat().st_size}
            check(pin == {'sha256': record['raw_sha256'], 'bytes': row['stored_size']}, 'Standalone raw source range bytes differ')
            pins[str(path.absolute())] = pin
            if key in new_keys:
                check(request_map[key]['standalone_raw_path'] == expected_path
                      and request_map[key]['standalone_raw_fsynced'] is True, 'New source durable receipt differs')
            raw_map[key] = record
            counts['durable_raw_sidecars'] += 1
        compact_records = acquisition['decoded_files']
        check([record['scan_id'] for record in compact_records] == list(SCANS), 'Six acquired compact identities required')
        check(acquisition['decoded_row_progress'] == {record['scan_id']: record['decoded_rows'] for record in compact_records},
              'Acquisition row progress differs from final compact record')
        check(result['acquisition_receipt_sha256'] == args.expected_acquisition_sha256
              and result['verified_inputs'] == [{'scan_id': record['scan_id'], 'file_sha256': record['file_sha256'],
                  'decoded_rows_verified': 16} for record in compact_records]
              and result['MJD_anchor'] == anchor and result['new_telescope_HTTP_requests'] == 0
              and result['new_telescope_BODY_bytes'] == 0, 'Search input identity/accounting differs')
        global np
        import numpy as np
        drift_grid, channels, offsets = np.linspace(-4.0, 4.0, 785), np.arange(FIRST, FIRST + CORE), np.arange(-64, 65)
        mismatch = float((drift_grid[1] - drift_grid[0]) * (np.arange(16) * TSAMP)[-1] / (2 * abs(DF)))
        check(mismatch <= .5 + 1e-12 and 2 * math.ceil(4 * 15 * TSAMP / abs(DF)) + 1 == len(drift_grid),
              'Frozen drift quantization/mismatch differs')
        shifts = np.rint(drift_grid[:, None] * (np.arange(16) * TSAMP)[None, :] / DF).astype(np.int64)
        check(int(np.abs(shifts).max()) + 1 <= HALO, 'Frozen width3 drift family exceeds retained crop halo')
        expected_summary = {'completed_ON_maps': 3, 'carriers_per_ON': CORE, 'drift_grid_count': 785,
            'widths_channels': [1, 3], 'half_grid_mismatch_channels': mismatch,
            'bandwidth_per_ON_hz': CORE * abs(DF), 'native_chunk_fraction_searched': CORE / COUNT,
            'reference_time': 'each ON first integration midpoint; six-scan profiles use actual header epochs',
            'score_definition': 'unchanged row-MAD-standardized odd-box track sum/sqrt(Nrow*width)',
            'normalization': 'unchanged each4096-carrier row core and501-channel filter'}
        check(result['search_summary'] == expected_summary, 'Complete search geometry/quantization summary differs')
        checkpoint = read_json(out / 'DRIFT_CHECKPOINT.json')
        check(set(checkpoint) == {'completed_ON_maps', 'expected_ON_maps', 'complete', 'receipts'}
              and checkpoint['completed_ON_maps'] == 3 and checkpoint['expected_ON_maps'] == 3
              and checkpoint['complete'] is True and [record['scan_id'] for record in checkpoint['receipts']] == list(ONS),
              'Three completed maps required')
        map_schema = {'frequency_hz_at_tref': ('<f8', (CORE,)), 'maximum_robust_box_track_score': ('<f8', (CORE,)),
            'winning_drift_hz_s': ('<f8', (CORE,)), 'winning_width_channels': ('<i2', (CORE,)),
            'valid_hypothesis_count': ('<i8', (CORE,)), 'source_reference_channels': ('<i8', (CORE,)),
            'drift_grid_hz_s': ('<f8', (785,))}
        saved = {}
        for record in checkpoint['receipts']:
            scan = record['scan_id']
            check(record['path'] == scan + '_core128_all_carriers.npz' and record['searched_carriers'] == CORE
                  and record['valid_hypotheses_per_carrier'] == 1570
                  and record['reference_channel_interval_half_open'] == [FIRST, FIRST + CORE], 'Map physical geometry differs')
            normalization = record['normalization']
            check(set(normalization) == {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}, 'Core normalization schema differs')
            same(np.asarray(normalization['normalization_source_channels']), channels, 'Core normalization physical indices differ')
            same(np.asarray(normalization['normalization_unmasked_counts']), np.full(16, CORE), 'Core normalization mask counts differ')
            for field in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                values = np.asarray(normalization[field])
                check(values.shape == (16,) and np.isfinite(values).all(), 'Core normalization row geometry differs')
                if field in ('row_power_median', 'row_residual_MAD_scale'):
                    check((values > 0).all(), 'Core normalization requires positive scale')
            map_normalizations[scan] = normalization
            m = npz(record)
            check(set(m) == set(map_schema), 'Saved map complete schema differs')
            for field, (dtype, shape) in map_schema.items():
                check(m[field].dtype == np.dtype(dtype) and m[field].shape == shape, 'Map precision/shape differs: ' + field)
                check(np.isfinite(m[field]).all(), 'Map contains nonfinite values: ' + field)
            same(m['source_reference_channels'], channels, 'Saved map source indices differ')
            same(m['frequency_hz_at_tref'], FCH1 + DF * channels, 'Negative-df physical frequency mapping differs')
            same(m['drift_grid_hz_s'], drift_grid, 'Saved drift grid differs')
            same(m['valid_hypothesis_count'], np.full(CORE, 1570), 'Map hypothesis coverage incomplete')
            check(np.isin(m['winning_drift_hz_s'], drift_grid).all()
                  and np.isin(m['winning_width_channels'], (1, 3)).all(), 'Map winner outside frozen grid/widths')
            saved[scan] = m
            counts['maps'] += 1
            counts['map_normalization_records'] += 1
            counts['carrier_maximum_records'] += CORE
            counts['valid_hypothesis_records'] += int(m['valid_hypothesis_count'].sum())
        tops = read_json(out / 'DRIFT_TOP20.json')
        check(set(tops) == set(ONS), 'Top20 scan inventory differs')
        for scan in ONS:
            m, chosen = saved[scan], []
            for index in np.lexsort((channels, -m['maximum_robust_box_track_score'])):
                j = int(index)
                if all(abs(int(channels[j]) - int(channels[k])) > 3 for k in chosen):
                    chosen.append(j)
                if len(chosen) == 20:
                    break
            expected = [{'track_id': scan + '_visit20170428_Sband_core128_rank_%02d' % rank,
                'family': 'S2017_native_midpoint_fixed_core128', 'originating_scan': scan, 'originating_role': 'ON',
                'display_rank': rank, 'source_reference_channel': int(channels[j]),
                'reference_frequency_hz': float(m['frequency_hz_at_tref'][j]),
                'reference_seconds_from_anchor': float((headers[scan]['tstart'] - anchor) * 86400 + .5 * TSAMP),
                'drift_hz_s': float(m['winning_drift_hz_s'][j]), 'width_channels': int(m['winning_width_channels'][j]),
                'maximum_robust_box_track_score': float(m['maximum_robust_box_track_score'][j]),
                'reference_core_tile': 0, 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'} for rank, j in enumerate(chosen, 1)]
            check(len(expected) == 20 and tops[scan] == expected, 'Saved top20 rank/tie/suppression arithmetic differs')
            counts['top20_entries'] += 20
        fullnorm = read_json(out / 'NORMALIZATION.json')
        check(set(fullnorm) == {'source_channel0', 'count', 'row_power_medians', 'method', 'raw_dtype'}
              and fullnorm['source_channel0'] == C0 and fullnorm['count'] == COUNT
              and fullnorm['method'] == FULLNORM and fullnorm['raw_dtype'] == '<f4'
              and set(fullnorm['row_power_medians']) == set(SCANS), 'Full native normalization frame differs')
        rowmedians = np.asarray([fullnorm['row_power_medians'][scan] for scan in SCANS])
        check(rowmedians.shape == (6, 16) and np.isfinite(rowmedians).all() and (rowmedians > 0).all(), 'Invalid native row medians')
        expected_profile_summary = {'profile_count': 9, 'plot_count': 0, 'all_rows_retained': 16,
            'source_top20_sha256': pins[str((out / 'DRIFT_TOP20.json').absolute())]['sha256'],
            'saved_normalization_sha256': pins[str((out / 'NORMALIZATION.json').absolute())]['sha256'],
            'shift_frequency_drift_width_optimization_applied': False,
            'raw_patch_alignment': 'rounded absolute source channels along exact fixed selected track in each actual scan',
            'time_profile_units': 'width-mean raw power/full-chunk row median minus fixed flank median',
            'mean_profile_units': 'mean track-aligned row-normalized power minus each row fixed flank median'}
        check(result['fixed_profile_summary'] == expected_profile_summary, 'Fixed-profile summary/source hash differs')
        records = read_json(out / 'FIXED_TOP3_PROFILES.json')
        check(len(records) == 9 and [record['selected_track'] for record in records]
              == [track for scan in ONS for track in tops[scan][:3]], 'Exact top3 fixed profile selections differ')
        patch_schema = {'raw_power': ('<f4', (6, 16, 129)), 'row_normalized_power': ('<f8', (6, 16, 129)),
            'saved_full_chunk_row_medians': ('<f8', (6, 16)), 'frozen_source_channel_centers': ('<i8', (6, 16)),
            'source_channel_offsets': ('<i8', (129,)), 'times_seconds_from_reference': ('<f8', (6, 16)),
            'center_row_normalized_power': ('<f8', (6, 16)), 'fixed_flank_median_row_normalized_power': ('<f8', (6, 16)),
            'center_minus_flank_each_row': ('<f8', (6, 16)), 'mean_fixed_track_frequency_profile': ('<f8', (6, 129)),
            'scans': ('<U10', (6,)), 'df_hz': ('<f8', ()), 'source_channel0': ('<i8', ()),
            'reference_frequency_hz': ('<f8', ()), 'drift_hz_s': ('<f8', ()), 'width_channels': ('<i8', ()),
            'fixed_source_channel_shift': ('<i8', ())}
        for record in records:
            track = record['selected_track']
            check(record['patch']['path'] == 'profiles/' + track['track_id'] + '.npz', 'Fixed patch identity differs')
            a = npz(record['patch'])
            check(set(a) == set(patch_schema), 'Saved patch complete17-field schema differs')
            for field, (dtype, shape) in patch_schema.items():
                check(a[field].dtype == np.dtype(dtype) and a[field].shape == shape, 'Patch precision/shape differs: ' + field)
            raw = a['raw_power']
            check(np.isfinite(raw).all() and (raw >= 0).all(), 'Raw patch must be finite nonnegative float32')
            same(a['scans'], np.asarray(SCANS), 'Patch scan order differs')
            same(a['source_channel_offsets'], offsets, 'Patch fixed offsets differ')
            same(a['saved_full_chunk_row_medians'], rowmedians, 'Patch native row medians differ')
            for field, expected in (('df_hz', DF), ('source_channel0', C0), ('reference_frequency_hz', track['reference_frequency_hz']),
                ('drift_hz_s', track['drift_hz_s']), ('width_channels', track['width_channels']), ('fixed_source_channel_shift', 0)):
                check(a[field].item() == expected, 'Patch frozen track scalar differs: ' + field)
            dt = np.asarray([(headers[scan]['tstart'] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                             - track['reference_seconds_from_anchor'] for scan in SCANS])
            centers = np.rint((track['reference_frequency_hz'] - FCH1) / DF + track['drift_hz_s'] * dt / DF).astype(np.int64)
            same(a['times_seconds_from_reference'], dt, 'Patch actual-header time coordinates differ')
            same(a['frozen_source_channel_centers'], centers, 'Patch absolute np.rint physical centers differ')
            indices = centers[:, :, None] - C0 + offsets
            check(indices.min() >= 0 and indices.max() < COUNT, 'Fixed patch outside retained native chunk')
            normalized = raw.astype(np.float64) / rowmedians[:, :, None]
            baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
            radius = track['width_channels'] // 2
            center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
            residual = center - baseline
            mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
            for field, expected in (('row_normalized_power', normalized), ('fixed_flank_median_row_normalized_power', baseline),
                ('center_row_normalized_power', center), ('center_minus_flank_each_row', residual), ('mean_fixed_track_frequency_profile', mean_profile)):
                same(a[field], expected, 'Saved patch arithmetic differs: ' + field)
            check(record['fixed_frequency_shift_channels'] == 0
                  and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                  and record['fixed_flank_offsets'] == 'absolute channel offset > 3 within +/-64'
                  and len(record['scan_profiles']) == 6, 'Fixed descriptive profile contract differs')
            for i, profile in enumerate(record['scan_profiles']):
                expected = {'scan_id': SCANS[i], 'mean_center_minus_flank': float(residual[i].mean()),
                    'median_center_minus_flank': float(np.median(residual[i])), 'positive_rows': int(np.count_nonzero(residual[i] > 0)),
                    'first_eight_mean_center_minus_flank': float(residual[i, :8].mean()),
                    'last_eight_mean_center_minus_flank': float(residual[i, 8:].mean()),
                    'all_16_center_minus_flank_rows': residual[i].tolist(),
                    'all_16_raw_width_mean_power': raw[i, :, 64-radius:65+radius].mean(axis=1).tolist(),
                    'frozen_source_channel_centers': centers[i].tolist()}
                check(profile == expected, 'Saved all-row per-scan profile arithmetic differs')
            buffers.append({'raw': raw, 'indices': indices, 'filled': np.zeros(raw.shape, dtype=bool)})
            counts['patches'] += 1
            counts['scan_profiles'] += 6
            counts['time_row_occurrences'] += 96
            counts['retained_raw_patch_cells'] += raw.size
        print('PASS_SAVED_S2017_MAPS_AND_FIXED_PROFILE_ARITHMETIC', flush=True)
        import h5py
        import hdf5plugin
        hdf5plugin.register(filters='bshuf', force=True)
        check(h5py.version.hdf5_version == scope['hdf5_version']
              and h5py.h5z.filter_avail(32008)
              and h5py.h5z.get_filter_info(32008) & h5py.h5z.FILTER_CONFIG_DECODE_ENABLED,
              'Pinned native decoder unavailable')
        versions = {package: importlib.metadata.version(package) for package in scope['runtime_package_versions']}
        versions['HDF5'] = h5py.version.hdf5_version
        check(acquisition['runtime_versions'] == versions and result['runtime_versions'] == versions, 'Execution runtime binding differs')
        pipelines = acquisition['local_pipeline_records']
        check(len(pipelines) == 6 and set(record['scan_id'] for record in pipelines) == set(SCANS), 'Six local pipeline records required')
        for record in compact_records:
            scan = record['scan_id']
            check(record['array_file'] == scan + '.compact.h5' and record['shape'] == [16, 1, COUNT]
                  and record['source_channel0'] == C0 and [row['time_row'] for row in record['decoded_rows']] == list(range(16)),
                  'Exact native compact record geometry differs')
            path = confined(acquire, record['array_file'])
            pin = {'sha256': digest(path), 'bytes': path.stat().st_size}
            check(pin == {'sha256': record['file_sha256'], 'bytes': record['bytes']}, 'Acquired compact file bytes differ')
            pins[str(path.absolute())] = pin
            item = next(item for item in items if item['label'] == scan)
            pipeline = next(p for p in pipelines if p['scan_id'] == scan)
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                check(set(handle.keys()) == {'data'}, 'Compact dataset inventory differs')
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4') and data.chunks == (1, 1, COUNT)
                      and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                      and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'],
                      'Compact physical source identity differs')
                properties = data.id.get_create_plist()
                check(properties.get_nfilters() == 1 and data.id.get_num_chunks() == 16, 'Compact allocated/filter inventory differs')
                actual = properties.get_filter(0)
                actual_filter = [actual[0], actual[1], list(actual[2]), actual[3].decode('utf8', 'replace')]
                original_filter = item['current_header']['hdf5_filters'][0]
                check(pipeline == {'scan_id': scan, 'original_filter': original_filter, 'current_filter': actual_filter,
                    'prefix_identity_claim': False, 'semantic_parameters_preserved': True}
                    and actual[0] == original_filter[0] and actual[1] == original_filter[1] and list(actual[2][2:]) == original_filter[2][2:],
                    'Current/original filter semantics differ')
                for i in range(16):
                    mask, compressed = data.id.read_direct_chunk((i, 0, 0))
                    request = request_map[(scan, i)]
                    check(mask == 0 and len(compressed) == descriptors[(scan, i)][1]['stored_size']
                          and hashlib.sha256(compressed).hexdigest() == request['raw_sha256'] == raw_map[(scan, i)]['compact_raw_roundtrip_sha256'],
                          'Retained raw compressed chunk differs from exact physical source range')
                    counts['compressed_source_chunks'] += 1
                power = data[:, 0, :]
            check(power.shape == (16, COUNT) and power.dtype == np.dtype('<f4')
                  and np.isfinite(power).all() and (power >= 0).all(), 'Native decoded power invalid')
            for i, row in enumerate(record['decoded_rows']):
                check(row['decoded_bytes'] == COUNT * 4
                      and hashlib.sha256(power[i].tobytes(order='C')).hexdigest() == row['decoded_sha256'], 'Decoded native row SHA256 differs')
                counts['decoded_rows'] += 1
                prior_rows = {entry['time_row']: entry for entry in original['decoded_row_progress'][scan]}
                if i in prior_rows:
                    check(row == prior_rows[i], 'Previously authenticated decoded row changed')
                    counts['preserved_prior_decoded_rows_matched'] += 1
            si = SCANS.index(scan)
            # Float32 median is computed before promotion, exactly as the frozen driver.
            same(np.median(power, axis=1).astype(np.float64), rowmedians[si], 'Full native float32 row median differs')
            counts['native_row_medians_recomputed'] += 16
            if scan in ONS:
                same(np.median(power[:, Q * CORE:(Q + 1) * CORE].astype(np.float64), axis=1),
                     np.asarray(map_normalizations[scan]['row_power_median']), 'ON core float64 row median differs')
                counts['ON_core_row_medians_recomputed'] += 16
            for buffer in buffers:
                indices = buffer['indices'][si]
                observed = power[np.arange(16)[:, None], indices]
                retained = buffer['raw'][si]
                check(not buffer['filled'][si].any(), 'Source occurrence authenticated twice')
                check(np.array_equal(observed.view(np.uint32), retained.view(np.uint32)),
                      'Saved raw patch differs bitwise from its physical native source cells')
                buffer['filled'][si] = True
                counts['raw_cells_bitwise_checked'] += observed.size
            del power, compressed
            counts['compact_files'] += 1
            print('AUTHENTICATED_S2017_SOURCE', scan, flush=True)
        check(all(buffer['filled'].all() for buffer in buffers) and counts == EXPECTED_COUNTS,
              'Saved/source QA inventory incomplete: ' + str(counts))
        for name, pin in pins.items():
            path = Path(name)
            check(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during QA: ' + name)
        check(digest(own_path) == own_sha, 'QA code changed during execution')
        measured = use(started)
        check(0 < measured['process_CPU_seconds_including_imports'] <= CPU_CAP
              and 0 < measured['wall_seconds_including_imports'] <= WALL_CAP and 0 < measured['peak_RSS_bytes'] <= RAM_CAP,
              'QA resource cap exceeded')
        receipt = {'schema': 'SETI_S2017_SAVED_OUTPUT_AND_SOURCE_QA_V1',
            'status': 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS',
            'scope_sha256': SCOPE_SHA, 'driver_sha256': DRIVER_SHA, 'public_freeze_commit': args.freeze_commit,
            'qa_script_sha256': own_sha, 'acquisition_receipt_sha256': args.expected_acquisition_sha256,
            'search_receipt_sha256': args.expected_search_sha256, 'measurement_stage': STAGE,
            'original_scope_sha256': BASE_SCOPE_SHA, 'original_driver_sha256': BASE_DRIVER_SHA,
            'preserved_original_failure_sha256': ORIGINAL_FAILURE_SHA,
            'source_request_partition': {'original_received_reused': 27, 'new_previously_unattempted': 69, 'cumulative': 96},
            'counts': counts, 'all_input_byte_pins': pins, 'runtime_versions': versions,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, **measured,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'detector_or_score_rerun': False, 'fixed_track_optimization_applied': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'qualified_sky_detection': False,
            'OFF_veto_applied': False, 'calibrated_SNR_FAP': False,
            'limitations': ['Checks saved maxima geometry, ranks, physical source cells and fixed-profile arithmetic; does not recompute detector scores or winning hypotheses.',
                'Core row medians are recomputed; remaining saved detector normalization statistics are hash-bound and schema-checked, not independently refiltered.',
                'One historical2017 S-band visit with three ON/OFF pairs, not three independent visits or a same-frequency replication of2016 L-band cases.',
                'Exploratory scores and descriptive OFF profiles carry no calibrated sky detection, sensitivity or false-alarm inference.']}
        save_new(review / 'QA_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'counts': counts, **measured}), flush=True)
    except BaseException as error:
        save_new(review / 'FAILURE_RECEIPT.json', {'schema': 'SETI_S2017_SAVED_OUTPUT_AND_SOURCE_QA_V1',
            'status': 'INCOMPLETE_QA_PRESERVE_OUTPUTS_NO_RERUN', 'error_type': type(error).__name__, 'error': str(error),
            'scope_sha256': SCOPE_SHA, 'driver_sha256': DRIVER_SHA, 'public_freeze_commit': args.freeze_commit,
            'qa_script_sha256': own_sha, 'acquisition_receipt_sha256': args.expected_acquisition_sha256,
            'search_receipt_sha256': args.expected_search_sha256, 'counts': counts, 'all_input_byte_pins': pins,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, **use(started),
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'detector_or_score_rerun': False})
        raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:
            lock_handle.close()


if __name__ == '__main__':
    main()
