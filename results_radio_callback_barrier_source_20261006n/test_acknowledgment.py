"""Manufactured packets over real local sockets; no C callback is executed."""
import array
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('ack',Path(__file__).with_name('acknowledgment.py'))
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
EVIDENCE=[]


class AckTests(unittest.TestCase):
    def setUp(self):
        self.event={'kind':2,'sequence':7,'pid':1234,'generation':3}
        self.a,self.b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        self.barrier=n.SourceBarrier();self.inputs=[]

    def tearDown(self):
        EVIDENCE.append({'test':self.id(),'invented_inputs':self.inputs,'failure':self.barrier.failure,
                         'raw_ack_hex':self.barrier.raw_ack,'barrier_closed':self.barrier.closed,
                         'native_callback_executions':0,'observer_authenticated':False,'science_identity':None})
        self.a.close();self.b.close()

    def bytes(self,decision=1,**changes):
        e=dict(self.event);e.update(changes);raw=n.fixture_ack_bytes(e,decision)
        self.inputs.append({'ack_hex':raw.hex(),'fixture_identity':e});return raw

    def wait(self,raw=None):
        if raw is not None: self.b.sendmsg([raw])
        return self.barrier.wait_fixture(self.a,self.event,0.2)

    def event_packet(self,version=2,sequence=7,pid=1234,gen=3):
        return n.EVENT.pack(b'RLA1',version,2,sequence,pid,gen,0,0,0,0,0,0,0,0,0,1,0,0)

    def test_golden_wire_layout(self):
        # Independent literal encoding of the documented 28-byte ACK layout.
        golden=bytes.fromhex('5241434b0200020007000000d2040000030000000000000001000000')
        self.assertEqual(n.fixture_ack_bytes(self.event,1),golden)
        r=n.inspect_ack(golden,self.event);self.assertFalse(r['observer_authentication'])
        self.assertFalse(r['native_or_science_release_authority'])

    def test_source_wait_matches_without_native_authority(self):
        r=self.wait(self.bytes());self.assertFalse(r['native_or_science_release_authority'])

    def test_callback_fixture_cannot_advance_before_ack(self):
        done=threading.Event();fail=[]
        def producer():
            try:
                self.a.sendmsg([self.event_packet()])
                self.barrier.wait_fixture(self.a,self.event,0.5)
                self.a.sendmsg([b'next-fabricated-event']);done.set()
            except BaseException as exc: fail.append(str(exc))
        thread=threading.Thread(target=producer);thread.start()
        self.b.settimeout(0.2);self.assertEqual(self.b.recv(200),self.event_packet())
        self.b.settimeout(0.03)
        with self.assertRaises(TimeoutError): self.b.recv(200)
        self.assertFalse(done.is_set());self.b.sendmsg([self.bytes()]);thread.join(0.7)
        self.assertFalse(thread.is_alive());self.assertFalse(fail)
        self.assertEqual(self.b.recv(200),b'next-fabricated-event');self.assertTrue(done.is_set())

    def test_negative_ack_is_retained(self):
        with self.assertRaisesRegex(n.Refusal,'observer rejection'): self.wait(self.bytes(0))
        self.assertTrue(self.barrier.failure['raw_ack_hex'])

    def test_missing_ack_times_out_and_cannot_resume(self):
        with self.assertRaisesRegex(n.Refusal,'timeout'): self.barrier.wait_fixture(self.a,self.event,0.01)
        with self.assertRaises(n.Refusal): self.wait(self.bytes())

    def test_peer_close_before_ack(self):
        self.b.shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(n.Refusal,'closed'): self.wait()

    def test_wrong_sequence(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes(sequence=6))

    def test_wrong_process(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes(pid=1235))

    def test_wrong_generation(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes(generation=2))

    def test_wrong_kind(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes(kind=4))

    def test_old_wire_version(self):
        raw=bytearray(self.bytes());raw[4]=1
        with self.assertRaises(n.Refusal): self.wait(bytes(raw))

    def test_wrong_magic(self):
        raw=b'FAKE'+self.bytes()[4:]
        with self.assertRaises(n.Refusal): self.wait(raw)

    def test_short_ack(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes()[:-1])

    def test_trailing_byte_ack(self):
        with self.assertRaises(n.Refusal): self.wait(self.bytes()+b'x')

    def test_large_ack_truncation(self):
        with self.assertRaisesRegex(n.Refusal,'truncation'): self.wait(self.bytes()+b'x'*5000)

    def test_invalid_decision_wire(self):
        raw=bytearray(self.bytes());raw[24]=2
        with self.assertRaises(n.Refusal): self.wait(bytes(raw))

    def test_boolean_event_identity_refused(self):
        wrong=dict(self.event,kind=True)
        with self.assertRaises(n.Refusal): n.inspect_ack(self.bytes(),wrong)

    def test_boolean_decision_refused(self):
        with self.assertRaises(n.Refusal): n.fixture_ack_bytes(self.event,True)

    def test_event_generation_cap(self):
        with self.assertRaises(n.Refusal): n.event_identity(self.event_packet(gen=257))

    def test_event_sequence_cap(self):
        with self.assertRaises(n.Refusal): n.event_identity(self.event_packet(sequence=4096))

    def test_new_event_version_required(self):
        with self.assertRaises(n.Refusal): n.event_identity(self.event_packet(version=1))

    def test_exact_event_identity(self):
        self.assertEqual(n.event_identity(self.event_packet()),self.event)

    def test_event_trailing_payload_refused(self):
        with self.assertRaises(n.Refusal): n.event_identity(self.event_packet()+b'x')

    def test_ack_rights_descriptor_is_closed(self):
        with tempfile.TemporaryFile() as f:
            before=len(os.listdir('/proc/self/fd'))
            self.b.sendmsg([self.bytes()],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[f.fileno()]))])
            with self.assertRaises(n.Refusal): self.wait()
            self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_ack_ancillary_truncation_is_closed(self):
        with tempfile.TemporaryFile() as f:
            before=len(os.listdir('/proc/self/fd'))
            self.b.sendmsg([self.bytes()],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[f.fileno()]*20))])
            with self.assertRaises(n.Refusal): self.wait()
            self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_stream_ack_channel_refused(self):
        a,b=socket.socketpair()
        try:
            with self.assertRaises(n.Refusal): self.barrier.wait_fixture(a,self.event,0.01)
        finally: a.close();b.close()

    def flagged_channel(self,extra):
        channel=self.a
        class ManufacturedFlags:
            def fileno(_): return channel.fileno()
            def getsockopt(_,level,option): return channel.getsockopt(level,option)
            def recvmsg(_,size,ancillary,flags):
                raw,records,actual,address=channel.recvmsg(size,ancillary,flags)
                return raw,records,actual|extra,address
        return ManufacturedFlags()

    def test_normal_record_boundary_flag_allowed(self):
        self.b.sendmsg([self.bytes()])
        receipt=self.barrier.wait_fixture(self.flagged_channel(socket.MSG_EOR),self.event,0.2)
        self.assertFalse(receipt['native_or_science_release_authority'])

    def test_unknown_receive_flag_refused(self):
        self.b.sendmsg([self.bytes()])
        with self.assertRaisesRegex(n.Refusal,'unknown-flag'):
            self.barrier.wait_fixture(self.flagged_channel(socket.MSG_OOB),self.event,0.2)

    def test_source_timeout_cannot_be_unbounded(self):
        with self.assertRaises(n.Refusal): self.barrier.wait_fixture(self.a,self.event,3)

    def test_closed_success_cannot_be_reissued(self):
        self.wait(self.bytes())
        with self.assertRaises(n.Refusal): self.wait(self.bytes())

    def test_production_release_always_refuses_even_fixture_success(self):
        receipt=self.wait(self.bytes())
        with self.assertRaisesRegex(n.Refusal,'positive release closed'): n.release(self.a,self.event,receipt)

    def test_public_negative_ack(self):
        n.reject(self.b,self.event)
        with self.assertRaisesRegex(n.Refusal,'observer rejection'): self.wait()

    def test_dispatch_always_refuses(self):
        with self.assertRaises(n.Refusal): n.dispatch()


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AckTests))
    folder=Path(__file__).parent;number=1
    while (folder/('ACK_FIXTURES-%d.json'%number)).exists(): number+=1
    with (folder/('ACK_FIXTURES-%d.json'%number)).open('x') as out:
        json.dump({'schema':'radio-N-manufactured-ack-source-fixtures-v1','tests':EVIDENCE,'native_collector_executions':0,
                   'observer_authenticated':False,'native_or_science_authority':False},out,sort_keys=True);out.write('\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
