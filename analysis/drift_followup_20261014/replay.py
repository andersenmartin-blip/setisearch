"""Replay the delivered frozen analysis and independent QA in a fresh directory."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
PINS = {'SCOPE.json':'b0a76f82ba0cb901112f94ae6989e64f20b7aa6e395f37d51840ea3d37484075',
        'producer.py':'5ac4ac2c2ff939c0e54fef740f8bc219a3f7833d4a66c9fa73f7bcc3cb161e34',
        'qa.py':'54c9e50ba30463b70c0c420f1d71820ee3767a59bb090d323f298457f51207c6'}
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()
def save(path,obj):
    path.write_text(json.dumps(obj,indent=2)+'\n')
def main():
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python3 replay.py /absolute/new-replay-directory')
    dest=Path(sys.argv[1]).resolve()
    if dest.exists():
        raise SystemExit('Replay output must be a new directory')
    inputs=BASE/'inputs'
    if not inputs.is_dir():
        raise SystemExit('Run from the extracted result archive containing inputs/')
    for name,h in PINS.items():
        if sha(BASE/name)!=h:
            raise SystemExit('Frozen file differs: '+name)
    dest.mkdir(parents=True)
    for name in PINS:
        shutil.copyfile(BASE/name,dest/name)
    save(dest/'GO.json',{'status':'GO_LOCAL_DRIFT_DIAGNOSTIC','scope_sha256':PINS['SCOPE.json'],'code_sha256':PINS['producer.py'],'reproduction_only':True})
    subprocess.run([sys.executable,str(dest/'producer.py'),'--root',str(inputs),'--portable-inputs','--scope',str(dest/'SCOPE.json'),'--output-dir',str(dest/'results'),'--scope-sha256',PINS['SCOPE.json'],'--code-sha256',PINS['producer.py']],check=True)
    receipt=sha(dest/'results/EXECUTION_RECEIPT.json')
    go=dest/'QA_GO.json'
    save(go,{'status':'GO_INDEPENDENT_LOCAL_DRIFT_QA','scope_sha256':PINS['SCOPE.json'],'qa_code_sha256':PINS['qa.py'],'producer_receipt_sha256':receipt,'reproduction_only':True})
    subprocess.run([sys.executable,str(dest/'qa.py'),'--root',str(dest),'--inputs-root',str(inputs),'--portable-inputs','--scope-sha256',PINS['SCOPE.json'],'--qa-sha256',PINS['qa.py'],'--receipt-sha256',receipt,'--root-go-sha256',sha(go)],check=True)
    print('Completed reproduction. This is not a new observation.')
if __name__=='__main__':
    main()
