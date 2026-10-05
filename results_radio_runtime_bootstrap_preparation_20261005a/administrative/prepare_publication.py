"""Prepare lossless bounded Git-tool transport packets from already staged files.

Administrative publication only; never invokes the bootstrap or reads its root.
Large UTF-8 files are split for transport and rejoined before Git publication.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import stat


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'scratch', 'phase', 'base-commit', 'base-tree'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--allowed-prefix', action='append', default=[])
    parser.add_argument('--allowed-path', action='append', default=[])
    args = parser.parse_args()
    repo, scratch = Path(args.repo), Path(args.scratch)
    diff = subprocess.run(['git', 'diff', '--cached', '--name-status', args.base_tree],
                          cwd=repo, text=True, capture_output=True, check=True)
    (scratch / (args.phase + '-diff.stderr')).write_text(diff.stderr)
    rows = []
    for line in diff.stdout.splitlines():
        status, path = line.split('\t')
        if status not in ('A', 'M') or not (path in args.allowed_path or any(path.startswith(p) for p in args.allowed_prefix)):
            raise ValueError(('unexpected staged change', status, path))
        raw = (repo / path).read_bytes()
        raw.decode('utf-8')
        item = (repo / path).lstat()
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
            raise ValueError('publication file must be a sole-link regular object')
        mode = '100755' if stat.S_IMODE(item.st_mode) & 0o111 else '100644'
        rows.append(dict(status=status, path=path, mode=mode, type='blob', bytes=len(raw),
                         sha256=hashlib.sha256(raw).hexdigest(),
                         git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()))
    if not rows:
        raise ValueError('no staged publication changes')
    result = subprocess.run(['git', 'write-tree', '--missing-ok'], cwd=repo,
                            text=True, capture_output=True, check=True)
    (scratch / (args.phase + '-write-tree.stderr')).write_text(result.stderr)
    packets, small = [], []
    small_bytes = 0

    def flush():
        nonlocal small, small_bytes
        if small:
            packets.append(dict(files=small, fragments=[]))
            small, small_bytes = [], 0

    for row in rows:
        content = (repo / row['path']).read_bytes().decode('utf-8')
        if row['bytes'] > 600000:
            flush()
            parts = [content[i:i+330000] for i in range(0, len(content), 330000)]
            for i, part in enumerate(parts):
                packets.append(dict(files=[], fragments=[dict(path=row['path'], part=i, parts=len(parts), content=part)]))
        else:
            if small_bytes + row['bytes'] > 450000:
                flush()
            small.append(dict(row, content=content))
            small_bytes += row['bytes']
    flush()
    bundles = []
    for i, packet in enumerate(packets):
        path = scratch / (args.phase + '-bundle-%03d.json' % i)
        raw = (json.dumps(packet, ensure_ascii=True, separators=(',', ':')) + '\n').encode()
        if len(raw) >= 900000:
            raise ValueError('transport packet exceeds local output cap')
        path.write_bytes(raw)
        bundles.append(dict(path=str(path), bytes=len(raw), files=len(packet['files']), fragments=len(packet['fragments'])))
    aliases = []
    names = subprocess.run(['rg', '--files', '-g', '*transport.json',
                            'results_radio_runtime_bootstrap_preparation_20261005a'], cwd=repo,
                           text=True, capture_output=True, check=False)
    if names.returncode not in (0, 1):
        raise ValueError('transport descriptor discovery failed')
    by_path = {row['path']:row for row in rows}
    for name in names.stdout.splitlines():
        descriptor = json.loads((repo / name).read_bytes())
        if descriptor.get('schema') != 'radio-runtime-bootstrap-lossless-publication-transport-v1' or descriptor.get('path') not in by_path:
            continue
        body = bytearray()
        for part in descriptor['parts']:
            encoded = (repo / part['path']).read_bytes()
            decoded = base64.b64decode(encoded.rstrip(b'\n'), validate=True)
            if base64.b64encode(decoded) + b'\n' != encoded or part['raw_offset'] != len(body) or part['raw_bytes'] != len(decoded) or part['raw_sha256'] != hashlib.sha256(decoded).hexdigest() or part['bytes'] != len(encoded) or part['sha256'] != hashlib.sha256(encoded).hexdigest() or part['git_blob'] != hashlib.sha1(b'blob ' + str(len(encoded)).encode() + b'\0' + encoded).hexdigest() or part['path'] not in by_path:
                raise ValueError('lossless transport part mismatch or not in publication')
            body.extend(decoded)
        target = by_path[descriptor['path']]
        if bytes(body) != (repo / target['path']).read_bytes() or any(descriptor[k] != target[k] for k in ('bytes', 'sha256', 'git_blob')):
            raise ValueError('lossless decoded source body mismatch')
        aliases.append(dict(descriptor, descriptor_path=name, decoded_equal_to_original=True))
    meta = dict(base_commit=args.base_commit, base_tree=args.base_tree, expected_tree=result.stdout.strip(),
                fullbody_aliases=aliases,
                files=rows, file_count=len(rows), bytes=sum(r['bytes'] for r in rows), bundles=bundles)
    path = scratch / (args.phase + '-meta.json')
    path.write_text(json.dumps(meta, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k:v for k,v in meta.items() if k!='files'}, sort_keys=True))


if __name__ == '__main__':
    main()
