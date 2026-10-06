"""Root source-only builder for the fresh G input freeze. No child dispatch."""
import hashlib
import json
import os
from pathlib import Path
import stat
import types

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
SCOPE_ID = 'codec16-control-20261006g'
VENV = Path('/workspace/scratch/da6462abff17/radio-offline-runtime-materialization-20261005c/installer/venv')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def document(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out: out.write(encoded(value))


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as stream:
        before = os.fstat(stream.fileno()); assert stat.S_ISREG(before.st_mode)
        digest=hashlib.sha256(); total=0
        while block:=stream.read(1024**2): total+=len(block);digest.update(block)
        after=os.fstat(stream.fileno())
    identity=lambda st:(st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    assert identity(before)==identity(after)==identity(path.stat()) and total==before.st_size
    return dict(path=str(path),sha256=digest.hexdigest(),bytes=before.st_size,mode=before.st_mode,
                device=before.st_dev,inode=before.st_ino,mtime_ns=before.st_mtime_ns,ctime_ns=before.st_ctime_ns)


def source_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not p.is_relative_to(ROOT/'native/files')
                  and not p.is_relative_to(ROOT/'admission')
                  and not p.is_relative_to(ROOT/'closed')
                  and p.suffix != '.pyc')


def main():
    admission=ROOT/'admission';admission.mkdir(exist_ok=False)
    artifact=WORK/'radio-codec16-control-20261006g';artifact.mkdir(mode=0o700,exist_ok=False)
    gate=types.ModuleType('fresh_source_only_G_gate');gate.__file__=str(ROOT/'outer/gate.py')
    exec(compile((ROOT/'outer/gate.py').read_bytes(),gate.__file__,'exec'),gate.__dict__)
    native=json.loads((ROOT/'native/native-inventory.json').read_bytes())
    expected_e=next((WORK/'previous/E').rglob('runtime-inputs.json'))
    expected_installed=next((WORK/'previous/E').rglob('installed-tree-input.json'))
    runtime=json.loads(expected_e.read_bytes())
    installed=json.loads(expected_installed.read_bytes())
    scope=dict(schema='radio-codec16-scope-G-v1',scope_id=SCOPE_ID,
        project_identity='radio-codec16-control-20261006g',one_guarded_leaf=True,
        kind='controlled-source-shaped-codec-normalization',
        calibration_scan='epoch1_on',row_indices=list(range(16)),chunk_index=159,
        runtime_prefix=str(VENV),original_E_runtime_manifest=pin(expected_e),
        original_E_installed_manifest=pin(expected_installed),
        original_C_bundle=dict(file_name='SETI_offline_installation_2026-10-05_closed.zip',
            library_file_id='libfile_9763ef34782881919738134288f44fd8',
            bytes=189808619,sha256='434e5a5d64e9361b591d527608290a0f7443e6b7b0b7543c9d6e9dbad1111b7a'),
        protocol_sha256=pin(ROOT/'PROTOCOL.md')['sha256'],
        native_inventory_sha256=pin(ROOT/'native/native-inventory.json')['sha256'],
        applicable_native_graph_static_only=True,budgets=gate.BUDGETS,
        archive_spectral_access=False,scientific_authority=False,
        all_closed_scopes_unchanged=True,consolidation_date='2026-10-09')
    document(admission/'scope.json',scope)
    roles=dict(scope=str(admission/'scope.json'),dispatch=str(admission/'dispatch.json'),
        leaf_manifest=str(ROOT/'leaf/LEAF_FILES.json'),leaf_script=str(ROOT/'leaf/run_codec16.py'),
        plan=str(ROOT/'leaf/retained-draft/PLAN.json'),
        input_manifest=str(ROOT/'leaf/retained-draft/INPUT_MANIFEST.json'),
        selection=str(ROOT/'leaf/retained-draft/SELECTED_CODE.json'),python=str(VENV/'bin/python'),
        guard=str(ROOT/'outer/supervisor/leaf_guard'),exec_seal=str(ROOT/'outer/supervisor/exec_seal.so'),
        phase2=str(ROOT/'outer/supervisor/phase2_bootstrap.py'),
        proc_custody=str(ROOT/'outer/supervisor/proc_custody.py'),
        leaf_supervisor=str(ROOT/'outer/supervisor/leaf_supervisor.py'))
    dispatch=dict(schema='codec16-fresh-engineering-dispatch-v1',scope_id=SCOPE_ID,
        plan_sha256=pin(roles['plan'])['sha256'],input_manifest_sha256=pin(roles['input_manifest'])['sha256'],
        selection_sha256=pin(roles['selection'])['sha256'],runtime_prefix=str(VENV),
        outer_supervisor_scope_sha256=pin(roles['scope'])['sha256'],engineering_execution_authorized=True)
    document(admission/'dispatch.json',dispatch)
    sources=source_files()
    paths=set(sources)|{Path(roles['scope']),Path(roles['dispatch']),expected_e,expected_installed}
    original_expectations=runtime['runtime_pins']+installed['files']
    paths.update(Path(p['path']) for p in original_expectations)
    paths.update(Path(p['path']) for p in native['nodes'])
    pins=[pin(p) for p in sorted(paths)]
    actual={p['path']:p for p in pins}
    for old in original_expectations:
        now=actual[old['path']]
        assert now['sha256']==old['sha256'] and now['bytes']==old['bytes'] and stat.S_IMODE(now['mode'])==old['mode']
        assert [now['device'],now['inode']]==old['identity']
    for node in native['nodes']:
        assert actual[node['path']]['sha256']==node['sha256']
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',
        PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',OMP_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',
        HDF5_USE_FILE_LOCKING='FALSE')
    config=dict(schema=gate.SCHEMA,scope_id=SCOPE_ID,roles=roles,pinned_files=pins,
        inventory_roots=sorted([str(ROOT/'leaf'),str(ROOT/'outer'),str(VENV)]),
        runtime_prefix=str(VENV),cwd=str(ROOT),environment=environment,budgets=gate.BUDGETS,
        artifacts=dict(root=str(artifact),leaf_output=str(artifact/'controlled'),
            output_prefix=str(artifact/'leaf'),outer_report=str(artifact/'outer-result.json'),
            spent_marker=str(admission/'spent.json')))
    document(admission/'config.json',config)
    cp=pin(admission/'config.json')
    proof=dict(schema='radio-codec16-preread-G-v1',config_sha256=cp['sha256'],scope_id=SCOPE_ID,
        pinned_files_sha256=hashlib.sha256(encoded(pins)).hexdigest(),all_reads_complete=True,
        readback=pins,read_bytes=sum(p['bytes'] for p in pins))
    document(admission/'preread-proof.json',proof)
    document(admission/'build-summary.json',dict(scope_id=SCOPE_ID,files=len(pins),
        full_source_runtime_read_bytes=proof['read_bytes'],config_pin=cp,
        preread_pin=pin(admission/'preread-proof.json'),no_native_dispatch=True))
    print(encoded(json.loads((admission/'build-summary.json').read_bytes())).decode(),end='')


if __name__=='__main__': main()
