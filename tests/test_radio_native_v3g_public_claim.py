"""Tiny synthetic readback tests: no public claim, scope or workload is made."""
import copy
import hashlib
import unittest
from unittest import mock

import radio_native_v3g_public_claim as claims


def digest(value):
    return hashlib.sha256(claims.canonical(value)).hexdigest()


def repin(claim):
    """Synthetic trusted pins for inert fixtures; this is never publication."""
    raw = claims.canonical(claim['record']) + b'\n'
    claim['registry_pin']['sha256'] = hashlib.sha256(raw).hexdigest()
    claim['registry_pin']['blob'] = hashlib.sha1(
        b'blob ' + str(len(raw)).encode('ascii') + b'\x00' + raw).hexdigest()
    return digest(claim)


def synthetic_claim():
    root = '/synthetic/current-repository'
    scope = '/synthetic/current-repository/engineering-scope-not-created'
    documents = [{'kind': 'plan'}, {'kind': 'freeze'}, {'kind': 'preread'}]
    identity = digest({'namespace': claims.NAMESPACE, 'repository': claims.REPOSITORY,
        'branch': claims.BRANCH, 'marker_path': claims.MARKER})
    witness = {'schema': claims.WITNESS_SCHEMA,
        'activation_identity_sha256': identity,
        'activation_receipt_sha256': 'b' * 64,
        'activation_commit': '1' * 40, 'control_scope': scope,
        'ledger_root': root + '/' + claims.LEDGER_DIRECTORY,
        'ledger_identity': {'device': 1, 'inode': 2, 'mode': 0o700, 'uid': 3, 'gid': 4},
        'record_name': 'spent-' + identity + '.json', 'record_sha256': 'c' * 64,
        'record_identity': {'device': 1, 'inode': 5, 'mode': 0o600, 'nlink': 1,
            'uid': 3, 'gid': 4, 'bytes': 123, 'mtime_ns': 6, 'ctime_ns': 7},
        'durable_before_workload': True, 'one_invocation_spent': True}
    record = {'schema': claims.RECORD_SCHEMA, 'namespace': claims.NAMESPACE,
        'repository': claims.REPOSITORY, 'branch': claims.BRANCH,
        'state': 'SPENT_BEFORE_DISPATCH', 'marker_path': claims.MARKER,
        'activation_commit': '1' * 40, 'activation_tree': '2' * 40,
        'activation_parent': '3' * 40, 'marker_blob': '4' * 40,
        'marker_sha256': '5' * 64, 'repository_root': root, 'control_scope': scope,
        'plan_sha256': digest(documents[0]), 'complete_freeze_sha256': digest(documents[1]),
        'execution_preread_sha256': digest(documents[2]),
        'historical_spent_activations': [list(row) for row in claims.SPENT_ACTIVATIONS],
        'rejected_prospective_identifiers': [list(row) for row in claims.REJECTED_PROSPECTIVE_IDENTIFIERS],
        'local_invocation_spending_sha256': digest(witness),
        'local_ledger_identity': copy.deepcopy(witness['ledger_identity']),
        'local_record_identity': copy.deepcopy(witness['record_identity']),
        'permanent_spent': True, 'spent_before_dispatch': True,
        'one_control_invocation': True, **{name: False for name in claims.DISABLED}}
    claim = {'schema': claims.SCHEMA, 'record': record,
        'registry_pin': {'repository': claims.REPOSITORY, 'branch': claims.BRANCH,
            'path': claims.REGISTRY_PATH, 'commit': '6' * 40, 'tree': '7' * 40,
            'parent': '1' * 40, 'blob': '', 'sha256': '',
            'public_readback_verified': True, 'create_only_ref': claims.CLAIM_REF,
            'ref_create_only_verified': True, 'ref_readback_commit': '6' * 40},
        'public_readback_verified': True}
    return claim, {'expected_sha256': repin(claim), 'plan': documents[0],
        'complete_freeze': documents[1], 'execution_preread': documents[2],
        'execution_scope': scope, 'repository_root': root, 'invocation_spending': witness}


