"""Administrative preservation of closed D; C's complete input bundle remains its base."""
from pathlib import Path
import hashlib,json,os,stat,zipfile,time
BASE=Path('/workspace/scratch/da6462abff17');HERE=Path(__file__).resolve().parent
ROOT=BASE/'radio-runtime-metadata-capture-20261005d';PREP=BASE/'runtime-metadata-preparation'
BUNDLE=BASE/'SETI_metadata_capture_2026-10-05D_closed.zip'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def read(path):
    path=Path(path);before=path.lstat();assert stat.S_ISREG(before.st_mode)
    raw=path.read_bytes();after=path.lstat();facts=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    assert facts(before)==facts(after) and len(raw)==before.st_size
    return raw,dict(path=str(path),bytes=len(raw),sha256=sha(raw),mode=stat.S_IMODE(before.st_mode),
                    identity=[before.st_dev,before.st_ino],allocated_bytes=before.st_blocks*512)
def main():
    started=time.monotonic();freeze=json.loads((PREP/'freeze.json').read_bytes());result=json.loads((ROOT/'result.json').read_bytes())
    assert result['status']=='FAILED_CLOSED' and result['installed_inputs_after']['whole_byte_hashes_sizes_modes_and_membership_match']
    files=[];directories=[];selected={}
    for directory,names,filenames in os.walk(ROOT,followlinks=False):
        directory=Path(directory);st=directory.lstat();assert stat.S_ISDIR(st.st_mode)
        directories.append(dict(path=directory.relative_to(ROOT).as_posix(),bytes=st.st_size,
            allocated_bytes=st.st_blocks*512,mode=stat.S_IMODE(st.st_mode),identity=[st.st_dev,st.st_ino]))
        for filename in sorted(filenames):
            path=directory/filename;raw,pin=read(path);files.append(pin);selected[str(path)]=pin
    observed={str(Path(p['path']).relative_to(ROOT)):p for p in files}
    expected={p['path']:p for p in result['artifact_inventory']['entries']}
    assert set(observed)==set(expected)|{'result.json','caller-receipt.json'}
    assert all(all(observed[path][k]==pin[k] for k in ('bytes','sha256','mode')) for path,pin in expected.items())
    for pin in freeze['source_pins']+[{k:v for k,v in p.items() if k in ('path','bytes','sha256','mode')} for p in freeze['runtime_pins'] if p['path'].startswith(str(PREP))]:
        raw,current=read(pin['path']);assert all(current[k]==pin[k] for k in ('bytes','sha256','mode'));selected[pin['path']]=current
    for path in [PREP/'freeze.json',BASE/(ROOT.name+'.caller-stdout'),BASE/(ROOT.name+'.caller-stderr'),
                 BASE/'runtime-metadata-admission/launcher-arguments.json',Path(__file__)]:
        raw,pin=read(path);selected[str(path)]=pin
    manifest=dict(schema='radio-metadata-D-closed-preservation-v1',identity=freeze['identity'],scope_status=result['status'],
        root_files=files,root_directories=directories,archived_files=list(selected.values()),
        existing_installed_input_files=1038,existing_installed_directories=110,
        base_bundle=dict(filename='SETI_offline_installation_2026-10-05_closed.zip',bytes=189808619,
            sha256='434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a'),
        all_D_root_file_bytes_hashes_modes_match=True,administration_after_closed_scope=True,
        excludes_manifest_itself_and_bundle=True,restoration_is_not_historical_inode_custody=True,
        no_rerun_or_installation=True,runtime_qualified=False,scientific_authority=False,automatic_successor=False)
    mraw=canonical(manifest);(HERE/'preservation-manifest.json').write_bytes(mraw)
    about=b'D capture is FAILED_CLOSED before scientific importers. Complete D sources and raw failure are preserved. Reused installed/native/base bytes remain in the referenced verified C bundle. No input was reinstalled or old scope rerun. This archive supplies no runtime/scientific qualification.\n'
    with zipfile.ZipFile(BUNDLE,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('ABOUT.txt',about);z.writestr('preservation-manifest.json',mraw)
        for path,pin in sorted(selected.items()):
            raw,current=read(path);assert all(current[k]==pin[k] for k in ('bytes','sha256','mode','identity'))
            info=zipfile.ZipInfo('absolute_paths/'+path.lstrip('/'));info.external_attr=(stat.S_IFREG|pin['mode'])<<16
            z.writestr(info,raw,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(BUNDLE) as z:
        for path,pin in selected.items():
            raw=z.read('absolute_paths/'+path.lstrip('/'));assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256']
        assert z.read('preservation-manifest.json')==mraw and z.read('ABOUT.txt')==about
    raw,pin=read(BUNDLE)
    summary=dict(identity=freeze['identity'],bundle=pin,root_files=len(files),root_directories=len(directories),
        root_logical_bytes=sum(p['bytes'] for p in files)+sum(p['bytes'] for p in directories),
        root_allocated_bytes=sum(p['allocated_bytes'] for p in files)+sum(p['allocated_bytes'] for p in directories),
        archive_regular_entries=len(selected)+2,all_regular_entries_complete_hashes_verified=True,
        manifest_bytes=len(mraw),manifest_sha256=sha(mraw),administrative_elapsed_seconds=time.monotonic()-started,
        administrative_reads_separate_from_closed_D_scope=True)
    (HERE/'preservation-summary.json').write_bytes(canonical(summary));print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
