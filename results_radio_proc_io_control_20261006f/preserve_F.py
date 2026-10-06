"""Administrative preservation of the closed F scope; never execute inputs."""
from pathlib import Path
import base64,hashlib,json,os,stat,time,zipfile
BASE=Path('/workspace/scratch/da6462abff17');PREP=Path(__file__).resolve().parent
ROOT=BASE/'radio-proc-io-control-20261006f';HERE=BASE/'proc-io-preservation-20261006f'
BUNDLE=BASE/'SETI_proceskontrol_2026-10-06F_afsluttet.zip'
PREFIX='results_radio_proc_io_control_20261006f/closed'
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
    started=time.monotonic();HERE.mkdir(mode=0o700,exist_ok=True)
    freeze=json.loads((PREP/'freeze.json').read_bytes());result=json.loads((ROOT/'result.json').read_bytes())
    assert result['spent_marker_written'] and result['status'] in ('FAILED_CLOSED','OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION')
    assert not result['runtime_qualified'] and not result['scientific_authority']
    selected={};files=[];directories=[];references=[];extra_runtime=[]
    def select(path,expected=None):
        raw,pin=read(path)
        if expected is not None:assert all(pin[k]==expected[k] for k in ('bytes','sha256','mode'))
        selected[str(path)]=pin;return raw,pin
    for directory,names,filenames in os.walk(ROOT,followlinks=False):
        directory=Path(directory);st=directory.lstat();assert stat.S_ISDIR(st.st_mode)
        directories.append(dict(path=directory.relative_to(ROOT).as_posix(),bytes=st.st_size,
            allocated_bytes=st.st_blocks*512,mode=stat.S_IMODE(st.st_mode),identity=[st.st_dev,st.st_ino]))
        for name in names:assert not (directory/name).is_symlink()
        for filename in sorted(filenames):files.append(select(directory/filename)[1])
    observed={str(Path(p['path']).relative_to(ROOT)):p for p in files}
    expected={p['path']:p for p in result['artifact_inventory']['entries']}
    assert set(observed)==set(expected)|{'result.json','caller-receipt.json'}
    assert all(all(observed[path][k]==pin[k] for k in ('bytes','sha256','mode')) for path,pin in expected.items())
    for pin in freeze['source_pins']+[p for p in freeze['runtime_pins'] if p['path'].startswith(str(PREP)+'/')]:select(pin['path'],pin)
    for path in [PREP/'freeze.json',PREP/'preparation-summary.json',PREP/'publication-metadata.json',
                 BASE/(ROOT.name+'.caller-stdout'),BASE/(ROOT.name+'.caller-stderr'),
                 BASE/'proc-io-admission-20261006f/launcher-arguments.json']:
        select(path)
    for path in sorted(HERE.glob('*.md')):select(path)
    c=json.loads((BASE/'runtime-offline-preservation/preservation-manifest.json').read_bytes())
    c_pins={p['path']:p for p in list(c['actual_root_files'].values())+c['selected_input_files']+c['extra_files']}
    for pin in freeze['runtime_pins']:
        if pin['path'] in selected:continue
        prior=c_pins.get(pin['path'])
        if prior is not None and all(prior[k]==pin[k] for k in ('bytes','sha256','mode')):
            references.append(dict(path=pin['path'],bytes=pin['bytes'],sha256=pin['sha256'],mode=pin['mode'],
                retained_in_complete_C_bundle=True))
        else:extra_runtime.append(select(pin['path'],pin)[1])
    manifest=dict(schema='radio-proc-io-control-closed-preservation-v1',identity=freeze['identity'],scope_status=result['status'],
        root_files=files,root_directories=directories,archived_files=list(selected.values()),
        runtime_references_to_C=references,new_runtime_bodies=extra_runtime,
        base_bundle=dict(filename='SETI_offline_installation_2026-10-05_closed.zip',bytes=189808619,
            sha256='434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a'),
        all_F_root_file_bytes_hashes_modes_match=True,administration_after_closed_scope=True,
        excludes_manifest_itself_and_bundle=True,restoration_is_not_historical_inode_custody=True,
        no_rerun_or_installation=True,runtime_qualified=False,scientific_authority=False,automatic_successor=False)
    mraw=canonical(manifest);(HERE/'preservation-manifest.json').write_bytes(mraw)
    about=b'F is one closed harmless deterministic IO control. Full source/input/result evidence is retained; unchanged base-runtime bytes are in the exact referenced complete C bundle. This supplies no replay, scientific allocation, native certificate or per-file IO attribution authority.\n'
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
        runtime_C_references=len(references),new_runtime_bodies=len(extra_runtime),archive_regular_entries=len(selected)+2,
        all_regular_entries_complete_hashes_verified=True,manifest_bytes=len(mraw),manifest_sha256=sha(mraw),
        administrative_elapsed_seconds=time.monotonic()-started,administrative_reads_separate_from_closed_F_scope=True)
    sraw=canonical(summary);(HERE/'preservation-summary.json').write_bytes(sraw)
    bodies={};metas={}
    paths=[(Path(p['path']),PREFIX+'/'+Path(p['path']).relative_to(ROOT).as_posix()) for p in files]
    paths += [(p,PREFIX+'/'+p.name) for p in sorted(HERE.glob('*.md'))]
    paths += [(HERE/'preservation-manifest.json',PREFIX+'/preservation-manifest.json'),
              (HERE/'preservation-summary.json',PREFIX+'/preservation-summary.json')]
    paths += [(BASE/(ROOT.name+'.caller-'+kind),PREFIX+'/caller-'+kind+'.utf8') for kind in ('stdout','stderr')]
    for path,name in paths:
        raw,pin=read(path)
        try:
            body=raw.decode('utf-8');assert '\0' not in body;encoding='utf-8'
        except (UnicodeError,AssertionError):body=base64.b64encode(raw).decode()+'\n';name+='.base64';encoding='base64'
        encoded=body.encode();assert len(encoded)<950*1024
        bodies[name]=body;metas[name]=dict(local_path=str(path),raw_bytes=len(raw),raw_sha256=sha(raw),
            bytes=len(encoded),sha256=sha(encoded),encoding=encoding,
            git_blob=hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest())
    (HERE/'result-publication-payload.json').write_bytes(canonical(bodies))
    (HERE/'result-publication-meta.json').write_bytes(canonical(metas))
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
