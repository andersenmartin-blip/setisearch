import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_caller_tail.py'
spec = importlib.util.spec_from_file_location('caller_tail', SCRIPT)
tail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tail)


def payload():
    # Unicode exercises Python's exact ASCII canonical output, not a projected
    # normalized tool result. Final delivery can be followed by a terminal poll.
    return tail.canonical({'schema': tail.TAIL_SCHEMA, 'client_sha256': 'a' * 64,
        'records': [{'ordinal': 3, 'response_json': json.dumps({'output': 'Thy \u2603\U0001f680', 'session_id': 7})},
                    {'ordinal': 18, 'response_json': '{"output":"","session_id":7}'},
                    {'ordinal': 19, 'response_json': '{"output":"terminal poll","exit_code":0}'}]})


def options(data):
    return dict(expected_bytes=len(data), expected_sha256=hashlib.sha256(data).hexdigest(),
                client_sha256='a' * 64, terminal_ordinal=18)


class CallerTailTests(unittest.TestCase):
    def test_actual_bytes_are_exclusive_durable_and_independently_reopened(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = str(Path(directory) / 'tail.json')
            data = payload()
            real_open, real_fsync = os.open, os.fsync
            events = []

            def opened(path, flags, *args, **kwargs):
                events.append(('open', flags))
                return real_open(path, flags, *args, **kwargs)

            def fsynced(fd):
                events.append(('fsync', fd))
                return real_fsync(fd)

            with mock.patch.object(tail.os, 'open', side_effect=opened), mock.patch.object(tail.os, 'fsync', side_effect=fsynced):
                proof = tail.persist_tail(destination, data, **options(data))
            self.assertEqual(Path(destination).read_bytes(), data)
            self.assertEqual(proof['reopened_sha256'], hashlib.sha256(Path(destination).read_bytes()).hexdigest())
            self.assertEqual(proof['stored_record_ordinals'], [3, 18, 19])
            write_index = next(i for i, e in enumerate(events) if e[0] == 'open' and e[1] & os.O_EXCL)
            reopen_index = next(i for i, e in enumerate(events) if i > write_index and e[0] == 'open')
            self.assertEqual(sum(e[0] == 'fsync' for e in events[write_index:reopen_index]), 2)
            self.assertTrue(proof['independent_reopen'])
            self.assertFalse(proof['execution_authorized'])
            self.assertEqual(os.stat(destination).st_mode & 0o777, 0o600)

    def test_existing_file_is_never_replaced_or_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'tail.json'
            destination.write_bytes(b'previous irrevocable evidence')
            with self.assertRaises(FileExistsError):
                tail.persist_tail(str(destination), payload(), **options(payload()))
            self.assertEqual(destination.read_bytes(), b'previous irrevocable evidence')

    def test_actual_changed_bytes_between_fsync_and_reopen_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'tail.json'
            real_open = os.open

            def opened(path, flags, *args, **kwargs):
                if path == destination.name and not flags & os.O_CREAT:
                    data = destination.read_bytes()
                    destination.write_bytes(data[:-1] + b'!')
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(tail.os, 'open', side_effect=opened):
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    tail.persist_tail(str(destination), payload(), **options(payload()))
            self.assertTrue(destination.exists(), 'Failed evidence is preserved; no retry/delete credit')

    def test_symlink_parent_and_existing_symlink_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            actual = parent / 'actual'
            actual.mkdir()
            (parent / 'alias').symlink_to(actual, target_is_directory=True)
            with self.assertRaises(OSError):
                tail.persist_tail(str(parent / 'alias/tail.json'), payload(), **options(payload()))
            self.assertFalse((actual / 'tail.json').exists())
            (parent / 'tail.json').symlink_to(actual / 'uncreated')
            with self.assertRaises(FileExistsError):
                tail.persist_tail(str(parent / 'tail.json'), payload(), **options(payload()))

    def test_added_hardlink_before_independent_readback_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'tail.json'
            real_open = os.open

            def opened(path, flags, *args, **kwargs):
                if path == destination.name and not flags & os.O_CREAT:
                    os.link(destination, Path(directory) / 'second-authority.json')
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(tail.os, 'open', side_effect=opened):
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    tail.persist_tail(str(destination), payload(), **options(payload()))
            self.assertEqual(destination.stat().st_nlink, 2)

    def test_changed_pin_noncanonical_bytes_and_absent_ack_fail_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = str(Path(directory) / 'tail.json')
            data = payload()
            for raw, extra in ((data + b' ', {}), (data, {'expected_sha256': 'b' * 64}),
                               (data, {'terminal_ordinal': 17})):
                kwargs = options(raw)
                kwargs.update(extra)
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    tail.persist_tail(destination, raw, **kwargs)
                self.assertFalse(Path(destination).exists())

    def test_pinned_cli_retains_full_readback_receipt_and_second_call_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = str(Path(directory) / 'tail.json')
            data = payload()
            args = [sys.executable, '-I', '-S', '-B', str(SCRIPT), '--destination', destination,
                    '--payload-base64', base64.b64encode(data).decode(), '--expected-bytes', str(len(data)),
                    '--expected-sha256', tail.sha(data), '--client-sha256', 'a' * 64, '--terminal-ordinal', '18']
            first = subprocess.run(args, capture_output=True, text=True, check=True)
            proof = json.loads(first.stdout)
            self.assertTrue(proof['durable'])
            self.assertTrue(proof['exact_readback_verified'])
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(second.returncode, 1)
            self.assertFalse(json.loads(second.stdout)['durable'])
            self.assertEqual(Path(destination).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
