#!/usr/bin/env python3
"""Read-only exact terminal E file/storage inventory for evidence publication.

No workload, retry, reservation, source reconstruction, private ledger copy or
protected write occurs. JSON is printed only; save outside the terminal scope.
Large engineering source inputs and repeated frozen source copies are pinned
as explicit omissions, while every other original raw failure file is selected
for literal publication. The caller independently publishes and reads them.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import sys

METADATA_LIMIT=128*1024*1024
CHUNK_SIZE=1024*1024
SCOPE_NAME='results_radio_native_v3_compact_eight_input_control_20261003e'
PUBLIC_D='acdf53954f85b7dce04473a0fc1a8c2f09750026'


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


def directory_row(path):
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Actual sole non-symlink directory required')
    return {'path': path, 'device': info.st_dev, 'inode': info.st_ino,
            'mode': stat.S_IMODE(info.st_mode), 'links': info.st_nlink,
            'bytes': info.st_size, 'allocated_bytes': info.st_blocks * 512,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def inventory(root):
    root = _absolute(root)
    scope = root + '/' + SCOPE_NAME
    directories, directory_rows, all_paths = {}, [], []
    descriptor = _open_directory(scope, directories)
    os.close(descriptor)
    for current, folders, files in os.walk(scope, followlinks=False):
        directory_rows.append(directory_row(current))
        for name in folders:
            if not stat.S_ISDIR(os.lstat(current + '/' + name).st_mode):
                raise ValueError('Scope contains non-directory/symlink ancestry')
        all_paths.extend(current + '/' + name for name in files)
    all_paths.sort()
    before = {path: _stat_file(path, directories) for path in all_paths}
    if len({value[:2] for value in before.values()}) != len(before):
        raise ValueError('Aliased terminal files refused')
    plan_raw = _read_file(scope + '/plan.json', directories, before[scope + '/plan.json'], metadata=True)
    plan = json.loads(plan_raw['raw'], object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    rows = []
    for path in all_paths:
        relative = path[len(root) + 1:]
        pin = _read_file(path, directories, before[path])
        info = os.lstat(path)
        row = {'path': relative, 'bytes': pin['bytes'], 'sha256': pin['sha256'],
            'git_blob_sha': pin['git_blob_sha'], 'device': info.st_dev, 'inode': info.st_ino,
            'mode': stat.S_IMODE(info.st_mode), 'links': info.st_nlink,
            'allocated_bytes': info.st_blocks * 512, 'mtime_ns': info.st_mtime_ns,
            'ctime_ns': info.st_ctime_ns}
        parts = relative.split('/')
        if 'frozen-code' in parts:
            original = '/'.join(parts[parts.index('frozen-code') + 1:])
            expected = plan['code_files'].get(original)
            if expected != {'bytes': pin['bytes'], 'sha256': pin['sha256']}:
                raise ValueError('Repeated frozen source does not match exact retained plan pin')
            row.update({'publication': 'OMIT_DUPLICATE_FROZEN_PUBLIC_SOURCE_COPY',
                'original_public_path': original, 'original_preparation_commit': PUBLIC_D,
                'retained_plan_pin_equal': True,
                'independent_public_payload_lookup_performed_by_this_inventory': False,
                'omission_preserves_original_local_file': True})
        elif relative.endswith('/deterministic-source.bin') or relative.endswith('/store/items/request-000001/part'):
            row.update({'publication': 'OMIT_LARGE_ORIGINAL_ENGINEERING_INPUT_PIN_ONLY',
                'source_recipe_path': SCOPE_NAME + '/cases/case00/derived/prepare.py',
                'prepared_metadata_path': SCOPE_NAME + '/cases/case00/prepared.json',
                'public_independent_original_input_reconstruction_qualified': False,
                'omission_preserves_original_local_file': True})
        elif any(part.startswith('.radio-native-v3-invocation-ledger-') for part in parts):
            row.update({'publication': 'OMIT_PRIVATE_LEDGER_COPY_PIN_ONLY',
                        'omission_preserves_original_local_file': True})
        else:
            row.update({'publication': 'PUBLISH_LITERAL_ORIGINAL_RAW_BYTES',
                        'public_output_path': relative})
        rows.append(row)
    for path in all_paths:
        if _stat_file(path, directories) != before[path]:
            raise ValueError('Terminal file changed during common inventory window')
    for row in directory_rows:
        if directory_row(row['path']) != row:
            raise ValueError('Terminal directory membership changed during inventory')
    published = [row for row in rows if row['publication'] == 'PUBLISH_LITERAL_ORIGINAL_RAW_BYTES']
    omitted = [row for row in rows if row['publication'] != 'PUBLISH_LITERAL_ORIGINAL_RAW_BYTES']
    return {'schema': 'radio-native-v3-e-terminal-literal-publication-inventory-v1',
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': scope, 'status': 'PASS_READONLY_TERMINAL_SNAPSHOT',
        'files': rows, 'directories': directory_rows,
        'all_file_count': len(rows), 'all_directory_count': len(directory_rows),
        'current_literal_logical_bytes_including_directories': sum(row['bytes'] for row in rows + directory_rows),
        'current_literal_allocated_bytes_including_directories': sum(row['allocated_bytes'] for row in rows + directory_rows),
        'literal_publication_file_count': len(published),
        'literal_publication_file_bytes': sum(row['bytes'] for row in published),
        'maximum_literal_publication_file_bytes': max((row['bytes'] for row in published), default=0),
        'explicit_omission_count': len(omitted),
        'explicit_omission_logical_bytes': sum(row['bytes'] for row in omitted),
        'original_raw_failure_transcripts_selected_for_full_literal_publication': True,
        'public_independent_original_large_input_reconstruction_qualified': False,
        'public_source_copy_origin_requires_outer_d_readback': True,
        'private_ledger_outside_scope_read_or_copied': False,
        'scope_files_modified': 0, 'scope_directories_modified': 0,
        'control_or_case_reexecutions': 0, 'originals_deleted_or_truncated': 0,
        'execution_authorized': False, 'scientific_execution_authorized': False,
        'reservation_authorized': False, 'native_case_executions': 0,
        'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
        'qualification': 'Publication inventory only; original failure dispositions and observer/resource limitations remain unchanged'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    try:
        result = inventory(**vars(parser.parse_args(argv)))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, 'terminal inventory refused: ' + str(error) + '\n')
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))


if __name__ == '__main__':
    main()
