"""Root-authorized, once-only metadata admission after the active primary queue."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
PINS={
    'prepare_qa_go.py':'ea4068bfd2644156ae935ce55679c8714305d13baba05269e8abc7cc20078bba',
    'qa_v2.py':'ccc7f96d079653d04df5a679af2192173a8e1281c80a3d21b995d5a3dd847cd5',
}
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_code():
    for name,sha in PINS.items():
        if digest(BASE/name)!=sha: raise ValueError('Frozen code changed: '+name)
def main():
    verify_code()
    assert not (BASE/'QA_ROOT_GO.json').exists() and not (BASE/'qa_results').exists()
    started=time.monotonic()
    while not (BASE/'QUEUE_RECEIPT.json').exists():
        if time.monotonic()-started>7200: raise TimeoutError('Primary queue admission wait cap')
        time.sleep(5)
    queue=json.loads((BASE/'QUEUE_RECEIPT.json').read_bytes())
    assert queue['status']=='PASS_ALL21_SHARDS2010_NEW_MAPS'
    verify_code()
    builder=subprocess.run([sys.executable,str(BASE/'prepare_qa_go.py'),'--root',str(ROOT),'--prepare'],cwd=ROOT,capture_output=True,timeout=120)
    (BASE/'QA_PREPARE_STDOUT.json').write_bytes(builder.stdout)
    (BASE/'QA_PREPARE_STDERR.txt').write_bytes(builder.stderr)
    if builder.returncode: raise RuntimeError('QA admission builder failed; preserved, no retry')
    go_path=BASE/'QA_ROOT_GO.json';go=json.loads(go_path.read_bytes())
    assert go['status']=='GO_INDEPENDENT_FULL_ON_DUAL_BURST4_QA'
    args=['--root',str(ROOT),'--scope-sha256',go['scope_sha256'],'--qa-sha256',go['qa_sha256'],'--root-go-sha256',digest(go_path)]
    for job,sha in sorted(go['primary_receipt_sha256s'].items()):args+=['--primary-receipt',job+'='+sha]
    with (BASE/'QA_ARGS.json').open('x') as f:json.dump(args,f,indent=2);f.write('\n')
    verify_code()
    print('ENTERED_INDEPENDENT_FULL_SOURCE_DUAL_QA',flush=True)
    env=dict(os.environ);env.update({k:'1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    with (BASE/'main_qa_run.log').open('x') as logfile:
        run=subprocess.run([sys.executable,str(BASE/'qa_v2.py'),*args],cwd=ROOT,env=env,stdout=logfile,stderr=subprocess.STDOUT,timeout=930)
    p=BASE/'qa_results'/'QA_RECEIPT.json'
    status=json.loads(p.read_bytes()).get('status') if p.exists() else 'NO_TERMINAL_RECEIPT'
    receipt={'exit_code':run.returncode,'status':status,'automatic_retries':0,'QA_GO_sha256':digest(go_path),'QA_receipt_sha256':digest(p) if p.exists() else None}
    with (BASE/'QA_QUEUE_EXECUTION_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt),flush=True)
    if run.returncode or status!='PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY':raise RuntimeError('Main QA failed; preserved, no retry')

if __name__=='__main__':main()
