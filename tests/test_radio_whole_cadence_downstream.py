"""New downstream boundaries; fixed fixtures with no scientific allocation."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core
from seti_repeater.empty_null_radio import canonical
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import Family, reduce_fixture, digest, CadenceMaximum
from seti_repeater.whole_cadence_downstream_radio import (
    WholeCadenceThreshold, bind_threshold, execute_fixture, IncompleteRetention, operator_binding,
)

NS='radio-whole-cadence-handoff-engineering-20260928'
ROOT=Path(__file__).resolve().parents[1]


def case(i): return hashlib.sha256(f'{NS}/score/{i}'.encode()).hexdigest()


class DownstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid=core.make_proxy_carrier_grid(1400.,2.8,2,9)
        cls.family=Family('a'*64,'b'*64,2,cls.grid);cls.law=digest({'kind':'fixed-score-fixture', 'namespace':NS})
        cls.units=tuple(cls.unit(i) for i in range(127));cls.threshold=cls.bind(cls.units)

    @classmethod
    def store(cls, i=200, edits=()):
        arrays={(k,t,w):np.zeros((3,cls.grid.support_bin_count),dtype='<f4')
                for k in ('on','off') for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
        for k,t,w,q,values in edits: arrays[k,t,w][:,q+9]=values
        return ScoreStore(arrays,{'context_sha256':cls.family.context_sha256,
            'case_identity':case(i),'source_domain':'deterministic-score-fixture'})

    @classmethod
    def unit(cls,i,edits=()):
        return reduce_fixture(cls.family,cls.store(i,edits),case_identity=case(i),noise_law_sha256=cls.law)

    @classmethod
    def bind(cls,units,**overrides):
        args=dict(source_family=cls.family,destination_family=cls.family,
            expected_case_identities=[case(i) for i in range(127)],noise_law_sha256=cls.law)
        return bind_threshold(units,**{**args,**overrides})

    def execute(self,edits=(),threshold=None,i=200,**caps):
        return execute_fixture(self.family,self.store(i,edits),threshold or self.threshold,
            case_identity=case(i),noise_law_sha256=self.law,**caps)

    def test_all_empty_threshold_is_floor_without_false_finite_null(self):
        r=self.threshold.record();self.assertEqual(r['operational_threshold'],10)
        self.assertEqual(r['reference_bundle']['empty_count'],127)
        self.assertTrue(all(v['kind']=='empty' for v in r['reference_bundle']['ordered_maxima']))

    def test_empty_observation_complete_inventory_and_rank_one(self):
        r=self.execute();self.assertTrue(r['complete']);self.assertEqual(r['retained'],{'on':[],'off':[]})
        self.assertEqual(r['observed_maximum_rank']['exact_fraction'],[1,1])
        for k in ('on','off'):
            self.assertEqual(r['enumeration'][k]['visited_hypotheses'],64)
            self.assertEqual(r['enumeration'][k]['scored_cells'],320)
        self.assertEqual(len(r['mask_receipts']),4)

    def test_all_cells_widths_templates_subsets_retained_against_scalar_oracle(self):
        edits=[(k,t,w,q,(8.,9.,10.)) for k in ('on','off') for t in range(2)
               for w in core.M37_SPECTRAL_WIDTHS for q in (0,2,4)]
        r=self.execute(edits);expected=[]
        for t in range(2):
            for wi,w in enumerate(core.M37_SPECTRAL_WIDTHS):
                for subset in core.M37_ACTIVITY_SUBSETS:
                    score=np.float32(0)
                    for epoch in subset:score=np.float32(score+np.float32((8,9,10)[epoch]))
                    score=float(np.float32(score/np.float32(len(subset)**.5)))
                    for q in (0,2,4):
                        if score>=10:expected.append((t,wi,w,tuple(subset),q,score))
        for k in ('on','off'):
            observed=[(x['template_index'],x['spectral_width_index'],x['spectral_width_channels'],
                tuple(x['active_epochs_zero_based']),x['proxy_carrier_index'],x['stack_snr']) for x in r['retained'][k]]
            self.assertEqual(observed,expected)
        self.assertEqual(len(expected),192)
        self.assertEqual(len({x['record_id'] for k in ('on','off') for x in r['retained'][k]}),384)

    def test_tie_retained_but_rank_fails_without_discard(self):
        units=list(self.units);units[12]=self.unit(12,[('on',0,1,2,(8,8,8))]);t=self.bind(units)
        r=self.execute([('on',1,129,2,(8,8,8))],t)
        self.assertEqual(len(r['retained']['on']),1)
        rank=r['retained']['on'][0]['rank'];self.assertEqual(rank['exact_fraction'],[1,64])
        self.assertEqual(rank['unreduced_numerator'],2);self.assertEqual(rank['reference_denominator'],128)
        self.assertFalse(rank['meets_rank_cut'])

    def test_one_over_128_with_all_empty_reference(self):
        r=self.execute([('on',1,129,2,(20,20,20))])
        self.assertEqual(len(r['retained']['on']),4)
        for row in r['retained']['on']:
            self.assertEqual(row['rank']['exact_fraction'],[1,128]);self.assertTrue(row['rank']['meets_rank_cut'])
            self.assertFalse(row['scientific_candidate']);self.assertEqual(row['physical_disposition'],'PENDING_PHYSICAL_STAGES')
        self.assertFalse(r['physical_vetoes_evaluated'])

    def test_off_records_do_not_receive_on_calibrated_rank(self):
        r=self.execute([('off',1,129,2,(20,20,20))])
        self.assertEqual(len(r['retained']['off']),4)
        self.assertTrue(all('rank' not in x for x in r['retained']['off']))

    def test_finite_below_floor_remains_finite_but_unretained(self):
        r=self.execute([('on',0,1,2,(3,3,0))])
        self.assertEqual(r['cadence_maximum_receipt']['maximum']['kind'],'finite')
        self.assertFalse(r['retained']['on'])

    def test_masked_isolated_epoch_does_not_become_trigger(self):
        r=self.execute([('on',0,1,2,(20,0,0))])
        self.assertEqual(r['enumeration']['on']['maximum']['kind'],'empty')
        self.assertGreater(sum(x['masked_cells'] for x in r['mask_receipts']),0)

    def test_reference_case_cannot_be_observation(self):
        with self.assertRaisesRegex(ValueError,'overlap'):self.execute(i=0)

    def test_wrong_law_cannot_enter_threshold(self):
        with self.assertRaisesRegex(ValueError,'Noise law'):
            self.threshold.validate(self.family,case_identity=case(200),noise_law_sha256='e'*64,domain='deterministic-score-fixture')

    def test_fixture_cannot_enter_native_reference_domain(self):
        with self.assertRaisesRegex(ValueError,'domain'):
            self.threshold.validate(self.family,case_identity=case(200),noise_law_sha256=self.law,domain='synthetic-native')

    def test_changed_family_cannot_enter_threshold(self):
        with self.assertRaisesRegex(ValueError,'Destination family'):
            self.threshold.validate(replace(self.family,receiver_bank_sha256='e'*64),case_identity=case(200),
                noise_law_sha256=self.law,domain='deterministic-score-fixture')

    def test_threshold_byte_change_rejected(self):
        value=self.threshold.record();value['operational_threshold']=1
        with self.assertRaisesRegex(ValueError,'Receipt changed'):WholeCadenceThreshold(canonical(value)).record()

    def test_rehashed_threshold_cannot_change_fixed_floor(self):
        value=self.threshold.record();value.pop('threshold_receipt_sha256');value['floor']=1
        value['threshold_receipt_sha256']=digest(value)
        with self.assertRaisesRegex(ValueError,'semantics'):WholeCadenceThreshold(canonical(value)).record()

    def test_rehashed_threshold_cannot_claim_admission(self):
        value=self.threshold.record();value.pop('threshold_receipt_sha256');value['telescope_admission_authorized']=True
        value['threshold_receipt_sha256']=digest(value)
        with self.assertRaisesRegex(ValueError,'authority'):WholeCadenceThreshold(canonical(value)).record()

    def test_short_reference_rejected(self):
        with self.assertRaises(ValueError):self.bind(self.units[:-1])

    def test_mixed_reference_domains_rejected(self):
        r=self.units[0].record();r.pop('receipt_sha256');r['domain']='synthetic-native';r['receipt_sha256']=digest(r)
        with self.assertRaisesRegex(ValueError,'Mixed'):
            self.bind((CadenceMaximum(canonical(r)),)+self.units[1:])

    def test_no_legacy_or_untyped_threshold(self):
        with self.assertRaisesRegex(ValueError,'Distinct whole-cadence'):
            execute_fixture(self.family,self.store(),object(),case_identity=case(200),noise_law_sha256=self.law)

    def test_missing_off_vector_fails_before_success(self):
        store=self.store();store.arrays.pop(('off',1,129))
        with self.assertRaisesRegex(ValueError,'Missing or extra'):
            execute_fixture(self.family,store,self.threshold,case_identity=case(200),noise_law_sha256=self.law)

    def test_changed_last_off_identity_rejected(self):
        store=self.store();store.expected_ids['off',1,129]='e'*64
        with self.assertRaises(ValueError):
            execute_fixture(self.family,store,self.threshold,case_identity=case(200),noise_law_sha256=self.law)

    def test_record_cap_preserves_partial_and_first_overflow_trigger(self):
        with self.assertRaises(IncompleteRetention) as caught:
            self.execute([('on',0,1,2,(20,20,20))],maximum_records=2)
        r=caught.exception.evidence;self.assertFalse(r['complete']);self.assertEqual(len(r['retained']['on']),2)
        self.assertEqual(r['failure']['first_unstored_trigger']['active_epochs_zero_based'],list(core.M37_ACTIVITY_SUBSETS[2]))
        self.assertNotIn('result_sha256',r)

    def test_byte_cap_keeps_crossing_trigger_as_failure_evidence(self):
        with self.assertRaises(IncompleteRetention) as caught:
            self.execute([('off',1,129,4,(20,20,20))],maximum_evidence_bytes=1)
        self.assertFalse(caught.exception.evidence['complete'])
        self.assertEqual(caught.exception.evidence['failure']['kind'],'off')
        self.assertEqual(caught.exception.evidence['failure']['first_unstored_trigger']['proxy_carrier_index'],4)

    def test_off_eligible_overflow_is_error_not_empty(self):
        x=float(np.finfo(np.float32).max)
        with self.assertRaises(IncompleteRetention) as caught:self.execute([('off',1,129,2,(x,x,x))])
        self.assertIn('nonfinite',str(caught.exception));self.assertFalse(caught.exception.evidence['complete'])

    def test_caps_cannot_be_enlarged_or_boolean(self):
        for cap in (True,-1,10001):
            with self.assertRaisesRegex(ValueError,'cap'):self.execute(maximum_records=cap)

    def test_result_and_record_hashes_bind_complete_evidence(self):
        r=self.execute([('on',1,65,4,(20,20,20))]);checksum=r.pop('result_sha256');self.assertEqual(digest(r),checksum)
        for row in r['retained']['on']:
            checksum=row.pop('record_id');self.assertEqual(digest(row),checksum)


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from radio_receiver_adapter_common import context
        cls.contexts=(context('calibration'),context('validation'))
        cls.families=tuple(Family(c.identity,c.factor_contract.factors.identity,len(c.bank),c.grid) for c in cls.contexts)
        cls.proof=(ROOT/'results_radio_hd189733_score_map_2026-09-28/result.json').read_bytes()

    def test_published_translation_consumed_without_new_noise_claim(self):
        r=operator_binding(*self.families,self.proof,self.contexts)
        self.assertEqual(r['kind'],'published-translated-score-operator')
        self.assertFalse(r['noise_distribution_transfer_qualified'])
        self.assertFalse(r['absolute_frequency_veto_transfer_qualified'])

    def test_translation_needs_actual_contexts(self):
        with self.assertRaisesRegex(ValueError,'Both validated'):operator_binding(*self.families,self.proof)

    def test_modified_proof_rejected(self):
        with self.assertRaisesRegex(ValueError,'Exact published'):operator_binding(*self.families,self.proof+b' ',self.contexts)

    def test_wrong_grid_with_correct_claimed_context_rejected(self):
        fake=replace(self.families[1],grid=core.make_proxy_carrier_grid(1400.,2.8,40,9))
        with self.assertRaisesRegex(ValueError,'Grid/family'):
            operator_binding(self.families[0],fake,self.proof,self.contexts)

    def test_reversed_contexts_cannot_bind_ordered_families(self):
        with self.assertRaisesRegex(ValueError,'Grid/family'):
            operator_binding(*self.families,self.proof,tuple(reversed(self.contexts)))


if __name__=='__main__':unittest.main()
