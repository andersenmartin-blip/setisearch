import unittest

import numpy as np

from seti_repeater.tess_context_inputs import sector32_recipe, reconstruct, validate_links


class ContextInputTests(unittest.TestCase):
    def setUp(self):
        self.ap = np.ones((11, 11), bool); self.ap[0, 0] = False
        yy, xx = np.indices((11, 11))
        image = 5.+50*np.exp(-((yy-5)**2+(xx-5)**2)/4)
        self.native = np.broadcast_to(image, (401, 11, 11)).copy()
        self.seconds = (np.arange(401)-200)*20.

    def test_stress_uses_parent_window_when_selection_moves(self):
        p = {'trial_id': 'parent', 'anchor': 0, 'kind': 'stellar', 'shape': 'box30',
             'phase_seconds': 0., 'shift_yx': [0., 0.], 'sign': 1,
             'tuning': {'amplitude_e_per_s': 100.}, 'best': {'start': 199, 'stop': 201}}
        r = {**p, 'suite': 'sparse_stress', 'parent_trial_id': 'parent',
             'best': {'start': 200, 'stop': 202}, 'residual_location': 'inside',
             'residual_yx': [4, 4], 'residual_e_per_s': -7.}
        pattern, scale, residual, parent = sector32_recipe(r, {'parent': p}, self.native, self.ap)
        self.assertEqual((residual['start'], residual['stop']), (199, 201))
        self.assertEqual(parent, 'parent'); self.assertEqual(scale, 100.)
        recipe = {**r, 'pattern_scale': scale, 'residual': residual}
        stressed, _ = reconstruct(self.native, self.seconds, recipe, pattern)
        clean, _ = reconstruct(self.native, self.seconds, {**recipe, 'residual': None}, pattern)
        np.testing.assert_allclose(stressed[199:201, 4, 4]-clean[199:201, 4, 4], -7.)
        self.assertEqual(stressed[201, 4, 4], clean[201, 4, 4])

    def test_fixed_flux_and_null_preserve_archive_amplitudes(self):
        for fraction in [.01, 0.]:
            p = {'trial_id': 'p', 'anchor': 0, 'kind': 'stellar' if fraction else 'null',
                 'shape': 'box30', 'phase_seconds': 0., 'shift_yx': [0., 0.],
                 'sign': 1, 'tuning': None, 'amplitude_fraction': fraction}
            r = {**p, 'suite': 'ls7c_replay', 'original': {'trial_id': 'p'}}
            pattern, scale, residual, _ = sector32_recipe(r, {'p': p}, self.native, self.ap)
            self.assertAlmostEqual(scale, fraction*self.native[0, self.ap].sum())
            self.assertAlmostEqual(pattern[self.ap].sum(), 1.)
            self.assertIsNone(residual)

    def test_sector_qualified_identity_and_complete_source_order(self):
        records = [{'sector': s, 'case_id': f's{s:03d}/same', 'source_row': 0, 'source_trial_id': 'same'} for s in [29, 32]]
        validate_links(records, {'29': 1, '32': 1})
        with self.assertRaises(ValueError):
            validate_links(records+[records[0]], {'29': 2, '32': 1})
        with self.assertRaises(ValueError):
            validate_links([{**records[0], 'source_row': 1}, records[1]], {'29': 1, '32': 1})


if __name__ == '__main__':
    unittest.main()
