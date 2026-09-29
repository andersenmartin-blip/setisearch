import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import physical_case_radio as p
from seti_repeater import physical_evidence_radio as e
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_journal import manifest


class PhysicalCaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.tick=0.
        self.base={'base.bin':b'original deterministic bytes'}
        self.m=manifest(1,('base.bin',p.SEAL,p.OUTCOME))
        self.m['caps']['evidence_bytes']=4*1024**2
        self.m['caps']['ledger_reserve_bytes']=1024**2
        self.cap=1024**2
        self.config=e.configuration('physical-case-tests',self.m['cases'][0]['case_identity'],
            self.m['cases'][0]['plan_sha256'],self.base,
            budget_bytes=self.cap-sum(p.CLOSURE_RESERVES.values()))
        self.m['artifact_groups']=p.policy(self.config)
    def tearDown(self):self.tmp.cleanup()
    def claim(self):
        self.store=j.DirectoryStore.create(self.root/'journal',self.m);cp=self.store.read()
        lease=j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(self.m),
            binding=self.m['cases'][0],milliseconds=4000,artifact_bytes=self.cap,
            directory=self.root/'case',clock=lambda:self.tick)
        for name,data in self.base.items():lease.write_artifact(name,data)
        return lease
    def start(self):
        lease=self.claim();return p.PhysicalCase(lease,self.config,existing_artifacts=self.base)
    def doc(self,n=1,complete=False):
        return {'retention':{'case_identity':self.config['case_identity']},
            'rows':[{'i':i,'v':i/7} for i in range(n)],'complete':complete}

    def test_success_all_dynamic_members_registered_once_and_charged(self):
        case=self.start();case.writer.checkpoint('rows',self.doc(129))
        case.writer.close('completed','complete',snapshot=self.doc(129,True));cp=case.finish()
        view,check=p.inspect_case(cp,case.lease.directory)
        self.assertEqual(view.snapshot(1),canonical(self.doc(129,True)))
        self.assertEqual(check['status'],'completed')
        actual=sum(x.stat().st_size for x in case.lease.directory.iterdir())
        self.assertEqual(check['artifact_bytes'],actual)
        self.assertEqual(j.replay(cp.document)['archived_artifact_bytes'],actual)
        self.assertFalse(check['execution_restart_authorized'])
        self.assertTrue(all(x.is_file() for x in case.lease.directory.iterdir()))

    def test_failed_physical_state_seals_as_failed_parent_not_complete(self):
        case=self.start();case.writer.close('failed','old_failure',snapshot=self.doc(2))
        cp=case.finish(reason='retained historical failure')
        self.assertEqual(j.replay(cp.document)['cases'][0]['status'],'failed')
        view,check=p.inspect_case(cp,case.lease.directory)
        self.assertEqual(view.summary()['status'],'failed')
        self.assertFalse(check['can_read_complete_evidence'])

    def test_fixed_legacy_manifest_still_rejects_dynamic_extras_on_completion(self):
        self.m.pop('artifact_groups');lease=self.claim()
        lease.write_artifact('physical-unregistered',b'x')
        with self.assertRaises(ValueError):lease.finish()

    def test_scientific_manifest_cannot_enable_dynamic_policy(self):
        m=copy.deepcopy(self.m);m['mode']='scientific';m['cases']=[]
        for i in range(151):
            c={**self.m['cases'][0],'case_identity':digest({'i':i}),'role':'calibration' if i<127 else 'evaluation'}
            m['cases'].append(c)
        with self.assertRaisesRegex(ValueError,'engineering-only'):j.validate_manifest(m)

    def test_wrong_prospective_physical_binding_rejected_before_write(self):
        lease=self.claim();conf={**self.config,'namespace':'different'}
        with self.assertRaisesRegex(ValueError,'prospective'):p.PhysicalCase(lease,conf,existing_artifacts=self.base)
        self.assertEqual({x.name for x in lease.directory.iterdir()},set(self.base))

    def test_all_base_artifacts_must_be_in_existing_byte_pins(self):
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'inventory'):p.PhysicalCase(lease,self.config,existing_artifacts={})

    def test_unregistered_or_symlinked_base_file_prevents_entry(self):
        lease=self.claim();(lease.directory/'extra').symlink_to(lease.directory/'base.bin')
        with self.assertRaises(ValueError):p.PhysicalCase(lease,self.config,existing_artifacts=self.base)

    def test_full_parent_budget_cannot_consume_failure_reserve(self):
        lease=self.claim();before={x.name for x in lease.directory.iterdir()}
        with self.assertRaisesRegex(ValueError,'reserved closure'):
            lease.write_artifact('physical-oversize',b'x'*(self.cap-sum(p.CLOSURE_RESERVES.values())))
        self.assertEqual({x.name for x in lease.directory.iterdir()},before)

    def test_checkpoint_file_count_stops_before_any_partial_new_batch(self):
        self.m['artifact_groups']['physical']['max_files']=3
        case=self.start();before=e._inventory(case.lease.directory)
        with self.assertRaises(e.EvidenceCapacity):case.writer.checkpoint('many',self.doc(129))
        self.assertEqual(e._inventory(case.lease.directory),before)
        case.writer.close('failed','capacity');case.finish()

    def test_dynamic_member_cannot_be_written_after_seal(self):
        case=self.start();case.writer.close('completed','done',snapshot=self.doc(1,True))
        case.lease.write_artifact(p.SEAL,canonical(j.group_seal(case.lease.checkpoint,'physical',complete=True)))
        with self.assertRaisesRegex(ValueError,'Sealed'):case.lease.write_artifact('physical-extra',b'x')
        self.assertFalse((case.lease.directory/'physical-extra').exists())

    def test_seal_omitting_member_cannot_pass_archive_verification(self):
        case=self.start();case.writer.close('completed','done',snapshot=self.doc(1,True))
        seal=j.group_seal(case.lease.checkpoint,'physical',complete=True);seal['artifacts'].pop(next(iter(seal['artifacts'])))
        case.lease.write_artifact(p.SEAL,canonical(seal))
        with self.assertRaisesRegex(ValueError,'seal inventory'):p.inspect_case(case.lease.checkpoint,case.lease.directory)

    def test_failed_group_seal_blocks_direct_lease_completion(self):
        case=self.start();case.writer.close('failed','failed',snapshot=self.doc())
        case.lease.write_artifact(p.SEAL,canonical(j.group_seal(case.lease.checkpoint,'physical',complete=False)))
        case.lease.write_artifact(p.OUTCOME,b'{}')
        with self.assertRaisesRegex(ValueError,'completion differs'):case.lease.finish()

    def test_unrecognized_file_outside_policy_rejected_before_durable_write(self):
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'outside fixed'):lease.write_artifact('extra.bin',b'x')
        self.assertFalse((lease.directory/'extra.bin').exists())

    def test_timeout_writes_only_bounded_reserved_failed_footer(self):
        case=self.start();case.writer.checkpoint('before_timeout',self.doc(2));self.tick=5.
        result=case.fail(TimeoutError('deadline'))
        self.assertTrue(result['outer_footer_written']);self.assertEqual(result['parent_status'],'failed')
        raw=(case.lease.directory/p.OUTCOME).read_bytes();self.assertLess(len(raw),65536)
        self.assertIsNotNone(json.loads(raw)['physical_closure_error'])
        self.assertEqual(j.replay(self.store.read().document)['cases'][0]['status'],'failed')
        with self.assertRaises(ValueError):case.lease.budget()
        self.assertFalse((case.lease.directory/'partial_physical_or_retention.json').exists())

    def test_failure_finalization_is_irreversible_and_limited_to_reserved_files(self):
        lease=self.claim();self.tick=5.
        with self.assertRaisesRegex(ValueError,'reserved'):lease.write_failure_artifact('physical-new',b'x')
        lease.write_failure_artifact(p.OUTCOME,b'{}')
        with self.assertRaisesRegex(ValueError,'cannot resume'):lease.write_artifact('physical-new',b'x')
        with self.assertRaises(ValueError):lease.finish()
        lease.finish('failed','timeout')

    def test_failure_finalization_has_one_shared_five_second_window(self):
        lease=self.claim();lease.write_failure_artifact(p.OUTCOME,b'{}');self.tick=6.
        with self.assertRaisesRegex(ValueError,'window exhausted'):lease.write_failure_artifact(p.SEAL,b'{}')
        self.assertFalse((lease.directory/p.SEAL).exists())

    def test_lost_artifact_ack_retains_written_bytes_but_no_resume_or_false_finish(self):
        case=self.start();original=self.store.publish
        def lost(revision,document):
            original(revision,document);raise OSError('lost artifact acknowledgement')
        with patch.object(self.store,'publish',side_effect=lost):
            with self.assertRaises(OSError):case.writer.checkpoint('lost',self.doc(2))
        self.assertTrue(case.lease.broken);self.assertTrue(case.writer.poisoned)
        result=case.fail(OSError('uncertain'))
        self.assertEqual(result['parent_status'],'uncertain');self.assertFalse(result['outer_footer_written'])
        self.assertNotEqual(j.replay(self.store.read().document)['cases'][0]['status'],'completed')
        with self.assertRaises(ValueError):case.lease.write_failure_artifact(p.OUTCOME,b'{}')

    def test_torn_artifact_stays_visible_and_case_is_uncertain(self):
        case=self.start();original=j.durable_write
        def torn(path,data):
            if Path(path).name.startswith('physical-part-'):
                original(path,data[:1]);raise OSError('torn member')
            original(path,data)
        with patch.object(j,'durable_write',side_effect=torn):
            with self.assertRaises(OSError):case.writer.checkpoint('torn',self.doc(2))
        self.assertEqual(case.fail(OSError('torn'))['parent_status'],'uncertain')
        with self.assertRaisesRegex(ValueError,'Unregistered'):j.verify_archive(self.store.read(),case.lease.directory,case_index=0)

    def test_original_config_budget_cannot_hide_outer_reservations(self):
        conf={**self.config,'budget_bytes':self.cap};self.m['artifact_groups']=p.policy(conf)
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'closure reserves'):p.PhysicalCase(lease,conf,existing_artifacts=self.base)

    def test_flat_round_trip_and_unknown_names_rejected(self):
        for path in ['reservation.json','outcome.json','parts/'+'a'*64,'checkpoints/0123.json']:
            self.assertEqual(e.nested_name(e.flat_name(path)),path)
        for name in ['physical-../bad','physical-checkpoint-00000.json','physical-part-bad']:
            with self.assertRaises(ValueError):e.nested_name(name)

    def test_cumulative_journal_capacity_stops_before_artifact_write_and_allows_failed_closure(self):
        self.m['caps']['ledger_reserve_bytes']=j.GROUP_LEDGER_FINALIZATION_RESERVE+24000
        lease=self.claim();stopped=False
        for i in range(100):
            before=e._inventory(lease.directory)
            try:lease.write_artifact('physical-test'+str(i),b'x')
            except ValueError as error:
                self.assertIn('Cumulative journal history',str(error));stopped=True
                self.assertEqual(e._inventory(lease.directory),before);break
        self.assertTrue(stopped)
        lease.write_failure_artifact(p.OUTCOME,b'{}');lease.finish('failed','journal capacity')
        self.assertLessEqual(sum(x.stat().st_size for x in (self.root/'journal').rglob('*') if x.is_file()),self.m['caps']['ledger_reserve_bytes'])

    def test_too_small_journal_cannot_enable_group(self):
        self.m['caps']['ledger_reserve_bytes']=65536
        with self.assertRaisesRegex(ValueError,'closure reserve'):j.validate_manifest(self.m)


if __name__=='__main__':unittest.main()
