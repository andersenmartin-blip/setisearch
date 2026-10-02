"""Immutable preparation test attempts; no control or execution authority.

Every attempt has a distinct name. Publication uses a fully written, fsynced
staging file and an exclusive hard-link creation, never a mutable final alias.
Interrupted publication retains its staging evidence and cannot be selected
until the final path is a stable sole-link file. Selection requires an external
raw digest, a coherent passing summary, and current repository source bytes.
These are point-in-time preparation observations, not runtime admission.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'radio-native-v2-preparation-adjacent-suite-v2'
MAX_BYTES = 2 * 1024**2
MAX_ATTEMPT = 1_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def attempt_name(attempt):
    if type(attempt) is not int or not 1 <= attempt <= MAX_ATTEMPT:
        raise ValueError('Bounded positive integer attempt required')
    return f'final-suite-attempt-{attempt}-summary.json'


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Independent exact lowercase raw SHA256 required')
    return value


def _relative(value):
    if (type(value) is not str or not value or len(value.encode()) > 4096
            or value.startswith('/') or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical repository-relative source path required')
    return value


def _pins(value):
    if type(value) is not dict or len(value) > 20000:
        raise ValueError('Bounded source pin map required')
    for path, pin in value.items():
        _relative(path)
        if (type(pin) is not dict or set(pin) != {'bytes', 'sha256'}
                or type(pin['bytes']) is not int or not 0 <= pin['bytes'] <= MAX_BYTES):
            raise ValueError('Exact bounded source pin required')
        _digest(pin['sha256'])


def _summary(raw, attempt):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('Bounded immutable summary bytes required')
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate summary property refused')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite summary refused')))
    if type(value) is not dict or raw != canonical(value) + b'\n':
        raise ValueError('Canonical summary plus newline required')
    if (value.get('schema') != SCHEMA or type(value.get('attempt')) is not int
            or value['attempt'] != attempt or value.get('status') not in ('PASSED', 'FAILED')):
        raise ValueError('Exact attempt identity and disposition required')
    for key in ('test_count', 'failures', 'errors', 'skipped'):
        if type(value.get(key)) is not int or not 0 <= value[key] <= 1_000_000:
            raise ValueError('Exact nonnegative test counter required: ' + key)
    if type(value.get('source_snapshot_unchanged')) is not bool:
        raise ValueError('Exact source snapshot disposition required')
    _pins(value.get('source_and_test_pins'))
    _pins(value.get('initial_source_and_test_pins'))
    if value['status'] == 'PASSED' and (
            not value['test_count'] or value['failures'] or value['errors'] or value['skipped']
            or value['source_snapshot_unchanged'] is not True
            or not value['source_and_test_pins']
            or canonical(value['source_and_test_pins']) != canonical(value['initial_source_and_test_pins'])):
        raise ValueError('Passing status lacks complete unchanged evidence')
    return value


def _directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Absolute directory required')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if not stat.S_ISDIR(current.lstat().st_mode):
            raise ValueError('Directory aliases refused')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if (info.st_dev, info.st_ino, info.st_mode) != _directory_identity(path):
        os.close(fd)
        raise ValueError('Directory changed during open')
    return fd


def _directory_identity(path):
    info = Path(path).lstat()
    return info.st_dev, info.st_ino, info.st_mode


def _same_directory(path, identity):
    fd = _directory(path)
    try:
        info = os.fstat(fd)
        return (info.st_dev, info.st_ino, info.st_mode) == identity
    finally:
        os.close(fd)


def _key(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
        info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_at(directory, name, *, empty=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not int(not empty) <= before.st_size <= MAX_BYTES):
            raise ValueError('Bounded sole-link evidence required')
        parts = []; remaining = before.st_size + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            parts.append(part); remaining -= len(part)
        raw = b''.join(parts); after = os.fstat(fd)
        if (len(raw) != before.st_size or _key(before) != _key(after)
                or _key(after) != _key(os.stat(name, dir_fd=directory, follow_symlinks=False))):
            raise ValueError('Evidence changed during descriptor read')
        return raw
    finally:
        os.close(fd)


def record_attempt(root, attempt, raw):
    """Retain exactly one distinct attempt, including failed dispositions.

Any exception retains existing evidence. An interrupted pending file is never
deleted/reused automatically. The function creates no shared final alias.
"""
    name = attempt_name(attempt)
    _summary(raw, attempt)
    directory = _directory(root)
    info = os.fstat(directory)
    identity = info.st_dev, info.st_ino, info.st_mode
    pending = '.' + name + '.pending'
    try:
        try:
            os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('Existing attempt must be retained')
        fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=directory)
        try:
            position = 0
            while position < len(raw):
                written = os.write(fd, raw[position:])
                if written <= 0:
                    raise OSError('Incomplete summary write')
                position += written
            os.fsync(fd)
        finally:
            os.close(fd)
        if _read_at(directory, pending) != raw or not _same_directory(root, identity):
            raise ValueError('Staging file or directory changed before publication')
        os.link(pending, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.fsync(directory)
        os.unlink(pending, dir_fd=directory)
        os.fsync(directory)
        if _read_at(directory, name) != raw or not _same_directory(root, identity):
            raise ValueError('Published attempt changed before return')
        return {'path':name, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
            'exclusive_complete_file_publication':True, 'file_and_directory_fsync_returned':True,
            'shared_alias_created_or_changed':False, 'execution_authorized':False}
    finally:
        os.close(directory)


def read_selected_summary(root, attempt, expected_sha256, repository_root):
    """Select a named passing attempt using an independently retained raw digest.

Current source checks establish point-in-time bytes only. They do not admit a
protected control, telescope access, allocation or scientific execution.
"""
    name = attempt_name(attempt); _digest(expected_sha256)
    directory = _directory(root)
    try:
        raw = _read_at(directory, name)
    finally:
        os.close(directory)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Selected attempt differs from independent raw digest')
    value = _summary(raw, attempt)
    if value['status'] != 'PASSED':
        raise ValueError('Failed attempt cannot authorize preparation capture')
    repository_root = Path(repository_root)
    base = _directory(repository_root)
    os.close(base)
    for relative, pin in value['source_and_test_pins'].items():
        path = repository_root / relative
        parent = _directory(path.parent)
        try:
            observed = _read_at(parent, path.name, empty=True)
        finally:
            os.close(parent)
        if {'bytes':len(observed), 'sha256':hashlib.sha256(observed).hexdigest()} != pin:
            raise ValueError('Selected attempt source changed: ' + relative)
    return value, {'path':name, 'bytes':len(raw), 'sha256':expected_sha256}
