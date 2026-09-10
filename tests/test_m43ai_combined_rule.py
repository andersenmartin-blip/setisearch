import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

import m43ai_combined_rule as rule
import m43ai_design as design
import m43ai_native_validation as native


def model():
    return dict(schema='m43ai-two-rectangle-or-v1',operator='member_or',branches=[
        dict(feature='second_epoch_on',on_lower=10.,off_upper=2.),
        dict(feature='second_epoch_excess',on_lower=4.,off_upper=6.)])


def feature(rid='a',raw=11.,excess=0.,off=1.):
    return dict(record_id=rid,second_epoch_on=raw,second_epoch_excess=excess,
                original_m43af_coordinate=dict(on=-100.,off=off))


def case(features,signal=True,associated=('a',)):
    return dict(name='case',panel='training',signal_present=signal,complete=True,
        members=[dict(record_id=f['record_id'],coordinate=f['original_m43af_coordinate']) for f in features],
        associated_record_ids=list(associated),reference_recovered={p:signal for p in rule.ag.REFERENCES})


class MemberTests(unittest.TestCase):
    def test_each_branch_both_and_neither(self):
        expected=[(['second_epoch_on'],11,0,1),(['second_epoch_excess'],0,5,3),
                  (list(rule.METHODS),11,5,1),([],0,0,1)]
        for names,raw,excess,off in expected:
            self.assertEqual(rule.accepted_branches(model(),feature(raw=raw,excess=excess),off),names)

    def test_inclusive_on_strict_off_and_nextafter(self):
        self.assertEqual(rule.accepted_branches(model(),feature(raw=10),math.nextafter(2.,-math.inf)),['second_epoch_on'])
        self.assertEqual(rule.accepted_branches(model(),feature(raw=10),2.),[])
        self.assertEqual(rule.accepted_branches(model(),feature(raw=math.nextafter(10.,-math.inf)),1.),[])
        self.assertEqual(rule.accepted_branches(model(),feature(raw=0,excess=4),math.nextafter(6.,-math.inf)),['second_epoch_excess'])

    def test_incomplete_second_feature_cannot_short_circuit(self):
        for bad in (math.nan,math.inf,-math.inf,True,'5'):
            with self.assertRaises(ValueError):
                rule.accepted_branches(model(),feature(excess=bad),1.)

    def test_negative_values_and_unbounded_off(self):
        m=model();m['branches'][0].update(on_lower=-2.,off_upper=None)
        self.assertEqual(rule.accepted_branches(m,feature(raw=-1.,excess=-5),1000.),['second_epoch_on'])

    def test_truth_fields_have_no_effect(self):
        f=feature();baseline=rule.accepted_branches(model(),f,1.)
        f.update(signal_present=False,associated_record_ids=[],truth={'score_index':999999})
        self.assertEqual(rule.accepted_branches(model(),f,1.),baseline)

    def test_wrong_model_family_or_operator_rejected(self):
        for key,value in [('operator','case_max'),('schema','old')]:
            m=model();m[key]=value
            with self.assertRaises(ValueError):rule.validate_model(m)
        m=model();m['branches'].reverse()
        with self.assertRaises(ValueError):rule.validate_model(m)


class AccountingTests(unittest.TestCase):
    def test_member_coordinates_cannot_be_mixed(self):
        fs=[feature('a',raw=20,off=20),feature('b',raw=0,off=1)]
        out=rule.case_endpoint(case(fs),fs,model())
        self.assertFalse(out['recovered']);self.assertEqual(out['accepted_record_ids'],[])

    def test_unassociated_survivor_is_not_signal_recovery(self):
        fs=[feature('b')]
        out=rule.case_endpoint(case(fs),fs,model())
        self.assertFalse(out['recovered']);self.assertEqual(out['unassociated_accepted_ids'],['b'])

    def test_control_member_and_false_association_both_count(self):
        fs=[feature()]
        out=rule.case_endpoint(case(fs,False),fs,model())
        self.assertTrue(out['control_leak']);self.assertTrue(out['false_control_association'])

    def test_complete_identity_required(self):
        fs=[feature()];c=case(fs)
        variants=[[],fs+fs,[feature('b')]]
        for broken in variants:
            with self.assertRaises(ValueError):rule.case_endpoint(c,broken,model())
        c['complete']=False
        with self.assertRaises(ValueError):rule.case_endpoint(c,fs,model())

    def test_old_off_binding_required(self):
        fs=[feature()];c=copy.deepcopy(case(fs));fs[0]['original_m43af_coordinate']['off']=99
        with self.assertRaises(ValueError):rule.case_endpoint(c,fs,model())

    def test_per_reference_losses_and_no_hidden_denominator(self):
        fs=[feature(raw=0)];c=case(fs);r=rule.case_endpoint(c,fs,model())
        totals=rule.summarize([r])
        self.assertEqual(totals['required_signal_losses'],['case'])
        self.assertEqual(totals['lost_signal_cases'],['case'])
        self.assertFalse(totals['joint_case_requirements_passed'])

    def test_scalar_audit_detects_false_recovery(self):
        fs=[feature()];c=case(fs);out=rule.case_endpoint(c,fs,model())
        ledger=[dict(name=c['name'],members=fs)]
        self.assertTrue(rule.scalar_endpoint_audit([c],ledger,model(),[out])['passed'])
        out['associated_accepted_ids']=[]
        with self.assertRaises(ValueError):rule.scalar_endpoint_audit([c],ledger,model(),[out])


