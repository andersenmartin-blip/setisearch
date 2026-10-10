#!/usr/bin/env python3
"""Create one round scope from JSON/code and binary-file stats; no binary reads."""
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

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_structure_rounds_20261010'
LOADER = 'tools/radio_visit2019_blc66_metadata_20261010/cache_admission.py'
LOADER_SHA = 'c6770d95ddd14bf1437a8798ef896b0fd0ea851b1a87873ed4d2b60570417d73'
PARSER = 'tools/radio_visit2019_structure_v2_20261010/structure.py'
PARSER_SHA = '5fb4bf41245017ce9780c3e8b5727ff297fdbfaaa7fbe089aab8d53a014bcce8'
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 4194304, 'shared_workspace_bytes': 12884901888}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path(name):
    require(isinstance(name, str), 'Repository-relative path string required')
    p = Path(name)
    require(p.parts and not p.is_absolute() and '..' not in p.parts, 'Repository-relative path required')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents and not p.is_symlink()
            and stat.S_ISREG(p.stat().st_mode), 'Canonical regular metadata or binary-stat path required')
    return p


def file_pin(name):
    require(Path(name).suffix in ('.py', '.json', '.md'), 'Only UTF8 source/metadata files may be opened')
    p = path(name)
    require(p.stat().st_size <= 4194304, 'Metadata input size bound exceeded')
    raw = p.read_bytes()
    raw.decode('utf-8')
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}


def read_json_pin(pin):
    require(Path(pin['path']).suffix == '.json', 'JSON metadata pin required')
    raw = path(pin['path']).read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'JSON bytes changed before interpretation')
    return json.loads(raw)


def validate_inventory(value, metadata, binary_stats):
    if isinstance(value, dict):
        if set(value) == {'path', 'bytes', 'sha256'}:
            require(type(value['bytes']) is int and 0 <= value['bytes'] <= 4194304
                    and isinstance(value['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', value['sha256']),
                    'Exact bounded nested pin required')
            p = path(value['path'])
            if p.suffix.lower() == '.bin':
                require(p.stat().st_size == value['bytes'], 'Declared retained binary size differs')
                binary_stats[value['path']] = dict(value)
            else:
                require(file_pin(value['path']) == value, 'Source/metadata pin changed')
                metadata[value['path']] = dict(value)
        else:
            for child in value.values():
                validate_inventory(child, metadata, binary_stats)
    elif isinstance(value, list):
        for child in value:
            validate_inventory(child, metadata, binary_stats)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--expected-config-sha256', required=True)
    p.add_argument('--root-go-source-only-scope', action='store_true')
    args = p.parse_args()
    require(args.root_go_source_only_scope and re.fullmatch(r'[0-9a-f]{64}', args.expected_config_sha256),
            'Exact root metadata-only scope preparation GO required')
    def deadline(signum, frame):
        raise TimeoutError('Metadata-only round scope preparation deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (9, 10))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    signal.alarm(max(1, int(30 - (time.monotonic() - START))))
    cp = Path(args.config)
    require(cp.is_absolute() and cp.resolve() == cp and ROOT in cp.parents and cp.suffix == '.json',
            'Canonical absolute repository config JSON required')
    config_pin = file_pin(str(cp.relative_to(ROOT)))
    require(config_pin['sha256'] == args.expected_config_sha256, 'Root configuration pin changed')
    config = read_json_pin(config_pin)
    require(config['schema'] == 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_CONFIG_V1'
            and re.fullmatch(r'round_[0-9]{2}', config['round_id'])
            and 1 <= int(config['round_id'][-2:]) <= 16
            and config['cache_admission']['schema'] == 'SETI_VISIT2019_GENERIC_METADATA_CACHE_ADMISSION_V1',
            'Finite generic round config/cache schema required')
    metadata, binary_stats = {config_pin['path']: config_pin}, {}
    validate_inventory(config, metadata, binary_stats)
    manifest_pin = config['cache_admission']['source_manifest_pin']
    manifest = read_json_pin(manifest_pin)
    require(manifest['schema'] == config['cache_admission']['source_manifest_schema']
            and len(manifest['files']) == 6
            and [x['ordered_index'] for x in manifest['files']] == list(range(1, 7))
            and len({x['source_id'] for x in manifest['files']}) == len({x['url'] for x in manifest['files']}) == 6,
            'Exact six ordered source identities required')
    own = 'tools/' + FAMILY + '/'
    worker_pin, preparer_pin, loader_pin, parser_pin = [file_pin(x) for x in
        (own + 'plan_once.py', own + 'prepare_scope.py', LOADER, PARSER)]
    require(loader_pin['sha256'] == LOADER_SHA and parser_pin['sha256'] == PARSER_SHA,
            'Frozen shared cache loader or previously qualified pure parser source changed')
    extra = config.get('additional_dependency_pins', []) + [preparer_pin, config_pin]
    require(isinstance(extra, list) and len(extra) <= 128, 'Finite source/metadata proof inventory required')
    for pin in extra:
        require(file_pin(pin['path']) == pin, 'Additional proof/source pin changed')
    for pin in (worker_pin, preparer_pin, loader_pin, parser_pin):
        metadata[pin['path']] = pin
    scope = {'schema': 'SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_SCOPE_V1',
             'round_id': config['round_id'], 'script_sha256': worker_pin['sha256'],
             'parser_sha256': parser_pin['sha256'], 'parser_pin': parser_pin,
             'cache_admission_worker_pin': loader_pin, 'cache_admission': config['cache_admission'],
             'source_manifest_pin': manifest_pin, 'source_manifest_schema': manifest['schema'],
             'sources': [{k: x[k] for k in ('source_id', 'url', 'ordered_index')} for x in manifest['files']],
             'additional_dependency_pins': extra,
             'output_directory': 'results/' + FAMILY + '/' + config['round_id'],
             'shared_workspace_roots': [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6'],
             'limits': LIMITS, 'source_PREFIX_or_FRAGMENT_binaries_read_by_scope_preparer': False,
             'source_values_admission': 'BLOCKED', 'independent_validation_admission': 'BLOCKED'}
    require(all(file_pin(name) == pin for name, pin in metadata.items()), 'Source/metadata end-readback changed')
    require(all(path(name).stat().st_size == pin['bytes'] for name, pin in binary_stats.items()),
            'Binary declaration size changed during metadata-only scope preparation')
    require(time.process_time() <= 10 and time.monotonic() - START <= 30, 'Metadata scope preparation cap exceeded')
    target_dir = ROOT / 'tools' / FAMILY / 'scopes'
    target_dir.mkdir(exist_ok=True)
    (ROOT / 'results' / FAMILY).mkdir(exist_ok=True)
    target = target_dir / (config['round_id'] + '.json')
    raw = (json.dumps(scope, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= 4194304, 'Scope serialization bound exceeded')
    with target.open('xb') as h:
        h.write(raw)
        h.flush()
        os.fsync(h.fileno())
    fd = os.open(target_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    signal.alarm(0)
    print(json.dumps({'path': str(target.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw),
                      'HTTP_requests': 0, 'source_binaries_opened': False,
                      'parser_or_cache_loader_imported': False}, sort_keys=True))


if __name__ == '__main__':
    main()
