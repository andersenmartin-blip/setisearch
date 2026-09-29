#!/usr/bin/env python3
"""Verify/restore retained checkpoint bytes; never execute a closed fixture."""
import argparse
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path, PurePosixPath
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=Path(__file__).resolve().parents[1] /
                        'results_radio_physical_evidence_2026-09-29')
    parser.add_argument('--output', type=Path, help='New exclusive directory; omit to verify only')
    args = parser.parse_args()
    manifest = json.loads((args.archive / 'archive_manifest.json').read_bytes())
    pieces = []
    for row in manifest['parts']:
        name = PurePosixPath(row['path'])
        if name.is_absolute() or '..' in name.parts:
            raise ValueError('Unsafe part path')
        data = (args.archive / name).read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('Transport part differs')
        pieces.append(data)
    encoded = b''.join(pieces)
    if len(encoded) != manifest['base64_bytes']:
        raise ValueError('Encoded inventory differs')
    compressed = base64.b64decode(encoded, validate=True)
    if len(compressed) != manifest['xz_bytes'] or sha(compressed) != manifest['xz_sha256']:
        raise ValueError('Compressed archive differs')
    raw = lzma.decompress(compressed)
    if len(raw) != manifest['tar_bytes']:
        raise ValueError('Tar length differs')
    wanted = {r['path']: r for r in manifest['files']}
    restored = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as tar:
        for member in tar:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or '..' in name.parts
                    or member.name not in wanted or member.name in restored):
                raise ValueError('Unexpected, repeated or unsafe archive member')
            data = tar.extractfile(member).read()
            row = wanted[member.name]
            if len(data) != row['bytes'] or sha(data) != row['sha256']:
                raise ValueError('Original member bytes differ')
            restored[member.name] = data
    if set(restored) != set(wanted) or len(restored) != manifest['original_file_count']:
        raise ValueError('Missing original members')
    if sum(map(len, restored.values())) != manifest['original_bytes']:
        raise ValueError('Original total differs')
    if args.output is not None:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in restored.items():
            path = args.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
    print(json.dumps({'status': 'PASS', 'files': len(restored),
                      'original_bytes': sum(map(len, restored.values())),
                      'execution_restart_authorized': False}))


if __name__ == '__main__':
    main()
