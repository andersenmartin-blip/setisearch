"""Offline orchestration stubs: never actual eight-case authority or RNG.

All identities, plans, proof receipts and score documents below are marked
engineering unit-test stubs. Only storage/closure and offline Git mechanics are
real. These tests establish control flow, not transport or detector qualification.
"""
import copy
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from seti_repeater import native_v2_runner_radio as r
from seti_repeater import physical_case_v2_radio as cases
from seti_repeater import physical_evidence_v2_radio as physical
from seti_repeater import whole_cadence_journal_radio as journal
from seti_repeater.empty_null_radio import canonical, EMPTY
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_native_v2_broker import InlineGit

STUB_NAMESPACE='unit-test-runner-engineering-stubs-no-public-authority'


def proofs(authority):
    freeze={'schema':r.FREEZE_PROOF_SCHEMA,
        **{k:authority[k] for k in ('namespace','freeze_kind','freeze_commit','freeze_sha256',
            'code_inventory_sha256','input_inventory_sha256','runtime_inventory_sha256')},
        'code_files_verified':True,'input_files_verified':True,'runtime_files_verified':True,
        'exact_public_readback_verified':True,'execution_authorized':True,
        'transport_integration_qualified':True,'restart_authorized':False,
        'scientific_execution_authorized':False}
    reservation={'schema':r.RESERVATION_PROOF_SCHEMA,
        **{k:authority[k] for k in ('namespace','freeze_commit','freeze_sha256','reservation_commit',
            'reservation_sha256','allocation_sha256','ordered_case_identities')},
        'all_eight_irrevocably_reserved':True,'all_eight_allocation_remains_spent':True,
        'exact_public_readback_verified':True,'restart_authorized':False,
        'scientific_execution_authorized':False}
    return freeze,reservation


