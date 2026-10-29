"""Adversarial offline checks against retained BC bytes and altered copies.

Set SETI_BC_ROOT to the unmodified extracted BC checkpoint and run this file.
The source checkpoint is always read-only; all byte mutations use temp copies.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import tempfile
import unittest
from unittest.mock import patch

import preflight_bd as preflight


BC_ROOT = Path(os.environ.get('SETI_BC_ROOT', str(Path.cwd() / 'restored'))).resolve()


class RecoveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = preflight.read_json(BC_ROOT / 'work_bc/review/PARTIAL_INPUT_PROOF_BC.json')
        cls.spec = preflight.read_json(BC_ROOT / preflight.SPEC_PATH)
        cls.reports = cls.proof['scan5_valid_row_reports']
        cls.summary = cls.proof['partial_summary']
        cls.combined_hash = cls.summary['scan5_valid_rows_power_sha256']
        cls.temp = tempfile.TemporaryDirectory(prefix='seti_bd_preflight_tests_')
        cls.copy_root = Path(cls.temp.name) / 'checkpoint'
        shutil.copytree(BC_ROOT, cls.copy_root)
        cls.array_copy = cls.copy_root / preflight.ARRAY_PATH
        with cls.array_copy.open('rb') as stream:
            stream.seek(8)
            cls.header_length = struct.unpack('<H', stream.read(2))[0]
        cls.payload_offset = 10 + cls.header_length

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def altered_byte(self, path, offset):
        """A context manager restoring a single byte even if assertions fail."""
        from contextlib import contextmanager

        @contextmanager
        def mutation():
            with path.open('r+b') as stream:
                stream.seek(offset)
                old = stream.read(1)
                self.assertEqual(len(old), 1)
                stream.seek(offset)
                stream.write(bytes([old[0] ^ 1]))
            try:
                yield
            finally:
                with path.open('r+b') as stream:
                    stream.seek(offset)
                    stream.write(old)
        return mutation()

    def verify_rows(self, path=None, reports=None):
        return preflight.verify_valid_rows(
            path or self.array_copy,
            self.reports if reports is None else reports,
            self.combined_hash)

    def test_actual_eight_acquired_rows_match_pinned_storage_hashes(self):
        result = self.verify_rows(BC_ROOT / preflight.ARRAY_PATH)
        self.assertEqual([row['time_index'] for row in result['checked_rows']], list(range(8)))
        self.assertEqual(result['acquired_payload_bytes_checked'], 33554432)
        self.assertEqual(result['combined_sha256'], self.combined_hash)
        self.assertEqual(result['unacquired_rows_interpreted'], 0)

    def test_corrupted_acquired_row_is_rejected(self):
        offset = self.payload_offset + 7 * 4194304 + 1234
        with self.altered_byte(self.array_copy, offset):
            with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Acquired row bytes differ: 7'):
                self.verify_rows()

    def test_unacquired_storage_is_not_a_valid_row_but_inventory_still_protects_it(self):
        offset = self.payload_offset + 12 * 4194304 + 3456
        with self.altered_byte(self.array_copy, offset):
            result = self.verify_rows()
            self.assertEqual(len(result['checked_rows']), 8)
            self.assertEqual(result['unacquired_rows_interpreted'], 0)
            with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Member hash differs: .*scan5.npy.partial'):
                preflight.verify_inventory(self.copy_root)

    def test_ninth_row_cannot_be_silently_promoted_to_acquired(self):
        reports = copy.deepcopy(self.reports)
        reports.append({**reports[-1], 'time_index': 8})
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Expected eight acquired rows'):
            self.verify_rows(reports=reports)

    def test_truncated_array_is_rejected_before_row_checks(self):
        tiny = Path(self.temp.name) / 'truncated.npy'
        with self.array_copy.open('rb') as source:
            tiny.write_bytes(source.read(self.payload_offset + 32))
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'NPY file length differs'):
            self.verify_rows(path=tiny)

    def test_changed_storage_order_is_rejected(self):
        with self.array_copy.open('rb') as stream:
            header = stream.read(self.payload_offset)
        changed = header.replace(b'False', b'True ')
        self.assertNotEqual(changed, header)
        tiny = Path(self.temp.name) / 'fortran.npy'
        tiny.write_bytes(changed)
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Unexpected NPY storage layout'):
            self.verify_rows(path=tiny)

    def test_current_transition_has_exact_missing_eight_and_one_repeat(self):
        plan = preflight.transition_plan(self.spec, self.summary)
        self.assertEqual(plan['row_lineage'], {
            'BB_prior': 87, 'BC_prior': 1, 'BD_acquired': 0, 'later_missing': 8, 'expected_total': 96})
        self.assertEqual(plan['resume_scan5_time_indices'], list(range(8, 16)))
        self.assertEqual(plan['repeat_lineage'], {'prior': 5, 'BD_new': 0, 'later_missing': 1})
        self.assertEqual(plan['network_requests_authorized'], 0)

    def test_stale_nine_row_resume_is_rejected(self):
        spec, summary = copy.deepcopy(self.spec), copy.deepcopy(self.summary)
        spec['existing_read_state']['remaining_unacquired_time_rows'] = list(range(7, 16))
        summary['scan5_unacquired_row_indices'] = list(range(7, 16))
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Only eight rows remain'):
            preflight.transition_plan(spec, summary)

    def test_stale_eighty_seven_prior_row_count_is_rejected(self):
        spec, summary = copy.deepcopy(self.spec), copy.deepcopy(self.summary)
        spec['existing_read_state']['total_previously_decoded_rows'] = 87
        summary['validated_native_rows'] = 87
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Expected 88 prior rows'):
            preflight.transition_plan(spec, summary)

    def test_wrong_repeat_coordinate_is_rejected(self):
        spec = copy.deepcopy(self.spec)
        spec['existing_read_state']['remaining_repeat_time_row'] = 8
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Wrong remaining repeat'):
            preflight.transition_plan(spec, self.summary)

    def test_failed_metadata_interval_cannot_be_shifted(self):
        spec = copy.deepcopy(self.spec)
        spec['exact_failed_request']['start'] += 16384
        spec['exact_failed_request']['stop_inclusive'] += 16384
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Pending metadata request differs'):
            preflight.transition_plan(spec, self.summary)

    def test_failed_request_summary_must_match_spec(self):
        summary = copy.deepcopy(self.summary)
        summary['failed_request']['stop_inclusive'] -= 1
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Failure/spec interval mismatch'):
            preflight.transition_plan(self.spec, summary)

    def test_inherited_network_release_cannot_be_invented(self):
        summary = copy.deepcopy(self.summary)
        summary['network_release_authorized'] = True
        with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Unexpected inherited network release'):
            preflight.transition_plan(self.spec, summary)

    def test_corrupted_inventory_member_is_rejected(self):
        first = preflight.read_json(self.copy_root / 'INVENTORY_BC.json')['members'][0]
        path = self.copy_root / first['path']
        with self.altered_byte(path, 0):
            with self.assertRaisesRegex(preflight.InvalidCheckpoint, 'Member hash differs'):
                preflight.verify_inventory(self.copy_root)

    def test_paths_cannot_escape_checkpoint(self):
        for path in ('../elsewhere', '/etc/passwd'):
            with self.subTest(path=path):
                with self.assertRaises(preflight.InvalidCheckpoint):
                    preflight.safe_path(self.copy_root, path)

    def test_full_preflight_performs_no_network_and_retains_blocked_status(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network attempted')):
            result = preflight.preflight(BC_ROOT)
        self.assertEqual(result['inventory']['members_verified'], 136)
        self.assertEqual(result['archive_requests_this_run'], 0)
        self.assertEqual(result['new_observational_rows'], 0)
        self.assertFalse(result['science_completed'])
        self.assertEqual(result['status'], 'PASS_BC_BYTES_ONLY_FULL_RECOVERY_BLOCKED')


if __name__ == '__main__':
    unittest.main()
