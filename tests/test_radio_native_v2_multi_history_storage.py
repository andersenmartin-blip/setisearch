"""Inert tests for multi-generation accounting; no project ledger is touched."""
import copy
import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import radio_native_v2_historical_storage as storage
import radio_native_v2_multi_history_storage as multi


def pin(value):
    raw = storage.canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def metadata(path):
    info = path.lstat()
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'allocated_bytes': info.st_blocks * 512,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def manifest(root, role):
    rows = []
    for path in sorted([root, *root.rglob('*')], key=lambda value: value.relative_to(root).as_posix()):
        row = {'path': path.relative_to(root).as_posix(),
            'kind': 'directory' if path.is_dir() else 'file', 'metadata': metadata(path)}
        if row['kind'] == 'file':
            raw = path.read_bytes()
            row['raw_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    return {'schema': storage.MANIFEST_SCHEMA, 'role': role, 'scope': str(root), 'rows': rows}


def observation(root, role):
    value = manifest(root, role)
    return storage.observe_retained_scope(root, value, expected_manifest_pin=pin(value))


class MultiHistoryStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='seti-multi-history-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.histories = []
        for generation in ('b', 'c'):
            scope = self.root / (generation + '-scope')
            ledger = self.root / (generation + '-ledger')
            scope.mkdir(); ledger.mkdir()
            (scope / 'evidence').mkdir()
            (scope / 'evidence' / 'terminal.json').write_bytes(generation.encode())
            (ledger / 'spent.json').write_bytes((generation + '-spent').encode())
            self.histories.append({'generation': generation,
                'historical_scope': observation(scope, 'historical_scope'),
                'historical_ledger': observation(ledger, 'historical_ledger')})
        ledger = self.root / 'd-ledger'; ledger.mkdir()
        spent = ledger / 'spent.json'; spent.write_bytes(b'd-spent')
        rows = [{'path': str(ledger), 'kind': 'directory', **metadata(ledger)},
            {'path': str(spent), 'kind': 'file', **metadata(spent)}]
        self.prospective = {'schema': storage.LEDGER_STORAGE_SCHEMA,
            'ledger_root': str(ledger), 'control_scope': str(self.root / 'd-scope-absent'),
            'activation_receipt_sha256': '1' * 64, 'invocation_spending_sha256': '2' * 64,
            'rows': rows, 'logical_bytes': sum(row['bytes'] for row in rows),
            'allocated_bytes': sum(row['allocated_bytes'] for row in rows),
            'entry_count': len(rows), 'witness_bindings_verified': True,
            'ledger_inventory_exact': True, 'current_observation_stable': True}

    def pins(self, histories=None, prospective=None):
        histories = self.histories if histories is None else histories
        prospective = self.prospective if prospective is None else prospective
        values = {'prospective_ledger': pin(prospective)}
        for item in histories:
            values[item['generation'] + ':scope'] = pin(item['historical_scope'])
            values[item['generation'] + ':ledger'] = pin(item['historical_ledger'])
        return values

    def join(self, histories=None, prospective=None, pins=None):
        histories = self.histories if histories is None else histories
        prospective = self.prospective if prospective is None else prospective
        return multi.join_retained_generations(histories, prospective,
            expected_observation_pins=self.pins(histories, prospective) if pins is None else pins)

    def test_two_closed_generations_and_distinct_prospective_are_charged_once(self):
        result = self.join()
        inventories = [item[key] for item in self.histories
            for key in ('historical_scope', 'historical_ledger')] + [self.prospective]
        self.assertEqual(result['historical_generations'], ['b', 'c'])
        self.assertEqual(result['logical_bytes'], sum(value['logical_bytes'] for value in inventories))
        self.assertEqual(result['allocated_bytes'], sum(value['allocated_bytes'] for value in inventories))
        self.assertEqual(result['entry_count'], sum(value['entry_count'] for value in inventories))
        self.assertEqual(len(result['components']), 5)
        self.assertEqual(len({(row['device'], row['inode']) for row in result['rows']}), result['entry_count'])
        for field in ('execution_authorized', 'whole_control_qualified',
                'lifetime_accounting_proved', 'missing_history_reconstruction_authorized'):
            self.assertIs(result[field], False)

    def test_one_history_is_not_silently_promoted_to_multi_history(self):
        with self.assertRaisesRegex(ValueError, 'Two to sixteen'):
            self.join(histories=self.histories[:1])

    def test_unsorted_duplicate_and_malformed_generations_are_refused(self):
        for changed in ([self.histories[1], self.histories[0]],
                [self.histories[0], self.histories[0]],
                [{**self.histories[0], 'generation': '../b'}, self.histories[1]]):
            with self.subTest(changed=changed[0]['generation']):
                with self.assertRaises(ValueError): self.join(histories=changed)

    def test_missing_extra_and_changed_independent_pins_are_refused(self):
        original = self.pins()
        variants = [dict(original), dict(original), copy.deepcopy(original)]
        variants[0].pop('c:ledger')
        variants[1]['unchecked'] = pin({})
        variants[2]['b:scope']['sha256'] = '0' * 64
        for changed in variants:
            with self.assertRaises(ValueError): self.join(pins=changed)

    def test_changed_observation_after_pin_is_refused(self):
        pins = self.pins(); changed = copy.deepcopy(self.histories)
        changed[1]['historical_scope']['logical_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'independently retained'):
            self.join(histories=changed, pins=pins)

    def test_false_historical_authentication_flags_are_refused(self):
        changed = copy.deepcopy(self.histories)
        changed[0]['historical_scope']['read_only'] = False
        with self.assertRaisesRegex(ValueError, 'read-only historical'):
            self.join(histories=changed)

    def test_cross_generation_inode_alias_is_refused(self):
        changed = copy.deepcopy(self.histories)
        source = changed[0]['historical_scope']['rows'][0]
        target = changed[1]['historical_scope']['rows'][0]
        target['device'], target['inode'] = source['device'], source['inode']
        with self.assertRaisesRegex(ValueError, 'inode alias'):
            self.join(histories=changed)

    def test_cross_generation_root_overlap_is_refused(self):
        changed = copy.deepcopy(self.histories)
        root = changed[0]['historical_scope']['scope']
        changed[1]['historical_scope']['scope'] = root
        for row in changed[1]['historical_scope']['rows']:
            suffix = Path(row['path']).relative_to(self.root / 'c-scope')
            row['path'] = str(Path(root) / suffix)
        with self.assertRaises(ValueError): self.join(histories=changed)

    def test_prospective_control_overlap_is_refused(self):
        changed = copy.deepcopy(self.prospective)
        changed['control_scope'] = self.histories[1]['historical_scope']['scope'] + '/child'
        with self.assertRaisesRegex(ValueError, 'control scope overlaps'):
            self.join(prospective=changed)

    def test_prospective_false_witness_and_noncanonical_sha_are_refused(self):
        for field, value in (('witness_bindings_verified', False),
                ('activation_receipt_sha256', 'A' * 64)):
            changed = copy.deepcopy(self.prospective); changed[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.join(prospective=changed)

    def test_prospective_ledger_requires_exact_root_and_direct_file(self):
        changed = copy.deepcopy(self.prospective)
        changed['rows'][1]['path'] = changed['ledger_root'] + '/nested/spent.json'
        with self.assertRaises(ValueError): self.join(prospective=changed)

    def test_whole_bound_is_enforced_after_all_generations(self):
        with mock.patch.object(multi, 'MAX_JOIN_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'bound exceeded'):
                self.join()


if __name__ == '__main__':
    unittest.main()
