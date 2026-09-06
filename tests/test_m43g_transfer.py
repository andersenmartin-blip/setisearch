"""Independent arithmetic and adversarial fixtures for M43G transfer."""
from dataclasses import replace
import unittest
import numpy as np
from seti_repeater import transfer_m43g as new
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as old
from seti_repeater.spectral import normalized_boxcar


from m43g_reference import sorted_reference, direct_reference


class TransferTests(unittest.TestCase):
    def fixture(self):
        g = core.NativeFrequencyGeometry(100., 1., 8201)
        raw = ((np.arange(3*8201).reshape(3, 8201)*17 % 127)-63).astype('<f4')
        grid = core.make_proxy_carrier_grid(.004, 1., 30, 4)
        f = np.array([[.8,1.,1.2],[1.01,1.02,1.03]])
        src = new.normalize_synthetic_rows(lambda i: raw[i], g, 3,
                input_orientation='ascending', scope={'kind':'synthetic','label':'kat'})
        return g,raw,grid,f,src

    def test_block_normalization_matches_sort_reference_and_legacy(self):
        g,raw,grid,f,s = self.fixture()
        np.testing.assert_array_equal(s.values, sorted_reference(raw))
        np.testing.assert_array_equal(s.values, old.normalize_float32_blocks_v0p6(raw))
        self.assertFalse(s.values.flags.writeable)
        with self.assertRaises(ValueError):s.values.setflags(write=True)

    def test_descending_orientation_preserves_source_identity(self):
        g,raw,grid,f,s = self.fixture()
        desc = new.normalize_synthetic_rows(lambda i: raw[i,::-1],g,3,
                input_orientation='descending',scope={'kind':'synthetic','label':'kat'})
        self.assertEqual(s.identity,desc.identity)
        np.testing.assert_array_equal(s.values,desc.values)

    def test_all_widths_and_chunks_match_direct_window_reference(self):
        g,raw,grid,f,s = self.fixture()
        for width in core.M37_SPECTRAL_WIDTHS:
            cache = new.build_synthetic_cache(s,f,grid,width,bank_sha256='1'*64)
            ref = direct_reference(sorted_reference(raw),g,f,grid,width,0,grid.support_bin_count)
            for chunk in (1,7,100):
                np.testing.assert_array_equal(new.gather_bank_slice(cache,0,grid.support_bin_count,chunk_bins=chunk),ref)
            np.testing.assert_array_equal(new.gather_bank_slice(cache,3,11,template_indices=[1]),ref[1:2,3:11])

    def test_duplicate_channels_survive_and_old_gather_rejects(self):
        g,raw,grid,f,s = self.fixture()
        cache = new.build_synthetic_cache(s,f[:1],grid,1,bank_sha256='1'*64)
        mapped = core.nearest_native_indices(g,grid.support_hz*f[0,0])
        self.assertTrue(np.any(np.diff(mapped)==0))
        with self.assertRaises(core.V0P6ContractError):core._require_injective_q_mapping(mapped,0)
        out = new.gather_bank_slice(cache,0,grid.support_bin_count,chunk_bins=1)
        self.assertEqual(out.shape,(1,grid.support_bin_count))

    def test_legacy_injective_domain_agrees(self):
        g,raw,grid,f,s = self.fixture()
        freq = (g.raw_zero_hz+np.arange(g.channel_count)*g.channel_width_hz)/1e6
        for width in (1,129):
            cache = new.build_synthetic_cache(s,f[1:],grid,width,bank_sha256='1'*64)
            actual = new.gather_bank_slice(cache,0,grid.support_bin_count)[0]
            expected = core.native_filter_then_q_gather(s.values,freq,g,f[1],grid,width,return_support=True)
            np.testing.assert_array_equal(actual,expected)

    def test_identity_changes_and_tampering_is_rejected(self):
        g,raw,grid,f,s = self.fixture()
        cache = new.build_synthetic_cache(s,f,grid,3,bank_sha256='1'*64)
        different = new.build_synthetic_cache(s,f,grid,3,bank_sha256='2'*64)
        self.assertNotEqual(cache.identity,different.identity)
        for bad in (replace(cache,bank_sha256='2'*64),replace(cache,values=new.immutable(np.zeros_like(cache.values)))):
            with self.assertRaises(ValueError):new.gather_bank_slice(bad,0,5)
        with self.assertRaises(ValueError):new.validate_source(replace(s,identity='0'*64))

    def test_bad_inputs_and_source_claims_rejected(self):
        g,raw,grid,f,s = self.fixture()
        for bad in (raw[0].astype('f8'),raw[0,:5],np.full(g.channel_count,np.nan,dtype='f4')):
            with self.assertRaises(ValueError):new.normalize_synthetic_rows(lambda _:bad,g,1,input_orientation='ascending',scope={'kind':'synthetic'})
        with self.assertRaises(ValueError):new.normalize_synthetic_rows(lambda _:raw[0],g,1,input_orientation='ascending',scope={'kind':'telescope'})
        for bad in (np.zeros_like(f),f*np.nan,f*3):
            with self.assertRaises(ValueError):new.build_synthetic_cache(s,bad,grid,1,bank_sha256='1'*64)
        for width in (True,2,131):
            with self.assertRaises(ValueError):new.build_synthetic_cache(s,f,grid,width,bank_sha256='1'*64)

    def test_same_bytes_changed_dtype_shape_or_geometry_rejected(self):
        g,raw,grid,f,s = self.fixture()
        c = new.build_synthetic_cache(s,f,grid,1,bank_sha256='1'*64)
        altered = (replace(c,values=c.values.view('<u4')),
                   replace(c,values=c.values.reshape(1,-1)),
                   replace(c,source=replace(s,geometry=core.NativeFrequencyGeometry(101.,1.,8201))))
        for bad in altered:
            with self.assertRaises(ValueError):new.gather_bank_slice(bad,0,5)

    def test_coverage_and_memory_fail_before_reader(self):
        g,raw,grid,f,s = self.fixture()
        out = core.make_proxy_carrier_grid(.02,1.,30,4)
        with self.assertRaises(core.V0P6CoverageError):new.build_synthetic_cache(s,f,out,129,bank_sha256='1'*64)
        huge = core.NativeFrequencyGeometry(0.,1.,100_000_000)
        with self.assertRaises(core.V0P6CapacityError):new.normalize_synthetic_rows(lambda _:self.fail('reader called'),huge,16,input_orientation='ascending',scope={'kind':'synthetic'})

    def test_half_channel_nearest_even_and_bounds(self):
        g = core.NativeFrequencyGeometry(0.,1.,200)
        grid = core.make_proxy_carrier_grid(.0001005,1.,2,0)
        s = new.normalize_synthetic_rows(lambda _:np.arange(200,dtype='<f4'),g,1,input_orientation='ascending',scope={'kind':'synthetic'})
        cache = new.build_synthetic_cache(s,np.ones((1,1)),grid,1,bank_sha256='1'*64)
        np.testing.assert_array_equal(new.gather_bank_slice(cache,0,5,chunk_bins=1),s.values[:,[98,100,100,102,102]])
        for start,stop in ((-1,5),(0,6),(2,2)):
            with self.assertRaises(ValueError):new.gather_bank_slice(cache,start,stop)

    def test_filter_chunk_halos_match_whole_native_filter(self):
        g = core.NativeFrequencyGeometry(0.,1.,33001)
        raw = (np.arange(g.channel_count)%61).astype('<f4')
        grid = core.make_proxy_carrier_grid(.0165,1.,30,4)
        s = new.normalize_synthetic_rows(lambda _:raw,g,1,input_orientation='ascending',scope={'kind':'synthetic'})
        for width in (3,129):
            c = new.build_synthetic_cache(s,np.ones((1,1)),grid,width,bank_sha256='1'*64)
            np.testing.assert_array_equal(c.values,normalized_boxcar(s.values,width)[:,width//2:-(width//2)])


if __name__=='__main__':unittest.main()
