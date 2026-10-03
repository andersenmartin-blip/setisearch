#!/usr/bin/env python3
"""Pure multi-generation retained-storage accounting.

This preparation component extends the existing three-way b/c storage join to
an explicitly ordered set of closed historical generations plus one distinct
prospective ledger.  It never discovers, opens, creates, or repairs a ledger;
all observations and their canonical pins must be supplied independently.

The result is point-in-time accounting only.  It is not an activation receipt,
does not prove retention across process lifetime, and cannot replace a missing
original private journal or scope observation with a public copy.
"""
import re
from pathlib import Path

import radio_native_v2_historical_storage as storage


SCHEMA = 'radio-native-v2-multi-history-storage-join-v1'
GENERATION = re.compile(r'[a-z][a-z0-9-]{0,31}')
MIN_HISTORIES = 2
MAX_HISTORIES = 16
MAX_JOIN_BYTES = storage.MAX_STORAGE_BYTES


def _generation(value):
    if type(value) is not str or not GENERATION.fullmatch(value):
        raise ValueError('Canonical bounded historical generation required')
    return value


def _historical(inventory, *, expected_pin, role):
    inventory, digest = storage._authenticate(inventory, expected_pin)
    if (set(inventory) != storage.OBSERVATION_FIELDS
            or inventory['schema'] != storage.OBSERVATION_SCHEMA
            or inventory['role'] != role
            or any(inventory[field] is not True for field in
                ('authenticated_manifest_matched', 'current_observation_stable', 'read_only'))
            or inventory['execution_authorized'] is not False):
        raise ValueError('Authenticated read-only historical storage observation required')
    storage._sha(inventory['manifest_sha256'])
    root = storage._absolute(inventory['scope'])
    rows, identities = storage._totals(inventory, root, raw_pins=True)
    if role == 'historical_ledger' and (len(rows) != 2
            or sum(row['kind'] == 'file'
                and str(Path(row['path']).parent) == root for row in rows) != 1):
        raise ValueError('Exactly one historical ledger root and direct file required')
    return inventory, digest, root, rows, identities


def _prospective(inventory, *, expected_pin):
    inventory, digest = storage._authenticate(inventory, expected_pin)
    fields = {'schema', 'ledger_root', 'control_scope', 'activation_receipt_sha256',
        'invocation_spending_sha256', 'rows', 'logical_bytes', 'allocated_bytes',
        'entry_count', 'witness_bindings_verified', 'ledger_inventory_exact',
        'current_observation_stable'}
    if (set(inventory) != fields
            or inventory['schema'] != storage.LEDGER_STORAGE_SCHEMA
            or any(inventory[field] is not True for field in
                ('witness_bindings_verified', 'ledger_inventory_exact',
                    'current_observation_stable'))):
        raise ValueError('Exact authenticated prospective spend-storage observation required')
    for field in ('activation_receipt_sha256', 'invocation_spending_sha256'):
        storage._sha(inventory[field])
    root = storage._absolute(inventory['ledger_root'])
    control = storage._absolute(inventory['control_scope'])
    rows, identities = storage._totals(inventory, root, raw_pins=False)
    if (len(rows) != 2 or sum(row['kind'] == 'file'
            and str(Path(row['path']).parent) == root for row in rows) != 1):
        raise ValueError('Exactly one prospective ledger root and direct file required')
    return inventory, digest, root, control, rows, identities


def join_retained_generations(histories, prospective_ledger, *, expected_observation_pins):
    """Join two or more closed scope/ledger pairs and one prospective ledger.

    ``histories`` must be sorted by its caller-fixed generation labels.  This
    function deliberately refuses to infer chronology, recover absent state,
    or silently collapse several failed controls into a single observation.
    """
    if (type(histories) is not list
            or not MIN_HISTORIES <= len(histories) <= MAX_HISTORIES):
        raise ValueError('Two to sixteen explicit historical generations required')
    generations = []
    for item in histories:
        if type(item) is not dict or set(item) != {
                'generation', 'historical_scope', 'historical_ledger'}:
            raise ValueError('Exact historical generation observation pair required')
        generations.append(_generation(item['generation']))
    if generations != sorted(generations) or len(set(generations)) != len(generations):
        raise ValueError('Unique sorted historical generations required')

    expected_labels = {'prospective_ledger'}
    for generation in generations:
        expected_labels.update((generation + ':scope', generation + ':ledger'))
    if (type(expected_observation_pins) is not dict
            or set(expected_observation_pins) != expected_labels):
        raise ValueError('Exact independently retained multi-generation pins required')

    components = []
    all_rows = []
    roots = {}
    seen_identities = set()
    logical = allocated = 0

    def include(*, generation, role, inventory, digest, root, rows, identities):
        nonlocal logical, allocated
        for earlier in roots.values():
            if root == earlier or root.startswith(earlier + '/') or earlier.startswith(root + '/'):
                raise ValueError('Canonical multi-generation storage roots overlap')
        if identities & seen_identities:
            raise ValueError('Multi-generation storage device/inode alias rejected')
        roots[(generation, role)] = root
        seen_identities.update(identities)
        logical += inventory['logical_bytes']
        allocated += inventory['allocated_bytes']
        if (len(all_rows) + len(rows) > storage.MAX_ENTRIES
                or max(logical, allocated) > MAX_JOIN_BYTES):
            raise ValueError('Original whole storage or inventory bound exceeded by multi-generation join')
        components.append({'generation': generation, 'role': role, 'root': root,
            'observation_sha256': digest, 'entry_count': len(rows),
            'logical_bytes': inventory['logical_bytes'],
            'allocated_bytes': inventory['allocated_bytes']})
        all_rows.extend({'generation': generation, 'component': role, **row} for row in rows)

    for item in histories:
        generation = item['generation']
        for field, role, suffix in (
                ('historical_scope', 'historical_scope', 'scope'),
                ('historical_ledger', 'historical_ledger', 'ledger')):
            values = _historical(item[field],
                expected_pin=expected_observation_pins[generation + ':' + suffix], role=role)
            include(generation=generation, role=role, inventory=values[0],
                digest=values[1], root=values[2], rows=values[3], identities=values[4])

    values = _prospective(prospective_ledger,
        expected_pin=expected_observation_pins['prospective_ledger'])
    include(generation='prospective', role='prospective_ledger', inventory=values[0],
        digest=values[1], root=values[2], rows=values[4], identities=values[5])
    control = values[3]
    for root in roots.values():
        if control == root or control.startswith(root + '/') or root.startswith(control + '/'):
            raise ValueError('Prospective control scope overlaps retained storage overhead')

    return {'schema': SCHEMA, 'historical_generations': generations,
        'prospective_generation': 'prospective', 'components': components,
        'rows': all_rows, 'logical_bytes': logical, 'allocated_bytes': allocated,
        'entry_count': len(all_rows), 'charged_once': True, 'read_only': True,
        'execution_authorized': False, 'whole_control_qualified': False,
        'lifetime_accounting_proved': False,
        'missing_history_reconstruction_authorized': False}
