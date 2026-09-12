import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.light_sail_tess import qualify_injections
from seti_repeater.light_sail_tess_v2 import (
    eligibility, extended_trials, match_trial, pointing_delta, quality_mask, shifted_profile,
)

CFG = json.loads((Path(__file__).resolve().parents[1]/"config/ls7b_tess_l9859.json").read_text())


class TestTessCorrectionAware(unittest.TestCase):
    def test_flag_combinations_preserve_instrumental_exclusions(self):
        flags = np.array([0, 64, 1024, 1088, 4096, 4160, 16384, 32768, 512, 32, 8, 128, 65536])
        expected = np.array([True]*4 + [False]*9)
        np.testing.assert_array_equal(quality_mask(flags, np.ones(len(flags), bool), 1088), expected)
        self.assertFalse(quality_mask([64], [False], 1088)[0])

    def test_zero_anchors_returns_structured_failure(self):
        time = np.arange(2000)*20/86400
        good = np.arange(2000) % 100 != 0
        result, _, _ = eligibility(time, np.arange(2000), good, CFG)
        self.assertFalse(result["pass"])
        self.assertEqual(result["anchors"], [])

    def test_many_overlapping_indices_are_not_ten_backgrounds(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["qualification"].update(searchable_days_min=0, anchor_span_days_min=0)
        result, _, _ = eligibility(np.arange(420)*20/86400, np.arange(420), np.ones(420, bool), cfg)
        self.assertEqual(result["eligible_anchor_indices"], 20)
        self.assertFalse(result["gates"]["nonoverlapping_contexts"])
        self.assertFalse(result["pass"])

    def test_well_separated_time_selected_anchors(self):
        n = 40000
        result, _, searchable = eligibility(np.arange(n)*20/86400, np.arange(n), np.ones(n, bool), CFG)
        self.assertTrue(result["pass"])
        self.assertEqual(len(result["anchors"]), 10)
        self.assertEqual(int(searchable.sum()), n-120)
        self.assertTrue(all(b-a > 400 for a,b in zip(result["anchors"], result["anchors"][1:])))

    def test_shifted_profile_normalization_and_pointing_conservation(self):
        ap = np.zeros((5, 5), bool)
        ap[1:4, 1:4] = True
        p = np.zeros((5, 5))
        p[ap] = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1])/16
        moved = shifted_profile(p, ap, [.25, 0])
        self.assertAlmostEqual(moved.sum(), 1.)
        self.assertEqual(moved[~ap].sum(), 0.)
        self.assertFalse(np.allclose(moved, p))
        delta = pointing_delta(10000*p+10, [0, .2])
        self.assertAlmostEqual(delta.sum(), 0., places=8)
        self.assertGreater(np.abs(delta).sum(), 0.)

    def test_confounded_detection_is_identified(self):
        cfg = json.loads(json.dumps(CFG))
        seconds = (np.arange(401)-200)*20
        native = np.random.default_rng(721).normal(size=401)
        native[199:202] += 100
        best, confounded = match_trial(native, native.copy(), seconds, [0], 1, cfg)
        self.assertTrue(confounded)
        self.assertGreater(best["score"], 8)

    def test_base_and_new_matching_agree_and_extended_trials_run(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["injections"].update(anchors=1, amplitudes=[.01], phases_seconds=[0.], shapes=["box30"])
        ap = np.zeros((5, 5), bool)
        ap[1:4, 1:4] = True
        profile = np.zeros((5, 5))
        profile[ap] = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1])/16
        cube = np.random.default_rng(772).normal(scale=.2, size=(600, 5, 5)) + 10000*profile
        time = np.arange(600)*20/86400
        noise = [{"start": 0, "stop": 600, "sigma_e_per_s": 1.}]
        base = qualify_injections(cube, ap, time, noise, cfg)
        anchor = base[0]["native_index"]
        unchanged = base[-1]
        flux = cube[anchor-200:anchor+201, ap].sum(axis=1)
        seconds = (time[anchor-200:anchor+201]-time[anchor])*86400
        best, confounded = match_trial(flux, flux.copy(), seconds, [0], 1., cfg)
        self.assertEqual(best, unchanged["best"])
        self.assertEqual(confounded, unchanged["baseline_confounded"])
        extra = extended_trials(cube, ap, time, noise, [anchor], cfg)
        self.assertEqual(len(extra), 6)
        self.assertTrue(all(r["recovered"] for r in extra if r["kind"]=="off_profile"))
        self.assertFalse(any(r["accepted"] for r in extra if r["kind"]=="pointing"))


if __name__ == "__main__":
    unittest.main()
