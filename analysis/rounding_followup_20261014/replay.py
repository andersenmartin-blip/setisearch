"""Reproduce the delivered exact path scores and independent QA in a fresh stage."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
PINS={'SCOPE.json':'e159332d7a802a0924e2e4eb54c2d0a5467008db716424348de776e3e90a7cb7',
      'producer.py':'3921a24700f6c5885498020c7955c6f9cef62fedc4cbba95fd01dbd47b84d948',
      'geometry.py':'c00370868c63a951fe6bc6908a4aa0bf93a5ff9aed41523f316cc8a83b79daaf',
      'qa.py':'dd36fd4667f62699c0da16a0ed89817837e180a7e25839879f5ed637ed02066c'}
GEOMETRY='77651a3d9122398a8ebe9467ee8be93be7422dfd9a5958655e88ea480d94a7f1'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: python3 rounding_followup/replay.py /absolute/new-output-directory')
    dest=Path(sys.argv[1]).resolve()
    if dest.exists():raise SystemExit('Output must be a new directory')
    if not (BASE/'seti_work').is_dir() or not (BASE/'drift_followup').is_dir():raise SystemExit('Extract the complete result archive first')
    for name,value in PINS.items():
        if sha(STAGE/name)!=value:raise SystemExit('Frozen file differs: '+name)
    dest.mkdir(parents=True)
    for name in PINS:shutil.copyfile(STAGE/name,dest/name)
    go=dest/'GO.json'
    save(go,{'status':'GO_EXACT_CONTINUOUS_ROUNDING_OBSERVED','scope_sha256':PINS['SCOPE.json'],'code_sha256':PINS['producer.py'],'geometry_sha256':GEOMETRY,'reproduction_only':True})
    subprocess.run([sys.executable,str(dest/'producer.py'),'--root',str(BASE),'--portable-inputs','--scope',str(dest/'SCOPE.json'),'--output-dir',str(dest/'results'),'--scope-sha256',PINS['SCOPE.json'],'--code-sha256',PINS['producer.py'],'--geometry-sha256',GEOMETRY,'--root-go-sha256',sha(go)],check=True)
    receipt=sha(dest/'results/EXECUTION_RECEIPT.json');qgo=dest/'QA_GO.json'
    save(qgo,{'status':'GO_INDEPENDENT_EXACT_ROUNDING_QA','scope_sha256':PINS['SCOPE.json'],'qa_code_sha256':PINS['qa.py'],'producer_receipt_sha256':receipt,'reproduction_only':True})
    subprocess.run([sys.executable,str(dest/'qa.py'),'--root',str(dest),'--inputs-root',str(BASE),'--portable-inputs','--scope-sha256',PINS['SCOPE.json'],'--qa-sha256',PINS['qa.py'],'--receipt-sha256',receipt,'--root-go-sha256',sha(qgo)],check=True)
    print('Reproduction complete. No new observation.')
if __name__=='__main__':main()
