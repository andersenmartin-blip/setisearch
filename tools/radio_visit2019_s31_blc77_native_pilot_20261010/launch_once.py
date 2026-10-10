"""Thin once-only wait4 launcher for the frozen NEW-visit native pilot.

Stdlib-only; no HDF5/NumPy/source API. Full child CPU/RSS and closed exit are
authoritative, including scientific imports, writers, teardown and receipts.
"""
import time
START = time.monotonic()
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import resource
import selectors
import signal
import subprocess
import sys

FAMILY = 'radio_visit2019_s31_blc77_native_pilot_20261010'
MAX_LIMITS = {'CPU_seconds': 6000, 'wall_seconds': 7200, 'memory_bytes': 1610612736,
              'output_bytes': 134217728, 'shared_workspace_bytes': 12884901888}
sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path, root):
    raw = path.read_bytes()
    require(path.is_absolute() and path.resolve() == path and root in path.parents, 'Canonical own pin path required')
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save_new(path, value):
    raw = (json.dumps(value, allow_nan=False, indent=2) + '\n').encode()
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit',
                 'root-admission', 'expected-root-admission-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    require(root.is_absolute() and root.resolve() == root and args.root_go_after_review, 'Canonical root and explicit one GO required')
    scope_path, admission_path = Path(args.scope), Path(args.root_admission)
    require(scope_path == root / 'tools' / FAMILY / 'scope.json', 'Exact new prospective scope path required')
    scope_raw, admission_raw = scope_path.read_bytes(), admission_path.read_bytes()
    require(hashlib.sha256(scope_raw).hexdigest() == args.expected_scope_sha256
            and hashlib.sha256(admission_raw).hexdigest() == args.expected_root_admission_sha256, 'Exact frozen scope/admission SHA required')
    scope, admission = json.loads(scope_raw), json.loads(admission_raw)
    own, worker = pin(Path(__file__), root), pin(Path(__file__).parent / 'search_saved.py', root)
    require(scope['family_id'] == FAMILY and worker['sha256'] == scope['search_script_sha256']
            and own in scope['input_pins'] and worker in scope['input_pins'], 'Frozen own launcher/worker required')
    require(admission['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_ROOT_ADMISSION_V1'
            and admission['status'] == 'PASS_FIXED_NEW_NATIVE_PILOT_ADMISSION'
            and admission['scope_sha256'] == args.expected_scope_sha256
            and admission['script_sha256'] == worker['sha256']
            and admission['public_freeze_commit'] == args.freeze_commit
            and admission['all_frozen_input_readbacks_PASS'] is True
            and admission['all_acquisition_and_source_QA_processes_closed'] is True
            and admission['one_search_GO'] is True, 'Exact late root closure/freeze/readback/GO required')
    limits = scope['limits']
    require(set(limits) == set(MAX_LIMITS) and all(type(limits[k]) is int and 0 < limits[k] <= v
            for k, v in MAX_LIMITS.items()), 'Finite launch caps differ')
    stage = root / 'results' / FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    marker, receipt_path = stage / 'OUTER_STARTED_ONCE.json', stage / 'ROOT_OUTER_EXECUTION_RECEIPT.json'
    stdout_path, stderr_path = stage / 'STDOUT.txt', stage / 'STDERR.txt'
    lock = (stage / 'OUTER_SERIAL_ACTIVE.lock').open('a+b')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(all(not p.exists() for p in (marker, receipt_path, stdout_path, stderr_path,
            stage / 'SEARCH_STARTED_ONCE.json', stage / 'measurement')), 'Preserve previous namespace attempt; no retry/append')
    command = [sys.executable, str(Path(__file__).parent / 'search_saved.py'), '--root', str(root),
        '--scope', str(scope_path), '--expected-scope-sha256', args.expected_scope_sha256,
        '--freeze-commit', args.freeze_commit, '--root-admission', str(admission_path),
        '--expected-root-admission-sha256', args.expected_root_admission_sha256, '--root-go-after-review']
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(root.parent / 'seti_fullpower_work/deps'),
                       PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        environment[name] = '1'
    launch_signals = {signal.SIGALRM, signal.SIGTERM, signal.SIGHUP, signal.SIGINT}
    previous_spawn_mask = None
    def child_limits():
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_spawn_mask)
        resource.setrlimit(resource.RLIMIT_CPU, (limits['CPU_seconds'], limits['CPU_seconds'] + 2))
        resource.setrlimit(resource.RLIMIT_AS, (limits['memory_bytes'], limits['memory_bytes']))
    def timeout(signum, frame):
        if signum == signal.SIGALRM:
            raise TimeoutError('Whole frozen pilot launch wall deadline reached')
        raise InterruptedError('Whole frozen pilot launcher received signal %d' % signum)
    save_new(marker, {'status': 'STARTED_ONE_FROZEN_NEW_NATIVE_PILOT_OUTER', 'command': command,
        'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
        'child_soft_hard_CPU_seconds': [limits['CPU_seconds'], limits['CPU_seconds'] + 2], 'retry': False})
    child, reaped, used, ok = None, False, None, False
    logged_bytes, observed_pipe_bytes, log_cap_exceeded = 0, 0, False
    result = {'schema': 'SETI_VISIT2019_NATIVE_PILOT_WHOLE_CHILD_EXECUTION_V1',
        'status': 'FAILED_CLOSED_PRESERVED_NO_RETRY', 'family_id': FAMILY,
        'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
        'root_admission_sha256': args.expected_root_admission_sha256, 'command': command,
        'launcher_pin': own, 'worker_pin': worker, 'limits': limits, 'child_started': False,
        'child_closed_reaped': False, 'actual_child_return_code': None, 'retry': False,
        'source_GETs': 0, 'arrays_opened_by_launcher': False}
    try:
        for termination_signal in launch_signals:
            signal.signal(termination_signal, timeout)
        signal.alarm(max(1, int(limits['wall_seconds'] - (time.monotonic() - START))))
        with stdout_path.open('xb') as stdout_log, stderr_path.open('xb') as stderr_log:
            # Never deliver termination between fork and assigning the owned
            # child. The child restores the inherited pre-block mask before
            # exec, and a pending parent signal reaches the cleanup below.
            previous_spawn_mask = signal.pthread_sigmask(signal.SIG_BLOCK, launch_signals)
            try:
                child = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                    preexec_fn=child_limits)
                result['child_started'] = True
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_spawn_mask)
            with selectors.DefaultSelector() as monitor:
                monitor.register(child.stdout, selectors.EVENT_READ, stdout_log)
                monitor.register(child.stderr, selectors.EVENT_READ, stderr_log)
                while monitor.get_map():
                    for event, _ in monitor.select():
                        block = os.read(event.fileobj.fileno(), 8192)
                        if not block:
                            monitor.unregister(event.fileobj)
                            event.fileobj.close()
                            continue
                        observed_pipe_bytes += len(block)
                        keep = min(len(block), 65536 - logged_bytes)
                        event.data.write(block[:keep])
                        logged_bytes += keep
                        if keep != len(block):
                            log_cap_exceeded = True
                            raise ValueError('Combined live child stdout/stderr exceeded 65536 bytes')
            found, wait_status, used = os.wait4(child.pid, 0)
            require(found == child.pid, 'Unexpected wait4 process identity')
            child.returncode = os.waitstatus_to_exitcode(wait_status)
            reaped = True
            stdout_log.flush(); os.fsync(stdout_log.fileno())
            stderr_log.flush(); os.fsync(stderr_log.fileno())
        result.update(actual_child_return_code=child.returncode, child_closed_reaped=True,
            whole_child_process_CPU_seconds=used.ru_utime + used.ru_stime,
            whole_child_peak_RSS_bytes=used.ru_maxrss * 1024,
            whole_command_process_CPU_seconds_before_receipt=used.ru_utime + used.ru_stime + time.process_time(),
            launcher_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            whole_launch_wall_seconds_before_receipt=time.monotonic() - START,
            outer_metadata_CPU_seconds_before_receipt=time.process_time(),
            stdout_bytes=stdout_path.stat().st_size, stderr_bytes=stderr_path.stat().st_size,
            observed_pipe_bytes=observed_pipe_bytes, live_log_cap_exceeded=log_cap_exceeded)
        resources = (result['whole_command_process_CPU_seconds_before_receipt'] <= limits['CPU_seconds']
            and result['whole_child_peak_RSS_bytes'] + result['launcher_peak_RSS_bytes'] <= limits['memory_bytes']
            and result['whole_launch_wall_seconds_before_receipt'] <= limits['wall_seconds']
            and result['stdout_bytes'] + result['stderr_bytes'] <= 65536)
        require(child.returncode == 0 and resources, 'Child exit/full closed resources failed')
        terminal = stage / 'measurement/EXECUTION_RECEIPT.json'
        terminal_pin = pin(terminal, root)
        execution = json.loads(terminal.read_bytes())
        require(execution['schema'] == 'SETI_VISIT2019_ONE_NATIVE_PILOT_EXECUTION_V1'
            and execution['status'] == 'COMPLETE_NEW_VISIT_FIXED_NATIVE_PILOT_EXPLORATORY_ONLY'
            and execution['scope_sha256'] == args.expected_scope_sha256
            and execution['public_freeze_commit'] == args.freeze_commit
            and execution['script_sha256'] == worker['sha256']
            and execution['all_input_end_readbacks_PASS'] is True, 'Actual exact canonical inner COMPLETE required')
        require(pin(Path(__file__), root) == own and pin(Path(__file__).parent / 'search_saved.py', root) == worker
            and scope_path.read_bytes() == scope_raw and admission_path.read_bytes() == admission_raw,
            'Frozen source/scope/admission changed during child')
        result.update(status='PASS_CLOSED_COMPLETE_NATIVE_PILOT_WHOLE_CHILD_RESOURCES',
                      resource_caps_satisfied=True, EXECUTION_RECEIPT_pin=terminal_pin)
        ok = True
    except BaseException as error:
        signal.alarm(0)
        signal.pthread_sigmask(signal.SIG_BLOCK, launch_signals)
        if child is not None and not reaped:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            found, wait_status, used = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(wait_status)
            reaped = found == child.pid
        result.update(status='FAILED_CLOSED_PRESERVED_NO_RETRY', error_type=type(error).__name__, error=str(error),
                      child_closed_reaped=reaped, resource_caps_satisfied=False,
                      actual_child_return_code=None if child is None else child.returncode,
                      observed_pipe_bytes=observed_pipe_bytes, live_log_cap_exceeded=log_cap_exceeded)
        if used is not None:
            result.update(whole_child_process_CPU_seconds=used.ru_utime + used.ru_stime,
                          whole_child_peak_RSS_bytes=used.ru_maxrss * 1024)
    finally:
        signal.alarm(0)
        signal.pthread_sigmask(signal.SIG_BLOCK, launch_signals)
        if child is not None:
            for stream in (child.stdout, child.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
        result.update(whole_launch_wall_seconds_before_receipt=time.monotonic() - START,
                      outer_metadata_CPU_seconds_before_receipt=time.process_time(),
                      launcher_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      stdout_bytes=stdout_path.stat().st_size if stdout_path.exists() else 0,
                      stderr_bytes=stderr_path.stat().st_size if stderr_path.exists() else 0)
        if used is not None:
            result['whole_command_process_CPU_seconds_before_receipt'] = used.ru_utime + used.ru_stime + time.process_time()
        if ok and (result['whole_launch_wall_seconds_before_receipt'] > limits['wall_seconds']
                   or result['whole_command_process_CPU_seconds_before_receipt'] > limits['CPU_seconds']
                   or result['whole_child_peak_RSS_bytes'] + result['launcher_peak_RSS_bytes'] > limits['memory_bytes']):
            ok = False
            result.update(status='FAILED_CLOSED_PRESERVED_NO_RETRY', resource_caps_satisfied=False,
                          error='Whole launch resource cap exceeded during endreadback')
        save_new(receipt_path, result)
        lock.close()
    try:
        print(json.dumps({'status': result['status'], 'child_CPU_seconds': result.get('whole_child_process_CPU_seconds'),
                          'actual_child_return_code': result['actual_child_return_code']}), flush=True)
    except BrokenPipeError:
        pass
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