class PublicClaimTests(unittest.TestCase):
    def setUp(self):
        self.claim, self.arguments = synthetic_claim()

    def verify(self, claim=None, **changes):
        arguments = {**self.arguments, **changes}
        return claims.verify_public_claim(self.claim if claim is None else claim, **arguments)

    def rehash(self):
        self.arguments['expected_sha256'] = repin(self.claim)

    def test_valid_read_only_receipt_has_no_execution_authority(self):
        with mock.patch('builtins.open', side_effect=AssertionError('no file reads or writes')):
            receipt = self.verify()
            self.assertEqual(receipt, self.verify())
        self.assertTrue(receipt['public_claim_verified'])
        self.assertTrue(receipt['permanent_spent'])
        self.assertTrue(receipt['spent_before_dispatch'])
        for key in claims.DISABLED:
            self.assertIs(receipt[key], False)

    def test_missing_claim_independent_pin_and_self_pin_fail_closed(self):
        with self.assertRaises(ValueError):
            claims.verify_public_claim(None, **self.arguments)
        with self.assertRaises(ValueError):
            self.verify(expected_sha256=None)
        with self.assertRaises(ValueError):
            self.verify(expected_sha256='0' * 64)
        self.claim['expected_sha256'] = self.arguments['expected_sha256']
        with self.assertRaises(ValueError):
            self.verify(expected_sha256=digest(self.claim))

    def test_all_historical_identity_components_and_d_are_refused(self):
        for old in claims.SPENT_ACTIVATIONS:
            for key, value in zip(('namespace', 'marker_path', 'activation_commit'), old):
                with self.subTest(key=key, value=value):
                    claim, arguments = synthetic_claim()
                    claim['record'][key] = value
                    arguments['expected_sha256'] = repin(claim)
                    with self.assertRaisesRegex(ValueError, 'permanently spent'):
                        claims.verify_public_claim(claim, **arguments)
        for old in claims.REJECTED_PROSPECTIVE_IDENTIFIERS:
            for key, value in zip(('namespace', 'marker_path'), old):
                claim, arguments = synthetic_claim()
                claim['record'][key] = value
                arguments['expected_sha256'] = repin(claim)
                with self.assertRaisesRegex(ValueError, 'Prospective d'):
                    claims.verify_public_claim(claim, **arguments)

    def test_tombstones_cannot_be_edited_even_with_a_new_pin(self):
        for key in ('historical_spent_activations', 'rejected_prospective_identifiers'):
            claim, arguments = synthetic_claim()
            claim['record'][key] = []
            arguments['expected_sha256'] = repin(claim)
            with self.assertRaisesRegex(ValueError, 'tombstones'):
                claims.verify_public_claim(claim, **arguments)

    def test_every_authority_and_truth_flag_requires_exact_bool(self):
        for key in claims.DISABLED:
            for value in (True, 0, None, 'false'):
                claim, arguments = synthetic_claim()
                claim['record'][key] = value
                arguments['expected_sha256'] = repin(claim)
                with self.assertRaises(ValueError):
                    claims.verify_public_claim(claim, **arguments)
        for section, key in ((self.claim, 'public_readback_verified'),
                (self.claim['record'], 'permanent_spent'),
                (self.claim['record'], 'spent_before_dispatch'),
                (self.claim['registry_pin'], 'public_readback_verified'),
                (self.claim['registry_pin'], 'ref_create_only_verified')):
            section[key] = 1
            self.rehash()
            with self.assertRaises(ValueError):
                self.verify()
            section[key] = True

    def test_commit_ref_blob_digest_root_scope_and_input_bindings(self):
        for key, value in (('commit', 'xyz'), ('tree', '0' * 40),
                ('parent', '8' * 39), ('blob', 'f' * 40), ('sha256', '0' * 64),
                ('create_only_ref', 'refs/tags/other'), ('ref_readback_commit', '9' * 40)):
            claim, arguments = synthetic_claim()
            claim['registry_pin'][key] = value
            arguments['expected_sha256'] = digest(claim)
            with self.assertRaises(ValueError):
                claims.verify_public_claim(claim, **arguments)
        for key, value in (('repository_root', '/synthetic/other'),
                ('execution_scope', '/synthetic/other-scope'),
                ('repository_root', '/synthetic/../current-repository'),
                ('plan', {'kind': 'changed'}), ('complete_freeze', {}),
                ('execution_preread', {})):
            with self.assertRaises(ValueError):
                self.verify(**{key: value})

    def test_original_local_witness_cannot_be_lost_or_recreated(self):
        with self.assertRaises(ValueError):
            self.verify(invocation_spending=None)
        witness = copy.deepcopy(self.arguments['invocation_spending'])
        witness['ledger_identity']['inode'] += 1
        with self.assertRaises(ValueError):
            self.verify(invocation_spending=witness)
        witness = copy.deepcopy(self.arguments['invocation_spending'])
        witness['record_identity']['inode'] += 1
        with self.assertRaises(ValueError):
            self.verify(invocation_spending=witness)
        self.claim['record']['local_ledger_identity']['device'] = True
        self.rehash()
        with self.assertRaises(ValueError):
            self.verify()

    def test_returned_receipt_is_detached_from_caller_mutations(self):
        receipt = self.verify()
        snapshot = copy.deepcopy(receipt)
        self.claim['registry_pin']['commit'] = 'f' * 40
        self.claim['record']['local_ledger_identity']['inode'] = 999
        self.claim['record']['historical_spent_activations'].clear()
        self.arguments['invocation_spending']['record_identity']['inode'] = 888
        self.assertEqual(receipt, snapshot)

    def test_mutation_during_verification_is_refused(self):
        original = claims._git
        mutated = False

        def mutate(value, label):
            nonlocal mutated
            if not mutated:
                mutated = True
                self.claim['record']['control_scope'] += '-changed'
            return original(value, label)

        with mock.patch.object(claims, '_git', side_effect=mutate):
            with self.assertRaises(ValueError):
                self.verify()


if __name__ == '__main__':
    unittest.main()
