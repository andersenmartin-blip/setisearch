"""Independent full-search comparisons and intervention geometry oracles."""
import json
from pathlib import Path
import unittest
import numpy as np
from seti_repeater import light_sail as ls
from ls4i_measured_digital_injections import associated, cached_search, coarse_parameters, modified_coarse, profile, trial_specs

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'config/ls4i_measured_digital_injections.json').read_text())


class LS4ITests(unittest.TestCase):
    def test_cached_and_injected_search_exactly_equal_full_native_recomputation(self):
        rng = np.random.default_rng(114900)
        data = rng.normal(100, 1, (96, 1027)).astype(np.float32)
        data[21:31, 310:455] += 2
        data[:, 16] = 100  # invalid scale must stay invalid
        frequency = 8000 + np.arange(data.shape[1]) * .02
        kwargs = dict(base_bin_channels=16, spectral_width_bins=[1,4,16,32,64], duration_s=[4,8,16,32,64],
                      minimum_score=6., maximum_events=2048, clip_low=-6., clip_high=12., minimum_valid_fraction=.8)
        coarse, valid = ls._coarse_normalized_spectrum(data, *coarse_parameters(kwargs))
        expected = ls.search_broadband_events(data, frequency, 1., **kwargs)
        self.assertEqual(cached_search(coarse, valid, frequency, 1., kwargs), expected)
        truth = {'frequency_start_mhz': 8006.11, 'frequency_stop_mhz': 8009.41}
        shape = np.zeros(96); shape[48:80] = .1; shape[52] = 1.1
        for amplitude in [0., 1., 16.]:
            modified = data.copy()
            mask = (frequency >= truth['frequency_start_mhz']) & (frequency <= truth['frequency_stop_mhz'])
            sigma = 1.4826*np.median(np.abs(data - np.median(data, axis=0)), axis=0)
            good = mask & np.isfinite(sigma) & (sigma > np.finfo(np.float32).eps)
            modified[:, good] = (data[:, good].astype(np.float64) + amplitude*shape[:, None]*sigma[good]).astype(np.float32)
            c, v = modified_coarse(data, frequency, coarse, valid, shape, truth, amplitude, kwargs)
            self.assertEqual(cached_search(c, v, frequency, 1., kwargs), ls.search_broadband_events(modified, frequency, 1., **kwargs))
        # The process-wide detector still reads native inputs normally.
        self.assertEqual(ls.search_broadband_events(data, frequency, 1., **kwargs), expected)

    def test_association_requires_half_of_both_time_and_frequency_intervals(self):
        truth = dict(frequency_start_mhz=8500., frequency_stop_mhz=8512., time_start_s=48., time_stop_s=80.)
        self.assertTrue(associated(truth, truth, .5))
        broad = {**truth, 'frequency_stop_mhz': 8600.}
        short = {**truth, 'time_stop_s': 50.}
        displaced = {**truth, 'time_start_s': 100., 'time_stop_s': 132.}
        for event in [broad, short, displaced]:
            self.assertFalse(associated(event, truth, .5))

    def test_profile_area_retains_subsecond_dilution_and_same_analytic_shape(self):
        spec = next(trial_specs(CONFIG))
        for dt, n in [(1., 292), (.001, 292000)]:
            actual = profile(n, dt, spec, CONFIG).sum()*dt
            self.assertAlmostEqual(actual, 3.2 + 6*.003, places=10)

    def test_reserved_files_are_excluded_and_grid_complete(self):
        self.assertEqual({x['label'] for x in CONFIG['sources']}, {'A1','B1'})
        self.assertEqual(len(list(trial_specs(CONFIG))), 36)
        self.assertEqual(len(list(trial_specs(CONFIG, include_zero=True))), 12)
        self.assertEqual(sum(x['source_size_bytes'] for x in CONFIG['sources']), 22007514360)


if __name__ == '__main__':
    unittest.main()
