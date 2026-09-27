"""New risks only: limit/reference loss, free-carrier coverage and partial bounds."""
import copy
from decimal import Decimal, localcontext
import math
import unittest

import numpy as np

from seti_repeater import motion_contract_radio as m
from seti_repeater.motion_radio import AU_M, DAY_S


def declared_solution():
    parameters = {name: {"value": value, "limit_flag": 0, "reference": "one-solution"}
                  for name, value in {"period": 5.77, "axis": .0634,
                      "eccentricity": .1, "omega": -10, "periastron_epoch": 2450000.}.items()}
    conventions = {"phase_policy": "all_phases", "time_scale": "TDB",
                   "omega_body": "stellar_reflex", "axis_definition": "planet_barycentric"}
    return parameters, conventions


class MetadataRisks(unittest.TestCase):
    def test_actual_upper_limit_and_mixed_model_inputs_refused(self):
        from radio_motion_contract import orbital_provenance
        audit = orbital_provenance()
        core = audit["central_orbit_audit_all_phases"]
        self.assertIn("eccentricity:not_declared_point_estimate", core["blockers"])
        self.assertIn("mixed_orbital_solutions", core["blockers"])
        self.assertEqual(len(core["references"]), 2)
        self.assertEqual(len(audit["central_orbit_audit_epoch_anchored"]["references"]), 3)
        self.assertFalse(audit["absolute_epoch_used_by_historical_bank"])
        self.assertEqual(audit["parameters"]["omega"]["reference"], "ROSENTHAL_ET_AL__2021")

    def test_missing_flag_cannot_be_defaulted_to_point(self):
        p, c = declared_solution()
        for flag in (None, 1, -1, False, "0"):
            with self.subTest(flag=flag):
                p["eccentricity"]["limit_flag"] = flag
                self.assertFalse(m.central_solution_audit(p, c)["metadata_consistent"])

    def test_one_reference_missing_cannot_disappear_from_mixed_check(self):
        p, c = declared_solution()
        del p["omega"]["reference"]
        self.assertIn("omega:reference_missing", m.central_solution_audit(p, c)["blockers"])

    def test_bjd_does_not_establish_time_scale(self):
        p, c = declared_solution()
        for scale in (None, "BJD", "JD"):
            c["time_scale"] = scale
            self.assertIn("time_scale_unresolved", m.central_solution_audit(p, c)["blockers"])

    def test_relative_axis_needs_mass_conversion(self):
        p, c = declared_solution()
        c["axis_definition"] = "relative"
        self.assertIn("relative_to_transmitter_axis_unresolved", m.central_solution_audit(p, c)["blockers"])

    def test_no_implicit_omega_body_or_180_degree_correction(self):
        p, c = declared_solution()
        original = copy.deepcopy(p)
        c["omega_body"] = None
        self.assertIn("omega_body_unresolved", m.central_solution_audit(p, c)["blockers"])
        self.assertEqual(p, original)

    def test_all_phase_policy_does_not_require_absolute_epoch(self):
        p, c = declared_solution()
        del p["periastron_epoch"]
        audit = m.central_solution_audit(p, c)
        self.assertTrue(audit["metadata_consistent"])
        self.assertFalse(audit["physical_model_qualified"])
        self.assertFalse(audit["spectral_access_authorized"])
        c["phase_policy"] = "epoch_anchored"
        self.assertIn("periastron_epoch:missing_or_nonfinite", m.central_solution_audit(p, c)["blockers"])

    def test_bad_numeric_parameters_refused(self):
        for name, value in (("period", 0), ("axis", -1), ("eccentricity", 1), ("omega", math.nan)):
            p, c = declared_solution()
            p[name]["value"] = value
            self.assertFalse(m.central_solution_audit(p, c)["metadata_consistent"])


