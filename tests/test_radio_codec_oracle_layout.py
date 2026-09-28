"""The demonstrated new oracle-layout defect only; no codec/noise rerun."""
import unittest
import numpy as np

from radio_hd189733_codec_reconcile import reference_normalization
from seti_repeater import source_v0p6 as normalization


class OracleLayoutTests(unittest.TestCase):
    def test_strided_order_preserved_when_made_contiguous(self):
        values=np.arange(16384,dtype='<f4')[::2]
        self.assertFalse(values.flags.c_contiguous)
        with self.assertRaisesRegex(ValueError,'C-order'):
            normalization.normalize_float32_blocks_v0p6(values[::-1].reshape(1,-1))
        expected=normalization.normalize_float32_blocks_v0p6(np.array([list(reversed(values))],dtype='<f4',order='C'))[0]
        actual=reference_normalization(values)
        np.testing.assert_array_equal(actual.view('<u4'),expected.view('<u4'))

    def test_invalid_oracle_input_rejected_before_normalization(self):
        for value in (np.array([1.],dtype='<f8'),np.array([np.nan],dtype='<f4'),np.zeros((1,2),dtype='<f4')):
            with self.assertRaises(ValueError):reference_normalization(value)


if __name__=='__main__':unittest.main()
