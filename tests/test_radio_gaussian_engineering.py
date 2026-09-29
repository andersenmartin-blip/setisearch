"""New engineering RNG admission risks, with constructors blocked in guard tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from radio_receiver_adapter_common import ROOT, context
from seti_repeater import gaussian_engineering_radio as e
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_render_radio import render_gaussian


class EngineeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contexts = [context('calibration'), context('validation')]
        cls.plans = [e.make_plan(c, i) for i, c in enumerate(cls.contexts)]
        cls.forbidden = json.loads((ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes())['cases']

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.m = {'schema': j.SCHEMA, 'mode': 'engineering', 'namespace': e.NAMESPACE,
                  'execution_binding_sha256': digest('guard-test-freeze'),
                  'allocation_sha256': digest('guard-test-allocation'),
                  'cases': [e.binding(p) for p in self.plans],
                  'caps': {**j.CAPS, 'active_milliseconds': 60000,
                           'evidence_bytes': 1048576, 'ledger_reserve_bytes': 65536},
                  'required_artifacts': e.ARTIFACTS}
        self.store = j.DirectoryStore.create(self.root/'store', self.m)
        cp = self.store.read()
        self.lease = j.consume(self.store, expected_revision=cp.revision,
                               expected_manifest_sha256=digest(self.m), binding=self.m['cases'][0],
                               milliseconds=30000, artifact_bytes=10000, directory=self.root/'case')
    def tearDown(self): self.tmp.cleanup()
    def run_render(self, plan=None, forbidden=None, verifier=lambda m: None):
        return e.render(self.contexts[0], plan or self.plans[0], lease=self.lease,
                        forbidden_cases=self.forbidden if forbidden is None else forbidden,
                        verify_freeze=verifier)

    def test_two_seed_and_identity_domains_are_disjoint_from_all_151_reserved(self):
        self.assertEqual(len({p['case']['seed'] for p in self.plans}), 2)
        for c,p in zip(self.contexts, self.plans): e.validate_plan(c,p,self.forbidden)

    def test_publication_marker_precedes_prng_constructor(self):
        def stop(entropy):
            cp=self.store.read(); case=j.replay(cp.document)['cases'][0]
            self.assertIn('rng_start.json', case['artifacts'])
            self.assertEqual(entropy, [self.plans[0]['case']['seed'],0])
            self.assertEqual(cp.document['manifest']['mode'], 'engineering')
            raise RuntimeError('BEFORE_FIRST_VALUE')
        with patch('numpy.random.SeedSequence', side_effect=stop) as p:
            with self.assertRaisesRegex(RuntimeError,'BEFORE_FIRST_VALUE'): self.run_render()
        self.assertEqual(p.call_count,1)

    def test_second_entry_cannot_construct_prng(self):
        e.begin(self.contexts[0],self.plans[0],self.lease,self.forbidden,lambda m:None)
        with patch('numpy.random.SeedSequence', side_effect=AssertionError('constructor reached')) as p:
            with self.assertRaisesRegex(ValueError,'already exists'): self.run_render()
        self.assertEqual(p.call_count,0)

    def test_runtime_failure_precedes_marker_and_constructor(self):
        def fail(m): raise ValueError('runtime changed')
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')):
            with self.assertRaisesRegex(ValueError,'runtime changed'): self.run_render(verifier=fail)
        self.assertEqual(j.replay(self.store.read().document)['cases'][0]['artifacts'], {})

    def test_rehashed_final_scan_schedule_fails_before_constructor(self):
        p=copy.deepcopy(self.plans[0]); p['streams'][-1]['normal_calls']=15
        p['plan_sha256']=digest({k:v for k,v in p.items() if k!='plan_sha256'})
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')):
            with self.assertRaisesRegex(ValueError,'schedule'): self.run_render(plan=p)

    def test_reserved_seed_collision_fails_before_constructor(self):
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')):
            with self.assertRaisesRegex(ValueError,'collision'):
                self.run_render(forbidden=[{'identity':'0'*64,'seed':self.plans[0]['case']['seed']}])

    def test_reserved_identity_collision_fails_before_constructor(self):
        with self.assertRaisesRegex(ValueError,'collision'):
            self.run_render(forbidden=[{'identity':self.plans[0]['case']['identity'],'seed':0}])

    def test_engineering_lease_cannot_enter_original_scientific_renderer(self):
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')):
            with self.assertRaises((ValueError,AttributeError)):
                render_gaussian(self.contexts[0], self.plans[0], lease=self.lease)

    def test_ambiguous_start_artifact_blocks_all_further_entry(self):
        original=self.store.publish
        def fail(revision, doc):
            original(revision,doc)
            raise OSError('receipt lost after durable write')
        with patch.object(self.store,'publish',side_effect=fail):
            with self.assertRaises(OSError): self.run_render()
        with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')):
            with self.assertRaisesRegex(ValueError,'uncertain'): self.run_render()
        self.assertTrue((self.root/'case/rng_start.json').exists())

    def test_consumed_case_cannot_be_recreated_after_process_loss(self):
        cp=self.store.read()
        with self.assertRaisesRegex(ValueError,'Prior case incomplete'):
            j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(self.m),
                      binding=self.m['cases'][0],milliseconds=30000,artifact_bytes=10000,directory=self.root/'again')

    def test_fake_or_scientific_namespace_lease_refused(self):
        with self.assertRaisesRegex(ValueError,'journal lease'):
            e.begin(self.contexts[0],self.plans[0],object(),self.forbidden,lambda m:None)
        self.lease.manifest['namespace']='scientific-copy'
        with self.assertRaisesRegex(ValueError,'domain'):
            e.begin(self.contexts[0],self.plans[0],self.lease,self.forbidden,lambda m:None)

    def test_nonfinite_row_refused_without_source_success(self):
        class Bad:
            def normal(self,*args): return np.full(65536,np.nan,dtype='<f8')
        with self.assertRaisesRegex(ValueError,'finite'):
            e._rows(self.contexts[0],self.plans[0],lambda entropy:Bad(),lambda *args:None,{})

    def test_deterministic_row_oracle_and_injection_mass(self):
        class Pattern:
            def normal(self,*args): return 100.+np.arange(65536,dtype='<f8')%257/512.
        calls=[]
        def factory(entropy): calls.append(entropy); return Pattern()
        run,receipt=e._rows(self.contexts[1],self.plans[1],factory,lambda *args:None,{'fixture':True})
        self.assertEqual(calls,[s['entropy'] for s in self.plans[1]['streams']])
        self.assertEqual(len(receipt['row_receipts']),6)
        active=[r for s in receipt['row_receipts'] for r in s['rows'] if r['injected']]
        self.assertEqual(len(active),48)
        self.assertLessEqual(max(abs(r['added_total_power_before_float32']-500) for r in active),1e-9)
        self.assertEqual(sum(s.values.size for s in run.sources.values()),6291456)
        # OFF raw rows must exactly equal the pre-cast background oracle.
        expected=e.native.array_hash((100.+np.arange(65536,dtype='<f8')%257/512.).astype('<f4'))
        for s in receipt['row_receipts']:
            for r in s['rows']:
                self.assertEqual(r['background_sha256'],expected)
                if not r['injected']: self.assertEqual(r['raw_sha256'],expected)

if __name__=='__main__': unittest.main()
