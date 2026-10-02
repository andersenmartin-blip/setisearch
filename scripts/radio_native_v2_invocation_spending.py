#!/usr/bin/env python3
"""Bounded, fail-closed local spending before one engineering invocation.

Caller contract: authenticate the activation receipt independently, derive the
ledger from the pinned ORIGINAL repository root, and always call consume_once
before creating a workload scope. Every worker must authenticate the resulting
witness through its independently pinned admission-bundle digest before calling
verify_spend_witness. A digest-bearing witness is NOT a standalone signature or
secret capability; it is authenticated relative to that trusted outer argv.

O_EXCL serializes cooperating invocations. File and directory fsync complete
before a witness is returned. Partial records, failed writes, failed fsyncs and
workload failures leave the claim spent; this module offers no deletion/rearm
API. This trusts the local kernel/filesystem and a stable, private ledger root.
It cannot prevent a privileged/same-owner writer from deleting, rolling back,
replacing or copying the ledger, nor promise durability beyond filesystem fsync
semantics. Changing the caller's pinned repository root requires separate review.

No subprocess, Git, RNG, workload, source generation or telescope read occurs.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'radio-native-v2-control-invocation-spend-v1'
WITNESS_SCHEMA = 'radio-native-v2-control-invocation-spend-witness-v1'
RECEIPT_SCHEMA = 'radio-native-v2-control-single-activation-receipt-v2'
NAMESPACE = 'radio-native-v2-control-activation-transition-20261002b'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
MARKER = 'config/radio_native_v2_control_activation_20261002b.activate.json'
SPENT_MARKER = 'config/radio_native_v2_control_activation_20261002a.activate.json'
SPENT_ACTIVATION_COMMIT = 'ba1b6c918931a02a84cd23e0e14057bd9f700e40'
LEDGER_DIRECTORY = '.radio-native-v2-invocation-ledger'
MAX_RECORD_BYTES = 16384
MAX_PATH_BYTES = 4096
DISABLED = ('reservation_authorized', 'rng_authorized',
    'scientific_execution_authorized', 'native_execution_authorized',
    'restart_authorized', 'automatic_retry')
RECEIPT_FIELDS = frozenset(('schema', 'namespace', 'activation_commit',
    'activation_tree', 'activation_parent', 'activation_public_readback_verified',
    'marker_path', 'marker_blob', 'marker_sha256', 'plan_sha256',
    'complete_freeze_sha256', 'execution_preread_sha256', 'one_control_invocation',
    'control_scope', 'runtime_custody_manifest_sha256',
    'activation_only_runtime_complete', *DISABLED))
IDENTITY_FIELDS = ('device', 'inode', 'mode', 'nlink', 'uid', 'gid',
    'bytes', 'mtime_ns', 'ctime_ns')
WITNESS_FIELDS = frozenset(('schema', 'activation_identity_sha256',
    'activation_receipt_sha256', 'activation_commit', 'control_scope',
    'ledger_root', 'ledger_identity', 'record_name', 'record_sha256',
    'record_identity', 'durable_before_workload', 'one_invocation_spent'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _absolute(value):
    value = os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))
            or len(value.encode('utf-8')) > MAX_PATH_BYTES
            or len(value.split('/')) > 64):
        raise ValueError('Bounded canonical absolute invocation path required')
    return value


def ledger_root_for_repository(repository_root):
    """Pure path policy; caller must supply an independently pinned original root."""
    return _absolute(_absolute(repository_root) + '/' + LEDGER_DIRECTORY)


def _paths(execution_scope, ledger_root):
    scope = _absolute(execution_scope); ledger = _absolute(ledger_root)
    if scope == ledger or scope.startswith(ledger+'/') or ledger.startswith(scope+'/'):
        raise ValueError('Invocation ledger must be outside the per-invocation scope')
    return scope, ledger


def _sha(value, label):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact lowercase SHA256 required: '+label)
    return value


def _receipt(receipt, scope):
    if type(receipt) is dict and (receipt.get('marker_path') == SPENT_MARKER
            or receipt.get('activation_commit') == SPENT_ACTIVATION_COMMIT):
        raise ValueError('Historical failed activation marker/commit is permanently spent')
    if type(receipt) is not dict or set(receipt) != RECEIPT_FIELDS:
        raise ValueError('Exact invocation activation receipt structure required')
    if (receipt['schema'] != RECEIPT_SCHEMA or receipt['namespace'] != NAMESPACE
            or receipt['marker_path'] != MARKER
            or receipt['activation_public_readback_verified'] is not True
            or receipt['one_control_invocation'] is not True
            or receipt['activation_only_runtime_complete'] is not True):
        raise ValueError('Completed exact prospective one-invocation receipt required')
    if _absolute(receipt['control_scope']) != scope:
        raise ValueError('Invocation receipt control scope differs')
    for name in ('activation_commit', 'activation_tree', 'activation_parent', 'marker_blob'):
        if type(receipt[name]) is not str or not re.fullmatch('[0-9a-f]{40}', receipt[name]):
            raise ValueError('Exact lowercase Git object required: '+name)
    for name in ('marker_sha256', 'plan_sha256', 'complete_freeze_sha256',
            'execution_preread_sha256', 'runtime_custody_manifest_sha256'):
        _sha(receipt[name], name)
    if any(receipt[name] is not False for name in DISABLED):
        raise ValueError('Invocation receipt grants forbidden authority')
    # This lifetime key deliberately excludes execution scope and activation
    # commit. Another scope or edited/replayed receipt cannot rearm this marker.
    activation = {'namespace': NAMESPACE, 'repository': REPOSITORY,
        'branch': BRANCH, 'marker_path': MARKER}
    identity = _digest(activation)
    return identity, _digest(receipt), 'spent-'+identity+'.json'


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in _absolute(path)[1:].split('/'):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=fd)
            os.close(fd); fd = child
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
                or info.st_uid != os.geteuid()):
            raise ValueError('Pre-existing process-owned private 0700 invocation ledger required')
        return fd
    except BaseException:
        os.close(fd); raise


def _directory_identity(info):
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}


def _same_directory(fd, path, expected=None):
    current = _directory_identity(os.fstat(fd))
    again = _directory(path)
    try:
        if current != _directory_identity(os.fstat(again)) or (expected is not None and current != expected):
            raise ValueError('Invocation ledger directory identity changed')
    finally:
        os.close(again)
    return current


def _identity(info):
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def _regular(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid()
            or not 0 < info.st_size <= MAX_RECORD_BYTES):
        raise ValueError('Bounded private sole-link invocation spend record required')
    return _identity(info)


def _read_record(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = _regular(os.fstat(fd)); chunks = []; remaining = before['bytes']+1
        while remaining:
            raw = os.read(fd, min(4096, remaining))
            if not raw: break
            chunks.append(raw); remaining -= len(raw)
        raw = b''.join(chunks)
        after = _regular(os.fstat(fd))
        named = _regular(os.stat(name, dir_fd=directory, follow_symlinks=False))
        if before != after or after != named or len(raw) != before['bytes']:
            raise ValueError('Invocation spend record changed during descriptor read')
        value = json.loads(raw, object_pairs_hook=_unique)
        if type(value) is not dict or canonical(value)+b'\n' != raw:
            raise ValueError('Canonical complete invocation spend record required')
        return value, raw, after
    finally:
        os.close(fd)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('Duplicate invocation spend property refused')
        value[key] = item
    return value


def _record(receipt, scope, identity, receipt_digest):
    return {'schema': SCHEMA, 'state': 'SPENT_BEFORE_WORKLOAD',
        'activation_identity_sha256': identity,
        'activation_receipt_sha256': receipt_digest,
        'activation_commit': receipt['activation_commit'], 'control_scope': scope,
        'one_invocation_spent': True}


def consume_once(receipt, *, execution_scope, ledger_root, receipt_validator):
    """Claim once before workload; all post-O_EXCL failures retain the claim.

    receipt_validator is a trusted outer callback returning exactly True only
    after independent marker/preread/runtime admission. It is not called during
    worker witness reads. No workload callback is accepted or executed here.
    """
    scope, ledger = _paths(execution_scope, ledger_root)
    identity, receipt_digest, name = _receipt(receipt, scope)
    admitted_bytes = canonical(receipt)
    if not callable(receipt_validator) or receipt_validator(receipt) is not True:
        raise ValueError('Independent activation receipt admission required before spending')
    if canonical(receipt) != admitted_bytes:
        raise ValueError('Activation receipt changed during independent admission')
    record = _record(receipt, scope, identity, receipt_digest)
    raw = canonical(record)+b'\n'
    if len(raw) > MAX_RECORD_BYTES: raise ValueError('Bounded invocation spend record exceeded')
    directory = _directory(ledger); fd = None
    try:
        directory_identity = _same_directory(directory, ledger)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=directory)
        except FileExistsError as failure:
            # Never attempt to parse, repair, remove, or retry an existing claim.
            raise ValueError('Activation marker is already spent or has an incomplete claim') from failure
        # Persist even an empty claim early. A crash before this fsync cannot
        # have received a witness; filesystem failure still never grants one.
        os.fsync(fd); os.fsync(directory)
        position = 0
        while position < len(raw):
            written = os.write(fd, raw[position:])
            if written <= 0: raise ValueError('Incomplete invocation spend write')
            position += written
        os.fsync(fd); os.fsync(directory)
        file_identity = _regular(os.fstat(fd))
        readback, observed, observed_identity = _read_record(directory, name)
        if observed != raw or readback != record or observed_identity != file_identity:
            raise ValueError('Durable invocation spend record readback differs')
        _same_directory(directory, ledger, directory_identity)
        if (_regular(os.fstat(fd)) != file_identity
                or _regular(os.stat(name, dir_fd=directory, follow_symlinks=False)) != file_identity):
            raise ValueError('Durable invocation spend record changed after readback')
        return {'schema': WITNESS_SCHEMA,
            'activation_identity_sha256': identity,
            'activation_receipt_sha256': receipt_digest,
            'activation_commit': receipt['activation_commit'], 'control_scope': scope,
            'ledger_root': ledger, 'ledger_identity': directory_identity,
            'record_name': name, 'record_sha256': hashlib.sha256(raw).hexdigest(),
            'record_identity': file_identity, 'durable_before_workload': True,
            'one_invocation_spent': True}
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def verify_spend_witness(witness, receipt, *, execution_scope, ledger_root):
    """Read-only worker recheck AFTER independent admission-bundle authentication.

    This does not spend again and cannot authorize a new outer invocation. The
    trusted runner must always call consume_once for each attempted invocation.
    """
    scope, ledger = _paths(execution_scope, ledger_root)
    identity, receipt_digest, name = _receipt(receipt, scope)
    if type(witness) is not dict or set(witness) != WITNESS_FIELDS:
        raise ValueError('Exact invocation spend witness structure required')
    if (witness['schema'] != WITNESS_SCHEMA
            or witness['activation_identity_sha256'] != identity
            or witness['activation_receipt_sha256'] != receipt_digest
            or witness['activation_commit'] != receipt['activation_commit']
            or witness['control_scope'] != scope or witness['ledger_root'] != ledger
            or witness['record_name'] != name
            or witness['durable_before_workload'] is not True
            or witness['one_invocation_spent'] is not True):
        raise ValueError('Invocation spend witness binding differs')
    _sha(witness['record_sha256'], 'spend record')
    for value, fields in ((witness['ledger_identity'],
            ('device', 'inode', 'mode', 'uid', 'gid')),
            (witness['record_identity'], IDENTITY_FIELDS)):
        if (type(value) is not dict or set(value) != set(fields)
                or any(type(item) is not int or item < 0 for item in value.values())):
            raise ValueError('Exact nonnegative invocation spend identity required')
    directory = _directory(ledger)
    try:
        _same_directory(directory, ledger, witness['ledger_identity'])
        record, raw, file_identity = _read_record(directory, name)
        if (raw != canonical(_record(receipt, scope, identity, receipt_digest))+b'\n'
                or hashlib.sha256(raw).hexdigest() != witness['record_sha256']
                or file_identity != witness['record_identity']):
            raise ValueError('Persisted invocation spend witness record differs')
        _same_directory(directory, ledger, witness['ledger_identity'])
        return True
    finally:
        os.close(directory)
