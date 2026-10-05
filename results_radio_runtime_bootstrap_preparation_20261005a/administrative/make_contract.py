"""Caller preparation from repository bytes; no gate or installer invocation."""
import hashlib
import base64
import json
import os
from pathlib import Path
import stat
import types

REPO = Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004')
NS = REPO / 'results_radio_runtime_bootstrap_preparation_20261005a'
PLAN = REPO / 'results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json'
IDENTITY = REPO.parent / 'bootstrap-20261005a-identity.json'
PYTHON = '/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'


def write_exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def pin(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError('selected repository source must be a sole-link regular file')
    raw = path.read_bytes()
    after = path.lstat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mode, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('repository source changed during preparation')
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode='%04o' % stat.S_IMODE(before.st_mode))


def main():
    plan_raw = PLAN.read_bytes()
    preread_raw = (NS / 'installer-preread.json').read_bytes()
    plan = json.loads(plan_raw)
    preread = json.loads(preread_raw)
    identity = json.loads(IDENTITY.read_bytes())
    # A separately hashed lossless representation supports bounded immutable
    # readback even when a text wrapper cannot return the >1 MiB manifest.
    transport = NS / 'publication-transport/installer-preread.json'
    transport.mkdir(parents=True, exist_ok=False)
    segments = []
    for number, offset in enumerate(range(0, len(preread_raw), 374997)):
        body = preread_raw[offset:offset+374997]
        encoded = base64.b64encode(body) + b'\n'
        part = transport / ('%06d.b64' % number)
        write_exclusive(part, encoded)
        segments.append(dict(path=str(part.relative_to(REPO)), raw_offset=offset, raw_bytes=len(body),
                             raw_sha256=hashlib.sha256(body).hexdigest(), bytes=len(encoded),
                             sha256=hashlib.sha256(encoded).hexdigest(),
                             git_blob=hashlib.sha1(b'blob ' + str(len(encoded)).encode() + b'\0' + encoded).hexdigest()))
    alias = dict(schema='radio-runtime-bootstrap-lossless-publication-transport-v1',
                 path=str((NS / 'installer-preread.json').relative_to(REPO)), bytes=len(preread_raw),
                 sha256=hashlib.sha256(preread_raw).hexdigest(),
                 git_blob=hashlib.sha1(b'blob ' + str(len(preread_raw)).encode() + b'\0' + preread_raw).hexdigest(),
                 parts=segments, encoding='canonical-base64-segments', scientific_authority=False)
    write_exclusive(NS / 'publication-transport/installer-preread-transport.json',
                    (json.dumps(alias, sort_keys=True, indent=2) + '\n').encode())
    root = Path(identity['output_root'])
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        observed = os.fstat(fd)
        if dict(device=observed.st_dev, inode=observed.st_ino, mode='%04o' % stat.S_IMODE(observed.st_mode)) != identity['output_root_identity'] or os.listdir(fd):
            raise ValueError('prospective root identity/emptiness differs')
    finally:
        os.close(fd)
    write_exclusive(NS / 'wheel-lock.txt', plan['materialization']['offline_hash_lock_utf8'].encode())
    names = ['bootstrap_gate.py', 'wheel_io.py', 'capture_basis.py', 'build_contracts.py',
             'PROTOCOL.md', 'prepare_installer_preread.py', 'installer-preread.json',
             'official-metadata-readback.json', 'official-metadata/numpy-2.3.5.json',
             'official-metadata/h5py-3.16.0.json', 'official-metadata/hdf5plugin-7.1.0.json', 'wheel-lock.txt']
    paths = [PLAN] + [NS / name for name in names]
    paths += [REPO / row['repository_artifact_path'] for row in preread['installer_source_files']]
    source = sorted([pin(path) for path in paths], key=lambda row: row['path'])
    builder_raw = (NS / 'build_contracts.py').read_bytes()
    module = types.ModuleType('_pure_preparation_builder')
    module.__file__ = str(NS / 'build_contracts.py')
    exec(compile(builder_raw, module.__file__, 'exec'), module.__dict__)
    result = module.build_contracts(plan_raw, preread_raw, source,
        bootstrap_identity=identity['bootstrap_identity'], output_root=str(root),
        output_root_identity=identity['output_root_identity'], python_executable=PYTHON,
        gate_path=str(NS / 'bootstrap_gate.py'), attribution_basis_path=str(NS / 'capture_basis.py'),
        wheel_io_path=str(NS / 'wheel_io.py'), plan_path=str(PLAN),
        activation_path=str(REPO / 'config/radio_runtime_bootstrap_20261005a.activate.json'))
    freeze_path = REPO / 'config/radio_runtime_bootstrap_20261005a.freeze.json'
    write_exclusive(freeze_path, result['freeze_raw'])
    write_exclusive(NS / 'pure-preparation.json', (json.dumps(result['preparation'], sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps(result['preparation'], sort_keys=True))


if __name__ == '__main__':
    main()
