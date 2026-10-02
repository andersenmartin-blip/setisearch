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
                {'controls.json', 'supervisor-identity.json', 'subreaper-receipt.json', 'subreaper-measurements.json'} |
                    ({'caller-start.json', 'rss-observation-request.json', 'rss-observation.json'} if name == 'rss-handshake' else set()))
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
            self.assertTrue(receipt['child_escape_guard_installed_before_exec'])
            self.assertTrue(receipt['child_escape_guard_no_new_privileges'])
            self.assertTrue(receipt['child_escape_guard_seccomp_filter'])
            return process, receipt

    def assert_complete(self, process, receipt):
        self.assertEqual(process.returncode, 0, process.stdout.decode())
        self.assertEqual(receipt['status'], 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE')
        self.assertIsNone(receipt['reason'])
        self.assertEqual(receipt['root_exit_code'], 0)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertTrue(receipt['complete_descendant_wait_chain_verified'])
        self.assertEqual(receipt['tree_termination_coverage'], 'SUBREAPER_ECHILD_OBSERVED')

    def test_escape_guard_is_inherited_and_refuses_namespace_tracing_and_clone3(self):
        process, receipt = self.run_probe('escape-guard')
        self.assert_complete(process, receipt)
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)
        self.assertEqual(receipt['retained_output_bytes']['stdout'], len(b'escape guard active\n'))
        self.assertEqual(receipt['reaped_process_count'], 1)
        self.assertIn('clone3', receipt['child_escape_guard_denied_operations'])
        self.assertIn('ptrace', receipt['child_escape_guard_denied_operations'])

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

    def test_storage_scan_is_bounded_and_rejects_nonregular_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory)
            for index in range(32):
                (scope / f'evidence-{index}').write_bytes(b'tiny')
            with mock.patch.object(supervisor, 'MAX_STORAGE_ENTRIES', 32):
                with self.assertRaisesRegex(ValueError, 'entry count'):
                    supervisor.storage_bytes(scope)
            self.assertGreater(supervisor.storage_bytes(scope), 0)
            (scope / 'unexpected-alias').symlink_to(scope / 'evidence-0')
            with self.assertRaisesRegex(ValueError, 'sole-link'):
                supervisor.storage_bytes(scope)

    def test_exact_raw_output_passthrough_has_no_json_summary_or_raw_file(self):
        process, receipt = self.run_probe('stdout-passthrough')
        self.assert_complete(process, receipt)
        self.assertEqual(process.stdout, b'tiny exact forwarded output\n')
        self.assertTrue(receipt['raw_output_passthrough_requested'])
        self.assertTrue(receipt['raw_output_passthrough_complete'])
        self.assertEqual(receipt['observed_output_bytes']['stdout'], len(process.stdout))

    def test_raw_output_backpressure_is_bounded_by_deadline(self):
        read_fd, write_fd = os.pipe()
        try:
            os.set_blocking(write_fd, False)
            while True:
                try: os.write(write_fd, b'x' * 65536)
                except BlockingIOError: break
            with os.fdopen(os.dup(write_fd), 'wb', buffering=0) as stream:
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, 'passthrough deadline'):
                    supervisor.bounded_output_passthrough(stream, b'bounded tiny payload', deadline=started + 0.04)
                self.assertLess(time.monotonic() - started, 0.2)
                self.assertFalse(os.get_blocking(stream.fileno()))
        finally:
            os.close(read_fd); os.close(write_fd)

    def test_caller_rss_accessor_is_bound_to_live_root_and_keeps_final_join_false(self):
        process, receipt = self.run_probe('rss-handshake')
        self.assert_complete(process, receipt)
        callback = receipt['caller_accessor_observation']
        self.assertTrue(callback['completed'])
        self.assertEqual(callback['client_sha256'], '1' * 64)
        self.assertGreater(callback['accessor_peak_rss_bytes'], 0)
        self.assertGreater(receipt['launched_root_procfs_sample_count'], 0)
        self.assertGreaterEqual(receipt['maximum_individual_process_rss_bytes'], callback['accessor_peak_rss_bytes'])
        self.assertTrue(receipt['complete_descendant_wait_chain_verified'])
        self.assertFalse(receipt['supervisor_final_receipt_and_termination_independently_observed'])

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

    def test_all_role_controls_preserve_case_run_command_and_tiny_limits(self):
        for role, limits in supervisor.ROLE_LIMITS.items():
            controls = supervisor.admitted_role_controls(role, limits['seconds'])
            supervisor.validate_admitted_role_controls(controls)
            self.assertEqual(controls['shared_storage_bytes'],
                supervisor.RUN_STORAGE_BYTES if role in ('control', 'verifier') else supervisor.CASE_STORAGE_BYTES)
            self.assertEqual(controls['output_bytes'], 2 * 1024 * 1024 if role == 'command' else 65536)
            with self.subTest(role=role), self.assertRaises(ValueError):
                supervisor.validate_controls(controls)
            for name, changed in [('seconds', limits['seconds'] + 1), ('seconds', True),
                    ('output_bytes', limits['output_bytes'] + 1), ('shared_storage_bytes', limits['shared_storage_bytes'] + 1),
                    ('reaped_children', 65), ('rss_bytes', supervisor.MAX_RSS_BYTES + 1)]:
                with self.subTest(role=role, name=name), self.assertRaises(ValueError):
                    supervisor.validate_admitted_role_controls({**controls, name: changed})

    def test_generic_role_dispatch_checks_before_scope_creation_or_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            for role in supervisor.ROLE_LIMITS:
                if role == 'prepare': continue
                with self.subTest(role=role), \
                        mock.patch.object(supervisor, 'check_admitted_worker', side_effect=ValueError('Rejected role admission')) as check, \
                        mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                    with self.assertRaisesRegex(ValueError, 'Rejected role admission'):
                        supervisor.dispatch_admitted_worker(scope / 'bundle.json', scope, role=role,
                            ordinal=None if role in ('control', 'verifier') else 0,
                            expected_bundle_sha256='0' * 64)
                    check.assert_called_once(); launch.assert_not_called()
                    self.assertFalse(scope.exists())

    def test_exact_supervisor_orig_argv_refuses_extra_flags_and_interpreter_alias(self):
        checked = {'supervisor_python_path': PYTHON}
        prefix = [PYTHON, '-I', '-S', '-B', str(SCRIPT)]
        with mock.patch.object(supervisor.sys, 'orig_argv', prefix + ['--admitted-worker']):
            supervisor.require_exact_supervisor_invocation(checked)
        for argv in ([PYTHON, '-I', '-S', '-B', '-X', 'utf8', str(SCRIPT)],
                ['python', '-I', '-S', '-B', str(SCRIPT)],
                [PYTHON, '-I', '-S', '-B', str(SCRIPT.parent / 'alias.py')]):
            with self.subTest(argv=argv), mock.patch.object(supervisor.sys, 'orig_argv', argv), \
                    self.assertRaisesRegex(RuntimeError, 'Exact supervisor interpreter invocation'):
                supervisor.require_exact_supervisor_invocation(checked)

    def test_caller_rss_handshake_rejects_forged_pid_without_writing_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); now = time.time_ns() // 1000000
            request = {'dispatch_at_epoch_ms': now, 'returned_at_epoch_ms': now, 'client_sha256': '1' * 64}
            supervisor.durable_json(root / 'rss-observation-request.json', request)
            supervisor.durable_json(root / 'caller-start.json', {'identity': 'node-proc:123',
                'pid': 999, 'proc_pid': 123, 'started_at_epoch_ms': now})
            with mock.patch.object(supervisor, 'sample_root_memory') as sample, \
                    self.assertRaisesRegex(ValueError, 'reported start differs'):
                supervisor.caller_rss_handshake(root,
                    root_identity={'procfs_pid': 123, 'namespace_pid': 456}, observer={'procfs_pid': 1},
                    launch_epoch_ms=now, sample_count=1, root_peak=1024, state={})
            sample.assert_not_called()
            self.assertFalse((root / 'rss-observation.json').exists())

    def test_caller_observation_json_refuses_duplicate_and_nonfinite_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            for raw in (b'{"client_sha256":"a","client_sha256":"b"}', b'{"timestamp":NaN}'):
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    supervisor.read_json_evidence(path)

    def test_incomplete_live_rss_publication_retries_without_sampling_or_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'rss-observation-request.json').write_bytes(b'{')
            state = {}
            for failure in (json.JSONDecodeError('incomplete', '{', 1),
                    supervisor.EvidenceChangedDuringRead('live publication changed')):
                with self.subTest(failure=type(failure).__name__), \
                        mock.patch.object(supervisor, 'read_json_evidence', side_effect=failure), \
                        mock.patch.object(supervisor, 'sample_root_memory') as sample:
                    supervisor.caller_rss_handshake(root, root_identity={}, observer={},
                        launch_epoch_ms=1, sample_count=1, root_peak=1, state=state)
                    sample.assert_not_called()
                    self.assertEqual(state, {})
                    self.assertFalse((root / 'rss-observation.json').exists())

    def test_engineering_pin_reader_refuses_oversized_input_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'oversized'
            path.write_bytes(b'tiny bounded engineering evidence')
            with mock.patch.object(supervisor.os, 'read') as read:
                with self.assertRaisesRegex(ValueError, 'Bounded regular'):
                    supervisor.pin_file(path, maximum=4)
                read.assert_not_called()

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
            checked = {'receipt_scope': str(scope), 'argv': [PYTHON, '-c', 'pass'],
                'activation_evidence': {}}
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

    def synthetic_admission_helpers(self):
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
        return helpers

    def synthetic_admission_materials(self, root):
        return self.synthetic_admission_helpers().synthetic_worker_materials(root)

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
                with self.assertRaisesRegex(RuntimeError, 'complete minimal supervisor environment'):
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


    def test_real_role_checks_bind_case_and_whole_layouts_without_dispatch(self):
        helpers = self.synthetic_admission_helpers()
        for role in ('caller', 'command', 'lossless-project', 'control', 'verifier'):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                materials = helpers.synthetic_role_materials(Path(directory), role)
                worker = materials['role_materials']
                before = sorted(str(path) for path in Path(directory).rglob('*'))
                with mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                        mock.patch.object(supervisor.sys, 'flags',
                            types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                    checked, _ = supervisor.check_admitted_worker(worker['bundle_path'], role=role,
                        ordinal=worker['ordinal'], expected_bundle_sha256=worker['bundle_sha256'])
                    self.assertEqual(checked['argv'], worker['argv'])
                    self.assertEqual(checked['role'], role)
                    self.assertFalse(checked['execution_authorized'])
                    expected_scope = materials['scope'] if role in ('control', 'verifier') else materials['case_root']
                    self.assertEqual(checked['worker_scope'], str(expected_scope))
                    self.assertEqual(checked['shared_storage_root'], str(expected_scope))
                    self.assertFalse(Path(checked['receipt_scope']).exists())
                    with self.assertRaisesRegex(RuntimeError, 'complete minimal supervisor environment'):
                        supervisor.dispatch_admitted_worker(worker['bundle_path'], checked['receipt_scope'],
                            role=role, ordinal=worker['ordinal'], expected_bundle_sha256=worker['bundle_sha256'])
                    launch.assert_not_called()
                self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))


if __name__ == '__main__':
    unittest.main()
