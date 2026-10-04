"""One-shot engineering GitHub CAS control; inert on import, never scientific authority.

Synthetic transports are explicitly marked synthetic. Only the CLI supplies the
HTTPS transport. A failed/ambiguous call spends the attempt without retry.
"""
import argparse
import base64
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time

REPOSITORY = 'andersenmartin-blip/setisearch'
REPOSITORY_ID = 'R_kgDOT558WQ'
BRANCH = 'm43-support-qualification'
REF = 'refs/heads/' + BRANCH
PREFIX = 'results_radio_hosted_cas_control_20261004a'
NAMESPACE = 'radio-hosted-cas-control-20261004a'
WORKFLOW_PATH = '.github/workflows/radio_hosted_cas_control_20261004a.yml'
FREEZE_PATH = 'config/radio_hosted_cas_control_20261004a.freeze.json'
MARKER_PATH = 'config/radio_hosted_cas_control_20261004a.activate.json'
SOURCE_PATHS = tuple(sorted((WORKFLOW_PATH, 'RADIO_HOSTED_CAS_CONTROL_2026-10-04_PROTOCOL.md',
    *(PREFIX + '/' + name for name in ('activation_gate.py', 'control.py', 'publisher.py',
      'supervisor.py', 'test_activation_gate.py', 'test_control.py', 'test_publisher.py',
      'test_supervisor.py')))))
LIMITS = {'control_wall_seconds': 180, 'control_api_calls': 40,
          'response_bytes': 2097152, 'wire_bytes': 8388608, 'retained_bytes': 8388608,
          'publication_wall_seconds': 120, 'publication_api_calls': 20,
          'publication_wire_bytes': 12582912, 'publication_retained_bytes': 12582912}
STATE_PATH = PREFIX + '/service-state.json'
CONFLICT_PATH = PREFIX + '/conflict-test-state.json'
QUERY = 'mutation($input:UpdateRefsInput!){updateRefs(input:$input){clientMutationId}}'
HEAD_QUERY = ('query($owner:String!,$name:String!,$ref:String!){repository(owner:$owner,'
              'name:$name){id ref(qualifiedName:$ref){target{oid}}}}')
MAX_CALLS, MAX_RESPONSE, MAX_TOTAL, MAX_RETAINED, MAX_SECONDS = 40, 2 << 20, 8 << 20, 8 << 20, 180
DATE = '2026-10-04T00:00:00Z'
IDENTITY = {'name': 'SETI engineering control',
            'email': 'radio-control@users.noreply.github.com', 'date': DATE}
FALSE_AUTHORITY = {'scientific_execution_authorized': False,
                   'scientific_allocation_authorized': False,
                   'scientific_store_qualified': False,
                   'source_execution_qualified': False,
                   'full_runtime_freeze_qualified': False,
                   'production_synthetic_ack': False}


class ClosedError(Exception):
    """Diagnostics deliberately carry no externally supplied text."""


def require(condition):
    if not condition:
        raise ClosedError()


def sha(value, length=40):
    require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None)
    return value


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out)
            out[key] = value
        return out
    def invalid(_):
        raise ClosedError()
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except Exception:
        raise ClosedError() from None


