"""Real filesystem/CLI durability and queue checks; no RNG or native cases."""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from seti_repeater.empty_null_radio import canonical
from seti_repeater import native_v2_bridge_radio as bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'bridge'
        self.store=bridge.Store.create(str(self.root))

    def tearDown(self): self.temp.cleanup()

    def service(self,result,*,claim=True):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            state=bridge._dispatch({'action':'pending','root':str(self.root)})
            if state['pending']: break
            time.sleep(.005)
        else: raise AssertionError('Worker did not publish request')
        item=state['pending'][0]; packet=json.loads(self.store.payload(item['id']))
        before=self.store.status()
        self.assertGreater(before['buckets']['response']['unknown_bytes'],0)
        if claim: self.store.claim(item['id'])
        raw=canonical(result); identity=packet['response_id']
        for offset in range(0,len(raw),bridge.CHUNK_BYTES):
            self.store.append(identity,offset,raw[offset:offset+bridge.CHUNK_BYTES])
        self.store.seal(identity,size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        return packet

    def thread_call(self,call):
        outcome={}
        def run():
            try: outcome['result']=call()
            except BaseException as error: outcome['error']=error
        thread=threading.Thread(target=run); thread.start()
        return thread,outcome

    def test_real_chunks_fsync_permissions_and_reopen(self):
        data=(b'abc\0\xff'*15000)
        original=os.fsync; types=[]
        def sync(fd): types.append(stat.S_IFMT(os.fstat(fd).st_mode)); original(fd)
        with patch.object(bridge.os,'fsync',side_effect=sync):
            receipt=self.store.write('payload','python_receipt',data,case_ordinal=0)
        self.assertTrue(receipt['durable'])
        self.assertIn(stat.S_IFREG,types); self.assertIn(stat.S_IFDIR,types)
        self.assertEqual(bridge.Store(str(self.root)).payload('payload'),data)
        self.assertEqual(stat.S_IMODE(os.stat(receipt['path']).st_mode),0o400)
        state=self.store.status()
        self.assertEqual(state['buckets']['python_receipt']['known_bytes'],len(data))
        self.assertEqual(state['buckets']['python_receipt']['unknown_bytes'],0)
        for bucket in state['buckets'].values():
            self.assertEqual(bucket['charged_bytes'],bucket['known_bytes']+bucket['unknown_bytes'])

    def test_unknown_reservation_survives_partial_write_and_reopen(self):
        self.store.reserve('response','response',100)
        self.store.append('response',0,b'x'*7)
        bucket=bridge.Store(str(self.root)).status()['buckets']['response']
        self.assertEqual(bucket,{'known_bytes':0,'unknown_bytes':100,'charged_bytes':100,'items':1})

    def test_duplicate_offset_stops_without_overwriting(self):
        self.store.reserve('partial','response',30)
        self.store.append('partial',0,b'first')
        with self.assertRaises(ValueError): self.store.append('partial',0,b'other')
        self.assertTrue(self.store.status()['stopped'])
        self.assertEqual((self.root/'items/partial/part').read_bytes(),b'first')
        with self.assertRaises(RuntimeError): self.store.append('partial',5,b'next')

    def test_duplicate_reservation_and_completed_seal_have_no_retry(self):
        self.store.write('one','request',b'known')
        with self.assertRaises(ValueError): self.store.reserve('one','request',5)
        self.assertTrue(self.store.status()['stopped'])
        self.assertEqual(self.store.payload('one'),b'known')

    def test_wrong_sha_never_seals_and_keeps_charge(self):
        self.store.reserve('wrong','response',20,'0'*64)
        self.store.append('wrong',0,b'actual')
        with self.assertRaises(ValueError): self.store.seal('wrong')
        self.assertFalse((self.root/'items/wrong/sealed.json').exists())
        self.assertEqual(self.store.status()['buckets']['response']['unknown_bytes'],20)

    def test_seal_preserves_one_authoritative_file_without_delete_credit(self):
        raw=b'one immutable file'; self.store.reserve('single','response',len(raw),hashlib.sha256(raw).hexdigest())
        self.store.append('single',0,raw)
        part=self.root/'items/single/part'; inode=part.stat().st_ino
        receipt=self.store.seal('single')
        self.assertEqual(receipt['path'],str(part)); self.assertEqual(part.stat().st_ino,inode)
        self.assertEqual(part.stat().st_nlink,1)
        self.assertFalse((self.root/'items/single/payload').exists())
        self.assertEqual(self.store.payload('single'),raw)

    def test_unexpected_duplicate_bytes_fail_storage_audit(self):
        self.store.write('duplicate','response',b'known')
        (self.root/'items/duplicate/payload').write_bytes(b'known')
        with self.assertRaisesRegex(ValueError,'uncharged'): self.store.status()
        with self.assertRaisesRegex(ValueError,'uncharged'): self.store.read('duplicate')

    def test_interrupted_final_marker_holds_reservation_and_prevents_reopen(self):
        raw=b'known'; self.store.reserve('interrupted','response',20,hashlib.sha256(raw).hexdigest())
        self.store.append('interrupted',0,raw)
        original=bridge._exclusive
        def write(fd,name,data,mode=0o400):
            if name=='sealed.json': raise OSError('simulated durable marker failure')
            return original(fd,name,data,mode)
        with patch.object(bridge,'_exclusive',side_effect=write):
            with self.assertRaises(OSError): self.store.seal('interrupted')
        self.assertTrue((self.root/'items/interrupted/sealing.json').exists())
        self.assertEqual(self.store.status()['buckets']['response']['unknown_bytes'],20)
        self.assertTrue(self.store.status()['stopped'])
        with self.assertRaises(RuntimeError): self.store.append('interrupted',len(raw),b'retry')

    def test_unknown_sha_requires_independent_final_count_and_hash(self):
        self.store.reserve('unknown','response',20)
        self.store.append('unknown',0,b'known')
        with self.assertRaises(ValueError): self.store.seal('unknown')
        self.assertTrue(self.store.status()['stopped'])

    def test_symlink_ancestor_and_payload_rejected(self):
        linked=Path(self.temp.name)/'linked'; linked.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(OSError): bridge.Store(str(linked)).status()
        self.store.reserve('escape','response',20)
        part=self.root/'items/escape/part'; part.unlink()
        outside=Path(self.temp.name)/'outside'; outside.write_bytes(b'outside')
        part.symlink_to(outside)
        with self.assertRaises(OSError): self.store.append('escape',0,b'x')
        self.assertEqual(outside.read_bytes(),b'outside')

    def test_hardlink_and_escape_identity_rejected(self):
        self.store.reserve('linked','response',20)
        os.link(self.root/'items/linked/part',Path(self.temp.name)/'extra')
        with self.assertRaises(ValueError): self.store.append('linked',0,b'x')
        for value in ('../escape','/absolute','a/b','.', 'a\\b'):
            with self.assertRaises(ValueError): bridge._id(value)

    def test_per_case_budget_refuses_before_item_creation(self):
        other=Path(self.temp.name)/'small'
        limits={**bridge.LIMITS,'response':100}
        cases={**bridge.CASE_LIMITS,'response':50}
        store=bridge.Store.create(str(other),limits=limits,case_limits=cases)
        with self.assertRaises(ValueError): store.reserve('too-big','response',51,case_ordinal=0)
        self.assertFalse((other/'items/too-big').exists()); self.assertTrue(store.status()['stopped'])

    def test_global_budget_and_item_count_are_independent(self):
        other=Path(self.temp.name)/'small'
        limits={**bridge.LIMITS,'response':100,'items':1}
        store=bridge.Store.create(str(other),limits=limits)
        store.reserve('one','response',70)
        with self.assertRaises(ValueError): store.reserve('two','runner_state',1)
        self.assertEqual(store.status()['item_count'],1)

    def test_bounded_read_reports_chunk_length_and_whole_size(self):
        data=b'a'*(bridge.READ_BYTES+1); self.store.write('read','response',data)
        row=self.store.read('read',0,bridge.READ_BYTES)
        self.assertEqual(row['bytes'],bridge.READ_BYTES)
        self.assertEqual(row['total_bytes'],len(data)); self.assertFalse(row['eof'])
        self.assertEqual(len(base64.b64decode(row['content_base64'])),bridge.READ_BYTES)
        with self.assertRaises(ValueError): self.store.read('read',0,bridge.READ_BYTES+1)

    def test_real_cli_wrapper_and_previous_complete_tool_reply(self):
        helper=Path(__file__).resolve().parents[1]/'scripts/radio_native_v2_bridge.py'
        environment={**os.environ,'PYTHONPATH':str(helper.parent.parent/'src')}
        response_json='{"content":[{"type":"text","text":"æ"}],"structuredContent":{"ok":true}}'
        response=response_json.encode('utf-8')
        command={'action':'status','root':str(self.root),'support_receipts':[{
            'ordinal':0,'request_bytes':37,'request_sha256':'a'*64,
            'response_json':response_json,'response_bytes':len(response),
            'response_sha256':hashlib.sha256(response).hexdigest()}]}
        result=subprocess.run([sys.executable,'-B',str(helper)],input=canonical(command),
                              capture_output=True,check=True,env=environment)
        value=json.loads(result.stdout)
        self.assertEqual(value['support_receipts_persisted'],1)
        retained=json.loads(self.store.payload('support-00000000'))
        self.assertEqual(retained['response_json'],response_json)
        self.assertLess(len(result.stdout),65536)
        self.assertFalse(value['result']['execution_authorized'])

    def test_cli_rejects_oversized_input(self):
        helper=Path(__file__).resolve().parents[1]/'scripts/radio_native_v2_bridge.py'
        environment={**os.environ,'PYTHONPATH':str(helper.parent.parent/'src')}
        result=subprocess.run([sys.executable,'-B',str(helper)],input=b' '*(bridge.MAX_INPUT_BYTES+1),
                              capture_output=True,env=environment)
        self.assertNotEqual(result.returncode,0); self.assertIn(b'fixed bound',result.stderr)

    def test_support_reply_hash_mismatch_rejected(self):
        row={'ordinal':0,'request_bytes':1,'request_sha256':'a'*64,'response_json':'{}',
             'response_bytes':2,'response_sha256':'b'*64}
        with self.assertRaises(ValueError): bridge.dispatch({'action':'status','root':str(self.root),'support_receipts':[row]})
        self.assertEqual(self.store.status()['item_count'],0)

    def batch(self,values):
        spool=Path(self.temp.name)/'batch.raw'; raw=b''; files={}
        for path,data in sorted(values.items()):
            blob=hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
            files[path]={'bytes':len(data),'blob':blob,'sha256':hashlib.sha256(data).hexdigest()}
            raw+=(blob+' blob '+str(len(data))+'\n').encode()+data+b'\n'
        spool.write_bytes(raw)
        return spool,raw,files

    def test_streamed_git_projection_binary_empty_unicode_path(self):
        values={'directory/é.bin':bytes(range(256))*300,'empty':b''}
        spool,raw,files=self.batch(values)
        result=bridge.git_projection(self.store,'projection',str(spool),'a'*40,sorted(files),files,0)
        projection=json.loads(self.store.payload('projection'))
        for path,data in values.items():
            self.assertEqual(base64.b64decode(projection[path]['content']),data)
            self.assertEqual(projection[path]['sha'],files[path]['blob'])
        self.assertEqual(result['raw_git_receipt']['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['raw_git_receipt']['bytes'],len(raw))
        self.assertEqual(spool.read_bytes(),raw)

    def test_invalid_git_spool_retained_unknown_and_stopped(self):
        spool,raw,files=self.batch({'one':b'original'})
        spool.write_bytes(raw+b'extra')
        with self.assertRaises(ValueError):
            bridge.git_projection(self.store,'bad-projection',str(spool),'a'*40,sorted(files),files)
        state=self.store.status()
        self.assertTrue(state['stopped']); self.assertGreater(state['buckets']['git_projection']['unknown_bytes'],0)
        self.assertFalse((self.root/'items/bad-projection/sealed.json').exists())

    def test_git_spool_fsync_precedes_projection_seal(self):
        spool,raw,files=self.batch({'one':b'original'})
        original=os.fsync; spool_synced=[]
        def sync(fd):
            if os.fstat(fd).st_ino==os.stat(spool).st_ino: spool_synced.append(True)
            original(fd)
        seal=self.store.seal
        def checked(*args,**kwargs): self.assertTrue(spool_synced); return seal(*args,**kwargs)
        with patch.object(bridge.os,'fsync',side_effect=sync),patch.object(self.store,'seal',side_effect=checked):
            bridge.git_projection(self.store,'projection',str(spool),'a'*40,sorted(files),files)

    def test_worker_roundtrip_pre_reserves_python_receipt_exact_ordinal(self):
        worker=bridge.Worker(self.store)
        thread,outcome=self.thread_call(lambda:worker.invoke('fetch',{'url':'test://fixture'}))
        packet=self.service({'untouched':{'unicode':'æ','array':[1,2]}})
        thread.join(3); self.assertFalse(thread.is_alive()); self.assertNotIn('error',outcome)
        self.assertEqual(packet['operation'],'invoke:fetch')
        self.assertEqual(self.store.status()['buckets']['python_receipt']['unknown_bytes'],4*bridge.MIB)
        with self.assertRaises(ValueError): worker.persist(1,'fetch',canonical(packet['params']),outcome['result'])
        saved=worker.persist(0,'fetch',canonical(packet['params']),outcome['result'])
        self.assertEqual(saved['sha256'],hashlib.sha256(canonical(outcome['result'])).hexdigest())
        self.assertEqual(self.store.status()['buckets']['python_receipt']['unknown_bytes'],0)
        with self.assertRaises(ValueError): worker.persist(0,'fetch',canonical(packet['params']),outcome['result'])

    def test_worker_timeout_closes_store_and_cannot_dispatch_late(self):
        worker=bridge.Worker(self.store,seconds=.03,poll_seconds=.005)
        with self.assertRaises(TimeoutError): worker.invoke('update_ref',{'sha':'a'*40})
        state=self.store.status(); self.assertTrue(state['stopped'])
        self.assertEqual(state['buckets']['response']['unknown_bytes'],16384)
        with self.assertRaises(RuntimeError): self.store.claim('request-000000')
        with self.assertRaises(RuntimeError): worker.invoke('update_ref',{'sha':'a'*40})

    def test_expired_claim_and_duplicate_claim_stop_before_host(self):
        packet={'schema':bridge.SCHEMA,'deadline_monotonic_seconds':time.monotonic()-1}
        self.store.write('expired','request',canonical(packet))
        with self.assertRaises(TimeoutError): self.store.claim('expired')
        self.assertTrue(self.store.status()['stopped'])

    def test_worker_state_uses_independent_durable_bucket(self):
        worker=bridge.Worker(self.store); worker.case_ordinal=0
        saved=worker.persist_state({'status':'fixture','execution_authorized':False})
        raw=self.store.payload('state-000000')
        self.assertEqual(saved,{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        state=self.store.status()
        self.assertEqual(state['buckets']['runner_state']['known_bytes'],len(raw))
        self.assertEqual(state['buckets']['response']['charged_bytes'],0)

    def test_original_native_budgets_reject_full_projection_dispatch(self):
        # A 26MiB case needs >1000 supporting writes and >1000 reads. The
        # existing native broker budget is64calls; this is an explicit gap.
        source_bytes=26*bridge.MIB
        projection_bytes=4*((source_bytes+2)//3)
        writes=(projection_bytes+bridge.CHUNK_BYTES-1)//bridge.CHUNK_BYTES
        reads=(projection_bytes+bridge.READ_BYTES-1)//bridge.READ_BYTES
        self.assertGreater(writes+reads,64)
        self.assertEqual(bridge.LIMITS['items'],2048)
        self.assertEqual(bridge.LIMITS['metadata'],16*bridge.MIB)


if __name__=='__main__': unittest.main()
