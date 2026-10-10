"""Create-only metadata JSON support for the fixed one-native acquisition.

No target import/execution, HTTP, binary cache read, HDF5, or array API. Run only
after root has the final closed COMPLETE TREE plan and exact finite history.
This helper never creates acquisition admission or authorizes payload requests.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import stat
import struct
import time

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_native_acquisition_20261010'
TOOLS = 'tools/' + FAMILY
RESULTS = 'results/' + FAMILY
MIDPOINT_RULE = 'floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes'
COMPLETE_PLAN = 'COMPLETE_SELECTED_SIX_SOURCE_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION'
COMPLETE_SOURCE = 'COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION'
LIMITS = {'CPU_seconds': 120, 'wall_seconds': 1800, 'memory_bytes': 536870912,
          'payload_BODY_bytes': 268435456, 'shared_workspace_bytes': 12884901888}
SOURCE_PINS = {
    'worker_pin': (TOOLS + '/acquire_once.py', 38695, '8b85e33ea82dfee72e72928afb0c69f7765ee6e2f12f49be4a9ff32e366f933a'),
    'common_pin': (TOOLS + '/common.py', 4783, '5a8e351275b1d478c6d2c10a70395e514720fb32299eae0a9d0e98191f7d5158'),
    'launcher_pin': (TOOLS + '/launch_once.py', 15799, 'b52cd8caf0a5920a06f61dd036ec533f53eef8587de87a9e0bf15a086e5c5fab')}
SOURCE_IDS = ('S2019_31_BLC77_ON1_0077', 'S2019_31_BLC77_CONTROL1_0078',
              'S2019_31_BLC77_ON2_0079', 'S2019_31_BLC77_CONTROL2_0080',
              'S2019_31_BLC77_ON3_0081', 'S2019_31_BLC77_CONTROL3_0082')
FILENAMES = ('blc77_guppi_58755_79249_HIP98505_0077.gpuspec.0000.h5',
             'blc77_guppi_58755_79564_HIP98375_0078.gpuspec.0000.h5',
             'blc77_guppi_58755_79879_HIP98505_0079.gpuspec.0000.h5',
             'blc77_guppi_58755_80200_HIP98154_0080.gpuspec.0000.h5',
             'blc77_guppi_58755_80521_HIP98505_0081.gpuspec.0000.h5',
             'blc77_guppi_58755_80832_HIP98440_0082.gpuspec.0000.h5')
URLS = tuple('https://bldata.berkeley.edu/pipeline/AGBT19B_999_31/blc77/' + x for x in FILENAMES)
START = time.monotonic()
ADMITTED = {}
BINARY_STAT_ONLY = {}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(name):
    require(isinstance(name, str), 'Root-relative path required')
    p = Path(name)
    require(p.parts and not p.is_absolute() and '..' not in p.parts, 'Invalid relative path')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents, 'Escaped root or symlink path')
    return p


def admitted_pin(pin, read_content=True):
    require(isinstance(pin, dict) and set(pin) == {'path', 'bytes', 'sha256'}
            and type(pin['bytes']) is int and 0 <= pin['bytes'] <= 16777216
            and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'Exact finite pin required')
    p = relative(pin['path'])
    require(stat.S_ISREG(p.stat().st_mode) and not p.is_symlink()
            and p.stat().st_size == pin['bytes'], 'Exact regular pinned input required')
    require(pin['path'] not in ADMITTED or ADMITTED[pin['path']] == pin, 'Conflicting pin')
    ADMITTED[pin['path']] = dict(pin)
    if not read_content:
        require(p.suffix == '.bin', 'Only retained cache BIN pins may use stat-only admission')
        BINARY_STAT_ONLY[pin['path']] = dict(pin)
        return None
    require(p.suffix in ('.json', '.py', '.md'), 'Helper reads JSON/source only; no BIN/HDF/arrays')
    raw = p.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned JSON/source changed')
    return raw


def read_json(pin):
    require(Path(pin['path']).suffix == '.json', 'JSON pin required')
    def nonfinite(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(admitted_pin(pin), parse_constant=nonfinite)


def include_evidence(pin):
    admitted_pin(pin, Path(pin['path']).suffix != '.bin')


def file_pin(path):
    path = Path(path)
    require(path.resolve() == path and ROOT in path.parents and not path.is_symlink(), 'Canonical own file required')
    require(path.suffix in ('.json', '.py', '.md') and stat.S_ISREG(path.stat().st_mode)
            and path.stat().st_size <= 16777216, 'Finite source/JSON file required')
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= 16777216, 'Finite metadata output cap exceeded')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def span(value, size=None):
    require(isinstance(value, list) and len(value) == 2 and all(type(x) is int for x in value)
            and 0 <= value[0] < value[1] and (size is None or value[1] <= size), 'Invalid exact interval')
    return value


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def limits_now():
    measured = {'CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(measured['CPU_seconds'] <= 20 and measured['wall_seconds'] <= 300
            and measured['peak_RSS_bytes'] <= 536870912, 'Scope helper resource cap exceeded')
    require(len(ADMITTED) <= 1024, 'Finite evidence pin count exceeded')
    return measured


def bind_qualification(tree_scope):
    q = tree_scope['metadata_qualification']
    qs, result, execution = (read_json(q[k]) for k in ('scope_pin', 'result_pin', 'execution_pin'))
    admitted_pin(q['worker_pin'])
    require(qs['schema'] == 'SETI_VISIT2019_SIX_HDF_HEADER_CACHE_QUALIFICATION_SCOPE_V3'
            and result['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and execution['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1'
            and result['status'] == execution['metadata_eligibility_status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and execution['status'] == 'COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION'
            and execution['all_input_end_readbacks_exact'] is execution['resource_caps_satisfied'] is True,
            'Closed actual V3 PASS qualification required')
    require(result['scope_sha256'] == execution['scope_sha256'] == q['scope_pin']['sha256']
            and result['script_sha256'] == execution['script_sha256'] == q['worker_pin']['sha256'] == qs['script_sha256']
            and execution['METADATA_QUALIFICATION_RESULT_sha256'] == q['result_pin']['sha256']
            and result['public_freeze_commit'] == execution['public_freeze_commit']
            and re.fullmatch('[0-9a-f]{40}', execution['public_freeze_commit'])
            and qs['cache_admission'] == tree_scope['cache_admission']
            and tree_scope['qualification_result_pin'] == q['result_pin'], 'Qualification pin/history joins differ')
    require(result['metadata_eligibility']['status'] == result['status']
            and all(c['PASS'] is True for c in result['metadata_eligibility']['checks'])
            and result['HTTP_requests'] == execution['HTTP_requests'] == 0
            and result['spectral_values_read'] is execution['spectral_values_read'] is False
            and result['dataset_value_API_used'] is execution['dataset_value_API_used'] is False
            and result['independent_validation_admission'] == 'BLOCKED', 'Qualification is not metadata-only PASS')
    for pin in execution['input_pins']:
        include_evidence(pin)
    return q, result


def bind_tree(config):
    scope = read_json(config['tree_scope_pin'])
    result = read_json(config['tree_result_pin'])
    execution = read_json(config['tree_execution_pin'])
    require(scope['schema'] == 'SETI_VISIT2019_TYPED_TREE1_PLAN_SCOPE_V1'
            and result['schema'] == 'SETI_VISIT2019_PURE_TREE1_METADATA_PLAN_RESULT_V1'
            and result['status'] == COMPLETE_PLAN
            and execution['schema'] == 'SETI_VISIT2019_TREE1_METADATA_PLAN_EXECUTION_V1'
            and execution['status'] == 'COMPLETE_PURE_TREE1_METADATA_PLAN_CAPTURE_NO_VALUES_ADMISSION'
            and execution['structure_status'] == COMPLETE_PLAN
            and execution['resource_caps_satisfied'] is execution['all_input_end_readbacks_exact'] is True,
            'Only final closed COMPLETE TREE plan may prepare acquisition scope')
    require(result['scope_sha256'] == execution['scope_sha256'] == config['tree_scope_pin']['sha256']
            and result['script_sha256'] == execution['script_sha256'] == scope['script_sha256']
            and result['parser_sha256'] == execution['parser_sha256'] == scope['parser_sha256']
            and execution['PLAN_RESULT_sha256'] == config['tree_result_pin']['sha256']
            and result['public_freeze_commit'] == execution['public_freeze_commit']
            and re.fullmatch('[0-9a-f]{40}', execution['public_freeze_commit'])
            and result['qualification_result_pin'] == scope['metadata_qualification']['result_pin']
            and result['HTTP_requests'] == execution['HTTP_requests'] == 0
            and result['spectral_values_read'] is execution['spectral_values_read'] is False
            and result['payload_pointer_followed'] is execution['payload_pointer_followed'] is False,
            'Closed TREE result/EXEC/science provenance joins differ')
    manifest = read_json(execution['input_pins_manifest_pin'])
    require(manifest['schema'] == 'SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1'
            and manifest['all_input_end_readbacks_exact'] is True, 'Closed TREE input manifest required')
    for pin in manifest['input_pins']:
        include_evidence(pin)
    require(any(p['sha256'] == scope['script_sha256'] and p['path'].endswith('/planner_v2.py')
                for p in manifest['input_pins']) and scope['tree_core_pin'] in manifest['input_pins'],
            'Exact V2 TREE caller/parser must be closed-plan inputs')
    return scope, result


def bind_closed_transport(entry, result_key):
    scope, result, execution, outer = (read_json(entry[k]) for k in
                                      ('scope_pin', 'result_pin', 'execution_pin', 'outer_resources_pin'))
    for key in ('worker_pin', 'outer_worker_pin'):
        admitted_pin(entry[key])
    root = read_json(entry['root_admission_pin'])
    require(scope['schema'] == entry['expected_scope_schema']
            and result['schema'] == entry['expected_result_schema']
            and result['status'] == execution['status'] == entry['expected_complete_status']
            and result['scope_sha256'] == execution['scope_sha256'] == entry['scope_pin']['sha256']
            and result['wrapper_sha256'] == execution['wrapper_sha256'] == entry['worker_pin']['sha256']
            and execution[result_key] == entry['result_pin']['sha256']
            and result['root_admission_sha256'] == execution['root_admission_sha256'] == entry['root_admission_pin']['sha256']
            and execution['resource_caps_satisfied'] is execution['no_retry'] is True
            and result['spectral_values_read'] is result['dataset_value_API_used'] is False,
            'Prior transport must have exact closed COMPLETE metadata provenance')
    require(root['schema'] == entry['expected_root_admission_schema']
            and root['status'] == entry['expected_root_admission_status']
            and root['scope_sha256'] == entry['scope_pin']['sha256']
            and root['wrapper_sha256'] == entry['worker_pin']['sha256']
            and root['source_public_freeze_commit'] == execution['source_public_freeze_commit']
            and result['source_public_freeze_commit'] == execution['source_public_freeze_commit']
            and re.fullmatch('[0-9a-f]{40}', execution['source_public_freeze_commit']), 'Prior root/freeze join differs')
    require(outer['schema'] == 'SETI_VISIT2019_FULL_CHILD_COMMAND_RESOURCE_RECEIPT_V1'
            and outer['status'] == 'PASS_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED'
            and outer['resource_caps_satisfied'] is outer['child_started'] is True
            and outer['retry'] is False and outer['actual_child_return_code'] == outer['actual_child_exit_code'] == 0
            and outer['actual_child_terminating_signal'] is None
            and outer['child_wall_timeout'] is outer['child_group_SIGKILL_after_timeout'] is False
            and outer['worker'] == entry['worker_pin'] and outer['launcher'] == entry['outer_worker_pin']
            and outer['scope'] == entry['scope_pin'] and outer['root_admission'] == entry['root_admission_pin'],
            'Prior actual whole-child exit0/resource closure required')
    for name, pin, state in (('EXECUTION_RECEIPT.json', entry['execution_pin'], execution['status']),
                             (Path(entry['result_pin']['path']).name, entry['result_pin'], result['status'])):
        require(outer[name]['pin'] == pin and outer[name]['original_status'] == state, 'Prior outer exact inner pin differs')
    return scope, result


def prior_history(tree_scope, headers):
    by_id = {h['source_id']: h for h in headers}
    ranges = {sid: [] for sid in SOURCE_IDS}
    request_pins = []
    def add(pin, expected_source, expected_interval=None):
        get = read_json(pin)
        h = by_id[expected_source]
        require(get['source_id'] == expected_source and get['url'] == get['final_url'] == h['url']
                and get['etag'] == h['etag'] and get['source_file_bytes'] == h['source_file_bytes']
                and get['method'] == 'GET' and get['attempt'] == 1, 'Prior GET identity differs')
        match = re.fullmatch(r'bytes=(\d+)-(\d+)', get['request_headers']['Range'])
        require(match is not None and get['request_headers']['If-Match'] == h['etag']
                and get['request_headers']['Accept-Encoding'] == 'identity', 'Prior exact GET headers required')
        interval = span([int(match[1]), int(match[2]) + 1], h['source_file_bytes'])
        require(expected_interval is None or interval == expected_interval, 'Prior expected request range differs')
        require('requested_interval_half_open' not in get or get['requested_interval_half_open'] == interval,
                'Prior requested interval/header mismatch')
        require(pin not in request_pins, 'Duplicate request receipt in complete history')
        request_pins.append(pin)
        ranges[expected_source].append(interval)
        return get
    cache = tree_scope['cache_admission']
    require(cache['schema'] == 'SETI_VISIT2019_GENERIC_METADATA_CACHE_ADMISSION_V1'
            and len(cache['initial_sources']) == 6 and len(cache['completion_rounds']) <= 16
            and len(tree_scope['tree_metadata_rounds']) <= 16, 'Finite exact metadata history required')
    initial = cache['initial_transport']
    require(initial['expected_complete_status'] == 'COMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_VALUES_ADMISSION',
            'Exact initial history family required')
    old_scope, result = bind_closed_transport(initial, 'HEADER_RESULT_sha256')
    require(len(result['sources']) == 6 and result['prefix_GET_requests_attempted'] == 6, 'Complete initial six GETs required')
    for i, (entry, header, saved) in enumerate(zip(cache['initial_sources'], headers, result['sources']), 1):
        require(entry['source_id'] == saved['source_id'] == header['source_id']
                and entry['url'] == saved['url'] == header['url'] and entry['ordered_index'] == i,
                'Initial exact source order differs')
        add(entry['PREFIX_receipt_pin'], header['source_id'], [0, old_scope['limits']['prefix_bytes_per_source']])
        read_json(entry['HEAD_receipt_pin'])
        read_json(entry['HEADER_receipt_pin'])
    stages = cache['completion_rounds'] + tree_scope['tree_metadata_rounds']
    seen_stages = set()
    for entry in stages:
        require(entry['result_pin']['path'] not in seen_stages
                and entry['expected_complete_status'] in ('COMPLETE_FIXED_TYPED_METADATA_FETCH_NO_VALUES_ADMISSION',
                                                          'COMPLETE_FIXED_TREE1_METADATA_FETCH_NO_VALUES_ADMISSION'),
                'Duplicate/unsupported prior metadata transport')
        seen_stages.add(entry['result_pin']['path'])
        old_scope, result = bind_closed_transport(entry, 'FETCH_RESULT_sha256')
        require(len(entry['requests']) == len(result['requests']) == result['GET_requests_attempted']
                and result['HEAD_requests_attempted'] == 0, 'Complete prior request inventory required')
        for entry_get, saved in zip(entry['requests'], result['requests']):
            require(saved['request_receipt_pin'] == entry_get['GET_receipt_pin']
                    and saved['request_id'] == entry_get['request_id'] and saved['source_id'] == entry_get['source_id'],
                    'Prior standalone/global request pin differs')
            got = add(entry_get['GET_receipt_pin'], saved['source_id'], saved['requested_interval_half_open'])
            require({k: v for k, v in saved.items() if k != 'request_receipt_pin'} == got,
                    'Prior standalone/global complete request differs')
    return [dict(source_id=h['source_id'], url=h['url'], ordered_index=h['ordered_index'], etag=h['etag'],
                 source_file_bytes=h['source_file_bytes'], attempted_ranges_half_open=ranges[h['source_id']])
            for h in headers], request_pins


def compact_scalar_exact(header):
    attrs, types = header['data_attributes'], header['data_attribute_types']
    c0 = header['metadata_derived_midpoint']['absolute_channel_start']
    values = {'fch1': attrs['fch1'] + c0 * attrs['foff'], 'nchans': header['chunks'][2]}
    formats = {'<f4': '<f', '<f8': '<d', '<i1': '<b', '|i1': '<b', '<u1': '<B', '|u1': '<B',
               '<i2': '<h', '<u2': '<H', '<i4': '<i', '<u4': '<I', '<i8': '<q', '<u8': '<Q'}
    for key, value in values.items():
        record = types[key]
        require(record['shape'] == [] and record['numpy_dtype_string'] in formats
                and type(value) in (int, float) and math.isfinite(value), 'Finite original compact scalar type required')
        packed = struct.pack(formats[record['numpy_dtype_string']], value)
        require(struct.unpack(formats[record['numpy_dtype_string']], packed)[0] == value,
                'Shifted compact scalar not exactly representable in original dtype')


def exact_descriptors(plan, headers, prior):
    require(len(plan['sources']) == len(headers) == len(prior) == 6, 'Exact six-source plan required')
    sources, frames, total, requests, grid = [], [], 0, 0, None
    for i, (saved, h, old) in enumerate(zip(plan['sources'], headers, prior), 1):
        require(all(r['source_id'] == SOURCE_IDS[i-1] and r['url'] == URLS[i-1] and r['ordered_index'] == i
                    for r in (saved, h, old)) and saved['etag'] == h['etag'] == old['etag']
                and saved['source_file_bytes'] == h['source_file_bytes'] == old['source_file_bytes'],
                'Frozen source identity/order/HEAD differs')
        require(saved['schema'] == 'SETI_CACHE_ONLY_LEGACY_TREE1_MIDPOINT_PLAN_V1' and saved['status'] == COMPLETE_SOURCE
                and not saved['invalid'] and not saved['unsupported'] and not saved['missing_metadata_fragments']
                and saved['HTTP_requests'] == 0 and saved['spectral_values_read'] is saved['payload_pointer_followed'] is False,
                'Every actual TREE source must be clean COMPLETE')
        shape, chunks = h['shape'], h['chunks']
        require(h['status'] == 'COMPLETE_HEADER_METADATA_ONLY' and h['dtype_string'] == '<f4'
                and h['dtype_itemsize_bytes'] == 4 and len(shape) == len(chunks) == 3
                and all(type(x) is int and x > 0 for x in shape + chunks)
                and shape[1] == chunks[0] == chunks[1] == 1, 'Actual source geometry/dtype differs')
        ntime, nchan, width = shape[0], shape[2], chunks[2]
        count = (nchan + width - 1) // width
        c0 = count // 2 * width
        require(h['fixed_midpoint_rule'] == MIDPOINT_RULE and h['native_chunks_along_frequency'] == count
                and h['metadata_derived_midpoint'] == {'native_ordinal_zero_based': count//2,
                    'absolute_channel_start': c0, 'channel_count': width} and c0 + width <= nchan,
                'Actual fixed full-native midpoint required')
        current = {key: h[key] for key in ('shape', 'chunks', 'dtype_string', 'creation_filters')}
        current['grid'] = {key: h['data_attributes'][key] for key in ('fch1', 'foff', 'tsamp')}
        require(grid is None or current == grid, 'Actual all-six grids differ')
        grid = current
        compact_scalar_exact(h)
        rows = saved['descriptors']
        require(len(rows) == ntime and [r['time_row'] for r in rows] == list(range(ntime)), 'Untouched complete time-row inventory required')
        new = []
        for row in rows:
            a, n, mask = row['file_offset'], row['size'], row['filter_mask']
            require(type(a) is int and type(n) is int and 0 < n <= LIMITS['payload_BODY_bytes']
                    and type(mask) is int and 0 <= mask < (1 << len(h['creation_filters']))
                    and row['coordinates'] == [row['time_row'], 0, c0, 0]
                    and row['source_channel_start'] == c0 and row['logical_channel_count'] == width
                    and row['decoded_full_chunk_bytes'] == width*4
                    and row['payload_pointer_followed'] is row['HTTP_authorized'] is False
                    and row['typed_leaf_pointer_evidence'] and row['metadata_traversal'], 'Exact typed raw row differs')
            interval = span([a, a+n], h['source_file_bytes'])
            require(row['payload_interval_half_open'] == interval
                    and all(not overlaps(interval, other) for other in old['attempted_ranges_half_open'] + new),
                    'Prior replay/new payload overlap or descriptor interval mismatch')
            new.append(interval)
            total += n
            requests += 1
        sources.append({key: saved[key] for key in ('source_id', 'url', 'ordered_index', 'etag', 'source_file_bytes', 'status', 'descriptors')})
        frames.append({'source_id': h['source_id'], 'url': h['url'],
                       'source_channel_interval_half_open': [c0, c0+width], 'source_ranges_half_open': new})
    require(0 < total <= LIMITS['payload_BODY_bytes'], 'Exact finite pilot BODY exceeds 256MiB')
    return sources, frames, total, requests


def known_protection(pin, headers, frames):
    known = read_json(pin)
    require(known['schema'] == 'SETI_VISIT2019_KNOWN_OLD_SOURCE_FRAMES_PROSPECTIVE_CONFIG_V1'
            and known['status'] == 'PASS_FINITE_KNOWN_URL_IDENTITIES_DISJOINT_ACTUAL_DESCRIPTOR_GATE_PENDING'
            and known['known_frame_count'] == len(known['known_frames']) == 12
            and known['original_A_B_status'] == 'FAIL_CLOSED' and known['independent_validation_admission'] == 'BLOCKED'
            and known['global_registry_completeness_claim'] is False, 'Exact finite known-twelve registry required')
    require(known['selected_source_ids_and_URLs'] == [
        {key: h[key] for key in ('ordered_index', 'source_id', 'url')} for h in headers], 'Known registry selection differs')
    for item in known['metadata_evidence']:
        read_json(item['pin'])
    for frame in known['known_frames']:
        evidence = read_json(frame['evidence_pin'])
        source = evidence['sources'][frame['ordered_index']-1]
        interval = span(frame['source_channel_interval_half_open'])
        require(source['url'] == frame['url'] and interval == [0, source['current_header']['dataset_shape'][2]],
                'Known entire source extent differs from pinned UTF8 metadata')
        require(all(f['url'] != frame['url'] or not overlaps(f['source_channel_interval_half_open'], interval)
                    for f in frames), 'Known protected source-channel frame overlaps')
    return known


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--expected-configuration-sha256', required=True)
    parser.add_argument('--root-go-metadata-only', action='store_true')
    args = parser.parse_args()
    require(args.root_go_metadata_only and re.fullmatch('[0-9a-f]{64}', args.expected_configuration_sha256),
            'Explicit root metadata-only GO and exact config SHA required')
    require(os.environ.get('PYTHONPATH') == str(ROOT.parent/'seti_fullpower_work/deps')
            and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1', 'Exact own deps and disabled bytecode writes required')
    def deadline(signum, frame):
        raise TimeoutError('Metadata scope helper deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 22))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    signal.alarm(300)
    config_path = Path(args.configuration)
    require(config_path.is_absolute() and config_path.resolve() == config_path and ROOT in config_path.parents,
            'Canonical own configuration required')
    config_pin = file_pin(config_path)
    require(config_pin['sha256'] == args.expected_configuration_sha256, 'Configuration SHA differs')
    config = read_json(config_pin)
    own = file_pin(Path(__file__).resolve())
    require(config['schema'] == 'SETI_VISIT2019_NATIVE_ACQUISITION_SCOPE_PREPARATION_CONFIG_V1'
            and config['helper_pin'] == own and config['finite_request_history_in_final_tree_scope_complete'] is True
            and config['final_tree_and_HTTP_processes_closed'] is True, 'Exact helper and root finite closure declaration required')
    admitted_pin(own)
    pins = {key: {'path': row[0], 'bytes': row[1], 'sha256': row[2]} for key, row in SOURCE_PINS.items()}
    for pin in pins.values():
        admitted_pin(pin)
    tree_scope, plan = bind_tree(config)
    qualification_pins, qualification = bind_qualification(tree_scope)
    prior_sources, request_pins = prior_history(tree_scope, qualification['sources'])
    sources, frames, body, requests = exact_descriptors(plan, qualification['sources'], prior_sources)
    known = known_protection(config['known_frames_candidate_pin'], qualification['sources'], frames)
    runtime = read_json(config['runtime_metadata_pin'])
    require(runtime['status'] == 'PASS_DEPENDENCY_RUNTIME_METADATA_ONLY'
            and runtime['h5py_version'] == '3.15.1' and runtime['hdf5plugin_version'] == '7.1.0'
            and runtime['HDF5_version'] == '1.14.6' and runtime['source_HTTP'] == runtime['source_files_opened'] == 0
            and runtime['spectral_values_read'] is False, 'Exact root runtime metadata receipt required')
    evidence_pins = sorted(ADMITTED.values(), key=lambda p: p['path'])
    limits_now()
    stage = relative(RESULTS + '/scope_preparation_once')
    scope_path = relative(TOOLS + '/scope.json')
    require(not stage.exists() and not scope_path.exists()
            and not relative(RESULTS+'/ROOT_ADMISSION.json').exists()
            and not relative(RESULTS+'/acquire_once').exists()
            and not relative(RESULTS+'/command_attempt').exists(), 'Fresh create-only acquisition namespace required')
    stage.parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir(exist_ok=False)
    fsync_dir(stage.parent)
    save_new(stage/'PREPARATION_STARTED_ONCE.json', {'status':'STARTED_METADATA_ONLY_NO_RETRY',
             'configuration_pin':config_pin, 'helper_pin':own, 'HTTP_requests':0, 'source_values_admitted':False})
    descriptors = {'schema':'SETI_VISIT2019_ONE_NATIVE_RAW_DESCRIPTOR_MANIFEST_V1',
        'status':'PASS_CLEAN_EXACT_SIX_NATIVE_ROW_DESCRIPTORS_METADATA_ONLY',
        'qualification_result_pin':qualification_pins['result_pin'], 'fixed_midpoint_rule':MIDPOINT_RULE,
        'spectral_values_read':False, 'spectral_payload_fetched':False,
        'typed_index_evidence_pins':evidence_pins, 'sources':sources,
        'source_descriptor_count':requests, 'descriptor_records_copied_unchanged':True}
    descriptor_pin = save_new(stage/'DESCRIPTOR_MANIFEST.json', descriptors)
    prior_pin = save_new(stage/'PRIOR_SOURCE_RANGE_ATTEMPTS.json', {
        'schema':'SETI_VISIT2019_PRIOR_SOURCE_RANGE_ATTEMPTS_V1',
        'status':'PASS_COMPLETE_KNOWN_REQUEST_HISTORY_NO_REPLAY', 'sources':prior_sources,
        'request_receipt_pins':request_pins, 'final_tree_scope_pin':config['tree_scope_pin'],
        'root_finite_history_declaration_pin':config_pin, 'prior_attempt_count':len(request_pins)})
    protection_pin = save_new(stage/'PROTECTED_KNOWN_FRAMES_DISJOINT.json', {
        'schema':'SETI_VISIT2019_PROTECTED_KNOWN_FRAMES_DISJOINT_V1',
        'status':'PASS_PROTECTED_KNOWN_FRAMES_DISJOINT', 'descriptor_manifest_pin':descriptor_pin,
        'qualified_metadata_pin':qualification_pins['result_pin'], 'acquisition_frames':frames,
        'known_frames':known['known_frames'], 'known_frames_candidate_pin':config['known_frames_candidate_pin'],
        'complete_scope_of_this_known_list':known['complete_scope_of_this_known_list'],
        'global_registry_completeness_claim':False, 'unresolved_history':known['unresolved_history'],
        'original_A_B_status':'FAIL_CLOSED', 'independent_validation_admission':'BLOCKED'})
    scope = {'schema':'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_SCOPE_V1', **pins,
        'qualified_metadata_pin':qualification_pins['result_pin'], 'qualified_execution_pin':qualification_pins['execution_pin'],
        'descriptor_manifest_pin':descriptor_pin, 'prior_source_attempts_pin':prior_pin, 'protected_frames_pin':protection_pin,
        'limits':LIMITS, 'shared_workspace_roots':[str(ROOT.parent),'/workspace/scratch/5bf3860dacd6'],
        'output_directory':RESULTS+'/acquire_once', 'source_workers_max':1, 'signal_decode_authorized':False,
        'retry_resume_or_rerun_authorized':False, 'independent_validation_admission':'BLOCKED', 'original_A_B_status':'FAIL_CLOSED',
        'runtime_package_versions':{'h5py':'3.15.1','hdf5plugin':'7.1.0'}, 'hdf5_version':runtime['HDF5_version'],
        'exact_expected_payload_BODY_bytes':body, 'payload_HTTP_request_cap':requests, 'output_cap_bytes':2*body+67108864}
    for pin in evidence_pins:
        include_evidence(pin)
    for pin in (descriptor_pin, prior_pin, protection_pin):
        read_json(pin)
    limits_now()
    scope_pin = save_new(scope_path, scope)
    receipt = {'schema':'SETI_VISIT2019_NATIVE_ACQUISITION_SCOPE_PREPARATION_RECEIPT_V1',
        'status':'COMPLETE_METADATA_ONLY_SCOPE_PREPARATION_NO_PAYLOAD_ADMISSION', 'helper_pin':own,
        'configuration_pin':config_pin, 'scope_pin':scope_pin, 'descriptor_manifest_pin':descriptor_pin,
        'prior_source_attempts_pin':prior_pin, 'protected_frames_pin':protection_pin,
        'copied_descriptor_count':requests, 'prior_attempt_count':len(request_pins),
        'exact_future_payload_BODY_bytes':body, 'source_signal_codec_decodes':0, 'source_HTTP_requests':0,
        'source_BODY_bytes_received':0, 'HDF5_or_array_API_used':False, 'binary_cache_content_reads':0,
        'binary_cache_pins_stat_only':sorted(BINARY_STAT_ONLY.values(), key=lambda p:p['path']),
        'binary_cache_content_integrity_evidence':'Exact closed TREE INPUT_PINS manifest; this helper checks stat only.',
        'all_read_JSON_and_source_end_pins_exact':True, 'all_binary_stat_end_pins_exact':True,
        'resource_measurement':limits_now(), 'acquisition_root_admission_created':False,
        'original_A_B_status':'FAIL_CLOSED', 'independent_validation_admission':'BLOCKED'}
    receipt_pin = save_new(stage/'PREPARATION_RECEIPT.json', receipt)
    signal.alarm(0)
    print(json.dumps({'status':receipt['status'], 'scope_pin':scope_pin, 'preparation_receipt_pin':receipt_pin}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
