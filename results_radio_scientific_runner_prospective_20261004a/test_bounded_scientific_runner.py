import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCIENCE = REPO / 'results_radio_scientific_execution_prospective_20261003a'
RETENTION = REPO / 'results_radio_native_v3_execution_preparation_20261003f'
sys.path[:0] = [str(HERE), str(SCIENCE), str(RETENTION)]

import scientific_store
import scientific_admission
from failure_output_retention import RetentionError, reconstruct_raw
from bounded_scientific_runner import (RESULT_SCHEMA, RunnerError, canonical,
                                       dispatch_once)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_pin(path, identity):
    path = Path(path).resolve()
    raw = path.read_bytes()
    mode = stat.S_IMODE(path.stat().st_mode)
    return {'closure_identity': identity, 'path': str(path),
            'mode': '100755' if mode == 0o755 else '100644',
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class Clock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='radio-runner-test-')
        self.python = str(Path(sys.executable).resolve())
        self.retention = str((RETENTION / 'failure_output_retention.py').resolve())
        self.receiver = str((SCIENCE / 'receiver_telescope_adapter.py').resolve())
        self.dispatch = '1' * 64
        self.session = canonical({'started_epoch_milliseconds': 1000,
                                  'deadline_epoch_milliseconds': 9000})
        self.session_pin = pin(self.session)
        self.files = [file_pin(self.python, 'python'), file_pin(self.retention, 'retention'),
                      file_pin(self.receiver, 'receiver')]
        inventory = {}
        for row in self.files:
            inventory[row['closure_identity']] = {
                'role': 'runtime' if row['closure_identity'] == 'python' else 'code',
                'location': 'runtime', 'path': row['path'], 'mode': row['mode'],
                'bytes': row['bytes'], 'sha256': row['sha256']}
        self.execution_manifest = canonical({'inventory': inventory})
        self.execution_manifest_pin = pin(self.execution_manifest)
        closure_doc = {'evidence_domain': 'synthetic-test-fixture',
                       'document_sha256s': {
                           'executable_freeze': self.execution_manifest_pin['sha256']}}
        closure_raw = scientific_admission.canonical(closure_doc)
        self.closure = scientific_admission.VerifiedClosure(
            closure_raw, _permit=scientific_admission._VERIFICATION_TOKEN)
        admission_doc = {'domain': 'synthetic-test-fixture', 'status': 'PENDING',
                         'scientific_execution_authorized': False,
                         'closure_sha256': hashlib.sha256(closure_raw).hexdigest(),
                         'validated_current_epoch_milliseconds': 2000,
                         'session_deadline_epoch_milliseconds': 9000,
                         'stop_epoch_milliseconds': 10000}
        admission_raw = canonical(admission_doc)
        self.admission = scientific_store.VerifiedAdmission(
            admission_raw, _token=scientific_store._ADMISSION_TOKEN)
        self.admission_sha = hashlib.sha256(admission_raw).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def envelope(self, **changes):
        value = {'schema': RESULT_SCHEMA, 'evidence_domain': 'synthetic-test-fixture',
                 'status': 'SYNTHETIC_INTERFACE_QUALIFIED',
                 'dispatch_identity': self.dispatch,
                 'admission_sha256': self.admission_sha,
                 'session_proof_sha256': self.session_pin['sha256'],
                 'receiver_adapter_sha256': self.files[2]['sha256'],
                 'live_clock_record': {
                     'checked_before_and_after_every_loader_attempt': True,
                     'nondecreasing_integer_observations': [
                         {'scan': 'fixture', 'phase': 'before', 'epoch_milliseconds': 3000},
                         {'scan': 'fixture', 'phase': 'after', 'epoch_milliseconds': 3001}]},
                 'telescope_values_opened': False,
                 'scientific_execution_authorized': False, 'automatic_retry': False}
        value.update(changes)
        return value

    def spec(self, code, **changes):
        value = {'schema': 'radio-bounded-scientific-runner-v1',
                 'evidence_domain': 'synthetic-test-fixture',
                 'dispatch_identity': self.dispatch,
                 'argv': [self.python, '-c', code],
                 'environment': {'PYTHONIOENCODING': 'utf-8'},
                 'worker_files': self.files,
                 'admission_sha256': self.admission_sha,
                 'session_proof_sha256': self.session_pin['sha256'],
                 'failure_retention_sha256': self.files[1]['sha256'],
                 'receiver_adapter_sha256': self.files[2]['sha256'],
                 'timeout_seconds': 1, 'stdout_cap_bytes': 65536,
                 'stderr_cap_bytes': 65536, 'scientific_execution_authorized': False}
        value.update(changes)
        raw = canonical(value)
        return raw, pin(raw)

    def run_spec(self, raw, raw_pin, name='evidence', clock=(2500, 2600)):
        return dispatch_once(raw, raw_pin, verified_admission=self.admission,
            verified_closure=self.closure, raw_execution_manifest=self.execution_manifest,
            expected_execution_manifest_pin=self.execution_manifest_pin,
            raw_session_proof=self.session, expected_session_proof_pin=self.session_pin,
            live_clock=Clock(clock), destination=str(Path(self.tmp.name) / name),
            repository_root=str(REPO))

    def success_code(self, envelope=None):
        raw = canonical(self.envelope() if envelope is None else envelope)
        return 'import sys;sys.stdout.buffer.write('+repr(raw)+')'

    def test_synthetic_success_is_qualified_but_blocked(self):
        raw, raw_pin = self.spec(self.success_code())
        result = self.run_spec(raw, raw_pin)
        record = result.record()
        self.assertEqual(record['status'], 'QUALIFIED')
        self.assertFalse(record['scientific_execution_authorized'])
        self.assertFalse(record['telescope_values_opened'])
        self.assertEqual(record['outer_clock']['nondecreasing_integer_observations'], [
            {'epoch_milliseconds': 2500, 'phase': 'before'},
            {'epoch_milliseconds': 2600, 'phase': 'after'}])

    def test_real_closure_refuses_worker_outside_its_executable_freeze(self):
        from test_scientific_admission import make_fixture
        from test_scientific_store import current_admission_fixture
        packet = make_fixture().seal()
        closure = scientific_admission.validate_scientific_closure(**packet)
        args = current_admission_fixture(closure, packet['expected_basis'])
        admission = scientific_store.validate_current_admission(**args)
        admission_sha = hashlib.sha256(admission.payload).hexdigest()
        session_raw = args['raw_session_proof']
        session_pin = args['expected_session_proof_pin']
        envelope = self.envelope(admission_sha256=admission_sha,
                                 session_proof_sha256=session_pin['sha256'])
        raw, raw_pin = self.spec(self.success_code(envelope), admission_sha256=admission_sha,
                                 session_proof_sha256=session_pin['sha256'])
        with self.assertRaisesRegex(RunnerError, 'worker closure identity|worker file differs'):
            dispatch_once(raw, raw_pin, verified_admission=admission,
                verified_closure=closure,
                raw_execution_manifest=packet['raw_documents']['executable_freeze'],
                expected_execution_manifest_pin=packet['expected_raw_pins']['executable_freeze'],
                raw_session_proof=session_raw, expected_session_proof_pin=session_pin,
                live_clock=Clock((2500, 2600)), destination=str(Path(self.tmp.name) / 'maintained'),
                repository_root=str(REPO))

    def test_nonzero_stderr_is_retained_and_closed(self):
        raw, raw_pin = self.spec("import sys;sys.stderr.buffer.write(b'root-cause\\x00bytes');sys.exit(7)")
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        capture = json.loads(result.capture_payload)
        self.assertEqual(capture['process_status'], 'EXIT_NONZERO')
        self.assertEqual(capture['returncode'], 7)
        self.assertEqual(reconstruct_raw(capture['streams']['stderr']['reconstruction']),
                         b'root-cause\x00bytes')

    def test_timeout_is_terminal_and_retained(self):
        raw, raw_pin = self.spec("import time,sys;sys.stderr.write('started');sys.stderr.flush();time.sleep(5)",
                                 timeout_seconds=0.05)
        result = self.run_spec(raw, raw_pin)
        record = result.record(); capture = json.loads(result.capture_payload)
        self.assertEqual(record['status'], 'CLOSED_FAILED')
        self.assertEqual(capture['process_status'], 'TIMEOUT')
        self.assertTrue(capture['timed_out'])
        self.assertEqual(reconstruct_raw(capture['streams']['stderr']['reconstruction']), b'started')

    def test_output_limit_is_terminal(self):
        raw, raw_pin = self.spec("import sys;sys.stdout.buffer.write(b'x'*10000)",
                                 stdout_cap_bytes=64)
        result = self.run_spec(raw, raw_pin)
        capture = json.loads(result.capture_payload)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertEqual(capture['process_status'], 'OUTPUT_LIMIT')
        self.assertEqual(len(reconstruct_raw(capture['streams']['stdout']['reconstruction'])), 64)

    def test_malformed_zero_exit_is_closed(self):
        raw, raw_pin = self.spec("print('not-json')")
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertIn('invalid child result JSON', result.record()['child_result_error'])

    def test_duplicate_json_key_is_closed(self):
        raw, raw_pin = self.spec("print('{\"schema\":1,\"schema\":2}')")
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_synthetic_telescope_claim_is_closed(self):
        envelope = self.envelope(telescope_values_opened=True)
        raw, raw_pin = self.spec(self.success_code(envelope))
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_synthetic_authority_claim_is_closed(self):
        envelope = self.envelope(scientific_execution_authorized=True)
        raw, raw_pin = self.spec(self.success_code(envelope))
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_missing_per_load_clock_is_closed(self):
        envelope = self.envelope(live_clock_record={})
        raw, raw_pin = self.spec(self.success_code(envelope))
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_expired_post_clock_closes_zero_exit(self):
        raw, raw_pin = self.spec(self.success_code())
        result = self.run_spec(raw, raw_pin, clock=(2500, 9000))
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertIn('expired', result.record()['post_dispatch_clock_error'])

    def test_regressed_post_clock_closes_zero_exit(self):
        raw, raw_pin = self.spec(self.success_code())
        result = self.run_spec(raw, raw_pin, clock=(2500, 2400))
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertIn('regressed', result.record()['post_dispatch_clock_error'])

    def test_timeout_cannot_exceed_session_remainder(self):
        raw, raw_pin = self.spec(self.success_code(), timeout_seconds=2)
        with self.assertRaisesRegex(RunnerError, 'exceeds'):
            self.run_spec(raw, raw_pin, clock=(8000,))

    def test_destination_cannot_be_reused(self):
        raw, raw_pin = self.spec(self.success_code())
        self.run_spec(raw, raw_pin, name='single')
        with self.assertRaises(RetentionError):
            self.run_spec(raw, raw_pin, name='single')

    def test_admission_hash_mismatch_is_rejected_before_launch(self):
        raw, raw_pin = self.spec(self.success_code(), admission_sha256='2'*64)
        with self.assertRaisesRegex(RunnerError, 'admission'):
            self.run_spec(raw, raw_pin)
        self.assertFalse((Path(self.tmp.name) / 'evidence').exists())

    def test_session_hash_mismatch_is_rejected_before_launch(self):
        raw, raw_pin = self.spec(self.success_code(), session_proof_sha256='2'*64)
        with self.assertRaisesRegex(RunnerError, 'session'):
            self.run_spec(raw, raw_pin)

    def test_retention_implementation_must_be_in_inventory(self):
        raw, raw_pin = self.spec(self.success_code(), failure_retention_sha256='2'*64)
        with self.assertRaisesRegex(RunnerError, 'must occur'):
            self.run_spec(raw, raw_pin)

    def test_receiver_adapter_must_be_in_inventory(self):
        raw, raw_pin = self.spec(self.success_code(), receiver_adapter_sha256='2'*64)
        with self.assertRaisesRegex(RunnerError, 'must occur'):
            self.run_spec(raw, raw_pin)

    def test_launcher_must_be_in_inventory(self):
        raw, raw_pin = self.spec(self.success_code(), worker_files=self.files[1:])
        with self.assertRaisesRegex(RunnerError, 'must occur'):
            self.run_spec(raw, raw_pin)

    def test_environment_is_not_implicitly_inherited(self):
        os.environ['RADIO_RUNNER_FORBIDDEN_PARENT_VALUE'] = 'secret'
        envelope = self.envelope()
        result_raw = canonical(envelope)
        code = ("import os,sys;sys.exit(9) if 'RADIO_RUNNER_FORBIDDEN_PARENT_VALUE' in os.environ "
                "else sys.stdout.buffer.write("+repr(result_raw)+")")
        raw, raw_pin = self.spec(code)
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'QUALIFIED')
        del os.environ['RADIO_RUNNER_FORBIDDEN_PARENT_VALUE']

    def test_noncanonical_child_json_is_closed(self):
        envelope = self.envelope()
        raw_child = json.dumps(envelope, indent=2).encode()+b'\n'
        raw, raw_pin = self.spec('import sys;sys.stdout.buffer.write('+repr(raw_child)+')')
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_wrong_dispatch_binding_is_closed(self):
        raw, raw_pin = self.spec(self.success_code(self.envelope(dispatch_identity='3'*64)))
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_wrong_receiver_binding_is_closed(self):
        raw, raw_pin = self.spec(self.success_code(self.envelope(receiver_adapter_sha256='3'*64)))
        result = self.run_spec(raw, raw_pin)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')

    def test_public_spec_refuses_pending_synthetic_admission(self):
        raw, raw_pin = self.spec(self.success_code(), evidence_domain='public-scientific-evidence',
                                 scientific_execution_authorized=True)
        with self.assertRaisesRegex(RunnerError, 'domain'):
            self.run_spec(raw, raw_pin)

    def test_duplicate_worker_path_rejected(self):
        raw, raw_pin = self.spec(self.success_code(), worker_files=self.files+[self.files[0]])
        with self.assertRaisesRegex(RunnerError, 'distinct'):
            self.run_spec(raw, raw_pin)


if __name__ == '__main__':
    unittest.main()
