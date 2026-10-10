"""Create-only outer wait4 meter for the single frozen acquisition child.

No network, native library, HDF5, array, or signal-value API is present. A closed
resource PASS requires real child exit0 and exact complete inner result pins.
"""
import time
STARTED = time.monotonic()
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys
import hashlib
import types
# The common helper is executable source, so authenticate it before import.
_boot_root = Path(__file__).resolve().parents[2]
_boot_family = 'radio_visit2019_native_acquisition_20261010'
_boot_scope_path = _boot_root / 'tools' / _boot_family / 'scope.json'
if '--root-go-exploratory-source-values' not in sys.argv:
    raise ValueError('Explicit root exploratory GO required before shared source import')
if os.environ.get('PYTHONPATH') != str(_boot_root.parent / 'seti_fullpower_work/deps') or os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
    raise ValueError('Exact own dependency path and disabled bytecode writes required')
_boot_expected = sys.argv[sys.argv.index('--expected-scope-sha256') + 1]
if _boot_scope_path.stat().st_size > 16777216:
    raise ValueError('Scope exceeds finite pre-import cap')
_boot_raw = _boot_scope_path.read_bytes()
if hashlib.sha256(_boot_raw).hexdigest() != _boot_expected:
    raise ValueError('Scope byte pin differs before shared source import')
_boot_common = json.loads(_boot_raw)['common_pin']
_boot_common_path = _boot_root / 'tools' / _boot_family / 'common.py'
if _boot_common['path'] != str(_boot_common_path.relative_to(_boot_root)) or _boot_common_path.is_symlink() or _boot_common_path.stat().st_size != _boot_common['bytes'] or _boot_common['bytes'] > 1048576:
    raise ValueError('Shared source byte pin differs before import')
_boot_common_raw = _boot_common_path.read_bytes()
if len(_boot_common_raw) != _boot_common['bytes'] or hashlib.sha256(_boot_common_raw).hexdigest() != _boot_common['sha256']:
    raise ValueError('Shared source byte pin differs before import')
_boot_common_module = types.ModuleType('common')
_boot_common_module.__file__ = str(_boot_common_path)
sys.modules['common'] = _boot_common_module
exec(compile(_boot_common_raw, str(_boot_common_path), 'exec'), _boot_common_module.__dict__)
from common import (ROOT, TOOLS, RESULTS, PRIVATE, DEPS, LIMITS,
                    require, pin, read_pin, read_json, save, fsync_dir, exact_environment)

TERMINATION_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
STREAM_CAPS = {'stdout': 1048576, 'stderr': 262144}


class Termination(Exception):
    pass


def terminated(signum, frame):
    raise Termination('Outer launcher termination signal ' + str(signum))


def group_signal(pid, signum):
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass


