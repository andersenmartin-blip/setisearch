#!/usr/bin/env python3
"""Install separately pinned public Git metadata and approved local UTF-8 blobs.

No network, checkout, or unselected blob-content read is performed. HEAD and
index remain untouched unless the caller explicitly requests --align-head.
Only unsigned Git API commits whose supported canonical serialization exactly
hashes to the independently expected commit are admitted.
"""

import argparse
import datetime
import hashlib
import itertools
import json
import os
from pathlib import PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

SCHEMA = "radio-native-v3-public-git-metadata-import-spec-v1"
METADATA_LIMIT = 128 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
_REGULAR_MODES = frozenset(("100644", "100755"))
_TREE_MODES = {"040000": "tree", "100644": "blob", "100755": "blob",
               "120000": "blob", "160000": "commit"}


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


def _object_sha(kind, data):
    return hashlib.sha1(kind.encode('ascii') + b' ' + str(len(data)).encode('ascii')
                        + b'\0' + data).hexdigest()


def _tree_objects(tree, expected_tree):
    inventory = _tree_inventory(tree, expected_tree)
    groups = {'': []}
    for path, entry in inventory.items():
        parent = path.rsplit('/', 1)[0] if '/' in path else ''
        groups.setdefault(parent, []).append(entry)
        if entry['type'] == 'tree':
            groups.setdefault(path, [])
    objects = {}
    for directory, entries in groups.items():
        entries.sort(key=lambda entry: entry['path'].rsplit('/', 1)[-1].encode('utf-8')
                     + (b'/' if entry['type'] == 'tree' else b''))
        body = b''.join((('40000' if entry['mode'] == '040000' else entry['mode']).encode('ascii')
                        + b' ' + entry['path'].rsplit('/', 1)[-1].encode('utf-8')
                        + b'\0' + bytes.fromhex(entry['sha'])) for entry in entries)
        wanted = expected_tree if not directory else inventory[directory]['sha']
        if _object_sha('tree', body) != wanted:
            raise ValueError('Canonical tree bytes differ from expected Git object')
        objects[wanted] = ('tree', body)
    return inventory, objects


def _timezone(value):
    if not isinstance(value, str) or re.fullmatch('[+-][0-9]{4}', value) is None:
        raise ValueError('Exact numeric timezone candidate required')
    hours, minutes = int(value[1:3]), int(value[3:])
    signed = (hours * 60 + minutes) * (-1 if value[0] == '-' else 1)
    if minutes >= 60 or not -720 <= signed <= 840:
        raise ValueError('Timezone candidate outside supported -1200..+1400 range')
    return value


def _identity(identity):
    if not isinstance(identity, dict) or not {'name', 'email', 'date'} <= set(identity):
        raise ValueError('Complete Git author/committer metadata required')
    for key in ('name', 'email'):
        if (not isinstance(identity[key], str) or not identity[key]
                or any(character in identity[key] for character in '\n\r\0<>')):
            raise ValueError('Canonical single-line Git identity required')
    date = identity['date']
    if not isinstance(date, str):
        raise ValueError('ISO author/committer date required')
    try:
        instant = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('ISO author/committer date required') from error
    if instant.tzinfo is None or instant.microsecond:
        raise ValueError('Exact timezone-aware integral-second Git date required')
    timestamp = int(instant.timestamp())
    return identity['name'] + ' <' + identity['email'] + '> ' + str(timestamp)


