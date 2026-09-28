"""Pure association gates on handcrafted decisions, not recovery measurements."""
import copy
import unittest
from radio_receiver_adapter_common import context
from seti_repeater import search_v0p6 as core
from seti_repeater.whole_cadence_reference_radio import Family,digest
from seti_repeater.whole_cadence_evaluation_radio import evaluate

NS='radio-whole-cadence-gates-engineering-20260928'


def fixture(c,kind='on_signal',rows=((0,1,2),),offsets=None,widths=None,finals=None,merged=False):
    # Template index 40 is the fixed zero-drift member of the 81-rate bank.
    recipe={'case_id':'handcrafted-decisions','kind':kind,'rate_label_hz_s':0,
        'activity_patterns':{k:{'on_epochs_zero_based':[0,1,2] if k!='single_adjacent_off' else [0,2],
                                'off_epochs_zero_based':[]} for k in ('on_signal','matched_on_off','single_adjacent_off')}}
    case={'namespace':NS,'recipe':recipe,'role':'evaluation','context_sha256':c.identity,
        'source_domain':'handcrafted-completed-engineering-decisions'}
    case['identity']=digest(case);records=[];decisions=[]
    offsets=offsets or [0]*len(rows);widths=widths or [1]*len(rows);finals=[True]*len(rows) if finals is None else finals
    for epochs,offset,width,final in zip(rows,offsets,widths,finals,strict=True):
        r={'schema':'handcrafted-retained-gate-fixture-v1','template_index':40,'spectral_width_index':core.M37_SPECTRAL_WIDTHS.index(width),
            'spectral_width_channels':width,'proxy_carrier_index':40+offset,
            'carrier_hz':float(c.grid.score_hz[40+offset]),'active_epochs_zero_based':list(epochs)}
        r['record_id']=digest(r);records.append(r)
        decisions.append({'record_id':r['record_id'],'passes_evaluated_physical_vetoes':final,
            'meets_diagnostic_rank_cut':True,'diagnostic_final':final,'scientific_candidate':False})
    retention={'complete':True,'case_identity':case['identity'],'retained':{'on':records,'off':[]}}
    retention['result_sha256']=digest(retention)
    groups=[records] if merged and records else [[r] for r in records]
    by_id={d['record_id']:d for d in decisions};clusters=[]
    for rs in groups:
        ids=[r['record_id'] for r in rs];clusters.append({'cluster_sha256':digest(ids),'member_ids':ids,'member_count':len(ids),
            'diagnostic_final_ids':[i for i in ids if by_id[i]['diagnostic_final']]})
    f=Family(c.identity,c.factor_contract.factors.identity,len(c.bank),c.grid)
    result={'schema':'radio-whole-cadence-physical-v1','complete':True,'family_sha256':digest(f.record()),
        'retention':retention,'decisions':decisions,'clusters':clusters,
        'engineering_fixture_not_a_detector_execution':True,'scientific_candidate_selection_authorized':False}
    result['result_sha256']=digest(result);return result,case


