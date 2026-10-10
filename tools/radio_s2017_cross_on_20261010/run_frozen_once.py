#!/usr/bin/env python3
"""Root-owned launcher: one child, actual outer resource receipt, no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-commit', required=True)
    args = parser.parse_args()
    repo = Path('/workspace/scratch/a8d1e29996d0/setisearch_fullpower')
    tool = repo / 'tools/radio_s2017_cross_on_20261010'
    stage = repo / 'results/radio_s2017_cross_on_20261010'
    scope_sha = 'dd96f3b30de939accd607fe5bedeca3c4450bedbeb80e5b284a0fc4651cbe5e5'
    admission_sha = 'ef1ed7eb7337042927f4d83111b527ada193bb9ffe8395fbe8f1cc619cd68f05'
    assert len(args.freeze_commit) == 40 and all(c in '0123456789abcdef' for c in args.freeze_commit)
    assert hashlib.sha256((tool / 'scope.json').read_bytes()).hexdigest() == scope_sha
    assert hashlib.sha256((stage / 'ROOT_ADMISSION.json').read_bytes()).hexdigest() == admission_sha
    assert not (stage / 'MATCH_STARTED_ONCE.json').exists()
    assert not (stage / 'measurement').exists()
    marker = {'status': 'ROOT_ONE_SHOT_CHILD_LAUNCH_STARTED', 'freeze_commit': args.freeze_commit,
              'launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (stage / 'ROOT_OUTER_STARTED.json').open('x', encoding='utf-8') as handle:
        json.dump(marker, handle, indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    environment = os.environ.copy()
    environment['PYTHONPATH'] = '/workspace/scratch/a8d1e29996d0/seti_fullpower_work/deps'
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        environment[name] = '1'
    command = [sys.executable, '-u', str(tool / 'match_saved.py'), '--scope', str(tool / 'scope.json'),
               '--expected-scope-sha256', scope_sha, '--expected-admission-sha256', admission_sha,
               '--freeze-commit', args.freeze_commit, '--root-go-after-closed-durable-QA']
    def child_limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 121))
        resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    child = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             preexec_fn=child_limits)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=1800)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        stdout, stderr = child.communicate()
    end = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = time.monotonic() - start
    cpu = end.ru_utime + end.ru_stime - before.ru_utime - before.ru_stime
    rss = end.ru_maxrss * 1024
    terminal = stage / 'measurement/EXECUTION_RECEIPT.json'
    inner = json.loads(terminal.read_bytes()) if terminal.exists() else None
    passed = (not timed_out and child.returncode == 0 and cpu <= 120 and wall <= 1800 and rss <= 1073741824
              and inner is not None and inner['status'] == 'COMPLETE_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_EXPLORATORY_ONLY')
    receipt = {**marker, 'status': 'PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS' if passed
               else 'FAIL_ONE_CHILD_NO_RETRY_OUTER_OR_INNER_INCOMPLETE', 'child_exit_code': child.returncode,
               'child_PID': child.pid, 'child_timed_out': timed_out, 'child_process_CPU_seconds': cpu,
               'child_wall_seconds': wall, 'child_peak_RSS_bytes': rss, 'CPU_cap_s': 120,
               'wall_cap_s': 1800, 'memory_cap_bytes': 1073741824, 'automatic_retry_performed': False,
               'inner_terminal_sha256': hashlib.sha256(terminal.read_bytes()).hexdigest() if inner else None,
               'inner_terminal_status': inner['status'] if inner else None,
               'child_stdout': stdout.decode('utf-8', errors='replace')[-8192:],
               'child_stderr': stderr.decode('utf-8', errors='replace')[-8192:]}
    with (stage / 'ROOT_OUTER_EXECUTION_RECEIPT.json').open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps({k: receipt[k] for k in ('status', 'child_exit_code', 'child_process_CPU_seconds',
                                            'child_wall_seconds', 'child_peak_RSS_bytes')}), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
