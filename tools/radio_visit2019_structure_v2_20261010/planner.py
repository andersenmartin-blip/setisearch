#!/usr/bin/env python3
"""One cached-prefix typed-structure plan; no network or source-value API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_structure_v2_20261010'
SCHEMA = 'SETI_VISIT2019_TYPED_STRUCTURE_PLAN_SCOPE_V2'
SHARED_ROOTS = [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6']
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 4194304, 'shared_workspace_bytes': 12884901888}
STATUSES = ('COMPLETE_SUPPORTED_HEADER_STRUCTURE', 'INCOMPLETE_TYPED_METADATA_FRAGMENTS',
            'UNSUPPORTED_FORMAT', 'INVALID_METADATA')
START = time.monotonic()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative_path(value):
    p = Path(value)
    require(isinstance(value, str) and p.parts and not p.is_absolute()
            and '..' not in p.parts, 'Expected ROOT-relative path without traversal')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents, 'Noncanonical or escaped ROOT path')
    return p


def read_pin(pin, admitted):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and pin['bytes'] >= 0 and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']), 'Bad pin schema')
    p = relative_path(pin['path'])
    require(not p.is_symlink() and stat.S_ISREG(p.stat().st_mode), 'Expected regular pinned file')
    raw = p.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'File byte pin changed')
    require(pin['path'] not in admitted or admitted[pin['path']] == pin, 'Conflicting pin')
    admitted[pin['path']] = dict(pin)
    return raw


def expected_file(path, digest, admitted):
    p = relative_path(path)
    return read_pin({'path': path, 'bytes': p.stat().st_size, 'sha256': digest}, admitted)


def pinned_json(pin, admitted):
    return json.loads(read_pin(pin, admitted))


def tree_bytes(root):
    total = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(parent) / name
            info = p.lstat()
            if not stat.S_ISDIR(info.st_mode):
                total += info.st_size
        dirs[:] = [n for n in dirs if not (Path(parent) / n).is_symlink()]
    return total


def usage():
    value = {'process_CPU_seconds_including_imports': time.process_time(),
             'wall_seconds_since_module_start': time.monotonic() - START,
             'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(value['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and value['wall_seconds_since_module_start'] <= LIMITS['wall_seconds']
            and value['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Measured resource cap exceeded')
    return value


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, value, reserve=131072):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(tree_bytes(path.parent) + len(raw) + reserve <= LIMITS['output_bytes'], 'Output serialization exceeds reservation')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)


def admission(scope, admitted):
    INITIAL = scope['initial_family']
    require(re.fullmatch(r'radio_visit2019_s[0-9]+_blc[0-9]+_headers_20261010', INITIAL),
            'New separately admitted transport family required; lost BLC66 is forbidden')
    manifest = pinned_json(scope['source_id_manifest_pin'], admitted)
    require(scope['source_id_manifest_pin']['path'] == 'tools/' + INITIAL + '/SIX_SOURCE_IDENTITIES.json'
            and manifest['family_id'] == INITIAL
            and re.fullmatch(r'SETI_VISIT2019_SESSION[0-9]+_BLC[0-9]+_EXACT_SIX_SOURCE_IDENTITIES_V1', manifest['schema']),
            'Frozen exact-six transport manifest required')
    original = pinned_json(scope['initial_scope_pin'], admitted)
    execution = pinned_json(scope['initial_execution_pin'], admitted)
    result = pinned_json(scope['initial_header_result_pin'], admitted)
    require(scope['initial_scope_pin']['path'] == 'tools/' + INITIAL + '/initial_scope.json'
            and scope['initial_execution_pin']['path'] == 'results/' + INITIAL + '/initial/EXECUTION_RECEIPT.json'
            and scope['initial_header_result_pin']['path'] == 'results/' + INITIAL + '/initial/HEADER_RESULT.json', 'Initial paths differ')
    require(original['schema'] == 'SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_SCOPE_V1'
            and original['sources'] == manifest['files'] and len(manifest['files']) == 6,
            'Initial scope/manifest differs')
    require(original['candidate_metadata_path'] == scope['source_id_manifest_pin']['path']
            and original['candidate_metadata_sha256'] == scope['source_id_manifest_pin']['sha256'], 'Initial identities differ')
    expected_file(original['wrapper_path'], original['wrapper_sha256'], admitted)
    require(relative_path(original['wrapper_path']).parent == ROOT / 'tools' / INITIAL, 'Initial code namespace differs')
    require(execution['status'] == result['status'] and result['status'] in (
        'COMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_VALUES_ADMISSION',), 'Initial prefix phase not admitted')
    require(result['schema'] == 'SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_RESULT_V1'
            and result['all_six_exact_prefix_pairs_complete'] is True
            and execution['HEADER_RESULT_sha256'] == scope['initial_header_result_pin']['sha256']
            and execution['resource_caps_satisfied'] is True and execution['no_retry'] is True,
            'Initial execution/result/resource binding differs')
    for value in (execution, result):
        require(value['scope_sha256'] == scope['initial_scope_pin']['sha256']
                and value['wrapper_sha256'] == original['wrapper_sha256']
                and value['source_public_freeze_commit'] == execution['source_public_freeze_commit']
                and value['root_admission_sha256'] == execution['root_admission_sha256'], 'Initial provenance differs')
    require(re.fullmatch(r'[0-9a-f]{40}', execution['source_public_freeze_commit']), 'Initial public freeze missing')
    require(original['root_admission_path'] == 'results/' + INITIAL + '/ROOT_ADMISSION.json', 'Root admission path differs')
    root = json.loads(expected_file(original['root_admission_path'], execution['root_admission_sha256'], admitted))
    require(root['schema'] == scope['initial_root_admission_schema']
            and root['status'] == 'PASS_FINITE_PREFIX_ONLY_NO_REPLAY_ROOT_ADMISSION'
            and root['scope_sha256'] == scope['initial_scope_pin']['sha256']
            and root['wrapper_sha256'] == original['wrapper_sha256']
            and root['source_public_freeze_commit'] == execution['source_public_freeze_commit'], 'Initial root join differs')
    prefix_bytes = original['prefix_bytes']
    require(type(prefix_bytes) is int and 4096 <= prefix_bytes <= 65536 and prefix_bytes % 512 == 0
            and prefix_bytes == scope['cache_prefix_bytes'], 'Frozen transport prefix extent differs')
    require(result['candidate_metadata_sha256'] == scope['source_id_manifest_pin']['sha256'] and result['HEAD_requests_attempted'] == 6
            and result['prefix_GET_requests_attempted'] == 6 and len(result['sources']) == 6
            and result['application_BODY_bytes_received'] == result['application_BODY_charged_upper_bound_bytes'] == 6 * prefix_bytes
            and result['root_reservation_verified'] is True and result['spectral_values_read'] is False
            and result['dataset_value_API_used'] is False
            and all(result[k] == 0 for k in ('retries', 'redirects', 'metadata_followup_requests'))
            and result['geometry'] is None and result['midpoint'] is None, 'Initial prefix completeness differs')
    require(len(scope['sources']) == 6
            and len({v['source_id'] for v in scope['sources']}) == 6
            and len({v['url'] for v in scope['sources']}) == 6
            and [v['ordered_index'] for v in scope['sources']] == list(range(1, 7)),
            'Exactly six unique ordered initial prefixes required')
    sizes = []
    for entry, identity, saved in zip(scope['sources'], manifest['files'], result['sources']):
        require(all(entry[k] == identity[k] == saved[k] for k in ('source_id', 'url', 'ordered_index')), 'Source order/identity differs')
        base = 'results/' + INITIAL + '/initial/' + entry['source_id'] + '/'
        for key, name in (('HEAD_receipt_pin', 'HEAD_RECEIPT.json'), ('PREFIX_receipt_pin', 'PREFIX_RECEIPT.json'),
                          ('HEADER_receipt_pin', 'HEADER_RECEIPT.json'), ('prefix_pin', 'PREFIX.bin')):
            require(entry[key]['path'] == base + name, 'Initial source file path differs')
        head = pinned_json(entry['HEAD_receipt_pin'], admitted)
        get = pinned_json(entry['PREFIX_receipt_pin'], admitted)
        header = pinned_json(entry['HEADER_receipt_pin'], admitted)
        require(header == saved and header['HEAD'] == head and header['prefix_GET'] == get
                and header['retained_prefix'] == entry['prefix_pin'] and entry['prefix_pin']['bytes'] == prefix_bytes
                and header['prefix_BODY_bytes_received'] == prefix_bytes and header['spectral_values_read'] is False
                and header['dataset_value_API_used'] is False,
                'Retained prefix/header receipt join differs')
        for record, method in ((head, 'HEAD'), (get, 'GET')):
            require(record['source_id'] == entry['source_id'] and record['url'] == record['final_url'] == entry['url']
                    and record['method'] == method and record['attempt'] == 1, 'Exact source request identity differs')
        size, etag = head['source_file_bytes'], head['etag']
        require(type(size) is int and size >= prefix_bytes and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', etag)
                and head['state'] == 'PASS_HEAD_METADATA_PIN' and head['status'] == 200
                and head['request_headers'] == {'Accept-Encoding': 'identity'}
                and head['body_bytes_returned_to_application'] == head['BODY_reserved_upper_bound_bytes'] == 0
                and head['response_headers']['Content-Length'] == str(size)
                and head['response_headers']['ETag'] == etag, 'HEAD size/strong ETag differs')
        require(get['state'] == 'PASS_EXACT_' + str(prefix_bytes) + '_PREFIX_RETAINED' and get['status'] == 206
                and get['body_bytes_returned_to_application'] == get['BODY_reserved_upper_bound_bytes'] == prefix_bytes
                and get['request_headers'] == {'Accept-Encoding': 'identity', 'Range': 'bytes=0-' + str(prefix_bytes - 1), 'If-Match': etag}
                and get['response_headers']['Content-Range'] == 'bytes 0-' + str(prefix_bytes - 1) + '/' + str(size)
                and get['response_headers']['Content-Length'] == str(prefix_bytes)
                and get['response_headers']['ETag'] == etag, 'Prefix exact 206/range/ETag differs')
        require(all((r['response_headers'].get('Content-Encoding') or 'identity').lower() == 'identity'
                    for r in (head, get)), 'Encoded response provenance forbidden')
        sizes.append(size)
    return sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--root-go-after-public-freeze', action='store_true')
    args = parser.parse_args()
    require(args.root_go_after_public_freeze and re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit)
            and re.fullmatch(r'[0-9a-f]{64}', args.expected_scope_sha256), 'Exact root freeze/GO required')
    def deadline(signum, frame):
        raise TimeoutError('Typed planner resource deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (19, 20))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, int(LIMITS['wall_seconds'] - (time.monotonic() - START))))
    admitted = {}
    path = Path(args.scope)
    require(path.is_absolute() and path.resolve() == path and ROOT / 'tools' / FAMILY in path.parents, 'Scope path differs')
    scope = json.loads(expected_file(str(path.relative_to(ROOT)), args.expected_scope_sha256, admitted))
    require(scope['schema'] == SCHEMA and scope['script_sha256'] == sha(Path(__file__).read_bytes())
            and scope['limits'] == LIMITS and scope['shared_workspace_roots'] == SHARED_ROOTS, 'Scope/code/caps differ')
    expected_file(str(Path(__file__).relative_to(ROOT)), scope['script_sha256'], admitted)
    parser_raw = expected_file('tools/' + FAMILY + '/structure.py', scope['parser_sha256'], admitted)
    for name, pin in scope['pinned_provenance_dependencies'].items():
        require(name == pin['path'], 'Dependency key/path differs')
        read_pin(pin, admitted)
    out = relative_path(scope['output_directory'])
    require(ROOT / 'results' / FAMILY in out.parents and out.parent.is_dir(), 'Output namespace differs')
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    save_new(out / 'PLAN_STARTED_ONCE.json', {'status': 'STARTED_ONCE_NO_RETRY', 'scope_sha256': args.expected_scope_sha256,
             'public_freeze_commit': args.freeze_commit, 'family_id': FAMILY})
    committed = False
    try:
        require(sum(tree_bytes(r) for r in SHARED_ROOTS) + LIMITS['output_bytes'] <= LIMITS['shared_workspace_bytes'], 'Shared reservation fails')
        free = os.statvfs(out)
        require(free.f_bavail * free.f_frsize >= LIMITS['output_bytes'], 'Output free-space reservation fails')
        sizes = admission(scope, admitted)
        module = types.ModuleType('_frozen_visit2019_structure')
        module.__file__ = str(ROOT / 'tools' / FAMILY / 'structure.py')
        sys.modules[module.__name__] = module
        exec(compile(parser_raw, module.__file__, 'exec'), module.__dict__)
        plans = []
        for entry, size in zip(scope['sources'], sizes):
            prefix = read_pin(entry['prefix_pin'], admitted)
            require(len(prefix) == scope['cache_prefix_bytes'], 'Retained prefix size differs')
            cache = module.MetadataCache([(0, prefix, entry['prefix_pin'])], size)
            plan = module.plan_source(entry['source_id'], cache, size)
            require(plan['source_id'] == entry['source_id'] and plan['status'] in STATUSES
                    and plan['spectral_values_read'] is False and plan['HTTP_requests'] == plan['payload_ranges_proposed'] == 0,
                    'Parser returned nonmetadata or unrecognized plan')
            plans.append(plan)
            usage()
        status = max((x['status'] for x in plans), key=STATUSES.index)
        save_new(out / 'PLAN_RESULT.json', {'family_id': FAMILY, 'status': status, 'sources': plans,
                 'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
                 'whole_header_or_science_qualification': False, 'chunk_index_traversed': False,
                 'HTTP_requests': 0, 'spectral_values_read': False})
        for pin in list(admitted.values()):
            read_pin(pin, admitted)
        require(tree_bytes(out) + 65536 <= LIMITS['output_bytes']
                and sum(tree_bytes(r) for r in SHARED_ROOTS) + 65536 <= LIMITS['shared_workspace_bytes'], 'Final disk cap fails')
        terminal = {'status': 'COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION', 'structure_status': status,
                    'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
                    'parser_sha256': scope['parser_sha256'], 'public_freeze_commit': args.freeze_commit,
                    'PLAN_RESULT_sha256': sha((out / 'PLAN_RESULT.json').read_bytes()), 'input_pins': list(admitted.values()),
                    'all_input_end_readbacks_exact': True, 'HTTP_requests': 0, 'spectral_values_read': False,
                    'resource_caps_satisfied': True, 'limits': LIMITS, 'measured_resources_before_terminal_serialization': usage()}
        prepared = out / 'EXECUTION_RECEIPT.json.prepared'
        save_new(prepared, terminal)
        require(prepared.stat().st_size <= 65536, 'Terminal serialization exceeds reservation')
        require(tree_bytes(out) + prepared.stat().st_size <= LIMITS['output_bytes']
                and sum(tree_bytes(r) for r in SHARED_ROOTS) + prepared.stat().st_size <= LIMITS['shared_workspace_bytes'], 'Publication disk cap fails')
        usage()
        os.link(prepared, out / 'EXECUTION_RECEIPT.json')
        committed = True
        fsync_dir(out)
        prepared.unlink()
        fsync_dir(out)
    except BaseException as error:
        if not committed:
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'FAILED_CLOSED_TYPED_STRUCTURE_PLAN_NO_RETRY',
                     'error_type': type(error).__name__, 'error': str(error)[:2048], 'scope_sha256': args.expected_scope_sha256}, reserve=0)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
