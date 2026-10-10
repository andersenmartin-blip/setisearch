#!/usr/bin/env python3
"""Synthetic plugin/runtime check under actual profile memory and CPU limits."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

def main():
    stage = Path('/workspace/scratch/a8d1e29996d0/seti_fullpower_work/recovery_design/cross_on_review')
    receipt = stage / 'ISOLATED_PROFILE_H5_RUNTIME_FIXTURE_RECEIPT.json'
    fixture = stage / 'ISOLATED_PROFILE_H5_SYNTHETIC_FIXTURE.h5'
    assert not receipt.exists() and not fixture.exists()
    environment = os.environ.copy()
    environment['PYTHONPATH'] = '/workspace/scratch/a8d1e29996d0/seti_fullpower_work/deps'
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLOSC_NTHREADS'):
        environment[name] = '1'
    code = '''import sys,json
import numpy as np
import h5py,hdf5plugin
assert np.__version__ == "2.3.5"
value = np.array([float(index % 23) + .25 for index in range(16*129)], dtype="<f4").reshape(16,1,129)
with h5py.File(sys.argv[1], "x") as handle:
    dataset = handle.create_dataset("data", data=value, chunks=(1,1,129), **hdf5plugin.Blosc(cname="lz4",clevel=5,shuffle=hdf5plugin.Blosc.BITSHUFFLE))
    assert dataset.id.get_create_plist().get_filter(0)[0] == 32001
with h5py.File(sys.argv[1], "r") as handle:
    actual = handle["data"][:]
assert actual.dtype.str == "<f4" and actual.shape == (16,1,129) and actual.tobytes() == value.tobytes()
print(json.dumps({"status":"PASS_SYNTHETIC_NATIVE_FILTER32001_ROUNDTRIP","cells":2096,"numpy":np.__version__,"h5py":h5py.__version__}))
'''
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (20,22))
        resource.setrlimit(resource.RLIMIT_AS, (1073741824,1073741824))
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    child = subprocess.run([sys.executable, '-c', code, str(fixture)], env=environment,
                           preexec_fn=limits, capture_output=True, timeout=60)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    passed = child.returncode == 0 and cpu < 20 and after.ru_maxrss * 1024 < 1073741824
    value = {'status':'PASS_ISOLATED_SYNTHETIC_H5_RUNTIME_UNDER_1GiB' if passed else 'FAIL_ISOLATED_SYNTHETIC_H5_RUNTIME',
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'child_exit_code':child.returncode,'child_CPU_seconds':cpu,'child_wall_seconds':time.monotonic()-start,
             'child_peak_RSS_bytes':after.ru_maxrss*1024,'memory_cap_bytes':1073741824,
             'synthetic_fixture_only':True,'real_source_files_opened':0,'source_HTTP_requests':0,
             'child_stdout':child.stdout.decode(),'child_stderr':child.stderr.decode()[-4096:]}
    with receipt.open('x') as handle:
        json.dump(value, handle, indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    print(json.dumps({k:value[k] for k in ('status','child_exit_code','child_CPU_seconds','child_peak_RSS_bytes')}))
    if not passed:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
