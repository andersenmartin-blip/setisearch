import json
from pathlib import Path
import unittest
import numpy as np

from seti_repeater.light_sail_tess_v3 import trial_specs
from seti_repeater.tess_transfer import spatial_mask, placed_pattern, decisions, expected_suites

ROOT = Path(__file__).resolve().parents[1]


class TransferTests(unittest.TestCase):
    def test_unmodeled_shapes_are_explicit(self):
        self.assertEqual(spatial_mask('cross3x3').sum(), 5)
        self.assertEqual(spatial_mask('ring3x3').sum(), 8)
        self.assertEqual(spatial_mask('triangle3x3').sum(), 6)
        self.assertEqual(spatial_mask('ring3x3')[1, 1], 0)

    def test_placement_ties_are_row_major_and_aperture_normalized(self):
        profile = np.ones((5, 5))/25
        aperture = np.ones((5, 5), dtype=bool)
        for kind in ['block3x3', 'row1x5', 'column5x1', 'cross3x3', 'ring3x3', 'triangle3x3']:
            pattern, corner = placed_pattern(kind, profile, aperture)
            self.assertEqual(corner, [0, 0])
            self.assertAlmostEqual(pattern[aperture].sum(), 1.)

    def test_negative_margin_acceptance_is_not_source_preference(self):
        star = {'objective': 3., 'chi2': 3., 'residual_dof': 18, 'amplitude_noise_score': 7.}
        result = decisions(star, {'objective': 2.5}, True, False, [-1, 0, 9])
        self.assertTrue(result['-1']['recovered'])
        self.assertTrue(result['-1']['nuisance_preferred_acceptance'])
        self.assertFalse(result['0']['accepted'])
        self.assertFalse(result['9']['accepted'])

    def test_no_margin_bypasses_temporal_or_confounding_accounting(self):
        star = {'objective': 0., 'chi2': 0., 'residual_dof': 18, 'amplitude_noise_score': 7.}
        for result in decisions(star, {'objective': 20.}, False, False, [-1, 0, 9]).values():
            self.assertFalse(result['accepted'])
        for result in decisions(star, {'objective': 20.}, True, True, [-1, 0, 9]).values():
            self.assertTrue(result['accepted'])
            self.assertFalse(result['recovered'])

    def test_strength_matching_and_stress_denominators(self):
        cfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
        specs = trial_specs(cfg)
        self.assertEqual(len(specs)*20, 1460)
        parents = [r for r in specs if (r['group'] == 'matched' and r['kind'] in ('stellar', 'block_2x2')) or r['kind'] == 'null']
        self.assertEqual(len(parents)*20*4, 1040)
        self.assertEqual(sum(expected_suites().values()), 3540)


if __name__ == '__main__':
    unittest.main()
