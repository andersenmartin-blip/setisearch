import unittest
import numpy as np
from m43f_source_cache_preflight import endpoint_coverage, enlarged_interval, duplicate_witness, resource_estimate
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as source


class SourceCoverageTests(unittest.TestCase):
    def test_endpoint_certificate_matches_every_toy_carrier(self):
        grid=core.make_proxy_carrier_grid(.0005,1.,40,4)
        geometry=core.NativeFrequencyGeometry(400.,1.,201)
        matrix=np.array([[1.,1.01],[.8,1.2],[.99,1.03]])
        for width in (1,3,17,129):
            result=endpoint_coverage(geometry,matrix,grid,width)
            dense=core.nearest_native_indices(geometry,matrix[:,:,None]*grid.support_hz)
            bad=(dense<width//2)|(dense>=geometry.channel_count-width//2)
            self.assertEqual(result['all_covered'],not bad.any())
            self.assertEqual(result['uncovered_templates'],int(np.any(bad,axis=(1,2)).sum()))
            self.assertEqual(result['uncovered_template_integration_rows'],int(np.any(bad,axis=2).sum()))
            self.assertEqual(result['raw_center_start'],int(dense.min()))
            self.assertEqual(result['raw_center_stop'],int(dense.max())+1)

    def test_proposed_descending_interval_restores_filter_coverage(self):
        old=(400,601)
        grid=core.make_proxy_carrier_grid(.0005,1.,40,4)
        factors=np.array([[.7,1.3]])
        geometry=core.native_geometry_from_extraction(fch1_mhz=.001,foff_mhz=-.000001,channel_start=old[0],channel_stop=old[1])
        need=endpoint_coverage(geometry,factors,grid,129)
        self.assertFalse(need['all_covered'])
        new=enlarged_interval(old,need,2000)
        self.assertLess(new[0],old[0]);self.assertGreater(new[1],old[1])
        newgeo=core.native_geometry_from_extraction(fch1_mhz=.001,foff_mhz=-.000001,channel_start=new[0],channel_stop=new[1])
        self.assertTrue(endpoint_coverage(newgeo,factors,grid,129)['all_covered'])

    def test_no_expansion_when_existing_filter_margin_suffices(self):
        c={'raw_center_start':50,'raw_center_stop':150,'filter_radius_channels':4}
        self.assertEqual(enlarged_interval((400,601),c,2000),(400,601))
        with self.assertRaises(ValueError):enlarged_interval((0,200),{'raw_center_start':-100,'raw_center_stop':1000,'filter_radius_channels':64},300)

    def test_nearest_even_half_channel_boundaries(self):
        grid=core.make_proxy_carrier_grid(.0005,1.,0,0)
        g=core.NativeFrequencyGeometry(400.5,1.,201)
        c=endpoint_coverage(g,np.ones((1,1)),grid,1)
        self.assertEqual(c['raw_center_start'],100)
        self.assertEqual(c['raw_center_stop'],101)

    def test_duplicate_witness_uses_literal_mapping(self):
        g=core.NativeFrequencyGeometry(200.,1.,700)
        grid=core.make_proxy_carrier_grid(.0005,1.,100,4)
        f=np.array([[1.1,.8],[1.,1.]])
        w=duplicate_witness(g,f,grid)
        self.assertEqual((w['template_index'],w['integration_index']),(0,1))
        self.assertGreater(w['duplicate_pairs'],0)
        a,b=w['first_duplicate']['mapped_native_indices']
        self.assertEqual(a,b)
        self.assertEqual(sum(w['step_counts'].values()),grid.support_bin_count-1)
        self.assertTrue(duplicate_witness(g,np.array([[1.1]]),grid)['mapping_injective'])

    def test_existing_cache_planner_rejects_subunit_factors_even_with_wide_source(self):
        g=core.NativeFrequencyGeometry(0.,1.,2000)
        grid=core.make_proxy_carrier_grid(.0005,1.,40,4)
        with self.assertRaisesRegex(core.V0P6ContractError,'injective'):
            core.plan_native_filter_cache(g,np.array([[.8,1.1]]),grid,1,
                window_id='fixture',scan_label='fixture_on',scan_kind='on',source_sha256='0'*64,
                factor_basis_sha256_value='1'*64,factor_basis_labels_sha256_value='2'*64,
                scan_inventory_sha256_value='3'*64,factor_scan_selection_sha256_value='4'*64,
                template_bank_sha256_value='5'*64)

    def test_resource_caps_and_invalid_inputs_fail_explicitly(self):
        a=resource_estimate(source.M37_MAXIMUM_SOURCE_NATIVE_CHANNELS,16)
        self.assertTrue(a['legacy_source_channel_cap_passed'])
        self.assertFalse(resource_estimate(source.M37_MAXIMUM_SOURCE_NATIVE_CHANNELS+1,16)['legacy_source_channel_cap_passed'])
        g=core.NativeFrequencyGeometry(0.,1.,2000);grid=core.make_proxy_carrier_grid(.0005,1.,40,4)
        for f in (np.array([[0.]]),np.array([[float('nan')]]),np.array([1.])):
            with self.assertRaises(ValueError):endpoint_coverage(g,f,grid,1)
        for width in (0,2,True):
            with self.assertRaises(ValueError):endpoint_coverage(g,np.ones((1,1)),grid,width)


if __name__=='__main__':unittest.main()
