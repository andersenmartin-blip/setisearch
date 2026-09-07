import copy
import math
import unittest
from itertools import permutations
from types import SimpleNamespace as NS
import numpy as np
from seti_repeater.confirmation_m43x import remaining_evidence,apply_controls
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater import search_v0p6 as core

class RemainingTests(unittest.TestCase):
    def test_scalar_permutations_all_subsets(self):
        for values in permutations([3.,5.,20.]):
            for active in core.M37_ACTIVITY_SUBSETS:
                e=remaining_evidence(values,active)
                ordered=sorted((values[i],i) for i in active)
                ref=math.fsum(x[0] for x in ordered[:-1])/math.sqrt(len(active)-1)
                self.assertEqual(e['remaining_score'],ref)
                self.assertEqual(e['remaining_passed'],ref>=5.5)
                if len(active)==2:self.assertEqual(e['remaining_passed'],e['active_confirmation_passed'])

    def test_threshold_ties_and_inactive_epoch(self):
        self.assertTrue(remaining_evidence([100,5.5,-999],[0,1])['remaining_passed'])
        self.assertFalse(remaining_evidence([100,np.nextafter(5.5,0),999],[0,1])['remaining_passed'])
        e=remaining_evidence([6,6,6],[0,1,2]);self.assertEqual(e['excluded_epoch'],0)
        self.assertEqual(e['remaining_epochs'],[1,2])
        self.assertTrue(remaining_evidence([20,4,4],[0,1,2])['remaining_passed'])
        self.assertFalse(remaining_evidence([20,3,3],[0,1,2])['remaining_passed'])

    def test_policies_prior_veto_and_input_immutability(self):
        g=NS(score_bin_count=5,score_slice=slice(0,5))
        v=np.array([[20,20,8,20,20],[4,3,8,4,4],[4,3,8,4,4]],dtype='<f4')
        a={'members':[]}
        for i in range(5):
            a['members'].append(dict(record_id=str(i),template_index=0,spectral_width_channels=1,
                proxy_carrier_index=i,active_epochs_zero_based=[0,1,2],epoch_values_at_proxy_carrier=v[:,i].tolist(),
                passes_evaluated_physical_vetoes=i!=3,meets_diagnostic_rank_cut=i!=4,
                physical_disposition='old_veto' if i==3 else 'pending_receiver_alias_evaluation'))
        store=ScoreStore({('on',0,1):v},{'family':'unit'});before=copy.deepcopy(a)
        out,_=apply_controls(a,store,g);self.assertEqual(a,before)
        self.assertEqual([out[p]['final_diagnostic_survivors'] for p in out],[3,1,2])
        for p in out:self.assertFalse(out[p]['members'][3]['passes_evaluated_physical_vetoes'])
        a['members'][0]['epoch_values_at_proxy_carrier'][0]+=1
        with self.assertRaises(ValueError):apply_controls(a,store,g)

    def test_invalid_evidence_fails_closed(self):
        for v in ([1,2],[1,2,3,4],[1,np.nan,3],[1,np.inf,3]):
            with self.assertRaises(ValueError):remaining_evidence(v,[0,1])
        for a in ([0],[0,0],[1,0],[0,3]):
            with self.assertRaises(ValueError):remaining_evidence([1,2,3],a)

if __name__=='__main__':unittest.main()
