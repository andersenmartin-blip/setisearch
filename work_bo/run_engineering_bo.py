"""Run the five frozen deterministic BO engineering gates once, in order.

Main-safe: importing this module does not reserve an identity or start a child.
The exact public-freeze receipt, plan, runtime and source pins are validated
before the exclusive run directory is created. No RNG, telescope input or
astronomical-score phase is authorized by this runner.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import math
import os
import re
import signal
import stat
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
import methods
import capture

IDS = ('E01', 'E02', 'E03', 'E04', 'E05')
SCRIPTS = ('gates/e01_bytes.py', 'gates/e02_normalization.py',
           'gates/e03_arithmetic.py', 'gates/e04_calibration_time.py',
           'gates/e05_capture.py')
EXPECTED_CAPS = ((240, 120, 1 << 30, 512 << 20),
                 (300, 180, 2 << 30, 1 << 30),
                 (300, 180, 2 << 30, 1 << 30),
                 (300, 180, 2 << 30, 1 << 30),
                 (120, 60, 512 << 20, 64 << 20))
GROUP_IDS = ('E02', 'E03', 'E04')


def require(value, message):
    if not value:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def pin_map(config, config_path, receipt_path):
    pins = {str((ROOT / p['path']).resolve()): p['sha256']
            for p in config['source_pins']}
    pins[str(config_path)] = methods.file_sha(config_path)
    pins[str(receipt_path)] = methods.file_sha(receipt_path)
    pins[str(Path(sys.executable).resolve())] = config['runtime']['python_executable_sha256']
    return pins


def preflight(config_path, requested_commit):
    """Metadata/source/runtime checks only; do not create execution outputs."""
    require(config_path == (ROOT / 'BO_ENGINEERING_PLAN.json').resolve()
            and not (ROOT / 'BO_ENGINEERING_PLAN.json').is_symlink(),
            'Exact regular BO_ENGINEERING_PLAN.json required')
    config = methods.verify_config(config_path)
    require(config['engineering_only'] is True
            and config['real_telescope_powers_authorized'] is False
            and config['rng_authorized'] is False
            and config['scientific_scores_authorized'] is False,
            'Plan does not authorize exactly deterministic engineering')
    require(all(config[k] == 0 for k in ['new_observations', 'new_archive_requests',
                                        'new_coverage_credit', 'cost_DKK']),
            'No new observation, archive, coverage or spending scope is permitted')
    require(config['preserved_history']['HIP45688_M_raw_sum_failures'] == 24
            and config['preserved_history']['HIP45688_M_full_QA'] is False
            and config['preserved_history']['all_M_raw_sum_failures'] == 142,
            'Historical M failures must remain literal')
    require(config['execution_relative_dir'] == 'execution/BO_ENGINEERING_V1',
            'Wrong finite execution identity')
    run_root = ROOT / config['execution_relative_dir']
    require(run_root.resolve() == run_root and run_root.is_relative_to(ROOT),
            'Execution path is not the exact BO-relative identity')
    require(len(config['gates']) == 5, 'Exactly five ordered gates required')
    pinned = {p['path'] for p in config['source_pins']}
    require({'run_engineering_bo.py', 'src/capture.py', 'src/methods.py', *SCRIPTS} <= pinned,
            'Runner, capture, methods and every gate source must be pinned')
    for number, gate in enumerate(config['gates']):
        require(gate['id'] == IDS[number] and gate['script'] == SCRIPTS[number],
                'Gate identity, order or source differs')
        c = gate['caps']
        require(tuple(c[k] for k in ['wall_seconds', 'cpu_seconds', 'rss_bytes', 'stored_bytes'])
                == EXPECTED_CAPS[number], 'Frozen individual gate caps differ')
        expected = run_root / gate['id'] / 'payload'
        require(Path(config['gate_outputs'][gate['id']]).resolve() == expected,
                'Gate payload is outside its exact capture reservation')
    group = config['deterministic_group']
    require(group['gate_ids'] == list(GROUP_IDS)
            and (group['cpu_seconds'], group['wall_seconds'], group['rss_bytes'], group['stored_bytes'])
            == (180, 300, 2 << 30, 1 << 30), 'Shared E02–E04 reservation differs')
    require(config['capture'] == dict(max_stdout_bytes=4 << 20,
                                     failure_reserve_bytes=1 << 20, poll_seconds=0.02),
            'Frozen capture/footer limits differ')
    require(all(config['thread_environment'].get(k) == '1' for k in capture.THREAD_KEYS),
            'Single-thread environment required')
    receipt_path = ROOT / 'PUBLIC_FREEZE_RECEIPT_BO.json'
    require(receipt_path.is_file() and not receipt_path.is_symlink(),
            'A regular public exact-readback receipt is required before reservation')
    receipt = methods.read_json(receipt_path)
    require(receipt['schema'] == 'SETI_BO_PUBLIC_FREEZE_RECEIPT_V1'
            and receipt['plan_sha256'] == methods.file_sha(config_path)
            and receipt['exact_readback_verified'] is True
            and receipt['before_execution'] is True,
            'Public freeze receipt does not bind the current plan before execution')
    for key in ['public_commit_sha', 'source_tree_sha']:
        require(isinstance(receipt[key], str)
                and re.fullmatch('[0-9a-f]{40}', receipt[key]) is not None,
                'Exact public Git identity required: ' + key)
    if requested_commit is not None:
        require(requested_commit == receipt['public_commit_sha'],
                'Requested preregistration commit differs from public receipt')
    pins = pin_map(config, config_path, receipt_path)
    capture.verify_pins(pins)
    methods.verify_sources()
    return config, receipt, receipt_path, pins, run_root


def child_cpu(receipt):
    resources = receipt['resources']
    return sum(float(resources[k] or 0) for k in ['child_user_cpu_seconds', 'child_system_cpu_seconds'])


def capture_is_quiescent(receipt):
    # No child was started is distinct from an unverified started-child cleanup.
    if receipt.get('child_pid') is None:
        return True
    return (receipt.get('child_wait_completed') is True
            and receipt.get('stdout_eof') is True
            and receipt.get('descendant_cleanup_completed') is True
            and receipt.get('remaining_live_descendants') == [])


def validate_closed_capture(receipt, folder, gate_id, context):
    require(receipt['status'] == 'PASS' and receipt['actual_exit_code'] == 0
            and receipt['child_wait_completed'] is True
            and receipt['stdout_eof'] is True and receipt['natural_stdout_eof'] is True
            and receipt['stdout_fully_preserved'] is True
            and receipt['killed'] is False and receipt['capture_error'] is None
            and receipt['process_namespace_mapping_verified'] is True
            and receipt['descendant_cleanup_completed'] is True
            and receipt['remaining_live_descendants'] == []
            and receipt['source_pins_verified_before'] is True
            and receipt['source_pins_verified_after'] is True,
            'Gate capture did not close and qualify exactly: ' + gate_id)
    require(receipt['context'] == context, 'Capture context differs')
    log = folder / 'STDOUT.log'
    result_path = folder / 'payload/RESULT.json'
    require(receipt['log_path'] == str(log) and receipt['result_path'] == str(result_path)
            and methods.file_sha(log) == receipt['log_sha256'] == receipt['observed_stdout_sha256']
            and log.stat().st_size == receipt['log_bytes'] == receipt['observed_stdout_bytes'],
            'Saved/observed log binding differs')
    require(not result_path.is_symlink() and result_path.is_file()
            and methods.file_sha(result_path) == receipt['result_sha256'],
            'Gate result digest differs')
    terminal = receipt['terminal_stdout_json']
    require(terminal['event'] == 'GATE_TERMINAL_EOF' and terminal['status'] == 'PASS'
            and terminal['result_sha256'] == receipt['result_sha256'],
            'Gate terminal stdout/result binding differs')
    result = methods.read_json(result_path)
    require(result['gate'] == gate_id and result['status'] == 'PASS',
            'Gate result identity differs')
    if 'plan_sha256' in result:
        require(result['plan_sha256'] == context['plan_sha256'], 'Gate result plan differs')
    saved = methods.read_json(folder / 'ACTUAL_RECEIPT.json')
    require(saved == receipt, 'Returned and saved actual capture receipt differ')


def validate_special_scope(special, run_root, require_complete_e01):
    """Permit only the two exact, no-follow E01 rejection fixtures."""
    fixture_root = run_root / 'E01/payload/fixtures'
    symlink = str(fixture_root / 'symlink.npy')
    fifo = str(fixture_root / 'nonblocking_fifo.npy')
    allowed = {symlink, fifo}
    require(set(special) <= allowed, 'Unexpected special-node path; scope rejected')
    if require_complete_e01:
        require(set(special) == allowed, 'Complete E01 must retain both exact special fixtures')
    for path, evidence in special.items():
        require(isinstance(evidence, dict), 'Malformed special-node descriptor')
        if path == symlink:
            require(set(evidence) == {'lstat_mode', 'lstat_size', 'type',
                                      'target_text', 'target_sha256'}
                    and evidence['lstat_mode'] == stat.S_IFLNK | 0o777
                    and evidence['lstat_size'] == 12
                    and evidence['type'] == 'symlink'
                    and evidence['target_text'] == 'small_v1.npy'
                    and evidence['target_sha256'] == hashlib.sha256(b'small_v1.npy').hexdigest(),
                    'E01 symlink type/mode/target differs; scope rejected')
        else:
            require(set(evidence) == {'lstat_mode', 'lstat_size', 'type'}
                    and evidence['lstat_mode'] == stat.S_IFIFO | 0o600
                    and evidence['lstat_size'] == 0 and evidence['type'] == 'fifo',
                    'E01 FIFO type/mode differs; scope rejected')


def verify_closed_outputs(closed, run_root):
    for entry in closed:
        capture.verify_pins(entry['regular'])
        current = capture.special_inventory(entry['folder'])
        validate_special_scope(current, run_root, entry['gate_id'] == 'E01')
        require(current == entry['special'],
                'Prior closed special-node evidence changed')


def group_resources(group, run_root, started, parent_start, children_cpu, final=False):
    roots = [run_root / gate for gate in GROUP_IDS]
    wall = 0.0 if started is None else time.monotonic() - started
    parent_cpu = 0.0 if parent_start is None else time.process_time() - parent_start
    return dict(gate_ids=list(GROUP_IDS), started=started is not None,
                finalized=final, wall_seconds=wall,
                parent_cpu_seconds=parent_cpu, child_cpu_seconds=children_cpu,
                total_cpu_seconds=parent_cpu + children_cpu,
                stored_bytes=capture.stored_bytes(roots),
                storage_roots=[str(p) for p in roots], caps=dict(group))


def require_group_within_limits(resources):
    caps = resources['caps']
    require(resources['wall_seconds'] <= caps['wall_seconds'], 'Shared E02–E04 wall cap exceeded')
    require(resources['total_cpu_seconds'] <= caps['cpu_seconds'], 'Shared E02–E04 total CPU cap exceeded')
    require(resources['stored_bytes'] <= caps['stored_bytes'], 'Shared E02–E04 storage cap exceeded')


def run(config_path, requested_commit):
    config, public, receipt_path, pins, run_root = preflight(config_path, requested_commit)
    # Reservation begins only after every public/source/runtime check above.
    run_root.parent.mkdir(exist_ok=True)
    try:
        run_root.mkdir()
    except FileExistsError as exc:
        raise capture.ReservationConflict('BO run identity already exists; no retry or overwrite') from exc
    started = time.monotonic()
    started_utc = utc()
    root_parent_cpu_start = time.process_time()
    reserve = None
    completed = []
    receipts = []
    closed_outputs = []
    stopped_gate = None
    reason = None
    unreturned_capture = False
    group_start = group_parent_start = None
    group_children_cpu = 0.0
    group_final = None
    per_gate_resources = []
    freeze_context = dict(engineering_only=True, identity=config['identity'],
                          prereg_public_commit_sha=public['public_commit_sha'],
                          source_tree_sha=public['source_tree_sha'],
                          plan_sha256=methods.file_sha(config_path),
                          public_freeze_receipt_path=str(receipt_path),
                          public_freeze_receipt_sha256=methods.file_sha(receipt_path))
    try:
        reserve = capture.FailureReserve(run_root / 'FAILURE_RESERVE.bin',
                                         config['capture']['failure_reserve_bytes'])
        capture.publish_json(run_root / 'RUN_START_BO.json', dict(
            schema='SETI_BO_ENGINEERING_START_V1', started_utc=started_utc,
            **freeze_context, ordered_gate_ids=list(IDS), source_and_runtime_pins=pins,
            capture=config['capture'], deterministic_group=config['deterministic_group'],
            failure_reserve_bytes=config['capture']['failure_reserve_bytes'],
            failure_reserve_is_separate_from_E02_E04_storage_cap=True,
            random_draws_authorized=0, astronomical_powers_authorized=False,
            automatic_retry=False, overwrite=False))
        for gate in config['gates']:
            gate_id = gate['id']
            stopped_gate = gate_id
            if gate_id == 'E02':
                group_start = time.monotonic()
                group_parent_start = time.process_time()
            gate_wall_start = time.monotonic()
            gate_parent_cpu_start = time.process_time()
            methods.verify_config(config_path)
            capture.verify_pins(pins)
            verify_closed_outputs(closed_outputs, run_root)
            group_capture = None
            if gate_id in GROUP_IDS:
                resources = group_resources(config['deterministic_group'], run_root,
                                            group_start, group_parent_start, group_children_cpu)
                require_group_within_limits(resources)
                group_capture = dict(
                    deadline_monotonic=group_start + config['deterministic_group']['wall_seconds'],
                    cpu_remaining=config['deterministic_group']['cpu_seconds'] - resources['total_cpu_seconds'],
                    rss_bytes=config['deterministic_group']['rss_bytes'],
                    storage_roots=resources['storage_roots'],
                    stored_bytes=config['deterministic_group']['stored_bytes'])
            folder = run_root / gate_id
            payload = folder / 'payload'
            context = dict(gate_id=gate_id, plan_sha256=freeze_context['plan_sha256'],
                           prereg_public_commit_sha=public['public_commit_sha'], engineering_only=True)
            command = [sys.executable, '-B', str(ROOT / gate['script']),
                       '--config', str(config_path), '--out', str(payload)]
            print('Starting frozen BO gate ' + gate_id, flush=True)
            unreturned_capture = True
            actual = capture.capture_child(
                command, folder, payload / 'RESULT.json', gate['caps'], pins, context,
                stdout_limit=config['capture']['max_stdout_bytes'],
                poll_seconds=config['capture']['poll_seconds'], group=group_capture)
            unreturned_capture = False
            entry = dict(gate_id=gate_id, path=str(folder / 'ACTUAL_RECEIPT.json'),
                         sha256=methods.file_sha(folder / 'ACTUAL_RECEIPT.json'), status=actual['status'])
            receipts.append(entry)
            if gate_id in GROUP_IDS:
                group_children_cpu += child_cpu(actual)
            validate_closed_capture(actual, folder, gate_id, context)
            capture.verify_pins(pins)
            verify_closed_outputs(closed_outputs, run_root)
            regular = capture.inventory(folder)
            special = capture.special_inventory(folder)
            validate_special_scope(special, run_root, gate_id == 'E01')
            capture.verify_pins(regular)
            require(capture.special_inventory(folder) == special, 'Gate special evidence changed during inventory')
            wall = time.monotonic() - gate_wall_start
            cpu = time.process_time() - gate_parent_cpu_start + child_cpu(actual)
            require(wall <= gate['caps']['wall_seconds'], 'Actual gate including admission/footer exceeded wall cap')
            require(cpu <= gate['caps']['cpu_seconds'], 'Actual gate including parent/child/footer exceeded CPU cap')
            require(capture.stored_bytes([folder]) <= gate['caps']['stored_bytes'], 'Actual gate storage cap exceeded')
            per_gate_resources.append(dict(gate_id=gate_id, wall_seconds=wall,
                                           parent_and_child_cpu_seconds=cpu,
                                           stored_bytes=capture.stored_bytes([folder])))
            closed_outputs.append(dict(gate_id=gate_id, folder=str(folder), regular=regular, special=special))
            completed.append(gate_id)
            if gate_id in GROUP_IDS:
                resources = group_resources(config['deterministic_group'], run_root,
                                            group_start, group_parent_start, group_children_cpu,
                                            final=gate_id == 'E04')
                require_group_within_limits(resources)
                if gate_id == 'E04':
                    group_final = resources
            print('Closed BO gate ' + gate_id + ' with exact actual exit/EOF/result binding', flush=True)
        stopped_gate = None
        require(completed == list(IDS), 'All five finite gates did not close')
        methods.verify_config(config_path)
        capture.verify_pins(pins)
        verify_closed_outputs(closed_outputs, run_root)
    except BaseException as exc:
        reason = type(exc).__name__ + ': ' + str(exc)
    actual_receipts = [methods.read_json(r['path']) for r in receipts]
    quiescent = (not unreturned_capture and all(capture_is_quiescent(r) for r in actual_receipts))
    special_scope_error = None
    try:
        validate_special_scope(capture.special_inventory(run_root), run_root, 'E01' in completed)
    except (ValueError, OSError) as exc:
        special_scope_error = type(exc).__name__ + ': ' + str(exc)
        reason = ((reason + '; ') if reason is not None else '') + special_scope_error
    if reason is not None and reserve is not None:
        reserve.commit(dict(schema='SETI_BO_RESERVED_FAILURE_FOOTER_V1',
                            completed_utc=utc(), **freeze_context,
                            stopped_gate=stopped_gate, reason=reason,
                            gates_completed=completed, gate_receipts=receipts,
                            background_children_running=False if quiescent else None,
                            cleanup_status='CLOSED_OR_NOT_STARTED' if quiescent else 'UNKNOWN_NOT_CLAIMED_CLOSED',
                            no_next_gate_started=True))
    if group_final is None:
        group_final = group_resources(config['deterministic_group'], run_root,
                                      group_start, group_parent_start, group_children_cpu,
                                      final=group_start is not None)
    regular = capture.inventory(run_root)
    special = capture.special_inventory(run_root)
    capture.verify_pins(regular)
    require(capture.special_inventory(run_root) == special, 'Terminal special evidence changed')
    is_complete = reason is None
    terminal = dict(
        schema='SETI_BO_ENGINEERING_TERMINAL_V1',
        status='PASS_ALL_FIVE_ENGINEERING_GATES' if is_complete else 'STOPPED_NO_NEXT_GATE',
        started_utc=started_utc, completed_utc=utc(), **freeze_context,
        gates_completed=completed, gate_receipts=receipts,
        stopped_gate=stopped_gate, reason=reason,
        output_artifact_sha256=regular, special_node_evidence=special,
        special_node_scope_status='PASS_EXACT_DECLARED_OR_FAILED_PREFIX_SUBSET' if special_scope_error is None else 'FAIL_UNDECLARED_OR_CHANGED_SPECIAL_NODE_SCOPE',
        special_node_scope_error=special_scope_error,
        source_and_runtime_pins=pins, source_and_runtime_reverified_after_last_gate=is_complete,
        deterministic_group_resources=group_final, per_gate_resources=per_gate_resources,
        total_run_wall_seconds=time.monotonic()-started,
        total_parent_cpu_seconds=time.process_time()-root_parent_cpu_start,
        captured_child_cpu_seconds=sum(child_cpu(r) for r in actual_receipts),
        retained_root_stored_bytes_before_terminal=capture.stored_bytes([run_root]),
        failure_reserve=dict(path=str(run_root / 'FAILURE_RESERVE.bin'),
                             reserved_bytes=config['capture']['failure_reserve_bytes'],
                             allocation_completed=reserve is not None,
                             failure_footer_committed=bool(reserve and reserve.committed),
                             counted_in_root_storage=True,
                             excluded_from_E02_E04_phase_storage=True),
        background_children_running=False if quiescent else None,
        cleanup_status='CLOSED_OR_NOT_STARTED' if quiescent else 'UNKNOWN_NOT_CLAIMED_CLOSED',
        random_draws=0, astronomical_powers_opened=0, new_archive_requests=0,
        historical_M_failures_and_tolerances_unchanged=True,
        statistical_sensitivity_recovery_or_FAP_qualified=False,
        next_scientific_or_randomized_phase_activated=False,
        interpretation='Only the explicitly frozen deterministic engineering gates; no synthetic recovery matrix, astronomical search, historical requalification or statistical qualification.')
    terminal_path = run_root / ('RUN_COMPLETE_BO.json' if is_complete else 'RUN_STOP_BO.json')
    capture.publish_json(terminal_path, terminal)
    print(('Completed' if is_complete else 'Stopped') + ' BO engineering: ' + str(terminal_path), flush=True)
    return 0 if is_complete else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--prereg-commit')
    args = parser.parse_args()
    require(sys.flags.optimize == 0, 'Unoptimized Python required')
    if args.prereg_commit is not None:
        require(re.fullmatch('[0-9a-f]{40}', args.prereg_commit) is not None,
                'Exact optional preregistration commit required')
    def interrupted(signum, _frame):
        raise InterruptedError('Runner received signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    return run(args.config.resolve(), args.prereg_commit)


if __name__ == '__main__':
    sys.exit(main())
