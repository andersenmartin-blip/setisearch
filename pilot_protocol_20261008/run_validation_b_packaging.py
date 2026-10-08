#!/usr/bin/env python3
"""Inert wrapper measuring the whole archival child process after B closure."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coordinator-closed',action='store_true')
    parser.add_argument('--coordinator-exit-code',type=int,required=True)
    args = parser.parse_args()
    if not args.coordinator_closed:
        raise ValueError('Parent must confirm coordinator and child processes closed before archival invocation')
    root = Path(__file__).resolve().parents[1]
    start,cpu = time.monotonic(),time.process_time()
    command = [sys.executable,str(Path(__file__).with_name('package_validation_b.py')),
               '--coordinator-closed','--coordinator-exit-code',str(args.coordinator_exit_code)]
    result = subprocess.run(command,cwd=root)
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    if result.returncode:
        record = {'phase':'VAL_B_archival_child_failed','returncode':result.returncode,
                  'wall_s':time.monotonic()-start,'cpu_s':used.ru_utime+used.ru_stime,
                  'peak_rss_bytes':used.ru_maxrss*1024,'originals_preserved':True,
                  'scientific_work_performed':False,'no_automatic_archival_replay':True,
                  'budget_binding':'Measured archival child CPU within shared1200second root preparation planning reserve.'}
        p=root/'pilot_protocol_20261008/validation_b_packaging_failure_receipt.json'
        p.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
        return result.returncode
    path = root/'pilot_protocol_20261008/validation_b_packaging_resource_receipt.json'
    record = json.loads(path.read_text())
    record.update(internal_interval_wall_s=record['wall_s'],internal_interval_cpu_s=record['cpu_s'],
                  wall_s=time.monotonic()-start,cpu_s=used.ru_utime+used.ru_stime,
                  peak_rss_bytes=used.ru_maxrss*1024,whole_child_python_process_measured=True,
                  wrapper_cpu_s=time.process_time()-cpu,
                  wrapper_sha256=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='Entire archival Python child process including imports and final resource receipt write. Wrapper intervalCPU tracked separately; earlier preparation/MCP upload CPU remains unmeasured, not zero, within existing1200second planning reserve.')
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    temporary.replace(path)
    print(json.dumps(record),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
