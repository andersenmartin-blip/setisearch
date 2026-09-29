"""Guard/seam tests use hand-built receipts or deterministic arrays, never RNG."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from radio_receiver_adapter_common import context, ROOT
from seti_repeater import native_chain_engineering_radio as e
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater import search_v0p6 as core
from seti_repeater.empty_null_radio import canonical, EMPTY, Maximum
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import CadenceMaximum, digest, _reduce
from seti_repeater.whole_cadence_downstream_radio import _execute, _execute_core, WholeCadenceThreshold


class NativeChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=context('validation'); cls.plans=[e.make_plan(cls.c,i) for i in range(8)]
        cls.f=e.family(cls.c)
        cls.forbidden=json.loads((ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes())['cases']
        # Deliberately hand-built UNIT TEST receipts. Never saved as runtime references.
        cls.records=[]
        for p in cls.plans[:4]:
            r={'schema':'radio-whole-cadence-maximum-v1','case_identity':p['case']['identity'],
               'family':cls.f.record(),'family_sha256':digest(cls.f.record()),'noise_law_sha256':e.LAW_SHA,
               'domain':'synthetic-native','all_hypotheses_evaluated':True,'score_shift_resampling':False,
               'visited_hypotheses':2592,'scored_cells':209952,'eligible_cells':0,'maximum':EMPTY.record(),
               'unit_test_fixture_not_observed_reference':True}
            r['receipt_sha256']=digest(r);cls.records.append(r)

    def units(self, records=None): return [CadenceMaximum(canonical(r)) for r in (self.records if records is None else records)]
    def threshold(self): return e.bind_threshold(self.c,self.units())
    def reseal(self,r): r['receipt_sha256']=digest({k:v for k,v in r.items() if k!='receipt_sha256'});return r

    def test_eight_unique_plans_disjoint_from_all_reserved_cases(self):
        self.assertEqual(len({p['case']['identity'] for p in self.plans}),8)
        self.assertEqual(len({p['case']['seed'] for p in self.plans}),8)
        for p in self.plans:e.validate_plan(self.c,p,self.forbidden)

    def test_calibration_window_cannot_enter_same_window_suite(self):
        with self.assertRaisesRegex(ValueError,'Same validation'):e.make_plan(context('calibration'),0)

    def test_rehashed_injection_or_stream_schedule_rejected(self):
        for key in ('spec','streams'):
            p=copy.deepcopy(self.plans[4])
            if key=='spec':p['case']['spec']['total_digital_power']=501
            else:p['streams'][-1]['normal_calls']=15
            p['plan_sha256']=digest({k:v for k,v in p.items() if k!='plan_sha256'})
            with self.assertRaises(ValueError):e.validate_plan(self.c,p,[])

    def test_four_empty_references_keep_empty_and_floor_without_calibration_claim(self):
        t=self.threshold().record();self.assertEqual(t['operational_threshold'],10.)
        self.assertEqual(t['reference_bundle']['ordered_maxima'],[EMPTY.record()]*4)
        self.assertEqual(t['reference_denominator'],5);self.assertEqual(t['minimum_possible_rank_p'],.2)
        self.assertFalse(t['calibrated_1_percent_test']);self.assertFalse(t['production_threshold'])

    def test_wrong_count_or_order_rejected(self):
        for rr in (self.records[:3],self.records+[self.records[0]],self.records[::-1]):
            with self.assertRaises(ValueError):e.bind_threshold(self.c,self.units(rr))

    def test_finite_maximum_above_floor_is_used_without_dropping_empty(self):
        rr=copy.deepcopy(self.records);rr[2].update(maximum=Maximum('finite',12.).record(),eligible_cells=1);self.reseal(rr[2])
        self.assertEqual(e.bind_threshold(self.c,self.units(rr)).record()['operational_threshold'],12.)

    def test_wrong_law_domain_family_or_incomplete_receipt_rejected_even_rehashed(self):
        for k,v in [('noise_law_sha256','f'*64),('domain','deterministic-score-fixture'),
                    ('family_sha256','e'*64),('visited_hypotheses',2591),('eligible_cells',1)]:
            rr=copy.deepcopy(self.records);rr[0][k]=v;self.reseal(rr[0])
            with self.assertRaises(ValueError):e.bind_threshold(self.c,self.units(rr))

    def test_rehashed_threshold_rank_or_floor_change_rejected(self):
        for k,v in [('operational_threshold',9.),('reference_denominator',128),('rank_ceiling',[1,5])]:
            r=self.threshold().record();r[k]=v;r['threshold_receipt_sha256']=digest({a:b for a,b in r.items() if a!='threshold_receipt_sha256'})
            with self.assertRaises(ValueError):e.EngineeringThreshold(canonical(r),self.c).record()

    def test_reference_reuse_unknown_case_and_other_law_or_domain_rejected(self):
        t=self.threshold()
        for case,law,domain in [(self.plans[0]['case']['identity'],e.LAW_SHA,'synthetic-native'),
                                 ('f'*64,e.LAW_SHA,'synthetic-native'),
                                 (self.plans[4]['case']['identity'],'f'*64,'synthetic-native'),
                                 (self.plans[4]['case']['identity'],e.LAW_SHA,'deterministic-score-fixture')]:
            with self.assertRaises(ValueError):t.validate(self.f,case_identity=case,noise_law_sha256=law,domain=domain)

    def test_public_127_entrypoint_and_receipt_reject_engineering_threshold(self):
        with self.assertRaisesRegex(ValueError,'Distinct whole-cadence'):_execute(None,None,self.threshold(),None)
        with self.assertRaises(ValueError):WholeCadenceThreshold(self.threshold().payload).record()

    def test_shared_retention_reports_actual_denominator_and_cannot_pass_one_percent(self):
        arrays={(k,t,w):np.zeros((3,self.c.grid.support_bin_count),dtype='<f4')
                for k in ('on','off') for t in range(81) for w in core.M37_SPECTRAL_WIDTHS}
        arrays['on',0,129][:,49]=20.
        identity=self.plans[4]['case']['identity']
        store=ScoreStore(arrays,{'context_sha256':self.c.identity,'case_identity':identity,
                               'unit_test_fixture_not_native_execution':True})
        unit=_reduce(self.f,store,identity,e.LAW_SHA,'synthetic-native',{'unit_test_fixture':True})
        result=_execute_core(self.f,store,self.threshold(),unit)
        self.assertTrue(result['retained']['on'])
        for row in result['retained']['on']:
            self.assertEqual(row['rank']['reference_denominator'],5)
            self.assertEqual(row['rank']['exact_fraction'],[1,5]);self.assertFalse(row['rank']['meets_rank_cut'])

    def guarded_lease(self,tmp,ordinal=0):
        m={'schema':j.SCHEMA,'mode':'engineering','namespace':e.NAMESPACE,
           'execution_binding_sha256':digest('test-freeze'),'allocation_sha256':digest('test-allocation'),
           'cases':[e.binding(self.plans[ordinal])],'caps':{**j.CAPS,'active_milliseconds':60000,
           'evidence_bytes':1048576,'ledger_reserve_bytes':65536},'required_artifacts':e.ARTIFACTS}
        store=j.DirectoryStore.create(tmp/'journal',m);cp=store.read()
        lease=j.consume(store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
                        binding=m['cases'][0],milliseconds=30000,artifact_bytes=10000,directory=tmp/'case')
        return store,lease

    def test_durable_start_precedes_first_constructor_and_second_entry_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            store,lease=self.guarded_lease(Path(tmp))
            def stop(entropy):
                self.assertIn('rng_start.json',j.replay(store.read().document)['cases'][0]['artifacts'])
                raise RuntimeError('STOP_BEFORE_DRAW')
            with patch('numpy.random.SeedSequence',side_effect=stop) as p:
                with self.assertRaisesRegex(RuntimeError,'STOP_BEFORE_DRAW'):
                    e.render(self.c,self.plans[0],lease=lease,forbidden_cases=self.forbidden,verify_freeze=lambda m:None)
                with self.assertRaisesRegex(ValueError,'already exists'):
                    e.render(self.c,self.plans[0],lease=lease,forbidden_cases=self.forbidden,verify_freeze=lambda m:None)
                self.assertEqual(p.call_count,1)

    def test_freeze_failure_or_collision_blocks_constructor(self):
        for failure in ('freeze','collision'):
            with tempfile.TemporaryDirectory() as tmp:
                store,lease=self.guarded_lease(Path(tmp))
                def verify(m):
                    if failure=='freeze':raise ValueError('freeze differs')
                forbidden=[{'identity':'f'*64,'seed':self.plans[0]['case']['seed']}] if failure=='collision' else self.forbidden
                with patch('numpy.random.SeedSequence',side_effect=AssertionError('constructor reached')) as p:
                    with self.assertRaises(ValueError):e.render(self.c,self.plans[0],lease=lease,forbidden_cases=forbidden,verify_freeze=verify)
                    self.assertEqual(p.call_count,0)
                self.assertEqual(j.replay(store.read().document)['cases'][0]['artifacts'],{})

    def test_deterministic_kernel_preserves_new_law_and_both_on_off_injection(self):
        class Pattern:
            def normal(self,*args):return 100.+np.arange(65536,dtype='<f8')%257/512.
        plan=self.plans[6]
        run,r=e.gaussian._rows(self.c,plan,lambda entropy:Pattern(),lambda *args:None,{'unit_test_fixture':True},
                              receipt_schema='radio-native-chain-gaussian-receipt-v1')
        self.assertEqual(r['noise_law_sha256'],e.LAW_SHA)
        self.assertEqual(sum(x['injected'] for s in r['row_receipts'] for x in s['rows']),96)
        for s in run.sources.values():self.assertEqual(json.loads(s.scope_json)['noise_law_sha256'],e.LAW_SHA)
        # End-to-end new receipt/compact seam on deterministic rows, not Gaussian draws.
        scores=run.build_store(); parts=e.gaussian.compact_parts(run,scores,plan,r)
        from seti_repeater.whole_cadence_compact_radio import audit
        import hashlib
        pins={k:hashlib.sha256(v).hexdigest() for k,v in parts.items()}
        result=audit(self.c,{k:v for k,v in e.binding(plan).items() if k!='role'},parts,
                     expected_sha256s=pins,byte_cap=18*1024**2)
        self.assertEqual(result['score_vectors'],1296)
        self.assertEqual(result['score_values'],384912)

    def test_empty_engineering_gate_passes_null_and_fails_on_recovery(self):
        for index,expected in ((4,False),(7,True)):
            p=self.plans[index]
            report={'complete':True,'family_sha256':digest(self.f.record()),
                    'retention':{'case_identity':p['case']['identity'],'retained':{'on':[]}},
                    'decisions':[],'clusters':[],
                    'factor_provider_receipt':{'domain':'uncalibrated-four-reference-native-engineering'}}
            report['result_sha256']=digest(report)
            result=e.evaluate(report,self.c,p)
            self.assertEqual(result['engineering_gate_pass'],expected)
            self.assertFalse(result['calibrated_rank_gate_pass'])
            self.assertFalse(result['production_recovery_rfi_null_qualification'])


if __name__=='__main__':unittest.main()
