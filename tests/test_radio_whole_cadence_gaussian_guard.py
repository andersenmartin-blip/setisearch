"""Publication adapter mocks stop BEFORE any proposed PRNG constructor/value.

The in-memory Store mimics the external adapter API for ordering/rejection
checks only. These tests do not qualify GitHub publication or activate cases.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from radio_receiver_adapter_common import context
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_render_radio import prepare,render_gaussian,DrawPlan
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical


class FixtureStore:
    def __init__(self,m):
        self.document=j.genesis(m);self.validations=0;self.runtime_changed=False
        self.artifacts={};self.bad_readback=False
    def read(self):return j.Checkpoint(j.clone(self.document),digest(self.document),{'kind':'github-published-scientific','test_double':True})
    def publish(self,revision,document):
        if digest(self.document)!=revision:raise ValueError('CAS')
        j.replay(document);self.document=j.clone(document)
    def publish_artifact(self,checkpoint,name,payload):
        self.artifacts[name]=payload
        import hashlib
        return {'location':name,'revision':'fixture-only','sha256':hashlib.sha256(payload).hexdigest()}
    def read_artifact(self,publication):
        return b'wrong' if self.bad_readback else self.artifacts[publication['location']]
    def verify_completed_evidence(self,checkpoint):
        for case in j.replay(checkpoint.document)['cases']:
            if case['status']=='completed':
                for meta in case['artifacts'].values():
                    import hashlib
                    if hashlib.sha256(self.read_artifact(meta['publication'])).hexdigest()!=meta['sha256']:
                        raise ValueError('Prior published evidence missing/changed')
    def verify_execution(self,m):
        self.validations+=1
        if self.runtime_changed:raise ValueError('Fixture runtime binding changed')
        if m!=self.document['manifest']:raise ValueError('Fixture freeze changed')


class GaussianGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=(Path(__file__).resolve().parents[1]/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes()
        cls.c=context('calibration');cls.plan=prepare(cls.c,json.loads(raw)['cases'][0],raw)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();r=self.plan.record();c=r['case']
        first={**{k:c[k] for k in ('context_sha256','source_contract_sha256','noise_law_sha256','role')},
               'case_identity':c['identity'],'plan_sha256':r['plan_sha256']}
        cases=[first]+[{**first,'case_identity':digest({'test-double-unused-case':i}),
                'role':'calibration' if i<127 else 'evaluation'} for i in range(1,151)]
        m={'schema':j.SCHEMA,'mode':'scientific','namespace':'PUBLICATION-ADAPTER-TEST-DOUBLE-NOT-ACTIVATION',
            'execution_binding_sha256':digest({'fixture':1}),'allocation_sha256':digest({'fixture':2}),
            'cases':cases,'caps':j.CAPS,'required_artifacts':['unused']}
        self.store=FixtureStore(m);cp=self.store.read()
        self.lease=j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
            binding=first,milliseconds=10000,artifact_bytes=1000,directory=Path(self.temp.name)/'case')

    def tearDown(self):self.temp.cleanup()

    def test_charge_and_start_are_published_before_first_prng_constructor(self):
        def prohibited(entropy):
            case=j.replay(self.store.read().document)['cases'][0]
            self.assertTrue(case['rng_started']);self.assertEqual(case['status'],'started')
            self.assertEqual(entropy,[self.plan.record()['case']['seed'],0])
            self.assertEqual(self.store.validations,2)
            raise RuntimeError('STOP_BEFORE_PRNG_CONSTRUCTION_NO_VALUES')
        with patch('numpy.random.SeedSequence',side_effect=prohibited) as constructor:
            with self.assertRaisesRegex(RuntimeError,'STOP_BEFORE'):render_gaussian(self.c,self.plan,lease=self.lease)
        self.assertEqual(constructor.call_count,1)
        self.assertEqual(j.replay(self.store.read().document)['archived_artifact_bytes'],0)

    def test_repeated_generator_entry_is_rejected_without_constructor(self):
        self.lease.begin_gaussian(self.plan)
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('No second constructor')):
            with self.assertRaisesRegex(ValueError,'already started'):render_gaussian(self.c,self.plan,lease=self.lease)

    def test_runtime_changes_after_consumption_fail_before_rng_start(self):
        self.store.runtime_changed=True
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('No constructor')):
            with self.assertRaisesRegex(ValueError,'runtime binding'):render_gaussian(self.c,self.plan,lease=self.lease)
        self.assertFalse(j.replay(self.store.read().document)['cases'][0]['rng_started'])

    def test_bad_final_scan_schedule_fails_before_rng_start(self):
        r=self.plan.record();r.pop('plan_sha256');r['streams'][-1]['normal_calls']=15;r['plan_sha256']=digest(r)
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('No constructor')):
            with self.assertRaisesRegex(ValueError,'schedule'):render_gaussian(self.c,DrawPlan(canonical(r)),lease=self.lease)
        self.assertFalse(j.replay(self.store.read().document)['cases'][0]['rng_started'])

    def test_rehashed_changed_plan_not_accepted_by_consumption(self):
        r=self.plan.record();r.pop('plan_sha256');r['new_field']='unauthorized';r['plan_sha256']=digest(r)
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('No constructor')):
            with self.assertRaisesRegex(ValueError,'binding'):render_gaussian(self.c,DrawPlan(canonical(r)),lease=self.lease)

    def test_scientific_artifact_requires_external_byte_readback(self):
        self.lease.begin_gaussian(self.plan);self.store.bad_readback=True
        with self.assertRaisesRegex(ValueError,'External artifact bytes'):self.lease.write_artifact('unused',b'fixture')
        state=j.replay(self.store.read().document)
        self.assertEqual(state['cases'][0]['artifacts'],{})
        self.assertNotEqual(state['cases'][0]['status'],'completed')

    def test_external_disappearance_blocks_completion(self):
        self.lease.begin_gaussian(self.plan);self.lease.write_artifact('unused',b'fixture')
        self.store.bad_readback=True
        with self.assertRaisesRegex(ValueError,'missing/changed'):self.lease.finish()
        self.assertNotEqual(j.replay(self.store.read().document)['cases'][0]['status'],'completed')

    def test_lost_prior_external_evidence_blocks_next_consumption(self):
        self.lease.begin_gaussian(self.plan);self.lease.write_artifact('unused',b'fixture');self.lease.finish()
        self.store.bad_readback=True;cp=self.store.read();m=cp.document['manifest']
        with self.assertRaisesRegex(ValueError,'Prior published evidence'):
            j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
                binding=m['cases'][1],milliseconds=10000,artifact_bytes=1000,directory=Path(self.temp.name)/'next')
        self.assertEqual(len(j.replay(self.store.read().document)['cases']),1)


if __name__=='__main__':unittest.main()
