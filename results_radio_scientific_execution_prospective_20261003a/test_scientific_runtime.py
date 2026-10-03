"""Small in-memory closure tests; no installed scientific runtime is certified."""
import copy
import hashlib
import unittest
import scientific_runtime as r


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def fixture(actual=False):
    contents = {'code': b'pass\n', 'input': b'{}\n', 'python': b'fixture interpreter',
                'elf': b'fixture ELF', 'plugin': b'fixture plugin'}
    inventory = {}
    for key, role, location, path, mode in (
        ('code', 'code', 'repository', 'src/future.py', '100644'),
        ('input', 'input', 'repository', 'config/source.json', '100644'),
        ('python', 'runtime', 'runtime', '/fixture/python', '100755'),
        ('elf', 'elf', 'runtime', '/fixture/libhdf5.so', '100755'),
        ('plugin', 'plugin', 'runtime', '/fixture/bitshuffle.so', '100755')):
        inventory[key] = {'role': role, 'location': location, 'path': path, 'mode': mode, **pin(contents[key])}
    edges = {'elf': [], 'plugin': ['elf']}
    runtime = {'python': '3.12.14', 'numpy': '2.3.5', 'h5py': '3.16.0',
               'hdf5': '2.0.0', 'hdf5plugin': '7.1.0', 'python_executable_sha256': pin(contents['python'])['sha256']}
    doc = {'schema': r.SCHEMA, 'mode': r.MODE, 'status': 'PENDING', 'inventory': inventory,
           'role_inventories': r.validate_inventory(inventory), 'dependency_edges': edges,
           'runtime_identity': runtime, 'limits': copy.deepcopy(r.LIMITS),
           'source_contract_sha256': '1'*64, 'trial_protocol_sha256': '2'*64,
           'codec_certificate_sha256': '3'*64, 'scientific_execution_authorized': False,
           'scientific_allocation_charged': False}
    if actual:
        doc.update(schema='radio-scientific-executable-freeze-v1', mode='SCIENTIFIC_EXECUTABLE_ONLY',
                   status='QUALIFIED', domain='synthetic-test-fixture')
    return doc, contents, inventory, edges, runtime


