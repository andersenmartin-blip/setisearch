"""Once-only bounded launcher for the final metadata checkpoint, not a science run."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from zoneinfo import ZoneInfo


def main():
    root = Path(__file__).resolve().parents[2]
    folder = root / 'results/radio_final_checkpoint_20261020'
    scope = json.loads((folder / 'CHECKPOINT_SCOPE.json').read_text())
    if datetime.now(ZoneInfo('Europe/Copenhagen')).date().isoformat() != scope['actual_date']:
        raise RuntimeError('Wrong checkpoint date')
    for entry in scope['checkpoint_code_pins']:
        if hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Checkpoint code differs from public freeze')
    with (folder / 'RUN_CLAIM.json').open('x') as f:
        json.dump({'status': 'CLAIMED_ONCE', 'scope_sha256': hashlib.sha256((folder / 'CHECKPOINT_SCOPE.json').read_bytes()).hexdigest(),
                   'public_freeze_commit': os.environ['SETI_FINAL_FREEZE_COMMIT'],
                   'CPU_reservation_s': 2000, 'maximum_child_CPU_s': 60}, f, indent=2)
        f.write('\n')

    def limit():
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
        resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    start = time.monotonic(); timeout = False
    command = [sys.executable, str(root / 'tools/final_checkpoint_20261020/check.py'), str(root)]
    with (folder / 'stdout.log').open('xb') as out, (folder / 'stderr.log').open('xb') as err:
        proc = subprocess.Popen(command, stdout=out, stderr=err, preexec_fn=limit,
                                start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status); break
            if time.monotonic() - start >= 120:
                timeout = True; os.killpg(proc.pid, signal.SIGKILL)
            time.sleep(.02)
    cpu = usage.ru_utime + usage.ru_stime
    output_bytes = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
    ok = proc.returncode == 0 and not timeout and cpu <= 60 and output_bytes <= 16777216
    receipt = {'status': 'METADATA_PROCESS_COMPLIANT_ONLY' if ok else 'FAILED_RETAINED',
               'command': command, 'wait4_reaped': True, 'exit_code': proc.returncode,
               'whole_child_CPU_s': cpu, 'wall_s': time.monotonic() - start,
               'peak_RSS_bytes': usage.ru_maxrss * 1024, 'timed_out': timeout,
               'output_bytes_at_process_completion': output_bytes,
               'checkpoint_reservation_CPU_s_retained': 2000,
               'whole_activity_CPU_s_measured': False,
               'unmeasured_preparation_delivery_review_reserved_CPU_s': 1940,
               'scientific_search_or_QA_or_admission_established': False}
    with (folder / 'PROCESS_RECEIPT.json').open('x') as f:
        json.dump(receipt, f, indent=2); f.write('\n')
    print(json.dumps(receipt, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
