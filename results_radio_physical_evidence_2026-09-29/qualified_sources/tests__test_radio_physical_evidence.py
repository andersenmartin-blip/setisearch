"""Storage faults and physical observer integration, with deterministic fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import physical_evidence_radio as e
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_physical_radio import run_fixture,IncompletePhysical
from test_radio_whole_cadence_physical import PhysicalTests,identity


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'evidence'
        self.case=identity('storage');self.plan=identity('plan');self.existing={'scores.npz':b'fixed old score bytes'}
        self.config=e.configuration('physical-evidence-test',self.case,self.plan,self.existing)
    def tearDown(self):self.tmp.cleanup()
    def writer(self,**changes):
        c={**self.config,**changes};return e.Writer.create(self.root,c,existing_artifacts=self.existing)
    def doc(self,count=1):
        return {'retention':{'case_identity':self.case,'immutable':'x'*2048},'rows':[{'i':i,'value':i/3} for i in range(count)],'complete':False}
    def inspect(self,w,**kw):return e.inspect(self.root,expected_config_sha256=w.config_sha,**kw)

    def test_every_checkpoint_restores_exact_original_bytes_including_empty_lists(self):
        w=self.writer();raw=[]
        for count in (0,1,128,129,1024):
            d=self.doc(count);raw.append(canonical(d));w.checkpoint('rows',d)
        d=self.doc(1024);d['complete']=True;raw.append(canonical(d));w.close('completed','done',snapshot=d)
        r=self.inspect(w,expected_last_checkpoint_sha256=w.previous)
        self.assertEqual([r.snapshot(i) for i in range(6)],raw)
        self.assertEqual(r.summary()['status'],'completed');self.assertFalse(hasattr(r,'consume'))
        self.assertFalse(hasattr(r,'checkpoint'));self.assertFalse(r.summary()['execution_restart_authorized'])

    def test_unchanged_parts_are_shared_and_all_checkpoint_metadata_charged(self):
        w=self.writer();d=self.doc(1024);w.checkpoint('a',d);size=w.receipt()['stored_bytes']
        w.checkpoint('b',d)
        row=(self.root/'checkpoints/0001.json').stat().st_size
        self.assertEqual(w.receipt()['stored_bytes']-size,row)
        r=self.inspect(w);self.assertEqual(r.charged_bytes,r.stored_bytes+len(self.existing['scores.npz']))

    def test_existing_artifact_pin_or_amount_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError,'artifact bytes differ'):
            e.Writer.create(self.root,self.config,existing_artifacts={'scores.npz':b'changed'})
        self.assertFalse(self.root.exists())

    def test_wrong_case_has_no_checkpoint(self):
        w=self.writer();d=self.doc();d['retention']['case_identity']='f'*64
        with self.assertRaisesRegex(ValueError,'case differs'):w.checkpoint('bad',d)
        self.assertEqual(w.count,0)

    def test_case_cap_rejected_before_any_new_file_and_footer_survives(self):
        w=self.writer(budget_bytes=100000);w.checkpoint('small',self.doc());before=e._inventory(self.root)
        d=self.doc();d['oversize']='z'*50000
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('oversize',d)
        self.assertEqual(e._inventory(self.root),before)
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('cannot_shrink_to_retry',self.doc())
        ref=w.close('failed','oversize','bound exceeded',snapshot=d);self.assertFalse(ref['final_snapshot_saved'])
        r=self.inspect(w);self.assertEqual(len(r.checkpoint_bytes),1);self.assertLessEqual(r.charged_bytes,100000)
        self.assertLessEqual(len(r.footer_bytes),e.FOOTER_RESERVE);self.assertEqual(r.summary()['status'],'failed')

    def test_checkpoint_limit_is_irrevocable_and_cannot_be_completed(self):
        w=self.writer(checkpoint_limit=1);w.checkpoint('first',self.doc())
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('second',self.doc())
        d=self.doc();d['complete']=True
        with self.assertRaises(ValueError):w.close('completed','done',snapshot=d)
        self.assertEqual(w.close('failed','capacity')['status'],'failed')

    def test_missing_or_tampered_committed_part_rejected(self):
        w=self.writer();w.checkpoint('first',self.doc());part=next((self.root/'parts').iterdir());data=part.read_bytes()
        part.write_bytes(data+b' ')
        with self.assertRaises(ValueError):self.inspect(w)
        with self.assertRaises(e.EvidenceStopped):w.checkpoint('later',self.doc())
        self.assertTrue(w.poisoned)

    def test_stale_pin_cannot_hide_later_checkpoint(self):
        w=self.writer();w.checkpoint('first',self.doc());old=w.previous;w.checkpoint('second',self.doc(2))
        with self.assertRaisesRegex(ValueError,'independent pin'):self.inspect(w,expected_last_checkpoint_sha256=old)

    def test_reordered_or_missing_checkpoint_rejected(self):
        w=self.writer();w.checkpoint('first',self.doc());w.checkpoint('second',self.doc(2))
        (self.root/'checkpoints/0000.json').unlink()
        with self.assertRaisesRegex(ValueError,'gap'):self.inspect(w)

    def test_unregistered_file_cannot_be_hidden_by_clean_checkpoint(self):
        w=self.writer();w.checkpoint('first',self.doc());(self.root/'unexpected').write_bytes(b'orphan')
        with self.assertRaisesRegex(ValueError,'unexpected evidence'):self.inspect(w)
        r=self.inspect(w,allow_orphans=True);self.assertEqual(r.orphan_paths,('unexpected',))
        self.assertEqual(r.snapshot(0),canonical(self.doc()))

    def test_lost_ack_after_durable_checkpoint_poisoned_but_reader_sees_written_bytes(self):
        w=self.writer();original=e.durable_write
        def lost(path,data):
            original(path,data)
            if 'checkpoints' in Path(path).parts:raise OSError('lost acknowledgement')
        with patch.object(e,'durable_write',side_effect=lost):
            with self.assertRaises(OSError):w.checkpoint('first',self.doc())
        self.assertTrue(w.poisoned)
        with self.assertRaises(e.EvidenceStopped):w.checkpoint('retry',self.doc())
        r=self.inspect(w);self.assertEqual(r.snapshot(0),canonical(self.doc()));self.assertIsNone(r.footer_bytes)
        self.assertEqual(w.close('failed','lost')['status'],'uncertain')

    def test_partial_part_write_preserves_prior_prefix_and_counts_orphan(self):
        w=self.writer();w.checkpoint('first',self.doc());original=e.durable_write
        def partial(path,data):
            if 'parts' in Path(path).parts:
                original(path,data[:2]);raise OSError('partial part')
            original(path,data)
        d=self.doc(2)
        with patch.object(e,'durable_write',side_effect=partial):
            with self.assertRaises(OSError):w.checkpoint('second',d)
        r=self.inspect(w,allow_orphans=True);self.assertEqual(len(r.checkpoint_bytes),1)
        self.assertTrue(r.orphan_paths);self.assertEqual(r.snapshot(0),canonical(self.doc()))

    def test_partial_checkpoint_recovers_only_valid_prefix_and_never_skips_it(self):
        w=self.writer();w.checkpoint('first',self.doc());original=e.durable_write
        def partial(path,data):
            if 'checkpoints' in Path(path).parts:
                original(path,data[:20]);raise OSError('torn commit')
            original(path,data)
        with patch.object(e,'durable_write',side_effect=partial):
            with self.assertRaises(OSError):w.checkpoint('second',self.doc(2))
        with self.assertRaises(ValueError):self.inspect(w)
        r=self.inspect(w,allow_orphans=True);self.assertEqual(len(r.checkpoint_bytes),1)
        self.assertIn('checkpoints/0001.json',r.orphan_paths)

    def test_footer_write_failure_never_certifies_completed_state(self):
        w=self.writer();d=self.doc();d['complete']=True;original=e.durable_write
        def fail(path,data):
            if Path(path).name=='outcome.json':raise OSError('footer unavailable')
            original(path,data)
        with patch.object(e,'durable_write',side_effect=fail):
            with self.assertRaises(OSError):w.close('completed','done',snapshot=d)
        r=self.inspect(w);self.assertIsNone(r.footer_bytes);self.assertTrue(w.poisoned)
        with self.assertRaises(e.EvidenceStopped):w.checkpoint('again',d)

    def test_completed_marker_rejected_for_incomplete_physical_snapshot(self):
        w=self.writer()
        with self.assertRaisesRegex(ValueError,'Complete final'):w.close('completed','done',snapshot=self.doc())
        self.assertFalse((self.root/'outcome.json').exists())

    def test_existing_directory_and_readonly_data_cannot_start_writer(self):
        w=self.writer();w.checkpoint('one',self.doc())
        with self.assertRaises(FileExistsError):self.writer()
        with self.assertRaises(ValueError):e.Writer(self.root,self.config)

    def test_symlink_and_modified_reservation_rejected(self):
        w=self.writer();(self.root/'link').symlink_to(self.root/'reservation.json')
        with self.assertRaisesRegex(ValueError,'Symlink'):self.inspect(w)
        (self.root/'link').unlink();w.config['budget_bytes']-=1
        with self.assertRaises(e.EvidenceStopped):w.checkpoint('one',self.doc())

    def test_reader_blocks_reference_expansion_before_decoding(self):
        descriptor={'kind':'raw','parts':['a'*64],'bytes':e.MAX_BYTES,'sha256':'b'*64}
        with self.assertRaisesRegex(ValueError,'expansion'):e._decode({'first':descriptor,'second':descriptor},{})


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PhysicalTests.setUpClass();cls.fixture=PhysicalTests()
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'evidence'
    def tearDown(self):self.tmp.cleanup()
    def writer(self,**changes):
        c=e.configuration('physical-integration-fixture',identity(200),identity('plan'),{},**changes)
        return e.Writer.create(self.root,c,existing_artifacts={})
    def run_case(self,w,factory=None):
        f=self.fixture
        return run_fixture(f.family,f.store(edits=[('on',0,1,4,(20,20,0))]),f.threshold,
            case_identity=identity(200),noise_law_sha256=f.law,on_factors=f.on,off_factors=f.off,
            receiver_factory=factory or f.factory(),evidence=w)

    def test_observer_leaves_numerical_result_byte_identical(self):
        expected=self.fixture.run_case([('on',0,1,4,(20,20,0))]);w=self.writer();actual=self.run_case(w)
        self.assertEqual(canonical(actual),canonical(expected))
        r=e.inspect(self.root,expected_config_sha256=w.config_sha,expected_last_checkpoint_sha256=w.previous)
        self.assertEqual(r.snapshot(len(r.checkpoint_bytes)-1),canonical(expected));self.assertEqual(r.summary()['status'],'completed')

    def test_timeout_keeps_latest_stage_and_final_failed_snapshot_with_rss(self):
        w=self.writer()
        def interrupt(records):raise TimeoutError('fixed injected timeout')
        with self.assertRaises(IncompletePhysical) as caught:self.run_case(w,interrupt)
        self.assertTrue(caught.exception.evidence_reference['final_snapshot_saved'])
        r=e.inspect(self.root,expected_config_sha256=w.config_sha);doc=json.loads(r.snapshot(len(r.checkpoint_bytes)-1))
        self.assertEqual(doc['failure']['stage'],'receiver_signatures');self.assertTrue(doc['retention']['complete'])
        footer=json.loads(r.footer_bytes);self.assertEqual(footer['status'],'failed');self.assertGreater(footer['peak_process_rss_bytes'],0)

    def test_keyboard_interrupt_is_failed_evidence_without_restart(self):
        w=self.writer()
        def interrupt(records):raise KeyboardInterrupt('fixed cancellation')
        with self.assertRaises(IncompletePhysical):self.run_case(w,interrupt)
        r=e.inspect(self.root,expected_config_sha256=w.config_sha);self.assertEqual(r.summary()['status'],'failed')

    def test_bad_receiver_receipt_and_returned_signatures_are_saved_before_check(self):
        w=self.writer();factory=self.fixture.factory()
        def bad(records):
            sig,rec=factory(records);rec['signatures_sha256']='f'*64;return sig,rec
        with self.assertRaises(IncompletePhysical) as caught:self.run_case(w,bad)
        r=e.inspect(self.root,expected_config_sha256=w.config_sha);doc=json.loads(r.snapshot(len(r.checkpoint_bytes)-1))
        self.assertEqual(doc['receiver_receipt']['signatures_sha256'],'f'*64)
        self.assertTrue(doc['receiver_signatures']);self.assertFalse(doc['complete'])

    def test_storage_capacity_failure_cannot_return_complete_physical_result(self):
        w=self.writer(checkpoint_limit=1)
        with self.assertRaises(IncompletePhysical) as caught:self.run_case(w)
        self.assertFalse(caught.exception.evidence['complete']);self.assertTrue(w.capacity_failed)
        r=e.inspect(self.root,expected_config_sha256=w.config_sha);self.assertEqual(r.summary()['status'],'failed')
        self.assertEqual(len(r.checkpoint_bytes),1)
