"""Exhaustive native-center traversal and failure checks for M43K."""
from dataclasses import replace
import unittest
import numpy as np
from m43k_native_filters import audit_native_values,bank_coverage
from seti_repeater import transfer_m43g as synthetic
from seti_repeater import search_v0p6 as core


class NativeFilterTests(unittest.TestCase):
    def fixture(self):
        n=33001;g=core.NativeFrequencyGeometry(0.,1.,n)
        rng=np.random.default_rng(43011)
        raw=rng.normal(size=(2,n)).astype('<f4')
        src=synthetic.normalize_synthetic_rows(lambda i:raw[i],g,2,
            input_orientation='ascending',scope={'kind':'synthetic','test':'m43k'})
        grid=core.make_proxy_carrier_grid(.0165,1.,34,4);f=np.array([[.8,1.2],[1.,1.]])
        return src,grid,f

    def test_all_widths_every_center_and_both_chunk_boundaries(self):
        s,g,f=self.fixture()
        for w in (3,5,9,17,33,65,129):
            c=synthetic.build_synthetic_cache(s,f,g,w,bank_sha256='1'*64)
            rows=audit_native_values(s.values,c.values,w,chunk_centers=2048)
            alternate=audit_native_values(s.values,c.values,w,chunk_centers=5003)
            self.assertEqual(rows,alternate)
            self.assertEqual([r['row'] for r in rows],[0,1])
            self.assertEqual(sum(r['values_compared'] for r in rows),2*(33001-w+1))
            self.assertEqual(rows[0]['native_center_start'],w//2)
            self.assertEqual(rows[0]['native_center_stop'],33001-w//2)

    def test_one_ulp_at_edges_or_production_halo_is_detected(self):
        s,g,f=self.fixture();c=synthetic.build_synthetic_cache(s,f,g,129,bank_sha256='1'*64)
        for index in (0,16383,16384,c.values.shape[1]-1):
            damaged=c.values.copy();damaged[1,index]=np.nextafter(damaged[1,index],np.float32(np.inf))
            with self.assertRaises(RuntimeError):audit_native_values(s.values,damaged,129,chunk_centers=2048)

    def test_wrong_dtype_shape_row_order_or_chunk_is_rejected(self):
        s,g,f=self.fixture();c=synthetic.build_synthetic_cache(s,f,g,3,bank_sha256='1'*64)
        for bad in (c.values.view('<u4'),c.values[:,:-1].copy()):
            with self.assertRaises(ValueError):audit_native_values(s.values,bad,3,chunk_centers=2048)
        with self.assertRaises(RuntimeError):audit_native_values(s.values,c.values[::-1].copy(),3,chunk_centers=2048)
        for chunk in (0,True,2.5):
            with self.assertRaises(ValueError):audit_native_values(s.values,c.values,3,chunk_centers=chunk)

    def test_monotonic_endpoint_bound_matches_all_small_grid_mappings(self):
        s,g,f=self.fixture()
        for w in (3,129):
            r=bank_coverage(s.geometry,f,g,w)
            every=core.nearest_native_indices(s.geometry,f[...,None]*g.support_hz)
            self.assertEqual(r['minimum_mapped_center'],int(every.min()))
            self.assertEqual(r['maximum_mapped_center'],int(every.max()))
            self.assertTrue(np.any(np.diff(every,axis=-1)==0))
        for bad in (f*0,f*np.nan,-f,f.astype('<f4')):
            with self.assertRaises(ValueError):bank_coverage(s.geometry,bad,g,129)
        with self.assertRaises(core.V0P6CoverageError):bank_coverage(s.geometry,f,core.make_proxy_carrier_grid(.04,1.,34,4),129)
        with self.assertRaises(ValueError):bank_coverage(s.geometry,f,replace(g,support_hz=g.support_hz[::-1]),129)


if __name__=='__main__':unittest.main()
