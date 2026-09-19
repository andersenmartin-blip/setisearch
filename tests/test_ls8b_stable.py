import unittest
import numpy as np
from seti_repeater.cheops_l2_stable import stable_score_window


class StableAnswers(unittest.TestCase):
    def test_large_constant_background_small_pulses(self):
        t = np.arange(80, dtype=float)/86400.
        for duration in (1, 2, 3):
            for pulse in (0., 1e-6, -1e-6, 10., -10.):
                flux = np.full(80, 400_000_000.)
                flux[35:35+duration] += pulse
                expected = duration*(flux[35]-400_000_000.)
                row = stable_score_window(t, flux, np.ones(80), np.zeros(80, int),
                                           np.zeros(80, int), 35, duration, 1.)
                self.assertAlmostEqual(row['excess_electrons'], expected, places=11)

    def test_original_raw_flux_noise_floor_survives_centering(self):
        t = np.arange(80, dtype=float)/86400.
        row = stable_score_window(t, np.full(80, 400_000_000.), np.full(80, 1e-10),
                                   np.zeros(80, int), np.zeros(80, int), 35, 1, 1.)
        self.assertAlmostEqual(row['sigma_electrons'], .0004, delta=1e-18)


if __name__ == '__main__':
    unittest.main()
