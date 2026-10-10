"""One-shot cache-only TREE1 caller. No HDF5/native imports or HTTP entry point.

All actual execution, scope preparation and root GO remain prospective.
"""
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
FAMILY = 'radio_visit2019_chunk_index_20261010'
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 33554432, 'shared_workspace_bytes': 12884901888}
SHARED_ROOTS = [ROOT.parent, Path('/workspace/scratch/5bf3860dacd6')]
START = time.monotonic()
RESOURCE_LIMIT_HIT = False


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative_path(name):
    path = Path(name)
    require(path.parts and not path.is_absolute() and '..' not in path.parts,
            'Canonical root-relative path required')
    path = ROOT / path
    require(path.resolve() == path and ROOT in path.parents,
            'Pinned input/output path escapes root or traverses a symlink')
    return path


def read_pin(pin, admitted):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and 0 <= pin['bytes'] <= 4 * 1024 ** 2
            and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']),
            'Exact bounded byte pin required')
    path = relative_path(pin['path'])
    require(stat.S_ISREG(path.stat().st_mode) and path.stat().st_size == pin['bytes'],
            'Pinned input is not an exact regular file')
    raw = path.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned input changed')
    require(pin['path'] not in admitted or admitted[pin['path']] == pin,
            'Conflicting input pin declaration')
    admitted[pin['path']] = dict(pin)
    return raw


def read_json(pin, admitted):
    return json.loads(read_pin(pin, admitted))


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    require(len(raw) <= LIMITS['output_bytes'], 'Metadata JSON exceeds finite output bound')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def tree_bytes(path):
    if not path.exists():
        return 0
    total = 0
    for directory, _, names in os.walk(path, followlinks=False):
        for name in names:
            entry = Path(directory) / name
            mode = entry.lstat()
            if stat.S_ISREG(mode.st_mode) or stat.S_ISLNK(mode.st_mode):
                total += mode.st_size
    return total


def usage():
    measured = {'CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(not RESOURCE_LIMIT_HIT and measured['CPU_seconds'] <= LIMITS['CPU_seconds']
            and measured['wall_seconds'] <= LIMITS['wall_seconds']
            and measured['peak_RSS_bytes'] <= LIMITS['memory_bytes'],
            'Measured cache-only TREE1 resource cap exceeded')
    return measured


