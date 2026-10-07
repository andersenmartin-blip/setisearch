import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('activity', HERE/'activity.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
build_spec = importlib.util.spec_from_file_location('build_successor', HERE/'build_successor.py')
b = importlib.util.module_from_spec(build_spec); build_spec.loader.exec_module(b)


def packet(kind, seq, gen=0, flags=0, name='', path='', pid=73005, t=None):
    nb, pb = name.encode(), path.encode(); t = t or seq + 1
    open_fields = (1, 2, 3, 0o100755, 4, 5) if kind == a.OPEN else (0,)*6
    return a.EVENT.pack(b'RLA1',2,kind,seq,pid,gen,0,open_fields[0],open_fields[1],
                        open_fields[2],open_fields[3],open_fields[4],flags,open_fields[5],0,t,len(nb),len(pb))+nb+pb


def valid():
    return [packet(a.HANDSHAKE,0,flags=2), packet(a.ACTIVITY,1,flags=a.ADD),
            packet(a.OPEN,2,1,name='',path='/proc/self/exe'),
            packet(a.OPEN,3,2,name='/lib/x.so',path='/usr/lib/x.so'),
            packet(a.ACTIVITY,4,1,flags=a.CONSISTENT), packet(a.PREINIT,5,1),
            packet(a.ACTIVITY,6,1,flags=a.ADD),
            packet(a.OPEN,7,3,name='/lib/y.so',path='/usr/lib/y.so'),
            packet(a.ACTIVITY,8,1,flags=a.CONSISTENT),
            packet(a.ACTIVITY,9,1,flags=a.DELETE), packet(a.CLOSE,10,3),
            packet(a.ACTIVITY,11,1,flags=a.CONSISTENT)]


def ledger(records=None):
    out=a.ActivityLedger(73005)
    for raw in records or valid(): out.consume(raw)
    return out


class ActivityTests(unittest.TestCase):
    def refuse(self, records):
        x=a.ActivityLedger(73005)
        with self.assertRaises(a.Refusal):
            for r in records: x.consume(r)
        self.assertTrue(x.poisoned); self.assertTrue(x.failures)
        with self.assertRaises(a.Refusal): x.consume(packet(a.HANDSHAKE,99,flags=2))

    def test_valid_startup_add_delete(self):
        r=ledger().receipt(); self.assertEqual((r['batches'],r['records']), (3,12))
        self.assertEqual(r['live_generations'],[1,2]); self.assertFalse(r['dispatch_enabled'])
    def test_raw_records_retained(self):
        x=ledger(); self.assertEqual(x.raw_records[0]['sha256'],hashlib.sha256(valid()[0]).hexdigest())
    def test_no_authority_booleans(self):
        r=ledger().receipt(); self.assertTrue(all(r[k] is False for k in
          ('collector_authentication','continuous_loader_file_coverage','native_runtime_qualification','codec_science_authority','terminal_qualification')))
    def test_dispatch_closed(self):
        with self.assertRaises(a.Refusal): a.dispatch()
    def test_activity_not_rewritten(self): self.assertEqual(a.decode(valid()[1])['kind'],a.ACTIVITY)
    def test_missing_handshake(self): self.refuse(valid()[1:2])
    def test_duplicate_handshake(self): self.refuse(valid()[:1]+valid()[:1])
    def test_nested_batch(self): self.refuse(valid()[:2]+[packet(a.ACTIVITY,2,flags=a.ADD)])
    def test_consistent_without_batch(self): self.refuse(valid()[:1]+[packet(a.ACTIVITY,1,flags=a.CONSISTENT)])
    def test_wrong_bootstrap_head(self): self.refuse(valid()[:1]+[packet(a.ACTIVITY,1,1,flags=a.ADD)])
    def test_wrong_runtime_head(self): self.refuse(valid()[:6]+[packet(a.ACTIVITY,6,2,flags=a.ADD)])
    def test_open_outside_add(self): self.refuse(valid()[:1]+[valid()[2]])
    def test_close_in_add(self): self.refuse(valid()[:2]+[packet(a.CLOSE,2,1)])
    def test_open_in_delete(self): self.refuse(valid()[:6]+[packet(a.ACTIVITY,6,1,flags=a.DELETE),valid()[7]])
    def test_empty_runtime_batch(self): self.refuse(valid()[:6]+[packet(a.ACTIVITY,6,1,flags=a.ADD),packet(a.ACTIVITY,7,1,flags=a.CONSISTENT)])
    def test_preinit_during_batch(self): self.refuse(valid()[:4]+[packet(a.PREINIT,4,1)])
    def test_preinit_wrong_main(self): self.refuse(valid()[:5]+[packet(a.PREINIT,5,2)])
    def test_main_replacement(self): self.refuse(valid()[:3]+[packet(a.OPEN,3,2,name='',path='/proc/self/exe')])
    def test_nonabsolute_name(self): self.refuse(valid()[:3]+[packet(a.OPEN,3,2,name='x.so',path='/x.so')])
    def test_nonabsolute_path(self): self.refuse(valid()[:2]+[packet(a.OPEN,2,1,name='',path='exe')])
    def test_generation_gap(self): self.refuse(valid()[:2]+[packet(a.OPEN,2,2,name='',path='/proc/self/exe')])
    def test_double_close(self): self.refuse(valid()+[packet(a.ACTIVITY,12,1,flags=a.DELETE),packet(a.CLOSE,13,3)])
    def test_main_close(self): self.refuse(valid()[:6]+[packet(a.ACTIVITY,6,1,flags=a.DELETE),packet(a.CLOSE,7,1)])
    def test_wrong_pid(self): self.refuse([packet(a.HANDSHAKE,0,flags=2,pid=9)])
    def test_sequence_gap(self): self.refuse(valid()[:1]+[packet(a.ACTIVITY,2,flags=a.ADD)])
    def test_nonincreasing_time(self): self.refuse([packet(a.HANDSHAKE,0,flags=2,t=2),packet(a.ACTIVITY,1,flags=a.ADD,t=2)])
    def test_bad_nonopen_payload(self):
        raw=bytearray(packet(a.ACTIVITY,0,flags=a.ADD)); raw[32]=1; self.refuse([bytes(raw)])
    def test_unknown_flag(self): self.refuse(valid()[:1]+[packet(a.ACTIVITY,1,flags=9)])
    def test_veto_retained(self): self.refuse(valid()[:1]+[packet(a.VETO,1,flags=5)])
    def test_incomplete_batch_no_receipt(self):
        x=ledger(valid()[:2]);
        with self.assertRaises(a.Refusal): x.receipt()
    def test_deterministic_successor_and_no_raw_cookie_emit(self):
        raw=b.SOURCE.read_bytes(); one=b.derive(raw); two=b.derive(raw)
        self.assertEqual(one,two); self.assertNotIn(b'(uint64_t)*cookie,0,0,flag',one)
        self.assertIn(b'objects[gen].cookie_slot==cookie',one)
    def test_successor_rejects_drift(self):
        with self.assertRaises(ValueError): b.derive(b.SOURCE.read_bytes()+b' ')
    def test_strict_syntax_only(self):
        with tempfile.NamedTemporaryFile(suffix='.c') as f:
            f.write(b.derive(b.SOURCE.read_bytes())); f.flush()
            p=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fsyntax-only',f.name],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
