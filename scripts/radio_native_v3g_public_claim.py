#!/usr/bin/env python3
"""Read-only v3 evidence for a public claim spent before engineering dispatch.

This verifier creates no claim, marker, journal, scope or network request. Its
caller MUST obtain the public readback independently, verify the commit, tree,
parent and blob at the public repository, and pass the independently pinned
SHA256 of that readback envelope as ``expected_sha256``. A digest stored inside
an envelope is not an independent pin. This module checks the evidence's shape
and bindings; it does not assert that a network readback occurred.

The committed record is separate from its public-readback envelope so neither
the record's Git blob nor its commit has a circular self-reference. The record
bytes are canonical JSON plus one newline. The envelope digest covers canonical
JSON WITHOUT a newline, consistently with plan/freeze/preread object digests.

A successful receipt proves only that the trusted outer readback describes the
fresh f engineering claim as permanently SPENT_BEFORE_DISPATCH. It grants no
dispatch, retry, scientific execution, source acquisition or telescope access.
Repeated read-only verification cannot rearm a claim. Actual publication,
durability, dispatch admission and local once-only arbitration belong to the
outer integration. Historical a/b/c activations stay spent; prospective d is
also excluded from this successor. No original historical custody is asserted.
"""
import hashlib
import json
import os
import re

SCHEMA = 'radio-native-v3-public-spent-claim-v1'
RECORD_SCHEMA = 'radio-native-v3-public-spent-record-v1'
RECEIPT_SCHEMA = 'radio-native-v3-public-spent-claim-receipt-v1'
NAMESPACE = 'radio-native-v3-control-activation-transition-20261003g'
MARKER = 'config/radio_native_v3_control_activation_20261003g.activate.json'
REGISTRY_PATH = 'config/radio_native_v3_control_spent_20261003g.claim.json'
CLAIM_REF = 'refs/heads/radio-native-v3-spent-20261003g'
LEDGER_DIRECTORY = '.radio-native-v3-invocation-ledger-20261003g'
WITNESS_SCHEMA = 'radio-native-v3-control-invocation-spend-witness-v1'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
SPENT_ACTIVATIONS = (('radio-native-v2-control-activation-transition-20261002a', 'config/radio_native_v2_control_activation_20261002a.activate.json', 'ba1b6c918931a02a84cd23e0e14057bd9f700e40'), ('radio-native-v2-control-activation-transition-20261002b', 'config/radio_native_v2_control_activation_20261002b.activate.json', '1bc31d49b2552de10c3fbabb7bc106618a44a241'), ('radio-native-v2-control-activation-transition-20261002c', 'config/radio_native_v2_control_activation_20261002c.activate.json', 'f514d782a0f807223e4bc47cb0b330b4b46a198f'), ('radio-native-v3-control-activation-transition-20261003e', 'config/radio_native_v3_control_activation_20261003e.activate.json', '2cde096565519be82d8effe5d9cc878d6122ab45'))
REJECTED_PROSPECTIVE_IDENTIFIERS = (
    ('radio-native-v2-control-activation-transition-20261003d',
     'config/radio_native_v2_control_activation_20261003d.activate.json'),)
DISABLED = ('reservation_authorized', 'rng_authorized',
    'scientific_execution_authorized', 'native_execution_authorized',
    'restart_authorized', 'automatic_retry', 'activation_authorized',
    'execution_authorized', 'telescope_read_authorized',
    'source_acquisition_authorized')
CLAIM_FIELDS = frozenset(('schema', 'record', 'registry_pin',
    'public_readback_verified'))
REGISTRY_PIN_FIELDS = frozenset(('repository', 'branch', 'path', 'commit',
    'tree', 'parent', 'blob', 'sha256', 'public_readback_verified',
    'create_only_ref', 'ref_create_only_verified', 'ref_readback_commit'))
