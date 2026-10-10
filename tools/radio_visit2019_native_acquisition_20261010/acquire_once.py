"""One frozen exact native payload pass, durable compressed rows, no signal decode.

No HEAD, metadata follow-up, index traversal, redirect, retry, resume, or signal
value API exists in this runner. Only explicit root exploratory source-value GO
after frozen qualification/descriptors/protection permits payload HTTP.
"""
import time
STARTED = time.monotonic()
import argparse
import datetime
import fcntl
import hashlib
import http.client
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import types
import urllib.error
import urllib.request
# Pin the shared executable source before its first import. This preflight uses
# standard-library bytes only and permits neither check-only imports nor replay.
_boot_root = Path(__file__).resolve().parents[2]
_boot_family = 'radio_visit2019_native_acquisition_20261010'
_boot_scope_path = _boot_root / 'tools' / _boot_family / 'scope.json'
if '--root-go-exploratory-source-values' not in sys.argv:
    raise ValueError('Explicit root exploratory GO required before shared source import')
if os.environ.get('PYTHONPATH') != str(_boot_root.parent / 'seti_fullpower_work/deps') or os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
    raise ValueError('Exact own dependency path and disabled bytecode writes required')
_boot_expected = sys.argv[sys.argv.index('--expected-scope-sha256') + 1]
if _boot_scope_path.stat().st_size > 16777216:
    raise ValueError('Scope exceeds finite pre-import cap')
_boot_raw = _boot_scope_path.read_bytes()
if hashlib.sha256(_boot_raw).hexdigest() != _boot_expected:
    raise ValueError('Scope byte pin differs before shared source import')
_boot_scope = json.loads(_boot_raw)
_boot_common = _boot_scope['common_pin']
_boot_common_path = _boot_root / 'tools' / _boot_family / 'common.py'
if _boot_common['path'] != str(_boot_common_path.relative_to(_boot_root)) or _boot_common_path.is_symlink() or _boot_common_path.stat().st_size != _boot_common['bytes'] or _boot_common['bytes'] > 1048576:
    raise ValueError('Shared source byte pin differs before import')
_boot_common_raw = _boot_common_path.read_bytes()
if len(_boot_common_raw) != _boot_common['bytes'] or hashlib.sha256(_boot_common_raw).hexdigest() != _boot_common['sha256']:
    raise ValueError('Shared source byte pin differs before import')
_boot_common_module = types.ModuleType('common')
_boot_common_module.__file__ = str(_boot_common_path)
sys.modules['common'] = _boot_common_module
exec(compile(_boot_common_raw, str(_boot_common_path), 'exec'), _boot_common_module.__dict__)
from common import (ROOT, FAMILY, TOOLS, RESULTS, PRIVATE, DEPS, SHARED_ROOTS, LIMITS,
                    SOURCES, BASE_URL, MIDPOINT_RULE, require, sha, digest, relative,
                    pin, read_pin, read_json, fsync_dir, save, allocated_bytes,
                    output_bytes, exact_environment)

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        raise ValueError('Redirect forbidden; source request consumed, no retry')


