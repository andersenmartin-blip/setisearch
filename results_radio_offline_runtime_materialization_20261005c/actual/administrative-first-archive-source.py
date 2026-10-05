"""Administrative lossless preservation after the closed scope; no native imports."""
from pathlib import Path
import hashlib, json, os, stat, time, zipfile

BASE=Path('/workspace/scratch/da6462abff17')
ROOT=BASE/'radio-offline-runtime-materialization-20261005c'
PREP=BASE/'runtime-offline-preparation'
HERE=Path(__file__).resolve().parent
BUNDLE=BASE/'SETI_offline_installation_2026-10-05_closed.zip'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def identity(st): return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,stat.S_IMODE(st.st_mode),st.st_nlink)
def read(path):
    path=Path(path)
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode): raise ValueError('nonregular preservation source')
    raw=path.read_bytes()
    after=path.lstat()
    if identity(before)!=identity(after) or len(raw)!=before.st_size: raise ValueError('changed preservation source')
    return raw,dict(path=str(path),bytes=len(raw),sha256=sha(raw),device=before.st_dev,inode=before.st_ino,
                    mode=stat.S_IMODE(before.st_mode),allocated_bytes=before.st_blocks*512)
def main():
    started=time.monotonic()
    freeze=json.loads((PREP/'freeze.json').read_bytes())
    gate=json.loads((ROOT/'result.json').read_bytes())
    caller=json.loads((ROOT/'caller-receipt.json').read_bytes())
    if gate['status']!='FAILED_CLOSED' or caller['success'] is not False: raise ValueError('expected closed outcome')
    files={}; directories=[]
    for directory,names,filenames in os.walk(ROOT,followlinks=False):
        directory=Path(directory);st=directory.lstat()
        if not stat.S_ISDIR(st.st_mode):raise ValueError('nonregular directory')
        directories.append(dict(path=directory.relative_to(ROOT).as_posix(),device=st.st_dev,inode=st.st_ino,
                                bytes=st.st_size,allocated_bytes=st.st_blocks*512,mode=stat.S_IMODE(st.st_mode)))
        for name in filenames:
            path=directory/name;raw,item=read(path);files[path.relative_to(ROOT).as_posix()]=item
    expected={x['path']:x for x in gate['artifact_inventory']['entries']}
    if set(files)!=set(expected)|{'result.json','caller-receipt.json'}:raise ValueError('terminal inventory membership mismatch')
    for path,item in expected.items():
        if any(files[path][k]!=item[k] for k in ('bytes','sha256','mode','allocated_bytes')):raise ValueError('terminal file mismatch')
    original_keys={'path','bytes','sha256','mode'}
    current=json.loads((PREP/'current-inputs.json').read_bytes())
    selected=freeze['source_pins']+freeze['runtime_pins']+[freeze['installer_plan_pin']]+[x['pin'] for x in current['seed_pins']]
    selected_by_path={x['path']:x for x in selected}
    selected_rows=[]
    for path,pin in sorted(selected_by_path.items()):
        raw,item=read(path)
        if any(item[k]!=pin[k] for k in original_keys):raise ValueError('selected input mismatch')
        selected_rows.append(item)
    extra=[]
    for path in [PREP/'freeze.json',BASE/'runtime-offline-admission/publication-proof.json',
                 BASE/'runtime-offline-admission/activation-marker.json',BASE/'runtime-offline-admission/launcher-arguments.json',
                 BASE/(ROOT.name+'.caller-stdout'),BASE/(ROOT.name+'.caller-stderr'),Path(__file__)]:
        raw,item=read(path);extra.append(item)
    manifest=dict(schema='radio-closed-scope-preservation-manifest-v1',identity=freeze['identity'],
        administration_after_closed_scope=True,scope_outcome=gate['status'],automatic_successor=False,
        actual_root_files=files,actual_root_directories=directories,selected_input_files=selected_rows,extra_files=extra,
        independent_gate_inventory_matches=True,selected_inputs_match=True,
        excludes_manifest_itself_and_bundle=True,restoration_does_not_restore_historical_inode_custody=True,
        native_runtime_and_all_eleven_scientific_fields_pending=True)
    raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    (HERE/'preservation-manifest.json').write_bytes(raw)
    about=('SETI offline installation, 5 October 2026.\n'
           'Exact NumPy2.3.5/h5py3.16.0/hdf5plugin7.1.0 installed and1028 original member bytes verified.\n'
           'The single scope is FAILED_CLOSED: the metadata collector refused a nonunique ELF PT_LOAD string-table mapping before scientific imports.\n'
           'Contains the actual installed environment, original staged wheels, raw terminal evidence, source and selected runtime inputs.\n'
           'This is preservation of observed bytes, not portable/runtime/scientific qualification or permission to rerun the spent scope.\n'
           'Administrative packaging occurs after the closed300-second scope. Native closure and all11 scientific fields remain pending.\n').encode()
    all_paths=set(selected_by_path)|{v['path'] for v in files.values()}|{v['path'] for v in extra}
    archive_entries={}
    with zipfile.ZipFile(BUNDLE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        z.writestr('ABOUT.txt',about)
        z.writestr('preservation-manifest.json',raw)
        for path in sorted(all_paths):
            data,item=read(path)
            expected_item=next((r for r in selected_rows+extra if r['path']==path),None)
            if expected_item is None:expected_item=files[str(Path(path).relative_to(ROOT))]
            if item!=expected_item:raise ValueError('source changed during archive construction')
            name='absolute_paths/'+path.lstrip('/')
            info=zipfile.ZipInfo(name);info.external_attr=(stat.S_IFREG|item['mode'])<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
            archive_entries[name]=dict(bytes=len(data),sha256=sha(data))
    with zipfile.ZipFile(BUNDLE) as z:
        for name,pin in archive_entries.items():
            data=z.read(name)
            if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('archive verification mismatch')
        if z.read('preservation-manifest.json')!=raw or z.read('ABOUT.txt')!=about:raise ValueError('archive manifest mismatch')
    bundle_raw,bundle_item=read(BUNDLE)
    summary=dict(schema='radio-closed-scope-preservation-summary-v1',identity=freeze['identity'],
        bundle=bundle_item,manifest_bytes=len(raw),manifest_sha256=sha(raw),
        actual_root_file_count=len(files),actual_root_directory_count=len(directories),
        actual_root_logical_bytes=sum(x['bytes'] for x in files.values())+sum(x['bytes'] for x in directories),
        actual_root_allocated_bytes=sum(x['allocated_bytes'] for x in files.values())+sum(x['allocated_bytes'] for x in directories),
        archive_regular_entries=len(archive_entries)+2,archive_all_regular_entry_hashes_verified=True,
        selected_input_files=len(selected_rows),administrative_elapsed_seconds=time.monotonic()-started,
        administrative_reads_separate_from_original_closed_scope=True)
    (HERE/'preservation-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
