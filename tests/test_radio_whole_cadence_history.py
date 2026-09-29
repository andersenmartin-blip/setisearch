"""New lossless history format: byte identity, partial states and no authority."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from test_radio_whole_cadence_capacity import fixture
from seti_repeater import whole_cadence_history_radio as h
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);m,rs=fixture(1)
        s=j.DirectoryStore.create(root/'store',m);cp=s.read()
        lease=j.consume(s,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
                        binding=m['cases'][0],milliseconds=1000,artifact_bytes=1000,directory=root/'case',clock=lambda:0.)
        lease.write_artifact('a.json',b'{}');lease.write_artifact('b.bin',b'bytes');lease.finish()
        self.raw=sorted((p.read_bytes() for p in (root/'store/revisions').iterdir()),key=lambda x:len(json.loads(x)['events']))
        self.pins=[hashlib.sha256(x).hexdigest() for x in self.raw]
        self.payload=h.encode(self.raw,expected_revision_sha256s=self.pins)
    def tearDown(self):self.tmp.cleanup()
    def verify(self,payload=None,**kw):
        payload=self.payload if payload is None else payload
        return h.verify(payload,expected_sha256=hashlib.sha256(payload).hexdigest(),expected_revision_sha256s=self.pins,**kw)

    def test_every_original_byte_and_revision_restored(self):
        v=self.verify();self.assertEqual([v.revision(i) for i in range(len(self.raw))],self.raw)
        self.assertLess(len(self.payload),sum(map(len,self.raw)))
        self.assertFalse(v.summary()['execution_restart_authorized'])

    def test_consumed_incomplete_state_stays_consumed(self):
        raw=self.raw[:2];pins=self.pins[:2];p=h.encode(raw,expected_revision_sha256s=pins)
        v=h.verify(p,expected_sha256=hashlib.sha256(p).hexdigest(),expected_revision_sha256s=pins)
        self.assertEqual(j.replay(json.loads(v.revision(1)))['cases'][0]['status'],'consumed')
        self.assertFalse(v.summary()['writable_store_qualified'])

    def test_missing_middle_or_last_revision_rejected(self):
        for raw in (self.raw[:2]+self.raw[3:],self.raw[:-1]):
            with self.assertRaises(ValueError):h.encode(raw,expected_revision_sha256s=self.pins)

    def test_reordered_revision_rejected(self):
        raw=list(self.raw);raw[1],raw[2]=raw[2],raw[1]
        with self.assertRaises(ValueError):h.encode(raw,expected_revision_sha256s=self.pins)

    def test_duplicate_original_pin_rejected(self):
        pins=list(self.pins);pins[1]=pins[0]
        with self.assertRaises(ValueError):h.encode(self.raw,expected_revision_sha256s=pins)

    def test_changed_event_with_rehashed_envelope_rejected(self):
        p=json.loads(self.payload);p['latest']['events'][-1]['event']['reason']='changed'
        with self.assertRaises(ValueError):self.verify(canonical(p))

    def test_changed_revision_hash_cannot_be_self_certified(self):
        p=json.loads(self.payload);p['checkpoints'][0]['sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'pin'):self.verify(canonical(p))

    def test_forged_short_lengths_rejected_by_restoration(self):
        p=json.loads(self.payload);p['checkpoints'][0]['size']=1
        with self.assertRaisesRegex(ValueError,'differs'):self.verify(canonical(p))

    def test_raw_envelope_hash_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'independent pin'):
            h.verify(self.payload,expected_sha256='f'*64,expected_revision_sha256s=self.pins)

    def test_encoded_and_decoded_caps_stop_before_approval(self):
        for kw in ({'encoded_cap':len(self.payload)-1},{'decoded_cap':sum(map(len,self.raw))-1}):
            with self.assertRaisesRegex(ValueError,'capacity'):self.verify(**kw)

    def test_archive_cannot_grant_restart(self):
        p=json.loads(self.payload);p['execution_restart_authorized']=True
        with self.assertRaisesRegex(ValueError,'authority'):self.verify(canonical(p))

    def test_history_object_cannot_be_a_journal_lease(self):
        v=self.verify();self.assertNotIsInstance(v,j.Lease)
        self.assertFalse(hasattr(v,'write_artifact'));self.assertFalse(hasattr(v,'begin_gaussian'))

    def test_boolean_or_out_of_range_revision_index_rejected(self):
        v=self.verify()
        for i in (True,-1,len(self.raw)):
            with self.assertRaises(ValueError):v.revision(i)


if __name__=='__main__':unittest.main()