def usage():
    value = {'process_CPU_seconds_including_imports': time.process_time(),
             'wall_seconds_since_module_start': time.monotonic() - STARTED,
             'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(value['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and value['wall_seconds_since_module_start'] <= LIMITS['wall_seconds']
            and value['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Measured child resource cap exceeded')
    return value


def interval(value):
    require(isinstance(value, list) and len(value) == 2 and all(type(x) is int for x in value)
            and 0 <= value[0] < value[1], 'Bad half-open source interval')
    return value


def overlap(first, second):
    return first[0] < second[1] and second[0] < first[1]


def contract(scope, args):
    require(scope.get('schema') == 'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_SCOPE_V1'
            and scope.get('limits') == LIMITS and scope.get('shared_workspace_roots') == SHARED_ROOTS,
            'Acquisition schema/limits/shared roots differ')
    require(scope['output_directory'] == RESULTS + '/acquire_once'
            and scope['source_workers_max'] == 1 and scope['signal_decode_authorized'] is False
            and scope['retry_resume_or_rerun_authorized'] is False
            and scope['independent_validation_admission'] == 'BLOCKED'
            and scope['original_A_B_status'] == 'FAIL_CLOSED'
            and scope['runtime_package_versions'] == {'h5py': '3.15.1', 'hdf5plugin': '7.1.0'},
            'Execution contract differs')
    own = pin(Path(__file__).resolve())
    require(own == scope['worker_pin'] and own['sha256'] == args.expected_worker_sha256,
            'Worker source changed')
    require(scope['launcher_pin']['path'] == TOOLS + '/launch_once.py'
            and scope['common_pin']['path'] == TOOLS + '/common.py', 'Source namespace differs')
    for key in ('launcher_pin', 'common_pin'):
        read_pin(scope[key])
    qualification = read_json(scope['qualified_metadata_pin'])
    require(qualification.get('schema') == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and qualification.get('status') == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and qualification['metadata_eligibility']['status'] == qualification['status']
            and all(check['PASS'] is True for check in qualification['metadata_eligibility']['checks'])
            and qualification['spectral_values_read'] is False
            and qualification['dataset_value_API_used'] is False
            and qualification['independent_validation_admission'] == 'BLOCKED',
            'Clean exact actual six-source qualification required')
    qualified_execution = read_json(scope['qualified_execution_pin'])
    require(qualified_execution.get('schema') == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1'
            and qualified_execution.get('status') == 'COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION'
            and qualified_execution['metadata_eligibility_status'] == qualification['status']
            and qualified_execution['METADATA_QUALIFICATION_RESULT_sha256'] == scope['qualified_metadata_pin']['sha256']
            and qualified_execution['scope_sha256'] == qualification['scope_sha256']
            and qualified_execution['script_sha256'] == qualification['script_sha256']
            and qualified_execution['public_freeze_commit'] == qualification['public_freeze_commit']
            and qualified_execution['resource_caps_satisfied'] is True
            and qualified_execution['all_input_end_readbacks_exact'] is True
            and qualified_execution['HTTP_requests'] == 0
            and qualified_execution['spectral_values_read'] is False
            and qualified_execution['dataset_value_API_used'] is False,
            'Closed exact qualification execution/resource/end-readback proof required')
    descriptors = read_json(scope['descriptor_manifest_pin'])
    require(descriptors.get('schema') == 'SETI_VISIT2019_ONE_NATIVE_RAW_DESCRIPTOR_MANIFEST_V1'
            and descriptors.get('status') == 'PASS_CLEAN_EXACT_SIX_NATIVE_ROW_DESCRIPTORS_METADATA_ONLY'
            and descriptors['qualification_result_pin'] == scope['qualified_metadata_pin']
            and descriptors['spectral_values_read'] is False and descriptors['spectral_payload_fetched'] is False
            and descriptors['fixed_midpoint_rule'] == MIDPOINT_RULE,
            'Clean typed TREE1 descriptors bound to qualified six required')
    require(isinstance(descriptors['typed_index_evidence_pins'], list)
            and 0 < len(descriptors['typed_index_evidence_pins']) <= 1024, 'Finite typed evidence pins required')
    for evidence in descriptors['typed_index_evidence_pins']:
        read_pin(evidence)
    prior = read_json(scope['prior_source_attempts_pin'])
    require(prior.get('schema') == 'SETI_VISIT2019_PRIOR_SOURCE_RANGE_ATTEMPTS_V1'
            and prior.get('status') == 'PASS_COMPLETE_KNOWN_REQUEST_HISTORY_NO_REPLAY',
            'Frozen complete known prior attempt inventory required')
    protection = read_json(scope['protected_frames_pin'])
    require(protection.get('schema') == 'SETI_VISIT2019_PROTECTED_KNOWN_FRAMES_DISJOINT_V1'
            and protection.get('status') == 'PASS_PROTECTED_KNOWN_FRAMES_DISJOINT'
            and protection['descriptor_manifest_pin'] == scope['descriptor_manifest_pin']
            and protection['qualified_metadata_pin'] == scope['qualified_metadata_pin']
            and protection['original_A_B_status'] == 'FAIL_CLOSED'
            and protection['independent_validation_admission'] == 'BLOCKED',
            'Exact protected known frames disjoint proof required')
    sources, headers = descriptors['sources'], qualification['sources']
    require(len(sources) == len(headers) == 6 and len(prior['sources']) == 6, 'Exact six sources required')
    total, request_count, frames, grid = 0, 0, [], None
    for index, (identity, source, header, old) in enumerate(zip(SOURCES, sources, headers, prior['sources']), 1):
        source_id, name, filename = identity
        url = BASE_URL + filename
        require(all(record['source_id'] == source_id and record['url'] == url
                    and record['ordered_index'] == index for record in (source, header, old)), 'Exact six identity/order differs')
        require(header['status'] == 'COMPLETE_HEADER_METADATA_ONLY'
                and header['data_attributes']['source_name'] == name
                and header['dtype_string'] == '<f4' and header['dtype_itemsize_bytes'] == 4,
                'Actual dtype/source name not qualified')
        shape, chunks = header['shape'], header['chunks']
        require(len(shape) == len(chunks) == 3 and all(type(x) is int and x > 0 for x in shape + chunks)
                and shape[1] == chunks[0] == chunks[1] == 1 and chunks[2] <= shape[2], 'Actual shape/chunks differ')
        ntime, nchan, width = shape[0], shape[2], chunks[2]
        count = (nchan + width - 1) // width
        ordinal, c0 = count // 2, (count // 2) * width
        midpoint = {'native_ordinal_zero_based': ordinal, 'absolute_channel_start': c0,
                    'channel_count': min(width, nchan - c0)}
        require(midpoint['channel_count'] == width and header['metadata_derived_midpoint'] == midpoint
                and header['fixed_midpoint_rule'] == MIDPOINT_RULE
                and header['native_chunks_along_frequency'] == count,
                'Frozen full native midpoint differs; partial edge native unsupported')
        current_grid = {key: header[key] for key in ('shape', 'dtype_string', 'chunks', 'creation_filters')}
        current_grid['frequency_time'] = {key: header['data_attributes'][key] for key in ('fch1', 'foff', 'tsamp')}
        require(grid is None or current_grid == grid, 'Actual six grids differ')
        grid = current_grid
        for group in ('root', 'data'):
            attrs, types = header[group + '_attributes'], header[group + '_attribute_types']
            require(isinstance(attrs, dict) and isinstance(types, dict) and set(attrs) == set(types), 'Exact attribute type/value bijection required')
            for key, record in types.items():
                encoded = bytes.fromhex(record['hdf5_type_encoded_hex'])
                require(len(encoded) == record['hdf5_type_encoded_bytes'] <= 65536
                        and sha(encoded) == record['hdf5_type_encoded_sha256']
                        and isinstance(record['shape'], list) and len(record['shape']) <= 3
                        and all(type(x) is int and x > 0 for x in record['shape']), 'Exact finite attribute datatype encoding differs')
        size, etag = header['source_file_bytes'], header['etag']
        require(type(size) is int and size > 0 and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', etag)
                and source['source_file_bytes'] == old['source_file_bytes'] == size
                and source['etag'] == old['etag'] == etag, 'Exact HEAD size/strong ETag differs')
        require(source['status'] == 'COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION'
                and len(source['descriptors']) == ntime
                and [row['time_row'] for row in source['descriptors']] == list(range(ntime)), 'All actual time row descriptors required')
        old_ranges = [interval(value) for value in old['attempted_ranges_half_open']]
        new_ranges = []
        for row in source['descriptors']:
            offset, stored, mask = row['file_offset'], row['size'], row['filter_mask']
            require(type(offset) is int and type(stored) is int and 0 < stored <= LIMITS['payload_BODY_bytes']
                    and 0 <= offset <= size - stored and type(mask) is int
                    and 0 <= mask < (1 << len(header['creation_filters']))
                    and row['coordinates'] == [row['time_row'], 0, c0, 0]
                    and row['source_channel_start'] == c0 and row['logical_channel_count'] == width
                    and row['decoded_full_chunk_bytes'] == 4 * width
                    and row['payload_pointer_followed'] is False and row['HTTP_authorized'] is False
                    and row['typed_leaf_pointer_evidence'] and row['metadata_traversal'],
                    'Actual typed row descriptor origin/range/filter mask differs')
            span = [offset, offset + stored]
            require(all(not overlap(span, previous) for previous in old_ranges + new_ranges), 'Prior/new payload range overlaps or replay')
            new_ranges.append(span)
            total += stored
            request_count += 1
        frames.append({'source_id': source_id, 'url': url, 'source_channel_interval_half_open': [c0, c0 + width],
                       'source_ranges_half_open': new_ranges})
    require(protection['acquisition_frames'] == frames, 'Protection proof source/channel/range frame differs')
    for known in protection['known_frames']:
        span = interval(known['source_channel_interval_half_open'])
        require(all(frame['url'] != known['url'] or not overlap(frame['source_channel_interval_half_open'], span)
                    for frame in frames), 'Protected known source-channel frame overlaps')
    require(0 < total == scope['exact_expected_payload_BODY_bytes'] <= LIMITS['payload_BODY_bytes']
            and request_count == scope['payload_HTTP_request_cap']
            and scope['output_cap_bytes'] == 2 * total + 67108864, 'Exact finite BODY/output reservation differs')
    admission = json.loads(read_pin({'path': str(Path(args.root_admission).relative_to(ROOT)),
                                   'bytes': Path(args.root_admission).stat().st_size,
                                   'sha256': args.expected_root_admission_sha256}))
    require(admission.get('schema') == 'SETI_VISIT2019_ONE_NATIVE_RAW_ROOT_ADMISSION_V1'
            and admission.get('status') == 'PASS_FROZEN_ONE_NATIVE_EXPLORATORY_SOURCE_VALUES_GO'
            and admission['scope_sha256'] == args.expected_scope_sha256
            and admission['worker_sha256'] == args.expected_worker_sha256
            and admission['launcher_sha256'] == scope['launcher_pin']['sha256']
            and admission['public_freeze_commit'] == args.public_freeze_commit
            and admission['exploratory_source_values_GO'] is True
            and admission['protected_known_frames_disjoint'] is True
            and admission['prior_source_attempts_complete'] is True
            and admission['new_payload_BODY_reserved_bytes'] == total
            and admission['new_payload_HTTP_request_cap'] == request_count
            and admission['independent_validation_admission'] == 'BLOCKED'
            and admission['original_A_B_status'] == 'FAIL_CLOSED', 'Exact root exploratory acquisition admission required')
    review = read_json(admission['source_only_peer_receipt_pin'])
    require(review.get('status') == 'PASS_SOURCE_ONLY_NO_HTTP_HDF5_ARRAYS_OR_VALUES'
            and review['scope_sha256'] == args.expected_scope_sha256
            and review['worker_pin'] == scope['worker_pin'] and review['launcher_pin'] == scope['launcher_pin']
            and review['common_pin'] == scope['common_pin'], 'Exact frozen source-only review binding required')
    return qualification, descriptors, admission


def make_compact(out, source, header, raw_rows, scope):
    # This is the first native-library import. Every descriptor and gate is already frozen.
    import h5py
    import hdf5plugin
    import numpy as np
    require(importlib.metadata.version('h5py') == '3.15.1'
            and importlib.metadata.version('hdf5plugin') == '7.1.0', 'Runtime packages differ')
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'Frozen HDF5 runtime differs')
    width, ntime = header['chunks'][2], header['shape'][0]
    c0 = header['metadata_derived_midpoint']['absolute_channel_start']
    path = out / (source['source_id'] + '.compact.h5')

    def attribute(owner, name, value, record):
        type_id = h5py.h5t.decode(bytes.fromhex(record['hdf5_type_encoded_hex']))
        space = h5py.h5s.create(h5py.h5s.SCALAR) if not record['shape'] else h5py.h5s.create_simple(tuple(record['shape']))
        attr = None
        try:
            dtype = type_id.dtype
            string = h5py.check_string_dtype(dtype)
            if string is not None:
                values = np.asarray(value, dtype=object)
                converted = [str(item) if string.length is None and string.encoding == 'utf-8'
                             else str(item).encode('utf-8') for item in values.reshape(-1)]
                array = np.asarray(converted, dtype=dtype).reshape(tuple(record['shape']))
            else:
                array = np.asarray(value, dtype=dtype).reshape(tuple(record['shape']))
            attr = h5py.h5a.create(owner.id, name.encode('utf-8'), type_id, space)
            attr.write(array)
            actual_type = attr.get_type()
            try:
                require(actual_type.encode() == type_id.encode(), 'Compact attribute datatype changed')
            finally:
                actual_type.close()
        finally:
            if attr is not None:
                attr.close()
            space.close()
            type_id.close()

    with h5py.File(path, 'x', rdcc_nbytes=0) as handle:
        for name, value in header['root_attributes'].items():
            attribute(handle, name, value, header['root_attribute_types'][name])
        space = h5py.h5s.create_simple((ntime, 1, width))
        creation = h5py.h5p.create(h5py.h5p.DATASET_CREATE)
        datatype = h5py.h5t.IEEE_F32LE.copy()
        try:
            creation.set_chunk((1, 1, width))
            for filter_record in header['creation_filters']:
                creation.set_filter(filter_record[0], filter_record[1], tuple(filter_record[2]))
            identifier = h5py.h5d.create(handle.id, b'data', datatype, space, dcpl=creation)
            data = h5py.Dataset(identifier)
        finally:
            datatype.close()
            creation.close()
            space.close()
        actual = data.id.get_create_plist()
        try:
            pipeline = [list(actual.get_filter(i)[:3]) for i in range(actual.get_nfilters())]
            expected = [[row[0], row[1], tuple(row[2])] for row in header['creation_filters']]
            require(pipeline == expected, 'Compact creation filter pipeline changed')
        finally:
            actual.close()
        shifted = dict(header['data_attributes'])
        shifted['fch1'] = shifted['fch1'] + c0 * shifted['foff']
        shifted['nchans'] = width
        for name, value in shifted.items():
            attribute(data, name, value, header['data_attribute_types'][name])
        provenance = {'original_source_url': source['url'], 'original_source_etag': source['etag'],
                      'original_source_frequency_chunk_origin': c0,
                      'original_source_native_ordinal': header['metadata_derived_midpoint']['native_ordinal_zero_based'],
                      'original_source_file_bytes': source['source_file_bytes']}
        require(not set(provenance).intersection(shifted), 'Original attribute collides with compact provenance')
        for name, value in provenance.items():
            data.attrs[name] = value
        for record in raw_rows:
            raw_path = out / record['path']
            raw = raw_path.read_bytes()
            require(len(raw) == record['bytes'] and sha(raw) == record['sha256'], 'Durable compressed source row changed')
            data.id.write_direct_chunk((record['time_row'], 0, 0), raw, filter_mask=record['filter_mask'])
            del raw
        handle.flush()
    with path.open('rb') as handle:
        os.fsync(handle.fileno())
    fsync_dir(path.parent)
    # Raw-only roundtrip never invokes a codec or a dataset value API.
    with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
        data = handle['data']
        require(data.shape == (ntime, 1, width) and data.dtype.str == '<f4', 'Compact geometry/dtype changed')
        for record in raw_rows:
            mask, raw = data.id.read_direct_chunk((record['time_row'], 0, 0))
            require(mask == record['filter_mask'] and len(raw) == record['bytes']
                    and sha(raw) == record['sha256'], 'Compact raw compressed-row roundtrip changed')
            del raw
    return {'source_id': source['source_id'], 'ordered_index': source['ordered_index'],
            'path': path.relative_to(out).as_posix(), 'pin': pin(path), 'shape': [ntime, 1, width],
            'dtype_string': '<f4', 'source_channel0': c0,
            'native_ordinal_zero_based': header['metadata_derived_midpoint']['native_ordinal_zero_based'],
            'source_url': source['url'], 'source_etag': source['etag'],
            'source_file_bytes': source['source_file_bytes'], 'raw_rows': raw_rows,
            'original_metadata': {'root_attributes': header['root_attributes'], 'data_attributes': header['data_attributes'],
                                  'root_attribute_types': header['root_attribute_types'], 'data_attribute_types': header['data_attribute_types'],
                                  'creation_filters': header['creation_filters']},
            'compact_data_attributes': shifted, 'compact_provenance_attributes': provenance,
            'raw_roundtrip_verified': True,
            'codec_signal_decode_invocations': 0, 'writer_closed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scope', 'expected-scope-sha256', 'expected-worker-sha256', 'root-admission',
                 'expected-root-admission-sha256', 'public-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-exploratory-source-values', action='store_true')
    args = parser.parse_args()
    exact_environment()
    require(args.root_go_exploratory_source_values and re.fullmatch(r'[0-9a-f]{40}', args.public_freeze_commit), 'Explicit frozen root exploratory GO required')
    for value in (args.expected_scope_sha256, args.expected_worker_sha256, args.expected_root_admission_sha256):
        require(re.fullmatch(r'[0-9a-f]{64}', value), 'Exact SHA256 required')
    require(Path(args.scope) == ROOT / TOOLS / 'scope.json'
            and Path(args.root_admission) == ROOT / RESULTS / 'ROOT_ADMISSION.json', 'Frozen scope/admission paths differ')
    def deadline(signum, frame):
        raise TimeoutError('Acquisition child resource deadline')
    for signum in (signal.SIGALRM, signal.SIGXCPU, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (119, 120))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, int(LIMITS['wall_seconds'] - (time.monotonic() - STARTED))))
    scope = read_json({'path': TOOLS + '/scope.json', 'bytes': Path(args.scope).stat().st_size,
                       'sha256': args.expected_scope_sha256})
    qualified, manifest, admission = contract(scope, args)
    out = relative(scope['output_directory'])
    require(out.parent.is_dir(), 'Create output parent before freezing; output itself must remain absent')
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    directory_fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    result = {'schema': 'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_RESULT_V1', 'status': 'IN_PROGRESS',
              'scope_sha256': args.expected_scope_sha256, 'worker_pin': scope['worker_pin'],
              'public_freeze_commit': args.public_freeze_commit,
              'root_admission_sha256': args.expected_root_admission_sha256,
              'qualified_metadata_pin': scope['qualified_metadata_pin'], 'qualified_execution_pin': scope['qualified_execution_pin'],
              'descriptor_manifest_pin': scope['descriptor_manifest_pin'],
              'original_A_B_status': 'FAIL_CLOSED', 'independent_validation_admission': 'BLOCKED',
              'acquisition_admission': 'ROOT_EXPLORATORY_SOURCE_VALUES_GO',
              'compact_files': [], 'raw_range_records': [], 'value_read_requests': [],
              'metadata_followup_requests': 0, 'HEAD_requests': 0, 'retries': 0, 'redirects': 0,
              'dataset_value_API_used': False, 'codec_signal_decode_invocations': 0,
              'whole_original_source_MD5_verified': False, 'scientific_search_run': False}
    ledger = {'schema': 'SETI_VISIT2019_ONE_NATIVE_APPLICATION_BODY_LEDGER_V1',
              'exact_payload_BODY_reserved_before_first_HTTP_bytes': scope['exact_expected_payload_BODY_bytes'],
              'payload_BODY_cap_bytes': LIMITS['payload_BODY_bytes'], 'BODY_bytes_received': 0,
              'requests_attempted': 0, 'HTTP_request_cap': scope['payload_HTTP_request_cap'],
              'attempts_per_exact_range': 1, 'complete': False}
    success = False
    try:
        require(allocated_bytes(SHARED_ROOTS) + scope['output_cap_bytes'] <= LIMITS['shared_workspace_bytes'], 'Shared 12GiB output reservation fails')
        free = os.statvfs(out)
        require(free.f_bavail * free.f_frsize >= scope['output_cap_bytes'], 'Finite output free-space reservation fails')
        rawdir = out / 'raw_ranges'
        rawdir.mkdir()
        fsync_dir(out)
        save(out / 'SOURCE_BODY_LEDGER.json', ledger, create_only=True)
        save(out / 'ACQUISITION_STARTED_ONCE.json', {'status': 'CREATE_ONLY_NO_RETRY_NO_RESUME',
             'scope_sha256': args.expected_scope_sha256, 'BODY_reserved_bytes': scope['exact_expected_payload_BODY_bytes']}, create_only=True)
        save(out / 'ACQUISITION_RESULT.json', result, create_only=True)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        def checkpoint():
            require(output_bytes(out) <= scope['output_cap_bytes'], 'Finite acquisition output cap exceeded')
            save(out / 'SOURCE_BODY_LEDGER.json', ledger)
            save(out / 'ACQUISITION_RESULT.json', result)
        for source, header in zip(manifest['sources'], qualified['sources']):
            for row in source['descriptors']:
                usage()
                offset, size = row['file_offset'], row['size']
                record = {'source_id': source['source_id'], 'ordered_index': source['ordered_index'],
                          'time_row': row['time_row'], 'url': source['url'], 'attempt': 1,
                          'source_range_half_open': [offset, offset + size],
                          'expected_etag': source['etag'], 'source_file_bytes': source['source_file_bytes'],
                          'body_bytes_received': 0, 'status': 'ATTEMPT_CONSUMED_BEFORE_HTTP',
                          'request_headers': {'Range': f'bytes={offset}-{offset + size - 1}',
                                              'If-Match': source['etag'], 'Accept-Encoding': 'identity'}}
                require(ledger['requests_attempted'] < scope['payload_HTTP_request_cap'], 'Finite request reservation exhausted')
                ledger['requests_attempted'] += 1
                result['value_read_requests'].append(record)
                checkpoint()
                raw_path = rawdir / (source['source_id'] + '_row%06d.raw.bin' % row['time_row'])
                temp = raw_path.with_name(raw_path.name + '.partial')
                response, body_hash = None, hashlib.sha256()
                def count(piece):
                    require(isinstance(piece, bytes), 'HTTP read returned non-bytes')
                    record['body_bytes_received'] += len(piece)
                    ledger['BODY_bytes_received'] += len(piece)
                    # Accounting is committed before any raw file write, also on exceptional partial returns.
                    save(out / 'SOURCE_BODY_LEDGER.json', ledger)
                    require(record['body_bytes_received'] <= size
                            and ledger['BODY_bytes_received'] <= scope['exact_expected_payload_BODY_bytes'], 'Returned BODY exceeds exact frozen reservation')
                try:
                    request = urllib.request.Request(source['url'], headers=record['request_headers'], method='GET')
                    response = opener.open(request, timeout=min(60, max(1, LIMITS['wall_seconds'] - (time.monotonic() - STARTED))))
                    record['http_status'] = response.status
                    record['response_url'] = response.geturl()
                    record['response_headers'] = {name: response.headers.get(name) for name in
                        ('Content-Range', 'Content-Length', 'Content-Encoding', 'ETag', 'Last-Modified')}
                    require(response.status == 206 and response.geturl() == source['url']
                            and response.headers.get('Content-Range') == f'bytes {offset}-{offset + size - 1}/{source["source_file_bytes"]}'
                            and response.headers.get('Content-Length') == str(size)
                            and response.headers.get('ETag') == source['etag']
                            and (response.headers.get('Content-Encoding') or 'identity').lower() == 'identity',
                            'Exact frozen URL/206/range/length/identity/strong ETag required before BODY')
                    with temp.open('xb') as handle:
                        try:
                            while record['body_bytes_received'] < size:
                                usage()
                                try:
                                    piece = response.read(min(65536, size - record['body_bytes_received']))
                                except BaseException as error:
                                    partial = getattr(error, 'partial', b'')
                                    if isinstance(partial, bytes) and partial:
                                        count(partial)
                                        body_hash.update(partial)
                                        require(handle.write(partial) == len(partial), 'Short exceptional partial compressed-row write')
                                    raise
                                count(piece)
                                require(piece, 'Incomplete exact source BODY; no retry')
                                body_hash.update(piece)
                                require(handle.write(piece) == len(piece), 'Short raw compressed-row write')
                            handle.flush()
                            os.fsync(handle.fileno())
                        except BaseException:
                            # Preserve already-returned bytes on every exceptional
                            # exit, including EOF, deadlines and errors without partial.
                            handle.flush()
                            os.fsync(handle.fileno())
                            if handle.tell():
                                record.update(partial_raw_path=temp.relative_to(out).as_posix(),
                                              partial_raw_bytes=handle.tell(), partial_raw_sha256=body_hash.hexdigest(),
                                              partial_raw_fsynced=True)
                            fsync_dir(rawdir)
                            raise
                    response.close()
                    response = None
                    os.replace(temp, raw_path)
                    fsync_dir(rawdir)
                    raw_record = {'source_id': source['source_id'], 'ordered_index': source['ordered_index'],
                                  'time_row': row['time_row'], 'path': raw_path.relative_to(out).as_posix(),
                                  'bytes': size, 'sha256': body_hash.hexdigest(), 'filter_mask': row['filter_mask'],
                                  'original_chunk_origin': row['coordinates'][:3],
                                  'source_range_half_open': [offset, offset + size], 'fsynced_before_HDF5': True,
                                  'source_url': source['url'], 'source_etag': source['etag']}
                    require(raw_path.stat().st_size == size and digest(raw_path) == raw_record['sha256'], 'Durable original compressed row changed')
                    result['raw_range_records'].append(raw_record)
                    record.update(status='PASS_EXACT_SOURCE_RANGE_DURABLE_RAW', raw_sha256=raw_record['sha256'], standalone_raw_path=raw_record['path'])
                    checkpoint()
                    print('RAW_ROW_DURABLE', source['source_id'], row['time_row'], size, flush=True)
                except BaseException as error:
                    if isinstance(error, urllib.error.HTTPError):
                        error.close()  # Do not read an error response BODY.
                    record.update(status='FAILED_CLOSED_ATTEMPT_CONSUMED_NO_RETRY', error_type=type(error).__name__, error=str(error))
                    raise
                finally:
                    if response is not None:
                        response.close()
                    checkpoint()
        require(ledger['BODY_bytes_received'] == scope['exact_expected_payload_BODY_bytes']
                and ledger['requests_attempted'] == len(result['raw_range_records']) == scope['payload_HTTP_request_cap'], 'Complete exact raw count/BODY accounting differs')
        result['status'] = 'COMPLETE_EXACT_COMPRESSED_RAW_ROWS_BEFORE_HDF5'
        checkpoint()
        for source, header in zip(manifest['sources'], qualified['sources']):
            raw_rows = [record for record in result['raw_range_records'] if record['source_id'] == source['source_id']]
            result['compact_files'].append(make_compact(out, source, header, raw_rows, scope))
            checkpoint()
            print('COMPACT_WRITER_CLOSED_NO_SIGNAL_DECODE', source['source_id'], flush=True)
        require(len(result['compact_files']) == 6, 'Exactly six closed compact writers required')
        input_pins = [scope[key] for key in ('worker_pin', 'launcher_pin', 'common_pin', 'qualified_metadata_pin', 'qualified_execution_pin',
                      'descriptor_manifest_pin', 'prior_source_attempts_pin', 'protected_frames_pin')]
        input_pins += manifest['typed_index_evidence_pins']
        input_pins += [admission['source_only_peer_receipt_pin']]
        for original_pin in input_pins:
            read_pin(original_pin)
        require(digest(args.scope) == args.expected_scope_sha256
                and digest(args.root_admission) == args.expected_root_admission_sha256, 'Frozen scope/root admission changed before final result')
        result['verified_input_end_pins'] = input_pins
        ledger['complete'] = True
        result['status'] = 'COMPLETE_EXACT_RAW_ROWS_AND_COMPACT_FILES_NO_SIGNAL_DECODE'
        result['application_BODY_bytes_received'] = ledger['BODY_bytes_received']
        result['source_values_rows_acquired'] = len(result['raw_range_records'])
        result['source_workers_max'] = result['HDF5_assembly_threads'] = 1
        result['write_decode_interleaving'] = False
        checkpoint()
        success = True
    except BaseException as error:
        result.update(status='FAILED_CLOSED_NO_RETRY_NO_RESUME', error_type=type(error).__name__, error=str(error),
                      application_BODY_bytes_received=ledger['BODY_bytes_received'])
        save(out / 'SOURCE_BODY_LEDGER.json', ledger)
        save(out / 'ACQUISITION_RESULT.json', result)
    finally:
        for signum in (signal.SIGALRM, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(signum, signal.SIG_IGN)
        signal.alarm(0)
        measured = {'process_CPU_seconds_including_imports_and_HDF5_close': time.process_time(),
                    'wall_seconds_since_module_start': time.monotonic() - STARTED,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        resources_pass = measured['process_CPU_seconds_including_imports_and_HDF5_close'] <= LIMITS['CPU_seconds'] and measured['wall_seconds_since_module_start'] <= LIMITS['wall_seconds'] and measured['peak_RSS_bytes'] <= LIMITS['memory_bytes']
        receipt = {'schema': 'SETI_VISIT2019_ONE_NATIVE_RAW_EXECUTION_RECEIPT_V1',
                   'status': result['status'], 'scope_sha256': args.expected_scope_sha256,
                   'public_freeze_commit': args.public_freeze_commit,
                   'root_admission_sha256': args.expected_root_admission_sha256,
                   'ACQUISITION_RESULT_pin': pin(out / 'ACQUISITION_RESULT.json'),
                   'SOURCE_BODY_LEDGER_pin': pin(out / 'SOURCE_BODY_LEDGER.json'),
                   'measured_resources': measured, 'resource_caps_satisfied': resources_pass,
                   'payload_application_BODY_bytes_received': ledger['BODY_bytes_received'],
                   'retry': False, 'signal_decode_invocations': 0,
                   'original_A_B_status': 'FAIL_CLOSED', 'independent_validation_admission': 'BLOCKED'}
        save(out / 'EXECUTION_RECEIPT.json', receipt, create_only=True)
        os.close(directory_fd)
        print(json.dumps(receipt, sort_keys=True, allow_nan=False), flush=True)
    return 0 if success and resources_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
