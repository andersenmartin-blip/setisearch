"""Launch exactly the three admitted primary jobs once; preserve exit evidence.

This orchestrator does not import numerical libraries or open source arrays.
The numerical child enforces its own frozen limits and source admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = 'analysis/s2017_control_targets_20261011'
JOBS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--child-arguments-json', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    config = json.loads(args.child_arguments_json.read_text())
    assert config['jobs'] == list(JOBS)
    extra = config['child_arguments']
    assert isinstance(extra, list) and all(isinstance(a, str) for a in extra)
    assert '--root-go-sha256' in extra and '--public-freeze-sha256' in extra
    evidence = root / 'continuation_20261011' / 'execution' / 'control_target_primary'
    evidence.mkdir(parents=True, exist_ok=False)
    command0 = [sys.executable, str(root / BASE / 'driver.py'), '--root', str(root)]
    started = time.monotonic()
    processes, records, streams = {}, [], []
    try:
        for job in JOBS:
            assert not (root / BASE / 'results' / job).exists()
            log = evidence / (job + '.log')
            stream = log.open('xb')
            streams.append(stream)
            command = command0 + ['--job', job] + extra
            proc = subprocess.Popen(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
            processes[proc.pid] = (proc, job, log, command)
        while processes:
            if time.monotonic() - started > 1810:
                for proc, *_ in processes.values():
                    proc.kill()
                raise TimeoutError('Outer 1810s numerical-family wall bound')
            pid, status, usage = os.wait4(-1, os.WNOHANG)
            if not pid:
                time.sleep(0.5)
                continue
            proc, job, log, command = processes.pop(pid)
            proc.returncode = os.waitstatus_to_exitcode(status)
            rec = {'job': job, 'exit_code': proc.returncode,
                   'outer_child_CPU_seconds': usage.ru_utime + usage.ru_stime,
                   'outer_child_peak_RSS_bytes': usage.ru_maxrss * 1024,
                   'command': command,
                   'log': str(log.relative_to(root)),
                   'completed_receipt': BASE + '/results/' + job + '/EXECUTION_RECEIPT.json'}
            records.append(rec)
            print(json.dumps({'job': job, 'exit_code': proc.returncode,
                              'child_CPU_seconds': rec['outer_child_CPU_seconds']}), flush=True)
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())
        for rec in records:
            log = root / rec['log']
            rec['log_sha256'] = sha(log)
            path = root / rec['completed_receipt']
            rec['completed_receipt_sha256'] = sha(path) if path.is_file() else None
            receipt = json.loads(path.read_text()) if path.is_file() else {}
            rec['actual_receipt_status'] = receipt.get('status')
        good = all(r['exit_code'] == 0 and r['actual_receipt_status'] ==
                   'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY' for r in records)
        result = {'schema': 'SETI_CONTROL_PRIMARY_ACTUAL_OUTER_EXECUTION_V1',
                  'status': 'PASS_THREE_ACTUAL_EXIT0_COMPLETE_JOBS' if good else 'FAILED_PRESERVED_NO_RETRY',
                  'launcher_sha256': sha(Path(__file__).resolve()),
                  'configuration_sha256': sha(args.child_arguments_json),
                  'wall_seconds': time.monotonic() - started,
                  'records': sorted(records, key=lambda r: JOBS.index(r['job'])),
                  'new_source_requests': 0, 'automated_retries': 0}
        path = evidence / 'OUTER_EXECUTION.json'
        with path.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        if not good:
            raise RuntimeError('One or more numerical children failed; evidence preserved')
    except BaseException as exc:
        for proc, *_ in processes.values():
            if proc.returncode is None:
                proc.kill()
        for pid, (proc, job, log, command) in list(processes.items()):
            _, status, usage = os.wait4(pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            records.append({'job': job, 'exit_code': proc.returncode,
                            'outer_child_CPU_seconds': usage.ru_utime + usage.ru_stime,
                            'outer_child_peak_RSS_bytes': usage.ru_maxrss * 1024,
                            'command': command, 'log': str(log.relative_to(root)),
                            'completed_receipt': BASE + '/results/' + job + '/EXECUTION_RECEIPT.json'})
            del processes[pid]
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())
        for rec in records:
            rec['log_sha256'] = sha(root / rec['log'])
            path = root / rec['completed_receipt']
            rec['completed_receipt_sha256'] = sha(path) if path.is_file() else None
        path = evidence / 'OUTER_EXECUTION.json'
        if not path.exists():
            with path.open('x') as stream:
                json.dump({'schema': 'SETI_CONTROL_PRIMARY_ACTUAL_OUTER_EXECUTION_V1',
                           'status': 'FAILED_PRESERVED_NO_RETRY',
                           'failure_type': type(exc).__name__, 'failure': str(exc),
                           'launcher_sha256': sha(Path(__file__).resolve()),
                           'configuration_sha256': sha(args.child_arguments_json),
                           'wall_seconds': time.monotonic() - started,
                           'records': sorted(records, key=lambda r: JOBS.index(r['job'])),
                           'new_source_requests': 0, 'automated_retries': 0}, stream, indent=2)
                stream.write('\n')
        raise
    finally:
        for proc, *_ in processes.values():
            proc.kill()
        for stream in streams:
            stream.close()

if __name__ == '__main__':
    main()