def _commit_object(commit, expected_sha, expected_tree, timezone_candidates):
    if (commit.get('sha') != expected_sha or not isinstance(commit.get('tree'), dict)
            or commit['tree'].get('sha') != expected_tree):
        raise ValueError('Commit/tree IDs differ from independent manifest pins')
    verification = commit.get('verification')
    if (not isinstance(verification, dict) or verification.get('signature') is not None
            or verification.get('payload') is not None
            or verification.get('verified') is not False
            or verification.get('reason') != 'unsigned'):
        raise ValueError('Only explicitly unsigned supported Git API commits are admitted')
    parents = commit.get('parents')
    if not isinstance(parents, list):
        raise ValueError('Ordered Git commit parents required')
    parent_sha = []
    for parent in parents:
        if not isinstance(parent, dict):
            raise ValueError('Git parent record required')
        parent_sha.append(_hash(parent.get('sha'), 40, 'parent commit'))
    message = commit.get('message')
    if not isinstance(message, str) or '\0' in message:
        raise ValueError('Supported UTF-8 Git commit message required')
    message.encode('utf-8', 'strict')
    author, committer = _identity(commit.get('author')), _identity(commit.get('committer'))
    prefix = 'tree ' + expected_tree + '\n' + ''.join('parent ' + sha + '\n' for sha in parent_sha)
    supplied = list(dict.fromkeys(_timezone(value) for value in timezone_candidates))
    if len(supplied) > 32:
        raise ValueError('At most 32 explicit timezone candidates are supported')
    # Exact SHA, rather than a presumed timezone, selects the serialization.
    # Cross-zone pairs are bounded to explicit candidates; all supported minute
    # offsets are additionally tried with matching author/committer zones.
    pairs = list(itertools.product(supplied, repeat=2))
    for minutes in range(-720, 841):
        zone = ('-' if minutes < 0 else '+') + '%02d%02d' % divmod(abs(minutes), 60)
        pairs.append((zone, zone))
    pairs = list(dict.fromkeys(pairs))
    matches = {}
    attempts = 0
    for author_zone, committer_zone in pairs:
        header = (prefix + 'author ' + author + ' ' + author_zone + '\n'
                  + 'committer ' + committer + ' ' + committer_zone + '\n\n')
        for suffix in ('', '\n', '\n\n'):
            raw = (header + message + suffix).encode('utf-8')
            attempts += 1
            if _object_sha('commit', raw) == expected_sha:
                matches[raw] = (author_zone, committer_zone, len(suffix))
    if len(matches) != 1:
        raise ValueError('No unique exact supported Git commit serialization matches expected SHA')
    raw = next(iter(matches))
    zones = matches[raw]
    return raw, {'sha': expected_sha, 'tree_sha': expected_tree, 'parents': parent_sha,
                 'author_timezone': zones[0], 'committer_timezone': zones[1],
                 'message_suffix_newlines': zones[2], 'serialization_candidates': attempts}


