"""Restore unchanged published native inputs; preserve historical recovery logs."""
import argparse
from pathlib import Path
import m43t_restore_inputs as inputs
import m43t_restore_mirrors as mirrors
from m43e_economical_bank import write_sealed
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43z_joint_controls/restoration'

def run(runtime):
    OUT.mkdir(parents=True,exist_ok=True)
    # Redirect recovery receipts only; all source/config/hash checks are unchanged.
    inputs.OUT=OUT
    mirrors.write_sealed=lambda path,record:write_sealed(OUT/path.name,record)
    for epoch in (1,2,3):
        for kind in ('on','off'):
            label=f'epoch{epoch}_{kind}'
            mirrors.restore(runtime,label)
            inputs.one(runtime,label)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True)
    run(p.parse_args().runtime_root)
