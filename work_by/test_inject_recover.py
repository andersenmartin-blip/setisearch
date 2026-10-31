"""Synthetic-only BY method checks. No observation arrays are opened."""
from pathlib import Path
import importlib.util
import json
import math
import time
import unittest
import numpy as np

P = Path(__file__).resolve().with_name('inject_recover.py')
spec = importlib.util.spec_from_file_location('by_synthetic_target', P)
by = importlib.util.module_from_spec(spec); spec.loader.exec_module(by)
SCOPE = {'scan': 0, 'dt_seconds': 18.253611008, 'df_hz': -2.7939677238464355,
         'tref_midpoint_mjd': 57660.61533451484, 'fch1_mhz': 2301.85546875}
RECORD = {'support_start': 253*4096, 'support_stop': 256*4096}
SHAPE = (16, 12288)

def case(rate=0., phase=0.):
    return {'true_center_native_at_scan0_midpoint': 254*4096+1536+phase,
            'true_drift_hz_s': rate}

class SyntheticTests(unittest.TestCase):
    def test_zero_drift_half_channel_mass(self):
        sparse = by.unit_injection(case(0., .5), SCOPE, SCOPE, RECORD, SHAPE)
        for channels, weights in sparse:
            self.assertEqual(channels.tolist(), [5632, 5633])
            self.assertEqual(weights.tolist(), [.5, .5])
            self.assertEqual(math.fsum(weights), 1.)

    def test_integrated_profile_against_midpoint_quadrature(self):
        c = case(1.0, .5)
        sparse = by.unit_injection(c, SCOPE, SCOPE, RECORD, SHAPE)
        row = 7
        center = c['true_center_native_at_scan0_midpoint']-RECORD['support_start'] + (row-7.5)*SCOPE['dt_seconds']/SCOPE['df_hz']
        half = abs(SCOPE['dt_seconds']/SCOPE['df_hz'])/2
        positions = center + (np.arange(100000, dtype=np.float64)+.5)/100000*(2*half)-half
        channels, weights = sparse[row]
        reference = np.array([np.maximum(1-np.abs(positions-j), 0).mean() for j in channels])
        self.assertLess(float(np.max(np.abs(reference-weights))), 1e-8)
        self.assertAlmostEqual(math.fsum(weights), 1., places=12)

    def test_signed_drift_and_exclusive_support(self):
        for rate in [-1., 1.]:
            sparse = by.unit_injection(case(rate), SCOPE, SCOPE, RECORD, SHAPE)
            means = [math.fsum((channels*weights).tolist()) for channels, weights in sparse]
            self.assertAlmostEqual(means[-1]-means[0], rate*15*SCOPE['dt_seconds']/SCOPE['df_hz'], places=9)
        c = case(); c['true_center_native_at_scan0_midpoint'] = RECORD['support_stop']+2
        with self.assertRaises(ValueError):
            by.unit_injection(c, SCOPE, SCOPE, RECORD, SHAPE)

    def test_fixed_design_and_inactive_exactness(self):
        cases = by.build_cases({})
        self.assertEqual(len(cases), 264)
        self.assertEqual(len({c['geometry'] for c in cases}), 24)
        self.assertEqual(sum(c['presence']=='ZERO_CONTROL' for c in cases), 24)
        y = np.random.default_rng(8731).normal(size=SHAPE).astype(np.float32)
        sparse = by.unit_injection(case(1.), SCOPE, SCOPE, RECORD, SHAPE)
        self.assertTrue(np.array_equal(by.inject(y, sparse, 16., False), y))
        self.assertTrue(np.array_equal(by.inject(y, sparse, 0., True), y))
        injected = by.inject(y, sparse, 16., True)
        for row, (channels, weights) in enumerate(sparse):
            expected = (y[row, channels].astype(np.float64)+16.*weights).astype(np.float32)
            self.assertTrue(np.array_equal(injected[row, channels], expected))

    def test_kernel_scalar_sums_and_missing_OFF_classification(self):
        kernel, classifier = by.load_components()
        y = np.random.default_rng(831264).normal(0, .3, size=SHAPE).astype(np.float32)
        sparse = by.unit_injection(case(1., .5), SCOPE, SCOPE, RECORD, SHAPE)
        y = by.inject(y, sparse, 16., True)
        offsets = np.rint((np.arange(16)-7.5)*SCOPE['dt_seconds']/SCOPE['df_hz']).astype(np.int32)
        centers = np.array([5624, 5632, 5640], dtype=np.int32)
        for width in by.WIDTHS:
            actual = kernel.tracks_selected(y, kernel.boxcars(y, width), offsets, centers, width)[0]
            reference = [math.fsum(float(y[t,int(c)+int(o)+d]) for t,o in enumerate(offsets)
                                  for d in range(-width//2+1, width//2+1)) for c in centers]
            self.assertLess(float(np.max(np.abs(actual-reference))), 5e-5)
        center = np.array([[12, 0, 12, 0, 12, np.nan], [12, 12, 12, 12, 12, np.nan]])
        valid = np.ones((2, 6), dtype=bool); valid[:, 5] = False
        result = classifier(center, center.copy(), valid)
        self.assertEqual(result['candidate_status'].tolist(), ['INCOMPLETE_OFF_COVERAGE', 'REJECTED_AVAILABLE_OFF'])
        self.assertFalse(result['complete_OFF_support'].any())


def benchmark_one_case():
    kernel, _ = by.load_components()
    rates = np.linspace(-4, 4, 839)
    offsets = np.rint(rates[:, None]*(np.arange(16)-7.5)[None, :]*SCOPE['dt_seconds']/SCOPE['df_hz']).astype(np.int32)
    y = np.random.default_rng(31102026).normal(size=SHAPE).astype(np.float32)
    start = time.monotonic(); count = 0
    for scan in range(5):
        for width, stride in zip(by.WIDTHS, by.STRIDES):
            prepared = kernel.boxcars(y, width)
            for ri in [313,314,315]:
                sums = kernel.tracks_grid(y, prepared, offsets[ri], 4096, 8192, stride, width)[0]
                median = np.median(sums); scale = 1.4826*np.median(np.abs(sums-median))
                by.local_peak_mask((sums-median)/scale, max(3, 2*math.ceil(width/stride)+1))
                count += len(sums)
    elapsed = time.monotonic()-start
    print(json.dumps({'synthetic_only': True, 'one_case_track_combinations': count,
                      'wall_seconds': elapsed, 'linear_264_case_extrapolation_seconds': elapsed*264,
                      'extrapolation_excludes_injection_hashing_and_forced_association': True}))

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    benchmark_one_case()
