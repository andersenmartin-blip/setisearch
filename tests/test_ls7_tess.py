"""Known-answer checks for the isolated LS7 optical pilot."""
import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.light_sail_tess import (
    good_segments, integrated_pulse, pixel_diagnostic, restore_cosmic_rays,
    screen, geometry_diagnostic, qualify_injections,
)

CFG = json.loads((Path(__file__).resolve().parents[1] / "config/ls7_tess_l9859.json").read_text())


class TestTessPilot(unittest.TestCase):
    def test_exposure_integration_and_phase(self):
        times = np.arange(-100, 120, 20)
        for phase in (0, 10, 3.4):
            pulse = integrated_pulse(times, phase, 30)
            self.assertAlmostEqual(pulse.sum() * 20, 30)
        np.testing.assert_allclose(integrated_pulse(np.array([-20, 0, 20]), 0, 30), [.25, 1, .25])

    def test_quality_id_and_time_gaps_split(self):
        t = np.arange(12) * 20 / 86400
        ids = np.arange(12)
        good = np.ones(12, bool)
        good[3] = False
        ids[6:] += 1
        t[9:] += 100 / 86400
        self.assertEqual(good_segments(t, ids, good, 20), [(0, 3), (4, 6), (6, 9), (9, 12)])

    def test_cosmic_mapping_duplicates_and_absent_cadence(self):
        records = {"CADENCENO": [30, 10, 30, 99], "RAWX": [101, 100, 101, 100],
                   "RAWY": [200, 201, 200, 200], "COSMIC_RAY": [2., 3., 4., 9.]}
        restored, info = restore_cosmic_rays(np.zeros((2, 2, 2)), [10, 30], records, 100, 200)
        self.assertEqual(restored[1, 0, 1], 6)
        self.assertEqual(restored[0, 1, 0], 3)
        self.assertEqual(restored.sum(), 9)
        self.assertEqual(info["absent_cadence_records"], 1)

    def test_cosmic_bad_coordinates_and_duplicate_ids_fail(self):
        records = {"CADENCENO": [1], "RAWX": [999], "RAWY": [0], "COSMIC_RAY": [1.]}
        with self.assertRaises(ValueError):
            restore_cosmic_rays(np.zeros((2, 2, 2)), [1, 2], records, 0, 0)
        with self.assertRaises(ValueError):
            restore_cosmic_rays(np.zeros((2, 2, 2)), [1, 1], records, 0, 0)

    def test_screen_positive_negative_edges_and_gaps(self):
        x = np.random.default_rng(710).normal(size=1000)
        x[200:203] += 20
        x[750:753] -= 20
        x[2:5] += 200
        x[499:502] += 200
        segments = [(0, 500), (502, 1000)]
        pos, _, overflow = screen(x, segments, CFG)
        neg, _, _ = screen(x, segments, CFG, sign=-1)
        self.assertFalse(overflow)
        self.assertEqual(len(pos), 1)
        self.assertEqual(len(neg), 1)
        self.assertLessEqual(pos[0]["start"], 202)
        self.assertGreater(pos[0]["stop"], 200)
        self.assertLessEqual(neg[0]["start"], 752)
        self.assertGreater(neg[0]["stop"], 750)

    def test_spatial_star_passes_pixel_and_uniform_fail(self):
        aperture = np.zeros((5, 5), bool)
        aperture[1:4, 1:4] = True
        profile = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], float)
        cube = np.ones((200, 5, 5)) * 10
        cube[:, aperture] = profile.ravel() * 100
        stellar = cube.copy()
        stellar[99:102, 1:4, 1:4] += profile * 10
        cosmic = cube.copy()
        cosmic[99:102, 2, 2] += 160
        uniform = cube.copy()
        uniform[99:102] += 20
        for data, expected in [(stellar, True), (cosmic, False), (uniform, False)]:
            result = pixel_diagnostic(data, aperture, 99, 102, CFG["morphology"])
            self.assertEqual(result["pass"], expected, result)

    def test_geometry_uses_bjd_reference(self):
        geometry = {"stellar_radius_solar": 1., "planets": [
            {"name": "a", "a_au": 1., "period_days": 4., "t0_bjd_tdb": 2457000.},
            {"name": "b", "a_au": 2., "period_days": 4., "t0_bjd_tdb": 2457000.}]}
        values = geometry_diagnostic(np.array([2457000., 2457001.]), geometry)["a-b"]
        np.testing.assert_allclose(values, [0, 1 / 0.00465047], atol=1e-8)

    def test_injection_end_to_end_noiseless_profile_noisy_flux(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["injections"].update(anchors=1, amplitudes=[.01], phases_seconds=[0.], shapes=["box30"])
        aperture = np.zeros((5, 5), bool)
        aperture[1:4, 1:4] = True
        profile = np.zeros((5, 5))
        profile[aperture] = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1]) / 16
        cube = np.random.default_rng(771).normal(scale=.2, size=(600, 5, 5)) + profile * 10000
        noise = [{"start": 0, "stop": 600, "sigma_e_per_s": 1.0}]
        rows = qualify_injections(cube, aperture, np.arange(600) * 20 / 86400, noise, cfg)
        self.assertTrue(rows[0]["recovered"])
        self.assertFalse(rows[1]["recovered"])
        self.assertFalse(rows[2]["recovered"])
        self.assertFalse(rows[3]["recovered"])


if __name__ == "__main__":
    unittest.main()
