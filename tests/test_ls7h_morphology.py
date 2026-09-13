import unittest

import numpy as np

from seti_repeater.tess_joint_spatial import FitBank
from seti_repeater.tess_morphology import shape_bank, components, margin_components, decision


class MorphologyTests(unittest.TestCase):
    def test_shapes_rotations_and_edge_intersections(self):
        aperture = np.ones((3, 3), dtype=bool)
        p, labels = shape_bank(aperture, ['cross3x3', 'ring3x3', 'triangle3x3'])
        self.assertEqual(len(p), 6)
        self.assertEqual(p.sum(axis=1).tolist(), [5, 8, 6, 6, 6, 6])
        self.assertEqual(len({tuple(v) for v in p[2:]}), 4)
        self.assertEqual(p[1, 4], 0)
        a = np.zeros((4, 4), dtype=bool); a[1:3, 1:3] = True
        p, labels = shape_bank(a, ['cross3x3'])
        self.assertEqual(labels, ['cross3x3_r0_0_0', 'cross3x3_r0_0_1', 'cross3x3_r0_1_0', 'cross3x3_r0_1_1'])
        np.testing.assert_array_equal(p[0], [1, 1, 1, 0])

    def test_selected_window_signed_partial_residual_and_exact_sum(self):
        t = (np.arange(401)-200)*20.
        native = np.broadcast_to(np.arange(401)[:, None, None], (401, 3, 3)).copy().astype(float)
        aperture = np.ones((3, 3), bool); pattern = np.ones((3, 3))/9
        row = {'phase_seconds': 0., 'shape': 'box30', 'pattern_scale': 90., 'sign': -1,
               'best': {'start': 200, 'stop': 202},
               'residual': {'pixel_yx': [1, 1], 'start': 199, 'stop': 201, 'amplitude_e_per_s': 12.}}
        b, clean, pure, observed = components(native, t, aperture, pattern, row)
        expected = np.full(9, -6.25); expected[4] -= 6.
        np.testing.assert_allclose(clean, expected)
        np.testing.assert_allclose(pure, expected)
        np.testing.assert_allclose(b+clean, observed)

    def test_median_nonadditivity_is_preserved(self):
        t = (np.arange(401)-200)*20.
        native = np.broadcast_to(np.arange(401)[:, None, None], (401, 3, 3)).copy().astype(float)
        aperture = np.ones((3, 3), bool)
        row = {'phase_seconds': 0., 'shape': 'box30', 'pattern_scale': 0., 'sign': 1,
               'best': {'start': 200, 'stop': 202},
               'residual': {'pixel_yx': [1, 1], 'start': 140, 'stop': 170, 'amplitude_e_per_s': 100.}}
        b, clean, pure, observed = components(native, t, aperture, np.ones((3, 3)), row)
        self.assertGreater(abs(clean[4]-pure[4]), 1.)
        np.testing.assert_allclose(b+clean, observed)

    def test_margin_decomposition_with_sparse_winner(self):
        c = np.diag(np.arange(1, 10)/10)
        star_p = np.array([[0, 1, 2, 4, 8, 4, 2, 1, 0.]])
        nuisance_p = np.array([[0, 0, 1, 1, 1, 1, 0, 0, 0.]])
        clean = 3*star_p[0]; background = np.array([1, -2, 1, 0, -1, 1, 0, 2, 20.])
        y = clean+background
        star = FitBank(c, star_p, True, 9).fit(y)
        nuisance = FitBank(c, nuisance_p, True, 9).fit(y)
        self.assertIsNotNone(star['sparse_pixel'])
        terms = margin_components(background, clean, c, star_p[0], nuisance_p[0], star, nuisance, 9)
        self.assertAlmostEqual(terms['sum'], nuisance['objective']-star['objective'], places=8)

    def test_fixed_cut_rejects_and_accounts_confounding(self):
        cfg = {'source_score_min': 5, 'reduced_chi2_max': 2, 'margin': -1}
        star = {'amplitude_noise_score': 7, 'chi2': 18, 'residual_dof': 18}
        row = {'screen_detected': True, 'baseline_confounded': False}
        self.assertTrue(decision(row, star, -1, cfg)['recovered'])
        self.assertFalse(decision(row, star, -1.0001, cfg)['accepted'])
        row['baseline_confounded'] = True
        d = decision(row, star, 2, cfg)
        self.assertTrue(d['accepted']); self.assertFalse(d['recovered'])
        self.assertEqual(d['recovery_path'], 'confounded')


if __name__ == '__main__':
    unittest.main()
