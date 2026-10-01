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
import types
import unittest
from unittest import mock

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
                {'controls.json', 'supervisor-identity.json', 'subreaper-receipt.json', 'subreaper-measurements.json'})
            measurements = json.loads((scope / 'subreaper-measurements.json').read_bytes())
            self.assertEqual(measurements['status'], 'PENDING_FILESYSTEM_DISPOSITION')
            self.assertTrue(receipt['measurements_fsynced_before_disposition'])
            self.assertTrue(receipt['filesystem_checks_completed_before_disposition'])
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

    def test_pipeline_controls_are_separate_and_keep_original_case_caps(self):
        controls = {'schema': supervisor.SCHEMA + '-admitted-prepare-controls',
            'seconds': 600, 'output_bytes': 65536, 'reaped_children': 64,
            'case_storage_bytes': 192 * 1024 * 1024, 'rss_bytes': 512 * 1024 * 1024,
            'worker_role': 'prepare'}
        supervisor.validate_admitted_prepare_controls(controls)
        with self.assertRaises(ValueError): supervisor.validate_controls(controls)
        for field, value in [('seconds', 601), ('seconds', True), ('seconds', float('nan')),
                ('output_bytes', 65537), ('reaped_children', 65), ('case_storage_bytes', 193 * 1024 * 1024),
                ('rss_bytes', 513 * 1024 * 1024), ('worker_role', 'arbitrary')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                supervisor.validate_admitted_prepare_controls({**controls, field: value})

    def test_admitted_dispatch_checks_before_creating_scope_or_spawning(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            with mock.patch.object(supervisor, 'check_admitted_prepare_worker',
                    side_effect=ValueError('Rejected admission')) as check, \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'Rejected admission'):
                    supervisor.dispatch_admitted_prepare_worker(scope / 'missing.json', scope,
                        ordinal=0, expected_bundle_sha256='0' * 64)
                check.assert_called_once(); launch.assert_not_called()
                self.assertFalse(scope.exists())

    def test_materialized_fixture_gate_refuses_before_scope_and_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'preparation-supervisor'
            checked = {'receipt_scope': str(scope), 'argv': [PYTHON, '-c', 'pass']}
            fixture = mock.Mock()
            fixture.require_execution_ready.side_effect = RuntimeError('BLOCKED_PREPARATION_REVIEW')
            with mock.patch.object(supervisor, 'check_admitted_prepare_worker', return_value=(checked, fixture)), \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor.sys, 'flags',
                        types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                with self.assertRaisesRegex(RuntimeError, 'BLOCKED_PREPARATION_REVIEW'):
                    supervisor.dispatch_admitted_prepare_worker(scope / 'bundle.json', scope,
                        ordinal=0, expected_bundle_sha256='0' * 64)
                fixture.require_execution_ready.assert_called_once()
                launch.assert_not_called(); self.assertFalse(scope.exists())

    def test_admitted_cli_requires_independently_retained_bundle_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT),
                '--admitted-prepare-worker', '--admission-bundle', str(scope / 'bundle.json'),
                '--ordinal', '0', '--scope', str(scope)], capture_output=True, timeout=3,
                env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'retained SHA256', process.stderr)
            self.assertFalse(scope.exists())

    def test_admission_check_only_rejects_scope_and_checks_without_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--admission-check-only',
                '--admission-bundle', str(scope / 'bundle.json'), '--bundle-sha256', '0' * 64,
                '--ordinal', '0', '--scope', str(scope)], capture_output=True, timeout=3,
                env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'no receipt scope', process.stderr)
            self.assertFalse(scope.exists())

    def test_bundle_hash_and_special_files_refuse_before_loading_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle.json'; bundle.write_bytes(b'{}')
            with mock.patch.object(supervisor, 'source_module') as loader, \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'retained byte hash'):
                    supervisor.check_admitted_prepare_worker(bundle, ordinal=0,
                        expected_bundle_sha256='0' * 64)
                loader.assert_not_called(); launch.assert_not_called()
                fifo = Path(directory) / 'fifo'; os.mkfifo(fifo)
                with self.assertRaisesRegex(ValueError, 'sole-link'):
                    supervisor.check_admitted_prepare_worker(fifo, ordinal=0,
                        expected_bundle_sha256='0' * 64)

    def test_source_module_ignores_bytecode_and_rejects_changed_source_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'module.py'; source.write_bytes(b'value=7\n')
            expected = supervisor.pin_file(source)
            loaded = supervisor.source_module(source, 'tiny_source_module', expected)
            self.assertEqual(loaded.value, 7)
            source.write_bytes(b'value=8\n')
            with self.assertRaisesRegex(ValueError, 'source pin drift'):
                supervisor.source_module(source, 'tiny_source_module', expected)
            self.assertEqual(set(Path(directory).iterdir()), {source})

    def test_unverified_bundle_cannot_select_executable_admission_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'bundle.json'
            own_key = 'scripts/radio_native_v2_process_tree_supervisor.py'
            module_key = 'scripts/radio_native_v2_worker_admission.py'
            supplied = {'plan': {'code_files': {own_key: supervisor.pin_file(SCRIPT),
                module_key: {'bytes': 10, 'sha256': '0' * 64}}}, 'code_root': str(root)}
            raw = supervisor.canonical(supplied) + b'\n'; bundle.write_bytes(raw)
            with mock.patch.object(supervisor, 'source_module') as loader:
                with self.assertRaisesRegex(ValueError, 'bootstrap pins'):
                    supervisor.check_admitted_prepare_worker(bundle, ordinal=0,
                        expected_bundle_sha256=hashlib.sha256(raw).hexdigest())
                loader.assert_not_called()
            self.assertEqual(set(root.iterdir()), {bundle})

    def test_actual_supervisor_interpreter_flags_are_checked_before_mutation(self):
        flags = types.SimpleNamespace(isolated=0, no_site=1, dont_write_bytecode=1)
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
                'output_bytes': 100, 'reaped_children': 2}
            with mock.patch.object(supervisor.sys, 'flags', flags), \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor, 'set_subreaper') as setter:
                with self.assertRaisesRegex(RuntimeError, 'Actual isolated'):
                    supervisor.supervise_engineering_subprocess([PYTHON, '-c', 'pass'], scope,
                        controls, dedicated_process=True)
                setter.assert_not_called(); launch.assert_not_called()
                self.assertFalse(scope.exists())

    def test_bootstrap_pins_bind_current_reviewed_dependency_sources(self):
        for relative, expected in supervisor.BOOTSTRAP_SOURCE_PINS.items():
            self.assertEqual(supervisor.pin_file(ROOT / relative), expected, relative)

    def synthetic_admission_materials(self, root):
        # Reuse tiny supplied-claim materials; no prospective generator runs.
        modules = {}
        for name in ('radio_native_v2_compact_eight_case_resource_fixture',
                'radio_native_v2_worker_admission'):
            relative = 'scripts/' + name + '.py'
            modules[name] = supervisor.source_module(ROOT / relative, name,
                supervisor.BOOTSTRAP_SOURCE_PINS[relative])
        with mock.patch.dict(sys.modules, modules):
            helpers = supervisor.source_module(ROOT / 'tests/test_radio_native_v2_worker_admission.py',
                'tiny_supplied_claim_helpers')
        return helpers.synthetic_worker_materials(root)

    def test_real_structural_check_is_read_only_and_large_dispatch_stays_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            materials = self.synthetic_admission_materials(Path(directory))
            before = sorted(str(path) for path in Path(directory).rglob('*'))
            with mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor.sys, 'flags',
                        types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                checked, fixture = supervisor.check_admitted_prepare_worker(materials['bundle_path'],
                    ordinal=0, expected_bundle_sha256=materials['bundle_sha256'])
                self.assertEqual(checked['argv'], materials['argv'])
                self.assertFalse(checked['independent_immutable_publication_join_complete'])
                self.assertEqual(checked['materialized_fixture_execution_status'], 'BLOCKED_PREPARATION_REVIEW')
                self.assertEqual(checked['structural_admission']['status'],
                    'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED')
                with self.assertRaisesRegex(RuntimeError, 'BLOCKED_PREPARATION_REVIEW'):
                    supervisor.dispatch_admitted_prepare_worker(materials['bundle_path'],
                        Path(checked['receipt_scope']), ordinal=0,
                        expected_bundle_sha256=materials['bundle_sha256'])
                launch.assert_not_called()
            self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))
            self.assertFalse((materials['case_root'] / 'deterministic-source.bin').exists())

    def test_real_admission_check_cli_has_no_scope_or_generator_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            materials = self.synthetic_admission_materials(Path(directory))
            before = sorted(str(path) for path in Path(directory).rglob('*'))
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--admission-check-only',
                '--admission-bundle', str(materials['bundle_path']), '--bundle-sha256', materials['bundle_sha256'],
                '--ordinal', '0'], capture_output=True, timeout=8, env=supervisor.ENVIRONMENT)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            result = json.loads(process.stdout)
            self.assertFalse(result['execution_authorized'])
            self.assertEqual(result['argv'], materials['argv'])
            self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))


if __name__ == '__main__':
    unittest.main()
