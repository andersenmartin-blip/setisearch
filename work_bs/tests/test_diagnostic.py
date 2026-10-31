import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[1]/'diagnostic.py'
spec = importlib.util.spec_from_file_location('bs_diagnostic_tests', PATH)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DiagnosticTests(unittest.TestCase):
    def test_audited_cli_br_events_and_limits_of_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'new'
            audit = Path(folder)/'PYTHON_AUDIT.jsonl'
            completed = subprocess.run([sys.executable, str(PATH.with_name('audited_worker.py')),
                                        '--audit', str(audit), '--writer', 'br',
                                        '--output-dir', str(out), '--records', '2'],
                                       capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            events = [json.loads(line) for line in audit.read_text().splitlines()]
            self.assertEqual(events[0]['event'], 'BS_PYTHON_AUDIT_START')
            self.assertFalse(events[0]['syscall_trace'])
            self.assertEqual(events[-1]['event'], 'BS_PYTHON_AUDIT_END')
            self.assertEqual(events[-1]['diagnostic_return_code'], 0)
            observed = {event['event'] for event in events}
            self.assertTrue({'open', 'os.chmod', 'os.link', 'os.remove'} <= observed)
            self.assertEqual(events[-1]['recorded_operation_events'], len(events)-2)
            self.assertEqual(json.loads((out/'RESULT.json').read_text())['status'], 'PASS')

    def test_cli_respects_inherited_cpu_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'new'
            def set_inherited_limits():
                resource.setrlimit(resource.RLIMIT_CPU, (90, 91))
            completed = subprocess.run([sys.executable, str(PATH), '--writer', 'bq',
                                        '--output-dir', str(out), '--records', '2'],
                                       capture_output=True, text=True, timeout=20,
                                       preexec_fn=set_inherited_limits)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((out/'RESULT.json').read_text())
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['inherited_or_tightened_resource_limits']['RLIMIT_CPU'], [90, 91])
            terminal = json.loads(completed.stdout.splitlines()[-1])
            self.assertEqual(terminal['event'], 'GATE_TERMINAL_EOF')
            self.assertEqual(terminal['result_sha256'], d.sha(out/'RESULT.json'))

    def test_tighten_all_limits_preserves_stricter_soft_and_hard(self):
        for which in (resource.RLIMIT_CPU, resource.RLIMIT_AS, resource.RLIMIT_FSIZE):
            with mock.patch.object(d.resource, 'getrlimit', return_value=(90, 91)), \
                    mock.patch.object(d.resource, 'setrlimit') as setter:
                d.tighten_limit(which, 180)
                setter.assert_called_once_with(which, (90, 91))

    def test_original_bq_writer_complete_exact_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            result = d.run_fixture('bq', Path(folder)/'new', records=17)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual([s['writer_receipt']['records'] for s in result['streams']], [17, 17])
            self.assertEqual(result['monitor_violations'], 0)

    def test_original_br_writer_complete_exact_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            result = d.run_fixture('br', Path(folder)/'new', records=19)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual([s['writer_receipt']['records'] for s in result['streams']], [19, 19])
            self.assertEqual(result['monitor_violations'], 0)

    def test_exclusive_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                d.run_fixture('bq', folder, records=1)

    def test_fixture_truncation_detected_independently(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'new'
            result = d.run_fixture('bq', out, records=7)
            item = result['streams'][0]
            path = out/'payload'/item['path']
            with path.open('r+b') as stream:
                stream.truncate(path.stat().st_size-4)
            with self.assertRaises(ValueError):
                d.verify_file(path, item['expected'])

    def test_same_length_mutation_detected_independently(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'new'
            result = d.run_fixture('bq', out, records=3)
            item = result['streams'][0]
            path = out/'payload'/item['path']
            raw = path.read_bytes().replace(b'0123456789abcdef', b'0123456789abcdeg', 1)
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                d.verify_file(path, item['expected'])

    def test_monitor_retains_held_fd_and_detects_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture_0.jsonl'
            path.write_bytes(b'first\n')
            monitor = d.LifecycleMonitor(folder)
            monitor.begin()
            first = monitor.snapshot('first')
            monitor.mark_closed(path)
            replacement = Path(folder)/'replacement'
            replacement.write_bytes(b'second\n')
            os.replace(replacement, path)
            second = monitor.snapshot('replacement')
            saved = monitor.finish()
            self.assertNotEqual(first['paths'][path.name]['inode'], second['paths'][path.name]['inode'])
            self.assertGreaterEqual(len(second['held_descriptors']), 2)
            self.assertIn('PATH_REPLACED', [v['kind'] for v in saved['violations']])
            self.assertIn('CLOSED_FILE_CHANGED', [v['kind'] for v in saved['violations']])

    def test_monitor_keys_descriptor_by_actual_opened_inode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture_0.jsonl'
            path.write_bytes(b'original\n')
            monitor = d.LifecycleMonitor(folder)
            replacement = Path(folder)/'replacement'
            replacement.write_bytes(b'replacement\n')
            actual_open = os.open
            replaced = False
            def racing_open(name, flags, *args, **kwargs):
                nonlocal replaced
                if Path(name) == path and not replaced:
                    os.replace(replacement, path)
                    replaced = True
                return actual_open(name, flags, *args, **kwargs)
            try:
                with mock.patch.object(d.os, 'open', side_effect=racing_open):
                    monitor.snapshot('race')
                self.assertTrue(replaced)
                for key, (fd, _) in monitor.held.items():
                    opened = os.fstat(fd)
                    self.assertEqual(key, (opened.st_dev, opened.st_ino))
                self.assertIn('PATH_OPEN_RACE', [v['kind'] for v in monitor.violations])
            finally:
                monitor.begin()
                monitor.finish()

    def test_monitor_detects_size_regression(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture_0.jsonl'
            path.write_bytes(b'initial contents\n')
            monitor = d.LifecycleMonitor(folder)
            monitor.begin()
            monitor.snapshot('first')
            path.write_bytes(b'short\n')
            monitor.snapshot('second')
            saved = monitor.finish()
            self.assertIn('SIZE_REGRESSION', [v['kind'] for v in saved['violations']])

    def test_monitor_detects_closed_file_disappearance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture_0.jsonl'
            path.write_bytes(b'closed\n')
            monitor = d.LifecycleMonitor(folder)
            monitor.begin()
            monitor.mark_closed(path)
            path.unlink()
            monitor.snapshot('removed')
            saved = monitor.finish()
            self.assertIn('CLOSED_FILE_MISSING', [v['kind'] for v in saved['violations']])

    def test_metadata_only_change_after_close_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture_0.jsonl'
            path.write_bytes(b'unchanged content\n')
            path.chmod(0o600)
            monitor = d.LifecycleMonitor(folder)
            monitor.begin()
            monitor.mark_closed(path)
            path.chmod(0o400)
            monitor.snapshot('mode_only_change')
            saved = monitor.finish()
            changes = [v for v in saved['violations'] if v['kind'] == 'CLOSED_FILE_CHANGED']
            self.assertTrue(changes)
            self.assertEqual(changes[0]['before']['size'], changes[0]['after']['size'])
            self.assertEqual(changes[0]['before']['inode'], changes[0]['after']['inode'])
            self.assertNotEqual(changes[0]['before']['mode'], changes[0]['after']['mode'])

    def test_br_pending_unlink_is_benign_after_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'new'
            result = d.run_fixture('br', out, records=2)
            saved = json.loads((out/'FILE_MONITOR.json').read_text())
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(saved['violations'], [])
            paths = saved['samples'][-1]['paths']
            self.assertEqual(set(paths), {'fixture_0.jsonl', 'fixture_1.jsonl'})
            self.assertTrue(all(item['nlink'] == 1 for item in paths.values()))
            self.assertTrue(all(item['mode'] == 0o444 for item in paths.values()))
            self.assertTrue(any(item['first_name'].endswith('.pending')
                                for item in saved['samples'][-1]['held_descriptors']))

    def test_bounds_reject_without_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'new'
            for n in [0, 45001]:
                with self.assertRaises(ValueError):
                    d.run_fixture('bq', path, records=n)
            with self.assertRaises(ValueError):
                d.run_fixture('br', path, records=1, pace_ms=101)
            self.assertFalse(path.exists())

    def test_fixture_schema_and_fixed_payload(self):
        values = [d.fixture_record(1, i) for i in range(4)]
        self.assertEqual(len(values[0]['payload']), 1900)
        self.assertEqual([v['status'] for v in values], ['OFF_VETO', 'THREE_ON_FAIL', 'THREE_ON_FAIL', 'OFF_VETO'])
        self.assertTrue(all(d.encode(v).endswith(b'\n') for v in values))
        self.assertEqual(json.loads(d.encode(values[0])), values[0])


if __name__ == '__main__':
    unittest.main()
