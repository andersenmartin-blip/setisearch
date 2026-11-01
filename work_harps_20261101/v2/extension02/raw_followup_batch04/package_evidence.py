"""Package completed native arrays/reference JSON without altering scientific evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent
PART_BYTES=2*1024*1024


def digest(path):
    h=hashlib.sha256()
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def require(condition,message):
    if not condition:raise RuntimeError(message)


def write_new(path,data):
    if path.exists():
        require(path.is_file()and not path.is_symlink()and path.read_bytes()==data,'Existing output differs: '+str(path))
        return
    with path.open('xb')as stream:stream.write(data)


def main():
    mapping=json.loads((ROOT/'NATIVE_MAPPING.json').read_text())
    figures=json.loads((ROOT/'FIGURE_INDEX.json').read_text())
    require(len(figures)==len(mapping['events'])==mapping['hits']==94,'Incomplete mapping/plot index')
    require({x['review_id']for x in figures}=={x['review_id']for x in mapping['events']},'Plot event set differs')
    require(all((ROOT/x['figure']).is_file()for x in figures),'Missing completed atlas page')
    cutouts={x['cutout']:x['cutout_sha256']for x in mapping['orders']if x.get('cutout')}
    references={x['reference_grid']for x in mapping['spectra']if x.get('reference_grid')}
    native_files={p.relative_to(ROOT).as_posix()for p in(ROOT/'native').glob('*.npz')}
    reference_files={p.relative_to(ROOT).as_posix()for p in(ROOT/'reference').glob('*.json')}
    require(native_files==set(cutouts)and len(native_files)==mapping['extracted_orders'],'Native evidence inventory differs from mapping')
    require(reference_files==references,'Reference inventory differs from mapping')
    names=sorted(native_files|reference_files)
    members=[]
    for name in names:
        path=ROOT/name
        require(path.is_file()and not path.is_symlink(),'Evidence must be regular file: '+name)
        h=digest(path)
        if name in cutouts:require(h==cutouts[name],'Native evidence changed: '+name)
        members.append(dict(path=name,bytes=path.stat().st_size,sha256=h))
    archive_path=ROOT/'EVIDENCE.zip'
    fd,temp_name=tempfile.mkstemp(prefix='evidence_packaging_',suffix='.zip',dir=ROOT)
    os.close(fd);temporary=Path(temp_name)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as archive:
            for member in members:
                info=zipfile.ZipInfo(member['path'],date_time=(1980,1,1,0,0,0))
                info.create_system=3;info.external_attr=0o100644<<16
                info.compress_type=zipfile.ZIP_DEFLATED
                data=(ROOT/member['path']).read_bytes()
                require(hashlib.sha256(data).hexdigest()==member['sha256'],'Evidence changed during packaging')
                archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        with zipfile.ZipFile(temporary)as archive:
            require(archive.namelist()==names and archive.testzip()is None,'ZIP inventory or CRC mismatch')
            for member in members:
                data=archive.read(member['path'])
                require(len(data)==member['bytes']and hashlib.sha256(data).hexdigest()==member['sha256'],'ZIP member hash mismatch')
        if archive_path.exists():
            require(digest(archive_path)==digest(temporary),'Existing evidence ZIP differs')
        else:write_new(archive_path,temporary.read_bytes())
    finally:temporary.unlink(missing_ok=True)
    parts_dir=ROOT/'evidence_archive_parts';parts_dir.mkdir(exist_ok=True)
    parts=[]
    with archive_path.open('rb')as stream:
        for index,data in enumerate(iter(lambda:stream.read(PART_BYTES),b''),1):
            relative=f'evidence_archive_parts/EVIDENCE.zip.part{index:03d}'
            write_new(ROOT/relative,data)
            parts.append(dict(index=index,path=relative,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    require({p.name for p in parts_dir.iterdir()}=={Path(x['path']).name for x in parts},'Unexpected part files')
    archive_manifest=dict(schema='SETI_BATCH04_EVIDENCE_ARCHIVE_V1',archive_filename='EVIDENCE.zip',bytes=archive_path.stat().st_size,sha256=digest(archive_path),member_count=len(members),native_cutouts=len(native_files),reference_grids=len(reference_files),members=members,zip_format=dict(compression='DEFLATE',level=9,timestamp='1980-01-01T00:00:00',mode='regular0644',member_order='lexicographic'),source_hashes={name:digest(ROOT/name)for name in ['NATIVE_MAPPING.json','FIGURE_INDEX.json','FOLLOWUP_FREEZE.json']},scope='Only native/*.npz and reference/*.json. No raw input products, status tables or figures.',verification='Every source/member SHA256, exact inventory and all ZIP CRCs verified. Original evidence retained.')
    manifest_bytes=(json.dumps(archive_manifest,indent=2,allow_nan=False)+'\n').encode()
    write_new(ROOT/'EVIDENCE_ARCHIVE.json',manifest_bytes)
    parts_manifest=dict(schema='SETI_BATCH04_EVIDENCE_PARTS_V1',output_filename='EVIDENCE.zip',bytes=archive_manifest['bytes'],sha256=archive_manifest['sha256'],archive_manifest='EVIDENCE_ARCHIVE.json',archive_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),part_max_bytes=PART_BYTES,parts=parts)
    write_new(ROOT/'EVIDENCE_PARTS.json',(json.dumps(parts_manifest,indent=2,allow_nan=False)+'\n').encode())
    print(json.dumps({k:archive_manifest[k]for k in ['bytes','sha256','member_count','native_cutouts','reference_grids']}|{'parts':len(parts)},indent=2))


if __name__=='__main__':main()
