#!/usr/bin/env python3
"""One pure typed-metadata plan from a frozen six-source retained cache history."""
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
FAMILY = 'radio_visit2019_structure_rounds_20261010'
SCHEMA = 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_SCOPE_V1'
LOADER_PATH = 'tools/radio_visit2019_blc66_metadata_20261010/cache_admission.py'
LOADER_SHA = 'c6770d95ddd14bf1437a8798ef896b0fd0ea851b1a87873ed4d2b60570417d73'
PARSER_PATH = 'tools/radio_visit2019_structure_v2_20261010/structure.py'
PARSER_SHA = '5fb4bf41245017ce9780c3e8b5727ff297fdbfaaa7fbe089aab8d53a014bcce8'
SHARED_ROOTS = [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6']
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 4194304, 'shared_workspace_bytes': 12884901888}
STATUSES = ('COMPLETE_SUPPORTED_HEADER_STRUCTURE', 'INCOMPLETE_TYPED_METADATA_FRAGMENTS',
            'UNSUPPORTED_FORMAT', 'INVALID_METADATA')
RESOURCE_LIMIT_HIT = False


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path(name):
    require(isinstance(name, str), 'Repository-relative path string required')
    p = Path(name)
    require(p.parts and not p.is_absolute() and '..' not in p.parts, 'Canonical repository-relative path required')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents, 'Repository path escapes or uses symlinks')
    return p


def read_pin(pin, admitted):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and 0 <= pin['bytes'] <= LIMITS['output_bytes']
            and isinstance(pin['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']),
            'Exact bounded input pin required')
    p = path(pin['path'])
    require(not p.is_symlink() and stat.S_ISREG(p.stat().st_mode) and p.stat().st_size == pin['bytes'],
            'Pinned regular file or size changed')
    raw = p.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Pinned input bytes changed')
    require(pin['path'] not in admitted or admitted[pin['path']] == pin, 'Conflicting input pin')
    admitted[pin['path']] = dict(pin)
    return raw


def tree_bytes(root):
    total = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            info = (Path(parent) / name).lstat()
            if not stat.S_ISDIR(info.st_mode):
                total += info.st_size
        dirs[:] = [n for n in dirs if not (Path(parent) / n).is_symlink()]
    return total


