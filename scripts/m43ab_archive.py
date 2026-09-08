"""Lossless record archive with verified reconstruction of published file hashes.

Records are stored as text before xz compression to avoid recompressing opaque
gzip streams. Original gzip header bytes and SHA256 values are retained. Gzip
reconstruction requires compatible zlib output and fails closed on any mismatch.
"""
import argparse
import gzip
import hashlib
import json
import lzma
import platform
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ab_attribution'
ARCHIVE = OUT/'archive'


def sha(data): return hashlib.sha256(data).hexdigest()


def rebuild(record):
    raw = record['text'].encode('utf-8')
    assert sha(raw) == record['uncompressed_sha256']
    if record['encoding'] == 'gzip6':
        payload = gzip.compress(raw, compresslevel=6, mtime=0)
        payload = bytes.fromhex(record['gzip_header_hex'])+payload[10:]
    else:
        assert record['encoding'] == 'utf-8'
        payload = raw
    if sha(payload) != record['file_sha256']:
        raise ValueError('gzip byte reconstruction differs; use archive-recorded Python/zlib: '+record['path'])
    return payload


def pack():
    paths = sorted((OUT/'inputs').glob('*.json.gz')) + [OUT/'result.json', OUT/'paired_signal_costs.json']
    assert len(paths) == 151
    ARCHIVE.mkdir(exist_ok=True)
    tmp = ARCHIVE/'records.jsonl.xz.tmp'
    rows = []
    with lzma.open(tmp, 'wt', encoding='utf-8', preset=6) as f:
        for path in paths:
            data = path.read_bytes(); packed = path.suffix == '.gz'
            raw = gzip.decompress(data) if packed else data
            r = dict(path=path.relative_to(ROOT).as_posix(), file_sha256=sha(data),
                encoding='gzip6' if packed else 'utf-8',
                gzip_header_hex=data[:10].hex() if packed else None,
                uncompressed_sha256=sha(raw), text=raw.decode('utf-8'))
            assert rebuild(r) == data
            f.write(json.dumps(r, separators=(',', ':'))+'\n')
            rows.append({k:v for k,v in r.items() if k != 'text'})
    data = tmp.read_bytes(); parts = []
    for start in range(0, len(data), 524288):
        path = ARCHIVE/f'records.jsonl.xz.part{len(parts):03d}'
        value = data[start:start+524288]; path.write_bytes(value)
        parts.append(dict(path=path.relative_to(ROOT).as_posix(), size=len(value), sha256=sha(value)))
    tmp.unlink()
    manifest = dict(format='m43ab-lossless-record-text-xz-v1', python_version=platform.python_version(),
        zlib_version=zlib.ZLIB_RUNTIME_VERSION, files=rows, parts=parts,
        archive_sha256=sha(data), archive_bytes=len(data), original_files=len(paths),
        local_byte_roundtrip_verified=True)
    (ARCHIVE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('original_files','archive_bytes','archive_sha256')}))


def restore(verify_only=False):
    manifest = json.loads((ARCHIVE/'manifest.json').read_text()); parts = []
    for item in manifest['parts']:
        path = (ROOT/item['path']).resolve()
        assert path.is_relative_to(ARCHIVE.resolve())
        data = path.read_bytes(); assert len(data) == item['size'] and sha(data) == item['sha256']
        parts.append(data)
    packed = b''.join(parts); assert sha(packed) == manifest['archive_sha256']
    records = lzma.decompress(packed).decode('utf-8').splitlines()
    assert len(records) == len(manifest['files'])
    for text, expected in zip(records, manifest['files']):
        record = json.loads(text)
        assert {k:v for k,v in record.items() if k != 'text'} == expected
        path = (ROOT/record['path']).resolve(); assert path.is_relative_to(OUT.resolve())
        payload = rebuild(record)
        if path.exists(): assert path.read_bytes() == payload
        elif not verify_only:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
    print(f'Verified {len(records)} original files; byte-identical reconstruction')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=('pack','restore','verify'))
    a = p.parse_args()
    pack() if a.action == 'pack' else restore(a.action == 'verify')
