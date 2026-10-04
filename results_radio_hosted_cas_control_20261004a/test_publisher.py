"""Synthetic administrative publication checks; never a service qualification."""
import base64
import ast
import gzip
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

_path = Path(__file__).with_name('publisher.py').resolve()
_spec = importlib.util.spec_from_file_location('publisher_under_test', _path)
p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p)
c = p.c


class MemoryGit:
    synthetic = True

    def __init__(self, activation, baseline):
        self.head = activation
        self.trees = {}
        self.blobs = {}
        self.commits = {}
        self.calls = []
        self.cas_count = 0
        self.fail_cas = False
        self.bad_blob = False
        self.bad_commit_ack = False
        self.add_tree(baseline['owned'])
        self.add_tree(baseline['root'])

    def contains_secret(self, raw):
        return b'test-memory-secret-not-a-token' in raw

    def add_tree(self, entries):
        oid = c.git_oid('tree', c.tree_bytes(entries))
        self.trees[oid] = dict(entries)
        return oid

    def add_candidate(self, candidate):
        self.add_tree(candidate['owned']); self.add_tree(candidate['root'])
        self.blobs[candidate['blob']] = candidate['body']
        self.commits[candidate['oid']] = {
            'sha': candidate['oid'], 'tree': {'sha': candidate['tree']},
            'parents': [{'sha': candidate['parent']}], 'author': c.IDENTITY,
            'committer': c.IDENTITY, 'message': 'Engineering CAS control: accepted-cas'}

    def __call__(self, method, path, raw, timeout):
        payload = c.strict_json(raw) if raw else None
        self.calls.append((method, path, payload))
        status = 200
        if path == '/graphql':
            if payload['query'] == c.HEAD_QUERY:
                result = {'data': {'repository': {'id': c.REPOSITORY_ID,
                         'ref': {'target': {'oid': self.head}}}}}
            else:
                self.cas_count += 1
                update = payload['variables']['input']['refUpdates'][0]
                if self.fail_cas:
                    return 200, c.canonical({'errors': [{'message': 'expected head changed'}],
                                             'data': {'updateRefs': None}})
                if update['beforeOid'] != self.head:
                    raise AssertionError('Unexpected stale publisher head')
                if update['force'] is not False:
                    raise AssertionError('Unexpected force')
                self.head = update['afterOid']
                result = {'data': {'updateRefs': {'clientMutationId':
                    payload['variables']['input']['clientMutationId']}}}
        else:
            suffix = path.split('/git/', 1)[1]
            if method == 'GET' and suffix.startswith('trees/'):
                oid = suffix[6:]
                result = {'sha': oid, 'truncated': False, 'tree': [
                    {'path': name, 'mode': entry[0], 'type': entry[1], 'sha': entry[2]}
                    for name, entry in self.trees[oid].items()]}
            elif method == 'GET' and suffix.startswith('blobs/'):
                oid = suffix[6:]
                body = self.blobs[oid]
                if self.bad_blob:
                    body += b'!'
                result = {'sha': oid, 'encoding': 'base64', 'size': len(body),
                          'content': base64.b64encode(body).decode()}
            elif method == 'GET' and suffix.startswith('commits/'):
                result = self.commits[suffix[8:]]
            elif method == 'POST' and suffix == 'blobs':
                body = base64.b64decode(payload['content'], validate=True)
                oid = c.git_oid('blob', body)
                self.blobs[oid] = body
                result = {'sha': oid}; status = 201
            elif method == 'POST' and suffix == 'trees':
                root = dict(self.trees[payload['base_tree']])
                owned = dict(self.trees[root[c.PREFIX][2]])
                for entry in payload['tree']:
                    filename = entry['path'].split('/')[-1]
                    owned[filename] = (entry['mode'], entry['type'], entry['sha'])
                root[c.PREFIX] = ('040000', 'tree', self.add_tree(owned))
                result = {'sha': self.add_tree(root)}; status = 201
            elif method == 'POST' and suffix == 'commits':
                oid = c.git_oid('commit', c.commit_bytes(payload['tree'],
                    payload['parents'][0], payload['message'].rstrip('\n')))
                result = {'sha': oid, 'tree': {'sha': payload['tree']},
                          'parents': [{'sha': payload['parents'][0]}],
                          'author': payload['author'], 'committer': payload['committer'],
                          'message': payload['message']}
                self.commits[oid] = result; status = 201
                if self.bad_commit_ack:
                    result = {**result, 'sha': '8' * 40}
            else:
                raise AssertionError('Unexpected request')
        return status, c.canonical(result)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root / 'scope'; self.output.mkdir()
        self.child = self.output / 'child'; self.child.mkdir()
        self.activation = 'a' * 40
        self.proof = {'activation': self.activation, 'run_id': '12345', 'manifest_sha256': 'f' * 64}
        self.report = {'schema': 'radio-hosted-cas-supervisor-observation-v1',
            'status': 'COMPONENT_OBSERVED', 'direct_child_reaped': True, 'full_retained': True,
            'launch_attempted': True, 'launched': True, 'no_child_launch_proven': False,
            'component_only': True, 'scientific_authority': False, 'no_retry': True,
            'direct_child': {'pid': 9001, 'wait_status': 0, 'exit_code': 0,
                'reaped_epoch_ns': 100, 'wait4_max_rss_bytes': 1024}}
        self.write('terminal.json', self.report)
        self.write('supervisor-outcome.json', {'status': 'COMPONENT_OBSERVED',
                   'component_only': True, 'scientific_authority': False})
        self.write('child/result.json', {'status': 'SERVICE_COMPONENT_CONTROL_PASSED'})
        (self.output / 'stdout.bin').write_bytes(b'raw\x00stdout\xff\n')
        owned = {'control.py': ('100644', 'blob', 'c' * 40)}
        top = {c.PREFIX: ('040000', 'tree', c.git_oid('tree', c.tree_bytes(owned))),
               'README.md': ('100644', 'blob', 'd' * 40)}
        self.baseline = {'root': top, 'owned': owned, 'tree': c.git_oid('tree', c.tree_bytes(top))}
        body = c.canonical({'schema': 'radio-hosted-cas-control-state-v1', 'engineering_only': True,
            'purpose': 'accepted-cas', 'activation': self.activation, 'parent': self.activation,
            'manifest_sha256': self.proof['manifest_sha256'], 'run_id': self.proof['run_id'],
            **c.FALSE_AUTHORITY})
        blob = c.git_oid('blob', body)
        new_owned = dict(owned); new_owned['service-state.json'] = ('100644', 'blob', blob)
        new_top = dict(top); new_top[c.PREFIX] = ('040000', 'tree', c.git_oid('tree', c.tree_bytes(new_owned)))
        tree = c.git_oid('tree', c.tree_bytes(new_top))
        raw = c.commit_bytes(tree, self.activation, 'Engineering CAS control: accepted-cas')
        self.witness = {'oid': c.git_oid('commit', raw), 'tree': tree, 'parent': self.activation,
            'blob': blob, 'path': c.STATE_PATH, 'raw_commit_hex': raw.hex(), 'body_hex': body.hex()}
        self.write('child/accepted-candidate.json', self.witness)
        self.candidate = p.accepted_candidate(self.witness, self.activation, self.proof, self.baseline)
        self.transport = MemoryGit(self.activation, self.baseline)
        self.transport.add_candidate(self.candidate)
        self.transport.head = self.candidate['oid']

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, value):
        (self.output / relative).write_bytes(c.canonical(value))

    def publisher(self):
        return p.Publisher(self.transport, self.output, self.proof, self.root,
                           self.proof['manifest_sha256'], self.baseline)

    def run_publisher(self, instance=None):
        with patch.object(c, 'verify_proof', return_value=[]):
            return (instance or self.publisher()).run()

    def test_archive_lossless_all_original_regular_files(self):
        raw = p.archive(self.output, self.proof, self.report, 'SERVICE_COMPONENT_CONTROL_PASSED')
        envelope = c.strict_json(raw)
        paths = [x.relative_to(self.output).as_posix() for x in self.output.rglob('*') if x.is_file()]
        self.assertEqual(sorted(envelope['files']), sorted(paths))
        for name, item in envelope['files'].items():
            decoded = gzip.decompress(base64.b64decode(item['content'], validate=True))
            self.assertEqual(decoded, (self.output / name).read_bytes())
            self.assertEqual(item['sha256'], hashlib.sha256(decoded).hexdigest())
            self.assertEqual(item['bytes'], len(decoded))
        self.assertFalse(envelope['scientific_authority'])
        files_bytes = sum((self.output / path).stat().st_size for path in paths)
        self.assertGreater(envelope['original_scope_logical_bytes'], files_bytes)

    def test_archive_is_deterministic(self):
        self.assertEqual(p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED'),
                         p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED'))

    def test_symlink_refused(self):
        (self.output / 'escape').symlink_to(self.root / 'outside')
        with self.assertRaises(c.ClosedError):
            p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED')

    def test_hardlink_refused(self):
        os = __import__('os')
        os.link(self.output / 'stdout.bin', self.output / 'duplicate.bin')
        with self.assertRaises(c.ClosedError):
            p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED')

    def test_changed_body_refused(self):
        def mutate(path):
            if path.name == 'stdout.bin':
                path.write_bytes(b'changed')
        with self.assertRaises(c.ClosedError):
            p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED', after_read=mutate)

    def test_secret_patterns_refused(self):
        (self.output / 'stdout.bin').write_bytes(b'ghp_' + b'A' * 30)
        with self.assertRaises(c.ClosedError):
            p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED')

    def test_exact_transport_secret_refused(self):
        (self.output / 'stdout.bin').write_bytes(b'test-memory-secret-not-a-token')
        with self.assertRaises(c.ClosedError):
            p.archive(self.output, self.proof, self.report, 'CLOSED_FAILED', transport=self.transport)

    def test_unreaped_child_zero_network_calls(self):
        self.report['direct_child_reaped'] = False
        self.write('terminal.json', self.report)
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.calls, [])

    def test_success_exact_single_delta_and_one_cas(self):
        result = self.run_publisher()
        self.assertEqual(result['status'], 'SYNTHETIC_PUBLICATION_ONLY')
        self.assertEqual(self.transport.cas_count, 1)
        self.assertEqual(result['parent'], self.candidate['oid'])
        self.assertEqual(result['calls'], 19)
        archive_blob = self.transport.blobs[result['blob']]
        envelope = c.strict_json(archive_blob)
        self.assertFalse(any(name.startswith('publication/') for name in envelope['files']))
        trees = [args[2] for args in self.transport.calls if args[1].endswith('/trees')]
        self.assertEqual(len(trees), 1)
        self.assertEqual(trees[0]['tree'][0]['path'], p.EVIDENCE_PATH)
        commits = [args[2] for args in self.transport.calls if args[1].endswith('/commits')]
        self.assertTrue(commits[0]['message'].endswith('\n'))
        self.assertFalse(result['scientific_authority'])

    def test_cas_error_spends_instance_without_retry(self):
        self.transport.fail_cas = True
        instance = self.publisher()
        result = self.run_publisher(instance)
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 1)
        recovery = result['recoverable_precreated_objects']
        self.assertTrue(recovery['pre_cas_immutable_readback_complete'])
        self.assertEqual(recovery['archive_sha256'],
            hashlib.sha256(self.transport.blobs[recovery['blob']]).hexdigest())
        calls = len(self.transport.calls)
        with self.assertRaises(c.ClosedError):
            self.run_publisher(instance)
        self.assertEqual(len(self.transport.calls), calls)

    def test_unknown_remote_head_refused_before_object_creation(self):
        self.transport.head = '9' * 40
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 0)
        self.assertEqual(len(self.transport.calls), 1)

    def test_passed_child_requires_accepted_head(self):
        self.transport.head = self.activation
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 0)

    def test_failed_child_can_archive_activation_head(self):
        self.report['status'] = 'CLOSED_FAILED'; self.report['direct_child']['exit_code'] = 1
        self.report['full_retained'] = False
        self.write('terminal.json', self.report)
        self.write('child/result.json', {'status': 'CLOSED_FAILED'})
        self.transport.head = self.activation
        result = self.run_publisher()
        self.assertEqual(result['status'], 'SYNTHETIC_PUBLICATION_ONLY')
        self.assertEqual(result['calls'], 15)
        self.assertFalse(c.strict_json(self.transport.blobs[result['blob']])['complete_child_streams_retained'])

    def test_candidate_witness_cannot_alter_parent_or_body(self):
        for field, value in [('parent', '8' * 40), ('body_hex', '00'), ('tree', '7' * 40)]:
            witness = dict(self.witness); witness[field] = value
            with self.subTest(field=field), self.assertRaises(c.ClosedError):
                p.accepted_candidate(witness, self.activation, self.proof, self.baseline)

    def test_immutable_blob_mismatch_blocks_cas(self):
        self.transport.bad_blob = True
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 0)

    def test_source_pin_failure_zero_network_calls(self):
        instance = self.publisher()
        with patch.object(c, 'verify_proof', side_effect=c.ClosedError):
            result = instance.run()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.calls, [])

    def test_no_launch_terminal_archived_without_reap_claim(self):
        self.report.update(status='CLOSED_BEFORE_CHILD', direct_child=None,
                           direct_child_reaped=False, launch_attempted=False,
                           launched=False, no_child_launch_proven=True)
        self.write('terminal.json', self.report)
        self.write('supervisor-outcome.json', {'status': 'CLOSED_FAILED',
                   'component_only': True, 'scientific_authority': False})
        self.transport.head = self.activation
        result = self.run_publisher()
        self.assertEqual(result['status'], 'SYNTHETIC_PUBLICATION_ONLY')
        self.assertFalse(c.strict_json(self.transport.blobs[result['blob']])['supervisor_child_reaped'])

    def test_final_supervisor_failure_overrides_passed_child(self):
        self.write('supervisor-outcome.json', {'status': 'CLOSED_FAILED',
                   'component_only': True, 'scientific_authority': False})
        result = self.run_publisher()
        self.assertEqual(result['status'], 'SYNTHETIC_PUBLICATION_ONLY')
        self.assertEqual(c.strict_json(self.transport.blobs[result['blob']])['status'], 'CLOSED_FAILED')

    def test_unknown_response_allowance_spent(self):
        class TimeoutGit(MemoryGit):
            def __call__(self, method, path, raw, timeout):
                raise TimeoutError()
        self.transport = TimeoutGit(self.activation, self.baseline)
        instance = self.publisher()
        with patch.object(c, 'verify_proof', return_value=[]), self.assertRaises(c.ClosedError):
            instance.api('GET', 'git/trees/' + '1' * 40)
        self.assertEqual(instance.calls, 1)
        self.assertGreater(instance.total, c.MAX_RESPONSE)
        error = c.strict_json((instance.artifacts.path / '01-error.json').read_bytes())
        self.assertTrue(error['unknown_response_allowance_spent'])

    def test_reply_cap_reserved_before_network(self):
        instance = self.publisher()
        instance.total = p.MAX_TOTAL - c.MAX_RESPONSE
        with patch.object(c, 'verify_proof', return_value=[]), self.assertRaises(c.ClosedError):
            instance.api('GET', 'git/trees/' + '1' * 40)
        self.assertEqual(self.transport.calls, [])

    def test_cli_exit_wrapper_preserves_success(self):
        # Execute the exact frozen wrapper in a fresh interpreter with a pure
        # successful main fixture: no HTTP, token, or project publication.
        module = ast.parse(_path.read_text())
        wrapper = module.body[-1]
        self.assertIsInstance(wrapper, ast.If)
        code = ast.unparse(wrapper)
        fixture = 'import sys\ndef main(): return 0\n' + code
        result = subprocess.run([sys.executable, '-I', '-B', '-S', '-c', fixture],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b'')

    def test_exact_response_cap_preserves_prefix_then_closes(self):
        class CappedGit(MemoryGit):
            def __call__(self, method, path, raw, timeout):
                body = c.canonical({'complete_json': True})
                return 200, body + b' ' * (c.MAX_RESPONSE - len(body))
        self.transport = CappedGit(self.activation, self.baseline)
        instance = self.publisher()
        with patch.object(c, 'verify_proof', return_value=[]), self.assertRaises(c.ClosedError):
            instance.api('GET', 'git/trees/' + '1' * 40)
        self.assertEqual((instance.artifacts.path / '01-response-partial.raw').stat().st_size, c.MAX_RESPONSE)
        journal = c.strict_json((instance.artifacts.path / '01-journal.json').read_bytes())
        self.assertTrue(journal['response_capped_unknown_eof'])

    def test_response_secret_refused_without_secret_receipt(self):
        class SecretGit(MemoryGit):
            def __call__(self, method, path, raw, timeout):
                return 200, c.canonical({'secret': 'ghp_' + 'A' * 30})
        self.transport = SecretGit(self.activation, self.baseline)
        instance = self.publisher()
        with patch.object(c, 'verify_proof', return_value=[]), self.assertRaises(c.ClosedError):
            instance.api('GET', 'git/trees/' + '1' * 40)
        self.assertTrue((instance.artifacts.path / '01-response-redacted.json').is_file())
        for file in instance.artifacts.path.iterdir():
            self.assertNotIn(b'ghp_', file.read_bytes())

    def test_original_scope_over_cap_refused_before_http(self):
        (self.output / 'large.bin').write_bytes(b'x' * (p.ORIGINAL_CAP + 1))
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.calls, [])

    def test_unqualified_commit_ack_preserves_archive_recovery(self):
        self.transport.bad_commit_ack = True
        result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 0)
        recovery = result['recoverable_archive_object']
        self.assertTrue(recovery['blob_create_acknowledged'])
        self.assertEqual(recovery['unqualified_returned_commit_oid'], '8' * 40)
        self.assertNotEqual(recovery['precomputed_commit'], '8' * 40)
        self.assertEqual(recovery['archive_sha256'],
            hashlib.sha256(self.transport.blobs[recovery['blob']]).hexdigest())
        self.assertNotIn('recoverable_precreated_objects', result)

    def test_blob_request_ambiguity_retains_precomputed_archive_oid(self):
        original = self.transport.__class__.__call__
        def ambiguous(instance, method, path, raw, timeout):
            result = original(instance, method, path, raw, timeout)
            if method == 'POST' and path.endswith('/blobs'):
                raise TimeoutError()
            return result
        with patch.object(MemoryGit, '__call__', ambiguous):
            result = self.run_publisher()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(self.transport.cas_count, 0)
        recovery = result['recoverable_archive_object']
        self.assertFalse(recovery['blob_create_acknowledged'])
        self.assertEqual(recovery['archive_sha256'],
            hashlib.sha256(self.transport.blobs[recovery['blob']]).hexdigest())


if __name__ == '__main__':
    unittest.main()
