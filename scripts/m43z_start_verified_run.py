"""Operational launcher: wait for six verified restoration receipts, then run freeze."""
import argparse,subprocess,sys,time,json
from pathlib import Path
from m43e_economical_bank import read_sealed
ROOT=Path(__file__).resolve().parents[1]

def run(runtime,freeze):
    expected=json.loads((ROOT/'config/m43o_real_stacks.json').read_text())['sources']
    deadline=time.monotonic()+1800
    print('Waiting for six verified historical source restorations',flush=True)
    while True:
        ready=[]
        for s in expected:
            p=ROOT/'results_m43z_joint_controls/restoration'/f'restore.{s["scan"]}.json'
            if not p.exists():continue
            r=read_sealed(p)
            if not r.get('complete'):continue
            assert r['source_receipt_sha256']==s['receipt_sha256'] and len(r['arrays'])==16
            assert all(a['original_digest_exact'] for a in r['arrays'])
            ready.append(s['scan'])
        if len(ready)==6:break
        if time.monotonic()>deadline:raise TimeoutError('input restoration not complete')
        time.sleep(1)
    print('All six source receipts and 96 anchor arrays verified; starting public freeze '+freeze,flush=True)
    code=subprocess.call([sys.executable,'-u',str(ROOT/'scripts/m43z_joint_controls.py'),
        '--freeze-commit',freeze,'--anchor-root',str(runtime/'anchors'),'--source-root',str(runtime/'sources'),
        '--checkpoint-root',str(runtime/'trials')],cwd=ROOT)
    raise SystemExit(code)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--freeze-commit',required=True)
    a=p.parse_args();run(a.runtime_root,a.freeze_commit)
