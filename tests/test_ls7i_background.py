"""Synthetic known answers only: do not inspect the closed-sector outcomes."""
import unittest
import numpy as np

from seti_repeater.tess_background import observe, ridge_fit, predict, build_folds, residual_covariance
from seti_repeater.light_sail_tess import pulse_shape


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(713)

    def records(self, anchors=10):
        matrix = np.array([[.6, -.2, .4], [0., .3, -.5], [.1, .2, .4], [-.2, .5, .1], [.3, .1, -.1], [.2, -.1, .7]])
        out = []
        for a in range(anchors):
            for i in range(13):
                x = self.rng.normal(size=6)
                y = x@matrix+self.rng.normal(size=3)*.2
                out.append({'anchor': a, 'width': 3, 'sample_id': f'{a}/{i}', 'x': x.tolist(), 'y': y.tolist()})
        return out

    def test_event_and_guard_cannot_change_prediction_inputs(self):
        cube = self.rng.normal(size=(401, 3, 3))+100
        ap = np.ones((3, 3), bool)
        old = observe(cube, ap, 200, 203)
        changed = cube.copy(); changed[195:208] += self.rng.normal(size=(13, 3, 3))*1e5
        new = observe(changed, ap, 200, 203)
        for key in ['x', 'reference', 'sigma']:
            np.testing.assert_array_equal(old[key], new[key])
        self.assertGreater(np.linalg.norm(new['y']-old['y']), 1e4)

    def test_signed_short_pulse_is_preserved_exactly(self):
        cube = self.rng.normal(size=(401, 3, 3))+100
        ap = np.ones((3, 3), bool)
        old = observe(cube, ap, 200, 203)
        p = self.rng.normal(size=(3, 3))
        for sign in [-1, 1]:
            injected = cube.copy(); injected[200:203] += sign*19*p
            new = observe(injected, ap, 200, 203)
            np.testing.assert_array_equal(old['x'], new['x'])
            np.testing.assert_allclose(sign*(new['y']-old['y']), 19*p[ap]/old['sigma'], atol=2e-14)

    def test_width_guard_protects_declared_pulses_and_reselected_stress(self):
        seconds = (np.arange(401)-200)*20.+.00001*np.arange(401)
        for shape in ['box30', 'box60', 'box100', 'doublet30sep87']:
            for phase in [0., 10.]:
                pulse, centers = pulse_shape(seconds, phase, shape, 20.)
                for width in [2, 3, 5]:
                    for start in range(190, 210):
                        stop = start+width
                        if min(abs((seconds[start]+seconds[stop-1])/2-c) for c in centers) <= 20.1:
                            outside = np.r_[pulse[start-60:start-5], pulse[stop+5:stop+60]]
                            np.testing.assert_array_equal(outside, 0.)
        # A parent-local stress may move the selected center by one cadence.
        stress = np.zeros(401); stress[199:204] = 123.
        np.testing.assert_array_equal(np.r_[stress[140:195], stress[208:263]], 0.)

    def test_ridge_known_orthogonal_solution(self):
        x = np.vstack([np.eye(4), -np.eye(4)])
        beta = np.arange(12).reshape(4, 3)/10
        y = x@beta+np.array([2., -4., 1.])
        rows = [{'anchor': 0, 'width': 2, 'sample_id': str(i), 'x': a.tolist(), 'y': b.tolist()} for i, (a, b) in enumerate(zip(x, y))]
        fit = ridge_fit(rows, [], 2, 1.)
        np.testing.assert_allclose(fit['beta'], beta/2., atol=1e-14)
        np.testing.assert_allclose(predict(np.zeros(4), fit), [2., -4., 1.], atol=1e-14)

    def test_unpredictable_target_does_not_create_a_prediction(self):
        x = np.repeat(np.vstack([np.eye(4), -np.eye(4)]), 2, axis=0)
        y = np.tile([[1., 2., -3.], [-1., -2., 3.]], (8, 1))+[2., 4., 1.]
        rows = [{'anchor': 0, 'width': 2, 'sample_id': str(i), 'x': a.tolist(), 'y': b.tolist()} for i, (a, b) in enumerate(zip(x, y))]
        fit = ridge_fit(rows, [], 2)
        np.testing.assert_array_equal(fit['beta'], np.zeros((4, 3)))
        np.testing.assert_array_equal(predict(np.full(4, 1e6), fit), [2., 4., 1.])

    def test_predictable_background_generalizes_to_excluded_anchor(self):
        rows = self.records()
        fit = ridge_fit(rows, [9], 3)
        hold = [r for r in rows if r['anchor'] == 9]
        conditional = sum(np.sum((r['y']-predict(r['x'], fit))**2) for r in hold)
        static = sum(np.sum((r['y']-predict(r['x'], fit, 'static'))**2) for r in hold)
        self.assertLess(conditional, static/2)

    def test_nested_covariance_excludes_entire_assessed_background(self):
        rows = self.records()
        first = build_folds(rows, [3])
        for r in rows:
            if r['anchor'] == 3:
                r['x'] = (np.asarray(r['x'])+1e5).tolist()
                r['y'] = (np.asarray(r['y'])-1e5).tolist()
        second = build_folds(rows, [3])
        a = next(f for f in first['folds'] if f['excluded_anchor'] == 3)
        b = next(f for f in second['folds'] if f['excluded_anchor'] == 3)
        self.assertEqual(a, b)
        self.assertEqual(next(m for m in first['models'] if m['model_id'] == a['model_id']),
                         next(m for m in second['models'] if m['model_id'] == a['model_id']))
        self.assertEqual(len(a['calibration_ids']), 117)
        for method in ['conditional', 'static']:
            self.assertGreater(min(a['methods'][method]['eigenvalues']), 0)

    def test_invalid_context_scale_and_shrinkage_fail_explicitly(self):
        ap = np.ones((3, 3), bool)
        for lo, hi in [(59, 62), (339, 342)]:
            with self.assertRaises(ValueError):
                observe(self.rng.normal(size=(401, 3, 3)), ap, lo, hi)
        with self.assertRaises(ValueError):
            observe(np.ones((401, 3, 3)), ap, 200, 203)
        with self.assertRaises(ValueError):
            residual_covariance(np.ones((10, 3)))


if __name__ == '__main__':
    unittest.main()
