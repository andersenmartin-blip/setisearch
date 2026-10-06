"""Read-only base-runtime pins and copied unchanged guard; no native imports."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,stat,time
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'runtime-metadata-preparation-E'
CAP=160*1024**2
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
    started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    def expired(a,b):raise TimeoutError('input preparation30s')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,30)
    previous=json.loads((OLD/'runtime-inputs.json').read_bytes())
    sup=HERE/'supervisor';sup.mkdir(mode=0o700,exist_ok=True)
    for name in ('leaf_guard.c','leaf_guard','exec_seal.c','exec_seal.so','phase2_bootstrap.py'):
        assert not (sup/name).exists();shutil.copy2(OLD/'supervisor'/name,sup/name)
    binary_paths={str(OLD/'supervisor'/name) for name in ('leaf_guard','exec_seal.so')}
    runtime=[held_pin(p['path'],p) for p in previous['runtime_pins'] if p['path'] not in binary_paths]
    old_by_path={p['path']:p for p in previous['runtime_pins']}
    runtime+=[held_pin(sup/name,old_by_path[str(OLD/'supervisor'/name)]) for name in ('leaf_guard','exec_seal.so')]
    assert len(runtime)==1460 and sum(p['bytes'] for p in runtime)==109728045
    pattern=b'SETI-F-20261006 deterministic controlled IO; no spectral values.\n'
    payload=(pattern*((131072+len(pattern)-1)//len(pattern)))[:131072]
    with (HERE/'control-payload.txt').open('xb') as f:f.write(payload)
    (HERE/'runtime-inputs.json').write_bytes(canonical(dict(python_executable=previous['python_executable'],
        python_sha256=previous['python_sha256'],runtime_pins=runtime)))
    summary=dict(schema='radio-proc-io-control-input-preparation-v1',elapsed_seconds=time.monotonic()-started,
        charged_explicit_read_bytes=charged,limits=dict(wall_seconds=30,read_bytes=CAP,address_space_bytes=256*1024**2),
        runtime_files=len(runtime),runtime_regular_bytes=sum(p['bytes'] for p in runtime),
        payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest(),
        guard_and_seal_reused_unchanged=True,guard_compilations=0,installations=0,
        native_scientific_imports=0,installed_python_launches=0,old_scope_reruns=0,
        source_E_result_commit='b9d66f576e6eab2e291ddffa436cd50fddc20fbd',
        runtime_qualified=False,scientific_authority=False)
    (HERE/'input-preparation-receipt.json').write_bytes(canonical(summary))
    signal.setitimer(signal.ITIMER_REAL,0);print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
