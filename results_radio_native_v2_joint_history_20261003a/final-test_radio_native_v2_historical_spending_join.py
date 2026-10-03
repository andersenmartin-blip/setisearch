"""Tiny old/new journal integration; no project marker or invocation is created."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import radio_native_v2_historical_storage as storage
import radio_native_v2_prospective_spending as prospective


ROOT = Path(__file__).resolve().parents[1]
OLD_SOURCE = ROOT / 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py'
OLD_PIN = {'bytes': 20163, 'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'}
old_raw = OLD_SOURCE.read_bytes()
if {'bytes': len(old_raw), 'sha256': hashlib.sha256(old_raw).hexdigest()} != OLD_PIN:
    raise ValueError('Historical observer differs from retained public source pin')
historical = types.ModuleType('held_historical_b_spending_for_join')
historical.__file__ = str(OLD_SOURCE)
exec(compile(old_raw, historical.__file__, 'exec'), historical.__dict__)
C_SOURCE = ROOT / 'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py'
C_PIN = {'bytes': 22296, 'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'}
c_raw = C_SOURCE.read_bytes()
if {'bytes': len(c_raw), 'sha256': hashlib.sha256(c_raw).hexdigest()} != C_PIN:
    raise ValueError('Historical c observer differs from retained public source pin')
historical_c = types.ModuleType('held_historical_c_spending_for_join')
historical_c.__file__ = str(C_SOURCE)
exec(compile(c_raw, historical_c.__file__, 'exec'), historical_c.__dict__)


def value_pin(value):
    raw = storage.canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def receipt(module, scope):
    return {'schema': module.RECEIPT_SCHEMA, 'namespace': module.NAMESPACE,
        'activation_commit': '1' * 40, 'activation_tree': '2' * 40,
        'activation_parent': '3' * 40, 'marker_blob': '4' * 40,
        'marker_path': module.MARKER, 'marker_sha256': '5' * 64,
        'plan_sha256': '6' * 64, 'complete_freeze_sha256': '7' * 64,
        'execution_preread_sha256': '8' * 64,
        'runtime_custody_manifest_sha256': '9' * 64, 'control_scope': str(scope),
        'activation_public_readback_verified': True,
        'activation_only_runtime_complete': True, 'one_control_invocation': True,
        **{key: False for key in module.DISABLED}}


def manifest(scope, role):
    rows = []
    for path in sorted([scope, *scope.rglob('*')], key=lambda p: p.relative_to(scope).as_posix()):
        row = {'path': path.relative_to(scope).as_posix(),
            'kind': 'directory' if path.is_dir() else 'file',
            'metadata': storage._metadata(path.lstat())}
        if row['kind'] == 'file':
            raw = path.read_bytes()
            row['raw_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    return {'schema': storage.MANIFEST_SCHEMA, 'role': role, 'scope': str(scope), 'rows': rows}


class HistoricalSpendingJoinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seti-inert-join-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_scope = self.root / 'historical-scope'
        self.old_scope.mkdir(); (self.old_scope / 'retained-engineering.txt').write_bytes(b'tiny old evidence')
        self.new_scope = self.root / 'prospective-scope-absent'
        self.old_ledger = Path(historical.ledger_root_for_repository(str(self.root)))
        self.new_ledger = Path(prospective.ledger_root_for_repository(str(self.root)))
        self.old_ledger.mkdir(mode=0o700); self.new_ledger.mkdir(mode=0o700)
        self.old_receipt = receipt(historical, self.old_scope)
        self.new_receipt = receipt(prospective, self.new_scope)
        self.old_witness = historical.consume_once(self.old_receipt,
            execution_scope=str(self.old_scope), ledger_root=str(self.old_ledger), receipt_validator=lambda _: True)
        self.new_witness = prospective.consume_once(self.new_receipt,
            repository_root=str(self.root), execution_scope=str(self.new_scope),
            ledger_root=str(self.new_ledger), receipt_validator=lambda _: True)

    def observations(self):
        result = []
        for root, role in ((self.old_scope, 'historical_scope'), (self.old_ledger, 'historical_ledger')):
            expected = manifest(root, role)
            result.append(storage.observe_retained_scope(str(root), expected, expected_manifest_pin=value_pin(expected)))
        result.append(prospective.observe_spend_storage(self.new_witness, self.new_receipt,
            repository_root=str(self.root), execution_scope=str(self.new_scope), ledger_root=str(self.new_ledger)))
        return result

    def join(self, observations):
        return storage.join_historical_storage(*observations, expected_observation_pins={
            name: value_pin(value) for name, value in zip(
                ('historical_scope', 'historical_ledger', 'prospective_ledger'), observations)})

    def test_distinct_held_b_and_candidate_d_observers_charge_all_rows_once(self):
        self.assertIsNot(historical, prospective)
        self.assertTrue(historical.NAMESPACE.endswith('20261002b'))
        self.assertTrue(prospective.NAMESPACE.endswith('20261003d'))
        observations = self.observations(); result = self.join(observations)
        self.assertEqual(result['logical_bytes'], sum(value['logical_bytes'] for value in observations))
        self.assertEqual(result['allocated_bytes'], sum(value['allocated_bytes'] for value in observations))
        self.assertEqual(result['entry_count'], sum(value['entry_count'] for value in observations))
        self.assertEqual(len({(r['device'], r['inode']) for r in result['rows']}), result['entry_count'])
        self.assertTrue(result['charged_once']); self.assertTrue(result['read_only'])
        for key in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'):
            self.assertIs(result[key], False)
        self.assertFalse(self.new_scope.exists())

    def test_b_witness_remains_readable_but_d_refuses_it_before_any_ledger_open(self):
        before = historical.observe_spend_storage(self.old_witness, self.old_receipt,
            execution_scope=str(self.old_scope), ledger_root=str(self.old_ledger))
        with mock.patch.object(prospective, '_directory') as opened:
            with self.assertRaises(ValueError):
                prospective.verify_spend_witness(self.old_witness, self.old_receipt,
                    repository_root=str(self.root), execution_scope=str(self.old_scope), ledger_root=str(self.new_ledger))
            opened.assert_not_called()
        after = historical.observe_spend_storage(self.old_witness, self.old_receipt,
            execution_scope=str(self.old_scope), ledger_root=str(self.old_ledger))
        self.assertEqual(before, after)

    def test_historical_record_tamper_refused_by_b_and_retained_scope_observer(self):
        expected = manifest(self.old_ledger, 'historical_ledger')
        path = self.old_ledger / self.old_witness['record_name']
        path.write_bytes(b'altered historical claim')
        with self.assertRaises(ValueError):
            historical.observe_spend_storage(self.old_witness, self.old_receipt,
                execution_scope=str(self.old_scope), ledger_root=str(self.old_ledger))
        with self.assertRaises(ValueError):
            storage.observe_retained_scope(str(self.old_ledger), expected, expected_manifest_pin=value_pin(expected))

    def test_cross_ledger_inode_alias_and_changed_observation_pin_refused(self):
        observations = self.observations()
        original_pins = {name: value_pin(value) for name, value in zip(
            ('historical_scope', 'historical_ledger', 'prospective_ledger'), observations)}
        changed = copy.deepcopy(observations)
        changed[2]['rows'][1]['device'] = changed[1]['rows'][1]['device']
        changed[2]['rows'][1]['inode'] = changed[1]['rows'][1]['inode']
        with self.assertRaises(ValueError): self.join(changed)
        changed = copy.deepcopy(observations); changed[0]['manifest_sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            storage.join_historical_storage(*changed, expected_observation_pins=original_pins)

    def test_original_and_prospective_replays_do_not_create_a_second_record(self):
        with self.assertRaises(ValueError):
            historical.consume_once(self.old_receipt, execution_scope=str(self.old_scope),
                ledger_root=str(self.old_ledger), receipt_validator=lambda _: True)
        with self.assertRaises(ValueError):
            prospective.consume_once(self.new_receipt, repository_root=str(self.root),
                execution_scope=str(self.new_scope), ledger_root=str(self.new_ledger), receipt_validator=lambda _: True)
        self.assertEqual(len(list(self.old_ledger.iterdir())), 1)
        self.assertEqual(len(list(self.new_ledger.iterdir())), 1)
        self.assertFalse(self.new_scope.exists())


class TwoHistoricalSpendingJoinTests(unittest.TestCase):
    """Actual frozen b/c and current d contracts, only tiny temporary journals."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='seti-inert-joint-join-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.values = {}; self.retained_manifests = {}; self.scopes = {}
        self.receipts = {}; self.witnesses = {}; self.ledgers = {}
        for identity, module in (('b', historical), ('c', historical_c), ('d', prospective)):
            scope = self.root / ('synthetic-' + identity + '-scope')
            self.scopes[identity] = scope
            if identity != 'd':
                scope.mkdir()
                (scope / 'retained-engineering.txt').write_bytes(b'tiny retained ' + identity.encode('ascii'))
            ledger = Path(module.ledger_root_for_repository(str(self.root)))
            ledger.mkdir(mode=0o700)
            self.ledgers[identity] = ledger
            current_receipt = receipt(module, scope)
            self.receipts[identity] = current_receipt
            kwargs = {'execution_scope': str(scope), 'ledger_root': str(ledger),
                'receipt_validator': lambda _: True}
            if identity != 'b':
                kwargs['repository_root'] = str(self.root)
            witness = module.consume_once(current_receipt, **kwargs)
            self.witnesses[identity] = witness
            if identity != 'd':
                for root, role in ((scope, 'historical_scope'), (ledger, 'historical_ledger')):
                    label = 'historical_' + identity + ('_scope' if role == 'historical_scope' else '_ledger')
                    expected = manifest(root, role)
                    self.retained_manifests[label] = expected
                    self.values[label] = storage.observe_retained_scope(root, expected,
                        expected_manifest_pin=value_pin(expected))
            else:
                self.values['prospective_ledger'] = module.observe_spend_storage(witness,
                    current_receipt, repository_root=str(self.root), execution_scope=str(scope),
                    ledger_root=str(ledger))

    def join(self, values=None):
        values = self.values if values is None else values
        return storage.join_retained_storage_components(values,
            expected_observation_pins={label: value_pin(value) for label, value in values.items()},
            expected_component_roles=storage.JOINT_HISTORY_COMPONENT_ROLES)

    def test_exact_frozen_b_c_and_current_d_contracts_join_without_reusing_any_identity(self):
        self.assertTrue(historical.NAMESPACE.endswith('20261002b'))
        self.assertTrue(historical_c.NAMESPACE.endswith('20261002c'))
        self.assertTrue(prospective.NAMESPACE.endswith('20261003d'))
        self.assertEqual(len(set(map(str, self.ledgers.values()))), 3)
        before = {identity: list(ledger.iterdir()) for identity, ledger in self.ledgers.items()}
        with mock.patch.object(storage.os, 'open', side_effect=AssertionError('join is pure')):
            joined = self.join()
        self.assertEqual(joined['entry_count'], 10)
        self.assertEqual(joined['logical_bytes'], sum(value['logical_bytes'] for value in self.values.values()))
        self.assertEqual(joined['allocated_bytes'], sum(value['allocated_bytes'] for value in self.values.values()))
        self.assertEqual({component['role'] for component in joined['components']},
            set(storage.JOINT_HISTORY_COMPONENT_ROLES))
        self.assertEqual(len({(row['device'], row['inode']) for row in joined['rows']}), 10)
        self.assertEqual(before, {identity: list(ledger.iterdir()) for identity, ledger in self.ledgers.items()})
        self.assertFalse(self.scopes['d'].exists())
        for field in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'):
            self.assertIs(joined[field], False)

    def test_historical_c_record_drift_is_refused_by_frozen_contract_and_retained_manifest(self):
        witness = self.witnesses['c']; ledger = self.ledgers['c']
        (ledger / witness['record_name']).write_bytes(b'tampered tiny historical c record')
        with self.assertRaises(ValueError):
            historical_c.observe_spend_storage(witness, self.receipts['c'],
                repository_root=str(self.root), execution_scope=str(self.scopes['c']),
                ledger_root=str(ledger))
        expected = self.retained_manifests['historical_c_ledger']
        with self.assertRaises(ValueError):
            storage.observe_retained_scope(ledger, expected, expected_manifest_pin=value_pin(expected))

    def test_omitting_c_scope_or_spent_journal_fails_even_with_valid_remaining_spend_witness(self):
        for omitted in ('historical_c_scope', 'historical_c_ledger'):
            with self.subTest(omitted=omitted):
                values = {label: value for label, value in self.values.items() if label != omitted}
                with self.assertRaisesRegex(ValueError, 'complete independently required'):
                    self.join(values)
        prospective.verify_spend_witness(self.witnesses['d'], self.receipts['d'],
            repository_root=str(self.root), execution_scope=str(self.scopes['d']),
            ledger_root=str(self.ledgers['d']))
        self.assertFalse(self.scopes['d'].exists())


if __name__ == '__main__':
    unittest.main()
