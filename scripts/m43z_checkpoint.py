"""Package a complete leading block of sealed Z trials without interrupting work."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
from m43z_joint_controls import ROOT,OUT,CONFIG,sha
from m43e_economical_bank import read_sealed,write_sealed

def run(work,count,freeze):
    cfg=json.loads(CONFIG.read_text());directory=OUT/'checkpoints';directory.mkdir(exist_ok=True)
    name=f'inputs{count:03d}';target=directory/(name+'.jsonl.gz')
    assert not target.exists(),'preserve published checkpoint'
    records=[];endpoints=[]
    for case in cfg['cases'][:count]:
        path=work/f'case{case["case_index"]:03d}.json';r=read_sealed(path)
        assert r['freeze_commit']==freeze and r['config_sha256']==sha(CONFIG) and r['case']==case
        records.append(path.read_bytes());endpoints.extend(r['endpoints'])
    assert len(records)==count and len(endpoints)==4*count
    raw=b''.join(b+b'\n' for b in records);packed=gzip.compress(raw,compresslevel=9,mtime=0);target.write_bytes(packed)
    shutil.copyfile(OUT/'live_run.log',directory/(name+'.log'))
    write_sealed(directory/(name+'.json'),dict(complete=False,freeze_commit=freeze,declared_inputs=352,completed_inputs=count,
        completed_endpoints=4*count,config_sha256=sha(CONFIG),ledger_sha256=hashlib.sha256(packed).hexdigest(),
        ledger_uncompressed_sha256=hashlib.sha256(raw).hexdigest(),endpoints=endpoints,
        inference='intermediate progress only; no final gate decision'))
    print(json.dumps(dict(checkpoint=str(target.relative_to(ROOT)),completed_inputs=count,packed_bytes=len(packed))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint-root',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--freeze-commit',required=True)
    a=p.parse_args();run(a.checkpoint_root,a.count,a.freeze_commit)
