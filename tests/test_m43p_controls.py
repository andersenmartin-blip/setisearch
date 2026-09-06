"""Boundary and adversarial tests for the combined M43P controls."""
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
import test_m43i_transfer as fixture_module
from seti_repeater import transfer_m43i as transfer
from seti_repeater import search_v0p6 as core
from seti_repeater.adjacent_m43p import gather_score_indices, paired_off_decision
from m43p_reference import mask_reference, masked_stack_reference, scramble_reference
from m43p_combined_controls import make_accumulator


class CombinedControlsTests(unittest.TestCase):
    def test_sparse_all_widths_repeated_mapping_order_and_duplicate_queries(self):
        source, grid, factors = fixture_module.TelescopeTransferTests().fixture()
        selected = np.array([grid.score_bin_count-1,0,17,17,18,1], dtype=np.int64)
        for width in core.M37_SPECTRAL_WIDTHS:
            cache = transfer.build_telescope_cache(source, factors, grid, width, bank_sha256='1'*64)
            full = transfer.gather_bank_slice(cache, 0, grid.support_bin_count)
            for chunk in (1,4,100):
                actual = gather_score_indices(cache, selected, chunk_bins=chunk)
                np.testing.assert_array_equal(actual, full[:,selected+grid.support_guard_bins])
                np.testing.assert_array_equal(gather_score_indices(cache, selected, template_indices=[1]), actual[1:2])
            self.assertEqual(gather_score_indices(cache, np.array([],dtype=np.int64)).shape, (2,0))

    def test_sparse_rejects_bad_indices_and_changed_cache(self):
        source, grid, factors = fixture_module.TelescopeTransferTests().fixture()
        cache = transfer.build_telescope_cache(source, factors, grid, 1, bank_sha256='1'*64)
        for selected in ([True,2],[-1],[grid.score_bin_count],[1.0],[[1]], [False]):
            with self.assertRaises(ValueError): gather_score_indices(cache, selected)
        for bad in (replace(cache,bank_sha256='0'*64), replace(cache,values=cache.values.copy()),
                    replace(cache,source=replace(source,trusted_receipt_sha256='0'*64))):
            with self.assertRaises(ValueError): gather_score_indices(bad, [0])

    def test_masks_boundaries_width_union_clipping_and_inactive_epochs(self):
        arrays = {w:np.zeros((3,101),dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        strong = np.float32(core.M37_RFI_STRONG_SNR)
        ceiling = np.float32(core.M37_RFI_OTHER_EPOCHS_BELOW_SNR)
        arrays[1][0,0] = strong
        arrays[129][2,-1] = strong
        arrays[3][0,40] = np.nextafter(strong,np.float32(-np.inf))
        arrays[5][0,50] = strong; arrays[5][1,50] = ceiling
        arrays[9][1,70] = strong; arrays[9][2,70] = np.nextafter(ceiling,np.float32(-np.inf))
        actual = core.build_m37_two_pass_template_mask(arrays.__getitem__)
        np.testing.assert_array_equal(actual, mask_reference(arrays))
        self.assertTrue(actual[0,:10].all()); self.assertFalse(actual[0,-1])
        self.assertTrue(actual[2,-10:].all()); self.assertFalse(actual[:,40:60].any())
        vectors = np.full((3,101),4,dtype='<f4')
        for subset in core.M37_ACTIVITY_SUBSETS:
            np.testing.assert_array_equal(core.stack_hypothesis(vectors,subset,
                minimum_active_epoch_snr=3,stack_statistic='sum',exclusion_mask=actual),
                masked_stack_reference(vectors,subset,actual))
        self.assertTrue(np.isfinite(masked_stack_reference(vectors,(0,1),actual)[-1]))

    def test_scramble_moves_mask_with_scores_and_wraps_only_score_domain(self):
        arrays = {w:np.full((3,31),4,dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        arrays[1][0,0]=30; arrays[1][1,5]=100; arrays[1][2,11]=50
        mask=np.zeros((3,31),dtype=bool); mask[1,5]=True
        shifts=np.array([[0,2,3],[0,29,28]],dtype=np.int64)
        expected=scramble_reference(arrays,mask,shifts)
        actual=[]; incorrect=[]
        for shifts_row in shifts:
            moved_mask=np.array([np.roll(mask[e],s) for e,s in enumerate(shifts_row)])
            maxima=[-np.inf,-np.inf]
            for vectors in arrays.values():
                moved=np.array([np.roll(vectors[e],s) for e,s in enumerate(shifts_row)])
                for subset in core.M37_ACTIVITY_SUBSETS:
                    for k,m in enumerate((moved_mask,mask)):
                        score=core.stack_hypothesis(moved,subset,minimum_active_epoch_snr=3,
                            stack_statistic='sum',exclusion_mask=m)
                        maxima[k]=max(maxima[k],float(score.max()))
            actual.append(maxima[0]);incorrect.append(maxima[1])
        np.testing.assert_array_equal(actual,expected)
        self.assertTrue(np.any(np.array(incorrect)>expected))

    def test_paired_off_inclusive_floor_and_inactive_epoch(self):
        low=np.nextafter(np.float32(5.5),np.float32(-np.inf))
        scores=np.array([[low,5.5,0,0],[0,0,5.5,0],[100,0,0,5.5]],dtype='<f4')
        np.testing.assert_array_equal(paired_off_decision(scores,(0,1)),[False,True,True,False])
        for subset in core.M37_ACTIVITY_SUBSETS:
            expected=[any(float(scores[e,q])>=5.5 for e in subset) for q in range(4)]
            np.testing.assert_array_equal(paired_off_decision(scores,subset),expected)
        with self.assertRaises(ValueError):paired_off_decision(scores.astype('<f8'),(0,1))
        with self.assertRaises(ValueError):paired_off_decision(scores,(0,))

    def test_real_runner_accumulator_wiring_on_small_injected_scores(self):
        shifts=np.array([[0,2,3],[0,10,12],[0,15,17],[0,25,27]],dtype=np.int64)
        cfg={'bank_sha256':'1'*64,'factor_table_sha256':'2'*64,'score_carriers':31,
             'widths':list(core.M37_SPECTRAL_WIDTHS),'minimum_shift_bins':1,
             'scramble_table_sha256':core.scramble_table_sha256(shifts)}
        arrays={w:np.full((3,31),4,dtype='<f4') for w in cfg['widths']}
        arrays[1][0,5]=100;arrays[1][1,7]=100;arrays[1][2,9]=100
        mask=np.zeros((3,31),dtype=bool);mask[1,7]=True
        for kind in ('on','off'):
            acc=make_accumulator(cfg,kind,1696,shifts)
            for wi,w in enumerate(cfg['widths']):
                core.update_calibration(acc,arrays[w],template_index=0,width_index=wi,exclusion_mask=mask)
            np.testing.assert_array_equal(acc.null_maxima,scramble_reference(arrays,mask,shifts))
            self.assertEqual(acc.observed_score_cells,32*31)
            self.assertEqual(acc.null_score_cells,4*32*31)
            self.assertEqual(len(acc._visited_hypothesis_keys),32)


if __name__=='__main__':unittest.main()
