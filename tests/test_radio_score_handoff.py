"""New reconstruction, external-pin, durability and failure-boundary risks only."""
import copy
from dataclasses import replace
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import numpy as np
from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import score_handoff_radio as handoff
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native
from seti_repeater.detector_m43u import checked_vectors
from seti_repeater.injection_m43r import ScoreStore
from radio_score_handoff_fixture import fixture, reconstructed_with_changed_cell


class ScoreHandoffTests(unittest.TestCase):
    evidence = {}

    @classmethod
    def setUpClass(cls):
        cls.native_run, cls.legacy = fixture()
        cls.sealed = handoff.seal_native_store(cls.native_run, cls.legacy)
        cls.guarded = handoff.GuardedRun(cls.native_run.context, cls.native_run.sources)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'scores.bin'

    def save(self, **kwargs):
        return handoff.save_checkpoint(self.path, self.native_run, self.sealed,
            trusted_receipt_sha256=self.sealed.identity, **kwargs)

    def load(self, **kwargs):
        return handoff.load_checkpoint(self.path, kwargs.pop('run', self.native_run),
            trusted_receipt_sha256=kwargs.pop('pin', self.sealed.identity), **kwargs)

    def rewrite(self, receipt, payloads=None):
        payloads = self.sealed.payloads if payloads is None else payloads
        self.path.write_bytes(handoff.PREFIX.pack(handoff.MAGIC, len(receipt), sum(map(len, payloads)))
                             + receipt + b''.join(payloads))

    def test_01_legacy_reconstruction_accepts_stale_native_hash_but_guard_rejects(self):
        changed = reconstructed_with_changed_cell(self.legacy)
        self.native_run.validate_store(changed)
        values = checked_vectors(changed, 'on', 0, 1, self.native_run.context.grid)
        actual = native.array_hash(np.stack([changed.arrays['on', t, 1][0]
                                            for t in range(len(self.native_run.context.bank))]))
        retained = changed.provenance['native_caches'][0]['full_support_score_sha256']
        self.assertNotEqual(actual, retained)
        with self.assertRaisesRegex(ValueError, 'native cache score digest'):
            handoff.seal_native_store(self.native_run, changed)
        self.evidence['baseline_reconstruction'] = {
            'legacy_metadata_validation_accepted': True, 'legacy_checked_vectors_accepted': True,
            'new_boundary_rejected': True, 'retained_native_score_sha256': retained,
            'actual_changed_score_sha256': actual,
            'old_vector_id': self.legacy.expected_ids['on', 0, 1],
            'new_self_computed_vector_id': changed.expected_ids['on', 0, 1],
            'original_cell': float(self.legacy.arrays['on', 0, 1][0, 0]),
            'changed_cell': float(values[0, 0]), 'detector_or_calibration_executed': False,
            'published_result_corruption_established': False}

    def test_02_bit_exact_handoff_preserves_every_legacy_vector_identity(self):
        cells = 0
        for key in self.legacy.arrays:
            old, old_id = self.legacy.get(*key)
            new, new_id = self.sealed.get(*key)
            self.assertEqual(new_id, old_id)
            self.assertTrue(np.array_equal(old.view('<u4'), new.view('<u4')))
            self.assertFalse(new.flags.writeable)
            cells += new.size
        self.assertEqual(len(self.sealed.record['provenance']['native_caches']), 48)
        self.evidence['complete_reconciliation'] = {'vectors': len(self.sealed.arrays),
            'native_cache_records': 48, 'bit_exact_score_cells': cells,
            'receipt_sha256': self.sealed.identity, 'source_ids': self.native_run.source_ids,
            'context_sha256': self.native_run.context.identity,
            'payload_bytes': sum(map(len, self.sealed.payloads)),
            'receipt_bytes': len(self.sealed.receipt_json)}

    def test_03_native_cache_order_missing_extra_and_source_are_rejected(self):
        for fault in ('order', 'missing', 'extra', 'source'):
            p = copy.deepcopy(self.legacy.provenance)
            if fault == 'order': p['native_caches'].reverse()
            if fault == 'missing': p['native_caches'].pop()
            if fault == 'extra': p['native_caches'].append(p['native_caches'][0])
            if fault == 'source': p['native_caches'][0]['source_identity'] = '0' * 64
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                handoff.seal_native_store(self.native_run, ScoreStore(self.legacy.arrays, p))

    def test_04_vector_inventory_missing_extra_shape_dtype_and_nonfinite_fail(self):
        for fault in ('missing', 'extra', 'shape', 'dtype', 'nan'):
            a = dict(self.legacy.arrays)
            if fault == 'missing': a.pop(('off', 2, 129))
            if fault == 'extra': a['on', 3, 1] = a['on', 0, 1]
            if fault == 'shape': a['on', 0, 1] = a['on', 0, 1][:, :-1]
            if fault == 'dtype': a['on', 0, 1] = a['on', 0, 1].astype('<f8')
            if fault == 'nan':
                a['on', 0, 1] = a['on', 0, 1].copy(); a['on', 0, 1][0, 0] = np.nan
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                handoff.seal_native_store(self.native_run, ScoreStore(a, copy.deepcopy(self.legacy.provenance)))

    def test_05_mutable_run_source_ids_are_checked_against_actual_sources(self):
        run = copy.copy(self.native_run); run.source_ids = dict(run.source_ids)
        run.source_ids['epoch1_on'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source inventory'):
            handoff.seal_native_store(run, self.legacy)

    def test_06_snapshot_owns_immutable_bytes_and_detached_metadata(self):
        with self.assertRaises(TypeError): self.sealed.arrays['on', 0, 1] = np.zeros(1)
        with self.assertRaises(TypeError): self.sealed.expected_ids['on', 0, 1] = '0' * 64
        with self.assertRaises(ValueError): self.sealed.arrays['on', 0, 1].setflags(write=True)
        p = self.sealed.provenance; p['source_ids']['epoch1_on'] = '0' * 64
        self.assertEqual(self.sealed.provenance, self.legacy.provenance)
        self.guarded.validate_store(self.sealed)

    def test_07_guarded_consumers_reject_unsealed_store_before_detector_calls(self):
        with self.assertRaisesRegex(ValueError, 'sealed score store'):
            self.guarded.execute(self.legacy, None)
        with self.assertRaisesRegex(ValueError, 'sealed score store'):
            self.guarded.calibrate(self.legacy, shifts=None, minimum_shift_bins=0,
                reference_floor=0, quantile=0, rank_ceiling=0)

    def test_08_guarded_production_wraps_native_result_without_numeric_changes(self):
        with patch.object(pipeline.NativeRun, 'build_store', return_value=self.legacy) as produced:
            result = self.guarded.build_store()
        produced.assert_called_once_with()
        self.assertEqual(result, self.sealed)
        self.guarded.validate_store(result)

    def test_09_independent_reopen_preserves_all_bytes_and_metadata(self):
        confirmation = self.save()
        fresh = handoff.GuardedRun(self.native_run.context, dict(self.native_run.sources))
        restored = fresh.restore(self.path, trusted_receipt_sha256=self.sealed.identity)
        self.assertEqual(restored, self.sealed)
        self.assertFalse(confirmation['telescope_admission_issued'])
        self.evidence['checkpoint'] = {**confirmation, 'file_sha256': handoff.sha(self.path.read_bytes()),
            'fresh_run_reopen_identical': True, 'format': 'canonical receipt and uncompressed float32'}

    def test_10_wrong_external_pin_is_rejected_before_any_float_payload_decode(self):
        self.save()
        with patch.object(np, 'frombuffer', side_effect=AssertionError('payload decoded')):
            with self.assertRaisesRegex(ValueError, 'independent caller pin'):
                self.load(pin='0' * 64)

    def test_11_rewritten_self_consistent_receipt_cannot_replace_old_pin(self):
        record = self.sealed.record
        record['provenance']['native_caches'][0]['cache_identity'] = '0' * 64
        receipt = handoff.canonical(record)
        self.rewrite(receipt)
        self.assertNotEqual(handoff.sha(receipt), self.sealed.identity)
        with self.assertRaisesRegex(ValueError, 'independent caller pin'):
            self.load()

    def test_12_changed_float_bytes_rejected_despite_intact_receipt(self):
        self.save(); payload = bytearray(self.path.read_bytes()); payload[-1] ^= 1
        self.path.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, 'vector bytes'):
            self.load()

    def test_13_truncation_and_trailing_data_are_not_partial_success(self):
        self.save(); original = self.path.read_bytes()
        for cut in (0, 12, handoff.PREFIX.size, len(original) - 1, len(original) + 1):
            self.path.write_bytes(original[:cut] if cut <= len(original) else original + b'!')
            with self.subTest(bytes=cut), self.assertRaises(ValueError): self.load()

    def test_14_forged_lengths_version_and_caps_reject_before_payload_decode(self):
        for magic, receipt, payload in ((b'wrong', 1, 1), (handoff.MAGIC, 2**63, 1),
                (handoff.MAGIC, 1, 2**63), (handoff.MAGIC, 0, 0)):
            self.path.write_bytes(handoff.PREFIX.pack(magic, receipt, payload))
            with self.subTest(magic=magic, receipt=receipt), patch.object(np, 'frombuffer',
                    side_effect=AssertionError('payload decoded')):
                with self.assertRaisesRegex(ValueError, 'length, version or resource'): self.load()

    def test_15_wrong_context_rejected_even_with_correct_external_receipt_pin(self):
        self.save(); c = self.native_run.context
        other = pipeline.Context(scans=c.scans, factors=c.factor_contract.factors,
            grid=c.grid, window=c.window + '-different')
        with self.assertRaisesRegex(ValueError, 'context or layout'):
            self.load(run=pipeline.NativeRun(other, self.native_run.sources))

    def test_16_noncanonical_json_and_duplicate_keys_rejected(self):
        canonical = self.sealed.receipt_json
        for receipt in (b' ' + canonical, b'{"schema":"ignored",' + canonical[1:]):
            self.rewrite(receipt)
            with self.assertRaisesRegex(ValueError, 'context or layout'):
                self.load(pin=handoff.sha(receipt))

    def test_17_symlink_fifo_and_directory_are_not_checkpoint_files(self):
        other = self.path.parent / 'other'; other.write_bytes(b'not a checkpoint')
        self.path.symlink_to(other)
        with self.assertRaises(OSError): self.load()
        self.path.unlink(); os.mkfifo(self.path)
        with self.assertRaisesRegex(ValueError, 'regular immutable'): self.load()
        self.path.unlink(); self.path.mkdir()
        with self.assertRaisesRegex(ValueError, 'regular immutable'): self.load()

    def test_18_existing_checkpoint_never_overwritten(self):
        self.save(); before = self.path.read_bytes()
        with self.assertRaises(FileExistsError): self.save()
        self.assertEqual(before, self.path.read_bytes())

    def test_19_failure_before_install_returns_no_final_checkpoint(self):
        def fail(stage):
            if stage == 'temporary_fsynced': raise RuntimeError('before install')
        with self.assertRaisesRegex(RuntimeError, 'before install'): self.save(checkpoint=fail)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_20_lost_ack_after_install_recovers_only_by_explicit_pinned_read(self):
        def fail(stage):
            if stage == 'installed': raise RuntimeError('lost acknowledgement')
        with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'): self.save(checkpoint=fail)
        self.assertEqual(self.load(), self.sealed)
        with self.assertRaises(FileExistsError): self.save()

    def test_21_file_and_directory_fsync_failures_do_not_return_success(self):
        for failing_call in (1, 2):
            count = 0; real = os.fsync
            def fault(fd):
                nonlocal count
                count += 1
                if count == failing_call: raise OSError('fsync failure')
                return real(fd)
            with patch.object(os, 'fsync', side_effect=fault):
                with self.assertRaisesRegex(OSError, 'fsync failure'): self.save()
            if failing_call == 1: self.assertFalse(self.path.exists())
            else: self.assertEqual(self.load(), self.sealed)

    def test_22_competing_writers_have_one_install_winner(self):
        barrier = threading.Barrier(2, timeout=5)
        def write():
            try:
                self.save(checkpoint=lambda stage: barrier.wait() if stage == 'temporary_fsynced' else None)
                return 'confirmed'
            except FileExistsError: return 'refused-existing'
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: write(), range(2)))
        self.assertEqual(sorted(results), ['confirmed', 'refused-existing'])
        self.assertEqual(self.load(), self.sealed)
        self.evidence['concurrent_writers'] = results

    def test_23_process_crash_before_and_after_install_has_explicit_recovery(self):
        records = []
        for stage in ('temporary_fsynced', 'installed', 'directory_fsynced'):
            def child():
                self.save(checkpoint=lambda at: os._exit(73) if at == stage else None)
            process = multiprocessing.get_context('fork').Process(target=child)
            process.start(); process.join(5)
            if process.is_alive(): process.kill(); process.join(); self.fail('crash child timeout')
            self.assertEqual(process.exitcode, 73)
            exists = self.path.exists()
            self.assertEqual(exists, stage != 'temporary_fsynced')
            if exists: self.assertEqual(self.load(), self.sealed)
            records.append({'crash_stage': stage, 'exitcode': process.exitcode,
                'final_file_exists': exists, 'pinned_recovery_succeeded': exists,
                'power_loss_simulated': False})
            for path in self.path.parent.iterdir(): path.unlink()
        self.evidence['process_crashes'] = records

    def test_24_mutation_during_read_is_not_returned_as_valid(self):
        self.save(); real = os.fstat; count = 0
        def change(fd):
            nonlocal count
            count += 1
            if count == 3:
                with self.path.open('r+b') as other:
                    other.seek(-1, os.SEEK_END); value = other.read(1)
                    other.seek(-1, os.SEEK_END); other.write(bytes([value[0] ^ 1])); other.flush()
            return real(fd)
        with patch.object(os, 'fstat', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'changed during read'): self.load()

    def test_25_modeled_snapshot_capacity_fails_before_file_open(self):
        c = self.native_run.context
        extra = self.sealed.record['binding']['additional_modeled_array_bytes']
        small = pipeline.Context(scans=c.scans, factors=c.factor_contract.factors, grid=c.grid,
            window=c.window, memory_limit_bytes=self.native_run.modelled_bytes + extra - 1)
        run = pipeline.NativeRun(small, self.native_run.sources)
        with patch.object(os, 'open', side_effect=AssertionError('file opened')):
            with self.assertRaisesRegex(core.V0P6CapacityError, 'modeled buffer cap'):
                handoff.load_checkpoint(self.path, run, trusted_receipt_sha256=self.sealed.identity)

    def test_26_wrong_sealed_payload_and_native_inventory_are_rejected_by_consumer(self):
        p = list(self.sealed.payloads); b = bytearray(p[0]); b[0] ^= 1; p[0] = bytes(b)
        with self.assertRaisesRegex(ValueError, 'vector bytes'):
            self.guarded.validate_store(replace(self.sealed, payloads=tuple(p)))
        record = self.sealed.record; record['provenance']['native_caches'][0]['full_support_score_sha256'] = '0' * 64
        changed = replace(self.sealed, receipt_json=handoff.canonical(record))
        with self.assertRaises(ValueError): self.guarded.validate_store(changed)


if __name__ == '__main__':
    unittest.main()
