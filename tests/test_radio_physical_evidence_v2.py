"""v2 lossless framing, resource bounds, faults and numerical observer boundary."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_physical_radio import run_fixture,IncompletePhysical
from test_radio_whole_cadence_physical import PhysicalTests,identity


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'evidence'
        self.case=identity('v2-storage');self.plan=identity('v2-plan');self.existing={'scores.npz':b'old pinned score bytes'}
        self.config=e.configuration('physical-evidence-v2-test',self.case,self.plan,self.existing)
    def tearDown(self):self.tmp.cleanup()
    def writer(self,**changes):return e.Writer.create(self.root,{**self.config,**changes},existing_artifacts=self.existing)
    def doc(self,count=1):return {'retention':{'case_identity':self.case},'rows':[{'i':i,'value':i/3} for i in range(count)],'complete':False}
    def inspect(self,w,**kw):return e.inspect(self.root,expected_config_sha256=w.config_sha,**kw)

    def test_original_bytes_and_unchanged_parts_across_group_boundaries(self):
        w=self.writer();expected=[]
        for count in (0,1,128,129):
            d=self.doc(count);expected.append(canonical(d));w.checkpoint('rows',d)
        before=w.receipt()['stored_bytes'];w.checkpoint('same',d)
        self.assertEqual(w.receipt()['stored_bytes']-before,(self.root/'checkpoints/0004.json').stat().st_size)
        r=self.inspect(w);self.assertEqual([r.snapshot(i) for i in range(4)],expected)

    def test_stream_restores_snapshot_above_old_aggregate_bound(self):
        w=self.writer();d=self.doc();d.update(left='a'*13000000,right='b'*13000000)
        w.checkpoint('large',d);r=self.inspect(w)
        expected=canonical(d);h=hashlib.sha256();size=0
        for chunk in r.iter_snapshot(0):
            self.assertLessEqual(len(chunk),e.PART_BYTES);h.update(chunk);size+=len(chunk)
        self.assertEqual(size,len(expected));self.assertEqual(h.hexdigest(),e.sha(expected))
        with self.assertRaisesRegex(ValueError,'iter_snapshot'):r.snapshot(0)
        self.assertLess(r.stored_bytes,100000)

    def test_overlarge_individual_value_is_final_capacity_failure(self):
        w=self.writer();d=self.doc();d['large']='x'*e.MAX_VALUE_BYTES
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('too-large',d)
        self.assertTrue(w.capacity_failed)
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('retry',self.doc())
        self.assertEqual(w.close('failed','bound')['status'],'failed')

    def test_incompressible_stored_capacity_preserves_footer(self):
        w=self.writer(budget_bytes=100000);w.checkpoint('small',self.doc())
        d=self.doc();d['payload']=''.join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(4096))
        before=e._inventory(self.root)
        with self.assertRaises(e.EvidenceCapacity):w.checkpoint('capacity',d)
        self.assertEqual(e._inventory(self.root),before);w.close('failed','capacity')
        r=self.inspect(w);self.assertEqual(r.summary()['status'],'failed');self.assertLessEqual(r.charged_bytes,100000)

    def test_decompression_overflow_truncation_and_trailing_stream_rejected(self):
        for compressed,wanted in ((zlib.compress(b'aaaa'),3),(zlib.compress(b'aaa')[:-1],3),
                                  (zlib.compress(b'aaa')+zlib.compress(b'bbb'),3)):
            encoded=base64.b64encode(compressed);h=e.sha(encoded)
            d={'kind':'zlib-base64','parts':[h],'bytes':wanted,'sha256':e.sha(b'aaa')}
            with self.assertRaises(ValueError):e._raw(d,{'parts/'+h:encoded},set())

    def test_expansion_bound_checked_before_any_part_decoding(self):
        d={'kind':'zlib-base64','parts':['a'*64],'bytes':e.MAX_VALUE_BYTES,'sha256':'b'*64}
        with self.assertRaisesRegex(ValueError,'expansion'):
            list(e._iter_decode({str(i):d for i in range(6)},{},set()))

    def test_bad_hash_missing_part_and_noncanonical_value_rejected(self):
        for raw in (b'{ "x":1}',b'null '):
            encoded=base64.b64encode(zlib.compress(raw));h=e.sha(encoded)
            d={'kind':'zlib-base64','parts':[h],'bytes':len(raw),'sha256':e.sha(raw)}
            with self.assertRaisesRegex(ValueError,'Noncanonical'):e._raw(d,{'parts/'+h:encoded},set())
        w=self.writer();w.checkpoint('one',self.doc());part=next((self.root/'parts').iterdir());part.unlink()
        with self.assertRaises((ValueError,KeyError)):self.inspect(w)

    def test_lost_ack_poisoned_and_readonly_recovery_cannot_resume(self):
        w=self.writer();original=e.durable_write
        def lost(path,data):
            original(path,data)
            if 'checkpoints' in Path(path).parts:raise OSError('lost ack')
        with patch.object(e,'durable_write',side_effect=lost):
            with self.assertRaises(OSError):w.checkpoint('one',self.doc())
        r=self.inspect(w);self.assertEqual(r.snapshot(0),canonical(self.doc()))
        with self.assertRaises(e.EvidenceStopped):w.checkpoint('retry',self.doc())
        with self.assertRaises(FileExistsError):self.writer()
        self.assertFalse(hasattr(r,'checkpoint'));self.assertFalse(r.summary()['execution_restart_authorized'])

    def test_wrong_case_stale_pin_and_symlink_rejected(self):
        w=self.writer();d=self.doc();d['retention']['case_identity']='f'*64
        with self.assertRaisesRegex(ValueError,'case differs'):w.checkpoint('bad',d)
        w.checkpoint('one',self.doc());old=w.previous;w.checkpoint('two',self.doc(2))
        with self.assertRaisesRegex(ValueError,'independent pin'):self.inspect(w,expected_last_checkpoint_sha256=old)
        (self.root/'link').symlink_to(self.root/'reservation.json')
        with self.assertRaisesRegex(ValueError,'Symlink'):self.inspect(w)

    def test_parent_integration_and_incomplete_completion_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'not qualified'):e.Writer.create_for_lease(None,self.config,existing_artifacts=self.existing)
        w=self.writer()
        with self.assertRaisesRegex(ValueError,'Complete final'):w.close('completed','done',snapshot=self.doc())


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):PhysicalTests.setUpClass();cls.f=PhysicalTests()
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'evidence'
    def tearDown(self):self.tmp.cleanup()
    def writer(self):
        c=e.configuration('physical-v2-integration',identity(200),identity('v2-plan'),{})
        return e.Writer.create(self.root,c,existing_artifacts={})
    def run_case(self,w,factory=None):
        f=self.f
        return run_fixture(f.family,f.store(edits=[('on',0,1,4,(20,20,0))]),f.threshold,
            case_identity=identity(200),noise_law_sha256=f.law,on_factors=f.on,off_factors=f.off,
            receiver_factory=factory or f.factory(),evidence=w)

    def test_full_physical_observer_keeps_result_identical(self):
        expected=self.f.run_case([('on',0,1,4,(20,20,0))]);w=self.writer();actual=self.run_case(w)
        self.assertEqual(canonical(actual),canonical(expected));r=e.inspect(self.root,expected_config_sha256=w.config_sha)
        self.assertEqual(r.snapshot(len(r.checkpoint_bytes)-1),canonical(expected));self.assertEqual(r.summary()['status'],'completed')

    def test_interrupt_preserves_failure(self):
        w=self.writer()
        def interrupt(records):raise TimeoutError('fixed interruption')
        with self.assertRaises(IncompletePhysical):self.run_case(w,interrupt)
        r=e.inspect(self.root,expected_config_sha256=w.config_sha);doc=json.loads(r.snapshot(len(r.checkpoint_bytes)-1))
        self.assertEqual(doc['failure']['stage'],'receiver_signatures');self.assertEqual(r.summary()['status'],'failed')


if __name__=='__main__':unittest.main()
