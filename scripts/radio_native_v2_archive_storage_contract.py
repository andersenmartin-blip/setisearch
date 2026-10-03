#!/usr/bin/env python3
"""Pure point-in-time accounting for two authenticated metadata-copy bundles.

The independently retained requirements are the literal b/c label set, archive
roots, file pins, and observation pins.  A caller must establish that those file
pins identify archival metadata; filenames and matching bytes do not prove a
failed-control closure.  Current observations use historical_scope only as the
existing read-only observation transport.  The result names the copies as
archival metadata and never admits them as original scopes or private journals.

This module performs no filesystem access, repairs, creation, spending, or
activation.  It accounts for the two present copies and their directories only;
missing original storage is explicitly unaccounted for.  A separate verifier
must establish archival closure semantics.  Production admission remains
subject to its unchanged original-identity requirements.
"""
import json
from pathlib import Path
import re

import radio_native_v2_historical_storage as storage


SCHEMA = 'radio-native-v2-archive-metadata-storage-accounting-v1'
LABELS = ('b', 'c')
COMPONENT_ROLES = {
    'b': 'archival_b_metadata_copy',
    'c': 'archival_c_metadata_copy',
}
ORIGINAL_REPOSITORY_ROOT = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
MAX_METADATA_FILE_BYTES = 2 * 1024 * 1024
MAX_JOIN_BYTES = storage.MAX_STORAGE_BYTES
MAX_INVENTORY_ENTRIES = storage.MAX_ENTRIES
PRIVATE_SPEND_FILENAME = re.compile(r'spent-[a-f0-9]{64}\.json')


def _exact_labels(value, description):
    if type(value) is not dict or set(value) != set(LABELS):
        raise ValueError('Exact independently required b/c ' + description + ' required')


def _overlap(first, second):
    return (first == second or first.startswith(second + '/')
        or second.startswith(first + '/'))


def _private_name(path):
    if any(part.startswith('.radio-native-v2-invocation-ledger')
            or PRIVATE_SPEND_FILENAME.fullmatch(part)
            for part in path.split('/')):
        raise ValueError('Original private journal path naming cannot denote an archival metadata copy')


def _requirements(expected_archive_roots, expected_file_pins, expected_observation_pins):
    for value, description in (
            (expected_archive_roots, 'archive roots'),
            (expected_file_pins, 'metadata file pins'),
            (expected_observation_pins, 'observation pins')):
        _exact_labels(value, description)
    # Detach all externally held requirements before serializing observations.
    roots = dict(expected_archive_roots)
    for files in expected_file_pins.values():
        if (type(files) is not dict or not files
                or len(files) > MAX_INVENTORY_ENTRIES
                or any(type(relative) is not str for relative in files)):
            raise ValueError('Bounded exact-string independently required metadata file map required')
        for pin in files.values():
            storage._pin(pin)
    raw_requirements = storage.canonical(expected_file_pins)
    if len(raw_requirements) > storage.MAX_MANIFEST_BYTES:
        raise ValueError('Bounded archival metadata requirement serialization exceeded')
    file_pins = json.loads(raw_requirements)
    observation_pins = {label: storage._pin(expected_observation_pins[label]).copy()
        for label in LABELS}
    expected_directories = {}
    for label in LABELS:
        root = roots[label]
        if type(root) is not str:
            raise ValueError('Exact canonical archival metadata root string required')
        storage._absolute(root)
        _private_name(root)
        if _overlap(root, ORIGINAL_REPOSITORY_ROOT):
            raise ValueError('An archival metadata copy cannot overlap the original repository')
        files = file_pins[label]
        if (type(files) is not dict or not files
                or len(files) > MAX_INVENTORY_ENTRIES):
            raise ValueError('Bounded nonempty independently required metadata file map required')
        directories = {root}
        for relative, pin in files.items():
            if type(relative) is not str or relative == '.':
                raise ValueError('Canonical relative archival metadata file path required')
            storage._relative(relative)
            storage._absolute(root + '/' + relative)
            _private_name(relative)
            storage._pin(pin)
            if not 0 < pin['bytes'] <= MAX_METADATA_FILE_BYTES:
                raise ValueError('Bounded nonempty archival metadata file pin required')
            parent = Path(relative).parent
            while str(parent) != '.':
                directories.add(root + '/' + parent.as_posix())
                parent = parent.parent
        if directories & {root + '/' + relative for relative in files}:
            raise ValueError('An archival metadata file cannot also be a required directory')
        if len(files) + len(directories) > MAX_INVENTORY_ENTRIES:
            raise ValueError('Original inventory entry bound exceeded by archive requirements')
        expected_directories[label] = directories
    if _overlap(roots['b'], roots['c']):
        raise ValueError('Canonical archival metadata roots overlap')
    return roots, file_pins, observation_pins, expected_directories


