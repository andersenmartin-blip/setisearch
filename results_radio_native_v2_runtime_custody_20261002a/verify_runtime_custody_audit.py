#!/usr/bin/env python3
"""Reproduce the bounded Git hardlink-topology audit without changing it."""
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
RESULT = Path(__file__).resolve().parent
FREEZE = ROOT / 'config/radio_native_v2_activation_environment_20261002d.runtime.json'
PROTOCOL = ROOT / 'config/radio_native_v2_runtime_custody_remediation_20261002a.protocol.json'


def canonical_file(path):
    raw = path.read_bytes()
    value = json.loads(raw)
    assert json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n' == raw
    return value


def sha256_fd(path):
    digest = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        for offset in range(0, before.st_size, 65536):
            digest.update(os.pread(fd, min(65536, before.st_size - offset), offset))
        after = os.fstat(fd)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_mode,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        assert identity(before) == identity(after) == identity(os.stat(path, follow_symlinks=False))
        return digest.hexdigest(), before
    finally:
        os.close(fd)


def main():
    expected = canonical_file(RESULT / 'audit-summary.json')
    protocol = canonical_file(PROTOCOL)
    freeze = canonical_file(FREEZE)
    paths = freeze['runtime_file_inventory']
    assert len(paths) == expected['total_runtime_inventory_paths']
    groups = {}
    for name in paths:
        digest, info = sha256_fd(name)
        assert digest == freeze['runtime_sha256s'][name]
        if info.st_nlink > 1:
            groups.setdefault((info.st_dev, info.st_ino), {
                'nlink': info.st_nlink, 'bytes': info.st_size, 'sha256': digest,
                'inventory': []})['inventory'].append(name)
    aliases = {}
    for root in protocol['alias_roots']:
        for path in Path(root).iterdir():
            if not path.is_symlink() and path.is_file():
                info = path.stat(follow_symlinks=False)
                key = (info.st_dev, info.st_ino)
                if key in groups:
                    aliases.setdefault(key, []).append(str(path))
    observed = []
    for key, group in groups.items():
        closure = aliases.get(key, [])
        assert len(closure) == group['nlink']
        observed.append({'alias_closure_members': len(closure),
            'bytes': group['bytes'], 'inventory_members': len(group['inventory']),
            'nlink': group['nlink'], 'sha256': group['sha256']})
    observed.sort(key=lambda row: -row['nlink'])
    assert observed == expected['groups']
    assert sum(len(group['inventory']) for group in groups.values()) == expected['hardlinked_inventory_paths']
    assert sum(len(value) for value in aliases.values()) == expected['alias_closure_paths']
    assert sum(group['bytes'] for group in groups.values()) == expected['hardlinked_unique_bytes']
    git_paths = set(freeze['git_runtime_file_inventory']) | {freeze['executables']['git']['resolved']}
    assert all(path in git_paths for group in groups.values() for path in group['inventory'])
    assert expected['material_non_git_hardlinks'] == 0
    print(json.dumps({'status': 'VERIFIED', 'groups': len(groups),
        'inventory_hardlinks': expected['hardlinked_inventory_paths'],
        'alias_closure_paths': expected['alias_closure_paths']},
        sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
