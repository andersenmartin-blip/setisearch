"""New reference boundary only: deterministic score fixtures, no RNG/native data."""
import hashlib
import json
import math
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core
from seti_repeater.empty_null_radio import canonical
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import (
    CadenceMaximum, Family, digest, reduce_fixture, reduce_native_run, reference_bundle,
)


def case_id(index):
    return hashlib.sha256(f'whole-cadence-engineering-fixture/{index:03d}'.encode()).hexdigest()


class WholeCadenceReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = core.make_proxy_carrier_grid(1400., 2.8, 2, 9)
        cls.family = Family('a'*64, 'b'*64, 2, cls.grid)
        cls.law = 'c'*64
        cls.units = tuple(cls.unit(i) for i in range(127))
        cls.reference_args = {
            'expected_case_identities': tuple(case_id(i) for i in range(127)),
            'expected_family_sha256': digest(cls.family.record()),
            'expected_noise_law_sha256': cls.law,
            'destination_context_sha256': 'd'*64,
            'operator_translation_proof_sha256': 'e'*64,
        }

    @classmethod
    def store(cls, index=0, edits=None):
        arrays = {(kind,t,w): np.zeros((3,cls.grid.support_bin_count), dtype='<f4')
                  for kind in ('on','off') for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
        for key, epochs in (edits or {}).items():
            arrays[key][:,cls.grid.support_bin_count//2] = epochs
        return ScoreStore(arrays, {'context_sha256':cls.family.context_sha256,
            'case_identity':case_id(index), 'source_domain':'deterministic-score-fixture'})

    @classmethod
    def unit(cls, index=0, edits=None):
        return reduce_fixture(cls.family, cls.store(index, edits),
                              case_identity=case_id(index), noise_law_sha256=cls.law)

    def reduce(self, store):
        return reduce_fixture(self.family, store, case_identity=case_id(0), noise_law_sha256=self.law)

    def test_complete_empty_family_has_full_denominator_and_inventory(self):
        r=self.units[0].record()
        self.assertEqual(r['maximum']['kind'],'empty')
        self.assertEqual(r['visited_hypotheses'],64)
        self.assertEqual(r['scored_cells'],320)
        self.assertEqual(r['input_vector_count'],32)
        self.assertEqual(r['eligible_cells'],0)

    def test_maximum_searches_all_templates_widths_and_activity_subsets(self):
        r=self.unit(edits={('on',0,1):(5,5,5),('on',1,129):(6,6,0)}).record()
        expected=float(np.float32(15)/np.float32(math.sqrt(3)))
        self.assertEqual(r['maximum']['value'],expected)
        self.assertEqual(r['eligible_cells'],5)

    def test_finite_statistic_below_operational_floor_is_not_empty(self):
        r=self.unit(edits={('on',1,129):(3,3,0)}).record()
        self.assertEqual(r['maximum']['kind'],'finite')
        self.assertLess(r['maximum']['value'],10)
        self.assertEqual(r['eligible_cells'],1)

    def test_isolated_epoch_remains_empty_with_explicit_mask_receipt(self):
        r=self.unit(edits={('on',0,1):(19,0,0)}).record()
        self.assertEqual(r['maximum']['kind'],'empty')
        self.assertGreater(sum(x['masked_cells'] for x in r['mask_receipts']),0)

    def test_missing_off_vector_is_error_not_empty(self):
        store=self.store();store.arrays.pop(('off',1,129))
        with self.assertRaisesRegex(ValueError,'Missing or extra'):self.reduce(store)

    def test_extra_hypothesis_vector_is_rejected(self):
        store=self.store();store.arrays['on',2,1]=store.arrays['on',0,1]
        with self.assertRaisesRegex(ValueError,'Missing or extra'):self.reduce(store)

    def test_nonfinite_off_payload_is_rejected_even_for_empty_on_family(self):
        with self.assertRaisesRegex(ValueError,'finite'):
            self.reduce(self.store(edits={('off',0,1):(0,float('nan'),0)}))

    def test_eligible_float32_overflow_is_error_not_empty(self):
        x=float(np.finfo(np.float32).max)
        with self.assertRaisesRegex(ValueError,'arithmetic became nonfinite'):
            self.reduce(self.store(edits={('on',0,1):(x,x,x)}))

    def test_case_and_context_mismatch_rejected(self):
        for key,value in [('case_identity','f'*64),('context_sha256','f'*64)]:
            store=self.store();store.provenance[key]=value
            with self.assertRaises(ValueError):self.reduce(store)

    def test_modified_score_identity_rejected(self):
        store=self.store();store.expected_ids['on',0,1]='f'*64
        with self.assertRaises(ValueError):self.reduce(store)

    def test_fixture_cannot_claim_native_scope(self):
        store=self.store();store.provenance['source_domain']='synthetic-native'
        with self.assertRaisesRegex(ValueError,'fixture'):self.reduce(store)
        with self.assertRaisesRegex(ValueError,'NativeRun'):
            reduce_native_run(object(),store,case_identity=case_id(0),noise_law_sha256=self.law)

    def test_all_127_empty_reference_units_remain_and_no_authority_is_issued(self):
        r=reference_bundle(self.units,**self.reference_args)
        self.assertEqual(r['reference_count'],127)
        self.assertEqual(r['empty_count'],127)
        self.assertEqual(len(r['ordered_maxima']),127)
        self.assertEqual(r['higher_quantile']['kind'],'empty')
        self.assertEqual(r['floor_or_maximum']['value'],10)
        for key in ('budget_charged','detector_certificate_issued','telescope_admission_authorized',
                    'joint_exchangeability_proved_by_receipts','operator_translation_proof_semantics_verified_here'):
            self.assertFalse(r[key])

    def test_finite_and_empty_units_are_both_retained_in_order(self):
        units=list(self.units);units[63]=self.unit(63,{('on',1,9):(8,8,8)})
        r=reference_bundle(units,**self.reference_args)
        self.assertEqual((r['empty_count'],r['finite_count']),(126,1))
        self.assertEqual(r['ordered_maxima'][63]['kind'],'finite')
        self.assertGreater(r['floor_or_maximum']['value'],10)

    def test_short_duplicate_or_reordered_reference_rejected(self):
        for units in (self.units[:-1], (self.units[0],)+self.units[:-1], tuple(reversed(self.units))):
            with self.assertRaises(ValueError):reference_bundle(units,**self.reference_args)

    def test_reference_family_or_noise_law_change_rejected(self):
        for key in ('expected_family_sha256','expected_noise_law_sha256'):
            args={**self.reference_args,key:'f'*64}
            with self.assertRaises(ValueError):reference_bundle(self.units,**args)

    def test_modified_serialized_unit_is_rejected(self):
        r=self.units[0].record();r['maximum']['kind']='finite';r['maximum']['value']=20.
        units=(CadenceMaximum(canonical(r)),)+self.units[1:]
        with self.assertRaisesRegex(ValueError,'receipt changed'):
            reference_bundle(units,**self.reference_args)

    def test_rehashed_incomplete_inventory_still_rejected(self):
        r=self.units[0].record();r.pop('receipt_sha256');r['visited_hypotheses']-=1
        r['receipt_sha256']=digest(r)
        with self.assertRaisesRegex(ValueError,'hypothesis count'):
            reference_bundle((CadenceMaximum(canonical(r)),)+self.units[1:],**self.reference_args)

    def test_missing_external_translation_pin_rejected(self):
        args={**self.reference_args,'operator_translation_proof_sha256':None}
        with self.assertRaises(ValueError):reference_bundle(self.units,**args)


if __name__=='__main__':unittest.main()