RECORD_FIELDS = frozenset(('schema', 'namespace', 'repository', 'branch',
    'state', 'marker_path', 'activation_commit', 'activation_tree',
    'activation_parent', 'marker_blob', 'marker_sha256', 'repository_root',
    'control_scope', 'plan_sha256', 'complete_freeze_sha256',
    'execution_preread_sha256', 'historical_spent_activations',
    'rejected_prospective_identifiers', 'permanent_spent',
    'spent_before_dispatch', 'one_control_invocation',
    'local_invocation_spending_sha256', 'local_ledger_identity',
    'local_record_identity', *DISABLED))
WITNESS_FIELDS = frozenset(('schema', 'activation_identity_sha256',
    'activation_receipt_sha256', 'activation_commit', 'control_scope',
    'ledger_root', 'ledger_identity', 'record_name', 'record_sha256',
    'record_identity', 'durable_before_workload', 'one_invocation_spent'))
LEDGER_IDENTITY_FIELDS = frozenset(('device', 'inode', 'mode', 'uid', 'gid'))
RECORD_IDENTITY_FIELDS = frozenset(('device', 'inode', 'mode', 'nlink', 'uid',
    'gid', 'bytes', 'mtime_ns', 'ctime_ns'))
MAX_CLAIM_BYTES = 32768
MAX_PATH_BYTES = 4096


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')


def _json(value, label):
    """Reject subclass hooks, non-JSON keys/values and cycles before hashing."""
    seen = set()

    def visit(item, depth):
        if depth > 128:
            raise ValueError('Bounded plain JSON required: ' + label)
        if type(item) in (str, int, float, bool, type(None)):
            return
        if type(item) not in (dict, list):
            raise ValueError('Plain JSON values required: ' + label)
        identity = id(item)
        if identity in seen:
            raise ValueError('Acyclic plain JSON required: ' + label)
        seen.add(identity)
        try:
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError('Plain JSON string keys required: ' + label)
                items = item.values()
            else:
                items = item
            for child in items:
                visit(child, depth + 1)
        finally:
            seen.remove(identity)

    visit(value, 0)
    try:
        return canonical(value)
    except (TypeError, ValueError, OverflowError, UnicodeError) as failure:
        raise ValueError('Canonical finite JSON required: ' + label) from failure


def _sha(value, label):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Exact lowercase SHA256 required: ' + label)
    return value


def _git(value, label):
    if (type(value) is not str or re.fullmatch('[0-9a-f]{40}', value) is None
            or value == '0' * 40):
        raise ValueError('Exact non-null lowercase Git object required: ' + label)
    return value


def _absolute(value):
    try:
        value = os.fspath(value)
    except TypeError as failure:
        raise ValueError('Bounded canonical absolute current path required') from failure
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value[1:].split('/'))
            or len(value.encode('utf-8')) > MAX_PATH_BYTES
            or len(value.split('/')) > 64):
        raise ValueError('Bounded canonical absolute current path required')
    return value


def _historical_identity(value):
    if type(value) is not dict:
        return
    if any(value.get('namespace') == namespace
            or value.get('marker_path') == marker
            or value.get('activation_commit') == commit
            for namespace, marker, commit in SPENT_ACTIVATIONS):
        raise ValueError('Historical namespace/marker/commit is permanently spent')
    if any(value.get('namespace') == namespace
            or value.get('marker_path') == marker
            for namespace, marker in REJECTED_PROSPECTIVE_IDENTIFIERS):
        raise ValueError('Prospective d identifiers are excluded from the fresh f lifetime')


