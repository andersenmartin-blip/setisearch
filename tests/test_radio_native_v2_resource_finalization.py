"""Tiny process and synthetic receipt tests; no full source/native/science run."""
import contextlib
import copy
import hashlib
import io
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

import radio_native_v2_resource_finalization as finalization


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = finalization.canonical(value)+b'\n'
    path.write_bytes(raw)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ResourceFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.scope = Path(self.temporary.name)
        self.python = str(Path(sys.executable).resolve())
        self.runner_argv = [self.python, '-I', '-S', '-B', '/tiny/pinned-supervisor.py', '--admitted-worker']
        self.driver_argv = [self.python, '-I', '-S', '-B', '/tiny/pinned-driver.py', '--admitted-whole-control-driver']
        self.start = 1_000_000_000
        self.worker = {'status': 'PENDING_FINAL_MEASUREMENT_JOIN', 'cases': [], **finalization.AUTHORITY}
        for ordinal in range(8):
            case = self.scope/'cases'/f'case{ordinal:02d}'
            case.mkdir(parents=True)
            (case/'tiny.txt').write_text('explicit tiny synthetic case fixture\n')
            self.worker['cases'].append({'ordinal': ordinal,
                'source_case_id': finalization.NAMESPACE+f'/case{ordinal:02d}',
                'preparation_through_lossless_seconds': 0.02,
                'continuous_verifier_append_seconds': 0.01,
                'calls': 1, 'request_bytes': 2, 'response_bytes': 3})
        write_json(self.scope/'worker-result.json', self.worker)
        self.runner = self.observation(self.runner_argv, 1_200_000_000, 1_400_000_000,
            procfs_pid=102, namespace_pid=2)
        write_json(self.scope/finalization.RUNNER_OBSERVATION_NAME, self.runner)
        self.subreaper = {'status': 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE',
            'root_exit_code': 0, 'sole_wait4_owner': True, 'subreaper_set_and_get_verified': True,
            'subreaper_scope_reaped_to_echild': True, 'maximum_individual_process_rss_bytes': 1024,
            'supervisor_identity': {'procfs_pid': 102, 'namespace_pid': 2},
            'complete_descendant_wait_chain_verified': False,
            'synthetic_test_fixture': True}
        write_json(self.scope/'whole-control-supervisor/subreaper-receipt.json', self.subreaper)
        write_json(self.scope/finalization.DRIVER_IDENTITY_NAME, {'procfs_pid': 101, 'namespace_pid': 1})
        with mock.patch.object(finalization.time, 'monotonic_ns', return_value=1_600_000_000):
            self.pending = finalization.capture_pending_measurements(self.scope,
                admission_start_monotonic_ns=self.start, expected_runner_argv=self.runner_argv)
        self.pending_pin = write_json(self.scope/finalization.PENDING_NAME, self.pending)
        self.driver = self.observation(self.driver_argv, 1_100_000_000, 1_800_000_000,
            procfs_pid=101, namespace_pid=1)
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)

    def observation(self, argv, start, end, *, procfs_pid, namespace_pid):
        return {'schema': finalization.OBSERVATION_SCHEMA,
            'synthetic_test_fixture': True, 'observed_argv': list(argv),
            'child_environment': dict(finalization.ENVIRONMENT),
            'includes_entire_child_lifetime': True, 'reported_identity_verified': True,
            'direct_child_reaped': True, 'observer_source': 'independent_parent_procfs_and_kernel_wait4',
            'exit_code': 0, 'reason': None,
            'bound_child_identity': {'procfs_pid': procfs_pid, 'namespace_pid': namespace_pid,
                'procfs_start_ticks': '12345', 'namespace_pid_chain': [procfs_pid, namespace_pid]},
            'monotonic_start_ns': start, 'monotonic_end_ns': end,
            'peak_rss_bytes': 1024, 'observer_self_kernel_peak_rss_bytes': 2048,
            'child_executable_pin': finalization._interpreter_pin(self.python)}

    def join(self, *, now=2_000_000_000, **overrides):
        options = {'expected_pending_pin': self.pending_pin,
            'expected_driver_observation_pin': self.driver_pin,
            'expected_driver_argv': self.driver_argv, 'expected_runner_argv': self.runner_argv,
            'expected_admission_start_monotonic_ns': self.start}
        options.update(overrides)
        with mock.patch.object(finalization.time, 'monotonic_ns', return_value=now):
            return finalization.join_final_measurements(self.scope, **options)

    def assert_closed(self, result, phrase=None):
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertFalse(result['complete_resource_measurement_join_qualified'])
        if phrase: self.assertIn(phrase, result['error'])

    def final_report_input(self, scope=None, *, complete=False, tiny=True):
        scope = Path(scope or self.scope)
        return {'schema': finalization.SCHEMA+('-tiny-final-report-input' if tiny else '-final-report-input'),
            'scope': str(scope), 'status': 'TINY_ENGINEERING_REPORT_PROBE' if tiny else 'PENDING_FINAL_MEASUREMENT_JOIN',
            'complete_resource_measurement_join_qualified': complete,
            'final_reporting_process_termination_covered': False,
            'final_disposition_persisted': False,
            **({'tiny_engineering_probe_only': True} if tiny else {}), **finalization.AUTHORITY}

    def test_tiny_synthetic_join_counts_shared_directories_and_reserved_final_metadata(self):
        result = self.join()
        self.assertEqual(result['status'], 'SYNTHETIC_RESOURCE_BOUNDS_CHECKED')
        self.assertTrue(result['reported_resource_bounds_within_original_caps'])
        self.assertFalse(result['complete_resource_measurement_join_qualified'])
        self.assertFalse(result['final_reporting_process_termination_covered'])
        self.assertFalse(result['final_disposition_persisted'])
        self.assertEqual(result['timing']['complete_measured_elapsed_seconds'], 1.0)
        self.assertAlmostEqual(sum(row['complete_case_seconds'] for row in result['timing']['cases']), 1.0)
        self.assertGreater(result['storage']['shared_allocated_bytes'], finalization.METADATA_RESERVATION_BYTES)
        self.assertFalse((self.scope/finalization.FINAL_NAME).exists())
        for key, expected in finalization.AUTHORITY.items(): self.assertEqual(result[key], expected)

    def test_missing_driver_receipt_preserves_pending(self):
        (self.scope/finalization.DRIVER_OBSERVATION_NAME).unlink()
        result = self.join()
        self.assertEqual(result['status'], 'PENDING_FINAL_MEASUREMENT_JOIN')
        self.assertIn('not available', result['pending_reasons'][0])

    def test_forged_driver_receipt_bytes_fail_expected_pin(self):
        self.driver['exit_code'] = 7
        write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        self.assert_closed(self.join(), 'byte pin')

    def test_rehashed_driver_with_unexpected_interpreter_argv_still_fails(self):
        self.driver['observed_argv'].remove('-S')
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        self.assert_closed(self.join(), 'interpreter argv')

    def test_interpreter_executable_hash_cannot_be_self_selected(self):
        self.driver['child_executable_pin']['sha256'] = '0'*64
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        self.assert_closed(self.join(), 'actual installed runtime')

    def test_identity_swap_rejected_after_rehash(self):
        self.driver['bound_child_identity']['procfs_pid'] = 103
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        self.assert_closed(self.join(), 'child identity')

    def test_changed_admission_stamp_is_not_taken_from_pending_json(self):
        self.pending['admission_start_monotonic_ns'] += 1
        self.pending_pin = write_json(self.scope/finalization.PENDING_NAME, self.pending)
        self.assert_closed(self.join(), 'parent stamp')

    def test_driver_receipt_must_cover_snapshot_fsync_and_termination(self):
        self.driver['monotonic_end_ns'] = 1_500_000_000
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        self.assert_closed(self.join(), 'snapshot fsync/termination')

    def test_delayed_outer_finalization_is_charged_before_disposition(self):
        result = self.join(now=self.start+4_801_000_000_000)
        self.assert_closed(result, '600-second case')

    def test_extra_file_after_driver_snapshot_cannot_hide_as_shared_overhead(self):
        (self.scope/'unreserved-added.txt').write_bytes(b'x')
        self.assert_closed(self.join(), 'scope changed')

    def test_metadata_reservation_replaces_materialized_bytes_instead_of_double_count(self):
        before = self.join()['storage']
        write_json(self.scope/finalization.FINAL_NAME, {'status': 'PENDING_FINAL_MEASUREMENT_JOIN'})
        after = self.join()['storage']
        self.assertEqual(before['whole_logical_bytes_with_remaining_reservation'], after['whole_logical_bytes_with_remaining_reservation'])
        self.assertEqual(before['whole_allocated_bytes_with_remaining_reservation'], after['whole_allocated_bytes_with_remaining_reservation'])

    def test_terminal_metadata_overallocation_is_rejected(self):
        path = self.scope/finalization.FINAL_NAME
        with path.open('wb') as handle:
            os.posix_fallocate(handle.fileno(), 0, finalization.METADATA_RESERVATION_BYTES+4096)
        self.assert_closed(self.join(), 'reservation')

    def test_filesystem_failure_does_not_leave_or_write_pass(self):
        before = (self.scope/finalization.PENDING_NAME).read_bytes()
        with mock.patch.object(finalization, 'storage_inventory', side_effect=OSError('synthetic disk failure')):
            result = self.join()
        self.assert_closed(result, 'synthetic disk failure')
        self.assertEqual((self.scope/finalization.PENDING_NAME).read_bytes(), before)
        self.assertFalse((self.scope/finalization.FINAL_NAME).exists())

    def test_persisted_final_report_requires_and_joins_distinct_writer_observation(self):
        input_pin = write_json(self.scope/finalization.FINAL_INPUT_NAME,
            self.final_report_input())
        _, report_pin = finalization.persist_tiny_final_report_probe(
            self.scope, expected_input_pin=input_pin)
        identity = json.loads((self.scope/finalization.FINAL_WRITER_IDENTITY_NAME).read_text())
        writer_argv = [self.python, '-I', '-S', '-B',
            str(Path(finalization.__file__).resolve()), '--tiny-final-report-writer',
            '--scope', str(self.scope), '--input-bytes', str(input_pin['bytes']),
            '--input-sha256', input_pin['sha256']]
        observation = self.observation(writer_argv, 2_100_000_000, 2_200_000_000,
            procfs_pid=identity['procfs_pid'], namespace_pid=identity['namespace_pid'])
        observation_pin = write_json(
            self.scope/finalization.FINAL_WRITER_OBSERVATION_NAME, observation)
        result = finalization.join_final_report_lifetime(self.scope,
            expected_input_pin=input_pin, expected_report_pin=report_pin,
            expected_writer_observation_pin=observation_pin,
            expected_writer_argv=writer_argv)
        self.assertFalse(result['outer_report_fsync_and_termination_independently_observed'])
        self.assertFalse(result['final_reporting_process_termination_covered'])
        self.assertTrue(result['final_disposition_persisted'])
        self.assertFalse(result['complete_resource_measurement_join_qualified'])
        self.assertFalse(result['terminal_observer_own_future_termination_covered'])
        self.assertEqual(result['status'], 'SYNTHETIC_TINY_ENGINEERING_REPORT_WRITER_FIXTURE')
        self.assertEqual(result['final_report_observation_scope'], 'tiny_engineering_probe_writer_only')

    def test_actual_isolated_final_report_writer_fsyncs_and_exits(self):
        import radio_native_v2_compact_eight_case_resource_fixture as fixture
        scope = self.scope/'actual-writer'
        scope.mkdir()
        input_pin = write_json(scope/finalization.FINAL_INPUT_NAME,
            self.final_report_input(scope))
        argv = [self.python, '-I', '-S', '-B', str(Path(finalization.__file__).resolve()),
            '--tiny-final-report-writer', '--scope', str(scope),
            '--input-bytes', str(input_pin['bytes']), '--input-sha256', input_pin['sha256']]
        observed, stdout, stderr = fixture.observe_process(argv, scope, 'final-report-writer',
            scope/finalization.FINAL_WRITER_IDENTITY_NAME, deadline=time.monotonic()+5,
            pipe_output=True)
        self.assertEqual(stdout, b''); self.assertEqual(stderr, b'')
        report, report_pin = finalization.read_pinned_json(scope/finalization.FINAL_NAME)
        self.assertTrue(report['report_writer_fsync_completed_before_return'])
        self.assertTrue(report['final_disposition_persisted'])
        self.assertFalse(report['final_reporting_process_termination_covered'])
        self.assertTrue(report['tiny_engineering_probe_only'])
        self.assertEqual(report['report_writer_mode'], 'TINY_ENGINEERING_PROBE')
        self.assertFalse(report['complete_resource_measurement_join_qualified'])
        self.assertFalse(report['material_scope_gate']['real_control_or_runtime_custody_qualified'])
        _, observation_pin = finalization.read_pinned_json(scope/finalization.FINAL_WRITER_OBSERVATION_NAME)
        joined = finalization.join_final_report_lifetime(scope, expected_input_pin=input_pin,
            expected_report_pin=report_pin, expected_writer_observation_pin=observation_pin,
            expected_writer_argv=argv)
        self.assertTrue(joined['outer_report_fsync_and_termination_independently_observed'])
        self.assertTrue(joined['final_reporting_process_termination_covered'])
        self.assertFalse(joined['synthetic_report_writer_observation_fixture'])
        self.assertFalse(joined['complete_resource_measurement_join_qualified'])
        self.assertEqual(joined['status'], 'TINY_ENGINEERING_REPORT_PROBE_WRITER_OBSERVED')

    def test_production_writer_material_custody_gate_precedes_identity_or_output(self):
        input_pin = write_json(self.scope/finalization.FINAL_INPUT_NAME,
            self.final_report_input(tiny=False))
        before = sorted(str(path) for path in self.scope.rglob('*'))
        with mock.patch.object(finalization, 'check_final_report_material_scope',
                side_effect=ValueError('material runtime custody changed')) as gate, \
                mock.patch.object(finalization, '_write_durable_exclusive') as write:
            with self.assertRaisesRegex(ValueError, 'runtime custody changed'):
                finalization.persist_final_report(self.scope, expected_input_pin=input_pin)
            gate.assert_called_once_with(self.scope)
            write.assert_not_called()
        self.assertEqual(before, sorted(str(path) for path in self.scope.rglob('*')))

    def material_scope_records(self, scope):
        code_root = scope/'frozen-code'; (code_root/'scripts').mkdir(parents=True)
        own = code_root/finalization.SELF; own.write_bytes(b'# tiny material-path placeholder\n')
        plan = {'code_files': copy.deepcopy(finalization.BOOTSTRAP_SOURCE_PINS),
            'runtime_executables': {'python': {'path': self.python}}}
        plan['code_files'][finalization.SELF] = {'bytes': own.stat().st_size,
            'sha256': hashlib.sha256(own.read_bytes()).hexdigest()}
        records = {'plan': plan, 'freeze': {'synthetic_unit_receipt': 'freeze'},
            'preread': {'synthetic_unit_receipt': 'preread'},
            'activation_receipt': {'synthetic_unit_receipt': 'activation'}}
        for key, name in (('plan', 'plan.json'), ('freeze', 'complete-freeze.json'),
                ('preread', 'public-preread.json'), ('activation_receipt', 'activation-receipt.json')):
            write_json(scope/name, records[key])
        return code_root, own, records

    def test_report_scope_gate_passes_exact_material_evidence_and_scope_without_launch(self):
        scope = self.scope/'mocked-reviewed-material-gate'; scope.mkdir()
        code_root, own, records = self.material_scope_records(scope)
        fixture = types.SimpleNamespace(require_execution_ready=mock.Mock(return_value=True))
        before = sorted(str(path) for path in scope.rglob('*'))
        with mock.patch.object(finalization, '__file__', str(own)), \
                mock.patch.object(finalization, '_read_pinned_source', return_value=b'# checked source'), \
                mock.patch.object(finalization, '_verify_material_source_tree', return_value=3) as inventory, \
                mock.patch.object(finalization, '_source_module', return_value=fixture) as compiler:
            checked = finalization.check_final_report_material_scope(scope)
            fixture.require_execution_ready.assert_called_once_with(**records,
                repo=code_root, execution_scope=str(scope))
            compiler.assert_called_once_with(code_root/finalization.FIXTURE,
                finalization.BOOTSTRAP_SOURCE_PINS[finalization.FIXTURE], 'pinned_final_report_fixture')
            self.assertEqual(inventory.call_args_list, [mock.call(code_root, records['plan']['code_files']),
                mock.call(scope/'derived', records['plan'].get('derived_code'))])
        self.assertTrue(checked['material_scope_gate_rechecked_before_writer_identity'])
        self.assertFalse(checked['activation_only_runtime_used_by_final_writer'])
        self.assertEqual(before, sorted(str(path) for path in scope.rglob('*')))

    def tiny_material_tree(self):
        root = self.scope/'tiny-copied-material'; root.mkdir()
        pins = {}
        for name in ('scripts/helper.py', 'tests/test_helper.py', 'plain.js'):
            path = root/name; path.parent.mkdir(exist_ok=True)
            raw = ('# tiny copied source '+name+'\n').encode(); path.write_bytes(raw)
            pins[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return root, pins

    def test_exact_copied_source_inventory_checks_every_pin(self):
        root, pins = self.tiny_material_tree()
        self.assertEqual(finalization._verify_material_source_tree(root, pins), 3)
        (root/'scripts/helper.py').write_bytes(b'# same-length substituted source\n')
        with self.assertRaisesRegex(ValueError, 'size differs|differs from independent'):
            finalization._verify_material_source_tree(root, pins)

    def test_copied_source_inventory_rejects_extra_file_and_empty_directory(self):
        root, pins = self.tiny_material_tree()
        (root/'extra').mkdir()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            finalization._verify_material_source_tree(root, pins)
        (root/'extra').rmdir(); (root/'extra.py').write_bytes(b'# extra source\n')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            finalization._verify_material_source_tree(root, pins)

    def test_copied_source_inventory_rejects_missing_source(self):
        root, pins = self.tiny_material_tree(); (root/'plain.js').unlink()
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            finalization._verify_material_source_tree(root, pins)

    def test_copied_source_inventory_rejects_same_byte_hardlink(self):
        root, pins = self.tiny_material_tree()
        source = root/'plain.js'; duplicate = self.scope/'same-bytes-copy'
        duplicate.write_bytes(source.read_bytes()); source.unlink(); os.link(duplicate, source)
        with self.assertRaisesRegex(ValueError, 'alias or special file'):
            finalization._verify_material_source_tree(root, pins)

    def test_copied_source_inventory_rejects_source_and_ancestor_symlinks(self):
        root, pins = self.tiny_material_tree()
        source = root/'plain.js'; target = self.scope/'same-bytes-target'
        target.write_bytes(source.read_bytes()); source.unlink(); source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'alias or special file'):
            finalization._verify_material_source_tree(root, pins)
        alias = self.scope/'material-root-alias'; alias.symlink_to(root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink evidence ancestor'):
            finalization._verify_material_source_tree(alias, pins)

    def test_copied_source_pin_map_has_explicit_count_path_and_byte_bounds(self):
        root, pins = self.tiny_material_tree()
        invalid_maps = [
            {str(index)+'.py': pins['plain.js'] for index in range(finalization.MAX_MATERIAL_SOURCE_FILES+1)},
            {'../escape.py': pins['plain.js']},
            {'source.py': {'bytes': 2*finalization.MIB+1, 'sha256': 'a'*64}},
            {'x'*4097: pins['plain.js']},
            {'x'*256+'.py': pins['plain.js']},
            {'\u20ac'*86+'.py': pins['plain.js']},
            {'/'.join(['nested']*34)+'.py': pins['plain.js']}]
        for invalid in invalid_maps:
            with self.subTest(invalid_count=len(invalid)), self.assertRaises(ValueError):
                finalization._verify_material_source_tree(root, invalid)

    def test_copied_material_failure_precedes_fixture_compile_and_writer_identity(self):
        scope = self.scope/'copied-material-drift'; scope.mkdir()
        _, own, _ = self.material_scope_records(scope)
        with mock.patch.object(finalization, '__file__', str(own)), \
                mock.patch.object(finalization, '_read_pinned_source', return_value=b'# checked source'), \
                mock.patch.object(finalization, '_verify_material_source_tree', side_effect=ValueError('inventory differs')), \
                mock.patch.object(finalization, '_source_module') as compiler, \
                self.assertRaisesRegex(ValueError, 'inventory differs'):
            finalization.check_final_report_material_scope(scope)
        compiler.assert_not_called()
        self.assertFalse((scope/finalization.FINAL_WRITER_IDENTITY_NAME).exists())

    def test_report_scope_cannot_select_unverified_executable_fixture(self):
        scope = self.scope/'untrusted-material-validator'; scope.mkdir()
        _, _, records = self.material_scope_records(scope)
        records['plan']['code_files'][finalization.FIXTURE] = {
            'bytes': 13, 'sha256': hashlib.sha256(b'unchecked code').hexdigest()}
        write_json(scope/'plan.json', records['plan'])
        with mock.patch.object(finalization, '_source_module') as compiler, \
                self.assertRaisesRegex(ValueError, 'independent bootstrap pin'):
            finalization.check_final_report_material_scope(scope)
        compiler.assert_not_called()
        self.assertFalse((scope/finalization.FINAL_WRITER_IDENTITY_NAME).exists())

    def test_production_writer_cli_refuses_missing_activation_before_identity(self):
        scope = self.scope/'unadmitted-production-writer'; scope.mkdir()
        input_pin = write_json(scope/finalization.FINAL_INPUT_NAME,
            self.final_report_input(scope, tiny=False))
        argv = [self.python, '-I', '-S', '-B', str(Path(finalization.__file__).resolve()),
            '--persist-final-report', '--scope', str(scope), '--input-bytes', str(input_pin['bytes']),
            '--input-sha256', input_pin['sha256']]
        completed = subprocess.run(argv, env=finalization.ENVIRONMENT,
            capture_output=True, timeout=10, check=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, b'')
        self.assertEqual(set(path.name for path in scope.iterdir()), {finalization.FINAL_INPUT_NAME})

    def test_tiny_writer_refuses_real_qualification_extra_fields_or_full_input(self):
        for change in ({'complete_resource_measurement_join_qualified': True},
                {'arbitrary_workload': 'unadmitted'}, {'payload': 'x'*65536},
                {'schema': finalization.SCHEMA+'-final-report-input'}):
            with self.subTest(change=next(iter(change))), tempfile.TemporaryDirectory() as directory:
                scope = Path(directory); value = self.final_report_input(scope); value.update(change)
                input_pin = write_json(scope/finalization.FINAL_INPUT_NAME, value)
                with self.assertRaises(ValueError):
                    finalization.persist_tiny_final_report_probe(scope, expected_input_pin=input_pin)
                self.assertEqual(set(path.name for path in scope.iterdir()), {finalization.FINAL_INPUT_NAME})

    def test_tiny_writer_storage_bound_precedes_identity(self):
        scope = self.scope/'oversized-tiny-writer'; scope.mkdir()
        with (scope/'engineering-padding').open('wb') as stream:
            stream.truncate(finalization.TINY_REPORT_SCOPE_BYTES)
        input_pin = write_json(scope/finalization.FINAL_INPUT_NAME, self.final_report_input(scope))
        with self.assertRaisesRegex(ValueError, 'storage bound'):
            finalization.persist_tiny_final_report_probe(scope, expected_input_pin=input_pin)
        self.assertFalse((scope/finalization.FINAL_WRITER_IDENTITY_NAME).exists())
        self.assertFalse((scope/finalization.FINAL_NAME).exists())

    def synthetic_tiny_writer_join(self, scope):
        input_pin = write_json(scope/finalization.FINAL_INPUT_NAME, self.final_report_input(scope))
        _, report_pin = finalization.persist_tiny_final_report_probe(scope, expected_input_pin=input_pin)
        identity, _ = finalization.read_pinned_json(scope/finalization.FINAL_WRITER_IDENTITY_NAME)
        argv = [self.python, '-I', '-S', '-B', str(Path(finalization.__file__).resolve()),
            '--tiny-final-report-writer', '--scope', str(scope), '--input-bytes', str(input_pin['bytes']),
            '--input-sha256', input_pin['sha256']]
        observation = self.observation(argv, 2_100_000_000, 2_200_000_000,
            procfs_pid=identity['procfs_pid'], namespace_pid=identity['namespace_pid'])
        observation_pin = write_json(scope/finalization.FINAL_WRITER_OBSERVATION_NAME, observation)
        return {'expected_input_pin': input_pin, 'expected_report_pin': report_pin,
            'expected_writer_observation_pin': observation_pin, 'expected_writer_argv': argv}, observation

    def test_tiny_writer_lifetime_join_rechecks_storage_after_parent_metadata(self):
        scope = self.scope/'post-writer-storage'; scope.mkdir()
        options, _ = self.synthetic_tiny_writer_join(scope)
        with (scope/'unexpected-retained-growth').open('wb') as stream:
            stream.truncate(finalization.TINY_REPORT_SCOPE_BYTES)
        with self.assertRaisesRegex(ValueError, 'retained scope.*storage bound'):
            finalization.join_final_report_lifetime(scope, **options)

    def test_tiny_writer_lifetime_join_rechecks_report_bytes_and_observed_deadline(self):
        for failure in ('report-bytes', 'observed-deadline'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                scope = Path(directory); options, observation = self.synthetic_tiny_writer_join(scope)
                if failure == 'report-bytes':
                    report, _ = finalization.read_pinned_json(scope/finalization.FINAL_NAME)
                    report['unexpected-retained-growth'] = 'x'*65536
                    (scope/finalization.FINAL_NAME).chmod(0o600)
                    options['expected_report_pin'] = write_json(scope/finalization.FINAL_NAME, report)
                else:
                    observation['monotonic_end_ns'] = observation['monotonic_start_ns'] + 4_000_000_000
                    options['expected_writer_observation_pin'] = write_json(
                        scope/finalization.FINAL_WRITER_OBSERVATION_NAME, observation)
                with self.assertRaises(ValueError):
                    finalization.join_final_report_lifetime(scope, **options)

    def test_synthetic_writer_observation_cannot_certify_material_report(self):
        scope = self.scope/'synthetic-material-report'; scope.mkdir()
        value = self.final_report_input(scope, tiny=False, complete=True)
        input_pin = write_json(scope/finalization.FINAL_INPUT_NAME, value)
        report = {**value, 'schema': finalization.SCHEMA+'-persisted-final-report',
            'final_report_input_pin': input_pin, 'report_writer_fsync_completed_before_return': True,
            'report_writer_termination_observation_required': True, 'final_disposition_persisted': True,
            'report_writer_mode': 'ACTIVATION_BOUND_MATERIAL_SCOPE'}
        report_pin = write_json(scope/finalization.FINAL_NAME, report)
        write_json(scope/finalization.FINAL_WRITER_IDENTITY_NAME, {'procfs_pid': 555, 'namespace_pid': 5})
        argv = [self.python, '-I', '-S', '-B', str(Path(finalization.__file__).resolve()),
            '--persist-final-report', '--scope', str(scope), '--input-bytes', str(input_pin['bytes']),
            '--input-sha256', input_pin['sha256']]
        observation = self.observation(argv, 2_100_000_000, 2_200_000_000, procfs_pid=555, namespace_pid=5)
        observation_pin = write_json(scope/finalization.FINAL_WRITER_OBSERVATION_NAME, observation)
        with self.assertRaisesRegex(ValueError, 'Synthetic writer observations'):
            finalization.join_final_report_lifetime(scope, expected_input_pin=input_pin,
                expected_report_pin=report_pin, expected_writer_observation_pin=observation_pin,
                expected_writer_argv=argv)

    def test_subreaper_direct_receipt_does_not_imply_full_descendant_wait_chain(self):
        self.driver.pop('synthetic_test_fixture')
        self.runner.pop('synthetic_test_fixture')
        self.driver_pin = write_json(self.scope/finalization.DRIVER_OBSERVATION_NAME, self.driver)
        # The runner's changed byte pin and base inventory must be captured by a
        # new explicitly synthetic snapshot; no actual worker is relaunched.
        write_json(self.scope/finalization.RUNNER_OBSERVATION_NAME, self.runner)
        with mock.patch.object(finalization.time, 'monotonic_ns', return_value=1_600_000_000):
            self.pending = finalization.capture_pending_measurements(self.scope,
                admission_start_monotonic_ns=self.start, expected_runner_argv=self.runner_argv)
        self.pending_pin = write_json(self.scope/finalization.PENDING_NAME, self.pending)
        result = self.join()
        self.assertEqual(result['status'], 'PENDING_FINAL_MEASUREMENT_JOIN')
        self.assertTrue(result['all_original_resource_bounds_checked'])
        self.assertFalse(result['complete_descendant_wait_chain_verified'])

    def test_bool_ordinal_and_scientific_authority_are_rejected(self):
        worker = copy.deepcopy(self.worker); worker['cases'][0]['ordinal'] = False
        with self.assertRaisesRegex(ValueError, 'ordinal'): finalization._worker_cases(worker)
        worker = copy.deepcopy(self.worker); worker['scientific_execution_authorized'] = True
        with self.assertRaisesRegex(ValueError, 'authority'): finalization._worker_cases(worker)

    def test_original_calls_and_time_boundaries_are_inclusive(self):
        worker = copy.deepcopy(self.worker)
        for row in worker['cases']:
            row.update({'calls': 64, 'request_bytes': 48*finalization.MIB,
                'response_bytes': 64*finalization.MIB})
        cases, totals = finalization._worker_cases(worker)
        self.assertEqual(totals['calls'], 512)
        measured = finalization.allocate_elapsed(cases, 4800)
        self.assertAlmostEqual(sum(row['complete_case_seconds'] for row in measured['cases']), 4800)
        with self.assertRaisesRegex(ValueError, '600-second'):
            finalization.allocate_elapsed(cases, 4800.0001)
        worker['cases'][7]['calls'] += 1
        with self.assertRaisesRegex(ValueError, 'per-case'): finalization._worker_cases(worker)

    def test_original_storage_boundary_and_extra_allocated_block(self):
        rows = [{'path': '.', 'kind': 'directory', 'bytes': 0, 'allocated_bytes': 0}]
        for ordinal in range(8):
            rows.extend([{'path': f'cases/case{ordinal:02d}', 'kind': 'directory', 'bytes': 0, 'allocated_bytes': 0},
                {'path': f'cases/case{ordinal:02d}/synthetic.bin', 'kind': 'file',
                    'bytes': finalization.LIMITS['case_storage_bytes'],
                    'allocated_bytes': finalization.LIMITS['case_storage_bytes']}])
        inventory = {'rows': rows, 'logical_bytes': finalization.LIMITS['run_storage_bytes'],
            'allocated_bytes': finalization.LIMITS['run_storage_bytes']}
        result = finalization.allocate_storage(inventory, reserved_bytes=0, directory_reserved_bytes=0)
        self.assertEqual(result['whole_allocated_bytes_with_remaining_reservation'], 1536*finalization.MIB)
        inventory['rows'][0]['allocated_bytes'] = 8
        inventory['allocated_bytes'] += 8
        with self.assertRaisesRegex(ValueError, '192MiB'):
            finalization.allocate_storage(inventory, reserved_bytes=0, directory_reserved_bytes=0)

    def test_symlink_hardlink_and_fifo_storage_entries_rejected(self):
        path = self.scope/'untrusted'
        path.symlink_to(self.scope/'worker-result.json')
        with self.assertRaisesRegex(ValueError, 'sole-link'): finalization.storage_inventory(self.scope)
        path.unlink(); os.link(self.scope/'worker-result.json', path)
        with self.assertRaisesRegex(ValueError, 'sole-link'): finalization.storage_inventory(self.scope)
        path.unlink(); os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'sole-link'): finalization.storage_inventory(self.scope)

    def test_closed_driver_guard_precedes_identity_write_and_child_launch(self):
        fixture = types.SimpleNamespace(require_execution_ready=mock.Mock(side_effect=RuntimeError('BLOCKED_PREPARATION_REVIEW')),
            identity=mock.Mock(), observe_process=mock.Mock(), write=mock.Mock())
        checked = {'worker_scope': str(self.scope), 'activation_evidence': {}}
        with mock.patch.object(finalization, 'check_admitted_measurement_driver', return_value=(checked, fixture)):
            with self.assertRaisesRegex(RuntimeError, 'BLOCKED'):
                finalization.run_admitted_measurement_driver(self.scope/'closed-bundle.json', self.scope,
                    expected_bundle_sha256='a'*64, admission_start_monotonic_ns=self.start)
        fixture.identity.assert_not_called(); fixture.observe_process.assert_not_called(); fixture.write.assert_not_called()

    def test_fixed_cli_never_accepts_arbitrary_launch_argv(self):
        with mock.patch.object(sys, 'argv', ['fixed-driver', '--launch', '/bin/sh']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure: finalization.main()
        self.assertEqual(failure.exception.code, 2)

    def test_duplicate_json_properties_rejected_before_join(self):
        path = self.scope/'duplicate.json'
        path.write_bytes(b'{"status":"pending","status":"pass"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            finalization.read_pinned_json(path)

    def test_independently_captured_completion_binds_pending_pin_and_dynamic_deadline(self):
        completion = {'schema': finalization.SCHEMA+'-driver-completion', 'scope': str(self.scope),
            'admission_bundle_sha256': 'a'*64, 'pending_pin': self.pending_pin,
            'runner_argv': self.runner_argv+['--seconds', '4799.25']}
        value = finalization.parse_driver_completion(finalization.canonical(completion)+b'\n',
            scope=self.scope, expected_bundle_sha256='a'*64,
            expected_runner_argv_prefix=self.runner_argv)
        self.assertEqual(value['pending_pin'], self.pending_pin)
        self.assertEqual(value['runner_argv'][-1], '4799.25')
        completion['runner_argv'][1] = '-c'
        with self.assertRaisesRegex(ValueError, 'parent prefix'):
            finalization.parse_driver_completion(finalization.canonical(completion)+b'\n',
                scope=self.scope, expected_bundle_sha256='a'*64,
                expected_runner_argv_prefix=self.runner_argv)

    def test_completion_rejects_extra_output_and_enlarged_remaining_deadline(self):
        completion = {'schema': finalization.SCHEMA+'-driver-completion', 'scope': str(self.scope),
            'admission_bundle_sha256': 'a'*64, 'pending_pin': self.pending_pin,
            'runner_argv': self.runner_argv+['--seconds', '4800.1']}
        raw = finalization.canonical(completion)+b'\n'
        with self.assertRaisesRegex(ValueError, 'original scope'):
            finalization.parse_driver_completion(raw, scope=self.scope,
                expected_bundle_sha256='a'*64, expected_runner_argv_prefix=self.runner_argv)
        with self.assertRaisesRegex(ValueError, 'one bounded'):
            finalization.parse_driver_completion(raw+raw, scope=self.scope,
                expected_bundle_sha256='a'*64, expected_runner_argv_prefix=self.runner_argv)

    def test_actual_tiny_fixture_observation_has_the_exact_join_fields(self):
        import radio_native_v2_compact_eight_case_resource_fixture as fixture
        scope = self.scope/'independent-tiny-observer'
        scope.mkdir()
        identity_path = scope/'tiny-identity.json'
        code = ('import os,json,sys,time; '
            'f=open(sys.argv[1],"x"); '
            'json.dump({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()},f); '
            'f.close(); time.sleep(0.02)')
        argv = [self.python, '-I', '-S', '-B', '-c', code, str(identity_path)]
        observed, stdout, stderr = fixture.observe_process(argv, scope, 'tiny-finalization-observer',
            identity_path, deadline=time.monotonic()+5, pipe_output=True)
        identity, _ = finalization.read_pinned_json(identity_path)
        start, end, peak = finalization._observation(observed, argv, expected_identity=identity)
        self.assertLess(start, end)
        self.assertGreater(peak, 0)
        self.assertIn('observer_self_kernel_peak_rss_bytes', observed)
        self.assertEqual(stdout, b''); self.assertEqual(stderr, b'')
        self.assertFalse(observed['complete_descendant_wait_chain_verified'])

    def test_original_driver_interpreter_alias_rejected_before_identity_or_launch(self):
        fixture = types.SimpleNamespace(require_execution_ready=mock.Mock(),
            identity=mock.Mock(), observe_process=mock.Mock(), write=mock.Mock())
        checked = {'worker_scope': str(self.scope), 'argv': [self.python],
            'bundle_path': str(self.scope/'admission.json'), 'activation_evidence': {}}
        with mock.patch.object(finalization, 'check_admitted_measurement_driver', return_value=(checked, fixture)), \
                mock.patch.object(sys, 'orig_argv', [self.python, '-I', '-B', 'alias-driver']):
            with self.assertRaisesRegex(RuntimeError, 'original.*argv'):
                finalization.run_admitted_measurement_driver(self.scope/'admission.json', self.scope,
                    expected_bundle_sha256='a'*64, admission_start_monotonic_ns=self.start)
        fixture.identity.assert_not_called(); fixture.observe_process.assert_not_called(); fixture.write.assert_not_called()

    def test_growing_source_read_is_bounded_before_drift_rejection(self):
        source = self.scope/'bounded-source.py'
        source.write_bytes(b'value=1\n')
        pin = {'bytes': 8, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        with mock.patch.object(finalization.os, 'read', side_effect=lambda fd, count: b'x'*count) as read:
            with self.assertRaisesRegex(ValueError, 'bootstrap pin'):
                finalization._source_module(source, pin, 'tiny_growth_negative')
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read.call_args.args[1], 9)

    def test_optional_material_worker_rss_fields_have_an_exact_inclusive_cap(self):
        key = 'maximum_individual_material_process_rss_bytes'
        worker = copy.deepcopy(self.worker)
        worker[key] = finalization.LIMITS['rss_bytes']
        for row in worker['cases']: row[key] = finalization.LIMITS['rss_bytes']
        self.assertEqual(finalization._worker_material_peak(worker),
            (finalization.LIMITS['rss_bytes'], True))
        write_json(self.scope/'worker-result.json', worker)
        with mock.patch.object(finalization.time, 'monotonic_ns', return_value=1_600_000_000):
            pending = finalization.capture_pending_measurements(self.scope,
                admission_start_monotonic_ns=self.start, expected_runner_argv=self.runner_argv)
        self.assertEqual(pending['maximum_individual_process_rss_bytes_before_driver_termination'], 512*finalization.MIB)
        self.assertTrue(pending['complete_material_worker_and_case_rss_fields_present'])
        self.pending_pin = write_json(self.scope/finalization.PENDING_NAME, pending)
        joined = self.join()
        self.assertEqual(joined['maximum_individual_process_rss_bytes'], 512*finalization.MIB)
        self.assertTrue(joined['complete_material_worker_and_case_rss_fields_present'])
        worker['cases'][7][key] += 1
        with self.assertRaisesRegex(ValueError, '512MiB'): finalization._worker_cases(worker)
        worker['cases'][7][key] = False
        with self.assertRaisesRegex(ValueError, 'integer'): finalization._worker_cases(worker)

    def test_legacy_missing_material_rss_fields_remain_unqualified(self):
        result = self.join()
        self.assertFalse(result['complete_material_worker_and_case_rss_fields_present'])
        self.assertFalse(result['complete_resource_measurement_join_qualified'])
        self.assertTrue(any('RSS fields' in reason for reason in result['pending_reasons']))

    def test_descendant_completion_label_requires_exact_escape_guard_contract(self):
        receipt = copy.deepcopy(self.subreaper)
        receipt['complete_descendant_wait_chain_verified'] = True
        with self.assertRaisesRegex(ValueError, 'escape guard'):
            finalization._subreaper_terminal(receipt)
        receipt.update({'descendant_wait_chain_scope':
                'INHERITED_SECCOMP_GUARD_AND_LINUX_SUBREAPER_TO_ECHILD',
            'child_escape_guard_installed_before_exec': True,
            'child_escape_guard_no_new_privileges': True,
            'child_escape_guard_seccomp_filter': True,
            'child_escape_guard_denied_operations': list(finalization._ESCAPE_OPERATIONS)})
        self.assertTrue(finalization._subreaper_terminal(receipt))
        receipt['child_escape_guard_denied_operations'] = receipt['child_escape_guard_denied_operations'][:-1]
        with self.assertRaisesRegex(ValueError, 'escape guard'):
            finalization._subreaper_terminal(receipt)


if __name__ == '__main__': unittest.main()
