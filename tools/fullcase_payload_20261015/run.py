"""One bounded whole engineering suite, with authoritative outer wait4."""
import hashlib
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
    result = root / 'results'; result.mkdir()
    scope = json.loads((root / 'ENGINEERING_SCOPE.json').read_text())
    pins = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()
            if p.suffix in ('.py', '.json') and p.is_file()}
    reservation = {'status': 'ENGINEERING_ONLY_RESERVED_BEFORE_LAUNCH',
                   'total_reservation_CPU_s': 900, 'fixture_CPU_s_cap': 600,
                   'metadata_delivery_reserved_CPU_s': 300,
                   'pins': pins, 'source_scientific_bank_admitted': False}
    (result / 'RUN_RESERVATION.json').write_text(json.dumps(reservation, indent=2) + '\n')
    own_workspace = root.parent.parent.parent
    used = sum(p.stat().st_size for p in own_workspace.rglob('*')
               if p.is_file() and not p.is_symlink())
    if used + scope['new_output_artifact_cap_bytes'] > scope['workspace_cap_bytes']:
        raise RuntimeError('Cannot reserve engineering workspace capacity')
    def limit():
        resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
        resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    start = time.monotonic(); timeout = False
    with (result / 'suite.stdout.log').open('xb') as out, (result / 'suite.stderr.log').open('xb') as err:
        proc = subprocess.Popen([sys.executable, str(root / 'suite.py')], stdout=out, stderr=err,
                    preexec_fn=limit, start_new_session=True,
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                         'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status); break
            if time.monotonic() - start >= 1200:
                timeout = True; os.killpg(proc.pid, signal.SIGKILL)
            time.sleep(.1)
    cpu = usage.ru_utime + usage.ru_stime
    artifact_bytes = sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
    receipt = {'status': 'CLOSED_RETAINED', 'exit_code': proc.returncode, 'wait4_reaped': True,
               'whole_suite_including_reaped_descendants_CPU_s': cpu,
               'wall_s': time.monotonic() - start, 'peak_RSS_bytes': usage.ru_maxrss * 1024,
               'timed_out': timeout, 'artifact_bytes': artifact_bytes,
               'total_reservation_CPU_s_retained': 900,
               'metadata_delivery_CPU_s_not_measured_or_refunded': 300}
    (result / 'WHOLE_SUITE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2)); print((result / 'suite.stderr.log').read_text())
    return 0 if proc.returncode == 0 and not timeout and cpu <= 600 and artifact_bytes <= 2147483648 else 1


if __name__ == '__main__': raise SystemExit(main())
