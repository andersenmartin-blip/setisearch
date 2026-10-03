"""Tiny fake Git callbacks and metadata accounting; no actual publication."""
import copy
import hashlib
import json
import unittest
import scientific_store as s
from scientific_runtime import canonical, digest, LIMITS, MIB
from test_scientific_runtime import pin, fixture as runtime_fixture, publication_fixture
import scientific_runtime as runtime


def identity(text):
    return hashlib.sha256(text.encode()).hexdigest()


def cases_fixture():
    return [{'case_identity': identity('case'+str(i)), 'role': 'calibration' if i < 127 else 'evaluation',
             'context_sha256': identity('context'), 'source_contract_sha256': identity('source'),
             'noise_law_sha256': identity('law'), 'plan_sha256': identity('plan'+str(i))} for i in range(151)]


def current_admission_fixture(verified_closure, expected_basis, *, role='pilot', row_receipt_pins=None):
    """Fixture only: caller supplies a closure from the *real* detached validator.

    This builder refuses actual evidence and emits no public/store claim. Receiver
    integration tests can share it without monkeypatching either verifier.
    """
    closure = verified_closure.record()
    if closure['evidence_domain'] != 'synthetic-test-fixture':
        raise ValueError('Fixture builder cannot manufacture actual scientific admission')
    if row_receipt_pins is None:
        row_receipt_pins = {f'epoch{i}_{kind}': {'bytes': 32, 'sha256': identity(f'row{i}{kind}')}
                            for i in (1, 2, 3) for kind in ('on', 'off')}
    context = (closure['pilot_receiver_context_sha256'] if role == 'pilot'
               else expected_basis['receiver_context_sha256s'][role])
    session_identity = identity('session/'+role)
    cas_law = {'schema': 'radio-scientific-atomic-cas-qualification-v1', 'domain': 'synthetic-test-fixture',
               'repository': s.REPOSITORY, 'branch': s.BRANCH, 'atomic_expected_revision_cas': True,
               'immutable_readback_required': True, 'no_retries': True, 'qualified': True}
    cas_raw = canonical(cas_law)
    session = {'schema': 'radio-scientific-source-session-proof-v1', 'domain': 'synthetic-test-fixture',
               'session_identity': session_identity, 'source_contract_sha256': closure['new_executable_source_contract_sha256'],
               'context_sha256': context, 'window_identity': expected_basis['window_identities'][role],
               'role': role, 'row_receipt_pins': row_receipt_pins, 'session_ordinal': ('calibration', 'validation', 'pilot').index(role),
               'requests_used': 6, 'bytes_used': 192, 'started_epoch_milliseconds': 1000,
               'deadline_epoch_milliseconds': 1201000, 'no_retries': True, 'active': True}
    ack = {'schema': 'radio-scientific-irrevocable-store-ack-v1', 'domain': 'synthetic-test-fixture',
           'repository': s.REPOSITORY, 'branch': s.BRANCH,
           'ledger_revision': closure['acquisition_ledger_revision'],
           'ledger_sha256': closure['acquisition_ledger_sha256'],
           'allocation_sha256': closure['document_sha256s']['scientific_allocation'],
           'trial_allocation_sha256': closure['trial_allocation_sha256'],
           'trial_case_identity': closure['trial_case_identity'],
           'trial_protocol_sha256': closure['trial_protocol_sha256'], 'session_identity': session_identity,
           'source_contract_sha256': closure['new_executable_source_contract_sha256'],
           'row_receipt_pins': row_receipt_pins, 'atomic_expected_revision_cas': True,
           'cas_qualification_sha256': pin(cas_raw)['sha256'],
           'irrevocable': True, 'accepted': True, 'refund_or_retry_allowed': False}
    ack_raw, session_raw = canonical(ack), canonical(session)
    proof = {'schema': s.PROOF_SCHEMA, 'domain': 'synthetic-test-fixture', 'status': 'PENDING',
             'closure_sha256': hashlib.sha256(verified_closure.payload).hexdigest(),
             'basis_sha256': closure['basis_sha256'], 'role': role, 'context_sha256': context,
             'receiver_bank_sha256': expected_basis['receiver_bank_sha256s'][role],
             'window_identity': expected_basis['window_identities'][role],
             'source_inventory_sha256': expected_basis['source_inventory_sha256'],
             'source_contract_sha256': closure['new_executable_source_contract_sha256'],
             'runtime_identity_sha256': digest(closure['runtime_identity']),
             'trial_protocol_sha256': closure['trial_protocol_sha256'],
             'scientific_allocation_sha256': closure['document_sha256s']['scientific_allocation'],
             'trial_allocation_sha256': closure['trial_allocation_sha256'],
             'trial_case_identity': closure['trial_case_identity'],
             'acquisition_ledger_revision': closure['acquisition_ledger_revision'],
             'acquisition_ledger_sha256': closure['acquisition_ledger_sha256'],
             'store_acknowledgement_sha256': pin(ack_raw)['sha256'],
             'session_proof_sha256': pin(session_raw)['sha256'], 'session_identity': session_identity,
             'row_receipt_pins': row_receipt_pins, 'irrevocable': True, 'refund_or_retry_allowed': False}
    raw = canonical(proof)
    return {'raw_proof_bytes': raw, 'expected_raw_pin': pin(raw), 'verified_closure': verified_closure,
            'expected_basis': expected_basis, 'raw_store_acknowledgement': ack_raw,
            'expected_store_acknowledgement_pin': pin(ack_raw), 'raw_session_proof': session_raw,
            'expected_session_proof_pin': pin(session_raw), 'expected_row_receipt_pins': row_receipt_pins,
            'raw_cas_qualification': cas_raw, 'expected_cas_qualification_pin': pin(cas_raw),
            'expected_current_session': {'session_identity': session_identity, 'now_epoch_milliseconds': 2000}}


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.cases = cases_fixture()
        self.doc = s.phase_genesis(self.cases, self.cases)

    def consume(self, index=0):
        row = self.cases[index]; quota = LIMITS[row['role']]
        return {'ordinal': len(self.doc['events']), 'kind': 'consume', 'binding': row,
                'milliseconds': quota['milliseconds'], 'artifact_bytes': quota['artifact_bytes'],
                'attempt_identity': identity('attempt'+str(index))}

    def add(self, event):
        raw = canonical(self.doc)
        new = s.append_phase_event(raw, pin(raw), event, expected_cases=self.cases)
        self.doc = __import__('json').loads(new)

    def finish(self, outcome='completed', elapsed=1):
        return {'ordinal': len(self.doc['events']), 'kind': 'finish',
                'attempt_identity': self.doc['events'][-1]['attempt_identity'],
                'outcome': outcome, 'elapsed_milliseconds': elapsed}

    def test_exact_phase_totals_and_separate_protected_overhead(self):
        for i in range(151):
            self.add(self.consume(i)); self.add(self.finish())
        out = s.validate_phase_ledger(self.doc, self.cases)
        self.assertEqual(out['reserved_case_milliseconds'], 7000000)
        self.assertEqual(out['reserved_case_artifact_bytes'], 940*MIB)
        self.assertEqual(out['reserved_case_artifact_bytes']+8*MIB+76*MIB, 1024**3)
        self.assertEqual(out['reserved_case_milliseconds']+200000, 7200000)
        self.assertFalse(out['scientific_allocation_charged'])

    def test_partial_case_remains_fully_consumed(self):
        self.add(self.consume())
        out = s.validate_phase_ledger(self.doc, self.cases)
        self.assertEqual(out['reserved_case_milliseconds'], 40000)
        self.assertEqual(out['reserved_case_artifact_bytes'], 4*MIB)
        with self.assertRaisesRegex(ValueError, 'prior case remains consumed'):
            self.add(self.consume(1))

    def test_failed_case_charged_and_no_continuation(self):
        self.add(self.consume()); self.add(self.finish('failed', elapsed=40001))
        out = s.validate_phase_ledger(self.doc, self.cases)
        self.assertTrue(out['attempt_failed'])
        self.assertEqual(out['reserved_case_artifact_bytes'], 4*MIB)
        with self.assertRaisesRegex(ValueError, 'permanently closed'):
            self.add(self.consume(1))

    def test_case_cannot_borrow_overhead_or_use_underreservation(self):
        for key, value in (('milliseconds', 40001), ('artifact_bytes', 4*MIB+1), ('milliseconds', 39999)):
            event = self.consume(); event[key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'Exact per-case'):
                self.add(event)

    def test_independent_case_context_and_order_cannot_change_by_repin(self):
        for field in ('context_sha256', 'source_contract_sha256', 'plan_sha256', 'role'):
            event = self.consume(); event['binding'] = copy.deepcopy(event['binding']); event['binding'][field] = '9'*64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Ordered fresh case'):
                self.add(event)

    def test_repeat_case_and_attempt_identity_rejected(self):
        self.add(self.consume()); self.add(self.finish())
        with self.assertRaisesRegex(ValueError, 'Ordered fresh'):
            self.add(self.consume())
        event = self.consume(1); event['attempt_identity'] = identity('attempt0')
        with self.assertRaisesRegex(ValueError, 'reuse prohibited'):
            self.add(event)

    def test_complete_over_time_rejected_then_failed_is_retained(self):
        self.add(self.consume())
        with self.assertRaisesRegex(ValueError, 'Over-time'):
            self.add(self.finish(elapsed=40001))
        self.add(self.finish('failed', elapsed=40001))
        self.assertTrue(s.validate_phase_ledger(self.doc, self.cases)['attempt_failed'])

    def test_overhead_can_finalize_failure_but_never_refund(self):
        self.add(self.consume()); self.add(self.finish('failed'))
        event = {'ordinal': 2, 'kind': 'overhead', 'identity': identity('closure'), 'category': 'failure',
                 'milliseconds': 200000, 'bytes': 76*MIB, 'sha256': identity('receipt')}
        self.add(event)
        out = s.validate_phase_ledger(self.doc, self.cases)
        self.assertEqual(out['reserved_case_milliseconds'], 40000)
        bad = copy.deepcopy(event); bad.update(ordinal=3, identity=identity('extra'), bytes=1, milliseconds=0)
        with self.assertRaisesRegex(ValueError, 'overhead reservation'):
            self.add(bad)

    def test_refund_reset_and_negative_accounting_rejected(self):
        self.add(self.consume())
        for kind in ('refund', 'reset', 'retry'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'Unsupported'):
                self.add({'ordinal': 1, 'kind': kind})
        event = {'ordinal': 1, 'kind': 'overhead', 'identity': identity('negative'), 'category': 'setup',
                 'milliseconds': -1, 'bytes': 0, 'sha256': identity('receipt')}
        with self.assertRaisesRegex(ValueError, 'Nonnegative'):
            self.add(event)

    def test_metadata_bool_is_not_integer_quota(self):
        event = self.consume(); event['milliseconds'] = True
        with self.assertRaisesRegex(ValueError, 'Exact per-case'):
            self.add(event)

    def test_wrong_checkpoint_pin_blocks_append(self):
        raw = canonical(self.doc); wrong = pin(raw); wrong['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'independent bounded pin'):
            s.append_phase_event(raw, wrong, self.consume(), expected_cases=self.cases)

    def test_artifact_overcap_and_unpublished_provenance_rejected(self):
        self.add(self.consume())
        publication = {'repository': s.REPOSITORY, 'commit': 'a'*40, 'tree': 'b'*40,
                       'path': 'results_radio_scientific_fixture/artifact.bin', 'blob': 'c'*40, 'sha256': 'd'*64}
        event = {'ordinal': 1, 'kind': 'artifact', 'attempt_identity': identity('attempt0'),
                 'name': 'scores.bin', 'bytes': 4*MIB+1, 'sha256': 'd'*64, 'publication': publication}
        with self.assertRaisesRegex(ValueError, 'artifact capacity'):
            self.add(event)
        event['bytes'] = 1; event['publication']['commit'] = 'main'
        with self.assertRaisesRegex(ValueError, 'immutable Git'):
            self.add(event)


def git_object(kind, raw):
    return hashlib.sha1(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


class FakeGit:
    """Only in-memory Git objects; never a connector or repository subprocess."""
    def __init__(self):
        self.trees = {}; self.commits = {}; self.files = {}; self.operations = []
        self.head = self.commit(self.tree({}), None)
        self.fail = None; self.race = False; self.extra_path = False; self.bad_mode = False
        self.bad_blob = False; self.wrong_parent = False; self.cas_attempts = 0

    def tree(self, entries):
        names = sorted(entries, key=lambda n: (n+('/' if entries[n]['type'] == 'tree' else '')).encode())
        raw = b''.join(entries[n]['mode'].lstrip('0').encode()+b' '+n.encode()+b'\0'+bytes.fromhex(entries[n]['sha']) for n in names)
        sha = git_object('tree', raw)
        self.trees[sha] = {'sha': sha, 'truncated': False,
                           'tree': [{'path': n, **entries[n]} for n in names]}
        return sha

    def commit(self, tree, parent):
        raw = b'tree '+tree.encode()+b'\n'
        if parent is not None:
            raw += b'parent '+parent.encode()+b'\n'
        raw += b'author Fixture <fixture@example.invalid> 1 +0000\ncommitter Fixture <fixture@example.invalid> 1 +0000\n\nfixture only\n'
        sha = git_object('commit', raw); self.commits[sha] = {'sha': sha, 'data': raw}
        return sha

    def invoke(self, method, params):
        self.operations.append(method)
        if method == self.fail:
            raise RuntimeError('injected partial callback failure')
        if method == 'read_ref':
            return {'repository': s.REPOSITORY, 'branch': s.BRANCH, 'commit': self.head}
        if method == 'read_commit':
            return copy.deepcopy(self.commits[params['commit']])
        if method == 'read_tree':
            return copy.deepcopy(self.trees[params['tree']])
        if method == 'create_candidate':
            file = params['files'][0]; blob = git_object('blob', file['data'])
            leaf = {'mode': '100755' if self.bad_mode else '100644', 'type': 'blob', 'sha': blob}
            parts = file['path'].split('/'); tree = self.tree({parts[-1]: leaf})
            for part in reversed(parts[:-1]):
                tree = self.tree({part: {'mode': '040000', 'type': 'tree', 'sha': tree}})
            if self.extra_path:
                entries = {row['path']: {k: row[k] for k in ('mode', 'type', 'sha')} for row in self.trees[tree]['tree']}
                entries['unrelated.txt'] = {'mode': '100644', 'type': 'blob', 'sha': git_object('blob', b'bad')}
                tree = self.tree(entries)
            candidate = self.commit(tree, None if self.wrong_parent else params['parent'])
            self.files[(candidate, file['path'])] = {'repository': s.REPOSITORY, 'commit': candidate,
                'tree': tree, 'path': file['path'], 'mode': '100644', 'blob': '0'*40 if self.bad_blob else blob,
                'bytes': len(file['data']), 'data': file['data']}
            return {'commit': candidate, 'tree': tree}
        if method == 'atomic_ref_compare_and_swap':
            self.cas_attempts += 1
            if self.race:
                self.head = self.commit(self.tree({}), self.head)
            accepted = self.head == params['expected_revision']
            if accepted:
                self.head = params['candidate']
            return {'repository': s.REPOSITORY, 'branch': s.BRANCH,
                    'expected_revision': params['expected_revision'], 'commit': params['candidate'],
                    'atomic': True, 'accepted': accepted}
        if method == 'read_immutable_file':
            return copy.deepcopy(self.files[(params['commit'], params['path'])])
        raise AssertionError('Unexpected fake operation '+method)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.git = FakeGit()
        self.runtime_doc, self.runtime_data, self.runtime_inventory, self.runtime_edges, self.runtime_identity = runtime_fixture(actual=True)
        self.manifest = canonical(self.runtime_doc)
        self.location = {'repository': s.REPOSITORY, 'branch': s.BRANCH,
                         'prefix': 'results_radio_scientific_execution_prospective_20261003a/fixture-only'}
        self.law = {'schema': 'radio-scientific-atomic-cas-qualification-v1', 'domain': 'synthetic-test-fixture',
                    'repository': s.REPOSITORY, 'branch': s.BRANCH, 'atomic_expected_revision_cas': True,
                    'immutable_readback_required': True, 'no_retries': True, 'qualified': True}
        self.spec = {'schema': s.STORE_SCHEMA, 'domain': 'synthetic-test-fixture', **self.location,
                     'manifest_sha256': pin(self.manifest)['sha256'], 'cas_qualification_sha256': pin(canonical(self.law))['sha256'],
                     'max_calls': 100, 'max_response_bytes': 1024**2}
        self.payload = canonical({'fixture': 'checkpoint metadata only'})
        self.original = self.git.head

    def store(self, spec=None, law=None, **changes):
        raw_spec = canonical(self.spec if spec is None else spec)
        raw_law = canonical(self.law if law is None else law)
        args = dict(expected_location=self.location, raw_cas_qualification=raw_law,
                    expected_cas_qualification_pin=pin(raw_law), expected_manifest_sha256=pin(self.manifest)['sha256'],
                    execution_verifier=self.verify_runtime)
        args.update(changes)
        return s.ScientificGitStore(self.git.invoke, raw_spec, pin(raw_spec), **args)

    def verify_runtime(self, manifest):
        self.assertEqual(manifest, self.runtime_doc)
        verifier = runtime.ScientificFreeze(self.manifest, pin(self.manifest),
                   expected_inventory=self.runtime_inventory, expected_dependency_edges=self.runtime_edges,
                   expected_runtime_identity=self.runtime_identity)
        def local(location, path):
            key = next(k for k, row in self.runtime_inventory.items() if (row['location'], row['path']) == (location, path))
            row = self.runtime_inventory[key]
            return {'mode': row['mode'], 'bytes': row['bytes'], 'data': self.runtime_data[key]}
        commit, tree, public = publication_fixture(self.runtime_inventory, self.runtime_data)
        return verifier.verify(read_file=local, published_commit=commit, published_tree=tree,
                    read_published_file=public, expected_source_contract_sha256='1'*64,
                    expected_trial_protocol_sha256='2'*64, expected_codec_certificate_sha256='3'*64,
                    runtime_identity=self.runtime_identity)

    def publish(self, store):
        return store.publish(expected_revision=self.original, relative_path='ledger.json', raw_document=self.payload,
                             expected_document_pin=pin(self.payload), execution_manifest=self.manifest,
                             expected_execution_manifest_pin=pin(self.manifest), attempt_identity=identity('one attempt'))

    def test_one_simulated_atomic_cas_exact_parent_delta_and_raw_readback(self):
        store = self.store(); receipt = self.publish(store).record()
        self.assertEqual(receipt['status'], 'SIMULATION_ONLY')
        self.assertFalse(receipt['scientific_execution_authorized'])
        self.assertEqual(self.git.cas_attempts, 1)
        self.assertEqual(receipt['parent'], self.original)
        self.assertIn('read_immutable_file', self.git.operations)
        self.assertNotIn('update_ref', self.git.operations)

    def test_fast_forward_only_qualification_rejected_before_callback(self):
        law = copy.deepcopy(self.law); law['atomic_expected_revision_cas'] = False
        with self.assertRaisesRegex(ValueError, 'fast-forward is insufficient'):
            self.store(law=law)
        self.assertEqual(self.git.operations, [])

    def test_cas_race_stops_without_retry_or_new_parent(self):
        self.git.race = True; store = self.store()
        with self.assertRaisesRegex(ValueError, 'CAS rejected'):
            self.publish(store)
        self.assertEqual(self.git.cas_attempts, 1)
        calls = len(self.git.operations)
        with self.assertRaises(s.Stopped):
            self.publish(store)
        self.assertEqual(len(self.git.operations), calls)
        self.assertTrue(store.receipts[-1]['original_charges_retained'])

    def test_partial_remote_failure_keeps_ambiguous_candidate_and_stops(self):
        self.git.fail = 'read_immutable_file'; store = self.store()
        with self.assertRaises(s.Stopped):
            self.publish(store)
        self.assertNotEqual(self.git.head, self.original)
        self.assertTrue(store.receipts[-1]['publication_may_have_landed'])
        self.assertTrue(store.stopped)

    def test_unrelated_tree_change_rejected_before_cas(self):
        self.git.extra_path = True
        with self.assertRaisesRegex(ValueError, 'undeclared path'):
            self.publish(self.store())
        self.assertEqual(self.git.cas_attempts, 0)

    def test_executable_mode_rejected_even_with_valid_git_hash(self):
        self.git.bad_mode = True
        with self.assertRaisesRegex(ValueError, 'file mode'):
            self.publish(self.store())
        self.assertEqual(self.git.cas_attempts, 0)

    def test_candidate_wrong_parent_rejected_before_cas(self):
        self.git.wrong_parent = True
        with self.assertRaisesRegex(ValueError, 'exact parent'):
            self.publish(self.store())
        self.assertEqual(self.git.cas_attempts, 0)

    def test_readback_blob_failure_after_cas_is_closed_not_retried(self):
        self.git.bad_blob = True; store = self.store()
        with self.assertRaisesRegex(ValueError, 'Git blob'):
            self.publish(store)
        self.assertEqual(self.git.cas_attempts, 1)
        self.assertTrue(store.stopped)

    def test_changed_current_revision_not_silently_rebased(self):
        self.git.head = self.git.commit(self.git.tree({}), self.original)
        with self.assertRaisesRegex(ValueError, 'expected branch revision'):
            self.publish(self.store())
        self.assertNotIn('create_candidate', self.git.operations)

    def test_transport_response_overcap_stops_after_charge(self):
        spec = copy.deepcopy(self.spec); spec['max_response_bytes'] = 10; store = self.store(spec)
        with self.assertRaisesRegex(s.Stopped, 'response capacity'):
            self.publish(store)
        self.assertEqual(store.calls, 1)
        self.assertGreater(store.response_bytes, 10)

    def test_transport_call_overcap_stops_without_extra_callback(self):
        spec = copy.deepcopy(self.spec); spec['max_calls'] = 1; store = self.store(spec)
        with self.assertRaisesRegex(s.Stopped, 'call capacity'):
            self.publish(store)
        self.assertEqual(len(self.git.operations), 1)

    def test_store_location_and_manifest_are_independent_trust_anchors(self):
        spec = copy.deepcopy(self.spec); spec['prefix'] += '/elsewhere'
        with self.assertRaisesRegex(ValueError, 'location'):
            self.store(spec)
        with self.assertRaisesRegex(ValueError, 'manifest'):
            self.store(expected_manifest_sha256='0'*64)

    def test_simulated_cas_law_cannot_promote_actual_store_by_repin(self):
        spec = copy.deepcopy(self.spec); spec['domain'] = 'public-scientific-evidence'
        with self.assertRaisesRegex(ValueError, 'atomic CAS primitive'):
            self.store(spec)

    def phase_publication(self, raw, revision=None):
        return {'expected_revision': self.original if revision is None else revision,
                'relative_path': 'phase-ledger.json', 'raw_document': raw,
                'expected_document_pin': pin(raw), 'execution_manifest': self.manifest,
                'expected_execution_manifest_pin': pin(self.manifest), 'attempt_identity': identity('one phase write')}

    def test_phase_genesis_create_only_then_single_irrevocable_append(self):
        cases = cases_fixture(); before = canonical(s.phase_genesis(cases, cases)); store = self.store()
        created = store.publish_phase_genesis(expected_cases=cases, **self.phase_publication(before)).record()
        doc = json.loads(before); row = cases[0]
        doc['events'].append({'ordinal': 0, 'kind': 'consume', 'binding': row,
                             'milliseconds': 40000, 'artifact_bytes': 4*MIB, 'attempt_identity': identity('case0 attempt')})
        after = canonical(doc)
        receipt = store.publish_phase_checkpoint(previous_raw=before, previous_pin=pin(before), expected_cases=cases,
                    **self.phase_publication(after, created['commit'])).record()
        self.assertEqual(receipt['parent'], created['commit'])
        self.assertEqual(self.git.cas_attempts, 2)
        state = s.validate_phase_ledger(doc, cases)
        self.assertEqual(state['reserved_case_artifact_bytes'], 4*MIB)

    def test_phase_genesis_cannot_overwrite_or_rearm_existing_path(self):
        cases = cases_fixture(); raw = canonical(s.phase_genesis(cases, cases)); store = self.store()
        created = store.publish_phase_genesis(expected_cases=cases, **self.phase_publication(raw)).record()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            store.publish_phase_genesis(expected_cases=cases, **self.phase_publication(raw, created['commit']))
        self.assertEqual(self.git.cas_attempts, 1)

    def test_generic_metadata_api_cannot_bypass_phase_append_semantics(self):
        cases = cases_fixture(); raw = canonical(s.phase_genesis(cases, cases))
        with self.assertRaisesRegex(ValueError, 'append-only checkpoint API'):
            self.store().publish(**self.phase_publication(raw))
        self.assertEqual(self.git.operations, [])

    def test_phase_reset_and_multiple_appended_events_rejected_before_remote_call(self):
        cases = cases_fixture(); doc = s.phase_genesis(cases, cases)
        doc['events'] = [{'ordinal': 0, 'kind': 'consume', 'binding': cases[0],
                         'milliseconds': 40000, 'artifact_bytes': 4*MIB, 'attempt_identity': identity('case0 attempt')}]
        before = canonical(doc); store = self.store()
        for after in (canonical(s.phase_genesis(cases, cases)), before):
            with self.subTest(after=pin(after)), self.assertRaisesRegex(ValueError, 'strictly append-only'):
                store.publish_phase_checkpoint(previous_raw=before, previous_pin=pin(before), expected_cases=cases,
                           **self.phase_publication(after))
        self.assertEqual(self.git.operations, [])

    def test_phase_checkpoint_authenticates_original_remote_bytes_before_cas(self):
        cases = cases_fixture(); before = canonical(s.phase_genesis(cases, cases)); store = self.store()
        created = store.publish_phase_genesis(expected_cases=cases, **self.phase_publication(before)).record()
        self.git.files[(created['commit'], self.location['prefix']+'/phase-ledger.json')]['data'] = b'changed remote bytes'
        doc = json.loads(before); doc['events'] = [{'ordinal': 0, 'kind': 'consume', 'binding': cases[0],
            'milliseconds': 40000, 'artifact_bytes': 4*MIB, 'attempt_identity': identity('case0 attempt')}]
        with self.assertRaisesRegex(ValueError, 'publication bytes'):
            store.publish_phase_checkpoint(previous_raw=before, previous_pin=pin(before), expected_cases=cases,
                       **self.phase_publication(canonical(doc), created['commit']))
        self.assertEqual(self.git.cas_attempts, 1)
        self.assertTrue(store.stopped)

    def test_real_active_phase_input_can_be_validated_without_manufacturing_actual_allocation(self):
        cases = cases_fixture(); doc = s.phase_genesis(cases, cases)
        # Schema capability test only. This unit fixture is never published and
        # has no external service/runtime/admission proof or actual allocation.
        doc.update(domain='public-scientific-evidence', status='ACTIVE', scientific_allocation_charged=True)
        state = s.validate_phase_ledger(doc, cases)
        self.assertTrue(state['scientific_allocation_charged'])
        self.assertFalse(state['scientific_execution_authorized'])

    def test_ducktyped_runtime_boolean_cannot_reach_callbacks(self):
        class Forged:
            def record(self):
                return {'domain': 'synthetic-test-fixture', 'pins_authenticated': True,
                        'scientific_execution_authorized': True}
        store = self.store(execution_verifier=lambda _: Forged())
        with self.assertRaisesRegex(ValueError, 'externally verified execution'):
            self.publish(store)
        self.assertEqual(self.git.operations, [])

    def test_real_verification_of_different_freeze_cannot_satisfy_store_raw_binding(self):
        self.runtime_doc['codec_certificate_sha256'] = '8'*64
        self.manifest = canonical(self.runtime_doc)
        # Keep the store's independently retained raw hash from before mutation.
        spec = copy.deepcopy(self.spec)
        old = canonical(runtime_fixture(actual=True)[0])
        self.manifest = old
        genuine_other = runtime.ScientificFreeze(canonical(self.runtime_doc), pin(canonical(self.runtime_doc)),
            expected_inventory=self.runtime_inventory, expected_dependency_edges=self.runtime_edges,
            expected_runtime_identity=self.runtime_identity)
        commit, tree, public = publication_fixture(self.runtime_inventory, self.runtime_data)
        def local(location, path):
            key = next(k for k, row in self.runtime_inventory.items() if (row['location'], row['path']) == (location, path))
            row = self.runtime_inventory[key]
            return {'mode': row['mode'], 'bytes': row['bytes'], 'data': self.runtime_data[key]}
        verified = genuine_other.verify(read_file=local, published_commit=commit, published_tree=tree,
            read_published_file=public, expected_source_contract_sha256='1'*64,
            expected_trial_protocol_sha256='2'*64, expected_codec_certificate_sha256='8'*64,
            runtime_identity=self.runtime_identity)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.publish(self.store(spec, execution_verifier=lambda _: verified))
        self.assertEqual(self.git.operations, [])

    def test_production_schema_path_uses_real_verifier_and_only_in_memory_callbacks(self):
        # This is a schema/callback unit test over fixture byte strings. No actual
        # certificate is saved or published; the callback has no service access.
        self.runtime_doc['domain'] = 'public-scientific-evidence'
        self.manifest = canonical(self.runtime_doc)
        self.law['domain'] = 'public-scientific-evidence'
        self.spec.update(domain='public-scientific-evidence', manifest_sha256=pin(self.manifest)['sha256'],
                         cas_qualification_sha256=pin(canonical(self.law))['sha256'])
        receipt = self.publish(self.store()).record()
        self.assertEqual(receipt['status'], 'READBACK_VERIFIED')
        self.assertFalse(receipt['scientific_execution_authorized'])
        self.assertFalse(receipt['scientific_allocation_charged'])
        self.assertEqual(self.git.cas_attempts, 1)


class CurrentAdmissionTests(unittest.TestCase):
    def setUp(self):
        import scientific_admission
        from test_scientific_admission import make_fixture
        packet = make_fixture().seal()
        self.closure = scientific_admission.validate_scientific_closure(**packet)
        self.args = current_admission_fixture(self.closure, packet['expected_basis'])

    def mutate(self, document, function):
        raw_key = {'proof': 'raw_proof_bytes', 'ack': 'raw_store_acknowledgement',
                   'session': 'raw_session_proof', 'cas': 'raw_cas_qualification'}[document]
        pin_key = {'proof': 'expected_raw_pin', 'ack': 'expected_store_acknowledgement_pin',
                   'session': 'expected_session_proof_pin', 'cas': 'expected_cas_qualification_pin'}[document]
        doc = json.loads(self.args[raw_key]); function(doc)
        raw = canonical(doc); self.args[raw_key] = raw; self.args[pin_key] = pin(raw)
        if document in ('ack', 'session'):
            field = 'store_acknowledgement_sha256' if document == 'ack' else 'session_proof_sha256'
            self.mutate('proof', lambda doc: doc.update({field: pin(raw)['sha256']}))

    def test_real_detached_validator_and_current_proof_fixture_integrate_without_authority(self):
        result = s.validate_current_admission(**self.args).record()
        self.assertTrue(result['pins_authenticated'])
        self.assertEqual(result['status'], 'PENDING')
        self.assertTrue(result['simulation_only'])
        self.assertFalse(result['spectral_access_authorized'])
        self.assertFalse(result['scientific_allocation_charged'])
        self.assertFalse(result['source_rows_read_here'])

    def test_all_three_fixture_roles_bind_ledger_session_context_and_window(self):
        for role in ('calibration', 'validation', 'pilot'):
            with self.subTest(role=role):
                args = current_admission_fixture(self.closure, self.args['expected_basis'], role=role)
                got = s.validate_current_admission(**args).record()
                self.assertEqual(got['role'], role)
                self.assertFalse(got['scientific_execution_authorized'])

    def test_callback_or_boolean_cannot_replace_verified_closure(self):
        self.args['verified_closure'] = {'evidence_closure_verified': True}
        with self.assertRaisesRegex(ValueError, 'Authenticated immutable'):
            s.validate_current_admission(**self.args)

    def test_raw_proof_external_pin_required(self):
        self.args['expected_raw_pin']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'independent bounded pin'):
            s.validate_current_admission(**self.args)

    def test_fixture_relabel_cannot_promote_to_actual_active_permission(self):
        for document in ('ack', 'session', 'cas'):
            self.mutate(document, lambda doc: doc.update(domain='public-scientific-evidence'))
        self.mutate('proof', lambda doc: doc.update(domain='public-scientific-evidence', status='ACTIVE'))
        with self.assertRaisesRegex(ValueError, 'scientific closure'):
            s.validate_current_admission(**self.args)

    def test_current_session_cannot_be_replaced_even_with_coherent_repin(self):
        different = identity('unallocated session')
        for document in ('ack', 'session', 'proof'):
            self.mutate(document, lambda doc: doc.update(session_identity=different))
        self.args['expected_current_session']['session_identity'] = different
        with self.assertRaisesRegex(ValueError, 'absent from irrevocable'):
            s.validate_current_admission(**self.args)

    def test_fresh_trial_identity_cannot_reuse_scientific_case(self):
        scientific_case = self.args['expected_basis']['ordered_case_identities'][0]
        self.mutate('ack', lambda doc: doc.update(trial_case_identity=scientific_case))
        self.mutate('proof', lambda doc: doc.update(trial_case_identity=scientific_case))
        with self.assertRaisesRegex(ValueError, 'pilot trial identity'):
            s.validate_current_admission(**self.args)

    def test_expired_or_not_started_current_session_rejected(self):
        for now in (999, 1201000, 1201001):
            with self.subTest(now=now):
                self.args['expected_current_session']['now_epoch_milliseconds'] = now
                with self.assertRaisesRegex(ValueError, 'Expired'):
                    s.validate_current_admission(**self.args)

    def test_session_capacity_and_bool_counters_rejected_after_coherent_repin(self):
        original = copy.deepcopy(self.args)
        for key, bad in (('requests_used', 501), ('bytes_used', 512*MIB+1), ('session_ordinal', 3), ('requests_used', True)):
            self.args = copy.deepcopy(original)
            self.mutate('session', lambda doc: doc.update({key: bad}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'session capacity'):
                s.validate_current_admission(**self.args)

    def test_session_ordinal_must_match_actual_reserved_ledger_entry(self):
        self.mutate('session', lambda doc: doc.update(session_ordinal=0))
        with self.assertRaisesRegex(ValueError, 'reserved quota'):
            s.validate_current_admission(**self.args)

    def test_session_lifetime_cannot_extend_fixed_1200_seconds(self):
        self.mutate('session', lambda doc: doc.update(deadline_epoch_milliseconds=1201001))
        with self.assertRaisesRegex(ValueError, 'unbounded'):
            s.validate_current_admission(**self.args)

    def test_all_six_original_receipt_pins_are_required(self):
        for field in ('bytes', 'sha256'):
            args = copy.deepcopy(self.args)
            pin_value = args['expected_row_receipt_pins']['epoch1_on']
            pin_value[field] = 33 if field == 'bytes' else 'f'*64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'six independently'):
                s.validate_current_admission(**args)

    def test_codec_or_runtime_metadata_cannot_substitute_current_source_contract(self):
        self.mutate('proof', lambda doc: doc.update(source_contract_sha256=self.args['expected_basis']['source_metadata_sha256']))
        with self.assertRaisesRegex(ValueError, 'runtime/protocol/allocation/ledger'):
            s.validate_current_admission(**self.args)

    def test_receiver_role_window_and_bank_provenance_cannot_be_changed_by_repin(self):
        original = copy.deepcopy(self.args)
        for key in ('context_sha256', 'window_identity', 'receiver_bank_sha256', 'source_inventory_sha256'):
            self.args = copy.deepcopy(original)
            self.mutate('proof', lambda doc: doc.update({key: 'f'*64}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'differs'):
                s.validate_current_admission(**self.args)

    def test_atomic_service_qualification_cannot_be_false_or_fast_forward_only(self):
        self.mutate('cas', lambda doc: doc.update(atomic_expected_revision_cas=False))
        with self.assertRaisesRegex(ValueError, 'atomic CAS service law'):
            s.validate_current_admission(**self.args)

    def test_irrevocable_store_acknowledgement_accepted_and_no_refund_law(self):
        original = copy.deepcopy(self.args)
        for key, value in (('accepted', False), ('irrevocable', False), ('refund_or_retry_allowed', True)):
            self.args = copy.deepcopy(original)
            self.mutate('ack', lambda doc: doc.update({key: value}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'irreversible atomic'):
                s.validate_current_admission(**self.args)

    def test_original_acquisition_ledger_revision_must_be_immutable_and_exact(self):
        for revision in ('main', '0'*40):
            self.mutate('proof', lambda doc: doc.update(acquisition_ledger_revision=revision))
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, 'immutable'):
                s.validate_current_admission(**self.args)

    def test_current_verification_result_has_no_mutable_permission_alias(self):
        record = s.validate_current_admission(**self.args)
        out = record.record(); out['spectral_access_authorized'] = True
        self.assertFalse(record.record()['spectral_access_authorized'])

    def test_current_permission_result_cannot_be_directly_manufactured(self):
        with self.assertRaisesRegex(ValueError, 'maintained verifier'):
            s.VerifiedAdmission(canonical({'spectral_access_authorized': True}))

    def test_session_cannot_extend_past_fixed_9_october_stop_date(self):
        self.mutate('session', lambda doc: doc.update(
            started_epoch_milliseconds=s.STOP_EPOCH_MILLISECONDS-600000,
            deadline_epoch_milliseconds=s.STOP_EPOCH_MILLISECONDS+1))
        self.args['expected_current_session']['now_epoch_milliseconds'] = s.STOP_EPOCH_MILLISECONDS-1
        with self.assertRaisesRegex(ValueError, 'Fixed 2026-10-09 stop date'):
            s.validate_current_admission(**self.args)
        self.mutate('session', lambda doc: doc.update(deadline_epoch_milliseconds=s.STOP_EPOCH_MILLISECONDS))
        record = s.validate_current_admission(**self.args).record()
        self.assertFalse(record['spectral_access_authorized'])


if __name__ == '__main__':
    unittest.main()
