"""Package closed BP execution evidence without modifying original artifacts."""
from pathlib import Path
import hashlib
import json
import zipfile
import argparse


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def dump(path,obj):
    with path.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')


def package(root,dest):
    root=root.resolve();dest=dest.resolve();dest.mkdir(exist_ok=False)
    terminal=json.loads((root/'TERMINAL.json').read_text())
    expected={r['path']:r for r in terminal['evidence_files']}
    for rel,r in expected.items():
        p=root/rel
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('Changed evidence '+rel)
    files=sorted(p for p in root.rglob('*') if p.is_file())
    if set(str(p.relative_to(root)) for p in files)!=set(expected)|{'TERMINAL.json'}:raise ValueError('Unexpected execution file set')
    groups=[]
    for seed in sorted((root/'bases').glob('seed*')):
        groups.append((f'SETI_BP_BASE_{seed.name.upper()}_2026-10-31.zip',sorted(p for p in seed.rglob('*') if p.is_file())))
    groups.append(('SETI_BP_CONTROL_EVIDENCE_2026-10-31.zip',[p for p in files if not p.is_relative_to(root/'bases')]))
    archives=[];saved=[]
    for name,members in groups:
        manifest=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=sha(p)) for p in members]
        archive=dest/name
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
            for p in members:z.write(p,p.relative_to(root).as_posix())
            z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:raise ValueError('Archive CRC failed')
            for rec in manifest:
                with z.open(rec['path']) as f:
                    if hashlib.file_digest(f,'sha256').hexdigest()!=rec['sha256']:raise ValueError('Archive payload differs')
        info=dict(file_name=name,bytes=archive.stat().st_size,sha256=sha(archive),members=len(members),files=manifest)
        if archive.stat().st_size>400*1024*1024:
            parts=[]
            with archive.open('rb') as stream:
                i=1
                while chunk:=stream.read(200*1024*1024):
                    part=dest/(name+f'.part{i:02d}')
                    with part.open('xb') as f:f.write(chunk)
                    parts.append(dict(file_name=part.name,bytes=part.stat().st_size,sha256=sha(part)))
                    saved.append(str(part));i+=1
            with archive.open('rb') as original:
                for part in parts:
                    data=(dest/part['file_name']).read_bytes()
                    if original.read(len(data))!=data:raise ValueError('Part reconstruction mismatch')
                if original.read(1):raise ValueError('Trailing archive data')
            info['parts']=parts
        else:saved.append(str(archive))
        archives.append(info)
        print(json.dumps(dict(archive=name,bytes=info['bytes'],members=len(members))),flush=True)
    result=dict(schema='SETI_BP_EVIDENCE_ARCHIVES_V1',terminal_sha256=sha(root/'TERMINAL.json'),
                terminal_status=terminal['status'],archives=archives,
                execution_file_count=len(files),execution_bytes=sum(p.stat().st_size for p in files))
    manifest_path=dest/'SETI_BP_EVIDENCE_MANIFEST_2026-10-31.json';dump(manifest_path,result);saved.append(str(manifest_path))
    upload=dict(uploads=[dict(local_path=p,purpose='create_library_file',library_artifact_type='other') for p in saved])
    dump(dest/'UPLOAD_REQUEST.json',upload)
    print(json.dumps(dict(status='PASS',upload_files=len(saved),execution_files=len(files))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();package(a.root,a.destination)
