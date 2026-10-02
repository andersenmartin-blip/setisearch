"""Tiny process and synthetic receipt tests; no full source/native/science run."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
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
        checked = {'worker_scope': str(self.scope)}
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
            'bundle_path': str(self.scope/'admission.json')}
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
