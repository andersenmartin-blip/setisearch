"""Bounded BW capture with active evidence in tmpfs and closed-ZIP export.

No numerical rules are implemented here. The partial-search adapter supplies
the computation and bounded saved-result audit. Its incomplete-cadence status
is preserved; a passing capture proves execution/evidence closure only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / 'work_bw/BW_PARTIAL_PLAN.json'
FREEZE = REPO / 'work_bw/PUBLIC_FREEZE_RECEIPT_BW.json'
EXECUTION = REPO / 'work_bw/execution'
ISOLATION = Path('/dev/shm/seti_bw_partial_20261031')
CAPTURE_SOURCE = REPO / 'work_bo/src/capture.py'
ARCHIVE_SOURCE = REPO / 'work_bt/isolated_worker.py'
PARTIAL_SOURCE = REPO / 'work_bw/partial_search.py'
CAPS = {'wall_seconds': 180, 'cpu_seconds': 180,
        'rss_bytes': 2 * 1024**3, 'stored_bytes': 2 * 1024**3}
OVERALL_STORED_BYTES = 2 * 1024**3
ARCHIVE_MAX_MEMBERS = 512
BATCH_COUNT = 1
OVERALL_RUNTIME_WALL_SECONDS = 300
sys.dont_write_bytecode = True


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def archive_tools():
    archive = module_at('bw_frozen_bt_archive', ARCHIVE_SOURCE)
    # Identical BT archive functions; retain the previously reviewed512-member cap.
    # BW has five scans and one q. Strict byte validation remains unchanged.
    archive.MAX_MEMBERS = ARCHIVE_MAX_MEMBERS
    return archive


def bound_path(value):
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def storage_roots():
    return [EXECUTION, ISOLATION, REPO / 'work_bw/audit_execution', REPO / 'work_bw/review']


def binding_pins(planpath=PLAN, freezepath=FREEZE):
    """Read metadata and source hashes only; no NPY or power-array access."""
    planpath, freezepath = Path(planpath), Path(freezepath)
    plan, freeze = read(planpath), read(freezepath)
    runtime = plan['runtime']
    require(runtime['python_executable'] == sys.executable
            and runtime['python_version'] == platform.python_version()
            and runtime['python_executable_sha256'] == sha(sys.executable),
            'Frozen Python executable, version, or executable bytes differ')
    require(plan['caps'] == CAPS and plan['overall_storage_cap_bytes'] == OVERALL_STORED_BYTES,
            'Frozen resource caps differ')
    require(plan['isolation_root'] == str(ISOLATION), 'Frozen isolation root differs')
    require(plan['overall_runtime_wall_seconds'] == OVERALL_RUNTIME_WALL_SECONDS, 'Frozen overall wall cap differs')
    require(plan['batch_q_lists'] == [[254]], 'Frozen one-batch q254 continuation differs')
    require(freeze.get('exact_readback_verified') is True,
            'Public freeze must have exact verified readback before execution')
    plan_digest = sha(planpath)
    require(freeze.get('plan_sha256') == plan_digest,
            'Public freeze is not bound to these exact plan bytes')
    require(isinstance(plan.get('source_sha256'), dict) and plan['source_sha256'],
            'Plan must contain the frozen source digest map')
    sources = {}
    for name, digest in plan['source_sha256'].items():
        path = bound_path(name)
        require(path == path.resolve(strict=True), 'Source path must be canonical')
        require(str(path) not in sources, 'Duplicate source path alias')
        sources[str(path)] = digest
    for required in (Path(__file__).resolve(), CAPTURE_SOURCE, ARCHIVE_SOURCE, PARTIAL_SOURCE):
        require(str(required) in sources, 'Execution dependency is not frozen: ' + str(required))
    sources.update({str(planpath): plan_digest, str(freezepath): sha(freezepath)})
    inputs = {}
    for evidence in plan.get('metadata_evidence', []):
        inputs[str(bound_path(evidence['path']))] = evidence['sha256']
    for scan in plan['scans']:
        for pathkey, hashkey in (('path', 'input_sha256'), ('header_path', 'header_sha256')):
            path, digest = str(bound_path(scan[pathkey])), scan[hashkey]
            require(path not in inputs or inputs[path] == digest, 'Conflicting input identity')
            inputs[path] = digest
    require(len(plan['scans']) == 5, 'Only the five complete inputs may be bound')
    return plan, sources, inputs


def checked_bindings(archive, pins):
    checked = []
    for name, digest in sorted(pins.items()):
        actual = archive.stable_file(name)
        require(actual['sha256'] == digest, 'Frozen binding changed: ' + name)
        checked.append({'path': name, **actual})
    return checked


def record_error(result, phase, exc):
    result['errors'].append({'phase': phase, 'exception': type(exc).__name__ + ': ' + str(exc),
                             'traceback': traceback.format_exc()})


def worker(batch, output, isolated, planpath=PLAN, freezepath=FREEZE):
    """Invoked only as the bounded child. Keep tmpfs evidence for later review."""
    require(type(batch) is int and 1 <= batch <= BATCH_COUNT, 'Batch number must be 1')
    output, isolated = Path(output), Path(isolated)
    require(output == EXECUTION / f'batch{batch}' / 'payload', 'Unexpected export destination')
    require(isolated == ISOLATION / f'batch{batch}', 'Unexpected isolated destination')
    output.mkdir(exist_ok=False)
    archive = archive_tools()
    started = time.monotonic()
    result = {'schema': 'SETI_BW_ISOLATED_CAPTURE_RESULT_V1', 'status': 'FAIL',
              'execution_identity': f'BW_PARTIAL_FIVE_SCAN_BATCH_{batch}_V1', 'batch': batch,
              'isolation_directory': str(isolated), 'errors': [], 'archive': None,
              'caps': CAPS, 'overall_stored_bytes_cap': OVERALL_STORED_BYTES,
              'archive_max_members': ARCHIVE_MAX_MEMBERS,
              'qualification': 'Execution and byte preservation only; incomplete OFF coverage remains.',
              'source_pins_verified_before': False, 'input_pins_verified_before': False,
              'source_pins_verified_after': False, 'input_pins_verified_after': False}
    contents = isolated / 'contents'
    sources, inputs = {}, {}
    isolated_owned = False
    try:
        plan, sources, inputs = binding_pins(planpath, freezepath)
        result['source_pins_before'] = checked_bindings(archive, sources)
        result['source_pins_verified_before'] = True
        result['input_pins_before'] = checked_bindings(archive, inputs)
        result['input_pins_verified_before'] = True
        result['isolation'] = archive.prepare_isolation(isolated)
        isolated_owned = True
        partial = module_at('bw_frozen_partial_search', PARTIAL_SOURCE)
        computed = partial.run_batch(planpath, contents, batch)
        result['computation_status'] = computed['status']
        print(json.dumps({'event': 'BW_COMPUTATION_CLOSED', 'batch': batch}), flush=True)
        audit = partial.audit_batch(planpath, contents)
        require(audit.get('status') == 'PASS_BOUNDED_SAVED_RESULT_AUDIT', 'Bounded saved-result audit failed')
        archive.save_json(contents / 'BOUNDED_AUDIT.json', audit)
        result['bounded_audit_status'] = audit['status']
        result['bounded_audit'] = audit
        print(json.dumps({'event': 'BW_BOUNDED_AUDIT_CLOSED', 'batch': batch}), flush=True)
    except BaseException as exc:
        record_error(result, 'computation_or_bounded_audit', exc)
    try:
        require(result['source_pins_verified_before'] and result['input_pins_verified_before'],
                'Complete initial source and input binding is required')
        result['source_pins_after'] = checked_bindings(archive, sources)
        result['input_pins_after'] = checked_bindings(archive, inputs)
        result['source_pins_verified_after'] = result['source_pins_after'] == result['source_pins_before']
        result['input_pins_verified_after'] = result['input_pins_after'] == result['input_pins_before']
        require(result['source_pins_verified_after'] and result['input_pins_verified_after'],
                'Bound source or input changed during execution')
    except BaseException as exc:
        record_error(result, 'pins_after', exc)
    try:
        require(isolated_owned, 'No exclusively owned isolation directory')
        contents.mkdir(exist_ok=True)
        archive.save_json(contents / 'BW_SOURCE_INPUT_BINDINGS.json', {
            key: result.get(key) for key in (
                'source_pins_before', 'source_pins_after', 'input_pins_before', 'input_pins_after',
                'source_pins_verified_before', 'source_pins_verified_after',
                'input_pins_verified_before', 'input_pins_verified_after')})
        if result['errors']:
            archive.save_json(contents / 'BW_FAILURE.json', {'status': 'FAIL', 'errors': result['errors'], 'no_retry': True})
        receipt = archive.create_archive(contents, isolated / 'evidence.zip')
        exported = archive.export_archive(isolated / 'evidence.zip', output / 'EVIDENCE.zip', receipt)
        result['archive'] = {'path': 'EVIDENCE.zip', **exported}
        result['isolated_archive_verification'] = receipt
        result['exported_archive_verification'] = exported
        result['final_source_pins_after_export'] = checked_bindings(archive, sources)
        result['final_input_pins_after_export'] = checked_bindings(archive, inputs)
        require(result['final_source_pins_after_export'] == result['source_pins_before']
                and result['final_input_pins_after_export'] == result['input_pins_before'],
                'Bindings changed during archive export')
    except BaseException as exc:
        record_error(result, 'archive_or_export', exc)
    result['wall_seconds'] = time.monotonic() - started
    result['completed_utc'] = datetime.now(timezone.utc).isoformat()
    result['status'] = 'PASS' if not result['errors'] else 'FAIL'
    saved = archive.save_json(output / 'RESULT.json', result)
    print(json.dumps({'event': 'GATE_TERMINAL_EOF', 'status': result['status'],
                      'result_sha256': saved['sha256']}, sort_keys=True), flush=True)
    return 0 if result['status'] == 'PASS' else 1


def run_parent(batch, planpath=PLAN, freezepath=FREEZE, overall_deadline=None):
    parent_started, parent_cpu_started = time.monotonic(), time.process_time()
    effective_deadline = min(parent_started + CAPS['wall_seconds'], overall_deadline if overall_deadline is not None else float('inf'))
    require(parent_started < effective_deadline, 'No remaining overall wall budget')
    require(type(batch) is int and 1 <= batch <= BATCH_COUNT, 'Batch number must be 1')
    planpath, freezepath = Path(planpath).resolve(), Path(freezepath).resolve()
    require(planpath == PLAN and freezepath == FREEZE, 'Production plan and freeze locations are fixed')
    _, sources, _ = binding_pins(planpath, freezepath)
    capture = module_at('bw_frozen_exact_capture', CAPTURE_SOURCE)
    capture.verify_pins(sources)
    EXECUTION.mkdir(mode=0o700, exist_ok=True)
    folder, isolated = EXECUTION / f'batch{batch}', ISOLATION / f'batch{batch}'
    require(not folder.exists() and not isolated.exists(), 'Batch identity already exists; no overwrite or retry')
    for previous in range(1, batch):
        receipt = read(EXECUTION / f'batch{previous}' / 'ACTUAL_RECEIPT.json')
        require(receipt.get('status') == 'PASS', 'Previous batch capture did not pass')
        verified = read(EXECUTION / f'batch{previous}' / 'PARENT_EXPORT_VERIFICATION.json')
        require(verified.get('status') == 'PASS', 'Previous parent export verification did not pass')
    require(not any((EXECUTION / f'batch{later}').exists() for later in range(batch + 1, BATCH_COUNT + 1)),
            'Out-of-order batch execution is forbidden')
    lock = EXECUTION / '.active_batch_lock'
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (str(batch) + '\n').encode()); os.fsync(descriptor)
        # The unchanged capture monitor normally counts its own output tree.
        # Include this child's active tmpfs tree in that same per-batch count;
        # the separately configured group count covers every batch and export.
        original_stored_bytes = capture.stored_bytes
        def all_batch_storage(roots):
            roots = list(roots)
            if len(roots) == 1 and Path(roots[0]) == folder:
                roots.append(isolated)
            return original_stored_bytes(roots)
        capture.stored_bytes = all_batch_storage
        require(original_stored_bytes(storage_roots()) < OVERALL_STORED_BYTES,
                'No remaining total evidence storage budget')
        command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--batch', str(batch),
                   '--plan', str(planpath), '--freeze', str(freezepath)]
        receipt = capture.capture_child(command, folder, folder / 'payload' / 'RESULT.json',
            CAPS, sources, {'stage': 'BW', 'batch': batch, 'active_evidence': str(isolated),
                           'storage_accounting': 'Per batch includes tmpfs plus export; group includes all batches.'},
            stdout_limit=1024 * 1024, poll_seconds=.1,
            group={'storage_roots': storage_roots(), 'stored_bytes': OVERALL_STORED_BYTES,
                   'deadline_monotonic': effective_deadline,
                   'cpu_remaining': CAPS['cpu_seconds'] - (time.process_time() - parent_cpu_started)})
        verification = {'schema': 'SETI_BW_PARENT_EXPORT_VERIFICATION_V1', 'status': 'FAIL',
                        'batch': batch, 'capture_status': receipt['status'], 'errors': []}
        archive = archive_tools()
        try:
            require(receipt['status'] == 'PASS', 'Actual capture did not pass; no retry')
            resultpath = folder / 'payload' / 'RESULT.json'
            require(sha(resultpath) == receipt['result_sha256'], 'Result changed after actual capture')
            result = read(resultpath)
            capture.verify_pins(sources)
            expected = {key: value for key, value in result['archive'].items() if key != 'path'}
            verified = archive.verify_archive(folder / 'payload' / 'EVIDENCE.zip', expected['members'])
            require(verified == expected == result['isolated_archive_verification']
                    == result['exported_archive_verification'], 'Parent export verification differs')
            verification['archive'] = verified
            verification['final_source_pins'] = checked_bindings(archive, sources)
            require(sha(resultpath) == receipt['result_sha256'], 'Result changed during parent verification')
            verification['wall_seconds_including_parent_verification'] = time.monotonic() - parent_started
            verification['total_cpu_seconds_including_parent_verification'] = (
                time.process_time() - parent_cpu_started
                + receipt['resources']['child_user_cpu_seconds']
                + receipt['resources']['child_system_cpu_seconds'])
            require(verification['wall_seconds_including_parent_verification'] <= CAPS['wall_seconds'] and time.monotonic() <= effective_deadline,
                    'Total batch or overall wall cap exceeded including parent verification')
            require(verification['total_cpu_seconds_including_parent_verification'] <= CAPS['cpu_seconds'],
                    'Total CPU cap exceeded including parent verification')
            verification['status'] = 'PASS'
        except BaseException as exc:
            record_error(verification, 'parent_export_verification', exc)
        verification['completed_utc'] = datetime.now(timezone.utc).isoformat()
        archive.save_json(folder / 'PARENT_EXPORT_VERIFICATION.json', verification)
        overall_passed = receipt['status'] == 'PASS' and verification['status'] == 'PASS'
        print(json.dumps({'event': 'BW_CAPTURE_CLOSED', 'batch': batch, 'status': 'PASS' if overall_passed else 'FAIL',
                          'actual_exit_code': receipt['actual_exit_code'], 'stdout_eof': receipt['stdout_eof'],
                          'receipt_path': str(folder / 'ACTUAL_RECEIPT.json'),
                          'parent_export_verification_path': str(folder / 'PARENT_EXPORT_VERIFICATION.json')}), flush=True)
        return 0 if overall_passed else 1
    finally:
        os.close(descriptor)
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--plan', type=Path, default=PLAN)
    parser.add_argument('--freeze', type=Path, default=FREEZE)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        code = worker(args.batch, EXECUTION / f'batch{args.batch}' / 'payload',
                      ISOLATION / f'batch{args.batch}', args.plan, args.freeze)
    else:
        code = run_parent(args.batch, args.plan, args.freeze)
    raise SystemExit(code)
