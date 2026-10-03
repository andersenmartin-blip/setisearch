#!/usr/bin/env python3
"""Pending resource snapshots and independently joined whole-control receipts.

The only launch CLI is a fixed admitted control role. It remains behind the
materialized fixture's execution guard. A read-only join never writes a PASS
before the admitted measurement driver has been independently reaped. Local
JSON provenance labels do not authenticate themselves: the integrating parent
must retain the byte pins and exact argv before loading the receipts.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import stat
import sys
import time
import types

SCHEMA = 'radio-native-v2-whole-resource-finalization-v1'
LEDGER_STORAGE_SCHEMA = 'radio-native-v2-control-invocation-spend-storage-v1'
EXTERNAL_STORAGE_SCHEMA = 'radio-native-v2-retained-prospective-storage-join-v2'
EXTERNAL_STORAGE_ROLES = ('historical_b_scope', 'historical_b_ledger',
    'historical_c_scope', 'historical_c_ledger', 'prospective_ledger')
EXTERNAL_STORAGE_OBSERVATION_ROLES = {
    'historical_b_scope': 'historical_scope', 'historical_b_ledger': 'historical_ledger',
    'historical_c_scope': 'historical_scope', 'historical_c_ledger': 'historical_ledger',
    'prospective_ledger': 'prospective_ledger'}
EXTERNAL_STORAGE_METADATA = frozenset(('device', 'inode', 'mode', 'nlink',
    'uid', 'gid', 'bytes', 'allocated_bytes', 'mtime_ns', 'ctime_ns'))
MAX_EXTERNAL_STORAGE_BYTES = 16 * 1024 * 1024
OBSERVATION_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-process-observation'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
MIB = 1024 * 1024
LIMITS = {'case_calls': 64, 'run_calls': 512,
    'case_request_bytes': 48*MIB, 'run_request_bytes': 384*MIB,
    'case_response_bytes': 64*MIB, 'run_response_bytes': 512*MIB,
    'case_seconds': 600, 'run_seconds': 4800,
    'rss_bytes': 512*MIB, 'case_storage_bytes': 192*MIB,
    'run_storage_bytes': 1536*MIB}
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
SELF = 'scripts/radio_native_v2_resource_finalization.py'
FIXTURE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
SUPERVISOR = 'scripts/radio_native_v2_process_tree_supervisor.py'
ADMISSION = 'scripts/radio_native_v2_worker_admission.py'
PENDING_NAME = 'pending-resource-measurements.json'
DRIVER_IDENTITY_NAME = 'measurement-driver-identity.json'
DRIVER_OBSERVATION_NAME = 'measurement-driver-observation.json'
RUNNER_OBSERVATION_NAME = 'whole-control-supervisor-observation.json'
FINAL_NAME = 'resource-final-disposition.json'
FINAL_INPUT_NAME = 'final-report-input.json'
FINAL_WRITER_IDENTITY_NAME = 'final-report-writer-identity.json'
FINAL_WRITER_OBSERVATION_NAME = 'final-report-writer-observation.json'
FINAL_WRITER_STDOUT_NAME = 'final-report-writer-stdout.log'
FINAL_WRITER_STDERR_NAME = 'final-report-writer-stderr.log'
OUTER_LAUNCH_METADATA_NAMES = ('compact-control-launch-stdout.log',
    'compact-control-launch-stderr.log', 'compact-control-launch-observation.json',
    'compact-control-launch-disposition.json', 'compact-control-launch-preflight.json',
    'compact-control-launch-closed-failure.json')
FINAL_METADATA_NAMES = (PENDING_NAME, DRIVER_IDENTITY_NAME,
    DRIVER_OBSERVATION_NAME, FINAL_INPUT_NAME, FINAL_WRITER_IDENTITY_NAME,
    FINAL_WRITER_OBSERVATION_NAME, FINAL_WRITER_STDOUT_NAME,
    FINAL_WRITER_STDERR_NAME, FINAL_NAME, *OUTER_LAUNCH_METADATA_NAMES)
METADATA_RESERVATION_BYTES = 256 * 1024
DIRECTORY_RESERVATION_BYTES = 65536
MAX_EVIDENCE_BYTES = 2*MIB
MAX_INVENTORY_ENTRIES = 32768
MAX_MATERIAL_SOURCE_FILES = 128
TINY_REPORT_INPUT_BYTES = 65536
TINY_REPORT_SCOPE_BYTES = 2*MIB
TINY_REPORT_SECONDS = 3.0
# Independent reviewed dispatch pins. Root refreshes these only after reviewing
# the final code of the fixed source implementations; a supplied bundle cannot
# select an arbitrary implementation for any admission check.
BOOTSTRAP_SOURCE_PINS = {'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 129756, 'sha256': '9d73a4b31a97423fd7bc5fdee176b9d090b8534153b4727c54bc2da073cfcd1d'}, 'scripts/radio_native_v2_worker_admission.py': {'bytes': 82049, 'sha256': '1660d0b644674fd839aec2364fee1b1adf08539b524191dba9b54a83ea722917'}, 'scripts/radio_native_v2_process_tree_supervisor.py': {'bytes': 82676, 'sha256': '84950f2f6fe8094f2e86f55e0b4c6826b7e142581ec4503f8ccc75fe476d9b8b'}}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'real_public_github_mutations': 0,
    'actual_git_processes': 0, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False,
    'automatic_retry': False}
LIMITATIONS = [
    'Externally retained expected receipt pins and argv are caller trust inputs; JSON labels alone are not authenticated kernel evidence.',
    'The dedicated measurement driver must be independently observed through snapshot fsync and termination.',
    'The final report writer requires a distinct parent wait4 observation; that observer receipt does not prove the observer process future termination.',
    'Kernel escape, tracing, namespace transitions, complete operating runtime closure and native/HTTP host joins remain unqualified.',
    'RSS accounting is the maximum individual process, not simultaneous process RSS summed across a tree.']


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _integer(value, label, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Exact nonnegative integer required: ' + label)
    return value


def _seconds(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Finite nonnegative duration required: ' + label)
    return float(value)


def _absolute(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or str(path) != str(path.absolute()):
        raise ValueError('Canonical absolute evidence path required')
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('Symlink evidence ancestor rejected')
    return path


def _relative(scope, path):
    scope = _absolute(scope); path = _absolute(path)
    try: relative = path.relative_to(scope)
    except ValueError as failure:
        raise ValueError('All retained control evidence must remain in the measured scope') from failure
    if not relative.parts: raise ValueError('Evidence file cannot be the scope directory')
    return relative.as_posix()


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
        info.st_ctime_ns, info.st_nlink, info.st_blocks)


def read_pinned_json(path, expected_pin=None, *, maximum=MAX_EVIDENCE_BYTES):
    path = _absolute(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('Bounded sole-link regular evidence file required')
        chunks = []; remaining = maximum + 1
        while remaining:
            raw = os.read(fd, min(65536, remaining))
            if not raw: break
            chunks.append(raw); remaining -= len(raw)
        raw = b''.join(chunks); after = os.fstat(fd)
        if len(raw) != before.st_size or _identity(before) != _identity(after) or _identity(path.lstat()) != _identity(after):
            raise ValueError('Evidence identity or contents changed during read')
    finally: os.close(fd)
    observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected_pin is not None:
        _validate_pin(expected_pin)
        if canonical(observed) != canonical(expected_pin):
            raise ValueError('Evidence differs from the independently retained exact byte pin')
    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate JSON evidence property rejected')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite JSON evidence rejected')))
    if type(value) is not dict: raise ValueError('JSON evidence object required')
    return value, observed


def _validate_pin(pin):
    if type(pin) is not dict or set(pin) != {'bytes', 'sha256'}:
        raise ValueError('Exact independently retained bytes/SHA256 pin required')
    _integer(pin['bytes'], 'pin bytes')
    if type(pin['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', pin['sha256']):
        raise ValueError('Exact lowercase SHA256 pin required')


def _interpreter_pin(path):
    path = _absolute(Path(path).resolve())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    digest = hashlib.sha256(); count = 0
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 128*MIB:
            raise ValueError('Bounded installed interpreter executable required')
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            digest.update(raw); count += len(raw)
        if _identity(before) != _identity(os.fstat(fd)) or _identity(path.lstat()) != _identity(before):
            raise ValueError('Installed interpreter changed while checking observation')
    finally: os.close(fd)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


def storage_inventory(scope):
    """Count every file and directory; verify a stable bounded directory walk.

    Content hashing is not substituted for allocated blocks. Both logical and
    allocated bytes contribute to their separate run and per-case bounds.
    """
    scope = _absolute(scope)
    if not scope.is_dir(): raise ValueError('Measured directory scope required')
    rows = []
    def visit(path):
        before = path.lstat()
        if len(rows) >= MAX_INVENTORY_ENTRIES:
            raise ValueError('Bounded resource inventory capacity exceeded; disposition remains closed')
        relative = path.relative_to(scope).as_posix()
        if stat.S_ISDIR(before.st_mode):
            names = sorted(entry.name for entry in os.scandir(path))
            row = {'path': relative, 'kind': 'directory', 'bytes': before.st_size,
                'allocated_bytes': before.st_blocks*512, 'device': before.st_dev, 'inode': before.st_ino}
            rows.append(row)
            for name in names: visit(path/name)
            after = path.lstat()
            if _identity(before) != _identity(after) or names != sorted(entry.name for entry in os.scandir(path)):
                raise ValueError('Directory inventory changed during read')
        elif stat.S_ISREG(before.st_mode) and before.st_nlink == 1:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                if _identity(before) != _identity(os.fstat(fd)):
                    raise ValueError('File inventory identity changed during open')
            finally: os.close(fd)
            rows.append({'path': relative, 'kind': 'file', 'bytes': before.st_size,
                'allocated_bytes': before.st_blocks*512, 'device': before.st_dev, 'inode': before.st_ino,
                'mtime_ns': before.st_mtime_ns, 'ctime_ns': before.st_ctime_ns})
        else: raise ValueError('Only directories and sole-link ordinary files may be retained')
    visit(scope)
    return {'scope': str(scope), 'rows': rows, 'logical_bytes': sum(row['bytes'] for row in rows),
        'allocated_bytes': sum(row['allocated_bytes'] for row in rows), 'entry_count': len(rows)}


def _base_inventory_pin(inventory):
    base = []
    for row in inventory['rows']:
        if row['path'] in FINAL_METADATA_NAMES: continue
        # Creation of the predeclared terminal metadata may grow its parent
        # directory. Its actual size/allocation is still charged below.
        if row['kind'] == 'directory':
            base.append({key: row[key] for key in ('path', 'kind', 'device', 'inode')})
        else: base.append(row)
    return hashlib.sha256(canonical(base)).hexdigest()


def _validate_inventory_totals(inventory):
    if type(inventory) is not dict or type(inventory.get('rows')) is not list:
        raise ValueError('Exact storage inventory rows required')
    rows = inventory['rows']
    if len(rows) > MAX_INVENTORY_ENTRIES:
        raise ValueError('Bounded storage inventory capacity exceeded')
    names = set()
    for row in rows:
        if (type(row) is not dict or row.get('kind') not in ('file', 'directory')
                or type(row.get('path')) is not str or row['path'] in names):
            raise ValueError('Distinct exact file/directory storage rows required')
        names.add(row['path'])
        for field in ('bytes', 'allocated_bytes'):
            _integer(row.get(field), 'storage '+field)
    for field in ('logical_bytes', 'allocated_bytes'):
        value = _integer(inventory.get(field), 'inventory '+field)
        source = 'bytes' if field == 'logical_bytes' else field
        if value != sum(row[source] for row in rows):
            raise ValueError('Storage inventory total differs from its exact rows')
    if 'entry_count' in inventory and _integer(inventory['entry_count'], 'inventory entries') != len(rows):
        raise ValueError('Storage inventory entry count differs from its exact rows')


def _external_ledger_inventory(inventory, external_inventory):
    """Validate the complete historical/prospective external storage contract.

    A dictionary is no authentication mechanism: production stage APIs obtain
    this value anew through the independently pinned fixture, which authenticates
    and reobserves historical scope/ledger inputs and the current spend witness.
    Structural validation here never replaces that source/evidence gate. Tiny
    unit probes explicitly construct five-component observations in memory;
    there is no single-ledger production or test fallback.
    """
    if (type(external_inventory) is not dict
            or type(external_inventory.get('rows')) is not list
            or len(external_inventory['rows']) > MAX_INVENTORY_ENTRIES):
        raise ValueError('Bounded complete external storage inventory required')
    raw = canonical(external_inventory)
    if len(raw) > MAX_EXTERNAL_STORAGE_BYTES:
        raise ValueError('Bounded external storage observation serialization exceeded')
    # Validate and return the detached snapshot actually allocated, never mutable
    # caller dictionaries that could change after the totals or binding check.
    external_inventory = json.loads(raw)
    _validate_inventory_totals(external_inventory)
    fields = {'schema', 'components', 'rows', 'logical_bytes', 'allocated_bytes',
        'entry_count', 'charged_once', 'read_only', 'execution_authorized',
        'whole_control_qualified', 'lifetime_accounting_proved', 'current_control_scope'}
    if (set(external_inventory) != fields
            or external_inventory['schema'] != EXTERNAL_STORAGE_SCHEMA
            or external_inventory['charged_once'] is not True
            or external_inventory['read_only'] is not True
            or any(external_inventory[field] is not False for field in
                ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'))
            or type(external_inventory['components']) is not list
            or len(external_inventory['components']) != len(EXTERNAL_STORAGE_ROLES)):
        raise ValueError('Exact independently observed five-component external storage contract required')
    scope = inventory.get('scope')
    if type(scope) is not str or external_inventory['current_control_scope'] != scope:
        raise ValueError('Complete external storage must bind the exact measured control scope')
    scope = _storage_absolute(scope)
    if len(inventory['rows']) + len(external_inventory['rows']) > MAX_INVENTORY_ENTRIES:
        raise ValueError('Combined current/external storage inventory capacity exceeded')
    roots = {}; by_role = {}
    for role, component in zip(EXTERNAL_STORAGE_ROLES, external_inventory['components']):
        if (type(component) is not dict or set(component) != {'role', 'observation_role', 'root',
                'observation_sha256', 'entry_count', 'logical_bytes', 'allocated_bytes'}
                or component['role'] != role
                or component['observation_role'] != EXTERNAL_STORAGE_OBSERVATION_ROLES[role]):
            raise ValueError('Exact ordered historical/prospective storage components required')
        if type(component['observation_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', component['observation_sha256']):
            raise ValueError('Exact authenticated component observation digest required')
        root = _storage_absolute(component['root'])
        for other in [scope, *roots.values()]:
            if _storage_overlap(root, other):
                raise ValueError('Current/historical/prospective storage roots must be disjoint')
        roots[role] = root; by_role[role] = []
    existing = set()
    for row in inventory['rows']:
        identity = (_storage_integer(row.get('device'), 'scope storage device'),
            _storage_integer(row.get('inode'), 'scope storage inode', minimum=1))
        if identity in existing:
            raise ValueError('Current storage contains a duplicate inode allocation')
        existing.add(identity)
    seen = set()
    for row in external_inventory['rows']:
        role = row.get('component')
        if role not in roots:
            raise ValueError('Every external storage row requires its exact component')
        fields = {'component', 'path', 'kind'} | EXTERNAL_STORAGE_METADATA
        if row['kind'] == 'file' and role != 'prospective_ledger': fields |= {'raw_pin'}
        if set(row) != fields:
            raise ValueError('Exact authenticated external storage row metadata required')
        path = _storage_absolute(row['path']); root = roots[role]
        if path != root and not path.startswith(root + '/'):
            raise ValueError('External storage row escapes its component root')
        if _storage_overlap(path, scope):
            raise ValueError('External storage row overlaps the measured current scope')
        for field in EXTERNAL_STORAGE_METADATA:
            _storage_integer(row[field], 'external '+field, minimum=1 if field in ('inode', 'nlink') else 0)
        if row['mode'] > 0o7777:
            raise ValueError('Exact ordinary external storage permission mode required')
        if row['kind'] == 'file':
            if row['nlink'] != 1:
                raise ValueError('Sole-link authenticated external file required')
            if role != 'prospective_ledger':
                _validate_pin(row['raw_pin'])
                if row['raw_pin']['bytes'] != row['bytes']:
                    raise ValueError('Authenticated historical raw pin and storage bytes differ')
        identity = (row['device'], row['inode'])
        if identity in existing or identity in seen:
            raise ValueError('External storage overlaps measured or duplicate inode allocation')
        seen.add(identity); by_role[role].append(row)
    for component in external_inventory['components']:
        role = component['role']; rows = by_role[role]; root = roots[role]
        names = {row['path']: row for row in rows}
        if root not in names or names[root]['kind'] != 'directory':
            raise ValueError('Every external component requires its observed root directory')
        for path in names:
            if path != root and (str(Path(path).parent) not in names
                    or names[str(Path(path).parent)]['kind'] != 'directory'):
                raise ValueError('Complete external storage directory ancestry required')
        if role.endswith('ledger') and (len(rows) != 2
                or sum(row['kind'] == 'file' and str(Path(row['path']).parent) == root for row in rows) != 1):
            raise ValueError('Exactly one directory and direct spend file required for each ledger')
        for field, source in (('logical_bytes', 'bytes'), ('allocated_bytes', 'allocated_bytes')):
            if (_storage_integer(component[field], 'component '+field)
                    != sum(row[source] for row in rows)):
                raise ValueError('External component storage total differs from its exact rows')
        if _storage_integer(component['entry_count'], 'component entries', minimum=1) != len(rows):
            raise ValueError('External component entry count differs from its exact rows')
    if (_storage_integer(external_inventory['entry_count'], 'external entries', minimum=1)
            != len(external_inventory['rows'])):
        raise ValueError('External storage entry count differs from its exact rows')
    if max(external_inventory['logical_bytes'], external_inventory['allocated_bytes']) > LIMITS['run_storage_bytes']:
        raise ValueError('Original 1536MiB external storage bound exceeded')
    return external_inventory


def _storage_integer(value, label, *, minimum=0):
    value = _integer(value, label, minimum=minimum)
    if value > (1 << 63) - 1:
        raise ValueError('Bounded observed storage integer required: ' + label)
    return value


def _storage_absolute(value):
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or len(value.encode('utf-8')) > 4096
            or any(part in ('', '.', '..') for part in value[1:].split('/'))
            or len(value[1:].split('/')) > 64):
        raise ValueError('Canonical bounded absolute external storage path required')
    return value


def _storage_overlap(first, second):
    return first == second or first.startswith(second + '/') or second.startswith(first + '/')


def _ledger_inventory_pin(inventory):
    return hashlib.sha256(canonical(inventory)).hexdigest()


def observe_authenticated_ledger_storage(scope):
    """Read-only live ledger observation through the independently pinned gate."""
    scope = _absolute(scope); code_root = _absolute(scope/'frozen-code')
    plan, _ = read_pinned_json(scope/'plan.json', maximum=16*MIB)
    expected = BOOTSTRAP_SOURCE_PINS[FIXTURE]
    if canonical(plan.get('code_files', {}).get(FIXTURE)) != canonical(expected):
        raise ValueError('Ledger storage fixture differs from independent bootstrap pin')
    fixture = _source_module(code_root/FIXTURE, expected, 'pinned_ledger_storage_fixture')
    observed = fixture.persistent_ledger_storage(scope, repo=code_root)
    # The adapter authenticates activation and spending evidence; this boundary
    # also checks the exact returned scope/schema contract.
    if (type(observed) is not dict or observed.get('schema') != EXTERNAL_STORAGE_SCHEMA
            or observed.get('current_control_scope') != str(scope)):
        raise ValueError('Pinned fixture returned an invalid persistent ledger observation')
    return _external_ledger_inventory({'scope': str(scope), 'rows': []}, observed)


def _match_retained_ledger(inventory, expected_sha256):
    if (type(expected_sha256) is not str or not re.fullmatch('[a-f0-9]{64}', expected_sha256)
            or _ledger_inventory_pin(inventory) != expected_sha256):
        raise ValueError('Persistent ledger storage changed after the independently retained snapshot')


def allocate_storage(inventory, *, reserved_bytes=METADATA_RESERVATION_BYTES,
        directory_reserved_bytes=DIRECTORY_RESERVATION_BYTES, external_inventory=None):
    if (type(inventory) is not dict or type(inventory.get('rows')) is not list
            or len(inventory['rows']) > MAX_INVENTORY_ENTRIES):
        raise ValueError('Bounded exact current storage inventory required')
    current_raw = canonical(inventory)
    if len(current_raw) > MAX_EXTERNAL_STORAGE_BYTES:
        raise ValueError('Bounded current storage inventory serialization exceeded')
    inventory = json.loads(current_raw)
    _validate_inventory_totals(inventory)
    _integer(reserved_bytes, 'final metadata reservation')
    _integer(directory_reserved_bytes, 'terminal directory growth reservation')
    # The reservation is a total allowance, not a duplicate of metadata already
    # materialized. Replace logical and allocated reservations independently.
    metadata = [row for row in inventory['rows'] if row['path'] in FINAL_METADATA_NAMES]
    if any(row['kind'] != 'file' for row in metadata):
        raise ValueError('Reserved terminal metadata must be ordinary files, never directories')
    external = _external_ledger_inventory(inventory, external_inventory) if external_inventory is not None else None
    external_logical = external['logical_bytes'] if external is not None else 0
    external_allocated = external['allocated_bytes'] if external is not None else 0
    metadata_logical = sum(row['bytes'] for row in metadata)
    metadata_allocated = sum(row['allocated_bytes'] for row in metadata)
    if max(metadata_logical, metadata_allocated) > reserved_bytes:
        raise ValueError('Terminal metadata exceeded its retained storage reservation')
    logical = inventory['logical_bytes'] + external_logical + reserved_bytes - metadata_logical + directory_reserved_bytes
    allocated = inventory['allocated_bytes'] + external_allocated + reserved_bytes - metadata_allocated + directory_reserved_bytes
    cases = []
    for ordinal in range(8):
        prefix = f'cases/case{ordinal:02d}'
        rows = [row for row in inventory['rows'] if row['path'] == prefix or row['path'].startswith(prefix+'/')]
        if not rows or rows[0]['kind'] != 'directory':
            raise ValueError('Exactly eight retained case directory roots required')
        cases.append({'ordinal': ordinal, 'logical_bytes': sum(row['bytes'] for row in rows),
            'allocated_bytes': sum(row['allocated_bytes'] for row in rows)})
    # A ninth root is never silently counted as unassigned administrative work.
    for row in inventory['rows']:
        if row['path'].startswith('cases/case') and len(row['path'].split('/')) == 2:
            if row['path'] not in {f'cases/case{ordinal:02d}' for ordinal in range(8)}:
                raise ValueError('Unexpected retained case directory identity')
    shared_logical = logical - sum(row['logical_bytes'] for row in cases)
    shared_allocated = allocated - sum(row['allocated_bytes'] for row in cases)
    for row in cases:
        row['shared_logical_bytes_attributed'] = shared_logical/8
        row['shared_allocated_bytes_attributed'] = shared_allocated/8
        row['complete_logical_bytes'] = row['logical_bytes'] + shared_logical/8
        row['complete_allocated_bytes'] = row['allocated_bytes'] + shared_allocated/8
        if max(row['complete_logical_bytes'], row['complete_allocated_bytes']) > LIMITS['case_storage_bytes']:
            raise ValueError('Original 192MiB case storage bound exceeded after shared allocation')
    if max(logical, allocated) > LIMITS['run_storage_bytes']:
        raise ValueError('Original 1536MiB whole storage bound exceeded')
    return {'whole_logical_bytes_with_remaining_reservation': logical,
        'whole_allocated_bytes_with_remaining_reservation': allocated,
        'shared_logical_bytes': shared_logical, 'shared_allocated_bytes': shared_allocated,
        'metadata_logical_bytes_present': metadata_logical,
        'metadata_allocated_bytes_present': metadata_allocated,
        'final_metadata_reservation_bytes': reserved_bytes,
        'terminal_directory_growth_reservation_bytes': directory_reserved_bytes,
        'external_ledger_storage_included': external is not None,
        'external_ledger_logical_bytes': external_logical,
        'external_ledger_allocated_bytes': external_allocated,
        'external_ledger_inventory_sha256': _ledger_inventory_pin(external) if external is not None else None,
        'external_ledger_storage': external,
        'external_ledger_allocation': 'one eighth of every historical scope and historical/prospective ledger byte' if external is not None else None,
        'cases': cases}


def _worker_cases(worker):
    if worker.get('status') != 'PENDING_FINAL_MEASUREMENT_JOIN':
        raise ValueError('Worker must retain pending status until independent final measurement')
    for key, expected in AUTHORITY.items():
        if canonical(worker.get(key)) != canonical(expected):
            raise ValueError('Disabled scientific/external authority changed: '+key)
    rows = worker.get('cases')
    if type(rows) is not list or len(rows) != 8:
        raise ValueError('Exactly eight independently closed pending cases required')
    result = []; totals = {'calls': 0, 'request_bytes': 0, 'response_bytes': 0}
    for ordinal, row in enumerate(rows):
        if type(row) is not dict or type(row.get('ordinal')) is not int or row['ordinal'] != ordinal:
            raise ValueError('Exact fixed case ordinal sequence required')
        if row.get('source_case_id') != NAMESPACE + f'/case{ordinal:02d}':
            raise ValueError('Case identity does not bind the prospective eight-input namespace')
        exclusive = _seconds(row.get('preparation_through_lossless_seconds'), 'case generation/proof phase')
        exclusive += _seconds(row.get('continuous_verifier_append_seconds'), 'case verifier append')
        record = {'ordinal': ordinal, 'source_case_id': row['source_case_id'],
            'exclusive_seconds': exclusive}
        for key, cap in (('calls', 'case_calls'), ('request_bytes', 'case_request_bytes'), ('response_bytes', 'case_response_bytes')):
            amount = _integer(row.get(key), key)
            if amount > LIMITS[cap]: raise ValueError('Original per-case '+key+' cap exceeded')
            totals[key] += amount; record[key] = amount
        result.append(record)
    for key, cap in (('calls', 'run_calls'), ('request_bytes', 'run_request_bytes'), ('response_bytes', 'run_response_bytes')):
        if totals[key] > LIMITS[cap]: raise ValueError('Original cumulative '+key+' cap exceeded')
    _worker_material_peak(worker)
    return result, totals


def _worker_material_peak(worker):
    """Optional legacy fields never become invented complete RSS evidence."""
    key = 'maximum_individual_material_process_rss_bytes'
    fields = []
    complete = key in worker
    if key in worker: fields.append(_integer(worker[key], 'whole worker material RSS', minimum=1))
    for row in worker['cases']:
        if key in row: fields.append(_integer(row[key], 'case material RSS', minimum=1))
        else: complete = False
    peak = max(fields, default=0)
    if peak > LIMITS['rss_bytes']:
        raise ValueError('Original 512MiB material worker/case process RSS bound exceeded')
    return peak, complete


def allocate_elapsed(cases, elapsed_seconds):
    elapsed = _seconds(elapsed_seconds, 'admission-inclusive complete measured elapsed')
    exclusive = sum(row['exclusive_seconds'] for row in cases)
    if exclusive > elapsed + 0.000001:
        raise ValueError('Case phases exceed the independent complete measured interval')
    shared = max(0.0, elapsed-exclusive)
    rows = []
    for case in cases:
        row = {**case, 'shared_seconds_attributed': shared/8,
            'complete_case_seconds': case['exclusive_seconds']+shared/8}
        if row['complete_case_seconds'] > LIMITS['case_seconds']:
            raise ValueError('Original 600-second case bound exceeded including shared finalization')
        rows.append(row)
    if elapsed > LIMITS['run_seconds']:
        raise ValueError('Original 4800-second whole measured scope bound exceeded')
    return {'complete_measured_elapsed_seconds': elapsed,
        'shared_seconds': shared, 'allocation': 'one eighth of every non-case interval', 'cases': rows}


def _observation(receipt, expected_argv, *, expected_identity=None):
    if receipt.get('schema') != OBSERVATION_SCHEMA:
        raise ValueError('Exact independent process observation schema required')
    if type(expected_argv) is not list or len(expected_argv) < 5 or expected_argv[1:4] != ['-I', '-S', '-B']:
        raise ValueError('Exact isolated interpreter argv required for the control measurement chain')
    if canonical(receipt.get('observed_argv')) != canonical(expected_argv):
        raise ValueError('Observed interpreter argv differs from the independently expected argv')
    if canonical(receipt.get('child_environment')) != canonical(ENVIRONMENT):
        raise ValueError('Exact complete minimal child environment required')
    for key in ('includes_entire_child_lifetime', 'reported_identity_verified', 'direct_child_reaped'):
        if receipt.get(key) is not True: raise ValueError('Independent terminated child observation missing: '+key)
    if receipt.get('observer_source') != 'independent_parent_procfs_and_kernel_wait4':
        raise ValueError('Independent procfs and kernel wait4 observation required')
    if type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0 or receipt.get('reason') is not None:
        raise ValueError('Measured child did not terminate successfully')
    identity = receipt.get('bound_child_identity')
    if type(identity) is not dict: raise ValueError('Independent complete launched child identity required')
    for key in ('procfs_pid', 'namespace_pid'):
        _integer(identity.get(key), 'child '+key, minimum=1)
    if type(identity.get('procfs_start_ticks')) is not str or not identity['procfs_start_ticks'].isdigit():
        raise ValueError('Stable kernel process start ticks required')
    if expected_identity is not None:
        for key in ('procfs_pid', 'namespace_pid'):
            if canonical(identity.get(key)) != canonical(expected_identity.get(key)):
                raise ValueError('Observation did not bind the retained independent child identity')
    start = _integer(receipt.get('monotonic_start_ns'), 'observer start', minimum=1)
    end = _integer(receipt.get('monotonic_end_ns'), 'observer end', minimum=1)
    if end < start: raise ValueError('Monotonic observation interval reversed')
    if end > time.monotonic_ns():
        raise ValueError('Observation cannot claim termination in the future')
    peak = max(_integer(receipt.get('peak_rss_bytes'), 'child RSS', minimum=1),
        _integer(receipt.get('observer_self_kernel_peak_rss_bytes'), 'observer RSS', minimum=1))
    executable = receipt.get('child_executable_pin')
    if type(executable) is not dict or executable.get('path') != str(Path(expected_argv[0]).resolve()):
        raise ValueError('Observed interpreter executable identity differs')
    _validate_pin({key: executable[key] for key in ('bytes', 'sha256')})
    if canonical(executable) != canonical(_interpreter_pin(expected_argv[0])):
        raise ValueError('Observed interpreter executable pin differs from the actual installed runtime')
    return start, end, peak


_ESCAPE_OPERATIONS = ['clone-namespace-flags', 'clone3', 'io-uring-setup',
    'process-vm-read', 'process-vm-write', 'ptrace', 'setns', 'unshare']


def _subreaper_terminal(receipt):
    """Verify the exact bounded descendant-wait contract, not a lone label."""
    if (receipt.get('status') != 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE'
            or type(receipt.get('root_exit_code')) is not int or receipt['root_exit_code'] != 0
            or receipt.get('sole_wait4_owner') is not True
            or receipt.get('subreaper_set_and_get_verified') is not True
            or receipt.get('subreaper_scope_reaped_to_echild') is not True):
        raise ValueError('Dedicated control supervisor did not reach its checked terminal ECHILD scope')
    complete = receipt.get('complete_descendant_wait_chain_verified') is True
    if complete and (receipt.get('descendant_wait_chain_scope') !=
            'INHERITED_SECCOMP_GUARD_AND_LINUX_SUBREAPER_TO_ECHILD'
            or receipt.get('child_escape_guard_installed_before_exec') is not True
            or receipt.get('child_escape_guard_no_new_privileges') is not True
            or receipt.get('child_escape_guard_seccomp_filter') is not True
            or receipt.get('child_escape_guard_denied_operations') != _ESCAPE_OPERATIONS):
        raise ValueError('Complete descendant label lacks the exact inherited escape guard contract')
    return complete


def capture_pending_measurements(scope, *, admission_start_monotonic_ns,
        expected_runner_argv, worker_result_path=None, runner_observation_path=None,
        subreaper_receipt_path=None):
    """Read only, before driver termination; output can only be pending."""
    scope = _absolute(scope)
    worker_path = Path(worker_result_path or scope/'worker-result.json')
    runner_path = Path(runner_observation_path or scope/RUNNER_OBSERVATION_NAME)
    subreaper_path = Path(subreaper_receipt_path or scope/'whole-control-supervisor/subreaper-receipt.json')
    for path in (worker_path, runner_path, subreaper_path): _relative(scope, path)
    worker, worker_pin = read_pinned_json(worker_path)
    runner, runner_pin = read_pinned_json(runner_path)
    subreaper, subreaper_pin = read_pinned_json(subreaper_path)
    cases, totals = _worker_cases(worker)
    material_peak, complete_material_peaks = _worker_material_peak(worker)
    _, runner_end, peak = _observation(runner, expected_runner_argv,
        expected_identity=subreaper.get('supervisor_identity'))
    complete_descendant_chain = _subreaper_terminal(subreaper)
    peak = max(peak, material_peak, _integer(subreaper.get('maximum_individual_process_rss_bytes'), 'supervisor RSS', minimum=1),
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    if peak > LIMITS['rss_bytes']: raise ValueError('Original 512MiB maximum individual process RSS bound exceeded')
    start = _integer(admission_start_monotonic_ns, 'independently retained admission start', minimum=1)
    inventory = storage_inventory(scope)
    external = None if runner.get('synthetic_test_fixture') is True else observe_authenticated_ledger_storage(scope)
    if external is None and runner.get('synthetic_test_fixture') is not True:
        raise ValueError('Authenticated persistent ledger storage is required for a production snapshot')
    storage = allocate_storage(inventory, external_inventory=external)
    completed = time.monotonic_ns()
    if not start <= runner_end <= completed:
        raise ValueError('Whole measured interval does not contain the independently reaped runner')
    timing = allocate_elapsed(cases, (completed-start)/1e9)
    return {'schema': SCHEMA+'-pending', 'namespace': NAMESPACE,
        'status': 'PENDING_FINAL_MEASUREMENT_JOIN', 'scope': str(scope),
        'admission_start_monotonic_ns': start, 'snapshot_completed_monotonic_ns': completed,
        'worker_result_path': str(worker_path), 'worker_result_pin': worker_pin,
        'runner_observation_path': str(runner_path), 'runner_observation_pin': runner_pin,
        'subreaper_receipt_path': str(subreaper_path), 'subreaper_receipt_pin': subreaper_pin,
        'expected_runner_argv': expected_runner_argv, 'base_inventory_sha256': _base_inventory_pin(inventory),
        'final_metadata_names': list(FINAL_METADATA_NAMES),
        'storage_before_snapshot_fsync_with_final_reservation': storage,
        'timing_before_snapshot_fsync': timing, 'case_operations': totals,
        'maximum_individual_process_rss_bytes_before_driver_termination': peak,
        'complete_material_worker_and_case_rss_fields_present': complete_material_peaks,
        'snapshot_and_driver_termination_independently_observed': False,
        'complete_descendant_wait_chain_verified': complete_descendant_chain,
        'complete_resource_measurement_join_qualified': False,
        'complete_runtime_closure_qualified': False, 'exact_native_or_http_host_join_qualified': False,
        'limitations': list(LIMITATIONS), **AUTHORITY}


def join_final_measurements(scope, *, expected_pending_pin, expected_driver_observation_pin,
        expected_driver_argv, expected_runner_argv, expected_admission_start_monotonic_ns,
        pending_path=None, driver_observation_path=None):
    """Read-only final disposition after externally observed driver termination.

    The exact pins, argv and initial stamp must come from the integrating
    independent parent. Supplying labels copied from receipt JSON provides no
    independent provenance. This API never persists its returned disposition.
    """
    result = {'schema': SCHEMA, 'status': 'PENDING_FINAL_MEASUREMENT_JOIN',
        'complete_resource_measurement_join_qualified': False,
        'complete_runtime_closure_qualified': False, 'exact_native_or_http_host_join_qualified': False,
        'final_reporting_process_termination_covered': False,
        'final_disposition_persisted': False, 'limitations': list(LIMITATIONS), **AUTHORITY}
    try:
        scope = _absolute(scope)
        pending_path = Path(pending_path or scope/PENDING_NAME)
        driver_path = Path(driver_observation_path or scope/DRIVER_OBSERVATION_NAME)
        if _relative(scope, pending_path) != PENDING_NAME or _relative(scope, driver_path) != DRIVER_OBSERVATION_NAME:
            raise ValueError('Exact fixed terminal measurement evidence paths required')
        pending, pending_pin = read_pinned_json(pending_path, expected_pending_pin)
        driver, driver_pin = read_pinned_json(driver_path, expected_driver_observation_pin)
        if (pending.get('schema') != SCHEMA+'-pending' or pending.get('namespace') != NAMESPACE
                or pending.get('status') != 'PENDING_FINAL_MEASUREMENT_JOIN' or pending.get('scope') != str(scope)
                or pending.get('final_metadata_names') != list(FINAL_METADATA_NAMES)):
            raise ValueError('Exact pending measurement contract required')
        start = _integer(expected_admission_start_monotonic_ns, 'independently retained admission start', minimum=1)
        if type(pending.get('admission_start_monotonic_ns')) is not int or pending['admission_start_monotonic_ns'] != start:
            raise ValueError('Admission-inclusive start differs from independent parent stamp')
        identity, _ = read_pinned_json(scope/DRIVER_IDENTITY_NAME)
        driver_start, driver_end, peak = _observation(driver, expected_driver_argv, expected_identity=identity)
        snapshot_end = _integer(pending.get('snapshot_completed_monotonic_ns'), 'pending snapshot completion', minimum=1)
        if not start <= driver_start <= snapshot_end <= driver_end:
            raise ValueError('External driver interval does not cover admission and snapshot fsync/termination')
        if canonical(pending.get('expected_runner_argv')) != canonical(expected_runner_argv):
            raise ValueError('Pending runner argv differs from independent parent expectation')
        worker_path = Path(pending['worker_result_path']); runner_path = Path(pending['runner_observation_path'])
        subreaper_path = Path(pending['subreaper_receipt_path'])
        for path in (worker_path, runner_path, subreaper_path): _relative(scope, path)
        worker, _ = read_pinned_json(worker_path, pending['worker_result_pin'])
        runner, _ = read_pinned_json(runner_path, pending['runner_observation_pin'])
        subreaper, _ = read_pinned_json(subreaper_path, pending['subreaper_receipt_pin'])
        runner_start, runner_end, runner_peak = _observation(runner, expected_runner_argv,
            expected_identity=subreaper.get('supervisor_identity'))
        subreaper_chain_complete = _subreaper_terminal(subreaper)
        if not driver_start <= runner_start <= runner_end <= snapshot_end:
            raise ValueError('Runner termination is outside the measured driver interval')
        cases, totals = _worker_cases(worker)
        material_peak, complete_material_peaks = _worker_material_peak(worker)
        peak = max(peak, runner_peak, material_peak, _integer(subreaper.get('maximum_individual_process_rss_bytes'), 'supervisor RSS', minimum=1),
            _integer(pending.get('maximum_individual_process_rss_bytes_before_driver_termination'), 'measurement driver RSS', minimum=1),
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        if peak > LIMITS['rss_bytes']: raise ValueError('Original 512MiB maximum individual process RSS bound exceeded')
        inventory = storage_inventory(scope)
        if _base_inventory_pin(inventory) != pending.get('base_inventory_sha256'):
            raise ValueError('Retained scope changed after the driver snapshot outside reserved final metadata')
        synthetic = driver.get('synthetic_test_fixture') is True or runner.get('synthetic_test_fixture') is True
        external = None if synthetic else observe_authenticated_ledger_storage(scope)
        if not synthetic and external is None:
            raise ValueError('Authenticated persistent ledger storage is required for a production join')
        if external is not None:
            _match_retained_ledger(external, pending.get('storage_before_snapshot_fsync_with_final_reservation', {}).get('external_ledger_inventory_sha256'))
        storage = allocate_storage(inventory, external_inventory=external)
        # Time spent by this read-only external join is charged conservatively
        # too. Its future persistence/termination remains an explicit boundary.
        join_completed = time.monotonic_ns()
        elapsed = max(driver_end, join_completed)-start
        timing = allocate_elapsed(cases, elapsed/1e9)
        complete_descendant_chain = (pending.get('complete_descendant_wait_chain_verified') is True
            and subreaper_chain_complete)
        complete_join = (complete_descendant_chain
            and pending.get('complete_material_worker_and_case_rss_fields_present') is True
            and complete_material_peaks and external is not None)
        if synthetic: complete_join = complete_descendant_chain = False
        pending_reasons = []
        if synthetic: pending_reasons.append('Synthetic receipt fixtures are not execution evidence.')
        elif not complete_descendant_chain:
            pending_reasons.append('Complete descendant wait chain has not been independently verified.')
        if not complete_material_peaks:
            pending_reasons.append('Complete per-case and whole-worker material RSS fields are not available.')
        result.update({'scope': str(scope), 'expected_receipt_byte_pins_verified': True,
            'pending_pin': pending_pin, 'driver_observation_pin': driver_pin,
            'snapshot_fsync_and_driver_termination_independently_observed': True,
            'whole_admission_materialization_runner_fsync_and_driver_termination_included': True,
            'complete_descendant_wait_chain_verified': complete_descendant_chain,
            'complete_material_worker_and_case_rss_fields_present': complete_material_peaks,
            'all_original_resource_bounds_checked': True, 'reported_resource_bounds_within_original_caps': True,
            'maximum_individual_process_rss_bytes': peak, 'rss_accounting_scope': 'maximum individual process',
            'storage': storage, 'timing': timing, 'case_operations': totals,
            'persistent_ledger_storage_reobserved_and_charged': external is not None,
            'read_only_join_completed_monotonic_ns': join_completed,
            'final_metadata_storage_reserved_only': True,
            'status': 'SYNTHETIC_RESOURCE_BOUNDS_CHECKED' if synthetic else
                'OFFLINE_RESOURCE_MEASUREMENT_JOIN_PASSED' if complete_join else 'PENDING_FINAL_MEASUREMENT_JOIN',
            'complete_resource_measurement_join_qualified': complete_join,
            'pending_reasons': pending_reasons})
    except FileNotFoundError as failure:
        result['pending_reasons'] = ['Independently terminated final measurement evidence is not available: '+str(failure)]
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as failure:
        result.update({'status': 'CLOSED_FAILED', 'error': str(failure),
            'complete_resource_measurement_join_qualified': False})
    return result


def _write_durable_exclusive(path, value):
    """Write one fixed terminal artifact, fsync file and parent, then read back."""
    path = Path(path)
    if not path.is_absolute() or path.name in ('', '.', '..') or '..' in path.parts:
        raise ValueError('Canonical absolute terminal artifact path required')
    path = _absolute(path.parent)/path.name
    raw = value if isinstance(value, bytes) else canonical(value)+b'\n'
    if len(raw) > METADATA_RESERVATION_BYTES:
        raise ValueError('Terminal artifact exceeds the fixed metadata reservation')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(raw)
        while view:
            amount = os.write(fd, view)
            if amount <= 0: raise OSError('Incomplete exclusive terminal evidence write')
            view = view[amount:]
        os.fsync(fd); written = os.fstat(fd)
    finally: os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    value_read, observed = read_pinned_json(path) if not isinstance(value, bytes) else (None, {
        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    if observed != {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}:
        raise ValueError('Durable terminal artifact readback differs')
    reopened = path.stat(follow_symlinks=False)
    if (written.st_dev, written.st_ino) != (reopened.st_dev, reopened.st_ino):
        raise ValueError('Durable terminal artifact identity replaced')
    return value_read, observed


def check_final_report_material_scope(scope):
    """Read-only post-execution gate; no Git, control freshness or scope writes.

    Source selection is independently bound before compiling the fixture. Its
    gate rechecks the frozen original material runtime through the reviewed
    activation/custody chain. Copied material source remains sole-link and
    stable-byte checked, without claiming frozen inode continuity across copies.
    """
    scope = _absolute(scope); code_root = _absolute(scope/'frozen-code')
    records = {}
    for name, filename in (('plan', 'plan.json'), ('freeze', 'complete-freeze.json'),
            ('preread', 'public-preread.json'), ('activation_receipt', 'activation-receipt.json'),
            ('invocation_spending', 'invocation-spending.json')):
        records[name], _ = read_pinned_json(scope/filename, maximum=16*MIB)
    plan = records['plan']; code = plan.get('code_files', {})
    for relative, expected in BOOTSTRAP_SOURCE_PINS.items():
        if canonical(code.get(relative)) != canonical(expected):
            raise ValueError('Final writer dependency differs from independent bootstrap pin: '+relative)
        _read_pinned_source(code_root/relative, expected)
    own_path = _absolute(code_root/SELF)
    if Path(__file__).absolute() != own_path:
        raise ValueError('Final writer must execute the exact materialized source path')
    _read_pinned_source(own_path, code.get(SELF))
    material_counts = {
        'code': _verify_material_source_tree(code_root, code),
        'derived': _verify_material_source_tree(scope/'derived', plan.get('derived_code'))}
    fixture = _source_module(code_root/FIXTURE, BOOTSTRAP_SOURCE_PINS[FIXTURE],
        'pinned_final_report_fixture')
    fixture.require_execution_ready(**records, repo=code_root, execution_scope=str(scope))
    return {'material_scope_gate_rechecked_before_writer_identity': True,
        'activation_only_runtime_used_by_final_writer': False,
        'copied_material_source_files_rechecked': material_counts,
        'checks_remain_subject_to_postcheck_mutation': True,
        'scope': str(scope), 'python_path': plan['runtime_executables']['python']['path']}


def _pending_final_report_input(scope, expected_input_pin, *, tiny=False):
    scope = _absolute(scope)
    input_path = scope/FINAL_INPUT_NAME
    report_input, observed_input_pin = read_pinned_json(input_path, expected_input_pin,
        maximum=TINY_REPORT_INPUT_BYTES if tiny else MAX_EVIDENCE_BYTES)
    if (report_input.get('schema') != SCHEMA+('-tiny-final-report-input' if tiny else '-final-report-input')
            or report_input.get('scope') != str(scope)
            or report_input.get('final_reporting_process_termination_covered') is not False
            or report_input.get('final_disposition_persisted') is not False
            or type(report_input.get('complete_resource_measurement_join_qualified')) is not bool):
        raise ValueError('Exact pending final-report input contract required')
    for key, expected in AUTHORITY.items():
        if canonical(report_input.get(key)) != canonical(expected):
            raise ValueError('Disabled authority changed in terminal input: '+key)
    if tiny:
        fields = {'schema', 'scope', 'status', 'complete_resource_measurement_join_qualified',
            'final_reporting_process_termination_covered', 'final_disposition_persisted',
            'tiny_engineering_probe_only', *AUTHORITY}
        if (set(report_input) != fields or report_input.get('tiny_engineering_probe_only') is not True
                or report_input['complete_resource_measurement_join_qualified'] is not False
                or report_input.get('status') != 'TINY_ENGINEERING_REPORT_PROBE'):
            raise ValueError('Exact unqualified tiny engineering report input required')
    return report_input, observed_input_pin


def _persist_checked_final_report(scope, report_input, observed_input_pin, *, mode, gate):
    _write_durable_exclusive(scope/FINAL_WRITER_IDENTITY_NAME, {
        'procfs_pid': int(os.readlink('/proc/self')), 'namespace_pid': os.getpid(),
        'schema': SCHEMA+'-final-report-writer-identity'})
    report = {**report_input, 'schema': SCHEMA+'-persisted-final-report',
        'status': ('TINY_ENGINEERING_REPORT_PROBE_PENDING_OBSERVATION' if mode == 'TINY_ENGINEERING_PROBE' else
            'OFFLINE_RESOURCE_MEASUREMENT_JOIN_PASSED_REPORT_WRITER_PENDING_OBSERVATION'
            if report_input['complete_resource_measurement_join_qualified'] else
            'PENDING_FINAL_MEASUREMENT_JOIN_REPORT_WRITER_PENDING_OBSERVATION'),
        'final_report_input_pin': observed_input_pin,
        'report_writer_fsync_completed_before_return': True,
        'report_writer_termination_observation_required': True,
        'final_reporting_process_termination_covered': False,
        'final_disposition_persisted': True, 'report_writer_mode': mode,
        'material_scope_gate': gate,
        'real_control_execution_verified_by_report_writer': False}
    if mode == 'TINY_ENGINEERING_PROBE' and len(canonical(report))+1 > TINY_REPORT_INPUT_BYTES:
        raise ValueError('Tiny engineering report exceeds fixed byte bound')
    _, report_pin = _write_durable_exclusive(scope/FINAL_NAME, report)
    return report, report_pin


def persist_final_report(scope, *, expected_input_pin):
    """Activation-bound writer; material custody precedes its first write."""
    scope = _absolute(scope)
    report_input, observed_input_pin = _pending_final_report_input(scope, expected_input_pin)
    gate = check_final_report_material_scope(scope)
    external = observe_authenticated_ledger_storage(scope)
    disposition = report_input.get('independent_driver_measurement_disposition', {})
    _match_retained_ledger(external, disposition.get('storage', {}).get('external_ledger_inventory_sha256'))
    storage = allocate_storage(storage_inventory(scope), external_inventory=external)
    gate.update({'persistent_ledger_storage_reobserved_and_charged': True,
        'storage_before_report_writer_identity_with_final_reservation': storage})
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError('Actual isolated no-site no-bytecode final-report writer required')
    if dict(os.environ) != ENVIRONMENT:
        raise RuntimeError('Exact complete minimal final-report writer environment required')
    expected_argv = [gate['python_path'], '-I', '-S', '-B', str(scope/'frozen-code'/SELF),
        '--persist-final-report', '--scope', str(scope), '--input-bytes', str(expected_input_pin['bytes']),
        '--input-sha256', expected_input_pin['sha256']]
    if list(sys.orig_argv) != expected_argv:
        raise RuntimeError('Exact original material final-report writer interpreter argv required')
    return _persist_checked_final_report(scope, report_input, observed_input_pin,
        mode='ACTIVATION_BOUND_MATERIAL_SCOPE', gate=gate)


def persist_tiny_final_report_probe(scope, *, expected_input_pin):
    """Distinct bounded engineering path; never admits or qualifies a control."""
    started = time.monotonic(); scope = _absolute(scope)
    report_input, observed_input_pin = _pending_final_report_input(scope, expected_input_pin, tiny=True)
    inventory = storage_inventory(scope)
    if max(inventory['logical_bytes'], inventory['allocated_bytes']) + 2*TINY_REPORT_INPUT_BYTES + DIRECTORY_RESERVATION_BYTES > TINY_REPORT_SCOPE_BYTES:
        raise ValueError('Tiny engineering report scope exceeds fixed storage bound')
    if time.monotonic()-started > TINY_REPORT_SECONDS:
        raise RuntimeError('Tiny engineering report preparation deadline exceeded')
    report, pin = _persist_checked_final_report(scope, report_input, observed_input_pin,
        mode='TINY_ENGINEERING_PROBE', gate={'material_scope_gate_rechecked_before_writer_identity': False,
            'tiny_engineering_probe_only': True, 'real_control_or_runtime_custody_qualified': False})
    inventory = storage_inventory(scope)
    if max(inventory['logical_bytes'], inventory['allocated_bytes']) > TINY_REPORT_SCOPE_BYTES:
        raise ValueError('Tiny engineering report scope exceeded fixed storage bound after fsync')
    if time.monotonic()-started > TINY_REPORT_SECONDS:
        raise RuntimeError('Tiny engineering report fsync deadline exceeded')
    return report, pin


def join_final_report_lifetime(scope, *, expected_input_pin, expected_report_pin,
        expected_writer_observation_pin, expected_writer_argv):
    """Read-only join of a durable report with its writer's full wait4 lifetime."""
    scope = _absolute(scope)
    tiny = '--tiny-final-report-writer' in expected_writer_argv
    report_input, input_pin = _pending_final_report_input(scope, expected_input_pin, tiny=tiny)
    report, report_pin = read_pinned_json(scope/FINAL_NAME, expected_report_pin,
        maximum=TINY_REPORT_INPUT_BYTES if tiny else MAX_EVIDENCE_BYTES)
    observation, observation_pin = read_pinned_json(
        scope/FINAL_WRITER_OBSERVATION_NAME, expected_writer_observation_pin)
    identity, identity_pin = read_pinned_json(scope/FINAL_WRITER_IDENTITY_NAME)
    writer_start, writer_end, writer_peak = _observation(
        observation, expected_writer_argv, expected_identity=identity)
    synthetic = observation.get('synthetic_test_fixture') is True
    if synthetic and not tiny:
        raise ValueError('Synthetic writer observations cannot qualify a material final report')
    if tiny:
        inventory = storage_inventory(scope)
        if max(inventory['logical_bytes'], inventory['allocated_bytes']) > TINY_REPORT_SCOPE_BYTES:
            raise ValueError('Tiny engineering report retained scope exceeds fixed storage bound')
        if (writer_end-writer_start)/1e9 > TINY_REPORT_SECONDS:
            raise ValueError('Tiny engineering report observed lifetime exceeds fixed deadline')
    if (report.get('schema') != SCHEMA+'-persisted-final-report'
            or report.get('scope') != str(scope)
            or report.get('final_report_input_pin') != input_pin
            or report.get('report_writer_fsync_completed_before_return') is not True
            or report.get('report_writer_termination_observation_required') is not True
            or report.get('final_disposition_persisted') is not True
            or report.get('final_reporting_process_termination_covered') is not False):
        raise ValueError('Exact persisted final report contract required')
    expected_mode = 'TINY_ENGINEERING_PROBE' if tiny else 'ACTIVATION_BOUND_MATERIAL_SCOPE'
    if report.get('report_writer_mode') != expected_mode:
        raise ValueError('Observed writer entrypoint and persisted mode differ')
    if tiny and (report.get('tiny_engineering_probe_only') is not True
            or report.get('complete_resource_measurement_join_qualified') is not False
            or report.get('real_control_execution_verified_by_report_writer') is not False):
        raise ValueError('Tiny engineering writer cannot qualify an actual control')
    for key in report_input:
        if (key not in ('schema', 'status', 'final_disposition_persisted')
                and canonical(report.get(key)) != canonical(report_input[key])):
            raise ValueError('Persisted final report differs from pinned input: '+key)
    if writer_peak > LIMITS['rss_bytes']:
        raise ValueError('Original 512MiB report-writer process RSS bound exceeded')
    storage = None
    if not tiny:
        external = observe_authenticated_ledger_storage(scope)
        disposition = report_input.get('independent_driver_measurement_disposition', {})
        _match_retained_ledger(external, disposition.get('storage', {}).get('external_ledger_inventory_sha256'))
        storage = allocate_storage(storage_inventory(scope), external_inventory=external)
    return {**report,
        'status': ('SYNTHETIC_TINY_ENGINEERING_REPORT_WRITER_FIXTURE' if synthetic else
            'TINY_ENGINEERING_REPORT_PROBE_WRITER_OBSERVED' if tiny else 'OFFLINE_RESOURCE_MEASUREMENT_JOIN_PASSED'
            if report['complete_resource_measurement_join_qualified'] else
            'PENDING_FINAL_MEASUREMENT_JOIN'),
        'persisted_final_report_pin': report_pin,
        'final_report_writer_identity_pin': identity_pin,
        'final_report_writer_observation_pin': observation_pin,
        'final_report_writer_interval': {'monotonic_start_ns': writer_start,
            'monotonic_end_ns': writer_end, 'peak_rss_bytes': writer_peak},
        'outer_report_fsync_and_termination_independently_observed': not synthetic,
        'final_report_observation_scope': 'tiny_engineering_probe_writer_only' if tiny else 'activation_bound_material_report_writer',
        'final_reporting_process_termination_covered': not synthetic,
        'synthetic_report_writer_observation_fixture': synthetic,
        'final_disposition_persisted': True,
        'terminal_observer_own_future_termination_covered': False,
        **({'persistent_ledger_storage_reobserved_and_charged_after_writer_termination': True,
            'storage_after_report_writer_lifetime_with_final_reservation': storage} if not tiny else {})}


