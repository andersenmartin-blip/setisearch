"""Coverage calculus and resource-count risks, without constructing a grid."""
import copy
import json
import math
from pathlib import Path
import unittest

from seti_repeater import motion_covering_radio as m
from seti_repeater import time_transfer_radio as time_model
from seti_repeater.phase_domain_radio import AU_M
from radio_covering_oracle import Dual, sin, cos, scalar_derivatives

ROOT=Path(__file__).resolve().parents[1]
def contract():return json.loads((ROOT/"config/radio_phase_domain_20260927.json").read_text())
def study():return json.loads((ROOT/"config/radio_motion_covering_20260927.json").read_text())
def envelope():
    s=study();return m.sensitivity_envelope(contract(),s["reception_extent_seconds"],s["reference_hz"])
def scalar_parameters(x):
    p,a,projection,e,M,w=x
    return {"period_seconds":p*86400,"emitter_axis_m":a*AU_M,"projected_axis_m":a*AU_M*projection,
            "eccentricity":e,"mean_anomaly_reference":M,"omega":w}


class CoveringRisks(unittest.TestCase):
    def test_independent_dual_arithmetic_known_transcendental_identity(self):
        x=Dual(.7,(1,0,0,0,0,0));y=sin(x)*sin(x)+cos(x)*cos(x)
        self.assertAlmostEqual(y.value,1,places=14)
        self.assertAlmostEqual(y.derivative[0],0,places=14)
        z=(x*x+2*x+3)/(x+1)
        expected=1-2/(1+.7)**2
        self.assertAlmostEqual(z.derivative[0],expected,places=14)

    def test_two_independent_oracle_gradients_and_times_respect_envelope(self):
        cfg=study();env=envelope()
        for point in cfg["oracle_points"]:
            out=scalar_derivatives(point,cfg["reception_extent_seconds"],cfg["reference_hz"])
            self.assertLess(abs(out["arrival_residual_seconds"]),1e-9)
            for i,name in enumerate(m.PARAMETERS):
                bound=env["parameters"][name]
                self.assertLessEqual(abs(out["frequency_derivatives_hz_per_unit"][i]),bound["proper_frequency_lipschitz_hz_per_unit"])
                self.assertLessEqual(abs(out["emission_time_derivatives_seconds_per_unit"][i]),bound["implicit_source_time_derivative_seconds_per_unit"])

    def test_oracle_endpoint_values_match_separate_bracketed_solver(self):
        cfg=study()
        for point in cfg["oracle_points"]:
            out=scalar_derivatives(point,cfg["reception_extent_seconds"],cfg["reference_hz"])
            other=time_model.compare_scalar_models(contract(),cfg["reception_extent_seconds"],scalar_parameters(point),cfg["reference_hz"])
            self.assertLess(abs(out["emission_seconds"]-other["emission_seconds"]),2e-9)
            self.assertLess(abs(out["frequency_hz"]-cfg["reference_hz"]*other["retarded_factors"]["proper_frequency_relativistic"]),1e-6)

    def test_implicit_derivatives_against_separate_solver_finite_differences(self):
        cfg=study();point=cfg["oracle_points"][0];T=cfg["reception_extent_seconds"]
        oracle=scalar_derivatives(point,T,cfg["reference_hz"])
        steps=[1e-6,1e-6,1e-5,1e-5,1e-5,1e-5]
        for i,h in enumerate(steps):
            low,high=point.copy(),point.copy();low[i]-=h;high[i]+=h
            a=time_model.solve_emission_time(contract(),T,scalar_parameters(low))["emission_seconds"]
            b=time_model.solve_emission_time(contract(),T,scalar_parameters(high))["emission_seconds"]
            expected=oracle["emission_time_derivatives_seconds_per_unit"][i]
            self.assertLess(abs((b-a)/(2*h)-expected),max(2e-4,abs(expected)*.001))

    def test_normalization_annuls_all_parameter_derivatives_at_reference(self):
        cfg=study();out=scalar_derivatives(cfg["oracle_points"][0],0,cfg["reference_hz"])
        self.assertEqual(out["frequency_hz"],cfg["reference_hz"])
        self.assertLess(max(abs(v) for v in out["frequency_derivatives_hz_per_unit"]),1e-6)
        self.assertLess(max(abs(v) for v in out["emission_time_derivatives_seconds_per_unit"]),1e-10)

    def test_circular_phase_orientation_derivatives_are_degenerate(self):
        cfg=study();x=cfg["oracle_points"][0].copy();x[3]=0
        out=scalar_derivatives(x,cfg["reception_extent_seconds"],cfg["reference_hz"])
        self.assertAlmostEqual(out["frequency_derivatives_hz_per_unit"][4],out["frequency_derivatives_hz_per_unit"][5],places=7)

    def test_circle_boundary_distance_and_same_track_have_no_artificial_jump(self):
        self.assertAlmostEqual(m.circular_distance(.01,2*math.pi-.01),.02,places=14)
        self.assertAlmostEqual(m.circular_distance(-math.pi,math.pi),0,places=14)
        cfg=study();x=cfg["oracle_points"][0].copy();shift=x.copy();shift[4]+=2*math.pi
        a=scalar_derivatives(x,cfg["reception_extent_seconds"],cfg["reference_hz"])
        b=scalar_derivatives(shift,cfg["reception_extent_seconds"],cfg["reference_hz"])
        self.assertLess(abs(a["frequency_hz"]-b["frequency_hz"]),1e-6)
        for da,db in zip(a["frequency_derivatives_hz_per_unit"],b["frequency_derivatives_hz_per_unit"]):
            self.assertLess(abs(da-db),max(1e-6,abs(da)*1e-9))

    def test_sufficient_cell_radii_and_integer_product_not_a_lower_bound(self):
        cfg=study();out=m.sufficient_cover_count(envelope(),cfg["reporting_center_tolerance_hz"],96)
        self.assertLessEqual(out["bounded_center_difference_hz"],cfg["reporting_center_tolerance_hz"])
        self.assertEqual(out["product_nodes"],math.prod(r["nodes"] for r in out["dimensions"].values()))
        self.assertEqual(out["hypothetical_float64_factor_bytes"],out["product_nodes"]*96*3*8)
        self.assertFalse(out["count_is_necessary_lower_bound"])
        self.assertFalse(out["runtime_measured"])
        self.assertFalse(out["recovery_qualified"])
        self.assertEqual(out["templates_generated"],0)

    def test_midpoint_and_circular_cell_geometry(self):
        # Small abstract coordinate cells; no physical trajectory/grid created.
        N=7;width=2*math.pi;radius=width/(2*N)
        for x in (0.,1e-5,math.pi,2*math.pi-1e-5):
            nearest=(round(x*N/width)%N)*width/N
            self.assertLessEqual(m.circular_distance(x,nearest),radius+1e-14)
        for x in (0.,.05,.5,1.):
            cell=min(N-1,int(x*N));mid=(cell+.5)/N
            self.assertLessEqual(abs(x-mid),1/(2*N)+1e-14)

    def test_zero_coefficient_needs_one_node_not_zero_or_infinite(self):
        env=copy.deepcopy(envelope())
        for p in env["parameters"].values():p["proper_frequency_lipschitz_hz_per_unit"]=0.
        out=m.sufficient_cover_count(env,1.,1)
        self.assertEqual(out["product_nodes"],1)
        self.assertEqual(out["bounded_center_difference_hz"],0)

    def test_factor_storage_is_hypothetical_and_does_not_debit_source_bytes(self):
        out=m.sufficient_cover_count(envelope(),study()["reporting_center_tolerance_hz"],96)
        self.assertGreater(out["product_nodes"],33)
        self.assertNotIn("source_bytes_spent",out)
        self.assertFalse(out["templates_adopted"])
        self.assertFalse(envelope()["physical_model_qualified"])
        self.assertFalse(envelope()["spectral_access_authorized"])

    def test_frequency_scaling_and_emission_time_term_not_silently_dropped(self):
        cfg=study();a=envelope();b=m.sensitivity_envelope(contract(),cfg["reception_extent_seconds"],2*cfg["reference_hz"])
        for name,p in a["parameters"].items():
            self.assertEqual(b["parameters"][name]["proper_frequency_lipschitz_hz_per_unit"],2*p["proper_frequency_lipschitz_hz_per_unit"])
            self.assertGreater(p["retarded_v_derivative_m_s_per_unit"],p["fixed_source_v_derivative_m_s_per_unit"])

    def test_incomplete_or_nonfinite_count_inputs_refused(self):
        for eps,rows in ((0,96),(-1,96),(math.inf,96),(1,True),(1,0)):
            with self.assertRaises(ValueError):m.sufficient_cover_count(envelope(),eps,rows)
        env=envelope();del env["parameters"]["omega_rad"]
        with self.assertRaises(ValueError):m.sufficient_cover_count(env,1,96)
        env=envelope();env["parameters"]["period_days"]["proper_frequency_lipschitz_hz_per_unit"]=math.nan
        with self.assertRaises(ValueError):m.sufficient_cover_count(env,1,96)


if __name__=="__main__":unittest.main()
