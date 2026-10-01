#!/usr/bin/env python3
"""One fixed Actions REST publication control; zero subprocesses or science.

Every attempted HTTP application body is charged and retained. TLS/HTTP wire
framing and secret header values are excluded explicitly. Administrative
evidence publication is a separate, unmeasured invocation, never authority.
"""
import argparse
import base64
import gzip
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import resource
import ssl
import stat
import sys
import time

SCHEMA = 'radio-native-v2-actions-publisher-control-v1'
NAMESPACE = 'radio-native-v2-actions-control-20261001a'
REPOSITORY = 'andersenmartin-blip/setisearch'
REPOSITORY_NODE_ID = 'R_kgDOT558WQ'
BRANCH = 'm43-support-qualification'
PREFIX = 'results_radio_native_v2_actions_control_20261001a'
SOURCE_BYTES = 26 * 1024**2
PATTERN = b'SETI_ENGINEERING_ONLY_NO_RNG_OR_TELESCOPE_DATA_20261001A_000000\n'
SOURCE_SHA256 = '32b0f33f276e346c5e73c38c6edd55a2bba651b092cd82bde2f4c50a435409c0'
SOURCE_BLOB = 'cd3d4e84a10043cd1cf5f61aca3377d8ae6041f2'
CAPS = {'operations': 64, 'prospective_http_operations': 20, 'request_bytes': 48*1024**2,
    'reply_bytes': 64*1024**2, 'rss_per_process_bytes': 512*1024**2, 'seconds': 600,
    'host_receipt_bytes': 192*1024**2, 'spool_bytes': 40*1024**2,
    'whole_run_host_receipt_bytes': 1536*1024**2}
DISABLED = {'reservation_authorized': False, 'rng_authorized': False, 'execution_authorized': False,
    'scientific_execution_authorized': False, 'restart_authorized': False,
    'transport_integration_qualified': False}
API = '/repos/' + REPOSITORY
SOURCE_RECIPE = {'bytes': SOURCE_BYTES, 'pattern': PATTERN.decode(), 'repetitions': SOURCE_BYTES//len(PATTERN),
    'sha256': SOURCE_SHA256, 'git_blob_sha1': SOURCE_BLOB}
