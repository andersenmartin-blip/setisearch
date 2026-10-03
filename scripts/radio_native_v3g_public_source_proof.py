#!/usr/bin/env python3
"""Read-only frozen-source/Git content-address equivalence, without authority.

The outer caller independently fetches and pins an immutable Git commit and its
complete recursive tree. This helper reads those metadata files and only the
code/input paths explicitly selected by the pinned freeze. It performs no Git,
network, project import, runtime discovery, reservation, or scientific work.
This is not a claim that each public blob was separately downloaded over HTTP.
"""

import argparse
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import sys


SCHEMA = 'radio-native-v3-public-source-content-address-proof-v1'
METADATA_LIMIT = 128 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
FREEZE_SCHEMA = 'radio-native-v2-runner-broker-runtime-freeze-v1'
AUTHORITY_FIELDS = (
    'reservation_authorized', 'rng_authorized', 'execution_authorized',
    'scientific_execution_authorized', 'restart_authorized',
    'transport_integration_qualified',
)
_REGULAR_MODES = frozenset(('100644', '100755'))
_TREE_MODES = {'040000': 'tree', '100644': 'blob', '100755': 'blob',
               '120000': 'blob', '160000': 'commit'}


def _hash(value, length, label):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{%d}' % length, value) is None:
        raise ValueError('Exact lowercase hash required: ' + label)
    return value


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or PurePosixPath(value).is_absolute()
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical repository-relative path required')
    try:
        value.encode('utf-8', 'strict')
    except UnicodeError as error:
        raise ValueError('UTF-8 path required') from error
    return value


def _absolute(value):
    value = os.fspath(value)
    if (not isinstance(value, str) or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Strict canonical absolute path required')
    return value


def _directory_signature(observed):
    if not stat.S_ISDIR(observed.st_mode):
        raise ValueError('Real directory required')
    return observed.st_dev, observed.st_ino, observed.st_mode


def _file_signature(observed):
    if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        raise ValueError('Sole-link regular file required')
    return (observed.st_dev, observed.st_ino, observed.st_mode, observed.st_nlink,
            observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns)


def _open_directory(absolute, witnesses):
    """Walk from / with directory descriptors; no ancestor symlink follows."""
    _absolute(absolute)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open('/', flags)
    current = ''
    try:
        for component in absolute[1:].split('/'):
            following = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
            current += '/' + component
            observed = _directory_signature(os.fstat(descriptor))
            if current in witnesses and witnesses[current] != observed:
                raise ValueError('Directory identity changed: ' + current)
            witnesses.setdefault(current, observed)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_regular(absolute, directories):
    _absolute(absolute)
    parent, name = absolute.rsplit('/', 1)
    # All callers use non-root parents, including their metadata files.
    descriptor = _open_directory(parent, directories)
    try:
        return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       dir_fd=descriptor)
    finally:
        os.close(descriptor)


def _stat_file(absolute, directories):
    descriptor = _open_regular(absolute, directories)
    try:
        return _file_signature(os.fstat(descriptor))
    finally:
        os.close(descriptor)


def _read_file(absolute, directories, expected_signature=None, *, metadata=False):
    descriptor = _open_regular(absolute, directories)
    try:
        before = _file_signature(os.fstat(descriptor))
        if expected_signature is not None and before != expected_signature:
            raise ValueError('File changed before read: ' + absolute)
        size = before[4]
        if metadata and size > METADATA_LIMIT:
            raise ValueError('Metadata file exceeds bounded read limit')
        sha256 = hashlib.sha256()
        git_blob = hashlib.sha1(('blob %d\0' % size).encode('ascii'))
        chunks = [] if metadata else None
        count = 0
        while True:
            block = os.read(descriptor, CHUNK_SIZE)
            if not block:
                break
            count += len(block)
            if count > size:
                raise ValueError('File grew while being read: ' + absolute)
            sha256.update(block)
            git_blob.update(block)
            if metadata:
                chunks.append(block)
        after = _file_signature(os.fstat(descriptor))
        if after != before or count != size:
            raise ValueError('File changed during read: ' + absolute)
        # Also bind the lexical pathname after closing races with renamed files.
        if _stat_file(absolute, directories) != before:
            raise ValueError('Path identity changed during read: ' + absolute)
        return {'sha256': sha256.hexdigest(), 'git_blob_sha': git_blob.hexdigest(),
                'bytes': count, 'signature': before,
                'raw': b''.join(chunks) if metadata else None}
    finally:
        os.close(descriptor)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key: ' + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Nonfinite JSON constant refused: ' + value)