class StubRun:
    modelled_bytes=0
    def build_store(self):return {'engineering_unit_test_stub':True}
    def validate_store(self,store):assert store=={'engineering_unit_test_stub':True}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.clock=0.;self.git=InlineGit()
        self.saved=[];self.raw=[];self.trace=[];self.active=None;self.host_receipts=[]
        self.fail_stage=None;self.fail_ordinal=0;self.gate_failure=None
        self.context=object();self.plans=[]
        for ordinal in range(8):
            self.plans.append({'engineering_unit_test_stub':True,'plan_sha256':digest(['stub-plan',ordinal]),
                'case':{'identity':digest(['stub-identity',ordinal]),'ordinal':ordinal,'seed':ordinal,
                    'context_sha256':digest('stub-context'),'source_contract_sha256':digest('stub-source'),
                    'noise_law_sha256':digest('stub-law'),
                    'spec':{'reference':ordinal<4,'kind':'stub-only'}}})
        bindings=[r.parent.case_binding(p) for p in self.plans]
        self.configs=[physical.configuration(STUB_NAMESPACE,b['case_identity'],b['plan_sha256'],{},
            budget_bytes=r.parent.CASE_BYTES-sum(cases.CLOSURE_RESERVES.values()),
            checkpoint_limit=r.parent.CHECKPOINT_LIMIT) for b in bindings]
        self.manifest={'schema':journal.SCHEMA,'mode':'engineering','namespace':STUB_NAMESPACE,
            'execution_binding_sha256':digest('stub-freeze'),'allocation_sha256':digest('stub-allocation'),
            'cases':bindings,'caps':r.parent.caps(),'required_artifacts':list(r.parent.REQUIRED_ARTIFACTS),
            'artifact_groups':cases.multi_policy(self.configs,max_files=r.parent.PHYSICAL_MAX_FILES)}
        self.authority={'schema':'unit-test-authority-not-public','namespace':STUB_NAMESPACE,
            'freeze_kind':'COMPLETE_RUNNER_BROKER_RUNTIME','freeze_commit':'a'*40,
            'reservation_commit':'b'*40,'freeze_sha256':digest('stub-freeze'),
            'reservation_sha256':digest('stub-reservation'),'allocation_sha256':digest('stub-allocation'),
            'code_inventory_sha256':digest('stub-code'),'input_inventory_sha256':digest('stub-input'),
            'runtime_inventory_sha256':digest('stub-runtime'),
            'ordered_case_identities':[p['case']['identity'] for p in self.plans]}
        self.freeze_proof,self.reservation_proof=proofs(self.authority)
        prepared={'plans':self.plans,'manifest':self.manifest,'configs':self.configs}
        patches=[patch.object(r,'prepare_manifest',return_value=prepared),
            patch.object(r,'validate_authority',side_effect=lambda a,*args:copy.deepcopy(a)),
            patch.object(r.chain,'render',side_effect=self.render),
            patch.object(r.gaussian,'compact_parts',side_effect=self.compact_parts),
            patch.object(r.compact,'audit',return_value={'engineering_unit_test_stub':True}),
            patch.object(r.chain,'bind_threshold',side_effect=self.threshold),
            patch.object(r.chain,'run_physical',side_effect=self.run_physical),
            patch.object(r.chain,'evaluate',side_effect=self.evaluate),
            patch.object(r.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=0)),
            patch.object(physical.time,'monotonic',return_value=0.),
            patch.object(journal.uuid,'uuid4',side_effect=[uuid.UUID(int=i+1) for i in range(1024)]),
            patch('numpy.random.SeedSequence',side_effect=AssertionError('Actual RNG forbidden')),
            patch('numpy.random.Generator',side_effect=AssertionError('Actual RNG forbidden'))]
        for p in patches:p.start();self.addCleanup(p.stop)

    def fault(self,stage,ordinal):
        if self.fail_stage==stage and self.fail_ordinal==ordinal:
            raise RuntimeError('STUB_FAILURE_'+stage)

    def render(self,context,plan,*,lease,forbidden_cases,verify_freeze):
        ordinal=plan['case']['ordinal'];self.trace.append(('render',ordinal))
        if ordinal:
            self.assertEqual(len(self.host_receipts),ordinal)
            self.assertEqual(len(self.runner.publisher.receipts),ordinal)
        state=journal.replay(lease.checkpoint.document)['cases'][-1]
        self.assertEqual(set(state['artifacts']),{'physical-reservation.json'})
        verify_freeze(lease.manifest);self.fault('render',ordinal)
        lease.write_artifact('rng_start.json',canonical({'engineering_stub_no_rng_constructed':True}))
        run=StubRun()
        def build():
            self.fault('score',ordinal)
            if self.fail_stage=='case_time' and ordinal==self.fail_ordinal:self.clock+=601
            return {'engineering_unit_test_stub':True}
        run.build_store=build
        return run,{'engineering_unit_test_stub':True}

    def compact_parts(self,run,store,plan,renderer):
        ordinal=plan['case']['ordinal'];self.fault('compact',ordinal)
        record={'schema':'radio-whole-cadence-maximum-v1','maximum':EMPTY.record(),
            'case_identity':plan['case']['identity'],'engineering_unit_test_stub':True,
            'domain':'unit-test-not-observed-reference'}
        record['receipt_sha256']=digest(record)
        return {'sources.json':canonical({'engineering_unit_test_stub':True}),
            'scores.json':canonical({'engineering_unit_test_stub':True}),
            'scores.npz':b'engineering stub bytes, no numerical arrays',
            'maximum.json':canonical(record),'renderer.json':canonical(renderer)}

    def threshold(self,context,units):
        self.assertEqual(len(units),4);self.assertEqual(len(self.host_receipts),4)
        self.trace.append(('threshold',4));return object()

    def run_physical(self,run,store,threshold,plan,*,evidence):
        ordinal=plan['case']['ordinal'];self.trace.append(('physical',ordinal))
        document={'complete':False,'retention':{'case_identity':plan['case']['identity']},
            'engineering_unit_test_stub':True}
        evidence.checkpoint('stub_predecision',document);self.fault('physical',ordinal)
        document['complete']=True;document['result_sha256']=digest(document)
        evidence.close('completed','stub_terminal',snapshot=document)

    def evaluate(self,document,context,plan):
        ordinal=plan['case']['ordinal'];self.fault('evaluate',ordinal)
        self.trace.append(('evaluate',ordinal))
        return {'engineering_unit_test_stub':True,'engineering_gate_pass':self.gate_failure!=ordinal,
            'association':[],'scientific_candidate':False}

    def usage(self):
        return {'schema':r.HOST_SCHEMA,**{k:0 for k in r.HOST_COUNTERS},
            'calls':len(self.git.calls),'cases':len(self.host_receipts),
            'elapsed_seconds':self.clock,'automatic_retry':False,
            'visible_tool_objects_only':True,'hidden_http_bytes_known':False}

    def prepare(self,freeze_json,pin):
        self.assertIsNone(self.active);self.assertEqual(digest(json.loads(freeze_json)),pin)
        self.active=json.loads(freeze_json);self.fault('prepare_transport',self.active['ordinal'])

    def finish(self):
        freeze=self.active;ordinal=freeze['ordinal'];self.fault('finish_transport',ordinal)
        receipt=self.runner.publisher.receipts[-1]
        result={'ordinal':ordinal,'parent':freeze['parent'],'commit':receipt['commit'],
            'tree':receipt['tree'],'bundle_sha256':digest(freeze),
            'actual_tool_usage':{k:0 for k in r.HOST_COUNTERS},'raw_git_receipt':{'engineering_unit_test_stub':True},
            'automatic_retry':False}
        self.host_receipts.append(result);self.active=None;self.trace.append(('barrier',ordinal))
        return result

    def persist(self,ordinal,operation,request,result):
        raw=canonical(result);self.raw.append((ordinal,operation,request,raw))
        return {'bytes':len(raw),'sha256':physical.sha(raw)}

    def save(self,record):
        self.saved.append(copy.deepcopy(record));raw=canonical(record)
        if self.fail_stage=='persist_time' and record['status']=='CLOSED_ENGINEERING_PASS':self.clock=4801
        return {'bytes':len(raw),'sha256':physical.sha(raw)}

    def make_runner(self,**changes):
        kwargs={'authority':self.authority,'verify_freeze':lambda m:copy.deepcopy(self.freeze_proof),
            'verify_reservation':lambda a:copy.deepcopy(self.reservation_proof),'target':self.root/'run',
            'forbidden_cases':[],'invoke':self.git.invoke,'persist':self.persist,
            'parent_sha':self.git.head,'parent_tree_sha':self.git.root,'transport_usage':self.usage,
            'prepare_transport':self.prepare,'finish_transport':self.finish,'persist_state':self.save,
            'clock':lambda:self.clock}
        kwargs.update(changes);self.runner=r.Runner(self.context,self.plans,self.manifest,**kwargs)
        return self.runner

    def stopped(self,runner=None):
        with self.assertRaises(r.RunnerStopped) as caught:(runner or self.runner).run()
        return caught.exception.result

    def test_eight_stub_cases_close_publish_and_finish_once_before_next_case(self):
        runner=self.make_runner();result=runner.run()
        self.assertEqual(result['status'],'CLOSED_ENGINEERING_PASS')
        self.assertEqual([row['ordinal'] for row in result['cases']],list(range(8)))
        self.assertEqual(len(result['broker_receipts']),8)
        self.assertEqual(len(result['transport_terminal_receipts']),8)
        self.assertEqual(len(result['raw_transport_receipts']),len(self.git.calls))
        state=journal.replay(runner.store.read().document)
        self.assertEqual([c['status'] for c in state['cases']],['completed']*8)
        for ordinal,case in enumerate(state['cases']):
            self.assertEqual(set(case['artifacts']),set(p.name for p in (runner.target/f'case{ordinal:02d}').iterdir()))
            view=cases.inspect_case(runner.store.read(),runner.target/f'case{ordinal:02d}',case_index=ordinal)[0]
            wrapper=json.loads(view.snapshot(len(view.checkpoint_bytes)-1));original=r.original_snapshot(wrapper)
            self.assertTrue(original['complete'])
            self.assertIn('native_v2_engineering_gate',wrapper)
            if ordinal<4:self.assertTrue(original['reference_only'])
        methods=[operation for operation,_ in self.git.calls]
        self.assertEqual(methods.count('create_tree'),8);self.assertEqual(methods.count('update_ref'),8)
        self.assertEqual(methods.count('fetch_files'),8)
        before=len(self.git.calls);self.stopped(runner);self.assertEqual(len(self.git.calls),before)
        self.assertFalse(result['telescope_values_opened']);self.assertFalse(result['scientific_candidate'])
        self.assertTrue(any(row['stage']=='physical_until_stub_terminal' for row in result['stage_resources']))

    def test_missing_qualified_freeze_or_reservation_stops_before_storage(self):
        for field in ('freeze','reservation'):
            with self.subTest(field=field):
                if field=='freeze':self.freeze_proof['transport_integration_qualified']=False
                else:self.reservation_proof['exact_public_readback_verified']=False
                result=self.stopped(self.make_runner())
                self.assertEqual(result['status'],'CLOSED_FAILED');self.assertFalse((self.root/'run').exists())
                self.assertEqual(self.trace,[]);self.assertEqual(self.git.calls,[])
                self.freeze_proof,self.reservation_proof=proofs(self.authority)

    def test_stub_render_failure_closes_and_publishes_only_failed_case(self):
        self.fail_stage='render';runner=self.make_runner();result=self.stopped()
        state=journal.replay(runner.store.read().document)
        self.assertEqual([c['status'] for c in state['cases']],['failed'])
        self.assertEqual(result['failure_closure']['parent_status'],'failed')
        self.assertEqual(len(result['broker_receipts']),1);self.assertEqual(len(self.host_receipts),1)
        self.assertEqual(self.trace,[('render',0),('barrier',0)])

    def test_gate_failure_is_published_once_and_no_next_case(self):
        self.gate_failure=4;runner=self.make_runner();result=self.stopped()
        self.assertEqual(len(result['cases']),5);self.assertEqual(len(result['broker_receipts']),5)
        self.assertFalse(result['cases'][-1]['engineering_gate_pass'])
        self.assertNotIn(('render',5),self.trace);self.assertIsNone(result['failure_publication'])

    def test_mutation_reply_lost_stops_without_retry_or_next_case(self):
        self.git.lost_update=True;runner=self.make_runner();result=self.stopped()
        self.assertTrue(result['broker_failed_attempt']['update_may_have_landed'])
        self.assertEqual(result['broker_usage']['unknown_response_count'],1)
        self.assertEqual([x[0] for x in self.git.calls].count('update_ref'),1)
        before=len(self.git.calls);self.stopped(runner);self.assertEqual(len(self.git.calls),before)
        self.assertNotIn(('render',1),self.trace)

    def test_finish_transport_failure_retains_confirmed_python_commit(self):
        self.fail_stage='finish_transport';runner=self.make_runner();result=self.stopped()
        self.assertEqual(len(result['broker_receipts']),1)
        self.assertEqual(result['broker_receipts'][0]['commit'],self.git.head)
        self.assertEqual(result['transport_terminal_receipts'],[])
        self.assertNotIn(('render',1),self.trace)

    def test_case_time_cap_failure_keeps_registered_prefix_and_allocation_spent(self):
        self.fail_stage='case_time';runner=self.make_runner();result=self.stopped()
        self.assertTrue(result['all_eight_allocation_remains_spent'])
        self.assertFalse(result['restart_authorized']);self.assertNotIn(('render',1),self.trace)
        state=journal.replay(runner.store.read().document)
        self.assertEqual(state['cases'][0]['status'],'failed')

    def test_final_persistence_exceeding_whole_time_cannot_return_pass(self):
        self.fail_stage='persist_time';runner=self.make_runner();result=self.stopped()
        self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(result['broker_receipts']),8)
        self.assertEqual(result['cases'][-1]['publication']['commit'],self.git.head)

    def test_usage_error_during_failure_still_retains_forensic_result(self):
        def broken_usage():raise OSError('stub usage unavailable')
        result=self.stopped(self.make_runner(transport_usage=broken_usage))
        self.assertIn('transport_usage_error',result);self.assertTrue(self.saved)
        self.assertFalse((self.root/'run').exists())

    def test_usage_precheck_cannot_grant_execution_time_again(self):
        def slow_usage():
            self.clock=4801
            value=self.usage();value['elapsed_seconds']=0
            return value
        result=self.stopped(self.make_runner(transport_usage=slow_usage))
        self.assertIn('wall-time cap exceeded',result['failure']['error'])
        self.assertFalse((self.root/'run').exists());self.assertEqual(self.trace,[])

    def test_terminal_extraction_requires_closed_matching_exact_archive(self):
        self.fail_stage='render';runner=self.make_runner();self.stopped()
        physical_map,journal_map,base,pins=r.terminal_maps(runner.store,runner.lease,runner.configs[0])
        self.assertIn('reservation.json',physical_map);self.assertIn('HEAD',journal_map)
        self.assertIn(cases.SEAL,base);self.assertEqual(pins['config_sha256'],digest(runner.configs[0]))
        (runner.lease.directory/'case_outcome.json').write_bytes(b'changed stub bytes')
        with self.assertRaises(ValueError):r.terminal_maps(runner.store,runner.lease,runner.configs[0])

    def test_failed_numerical_stages_close_without_next_case(self):
        for stage in ('score','compact'):
            with self.subTest(stage=stage):
                self.fail_stage=stage
                runner=self.make_runner(target=self.root/stage);result=self.stopped()
                self.assertEqual(result['status'],'CLOSED_FAILED')
                self.assertEqual(journal.replay(runner.store.read().document)['cases'][0]['status'],'failed')
                self.assertNotIn(('render',1),self.trace)
                self.git=InlineGit();self.active=None;self.host_receipts=[];self.trace=[]

    def test_host_resource_cap_is_enforced_before_storage(self):
        def excessive():
            value=self.usage();value['receipt_bytes']=value['receipt_charged_bytes']=1536*1024**2+1
            return value
        result=self.stopped(self.make_runner(transport_usage=excessive))
        self.assertIn('capacity exceeded',result['failure']['error'])
        self.assertFalse((self.root/'run').exists());self.assertEqual(self.git.calls,[])

    def test_checkpoint_wrapper_restores_only_exact_original_bytes(self):
        original={'complete':True,'engineering_unit_test_stub':True}
        wrapper={**original,'native_v2_runner_checkpoint':{'schema':r.CHECKPOINT_SCHEMA,
            'original_snapshot_sha256':digest(original)}}
        self.assertEqual(r.original_snapshot(wrapper),original)
        wrapper['complete']=False
        with self.assertRaisesRegex(ValueError,'Original report'):r.original_snapshot(wrapper)

    def test_deadline_nested_stages_preserve_outer_timer_and_external_timer(self):
        with r.deadline(2):
            outer=signal.getitimer(signal.ITIMER_REAL)[0]
            with r.deadline(1):self.assertLessEqual(signal.getitimer(signal.ITIMER_REAL)[0],1)
            self.assertLessEqual(signal.getitimer(signal.ITIMER_REAL)[0],outer)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        signal.setitimer(signal.ITIMER_REAL,2)
        try:
            with self.assertRaisesRegex(ValueError,'external deadline'):
                with r.deadline(1):pass
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0],0)
        finally:signal.setitimer(signal.ITIMER_REAL,0)

    def test_nested_timeout_restores_handlers_and_no_retry_timer(self):
        previous=signal.getsignal(signal.SIGALRM)
        with self.assertRaises(TimeoutError):
            with r.deadline(2):
                with r.deadline(1):signal.raise_signal(signal.SIGALRM)
        self.assertEqual(signal.getsignal(signal.SIGALRM),previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))


