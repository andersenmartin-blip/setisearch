"""Known-answer protection for the three-row event contexts used by LS8O."""
import unittest
import numpy as np
from seti_repeater.cheops_image_pair import temporal_map, analyze


class ThreeRowAnswers(unittest.TestCase):
    def test_three_row_sum_and_guards_on_large_linear_background(self):
        time = (np.arange(31, dtype=float) - 14) * 60
        side = np.r_[np.arange(12), np.arange(19, 31)]
        event = np.array([14, 15, 16])
        for pulse in (.25, -.25, 19., -19.):
            cube = np.broadcast_to((4e8 + time)[:, None, None], (31, 2, 3)).copy()
            cube[event] += pulse
            cube[12:14] += 1e7; cube[17:19] -= 1e7
            result = temporal_map(time, cube, side, event)
            np.testing.assert_allclose(result, 3 * pulse, rtol=0, atol=1e-9)

    def test_signed_three_row_brightness_is_retained_without_false_closure(self):
        yy, xx = np.indices((101, 101))
        profile = 1e4 * np.exp(-((xx - 50) ** 2 + (yy - 50) ** 2) / 80)
        time = (np.arange(31, dtype=float) - 14) * 60
        side = np.r_[np.arange(12), np.arange(19, 31)]
        event = np.array([14, 15, 16])
        for sign, pulse in [('positive', .01), ('negative', -.01)]:
            cube = np.repeat((100 + profile)[None], 31, axis=0)
            cube[event] += pulse * profile
            result, maps = analyze(time, cube, cube, np.zeros((31, 101)), side, event, [50., 50.], sign)
            np.testing.assert_allclose(maps['COR'], 3 * pulse * profile, rtol=0, atol=1e-8)
            self.assertEqual(result['classification'], 'UNRESOLVED_WITHIN_FIXED_SCOPE')
            for convention in result['conventions'].values():
                self.assertTrue(convention['sign_matches_l2'])
                self.assertAlmostEqual(convention['fits']['COR']['brightness']['explained'], 1., places=10)


if __name__ == '__main__':
    unittest.main()