class CarrierRisks(unittest.TestCase):
    def test_two_point_chebyshev_solution_and_active_pair(self):
        result = m.carrier_minimax([3, 10], [1, 2])
        self.assertAlmostEqual(result["carrier_hz"], 13/3, places=14)
        self.assertAlmostEqual(result["error_hz"], 4/3, places=14)
        self.assertEqual(set(result["active_pair_local_indices"]), {0, 1})

    def test_independent_decimal_feasibility_oracle_at_radio_frequency(self):
        y = [1500000000.125, 1500000311.5, 1500000661.75, 1500000237.0]
        g = [1.0, 1.00000012, 1.00000039, 1.00000005]
        result = m.carrier_minimax(y, g)
        # Independent interval-feasibility bisection, not the pairwise formula.
        with localcontext() as ctx:
            ctx.prec = 60
            dy, dg = [Decimal.from_float(v) for v in y], [Decimal.from_float(v) for v in g]
            lo, hi = Decimal(0), Decimal(10000)
            for _ in range(190):
                error = (lo+hi)/2
                feasible = max((v-error)/w for v, w in zip(dy, dg)) <= min((v+error)/w for v, w in zip(dy, dg))
                if feasible: hi = error
                else: lo = error
            self.assertLess(abs(result["error_hz"]-float(hi)), 2e-7)

    def test_free_carrier_improves_over_fixed_carrier(self):
        y, g = np.array([101., 103., 105.]), np.array([1., 1.01, 1.02])
        result = m.carrier_minimax(y, g)
        self.assertLess(result["error_hz"], float(np.max(abs(y-100*g))))
        # Arbitrary discrete candidates cannot beat the relaxed optimum.
        for q in (99., 100., 101., 102., 103.):
            self.assertLessEqual(result["error_hz"], float(np.max(abs(y-q*g)))+1e-12)

    def test_exact_template_and_single_row_have_zero_error(self):
        for y, g in (([8., 10., 16.], [1., 1.25, 2.]), ([123.], [2.])):
            self.assertEqual(m.carrier_minimax(y, g)["error_hz"], 0)

    def test_restriction_cannot_increase_best_fit_error(self):
        y, g = [10., 15., 9.], [1., 1.1, .9]
        whole = m.carrier_minimax(y, g)["error_hz"]
        self.assertLessEqual(m.carrier_minimax(y[:2], g[:2])["error_hz"], whole)

    def test_invalid_vectors_rejected(self):
        cases = [([], []), ([1], [0]), ([1], [-1]), ([1], [math.inf]),
                 ([math.nan], [1]), ([1, 2], [1]), ([[1]], [[1]]), ([0], [1])]
        for y, g in cases:
            with self.subTest(y=y, g=g), self.assertRaises(ValueError):
                m.carrier_minimax(y, g)


class BoundRisks(unittest.TestCase):
    def bounds(self, **updates):
        return m.kepler_domain_bounds(**(dict(period_days=5.77152, semi_major_axis_au=.0634,
            eccentricity_max=.172, integration_seconds=17.986224128, frequency_hz=1.5e9) | updates))

    def test_jerk_norm_bound_covers_analytic_circular_orbit(self):
        result = self.bounds(eccentricity_max=0)
        n, a = 2*math.pi/(5.77152*DAY_S), .0634*AU_M
        self.assertAlmostEqual(result["speed_m_s"]/(n*a), 1)
        self.assertAlmostEqual(result["acceleration_m_s2"]/(n*n*a), 1)
        # Operator-norm bound is twice the exact circular jerk norm.
        self.assertAlmostEqual(result["jerk_m_s3"]/(n**3*a), 2)

    def test_exposure_duration_squared_and_frequency_linear(self):
        base = self.bounds()["emitter_interpolation_bound_hz"]
        self.assertAlmostEqual(self.bounds(integration_seconds=2*17.986224128)["emitter_interpolation_bound_hz"], 4*base)
        self.assertAlmostEqual(self.bounds(frequency_hz=3e9)["emitter_interpolation_bound_hz"], 2*base)
        self.assertIsNone(self.bounds()["joint_probability_coverage"])
        self.assertFalse(self.bounds()["physical_model_qualified"])

    def test_nonphysical_bound_inputs_rejected(self):
        for changes in ({"eccentricity_max": 1}, {"period_days": math.nan},
                        {"integration_seconds": 0}, {"semi_major_axis_au": 1e6}):
            with self.assertRaises(ValueError): self.bounds(**changes)

    def test_missing_term_never_becomes_zero_or_partial_total(self):
        known = {"a": {"bound_hz": .01, "qualified": True, "scope": "s"}}
        result = m.accuracy_contract(known, ["a", "b"], 1., "s")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["total_bound_hz"])
        self.assertEqual(result["known_terms_hz"], {"a": .01})

    def test_scope_mismatch_invalid_and_unqualified_bounds_block(self):
        for changes in ({"scope": "emitter_only"}, {"bound_hz": None}, {"bound_hz": -1},
                        {"bound_hz": math.nan}, {"qualified": False}):
            term = {"bound_hz": .1, "qualified": True, "scope": "s"} | changes
            self.assertEqual(m.accuracy_contract({"a": term}, ["a"], 1., "s")["status"], "BLOCKED")

    def test_complete_mathematical_budget_still_cannot_authorize_science(self):
        term = {"bound_hz": .75, "qualified": True, "scope": "s"}
        result = m.accuracy_contract({"a": term}, ["a"], 1., "s")
        self.assertEqual(result["status"], "WITHIN_TOLERANCE")
        self.assertFalse(result["spectral_access_authorized"])
        self.assertEqual(m.accuracy_contract({"a": term}, ["a"], .5, "s")["status"], "EXCEEDS_TOLERANCE")


if __name__ == "__main__":
    unittest.main()
