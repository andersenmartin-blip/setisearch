"""No-RNG deterministic unit checks for BP geometry and endpoint rules."""
import importlib.util
import math
from pathlib import Path
import unittest

import numpy as np

P = Path(__file__).resolve().parents[1]/'paired_search.py'
S = importlib.util.spec_from_file_location('bp_paired_tests', P)
p = importlib.util.module_from_spec(S)
S.loader.exec_module(p)


class FixedScores:
    def __init__(self, on=10.0, off=4.99, unsupported_scan=None, missing_on=None):
        self.on, self.off = on, off
        self.unsupported_scan, self.missing_on = unsupported_scan, missing_on

    def points(self, method, scan, ri, width, centers):
        if scan == self.unsupported_scan:
            return None
        v = self.on if scan in p.ON else self.off
        if scan == self.missing_on:
            v = 9.99
        return [v]*len(centers)


class GeometryTests(unittest.TestCase):
    def test_exact_rate_bank(self):
        self.assertEqual(len(p.RATES), 839)
        self.assertEqual(p.RATES[419], 0)
        np.testing.assert_array_equal(p.offsets_for(419), np.zeros(16, dtype=np.int32))
        np.testing.assert_array_equal(p.offsets_for(0), -p.offsets_for(838))
        self.assertEqual(p.offsets_for(838).tolist(), (-p.offsets_for(838)[::-1]).tolist())

    def test_quantized_propagation_and_original_dense_radius(self):
        for source in (0, 2, 4):
            for target in range(6):
                for width, stride in zip(p.WIDTHS, p.STRIDES):
                    g = p.forced_geometry(source, 264192, 838, width, target)
                    self.assertEqual(g['center'] % stride, 0)
                    self.assertLessEqual(abs(g['center']-g['physical_center']), stride/2)
                    if target in p.OFF:
                        expected = math.ceil(1+.5*(8/838)*abs(g['gap_seconds'])/abs(p.DF))+math.ceil(stride/2)
                        self.assertEqual(g['radius_channels'], expected)
                        self.assertTrue(all(abs(x-g['center']) <= expected for x in g['points']))

    def test_truth_selected_near_known_track(self):
        truth = {'channel_scan0_at_row7p5': 264192.5, 'rate_index': 0}
        candidates = p.truth_candidates(truth)
        self.assertTrue(candidates)
        self.assertEqual(set(c['width'] for c in candidates), {1,3,9,33})
        for c in candidates:
            self.assertEqual(c['source_scan'], 0)
            self.assertEqual(c['rate_index'], 0)
            self.assertLessEqual(abs(c['center']-264192.5), c['stride']/2+1)

    def test_midpoint_and_halfdt_conventions_not_conflated(self):
        rate = p.RATES[838]
        shift = rate*(.5*p.DT)/p.DF
        self.assertNotEqual(shift, 0)
        times = (np.arange(16)-7.5)*p.DT
        self.assertEqual(float(np.mean(times)), 0)


class EndpointTests(unittest.TestCase):
    def candidate(self):
        return {'source_scan': 0, 'center': 264192, 'rate_index': 419, 'width': 1}

    def test_on_inclusive_off_exclusive(self):
        self.assertTrue(p.force(FixedScores(), 'current', self.candidate())['flag'])
        r = p.force(FixedScores(off=5), 'current', self.candidate())
        self.assertEqual(r['status'], 'OFF_VETO')
        self.assertFalse(r['flag'])

    def test_single_on_not_enough(self):
        r = p.force(FixedScores(missing_on=2), 'current', self.candidate())
        self.assertEqual(r['status'], 'THREE_ON_FAIL')
        self.assertFalse(r['flag'])

    def test_unsupported_off_is_not_absence(self):
        r = p.force(FixedScores(unsupported_scan=1), 'current', self.candidate())
        self.assertEqual(r['status'], 'UNSUPPORTED')
        self.assertFalse(r['flag'])

    def test_each_on_can_source(self):
        for scan in (0,2,4):
            c = {**self.candidate(), 'source_scan': scan}
            self.assertTrue(p.force(FixedScores(), 'legacy', c)['flag'])

    def test_physical_q_and_stride_support(self):
        store = object.__new__(p.ScoreStore)
        store.arrays = [{p._key('current',419,9,64,'score'): np.ones(2048)} for _ in range(6)]
        self.assertEqual(store.points('current',0,419,9,[264192]), [1.0])
        self.assertIsNone(store.points('current',0,419,9,[264193]))
        self.assertIsNone(store.points('current',0,419,9,[128*4096]))
        self.assertIsNone(store.points('current',0,419,9,[65*4096]))


class OracleTests(unittest.TestCase):
    def test_independent_prefix_replays_staged_width_and_rows(self):
        y = ((np.arange(16*80).reshape(16,80) % 11)-5).astype(np.float32)
        off = np.arange(16,dtype=np.int32)%3-1
        reqs = [{'width':3,'offsets':off,'centers':np.array([30,50])}]
        prefix = p.independent_prefixes(y,reqs)
        box = p.M.legacy_centered_boxcar(y,3)
        for center in (30,50):
            expected = p.M.legacy_track_sum(box,off,center,center+1,1)[0]
            got = p.legacy_staged_oracle(y,prefix,off,center,3)
            self.assertEqual(expected.tobytes(),got.tobytes())

    def test_legacy_float32_loss_remains_a_failure(self):
        y=np.zeros((16,5),dtype=np.float32)
        y[:,2]=np.tile(np.array([2**30,1,-2**30,1],dtype=np.float32),4)
        off=np.zeros(16,dtype=np.int32)
        staged=p.legacy_staged_oracle(y,[{}]*16,off,2,1)
        scalar=math.fsum(p.scalar_terms(y,off,2,1))
        self.assertGreater(abs(float(staged)-scalar),5e-5)

    def test_vendor_functions_are_original_ast(self):
        self.assertEqual(p.M.verify_sources()['status'],'PASS_EXACT_VENDOR_AND_LEGACY_FUNCTION_AST')


if __name__ == '__main__':
    unittest.main()
