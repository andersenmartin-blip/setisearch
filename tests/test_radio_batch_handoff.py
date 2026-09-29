import json
from pathlib import Path
import tempfile
import threading
import unittest
from radio_batch_handoff import FileRPC,publish,next_message,deliver_and_next,MAX_REQUEST

class BatchHandoffTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def reply(self,n,obj):
        (self.root/f'response{n:04d}.json.tmp').write_text(json.dumps(obj))
    def test_delivery_and_next_request_in_one_operation(self):
        self.reply(1,{'id':1,'ok':True,'result':{'a':1}})
        publish(self.root/'request0002.json',{'id':2,'method':'fetch','params':{}})
        self.assertEqual(deliver_and_next(self.root,1)['kind'],'request')
        self.assertTrue((self.root/'response0001.json').exists())
    def test_done_after_delivery(self):
        self.reply(1,{'id':1,'ok':True,'result':{}});publish(self.root/'done.json',{'status':'CLOSED'})
        self.assertEqual(deliver_and_next(self.root,1)['result']['status'],'CLOSED')
    def test_duplicate_delivery_rejected_without_overwrite(self):
        self.reply(1,{'id':1,'ok':True,'result':{}});(self.root/'response0001.json').write_bytes(b'old')
        with self.assertRaises(ValueError):deliver_and_next(self.root,1)
        self.assertEqual((self.root/'response0001.json').read_bytes(),b'old')
    def test_wrong_id_or_retry_frame_stops_before_rename(self):
        for obj in ({'id':2,'ok':True,'result':{}},{'id':1,'ok':False,'error':'x','automatic_retry':True}):
            self.reply(1,obj)
            with self.assertRaises(ValueError):deliver_and_next(self.root,1)
            self.assertFalse((self.root/'response0001.json').exists())
    def test_batch_request_above_old_cap_is_bounded_and_framed(self):
        publish(self.root/'request0001.json',{'id':1,'method':'create_tree','params':{'content':'a'*720000}})
        h=next_message(self.root,1);self.assertGreater(h['bytes'],600000);self.assertEqual(len(h['first']),48000)
    def test_oversize_or_partial_input_is_not_admitted(self):
        (self.root/'request0001.json').write_bytes(b'x'*(MAX_REQUEST+1))
        with self.assertRaises(ValueError):next_message(self.root,1)
    def test_real_waiting_worker_receives_error_and_finishes(self):
        rpc=FileRPC(self.root/'rpc');self.root=rpc.path
        outcome=[]
        def worker():
            try:rpc('fetch',{})
            except RuntimeError:outcome.append('STOPPED')
            publish(self.root/'done.json',{'status':'STOPPED'})
        t=threading.Thread(target=worker);t.start();next_message(self.root,1)
        self.reply(1,{'id':1,'ok':False,'error':'ambiguous','automatic_retry':False})
        self.assertEqual(deliver_and_next(self.root,1)['result']['status'],'STOPPED')
        t.join();self.assertEqual(outcome,['STOPPED']);self.assertEqual(rpc.sequence,1)

if __name__=='__main__':unittest.main()
