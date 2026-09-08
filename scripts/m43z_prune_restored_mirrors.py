"""Release redundant sparse HTTP caches only after source and 16 anchors verify."""
import argparse,time
from pathlib import Path
from m43e_economical_bank import read_sealed,write_sealed
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43z_joint_controls/restoration'

def run(runtime):
    done={};deadline=time.monotonic()+3600
    while len(done)<6:
        for e in (1,2,3):
            for kind in ('on','off'):
                label=f'epoch{e}_{kind}';proof=OUT/f'restore.{label}.json'
                if label in done or not proof.exists():continue
                r=read_sealed(proof)
                if not r.get('complete'):continue
                assert len(r['arrays'])==16 and all(a['original_digest_exact'] for a in r['arrays'])
                paths=[runtime/'mirrors'/f'{label}.h5.sparse',runtime/'mirrors'/f'{label}.h5.sparse.ranges.json']
                removed=[]
                for p in paths:
                    if p.exists():p.unlink();removed.append(p.name)
                done[label]=dict(source_receipt_sha256=r['source_receipt_sha256'],verified_anchor_arrays=16,
                    removed_redundant_cache_files=removed,source_and_anchor_files_preserved=True)
                write_sealed(OUT/'cache_cleanup.json',dict(complete=len(done)==6,scans=done))
                print(label+': retained verified source and anchors; released redundant HTTP cache',flush=True)
        if time.monotonic()>deadline:raise TimeoutError('restoration did not finish within one hour')
        if len(done)<6:time.sleep(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True);run(p.parse_args().runtime_root)
