"""Known-answer and boundary tests for the LS7C scientific changes."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater.light_sail_tess import pulse_shape
from seti_repeater.light_sail_tess_v2 import shifted_profile
from seti_repeater.light_sail_tess_v3 import (
    accounting, empirical_profile, matched_window, nuisance_pattern,
    run_anchor, spatial_diagnostic, spatial_model, strength_amplitude, trial_specs, weighted_fit,
)

CFG = json.loads((Path(__file__).resolve().parents[1]/"config/ls7c_tess_l9859.json").read_text())


class WeightedFitTests(unittest.TestCase):
    def test_heteroscedastic_fit_matches_independent_lstsq(self):
        rng = np.random.default_rng(823)
        p = np.exp(-np.arange(20)/4)
        v = np.linspace(1, 8, 20)**2
        y = 18*p+3+rng.normal(0, np.sqrt(v))
        design = np.column_stack([p, np.ones(20)])/np.sqrt(v)[:, None]
        expected = np.linalg.lstsq(design, y/np.sqrt(v), rcond=None)[0]
        result = weighted_fit(y, v, p)
        self.assertAlmostEqual(result["amplitude"], expected[0])
        self.assertAlmostEqual(result["background"], expected[1])
        self.assertAlmostEqual(result["chi2"], np.sum((y-expected[0]*p-expected[1])**2/v))

    def test_negative_source_hits_nonnegative_boundary(self):
        r = weighted_fit(-5*np.arange(8)+2, np.ones(8), np.arange(8))
        self.assertEqual(r["amplitude"], 0)
        self.assertEqual(r["chi2"], r["background_only_chi2"])

    def test_uniform_is_background_not_source(self):
        r = weighted_fit(np.full(9, 32.), np.ones(9), np.arange(9))
        self.assertEqual(r["amplitude_noise_score"], 0)
        self.assertEqual(r["chi2"], 0)

    def test_variance_rescaling_changes_noise_score_and_residual(self):
        y, p = np.array([3., 6., 11., 14.]), np.arange(4)
        a, b = [weighted_fit(y, np.ones(4)*scale, p) for scale in (1, 4)]
        self.assertAlmostEqual(a["amplitude"], b["amplitude"])
        self.assertAlmostEqual(a["amplitude_noise_score"], 2*b["amplitude_noise_score"])
        self.assertAlmostEqual(a["chi2"], 4*b["chi2"])

    def test_invalid_variance_is_error(self):
        with self.assertRaises(ValueError):
            weighted_fit(np.ones(3), [1, 0, 1], np.arange(3))


class SpatialTests(unittest.TestCase):
    def setUp(self):
        y, x = np.indices((9, 9))
        self.ap = (x-4)**2+(y-4)**2 <= 6
        image = 1000*np.exp(-((x-4.1)**2+(y-3.9)**2)/2)
        self.native = np.broadcast_to(image, (401, 9, 9)).copy()
        self.errors = np.full_like(self.native, 5.)
        self.profile = empirical_profile(image, self.ap)
        self.model = spatial_model(self.native, self.errors, self.ap, 199, 202, CFG)

    def test_star_pass_and_bright_pixel_reject(self):
        stellar = self.native.copy(); stellar[199:202] += 400*self.profile
        r = spatial_diagnostic(stellar, 199, 202, self.model, CFG)
        self.assertTrue(r["pass"], r)
        bad = self.native.copy(); bad[199:202, 4, 4] += 400
        r = spatial_diagnostic(bad, 199, 202, self.model, CFG)
        self.assertFalse(r["pass"])
        self.assertLess(r["nuisance_delta_chi2"], 0)

    def test_off_grid_diagonal_profile_and_uniform(self):
        injected = self.native.copy()
        injected[199:202] += 400*shifted_profile(self.profile, self.ap, [.2, -.2])
        self.assertTrue(spatial_diagnostic(injected, 199, 202, self.model, CFG)["pass"])
        injected = self.native.copy(); injected[199:202] += 80
        self.assertFalse(spatial_diagnostic(injected, 199, 202, self.model, CFG)["pass"])

    def test_no_sideband_jump_and_exact_variance_floor(self):
        native = self.native.copy(); native[207:262] += 100
        m = spatial_model(native, self.errors, self.ap, 199, 202, CFG)
        self.assertTrue(np.allclose(m["variance"], 25*(1/3+np.pi/220)))
        self.assertEqual(m["empirical_dominant_pixels"], 0)

    def test_central_injection_cannot_change_noise_or_reference(self):
        modified = self.native.copy(); modified[194:207] += 1e6
        m = spatial_model(modified, self.errors, self.ap, 199, 202, CFG)
        for key in ("reference", "variance", "star", "nuisance"):
            np.testing.assert_array_equal(m[key], self.model[key])

    def test_missing_aperture_error_and_short_context_fail(self):
        error = self.errors.copy(); error[:, 4, 4] = np.nan
        with self.assertRaises(ValueError):
            spatial_model(self.native, error, self.ap, 199, 202, CFG)
        with self.assertRaises(ValueError):
            spatial_model(self.native[:30], self.errors[:30], self.ap, 10, 13, CFG)


class TrialTests(unittest.TestCase):
    def test_fixed_case_counts_and_no_exact_shift_reuse(self):
        specs = trial_specs(CFG)
        self.assertEqual(len(specs), 73)
        self.assertEqual(len(specs)*10*2, 1460)
        self.assertEqual(sum(s["group"] == "fixed" for s in specs)*20, 240)
        self.assertEqual(sum(s["group"] == "matched" and s["kind"] in ("stellar", "off_profile") for s in specs)*20, 600)
        self.assertEqual(sum(s["group"] == "matched" and s["kind"] not in ("stellar", "off_profile") for s in specs)*20, 600)
        self.assertTrue(all(d not in CFG["spatial"]["fit_shifts_yx"] for d in CFG["strength_trials"]["signal_shifts_yx"]))

    def test_strength_matching_both_signs_and_fraction_cap(self):
        rng = np.random.default_rng(184)
        seconds = (np.arange(401)-200)*20.
        native = 20000+rng.normal(0, 50, 401)
        pulse, centers = pulse_shape(seconds, 10., "box30", 20.)
        for sign in (1, -1):
            a = strength_amplitude(native, pulse, seconds, centers, 50., 12., CFG, sign)
            self.assertTrue(a["matched"])
            b = matched_window(native+sign*a["amplitude_e_per_s"]*pulse, seconds, centers, 50., CFG, sign)
            self.assertAlmostEqual(b["score"], 12., places=4)
        cfg = copy.deepcopy(CFG); cfg["strength_trials"]["maximum_aperture_fraction"] = 1e-6
        self.assertFalse(strength_amplitude(native, pulse, seconds, centers, 50., 12., cfg)["matched"])

    def test_compact_control_preserves_aperture_normalization(self):
        ref = np.arange(81).reshape(9, 9)+10.
        ap = np.zeros((9, 9), dtype=bool); ap[3:6, 3:6] = True
        profile = empirical_profile(ref, ap)
        for kind in ("single_pixel", "block_2x2", "uniform", "pointing"):
            p, sign, norm = nuisance_pattern(kind, ref, profile, ap, [0., .2])
            self.assertAlmostEqual(p[ap].sum(), sign)
            self.assertGreater(norm, 0)

    def test_incomplete_ledger_cannot_qualify(self):
        result, gates = accounting([], CFG)
        self.assertEqual(result["total_trials"], 0)
        self.assertFalse(gates["complete_trial_count"])
        self.assertFalse(gates["stellar_8.5"])

    def test_complete_anchor_keeps_all_cases_and_matched_strengths(self):
        cfg = copy.deepcopy(CFG); cfg["injections"]["phases_seconds"] = [0.]
        y, x = np.indices((9, 9))
        image = 1000*np.exp(-((x-4.15)**2+(y-3.85)**2)/2)
        ap = (x-4)**2+(y-4)**2 <= 6
        rng = np.random.default_rng(7421)
        cube = image[None, :, :]+rng.normal(0, 5, (401, 9, 9))
        errors = np.full_like(cube, 5.)
        time = 2100+np.arange(401)*20/86400
        rows = run_anchor(cube, errors, ap, time, 200, 0, 5*np.sqrt(ap.sum()), cfg)
        self.assertEqual(len(rows), 73)
        self.assertEqual(len({r["trial_id"] for r in rows}), 73)
        self.assertTrue(all(r["strength_matched"] for r in rows if r["group"] == "matched"))
        self.assertTrue(all(not r["accepted"] for r in rows if r["kind"] in ("null", "uniform")))
        json.dumps(rows, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
