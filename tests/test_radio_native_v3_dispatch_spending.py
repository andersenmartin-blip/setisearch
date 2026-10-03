"""Tiny temporary metadata tests; no control, source or telescope work runs.

Public readbacks and their independent admission are synthetic test fixtures.
They do not represent publication or qualify any real public publisher API.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import radio_native_v3_public_claim as claims
import radio_native_v3_prospective_spending as spending
from test_radio_native_v3_public_claim import repin, synthetic_claim


def digest(value):
    return hashlib.sha256(spending.canonical(value)).hexdigest()


class DispatchSpendingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = self.root / 'scope-not-created'
        self.ledger = Path(spending.ledger_root_for_repository(self.root))
        self.ledger.mkdir(mode=0o700)
        claim, admission = synthetic_claim()
        self.receipt = {'schema': spending.RECEIPT_SCHEMA,
            'namespace': spending.NAMESPACE, 'activation_commit': '1' * 40,
            'activation_tree': '2' * 40, 'activation_parent': '3' * 40,
            'activation_public_readback_verified': True,
            'marker_path': spending.MARKER, 'marker_blob': '4' * 40,
            'marker_sha256': '5' * 64, 'plan_sha256': digest(admission['plan']),
            'complete_freeze_sha256': digest(admission['complete_freeze']),
            'execution_preread_sha256': digest(admission['execution_preread']),
            'one_control_invocation': True, 'control_scope': str(self.scope),
            'runtime_custody_manifest_sha256': '9' * 64,
            'activation_only_runtime_complete': True,
            **{key: False for key in spending.DISABLED}}
        self.paths = {'execution_scope': str(self.scope),
            'ledger_root': str(self.ledger), 'repository_root': str(self.root)}
        self.witness = spending.consume_once(self.receipt, **self.paths,
            receipt_validator=lambda value: True)
        record = claim['record']
        record['repository_root'] = str(self.root)
        record['control_scope'] = str(self.scope)
        record['local_invocation_spending_sha256'] = digest(self.witness)
        record['local_ledger_identity'] = copy.deepcopy(self.witness['ledger_identity'])
        record['local_record_identity'] = copy.deepcopy(self.witness['record_identity'])
        self.independent_claim_sha256 = repin(claim)
        self.admission = {**admission, 'expected_sha256': self.independent_claim_sha256,
            'execution_scope': str(self.scope), 'repository_root': str(self.root)}
        self.bundle = {'schema': spending.SPENDING_BUNDLE_SCHEMA,
            'local_witness': copy.deepcopy(self.witness), 'public_claim': claim,
            'public_claim_sha256': self.independent_claim_sha256,
            'dispatch_witness': None}
        self.claim_path = self.ledger / self.witness['record_name']
        self.dispatch_path = self.ledger / ('dispatch-' + self.witness['record_name'][len('spent-'):])

    def admit_public_claim(self, bundle):
        receipt = claims.verify_public_claim(bundle['public_claim'],
            **{**self.admission, 'invocation_spending': bundle['local_witness']})
        return receipt['public_claim_verified'] is True

    def dispatch(self, bundle=None, **changes):
        arguments = {**self.paths, 'public_claim_validator': self.admit_public_claim,
            **changes}
        return spending.consume_dispatch_once(self.bundle if bundle is None else bundle,
            self.receipt, **arguments)

    def verify_dispatch(self, bundle):
        return spending.verify_dispatch_witness(bundle, self.receipt, **self.paths)

    def test_preclaim_public_admission_dispatch_and_sorted_three_row_observation(self):
        self.assertTrue(spending.verify_spend_witness(self.witness,
            self.receipt, **self.paths))
        self.assertTrue(self.admit_public_claim(self.bundle))
        self.assertFalse(self.scope.exists())
        dispatched = self.dispatch()
        self.assertTrue(self.verify_dispatch(dispatched))
        witness = dispatched['dispatch_witness']
        self.assertIs(witness['durable_before_dispatch'], True)
        self.assertIs(witness['one_dispatch_spent'], True)
        raw = self.dispatch_path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), witness['dispatch_sha256'])
        before = {path: path.stat() for path in (self.ledger, self.claim_path, self.dispatch_path)}
        observed = spending.observe_spend_storage(dispatched, self.receipt, **self.paths)
        rows = observed['rows']
        self.assertEqual([row['path'] for row in rows],
            sorted(map(str, (self.ledger, self.claim_path, self.dispatch_path))))
        self.assertEqual(observed['entry_count'], 3)
        self.assertEqual(observed['logical_bytes'], sum(row['bytes'] for row in rows))
        self.assertEqual(observed['allocated_bytes'], sum(row['allocated_bytes'] for row in rows))
        self.assertEqual(observed['invocation_spending_sha256'], digest(dispatched))
        self.assertIs(observed['witness_bindings_verified'], True)
        self.assertIs(observed['current_observation_stable'], True)
        self.assertEqual(before, {path: path.stat() for path in before})
        self.assertFalse(self.scope.exists())

    def test_dispatch_once_rejects_predispatch_and_returned_bundle_replays(self):
        dispatched = self.dispatch()
        for bundle in (self.bundle, dispatched):
            with self.assertRaises(ValueError):
                self.dispatch(bundle)
        self.assertTrue(self.verify_dispatch(dispatched))
        self.assertEqual(len(list(self.ledger.iterdir())), 2)
        self.assertFalse(self.scope.exists())

    def test_four_concurrent_metadata_attempts_accept_exactly_one(self):
        def attempt(_):
            try:
                return self.dispatch()
            except ValueError:
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            outcomes = list(executor.map(attempt, range(4)))
        accepted = [value for value in outcomes if value is not None]
        self.assertEqual(len(accepted), 1)
        self.assertTrue(self.verify_dispatch(accepted[0]))
        self.assertFalse(self.scope.exists())

    def test_missing_public_claim_is_rejected_before_dispatch_marker(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['public_claim'] = None
        with self.assertRaises(ValueError):
            self.dispatch(bundle)
        self.assertFalse(self.dispatch_path.exists())

    def test_missing_private_original_claim_is_never_recreated(self):
        self.claim_path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.dispatch()
        self.assertFalse(self.claim_path.exists())
        self.assertFalse(self.dispatch_path.exists())
        self.assertFalse(self.scope.exists())

    def test_lost_private_original_ledger_is_never_recreated(self):
        shutil.rmtree(self.ledger)
        with self.assertRaises((ValueError, OSError)):
            self.dispatch()
        self.assertFalse(self.ledger.exists())
        self.assertFalse(self.scope.exists())

    def test_copied_private_journal_cannot_replace_original_identity(self):
        original = self.root / 'original-ledger-held-outside-claim-path'
        self.ledger.rename(original)
        shutil.copytree(original, self.ledger)
        self.assertEqual(self.claim_path.read_bytes(),
            (original / self.witness['record_name']).read_bytes())
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(self.dispatch_path.exists())

    def test_copied_original_claim_file_cannot_replace_original_inode(self):
        original = self.root / 'original-claim-held-outside-ledger'
        self.claim_path.rename(original)
        shutil.copy2(original, self.claim_path)
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(self.dispatch_path.exists())

    def test_empty_partial_dispatch_marker_remains_spent_after_failed_write(self):
        with mock.patch.object(spending.os, 'write', return_value=0):
            with self.assertRaisesRegex(ValueError, 'Incomplete durable dispatch write'):
                self.dispatch()
        self.assertTrue(self.dispatch_path.exists())
        self.assertEqual(self.dispatch_path.read_bytes(), b'')
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertEqual(self.dispatch_path.read_bytes(), b'')
        self.assertFalse(self.scope.exists())

    def test_partial_dispatch_marker_remains_spent_after_failed_fsync(self):
        with mock.patch.object(spending.os, 'fsync', side_effect=OSError('synthetic fsync failure')):
            with self.assertRaises(OSError):
                self.dispatch()
        self.assertTrue(self.dispatch_path.exists())
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(self.scope.exists())

    def test_admission_callback_mutation_is_refused_before_dispatch(self):
        def mutate(value):
            value['public_claim']['record']['control_scope'] += '-changed'
            return True

        with self.assertRaisesRegex(ValueError, 'changed during admission'):
            self.dispatch(public_claim_validator=mutate)
        self.assertFalse(self.dispatch_path.exists())
        self.assertIs(self.bundle['dispatch_witness'], None)
        self.assertTrue(self.admit_public_claim(self.bundle))

    def test_false_or_non_bool_admission_callback_is_refused(self):
        for answer in (False, None, 0, 1, 'true'):
            with self.subTest(answer=answer):
                with self.assertRaises(ValueError):
                    self.dispatch(public_claim_validator=lambda value: answer)
                self.assertFalse(self.dispatch_path.exists())
        with self.assertRaises(ValueError):
            self.dispatch(public_claim_validator=None)

    def test_original_bundle_mutation_cannot_edit_returned_dispatch_witness(self):
        dispatched = self.dispatch()
        snapshot = copy.deepcopy(dispatched)
        self.assertIs(self.bundle['dispatch_witness'], None)
        self.bundle['public_claim']['registry_pin']['commit'] = 'f' * 40
        self.bundle['local_witness']['record_identity']['inode'] += 1
        self.assertEqual(dispatched, snapshot)
        self.assertTrue(self.verify_dispatch(dispatched))

    def test_extra_ledger_file_rejects_postdispatch_observation(self):
        dispatched = self.dispatch()
        (self.ledger / 'unexpected').write_bytes(b'inert')
        with self.assertRaises(ValueError):
            spending.observe_spend_storage(dispatched, self.receipt, **self.paths)
        self.assertFalse(self.scope.exists())


if __name__ == '__main__':
    unittest.main()
