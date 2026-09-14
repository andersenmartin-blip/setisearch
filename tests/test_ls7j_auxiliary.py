"""Synthetic known answers; no closed-sector outcomes enter these tests."""
import unittest
import sys
from pathlib import Path
import numpy as np

from seti_repeater.tess_auxiliary import prepare, footprint, motion, predict, aperture_centroid
from seti_repeater.light_sail_tess_v2 import pointing_delta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from ls7j_review_auxiliary import footprint as audit_footprint, shifted


SHIFTS = [[0., 0.], [0., -.25], [0., .25], [-.25, 0.], [-.25, -.25], [-.25, .25], [.25, 0.], [.25, -.25], [.25, .25]]


class AuxiliaryTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(719)
        y, x = np.indices((11, 11))
        self.ap = (y-5)**2+(x-5)**2 <= 5
        image = 500*np.exp(-((y-5.1)**2+(x-4.8)**2)/2.)+10.
        self.cube = image[None, :, :]+rng.normal(size=(401, 11, 11))
        self.model = prepare(self.cube, self.ap, 199, 202, SHIFTS)

    def test_guard_and_event_do_not_change_operator(self):
        changed = self.cube.copy(); changed[194:207] += 1e6
        other = prepare(changed, self.ap, 199, 202, SHIFTS)
        for key in ['operator', 'reference', 'sigma', 'profiles', 'outside_noise']:
            np.testing.assert_array_equal(self.model[key], other[key])

    def test_all_protected_wings_are_annihilated(self):
        self.assertTrue(self.model['valid'])
        for p in self.model['profiles']:
            for sign in [-1., 1.]:
                prediction, _ = predict(sign*57*p, self.model, np.zeros((11, 11)))
                np.testing.assert_allclose(prediction['combined'], 0., atol=1e-11)
                self.assertGreater(np.linalg.norm(p[~self.ap]), 0.)

    def test_plane_and_source_are_separated_in_same_exposure(self):
        beta = np.array([3., -2., 5.])
        plane = self.model['plane']@beta
        source = self.model['profiles'][4]*700
        prediction, coefficients = predict(plane+source, self.model, np.zeros((11, 11)))
        np.testing.assert_allclose(coefficients['combined'], beta, atol=2e-11)
        np.testing.assert_allclose(plane+source-prediction['combined'], source, atol=2e-11)

    def test_aperture_pixel_disturbance_does_not_enter_auxiliary_fit(self):
        first, _ = predict(np.zeros((11, 11)), self.model, np.zeros((11, 11)))
        delta = np.zeros((11, 11)); delta[5, 5] = 1e8
        second, _ = predict(delta, self.model, np.zeros((11, 11)))
        np.testing.assert_array_equal(first['combined'], second['combined'])

    def test_axis_order_and_fixed_physical_motion_response(self):
        positions = np.zeros((401, 2)); positions[199:202] = [.02, -.03]
        image, d = motion(positions, self.model['reference'], 199, 202)
        np.testing.assert_allclose(d, [.02, -.03], atol=1e-15)
        expected = pointing_delta(self.model['reference'], [.02, -.03])
        np.testing.assert_allclose(image, expected, atol=1e-11)
        prediction, beta = predict(image+self.model['profiles'][0]*41, self.model, image)
        np.testing.assert_allclose(beta['combined'], 0., atol=1e-12)
        np.testing.assert_allclose(prediction['combined'], image, atol=1e-11)

    def test_missing_motion_is_explicit_and_not_zero_filled(self):
        positions = np.zeros((401, 2)); positions[200, 0] = np.nan
        image, d = motion(positions, self.model['reference'], 199, 202)
        self.assertIsNone(image); self.assertIsNone(d)
        prediction, _ = predict(np.zeros((11, 11)), self.model, image)
        self.assertIsNone(prediction['combined']); self.assertIsNotNone(prediction['plane'])

    def test_centroid_is_signal_dependent(self):
        image = np.ones((11, 11))*20
        shifted = image.copy(); shifted[5, 7] += 1000
        before = aperture_centroid(image, self.ap); after = aperture_centroid(shifted, self.ap)
        self.assertGreater(after[1]-before[1], .5)
        self.assertAlmostEqual(after[0], before[0])

    def test_broadened_wings_are_a_separate_mismatch_stress(self):
        nominal = footprint(self.model['reference'], self.ap)
        broader = footprint(self.model['reference'], self.ap, blur=.5)
        self.assertAlmostEqual(nominal[self.ap].sum(), 1.)
        self.assertAlmostEqual(broader[self.ap].sum(), 1.)
        self.assertGreater(broader[~self.ap].sum(), nominal[~self.ap].sum())
        pred, _ = predict(broader*100, self.model, np.zeros((11, 11)))
        self.assertGreater(np.linalg.norm(pred['combined']), 1e-5)

    def test_independent_geometry_and_joint_solver_match_synthetic_known_answers(self):
        ref = self.model['reference']
        for displacement in [[.2, -.2], [-.25, .25], [0., 0.]]:
            for blur in [0., .5]:
                np.testing.assert_allclose(audit_footprint(ref, self.ap, displacement, blur),
                                           footprint(ref, self.ap, displacement, blur), rtol=0, atol=1e-15)
            moved = shifted(ref, displacement, True); moved *= ref.sum()/moved.sum()
            np.testing.assert_allclose(moved-ref, pointing_delta(ref, displacement), rtol=0, atol=1e-12)
        noise = self.model['outside_noise']; outside = ~self.ap
        protected = self.model['profiles'][:, outside].T/noise[:, None]
        u, s, _ = np.linalg.svd(protected, full_matrices=False)
        design = np.column_stack([u[:, s > 1e-10*s[0]], self.model['plane'][outside]/noise[:, None]])
        joint = np.linalg.lstsq(design, np.diag(1./noise), rcond=1e-12)[0][-3:]
        np.testing.assert_allclose(joint, self.model['operator'], rtol=0, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
