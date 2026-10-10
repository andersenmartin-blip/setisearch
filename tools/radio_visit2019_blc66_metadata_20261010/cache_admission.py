"""Inert authentication of six retained prefix/typed-completion caches.

No HTTP, parser, h5py or source-value import/call exists. The caller installs
resource limits and supplies an exact frozen scope containing cache_admission.
Binary buffers are returned unchanged only after closed transport provenance.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'SETI_VISIT2019_GENERIC_METADATA_CACHE_ADMISSION_V1'
MAX_FILE_BYTES = 4 * 1024 ** 2
MAX_CACHE_BYTES_PER_SOURCE = 4 * 1024 ** 2
MAX_RANGES_PER_SOURCE = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(pin, admitted):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and 0 <= pin['bytes'] <= MAX_FILE_BYTES
            and isinstance(pin['path'], str) and isinstance(pin['sha256'], str)
            and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']), 'Exact bounded input pin required')
    path = Path(pin['path'])
    require(path.parts and not path.is_absolute() and '..' not in path.parts, 'ROOT-relative pin path required')
    path = ROOT / path
    require(path.resolve() == path and ROOT in path.parents and not path.is_symlink()
            and stat.S_ISREG(path.stat().st_mode) and path.stat().st_size == pin['bytes'],
            'Canonical regular pinned input required')
    raw = path.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned input bytes changed')
    require(pin['path'] not in admitted or admitted[pin['path']] == pin, 'Conflicting input pin')
    admitted[pin['path']] = dict(pin)
    return raw


def read_json(pin, admitted):
    return json.loads(read_pin(pin, admitted))


def admit_planner_input_pins(execution, admitted):
    """Authenticate either frozen inline pins or the exact manifested pin list."""
    if 'input_pins' in execution:
        pins = execution['input_pins']
    else:
        manifest = read_json(execution['input_pins_manifest_pin'], admitted)
        require(manifest['schema'] == 'SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1',
                'Exact typed planner input-pin manifest schema required')
        pins = manifest['input_pins']
    require(isinstance(pins, list) and 0 < len(pins) <= 4096,
            'Finite nonempty exact typed planner input-pin inventory required')
    for pin in pins:
        read_pin(pin, admitted)


def exact_source(record, identity):
    require(all(record[k] == identity[k] for k in ('source_id', 'url', 'ordered_index')),
            'Fixed source order/identity differs')


def strong_etag(value):
    return isinstance(value, str) and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', value) is not None


def identity_encoding(record):
    require((record['response_headers'].get('Content-Encoding') or 'identity').lower() == 'identity',
            'Encoded source response refused')


def bind_plan_cache_history(plan_scope, config):
    """Exact adapter for the frozen initial V2 anchor; no alias mutation."""
    if plan_scope['schema'] == 'SETI_VISIT2019_TYPED_STRUCTURE_PLAN_SCOPE_V2':
        initial = config['initial_transport']
        family = Path(initial['scope_pin']['path']).parent.name
        require(config['completion_rounds'] == []
                and plan_scope['initial_family'] == family
                and config['source_manifest_pin']['path'] == 'tools/' + family + '/SIX_SOURCE_IDENTITIES.json'
                and plan_scope['source_id_manifest_pin'] == config['source_manifest_pin']
                and plan_scope['initial_scope_pin'] == initial['scope_pin']
                and plan_scope['initial_execution_pin'] == initial['execution_pin']
                and plan_scope['initial_header_result_pin'] == initial['result_pin']
                and plan_scope['initial_root_admission_schema'] == initial['expected_root_admission_schema']
                and plan_scope['sources'] == config['initial_sources']
                and all(x['prefix_pin']['bytes'] == plan_scope['cache_prefix_bytes'] for x in config['initial_sources']),
                'Frozen initial V2 anchor differs from exact initial-only cache configuration')
    else:
        require(plan_scope['schema'] == 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_SCOPE_V1'
                and plan_scope['cache_admission'] == config
                and plan_scope['source_manifest_pin'] == config['source_manifest_pin'],
                'Typed parent did not use the exact retained generic cache history')


def bind_closed_transport(entry, scope, result, execution, result_key, admitted):
    code = entry['worker_pin']
    require(isinstance(entry['expected_root_admission_schema'], str)
            and entry['expected_root_admission_schema'].startswith('SETI_')
            and isinstance(entry['expected_root_admission_status'], str)
            and entry['expected_root_admission_status'].startswith('PASS_'),
            'An exact affirmative root transport admission is required')
    require(scope['wrapper_path'] == code['path'] and scope['wrapper_sha256'] == code['sha256'],
            'Frozen transport source binding differs')
    read_pin(code, admitted)
    require(scope['schema'] == entry['expected_scope_schema']
            and result['schema'] == entry['expected_result_schema']
            and result['status'] == execution['status'] == entry['expected_complete_status'],
            'Unsupported or incomplete transport family')
    require(result['scope_sha256'] == execution['scope_sha256'] == entry['scope_pin']['sha256']
            and result['wrapper_sha256'] == execution['wrapper_sha256'] == code['sha256']
            and execution[result_key] == entry['result_pin']['sha256']
            and result['source_public_freeze_commit'] == execution['source_public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', execution['source_public_freeze_commit'])
            and result['root_admission_sha256'] == execution['root_admission_sha256'] == entry['root_admission_pin']['sha256'],
            'Closed transport scope/result/execution/freeze binding differs')
    require(execution['resource_caps_satisfied'] is True and execution['no_retry'] is True
            and result['spectral_values_read'] is False and result['dataset_value_API_used'] is False
            and all(result[k] == 0 for k in ('retries', 'redirects', 'metadata_followup_requests')),
            'Closed resource/no-replay/no-values provenance differs')
    root = read_json(entry['root_admission_pin'], admitted)
    require(scope['root_admission_path'] == entry['root_admission_pin']['path']
            and root['schema'] == entry['expected_root_admission_schema']
            and root['status'] == entry['expected_root_admission_status']
            and root['scope_sha256'] == entry['scope_pin']['sha256']
            and root['wrapper_sha256'] == code['sha256']
            and root['source_public_freeze_commit'] == execution['source_public_freeze_commit'],
            'Exact root transport admission join differs')
    outer = read_json(entry['outer_resources_pin'], admitted)
    read_pin(entry['outer_worker_pin'], admitted)
    require(outer['schema'] == 'SETI_VISIT2019_FULL_CHILD_COMMAND_RESOURCE_RECEIPT_V1'
            and outer['status'] == 'PASS_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED'
            and outer['resource_caps_satisfied'] is True and outer['child_started'] is True
            and outer['retry'] is False and outer['actual_child_return_code'] == outer['actual_child_exit_code'] == 0
            and outer['actual_child_terminating_signal'] is None
            and outer['child_wall_timeout'] is outer['child_group_SIGKILL_after_timeout'] is False
            and outer['worker'] == code and outer['launcher'] == entry['outer_worker_pin']
            and outer['scope'] == entry['scope_pin'] and outer['root_admission'] == entry['root_admission_pin']
            and outer['source_public_freeze_commit'] == execution['source_public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', outer['launcher_public_freeze_commit']),
            'Exact reaped child exit0/full-command resource closure required')
    for key, pin, status in (('EXECUTION_RECEIPT.json', entry['execution_pin'], execution['status']),
                             (Path(entry['result_pin']['path']).name, entry['result_pin'], result['status'])):
        require(outer[key]['pin'] == pin and outer[key]['original_status'] == status,
                'Outer closed-process receipt does not bind exact original inner status/bytes')
    measurements = (
        ('combined_process_CPU_seconds_before_receipt', 'CPU_cap_seconds_including_launcher_and_child', 'CPU_seconds'),
        ('whole_child_wall_seconds_until_reaped', 'whole_launch_wall_cap_seconds', 'wall_seconds'),
        ('launcher_wall_seconds_since_module_start_before_receipt', 'whole_launch_wall_cap_seconds', 'wall_seconds'),
        ('whole_child_peak_RSS_bytes', 'per_process_peak_RSS_cap_bytes', 'memory_bytes'),
        ('launcher_peak_RSS_bytes', 'per_process_peak_RSS_cap_bytes', 'memory_bytes'))
    for measured_key, cap_key, scope_key in measurements:
        value, cap = outer[measured_key], outer[cap_key]
        require(type(value) in (int, float) and math.isfinite(value) and type(cap) in (int, float)
                and math.isfinite(cap) and 0 <= value <= cap == scope['limits'][scope_key],
                'Measured closed-process cap differs from frozen transport limits')


def admit_initial(config, manifest, admitted):
    entry = config['initial_transport']
    scope = read_json(entry['scope_pin'], admitted)
    result = read_json(entry['result_pin'], admitted)
    execution = read_json(entry['execution_pin'], admitted)
    require(entry['expected_scope_schema'] == 'SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_SCOPE_V1'
            and entry['expected_result_schema'] == 'SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_RESULT_V1'
            and entry['expected_complete_status'] == 'COMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_VALUES_ADMISSION',
            'Only the opaque initial-prefix transport schema is supported')
    bind_closed_transport(entry, scope, result, execution, 'HEADER_RESULT_sha256', admitted)
    prefix_bytes = scope['prefix_bytes']
    require(type(prefix_bytes) is int and 4096 <= prefix_bytes <= 65536 and prefix_bytes & (prefix_bytes - 1) == 0,
            'Finite power-of-two prospective prefix length required')
    require(scope['candidate_metadata_path'] == config['source_manifest_pin']['path']
            and scope['candidate_metadata_sha256'] == config['source_manifest_pin']['sha256']
            and scope['sources'] == manifest['files'] and len(result['sources']) == len(config['initial_sources']) == 6
            and result['all_six_exact_prefix_pairs_complete'] is True
            and result['HEAD_requests_attempted'] == result['prefix_GET_requests_attempted'] == 6
            and result['application_BODY_bytes_received'] == result['application_BODY_charged_upper_bound_bytes'] == 6 * prefix_bytes,
            'Initial six-prefix transport completeness differs')
    caches = []
    for identity, pins, saved in zip(manifest['files'], config['initial_sources'], result['sources']):
        exact_source(pins, identity)
        exact_source(saved, identity)
        require(re.fullmatch(r'[A-Z0-9_]+', identity['source_id']), 'Safe fixed source identifier required')
        base = scope['output_directory'].rstrip('/') + '/' + identity['source_id'] + '/'
        for key, name in (('HEAD_receipt_pin', 'HEAD_RECEIPT.json'), ('PREFIX_receipt_pin', 'PREFIX_RECEIPT.json'),
                          ('HEADER_receipt_pin', 'HEADER_RECEIPT.json'), ('prefix_pin', 'PREFIX.bin')):
            require(pins[key]['path'] == base + name, 'Retained initial source path differs')
        head = read_json(pins['HEAD_receipt_pin'], admitted)
        get = read_json(pins['PREFIX_receipt_pin'], admitted)
        header = read_json(pins['HEADER_receipt_pin'], admitted)
        require(header == saved and header['HEAD'] == head and header['prefix_GET'] == get
                and header['retained_prefix'] == pins['prefix_pin']
                and pins['prefix_pin']['bytes'] == header['prefix_BODY_bytes_received'] == prefix_bytes
                and header['status'] == 'PREFIX_COMPLETE_METADATA_PARSE_DEFERRED_NO_VALUES_ADMISSION',
                'Initial retained prefix/header/HTTP receipt joins differ')
        size, etag = head['source_file_bytes'], head['etag']
        require(type(size) is int and size >= prefix_bytes and strong_etag(etag), 'Initial logical size/strong ETag differs')
        for record, method in ((head, 'HEAD'), (get, 'GET')):
            require(record['source_id'] == identity['source_id'] and record['url'] == record['final_url'] == identity['url']
                    and record['method'] == method and record['attempt'] == 1, 'Exact initial request identity differs')
            identity_encoding(record)
        require(head['state'] == 'PASS_HEAD_METADATA_PIN' and head['status'] == 200
                and head['request_headers'] == {'Accept-Encoding': 'identity'}
                and head['body_bytes_returned_to_application'] == head['BODY_reserved_upper_bound_bytes'] == 0
                and head['response_headers']['Content-Length'] == str(size)
                and head['response_headers']['ETag'] == etag, 'Initial HEAD provenance differs')
        require(get['state'] == f'PASS_EXACT_{prefix_bytes}_PREFIX_RETAINED' and get['status'] == 206
                and get['body_bytes_returned_to_application'] == get['BODY_reserved_upper_bound_bytes'] == prefix_bytes
                and get['request_headers'] == {'Accept-Encoding': 'identity', 'Range': f'bytes=0-{prefix_bytes - 1}', 'If-Match': etag}
                and get['response_headers']['Content-Range'] == f'bytes 0-{prefix_bytes - 1}/{size}'
                and get['response_headers']['Content-Length'] == str(prefix_bytes)
                and get['response_headers']['ETag'] == etag, 'Initial exact 206/range/ETag provenance differs')
        raw = read_pin(pins['prefix_pin'], admitted)
        caches.append({'source_id': identity['source_id'], 'url': identity['url'], 'ordered_index': identity['ordered_index'],
                       'file_size': size, 'etag': etag, 'cache_ranges': [(0, raw, pins['prefix_pin'])]})
    return caches


def append_completion(round_entry, caches, admitted, config, previous_rounds):
    """Optional exact typed-fragment transport; unsupported schemas fail closed."""
    scope = read_json(round_entry['scope_pin'], admitted)
    result = read_json(round_entry['result_pin'], admitted)
    execution = read_json(round_entry['execution_pin'], admitted)
    require(round_entry['expected_scope_schema'] == 'SETI_VISIT2019_FIXED_TYPED_METADATA_FETCH_SCOPE_V1'
            and round_entry['expected_result_schema'] == 'SETI_VISIT2019_FIXED_TYPED_METADATA_FETCH_RESULT_V1'
            and round_entry['expected_complete_status'] == 'COMPLETE_FIXED_TYPED_METADATA_FETCH_NO_VALUES_ADMISSION',
            'Only the closed exact typed-fragment transport schema is supported')
    bind_closed_transport(round_entry, scope, result, execution, 'FETCH_RESULT_sha256', admitted)
    plan_scope = read_json(round_entry['planner_scope_pin'], admitted)
    plan = read_json(round_entry['planner_result_pin'], admitted)
    plan_execution = read_json(round_entry['planner_execution_pin'], admitted)
    parent_history = dict(config, completion_rounds=previous_rounds)
    bind_plan_cache_history(plan_scope, parent_history)
    read_pin(round_entry['planner_worker_pin'], admitted)
    read_pin(round_entry['planner_parser_pin'], admitted)
    require(plan['scope_sha256'] == plan_execution['scope_sha256'] == round_entry['planner_scope_pin']['sha256']
            and plan_execution['PLAN_RESULT_sha256'] == round_entry['planner_result_pin']['sha256']
            and plan_execution['status'] == 'COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION'
            and plan_execution['all_input_end_readbacks_exact'] is plan_execution['resource_caps_satisfied'] is True
            and plan_execution['script_sha256'] == plan_scope['script_sha256']
            and plan_execution['parser_sha256'] == plan_scope['parser_sha256']
            and plan_execution['script_sha256'] == round_entry['planner_worker_pin']['sha256']
            and plan_execution['parser_sha256'] == round_entry['planner_parser_pin']['sha256']
            and plan['public_freeze_commit'] == plan_execution['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', plan_execution['public_freeze_commit'])
            and plan['HTTP_requests'] == plan_execution['HTTP_requests'] == 0
            and plan['spectral_values_read'] is plan_execution['spectral_values_read'] is False,
            'Typed parent planner closure differs')
    for key in ('planner_scope_pin', 'planner_result_pin', 'planner_execution_pin'):
        require(scope[key] == round_entry[key], 'Transport typed-parent pin differs')
    admit_planner_input_pins(plan_execution, admitted)
    require(len(scope['sources']) == len(plan['sources']) == len(caches) == 6,
            'Typed completion must preserve the six source frame')
    require(plan['status'] == 'INCOMPLETE_TYPED_METADATA_FRAGMENTS'
            and plan['chunk_index_traversed'] is False
            and plan['whole_header_or_science_qualification'] is False
            and all(p['status'] in ('COMPLETE_SUPPORTED_HEADER_STRUCTURE', 'INCOMPLETE_TYPED_METADATA_FRAGMENTS')
                    and not p['invalid'] and not p['unsupported']
                    and p['HTTP_requests'] == p['payload_ranges_proposed'] == 0
                    and p['spectral_values_read'] is False for p in plan['sources']),
            'Whole six-source typed parent must be clean incomplete metadata only')
    requests = []
    for source, source_plan, cache in zip(scope['sources'], plan['sources'], caches):
        exact_source(source, cache)
        require(source_plan['source_id'] == cache['source_id'], 'Typed completion plan source order differs')
        require([x['proposal'] for x in source['requests']] == source_plan['missing_metadata_fragments'],
                'Fixed completion requests differ from entire clean typed proposal list')
        if source['requests']:
            require(source_plan['status'] == 'INCOMPLETE_TYPED_METADATA_FRAGMENTS'
                    and not source_plan['invalid'] and not source_plan['unsupported'],
                    'Invalid or unsupported typed parent cannot authorize completion fragments')
        for request in source['requests']:
            proposal = request['proposal']
            require(proposal in source_plan['missing_metadata_fragments']
                    and proposal['source_id'] == cache['source_id'] and proposal['payload_pointer'] is False
                    and proposal['HTTP_authorized'] is False and bool(proposal['typed_parent_evidence']),
                    'Completion proposal is not an exact typed missing metadata fragment')
            requests.append((cache, request, proposal))
    require(0 < len(requests) <= 384 and len(round_entry['requests']) == len(result['requests']) == len(requests),
            'Finite exact completion request inventory differs')
    received = 0
    for (cache, requested, proposal), pins, saved in zip(requests, round_entry['requests'], result['requests']):
        require(pins['request_id'] == requested['request_id'] and pins['source_id'] == cache['source_id'],
                'Completion request order/source differs')
        require(re.fullmatch(r'[A-Za-z0-9_]+', pins['request_id']), 'Safe fixed completion request identifier required')
        base = scope['output_directory'].rstrip('/') + '/' + pins['request_id'] + '/'
        require(pins['GET_receipt_pin']['path'] == base + 'GET_RECEIPT.json'
                and pins['fragment_pin']['path'] == base + 'FRAGMENT.bin', 'Completion cache path differs')
        get = read_json(pins['GET_receipt_pin'], admitted)
        require(saved['request_receipt_pin'] == pins['GET_receipt_pin']
                and {k: v for k, v in saved.items() if k != 'request_receipt_pin'} == get,
                'Completion result/GET receipt join differs')
        offset, length = proposal['offset'], proposal['length']
        require(type(offset) is int and type(length) is int and 0 < length <= 65536
                and 0 <= offset <= cache['file_size'] - length
                and len(cache['cache_ranges']) < MAX_RANGES_PER_SOURCE
                and sum(len(raw) for start, raw, pin in cache['cache_ranges']) + length <= MAX_CACHE_BYTES_PER_SOURCE
                and all(offset + length <= start or start + len(raw) <= offset for start, raw, pin in cache['cache_ranges']),
                'Completion range overlaps retained bytes or exceeds typed bounds')
        proposal_sha = sha(json.dumps(proposal, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
        require(get['source_id'] == cache['source_id'] and get['url'] == get['final_url'] == cache['url']
                and get['method'] == 'GET' and get['attempt'] == 1 and get['status'] == 206
                and get['state'] == 'PASS_EXACT_TYPED_METADATA_FRAGMENT_RETAINED'
                and get['offset'] == offset and get['original_expected_length'] == length
                and get['requested_interval_half_open'] == [offset, offset + length]
                and get['source_file_bytes'] == cache['file_size'] and get['etag'] == cache['etag']
                and get['proposal_sha256'] == proposal_sha and get['retained_fragment'] == pins['fragment_pin']
                and get['body_bytes_returned_to_application'] == pins['fragment_pin']['bytes'] == length
                and get['request_headers'] == {'Accept-Encoding': 'identity', 'Range': f'bytes={offset}-{offset + length - 1}', 'If-Match': cache['etag']}
                and get['response_headers']['Content-Range'] == f'bytes {offset}-{offset + length - 1}/{cache["file_size"]}'
                and get['response_headers']['Content-Length'] == str(length)
                and get['response_headers']['ETag'] == cache['etag'], 'Completion exact 206/range/ETag/body provenance differs')
        identity_encoding(get)
        body = read_pin(pins['fragment_pin'], admitted)
        cache['cache_ranges'].append((offset, body, pins['fragment_pin']))
        received += length
    require(result['application_BODY_bytes_received'] == result['application_BODY_charged_upper_bound_bytes'] == received,
            'Closed completion BODY accounting differs')


def admit_cache_history(scope, admitted):
    config = scope['cache_admission']
    require(config['schema'] == SCHEMA, 'Exact generic cache-admission schema required')
    manifest = read_json(config['source_manifest_pin'], admitted)
    require(manifest['schema'] == config['source_manifest_schema'] and len(manifest['files']) == 6
            and [x['ordered_index'] for x in manifest['files']] == list(range(1, 7))
            and len({x['source_id'] for x in manifest['files']}) == len({x['url'] for x in manifest['files']}) == 6,
            'Exactly six unique ordered frozen source identities required')
    caches = admit_initial(config, manifest, admitted)
    rounds = config['completion_rounds']
    require(isinstance(rounds, list) and len(rounds) <= 16, 'Finite completion history bound exceeded')
    for i, round_entry in enumerate(rounds):
        append_completion(round_entry, caches, admitted, config, rounds[:i])
    for cache in caches:
        require(len(cache['cache_ranges']) <= MAX_RANGES_PER_SOURCE
                and sum(len(raw) for offset, raw, pin in cache['cache_ranges']) <= MAX_CACHE_BYTES_PER_SOURCE,
                'Admitted cache extent/count bound exceeded')
        cache['cache_ranges'].sort(key=lambda x: x[0])
    return caches
