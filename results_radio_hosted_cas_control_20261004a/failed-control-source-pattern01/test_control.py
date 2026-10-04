"""Focused injected-service tests; no credentials and no network are used."""
import base64
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('engineering_control', Path(__file__).with_name('control.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class Service:
    synthetic = True

    def __init__(self, root, run_id='123'):
        self.head = 'a' * 40
        self.activation = self.head
        self.preparation = 'b' * 40
        self.run_id = run_id
        self.files = []
        self.blobs = {}
        owned = {}
        for path in c.SOURCE_PATHS:
            name = path.split('/')[-1]
            raw = ('synthetic frozen ' + path + '\n').encode()
            local = root / path
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(raw)
            blob = c.git_oid('blob', raw)
            self.blobs[blob] = raw
            if path.startswith(c.PREFIX + '/'):
                owned[name] = ('100644', 'blob', blob)
            self.files.append({'path': path, 'bytes': len(raw),
                               'sha256': hashlib.sha256(raw).hexdigest()})
        owned_oid = c.git_oid('tree', c.tree_bytes(owned))
        self.root_entries = {c.PREFIX: ('040000', 'tree', owned_oid),
                             'untouched.txt': ('100644', 'blob', 'c' * 40)}
        self.root_oid = c.git_oid('tree', c.tree_bytes(self.root_entries))
        self.trees = {owned_oid: owned, self.root_oid: self.root_entries}
        self.commits = {self.head: {'sha': self.head, 'tree': {'sha': self.root_oid},
                                  'parents': [{'sha': self.preparation}]}}
        self.sources = {f['path']: (root / f['path']).read_bytes() for f in self.files}
        freeze = c.canonical({'schema': 'radio-hosted-cas-control-freeze-v1', 'namespace': c.NAMESPACE,
            'repository': c.REPOSITORY, 'branch': c.BRANCH, 'source_files': self.files, 'limits': c.LIMITS})
        (root / c.FREEZE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (root / c.FREEZE_PATH).write_bytes(freeze)
        self.proof = {'schema': 'radio-hosted-cas-control-activation-proof-v1',
            'repository': c.REPOSITORY, 'branch': c.BRANCH, 'namespace': c.NAMESPACE,
            'activation': self.activation, 'preparation': self.preparation,
            'manifest_sha256': hashlib.sha256(freeze).hexdigest(), 'run_id': run_id,
            'source_files': copy.deepcopy(self.files)}
        marker = c.canonical({'schema': 'radio-hosted-cas-control-activation-v1',
            'namespace': c.NAMESPACE, 'repository': c.REPOSITORY, 'branch': c.BRANCH,
            'preparation': self.preparation, 'manifest_sha256': self.proof['manifest_sha256'],
            'source_readback_sha256': c.manifest_sha256(self.files),
            'allocation': {'identity': c.NAMESPACE, 'wall_seconds': 300,
                           'retained_bytes': 20971520, 'attempts': 1}})
        (root / c.MARKER_PATH).write_bytes(marker)
        self.sources[c.FREEZE_PATH] = freeze
        self.sources[c.MARKER_PATH] = marker
        self.requests = []
        self.mutations = []
        self.hook = None

    def contains_secret(self, raw):
        return b'synthetic-test-secret' in raw

    def __call__(self, method, path, raw, timeout):
        request = c.strict_json(raw) if raw else None
        self.requests.append((method, path, copy.deepcopy(request)))
        require_timeout = 0 < timeout <= 30
        if not require_timeout:
            raise AssertionError('bounded timeout')
        if self.hook:
            overridden = self.hook(method, path, request)
            if overridden is not None:
                return overridden
        result, status = self.answer(method, path, request)
        return status, c.canonical(result)

    def answer(self, method, path, payload):
        if '/actions/runs?' in path:
            return {'total_count': 1, 'workflow_runs': [{'path': c.WORKFLOW_PATH,
                'event': 'push', 'head_sha': self.activation, 'id': int(self.run_id),
                'run_attempt': 1, 'head_branch': c.BRANCH}]}, 200
        if path == '/graphql':
            if payload['query'] == c.HEAD_QUERY:
                return {'data': {'repository': {'id': c.REPOSITORY_ID,
                        'ref': {'target': {'oid': self.head}}}}}, 200
            if payload['query'] == c.QUERY:
                args = payload['variables']['input']
                update = args['refUpdates'][0]
                self.mutations.append(copy.deepcopy(update))
                if update['beforeOid'] != self.head:
                    return {'data': {'updateRefs': None}, 'errors': [{'message':
                        'Expected beforeOid %s but current ref oid is %s' % (update['beforeOid'], self.head),
                        'path': ['updateRefs']}]}, 200
                self.head = update['afterOid']
                return {'data': {'updateRefs': {'clientMutationId': args['clientMutationId']}}}, 200
            repository = {'id': c.REPOSITORY_ID}
            for n, file in enumerate(self.files):
                raw = self.sources[file['path']]
                repository['s%d' % n] = {'oid': c.git_oid('blob', raw), 'byteSize': len(raw),
                                         'isBinary': False, 'text': raw.decode()}
            for alias, path in (('freeze', c.FREEZE_PATH), ('marker', c.MARKER_PATH)):
                raw = self.sources[path]
                repository[alias] = {'oid': c.git_oid('blob', raw), 'byteSize': len(raw),
                                     'isBinary': False, 'text': raw.decode()}
            return {'data': {'repository': repository}}, 200
        suffix = path.split('/git/', 1)[1]
        kind, _, oid = suffix.partition('/')
        if method == 'GET' and kind == 'commits':
            return copy.deepcopy(self.commits[oid]), 200
        if method == 'GET' and kind == 'trees':
            return {'sha': oid, 'truncated': False, 'tree': [
                {'path': name, 'mode': mode, 'type': kind, 'sha': sha}
                for name, (mode, kind, sha) in self.trees[oid].items()]}, 200
        if method == 'GET' and kind == 'blobs':
            raw = self.blobs[oid]
            return {'sha': oid, 'size': len(raw), 'encoding': 'base64',
                    'content': base64.b64encode(raw).decode()}, 200
        if method == 'POST' and kind == 'blobs':
            raw = base64.b64decode(payload['content'])
            oid = c.git_oid('blob', raw)
            self.blobs[oid] = raw
            return {'sha': oid}, 201
        if method == 'POST' and kind == 'trees':
            root = copy.deepcopy(self.trees[payload['base_tree']])
            one = payload['tree'][0]
            directory, filename = one['path'].split('/')
            owned = copy.deepcopy(self.trees[root[directory][2]])
            owned[filename] = (one['mode'], one['type'], one['sha'])
            owned_oid = c.git_oid('tree', c.tree_bytes(owned))
            self.trees[owned_oid] = owned
            root[directory] = ('040000', 'tree', owned_oid)
            oid = c.git_oid('tree', c.tree_bytes(root))
            self.trees[oid] = root
            return {'sha': oid}, 201
        if method == 'POST' and kind == 'commits':
            raw = c.commit_bytes(payload['tree'], payload['parents'][0], payload['message'].rstrip('\n'))
            oid = c.git_oid('commit', raw)
            self.commits[oid] = {'sha': oid, 'tree': {'sha': payload['tree']},
                'parents': [{'sha': p} for p in payload['parents']], 'message': payload['message'],
                'author': copy.deepcopy(payload['author']), 'committer': copy.deepcopy(payload['committer']),
                'verification': {'signature': None}}
            return {'sha': oid}, 201
        raise AssertionError('unexpected service operation')


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = Service(self.root)

    def control(self, **overrides):
        args = {'transport': self.service, 'output': str(self.root / 'fresh-output'),
                'activation': self.service.activation, 'proof': self.service.proof,
                'run_id': self.service.run_id, 'root': self.root,
                'expected_manifest': self.service.proof['manifest_sha256']}
        args.update(overrides)
        return c.Control(**args)

    def test_success_discriminates_stale_beforeoid_from_ancestry(self):
        control = self.control()
        result = control.run()
        self.assertEqual(result['status'], 'SYNTHETIC_CONTROL_ONLY')
        self.assertFalse(result['actual_service_component_observed'])
        self.assertFalse(result['scientific_store_qualified'])
        self.assertEqual(len(self.service.mutations), 2)
        accepted, stale = self.service.mutations
        self.assertEqual(accepted['beforeOid'], self.service.activation)
        self.assertEqual(stale['beforeOid'], self.service.activation)
        self.assertEqual(self.service.commits[stale['afterOid']]['parents'],
                         [{'sha': accepted['afterOid']}])
        self.assertEqual(self.service.head, accepted['afterOid'])
        self.assertTrue(all(m['force'] is False for m in self.service.mutations))
        self.assertLessEqual(control.calls, 40)
        self.assertTrue((control.artifacts.path / 'accepted-candidate.json').is_file())
        self.assertTrue((control.artifacts.path / 'stale-expected-error.json').is_file())
        with self.assertRaises(c.ClosedError):
            control.run()

    def test_ambiguous_positive_ack_never_retries_or_conflict_tests(self):
        def hook(method, path, payload):
            if path == '/graphql' and payload['query'] == c.QUERY:
                result, status = self.service.answer(method, path, payload)
                return status, c.canonical({'data': result['data'], 'extra': 'unknown'})
        self.service.hook = hook
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(len(self.service.mutations), 1)
        self.assertTrue((self.root / 'fresh-output/accepted-candidate.json').is_file())

    def test_negative_transport_failure_cannot_be_evidence(self):
        def hook(method, path, payload):
            if path == '/graphql' and payload['query'] == c.QUERY and self.service.mutations:
                raise OSError('untrusted diagnostic synthetic-test-secret')
        self.service.hook = hook
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(len(self.service.mutations), 1)
        self.assertFalse((self.root / 'fresh-output/stale-expected-error.json').exists())
        for path in (self.root / 'fresh-output').iterdir():
            self.assertNotIn(b'synthetic-test-secret', path.read_bytes())

    def test_token_response_is_rejected_before_retention(self):
        self.service.hook = lambda *_: (200, b'{"diagnostic":"synthetic-test-secret"}')
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.mutations)
        for path in (self.root / 'fresh-output').iterdir():
            self.assertNotIn(b'synthetic-test-secret', path.read_bytes())

    def test_full_tree_intrinsic_hash_prevents_outside_delta(self):
        original = self.service.answer
        def answer(method, path, payload):
            result, status = original(method, path, payload)
            if method == 'GET' and '/git/trees/' in path:
                result['tree'][0]['sha'] = 'd' * 40
            return result, status
        self.service.answer = answer
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.mutations)

    def test_duplicate_json_and_oversize_response_stop(self):
        for index, response in enumerate((b'{"data":1,"data":2}', b'x' * (c.MAX_RESPONSE + 1))):
            self.service.hook = lambda *_, response=response: (200, response)
            result = self.control(output=str(self.root / ('output%d' % index))).run()
            self.assertEqual(result['status'], 'CLOSED_FAILED')
            self.assertFalse(self.service.mutations)

    def test_source_mismatch_before_api_and_exclusive_output(self):
        (self.root / self.service.files[0]['path']).write_bytes(b'changed')
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.requests)
        with self.assertRaises(c.ClosedError):
            self.control()

    def test_forged_remote_sources_rejected_before_creates(self):
        self.service.sources[self.service.files[0]['path']] = b'forged immutable source\n'
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.mutations)
        self.assertFalse(any(m == 'POST' and '/git/' in p for m, p, _ in self.service.requests))

    def test_existing_owned_metadata_path_stops_without_mutation(self):
        owned_oid = self.service.root_entries[c.PREFIX][2]
        owned = dict(self.service.trees[owned_oid]); owned['service-state.json'] = ('100644', 'blob', 'e' * 40)
        new_owned = c.git_oid('tree', c.tree_bytes(owned)); self.service.trees[new_owned] = owned
        root = dict(self.service.root_entries); root[c.PREFIX] = ('040000', 'tree', new_owned)
        new_root = c.git_oid('tree', c.tree_bytes(root)); self.service.trees[new_root] = root
        self.service.commits[self.service.activation]['tree']['sha'] = new_root
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.mutations)

    def test_missing_negative_error_and_moving_head_rejected(self):
        for index, mode in enumerate(('no-error', 'head-moved')):
            service = Service(self.root / ('case%d' % index))
            def hook(method, path, payload, service=service, mode=mode):
                if path == '/graphql' and payload['query'] == c.QUERY and service.mutations:
                    result, status = service.answer(method, path, payload)
                    if mode == 'no-error':
                        result.pop('errors')
                    else:
                        service.head = payload['variables']['input']['refUpdates'][0]['afterOid']
                    return status, c.canonical(result)
            service.hook = hook
            result = self.control(transport=service, output=str(self.root / ('out%d' % index)),
                proof=service.proof, root=self.root / ('case%d' % index)).run()
            self.assertEqual(result['status'], 'CLOSED_FAILED')
            self.assertEqual(len(service.mutations), 2)

    def test_deadline_and_call_budget_are_closed(self):
        control = self.control(clock=lambda: 0)
        control.clock = lambda: 181
        self.assertEqual(control.run()['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.requests)
        control = self.control(output=str(self.root / 'other-output'))
        control.calls = 40
        self.assertEqual(control.run()['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.requests)

    def test_inert_import_contains_no_live_transport_call(self):
        self.assertEqual(self.service.requests, [])
        self.assertNotIn('requests', c.__dict__)
        self.assertTrue(callable(c.HTTPSTransport))

    def test_isolated_entrypoint_success_exit_remains_zero(self):
        # Execute the actual entrypoint AST with a successful inert main stub.
        # This tests SystemExit handling without importing or invoking transport.
        program = ('import ast,sys; source=open(sys.argv[1]).read(); '
            'guard=ast.parse(source).body[-1]; '
            'exec(compile(ast.Module(body=[guard],type_ignores=[]),sys.argv[1],"exec"),'
            '{"__name__":"__main__","sys":sys,"main":lambda:0})')
        result = subprocess.run([sys.executable, '-I', '-c', program, str(Path(c.__file__))],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_permission_error_is_not_stale_expected_evidence(self):
        def hook(method, path, payload):
            if path == '/graphql' and payload['query'] == c.QUERY and self.service.mutations:
                return 200, c.canonical({'data': {'updateRefs': None},
                    'errors': [{'message': 'Resource not accessible by integration',
                                'path': ['updateRefs']}]})
        self.service.hook = hook
        result = self.control().run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse((self.root / 'fresh-output/stale-expected-error.json').exists())

    def test_signed_or_unmodeled_commit_does_not_reach_cas(self):
        original = self.service.answer
        def answer(method, path, payload):
            result, status = original(method, path, payload)
            if method == 'GET' and '/git/commits/' in path and not path.endswith(self.service.activation):
                result['verification']['signature'] = 'unmodeled signature'
            return result, status
        self.service.answer = answer
        self.assertEqual(self.control().run()['status'], 'CLOSED_FAILED')
        self.assertFalse(self.service.mutations)

    def test_duplicate_run_is_closed_before_git_objects(self):
        def hook(method, path, payload):
            if '/actions/runs?' in path:
                result, _ = self.service.answer(method, path, payload)
                result['workflow_runs'].append(copy.deepcopy(result['workflow_runs'][0]))
                result['total_count'] = 2
                return 200, c.canonical(result)
        self.service.hook = hook
        self.assertEqual(self.control().run()['status'], 'CLOSED_FAILED')
        self.assertEqual(len(self.service.requests), 1)

    def test_source_change_during_transport_stops_before_next_api(self):
        def hook(method, path, payload):
            if len(self.service.requests) == 1:
                (self.root / self.service.files[0]['path']).write_bytes(b'changed during read')
        self.service.hook = hook
        self.assertEqual(self.control().run()['status'], 'CLOSED_FAILED')
        self.assertEqual(len(self.service.requests), 1)

    def test_response_cap_is_partial_evidence_and_charged(self):
        self.service.hook = lambda *_: (200, b'x' * c.MAX_RESPONSE)
        control = self.control()
        result = control.run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertGreaterEqual(result['request_reply_bytes'], c.MAX_RESPONSE)
        self.assertTrue((control.artifacts.path / '01-response-partial.raw').is_file())
        self.assertFalse((control.artifacts.path / '01-response.raw').exists())

    def test_https_secret_filter_recognizes_json_escape_and_other_token_shape(self):
        transport = c.HTTPSTransport('synthetic-test-secret')
        self.assertTrue(transport.contains_secret(b'{"x":"synthetic-test-secr\\u0065t"}'))
        self.assertTrue(transport.contains_secret(b'{"x":"ghp_abcdefghijklmnopqrstuvwxyz"}'))
        self.assertFalse(transport.contains_secret(b'{"x":"ordinary engineering data"}'))

    def test_complete_selected_source_reply_contains_no_token_shaped_fixture_literal(self):
        root = Path(__file__).resolve().parents[1]
        sources = {str(n): {'text': (root / path).read_text(encoding='utf-8')}
                   for n, path in enumerate(c.SOURCE_PATHS)}
        transport = c.HTTPSTransport('source-readback-' + 'filter-canary')
        self.assertFalse(transport.contains_secret(c.canonical({'data': {'repository': sources}})))

    def test_runtime_drift_and_retained_allocation_close(self):
        original = c.runtime_hashes
        observations = iter(({'runtime': 'before'}, {'runtime': 'changed'}))
        c.runtime_hashes = lambda: next(observations)
        try:
            self.assertEqual(self.control().run()['status'], 'CLOSED_FAILED')
        finally:
            c.runtime_hashes = original
        control = self.control(output=str(self.root / 'allocation-limit'))
        control.artifacts.allocated = c.MAX_RETAINED
        with self.assertRaises(c.ClosedError):
            control.artifacts.write('overflow.raw', b'x')


if __name__ == '__main__':
    unittest.main(verbosity=2)