def reap_and_drain(child, logs, receipt):
    selector = selectors.DefaultSelector()
    counts = {name: 0 for name in STREAM_CAPS}
    status, used, timeout, killed, term_at = None, None, False, False, None
    for name, stream in (('stdout', child.stdout), ('stderr', child.stderr)):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    try:
        while status is None or selector.get_map():
            if not timeout and time.monotonic() - STARTED > LIMITS['wall_seconds']:
                timeout, term_at = True, time.monotonic()
                group_signal(child.pid, signal.SIGTERM)
            elif timeout and not killed and time.monotonic() - term_at > 2:
                killed = True
                group_signal(child.pid, signal.SIGKILL)
            for key, event in selector.select(0.05):
                try:
                    piece = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                name = key.data
                if not piece:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                counts[name] += len(piece)
                receipt['live_stream_bytes_observed'] = dict(counts)
                require(counts[name] <= STREAM_CAPS[name], 'Finite child stream cap exceeded')
                if name == 'stdout':
                    sys.stdout.buffer.write(piece)
                    sys.stdout.buffer.flush()
                require(logs[name].write(piece) == len(piece), 'Short outer log write')
                logs[name].flush()
                os.fsync(logs[name].fileno())
            if status is None:
                try:
                    found, actual_status, actual_used = os.wait4(child.pid, os.WNOHANG)
                except InterruptedError:
                    continue
                if found:
                    status, used = actual_status, actual_used
                    child.returncode = os.waitstatus_to_exitcode(status)
        return status, used, timeout, killed, counts
    finally:
        selector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('expected-launcher-sha256', 'expected-worker-sha256', 'expected-scope-sha256',
                 'expected-root-admission-sha256', 'public-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-exploratory-source-values', action='store_true')
    args = parser.parse_args()
    exact_environment()
    require(args.root_go_exploratory_source_values
            and re.fullmatch(r'[0-9a-f]{40}', args.public_freeze_commit), 'Exact public frozen root exploratory GO required')
    for value in (args.expected_launcher_sha256, args.expected_worker_sha256,
                  args.expected_scope_sha256, args.expected_root_admission_sha256):
        require(re.fullmatch(r'[0-9a-f]{64}', value), 'Exact SHA256 required')
    own, worker = pin(Path(__file__).resolve()), pin(ROOT / TOOLS / 'acquire_once.py')
    require(own['sha256'] == args.expected_launcher_sha256
            and worker['sha256'] == args.expected_worker_sha256, 'Frozen launcher/worker changed')
    scope_path, admission_path = ROOT / TOOLS / 'scope.json', ROOT / RESULTS / 'ROOT_ADMISSION.json'
    scope_pin, admission_pin = pin(scope_path), pin(admission_path)
    require(scope_pin['sha256'] == args.expected_scope_sha256
            and admission_pin['sha256'] == args.expected_root_admission_sha256, 'Frozen scope/admission changed')
    scope, admission = read_json(scope_pin), read_json(admission_pin)
    require(scope['worker_pin'] == worker and scope['launcher_pin'] == own
            and scope['limits'] == LIMITS and scope['output_directory'] == RESULTS + '/acquire_once'
            and scope['common_pin']['path'] == TOOLS + '/common.py', 'Frozen source/cap/output binding differs')
    read_pin(scope['common_pin'])
    require(admission['status'] == 'PASS_FROZEN_ONE_NATIVE_EXPLORATORY_SOURCE_VALUES_GO'
            and admission['scope_sha256'] == args.expected_scope_sha256
            and admission['worker_sha256'] == args.expected_worker_sha256
            and admission['launcher_sha256'] == args.expected_launcher_sha256
            and admission['public_freeze_commit'] == args.public_freeze_commit
            and admission['exploratory_source_values_GO'] is True, 'Exact root admission binding required')
    peer = read_json(admission['source_only_peer_receipt_pin'])
    require(peer['status'] == 'PASS_SOURCE_ONLY_NO_HTTP_HDF5_ARRAYS_OR_VALUES'
            and peer['scope_sha256'] == args.expected_scope_sha256
            and peer['worker_pin'] == worker and peer['launcher_pin'] == own
            and peer['common_pin'] == scope['common_pin'], 'Exact peer source-only pin binding required')
    out = ROOT / RESULTS / 'command_attempt'
    require(not (ROOT / RESULTS / 'acquire_once').exists(), 'Acquisition output exists; no rerun/resume')
    require(out.parent.is_dir() and PRIVATE.is_dir(), 'Create output/private parents before final freeze')
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['CPU_seconds'], LIMITS['CPU_seconds'] + 1))
    # Root must use this shared HTTP lock for any concurrent source request stage.
    lock_path = PRIVATE / 'SOURCE_HTTP_GLOBAL_FLOCK.lock'
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    out.mkdir(exist_ok=False)
    fsync_dir(out.parent)
    directory_fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    command = [sys.executable, str(ROOT / TOOLS / 'acquire_once.py'), '--scope', str(scope_path),
               '--expected-scope-sha256', args.expected_scope_sha256,
               '--expected-worker-sha256', args.expected_worker_sha256,
               '--root-admission', str(admission_path), '--expected-root-admission-sha256', args.expected_root_admission_sha256,
               '--public-freeze-commit', args.public_freeze_commit, '--root-go-exploratory-source-values']
    receipt = {'schema': 'SETI_VISIT2019_ONE_NATIVE_RAW_FULL_CHILD_RESOURCE_RECEIPT_V1',
               'status': 'CREATE_ONLY_LAUNCH_STARTED_ONCE', 'launcher_pin': own, 'worker_pin': worker,
               'common_pin': scope['common_pin'], 'scope_pin': scope_pin, 'root_admission_pin': admission_pin,
               'public_freeze_commit': args.public_freeze_commit, 'limits': LIMITS, 'command': command,
               'source_HTTP_global_lock_path': str(lock_path), 'child_started': False, 'retry': False,
               'original_A_B_status': 'FAIL_CLOSED', 'independent_validation_admission': 'BLOCKED',
               'resource_caps_satisfied': False, 'live_stream_bytes_observed': {'stdout': 0, 'stderr': 0}}
    save(out / 'LAUNCH_INPUT_RECEIPT.json', receipt, create_only=True)
    child, ok = None, False
    try:
        for signum in TERMINATION_SIGNALS:
            signal.signal(signum, terminated)
        environment = os.environ.copy()
        environment.update(PYTHONPATH=str(DEPS), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
        for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            environment[name] = '1'
        with (out / 'STDOUT.txt').open('xb') as stdout_log, (out / 'STDERR.txt').open('xb') as stderr_log:
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, TERMINATION_SIGNALS)
            try:
                child = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                         preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, old_mask))
                receipt['child_started'] = True
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            status, used, timeout, killed, counts = reap_and_drain(child, {'stdout': stdout_log, 'stderr': stderr_log}, receipt)
        current = resource.getrusage(resource.RUSAGE_SELF)
        child_cpu, launcher_cpu = used.ru_utime + used.ru_stime, current.ru_utime + current.ru_stime
        child_rss, launcher_rss = used.ru_maxrss * 1024, current.ru_maxrss * 1024
        wall = time.monotonic() - STARTED
        cap_pass = not timeout and child_cpu + launcher_cpu <= LIMITS['CPU_seconds'] and wall <= LIMITS['wall_seconds'] and max(child_rss, launcher_rss) <= LIMITS['memory_bytes']
        receipt.update(actual_child_return_code=child.returncode,
                       actual_child_exit_code=os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
                       actual_child_terminating_signal=os.WTERMSIG(status) if os.WIFSIGNALED(status) else None,
                       child_wall_timeout=timeout, child_group_SIGKILL_after_timeout=killed,
                       whole_child_process_CPU_seconds_including_imports_and_close=child_cpu,
                       launcher_CPU_seconds_before_final_receipt=launcher_cpu,
                       combined_CPU_seconds_before_final_receipt=child_cpu + launcher_cpu,
                       whole_child_peak_RSS_bytes=child_rss, launcher_peak_RSS_bytes=launcher_rss,
                       whole_launch_wall_seconds_before_final_receipt=wall, live_stream_bytes_observed=counts,
                       resource_caps_satisfied=cap_pass)
        result_path, exec_path = ROOT / RESULTS / 'acquire_once/ACQUISITION_RESULT.json', ROOT / RESULTS / 'acquire_once/EXECUTION_RECEIPT.json'
        require(result_path.is_file() and exec_path.is_file(), 'Actual closed inner receipt/result missing')
        result_pin, exec_pin = pin(result_path), pin(exec_path)
        result, execution = read_json(result_pin), read_json(exec_pin)
        receipt.update(ACQUISITION_RESULT_pin=result_pin, EXECUTION_RECEIPT_pin=exec_pin,
                       original_inner_status=result.get('status'),
                       actual_payload_application_BODY_bytes_received=execution.get('payload_application_BODY_bytes_received'))
        complete = 'COMPLETE_EXACT_RAW_ROWS_AND_COMPACT_FILES_NO_SIGNAL_DECODE'
        require(result['status'] == execution['status'] == complete
                and result['scope_sha256'] == execution['scope_sha256'] == args.expected_scope_sha256
                and execution['ACQUISITION_RESULT_pin'] == result_pin
                and execution['resource_caps_satisfied'] is True
                and execution['root_admission_sha256'] == args.expected_root_admission_sha256,
                'Inner acquisition did not complete with exact closed resource/provenance pins')
        for path, expected in ((Path(__file__).resolve(), own), (ROOT / TOOLS / 'acquire_once.py', worker),
                               (scope_path, scope_pin), (admission_path, admission_pin),
                               (ROOT / scope['common_pin']['path'], scope['common_pin'])):
            require(pin(path) == expected, 'Frozen input changed during command')
        receipt.update(status='PASS_WHOLE_CHILD_RESOURCES_AND_COMPLETE_ACQUISITION' if cap_pass and child.returncode == 0 else 'FAIL_WHOLE_CHILD_RESOURCES_OR_CHILD_EXIT')
        ok = cap_pass and child.returncode == 0
    except BaseException as error:
        for signum in TERMINATION_SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        if child is not None and child.returncode is None:
            group_signal(child.pid, signal.SIGKILL)
            try:
                found, status, used = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
                receipt.update(actual_child_return_code=child.returncode,
                               whole_child_process_CPU_seconds_including_imports_and_close=used.ru_utime + used.ru_stime,
                               whole_child_peak_RSS_bytes=used.ru_maxrss * 1024)
            except ChildProcessError:
                receipt['actual_child_reaping_evidence_unavailable'] = True
        receipt.update(status='FAILED_CLOSED_OUTER_METER_NO_RETRY', error_type=type(error).__name__, error=str(error))
    finally:
        for signum in TERMINATION_SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        receipt['output_pins'] = [pin(out / name) for name in ('STDOUT.txt', 'STDERR.txt') if (out / name).is_file()]
        save(out / 'COMMAND_RESOURCES.json', receipt, create_only=True)
        os.close(directory_fd)
        os.close(lock_fd)
        print(json.dumps(receipt, sort_keys=True, allow_nan=False), flush=True)
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
