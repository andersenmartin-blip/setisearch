"""Fresh engineering-only one-shot dispatch through a maintained receiver child.

This successor fixes v1's destination and child-clock admission gaps. It never
constructs a VerifiedClosure/VerifiedAdmission and never grants science access.
Actual public-domain execution is refused, pending authentic service evidence.
Claims persist in a separately pinned directory and are keyed by identity.
There is no replay after success, failure, ambiguity or parent crash.
"""
from dataclasses import dataclass
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time
import types

SCHEMA = 'radio-engineering-receiver-dispatch-v2'
MODULES = ('scientific_runtime', 'scientific_admission', 'scientific_store',
           'receiver_telescope_adapter', 'failure_output_retention')
LABELS = tuple(f'epoch{i}_{kind}' for i in (1, 2, 3) for kind in ('on', 'off'))
MAX_METADATA = 4 * 1024**2
MAX_EXECUTABLE = 64 * 1024**2
STOP_MS = 1791590400000  # 2026-10-10 00:00:00 UTC; original stop law.
ROOT = str(Path(__file__).resolve().parent.parent)


class Refused(ValueError):
    pass


def need(value, reason):
    if not value:
        raise Refused(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def unique(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate JSON member')
        value[key] = item
    return value


def parse(raw, expected_pin, cap=MAX_METADATA):
    need(type(raw) is bytes and type(expected_pin) is dict and
         set(expected_pin) == {'bytes', 'sha256'} and type(expected_pin['bytes']) is int
         and 0 < len(raw) <= cap and pin(raw) == expected_pin,
         'raw bounded external pin differs')
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(Refused('nonfinite JSON')))
        need(canonical(value) == raw, 'canonical JSON with terminal LF required')
        return value
    except (RecursionError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise Refused('invalid pinned JSON: '+str(error)) from error


def absolute(value):
    need(type(value) is str and len(value) <= 4096 and value.startswith('/')
         and value != '/' and value == os.path.normpath(value) and '\\' not in value
         and all(ord(c) >= 32 for c in value)
         and all(part not in ('', '.', '..') for part in value.split('/')[1:]),
         'canonical absolute path required')
    return value


def directory(path):
    """Walk every ancestor using held no-follow directory descriptors."""
    path = absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for part in path.split('/')[1:]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd); fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def file_pin(path):
    path = absolute(str(path))
    raw = Path(path).read_bytes()  # fixture/scope producer only, never authority.
    return {'path': path, 'mode': stat.S_IMODE(os.stat(path).st_mode), **pin(raw)}


def read_checked(expected, cap=MAX_METADATA):
    need(type(expected) is dict and set(expected) == {'path', 'mode', 'bytes', 'sha256'}
         and type(expected['mode']) is int and expected['mode'] in (0o400, 0o600, 0o644, 0o755)
         and type(expected['bytes']) is int and 0 < expected['bytes'] <= cap
         and type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}', expected['sha256']),
         'exact bounded ordinary file pin required')
    path = absolute(expected['path'])
    parent = directory(os.path.dirname(path))
    fd = None
    try:
        fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink >= 1
             and stat.S_IMODE(before.st_mode) == expected['mode'] and before.st_size == expected['bytes'],
             'ordinary file identity, mode or size differs')
        raw = bytearray()
        while len(raw) < before.st_size:
            block = os.read(fd, min(65536, before.st_size-len(raw)))
            need(block, 'pinned file truncated during readback')
            raw.extend(block)
        after = os.fstat(fd)
        visible = os.stat(os.path.basename(path), dir_fd=parent, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        need(identity(before) == identity(after) == identity(visible)
             and hashlib.sha256(raw).hexdigest() == expected['sha256'],
             'pinned file bytes or pathname changed')
        return bytes(raw)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def pack(value):
    if type(value) is bytes:
        return {'$bytes': base64.b64encode(value).decode('ascii')}
    if type(value) is tuple:
        return [pack(v) for v in value]
    if type(value) is list:
        return [pack(v) for v in value]
    if type(value) is dict:
        need('$bytes' not in value, 'reserved packet key')
        return {k: pack(v) for k, v in value.items()}
    return value


def unpack(value, depth=0):
    need(depth < 64, 'packet nesting bound exceeded')
    if type(value) is dict and '$bytes' in value:
        need(set(value) == {'$bytes'} and type(value['$bytes']) is str,
             'exact byte encoding required')
        try:
            raw = base64.b64decode(value['$bytes'], validate=True)
        except (ValueError, UnicodeError) as error:
            raise Refused('invalid packet base64') from error
        need(base64.b64encode(raw).decode('ascii') == value['$bytes'], 'canonical base64 required')
        return raw
    if type(value) is dict:
        return {k: unpack(v, depth+1) for k, v in value.items()}
    if type(value) is list:
        return [unpack(v, depth+1) for v in value]
    return value


def load_modules(spec):
    """Execute the exact independently pinned source bytes, in fixed order."""
    need(type(spec['modules']) is dict and set(spec['modules']) == set(MODULES),
         'complete fixed maintained module inventory required')
    result = {}
    for name in MODULES:
        location = spec['modules'][name]
        raw = read_checked(location)
        module = types.ModuleType(name)
        module.__file__ = location['path']
        sys.modules[name] = module
        exec(compile(raw, location['path'], 'exec'), module.__dict__)
        result[name] = module
    return result


def admitted_fixture(spec, modules):
    raw = read_checked(spec['packet'])
    packet = unpack(parse(raw, {key: spec['packet'][key] for key in ('bytes', 'sha256')}))
    need(type(packet) is dict and set(packet) == {'metadata', 'rows', 'row_pins'},
         'exact synthetic fixture packet required')
    metadata, rows, row_pins = packet['metadata'], packet['rows'], packet['row_pins']
    need(type(metadata) is dict and type(rows) is dict and set(rows) == set(LABELS)
         and type(row_pins) is dict and set(row_pins) == set(LABELS),
         'complete six-scan fixture required')
    adapter = modules['receiver_telescope_adapter']
    closure, admission, context, requests, receipts = adapter._gated_metadata(**metadata)
    need(closure.record()['evidence_domain'] == 'synthetic-test-fixture'
         and admission.record()['domain'] == 'synthetic-test-fixture'
         and admission.record()['status'] == 'PENDING'
         and admission.record()['scientific_execution_authorized'] is False,
         'synthetic fixture cannot grant actual admission')
    for label in LABELS:
        need(type(rows[label]) is list and len(rows[label]) == 16
             and type(row_pins[label]) is list and len(row_pins[label]) == 16,
             'exact tiny row inventory required')
        for row, expected in zip(rows[label], row_pins[label], strict=True):
            need(type(row) is bytes and len(row) == 16 and pin(row) == expected,
                 'fixture row differs from independent pin or tiny geometry')
    return packet, admission, requests


def validate_scope(spec, expected_claim_root):
    need(type(spec) is dict and set(spec) == {
        'schema', 'domain', 'dispatch_identity', 'claim_root', 'python', 'runner', 'child',
        'modules', 'packet', 'environment', 'timeout_seconds', 'stdout_cap_bytes',
        'stderr_cap_bytes', 'fault', 'scientific_execution_authorized'},
        'exact receiver dispatch scope required')
    need(spec['schema'] == SCHEMA and spec['domain'] == 'synthetic-test-fixture'
         and spec['scientific_execution_authorized'] is False,
         'actual public execution remains blocked')
    need(type(spec['dispatch_identity']) is str and re.fullmatch('[0-9a-f]{64}', spec['dispatch_identity']),
         'distinct SHA256 dispatch identity required')
    need(spec['claim_root'] == expected_claim_root and type(expected_claim_root) is dict
         and set(expected_claim_root) == {'path', 'device', 'inode'}
         and all(type(expected_claim_root[k]) is int for k in ('device', 'inode')),
         'independent claim-root identity differs')
    root = absolute(expected_claim_root['path'])
    need(root != ROOT and not root.startswith(ROOT+'/') and not ROOT.startswith(root+'/'),
         'claim root must be disjoint from implementation repository')
    need(type(spec['timeout_seconds']) in (int, float) and not isinstance(spec['timeout_seconds'], bool)
         and math.isfinite(spec['timeout_seconds']) and 0 < spec['timeout_seconds'] <= 30,
         'protected engineering timeout exceeded')
    need(all(type(spec[k]) is int and 0 <= spec[k] <= 65536
             for k in ('stdout_cap_bytes', 'stderr_cap_bytes')),
         'protected engineering stream caps exceeded')
    need(spec['environment'] == {'LC_ALL': 'C', 'PYTHONHASHSEED': '0'}
         and type(spec['environment']) is dict, 'exact non-inherited child environment required')
    need(spec['fault'] in ('none', 'raise-first', 'hang-first'), 'explicit synthetic fault only')
    return spec


def reserve(spec, expected_claim_root, raw_pin):
    parent = directory(expected_claim_root['path'])
    try:
        s = os.fstat(parent)
        need((s.st_dev, s.st_ino) == (expected_claim_root['device'], expected_claim_root['inode']),
             'claim root replaced')
        name = spec['dispatch_identity']
        os.mkdir(name, 0o700, dir_fd=parent)  # Fail closed: identity spent in this ledger.
        os.fsync(parent)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        try:
            raw = canonical({'schema': 'radio-local-engineering-irrevocable-claim-v2',
                'dispatch_identity': name, 'scope_pin': raw_pin,
                'scientific_execution_authorized': False, 'retry_or_resume_allowed': False})
            exclusive_write(child, 'claim.json', raw)
        finally:
            os.close(child)
        return expected_claim_root['path']+'/'+name
    finally:
        os.close(parent)


def exclusive_write(directory_fd, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            need(count > 0, 'terminal write failed')
            offset += count
        os.fsync(fd); os.fchmod(fd, 0o400)
        os.fsync(directory_fd)
    finally:
        os.close(fd)


def verify_child(raw, spec, packet, admission):
    value = parse(raw, pin(raw), cap=65536)
    need(type(value) is dict and set(value) == {
         'schema', 'dispatch_identity', 'packet_sha256', 'receiver_adapter_sha256',
         'receiver_result', 'loader_calls', 'normalized_row_bytes', 'isolated_flags',
         'scientific_execution_authorized', 'telescope_values_opened'},
         'exact child result envelope required')
    need(value['schema'] == 'radio-synthetic-receiver-child-result-v2'
         and value['dispatch_identity'] == spec['dispatch_identity']
         and value['packet_sha256'] == spec['packet']['sha256']
         and value['receiver_adapter_sha256'] == spec['modules']['receiver_telescope_adapter']['sha256']
         and value['isolated_flags'] == {'isolated': 1, 'no_site': 1, 'dont_write_bytecode': 1}
         and value['loader_calls'] == list(LABELS) and type(value['normalized_row_bytes']) is int
         and value['normalized_row_bytes'] == 1536
         and value['scientific_execution_authorized'] is False and value['telescope_values_opened'] is False,
         'child identity, geometry or blocked authority differs')
    receiver = value['receiver_result']
    need(type(receiver) is dict and receiver.get('source_domain') == 'synthetic-interface-fixture-only'
         and receiver.get('status') == 'SYNTHETIC_INTERFACE_QUALIFIED'
         and receiver.get('fixture_row_pins') == packet['row_pins']
         and receiver.get('scientific_execution_authorized') is False
         and receiver.get('spectral_access_authorized') is False
         and receiver.get('telescope_values_opened') is False,
         'actual maintained receiver result required')
    clock = receiver.get('per_load_live_clock')
    authority = admission.record()
    need(type(clock) is dict and set(clock) == {
        'session_started_epoch_milliseconds', 'validated_current_epoch_milliseconds',
        'session_deadline_epoch_milliseconds', 'stop_epoch_milliseconds',
        'nondecreasing_integer_observations', 'checked_before_and_after_every_loader_attempt',
        'time_source_assumption', 'callback_interruption_guaranteed_here'},
        'complete per-load clock evidence required')
    session = json.loads(packet['metadata']['raw_session_proof'])
    need(clock['session_started_epoch_milliseconds'] == session['started_epoch_milliseconds']
         and clock['validated_current_epoch_milliseconds'] == authority['validated_current_epoch_milliseconds']
         and clock['session_deadline_epoch_milliseconds'] == authority['session_deadline_epoch_milliseconds']
         and clock['stop_epoch_milliseconds'] == authority['stop_epoch_milliseconds']
         and clock['checked_before_and_after_every_loader_attempt'] is True
         and clock['callback_interruption_guaranteed_here'] is False,
         'child source clock bounds or authority differ')
    observations = clock['nondecreasing_integer_observations']
    need(type(observations) is list and len(observations) == 12,
         'exactly twelve ordered before/after observations required')
    previous = authority['validated_current_epoch_milliseconds']
    for label, phase, got in zip(
            [label for label in LABELS for _ in (0, 1)], ['before', 'after']*6,
            observations, strict=True):
        need(type(got) is dict and set(got) == {'scan', 'phase', 'epoch_milliseconds'}
             and got['scan'] == label and got['phase'] == phase
             and type(got['epoch_milliseconds']) is int,
             'ordered typed per-load observation required')
        now = got['epoch_milliseconds']
        need(previous <= now < clock['session_deadline_epoch_milliseconds']
             and now < clock['stop_epoch_milliseconds'], 'child clock regressed or expired')
        previous = now
    return value


@dataclass(frozen=True)
class Result:
    payload: bytes
    capture_payload: bytes | None

    def record(self):
        return json.loads(self.payload)


def dispatch(raw_scope, expected_scope_pin, *, scope_path, expected_claim_root):
    """One irreversible local engineering dispatch; never actual science."""
    started = time.monotonic()
    spec = validate_scope(parse(raw_scope, expected_scope_pin), expected_claim_root)
    need(time.time_ns()//1000000 < STOP_MS, 'fixed plan end reached')
    claim_path = reserve(spec, expected_claim_root, expected_scope_pin)
    capture_payload = None
    capture_record = None
    child_result = None
    error = None
    outcome = 'CLOSED_FAILED'
    try:
        need(read_checked({'path': absolute(scope_path), 'mode': 0o400, **expected_scope_pin}) == raw_scope,
             'immutable scope file differs')
        read_checked(spec['runner']); read_checked(spec['child'])
        read_checked(spec['python'], cap=MAX_EXECUTABLE)
        modules = load_modules(spec)
        packet, admission, _ = admitted_fixture(spec, modules)
        remaining = spec['timeout_seconds']-(time.monotonic()-started)
        need(remaining > 0, 'engineering deadline expired before child dispatch')
        argv = [spec['python']['path'], '-I', '-S', '-B', spec['child']['path'],
                scope_path, expected_scope_pin['sha256'], str(expected_scope_pin['bytes'])]
        result = modules['failure_output_retention'].capture(argv,
            destination=claim_path+'/capture', repository_root=ROOT,
            stdout_cap=spec['stdout_cap_bytes'], stderr_cap=spec['stderr_cap_bytes'],
            timeout_seconds=remaining, env=spec['environment'])
        capture_payload = result.payload; capture_record = result.record()
        need(capture_record['strictly_completed'] is True,
             'child/capture closed: '+capture_record['process_status'])
        # Re-read every selected source/input. Any exception still retains capture.
        for name in ('runner', 'child', 'python', 'packet'):
            read_checked(spec[name], cap=MAX_EXECUTABLE if name == 'python' else MAX_METADATA)
        for expected in spec['modules'].values():
            read_checked(expected)
        need(time.monotonic()-started < spec['timeout_seconds'], 'whole-dispatch engineering timeout exceeded')
        raw = modules['failure_output_retention'].reconstruct_raw(
            capture_record['streams']['stdout']['reconstruction'])
        child_result = verify_child(raw, spec, packet, admission)
        outcome = 'SYNTHETIC_PROCESS_QUALIFIED'
    except BaseException as cause:
        error = type(cause).__name__+': '+str(cause)
    terminal = {
        'schema': 'radio-engineering-receiver-dispatch-result-v2',
        'domain': 'synthetic-test-fixture', 'status': outcome,
        'dispatch_identity': spec['dispatch_identity'], 'scope_pin': expected_scope_pin,
        'claim_path': claim_path, 'claim_permanently_spent': True,
        'elapsed_milliseconds': math.ceil((time.monotonic()-started)*1000),
        'capture_sha256': None if capture_payload is None else pin(capture_payload)['sha256'],
        'capture_process_status': None if capture_record is None else capture_record['process_status'],
        'error': error, 'child_result': child_result,
        'automatic_retry': False, 'actual_atomic_cas_qualified': False,
        'whole_descendant_lifetime_qualified': False,
        'full_runtime_closure_qualified': False, 'scientific_execution_authorized': False,
        'scientific_allocation_charged': False, 'telescope_values_opened': False}
    fd = directory(claim_path)
    try:
        if capture_payload is not None:
            exclusive_write(fd, 'capture-proof.json', capture_payload)
        exclusive_write(fd, 'terminal.json', canonical(terminal))
    finally:
        os.close(fd)
    return Result(canonical(terminal), capture_payload)
