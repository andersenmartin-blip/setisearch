#!/usr/bin/env python3
"""Operational coordinator for the 23 untouched DEV recipes; no RNG here."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

def main():
    base = Path('results/radio_pilot_dev_20261008')
    root_receipt = json.loads(Path('pilot_protocol_20261008/dev_admission.json').read_text())
    cases = json.loads(Path('pilot_controls_20261008/development_cases.json').read_text())
    first = json.loads((base/'job_000/resource_receipt.json').read_text())
    outcome = json.loads((base/'job_000/case_000/outcome.json').read_text())
    if not first['caps_passed'] or not outcome['data_integrity_ok']:
        raise ValueError('First full-family job did not establish resource feasibility')
    allocation_path = base/'parallel_allocation.json'
    if allocation_path.exists() or any((base/f'job_{i:03d}').exists() for i in range(1,24)):
        raise ValueError('Distinct continuation already attempted; no replay')
    if len(cases) != 24 or cases[0]['case_id'] != outcome['case_id']:
        raise ValueError('Frozen case order differs')
    reservations = 23*1500.0
    remaining = 38000.0-first['cpu_s']
    if reservations > remaining:
        raise ValueError('Exclusive CPU reservations exceed remaining DEV allowance')
    spec = {'scope':'DEV_ONLY_DISTINCT_REMAINING_23',
            'scientific_definition_commit':root_receipt['public_commit_sha'],
            'coordinator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'previous_job_actual_cpu_s':first['cpu_s'],
            'remaining_DEV_allowance_before_reservations_cpu_s':remaining,
            'exclusive_cpu_reservations_s':reservations,
            'unallocated_margin_cpu_s':remaining-reservations,
            'maximum_concurrent_jobs':4,
            'case_ids':[c['case_id'] for c in cases[1:]],
            'per_job_cpu_reservation_s':1500.0,
            'per_job_wall_limit_s':1800.0,
            'validation_or_pilot_execution':False}
    write(allocation_path,spec)
    # Allocate every disjoint case before starting any child; no shared allowance.
    for i,c in enumerate(cases[1:],1):
        rec=dict(root_receipt)
        rec['allowed_case_ids']=[c['case_id']]
        rec['budget']={'remaining_cpu_seconds':1500.0,
                       'max_wall_seconds_per_job':1800.0,
                       'max_rss_bytes':4294967296}
        rec['exclusive_partition_id']=f'job_{i:03d}'
        write(base/f'admission_job_{i:03d}.json',rec)
    def run(item):
        i,c=item
        cmd=[sys.executable,'pilot_engine_20261008/run_dev.py',
             '--contract','pilot_controls_20261008/control_contract.json',
             '--cases','pilot_controls_20261008/development_cases.json',
             '--generator','pilot_controls_20261008/generator.py',
             '--summarizer','pilot_controls_20261008/summarize.py',
             '--freeze-receipt',str(base/f'admission_job_{i:03d}.json'),
             '--case',c['case_id'],'--output',str(base/f'job_{i:03d}')]
        write(base/f'command_job_{i:03d}.json',{'argv':cmd})
        with (base/f'job_{i:03d}.log').open('w') as log:
            p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        result={'job_index':i,'case_id':c['case_id'],'returncode':p.returncode}
        result_path=base/f'job_{i:03d}/case_000/outcome.json'
        if result_path.exists(): result['outcome']=json.loads(result_path.read_text())
        print(json.dumps(result),flush=True)
        return result
    start=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(run,enumerate(cases[1:],1)))
    cpu=resource.getrusage(resource.RUSAGE_SELF)
    children=resource.getrusage(resource.RUSAGE_CHILDREN)
    write(base/'continuation_completion.json',{
        'results':results,'wall_s':time.monotonic()-start,
        'controller_cpu_s':cpu.ru_utime+cpu.ru_stime,
        'children_cpu_s':children.ru_utime+children.ru_stime,
        'all_returncodes_zero':all(x['returncode']==0 for x in results),
        'scientific_gate':'NOT_EVALUATED_DEVELOPMENT_ONLY'})
    return 0 if all(x['returncode']==0 for x in results) else 1

if __name__=='__main__': raise SystemExit(main())
