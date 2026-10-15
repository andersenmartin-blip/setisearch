"""Once-only, resource-measured engineering suite; never a scientific runner."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parent
    result = root / 'results'
    result.mkdir()  # No overwrite or automatic retry of a completed/partial suite.
    scope = json.loads((root / 'ENGINEERING_SCOPE.json').read_text())
    pins = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
            ('ENGINEERING_SCOPE.json', 'payload_store.py', 'executor.py',
             'fixture_worker.py', 'test_integration.py', 'run_suite.py')}
    reservation = {'status': 'ENGINEERING_ONLY_RESERVED_BEFORE_LAUNCH',
                   'reserved_CPU_s': scope['aggregate_reservation_CPU_s'],
                   'fixture_CPU_s_cap': scope['all_fixture_suites_CPU_s_cap'],
                   'metadata_reserved_CPU_s': scope['metadata_delivery_reserved_CPU_s'],
                   'scope_and_source_sha256': pins, 'python_version': sys.version,
                   'msgpack_version': importlib.metadata.version('msgpack'),
                   'new_science': False}
    (result / 'RUN_RESERVATION.json').write_text(json.dumps(reservation, indent=2) + '\n')

    def limits():
        cap = scope['all_fixture_suites_CPU_s_cap']
        resource.setrlimit(resource.RLIMIT_CPU, (cap, cap))
        cap = scope['whole_suite_address_space_bytes']
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.monotonic()
    timed_out = False
    with (result / 'suite.stdout.log').open('xb') as out, (result / 'suite.stderr.log').open('xb') as err:
        proc = subprocess.Popen([sys.executable, str(root / 'test_integration.py'),
                    str(result / 'suite')], stdout=out, stderr=err,
                    preexec_fn=limits, start_new_session=True,
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - started >= scope['whole_suite_wall_s_cap']:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
            time.sleep(.1)
    cpu = usage.ru_utime + usage.ru_stime
    receipt = {'status': 'CLOSED_RETAINED', 'exit_code': proc.returncode,
               'wait4_reaped': True, 'whole_suite_including_reaped_descendants_CPU_s': cpu,
               'wall_s': time.monotonic() - started,
               'peak_RSS_bytes': usage.ru_maxrss * 1024, 'timed_out': timed_out,
               'total_reservation_CPU_s_retained': scope['aggregate_reservation_CPU_s'],
               'metadata_reservation_not_measured_or_refunded_CPU_s': scope['metadata_delivery_reserved_CPU_s']}
    (result / 'WHOLE_SUITE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    print((result / 'suite.stderr.log').read_text())
    return 0 if proc.returncode == 0 and not timed_out and cpu <= scope['all_fixture_suites_CPU_s_cap'] else 1


if __name__ == '__main__': raise SystemExit(main())
