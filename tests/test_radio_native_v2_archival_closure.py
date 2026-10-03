"""Tests for public closure verification; original private state is never opened."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import radio_native_v2_archival_closure as closure


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'results_radio_native_v2_control_activation_20261002c'
PATHS = {'spend_record': 'public-c-spend-record-copy.json',
    'launch_start': 'single-launch-start.json',
    'launch_terminal': 'single-launch-terminal.json',
    'terminal_scope_inventory': 'terminal-scope-inventory.json',
    'source_preservation': 'post-terminal-source-preservation.json'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


class ArchivalClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {label: (DIRECTORY / path).read_bytes() for label, path in PATHS.items()}
        cls.pins = {label: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for label, raw in cls.files.items()}

    def verify(self, files=None, pins=None):
        return closure.verify_archival_closure(self.files if files is None else files,
            expected_pins=self.pins if pins is None else pins)

    def changed(self, label, field, value):
        files = dict(self.files); record = json.loads(files[label]); record[field] = value
        files[label] = canonical(record)
        pins = dict(self.pins); pins[label] = {'bytes': len(files[label]),
            'sha256': hashlib.sha256(files[label]).hexdigest()}
        return files, pins

    def test_exact_public_bundle_closes_c_without_live_storage_authority(self):
        result = self.verify()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertTrue(result['permanently_spent'])
        for field in ('original_private_journal_observed', 'original_live_scope_observed',
                'live_storage_continuity_proved', 'storage_join_eligible',
                'activation_authorized', 'retry_authorized',
                'scientific_execution_authorized', 'telescope_read_authorized'):
            self.assertIs(result[field], False)

    def test_missing_extra_and_changed_pins_are_refused(self):
        files = dict(self.files); files.pop('launch_start')
        with self.assertRaises(ValueError): self.verify(files=files)
        pins = copy.deepcopy(self.pins); pins['spend_record']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'independent pin'): self.verify(pins=pins)
        files = dict(self.files); files['extra'] = b'{}\n'
        with self.assertRaises(ValueError): self.verify(files=files)

    def test_noncanonical_or_duplicate_json_is_refused_even_when_pinned(self):
        files = dict(self.files); files['spend_record'] = b'{"schema":"x", "schema":"y"}\n'
        pins = dict(self.pins); pins['spend_record'] = {'bytes': len(files['spend_record']),
            'sha256': hashlib.sha256(files['spend_record']).hexdigest()}
        with self.assertRaises(ValueError): self.verify(files=files, pins=pins)

    def test_spend_state_and_cross_file_activation_commit_are_bound(self):
        for label, field, value in (('spend_record', 'state', 'READY'),
                ('launch_start', 'activation_commit', '0' * 40)):
            files, pins = self.changed(label, field, value)
            with self.subTest(label=label, field=field):
                with self.assertRaises(ValueError): self.verify(files=files, pins=pins)

    def test_retry_restart_and_authority_bits_cannot_be_relaxed(self):
        for label, field, value in (('launch_start', 'automatic_retry', True),
                ('launch_start', 'restart_authorized', True),
                ('launch_terminal', 'permanently_spent', False),
                ('launch_terminal', 'scientific_execution_authorized', True),
                ('source_preservation', 'scope_reuse_or_retry_permitted', True)):
            files, pins = self.changed(label, field, value)
            with self.subTest(label=label, field=field):
                with self.assertRaises(ValueError): self.verify(files=files, pins=pins)

    def test_terminal_spend_hash_filename_and_counts_are_cross_checked(self):
        for field, value in (('private_c_claim_sha256', '0' * 64),
                ('private_c_claim_filename', 'spent-forged.json'),
                ('completed_engineering_cases', 1), ('protected_launcher_attempts', 2)):
            files, pins = self.changed('launch_terminal', field, value)
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.verify(files=files, pins=pins)

    def test_inventory_cannot_claim_completed_nonempty_or_scientific_work(self):
        for field, value in (('all_eight_case_directories_empty', False),
                ('completed_engineering_cases', 1),
                ('scientific_execution_authorized', True), ('file_count', 69)):
            files, pins = self.changed('terminal_scope_inventory', field, value)
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.verify(files=files, pins=pins)

    def test_public_archive_never_asserts_original_live_observation(self):
        result = self.verify()
        self.assertNotIn('private_ledger_path', result)
        self.assertFalse(result['storage_join_eligible'])
        self.assertEqual(result['terminal_scope_logical_bytes_label'], 3853729)
        self.assertEqual(result['terminal_scope_allocated_bytes_label'], 4087808)


if __name__ == '__main__':
    unittest.main()
