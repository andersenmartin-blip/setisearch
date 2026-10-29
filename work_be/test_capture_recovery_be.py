"""Lifecycle/acceptance tests using only explicit local synthetic subprocesses."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import capture_recovery_be as capture
import recover_missing_rows_be as recovery


class CaptureRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seti_be_capture_tests_')
        self.root = Path(self.temp.name)
        self.execution = self.root / 'execution'
        self.result = self.root / 'acquire/ACQUISITION_COMPLETE_BE.json'
        self.source = self.root / 'immutable_source.txt'
        self.source.write_text('Synthetic fixture, never telescope data\n')
        self.review = self.root / 'review.json'
        self.review.write_text('{"synthetic_review": true}\n')
        self.access = self.root / 'access.json'
        self.access.write_text('{"synthetic_access_receipt": true}\n')
        source_hash = recovery.sha(self.source)
        self.pins = {'source_path': str(self.source), 'source_sha256': source_hash,
                     'capture_source_sha256': recovery.sha(capture.__file__),
                     'protocol_sha256': 'b' * 64, 'gate_sha256': 'c' * 64,
                     'review_path': str(self.review), 'review_sha256': recovery.sha(self.review),
                     'normal_access_receipt_path': str(self.access),
                     'normal_access_receipt_sha256': recovery.sha(self.access),
                     'input_sha256': {str(self.source): source_hash,
                                      str(self.review): recovery.sha(self.review),
                                      str(self.access): recovery.sha(self.access)}}
        self.marker = {'schema': 'SETI_BE_RECOVERY_ACQUISITION_COMPLETE_V1',
                       'status': 'PASS', 'execution_mode': 'PRODUCTION',
                       'source_sha256': source_hash, 'protocol_sha256': 'b' * 64,
                       **recovery.COUNTS, 'scientific_coverage_credit': 0,
                       'mandatory_native_and_science_checks_pending': True}

    def tearDown(self):
        self.temp.cleanup()

    def command(self, marker=None, code=0, *, write_marker=True, mutate_source=False, mutate_input=None):
        script = "from pathlib import Path; import json,sys\n"
        script += "p=Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True)\n"
        if write_marker:
            script += "p.write_text(sys.argv[2])\n"
        script += "print('synthetic child stdout',flush=True)\n"
        script += "print('synthetic child stderr',file=sys.stderr,flush=True)\n"
        if mutate_source or mutate_input is not None:
            script += "Path(sys.argv[4]).write_text('changed fixture source')\n"
        script += "raise SystemExit(int(sys.argv[3]))\n"
        return [sys.executable, '-c', script, str(self.result),
                json.dumps(self.marker if marker is None else marker), str(code),
                str(self.source if mutate_input is None else mutate_input)]

    def run_fixture(self, command):
        return capture.capture_child(command, self.execution, self.result, self.pins)

    def test_valid_child_eof_wait_and_exact_result_binding(self):
        command = self.command()
        code, actual = self.run_fixture(command)
        self.assertEqual(code, 0)
        self.assertEqual(actual['child_exit_code'], 0)
        self.assertTrue(actual['stdout_eof'])
        self.assertTrue(actual['child_wait_completed'])
        self.assertGreater(actual['child_pid'], 0)
        self.assertTrue(actual['child_launched'])
        self.assertEqual(actual['command'], command)
        self.assertEqual(actual['result_path'], str(self.result.resolve()))
        self.assertEqual(actual['result_sha256'], recovery.sha(self.result))
        self.assertEqual(actual['log_sha256'], recovery.sha(self.execution / 'RECOVERY.log'))
        self.assertEqual(actual['observed_stdout_sha256'], actual['log_sha256'])
        self.assertEqual(actual['observed_stdout_bytes'], actual['log_bytes'])
        log = (self.execution / 'RECOVERY.log').read_text()
        self.assertIn('synthetic child stdout', log)
        self.assertIn('synthetic child stderr', log)
        self.assertIsNone(actual['acceptance_failure'])

    def test_nonzero_child_is_recorded_and_never_success_aliased(self):
        code, actual = self.run_fixture(self.command(code=7))
        self.assertEqual(code, 7)
        self.assertEqual(actual['actual_exit_code'], 7)
        self.assertEqual(actual['child_exit_code'], 7)
        self.assertTrue(actual['stdout_eof'])
        self.assertTrue(actual['child_wait_completed'])
        self.assertIsNone(actual['result_path'])
        self.assertIsNone(actual['result_sha256'])

    def test_child_zero_without_marker_is_explicit_acceptance_failure(self):
        code, actual = self.run_fixture(self.command(write_marker=False))
        self.assertEqual((code, actual['actual_exit_code'], actual['child_exit_code']), (1, 1, 0))
        self.assertIsNotNone(actual['acceptance_failure'])
        self.assertIsNone(actual['result_sha256'])

    def test_simulation_marker_cannot_be_accepted_as_production(self):
        marker = copy.deepcopy(self.marker)
        marker['execution_mode'] = 'SIMULATION'
        code, actual = self.run_fixture(self.command(marker))
        self.assertEqual((code, actual['child_exit_code']), (1, 0))
        self.assertIsNotNone(actual['acceptance_failure'])
        self.assertIsNone(actual['result_path'])

    def test_wrong_source_or_stale_lineage_marker_is_rejected(self):
        marker = copy.deepcopy(self.marker)
        marker['source_sha256'] = 'f' * 64
        marker['new_native_rows'] = 9
        code, actual = self.run_fixture(self.command(marker))
        self.assertEqual(code, 1)
        self.assertEqual(actual['child_exit_code'], 0)
        self.assertIsNotNone(actual['acceptance_failure'])

    def test_source_mutation_during_child_prevents_acceptance(self):
        code, actual = self.run_fixture(self.command(mutate_source=True))
        self.assertEqual((code, actual['child_exit_code']), (1, 0))
        self.assertIn('Capture input changed', actual['acceptance_failure']['error'])
        self.assertIsNone(actual['result_sha256'])

    def test_review_mutation_during_child_prevents_acceptance(self):
        code, actual = self.run_fixture(self.command(mutate_input=self.review))
        self.assertEqual((code, actual['child_exit_code']), (1, 0))
        self.assertIn(str(self.review), actual['acceptance_failure']['error'])
        self.assertIsNone(actual['result_sha256'])

    def test_normal_access_receipt_mutation_during_child_prevents_acceptance(self):
        code, actual = self.run_fixture(self.command(mutate_input=self.access))
        self.assertEqual((code, actual['child_exit_code']), (1, 0))
        self.assertIn(str(self.access), actual['acceptance_failure']['error'])
        self.assertIsNone(actual['result_sha256'])

    def test_review_digest_is_checked_before_spawn(self):
        self.review.write_text('changed before child')
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
            with self.assertRaisesRegex(recovery.RecoveryError, 'Capture input pin differs'):
                self.run_fixture(self.command())
        self.assertFalse(self.execution.exists())

    def test_capture_cannot_overwrite_or_restart(self):
        command = self.command()
        self.run_fixture(command)
        before = {p.name: recovery.sha(p) for p in self.execution.iterdir()}
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
            with self.assertRaisesRegex(recovery.RecoveryError, 'No capture overwrite'):
                self.run_fixture(command)
        self.assertEqual(before, {p.name: recovery.sha(p) for p in self.execution.iterdir()})

    def test_existing_completion_marker_cannot_be_reused(self):
        self.result.parent.mkdir()
        self.result.write_text(json.dumps(self.marker))
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
            with self.assertRaisesRegex(recovery.RecoveryError, 'Existing acquisition marker'):
                self.run_fixture(self.command())
        self.assertFalse(self.execution.exists())

    def test_spawn_failure_has_no_fabricated_pid_eof_or_wait(self):
        code, actual = self.run_fixture([str(self.root / 'no-such-executable')])
        self.assertEqual(code, 1)
        self.assertFalse(actual['child_launched'])
        self.assertIsNone(actual['child_pid'])
        self.assertIsNone(actual['child_exit_code'])
        self.assertFalse(actual['stdout_eof'])
        self.assertFalse(actual['child_wait_completed'])
        self.assertIsNotNone(actual['capture_error'])

    def test_public_api_requires_explicit_execute_before_any_gate_or_child(self):
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
            with self.assertRaisesRegex(recovery.RecoveryError, 'Use --execute explicitly'):
                capture.capture_acquisition(self.root, self.root / 'missing_protocol', self.root,
                                            self.root / 'missing_gate', execute=False)
        self.assertFalse((self.root / 'work_be').exists())

    def test_public_api_rejects_unreleased_gate_before_child(self):
        gate, protocol = self.root / 'gate.json', self.root / 'protocol.json'
        gate.write_text(json.dumps({'schema': 'SETI_BE_RECOVERY_DISPATCH_GATE_V1',
                                    'authorized': False, 'mode': 'PRODUCTION'}))
        protocol.write_text('{}')
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
            with self.assertRaisesRegex(recovery.RecoveryError, 'No production recovery gate'):
                capture.capture_acquisition(self.root, protocol, self.root, gate, execute=True)
        self.assertFalse((self.root / 'work_be').exists())

    def test_gate_asserted_review_and_access_digests_are_not_recomputed_away(self):
        protocol, gate_path = self.root / 'protocol.json', self.root / 'gate.json'
        protocol.write_text('{"synthetic_protocol": true}')
        gate_path.write_text('{"synthetic_gate_fixture_only": true}')
        base = {'source_sha256': recovery.sha(recovery.__file__),
                'protocol_sha256': recovery.sha(protocol), 'review_path': str(self.review),
                'review_sha256': recovery.sha(self.review),
                'normal_access_receipt_path': str(self.access),
                'normal_access_receipt_sha256': recovery.sha(self.access)}
        # Only the validator's return is faked here. No real production gate is
        # created or invoked, and every attempted subprocess launch is forbidden.
        for key in ('review_sha256', 'normal_access_receipt_sha256'):
            gate = {**base, key: 'f' * 64}
            with self.subTest(pin=key):
                with patch.object(recovery, 'production_gate', return_value=(
                        gate, {'protocol_file_sha256': recovery.sha(protocol)})):
                    with patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected child')):
                        with self.assertRaisesRegex(recovery.RecoveryError, 'Capture input pin differs'):
                            capture.capture_acquisition(self.root, protocol, self.root, gate_path, execute=True)
        self.assertFalse((self.root / 'work_be').exists())

    def run_with_log_writer(self, behavior):
        original_open = Path.open
        class Writer:
            def __init__(self, real):
                self.real = real
            def write(self, value):
                if behavior == 'zero':
                    return 0
                if behavior == 'lying_short':
                    self.real.write(value[:3])
                    return len(value)
                return self.real.write(value[:3])
            def flush(self):
                return self.real.flush()
            def fileno(self):
                return self.real.fileno()
            def close(self):
                return self.real.close()
        def open_path(path, mode='r', *args, **kwargs):
            real = original_open(path, mode, *args, **kwargs)
            if path.name == 'RECOVERY.log' and mode == 'xb':
                return Writer(real)
            return real
        with patch.object(Path, 'open', open_path):
            return self.run_fixture(self.command())

    def test_short_log_writes_are_completed_before_acceptance(self):
        code, actual = self.run_with_log_writer('short')
        self.assertEqual(code, 0)
        self.assertEqual(actual['log_bytes'], actual['observed_stdout_bytes'])
        self.assertEqual(actual['log_sha256'], actual['observed_stdout_sha256'])
        self.assertIn('synthetic child stdout', (self.execution / 'RECOVERY.log').read_text())
        self.assertIn('synthetic child stderr', (self.execution / 'RECOVERY.log').read_text())

    def test_zero_progress_log_write_prevents_acceptance(self):
        code, actual = self.run_with_log_writer('zero')
        self.assertEqual(code, 1)
        self.assertIsNone(actual['result_sha256'])
        self.assertIsNotNone(actual['capture_error'])
        self.assertIn('no valid progress', actual['capture_error']['error'])
        self.assertGreater(actual['observed_stdout_bytes'], actual['log_bytes'])

    def test_truncated_log_cannot_be_accepted_even_if_writer_lies_about_count(self):
        code, actual = self.run_with_log_writer('lying_short')
        self.assertEqual(code, 1)
        self.assertEqual(actual['child_exit_code'], 0)
        self.assertTrue(actual['stdout_eof'])
        self.assertTrue(actual['child_wait_completed'])
        self.assertIsNone(actual['result_sha256'])
        self.assertIn('Persisted log differs', actual['acceptance_failure']['error'])


if __name__ == '__main__':
    unittest.main()
