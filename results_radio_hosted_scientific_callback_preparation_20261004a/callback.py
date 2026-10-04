"""Inert synthetic callback integration; no network, credentials or certificate producer.

Six exact ScientificGitStore operations are mapped through caller-injected HTTP,
original raw Git bytes and journal callbacks. Every failure permanently stops this
instance. Production and omitted domains refuse before any injected call.
"""
import base64
import copy
import datetime
import hashlib
import json
import re

REPOSITORY = 'andersenmartin-blip/setisearch'
REPOSITORY_ID = 'R_kgDOT558WQ'
BRANCH = 'm43-support-qualification'
REF = 'refs/heads/' + BRANCH
PREFIX = 'results_radio_scientific_callback_preparation_20261004a'
NAMESPACE = 'radio-hosted-scientific-callback-preparation-20261004a'
DOMAIN = 'synthetic-test-fixture'
QUERY = 'mutation($input:UpdateRefsInput!){updateRefs(input:$input){clientMutationId}}'
HEAD_QUERY = ('query($owner:String!,$name:String!,$ref:String!){repository(owner:$owner,'
              'name:$name){id ref(qualifiedName:$ref){target{oid}}}}')
LIMITS = {'requests': 100, 'response_bytes': 2 << 20, 'wire_bytes': 8 << 20,
          'retained_bytes': 8 << 20, 'external_callbacks': 400, 'operations': 100}
DATE = '2026-10-04T00:00:00Z'
IDENTITY = {'name': 'SETI synthetic callback fixture',
            'email': 'synthetic-fixture@example.invalid', 'date': DATE}


class ClosedError(Exception):
    """Fixed diagnostics contain no external response or exception text."""


def require(condition):
    if not condition:
        raise ClosedError()


def hex_id(value, length=40):
    require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None)
    return value


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def tagged_bytes(value):
    def tag(item):
        kind = type(item)
        if kind is dict:
            require(all(type(k) is str for k in item))
            return ['dict', [[k, tag(item[k])] for k in sorted(item)]]
        if kind is list:
            return ['list', [tag(x) for x in item]]
        if kind is bytes:
            return ['bytes', item.hex()]
        if kind in (str, bool, int) or item is None:
            return [kind.__name__, item]
        raise ClosedError()
    return json_bytes(tag(value))


def pin(value):
    return hashlib.sha256(tagged_bytes(value)).hexdigest()


def parse_json(raw):
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


def object_id(kind, raw):
    require(type(raw) is bytes)
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def safe_path(path):
    require(type(path) is str and path and len(path) <= 4096 and '\\' not in path
            and not path.startswith('/') and all(ord(x) >= 32 for x in path)
            and all(x not in ('', '.', '..') for x in path.split('/')))
    return path


def commit_info(oid, raw):
    require(0 < len(raw) <= 65536 and object_id('commit', raw) == hex_id(oid) and b'\n\n' in raw)
    headers = raw.split(b'\n\n', 1)[0].split(b'\n')
    trees = [r[5:].decode('ascii') for r in headers if r.startswith(b'tree ')]
    parents = [r[7:].decode('ascii') for r in headers if r.startswith(b'parent ')]
    require(len(trees) == 1 and sum(r.startswith(b'author ') for r in headers) == 1
            and sum(r.startswith(b'committer ') for r in headers) == 1)
    return {'tree': hex_id(trees[0]), 'parents': [hex_id(p) for p in parents]}


def tree_bytes(rows):
    modes = {'040000': 'tree', '100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'}
    for name, row in rows.items():
        require('/' not in safe_path(name) and set(row) == {'mode', 'type', 'sha'}
                and modes.get(row['mode']) == row['type'])
        hex_id(row['sha'])
    names = sorted(rows, key=lambda n: (n + ('/' if rows[n]['type'] == 'tree' else '')).encode())
    return b''.join(rows[n]['mode'].lstrip('0').encode() + b' ' + n.encode()
                    + b'\0' + bytes.fromhex(rows[n]['sha']) for n in names)


def candidate_raw(tree, parent, message):
    epoch = int(datetime.datetime.fromisoformat(DATE.replace('Z', '+00:00')).timestamp())
    person = '%s <%s> %d +0000' % (IDENTITY['name'], IDENTITY['email'], epoch)
    return ('tree %s\nparent %s\nauthor %s\ncommitter %s\n\n%s\n'
            % (hex_id(tree), hex_id(parent), person, person, message)).encode()


