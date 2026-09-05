"""Regression for live tuple versus persisted JSON list replay."""
import unittest
from ls4f_v2_native_reanalysis import numeric_agreement
from ls4l_v2_vetoed_fragment_diagnostics import canonical_replay_agreement,load

T={'rtol':1e-10,'atol':1e-8}

class ReplayTests(unittest.TestCase):
    def test_old_representation_failure_is_corrected_without_changing_values(self):
        actual={'band_indices':(102,113),'score':4.25,'passed':False}
        expected={'band_indices':[102,113],'score':4.25,'passed':False}
        self.assertFalse(numeric_agreement(actual,expected,**T))
        self.assertTrue(canonical_replay_agreement(actual,expected,T))

    def test_real_value_key_and_length_changes_still_fail(self):
        expected={'band_indices':[102,113],'score':4.25}
        for actual in ({'band_indices':(102,114),'score':4.25},{'band_indices':(102,113),'score':4.26},{'band_indices':(102,113,114),'score':4.25},{'band_indices':(102,113)}):
            self.assertFalse(canonical_replay_agreement(actual,expected,T))

    def test_repeat_cannot_exceed_original_combined_download_budget(self):
        c=load('config/ls4l_v2_vetoed_fragment_diagnostics.json')
        self.assertEqual(c['resource']['attempts_per_source'],1)
        self.assertEqual(c['prior_charged_download_bytes'],18870174378)
        self.assertEqual(c['prior_charged_download_bytes']+sum(s['source_size_bytes'] for s in c['sources']),c['resource']['max_total_download_bytes'])

if __name__=='__main__':unittest.main()
