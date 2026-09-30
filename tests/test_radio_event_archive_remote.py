"""Offline proof of single-commit, exact-byte, stop-without-retry archiving."""
import base64
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote

from seti_repeater import event_archive_remote_radio as r
from seti_repeater import physical_case_radio as case
from seti_repeater import physical_evidence_radio as naming
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater import whole_cadence_event_store_radio as s
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_journal import manifest


class FakeGit:
    """Actual Git blob/tree hashes and immutable commit-path readback, offline."""
    def __init__(self, initial_files=None):
        self.calls = []
        self.blobs = {}
        self.trees = {}
        self.commits = {}
        self.wrong_blob = self.wrong_tree = self.bad_readback = False
        self.lost_update = self.unrelated_change = self.move_before_update = False
        self.tick = 0
        self.root = self.build({name: self.blob(data) for name, data in
                                (initial_files or {'README.md': b'original public README\n'}).items()})
        self.head = self.commit(self.root, [])
        self.initial_head = self.head

    def blob(self, data):
        sha = r.git_object('blob', data)
        self.blobs[sha] = data
        return sha

    def tree(self, entries):
        order = sorted(entries, key=lambda n: (n + ('/' if entries[n]['type'] == 'tree' else '')).encode())
        raw = b''.join(entries[n]['mode'].lstrip('0').encode() + b' ' + n.encode() + b'\0'
                       + bytes.fromhex(entries[n]['sha']) for n in order)
        sha = r.git_object('tree', raw)
        self.trees[sha] = {k: dict(v) for k, v in entries.items()}
        return sha

    def build(self, leaves):
        groups = {}
        for path, sha in leaves.items():
            name, sep, rest = path.partition('/')
            groups.setdefault(name, {})[rest if sep else ''] = sha
        entries = {}
        for name, values in groups.items():
            if '' in values:
                entries[name] = {'mode': '100644', 'type': 'blob', 'sha': values['']}
            else:
                entries[name] = {'mode': '040000', 'type': 'tree', 'sha': self.build(values)}
        return self.tree(entries)

    def flatten(self, sha, prefix=''):
        result = {}
        for name, row in self.trees[sha].items():
            if row['type'] == 'tree':
                result.update(self.flatten(row['sha'], prefix + name + '/'))
            else:
                result[prefix + name] = row['sha']
        return result

    def commit(self, tree, parents, message='fixture'):
        raw = (f'tree {tree}\n' + ''.join(f'parent {p}\n' for p in parents)
               + 'author Fixture <fixture@example.org> 0 +0000\n'
               + 'committer Fixture <fixture@example.org> 0 +0000\n\n' + message).encode()
        sha = r.git_object('commit', raw)
        self.commits[sha] = {'sha': sha, 'tree': {'sha': tree}, 'parents': [{'sha': p} for p in parents]}
        return sha

    def invoke(self, operation, params):
        self.calls.append((operation, params))
        self.tick += 1
        if operation == 'fetch':
            path = params['url'].split('/git/', 1)[1]
            if path.startswith('ref/heads/'):
                assert unquote(path[10:]) == r.BRANCH
                if self.move_before_update and sum(o == 'create_commit' for o, _ in self.calls):
                    self.head = self.commit(self.root, [self.head], 'concurrent edit')
                return {'ref': 'refs/heads/' + r.BRANCH, 'object': {'sha': self.head, 'type': 'commit'}}
            kind, sha = path.split('/')
            if kind == 'commits':
                return self.commits[sha]
            if kind == 'trees':
                entries = [{'path': name, **row} for name, row in self.trees[sha].items()]
                if self.wrong_tree and entries:
                    entries[0]['sha'] = 'a' * 40
                return {'sha': sha, 'truncated': False, 'tree': entries}
            raise AssertionError(path)
        assert params['repository_full_name'] == r.REPO
        if operation == 'create_blob':
            assert params['encoding'] == 'base64'
            sha = self.blob(base64.b64decode(params['content'], validate=True))
            return {'sha': 'b' * 40 if self.wrong_blob else sha}
        if operation == 'create_tree':
            leaves = self.flatten(params['base_tree_sha'])
            for row in params['tree_elements']:
                assert (row['mode'], row['type']) == ('100644', 'blob')
                leaves[row['path']] = row['sha']
            if self.unrelated_change:
                leaves['README.md'] = self.blob(b'changed unrelated README')
            return {'sha': self.build(leaves)}
        if operation == 'create_commit':
            return {'sha': self.commit(params['tree_sha'], [params['parent_sha']], params['message'])}
        if operation == 'update_ref':
            assert params['force'] is False and params['branch_name'] == r.BRANCH
            assert self.commits[params['sha']]['parents'] == [{'sha': self.head}]
            self.head = params['sha']
            if self.lost_update:
                raise OSError('lost update response after atomic ref change')
            return {'success': True}
        if operation == 'fetch_file':
            assert params['encoding'] == 'base64'
            sha = self.flatten(self.commits[params['ref']]['tree']['sha'])[params['path']]
            data = self.blobs[sha]
            if self.bad_readback and data:
                data = bytes([data[0] ^ 1]) + data[1:]
            return {'sha': sha, 'encoding': 'base64', 'content': base64.b64encode(data).decode()}
        raise AssertionError(operation)


class RemoteArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.base_original = {'scores.npz': b'\x00\xffraw binary score bytes\n'}
        self.m = manifest(1, ('scores.npz', case.SEAL, case.OUTCOME))
        self.m['caps']['evidence_bytes'] = 4 * 1024**2
        self.m['caps']['ledger_reserve_bytes'] = 1024**2
        self.config = e.configuration('remote-archive-test', self.m['cases'][0]['case_identity'],
            self.m['cases'][0]['plan_sha256'], self.base_original,
            budget_bytes=2 * 1024**2 - sum(case.CLOSURE_RESERVES.values()))
        self.m['artifact_groups'] = case.policy(self.config)
        self.store = s.EventDirectoryStore.create(self.path / 'journal', self.m)
        cp = self.store.read()
        self.lease = j.consume(self.store, expected_revision=cp.revision, expected_manifest_sha256=digest(self.m),
            binding=self.m['cases'][0], milliseconds=10000, artifact_bytes=2 * 1024**2,
            directory=self.path / 'case', clock=lambda: 0.)
        self.lease.write_artifact('scores.npz', self.base_original['scores.npz'])
        self.writer = e.Writer.create(self.path / 'physical', self.config, existing_artifacts=self.base_original)
        self.writer.checkpoint('first', self.document(False))
        self.writer.close('completed', 'end', snapshot=self.document(True))
        # Keep the offline input fixture itself stable across process resources.
        footer = json.loads((self.path / 'physical/outcome.json').read_bytes())
        footer.update(elapsed_seconds=0., peak_process_rss_bytes=1234)
        (self.path / 'physical/outcome.json').write_bytes(canonical(footer))
        self.physical = e._inventory(self.path / 'physical')
        for name, raw in self.physical.items():
            self.lease.write_artifact(naming.flat_name(name), raw)
        self.lease.write_artifact(case.SEAL, canonical(j.group_seal(self.lease.checkpoint, 'physical', complete=True)))
        self.lease.write_artifact(case.OUTCOME, b'{"outcome":"completed"}')
        self.lease.finish()
        self.journal = s.inventory(self.path / 'journal')
        self.base = {p.name: p.read_bytes() for p in (self.path / 'case').iterdir() if not p.name.startswith('physical-')}
        self.transport = FakeGit()

    def tearDown(self):
        self.tmp.cleanup()

    def document(self, complete):
        return {'retention': {'case_identity': self.config['case_identity']}, 'complete': complete,
                'rows': [{'index': i, 'value': i / 3} for i in range(8)]}

    def bundle(self, **kw):
        args = dict(expected_config_sha256=self.writer.config_sha,
            expected_last_checkpoint_sha256=self.writer.previous,
            expected_genesis_sha256=self.store.genesis_sha256,
            expected_pointer_sha256=self.journal['HEAD'][:-1].decode(),
            expected_parent_sha=self.transport.head, expected_parent_tree_sha=self.transport.root)
        args.update(kw)
        return r.prepare_bundle(self.physical, self.journal, self.base, **args)

    def publisher(self, bundle=None, **kw):
        bundle = bundle or self.bundle()
        return r.Publisher(bundle, self.transport.invoke, expected_bundle_sha256=bundle.sha256,
                           clock=kw.get('clock', lambda: 0.))

    def replace_parent(self, *, status='completed', artifact_bytes=2 * 1024**2, changed_policy=False):
        m = copy.deepcopy(self.m)
        m['caps']['evidence_bytes'] = 32 * 1024**2
        if changed_policy:
            m['artifact_groups']['physical']['reserved_artifacts'][case.SEAL] //= 2
        store = s.EventDirectoryStore.create(self.path / 'replacement-journal', m)
        cp = store.read()
        lease = j.consume(store, expected_revision=cp.revision, expected_manifest_sha256=digest(m),
            binding=m['cases'][0], milliseconds=10000, artifact_bytes=artifact_bytes,
            directory=self.path / 'replacement-case', clock=lambda: 0.)
        for name, raw in self.base_original.items():
            lease.write_artifact(name, raw)
        for name, raw in self.physical.items():
            lease.write_artifact(naming.flat_name(name), raw)
        lease.write_artifact(case.SEAL, canonical(j.group_seal(lease.checkpoint, 'physical', complete=status == 'completed')))
        lease.write_artifact(case.OUTCOME, canonical({'outcome': status}))
        lease.finish(status)
        self.store = store
        self.lease = lease
        self.journal = s.inventory(store.path)
        self.base = {p.name: p.read_bytes() for p in lease.directory.iterdir() if not p.name.startswith('physical-')}

    def enlarge_base(self, *, collision=False):
        self.base_original['scores.npz'] = bytes(range(256)) * 1200
        if collision:
            self.base_original['scores.npz.part0000'] = b'independent original filename'
            self.m['required_artifacts'].append('scores.npz.part0000')
        self.config = e.configuration('remote-archive-large-test', self.m['cases'][0]['case_identity'],
            self.m['cases'][0]['plan_sha256'], self.base_original,
            budget_bytes=2 * 1024**2 - sum(case.CLOSURE_RESERVES.values()))
        self.m['artifact_groups'] = case.policy(self.config)
        self.writer = e.Writer.create(self.path / 'large-physical', self.config, existing_artifacts=self.base_original)
        self.writer.close('completed', 'end', snapshot=self.document(True))
        self.physical = e._inventory(self.path / 'large-physical')
        self.replace_parent()

    def assert_stopped_once(self, publisher, pattern):
        with self.assertRaisesRegex(r.Stopped, pattern):
            publisher.publish()
        before = len(self.transport.calls)
        with self.assertRaisesRegex(r.Stopped, 'no retry'):
            publisher.publish()
        self.assertEqual(len(self.transport.calls), before)

    def test_all_exact_bytes_single_commit_tree_and_immutable_readback(self):
        bundle = self.bundle()
        self.physical['unused_after_freeze'] = b'not part of prepared bytes'
        with self.assertRaises(TypeError):
            bundle.files['overwrite'] = b'x'
        publisher = self.publisher(bundle)
        result = publisher.publish()
        self.assertTrue(result['immutable_bytes_read_back'])
        self.assertTrue(result['exact_tree_delta_verified'])
        for path, raw in bundle.files.items():
            sha = self.transport.flatten(result['tree'])[path]
            self.assertEqual(self.transport.blobs[sha], raw)
        methods = [o for o, _ in self.transport.calls]
        self.assertEqual(methods.count('create_commit'), 1)
        self.assertEqual(methods.count('update_ref'), 1)
        self.assertEqual(methods.count('fetch_file'), len(bundle.files))
        self.assertEqual(publisher.usage()['unknown_response_bytes'], 0)
        self.assertEqual(publisher.usage()['unknown_response_count'], 0)
        self.assertEqual(publisher.usage()['response_charged_bytes'], publisher.usage()['response_bytes'])
        self.assertEqual(result['parent'], self.transport.initial_head)
        self.assertFalse(result['execution_restart_authorized'])
        self.assertFalse(result['scientific_admission_authorized'])
        self.assertFalse(result['remote_event_store_qualified'])
        history = s.restore({p.split('/archive/journal/', 1)[1]: raw for p, raw in bundle.files.items()
                            if '/archive/journal/' in p}, expected_genesis_sha256=self.store.genesis_sha256,
                            expected_pointer_sha256=self.journal['HEAD'][:-1].decode())
        self.assertEqual(history.revision_bytes[-1], canonical(self.lease.checkpoint.document))
        self.assertGreater(len(history.revision_bytes), 3)
        self.assert_stopped_once(publisher, 'no retry')

    def test_wrong_blob_and_tree_hash_stop_before_update(self):
        for name, pattern in [('wrong_blob', 'blob hash'), ('wrong_tree', 'tree content hash')]:
            with self.subTest(name=name):
                self.transport = FakeGit()
                setattr(self.transport, name, True)
                publisher = self.publisher()
                self.assert_stopped_once(publisher, pattern)
                self.assertFalse(any(o == 'update_ref' for o, _ in self.transport.calls))

    def test_unrelated_tree_modification_is_rejected(self):
        self.transport.unrelated_change = True
        self.assert_stopped_once(self.publisher(), 'unrelated path')
        self.assertFalse(any(o == 'create_commit' for o, _ in self.transport.calls))

    def test_wrong_exact_readback_stops_after_one_atomic_update(self):
        self.transport.bad_readback = True
        publisher = self.publisher()
        self.assert_stopped_once(publisher, 'stored bytes differ')
        self.assertTrue(publisher.receipt['update_may_have_landed'])
        self.assertEqual(sum(o == 'update_ref' for o, _ in self.transport.calls), 1)

    def test_lost_update_response_is_uncertain_and_never_retried(self):
        self.transport.lost_update = True
        publisher = self.publisher()
        self.assert_stopped_once(publisher, 'lost update response')
        self.assertEqual(self.transport.head, publisher.receipt['candidate'])
        self.assertTrue(publisher.receipt['update_may_have_landed'])
        self.assertEqual(sum(o == 'update_ref' for o, _ in self.transport.calls), 1)
        self.assertFalse(any(o == 'fetch_file' for o, _ in self.transport.calls))
        allowance = r.RESPONSE_RESERVATIONS['update_ref']
        self.assertEqual(publisher.usage()['unknown_response_bytes'], allowance)
        self.assertEqual(publisher.usage()['unknown_response_count'], 1)
        self.assertEqual(publisher.usage()['response_charged_bytes'], publisher.usage()['response_bytes'] + allowance)
        self.assertTrue(publisher.events[-1]['response_unknown'])
        self.assertEqual(publisher.events[-1]['response_reserved_bytes'], allowance)
        self.assertEqual(publisher.events[-1]['response_charged_bytes'], allowance)

    def test_initial_and_late_parent_conflicts_do_not_update(self):
        bundle = self.bundle()
        self.transport.head = self.transport.commit(self.transport.root, [self.transport.head], 'concurrent')
        self.assert_stopped_once(self.publisher(bundle), 'parent conflicts')
        self.assertEqual(len(self.transport.calls), 1)
        self.transport = FakeGit()
        self.transport.move_before_update = True
        self.assert_stopped_once(self.publisher(), 'parent changed')
        self.assertFalse(any(o == 'update_ref' for o, _ in self.transport.calls))

    def test_parent_tree_pin_and_existing_namespace_cannot_be_overwritten(self):
        self.assert_stopped_once(self.publisher(self.bundle(expected_parent_tree_sha='a' * 40)), 'parent tree pin')
        self.transport = FakeGit({'README.md': b'old', r.PREFIX + '/HEAD': b'existing immutable head'})
        self.assert_stopped_once(self.publisher(), 'overwrite prohibited')
        self.assertFalse(any(o == 'create_blob' for o, _ in self.transport.calls))

    def test_frozen_stored_request_response_call_and_elapsed_bounds(self):
        with self.assertRaisesRegex(ValueError, 'byte cap'):
            self.bundle(limits=r.Limits(stored_bytes=1))
        for field, value, pattern in [('request_bytes', 1, 'request/time'),
                                      ('response_bytes', 1, 'response/time'), ('calls', 1, 'call/request')]:
            with self.subTest(field=field):
                self.transport = FakeGit()
                limits = replace(r.Limits(), **{field: value})
                self.assert_stopped_once(self.publisher(self.bundle(limits=limits)), pattern)
                self.assertLessEqual(len(self.transport.calls), 1)
        self.transport = FakeGit()
        publisher = self.publisher(self.bundle(limits=r.Limits(seconds=1)), clock=lambda: self.transport.tick)
        self.assert_stopped_once(publisher, 'time bound')
        self.assertLessEqual(len(self.transport.calls), 2)

    def test_independent_bundle_pin_and_registered_source_bytes(self):
        bundle = self.bundle()
        with self.assertRaisesRegex(ValueError, 'bundle pin'):
            r.Publisher(bundle, self.transport.invoke, expected_bundle_sha256='a' * 64)
        self.base['scores.npz'] += b'corrupt'
        with self.assertRaisesRegex(ValueError, 'base evidence'):
            self.bundle()
        self.assertEqual(self.transport.calls, [])

    def test_valid_failed_case_is_retained_failed_without_resume_or_relabel(self):
        footer = json.loads(self.physical['outcome.json'])
        footer['status'] = 'failed'
        self.physical['outcome.json'] = canonical(footer)
        self.replace_parent(status='failed')
        bundle = self.bundle()
        summary = json.loads(bundle.manifest_bytes)['source_summary']
        self.assertEqual(summary['case_status'], 'failed')
        self.assertEqual(summary['physical']['status'], 'failed')
        self.publisher(bundle).publish()
        self.assertEqual(bundle.files[r.PREFIX + '/archive/physical/outcome.json'], self.physical['outcome.json'])
        self.assertFalse(summary['physical']['execution_restart_authorized'])

    def test_self_consistent_parent_allocation_cannot_hide_physical_budget(self):
        self.replace_parent(artifact_bytes=2 * 1024**2 + 1)
        with self.assertRaisesRegex(ValueError, 'cumulative budget'):
            self.bundle()
        self.assertEqual(self.transport.calls, [])

    def test_changed_self_consistent_closure_policy_rejected(self):
        self.replace_parent(changed_policy=True)
        with self.assertRaisesRegex(ValueError, 'closure policy'):
            self.bundle()
        self.assertEqual(self.transport.calls, [])

    def test_parent_case_above_fixed_18_mib_allocation_rejected(self):
        self.replace_parent(artifact_bytes=19 * 1024**2)
        with self.assertRaisesRegex(ValueError, '18-MiB allocation'):
            self.bundle()
        self.assertEqual(self.transport.calls, [])

    def test_frozen_publisher_state_mutation_stops_before_transport(self):
        publisher = self.publisher()
        publisher.freeze['parent'] = 'a' * 40
        self.assert_stopped_once(publisher, 'frozen publication state changed')
        self.assertEqual(self.transport.calls, [])

    def test_large_binary_original_is_split_bounded_and_restored_exactly(self):
        self.enlarge_base()
        bundle = self.bundle()
        source = r.PREFIX + '/archive/base/scores.npz'
        record = json.loads(bundle.manifest_bytes)['original_files'][source]
        self.assertEqual(record['stored_paths'], [source + '.part0000', source + '.part0001'])
        self.assertNotIn(source, bundle.files)
        self.assertTrue(all(len(v) <= r.MAX_BLOB_BYTES for v in bundle.files.values()))
        result = self.publisher(bundle).publish()
        published = {p: self.transport.blobs[sha] for p, sha in self.transport.flatten(result['tree']).items()
                     if p.startswith(r.PREFIX + '/')}
        originals = r.restore_original_files(published, expected_manifest_sha256=e.sha(bundle.manifest_bytes))
        self.assertEqual(originals[source], self.base_original['scores.npz'])
        self.assertEqual(result['original_files_reconstructed'], len(originals))
        self.assertTrue(all(len(base64.b64decode(p['content'])) <= r.MAX_BLOB_BYTES
                            for op, p in self.transport.calls if op == 'create_blob'))

    def test_large_original_part_order_is_verified_independently(self):
        self.enlarge_base()
        bundle = self.bundle()
        files = dict(bundle.files)
        manifest_doc = json.loads(bundle.manifest_bytes)
        source = r.PREFIX + '/archive/base/scores.npz'
        manifest_doc['original_files'][source]['stored_paths'].reverse()
        raw = canonical(manifest_doc)
        files[r.PREFIX + '/manifest.json'] = raw
        files[r.PREFIX + '/HEAD'] = e.sha(raw).encode() + b'\n'
        with self.assertRaisesRegex(ValueError, 'transport order'):
            r.restore_original_files(files, expected_manifest_sha256=e.sha(raw))

    def test_large_original_generated_part_path_collision_is_rejected(self):
        self.enlarge_base(collision=True)
        with self.assertRaisesRegex(ValueError, 'immutable path collision'):
            self.bundle()
        self.assertEqual(self.transport.calls, [])


if __name__ == '__main__':
    unittest.main()
