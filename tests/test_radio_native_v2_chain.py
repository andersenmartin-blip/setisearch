"""No-RNG qualification of the fresh native-v2 stage bindings."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from radio_receiver_adapter_common import ROOT,context
from seti_repeater import native_v2_chain_radio as chain
from seti_repeater import native_v2_parent_radio as parent
from seti_repeater import whole_cadence_event_store_radio as events
from seti_repeater import whole_cadence_journal_radio as journal
from seti_repeater.empty_null_radio import canonical,EMPTY
from seti_repeater.whole_cadence_reference_radio import CadenceMaximum,digest


class NativeV2ChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=context('validation')
        cls.plans=[parent.make_plan(cls.context,i) for i in range(8)]
        cls.forbidden=json.loads((ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes())['cases']
        cls.family=chain.family(cls.context)
        cls.records=[]
        for plan in cls.plans[:4]:
            record={'schema':'radio-whole-cadence-maximum-v1',
                'case_identity':plan['case']['identity'],'family':cls.family.record(),
                'family_sha256':digest(cls.family.record()),
                'noise_law_sha256':parent.LAW_SHA,'domain':'synthetic-native',
                'all_hypotheses_evaluated':True,'score_shift_resampling':False,
                'visited_hypotheses':2592,'scored_cells':209952,
                'eligible_cells':0,'maximum':EMPTY.record(),
                'unit_test_fixture_not_observed_reference':True}
            record['receipt_sha256']=digest(record);cls.records.append(record)

    def units(self):
        return [CadenceMaximum(canonical(record)) for record in self.records]

    def threshold(self):
        return chain.bind_threshold(self.context,self.units())

    def lease(self,root,ordinal=0):
        cases=[parent.case_binding(plan) for plan in self.plans]
        manifest,_=parent.manifest(digest('runner-freeze'),digest('allocation'),cases)
        store=events.EventDirectoryStore.create(root/'journal',manifest)
        before=store.read()
        lease=journal.consume(store,expected_revision=before.revision,
            expected_manifest_sha256=digest(manifest),binding=cases[ordinal],
            milliseconds=parent.CASE_MILLISECONDS,artifact_bytes=parent.CASE_BYTES,
            directory=root/f'case{ordinal}')
        return store,lease

    def test_fresh_threshold_uses_only_fresh_ordered_references(self):
        value=self.threshold().record()
        self.assertEqual(value['schema'],chain.THRESHOLD_SCHEMA)
        self.assertEqual(value['operational_threshold'],10.)
        self.assertEqual(value['reference_bundle']['ordered_case_identities'],
            [plan['case']['identity'] for plan in self.plans[:4]])
        self.assertFalse(value['calibrated_1_percent_test'])
        wrong=copy.deepcopy(self.records);wrong[0]['case_identity']='f'*64
        wrong[0]['receipt_sha256']=digest({k:v for k,v in wrong[0].items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):
            chain.bind_threshold(self.context,[CadenceMaximum(canonical(record)) for record in wrong])

    def test_durable_v2_start_precedes_constructor_and_second_entry_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            store,lease=self.lease(Path(tmp))
            def stop(entropy):
                state=journal.replay(store.read().document)['cases'][0]
                self.assertIn('rng_start.json',state['artifacts'])
                marker=json.loads((lease.directory/'rng_start.json').read_bytes())
                self.assertEqual(marker['schema'],chain.START_SCHEMA)
                raise RuntimeError('STOP_BEFORE_DRAW')
            with patch('numpy.random.SeedSequence',side_effect=stop) as constructor:
                with self.assertRaisesRegex(RuntimeError,'STOP_BEFORE_DRAW'):
                    chain.render(self.context,self.plans[0],lease=lease,
                        forbidden_cases=self.forbidden,verify_freeze=lambda manifest:manifest)
                with self.assertRaisesRegex(ValueError,'already exists'):
                    chain.render(self.context,self.plans[0],lease=lease,
                        forbidden_cases=self.forbidden,verify_freeze=lambda manifest:manifest)
                self.assertEqual(constructor.call_count,1)

    def test_freeze_or_identity_failure_precedes_durable_start_and_rng(self):
        for kind in ('freeze','collision'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                store,lease=self.lease(Path(tmp))
                def verify(manifest):
                    if kind=='freeze':raise ValueError('freeze differs')
                forbidden=([{'identity':'f'*64,'seed':self.plans[0]['case']['seed']}]
                    if kind=='collision' else self.forbidden)
                with patch('numpy.random.SeedSequence',side_effect=AssertionError('RNG reached')) as constructor:
                    with self.assertRaises(ValueError):
                        chain.render(self.context,self.plans[0],lease=lease,
                            forbidden_cases=forbidden,verify_freeze=verify)
                    self.assertEqual(constructor.call_count,0)
                self.assertEqual(journal.replay(store.read().document)['cases'][0]['artifacts'],{})

    def test_physical_stage_requires_evaluation_case_threshold_and_v2_writer(self):
        threshold=self.threshold();run=SimpleNamespace(context=self.context);evidence=object();store=object()
        with patch.object(chain.physical,'run_native',return_value={'complete':True}) as execute:
            result=chain.run_physical(run,store,threshold,self.plans[4],evidence=evidence)
        self.assertEqual(result,{'complete':True})
        execute.assert_called_once_with(run,store,threshold,
            case_identity=self.plans[4]['case']['identity'],noise_law_sha256=parent.LAW_SHA,
            evidence=evidence)
        with self.assertRaisesRegex(ValueError,'evaluation threshold'):
            chain.run_physical(run,store,threshold,self.plans[0],evidence=evidence)
        with self.assertRaisesRegex(ValueError,'evidence writer'):
            chain.run_physical(run,store,threshold,self.plans[4],evidence=None)

    def test_empty_complete_reports_keep_reference_floor_and_truth_postdecision(self):
        threshold=self.threshold()
        threshold.validate(self.family,case_identity=self.plans[4]['case']['identity'],
            noise_law_sha256=parent.LAW_SHA,domain='synthetic-native')
        for ordinal,expected in ((4,False),(7,True)):
            plan=self.plans[ordinal]
            report={'complete':True,'family_sha256':digest(self.family.record()),
                'retention':{'case_identity':plan['case']['identity'],'retained':{'on':[]}},
                'decisions':[],'clusters':[],
                'factor_provider_receipt':{'domain':'synthetic-native'}}
            report['result_sha256']=digest(report)
            result=chain.evaluate(report,self.context,plan)
            self.assertEqual(result['engineering_gate_pass'],expected)
            self.assertTrue(result['truth_used_only_after_decisions'])
            self.assertFalse(result['calibrated_rank_gate_pass'])
            self.assertFalse(result['scientific_candidate'])


if __name__=='__main__':unittest.main()