def _material_directory_fd(path):
    """Open each existing directory component without following an alias."""
    path = _absolute(path)
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:]:
            parent_before = os.fstat(directory)
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                if (_identity(named) != _identity(os.fstat(child))
                        or _identity(parent_before) != _identity(os.fstat(directory))):
                    raise ValueError('Materialized source directory changed during open')
            except BaseException:
                os.close(child); raise
            os.close(directory); directory = child
        return directory
    except BaseException:
        os.close(directory); raise


def _verify_material_source_tree(root, pins):
    """Recheck an exact bounded copied source tree, including empty directories."""
    if type(pins) is not dict or not pins or len(pins) > MAX_MATERIAL_SOURCE_FILES:
        raise ValueError('Bounded nonempty exact material source pin map required')
    expected_directories = set()
    for relative, expected in pins.items():
        if (type(relative) is not str or not relative or len(relative) > 4096
                or len(relative.encode('utf-8')) > 4096 or relative.startswith('/')
                or '\\' in relative or re.search(r'[\x00-\x1f\x7f]', relative)
                or any(name in ('', '.', '..') for name in relative.split('/'))):
            raise ValueError('Canonical relative material source path required')
        _validate_pin(expected)
        if expected['bytes'] > 2*MIB:
            raise ValueError('Bounded material source byte pin required')
        parts = relative.split('/')
        if any(len(name.encode('utf-8')) > 255 for name in parts):
            raise ValueError('Bounded material source path component required')
        if len(parts) > 33:
            raise ValueError('Bounded material source tree depth exceeded')
        expected_directories.update('/'.join(parts[:count]) for count in range(1, len(parts)))
    root = _absolute(root); directory = _material_directory_fd(root)
    found = set(); directories = set(); visited = 0
    def walk(fd, prefix, depth):
        nonlocal visited
        if depth > 32: raise ValueError('Bounded material source tree depth exceeded')
        before = os.fstat(fd); names = []
        with os.scandir(fd) as entries:
            for entry in entries:
                visited += 1
                if visited > len(pins)+len(expected_directories):
                    raise ValueError('Bounded material source inventory exceeded')
                names.append(entry.name)
        for name in sorted(names):
            relative = prefix+name
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(named.st_mode):
                if relative not in expected_directories:
                    raise ValueError('Material source directory inventory differs')
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if _identity(named) != _identity(os.fstat(child)):
                        raise ValueError('Materialized source directory changed during inventory')
                    walk(child, relative+'/', depth+1)
                    if _identity(named) != _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)):
                        raise ValueError('Named material source directory changed during inventory')
                finally: os.close(child)
                directories.add(relative)
            elif stat.S_ISREG(named.st_mode) and named.st_nlink == 1:
                if relative not in pins:
                    raise ValueError('Material source file inventory differs')
                _read_pinned_source(name, pins[relative], directory_fd=fd)
                found.add(relative)
            else:
                raise ValueError('Material source alias or special file refused')
        if _identity(before) != _identity(os.fstat(fd)):
            raise ValueError('Materialized source directory changed during inventory')
    try:
        walk(directory, '', 0)
        reopened = _material_directory_fd(root)
        try:
            if _identity(os.fstat(directory)) != _identity(os.fstat(reopened)):
                raise ValueError('Material source root replaced during inventory')
        finally: os.close(reopened)
    finally: os.close(directory)
    if found != set(pins) or directories != expected_directories:
        raise ValueError('Exact material source file/directory inventory differs')
    return len(found)


