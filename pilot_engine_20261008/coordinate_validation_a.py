#!/usr/bin/env python3
"""Run the fresh, pinned A bank once in exclusive CPU partitions; no RNG here."""
import concurrent.futures
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

def main():
    receipt_path=Path('pilot_protocol_20261008/validation_a_admission.json')
    receipt=json.loads(receipt_path.read_text())
    cases=json.loads(Path('pilot_controls_20261008/validation_a_cases.json').read_text())
    if receipt['status']!='ADMITTED_VALIDATION_A_ONLY' or len(cases)!=142:
        raise ValueError('Fresh complete A bank admission required')
    allocation=receipt['budget']['exclusive_cpu_allocation_seconds']
    if allocation!=250 or 142*allocation>receipt['global_cpu_remaining_before_allocation_s']:
        raise ValueError('Distinct exclusive case partitions do not fit global allowance')
    base=Path('results/radio_pilot_validation_a_20261008')
    base.mkdir(parents=True,exist_ok=False)
    write(base/'allocation.json',{'case_count':142,'exclusive_cpu_s_each':allocation,
        'total_CPU_reservation_s':142*allocation,'maximum_concurrent_jobs':8,
        'validation_public_commit':receipt['public_commit_sha'],
        'scientific_definition_commit':'cbc27ebfb10fc09f58a8ab4a1f00adad47ab1960',
        'case_ids':[c['case_id'] for c in cases]})
    for i,c in enumerate(cases):
        rec=dict(receipt); rec['allowed_case_ids']=[c['case_id']]
        rec['exclusive_partition_id']=f'case_{i:03d}'
        write(base/f'admission_{i:03d}.json',rec)
    def run(item):
        i,c=item
        cmd=[sys.executable,'pilot_engine_20261008/run_validation.py',
          '--contract','pilot_controls_20261008/control_contract.json',
          '--cases','pilot_controls_20261008/validation_a_cases.json',
          '--development-cases','pilot_controls_20261008/development_cases.json',
          '--validation-b-cases','pilot_controls_20261008/validation_b_cases.json',
          '--development-outcomes','pilot_protocol_20261008/dev_complete_outcomes.json',
          '--development-summary','pilot_protocol_20261008/dev_complete_summary.json',
          '--generator','pilot_controls_20261008/generator.py',
          '--summarizer','pilot_controls_20261008/summarize.py',
          '--freeze-receipt',str(base/f'admission_{i:03d}.json'),
          '--claim-directory','pilot_protocol_20261008/validation_a_claims',
          '--case',c['case_id'],'--output',str(base/f'case_{i:03d}')]
        write(base/f'command_{i:03d}.json',{'argv':cmd})
        with (base/f'case_{i:03d}.log').open('w') as log:
            p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        result={'index':i,'case_id':c['case_id'],'returncode':p.returncode}
        op=base/f'case_{i:03d}/outcome.json'
        if op.exists():
            x=json.loads(op.read_text())
            result.update({k:x.get(k) for k in ['family','data_integrity_ok',
                'all_active_on_recovered','pre_OFF_all_active_recovery',
                'survivor_count','failure','cpu_s','wall_s']})
        print(json.dumps(result),flush=True)
        return result
    start=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(run,enumerate(cases)))
    own=resource.getrusage(resource.RUSAGE_SELF)
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    write(base/'completion.json',{'results':results,'wall_s':time.monotonic()-start,
        'controller_CPU_s':own.ru_utime+own.ru_stime,
        'children_CPU_s':child.ru_utime+child.ru_stime,
        'all_returncodes_zero':all(x['returncode']==0 for x in results)})
    return 0 if all(x['returncode']==0 for x in results) else 1

if __name__=='__main__': raise SystemExit(main())