def successful_ack(status, raw, mutation_id):
    """Shape parser only; applying it to archival bytes creates no service qualification."""
    require(type(status) is int and status == 200 and type(raw) is bytes)
    require(parse_json(raw) == {'data': {'updateRefs': {'clientMutationId': mutation_id}}})
    return True


def constants():
    return {name: globals()[name] for name in ('REPOSITORY', 'REPOSITORY_ID', 'BRANCH', 'REF',
        'PREFIX', 'NAMESPACE', 'DOMAIN', 'QUERY', 'HEAD_QUERY', 'LIMITS', 'DATE', 'IDENTITY')}


_CONSTANTS_PIN = pin(constants())


class SyntheticHostedCallback:
    def __init__(self, http=None, raw_commit_reader=None, journal=None, *, domain=None,
                 qualification_sha256=None, contract=None, allowed_updates=None, limits=None):
        require(type(domain) is str and domain == DOMAIN and pin(constants()) == _CONSTANTS_PIN
                and all(callable(x) for x in (http, raw_commit_reader, journal)))
        require(type(contract) is dict and tagged_bytes(contract) == tagged_bytes(
            {'domain': DOMAIN, 'secret_free': True, 'durable_journal': True}))
        qualification_sha256 = hex_id(qualification_sha256, 64)
        limits = copy.deepcopy(LIMITS if limits is None else limits)
        require(type(limits) is dict and set(limits) == set(LIMITS)
                and all(type(limits[k]) is int and 0 < limits[k] <= LIMITS[k] for k in limits))
        allowed_updates = {} if allowed_updates is None else allowed_updates
        require(type(allowed_updates) is dict)
        for path, oid in allowed_updates.items():
            require(safe_path(path).startswith(PREFIX + '/'))
            hex_id(oid)
        self._http, self._reader, self._journal = http, raw_commit_reader, journal
        self._source_contract, self._source_updates = contract, allowed_updates
        self._source_pin = pin({'contract': contract, 'updates': allowed_updates})
        self._updates, self._limits = copy.deepcopy(allowed_updates), limits
        self._qualification = qualification_sha256
        self._constants_pin = _CONSTANTS_PIN
        self._configuration_pin = pin({'updates': self._updates, 'limits': self._limits,
                                       'qualification': self._qualification})
        self.stopped = False
        self.requests = self.external_callbacks = self.operations = 0
        self.wire_bytes = self.retained_bytes = 0
        self.records = []
        self._candidate = None
        self._candidate_pin = pin(None)
        self._cas_attempted = False
        self._active = None

    def _unchanged(self):
        require(not self.stopped and pin(constants()) == self._constants_pin)
        require(pin({'updates': self._updates, 'limits': self._limits,
                     'qualification': self._qualification}) == self._configuration_pin)
        require(pin({'contract': self._source_contract, 'updates': self._source_updates}) == self._source_pin)
        require(pin(self._candidate) == self._candidate_pin)
        if self._active is not None:
            require(pin(self._active[0]) == self._active[1])

    def _external(self, function, request, *, kind):
        self._unchanged()
        require(self.external_callbacks < self._limits['external_callbacks'])
        self.external_callbacks += 1
        frozen = copy.deepcopy(request); expected = pin(frozen)
        result = function(frozen)
        self._unchanged()
        require(pin(frozen) == expected)
        require(type(result) is dict)
        if kind == 'http':
            require(set(result) == {'status', 'data'} and type(result['status']) is int
                    and type(result['data']) is bytes
                    and len(result['data']) <= self._limits['response_bytes'])
        elif kind == 'raw-reader':
            require(set(result) == {'sha', 'data'} and type(result['data']) is bytes
                    and 0 < len(result['data']) <= 65536)
            hex_id(result['sha'])
        else:
            require(set(result) == {'sealed', 'record_sha256'} and result['sealed'] is True)
            hex_id(result['record_sha256'], 64)
        tagged_bytes(result)
        return copy.deepcopy(result)

    def _seal(self, phase, kind, raw):
        record = {'ordinal': len(self.records), 'phase': phase, 'kind': kind,
                  'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw}
        charge = len(tagged_bytes(record))
        require(self.retained_bytes + charge <= self._limits['retained_bytes'])
        answer = self._external(self._journal, record, kind='journal')
        require(tagged_bytes(answer) == tagged_bytes({'sealed': True, 'record_sha256': pin(record)}))
        self.records.append(copy.deepcopy(record)); self.retained_bytes += charge

    def _http_call(self, method, suffix, payload=None, *, graphql=False):
        require(self.requests < self._limits['requests'])
        path = '/graphql' if graphql else '/repos/' + REPOSITORY + '/git/' + suffix
        body = b'' if payload is None else json_bytes(payload)
        request = {'method': method, 'path': path, 'body': body}
        raw_request = tagged_bytes(request)
        require(self.wire_bytes + len(raw_request) + self._limits['response_bytes'] <= self._limits['wire_bytes'])
        self._seal('before-dispatch', 'http-request', raw_request)
        self.requests += 1; self.wire_bytes += len(raw_request)
        try:
            answer = self._external(self._http, request, kind='http')
        except BaseException:
            self.wire_bytes += self._limits['response_bytes']
            self._seal('closed-failure', 'http-unknown-reply', b'AMBIGUOUS_HTTP_CALL')
            raise
        require(type(answer) is dict and set(answer) == {'status', 'data'}
                and type(answer['status']) is int and type(answer['data']) is bytes)
        raw = answer['data']; self.wire_bytes += len(raw)
        require(len(raw) <= self._limits['response_bytes'] and self.wire_bytes <= self._limits['wire_bytes'])
        self._seal('after-reply', 'http-response', tagged_bytes(answer))
        value = parse_json(raw)
        require(type(value) is dict and answer['status'] in (200, 201) and 'errors' not in value)
        return answer['status'], value, raw

    def _read_commit(self, oid):
        request = {'repository': REPOSITORY, 'commit': hex_id(oid)}
        self._seal('before-dispatch', 'raw-git-request', tagged_bytes(request))
        answer = self._external(self._reader, request, kind='raw-reader')
        require(type(answer) is dict and set(answer) == {'sha', 'data'} and answer['sha'] == oid
                and type(answer['data']) is bytes)
        self._seal('after-reply', 'raw-git-response', tagged_bytes(answer))
        commit_info(oid, answer['data'])
        return answer

    def _read_tree(self, oid):
        _, value, _ = self._http_call('GET', 'trees/' + hex_id(oid))
        require(value.get('sha') == oid and value.get('truncated') is False and type(value.get('tree')) is list)
        rows = {}
        for row in value['tree']:
            require(type(row) is dict and row.get('path') not in rows)
            rows[row.get('path')] = {k: row.get(k) for k in ('mode', 'type', 'sha')}
        require(object_id('tree', tree_bytes(rows)) == oid)
        return rows

    def _blob(self, oid):
        _, value, _ = self._http_call('GET', 'blobs/' + hex_id(oid))
        require(value.get('sha') == oid and value.get('encoding') == 'base64')
        try:
            raw = base64.b64decode(''.join(value['content'].split()), validate=True)
        except Exception:
            raise ClosedError() from None
        require(type(value.get('size')) is int and len(raw) == value['size'] and object_id('blob', raw) == oid)
        return raw

    def _edit(self, prior_oid, parts, blob, path):
        rows = {} if prior_oid is None else self._read_tree(prior_oid)
        first = parts[0]; old = rows.get(first)
        if len(parts) == 1:
            if old is not None:
                require(old == {'mode': '100644', 'type': 'blob', 'sha': self._updates.get(path)})
            else:
                require(path not in self._updates)
            rows[first] = {'mode': '100644', 'type': 'blob', 'sha': blob}
        else:
            require(old is None or (old['mode'], old['type']) == ('040000', 'tree'))
            subtree = self._edit(None if old is None else old['sha'], parts[1:], blob, path)
            rows[first] = {'mode': '040000', 'type': 'tree', 'sha': subtree}
        oid = object_id('tree', tree_bytes(rows))
        _, made, _ = self._http_call('POST', 'trees', {'tree': [{'path': name, **row}
                                                            for name, row in sorted(rows.items())]})
        require(made.get('sha') == oid and self._read_tree(oid) == rows)
        return oid

    def _create(self, params):
        require(self._candidate is None and type(params['files']) is list and len(params['files']) == 1)
        item = params['files'][0]
        require(type(item) is dict and set(item) == {'path', 'mode', 'data'} and item['mode'] == '100644'
                and type(item['data']) is bytes and len(item['data']) <= self._limits['response_bytes'])
        path = safe_path(item['path']); require(path.startswith(PREFIX + '/'))
        parent = hex_id(params['parent']); hex_id(params['attempt_identity'], 64)
        parent_info = commit_info(parent, self._read_commit(parent)['data'])
        blob = object_id('blob', item['data'])
        _, made, _ = self._http_call('POST', 'blobs', {'encoding': 'base64',
            'content': base64.b64encode(item['data']).decode()})
        require(made.get('sha') == blob and self._blob(blob) == item['data'])
        tree = self._edit(parent_info['tree'], path.split('/'), blob, path)
        message = 'Synthetic callback preparation ' + params['attempt_identity']
        raw = candidate_raw(tree, parent, message); oid = object_id('commit', raw)
        _, made, _ = self._http_call('POST', 'commits', {'tree': tree, 'parents': [parent],
            'author': IDENTITY, 'committer': IDENTITY, 'message': message + '\n'})
        require(made.get('sha') == oid and self._read_commit(oid)['data'] == raw)
        self._candidate = {'commit': oid, 'tree': tree, 'parent': parent, 'path': path,
                           'blob': blob, 'data': item['data'], 'raw_commit': raw}
        self._candidate_pin = pin(self._candidate)
        return {'commit': oid, 'tree': tree}

    def _head(self):
        status, value, _ = self._http_call('POST', '', {'query': HEAD_QUERY, 'variables': {
            'owner': 'andersenmartin-blip', 'name': 'setisearch', 'ref': REF}}, graphql=True)
        repository = value.get('data', {}).get('repository', {})
        require(status == 200 and repository.get('id') == REPOSITORY_ID)
        return hex_id(repository.get('ref', {}).get('target', {}).get('oid'))

    def _immutable(self, params):
        oid, path = hex_id(params['commit']), safe_path(params['path'])
        require(path.startswith(PREFIX + '/'))
        root = commit_info(oid, self._read_commit(oid)['data'])['tree']; tree = root
        parts = path.split('/')
        for part in parts[:-1]:
            row = self._read_tree(tree).get(part)
            require(row is not None and (row['mode'], row['type']) == ('040000', 'tree'))
            tree = row['sha']
        row = self._read_tree(tree).get(parts[-1])
        require(row is not None and (row['mode'], row['type']) == ('100644', 'blob'))
        raw = self._blob(row['sha'])
        return {'repository': REPOSITORY, 'commit': oid, 'tree': root, 'path': path,
                'mode': '100644', 'blob': row['sha'], 'bytes': len(raw), 'data': raw}

    def invoke(self, method, params):
        require(not self.stopped)
        if self._active is not None:
            self.stopped = True
            raise ClosedError()
        try:
            schemas = {'read_ref': {'repository', 'branch'}, 'read_commit': {'repository', 'commit'},
                'read_tree': {'repository', 'tree'}, 'read_immutable_file': {'repository', 'commit', 'path'},
                'create_candidate': {'repository', 'parent', 'files', 'attempt_identity'},
                'atomic_ref_compare_and_swap': {'repository', 'branch', 'expected_revision', 'candidate', 'qualification_sha256'}}
            require(type(method) is str and type(params) is dict and method in schemas and set(params) == schemas[method]
                    and params['repository'] == REPOSITORY and self.operations < self._limits['operations'])
            self.operations += 1
            self._active = (params, pin(params)); self._unchanged(); frozen = copy.deepcopy(params)
            if 'branch' in frozen:
                require(frozen['branch'] == BRANCH)
            if method == 'read_ref':
                result = {'repository': REPOSITORY, 'branch': BRANCH, 'commit': self._head()}
            elif method == 'read_commit':
                result = self._read_commit(frozen['commit'])
            elif method == 'read_tree':
                rows = self._read_tree(frozen['tree'])
                result = {'sha': frozen['tree'], 'truncated': False,
                          'tree': [{'path': p, **r} for p, r in sorted(rows.items())]}
            elif method == 'create_candidate':
                result = self._create(frozen)
            elif method == 'read_immutable_file':
                result = self._immutable(frozen)
            else:
                require(not self._cas_attempted and self._candidate is not None
                        and hex_id(frozen['expected_revision']) == self._candidate['parent']
                        and hex_id(frozen['candidate']) == self._candidate['commit']
                        and hex_id(frozen['qualification_sha256'], 64) == self._qualification)
                self._cas_attempted = True
                status, _, raw = self._http_call('POST', '', {'query': QUERY, 'variables': {'input': {
                    'repositoryId': REPOSITORY_ID, 'clientMutationId': NAMESPACE,
                    'refUpdates': [{'name': REF, 'beforeOid': frozen['expected_revision'],
                        'afterOid': frozen['candidate'], 'force': False}]}}}, graphql=True)
                successful_ack(status, raw, NAMESPACE)
                result = {'repository': REPOSITORY, 'branch': BRANCH,
                    'expected_revision': frozen['expected_revision'], 'commit': frozen['candidate'],
                    'atomic': True, 'accepted': True}
            self._unchanged(); self._active = None
            return copy.deepcopy(result)
        except BaseException:
            self.stopped = True
            raise ClosedError() from None

    __call__ = invoke
