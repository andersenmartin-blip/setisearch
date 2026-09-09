"""Sequential, process-isolated recovery using the unchanged published helpers."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--scan')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    a.runtime_root.mkdir(parents=True, exist_ok=True)
    if a.scan:
        import m43t_restore_inputs as inputs
        import m43t_restore_mirrors as mirrors
        from m43e_economical_bank import write_sealed
        if (a.output/f'restore.{a.scan}.json').exists():
            raise FileExistsError('preserve closed receipts; choose a fresh output directory')
        inputs.OUT = a.output
        mirrors.write_sealed = lambda path, record: write_sealed(a.output/path.name, record)
        mirrors.restore(a.runtime_root, a.scan)
        inputs.one(a.runtime_root, a.scan)
    else:
        for e in (1, 2, 3):
            for kind in ('on', 'off'):
                subprocess.run([sys.executable, __file__, '--runtime-root', str(a.runtime_root),
                    '--output', str(a.output), '--scan', f'epoch{e}_{kind}'], check=True)
        print('ALL SIX SOURCES AND 96 ARRAYS RESTORED', flush=True)


if __name__ == '__main__':
    main()
