import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from radio_lossless_handoff import publish,next_message,FileRPC

class HandoffTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_request_and_done_are_distinct(self):
        publish(self.root/'request0001.json',{'id':1,'method':'fetch','params':{}})
        self.assertEqual(next_message(self.root,1)['kind'],'request')
        publish(self.root/'done.json',{'status':'STOPPED'})
        self.assertEqual(next_message(self.root,2)['result']['status'],'STOPPED')
    def test_duplicate_sequence_not_overwritten(self):
        publish(self.root/'done.json',{'a':1})
        with self.assertRaises(ValueError):publish(self.root/'done.json',{'a':2})
        self.assertEqual(json.loads((self.root/'done.json').read_bytes()),{'a':1})
    def test_partial_pending_request_never_admitted(self):
        (self.root/'request0001.json.pending').write_bytes(b'{')
        with self.assertRaises(TimeoutError):next_message(self.root,1,timeout=.02)
    def test_wrong_sequence_and_noncanonical_request_rejected(self):
        (self.root/'request0001.json').write_text('{"id":2}')
        with self.assertRaises(ValueError):next_message(self.root,1)
    def test_response_error_is_not_retried(self):
        rpc=FileRPC(self.root/'rpc')
        def answer():
            next_message(rpc.path,1);publish(rpc.path/'response0001.json',{'id':1,'ok':False,'error':'ambiguous'})
        t=threading.Thread(target=answer);t.start()
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):rpc('fetch',{})
        t.join();self.assertEqual(rpc.sequence,1)
    def test_atomic_rpc_returns_correct_frame(self):
        rpc=FileRPC(self.root/'rpc')
        def answer():
            next_message(rpc.path,1);publish(rpc.path/'response0001.json',{'id':1,'ok':True,'result':{'sha':'fixed'}})
        t=threading.Thread(target=answer);t.start();self.assertEqual(rpc('fetch',{}),{'sha':'fixed'});t.join()

if __name__=='__main__':unittest.main()
