"""Publish M43AE ledgers with lossless, streaming record reconstruction."""
import argparse
import base64
import io
import json
import lzma
import gzip
import platform
import zlib
from pathlib import Path
from m43ad_archive import rebuild, sha
from m43e_economical_bank import read_sealed

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43ae_joint_response'
ARCHIVE=OUT/'archive'


def pack():
    result=read_sealed(OUT/'result.json');audit=read_sealed(OUT/'audit.json')
    assert result['complete'] and audit['passed']
    paths=[ROOT/r['file'] for r in result['inventory']]+[OUT/'result.json',OUT/'paired_signal_costs.json']
    assert len(paths)==264 and len(set(paths))==264
    assert not (ARCHIVE/'manifest.json').exists(),'preserve completed archive'
    ARCHIVE.mkdir(exist_ok=True);temporary=ARCHIVE/'records.jsonl.xz.tmp';rows=[]
    with lzma.open(temporary,'wt',encoding='utf-8',preset=9) as f:
        for path in paths:
            data=path.read_bytes();packed=path.suffix=='.gz';raw=gzip.decompress(data) if packed else data
            r=dict(path=path.relative_to(ROOT).as_posix(),file_sha256=sha(data),
                encoding='gzip6' if packed else 'utf-8',gzip_header_hex=data[:10].hex() if packed else None,
                uncompressed_sha256=sha(raw),text=raw.decode('utf-8'))
            assert rebuild(r)==data
            f.write(json.dumps(r,separators=(',',':'))+'\n');rows.append({k:v for k,v in r.items() if k!='text'})
    data=temporary.read_bytes();transport=base64.b64encode(data);parts=[]
    for start in range(0,len(transport),524288):
        path=ARCHIVE/f'records.jsonl.xz.b64.part{len(parts):03d}';value=transport[start:start+524288]
        if path.exists():assert path.read_bytes()==value
        else:path.write_bytes(value)
        parts.append(dict(path=path.relative_to(ROOT).as_posix(),size=len(value),sha256=sha(value)))
    manifest=dict(format='m43ae-lossless-record-text-xz-base64-v1',transport_encoding='base64',
        python_version=platform.python_version(),zlib_version=zlib.ZLIB_RUNTIME_VERSION,
        files=rows,parts=parts,archive_sha256=sha(data),archive_bytes=len(data),original_files=len(paths),
        local_byte_roundtrip_verified=True,result_sha256=result['result_sha256'],audit_sha256=audit['result_sha256'])
    (ARCHIVE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');temporary.unlink()
    print(json.dumps(dict(original_files=len(paths),archive_bytes=len(data),parts=len(parts),archive_sha256=sha(data))),flush=True)


def restore(verify_only=False):
    manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    assert manifest['format']=='m43ae-lossless-record-text-xz-base64-v1'
    assert manifest['original_files']==len(manifest['files'])==264
    parts=[]
    for item in manifest['parts']:
        path=(ROOT/item['path']).resolve();assert path.is_relative_to(ARCHIVE.resolve())
        data=path.read_bytes();assert len(data)==item['size'] and sha(data)==item['sha256'];parts.append(data)
    packed=base64.b64decode(b''.join(parts),validate=True)
    assert len(packed)==manifest['archive_bytes'] and sha(packed)==manifest['archive_sha256']
    count=0;seen=set()
    with lzma.open(io.BytesIO(packed),'rt',encoding='utf-8') as records:
        for text in records:
            record=json.loads(text);assert count<len(manifest['files'])
            assert {k:v for k,v in record.items() if k!='text'}==manifest['files'][count]
            path=(ROOT/record['path']).resolve();assert path.is_relative_to(OUT.resolve()) and path not in seen
            payload=rebuild(record)
            if path.exists():assert path.read_bytes()==payload
            elif not verify_only:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
            seen.add(path);count+=1
    assert count==manifest['original_files']
    print(f'Verified {count} original files; byte-identical reconstruction',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('pack','restore','verify'));a=p.parse_args()
    pack() if a.action=='pack' else restore(a.action=='verify')
