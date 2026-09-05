"""LS4F extraction, provenance and channel-concentration oracles."""
import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ls4f_native_reanalysis import extract_bands, concentration, numeric_agreement


class LS4FNativeTests(unittest.TestCase):
    def test_original_and_corrected_extraction_against_direct_oracle(self):
        matrix = (np.arange(128 * 20).reshape(128, 20) % 256).astype(np.uint8)
        original, corrected = np.arange(3, 16), np.arange(4, 15)
        old, new, baseline, occupancy = extract_bands(matrix, original, corrected, 40, 80, 38, 82, 17)
        np.testing.assert_array_equal(old, matrix[:, 3:16].mean(axis=1))
        np.testing.assert_array_equal(new, matrix[:, 4:15].mean(axis=1))
        expected = np.concatenate([matrix[:38, 3:16], matrix[82:, 3:16]])
        np.testing.assert_array_equal(baseline, expected.mean(axis=0))
        self.assertEqual(occupancy['zero_byte_counts'], (matrix[:, 3:16] == 0).sum(axis=0).tolist())
        self.assertEqual(occupancy['max_byte_counts'], (matrix[:, 3:16] == 255).sum(axis=0).tolist())

    def test_extra_channel_only_impulse_has_unit_extra_fraction(self):
        matrix = np.full((100, 13), 100, dtype=np.uint8)
        matrix[49:51, 0] = 200
        result = concentration(matrix, np.arange(13), np.full(13, 100.), .05, .002, .001, np.arange(1, 12))
        self.assertEqual(result['extra_channel_fraction'], 1.0)
        self.assertEqual(result['largest_channel_index'], 0)
        self.assertEqual(result['sample_count'], 2)

    def test_uniform_channel_increase_has_known_concentration(self):
        matrix = np.full((100, 13), 120, dtype=np.uint8)
        result = concentration(matrix, np.arange(13), np.full(13, 100.), .05, .01, .001, np.arange(1, 12))
        self.assertAlmostEqual(result['largest_channel_fraction'], 1/13)
        self.assertAlmostEqual(result['extra_channel_fraction'], 2/13)

    def test_replay_rejects_disposition_changes(self):
        expected = {'score': 12.1, 'decision': False, 'scales': [1, 2]}
        self.assertTrue(numeric_agreement(copy.deepcopy(expected), expected, 1e-10, 1e-8))
        self.assertFalse(numeric_agreement({**expected, 'decision': True}, expected, 1e-10, 1e-8))
        self.assertFalse(numeric_agreement({**expected, 'score': 12.2}, expected, 1e-10, 1e-8))
        self.assertFalse(numeric_agreement({**expected, 'extra': 1}, expected, 1e-10, 1e-8))

    def test_frozen_sources_and_download_budget_match_published_receipts(self):
        config = json.loads((ROOT / 'config/ls4f_native_reanalysis.json').read_text())
        previous = json.loads((ROOT / 'results_ls4c_htr/followup.json').read_text())
        self.assertEqual(config['sources'], previous['source_receipts'])
        self.assertEqual(sum(s['source_size_bytes'] for s in config['sources']), 18870174378)
        self.assertLessEqual(18870174378, config['resource']['max_total_download_bytes'])


if __name__ == '__main__':
    unittest.main()