def usage():
    u = {'process_CPU_seconds_including_imports': time.process_time(),
         'wall_seconds_since_module_start': time.monotonic() - START,
         'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(not RESOURCE_LIMIT_HIT and u['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and u['wall_seconds_since_module_start'] <= LIMITS['wall_seconds']
            and u['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Measured planner resource cap exceeded')
    return u


def fsync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(p, value, reserve=131072):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= LIMITS['output_bytes']
            and tree_bytes(p.parent) + len(raw) + reserve <= LIMITS['output_bytes'],
            'Bounded planner output reservation exceeded')
    with p.open('xb') as h:
        h.write(raw)
        h.flush()
        os.fsync(h.fileno())
    fsync_dir(p.parent)
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def frozen_module(name, pin, admitted):
    raw = read_pin(pin, admitted)
    m = types.ModuleType(name)
    m.__file__ = str(path(pin['path']))
    sys.modules[name] = m
    exec(compile(raw, m.__file__, 'exec'), m.__dict__)
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope', required=True)
    p.add_argument('--expected-scope-sha256', required=True)
    p.add_argument('--public-freeze-commit', required=True)
    p.add_argument('--root-go-metadata-only', action='store_true')
    args = p.parse_args()
    require(args.root_go_metadata_only and re.fullmatch(r'[0-9a-f]{64}', args.expected_scope_sha256)
            and re.fullmatch(r'[0-9a-f]{40}', args.public_freeze_commit), 'Exact public scope freeze and root GO required')
    require(sys.dont_write_bytecode is True and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1',
            'Disabled bytecode writes required')
    def deadline(signum, frame):
        global RESOURCE_LIMIT_HIT
        RESOURCE_LIMIT_HIT = True
        raise TimeoutError('Typed round planner resource deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (19, 20))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, int(LIMITS['wall_seconds'] - (time.monotonic() - START))))
    admitted = {}
    scope_path = Path(args.scope)
    require(scope_path.is_absolute() and scope_path.resolve() == scope_path
            and scope_path.parent == ROOT / 'tools' / FAMILY / 'scopes', 'Exact new round scope namespace required')
    scope = json.loads(read_pin({'path': str(scope_path.relative_to(ROOT)), 'bytes': scope_path.stat().st_size,
                                'sha256': args.expected_scope_sha256}, admitted))
    require(scope['schema'] == SCHEMA and scope['limits'] == LIMITS
            and scope['shared_workspace_roots'] == SHARED_ROOTS
            and re.fullmatch(r'round_[0-9]{2}', scope['round_id']) and 1 <= int(scope['round_id'][-2:]) <= 16
            and scope_path.name == scope['round_id'] + '.json'
            and scope['script_sha256'] == sha(Path(__file__).read_bytes())
            and scope['cache_admission_worker_pin']['path'] == LOADER_PATH
            and scope['cache_admission_worker_pin']['sha256'] == LOADER_SHA
            and scope['parser_pin']['path'] == PARSER_PATH
            and scope['parser_pin']['sha256'] == scope['parser_sha256'] == PARSER_SHA
            and scope['source_manifest_pin'] == scope['cache_admission']['source_manifest_pin']
            and scope['source_manifest_schema'] == scope['cache_admission']['source_manifest_schema'],
            'Frozen round scope/source/cache/limits differ')
    read_pin({'path': str(Path(__file__).relative_to(ROOT)), 'bytes': Path(__file__).stat().st_size,
              'sha256': scope['script_sha256']}, admitted)
    require(isinstance(scope['additional_dependency_pins'], list) and len(scope['additional_dependency_pins']) <= 128
            and all(Path(pin['path']).suffix in ('.py', '.json', '.md') for pin in scope['additional_dependency_pins']),
            'Only finite UTF8 source/metadata proofs may be additional inputs')
    for pin in scope['additional_dependency_pins']:
        read_pin(pin, admitted)
    out = path(scope['output_directory'])
    require(out == ROOT / 'results' / FAMILY / scope['round_id'] and out.parent.is_dir(),
            'Exact create-only round output directory required')
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    save_new(out / 'PLAN_STARTED_ONCE.json', {'status': 'STARTED_ONCE_NO_RETRY', 'HTTP_requests': 0,
             'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.public_freeze_commit})
    committed = False
    try:
        require(sum(tree_bytes(x) for x in SHARED_ROOTS) + LIMITS['output_bytes'] <= LIMITS['shared_workspace_bytes'],
                'Shared planner output reservation exceeded')
        free = os.statvfs(out)
        require(free.f_bavail * free.f_frsize >= LIMITS['output_bytes'], 'Planner free-space reservation fails')
        loader = frozen_module('_frozen_visit2019_round_cache', scope['cache_admission_worker_pin'], admitted)
        manifest = loader.read_json(scope['source_manifest_pin'], admitted)
        require(manifest['schema'] == scope['source_manifest_schema'] and len(manifest['files']) == 6
                and scope['sources'] == [{k: x[k] for k in ('source_id', 'url', 'ordered_index')} for x in manifest['files']],
                'Exact six-source manifest/order differs')
        caches = loader.admit_cache_history(scope, admitted)
        parser = frozen_module('_frozen_visit2019_round_parser', scope['parser_pin'], admitted)
        require(len(caches) == 6, 'Cache loader must preserve all six sources')
        plans, inventory = [], []
        for identity, cache_entry in zip(scope['sources'], caches):
            require(all(identity[k] == cache_entry[k] for k in ('source_id', 'url', 'ordered_index')),
                    'Actual admitted cache source order differs')
            cache = parser.MetadataCache(cache_entry['cache_ranges'], cache_entry['file_size'])
            plan = parser.plan_source(identity['source_id'], cache, cache_entry['file_size'])
            require(plan['source_id'] == identity['source_id'] and plan['status'] in STATUSES
                    and plan['HTTP_requests'] == plan['payload_ranges_proposed'] == 0
                    and plan['spectral_values_read'] is False, 'Pure parser returned nonmetadata plan')
            plans.append(plan)
            inventory.append({'source_id': identity['source_id'], 'source_file_bytes': cache_entry['file_size'],
                              'etag': cache_entry['etag'], 'cache_spans': [
                                  {'offset': a, 'length': len(b), 'pin': pin} for a, b, pin in cache_entry['cache_ranges']]})
            usage()
        structure_status = max((x['status'] for x in plans), key=STATUSES.index)
        result_pin = save_new(out / 'PLAN_RESULT.json', {
            'schema': 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_RESULT_V1', 'family_id': FAMILY,
            'round_id': scope['round_id'], 'status': structure_status, 'sources': plans,
            'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.public_freeze_commit,
            'admitted_cache_inventory': inventory, 'whole_header_or_science_qualification': False,
            'chunk_index_traversed': False, 'HTTP_requests': 0, 'spectral_values_read': False,
            'dataset_value_API_used': False, 'source_values_admission': 'BLOCKED',
            'independent_validation_admission': 'BLOCKED'})
        require(0 < len(admitted) <= 4096, 'Finite input pin inventory exceeded')
        for pin in list(admitted.values()):
            read_pin(pin, admitted)
        inputs_pin = save_new(out / 'INPUT_PINS.json', {
            'schema': 'SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1', 'input_pins': list(admitted.values())})
        require(tree_bytes(out) + 65536 <= LIMITS['output_bytes']
                and sum(tree_bytes(x) for x in SHARED_ROOTS) + 65536 <= LIMITS['shared_workspace_bytes'],
                'Final planner disk cap exceeded')
        terminal = {'schema': 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_EXECUTION_V1',
                    'status': 'COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION',
                    'structure_status': structure_status, 'family_id': FAMILY, 'round_id': scope['round_id'],
                    'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
                    'parser_sha256': scope['parser_sha256'], 'public_freeze_commit': args.public_freeze_commit,
                    'PLAN_RESULT_sha256': result_pin['sha256'], 'input_pins_manifest_pin': inputs_pin,
                    'all_input_end_readbacks_exact': True, 'HTTP_requests': 0, 'spectral_values_read': False,
                    'dataset_value_API_used': False, 'chunk_index_traversed': False,
                    'resource_caps_satisfied': True, 'limits': LIMITS,
                    'measured_resources_before_terminal_serialization': usage()}
        prepared = out / 'EXECUTION_RECEIPT.json.prepared'
        save_new(prepared, terminal, reserve=65536)
        require(prepared.stat().st_size <= 65536, 'Planner terminal receipt cap exceeded')
        require(tree_bytes(out) + prepared.stat().st_size <= LIMITS['output_bytes']
                and sum(tree_bytes(x) for x in SHARED_ROOTS) + prepared.stat().st_size <= LIMITS['shared_workspace_bytes'],
                'Planner terminal publication disk cap exceeded')
        usage()
        os.link(prepared, out / 'EXECUTION_RECEIPT.json')
        committed = True
        fsync_dir(out)
        prepared.unlink()
        fsync_dir(out)
    except BaseException as error:
        if not committed:
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'FAILED_CLOSED_TYPED_ROUND_PLAN_NO_RETRY',
                     'error_type': type(error).__name__, 'error': str(error)[:2048],
                     'scope_sha256': args.expected_scope_sha256, 'HTTP_requests': 0}, reserve=0)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