def _read_pinned_source(path, expected_pin, *, directory_fd=None):
    path = _absolute(path) if directory_fd is None else path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 2*MIB:
            raise ValueError('Bounded pinned source implementation required')
        _validate_pin(expected_pin)
        if before.st_size != expected_pin['bytes']:
            raise ValueError('Pinned source size differs from independent bootstrap pin')
        chunks = []; remaining = expected_pin['bytes']+1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk: break
            chunks.append(chunk); remaining -= len(chunk)
        raw = b''.join(chunks)
        named = os.stat(path, dir_fd=directory_fd, follow_symlinks=False)
        if _identity(before) != _identity(os.fstat(fd)) or _identity(named) != _identity(before):
            raise ValueError('Pinned implementation changed during read')
    finally: os.close(fd)
    if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != expected_pin:
        raise ValueError('Supplied source differs from independent measurement-driver bootstrap pin')
    return raw


def _source_module(path, expected_pin, name):
    # Compile the actual bounded checked bytes; never import repository bytecode.
    raw = _read_pinned_source(path, expected_pin)
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def check_admitted_measurement_driver(bundle_path, *, expected_bundle_sha256):
    """No side effects; selects only the fixed control supervisor role."""
    if type(expected_bundle_sha256) is not str or not re.fullmatch('[a-f0-9]{64}', expected_bundle_sha256):
        raise ValueError('Independently retained exact bundle SHA256 required')
    bundle, observed = read_pinned_json(bundle_path, maximum=16*MIB)
    if observed['sha256'] != expected_bundle_sha256:
        raise ValueError('Admission bundle differs from independent parent digest')
    code = bundle['plan']['code_files']; root = _absolute(bundle['code_root'])
    for relative, expected in BOOTSTRAP_SOURCE_PINS.items():
        if canonical(code.get(relative)) != canonical(expected):
            raise ValueError('Supplied driver dependency differs from independent bootstrap pin: '+relative)
    _read_pinned_source(Path(__file__).resolve(), code.get(SELF))
    supervisor = _source_module(root/SUPERVISOR, BOOTSTRAP_SOURCE_PINS[SUPERVISOR], 'pinned_control_supervisor')
    checked, fixture = supervisor.check_admitted_worker(bundle_path, role='control', ordinal=None,
        expected_bundle_sha256=expected_bundle_sha256)
    scope = _absolute(checked['worker_scope'])
    if checked['receipt_scope'] != str(scope/'whole-control-supervisor'):
        raise ValueError('Fixed whole-control supervisor scope required')
    return checked, fixture


