"""Bounded one-shot scientific child supervisor; no authority is created here.

The caller supplies an already maintained ``VerifiedAdmission`` and the exact
raw current-session proof.  This module binds those objects, an explicit
environment, immutable file pins, a receiver-adapter pin and a dispatch
identity to one exclusive failure-retention destination.  It delegates the
single launch to the separately qualified diagnostic retention utility.

The child must emit one canonical result envelope.  Nonzero exit, timeout,
output overflow, malformed output, clock regression/expiry or any persistence
error is terminal.  There is no retry, destination reuse, refund or fallback.
The synthetic domain remains blocked from telescope data and scientific
authority.  Successful public-domain use still depends on genuine maintained
closure/admission, hosted runtime, atomic CAS and allocation evidence supplied
outside this module.
"""
from dataclasses import dataclass
import hashlib
import json
import os
import re
import stat

from scientific_runtime import load_raw, sha256
from scientific_store import VerifiedAdmission
from scientific_admission import VerifiedClosure
from failure_output_retention import CaptureResult, capture, reconstruct_raw


SCHEMA = 'radio-bounded-scientific-runner-v1'
RESULT_SCHEMA = 'radio-bounded-scientific-child-result-v1'
DOMAINS = ('synthetic-test-fixture', 'public-scientific-evidence')
MAX_SPEC_BYTES = 1024 * 1024
MAX_FILES = 256
MAX_ENVIRONMENT = 256
MAX_ENVIRONMENT_BYTES = 65536
_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,127}')


