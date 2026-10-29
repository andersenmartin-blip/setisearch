"""Capture one explicitly authorized BE production acquisition process.

Import/default execution never launches a child or contacts an archive. The CLI
accepts only the fixed recovery command after its production gate is verified.
The internal lifecycle helper is exercised with synthetic subprocesses only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

import recover_missing_rows_be as recovery


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_all(stream, data):
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)
        recovery.check(isinstance(written, int) and 0 < written <= len(remaining),
                       'Capture log write made no valid progress')
        remaining = remaining[written:]


def validate_marker(path, source_sha256, protocol_sha256):
    result = recovery.json_read(path)
    recovery.check(result.get('schema') == 'SETI_BE_RECOVERY_ACQUISITION_COMPLETE_V1'
                   and result.get('status') == 'PASS' and result.get('execution_mode') == 'PRODUCTION',
                   'Missing valid production acquisition marker')
    recovery.check(result.get('source_sha256') == source_sha256
                   and result.get('protocol_sha256') == protocol_sha256, 'Acquisition marker source/protocol differs')
    recovery.check(all(result.get(key) == value for key, value in recovery.COUNTS.items()),
                   'Acquisition marker lineage differs')
    recovery.check(result.get('scientific_coverage_credit') == 0
                   and result.get('mandatory_native_and_science_checks_pending') is True,
                   'Acquisition marker must retain pending science gates')
    return result


def capture_child(command, execution_dir, result_path, pins):
    """Private lifecycle core. Tests inject a local synthetic child command.

    Public production entry points construct the command themselves after the
    gate; callers of this helper own their supplied command's authorization.
    """
    execution_dir, result_path = Path(execution_dir).resolve(), Path(result_path).resolve()
    names = {'start': 'RECOVERY_START_BE.json', 'log': 'RECOVERY.log',
             'actual': 'RECOVERY_ACTUAL_EXIT_BE.json'}
    paths = {key: execution_dir / value for key, value in names.items()}
    recovery.check(all(not path.exists() for path in paths.values()), 'No capture overwrite or automatic restart')
    recovery.check(not result_path.exists(), 'Existing acquisition marker cannot be reused')
    for path, expected in pins['input_sha256'].items():
        recovery.check(recovery.sha(path) == expected, 'Capture input pin differs: ' + path)
    execution_dir.mkdir(parents=True, exist_ok=True)
    # Exclusive log plus START files reserve this one attempt before any spawn.
    log = paths['log'].open('xb', buffering=0)
    try:
        recovery.json_new(paths['start'], {'schema': 'SETI_BE_RECOVERY_CAPTURE_START_V1',
                          'started_utc': utc(), 'wrapper_pid': os.getpid(),
                          'command': command, **pins, 'child_launched': False,
                          'meaning': 'Immutable prospective reservation; actual lifecycle is in ACTUAL_EXIT.'})
    except BaseException:
        log.close()
        raise
    child, child_code = None, None
    stdout_eof = child_wait_completed = False
    capture_error = acceptance_failure = None
    marker = None
    accepted_code = 1
    observed_stdout = hashlib.sha256()
    observed_stdout_bytes = 0
    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            while True:
                data = child.stdout.read(65536)
                if not data:
                    stdout_eof = True
                    break
                observed_stdout.update(data)
                observed_stdout_bytes += len(data)
                write_all(log, data)
            child.stdout.close()
            child_code = child.wait()
            child_wait_completed = True
            accepted_code = child_code
        except BaseException:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            child_code = child.wait()
            child_wait_completed = True
            raise
        if child_code == 0:
            try:
                for path, expected in pins['input_sha256'].items():
                    recovery.check(recovery.sha(path) == expected, 'Capture input changed during child: ' + path)
                marker = validate_marker(result_path, pins['source_sha256'], pins['protocol_sha256'])
            except BaseException as error:
                accepted_code = 1
                acceptance_failure = {'error': repr(error), 'traceback': traceback.format_exc(),
                                      'child_exit_code': 0,
                                      'meaning': 'Child exited0; completion evidence was not accepted.'}
    except BaseException as error:
        accepted_code = 1
        capture_error = {'error': repr(error), 'traceback': traceback.format_exc()}
    finally:
        if child is not None and child.stdout is not None:
            child.stdout.close()
        try:
            log.flush()
            os.fsync(log.fileno())
        except BaseException as error:
            accepted_code, marker = 1, None
            capture_error = {'error': repr(error), 'traceback': traceback.format_exc()}
        finally:
            log.close()
    log_hash, log_bytes = recovery.sha(paths['log']), paths['log'].stat().st_size
    if log_hash != observed_stdout.hexdigest() or log_bytes != observed_stdout_bytes:
        accepted_code, marker = 1, None
        acceptance_failure = {'error': 'Persisted log differs from observed child stdout',
                              'child_exit_code': child_code,
                              'meaning': 'No completion evidence accepted because capture bytes differ.'}
    actual = {'schema': 'SETI_BE_RECOVERY_CAPTURE_ACTUAL_EXIT_V1', 'completed_utc': utc(),
              'command': command, **pins, 'wrapper_pid': os.getpid(),
              'child_pid': None if child is None else child.pid,
              'child_launched': child is not None, 'child_exit_code': child_code,
              'actual_exit_code': accepted_code, 'stdout_eof': stdout_eof,
              'child_wait_completed': child_wait_completed, 'log_path': str(paths['log']),
              'log_sha256': log_hash, 'log_bytes': log_bytes,
              'observed_stdout_sha256': observed_stdout.hexdigest(),
              'observed_stdout_bytes': observed_stdout_bytes,
              'result_path': str(result_path) if marker is not None else None,
              'result_sha256': recovery.sha(result_path) if marker is not None else None,
              'capture_error': capture_error, 'acceptance_failure': acceptance_failure,
              'science_completed': False, 'scientific_coverage_credit': 0}
    recovery.json_new(paths['actual'], actual)
    return accepted_code, actual


def capture_acquisition(evidence_root, protocol_path, runtime, gate_path, *, execute=False):
    recovery.check(execute is True, 'Use --execute explicitly; no child was launched')
    root, protocol_path, runtime, gate_path = (Path(path).resolve()
                                             for path in (evidence_root, protocol_path, runtime, gate_path))
    gate_hash_before = recovery.sha(gate_path)
    gate, protocol = recovery.production_gate(gate_path, protocol_path)
    recovery.check(recovery.sha(gate_path) == gate_hash_before, 'Gate changed during validation')
    review_path = Path(gate['review_path']).resolve()
    access_path = Path(gate['normal_access_receipt_path']).resolve()
    source = Path(recovery.__file__).resolve()
    command = [sys.executable, str(source), '--evidence-root', str(root),
               '--protocol', str(protocol_path), '--runtime', str(runtime),
               '--acquire', '--gate', str(gate_path)]
    pins = {'source_path': str(source), 'source_sha256': gate['source_sha256'],
            'capture_source_path': str(Path(__file__).resolve()), 'capture_source_sha256': recovery.sha(__file__),
            'protocol_path': str(protocol_path), 'protocol_sha256': gate['protocol_sha256'],
            'gate_path': str(gate_path), 'gate_sha256': gate_hash_before,
            'review_path': str(review_path), 'review_sha256': gate['review_sha256'],
            'normal_access_receipt_path': str(access_path),
            'normal_access_receipt_sha256': gate['normal_access_receipt_sha256'],
            'input_sha256': {str(source): gate['source_sha256'],
                             str(Path(__file__).resolve()): recovery.sha(__file__),
                             str(protocol_path): gate['protocol_sha256'],
                             str(gate_path): gate_hash_before,
                             str(review_path): gate['review_sha256'],
                             str(access_path): gate['normal_access_receipt_sha256']}}
    recovery.check(protocol['protocol_file_sha256'] == pins['protocol_sha256'], 'Validated protocol pin differs')
    return capture_child(command, root / 'work_be/execution',
                         root / 'work_be/acquire/ACQUISITION_COMPLETE_BE.json', pins)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--gate', type=Path, required=True)
    args = parser.parse_args()
    code, actual = capture_acquisition(args.evidence_root, args.protocol, args.runtime,
                                       args.gate, execute=args.execute)
    print(json.dumps({'actual_exit_code': code, 'child_exit_code': actual['child_exit_code'],
                      'child_wait_completed': actual['child_wait_completed'],
                      'stdout_eof': actual['stdout_eof'], 'science_completed': False}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
