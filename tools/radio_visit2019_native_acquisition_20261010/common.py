"""Inert standard-library contract helpers; no source, HDF5, or array imports."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_visit2019_native_acquisition_20261010'
TOOLS = 'tools/' + FAMILY
RESULTS = 'results/' + FAMILY
PRIVATE = ROOT.parent / 'seti_fullpower_work'
DEPS = PRIVATE / 'deps'
SHARED_ROOTS = [str(ROOT.parent), '/workspace/scratch/5bf3860dacd6']
LIMITS = {'CPU_seconds': 120, 'wall_seconds': 1800, 'memory_bytes': 536870912,
          'payload_BODY_bytes': 268435456, 'shared_workspace_bytes': 12884901888}
SOURCES = (
    ('S2019_31_BLC77_ON1_0077', 'HIP98505', 'blc77_guppi_58755_79249_HIP98505_0077.gpuspec.0000.h5'),
    ('S2019_31_BLC77_CONTROL1_0078', 'HIP98375', 'blc77_guppi_58755_79564_HIP98375_0078.gpuspec.0000.h5'),
    ('S2019_31_BLC77_ON2_0079', 'HIP98505', 'blc77_guppi_58755_79879_HIP98505_0079.gpuspec.0000.h5'),
    ('S2019_31_BLC77_CONTROL2_0080', 'HIP98154', 'blc77_guppi_58755_80200_HIP98154_0080.gpuspec.0000.h5'),
    ('S2019_31_BLC77_ON3_0081', 'HIP98505', 'blc77_guppi_58755_80521_HIP98505_0081.gpuspec.0000.h5'),
    ('S2019_31_BLC77_CONTROL3_0082', 'HIP98440', 'blc77_guppi_58755_80832_HIP98440_0082.gpuspec.0000.h5'),
)
BASE_URL = 'https://bldata.berkeley.edu/pipeline/AGBT19B_999_31/blc77/'
MIDPOINT_RULE = 'floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for piece in iter(lambda: handle.read(1048576), b''):
            h.update(piece)
    return h.hexdigest()


def relative(value):
    require(isinstance(value, str), 'Expected ROOT-relative string path')
    p = Path(value)
    require(p.parts and not p.is_absolute() and '..' not in p.parts, 'Invalid relative path')
    p = ROOT / p
    require(p.resolve() == p and ROOT in p.parents, 'Escaped or noncanonical path')
    return p


def pin(path):
    path = Path(path)
    require(path.resolve() == path and ROOT in path.parents and not path.is_symlink(), 'Bad pin path')
    require(stat.S_ISREG(path.stat().st_mode), 'Expected regular pinned file')
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def read_pin(record, max_bytes=16777216):
    require(isinstance(record, dict) and set(record) == {'path', 'bytes', 'sha256'}, 'Bad pin schema')
    require(type(record['bytes']) is int and 0 <= record['bytes'] <= max_bytes
            and re.fullmatch(r'[0-9a-f]{64}', record['sha256']), 'Bad pin size/hash')
    path = relative(record['path'])
    require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Expected regular pinned input')
    require(path.stat().st_size == record['bytes'], 'Pinned input size changed')
    raw = path.read_bytes()
    require(len(raw) == record['bytes'] and sha(raw) == record['sha256'], 'Pinned input changed')
    return raw


def read_json(record):
    return json.loads(read_pin(record))


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(path, value, create_only=False):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= 16777216, 'Receipt serialization exceeds finite cap')
    path = Path(path)
    if create_only:
        with path.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    else:
        temp = path.with_name(path.name + '.tmp')
        with temp.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    fsync_dir(path.parent)


def allocated_bytes(roots):
    total, seen = 0, set()
    for root in roots:
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(base) / name).is_symlink()]
            for name in files:
                info = (Path(base) / name).lstat()
                key = (info.st_dev, info.st_ino)
                if stat.S_ISREG(info.st_mode) and key not in seen:
                    seen.add(key)
                    total += max(info.st_size, info.st_blocks * 512)
    return total


def output_bytes(path):
    return allocated_bytes([path])


def exact_environment():
    require(os.environ.get('PYTHONPATH') == str(DEPS)
            and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1',
            'Exact own dependency path and disabled bytecode writes required')
