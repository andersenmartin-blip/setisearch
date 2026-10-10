"""Reassemble the three saved RAW parts using only Python's standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path,
                        default=Path(__file__).with_name('RAW_ARCHIVE_PARTS_PLAN.json'))
    parser.add_argument('--parts-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    plan = json.loads(args.manifest.read_text())
    if plan['schema'] != 'SETI_BYTE_EXACT_RAW_ARCHIVE_PARTS_V1':
        raise ValueError('Unsupported archive-part manifest')
    parts = plan['parts']
    if len(parts) != 3 or [x['index'] for x in parts] != [1, 2, 3]:
        raise ValueError('Exactly three ordered parts are required')
    offset = 0
    for part in parts:
        if Path(part['filename']).name != part['filename'] or part['source_offset'] != offset:
            raise ValueError('Invalid part name or byte offset')
        offset += part['bytes']
        if (args.parts_dir / part['filename']).stat().st_size != part['bytes']:
            raise ValueError('Part size differs: ' + part['filename'])
    if offset != plan['original_archive_bytes']:
        raise ValueError('Combined archive size differs')
    output = args.output or args.parts_dir / plan['original_archive_filename']
    temporary = output.with_name(output.name + '.assembling')
    if output.exists() or temporary.exists():
        raise FileExistsError('Output or partial output already exists; no file is overwritten')
    whole = hashlib.sha256()
    with temporary.open('xb') as assembled:
        for part in parts:
            digest = hashlib.sha256()
            with (args.parts_dir / part['filename']).open('rb') as source:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
                    whole.update(block)
                    assembled.write(block)
            if digest.hexdigest() != part['sha256']:
                raise ValueError('Part SHA256 differs: ' + part['filename'])
        assembled.flush()
        os.fsync(assembled.fileno())
    if temporary.stat().st_size != offset or whole.hexdigest() != plan['original_archive_sha256']:
        raise ValueError('Combined archive SHA256 differs')
    temporary.rename(output)
    print(json.dumps({'status': 'PASS_BYTE_EXACT_RAW_ARCHIVE_REASSEMBLY',
                      'path': str(output), 'bytes': offset, 'sha256': whole.hexdigest()}))


if __name__ == '__main__':
    main()
