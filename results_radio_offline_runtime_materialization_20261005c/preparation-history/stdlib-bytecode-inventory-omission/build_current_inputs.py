"""Bounded read-only preparation pins; no scientific/native package imports."""
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python')
STDLIB = PYTHON_ROOT / 'lib/python3.12'
PIP = STDLIB / 'site-packages/pip'
WHEELS = Path('/workspace/scratch/da6462abff17/package-source-preparation/verified-package-source/originals')
ORIGINAL_PLAN = Path('/workspace/scratch/da6462abff17/package-source-preparation/results_radio_runtime_bootstrap_preparation_20261005b/original-plan.json')
CAP = 512 * 1024 * 1024
started = time.monotonic()
charged = 0

def pin(path):
    global charged
    path = Path(path).resolve(strict=True)
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > 128 * 1024 * 1024:
        raise ValueError('unbounded/nonregular file')
    charged += st.st_size
    if charged > CAP or time.monotonic() - started > 60:
        raise ValueError('preparation read/wall cap')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(fd)
        named = path.stat(follow_symlinks=False)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode)
        if fields(st) != fields(before) or fields(before) != fields(after) or fields(after) != fields(named):
            raise ValueError('file changed during pinning')
        return dict(path=str(path), bytes=st.st_size, sha256=digest.hexdigest(), mode=stat.S_IMODE(st.st_mode))
    finally:
        os.close(fd)

def main():
    require_files = [p for p in STDLIB.rglob('*') if p.is_file() and
                     '__pycache__' not in p.parts and 'site-packages' not in p.parts]
    pip_files = [p for p in PIP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    require_files += pip_files + [Path(sys.executable).resolve(), PYTHON_ROOT / 'lib/libpython3.12.so.1.0']
    # Complete ambient startup mappings are retained as observations, not loader closure.
    maps = Path('/proc/self/maps').read_text()
    for line in maps.splitlines():
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5].startswith('/') and not fields[5].endswith(' (deleted)'):
            require_files.append(Path(fields[5]))
    # A fixed supplemental system dependency cohort; observed loader edges remain pending.
    system = Path('/usr/lib/x86_64-linux-gnu')
    for pattern in ['libz.so.*', 'libbz2.so.*', 'liblzma.so.*', 'libffi.so.*',
                    'libssl.so.*', 'libcrypto.so.*', 'libgcc_s.so.*', 'libstdc++.so.*',
                    'libsqlite3.so.*', 'libexpat.so.*', 'libcrypt.so.*', 'libzstd.so.*']:
        require_files.extend(system.glob(pattern))
    runtime = [pin(p) for p in sorted({p.resolve(strict=True) for p in require_files})]
    seed = [{'relative_path': 'pip/' + p.relative_to(PIP).as_posix(),
             'pin': next(x for x in runtime if x['path'] == str(p.resolve()))}
            for p in sorted(pip_files)]
    original = json.loads(ORIGINAL_PLAN.read_text())
    # The original schema is inspected without execution; caller fills unchanged wheel specs.
    result = dict(schema='radio-offline-runtime-current-inputs-v1',
            observation_only=True, scientific_authority=False, runtime_qualified=False,
            python_executable=str(Path(sys.executable).resolve()), python_version=list(sys.version_info[:3]),
            stdlib_root=str(STDLIB), runtime_pins=runtime, seed_pins=seed,
            original_plan_pin=pin(ORIGINAL_PLAN), wheel_pins=[pin(p) for p in sorted(WHEELS.glob('*.whl'))],
            startup_maps=maps, preparation_reserved_read_bytes=charged,
            preparation_elapsed_seconds=time.monotonic() - started,
            system_dependency_cohort_is_selected_not_complete_loader_closure=True)
    target = ROOT / 'current-inputs.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ['python_executable', 'python_version',
         'preparation_reserved_read_bytes', 'preparation_elapsed_seconds']}))
    print(json.dumps({'runtime_pins':len(runtime),'pip_seed_pins':len(seed),'bytes':target.stat().st_size}))

if __name__ == '__main__':
    main()
