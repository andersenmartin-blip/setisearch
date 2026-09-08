"""Recover the original six sources into a new runtime with preserved receipts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import m43t_restore_inputs as inputs
import m43t_restore_mirrors as mirrors
from m43e_economical_bank import write_sealed


def run(runtime, output):
    output.mkdir(parents=True, exist_ok=True)
    inputs.OUT = output
    mirrors.write_sealed = lambda p,r:write_sealed(output/p.name, r)
    def one(label):
        # Never overwrite a closed restoration receipt. A new recovery session
        # must use a fresh output directory, even when reusing verified bytes.
        if (output/f'restore.{label}.json').exists():
            raise FileExistsError('choose a fresh recovery receipt directory')
        mirrors.restore(runtime, label)
        inputs.one(runtime, label)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one, [f'epoch{e}_{kind}' for e in (1,2,3) for kind in ('on','off')]))
    print('RESTORATION COMPLETE', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    run(a.runtime_root, a.output)
