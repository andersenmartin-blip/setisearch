#!/usr/bin/env python3
"""Bounded synthetic structural review. No real scopes, spending or telescope IO.

Use an explicitly named retained candidate source, compile its exact bytes in a
non-main module, and call only pure allocation/validation functions. All paths
and metadata below are synthetic in-memory values, not claims of observation.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve()
raw = source.read_bytes()
assert raw == source.read_bytes(), 'Source changed during retained read'
module = types.ModuleType('synthetic_storage_review')
module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
scope = '/synthetic/current-control'
own_rows = [{'path': '.', 'kind': 'directory', 'device': 11, 'inode': 1,
             'bytes': 0, 'allocated_bytes': 0}]
for ordinal in range(8):
    own_rows.append({'path': f'cases/case{ordinal:02d}', 'kind': 'directory',
                    'device': 11, 'inode': 2 + ordinal,
                    'bytes': 0, 'allocated_bytes': 0})
own = {'scope': scope, 'rows': own_rows, 'logical_bytes': 0,
       'allocated_bytes': 0, 'entry_count': len(own_rows)}


def external():
    rows = []; components = []; inode = 100
    for index, role in enumerate(module.EXTERNAL_STORAGE_ROLES):
        root = '/synthetic/' + role
        template = {'component': role, 'device': 12, 'mode': 0o700,
                    'nlink': 2, 'uid': 1, 'gid': 1, 'mtime_ns': 0,
                    'ctime_ns': 0, 'bytes': 0, 'allocated_bytes': 0}
        inode += 1
        component_rows = [{**template, 'path': root, 'kind': 'directory',
                           'inode': inode}]
        if role.endswith('ledger'):
            inode += 1
            row = {**template, 'path': root+'/spend.json', 'kind': 'file',
                   'mode': 0o600, 'nlink': 1, 'inode': inode}
            if role == 'historical_ledger':
                row['raw_pin'] = pin(b'')
            component_rows.append(row)
        components.append({'role': role, 'root': root,
                           'observation_sha256': str(index+1)*64,
                           'entry_count': len(component_rows),
                           'logical_bytes': 0, 'allocated_bytes': 0})
        rows.extend(component_rows)
    return {'schema': module.EXTERNAL_STORAGE_SCHEMA, 'components': components,
            'rows': rows, 'entry_count': len(rows), 'logical_bytes': 0,
            'allocated_bytes': 0, 'charged_once': True, 'read_only': True,
            'execution_authorized': False, 'whole_control_qualified': False,
            'lifetime_accounting_proved': False, 'current_control_scope': scope}


def repair_totals(value):
    for component in value['components']:
        rows = [row for row in value['rows']
                if row['component'] == component['role']]
        component.update(entry_count=len(rows),
                         logical_bytes=sum(row['bytes'] for row in rows),
                         allocated_bytes=sum(row['allocated_bytes'] for row in rows))
    value.update(entry_count=len(value['rows']),
                 logical_bytes=sum(row['bytes'] for row in value['rows']),
                 allocated_bytes=sum(row['allocated_bytes'] for row in value['rows']))


def duplicate_root(value):
    row = copy.deepcopy(value['rows'][0]); row['inode'] = 9001
    value['rows'].insert(1, row); repair_totals(value)


def duplicate_file(value):
    root = value['components'][0]['root']
    template = copy.deepcopy(value['rows'][0])
    for inode in (9002, 9003):
        value['rows'].append({**template, 'path': root+'/same-file',
            'kind': 'file', 'inode': inode, 'mode': 0o600,
            'nlink': 1, 'bytes': 1, 'allocated_bytes': 1,
            'raw_pin': pin(b'x')})
    repair_totals(value)


def alias_own_root(value):
    value['rows'][0].update(device=11, inode=1)


def duplicate_external_inode(value):
    value['rows'][-1].update(device=value['rows'][0]['device'],
                            inode=value['rows'][0]['inode'])


def ancestor_overlap(value):
    value['components'][0]['root'] = '/synthetic'
    value['rows'][0]['path'] = '/synthetic'


def missing_ancestry(value):
    row = copy.deepcopy(value['rows'][0])
    row.update(path=row['path']+'/missing-parent/child', inode=9004)
    value['rows'].append(row); repair_totals(value)


def path_escape(value):
    value['rows'][0]['path'] = '/synthetic/elsewhere'


def component_total_drift(value):
    value['components'][0]['logical_bytes'] = 1


def detached_mutation(value):
    # Hook exactly before finalizer canonicalizes the caller value. Bounds are
    # re-applied to the detached authenticated contract, which must reject this.
    original = module.canonical
    def racing_canonical(item):
        if item is value:
            item['schema'] = 'altered-at-canonicalization'
        return original(item)
    module.canonical = racing_canonical


def ledger_extra_entry(value):
    row = copy.deepcopy(value['rows'][-1]); row['inode'] = 9010
    row['path'] += '-extra'; value['rows'].append(row); repair_totals(value)


cases = [('baseline', None, True),
         ('duplicate_historical_root_path_distinct_inode', duplicate_root, False),
         ('duplicate_historical_file_path_distinct_inode', duplicate_file, False),
         ('external_aliases_own_root', alias_own_root, False),
         ('duplicate_external_inode', duplicate_external_inode, False),
         ('ancestor_root_overlap', ancestor_overlap, False),
         ('missing_directory_ancestry', missing_ancestry, False),
         ('external_path_escape', path_escape, False),
         ('component_total_drift', component_total_drift, False),
         ('canonicalization_header_mutation', detached_mutation, False),
         ('ledger_extra_entry', ledger_extra_entry, False)]
results = []
initial_canonical = module.canonical
for name, mutation, expected_accept in cases:
    module.canonical = initial_canonical
    value = external()
    if mutation: mutation(value)
    try:
        allocated = module.allocate_storage(copy.deepcopy(own),
            external_inventory=value, reserved_bytes=0, directory_reserved_bytes=0)
    except Exception as error:
        result = {'name': name, 'accepted': False,
                  'error': type(error).__name__ + ': ' + str(error)}
    else:
        result = {'name': name, 'accepted': True,
                  'charged_entries': allocated['external_ledger_storage']['entry_count'],
                  'whole_logical_bytes': allocated['whole_logical_bytes_with_remaining_reservation']}
    result['expected_accept'] = expected_accept
    result['expectation_met'] = result['accepted'] is expected_accept
    results.append(result)
print(json.dumps({'schema': 'radio-native-v2-independent-storage-review-v1',
                  'reviewer_kind': 'independent_machine_agent',
                  'human_review': False, 'source_path': str(source),
                  'source_pin': pin(raw), 'synthetic_only': True,
                  'real_c_journal_created': False, 'real_control_dispatched': False,
                  'telescope_reads': 0, 'cases': results,
                  'all_expectations_met': all(item['expectation_met'] for item in results)},
                 sort_keys=True, indent=2))
