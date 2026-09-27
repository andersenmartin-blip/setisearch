"""New one-sided arithmetic and derivative-majorant risks; no generated tracks."""
import json
import math
from fractions import Fraction as F
from pathlib import Path
import unittest

from seti_repeater import temporal_majorant_radio as m

ROOT=Path(__file__).resolve().parents[1]
def contract():return json.loads((ROOT/"config/radio_phase_domain_20260927.json").read_text())
def study():return json.loads((ROOT/"config/radio_temporal_majorant_20260927.json").read_text())
def decode(value):return F(int(value["numerator"]),int(value["denominator"]))


class RationalMajorantRisks(unittest.TestCase):
    def test_Machin_tangent_identity_is_exact_rational(self):
        # tan(4 atan(1/5)-atan(1/239))=1; angles are in the first quadrant.
        tangent=F(1,5)
        for _ in range(2):tangent=2*tangent/(1-tangent*tangent)
        self.assertEqual((tangent-F(1,239))/(1+tangent/F(239)),1)

    def test_alternating_remainder_and_outward_pi_rounding(self):
        low,high,rounded=m.pi_upper()
        self.assertLess(low,high);self.assertLess(high-low,F(1,10**60))
        self.assertLessEqual(high,rounded);self.assertLess(rounded-high,F(1,10**40))
        self.assertGreater(low,F('3.1415926535897932384626433832795028841971'))
        self.assertLess(high,F('3.1415926535897932384626433832795028841972'))
        lo1,hi1=m.atan_reciprocal_enclosure(5,9)
        lo2,hi2=m.atan_reciprocal_enclosure(5,10)
        self.assertLessEqual(lo1,lo2);self.assertLessEqual(hi2,hi1)

    def test_integer_square_root_enclosures_include_exact_and_irrational_cases(self):
        for x in (F(2),F(9,16),F(1,10**41),F(0),F(999999999999,1000000000000)):
            lo,hi=m.sqrt_enclosure(x)
            self.assertLessEqual(lo*lo,x);self.assertGreaterEqual(hi*hi,x)
            self.assertLessEqual(hi-lo,F(1,10**40))
        self.assertEqual(m.sqrt_enclosure(F(9,16)),(F(3,4),F(3,4)))

    def test_absolute_binomial_majorants_match_known_coefficients(self):
        delta=[F(0),F(1),F(0),F(0),F(0)]
        sqrt=m.binomial_absolute_series(delta,F(1,2),4)
        self.assertEqual(sqrt,[F(1),F(1,2),F(1,8),F(1,16),F(5,128)])
        inverse=m.binomial_absolute_series(delta,F(-3,2),4)
        self.assertEqual(inverse,[F(1),F(3,2),F(15,8),F(35,16),F(315,128)])

    def test_inverse_time_majorant_matches_independent_Catalan_solution(self):
        # H=s+H² has Catalan coefficients, independently known closed recurrence.
        q=[F(0)]*8;q[2]=1
        h=m.inverse_positive_majorant(1,q,7)
        self.assertEqual(h,[F(0),F(1),F(1),F(2),F(5),F(14),F(42),F(132)])
        scaled=m.inverse_positive_majorant(F(2),q,4)
        self.assertEqual(scaled,[F(0),F(1,2),F(1,8),F(1,16),F(5,128)])

    def test_composition_retains_cross_terms_and_truncation(self):
        # (1+2t+3t²) at t=s+2s², through cubic order.
        found=m.compose([F(1),F(2),F(3)],[F(0),F(1),F(2),F(0)],3)
        self.assertEqual(found,[F(1),F(2),F(7),F(12)])
        with self.assertRaises(ValueError):m.compose([F(1)],[F(1)],0)

    def test_newtonian_majorants_include_circular_derivatives_with_factorials(self):
        n=F(1,100);r=m.normalized_position_majorant(n,F(0),8)
        for j,R in enumerate(r):self.assertGreaterEqual(R,n**j/math.factorial(j))
        self.assertEqual(r[2],n*n/2)
        # J bound is deliberately twice circular truth before factorial division.
        self.assertEqual(r[3],2*n**3/math.factorial(3))

    def test_low_order_coefficients_match_published_norm_units(self):
        # Independent physical norm expressions, checking factorial/unit placement.
        n=F(1,100000);e=F(172,1000);r=m.normalized_position_majorant(n,e,8)
        speed_upper=m.sqrt_enclosure((1+e)/(1-e))[1]*n
        self.assertEqual(r[1],speed_upper)
        self.assertEqual(2*r[2],n*n/(1-e)**2)
        self.assertEqual(6*r[3],2*n*n*speed_upper/(1-e)**3)

    def test_circular_reception_derivative_formulas_fit_composed_bounds(self):
        n=F(1,100000);a=F(9000000000);c=F(299792458);f=F(1500000000)
        r=m.normalized_position_majorant(n,0,8);B=n*a/c
        result=m.frequency_majorant(r,B,a,f,7)
        bounds=result["frequency_coefficients_hz_per_second_power"]
        # Circular edge-on beta=-B*cos(M), derivative w.r.t source time.
        for M in (.3,1.1,2.2):
            b=-float(B)*math.cos(M);b1=float(B*n)*math.sin(M)
            b2=float(B*n*n)*math.cos(M);b3=-float(B*n**3)*math.sin(M)
            first=float(f)*(1+b)*(-b1/(1+b)**3)
            second=float(f)*(1+b)*(-b2/(1+b)**4+3*b1*b1/(1+b)**5)
            third=float(f)*(1+b)*(-b3/(1+b)**5+10*b1*b2/(1+b)**6-15*b1**3/(1+b)**7)
            for j,actual in enumerate((first,second,third),1):
                self.assertLessEqual(abs(actual)/math.factorial(j),float(bounds[j]))

    def test_zero_axis_has_no_nonconstant_frequency_coefficients(self):
        r=m.normalized_position_majorant(F(1,100),F(1,10),8)
        out=m.frequency_majorant(r,0,0,1500000000,7)
        self.assertEqual(out["frequency_coefficients_hz_per_second_power"],[F(1500000000)]+[F(0)]*7)

    def test_exact_remainder_comparison_and_outward_decimal_are_consistent(self):
        cfg=study();out=m.temporal_remainder_certificate(contract(),cfg)
        T,eps=F(cfg["reception_extent_seconds"]),F(cfg["reporting_tolerance_hz"])
        for row in out["degrees"]:
            coefficient=decode(row["derivative_coefficient_upper"])
            remainder=decode(row["remainder_hz_exact_upper"])
            self.assertEqual(remainder,coefficient*T**(row["degree"]+1))
            self.assertGreaterEqual(F(row["remainder_hz_outward_decimal"]),remainder)
            self.assertLess(F(row["remainder_hz_outward_decimal"])-remainder,F(1,10**15))
            self.assertEqual(row["within_reporting_tolerance"],remainder<=eps)

    def test_six_orders_do_not_authorize_templates_or_full_physical_error(self):
        out=m.temporal_remainder_certificate(contract(),study())
        self.assertEqual([r["degree"] for r in out["degrees"]],[1,2,3,4,5,6])
        self.assertTrue(out["conditional_mathematical_arithmetic_certified"])
        for key in ("bank_adopted","coefficient_grid_qualified","runtime_for_search_measured",
                    "recovery_qualified","physical_model_qualified","spectral_access_authorized"):
            self.assertFalse(out[key])
        self.assertEqual(out["templates_generated"],0);self.assertEqual(out["polynomial_tracks_generated"],0)
        self.assertIsNone(out["total_physical_error_hz"])

    def test_frozen_degree_and_domain_changes_are_rejected(self):
        cfg=study();cfg["orders"]+=[7]
        with self.assertRaises(ValueError):m.temporal_remainder_certificate(contract(),cfg)
        cfg=study();cfg["domain_sha256"]="wrong"
        with self.assertRaises(ValueError):m.temporal_remainder_certificate(contract(),cfg)
        cfg=study();cfg["outward_decimal_digits"]=10
        with self.assertRaises(ValueError):m.temporal_remainder_certificate(contract(),cfg)

    def test_invalid_series_and_nonpositive_arrival_derivative_refused(self):
        with self.assertRaises(ValueError):m.sqrt_enclosure(-1)
        with self.assertRaises(ValueError):m.atan_reciprocal_enclosure(1,5)
        with self.assertRaises(ValueError):m.binomial_absolute_series([F(0),F(-1)],F(1,2),1)
        with self.assertRaises(ValueError):m.inverse_positive_majorant(0,[F(0)]*3,2)
        r=m.normalized_position_majorant(F(1,100),0,8)
        with self.assertRaises(ValueError):m.frequency_majorant(r,1,1,1,7)
        with self.assertRaises(ValueError):m.frequency_majorant(r,0,1,1,7)


if __name__=="__main__":unittest.main()
