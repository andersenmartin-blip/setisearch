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

    def test_distinct_held_b_and_candidate_c_observers_charge_all_rows_once(self):
        self.assertIsNot(historical, prospective)
        self.assertTrue(historical.NAMESPACE.endswith('20261002b'))
        self.assertTrue(prospective.NAMESPACE.endswith('20261002c'))
        observations = self.observations(); result = self.join(observations)
        self.assertEqual(result['logical_bytes'], sum(value['logical_bytes'] for value in observations))
        self.assertEqual(result['allocated_bytes'], sum(value['allocated_bytes'] for value in observations))
        self.assertEqual(result['entry_count'], sum(value['entry_count'] for value in observations))
        self.assertEqual(len({(r['device'], r['inode']) for r in result['rows']}), result['entry_count'])
        self.assertTrue(result['charged_once']); self.assertTrue(result['read_only'])
        for key in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'):
            self.assertIs(result[key], False)
        self.assertFalse(self.new_scope.exists())

    def test_b_witness_remains_readable_but_c_refuses_it_before_any_ledger_open(self):
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


if __name__ == '__main__':
    unittest.main()