class FreshCompactBindingTests(unittest.TestCase):
    """Only stub metadata is inspected, never saved sources or score arrays."""
    def setUp(self):
        self.context=object()
        self.plans=[{'plan_sha256':digest(['compact-stub-plan',i]),'case':{
            'identity':digest(['compact-stub-identity',i]),'context_sha256':digest('compact-stub-context'),
            'source_contract_sha256':digest('compact-stub-source')}} for i in range(8)]
        self.binding={'case_identity':self.plans[0]['case']['identity'],
            'plan_sha256':self.plans[0]['plan_sha256'],'context_sha256':digest('compact-stub-context'),
            'source_contract_sha256':digest('compact-stub-source'),'noise_law_sha256':r.parent.LAW_SHA}
        self.renderer={'noise_law':r.parent.LAW,'scientific_allocation_charged':False}
        p=patch.object(r.parent,'make_plan',side_effect=lambda ctx,i:copy.deepcopy(self.plans[i]))
        p.start();self.addCleanup(p.stop)

    def test_exact_stub_metadata_matches_fresh_schema_binding(self):
        r.compact._fresh_v2_renderer_binding(self.context,self.binding,self.renderer)

    def test_rehashed_stale_or_scientific_metadata_cannot_match(self):
        for field in ('plan_sha256','context_sha256','source_contract_sha256','noise_law_sha256'):
            with self.subTest(field=field):
                changed={**self.binding,field:digest('changed-stub')}
                with self.assertRaises(ValueError):r.compact._fresh_v2_renderer_binding(self.context,changed,self.renderer)
        with self.assertRaises(ValueError):r.compact._fresh_v2_renderer_binding(self.context,self.binding,
            {**self.renderer,'scientific_allocation_charged':True})

    def test_duplicate_stub_identity_is_not_unique_fresh_binding(self):
        self.plans[1]=copy.deepcopy(self.plans[0])
        with self.assertRaises(ValueError):r.compact._fresh_v2_renderer_binding(self.context,self.binding,self.renderer)


if __name__=='__main__':unittest.main()
