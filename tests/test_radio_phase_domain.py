"""New conditional-domain/convention risks; no search bank or data evaluation."""
import copy
import json
import math
from pathlib import Path
import unittest

from seti_repeater import phase_domain_radio as m

ROOT = Path(__file__).resolve().parents[1]


def config():
    return json.loads((ROOT/"config/radio_phase_domain_20260927.json").read_text())


def state(**changes):
    return m.state_at_eccentric_anomaly(**(dict(anomaly=.73, eccentricity=.172,
        period_seconds=5.77152*86400, emitter_axis_m=.0634*m.AU_M,
        projected_axis_m=.025*m.AU_M, omega=-.31) | changes))


class DomainRisks(unittest.TestCase):
    def test_valid_conditional_domain_never_grants_source_or_bank_permission(self):
        out = m.audit_contract(config())
        self.assertTrue(out["mathematical_declaration_valid"])
        for key in ("actual_source_membership_established", "physical_model_qualified",
                    "spectral_access_authorized", "templates_authorized"):
            self.assertIs(out[key], False)
        self.assertIsNone(out["joint_probability"])

    def test_marginal_error_rectangle_retains_explicit_nonprobabilistic_meaning(self):
        c = config()
        facts = json.loads((ROOT/"results_radio_motion_contract_2026-09-27/primary_orbital_facts.json").read_text())
        for key, fact in (("period_days", "period_days"), ("relative_axis_au", "semi_major_axis_relative_au")):
            f = facts[fact]
            for found, expected in zip(c["domain"][key], (f["value"]-f["plus_minus"], f["value"]+f["plus_minus"])):
                self.assertAlmostEqual(found, expected, places=12)
        self.assertEqual(c["domain"]["eccentricity"][1], facts["eccentricity"]["p99"])
        for value in (.99, 0, "unknown"):
            c["uncertainty"]["joint_probability"] = value
            with self.assertRaises(ValueError): m.audit_contract(c)

    def test_upper_limit_cannot_be_relabelled_central_eccentricity(self):
        c = config()
        c["domain"]["eccentricity_kind"] = "point_estimate"
        with self.assertRaises(ValueError): m.audit_contract(c)

    def test_missing_or_changed_conventions_rejected(self):
        c = config()
        for field in c["conventions"]:
            for replacement in (None, "BJD"):
                changed = copy.deepcopy(c)
                changed["conventions"][field] = replacement
                with self.subTest(field=field), self.assertRaises(ValueError):
                    m.audit_contract(changed)

    def test_no_missing_error_can_be_promoted_to_zero(self):
        for name in config()["unresolved"]:
            changed = config()
            changed["unresolved"][name] = 0
            with self.assertRaises(ValueError): m.audit_contract(changed)
        c = config(); c["unresolved"].pop("additional_emitter_motion")
        with self.assertRaises(ValueError): m.audit_contract(c)

    def test_identity_binds_semantics_even_with_same_numeric_box(self):
        c = config(); h = m.contract_identity(c)
        changed = copy.deepcopy(c)
        changed["uncertainty"]["selection"] += "; not epoch anchored"
        self.assertNotEqual(h, m.contract_identity(changed))
        self.assertEqual(h, m.contract_identity(dict(reversed(list(c.items())))))

    def test_invalid_endpoints_and_nonpositive_doppler_denominator_refused(self):
        cases = [("period_days", [0, 1]), ("period_days", [2, 1]),
                 ("relative_axis_au", [False, 1]), ("relative_axis_au", [1, math.inf]),
                 ("eccentricity", [.1, .2]), ("eccentricity", [0, 1]),
                 ("relative_axis_au", [1e6, 1e7])]
        for key, value in cases:
            c = config(); c["domain"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): m.audit_contract(c)

    def test_no_implicit_mass_ratio_or_emitter_site_assumption(self):
        c = config(); c["axis"]["emitter"] = "planet_surface"
        with self.assertRaises(ValueError): m.audit_contract(c)
        c = config(); del c["axis"]["mass_ratio_policy"]
        with self.assertRaises(ValueError): m.audit_contract(c)

    def test_activation_or_partial_phase_domain_is_rejected(self):
        for field in ("physical_bank_adopted", "templates_authorized", "spectral_access_authorized",
                      "actual_source_membership_established"):
            c = config(); c[field] = True
            with self.assertRaises(ValueError): m.audit_contract(c)
        c = config(); c["domain"]["planet_orientation_angle"] = [-10, -10]
        with self.assertRaises(ValueError): m.audit_contract(c)


