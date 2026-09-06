import unittest
import numpy as np
from m43q_fixture import fixture
from seti_repeater import search_v0p6 as core
from seti_repeater.mask_m43t import build_mask,reference_mask,validate_scope
from seti_repeater import detector_m43t as detector


class MaskComparisonTests(unittest.TestCase):
    def test_single_epoch_is_still_removed_and_displaced_pair_is_protected(self):
        arrays={w:np.zeros((3,101),dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        arrays[1][0,50]=12
        for policy in ('legacy','neighbor2'):
            self.assertTrue(build_mask(arrays.__getitem__,policy)[0,50])
        arrays[1][1,52]=3
        self.assertTrue(build_mask(arrays.__getitem__,'legacy')[0,50])
        self.assertFalse(build_mask(arrays.__getitem__,'neighbor2')[0,50])
        arrays[1][1,52]=np.nextafter(np.float32(3),np.float32(0))
        self.assertTrue(build_mask(arrays.__getitem__,'neighbor2')[0,50])
        arrays[1][1,52]=0;arrays[1][1,53]=3
        self.assertTrue(build_mask(arrays.__getitem__,'neighbor2')[0,50])

    def test_clipped_edges_and_width_or(self):
        arrays={w:np.zeros((3,50),dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        arrays[1][0,0]=20;arrays[1][1,-1]=5
        self.assertTrue(build_mask(arrays.__getitem__,'neighbor2')[0,0])
        self.assertFalse(build_mask(arrays.__getitem__,'neighbor2')[0,-1])
        arrays[1][1,2]=5
        self.assertFalse(build_mask(arrays.__getitem__,'neighbor2')[0,0])
        arrays[129][0,0]=11
        self.assertTrue(build_mask(arrays.__getitem__,'neighbor2')[0,0])

    def test_independent_reference_and_subset_property(self):
        rng=np.random.default_rng(430020)
        for n in (1,2,7,53,301):
            arrays={w:rng.choice(np.array([-2,0,2.99,3.,9.99,10.,15.],dtype='<f4'),size=(3,n)) for w in core.M37_SPECTRAL_WIDTHS}
            legacy=build_mask(arrays.__getitem__,'legacy');new=build_mask(arrays.__getitem__,'neighbor2')
            for policy,observed in (('legacy',legacy),('neighbor2',new)):
                np.testing.assert_array_equal(observed,reference_mask(arrays.__getitem__,policy))
            self.assertFalse(np.any(new&~legacy))

    def test_scope_mismatch_rejected(self):
        with self.assertRaises(ValueError):validate_scope('m43t-mask-legacy','neighbor2')

    def test_complete_legacy_fixture_keeps_known_physical_outcomes(self):
        kw,_=fixture();kw['window']='m43t-mask-legacy';kw['policy']='legacy'
        cal,_=detector.calibrate(**{k:v for k,v in kw.items() if k not in ('receiver_factory','reference_floor','maximum_records')})
        threshold=core.calibrated_threshold((cal,),expected_window_ids=(kw['window'],),reference_floor=50.,quantile=1.,scientific_p_ceiling=.01)
        result=detector.execute(**{k:v for k,v in kw.items() if k not in ('shifts','minimum_shift_bins','reference_floor')},calibration=cal,threshold=threshold)
        selected={x['proxy_carrier_index']:x['member_disposition'] for x in result['receiver_alias']['records'] if x['template_index']==1 and x['active_epochs_zero_based']==[0,1]}
        self.assertEqual(selected,{50:'rfi_veto_matched_off_same_hypothesis',100:'rfi_veto_local_off_track',150:'rfi_veto_single_adjacent_off',
            250:'rfi_veto_receiver_frame_alias',290:'rfi_veto_receiver_frame_alias',350:'pending_receiver_alias_evaluation'})


if __name__=='__main__':unittest.main()
