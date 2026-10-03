#!/usr/bin/env python3
"""Run held production observer read-only; expected original identities refuse.

The caller supplies the exact observer byte pin independently. Current captured
metadata is preparation evidence; no restored inode can replace a spend witness.
No consumption, protected control, marker, runtime freeze or publication occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
SELF = 'scripts/radio_native_v2_historical_observation.py'
READ_PHASE = False
DENIED = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def audit(event, args):
    if not READ_PHASE: return
    mutation = {'os.remove', 'os.unlink', 'os.rename', 'os.mkdir', 'os.rmdir',
        'os.link', 'os.symlink', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate',
        'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.system'}
    refused = event in mutation or event.startswith(('subprocess.', 'socket.'))
    if event == 'open' and len(args) >= 3:
        refused |= bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if refused:
        DENIED.append(event)
        raise RuntimeError('Read-only production adapter audit denied ' + event)


def held_observer(expected):
    fd = os.open(ROOT / SELF, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Sole-link observer source required')
        blocks = []
        while True:
            block = os.read(fd, 65536)
            if not block: break
            blocks.append(block)
        raw = b''.join(blocks)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(os.fstat(fd)) or raw_pin(raw) != expected:
            raise ValueError('Observer differs from independent selected byte pin')
    finally:
        os.close(fd)
    module = types.SimpleNamespace(__name__='held_actual_refusal_observer', __file__=str(ROOT / SELF))
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def run():
    global READ_PHASE
    parser = argparse.ArgumentParser()
    parser.add_argument('--observer-bytes', required=True, type=int)
    parser.add_argument('--observer-sha256', required=True)
    args = parser.parse_args()
    if not 0 < args.observer_bytes <= 2 * 1024**2 or not re.fullmatch('[a-f0-9]{64}', args.observer_sha256):
        raise ValueError('Exact bounded selected observer byte pin required')
    expected = {'bytes': args.observer_bytes, 'sha256': args.observer_sha256}
    sys.addaudithook(audit)
    READ_PHASE = True
    try:
        history = held_observer(expected)
        root = history.ORIGINAL_REPOSITORY_ROOT
        if str(ROOT) != root: raise ValueError('Exact independent original repository required')
        scope = root + '/results_radio_native_v2_compact_control_20261003d'
        plan = {'invocation_repository_root': root,
            'invocation_ledger_root': root + history.PROSPECTIVE_LEDGER_DIRECTORY,
            'historical_storage_original_identity_continuity_qualified': False,
            'retained_storage_component_roles': history.JOINT_HISTORY_COMPONENT_ROLES,
            'historical_storage_inputs': history.HISTORICAL_INPUT_PINS,
            'code_files': {**history.HISTORICAL_INPUT_PINS,
                history.STORAGE_SOURCE: history.STORAGE_IMPLEMENTATION_PIN}}
        freeze = {'input_sha256s': {relative: pin['sha256'] for relative, pin in history.HISTORICAL_INPUT_PINS.items()}}
        history.validate_contract(plan, freeze, repository_root=root, execution_scope=scope)
        failures = {}
        try:
            history.observe_historical_storage(root, plan=plan, freeze=freeze,
                repository_root=root, execution_scope=scope)
        except ValueError as error:
            failures['b'] = {'error_type': type(error).__name__, 'error': str(error)}
        context = {}
        for relative, pin in history.HISTORICAL_INPUT_PINS.items():
            if relative in (history.OLD_SOURCE, history.C_SOURCE): continue
            raw = history.read_raw(root + '/' + relative, pin)
            value = json.loads(raw)
            if canonical(value) + b'\n' != raw: raise ValueError('Canonical independent input required')
            context[relative] = value
        storage = history._module(root, history.STORAGE_SOURCE, history.STORAGE_IMPLEMENTATION_PIN)
        try:
            history._observe_c(storage, root, context)
        except ValueError as error:
            failures['c'] = {'error_type': type(error).__name__, 'error': str(error)}
        if set(failures) != {'b', 'c'} or any(row['error'] != 'Invocation ledger directory identity changed' for row in failures.values()):
            raise ValueError('Exact original b/c live identity refusal expected; got ' + repr(failures))
        result = {'schema': 'radio-native-v2-production-original-history-refusal-v1',
            'status': 'EXPECTED_BLOCKED_IDENTITY_REFUSALS_VERIFIED',
            'selected_observer_raw_pin': expected,
            'historical_input_count': len(history.HISTORICAL_INPUT_PINS),
            'historical_input_map_sha256': history.HISTORICAL_INPUT_MAP_SHA256,
            'shared_storage_source_raw_pin': history.STORAGE_IMPLEMENTATION_PIN,
            'complete_c_closure_directory_contract_checked_before_refusal': True,
            'failures': failures,
            'read_only_audit_denied_events': DENIED,
            'original_witnesses_unchanged': True,
            'original_identity_continuity_qualified': False,
            'historical_ledger_rebinding_authorized': False,
            'future_d_marker_ledger_scope_created': False,
            'protected_control_invocations': 0, 'new_spends': 0,
            'telescope_reads': 0, 'scientific_execution_authorized': False,
            'execution_authorized': False,
            'limitations': ['Current point-time restored content inventory does not authenticate original inode/ctime continuity.',
                'Held original spenders still refuse their untouched original witnesses before returning a storage join.',
                'No continuous custody, resource lifetime, activation, native or scientific qualification is established.']}
        return result
    finally:
        READ_PHASE = False


if __name__ == '__main__':
    print(canonical(run()).decode())
