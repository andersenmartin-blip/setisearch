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
        return self.mutated(label, lambda record: record.__setitem__(field, value))

    def mutated(self, label, mutate):
        files = dict(self.files); record = json.loads(files[label]); mutate(record)
        files[label] = canonical(record)
        pins = dict(self.pins); pins[label] = {'bytes': len(files[label]),
            'sha256': hashlib.sha256(files[label]).hexdigest()}
        return files, pins

    def assert_refused_mutation(self, label, mutate):
        files, pins = self.mutated(label, mutate)
        with self.assertRaises(ValueError):
            self.verify(files=files, pins=pins)

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

    def test_inventory_rows_and_declared_totals_must_agree(self):
        for field, value in (('files', []), ('directories', []),
                ('logical_bytes', 0), ('allocated_bytes', 0),
                ('allocated_bytes', 4087808 + 4096),
                ('logical_bytes', 1536 * 1024 * 1024 + 1)):
            with self.subTest(field=field):
                self.assert_refused_mutation('terminal_scope_inventory',
                    lambda record, field=field, value=value: record.__setitem__(field, value))

    def test_inventory_row_digests_links_and_exact_shapes_are_validated(self):
        for field, value in (('sha256', '0' * 63), ('git_blob_sha', 'g' * 40),
                ('links', True), ('links', 2), ('bytes', True),
                ('allocated_bytes', -1), ('unexpected', False)):
            with self.subTest(field=field, value=value):
                self.assert_refused_mutation('terminal_scope_inventory',
                    lambda record, field=field, value=value:
                        record['files'][0].__setitem__(field, value))
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['files'].__setitem__(0, []))

    def test_inventory_paths_cannot_escape_duplicate_or_alias_directory_labels(self):
        root = 'results_radio_native_v2_compact_control_20261002c'
        for path in ('/tmp/outside.json', root + '/../outside.json',
                root + '//copy.json', root + '/./copy.json', root):
            with self.subTest(path=path):
                self.assert_refused_mutation('terminal_scope_inventory',
                    lambda record, path=path: record['files'][0].__setitem__('path', path))
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['files'][1].__setitem__('path', record['files'][0]['path']))
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['directories'][1].__setitem__('path', root))

    def test_inventory_directory_modes_allocation_and_ancestry_are_validated(self):
        for field, value in (('mode', '0o755'), ('allocated_bytes', True),
                ('allocated_bytes', -1), ('extra', False)):
            with self.subTest(field=field):
                self.assert_refused_mutation('terminal_scope_inventory',
                    lambda record, field=field, value=value:
                        record['directories'][0].__setitem__(field, value))
        root = 'results_radio_native_v2_compact_control_20261002c'
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['files'][0].__setitem__('path', root + '/undeclared/file.json'))

    def test_inventory_empty_case_and_frozen_file_claims_require_corresponding_rows(self):
        root = 'results_radio_native_v2_compact_control_20261002c'
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['files'][0].__setitem__('path', root + '/cases/case00/file.json'))
        self.assert_refused_mutation('terminal_scope_inventory',
            lambda record: record['directories'][9].__setitem__('path', root + '/cases/case08'))
        def move_frozen_file(record):
            row = next(row for row in record['files'] if '/frozen-code/' in row['path'])
            row['path'] = root + '/relocated-frozen-file.json'
        self.assert_refused_mutation('terminal_scope_inventory', move_frozen_file)

    def test_launch_config_commit_ledger_and_utc_fields_are_validated(self):
        for field, value in (('config_sha256', 'bad'), ('public_preread_commit', None),
                ('public_sidecar_commit', 'g' * 40), ('private_c_ledger', '/tmp/other-ledger'),
                ('utc_start', None), ('utc_start', '2026-10-02T19:11:40+00:00'),
                ('utc_start', '2026-02-30T19:11:40Z')):
            with self.subTest(field=field, value=value):
                self.assert_refused_mutation('launch_start',
                    lambda record, field=field, value=value: record.__setitem__(field, value))

    def test_launch_argv_must_bind_isolation_script_and_config(self):
        for mutate in (lambda record: record.__setitem__('argv', None),
                lambda record: record['argv'].__setitem__(0, 'python3'),
                lambda record: record['argv'].__setitem__(1, '-c'),
                lambda record: record['argv'].__setitem__(4, '/tmp/other.py'),
                lambda record: record['argv'].__setitem__(7, '0' * 64)):
            with self.subTest(mutate=mutate):
                self.assert_refused_mutation('launch_start', mutate)

    def test_launch_environment_must_preserve_isolation_and_canonical_path(self):
        for mutate in (lambda record: record.__setitem__('environment', None),
                lambda record: record['environment'].__setitem__('PYTHONSAFEPATH', '0'),
                lambda record: record['environment'].__setitem__('PYTHONPATH', '/tmp'),
                lambda record: record['environment'].pop('GIT_NO_LAZY_FETCH'),
                lambda record: record['environment'].__setitem__('PATH', '/tmp'),
                lambda record: record['environment'].__setitem__('PATH', record['environment']['PATH'] + ':'),
                lambda record: record['environment'].__setitem__('PATH', record['environment']['PATH'] + ':/usr/bin')):
            with self.subTest(mutate=mutate):
                self.assert_refused_mutation('launch_start', mutate)

    def test_terminal_timestamp_must_be_canonical_and_not_precede_start(self):
        for value in (None, '2026-10-02T19:13:08+00:00', '2026-10-02T19:11:39Z'):
            with self.subTest(value=value):
                self.assert_refused_mutation('launch_terminal',
                    lambda record, value=value: record.__setitem__('terminal_utc', value))

    def test_bool_and_float_values_cannot_satisfy_integer_contracts(self):
        changes = {
            'launch_terminal': {'launcher_exit_code': True, 'protected_launcher_attempts': 1.0,
                'completed_engineering_cases': False, 'durable_claim_records': True,
                'telescope_reads': False, 'rng_draws': 0.0},
            'terminal_scope_inventory': {'file_count': 68.0, 'directory_count': 21.0,
                'frozen_materialized_files': 49.0, 'completed_engineering_cases': False},
            'source_preservation': {'pin_count': 1002.0, 'production_source_edits': False,
                'protected_control_invocations_this_turn': True,
                'c_frozen_materialized_files_verified_separately': 49.0}}
        for label, fields in changes.items():
            for field, value in fields.items():
                with self.subTest(label=label, field=field):
                    self.assert_refused_mutation(label,
                        lambda record, field=field, value=value: record.__setitem__(field, value))

    def test_preservation_status_baseline_count_and_no_rerun_claim_are_bound(self):
        for field, value in (('status', 'OTHER'), ('baseline', None),
                ('pin_count', -1), ('tests_rerun_for_metadata_only', True)):
            with self.subTest(field=field):
                self.assert_refused_mutation('source_preservation',
                    lambda record, field=field, value=value: record.__setitem__(field, value))

    def test_scope_label_must_be_canonical_and_bind_the_closed_c_generation(self):
        for scope in ('/tmp/../' + closure.CONTROL_NAME, '//tmp/' + closure.CONTROL_NAME,
                '/tmp/' + closure.CONTROL_NAME + '/',
                '/tmp/results_radio_native_v2_compact_control_20261003d'):
            files = dict(self.files)
            spend = json.loads(files['spend_record']); spend['control_scope'] = scope
            files['spend_record'] = canonical(spend)
            start = json.loads(files['launch_start']); start['scope'] = scope
            files['launch_start'] = canonical(start)
            pins = {label: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                for label, raw in files.items()}
            with self.subTest(scope=scope):
                with self.assertRaises(ValueError): self.verify(files=files, pins=pins)


if __name__ == '__main__':
    unittest.main()
