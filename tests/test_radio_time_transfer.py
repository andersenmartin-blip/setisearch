"""Independent scalar clock/Doppler oracles; no templates or detector controls."""
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
import unittest

from seti_repeater import time_transfer_radio as m
from seti_repeater.phase_domain_radio import C_M_S

ROOT = Path(__file__).resolve().parents[1]


def contract(): return json.loads((ROOT/"config/radio_phase_domain_20260927.json").read_text())
def study(): return json.loads((ROOT/"config/radio_time_transfer_20260927.json").read_text())
def parameters(**changes): return study()["cases"][0]["parameters"] | changes


def independent_E(M, e):
    # Monotonic bisection, independent of the Newton/residual implementation.
    M = math.remainder(M, 2*math.pi)
    lo, hi = M-e, M+e
    for _ in range(70):
        x = (lo+hi)/2
        if x-e*math.sin(x) > M: hi=x
        else: lo=x
    return (lo+hi)/2


class TimeTransferRisks(unittest.TestCase):
    def test_newton_solver_agrees_with_independent_monotonic_bisection(self):
        for M,e in ((-math.pi,.172), (-.7,.172), (0,.172), (2.9,.172), (2*math.pi+.1,.172), (.4,0)):
            self.assertAlmostEqual(m.eccentric_anomaly_scalar(M,e), independent_E(M,e), places=13)

    def test_retarded_solution_agrees_with_independent_fixed_point(self):
        p = parameters(); s = study()["reception_extent_seconds"]
        # Cartesian geometry and bisection in E; do not call source_state here.
        def z(t):
            E=independent_E(p["mean_anomaly_reference"]+2*math.pi*t/p["period_seconds"], p["eccentricity"])
            return -p["projected_axis_m"]*((math.cos(E)-p["eccentricity"])*math.sin(p["omega"])
                 + math.sqrt(1-p["eccentricity"]**2)*math.sin(E)*math.cos(p["omega"]))
        t=s
        for _ in range(12): t=s-(z(t)-z(0))/C_M_S
        solved=m.solve_emission_time(contract(),s,p)
        self.assertLess(abs(t-solved["emission_seconds"]), 2e-9)
        self.assertLess(abs(solved["arrival_residual_seconds"]), 2e-9)

    def test_negative_reception_offsets_and_origin_are_supported(self):
        p=parameters()
        for s in (-100.,0.,100.):
            out=m.solve_emission_time(contract(),s,p)
            self.assertLess(abs(out["arrival_residual_seconds"]),2e-9)
            if s==0: self.assertLess(abs(out["emission_seconds"]),2e-9)

    def test_face_on_has_no_Romer_delay_but_eccentric_transverse_term_survives(self):
        out=m.compare_scalar_models(contract(),1000.,parameters(projected_axis_m=0),1.5e9)
        self.assertLess(abs(out["emission_seconds"]-1000),2e-9)
        self.assertEqual(out["retarded_factors"]["coordinate_frequency_reciprocal"],1)
        self.assertGreater(abs(out["transverse_difference_hz"]),1e-4)

    def test_circular_transverse_factor_is_constant_after_normalization(self):
        p=parameters(eccentricity=0)
        out=m.compare_scalar_models(contract(),1000.,p,1.5e9)
        self.assertEqual(out["transverse_difference_hz"],0)
        c=contract();c["domain"]["eccentricity"][1]=0
        self.assertEqual(m.conditional_error_bounds(c,1000.,1.5e9)["normalized_transverse_bound_hz"],0)

    def test_constant_phase_offset_does_not_erase_variable_light_travel_delay(self):
        p=parameters();out=m.compare_scalar_models(contract(),1000.,p,1.5e9)
        self.assertGreater(abs(out["emission_seconds"]-1000),.01)
        self.assertGreater(abs(out["wrong_clock_difference_hz"]),.001)

    def test_inverse_derivative_matches_one_over_one_plus_beta(self):
        p=parameters();s=1000.;h=.1
        x=m.solve_emission_time(contract(),s,p)["emission_seconds"]
        low=m.solve_emission_time(contract(),s-h,p)["emission_seconds"]
        high=m.solve_emission_time(contract(),s+h,p)["emission_seconds"]
        numerical=(high-low)/(2*h)
        beta=m.source_state(x,p)["velocity_away_m_s"]/C_M_S
        self.assertAlmostEqual(numerical,1/(1+beta),places=8)

    def test_emitted_coordinate_and_proper_frequency_are_distinct(self):
        p=parameters();ref=m.source_state(0,p);cur=m.source_state(1000,p)
        out=m.normalized_factors(ref,cur)
        self.assertNotEqual(out["coordinate_frequency_reciprocal"],out["proper_frequency_relativistic"])
        self.assertEqual(m.normalized_factors(ref,ref)["proper_frequency_relativistic"],1)

    def test_reciprocal_minus_linear_identity_against_60_digit_decimal(self):
        with localcontext() as ctx:
            ctx.prec=60
            b0=Decimal('-0.0004');b1=Decimal('-0.00039');one=Decimal(1)
            exact=(one+b0)/(one+b1)-(one-b1)/(one-b0)
            algebra=(b1*b1-b0*b0)/((one+b1)*(one-b0))
            self.assertLess(abs(exact-algebra),Decimal('1e-58'))
            ref={"velocity_away_m_s":float(b0)*C_M_S,"speed_squared_m2_s2":(.00045*C_M_S)**2}
            cur={"velocity_away_m_s":float(b1)*C_M_S,"speed_squared_m2_s2":(.00044*C_M_S)**2}
            found=m.normalized_factors(ref,cur)
            diff=1.5e9*(found["coordinate_frequency_reciprocal"]-found["first_order_coordinate"])
            self.assertLess(abs(diff-float(exact)*1.5e9),5e-7)

    def test_four_frozen_endpoints_respect_separately_derived_bounds(self):
        c, cfg=contract(),study()
        bounds=m.conditional_error_bounds(c,cfg["reception_extent_seconds"],cfg["reference_hz"])
        mapping={"wrong_clock_difference_hz":"normalized_wrong_clock_bound_hz",
            "reciprocal_difference_hz":"normalized_reciprocal_vs_linear_bound_hz",
            "transverse_difference_hz":"normalized_transverse_bound_hz",
            "combined_emitter_difference_hz":"conditional_emitter_comparison_sum_hz"}
        for case in cfg["cases"]:
            out=m.compare_scalar_models(c,cfg["reception_extent_seconds"],case["parameters"],cfg["reference_hz"])
            self.assertLessEqual(abs(out["emission_seconds"]-cfg["reception_extent_seconds"]),bounds["variable_light_travel_delay_seconds"]+2e-9)
            for term,bound in mapping.items(): self.assertLessEqual(abs(out[term]),bounds[bound]+1e-6)
            self.assertLess(abs(sum(out[k] for k in list(mapping)[:3])-out["combined_emitter_difference_hz"]),1e-6)

    def test_zero_horizon_annuls_normalized_bounds_and_frequency_scaling(self):
        c=contract();z=m.conditional_error_bounds(c,0,1.5e9)
        self.assertEqual(z["conditional_emitter_comparison_sum_hz"],0)
        low=m.conditional_error_bounds(c,1000,1.5e9);high=m.conditional_error_bounds(c,1000,3e9)
        self.assertEqual(high["conditional_emitter_comparison_sum_hz"],2*low["conditional_emitter_comparison_sum_hz"])

    def test_complete_exposure_edges_not_only_midpoints_define_numeric_extent(self):
        rows=json.loads((ROOT/"results_radio_motion_2026-09-26/clock.json").read_text())["rows"]
        expected=max(abs(r["mid_offset_seconds"]+sign*r["duration_s"]/2) for r in rows for sign in (-1,1))
        self.assertEqual(expected,study()["reception_extent_seconds"])
        self.assertGreater(expected,max(abs(r["mid_offset_seconds"]) for r in rows))

    def test_conditional_sum_is_never_a_total_physical_certificate(self):
        out=m.conditional_error_bounds(contract(),1000,1.5e9)
        self.assertFalse(out["is_total_physical_error_bound"])
        self.assertIsNone(out["total_physical_error_bound_hz"])
        self.assertFalse(out["numeric_interval_certificate"])
        self.assertFalse(out["physical_model_qualified"])
        self.assertFalse(out["spectral_access_authorized"])

    def test_inconsistent_speed_and_nonfinite_states_rejected(self):
        valid={"velocity_away_m_s":1.,"speed_squared_m2_s2":4.}
        for changed in ({"velocity_away_m_s":3.}, {"velocity_away_m_s":math.nan},
                        {"speed_squared_m2_s2":-1.}, {"speed_squared_m2_s2":C_M_S**2}):
            with self.assertRaises(ValueError): m.normalized_factors(valid,valid|changed)

    def test_outside_domain_or_unbounded_solver_scope_rejected(self):
        for change in ({"period_seconds":1.}, {"projected_axis_m":1e20}, {"eccentricity":.3},
                       {"mean_anomaly_reference":math.inf}, {"omega":False}):
            with self.assertRaises(ValueError):m.solve_emission_time(contract(),100.,parameters(**change))
        with self.assertRaises(ValueError):m.eccentric_anomaly_scalar(1e20,.1)
        with self.assertRaises(ValueError):m.conditional_error_bounds(contract(),-1,1.5e9)


if __name__ == "__main__": unittest.main()
