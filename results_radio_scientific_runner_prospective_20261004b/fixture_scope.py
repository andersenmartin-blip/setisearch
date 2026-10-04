"""Explicit synthetic qualification producer; no actual evidence certificates.

The preserved receiver test fixture supplies synthetic closure/outcome/receipt
shapes and 96 tiny deterministic rows. This producer never changes or promotes
those synthetic domains and never constructs maintained verification tokens.
"""
import hashlib
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCIENCE = ROOT / 'results_radio_scientific_execution_prospective_20261003a'
RETENTION = ROOT / 'results_radio_native_v3_execution_preparation_20261003f'
sys.path[:0] = [str(HERE), str(SCIENCE)]
import runner_v2 as runner


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            if count <= 0:
                raise OSError('short fixture write')
            offset += count
        os.fsync(fd); os.fchmod(fd, 0o400)
    finally:
        os.close(fd)


def fixture_packet():
    from test_receiver_telescope_adapter import gated_fixture
    metadata, rows = gated_fixture()
    return {'metadata': metadata, 'rows': {key: list(value) for key, value in rows.items()},
            'row_pins': {key: [runner.pin(row) for row in value] for key, value in rows.items()}}


def build(root, *, identity, fault='none', timeout=10, stdout_cap=65536,
          stderr_cap=65536, packet=None, registry=None):
    root = Path(root)
    need_new_registry = registry is None
    registry = root/'claims' if registry is None else Path(registry)
    if need_new_registry:
        registry.mkdir(mode=0o700)
    info = registry.stat()
    claim = {'path': str(registry), 'device': info.st_dev, 'inode': info.st_ino}
    packet_raw = runner.canonical(runner.pack(fixture_packet() if packet is None else packet))
    packet_path = root/'packet.json'
    write_new(packet_path, packet_raw)
    modules = {name: runner.file_pin((RETENTION if name == 'failure_output_retention'
                                     else SCIENCE)/f'{name}.py') for name in runner.MODULES}
    scope = {'schema': runner.SCHEMA, 'domain': 'synthetic-test-fixture',
        'dispatch_identity': hashlib.sha256(identity.encode()).hexdigest(),
        'claim_root': claim, 'python': runner.file_pin(Path(sys.executable).resolve()),
        'runner': runner.file_pin(HERE/'runner_v2.py'),
        'child': runner.file_pin(HERE/'synthetic_receiver_child.py'), 'modules': modules,
        'packet': runner.file_pin(packet_path), 'environment': {'LC_ALL': 'C', 'PYTHONHASHSEED': '0'},
        'timeout_seconds': timeout, 'stdout_cap_bytes': stdout_cap,
        'stderr_cap_bytes': stderr_cap, 'fault': fault, 'scientific_execution_authorized': False}
    raw = runner.canonical(scope)
    path = root/'scope.json'
    write_new(path, raw)
    return raw, runner.pin(raw), str(path), claim


def run(arguments):
    raw, expected, path, claim = arguments
    return runner.dispatch(raw, expected, scope_path=path, expected_claim_root=claim)