def frozen_module(name, pin, admitted):
    raw = read_pin(pin, admitted)
    module = types.ModuleType(name)
    module.__file__ = str(relative_path(pin['path']))
    sys.modules[name] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def admit_qualification(scope, admitted, loader):
    q = scope['metadata_qualification']
    qs = read_json(q['scope_pin'], admitted)
    result = read_json(q['result_pin'], admitted)
    execution = read_json(q['execution_pin'], admitted)
    read_pin(q['worker_pin'], admitted)
    require(scope['qualification_result_pin'] == q['result_pin']
            and qs['schema'] == 'SETI_VISIT2019_SIX_HDF_HEADER_CACHE_QUALIFICATION_SCOPE_V3'
            and result['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and execution['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1'
            and result['status'] == execution['metadata_eligibility_status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and execution['status'] == 'COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION'
            and execution['resource_caps_satisfied'] is execution['all_input_end_readbacks_exact'] is True,
            'Actual successful six-header metadata qualification required')
    require(result['scope_sha256'] == execution['scope_sha256'] == q['scope_pin']['sha256']
            and result['script_sha256'] == execution['script_sha256'] == q['worker_pin']['sha256'] == qs['script_sha256']
            and execution['METADATA_QUALIFICATION_RESULT_sha256'] == q['result_pin']['sha256']
            and result['public_freeze_commit'] == execution['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', execution['public_freeze_commit'])
            and qs['cache_admission'] == scope['cache_admission']
            and qs['cache_admission_worker_pin'] == scope['cache_admission_worker_pin']
            and qs['typed_parser_pin'] == scope['typed_parser_pin']
            and qs['source_manifest_pin'] == scope['source_manifest_pin']
            and execution['metadata_core_sha256'] == qs['metadata_core_pin']['sha256']
            and execution['typed_parser_sha256'] == qs['typed_parser_pin']['sha256']
            and execution['cache_admission_worker_sha256'] == qs['cache_admission_worker_pin']['sha256'],
            'Qualification execution/code/cache/source bindings differ')
    require(result['HTTP_requests'] == execution['HTTP_requests'] == 0
            and result['spectral_values_read'] is execution['spectral_values_read'] is False
            and result['dataset_value_API_used'] is execution['dataset_value_API_used'] is False
            and result['chunk_index_nodes_read'] == execution['chunk_index_nodes_read'] == 0
            and result['codec_invoked'] is execution['codec_invoked'] is False,
            'Qualification is not metadata-only')
    loader.admit_planner_input_pins(execution, admitted)
    require(len(result['sources']) == 6 and
            all(r['status'] == 'COMPLETE_HEADER_METADATA_ONLY' for r in result['sources']),
            'Exact six complete source metadata records required')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    parser.add_argument('--public-freeze-commit', required=True)
    parser.add_argument('--root-go-metadata-only', action='store_true')
    args = parser.parse_args()
    require(args.root_go_metadata_only and re.fullmatch(r'[0-9a-f]{64}', args.expected_scope_sha256)
            and re.fullmatch(r'[0-9a-f]{40}', args.public_freeze_commit),
            'Exact prospective freeze and root metadata-only GO required')
    require(sys.dont_write_bytecode and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1',
            'Metadata source imports must not write bytecode')
    def deadline(signum, frame):
        global RESOURCE_LIMIT_HIT
        RESOURCE_LIMIT_HIT = True
        raise TimeoutError('Cache-only TREE1 resource deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 22))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(LIMITS['wall_seconds'])
    scope_path = Path(args.scope)
    require(scope_path.is_absolute() and scope_path.resolve() == scope_path
            and ROOT / 'tools' / FAMILY == scope_path.parent,
            'Exact new TREE1 scope path required')
    scope_pin = {'path': str(scope_path.relative_to(ROOT)), 'bytes': scope_path.stat().st_size,
                 'sha256': args.expected_scope_sha256}
    admitted = {}
    scope = read_json(scope_pin, admitted)
    self_path = Path(__file__)
    self_pin = {'path': str(self_path.relative_to(ROOT)), 'bytes': self_path.stat().st_size,
                'sha256': scope['script_sha256']}
    read_pin(self_pin, admitted)
    require(scope['schema'] == 'SETI_VISIT2019_TYPED_TREE1_PLAN_SCOPE_V1'
            and scope['limits'] == LIMITS and scope['parser_sha256'] == scope['tree_core_pin']['sha256']
            and scope['shared_workspace_roots'] == [str(r) for r in SHARED_ROOTS],
            'TREE1 scope, core or resource contract differs')
    require(any(ROOT == r or r in ROOT.parents for r in SHARED_ROOTS),
            'Actual source root omitted from shared disk accounting')
    out = relative_path(scope['output_directory'])
    require(ROOT / 'results' / FAMILY in out.parents and out.parent.is_dir()
            and any(r in out.parents for r in SHARED_ROOTS), 'New output namespace or disk root differs')
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    committed = False
    try:
        save_new(out / 'TREE1_PLAN_STARTED_ONCE.json', {
            'status': 'STARTED_ONCE_NO_RETRY', 'scope_sha256': args.expected_scope_sha256,
            'public_freeze_commit': args.public_freeze_commit, 'HTTP_requests': 0})
        require(sum(tree_bytes(r) for r in SHARED_ROOTS) + LIMITS['output_bytes'] <= LIMITS['shared_workspace_bytes'],
                'Fresh shared TREE1 output reservation fails')
        disk = os.statvfs(out)
        require(disk.f_bavail * disk.f_frsize >= LIMITS['output_bytes'], 'Fresh physical disk reservation fails')
        for pin in scope['pinned_dependencies']:
            read_pin(pin, admitted)
        loader = frozen_module('_tree1_header_cache_admission', scope['cache_admission_worker_pin'], admitted)
        extension = frozen_module('_tree1_index_cache_admission', scope['tree_cache_admission_worker_pin'], admitted)
        structure = frozen_module('_tree1_authenticated_cache', scope['typed_parser_pin'], admitted)
        core = frozen_module('_tree1_pure_core', scope['tree_core_pin'], admitted)
        qualified = admit_qualification(scope, admitted, loader)
        caches = loader.admit_cache_history(scope, admitted)
        caches = extension.admit_tree_cache_history(scope, admitted, loader, caches)
        identities = scope['sources']
        require(len(caches) == len(identities) == 6
                and [x['ordered_index'] for x in identities] == list(range(1, 7))
                and len({x['source_id'] for x in identities}) == len({x['url'] for x in identities}) == 6,
                'Exact ordered six-source TREE1 inventory required')
        results = []
        for identity, record, entry in zip(identities, qualified['sources'], caches):
            require(all(identity[k] == record[k] == entry[k] for k in ('source_id', 'url', 'ordered_index'))
                    and record['source_file_bytes'] == entry['file_size']
                    and record['etag'] == entry['etag'], 'TREE1 cache/header identity differs')
            spans = entry['cache_ranges']
            for offset, raw, pin in spans:
                require(type(offset) is int and read_pin(pin, admitted) == raw,
                        'TREE1 cache bytes are not authenticated retained fragments')
            cache = structure.MetadataCache(spans, entry['file_size'])
            result = core.plan_source(record, cache)
            result.update(url=identity['url'], ordered_index=identity['ordered_index'],
                          etag=entry['etag'], source_file_bytes=entry['file_size'])
            results.append(result)
            usage()
        status = ('INVALID_METADATA' if any(r['status'] == 'INVALID_METADATA' for r in results) else
                  'UNSUPPORTED_FORMAT' if any(r['status'] == 'UNSUPPORTED_FORMAT' for r in results) else
                  'INCOMPLETE_TYPED_CHUNK_INDEX_METADATA' if any(r['missing_metadata_fragments'] for r in results) else
                  'COMPLETE_SELECTED_SIX_SOURCE_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION')
        result = {'schema': 'SETI_VISIT2019_PURE_TREE1_METADATA_PLAN_RESULT_V1',
            'status': status, 'sources': results,
            'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
            'parser_sha256': scope['parser_sha256'], 'public_freeze_commit': args.public_freeze_commit,
            'qualification_result_pin': scope['qualification_result_pin'],
            'HTTP_requests': 0, 'spectral_values_read': False, 'payload_pointer_followed': False,
            'source_values_admission': 'BLOCKED', 'independent_validation_admission': 'BLOCKED'}
        result_pin = save_new(out / 'PLAN_RESULT.json', result)
        for pin in list(admitted.values()):
            read_pin(pin, admitted)
        manifest_pin = save_new(out / 'INPUT_PINS.json', {
            'schema': 'SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1',
            'input_pins': list(admitted.values()), 'all_input_end_readbacks_exact': True})
        terminal = {'schema': 'SETI_VISIT2019_TREE1_METADATA_PLAN_EXECUTION_V1',
            'status': 'COMPLETE_PURE_TREE1_METADATA_PLAN_CAPTURE_NO_VALUES_ADMISSION',
            'structure_status': status, 'scope_sha256': args.expected_scope_sha256,
            'script_sha256': scope['script_sha256'], 'parser_sha256': scope['parser_sha256'],
            'public_freeze_commit': args.public_freeze_commit, 'PLAN_RESULT_sha256': result_pin['sha256'],
            'input_pins_manifest_pin': manifest_pin, 'all_input_end_readbacks_exact': True,
            'resource_caps_satisfied': True, 'limits': LIMITS,
            'HTTP_requests': 0, 'spectral_values_read': False, 'payload_pointer_followed': False,
            'measured_resources_before_terminal_serialization': usage()}
        prepared = out / 'EXECUTION_RECEIPT.json.prepared'
        save_new(prepared, terminal)
        require(prepared.stat().st_size <= 65536
                and tree_bytes(out) + prepared.stat().st_size <= LIMITS['output_bytes']
                and sum(tree_bytes(r) for r in SHARED_ROOTS) + prepared.stat().st_size <= LIMITS['shared_workspace_bytes'],
                'Final TREE1 output/shared publication reservation fails')
        usage()
        signal.alarm(0)
        os.link(prepared, out / 'EXECUTION_RECEIPT.json')
        committed = True
        fsync_dir(out)
    except BaseException as error:
        if not committed:
            signal.alarm(0)
            save_new(out / 'FAILURE_RECEIPT.json', {
                'status': 'INCOMPLETE_TREE1_PLAN_NO_RETRY',
                'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.public_freeze_commit,
                'error_type': type(error).__name__, 'error': str(error)[:2048],
                'HTTP_requests': 0, 'spectral_values_read': False, 'payload_pointer_followed': False,
                'actual_resources': {'CPU_seconds': time.process_time(),
                    'wall_seconds': time.monotonic() - START,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
