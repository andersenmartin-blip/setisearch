#!/usr/bin/env python3
"""Meter one report-rendering child; the frozen reporter gates closed inputs."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent.parent

def main():
    review = BASE / 'pilot_protocol_20261008/review'
    log_path = review / 'METHOD_REPORT_STDOUT.log'
    receipt_path = review / 'METHOD_REPORT_WHOLE_JOB_RESOURCE_RECEIPT.json'
    assert not receipt_path.exists() and not log_path.exists()
    command = ['prlimit', '--as=4294967296', '--cpu=180', '--', 'timeout', '300s',
               'env', 'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1',
               'MKL_NUM_THREADS=1', 'NUMEXPR_NUM_THREADS=1', sys.executable,
               str(BASE / 'pilot_method_study_20261008/build_method_report.py'),
               '--output', str(BASE / 'results/radio_pilot_method_report_20261008')]
    start = time.monotonic()
    with log_path.open('xb') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                 cwd=BASE, start_new_session=True)
        _, status, usage = os.wait4(child.pid, 0)
        child.returncode = os.waitstatus_to_exitcode(status)
        log.flush()
        os.fsync(log.fileno())
    own = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'CLOSED_REPORT_RENDERING_ONLY', 'argv': command,
               'child_exit_code': child.returncode,
               'whole_child_CPU_s': usage.ru_utime + usage.ru_stime,
               'whole_child_wall_s': time.monotonic() - start,
               'whole_child_peak_RSS_bytes': usage.ru_maxrss * 1024,
               'controller_CPU_s': own.ru_utime + own.ru_stime,
               'CPU_accounting': 'Component of existing 1200-second preparation planning reservation; no reserve refund.',
               'qualification': False, 'generation_or_search': False}
    with receipt_path.open('x') as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps(receipt))
    return child.returncode

if __name__ == '__main__':
    raise SystemExit(main())
