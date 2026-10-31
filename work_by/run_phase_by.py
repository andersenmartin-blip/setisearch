"""One bounded BY analysis phase, exclusive tmpfs output and verified closed export."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, resource, signal, subprocess, sys, time, traceback
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'work_by'
ISOLATION=Path('/dev/shm/seti_by_20261031')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def checked(pins):
    actual={p:sha(p) for p in pins}
    if actual!=pins:raise ValueError('Source/input binding changed')
    return actual
def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
def main(phase):
    begin=time.monotonic(); planpath=HERE/'PLAN_BY.json';freeze=HERE/'PUBLIC_FREEZE_BY.json'
    plan=read(planpath);frozen=read(freeze)
    assert frozen['exact_readback_verified'] and frozen['plan_sha256']==sha(planpath)
    pins=dict(plan['source_sha256']);pins.update({x['path']:x['sha256'] for x in plan['inputs']});pins.update({str(planpath):sha(planpath),str(freeze):sha(freeze)})
    base=ISOLATION/phase;base.mkdir(parents=True,exist_ok=False);out=base/'outputs'
    destination=HERE/'execution'/phase;destination.mkdir(parents=True,exist_ok=False)
    result=dict(schema='SETI_BY_PHASE_CAPTURE_V1',phase=phase,status='FAIL',plan_sha256=sha(planpath),
        actual_exit_code=None,child_wait_completed=False,natural_stdout_eof=False,killed=False,
        errors=[],started_utc=datetime.now(timezone.utc).isoformat(),no_retry=True)
    child=None
    try:
        if phase.startswith('rfi'):
            scope=read(HERE/'rfi_scope.json')
            for item in scope['inputs']:
                path=HERE/item['local_relative_path'];raw=path.read_bytes()
                assert len(raw)==item['bytes']
                assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob_sha1']
                pins[str(path)]=hashlib.sha256(raw).hexdigest()
        if phase in ('audit','rfi_audit'):
            parent_phase='injection' if phase=='audit' else 'rfi'
            parent_capture=HERE/'execution'/parent_phase/'RESULT.json'
            pins[str(parent_capture)]=sha(parent_capture)
            production=read(parent_capture)
            assert production['status']=='PASS' and production['actual_exit_code']==0 and production['natural_stdout_eof']
            for name,digest in production['output_sha256'].items():
                p=ISOLATION/parent_phase/'outputs'/name;assert sha(p)==digest;pins[str(p)]=digest
        result['pins_before']=checked(pins)
        command=[sys.executable,str(HERE/('inject_recover.py' if phase=='injection' else 'review_injection.py')),
                 '--plan',str(planpath),'--freeze',str(freeze),'--out',str(out)]
        if phase=='audit':command+=['--production',str(ISOLATION/'injection/outputs')]
        if phase.startswith('rfi'):
            command=[sys.executable,str(HERE/('analyze_rfi.py' if phase=='rfi' else 'review_rfi.py')),
                     '--scope',str(HERE/'rfi_scope.json'),'--out',str(out)]
            if phase=='rfi_audit':command+=['--production',str(ISOLATION/'rfi/outputs')]
        result['command']=command
        env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,
                               start_new_session=True,preexec_fn=limits)
        try:log,_=child.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            result['killed']=True;os.killpg(child.pid,signal.SIGKILL);log,_=child.communicate()
        result.update(actual_exit_code=child.returncode,child_wait_completed=True,natural_stdout_eof=not result['killed'])
        (base/'STDOUT.log').write_bytes(log);result['stdout_sha256']=sha(base/'STDOUT.log')
        assert child.returncode==0 and not result['killed'] and len(log)<=1024**2
        filename,expected={
            'injection':('SUMMARY_BY.json','PASS_CONDITIONAL_INJECTION_RECOVERY'),
            'audit':('REVIEW_BY.json','PASS_INDEPENDENT_INJECTION_REVIEW'),
            'rfi':('SUMMARY_RFI_BY.json','PASS_DESCRIPTIVE_DERIVED_COUNTS'),
            'rfi_audit':('REVIEW_RFI_BY.json','PASS_INDEPENDENT_RFI_REVIEW')}[phase]
        value=read(out/filename)
        assert value['status']==expected
        result['scientific_status']=value['status'];result['output_sha256']={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        result['pins_after']=checked(pins);assert result['pins_after']==result['pins_before']
        result['status']='PASS'
    except BaseException as e:
        result['errors'].append(dict(error=type(e).__name__+': '+str(e),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGKILL);child.wait();result['killed']=True
    result['wall_seconds']=time.monotonic()-begin
    save(base/'CAPTURE.json',result)
    spec=importlib.util.spec_from_file_location('by_exact_archive',ROOT/'work_bt/isolated_worker.py')
    archive=importlib.util.module_from_spec(spec);sys.modules[spec.name]=archive;spec.loader.exec_module(archive)
    archive.MAX_MEMBERS=64
    receipt=archive.create_archive(base,ISOLATION/(phase+'.zip'))
    exported=archive.export_archive(ISOLATION/(phase+'.zip'),destination/'EVIDENCE.zip',receipt)
    result['archive']=exported
    result['pins_after_export']=checked(pins)
    save(destination/'RESULT.json',result)
    print(json.dumps(dict(phase=phase,status=result['status'],actual_exit_code=result['actual_exit_code'],
        natural_stdout_eof=result['natural_stdout_eof'],result_sha256=sha(destination/'RESULT.json'),
        archive_sha256=exported['sha256'],wall_seconds=result['wall_seconds'])),flush=True)
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['injection','audit','rfi','rfi_audit'],required=True)
    raise SystemExit(main(p.parse_args().phase))
