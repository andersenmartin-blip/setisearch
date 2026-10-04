"""Synthetic injected tests only: no credentials, services, spectra or files."""
import copy
import hashlib
import unittest

import hosted_cas as h


def object_id(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode()
                        + b'\0' + raw).hexdigest()


class Fixture:
    def __init__(self):
        self.expected = '1' * 40
        self.tree = '2' * 40
        raw = ('tree ' + self.tree + '\nparent ' + self.expected +
               '\nauthor Synthetic <fixture@example.invalid> 0 +0000\n'
               'committer Synthetic <fixture@example.invalid> 0 +0000\n\n'
               'synthetic preparation only\n').encode()
        data = b'{"engineering_only":true,"scientific_execution_authorized":false}\n'
        self.witness = {'repository': h.REPOSITORY, 'commit': object_id('commit', raw),
                        'tree': self.tree, 'parents': [self.expected], 'path': h.PATH,
                        'mode': '100644', 'blob': object_id('blob', data),
                        'data': data, 'raw_commit': raw}
        self.params = {'repository': h.REPOSITORY, 'branch': h.BRANCH,
                       'expected_revision': self.expected, 'candidate': self.witness['commit'],
                       'qualification_sha256': 'a' * 64}
        self.current = self.expected
        self.requests = []
        self.reads = 0
        self.ack = {'data': {'updateRefs': {'clientMutationId': h.NAMESPACE}}}

    def head(self, request):
        return {**request, 'commit': self.current}

    def immutable(self, request):
        self.reads += 1
        return copy.deepcopy(self.witness)

    def transport(self, request):
        self.requests.append(copy.deepcopy(request))
        self.current = self.witness['commit']
        return copy.deepcopy(self.ack)

    def adapter(self, **changes):
        arguments = {'transport': self.transport, 'read_ref': self.head,
                     'read_candidate': self.immutable, 'candidate_witness': self.witness,
                     'witness_pin': h.witness_sha256(self.witness),
                     'qualification_sha256': self.params['qualification_sha256']}
        arguments.update(changes)
        return h.HostedCASPreparation(**arguments)


