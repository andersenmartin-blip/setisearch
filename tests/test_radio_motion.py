"""Independent numerical and boundary checks for the new metadata diagnostics."""
import copy
import json
from pathlib import Path
import unittest
import numpy as np
from seti_repeater import motion_radio as m

ROOT = Path(__file__).resolve().parents[1]
ORBIT = dict(period_days=5.77152, semi_major_axis_au=.0634, eccentricity=.172, omega_deg=-10.)


class MotionTests(unittest.TestCase):
    def test_kepler_against_independent_bisection(self):
        means = np.linspace(-np.pi, np.pi, 257, endpoint=False)
        for e in (0., .172, .7):
            lo, hi = np.full_like(means, -np.pi), np.full_like(means, np.pi)
            for _ in range(64):
                mid = (lo+hi)/2
                high = mid-e*np.sin(mid) >= means
                hi = np.where(high, mid, hi); lo = np.where(high, lo, mid)
            np.testing.assert_allclose(m.eccentric_anomaly(means, e), (lo+hi)/2,
                                       rtol=0, atol=3e-15)

    def test_circular_analytic_solution_and_quadrature(self):
        seconds = np.linspace(0, 2500, 97); phase = np.linspace(0, 1, 65, endpoint=False)
        orbit = ORBIT | {"eccentricity": 0.}
        k = 2*np.pi*orbit["semi_major_axis_au"]*m.AU_M/(orbit["period_days"]*m.DAY_S)
        exact = -k*np.cos(2*np.pi*(seconds[None,:]/(orbit["period_days"]*m.DAY_S)-phase[:,None])
                          + np.deg2rad(orbit["omega_deg"]))
        np.testing.assert_allclose(m.kepler_velocity(seconds, phase, **orbit), exact, rtol=0, atol=2e-9)
        np.testing.assert_allclose(m.circular_quadrature(seconds, phase, **orbit), exact, rtol=0, atol=2e-9)

    def test_eccentric_quadrature_refuses_and_demonstrates_counterexample(self):
        with self.assertRaisesRegex(ValueError, "exact zero"):
            m.circular_quadrature([0, 1960], [.5], **ORBIT)
        exact = m.kepler_velocity([0, 1960], [.5], **ORBIT)
        false = m.unchecked_quadrature_diagnostic([0, 1960], [.5], **ORBIT)
        residual = np.diff(exact-false, axis=1)*1.5e9/m.C_M_S
        self.assertGreater(float(np.abs(residual).max()), 2.835503418452676)

    def test_clock_matches_integer_exposures_and_rejects_overlap(self):
        scans = json.loads((ROOT/'config/radio_hd1461_source_preparation_20260926.json').read_text())["scans"]
        rows, starts, mids, ends = m.integration_clock(scans)
        self.assertEqual(len(rows), 96)
        np.testing.assert_allclose((ends-starts).sec, 17.986224128, rtol=0, atol=2e-10)
        np.testing.assert_allclose((mids-starts).sec, 17.986224128/2, rtol=0, atol=2e-10)
        changed = copy.deepcopy(scans)
        changed[1]["expected_header"]["tstart_mjd"] = changed[0]["expected_header"]["tstart_mjd"]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            m.integration_clock(changed)
        changed = copy.deepcopy(scans); changed[0]["expected_header"]["tsamp_s"] = 0
        with self.assertRaises(ValueError): m.integration_clock(changed)

    def test_acceleration_bound_contains_sampled_derivatives(self):
        phases = np.arange(2048)/2048
        velocities = m.kepler_velocity([-.5, .5], phases, **ORBIT)
        acceleration = np.abs(velocities[:,1]-velocities[:,0])
        self.assertLessEqual(float(acceleration.max()), m.kepler_acceleration_bound(**ORBIT))
        # The LOS need not align with the acceleration at the archive omega.
        # At periastron and omega=90 degrees it does: check that limiting case.
        aligned = m.kepler_velocity([-.5, .5], [0.], **(ORBIT | {"omega_deg": 90.}))
        self.assertGreater(float(np.abs(np.diff(aligned)).max()), .999*m.kepler_acceleration_bound(**ORBIT))


if __name__ == '__main__': unittest.main()
