"""Injected synthetic integration tests; archived HTTP bytes are parser fixtures only."""
import base64
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
DEPENDENCY_PINS = {
    'scientific_runtime': (16751, 'd8a2017c96d897cfda1edeed153f3383631ed2a19c9b4622e0b06713ef384835', '64b832de609c5d4413c45adbd2f8beeed0ce8050'),
    'scientific_store': (41302, '390842d8b12aed75c76cd278585a7c59ca52d3e198181fa4930c1fee12781b76', '09dc715641745d972891ab30d06ca9a08bcf151c'),
    'test_scientific_runtime': (13585, '77faa9404e10362c2b67e8956081a03259372bf893fbcce77364613f8a47495d', '9e3efeec23f12b1c12fee6701299419eb930848d'),
    'test_scientific_store': (40899, '729e64e6e68dfcc4ed53805e64f511809cd3751df83a589a3526ef5d05fed29d', '42f0feaccef9e6cde20dc046a344f4219bb78d20')}


def checked_module(name):
    path = HERE / 'dependencies' / (name + '.py')
    raw = path.read_bytes(); count, sha, blob = DEPENDENCY_PINS[name]
    if (len(raw) != count or hashlib.sha256(raw).hexdigest() != sha
            or hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob):
        raise RuntimeError('Unchanged dependency bytes differ from independent pins')
    if name in sys.modules:
        module = sys.modules[name]
        if Path(module.__file__).resolve() != path:
            raise RuntimeError('Ambient dependency module refused')
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = checked_module('scientific_runtime')
store_module = checked_module('scientific_store')
checked_module('test_scientific_runtime')
store_fixtures = checked_module('test_scientific_store')
spec = importlib.util.spec_from_file_location('synthetic_callback', HERE / 'callback.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)

ARCHIVAL_ACK = b'{"data":{"updateRefs":{"clientMutationId":"radio-hosted-cas-control-20261004a"}}}'
ARCHIVAL_UNKNOWN = (b'{"errors":[{"message":"Something went wrong while executing your query on '
    b'2026-10-04T12:23:31Z. Please include `C7D5:37A3EE:B3BEE2:25412FB:6AC24543` when reporting this issue."}]}')


class Service:
    """Complete tiny Git object service in memory; never an actual service connection."""
    def __init__(self):
        self.trees, self.commits, self.blobs = {}, {}, {}
        blob = c.object_id('blob', b'preserve sibling\n'); self.blobs[blob] = b'preserve sibling\n'
        tree = self.put_tree({'untouched.txt': {'mode': '100644', 'type': 'blob', 'sha': blob}})
        raw = (b'tree ' + tree.encode() + b'\nauthor Fixture <fixture@example.invalid> 1 +0200\n'
            b'committer Fixture <fixture@example.invalid> 1 +0200\n'
            b'gpgsig -----BEGIN PGP SIGNATURE-----\n opaque synthetic header bytes\n'
            b' -----END PGP SIGNATURE-----\n\nsynthetic existing signed-header parent\n')
        self.head = c.object_id('commit', raw); self.commits[self.head] = raw
        self.initial = self.head
        self.http_calls, self.raw_calls, self.journal_records, self.mutations = [], [], [], []
        self.events = []; self.hook = None

    def put_tree(self, rows):
        oid = c.object_id('tree', c.tree_bytes(rows)); self.trees[oid] = copy.deepcopy(rows); return oid

    def journal(self, record):
        self.events.append(('journal', record['phase'], record['kind']))
        self.journal_records.append(copy.deepcopy(record))
        return {'sealed': True, 'record_sha256': c.pin(record)}

    def raw_reader(self, request):
        self.events.append(('raw-reader', request['commit']))
        self.raw_calls.append(copy.deepcopy(request))
        return {'sha': request['commit'], 'data': self.commits[request['commit']]}

    def http(self, request):
        self.events.append(('http', request['method'], request['path']))
        self.http_calls.append(copy.deepcopy(request))
        if self.hook:
            replacement = self.hook(request)
            if replacement is not None:
                return replacement
        return self.answer(request)

    def answer(self, request):
        method, path = request['method'], request['path']
        payload = c.parse_json(request['body']) if request['body'] else None
        if path == '/graphql':
            if payload['query'] == c.HEAD_QUERY:
                return {'status': 200, 'data': c.json_bytes({'data': {'repository': {
                    'id': c.REPOSITORY_ID, 'ref': {'target': {'oid': self.head}}}}})}
            update = payload['variables']['input']['refUpdates'][0]
            self.mutations.append(copy.deepcopy(update))
            if update['beforeOid'] != self.head:
                return {'status': 200, 'data': c.json_bytes({'errors': [{'message': 'synthetic stale head'}]})}
            self.head = update['afterOid']
            return {'status': 200, 'data': c.json_bytes({'data': {'updateRefs': {
                'clientMutationId': payload['variables']['input']['clientMutationId']}}})}
        suffix = path.split('/git/', 1)[1]; kind, _, oid = suffix.partition('/')
        status = 201 if method == 'POST' else 200
        if kind == 'trees':
            if method == 'POST':
                rows = {row['path']: {k: row[k] for k in ('mode', 'type', 'sha')} for row in payload['tree']}
                oid = self.put_tree(rows)
            result = {'sha': oid, 'truncated': False, 'tree': [{'path': name, **row}
                                for name, row in sorted(self.trees[oid].items())]}
        elif kind == 'blobs':
            if method == 'POST':
                raw = base64.b64decode(payload['content']); oid = c.object_id('blob', raw); self.blobs[oid] = raw
                result = {'sha': oid}
            else:
                raw = self.blobs[oid]
                result = {'sha': oid, 'encoding': 'base64', 'size': len(raw),
                          'content': base64.b64encode(raw).decode()}
        elif kind == 'commits' and method == 'POST':
            raw = c.candidate_raw(payload['tree'], payload['parents'][0], payload['message'].rstrip('\n'))
            oid = c.object_id('commit', raw); self.commits[oid] = raw; result = {'sha': oid}
        else:
            raise AssertionError('Unknown synthetic HTTP operation')
        return {'status': status, 'data': c.json_bytes(result)}


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.service = Service()
        self.fixture = store_fixtures.StoreTests(methodName='test_one_simulated_atomic_cas_exact_parent_delta_and_raw_readback')
        self.fixture.setUp()
        self.fixture.location['prefix'] = c.PREFIX
        self.fixture.spec['prefix'] = c.PREFIX
        self.callback = self.make_callback()
        self.store = self.make_store()

    def make_callback(self, **changes):
        args = {'domain': c.DOMAIN, 'qualification_sha256': self.fixture.spec['cas_qualification_sha256'],
                'contract': {'domain': c.DOMAIN, 'secret_free': True, 'durable_journal': True}}
        args.update(changes)
        return c.SyntheticHostedCallback(self.service.http, self.service.raw_reader, self.service.journal, **args)

    def make_store(self, callback=None):
        return store_module.ScientificGitStore(self.callback if callback is None else callback,
            runtime.canonical(self.fixture.spec), store_fixtures.pin(runtime.canonical(self.fixture.spec)),
            expected_location=self.fixture.location, raw_cas_qualification=runtime.canonical(self.fixture.law),
            expected_cas_qualification_pin=store_fixtures.pin(runtime.canonical(self.fixture.law)),
            expected_manifest_sha256=store_fixtures.pin(self.fixture.manifest)['sha256'],
            execution_verifier=self.fixture.verify_runtime)

    def publish(self, store=None, path='nested/ledger.json'):
        return (self.store if store is None else store).publish(expected_revision=self.service.head,
            relative_path=path, raw_document=self.fixture.payload, expected_document_pin=store_fixtures.pin(self.fixture.payload),
            execution_manifest=self.fixture.manifest, expected_execution_manifest_pin=store_fixtures.pin(self.fixture.manifest),
            attempt_identity=store_fixtures.identity('synthetic callback one shot'))

    def test_complete_unchanged_store_publish_is_simulation_only(self):
        receipt = self.publish().record()
        self.assertEqual(receipt['status'], 'SIMULATION_ONLY')
        self.assertEqual(receipt['domain'], c.DOMAIN)
        self.assertFalse(receipt['scientific_execution_authorized'])
        self.assertEqual(receipt['parent'], self.service.initial)
        self.assertEqual(len(self.service.mutations), 1)
        self.assertFalse(self.service.mutations[0]['force'])
        root = self.service.trees[c.commit_info(self.service.head, self.service.commits[self.service.head])['tree']]
        self.assertIn('untouched.txt', root)
        for index, event in enumerate(self.service.events):
            if event[0] in ('http', 'raw-reader'):
                self.assertEqual(self.service.events[index - 1][0:2], ('journal', 'before-dispatch'))

    def test_default_and_public_domains_refuse_before_any_callback(self):
        for domain in (None, 'public-scientific-evidence', 'prospective-component'):
            with self.assertRaises(c.ClosedError):
                self.make_callback(domain=domain)
        self.assertFalse(self.service.http_calls + self.service.raw_calls + self.service.journal_records)

    def test_actual_archival_bytes_are_parser_fixtures_not_qualification(self):
        self.assertEqual(hashlib.sha256(ARCHIVAL_ACK).hexdigest(), '8010ab6c7b6f641c1911ff01106d2a64eb15d048a2cf100c849cd87c7d75c9fb')
        self.assertTrue(c.successful_ack(200, ARCHIVAL_ACK, 'radio-hosted-cas-control-20261004a'))
        self.assertEqual(hashlib.sha256(ARCHIVAL_UNKNOWN).hexdigest(), '0fdcdfc887993a87d06d9e6ec74de144fedbc7a8a401bc0e29fa6d234c9bc9ae')
        with self.assertRaises(c.ClosedError):
            c.successful_ack(200, ARCHIVAL_UNKNOWN, 'radio-hosted-cas-control-20261004a')

    def test_actual_generic_error_spends_callback_and_store_without_retry(self):
        def hook(request):
            if request['path'] == '/graphql' and c.parse_json(request['body'])['query'] == c.QUERY:
                return {'status': 200, 'data': ARCHIVAL_UNKNOWN}
        self.service.hook = hook
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertTrue(self.callback.stopped and self.store.stopped)
        calls = len(self.service.http_calls)
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertEqual(len(self.service.http_calls), calls)
        self.assertEqual(self.service.head, self.service.initial)

    def test_signed_parent_original_raw_bytes_are_verified_without_rest_guessing(self):
        result = self.callback('read_commit', {'repository': c.REPOSITORY, 'commit': self.service.initial})
        self.assertIn(b'gpgsig ', result['data'])
        self.assertIn(b' +0200', result['data'])
        self.assertFalse(self.service.http_calls)
        self.assertEqual(c.object_id('commit', result['data']), self.service.initial)

    def test_bad_original_raw_commit_is_rejected_and_spent(self):
        self.service.commits[self.service.initial] += b'changed'
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertTrue(self.callback.stopped and self.store.stopped)
        self.assertFalse(self.service.mutations)

    def test_undeclared_root_delta_is_rejected_before_cas(self):
        original = self.service.answer
        def answer(request):
            value = original(request)
            if request['method'] == 'GET' and '/trees/' in request['path']:
                result = c.parse_json(value['data'])
                result['tree'].append({'path': 'unowned.txt', 'mode': '100644', 'type': 'blob', 'sha': 'a' * 40})
                value['data'] = c.json_bytes(result)
            return value
        self.service.answer = answer
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertFalse(self.service.mutations)

    def test_bad_blob_and_wrong_new_raw_commit_stop_before_cas(self):
        for case in ('blob', 'commit'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'blob':
                    original = self.service.answer
                    def answer(request):
                        value = original(request)
                        if request['method'] == 'GET' and '/blobs/' in request['path']:
                            result = c.parse_json(value['data']); result['content'] = base64.b64encode(b'wrong').decode()
                            value['data'] = c.json_bytes(result)
                        return value
                    self.service.answer = answer
                else:
                    original = self.service.raw_reader
                    def reader(request):
                        value = original(request)
                        if request['commit'] != self.service.initial:
                            value['data'] += b'wrong'
                        return value
                    self.callback._reader = reader
                with self.assertRaises(store_module.Stopped):
                    self.publish()
                self.assertFalse(self.service.mutations)

    def test_scope_escape_and_executable_mode_stop_before_http(self):
        for path, mode in ((c.PREFIX + '/../other.json', '100644'), ('outside/file.json', '100644'),
                           (c.PREFIX + '/native.py', '100755')):
            callback = self.make_callback()
            with self.assertRaises(c.ClosedError):
                callback('create_candidate', {'repository': c.REPOSITORY, 'parent': self.service.head,
                    'files': [{'path': path, 'mode': mode, 'data': b'{}'}], 'attempt_identity': 'a' * 64})
        self.assertFalse(self.service.http_calls + self.service.raw_calls)

    def test_ack_extras_and_candidate_parameter_replacement_are_rejected(self):
        def hook(request):
            if request['path'] == '/graphql' and c.parse_json(request['body'])['query'] == c.QUERY:
                answer = self.service.answer(request); value = c.parse_json(answer['data'])
                value['extra'] = 'unknown'; answer['data'] = c.json_bytes(value); return answer
        self.service.hook = hook
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertEqual(len(self.service.mutations), 1)
        self.setUp()
        made = self.callback('create_candidate', {'repository': c.REPOSITORY, 'parent': self.service.head,
            'files': [{'path': c.PREFIX + '/state.json', 'mode': '100644', 'data': b'{}'}], 'attempt_identity': 'a' * 64})
        with self.assertRaises(c.ClosedError):
            self.callback('atomic_ref_compare_and_swap', {'repository': c.REPOSITORY, 'branch': c.BRANCH,
                'expected_revision': self.service.initial, 'candidate': 'b' * 40,
                'qualification_sha256': self.fixture.spec['cas_qualification_sha256']})
        self.assertFalse(self.service.mutations)

    def test_mutated_params_request_and_witness_are_detected(self):
        for case in ('params', 'request', 'contract'):
            with self.subTest(case=case):
                self.setUp(); params = {'repository': c.REPOSITORY, 'branch': c.BRANCH}
                def hook(request):
                    if case == 'params':
                        params['branch'] = 'changed'
                    elif case == 'request':
                        request['body'] = b'changed'
                    else:
                        self.callback._source_contract['secret_free'] = False
                self.service.hook = hook
                with self.assertRaises(c.ClosedError):
                    self.callback('read_ref', params)
                self.assertTrue(self.callback.stopped)
                self.assertEqual(len(self.service.http_calls), 1)

    def test_response_and_request_ceiling_stop_without_later_dispatch(self):
        self.service.hook = lambda _: {'status': 200, 'data': b'x' * ((2 << 20) + 1)}
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        self.assertTrue(self.callback.stopped)
        self.setUp(); self.callback = self.make_callback(limits={**c.LIMITS, 'requests': 1})
        self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        self.assertEqual(len(self.service.http_calls), 1)

    def test_tagged_snapshot_distinguishes_bytes_from_lookalike_dictionary(self):
        self.assertNotEqual(c.pin(b'abc'), c.pin({'bytes': '616263'}))
        self.assertNotEqual(c.pin({'x': [b'abc']}), c.pin({'x': [{'bytes': '616263'}]}))

    def test_pinned_regular_checkpoint_update_preserves_siblings(self):
        self.publish()
        path = c.PREFIX + '/nested/ledger.json'
        old_blob = c.object_id('blob', self.fixture.payload)
        self.callback = self.make_callback(allowed_updates={path: old_blob}); self.store = self.make_store()
        self.fixture.payload = runtime.canonical({'fixture': 'one pinned replacement'})
        receipt = self.publish().record()
        self.assertEqual(receipt['status'], 'SIMULATION_ONLY')
        self.assertEqual(receipt['blob'], c.object_id('blob', self.fixture.payload))
        self.assertEqual(len(self.service.mutations), 2)
        self.callback = self.make_callback(); self.store = self.make_store()
        with self.assertRaises(store_module.Stopped):
            self.publish()
        self.assertEqual(len(self.service.mutations), 2)

    def test_missing_journal_ack_prevents_first_dispatch(self):
        self.callback._journal = lambda _: {'sealed': False, 'record_sha256': '0' * 64}
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        self.assertFalse(self.service.http_calls + self.service.raw_calls)

    def test_integer_boolean_contract_and_journal_substitution_refused(self):
        with self.assertRaises(c.ClosedError):
            self.make_callback(contract={'domain': c.DOMAIN, 'secret_free': 1, 'durable_journal': True})
        self.callback._journal = lambda record: {'sealed': 1, 'record_sha256': c.pin(record)}
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
        self.assertFalse(self.service.http_calls)

    def test_metadata_and_private_configuration_drift_spend_instance(self):
        for case in ('metadata', 'limits', 'qualification'):
            with self.subTest(case=case):
                self.setUp(); original = dict(c.IDENTITY)
                def hook(request):
                    if case == 'metadata':
                        c.IDENTITY['name'] += ' changed'
                    elif case == 'limits':
                        self.callback._limits['requests'] += 1
                    else:
                        self.callback._qualification = 'b' * 64
                self.service.hook = hook
                try:
                    with self.assertRaises(c.ClosedError):
                        self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
                finally:
                    c.IDENTITY.clear(); c.IDENTITY.update(original)

    def test_present_empty_errors_field_is_not_success(self):
        def hook(request):
            result = self.service.answer(request); value = c.parse_json(result['data'])
            value['errors'] = None; result['data'] = c.json_bytes(value); return result
        self.service.hook = hook
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})

    def test_reentrant_callback_cannot_clear_outer_argument_witness(self):
        params = {'repository': c.REPOSITORY, 'branch': c.BRANCH}
        entered = False
        def hook(request):
            nonlocal entered
            if not entered:
                entered = True
                try:
                    self.callback('read_ref', {'repository': c.REPOSITORY, 'branch': c.BRANCH})
                except c.ClosedError:
                    pass
                params['branch'] = 'changed after nested callback'
        self.service.hook = hook
        with self.assertRaises(c.ClosedError):
            self.callback('read_ref', params)
        self.assertTrue(self.callback.stopped)
        self.assertEqual(len(self.service.http_calls), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