def _git(root, *arguments, data=None, check=True, index_file=None):
    environment = dict(os.environ)
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE'):
        environment.pop(name, None)
    environment.update({'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'})
    if index_file is not None:
        environment['GIT_INDEX_FILE'] = index_file
    result = subprocess.run(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
                             '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                             *arguments], cwd=root, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=environment, timeout=60)
    if check and result.returncode:
        raise ValueError('Local Git operation refused: ' + result.stderr.decode('utf-8', 'replace')[:2000])
    return result.stdout if check else result


def _index_records(root, index_file=None):
    records = _git(root, 'ls-files', '-v', '-z', index_file=index_file).split(b'\0')
    result = {}
    for record in records:
        if not record:
            continue
        if len(record) < 3 or record[1:2] != b' ':
            raise ValueError('Unexpected Git index flag record')
        path = record[2:].decode('utf-8', 'strict')
        _relative(path)
        result[path] = record[:1].upper() == b'S'
    return result


def _stable_presence(root, paths):
    # Metadata only: never read contents of unselected worktree paths.
    present = {}
    absent = []
    for path in sorted(paths):
        try:
            observed = os.lstat(root + '/' + path)
        except FileNotFoundError:
            absent.append(path)
            continue
        present[path] = (observed.st_dev, observed.st_ino, observed.st_mode, observed.st_nlink,
                         observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns)
    return present, absent


def import_metadata(*, root, manifest_path, manifest_sha256, align_head=None, expected_old_head=None):
    root = _absolute(root)
    manifest_path = _absolute(manifest_path)
    directories = {}
    manifest, manifest_pin = _metadata(manifest_path, manifest_sha256, directories)
    if (set(manifest) - {'schema', 'commits', 'trees', 'blobs', 'timezone_candidates'}
            or manifest.get('schema') != SCHEMA):
        raise ValueError('Exact supported metadata import specification required')
    for section in ('commits', 'trees', 'blobs'):
        if not isinstance(manifest.get(section), list):
            raise ValueError('Explicit metadata import list required: ' + section)
    if not manifest['commits'] or not manifest['trees']:
        raise ValueError('Nonempty independently pinned commit/tree sets required')
    zones = manifest.get('timezone_candidates', ['+0200', '+0000'])
    if not isinstance(zones, list):
        raise ValueError('Explicit timezone candidate list required')
    if _git(root, 'rev-parse', '--show-toplevel').decode().strip() != root:
        raise ValueError('Exact repository worktree root required')
    git_directory = _git(root, 'rev-parse', '--absolute-git-dir').decode().strip()
    _absolute(git_directory)
    index_path = git_directory + '/index'
    original_index_pin = _read_file(index_path, directories, metadata=True)
    original_index_pin.pop('raw')
    original_head = _git(root, 'rev-parse', '--verify', 'HEAD').decode().strip()
    original_index = _index_records(root)
    original_present, original_absent = _stable_presence(root, original_index)
    objects, trees, commits, metadata_pins = {}, {}, [], []
    for record in manifest['trees']:
        if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'sha'}:
            raise ValueError('Exact pinned recursive tree record required')
        sha = _hash(record['sha'], 40, 'public tree')
        tree, pin = _metadata(_absolute(record['path']), record['sha256'], directories)
        inventory, tree_objects = _tree_objects(tree, sha)
        if sha in trees:
            raise ValueError('Duplicate pinned root tree')
        trees[sha] = inventory
        for object_sha, value in tree_objects.items():
            if object_sha in objects and objects[object_sha] != value:
                raise ValueError('Conflicting Git object bytes')
            objects[object_sha] = value
        metadata_pins.append((record['path'], pin))
    expected_commits = set()
    for record in manifest['commits']:
        if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'sha', 'tree_sha'}:
            raise ValueError('Exact pinned commit record required')
        sha, tree_sha = _hash(record['sha'], 40, 'public commit'), _hash(record['tree_sha'], 40, 'commit tree')
        if sha in expected_commits or tree_sha not in trees:
            raise ValueError('Duplicate commit or unavailable pinned complete commit tree')
        expected_commits.add(sha)
        commit, pin = _metadata(_absolute(record['path']), record['sha256'], directories)
        body, receipt = _commit_object(commit, sha, tree_sha, zones)
        objects[sha] = ('commit', body)
        commits.append(receipt)
        metadata_pins.append((record['path'], pin))
    if (align_head is None) != (expected_old_head is None):
        raise ValueError('--align-head and --expected-old-head must be supplied together')
    if align_head is not None:
        _hash(align_head, 40, 'requested aligned HEAD')
        if align_head not in expected_commits or original_head != _hash(expected_old_head, 40, 'old HEAD'):
            raise ValueError('HEAD alignment requires imported commit and exact current HEAD pin')
    selected = {}
    for record in manifest['blobs']:
        if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'git_blob_sha', 'tree_sha'}:
            raise ValueError('Exact approved local UTF-8 blob record required')
        path, tree_sha = _relative(record['path']), _hash(record['tree_sha'], 40, 'blob tree')
        if path in selected or tree_sha not in trees:
            raise ValueError('Duplicate selected local path or unavailable blob tree')
        expected_blob = trees[tree_sha].get(path)
        if (expected_blob is None or expected_blob['type'] != 'blob'
                or expected_blob['mode'] not in _REGULAR_MODES
                or expected_blob['sha'] != _hash(record['git_blob_sha'], 40, 'approved blob')):
            raise ValueError('Selected approved blob differs from pinned public tree')
        selected[path] = (record, expected_blob)
    signatures = {path: _stat_file(root + '/' + path, directories) for path in selected}
    if len({value[:2] for value in signatures.values()}) != len(signatures):
        raise ValueError('Aliased selected local blobs refused')
    blob_receipts = []
    total = 0
    for path, (record, expected_blob) in selected.items():
        pin = _read_file(root + '/' + path, directories, signatures[path], metadata=True)
        raw = pin.pop('raw')
        raw.decode('utf-8', 'strict')
        total += len(raw)
        if total > METADATA_LIMIT:
            raise ValueError('Aggregate approved text blob bytes exceed bounded import limit')
        if (pin['sha256'] != _hash(record['sha256'], 64, 'approved local blob SHA256')
                or pin['git_blob_sha'] != expected_blob['sha'] or pin['bytes'] != expected_blob['size']):
            raise ValueError('Selected local bytes differ from public tree and approved SHA256')
        objects[pin['git_blob_sha']] = ('blob', raw)
        blob_receipts.append({'path': path, 'sha256': pin['sha256'], 'git_blob_sha': pin['git_blob_sha'],
                              'bytes': pin['bytes'], 'tree_sha': record['tree_sha']})
    for path, expected in signatures.items():
        if _stat_file(root + '/' + path, directories) != expected:
            raise ValueError('Selected local bytes changed before object installation')
    for path, pin in [(manifest_path, manifest_pin), *metadata_pins]:
        if _stat_file(path, directories) != pin['signature']:
            raise ValueError('Pinned metadata changed before object installation')
    if _git(root, 'rev-parse', '--verify', 'HEAD').decode().strip() != original_head:
        raise ValueError('HEAD changed before object installation')
    if (_index_records(root) != original_index
            or _stat_file(index_path, directories) != original_index_pin['signature']):
        raise ValueError('Index changed before object installation')
    # All expected hashes are validated before the first irreversible object
    # append. Appending these exact content-addressed objects grants no authority.
    installed = {'tree': 0, 'commit': 0, 'blob': 0}
    for sha, (kind, body) in sorted(objects.items()):
        if _object_sha(kind, body) != sha:
            raise ValueError('Pre-install object digest differs')
        actual = _git(root, 'hash-object', '-w', '-t', kind, '--stdin', data=body).decode().strip()
        if actual != sha:
            raise ValueError('Installed Git object digest differs')
        installed[kind] += 1
    aligned = False
    prepared_index_sha256 = None
    prepared_index_records = None
    if align_head is not None:
        # read-tree is index-only: -u, checkout and reset --hard are never used.
        # Every tree in this complete recursive target has just been installed.
        index_signature = original_index_pin['signature']
        temporary_fd, temporary_index = tempfile.mkstemp(prefix='metadata-import-index-', dir=git_directory)
        os.close(temporary_fd)
        os.unlink(temporary_index)
        index_lock = index_path + '.lock'
        own_lock = False
        try:
            _git(root, 'read-tree', '--reset', align_head, index_file=temporary_index)
            current_index = _index_records(root, index_file=temporary_index)
            after_present, after_absent = _stable_presence(root, current_index)
            if any(after_present.get(path) != value for path, value in original_present.items()):
                raise ValueError('Present tracked worktree identity changed during index-only alignment')
            skip = {path for path, enabled in original_index.items() if enabled and path in current_index}
            skip.update(after_absent)
            if skip:
                _git(root, 'update-index', '--skip-worktree', '-z', '--stdin', index_file=temporary_index,
                     data=b''.join(path.encode('utf-8') + b'\0' for path in sorted(skip)))
            prepared = _read_file(temporary_index, directories, metadata=True)['raw']
            prepared_index_sha256 = hashlib.sha256(prepared).hexdigest()
            prepared_index_records = _index_records(root, index_file=temporary_index)
            # Reserve the ordinary Git index lock before the final HEAD CAS.
            # Preparation failures leave the original HEAD/index untouched.
            lock_fd = os.open(index_lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            own_lock = True
            try:
                if (_stat_file(index_path, directories) != index_signature
                        or _git(root, 'rev-parse', '--verify', 'HEAD').decode().strip() != original_head):
                    raise ValueError('HEAD/index changed before requested alignment commit')
                with os.fdopen(lock_fd, 'wb', closefd=False) as destination:
                    destination.write(prepared)
                    destination.flush()
                    os.fsync(destination.fileno())
                _git(root, 'update-ref', 'HEAD', align_head, original_head)
                try:
                    os.replace(index_lock, index_path)
                except BaseException:
                    # The original index remains intact if the rename fails.
                    # Restore only our exact ref transition, never overwrite a
                    # concurrently changed ref with an unconditional update.
                    _git(root, 'update-ref', 'HEAD', original_head, align_head)
                    raise
                own_lock = False
                aligned = True
            finally:
                os.close(lock_fd)
        finally:
            if own_lock:
                os.unlink(index_lock)
            for leftover in (temporary_index, temporary_index + '.lock'):
                try:
                    os.unlink(leftover)
                except FileNotFoundError:
                    pass
    terminal_head = _git(root, 'rev-parse', '--verify', 'HEAD').decode().strip()
    terminal_index = _index_records(root)
    terminal_index_pin = _read_file(index_path, directories, metadata=True)
    terminal_index_pin.pop('raw')
    terminal_present, terminal_absent = _stable_presence(root, terminal_index)
    if not aligned and (terminal_head != original_head or terminal_index != original_index
            or terminal_index_pin['signature'] != original_index_pin['signature']
            or terminal_index_pin['sha256'] != original_index_pin['sha256']):
        raise ValueError('HEAD/index changed despite object-only import')
    if aligned and (terminal_head != align_head
            or terminal_index_pin['sha256'] != prepared_index_sha256
            or terminal_index != prepared_index_records):
        raise ValueError('Requested exact aligned HEAD/index changed before terminal readback')
    if any(terminal_present.get(path) != value for path, value in original_present.items()):
        raise ValueError('Original present tracked file identity changed')
    for path, expected in signatures.items():
        if _stat_file(root + '/' + path, directories) != expected:
            raise ValueError('Approved selected local file changed during import')
    return {'schema': 'radio-native-v3-public-git-metadata-import-receipt-v1',
            'status': 'PASS_EXACT_PUBLIC_METADATA_AND_APPROVED_LOCAL_BYTES_IMPORTED',
            'manifest_sha256': manifest_sha256, 'repository_root': root,
            'old_head': original_head, 'new_head': terminal_head, 'head_alignment_requested': aligned,
            'original_index_sha256': original_index_pin['sha256'],
            'terminal_index_sha256': terminal_index_pin['sha256'],
            'prepared_aligned_index_sha256': prepared_index_sha256,
            'installed_unique_objects': installed, 'commits': commits,
            'selected_local_utf8_blobs': blob_receipts,
            'selected_local_utf8_blob_bytes': total, 'original_absent_paths': len(original_absent),
            'terminal_absent_paths': len(terminal_absent),
            'terminal_skip_worktree_paths': sum(terminal_index.values()),
            'original_present_tracked_file_stats_unchanged': True,
            'all_metadata_object_hashes_verified_before_write': True,
            'network_git_fetch_or_blob_downloads': 0, 'unselected_blob_content_reads': 0,
            'worktree_write_operations': 0, 'git_configuration_mutations': 0,
            'scientific_execution_authorized': False, 'execution_authorized': False,
            'reservation_authorized': False, 'transport_integration_qualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--align-head')
    parser.add_argument('--expected-old-head')
    arguments = vars(parser.parse_args(argv))
    arguments['manifest_path'] = arguments.pop('manifest')
    try:
        result = import_metadata(**arguments)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as error:
        parser.exit(2, 'public Git metadata import refused: ' + str(error) + '\n')
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n')
    return 0


if __name__ == '__main__':
    main()
