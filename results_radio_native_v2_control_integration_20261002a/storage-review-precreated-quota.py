#!/usr/bin/env python3
"""Five bounded quota probes: tiny directories and explicitly declared metadata.

No large file, historical source, journal, marker or real control is generated or
read. Synthetic external raw-pin labels are deliberately not authentication.
The separately supplied source pin authenticates the allocator implementation,
not these invented workload observations. Root reruns after final pin refresh.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import types


def load_finalizer(root, expected_bytes, expected_sha):
    path = root / 'scripts/radio_native_v2_resource_finalization.py'
    raw = path.read_bytes()
    if len(raw) != expected_bytes or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('Allocator differs from independently supplied source pin')
    module = types.ModuleType('bounded_precreation_finalizer')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def external_inventory(module, scope, logical, allocated):
    components = []; rows = []; inode = 0
    template = {'device': 987654321, 'mode': 0o700, 'nlink': 2, 'uid': os.geteuid(),
        'gid': os.getegid(), 'bytes': 0, 'allocated_bytes': 0, 'mtime_ns': 0, 'ctime_ns': 0}
    for index, role in enumerate(module.EXTERNAL_STORAGE_ROLES):
        root = str(scope.parent / (scope.name + '-declared-' + role))
        inode += 1
        selected = [{'component': role, 'path': root, 'kind': 'directory', **template, 'inode': inode}]
        inode += 1
        file = {'component': role, 'path': root + '/declared-inert.bin', 'kind': 'file',
            **template, 'inode': inode, 'mode': 0o600, 'nlink': 1,
            'bytes': logical if role == 'historical_scope' else 0,
            'allocated_bytes': allocated if role == 'historical_scope' else 0}
        if role != 'prospective_ledger':
            file['raw_pin'] = {'bytes': file['bytes'], 'sha256': str(index + 1) * 64}
        selected.append(file); rows.extend(selected)
        components.append({'role': role, 'root': root, 'observation_sha256': str(index + 4) * 64,
            'entry_count': 2, 'logical_bytes': sum(row['bytes'] for row in selected),
            'allocated_bytes': sum(row['allocated_bytes'] for row in selected)})
    return {'schema': module.EXTERNAL_STORAGE_SCHEMA, 'components': components, 'rows': rows,
        'logical_bytes': logical, 'allocated_bytes': allocated, 'entry_count': len(rows),
        'current_control_scope': str(scope), 'charged_once': True, 'read_only': True,
        'execution_authorized': False, 'whole_control_qualified': False, 'lifetime_accounting_proved': False}


def recompute(inventory):
    inventory.update(logical_bytes=sum(row['bytes'] for row in inventory['rows']),
        allocated_bytes=sum(row['allocated_bytes'] for row in inventory['rows']),
        entry_count=len(inventory['rows']))


def refused(callback, phrase):
    try:
        callback()
    except ValueError as failure:
        if phrase not in str(failure): raise
        return str(failure)
    raise AssertionError('Required quota/layout refusal was absent')


def run(module):
    results = []
    with tempfile.TemporaryDirectory(prefix='bounded-precreated-quota-') as name:
        scope = Path(name)
        for ordinal in range(8):
            (scope / 'cases' / ('case%02d' % ordinal)).mkdir(parents=True)
        current = module.storage_inventory(scope)
        external = external_inventory(module, scope, 128, 512)
        allocated = module.allocate_storage(current, external_inventory=external)
        assert len(allocated['cases']) == 8
        assert allocated['external_ledger_storage']['entry_count'] == 6
        assert allocated['final_metadata_reservation_bytes'] == 256 * 1024
        assert allocated['terminal_directory_growth_reservation_bytes'] == 65536
        results.append({'name': 'eight_empty_precreated_roots_charge_all_overhead', 'passed': True,
            'whole_logical_bytes': allocated['whole_logical_bytes_with_remaining_reservation'],
            'whole_allocated_bytes': allocated['whole_allocated_bytes_with_remaining_reservation']})

        missing = copy.deepcopy(current)
        missing['rows'] = [row for row in missing['rows'] if row['path'] != 'cases/case07']
        recompute(missing)
        reason = refused(lambda: module.allocate_storage(missing, external_inventory=external), 'eight retained case')
        results.append({'name': 'missing_precreated_case_refused_before_workload', 'passed': True, 'reason': reason})

        ninth = copy.deepcopy(current)
        template = next(row for row in current['rows'] if row['path'] == 'cases/case07')
        ninth['rows'].append({**template, 'path': 'cases/case08', 'inode': 999999999})
        recompute(ninth)
        reason = refused(lambda: module.allocate_storage(ninth, external_inventory=external), 'Unexpected retained case')
        results.append({'name': 'case08_refused_before_workload', 'passed': True, 'reason': reason})

        historical = external_inventory(module, scope, 8 * module.MIB, 8 * module.MIB)
        near = copy.deepcopy(current)
        file = {'path': 'cases/case00/declared-boundary.bin', 'kind': 'file', 'device': 987654322,
            'inode': 999999998, 'bytes': 0, 'allocated_bytes': 0}
        near['rows'].append(file); recompute(near)
        no_reservation = module.allocate_storage(near, external_inventory=historical,
            reserved_bytes=0, directory_reserved_bytes=0)
        first = no_reservation['cases'][0]
        file['bytes'] = module.LIMITS['case_storage_bytes'] - math.ceil(first['complete_logical_bytes'])
        file['allocated_bytes'] = module.LIMITS['case_storage_bytes'] - math.ceil(first['complete_allocated_bytes'])
        recompute(near)
        module.allocate_storage(near, external_inventory=historical, reserved_bytes=0, directory_reserved_bytes=0)
        module.allocate_storage(near)
        reason = refused(lambda: module.allocate_storage(near, external_inventory=historical), '192MiB')
        results.append({'name': 'history_share_and_terminal_reservations_jointly_exceed_case_cap',
            'passed': True, 'raw_case_file_logical_bytes': file['bytes'],
            'raw_case_file_allocated_bytes': file['allocated_bytes'],
            'without_history_passed': True, 'without_terminal_reservations_passed': True, 'reason': reason})

        overhead = module.METADATA_RESERVATION_BYTES + module.DIRECTORY_RESERVATION_BYTES
        logical = module.LIMITS['run_storage_bytes'] - current['logical_bytes'] - overhead
        physical = module.LIMITS['run_storage_bytes'] - current['allocated_bytes'] - overhead
        boundary = external_inventory(module, scope, logical, physical)
        exact = module.allocate_storage(current, external_inventory=boundary)
        assert exact['whole_logical_bytes_with_remaining_reservation'] == 1536 * module.MIB
        assert exact['whole_allocated_bytes_with_remaining_reservation'] == 1536 * module.MIB
        excessive = external_inventory(module, scope, logical + 8, physical + 8)
        reason = refused(lambda: module.allocate_storage(current, external_inventory=excessive), '192MiB')
        results.append({'name': 'whole_boundary_inclusive_and_eight_more_declared_bytes_refused',
            'passed': True, 'exact_whole_boundary_bytes': 1536 * module.MIB,
            'excess_declared_bytes': 8, 'reason': reason,
            'note': 'Eight attributed case caps detect this whole-cap excess first.'})
    assert len(results) == 5 and all(result['passed'] for result in results)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-bytes', type=int, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    module = load_finalizer(root, args.source_bytes, args.source_sha256)
    report = {'schema': 'radio-native-v2-precreated-quota-independent-probes-v1',
        'source_pin': {'bytes': args.source_bytes, 'sha256': args.source_sha256},
        'argv': sys.orig_argv, 'probe_count': 5, 'probes': run(module),
        'large_source_generated': False, 'real_control_launched': False, 'real_c_spend_consumed': False,
        'historical_artifacts_read_or_mutated': False, 'telescope_reads': 0,
        'execution_authorized': False, 'whole_control_qualified': False, 'lifetime_accounting_proved': False,
        'limitations': ['Declared metadata and synthetic external digests are arithmetic/layout probes, not authenticated retained storage.',
            'Tiny actual directories support precreation semantics; this does not prove sampled peak storage or future lifetime accounting.']}
    output = Path(__file__).with_suffix('.json')
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'probe_count': 5, 'passed': 5, 'output': str(output)}))


if __name__ == '__main__':
    main()
