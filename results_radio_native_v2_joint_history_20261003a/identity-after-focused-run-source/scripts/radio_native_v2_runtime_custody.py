#!/usr/bin/env python3
"""Read-only local runtime custody: full activation, material-only afterwards.

No Git process is launched. Device/inode identities bind held descriptors only
inside one observation; published timestamps/mode/link counts are exact local
custody metadata, not cross-host identity or protection against a false kernel.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'radio-native-v2-runtime-custody-manifest-v2'
HISTORICAL_SCHEMA = 'radio-native-v2-runtime-custody-manifest-v1'
MAX_RUNTIME_PATHS = 16384
MAX_ALIAS_ROOTS = 8
MAX_ALIAS_ENTRIES = 16384
MAX_DIRECTORY_DEPTH = 32
MAX_FILE_BYTES = 512 * 1024**2
AUTHORITY = {'execution_authorized': False, 'scientific_execution_authorized': False,
    'reservation_authorized': False, 'rng_authorized': False,
    'telescope_reads_authorized': False, 'automatic_retry': False}
META_FIELDS = frozenset(('bytes', 'nlink', 'mode', 'uid', 'gid', 'allocated_bytes', 'mtime_ns', 'ctime_ns'))
FILE_FIELDS = META_FIELDS | {'sha256', 'lifecycle'}
MANIFEST_FIELDS = frozenset(('schema', 'alias_roots', 'runtime_files', 'runtime_inventory_paths',
    'activation_only_paths', 'activation_only_runtime_ceases_before_receipt', 'hardlink_groups',
    'hardlinked_inventory_paths', 'hardlink_alias_closure_paths', 'material_runtime_paths',
    'material_runtime_sole_link_verified')) | AUTHORITY.keys()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def manifest_sha256(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _absolute(value, label='path'):
    if (type(value) is not str or not value.startswith('/') or value == '/' or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical absolute path required: ' + label)
    return value


def _sha(value, label):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact lowercase SHA256 required: ' + label)
    return value


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        if path != '/':
            for name in _absolute(os.fspath(path))[1:].split('/'):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd); raise


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
        value.st_uid, value.st_gid, value.st_blocks, value.st_mtime_ns, value.st_ctime_ns)


def _metadata(value):
    return {'bytes': value.st_size, 'nlink': value.st_nlink, 'mode': stat.S_IMODE(value.st_mode),
        'uid': value.st_uid, 'gid': value.st_gid, 'allocated_bytes': value.st_blocks*512,
        'mtime_ns': value.st_mtime_ns, 'ctime_ns': value.st_ctime_ns}


def _same_directory(fd, path):
    again = _directory(path)
    try:
        if _identity(os.fstat(fd)) != _identity(os.fstat(again)):
            raise ValueError('Runtime evidence ancestor directory changed')
    finally: os.close(again)


def _observe(path, *, anchors=None, expected_identity=None, maximum=MAX_FILE_BYTES):
    path = _absolute(os.fspath(path)); parent, name = path.rsplit('/', 1)
    parent = parent or '/'; directory = _directory(parent); fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise ValueError('Bounded regular runtime file required: ' + path)
        if expected_identity is not None and _identity(before) != expected_identity:
            raise ValueError('Runtime alias differs from independently enumerated inode')
        key = (before.st_dev, before.st_ino); cached = anchors.get(key) if anchors is not None else None
        if cached is not None:
            if _identity(before) != cached['identity'] or _identity(os.fstat(cached['fd'])) != cached['identity']:
                raise ValueError('Held runtime hardlink identity changed')
            digest = cached['sha256']
        else:
            hashed = hashlib.sha256(); offset = 0
            while offset < before.st_size:
                raw = os.pread(fd, min(65536, before.st_size-offset), offset)
                if not raw: raise ValueError('Runtime file truncated during hash: ' + path)
                hashed.update(raw); offset += len(raw)
            digest = hashed.hexdigest()
        after = os.fstat(fd); named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named):
            raise ValueError('Runtime file identity changed during hash: ' + path)
        _same_directory(directory, parent)
        if cached is None and anchors is not None and before.st_nlink > 1:
            anchors[key] = {'identity': _identity(before), 'sha256': digest, 'fd': os.dup(fd)}
        return {**_metadata(before), 'sha256': digest, '_device': before.st_dev,
            '_inode': before.st_ino, '_identity': _identity(before)}
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _pin(path):
    return _observe(path)


def read_material_pin(path, *, maximum=MAX_FILE_BYTES):
    observed = _observe(path, maximum=maximum)
    if observed['nlink'] != 1: raise ValueError('Post-activation material file must be sole-link: ' + os.fspath(path))
    return {key: observed[key] for key in ('bytes', 'sha256')}


def bounded_inventory(root, *, suffixes=None, skip_directories=(), maximum=MAX_RUNTIME_PATHS, sole_link=True):
    """Bounded descriptor-relative source tree; special files and aliases veto."""
    root = _absolute(os.fspath(root)); directory = _directory(root); paths = []; visited = set(); entries = 0
    def walk(fd, relative, depth):
        nonlocal entries
        if depth > MAX_DIRECTORY_DEPTH: raise ValueError('Bounded source directory depth exceeded')
        before = os.fstat(fd); key = (before.st_dev, before.st_ino)
        if key in visited: raise ValueError('Source directory alias/revisit refused')
        visited.add(key); names = []
        with os.scandir(fd) as stream:
            for entry in stream:
                entries += 1
                if entries > maximum: raise ValueError('Bounded source inventory exceeded')
                if re.search(r'[\x00-\x1f\x7f/\\]', entry.name): raise ValueError('Canonical source entry name required')
                names.append(entry.name)
        for name in sorted(names):
            info = os.stat(name, dir_fd=fd, follow_symlinks=False); path = relative + name
            if stat.S_ISDIR(info.st_mode):
                if name in skip_directories: continue
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if _identity(os.fstat(child)) != _identity(info): raise ValueError('Source directory changed during traversal')
                    walk(child, path+'/', depth+1)
                finally: os.close(child)
            elif stat.S_ISREG(info.st_mode) and (not sole_link or info.st_nlink == 1):
                if suffixes is None or Path(name).suffix in suffixes: paths.append(root+'/'+path)
            else: raise ValueError('Source inventory alias or special file refused')
        if _identity(before) != _identity(os.fstat(fd)): raise ValueError('Source directory changed during traversal')
    try:
        walk(directory, '', 0); _same_directory(directory, root)
    finally: os.close(directory)
    return sorted(paths)


def _arguments(runtime_paths, runtime_sha256s, activation_only_paths, alias_roots):
    if (type(runtime_paths) is not list or not 0 < len(runtime_paths) <= MAX_RUNTIME_PATHS
            or any(type(path) is not str for path in runtime_paths) or runtime_paths != sorted(set(runtime_paths))
            or type(runtime_sha256s) is not dict or runtime_paths != sorted(runtime_sha256s)):
        raise ValueError('Exact bounded sorted runtime inventory/hash map required')
    for path in runtime_paths: _absolute(path, 'runtime'); _sha(runtime_sha256s[path], path)
    if (type(activation_only_paths) is not list or any(type(path) is not str for path in activation_only_paths)
            or activation_only_paths != sorted(set(activation_only_paths))
            or not set(activation_only_paths).issubset(runtime_paths)):
        raise ValueError('Exact activation-only runtime subset required')
    if (type(alias_roots) is not list or not 0 < len(alias_roots) <= MAX_ALIAS_ROOTS
            or any(type(path) is not str for path in alias_roots) or alias_roots != sorted(set(alias_roots))):
        raise ValueError('Exact bounded sorted alias roots required')
    for root in alias_roots: _absolute(root, 'alias root')
    if any(a.startswith(b+'/') or b.startswith(a+'/') for i,a in enumerate(alias_roots) for b in alias_roots[:i]):
        raise ValueError('Overlapping runtime alias roots refused')


def build_manifest(*, runtime_paths, runtime_sha256s, activation_only_paths, alias_roots):
    """Observe exact caller policy. Freezer must independently derive Git subset."""
    _arguments(runtime_paths, runtime_sha256s, activation_only_paths, alias_roots)
    activation = set(activation_only_paths); groups = {}; anchors = {}; observations = {}; roots = []
    try:
        root_ids = set()
        for path in alias_roots:
            fd = _directory(path); before = os.fstat(fd); key = (before.st_dev, before.st_ino)
            if key in root_ids:
                os.close(fd); raise ValueError('Physical runtime alias root duplicated')
            root_ids.add(key); roots.append((path, fd, _identity(before)))
        for value in runtime_paths:
            observed = _observe(value, anchors=anchors); observations[value] = observed
            if observed['sha256'] != runtime_sha256s[value]: raise ValueError('Frozen runtime bytes differ: ' + value)
            if observed['nlink'] == 1: continue
            if value not in activation: raise ValueError('Post-activation runtime must be sole-link: ' + value)
            if value.rsplit('/', 1)[0] not in alias_roots:
                raise ValueError('Hardlinked activation runtime outside exact alias roots: ' + value)
            key = (observed['_device'], observed['_inode'])
            group = groups.setdefault(key, {'metadata': {k: observed[k] for k in META_FIELDS},
                'sha256': observed['sha256'], 'identity': observed['_identity'], 'inventory_members': []})
            if group['identity'] != observed['_identity']: raise ValueError('One hardlink group has inconsistent identity')
            group['inventory_members'].append(value)
        aliases = {key: [] for key in groups}
        for root, fd, before in roots:
            names = []
            with os.scandir(fd) as stream:
                for entry in stream:
                    if len(names) >= MAX_ALIAS_ENTRIES: raise ValueError('Bounded runtime alias inventory exceeded')
                    names.append(entry.name)
            for name in sorted(names):
                info = os.stat(name, dir_fd=fd, follow_symlinks=False); key = (info.st_dev, info.st_ino)
                if key not in groups: continue
                path = root+'/'+name; observed = _observe(path, anchors=anchors, expected_identity=_identity(info))
                if observed['_identity'] != groups[key]['identity']: raise ValueError('Alias no longer belongs to held runtime group')
                aliases[key].append(path)
            if before != _identity(os.fstat(fd)): raise ValueError('Runtime alias directory changed during closure')
            _same_directory(fd, root)
        portable = []
        for key, group in groups.items():
            members = sorted(aliases[key]); inventory = sorted(group['inventory_members'])
            if len(members) != len(set(members)) or len(members) != group['metadata']['nlink'] or not set(inventory).issubset(members):
                raise ValueError('Activation hardlink group has hidden or missing aliases')
            record = {**group['metadata'], 'alias_members': members, 'inventory_members': inventory, 'sha256': group['sha256']}
            record['group_id'] = manifest_sha256(record); portable.append(record)
        for path, first in observations.items():
            again = _observe(path, anchors=anchors)
            if first['_identity'] != again['_identity'] or first['sha256'] != again['sha256']:
                raise ValueError('Runtime inventory identity changed across closure')
        portable.sort(key=lambda row: row['group_id'])
        files = {path: {**{key: row[key] for key in META_FIELDS}, 'sha256': row['sha256'],
            'lifecycle': 'activation_only' if path in activation else 'material'} for path, row in observations.items()}
        manifest = {'schema': SCHEMA, 'alias_roots': alias_roots, 'runtime_files': files,
            'runtime_inventory_paths': len(runtime_paths), 'activation_only_paths': activation_only_paths,
            'activation_only_runtime_ceases_before_receipt': True, 'hardlink_groups': portable,
            'hardlinked_inventory_paths': sum(len(row['inventory_members']) for row in portable),
            'hardlink_alias_closure_paths': sum(len(row['alias_members']) for row in portable),
            'material_runtime_paths': len(runtime_paths)-len(activation), 'material_runtime_sole_link_verified': True, **AUTHORITY}
        validate_manifest_structure(manifest, runtime_paths=runtime_paths, runtime_sha256s=runtime_sha256s,
            activation_only_paths=activation_only_paths, alias_roots=alias_roots)
        # A last material recheck must not leave an earlier Git closure stale.
        # These held inode/root identities close that in-check race; mutations
        # after their last observation remain an explicit filesystem limit.
        for row in anchors.values():
            if _identity(os.fstat(row['fd'])) != row['identity']:
                raise ValueError('Held runtime hardlink changed after final inventory recheck')
        for path,fd,before in roots:
            if _identity(os.fstat(fd)) != before:
                raise ValueError('Runtime alias root changed after final inventory recheck')
            _same_directory(fd,path)
        return manifest
    finally:
        for row in anchors.values(): os.close(row['fd'])
        for _, fd, _ in roots: os.close(fd)


def validate_manifest_structure(expected, *, runtime_paths, runtime_sha256s, activation_only_paths, alias_roots):
    """Pure metadata validation and exact lifecycle join; no filesystem IO."""
    _arguments(runtime_paths, runtime_sha256s, activation_only_paths, alias_roots)
    if type(expected) is not dict or set(expected) != MANIFEST_FIELDS or expected.get('schema') != SCHEMA:
        raise ValueError('Exact current runtime custody manifest structure required')
    for key, value in AUTHORITY.items():
        if expected[key] is not value: raise ValueError('Runtime custody cannot grant authority: '+key)
    for key in ('activation_only_runtime_ceases_before_receipt', 'material_runtime_sole_link_verified'):
        if expected[key] is not True: raise ValueError('Exact runtime custody requirement required: '+key)
    if expected['alias_roots'] != alias_roots or expected['activation_only_paths'] != activation_only_paths:
        raise ValueError('Frozen runtime custody lifecycle/root policy differs')
    files = expected['runtime_files']; activation = set(activation_only_paths)
    if type(files) is not dict or sorted(files) != runtime_paths: raise ValueError('Exact runtime custody per-path inventory required')
    for path, row in files.items():
        if type(row) is not dict or set(row) != FILE_FIELDS: raise ValueError('Exact portable runtime custody file fields required')
        for key in META_FIELDS:
            if type(row[key]) is not int or row[key] < 0: raise ValueError('Strict nonnegative runtime custody metadata integer required: '+key)
        if row['bytes'] > MAX_FILE_BYTES or row['nlink'] < 1 or row['mode'] > 0o7777 or row['allocated_bytes'] % 512:
            raise ValueError('Bounded regular-file runtime custody metadata required')
        if row['sha256'] != runtime_sha256s[path]: raise ValueError('Runtime custody file/hash inventory differs')
        lifecycle = 'activation_only' if path in activation else 'material'
        if row['lifecycle'] != lifecycle or (lifecycle == 'material' and row['nlink'] != 1):
            raise ValueError('Exact sole-link material runtime lifecycle required')
    groups = expected['hardlink_groups']; aliases = set(); members = set(); ids = []
    if type(groups) is not list or len(groups) > MAX_RUNTIME_PATHS: raise ValueError('Bounded hardlink group list required')
    for group in groups:
        if type(group) is not dict or set(group) != META_FIELDS | {'sha256', 'alias_members', 'inventory_members', 'group_id'}:
            raise ValueError('Exact portable hardlink group structure required')
        _sha(group['group_id'], 'group_id'); _sha(group['sha256'], 'group file')
        if manifest_sha256({k:v for k,v in group.items() if k != 'group_id'}) != group['group_id']:
            raise ValueError('Canonical hardlink group identity differs')
        for key in ('alias_members', 'inventory_members'):
            values = group[key]
            if type(values) is not list or not values or any(type(v) is not str for v in values) or values != sorted(set(values)):
                raise ValueError('Exact unique sorted hardlink group paths required')
            for path in values: _absolute(path, 'group member')
        current = set(group['inventory_members']); all_aliases = set(group['alias_members'])
        if (type(group['nlink']) is not int or group['nlink'] < 2 or len(all_aliases) != group['nlink']
                or not current.issubset(all_aliases) or not current.issubset(activation)
                or aliases & all_aliases or members & current
                or any(path.rsplit('/',1)[0] not in alias_roots for path in all_aliases)):
            raise ValueError('Exact disjoint activation-only hardlink closure required')
        for path in current:
            if any(files[path][k] != group[k] or type(files[path][k]) is not type(group[k]) for k in META_FIELDS | {'sha256'}):
                raise ValueError('Hardlink group/per-path portable identity differs')
        aliases.update(all_aliases); members.update(current); ids.append(group['group_id'])
    if ids != sorted(set(ids)) or members != {path for path,row in files.items() if row['nlink'] > 1}:
        raise ValueError('Exact hardlinked runtime inventory membership required')
    counts = {'runtime_inventory_paths':len(runtime_paths), 'hardlinked_inventory_paths':len(members),
        'hardlink_alias_closure_paths':len(aliases), 'material_runtime_paths':len(runtime_paths)-len(activation)}
    for key, value in counts.items():
        if type(expected[key]) is not int or expected[key] != value: raise ValueError('Exact runtime custody count required: '+key)
    return expected


def _expected(expected, expected_manifest_sha256, arguments):
    _sha(expected_manifest_sha256, 'independently pinned canonical custody manifest')
    if manifest_sha256(expected) != expected_manifest_sha256: raise ValueError('Canonical runtime custody manifest SHA differs')
    supplied = [value is not None for value in arguments.values()]
    if any(supplied) and not all(supplied): raise ValueError('All runtime custody inventory joins must be supplied together')
    if not any(supplied):
        if type(expected) is not dict or type(expected.get('runtime_files')) is not dict:
            raise ValueError('Current runtime custody manifest required')
        arguments = {'runtime_paths':sorted(expected['runtime_files']),
            'runtime_sha256s':{path:row.get('sha256') for path,row in expected['runtime_files'].items()},
            'activation_only_paths':expected.get('activation_only_paths'), 'alias_roots':expected.get('alias_roots')}
    validate_manifest_structure(expected, **arguments)
    return arguments


def validate_activation_runtime(expected, *, expected_manifest_sha256, runtime_paths=None,
        runtime_sha256s=None, activation_only_paths=None, alias_roots=None):
    arguments = _expected(expected, expected_manifest_sha256, dict(runtime_paths=runtime_paths,
        runtime_sha256s=runtime_sha256s, activation_only_paths=activation_only_paths, alias_roots=alias_roots))
    observed = build_manifest(**arguments)
    if canonical(observed) != canonical(expected): raise ValueError('Runtime custody manifest differs from current full topology/metadata')
    return {'schema':SCHEMA+'-activation-check', 'runtime_custody_manifest_sha256':expected_manifest_sha256,
        'complete_runtime_topology_rechecked':True, 'material_runtime_files_rechecked':True,
        'git_processes_launched':0, 'activation_receipt_issued':False, **AUTHORITY}


def validate_material_runtime(expected, *, expected_manifest_sha256):
    """Open only material paths; never scan roots, open Git, or invoke freezer."""
    _expected(expected, expected_manifest_sha256, dict(runtime_paths=None, runtime_sha256s=None,
        activation_only_paths=None, alias_roots=None))
    count = 0
    for path, row in expected['runtime_files'].items():
        if row['lifecycle'] != 'material': continue
        observed = _observe(path)
        actual = {**{key:observed[key] for key in META_FIELDS}, 'sha256':observed['sha256'], 'lifecycle':'material'}
        if canonical(actual) != canonical(row): raise ValueError('Material runtime custody bytes/metadata changed: '+path)
        count += 1
    return {'schema':SCHEMA+'-material-check', 'runtime_custody_manifest_sha256':expected_manifest_sha256,
        'material_runtime_files_rechecked':True, 'material_runtime_paths_checked':count,
        'activation_only_runtime_paths_opened':0, 'activation_alias_roots_enumerated':0,
        'git_processes_launched':0, 'complete_runtime_topology_rechecked':False, **AUTHORITY}


def validate_manifest(expected, **arguments):
    validate_activation_runtime(expected, expected_manifest_sha256=manifest_sha256(expected), **arguments)
    return expected
