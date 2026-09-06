"""Independent factorization, absolute coordinates and full-batch traversal."""
import unittest
from unittest.mock import patch
import numpy as np
import test_m43i_transfer as fixtures
from m43g_reference import direct_reference
from m43l_reference import build_reference,integrate_reference
from m43l_wider_integrated import qualify_batch,validate_batches
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer


class WiderIntegratedTests(unittest.TestCase):
    def test_all_widths_factorized_oracle_equals_direct_windows(self):
        s,g,f=fixtures.TelescopeTransferTests().fixture()
        for width in (3,5,9,17,33,65,129):
            ref=build_reference(s.values,s.geometry,width,chunk_centers=127)
            cache=transfer.build_telescope_cache(s,f,g,width,bank_sha256='1'*64)
            self.assertEqual(ref.filtered_payload_sha256,cache.payload_sha256)
            self.assertFalse(np.shares_memory(ref.values,cache.values))
            self.assertTrue(np.isnan(ref.values[:,:width//2]).all())
            self.assertTrue(np.isnan(ref.values[:,-(width//2):]).all())
            expected=direct_reference(s.values,s.geometry,f,g,width,0,g.support_bin_count)
            for chunk in (5,17,g.support_bin_count):
                actual=np.concatenate([integrate_reference(ref,f,g,a,min(a+chunk,g.support_bin_count))
                    for a in range(0,g.support_bin_count,chunk)],axis=1)
                np.testing.assert_array_equal(actual,expected)
            with self.assertRaises(ValueError):ref.values.setflags(write=True)

    def test_full_batch_counts_and_retained_order_match_direct(self):
        s,g,f=fixtures.TelescopeTransferTests().fixture();width=129
        cache=transfer.build_telescope_cache(s,f,g,width,bank_sha256='1'*64)
        ref=build_reference(s.values,s.geometry,width,chunk_centers=2048)
        records=[];kept={}
        for a,b in ((0,1),(1,2)):
            r,v=qualify_batch(cache,ref,a,b,gather_chunk=7,reference_chunk=11,retain_indices=[0,1])
            records.append(r);kept.update(v)
        self.assertEqual(validate_batches(records,2,1,g.support_bin_count),2*g.support_bin_count)
        expected=direct_reference(s.values,s.geometry,f,g,width,0,g.support_bin_count)
        np.testing.assert_array_equal(np.stack([kept[0],kept[1]]),expected)

    def test_missing_reordered_false_oracle_success_rejected(self):
        records=[{'template_start':i,'template_stop':i+1,'cells_compared':5,
            'factorized_reference_exact':True,'score_sha256':'1'*64} for i in (0,1)]
        for bad in (records[:1],records[::-1],[records[0],records[0]],
                    [dict(records[0],factorized_reference_exact=False),records[1]]):
            with self.assertRaises(ValueError):validate_batches(bad,2,1,5)
        s,g,f=fixtures.TelescopeTransferTests().fixture();c=transfer.build_telescope_cache(s,f,g,3,bank_sha256='1'*64)
        ref=build_reference(s.values,s.geometry,3)
        with patch('m43l_wider_integrated.integrate_reference',return_value=np.zeros((1,11),dtype='<f4')):
            with self.assertRaises(RuntimeError):qualify_batch(c,ref,0,1,gather_chunk=7,reference_chunk=11,retain_indices=[])

    def test_absolute_reference_guards_and_input_shape_rejected(self):
        s,g,f=fixtures.TelescopeTransferTests().fixture();ref=build_reference(s.values,s.geometry,129)
        badgrid=core.make_proxy_carrier_grid(.000101,1.,2,0)
        with self.assertRaises(ValueError):integrate_reference(ref,f,badgrid,0,badgrid.support_bin_count)
        for a in (s.values.astype('<f8'),s.values[:,:-1].copy()):
            with self.assertRaises(ValueError):build_reference(a,s.geometry,129)


if __name__=='__main__':unittest.main()
