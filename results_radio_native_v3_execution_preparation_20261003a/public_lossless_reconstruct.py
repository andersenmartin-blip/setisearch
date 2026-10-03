#!/usr/bin/env python3
"""Reconstruct original admitted counter bytes, never a case/control worker.

Reads only a published compact projection and exact original recipe (which is
never executed). Outputs original deterministic payload/wire plus metadata in
a new separate scratch directory. No original source/transcript is read, and
no protected state, subprocess, network, RNG, native or science is used.

python -I -S -B public_lossless_reconstruct.py --projection ABS_JSON
  --projection-sha256 RAW_SHA --original-recipe ABS_PY
  --original-recipe-sha256 RAW_SHA --output-root NEW_ABS_SCRATCH_ROOT
Then use public_lossless_audit.js --offline-audit to hash the exact original
transcript from the reconstructed source ranges without writing that transcript.
For a failed case with no compact projection, use --prepared ABS_JSON
--prepared-sha256 RAW_SHA instead of the projection pair; this verifies only
the two originally admitted payload/wire inputs. No transcript is invented.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

NAMESPACE = 'radio-native-v3-compact-eight-input-control-20261003e'
PREFIX = 'results_radio_native_v3_compact_eight_input_control_20261003e'
SOURCE_BYTES = 26 * 1024 * 1024
MAX_METADATA = 8 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def absolute(value):
    if (not isinstance(value, str) or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical absolute path required')
    return value


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key refused')
        result[key] = value
    return result


def signature(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('Sole-link regular metadata required')
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_pin(path, expected):
    absolute(path)
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Independently supplied exact SHA256 required')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = path[1:].split('/')
        for name in parts[:-1]:
            following = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = following
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            before = signature(os.fstat(descriptor))
            if not 0 < before[4] <= MAX_METADATA:
                raise ValueError('Bounded nonempty metadata required')
            raw = bytearray()
            while len(raw) <= before[4]:
                block = os.read(descriptor, min(65536, before[4] + 1 - len(raw)))
                if not block:
                    break
                raw.extend(block)
            if (len(raw) != before[4] or signature(os.fstat(descriptor)) != before
                    or signature(os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)) != before):
                raise ValueError('Metadata changed during stable read')
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)
    raw = bytes(raw)
    if sha(raw) != expected:
        raise ValueError('Metadata bytes differ from independent SHA256')
    return raw


def counter_bytes(domain, size):
    # This reproduces the original deterministic byte codec, not a new trial.
    return b''.join(hashlib.sha256(domain + count.to_bytes(8, 'big')).digest()
                    for count in range((size + 31) // 32))[:size]


def exclusive_write(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError('Incomplete offline reconstruction write')
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def reconstruct(*, original_recipe, original_recipe_sha256, output_root,
                projection=None, projection_sha256=None, prepared=None, prepared_sha256=None):
    if (projection is None) == (prepared is None):
        raise ValueError('Exactly one original projection or original prepared input required')
    raw_recipe = read_pin(original_recipe, original_recipe_sha256)
    input_path = projection if projection is not None else prepared
    input_sha256 = projection_sha256 if projection is not None else prepared_sha256
    raw_input = read_pin(input_path, input_sha256)
    value = json.loads(raw_input.decode('utf-8'), object_pairs_hook=object_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON refused')))
    if prepared is not None:
        if projection_sha256 is not None:
            raise ValueError('Projection pin must be absent in original prepared-input mode')
        if not isinstance(value, dict) or value.get('schema') != 'radio-native-v2-offline-maximum-prepared-v1':
            raise ValueError('Exact original prepared engineering input required')
        identity = value['control_case_identity']
        ordinal = identity['case_ordinal']
        data = {'fixture_only': True, 'execution_authorized': False,
            'scientific_execution_authorized': False,
            'regeneration': {'recipe_sha256': original_recipe_sha256,
                'recipe_bytes': len(raw_recipe), 'prepared': value,
                'recipe_arguments': [value['scope'], value['python'], identity['namespace'],
                    str(ordinal), PREFIX + '/case%02d-fixed' % ordinal,
                    'UNUSED_ORIGINAL_ADMISSION_NOT_EXECUTED', 'UNUSED_ORIGINAL_ADMISSION_NOT_EXECUTED']}}
        input_kind = 'ORIGINAL_PREPARED_FAILED_CASE_INPUTS_ONLY'
    else:
        if prepared_sha256 is not None:
            raise ValueError('Prepared pin must be absent in projection mode')
        data = value
        input_kind = 'ORIGINAL_COMPACT_TRANSCRIPT_PROJECTION'
    if not isinstance(data, dict) or data.get('fixture_only') is not True:
        raise ValueError('Exact original engineering compact projection required')
    regeneration = data['regeneration']
    prepared = regeneration['prepared']
    identity = prepared['control_case_identity']
    ordinal = identity['case_ordinal']
    if (type(ordinal) is not int or not 0 <= ordinal < 8 or identity['namespace'] != NAMESPACE
            or identity['source_case_id'] != NAMESPACE + '/case%02d' % ordinal
            or identity['native_case_binding_verified'] is not False
            or data.get('execution_authorized') is not False
            or data.get('scientific_execution_authorized') is not False):
        raise ValueError('Exact original v3 e engineering identity required')
    if (regeneration['recipe_sha256'] != original_recipe_sha256
            or regeneration['recipe_bytes'] != len(raw_recipe)
            or prepared['source_bytes'] != SOURCE_BYTES):
        raise ValueError('Original recipe/source pins differ')
    args = regeneration['recipe_arguments']
    prefix = PREFIX + '/case%02d-fixed' % ordinal
    if (not isinstance(args, list) or len(args) != 7 or args[0] != prepared['scope']
            or args[2] != NAMESPACE or args[3] != str(ordinal) or args[4] != prefix):
        raise ValueError('Exact original admission recipe metadata required')
    output_root = absolute(output_root)
    original_scope = absolute(prepared['scope'])
    original_execution = str(Path(original_scope).parent.parent)
    if output_root == original_execution or output_root.startswith(original_execution + '/'):
        raise ValueError('Offline output must remain outside original protected execution scope')
    domain = b'seti-compact-eight-input-sha256-counter-v3\0' + NAMESPACE.encode() + b'\0' + ordinal.to_bytes(8, 'big')
    if prepared['source_domain_hex'] != domain.hex():
        raise ValueError('Original deterministic source domain differs')
    source = counter_bytes(domain, SOURCE_BYTES)
    if sha(source) != prepared['source_sha256'] or identity['source_sha256'] != sha(source):
        raise ValueError('Reconstructed original deterministic payload SHA differs')
    files, chunks = {}, []
    for number, start in enumerate(range(0, len(source), 1024 * 1024)):
        encoded = base64.b64encode(source[start:start + 1024 * 1024])
        name = prefix + '/chunk%04d.b64' % number
        files[name] = encoded
        chunks.append({'path': name, 'stored_bytes': len(encoded), 'stored_sha256': sha(encoded)})
    manifest = {'schema': 'radio-native-v2-offline-maximum-archive-v1', 'fixture_only': True,
        'source_bytes': len(source), 'source_sha256': sha(source),
        'source_case_id': identity['source_case_id'], 'case_ordinal': ordinal,
        'namespace': NAMESPACE, 'native_case_binding_verified': False,
        'source_mode': 'sha256-counter-deterministic-no-rng', 'chunk_bytes': 1024 * 1024,
        'chunks': chunks, 'execution_authorized': False, 'scientific_execution_authorized': False,
        'rng_draws': 0, 'telescope_reads': 0, 'padding': ''}
    manifest['padding'] = 'x' * (524288 - len(canonical(manifest)))
    manifest_bytes = canonical(manifest)
    files[prefix + '/manifest.json'] = manifest_bytes
    files[prefix + '/HEAD'] = sha(manifest_bytes).encode() + b'\n'
    file_pins = {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in sorted(files.items())}
    if (len(manifest_bytes) != 524288 or len(files) != 28
            or sum(map(len, files.values())) != 36875057 or file_pins != prepared['files']):
        raise ValueError('Reconstructed original archive bytes/layout pins differ')
    params = {'base_tree_sha': 'a' * 40, 'repository_full_name': 'andersenmartin-blip/setisearch',
        'tree_elements': [{'content': raw.decode('ascii'), 'mode': '100644', 'path': name, 'type': 'blob'}
                          for name, raw in sorted(files.items())]}
    packet = {'control_case_identity': identity, 'automatic_retry': False, 'fixture_only': True,
        'kind': 'offline-worker-request', 'ordinal': 1, 'params': params,
        'schema': 'radio-native-v2-offline-frozen-request-v1', 'tool': 'mcp__codex_apps__github_create_tree'}
    wire, params_bytes = canonical(packet), canonical(params)
    view = prepared['request_view']
    if (len(wire) != view['source_bytes'] or sha(wire) != view['source_sha256']
            or len(params_bytes) != view['bytes'] or sha(params_bytes) != view['sha256']
            or wire[view['offset']:view['offset'] + view['bytes']] != params_bytes):
        raise ValueError('Reconstructed exact original request wire/params pins differ')
    for row in prepared['reads']:
        selected = wire[row['offset']:row['offset'] + row['bytes']]
        if len(selected) != row['bytes'] or sha(selected) != row['output_sha256']:
            raise ValueError('Reconstructed original read-range bytes differ')
    if len(prepared['reads']) != 38:
        raise ValueError('Exactly 38 original source read ranges required')
    # All original byte identities are checked before creating the scratch root.
    os.mkdir(output_root, 0o700)
    exclusive_write(output_root + '/deterministic-source.bin', source)
    exclusive_write(output_root + '/request-wire.bin', wire)
    receipt = {'schema': 'radio-native-v3-offline-original-source-reconstruction-v1',
        'input_kind': input_kind, 'projection_sha256': projection_sha256,
        'original_prepared_sha256': prepared_sha256,
        'original_recipe_sha256': original_recipe_sha256,
        'control_case_identity': identity, 'archive_file_pins': file_pins,
        'source_payload': {'bytes': len(source), 'sha256': sha(source)},
        'request_wire': {'bytes': len(wire), 'sha256': sha(wire)},
        'original_guarded_recipe_executed': False, 'original_case_or_control_reexecuted': False,
        'data_reconstruction_only': True, 'new_case_executions': 0, 'scientific_cases_run': 0,
        'native_case_executions': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'network_calls': 0, 'git_calls': 0, 'subprocess_calls': 0,
        'execution_authorized': False, 'scientific_execution_authorized': False}
    exclusive_write(output_root + '/offline-reconstruction.json', canonical(receipt) + b'\n')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--projection')
    input_group.add_argument('--prepared')
    parser.add_argument('--projection-sha256')
    parser.add_argument('--prepared-sha256')
    for name in ('original-recipe', 'original-recipe-sha256', 'output-root'):
        parser.add_argument('--' + name, required=True)
    try:
        result = reconstruct(**vars(parser.parse_args(argv)))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, 'offline original-byte reconstruction refused: ' + str(error) + '\n')
    print(canonical({'status': 'PASS_ORIGINAL_SOURCE_BYTES_RECONSTRUCTED', **result}).decode())


if __name__ == '__main__':
    main()
