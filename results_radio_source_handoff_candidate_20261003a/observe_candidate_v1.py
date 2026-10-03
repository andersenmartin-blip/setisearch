"""Bounded external observation of a fresh offline engineering subprocess.

This diagnostic observer grants no production, transport or scientific admission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def pin(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    stat = path.stat()
    return {'bytes': stat.st_size, 'sha256': h.hexdigest(),
            'device': stat.st_dev, 'inode': stat.st_ino,
            'mtime_ns': stat.st_mtime_ns, 'ctime_ns': stat.st_ctime_ns}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', required=True)
    p.add_argument('--cwd', required=True)
    p.add_argument('--pythonpath', required=True)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--rss', type=int, default=512*1024**2)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    evidence = Path(a.evidence)
    evidence.mkdir(parents=True, exist_ok=False)
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    env = {**os.environ, 'PYTHONPATH': a.pythonpath,
           'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1',
           'OMP_NUM_THREADS': '1'}
    start = time.monotonic()
    samples = []
    faults = []
    with (evidence/'stdout.log').open('xb') as out, (evidence/'stderr.log').open('xb') as err:
        child = subprocess.Popen(command, cwd=a.cwd, env=env, stdout=out, stderr=err,
                                 start_new_session=True)
        while child.poll() is None:
            elapsed = time.monotonic()-start
            try:
                fields = {}
                for line in Path(f'/proc/{child.pid}/status').read_text().splitlines():
                    key, _, value = line.partition(':')
                    if key in ('VmRSS', 'VmHWM', 'VmSize', 'Threads'):
                        fields[key] = int(value.split()[0])
                samples.append({'elapsed_seconds': elapsed, **fields})
                if fields.get('VmRSS', 0)*1024 > a.rss:
                    faults.append('observed RSS cap exceeded')
            except FileNotFoundError:
                pass
            if elapsed > a.seconds:
                faults.append('wall-time cap exceeded')
            if max(out.tell(), err.tell()) > 2*1024**2:
                faults.append('diagnostic log cap exceeded')
            if faults:
                os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(.02)
        rc = child.wait()
    record = {'schema': 'seti-offline-candidate-external-observation-v1',
              'command': command, 'cwd': a.cwd, 'pythonpath': a.pythonpath,
              'exit_code': rc, 'elapsed_seconds': time.monotonic()-start,
              'samples': samples, 'observed_peak_rss_bytes':
                  max((x.get('VmRSS', 0)*1024 for x in samples), default=0),
              'observed_peak_hwm_bytes':
                  max((x.get('VmHWM', 0)*1024 for x in samples), default=0),
              'candidate_limits': {'seconds': a.seconds, 'rss_bytes': a.rss,
                                   'log_bytes_each': 2*1024**2},
              'cap_failures': faults,
              'stdout': pin(evidence/'stdout.log'), 'stderr': pin(evidence/'stderr.log'),
              'observer_script': pin(Path(__file__)),
              'polling_can_miss_between_sample_peaks': True,
              'descendant_process_tree_not_certified': True,
              'whole_source_lifetime_qualified': False,
              'production_execution_admission': False,
              'scientific_execution_authorized': False}
    (evidence/'observation.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: record[k] for k in ('exit_code','elapsed_seconds',
          'observed_peak_rss_bytes','cap_failures')}))
    raise SystemExit(0 if rc == 0 and not faults else 1)


if __name__ == '__main__':
    main()
