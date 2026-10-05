"""Bounded read-only input preparation; no installed Python/native import."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,stat,time
BASE=Path('/workspace/scratch/da6462abff17');HERE=Path(__file__).resolve().parent
OLD=BASE/'runtime-offline-preparation';CROOT=BASE/'radio-offline-runtime-materialization-20261005c'
PREVIOUS=BASE/'runtime-metadata-preparation'
VENV=CROOT/'installer/venv';CAP=512*1024**2
charged=0
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def held_pin(path,expected=None):
    global charged
    path=Path(path);assert path.resolve()==path
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd);assert stat.S_ISREG(st.st_mode) and st.st_size<=128*1024**2
        charged+=st.st_size;assert charged<=CAP
        digest=hashlib.sha256();left=st.st_size
        while left:
            raw=os.read(fd,min(left,1024**2));assert raw;digest.update(raw);left-=len(raw)
        after=os.fstat(fd);named=path.stat(follow_symlinks=False)
        facts=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)
        assert facts(st)==facts(after)==facts(named)
        pin=dict(path=str(path),bytes=st.st_size,sha256=digest.hexdigest(),mode=stat.S_IMODE(st.st_mode),
                 identity=[st.st_dev,st.st_ino],links=st.st_nlink)
        if expected:assert all(pin[k]==expected[k] for k in ('bytes','sha256','mode'))
        return pin
    finally:os.close(fd)
def main():
    started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    def expired(a,b):raise TimeoutError('input preparation60s')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,60)
    f=json.loads((OLD/'freeze.json').read_bytes())
    custody=json.loads((BASE/'runtime-offline-preservation/preservation-manifest.json').read_bytes())
    gate=json.loads((CROOT/'result.json').read_bytes());verified=json.loads((CROOT/'installed-byte-evidence.json').read_bytes())
    assert gate['status']=='FAILED_CLOSED' and verified['status']=='INSTALLED_BYTES_VERIFIED_NO_PACKAGE_IMPORT'
    previous_runtime=json.loads((PREVIOUS/'runtime-inputs.json').read_bytes())
    sup=HERE/'supervisor';sup.mkdir(mode=0o700)
    for name in ('leaf_supervisor.py','leaf_guard.c','leaf_guard','exec_seal.c','exec_seal.so','phase2_bootstrap.py'):
        shutil.copy2(PREVIOUS/'supervisor'/name,sup/name)
    binaries={str(PREVIOUS/'supervisor/leaf_guard'),str(PREVIOUS/'supervisor/exec_seal.so')}
    runtime=[held_pin(x['path'],x) for x in previous_runtime['runtime_pins'] if x['path'] not in binaries]
    previous_by_path={p['path']:p for p in previous_runtime['runtime_pins']}
    runtime += [held_pin(sup/name,previous_by_path[str(PREVIOUS/'supervisor'/name)])
                for name in ('leaf_guard','exec_seal.so')]
    expected={str(Path(p['path']).relative_to(VENV)):p for p in custody['actual_root_files'].values()
              if Path(p['path']).is_relative_to(VENV)}
    expected_dirs={str(Path(p['path']).relative_to(Path('installer/venv'))):p for p in custody['actual_root_directories']
                   if Path(p['path']).is_relative_to(Path('installer/venv'))}
    files=[];directories=[]
    for directory,names,filenames in os.walk(VENV,followlinks=False):
        directory=Path(directory);rel=directory.relative_to(VENV).as_posix();st=directory.lstat()
        assert rel in expected_dirs and stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==expected_dirs[rel]['mode']
        directories.append(dict(relative_path=rel,identity=[st.st_dev,st.st_ino],mode=stat.S_IMODE(st.st_mode)))
        for name in names:assert not (directory/name).is_symlink()
        for name in sorted(filenames):
            path=directory/name;rel=path.relative_to(VENV).as_posix();assert rel in expected
            assert not rel.endswith(('.pth','.pyc','.pyo')) and Path(rel).name not in ('sitecustomize.py','usercustomize.py')
            pin=held_pin(path,expected[rel]);pin['relative_path']=rel;files.append(pin)
    assert {p['relative_path'] for p in files}==set(expected) and len(files)==1038
    assert {p['relative_path'] for p in directories}==set(expected_dirs) and len(directories)==110
    (HERE/'installed-tree-input.json').write_bytes(canonical(dict(schema='radio-installed-tree-input-v1',
        root=str(VENV),files=sorted(files,key=lambda p:p['relative_path']),directories=sorted(directories,key=lambda p:p['relative_path']),
        reused_C_identity=f['identity'],reused_C_closed=True,byte_verified_original_members=1025,regenerated_RECORD_files=3,
        expected_absent_site_hooks=['*.pth','*.pyc','*.pyo','sitecustomize.py','usercustomize.py'],
        input_integrity_not_continuous_native_custody=True)))
    (HERE/'runtime-inputs.json').write_bytes(canonical(dict(python_executable=f['python_executable'],
        python_sha256=f['python_sha256'],runtime_pins=runtime)))
    basis=dict(schema='radio-capture-E-installed-basis-v1',C_preparation_commit='941a5e434cc2449c2b41e7f9c28c27c4c133519e',
        C_activation_commit='21e03bcd63ff8e5a672e424923388a47c936a98c',C_result_commit='4dcfc344b9f083d40d38bdd202db0213a602593d',
        C_final_science_commit='63d03380c9901d7e9807490d1c21bca184b352a8',
        C_gate_result=held_pin(CROOT/'result.json'),C_installed_byte_evidence=held_pin(CROOT/'installed-byte-evidence.json'),
        C_preservation_manifest=held_pin(BASE/'runtime-offline-preservation/preservation-manifest.json'),
        C_bundle_bytes=189808619,C_bundle_sha256='434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a',
        prior_D_basis_pin=held_pin(PREVIOUS/'C-installed-basis.json'),
        previous_input_manifest_pin=held_pin(PREVIOUS/'installed-tree-input.json'),
        unchanged_supervisor_from_D=True,
        no_installation_or_old_scope_rerun=True,runtime_qualified=False,scientific_authority=False)
    (HERE/'C-installed-basis.json').write_bytes(canonical(basis))
    # The reviewed E collector owns its separate source-derived filter/RECORD
    # inputs. Never overwrite them with a historical collector input.
    summary=dict(schema='radio-capture-E-readonly-input-preparation-v1',elapsed_seconds=time.monotonic()-started,
        charged_explicit_read_bytes=charged,limits=dict(wall_seconds=60,read_bytes=CAP,process_AS_bytes=CAP),
        installed_files=len(files),installed_directories=len(directories),installed_regular_bytes=sum(x['bytes'] for x in files),
        runtime_files=len(runtime),runtime_regular_bytes=sum(x['bytes'] for x in runtime),
        native_scientific_imports=0,installed_python_launches=0,installations=0,old_scope_reruns=0,
        freeze_created=False,publication_created=False,activation_created=False,
        scientific_authority=False,runtime_qualified=False)
    (HERE/'input-preparation-receipt.json').write_bytes(canonical(summary))
    print(json.dumps(summary,sort_keys=True));signal.setitimer(signal.ITIMER_REAL,0)
if __name__=='__main__':main()