class HostedCASTests(unittest.TestCase):
    def assert_spent(self, adapter, fixture):
        calls = adapter.calls
        with self.assertRaises(RuntimeError):
            adapter(h.OPERATION, fixture.params)
        self.assertEqual(adapter.calls, calls)

    def test_exact_mapping_and_immutable_reads(self):
        f = Fixture(); adapter = f.adapter()
        result = adapter(h.OPERATION, f.params)
        self.assertEqual(f.requests, [{'query': h.QUERY, 'variables': {'input': {
            'repositoryId': 'R_kgDOT558WQ', 'clientMutationId': h.NAMESPACE,
            'refUpdates': [{'name': 'refs/heads/m43-support-qualification',
                            'beforeOid': f.expected, 'afterOid': f.witness['commit'],
                            'force': False}]}}}])
        self.assertEqual(f.reads, 2); self.assertEqual(adapter.calls, 5)
        self.assertTrue(result['accepted']); self.assertTrue(result['preparation_only'])
        self.assertTrue(result['engineering_only'])
        for key in h.FALSE_AUTHORITY:
            self.assertIs(result[key], False)
        self.assert_spent(adapter, f)

    def test_precheck_concurrent_head_change(self):
        f = Fixture(); f.current = '3' * 40; adapter = f.adapter()
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(f.requests, []); self.assertEqual(f.reads, 0)
        self.assertFalse(adapter.result['mutation_may_have_landed'])
        self.assert_spent(adapter, f)

    def test_race_returns_server_error_without_retry(self):
        f = Fixture()
        def conflict(request):
            f.requests.append(copy.deepcopy(request)); f.current = '3' * 40
            return {'data': {'updateRefs': None}, 'errors': [{'message': 'Expected old OID differs'}]}
        adapter = f.adapter(transport=conflict)
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(len(f.requests), 1)
        self.assert_spent(adapter, f)

    def test_wrong_candidate_parents(self):
        for parents in ([], ['3' * 40], [Fixture().expected, '3' * 40]):
            with self.subTest(parents=parents):
                f = Fixture(); f.witness['parents'] = parents; adapter = f.adapter()
                with self.assertRaises(ValueError):
                    adapter(h.OPERATION, f.params)
                self.assertEqual(adapter.calls, 0); self.assert_spent(adapter, f)

    def test_missing_invalid_and_erroneous_ack(self):
        for ack in (None, {}, {'data': None}, {'data': {'updateRefs': {}}},
                    {'data': {'updateRefs': {'clientMutationId': 'other'}}},
                    {'data': {'updateRefs': {'clientMutationId': h.NAMESPACE}}, 'errors': []},
                    {'data': {'updateRefs': {'clientMutationId': h.NAMESPACE, 'qualified': True}}}):
            with self.subTest(ack=ack):
                f = Fixture(); f.ack = ack; adapter = f.adapter()
                with self.assertRaises(ValueError):
                    adapter(h.OPERATION, f.params)
                self.assertEqual(len(f.requests), 1); self.assert_spent(adapter, f)

    def test_unknown_timeout_spends_without_retry(self):
        f = Fixture()
        def timeout(request):
            f.requests.append(copy.deepcopy(request)); raise TimeoutError()
        adapter = f.adapter(transport=timeout)
        with self.assertRaises(TimeoutError):
            adapter(h.OPERATION, f.params)
        self.assertTrue(adapter.result['mutation_may_have_landed'])
        self.assertEqual(len(f.requests), 1); self.assert_spent(adapter, f)

    def test_posthead_mismatch(self):
        f = Fixture()
        def changed(request):
            result = f.transport(request); f.current = '3' * 40; return result
        adapter = f.adapter(transport=changed)
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(f.reads, 2); self.assert_spent(adapter, f)

    def test_source_witness_mutation(self):
        f = Fixture(); adapter = f.adapter(); f.witness['tree'] = '3' * 40
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(adapter.calls, 0); self.assert_spent(adapter, f)

    def test_source_params_mutation_during_call(self):
        f = Fixture()
        def changed(request):
            f.params['candidate'] = '3' * 40; return f.head(request)
        adapter = f.adapter(read_ref=changed)
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(f.requests, []); self.assert_spent(adapter, f)

    def test_caller_bytes_to_dict_substitution_during_read(self):
        for field in ('data', 'raw_commit'):
            with self.subTest(field=field):
                f = Fixture(); independent = copy.deepcopy(f.witness)
                def changed(request):
                    f.witness[field] = {'raw_bytes_hex': independent[field].hex()}
                    return f.head(request)
                def immutable(request):
                    f.reads += 1
                    return copy.deepcopy(independent)
                adapter = f.adapter(read_ref=changed, read_candidate=immutable)
                with self.assertRaises(ValueError):
                    adapter(h.OPERATION, f.params)
                self.assertEqual(adapter.calls, 1)
                self.assertEqual(f.reads, 0); self.assertEqual(f.requests, [])
                self.assert_spent(adapter, f)

    def test_fixed_request_mutation(self):
        f = Fixture()
        def changed(request):
            request['variables']['input']['refUpdates'][0]['force'] = True
            return f.transport(request)
        adapter = f.adapter(transport=changed)
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assert_spent(adapter, f)

    def test_forbidden_repository_ref_force_and_method(self):
        for changes, method in (({'repository': 'other/repo'}, h.OPERATION),
                                ({'branch': 'main'}, h.OPERATION),
                                ({'force': True}, h.OPERATION),
                                ({}, 'update_ref')):
            with self.subTest(changes=changes, method=method):
                f = Fixture(); f.params.update(changes); adapter = f.adapter()
                with self.assertRaises(ValueError):
                    adapter(method, f.params)
                self.assertEqual(adapter.calls, 0); self.assert_spent(adapter, f)

    def test_qualification_pin_syntax_and_binding(self):
        for pin in (None, '', 'A' * 64, 'a' * 63):
            with self.subTest(pin=pin):
                f = Fixture()
                with self.assertRaises(ValueError):
                    f.adapter(qualification_sha256=pin)
        f = Fixture(); adapter = f.adapter(); f.params['qualification_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(adapter.calls, 0); self.assert_spent(adapter, f)

    def test_false_authority_cannot_be_inserted(self):
        f = Fixture(); f.witness['scientific_execution_authorized'] = True; adapter = f.adapter()
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(adapter.calls, 0)
        f = Fixture(); result = f.adapter()(h.OPERATION, f.params)
        production_fields = {'repository', 'branch', 'expected_revision', 'commit', 'atomic', 'accepted'}
        self.assertNotEqual(set(result), production_fields)

    def test_intrinsic_commit_and_blob_tampering(self):
        for field in ('raw_commit', 'data'):
            with self.subTest(field=field):
                f = Fixture(); f.witness[field] += b'x'; adapter = f.adapter()
                with self.assertRaises(ValueError):
                    adapter(h.OPERATION, f.params)
                self.assertEqual(adapter.calls, 0)

    def test_postmutation_immutable_readback_changed(self):
        f = Fixture()
        def changed(request):
            got = f.immutable(request)
            if f.reads == 2:
                got['mode'] = '100755'
            return got
        adapter = f.adapter(read_candidate=changed)
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(f.reads, 2); self.assert_spent(adapter, f)

    def test_bad_witness_pin_and_identity_noop(self):
        f = Fixture()
        with self.assertRaises(ValueError):
            f.adapter(witness_pin='f' * 64)
        adapter = f.adapter(); f.params['candidate'] = f.expected
        with self.assertRaises(ValueError):
            adapter(h.OPERATION, f.params)
        self.assertEqual(adapter.calls, 0); self.assert_spent(adapter, f)


if __name__ == '__main__':
    unittest.main()
