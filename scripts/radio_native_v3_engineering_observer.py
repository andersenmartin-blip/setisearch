#!/usr/bin/env python3
"""Finite external observation of the fixed, independently admitted v3 launcher.

The immutable capsule digest is an external caller trust input. A capsule cannot
authorize scientific, native, RNG or telescope execution. This observer adds no
marker, claim, journal, retry or scope-creation route. It observes the launcher
through wait4/ECHILD, then independently replays its retained descendant join.
Its final checks cover its retained bytes and elapsed interval; they cannot
certify this observer's own future termination or broader kernel integrity.
"""
import argparse
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

REPO = Path(__file__).resolve().parents[1]
SELF = 'scripts/radio_native_v3_engineering_observer.py'
LAUNCHER = 'scripts/radio_native_v3_compact_control_launch.py'
FINALIZER = 'scripts/radio_native_v3_resource_finalization.py'
SUPERVISOR = 'scripts/radio_native_v3_process_tree_supervisor.py'
SOURCE_PATHS = frozenset((SELF, LAUNCHER, FINALIZER, SUPERVISOR))
CAPSULE_PATH = 'results_radio_native_v3_predispatch_20261003e/observer-capsule.json'
CONFIG_PATH = 'results_radio_native_v3_predispatch_20261003e/launch-config.json'
SCOPE_NAME = 'results_radio_native_v3_compact_eight_input_control_20261003e'
SCHEMA = 'radio-native-v3-engineering-observer-v1'
CAPSULE_SCHEMA = 'radio-native-v3-engineering-observer-capsule-v1'
NAMESPACE = 'radio-native-v3-compact-eight-input-control-20261003e'
STDOUT_NAME = 'engineering-observer-stdout.log'
STDERR_NAME = 'engineering-observer-stderr.log'
OBSERVATION_NAME = 'engineering-observer-observation.json'
DISPOSITION_NAME = 'engineering-observer-disposition.json'
FAILURE_NAME = 'engineering-observer-closed-failure.json'
OUTPUT_NAMES = (STDOUT_NAME, STDERR_NAME, OBSERVATION_NAME, DISPOSITION_NAME, FAILURE_NAME)
STDOUT_CAP = 65536
STDERR_CAP = 8192
OBSERVATION_CAP = 16384
DISPOSITION_CAP = 32768
FAILURE_CAP = 8192
MAX_SOURCE_BYTES = 2*1024**2
MAX_JSON_BYTES = 16*1024**2
MAX_EXECUTABLE_BYTES = 64*1024**2
MAX_REAPED_CHILDREN = 64
RUN_SECONDS = 4800
RSS_BYTES = 512*1024**2
LIMITS = {'run_seconds': RUN_SECONDS, 'case_seconds': 600,
    'rss_bytes': RSS_BYTES, 'case_storage_bytes': 192*1024**2,
    'run_storage_bytes': 1536*1024**2, 'terminal_metadata_bytes': 256*1024,
    'terminal_directory_growth_bytes': 65536,
    'stdout_bytes': STDOUT_CAP, 'stderr_bytes': STDERR_CAP}
ENVIRONMENT_FIXED = {'LANG':'C', 'LC_ALL':'C', 'HOME':'/nonexistent',
    'PYTHONSAFEPATH':'1', 'PYTHONNOUSERSITE':'1', 'GIT_CONFIG_NOSYSTEM':'1',
    'GIT_CONFIG_GLOBAL':'/dev/null', 'GIT_TERMINAL_PROMPT':'0', 'GIT_NO_LAZY_FETCH':'1'}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}
_entered = False


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _absolute(value):
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or len(value.encode()) > 4096 or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Canonical bounded absolute observer path required')
    return value


