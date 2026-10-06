"""Real local descriptor transport, invented loader frames; no native audit run."""
import array
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('receiver',Path(__file__).with_name('receiver.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
EVIDENCE=[]


class DescriptorTransport(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.main=self.root/'main.fixture';self.main.write_bytes(b'never executed main bytes')
        self.transient=self.root/'transient.fixture';self.transient.write_bytes(b'never loaded object bytes')
        self.pid=os.getpid()
        self.files={str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in (self.main,self.transient)}
        self.rx=r.Receiver(self.pid,str(self.main),self.files)
        self.a,self.b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)

    def tearDown(self):
        EVIDENCE.append({'test':self.id(),'raw_events_hex':list(self.rx.raw),'refusals':list(self.rx.failures),
                         'read_bytes':self.rx.read_bytes,'phase_before_cleanup':self.rx.phase,
                         'native_event_origin':False,'science_identity':None,
                         'observed_fixture_generations':[{k:v for k,v in row.items() if k!='fd'} for row in self.rx.objects.values()]})
        self.rx.close_retained_descriptors();self.a.close();self.b.close();self.temp.cleanup()

    def frame(self,kind,gen=0,path=None,name=None,flags=0,**changes):
        e=dict(magic=b'RLA1',version=1,kind=kind,sequence=self.rx.sequence,pid=self.pid,
               generation=gen,namespace=0,load_base=0,device=0,inode=0,bytes=0,mode=0,
               flags=flags,mtime_ns=0,ctime_ns=0,monotonic_ns=self.rx.sequence+1,name_len=0,path_len=0)
        spelling=b'';resolved=b''
        if path is not None:
            e.update(r.identity(path.stat()));resolved=str(path).encode()
            spelling=(str(path) if name is None else name).encode()
        e.update(name_len=len(spelling),path_len=len(resolved));e.update(changes)
        return r.HEADER.pack(*e.values())+spelling+resolved

    def send(self,raw,fds=()):
        ancillary=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',fds))] if fds else []
        self.b.sendmsg([raw],ancillary);return self.rx.receive(self.a)

    def open(self,path,gen,name=None,**changes):
        fd=os.open(path,os.O_RDONLY)
        try: return self.send(self.frame(r.OPEN,gen,path,name,**changes),[fd])
        finally: os.close(fd)

    def startup(self):
        self.send(self.frame(r.HANDSHAKE,flags=2));self.open(self.main,1,name='')
        self.send(self.frame(r.PREINIT,1))

    def terminal(self):
        self.b.shutdown(socket.SHUT_WR);self.assertFalse(self.rx.receive(self.a))
        return self.rx.finish(self.pid,0)

    def test_actual_descriptor_survives_transient_unload_and_eof(self):
        self.startup();self.open(self.transient,2);self.send(self.frame(r.CLOSE,2))
        fd=self.rx.objects[2]['fd'];self.assertEqual(os.pread(fd,100,0),self.transient.read_bytes())
        receipt=self.terminal();self.assertEqual(receipt['transient_generations_retained'],1)
        self.assertFalse(receipt['collector_authentication']);self.assertFalse(receipt['mapped_inode_binding'])
        self.assertFalse(receipt['runtime_qualified']);self.assertFalse(receipt['native_or_science_authority'])

    def test_alias_is_bound_to_actual_descriptor_path(self):
        self.startup();alias=self.root/'alias';alias.symlink_to(self.transient)
        self.open(self.transient,2,name=str(alias));self.terminal()

    def test_descriptor_offset_not_consumed(self):
        self.send(self.frame(r.HANDSHAKE,flags=2));fd=os.open(self.main,os.O_RDONLY)
        try:
            os.lseek(fd,3,os.SEEK_SET);self.send(self.frame(r.OPEN,1,self.main,name=''),[fd])
            self.assertEqual(os.lseek(fd,0,os.SEEK_CUR),3)
        finally: os.close(fd)

    def test_descriptor_is_noninheritable(self):
        self.startup();self.assertFalse(os.get_inheritable(self.rx.objects[1]['fd']))

    def test_wrong_pid_poisoned(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2,pid=self.pid+1))
        self.assertTrue(self.rx.failures)
        with self.assertRaises(r.Refusal): self.rx.receive(self.a)

    def test_wrong_sequence(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2,sequence=1))

    def test_backward_clock(self):
        self.startup()
        with self.assertRaises(r.Refusal): self.send(self.frame(r.ACTIVITY,1,monotonic_ns=1))

    def test_wrong_version(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2,version=2))

    def test_changed_length(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2,path_len=1))

    def test_truncated_packet(self):
        with self.assertRaises(r.Refusal): self.send(b'RLA1')

    def test_extra_payload(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2)+b'extra')

    def test_descriptor_count_zero_on_open(self):
        self.send(self.frame(r.HANDSHAKE,flags=2))
        with self.assertRaises(r.Refusal): self.send(self.frame(r.OPEN,1,self.main,name=''))

    def test_descriptor_count_two_on_open_closed(self):
        self.send(self.frame(r.HANDSHAKE,flags=2));fd=os.open(self.main,os.O_RDONLY)
        before=len(os.listdir('/proc/self/fd'))
        try:
            with self.assertRaises(r.Refusal): self.send(self.frame(r.OPEN,1,self.main,name=''),[fd,fd])
            self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        finally: os.close(fd)

    def test_ancillary_truncation_no_fd_leak(self):
        fd=os.open(self.main,os.O_RDONLY);before=len(os.listdir('/proc/self/fd'))
        try:
            with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2),[fd]*20)
            self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        finally: os.close(fd)

    def test_descriptor_on_handshake_closed(self):
        fd=os.open(self.main,os.O_RDONLY);before=len(os.listdir('/proc/self/fd'))
        try:
            with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2),[fd])
            self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        finally: os.close(fd)

    def test_unknown_object(self):
        self.startup();del self.rx.expected[str(self.transient)]
        with self.assertRaises(r.Refusal): self.open(self.transient,2)

    def test_callback_inode_differs(self):
        self.startup()
        with self.assertRaises(r.Refusal): self.open(self.transient,2,inode=self.transient.stat().st_ino+1)

    def test_actual_descriptor_does_not_match_spelling(self):
        self.send(self.frame(r.HANDSHAKE,flags=2));fd=os.open(self.transient,os.O_RDONLY)
        try:
            with self.assertRaises(r.Refusal): self.send(self.frame(r.OPEN,1,self.main,name=''),[fd])
        finally: os.close(fd)

    def test_original_hash_differs(self):
        self.startup();self.rx.expected[str(self.transient)]['sha256']='0'*64
        with self.assertRaises(r.Refusal): self.open(self.transient,2)

    def test_file_mutation_before_terminal(self):
        self.startup();self.open(self.transient,2);self.transient.write_bytes(b'changed')
        self.b.shutdown(socket.SHUT_WR);self.rx.receive(self.a)
        with self.assertRaises(r.Refusal): self.rx.finish(self.pid,0)
        self.assertTrue(self.rx.poisoned);self.assertIn('terminal_refusal',self.rx.failures[-1])

    def test_read_cap_before_body(self):
        self.send(self.frame(r.HANDSHAKE,flags=2))
        with patch.object(r,'MAX_READ',1):
            with self.assertRaises(r.Refusal): self.open(self.main,1,name='')
        self.assertEqual(self.rx.read_bytes,0)

    def test_namespace_veto(self):
        self.send(self.frame(r.HANDSHAKE,flags=2))
        with self.assertRaises(r.Refusal): self.open(self.main,1,name='',namespace=1)

    def test_kernel_pseudo_object_veto(self):
        self.startup()
        with self.assertRaises(r.Refusal): self.open(self.transient,2,name='linux-vdso.so.1')

    def test_duplicate_generation(self):
        self.startup()
        with self.assertRaises(r.Refusal): self.open(self.transient,1)

    def test_double_close(self):
        self.startup();self.send(self.frame(r.CLOSE,1))
        with self.assertRaises(r.Refusal): self.send(self.frame(r.CLOSE,1))

    def test_early_close(self):
        self.send(self.frame(r.HANDSHAKE,flags=2));self.open(self.main,1,name='')
        with self.assertRaises(r.Refusal): self.send(self.frame(r.CLOSE,1))

    def test_eof_without_startup(self):
        self.b.shutdown(socket.SHUT_WR)
        with self.assertRaises(r.Refusal): self.rx.receive(self.a)

    def test_wrong_wait_pid(self):
        self.startup();self.b.shutdown(socket.SHUT_WR);self.rx.receive(self.a)
        with self.assertRaises(r.Refusal): self.rx.finish(self.pid+1,0)

    def test_failed_exit(self):
        self.startup();self.b.shutdown(socket.SHUT_WR);self.rx.receive(self.a)
        with self.assertRaises(r.Refusal): self.rx.finish(self.pid,1)

    def test_finish_cannot_be_reissued(self):
        self.startup();self.terminal()
        with self.assertRaises(r.Refusal): self.rx.finish(self.pid,0)

    def test_veto_is_retained(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.VETO,flags=3))
        self.assertIn('veto',self.rx.failures[-1]['reason'])

    def test_stream_socket_refused(self):
        a,b=socket.socketpair()
        try:
            with self.assertRaises(r.Refusal): self.rx.receive(a)
        finally: a.close();b.close()

    def test_raw_byte_cap(self):
        with patch.object(r,'MAX_RAW',1):
            with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2))

    def test_mixed_unknown_ancillary_closes_later_rights(self):
        class ManufacturedChannel:
            def getsockopt(_,level,option): return socket.SOCK_SEQPACKET
            def recvmsg(_,size,ancillary,flags):
                return b'RLA1',[(999,999,b'unsupported'),(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[duplicate]).tobytes())],0,None
        duplicate=os.open(self.main,os.O_RDONLY)
        with self.assertRaises(r.Refusal): self.rx.receive(ManufacturedChannel())
        with self.assertRaises(OSError): os.fstat(duplicate)

    def test_actual_packet_truncation(self):
        with self.assertRaises(r.Refusal): self.send(self.frame(r.HANDSHAKE,flags=2)+b'x'*5000)
        self.assertIn('truncated',self.rx.failures[-1]['reason'])

    def test_no_native_dispatch(self):
        with self.assertRaises(r.Refusal): r.dispatch()


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DescriptorTransport)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    # Per-test fabricated triggers/vetoes retained even on failure, with exclusive
    # filenames; they are ordinary local socket fixtures, not native evidence.
    number=1;folder=Path(__file__).parent
    while (folder/('TRANSPORT_FIXTURES-%d.json'%number)).exists(): number+=1
    with (folder/('TRANSPORT_FIXTURES-%d.json'%number)).open('x') as f:
        json.dump({'schema':'radio-L-manufactured-fd-transport-fixtures-v1','tests':EVIDENCE,
                   'native_callback_executions':0,'runtime_or_science_authority':False},f,sort_keys=True)
        f.write('\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
