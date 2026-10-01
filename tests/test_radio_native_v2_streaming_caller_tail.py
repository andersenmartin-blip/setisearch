import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import termios
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_streaming_caller_tail.py'
spec = importlib.util.spec_from_file_location('stream_tail', SCRIPT)
tail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tail)


def sample(padding=80000, records=1):
    rows = []
    for ordinal in range(records):
        result = {'output': '', 'padding': '\x7f' * padding, 'session_id': 7}
        if ordinal == records - 1:
            result = {'exit_code': 0, 'output': '{"kind":"terminal"}\n', 'padding': '\x7f' * padding}
        response = json.dumps(result, separators=(',', ':'), ensure_ascii=False)
        rows.append({'ordinal': ordinal + 20, 'response_json': response})
    value = {'schema': tail.TAIL_SCHEMA, 'client_sha256': 'a' * 64, 'records': rows}
    wire = json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()
    payload = tail.canonical(value)
    return wire, payload, dict(wire_bytes=len(wire), wire_sha256=tail.sha(wire),
        payload_bytes=len(payload), payload_sha256=tail.sha(payload), client_sha256='a' * 64,
        terminal_ordinal=rows[-1]['ordinal'])


def maximum_sample(symbol):
    rows = []
    for ordinal in range(7):
        result = {'output': '', 'padding': '', 'session_id': 7}
        if ordinal == 6:
            result = {'exit_code': 0, 'output': '{"kind":"terminal"}\n', 'padding': ''}
        dump = lambda obj: json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
        baseline = len(dump(result).encode())
        expansion = len(dump(symbol).encode()) - 2
        count, remainder = divmod(tail.MAX_ENVELOPE_BYTES - baseline, expansion)
        result['padding'] = symbol * count + 'a' * remainder
        response = dump(result)
        if len(response.encode()) != tail.MAX_ENVELOPE_BYTES:
            raise AssertionError('Exact legal raw support-envelope ceiling required')
        rows.append({'ordinal': ordinal + 20, 'response_json': response})
    value = {'schema': tail.TAIL_SCHEMA, 'client_sha256': 'a' * 64, 'records': rows}
    wire = json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()
    payload = tail.canonical(value)
    return wire, payload, dict(wire_bytes=len(wire), wire_sha256=tail.sha(wire),
        payload_bytes=len(payload), payload_sha256=tail.sha(payload), client_sha256='a' * 64,
        terminal_ordinal=rows[-1]['ordinal'])


def argv(destination, kwargs):
    out = [sys.executable, '-I', '-S', '-B', str(SCRIPT), '--destination', destination]
    for key, value in kwargs.items():
        out.extend(['--' + key.replace('_', '-'), str(value)])
    return out


def read_line(fd, seconds=10):
    data = bytearray()
    while b'\n' not in data:
        if not select.select([fd], [], [], seconds)[0]:
            raise AssertionError('Actual PTY helper failed to return a bounded frame')
        data.extend(os.read(fd, 65536))
        if len(data) > 4096:
            raise AssertionError('Input echo or unexpectedly large helper reply')
    return bytes(data)


