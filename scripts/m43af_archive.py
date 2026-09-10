"""Lossless M43AF transport archives; does not change scientific measurements."""
import argparse
import base64
import gzip
import io
import json
import lzma
import platform
import zlib
from pathlib import Path

from m43ad_archive import rebuild, sha
from m43e_economical_bank import read_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43af_response'
FORMAT = 'm43af-lossless-record-text-xz-base64-v1'


def inventory(stage):
    decision = read_sealed(OUT / 'model_decision.json')
    if stage == 'training':
        entries = decision['inventory']
        assert len(entries) == 241
        counts = {}
        for entry in entries:
            counts[entry['phase']] = counts.get(entry['phase'], 0) + 1
        assert counts == {'baseline': 1, 'training': 112, 'null_training': 128}
        extra = ['model_decision.json', 'training_grid.json.gz', 'training_audit.json']
        seal = decision['result_sha256']
    else:
        result = read_sealed(OUT / 'result.json')
        audit = read_sealed(OUT / 'audit.json')
        assert result['complete'] and audit['passed']
        assert result['model_decision_sha256'] == decision['result_sha256']
        entries = result['inventory']
        assert len(entries) == (742 if decision['feasible'] else 502)
        extra = ['model_decision.json', 'training_grid.json.gz', 'training_audit.json',
                 'model_publication.json', 'result.json', 'audit.json']
        seal = result['result_sha256']
    paths = []
    for entry in entries:
        path = (ROOT / entry['file']).resolve()
        assert path.is_relative_to((OUT / 'records').resolve())
        assert sha(path.read_bytes()) == entry['file_sha256']
        record = read_sealed(path)
        assert record['result_sha256'] == entry['record_sha256']
        assert record['freeze_commit'] == decision['freeze_commit']
        assert record['config_sha256'] == decision['config_sha256']
        paths.append(path)
    paths.extend((OUT / name).resolve() for name in extra)
    assert len(set(paths)) == len(paths)
    for path in paths:
        read_sealed(path)
    return paths, seal


def pack(stage):
    paths, seal = inventory(stage)
    archive = OUT / (stage + '_archive')
    assert not (archive / 'manifest.json').exists(), 'preserve completed archive'
    archive.mkdir(parents=True, exist_ok=True)
    temporary = archive / 'records.jsonl.xz.tmp'
    rows = []
    with lzma.open(temporary, 'wt', encoding='utf-8', preset=6) as stream:
        for path in paths:
            data = path.read_bytes()
            compressed = path.suffix == '.gz'
            raw = gzip.decompress(data) if compressed else data
            record = dict(path=path.relative_to(ROOT).as_posix(), file_sha256=sha(data),
                encoding='gzip6' if compressed else 'utf-8',
                gzip_header_hex=data[:10].hex() if compressed else None,
                uncompressed_sha256=sha(raw), text=raw.decode('utf-8'))
            assert rebuild(record) == data
            stream.write(json.dumps(record, separators=(',', ':')) + '\n')
            rows.append({k: v for k, v in record.items() if k != 'text'})
    packed = temporary.read_bytes()
    encoded = base64.b64encode(packed)
    parts = []
    for start in range(0, len(encoded), 524288):
        path = archive / f'records.jsonl.xz.b64.part{len(parts):03d}'
        data = encoded[start:start + 524288]
        if path.exists():
            assert path.read_bytes() == data, 'preserve existing archive part'
        else:
            path.write_bytes(data)
        parts.append(dict(path=path.relative_to(ROOT).as_posix(), size=len(data), sha256=sha(data)))
    manifest = dict(format=FORMAT, stage=stage, source_result_sha256=seal,
        transport_encoding='base64', python_version=platform.python_version(),
        zlib_version=zlib.ZLIB_RUNTIME_VERSION, files=rows, parts=parts,
        archive_sha256=sha(packed), archive_bytes=len(packed), original_files=len(paths),
        local_byte_roundtrip_verified=True)
    (archive / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.unlink()
    print(json.dumps(dict(stage=stage, original_files=len(paths), parts=len(parts),
                          archive_bytes=len(packed), archive_sha256=sha(packed))), flush=True)


def restore(stage, verify_only=False):
    archive = OUT / (stage + '_archive')
    manifest = json.loads((archive / 'manifest.json').read_text())
    assert manifest['format'] == FORMAT and manifest['stage'] == stage
    parts = []
    for item in manifest['parts']:
        path = (ROOT / item['path']).resolve()
        assert path.is_relative_to(archive.resolve())
        data = path.read_bytes()
        assert len(data) == item['size'] and sha(data) == item['sha256']
        parts.append(data)
    packed = base64.b64decode(b''.join(parts), validate=True)
    assert len(packed) == manifest['archive_bytes'] and sha(packed) == manifest['archive_sha256']
    count, seen = 0, set()
    with lzma.open(io.BytesIO(packed), 'rt', encoding='utf-8') as stream:
        for line in stream:
            record = json.loads(line)
            assert count < len(manifest['files'])
            assert {k: v for k, v in record.items() if k != 'text'} == manifest['files'][count]
            path = (ROOT / record['path']).resolve()
            assert path.is_relative_to(OUT.resolve()) and path not in seen
            payload = rebuild(record)
            if path.exists():
                assert path.read_bytes() == payload, 'preserve differing existing file'
            elif not verify_only:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            seen.add(path)
            count += 1
    assert count == manifest['original_files'] == len(manifest['files'])
    print(f'Verified {count} original files; byte-identical reconstruction ({stage})', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('pack', 'restore', 'verify'))
    parser.add_argument('--stage', required=True, choices=('training', 'complete'))
    args = parser.parse_args()
    if args.action == 'pack':
        pack(args.stage)
    else:
        restore(args.stage, args.action == 'verify')
