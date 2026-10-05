"""Create prospective plans from fixed inputs; no installer/native dispatch."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT.parent/'radio-offline-runtime-materialization-20261005c'
PREFIX='results_radio_offline_runtime_materialization_20261005c'
IDENTITY='radio-offline-runtime-materialization-20261005c'
FREEZE_REPO='config/radio_offline_runtime_materialization_20261005c.freeze.json'
MARKER_REPO='config/radio_offline_runtime_materialization_20261005c.activate.json'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def raw_pin(path):
    path=Path(path).resolve(strict=True)
    data=path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=sha(data),mode=stat.S_IMODE(path.stat().st_mode))
def write(path,obj):
    raw=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
    with Path(path).open('xb') as f:f.write(raw)
    return raw
def representation(path):
    raw=path.read_bytes()
    name=PREFIX+'/'+path.relative_to(ROOT).as_posix()
    try:
        body=raw.decode('utf-8')
        if '\0' in body:raise UnicodeError('binary NUL')
        encoding='utf-8'
    except UnicodeError:
        body=base64.b64encode(raw).decode()+'\n'
        name+='.base64'
        encoding='base64'
    encoded=body.encode()
    git_blob=hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest()
    meta=dict(local_path=str(path),bytes=len(encoded),sha256=sha(encoded),git_blob=git_blob,
              raw_bytes=len(raw),raw_sha256=sha(raw),encoding=encoding)
    return name,body,meta

def main():
    if OUTPUT.exists():
        existing=OUTPUT.lstat()
        if OUTPUT.is_symlink() or not stat.S_ISDIR(existing.st_mode) or stat.S_IMODE(existing.st_mode)!=0o700 or any(OUTPUT.iterdir()):
            raise ValueError('existing nonempty or unsafe scope root refused')
        if [existing.st_dev,existing.st_ino]!=[27,544584]:
            raise ValueError('existing preallocated root identity changed')
    else:
        OUTPUT.mkdir(mode=0o700)
    st=OUTPUT.stat()
    current=json.loads((ROOT/'current-inputs.json').read_text())
    original_source=Path(current['original_plan_pin']['path'])
    shutil.copy2(original_source,ROOT/'original-plan.json')
    original=json.loads((ROOT/'original-plan.json').read_text())
    binary_paths={ROOT/'supervisor/leaf_guard',ROOT/'supervisor/exec_seal.so'}
    excluded={'installer-plan.json','freeze.json','publication-payload.json','preparation-summary.json'}
    prepared_files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name not in excluded and
                    '__pycache__' not in p.parts]
    sources=[raw_pin(p) for p in prepared_files if p not in binary_paths]
    runtime=list(current['runtime_pins'])+[raw_pin(p) for p in binary_paths]
    sources.sort(key=lambda p:p['path']);runtime.sort(key=lambda p:p['path'])
    wheel_by_filename={Path(p['path']).name:p for p in current['wheel_pins']}
    wheels=[]
    for w in original['materialization']['official_wheels']:
        spec={key:w[key] for key in ('name','version','filename','bytes','sha256','url','tags')}
        wheel=wheel_by_filename[w['filename']]
        if wheel['bytes']!=w['bytes'] or wheel['sha256']!=w['sha256']:raise ValueError('wheel pin mismatch')
        wheels.append(dict(path=wheel['path'],spec=spec))
    installer=dict(schema='radio-offline-runtime-installer-plan-v1',identity=IDENTITY,
        purpose='offline-package-install-only',single_use=True,network=False,compile=False,native_imports=False,
        original_plan_pin=raw_pin(ROOT/'original-plan.json'),source_pins=sources,runtime_pins=runtime,
        python_executable=current['python_executable'],python_version=current['python_version'],
        stdlib_root=current['stdlib_root'],guard_path=str(ROOT/'supervisor/leaf_guard'),
        seed_pins=current['seed_pins'],wheels=wheels,
        wheel_lock_utf8=original['materialization']['offline_hash_lock_utf8'],
        limits=dict(wall_seconds=300,cpu_seconds=240,address_space_bytes=512*1024**2,
          artifact_bytes=1536*1024**2,parent_read_bytes=2304*1024**2,child_read_reserve_bytes=512*1024**2,
          joined_read_bytes=2816*1024**2,stream_bytes=4*1024**2,file_bytes=128*1024**2,
          file_count=20000,directory_count=4096,terminal_reserve_bytes=8*1024**2),
        output_root=str(OUTPUT/'installer'))
    write(ROOT/'installer-plan.json',installer)
    prepared_files.append(ROOT/'installer-plan.json')
    bodies={};published={}
    for path in prepared_files:
        repo_path,body,metadata=representation(path)
        bodies[repo_path]=body;published[repo_path]=metadata
    py_pin=next(p for p in runtime if p['path']==current['python_executable'])
    limits=dict(wall_seconds=300,operation_seconds=270,child_wall_seconds=120,child_cpu_seconds=100,
        parent_address_space_bytes=512*1024**2,child_address_space_bytes=512*1024**2,
        artifact_bytes=1536*1024**2,parent_read_bytes=3*1024**3,child_read_reserve_bytes=1024**3,
        joined_read_bytes=4*1024**3,stream_bytes=4*1024**2,root_explicit_read_bytes=624*1024**2,
        installer_explicit_read_bytes=2304*1024**2,supervisor_explicit_pin_read_bytes=64*1024**2,
        supervisor_explicit_proc_read_bytes=64*1024**2,misc_stream_read_bytes=16*1024**2,
        child_sample_interval_seconds=0.02,child_cleanup_seconds=10,
        file_bytes=128*1024**2,file_count=20000,directory_count=4096,child_dispatches=2,
        terminal_reserve_bytes=8*1024**2)
    freeze=dict(schema='radio-offline-runtime-materialization-freeze-v1',identity=IDENTITY,
        single_use=True,automatic_successor=False,engineering_only=True,network=False,
        hdf5_dataset_access=False,scientific_authority=False,limits=limits,
        output_root=str(OUTPUT),output_root_identity=[st.st_dev,st.st_ino],preparation_root=str(ROOT),
        python_executable=current['python_executable'],python_sha256=py_pin['sha256'],
        source_pins=sources,runtime_pins=runtime,published_sources=published,
        installer_plan_pin=raw_pin(ROOT/'installer-plan.json'),
        installer_plan_sha256=raw_pin(ROOT/'installer-plan.json')['sha256'],
        gate_source_path=str(ROOT/'runtime_gate.py'),launcher_source_path=str(ROOT/'launch_scope.py'),
        installer_source_path=str(ROOT/'installer/offline_installer.py'),
        supervisor_source_path=str(ROOT/'supervisor/leaf_supervisor.py'),
        collector_source_path=str(ROOT/'collector/collect_runtime_identity.py'),
        filter_input_path=str(ROOT/'collector/filter-input.json'),
        marker_repository_path=MARKER_REPO,freeze_repository_path=FREEZE_REPO,
        runtime_host_observation=dict(platform=os.uname().sysname,kernel_release=os.uname().release,
            kernel_version=os.uname().version,machine=os.uname().machine),
        guards_are_engineering_inputs_not_scientific_attestation=True)
    for name,path in [('guard',ROOT/'supervisor/leaf_guard'),('exec_seal',ROOT/'supervisor/exec_seal.so'),
                       ('phase2',ROOT/'supervisor/phase2_bootstrap.py')]:
        freeze[name+'_path']=str(path);freeze[name+'_sha256']=raw_pin(path)['sha256']
    freeze_raw=write(ROOT/'freeze.json',freeze)
    bodies[FREEZE_REPO]=freeze_raw.decode()
    write(ROOT/'publication-payload.json',bodies)
    summary=dict(identity=IDENTITY,files=len(bodies),publication_utf8_bytes=sum(len(b.encode()) for b in bodies.values()),
        freeze_bytes=len(freeze_raw),freeze_sha256=sha(freeze_raw),installer_plan_sha256=freeze['installer_plan_sha256'],
        source_pins=len(sources),runtime_pins=len(runtime),output_root=str(OUTPUT),
        output_root_identity=freeze['output_root_identity'])
    write(ROOT/'preparation-summary.json',summary)
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':main()
