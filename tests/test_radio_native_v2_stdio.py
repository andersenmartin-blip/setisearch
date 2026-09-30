"""Concrete persistent-pipe durability/fault tests; dummy bytes, no RNG."""
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from seti_repeater.empty_null_radio import canonical
from seti_repeater import native_v2_bridge_radio as bridge
from seti_repeater import native_v2_stdio_radio as stdio


class ShortReader(io.BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 7) if size >= 0 else 7)


class StdioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'store'
        self.store = bridge.Store.create(str(self.root))

    def tearDown(self):
        self.temp.cleanup()

    def header(self, ordinal, action, *, case=None, **extra):
        return canonical({'schema': stdio.SCHEMA, 'ordinal': ordinal,
                          'action': action, 'case_ordinal': case, **extra}) + b'\n'

    def put(self, ordinal, data, *, identity='dummy', kind='host_receipt',
            reservation='new', case=None):
        return self.header(ordinal, 'put', case=case, id=identity, kind=kind,
                           bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           reservation=reservation) + data

    def test_large_cli_upload_uses_one_command_ack_and_exact_readback(self):
        data = (b'one\x00\xff\r\n' * 170000) + b'end'
        packet = self.put(0, data, case=0) + self.header(1, 'get', case=0, id='dummy') + self.header(2, 'close')
        script = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_stdio.py'
        env = {**os.environ, 'PYTHONPATH': str(script.parent.parent / 'src')}
        result = subprocess.run([sys.executable, '-B', str(script), '--root', str(self.root)],
                                input=packet, capture_output=True, env=env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        output = io.BytesIO(result.stdout)
        put = json.loads(output.readline())
        get = json.loads(output.readline())
        self.assertEqual(put['ordinal'], 0)
        self.assertEqual(get['result']['binary_bytes'], len(data))
        self.assertEqual(output.read(len(data)), data)
        self.assertTrue(json.loads(output.readline())['result']['closed'])
        self.assertEqual(output.read(), b'')
        self.assertEqual(self.store.payload('dummy'), data)
        self.assertEqual(len([row for row in self.store.status()['items'] if '-ack-' in row['id']]), 3)
        self.assertFalse(self.store.status()['stopped'])

    def test_ack_is_durable_before_first_output_and_bucket_limits_unchanged(self):
        service = stdio.StdioService(self.store)
        outer = self
        class CheckWriter(io.BytesIO):
            def write(self, raw):
                ack = outer.store.payload('stdio-session-ack-000000')
                outer.assertTrue(json.loads(ack)['result']['durable'])
                return super().write(raw)
        output = CheckWriter()
        service.one(io.BytesIO(self.put(0, b'exact')), output)
        self.assertEqual(self.store.status()['limits'], bridge.LIMITS)
        self.assertEqual(self.store.status()['case_limits'], bridge.CASE_LIMITS)
        self.assertEqual(self.store.payload('stdio-session-command-000000') + b'\n',
                         self.put(0, b'exact')[:-5])
        ack_bytes = len(self.store.payload('stdio-session-ack-000000'))
        self.assertLess(ack_bytes, stdio.ACK_BYTES)
        self.assertEqual(self.store.status()['buckets']['bridge_receipt']['unknown_bytes'], 0)

    def test_short_pipe_reads_upload_binary_without_full_payload_join(self):
        data = b'\x00\xffbinary\r\n' * 6000
        service = stdio.StdioService(self.store)
        output = io.BytesIO()
        service.one(ShortReader(self.put(0, data)), output)
        self.assertEqual(self.store.payload('dummy'), data)
        self.assertLess(len(output.getvalue()), 1000)

    def test_existing_worker_reservation_seals_exact_response_without_second_charge(self):
        self.store.reserve('response-000000', 'response', 10000, case_ordinal=3)
        data = canonical({'result': 'exact'})
        service = stdio.StdioService(self.store)
        service.one(io.BytesIO(self.put(0, data, identity='response-000000', kind='response',
                                       reservation='existing', case=3)), io.BytesIO())
        bucket = self.store.status()['buckets']['response']
        self.assertEqual(bucket['items'], 1)
        self.assertEqual(bucket['known_bytes'], len(data))
        self.assertEqual(bucket['unknown_bytes'], 0)

    def test_partial_upload_retains_entire_reservation_and_ack_unknown(self):
        service = stdio.StdioService(self.store)
        packet = self.put(0, b'x' * (bridge.CHUNK_BYTES + 1))[:-1]
        with self.assertRaises(EOFError):
            service.one(io.BytesIO(packet), io.BytesIO())
        state = bridge.Store(str(self.root)).status()
        self.assertTrue(state['stopped'])
        self.assertEqual(state['buckets']['host_receipt']['unknown_bytes'], bridge.CHUNK_BYTES + 1)
        self.assertEqual(state['buckets']['bridge_receipt']['unknown_bytes'], stdio.ACK_BYTES)
        self.assertEqual((self.root / 'items/dummy/part').stat().st_size, bridge.CHUNK_BYTES)
        with self.assertRaises(RuntimeError):
            service.one(io.BytesIO(packet), io.BytesIO())

    def test_wrong_sha_keeps_original_bytes_and_no_success_ack(self):
        service = stdio.StdioService(self.store)
        packet = self.header(0, 'put', id='wrong', kind='host_receipt', bytes=6,
                             sha256='0' * 64, reservation='new') + b'actual'
        output = io.BytesIO()
        with self.assertRaises(ValueError):
            service.one(io.BytesIO(packet), output)
        self.assertEqual(output.getvalue(), b'')
        self.assertEqual((self.root / 'items/wrong/part').read_bytes(), b'actual')
        self.assertEqual(self.store.status()['buckets']['host_receipt']['unknown_bytes'], 6)

    def test_duplicate_command_and_session_cannot_retry(self):
        service = stdio.StdioService(self.store)
        service.one(io.BytesIO(self.put(0, b'original')), io.BytesIO())
        with self.assertRaises(ValueError):
            service.one(io.BytesIO(self.put(0, b'overwrite')), io.BytesIO())
        self.assertEqual(self.store.payload('dummy'), b'original')
        with self.assertRaises((ValueError, RuntimeError)):
            stdio.StdioService(self.store)

    def test_existing_partial_or_wrong_case_cannot_resume(self):
        for variant in ('partial', 'case'):
            root = Path(self.temp.name) / variant
            store = bridge.Store.create(str(root))
            store.reserve('existing', 'response', 100, case_ordinal=0)
            if variant == 'partial':
                store.append('existing', 0, b'old')
            service = stdio.StdioService(store)
            with self.assertRaises(ValueError):
                service.one(io.BytesIO(self.put(0, b'new', identity='existing', kind='response',
                    reservation='existing', case=1 if variant == 'case' else 0)), io.BytesIO())
            self.assertTrue(store.status()['stopped'])
            self.assertEqual(store.status()['buckets']['response']['unknown_bytes'], 100)

    def test_corrupted_sealed_read_fails_before_any_output(self):
        self.store.write('corrupt', 'response', b'original', case_ordinal=1)
        (self.root / 'items/corrupt/part').chmod(0o600)
        (self.root / 'items/corrupt/part').write_bytes(b'modified')
        service = stdio.StdioService(self.store)
        output = io.BytesIO()
        with self.assertRaisesRegex(ValueError, 'digest'):
            service.one(io.BytesIO(self.header(0, 'get', case=1, id='corrupt')), output)
        self.assertEqual(output.getvalue(), b'')
        self.assertEqual(self.store.status()['buckets']['bridge_receipt']['unknown_bytes'], stdio.ACK_BYTES)

    def test_output_failure_has_durable_ack_and_never_reopens(self):
        service = stdio.StdioService(self.store)
        class BrokenWriter:
            def write(self, raw):
                raise OSError('lost acknowledgement')
        with self.assertRaises(OSError):
            service.one(io.BytesIO(self.put(0, b'committed')), BrokenWriter())
        self.assertEqual(self.store.payload('dummy'), b'committed')
        self.assertTrue(json.loads(self.store.payload('stdio-session-ack-000000'))['result']['durable'])
        self.assertTrue(service.closed)
        self.assertTrue(self.store.status()['stopped'])

    def test_mutation_after_read_header_closes_before_successful_completion(self):
        original = b'x' * (bridge.CHUNK_BYTES + 1)
        self.store.write('changing', 'response', original)
        part = self.root / 'items/changing/part'
        service = stdio.StdioService(self.store)
        class ChangingWriter(io.BytesIO):
            changed = False
            def write(self, raw):
                if not self.changed:
                    self.changed = True
                    part.chmod(0o600)
                    part.write_bytes(b'y' * len(original))
                return super().write(raw)
        output = ChangingWriter()
        with self.assertRaisesRegex(ValueError, 'changed during output'):
            service.one(io.BytesIO(self.header(0, 'get', id='changing')), output)
        self.assertTrue(self.store.status()['stopped'])
        self.assertTrue(service.closed)

    def test_noncanonical_overlong_header_and_root_override_refused(self):
        for variant, packet in (
                ('noncanonical', b'{"schema": "x"}\n'),
                ('overlong', b'x' * (stdio.HEADER_BYTES + 1) + b'\n'),
                ('root', self.header(0, 'dispatch', command={'action': 'status', 'root': '/elsewhere'}))):
            store = bridge.Store.create(str(Path(self.temp.name) / variant))
            service = stdio.StdioService(store)
            with self.assertRaises(ValueError):
                service.one(io.BytesIO(packet), io.BytesIO())
            self.assertTrue(store.status()['stopped'])

    def test_explicit_close_and_bounded_metadata_dispatch(self):
        service = stdio.StdioService(self.store)
        output = io.BytesIO()
        service.serve(io.BytesIO(self.header(0, 'dispatch', command={'action': 'pending'}) +
                                 self.header(1, 'close')), output)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(rows[0]['result']['pending'], [])
        self.assertTrue(rows[1]['result']['closed'])
        self.assertTrue(service.closed)
        self.assertFalse(rows[1]['result']['execution_authorized'])

    def test_eof_without_close_permanently_stops_store(self):
        service = stdio.StdioService(self.store)
        with self.assertRaises(EOFError):
            service.serve(io.BytesIO(), io.BytesIO())
        self.assertTrue(self.store.status()['stopped'])

    def test_command_limit_stops_durably_before_extra_action(self):
        service = stdio.StdioService(self.store, commands=1)
        service.one(io.BytesIO(self.put(0, b'original')), io.BytesIO())
        with self.assertRaisesRegex(RuntimeError, 'count exhausted'):
            service.one(io.BytesIO(self.header(1, 'close')), io.BytesIO())
        self.assertTrue(service.closed)
        self.assertTrue(self.store.status()['stopped'])
        self.assertFalse((self.root / 'items/stdio-session-command-000001').exists())

    def test_foreign_timer_is_preserved_and_service_refused(self):
        service = stdio.StdioService(self.store)
        old = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, lambda *_: None)
        signal.setitimer(signal.ITIMER_REAL, 60)
        try:
            with self.assertRaises(RuntimeError):
                service.one(io.BytesIO(self.header(0, 'close')), io.BytesIO())
            remaining, interval = signal.getitimer(signal.ITIMER_REAL)
            self.assertGreater(remaining, 59)
            self.assertEqual(interval, 0)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)

    def test_actual_blocking_stdin_deadline_stops_and_retains_session(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_stdio.py'
        env = {**os.environ, 'PYTHONPATH': str(script.parent.parent / 'src')}
        child = subprocess.Popen([sys.executable, '-B', str(script), '--root', str(self.root),
                                  '--operation-seconds', '.03'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            child.wait(timeout=3)
            self.assertNotEqual(child.returncode, 0)
            self.assertTrue(self.store.status()['stopped'])
            self.assertTrue(json.loads(self.store.payload('stdio-session'))['automatic_retry'] is False)
        finally:
            child.kill() if child.poll() is None else None
            child.communicate(timeout=3)


if __name__ == '__main__':
    unittest.main()
