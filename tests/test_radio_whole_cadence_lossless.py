"""New atomic lossless journal risks; all remotes here are test doubles."""
import base64
import copy
import unittest
from unittest.mock import patch
from seti_repeater import whole_cadence_lossless_radio as r
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_remote import GitDouble

def manifest():
    return {'schema':r.SCHEMA,'mode':'ENGINEERING_ONLY','namespace':r.PREFIX,
        'execution_binding_sha256':digest('lossless-test-freeze'),'recipe_sha256':digest('lossless-test-recipe'),
        'cases':[{'ordinal':i,'case_identity':digest(['lossless-unit-only',i]),'milliseconds':(300000,120000)[i],
            'physical_bytes':(1048576,256)[i],'failure_bytes':8192,
            'required_artifacts':(['witness.json','payload.bin'],['capacity_probe.bin'])[i]} for i in range(2)]}

class LosslessTests(unittest.TestCase):
    def setUp(self):
        self.m=manifest();self.tick=0.;self.git=GitDouble.__new__(GitDouble)
        self.git.blobs={};self.git.trees={};self.git.flat={};self.git.commits={};self.git.calls=[];self.git.hook=None
        self.git.head=self.git.commit(None,self.git.tree({r.PREFIX+'/ledger.json':self.git.blob(canonical(r.genesis(self.m))),
            'untouched.txt':self.git.blob(b'preserved')}))
        self.client=r.Client(self.git.invoke,clock=lambda:self.tick);self.store=self.fresh()

    def fresh(self):return r.Store(self.client,self.m,execution_verifier=lambda m:None)
    def payloads(self):return {'witness.json':b'{}','payload.bin':bytes(range(256))*2048+b'tail\x80\xff'}
    def complete(self):
        doc,_,_=self.store.consume(0)
        return self.store.seal(doc,self.payloads(),'archived','fixed unit witness',1)

    def test_atomic_two_artifacts_and_separate_bounded_failure(self):
        doc=self.complete();self.assertEqual(len(self.store.receipts),2)
        self.assertEqual(len(self.store.receipts[-1]['files']),7)
        claimed,c,_=self.store.consume(1)
        with self.assertRaisesRegex(ValueError,'physical cap'):r.pack(c,{'capacity_probe.bin':b'x'*1024},'archived')
        done=self.store.seal(claimed,{'failure.json':b'{"failure":"expected capacity"}'},'failed','expected capacity',1)
        fresh=self.fresh();remote,_=fresh.read();restored=fresh.read_archives(remote,fresh.last_head)
        self.assertEqual(remote,done);self.assertEqual(len(restored),3)
        self.assertEqual(restored[c['case_identity']+'/failure.json'],b'{"failure":"expected capacity"}')
        self.assertEqual([x['status'] for x in r.replay(done)['cases']],['archived','failed'])
        self.assertEqual(len(self.store.receipts),4)
        self.assertTrue(all(p['force'] is False for m,p in self.git.calls if m=='update_ref'))

    def test_new_process_cannot_seal_consumed_case(self):
        doc,_,_=self.store.consume(0);n=self.client.calls
        with self.assertRaisesRegex(ValueError,'process-local'):self.fresh().seal(doc,self.payloads(),'archived','',1)
        self.assertEqual(self.client.calls,n)

    def test_incomplete_case_cannot_advance(self):
        self.store.consume(0)
        with self.assertRaisesRegex(ValueError,'incomplete'):self.fresh().consume(1)

    def test_closed_case_cannot_reconsume(self):
        self.complete()
        with self.assertRaisesRegex(ValueError,'already consumed'):self.store.consume(0)

    def test_fresh_process_cannot_continue_after_archival_without_timing(self):
        self.complete();n=self.client.calls
        with self.assertRaisesRegex(ValueError,'finalization incomplete'):self.fresh().consume(1)
        self.assertEqual(n,self.client.calls)

    def test_exact_physical_history_counts_every_ledger_version(self):
        doc=self.complete();state=r.replay(doc)
        expected=sum(len(canonical({'manifest':self.m,'events':doc['events'][:i]})) for i in range(3))
        self.assertEqual(state['ledger_history_bytes'],expected)
        parts=sum(a['physical_bytes'] for a in state['cases'][0]['artifacts'].values())
        self.assertEqual(state['used_physical_bytes'],parts+expected)
        self.assertGreater(parts,sum(map(len,self.payloads().values())))

    def test_ledger_history_reserve_enforced(self):
        with patch.object(r,'MAX_LEDGER_HISTORY',1000):
            with self.assertRaisesRegex(ValueError,'history cap'):self.store.consume(0)

    def test_no_normal_quota_borrowing_failure_reserve(self):
        c=self.m['cases'][1]
        with self.assertRaises(ValueError):r.pack(c,{'capacity_probe.bin':b'a'*1024},'archived')
        parts,records=r.pack(c,{'failure.json':b'{}'},'failed')
        self.assertGreater(sum(map(len,parts.values())),c['physical_bytes'])
        self.assertLess(sum(map(len,parts.values())),c['failure_bytes'])

    def test_failure_receipt_cannot_exceed_reserve(self):
        with self.assertRaises(ValueError):r.pack(self.m['cases'][1],{'failure.json':b'a'*8192},'failed')

    def test_changed_checkpoint_does_not_issue_calls(self):
        doc,_,_=self.store.consume(0);bad=copy.deepcopy(doc);bad['events']=[];n=self.client.calls
        with self.assertRaisesRegex(ValueError,'capability'):self.store.seal(bad,self.payloads(),'archived','',1)
        self.assertEqual(self.client.calls,n)

    def test_changed_remote_checkpoint_rejected(self):
        doc,_,_=self.store.consume(0)
        changed=copy.deepcopy(doc);changed['events'][0]['event']['nonce']='00000000-0000-4000-8000-000000000001'
        changed['events'][0]['sha256']=digest({k:v for k,v in changed['events'][0].items() if k!='sha256'})
        flat=dict(self.git.flat[self.git.commits[self.git.head]['tree']['sha']]);flat[r.PREFIX+'/ledger.json']=self.git.blob(canonical(changed))
        self.git.head=self.git.commit(self.git.head,self.git.tree(flat))
        with self.assertRaisesRegex(ValueError,'checkpoint changed'):self.store.seal(doc,self.payloads(),'archived','',1)

    def test_ambiguous_atomic_seal_preserves_all_files_and_never_retries(self):
        doc,_,_=self.store.consume(0)
        def hook(m,p,result):
            if m=='update_ref':raise OSError('lost after landed atomic seal')
            return result
        self.git.hook=hook
        with self.assertRaises(r.Stopped):self.store.seal(doc,self.payloads(),'archived','',1)
        files=self.git.flat[self.git.commits[self.git.head]['tree']['sha']]
        remote=__import__('json').loads(self.git.blobs[files[r.PREFIX+'/ledger.json']])
        self.assertEqual(r.replay(remote)['cases'][0]['status'],'archived')
        self.assertEqual(len([p for p in files if '/artifacts/' in p]),6)
        n=self.client.calls
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(n,self.client.calls)

    def test_branch_race_prevents_seal_ref_update(self):
        doc,_,_=self.store.consume(0)
        def hook(m,p,result):
            if m=='create_commit':self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'advanced'):self.store.seal(doc,self.payloads(),'archived','',1)
        self.assertEqual(sum(m=='update_ref' for m,p in self.git.calls),1)

    def test_existing_artifact_protected_before_blob_upload(self):
        self.complete();path=next(p for p in self.store.receipts[-1]['files'] if '/artifacts/' in p);n=self.client.calls
        with self.assertRaisesRegex(ValueError,'overwrite'):self.store._atomic(self.git.head,{path:b'changed'})
        self.assertFalse(any(m=='create_blob' for m,p in self.git.calls[n:]))

    def test_symlink_and_executable_leaf_and_ancestor_protected(self):
        for mode in ('100755','120000'):
            self.store._commit=lambda h:{'tree':'a'*40}
            self.store._tree=lambda h:{'x':{'mode':mode,'type':'blob','sha':'b'*40}}
            with self.assertRaisesRegex(ValueError,'overwrite'):self.store._assert_absent('0'*40,'x')
            with self.assertRaisesRegex(ValueError,'ancestor'):self.store._assert_absent('0'*40,'x/y')

    def test_ascii_response_corruption_stops(self):
        doc=self.complete();fresh=self.fresh();remote,_=fresh.read()
        def hook(m,p,result):
            if m=='fetch_file' and p['path'].endswith('chunk0002.b64'):result['content']=base64.b64encode(b'corrupt').decode()
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'content hash'):fresh.read_archives(remote,fresh.last_head)

    def test_missing_envelope_part_stops(self):
        self.complete();fresh=self.fresh();remote,_=fresh.read()
        path=next(p for p in self.store.receipts[-1]['files'] if p.endswith('chunk0002.b64'))
        del self.git.blobs[self.store.receipts[-1]['files'][path]]
        with self.assertRaises(r.Stopped):fresh.read_archives(remote,fresh.last_head)

    def test_consume_latency_charged_before_work(self):
        def hook(m,p,result):
            if m=='update_ref':self.tick+=301
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(r.Stopped,'end-to-end'):self.store.consume(0)
        self.assertTrue(self.store.stopped)

    def test_seal_readback_latency_blocks_following_case(self):
        doc,_,_=self.store.consume(0)
        def hook(m,p,result):
            if m=='update_ref':self.tick+=301
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(r.Stopped,'end-to-end'):self.store.seal(doc,self.payloads(),'archived','',1)
        n=self.client.calls
        with self.assertRaises((r.Stopped,ValueError)):self.store.consume(1)
        self.assertEqual(n,self.client.calls)

    def test_manifest_rejects_science_bool_quota_and_unknown_fields(self):
        for key,value in (('mode','scientific'),('unknown',1)):
            bad=copy.deepcopy(self.m);bad[key]=value
            with self.assertRaises(ValueError):r.validate_manifest(bad)
        bad=copy.deepcopy(self.m);bad['cases'][0]['ordinal']=False
        with self.assertRaises(ValueError):r.validate_manifest(bad)

    def test_unknown_outcome_cannot_be_failure(self):
        with self.assertRaises(ValueError):r.pack(self.m['cases'][1],{'failure.json':b'{}'},'EMPTY')

    def test_physical_receipt_tamper_rejected(self):
        doc=self.complete();row=doc['events'][-1];row['event']['artifacts']['payload.bin']['physical_bytes']-=1
        row['sha256']=digest({k:v for k,v in row.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'Physical artifact'):r.replay(doc)

    def test_transport_records_elapsed_and_closed_quota(self):
        self.tick=12.;self.store.read()
        self.assertEqual(self.client.events[0]['started_seconds'],12.)
        self.assertEqual(self.client.events[0]['ended_seconds'],12.)
        self.client.calls=r.LIMITS['calls'];n=len(self.git.calls)
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(len(self.git.calls),n)

if __name__=='__main__':unittest.main()
