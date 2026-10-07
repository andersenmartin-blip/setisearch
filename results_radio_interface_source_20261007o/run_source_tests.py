"""One bounded administrative new-source cohort; preserve every output."""
import json
import os
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 ** 2, 384 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 ** 2, 32 * 1024 ** 2))
    paths = {key: ROOT / ('tests-attempt1.' + key + '.log') for key in ('stdout', 'stderr')}
    at = time.monotonic(); returncode = None; error = None
    with paths['stdout'].open('xb') as out, paths['stderr'].open('xb') as err:
        try:
            result = subprocess.run(['/usr/bin/python3', '-I', '-S', '-B', str(ROOT / 'test_interface.py')],
                                    cwd=ROOT.parent, stdout=out, stderr=err, timeout=110, check=False)
            returncode = result.returncode
        except BaseException as exc: error = {'type': type(exc).__name__, 'reason': str(exc)}
    seconds = time.monotonic() - at
    logical = allocated = files = dirs = 0
    for path in (ROOT, *ROOT.rglob('*')):
        st = path.lstat(); logical += st.st_size; allocated += st.st_blocks * 512
        if path.is_dir(): dirs += 1
        else: files += 1
    record = {'schema': 'radio-O-administrative-source-cohort-v1', 'returncode': returncode,
              'exception': error, 'seconds': seconds,
              'child_peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
              'evidence_footprint_before_this_receipt': {'logical_bytes': logical, 'allocated_bytes': allocated,
                                                       'files': files, 'dirs_including_root': dirs},
              'limits': {'external_wall_seconds': 120, 'child_timeout_seconds': 110, 'cpu_seconds': 60,
                         'address_space_bytes': 384*1024**2, 'descriptors':128, 'evidence_bytes':32*1024**2},
              'actual_native_callbacks':0, 'native_module_builds_loads':0, 'codec_handoffs':0,
              'native_runtime_science_authority':False}
    with (ROOT / 'ADMIN_COHORT-1.json').open('x') as out: json.dump(record,out,sort_keys=True); out.write('\n')
    if max(logical,allocated)>32*1024**2: raise ValueError('aggregate retained evidence ceiling exceeded')
    raise SystemExit(0 if returncode == 0 and error is None else 1)


if __name__ == '__main__': main()
