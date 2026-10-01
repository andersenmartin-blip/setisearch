import argparse
import base64
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/radio_native_v2_actions_publisher_control.py'
PROTOCOL = 'config/radio_native_v2_actions_control_20261001a.protocol.json'
spec = importlib.util.spec_from_file_location('actions_publisher', SCRIPT)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
ACTIVATION = 'a' * 40
TOKEN = 'test-private-authentication-value-never-retain'


def tree_sha(rows):
    """Hash the actual Git tree representation, including directory sort order."""
    ordered = sorted(rows.items(), key=lambda row: (row[0] + ('/' if row[1]['type'] == 'tree' else '')).encode())
    raw = b''.join(row['mode'].lstrip('0').encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(row['sha'])
        for name, row in ordered)
    return hashlib.sha1(b'tree ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class FakeGitHub:
    """A deterministic in-memory Git object API; never makes a network call."""

    token = TOKEN

    def __init__(self, *, duplicate=False, existing=False, lost_ack=False, race_before_cas=False):
        self.duplicate = duplicate
        self.lost_ack = lost_ack
        self.race_before_cas = race_before_cas
        self.head = ACTIVATION
        self.calls = []
        self.blobs = {}
        self.trees = {}
        self.commits = {}
        self.ref_updates = []
        readme = self.put_blob(b'Existing unrelated engineering repository file\n')
        root = {'README.md': {'mode': '100644', 'type': 'blob', 'sha': readme}}
        if existing:
            folder = self.put_tree({'old.json': {'mode': '100644', 'type': 'blob', 'sha': self.put_blob(b'{}')}})
            root[publisher.PREFIX] = {'mode': '040000', 'type': 'tree', 'sha': folder}
        self.parent_tree = self.put_tree(root)
        self.commits[ACTIVATION] = {'sha': ACTIVATION, 'tree': {'sha': self.parent_tree}, 'parents': []}

    def put_blob(self, raw):
        sha = publisher.blob_sha(raw)
        self.blobs[sha] = raw
        return sha

    def put_tree(self, rows):
        sha = tree_sha(rows)
        self.trees[sha] = {name: dict(row) for name, row in rows.items()}
        return sha

    def request(self, method, path, body_path, output, limit, timeout, *, request_pin):
        self.calls.append((method, path))
        if not 0 < timeout <= publisher.CAPS['seconds']:
            raise AssertionError('Each dispatch needs the remaining finite control budget')
        request_raw = body_path.read_bytes() if body_path is not None else b''
        if request_pin != {'bytes': len(request_raw), 'sha256': publisher.digest(request_raw)}:
            raise AssertionError('Prospective request pin differs from the actual transmitted body')
        payload = json.loads(request_raw) if body_path is not None else None
        if path == '/graphql' or path.endswith('/graphql'):
            value = self.graphql(payload)
        else:
            if not path.startswith(publisher.API + '/'):
                raise AssertionError('Fake received an unexpected repository API route: ' + path)
            suffix = path[len(publisher.API):]
            value = self.rest(method, suffix, payload)
        raw = publisher.canonical(value)
        if self.lost_ack and (method == 'PATCH' or path.endswith('/graphql')):
            output.write(raw[:19])
            raise ConnectionError('lost mutation acknowledgement; ' + TOKEN)
        if len(raw) > limit:
            raise AssertionError('Fake response exceeds caller reservation')
        output.write(raw)
        return {'status': 200 if method == 'GET' else 201, 'header_count': 4,
            'authentication_header_value_retained': False, 'authentication_header_bytes': len('Bearer ' + TOKEN),
            'full_http_tls_wire_known': False, 'request_body_transmission_verified': True,
            'sent_request_body_bytes': len(request_raw), 'sent_request_body_sha256': publisher.digest(request_raw)}

    def rest(self, method, suffix, payload):
        if method == 'GET' and suffix.startswith('/actions/runs?'):
            row = {'id': 17, 'run_attempt': 1, 'head_sha': ACTIVATION}
            return {'total_count': 2 if self.duplicate else 1, 'workflow_runs': [row, row] if self.duplicate else [row]}
        if method == 'GET' and suffix == '/git/ref/heads/' + publisher.BRANCH:
            return {'ref': 'refs/heads/' + publisher.BRANCH, 'object': {'type': 'commit', 'sha': self.head}}
        if method == 'GET' and suffix.startswith('/git/commits/'):
            return self.commits[suffix.rsplit('/', 1)[1]]
        if method == 'GET' and suffix.startswith('/git/trees/'):
            sha = suffix.rsplit('/', 1)[1]
            return {'sha': sha, 'truncated': False,
                'tree': [{'path': name, **row} for name, row in sorted(self.trees[sha].items())]}
        if method == 'POST' and suffix == '/git/blobs':
            if payload['encoding'] != 'base64':
                raise AssertionError('Only exact base64 blob bytes accepted')
            raw = base64.b64decode(payload['content'], validate=True)
            return {'sha': self.put_blob(raw)}
        if method == 'GET' and suffix.startswith('/git/blobs/'):
            sha = suffix.rsplit('/', 1)[1]
            raw = self.blobs[sha]
            return {'sha': sha, 'size': len(raw), 'encoding': 'base64',
                'content': base64.encodebytes(raw).decode()}
        if method == 'POST' and suffix == '/git/trees':
            rows = {name: dict(row) for name, row in self.trees[payload['base_tree']].items()}
            folder = {}
            if publisher.PREFIX in rows:
                folder = {name: dict(row) for name, row in self.trees[rows[publisher.PREFIX]['sha']].items()}
            for row in payload['tree']:
                prefix, name = row['path'].split('/', 1)
                if prefix != publisher.PREFIX or '/' in name:
                    raise AssertionError('Candidate mutation escaped its owned namespace')
                folder[name] = {key: row[key] for key in ('mode', 'type', 'sha')}
            rows[publisher.PREFIX] = {'mode': '040000', 'type': 'tree', 'sha': self.put_tree(folder)}
            return {'sha': self.put_tree(rows)}
        if method == 'POST' and suffix == '/git/commits':
            raw = publisher.canonical(payload)
            sha = hashlib.sha1(b'commit ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            self.commits[sha] = {'sha': sha, 'tree': {'sha': payload['tree']},
                'parents': [{'sha': parent} for parent in payload['parents']]}
            return {'sha': sha}
        if method == 'PATCH' and suffix == '/git/refs/heads/' + publisher.BRANCH:
            if payload.get('force') is not False:
                raise AssertionError('Force updates are forbidden')
            self.ref_updates.append(payload)
            self.head = payload['sha']
            return {'object': {'type': 'commit', 'sha': self.head}}
        raise AssertionError('Unexpected fake operation: ' + method + ' ' + suffix)

    def graphql(self, payload):
        query = payload.get('query', '')
        if 'updateRefs' not in query:
            raise AssertionError('The only GraphQL control mutation must be updateRefs')
        variables = payload.get('variables', {})
        mutation = variables.get('input', variables)
        if mutation['repositoryId'] != 'R_kgDOT558WQ':
            raise AssertionError('Exact pinned repository node ID required')
        refs = mutation['refUpdates']
        if len(refs) != 1:
            raise AssertionError('Exactly one fixed branch ref update required')
        row = refs[0]
        if row['name'] != 'refs/heads/' + publisher.BRANCH or row.get('force') is not False:
            raise AssertionError('Exactly the owned non-force branch mutation required')
        if self.race_before_cas:
            self.head = 'b' * 40
        if row['beforeOid'] != self.head:
            return {'errors': [{'message': 'Expected branch old oid changed'}], 'data': {'updateRefs': None}}
        self.head = row['afterOid']
        self.ref_updates.append(row)
        return {'data': {'updateRefs': {'clientMutationId': mutation.get('clientMutationId')}}}


def args(output):
    return argparse.Namespace(root=str(ROOT), output=str(output), activation_sha=ACTIVATION,
        expected_parent=ACTIVATION, protocol=PROTOCOL, activation_proof=None)


def environment():
    return mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': publisher.REPOSITORY,
        'GITHUB_REF': 'refs/heads/' + publisher.BRANCH, 'GITHUB_RUN_ATTEMPT': '1',
        'GITHUB_SHA': ACTIVATION, 'GITHUB_RUN_ID': '17', 'GITHUB_TOKEN': TOKEN})


