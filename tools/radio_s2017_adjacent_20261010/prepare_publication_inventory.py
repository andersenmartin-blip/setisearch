"""Prepare bounded text publication metadata; no values, HTTP, or mutation."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--prefix', default='tools/radio_s2017_adjacent_20261010')
    p.add_argument('files', nargs='+')
    a = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    base = Path('analysis/s2017_next_native')
    rows = []
    seen = set()
    for name in a.files:
        local = Path(name)
        if local.is_absolute() or '..' in local.parts or not local.is_relative_to(base):
            raise ValueError('Only confined new-phase paths may be published')
        path = root / local
        data = path.read_bytes()
        content = data.decode('utf-8', errors='strict')
        if '\x00' in content or path.suffix not in {'.py', '.json', '.md', '.txt', '.csv'}:
            raise ValueError('Only bounded plain text publication')
        target = a.prefix + '/' + local.relative_to(base).as_posix()
        if target in seen:
            raise ValueError('Duplicate repository path')
        seen.add(target)
        rows.append({'local_path': local.as_posix(), 'repo_path': target,
            'byte_count': len(data), 'char_count': len(content),
            'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()})
    result = {'status': 'PREPARED_LOCAL_TEXT_INVENTORY_NOT_PUBLISHED',
        'files': rows, 'file_count': len(rows), 'total_bytes': sum(r['byte_count'] for r in rows)}
    out = root / a.output
    if not out.resolve().is_relative_to(root / base):
        raise ValueError('Inventory destination must remain in new phase')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'path': str(out),
        'files': len(rows), 'bytes': result['total_bytes']}))


if __name__ == '__main__':
    main()
