import copy,unittest
from types import SimpleNamespace as NS
import numpy as np
from seti_repeater.confirmation_m43z import apply_controls
from seti_repeater.injection_m43r import ScoreStore

class JointTests(unittest.TestCase):
    def fixture(self):
        grid=NS(score_bin_count=5,support_bin_count=133,score_slice=slice(64,69))
        on=np.zeros((3,133),dtype='<f4');off=on.copy()
        on[:,64:69]=np.array([[20,20,20,20,20],[4,3,4,4,4],[4,3,4,4,4]],dtype='<f4')
        off[0,66]=5.5;a={'members':[]}
        for i in range(5):
            a['members'].append(dict(record_id=str(i),template_index=0,proxy_carrier_index=i,spectral_width_channels=1,
                active_epochs_zero_based=[0,1,2],epoch_values_at_proxy_carrier=on[:,64+i].tolist(),
                physical_disposition='old_veto' if i==3 else 'pending_receiver_alias_evaluation',
                passes_evaluated_physical_vetoes=i!=3,meets_diagnostic_rank_cut=i!=4))
        return a,ScoreStore({('on',0,1):on,('off',0,1):off},{'family':'Z unit'}),grid
    def test_composition_intersection_prior_veto_rank_and_immutability(self):
        a,s,g=self.fixture();before=copy.deepcopy(a);out,e=apply_controls(a,s,g)
        expected={'neighbor9':{'0','1','2'},'off_window':{'0','1'},'remaining_aggregate':{'0','2'},'combined':{'0'}}
        for p,keys in expected.items():
            actual={m['record_id'] for m in out[p]['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
            self.assertEqual(actual,keys);self.assertFalse(out[p]['members'][3]['passes_evaluated_physical_vetoes'])
        self.assertEqual(a,before);self.assertTrue(e[0]['remaining']['remaining_passed'])
    def test_source_bound_scores(self):
        a,s,g=self.fixture();a['members'][0]['epoch_values_at_proxy_carrier'][0]+=1
        with self.assertRaises(ValueError):apply_controls(a,s,g)
if __name__=='__main__':unittest.main()
