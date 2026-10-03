#!/usr/bin/env python3
"""Fresh f current-lifetime metadata preclaim and once-only dispatch arbitration.

This component is wired into the still-blocked prospective control. Importing
it creates no marker or ledger and grants no activation or execution authority.

Caller contract: authenticate the activation receipt independently, derive the
ledger from the independently pinned CURRENT repository root. First consume_once
creates the metadata-only private preclaim. An externally authenticated create-only
public reference/readback binds that exact private witness before consume_dispatch_once
permits one dispatch. No missing private witness is reconstructed. Every worker must authenticate the resulting
witness through its independently pinned admission-bundle digest before calling
verify_spend_witness. A digest-bearing witness is NOT a standalone signature or
secret capability; it is authenticated relative to that trusted outer argv.

O_EXCL serializes cooperating invocations. File and directory fsync complete
before a witness is returned. Partial records, failed writes, failed fsyncs and
workload failures leave the claim spent; this module offers no deletion/rearm
API. This trusts the local kernel/filesystem and a stable, private ledger root.
It cannot prevent a privileged/same-owner writer from deleting, rolling back,
replacing or copying the ledger, nor promise durability beyond filesystem fsync
semantics. Losing this f lifetime's original private journal permanently blocks f; a public
copy cannot restore it. This lifetime never requires old a/b/c original journals.

No subprocess, Git, RNG, workload, source generation or telescope read occurs.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'radio-native-v3-control-invocation-spend-v1'
WITNESS_SCHEMA = 'radio-native-v3-control-invocation-spend-witness-v1'
STORAGE_SCHEMA = 'radio-native-v3-control-invocation-spend-storage-v1'
RECEIPT_SCHEMA = 'radio-native-v2-control-single-activation-receipt-v2'
NAMESPACE = 'radio-native-v3-control-activation-transition-20261003g'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
MARKER = 'config/radio_native_v3_control_activation_20261003g.activate.json'
# Exact historical identities, retained even if other receipt fields are edited.
# The b and c commits are pinned by their archived activation receipts.
SPENT_ACTIVATIONS = (('radio-native-v2-control-activation-transition-20261002a', 'config/radio_native_v2_control_activation_20261002a.activate.json', 'ba1b6c918931a02a84cd23e0e14057bd9f700e40'), ('radio-native-v2-control-activation-transition-20261002b', 'config/radio_native_v2_control_activation_20261002b.activate.json', '1bc31d49b2552de10c3fbabb7bc106618a44a241'), ('radio-native-v2-control-activation-transition-20261002c', 'config/radio_native_v2_control_activation_20261002c.activate.json', 'f514d782a0f807223e4bc47cb0b330b4b46a198f'), ('radio-native-v3-control-activation-transition-20261003e', 'config/radio_native_v3_control_activation_20261003e.activate.json', '2cde096565519be82d8effe5d9cc878d6122ab45'))
LEDGER_DIRECTORY = '.radio-native-v3-invocation-ledger-20261003g'
MAX_RECORD_BYTES = 16384
# A one-file private ledger needs no directory growth beyond this bounded
# metadata window. This is a scan bound, not an additional workload budget.
MAX_LEDGER_DIRECTORY_BYTES = 16384
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

SPENDING_BUNDLE_SCHEMA='radio-native-v3-public-private-spending-bundle-v1'
SPENDING_BUNDLE_FIELDS=frozenset(('schema','local_witness','public_claim','public_claim_sha256','dispatch_witness'))
DISPATCH_SCHEMA='radio-native-v3-dispatch-spend-v1'
DISPATCH_WITNESS_SCHEMA='radio-native-v3-dispatch-spend-witness-v1'
DISPATCH_WITNESS_FIELDS=frozenset(('schema','dispatch_name','dispatch_sha256','dispatch_identity','local_witness_sha256','public_claim_sha256','durable_before_dispatch','one_dispatch_spent'))


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
    """Pure path policy; caller must supply an independently pinned current root."""
    return _absolute(_absolute(repository_root) + '/' + LEDGER_DIRECTORY)


def _paths(execution_scope, ledger_root, repository_root):
    # The trusted caller supplies the pinned CURRENT root independently of the
    # scope and any witness. Never infer it by walking upward from either path.
    repository = _absolute(repository_root)
    scope = _absolute(execution_scope); ledger = _absolute(ledger_root)
    if ledger != ledger_root_for_repository(repository):
        raise ValueError('Invocation ledger must equal the pinned current repository ledger')
    if scope == ledger or scope.startswith(ledger+'/') or ledger.startswith(scope+'/'):
        raise ValueError('Invocation ledger must be outside the per-invocation scope')
    return scope, ledger


def _sha(value, label):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact lowercase SHA256 required: '+label)
    return value


def _receipt(receipt, scope):
    if type(receipt) is dict and any(
            receipt.get('namespace') == namespace
            or receipt.get('marker_path') == marker
            or receipt.get('activation_commit') == commit
            for namespace, marker, commit in SPENT_ACTIVATIONS):
        raise ValueError('Historical failed activation namespace/marker/commit is permanently spent')
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


def _unclaimed_ledger(directory, name):
    # Check the claim name first, without opening or following any entry. An
    # existing empty, malformed or special claim stays permanently spent even
    # when unexpected entries also exist. O_EXCL still arbitrates later races.
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise ValueError('Activation marker is already spent or has an incomplete claim')
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name == name:
                raise ValueError('Activation marker is already spent or has an incomplete claim')
            raise ValueError('Empty invocation ledger inventory required before spending')


def consume_once(receipt, *, execution_scope, ledger_root, repository_root, receipt_validator):
    """Claim once before workload; all post-O_EXCL failures retain the claim.

    receipt_validator is a trusted outer callback returning exactly True only
    after independent marker/preread/runtime admission. It is not called during
    worker witness reads. No workload callback is accepted or executed here.
    """
    scope, ledger = _paths(execution_scope, ledger_root, repository_root)
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
        _unclaimed_ledger(directory, name)
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
        _ledger_names(directory, name)
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


def verify_spend_witness(witness, receipt, *, execution_scope, ledger_root, repository_root):
    if type(witness) is dict and witness.get('schema')==SPENDING_BUNDLE_SCHEMA:
        return verify_dispatch_witness(witness,receipt,execution_scope=execution_scope,ledger_root=ledger_root,repository_root=repository_root)
    """Read-only worker recheck AFTER independent admission-bundle authentication.

    This does not spend again and cannot authorize a new outer invocation. The
    trusted runner must always call consume_once for each attempted invocation.
    """
    scope, ledger = _paths(execution_scope, ledger_root, repository_root)
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
        _ledger_names(directory, name)
        return True
    finally:
        os.close(directory)


def _storage_identity(info):
    value = {**_identity(info), 'allocated_bytes': info.st_blocks*512}
    if any(type(item) is not int or item < 0 for item in value.values()):
        raise ValueError('Nonnegative observed ledger storage metadata required')
    return value


def _ledger_names(directory, expected_name):
    dispatch='dispatch-'+expected_name[len('spent-'):]
    names=[]
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name not in {expected_name,dispatch} or len(names)>=2:
                raise ValueError('Exact claim and optional dispatch-marker ledger inventory required')
            names.append(entry.name)
    if expected_name not in names or len(set(names))!=len(names):
        raise ValueError('Original current-lifetime claim remains mandatory')
    return sorted(names)


def _observe_local_spend_storage(witness, receipt, *, execution_scope, ledger_root, repository_root):
    """Read-only current ledger storage AFTER independent bundle authentication.

    Recheck the witness, receipt and scope; then observe exactly the ledger
    directory plus its sole spend record through held stable descriptors. Count
    both directory and file logical bytes and allocated blocks. Any extra entry
    (including dotfiles), subdirectory, special file, alias, mutation or missing
    record fails closed. Rows use absolute paths so the original resource
    allocator can reject cross-scope inode aliases and charge this storage once
    as shared external overhead, within its unchanged whole/per-case budgets.

    This observation is distinct from the immutable spend witness: directory
    size, allocated blocks and timestamps describe NOW, not the earlier claim.
    It grants no invocation authority, writes nothing and promises no future
    immutability or protection from local filesystem rollback.
    """
    scope, ledger = _paths(execution_scope, ledger_root, repository_root)
    if verify_spend_witness(witness, receipt, execution_scope=scope,
            ledger_root=ledger, repository_root=repository_root) is not True:
        raise ValueError('Authenticated invocation spend witness required for storage observation')
    identity, receipt_digest, name = _receipt(receipt, scope)
    directory = _directory(ledger); fd = None
    try:
        _same_directory(directory, ledger, witness['ledger_identity'])
        directory_before = _storage_identity(os.fstat(directory))
        if (directory_before['nlink'] != 2
                or directory_before['bytes'] > MAX_LEDGER_DIRECTORY_BYTES):
            raise ValueError('Bounded leaf invocation ledger directory required')
        _ledger_names(directory, name)
        named_before = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _regular(named_before) != witness['record_identity']:
            raise ValueError('Spend record identity differs before storage observation')
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        file_before = _storage_identity(os.fstat(fd))
        if file_before != _storage_identity(named_before):
            raise ValueError('Spend record storage changed during descriptor open')
        _, raw, observed_identity = _read_record(directory, name)
        if (raw != canonical(_record(receipt, scope, identity, receipt_digest))+b'\n'
                or hashlib.sha256(raw).hexdigest() != witness['record_sha256']
                or observed_identity != witness['record_identity']):
            raise ValueError('Spend record binding differs during storage observation')
        _ledger_names(directory, name)
        _same_directory(directory, ledger, witness['ledger_identity'])
        if directory_before != _storage_identity(os.fstat(directory)):
            raise ValueError('Invocation ledger directory storage changed during observation')
        if (file_before != _storage_identity(os.fstat(fd))
                or file_before != _storage_identity(os.stat(name, dir_fd=directory,
                    follow_symlinks=False))):
            raise ValueError('Invocation spend record storage changed during observation')
        rows = [{'path': ledger, 'kind': 'directory', **directory_before},
            {'path': ledger+'/'+name, 'kind': 'file', **file_before}]
        return {'schema': STORAGE_SCHEMA, 'ledger_root': ledger, 'control_scope': scope,
            'activation_receipt_sha256': receipt_digest,
            'invocation_spending_sha256': _digest(witness), 'rows': rows,
            'logical_bytes': sum(row['bytes'] for row in rows),
            'allocated_bytes': sum(row['allocated_bytes'] for row in rows),
            'entry_count': len(rows), 'witness_bindings_verified': True,
            'ledger_inventory_exact': True, 'current_observation_stable': True}
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def validate_spending_bundle(value, *, require_dispatch=True):
    if type(value) is not dict or set(value)!=SPENDING_BUNDLE_FIELDS or value.get('schema')!=SPENDING_BUNDLE_SCHEMA:
        raise ValueError('BLOCKED_PUBLIC_PERMANENT_SPEND: exact independent public/private spending envelope required')
    if type(value['local_witness']) is not dict or set(value['local_witness'])!=WITNESS_FIELDS:
        raise ValueError('Original current-lifetime local claim witness required; no reconstruction')
    if type(value['public_claim']) is not dict:
        raise ValueError('Independent create-only public permanent-spend readback required')
    _sha(value['public_claim_sha256'],'independent public claim')
    if hashlib.sha256(canonical(value['public_claim'])).hexdigest()!=value['public_claim_sha256']:
        raise ValueError('Public claim readback envelope digest differs')
    dispatch=value['dispatch_witness']
    if require_dispatch:
        if type(dispatch) is not dict or set(dispatch)!=DISPATCH_WITNESS_FIELDS:
            raise ValueError('Live once-only dispatch witness required')
    elif dispatch is not None:
        raise ValueError('Existing or incomplete dispatch cannot be adopted for another invocation')
    return json.loads(canonical(value))


def _dispatch_record(bundle, receipt, scope):
    identity,receipt_sha,name=_receipt(receipt,scope)
    return {'schema':DISPATCH_SCHEMA,'state':'DISPATCH_SPENT_BEFORE_WORKLOAD',
        'activation_identity_sha256':identity,'activation_receipt_sha256':receipt_sha,
        'control_scope':scope,'local_witness_sha256':_digest(bundle['local_witness']),
        'public_claim_sha256':bundle['public_claim_sha256'],'one_dispatch_spent':True}


def consume_dispatch_once(bundle, receipt, *, execution_scope, ledger_root, repository_root, public_claim_validator):
    """Adopt a public preclaimed lifetime once; never creates missing history.

    The trusted outer caller validates the independently pinned create-only
    publication evidence before this metadata-only O_EXCL transition. A public
    record cannot replace the exact existing private witness. No workload or
    generation runs here. A partial dispatch marker remains spent.
    """
    value=validate_spending_bundle(bundle,require_dispatch=False)
    admitted=canonical(value)
    if not callable(public_claim_validator) or public_claim_validator(value) is not True:
        raise ValueError('Independent public claim admission required before dispatch spending')
    if canonical(value)!=admitted: raise ValueError('Public spending envelope changed during admission')
    scope,ledger=_paths(execution_scope,ledger_root,repository_root)
    verify_spend_witness(value['local_witness'],receipt,execution_scope=scope,ledger_root=ledger,repository_root=repository_root)
    _,_,claim_name=_receipt(receipt,scope);name='dispatch-'+claim_name[len('spent-'):]
    record=_dispatch_record(value,receipt,scope);raw=canonical(record)+b'\n'
    directory=_directory(ledger);fd=None
    try:
        _same_directory(directory,ledger,value['local_witness']['ledger_identity'])
        if _ledger_names(directory,claim_name)!=[claim_name]:
            raise ValueError('f dispatch permanently spent; no replay/rearm')
        try:fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        except FileExistsError as failure:raise ValueError('f dispatch permanently spent or incomplete') from failure
        os.fsync(fd);os.fsync(directory)
        position=0
        while position<len(raw):
            written=os.write(fd,raw[position:])
            if written<=0:raise ValueError('Incomplete durable dispatch write')
            position+=written
        os.fsync(fd);os.fsync(directory)
        identity=_regular(os.fstat(fd));observed,held,observed_identity=_read_record(directory,name)
        if held!=raw or observed!=record or observed_identity!=identity:
            raise ValueError('Durable dispatch record readback differs')
        value['dispatch_witness']={'schema':DISPATCH_WITNESS_SCHEMA,'dispatch_name':name,
            'dispatch_sha256':hashlib.sha256(raw).hexdigest(),'dispatch_identity':identity,
            'local_witness_sha256':_digest(value['local_witness']),'public_claim_sha256':value['public_claim_sha256'],
            'durable_before_dispatch':True,'one_dispatch_spent':True}
        verify_dispatch_witness(value,receipt,execution_scope=scope,ledger_root=ledger,repository_root=repository_root)
        return value
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)


def verify_dispatch_witness(bundle, receipt, *, execution_scope, ledger_root, repository_root):
    value=validate_spending_bundle(bundle,require_dispatch=True);witness=value['dispatch_witness']
    scope,ledger=_paths(execution_scope,ledger_root,repository_root)
    verify_spend_witness(value['local_witness'],receipt,execution_scope=scope,ledger_root=ledger,repository_root=repository_root)
    _,_,claim_name=_receipt(receipt,scope);name='dispatch-'+claim_name[len('spent-'):]
    wanted=_dispatch_record(value,receipt,scope);raw=canonical(wanted)+b'\n'
    if (witness['schema']!=DISPATCH_WITNESS_SCHEMA or witness['dispatch_name']!=name
            or witness['dispatch_sha256']!=hashlib.sha256(raw).hexdigest()
            or witness['local_witness_sha256']!=_digest(value['local_witness'])
            or witness['public_claim_sha256']!=value['public_claim_sha256']
            or witness['durable_before_dispatch'] is not True or witness['one_dispatch_spent'] is not True):
        raise ValueError('Exact original current-lifetime dispatch witness differs')
    directory=_directory(ledger)
    try:
        if _ledger_names(directory,claim_name)!=sorted([claim_name,name]):
            raise ValueError('Both original claim and dispatch marker required')
        record,observed,identity=_read_record(directory,name)
        if observed!=raw or record!=wanted or identity!=witness['dispatch_identity']:
            raise ValueError('Live dispatch identity differs; replay/restoration refused')
        _same_directory(directory,ledger,value['local_witness']['ledger_identity'])
        return True
    finally:os.close(directory)


def observe_spend_storage(witness, receipt, *, execution_scope, ledger_root, repository_root):
    value=validate_spending_bundle(witness,require_dispatch=True)
    args={'execution_scope':execution_scope,'ledger_root':ledger_root,'repository_root':repository_root}
    directory=_directory(ledger_root);fd=None
    try:
        before=_storage_identity(os.fstat(directory))
        verify_dispatch_witness(value,receipt,**args)
        current=_observe_local_spend_storage(value['local_witness'],receipt,**args)
        if {key:current['rows'][0][key] for key in before}!=before:
            raise ValueError('Current ledger metadata changed before full claim/dispatch observation')
        name=value['dispatch_witness']['dispatch_name']
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        metadata=_storage_identity(os.fstat(fd))
        _,raw,identity=_read_record(directory,name)
        if identity!=value['dispatch_witness']['dispatch_identity']:
            raise ValueError('Dispatch marker changed during storage observation')
        if metadata!=_storage_identity(os.fstat(fd)) or metadata!=_storage_identity(os.stat(name,dir_fd=directory,follow_symlinks=False)):
            raise ValueError('Dispatch storage metadata changed during held observation')
        current['rows'].append({'path':ledger_root+'/'+name,'kind':'file',**metadata})
        current['rows'].sort(key=lambda row:row['path'])
        current['logical_bytes']=sum(row['bytes'] for row in current['rows'])
        current['allocated_bytes']=sum(row['allocated_bytes'] for row in current['rows'])
        current['entry_count']=len(current['rows'])
        current['invocation_spending_sha256']=_digest(value)
        verify_dispatch_witness(value,receipt,**args)
        if before!=_storage_identity(os.fstat(directory)):
            raise ValueError('Ledger directory changed during complete claim/dispatch observation')
        _same_directory(directory,ledger_root,value['local_witness']['ledger_identity'])
        return current
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)
