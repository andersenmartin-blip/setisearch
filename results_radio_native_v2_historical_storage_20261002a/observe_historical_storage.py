#!/usr/bin/env python3
"""Pinned point-in-time historical observation; no prospective claim or workload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent
SCOPE = 'results_radio_native_v2_compact_control_20261002b'
MANIFEST = 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json'
OLD_SOURCE = SCOPE + '/frozen-code/scripts/radio_native_v2_invocation_spending.py'
COMPONENT = 'scripts/radio_native_v2_historical_storage.py'
COMPONENT_PIN = {'bytes': 21869, 'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'}
BOOTSTRAP_HELPER_PIN = {'bytes': 16210, 'sha256': 'b313aa3cada72d2e4956893b300f1c258a03f8621c54ccb71fab41f13276bea6'}
BOOTSTRAP_LAUNCHER_PIN = {'bytes': 33354, 'sha256': '9bd4bcd55677dea320c7251ec34ce0d941cfbfed5371780dadd1fc8111cd48e3'}
OUTPUT_PREFIX = ''
INPUT_PINS = {
    MANIFEST: {'bytes': 81935, 'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'},
    OLD_SOURCE: {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
    SCOPE + '/activation-receipt.json': {'bytes': 1332, 'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'},
    SCOPE + '/invocation-spending.json': {'bytes': 1018, 'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def value_pin(value):
    raw = canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_held(name, relative, raw):
    module = types.ModuleType(name); module.__file__ = str(ROOT / relative)
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def read_bootstrap(path, expected):
    if not isinstance(expected, dict): raise ValueError('Explicit reviewed bootstrap pin required')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 * 1024**2:
                raise ValueError('Bounded sole-link bootstrap source required')
            chunks = []; remaining = before.st_size + 1
            while remaining:
                part = os.read(fd, min(65536, remaining))
                if not part: break
                chunks.append(part); remaining -= len(part)
            raw = b''.join(chunks); after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if identity(before) != identity(after) or identity(after) != identity(named) or len(raw) != before.st_size:
                raise ValueError('Bootstrap source changed during descriptor read')
            if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != expected:
                raise ValueError('Bootstrap source differs from independently reviewed literal')
            return raw
        finally: os.close(fd)
    finally: os.close(directory)


def write_new(filename, value):
    raw = canonical(value) + b'\n'
    fd = os.open(HERE / (OUTPUT_PREFIX + filename), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        offset = 0
        while offset < len(raw):
            amount = os.write(fd, raw[offset:])
            if amount <= 0: raise OSError('Incomplete exclusive observation write')
            offset += amount
        os.fsync(fd)
    finally: os.close(fd)
    directory = os.open(HERE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    global OUTPUT_PREFIX
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 1000000: raise ValueError('Bounded distinct observation attempt required')
    OUTPUT_PREFIX = '' if args.attempt == 1 else f'observation-attempt-{args.attempt}-'
    helper_path = HERE / 'prepare_snapshot.py'
    helper_raw = read_bootstrap(helper_path, BOOTSTRAP_HELPER_PIN)
    read_bootstrap(ROOT / 'scripts/radio_native_v2_compact_control_launch.py', BOOTSTRAP_LAUNCHER_PIN)
    helper = load_held('historical_observation_preparation_helper',
        str(helper_path.relative_to(ROOT)), helper_raw)
    launcher, _, _, _, bootstrap = helper.bootstrap_exact_environment(BOOTSTRAP_LAUNCHER_PIN)
    if not isinstance(COMPONENT_PIN, dict): raise ValueError('Final reviewed storage component pin required')
    raws = {}
    for path, wanted in {**INPUT_PINS, COMPONENT: COMPONENT_PIN}.items():
        _, raws[path] = launcher.read_pinned(ROOT / path, expected=wanted, maximum=2 * 1024**2, retain=True)
    source = load_held('held_read_only_historical_storage', COMPONENT, raws[COMPONENT])
    old = load_held('held_b_ledger_observer', OLD_SOURCE, raws[OLD_SOURCE])
    original = json.loads(raws[MANIFEST])
    receipt = json.loads(raws[SCOPE + '/activation-receipt.json'])
    witness = json.loads(raws[SCOPE + '/invocation-spending.json'])
    scope = str(ROOT / SCOPE); ledger = str(ROOT / '.radio-native-v2-invocation-ledger')
    if receipt['control_scope'] != scope or witness['ledger_root'] != ledger:
        raise ValueError('Historical scope/ledger differs from immutable public witness')
    expected = {row['path'][len(SCOPE)+1:]: {'bytes': row['bytes'], 'sha256': row['sha256']}
        for row in original['actual_scope_files_retained'] if row['path'].startswith(SCOPE + '/')}
    if len(expected) != 107 or sum(row['bytes'] for row in expected.values()) != 70168047:
        raise ValueError('Exact immutable 107-file historical failure required')
    directories = {'.'}
    for name in expected:
        current = Path(name).parent
        while current.as_posix() != '.':
            directories.add(current.as_posix()); current = current.parent
    if len(directories) != 20: raise ValueError('Exact historical directory ancestry required')
    active = True
    def audit(event, args):
        if not active: return
        if event == 'open':
            flags = args[2]
            if type(flags) is int and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise RuntimeError('Mutation open refused during historical observation')
        if event in ('os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                'os.chmod', 'os.chown', 'os.truncate', 'os.utime', 'subprocess.Popen', 'os.system') or event.startswith('socket.'):
            raise RuntimeError('Mutation or external operation refused during historical observation')
    sys.addaudithook(audit)
    before = old.observe_spend_storage(witness, receipt, execution_scope=scope, ledger_root=ledger)
    rows = []
    for relative in sorted(directories | set(expected)):
        info = (ROOT / SCOPE / relative).lstat()
        directory = relative in directories
        if (directory and not stat.S_ISDIR(info.st_mode)) or (not directory and not stat.S_ISREG(info.st_mode)):
            raise ValueError('Historical public path changed kind')
        row = {'path': relative, 'kind': 'directory' if directory else 'file', 'metadata': source._metadata(info)}
        if not directory: row['raw_pin'] = expected[relative]
        rows.append(row)
    scope_manifest = {'schema': source.MANIFEST_SCHEMA, 'role': 'historical_scope', 'scope': scope, 'rows': rows}
    scope_observation = source.observe_retained_scope(scope, scope_manifest, expected_manifest_pin=value_pin(scope_manifest))
    ledger_rows = []
    for row in before['rows']:
        value = {'path': '.' if row['kind'] == 'directory' else witness['record_name'],
            'kind': row['kind'], 'metadata': {field: row[field] for field in source.METADATA_FIELDS}}
        if row['kind'] == 'file':
            value['raw_pin'] = {'bytes': row['bytes'], 'sha256': witness['record_sha256']}
        ledger_rows.append(value)
    ledger_manifest = {'schema': source.MANIFEST_SCHEMA, 'role': 'historical_ledger', 'scope': ledger,
        'rows': sorted(ledger_rows, key=lambda row: row['path'])}
    ledger_observation = source.observe_retained_scope(ledger, ledger_manifest,
        expected_manifest_pin=value_pin(ledger_manifest))
    after = old.observe_spend_storage(witness, receipt, execution_scope=scope, ledger_root=ledger)
    if before != after: raise ValueError('Historical spend observation changed')
    if {row['path']: {field: row[field] for field in source.METADATA_FIELDS} for row in ledger_observation['rows']} != {
            row['path']: {field: row[field] for field in source.METADATA_FIELDS} for row in before['rows']}:
        raise ValueError('Held historical ledger observers disagree')
    # Recheck the complete observed scope once more; this is a current snapshot,
    # not a claim to observe a future workload or freeze the operating kernel.
    if source.observe_retained_scope(scope, scope_manifest, expected_manifest_pin=value_pin(scope_manifest)) != scope_observation:
        raise ValueError('Historical scope changed between independent reads')
    active = False
    output_pins = {
        'historical-scope-manifest.json': write_new('historical-scope-manifest.json', scope_manifest),
        'historical-scope-observation.json': write_new('historical-scope-observation.json', scope_observation),
        'historical-ledger-manifest.json': write_new('historical-ledger-manifest.json', ledger_manifest),
        'historical-ledger-observation.json': write_new('historical-ledger-observation.json', ledger_observation),
        'historical-ledger-spend-observation.json': write_new('historical-ledger-spend-observation.json', after),
    }
    output_pins = {OUTPUT_PREFIX + name: pin for name, pin in output_pins.items()}
    result = {'schema': 'radio-native-v2-historical-storage-real-observation-preparation-v1',
        'attempt': args.attempt, 'bootstrap_source_literals_verified_before_exec': True,
        'bootstrap_helper_pin': BOOTSTRAP_HELPER_PIN, 'bootstrap_launcher_pin': BOOTSTRAP_LAUNCHER_PIN,
        'status': 'HISTORICAL_STORAGE_VERIFIED_PREPARATION_ONLY', 'public_input_commit': '1468a19d2603bde2b491b5400a2d3cdf8954c69f',
        'scope_files': 107, 'scope_entries': scope_observation['entry_count'],
        'scope_file_raw_bytes_verified': sum(row['raw_pin']['bytes'] for row in scope_observation['rows'] if row['kind'] == 'file'),
        'scope_logical_bytes': scope_observation['logical_bytes'], 'scope_allocated_bytes': scope_observation['allocated_bytes'],
        'historical_ledger_logical_bytes': ledger_observation['logical_bytes'],
        'historical_ledger_allocated_bytes': ledger_observation['allocated_bytes'],
        'ledger_spend_witness_and_storage_matched': True, 'two_complete_scope_reads_match': True,
        'read_only_audit_guard_active_during_observation': True, 'output_raw_pins': output_pins,
        'bootstrap': bootstrap, 'component_pin': COMPONENT_PIN, 'input_raw_pins': INPUT_PINS,
        'new_project_marker_created': False, 'new_project_ledger_or_claim_created': False,
        'protected_control_invocations': 0, 'new_source_generation': False, 'telescope_reads': 0,
        'scientific_cases_run': 0, 'rng_draws': 0, 'execution_authorized': False,
        'future_lifetime_accounting_proved': False,
        'scope_raw_reads_are_retained_engineering_outputs_and_evidence': True,
        'trust_boundary': 'Public immutable file pins and freshly captured directory metadata; local kernel/filesystem. Access times excluded.'}
    write_new('observation-result.json', result)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
