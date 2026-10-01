#!/usr/bin/env python3
"""Dedicated Linux subreaper evidence; tiny probes and guarded preparation.

The reusable function must run in a fresh, dedicated process. Its evidence is
not an admission path for the SETI pipeline or a complete runtime/host join.
ECHILD establishes termination of this kernel subreaper's adoption scope;
arbitrary process escape, tracing and namespace transitions are not qualified.
The caller must independently observe this supervisor through its termination.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
import types

SCHEMA = 'radio-native-v2-dedicated-subreaper-engineering-v1'
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
MAX_SECONDS = 10.0
MAX_OUTPUT_BYTES = 65536
MAX_REAPED_CHILDREN = 64
MAX_STORAGE_BYTES = 2 * 1024 * 1024
MAX_RSS_BYTES = 512 * 1024 * 1024
PREPARE_MAX_SECONDS = 600.0
CASE_STORAGE_BYTES = 192 * 1024 * 1024
RECEIPT_RESERVATION_BYTES = 131072
DIRECTORY_RESERVATION_BYTES = 65536
# Independently reviewed implementation pins bootstrap admission. Supplied
# bundle hashes cannot select executable validator/fixture implementations.
# Updating either implementation requires reviewing and refreshing this table.
BOOTSTRAP_SOURCE_PINS = {
    'scripts/radio_native_v2_worker_admission.py': {
        'bytes': 30761,
        'sha256': '8c5008fe9f31d0833a4b64958fb4691bdafa01cb01d260984212204eaf0346bf'},
    'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {
        'bytes': 86992,
        'sha256': '28a20154f7a652d9413d8f7fbbb200e627e58c771a401810df4eb5d8e333e2e1'},
}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'real_public_github_mutations': 0,
    'pipeline_integration_qualified': False, 'runtime_closure_qualified': False,
    'host_ledger_join_complete': False, 'automatic_retry': False}

# These sources are deliberately small. The CLI never accepts an arbitrary
# command, input recipe or existing scientific/maximum-size worker entrypoint.
PROBES = {
    'nested-wait': "import subprocess,sys; subprocess.run([sys.executable,'-I','-S','-B','-c',\"import sys; payload=bytearray(2*1024*1024); print('tiny-grandchild')\"],check=True); print('tiny-root')",
    'orphan': "import subprocess,sys,os; subprocess.Popen([sys.executable,'-I','-S','-B','-c',\"import time; time.sleep(0.06); print('tiny-orphan')\"]); os._exit(0)",
    'adopted-nonzero': "import subprocess,sys,os; subprocess.Popen([sys.executable,'-I','-S','-B','-c',\"import time; time.sleep(0.06); raise SystemExit(7)\"]); os._exit(0)",
    'double-fork': "import os,time\nchild=os.fork()\nif child==0:\n grandchild=os.fork()\n if grandchild: os._exit(0)\n time.sleep(0.08); os._exit(0)\nos.waitpid(child,0); os._exit(0)",
    'timeout': "import subprocess,sys,time; subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time; time.sleep(60)']); time.sleep(60)",
    'output-overflow': "import sys; sys.stdout.write('x'*200000); sys.stdout.flush()",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def bounded_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError('Bounded sole-link engineering evidence required')
        chunks = []; remaining = limit + 1
        while remaining:
            raw = os.read(fd, min(65536, remaining))
            if not raw: break
            chunks.append(raw); remaining -= len(raw)
        after = os.fstat(fd)
        raw = b''.join(chunks)
        if len(raw) != before.st_size or (before.st_dev, before.st_ino,
                before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev,
                after.st_ino, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Engineering evidence changed during read')
        return raw
    finally:
        os.close(fd)


def source_module(path, name, expected=None):
    """Compile checked source bytes directly; never load repository bytecode."""
    raw = bounded_bytes(path, 2 * 1024 * 1024)
    observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None and observed != expected:
        raise ValueError('Materialized admission/fixture source pin drift')
    module = types.ModuleType(name); module.__file__ = str(Path(path).absolute())
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def check_admitted_prepare_worker(bundle_path, *, ordinal, expected_bundle_sha256):
    """Read-only structural check; neither launches work nor creates a scope."""
    if not isinstance(expected_bundle_sha256, str) or not re.fullmatch('[a-f0-9]{64}', expected_bundle_sha256):
        raise ValueError('Independently retained exact admission-bundle SHA256 required')
    raw = bounded_bytes(bundle_path, 16 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != expected_bundle_sha256:
        raise ValueError('Admission bundle differs from independently retained byte hash')
    bundle = json.loads(raw)
    code_files = bundle['plan']['code_files']
    own_key = 'scripts/radio_native_v2_process_tree_supervisor.py'
    if pin_file(Path(__file__).resolve()) != code_files[own_key]:
        raise ValueError('Dispatcher source differs from materialized admission pins')
    module_key = 'scripts/radio_native_v2_worker_admission.py'
    # The module is loaded only from the prospectively pinned materialization.
    if code_files.get(module_key) != BOOTSTRAP_SOURCE_PINS[module_key]:
        raise ValueError('Supplied admission implementation differs from dispatcher bootstrap pins')
    admission = source_module(Path(bundle['code_root']) / module_key,
        'pinned_worker_admission', BOOTSTRAP_SOURCE_PINS[module_key])
    argv = admission.expected_worker_argv(bundle, str(Path(bundle_path).absolute()),
        role='prepare', ordinal=ordinal, expected_bundle_sha256=expected_bundle_sha256)
    structural = admission.validate_worker_admission(bundle_path, role='prepare',
        ordinal=ordinal, argv=argv, environment=ENVIRONMENT,
        expected_bundle_sha256=expected_bundle_sha256)
    fixture_key = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
    if code_files.get(fixture_key) != BOOTSTRAP_SOURCE_PINS[fixture_key]:
        raise ValueError('Supplied fixture implementation differs from dispatcher bootstrap pins')
    fixture = source_module(Path(bundle['code_root']) / fixture_key,
        'pinned_preparation_fixture', BOOTSTRAP_SOURCE_PINS[fixture_key])
    return {'schema': SCHEMA + '-admitted-prepare-check', 'role': 'prepare',
        'ordinal': ordinal, 'argv': argv, 'bundle_path': str(Path(bundle_path).absolute()),
        'bundle_sha256': expected_bundle_sha256, 'worker_scope': argv[5],
        'receipt_scope': str(Path(argv[5]) / 'preparation-supervisor'),
        'structural_admission': structural,
        'materialized_fixture_execution_status': fixture.EXECUTION_STATUS,
        'independent_immutable_publication_join_complete': False,
        **AUTHORITY}, fixture


def validate_admitted_prepare_controls(controls):
    expected_keys = {'schema', 'seconds', 'output_bytes', 'reaped_children',
        'case_storage_bytes', 'rss_bytes', 'worker_role'}
    if not isinstance(controls, dict) or set(controls) != expected_keys:
        raise ValueError('Exact admitted preparation controls required')
    if (controls['schema'] != SCHEMA + '-admitted-prepare-controls'
            or controls['worker_role'] != 'prepare'
            or type(controls['seconds']) not in (int, float)
            or not 0 < controls['seconds'] <= PREPARE_MAX_SECONDS
            or type(controls['output_bytes']) is not int or controls['output_bytes'] != MAX_OUTPUT_BYTES
            or type(controls['reaped_children']) is not int or controls['reaped_children'] != MAX_REAPED_CHILDREN
            or type(controls['case_storage_bytes']) is not int or controls['case_storage_bytes'] != CASE_STORAGE_BYTES
            or type(controls['rss_bytes']) is not int or controls['rss_bytes'] != MAX_RSS_BYTES):
        raise ValueError('Original prescribed preparation caps required')


def require_isolated_supervisor_runtime(*, check_environment=False):
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError('Actual isolated no-site no-bytecode supervisor required')
    if check_environment and dict(os.environ) != ENVIRONMENT:
        raise RuntimeError('Exact complete minimal supervisor environment required')


def dispatch_admitted_prepare_worker(bundle_path, scope, *, ordinal,
        expected_bundle_sha256, seconds=PREPARE_MAX_SECONDS):
    started = time.monotonic()
    checked, fixture = check_admitted_prepare_worker(bundle_path, ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256)
    if str(Path(scope).absolute()) != checked['receipt_scope']:
        raise ValueError('Exact admission-bound preparation supervisor scope required')
    controls = {'schema': SCHEMA + '-admitted-prepare-controls', 'seconds': seconds,
        'output_bytes': MAX_OUTPUT_BYTES, 'reaped_children': MAX_REAPED_CHILDREN,
        'case_storage_bytes': CASE_STORAGE_BYTES, 'rss_bytes': MAX_RSS_BYTES,
        'worker_role': 'prepare'}
    validate_admitted_prepare_controls(controls)
    require_isolated_supervisor_runtime()
    # The independently materialized fixture is the actual authority gate.
    # A successful local structural check cannot open this closed branch.
    fixture.require_execution_ready()
    require_isolated_supervisor_runtime(check_environment=True)
    return supervise_engineering_subprocess(checked['argv'], scope, controls,
        dedicated_process=True, input_pin={'kind': 'admission-bound-prepare-worker',
            'bundle_sha256': expected_bundle_sha256, 'role': 'prepare', 'ordinal': ordinal},
        _admitted_dispatch=checked, _started_at=started)


def pin_file(path):
    digest = hashlib.sha256(); count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Regular pinned engineering file required')
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            count += len(raw); digest.update(raw)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Engineering pin changed during hash')
    finally:
        os.close(fd)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def durable_json(path, value):
    raw = canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(raw)
        while view:
            amount = os.write(fd, view)
            if amount <= 0: raise OSError('Incomplete engineering receipt write')
            view = view[amount:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


def storage_bytes(scope):
    logical = allocated = 0
    for path in [scope, *scope.rglob('*')]:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) and (
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError('Ordinary sole-link engineering evidence required')
        logical += info.st_size; allocated += info.st_blocks * 512
    return max(logical, allocated)


def proc_identity(procfs_pid):
    text = (Path('/proc') / str(procfs_pid) / 'status').read_text()
    parent = re.search(r'^PPid:\s+(\d+)', text, re.M)
    namespace = re.search(r'^NSpid:\s+([0-9 \t]+)$', text, re.M)
    if not parent or not namespace:
        raise ValueError('Kernel PPid and PID-namespace mapping required')
    chain = [int(value) for value in namespace.group(1).split()]
    ticks = (Path('/proc') / str(procfs_pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]
    return {'procfs_pid': procfs_pid, 'parent_procfs_pid': int(parent.group(1)),
        'namespace_pid_chain': chain, 'procfs_start_ticks': ticks}


def direct_children(observer):
    found = []
    depth = len(observer['namespace_pid_chain']) - 1
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            candidate = proc_identity(int(entry.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if candidate['parent_procfs_pid'] != observer['procfs_pid']: continue
        if len(candidate['namespace_pid_chain']) <= depth:
            raise ValueError('Adopted child is outside observer PID namespace')
        candidate['namespace_pid'] = candidate['namespace_pid_chain'][depth]
        found.append(candidate)
    return found


def set_subreaper():
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Dedicated subreaper component requires Linux')
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    enabled = ctypes.c_int()
    if library.prctl(37, ctypes.byref(enabled), 0, 0, 0) != 0 or enabled.value != 1:
        raise RuntimeError('PR_GET_CHILD_SUBREAPER did not verify activation')


def cancel_direct_children(observer):
    """Signal independently mapped direct/adopted children through pidfds only."""
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Identity-safe pidfd cancellation is unavailable')
    cancellations = []
    for candidate in direct_children(observer):
        try:
            fd = os.pidfd_open(candidate['namespace_pid'], 0)
        except ProcessLookupError:
            continue
        try:
            after = proc_identity(candidate['procfs_pid'])
            if (after['procfs_start_ticks'] != candidate['procfs_start_ticks']
                    or after['parent_procfs_pid'] != observer['procfs_pid']):
                raise ValueError('Cancellation PID mapping changed before pidfd signal')
            signal.pidfd_send_signal(fd, signal.SIGKILL)
            cancellations.append(candidate)
        except ProcessLookupError:
            pass
        finally:
            os.close(fd)
    return cancellations


def validate_controls(controls):
    if set(controls) != {'schema', 'seconds', 'output_bytes', 'reaped_children'} or controls['schema'] != SCHEMA + '-controls':
        raise ValueError('Exact dedicated engineering control schema required')
    seconds = controls['seconds']; output = controls['output_bytes']; children = controls['reaped_children']
    if type(seconds) not in (int, float) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('Positive engineering deadline at most ten seconds required')
    if type(output) is not int or not 0 < output <= MAX_OUTPUT_BYTES:
        raise ValueError('Bounded engineering output allowance required')
    if type(children) is not int or not 0 < children <= MAX_REAPED_CHILDREN:
        raise ValueError('Bounded engineering child-receipt count required')


def supervise_engineering_subprocess(argv, scope, controls, *, dedicated_process=False,
        input_pin=None, _admitted_dispatch=None, _started_at=None):
    """Reusable future component; only call from a fresh dedicated process.

    Generic argv admission is the future integrating caller's responsibility.
    No arbitrary-argv CLI is exposed, and this function grants no scientific or
    large-source authority. The original deadline includes cleanup; exceeding
    it remains CLOSED_FAILED even when cleanup reaches ECHILD afterwards.
    """
    if dedicated_process is not True:
        raise RuntimeError('Fresh dedicated-process invocation required')
    require_isolated_supervisor_runtime()
    shared_storage_root = None
    if _admitted_dispatch is None:
        validate_controls(controls)
        if _started_at is not None:
            raise ValueError('Custom dispatch timing requires checked worker admission')
    else:
        validate_admitted_prepare_controls(controls)
        checked, fixture = check_admitted_prepare_worker(_admitted_dispatch['bundle_path'],
            ordinal=_admitted_dispatch['ordinal'],
            expected_bundle_sha256=_admitted_dispatch['bundle_sha256'])
        if (checked != _admitted_dispatch or argv != checked['argv']
                or str(Path(scope).absolute()) != checked['receipt_scope']):
            raise ValueError('Exact read-only checked preparation dispatch required')
        fixture.require_execution_ready()
        shared_storage_root = Path(checked['worker_scope'])
    if not isinstance(argv, list) or not argv or any(type(item) is not str for item in argv):
        raise ValueError('Exact engineering argv strings required')
    if not Path(argv[0]).is_absolute() or sum(len(item.encode()) for item in argv) > 32768:
        raise ValueError('Absolute executable and bounded engineering argv required')
    started = time.monotonic() if _started_at is None else _started_at
    if type(started) not in (int, float) or not 0 < started <= time.monotonic():
        raise ValueError('Valid admission-inclusive monotonic dispatch start required')
    deadline = started + controls['seconds']
    if time.monotonic() >= deadline:
        raise RuntimeError('Admission checks consumed the fixed preparation deadline')
    observer = proc_identity(int(os.readlink('/proc/self')))
    if len(list((Path('/proc/self/task')).iterdir())) != 1 or direct_children(observer):
        raise RuntimeError('Dedicated supervisor must start with one thread and no children')
    # Establish cancellation support before creating a scope or spawning work.
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Identity-safe pidfd cancellation is unavailable')
    set_subreaper()
    scope = Path(scope).absolute()
    scope.mkdir(mode=0o700, exist_ok=False)
    identity = {'procfs_pid': observer['procfs_pid'], 'namespace_pid': os.getpid()}
    durable_json(scope / 'supervisor-identity.json', identity)
    code_pin = pin_file(Path(__file__).resolve())
    runtime_pin = pin_file(Path(sys.executable).resolve())
    durable_json(scope / 'controls.json', controls)
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    observed_bytes = {'stdout': 0, 'stderr': 0}
    selector = selectors.DefaultSelector()
    child = None; root_identity = None; root_status = None; rows = []
    echild = False; reason = None; cancellation_count = 0; reap_count = 0; kernel_peak = 0
    setup_error = None
    try:
        if time.monotonic() >= deadline:
            raise RuntimeError('Supervisor setup consumed the fixed preparation deadline')
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=ENVIRONMENT, close_fds=True)
        candidates = [row for row in direct_children(observer) if row['namespace_pid'] == child.pid]
        if len(candidates) != 1:
            raise RuntimeError('Unique launched root PID mapping required')
        root_identity = candidates[0]
        for name, stream in (('stdout', child.stdout), ('stderr', child.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while not echild or selector.get_map():
            for key, _ in selector.select(0.005):
                raw = os.read(key.fileobj.fileno(), 65536)
                if not raw:
                    selector.unregister(key.fileobj); key.fileobj.close(); continue
                name = key.data; observed_bytes[name] += len(raw)
                remaining = max(0, controls['output_bytes'] - len(output[name]))
                output[name].extend(raw[:remaining])
                if observed_bytes[name] > controls['output_bytes']:
                    reason = reason or 'Bounded engineering output cap exceeded'
            while True:
                try:
                    pid, status, usage = os.wait4(-1, os.WNOHANG)
                except ChildProcessError:
                    echild = True; break
                if not pid: break
                reap_count += 1
                kernel_peak = max(kernel_peak, usage.ru_maxrss * 1024)
                exit_code = os.waitstatus_to_exitcode(status)
                is_root = pid == child.pid
                if is_root:
                    root_status = exit_code; child.returncode = exit_code
                if len(rows) < controls['reaped_children']:
                    rows.append({'namespace_pid': pid, 'kind': 'launched_root' if is_root else 'adopted_orphan',
                        'exit_code': exit_code, 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
                        'wait4_user_seconds': usage.ru_utime, 'wait4_system_seconds': usage.ru_stime})
                if reap_count > controls['reaped_children']:
                    reason = reason or 'Bounded engineering reaped-child count exceeded'
                if exit_code != 0:
                    reason = reason or 'Reaped engineering process returned nonzero'
                if usage.ru_maxrss * 1024 > MAX_RSS_BYTES:
                    reason = reason or 'Engineering individual-process RSS cap exceeded'
            if time.monotonic() > deadline:
                reason = reason or 'Fixed engineering scope deadline exceeded'
            if storage_bytes(scope) + 2 * RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > MAX_STORAGE_BYTES:
                reason = reason or 'Bounded engineering receipt storage allowance exceeded'
            if shared_storage_root is not None and (
                    storage_bytes(shared_storage_root) + 2 * RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > CASE_STORAGE_BYTES):
                reason = reason or 'Original preparation whole-case storage allowance exceeded'
            if reason and not echild:
                cancellation_count += len(cancel_direct_children(observer))
                # Cancellation may cause another orphan generation to be
                # adopted. Each subsequent tick discovers and cancels it.
            if reason and echild:
                for key in list(selector.get_map().values()):
                    selector.unregister(key.fileobj); key.fileobj.close()
                break
            if reason and time.monotonic() > deadline + 1.0:
                # A killed task in uninterruptible sleep cannot be promised
                # reaped. Preserve a closed result for independent outer kill.
                break
        if not echild or root_status is None:
            reason = reason or 'Subreaper did not reach root status and terminal ECHILD'
    except BaseException as failure:
        setup_error = repr(failure)
        reason = reason or 'Dedicated engineering supervisor failed: ' + setup_error
        if child is not None:
            try:
                cancellation_count += len(cancel_direct_children(observer))
                while time.monotonic() <= deadline + 1.0:
                    try: pid, status, usage = os.wait4(-1, os.WNOHANG)
                    except ChildProcessError: echild = True; break
                    if not pid:
                        cancellation_count += len(cancel_direct_children(observer)); time.sleep(0.005); continue
                    reap_count += 1
                    kernel_peak = max(kernel_peak, usage.ru_maxrss * 1024)
                    if pid == child.pid:
                        root_status = os.waitstatus_to_exitcode(status); child.returncode = root_status
                    if len(rows) < controls['reaped_children']:
                        rows.append({'namespace_pid': pid, 'kind': 'launched_root' if pid == child.pid else 'adopted_orphan',
                            'exit_code': os.waitstatus_to_exitcode(status), 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
                            'wait4_user_seconds': usage.ru_utime, 'wait4_system_seconds': usage.ru_stime})
            except BaseException as cleanup_failure:
                reason += '; identity-safe cleanup failed: ' + repr(cleanup_failure)
    finally:
        for key in list(selector.get_map().values()):
            selector.unregister(key.fileobj); key.fileobj.close()
        selector.close()
        if child is not None:
            for stream in (child.stdout, child.stderr):
                if stream is not None: stream.close()
    maximum = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, kernel_peak)
    if maximum > MAX_RSS_BYTES:
        reason = reason or 'Engineering supervisor or reaped-process RSS cap exceeded'
    elapsed = time.monotonic() - started
    if elapsed > controls['seconds']:
        reason = reason or 'Fixed engineering scope deadline exceeded'
    # Raw stdout is counted and discarded. It is never duplicated into files.
    receipt = {'schema': SCHEMA, 'status': 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' if reason is None and echild and root_status == 0 else 'CLOSED_FAILED',
        'reason': reason, 'supervisor_identity': identity, 'subreaper_set_and_get_verified': True,
        'root_identity': root_identity, 'root_exit_code': root_status,
        'sole_wait4_owner': True, 'subreaper_scope_reaped_to_echild': echild,
        'reaped_processes': rows, 'reaped_process_count': reap_count,
        'maximum_individual_process_rss_bytes': maximum,
        'concurrent_process_rss_sum_measured': False,
        'complete_process_tree_qualified': False, 'complete_descendant_wait_chain_verified': False,
        'procfs_descendant_escape_detection_complete': False,
        'tree_termination_coverage': 'SUBREAPER_ECHILD_OBSERVED' if echild else 'UNKNOWN_ON_FAILURE',
        'observed_output_bytes': observed_bytes, 'retained_output_bytes': {name: len(raw) for name, raw in output.items()},
        'raw_stdout_duplicate_written': False, 'raw_stderr_duplicate_written': False,
        'stdout_sha256_of_retained_prefix': hashlib.sha256(output['stdout']).hexdigest(),
        'stderr_sha256_of_retained_prefix': hashlib.sha256(output['stderr']).hexdigest(),
        'pidfd_cancellation_count': cancellation_count,
        'failed_cleanup_grace_seconds': 1.0,
        'elapsed_seconds_before_final_receipt_fsync': elapsed,
        'supervisor_final_receipt_and_termination_independently_observed': False,
        'shared_storage_and_original_case_run_limits_joined': False,
        'controls': controls, 'controls_sha256': hashlib.sha256(canonical(controls)).hexdigest(),
        'supervisor_code': code_pin, 'python_executable': {'path': str(Path(sys.executable).resolve()), **runtime_pin},
        'engineering_input_pin': input_pin, 'child_environment': ENVIRONMENT,
        'storage_bytes_before_receipt': storage_bytes(scope), 'receipt_storage_reserved_bytes': RECEIPT_RESERVATION_BYTES,
        'directory_storage_reserved_bytes': DIRECTORY_RESERVATION_BYTES,
        'whole_case_storage_accounted': shared_storage_root is not None,
        'admitted_preparation_check': _admitted_dispatch,
        'limitations': ['Kernel subreaper adoption scope only; process escape/tracing/namespace transitions are unqualified.',
            'Outer supervisor lifetime, complete runtime closure, pipeline admission and storage/time joins are required separately.'],
        **AUTHORITY}
    # Persist measurements with a pending status before deriving disposition.
    # No durable success is left behind by a subsequent filesystem check.
    pending = {**receipt, 'status': 'PENDING_FILESYSTEM_DISPOSITION'}
    if len(canonical(pending)) + 1 > RECEIPT_RESERVATION_BYTES:
        raise RuntimeError('Bounded supervisor measurements reservation exceeded')
    durable_json(scope / 'subreaper-measurements.json', pending)
    checked_storage = storage_bytes(scope)
    if checked_storage + RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > MAX_STORAGE_BYTES:
        reason = reason or 'Final engineering receipt storage cap reservation exceeded'
    shared_storage = None
    if shared_storage_root is not None:
        try:
            shared_storage = storage_bytes(shared_storage_root)
            if shared_storage + RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > CASE_STORAGE_BYTES:
                reason = reason or 'Final original whole-case storage cap reservation exceeded'
        except (ValueError, OSError) as failure:
            reason = reason or 'Final whole-case filesystem checks failed: ' + repr(failure)
    if time.monotonic() > deadline:
        reason = reason or 'Fixed engineering scope deadline exceeded after filesystem checks'
    receipt.update({'status': 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' if reason is None and echild and root_status == 0 else 'CLOSED_FAILED',
        'reason': reason, 'measurements_fsynced_before_disposition': True,
        'filesystem_checks_completed_before_disposition': True,
        'storage_bytes_after_measurements': checked_storage,
        'whole_case_storage_bytes_before_final_receipt': shared_storage,
        'elapsed_seconds_before_final_receipt_fsync': time.monotonic() - started})
    if len(canonical(receipt)) + 1 > RECEIPT_RESERVATION_BYTES:
        raise RuntimeError('Bounded final supervisor receipt reservation exceeded')
    durable_json(scope / 'subreaper-receipt.json', receipt)
    # The integrating outer observer covers this fsync, final allocation and
    # process termination. This local receipt explicitly leaves that join false.
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe', choices=sorted(PROBES))
    mode.add_argument('--admitted-prepare-worker', action='store_true')
    mode.add_argument('--admission-check-only', action='store_true')
    parser.add_argument('--scope', type=Path)
    parser.add_argument('--admission-bundle', type=Path)
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--ordinal', type=int)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--output-bytes', type=int, default=MAX_OUTPUT_BYTES)
    parser.add_argument('--reaped-children', type=int, default=MAX_REAPED_CHILDREN)
    args = parser.parse_args()
    if args.admitted_prepare_worker or args.admission_check_only:
        if any(value is None for value in (args.admission_bundle, args.bundle_sha256, args.ordinal)):
            parser.error('Exact admission bundle, retained SHA256 and outer ordinal required')
        if args.output_bytes != MAX_OUTPUT_BYTES or args.reaped_children != MAX_REAPED_CHILDREN:
            parser.error('Admitted preparation output and child caps are fixed')
        if args.admission_check_only:
            if args.scope is not None or args.seconds is not None:
                parser.error('Admission-check-only accepts no receipt scope or timing mutation')
            checked, _ = check_admitted_prepare_worker(args.admission_bundle,
                ordinal=args.ordinal, expected_bundle_sha256=args.bundle_sha256)
            print(canonical(checked).decode()); return 0
        if args.scope is None:
            parser.error('Exact admission-bound preparation supervisor scope required')
        receipt = dispatch_admitted_prepare_worker(args.admission_bundle, args.scope,
            ordinal=args.ordinal, expected_bundle_sha256=args.bundle_sha256,
            seconds=PREPARE_MAX_SECONDS if args.seconds is None else args.seconds)
        print(canonical({'schema': SCHEMA, 'status': receipt['status'], 'reason': receipt['reason'], **AUTHORITY}).decode())
        return 0 if receipt['status'] == 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' else 2
    if args.scope is None or any(value is not None for value in (args.admission_bundle, args.bundle_sha256, args.ordinal)):
        parser.error('Tiny probe requires a fresh scope and accepts no pipeline admission')
    source = PROBES[args.probe]
    controls = {'schema': SCHEMA + '-controls', 'seconds': 3.0 if args.seconds is None else args.seconds,
        'output_bytes': args.output_bytes, 'reaped_children': args.reaped_children}
    receipt = supervise_engineering_subprocess([str(Path(sys.executable).resolve()), '-I', '-S', '-B', '-c', source],
        args.scope, controls, dedicated_process=True,
        input_pin={'kind': 'fixed_tiny_engineering_probe', 'probe': args.probe,
            'source_bytes': len(source.encode()), 'source_sha256': hashlib.sha256(source.encode()).hexdigest()})
    print(canonical({'schema': SCHEMA, 'status': receipt['status'], 'reason': receipt['reason'],
        'subreaper_scope_reaped_to_echild': receipt['subreaper_scope_reaped_to_echild'], **AUTHORITY}).decode())
    return 0 if receipt['status'] == 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
