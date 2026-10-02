#!/usr/bin/env python3
"""Read-only runtime hardlink-custody manifest for future activation.

This component does not activate or execute a control. It hashes only frozen
runtime files, closes allowed activation-only hardlink groups inside exact roots,
and requires sole-link custody for every runtime that may be used afterwards.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

SCHEMA = 'radio-native-v2-runtime-custody-manifest-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()


def _absolute(value, label):
    if (type(value) is not str or not value or '\x00' in value
            or not Path(value).is_absolute() or Path(value) != Path(value).absolute()
            or '..' in Path(value).parts):
        raise ValueError('Canonical absolute path required: ' + label)
    return value


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _pin(path):
    path = Path(path)
    digest = hashlib.sha256(); count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Regular runtime file required: ' + str(path))
        offset = 0
        while offset < before.st_size:
            raw = os.pread(fd, min(65536, before.st_size - offset), offset)
            if not raw:
                raise ValueError('Runtime file truncated during hash: ' + str(path))
            digest.update(raw); count += len(raw); offset += len(raw)
        after = os.fstat(fd); named = os.stat(path, follow_symlinks=False)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named):
            raise ValueError('Runtime file identity changed during hash: ' + str(path))
        return {'bytes': count, 'sha256': digest.hexdigest(),
            'nlink': before.st_nlink, '_device': before.st_dev, '_inode': before.st_ino}
    finally:
        os.close(fd)


def build_manifest(*, runtime_paths, runtime_sha256s,
        activation_only_paths, alias_roots):
    """Return a portable manifest or reject incomplete hardlink custody."""
    if (type(runtime_paths) is not list or runtime_paths != sorted(set(runtime_paths))
            or type(runtime_sha256s) is not dict
            or runtime_paths != sorted(runtime_sha256s)):
        raise ValueError('Exact sorted runtime inventory/hash map required')
    if (type(activation_only_paths) is not list
            or activation_only_paths != sorted(set(activation_only_paths))
            or not set(activation_only_paths).issubset(runtime_paths)):
        raise ValueError('Exact activation-only runtime subset required')
    if type(alias_roots) is not list or alias_roots != sorted(set(alias_roots)):
        raise ValueError('Exact sorted alias roots required')
    roots = [Path(_absolute(value, 'alias root')) for value in alias_roots]
    if any(root.is_symlink() or not root.is_dir() for root in roots):
        raise ValueError('Regular alias directory required')
    activation = set(activation_only_paths); groups = {}
    for value in runtime_paths:
        path = Path(_absolute(value, 'runtime'))
        observed = _pin(path)
        if observed['sha256'] != runtime_sha256s[value]:
            raise ValueError('Frozen runtime bytes differ: ' + value)
        if observed['nlink'] == 1:
            continue
        if value not in activation:
            raise ValueError('Post-activation runtime must be sole-link: ' + value)
        if not any(path.parent == root for root in roots):
            raise ValueError('Hardlinked activation runtime outside exact alias roots: ' + value)
        key = (observed['_device'], observed['_inode'])
        group = groups.setdefault(key, {'nlink': observed['nlink'],
            'bytes': observed['bytes'], 'sha256': observed['sha256'],
            'inventory_members': []})
        if any(group[name] != observed[name] for name in ('nlink', 'bytes', 'sha256')):
            raise ValueError('One hardlink group has inconsistent identity')
        group['inventory_members'].append(value)
    aliases = {key: [] for key in groups}
    for root in roots:
        for path in sorted(root.iterdir()):
            if path.is_symlink():
                continue
            info = path.stat(follow_symlinks=False)
            key = (info.st_dev, info.st_ino)
            if key in groups:
                observed = _pin(path)
                group = groups[key]
                if (observed['sha256'] != group['sha256']
                        or observed['bytes'] != group['bytes']
                        or observed['nlink'] != group['nlink']):
                    raise ValueError('Hardlink alias differs during closure')
                aliases[key].append(str(path))
    portable = []
    for key, group in groups.items():
        members = sorted(aliases[key]); inventory_members = sorted(group['inventory_members'])
        if len(members) != group['nlink'] or not set(inventory_members).issubset(members):
            raise ValueError('Activation hardlink group has hidden or missing aliases')
        record = {'alias_members': members, 'bytes': group['bytes'],
            'inventory_members': inventory_members, 'nlink': group['nlink'],
            'sha256': group['sha256']}
        record['group_id'] = hashlib.sha256(canonical(record)).hexdigest()
        portable.append(record)
    portable.sort(key=lambda value: value['group_id'])
    manifest = {'schema': SCHEMA, 'alias_roots': alias_roots,
        'runtime_inventory_paths': len(runtime_paths),
        'activation_only_paths': activation_only_paths,
        'activation_only_runtime_ceases_before_receipt': True,
        'hardlink_groups': portable,
        'hardlinked_inventory_paths': sum(len(value['inventory_members']) for value in portable),
        'hardlink_alias_closure_paths': sum(len(value['alias_members']) for value in portable),
        'material_runtime_paths': len(runtime_paths) - len(activation),
        'material_runtime_sole_link_verified': True,
        'execution_authorized': False, 'scientific_execution_authorized': False,
        'reservation_authorized': False, 'rng_authorized': False,
        'telescope_reads_authorized': False, 'automatic_retry': False}
    return manifest


def validate_manifest(expected, **arguments):
    if type(expected) is not dict or expected.get('schema') != SCHEMA:
        raise ValueError('Exact runtime custody manifest required')
    observed = build_manifest(**arguments)
    if canonical(observed) != canonical(expected):
        changed = sorted(key for key in set(observed) | set(expected)
            if canonical(observed.get(key)) != canonical(expected.get(key)))
        raise ValueError('Runtime custody manifest differs: ' + ','.join(changed))
    return observed