def verify_public_claim(claim, *, expected_sha256, plan, complete_freeze,
        execution_preread, execution_scope, repository_root,
        invocation_spending=None):
    """Validate only an independently pinned, already-public spent readback.

    The returned receipt is detached from all caller-owned objects. Public
    object existence and independence of the pin remain trusted outer duties.
    Neither a returned receipt nor its hash is an execution capability.
    """
    pin_digest = _sha(expected_sha256, 'independent public claim readback')
    if type(claim) is not dict or set(claim) != CLAIM_FIELDS:
        raise ValueError('Exact public spent claim envelope required')
    admitted_bytes = _json(claim, 'public claim')
    if len(admitted_bytes) > MAX_CLAIM_BYTES:
        raise ValueError('Bounded public spent claim required')
    if hashlib.sha256(admitted_bytes).hexdigest() != pin_digest:
        raise ValueError('Independent public claim readback SHA256 differs')
    if (claim['schema'] != SCHEMA
            or claim['public_readback_verified'] is not True):
        raise ValueError('Verified public spent claim readback required')
    record = claim['record']
    _historical_identity(record)
    if type(record) is not dict or set(record) != RECORD_FIELDS:
        raise ValueError('Exact public spent record structure required')
    if (record['schema'] != RECORD_SCHEMA or record['namespace'] != NAMESPACE
            or record['repository'] != REPOSITORY or record['branch'] != BRANCH
            or record['state'] != 'SPENT_BEFORE_DISPATCH'
            or record['marker_path'] != MARKER
            or record['permanent_spent'] is not True
            or record['spent_before_dispatch'] is not True
            or record['one_control_invocation'] is not True):
        raise ValueError('Fresh exact permanently spent e engineering record required')
    if (record['historical_spent_activations'] != [list(row) for row in SPENT_ACTIVATIONS]
            or record['rejected_prospective_identifiers'] !=
                [list(row) for row in REJECTED_PROSPECTIVE_IDENTIFIERS]):
        raise ValueError('Exact immutable historical tombstones and d exclusion required')
    if any(record[name] is not False for name in DISABLED):
        raise ValueError('Public claim grants forbidden authority')
    root = _absolute(repository_root)
    scope = _absolute(execution_scope)
    if (_absolute(record['repository_root']) != root
            or _absolute(record['control_scope']) != scope or root == scope):
        raise ValueError('Public claim current repository root/control scope differs')
    for name in ('activation_commit', 'activation_tree', 'activation_parent', 'marker_blob'):
        _git(record[name], name)
    if record['activation_commit'] == record['activation_parent']:
        raise ValueError('Activation commit cannot be its own parent')
    _sha(record['marker_sha256'], 'marker')
    documents = ((plan, 'plan_sha256'),
        (complete_freeze, 'complete_freeze_sha256'),
        (execution_preread, 'execution_preread_sha256'))
    document_bytes = []
    for value, key in documents:
        if type(value) is not dict:
            raise ValueError('Exact independently supplied object required: ' + key)
        raw = _json(value, key)
        document_bytes.append(raw)
        if _sha(record[key], key) != hashlib.sha256(raw).hexdigest():
            raise ValueError('Public claim frozen input binding differs: ' + key)
    if (type(invocation_spending) is not dict
            or set(invocation_spending) != WITNESS_FIELDS):
        raise ValueError('Exact independently supplied local invocation spend witness required')
    witness_bytes = _json(invocation_spending, 'local invocation spend witness')
    if (invocation_spending['schema'] != WITNESS_SCHEMA
            or invocation_spending['activation_commit'] != record['activation_commit']
            or invocation_spending['control_scope'] != scope
            or _absolute(invocation_spending['ledger_root']) != root + '/' + LEDGER_DIRECTORY
            or invocation_spending['durable_before_workload'] is not True
            or invocation_spending['one_invocation_spent'] is not True):
        raise ValueError('Local invocation spend witness current-lifetime binding differs')
    for name in ('activation_identity_sha256', 'activation_receipt_sha256', 'record_sha256'):
        _sha(invocation_spending[name], 'local ' + name)
    activation_identity = hashlib.sha256(canonical({'namespace': NAMESPACE,
        'repository': REPOSITORY, 'branch': BRANCH, 'marker_path': MARKER})).hexdigest()
    if invocation_spending['activation_identity_sha256'] != activation_identity:
        raise ValueError('Local invocation witness fresh f activation identity differs')
    if invocation_spending['record_name'] != 'spent-' + invocation_spending['activation_identity_sha256'] + '.json':
        raise ValueError('Local invocation spend record name differs')
    for name, fields in (('ledger_identity', LEDGER_IDENTITY_FIELDS),
            ('record_identity', RECORD_IDENTITY_FIELDS)):
        identity = invocation_spending[name]
        public_identity = record['local_' + name]
        if (type(identity) is not dict or set(identity) != fields
                or any(type(value) is not int or value < 0 for value in identity.values())
                or type(public_identity) is not dict or set(public_identity) != fields
                or any(type(value) is not int or value < 0 for value in public_identity.values())
                or public_identity != identity):
            raise ValueError('Public claim exact original current-lifetime local identity differs')
    if (invocation_spending['ledger_identity']['mode'] != 0o700
            or invocation_spending['record_identity']['mode'] != 0o600
            or invocation_spending['record_identity']['nlink'] != 1
            or not 0 < invocation_spending['record_identity']['bytes'] <= 16384):
        raise ValueError('Bounded private local ledger/record identity required')
    if _sha(record['local_invocation_spending_sha256'], 'local invocation witness') != hashlib.sha256(witness_bytes).hexdigest():
        raise ValueError('Public claim original current-lifetime local witness digest differs')
    public_pin = claim['registry_pin']
    if type(public_pin) is not dict or set(public_pin) != REGISTRY_PIN_FIELDS:
        raise ValueError('Exact independently verified public registry pin required')
    if (public_pin['repository'] != REPOSITORY or public_pin['branch'] != BRANCH
            or public_pin['path'] != REGISTRY_PATH
            or public_pin['public_readback_verified'] is not True
            or public_pin['create_only_ref'] != CLAIM_REF
            or public_pin['ref_create_only_verified'] is not True
            or public_pin['ref_readback_commit'] != public_pin['commit']):
        raise ValueError('Exact verified public registry location required')
    for name in ('commit', 'tree', 'parent', 'blob'):
        _git(public_pin[name], 'public ' + name)
    if (public_pin['commit'] == public_pin['parent']
            or public_pin['commit'] == record['activation_commit']):
        raise ValueError('Public claim requires a distinct commit after activation')
    if public_pin['commit'] in {row[2] for row in SPENT_ACTIVATIONS}:
        raise ValueError('Historical activation cannot publish a fresh f claim')
    public_bytes = canonical(record) + b'\n'
    record_digest = hashlib.sha256(public_bytes).hexdigest()
    blob_digest = hashlib.sha1(b'blob ' + str(len(public_bytes)).encode('ascii')
        + b'\x00' + public_bytes).hexdigest()
    if (_sha(public_pin['sha256'], 'public record') != record_digest
            or public_pin['blob'] != blob_digest):
        raise ValueError('Public registry blob/SHA256 does not bind the exact spent record')
    if (_json(claim, 'public claim') != admitted_bytes
            or _json(invocation_spending, 'local invocation spend witness') != witness_bytes
            or any(_json(value, key) != raw
                for (value, key), raw in zip(documents, document_bytes))):
        raise ValueError('Public claim or frozen inputs changed during verification')
    # Parsing the already admitted bytes detaches nested arrays and the pin.
    snapshot = json.loads(admitted_bytes)
    record = snapshot['record']
    return {'schema': RECEIPT_SCHEMA, 'namespace': NAMESPACE,
        'marker_path': MARKER, 'activation_commit': record['activation_commit'],
        'activation_tree': record['activation_tree'],
        'activation_parent': record['activation_parent'],
        'marker_blob': record['marker_blob'], 'marker_sha256': record['marker_sha256'],
        'repository_root': root, 'control_scope': scope,
        'plan_sha256': record['plan_sha256'],
        'complete_freeze_sha256': record['complete_freeze_sha256'],
        'execution_preread_sha256': record['execution_preread_sha256'],
        'local_invocation_spending_sha256': record['local_invocation_spending_sha256'],
        'local_ledger_identity': snapshot['record']['local_ledger_identity'],
        'local_record_identity': snapshot['record']['local_record_identity'],
        'public_claim_sha256': pin_digest, 'public_record_sha256': record_digest,
        'registry_pin': snapshot['registry_pin'],
        'historical_spent_activations': snapshot['record']['historical_spent_activations'],
        'rejected_prospective_identifiers': snapshot['record']['rejected_prospective_identifiers'],
        'public_claim_verified': True, 'permanent_spent': True,
        'spent_before_dispatch': True, 'one_control_invocation': True,
        **{name: False for name in DISABLED}}