class SelectionTests(unittest.TestCase):
    def family(self):
        rows=[dict(lower_kind='above_maximum',on_lower=None,control_free_off_upper=None,control_free_required_losses=['x','y']),
              dict(lower_kind='finite',on_lower=10,control_free_off_upper=2,control_free_required_losses=['x']),
              dict(lower_kind='finite',on_lower=8,control_free_off_upper=1,control_free_required_losses=['x'])]
        return dict(result=dict(sweep=rows,minimum_required_losses_with_zero_leaks=1,control_free_optimal_state_indices=[1,2]))

    def test_first_optimum_is_the_only_deterministic_selection(self):
        f={m:self.family() for m in rule.METHODS}
        got=rule.select_model(f)
        self.assertEqual([b['source_state_index'] for b in got['branches']],[1,1])
        self.assertEqual([b['on_lower'] for b in got['branches']],[10,10])

    def test_incomplete_optimum_ledger_rejected(self):
        f={m:self.family() for m in rule.METHODS}
        f[rule.METHODS[0]]['result']['control_free_optimal_state_indices']=[2]
        with self.assertRaises(ValueError):rule.select_model(f)


class DesignTests(unittest.TestCase):
    def test_all_component_carriers_and_strengths_transformed_without_mutation(self):
        original=dict(name='training000',score_index=1000,strength=28,
            reference_truth=dict(score_index=1000),components=[dict(strength=112,truth=dict(score_index=1012))])
        before=copy.deepcopy(original);got=design.translated_case(original,7)
        self.assertEqual(original,before)
        self.assertEqual(got['score_index'],1211)
        self.assertEqual(got['reference_truth']['score_index'],1211)
        self.assertEqual(got['components'][0]['truth']['score_index'],1223)
        self.assertEqual(got['strength'],26.25)
        self.assertEqual(got['components'][0]['strength'],105.)
        self.assertEqual(got['name'],'ai_validation007')

    def test_null_inventory_is_deterministic_disjoint_and_bounded(self):
        first=design.new_shifts([],4)
        rows=design.new_shifts(first,128)
        self.assertEqual(rows,design.new_shifts(first,128))
        self.assertEqual(len({tuple(r) for r in rows}),128)
        self.assertFalse({tuple(r) for r in rows}&{tuple(r) for r in first})
        self.assertTrue(all(r[0]==0 and all(128<=s<=3967 for s in r[1:]) and abs(r[1]-r[2])>=128 for r in rows))


class PublicationTests(unittest.TestCase):
    def setup_model(self):
        m=model();m.update(config_sha256='config',protocol_commit='a'*40,training_eligible=True)
        m=rule.sealed(m)
        receipt=rule.sealed(dict(kind='model',remote_verified=True,model_sha256=m['result_sha256'],commit='b'*40))
        return m,receipt

    def test_public_model_required_before_native_work(self):
        m,r=self.setup_model()
        native.verify_model_publication(m,r,'config','a'*40)
        for key,value in [('remote_verified',False),('model_sha256','other'),('kind','protocol')]:
            bad=rule.sealed(dict(r,**{key:value}))
            with self.assertRaises(ValueError):native.verify_model_publication(m,bad,'config','a'*40)

    def test_ineligible_training_model_cannot_open_validation(self):
        m,r=self.setup_model();m=rule.sealed(dict(m,training_eligible=False))
        r=rule.sealed(dict(r,model_sha256=m['result_sha256']))
        with self.assertRaises(ValueError):native.verify_model_publication(m,r,'config','a'*40)

    def test_sealed_model_and_checkpoint_cannot_change_silently(self):
        m,r=self.setup_model();m['branches'][0]['on_lower']=9.
        with self.assertRaises(ValueError):native.verify_model_publication(m,r,'config','a'*40)
        m,_=self.setup_model();spec={'name':'new'}
        record=rule.sealed(dict(spec=spec,phase='ai_validation',model_sha256=m['result_sha256'],protocol_commit='a'*40,config_sha256='config'))
        native.verify_saved(record,spec,'ai_validation',m,'a'*40,'config')
        with self.assertRaises(ValueError):native.verify_saved(record,{'name':'other'},'ai_validation',m,'a'*40,'config')

    def test_public_receipt_binds_all_frozen_file_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'receipt.json'
            rule.save(p,rule.sealed(dict(kind='protocol',remote_verified=True,files={'script':'sha'},commit='a'*40)))
            rule.verify_public_receipt(p,'protocol',{'script':'sha'})
            with self.assertRaises(ValueError):rule.verify_public_receipt(p,'protocol',{'script':'changed'})

    def test_different_completed_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json';rule.save(p,{'x':1})
            with self.assertRaises(ValueError):rule.save(p,{'x':2})
            self.assertEqual(json.loads(p.read_text()),{'x':1})


if __name__=='__main__':unittest.main()