def join_archival_metadata_storage(observations, *, expected_archive_roots,
        expected_file_pins, expected_observation_pins):
    """Charge only exact current b/c metadata-copy files and their directories.

    Requirements must come from a separately authenticated source, rather than
    be derived from ``observations``.  No original state is inferred from a
    public spend-record copy, an archived inode label, or absent private state.
    """
    _exact_labels(observations, 'metadata-copy observations')
    roots, file_pins, pins, expected_directories = _requirements(
        expected_archive_roots, expected_file_pins, expected_observation_pins)
    components = []; all_rows = []; identities_seen = set()
    logical = allocated = 0
    for label in LABELS:
        value = observations[label]
        if (type(value) is not dict or type(value.get('rows')) is not list
                or not 1 <= len(value['rows']) <= MAX_INVENTORY_ENTRIES):
            raise ValueError('Bounded current archival metadata observation required')
        value, digest = storage._authenticate(value, pins[label])
        if (set(value) != storage.OBSERVATION_FIELDS
                or value['schema'] != storage.OBSERVATION_SCHEMA
                or value['role'] != 'historical_scope'
                or value['scope'] != roots[label]
                or any(value[field] is not True for field in
                    ('authenticated_manifest_matched', 'current_observation_stable', 'read_only'))
                or value['execution_authorized'] is not False):
            raise ValueError('Exact root-bound read-only metadata-copy observation transport required')
        storage._sha(value['manifest_sha256'])
        rows, identities = storage._totals(value, roots[label], raw_pins=True)
        if [row['path'] for row in rows] != sorted(row['path'] for row in rows):
            raise ValueError('Canonical sorted archival metadata rows required')
        actual_files = {row['path'][len(roots[label]) + 1:]: row['raw_pin']
            for row in rows if row['kind'] == 'file'}
        actual_directories = {row['path'] for row in rows if row['kind'] == 'directory'}
        if actual_files != file_pins[label]:
            raise ValueError('Exact independently pinned archival metadata file membership required')
        if actual_directories != expected_directories[label]:
            raise ValueError('Only the archive root and required file ancestor directories are permitted')
        if identities & identities_seen:
            raise ValueError('Archival metadata copies share a device/inode alias')
        identities_seen.update(identities)
        logical += value['logical_bytes']; allocated += value['allocated_bytes']
        if (len(all_rows) + len(rows) > MAX_INVENTORY_ENTRIES
                or max(logical, allocated) > MAX_JOIN_BYTES):
            raise ValueError('Original whole storage or inventory bound exceeded by metadata copies')
        role = COMPONENT_ROLES[label]
        components.append({'generation': label, 'role': role, 'root': roots[label],
            'observation_transport_role': 'historical_scope',
            'observation_sha256': digest, 'entry_count': len(rows),
            'logical_bytes': value['logical_bytes'],
            'allocated_bytes': value['allocated_bytes']})
        all_rows.extend({'component': role, **row} for row in rows)
    return {'schema': SCHEMA, 'components': components, 'rows': all_rows,
        'logical_bytes': logical, 'allocated_bytes': allocated,
        'entry_count': len(all_rows), 'charged_once': True, 'read_only': True,
        'point_in_time_accounting_only': True, 'archive_closure_proved': False,
        'storage_join_eligible': False, 'original_private_journal_observed': False,
        'original_scope_observed': False, 'original_identity_continuity_proved': False,
        'missing_original_storage_accounted': False,
        'lifetime_accounting_proved': False, 'whole_control_qualified': False,
        'execution_authorized': False, 'activation_authorized': False,
        'retry_authorized': False, 'restart_authorized': False,
        'missing_history_reconstruction_authorized': False,
        'native_execution_authorized': False, 'scientific_execution_authorized': False,
        'telescope_read_authorized': False}
