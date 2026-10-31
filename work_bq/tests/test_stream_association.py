"""No-RNG, no saved science/score input: exact mocked BP/BQ comparisons."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

P = Path(__file__).resolve().parents[1]/'stream_association.py'
SPEC = importlib.util.spec_from_file_location('bq_stream_tests', P)
bq = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bq)
bp = bq.load_bp()

CASE = {'case_id': 'A04', 'kind': 'association_broad',
        'truth': {'channel_scan0_at_row7p5': 264192.5, 'rate_index': 419,
                  'intrinsic_width': 1025, 'present_scans': list(range(6))}}


class MockStore:
    def __init__(self, on=(12,12,12), off=8, unsupported=None, legacy_off=None, many=False):
        self.on = dict(zip(bp.ON,on))
        self.off, self.unsupported = off, unsupported
        self.legacy_off = off if legacy_off is None else legacy_off
        self.results = []
        for scan in range(6):
            hits = {'current': [], 'legacy': []}
            if scan in bp.ON and self.on[scan] >= 10:
                for method in ('current','legacy'):
                    for center, width, stride in ((264192,1,1),(264194,9,2),(264200,33,8)):
                        hits[method].append({'source_scan':scan,'rate_index':419,
                                             'width':width,'stride':stride,'q':64,
                                             'center':center,'ESS':self.on[scan]})
            self.results.append({'hits':hits})
        if many:
            self.results[0]['hits']['current'] = [self.results[0]['hits']['current'][0]]*50001

    def points(self, method, scan, ri, width, centers):
        if scan == self.unsupported:
            return None
        value = self.on[scan] if scan in bp.ON else (self.legacy_off if method=='legacy' else self.off)
        return [float(value)]*len(centers)


def original(store,base):
    with patch.object(bp,'ScoreStore',side_effect=[store,base]):
        return bp.assess_case(['mock']*6,CASE,base_scan_dirs=['mock-base']*6)


class ExactComparatorTests(unittest.TestCase):
    def compare(self,store):
        baseline = MockStore(on=(1,1,1),off=0)
        expected = original(store,baseline)
        with tempfile.TemporaryDirectory() as directory:
            actual = bq._stream_stores(bp,store,baseline,CASE,directory)
            self.assertEqual(actual['status'],expected['status'])
            self.assertEqual(actual['gate_reasons'],expected['gate_reasons'])
            for key in ('case_id','kind','association_policy','current_flags','legacy_flags',
                        'current_truth_recovered','legacy_truth_recovered'):
                self.assertEqual(actual[key],expected[key])
            for method in ('current','legacy'):
                streamed = copy.deepcopy(actual['method_results'][method])
                reference = copy.deepcopy(expected['method_results'][method])
                receipt = streamed.pop('association_stream')
                associations = reference.pop('associations')
                self.assertEqual(streamed,reference)
                path = Path(directory)/receipt['path']
                with path.open() as f:
                    decoded = [json.loads(line) for line in f]
                self.assertEqual(decoded,associations)
                self.assertEqual(receipt['records'],len(associations))
                self.assertEqual(receipt['bytes'],path.stat().st_size)
                self.assertEqual(receipt['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertTrue(receipt['complete'])
        return actual

    def test_supported_off_veto_identical(self):
        r=self.compare(MockStore())
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['current_flags'],0)

    def test_supported_flag_fails_identically(self):
        r=self.compare(MockStore(off=4))
        self.assertEqual(r['status'],'FAIL')
        self.assertGreater(r['current_flags'],0)

    def test_supported_three_on_rejection_identical(self):
        r=self.compare(MockStore(on=(12,3,3),off=0))
        self.assertEqual(r['status'],'PASS')

    def test_unsupported_is_not_a_passing_rejection(self):
        r=self.compare(MockStore(unsupported=1))
        self.assertEqual(r['status'],'FAIL')
        self.assertEqual(r['method_results']['current']['association_counts']['UNSUPPORTED'],9)

    def test_current_and_legacy_have_independent_identical_counters(self):
        r=self.compare(MockStore(off=8,legacy_off=4))
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['current_flags'],0)
        self.assertEqual(r['legacy_flags'],9)

    def test_empty_source_catalogs_and_truth_gate_identical(self):
        r=self.compare(MockStore(on=(1,1,1),off=0))
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['method_results']['current']['source_ON_hits'],0)

    def test_exact_original_cap_before_any_forcing(self):
        store,base=MockStore(many=True),MockStore(on=(1,1,1),off=0)
        with self.assertRaisesRegex(ValueError,'Frozen association cap exceeded'):
            original(store,base)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Frozen association cap exceeded'):
                bq._stream_stores(bp,store,base,CASE,directory)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_other_case_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'restricted to A04'):
                bq._stream_stores(bp,MockStore(),MockStore(),{**CASE,'case_id':'A03'},directory)


class EvidenceTests(unittest.TestCase):
    def test_exclusive_stream_preserves_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.jsonl'
            path.write_text('preserve')
            with self.assertRaises(FileExistsError):
                bq.AssociationWriter(path)
            self.assertEqual(path.read_text(),'preserve')

    def test_pin_verification_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.bin'
            path.write_bytes(b'original')
            pins=[{'path':str(path),'bytes':8,'sha256':bq.sha(path)}]
            self.assertEqual(bq.verify_pins(pins),pins)
            path.write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError,'SHA differs'):
                bq.verify_pins(pins)

    def test_duplicate_and_symlink_pins_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.bin'
            path.write_bytes(b'x')
            pin={'path':str(path),'bytes':1,'sha256':bq.sha(path)}
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                bq.verify_pins([pin,pin])
            link=Path(directory)/'link.bin'
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                bq.verify_pins([{**pin,'path':str(link)}])


if __name__=='__main__':
    unittest.main()