def git_oid(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def manifest_sha256(files):
    """Canonical source inventory digest; does not hash freeze.json itself."""
    return hashlib.sha256(canonical(files).rstrip(b'\n')).hexdigest()


def validate_source_files(files):
    require(type(files) is list and len(files) == len(SOURCE_PATHS))
    names = []
    for entry in files:
        require(type(entry) is dict and set(entry) == {'path', 'bytes', 'sha256'})
        p = entry['path']
        require(type(p) is str and not p.startswith('/') and '\\' not in p
                and all(x not in ('', '.', '..') for x in p.split('/')))
        require(p in SOURCE_PATHS)
        require(type(entry['bytes']) is int and 0 < entry['bytes'] <= MAX_RESPONSE)
        sha(entry['sha256'], 64)
        names.append(p)
    require(names == list(SOURCE_PATHS))
    return files


def verify_proof(proof, activation, run_id, root, expected_manifest):
    """Strict reusable gate helper; independent pin must come from frozen code/config."""
    require(type(proof) is dict and set(proof) == {
        'schema', 'repository', 'branch', 'namespace', 'activation', 'preparation',
        'manifest_sha256', 'run_id', 'source_files'})
    require(proof['schema'] == 'radio-hosted-cas-control-activation-proof-v1'
            and proof['repository'] == REPOSITORY and proof['branch'] == BRANCH
            and proof['namespace'] == NAMESPACE and proof['activation'] == sha(activation))
    sha(proof['preparation'])
    require(proof['preparation'] != activation
            and proof['run_id'] == run_id)
    files = validate_source_files(proof['source_files'])
    require(sha(proof['manifest_sha256'], 64) == sha(expected_manifest, 64))
    root = Path(root).resolve()
    freeze_raw = (root / FREEZE_PATH).read_bytes()
    require(hashlib.sha256(freeze_raw).hexdigest() == expected_manifest)
    freeze = strict_json(freeze_raw)
    require(type(freeze) is dict and set(freeze) == {
        'schema', 'namespace', 'repository', 'branch', 'source_files', 'limits'}
        and freeze['schema'] == 'radio-hosted-cas-control-freeze-v1'
        and freeze['namespace'] == NAMESPACE and freeze['repository'] == REPOSITORY
        and freeze['branch'] == BRANCH and freeze['source_files'] == files
        and freeze['limits'] == LIMITS and all(type(v) is int for v in freeze['limits'].values()))
    for item in files:
        path = root / item['path']
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root))
        require(all(not parent.is_symlink() for parent in path.parents if parent != root.parent))
        raw = path.read_bytes()
        require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'])
    return files


def verify_marker(marker, proof):
    require(type(marker) is dict and set(marker) == {'schema', 'namespace', 'repository',
        'branch', 'preparation', 'manifest_sha256', 'source_readback_sha256', 'allocation'})
    require(marker['schema'] == 'radio-hosted-cas-control-activation-v1'
            and marker['namespace'] == NAMESPACE and marker['repository'] == REPOSITORY
            and marker['branch'] == BRANCH and marker['preparation'] == proof['preparation']
            and marker['manifest_sha256'] == proof['manifest_sha256']
            and marker['source_readback_sha256'] == manifest_sha256(proof['source_files'])
            and marker['allocation'] == {'identity': NAMESPACE, 'wall_seconds': 300,
                                        'retained_bytes': 20971520, 'attempts': 1}
            and all(type(marker['allocation'][key]) is int
                    for key in ('wall_seconds', 'retained_bytes', 'attempts')))


def tree_bytes(entries):
    require(type(entries) is dict)
    keys = []
    for name, entry in entries.items():
        require(type(name) is str and name and '/' not in name and '\0' not in name
                and name not in ('.', '..'))
        require(type(entry) is tuple and len(entry) == 3)
        mode, kind, oid = entry
        require((mode, kind) in {('100644', 'blob'), ('100755', 'blob'),
                ('120000', 'blob'), ('040000', 'tree'), ('160000', 'commit')})
        sha(oid)
        keys.append((name.encode('utf-8') + (b'/' if kind == 'tree' else b''), name))
    return b''.join(entries[n][0].lstrip('0').encode() + b' ' + n.encode('utf-8')
                    + b'\0' + bytes.fromhex(entries[n][2]) for _, n in sorted(keys))


def commit_bytes(tree, parent, message):
    sha(tree); sha(parent)
    epoch = int(datetime.datetime.fromisoformat(DATE.replace('Z', '+00:00')).timestamp())
    identity = '%s <%s> %d +0000' % (IDENTITY['name'], IDENTITY['email'], epoch)
    return ('tree %s\nparent %s\nauthor %s\ncommitter %s\n\n%s\n'
            % (tree, parent, identity, identity, message)).encode()