def parse_driver_completion(raw, *, scope, expected_bundle_sha256, expected_runner_argv_prefix):
    """Bind dynamic metadata to independently captured fixed-driver stdout.

    Parent must capture this bounded output from its independently pinned and
    identity-checked driver. It may not read it from a driver-selected file.
    """
    if type(raw) is not bytes or not raw.endswith(b'\n') or len(raw) > 65536 or raw.count(b'\n') != 1:
        raise ValueError('Exactly one bounded independently captured driver completion line required')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate driver completion property rejected')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if type(value) is not dict or set(value) != {'schema', 'scope', 'admission_bundle_sha256',
            'pending_pin', 'runner_argv'} or value['schema'] != SCHEMA+'-driver-completion':
        raise ValueError('Exact fixed driver completion contract required')
    if value['scope'] != str(Path(scope).absolute()) or value['admission_bundle_sha256'] != expected_bundle_sha256:
        raise ValueError('Completion does not bind the independent parent scope and admission digest')
    _validate_pin(value['pending_pin'])
    argv = value['runner_argv']
    if (type(argv) is not list or any(type(item) is not str for item in argv)
            or len(argv) != len(expected_runner_argv_prefix)+2
            or argv[:-2] != expected_runner_argv_prefix or argv[-2] != '--seconds'):
        raise ValueError('Fixed runner argv differs from independent parent prefix')
    seconds = _seconds(float(argv[-1]), 'driver remaining deadline')
    if not 0 < seconds <= LIMITS['run_seconds']:
        raise ValueError('Driver remaining deadline exceeds original scope bound')
    return value


