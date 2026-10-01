import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from seti_repeater import native_v2_transport_contract_radio as contract
from seti_repeater.empty_null_radio import canonical
from test_radio_native_v2_transport_contract import client, persistence

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v2_compact_run_verifier.py'
SPEC = importlib.util.spec_from_file_location('compact_run_verifier', SCRIPT)
compact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compact)


class CompactRunVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='seti-compact-verifier-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def plan(self, count=1, mutate=None):
        cases = []; clients = []
        for ordinal in range(count):
            value = client(polls=0, source_reads=2)
            value['events'] = [{'source_case_id': 'fixed-offline-control/case%02d' % ordinal}]
            proof = persistence(value)
            if mutate: mutate(ordinal, value, proof)
            path = self.root / ('retained%02d.json' % ordinal)
            raw = canonical({'qualified': {'client': value, 'persistence': proof}}) + b'\n'
            path.write_bytes(raw)
            cases.append({'ordinal': ordinal, 'source_case_id': 'fixed-offline-control/case%02d' % ordinal,
                'source_path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                'client_peak_rss_bytes': 64 * 1024**2, 'other_host_receipt_bytes': 0,
                'other_host_receipt_allocated_bytes': 0})
            clients.append((value, proof))
        return {'schema': compact.PLAN_SCHEMA, 'run_id': 'fresh-compact-control', 'cases': cases}, clients

    def verifier(self, plan):
        return compact.CompactRunVerifier(self.root / 'verifier', plan)

    def test_eight_small_cases_match_unchanged_contract_accounting(self):
        plan, inputs = self.plan(count=8)
        old = contract.RunTranscript(); new = self.verifier(plan)
        for ordinal, (value, proof) in enumerate(inputs):
            old.append(ordinal, value, proof, client_peak_rss_bytes=plan['cases'][ordinal]['client_peak_rss_bytes'])
            new.append(ordinal)
            # Cumulative in-memory custody is only pinned references/counters.
            self.assertNotIn('request_json', canonical(new.cases).decode())
            self.assertNotIn('response_json', canonical(new.cases).decode())
        before = {Path(case['source_path']): Path(case['source_path']).read_bytes() for case in plan['cases']}
        receipt = new.finish(); full = old.receipt()
        self.assertEqual(receipt['status'], 'COMPONENT_COMPLETE')
        self.assertEqual(receipt['case_count'], 8)
        for field in ('calls', 'request_bytes', 'response_bytes', 'elapsed_seconds'):
            self.assertEqual(receipt[field], full[field])
        self.assertLess(len(canonical(receipt)), compact.SMALL_FILE_BYTES)
        self.assertFalse(receipt['runtime_resource_qualification_complete'])
        self.assertFalse(receipt['host_ledger_join_complete'])
        self.assertFalse(receipt['execution_authorized'])
        self.assertEqual(receipt['native_case_executions'], 0)
        for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)
        durable = json.loads((self.root / 'verifier/receipt.json').read_bytes())
        self.assertEqual(durable, json.loads(canonical(receipt)))
        with self.assertRaisesRegex(RuntimeError, 'no retry or resume'): new.append(8)
        with self.assertRaisesRegex(RuntimeError, 'no retry or resume'): new.finish()

    def test_complete_semantic_validators_reject_corrupt_retained_envelope(self):
        plan, _ = self.plan(mutate=lambda ordinal, value, proof: value['records'][0]['raw_result'].update(ok=False))
        new = self.verifier(plan)
        with self.assertRaisesRegex(ValueError, 'raw caller result'): new.append(0)
        self.assertTrue(new.stopped)
        self.assertEqual(new.cases, [])
        self.assertTrue((self.root / 'verifier/failure.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'no retry or resume'): new.append(0)

    def test_failed_tail_and_combined_elapsed_match_original_failures(self):
        for label in ('tail', 'elapsed'):
            with self.subTest(label=label), tempfile.TemporaryDirectory(dir=self.root) as directory:
                old_root = self.root; self.root = Path(directory)
                try:
                    def mutate(ordinal, value, proof):
                        if label == 'tail': proof['durable'] = False
                        else:
                            proof['shared_case_finished_at_epoch_ms'] = 601000
                            proof['shared_case_elapsed_seconds'] = 601
                    plan, inputs = self.plan(mutate=mutate)
                    value, proof = inputs[0]
                    with self.assertRaises(ValueError): contract.RunTranscript().append(0, value, proof, client_peak_rss_bytes=1)
                    new = self.verifier(plan)
                    with self.assertRaises(ValueError): new.append(0)
                    self.assertTrue(new.stopped)
                finally: self.root = old_root

    def test_raw_hash_or_file_identity_change_closes_final_readback(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        path = Path(plan['cases'][0]['source_path'])
        path.write_bytes(path.read_bytes().replace(b'fixed-offline-control', b'wrong-offline-control'))
        with self.assertRaisesRegex(ValueError, 'identity changed'): new.receipt()
        self.assertTrue(new.stopped)

    def test_same_bytes_replaced_inode_is_refused(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        path = Path(plan['cases'][0]['source_path']); raw = path.read_bytes()
        replacement = self.root / 'replacement.json'; replacement.write_bytes(raw)
        os.replace(replacement, path)
        with self.assertRaisesRegex(ValueError, 'identity changed'): new.receipt()

    def test_directory_replacement_cannot_redirect_custody(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        destination = self.root / 'verifier'; destination.rename(self.root / 'old-verifier')
        destination.mkdir()
        with self.assertRaisesRegex(ValueError, 'directory identity changed'): new.receipt()
        self.assertTrue(new.stopped)

    def test_tampered_compact_metadata_cannot_self_certify(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        path = self.root / 'verifier/case00.json'; path.chmod(0o600); path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'metadata identity or SHA256'): new.receipt()

    def test_original_hash_is_checked_before_semantic_acceptance(self):
        plan, _ = self.plan(); plan['cases'][0]['sha256'] = 'f' * 64; new = self.verifier(plan)
        with self.assertRaisesRegex(ValueError, 'SHA256 differs'): new.append(0)
        self.assertTrue(new.stopped)

    def test_duplicate_cases_and_original_storage_or_rss_caps_are_refused(self):
        plan, _ = self.plan(count=2)
        duplicate = copy.deepcopy(plan); duplicate['cases'][1]['sha256'] = duplicate['cases'][0]['sha256']
        with self.assertRaisesRegex(ValueError, 'cannot be relabeled'): compact.validate_plan(duplicate)
        for field, value in (('other_host_receipt_bytes', compact.CASE_STORAGE_BYTES),
                ('other_host_receipt_allocated_bytes', compact.CASE_STORAGE_BYTES),
                ('client_peak_rss_bytes', contract.RSS_BYTES + 1)):
            with self.subTest(field=field):
                changed = copy.deepcopy(plan); changed['cases'][0][field] = value
                with self.assertRaises(ValueError): compact.validate_plan(changed)

    def test_hardlinked_raw_receipt_is_refused(self):
        plan, _ = self.plan(); path = Path(plan['cases'][0]['source_path'])
        os.link(path, self.root / 'other-link.json')
        new = self.verifier(plan)
        with self.assertRaisesRegex(ValueError, 'Sole-link'): new.append(0)

    def test_symlink_raw_receipt_is_refused(self):
        plan, _ = self.plan(); path = Path(plan['cases'][0]['source_path'])
        target = self.root / 'symlink-target.json'; path.rename(target); path.symlink_to(target)
        new = self.verifier(plan)
        with self.assertRaises(OSError): new.append(0)
        self.assertTrue(new.stopped)

    def test_fifo_replacement_of_raw_or_metadata_is_rejected_without_a_writer(self):
        for kind in ('raw', 'metadata'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=self.root) as directory:
                original_root = self.root; self.root = Path(directory)
                try:
                    plan, _ = self.plan(); new = self.verifier(plan)
                    if kind == 'raw':
                        path = Path(plan['cases'][0]['source_path'])
                    else:
                        new.append(0); path = self.root / 'verifier/case00.json'
                    path.unlink(); os.mkfifo(path)
                    operation = (lambda: new.append(0)) if kind == 'raw' else new.receipt
                    with self.assertRaisesRegex(ValueError, 'Sole-link regular'): operation()
                    self.assertTrue(new.stopped)
                finally: self.root = original_root

    def test_partial_replay_never_claims_eight_cases_or_resource_qualification(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        receipt = new.finish()
        self.assertEqual(receipt['status'], 'INCOMPLETE')
        self.assertEqual(receipt['case_count'], 1)
        self.assertFalse(receipt['runtime_resource_qualification_complete'])
        self.assertEqual(receipt['original_limits']['process_rss_bytes'], 512 * 1024**2)
        self.assertEqual(receipt['original_limits']['case_host_receipt_bytes'], 192 * 1024**2)
        with self.assertRaises(FileExistsError): self.verifier(plan)

    def test_mutated_prospective_plan_closes_verifier(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        new.plan['cases'][0]['other_host_receipt_bytes'] = 1
        with self.assertRaisesRegex(ValueError, 'plan changed'): new.receipt()

    def test_unknown_local_storage_closes_verifier(self):
        plan, _ = self.plan(); new = self.verifier(plan); new.append(0)
        (self.root / 'verifier/unaccounted.bin').write_bytes(b'unaccounted')
        with self.assertRaisesRegex(ValueError, 'Unaccounted entry'): new.receipt()


if __name__ == '__main__':
    unittest.main()
