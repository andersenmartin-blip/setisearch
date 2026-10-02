#!/usr/bin/env python3
"""Authenticated live historical accounting inside the material c control.

This adapter reads mandatory copied, independently pinned historical metadata;
its b observer and shared storage implementation execute only held source bytes
from the checked material code root. Every call reobserves the original failed
scope and original one-record b journal. It writes nothing, consumes nothing,
and does not import repository source from the ambient Python import path.

The original root and historical input literals derive from the retained public
b package and hardened point-in-time preparation. They are not refreshable
configuration. A plan, receipt or relocated code root cannot select other history.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types

SELF = 'scripts/radio_native_v2_historical_observation.py'
STORAGE_SOURCE = 'scripts/radio_native_v2_historical_storage.py'
STORAGE_IMPLEMENTATION_PIN = {'bytes': 21869, 'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'}
ORIGINAL_REPOSITORY_ROOT = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
HISTORICAL_SCOPE = ORIGINAL_REPOSITORY_ROOT + '/results_radio_native_v2_compact_control_20261002b'
HISTORICAL_LEDGER = ORIGINAL_REPOSITORY_ROOT + '/.radio-native-v2-invocation-ledger'
OLD_SOURCE = 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py'
OLD_RECEIPT = 'results_radio_native_v2_compact_control_20261002b/activation-receipt.json'
OLD_WITNESS = 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json'
PUBLIC_MANIFEST = 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json'
HISTORY_PREFIX = 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-'
HISTORICAL_INPUT_PINS = {'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332, 'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'}, 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'}, 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018, 'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778, 'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200, 'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293, 'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900, 'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112, 'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'}, 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935, 'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'}}
INPUT_PATHS = tuple(sorted(HISTORICAL_INPUT_PINS))
HISTORICAL_INPUT_MAP_SHA256 = hashlib.sha256(json.dumps(HISTORICAL_INPUT_PINS, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
MAX_BYTES = 2 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def value_pin(value):
    raw = canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def absolute(value):
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or len(value.encode()) > 4096 or len(value.split('/')) > 64
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Bounded canonical absolute historical accounting path required')
    return value


def validate_root(plan, repository_root, execution_scope=None):
    root = absolute(repository_root)
    if root != ORIGINAL_REPOSITORY_ROOT or plan.get('invocation_repository_root') != root:
        raise ValueError('Exact independently authenticated original historical repository root required')
    if plan.get('invocation_ledger_root') != root + '/.radio-native-v2-invocation-ledger-20261002c':
        raise ValueError('Exact separate prospective c invocation ledger required')
    if execution_scope is not None:
        scope = absolute(execution_scope)
        if not scope.startswith(root + '/'):
            raise ValueError('Current control scope must be within the independently authenticated original root')
    return root


def validate_contract(plan, freeze, *, repository_root, execution_scope):
    root = validate_root(plan, repository_root, execution_scope)
    if plan.get('historical_storage_inputs') != HISTORICAL_INPUT_PINS:
        raise ValueError('Exact mandatory independently pinned historical storage inputs required')
    for relative, expected in HISTORICAL_INPUT_PINS.items():
        if (freeze.get('input_sha256s', {}).get(relative) != expected['sha256']
                or plan.get('code_files', {}).get(relative) != expected):
            raise ValueError('Complete freeze and material tree must bind every historical input: ' + relative)
    if plan.get('code_files', {}).get(STORAGE_SOURCE) != STORAGE_IMPLEMENTATION_PIN:
        raise ValueError('Shared historical storage source differs from independent implementation pin')
    return root


def _ancestor(info):
    if not stat.S_ISDIR(info.st_mode): raise ValueError('Ordinary nofollow history ancestor required')
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def read_raw(path, expected):
    path = absolute(path)
    if (type(expected) is not dict or set(expected) != {'bytes', 'sha256'}
            or type(expected['bytes']) is not int or not 0 < expected['bytes'] <= MAX_BYTES
            or type(expected['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', expected['sha256'])):
        raise ValueError('Exact bounded independent historical raw-file pin required')
    opened = []; chain = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW); opened.append(fd)
        chain.append((fd, None, None, _ancestor(os.fstat(fd))))
        for name in path[1:].split('/')[:-1]:
            parent = fd; named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            identity = _ancestor(named)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent); opened.append(fd)
            if _ancestor(os.fstat(fd)) != identity: raise ValueError('History ancestor changed during open')
            chain.append((fd, parent, name, identity))
        name = Path(path).name; parent = fd
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent); opened.append(fd)
        before = os.fstat(fd)
        key = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected['bytes']:
            raise ValueError('Exact stable sole-link historical input required')
        blocks = []; remaining = before.st_size + 1
        while remaining:
            block = os.read(fd, min(65536, remaining))
            if not block: break
            blocks.append(block); remaining -= len(block)
        raw = b''.join(blocks)
        if (key(before) != key(os.fstat(fd)) or key(before) != key(os.stat(name, dir_fd=parent, follow_symlinks=False))
                or len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']):
            raise ValueError('Historical input differs from independent raw pin or changed during read')
        for held, ancestor_parent, ancestor_name, identity in chain:
            if (_ancestor(os.fstat(held)) != identity
                    or (ancestor_parent is not None and _ancestor(os.stat(ancestor_name, dir_fd=ancestor_parent, follow_symlinks=False)) != identity)):
                raise ValueError('Historical ancestor binding changed during read')
        return raw
    finally:
        for held in reversed(opened): os.close(held)


def _module(code_root, relative, expected):
    raw = read_raw(str(Path(code_root) / relative), expected)
    module = types.SimpleNamespace(__name__='held_historical_accounting_component', __file__=str(Path(code_root) / relative))
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def observe_historical_storage(code_root, *, plan, freeze, repository_root, execution_scope):
    """Authenticate copied historical inputs and reobserve b without any spend."""
    validate_contract(plan, freeze, repository_root=repository_root, execution_scope=execution_scope)
    code_root = absolute(code_root)
    storage = _module(code_root, STORAGE_SOURCE, STORAGE_IMPLEMENTATION_PIN)
    old = _module(code_root, OLD_SOURCE, HISTORICAL_INPUT_PINS[OLD_SOURCE])
    context = {}
    for relative, expected in HISTORICAL_INPUT_PINS.items():
        if relative == OLD_SOURCE: continue
        raw = read_raw(code_root + '/' + relative, expected)
        value = json.loads(raw)
        if type(value) is not dict or canonical(value) + b'\n' != raw:
            raise ValueError('Exact canonical copied historical JSON input required')
        context[relative] = value
    receipt = context[OLD_RECEIPT]; witness = context[OLD_WITNESS]
    if receipt.get('control_scope') != HISTORICAL_SCOPE or witness.get('ledger_root') != HISTORICAL_LEDGER:
        raise ValueError('Historical receipt/witness scope or journal differs from authenticated original root')
    scope_manifest = context[HISTORY_PREFIX + 'historical-scope-manifest.json']
    ledger_manifest = context[HISTORY_PREFIX + 'historical-ledger-manifest.json']
    if (scope_manifest.get('scope') != HISTORICAL_SCOPE or scope_manifest.get('role') != 'historical_scope'
            or ledger_manifest.get('scope') != HISTORICAL_LEDGER or ledger_manifest.get('role') != 'historical_ledger'):
        raise ValueError('Authenticated historical manifests must bind exact original scope and b journal')
    published = context[PUBLIC_MANIFEST]['actual_scope_files_retained']
    expected_files = {row['path'][len('results_radio_native_v2_compact_control_20261002b/') :]:
        {'bytes': row['bytes'], 'sha256': row['sha256']} for row in published
        if row['path'].startswith('results_radio_native_v2_compact_control_20261002b/')}
    manifested = {row['path']: row['raw_pin'] for row in scope_manifest['rows'] if row['kind'] == 'file'}
    if manifested != expected_files or len(manifested) != 107 or sum(row['bytes'] for row in manifested.values()) != 70168047:
        raise ValueError('Complete exact public historical 107-file inventory required')
    before = old.observe_spend_storage(witness, receipt, execution_scope=HISTORICAL_SCOPE, ledger_root=HISTORICAL_LEDGER)
    scope_observation = storage.observe_retained_scope(HISTORICAL_SCOPE, scope_manifest,
        expected_manifest_pin=value_pin(scope_manifest))
    ledger_observation = storage.observe_retained_scope(HISTORICAL_LEDGER, ledger_manifest,
        expected_manifest_pin=value_pin(ledger_manifest))
    after = old.observe_spend_storage(witness, receipt, execution_scope=HISTORICAL_SCOPE, ledger_root=HISTORICAL_LEDGER)
    if before != after or after != context[HISTORY_PREFIX + 'historical-ledger-spend-observation.json']:
        raise ValueError('Historical b spend/storage changed since authenticated retained observation')
    if (scope_observation != context[HISTORY_PREFIX + 'historical-scope-observation.json']
            or ledger_observation != context[HISTORY_PREFIX + 'historical-ledger-observation.json']):
        raise ValueError('Historical scope or b journal changed since authenticated retained observation')
    return storage, scope_observation, ledger_observation


def observe_joined_storage(code_root, *, plan, freeze, repository_root, execution_scope, prospective_ledger):
    """Every call live-authenticates all mandatory historical rows and the c scope."""
    root = validate_root(plan, repository_root, execution_scope)
    if (prospective_ledger.get('control_scope') != execution_scope
            or prospective_ledger.get('ledger_root') != plan.get('invocation_ledger_root')):
        raise ValueError('Authenticated prospective ledger must bind current control scope and exact c root')
    storage, historical_scope, historical_ledger = observe_historical_storage(code_root,
        plan=plan, freeze=freeze, repository_root=root, execution_scope=execution_scope)
    inventories = {'historical_scope': historical_scope, 'historical_ledger': historical_ledger,
        'prospective_ledger': prospective_ledger}
    joined = storage.join_historical_storage(historical_scope, historical_ledger, prospective_ledger,
        expected_observation_pins={name: value_pin(value) for name, value in inventories.items()})
    joined['current_control_scope'] = execution_scope
    return joined
