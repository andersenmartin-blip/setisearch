import unittest
import copy
from types import SimpleNamespace as NS
import numpy as np
from seti_repeater.confirmation_m43w import off_window,apply_controls,POLICIES
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater import search_v0p6 as core

class ConfirmationTests(unittest.TestCase):
    def setUp(self):self.grid=NS(score_bin_count=9,support_bin_count=137,score_slice=slice(64,73))

    def test_inclusive_threshold_width_boundary_and_inactive_epoch(self):
        v=np.zeros((3,137),dtype='<f4');v[0,64+4+4]=5.5
        self.assertTrue(off_window(v,self.grid,4,9,[0,1])['vetoed'])
        self.assertFalse(off_window(v,self.grid,4,5,[0,1])['vetoed'])
        self.assertFalse(off_window(v,self.grid,4,9,[1,2])['vetoed'])
        v[0,72]=np.nextafter(np.float32(5.5),np.float32(0))
        self.assertFalse(off_window(v,self.grid,4,9,[0,1])['vetoed'])

    def test_full_guard_edges_and_independent_scalar_maxima(self):
        rng=np.random.default_rng(430023);v=rng.normal(size=(3,137)).astype('<f4')
        for q in (0,4,8):
            for w in core.M37_SPECTRAL_WIDTHS:
                a=off_window(v,self.grid,q,w,[0,1,2]);center=64+q
                expected=[max(float(v[e,j]) for j in range(center-w//2,center+w//2+1)) for e in range(3)]
                self.assertEqual(a['maxima'],expected)
        with self.assertRaises(core.V0P6CoverageError):off_window(v,NS(score_bin_count=9,support_bin_count=137,score_slice=slice(0,9)),0,129,[0,1])

    def test_all_four_outcomes_and_preserve_prior_veto(self):
        def member(i,on,prior=True):return dict(record_id=str(i),template_index=0,spectral_width_channels=1,
            proxy_carrier_index=i,active_epochs_zero_based=[0,1],epoch_values_at_proxy_carrier=on,
            physical_disposition='pending_receiver_alias_evaluation' if prior else 'old_veto',
            passes_evaluated_physical_vetoes=prior,meets_diagnostic_rank_cut=True)
        a={'members':[member(0,[6,6,0]),member(1,[6,4,0]),member(2,[6,6,0]),member(3,[6,4,0]),member(4,[6,6,0],False)]}
        before=copy.deepcopy(a);v=np.zeros((3,137),dtype='<f4');v[0,[66,67]]=5.5
        store=ScoreStore({('off',0,1):v},{'family':'unit'})
        result,e=apply_controls(a,store,self.grid)
        self.assertEqual(a,before)
        expected={'neighbor9':{'0','1','2','3'},'off_window':{'0','1'},'epoch_confirmation':{'0','2'},'combined':{'0'}}
        for p in POLICIES:
            actual={m['record_id'] for m in result[p]['members'] if m['passes_evaluated_physical_vetoes']}
            self.assertEqual(actual,expected[p])
        a['members'][0]['epoch_values_at_proxy_carrier']=[5.5,5.5,0]
        self.assertTrue(apply_controls(a,store,self.grid)[1][0]['active_confirmation_passed'])

    def test_corrupt_and_incomplete_evidence_fail_closed(self):
        v=np.zeros((3,137),dtype='<f4');v[1,20]=np.nan
        with self.assertRaises(ValueError):off_window(v,self.grid,0,1,[0,1])
        with self.assertRaises(ValueError):off_window(np.zeros((3,137)),self.grid,0,1,[0,1])
        with self.assertRaises(ValueError):off_window(np.zeros((3,137),dtype='<f4'),self.grid,9,1,[0,1])

if __name__=='__main__':unittest.main()