def runtime_hashes():
    """Selected current files only; does not assert a future interpreter/ELF freeze."""
    import urllib.parse
    paths = {str(Path(sys.executable).resolve())}
    for module in (json, json.decoder, json.encoder, hashlib, http.client, ssl,
                   argparse, base64, re, datetime, urllib.parse):
        if getattr(module, '__file__', None):
            paths.add(str(Path(module.__file__).resolve()))
    return {'python': sys.version, 'implementation': sys.implementation.name,
            'executable': str(Path(sys.executable).resolve()),
            'files': [{'path': p, 'bytes': Path(p).stat().st_size,
                       'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                      for p in sorted(paths)], 'scope': 'SELECTED_CURRENT_RUNTIME_FILES_ONLY'}


class Artifacts:
    def __init__(self, output):
        p = Path(output)
        require(p.is_absolute() and not p.exists())
        p.mkdir(mode=0o700)
        self.path = p
        self.logical = p.stat().st_size
        self.allocated = max(self.logical, p.stat().st_blocks * 512)
        self.write('exclusive-claim.json', canonical({'exclusive': True, 'pid': os.getpid()}))

    def write(self, name, raw):
        require(type(raw) is bytes and '/' not in name)
        charge = max(len(raw), ((len(raw) + 4095) // 4096) * 4096)
        require(self.logical + len(raw) <= MAX_RETAINED
                and self.allocated + charge <= MAX_RETAINED)
        fd = os.open(self.path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            actual = (self.path / name).stat()
            self.logical += actual.st_size
            self.allocated += max(actual.st_size, actual.st_blocks * 512)
            members = [self.path, *self.path.iterdir()]
            self.logical = sum(p.stat().st_size for p in members)
            self.allocated = sum(max(p.stat().st_size, p.stat().st_blocks * 512) for p in members)
            require(self.logical <= MAX_RETAINED and self.allocated <= MAX_RETAINED)
            directory = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            raise ClosedError() from None


class HTTPSTransport:
    """Direct HTTPS, default certificate verification, no redirect, auth only in memory."""
    synthetic = False

    def __init__(self, token):
        require(type(token) is str and token and '\r' not in token and '\n' not in token)
        self._token = token

    def contains_secret(self, raw):
        pattern = rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'
        if self._token.encode() in raw or re.search(pattern, raw) is not None:
            return True
        try:
            decoded = json.dumps(json.loads(raw), ensure_ascii=False).encode('utf-8')
            return self._token.encode() in decoded or re.search(pattern, decoded) is not None
        except Exception:
            return False

    def __call__(self, method, path, raw, timeout):
        require(path.startswith('/repos/' + REPOSITORY + '/git/')
                or path.startswith('/repos/' + REPOSITORY + '/actions/runs?') or path == '/graphql')
        connection = http.client.HTTPSConnection('api.github.com', timeout=timeout,
                                                context=ssl.create_default_context())
        try:
            connection.request(method, path, body=raw or None, headers={
                'Authorization': 'Bearer ' + self._token, 'User-Agent': 'radio-engineering-control',
                'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                'X-GitHub-Api-Version': '2022-11-28'})
            response = connection.getresponse()
            body = response.read(MAX_RESPONSE)
            return response.status, body
        finally:
            connection.close()


class Control:
    def __init__(self, transport, output, activation, proof, run_id, root, expected_manifest,
                 clock=time.monotonic):
        self.transport, self.clock = transport, clock
        self.started = clock()
        self.calls = self.total = 0
        self.attempted = self.mutations = 0
        self.activation, self.run_id = sha(activation), run_id
        self.proof, self.root, self.expected_manifest = proof, Path(root), expected_manifest
        require(type(run_id) is str and re.fullmatch('[1-9][0-9]{0,19}', run_id) is not None)
        self.artifacts = Artifacts(output)
        self.tree_cache = {}

    def remaining(self):
        remaining = MAX_SECONDS - (self.clock() - self.started)
        require(remaining > 0)
        return remaining

    def api(self, method, suffix, payload=None, *, graphql=False, allow_error=False):
        require(self.calls < MAX_CALLS)
        verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
        self.remaining()
        path = '/graphql' if graphql else '/repos/' + REPOSITORY + '/' + suffix
        raw = b'' if payload is None else canonical(payload)
        request = canonical({'method': method, 'path': path, 'body': payload})
        # Conservative envelope charge exceeds actual body; reserve one full
        # bounded reply before dispatch, and spend it on transport ambiguity.
        require(self.total + len(request) + MAX_RESPONSE <= MAX_TOTAL
                and self.artifacts.logical + len(request) + MAX_RESPONSE + 16384 <= MAX_RETAINED
                and self.artifacts.allocated + len(request) + MAX_RESPONSE + 16384 <= MAX_RETAINED)
        self.calls += 1
        number = '%02d' % self.calls
        self.artifacts.write(number + '-request.json', request)
        self.total += len(request)
        dispatched = received = False
        try:
            dispatched = True
            status, response = self.transport(method, path, raw, min(30, self.remaining()))
            received = True
            require(type(status) is int and type(response) is bytes)
            self.total += len(response)
            if self.transport.contains_secret(response):
                self.artifacts.write(number + '-response-redacted.json', canonical({'redacted': True}))
                raise ClosedError()
            capped = len(response) >= MAX_RESPONSE
            self.artifacts.write(number + ('-response-partial.raw' if capped else '-response.raw'),
                                 response[:MAX_RESPONSE])
            self.artifacts.write(number + '-journal.json', canonical({
                'call': self.calls, 'status': status, 'request_sha256': hashlib.sha256(request).hexdigest(),
                'response_sha256': hashlib.sha256(response).hexdigest(), 'total_bytes': self.total,
                'response_possibly_capped': capped}))
            require(not capped and self.total <= MAX_TOTAL)
            self.remaining()
            answer = strict_json(response)
            require(type(answer) is dict and status in (200, 201))
            if not allow_error:
                require(not answer.get('errors'))
            return status, answer
        except BaseException as error:
            if dispatched and not received:
                self.total += MAX_RESPONSE
            self.artifacts.write(number + '-error.json', canonical({'closed': True,
                'error_type': type(error).__name__ if type(error).__module__ == 'builtins' else 'ClosedError',
                'unknown_response_allowance_spent': dispatched and not received,
                'wire_charge_scope': 'CONSERVATIVE_REQUEST_ENVELOPES_AND_REPLY_BYTES'}))
            raise ClosedError() from None

    def head(self):
        status, answer = self.api('POST', '', {'query': HEAD_QUERY, 'variables': {
            'owner': 'andersenmartin-blip', 'name': 'setisearch', 'ref': REF}}, graphql=True)
        require(status == 200)
        repository = answer.get('data', {}).get('repository', {})
        require(repository.get('id') == REPOSITORY_ID)
        return sha(repository.get('ref', {}).get('target', {}).get('oid'))

    def read_tree(self, oid, *, fresh=False):
        sha(oid)
        if not fresh and oid in self.tree_cache:
            return dict(self.tree_cache[oid])
        _, result = self.api('GET', 'git/trees/' + oid)
        require(result.get('sha') == oid and result.get('truncated') is False
                and type(result.get('tree')) is list)
        entries = {}
        for e in result['tree']:
            require(type(e) is dict and e.get('path') not in entries)
            entries[e.get('path')] = (e.get('mode'), e.get('type'), e.get('sha'))
        raw = tree_bytes(entries)
        require(git_oid('tree', raw) == oid)
        self.artifacts.write('tree-%02d.raw' % self.calls, raw)
        self.tree_cache[oid] = dict(entries)
        return entries

    def read_blob(self, oid):
        _, result = self.api('GET', 'git/blobs/' + sha(oid))
        require(result.get('sha') == oid and result.get('encoding') == 'base64')
        try:
            raw = base64.b64decode(''.join(result['content'].split()), validate=True)
        except Exception:
            raise ClosedError() from None
        require(type(result.get('size')) is int and len(raw) == result['size']
                and git_oid('blob', raw) == oid)
        self.artifacts.write('blob-%02d.raw' % self.calls, raw)
        return raw

    def read_commit(self, oid, expected_raw=None):
        _, result = self.api('GET', 'git/commits/' + sha(oid))
        require(result.get('sha') == oid)
        tree = sha(result.get('tree', {}).get('sha'))
        if oid == self.activation:
            require(type(result.get('parents')) is list
                    and [p.get('sha') for p in result['parents']] == [self.proof['preparation']])
        if expected_raw is not None:
            require(type(result.get('parents')) is list and len(result['parents']) == 1
                    and result.get('author') == IDENTITY and result.get('committer') == IDENTITY)
            parent = sha(result['parents'][0].get('sha'))
            message = result.get('message')
            require(type(message) is str)
            reconstructed = commit_bytes(tree, parent, message.rstrip('\n'))
            require(reconstructed == expected_raw and git_oid('commit', reconstructed) == oid
                    and not result.get('verification', {}).get('signature'))
            self.artifacts.write('commit-%02d.raw' % self.calls, reconstructed)
        return tree

    def source_witness(self, files):
        aliases = ['s%d' % n for n in range(len(files))]
        fields = ['%s:object(expression:%s){... on Blob{oid byteSize isBinary text}}'
            % (alias, json.dumps(self.activation + ':' + item['path']))
            for alias, item in zip(aliases, files)]
        fields += ['freeze:object(expression:%s){... on Blob{oid byteSize isBinary text}}'
            % json.dumps(self.proof['preparation'] + ':' + FREEZE_PATH),
            'marker:object(expression:%s){... on Blob{oid byteSize isBinary text}}'
            % json.dumps(self.activation + ':' + MARKER_PATH)]
        query = 'query{repository(owner:"andersenmartin-blip",name:"setisearch"){id ' + ' '.join(fields) + '}}'
        status, result = self.api('POST', '', {'query': query}, graphql=True)
        repository = result.get('data', {}).get('repository', {})
        require(status == 200 and repository.get('id') == REPOSITORY_ID)
        for alias, item in zip(aliases, files):
            blob = repository.get(alias, {})
            require(blob.get('isBinary') is False and type(blob.get('text')) is str)
            raw = blob['text'].encode('utf-8')
            require(type(blob.get('byteSize')) is int and len(raw) == blob['byteSize'] == item['bytes']
                    and git_oid('blob', raw) == sha(blob.get('oid'))
                    and hashlib.sha256(raw).hexdigest() == item['sha256'])
        for alias, path in (('freeze', FREEZE_PATH), ('marker', MARKER_PATH)):
            blob = repository.get(alias, {})
            require(blob.get('isBinary') is False and type(blob.get('text')) is str)
            raw = blob['text'].encode('utf-8')
            require(type(blob.get('byteSize')) is int and len(raw) == blob['byteSize']
                    and git_oid('blob', raw) == sha(blob.get('oid'))
                    and raw == (self.root / path).read_bytes())
            if alias == 'freeze':
                require(hashlib.sha256(raw).hexdigest() == self.expected_manifest)
            else:
                verify_marker(strict_json(raw), self.proof)

    def unique_run(self):
        _, result = self.api('GET', 'actions/runs?head_sha=' + self.activation + '&per_page=100')
        require(type(result.get('total_count')) is int and result['total_count'] <= 100
                and type(result.get('workflow_runs')) is list
                and len(result['workflow_runs']) == result['total_count'])
        matching = [r for r in result['workflow_runs'] if r.get('path') == WORKFLOW_PATH
                    and r.get('event') == 'push' and r.get('head_sha') == self.activation]
        require(len(matching) == 1 and str(matching[0].get('id')) == self.run_id
                and matching[0].get('run_attempt') == 1
                and matching[0].get('head_branch') == BRANCH)

    def candidate(self, parent, parent_tree, parent_entries, owned_entries, path, purpose):
        filename = path.split('/')[-1]
        require(path in (STATE_PATH, CONFLICT_PATH) and filename not in owned_entries)
        body = canonical({'schema': 'radio-hosted-cas-control-state-v1', 'engineering_only': True,
            'purpose': purpose, 'activation': self.activation, 'parent': parent,
            'manifest_sha256': self.expected_manifest, 'run_id': self.run_id, **FALSE_AUTHORITY})
        blob = git_oid('blob', body)
        _, result = self.api('POST', 'git/blobs', {'content': base64.b64encode(body).decode(), 'encoding': 'base64'})
        require(result.get('sha') == blob)
        owned = dict(owned_entries); owned[filename] = ('100644', 'blob', blob)
        subtree = git_oid('tree', tree_bytes(owned))
        root = dict(parent_entries); root[PREFIX] = ('040000', 'tree', subtree)
        tree = git_oid('tree', tree_bytes(root))
        _, result = self.api('POST', 'git/trees', {'base_tree': parent_tree,
            'tree': [{'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob}]})
        require(result.get('sha') == tree)
        message = 'Engineering CAS control: ' + purpose
        raw = commit_bytes(tree, parent, message)
        commit = git_oid('commit', raw)
        _, result = self.api('POST', 'git/commits', {'tree': tree, 'parents': [parent],
            'message': message + '\n', 'author': IDENTITY, 'committer': IDENTITY})
        require(result.get('sha') == commit)
        return {'oid': commit, 'raw': raw, 'tree': tree, 'root': root, 'owned': owned,
                'blob': blob, 'body': body, 'parent': parent, 'path': path}

    def immutable(self, candidate):
        require(self.read_commit(candidate['oid'], candidate['raw']) == candidate['tree'])
        root = self.read_tree(candidate['tree'], fresh=True)
        require(root == candidate['root'])
        owned = self.read_tree(root[PREFIX][2], fresh=True)
        require(owned == candidate['owned'] and self.read_blob(candidate['blob']) == candidate['body'])

    def cas(self, expected, candidate, suffix, *, negative=False):
        self.mutations += 1
        mutation_id = NAMESPACE
        status, result = self.api('POST', '', {'query': QUERY, 'variables': {'input': {
            'repositoryId': REPOSITORY_ID, 'clientMutationId': mutation_id,
            'refUpdates': [{'name': REF, 'beforeOid': expected, 'afterOid': candidate, 'force': False}]} }},
            graphql=True, allow_error=negative)
        require(status == 200)
        if negative:
            errors = result.get('errors')
            require(type(errors) is list and errors and all(type(e) is dict
                and type(e.get('message')) is str and e['message'].strip() for e in errors)
                and result.get('data') == {'updateRefs': None})
            for error in errors:
                message = error['message'].lower()
                require(type(error.get('path')) is list and 'updateRefs' in error['path']
                    and ('beforeoid' in message or ('expected' in message
                        and any(word in message for word in ('oid', 'object', 'revision')))))
            self.artifacts.write('stale-expected-error.json', canonical(result))
        else:
            require(result == {'data': {'updateRefs': {'clientMutationId': mutation_id}}})

    def run(self):
        require(not self.attempted)
        self.attempted = True
        result = None
        try:
            files = verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
            before = runtime_hashes()
            self.artifacts.write('runtime-before.json', canonical(before))
            self.artifacts.write('activation-proof.json', canonical(self.proof))
            self.unique_run()
            require(self.head() == self.activation)
            activation_tree = self.read_commit(self.activation)
            root = self.read_tree(activation_tree)
            require(PREFIX in root and root[PREFIX][:2] == ('040000', 'tree'))
            owned = self.read_tree(root[PREFIX][2])
            require('service-state.json' not in owned and 'conflict-test-state.json' not in owned)
            self.source_witness(files)
            first = self.candidate(self.activation, activation_tree, root, owned, STATE_PATH, 'accepted-cas')
            self.immutable(first)
            self.artifacts.write('accepted-candidate.json', canonical({k: v for k, v in first.items()
                if k not in ('raw', 'body')} | {'raw_commit_hex': first['raw'].hex(),
                                               'body_hex': first['body'].hex()}))
            require(self.head() == self.activation)
            self.cas(self.activation, first['oid'], 'accepted')
            self.immutable(first)
            require(self.head() == first['oid'])
            second = self.candidate(first['oid'], first['tree'], first['root'], first['owned'],
                                    CONFLICT_PATH, 'stale-expected-conflict')
            self.immutable(second)
            require(second['parent'] == first['oid'] and self.head() == first['oid'])
            self.cas(self.activation, second['oid'], 'stale', negative=True)
            require(self.head() == first['oid'])
            self.immutable(second)
            after = runtime_hashes()
            self.artifacts.write('runtime-after.json', canonical(after))
            require(before == after)
            verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
            self.remaining()
            synthetic = type(self.transport) is not HTTPSTransport
            result = {'schema': 'radio-hosted-cas-service-component-control-v1',
                'status': 'SYNTHETIC_CONTROL_ONLY' if synthetic else 'SERVICE_COMPONENT_CONTROL_PASSED',
                'domain': 'synthetic-test-fixture' if synthetic else 'authenticated-github-service',
                'actual_service_component_observed': not synthetic, 'engineering_only': True,
                'activation': self.activation, 'accepted_commit': first['oid'],
                'conflict_candidate': second['oid'], 'final_head': first['oid'],
                'stale_expected_rejected': True, 'conflict_candidate_parent': first['oid'],
                'automatic_retry': False, 'calls': self.calls, 'request_reply_bytes': self.total,
                'retained_logical_bytes': self.artifacts.logical,
                'retained_allocated_bytes': self.artifacts.allocated, **FALSE_AUTHORITY}
        except BaseException:
            result = {'schema': 'radio-hosted-cas-service-component-control-v1',
                'status': 'CLOSED_FAILED', 'attempt_spent': True, 'automatic_retry': False,
                'engineering_only': True, 'calls': self.calls,
                'mutations_attempted': self.mutations, 'mutation_may_have_landed': self.mutations > 0,
                'request_reply_bytes': self.total,
                **FALSE_AUTHORITY}
        self.artifacts.write('result.json', canonical(result))
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--activation', required=True)
    parser.add_argument('--proof', required=True)
    args = parser.parse_args()
    require(Path(args.proof).is_absolute() and Path(args.proof).is_file())
    env = os.environ
    require(env.get('GITHUB_REPOSITORY') == REPOSITORY and env.get('GITHUB_REF') == REF
            and env.get('GITHUB_EVENT_NAME') == 'push' and env.get('GITHUB_RUN_ATTEMPT') == '1'
            and env.get('GITHUB_WORKFLOW_REF') == REPOSITORY + '/' + WORKFLOW_PATH + '@' + REF
            and env.get('GITHUB_SHA') == args.activation)
    proof = strict_json(Path(args.proof).read_bytes())
    root = Path(__file__).resolve().parents[1]
    expected_manifest = hashlib.sha256((root / FREEZE_PATH).read_bytes()).hexdigest()
    control = Control(HTTPSTransport(env.get('GITHUB_TOKEN')), args.output, args.activation,
        proof, env.get('GITHUB_RUN_ID'), root, expected_manifest)
    result = control.run()
    print(result['status'])
    return 0 if result['status'] == 'SERVICE_COMPONENT_CONTROL_PASSED' else 1


if __name__ == '__main__':
    try:
        status = main()
    except BaseException:
        print('CLOSED_FAILED', file=sys.stderr)
        status = 1
    sys.exit(status)
