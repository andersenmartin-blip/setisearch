"""Exact inactive phase and protected overhead metadata checks; no RNG."""
import copy
import json
from pathlib import Path
import unittest
from seti_repeater import whole_cadence_phase_radio as p
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest

class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.raw=Path('config/radio_whole_cadence_null_proposal_20260928.json').read_bytes();self.b=p.phase_budget(self.raw)
        cases=json.loads(self.raw)['cases']
        self.m={'schema':j.SCHEMA,'mode':'scientific','namespace':'metadata-only-phase-unit',
            'execution_binding_sha256':'a'*64,'allocation_sha256':'b'*64,'caps':copy.deepcopy(j.CAPS),
            'cases':[{'case_identity':c['identity'],'plan_sha256':digest({'metadata-only-plan':i}),
                **{k:c[k] for k in ('role','context_sha256','source_contract_sha256','noise_law_sha256')}} for i,c in enumerate(cases)],
            'required_artifacts':['metadata-only.json']}
        self.doc=j.genesis(self.m)
        self.event={'kind':'consume','binding':self.m['cases'][0],'milliseconds':40000,'artifact_bytes':4*1024**2,'nonce':'00000000-0000-4000-8000-000000000001'}
        self.o=p.overhead_genesis(self.raw,self.b)
        self.e={'ordinal':0,'identity':'c'*64,'kind':'failure','milliseconds':200000,'bytes':76*1024**2,'artifact_sha256':'d'*64}

    def test_exact_phase_has_no_execution_authority(self):
        out=p.validate_cases(j.append(self.doc,self.event),self.raw,self.b)
        self.assertFalse(out['scientific_execution_authorized']);self.assertEqual(out['case_milliseconds'],40000)

    def test_case_cannot_spend_overhead_time(self):
        self.event['milliseconds']+=1
        with self.assertRaisesRegex(ValueError,'Exact per-case'):p.validate_cases(j.append(self.doc,self.event),self.raw,self.b)

    def test_case_cannot_spend_overhead_bytes(self):
        self.event['artifact_bytes']+=1
        with self.assertRaisesRegex(ValueError,'Exact per-case'):p.validate_cases(j.append(self.doc,self.event),self.raw,self.b)

    def test_context_substitution_rejected(self):
        self.m['cases'][0]['context_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'binding'):p.validate_cases(j.genesis(self.m),self.raw,self.b)

    def append(self,event=None):return p.append_overhead(self.o,event or self.e,expected_sha256=digest(self.o),proposal_bytes=self.raw,budget=self.b)

    def test_exact_overhead_ceiling_is_nonrefundable(self):
        out=p.validate_overhead(self.append(),self.raw,self.b)
        self.assertEqual(out['remaining_milliseconds'],0);self.assertEqual(out['remaining_failure_summary_bytes'],0)
        self.assertTrue(out['full_reservation_stays_charged'])

    def test_overhead_time_overflow_rejected(self):
        self.e['milliseconds']+=1
        with self.assertRaisesRegex(ValueError,'capacity'):self.append()

    def test_overhead_bytes_overflow_rejected(self):
        self.e['bytes']+=1
        with self.assertRaisesRegex(ValueError,'capacity'):self.append()

    def test_failure_cannot_become_empty_or_refund(self):
        for kind in ('EMPTY','refund','completed'):
            with self.subTest(kind=kind):
                self.e['kind']=kind
                with self.assertRaisesRegex(ValueError,'kind'):self.append()

    def test_stale_overhead_checkpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'checkpoint'):p.append_overhead(self.o,self.e,expected_sha256='f'*64,proposal_bytes=self.raw,budget=self.b)

    def test_duplicate_failure_identity_rejected(self):
        self.e['milliseconds']=1;self.e['bytes']=1;self.o=self.append();self.e['ordinal']=1
        with self.assertRaisesRegex(ValueError,'identity'):self.append()

if __name__=='__main__':unittest.main()