def run_admitted_measurement_driver(bundle_path, scope, *, expected_bundle_sha256,
        admission_start_monotonic_ns):
    """Dedicated fixed-role driver; closed before any mkdir/write/Popen."""
    checked, fixture = check_admitted_measurement_driver(bundle_path,
        expected_bundle_sha256=expected_bundle_sha256)
    if str(Path(scope).absolute()) != checked['worker_scope']:
        raise ValueError('Exact admission-bound whole-control scope required')
    fixture.require_execution_ready(**checked['activation_evidence'])
    expected_driver_argv = [checked['argv'][0], '-I', '-S', '-B',
        str(Path(checked['worker_scope'])/'frozen-code'/SELF),
        '--admitted-whole-control-driver', '--admission-bundle', checked['bundle_path'],
        '--bundle-sha256', expected_bundle_sha256, '--scope', checked['worker_scope'],
        '--admission-start-monotonic-ns', str(admission_start_monotonic_ns)]
    if list(sys.orig_argv) != expected_driver_argv:
        raise RuntimeError('Exact original measurement-driver interpreter argv required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError('Actual isolated no-site no-bytecode measurement driver required')
    if dict(os.environ) != ENVIRONMENT:
        raise RuntimeError('Exact complete minimal measurement-driver environment required')
    start = _integer(admission_start_monotonic_ns, 'parent admission start', minimum=1)
    now = time.monotonic_ns()
    if not start <= now or now-start >= LIMITS['run_seconds']*1e9:
        raise RuntimeError('Original whole-control admission-inclusive deadline already exceeded')
    scope = _absolute(scope)
    fixture.identity(scope/DRIVER_IDENTITY_NAME)
    argv = [checked['argv'][0], '-I', '-S', '-B', str(Path(checked['worker_scope'])/'frozen-code'/SUPERVISOR),
        '--admitted-worker', '--worker-role', 'control', '--admission-bundle', checked['bundle_path'],
        '--bundle-sha256', expected_bundle_sha256, '--scope', checked['receipt_scope'],
        '--seconds', str((start+int(LIMITS['run_seconds']*1e9)-time.monotonic_ns())/1e9)]
    fixture.observe_process(argv, scope, 'whole-control-supervisor',
        Path(checked['receipt_scope'])/'supervisor-identity.json', deadline=start/1e9+LIMITS['run_seconds'])
    pending = capture_pending_measurements(scope, admission_start_monotonic_ns=start,
        expected_runner_argv=argv)
    pending.update({'measurement_driver_argv': list(sys.orig_argv),
        'admission_bundle_sha256': expected_bundle_sha256,
        'independently_bootstrapped_dispatch_sources': BOOTSTRAP_SOURCE_PINS})
    if len(canonical(pending))+1 > METADATA_RESERVATION_BYTES:
        raise RuntimeError('Bounded pending resource snapshot storage reservation exceeded')
    fixture.write(scope/PENDING_NAME, pending)
    completion = {'schema': SCHEMA+'-driver-completion', 'scope': str(scope),
        'admission_bundle_sha256': expected_bundle_sha256,
        'pending_pin': fixture.pin(scope/PENDING_NAME), 'runner_argv': argv}
    raw = canonical(completion)+b'\n'
    if len(raw) > 65536: raise RuntimeError('Bounded driver completion output exceeded')
    sys.stdout.buffer.write(raw); sys.stdout.buffer.flush()
    # The parent observer measures this write/fsync, any final exception and
    # dedicated driver termination. No successful disposition is written here.
    return pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--admitted-whole-control-driver', action='store_true')
    modes.add_argument('--persist-final-report', action='store_true')
    modes.add_argument('--tiny-final-report-writer', action='store_true')
    parser.add_argument('--admission-bundle')
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--scope', required=True)
    parser.add_argument('--admission-start-monotonic-ns', type=int)
    parser.add_argument('--input-bytes', type=int)
    parser.add_argument('--input-sha256')
    args = parser.parse_args()
    if args.admitted_whole_control_driver:
        if (args.admission_bundle is None or args.bundle_sha256 is None
                or args.admission_start_monotonic_ns is None
                or args.input_bytes is not None or args.input_sha256 is not None):
            parser.error('Exact admitted measurement-driver arguments required')
        run_admitted_measurement_driver(args.admission_bundle, args.scope,
            expected_bundle_sha256=args.bundle_sha256,
            admission_start_monotonic_ns=args.admission_start_monotonic_ns)
    else:
        if (args.input_bytes is None or args.input_sha256 is None
                or args.admission_bundle is not None or args.bundle_sha256 is not None
                or args.admission_start_monotonic_ns is not None):
            parser.error('Exact final-report writer arguments required')
        expected = {'bytes': args.input_bytes, 'sha256': args.input_sha256}
        _validate_pin(expected)
        writer_mode = '--tiny-final-report-writer' if args.tiny_final_report_writer else '--persist-final-report'
        expected_argv = [str(Path(sys.executable).resolve()), '-I', '-S', '-B',
            str(Path(__file__).resolve()), writer_mode, '--scope',
            str(Path(args.scope).absolute()), '--input-bytes', str(args.input_bytes),
            '--input-sha256', args.input_sha256]
        if list(sys.orig_argv) != expected_argv:
            raise RuntimeError('Exact original final-report writer interpreter argv required')
        if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
            raise RuntimeError('Actual isolated no-site no-bytecode final-report writer required')
        if dict(os.environ) != ENVIRONMENT:
            raise RuntimeError('Exact complete minimal final-report writer environment required')
        if args.tiny_final_report_writer:
            persist_tiny_final_report_probe(args.scope, expected_input_pin=expected)
        else:
            persist_final_report(args.scope, expected_input_pin=expected)


if __name__ == '__main__': main()
