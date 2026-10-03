#!/usr/bin/env python3
"""Authenticated live b/c historical accounting inside a future material d control.

This adapter reads mandatory copied, independently pinned historical metadata;
its b/c observers and shared storage implementation execute only held source bytes
from the checked material code root. Every call reobserves the original failed
b/c scopes and both original one-record spent journals. It writes nothing, consumes nothing,
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
STORAGE_IMPLEMENTATION_PIN = {'bytes': 25274, 'sha256': '9f709c42ad726732b9da98d2b830a9905e6d3ae90f3a8ba1f49482d11db299d5'}
ORIGINAL_REPOSITORY_ROOT = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
HISTORICAL_SCOPE = ORIGINAL_REPOSITORY_ROOT + '/results_radio_native_v2_compact_control_20261002b'
HISTORICAL_LEDGER = ORIGINAL_REPOSITORY_ROOT + '/.radio-native-v2-invocation-ledger'
HISTORICAL_C_SCOPE = ORIGINAL_REPOSITORY_ROOT + '/results_radio_native_v2_compact_control_20261002c'
HISTORICAL_C_LEDGER = ORIGINAL_REPOSITORY_ROOT + '/.radio-native-v2-invocation-ledger-20261002c'
PROSPECTIVE_LEDGER_DIRECTORY = '/.radio-native-v2-invocation-ledger-20261003d'
JOINT_HISTORY_COMPONENT_ROLES = {
    'historical_b_scope': 'historical_scope',
    'historical_b_ledger': 'historical_ledger',
    'historical_c_scope': 'historical_scope',
    'historical_c_ledger': 'historical_ledger',
    'prospective_ledger': 'prospective_ledger'}
C_SOURCE = 'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py'
C_RECEIPT = 'results_radio_native_v2_compact_control_20261002c/activation-receipt.json'
C_WITNESS = 'results_radio_native_v2_compact_control_20261002c/invocation-spending.json'
C_PUBLIC_MANIFEST = 'results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json'
C_TERMINAL_INVENTORY = 'results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json'
C_ORIGINAL_LEDGER_REVIEW = 'results_radio_native_v2_control_activation_20261002c/independent-terminal-ledger-review.json'
C_HISTORY_PREFIX = 'results_radio_native_v2_joint_history_20261003a/observation-c-'
OLD_SOURCE = 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py'
OLD_RECEIPT = 'results_radio_native_v2_compact_control_20261002b/activation-receipt.json'
OLD_WITNESS = 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json'
PUBLIC_MANIFEST = 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json'
HISTORY_PREFIX = 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-'
HISTORICAL_INPUT_PINS = {'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332, 'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'}, 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'}, 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018, 'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'}, 'results_radio_native_v2_compact_control_20261002c/activation-receipt.json': {'bytes': 1332, 'sha256': '0ebcfb6cc50183ef4635cf30c1e45a403dfc2f2334c98f939f7bfd5cbb498c85'}, 'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py': {'bytes': 22296, 'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'}, 'results_radio_native_v2_compact_control_20261002c/invocation-spending.json': {'bytes': 1028, 'sha256': '647b91d67c73065399481ba1759e70775b65fc166551391699e617230b75af80'}, 'results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json': {'bytes': 22816, 'sha256': 'c078c571ab0e57ed766b89dc0ebe2c9f8b2ef8720ccc05e174a9f1a82cf73827'}, 'results_radio_native_v2_control_activation_20261002c/independent-terminal-ledger-review.json': {'bytes': 9666, 'sha256': 'b430b7ec8830c733e15e5839a3b281b184281f909615fbbe33b26945a89390c7'}, 'results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json': {'bytes': 23482, 'sha256': '98bcb0f744aa1fbdb69623e792b08c97fb0dbbc52723d946c8b76b33ae1143dc'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778, 'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200, 'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293, 'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900, 'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112, 'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-ledger-manifest.json': {'bytes': 790, 'sha256': 'a746a35cccb7260c98042a01dbe0f292c6bb42276da82886bdcaa4875b96eb83'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-ledger-observation.json': {'bytes': 1232, 'sha256': '32d2c66d6d1f22d35b8be168e12e8f3d9bb994014d0f2d00e5776cb12d9b6aca'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-scope-manifest.json': {'bytes': 29691, 'sha256': '31952c81f8e555539f58722282f15960ff223efdb208d5a2f134430c0a579427'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-scope-observation.json': {'bytes': 38328, 'sha256': '68e820920f2f636b8bff1f12f8ccf61eb558a8329c08a6245a38ddd837957e04'}, 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935, 'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'}}
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
    if plan.get('invocation_ledger_root') != root + PROSPECTIVE_LEDGER_DIRECTORY:
        raise ValueError('Exact separate prospective d invocation ledger required')
    if execution_scope is not None:
        scope = absolute(execution_scope)
        if not scope.startswith(root + '/'):
            raise ValueError('Current control scope must be within the independently authenticated original root')
        for retained in (HISTORICAL_SCOPE, HISTORICAL_LEDGER, HISTORICAL_C_SCOPE, HISTORICAL_C_LEDGER):
            if scope == retained or scope.startswith(retained + '/') or retained.startswith(scope + '/'):
                raise ValueError('Current control scope cannot overlap permanently spent historical scope or journal')
    return root


def validate_contract(plan, freeze, *, repository_root, execution_scope):
    root = validate_root(plan, repository_root, execution_scope)
    if plan.get('historical_storage_original_identity_continuity_qualified') is not False:
        raise ValueError('Historical original identity continuity remains unqualified')
    if plan.get('retained_storage_component_roles') != JOINT_HISTORY_COMPONENT_ROLES:
        raise ValueError('Exact complete mandatory b/c historical and prospective storage component roles required')
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
    """Authenticate copied historical inputs and reobserve b/c without any spend."""
    validate_contract(plan, freeze, repository_root=repository_root, execution_scope=execution_scope)
    code_root = absolute(code_root)
    storage = _module(code_root, STORAGE_SOURCE, STORAGE_IMPLEMENTATION_PIN)
    old = _module(code_root, OLD_SOURCE, HISTORICAL_INPUT_PINS[OLD_SOURCE])
    context = {}
    for relative, expected in HISTORICAL_INPUT_PINS.items():
        if relative in (OLD_SOURCE, C_SOURCE): continue
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
    components = {'historical_b_scope': scope_observation, 'historical_b_ledger': ledger_observation}
    components.update(_observe_c(storage, code_root, context))
    return storage, components


def _observe_c(storage, code_root, context):
    old = _module(code_root, C_SOURCE, HISTORICAL_INPUT_PINS[C_SOURCE])
    receipt = context[C_RECEIPT]; witness = context[C_WITNESS]
    if receipt.get('control_scope') != HISTORICAL_C_SCOPE or witness.get('ledger_root') != HISTORICAL_C_LEDGER:
        raise ValueError('Historical c receipt/witness scope or journal differs from authenticated original root')
    scope_manifest = context[C_HISTORY_PREFIX + 'scope-manifest.json']
    ledger_manifest = context[C_HISTORY_PREFIX + 'ledger-manifest.json']
    if (scope_manifest.get('scope') != HISTORICAL_C_SCOPE or scope_manifest.get('role') != 'historical_scope'
            or ledger_manifest.get('scope') != HISTORICAL_C_LEDGER or ledger_manifest.get('role') != 'historical_ledger'):
        raise ValueError('Authenticated historical manifests must bind exact original c scope and spent c journal')
    publication = context[C_PUBLIC_MANIFEST]; terminal = context[C_TERMINAL_INVENTORY]
    if (publication.get('status') != 'CLOSED_FAILED' or publication.get('permanently_spent') is not True
            or publication.get('completed_engineering_cases') != 0
            or publication.get('all_68_terminal_scope_files_included') is not True
            or terminal.get('status') != 'CLOSED_FAILED'
            or terminal.get('all_eight_case_directories_empty') is not True
            or terminal.get('file_count') != 68 or terminal.get('directory_count') != 21):
        raise ValueError('Exact permanently failed public c closure and terminal inventory required')
    prefix = 'results_radio_native_v2_compact_control_20261002c/'
    expected_files = {row['path'][len(prefix):]: {'bytes': row['bytes'], 'sha256': row['sha256']}
        for row in publication['files'] if row['path'].startswith(prefix)}
    terminal_files = {row['path'][len(prefix):]: {'bytes': row['bytes'], 'sha256': row['sha256']}
        for row in terminal['files'] if row['path'].startswith(prefix)}
    manifested = {row['path']: row['raw_pin'] for row in scope_manifest['rows'] if row['kind'] == 'file'}
    if (manifested != expected_files or terminal_files != expected_files or len(manifested) != 68
            or sum(row['bytes'] for row in manifested.values()) != 3853729):
        raise ValueError('Complete exact public historical c 68-file inventory required')
    terminal_dirs = {'.' if row['path'] == prefix[:-1] else row['path'][len(prefix):]
        for row in terminal['directories']}
    manifested_dirs = {row['path'] for row in scope_manifest['rows'] if row['kind'] == 'directory'}
    empty_cases = {'cases/case%02d' % ordinal for ordinal in range(8)}
    if (manifested_dirs != terminal_dirs or len(manifested_dirs) != 21
            or not empty_cases.issubset(manifested_dirs)
            or any(path.startswith(case + '/') for case in empty_cases for path in manifested)):
        raise ValueError('Exact historical c directories including eight retained empty cases required')
    arguments = {'execution_scope': HISTORICAL_C_SCOPE, 'ledger_root': HISTORICAL_C_LEDGER,
        'repository_root': ORIGINAL_REPOSITORY_ROOT}
    before = old.observe_spend_storage(witness, receipt, **arguments)
    scope_observation = storage.observe_retained_scope(HISTORICAL_C_SCOPE, scope_manifest,
        expected_manifest_pin=value_pin(scope_manifest))
    ledger_observation = storage.observe_retained_scope(HISTORICAL_C_LEDGER, ledger_manifest,
        expected_manifest_pin=value_pin(ledger_manifest))
    after = old.observe_spend_storage(witness, receipt, **arguments)
    # The archived original observation is evidence, not replacement authority.
    # Restored inode/ctime identities currently differ from the original witness.
    # The held original spender must still verify its untouched witness; this
    # adapter cannot rebind historical identity or make that restoration pass.
    expected_spend = context[C_ORIGINAL_LEDGER_REVIEW]['actual_c_ledger']
    if before != after or after != expected_spend:
        raise ValueError('Historical c spend/storage changed since authenticated retained observation')
    if (scope_observation != context[C_HISTORY_PREFIX + 'scope-observation.json']
            or ledger_observation != context[C_HISTORY_PREFIX + 'ledger-observation.json']):
        raise ValueError('Historical c scope or journal changed since authenticated retained observation')
    return {'historical_c_scope': scope_observation, 'historical_c_ledger': ledger_observation}


def observe_joined_storage(code_root, *, plan, freeze, repository_root, execution_scope, prospective_ledger):
    """Live-authenticate both spent scopes/journals plus the current d journal."""
    root = validate_root(plan, repository_root, execution_scope)
    if (prospective_ledger.get('control_scope') != execution_scope
            or prospective_ledger.get('ledger_root') != plan.get('invocation_ledger_root')):
        raise ValueError('Authenticated prospective ledger must bind current control scope and exact d root')
    storage, components = observe_historical_storage(code_root,
        plan=plan, freeze=freeze, repository_root=root, execution_scope=execution_scope)
    components['prospective_ledger'] = prospective_ledger
    joined = storage.join_retained_storage_components(components,
        expected_observation_pins={name: value_pin(value) for name, value in components.items()},
        expected_component_roles=JOINT_HISTORY_COMPONENT_ROLES)
    joined['current_control_scope'] = execution_scope
    return joined
