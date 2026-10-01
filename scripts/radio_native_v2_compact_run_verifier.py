#!/usr/bin/env python3
"""Verify retained transport receipts sequentially with compact custody.

This is a separately versioned verification component, not the old full-run
receipt schema or an execution certificate. Exact raw caller files remain in
their original scopes. Their pins and filesystem identities are durably stored
here, and every semantic verification reopens the pinned file. No case is run,
retried, renamed, scored or reserved. Independent process RSS/time observation
and joins to the host's complete receipt/storage ledger remain required.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from seti_repeater import native_v2_transport_contract_radio as contract
from seti_repeater.empty_null_radio import canonical

SCHEMA = 'radio-native-v2-compact-retained-run-verifier-v1'
PLAN_SCHEMA = 'radio-native-v2-compact-retained-run-plan-v1'
CASE_STORAGE_BYTES = 192 * 1024**2
TOTAL_STORAGE_BYTES = 1536 * 1024**2
METADATA_RESERVATION_BYTES = 65536
SMALL_FILE_BYTES = 16384
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_executions': 0,
    'scientific_cases_run': 0, 'rng_draws': 0, 'telescope_reads': 0,
    'automatic_retry': False, 'runtime_resource_qualification_complete': False,
    'host_ledger_join_complete': False}


def _integer(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Nonnegative integer required: ' + label)
    return value


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact SHA256 required')
    return value


def _absolute(value):
    value = os.fspath(value)
    if (not value.startswith('/') or value == '/' or '\\' in value
            or any(part in ('', '.', '..') for part in value[1:].split('/'))
            or any(ord(char) < 32 for char in value)):
        raise ValueError('Canonical absolute path required')
    return value


def _directory(path):
    if path == '/':
        return os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in _absolute(path)[1:].split('/'):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _identity(value):
    return {'device': value.st_dev, 'inode': value.st_ino}


def _file_identity(value):
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise ValueError('Sole-link regular raw receipt required')
    return {**_identity(value), 'bytes': value.st_size, 'allocated_bytes': value.st_blocks * 512,
        'mode': stat.S_IMODE(value.st_mode), 'mtime_ns': value.st_mtime_ns,
        'ctime_ns': value.st_ctime_ns}


def _write_all(fd, payload):
    view = memoryview(payload)
    while view:
        amount = os.write(fd, view)
        if amount <= 0:
            raise OSError('Incomplete durable metadata write')
        view = view[amount:]


def _code_pins():
    files = (Path(__file__).resolve(), Path(contract.__file__).resolve(),
        REPO / 'src/seti_repeater/empty_null_radio.py', REPO / 'src/seti_repeater/__init__.py')
    result = {}
    for path in files:
        raw = path.read_bytes()
        result[str(path.relative_to(REPO))] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return result


def validate_plan(plan):
    """Fix exact source identities and conservative storage before verification."""
    if not isinstance(plan, dict) or set(plan) != {'schema', 'run_id', 'cases'} or plan['schema'] != PLAN_SCHEMA:
        raise ValueError('Exact compact retained-run plan required')
    if not isinstance(plan['run_id'], str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,79}', plan['run_id']):
        raise ValueError('Safe distinct verification run identity required')
    cases = plan['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise ValueError('One to eight prospectively identified retained inputs required')
    required = {'ordinal', 'source_case_id', 'source_path', 'bytes', 'sha256',
        'client_peak_rss_bytes', 'other_host_receipt_bytes', 'other_host_receipt_allocated_bytes'}
    identities = set(); paths = set(); hashes = set(); logical = allocated = 0
    for ordinal, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != required or type(case['ordinal']) is not int or case['ordinal'] != ordinal:
            raise ValueError('Exact ordered retained input fields required')
        identity = case['source_case_id']
        if not isinstance(identity, str) or not 1 <= len(identity) <= 256 or any(ord(c) < 32 for c in identity):
            raise ValueError('Unchanged original source-case identity required')
        path = _absolute(case['source_path']); digest = _sha(case['sha256'])
        if identity in identities or path in paths or digest in hashes:
            raise ValueError('A retained case/file/hash cannot be relabeled or replayed twice')
        identities.add(identity); paths.add(path); hashes.add(digest)
        raw_bytes = _integer(case['bytes'], 'raw_receipt_bytes')
        if raw_bytes == 0:
            raise ValueError('Nonempty exact raw receipt required')
        rss = _integer(case['client_peak_rss_bytes'], 'client_peak_rss_bytes')
        if not 0 < rss <= contract.RSS_BYTES:
            raise ValueError('Measured caller process RSS cap exceeded')
        other = _integer(case['other_host_receipt_bytes'], 'other_host_receipt_bytes')
        other_allocated = _integer(case['other_host_receipt_allocated_bytes'], 'other_host_receipt_allocated_bytes')
        if raw_bytes + other + METADATA_RESERVATION_BYTES > CASE_STORAGE_BYTES:
            raise ValueError('Original 192MiB per-case host receipt allocation exceeded')
        if raw_bytes + other_allocated + METADATA_RESERVATION_BYTES > CASE_STORAGE_BYTES:
            raise ValueError('Original 192MiB per-case allocated host receipt reservation exceeded')
        logical += raw_bytes + other + METADATA_RESERVATION_BYTES
        allocated += raw_bytes + other_allocated + METADATA_RESERVATION_BYTES
    if logical > TOTAL_STORAGE_BYTES or allocated > TOTAL_STORAGE_BYTES:
        raise ValueError('Original 1536MiB whole-run host receipt allocation exceeded')
    if len(canonical(plan)) + 1 > SMALL_FILE_BYTES:
        raise ValueError('Compact prospective plan exceeds metadata bound')
    return json.loads(canonical(plan))


class CompactRunVerifier:
    """Exclusive, fail-closed verifier retaining no prior full client objects.

    The plan binds external raw receipts rather than duplicating them. Its
    ``other_host_receipt_*`` values must cover all remaining host receipts; this
    component cannot independently discover or certify that external ledger.
    Source case IDs are assertions from that frozen ledger, never invented by
    this verifier. All accounting and semantic failures permanently stop it.
    """
    def __init__(self, root, plan):
        self.plan = validate_plan(plan)
        self.root = _absolute(root)
        self.cases = []; self.stopped = False; self.finished = False
        self.metadata = {}
        self.started = time.monotonic()
        self.code_pins = _code_pins()
        self.plan_sha256 = hashlib.sha256(canonical(self.plan)).hexdigest()
        parent, name = self.root.rsplit('/', 1)
        fd = _directory(parent or '/')
        try:
            os.mkdir(name, mode=0o700, dir_fd=fd)
            os.fsync(fd)
        finally:
            os.close(fd)
        fd = _directory(self.root)
        try:
            self.root_identity = _identity(os.fstat(fd))
        finally:
            os.close(fd)
        self._write('plan.json', self.plan)

    def _root_fd(self):
        fd = _directory(self.root)
        if _identity(os.fstat(fd)) != self.root_identity:
            os.close(fd)
            raise ValueError('Exclusive verifier receipt directory identity changed')
        return fd

    def _write(self, name, value):
        payload = canonical(value) + b'\n'
        if len(payload) > SMALL_FILE_BYTES:
            raise ValueError('Compact metadata exceeds frozen bound')
        directory = self._root_fd()
        fd = None
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400, dir_fd=directory)
            _write_all(fd, payload); os.fsync(fd)
            wanted = _file_identity(os.fstat(fd))
            os.close(fd); fd = None
            os.fsync(directory)
            reopened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                raw = os.read(reopened, SMALL_FILE_BYTES + 1)
                if raw != payload or _file_identity(os.fstat(reopened)) != wanted:
                    raise ValueError('Independent compact metadata readback differs')
            finally:
                os.close(reopened)
            independent_directory = self._root_fd()
            os.close(independent_directory)
            self.metadata[name] = {'sha256': hashlib.sha256(payload).hexdigest(), 'file': wanted}
        finally:
            if fd is not None: os.close(fd)
            os.close(directory)

    def _verify_metadata(self):
        if hashlib.sha256(canonical(self.plan)).hexdigest() != self.plan_sha256:
            raise ValueError('Prospective retained-input plan changed')
        if _code_pins() != self.code_pins:
            raise ValueError('Verifier or transport contract code changed after initialization')
        directory = self._root_fd()
        try:
            if set(os.listdir(directory)) != set(self.metadata):
                raise ValueError('Unaccounted entry in exclusive verifier receipt directory')
            usage = {ordinal: {'logical_bytes': 0, 'allocated_bytes': 0} for ordinal in range(len(self.plan['cases']))}
            for name, pin in self.metadata.items():
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    identity = _file_identity(os.fstat(fd))
                    raw = os.read(fd, SMALL_FILE_BYTES + 1)
                    if (identity != pin['file'] or len(raw) != identity['bytes']
                            or hashlib.sha256(raw).hexdigest() != pin['sha256']):
                        raise ValueError('Durable compact metadata identity or SHA256 differs')
                finally:
                    os.close(fd)
                ordinal = int(name[4:6]) if re.fullmatch('case[0-9]{2}\\.json', name) else 0
                usage[ordinal]['logical_bytes'] += identity['bytes']
                usage[ordinal]['allocated_bytes'] += identity['allocated_bytes']
            if any(max(value.values()) > METADATA_RESERVATION_BYTES for value in usage.values()):
                raise ValueError('Frozen compact metadata storage reservation exceeded')
            return {'case_usage': usage, 'logical_bytes': sum(value['logical_bytes'] for value in usage.values()),
                'allocated_bytes': sum(value['allocated_bytes'] for value in usage.values()),
                'final_receipt_file_itself_may_be_pending': not self.finished,
                'final_receipt_storage_already_reserved': True}
        finally:
            os.close(directory)

    def _fail(self, error):
        self.stopped = True
        try:
            self._write('failure.json', {'schema': SCHEMA, 'status': 'CLOSED_FAILED',
                'accepted_case_count': len(self.cases), 'error': repr(error), **AUTHORITY})
        except (OSError, ValueError):
            pass

    def _read_case(self, spec, expected_identity=None):
        """One raw buffer/parse at a time; source names and ancestors are rewalked."""
        parent, name = spec['source_path'].rsplit('/', 1)
        directory = _directory(parent or '/')
        fd = None
        try:
            parent_identity = _identity(os.fstat(directory))
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            identity = _file_identity(os.fstat(fd))
            if identity['bytes'] != spec['bytes']:
                raise ValueError('Pinned raw receipt byte length differs')
            if expected_identity is not None and (identity != expected_identity['file'] or parent_identity != expected_identity['parent']):
                raise ValueError('Retained raw receipt filesystem identity changed')
            if identity['allocated_bytes'] + spec['other_host_receipt_allocated_bytes'] + METADATA_RESERVATION_BYTES > CASE_STORAGE_BYTES:
                raise ValueError('Original 192MiB actual allocated host receipt cap exceeded')
            os.fsync(fd); os.fsync(directory)
            os.close(fd); fd = None
            # The authoritative read is a distinct open after file/directory
            # fsync. A fresh path walk detects replaced parent directories.
            reopened_parent = _directory(parent or '/')
            try:
                reopened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=reopened_parent)
                try:
                    if (_identity(os.fstat(reopened_parent)) != parent_identity
                            or _file_identity(os.fstat(reopened)) != identity):
                        raise ValueError('Independent raw receipt reopen identity differs')
                    # Hash the exact bytes used by the parser. Release the raw
                    # buffer before constructing defensive contract copies.
                    with os.fdopen(os.dup(reopened), 'rb') as stream:
                        raw = stream.read(spec['bytes'] + 1)
                    if len(raw) != spec['bytes'] or hashlib.sha256(raw).hexdigest() != spec['sha256']:
                        raise ValueError('Pinned raw receipt SHA256 differs')
                    parsed = json.loads(raw)
                    del raw
                    if _file_identity(os.fstat(reopened)) != identity:
                        raise ValueError('Raw receipt changed during exact parse')
                finally:
                    os.close(reopened)
            finally:
                os.close(reopened_parent)
            qualified = parsed.get('qualified') if isinstance(parsed, dict) else None
            if not isinstance(qualified, dict) or not {'client', 'persistence'} <= set(qualified):
                raise ValueError('Exact retained qualified client and persistence required')
            source_client = qualified['client']; source_persistence = qualified['persistence']
            del qualified, parsed
            # These are the unchanged public validators used by RunTranscript.
            client = contract.validate_client(source_client, qualified=True)
            del source_client
            persistence = contract.validate_persistence(source_persistence, client)
            del source_persistence
            usage = client['usage']
            tail_seconds = persistence.get('elapsed_seconds')
            if type(tail_seconds) not in (int, float) or not math.isfinite(tail_seconds) or tail_seconds < 0:
                raise ValueError('Measured caller tail elapsed time required')
            row = {'ordinal': spec['ordinal'], 'source_case_id': spec['source_case_id'],
                'source_path': spec['source_path'], 'bytes': spec['bytes'], 'sha256': spec['sha256'],
                'filesystem_identity': {'parent': parent_identity, 'file': identity},
                'client_binding_sha256': contract.client_binding_sha256(client),
                'tail_payload_sha256': hashlib.sha256(contract.caller_tail_payload(client)).hexdigest(),
                'client_peak_rss_bytes': spec['client_peak_rss_bytes'],
                'calls': usage['calls_including_declared_git_processes'] + persistence['calls'],
                'request_bytes': usage['request_bytes'] + persistence['request_bytes'],
                'response_bytes': usage['response_bytes'] + persistence['response_bytes'],
                'elapsed_seconds': persistence['shared_case_elapsed_seconds'],
                'host_receipt_reserved_bytes': spec['bytes'] + spec['other_host_receipt_bytes'] + METADATA_RESERVATION_BYTES,
                'host_receipt_allocated_reserved_bytes': identity['allocated_bytes'] + spec['other_host_receipt_allocated_bytes'] + METADATA_RESERVATION_BYTES,
                'raw_receipt_independently_reopened': True, 'source_scope_unchanged': True}
            del client, persistence, usage
            if (row['calls'] > contract.CASE_CALLS or row['request_bytes'] > contract.CASE_REQUEST_BYTES
                    or row['response_bytes'] > contract.CASE_RESPONSE_BYTES or row['elapsed_seconds'] > contract.CASE_SECONDS):
                raise ValueError('Combined caller case allocation exceeded')
            return row
        finally:
            if fd is not None: os.close(fd)
            os.close(directory)

    def _totals(self, rows):
        totals = {field: sum(row[field] for row in rows) for field in
            ('calls', 'request_bytes', 'response_bytes', 'elapsed_seconds',
             'host_receipt_reserved_bytes', 'host_receipt_allocated_reserved_bytes')}
        if (totals['calls'] > contract.TOTAL_CALLS or totals['request_bytes'] > contract.TOTAL_REQUEST_BYTES
                or totals['response_bytes'] > contract.TOTAL_RESPONSE_BYTES or totals['elapsed_seconds'] > contract.TOTAL_SECONDS
                or totals['host_receipt_reserved_bytes'] > TOTAL_STORAGE_BYTES
                or totals['host_receipt_allocated_reserved_bytes'] > TOTAL_STORAGE_BYTES):
            raise ValueError('Cumulative eight-case allocation exceeded')
        return totals

    def append(self, ordinal):
        if self.stopped or self.finished:
            raise RuntimeError('Compact verifier closed; no retry or resume')
        try:
            if type(ordinal) is not int or ordinal != len(self.cases) or ordinal >= len(self.plan['cases']):
                raise ValueError('Exact next retained case ordinal required')
            fd = self._root_fd(); os.close(fd)
            row = self._read_case(self.plan['cases'][ordinal])
            if any(row['filesystem_identity']['file']['device'] == old['filesystem_identity']['file']['device']
                    and row['filesystem_identity']['file']['inode'] == old['filesystem_identity']['file']['inode'] for old in self.cases):
                raise ValueError('Raw receipt inode cannot be relabeled as another case')
            self._totals(self.cases + [row])
            self._write('case%02d.json' % ordinal, {'schema': SCHEMA, 'plan_sha256': self.plan_sha256, 'case': row, **AUTHORITY})
            self._verify_metadata()
            self.cases.append(row)
            return json.loads(canonical(row))
        except BaseException as error:
            self._fail(error)
            raise

    def receipt(self):
        if self.stopped:
            raise RuntimeError('Compact verifier closed; no retry or resume')
        try:
            metadata_storage = self._verify_metadata()
            # Reopen/hash/semantic verification is sequential, never eight full
            # parses at once. No previous client strings survive in self.cases.
            for old in self.cases:
                row = self._read_case(self.plan['cases'][old['ordinal']], old['filesystem_identity'])
                if row != old:
                    raise ValueError('Independent final retained-case semantic readback differs')
                del row
            return {'schema': SCHEMA, 'status': 'COMPONENT_COMPLETE' if len(self.cases) == 8 else 'INCOMPLETE',
                'mode': 'RETAINED_RECEIPT_VERIFICATION_ONLY', 'case_count': len(self.cases),
                'planned_case_count': len(self.plan['cases']), 'cases': json.loads(canonical(self.cases)),
                'plan_sha256': self.plan_sha256, 'code_pins': self.code_pins,
                'root': self.root, 'root_filesystem_identity': self.root_identity,
                'metadata_storage': metadata_storage,
                'verification_elapsed_seconds': time.monotonic() - self.started,
                'original_limits': {'case_calls': contract.CASE_CALLS, 'run_calls': contract.TOTAL_CALLS,
                    'case_request_bytes': contract.CASE_REQUEST_BYTES, 'run_request_bytes': contract.TOTAL_REQUEST_BYTES,
                    'case_response_bytes': contract.CASE_RESPONSE_BYTES, 'run_response_bytes': contract.TOTAL_RESPONSE_BYTES,
                    'case_seconds': contract.CASE_SECONDS, 'run_seconds': contract.TOTAL_SECONDS,
                    'process_rss_bytes': contract.RSS_BYTES, 'case_host_receipt_bytes': CASE_STORAGE_BYTES,
                    'run_host_receipt_bytes': TOTAL_STORAGE_BYTES},
                'all_visible_polls_and_deliveries_counted': True, 'hidden_http_bytes_known': False,
                'external_host_storage_declarations_independently_verified': False,
                'source_case_identities_supplied_by_frozen_external_ledger': True,
                'old_full_run_schema_emitted': False, **self._totals(self.cases), **AUTHORITY}
        except BaseException as error:
            self._fail(error)
            raise

    def finish(self):
        if self.finished:
            raise RuntimeError('Compact verifier closed; no retry or resume')
        result = self.receipt()
        try:
            self._write('receipt.json', result)
            self.finished = True
            self._verify_metadata()
            return result
        except BaseException as error:
            self._fail(error)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    verifier = CompactRunVerifier(args.root, json.loads(args.plan.read_bytes()))
    for ordinal in range(len(verifier.plan['cases'])):
        verifier.append(ordinal)
    result = verifier.finish()
    print(json.dumps({'status': result['status'], 'case_count': result['case_count'],
        'receipt_path': str(args.root / 'receipt.json'), **AUTHORITY}, sort_keys=True))


if __name__ == '__main__':
    main()
