"""Bounded engineering-test launcher; never invokes a scientific worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from guard import durable_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('label', choices=['process_clock'])
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    output = root / 'results'
    scope = json.loads((root / 'ENGINEERING_SCOPE.json').read_text())
    history = sorted(output.glob('WHOLE_*_RECEIPT.json'))
    prior = sum(json.loads(p.read_text())['whole_suite_including_reaped_descendants_CPU_s']
                for p in history)
    probe_charge = 1  # Separate clock probe conservatively charged, not refunded.
    reservation = 20
    if prior + probe_charge + reservation > scope['fixture_suite_CPU_s_cap']:
        raise RuntimeError('Engineering fixture CPU envelope cannot reserve another suite')
    stem = args.label.upper()
    claim = output / f'{stem}_RESERVATION.json'
    if claim.exists() or (output / f'suite_{args.label}').exists():
        raise RuntimeError('This engineering attempt already exists; retain it, no overwrite')
    durable_json(claim, {'status': 'ENGINEERING_ONLY_RESERVED_BEFORE_LAUNCH',
        'prior_suite_CPU_s': prior, 'probe_CPU_s_conservatively_charged': probe_charge,
        'suite_CPU_s_reserved': reservation, 'total_reservation_CPU_s_retained': 120,
        'prior_receipt_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in history},
        'pins': {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                 for n in ('ENGINEERING_SCOPE.json', 'guard.py', 'test_guard.py',
                           'run_engineering_suite.py')}})

    def limits():
        # This outer harness is single-threaded. Inner processes use guard exec.
        resource.setrlimit(resource.RLIMIT_CPU, (reservation, reservation))
        resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    start = time.monotonic()
    timed_out = False
    with (output / f'{args.label}.stdout.log').open('xb') as out, \
            (output / f'{args.label}.stderr.log').open('xb') as err:
        proc = subprocess.Popen([sys.executable, str(root / 'test_guard.py'),
                    str(output / f'suite_{args.label}')], stdout=out, stderr=err,
                    preexec_fn=limits, start_new_session=True,
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - start >= 120:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
            time.sleep(.05)
    cpu = usage.ru_utime + usage.ru_stime
    receipt = {'status': 'CLOSED_NO_RETRY', 'exit_code': proc.returncode,
               'wait4_reaped': True, 'whole_suite_including_reaped_descendants_CPU_s': cpu,
               'wall_s': time.monotonic() - start, 'peak_RSS_bytes': usage.ru_maxrss * 1024,
               'timed_out': timed_out, 'total_engineering_reservation_CPU_s_retained': 120}
    durable_json(output / f'WHOLE_{stem}_SUITE_RECEIPT.json', receipt)
    print(json.dumps(receipt, indent=2))
    print((output / f'{args.label}.stderr.log').read_text())
    return 0 if proc.returncode == 0 and not timed_out and cpu <= reservation else 1


if __name__ == '__main__':
    raise SystemExit(main())
