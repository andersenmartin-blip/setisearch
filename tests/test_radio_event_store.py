import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import whole_cadence_event_store_radio as s
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater import physical_case_radio as p
from seti_repeater import physical_evidence_radio as e
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_journal import manifest


class EventStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.base={'base.bin':b'deterministic base bytes'}
        self.m=manifest(1,('base.bin',p.SEAL,p.OUTCOME));self.m['caps']['evidence_bytes']=4*1024**2
        self.m['caps']['ledger_reserve_bytes']=1024**2
        self.config=e.configuration('event-store-tests',self.m['cases'][0]['case_identity'],
            self.m['cases'][0]['plan_sha256'],self.base,budget_bytes=1024**2-sum(p.CLOSURE_RESERVES.values()))
        self.m['artifact_groups']=p.policy(self.config)
        self.store=s.EventDirectoryStore.create(self.root/'journal',self.m)
    def tearDown(self):self.tmp.cleanup()
    def claim(self):
        cp=self.store.read()
        lease=j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(self.m),
            binding=self.m['cases'][0],milliseconds=10000,artifact_bytes=1024**2,directory=self.root/'case')
        lease.write_artifact('base.bin',self.base['base.bin']);return lease
    def history(self,**kw):
        head=(self.store.path/'HEAD').read_text().strip()
        return s.read_history(self.store.path,expected_genesis_sha256=self.store.genesis_sha256,
            expected_pointer_sha256=head,**kw)
    def doc(self,complete=False):return {'retention':{'case_identity':self.config['case_identity']},'rows':[1,2,3],'complete':complete}

    def test_all_original_revisions_and_pointer_versions_retained_exactly(self):
        originals=[canonical(self.store.read().document)];lease=self.claim()
        history=self.history();originals=list(history.revision_bytes)
        for i in range(12):
            lease.write_artifact('physical-test'+str(i),b'x');originals.append(canonical(lease.checkpoint.document))
        history=self.history();self.assertEqual(list(history.revision_bytes),originals)
        self.assertEqual(history.summary()['stored_bytes'],sum(x.stat().st_size for x in self.store.path.rglob('*') if x.is_file()))
        self.assertEqual(len(list((self.store.path/'pointers').iterdir())),len(originals))
        self.assertLess(history.summary()['stored_bytes'],history.summary()['original_revision_bytes'])
        self.assertFalse(hasattr(history,'publish'));self.assertFalse(hasattr(history,'consume'))

    def test_complete_physical_case_uses_event_store_without_duplicate_archive(self):
        lease=self.claim();case=p.PhysicalCase(lease,self.config,existing_artifacts=self.base)
        case.writer.checkpoint('start',self.doc());case.writer.close('completed','end',snapshot=self.doc(True))
        cp=case.finish();view,check=p.inspect_case(cp,lease.directory)
        self.assertEqual(view.snapshot(1),canonical(self.doc(True)));self.assertEqual(check['status'],'completed')
        self.assertEqual(self.history().revision_bytes[-1],canonical(cp.document))

    def test_old_readonly_bytes_cannot_open_publisher_or_reconsume_case(self):
        self.claim()
        with self.assertRaisesRegex(ValueError,'exclusive'):s.EventDirectoryStore(self.store.path,self.store.genesis_sha256)
        with self.assertRaises(FileExistsError):s.EventDirectoryStore.create(self.store.path,self.m)
        cp=self.store.read()
        with self.assertRaisesRegex(ValueError,'incomplete'):
            j.consume(self.store,expected_revision=cp.revision,expected_manifest_sha256=digest(self.m),binding=self.m['cases'][0],
                milliseconds=1000,artifact_bytes=1024**2,directory=self.root/'retry')

    def test_changed_event_or_removed_pointer_rejected(self):
        self.claim();head=(self.store.path/'HEAD').read_text().strip()
        path=self.store.path/'events/0000.json';original=path.read_bytes();path.write_bytes(original+b' ')
        with self.assertRaises(ValueError):self.history()
        path.write_bytes(original);(self.store.path/'pointers/0001.json').unlink()
        with self.assertRaises((ValueError,KeyError)):self.history()

    def test_stale_pointer_cannot_hide_later_events(self):
        old=(self.store.path/'HEAD').read_bytes();self.claim();current=(self.store.path/'HEAD').read_text().strip()
        (self.store.path/'HEAD').write_bytes(old)
        with self.assertRaises(ValueError):s.read_history(self.store.path,expected_genesis_sha256=self.store.genesis_sha256,expected_pointer_sha256=current)
        with self.assertRaisesRegex(ValueError,'Uncommitted'):self.history()

    def test_partial_event_retains_only_old_prefix_and_explicit_orphans(self):
        lease=self.claim();before=self.history();original=j.durable_write
        def torn(path,data):
            if Path(path).parent.name=='events':original(path,data[:3]);raise OSError('torn event')
            original(path,data)
        with patch.object(j,'durable_write',side_effect=torn):
            with self.assertRaises(OSError):lease.write_artifact('physical-partial',b'x')
        self.assertTrue(lease.broken);self.assertTrue(self.store.stopped)
        recovered=self.history(allow_orphans=True)
        self.assertEqual(recovered.revision_bytes,before.revision_bytes);self.assertEqual(len(recovered.orphan_paths),1)
        with self.assertRaises(ValueError):lease.finish('failed')

    def test_partial_head_retains_event_and_pointer_as_uncommitted(self):
        lease=self.claim();before=self.history();original=j.durable_write
        def torn(path,data):
            if Path(path).name.startswith('HEAD.'):
                original(path,b'xx');raise OSError('torn head')
            original(path,data)
        with patch.object(j,'durable_write',side_effect=torn):
            with self.assertRaises(OSError):lease.write_artifact('physical-partial',b'x')
        recovered=self.history(allow_orphans=True)
        self.assertEqual(recovered.revision_bytes,before.revision_bytes);self.assertEqual(len(recovered.orphan_paths),3)
        self.assertTrue(lease.broken)

    def test_lost_ack_after_head_swap_preserves_committed_revision_but_stops_lease(self):
        lease=self.claim();original=self.store.publish;before=len(self.history().revision_bytes)
        def lost(rev,doc):original(rev,doc);raise OSError('lost acknowledgement')
        with patch.object(self.store,'publish',side_effect=lost):
            with self.assertRaises(OSError):lease.write_artifact('physical-written',b'x')
        self.assertTrue(lease.broken);self.assertEqual(len(self.history().revision_bytes),before+1)
        self.assertEqual((lease.directory/'physical-written').read_bytes(),b'x')
        with self.assertRaises(ValueError):lease.write_failure_artifact(p.OUTCOME,b'{}')

    def test_unknown_file_symlink_or_modified_genesis_cannot_enter_active_cache(self):
        extra=self.store.path/'unexpected';extra.write_bytes(b'x')
        with self.assertRaises(ValueError):self.store.read()
        extra.unlink();extra.symlink_to(self.store.path/'genesis.json')
        with self.assertRaises(ValueError):self.store.read()

    def test_capacity_counts_all_event_and_pointer_versions_and_protects_closure(self):
        # Separate fresh bounded store, same deterministic fixture definition.
        m=json.loads(canonical(self.m));m['caps']['ledger_reserve_bytes']=j.GROUP_LEDGER_FINALIZATION_RESERVE+12000
        self.store=s.EventDirectoryStore.create(self.root/'small',m);self.m=m
        lease=self.claim();refused=False
        for i in range(40):
            before=e._inventory(lease.directory)
            try:lease.write_artifact('physical-test'+str(i),b'x')
            except ValueError as error:
                self.assertIn('Cumulative events',str(error));self.assertEqual(e._inventory(lease.directory),before)
                refused=True;break
        self.assertTrue(refused)
        lease.write_failure_artifact(p.OUTCOME,b'{}');lease.finish('failed','capacity')
        self.assertLessEqual(self.history().summary()['stored_bytes'],m['caps']['ledger_reserve_bytes'])


if __name__=='__main__':unittest.main()
