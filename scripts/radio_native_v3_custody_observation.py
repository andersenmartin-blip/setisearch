#!/usr/bin/env python3
"""Current-lifetime custody accounting for a separately reviewed v3 successor.

The trusted, versioned caller supplies the current repository root independently
of the plan and observations. This adapter only authenticates the nineteen fixed
archival metadata files in two disjoint current copy roots, their complete directories, and a
separately authenticated current ledger observation. It never opens the lost
original root, executes an archived spender, rearms old identities, consumes a
claim, generates inputs, launches work, or reads telescope data.

Matching archival bytes authenticate metadata copies, not original inode custody
or missing historical storage. Each copy root has exact directory/file membership;
the surrounding historical workload trees are not scanned. Directory allocation
is charged; those historical trees are outside this new current lifetime.
The root must be authenticated by the outer source/plan/preread/claim chain;
self-consistency of a caller-supplied plan alone is not authentication.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types

SELF = 'scripts/radio_native_v3_custody_observation.py'
ORIGINAL_REPOSITORY_ROOT = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
CURRENT_LEDGER_DIRECTORY = '.radio-native-v3-invocation-ledger-20261003e'
PROSPECTIVE_LEDGER_DIRECTORY = '/' + CURRENT_LEDGER_DIRECTORY
RETAINED_COMPONENT_ROLES = {
    'archive_b_metadata_copy': 'archive_b_metadata_copy',
    'archive_c_metadata_copy': 'archive_c_metadata_copy',
    'current_ledger': 'prospective_ledger',
    'current_claim': 'current_claim_metadata',
}
JOINT_HISTORY_COMPONENT_ROLES = RETAINED_COMPONENT_ROLES
# Immutable public a/b/c tombstones copied from the retained v2 spender.
SPENT_ACTIVATIONS = (
    ('radio-native-v2-control-activation-transition-20261002a',
        'config/radio_native_v2_control_activation_20261002a.activate.json',
        'ba1b6c918931a02a84cd23e0e14057bd9f700e40'),
    ('radio-native-v2-control-activation-transition-20261002b',
        'config/radio_native_v2_control_activation_20261002b.activate.json',
        '1bc31d49b2552de10c3fbabb7bc106618a44a241'),
    ('radio-native-v2-control-activation-transition-20261002c',
        'config/radio_native_v2_control_activation_20261002c.activate.json',
        'f514d782a0f807223e4bc47cb0b330b4b46a198f'))
# d was preparation only: its namespace and paths are retired, without inventing
# an activation commit, historical spend, or proof that a d invocation occurred.
RETIRED_PREPARATION_IDENTITIES = (
    ('radio-native-v2-control-activation-transition-20261003d',
        'config/radio_native_v2_control_activation_20261003d.activate.json'),)
HISTORICAL_RELATIVE_ROOTS = (
    'results_radio_native_v2_one_control_20261002a',
    'results_radio_native_v2_compact_control_20261002a',
    'results_radio_native_v2_compact_control_20261002b',
    'results_radio_native_v2_compact_control_20261002c',
    'results_radio_native_v2_compact_control_20261003d',
    '.radio-native-v2-invocation-ledger',
    '.radio-native-v2-invocation-ledger-20261002a',
    '.radio-native-v2-invocation-ledger-20261002b',
    '.radio-native-v2-invocation-ledger-20261002c',
    '.radio-native-v2-invocation-ledger-20261003d')
ARCHIVAL_SOURCE_PINS = {'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332, 'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'}, 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'}, 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018, 'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'}, 'results_radio_native_v2_compact_control_20261002c/activation-receipt.json': {'bytes': 1332, 'sha256': '0ebcfb6cc50183ef4635cf30c1e45a403dfc2f2334c98f939f7bfd5cbb498c85'}, 'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py': {'bytes': 22296, 'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'}, 'results_radio_native_v2_compact_control_20261002c/invocation-spending.json': {'bytes': 1028, 'sha256': '647b91d67c73065399481ba1759e70775b65fc166551391699e617230b75af80'}, 'results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json': {'bytes': 22816, 'sha256': 'c078c571ab0e57ed766b89dc0ebe2c9f8b2ef8720ccc05e174a9f1a82cf73827'}, 'results_radio_native_v2_control_activation_20261002c/independent-terminal-ledger-review.json': {'bytes': 9666, 'sha256': 'b430b7ec8830c733e15e5839a3b281b184281f909615fbbe33b26945a89390c7'}, 'results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json': {'bytes': 23482, 'sha256': '98bcb0f744aa1fbdb69623e792b08c97fb0dbbc52723d946c8b76b33ae1143dc'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778, 'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200, 'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293, 'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900, 'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'}, 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112, 'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-ledger-manifest.json': {'bytes': 790, 'sha256': 'a746a35cccb7260c98042a01dbe0f292c6bb42276da82886bdcaa4875b96eb83'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-ledger-observation.json': {'bytes': 1232, 'sha256': '32d2c66d6d1f22d35b8be168e12e8f3d9bb994014d0f2d00e5776cb12d9b6aca'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-scope-manifest.json': {'bytes': 29691, 'sha256': '31952c81f8e555539f58722282f15960ff223efdb208d5a2f134430c0a579427'}, 'results_radio_native_v2_joint_history_20261003a/observation-c-scope-observation.json': {'bytes': 38328, 'sha256': '68e820920f2f636b8bff1f12f8ccf61eb558a8329c08a6245a38ddd837957e04'}, 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935, 'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'}}
ARCHIVAL_COPY_PREFIX = 'results_radio_native_v3_portable_custody_20261003a'
ARCHIVAL_COPY_ROOTS = {
    'archive_b_metadata_copy': ARCHIVAL_COPY_PREFIX + '/archival-b-metadata',
    'archive_c_metadata_copy': ARCHIVAL_COPY_PREFIX + '/archival-c-metadata',
}
SOURCE_TO_CURRENT_COPY = {
    relative: ARCHIVAL_COPY_ROOTS['archive_c_metadata_copy' if ('20261002c' in relative
        or relative.startswith('results_radio_native_v2_joint_history_20261003a/'))
        else 'archive_b_metadata_copy'] + '/' + relative
    for relative in ARCHIVAL_SOURCE_PINS}
ARCHIVAL_INPUT_PINS = {SOURCE_TO_CURRENT_COPY[relative]: dict(pin)
    for relative, pin in ARCHIVAL_SOURCE_PINS.items()}
HISTORICAL_INPUT_PINS = ARCHIVAL_INPUT_PINS
INPUT_PATHS = tuple(sorted(ARCHIVAL_INPUT_PINS))
HISTORICAL_INPUT_MAP_SHA256 = hashlib.sha256(json.dumps(ARCHIVAL_INPUT_PINS,
    sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
ARCHIVAL_INPUT_MAP_SHA256 = HISTORICAL_INPUT_MAP_SHA256
MAX_BYTES = 2 * 1024**2
MAX_ENTRIES = 32768
MAX_STORAGE_BYTES = 1536 * 1024**2
METADATA_FIELDS = frozenset(('device', 'inode', 'mode', 'nlink', 'uid', 'gid',
    'bytes', 'allocated_bytes', 'mtime_ns', 'ctime_ns'))
ARCHIVE_SCHEMA = 'radio-native-v3-current-archive-metadata-observation-v1'
JOIN_SCHEMA = 'radio-native-v3-current-retained-storage-join-v1'
LEDGER_STORAGE_SCHEMA = 'radio-native-v3-control-invocation-spend-storage-v1'
CURRENT_PUBLIC_CLAIM_PATH = 'results_radio_native_v3_predispatch_20261003e/public-spending-envelope.json'
CURRENT_LAUNCH_CONFIG_PATH = 'results_radio_native_v3_predispatch_20261003e/launch-config.json'
CURRENT_OBSERVER_CAPSULE_PATH = 'results_radio_native_v3_predispatch_20261003e/observer-capsule.json'
CURRENT_PREDISPATCH_PATHS = (CURRENT_PUBLIC_CLAIM_PATH,
    CURRENT_LAUNCH_CONFIG_PATH, CURRENT_OBSERVER_CAPSULE_PATH)
PUBLIC_SPENDING_SCHEMA = 'radio-native-v3-public-private-spending-bundle-v1'
CLAIM_STORAGE_SCHEMA = 'radio-native-v3-current-public-claim-metadata-observation-v1'
ARCHIVE_FIELDS = frozenset(('schema', 'role', 'repository_root', 'scope', 'rows',
    'logical_bytes', 'allocated_bytes', 'entry_count', 'current_observation_stable',
    'archival_input_map_sha256', 'selected_metadata_only', 'read_only',
    'original_identity_continuity_proved', 'missing_original_storage_accounted', 'execution_authorized'))
CLAIM_FIELDS = frozenset(('schema', 'role', 'repository_root', 'scope', 'control_scope',
    'public_claim_sha256', 'normalized_spending_sha256', 'rows', 'logical_bytes',
    'allocated_bytes', 'entry_count', 'current_observation_stable', 'read_only', 'execution_authorized',
    'metadata_only', 'bootstrap_origin_qualified'))
LEDGER_FIELDS = frozenset(('schema', 'ledger_root', 'control_scope', 'activation_receipt_sha256',
    'invocation_spending_sha256', 'rows', 'logical_bytes', 'allocated_bytes', 'entry_count',
    'witness_bindings_verified', 'ledger_inventory_exact', 'current_observation_stable'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()


def value_pin(value):
    raw = canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def absolute(value):
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError('Bounded canonical absolute current custody path required')
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or len(value.encode()) > 4096 or len(value.split('/')) > 64
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Bounded canonical absolute current custody path required')
    return value


def _overlap(first, second):
    return (first == second or first.startswith(second + '/')
        or second.startswith(first + '/'))


def reject_historical_identity(value):
    if type(value) is not dict:
        raise ValueError('Exact custody identity object required')
    for namespace, marker, commit in SPENT_ACTIVATIONS:
        if (value.get('namespace') == namespace or value.get('marker_path') == marker
                or value.get('activation_commit') == commit):
            raise ValueError('Historical a/b/c activation identity remains permanently spent')
    for namespace, marker in RETIRED_PREPARATION_IDENTITIES:
        if value.get('namespace') == namespace or value.get('marker_path') == marker:
            raise ValueError('Historical d preparation identity remains retired')


def validate_root(plan, repository_root, execution_scope=None):
    """Bind the current canonical root supplied by the independently held caller."""
    root = validate_current_root(repository_root)
    reject_historical_identity(plan)
    if plan.get('invocation_repository_root') != root:
        raise ValueError('Plan must bind the independently authenticated current repository root')
    ledger = root + '/' + CURRENT_LEDGER_DIRECTORY
    if plan.get('invocation_ledger_root') != ledger:
        raise ValueError('Exact separate current e ledger required')
    if plan.get('current_public_claim_path') != CURRENT_PUBLIC_CLAIM_PATH:
        raise ValueError('Exact fixed current public permanent-spend envelope path required')
    if execution_scope is not None:
        scope = absolute(execution_scope)
        if not scope.startswith(root + '/'):
            raise ValueError('Current control scope must be within the authenticated current root')
        if _overlap(scope, ledger):
            raise ValueError('Current e ledger must remain outside the workload scope')
        if _overlap(scope, root + '/' + str(Path(CURRENT_PUBLIC_CLAIM_PATH).parent)):
            raise ValueError('Current public claim metadata must remain outside the workload scope')
        for relative in HISTORICAL_RELATIVE_ROOTS:
            if _overlap(scope, root + '/' + relative):
                raise ValueError('Current scope cannot overlap a retired historical scope or ledger')
        for relative in (*INPUT_PATHS, *ARCHIVAL_SOURCE_PINS):
            if _overlap(scope, root + '/' + relative):
                raise ValueError('Current scope cannot overlap fixed archival metadata copies')
        for _, marker, *_ in (*SPENT_ACTIVATIONS, *RETIRED_PREPARATION_IDENTITIES):
            if _overlap(scope, root + '/' + marker):
                raise ValueError('Current scope cannot overlap a historical activation marker')
    return root


def validate_current_root(repository_root):
    """Pure root policy for plan construction; no original filesystem query."""
    root = absolute(repository_root)
    if _overlap(root, ORIGINAL_REPOSITORY_ROOT):
        raise ValueError('Current custody cannot overlap the unavailable original repository root')
    for retained in HISTORICAL_RELATIVE_ROOTS:
        # A moved repository cannot make a spent workload or journal its root.
        if retained in root.split('/'):
            raise ValueError('Current repository cannot be a historical scope or ledger')
    return root


def validate_contract(plan, freeze, *, repository_root, execution_scope):
    root = validate_root(plan, repository_root, execution_scope)
    if plan.get('historical_storage_original_identity_continuity_qualified') is not False:
        raise ValueError('Original historical identity continuity remains unqualified')
    for field in ('missing_original_storage_accounted', 'original_identity_continuity_proved'):
        if plan.get(field, False) is not False:
            raise ValueError('Missing original storage and original identity cannot be qualified')
    if plan.get('retained_storage_component_roles') != RETAINED_COMPONENT_ROLES:
        raise ValueError('Exact current archive b/c and e ledger component roles required')
    if plan.get('historical_storage_inputs') != ARCHIVAL_INPUT_PINS:
        raise ValueError('Exact nineteen independently pinned archival metadata inputs required')
    if type(freeze) is not dict:
        raise ValueError('Independently held current input/source freeze required')
    for relative, expected in ARCHIVAL_INPUT_PINS.items():
        if (freeze.get('input_sha256s', {}).get(relative) != expected['sha256']
                or plan.get('code_files', {}).get(relative) != expected):
            raise ValueError('Complete current freeze and material must bind every archive: ' + relative)
    source_pin = plan.get('code_files', {}).get(SELF)
    _pin(source_pin)
    if freeze.get('code_sha256s', {}).get(SELF) != source_pin['sha256']:
        raise ValueError('Current freeze must bind the reviewed v3 custody source')
    return root


def _pin(value):
    if (type(value) is not dict or set(value) != {'bytes', 'sha256'}
            or type(value['bytes']) is not int or not 0 < value['bytes'] <= MAX_BYTES
            or type(value['sha256']) is not str
            or not re.fullmatch('[a-f0-9]{64}', value['sha256'])):
        raise ValueError('Exact bounded independent raw-file pin required')
    return value


def _metadata(info):
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'allocated_bytes': info.st_blocks * 512,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def _directory(info):
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Ordinary nofollow custody ancestor required')
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def _read_snapshot(path, expected=None):
    """Read a stable sole-link leaf, optionally against an independent byte pin.

    Omitting ``expected`` only measures current raw bytes for accounting. It
    proves no metadata origin, admission, execution, or bootstrap authority.
    """
    path = absolute(path)
    expected = dict(_pin(expected)) if expected is not None else None
    opened = []; chain = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(fd); chain.append((fd, None, None, _directory(os.fstat(fd))))
        for name in path[1:].split('/')[:-1]:
            parent = fd; named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            identity = _directory(named)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append(fd)
            if _directory(os.fstat(fd)) != identity:
                raise ValueError('Current custody ancestor changed during open')
            chain.append((fd, parent, name, identity))
        name = Path(path).name; parent = fd
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        opened.append(fd); before = os.fstat(fd); metadata = _metadata(before)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= MAX_BYTES
                or expected is not None and before.st_size != expected['bytes']):
            raise ValueError('Exact stable sole-link current metadata input required')
        chunks = []; remaining = before.st_size + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk: break
            chunks.append(chunk); remaining -= len(chunk)
        raw = b''.join(chunks)
        if (metadata != _metadata(os.fstat(fd))
                or metadata != _metadata(os.stat(name, dir_fd=parent, follow_symlinks=False))
                or len(raw) != before.st_size
                or expected is not None and hashlib.sha256(raw).hexdigest() != expected['sha256']):
            raise ValueError('Current metadata changed or differs from independent raw pin')
        for held, ancestor_parent, ancestor_name, identity in chain:
            if (_directory(os.fstat(held)) != identity
                    or (ancestor_parent is not None and
                        _directory(os.stat(ancestor_name, dir_fd=ancestor_parent, follow_symlinks=False)) != identity)):
                raise ValueError('Current custody ancestor binding changed during read')
        actual_pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return raw, {'path': path, 'kind': 'file', **metadata, 'raw_pin': actual_pin}
    except OSError as error:
        raise ValueError('Required nofollow current custody input unavailable') from error
    finally:
        for held in reversed(opened): os.close(held)


def read_raw(path, expected):
    return _read_snapshot(path, dict(_pin(expected)))[0]


def _directory_snapshot(path, expected_names=None):
    path = absolute(path); opened = []; chain = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(fd)
        for name in path[1:].split('/'):
            parent = fd; identity = _directory(os.stat(name, dir_fd=parent, follow_symlinks=False))
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append(fd)
            if _directory(os.fstat(fd)) != identity:
                raise ValueError('Current metadata directory changed during open')
            chain.append((fd, parent, name, identity))
        metadata = _metadata(os.fstat(fd))
        if expected_names is not None:
            observed_names = set()
            with os.scandir(fd) as entries:
                for entry in entries:
                    observed_names.add(entry.name)
                    if len(observed_names) > len(expected_names):
                        raise ValueError('Exact current metadata directory membership required')
            if observed_names != set(expected_names):
                raise ValueError('Exact current metadata directory membership required')
        if metadata != _metadata(os.stat(name, dir_fd=parent, follow_symlinks=False)):
            raise ValueError('Current metadata directory binding changed')
        for held, ancestor_parent, ancestor_name, identity in chain:
            if (_directory(os.fstat(held)) != identity or
                    _directory(os.stat(ancestor_name, dir_fd=ancestor_parent, follow_symlinks=False)) != identity):
                raise ValueError('Current metadata directory ancestor changed')
        return {'path': path, 'kind': 'directory', **metadata}
    except OSError as error:
        raise ValueError('Required nofollow current metadata directory unavailable') from error
    finally:
        for held in reversed(opened): os.close(held)


def _archive_label(relative):
    for label, copy_root in ARCHIVAL_COPY_ROOTS.items():
        if relative.startswith(copy_root + '/'):
            return label
    raise ValueError('Fixed current archival metadata copy path required')


def _required_files(root, label):
    return {root + '/' + relative: pin for relative, pin in ARCHIVAL_INPUT_PINS.items()
        if _archive_label(relative) == label}


def _required_directories(root, files):
    directories = {root}
    for path in files:
        parent = str(Path(path).parent)
        while parent != root:
            if not parent.startswith(root + '/'):
                raise ValueError('Archival metadata cannot escape current root')
            directories.add(parent); parent = str(Path(parent).parent)
    return directories


def _observation(root, label, rows):
    return {'schema': ARCHIVE_SCHEMA, 'role': label, 'repository_root': root,
        'scope': root + '/' + ARCHIVAL_COPY_ROOTS[label],
        'rows': sorted(rows, key=lambda row: row['path']),
        'logical_bytes': sum(row['bytes'] for row in rows),
        'allocated_bytes': sum(row['allocated_bytes'] for row in rows),
        'entry_count': len(rows), 'current_observation_stable': True,
        'archival_input_map_sha256': ARCHIVAL_INPUT_MAP_SHA256,
        'selected_metadata_only': True, 'read_only': True,
        'original_identity_continuity_proved': False,
        'missing_original_storage_accounted': False, 'execution_authorized': False}


def observe_historical_storage(code_root, *, plan, freeze, repository_root, execution_scope):
    """Read only current metadata copies; do not probe any original scope."""
    root = validate_contract(plan, freeze, repository_root=repository_root,
        execution_scope=execution_scope)
    code_root = absolute(code_root)
    if not (code_root == root or code_root.startswith(root + '/')):
        raise ValueError('Reviewed source root must be within the authenticated current repository')
    all_files = {root + '/' + relative: expected for relative, expected in ARCHIVAL_INPUT_PINS.items()}
    directories = set()
    for label in ARCHIVAL_COPY_ROOTS:
        directories.update(_required_directories(root + '/' + ARCHIVAL_COPY_ROOTS[label], _required_files(root, label)))
    names = {directory: {Path(path).name for path in set(all_files) | directories
        if str(Path(path).parent) == directory} for directory in directories}
    before = {path: _directory_snapshot(path, names[path]) for path in sorted(directories)}
    file_rows = {}
    for path, expected in all_files.items():
        _, file_rows[path] = _read_snapshot(path, expected)
    # A second descriptor read of every leaf makes this a bounded stable window,
    # rather than a concatenation of unrelated file observations.
    for path, expected in all_files.items():
        if _read_snapshot(path, expected)[1] != file_rows[path]:
            raise ValueError('Current archival metadata changed across observation window')
    after = {path: _directory_snapshot(path, names[path]) for path in sorted(directories)}
    if before != after:
        raise ValueError('Current archival metadata directories changed across observation window')
    components = {}
    for label in ('archive_b_metadata_copy', 'archive_c_metadata_copy'):
        files = _required_files(root, label)
        dirs = _required_directories(root + '/' + ARCHIVAL_COPY_ROOTS[label], files)
        rows = [file_rows[path] for path in files] + [before[path] for path in dirs]
        components[label] = _observation(root, label, rows)
    return types.SimpleNamespace(join_retained_storage_components=join_retained_storage_components), components


def _validated_rows(value):
    rows = value.get('rows')
    if type(rows) is not list or not 1 <= len(rows) <= MAX_ENTRIES:
        raise ValueError('Bounded complete current storage rows required')
    if any(type(row) is not dict or type(row.get('path')) is not str for row in rows):
        raise ValueError('Exact current storage row object required')
    if [row['path'] for row in rows] != sorted(row['path'] for row in rows):
        raise ValueError('Canonical sorted current storage rows required')
    paths = set(); identities = set(); logical = allocated = 0
    for row in rows:
        path = absolute(row['path']); kind = row.get('kind')
        info = {name: row[name] for name in METADATA_FIELDS if name in row}
        fields = {'path', 'kind'} | METADATA_FIELDS
        if (kind not in ('file', 'directory') or set(info) != METADATA_FIELDS
                or set(row) not in (fields, fields | {'raw_pin'})):
            raise ValueError('Exact ordinary current storage row and metadata required')
        for name, number in info.items():
            if type(number) is not int or not 0 <= number <= (1 << 63) - 1:
                raise ValueError('Bounded exact current storage metadata integers required')
        if not info['inode'] or not info['nlink'] or info['mode'] > 0o7777:
            raise ValueError('Ordinary current storage inode/link/mode required')
        identity = (info['device'], info['inode'])
        if path in paths or identity in identities:
            raise ValueError('Current storage path or device/inode alias rejected')
        paths.add(path); identities.add(identity)
        if kind == 'file':
            if info['nlink'] != 1:
                raise ValueError('Current storage files require sole links')
            if 'raw_pin' in row and _pin(row['raw_pin'])['bytes'] != info['bytes']:
                raise ValueError('Current storage raw pin size differs from metadata')
        elif 'raw_pin' in row:
            raise ValueError('Directory cannot bear a raw file pin')
        logical += info['bytes']; allocated += info['allocated_bytes']
    if (type(value.get('logical_bytes')) is not int or value['logical_bytes'] != logical
            or type(value.get('allocated_bytes')) is not int or value['allocated_bytes'] != allocated
            or type(value.get('entry_count')) is not int or value['entry_count'] != len(rows)):
        raise ValueError('Current storage totals differ from exact rows')
    return rows, paths, identities, logical, allocated


def _normalized_public_spending(value, *, root, scope):
    if (type(value) is not dict
            or set(value) != {'schema', 'local_witness', 'public_claim', 'public_claim_sha256', 'dispatch_witness'}
            or value.get('schema') != PUBLIC_SPENDING_SCHEMA
            or type(value['local_witness']) is not dict or type(value['public_claim']) is not dict
            or type(value['public_claim_sha256']) is not str
            or not re.fullmatch('[a-f0-9]{64}', value['public_claim_sha256'])
            or hashlib.sha256(canonical(value['public_claim'])).hexdigest() != value['public_claim_sha256']
            or value['dispatch_witness'] is not None and type(value['dispatch_witness']) is not dict):
        raise ValueError('Independently authenticated exact public/private spending envelope required')
    value = json.loads(canonical(value))
    if (value['local_witness'].get('control_scope') != scope
            or value['local_witness'].get('ledger_root') != root + '/' + CURRENT_LEDGER_DIRECTORY):
        raise ValueError('Public claim envelope must retain the exact current local witness scope and ledger')
    # The create-only retained envelope precedes the local dispatch transition.
    # A running worker's witness binds that transition separately; the retained
    # public envelope is never overwritten merely to add a dispatch receipt.
    value['dispatch_witness'] = None
    return value


def observe_current_public_claim(public_spending, *, root, scope):
    """Charge the fixed three-file bootstrap directory, granting no authority.

    The envelope must match the independently authenticated spending argument.
    Config and capsule canonical bytes are measured only; their independent
    outer CLI pins must be checked by the launcher and observer respectively.
    A self-pinned config/capsule or this accounting result cannot admit dispatch.
    """
    normalized = _normalized_public_spending(public_spending, root=root, scope=scope)
    raw = canonical(normalized) + b'\n'; expected = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    path = root + '/' + CURRENT_PUBLIC_CLAIM_PATH; directory = str(Path(path).parent)
    names = {Path(relative).name for relative in CURRENT_PREDISPATCH_PATHS}
    before = _directory_snapshot(directory, names)
    observed, envelope_row = _read_snapshot(path, expected)
    if observed != raw:
        raise ValueError('Retained public claim envelope differs from authenticated normalized bytes')
    rows = [before, envelope_row]
    for relative in (CURRENT_LAUNCH_CONFIG_PATH, CURRENT_OBSERVER_CAPSULE_PATH):
        measured, row = _read_snapshot(root + '/' + relative)
        try:
            value = json.loads(measured)
            if type(value) is not dict or canonical(value) + b'\n' != measured:
                raise ValueError('Bounded exact canonical bootstrap metadata object required')
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError('Bounded exact canonical bootstrap metadata object required') from error
        rows.append(row)
    identities = {(row['device'], row['inode']) for row in rows}
    if len(identities) != len(rows):
        raise ValueError('Predispatch metadata device/inode alias rejected')
    for row in rows[1:]:
        if _read_snapshot(row['path'], row['raw_pin'])[1] != row:
            raise ValueError('Predispatch metadata changed across the observation window')
    if _directory_snapshot(directory, names) != before:
        raise ValueError('Predispatch metadata directory changed across the observation window')
    return {'schema': CLAIM_STORAGE_SCHEMA, 'role': 'current_claim_metadata',
        'repository_root': root, 'scope': directory, 'control_scope': scope,
        'public_claim_sha256': normalized['public_claim_sha256'],
        'normalized_spending_sha256': hashlib.sha256(canonical(normalized)).hexdigest(),
        'rows': sorted(rows, key=lambda value: value['path']),
        'logical_bytes': sum(row['bytes'] for row in rows),
        'allocated_bytes': sum(row['allocated_bytes'] for row in rows), 'entry_count': len(rows),
        'current_observation_stable': True, 'read_only': True, 'execution_authorized': False,
        'metadata_only': True, 'bootstrap_origin_qualified': False}


def observe_current_claim(plan, public_spending, *, repository_root, execution_scope):
    root = validate_root(plan, repository_root, execution_scope)
    return observe_current_public_claim(public_spending, root=root, scope=execution_scope)


def join_retained_storage_components(components, *, expected_observation_pins, expected_component_roles):
    """Pure exact join after the caller authenticates current ledger bindings."""
    if (expected_component_roles != RETAINED_COMPONENT_ROLES
            or type(components) is not dict or set(components) != set(RETAINED_COMPONENT_ROLES)
            or type(expected_observation_pins) is not dict
            or set(expected_observation_pins) != set(RETAINED_COMPONENT_ROLES)):
        raise ValueError('Exact complete current archive/ledger components and independent pins required')
    detached = {}
    for label in RETAINED_COMPONENT_ROLES:
        value = components[label]
        fields = LEDGER_FIELDS if label == 'current_ledger' else CLAIM_FIELDS if label == 'current_claim' else ARCHIVE_FIELDS
        if (type(value) is not dict or set(value) != fields
                or type(value.get('rows')) is not list or not 1 <= len(value['rows']) <= MAX_ENTRIES):
            raise ValueError('Exact bounded current component observation fields required')
        pin = dict(_pin(expected_observation_pins[label]))
        if value_pin(components[label]) != pin:
            raise ValueError('Current component differs from independently held observation pin')
        detached[label] = json.loads(canonical(components[label]))
    ledger = detached['current_ledger']; root = absolute(detached['archive_b_metadata_copy'].get('repository_root'))
    scope = absolute(ledger.get('control_scope')); ledger_root = absolute(ledger.get('ledger_root'))
    if (ledger_root != root + '/' + CURRENT_LEDGER_DIRECTORY or not scope.startswith(root + '/')
            or _overlap(scope, ledger_root)):
        raise ValueError('Current joined ledger and workload must bind the independent current root')
    validate_current_root(root)
    labels = []; all_rows = []; seen_paths = set(); seen_identities = set(); logical = allocated = 0
    for label, value in detached.items():
        role = RETAINED_COMPONENT_ROLES[label]
        rows, paths, identities, current_logical, current_allocated = _validated_rows(value)
        if label in ('archive_b_metadata_copy', 'archive_c_metadata_copy'):
            archive_root = root + '/' + ARCHIVAL_COPY_ROOTS[label]
            if (value.get('schema') != ARCHIVE_SCHEMA or value.get('role') != role
                    or value.get('repository_root') != root
                    or value.get('scope') != archive_root
                    or value.get('archival_input_map_sha256') != ARCHIVAL_INPUT_MAP_SHA256
                    or any(value.get(field) is not True for field in
                        ('current_observation_stable', 'selected_metadata_only', 'read_only'))
                    or any(value.get(field) is not False for field in
                        ('original_identity_continuity_proved', 'missing_original_storage_accounted', 'execution_authorized'))):
                raise ValueError('Exact current read-only archive metadata observation required')
            required_files = _required_files(root, label)
            actual_files = {row['path']: row.get('raw_pin') for row in rows if row['kind'] == 'file'}
            actual_dirs = {row['path'] for row in rows if row['kind'] == 'directory'}
            if (actual_files != required_files
                    or actual_dirs != _required_directories(archive_root, required_files)):
                raise ValueError('Exact fixed archival metadata and selected parent membership required')
        elif label == 'current_claim':
            claim_root = root + '/' + str(Path(CURRENT_PUBLIC_CLAIM_PATH).parent)
            claim_paths = {root + '/' + relative for relative in CURRENT_PREDISPATCH_PATHS}
            if (value.get('schema') != CLAIM_STORAGE_SCHEMA or value.get('role') != role
                    or value.get('repository_root') != root or value.get('scope') != claim_root
                    or value.get('control_scope') != scope or len(rows) != 4
                    or {row['path'] for row in rows if row['kind'] == 'directory'} != {claim_root}
                    or {row['path'] for row in rows if row['kind'] == 'file'} != claim_paths
                    or any(value.get(field) is not True for field in ('current_observation_stable', 'read_only'))
                    or value.get('execution_authorized') is not False
                    or value.get('metadata_only') is not True
                    or value.get('bootstrap_origin_qualified') is not False
                    or any('raw_pin' not in row for row in rows if row['kind'] == 'file')):
                raise ValueError('Exact current retained public-claim file/directory observation required')
            for field in ('public_claim_sha256', 'normalized_spending_sha256'):
                if type(value.get(field)) is not str or not re.fullmatch('[a-f0-9]{64}', value[field]):
                    raise ValueError('Current claim metadata must bind authenticated public envelope SHA256')
        else:
            if (value.get('schema') != LEDGER_STORAGE_SCHEMA
                    or any(value.get(field) is not True for field in
                        ('witness_bindings_verified', 'ledger_inventory_exact', 'current_observation_stable'))
                    or len(rows) != 3 or {row['path'] for row in rows if row['kind'] == 'directory'} != {ledger_root}
                    or sum(row['kind'] == 'file' and str(Path(row['path']).parent) == ledger_root for row in rows) != 2):
                raise ValueError('Exact independently verified current claim and dispatch ledger required')
            filenames = {Path(row['path']).name for row in rows if row['kind'] == 'file'}
            claims = {name for name in filenames if re.fullmatch('spent-[a-f0-9]{64}\\.json', name)}
            if len(claims) != 1 or filenames != claims | {'dispatch-' + next(iter(claims))[len('spent-'):]}:
                raise ValueError('Current ledger must retain exactly matching claim and dispatch filenames')
            for field in ('activation_receipt_sha256', 'invocation_spending_sha256'):
                if type(value.get(field)) is not str or not re.fullmatch('[a-f0-9]{64}', value[field]):
                    raise ValueError('Current ledger observation must bind receipt and spending SHA256')
        if paths & seen_paths or identities & seen_identities:
            raise ValueError('Current archive/ledger path or device/inode alias rejected')
        if any(_overlap(scope, path) for path in paths):
            raise ValueError('Current workload cannot overlap retained archive or ledger storage')
        seen_paths.update(paths); seen_identities.update(identities)
        logical += current_logical; allocated += current_allocated
        if max(logical, allocated) > MAX_STORAGE_BYTES or len(all_rows) + len(rows) > MAX_ENTRIES:
            raise ValueError('Original whole storage or entry bound exceeded by current retained storage')
        component_root = ledger_root if label == 'current_ledger' else claim_root if label == 'current_claim' else archive_root
        labels.append({'role': label, 'root': component_root,
            'observation_role': role, 'observation_sha256': expected_observation_pins[label]['sha256'],
            'logical_bytes': current_logical, 'allocated_bytes': current_allocated, 'entry_count': len(rows)})
        all_rows.extend({'component': label, **row} for row in rows)
    return {'schema': JOIN_SCHEMA, 'components': labels, 'rows': sorted(all_rows, key=lambda row: row['path']),
        'logical_bytes': logical, 'allocated_bytes': allocated, 'entry_count': len(all_rows),
        'charged_once': True, 'read_only': True, 'execution_authorized': False,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False,
        'missing_original_storage_accounted': False, 'original_identity_continuity_proved': False,
        'current_control_scope': scope, 'selected_archival_metadata_only': True}


def observe_joined_storage(code_root, *, plan, freeze, repository_root, execution_scope,
        prospective_ledger, public_spending=None):
    root = validate_root(plan, repository_root, execution_scope)
    if (type(prospective_ledger) is not dict
            or prospective_ledger.get('control_scope') != execution_scope
            or prospective_ledger.get('ledger_root') != plan.get('invocation_ledger_root')):
        raise ValueError('Current ledger must bind the current scope and exact e root before archive reads')
    ledger = json.loads(canonical(prospective_ledger))
    claim = observe_current_claim(plan, public_spending, repository_root=root, execution_scope=execution_scope)
    storage, components = observe_historical_storage(code_root,
        plan=plan, freeze=freeze, repository_root=root, execution_scope=execution_scope)
    components['current_ledger'] = ledger
    components['current_claim'] = claim
    return storage.join_retained_storage_components(components,
        expected_observation_pins={name: value_pin(value) for name, value in components.items()},
        expected_component_roles=RETAINED_COMPONENT_ROLES)
