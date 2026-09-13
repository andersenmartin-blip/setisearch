import unittest
import numpy as np

from seti_repeater.tess_joint_spatial import FitBank
from seti_repeater.tess_separation import rectangle_bank, exact_thresholds, threshold_counts


class SeparationTests(unittest.TestCase):
    def test_rectangles_use_pixel_coordinates_and_keep_partial_overlaps(self):
        coords = [[0, 0], [0, 2], [1, 1], [2, 2]]
        p, labels = rectangle_bank(coords, [3, 3], [[2, 2]])
        self.assertEqual(labels, ['rect2x2_0_0', 'rect2x2_0_1', 'rect2x2_1_0', 'rect2x2_1_1'])
        np.testing.assert_array_equal(p, [[1, 0, 1, 0], [0, 1, 1, 0], [0, 0, 1, 0], [0, 0, 1, 1]])

    def test_tied_thresholds_include_all_distinct_acceptance_sets(self):
        margins = np.array([-2., 1., 1., 10., 99.])
        eligible = np.array([True, True, True, True, False])
        cuts = exact_thresholds(margins, eligible)
        counts = threshold_counts(margins, eligible, cuts, [np.ones(5, bool)])[:, 0]
        self.assertEqual(counts.tolist(), [4, 3, 1, 1, 0])
        self.assertEqual(cuts[-1], np.nextafter(10., np.inf))

    def test_counts_respect_eligibility_and_masks(self):
        margins = [0., 3., 8., 9.]
        counts = threshold_counts(margins, [1, 0, 1, 1], [0., 8., 9., 10.],
                                  [[1, 1, 0, 0], [0, 0, 1, 1]])
        np.testing.assert_array_equal(counts, [[1, 2], [0, 2], [0, 1], [0, 0]])

    def test_no_eligible_cases(self):
        self.assertEqual(exact_thresholds([1., 2.], [False, False]).tolist(), [9.])

    def test_extended_bank_cannot_improve_signal_margin(self):
        c = np.eye(8)
        source = np.array([0., .05, .15, .3, .3, .15, .05, 0.])
        y = 200*source+3
        old = np.eye(8)
        broad = np.vstack([old, source])
        s = FitBank(c, [source], True).fit(y)['objective']
        a = FitBank(c, old, True).fit(y)['objective']-s
        b = FitBank(c, broad, True).fit(y)['objective']-s
        self.assertGreater(a, 9.)
        self.assertAlmostEqual(b, 0.)
        self.assertLessEqual(b, a)

    def test_positive_rescaling_of_nuisance_template_preserves_objective(self):
        y = np.array([1., 4., 8., 9., 8., 1., 0., 4.])
        p = np.array([0., 0., 1., 1., 1., 0., 0., 0.])
        f = FitBank(np.eye(8), [p], True).fit(y)
        g = FitBank(np.eye(8), [p/3], True).fit(y)
        self.assertAlmostEqual(f['objective'], g['objective'])


if __name__ == '__main__':
    unittest.main()
