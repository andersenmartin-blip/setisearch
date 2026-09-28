"""Metadata preflight only; no reserved Gaussian value is generated."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from radio_receiver_adapter_common import context
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_render_radio import prepare, DrawPlan, render_mock, render_gaussian, NOISE_LAW_SHA256, MOCK_LAW

ROOT=Path(__file__).resolve().parents[1]


class RenderBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes()
        cls.proposal=json.loads(cls.raw);cls.contexts={r:context('calibration' if r=='calibration' else 'validation') for r in ('calibration','evaluation')}
        cls.case=cls.proposal['cases'][0];cls.c=cls.contexts['calibration'];cls.plan=prepare(cls.c,cls.case,cls.raw)

    def test_all_151_metadata_cases_bind_without_rng(self):
        with patch('numpy.random.Generator',side_effect=AssertionError('RNG must not be called')):
            plans=[prepare(self.contexts[c['role']],c,self.raw).record() for c in self.proposal['cases']]
        self.assertEqual(len(plans),151);self.assertEqual(len({p['plan_sha256'] for p in plans}),151)
        self.assertTrue(all(not p['scientific_execution_authorized'] and not p['random_values_generated'] for p in plans))

    def test_exact_six_stream_96_call_schedule(self):
        r=self.plan.record();self.assertEqual(len(r['streams']),6)
        self.assertEqual(sum(x['normal_calls'] for x in r['streams']),96)
        for i,x in enumerate(r['streams']):self.assertEqual(x['seed_sequence_entropy'],[self.case['seed'],i])

    def test_changed_proposal_bytes_rejected(self):
        with self.assertRaisesRegex(ValueError,'Exact immutable'):prepare(self.c,self.case,self.raw+b' ')

    def test_changed_seed_rejected_before_any_rng(self):
        c={**self.case,'seed':self.case['seed']+1}
        with self.assertRaisesRegex(ValueError,'unchanged'):prepare(self.c,c,self.raw)

    def test_changed_recipe_rejected(self):
        c=copy.deepcopy(self.case);c['recipe']={'kind':'on_signal'}
        with self.assertRaises(ValueError):prepare(self.c,c,self.raw)

    def test_wrong_context_rejected(self):
        with self.assertRaisesRegex(ValueError,'Case/context'):prepare(self.contexts['evaluation'],self.case,self.raw)

    def test_relabelled_case_role_rejected(self):
        with self.assertRaises(ValueError):prepare(self.c,{**self.case,'role':'evaluation'},self.raw)

    def test_old_or_unregistered_case_rejected(self):
        with self.assertRaises(ValueError):prepare(self.c,{'identity':'a'*64},self.raw)

    def test_case_cannot_self_activate(self):
        with self.assertRaises(ValueError):prepare(self.c,{**self.case,'budget_charged':True},self.raw)

    def test_corrupt_draw_plan_rejected(self):
        r=self.plan.record();r['context_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'changed'):DrawPlan(canonical(r)).record()

    def test_rehashed_plan_cannot_claim_execution_authority(self):
        r=self.plan.record();r.pop('plan_sha256');r['scientific_execution_authorized']=True;r['plan_sha256']=digest(r)
        with self.assertRaisesRegex(ValueError,'activation'):DrawPlan(canonical(r)).record()

    def test_mock_law_is_distinct_from_gaussian(self):
        self.assertNotEqual(digest(MOCK_LAW),NOISE_LAW_SHA256)
        self.assertFalse(MOCK_LAW['gaussian_draws']);self.assertFalse(MOCK_LAW['scientific_calibration_reference'])

    def test_unlabelled_stream_rejected_before_read(self):
        def factory(*args):raise AssertionError('Must not read')
        with self.assertRaisesRegex(ValueError,'deterministic provider'):render_mock(self.c,self.plan,factory)

    def test_real_gaussian_entry_stops_before_rng(self):
        with patch('numpy.random.Generator',side_effect=AssertionError('No RNG')):
            with self.assertRaisesRegex(ValueError,'PROPOSED_NOT_ACTIVATED'):render_gaussian(self.c,self.plan)


if __name__=='__main__':unittest.main()
