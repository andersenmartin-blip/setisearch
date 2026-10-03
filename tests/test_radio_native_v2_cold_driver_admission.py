"""Cold fixture/admission integration, with every runtime launch forbidden.

The producer is the actual run_control preparation path. Its resulting bundle
is read by the actual worker admission validator at the measurement-driver
launch boundary. Only synthetic temporary evidence is supplied; activation,
historical observation, spending and storage qualification are stubbed. This
does not invoke a control, start a child, generate source or establish authority.
"""
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_resource_finalization as finalization
import radio_native_v2_worker_admission as admission
from test_radio_native_v2_worker_admission import synthetic_worker_materials


class AdmissionBoundaryReached(Exception):
    """Stop after the read-only admission check, before any child launch."""


class ColdDriverAdmissionTests(unittest.TestCase):
    def exercise_cold_preparation(self, *, mutate=None, driver_bootstrap=False,
                                  repeat_with_metadata=False):
        temporary = tempfile.TemporaryDirectory(prefix='seti-cold-admission-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        templates = fixture.templates((fixture.REPO / fixture.CODE_FILES[0]).read_text())
        material = synthetic_worker_materials(root, derived_sources=templates)
        scope = material['scope']
        # The reused metadata builder seeds a disposable example case. Remove
        # only that synthetic scaffolding so the real producer gets fresh scope.
        shutil.rmtree(scope)
        self.assertFalse(scope.exists())
        receipts = []
        boundaries = []

        def at_driver_boundary(argv, observed_scope, label, identity_path, **kwargs):
            self.assertEqual(label, 'measurement-driver')
            self.assertEqual(Path(observed_scope), scope)
            self.assertIn('--admitted-whole-control-driver', argv)
            self.assertEqual(Path(identity_path), scope / 'measurement-driver-identity.json')
            self.assertFalse(Path(identity_path).exists())
            cases = scope / 'cases'
            self.assertEqual(sorted(path.name for path in cases.iterdir()),
                             [f'case{index:02d}' for index in range(8)])
            self.assertTrue(all(path.is_dir() and not list(path.iterdir())
                                for path in cases.iterdir()))
            boundaries.append(list(argv))
            if mutate is not None:
                mutate(scope)
            bundle_path = argv[argv.index('--admission-bundle') + 1]
            digest = argv[argv.index('--bundle-sha256') + 1]
            bundle = admission.load_bundle(bundle_path, expected_bundle_sha256=digest)
            worker_argv = admission.expected_worker_argv(bundle, bundle_path,
                role='control', ordinal=None, expected_bundle_sha256=digest)
            def check():
                if driver_bootstrap:
                    checked, frozen_fixture = finalization.check_admitted_measurement_driver(
                        bundle_path, expected_bundle_sha256=digest)
                    self.assertEqual(checked['worker_scope'], str(scope))
                    self.assertEqual(checked['receipt_scope'], str(scope / 'whole-control-supervisor'))
                    self.assertEqual(checked['argv'], worker_argv)
                    self.assertEqual(Path(frozen_fixture.__file__),
                                     scope / 'frozen-code' / fixture.SELF)
                    return checked['structural_admission']
                return admission.validate_worker_admission(bundle_path,
                    role='control', ordinal=None, argv=worker_argv,
                    environment=dict(admission.CHILD_ENVIRONMENT),
                    expected_bundle_sha256=digest)

            receipts.append(check())
            if repeat_with_metadata:
                # Model the identities and observer files added outside cases
                # between driver, supervisor and final worker entry checks.
                # They are tiny labelled synthetic metadata, never real process
                # evidence. All four checks use the same exact pinned bundle.
                (scope / 'measurement-driver-identity.json').write_bytes(
                    b'{"synthetic_test_fixture":true}\n')
                receipts.append(check())
                supervisor = scope / 'whole-control-supervisor'
                supervisor.mkdir(mode=0o700)
                (supervisor / 'supervisor-identity.json').write_bytes(
                    b'{"synthetic_test_fixture":true}\n')
                receipts.append(check())
                for name in ('measurement-driver-stdout.log', 'measurement-driver-stderr.log',
                             'whole-control-supervisor-stdout.log', 'whole-control-supervisor-stderr.log'):
                    (scope / name).write_bytes(b'')
                receipts.append(check())
                self.assertEqual(len(receipts), 4)
            receipt = receipts[-1]
            self.assertTrue(receipt['role_identity_metadata_checked'])
            self.assertTrue(receipt['current_materialized_code_and_derived_pins_checked'])
            self.assertTrue(receipt['fresh_role_output_names_absent'])
            for key in ('execution_authorized', 'scientific_execution_authorized',
                        'large_source_generation_admitted', 'pipeline_integration_qualified',
                        'publication_claim_independently_verified',
                        'complete_expected_runtime_closure_verified'):
                self.assertIs(receipt[key], False)
            for key in ('native_case_executions', 'scientific_cases_run',
                        'rng_draws', 'telescope_reads', 'actual_git_processes'):
                self.assertEqual(receipt[key], 0)
            raise AdmissionBoundaryReached('Read-only cold control admission reached; no child launched')

        with ExitStack() as stack:
            root_check = stack.enter_context(mock.patch.object(fixture,
                'authenticated_repository_root', return_value=str(root)))
            stack.enter_context(mock.patch.object(fixture, '_checked_activation_receipt'))
            stack.enter_context(mock.patch.object(fixture, 'validate_activation'))
            stack.enter_context(mock.patch.object(fixture, 'require_execution_ready'))
            stack.enter_context(mock.patch.object(fixture, 'historical_observation_module',
                return_value={'observe_historical_storage': mock.Mock()}))
            consume = mock.Mock(return_value=material['invocation_spending'])
            stack.enter_context(mock.patch.object(fixture, 'invocation_spending_module',
                return_value={'consume_once': consume}))
            stack.enter_context(mock.patch.object(fixture, 'check_storage'))
            observe = stack.enter_context(mock.patch.object(fixture, 'observe_process',
                side_effect=at_driver_boundary))
            children = stack.enter_context(mock.patch.object(subprocess, 'Popen',
                side_effect=AssertionError('No subprocess is permitted in cold admission regression')))
            try:
                fixture.run_control(scope, material['plan'], material['proof'], material['freeze'],
                    material['activation_receipt'], templates['lossless-helper.js'])
            finally:
                root_check.assert_called_once()
                consume.assert_called_once()
                observe.assert_called_once()
                children.assert_not_called()
                self.assertEqual(len(boundaries), 1)
                self.assertEqual((scope / 'measurement-driver-identity.json').exists(),
                                 repeat_with_metadata and bool(receipts))
                self.assertFalse(any(scope.rglob('deterministic-source.bin')))
        return receipts

    def test_actual_cold_preparation_reaches_read_only_control_admission(self):
        with self.assertRaisesRegex(AdmissionBoundaryReached, 'no child launched'):
            self.exercise_cold_preparation()

    def test_populated_case_is_refused_at_the_same_cold_boundary(self):
        def populate(scope):
            (scope / 'cases' / 'case07' / 'previous-work.json').write_bytes(b'{}\n')

        with self.assertRaises(ValueError):
            self.exercise_cold_preparation(mutate=populate)

    def test_real_driver_bootstrap_accepts_actual_cold_preparation(self):
        with self.assertRaisesRegex(AdmissionBoundaryReached, 'no child launched'):
            self.exercise_cold_preparation(driver_bootstrap=True)

    def test_driver_bootstrap_rechecks_with_observer_metadata_outside_cases(self):
        with self.assertRaisesRegex(AdmissionBoundaryReached, 'no child launched'):
            self.exercise_cold_preparation(driver_bootstrap=True, repeat_with_metadata=True)


if __name__ == '__main__':
    unittest.main()
