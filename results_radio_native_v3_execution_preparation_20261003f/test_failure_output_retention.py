"""Tiny subprocess/filesystem regressions; no protected control is invoked."""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('failure_output_retention', HERE/'failure_output_retention.py')
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='radio-diagnostic-retention-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repository = self.root/'synthetic-repository'
        self.repository.mkdir()
        self.destination = self.root/'new-exclusive-output'
        self.env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}

    def run_child(self, code, **extra):
        args = {'destination': str(self.destination), 'repository_root': str(self.repository),
                'stdout_cap': 8192, 'stderr_cap': 8192, 'timeout_seconds': 3, 'env': self.env}
        args.update(extra)
        return h.capture([sys.executable, '-I', '-S', '-B', '-c', code], **args)

    def test_nonzero_3000_raw_stderr_retained_exactly(self):
        result = self.run_child("import os;os.write(2,b'E'*3000);os._exit(7)")
        record = result.record()
        self.assertEqual(record['process_status'], 'EXIT_NONZERO')
        self.assertEqual(record['returncode'], 7)
        self.assertFalse(record['strictly_completed'])
        self.assertTrue(record['child_reaped'])
        raw = (self.destination/'stderr.raw').read_bytes()
        self.assertEqual(raw, b'E'*3000)
        evidence = record['streams']['stderr']['reconstruction']
        self.assertEqual(h.reconstruct_raw(evidence), raw)
        self.assertEqual(record['streams']['stderr']['file_pin']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(record['streams']['stderr']['full_stream_retained'])
        self.assertEqual((self.destination/'disposition.json').read_bytes(), result.disposition_payload)
        self.assertTrue(record['disposition_fsync_complete'])
        self.assertFalse(record['engineering_control_qualified'])

    def test_non_utf8_output_has_json_safe_lossless_reconstruction(self):
        raw = b'\x00\xff\xfe\x80\nhello\r\x00'
        result = self.run_child('import os;os.write(1,'+repr(raw)+');os._exit(9)')
        record = json.loads(result.payload)
        self.assertEqual(h.reconstruct_raw(record['streams']['stdout']['reconstruction']), raw)
        self.assertEqual((self.destination/'stdout.raw').read_bytes(), raw)
        self.assertNotIn('decode', record['streams']['stdout'])

    def test_zero_exit_requires_all_capture_and_persistence_checks(self):
        result = self.run_child("import os;os.write(1,b'valid');os.write(2,b'notice')")
        record = result.record()
        self.assertEqual(record['process_status'], 'EXIT_ZERO')
        self.assertTrue(record['strictly_completed'])
        self.assertFalse(record['scientific_execution_authorized'])
        self.assertFalse(record['whole_descendant_lifetime_qualified'])
        self.assertEqual(record['persistence_errors'], [])

    def test_stdout_cap_retains_exact_prefix_and_marks_unknown_tail(self):
        result = self.run_child("import os;os.write(1,b'0123456789'*1000)", stdout_cap=123)
        record = result.record()
        self.assertEqual(record['process_status'], 'OUTPUT_LIMIT')
        self.assertFalse(record['strictly_completed'])
        stream = record['streams']['stdout']
        self.assertEqual(h.reconstruct_raw(stream['reconstruction']), (b'0123456789'*1000)[:123])
        self.assertGreater(stream['observed_bytes'], 123)
        self.assertTrue(stream['truncated'])
        self.assertFalse(stream['full_stream_retained'])
        self.assertEqual((self.destination/'stdout.raw').stat().st_size, 123)

    def test_zero_exit_cannot_promote_stderr_cap_breach(self):
        record = self.run_child("import os;os.write(2,b'X'*5000)", stderr_cap=8).record()
        self.assertFalse(record['strictly_completed'])
        self.assertEqual(record['process_status'], 'OUTPUT_LIMIT')
        self.assertEqual(h.reconstruct_raw(record['streams']['stderr']['reconstruction']), b'X'*8)

    def test_exact_cap_and_eof_not_truncated(self):
        record = self.run_child("import os;os.write(1,b'A'*32)", stdout_cap=32).record()
        self.assertTrue(record['strictly_completed'])
        self.assertFalse(record['streams']['stdout']['truncated'])
        self.assertTrue(record['streams']['stdout']['full_stream_retained'])

    def test_zero_cap_accepts_empty_only(self):
        record = self.run_child('pass', stdout_cap=0, stderr_cap=0).record()
        self.assertTrue(record['strictly_completed'])
        self.assertEqual(h.reconstruct_raw(record['streams']['stdout']['reconstruction']), b'')

    def test_timeout_preserves_prefix_and_never_becomes_success(self):
        record = self.run_child("import os,time;os.write(2,b'before-timeout');time.sleep(5)", timeout_seconds=0.15).record()
        self.assertEqual(record['process_status'], 'TIMEOUT')
        self.assertTrue(record['timed_out'])
        self.assertTrue(record['child_reaped'])
        self.assertFalse(record['strictly_completed'])
        self.assertEqual(h.reconstruct_raw(record['streams']['stderr']['reconstruction']), b'before-timeout')

    def test_launch_failure_retains_one_failed_disposition(self):
        record = h.capture(['/no/such/diagnostic-test-executable'], destination=str(self.destination),
                           repository_root=str(self.repository)).record()
        self.assertEqual(record['process_status'], 'LAUNCH_FAILURE')
        self.assertFalse(record['strictly_completed'])
        self.assertFalse(record['child_reaped'])
        self.assertIsNone(record['returncode'])
        self.assertTrue(record['disposition_fsync_complete'])

    def test_existing_destination_refused_before_launch_without_overwrite(self):
        self.run_child("import os;os.write(2,b'original-failure');os._exit(3)")
        before = {p.name:p.read_bytes() for p in self.destination.iterdir()}
        with mock.patch.object(h.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaises(h.RetentionError):
                self.run_child('pass')
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.destination.iterdir()})
        self.assertEqual(json.loads(before['disposition.json'])['process_status'], 'EXIT_NONZERO')

    def test_existing_hardlinked_artifact_destination_is_never_adopted(self):
        self.destination.mkdir()
        original = self.root/'original';original.write_bytes(b'old')
        os.link(original, self.destination/'stderr.raw')
        with mock.patch.object(h.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaises(h.RetentionError):
                self.run_child('pass')
        self.assertEqual(original.read_bytes(), b'old')
        self.assertEqual(original.stat().st_nlink, 2)

    def test_repository_and_protected_root_overlap_reject_before_open_or_launch(self):
        protected = self.root/'private-protected'
        for destination in (self.repository/'out', self.repository, self.root, protected/'out'):
            with self.subTest(destination=destination), mock.patch.object(h.os, 'open', side_effect=AssertionError('must not open')):
                with self.assertRaises(h.RetentionError):
                    self.run_child('pass', destination=str(destination), protected_roots=[str(protected)])

    def test_false_supplied_repository_cannot_allow_selected_helper_repository(self):
        with mock.patch.object(h.os,'open',side_effect=AssertionError('must not open selected repository')):
            with self.assertRaisesRegex(h.RetentionError,'overlaps'):
                self.run_child('pass',destination=h.IMPLEMENTATION_REPOSITORY_ROOT+'/forbidden-diagnostic-output')

    def test_symlink_parent_and_destination_refused(self):
        actual = self.root/'actual';actual.mkdir()
        alias = self.root/'alias';alias.symlink_to(actual, target_is_directory=True)
        for destination in (alias/'new', alias):
            with self.subTest(destination=destination), mock.patch.object(h.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
                with self.assertRaises(h.RetentionError):
                    self.run_child('pass', destination=str(destination))
        self.assertEqual(list(actual.iterdir()), [])

    def test_noncanonical_paths_and_invalid_caps_refuse(self):
        cases = [{'destination': str(self.root)+'/./new'}, {'stdout_cap': True}, {'stderr_cap': -1},
                 {'stdout_cap': h.MAX_STREAM_CAP+1}, {'timeout_seconds': float('nan')},
                 {'timeout_seconds': h.MAX_TIMEOUT_SECONDS+1}, {'timeout_seconds': True}]
        for extra in cases:
            with self.subTest(extra=extra), mock.patch.object(h.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
                with self.assertRaises(h.RetentionError):
                    self.run_child('pass', **extra)
        self.assertFalse(self.destination.exists())

    def test_command_argv_bounds_refuse_before_destination_reservation(self):
        for argv in ([sys.executable]*129, [sys.executable,'X'*4097], [sys.executable]+['X'*4096]*9):
            with self.subTest(length=len(argv)), mock.patch.object(h.os,'open',side_effect=AssertionError('must not reserve')):
                with self.assertRaises(h.RetentionError):
                    h.capture(argv,destination=str(self.destination),repository_root=str(self.repository))

    def test_fsync_failure_cannot_turn_nonzero_disposition_successful(self):
        real = h.os.fsync
        count = 0
        def failed(fd):
            nonlocal count
            count += 1
            if count == 4:
                raise OSError('simulated diagnostic fsync failure')
            return real(fd)
        with mock.patch.object(h.os,'fsync',side_effect=failed):
            record = self.run_child("import os;os.write(2,b'failed-before-fsync');os._exit(6)").record()
        self.assertEqual(record['process_status'],'EXIT_NONZERO')
        self.assertFalse(record['strictly_completed'])
        self.assertTrue(record['persistence_errors'])
        self.assertEqual(h.reconstruct_raw(record['streams']['stderr']['reconstruction']),b'failed-before-fsync')

    def test_partial_stream_write_failure_retains_actual_prefix_pin_and_closes(self):
        original = h._write_all
        def failed(fd, raw):
            if raw == b'Z'*3000:
                os.write(fd, raw[:17])
                raise OSError('simulated diagnostic storage failure')
            return original(fd, raw)
        with mock.patch.object(h, '_write_all', side_effect=failed):
            record = self.run_child("import os;os.write(2,b'Z'*3000)").record()
        self.assertEqual(record['process_status'], 'EXIT_ZERO')
        self.assertFalse(record['strictly_completed'])
        self.assertTrue(record['persistence_errors'])
        stream = record['streams']['stderr']
        self.assertFalse(stream['file_write_complete'])
        self.assertEqual(stream['file_pin']['bytes'], 17)
        self.assertEqual(stream['file_pin']['sha256'], hashlib.sha256(b'Z'*17).hexdigest())
        self.assertEqual(h.reconstruct_raw(stream['reconstruction']), b'Z'*3000)
        self.assertEqual((self.destination/'stderr.raw').read_bytes(), b'Z'*17)
        self.assertFalse(json.loads((self.destination/'disposition.json').read_bytes())['strictly_completed'])

    def test_manifest_write_failure_never_overwrites_to_success(self):
        original = h._write_all
        writes = []
        def failed(fd, raw):
            if raw.startswith(b'{'):
                writes.append(raw)
                os.write(fd, raw[:40])
                raise OSError('simulated manifest write failure')
            return original(fd, raw)
        with mock.patch.object(h, '_write_all', side_effect=failed):
            result = self.run_child("import os;os.write(2,b'failed');os._exit(8)")
        record = result.record()
        self.assertFalse(record['strictly_completed'])
        self.assertEqual(record['process_status'], 'EXIT_NONZERO')
        self.assertEqual(len(writes), 1)
        self.assertFalse(record['disposition_write_complete'])
        self.assertFalse(record['disposition_fsync_complete'])
        self.assertEqual((self.destination/'disposition.json').read_bytes(), result.disposition_payload[:40])
        self.assertEqual((self.destination/'stderr.raw').read_bytes(), b'failed')

    def test_hardlink_added_during_write_refuses_file_proof(self):
        original = h._write_all
        def linked(fd, raw):
            original(fd, raw)
            if raw == b'link-race':
                os.link(self.destination/'stderr.raw', self.root/'foreign-alias')
        with mock.patch.object(h, '_write_all', side_effect=linked):
            record = self.run_child("import os;os.write(2,b'link-race')").record()
        self.assertFalse(record['strictly_completed'])
        self.assertIsNone(record['streams']['stderr']['file_pin'])
        self.assertTrue(any('link count' in e['error'] for e in record['persistence_errors']))

    def test_output_path_replacement_cannot_claim_success_from_held_old_inode(self):
        original = h._write_all
        def replaced(fd, raw):
            original(fd, raw)
            if raw == b'path-race':
                (self.destination/'stdout.raw').rename(self.root/'displaced-stdout')
                (self.destination/'stdout.raw').symlink_to(self.root/'displaced-stdout')
        with mock.patch.object(h,'_write_all',side_effect=replaced):
            record = self.run_child("import os;os.write(1,b'path-race')").record()
        self.assertFalse(record['strictly_completed'])
        self.assertTrue(any('pathname' in e['error'] for e in record['persistence_errors']))

    def test_reservation_failure_leaves_spent_destination_and_never_launches(self):
        original = h.os.open
        def failed(path, *args, **kwargs):
            if path == 'disposition.json':
                raise OSError('simulated exclusive reservation failure')
            return original(path, *args, **kwargs)
        with mock.patch.object(h.os, 'open', side_effect=failed), mock.patch.object(h.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaises(h.RetentionError):
                self.run_child('pass')
        self.assertTrue(self.destination.is_dir())
        with self.assertRaises(h.RetentionError):
            self.run_child('pass')

    def test_reconstruction_rejects_size_hash_encoding_and_ambiguous_base64(self):
        evidence = h._evidence(b'\x00\xffraw')
        for key,value in (('bytes',True),('bytes',99),('sha256','0'*64),('encoding','utf8'),('data','!!!!'),('data',evidence['data']+'\n')):
            other = copy.deepcopy(evidence);other[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(h.RetentionError):
                h.reconstruct_raw(other)
        self.assertEqual(h.reconstruct_raw(evidence), b'\x00\xffraw')

    def test_import_has_no_files_network_or_process_effect(self):
        import socket
        import subprocess
        spec = importlib.util.spec_from_file_location('retention_import_purity_probe', HERE/'failure_output_retention.py')
        raw = (HERE/'failure_output_retention.py').read_bytes()
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        with mock.patch('builtins.open',side_effect=AssertionError('open')), mock.patch.object(io,'open',side_effect=AssertionError('io.open')), mock.patch.object(os,'open',side_effect=AssertionError('os.open')), mock.patch.object(socket,'socket',side_effect=AssertionError('socket')), mock.patch.object(subprocess,'Popen',side_effect=AssertionError('Popen')):
            exec(compile(raw,str(HERE/'failure_output_retention.py'),'exec'), module.__dict__)
        self.assertEqual(module.SCHEMA, h.SCHEMA)


if __name__ == '__main__':
    unittest.main()
