"""Bounded format/integration fixtures, not a SETI test bank."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time
import unittest

import msgpack

from executor import guard, run_jobs
from fixture_worker import edges, same
from payload_store import (FORMAT, QuotaExceeded, digest_file, semantic_digest,
                           validate, verify_bundle, write_bundle)

ROOT = Path(sys.argv[1]).resolve()
ROOT.mkdir()
OBS = []


def job(records=1, fault=None, cap=2 * 1024**2, CPU=4):
    return {'records': records, 'fault': fault, 'payload_cap_bytes': cap,
            'CPU_s': CPU, 'wall_s': 1800 if CPU > 4 else 15}


class IntegrationTests(unittest.TestCase):
    def setUp(self): self.folder = ROOT / self.id().split('.')[-1]
    def observe(self, **value): OBS.append({'test': self.id().split('.')[-1], **value})

    def test_01_exact_edge_values_and_opaque_bytes(self):
        self.folder.mkdir()
        asset = self.folder / 'source.bin'; asset.write_bytes(bytes(range(256)) * 4)
        value = edges()
        before = semantic_digest(value)
        stored = write_bundle(self.folder / 'payload', value, {'array_bits.bin': asset}, 8192)
        restored, receipt = verify_bundle(self.folder / 'payload', cap=8192)
        same(restored, value)
        self.assertEqual((self.folder / 'payload/array_bits.bin').read_bytes(), asset.read_bytes())
        self.assertEqual(before, receipt['semantic_sha256'])
        self.assertNotEqual(struct.pack('>d', restored['negative_zero']),
                            struct.pack('>d', restored['positive_zero']))
        self.observe(stored=stored, verified=receipt, exact_bit_and_order_comparison=True)

    def test_02_full_retained_ON_record_shape_through_guard_and_verifier(self):
        state = run_jobs(self.folder, [job(3 * 4096 * 5, cap=16 * 1024**2, CPU=120)],
                         mode='ENGINEERING_FIXTURES_ONLY', CPU_envelope_s=240,
                         output_cap_bytes=24 * 1024**2)
        self.assertEqual(state['status'], 'COMPLETE_ENGINEERING_ONLY')
        self.assertTrue(state['jobs'][0]['accepted'])
        root = self.folder / 'job_0000'
        metrics = json.loads((root / 'PRODUCER_METRICS.json').read_text())
        verified = json.loads((root / 'VERIFICATION.json').read_text())
        self.assertEqual(verified['fixture_all_records_checked'], 61440)
        self.assertEqual(verified['fixture_OFF_receipts_checked'], 184320)
        self.assertEqual(verified['semantic_sha256'], metrics['input_semantic_sha256'])
        self.assertFalse(json.loads((root / 'ACCEPTED_ENGINEERING.json').read_text())['science_admission'])
        self.observe(metrics=metrics, verification=verified,
                     producer=state['jobs'][0]['producer'], verifier=state['jobs'][0]['verifier'])

    def test_03_quota_exhaustion_retains_partial_and_stops_next(self):
        state = run_jobs(self.folder, [job(cap=32768), job()], mode='ENGINEERING_FIXTURES_ONLY',
                         CPU_envelope_s=16, output_cap_bytes=8 * 1024**2)
        self.assertEqual(state['status'], 'STOPPED_RETAINED_NO_RETRY')
        self.assertEqual(state['unsubmitted'], [1])
        first = self.folder / 'job_0000'
        self.assertLessEqual(sum(p.stat().st_size for p in (first/'payload').iterdir()), 32768)
        self.assertFalse((first / 'ACCEPTED_ENGINEERING.json').exists())
        self.assertFalse((first / 'verifier').exists())
        self.assertFalse((self.folder / 'job_0001').exists())
        self.assertIn('QuotaExceeded', (first / 'producer/stderr.log').read_text())
        self.observe(state=state, partial_payload_retained=True)

    def test_04_modified_bytes_rejected_by_separate_verifier(self):
        state = run_jobs(self.folder, [job(fault='tamper'), job()],
                         mode='ENGINEERING_FIXTURES_ONLY', CPU_envelope_s=16,
                         output_cap_bytes=10 * 1024**2)
        self.assertTrue(state['jobs'][0]['producer']['resource_acceptance'])
        self.assertFalse(state['jobs'][0]['verifier']['resource_acceptance'])
        self.assertFalse(state['jobs'][0]['accepted'])
        self.assertEqual(state['unsubmitted'], [1])
        self.assertFalse((self.folder / 'job_0001').exists())
        self.assertFalse((self.folder / 'job_0000/ACCEPTED_ENGINEERING.json').exists())
        self.observe(state=state, modified_bytes_preserved=True)

    def test_05_CPU_stop_after_valid_payload_never_accepts_or_submits_next(self):
        state = run_jobs(self.folder, [job(fault='CPU_after_payload', CPU=3), job()],
                         mode='ENGINEERING_FIXTURES_ONLY', CPU_envelope_s=14,
                         output_cap_bytes=10 * 1024**2)
        first = self.folder / 'job_0000'
        self.assertTrue((first / 'payload/MANIFEST.json').exists())
        self.assertFalse(state['jobs'][0]['producer']['resource_acceptance'])
        self.assertTrue(state['jobs'][0]['producer']['watchdog_fired'])
        self.assertIsNone(state['jobs'][0]['verifier'])
        self.assertEqual(state['unsubmitted'], [1])
        self.assertFalse((first / 'ACCEPTED_ENGINEERING.json').exists())
        self.assertFalse((self.folder / 'job_0001').exists())
        self.observe(state=state, valid_payload_is_not_acceptance=True)

    def test_06_output_reservation_precedes_launch(self):
        state = run_jobs(self.folder, [job()], mode='ENGINEERING_FIXTURES_ONLY',
                         CPU_envelope_s=8, output_cap_bytes=8192)
        self.assertEqual(state['status'], 'STOPPED_OUTPUT_RESERVATION')
        self.assertEqual(state['unsubmitted'], [0]); self.assertEqual(state['jobs'], [])
        self.assertFalse((self.folder / 'job_0000').exists())
        self.observe(state=state)

    def test_07_unsupported_domain_is_not_coerced(self):
        cyclic = []; cyclic.append(cyclic)
        values = [float('nan'), float('inf'), 1 << 64, -(1 << 63)-1,
                  {1: 'nonstring key'}, b'bytes_not_a_JSON_scalar', (1, 2), cyclic]
        count = 0
        for value in values:
            with self.assertRaises((TypeError, ValueError)): validate(value)
            count += 1
        self.observe(rejected_without_coercion=count)

    def test_08_inventory_and_path_faults_retained(self):
        self.folder.mkdir()
        base = self.folder / 'reference'
        write_bundle(base, edges(), {}, 8192)
        results = []
        for fault in ('unlisted', 'truncated', 'unsafe_name', 'symlink'):
            bad = self.folder / fault; shutil.copytree(base, bad)
            if fault == 'unlisted': (bad / 'extra.bin').write_bytes(b'UNLISTED')
            elif fault == 'truncated':
                p = bad / 'output.msgpack.gz'; p.write_bytes(p.read_bytes()[:-8])
            elif fault == 'unsafe_name':
                p = bad / 'MANIFEST.json'; m = json.loads(p.read_text())
                m['members']['../outside'] = {'bytes': 0, 'sha256': '0' * 64}
                p.write_text(json.dumps(m))
            else: (bad / 'link').symlink_to('output.msgpack.gz')
            with self.assertRaises((ValueError, QuotaExceeded, EOFError, OSError)):
                verify_bundle(bad, cap=8192)
            results.append(fault)
        self.observe(faults_rejected_and_reference_preserved=results)

    def test_09_decoder_extensions_duplicate_keys_and_decompression_cap(self):
        self.folder.mkdir()
        cases = {
            'duplicate': b'\x82\xa1x\x01\xa1x\x02',
            'extension': msgpack.packb(msgpack.ExtType(7, b'opaque')),
            'decompression': msgpack.packb('a' * 4096)}
        for name, raw in cases.items():
            folder = self.folder / name; folder.mkdir()
            p = folder / 'output.msgpack.gz'; p.write_bytes(gzip.compress(raw, mtime=0))
            manifest = {'format': FORMAT, 'metadata': p.name, 'semantic_sha256': '0' * 64,
                        'members': {p.name: {'bytes': p.stat().st_size, 'sha256': digest_file(p)}}}
            (folder / 'MANIFEST.json').write_text(json.dumps(manifest))
            with self.assertRaises((ValueError, QuotaExceeded)):
                verify_bundle(folder, cap=8192, metadata_unpacked_cap=1024)
        self.observe(decoder_faults_retained=list(cases))

    def test_10_science_mode_and_attempt_reuse_rejected(self):
        with self.assertRaises(ValueError):
            run_jobs(self.folder, [], mode='SCIENCE', CPU_envelope_s=8, output_cap_bytes=8192)
        self.assertFalse(self.folder.exists())
        existing = ROOT / 'test_02_full_retained_ON_record_shape_through_guard_and_verifier'
        before = digest_file(existing / 'STATE.json')
        with self.assertRaises(FileExistsError):
            run_jobs(existing, [job()], mode='ENGINEERING_FIXTURES_ONLY',
                     CPU_envelope_s=8, output_cap_bytes=8 * 1024**2)
        self.assertEqual(digest_file(existing / 'STATE.json'), before)
        self.observe(science_mode_rejected=True, completed_attempt_unchanged=True)

    def test_11_CPU_reservation_for_both_phases_precedes_launch(self):
        state = run_jobs(self.folder, [job()], mode='ENGINEERING_FIXTURES_ONLY',
                         CPU_envelope_s=7.99, output_cap_bytes=8 * 1024**2)
        self.assertEqual(state['status'], 'STOPPED_CPU_RESERVATION')
        self.assertEqual(state['unsubmitted'], [0]); self.assertEqual(state['jobs'], [])
        self.assertFalse((self.folder / 'job_0000').exists())
        self.observe(state=state)


if __name__ == '__main__':
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests))
    guard.durable_json(ROOT / 'TEST_RESULT.json', {
        'status': 'PASS_ENGINEERING_ONLY' if result.wasSuccessful() else 'FAIL_ENGINEERING',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'wall_s': time.monotonic() - started, 'observations': OBS,
        'science_admission': False, 'new_scientific_cases_or_draws': 0,
        'new_telescope_bytes': 0})
    raise SystemExit(0 if result.wasSuccessful() else 1)
