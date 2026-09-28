"""Exact examples for a new statistic representation; no data/PRNG controls."""
from fractions import Fraction
import json
import unittest

from seti_repeater.empty_null_radio import (
    EMPTY, Maximum, ProposedReferenceDesign, arithmetic_screen,
    higher_quantile, inclusive_rank, maximum,
)


class EmptyMaximumTests(unittest.TestCase):
    def test_empty_is_distinct_from_every_finite_negative_score(self):
        negative=Maximum('finite',-1e300)
        self.assertLess(EMPTY.order_key,negative.order_key)
        self.assertNotEqual(EMPTY,negative)

    def test_maximum_of_no_eligible_values_is_explicit_empty(self):
        self.assertEqual(maximum([]),EMPTY)
        self.assertEqual(maximum([EMPTY,EMPTY]),EMPTY)

    def test_json_roundtrip_has_no_nonfinite_number(self):
        for item in (EMPTY,Maximum('finite',-2),Maximum('finite',12.5)):
            value=json.loads(json.dumps(item.record(),allow_nan=False))
            self.assertEqual(Maximum.from_record(value),item)

    def test_invalid_numeric_and_empty_payloads_rejected(self):
        for item in [('empty',0),('finite',None),('finite',True),('finite',float('nan')),
                     ('finite',float('inf')),('finite',-float('inf')),('unknown',None)]:
            with self.assertRaises(ValueError):Maximum(*item)

    def test_empty_observed_has_rank_one_even_with_finite_references(self):
        self.assertEqual(inclusive_rank(EMPTY,[EMPTY,Maximum('finite',-2)]),1)

    def test_finite_observed_keeps_all_empty_reference_units(self):
        self.assertEqual(inclusive_rank(Maximum('finite',12),[EMPTY]*127),Fraction(1,128))

    def test_ties_count_inclusive(self):
        self.assertEqual(inclusive_rank(Maximum('finite',3),
            [EMPTY,Maximum('finite',3),Maximum('finite',4)]),Fraction(3,4))

    def test_sample_size_three_cannot_reach_one_percent(self):
        result=arithmetic_screen(Maximum('finite',20),[EMPTY]*3)
        self.assertEqual(result['inclusive_rank_denominator'],4)
        self.assertFalse(result['passes_arithmetic_rule'])

    def test_empty_reference_is_not_authorized_by_numeric_rank(self):
        result=arithmetic_screen(Maximum('finite',20),[EMPTY]*127)
        self.assertTrue(result['passes_arithmetic_rule'])
        self.assertFalse(result['null_exchangeability_established'])
        self.assertFalse(result['detector_certificate_issued'])
        self.assertFalse(result['telescope_admission_authorized'])

    def test_empty_observed_never_selected(self):
        self.assertFalse(arithmetic_screen(EMPTY,[EMPTY]*127)['passes_arithmetic_rule'])

    def test_higher_quantile_preserves_empty_atom(self):
        x=[EMPTY,EMPTY,Maximum('finite',2),Maximum('finite',7)]
        self.assertEqual(higher_quantile(x,Fraction(1,3)),EMPTY)
        self.assertEqual(higher_quantile(x,Fraction(1,2)),Maximum('finite',2))
        self.assertEqual(higher_quantile(x),Maximum('finite',7))

    def test_floor_is_unchanged_with_empty_reference_maximum(self):
        r=arithmetic_screen(Maximum('finite',9),[EMPTY]*127)
        self.assertEqual(r['operational_floor_or_maximum']['value'],10.)
        self.assertFalse(r['passes_arithmetic_rule'])

    def test_reference_tie_at_operational_maximum_fails_rank_cut(self):
        r=arithmetic_screen(Maximum('finite',20),[Maximum('finite',20)]+[EMPTY]*126)
        self.assertEqual(Fraction(r['inclusive_rank_numerator'],r['inclusive_rank_denominator']),Fraction(2,128))
        self.assertFalse(r['passes_arithmetic_rule'])

    def test_rank_requires_complete_typed_reference(self):
        for ref in ([],[None],[float('-inf')]):
            with self.assertRaises(ValueError):inclusive_rank(EMPTY,ref)


class ProposalBoundaryTests(unittest.TestCase):
    def valid(self):
        prefix='method-unit-example'
        return ProposedReferenceDesign(prefix,tuple(f'{prefix}/null/{i}' for i in range(127)),
            tuple(f'{prefix}/evaluation/{i}' for i in range(24)),tuple(range(151)),
            'a'*64,'b'*64,'c'*64)

    def test_identity_proposal_never_charges_or_activates(self):
        record=self.valid().record()
        self.assertEqual(record['status'],'PROPOSED_NOT_ACTIVATED')
        self.assertFalse(record['budget_charged']);self.assertFalse(record['new_values_generated'])

    def test_duplicate_identity_or_seed_is_rejected(self):
        from dataclasses import replace
        p=self.valid()
        for bad in (replace(p,control_seeds=(0,)*151),
                    replace(p,evaluation_namespaces=p.null_namespaces[:24])):
            with self.assertRaises(ValueError):bad.validate()

    def test_context_shortcut_and_missing_external_pin_rejected(self):
        from dataclasses import replace
        p=self.valid()
        for bad in (replace(p,destination_context_sha256=p.source_context_sha256),
                    replace(p,noise_law_sha256='bad')):
            with self.assertRaises(ValueError):bad.validate()


if __name__=='__main__':unittest.main()
