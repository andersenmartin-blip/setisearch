import unittest
import numpy as np
from seti_repeater.light_sail import search_broadband_events
class DurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=np.random.default_rng(6).normal(100,1,(56,65536)).astype('float32')
        cls.frequency=10013.963413238525-np.arange(65536)*.00286102294921875
        cls.kwargs=dict(base_bin_channels=1024,spectral_width_bins=(1,4,16,32,64),minimum_score=6,maximum_events=2048,clip_low=-6,clip_high=12,minimum_valid_fraction=.8)
    def test_initial_bank_reproduces_failure(self):
        with self.assertRaisesRegex(ValueError,'time template exceeds scan duration'):
            search_broadband_events(self.data,self.frequency,1.073741824,duration_s=(4,8,16,32,64),**self.kwargs)
    def test_repaired_bank_fits_identical_header_shape(self):
        r=search_broadband_events(self.data,self.frequency,1.073741824,duration_s=(4,8,16,32),**self.kwargs)
        self.assertFalse(r['retention_truncated']);self.assertEqual(r['valid_base_frequency_bin_count'],64)
        self.assertEqual(r['evaluated_band_duration_templates'],832)
