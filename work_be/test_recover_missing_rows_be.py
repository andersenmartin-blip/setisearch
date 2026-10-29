"""Synthetic end-to-end recovery tests. No original archive or decoder contact.

Run: python3 -m unittest discover -s work_be -p 'test_recover_missing_rows_be.py' -v
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest.mock import patch

import recover_missing_rows_be as be


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def write_npy(path, rows, channels):
    literal = repr({'descr': '<f4', 'fortran_order': False, 'shape': (16, channels)})
    padding = (16 - ((10 + len(literal) + 1) % 16)) % 16
    header = (literal + ' ' * padding + '\n').encode('latin1')
    path.write_bytes(b'\x93NUMPY\x01\x00' + struct.pack('<H', len(header)) + header + b''.join(rows))


class FakeBackend:
    """Receipts and bytes originate entirely from an explicit test fixture."""
    def __init__(self, plan, *, fail_at=None, row_mutation=None, repeat_mutation=None,
                 manifest_mutation=None, fail_recheck=False, fail_close=False):
        self.plan = plan
        self.fail_at = fail_at
        self.row_mutation = row_mutation
        self.repeat_mutation = repeat_mutation
        self.manifest_mutation = manifest_mutation
        self.fail_recheck = fail_recheck
        self.fail_close = fail_close
        self.calls = []
        self.prepared = False
        self.closed = False
        self.recheck_count = 0
        self.output = None
        self.source_pins = {}

    def prepare(self, output):
        self.calls.append(('prepare',))
        self.prepared = True
        self.output = output
        self.source_pins = {self.plan['prior_scan5_array']: be.sha(self.plan['prior_scan5_array'])}
        self.source_pins.update({proof['path']: proof['sha256'] for proof in self.plan['parent_array_proofs']})

    def http(self, a, raw, path, *, repeat=False, time_index=None):
        source = self.plan['source']
        r = {'scan': 5, 'archive_id': source['id'], 'url': source['url'], 'etag': source['etag'],
             'status': 206, 'attempts': 1, 'failed_attempts': [], 'start': a,
             'stop_inclusive': a + len(raw) - 1, 'bytes': len(raw), 'sha256': digest_bytes(raw),
             'content_range': f"bytes {a}-{a + len(raw) - 1}/{source['size']}",
             'kind': 'repeat' if repeat else 'hdf_io', 'receipt_relative_path': path,
             'payload_relative_path': path.replace('.json', '.bin')}
        if repeat:
            r['coordinate'] = {'phase': 'repeat', 'scan': 5, 'time_index': 7,
                               'channel_start': self.plan['channel_start']}
        return r

    def record(self, t):
        decoded = struct.pack('<' + 'f' * self.plan['channels'],
                              *[t * 10.0 + c for c in range(self.plan['channels'])])
        payload = b'P' + bytes([t]) + decoded
        a = 10000 + 128 * t
        raw_http = self.http(a, payload, f'fixture/scan5_row{t}.json')
        segment = {'output_offset': 0, 'length': len(payload), 'source_start': a,
                   'source_stop': a + len(payload) - 1, 'source_receipt': raw_http}
        source = self.plan['source']
        receipt = {'receipt_schema': be.SCHEMAS['BB' if t < 7 else 'BC' if t == 7 else 'BE'],
                   'status': 'DERIVED_FROM_VERIFIED_RANGES', 'scan': 5, 'time_index': t,
                   'archive_id': source['id'], 'url': source['url'], 'etag': source['etag'],
                   'start': a, 'stop_inclusive': a + len(payload) - 1, 'bytes': len(payload),
                   'sha256': digest_bytes(payload), 'coverage_segments': [segment],
                   'new_HTTP_whole_chunk_receipt_claimed': False,
                   'receipt_relative_path': f'fixture/derived/scan5_row{t}.json',
                   'payload_relative_path': f'fixture/derived/scan5_row{t}.bin'}
        return {'descriptor': {'byte_offset': a, 'size': len(payload), 'filter_mask': 0,
                               'chunk_offset': [t, 0, self.plan['channel_start']]},
                'payload': payload, 'decoded': decoded, 'receipt': receipt,
                'source_payloads': {raw_http['receipt_relative_path']: payload}}

    def read_row(self, t, allow_new):
        self.calls.append(('row', t, allow_new))
        if t == self.fail_at:
            raise OSError('Synthetic transport denial')
        record = self.record(t)
        if self.row_mutation:
            self.row_mutation(t, record)
        return record

    def repeat_row7(self, record):
        self.calls.append(('repeat', 7))
        raw = record['payload']
        r = self.http(record['receipt']['start'], raw, 'fixture/scan5_row7.repeat.json', repeat=True)
        value = {'payload': raw, 'receipt': r}
        if self.repeat_mutation:
            self.repeat_mutation(value)
        return value

    def recheck(self):
        self.calls.append(('recheck',))
        self.recheck_count += 1
        if self.fail_recheck:
            raise be.RecoveryError('Synthetic immutable input changed')
        for path, expected in self.source_pins.items():
            if be.sha(path) != expected:
                raise be.RecoveryError('Synthetic immutable input changed')

    def manifest(self, records, repeat, partial, canonical):
        self.calls.append(('manifest',))
        receipts = [{'scan': j, 'time_index': t, 'receipt_schema': be.SCHEMAS['BB']}
                    for j in range(5) for t in range(16)]
        receipts.extend([r['receipt'] for r in records])
        scans = [{'scan': proof['scan'], 'array_path': proof['path'],
                  'array_sha256': proof['sha256']} for proof in self.plan['parent_array_proofs']]
        scans.append({'scan': 5, 'array_path': str(canonical), 'array_sha256': be.sha(partial)})
        value = {'schema': 'HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1', 'target': 'HIP44295',
                 'primary_id': 65133, **be.COUNTS, 'scan5_prior_rows_reconstructed': 8,
                 'scan5_new_rows_decoded': 8, 'scans': scans, 'chunk_receipts': receipts,
                 'repeated_chunk_receipts': copy.deepcopy(self.plan['prior_repeat_receipts']) + [repeat['receipt']],
                 'scientific_coverage_credit': 0, 'candidate_assessment': None,
                 'detector_searches_executed': 0, 'execution_mode': 'SIMULATION',
                 'protocol_sha256': '0' * 64}
        if self.manifest_mutation:
            self.manifest_mutation(value)
        return value

    def close(self):
        self.calls.append(('close',))
        self.closed = True
        if self.fail_close:
            raise be.RecoveryError('Synthetic close failure')


class MissingEightRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seti_be_recovery_tests_')
        self.root = Path(self.temp.name)
        self.parent = self.root / 'parent_partial.npy'
        self.output = self.root / 'new_attempt'
        self.plan = {'channels': 4, 'channel_start': 179306496,
                     'source': {'id': 65143, 'url': 'https://example.invalid/synthetic.h5',
                                'etag': '"synthetic-etag"', 'size': 1000000},
                     'prior_scan5_array': str(self.parent), 'prior_row_reports': [],
                     'prior_valid_time_indices': list(range(8)), 'missing_time_indices': list(range(8, 16)),
                     'row_lineage': {'BB': 87, 'BC': 1, 'new': 8, 'total': 96}}
        fixture = FakeBackend(self.plan)
        records = [fixture.record(t) for t in range(8)]
        self.plan['prior_row_reports'] = [
            {'time_index': t, 'decoded_row_sha256': digest_bytes(record['decoded']),
             'compressed_sha256': digest_bytes(record['payload'])}
            for t, record in enumerate(records)]
        write_npy(self.parent, [r['decoded'] for r in records] + [b'\xA5' * 16] * 8, 4)
        self.plan['parent_array_proofs'] = []
        for j in range(5):
            path = self.root / f'parent_scan{j}.npy'
            path.write_bytes(self.parent.read_bytes())
            self.plan['parent_array_proofs'].append({'scan': j, 'path': str(path), 'sha256': be.sha(path)})
        self.plan['prior_repeat_receipts'] = [{'scan': j, 'lineage': 'BB_prior_repeat'} for j in range(5)]
        self.parent_before = self.parent.read_bytes()
        self.gate = {'authorized': True, 'mode': 'SIMULATION'}

    def tearDown(self):
        self.assertEqual(self.parent.read_bytes(), self.parent_before, 'Parent evidence changed')
        self.temp.cleanup()

    def execute(self, backend, gate=None, plan=None):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Real network attempted')):
            return be.execute(backend, plan or self.plan, self.output, self.gate if gate is None else gate)

    def assert_no_completion(self):
        self.assertFalse((self.output / 'data/scan5.npy').exists())
        self.assertFalse((self.output / 'SIMULATION_COMPLETE_BE.json').exists())
        self.assertFalse((self.output / 'ACQUISITION_COMPLETE_BE.json').exists())

    def test_happy_simulation_acquires_only_eight_and_has_simulation_marker(self):
        backend = FakeBackend(self.plan)
        result = self.execute(backend)
        self.assertEqual([c for c in backend.calls if c[0] == 'row'],
                         [('row', t, t >= 8) for t in range(16)])
        self.assertEqual([c for c in backend.calls if c[0] == 'repeat'], [('repeat', 7)])
        marker = json.loads(Path(result['marker']).read_text())
        self.assertEqual(marker['execution_mode'], 'SIMULATION')
        self.assertEqual(marker['new_native_rows'], 8)
        self.assertEqual(marker['inherited_native_rows'], 88)
        self.assertEqual(marker['scientific_coverage_credit'], 0)
        self.assertFalse((self.output / 'ACQUISITION_COMPLETE_BE.json').exists())
        self.assertTrue((self.output / 'data/scan5.npy.partial').exists())
        self.assertTrue(backend.closed)

    def test_missing_gate_never_prepares_backend(self):
        backend = FakeBackend(self.plan)
        with self.assertRaisesRegex(be.RecoveryError, 'Missing recovery authorization'):
            self.execute(backend, gate={})
        self.assertEqual(backend.calls, [])
        self.assertFalse(self.output.exists())

    def test_unknown_mode_never_prepares_backend(self):
        backend = FakeBackend(self.plan)
        with self.assertRaises(be.RecoveryError):
            self.execute(backend, gate={'authorized': True, 'mode': 'AUTO'})
        self.assertEqual(backend.calls, [])

    def test_stale_nine_missing_rows_never_prepares_backend(self):
        plan = copy.deepcopy(self.plan)
        plan['missing_time_indices'] = list(range(7, 16))
        backend = FakeBackend(plan)
        with self.assertRaisesRegex(be.RecoveryError, 'Only eight missing rows'):
            self.execute(backend, plan=plan)
        self.assertEqual(backend.calls, [])

    def test_stale_eighty_seven_plus_nine_lineage_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['row_lineage'] = {'BB': 87, 'BC': 0, 'new': 9, 'total': 96}
        backend = FakeBackend(plan)
        with self.assertRaisesRegex(be.RecoveryError, 'Stale recovery lineage'):
            self.execute(backend, plan=plan)
        self.assertEqual(backend.calls, [])

    def test_prior_row7_corruption_fails_before_new_rows(self):
        def mutate(t, r):
            if t == 7:
                r['decoded'] = b'!' + r['decoded'][1:]
        backend = FakeBackend(self.plan, row_mutation=mutate)
        with self.assertRaisesRegex(be.RecoveryError, 'Retained partial row differs'):
            self.execute(backend)
        self.assertFalse(any(c[0] == 'row' and c[1] >= 8 for c in backend.calls))
        self.assert_no_completion()

    def test_row8_failure_retains_only_eight_prior_rows(self):
        backend = FakeBackend(self.plan, fail_at=8)
        with self.assertRaises(OSError):
            self.execute(backend)
        state = json.loads((self.output / 'RECOVERY_FAILURE_BE.json').read_text())
        self.assertEqual(state['prior_rows_verified'], 8)
        self.assertEqual(state['new_rows_decoded'], 0)
        self.assertEqual([c for c in backend.calls if c[0] == 'row' and c[1] >= 8], [('row', 8, True)])
        self.assert_no_completion()

    def test_late_failure_preserves_four_new_rows_without_promoting(self):
        backend = FakeBackend(self.plan, fail_at=12)
        with self.assertRaises(OSError):
            self.execute(backend)
        state = json.loads((self.output / 'RECOVERY_FAILURE_BE.json').read_text())
        self.assertEqual(state['new_rows_decoded'], 4)
        self.assertFalse(state['row7_repeat_completed'])
        self.assert_no_completion()

    def test_wrong_new_etag_stops_after_first_attempt(self):
        def mutate(t, r):
            if t == 8:
                r['receipt']['coverage_segments'][0]['source_receipt']['etag'] = '"changed"'
        backend = FakeBackend(self.plan, row_mutation=mutate)
        with self.assertRaisesRegex(be.RecoveryError, 'HTTP source identity differs'):
            self.execute(backend)
        self.assertEqual([c for c in backend.calls if c[0] == 'row' and c[1] >= 8], [('row', 8, True)])
        self.assert_no_completion()

    def test_wrong_selected_descriptor_is_rejected(self):
        def mutate(t, r):
            if t == 8:
                r['descriptor']['chunk_offset'][2] += 1
        with self.assertRaisesRegex(be.RecoveryError, 'Selected descriptor differs'):
            self.execute(FakeBackend(self.plan, row_mutation=mutate))
        self.assert_no_completion()

    def test_gap_or_overlap_in_source_union_is_rejected(self):
        def mutate(t, r):
            if t == 8:
                r['receipt']['coverage_segments'][0]['output_offset'] = 1
        with self.assertRaisesRegex(be.RecoveryError, 'Derived union gap/overlap'):
            self.execute(FakeBackend(self.plan, row_mutation=mutate))
        self.assert_no_completion()

    def test_source_bytes_disagreeing_with_receipt_are_rejected(self):
        def mutate(t, r):
            if t == 8:
                key = next(iter(r['source_payloads']))
                raw = r['source_payloads'][key]
                r['source_payloads'][key] = b'!' + raw[1:]
        with self.assertRaisesRegex(be.RecoveryError, 'HTTP bytes/hash differ'):
            self.execute(FakeBackend(self.plan, row_mutation=mutate))
        self.assert_no_completion()

    def test_cached_row7_cannot_substitute_for_genuine_repeat(self):
        def mutate(r):
            r['receipt']['kind'] = 'hdf_io'
        with self.assertRaisesRegex(be.RecoveryError, 'HTTP repeat scope differs'):
            self.execute(FakeBackend(self.plan, repeat_mutation=mutate))
        self.assert_no_completion()

    def test_repeat_wrong_etag_is_rejected_without_promotion(self):
        def mutate(r):
            r['receipt']['etag'] = '"changed"'
        with self.assertRaisesRegex(be.RecoveryError, 'HTTP source identity differs'):
            self.execute(FakeBackend(self.plan, repeat_mutation=mutate))
        self.assert_no_completion()

    def test_repeat_must_cover_complete_original_row7_chunk(self):
        def mutate(r):
            raw = r['payload'][:-1]
            r['payload'] = raw
            receipt = r['receipt']
            receipt['stop_inclusive'] -= 1
            receipt['bytes'] -= 1
            receipt['sha256'] = digest_bytes(raw)
            receipt['content_range'] = f"bytes {receipt['start']}-{receipt['stop_inclusive']}/{self.plan['source']['size']}"
        with self.assertRaisesRegex(be.RecoveryError, 'Full genuine row7 repeat differs'):
            self.execute(FakeBackend(self.plan, repeat_mutation=mutate))
        self.assert_no_completion()

    def test_repeat_body_must_match_original_row7_chunk(self):
        def mutate(r):
            raw = b'!' + r['payload'][1:]
            r['payload'] = raw
            r['receipt']['sha256'] = digest_bytes(raw)
        with self.assertRaisesRegex(be.RecoveryError, 'Full genuine row7 repeat differs'):
            self.execute(FakeBackend(self.plan, repeat_mutation=mutate))
        self.assert_no_completion()

    def test_recheck_failure_cannot_promote_canonical(self):
        with self.assertRaisesRegex(be.RecoveryError, 'Synthetic immutable input changed'):
            self.execute(FakeBackend(self.plan, fail_recheck=True))
        self.assert_no_completion()

    def test_close_failure_cannot_publish_completion(self):
        with self.assertRaisesRegex(be.RecoveryError, 'Synthetic close failure'):
            self.execute(FakeBackend(self.plan, fail_close=True))
        self.assert_no_completion()

    def test_manifest_missing_parent_scan_fails_before_promotion(self):
        def mutate(m):
            m['scans'].pop(0)
        with self.assertRaisesRegex(be.RecoveryError, 'Six scans required'):
            self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
        self.assert_no_completion()

    def test_manifest_substituted_scan5_receipt_is_rejected(self):
        def mutate(m):
            m['chunk_receipts'] = copy.deepcopy(m['chunk_receipts'])
            m['chunk_receipts'][-1]['sha256'] = 'f' * 64
        with self.assertRaises(be.RecoveryError):
            self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
        self.assert_no_completion()

    def test_manifest_cannot_grant_scientific_credit(self):
        def mutate(m):
            m['scientific_coverage_credit'] = 1
        with self.assertRaisesRegex(be.RecoveryError, 'Acquisition cannot grant science credit'):
            self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
        self.assert_no_completion()

    def test_manifest_cannot_replace_inherited_repeat_receipts(self):
        def mutate(m):
            m['repeated_chunk_receipts'][0]['lineage'] = 'forged'
        with self.assertRaisesRegex(be.RecoveryError, 'Prior repeat receipts changed'):
            self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
        self.assert_no_completion()

    def test_manifest_parent_array_path_substitution_is_rejected(self):
        def mutate(m):
            m['scans'][0]['array_path'] = self.plan['parent_array_proofs'][1]['path']
        with self.assertRaises(be.RecoveryError):
            self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
        self.assert_no_completion()

    def test_parent_mutation_inside_manifest_callback_is_caught_before_promotion(self):
        parent = Path(self.plan['parent_array_proofs'][0]['path'])
        original = parent.read_bytes()
        def mutate(m):
            parent.write_bytes(b'!' + original[1:])
        try:
            with self.assertRaises(be.RecoveryError):
                self.execute(FakeBackend(self.plan, manifest_mutation=mutate))
            self.assert_no_completion()
        finally:
            parent.write_bytes(original)

    def test_existing_failed_output_cannot_be_restarted(self):
        self.output.mkdir()
        backend = FakeBackend(self.plan)
        with self.assertRaisesRegex(be.RecoveryError, 'No automatic restart'):
            self.execute(backend)
        self.assertEqual(backend.calls, [])


if __name__ == '__main__':
    unittest.main()
