import unittest
from dataclasses import replace
import numpy as np
import test_m43i_transfer as fixtures
from m43g_reference import direct_reference
from m43l_reference import build_reference
from m43l_wider_integrated import qualify_batch
from m43n_epoch_scores import native_gate, inventory
from seti_repeater import transfer_m43i as t

class EpochScoreTests(unittest.TestCase):
    def test_all_eight_widths_native_and_integrated_direct_reference(self):
        source,grid,factors=fixtures.TelescopeTransferTests().fixture()
        for width in (1,3,5,9,17,33,65,129):
            cache=t.build_telescope_cache(source,factors,grid,width,bank_sha256='1'*64)
            ref=build_reference(source.values,source.geometry,width,chunk_centers=131)
            rows=native_gate(cache,ref)
            self.assertEqual(sum(r['values_compared'] for r in rows),3*(8201-width+1))
            record,kept=qualify_batch(cache,ref,0,2,gather_chunk=7,reference_chunk=11,retain_indices=[0,1])
            expected=direct_reference(source.values,source.geometry,factors,grid,width,0,grid.support_bin_count)
            np.testing.assert_array_equal(np.stack([kept[0],kept[1]]),expected)
            self.assertEqual(record['cells_compared'],2*grid.support_bin_count)

    def test_native_scope_interior_corruption_and_digest_rejected(self):
        source,grid,factors=fixtures.TelescopeTransferTests().fixture()
        cache=t.build_telescope_cache(source,factors,grid,3,bank_sha256='1'*64)
        ref=build_reference(source.values,source.geometry,3)
        values=ref.values.copy();values[1,100]+=1
        for bad in (replace(ref,width=5),replace(ref,values=values),replace(ref,filtered_payload_sha256='0'*64)):
            with self.assertRaises(ValueError):native_gate(cache,bad)

    def test_complete_cartesian_inventory_required(self):
        cfg={'anchors':[{'scan':'on'},{'scan':'off'}],'widths':[1,3],'template_count':2}
        checks=[dict(scan=s,width=w,batch_count=1,native_values_compared=10,cells_compared=20)
                for s in ('on','off') for w in (1,3)]
        self.assertEqual(inventory(checks,cfg)['integrated_score_cells_compared'],80)
        for bad in (checks[:-1],checks[::-1],checks+[checks[0]],[checks[0]]*4):
            with self.assertRaises(ValueError):inventory(bad,cfg)