class StreamingCallerTailTests(unittest.TestCase):
    def test_actual_pty_large_del_transfer_is_raw_noecho_before_ready_and_canonical_after_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = str(Path(directory) / 'tail.json')
            # Seven replies close the permitted six-poll plus final-ack shape.
            # Near-maximum raw DEL replies expand sixfold in the stored file.
            wire, payload, kwargs = sample(padding=tail.MAX_ENVELOPE_BYTES - 100, records=7)
            master, slave = pty.openpty()
            process = subprocess.Popen(argv(destination, kwargs), stdin=slave, stdout=slave, stderr=slave)
            os.close(slave)
            try:
                ready = json.loads(read_line(master))
                self.assertEqual(ready['schema'], tail.READY_SCHEMA)
                self.assertTrue(ready['stdin_is_tty'])
                self.assertEqual(ready['stdin_mode'], 'tty_raw_noecho')
                settings = termios.tcgetattr(master)
                self.assertEqual(settings[3] & (termios.ECHO | termios.ICANON), 0)
                encoded = base64.b64encode(wire) + b'\n'
                self.assertLessEqual(len(encoded), ready['max_stdin_bytes'])
                cursor = 0
                while cursor < len(encoded):
                    cursor += os.write(master, memoryview(encoded)[cursor:])
                receipt = json.loads(read_line(master))
                self.assertEqual(process.wait(timeout=10), 0)
                self.assertTrue(receipt['independent_reopen'])
                self.assertTrue(receipt['exact_readback_verified'])
                self.assertEqual(Path(destination).read_bytes(), payload)
                self.assertGreater(len(payload), 10 * 1024**2)
                self.assertGreater(len(payload), 47616)
                self.assertEqual(receipt['reopened_sha256'], hashlib.sha256(payload).hexdigest())
                self.assertFalse(receipt['execution_authorized'])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)

    def test_actual_pty_exact_maximum_backslash_and_del_envelopes_fit_wire_and_storage_bounds(self):
        for symbol in ('\\', '\x7f'):
            with self.subTest(symbol=repr(symbol)), tempfile.TemporaryDirectory() as directory:
                destination = str(Path(directory) / 'tail.json')
                wire, payload, kwargs = maximum_sample(symbol)
                self.assertLessEqual(len(wire), tail.MAX_WIRE_BYTES)
                self.assertLessEqual(len(payload), tail.MAX_CANONICAL_BYTES)
                master, slave = pty.openpty()
                process = subprocess.Popen(argv(destination, kwargs), stdin=slave, stdout=slave, stderr=slave)
                os.close(slave)
                try:
                    ready = json.loads(read_line(master))
                    self.assertTrue(ready['stdin_raw_noecho_ready'])
                    encoded = base64.b64encode(wire) + b'\n'
                    self.assertLessEqual(len(encoded), ready['max_stdin_bytes'])
                    if symbol == '\\':
                        self.assertGreater(len(encoded), tail.MAX_BASE64_BYTES - 4096)
                    else:
                        self.assertGreater(len(payload), tail.MAX_CANONICAL_BYTES - 4096)
                    cursor = 0
                    while cursor < len(encoded):
                        cursor += os.write(master, memoryview(encoded)[cursor:])
                    receipt = json.loads(read_line(master))
                    self.assertEqual(process.wait(timeout=10), 0)
                    self.assertEqual(Path(destination).read_bytes(), payload)
                    self.assertEqual(receipt['payload_bytes'], len(payload))
                    self.assertEqual(receipt['reopened_sha256'], tail.sha(payload))
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)

    def test_default_cli_cannot_claim_tty_ready_for_pipe_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            wire, _, kwargs = sample()
            result = subprocess.run(argv(str(Path(directory) / 'tail.json'), kwargs), input=b'', capture_output=True)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output['status'], 'CLOSED_FAILED')
            self.assertIn('TTY', output['error'])
            self.assertFalse((Path(directory) / 'tail.json').exists())

    def test_partial_stdin_is_bounded_by_internal_deadline(self):
        read, write = os.pipe()
        try:
            os.write(write, b'partial-base64-without-newline')
            with self.assertRaisesRegex(TimeoutError, 'deadline exhausted'):
                tail.read_transfer(read, seconds=0.01)
        finally:
            os.close(read)
            os.close(write)

    def test_changed_pins_and_extra_envelope_refuse_before_authoritative_file(self):
        wire, _, kwargs = sample()
        bad = dict(kwargs, payload_sha256='b' * 64)
        with self.assertRaisesRegex(ValueError, 'canonical streaming tail pin'):
            tail.validate_wire(wire, **bad)
        too_large_wire, _, too_large = sample(padding=tail.MAX_ENVELOPE_BYTES, records=1)
        with self.assertRaisesRegex(ValueError, 'unchanged envelope cap'):
            tail.validate_wire(too_large_wire, **too_large)

    def test_existing_file_and_changed_bytes_are_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'tail.json'
            _, payload, _ = sample()
            destination.write_bytes(b'irrevocable earlier evidence')
            with self.assertRaises(FileExistsError):
                tail.persist_tail(str(destination), payload)
            self.assertEqual(destination.read_bytes(), b'irrevocable earlier evidence')
            destination.unlink()
            real_open = os.open

            def opened(path, flags, *args, **kwargs):
                if path == destination.name and not flags & os.O_CREAT:
                    data = destination.read_bytes()
                    destination.write_bytes(data[:-1] + b'!')
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(tail.os, 'open', side_effect=opened):
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    tail.persist_tail(str(destination), payload)
            self.assertTrue(destination.exists())

    def test_added_hardlink_is_refused_after_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'tail.json'
            _, payload, _ = sample()
            real_open = os.open

            def opened(path, flags, *args, **kwargs):
                if path == destination.name and not flags & os.O_CREAT:
                    os.link(destination, Path(directory) / 'duplicate.json')
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(tail.os, 'open', side_effect=opened):
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    tail.persist_tail(str(destination), payload)

    def test_replaced_absolute_parent_is_refused_even_when_retained_fd_readback_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / 'parent'
            parent.mkdir()
            destination = parent / 'tail.json'
            _, payload, _ = sample()
            real_open = os.open

            def opened(path, flags, *args, **kwargs):
                if path == destination.name and not flags & os.O_CREAT:
                    parent.rename(Path(directory) / 'renamed-parent')
                    parent.mkdir()
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(tail.os, 'open', side_effect=opened):
                with self.assertRaisesRegex(ValueError, 'parent path changed'):
                    tail.persist_tail(str(destination), payload)
            self.assertFalse(destination.exists())
            self.assertEqual((Path(directory) / 'renamed-parent/tail.json').read_bytes(), payload)


if __name__ == '__main__':
    unittest.main()
