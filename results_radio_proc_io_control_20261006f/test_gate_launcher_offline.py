"""Pure F validator and fake-launcher regressions; no real child or native import."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


gate = load('f_gate_offline', 'runtime_gate.py')
launcher = load('f_launcher_offline', 'launch_scope.py')
AUTHORITY = {k: False for k in ('scientific_execution_authorized', 'spectral_access_authorized',
    'runtime_qualified', 'source_closure_qualified', 'native_custody_qualified',
    'cas_qualified', 'certificate_issued')}
PYTHON = '/inert/python3.12'
DIGEST = 'a' * 64


def control_fixture():
    io_before = dict(rchar=1000, wchar=0, syscr=10, syscw=0, read_bytes=0,
                     write_bytes=0, cancelled_write_bytes=0)
    io_after = dict(io_before, rchar=1049576, syscr=42)
    terminal_io = dict(io_after, rchar=1049800, wchar=4096, syscw=2)
    metadata = dict(schema='radio-proc-io-control-leaf-v1', status='DETERMINISTIC_READ_CONTROL_COMPLETED',
        authority=dict(AUTHORITY), pid=6, executable=PYTHON, isolated=True, no_site=True,
        dont_write_bytecode=True, installed_python_launched=False, scientific_modules_imported=False,
        workload_explicit_read_bytes=1048576, passes=8, payload_bytes=131072,
        payload_sha256=DIGEST, pass_sha256=[DIGEST] * 8,
        own_io_before={'values': io_before}, own_io_after={'values': io_after})
    snapshot = dict(local_wait_pid=6, outer_proc_pid=1001, starttime_ticks=99,
        held_proc_directory_identity=[8, 10], state_before='Z', state_after='Z', io=terminal_io)
    capture = dict(pid=6, terminal_proc=dict(available=True, terminal_observed=True,
        wnowait_requested=True, waitid_pid=6, io=terminal_io, snapshot=snapshot),
        proc_resolution=dict(local_wait_pid=6, outer_proc_pid=1001, child_starttime_ticks=99,
        held_child_directory_identity=[8, 10]))
    return metadata, capture


class ControlValidatorTests(unittest.TestCase):
    def validate(self, metadata, capture):
        return gate.validate_control(metadata, capture, DIGEST, PYTHON)

    def test_complete_known_reads_allow_zero_storage_layer_reads_without_scientific_authority(self):
        metadata, capture = control_fixture()
        result = self.validate(metadata, capture)
        self.assertEqual(result['terminal_kernel_io']['read_bytes'], 0)
        self.assertTrue(result['terminal_kernel_rchar_covers_known_workload'])
        self.assertTrue(result['no_per_file_attribution_claim'])
        self.assertTrue(result['no_runtime_or_scientific_certificate'])

    def test_missing_terminal_or_wnowait_evidence_is_not_replaced_by_zero(self):
        for field in ('available', 'terminal_observed', 'wnowait_requested'):
            metadata, capture = control_fixture()
            capture['terminal_proc'][field] = False
            with self.subTest(field=field), self.assertRaises(gate.Refusal):
                self.validate(metadata, capture)
        metadata, capture = control_fixture()
        capture['terminal_proc'] = None
        with self.assertRaises(gate.Refusal):
            self.validate(metadata, capture)

    def test_leaf_waitable_proc_namespace_starttime_and_directory_binding_must_agree(self):
        mutations = [('metadata', 'pid', 7), ('capture', 'pid', 7), ('terminal', 'waitid_pid', 7),
                     ('snapshot', 'local_wait_pid', 7), ('binding', 'local_wait_pid', 7),
                     ('snapshot', 'outer_proc_pid', 1002), ('snapshot', 'starttime_ticks', 100),
                     ('snapshot', 'held_proc_directory_identity', [8, 11])]
        for where, key, value in mutations:
            metadata, capture = control_fixture()
            objects = dict(metadata=metadata, capture=capture, terminal=capture['terminal_proc'],
                           snapshot=capture['terminal_proc']['snapshot'], binding=capture['proc_resolution'])
            objects[where][key] = value
            with self.subTest(where=where, key=key), self.assertRaises(gate.Refusal):
                self.validate(metadata, capture)

    def test_exact_complete_unsigned_kernel_counter_set_required(self):
        for mutation in ('missing', 'negative', 'boolean', 'unknown'):
            metadata, capture = control_fixture()
            counters = capture['terminal_proc']['io']
            if mutation == 'missing':
                del counters['syscr']
            elif mutation == 'negative':
                counters['cancelled_write_bytes'] = -1
            elif mutation == 'boolean':
                counters['syscr'] = True
            else:
                counters['unrelated'] = 0
            with self.subTest(mutation=mutation), self.assertRaises(gate.Refusal):
                self.validate(metadata, capture)

    def test_kernel_terminal_must_cover_self_counter_and_known_read_delta(self):
        metadata, capture = control_fixture()
        metadata['own_io_after']['values']['rchar'] -= 1
        with self.assertRaises(gate.Refusal):
            self.validate(metadata, capture)
        metadata, capture = control_fixture()
        capture['terminal_proc']['io']['rchar'] = 1049575
        with self.assertRaises(gate.Refusal):
            self.validate(metadata, capture)

    def test_exact_false_authority_and_stdlib_isolation_cannot_be_omitted_or_changed(self):
        mutations = [('authority', {}), ('authority', {**AUTHORITY, 'additional': False}),
                     ('authority', {**AUTHORITY, 'runtime_qualified': True}), ('isolated', False),
                     ('no_site', False), ('dont_write_bytecode', False),
                     ('installed_python_launched', True), ('scientific_modules_imported', True),
                     ('executable', '/inert/venv/bin/python')]
        for key, value in mutations:
            metadata, capture = control_fixture()
            metadata[key] = value
            with self.subTest(key=key), self.assertRaises(gate.Refusal):
                self.validate(metadata, capture)

    def test_all_eight_exact_pass_hashes_and_payload_geometry_are_required(self):
        for key, value in [('passes', 7), ('payload_bytes', 131071), ('workload_explicit_read_bytes', 1048575),
                           ('payload_sha256', 'b' * 64), ('pass_sha256', [DIGEST] * 7)]:
            metadata, capture = control_fixture()
            metadata[key] = value
            with self.subTest(key=key), self.assertRaises(gate.Refusal):
                self.validate(metadata, capture)

    def test_f_declared_envelopes_match_agreed_scope_and_joined_read_reservation(self):
        mib = 1024 ** 2
        self.assertEqual(gate.LIMITS['child_address_space_bytes'], 128 * mib)
        self.assertEqual(gate.LIMITS['input_file_bytes'], 128 * mib)
        self.assertEqual(gate.LIMITS['parent_address_space_bytes'], 256 * mib)
        self.assertEqual(gate.LIMITS['joined_read_bytes'], 528 * mib)
        self.assertEqual(gate.LIMITS['artifact_bytes'], 16 * mib)
        self.assertEqual(gate.LIMITS['root_explicit_read_bytes'] + gate.LIMITS['supervisor_pin_read_bytes'] +
                         gate.LIMITS['supervisor_proc_read_bytes'] + gate.LIMITS['misc_stream_read_bytes'],
                         gate.LIMITS['parent_read_bytes'])
        self.assertEqual(gate.LIMITS['parent_read_bytes'] + gate.LIMITS['opaque_child_read_reserve_bytes'],
                         gate.LIMITS['joined_read_bytes'])
        self.assertEqual((gate.LIMITS['wall_seconds'], gate.LIMITS['operation_seconds'],
                          gate.LIMITS['child_wall_seconds']), (30, 20, 10))


class FakeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.base = Path(self.directory.name)
        self.root = self.base / 'actual';self.root.mkdir()
        self.gate = self.base / 'inert-gate.py';self.gate.write_bytes(b'# inert, never executed\n')
        self.python = self.base / 'inert-python';self.python.write_bytes(b'INERT NEVER EXECUTED')
        pins = [dict(path=str(p), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in (self.gate, self.python)]
        self.freeze = dict(identity='radio-proc-io-control-20261006f', output_root=str(self.root),
            preparation_root=str(self.base), gate_source_path=str(self.gate), python_executable=str(self.python),
            source_pins=[pins[0]], runtime_pins=[pins[1]])
        self.freeze_path = self.base / 'freeze.json'
        self.freeze_raw = json.dumps(self.freeze).encode();self.freeze_path.write_bytes(self.freeze_raw)
        self.argv = ['launcher', '--freeze', str(self.freeze_path), '--freeze-sha256',
            hashlib.sha256(self.freeze_raw).hexdigest(), '--proof', str(self.base / 'proof.json'),
            '--proof-sha256', '0' * 64, '--marker', str(self.base / 'marker.json'), '--marker-sha256', '1' * 64]

    def tearDown(self):
        self.directory.cleanup()

    def run_fake(self, exit_code=0, gate_status='OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION', peak=4096):
        calls = []
        process = SimpleNamespace(pid=123, returncode=None)
        def popen(command, **kwargs):
            calls.append(('dispatch', command, kwargs))
            result = dict(status=gate_status, children=[{'wait4_direct_child_ru_maxrss_bytes': peak}])
            (self.root / 'result.json').write_text(json.dumps(result))
            return process
        def waitid(kind, pid, flags):
            calls.append(('waitid', kind, pid, flags))
            return SimpleNamespace(si_pid=pid, si_code=launcher.os.CLD_EXITED, si_status=exit_code)
        usage = SimpleNamespace(ru_maxrss=100, ru_utime=0.01, ru_stime=0.02)
        def wait4(pid, options):
            calls.append(('wait4', pid, options));return pid, exit_code << 8, usage
        with patch.object(launcher.sys if hasattr(launcher, 'sys') else __import__('sys'), 'argv', self.argv), \
             patch.object(launcher.subprocess, 'Popen', side_effect=popen), \
             patch.object(launcher.os, 'waitid', side_effect=waitid), \
             patch.object(launcher.os, 'wait4', side_effect=wait4), \
             patch.object(launcher.os, 'killpg', side_effect=AssertionError('no real signal')), \
             contextlib.redirect_stdout(io.StringIO()):
            code = launcher.main()
        return code, calls, json.loads((self.root / 'caller-receipt.json').read_text())

    def test_one_inert_dispatch_wnowait_then_exact_wait4_and_honest_lifetime_receipt(self):
        code, calls, receipt = self.run_fake()
        self.assertEqual(code, 0);self.assertTrue(receipt['success'])
        self.assertEqual([c[0] for c in calls], ['dispatch', 'waitid', 'wait4'])
        self.assertTrue(calls[1][3] & launcher.os.WNOWAIT)
        self.assertEqual(calls[0][1][:4], [str(self.python), '-I', '-B', '-S'])
        self.assertEqual(receipt['dispatches'], 1)
        self.assertEqual(receipt['parent_wait4_lifetime_ru_maxrss_bytes'], 100 * 1024)
        self.assertEqual(receipt['conservative_joined_rss_upper_bound_bytes'], 100 * 1024 + 4096)
        self.assertFalse(receipt['runtime_qualified']);self.assertFalse(receipt['scientific_authority'])
        self.assertIn('administrative caller overhead', receipt['explicit_limitations'][0])

    def test_nonzero_gate_exit_or_failed_gate_status_cannot_yield_caller_success(self):
        for code, status in [(2, 'OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION'), (0, 'FAILED_CLOSED')]:
            with self.subTest(code=code, status=status):
                returned, calls, receipt = self.run_fake(code, status)
                self.assertEqual(returned, 1);self.assertFalse(receipt['success'])
                self.assertEqual([c[0] for c in calls], ['dispatch', 'waitid', 'wait4'])
            for path in self.root.iterdir():path.unlink()
            for path in self.base.glob('actual.caller-*'):path.unlink()

    def test_missing_child_peak_refuses_success_instead_of_substituting_zero(self):
        code, _, receipt = self.run_fake(peak=None)
        self.assertEqual(code, 1);self.assertFalse(receipt['success'])
        self.assertFalse(receipt['child_peak_custody_complete'])
        self.assertIsNone(receipt['conservative_joined_rss_upper_bound_bytes'])

    def test_modified_pin_and_spent_output_are_refused_before_any_dispatch(self):
        self.python.write_bytes(b'CHANGED')
        with patch.object(__import__('sys'), 'argv', self.argv), \
             patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not dispatch')):
            with self.assertRaisesRegex(ValueError, 'pinned gate/Python mismatch'):
                launcher.main()
        self.python.write_bytes(b'INERT NEVER EXECUTED')
        (self.root / 'spent.json').write_text('{}')
        with patch.object(__import__('sys'), 'argv', self.argv), \
             patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not dispatch')):
            with self.assertRaisesRegex(ValueError, 'occupied one-shot root'):
                launcher.main()


if __name__ == '__main__':
    unittest.main()