def _metadata(absolute, expected_sha256, directories):
    _hash(expected_sha256, 64, 'metadata SHA256')
    pin = _read_file(_absolute(absolute), directories, metadata=True)
    if pin['sha256'] != expected_sha256:
        raise ValueError('Raw metadata SHA256 differs: ' + absolute)
    try:
        value = json.loads(pin.pop('raw').decode('utf-8', 'strict'),
                           object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Strict UTF-8 JSON metadata required') from error
    if not isinstance(value, dict):
        raise ValueError('JSON metadata object required')
    return value, pin


def _count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Nonnegative integer count required: ' + label)
    return value


def _freeze_selection(freeze, expected_code_count, expected_input_count, expected_unique_count):
    if (freeze.get('schema') != FREEZE_SCHEMA
            or freeze.get('freeze_kind') != 'COMPLETE_RUNNER_BROKER_RUNTIME'
            or freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'):
        raise ValueError('Complete prospective engineering freeze required')
    if any(freeze.get(field) is not False for field in AUTHORITY_FIELDS):
        raise ValueError('Freeze cannot confer execution or transport authority')
    if freeze.get('transport_qualification') is not None:
        raise ValueError('Freeze transport qualification must remain absent')
    maps = []
    for inventory_name, hashes_name, expected_count in (
            ('repository_code_inventory', 'code_sha256s', expected_code_count),
            ('input_file_inventory', 'input_sha256s', expected_input_count)):
        inventory, hashes = freeze.get(inventory_name), freeze.get(hashes_name)
        if (not isinstance(inventory, list) or not isinstance(hashes, dict)
                or any(not isinstance(path, str) for path in inventory)
                or inventory != sorted(hashes)):
            raise ValueError('Exact sorted inventory/hash-map join required: ' + inventory_name)
        if len(inventory) != _count(expected_count, inventory_name):
            raise ValueError('Independently pinned inventory count differs: ' + inventory_name)
        for path, sha256 in hashes.items():
            _relative(path)
            _hash(sha256, 64, path)
        maps.append(hashes)
    code, inputs = maps
    shared = set(code) & set(inputs)
    if any(code[path] != inputs[path] for path in shared):
        raise ValueError('Overlapping code/input identities conflict')
    selected = {**code, **inputs}
    if len(selected) != _count(expected_unique_count, 'unique paths'):
        raise ValueError('Independently pinned unique joined count differs')
    if not selected:
        raise ValueError('Nonempty frozen source selection required')
    return code, inputs, selected


def _tree_inventory(tree, expected_tree):
    """Rebuild every canonical Git tree object from complete recursive metadata."""
    if tree.get('sha') != expected_tree or tree.get('truncated') is not False:
        raise ValueError('Exact complete immutable recursive Git tree required')
    entries = tree.get('tree')
    if not isinstance(entries, list):
        raise ValueError('Recursive Git tree entry list required')
    by_path = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Git tree entry object required')
        path = _relative(entry.get('path'))
        if path in by_path:
            raise ValueError('Duplicate recursive Git tree path: ' + path)
        mode = entry.get('mode')
        if mode not in _TREE_MODES or entry.get('type') != _TREE_MODES[mode]:
            raise ValueError('Git tree mode/type mismatch: ' + path)
        _hash(entry.get('sha'), 40, path)
        if entry['type'] == 'blob':
            _count(entry.get('size'), 'Git blob size: ' + path)
        by_path[path] = entry
    children = {'': []}
    for path, entry in by_path.items():
        parent = path.rsplit('/', 1)[0] if '/' in path else ''
        if parent and (parent not in by_path or by_path[parent]['type'] != 'tree'):
            raise ValueError('Missing/non-directory recursive Git ancestry: ' + path)
        children.setdefault(parent, []).append(entry)
        if entry['type'] == 'tree':
            children.setdefault(path, [])
    for directory, immediate in children.items():
        def order(entry):
            name = entry['path'].rsplit('/', 1)[-1].encode('utf-8')
            return name + (b'/' if entry['type'] == 'tree' else b'')
        body = b''.join(
            (('40000' if entry['mode'] == '040000' else entry['mode']).encode('ascii')
             + b' ' + entry['path'].rsplit('/', 1)[-1].encode('utf-8')
             + b'\0' + bytes.fromhex(entry['sha']))
            for entry in sorted(immediate, key=order))
        actual = hashlib.sha1(('tree %d\0' % len(body)).encode('ascii') + body).hexdigest()
        wanted = expected_tree if not directory else by_path[directory]['sha']
        if actual != wanted:
            raise ValueError('Canonical Git tree object hash differs: ' + (directory or '<root>'))
    return by_path


def prove_source_bytes(*, root, freeze_path, freeze_sha256,
                       commit_readback_path, commit_readback_sha256,
                       tree_readback_path, tree_readback_sha256,
                       expected_commit, expected_tree, expected_code_count,
                       expected_input_count, expected_unique_count):
    """Prove selected local bytes against independently pinned public metadata.

    Pin arguments must originate from the trusted outer immutable fetch, not
    from a boolean or values copied out of an untrusted readback file. This
    validates code/input file bytes only, not the rest of the runtime freeze.
    """
    root = _absolute(root)
    _hash(expected_commit, 40, 'expected immutable commit')
    _hash(expected_tree, 40, 'expected immutable tree')
    directories = {}
    descriptor = _open_directory(root, directories)
    os.close(descriptor)
    metadata_paths = (freeze_path, commit_readback_path, tree_readback_path)
    if len({_absolute(path) for path in metadata_paths}) != 3:
        raise ValueError('Distinct freeze/commit/tree metadata files required')
    freeze, freeze_pin = _metadata(freeze_path, freeze_sha256, directories)
    commit, commit_pin = _metadata(commit_readback_path, commit_readback_sha256, directories)
    tree, tree_pin = _metadata(tree_readback_path, tree_readback_sha256, directories)
    if (commit.get('sha') != expected_commit or not isinstance(commit.get('tree'), dict)
            or commit['tree'].get('sha') != expected_tree):
        raise ValueError('Immutable commit/tree readback differs from independent pins')
    code, inputs, selected = _freeze_selection(
        freeze, expected_code_count, expected_input_count, expected_unique_count)
    public = _tree_inventory(tree, expected_tree)
    for path in selected:
        if path not in public:
            raise ValueError('Frozen path missing from public tree: ' + path)
        if public[path]['type'] != 'blob' or public[path]['mode'] not in _REGULAR_MODES:
            raise ValueError('Frozen public path must be a regular Git blob: ' + path)
    # The common observation window covers every file: all first signatures
    # precede every content read and all terminal signatures follow every read.
    before = {path: _stat_file(root + '/' + path, directories) for path in sorted(selected)}
    if len({signature[:2] for signature in before.values()}) != len(before):
        raise ValueError('Aliased frozen file identities refused')
    rows = []
    for path in sorted(selected):
        pin = _read_file(root + '/' + path, directories, before[path])
        expected_blob = public[path]
        if pin['sha256'] != selected[path]:
            raise ValueError('Local SHA256 differs from freeze: ' + path)
        if pin['bytes'] != expected_blob['size']:
            raise ValueError('Local byte length differs from public tree: ' + path)
        if pin['git_blob_sha'] != expected_blob['sha']:
            raise ValueError('Local canonical Git blob SHA differs from public tree: ' + path)
        rows.append({'path': path, 'bytes': pin['bytes'], 'sha256': pin['sha256'],
                     'git_blob_sha': pin['git_blob_sha'], 'public_git_mode': expected_blob['mode'],
                     'code_selected': path in code, 'input_selected': path in inputs,
                     'local_file_identity': {'device': before[path][0], 'inode': before[path][1],
                         'links': before[path][3], 'mtime_ns': before[path][5],
                         'ctime_ns': before[path][6]},
                     'freeze_sha256_equal': True, 'public_blob_sha_equal': True,
                     'public_blob_size_equal': True})
    for path in sorted(selected):
        if _stat_file(root + '/' + path, directories) != before[path]:
            raise ValueError('Frozen file changed within common observation window: ' + path)
    for path, pin in zip(metadata_paths, (freeze_pin, commit_pin, tree_pin)):
        if _stat_file(path, directories) != pin['signature']:
            raise ValueError('Pinned metadata changed within observation window: ' + path)
    descriptor = _open_directory(root, directories)
    os.close(descriptor)
    return {'schema': SCHEMA, 'status': 'PASS_SELECTED_FROZEN_BYTE_EQUIVALENCE',
            'repository_root': root, 'immutable_commit': expected_commit,
            'immutable_tree': expected_tree,
            'freeze_sha256': freeze_pin['sha256'],
            'commit_readback_sha256': commit_pin['sha256'],
            'recursive_tree_readback_sha256': tree_pin['sha256'],
            'recursive_tree_truncated': False,
            'canonical_git_tree_objects_verified': 1 + sum(
                entry['type'] == 'tree' for entry in public.values()),
            'recursive_tree_entry_count': len(public),
            'code_path_count': len(code), 'input_path_count': len(inputs),
            'shared_code_input_path_count': len(set(code) & set(inputs)),
            'selected_unique_path_count': len(selected),
            'selected_logical_bytes': sum(row['bytes'] for row in rows),
            'all_selected_frozen_paths_equal': True, 'files': rows,
            'proof_kind': 'LOCAL_RAW_SHA256_AND_CANONICAL_GIT_BLOB_SHA1_MATCH_PINNED_PUBLIC_TREE',
            'outer_independent_immutable_metadata_fetch_required': True,
            'all_public_blobs_individually_http_downloaded': False,
            'unselected_public_blob_content_reads': 0,
            'runtime_files_read': 0, 'project_module_imports': 0,
            'network_calls': 0, 'git_subprocess_calls': 0,
            'reservation_authorized': False, 'rng_authorized': False,
            'execution_authorized': False, 'scientific_execution_authorized': False,
            'transport_integration_qualified': False,
            'complete_runtime_freeze_validated': False,
            'scientific_source_certificate_validated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('root', 'freeze', 'freeze-sha256', 'commit-readback',
                 'commit-readback-sha256', 'tree-readback', 'tree-readback-sha256',
                 'expected-commit', 'expected-tree'):
        parser.add_argument('--' + flag, required=True)
    for flag in ('expected-code-count', 'expected-input-count', 'expected-unique-count'):
        parser.add_argument('--' + flag, required=True, type=int)
    arguments = vars(parser.parse_args(argv))
    arguments['freeze_path'] = arguments.pop('freeze')
    arguments['commit_readback_path'] = arguments.pop('commit_readback')
    arguments['tree_readback_path'] = arguments.pop('tree_readback')
    try:
        result = prove_source_bytes(**arguments)
    except (ValueError, OSError) as error:
        parser.exit(2, 'public-source proof refused: ' + str(error) + '\n')
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    return 0


if __name__ == '__main__':
    main()
