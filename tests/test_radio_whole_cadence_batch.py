"""New risks from content batching and locally predicted immutable tree closure."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from seti_repeater import whole_cadence_batch_radio as r
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_remote import GitDouble

class ContentDouble(GitDouble):
    def __init__(self,m):
        self.blobs={};self.trees={};self.flat={};self.commits={};self.calls=[];self.hook=None;self.actual=[]
        self.head=self.commit(None,self.tree({r.PREFIX+'/ledger.json':self.blob(canonical(r.genesis(m))),
            'untouched.txt':self.blob(b'preserved'),'z/a.txt':self.blob(b'z')}))
    def invoke(self,method,p):
        self.actual.append((method,copy.deepcopy(p)))
        if method=='create_tree':
            p=copy.deepcopy(p)
            for e in p['tree_elements']:e['sha']=self.blob(e.pop('content').encode('ascii'))
        return super().invoke(method,p)

def manifest():
    return {'schema':r.SCHEMA,'mode':'ENGINEERING_ONLY','namespace':r.PREFIX,
        'execution_binding_sha256':digest('batch-unit-freeze'),'recipe_sha256':digest('batch-unit-recipe'),
        'cases':[{'ordinal':0,'case_identity':digest('batch-unit-case'),'milliseconds':80000,
            'physical_bytes':1048576,'failure_bytes':8192,'required_artifacts':['witness.json','payload.bin']}]}

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.m=manifest();self.git=ContentDouble(self.m);self.tick=0
        self.client=r.Client(self.git.invoke,clock=lambda:self.tick);self.store=self.fresh()
    def fresh(self):return r.Store(self.client,self.m,execution_verifier=lambda m:None)
    def payloads(self):return {'witness.json':b'{}','payload.bin':bytes(range(256))*1024+b'\xff\x00tail'}
    def complete(self):
        doc,_,_=self.store.consume(0)
        return self.store.seal(doc,self.payloads(),'archived','fixed unit fixture',1)
    def test_two_commits_no_blob_uploads_exact_external_bytes(self):
        doc=self.complete();fresh=self.fresh();remote,_=fresh.read();data=fresh.read_archives(remote,fresh.last_head)
        self.assertEqual(doc,remote)
        self.assertEqual(data,{self.m['cases'][0]['case_identity']+'/'+k:v for k,v in self.payloads().items()})
        self.assertEqual([m for m,p in self.git.actual].count('create_tree'),2)
        self.assertNotIn('create_blob',[m for m,p in self.git.actual])
        self.assertEqual(len(self.store.receipts),2)
        for method,p in self.git.actual:
            if method=='create_tree':self.assertTrue(all('content' in e and 'sha' not in e for e in p['tree_elements']))
    def test_git_mktree_is_independent_hash_oracle(self):
        self.complete()
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['git','init','-q',directory],check=True)
            for sha,entries in self.store.candidate_trees.items():
                data=b''.join((v['mode']+' '+v['type']+' '+v['sha']+'\t'+n).encode()+b'\0' for n,v in reversed(list(entries.items())))
                actual=subprocess.check_output(['git','mktree','-z','--missing'],input=data,cwd=directory).decode().strip()
                self.assertEqual(actual,sha)
    def test_server_tree_differs_stops_before_commit(self):
        def hook(method,p,result):
            if method=='create_tree':
                flat=dict(self.git.flat[result['sha']]);flat['untouched.txt']=self.git.blob(b'changed')
                return {'sha':self.git.tree(flat)}
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'exact locally computed'):self.store.consume(0)
        self.assertNotIn('create_commit',[m for m,p in self.git.actual]);self.assertTrue(self.store.stopped)
    def test_leaf_directory_collision_rejected(self):
        self.store.candidate_trees={}
        with self.assertRaisesRegex(ValueError,'collision'):self.store._expected_tree(None,{'a':'a'*40,'a/b':'b'*40})
    def test_mode_change_and_nonordinary_ancestor_rejected(self):
        for mode in ('100755','120000'):
            self.store.candidate_trees={};self.store._tree=lambda sha:{'a':{'mode':mode,'type':'blob','sha':'a'*40}}
            with self.assertRaisesRegex(ValueError,'leaf mode'):self.store._expected_tree('b'*40,{'a':'c'*40})
            with self.assertRaisesRegex(ValueError,'Nonordinary ancestor'):self.store._expected_tree('b'*40,{'a/b':'c'*40})
    def test_existing_artifact_cannot_overwrite(self):
        self.complete();path=next(p for p in self.store.receipts[-1]['files'] if '/artifacts/' in p)
        n=len(self.git.actual)
        with self.assertRaisesRegex(ValueError,'overwrite'):self.store._atomic(self.git.head,{path:b'new'})
        self.assertFalse(any(m=='create_tree' for m,p in self.git.actual[n:]))
    def test_content_guard_rejects_sha_nonascii_delete_and_duplicates(self):
        e={'path':r.PREFIX+'/x','mode':'100644','type':'blob','content':'a'}
        bads=[{**e,'sha':'a'*40},{**e,'content':'ø'},{**e,'content':None},{**e,'path':'elsewhere'},{**e,'mode':'120000'}]
        for bad in bads:
            with self.assertRaises(ValueError):self.client.call('create_tree',repository_full_name=r.REPO,base_tree_sha='a'*40,tree_elements=[bad])
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.client.call('create_tree',repository_full_name=r.REPO,base_tree_sha='a'*40,tree_elements=[e,e])
        self.assertEqual(self.git.actual,[])
    def test_content_request_cap_before_remote(self):
        e={'path':r.PREFIX+'/x','mode':'100644','type':'blob','content':'a'*1048576}
        with self.assertRaisesRegex(ValueError,'request cap'):self.client.call('create_tree',repository_full_name=r.REPO,base_tree_sha='a'*40,tree_elements=[e])
        self.assertEqual(self.git.actual,[])
    def test_cached_predicted_tree_still_requires_fresh_blob_readback(self):
        def hook(method,p,result):
            if method=='fetch_file' and '/artifacts/' in p['path']:result['content']=base64.b64encode(b'corrupt').decode()
            return result
        doc,_,_=self.store.consume(0);self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'content hash'):self.store.seal(doc,self.payloads(),'archived','',1)
        self.assertTrue(self.store.stopped)
    def test_race_before_ref_aborts(self):
        def hook(method,p,result):
            if method=='create_commit':self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'advanced'):self.store.consume(0)
        self.assertNotIn('update_ref',[m for m,p in self.git.actual])
    def test_ambiguous_landed_write_never_retries(self):
        def hook(method,p,result):
            if method=='update_ref':raise OSError('lost receipt')
            return result
        self.git.hook=hook
        with self.assertRaises(r.Stopped):self.store.consume(0)
        n=len(self.git.actual)
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(len(self.git.actual),n)
    def test_late_seal_cannot_authorize_completion(self):
        doc,_,_=self.store.consume(0)
        def hook(method,p,result):
            if method=='update_ref':self.tick=81
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(r.Stopped,'end-to-end'):self.store.seal(doc,self.payloads(),'archived','',1)
        self.assertTrue(self.store.stopped)
    def test_new_process_cannot_seal_or_reset_consumed_case(self):
        doc,_,_=self.store.consume(0)
        with self.assertRaisesRegex(ValueError,'process-local'):self.fresh().seal(doc,self.payloads(),'archived','',1)
        with self.assertRaisesRegex(ValueError,'already consumed'):self.fresh().consume(0)
    def test_closed_scope_has_no_second_case(self):
        self.complete();n=len(self.git.actual)
        with self.assertRaisesRegex(ValueError,'exhausted'):self.store.consume(1)
        self.assertEqual(n,len(self.git.actual))
    def test_call_and_response_caps_are_charged(self):
        self.client.calls=160
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(self.git.actual,[])
        client=r.Client(self.git.invoke,prior_usage={'calls':0,'seconds':0,'response_bytes':16*1024**2})
        with self.assertRaises(r.Stopped):client.call('fetch',url='https://api.github.com/repos/'+r.REPO+'/git/ref/heads/'+r.BRANCH)
        self.assertTrue(client.stopped)

if __name__=='__main__':unittest.main()
