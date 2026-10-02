#!/usr/bin/env python3
"""Prospective finite outer observation of one future engineering control.

The fixed launch-config digest must come from independent immutable readback.
This file supplies no activation marker or launch authority. Preflight recomputes
original runtime scope under the exact public ten-value environment, before the
fixture may check its marker or spend an invocation. No retry or path override
exists. Native/scientific/transport gates remain unqualified.

The finite endpoint observes the fixture child through wait4, then rechecks its
retained output, storage (including the persistent ledger), elapsed time and
RSS. It never claims its own future termination or a kernel-integrity guarantee.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
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
SELF = 'scripts/radio_native_v2_compact_control_launch.py'
CONFIG_PATH = 'config/radio_native_v2_compact_control_launch_20261002c.launch.json'
CONFIG_SCHEMA = 'radio-native-v2-compact-control-launch-config-v1'
SCHEMA = 'radio-native-v2-compact-control-launch-v1'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
FIXTURE = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
AUDIT = 'scripts/radio_native_v2_compact_preparation_audit.py'
FREEZER = 'scripts/radio_native_v2_runner_freeze.py'
ENVIRONMENT = 'scripts/radio_native_v2_activation_environment.py'
FINALIZER = 'scripts/radio_native_v2_resource_finalization.py'
# Independently reviewed literals, never supplied by a plan or launch config.
# Root finalizes these only after all owning agents freeze their sources.
BOOTSTRAP_SOURCE_PINS = {'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 121236, 'sha256': 'e108af6dd7cd649d82eb27148401db8075d9db49e2a973509eae43d44978fba1'}, 'scripts/radio_native_v2_compact_preparation_audit.py': {'bytes': 24928, 'sha256': 'd1fe910ca3e0c0b274828fcbae05bd2ead0cfb7b918d005ed3769a4993381014'}, 'scripts/radio_native_v2_runner_freeze.py': {'bytes': 24313, 'sha256': '74ea2fee48eccf6e74a7b3f34517c0c0ccb50ff9abaacd57ab0a187acd24482b'}, 'scripts/radio_native_v2_activation_environment.py': {'bytes': 11741, 'sha256': '059003934a8b51c544f72b488c41c19a6067c0ffb0e65c31afc6eacd35d76bfd'}, 'scripts/radio_native_v2_resource_finalization.py': {'bytes': 73131, 'sha256': '7e7a04e65cae65a309dd88ebc99c42a33cb40c8f8f4baada4f3915fa898ebc4c'}, 'scripts/radio_native_v2_worker_admission.py': {'bytes': 75309, 'sha256': '475c2884f87f10986e15df57bbb9b5ee7c0652cf37604b2f7f03d9fd277142ae'}, 'scripts/radio_native_v2_runtime_custody.py': {'bytes': 22519, 'sha256': 'd0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'}, 'scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'}}
STDOUT_NAME = 'compact-control-launch-stdout.log'
STDERR_NAME = 'compact-control-launch-stderr.log'
OBSERVATION_NAME = 'compact-control-launch-observation.json'
PREFLIGHT_NAME = 'compact-control-launch-preflight.json'
DISPOSITION_NAME = 'compact-control-launch-disposition.json'
FAILURE_NAME = 'compact-control-launch-closed-failure.json'
INPUT_NAMES = frozenset(('plan', 'complete_freeze', 'preread', 'activation_readback'))
MAX_JSON_BYTES = 16*1024**2
MAX_SOURCE_BYTES = 2*1024**2
STDOUT_CAP = 65536
STDERR_CAP = 16384
OBSERVATION_CAP = 16384
PREFLIGHT_CAP = 16384
DISPOSITION_CAP = 32768
RUN_SECONDS = 4800
RSS_BYTES = 512*1024**2
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}
_launch_entered = False


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _sha(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Exact independently retained lowercase SHA256 required')
    return value


def _absolute(value):
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or len(value.encode()) > 4096 or len(value.split('/')) > 64
            or any(part in ('', '.', '..') for part in value[1:].split('/'))):
        raise ValueError('Bounded canonical absolute launch path required')
    return value


def _relative(value):
    if (type(value) is not str or not value or len(value.encode()) > 4096
            or value.startswith('/') or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Bounded canonical repository-relative launch input required')
    return value


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in _absolute(path)[1:].split('/'):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd); raise


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
        info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_pinned(path, *, expected=None, maximum=None, retain=False, sole_link=True):
    value = _absolute(path); parent, name = value.rsplit('/', 1)
    directory = _directory(parent); fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or (sole_link and before.st_nlink != 1)
                or (maximum is not None and before.st_size > maximum)):
            raise ValueError('Bounded stable regular launch material required')
        digest = hashlib.sha256(); count = 0; chunks = []
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            count += len(raw)
            if maximum is not None and count > maximum:
                raise ValueError('Launch material exceeded bounded byte count')
            digest.update(raw)
            if retain: chunks.append(raw)
        after = os.fstat(fd); named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        reopened = _directory(parent)
        try:
            if _identity(os.fstat(directory))[:2] != _identity(os.fstat(reopened))[:2]:
                raise ValueError('Launch material ancestor replaced')
        finally: os.close(reopened)
        if _identity(before) != _identity(after) or _identity(after) != _identity(named) or count != after.st_size:
            raise ValueError('Launch material changed during descriptor read')
        pin = {'bytes': count, 'sha256': digest.hexdigest()}
        if expected is not None and pin != expected:
            raise ValueError('Launch material differs from independently retained pin')
        return pin, b''.join(chunks) if retain else None
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _json(raw, *, require_canonical=True):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('Duplicate launch JSON property refused')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite launch JSON refused')))
    if type(value) is not dict:
        raise ValueError('Exact launch JSON object required')
    if require_canonical and raw != canonical(value)+b'\n':
        raise ValueError('Exact canonical launch JSON plus newline required')
    return value


def load_launch_config(expected_sha256):
    pin, raw = read_pinned(REPO/CONFIG_PATH, maximum=65536, retain=True)
    if pin['sha256'] != _sha(expected_sha256):
        raise ValueError('Fixed launch config differs from independent immutable readback digest')
    config = _json(raw)
    validate_launch_config(config)
    return config


def validate_launch_config(config):
    required = {'schema', 'namespace', 'mode', 'repository_root', 'scope', 'inputs'}
    if type(config) is not dict or set(config) != required:
        raise ValueError('Exact fixed launch config structure required')
    if (config['schema'] != CONFIG_SCHEMA or config['namespace'] != NAMESPACE
            or config['mode'] != 'PROSPECTIVE_NOT_EXECUTED'
            or _absolute(config['repository_root']) != str(REPO)):
        raise ValueError('Fixed prospective launch identity/root required')
    scope = _absolute(config['scope'])
    if not scope.startswith(str(REPO)+'/'):
        raise ValueError('Fresh control scope must remain under the pinned repository root')
    if type(config['inputs']) is not dict or set(config['inputs']) != INPUT_NAMES:
        raise ValueError('Exact four fixed launch input descriptors required')
    paths = set()
    for name, value in config['inputs'].items():
        if (type(value) is not dict or set(value) != {'path', 'bytes', 'sha256'}
                or type(value['bytes']) is not int or not 0 < value['bytes'] <= MAX_JSON_BYTES):
            raise ValueError('Exact bounded launch input pin required: '+name)
        path = _relative(value['path']); _sha(value['sha256'])
        if path in paths: raise ValueError('Distinct launch input paths required')
        paths.add(path)
    return True


def _source_module(name, relative):
    wanted = BOOTSTRAP_SOURCE_PINS.get(relative)
    if type(wanted) is not dict or set(wanted) != {'bytes', 'sha256'}:
        raise RuntimeError('BLOCKED_PREPARATION_REVIEW: reviewed launcher bootstrap pin absent: '+relative)
    _, raw = read_pinned(REPO/relative, expected=wanted, maximum=MAX_SOURCE_BYTES, retain=True)
    module = types.ModuleType(name); module.__file__ = str(REPO/relative)
    sys.modules[name] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


class _PinnedSourceLoader:
    def __init__(self, path, digest, *, package=False, bootstrap=None):
        self.path = path; self.digest = digest; self.package = package; self.bootstrap = bootstrap

    def create_module(self, spec): return None

    def exec_module(self, module):
        pin, raw = read_pinned(self.path, maximum=MAX_SOURCE_BYTES, retain=True)
        if pin['sha256'] != self.digest or (self.bootstrap is not None and pin != self.bootstrap):
            raise ValueError('Pinned preflight import source differs')
        module.__file__ = self.path
        if self.package: module.__path__ = [str(Path(self.path).parent)]
        exec(compile(raw, self.path, 'exec'), module.__dict__)


class _PinnedExtensionLoader:
    def __init__(self, name, path, digest):
        self.path = path; self.digest = digest
        self.loader = importlib.machinery.ExtensionFileLoader(name, path)

    def _check(self):
        if read_pinned(self.path, sole_link=False)[0]['sha256'] != self.digest:
            raise ValueError('Pinned preflight NumPy extension differs')

    def create_module(self, spec):
        self._check(); return self.loader.create_module(spec)

    def exec_module(self, module):
        self._check(); self.loader.exec_module(module); self._check()


class _PinnedPreflightFinder:
    def __init__(self, freeze, numpy_site):
        self.freeze = freeze; self.numpy_site = numpy_site

    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'numpy' or fullname.startswith('numpy.'):
            base = self.numpy_site+'/'+fullname.replace('.', '/')
            hashes = self.freeze['runtime_sha256s']
            candidates = [(base+'/__init__.py', True), (base+'.py', False)]
            candidates += [(base+suffix, False) for suffix in importlib.machinery.EXTENSION_SUFFIXES]
            actual = [(name, package) for name, package in candidates if name in hashes]
            if len(actual) != 1: raise ImportError('Unique pinned NumPy import path required: '+fullname)
            selected, package = actual[0]
            if selected.endswith('.py'):
                loader = _PinnedSourceLoader(selected, hashes[selected], package=package)
            else: loader = _PinnedExtensionLoader(fullname, selected, hashes[selected])
        elif fullname == 'seti_repeater' or fullname.startswith('seti_repeater.'):
            base = 'src/'+fullname.replace('.', '/')
            candidates = [(base+'/__init__.py', True), (base+'.py', False)]
            hashes = self.freeze['code_sha256s']
            actual = [(name, package) for name, package in candidates if name in hashes]
            if len(actual) != 1: raise ImportError('Unique pinned repository import path required: '+fullname)
            selected, package = actual[0]
            loader = _PinnedSourceLoader(str(REPO/selected), hashes[selected], package=package)
        elif fullname.startswith('radio_native_v2_'):
            selected = 'scripts/'+fullname+'.py'; package = False
            digest = self.freeze['code_sha256s'].get(selected)
            if digest is None: raise ImportError('Pinned preflight script import required: '+fullname)
            bootstrap = BOOTSTRAP_SOURCE_PINS.get(selected)
            if selected in BOOTSTRAP_SOURCE_PINS and type(bootstrap) is not dict:
                raise ImportError('Independent preflight bootstrap pin absent: '+fullname)
            loader = _PinnedSourceLoader(str(REPO/selected), digest, bootstrap=bootstrap)
        else: return None
        return importlib.util.spec_from_file_location(fullname, loader.path, loader=loader,
            submodule_search_locations=[str(Path(loader.path).parent)] if package else None)


def preflight(plan, freeze):
    """Actual independent local audit under the same environment as control."""
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError('Actual -I -S -B launcher required')
    # The launcher is executed from the authenticated original repository,
    # whereas material workers run relocated copies. Bind the journal before
    # importing any activation, fixture or storage adapter.
    if (type(plan) is not dict
            or plan.get('invocation_repository_root') != str(REPO)
            or plan.get('invocation_ledger_root') != str(REPO/'.radio-native-v2-invocation-ledger-20261002c')):
        raise ValueError('Prospective c journal must bind the independently selected original repository root')
    environment = _source_module('radio_native_v2_activation_environment', ENVIRONMENT)
    expected = environment.expected_environment(plan, freeze)
    environment.validate(plan, freeze, dict(os.environ))
    python = plan['runtime_executables']['python']
    if str(Path(sys.executable).resolve()) != python['path']:
        raise ValueError('Actual launcher interpreter differs from pinned runtime')
    if read_pinned(python['path'], sole_link=False)[0] != {'bytes':python['bytes'], 'sha256':python['sha256']}:
        raise ValueError('Pinned actual launcher interpreter bytes differ')
    for relative, wanted in BOOTSTRAP_SOURCE_PINS.items():
        if type(wanted) is not dict or plan['code_files'].get(relative) != wanted:
            raise ValueError('Independent launcher bootstrap differs from plan: '+relative)
        if freeze['code_sha256s'].get(relative) != wanted['sha256']:
            raise ValueError('Original freeze omits launcher bootstrap: '+relative)
        read_pinned(REPO/relative, expected=wanted, maximum=MAX_SOURCE_BYTES)
    for path, digest in freeze['runtime_sha256s'].items():
        if read_pinned(path, sole_link=False)[0]['sha256'] != _sha(digest):
            raise ValueError('Pinned runtime changed before NumPy/preflight import')
    roots = [path[:-len('/numpy/__init__.py')] for path in freeze['runtime_sha256s']
        if path.endswith('/numpy/__init__.py')]
    if len(roots) != 1: raise ValueError('Unique runtime-derived NumPy site path required')
    numpy_site = _absolute(roots[0]); directory = _directory(numpy_site); os.close(directory)
    finder = _PinnedPreflightFinder(freeze, numpy_site)
    controlled = [name for name in sys.modules if name == 'numpy' or name.startswith('numpy.')
        or name == 'seti_repeater' or name.startswith('seti_repeater.')
        or name.startswith('radio_native_v2_')]
    if set(controlled) != {'radio_native_v2_activation_environment'}:
        raise ValueError('Preloaded uncontrolled repository or NumPy module refused')
    sys.meta_path.insert(0, finder)
    sys.path.append(numpy_site)
    try:
        import radio_native_v2_runner_freeze as freezer
        import radio_native_v2_compact_preparation_audit as audit
        import radio_native_v2_compact_eight_case_resource_fixture as fixture
        audited = audit.audit(plan, freeze, repo=REPO)
        if plan != fixture.build_plan(REPO):
            raise ValueError('Current exact blocked plan differs before marker or spending')
        environment.validate(plan, freeze, dict(os.environ))
        return {'schema': SCHEMA+'-preflight', 'status':'LOCAL_PREFLIGHT_RECOMPUTED',
            'environment':expected, 'isolated_no_site_no_bytecode':True,
            'independent_original_scope_recomputed':True,
            'repository_code_files':len(freeze['repository_code_inventory']),
            'runtime_files':len(freeze['runtime_file_inventory']),
            'independent_supplement_inventory_recomputed':audited['exact_supplement_inventory_and_bytes_verified'],
            'runtime_and_supplement_union_sha256':audited['runtime_and_supplement_union_sha256'],
            'numpy_site_path_derived_from_pinned_runtime':numpy_site,
            'repository_numpy_source_imports_bypass_cached_bytecode':True,
            'bootstrap_source_pins':BOOTSTRAP_SOURCE_PINS,
            'public_marker_or_spend_called_by_preflight':False,
            'complete_runtime_closure_qualified':False, **AUTHORITY}
    finally:
        sys.meta_path.remove(finder)
        sys.path.remove(numpy_site)


def observe_child(argv, environment, *, deadline_monotonic_ns,
        stdout_cap=STDOUT_CAP, stderr_cap=STDERR_CAP):
    """One directly waited child, bounded pipes, no retry; tiny-testable."""
    if (type(argv) is not list or not argv or any(type(item) is not str for item in argv)
            or type(environment) is not dict
            or any(type(key) is not str or type(value) is not str for key,value in environment.items())
            or type(deadline_monotonic_ns) is not int or deadline_monotonic_ns <= time.monotonic_ns()
            or type(stdout_cap) is not int or not 0 < stdout_cap <= STDOUT_CAP
            or type(stderr_cap) is not int or not 0 < stderr_cap <= STDERR_CAP):
        raise ValueError('Exact bounded child observation contract required')
    start = time.monotonic_ns(); child = subprocess.Popen(argv, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=environment, start_new_session=True)
    selector = None; streams = {child.stdout:'stdout',child.stderr:'stderr'}
    output = {'stdout':bytearray(), 'stderr':bytearray()}; counts = {'stdout':0, 'stderr':0}
    caps = {'stdout':stdout_cap, 'stderr':stderr_cap}; reaped = False
    status = None; usage = None; reason = None
    try:
        selector = selectors.DefaultSelector()
        for pipe in streams:
            os.set_blocking(pipe.fileno(), False); selector.register(pipe, selectors.EVENT_READ)
        while True:
            # Retain the root PID/PGID while descendants can hold pipes, so
            # bounded cancellation cannot target a recycled process group.
            if not reaped and not selector.get_map():
                waited, child_status, child_usage = os.wait4(child.pid, os.WNOHANG)
                if waited:
                    reaped = True; status = child_status; usage = child_usage
                    child.returncode = os.waitstatus_to_exitcode(status)
            now = time.monotonic_ns()
            if now >= deadline_monotonic_ns:
                reason = 'original observation deadline exceeded'; break
            if reaped and not selector.get_map(): break
            for key, _ in selector.select(min(0.01,(deadline_monotonic_ns-now)/1e9)):
                pipe = key.fileobj; label = streams[pipe]
                raw = os.read(pipe.fileno(), 65536)
                if not raw:
                    selector.unregister(pipe); pipe.close(); continue
                counts[label] += len(raw)
                remaining = caps[label]-len(output[label])
                if remaining > 0: output[label].extend(raw[:remaining])
                if counts[label] > caps[label]:
                    reason = label+' exceeded fixed retained output cap'; break
            if reason is not None: break
    except BaseException as failure:
        reason = 'observer setup/read failed: '+type(failure).__name__
    finally:
        if reason is not None:
            # The child started its own new session. Its process-group identity
            # remains reserved while members exist; no unrelated group is used.
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if not reaped:
            cleanup_deadline = time.monotonic_ns()+10**9
            while time.monotonic_ns() < cleanup_deadline:
                waited, terminal_status, terminal_usage = os.wait4(child.pid, os.WNOHANG)
                if waited:
                    status = terminal_status; usage = terminal_usage; reaped = waited == child.pid
                    child.returncode = os.waitstatus_to_exitcode(status); break
                time.sleep(0.005)
            if not reaped: reason = reason or 'bounded cleanup ended without terminal wait4'
        for pipe in streams:
            if not pipe.closed: pipe.close()
        if selector is not None: selector.close()
    end = time.monotonic_ns()
    kernel_peak = int(usage.ru_maxrss)*1024 if usage is not None else 0
    return {'schema': SCHEMA+'-child-observation', 'observed_argv':argv,
        'child_environment':environment, 'namespace_child_pid':child.pid,
        'monotonic_start_ns':start, 'monotonic_end_ns':end,
        'elapsed_seconds':(end-start)/1e9, 'exit_code':child.returncode,
        'reason':reason, 'direct_child_reaped':reaped,
        'includes_entire_direct_child_lifetime':reaped,
        'complete_pipe_output':reason is None,
        'observed_output_bytes':counts, 'retained_output_bytes':{key:len(value) for key,value in output.items()},
        'procfs_sampled_peak_rss_bytes':None, 'procfs_sampling_qualified':False,
        'wait4_ru_maxrss_bytes':kernel_peak,
        'maximum_observed_direct_child_rss_bytes':kernel_peak,
        'observer_source':'independent_parent_kernel_wait4',
        'descendant_scope_qualified_by_this_observer':False,
        'terminal_observer_own_future_termination_covered':False}, bytes(output['stdout']), bytes(output['stderr'])


def _write_exclusive(path, raw, maximum):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError('Bounded observer evidence bytes required')
    parent = _directory(str(Path(path).parent))
    fd = None
    try:
        fd = os.open(Path(path).name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400, dir_fd=parent)
    except BaseException:
        os.close(parent); raise
    try:
        position = 0
        while position < len(raw):
            written = os.write(fd, raw[position:])
            if written <= 0: raise ValueError('Observer evidence write incomplete')
            position += written
        os.fsync(fd)
    finally:
        os.close(fd)
        try: os.fsync(parent)
        finally: os.close(parent)
    return read_pinned(path, expected={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})[0]


def _retain_child_observation(scope, prepared, observation, stdout, stderr):
    _write_exclusive(scope/PREFLIGHT_NAME, canonical(prepared)+b'\n', PREFLIGHT_CAP)
    _write_exclusive(scope/STDOUT_NAME, stdout, STDOUT_CAP)
    _write_exclusive(scope/STDERR_NAME, stderr, STDERR_CAP)
    _write_exclusive(scope/OBSERVATION_NAME, canonical(observation)+b'\n', OBSERVATION_CAP)


def _fixture_argv(config, plan, anchor):
    inputs = config['inputs']
    return [plan['runtime_executables']['python']['path'],'-I','-S','-B',str(REPO/FIXTURE),
        '--run','--scope',config['scope'],'--plan',str(REPO/inputs['plan']['path']),
        '--complete-freeze',str(REPO/inputs['complete_freeze']['path']),
        '--preread',str(REPO/inputs['preread']['path']),
        '--activation-readback',str(REPO/inputs['activation_readback']['path']),
        '--admission-start-monotonic-ns',str(anchor)]


def launch_control(config, *, admission_start_monotonic_ns=None):
    """Internal fixed-config entry; CLI authenticates its exact bytes first."""
    global _launch_entered
    if _launch_entered: raise RuntimeError('One launcher entry only; no retry or resume')
    _launch_entered = True
    now = time.monotonic_ns()
    anchor = now if admission_start_monotonic_ns is None else admission_start_monotonic_ns
    if type(anchor) is not int or not 0 < anchor <= now:
        raise ValueError('Actual invocation-start monotonic anchor required')
    validate_launch_config(config)
    scope = Path(config['scope'])
    if scope.exists(): raise ValueError('Fresh exclusive control scope required')
    root_fd = _directory(str(scope.parent)); os.close(root_fd)
    try:
        return _launch_control_once(config, anchor)
    except BaseException as failure:
        # Never invent a scope for a preflight/marker refusal. An existing
        # scope created by this child can retain a closed endpoint. If a later
        # self-check fails after a child-join record, preserve that prior
        # observation and record failure separately; no record is overwritten.
        try:
            info = scope.lstat()
        except FileNotFoundError:
            raise failure
        if not stat.S_ISDIR(info.st_mode): raise
        closed = {'schema':SCHEMA+'-disposition', 'status':'CLOSED_FAILED',
            'scope':str(scope), 'error_type':type(failure).__name__,
            'error':str(failure)[:4096], 'admission_start_monotonic_ns':anchor,
            'observed_elapsed_seconds':(time.monotonic_ns()-anchor)/1e9,
            'complete_resource_measurement_join_qualified':False,
            'terminal_observer_own_future_termination_covered':False,
            'automatic_retry':False, **AUTHORITY}
        _write_exclusive(scope/FAILURE_NAME, canonical(closed)+b'\n', 8192)
        raise


def _launch_control_once(config, anchor):
    scope = Path(config['scope'])
    inputs = {}
    for name, descriptor in config['inputs'].items():
        _, raw = read_pinned(REPO/descriptor['path'], expected={key:descriptor[key] for key in ('bytes','sha256')},
            maximum=MAX_JSON_BYTES, retain=True)
        inputs[name] = _json(raw, require_canonical=False)
    plan = inputs['plan']; freeze = inputs['complete_freeze']
    prepared = preflight(plan, freeze)
    prepared['admission_start_monotonic_ns'] = anchor
    if time.monotonic_ns()-anchor >= RUN_SECONDS*10**9:
        raise ValueError('Original whole deadline exceeded during preflight')
    argv = _fixture_argv(config, plan, anchor)
    observation, stdout, stderr = observe_child(argv, prepared['environment'],
        deadline_monotonic_ns=anchor+RUN_SECONDS*10**9)
    if not scope.is_dir():
        raise RuntimeError('Control refused before creating scope; no observer scope is invented')
    if observation['reason'] is not None or observation['exit_code'] != 0 or stderr:
        _retain_child_observation(scope, prepared, observation, stdout, stderr)
        raise RuntimeError('Observed control child failed or emitted unexpected stderr')
    try:
        finalizer = _source_module('radio_native_v2_resource_finalization', FINALIZER)
        summary = _json(stdout)
        input_value, input_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_INPUT_NAME)
        report_value, report_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_NAME)
        writer_observation, writer_pin = finalizer.read_pinned_json(scope/finalizer.FINAL_WRITER_OBSERVATION_NAME)
        writer_argv = [plan['runtime_executables']['python']['path'],'-I','-S','-B',str(scope/'frozen-code'/FINALIZER),
            '--persist-final-report','--scope',str(scope),
            '--input-bytes',str(input_pin['bytes']),'--input-sha256',input_pin['sha256']]
        independently_joined = finalizer.join_final_report_lifetime(scope,
            expected_input_pin=input_pin, expected_report_pin=report_pin,
            expected_writer_observation_pin=writer_pin, expected_writer_argv=writer_argv)
        if canonical(summary) != canonical(independently_joined):
            raise ValueError('Retained fixture stdout differs from independently replayed report join')
    except BaseException:
        _retain_child_observation(scope, prepared, observation, stdout, stderr)
        raise
    # Replay precedes terminal metadata writes; charge their changed inventory
    # separately. The retained old summary is never silently rewritten.
    _retain_child_observation(scope, prepared, observation, stdout, stderr)
    worker, worker_pin = finalizer.read_pinned_json(scope/'worker-result.json')
    cases, _ = finalizer._worker_cases(worker)
    external = finalizer.observe_authenticated_ledger_storage(scope)
    finalizer._match_retained_ledger(external, summary['independent_driver_measurement_disposition']
        ['storage']['external_ledger_inventory_sha256'])
    storage = finalizer.allocate_storage(finalizer.storage_inventory(scope), external_inventory=external)
    elapsed = finalizer.allocate_elapsed(cases,(time.monotonic_ns()-anchor)/1e9)
    peak = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,
        observation['maximum_observed_direct_child_rss_bytes'])
    if peak > RSS_BYTES: raise ValueError('Original512MiB preflight/fixture/observer maximum RSS exceeded')
    result = {'schema':SCHEMA+'-disposition', 'status':'OBSERVED_FIXTURE_CHILD_JOIN_PASSED',
        'scope':str(scope), 'fixture_stdout_pin':read_pinned(scope/STDOUT_NAME)[0],
        'fixture_child_observation_pin':read_pinned(scope/OBSERVATION_NAME)[0],
        'preflight_pin':read_pinned(scope/PREFLIGHT_NAME)[0], 'worker_result_pin':worker_pin,
        'fixture_child_exit_code':observation['exit_code'],
        'fixture_child_complete_wait4_lifetime_observed':True,
        'independently_observed_fixture_child_join_qualified':summary['complete_resource_measurement_join_qualified'],
        'preflight_and_fixture_in_original_monotonic_budget':True,
        'admission_start_monotonic_ns':anchor, 'measured_elapsed':elapsed,
        'maximum_preflight_fixture_observer_rss_bytes':peak,
        'storage_after_fixture_termination_with_remaining_terminal_allowance':storage,
        'persistent_ledger_reobserved_and_charged_after_fixture_termination':True,
        'historical_scope_and_b_and_c_journals_reobserved_after_fixture_termination':True,
        'complete_resource_measurement_join_qualified':False,
        'terminal_observer_own_future_termination_covered':False,
        'terminal_observer_final_self_checks_not_independent_lifetime_evidence':True,
        'limitations':['Finite observation closes the fixture child, not the terminal observer future.',
            'Config digest and fixed launcher bytes require independent immutable readback.',
            'Pinned native-extension imports retain a mutation-after-check filesystem limitation.',
            'Kernel/native/scientific/HTTP-host joins remain unqualified.'], **AUTHORITY}
    _write_exclusive(scope/DISPOSITION_NAME, canonical(result)+b'\n', DISPOSITION_CAP)
    # Final self-checks include retention/fsync of the disposition. They cannot
    # certify this terminal observer's own future termination; fields stay false.
    current_external = finalizer.observe_authenticated_ledger_storage(scope)
    finalizer._match_retained_ledger(current_external, storage['external_ledger_inventory_sha256'])
    finalizer.allocate_storage(finalizer.storage_inventory(scope), external_inventory=current_external)
    finalizer.allocate_elapsed(cases,(time.monotonic_ns()-anchor)/1e9)
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > RSS_BYTES:
        raise ValueError('Original512MiB terminal observer RSS exceeded after evidence fsync')
    return result


def main():
    anchor = time.monotonic_ns()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', required=True)
    parser.add_argument('--config-sha256', required=True)
    args = parser.parse_args()
    expected_argv = [str(Path(sys.executable).resolve()),'-I','-S','-B',str(REPO/SELF),
        '--run','--config-sha256',args.config_sha256]
    if list(sys.orig_argv) != expected_argv:
        raise ValueError('Exact actual fixed launcher argv required; no options or path overrides')
    result = launch_control(load_launch_config(args.config_sha256),
        admission_start_monotonic_ns=anchor)
    print(canonical(result).decode())


if __name__ == '__main__': main()