def _pin(value, *, maximum):
    if (type(value) is not dict or set(value) != {'bytes','sha256'}
            or type(value['bytes']) is not int or not 0 <= value['bytes'] <= maximum
            or type(value['sha256']) is not str
            or not re.fullmatch('[a-f0-9]{64}', value['sha256'])):
        raise ValueError('Exact bounded immutable byte pin required')
    return value


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid,
        info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _directory(path):
    """Open every named directory without aliases, retaining ancestor identities."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [(_identity(os.fstat(fd))[:2])]
    try:
        for part in _absolute(path)[1:].split('/'):
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            if _identity(before)[:2] != _identity(os.fstat(child))[:2]:
                os.close(child)
                raise ValueError('Observer ancestor changed during open')
            os.close(fd); fd = child; chain.append(_identity(os.fstat(fd))[:2])
        return fd, chain
    except BaseException:
        os.close(fd); raise


def read_pinned(path, *, expected=None, maximum=MAX_SOURCE_BYTES, retain=False, sole_link=True):
    path = _absolute(path); parent, name = path.rsplit('/', 1)
    directory, chain = _directory(parent); fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or (sole_link and before.st_nlink != 1)
                or before.st_size > maximum):
            raise ValueError('Bounded stable ordinary observer material required')
        digest = hashlib.sha256(); count = 0; chunks = []
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            count += len(raw)
            if count > maximum: raise ValueError('Observer material byte cap exceeded')
            digest.update(raw)
            if retain: chunks.append(raw)
        after = os.fstat(fd); named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        reopened, current_chain = _directory(parent)
        os.close(reopened)
        if (chain != current_chain or _identity(before) != _identity(after)
                or _identity(after) != _identity(named) or count != after.st_size):
            raise ValueError('Observer material or ancestry changed during read')
        pin = {'bytes':count, 'sha256':digest.hexdigest()}
        if expected is not None and pin != expected:
            raise ValueError('Observer material differs from independently retained pin')
        return pin, b''.join(chunks) if retain else None
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _json(raw, *, require_canonical=True):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate observer JSON property refused')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite observer JSON refused')))
    if type(value) is not dict: raise ValueError('Exact observer JSON object required')
    if require_canonical and raw != canonical(value)+b'\n':
        raise ValueError('Canonical observer JSON plus newline required')
    return value


def validate_capsule(capsule, *, root=REPO):
    root = _absolute(root)
    required = {'schema','namespace','repository_root','scope','python','environment',
        'source_pins','launch_config','limits','authority'}
    if type(capsule) is not dict or set(capsule) != required:
        raise ValueError('Exact independently authenticated observer capsule required')
    if (capsule['schema'] != CAPSULE_SCHEMA or capsule['namespace'] != NAMESPACE
            or capsule['repository_root'] != root or capsule['scope'] != root+'/'+SCOPE_NAME):
        raise ValueError('Fixed current repository and e scope required')
    python = capsule['python']
    if type(python) is not dict or set(python) != {'path','bytes','sha256'}:
        raise ValueError('Exact independently pinned Python executable required')
    _absolute(python['path']); _pin({key:python[key] for key in ('bytes','sha256')}, maximum=MAX_EXECUTABLE_BYTES)
    if not python['bytes']: raise ValueError('Nonempty pinned Python executable required')
    environment = capsule['environment']
    if (type(environment) is not dict or set(environment) != {'PATH',*ENVIRONMENT_FIXED}
            or any(type(v) is not str for v in environment.values())
            or any(environment.get(k) != v for k,v in ENVIRONMENT_FIXED.items())):
        raise ValueError('Exact ten-value frozen observer environment required')
    for part in environment['PATH'].split(':'): _absolute(part)
    if type(capsule['source_pins']) is not dict or set(capsule['source_pins']) != SOURCE_PATHS:
        raise ValueError('Exactly four independently reviewed observer source pins required')
    for pin in capsule['source_pins'].values():
        _pin(pin, maximum=MAX_SOURCE_BYTES)
        if not pin['bytes']: raise ValueError('Nonempty observer source required')
    config = capsule['launch_config']
    if type(config) is not dict or set(config) != {'path','bytes','sha256'} or config['path'] != CONFIG_PATH:
        raise ValueError('Exact fixed, charged predispatch launch-config path required')
    _pin({key:config[key] for key in ('bytes','sha256')}, maximum=65536)
    if canonical(capsule['limits']) != canonical(LIMITS) or canonical(capsule['authority']) != canonical(AUTHORITY):
        raise ValueError('Observer capsule cannot enlarge limits or grant execution authority')
    return True


def _source_module(relative, pin):
    _, raw = read_pinned(REPO/relative, expected=pin, retain=True)
    module = types.ModuleType('pinned_external_'+Path(relative).stem)
    module.__file__ = str(REPO/relative)
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def _write_exclusive(path, raw, maximum):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError('Bounded raw observer output required')
    path = _absolute(path); parent, name = path.rsplit('/', 1)
    directory, _ = _directory(parent); fd = None
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400, dir_fd=directory)
        position = 0
        while position < len(raw):
            amount = os.write(fd, raw[position:])
            if amount <= 0: raise OSError('Incomplete observer evidence write')
            position += amount
        os.fsync(fd)
        os.close(fd); fd = None; os.fsync(directory)
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)
    return read_pinned(path, expected={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}, maximum=maximum)[0]


def observe_child(argv, environment, *, deadline_monotonic_ns, supervisor,
        stdout_cap=STDOUT_CAP, stderr_cap=STDERR_CAP):
    """Observe one child and adopted descendants; generic only for tiny tests."""
    if (type(argv) is not list or not argv or any(type(x) is not str for x in argv)
            or type(environment) is not dict
            or any(type(k) is not str or type(v) is not str for k,v in environment.items())
            or type(deadline_monotonic_ns) is not int or deadline_monotonic_ns <= time.monotonic_ns()
            or type(stdout_cap) is not int or not 0 < stdout_cap <= STDOUT_CAP
            or type(stderr_cap) is not int or not 0 < stderr_cap <= STDERR_CAP):
        raise ValueError('Exact bounded external-child observation contract required')
    if not sys.platform.startswith('linux') or not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
        raise ValueError('Linux wait4, subreaper and identity-safe cancellation required')
    observer = supervisor.proc_identity(int(os.readlink('/proc/self')))
    if len(list(Path('/proc/self/task').iterdir())) != 1 or supervisor.direct_children(observer):
        raise ValueError('Dedicated external observer must start with one thread and no children')
    previous = supervisor.ctypes.c_int()
    library = supervisor.ctypes.CDLL(None, use_errno=True)
    if library.prctl(37, supervisor.ctypes.byref(previous), 0, 0, 0) != 0:
        raise OSError(supervisor.ctypes.get_errno(), 'Cannot read prior subreaper state')
    supervisor.set_subreaper()
    start = time.monotonic_ns(); child = None; selector = selectors.DefaultSelector()
    streams = {}; output = {'stdout':bytearray(),'stderr':bytearray()}
    counts = {'stdout':0,'stderr':0}; caps = {'stdout':stdout_cap,'stderr':stderr_cap}
    rows = []; root_exit = None; root_reaped = False; echild = False
    reason = None; cleanup_deadline = None; cancellation_count = 0
    try:
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, cwd=str(REPO), start_new_session=True,
            preexec_fn=supervisor.install_child_escape_guard)
        streams = {child.stdout:'stdout', child.stderr:'stderr'}
        for pipe in streams:
            os.set_blocking(pipe.fileno(), False); selector.register(pipe, selectors.EVENT_READ)
        while True:
            while True:
                try: waited, status, usage = os.wait4(-1, os.WNOHANG)
                except ChildProcessError:
                    echild = True; break
                if not waited: break
                peak = int(usage.ru_maxrss)*1024
                if len(rows) >= MAX_REAPED_CHILDREN:
                    reason = reason or 'External observation wait4 row capacity exceeded'
                else:
                    rows.append({'namespace_pid':waited,'wait_status':status,
                        'exit_code':os.waitstatus_to_exitcode(status),'wait4_ru_maxrss_bytes':peak,
                        'wait4_user_seconds':usage.ru_utime,'wait4_system_seconds':usage.ru_stime})
                if waited == child.pid:
                    root_reaped = True; root_exit = os.waitstatus_to_exitcode(status)
                    child.returncode = root_exit
                if peak > RSS_BYTES: reason = reason or 'Original512MiB observed individual RSS exceeded'
            now = time.monotonic_ns()
            if reason is None and now >= deadline_monotonic_ns:
                reason = 'Original external observation deadline exceeded'
            if reason is not None:
                if cleanup_deadline is None: cleanup_deadline = now+10**9
                cancellation_count += len(supervisor.cancel_direct_children(observer))
                if echild or now >= cleanup_deadline: break
            elif root_reaped and echild and not selector.get_map(): break
            delay = max(0.0,min(0.005,((cleanup_deadline or deadline_monotonic_ns)-now)/1e9))
            for key,_ in selector.select(delay):
                pipe = key.fileobj; label = streams[pipe]
                raw = os.read(pipe.fileno(),65536)
                if not raw:
                    selector.unregister(pipe); pipe.close(); continue
                counts[label] += len(raw)
                output[label].extend(raw[:max(0,caps[label]-len(output[label]))])
                if counts[label] > caps[label]: reason = reason or label+' exceeded retained output cap'
    except BaseException as failure:
        reason = reason or 'External observation failed: '+type(failure).__name__
        if child is not None:
            cleanup_deadline = time.monotonic_ns()+10**9
            while time.monotonic_ns() < cleanup_deadline:
                supervisor.cancel_direct_children(observer)
                try: waited,status,usage = os.wait4(-1,os.WNOHANG)
                except ChildProcessError: echild = True; break
                if waited:
                    if waited == child.pid:
                        root_reaped=True; root_exit=os.waitstatus_to_exitcode(status);child.returncode=root_exit
                    if len(rows)<MAX_REAPED_CHILDREN:
                        rows.append({'namespace_pid':waited,'wait_status':status,
                            'exit_code':os.waitstatus_to_exitcode(status),'wait4_ru_maxrss_bytes':int(usage.ru_maxrss)*1024,
                            'wait4_user_seconds':usage.ru_utime,'wait4_system_seconds':usage.ru_stime})
                else: time.sleep(0.005)
    finally:
        pipes_drained = not selector.get_map()
        for pipe in streams:
            if not pipe.closed: pipe.close()
        selector.close()
        # Restore only after ECHILD; a failed cleanup retains adoption protection.
        if echild and library.prctl(36, previous.value, 0, 0, 0) != 0:
            reason = reason or 'External observer subreaper restoration failed'
    end = time.monotonic_ns()
    if not root_reaped or not echild: reason = reason or 'Incomplete bounded terminal wait4/ECHILD cleanup'
    observation = {'schema':SCHEMA+'-child-observation','observed_argv':argv,
        'child_environment':environment,'namespace_child_pid':child.pid if child else None,
        'monotonic_start_ns':start,'monotonic_end_ns':end,'elapsed_seconds':(end-start)/1e9,
        'exit_code':root_exit,'reason':reason,'direct_child_reaped':root_reaped,
        'includes_entire_direct_child_lifetime':root_reaped,
        'subreaper_set_and_get_verified':True,'subreaper_scope_reaped_to_echild':echild,
        'declared_namespace_tracing_escape_guard_inherited':True,
        'kernel_integrity_or_general_sandbox_qualified':False,
        'reaped_processes':rows,'cancellation_count':cancellation_count,
        'maximum_observed_individual_rss_bytes':max((r['wait4_ru_maxrss_bytes'] for r in rows),default=0),
        'complete_pipe_output':reason is None and pipes_drained,
        'observed_output_bytes':counts,'retained_output_bytes':{k:len(v) for k,v in output.items()},
        'terminal_observer_own_future_termination_covered':False}
    if len(canonical(observation))+1>OBSERVATION_CAP:
        raise ValueError('Bounded external observation serialization exceeded')
    return observation, bytes(output['stdout']), bytes(output['stderr'])


def replay_launcher(scope, stdout, *, finalizer, python):
    """Replay retained material report and immutable launcher summary after exit."""
    scope = Path(scope)
    printed = _json(stdout)
    retained, retained_pin = finalizer.read_pinned_json(scope/'compact-control-launch-disposition.json', maximum=32768)
    finalizer.verify_launcher_completion_reference(printed,retained,retained_pin)
    if (retained.get('schema') != 'radio-native-v2-compact-control-launch-v1-disposition'
            or retained.get('status') != 'OBSERVED_FIXTURE_CHILD_JOIN_PASSED'
            or retained.get('scope') != str(scope)
            or retained.get('fixture_child_complete_wait4_lifetime_observed') is not True
            or retained.get('independently_observed_fixture_child_join_qualified') is not True
            or retained.get('terminal_observer_own_future_termination_covered') is not False):
        raise ValueError('Retained launcher is not the exact pending outer-observer contract')
    for key,value in AUTHORITY.items():
        if canonical(retained.get(key)) != canonical(value):
            raise ValueError('Launcher disposition changed disabled authority: '+key)
    _, input_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_INPUT_NAME)
    _, report_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_NAME)
    _, writer_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_WRITER_OBSERVATION_NAME)
    writer_argv = [python,'-I','-S','-B',str(scope/'frozen-code'/FINALIZER),
        '--persist-final-report','--scope',str(scope),
        '--input-bytes',str(input_pin['bytes']),'--input-sha256',input_pin['sha256']]
    joined = finalizer.join_final_report_lifetime(scope,expected_input_pin=input_pin,
        expected_report_pin=report_pin,expected_writer_observation_pin=writer_pin,
        expected_writer_argv=writer_argv)
    _, raw_fixture_stdout = read_pinned(scope/'compact-control-launch-stdout.log',
        expected=retained['fixture_stdout_pin'], maximum=65536, retain=True)
    # Terminal observer files legitimately change the current storage inventory.
    # The source-pinned compact reference fixes every persisted join/core field;
    # the one dynamic postwriter allocation is measured separately below.
    finalizer.verify_final_report_join_reference(_json(raw_fixture_stdout),joined)
    if joined.get('complete_resource_measurement_join_qualified') is not True:
        raise ValueError('Independent descendant report join remains incomplete')
    worker,worker_pin = finalizer.read_pinned_json(scope/'worker-result.json')
    cases,_ = finalizer._worker_cases(worker)
    external = finalizer.observe_authenticated_ledger_storage(scope)
    expected_external = retained['storage_after_fixture_termination_with_remaining_terminal_allowance']['external_ledger_inventory_sha256']
    finalizer._match_retained_ledger(external,expected_external)
    return {'launcher_disposition_pin':retained_pin,'worker_result_pin':worker_pin,
        'persisted_final_report_pin':report_pin,'final_report_writer_observation_pin':writer_pin,
        'descendant_join_replayed':True}, cases, expected_external


def _measure(scope, finalizer, cases, expected_external, anchor):
    external = finalizer.observe_authenticated_ledger_storage(scope)
    finalizer._match_retained_ledger(external,expected_external)
    storage = finalizer.allocate_storage(finalizer.storage_inventory(scope),external_inventory=external)
    elapsed = finalizer.allocate_elapsed(cases,(time.monotonic_ns()-anchor)/1e9)
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>RSS_BYTES:
        raise ValueError('Original512MiB external observer process RSS exceeded')
    return storage,elapsed


def run_observer(capsule, *, capsule_pin, admission_start_monotonic_ns):
    global _entered
    if _entered: raise RuntimeError('One external observer entry only; no retry/resume')
    _entered=True
    now=time.monotonic_ns();anchor=admission_start_monotonic_ns
    if type(anchor) is not int or not 0<anchor<=now:
        raise ValueError('Actual external observer entry monotonic anchor required')
    validate_capsule(capsule)
    _pin(capsule_pin,maximum=65536)
    if os.environ != capsule['environment']:
        raise ValueError('Actual external observer environment differs from frozen ten values')
    if str(Path(sys.executable).resolve()) != capsule['python']['path']:
        raise ValueError('External observer interpreter differs from independent capsule')
    read_pinned(capsule['python']['path'],expected={k:capsule['python'][k] for k in ('bytes','sha256')},
        maximum=MAX_EXECUTABLE_BYTES,sole_link=False)
    for path,pin in capsule['source_pins'].items(): read_pinned(REPO/path,expected=pin)
    config_descriptor=capsule['launch_config'];config_pin={k:config_descriptor[k] for k in ('bytes','sha256')}
    _,config_raw=read_pinned(REPO/CONFIG_PATH,expected=config_pin,maximum=65536,retain=True)
    config=_json(config_raw)
    if config.get('repository_root')!=str(REPO) or config.get('scope')!=capsule['scope']:
        raise ValueError('Pinned launch config differs from independently fixed e root/scope')
    if os.path.lexists(capsule['scope']): raise ValueError('Fresh e scope required before external launcher dispatch')
    finalizer=_source_module(FINALIZER,capsule['source_pins'][FINALIZER])
    supervisor=_source_module(SUPERVISOR,capsule['source_pins'][SUPERVISOR])
    if not set(OUTPUT_NAMES)<=set(finalizer.FINAL_METADATA_NAMES):
        raise ValueError('Every observer output must fit the unchanged final metadata reservation')
    if finalizer.METADATA_RESERVATION_BYTES!=LIMITS['terminal_metadata_bytes'] or finalizer.DIRECTORY_RESERVATION_BYTES!=LIMITS['terminal_directory_growth_bytes']:
        raise ValueError('Observer cannot enlarge terminal storage allowances')
    argv=[capsule['python']['path'],'-I','-S','-B',str(REPO/LAUNCHER),
        '--run','--config-sha256',config_descriptor['sha256']]
    observation,stdout,stderr=observe_child(argv,capsule['environment'],
        deadline_monotonic_ns=anchor+RUN_SECONDS*10**9,supervisor=supervisor)
    scope=Path(capsule['scope'])
    # A preflight refusal never creates a new scope merely to retain a wrapper log.
    scope_fd,_=_directory(str(scope));os.close(scope_fd)
    try:
        stdout_pin=_write_exclusive(scope/STDOUT_NAME,stdout,STDOUT_CAP)
        stderr_pin=_write_exclusive(scope/STDERR_NAME,stderr,STDERR_CAP)
        observation_pin=_write_exclusive(scope/OBSERVATION_NAME,canonical(observation)+b'\n',OBSERVATION_CAP)
        if observation['reason'] is not None or observation['exit_code']!=0 or stderr:
            raise ValueError('External launcher failed, exceeded limits or emitted unexpected stderr')
        replay,cases,expected_external=replay_launcher(scope,stdout,finalizer=finalizer,python=capsule['python']['path'])
        for path,pin in capsule['source_pins'].items(): read_pinned(REPO/path,expected=pin)
        read_pinned(REPO/CONFIG_PATH,expected=config_pin,maximum=65536)
        read_pinned(REPO/CAPSULE_PATH,expected=capsule_pin,maximum=65536)
        storage,elapsed=_measure(scope,finalizer,cases,expected_external,anchor)
        result={'schema':SCHEMA+'-disposition','status':'OBSERVED_LAUNCHER_AND_DESCENDANT_JOIN_PASSED',
            'scope':str(scope),'capsule_pin':capsule_pin,'launch_config_pin':config_pin,
            'launcher_stdout_pin':stdout_pin,'launcher_stderr_pin':stderr_pin,
            'launcher_observation_pin':observation_pin,**replay,
            'launcher_complete_wait4_lifetime_observed':True,
            'external_subreaper_scope_reaped_to_echild':True,
            'launcher_and_replayed_descendant_lifetimes_qualified':True,
            'complete_resource_measurement_join_qualified':True,
            'qualified_finite_domain':'launcher_lifetime_and_replayed_control_descendant_lifetimes',
            'maximum_observed_launcher_or_adopted_process_rss_bytes':observation['maximum_observed_individual_rss_bytes'],
            'observer_rss_bytes_at_final_check':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'admission_start_monotonic_ns':anchor,'measured_elapsed':elapsed,
            'storage_with_remaining_terminal_allowance':storage,
            'observer_metadata_and_postexit_fsync_in_resource_domain':True,
            'retained_measurement_snapshot_precedes_this_disposition_fsync':True,
            'terminal_observer_own_future_termination_covered':False,
            'observer_final_self_checks_not_independent_lifetime_evidence':True,
            'missing_original_storage_accounted':False,'original_identity_continuity_proved':False,
            'kernel_integrity_or_general_sandbox_qualified':False,
            'limitations':['Immutable capsule digest and observer entry bytes require independent caller readback.',
                'The finite qualified domain ends at observed launcher termination plus replayed child joins.',
                'Postexit inventory/fsync checks cannot certify this observer future termination.',
                'Kernel integrity, native/scientific/HTTP-host certificates remain unqualified.'],**AUTHORITY}
        _write_exclusive(scope/DISPOSITION_NAME,canonical(result)+b'\n',DISPOSITION_CAP)
        _measure(scope,finalizer,cases,expected_external,anchor)
        return result
    except BaseException as failure:
        closed={'schema':SCHEMA+'-disposition','status':'CLOSED_FAILED','scope':str(scope),
            'error_type':type(failure).__name__,'error':str(failure)[:2048],
            'observed_elapsed_seconds':(time.monotonic_ns()-anchor)/1e9,
            'launcher_complete_wait4_lifetime_observed':observation['direct_child_reaped'],
            'complete_resource_measurement_join_qualified':False,
            'terminal_observer_own_future_termination_covered':False,**AUTHORITY}
        _write_exclusive(scope/FAILURE_NAME,canonical(closed)+b'\n',FAILURE_CAP)
        raise


def main():
    anchor=time.monotonic_ns()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',required=True)
    parser.add_argument('--capsule-sha256',required=True)
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{64}',args.capsule_sha256):
        raise ValueError('Independent immutable capsule SHA256 required')
    capsule_pin,raw=read_pinned(REPO/CAPSULE_PATH,maximum=65536,retain=True)
    if capsule_pin['sha256']!=args.capsule_sha256:
        raise ValueError('Observer capsule differs from independent immutable readback')
    capsule=_json(raw);validate_capsule(capsule)
    expected=[capsule['python']['path'],'-I','-S','-B',str(REPO/SELF),
        '--run','--capsule-sha256',args.capsule_sha256]
    if list(sys.orig_argv)!=expected:
        raise ValueError('Exact independently approved external observer argv required')
    result=run_observer(capsule,capsule_pin=capsule_pin,admission_start_monotonic_ns=anchor)
    print(canonical(result).decode())


if __name__=='__main__': main()
