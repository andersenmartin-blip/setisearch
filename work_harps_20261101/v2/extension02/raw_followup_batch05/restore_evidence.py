"""Verify split evidence ZIP and safely restore missing native/reference files.

Run python3 restore_evidence.py in a repository checkout. Existing identical files
are retained; any differing file or symlink causes refusal before extraction.
Use --destination PATH for a separate directory, or --verify-only to check only.
"""
from pathlib import Path,PurePosixPath
import argparse
import hashlib
import json
import os
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent


def require(condition,message):
    if not condition:raise RuntimeError(message)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def local_path(root,name,allowed_parent=None):
    value=PurePosixPath(name)
    require(not value.is_absolute()and '\\'not in name and len(value.parts)==2 and all(p not in('','..','.')for p in value.parts),'Unsafe member/part path: '+name)
    if allowed_parent is not None:require(value.parts[0]in allowed_parent,'Unexpected evidence directory: '+name)
    path=root.joinpath(*value.parts)
    require(not path.is_symlink()and not path.parent.is_symlink(),'Symlink destination refused: '+name)
    require(path.resolve().is_relative_to(root.resolve()),'Path escapes destination: '+name)
    return path


def restore(source=ROOT,destination=None,verify_only=False):
    source=Path(source).resolve();destination=source if destination is None else Path(destination).resolve()
    parts_manifest=json.loads((source/'EVIDENCE_PARTS.json').read_text())
    require(parts_manifest['schema']=='SETI_BATCH05_EVIDENCE_PARTS_V1','Unexpected parts schema')
    require(parts_manifest['archive_manifest']=='EVIDENCE_ARCHIVE.json'and parts_manifest['output_filename']=='EVIDENCE.zip','Unexpected archive filenames')
    manifest_path=source/'EVIDENCE_ARCHIVE.json'
    require(digest(manifest_path)==parts_manifest['archive_manifest_sha256'],'Archive manifest hash mismatch')
    manifest=json.loads(manifest_path.read_text())
    require(manifest['schema']=='SETI_BATCH05_EVIDENCE_ARCHIVE_V1','Unexpected archive schema')
    require(manifest['sha256']==parts_manifest['sha256']and manifest['bytes']==parts_manifest['bytes'],'Archive manifests disagree')
    parts=parts_manifest['parts']
    require(bool(parts)and[x['index']for x in parts]==list(range(1,len(parts)+1)),'Part order invalid')
    require(len({x['path']for x in parts})==len(parts),'Duplicate part path')
    require(sum(x['bytes']for x in parts)==manifest['bytes'],'Part total differs')
    for part in parts:
        path=local_path(source,part['path'],{'evidence_archive_parts'})
        require(0<part['bytes']<=parts_manifest['part_max_bytes']<=2*1024*1024,'Part size limit differs')
        require(path.is_file()and path.stat().st_size==part['bytes']and digest(path)==part['sha256'],'Part hash/size mismatch: '+part['path'])
    target=source/'EVIDENCE.zip'
    require(not target.is_symlink(),'Archive symlink refused')
    if target.exists():require(target.stat().st_size==manifest['bytes']and digest(target)==manifest['sha256'],'Existing ZIP differs; move it aside explicitly')
    else:
        fd,temp_name=tempfile.mkstemp(prefix='evidence_restore_',suffix='.zip',dir=source)
        temporary=Path(temp_name)
        try:
            with os.fdopen(fd,'wb')as output:
                for part in parts:
                    with(source/part['path']).open('rb')as stream:
                        for block in iter(lambda:stream.read(1024*1024),b''):output.write(block)
            require(temporary.stat().st_size==manifest['bytes']and digest(temporary)==manifest['sha256'],'Assembled ZIP differs')
            with target.open('xb')as output,temporary.open('rb')as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):output.write(block)
        finally:temporary.unlink(missing_ok=True)
    members=manifest['members'];names=[x['path']for x in members]
    require(len(names)==len(set(names))==manifest['member_count'],'Duplicate/count-mismatched members')
    require(names==sorted(names),'Archive member order differs')
    for item in members:
        path=local_path(destination,item['path'],{'native','reference'})
        require((item['path'].startswith('native/')and path.suffix=='.npz')or(item['path'].startswith('reference/')and path.suffix=='.json'),'Unexpected evidence type')
    with zipfile.ZipFile(target)as archive:
        require(archive.namelist()==names and archive.testzip()is None,'ZIP inventory or CRC mismatch')
        # Validate all content and all existing destination files before any extraction.
        for item in members:
            data=archive.read(item['path']);path=local_path(destination,item['path'],{'native','reference'})
            require(len(data)==item['bytes']and hashlib.sha256(data).hexdigest()==item['sha256'],'Member hash/size mismatch: '+item['path'])
            if path.exists():require(path.is_file()and path.stat().st_size==item['bytes']and digest(path)==item['sha256'],'Existing evidence differs; refusing overwrite: '+item['path'])
        created=0
        if not verify_only:
            destination.mkdir(parents=True,exist_ok=True)
            for item in members:
                path=local_path(destination,item['path'],{'native','reference'})
                if path.exists():continue
                path.parent.mkdir(exist_ok=True)
                with path.open('xb')as output:output.write(archive.read(item['path']))
                require(digest(path)==item['sha256'],'Written member differs: '+item['path'])
                created+=1
    result=dict(status='VERIFIED'if verify_only else'RESTORED_AND_VERIFIED',parts=len(parts),members=len(members),created_files=created,archive_sha256=manifest['sha256'],destination=str(destination))
    print(json.dumps(result,indent=2));return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args();restore(destination=args.destination,verify_only=args.verify_only)


if __name__=='__main__':main()