class RunnerError(RuntimeError):
    """Closed runner disposition; the dispatch must never be retried."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _need(condition, reason):
    if not condition:
        raise RunnerError(reason)


def _absolute(value):
    _need(type(value) is str and 0 < len(value) <= 4096 and value.startswith('/') and
          value == os.path.normpath(value) and '\\' not in value and
          all(part not in ('', '.', '..') for part in value.split('/')[1:]) and
          all(ord(char) >= 32 for char in value), 'canonical absolute path required')
    return value


def _environment(value):
    _need(type(value) is dict and len(value) <= MAX_ENVIRONMENT,
          'finite explicit child environment required')
    result = {}
    total = 0
    for key, item in value.items():
        _need(type(key) is str and _NAME.fullmatch(key) and type(item) is str and
              '\x00' not in item and len(item) <= 4096,
              'plain bounded environment entry required')
        total += len(key.encode('utf-8')) + len(item.encode('utf-8'))
        _need(total <= MAX_ENVIRONMENT_BYTES, 'child environment capacity exhausted')
        result[key] = item
    return result


def _read_pinned_files(rows):
    _need(type(rows) is list and 0 < len(rows) <= MAX_FILES,
          'finite immutable worker file inventory required')
    seen = set()
    held = []
    records = []
    try:
        for row in rows:
            _need(type(row) is dict and
                  set(row) == {'closure_identity', 'path', 'mode', 'bytes', 'sha256'},
                  'exact worker file pin required')
            path = _absolute(row['path'])
            _need(path not in seen and row['mode'] in ('100644', '100755') and
                  type(row['bytes']) is int and 0 < row['bytes'] <= 1024**3,
                  'distinct bounded ordinary worker file required')
            sha256(row['sha256'])
            seen.add(path)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            held.append(fd)
            before = os.fstat(fd)
            wanted_mode = 0o755 if row['mode'] == '100755' else 0o644
            _need(stat.S_ISREG(before.st_mode) and before.st_nlink >= 1 and
                  stat.S_IMODE(before.st_mode) == wanted_mode and before.st_size == row['bytes'],
                  'worker file type, link, mode or size differs')
            data = bytearray()
            while len(data) < before.st_size:
                block = os.read(fd, min(65536, before.st_size - len(data)))
                _need(bool(block), 'worker file changed during held readback')
                data.extend(block)
            after = os.fstat(fd)
            _need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                   before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                                           after.st_mtime_ns, after.st_ctime_ns) and
                  hashlib.sha256(data).hexdigest() == row['sha256'],
                  'worker file identity or bytes differ from independent pin')
            records.append((path, fd, before))
        return held, records
    except BaseException:
        for fd in held:
            os.close(fd)
        raise


def _inventory_sets(rows):
    _need(type(rows) is list and 0 < len(rows) <= MAX_FILES,
          'finite immutable worker file inventory required')
    paths = set()
    hashes = set()
    for row in rows:
        _need(type(row) is dict and
              set(row) == {'closure_identity', 'path', 'mode', 'bytes', 'sha256'} and
              type(row['closure_identity']) is str and
              re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', row['closure_identity']),
              'exact worker file pin required')
        path = _absolute(row['path'])
        sha256(row['sha256'])
        _need(path not in paths, 'distinct worker file paths required')
        paths.add(path); hashes.add(row['sha256'])
    return paths, hashes


def _bind_closure_inventory(rows, manifest, repository_root):
    _need(type(manifest) is dict and type(manifest.get('inventory')) is dict,
          'authenticated executable freeze inventory required')
    repository_root = _absolute(repository_root)
    inventory = manifest['inventory']
    identities = set()
    for row in rows:
        identity = row['closure_identity']
        _need(identity not in identities and identity in inventory,
              'distinct worker closure identity required')
        identities.add(identity)
        frozen = inventory[identity]
        _need(type(frozen) is dict and
              set(frozen) == {'role', 'location', 'path', 'mode', 'bytes', 'sha256'},
              'exact executable freeze inventory row required')
        if frozen['location'] == 'repository':
            expected_path = os.path.join(repository_root, frozen['path'])
        else:
            _need(frozen['location'] == 'runtime', 'worker closure location differs')
            expected_path = frozen['path']
        _need(row['path'] == expected_path and
              {key: row[key] for key in ('mode', 'bytes', 'sha256')} ==
              {key: frozen[key] for key in ('mode', 'bytes', 'sha256')},
              'worker file differs from authenticated executable freeze')


def _files_unchanged(records):
    for path, fd, before in records:
        held = os.fstat(fd)
        visible = os.stat(path, follow_symlinks=False)
        _need(stat.S_ISREG(visible.st_mode) and
              (held.st_dev, held.st_ino, held.st_size, held.st_mtime_ns, held.st_ctime_ns) ==
              (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) and
              (visible.st_dev, visible.st_ino, visible.st_size, visible.st_mtime_ns,
               visible.st_ctime_ns) ==
              (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
               before.st_ctime_ns),
              'worker file pathname or identity changed across dispatch')


class _Clock:
    def __init__(self, live_clock, admission, session):
        _need(callable(live_clock), 'independently supplied live clock required')
        self.live_clock = live_clock
        self.start = session.get('started_epoch_milliseconds')
        self.anchor = admission.get('validated_current_epoch_milliseconds')
        self.deadline = admission.get('session_deadline_epoch_milliseconds')
        self.stop = admission.get('stop_epoch_milliseconds')
        _need(all(type(value) is int for value in
                  (self.start, self.anchor, self.deadline, self.stop)) and
              self.start <= self.anchor < self.deadline <= self.stop and
              session.get('deadline_epoch_milliseconds') == self.deadline,
              'authenticated dispatch clock bounds differ')
        self.previous = None
        self.observations = []

    def observe(self, phase):
        now = self.live_clock()
        _need(type(now) is int and now >= self.anchor and
              (self.previous is None or now >= self.previous), 'live clock regressed or is invalid')
        _need(self.start <= now < self.deadline and now < self.stop,
              'source session or plan deadline expired '+phase+' dispatch')
        self.previous = now
        self.observations.append({'phase': phase, 'epoch_milliseconds': now})
        return now

    def record(self):
        return {'session_started_epoch_milliseconds': self.start,
                'validated_current_epoch_milliseconds': self.anchor,
                'session_deadline_epoch_milliseconds': self.deadline,
                'stop_epoch_milliseconds': self.stop,
                'nondecreasing_integer_observations': self.observations,
                'checked_before_and_after_child': True}


def _child_result(raw, spec):
    _need(type(raw) is bytes and 0 < len(raw) <= spec['stdout_cap_bytes'],
          'one bounded child result required')
    try:
        value = json.loads(raw, object_pairs_hook=lambda pairs: _unique(pairs),
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise RunnerError('invalid child result JSON') from error
    fields = {'schema', 'evidence_domain', 'status', 'dispatch_identity',
              'admission_sha256', 'session_proof_sha256', 'receiver_adapter_sha256',
              'live_clock_record', 'telescope_values_opened',
              'scientific_execution_authorized', 'automatic_retry'}
    _need(type(value) is dict and set(value) == fields and canonical(value) == raw and
          value['schema'] == RESULT_SCHEMA and value['evidence_domain'] == spec['evidence_domain'] and
          value['dispatch_identity'] == spec['dispatch_identity'] and
          value['admission_sha256'] == spec['admission_sha256'] and
          value['session_proof_sha256'] == spec['session_proof_sha256'] and
          value['receiver_adapter_sha256'] == spec['receiver_adapter_sha256'] and
          value['automatic_retry'] is False,
          'child result binding or canonical encoding differs')
    clock = value['live_clock_record']
    _need(type(clock) is dict and
          clock.get('checked_before_and_after_every_loader_attempt') is True and
          type(clock.get('nondecreasing_integer_observations')) is list,
          'child per-load clock evidence missing')
    if spec['evidence_domain'] == 'synthetic-test-fixture':
        _need(value['status'] == 'SYNTHETIC_INTERFACE_QUALIFIED' and
              value['telescope_values_opened'] is False and
              value['scientific_execution_authorized'] is False,
              'synthetic child attempted to claim telescope or scientific authority')
    else:
        _need(value['status'] == 'ADMITTED_ROWS_VERIFIED' and
              value['telescope_values_opened'] is True and
              value['scientific_execution_authorized'] is True,
              'public child result lacks exact admitted authority')
    return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _closure_manifest(raw, expected_pin):
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_SPEC_BYTES and
          type(expected_pin) is dict and set(expected_pin) == {'bytes', 'sha256'} and
          type(expected_pin['bytes']) is int and expected_pin['bytes'] == len(raw) and
          hashlib.sha256(raw).hexdigest() == sha256(expected_pin['sha256']),
          'bounded authenticated executable freeze bytes required')
    try:
        value = json.loads(raw, object_pairs_hook=lambda pairs: _unique(pairs),
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise RunnerError('invalid executable freeze JSON') from error
    encoded = canonical(value)
    _need(raw == encoded or raw + b'\n' == encoded,
          'canonical executable freeze encoding required')
    return value


@dataclass(frozen=True)
class RunnerResult:
    payload: bytes
    capture_payload: bytes

    def record(self):
        return json.loads(self.payload)


def dispatch_once(raw_spec, expected_spec_pin, *, verified_admission,
                  verified_closure, raw_execution_manifest,
                  expected_execution_manifest_pin, raw_session_proof,
                  expected_session_proof_pin, live_clock,
                  destination, repository_root, protected_roots=()):
    """Perform one terminal dispatch through the bounded retention utility."""
    spec = load_raw(raw_spec, expected_spec_pin, cap=MAX_SPEC_BYTES)
    fields = {'schema', 'evidence_domain', 'dispatch_identity', 'argv', 'environment',
              'worker_files', 'admission_sha256', 'session_proof_sha256',
              'failure_retention_sha256', 'receiver_adapter_sha256',
              'timeout_seconds', 'stdout_cap_bytes', 'stderr_cap_bytes',
              'scientific_execution_authorized'}
    _need(set(spec) == fields and spec['schema'] == SCHEMA and
          spec['evidence_domain'] in DOMAINS, 'runner specification schema/domain differs')
    sha256(spec['dispatch_identity']); sha256(spec['admission_sha256'])
    sha256(spec['session_proof_sha256']); sha256(spec['failure_retention_sha256'])
    sha256(spec['receiver_adapter_sha256'])
    _need(type(verified_admission) is VerifiedAdmission and
          hashlib.sha256(verified_admission.payload).hexdigest() == spec['admission_sha256'],
          'maintained verified admission or binding required')
    admission = verified_admission.record()
    _need(type(verified_closure) is VerifiedClosure and
          admission.get('closure_sha256') == hashlib.sha256(verified_closure.payload).hexdigest(),
          'maintained verified closure must bind current admission')
    closure = verified_closure.record()
    _need(closure.get('evidence_domain') == spec['evidence_domain'],
          'closure domain differs from dispatch')
    manifest = _closure_manifest(raw_execution_manifest, expected_execution_manifest_pin)
    _need(closure.get('document_sha256s', {}).get('executable_freeze') ==
          expected_execution_manifest_pin['sha256'],
          'executable freeze differs from authenticated closure')
    _need(admission.get('domain') == spec['evidence_domain'], 'admission domain differs')
    if spec['evidence_domain'] == 'synthetic-test-fixture':
        _need(admission.get('status') == 'PENDING' and
              admission.get('scientific_execution_authorized') is False and
              spec['scientific_execution_authorized'] is False,
              'synthetic runner must remain blocked')
    else:
        _need(admission.get('status') == 'ACTIVE' and
              admission.get('scientific_execution_authorized') is True and
              spec['scientific_execution_authorized'] is True,
              'genuine ACTIVE scientific admission required')
    session = load_raw(raw_session_proof, expected_session_proof_pin)
    _need(expected_session_proof_pin['sha256'] == spec['session_proof_sha256'],
          'session proof raw binding differs')
    _need(type(spec['argv']) is list and 0 < len(spec['argv']) <= 128 and
          all(type(item) is str and item and len(item) <= 4096 and '\x00' not in item
              for item in spec['argv']), 'exact bounded argv required')
    env = _environment(spec['environment'])
    _need(type(spec['timeout_seconds']) in (int, float) and
          0 < spec['timeout_seconds'] <= 4800 and
          all(type(spec[key]) is int and 0 <= spec[key] <= 1024*1024
              for key in ('stdout_cap_bytes', 'stderr_cap_bytes')),
          'bounded child time/output limits required')
    pinned_paths, pinned_hashes = _inventory_sets(spec['worker_files'])
    _bind_closure_inventory(spec['worker_files'], manifest, repository_root)
    _need(spec['argv'][0] in pinned_paths and
          spec['failure_retention_sha256'] in pinned_hashes and
          spec['receiver_adapter_sha256'] in pinned_hashes,
          'launcher, failure retention and receiver adapter must occur in pinned worker inventory')
    clock = _Clock(live_clock, admission, session)
    before = clock.observe('before')
    remaining = (clock.deadline - before) / 1000
    _need(remaining > 0 and spec['timeout_seconds'] <= remaining,
          'child timeout exceeds authenticated remaining session')
    held, records = _read_pinned_files(spec['worker_files'])
    try:
        result = capture(spec['argv'], destination=destination,
                         repository_root=repository_root, protected_roots=protected_roots,
                         stdout_cap=spec['stdout_cap_bytes'], stderr_cap=spec['stderr_cap_bytes'],
                         timeout_seconds=spec['timeout_seconds'], env=env)
        _need(type(result) is CaptureResult, 'maintained capture result required')
        capture_record = result.record()
        _files_unchanged(records)
        after_error = None
        try:
            clock.observe('after')
        except BaseException as error:
            after_error = str(error)
        completed = capture_record.get('strictly_completed') is True and after_error is None
        child = None
        child_error = None
        if completed:
            try:
                child = _child_result(reconstruct_raw(capture_record['streams']['stdout']['reconstruction']), spec)
            except BaseException as error:
                child_error = type(error).__name__+': '+str(error)
                completed = False
        terminal = {'schema': 'radio-bounded-scientific-runner-result-v1',
                    'evidence_domain': spec['evidence_domain'],
                    'status': 'QUALIFIED' if completed else 'CLOSED_FAILED',
                    'dispatch_identity': spec['dispatch_identity'],
                    'spec_sha256': expected_spec_pin['sha256'],
                    'capture_sha256': hashlib.sha256(result.payload).hexdigest(),
                    'capture_process_status': capture_record.get('process_status'),
                    'capture_strictly_completed': capture_record.get('strictly_completed'),
                    'child_result': child, 'child_result_error': child_error,
                    'post_dispatch_clock_error': after_error,
                    'outer_clock': clock.record(), 'automatic_retry': False,
                    'destination_reuse_allowed': False,
                    'scientific_execution_authorized': completed and
                        spec['evidence_domain'] == 'public-scientific-evidence',
                    'telescope_values_opened': bool(child and child['telescope_values_opened'])}
        return RunnerResult(canonical(terminal), result.payload)
    finally:
        for fd in held:
            os.close(fd)