def reseal(r):
    r.pop('result_sha256',None);r['result_sha256']=digest(r)


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=context('validation')

    def evaluate(self,r,case,recipe=None):
        return evaluate(r,self.c,case['recipe'] if recipe is None else recipe,
            expected_case_identity=case['identity'],case_definition=case)

    def test_associated_on_recovery_counts_every_member_and_component(self):
        r,c=fixture(self.c,rows=((0,1),(0,2),(1,2),(0,1,2)),merged=True)
        out=self.evaluate(r,c);self.assertTrue(out['gate_pass']);self.assertEqual(out['counts']['associated_final_members'],4)
        self.assertEqual(out['counts']['associated_final_clusters'],1)

    def test_signal_with_no_final_member_fails(self):
        r,c=fixture(self.c,finals=[False]);self.assertFalse(self.evaluate(r,c)['gate_pass'])

    def test_unassociated_signal_does_not_count_as_recovery(self):
        r,c=fixture(self.c,offsets=[3]);out=self.evaluate(r,c)
        self.assertFalse(out['gate_pass']);self.assertEqual(out['counts']['unassociated_final_members'],1)

    def test_literal_two_channel_association_boundary(self):
        # Compare against the literal Hz expression, including binary64 grid rounding.
        r,c=fixture(self.c,rows=((0,1),(0,2)),offsets=[2,3]);out=self.evaluate(r,c)
        tolerance=2*self.c.geometry.channel_width_hz
        for x in out['association']:self.assertEqual(x['associated'],x['maximum_truth_track_error_hz']<=tolerance)
        self.assertFalse(out['association'][1]['associated'])

    def test_inactive_truth_epoch_cannot_associate(self):
        r,c=fixture(self.c,'single_adjacent_off',rows=((0,1),))
        out=self.evaluate(r,c);self.assertFalse(out['association'][0]['associated']);self.assertFalse(out['gate_pass'])

    def test_empty_null_passes_zero_control_gate(self):
        r,c=fixture(self.c,'noise_null',rows=());out=self.evaluate(r,c);self.assertTrue(out['gate_pass']);self.assertEqual(out['counts']['final_members'],0)

    def test_any_final_matched_off_control_fails_even_if_associated(self):
        r,c=fixture(self.c,'matched_on_off');out=self.evaluate(r,c)
        self.assertTrue(out['association'][0]['associated']);self.assertFalse(out['gate_pass'])

    def test_noise_null_has_no_associated_member(self):
        r,c=fixture(self.c,'noise_null');out=self.evaluate(r,c)
        self.assertEqual(out['counts']['associated_final_members'],0);self.assertFalse(out['gate_pass'])

    def test_broad_width_null_leakage_is_retained(self):
        r,c=fixture(self.c,'noise_null',rows=((0,1),(0,2)),widths=[65,129]);out=self.evaluate(r,c)
        self.assertFalse(out['broad_width_gate_pass'])
        self.assertEqual(out['broad_width_counts']['65']['unassociated_final_members'],1)
        self.assertEqual(out['broad_width_counts']['129']['unassociated_final_members'],1)

    def test_mixed_cluster_counts_in_both_categories(self):
        r,c=fixture(self.c,rows=((0,1),(0,2)),offsets=[0,3],merged=True);out=self.evaluate(r,c)
        self.assertEqual(out['counts']['final_clusters'],1)
        self.assertEqual(out['counts']['associated_final_clusters'],1);self.assertEqual(out['counts']['unassociated_final_clusters'],1)
        self.assertTrue(out['gate_pass'])

    def test_changed_report_rejected(self):
        r,c=fixture(self.c);r['complete']=False
        with self.assertRaisesRegex(ValueError,'Complete physical'):self.evaluate(r,c)

    def test_recipe_cannot_be_changed_for_fixed_case(self):
        r,c=fixture(self.c);recipe=copy.deepcopy(c['recipe']);recipe['rate_label_hz_s']=4
        with self.assertRaisesRegex(ValueError,'Truth recipe'):self.evaluate(r,c,recipe)

    def test_wrong_context_rejected(self):
        r,c=fixture(self.c);r['family_sha256']='e'*64;reseal(r)
        with self.assertRaisesRegex(ValueError,'context'):self.evaluate(r,c)

    def test_missing_decision_rejected(self):
        r,c=fixture(self.c);r['decisions']=[];reseal(r)
        with self.assertRaisesRegex(ValueError,'inventory'):self.evaluate(r,c)

    def test_missing_or_duplicate_cluster_member_rejected(self):
        r,c=fixture(self.c);r['clusters'][0]['member_ids']*=2;reseal(r)
        with self.assertRaisesRegex(ValueError,'partition'):self.evaluate(r,c)

    def test_cluster_cannot_hide_final_member(self):
        r,c=fixture(self.c);r['clusters'][0]['diagnostic_final_ids']=[];reseal(r)
        with self.assertRaisesRegex(ValueError,'partition'):self.evaluate(r,c)

    def test_retained_carrier_cannot_change_after_receipt(self):
        r,c=fixture(self.c);r['retention']['retained']['on'][0]['carrier_hz']+=1;reseal(r)
        with self.assertRaisesRegex(ValueError,'Retention receipt'):self.evaluate(r,c)

    def test_handcrafted_gate_pass_has_no_scientific_authority(self):
        r,c=fixture(self.c);out=self.evaluate(r,c)
        self.assertFalse(out['scientific_experiment_or_telescope_admission_authorized'])
        self.assertTrue(out['truth_used_only_after_decisions'])
        sha=out.pop('result_sha256');self.assertEqual(digest(out),sha)


if __name__=='__main__':unittest.main()
