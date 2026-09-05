"""Diagnostic gate truth table and hand-constructed handoff/clone controls."""
import copy
import itertools
import unittest
import numpy as np
from ls4n_reference_policy import policies,build,load,CLONES,measured,evaluate
from ls4m_control_morphology import selections
from ls4g_synthetic_recovery import evaluate as original_evaluate

C=load('config/ls4n_reference_policy.json')


class ReferencePolicyTests(unittest.TestCase):
    def test_exhaustive_policy_truth_table(self):
        for supported,onref,inside,reference in itertools.product((False,True),repeat=4):
            for count in (0,2,3,6):
                result=policies(supported,onref,inside,reference,count)
                old=supported and not onref and not inside and not reference
                new=supported and not onref and not inside
                self.assertEqual(result['original_htr_pass'],old)
                self.assertEqual(result['counterfactual_htr_pass'],new)
                self.assertEqual(result['counterfactual_truth_pass'],new and count>=3)
                self.assertEqual(result['new_diagnostic_pass'],new and not old)
                self.assertFalse(result['sky_candidate_promoted'])
                if new and not old:self.assertEqual(result['off_state'],'reference_only')

    def test_exact_control_locations_and_clone_inputs(self):
        base=np.zeros((2,C['sample_count']))
        spec={'family':'train_clean','width_s':.012,'amplitude_sigma':8.}
        clean,_,_=build(base,C['pulse_times_s'],spec,C)
        for family,destination,expected in [('train_off_inside',1,50.25),('train_off_reference_early',1,15.25),
                ('train_off_reference_late',1,105.25),('train_on_reference',0,15.25)]:
            pair,_,_=build(base,C['pulse_times_s'],{**spec,'family':family},C)
            delta=pair-clean;indices=np.flatnonzero(delta[destination])
            self.assertEqual(len(indices),12)
            self.assertAlmostEqual(float(((indices+.5)*.001).mean()),expected)
            self.assertTrue(np.all(delta[1-destination]==0))
        for clone,original in CLONES.items():
            a,ta,ca=build(base,C['pulse_times_s'],{**spec,'family':clone},C)
            b,tb,cb=build(base,C['pulse_times_s'],{**spec,'family':original},C)
            np.testing.assert_array_equal(a,b);self.assertEqual(ta,tb);self.assertEqual(ca,cb)
        self.assertTrue(np.all(base==0))

    def test_real_residual_rule_preserved_in_smoke_controls(self):
        base=np.random.default_rng(901).normal(100,1,(2,C['sample_count']))
        settings=load('config/ls4e_residual_qualification.json')['settings']
        for family in ('train_off_inside','train_off_reference_early','train_on_reference'):
            pair,truth,_=build(base,C['pulse_times_s'],{'family':family,'width_s':.012,'amplitude_sigma':16.},C)
            result=evaluate(pair,truth,C,settings);original=original_evaluate(pair,truth,C,settings)
            self.assertEqual(result['original_htr_pass'],original['passed'])
            self.assertEqual(result['original_truth_pass'],original['recovered'])
            self.assertTrue(result['supported'])
            self.assertEqual(result['counterfactual_truth_pass'],family=='train_off_reference_early')

    def fixture(self):
        rows=[];reviews=[]
        for ti,(fi,wi,width,medium) in enumerate(itertools.product(range(2),range(2),(.003,.012,.1),(1.,4.,16.))):
            for amplitude in (0.,4.,8.,16.):
                event={'band_indices':[10,21],'event_window_s':[30.,70.],'off_counts':[1]*6,'off_veto':True,
                    'stage1_off_survives':False,'cross_scale_supported':amplitude>0,'reference_veto':False,
                    'matched_truth_pulses':3 if amplitude else 0,'passed':False,'truth_associated_pass':False}
                events=[copy.deepcopy(event) for _ in range(64)] if ti==0 else []
                rows.append({'frequency_index':fi,'window_index':wi,'pulse_width_s':width,'medium_amplitude':medium,
                    'htr_amplitude':amplitude,'events':events,'joint_digital_pass':False})
                reviews.append({'events':[{'original_stage1_off_vetoes':[{'off_label':'B1','off_score':10.}]} for _ in events]})
        fixed=[{'band_indices':[40,73],'event_window_s':[30.,70.],'frequency_index':0,'off_counts':[0]*6,'off_veto':False} for _ in range(48)]
        previous={'paired_configurations':rows,'review_configurations':reviews,'fixed_window_diagnostics':fixed}
        records=[]
        for selection in selections(previous):
            has=bool(selection['uses'])
            records.append({**selection,'residual_metrics':{'envelope_s':selection['event_window_s'],
                'scales':[{'inside_pulses':[],'reference_pulses':[{}] if has else []} for _ in range(6)]}})
        return previous,{'records':records}

    def test_zero_comparison_and_retained_original_stage1_evidence(self):
        previous,morphology=self.fixture(); before=copy.deepcopy(previous)
        rows=measured(previous,morphology)
        self.assertEqual(sum(r['counterfactual_truth_pass_any'] for r in rows),3)
        self.assertEqual(sum(r['counterfactual_truth_pass_absent_at_zero_any'] for r in rows),3)
        self.assertTrue(all(not r['original_joint_pass'] and not r['sky_candidate_promoted'] for r in rows))
        self.assertEqual(previous,before)
        for r in rows:
            for e in r['events']:self.assertEqual(e['original_stage1_evidence'],[{'off_label':'B1','off_score':10.}])

    def test_tampered_join_and_original_veto_rejected(self):
        for key,value in [('off_counts',[0]*6),('stage1_off_survives',True),('passed',True)]:
            previous,morphology=self.fixture();previous['paired_configurations'][0]['events'][0][key]=value
            with self.assertRaises(ValueError):measured(previous,morphology)

    def test_frozen_inventory_and_null_truth(self):
        self.assertEqual(len(C['families'])*len(C['seeds'])*len(C['backgrounds'])*len(C['widths_s'])*len(C['amplitudes_sigma']),1296)
        base=np.zeros((2,C['sample_count']))
        for family,count in [('null_off_reference',0),('single_off_reference',1)]:
            _,truth,_=build(base,C['pulse_times_s'],{'family':family,'width_s':.012,'amplitude_sigma':8.},C)
            self.assertEqual(len(truth),count)


if __name__=='__main__':unittest.main()
