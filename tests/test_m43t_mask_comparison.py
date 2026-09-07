"""Independent mask oracle, unchanged legacy pipeline and calibration binding."""
import unittest
from unittest.mock import patch
import numpy as np
from m43q_fixture import fixture
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43r as old
from seti_repeater import detector_m43t as new
from seti_repeater.mask_m43t import build_mask, bind_calibration, validate_binding


class MaskComparisonTests(unittest.TestCase):
    def test_independent_clipped_oracle_all_widths(self):
        rng = np.random.default_rng(430020)
        arrays = {w: rng.uniform(-2, 5, (3, 45)).astype('<f4') for w in core.M37_SPECTRAL_WIDTHS}
        for i, w in enumerate(arrays):
            arrays[w][i % 3, [0, 9, 22, 44]] = 12
        expected = np.zeros((3, 45), dtype=bool)
        for a in arrays.values():
            for e in range(3):
                for q in range(45):
                    if a[e, q] < 10:
                        continue
                    if all(a[other, k] < 3 for other in range(3) if other != e
                           for k in range(max(0, q-9), min(45, q+10))):
                        expected[e, max(0, q-9):min(45, q+10)] = True
        np.testing.assert_array_equal(build_mask(arrays.__getitem__, 'neighbor9'), expected)

    def test_threshold_distance_same_width_and_no_wrap(self):
        arrays = {w: np.zeros((3, 50), dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        arrays[1][0, 20] = 10
        arrays[1][1, 29] = 3
        self.assertFalse(build_mask(arrays.__getitem__, 'neighbor9').any())
        arrays[1][1, 29] = np.nextafter(np.float32(3), np.float32(0))
        self.assertTrue(build_mask(arrays.__getitem__, 'neighbor9')[0, 20])
        arrays[1][1, 30] = 3
        self.assertTrue(build_mask(arrays.__getitem__, 'neighbor9')[0, 20])
        arrays[3][1, 20] = 4
        self.assertTrue(build_mask(arrays.__getitem__, 'neighbor9')[0, 20])
        arrays[1][0, 0] = 10
        arrays[1][1, 49] = 4
        mask = build_mask(arrays.__getitem__, 'neighbor9')
        self.assertTrue(mask[0, 0])
        self.assertFalse(mask[0, 49])
        self.assertFalse(np.any(mask & ~build_mask(arrays.__getitem__, 'legacy')))

    def test_nonfinite_and_unknown_policy_rejected(self):
        a = np.zeros((3, 20), dtype='<f4'); a[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'finite'):
            build_mask(lambda w: a, 'neighbor9')
        with self.assertRaisesRegex(ValueError, 'unknown'):
            build_mask(lambda w: a, 'other')

    def test_legacy_pipeline_exact_and_policy_binding(self):
        kwargs, _ = fixture()
        args = {k: v for k, v in kwargs.items() if k not in ('receiver_factory', 'reference_floor', 'maximum_records')}
        ca, _ = old.calibrate(**args)
        cb, _ = new.calibrate(**args, mask_policy='legacy')
        np.testing.assert_array_equal(ca.null_maxima, cb.null_maxima)
        threshold = core.calibrated_threshold((ca,), expected_window_ids=(kwargs['window'],),
                                             reference_floor=50., quantile=1.)
        binding = bind_calibration(cb, threshold, 'legacy')
        fixed = {k: v for k, v in kwargs.items() if k not in ('shifts', 'minimum_shift_bins', 'reference_floor')}
        with patch.object(core, 'update_calibration', side_effect=AssertionError('no trial recalibration')):
            expected = old.execute(**fixed, calibration=ca, threshold=threshold)
            actual = new.execute(**fixed, calibration=cb, threshold=threshold,
                                 mask_policy='legacy', calibration_binding=binding)
        for k in expected:
            if k not in ('schema', 'purpose', 'result_sha256'):
                self.assertEqual(actual[k], expected[k], k)
        with self.assertRaisesRegex(ValueError, 'binding'):
            validate_binding(binding, 'neighbor9', cb, threshold)

    def test_neighbor_null_maxima_match_independent_rolls(self):
        kwargs, _ = fixture()
        args = {k: v for k, v in kwargs.items() if k not in ('receiver_factory', 'reference_floor', 'maximum_records')}
        acc, _ = new.calibrate(**args, mask_policy='neighbor9')
        grid = kwargs['grid']; reference = np.full(len(kwargs['shifts']), -np.inf)
        for t in range(len(kwargs['bank'])):
            arrays = {w: kwargs['store'].get('on', t, w)[0] for w in core.M37_SPECTRAL_WIDTHS}
            masks = build_mask(arrays.__getitem__, 'neighbor9')[:, grid.score_slice]
            for a in arrays.values():
                for j, row in enumerate(kwargs['shifts']):
                    vectors = np.stack([np.roll(a[e, grid.score_slice], int(row[e])) for e in range(3)])
                    mask = np.stack([np.roll(masks[e], int(row[e])) for e in range(3)])
                    for subset in core.M37_ACTIVITY_SUBSETS:
                        use = np.all((vectors[list(subset)] >= 3) & ~mask[list(subset)], axis=0)
                        summed = np.zeros(grid.score_bin_count, dtype='<f4')
                        for e in subset:
                            summed += vectors[e]
                        summed /= np.float32(np.sqrt(len(subset)))
                        reference[j] = max(reference[j], np.max(np.where(use, summed, -np.inf)))
        np.testing.assert_array_equal(acc.null_maxima, reference)

    def test_neighbor_rule_reaches_unchanged_physical_stages(self):
        kwargs, _ = fixture()
        args = {k: v for k, v in kwargs.items() if k not in ('receiver_factory', 'reference_floor', 'maximum_records')}
        cal, _ = new.calibrate(**args, mask_policy='neighbor9')
        threshold = core.calibrated_threshold((cal,), expected_window_ids=(kwargs['window'],),
                                             reference_floor=50., quantile=1.)
        fixed = {k: v for k, v in kwargs.items() if k not in ('shifts', 'minimum_shift_bins', 'reference_floor')}
        result = new.execute(**fixed, calibration=cal, threshold=threshold,
            mask_policy='neighbor9', calibration_binding=bind_calibration(cal, threshold, 'neighbor9'))
        rescued = [r for r in result['receiver_alias']['records'] if r['template_index'] == 1
                   and r['proxy_carrier_index'] == 200 and r['active_epochs_zero_based'] == [0, 1]]
        self.assertEqual(len(rescued), 1)
        self.assertEqual(rescued[0]['member_disposition'], 'pending_receiver_alias_evaluation')
        self.assertFalse(any(r['scientific_candidate'] for r in result['decisions']))


if __name__ == '__main__':
    unittest.main()
