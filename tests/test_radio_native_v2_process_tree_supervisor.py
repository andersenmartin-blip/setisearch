"""Tiny isolated dedicated-supervisor tests; no pipeline/scientific execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/radio_native_v2_process_tree_supervisor.py'
SPEC = importlib.util.spec_from_file_location('tree_supervisor', SCRIPT)
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)
PYTHON = str(Path(sys.executable).resolve())


class DedicatedSubreaperTests(unittest.TestCase):
    def run_probe(self, name, *, seconds=3, output=65536, children=64):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'fresh-control'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--probe', name,
                '--scope', str(scope), '--seconds', str(seconds), '--output-bytes', str(output),
                '--reaped-children', str(children)], capture_output=True, timeout=8,
                env=supervisor.ENVIRONMENT)
            receipt = json.loads((scope / 'subreaper-receipt.json').read_bytes())
            self.assertEqual(process.stderr, b'', process.stderr.decode())
            self.assertEqual(set(path.name for path in scope.iterdir()),
                {'controls.json', 'supervisor-identity.json', 'subreaper-receipt.json'})
            self.assertLess(supervisor.storage_bytes(scope), supervisor.MAX_STORAGE_BYTES)
            self.assertFalse(receipt['raw_stdout_duplicate_written'])
            self.assertFalse(receipt['raw_stderr_duplicate_written'])
            self.assertTrue(receipt['subreaper_set_and_get_verified'])
            self.assertFalse(receipt['complete_process_tree_qualified'])
            self.assertFalse(receipt['supervisor_final_receipt_and_termination_independently_observed'])
            for key, value in supervisor.AUTHORITY.items():
                self.assertEqual(receipt[key], value, key)
            self.assertEqual(receipt['supervisor_code'], supervisor.pin_file(SCRIPT))
            self.assertEqual(receipt['engineering_input_pin']['source_sha256'],
                hashlib.sha256(supervisor.PROBES[name].encode()).hexdigest())
            self.assertTrue(receipt['sole_wait4_owner'])
            return process, receipt

    def assert_complete(self, process, receipt):
        self.assertEqual(process.returncode, 0, process.stdout.decode())
        self.assertEqual(receipt['status'], 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE')
        self.assertIsNone(receipt['reason'])
        self.assertEqual(receipt['root_exit_code'], 0)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertEqual(receipt['tree_termination_coverage'], 'SUBREAPER_ECHILD_OBSERVED')

    def test_proper_nested_wait_is_covered_by_root_kernel_receipt(self):
        process, receipt = self.run_probe('nested-wait')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 1)
        self.assertEqual(receipt['reaped_processes'][0]['kind'], 'launched_root')
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)
        self.assertGreater(receipt['maximum_individual_process_rss_bytes'], 2 * 1024 * 1024)

    def test_orphan_is_adopted_reaped_and_required_before_echild(self):
        process, receipt = self.run_probe('orphan')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertEqual({row['kind'] for row in receipt['reaped_processes']},
            {'launched_root', 'adopted_orphan'})
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)

    def test_double_fork_has_no_unreaped_daemon_in_subreaper_scope(self):
        process, receipt = self.run_probe('double-fork')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertEqual(sum(row['kind'] == 'adopted_orphan' for row in receipt['reaped_processes']), 1)

    def test_nonzero_adopted_exit_closes_even_when_root_exit_is_zero(self):
        process, receipt = self.run_probe('adopted-nonzero')
        self.assertEqual(process.returncode, 2)
        self.assertEqual(receipt['status'], 'CLOSED_FAILED')
        self.assertIn('nonzero', receipt['reason'])
        self.assertEqual(receipt['root_exit_code'], 0)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertTrue(any(row['kind'] == 'adopted_orphan' and row['exit_code'] == 7
            for row in receipt['reaped_processes']))

    def test_deadline_kills_root_then_adopted_children_by_pidfd_and_reaps(self):
        started = time.monotonic()
        process, receipt = self.run_probe('timeout', seconds=0.3)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(process.returncode, 2)
        self.assertIn('deadline', receipt['reason'])
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertGreaterEqual(receipt['pidfd_cancellation_count'], 2)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertTrue(all(row['exit_code'] < 0 for row in receipt['reaped_processes']))

    def test_output_overflow_remains_bounded_and_is_never_written_as_raw_file(self):
        process, receipt = self.run_probe('output-overflow', output=4096)
        self.assertEqual(process.returncode, 2)
        self.assertIn('output cap', receipt['reason'])
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 4096)
        self.assertEqual(receipt['retained_output_bytes']['stdout'], 4096)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])

    def test_reaped_receipt_count_is_bounded_and_overflow_closes(self):
        process, receipt = self.run_probe('orphan', children=1)
        self.assertEqual(process.returncode, 2)
        self.assertIn('reaped-child count', receipt['reason'])
        self.assertEqual(len(receipt['reaped_processes']), 1)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])

    def test_generic_function_refuses_shared_process_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'uncreated'
            controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
                'output_bytes': 100, 'reaped_children': 2}
            with self.assertRaisesRegex(RuntimeError, 'dedicated-process'):
                supervisor.supervise_engineering_subprocess([PYTHON, '-c', 'pass'], scope, controls)
            self.assertFalse(scope.exists())

    def test_cli_does_not_accept_generic_argv_or_existing_worker_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'uncreated'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--scope', str(scope),
                '--argv', PYTHON, '--control-worker', 'closed-existing-scope'],
                capture_output=True, timeout=3, env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(scope.exists())

    def test_control_limits_reject_boolean_nonfinite_and_oversized_values(self):
        controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
            'output_bytes': 100, 'reaped_children': 2}
        for field, value in [('seconds', True), ('seconds', float('nan')),
                ('seconds', float('inf')), ('seconds', 11), ('output_bytes', True),
                ('output_bytes', 65537), ('reaped_children', 0), ('reaped_children', 65)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                supervisor.validate_controls({**controls, field: value})


if __name__ == '__main__':
    unittest.main()
