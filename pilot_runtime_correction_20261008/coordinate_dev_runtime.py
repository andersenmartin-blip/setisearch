"""Run the two new, admitted operational DEV proofs exactly once."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent

def write(p, x):
    p.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')

def main():
    admitted = ROOT / 'pilot_runtime_correction_20261008/dev_runtime_admission.json'
    receipt = json.loads(admitted.read_text())
    cases = json.loads((ROOT / 'pilot_runtime_correction_20261008/development_runtime_cases.json').read_text())
    if receipt['status'] != 'ADMITTED_DEV_RUNTIME_ONLY' or len(cases) != 2:
        raise ValueError('Both new development-only cases require explicit admission')
    budget = receipt['budget']
    if budget['exclusive_cpu_allocation_seconds'] != 1800 or 3600 > budget['remaining_cpu_seconds']:
        raise ValueError('Two distinct full partitions must fit the existing remaining budget')
    if receipt['allowed_case_ids'] != [c['case_id'] for c in cases]:
        raise ValueError('Only the two newly frozen DEV_RUNTIME identities are allowed')
    base = ROOT / 'results/radio_pilot_dev_runtime_20261008'
    base.mkdir(parents=True, exist_ok=False)
    write(base / 'allocation.json', {'exclusive_CPU_s_each':1800,'total_CPU_reservation_s':3600,
        'cases':[c['case_id'] for c in cases], 'public_commit':receipt['public_commit_sha']})
    start = time.monotonic()
    def run(item):
        i, c = item
        command = [sys.executable, str(ROOT / 'pilot_runtime_correction_20261008/run_dev_runtime.py'),
                   '--admission', str(admitted), '--case', c['case_id'],
                   '--output', str(base / f'case_{i:03d}'),
                   '--claim-directory', str(ROOT / 'pilot_protocol_20261008/dev_runtime_correction_claims')]
        write(base / f'command_{i:03d}.json', {'argv':command})
        with (base / f'case_{i:03d}.log').open('x') as log:
            child = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        outcome = {'index':i,'case_id':c['case_id'],'returncode':child.returncode}
        result_path = base / f'case_{i:03d}/outcome.json'
        if result_path.exists():
            outcome['outcome'] = json.loads(result_path.read_text())
        print(json.dumps(outcome), flush=True)
        return outcome
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, enumerate(cases)))
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    completion = {'results':results,'wall_s':time.monotonic()-start,
                  'controller_CPU_s':own.ru_utime+own.ru_stime,
                  'children_CPU_s':children.ru_utime+children.ru_stime,
                  'all_returncodes_zero':all(x['returncode']==0 for x in results)}
    write(base / 'completion.json', completion)
    return 0 if completion['all_returncodes_zero'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
