#!/usr/bin/env python3
"""One cache-only qualification of six scope-frozen 2019 HDF5 headers."""
import time
START = time.monotonic()
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
import types

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_blc66_metadata_20261010'
SCHEMA = 'SETI_VISIT2019_SIX_HEADER_CACHE_QUALIFICATION_SCOPE_V2'
CORE_PATH = 'tools/' + FAMILY + '/metadata_with_types.py'
SHARED_ROOTS = [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6']
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 4194304, 'shared_workspace_bytes': 12884901888}
RESOURCE_LIMIT_HIT = False


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative_path(value):
    require(isinstance(value, str), 'ROOT-relative path string required')
    path = Path(value)
    require(path.parts and not path.is_absolute() and '..' not in path.parts,
            'ROOT-relative path without traversal required')
    path = ROOT / path
    require(path.resolve() == path and ROOT in path.parents, 'Noncanonical or escaped ROOT path')
    return path


def read_pin(pin, admitted):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and 0 <= pin['bytes'] <= 4 * 1024 ** 2
            and isinstance(pin['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']),
            'Exact bounded file pin required')
    path = relative_path(pin['path'])
    require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Regular pinned file required')
    require(path.stat().st_size == pin['bytes'], 'Pinned file length changed')
    raw = path.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned file bytes changed')
    require(pin['path'] not in admitted or admitted[pin['path']] == pin, 'Conflicting input pin')
    admitted[pin['path']] = dict(pin)
    return raw


def read_json(pin, admitted):
    return json.loads(read_pin(pin, admitted))


def tree_bytes(root):
    total = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(parent) / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                total += info.st_size
        dirs[:] = [n for n in dirs if not (Path(parent) / n).is_symlink()]
    return total


def usage():
    measured = {'process_CPU_seconds_including_imports': time.process_time(),
                'wall_seconds_since_module_start': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(not RESOURCE_LIMIT_HIT and measured['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and measured['wall_seconds_since_module_start'] <= LIMITS['wall_seconds']
            and measured['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Measured metadata resource cap exceeded')
    return measured


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, value, reserve=131072):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= LIMITS['output_bytes'] and tree_bytes(path.parent) + len(raw) + reserve <= LIMITS['output_bytes'],
            'Bounded qualification output reservation exceeded')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)


