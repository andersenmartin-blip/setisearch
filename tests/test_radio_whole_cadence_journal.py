"""New consumption boundaries; no proposed random values or old ledger reuse."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater import whole_cadence_journal_radio as j


def manifest(count=2,required=('result.json',)):
    def sha(x):return digest({'engineering':'journal-tests-20260928','label':x})
    return {'schema':j.SCHEMA,'mode':'engineering','namespace':'journal-tests-20260928',
        'execution_binding_sha256':sha('binding'),'allocation_sha256':sha('allocation'),
        'cases':[{'case_identity':sha(str(i)),'plan_sha256':sha('plan'+str(i)),
            'context_sha256':sha('context'),'source_contract_sha256':sha('source'),
            'noise_law_sha256':sha('law'),'role':'engineering'} for i in range(count)],
        'caps':{**j.CAPS,'active_milliseconds':10000,'evidence_bytes':1048576,'ledger_reserve_bytes':65536},
        'required_artifacts':list(required)}


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.m=manifest();self.store=j.DirectoryStore.create(self.root/'store',self.m)
        self.tick=0.

    def tearDown(self):self.temp.cleanup()

    def claim(self,index=0,store=None,**kwargs):
        store=store or self.store;c=store.read()
        args=dict(expected_revision=c.revision,expected_manifest_sha256=digest(self.m),
            binding=self.m['cases'][index],milliseconds=4000,artifact_bytes=1000,
            directory=self.root/('case'+str(index)),clock=lambda:self.tick)
        args.update(kwargs);return j.consume(store,**args)

    def done(self):
        lease=self.claim();lease.write_artifact('result.json',b'{}');lease.finish();return lease

    def test_duplicate_consumption_stops_before_local_directory(self):
        self.claim()
        with self.assertRaisesRegex(ValueError,'incomplete'):self.claim(directory=self.root/'duplicate')
        self.assertFalse((self.root/'duplicate').exists())
        self.assertEqual(len(j.replay(self.store.read().document)['cases']),1)

    def test_order_cannot_skip_first_case(self):
        with self.assertRaisesRegex(ValueError,'order'):self.claim(1)
        self.assertEqual(self.store.read().document['events'],[])

    def test_independent_manifest_checkpoint_required(self):
        with self.assertRaisesRegex(ValueError,'checkpoint'):self.claim(expected_manifest_sha256='a'*64)
        self.assertEqual(self.store.read().document['events'],[])

    def test_stale_revision_rejected(self):
        old=self.store.read();self.claim()
        with self.assertRaisesRegex(ValueError,'checkpoint'):self.claim(expected_revision=old.revision)

    def test_changed_plan_does_not_consume(self):
        bad={**self.m['cases'][0],'plan_sha256':'a'*64}
        with self.assertRaisesRegex(ValueError,'binding'):self.claim(binding=bad)
        self.assertEqual(self.store.read().document['events'],[])

    def test_failed_local_directory_still_consumes(self):
        p=self.root/'occupied';p.mkdir()
        with self.assertRaises(FileExistsError):self.claim(directory=p)
        self.assertEqual(j.replay(self.store.read().document)['cases'][0]['status'],'consumed')
        with self.assertRaises(ValueError):self.claim()

    def test_successful_archive_restores_readonly(self):
        lease=self.done();check=self.store.read()
        result=j.verify_archive(check,lease.directory,case_index=0)
        self.assertTrue(result['can_read_complete_evidence'])
        self.assertFalse(result['execution_restart_authorized'])
        self.assertFalse(result['incomplete_is_statistical_empty'])

    def test_finish_missing_required_artifact_rejected(self):
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'Incomplete evidence'):lease.finish()
        self.assertNotEqual(j.replay(self.store.read().document)['cases'][0]['status'],'completed')

    def test_registered_artifact_corruption_rejected(self):
        lease=self.done();(lease.directory/'result.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'bytes differ'):j.verify_archive(self.store.read(),lease.directory,case_index=0)

    def test_missing_completed_artifact_rejected(self):
        lease=self.done();(lease.directory/'result.json').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):j.verify_archive(self.store.read(),lease.directory,case_index=0)

    def test_partial_unregistered_write_never_completes(self):
        lease=self.claim();(lease.directory/'partial').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'partial'):lease.finish()
        with self.assertRaisesRegex(ValueError,'partial'):lease.write_artifact('result.json',b'{}')

    def test_no_artifact_overwrite(self):
        lease=self.claim();lease.write_artifact('result.json',b'{}')
        with self.assertRaisesRegex(ValueError,'overwrite'):lease.write_artifact('result.json',b'[]')
        self.assertEqual((lease.directory/'result.json').read_bytes(),b'{}')

    def test_symlink_artifact_is_not_an_archive(self):
        lease=self.done();p=lease.directory/'result.json';p.unlink()
        other=self.root/'other';other.write_bytes(b'{}');p.symlink_to(other)
        with self.assertRaisesRegex(ValueError,'regular'):j.verify_archive(self.store.read(),lease.directory,case_index=0)

    def test_path_escape_rejected(self):
        lease=self.claim()
        for name in ('../escape','/tmp/escape','x/y','..','x\\y'):
            with self.assertRaisesRegex(ValueError,'filename'):lease.write_artifact(name,b'x')

    def test_single_case_bytes_capped_before_write(self):
        lease=self.claim(artifact_bytes=1)
        with self.assertRaisesRegex(ValueError,'reservation exhausted'):lease.write_artifact('result.json',b'{}')
        self.assertEqual(list(lease.directory.iterdir()),[])
        lease.finish('failed','byte cap');self.assertTrue(j.replay(self.store.read().document)['attempt_failed'])

    def test_cumulative_time_reservations_never_refunded(self):
        lease=self.claim(milliseconds=9000);lease.write_artifact('result.json',b'{}');lease.finish()
        with self.assertRaisesRegex(ValueError,'Cumulative'):self.claim(1,milliseconds=1001)
        self.assertEqual(j.replay(self.store.read().document)['reserved_milliseconds'],9000)

    def test_cumulative_evidence_reservations_never_refunded(self):
        lease=self.claim(artifact_bytes=980000);lease.write_artifact('result.json',b'{}');lease.finish()
        with self.assertRaisesRegex(ValueError,'Cumulative'):self.claim(1,artifact_bytes=10000)

    def test_clock_limit_blocks_completion(self):
        lease=self.claim();lease.write_artifact('result.json',b'{}');self.tick=5.
        with self.assertRaisesRegex(ValueError,'active-time'):lease.finish()
        lease.finish('failed','time cap')
        with self.assertRaisesRegex(ValueError,'closed'):self.claim(1)

    def test_regressed_clock_rejected(self):
        lease=self.claim();self.tick=1.;lease.budget();self.tick=.5
        with self.assertRaisesRegex(ValueError,'clock regressed'):lease.budget()

    def test_rss_and_modelled_memory_caps(self):
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'Modelled'):lease.budget(j.CAPS['modelled_array_bytes']+1)
        class Usage:ru_maxrss=2**30
        with patch.object(j.resource,'getrusage',return_value=Usage()):
            with self.assertRaisesRegex(ValueError,'RSS'):lease.budget()

    def test_finished_lease_cannot_restart(self):
        lease=self.done()
        with self.assertRaisesRegex(ValueError,'closed'):lease.write_artifact('later',b'x')
        with self.assertRaisesRegex(ValueError,'newly published'):j.Lease(None,None,None,None,None)

    def test_remote_ambiguity_after_publish_never_returns_permission(self):
        base=self.store
        class Ambiguous:
            def read(self):return base.read()
            def publish(self,*args):base.publish(*args);raise OSError('lost response after durable commit')
        with self.assertRaisesRegex(OSError,'lost response'):self.claim(store=Ambiguous())
        self.assertEqual(len(j.replay(base.read().document)['cases']),1)
        self.assertFalse((self.root/'case0').exists())

    def test_wrong_readback_never_returns_permission(self):
        base=self.store;old=base.read()
        class Stale:
            calls=0
            def read(self):
                self.calls+=1
                return old if self.calls==3 else base.read()
            def publish(self,*args):base.publish(*args)
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.claim(store=Stale())
        self.assertEqual(len(j.replay(base.read().document)['cases']),1)

    def test_mutated_chain_fails_even_with_new_document_digest(self):
        self.done();doc=self.store.read().document;doc['events'][0]['event']['milliseconds']=1
        with self.assertRaisesRegex(ValueError,'chain'):j.replay(doc)

    def test_cas_conflict_does_not_overwrite_newer_revision(self):
        old=self.store.read();self.claim();current=self.store.read()
        with self.assertRaisesRegex(ValueError,'CAS'):self.store.publish(old.revision,old.document)
        self.assertEqual(self.store.read(),current)

    def test_attempt_failed_cannot_move_to_next_case(self):
        lease=self.claim();lease.finish('failed','technical error')
        with self.assertRaisesRegex(ValueError,'closed'):self.claim(1)

    def test_local_store_cannot_be_scientific_authority(self):
        m=manifest();m['mode']='scientific'
        with self.assertRaisesRegex(ValueError,'engineering-only'):j.DirectoryStore.create(self.root/'fake',m)

    def test_engineering_lease_rejected_before_proposed_generator(self):
        from radio_receiver_adapter_common import context
        from seti_repeater.whole_cadence_render_radio import prepare,render_gaussian
        raw=(Path(__file__).resolve().parents[1]/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes()
        c=context('calibration');plan=prepare(c,json.loads(raw)['cases'][0],raw);lease=self.claim()
        with patch('numpy.random.Generator',side_effect=AssertionError('No proposed RNG')):
            with self.assertRaisesRegex(ValueError,'PROPOSED_NOT_ACTIVATED'):render_gaussian(c,plan,lease=lease)
        self.assertFalse(j.replay(self.store.read().document)['cases'][0]['rng_started'])

    def test_torn_head_is_not_repaired(self):
        p=self.root/'store/HEAD';p.write_bytes(b'torn')
        with self.assertRaisesRegex(ValueError,'Torn'):self.store.read()
        self.assertEqual(p.read_bytes(),b'torn')

    def test_incomplete_archive_is_readonly_and_not_empty(self):
        lease=self.claim();lease.write_artifact('result.json',b'{}')
        r=j.verify_archive(self.store.read(),lease.directory,case_index=0)
        self.assertEqual(r['status'],'consumed');self.assertFalse(r['can_read_complete_evidence'])
        self.assertFalse(r['execution_restart_authorized']);self.assertFalse(r['incomplete_is_statistical_empty'])

    def test_mutated_case_quota_cannot_enlarge_running_lease(self):
        lease=self.claim();lease.case['milliseconds']=1000000
        with self.assertRaisesRegex(ValueError,'case or caps changed'):lease.budget()
        self.assertEqual(j.replay(self.store.read().document)['reserved_milliseconds'],4000)

    def test_mutated_memory_cap_cannot_enlarge_running_lease(self):
        lease=self.claim();lease.manifest['caps']['rss_bytes']=2**60
        with self.assertRaisesRegex(ValueError,'case or caps changed'):lease.budget()


if __name__=='__main__':unittest.main()
