"""Versioned V2 preparation; no old scope or result is overwritten.
"""
"""One finite TREE1 scope from code/JSON pins and binary stats, not cache parsing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import time

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_chunk_index_20261010'
LOADER_SHA = 'c6770d95ddd14bf1437a8798ef896b0fd0ea851b1a87873ed4d2b60570417d73'
PARSER_SHA = '5fb4bf41245017ce9780c3e8b5727ff297fdbfaaa7fbe089aab8d53a014bcce8'
LIMITS = {'CPU_seconds': 20, 'wall_seconds': 300, 'memory_bytes': 536870912,
          'output_bytes': 33554432, 'shared_workspace_bytes': 12884901888}
START = time.monotonic()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path(name):
    p = Path(name)
    require(p.parts and not p.is_absolute() and '..' not in p.parts,
            'Exact repository-relative input path required')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents and stat.S_ISREG(p.stat().st_mode),
            'Exact regular nonsymlink input required')
    return p


def source_pin(name):
    require(Path(name).suffix in ('.py', '.json', '.md'), 'Only UTF8 source/metadata may be opened')
    p = path(name)
    require(p.stat().st_size <= 4 * 1024 ** 2, 'Metadata input size bound exceeded')
    raw = p.read_bytes()
    raw.decode('utf-8')
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}


def json_pin(pin):
    require(Path(pin['path']).suffix == '.json' and source_pin(pin['path']) == pin,
            'Exact JSON metadata pin required')
    return json.loads(path(pin['path']).read_bytes())


def inventory(value, metadata, binaries):
    if isinstance(value, dict):
        if set(value) == {'path', 'bytes', 'sha256'}:
            require(type(value['bytes']) is int and 0 <= value['bytes'] <= 4 * 1024 ** 2
                    and re.fullmatch(r'[0-9a-f]{64}', value['sha256']), 'Exact bounded nested pin required')
            p = path(value['path'])
            selected = binaries if p.suffix == '.bin' else metadata
            require(value['path'] not in selected or selected[value['path']] == value,
                    'Conflicting nested input declaration')
            if selected is binaries:
                require(p.stat().st_size == value['bytes'], 'Retained cache binary size differs')
            else:
                require(source_pin(value['path']) == value, 'Source/metadata declaration changed')
            selected[value['path']] = dict(value)
        else:
            for child in value.values():
                inventory(child, metadata, binaries)
    elif isinstance(value, list):
        for child in value:
            inventory(child, metadata, binaries)


def save_new(p, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    require(len(raw) <= 1024 ** 2, 'Finite prospective scope/receipt output bound exceeded')
    with p.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--expected-configuration-sha256', required=True)
    parser.add_argument('--scope-output', required=True)
    parser.add_argument('--root-go-metadata-only-after-qualification-closed', action='store_true')
    args = parser.parse_args()
    require(args.root_go_metadata_only_after_qualification_closed
            and re.fullmatch(r'[0-9a-f]{64}', args.expected_configuration_sha256),
            'Exact prospective metadata scope GO required')
    def deadline(signum, frame):
        raise TimeoutError('TREE1 scope preparation deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    signal.alarm(30)
    config_path, output = Path(args.configuration), Path(args.scope_output)
    require(config_path.is_absolute() and config_path.resolve() == config_path
            and ROOT in config_path.parents and output.is_absolute()
            and output.resolve() == output and output.parent == ROOT / 'tools' / FAMILY
            and output.suffix == '.json' and not output.exists(), 'Exact new scope/config paths required')
    config_pin = source_pin(str(config_path.relative_to(ROOT)))
    require(config_pin['sha256'] == args.expected_configuration_sha256, 'Scope configuration changed')
    config = json_pin(config_pin)
    require(config['schema'] == 'SETI_TREE1_SCOPE_PREPARATION_CONFIGURATION_V1', 'Exact scope configuration schema required')
    marker = output.with_name(output.stem + '_PREPARATION_STARTED_ONCE.json')
    save_new(marker, {'status': 'STARTED_ONCE_NO_RETRY', 'configuration_pin': config_pin,
                      'HTTP_requests': 0, 'actual_cache_bytes_read': 0})
    metadata, binaries = {config_pin['path']: config_pin}, {}
    inventory(config, metadata, binaries)
    q = config['metadata_qualification']
    qs, qr, qe = (json_pin(q[k]) for k in ('scope_pin', 'result_pin', 'execution_pin'))
    require(qs['schema'] == 'SETI_VISIT2019_SIX_HDF_HEADER_CACHE_QUALIFICATION_SCOPE_V3'
            and qr['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and qe['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1'
            and qr['status'] == qe['metadata_eligibility_status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and qe['status'] == 'COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION'
            and qe['all_input_end_readbacks_exact'] is qe['resource_caps_satisfied'] is True,
            'Actual closed metadata qualification success required')
    require(qr['scope_sha256'] == qe['scope_sha256'] == q['scope_pin']['sha256']
            and qr['script_sha256'] == qe['script_sha256'] == qs['script_sha256'] == q['worker_pin']['sha256']
            and qe['METADATA_QUALIFICATION_RESULT_sha256'] == q['result_pin']['sha256']
            and qr['public_freeze_commit'] == qe['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}', qe['public_freeze_commit']),
            'Qualification metadata source/terminal/freeze binding differs')
    inventory(qs, metadata, binaries)
    inventory(qe, metadata, binaries)
    manifest = json_pin(qs['source_manifest_pin'])
    sources = [{k: x[k] for k in ('source_id', 'url', 'ordered_index')} for x in manifest['files']]
    require(len(sources) == len(qr['sources']) == 6
            and [x['ordered_index'] for x in sources] == list(range(1, 7))
            and len({x['source_id'] for x in sources}) == len({x['url'] for x in sources}) == 6
            and all(all(a[k] == b[k] for k in a) for a, b in zip(sources, qr['sources'])),
            'Exact six qualified source identities differ')
    names = ['tree_index_v2.py', 'TREE1_TOY_FIXTURE_V2.py', 'planner_v2.py', 'prepare_scope_v2.py']
    pins = [source_pin('tools/' + FAMILY + '/' + name) for name in names]
    review = json_pin(config['source_review_pin'])
    require(review['schema'] == 'SETI_TREE1_CORE_FIXTURE_CALLER_PREPARER_SOURCE_PEER_REVIEW_V1'
            and review['status'] == 'PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES'
            and all(pin in review['files'] for pin in pins), 'Exact current independent source peer required')
    toy = json_pin(config['toy_result_pin'])
    require(toy['status'] == 'PASS_SYNTHETIC_ONLY_TREE1_METADATA_FIXTURES'
            and toy['parser_sha256'] == pins[0]['sha256']
            and toy['fixture_source_sha256'] == pins[1]['sha256']
            and toy['cases_passed'] == 24, 'Actual exact 24-case V2 synthetic PASS required')
    require(qs['cache_admission_worker_pin']['sha256'] == LOADER_SHA
            and qs['typed_parser_pin']['sha256'] == PARSER_SHA,
            'Exact already reviewed generic loader/parser required')
    for pin in pins:
        metadata[pin['path']] = pin
    out = Path(config['output_directory'])
    require(not out.is_absolute() and '..' not in out.parts and
            ROOT / 'results' / FAMILY in (ROOT / out).parents,
            'Exact new per-round output directory required')
    scope = {'schema': 'SETI_VISIT2019_TYPED_TREE1_PLAN_SCOPE_V1',
        'script_sha256': pins[2]['sha256'], 'parser_sha256': pins[0]['sha256'],
        'tree_core_pin': pins[0], 'cache_admission_worker_pin': qs['cache_admission_worker_pin'],
        'typed_parser_pin': qs['typed_parser_pin'],
        'tree_cache_admission_worker_pin': config['tree_cache_admission_worker_pin'],
        'cache_admission': qs['cache_admission'],
        'tree_metadata_rounds': config['tree_metadata_rounds'],
        'metadata_qualification': q, 'qualification_result_pin': q['result_pin'],
        'source_manifest_pin': qs['source_manifest_pin'], 'sources': sources,
        'output_directory': config['output_directory'], 'limits': LIMITS,
        'shared_workspace_roots': [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6'],
        'pinned_dependencies': list(metadata.values())}
    for pin in metadata.values():
        require(source_pin(pin['path']) == pin, 'Preparation end metadata readback changed')
    for pin in binaries.values():
        require(path(pin['path']).stat().st_size == pin['bytes'], 'Preparation end binary size changed')
    measured = {'CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(measured['CPU_seconds'] <= 5 and measured['wall_seconds'] <= 30
            and measured['peak_RSS_bytes'] <= 268435456, 'Measured scope-preparation cap exceeded')
    scope_pin = save_new(output, scope)
    signal.alarm(0)
    save_new(output.with_name(output.stem + '_PREPARATION_RECEIPT.json'), {
        'status': 'COMPLETE_METADATA_ONLY_TREE1_SCOPE_PREPARATION', 'scope_pin': scope_pin,
        'configuration_pin': config_pin, 'actual_cache_bytes_read': 0,
        'HTTP_requests': 0, 'spectral_values_read': False, 'metadata_inputs': len(metadata),
        'binary_stat_only_inputs': len(binaries), 'measured_before_scope_serialization': measured})


if __name__ == '__main__':
    main()