class GeometryRisks(unittest.TestCase):
    def test_relative_to_COM_conversion_conserves_barycentre(self):
        for q in (0, .5, 100):
            axes = m.projected_axes(1000., q, .6)
            ap = axes["emitter_axis_m"]
            astar = 1000.-ap
            self.assertAlmostEqual(astar, q*ap, places=10)
            self.assertEqual(axes["projected_axis_m"], .6*ap)
            self.assertLessEqual(axes["projected_axis_m"], ap)
            self.assertLessEqual(ap, 1000.)

    def test_face_on_or_zero_axis_has_no_radial_track_but_speed_is_distinct(self):
        face = state(projected_axis_m=0)
        self.assertEqual(face["z_m"], 0)
        self.assertEqual(face["velocity_away_m_s"], 0)
        self.assertGreater(face["speed_squared_m2_s2"], 0)
        zero = state(projected_axis_m=0, emitter_axis_m=0)
        self.assertEqual(zero["speed_squared_m2_s2"], 0)

    def test_cartesian_orbit_derivative_matches_LOS_formula(self):
        E, e, omega, A, p = .73, .172, -.31, .025*m.AU_M, 5.77152*86400
        # Independent rotated Cartesian velocity, differentiated at fixed E.
        dx = -A*math.sin(E)
        dy = A*math.sqrt(1-e*e)*math.cos(E)
        expected = -(dx*math.sin(omega)+dy*math.cos(omega))*2*math.pi/p/(1-e*math.cos(E))
        self.assertAlmostEqual(state()["velocity_away_m_s"], expected, places=10)

    def test_circular_phase_orientation_degeneracy_and_orientation_reversal(self):
        initial = state(eccentricity=0)
        shifted = state(eccentricity=0, anomaly=.73+.43, omega=-.31-.43)
        for key in initial:
            self.assertAlmostEqual(initial[key]/max(1, abs(initial[key])),
                                   shifted[key]/max(1, abs(initial[key])), places=13)
        opposite = state(omega=-.31+math.pi)
        for key in ("z_m", "velocity_away_m_s"):
            self.assertAlmostEqual(opposite[key]/state()[key], -1, places=13)
        self.assertEqual(opposite["speed_squared_m2_s2"], state()["speed_squared_m2_s2"])

    def test_existing_velocity_sign_requires_explicit_negative_phase_mapping(self):
        # One deterministic equation/convention comparison, not a bank rerun.
        from seti_repeater.motion_radio import kepler_velocity
        E, e = .73, .172
        M = E-e*math.sin(E)
        old = kepler_velocity([0.], [-M/(2*math.pi)], period_days=5.77152,
            semi_major_axis_au=.025, eccentricity=e, omega_deg=math.degrees(-.31))[0, 0]
        self.assertAlmostEqual(old, state()["velocity_away_m_s"], places=8)

    def test_vis_viva_speed_is_not_LOS_speed(self):
        e, E, p, a = .172, .73, 5.77152*86400, .0634*m.AU_M
        mu, r = (2*math.pi/p)**2*a**3, a*(1-e*math.cos(E))
        expected = mu*(2/r-1/a)
        found = state()
        self.assertAlmostEqual(found["speed_squared_m2_s2"]/expected, 1, places=13)
        self.assertLess(found["velocity_away_m_s"]**2, found["speed_squared_m2_s2"])

    def test_unphysical_projection_and_nonfinite_inputs_refused(self):
        for args in ((100, -.1, .5), (100, .1, 1.1), (True, .1, .5), (100, math.nan, .5)):
            with self.assertRaises(ValueError): m.projected_axes(*args)
        for kw in ({"projected_axis_m": .1*m.AU_M}, {"period_seconds": 0}, {"anomaly": math.inf},
                   {"eccentricity": .8}, {"omega": False}):
            with self.assertRaises(ValueError): state(**kw)


if __name__ == "__main__": unittest.main()