def activation_fixture(output):
    """Produce a local test-only five-file preparation and marker readback closure."""
    request = args(output)
    root = Path(output).parent / 'fixture-prepared-tree'
    root.mkdir()
    files = []
    for relative in sorted(publisher.REQUIRED_FILES):
        raw = (ROOT / relative).read_bytes()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files.append({'path': relative, 'bytes': len(raw), 'sha256': publisher.digest(raw)})
    manifest = publisher.canonical({'namespace': publisher.NAMESPACE, 'files': files, **publisher.DISABLED})
    (root / publisher.MANIFEST).write_bytes(manifest)
    preparation = 'c' * 40
    marker = {'namespace': publisher.NAMESPACE, 'activate': True, 'preparation_commit': preparation,
        'manifest_sha256': publisher.digest(manifest), 'independent_readback': {'commit': preparation,
            'verified': True, 'manifest_sha256': publisher.digest(manifest), 'files': files}, **publisher.DISABLED}
    (root / publisher.MARKER).write_bytes(publisher.canonical(marker))
    proof_path = Path(output).parent / 'fixture-activation-proof.json'
    proof_path.write_bytes(publisher.canonical({'schema': 'radio-native-v2-actions-activation-readback-v1',
        'namespace': publisher.NAMESPACE, 'activation_commit': ACTIVATION, 'verified': True,
        'preparation_commit': preparation, 'manifest_sha256': publisher.digest(manifest), **publisher.DISABLED}))
    request.root = str(root)
    request.activation_proof = str(proof_path)
    return request


