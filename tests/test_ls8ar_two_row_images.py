"""Known answers for the first LS8AR two-exposure representative, before pixels."""
import unittest
import numpy as np
from seti_repeater.cheops_image_pair import temporal_map, analyze


class TwoRowAnswers(unittest.TestCase):
    def test_two_row_signed_sum_with_large_baseline_and_contaminated_guards(self):
        time = (np.arange(30, dtype=float) - 14) * 60.
        side = np.r_[np.arange(12), np.arange(18, 30)]
        event = np.array([14, 15])
        for pulse in (.25, -.25, 19., -19.):
            cube = np.broadcast_to((4e8 + time)[:, None, None], (30, 2, 3)).copy()
            cube[event] += pulse
            cube[12:14] += 1e7
            cube[16:18] -= 1e7
            np.testing.assert_allclose(temporal_map(time, cube, side, event),
                                       2 * pulse, rtol=0, atol=1e-7)

    def test_two_row_brightness_preserved_in_both_signs_and_conventions(self):
        yy, xx = np.indices((101, 101))
        profile = 1e4 * np.exp(-((xx - 50) ** 2 + (yy - 50) ** 2) / 80)
        time = (np.arange(30, dtype=float) - 14) * 60.
        side = np.r_[np.arange(12), np.arange(18, 30)]
        event = np.array([14, 15])
        for sign, pulse in [('positive', .01), ('negative', -.01)]:
            cube = np.repeat((100 + profile)[None], 30, axis=0)
            cube[event] += pulse * profile
            result, maps = analyze(time, cube, cube, np.zeros((30, 101)),
                                   side, event, [50., 50.], sign)
            np.testing.assert_allclose(maps['COR'], 2 * pulse * profile,
                                       rtol=0, atol=1e-8)
            self.assertEqual(result['classification'], 'UNRESOLVED_WITHIN_FIXED_SCOPE')
            for c in result['conventions'].values():
                self.assertTrue(c['sign_matches_l2'])
                self.assertAlmostEqual(c['fits']['COR']['brightness']['explained'],
                                       1., places=10)


if __name__ == '__main__':
    unittest.main()
