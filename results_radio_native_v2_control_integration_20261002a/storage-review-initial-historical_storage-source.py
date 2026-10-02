#!/usr/bin/env python3
"""Read-only preparation for retained historical storage accounting.

The caller must independently authenticate and retain the expected manifest and
observation byte pins. A supplied digest and a JSON provenance label are not a
signature, activation, or admission. This module never discovers a manifest,
reads a marker, consumes a spend record, launches work, or writes any file.

Held no-follow descriptors, exact metadata, directory membership and raw file
pins establish a bounded current observation under the local kernel/filesystem
trust model. They do not prove future immutability, lifetime accounting, or
protection from privileged rollback. Ordinary reads may update filesystem atime;
atime is deliberately excluded from the stable metadata contract.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MANIFEST_SCHEMA = 'radio-native-v2-retained-storage-manifest-v1'
OBSERVATION_SCHEMA = 'radio-native-v2-retained-storage-observation-v1'
JOIN_SCHEMA = 'radio-native-v2-historical-prospective-storage-join-v1'
LEDGER_STORAGE_SCHEMA = 'radio-native-v2-control-invocation-spend-storage-v1'
ROLES = ('historical_scope', 'historical_ledger')
MAX_ENTRIES = 32768
MAX_PATH_BYTES = 4096
MAX_DEPTH = 64
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_STORAGE_BYTES = 1536 * 1024 * 1024
MAX_INTEGER = (1 << 63) - 1
METADATA_FIELDS = frozenset(('device', 'inode', 'mode', 'nlink', 'uid', 'gid',
    'bytes', 'allocated_bytes', 'mtime_ns', 'ctime_ns'))
OBSERVATION_FIELDS = frozenset(('schema', 'role', 'scope', 'manifest_sha256',
    'rows', 'logical_bytes', 'allocated_bytes', 'entry_count',
    'authenticated_manifest_matched', 'current_observation_stable',
    'read_only', 'execution_authorized'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')


def _integer(value, label, *, minimum=0, maximum=MAX_INTEGER):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Bounded exact integer required: ' + label)
    return value


def _sha(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Exact lowercase SHA256 required')
    return value


def _pin(value):
    if type(value) is not dict or set(value) != {'bytes', 'sha256'}:
        raise ValueError('Exact independently retained bytes/SHA256 pin required')
    _integer(value['bytes'], 'pin bytes', maximum=MAX_STORAGE_BYTES)
    _sha(value['sha256'])
    return value


def _authenticate(value, expected_pin):
    expected_pin = _pin(expected_pin).copy()
    raw = canonical(value)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('Bounded manifest/observation serialization exceeded')
    if (len(raw) != expected_pin['bytes']
            or hashlib.sha256(raw).hexdigest() != expected_pin['sha256']):
        raise ValueError('Value differs from independently retained exact byte pin')
    # Retain the authenticated value, not references a caller could mutate after
    # its pin check. All following filesystem checks use this detached snapshot.
    return json.loads(raw), expected_pin['sha256']


def _components(value):
    if (type(value) is not str or not value
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or len(value.encode('utf-8')) > MAX_PATH_BYTES):
        raise ValueError('Bounded canonical storage path required')
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts) or len(parts) > MAX_DEPTH:
        raise ValueError('Bounded canonical storage path required')
    return parts


def _absolute(value):
    value = os.fspath(value)
    if type(value) is not str or not value.startswith('/') or value == '/':
        raise ValueError('Canonical absolute non-root storage path required')
    _components(value[1:])
    if len(value.encode('utf-8')) > MAX_PATH_BYTES:
        raise ValueError('Bounded canonical absolute storage path required')
    return value


def _relative(value):
    if value == '.':
        return value
    _components(value)
    return value


def _metadata(info):
    value = {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'allocated_bytes': info.st_blocks * 512,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}
    _validate_metadata(value)
    return value


def _validate_metadata(value):
    if type(value) is not dict or set(value) != METADATA_FIELDS:
        raise ValueError('Exact storage metadata required')
    for field in METADATA_FIELDS:
        _integer(value[field], field, minimum=1 if field in ('inode', 'nlink') else 0)
    _integer(value['mode'], 'mode', maximum=0o7777)


def _manifest_header(manifest, scope):
    if (type(manifest) is not dict
            or set(manifest) != {'schema', 'role', 'scope', 'rows'}
            or manifest['schema'] != MANIFEST_SCHEMA
            or manifest['role'] not in ROLES or manifest['scope'] != scope
            or type(manifest['rows']) is not list
            or not 1 <= len(manifest['rows']) <= MAX_ENTRIES):
        raise ValueError('Exact bounded retained storage manifest required')


def _manifest(manifest, scope, expected_pin):
    _manifest_header(manifest, scope)
    manifest, manifest_digest = _authenticate(manifest, expected_pin)
    # The caller may change the original between the initial cheap prebounds
    # and serialization. Apply every header constraint to the authenticated
    # detached object actually used by the observer as well.
    _manifest_header(manifest, scope)
    seen = {}; identities = set(); logical = allocated = 0
    for row in manifest['rows']:
        if type(row) is not dict or row.get('kind') not in ('file', 'directory'):
            raise ValueError('Exact ordinary file/directory manifest row required')
        fields = {'path', 'kind', 'metadata'} | ({'raw_pin'} if row['kind'] == 'file' else set())
        if set(row) != fields:
            raise ValueError('Exact retained manifest row fields required')
        relative = _relative(row['path'])
        if relative in seen:
            raise ValueError('Duplicate retained manifest path rejected')
        _validate_metadata(row['metadata'])
        identity = (row['metadata']['device'], row['metadata']['inode'])
        if identity in identities:
            raise ValueError('Duplicate retained manifest inode alias rejected')
        identities.add(identity); seen[relative] = row
        if row['kind'] == 'file':
            _pin(row['raw_pin'])
            if row['metadata']['nlink'] != 1 or row['raw_pin']['bytes'] != row['metadata']['bytes']:
                raise ValueError('Sole-link file metadata and exact raw pin required')
        logical += row['metadata']['bytes']; allocated += row['metadata']['allocated_bytes']
        if max(logical, allocated) > MAX_STORAGE_BYTES:
            raise ValueError('Original whole storage bound exceeded by retained manifest')
    if sorted(seen) != [row['path'] for row in manifest['rows']]:
        raise ValueError('Canonical sorted retained manifest rows required')
    if '.' not in seen or seen['.']['kind'] != 'directory':
        raise ValueError('Retained root directory manifest row required')
    for relative in seen:
        if relative != '.':
            parent = str(Path(relative).parent)
            if parent not in seen or seen[parent]['kind'] != 'directory':
                raise ValueError('Every retained row requires its manifest directory parent')
            _absolute(scope + '/' + relative)
    if manifest['role'] == 'historical_ledger':
        if (len(seen) != 2 or sum(row['kind'] == 'file' for row in seen.values()) != 1
                or any('/' in path for path in seen)):
            raise ValueError('Historical ledger requires exactly its root and one direct file')
    return seen, manifest_digest, manifest['role']


def _ancestor_identity(info):
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Ordinary storage ancestor directory required')
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def _directory_chain(scope, opened):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    root = os.open('/', flags); opened.append(root)
    chain = [(root, None, None, _ancestor_identity(os.fstat(root)))]
    for name in scope[1:].split('/'):
        parent = chain[-1][0]
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        expected = _ancestor_identity(named)
        fd = os.open(name, flags, dir_fd=parent); opened.append(fd)
        if _ancestor_identity(os.fstat(fd)) != expected:
            raise ValueError('Storage ancestor changed during descriptor open')
        chain.append((fd, parent, name, expected))
    return chain


def _names(fd, expected):
    seen = set()
    with os.scandir(fd) as entries:
        for entry in entries:
            if entry.name not in expected or entry.name in seen:
                raise ValueError('Unexpected retained directory entry rejected')
            seen.add(entry.name)
    if seen != expected:
        raise ValueError('Missing retained directory entry rejected')


def observe_retained_scope(scope, manifest, *, expected_manifest_pin):
    """Observe ONLY the externally authenticated, fully enumerated retained scope.

    Authentication and manifest bounds precede filesystem access. All retained
    descriptors remain held through final metadata/membership/path checks. The
    caller, not this function, establishes where the expected pin came from.
    Files are streamed within unchanged whole-storage limits; no special file,
    symlink, hardlink, extra entry, or partial inventory is accepted.
    """
    scope = _absolute(scope)
    expected, manifest_digest, role = _manifest(manifest, scope, expected_manifest_pin)
    children = {path: set() for path, row in expected.items() if row['kind'] == 'directory'}
    for path in expected:
        if path != '.': children[str(Path(path).parent)].add(Path(path).name)
    opened = []; held = {}; rows = {}
    try:
        chain = _directory_chain(scope, opened)
        def visit(relative, fd, parent, name):
            row = expected[relative]; info = os.fstat(fd)
            if not ((row['kind'] == 'directory' and stat.S_ISDIR(info.st_mode))
                    or (row['kind'] == 'file' and stat.S_ISREG(info.st_mode) and info.st_nlink == 1)):
                raise ValueError('Only ordinary directories and sole-link files may be retained')
            before = _metadata(info)
            if before != row['metadata']:
                raise ValueError('Retained storage metadata differs from authenticated manifest')
            held[relative] = (fd, parent, name, before)
            observed = {'path': scope if relative == '.' else scope + '/' + relative,
                'kind': row['kind'], **before}
            if row['kind'] == 'directory':
                _names(fd, children[relative])
                for child_name in sorted(children[relative]):
                    child_path = child_name if relative == '.' else relative + '/' + child_name
                    child_row = expected[child_path]
                    named = os.stat(child_name, dir_fd=fd, follow_symlinks=False)
                    ordinary = stat.S_ISDIR(named.st_mode) if child_row['kind'] == 'directory' else stat.S_ISREG(named.st_mode)
                    if not ordinary or (child_row['kind'] == 'file' and named.st_nlink != 1):
                        raise ValueError('Special, symlink or hardlink retained entry rejected')
                    if _metadata(named) != child_row['metadata']:
                        raise ValueError('Named retained metadata differs before descriptor open')
                    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
                    if child_row['kind'] == 'directory': flags |= os.O_DIRECTORY
                    child_fd = os.open(child_name, flags, dir_fd=fd); opened.append(child_fd)
                    visit(child_path, child_fd, fd, child_name)
            else:
                digest = hashlib.sha256(); count = 0
                while True:
                    raw = os.read(fd, min(65536, row['raw_pin']['bytes'] + 1 - count))
                    if not raw: break
                    digest.update(raw); count += len(raw)
                    if count > row['raw_pin']['bytes']:
                        raise ValueError('Retained raw file grew beyond authenticated pin')
                observed['raw_pin'] = {'bytes': count, 'sha256': digest.hexdigest()}
                if observed['raw_pin'] != row['raw_pin']:
                    raise ValueError('Retained raw file differs from authenticated pin')
            rows[relative] = observed
        root_fd, parent, name, _ = chain[-1]
        visit('.', root_fd, parent, name)
        for relative, (fd, parent, name, before) in held.items():
            if _metadata(os.fstat(fd)) != before:
                raise ValueError('Retained metadata changed during observation')
            if parent is not None and _metadata(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before:
                raise ValueError('Retained named identity changed during observation')
            if relative in children: _names(fd, children[relative])
        for fd, parent, name, before in chain:
            if (_ancestor_identity(os.fstat(fd)) != before
                    or (parent is not None and _ancestor_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before)):
                raise ValueError('Storage ancestor binding changed during observation')
        ordered = [rows[path] for path in sorted(rows)]
        return {'schema': OBSERVATION_SCHEMA, 'role': role, 'scope': scope,
            'manifest_sha256': manifest_digest, 'rows': ordered,
            'logical_bytes': sum(row['bytes'] for row in ordered),
            'allocated_bytes': sum(row['allocated_bytes'] for row in ordered),
            'entry_count': len(ordered), 'authenticated_manifest_matched': True,
            'current_observation_stable': True, 'read_only': True,
            'execution_authorized': False}
    finally:
        for fd in reversed(opened): os.close(fd)


def _totals(inventory, root, *, raw_pins):
    rows = inventory.get('rows')
    if type(rows) is not list or not 1 <= len(rows) <= MAX_ENTRIES:
        raise ValueError('Bounded nonempty exact storage rows required')
    names = {}; identities = set(); logical = allocated = 0
    for row in rows:
        if type(row) is not dict or row.get('kind') not in ('file', 'directory'):
            raise ValueError('Ordinary file/directory storage row required')
        fields = {'path', 'kind'} | METADATA_FIELDS | ({'raw_pin'} if raw_pins and row['kind'] == 'file' else set())
        if set(row) != fields:
            raise ValueError('Exact storage observation row fields required')
        path = _absolute(row['path'])
        if path != root and not path.startswith(root + '/'):
            raise ValueError('Storage row escapes its canonical inventory root')
        if path in names:
            raise ValueError('Duplicate storage observation path rejected')
        _validate_metadata({field: row[field] for field in METADATA_FIELDS})
        identity = (row['device'], row['inode'])
        if identity in identities:
            raise ValueError('Duplicate storage inode alias rejected')
        identities.add(identity); names[path] = row
        if row['kind'] == 'file':
            if row['nlink'] != 1: raise ValueError('Sole-link observed storage file required')
            if raw_pins:
                _pin(row['raw_pin'])
                if row['raw_pin']['bytes'] != row['bytes']:
                    raise ValueError('Storage raw pin and logical bytes differ')
        logical += row['bytes']; allocated += row['allocated_bytes']
        if max(logical, allocated) > MAX_STORAGE_BYTES:
            raise ValueError('Original whole storage bound exceeded')
    if root not in names or names[root]['kind'] != 'directory':
        raise ValueError('Storage inventory root directory required')
    for path in names:
        if path != root and (str(Path(path).parent) not in names
                or names[str(Path(path).parent)]['kind'] != 'directory'):
            raise ValueError('Complete storage directory ancestry required')
    if (_integer(inventory.get('logical_bytes'), 'logical total') != logical
            or _integer(inventory.get('allocated_bytes'), 'allocated total') != allocated
            or _integer(inventory.get('entry_count'), 'entry count') != len(rows)):
        raise ValueError('Storage totals differ from exact observed rows')
    return rows, identities


def join_historical_storage(historical_scope, historical_ledger, prospective_ledger,
        *, expected_observation_pins):
    """Pure charge-once join of three independently authenticated observations.

    No historical or prospective ledger is opened. The prospective observation
    must come from the unchanged authenticated spend-storage contract. Canonical
    root overlap and any cross-component device/inode alias fail closed. The
    result is present storage overhead for later integration, not whole-control
    qualification or permission to activate/consume/retry anything.
    """
    labels = ('historical_scope', 'historical_ledger', 'prospective_ledger')
    if type(expected_observation_pins) is not dict or set(expected_observation_pins) != set(labels):
        raise ValueError('Exactly three independently retained observation pins required')
    inventories = dict(zip(labels, (historical_scope, historical_ledger, prospective_ledger)))
    roots = {}; components = []; all_rows = []; seen = set(); logical = allocated = 0
    for label, inventory in inventories.items():
        if type(inventory) is not dict:
            raise ValueError('Exact storage observation object required')
        if type(inventory.get('rows')) is not list or len(inventory['rows']) > MAX_ENTRIES:
            raise ValueError('Bounded exact observation rows required')
        inventory, digest = _authenticate(inventory, expected_observation_pins[label])
        if label != 'prospective_ledger':
            if (set(inventory) != OBSERVATION_FIELDS
                    or inventory['schema'] != OBSERVATION_SCHEMA or inventory['role'] != label
                    or any(inventory[field] is not True for field in
                        ('authenticated_manifest_matched', 'current_observation_stable', 'read_only'))
                    or inventory['execution_authorized'] is not False):
                raise ValueError('Authenticated read-only historical storage observation required')
            _sha(inventory['manifest_sha256']); root = _absolute(inventory['scope'])
        else:
            fields = {'schema', 'ledger_root', 'control_scope', 'activation_receipt_sha256',
                'invocation_spending_sha256', 'rows', 'logical_bytes', 'allocated_bytes',
                'entry_count', 'witness_bindings_verified', 'ledger_inventory_exact', 'current_observation_stable'}
            if (set(inventory) != fields or inventory['schema'] != LEDGER_STORAGE_SCHEMA
                    or any(inventory[field] is not True for field in
                        ('witness_bindings_verified', 'ledger_inventory_exact', 'current_observation_stable'))):
                raise ValueError('Exact authenticated prospective spend-storage observation required')
            root = _absolute(inventory['ledger_root']); control = _absolute(inventory['control_scope'])
            for field in ('activation_receipt_sha256', 'invocation_spending_sha256'):
                _sha(inventory[field])
        rows, identities = _totals(inventory, root, raw_pins=label != 'prospective_ledger')
        if label.endswith('ledger') and (len(rows) != 2
                or sum(row['kind'] == 'file' and str(Path(row['path']).parent) == root for row in rows) != 1):
            raise ValueError('Exactly one ledger root directory and direct file required')
        for earlier in roots.values():
            if root == earlier or root.startswith(earlier + '/') or earlier.startswith(root + '/'):
                raise ValueError('Canonical historical/prospective storage roots overlap')
        if identities & seen:
            raise ValueError('Historical/prospective storage device/inode alias rejected')
        roots[label] = root; seen.update(identities)
        logical += inventory['logical_bytes']; allocated += inventory['allocated_bytes']
        if len(all_rows) + len(rows) > MAX_ENTRIES or max(logical, allocated) > MAX_STORAGE_BYTES:
            raise ValueError('Original whole storage or inventory entry bound exceeded by joined storage')
        components.append({'role': label, 'root': root, 'observation_sha256': digest,
            'entry_count': len(rows), 'logical_bytes': inventory['logical_bytes'],
            'allocated_bytes': inventory['allocated_bytes']})
        all_rows.extend({'component': label, **row} for row in rows)
    for root in roots.values():
        if control == root or control.startswith(root + '/') or root.startswith(control + '/'):
            raise ValueError('Prospective control scope overlaps retained storage overhead')
    return {'schema': JOIN_SCHEMA, 'components': components, 'rows': all_rows,
        'logical_bytes': logical, 'allocated_bytes': allocated, 'entry_count': len(all_rows),
        'charged_once': True, 'read_only': True, 'execution_authorized': False,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False}
