#!/usr/bin/env python3
"""Separate agent's bounded engineering review; never dispatch a control.

The reviewer authored supervisor propagation, periodic quota monitoring and their tests, so that
source is explicitly self-reviewed. Fixture/finalizer/worker/launcher changes
were owned by other agents. This wrapper checks their held source buffers and
performs tiny in-memory allocator probes only. A successful review is not an
activation, storage lifetime certificate, public preread or scientific result.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import types


SOURCE_PATHS = (
    'scripts/radio_native_v2_prospective_spending.py',
    'scripts/radio_native_v2_historical_storage.py',
    'scripts/radio_native_v2_historical_observation.py',
    'scripts/radio_native_v2_worker_admission.py',
    'scripts/radio_native_v2_control_activation.py',
    'scripts/radio_native_v2_compact_eight_case_resource_fixture.py',
    'scripts/radio_native_v2_process_tree_supervisor.py',
    'scripts/radio_native_v2_resource_finalization.py',
    'scripts/radio_native_v2_compact_control_launch.py',
    'tests/test_radio_native_v2_worker_admission.py',
    'tests/test_radio_native_v2_control_activation.py',
    'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py',
    'tests/test_radio_native_v2_process_tree_supervisor.py',
    'tests/test_radio_native_v2_resource_finalization.py',
    'tests/test_radio_native_v2_compact_control_launch.py',
    'tests/test_radio_native_v2_historical_observation.py',
    'results_radio_native_v2_control_integration_20261002a/review_control_integration.py',
)
FIXTURE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
WORKER = 'scripts/radio_native_v2_worker_admission.py'
FINALIZER = 'scripts/radio_native_v2_resource_finalization.py'
SUPERVISOR = 'scripts/radio_native_v2_process_tree_supervisor.py'
LAUNCHER = 'scripts/radio_native_v2_compact_control_launch.py'
MIB = 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False).encode('utf-8')


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns)


def read_stable(path, maximum=2*MIB):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('Bounded sole-link review source required: ' + str(path))
        raw = bytearray()
        while True:
            block = os.read(fd, 65536)
            if not block: break
            raw.extend(block)
            if len(raw) > maximum: raise ValueError('Review source bound exceeded')
        if identity(before) != identity(os.fstat(fd)) or identity(before) != identity(path.lstat()):
            raise ValueError('Review source changed during held read: ' + str(path))
        return bytes(raw)
    finally:
        os.close(fd)


def literals(raw):
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try: result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError): pass
    return result


def held_module(raw, path, name):
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def refuse(label, callback):
    try: callback()
    except (ValueError, RuntimeError) as error:
        return {'name': label, 'passed': True, 'refusal': str(error)}
    raise AssertionError('Review mutation unexpectedly accepted: ' + label)


def synthetic_external(module, scope):
    """Structural observations only; no file/journal/claim is created."""
    roles = ('historical_scope', 'historical_ledger', 'prospective_ledger')
    components = []; rows = []
    for index, role in enumerate(roles):
        root = str(scope.parent / ('in-memory-' + role))
        part = []
        for offset, kind in enumerate(('directory', 'file')):
            row = {'component': role, 'path': root if kind == 'directory' else root + '/record',
                'kind': kind, 'device': 2**40, 'inode': 1000 + index*10 + offset,
                'mode': 0o700 if kind == 'directory' else 0o600,
                'nlink': 2 if kind == 'directory' else 1, 'uid': 0, 'gid': 0,
                'bytes': 4096 if kind == 'directory' else 4, 'allocated_bytes': 4096,
                'mtime_ns': 1, 'ctime_ns': 1}
            if kind == 'file' and role != 'prospective_ledger': row['raw_pin'] = pin(b'tiny')
            part.append(row)
        rows.extend(part)
        components.append({'role': role, 'root': root, 'observation_sha256': str(index+1)*64,
            'entry_count': len(part), 'logical_bytes': sum(row['bytes'] for row in part),
            'allocated_bytes': sum(row['allocated_bytes'] for row in part)})
    return {'schema': module.EXTERNAL_STORAGE_SCHEMA, 'components': components, 'rows': rows,
        'logical_bytes': sum(row['bytes'] for row in rows),
        'allocated_bytes': sum(row['allocated_bytes'] for row in rows), 'entry_count': len(rows),
        'charged_once': True, 'read_only': True, 'execution_authorized': False,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False,
        'current_control_scope': str(scope)}


def allocator_review(module):
    checks = []
    with tempfile.TemporaryDirectory(prefix='seti-integration-review-') as directory:
        scope = Path(directory) / 'current'; scope.mkdir(); (scope/'cases').mkdir()
        for ordinal in range(8): (scope/'cases'/f'case{ordinal:02d}').mkdir()
        inventory = module.storage_inventory(scope)
        external = synthetic_external(module, scope)
        allocation = module.allocate_storage(inventory, external_inventory=external)
        wanted_logical = inventory['logical_bytes'] + external['logical_bytes'] + module.METADATA_RESERVATION_BYTES + module.DIRECTORY_RESERVATION_BYTES
        wanted_allocated = inventory['allocated_bytes'] + external['allocated_bytes'] + module.METADATA_RESERVATION_BYTES + module.DIRECTORY_RESERVATION_BYTES
        assert allocation['whole_logical_bytes_with_remaining_reservation'] == wanted_logical
        assert allocation['whole_allocated_bytes_with_remaining_reservation'] == wanted_allocated
        assert sum(row['complete_logical_bytes'] for row in allocation['cases']) == wanted_logical
        assert sum(row['complete_allocated_bytes'] for row in allocation['cases']) == wanted_allocated
        checks.append({'name': 'three_components_charged_once_with_each_shared_eighth_and_terminal_reservations', 'passed': True})
        changed = copy.deepcopy(external)
        changed['rows'][0]['device'] = inventory['rows'][0]['device']
        changed['rows'][0]['inode'] = inventory['rows'][0]['inode']
        checks.append(refuse('external_alias_of_current_scope_refuses',
            lambda: module.allocate_storage(inventory, external_inventory=changed)))
        changed = copy.deepcopy(external)
        changed['components'][2]['root'] = changed['components'][0]['root'] + '/nested'
        checks.append(refuse('nested_external_root_refuses',
            lambda: module.allocate_storage(inventory, external_inventory=changed)))
        changed = copy.deepcopy(external)
        changed['components'][0]['allocated_bytes'] -= 1
        checks.append(refuse('component_total_undercharge_refuses',
            lambda: module.allocate_storage(inventory, external_inventory=changed)))
        changed = copy.deepcopy(external)
        changed['rows'][1]['raw_pin']['bytes'] -= 1
        checks.append(refuse('historical_raw_pin_undercharge_refuses',
            lambda: module.allocate_storage(inventory, external_inventory=changed)))
        changed = copy.deepcopy(external)
        changed['rows'][1]['mtime_ns'] += 1
        checks.append(refuse('retained_digest_detects_metadata_only_historical_change',
            lambda: module._match_retained_ledger(changed, module._ledger_inventory_pin(external))))
        changed_inventory = copy.deepcopy(inventory)
        row = next(row for row in changed_inventory['rows'] if row['path'] == 'cases/case00')
        increment = 192*MIB - row['allocated_bytes']
        row['allocated_bytes'] += increment; changed_inventory['allocated_bytes'] += increment
        checks.append(refuse('case_bound_includes_shared_external_and_terminal_overhead',
            lambda: module.allocate_storage(changed_inventory, external_inventory=external)))
        # Mutate the caller's original after the detached observation has been
        # selected. Allocation must keep the authenticated detached metadata.
        original_validator = module._validate_inventory_totals
        def mutate_after_snapshot(value):
            original_validator(value)
            if value is not external and value.get('schema') == module.EXTERNAL_STORAGE_SCHEMA:
                external['rows'][0]['mtime_ns'] = 999
        module._validate_inventory_totals = mutate_after_snapshot
        before_sha256 = module._ledger_inventory_pin(external)
        try:
            detached = module.allocate_storage(inventory, external_inventory=external)
            assert detached['external_ledger_inventory_sha256'] == before_sha256
            assert detached['external_ledger_storage']['rows'][0]['mtime_ns'] == 1
        finally:
            module._validate_inventory_totals = original_validator
        checks.append({'name': 'caller_mutation_after_detach_does_not_change_allocated_snapshot', 'passed': True})
    return checks


def bootstrap_review(repository, sources):
    edges = []; tables = {path: literals(raw) for path, raw in sources.items()}
    for path in (SUPERVISOR, FINALIZER, LAUNCHER):
        pins = tables[path]['BOOTSTRAP_SOURCE_PINS']
        for dependency, expected in sorted(pins.items()):
            observed = pin(sources[dependency] if dependency in sources else read_stable(repository/dependency))
            assert observed == expected, 'Bootstrap drift: ' + path + ' -> ' + dependency
            edges.append({'source': path, 'dependency': dependency, 'pin': expected})
    for path, name, dependency in (
        (WORKER, 'SPENDING_IMPLEMENTATION_PIN', 'scripts/radio_native_v2_prospective_spending.py'),
        (FIXTURE, 'WORKER_ADMISSION_IMPLEMENTATION_PIN', WORKER),
        (FIXTURE, 'CONTROL_ACTIVATION_IMPLEMENTATION_PIN', 'scripts/radio_native_v2_control_activation.py'),
        (FIXTURE, 'INVOCATION_SPENDING_IMPLEMENTATION_PIN', 'scripts/radio_native_v2_prospective_spending.py'),
        (FIXTURE, 'ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN', 'scripts/radio_native_v2_activation_environment.py'),
        (FIXTURE, 'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN', 'scripts/radio_native_v2_historical_observation.py'),
        ('scripts/radio_native_v2_historical_observation.py', 'STORAGE_IMPLEMENTATION_PIN',
            'scripts/radio_native_v2_historical_storage.py'),
    ):
        expected = tables[path][name]
        observed = pin(sources[dependency] if dependency in sources else read_stable(repository/dependency))
        assert observed == expected, 'Implementation drift: ' + path + ' -> ' + dependency
        edges.append({'source': path, 'dependency': dependency, 'pin': expected})
    assert tables[WORKER]['SPENDING_SOURCE'] == 'scripts/radio_native_v2_prospective_spending.py'
    for dependency, expected in sorted(tables['scripts/radio_native_v2_historical_observation.py']['HISTORICAL_INPUT_PINS'].items()):
        assert pin(read_stable(repository/dependency)) == expected, 'Historical raw input drift: ' + dependency
        edges.append({'source': 'scripts/radio_native_v2_historical_observation.py',
            'dependency': dependency, 'pin': expected})
    return edges


def phase_guard_review(sources):
    required = {
        FIXTURE: {'require_execution_ready': 'observe_authenticated_invocation_storage',
            'persistent_ledger_storage': '_authenticated_retained_storage',
            '_authenticated_retained_storage': 'observe_authenticated_invocation_storage',
            'check_storage': '_authenticated_retained_storage'},
        FINALIZER: {'capture_pending_measurements': 'observe_authenticated_ledger_storage',
            'join_final_measurements': 'observe_authenticated_ledger_storage',
            'persist_final_report': 'observe_authenticated_ledger_storage',
            'join_final_report_lifetime': 'observe_authenticated_ledger_storage'},
        LAUNCHER: {'_launch_control_once': 'observe_authenticated_ledger_storage'},
        SUPERVISOR: {'prepare_admitted_storage_monitor': 'observe_authenticated_invocation_storage',
            'supervise_engineering_subprocess': 'prepare_admitted_storage_monitor'},
    }
    edges = []
    for path, functions in required.items():
        selected = {node.name: node for node in ast.parse(sources[path]).body if isinstance(node, ast.FunctionDef)}
        for function, guard in functions.items():
            names = {node.func.id if isinstance(node.func, ast.Name) else
                node.func.attr if isinstance(node.func, ast.Attribute) else ''
                for node in ast.walk(selected[function]) if isinstance(node, ast.Call)}
            assert guard in names, 'Missing mandatory phase observer: ' + path + ':' + function
            edges.append({'source': path, 'phase': function, 'observer': guard})
    return edges


def save_exclusive(path, value):
    raw = canonical(value)+b'\n'
    with path.open('xb') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository_root.absolute()
    output = args.output.absolute()
    assert output.parent == repository/'results_radio_native_v2_control_integration_20261002a'
    assert not os.path.lexists(repository/'.radio-native-v2-invocation-ledger-20261002c')
    assert not os.path.lexists(repository/'config/radio_native_v2_control_activation_20261002c.activate.json')
    sources = {path: read_stable(repository/path) for path in SOURCE_PATHS}
    source_pins = {path: pin(raw) for path, raw in sources.items()}
    edges = bootstrap_review(repository, sources)
    phase_edges = phase_guard_review(sources)
    module = held_module(sources[FINALIZER], repository/FINALIZER, 'held_independent_finalizer_review')
    checks = allocator_review(module)
    after_pins = {path: pin(read_stable(repository/path)) for path in SOURCE_PATHS}
    assert source_pins == after_pins, 'Source changed during review'
    assert not os.path.lexists(repository/'.radio-native-v2-invocation-ledger-20261002c')
    assert not os.path.lexists(repository/'config/radio_native_v2_control_activation_20261002c.activate.json')
    result = {'schema': 'radio-native-v2-control-integration-independent-agent-review-v1',
        'status': 'BOUNDED_PREPARATION_REVIEW_PASSED_EXECUTION_BLOCKED',
        'reviewer': 'integration_review_machine_agent',
        'reviewer_authored_sources': [SUPERVISOR, 'tests/test_radio_native_v2_process_tree_supervisor.py'],
        'independence_limits': ['Supervisor propagation, periodic quota monitoring and their tests are self-reviewed here; a separate storage reviewer supplies its own bounded probes.',
            'Root agent owns launcher, bootstrap refresh and publication; those are separately reviewed here.',
            'This is a machine-agent review, not a human approval or external audit.',
            'In-memory storage probes test allocator boundaries; no actual protected control was dispatched.'],
        'source_pins_before': source_pins, 'source_pins_after': after_pins,
        'bootstrap_edges_verified': edges, 'phase_guard_edges_verified': phase_edges, 'checks': checks,
        'real_prospective_ledger_absent_before_and_after': True,
        'real_prospective_marker_absent_before_and_after': True,
        'execution_authorized': False, 'scientific_execution_authorized': False,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False,
        'telescope_reads': 0, 'large_source_generation': False, 'native_case_reservations': 0,
        'limitations': ['Remaining phase integration and immutable preparation/preread must be checked separately.',
            'Finite phase observations do not prevent mutation followed by privileged rollback between checks.',
            'Terminal observer self-checks do not independently observe its own future termination.']}
    save_exclusive(output, result)
    print(json.dumps({'status': result['status'], 'checks': len(checks),
        'bootstrap_edges': len(edges), 'source_files': len(source_pins), 'output_pin': pin(read_stable(output))}, sort_keys=True))


if __name__ == '__main__':
    main()
