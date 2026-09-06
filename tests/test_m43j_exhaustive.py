"""Scheduler coverage and independent-oracle mismatch tests for M43J."""
import unittest
from unittest.mock import patch
import numpy as np
import test_m43i_transfer as fixtures
from seti_repeater import transfer_m43i as transfer
from m43g_reference import direct_reference
from m43j_exhaustive_anchors import batches,qualify_batch,validate_inventory


class ExhaustiveTests(unittest.TestCase):
    def test_partition_includes_last_partial_and_each_template_once(self):
        r=batches(1701,32)
        self.assertEqual(len(r),54);self.assertEqual(r[-1],(1696,1701))
        self.assertEqual([i for a,b in r for i in range(a,b)],list(range(1701)))
        for args in ((True,32),(0,32),(2,0),(2,1.5)):
            with self.assertRaises(ValueError):batches(*args)

    def test_complete_batched_outputs_and_retained_vector_order(self):
        src,grid,f=fixtures.TelescopeTransferTests().fixture()
        cache=transfer.build_telescope_cache(src,f,grid,1,bank_sha256='1'*64)
        records=[];retained={}
        for a,b in batches(len(f),1):
            r,v=qualify_batch(cache,a,b,gather_chunk=7,reference_chunk=11,retain_indices=(0,1))
            records.append(r);retained.update(v)
        self.assertEqual(validate_inventory(records,count=2,size=1,support=grid.support_bin_count),2*grid.support_bin_count)
        expected=direct_reference(src.values,src.geometry,f,grid,1,0,grid.support_bin_count)
        np.testing.assert_array_equal(np.stack([retained[0],retained[1]]),expected)
        self.assertEqual([r['score_sha256'] for r in records],[transfer.array_hash(expected[i:i+1]) for i in range(2)])

    def test_missing_duplicate_out_of_order_or_false_success_rejected(self):
        records=[{'template_start':i,'template_stop':i+1,'support_cells_per_template':5,
            'cells_compared':5,'native_window_reference_exact':True,'score_sha256':'1'*64} for i in range(2)]
        invalid=[records[:1],records[::-1],[records[0],records[0]],
            [dict(records[0],native_window_reference_exact=False),records[1]],
            [dict(records[0],cells_compared=4),records[1]]]
        for bad in invalid:
            with self.assertRaises(ValueError):validate_inventory(bad,count=2,size=1,support=5)

    def test_reference_mismatch_fails_before_success_record(self):
        src,grid,f=fixtures.TelescopeTransferTests().fixture()
        cache=transfer.build_telescope_cache(src,f,grid,1,bank_sha256='1'*64)
        with patch('m43j_exhaustive_anchors.direct_reference',return_value=np.zeros((1,11),dtype='<f4')):
            with self.assertRaises(RuntimeError):qualify_batch(cache,0,1,gather_chunk=7,reference_chunk=11)


if __name__=='__main__':unittest.main()
