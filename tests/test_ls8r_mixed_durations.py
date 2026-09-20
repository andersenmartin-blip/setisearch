"""Known-answer protection for LS8R's one- and two-stack event sums."""
import unittest
import numpy as np
from seti_repeater.cheops_image_pair import temporal_map, analyze


class MixedDurationAnswers(unittest.TestCase):
    def test_one_two_row_sums_and_guards_in_both_signs(self):
        for duration in (1, 2):
            n = 28 + duration; time = (np.arange(n, dtype=float) - 14) * 44.2
            side = np.r_[np.arange(12), np.arange(16 + duration, n)]
            event = np.arange(14, 14 + duration)
            for pulse in (.25, -.25, 19., -19.):
                cube = np.broadcast_to((4e8 + time)[:, None, None], (n, 2, 3)).copy()
                cube[event] += pulse
                cube[12:14] += 1e7; cube[14 + duration:16 + duration] -= 1e7
                np.testing.assert_allclose(temporal_map(time, cube, side, event),
                                           duration * pulse, rtol=0, atol=1e-7)

    def test_signed_brightness_retained_for_both_native_durations(self):
        yy, xx = np.indices((101, 101))
        profile = 1e4 * np.exp(-((xx - 50) ** 2 + (yy - 50) ** 2) / 80)
        for duration in (1, 2):
            n = 28 + duration; time = (np.arange(n, dtype=float) - 14) * 44.2
            side = np.r_[np.arange(12), np.arange(16 + duration, n)]
            event = np.arange(14, 14 + duration)
            for sign, pulse in [('positive', .01), ('negative', -.01)]:
                cube = np.repeat((100 + profile)[None], n, axis=0)
                cube[event] += pulse * profile
                result, maps = analyze(time, cube, cube, np.zeros((n, 101)), side, event, [50., 50.], sign)
                np.testing.assert_allclose(maps['COR'], duration * pulse * profile, rtol=0, atol=1e-8)
                self.assertEqual(result['classification'], 'UNRESOLVED_WITHIN_FIXED_SCOPE')
                for convention in result['conventions'].values():
                    self.assertTrue(convention['sign_matches_l2'])
                    self.assertAlmostEqual(convention['fits']['COR']['brightness']['explained'], 1., places=10)


if __name__ == '__main__':
    unittest.main()