GRAPHQL_QUERY = 'mutation($input:UpdateRefsInput!){updateRefs(input:$input){clientMutationId}}'
MANIFEST = 'config/radio_native_v2_actions_control_20261001a.manifest.json'
MARKER = 'config/radio_native_v2_actions_control_20261001a.activate.json'
REQUIRED_FILES = frozenset(('.github/workflows/radio_native_v2_actions_control_20261001a.yml',
    'scripts/radio_native_v2_actions_activation_gate.py', 'scripts/radio_native_v2_actions_publisher_control.py',
    'scripts/radio_native_v2_actions_supervisor.py', 'config/radio_native_v2_actions_control_20261001a.protocol.json'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha40(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('Full immutable Git object name required')
    return value


def blob_sha(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def file_digest(path):
    size, sha = 0, hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = stream.fileno()
        initial = os.fstat(before)
        if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
            raise ValueError('Regular sole-link exact body file required')
        while block := stream.read(65536):
            size += len(block)
            sha.update(block)
        final = os.fstat(before)
        current = os.stat(path, follow_symlinks=False)
        if identity(initial) != identity(final) or identity(final) != identity(current) or size != initial.st_size:
            raise ValueError('Exact body file identity changed while hashing')
    return size, sha.hexdigest()


def identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns)


def validate_graphql(value):
    if not isinstance(value, dict) or set(value) != {'query', 'variables'} or value['query'] != GRAPHQL_QUERY:
        raise ValueError('Only the fixed atomic ref mutation is permitted')
    variables = value['variables']
    if not isinstance(variables, dict) or set(variables) != {'input'}:
        raise ValueError('Exact fixed GraphQL variables required')
    item = variables['input']
    if (not isinstance(item, dict) or set(item) != {'repositoryId', 'refUpdates', 'clientMutationId'}
            or item['repositoryId'] != REPOSITORY_NODE_ID or item['clientMutationId'] != NAMESPACE
            or not isinstance(item['refUpdates'], list) or len(item['refUpdates']) != 1):
        raise ValueError('Only one atomic update of the pinned repository/ref is permitted')
    ref = item['refUpdates'][0]
    if (not isinstance(ref, dict) or set(ref) != {'name', 'beforeOid', 'afterOid', 'force'}
            or ref['name'] != 'refs/heads/'+BRANCH or ref['force'] is not False
            or sha40(ref['beforeOid']) == sha40(ref['afterOid'])):
        raise ValueError('Exact expected-parent non-force ref update required')
    return ref


class Store:
    def __init__(self, output):
        self.path = Path(output)
        if not self.path.is_absolute() or self.path != self.path.resolve():
            raise ValueError('Exclusive canonical absolute control output required')
        self.path.mkdir(parents=False, exist_ok=False)
        (self.path/'bodies').mkdir()

    def inventory(self):
        rows = []
        for item in [self.path, *sorted(self.path.rglob('*'))]:
            info = item.lstat()
            if item.is_symlink() or not (item.is_file() or item.is_dir()):
                raise ValueError('Unexpected storage object in control evidence')
            if item.is_file() and info.st_nlink != 1:
                raise ValueError('Single authoritative evidence file required')
            rows.append({'path': str(item.relative_to(self.path)) or '.', 'directory': item.is_dir(),
                'logical_bytes': info.st_size, 'allocated_bytes': info.st_blocks*512})
        logical = sum(r['logical_bytes'] for r in rows)
        allocated = sum(r['allocated_bytes'] for r in rows)
        if max(logical, allocated) > CAPS['host_receipt_bytes']:
            raise ValueError('Original 192MiB logical/allocated receipt storage cap exceeded')
        return {'files': rows, 'logical_bytes': logical, 'allocated_bytes': allocated,
            'git_spool_bytes': 0, 'git_spool_cap_bytes': CAPS['spool_bytes'],
            'host_receipt_cap_bytes': CAPS['host_receipt_bytes']}

    def open(self, relative, reserved_bytes):
        if self.inventory()['allocated_bytes'] + math.ceil(reserved_bytes/4096)*4096 > CAPS['host_receipt_bytes']:
            raise ValueError('Cannot prospectively reserve durable control receipt bytes')
        if not re.fullmatch(r'(?:bodies/)?[A-Za-z0-9_-][A-Za-z0-9_.-]*', relative):
            raise ValueError('Only fixed control evidence destinations allowed')
        path = self.path/relative
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        stream = os.fdopen(fd, 'wb')
        stream._seti_parent = path.parent
        stream._seti_path = path
        return stream

    def seal(self, stream):
        stream.flush()
        initial = os.fstat(stream.fileno())
        if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
            raise ValueError('Regular sole-link durable receipt required')
        os.fsync(stream.fileno())
        parent = getattr(stream, '_seti_parent', self.path)
        path = getattr(stream, '_seti_path', None)
        stream.close()
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if path is not None:
            size, sha = file_digest(path)
            final = path.lstat()
            if identity(initial) != identity(final) or size != initial.st_size:
                raise ValueError('Durable receipt independent readback identity differs')
            result = {'bytes': size, 'sha256': sha, 'durable_fsync': True,
                'independent_reopened_hash_verified': True, 'single_authoritative_file': True}
        else:
            result = None
        self.inventory()
        return result

    def save(self, relative, data):
        stream = self.open(relative, len(data))
        try:
            stream.write(data)
            self.seal(stream)
        finally:
            if not stream.closed:
                stream.close()
        return self.path/relative


class HttpsTransport:
    """Direct fixed-host HTTPS: no proxy, redirect handler or automatic retry."""
    def __init__(self, token):
        if not token or '\r' in token or '\n' in token:
            raise ValueError('Repository job authentication capability required')
        self.token = token

    def request(self, method, path, body_path, output, limit, timeout, *, request_pin):
        if not (path.startswith(API + '/') or path == '/graphql') or method not in ('GET', 'POST'):
            raise ValueError('Only the fixed owned repository API is allowed')
        if path == '/graphql':
            if method != 'POST' or body_path is None or request_pin['bytes'] > 4096:
                raise ValueError('Only the bounded fixed GraphQL mutation body is permitted')
        deadline = time.monotonic()+timeout
        def remaining():
            value = deadline-time.monotonic()
            if value <= 0:
                raise ValueError('Original finite request interval exhausted; no retry')
            if connection.sock is not None:
                connection.sock.settimeout(min(30, value))
            return value
        connection = http.client.HTTPSConnection('api.github.com', timeout=min(30, timeout),
            context=ssl.create_default_context())
        size = request_pin['bytes']
        source = None
        if body_path is not None:
            fd = os.open(body_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            source = os.fdopen(fd, 'rb')
            initial = os.fstat(fd)
            if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1 or initial.st_size != size:
                source.close()
                raise ValueError('Exact pinned regular request body required before dispatch')
            if path == '/graphql':
                try:
                    raw_graphql = source.read(size+1)
                    if len(raw_graphql) != size or digest(raw_graphql) != request_pin['sha256']:
                        raise ValueError('Fixed GraphQL body differs from actual before-dispatch pins')
                    validate_graphql(json.loads(raw_graphql))
                    source.seek(0)
                except BaseException:
                    source.close()
                    raise
        try:
            remaining()
            connection.putrequest(method, path, skip_accept_encoding=True)
            for name, value in [('Authorization', 'Bearer '+self.token), ('User-Agent', 'seti-actions-control/1'),
                    ('Accept', 'application/vnd.github+json'), ('X-GitHub-Api-Version', '2022-11-28'),
                    ('Content-Type', 'application/json'), ('Content-Length', str(size)), ('Cache-Control', 'no-cache')]:
                connection.putheader(name, value)
            connection.endheaders()
            sent, sent_sha = 0, hashlib.sha256()
            if source is not None:
                while sent < size:
                    remaining()
                    block = source.read(min(65536, size-sent))
                    if not block:
                        raise ValueError('Pinned request body truncated while sending')
                    connection.send(block)
                    sent += len(block)
                    sent_sha.update(block)
                if source.read(1) or identity(initial) != identity(os.fstat(source.fileno())) or identity(initial) != identity(body_path.lstat()):
                    raise ValueError('Pinned request body changed while sending')
            if sent != size or sent_sha.hexdigest() != request_pin['sha256']:
                raise ValueError('Actual sent request body bytes/hash differ from prospective pins')
            output._seti_sent_request_body = {'request_body_transmission_verified': True,
                'sent_request_body_bytes': sent, 'sent_request_body_sha256': sent_sha.hexdigest()}
            remaining()
            response = connection.getresponse()
            count = 0
            while True:
                remaining()
                block = response.read(min(65536, limit + 1 - count))
                if not block:
                    break
                count += len(block)
                output.write(block)
                if count > limit:
                    raise ValueError('Response body exceeded its prospective reservation; incomplete custody')
            return {'status': response.status, 'header_count': len(response.getheaders()),
                'authentication_header_value_retained': False,
                'authentication_header_bytes': len(('Bearer '+self.token).encode()),
                'request_body_transmission_verified': True, 'sent_request_body_bytes': sent,
                'sent_request_body_sha256': sent_sha.hexdigest(),
                'full_http_tls_wire_known': False}
        finally:
            if source is not None:
                source.close()
            connection.close()


class Control:
    def __init__(self, store, transport, *, clock=time.monotonic):
        self.store, self.transport, self.clock = store, transport, clock
        self.started = clock()
        self.records = []
        self.request_bytes = self.response_bytes = self.charged = 0
        self.stopped = self.update_attempted = False
        self.journal = store.open('receipt-ledger.jsonl', 512*1024)

    def event(self, value):
        self.journal.write(canonical(value)+b'\n')
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def check(self):
        if self.stopped or self.clock()-self.started >= CAPS['seconds']:
            raise ValueError('Finite control closed or original 600s deadline exhausted; no retry')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > CAPS['rss_per_process_bytes']:
            raise ValueError('Original 512MiB publisher process RSS cap exceeded')

    def call(self, method, suffix, payload=None, *, body_path=None, reserve=1024*1024):
        self.check()
        if suffix == '/graphql':
            if method != 'POST' or payload is None or body_path is not None:
                raise ValueError('Fixed ref mutation must use the bounded explicit structured payload')
            ref = validate_graphql(payload)
            if getattr(self, 'expected_ref_update', None) != (ref['beforeOid'], ref['afterOid']):
                raise ValueError('Atomic ref mutation differs from verified publication parent/candidate')
        ordinal = len(self.records)
        if ordinal >= CAPS['prospective_http_operations']:
            raise ValueError('Prospective twenty HTTP operation ceiling exhausted')
        if payload is not None:
            body_path = self.store.save(f'bodies/{ordinal:02d}-request.json', canonical(payload))
        body_bytes, body_sha = file_digest(body_path) if body_path is not None else (0, digest(b''))
        if self.request_bytes+body_bytes > CAPS['request_bytes'] or self.charged+reserve > CAPS['reply_bytes']:
            raise ValueError('Cannot reserve exact application bodies inside original request/reply caps')
        route = '/graphql' if suffix == '/graphql' else API+suffix
        record = {'ordinal': ordinal, 'method': method, 'path': route,
            'request_body_file': str(body_path.relative_to(self.store.path)) if body_path is not None else None,
            'request_body_bytes': body_bytes, 'request_body_sha256': body_sha,
            'response_reserved_bytes': reserve, 'response_unknown': True, 'automatic_retry': False,
            'request_body_transmission_verified': False,
            'started_epoch_ms': int(time.time()*1000)}
        self.records.append(record)
        self.request_bytes += body_bytes
        self.charged += reserve
        self.event({'kind': 'intent', **record})
        reply_name = f'bodies/{ordinal:02d}-response.json'
        stream = self.store.open(reply_name, reserve)
        try:
            metadata = self.transport.request(method, route, body_path, stream, reserve,
                CAPS['seconds']-(self.clock()-self.started),
                request_pin={'bytes': body_bytes, 'sha256': body_sha})
            custody = self.store.seal(stream)
            reply_path = self.store.path/reply_name
            size, sha = file_digest(reply_path)
            if size > reserve:
                raise ValueError('Returned application body exceeded its prospective reservation')
            if (metadata.get('request_body_transmission_verified') is not True
                    or metadata.get('sent_request_body_bytes') != body_bytes
                    or metadata.get('sent_request_body_sha256') != body_sha):
                raise ValueError('Independent exact sent-body metadata does not match pinned request')
            self.response_bytes += size
            self.charged += size-reserve
            record.update(response_body_file=reply_name, response_body_bytes=size, response_body_sha256=sha,
                response_unknown=False, finished_epoch_ms=int(time.time()*1000),
                response_durable_custody=custody, **metadata)
            self.event({'kind': 'reply', **record})
            self.check()
            if not 200 <= metadata['status'] < 300:
                raise ValueError('HTTP operation failed or redirected; no retry; status='+str(metadata['status']))
            with reply_path.open('r') as source:
                return json.load(source)
        except BaseException as error:
            self.stopped = True
            record.update(getattr(stream, '_seti_sent_request_body', {}))
            if not stream.closed:
                custody = self.store.seal(stream)
            else:
                size, sha = file_digest(self.store.path/reply_name)
                custody = {'bytes': size, 'sha256': sha, 'durable_fsync': True,
                    'independent_reopened_hash_verified': True, 'single_authoritative_file': True}
            if record['response_unknown']:
                record.update(response_prefix_file=reply_name, response_prefix_bytes=custody['bytes'],
                    response_prefix_sha256=custody['sha256'], response_prefix_complete=False,
                    response_prefix_durable_custody=custody)
            record['error'] = str(error).replace(getattr(self.transport, 'token', '\x00'), '<REDACTED>')
            self.event({'kind': 'closed', **record})
            raise
        finally:
            if not stream.closed:
                self.store.seal(stream)

    def head(self):
        value = self.call('GET', '/git/ref/heads/'+BRANCH)
        if value.get('ref') != 'refs/heads/'+BRANCH or value.get('object', {}).get('type') != 'commit':
            raise ValueError('Exact fixed publication branch ref required')
        return sha40(value['object']['sha'])

    def commit(self, sha):
        value = self.call('GET', '/git/commits/'+sha40(sha))
        if value.get('sha') != sha:
            raise ValueError('Immutable commit readback differs')
        return sha40(value['tree']['sha']), [sha40(row['sha']) for row in value['parents']]

    def tree(self, sha):
        value = self.call('GET', '/git/trees/'+sha40(sha), reserve=4*1024**2)
        if value.get('sha') != sha or value.get('truncated') is not False:
            raise ValueError('Complete immutable tree readback required')
        rows = {}
        for row in value['tree']:
            name = row['path']
            modes = {'040000': 'tree', '100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'}
            if (not isinstance(name, str) or not name or name in ('.', '..') or '/' in name
                    or '\0' in name or name in rows or modes.get(row.get('mode')) != row.get('type')):
                raise ValueError('Exact unique tree children required')
            rows[name] = {'mode': row['mode'], 'type': row['type'], 'sha': sha40(row['sha'])}
        raw = b''.join(row['mode'].lstrip('0').encode()+b' '+name.encode()+b'\0'+bytes.fromhex(row['sha'])
            for name, row in sorted(rows.items(), key=lambda item: item[0].encode()+(b'/' if item[1]['type'] == 'tree' else b'')))
        actual = hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual != sha:
            raise ValueError('Independent Git tree object hash differs from immutable readback')
        return rows

    def blob(self, content):
        value = self.call('POST', '/git/blobs', {'content': base64.b64encode(content).decode(), 'encoding': 'base64'})
        if value.get('sha') != blob_sha(content):
            raise ValueError('New immutable blob does not match exact supplied bytes')
        return value['sha']


def validate_protocol(root, relative):
    original = Path(root)/relative
    path = original.resolve()
    if not path.is_relative_to(Path(root).resolve()) or original.is_symlink():
        raise ValueError('Owned pinned protocol file required')
    raw = path.read_bytes()
    protocol = json.loads(raw)
    if (protocol.get('schema') != 'radio-native-v2-actions-local-python-publication-control-v1'
            or protocol.get('namespace') != NAMESPACE or protocol.get('repository') != REPOSITORY
            or protocol.get('repository_node_id') != REPOSITORY_NODE_ID
            or protocol.get('branch') != BRANCH or protocol.get('output_prefix') != PREFIX
            or protocol.get('caps') != CAPS or protocol.get('source') != SOURCE_RECIPE
            or any(protocol.get(key) is not value for key, value in DISABLED.items())
            or protocol.get('publication', {}).get('atomic_expected_parent_cas') is not True):
        raise ValueError('Exact fixed engineering protocol/source/caps with all authority closed required')
    return protocol, digest(raw)


def environment(activation):
    if (os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/'+BRANCH
            or os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or os.environ.get('GITHUB_SHA') != activation
            or not re.fullmatch('[1-9][0-9]*', os.environ.get('GITHUB_RUN_ID', ''))):
        raise ValueError('Fixed owned first-attempt activation environment required')
    return int(os.environ['GITHUB_RUN_ID'])


def validate_activation(root, activation, proof_path):
    if not proof_path or not Path(proof_path).is_absolute():
        raise ValueError('Required absolute external two-stage activation proof must precede HTTP dispatch')
    root = Path(root).resolve()
    proof_pin = file_digest(proof_path)
    raw = Path(proof_path).read_bytes()
    if proof_pin != (len(raw), digest(raw)):
        raise ValueError('Activation proof changed after its independent custody pin')
    proof = json.loads(raw)
    manifest_pin, marker_pin = file_digest(root/MANIFEST), file_digest(root/MARKER)
    manifest_raw = (root/MANIFEST).read_bytes()
    marker_raw = (root/MARKER).read_bytes()
    if manifest_pin != (len(manifest_raw), digest(manifest_raw)) or marker_pin != (len(marker_raw), digest(marker_raw)):
        raise ValueError('Preparation manifest or marker changed after custody pin')
    manifest, marker = json.loads(manifest_raw), json.loads(marker_raw)
    if (proof.get('schema') != 'radio-native-v2-actions-activation-readback-v1'
            or proof.get('namespace') != NAMESPACE or proof.get('activation_commit') != activation
            or proof.get('verified') is not True or manifest.get('namespace') != NAMESPACE
            or marker.get('namespace') != NAMESPACE or marker.get('activate') is not True
            or sha40(proof.get('preparation_commit')) != marker.get('preparation_commit')
            or proof.get('manifest_sha256') != digest(manifest_raw)
            or marker.get('manifest_sha256') != digest(manifest_raw)):
        raise ValueError('Exact marker-only activation/preparation manifest binding required')
    for document in (proof, manifest, marker):
        if any(document.get(key) is not value for key, value in DISABLED.items()):
            raise ValueError('Activation cannot grant scientific or native authority')
    files = manifest.get('files', [])
    readback = marker.get('independent_readback', {})
    if (not isinstance(files, list) or len(files) != len(REQUIRED_FILES)
            or {item.get('path') for item in files} != REQUIRED_FILES
            or readback.get('commit') != proof['preparation_commit'] or readback.get('verified') is not True
            or readback.get('manifest_sha256') != digest(manifest_raw) or readback.get('files') != files):
        raise ValueError('Independent readback must bind the exact five prepared files')
    for item in files:
        path = root/item['path']
        if not path.resolve().is_relative_to(root) or path.is_symlink() or file_digest(path) != (item.get('bytes'), item.get('sha256')):
            raise ValueError('Prepared five-file closure differs before publisher launch')
    return digest(raw), digest(canonical(files))


def source_request(store):
    source = store.open('source.txt', SOURCE_BYTES)
    sha, git = hashlib.sha256(), hashlib.sha1(b'blob '+str(SOURCE_BYTES).encode()+b'\0')
    try:
        block = PATTERN*1024
        for _ in range(SOURCE_BYTES//len(block)):
            source.write(block)
            sha.update(block)
            git.update(block)
        store.seal(source)
    finally:
        if not source.closed:
            source.close()
    if sha.hexdigest() != SOURCE_SHA256 or git.hexdigest() != SOURCE_BLOB:
        raise ValueError('Deterministic source recipe changed')
    size = len(b'{"content":"')+4*((SOURCE_BYTES+2)//3)+len(b'","encoding":"base64"}')
    request = store.open('source-blob-request.json', size)
    try:
        request.write(b'{"content":"')
        with (store.path/'source.txt').open('rb') as raw:
            while block := raw.read(48*1024):
                request.write(base64.b64encode(block))
        request.write(b'","encoding":"base64"}')
        store.seal(request)
    finally:
        if not request.closed:
            request.close()
    return store.path/'source-blob-request.json'


def public_source_readback(control):
    value = control.call('GET', '/git/blobs/'+SOURCE_BLOB, reserve=40*1024**2)
    if value.get('sha') != SOURCE_BLOB or value.get('size') != SOURCE_BYTES or value.get('encoding') != 'base64':
        raise ValueError('Exact maximum-source public blob metadata required')
    content = value['content']
    if not isinstance(content, str) or not re.fullmatch('[A-Za-z0-9+/=\r\n]*', content):
        raise ValueError('Exact bounded GitHub base64 blob reply required')
    decoded = base64.b64decode(content.replace('\r', '').replace('\n', ''), validate=True)
    if len(decoded) != SOURCE_BYTES or digest(decoded) != SOURCE_SHA256 or blob_sha(decoded) != SOURCE_BLOB:
        raise ValueError('Public maximum-source readback bytes differ')
    control.store.save('source-readback.txt', decoded)


def publish_tree(control, parent, before, files, *, evidence=False):
    parent_tree, _ = control.commit(parent)
    if before is None:
        before = control.tree(parent_tree)
    if not evidence and PREFIX in before:
        raise ValueError('Owned control namespace already exists; no replay')
    made = control.call('POST', '/git/trees', {'base_tree': parent_tree, 'tree': [
        {'path': PREFIX+'/'+name, 'mode': '100644', 'type': 'blob', 'sha': sha}
        for name, sha in sorted(files.items())]})
    tree = sha40(made['sha'])
    after = control.tree(tree)
    if {k:v for k,v in before.items() if k != PREFIX} != {k:v for k,v in after.items() if k != PREFIX}:
        raise ValueError('Candidate tree changes unrelated paths')
    folder = after.get(PREFIX, {})
    if folder.get('mode') != '040000' or folder.get('type') != 'tree':
        raise ValueError('Exact owned candidate directory required')
    contents = control.tree(folder['sha'])
    old = control.tree(before[PREFIX]['sha']) if evidence and PREFIX in before else {}
    if evidence and 'evidence.json' in old:
        raise ValueError('Administrative evidence path already published; no replay')
    expected = {**old, **{name: {'mode': '100644', 'type': 'blob', 'sha': sha} for name, sha in files.items()}}
    if contents != expected:
        raise ValueError('Exact fresh candidate leaf inventory differs')
    made = control.call('POST', '/git/commits', {'parents': [parent], 'tree': tree,
        'message': NAMESPACE+(' preserve measured evidence' if evidence else ' finite source control')})
    candidate = sha40(made['sha'])
    control.candidate = candidate
    if control.commit(candidate) != (tree, [parent]) or control.head() != parent:
        raise ValueError('Candidate parent/tree or late publication head changed')
    control.update_attempted = True
    control.expected_ref_update = (parent, candidate)
    updated = control.call('POST', '/graphql', {
        'query': GRAPHQL_QUERY,
        'variables': {'input': {'repositoryId': REPOSITORY_NODE_ID,
            'refUpdates': [{'name': 'refs/heads/'+BRANCH, 'beforeOid': parent,
                'afterOid': candidate, 'force': False}], 'clientMutationId': NAMESPACE}}})
    if ('errors' in updated or updated.get('data', {}).get('updateRefs', {}).get('clientMutationId') != NAMESPACE
            or control.head() != candidate):
        raise ValueError('Exact atomic expected-parent acknowledgement/head differs')
    return candidate, tree


def compact_evidence(store, summary, records):
    bodies = []
    paths = sorted({r[k] for r in records for k in ('request_body_file', 'response_body_file', 'response_prefix_file') if r.get(k)})
    for relative in paths:
        raw = (store.path/relative).read_bytes()
        packed = gzip.compress(raw, mtime=0)
        bodies.append({'path': relative, 'bytes': len(raw), 'sha256': digest(raw),
            'encoding': 'gzip_base64', 'content': base64.b64encode(packed).decode()})
    value = {'schema': 'radio-native-v2-actions-lossless-control-evidence-v1', 'summary': summary,
        'source_recipe': SOURCE_RECIPE, 'records': records, 'bodies': bodies,
        'authentication_header_values_retained': False, 'full_http_tls_wire_known': False,
        'post_control_evidence_publication_excluded': True, **DISABLED}
    store.save('compact-control-evidence.json', canonical(value))


def run_control(args, *, transport=None):
    sha40(args.activation_sha)
    if sha40(args.expected_parent) != args.activation_sha:
        raise ValueError('The control must publish directly from its fixed activation commit')
    protocol, protocol_sha = validate_protocol(args.root, args.protocol)
    run_id = environment(args.activation_sha)
    activation_proof_sha, prepared_files_sha = validate_activation(args.root, args.activation_sha,
        getattr(args, 'activation_proof', None))
    store = Store(args.output)
    transport = transport or HttpsTransport(os.environ.get('GITHUB_TOKEN', ''))
    control = Control(store, transport)
    candidate = tree = None
    status, reason = 'CLOSED_FAILED', None
    try:
        runs = control.call('GET', '/actions/runs?head_sha='+args.activation_sha+'&per_page=100')
        if (runs.get('total_count') != 1 or len(runs.get('workflow_runs', [])) != 1
                or runs['workflow_runs'][0].get('id') != run_id
                or runs['workflow_runs'][0].get('run_attempt') != 1
                or runs['workflow_runs'][0].get('head_sha') != args.activation_sha):
            raise ValueError('Exactly one current first-attempt activation workflow run required')
        if control.head() != args.expected_parent:
            raise ValueError('Activation publication head changed before source transport')
        parent_tree, _ = control.commit(args.expected_parent)
        before = control.tree(parent_tree)
        if PREFIX in before:
            raise ValueError('Owned source/witness/evidence namespace already exists; no replay')
        request = source_request(store)
        made = control.call('POST', '/git/blobs', body_path=request)
        if made.get('sha') != SOURCE_BLOB:
            raise ValueError('Maximum-source blob differs from exact local recipe')
        public_source_readback(control)
        witness = {'schema': SCHEMA, 'namespace': NAMESPACE, 'activation_commit': args.activation_sha,
            'expected_parent': args.expected_parent, 'workflow_run_id': run_id, 'protocol_sha256': protocol_sha,
            'activation_readback_sha256': activation_proof_sha,
            'activation_prepared_five_file_closure_sha256': prepared_files_sha,
            'source_recipe': SOURCE_RECIPE, 'exact_source_public_readback_verified': True,
            'application_body_accounting_only': True, 'atomic_expected_parent_cas': True,
            'future_native_runner_join_qualified': False, **DISABLED}
        store.save('protocol-witness.json', canonical(witness))
        witness_blob = control.blob(canonical(witness))
        candidate, tree = publish_tree(control, args.expected_parent, before,
            {'source.txt': SOURCE_BLOB, 'protocol-witness.json': witness_blob})
        status = 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY'
    except BaseException as error:
        reason = str(error).replace(getattr(transport, 'token', '\x00'), '<REDACTED>')
        control.stopped = True
    finally:
        store.seal(control.journal)
    usage = {'operation_count': len(control.records), 'request_bytes': control.request_bytes,
        'response_bytes': control.response_bytes, 'response_charged_bytes': control.charged,
        'unknown_response_bytes': sum(r['response_reserved_bytes'] for r in control.records if r['response_unknown']),
        'unknown_response_count': sum(r['response_unknown'] for r in control.records),
        'elapsed_seconds': control.clock()-control.started,
        'publisher_self_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    summary = {'schema': SCHEMA, 'status': status, 'reason': reason, 'namespace': NAMESPACE,
        'activation_commit': args.activation_sha, 'workflow_run_id': run_id, 'protocol_sha256': protocol_sha,
        'activation_readback_sha256': activation_proof_sha,
        'activation_prepared_five_file_closure_sha256': prepared_files_sha,
        'source_recipe': SOURCE_RECIPE, 'publication_commit': candidate, 'publication_tree': tree,
        'publication_candidate': getattr(control, 'candidate', None),
        'update_may_have_landed': control.update_attempted, 'usage': usage, 'caps': CAPS,
        'actual_child_processes_created': 0, 'automatic_retry': False, 'force': False,
        'atomic_expected_parent_cas': True, 'full_http_tls_wire_known': False,
        'accounting_domain': protocol['accounting']['domain'], 'independent_rss_supervision_required': True,
        'post_control_evidence_publication_excluded': True, 'future_native_runner_join_qualified': False,
        'rng_draws': 0, 'telescope_reads': 0, **DISABLED}
    provisional = {**summary, 'summary_is_before_archive_resource_finalization': True}
    try:
        compact_evidence(store, provisional, control.records)
        store.save('storage-inventory.json', canonical(store.inventory()))
        if not control.stopped:
            control.check()
    except BaseException as error:
        status = 'CLOSED_FAILED'
        reason = str(error).replace(getattr(transport, 'token', '\x00'), '<REDACTED>')
        control.stopped = True
    usage['elapsed_seconds'] = control.clock()-control.started
    usage['publisher_self_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    summary.update(status=status, reason=reason)
    store.save('caller-summary.json', canonical(summary))
    print(json.dumps({'schema': SCHEMA, 'status': status, 'reason': reason, 'publication_commit': candidate,
        'usage': usage, **DISABLED}, sort_keys=True), flush=True)
    return 0 if status == 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY' else 1


def publish_evidence(args, *, transport=None):
    root = Path(args.output).resolve()
    summary_path = root/'publisher/caller-summary.json'
    summary = json.loads(summary_path.read_bytes()) if summary_path.exists() else {
        'schema': SCHEMA, 'status': 'CLOSED_FAILED', 'activation_commit': sha40(args.activation_sha),
        'namespace': NAMESPACE, 'source_recipe': SOURCE_RECIPE,
        'reason': 'Publisher terminated before a complete summary; supervisor evidence is authoritative', **DISABLED}
    if (summary.get('schema') != SCHEMA or summary.get('namespace') != NAMESPACE
            or summary.get('source_recipe') != SOURCE_RECIPE
            or summary.get('status') not in ('PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY', 'CLOSED_FAILED')
            or summary.get('activation_commit') != sha40(args.activation_sha)
            or any(summary.get(key) is not value for key, value in DISABLED.items())):
        raise ValueError('Only fixed closed-authority control/failure evidence may be preserved')
    for key in ('publication_candidate', 'publication_commit'):
        if summary.get(key) is not None:
            sha40(summary[key])
    files = {}
    allowed = ['activation-proof.json', 'prepared-source-inventory.json', 'runtime-inventory-before-control.json',
        'supervisor-report.json', 'supervisor-storage-inventory.json', 'supervisor-terminal.json',
        'supervisor-terminal-storage-failure.json', 'procfs-samples.jsonl', 'publisher-stdout.log',
        'publisher-stderr.log', 'publisher/caller-summary.json', 'publisher/storage-inventory.json',
        'publisher/compact-control-evidence.json', 'publisher/protocol-witness.json', 'publisher/receipt-ledger.jsonl']
    if not (root/'publisher/compact-control-evidence.json').exists():
        allowed += ['publisher/source-blob-request.json', 'publisher/source.txt', 'publisher/source-readback.txt']
        allowed += [str(p.relative_to(root)) for p in sorted((root/'publisher/bodies').glob('*.json'))]
    for relative in allowed:
        path = root/relative
        if not path.exists():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Canonical sole-custody administrative evidence input required')
        pinned_bytes, pinned_sha = file_digest(path)
        if pinned_bytes > 40*1024**2:
            raise ValueError('Bounded observed control body/evidence only')
        data = path.read_bytes()
        if len(data) != pinned_bytes or digest(data) != pinned_sha:
            raise ValueError('Administrative evidence changed after independent pin')
        files[relative] = {'bytes': len(data), 'sha256': digest(data),
            'encoding': 'gzip_base64', 'content': base64.b64encode(gzip.compress(data, mtime=0)).decode()}
    envelope = canonical({'schema': 'radio-native-v2-actions-public-measured-evidence-v1',
        'activation_commit': args.activation_sha, 'measured_publication_commit': summary.get('publication_commit'),
        'control_status': summary['status'], 'synthetic_summary_if_missing': summary if not summary_path.exists() else None,
        'files': files, 'administrative_publication_outside_measured_control': True,
        'future_native_runner_join_qualified': False, **DISABLED})
    store = Store(str(root/'evidence-publication'))
    control = Control(store, transport or HttpsTransport(os.environ.get('GITHUB_TOKEN', '')))
    try:
        parent = control.head()
        allowed_heads = {args.activation_sha, summary.get('publication_candidate'), summary.get('publication_commit')}
        if parent not in allowed_heads:
            raise ValueError('Head outside the fixed activation/control candidates; preserve locally without new mutation')
        if summary['status'] == 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY' and parent != summary['publication_commit']:
            raise ValueError('Control head changed before one-shot evidence preservation')
        blob = control.blob(envelope)
        candidate, tree = publish_tree(control, parent, None, {'evidence.json': blob}, evidence=True)
        store.save('publication-receipt.json', canonical({'schema': SCHEMA, 'publication_commit': candidate,
            'tree': tree, 'evidence_sha256': digest(envelope), 'administrative_publication_outside_measured_control': True,
            'atomic_expected_parent_cas': True, **DISABLED}))
        print(json.dumps({'status': 'ADMINISTRATIVE_EVIDENCE_PUBLISHED', 'publication_commit': candidate,
            'evidence_sha256': digest(envelope), **DISABLED}, sort_keys=True), flush=True)
        return 0
    finally:
        store.seal(control.journal)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('control', 'publish-evidence'):
        sub = commands.add_parser(name)
        sub.add_argument('--root', default='.')
        sub.add_argument('--output', required=True)
        sub.add_argument('--activation-sha', required=True)
        if name == 'control':
            sub.add_argument('--expected-parent', required=True)
            sub.add_argument('--protocol', required=True)
            sub.add_argument('--activation-proof', required=True)
    args = parser.parse_args()
    try:
        return run_control(args) if args.command == 'control' else publish_evidence(args)
    except Exception as error:
        token = os.environ.get('GITHUB_TOKEN', '\x00')
        print(json.dumps({'schema': SCHEMA, 'status': 'CLOSED_FAILED',
            'reason': str(error).replace(token, '<REDACTED>'), **DISABLED}, sort_keys=True), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
