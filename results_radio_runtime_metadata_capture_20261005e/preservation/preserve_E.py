"""Administrative preservation after distinct E closes; never execute inputs."""
from pathlib import Path
import hashlib,json,os,stat,time,zipfile
BASE=Path('/workspace/scratch/da6462abff17');HERE=Path(__file__).resolve().parent
ROOT=BASE/'radio-runtime-metadata-capture-20261005e';PREP=BASE/'runtime-metadata-preparation-E'
BUNDLE=BASE/'SETI_metadata_capture_2026-10-05E_closed.zip'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def read(path):
    path=Path(path);before=path.lstat();assert stat.S_ISREG(before.st_mode)
    raw=path.read_bytes();after=path.lstat()
    facts=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
    assert facts(before)==facts(after) and len(raw)==before.st_size
    return raw,dict(path=str(path),bytes=len(raw),sha256=sha(raw),mode=stat.S_IMODE(before.st_mode),
                    identity=[before.st_dev,before.st_ino],allocated_bytes=before.st_blocks*512)
def main():
    started=time.monotonic();freeze=json.loads((PREP/'freeze.json').read_bytes())
    result=json.loads((ROOT/'result.json').read_bytes());assert result['spent_marker_written']
    assert result['status'] in ('FAILED_CLOSED','OBSERVED_METADATA_ONLY_PENDING_RUNTIME_QUALIFICATION')
    assert not result['runtime_qualified'] and not result['scientific_authority']
    assert result['installed_inputs_after']['whole_byte_hashes_sizes_modes_and_membership_match']
    selected={};files=[];directories=[]
    def select(path,expected=None):
        raw,pin=read(path)
        if expected is not None:assert all(pin[k]==expected[k] for k in ('bytes','sha256'))
        selected[str(path)]=pin
        return raw,pin
    for directory,names,filenames in os.walk(ROOT,followlinks=False):
        directory=Path(directory);st=directory.lstat();assert stat.S_ISDIR(st.st_mode)
        directories.append(dict(path=directory.relative_to(ROOT).as_posix(),bytes=st.st_size,
            allocated_bytes=st.st_blocks*512,mode=stat.S_IMODE(st.st_mode),identity=[st.st_dev,st.st_ino]))
        for filename in sorted(filenames):files.append(select(directory/filename)[1])
    observed={str(Path(p['path']).relative_to(ROOT)):p for p in files}
    expected={p['path']:p for p in result['artifact_inventory']['entries']}
    assert set(observed)==set(expected)|{'result.json','caller-receipt.json'}
    assert all(all(observed[path][k]==pin[k] for k in ('bytes','sha256','mode')) for path,pin in expected.items())
    for pin in freeze['source_pins']+[p for p in freeze['runtime_pins'] if p['path'].startswith(str(PREP)+'/')]:
        _,current=select(pin['path'],pin);assert current['mode']==pin['mode']
    for path in [PREP/'freeze.json',BASE/(ROOT.name+'.caller-stdout'),BASE/(ROOT.name+'.caller-stderr'),
                 BASE/'runtime-metadata-admission-E/launcher-arguments.json',Path(__file__)]:select(path)
    # Preserve the unsplit preflight body and independent terminal review too.
    for path in [BASE/'runtime-metadata-repair-E/metadata-only-preflight.json',HERE/'ACTUAL_REVIEW.md',HERE/'METADATA_REVIEW.md']:
        if path.exists():select(path)
    # Named files outside the already complete C archive are preserved from
    # retained metadata identities. This is administrative byte retention,
    # never continuous loader custody or authority to run those files.
    c=json.loads((BASE/'runtime-offline-preservation/preservation-manifest.json').read_bytes())
    c_pins={p['path']:p for p in list(c['actual_root_files'].values())+c['selected_input_files']+c['extra_files']}
    named={};references=[];new_named=[]
    def visit(value):
        if isinstance(value,dict):
            if set(('path','bytes','sha256','elf','identity')).issubset(value):
                path=value['path'];old=named.get(path)
                if old is not None:assert all(old[k]==value[k] for k in ('bytes','sha256','identity'))
                named[path]=value
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    metadata=ROOT/'native-metadata.json'
    if metadata.exists():visit(json.loads(metadata.read_bytes()))
    for path,pin in sorted(named.items()):
        prior=c_pins.get(path)
        if prior is not None and all(prior[k]==pin[k] for k in ('bytes','sha256')):
            references.append(dict(path=path,bytes=pin['bytes'],sha256=pin['sha256'],retained_in_complete_C_bundle=True))
        else:
            _,current=select(path,pin)
            ident=pin['identity'];assert current['identity']==[ident['device'],ident['inode']]
            new_named.append(current)
    manifest=dict(schema='radio-metadata-E-closed-preservation-v1',identity=freeze['identity'],scope_status=result['status'],
        root_files=files,root_directories=directories,archived_files=list(selected.values()),
        observed_named_file_references_to_C=references,new_observed_named_files=new_named,
        existing_installed_input_files=1038,existing_installed_directories=110,
        base_bundle=dict(filename='SETI_offline_installation_2026-10-05_closed.zip',bytes=189808619,
            sha256='434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a'),
        previous_D_bundle=dict(filename='SETI_metadata_capture_2026-10-05D_closed.zip',bytes=445287,
            sha256='e2d519ae58fb81becf65787b41a8f51d35e1c8653c7d7f648df37d0b929d29c7'),
        all_E_root_file_bytes_hashes_modes_match=True,administration_after_closed_scope=True,
        excludes_manifest_itself_and_bundle=True,restoration_is_not_historical_inode_custody=True,
        no_rerun_or_installation=True,runtime_qualified=False,scientific_authority=False,automatic_successor=False)
    mraw=canonical(manifest);(HERE/'preservation-manifest.json').write_bytes(mraw)
    about=b'E is a single closed engineering metadata capture. Complete raw evidence, sources and preflight are preserved. Reused installed/base bodies remain in the exact referenced complete C bundle; newly observed named external bytes are retained here. This archive establishes neither continuous loader/IO custody nor scientific admission and supplies no replay authority.\n'
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
    _,bundle=read(BUNDLE)
    summary=dict(identity=freeze['identity'],bundle=bundle,scope_status=result['status'],root_files=len(files),root_directories=len(directories),
        root_logical_bytes=sum(p['bytes'] for p in files)+sum(p['bytes'] for p in directories),
        root_allocated_bytes=sum(p['allocated_bytes'] for p in files)+sum(p['allocated_bytes'] for p in directories),
        named_files=len(named),named_file_C_references=len(references),new_named_files=len(new_named),
        archive_regular_entries=len(selected)+2,all_regular_entries_complete_hashes_verified=True,
        manifest_bytes=len(mraw),manifest_sha256=sha(mraw),administrative_elapsed_seconds=time.monotonic()-started,
        administrative_reads_separate_from_closed_E_scope=True)
    (HERE/'preservation-summary.json').write_bytes(canonical(summary));print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
