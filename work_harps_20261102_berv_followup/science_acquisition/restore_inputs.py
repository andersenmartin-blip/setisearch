"""Verify archived exact FITS bytes and safely restore the local product cache."""
import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'INPUT_ARCHIVE.json').read_bytes())
    chunks = []
    for item in manifest['parts']:
        data = (HERE / item['path']).read_bytes()
        if len(data) != item['bytes'] or digest(data) != item['sha256']:
            raise ValueError('Part mismatch: ' + item['path'])
        chunks.append(data)
    data = b''.join(chunks)
    if len(data) != manifest['archive_bytes'] or digest(data) != manifest['archive_sha256']:
        raise ValueError('Combined archive mismatch')
    expected = {item['path']: item for item in manifest['members']}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError('Archive member list mismatch')
        payloads = []
        for name, item in expected.items():
            destination = (HERE / name).resolve()
            if not destination.is_relative_to(HERE / 'products'):
                raise ValueError('Invalid destination')
            raw = archive.read(name)
            if len(raw) != item['bytes'] or digest(raw) != item['sha256']:
                raise ValueError('Member mismatch: ' + name)
            if destination.exists() and destination.read_bytes() != raw:
                raise FileExistsError('Preserve differing existing file: ' + name)
            payloads.append((destination, raw))
        if not args.verify_only:
            for destination, raw in payloads:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    with destination.open('xb') as stream:
                        stream.write(raw)
    print(json.dumps({'status': 'PASS_EXACT_ARCHIVE_AND_MEMBERS', 'parts': len(chunks),
                      'members': len(expected), 'uncompressed_bytes': sum(item['bytes'] for item in expected.values()),
                      'archive_sha256': manifest['archive_sha256'], 'mode': 'verify_only' if args.verify_only else 'restore',
                      'science_arrays_interpreted': 0}, indent=2))


if __name__ == '__main__':
    main()