def frozen_module(name, source_path, raw):
    module = types.ModuleType(name)
    module.__file__ = str(relative_path(source_path))
    sys.modules[name] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def complete_plan_admission(scope, admitted):
    history = read_json(scope['cache_history_scope_pin'], admitted)
    result = read_json(scope['last_complete_planner_result_pin'], admitted)
    execution = read_json(scope['last_complete_planner_execution_pin'], admitted)
    require(history['script_sha256'] == scope['last_complete_planner_worker_pin']['sha256']
            and history['parser_sha256'] == scope['typed_parser_pin']['sha256'],
            'Last complete planner source identities differ')
    require(result['scope_sha256'] == execution['scope_sha256'] == scope['cache_history_scope_pin']['sha256']
            and execution['script_sha256'] == scope['last_complete_planner_worker_pin']['sha256']
            and execution['parser_sha256'] == scope['typed_parser_pin']['sha256']
            and execution['PLAN_RESULT_sha256'] == scope['last_complete_planner_result_pin']['sha256']
            and result['public_freeze_commit'] == execution['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', execution['public_freeze_commit']),
            'Actual last planner execution/result/scope/source binding differs')
    require(execution['status'] == 'COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION'
            and execution['structure_status'] == result['status'] == 'COMPLETE_SUPPORTED_HEADER_STRUCTURE'
            and execution['all_input_end_readbacks_exact'] is execution['resource_caps_satisfied'] is True,
            'Actual complete typed plan/resource closure required')
    require(len(result['sources']) == 6
            and all(p['status'] == 'COMPLETE_SUPPORTED_HEADER_STRUCTURE'
                    and p['HTTP_requests'] == p['payload_ranges_proposed'] == 0
                    and p['spectral_values_read'] is False and not p['missing_metadata_fragments']
                    and not p['invalid'] and not p['unsupported'] for p in result['sources'])
            and result['HTTP_requests'] == execution['HTTP_requests'] == 0
            and result['spectral_values_read'] is execution['spectral_values_read'] is False,
            'Typed plan metadata-only completeness differs')
    read_pin(scope['last_complete_planner_worker_pin'], admitted)
    return history, result, execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    parser.add_argument('--public-freeze-commit', required=True)
    parser.add_argument('--root-go-metadata-only', action='store_true')
    args = parser.parse_args()
    require(args.root_go_metadata_only and re.fullmatch(r'[0-9a-f]{64}', args.expected_scope_sha256)
            and re.fullmatch(r'[0-9a-f]{40}', args.public_freeze_commit), 'Exact frozen metadata-only root GO required')
    require(sys.dont_write_bytecode is True and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
            and os.environ.get('PYTHONPATH') == str(ROOT.parent / 'seti_fullpower_work' / 'deps'),
            'Exact retained dependency path and disabled bytecode writes required')
    def deadline(signum, frame):
        global RESOURCE_LIMIT_HIT
        RESOURCE_LIMIT_HIT = True
        raise TimeoutError('Metadata qualification resource deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (19, 20))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, int(LIMITS['wall_seconds'] - (time.monotonic() - START))))
    admitted = {}
    path = Path(args.scope)
    require(path.is_absolute() and path.resolve() == path and ROOT / 'tools' / FAMILY in path.parents,
            'Fixed qualification scope namespace required')
    scope = read_json({'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                       'sha256': args.expected_scope_sha256}, admitted)
    require(scope['schema'] == SCHEMA and scope['limits'] == LIMITS
            and scope['shared_workspace_roots'] == SHARED_ROOTS
            and scope['script_sha256'] == sha(Path(__file__).read_bytes())
            and scope['metadata_core_pin']['path'] == CORE_PATH
            and relative_path(scope['source_manifest_pin']['path']).name == 'SIX_SOURCE_IDENTITIES.json'
            and ROOT / 'tools' in relative_path(scope['source_manifest_pin']['path']).parents
            and isinstance(scope['source_manifest_schema'], str)
            and scope['source_manifest_schema'].startswith('SETI_VISIT2019_')
            and scope['source_manifest_schema'].endswith('_EXACT_SIX_SOURCE_IDENTITIES_V1'),
            'Qualification scope/code/limits/source identity differs')
    read_pin({'path': str(Path(__file__).relative_to(ROOT)), 'bytes': Path(__file__).stat().st_size,
              'sha256': scope['script_sha256']}, admitted)
    out = relative_path(scope['output_directory'])
    require(ROOT / 'results' / FAMILY in out.parents and out.parent.is_dir(), 'Qualification output namespace differs')
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    save_new(out / 'QUALIFICATION_STARTED_ONCE.json', {'status': 'STARTED_ONCE_NO_RETRY',
             'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256,
             'public_freeze_commit': args.public_freeze_commit, 'HTTP_requests': 0})
    committed = False
    try:
        require(sum(tree_bytes(root) for root in SHARED_ROOTS) + LIMITS['output_bytes'] <= LIMITS['shared_workspace_bytes'],
                'Shared qualification output reservation fails')
        free = os.statvfs(out)
        require(free.f_bavail * free.f_frsize >= LIMITS['output_bytes'], 'Qualification free-space reservation fails')
        history, complete, planner_execution = complete_plan_admission(scope, admitted)
        manifest = read_json(scope['source_manifest_pin'], admitted)
        require(manifest['schema'] == scope['source_manifest_schema']
                and len(manifest['files']) == 6
                and [x['ordered_index'] for x in manifest['files']] == list(range(1, 7))
                and [x['candidate_role'] for x in manifest['files']] == ['ON_CANDIDATE', 'CONTROL_CANDIDATE'] * 3
                and all(re.fullmatch(r'[A-Z0-9_]+', x['source_id']) for x in manifest['files'])
                and len({x['source_id'] for x in manifest['files']}) == len({x['url'] for x in manifest['files']}) == 6
                and scope['cache_admission']['source_manifest_pin'] == scope['source_manifest_pin']
                and scope['cache_admission']['source_manifest_schema'] == scope['source_manifest_schema'], 'Frozen six identity manifest differs')
        loader_raw = read_pin(scope['cache_admission_worker_pin'], admitted)
        structure_raw = read_pin(scope['typed_parser_pin'], admitted)
        core_raw = read_pin(scope['metadata_core_pin'], admitted)
        loader = frozen_module('_visit2019_admitted_cache_history', scope['cache_admission_worker_pin']['path'], loader_raw)
        loader.admit_planner_input_pins(planner_execution, admitted)
        loader.bind_plan_cache_history(history, scope['cache_admission'])
        if history['schema'] != 'SETI_VISIT2019_TYPED_STRUCTURE_PLAN_SCOPE_V2':
            require(history['cache_admission_worker_pin'] == scope['cache_admission_worker_pin'],
                    'Generic parent/cache-loader source pin differs')
        caches = loader.admit_cache_history(scope, admitted)
        require(isinstance(caches, list) and len(caches) == 6, 'Cache admission must return exactly six ordered sources')
        structure = frozen_module('_visit2019_metadata_cache', scope['typed_parser_pin']['path'], structure_raw)
        core = frozen_module('_visit2019_metadata_qualification', CORE_PATH, core_raw)
        require(scope['qualification_rules'] == {
            'ON_pointing_tolerance_degrees': core.ON_POINTING_TOLERANCE_DEGREES,
            'distinct_pointing_minimum_degrees': core.DISTINCT_POINTING_MIN_DEGREES,
            'midpoint_rule': 'floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes',
            'source_values_admission': 'BLOCKED', 'independent_validation_admission': 'BLOCKED'},
            'Frozen metadata-only qualification rules differ')
        # The only native-library import occurs after every limit and byte pin.
        import h5py
        usage()
        records, inventory = [], []
        for identity, entry, plan in zip(manifest['files'], caches, complete['sources']):
            require(all(identity[k] == entry[k] for k in ('source_id', 'url', 'ordered_index'))
                    and plan['source_id'] == identity['source_id'], 'Six-source cache/plan order differs')
            size, spans = entry['file_size'], entry['cache_ranges']
            require(type(size) is int and size >= 96 and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', entry['etag']),
                    'Admitted cache source size/strong ETag differs')
            require(plan['superblock']['absolute_EOF'] == size, 'Typed/source logical size differs')
            require(isinstance(spans, list) and 0 < len(spans) <= 128, 'Finite retained metadata-span inventory required')
            for offset, raw, pin in spans:
                require(type(offset) is int and isinstance(raw, bytes) and read_pin(pin, admitted) == raw,
                        'Cached binary byte provenance differs')
            cache = structure.MetadataCache(spans, size)
            record = core.extract(identity, cache, plan, size, h5py)
            usage()
            record['schema'] = 'SETI_VISIT2019_SOURCE_HEADER_METADATA_V1'
            record['etag'] = entry['etag']
            record['superblock'] = plan['superblock']
            records.append(record)
            inventory.append({'source_id': entry['source_id'], 'source_file_bytes': size,
                              'etag': entry['etag'], 'cache_spans': [
                                  {'offset': offset, 'length': len(raw), 'pin': pin} for offset, raw, pin in spans]})
            save_new(out / (entry['source_id'] + '_HEADER_METADATA.json'), record)
        eligibility = core.qualify(records)
        usage()
        result = {'schema': 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1',
                  'family_id': FAMILY, 'status': eligibility['status'], 'sources': records,
                  'metadata_eligibility': eligibility, 'admitted_cache_inventory': inventory,
                  'last_complete_typed_plan_sha256': scope['last_complete_planner_result_pin']['sha256'],
                  'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
                  'public_freeze_commit': args.public_freeze_commit,
                  'source_values_admission': 'BLOCKED', 'independent_validation_admission': 'BLOCKED',
                  'HTTP_requests': 0, 'spectral_values_read': False, 'dataset_value_API_used': False,
                  'chunk_index_nodes_read': 0, 'codec_invoked': False, 'new_hypothesis_combinations_scored': 0,
                  'whole_telescope_origin_checksum_verified': False}
        save_new(out / 'METADATA_QUALIFICATION_RESULT.json', result)
        for pin in list(admitted.values()):
            read_pin(pin, admitted)
        require(tree_bytes(out) + 65536 <= LIMITS['output_bytes']
                and sum(tree_bytes(root) for root in SHARED_ROOTS) + 65536 <= LIMITS['shared_workspace_bytes'],
                'Final qualification disk cap fails')
        terminal = {'schema': 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1',
                    'status': 'COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION',
                    'metadata_eligibility_status': eligibility['status'], 'family_id': FAMILY,
                    'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
                    'metadata_core_sha256': scope['metadata_core_pin']['sha256'],
                    'cache_admission_worker_sha256': scope['cache_admission_worker_pin']['sha256'],
                    'typed_parser_sha256': scope['typed_parser_pin']['sha256'],
                    'public_freeze_commit': args.public_freeze_commit,
                    'METADATA_QUALIFICATION_RESULT_sha256': sha((out / 'METADATA_QUALIFICATION_RESULT.json').read_bytes()),
                    'input_pins': list(admitted.values()), 'all_input_end_readbacks_exact': True,
                    'HTTP_requests': 0, 'spectral_values_read': False, 'dataset_value_API_used': False,
                    'chunk_index_nodes_read': 0, 'codec_invoked': False,
                    'resource_caps_satisfied': True, 'limits': LIMITS,
                    'measured_resources_before_terminal_serialization': usage()}
        prepared = out / 'EXECUTION_RECEIPT.json.prepared'
        save_new(prepared, terminal)
        require(prepared.stat().st_size <= 65536, 'Qualification terminal receipt exceeds reservation')
        require(tree_bytes(out) + prepared.stat().st_size <= LIMITS['output_bytes']
                and sum(tree_bytes(root) for root in SHARED_ROOTS) + prepared.stat().st_size <= LIMITS['shared_workspace_bytes'],
                'Qualification publication disk cap fails')
        usage()
        os.link(prepared, out / 'EXECUTION_RECEIPT.json')
        committed = True
        fsync_dir(out)
        prepared.unlink()
        fsync_dir(out)
    except BaseException as error:
        if not committed:
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'FAILED_CLOSED_CACHE_ONLY_QUALIFICATION_NO_RETRY',
                     'error_type': type(error).__name__, 'error': str(error)[:2048],
                     'scope_sha256': args.expected_scope_sha256, 'HTTP_requests': 0}, reserve=0)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
