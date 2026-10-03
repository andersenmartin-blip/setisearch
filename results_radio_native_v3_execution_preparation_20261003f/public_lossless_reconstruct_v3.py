#!/usr/bin/env python3
"""V3 offline reconstruction of retained original partial F engineering bytes.

Never execute the original guarded recipe, admission or control. Supply the
independently pinned byte-preserving partial projection, original recipe and
entire original repository root. All fixed reconstructed outputs are exclusive,
owner-only and outside that complete root (including permanent E and F scopes).
The separate public_lossless_partial_audit_v3.js validates the same projection
and restored ranges with an independent streaming Node hash-only sink.

python -I -S -B public_lossless_reconstruct_v3.py --projection ABS_JSON
  --projection-sha256 RAW_SHA --original-recipe ABS_PY
  --original-recipe-sha256 RAW_SHA --original-repository-root ABS_REPO
  --output-root NEW_ABS_OUTSIDE_REPO
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

NAMESPACE = 'radio-native-v3-compact-eight-input-control-20261003f'
PREFIX = 'results_radio_native_v3_compact_eight_input_control_20261003f'
SOURCE_BYTES = 26 * 1024 * 1024
MAX_METADATA = 8 * 1024 * 1024
SCOPE_NAME = 'results_radio_native_v3_compact_eight_input_control_20261003f'
MAX_PROTECTED_DIRECTORIES = 100000
MAX_WIRE_BYTES = 40 * 1024 * 1024
MAX_RECEIPT_BYTES = 2 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 108 * 1024 * 1024
MAX_PROTECTED_NAMES = 250000
MAX_PENDING_DIRECTORIES = 4096
PARTIAL_SCHEMA = 'radio-native-v3-public-original-partial-transcript-projection-v1'


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


def directory_identity(info):
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Real no-follow directory required')
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def open_directory(path, witnesses):
    """Hold each walk component; reject symlinks and changed named ancestors."""
    absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open('/', flags)
    current = ''
    try:
        for name in path[1:].split('/'):
            following = os.open(name, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
            current += '/' + name
            observed = directory_identity(os.fstat(descriptor))
            if current in witnesses and witnesses[current] != observed:
                raise ValueError('Named directory ancestry changed during held walk')
            witnesses.setdefault(current, observed)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_pin(path, expected, witnesses):
    absolute(path)
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Independently supplied exact SHA256 required')
    parent, name = path.rsplit('/', 1)
    directory = open_directory(parent, witnesses)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
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
                    or signature(os.stat(name, dir_fd=directory, follow_symlinks=False)) != before):
                raise ValueError('Metadata changed during stable read')
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)
    raw = bytes(raw)
    if sha(raw) != expected:
        raise ValueError('Metadata bytes differ from independent SHA256')
    checked_parent = open_directory(parent, witnesses)
    try:
        if signature(os.stat(name, dir_fd=checked_parent, follow_symlinks=False)) != before:
            raise ValueError('Pinned metadata pathname changed after held read')
    finally:
        os.close(checked_parent)
    return raw


def counter_bytes(domain, size):
    # This reproduces the original deterministic byte codec, not a new trial.
    return b''.join(hashlib.sha256(domain + count.to_bytes(8, 'big')).digest()
                    for count in range((size + 31) // 32))[:size]


def protected_directory_identities(repository_root, witnesses):
    """Directory metadata only; never open repository/private file contents.

    Every protected directory inode is included, so a bind-mounted alias of a
    repository descendant is refused as an output parent. Symlink directories
    are not followed. Visited identities bound alias/mount cycles.
    """
    root_descriptor = open_directory(repository_root, witnesses)
    found = set()
    pending = [root_descriptor]
    names_seen = 0
    try:
        while pending:
            descriptor = pending.pop()
            try:
                identity = directory_identity(os.fstat(descriptor))[:2]
                if identity in found:
                    continue
                found.add(identity)
                if len(found) > MAX_PROTECTED_DIRECTORIES:
                    raise ValueError('Protected directory metadata scan exceeds bound')
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        name = entry.name
                        names_seen += 1
                        if names_seen > MAX_PROTECTED_NAMES:
                            raise ValueError('Protected directory name scan exceeds bound')
                        info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                        if stat.S_ISDIR(info.st_mode):
                            if len(pending) >= MAX_PENDING_DIRECTORIES:
                                raise ValueError('Protected pending directory descriptors exceed bound')
                            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                            dir_fd=descriptor)
                            if directory_identity(os.fstat(child))[:2] != (info.st_dev, info.st_ino):
                                os.close(child)
                                raise ValueError('Protected directory changed during metadata scan')
                            pending.append(child)
            finally:
                os.close(descriptor)
    finally:
        for descriptor in pending:
            os.close(descriptor)
    return found


class OutputRoot:
    """Held, independently disjoint, exclusive new root and bounded file writes."""
    def __init__(self, output_root, repository_root, witnesses):
        self.path, self.repository = absolute(output_root), absolute(repository_root)
        self.witnesses = witnesses
        if self.path == self.repository or self.path.startswith(self.repository + '/'):
            raise ValueError('Offline output must be outside the entire original repository')
        self.parent_path, self.name = self.path.rsplit('/', 1)
        self.parent = open_directory(self.parent_path, witnesses)
        self.parent_identity = directory_identity(os.fstat(self.parent))
        self.descriptor = None
        self.root_identity = None
        self.pins = {}
        try:
            protected = protected_directory_identities(repository_root, witnesses)
            self.protected_identities = protected
            output_ancestry = [identity[:2] for path, identity in witnesses.items()
                               if path == self.parent_path or self.parent_path.startswith(path + '/')]
            if set(output_ancestry) & protected:
                raise ValueError('Physical output ancestor aliases a protected repository directory')
            try:
                os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError('Exclusive new offline root required; existing/symlink root refused')
        except BaseException:
            os.close(self.parent)
            raise

    def create(self):
        # This call follows all metadata/content validation, never its failures.
        self.check_parent()
        os.mkdir(self.name, 0o700, dir_fd=self.parent)
        created = directory_identity(os.stat(self.name, dir_fd=self.parent, follow_symlinks=False))
        self.descriptor = os.open(self.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                  dir_fd=self.parent)
        if (directory_identity(os.fstat(self.descriptor)) != created
                or created[:2] in self.protected_identities or created[3] != os.geteuid()):
            raise ValueError('Created root changed or aliases a protected directory before ownership setup')
        os.fchmod(self.descriptor, 0o700)
        self.root_identity = directory_identity(os.fstat(self.descriptor))
        if self.root_identity[2] != 0o700 or self.root_identity[3] != os.geteuid():
            raise ValueError('New offline root must be owned exclusively by current effective user')
        os.fsync(self.parent)
        self.check_root()

    def check_parent(self):
        named_parent = open_directory(self.parent_path, self.witnesses)
        try:
            if directory_identity(os.fstat(named_parent)) != self.parent_identity:
                raise ValueError('Held output parent differs from current named parent')
        finally:
            os.close(named_parent)
        self.protected_identities = protected_directory_identities(self.repository, self.witnesses)
        ancestry = {identity[:2] for path, identity in self.witnesses.items()
                    if path == self.parent_path or self.parent_path.startswith(path + '/')}
        if ancestry & self.protected_identities:
            raise ValueError('Output parent became physically reachable inside protected repository')

    def check_root(self):
        self.check_parent()
        if self.descriptor is None:
            return
        current = directory_identity(os.fstat(self.descriptor))
        named = directory_identity(os.stat(self.name, dir_fd=self.parent, follow_symlinks=False))
        if current != self.root_identity or named != self.root_identity:
            raise ValueError('Exclusive offline root replaced, aliased or ownership changed')
        if current[:2] in self.protected_identities:
            raise ValueError('Offline root aliases protected repository before writing')

    def write(self, name, raw):
        limits = {'deterministic-source.bin': SOURCE_BYTES, 'request-wire.bin': MAX_WIRE_BYTES,
                  'offline-reconstruction.json': MAX_RECEIPT_BYTES,
                  'caller-result.partial.json': MAX_TRANSCRIPT_BYTES}
        if name not in limits or name in self.pins or not isinstance(raw, bytes) or len(raw) > limits[name]:
            raise ValueError('Exact bounded fixed offline output file required')
        self.check_root()
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o400, dir_fd=self.descriptor)
        try:
            os.fchmod(descriptor, 0o400)
            created = os.fstat(descriptor)
            if (not stat.S_ISREG(created.st_mode) or created.st_nlink != 1
                    or created.st_uid != os.geteuid() or stat.S_IMODE(created.st_mode) != 0o400
                    or created.st_size != 0):
                raise ValueError('Exclusive owner-only sole-link new output required')
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view[:65536])
                if written <= 0:
                    raise OSError('Incomplete bounded offline write')
                view = view[written:]
            os.fsync(descriptor)
            actual = os.fstat(descriptor)
            named = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
            if (signature(actual) != signature(named) or actual.st_size != len(raw)
                    or actual.st_uid != os.geteuid() or stat.S_IMODE(actual.st_mode) != 0o400):
                raise ValueError('New output changed during bounded write')
            self.pins[name] = {'bytes': len(raw), 'sha256': sha(raw), 'identity': signature(actual),
                               'uid': actual.st_uid, 'mode': stat.S_IMODE(actual.st_mode)}
        finally:
            os.close(descriptor)
        os.fsync(self.descriptor)
        self.check_root()

    def finish(self):
        self.check_root()
        if set(os.listdir(self.descriptor)) != set(self.pins):
            raise ValueError('Unknown entry in exclusive offline root')
        if self.root_identity[:2] in protected_directory_identities(self.repository, self.witnesses):
            raise ValueError('Offline root became physically reachable inside protected repository')
        for name, expected in self.pins.items():
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                 dir_fd=self.descriptor)
            try:
                before = signature(os.fstat(descriptor))
                observed = os.fstat(descriptor)
                digest = hashlib.sha256()
                count = 0
                while True:
                    block = os.read(descriptor, 65536)
                    if not block:
                        break
                    count += len(block)
                    if count > expected['bytes']:
                        raise ValueError('Offline output exceeded bounded readback bytes')
                    digest.update(block)
                if (before != expected['identity'] or signature(os.fstat(descriptor)) != before
                        or signature(os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)) != before
                        or count != expected['bytes'] or digest.hexdigest() != expected['sha256']
                        or observed.st_uid != os.geteuid() or stat.S_IMODE(observed.st_mode) != 0o400):
                    raise ValueError('Owner-only offline output identity/content changed at readback')
            finally:
                os.close(descriptor)
        self.check_root()

    def close(self):
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None
        os.close(self.parent)


def decode_b64(value):
    if not isinstance(value, str):
        raise ValueError('Exact base64 literal metadata required')
    raw = base64.b64decode(value, validate=True)
    if base64.b64encode(raw).decode() != value:
        raise ValueError('Canonical base64 literal metadata required')
    return raw


def ascii_json_string(raw):
    # Original source wire and retained envelope text are ASCII; no numeric or
    # metadata JSON is reserialized. This exact quoting agrees with Node.
    return json.dumps(raw.decode('ascii'), ensure_ascii=False, separators=(',', ':')).encode('ascii')


def restore_partial(projection, prepared, wire):
    if projection.get('schema') != PARTIAL_SCHEMA:
        raise ValueError('Exact original partial projection schema required')
    expected = projection.get('original_full_transcript')
    if (not isinstance(expected, dict) or set(expected) != {'bytes', 'sha256'}
            or type(expected['bytes']) is not int or not 0 < expected['bytes'] <= MAX_TRANSCRIPT_BYTES
            or not re.fullmatch('[0-9a-f]{64}', str(expected['sha256']))):
        raise ValueError('Exact bounded original partial transcript pin required')
    parts = projection.get('parts')
    count = projection.get('successful_source_reads')
    if type(count) is not int or not 0 <= count < len(prepared['reads']) or len(prepared['reads']) != 38:
        raise ValueError('Strictly partial original source read count required')
    if not isinstance(parts, list) or len(parts) != 4 * count + 1:
        raise ValueError('Exact alternating original literal/token part inventory required')
    plans = {row['ordinal']: row for row in prepared['reads']}
    if set(plans) != set(range(38)):
        raise ValueError('Exact original unique 38 read plans required')
    restored = bytearray()
    tokens = []
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            raise ValueError('Original partial part object required')
        if index % 2 == 0:
            if set(part) != {'kind', 'data_base64', 'bytes', 'sha256'} or part['kind'] != 'literal':
                raise ValueError('Exact retained original literal part required')
            raw = decode_b64(part['data_base64'])
        else:
            ordinal = (index - 1) // 4
            kind = 'source_output_json' if index % 4 == 1 else 'response_json'
            keys = {'kind', 'source_plan_ordinal', 'record_ordinal', 'bytes', 'sha256'}
            if kind == 'response_json':
                keys |= {'envelope_prefix_base64', 'envelope_suffix_base64'}
            if (set(part) != keys or part['kind'] != kind or part['source_plan_ordinal'] != ordinal
                    or part['record_ordinal'] != ordinal + 3):
                raise ValueError('Exact original partial token identity/order required')
            plan = plans[ordinal]
            selected = wire[plan['offset']:plan['offset'] + plan['bytes']]
            if len(selected) != plan['bytes'] or sha(selected) != plan['output_sha256']:
                raise ValueError('Original selected source range pin differs')
            raw = ascii_json_string(selected)
            if kind == 'response_json':
                prefix = decode_b64(part['envelope_prefix_base64'])
                suffix = decode_b64(part['envelope_suffix_base64'])
                raw = ascii_json_string(prefix + raw + suffix)
            tokens.append({'kind': kind, 'source_plan_ordinal': ordinal, 'record_ordinal': ordinal + 3})
        if (type(part['bytes']) is not int or part['bytes'] != len(raw) or sha(raw) != part['sha256']):
            raise ValueError('Restored original partial part bytes/SHA differ')
        restored.extend(raw)
        if len(restored) > expected['bytes']:
            raise ValueError('Original partial reconstruction exceeded exact byte bound')
    raw = bytes(restored)
    if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
        raise ValueError('Entire original partial raw transcript bytes/SHA differ')
    value = json.loads(raw.decode('utf8'), object_pairs_hook=object_pairs)
    if value.get('control_case_identity') != prepared['control_case_identity']:
        raise ValueError('Partial transcript original case identity differs')
    records = value['qualified']['client']['records']
    receipts = value['read_receipts']
    successes = [r for r in records if r.get('kind') == 'actual_source_read' and 'raw_result' in r]
    failed = [r for r in records if r.get('kind') == 'actual_source_read' and 'error' in r]
    if (len(successes) != count or len(receipts) != count or len(records) != count + 4
            or len(failed) != 1 or failed[0]['ordinal'] != count + 3):
        raise ValueError('Retained strictly partial records/receipts/failure inventory differs')
    for ordinal, (record, receipt) in enumerate(zip(successes, receipts)):
        plan = plans[ordinal]
        output = record['raw_result']['output'].encode('ascii')
        response = record['response_json'].encode('ascii')
        request = json.loads(record['request_json'])
        if (record['ordinal'] != ordinal + 3 or receipt['ordinal'] != ordinal
                or request['tool'] != 'exec_command' or request['arguments'] != plan['arguments']
                or output != wire[plan['offset']:plan['offset'] + plan['bytes']]
                or len(response) != record['response_bytes'] or sha(response) != record['response_sha256']
                or receipt['envelope_bytes'] != len(response) or receipt['envelope_sha256'] != sha(response)
                or json.loads(response) != record['raw_result']):
            raise ValueError('Restored original partial record/envelope/receipt binding differs')
    return raw, tokens


def reconstruct(*, original_recipe, original_recipe_sha256, output_root, original_repository_root,
                projection, projection_sha256, original_prepared_sha256):
    witnesses = {}
    raw_recipe = read_pin(original_recipe, original_recipe_sha256, witnesses)
    raw_projection = read_pin(projection, projection_sha256, witnesses)
    data = json.loads(raw_projection.decode('utf8'), object_pairs_hook=object_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite metadata refused')))
    if (data.get('schema') != PARTIAL_SCHEMA or data.get('fixture_only') is not True
            or data.get('execution_authorized') is not False or data.get('scientific_execution_authorized') is not False):
        raise ValueError('Exact retained original partial F engineering projection required')
    regeneration = data['regeneration'];prepared = regeneration['prepared']
    identity = prepared['control_case_identity'];ordinal = identity['case_ordinal']
    if (type(ordinal) is not int or not 0 <= ordinal < 8 or identity['namespace'] != NAMESPACE
            or identity['source_case_id'] != NAMESPACE + '/case%02d' % ordinal
            or identity['native_case_binding_verified'] is not False
            or data['control_case_identity'] != identity
            or regeneration['recipe_sha256'] != original_recipe_sha256
            or regeneration['recipe_bytes'] != len(raw_recipe) or prepared['source_bytes'] != SOURCE_BYTES):
        raise ValueError('Exact original F identity/recipe/source pins required')
    original_repository_root = absolute(original_repository_root)
    if absolute(prepared['scope']) != original_repository_root + '/' + SCOPE_NAME + '/cases/case%02d' % ordinal:
        raise ValueError('Original F scope differs from independent complete repository pin')
    if (not re.fullmatch('[0-9a-f]{64}', str(original_prepared_sha256))
            or regeneration['prepared_raw_sha256'] != original_prepared_sha256
            or prepared.get('schema') != 'radio-native-v2-offline-maximum-prepared-v1'):
        raise ValueError('Retained original prepared raw SHA required')
    output = OutputRoot(output_root, original_repository_root, witnesses)
    try:
        return reconstruct_to_held_output(data, prepared, identity, ordinal,
            PREFIX + '/case%02d-fixed' % ordinal, raw_recipe, original_recipe_sha256,
            projection_sha256, None, 'ORIGINAL_TERMINAL_PARTIAL_F_ONLY', output)
    finally:
        output.close()


def reconstruct_to_held_output(data, prepared, identity, ordinal, prefix, raw_recipe,
        original_recipe_sha256, projection_sha256, prepared_sha256, input_kind, output):
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
    partial, tokens = restore_partial(data, prepared, wire)
    # All original byte identities are checked before creating the scratch root.
    output.create()
    output.write('deterministic-source.bin', source)
    output.write('request-wire.bin', wire)
    output.write('caller-result.partial.json', partial)
    receipt = {'schema': 'radio-native-v3-offline-original-source-reconstruction-v3',
        'input_kind': input_kind, 'projection_sha256': projection_sha256,
        'original_prepared_sha256': data['regeneration']['prepared_raw_sha256'],
        'original_partial_transcript': {'bytes': len(partial), 'sha256': sha(partial)},
        'successful_source_reads': data['successful_source_reads'], 'restored_string_tokens': len(tokens),
        'full_case_completed': False, 'missing_unretained_stderr_reconstructed': False,
        'protected_original_scope_names': ['results_radio_native_v3_compact_eight_input_control_20261003e', SCOPE_NAME],
        'protected_scan_names_bound': MAX_PROTECTED_NAMES,
        'protected_scan_pending_descriptors_bound': MAX_PENDING_DIRECTORIES,
        'original_recipe_sha256': original_recipe_sha256,
        'control_case_identity': identity, 'archive_file_pins': file_pins,
        'source_payload': {'bytes': len(source), 'sha256': sha(source)},
        'request_wire': {'bytes': len(wire), 'sha256': sha(wire)},
        'original_guarded_recipe_executed': False, 'original_case_or_control_reexecuted': False,
        'data_reconstruction_only': True, 'new_case_executions': 0, 'scientific_cases_run': 0,
        'original_repository_root': output.repository,
        'offline_output_root': output.path,
        'held_no_follow_output_ancestry': True, 'physical_protected_directory_alias_checks': True,
        'entire_original_repository_excluded_from_output': True,
        'exclusive_current_user_only_output_root_and_files': True,
        'fixed_bounded_output_names': True,
        'native_case_executions': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'network_calls': 0, 'git_calls': 0, 'subprocess_calls': 0,
        'execution_authorized': False, 'scientific_execution_authorized': False}
    output.write('offline-reconstruction.json', canonical(receipt) + b'\n')
    output.finish()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('projection', 'projection-sha256', 'original-recipe',
            'original-recipe-sha256', 'output-root', 'original-repository-root', 'original-prepared-sha256'):
        parser.add_argument('--' + name, required=True)
    try:
        result = reconstruct(**vars(parser.parse_args(argv)))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, 'offline original partial reconstruction refused: ' + str(error) + '\n')
    print(canonical({'status': 'PASS_ORIGINAL_PARTIAL_BYTES_RECONSTRUCTED', **result}).decode())


if __name__ == '__main__':
    main()