def run(output, transport):
    request = activation_fixture(output)
    with environment(), contextlib.redirect_stdout(io.StringIO()) as stdout:
        code = publisher.run_control(request, transport=transport)
    return code, json.loads(stdout.getvalue())


class ActionsPublisherControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.output = Path(cls.directory.name) / 'publisher'
        cls.github = FakeGitHub()
        cls.code, cls.stdout = run(cls.output, cls.github)
        cls.summary = json.loads((cls.output / 'caller-summary.json').read_bytes())
        cls.compact = json.loads((cls.output / 'compact-control-evidence.json').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_actual_maximum_source_posts_reads_and_publishes_exact_owned_two_leaf_tree(self):
        self.assertEqual(self.code, 0)
        self.assertEqual(self.summary['status'], 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY')
        raw = self.github.blobs[publisher.SOURCE_BLOB]
        self.assertEqual(len(raw), 26 * 1024**2)
        self.assertEqual(publisher.digest(raw), publisher.SOURCE_SHA256)
        self.assertEqual(publisher.file_digest(self.output / 'source.txt'), (len(raw), publisher.SOURCE_SHA256))
        self.assertEqual(publisher.file_digest(self.output / 'source-readback.txt'), (len(raw), publisher.SOURCE_SHA256))
        self.assertEqual(self.github.head, self.summary['publication_commit'])
        self.assertEqual(len(self.github.ref_updates), 1)
        update = self.github.ref_updates[0]
        self.assertEqual(update['beforeOid'], ACTIVATION)
        self.assertEqual(update['afterOid'], self.github.head)
        self.assertFalse(update['force'])
        self.assertTrue(self.summary['atomic_expected_parent_cas'])
        candidate = self.github.commits[self.github.head]
        self.assertEqual(candidate['parents'], [{'sha': ACTIVATION}])
        before = self.github.trees[self.github.parent_tree]
        after = self.github.trees[candidate['tree']['sha']]
        self.assertEqual({key: row for key, row in after.items() if key != publisher.PREFIX}, before)
        leaves = self.github.trees[after[publisher.PREFIX]['sha']]
        self.assertEqual(set(leaves), {'source.txt', 'protocol-witness.json'})
        self.assertEqual(leaves['source.txt']['sha'], publisher.SOURCE_BLOB)
        witness = json.loads(self.github.blobs[leaves['protocol-witness.json']['sha']])
        self.assertTrue(witness['exact_source_public_readback_verified'])
        for key in publisher.DISABLED:
            self.assertIs(self.summary[key], False)
            self.assertIs(witness[key], False)
        usage = self.summary['usage']
        self.assertEqual(usage['operation_count'], len(self.github.calls))
        self.assertLessEqual(usage['operation_count'], 20)
        self.assertGreater(usage['request_bytes'], 34 * 1024**2)
        self.assertGreater(usage['response_bytes'], 34 * 1024**2)
        self.assertLessEqual(usage['request_bytes'], publisher.CAPS['request_bytes'])
        self.assertLessEqual(usage['response_charged_bytes'], publisher.CAPS['reply_bytes'])
        self.assertEqual(usage['unknown_response_count'], 0)
        inventory = json.loads((self.output / 'storage-inventory.json').read_bytes())
        self.assertLessEqual(max(inventory['logical_bytes'], inventory['allocated_bytes']), publisher.CAPS['host_receipt_bytes'])

    def test_compact_evidence_reconstructs_every_exact_body_without_private_authentication(self):
        bodies = {row['path']: row for row in self.compact['bodies']}
        records = self.compact['records']
        self.assertEqual(len(records), len(self.github.calls))
        for record in records:
            for kind in ('request', 'response'):
                path = record[kind + '_body_file']
                if path is None:
                    self.assertEqual(record[kind + '_body_bytes'], 0)
                    continue
                packed = bodies[path]
                raw = gzip.decompress(base64.b64decode(packed['content'], validate=True))
                self.assertEqual((len(raw), publisher.digest(raw)), (packed['bytes'], packed['sha256']))
                self.assertEqual((len(raw), publisher.digest(raw)),
                    (record[kind + '_body_bytes'], record[kind + '_body_sha256']))
                self.assertEqual(raw, (self.output / path).read_bytes())
        self.assertFalse(self.compact['authentication_header_values_retained'])
        self.assertFalse(self.compact['full_http_tls_wire_known'])
        self.assertTrue(self.compact['post_control_evidence_publication_excluded'])
        for path in self.output.rglob('*'):
            if path.is_file() and path.name not in ('source.txt', 'source-readback.txt'):
                self.assertNotIn(TOKEN.encode(), path.read_bytes(), str(path))

    def test_duplicate_activation_run_and_existing_namespace_stop_before_any_source_upload(self):
        for options in ({'duplicate': True}, {'existing': True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                transport = FakeGitHub(**options)
                output = Path(directory) / 'publisher'
                code, result = run(output, transport)
                self.assertEqual(code, 1)
                self.assertEqual(result['status'], 'CLOSED_FAILED')
                self.assertFalse((output / 'source.txt').exists())
                self.assertFalse(any(method == 'POST' for method, _ in transport.calls))
                self.assertFalse(transport.ref_updates)

    def test_lost_mutation_acknowledgement_retains_candidate_unknown_charge_and_durable_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeGitHub(lost_ack=True)
            output = Path(directory) / 'publisher'
            code, result = run(output, transport)
            self.assertEqual(code, 1)
            self.assertEqual(result['status'], 'CLOSED_FAILED')
            summary = json.loads((output / 'caller-summary.json').read_bytes())
            self.assertTrue(summary['update_may_have_landed'])
            self.assertEqual(summary['publication_candidate'], transport.head)
            self.assertEqual(len(transport.ref_updates), 1)
            compact = json.loads((output / 'compact-control-evidence.json').read_bytes())
            unknown = [row for row in compact['records'] if row['response_unknown']]
            self.assertEqual(len(unknown), 1)
            row = unknown[0]
            self.assertGreater(row['response_reserved_bytes'], 19)
            self.assertEqual(summary['usage']['unknown_response_bytes'], row['response_reserved_bytes'])
            self.assertEqual(row['response_prefix_bytes'], 19)
            self.assertIs(row['response_prefix_complete'], False)
            prefix = (output / row['response_prefix_file']).read_bytes()
            self.assertEqual((len(prefix), publisher.digest(prefix)), (19, row['response_prefix_sha256']))
            packed = next(item for item in compact['bodies'] if item['path'] == row['response_prefix_file'])
            self.assertEqual(gzip.decompress(base64.b64decode(packed['content'])), prefix)
            self.assertNotIn(TOKEN, json.dumps(compact))
            self.assertEqual(transport.calls[-1], ('POST', '/graphql'))

    def test_branch_change_after_late_head_check_fails_atomic_cas_without_replacing_new_head(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeGitHub(race_before_cas=True)
            output = Path(directory) / 'publisher'
            code, result = run(output, transport)
            self.assertEqual(code, 1)
            self.assertEqual(result['status'], 'CLOSED_FAILED')
            self.assertEqual(transport.head, 'b' * 40)
            self.assertEqual(transport.ref_updates, [])
            self.assertEqual(transport.calls[-1], ('POST', '/graphql'))
            summary = json.loads((output / 'caller-summary.json').read_bytes())
            self.assertIsNotNone(summary['publication_candidate'])
            self.assertTrue(summary['atomic_expected_parent_cas'])
            self.assertEqual(summary['usage']['unknown_response_count'], 0)

    def test_failed_control_administrative_preservation_adds_only_evidence_and_does_not_replay_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport = FakeGitHub(duplicate=True)
            code, _ = run(root / 'publisher', transport)
            self.assertEqual(code, 1)
            report = publisher.canonical({'status': 'CONTROL_FAILED', 'termination': 'normal', **publisher.DISABLED})
            (root / 'supervisor-report.json').write_bytes(report)
            transport.duplicate = False
            before_count = len(transport.calls)
            with environment(), contextlib.redirect_stdout(io.StringIO()):
                result = publisher.publish_evidence(args(root), transport=transport)
            self.assertEqual(result, 0)
            post = transport.calls[before_count:]
            self.assertEqual(sum(method == 'POST' and path.endswith('/git/blobs') for method, path in post), 1)
            self.assertNotIn(publisher.SOURCE_BLOB, transport.blobs)
            published = transport.commits[transport.head]
            folder = transport.trees[transport.trees[published['tree']['sha']][publisher.PREFIX]['sha']]
            self.assertEqual(set(folder), {'evidence.json'})
            envelope = json.loads(transport.blobs[folder['evidence.json']['sha']])
            self.assertEqual(envelope['control_status'], 'CLOSED_FAILED')
            packed = envelope['files']['supervisor-report.json']
            self.assertEqual(gzip.decompress(base64.b64decode(packed['content'])), report)
            self.assertTrue(envelope['administrative_publication_outside_measured_control'])
            for key in publisher.DISABLED:
                self.assertFalse(envelope[key])

    def test_terminated_control_without_summary_preserves_exact_existing_prefix_and_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bodies = root / 'publisher/bodies'
            bodies.mkdir(parents=True)
            observed = {'publisher/bodies/00-response.json': b'{"partially_received":',
                'publisher/source-blob-request.json': b'{"content":"partial',
                'publisher/receipt-ledger.jsonl': b'{"kind":"intent","response_unknown":true}\n',
                'publisher-stdout.log': b'publisher was terminated before summary\n',
                'procfs-samples.jsonl': b'{"rss_bytes":1048576}\n'}
            for relative, raw in observed.items():
                (root / relative).write_bytes(raw)
            transport = FakeGitHub()
            with environment(), contextlib.redirect_stdout(io.StringIO()):
                result = publisher.publish_evidence(args(root), transport=transport)
            self.assertEqual(result, 0)
            committed = transport.commits[transport.head]
            folder = transport.trees[transport.trees[committed['tree']['sha']][publisher.PREFIX]['sha']]
            self.assertEqual(set(folder), {'evidence.json'})
            envelope = json.loads(transport.blobs[folder['evidence.json']['sha']])
            self.assertEqual(envelope['control_status'], 'CLOSED_FAILED')
            self.assertEqual(envelope['synthetic_summary_if_missing']['activation_commit'], ACTIVATION)
            for relative, raw in observed.items():
                row = envelope['files'][relative]
                self.assertEqual((row['bytes'], row['sha256']), (len(raw), publisher.digest(raw)))
                self.assertEqual(gzip.decompress(base64.b64decode(row['content'])), raw)
            self.assertNotIn(publisher.SOURCE_BLOB, transport.blobs)

    def test_actual_https_transport_detects_same_size_request_file_replacement_after_send(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'request.json'
            raw = b'{"fixed":"before"}'
            path.write_bytes(raw)

            class Connection:
                sock = None
                closed = False
                response_requested = False

                def putrequest(self, *args, **kwargs):
                    pass

                def putheader(self, *args):
                    pass

                def endheaders(self):
                    pass

                def send(self, block):
                    self.sent = block
                    replacement = path.with_name('replacement.json')
                    replacement.write_bytes(b'{"fixed":"after!"}')
                    replacement.replace(path)

                def getresponse(self):
                    self.response_requested = True
                    raise AssertionError('Changed request must fail before response acceptance')

                def close(self):
                    self.closed = True

            connection = Connection()
            with mock.patch.object(publisher.http.client, 'HTTPSConnection', return_value=connection):
                with self.assertRaisesRegex(ValueError, 'Pinned request body changed'):
                    publisher.HttpsTransport(TOKEN).request('POST', publisher.API + '/git/blobs', path,
                        io.BytesIO(), 1024, 10, request_pin={'bytes': len(raw), 'sha256': publisher.digest(raw)})
            self.assertEqual(connection.sent, raw)
            self.assertFalse(connection.response_requested)
            self.assertTrue(connection.closed)

    def test_http_operation_and_body_reservations_refuse_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = FakeGitHub()
            store = publisher.Store(str(Path(directory) / 'publisher'))
            control = publisher.Control(store, transport)
            try:
                for _ in range(20):
                    self.assertEqual(control.head(), ACTIVATION)
                with self.assertRaisesRegex(ValueError, 'twenty'):
                    control.head()
                self.assertEqual(len(transport.calls), 20)
            finally:
                store.seal(control.journal)
        for key, cap, reserve, payload in [('request_bytes', 64, 1, {'content': 'x' * 65}),
                ('reply_bytes', 64, 65, None)]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                transport = FakeGitHub()
                store = publisher.Store(str(Path(directory) / 'publisher'))
                control = publisher.Control(store, transport)
                try:
                    with mock.patch.dict(publisher.CAPS, {key: cap}):
                        with self.assertRaisesRegex(ValueError, 'original request/reply caps'):
                            control.call('GET', '/git/ref/heads/' + publisher.BRANCH, payload, reserve=reserve)
                    self.assertEqual(transport.calls, [])
                    self.assertEqual(control.records, [])
                finally:
                    store.seal(control.journal)

    def test_changed_fixed_cap_or_run_attempt_refuses_before_output_or_http_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = json.loads((ROOT / PROTOCOL).read_bytes())
            protocol['caps']['request_bytes'] += 1
            (root / 'protocol.json').write_bytes(publisher.canonical(protocol))
            transport = FakeGitHub()
            request = args(root / 'publisher')
            request.root = str(root)
            request.protocol = 'protocol.json'
            with environment(), self.assertRaisesRegex(ValueError, 'fixed engineering protocol'):
                publisher.run_control(request, transport=transport)
            self.assertFalse(Path(request.output).exists())
            self.assertEqual(transport.calls, [])
            request = args(root / 'attempt')
            with environment(), mock.patch.dict(os.environ, {'GITHUB_RUN_ATTEMPT': '2'}):
                with self.assertRaisesRegex(ValueError, 'first-attempt'):
                    publisher.run_control(request, transport=transport)
            self.assertFalse(Path(request.output).exists())
            self.assertEqual(transport.calls, [])

    def test_missing_activation_proof_or_changed_prepared_file_refuses_before_http_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport = FakeGitHub()
            request = args(root / 'missing')
            with environment(), self.assertRaisesRegex(ValueError, 'two-stage activation proof'):
                publisher.run_control(request, transport=transport)
            self.assertFalse(Path(request.output).exists())
            self.assertEqual(transport.calls, [])
            request = activation_fixture(root / 'changed')
            owned = Path(request.root) / 'scripts/radio_native_v2_actions_supervisor.py'
            owned.write_bytes(owned.read_bytes() + b'\n# changed after preparation\n')
            with environment(), self.assertRaisesRegex(ValueError, 'five-file closure differs'):
                publisher.run_control(request, transport=transport)
            self.assertFalse(Path(request.output).exists())
            self.assertEqual(transport.calls, [])


if __name__ == '__main__':
    unittest.main()
