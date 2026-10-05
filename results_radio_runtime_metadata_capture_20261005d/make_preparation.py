"""Create inert D freeze/publication; no actual/native dispatch."""
import base64,hashlib,json,os,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREFIX='results_radio_runtime_metadata_capture_20261005d'
IDENTITY='radio-runtime-metadata-capture-20261005d'
FREEZE_REPO='config/radio_runtime_metadata_capture_20261005d.freeze.json'
MARKER_REPO='config/radio_runtime_metadata_capture_20261005d.activate.json'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def write(path,obj):
    raw=canonical(obj)
    with Path(path).open('xb') as f:f.write(raw)
    return raw
def pin(path):
    path=Path(path);raw=path.read_bytes();st=path.lstat()
    assert path.resolve()==path and stat.S_ISREG(st.st_mode)
    return dict(path=str(path),bytes=len(raw),sha256=sha(raw),mode=stat.S_IMODE(st.st_mode))
def representation(path):
    raw=path.read_bytes();name=PREFIX+'/'+path.relative_to(HERE).as_posix()
    try:
        body=raw.decode('utf-8')
        if '\0' in body:raise UnicodeError()
        encoding='utf-8'
    except UnicodeError:
        body=base64.b64encode(raw).decode()+'\n';name+='.base64';encoding='base64'
    encoded=body.encode()
    return name,body,dict(local_path=str(path),bytes=len(encoded),sha256=sha(encoded),
        git_blob=hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest(),
        raw_bytes=len(raw),raw_sha256=sha(raw),encoding=encoding)
def main():
    root_info=json.loads((HERE/'preallocated-root.json').read_bytes());output=Path(root_info['path']);st=output.lstat()
    assert stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==0o700 and not list(output.iterdir())
    assert [st.st_dev,st.st_ino]==root_info['identity']
    runtime=json.loads((HERE/'runtime-inputs.json').read_bytes())
    excluded={'freeze.json','publication-payload.json','publication-metadata.json','preparation-summary.json'}
    paths=[p for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in excluded and '__pycache__' not in p.parts]
    binary={HERE/'supervisor/leaf_guard',HERE/'supervisor/exec_seal.so'}
    sources=[pin(p) for p in paths if p not in binary]
    bodies={};published={}
    for path in paths:
        name,body,metadata=representation(path);bodies[name]=body;published[name]=metadata
    # Import only the inert gate's stdlib constants; no activation/native calls.
    namespace={'__name__':'prospective_gate_constants','__file__':str(HERE/'runtime_gate.py')}
    exec(compile((HERE/'runtime_gate.py').read_bytes(),str(HERE/'runtime_gate.py'),'exec'),namespace)
    freeze=dict(schema='radio-runtime-metadata-capture-freeze-v1',identity=IDENTITY,single_use=True,
        automatic_successor=False,engineering_only=True,network=False,install=False,hdf5_dataset_access=False,
        scientific_authority=False,limits=namespace['LIMITS'],output_root=str(output),output_root_identity=root_info['identity'],
        preparation_root=str(HERE),python_executable=runtime['python_executable'],python_sha256=runtime['python_sha256'],
        source_pins=sources,runtime_pins=runtime['runtime_pins'],published_sources=published,
        input_manifest_pin=pin(HERE/'installed-tree-input.json'),
        gate_source_path=str(HERE/'runtime_gate.py'),launcher_source_path=str(HERE/'launch_scope.py'),
        supervisor_source_path=str(HERE/'supervisor/leaf_supervisor.py'),
        collector_source_path=str(HERE/'collector/collect_runtime_identity.py'),
        filter_input_path=str(HERE/'collector/filter-input.json'),
        record_relocations_path=str(HERE/'collector/record-relocations.json'),
        freeze_repository_path=FREEZE_REPO,marker_repository_path=MARKER_REPO,
        runtime_host_observation=dict(platform=os.uname().sysname,kernel_release=os.uname().release,
            kernel_version=os.uname().version,machine=os.uname().machine),
        input_prepost_is_selected_integrity_not_continuous_namespace_custody=True)
    for name,path in [('guard',HERE/'supervisor/leaf_guard'),('exec_seal',HERE/'supervisor/exec_seal.so'),
                       ('phase2',HERE/'supervisor/phase2_bootstrap.py')]:
        freeze[name+'_path']=str(path);freeze[name+'_sha256']=pin(path)['sha256']
    raw=write(HERE/'freeze.json',freeze);assert len(raw)<1024**2
    bodies[FREEZE_REPO]=raw.decode();write(HERE/'publication-payload.json',bodies)
    write(HERE/'publication-metadata.json',published)
    summary=dict(identity=IDENTITY,files=len(bodies),publication_utf8_bytes=sum(len(x.encode()) for x in bodies.values()),
        freeze_bytes=len(raw),freeze_sha256=sha(raw),source_pins=len(sources),runtime_pins=len(runtime['runtime_pins']),
        reused_installed_files=1038,reused_installed_directories=110,output_root=str(output),output_root_identity=root_info['identity'])
    write(HERE/'preparation-summary.json',summary);print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
