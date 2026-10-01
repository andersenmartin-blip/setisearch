"""Local observer tests; no authenticated publication or scientific execution."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_actions_supervisor.py'
SPEC = importlib.util.spec_from_file_location('actions_supervisor', SCRIPT)
SUPERVISOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPERVISOR)


class SupervisorTests(unittest.TestCase):
    def run_child(self, program, **limits):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        result = SUPERVISOR.supervise_process(
            [sys.executable, '-I', '-S', '-B', '-c', program], output,
            sample_seconds=0.005, **limits)
        return result, output

    def test_kernel_lifetime_peak_and_procfs_identity(self):
        result, output = self.run_child(
            'import time; value=bytearray(12*1024*1024); time.sleep(.04)')
        self.assertEqual(result['status'], 'PASS_COMPONENT_RESOURCE_OBSERVATION')
        self.assertTrue(result['direct_child_termination_coverage_complete'])
        self.assertGreater(result['direct_child_kernel_wait4_peak_rss_bytes'], 12 * 1024 * 1024)
        self.assertNotEqual(result['direct_child_identity'], result['supervisor_identity'])
        self.assertEqual(result['observed_descendant_count'], 0)
        self.assertEqual(result['descendant_lifetime_coverage'], 'kernel_process_creation_prohibited')
        samples = [json.loads(line) for line in (output / 'procfs-samples.jsonl').read_text().splitlines()]
        self.assertTrue(any(row['processes'] for row in samples))
        self.assertTrue(all(row['seccomp_mode'] == 2 for sample in samples for row in sample['processes']))

    def test_fork_and_thread_creation_are_kernel_denied(self):
        result, output = self.run_child('''
import errno, os, threading, time
try:
    os.fork()
    raise AssertionError('fork was not prohibited')
except OSError as error:
    assert error.errno == errno.EPERM
try:
    worker=threading.Thread(target=lambda: None)
    worker.start()
    raise AssertionError('thread creation was not prohibited')
except RuntimeError:
    pass
print('kernel-denial-confirmed')
time.sleep(.02)
''')
        self.assertEqual(result['status'], 'PASS_COMPONENT_RESOURCE_OBSERVATION')
        self.assertIn('kernel-denial-confirmed', (output / 'publisher-stdout.log').read_text())

    def test_deadline_stops_one_process_without_retry(self):
        result, _ = self.run_child('import time; time.sleep(2)', seconds=0.04)
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('deadline_exceeded', result['failures'])
        self.assertLess(result['elapsed_seconds'], 0.3)
        self.assertTrue(result['direct_child_termination_coverage_complete'])

    def test_kernel_peak_enforces_original_limit_even_between_samples(self):
        result, _ = self.run_child(
            'import time; value=bytearray(96*1024*1024); time.sleep(.02)',
            rss_cap=64 * 1024 * 1024)
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('kernel_child_rss_cap_exceeded', result['failures'])
        self.assertFalse(result['native_eight_cases_qualified'])

    def test_existing_log_scope_cannot_resume(self):
        result, output = self.run_child('import time; time.sleep(.02)')
        with self.assertRaises(FileExistsError):
            SUPERVISOR.supervise_process([sys.executable, '-c', 'pass'], output)

    def test_output_capture_is_hard_bounded(self):
        result, output = self.run_child('import sys,time; sys.stdout.write("x"*1000000); sys.stdout.flush(); time.sleep(.05)', log_cap=1024)
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('bounded_log_cap_exceeded', result['failures'])
        self.assertLessEqual((output / 'publisher-stdout.log').stat().st_size, 1024)
        self.assertTrue(result['bounded_logs']['truncated'])

    def test_observer_error_stops_and_reaps_child(self):
        original = SUPERVISOR.proc_snapshot
        calls = 0
        def fail_during_observation():
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise OSError('synthetic observer failure')
            return original()
        with patch.object(SUPERVISOR, 'proc_snapshot', fail_during_observation):
            result, _ = self.run_child('import time; time.sleep(2)')
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('observer_internal_failure', result['failures'])
        self.assertIsNotNone(result['direct_child_kernel_wait4_peak_rss_bytes'])
        self.assertLess(result['elapsed_seconds'], .3)
        self.assertFalse(result['direct_child_termination_coverage_complete'])

    def test_receipt_reopen_detects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            SUPERVISOR.save_json(path, {'authority': False, 'value': '\u00e6'})
            self.assertEqual(json.loads(path.read_text()), {'authority': False, 'value': '\u00e6'})
            original = SUPERVISOR.os.fsync
            calls = 0
            def corrupt_after_file_sync(descriptor):
                nonlocal calls
                calls += 1
                original(descriptor)
                if calls == 2:
                    (Path(directory) / 'corrupt.json').write_bytes(b'changed')
            with patch.object(SUPERVISOR.os, 'fsync', corrupt_after_file_sync):
                with self.assertRaisesRegex(ValueError, 'exact readback failed'):
                    SUPERVISOR.save_json(Path(directory) / 'corrupt.json', {'authority': False})

    def test_foreign_child_recursion_and_runtime_safe_projection(self):
        tree = {1: {'pid': 1, 'ppid': 0}, 2: {'pid': 2, 'ppid': 1},
                3: {'pid': 3, 'ppid': 2}, 4: {'pid': 4, 'ppid': 0}}
        self.assertEqual([row['pid'] for row in SUPERVISOR.descendants(tree, 1)], [2, 3])
        policy = SUPERVISOR.seccomp_policy()
        if policy['architecture'] in ('x86_64', 'amd64'):
            self.assertTrue(policy['x32_denied'])
            self.assertEqual(policy['audit_arch'], 0xc000003e)
        with self.assertRaises(ValueError):
            SUPERVISOR.supervise_process([], Path('/tmp'), seconds=601)


if __name__ == '__main__':
    unittest.main()
