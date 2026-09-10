"""Losslessly pack/unpack original M43AI JSON records for public Git storage.

Serialization is a transport layer only; this script never changes scientific
payloads. Every original byte is checked before and after round-trip recovery.
"""
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path


def sha(data):return hashlib.sha256(data).hexdigest()


def pack(root,output):
    records=sorted((root/'results_m43ai_native_validation/records').glob('*.json'))
    if len(records)!=240:
        raise ValueError('Only the complete 240-record native study may be archived')
    lines=[];files=[]
    for p in records:
        data=p.read_bytes()
        # Preserve the original bytes, including exact float spellings/newlines.
        row=dict(path=str(p.relative_to(root)),content=data.decode('utf-8'))
        lines.append((json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode())
        files.append(dict(path=row['path'],bytes=len(data),sha256=sha(data)))
    raw=b''.join(lines)
    packed=lzma.compress(raw,format=lzma.FORMAT_XZ,preset=6)
    encoded=base64.b64encode(packed)
    parts=[encoded[i:i+524288] for i in range(0,len(encoded),524288)]
    manifest=dict(format='m43ai-json-original-bytes-jsonl-xz-base64-v1',records=len(files),files=files,
        raw_jsonl_bytes=len(raw),raw_jsonl_sha256=sha(raw),compressed_bytes=len(packed),compressed_sha256=sha(packed),
        parts=[dict(path=f'records.jsonl.xz.b64.part{i:03d}',bytes=len(data),sha256=sha(data)) for i,data in enumerate(parts)])
    # All destinations are checked before any write.
    payloads={p['path']:data for p,data in zip(manifest['parts'],parts,strict=True)}
    payloads['manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    for name,data in payloads.items():
        if (output/name).exists() and (output/name).read_bytes()!=data:
            raise ValueError('Preserve completed archive')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in payloads.items():(output/name).write_bytes(data)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','parts')}|dict(parts=len(parts))))


def restore(archive,destination):
    m=json.loads((archive/'manifest.json').read_text())
    if m['format']!='m43ai-json-original-bytes-jsonl-xz-base64-v1':
        raise ValueError('Unknown archive format')
    parts=[]
    for entry in m['parts']:
        data=(archive/entry['path']).read_bytes()
        if len(data)!=entry['bytes'] or sha(data)!=entry['sha256']:
            raise ValueError('Archive part differs')
        parts.append(data)
    packed=base64.b64decode(b''.join(parts),validate=True)
    if len(packed)!=m['compressed_bytes'] or sha(packed)!=m['compressed_sha256']:
        raise ValueError('Compressed archive differs')
    raw=lzma.decompress(packed)
    if len(raw)!=m['raw_jsonl_bytes'] or sha(raw)!=m['raw_jsonl_sha256']:
        raise ValueError('Original transport stream differs')
    rows=[json.loads(line) for line in raw.splitlines()]
    if len(rows)!=m['records'] or len(m['files'])!=m['records']:
        raise ValueError('Incomplete archive membership')
    entries={e['path']:e for e in m['files']}
    if len(entries)!=len(rows) or len({r['path'] for r in rows})!=len(rows) or set(entries)!={r['path'] for r in rows}:
        raise ValueError('Duplicate or missing archive identity')
    payloads=[]
    for row in rows:
        name=row['path'];p=(destination/name).resolve()
        if not p.is_relative_to((destination/'results_m43ai_native_validation/records').resolve()) or Path(name).is_absolute():
            raise ValueError('Unsafe archive member path')
        data=row['content'].encode();expected=entries[name]
        if len(data)!=expected['bytes'] or sha(data)!=expected['sha256']:
            raise ValueError('Restored original record bytes differ')
        if p.exists() and p.read_bytes()!=data:
            raise ValueError('Preserve differing restored record')
        payloads.append((p,data))
    for p,data in payloads:
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print(json.dumps(dict(restored=len(payloads),all_original_bytes_exact=True)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('pack','restore'));p.add_argument('--root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args()
    pack(a.root.resolve(),a.archive) if a.action=='pack' else restore(a.archive,a.root.resolve())