def publication_fixture(inventory, contents):
    """Actual in-memory Git hashes, with no Git command or service involved."""
    nested = {}; trees = {}
    def obj(kind, raw):
        return hashlib.sha1(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    for identity, row in inventory.items():
        if row['location'] != 'repository':
            continue
        parts = row['path'].split('/'); current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        data = contents[identity]
        current[parts[-1]] = {'mode': row['mode'], 'type': 'blob', 'sha': obj('blob', data)}
    def build(node):
        entries = {}
        for name, value in node.items():
            entries[name] = value if 'mode' in value else {'mode': '040000', 'type': 'tree', 'sha': build(value)}
        names = sorted(entries, key=lambda n: (n+('/' if entries[n]['type'] == 'tree' else '')).encode())
        raw = b''.join(entries[n]['mode'].lstrip('0').encode()+b' '+n.encode()+b'\0'+bytes.fromhex(entries[n]['sha']) for n in names)
        sha = obj('tree', raw)
        trees[sha] = {'sha': sha, 'truncated': False, 'tree': [{'path': n, **entries[n]} for n in names]}
        return sha
    root = build(nested)
    commit_raw = b'tree '+root.encode()+b'\nauthor Fixture <fixture@example.invalid> 1 +0000\ncommitter Fixture <fixture@example.invalid> 1 +0000\n\nfixture only\n'
    commit = obj('commit', commit_raw)
    def read_published(request_commit, path):
        identity = next(k for k, row in inventory.items() if row['location'] == 'repository' and row['path'] == path)
        row = inventory[identity]; data = contents[identity]; chain = []; tree = root
        for name in path.split('/'):
            doc = copy.deepcopy(trees[tree]); chain.append(doc)
            entry = next(row for row in doc['tree'] if row['path'] == name)
            tree = entry['sha']
        return {'commit': request_commit, 'tree': root, 'path': path, 'mode': row['mode'],
                'bytes': row['bytes'], 'data': data, 'blob': obj('blob', data),
                'commit_raw': commit_raw, 'tree_chain': chain}
    return commit, root, read_published


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.doc, self.contents, self.inventory, self.edges, self.runtime = fixture()
        self.reads = []
        self.public_commit, self.public_tree, self.public_reader = publication_fixture(self.inventory, self.contents)

    def verifier(self, doc=None, actual=False):
        raw = r.canonical(self.doc if doc is None else doc)
        cls = r.ScientificFreeze if actual else r.ProspectiveFreeze
        return cls(raw, pin(raw), expected_inventory=self.inventory,
                   expected_dependency_edges=self.edges, expected_runtime_identity=self.runtime)

    def local(self, location, path):
        self.reads.append(('local', location, path))
        key = next(k for k, row in self.inventory.items() if (row['location'], row['path']) == (location, path))
        row = self.inventory[key]
        return {'mode': row['mode'], 'bytes': row['bytes'], 'data': self.contents[key]}

    def published(self, commit, path):
        return self.public_reader(commit, path)

    def verify(self, verifier=None, **changes):
        args = dict(read_file=self.local, published_commit=self.public_commit, published_tree=self.public_tree,
                    read_published_file=self.published, expected_source_contract_sha256='1'*64,
                    expected_trial_protocol_sha256='2'*64, expected_codec_certificate_sha256='3'*64,
                    runtime_identity=self.runtime)
        args.update(changes)
        return (verifier or self.verifier()).verify(**args).record()

    def test_complete_independent_closure_and_immutable_source_readback(self):
        got = self.verify()
        self.assertEqual(got['published_files'], 2)
        self.assertEqual(got['closure_files'], 5)
        self.assertFalse(got['scientific_execution_authorized'])
        self.assertFalse(got['actual_elf_inspection_performed'])

    def test_no_self_derived_pin_default(self):
        raw = r.canonical(self.doc)
        with self.assertRaises(TypeError):
            r.ProspectiveFreeze(raw)
        bad = pin(raw); bad['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'independent'):
            r.ProspectiveFreeze(raw, bad, expected_inventory=self.inventory,
                               expected_dependency_edges=self.edges, expected_runtime_identity=self.runtime)

    def test_repinning_manifest_cannot_change_independently_expected_code(self):
        doc = copy.deepcopy(self.doc); doc['inventory']['code']['sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'independent closure'):
            self.verifier(doc)

    def test_unresolved_transitive_elf_dependency_rejected(self):
        edges = {'elf': ['missing-lib'], 'plugin': ['elf']}
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            r.validate_edges(edges, self.inventory)

    def test_missing_native_terminal_node_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Complete ELF'):
            r.validate_edges({'plugin': ['elf']}, self.inventory)

    def test_missing_whole_role_rejected(self):
        inv = copy.deepcopy(self.inventory); del inv['plugin']
        with self.assertRaisesRegex(ValueError, 'inventories all'):
            r.validate_inventory(inv)

    def test_runtime_location_alias_rejected(self):
        inv = copy.deepcopy(self.inventory); inv['plugin']['path'] = inv['elf']['path']
        with self.assertRaisesRegex(ValueError, 'Aliased'):
            r.validate_inventory(inv)

    def test_symlink_mode_rejected(self):
        inv = copy.deepcopy(self.inventory); inv['code']['mode'] = '120000'
        with self.assertRaisesRegex(ValueError, 'ordinary'):
            r.validate_inventory(inv)

    def test_code_must_be_repository_provenance(self):
        inv = copy.deepcopy(self.inventory); inv['code'].update(location='runtime', path='/fixture/code.py')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            r.validate_inventory(inv)

    def test_file_replaced_after_freeze_rejected(self):
        verifier = self.verifier(); self.contents['elf'] = b'replacement ELF'
        with self.assertRaisesRegex(ValueError, 'File bytes'):
            self.verify(verifier)

    def test_current_mode_changed_rejected(self):
        def bad(location, path):
            out = self.local(location, path); out['mode'] = '100644' if out['mode'] == '100755' else '100755'
            return out
        with self.assertRaisesRegex(ValueError, 'ordinary mode'):
            self.verify(read_file=bad)

    def test_mutable_publication_branch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'immutable Git'):
            self.verify(published_commit='m43-support-qualification')

    def test_other_publication_tree_rejected(self):
        def bad(commit, path):
            out = self.published(commit, path); out['tree'] = 'c'*40
            return out
        with self.assertRaisesRegex(ValueError, 'publication location'):
            self.verify(read_published_file=bad)

    def test_forged_git_blob_rejected(self):
        def bad(commit, path):
            out = self.published(commit, path); out['blob'] = 'c'*40
            return out
        with self.assertRaisesRegex(ValueError, 'Git blob'):
            self.verify(read_published_file=bad)

    def test_source_specific_codec_and_protocol_external_anchors_required(self):
        for key in ('expected_source_contract_sha256', 'expected_trial_protocol_sha256', 'expected_codec_certificate_sha256'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'provenance'):
                self.verify(**{key: '9'*64})

    def test_runtime_identity_independent_of_file_repin(self):
        with self.assertRaisesRegex(ValueError, 'runtime identity'):
            self.verify(runtime_identity={'python': 'different'})

    def test_fixed_limits_cannot_be_promoted_by_repin(self):
        doc = copy.deepcopy(self.doc); doc['limits']['total_milliseconds'] += 1
        with self.assertRaisesRegex(ValueError, 'limits'):
            self.verifier(doc)

    def test_candidate_codec_only_cannot_use_actual_freeze_schema(self):
        with self.assertRaisesRegex(ValueError, 'mode'):
            self.verifier(actual=True)

    def test_actual_schema_fixture_can_be_authenticated_without_authority(self):
        doc, _, _, _, _ = fixture(actual=True)
        got = self.verify(self.verifier(doc, actual=True))
        self.assertEqual(got['domain'], 'synthetic-test-fixture')
        self.assertFalse(got['scientific_execution_authorized'])

    def test_duplicate_json_keys_not_accepted_even_with_matching_raw_pin(self):
        raw = b'{"a":1,"a":2}\n'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            r.load_raw(raw, pin(raw))

    def test_raw_cap_and_bool_byte_count_rejected(self):
        raw = r.canonical(self.doc)
        for bad in ({'bytes': True, 'sha256': pin(raw)['sha256']}, {'bytes': len(raw), 'sha256': '0'*64}):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'bounded pin'):
                r.load_raw(raw, bad)

    def test_verification_records_cannot_be_mutated_through_returned_dict(self):
        record = self.verifier().verify(read_file=self.local, published_commit=self.public_commit, published_tree=self.public_tree,
                    read_published_file=self.published, expected_source_contract_sha256='1'*64,
                    expected_trial_protocol_sha256='2'*64, expected_codec_certificate_sha256='3'*64,
                    runtime_identity=self.runtime)
        external = record.record(); external['scientific_execution_authorized'] = True
        self.assertFalse(record.record()['scientific_execution_authorized'])

    def test_verification_result_cannot_be_directly_manufactured(self):
        with self.assertRaisesRegex(ValueError, 'maintained verifier'):
            r.VerifiedFreeze(r.canonical({'scientific_execution_authorized': True}))

    def test_original_source_raw_commit_must_match_expected_immutable_commit(self):
        def bad(commit, path):
            got = self.published(commit, path); got['commit_raw'] += b'extra'
            return got
        with self.assertRaisesRegex(ValueError, 'raw commit'):
            self.verify(read_published_file=bad)

    def test_missing_tree_ancestry_and_unrelated_same_blob_path_rejected(self):
        def missing(commit, path):
            got = self.published(commit, path); got['tree_chain'].pop()
            return got
        with self.assertRaisesRegex(ValueError, 'path ancestry'):
            self.verify(read_published_file=missing)
        def different(commit, path):
            got = self.published(commit, path)
            got['tree_chain'][-1]['tree'][0]['path'] = 'other-file'
            return got
        with self.assertRaisesRegex(ValueError, 'tree raw content hash'):
            self.verify(read_published_file=different)

    def test_incomplete_runtime_version_identity_refused_for_actual_schema(self):
        doc, _, _, _, _ = fixture(actual=True)
        doc['runtime_identity'].pop('numpy')
        raw = r.canonical(doc)
        with self.assertRaisesRegex(ValueError, 'runtime identity required'):
            r.ScientificFreeze(raw, pin(raw), expected_inventory=self.inventory,
                expected_dependency_edges=self.edges, expected_runtime_identity=doc['runtime_identity'])


if __name__ == '__main__':
    unittest.main()
