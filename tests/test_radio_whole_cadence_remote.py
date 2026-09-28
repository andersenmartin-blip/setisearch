"""New Git protocol fault doubles; deliberately not live-service evidence."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
from seti_repeater import whole_cadence_remote_radio as r
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest


def manifest():
    sha=lambda s:digest({'scope':'remote-unit-20260928','label':s})
    return {'schema':j.SCHEMA,'mode':'engineering','namespace':'remote-unit-20260928',
        'execution_binding_sha256':sha('freeze'),'allocation_sha256':sha('allocation'),
        'cases':[{k:sha(k) for k in j.BINDING_KEYS if k!='role'}|{'role':'engineering'}],
        'caps':{**j.CAPS,'active_milliseconds':100000,'evidence_bytes':8*1024**2,'ledger_reserve_bytes':65536},
        'required_artifacts':['witness.json','payload.bin']}


def specification(m):
    return canonical({'schema':'radio-whole-cadence-github-store-v1','mode':'engineering',
        'repository':r.REPO,'branch':r.BRANCH,'prefix':r.PREFIX,
        'manifest_sha256':digest(m),'genesis_sha256':digest(j.genesis(m)),
        'case_reservations':[{'case_identity':m['cases'][0]['case_identity'],'milliseconds':90000,'artifact_bytes':1024**2}]})


class GitDouble:
    """Real blob/tree hashes; synthetic commits. No authenticated connection."""
    def __init__(self,m):
        self.blobs={};self.trees={};self.flat={};self.commits={};self.calls=[];self.hook=None
        self.head=self.commit(None,self.tree({r.PREFIX+'/ledger.json':self.blob(canonical(j.genesis(m))),
            'untouched.txt':self.blob(b'preserved')}))

    def blob(self,payload):
        h=r.git_object('blob',payload);self.blobs[h]=payload;return h

    def tree(self,flat):
        children={}
        for path,sha in flat.items():
            first,sep,tail=path.partition('/');children.setdefault(first,{})[tail if sep else '']=sha
        entries={}
        for name,values in children.items():
            if '' in values:entries[name]={'mode':'100644','type':'blob','sha':values['']}
            else:entries[name]={'mode':'040000','type':'tree','sha':self.tree(values)}
        order=sorted(entries,key=lambda n:(n+('/' if entries[n]['type']=='tree' else '')).encode())
        payload=b''.join(entries[n]['mode'].lstrip('0').encode()+b' '+n.encode()+b'\0'+bytes.fromhex(entries[n]['sha']) for n in order)
        h=r.git_object('tree',payload);self.trees[h]=entries;self.flat[h]=dict(flat);return h

    def commit(self,parent,tree):
        rec={'tree':{'sha':tree},'parents':[] if parent is None else [{'sha':parent}],'sequence':len(self.commits)}
        h=hashlib.sha1(canonical(rec)).hexdigest();self.commits[h]={'sha':h,**rec};return h

    def invoke(self,method,p):
        self.calls.append((method,copy.deepcopy(p)))
        if method=='fetch':
            path=p['url'].split('/git/')[1]
            if path.startswith('ref/'):result={'ref':'refs/heads/'+r.BRANCH,'object':{'type':'commit','sha':self.head}}
            elif path.startswith('commits/'):result=self.commits[path.split('/')[-1]]
            elif path.startswith('trees/'):
                h=path.split('/')[-1];result={'sha':h,'truncated':False,'tree':[{'path':n,**v} for n,v in self.trees[h].items()]}
            else:
                h=path.split('/')[-1];data=self.blobs[h]
                result={'sha':h,'encoding':'base64','size':len(data),'content':base64.b64encode(data).decode()}
        elif method=='create_blob':result={'sha':self.blob(base64.b64decode(p['content']))}
        elif method=='create_tree':
            flat=dict(self.flat[p['base_tree_sha']]);flat.update({v['path']:v['sha'] for v in p['tree_elements']})
            result={'sha':self.tree(flat)}
        elif method=='create_commit':result={'sha':self.commit(p['parent_sha'],p['tree_sha'])}
        else:
            target=self.commits[p['sha']]
            if target['parents']!=[{'sha':self.head}]:raise ValueError('Non fast-forward')
            self.head=p['sha'];result={'success':True}
        result=copy.deepcopy(result)
        return self.hook(method,p,result) if self.hook else result


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.m=manifest()
        self.spec=specification(self.m);self.git=GitDouble(self.m);self.client=r.Client(self.git.invoke)
        self.verified=0;self.store=self.fresh()

    def tearDown(self):self.tmp.cleanup()

    def verifier(self,m):self.verified+=1

    def fresh(self):return r.GitStore(self.client,self.spec,hashlib.sha256(self.spec).hexdigest(),execution_verifier=self.verifier)

    def claim(self,**kw):
        cp=self.store.read();args={'expected_revision':cp.revision,'expected_manifest_sha256':digest(self.m),
            'binding':self.m['cases'][0],'milliseconds':90000,'artifact_bytes':1024**2,'directory':self.root/'case'}
        args.update(kw);return j.consume(self.store,**args)

    def complete(self):
        lease=self.claim();lease.write_artifact('witness.json',b'{}');lease.write_artifact('payload.bin',b'x'*(r.CHUNK+17));lease.finish();return lease

    def test_real_hash_chunk_boundary_roundtrip_and_readonly(self):
        lease=self.complete();fresh=self.fresh();cp=fresh.read();fresh.verify_completed_evidence(cp)
        self.assertEqual(j.replay(cp.document)['cases'][0]['status'],'completed')
        self.assertEqual(len(self.store.receipts),6);self.assertGreater(self.verified,4)
        self.assertLess(self.client.calls,r.LIMITS['calls'])
        self.assertEqual(j.verify_archive(cp,lease.directory,case_index=0)['artifact_bytes'],r.CHUNK+19)
        self.assertTrue(all(not p['force'] for m,p in self.git.calls if m=='update_ref'))

    def test_exact_case_quota_before_publication(self):
        before=self.git.head
        with self.assertRaisesRegex(ValueError,'case-specific'):self.claim(milliseconds=90001)
        self.assertEqual(self.git.head,before)

    def test_scientific_store_cannot_be_selected(self):
        spec=json.loads(self.spec);spec['mode']='scientific';raw=canonical(spec)
        with self.assertRaisesRegex(ValueError,'unactivated'):r.GitStore(self.client,raw,hashlib.sha256(raw).hexdigest(),execution_verifier=self.verifier)

    def test_engineering_cannot_start_reserved_rng(self):
        lease=self.claim()
        with self.assertRaisesRegex(ValueError,'PROPOSED_NOT_ACTIVATED'):lease.begin_gaussian(None)

    def test_completed_case_cannot_reconsume(self):
        self.complete();head=self.git.head
        with self.assertRaisesRegex(ValueError,'order'):self.claim(directory=self.root/'again')
        self.assertEqual(self.git.head,head)

    def test_branch_race_before_ref_update_stops(self):
        def hook(m,p,result):
            if m=='create_commit':self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'advanced'):self.claim()
        self.assertFalse(any(m=='update_ref' for m,p in self.git.calls));self.assertTrue(self.store.stopped)

    def test_ambiguous_success_never_retries(self):
        def hook(m,p,result):
            if m=='update_ref':raise OSError('lost response after mutation')
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(r.Stopped,'lost response'):self.claim()
        n=len(self.git.calls)
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(len(self.git.calls),n);self.assertTrue(self.store.receipts[-1]['quota_may_be_spent'])

    def test_postwrite_head_change_stops_without_retry(self):
        def hook(m,p,result):
            if m=='update_ref':self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'Post-publication'):self.claim()
        self.assertTrue(self.store.stopped)

    def test_unrelated_tree_change_rejected_before_ref(self):
        def hook(m,p,result):
            if m=='create_tree':
                flat=dict(self.git.flat[result['sha']]);flat['untouched.txt']=self.git.blob(b'changed');result={'sha':self.git.tree(flat)}
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'unrelated'):self.claim()
        self.assertFalse(any(m=='update_ref' for m,p in self.git.calls))

    def test_incorrect_tree_hash_rejected(self):
        def hook(m,p,result):
            if m=='fetch' and '/trees/' in p['url']:result['tree'].pop()
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'tree content hash'):self.store.read()

    def test_uploaded_blob_hash_rejected(self):
        self.git.hook=lambda m,p,res:({'sha':'a'*40} if m=='create_blob' else res)
        with self.assertRaisesRegex(ValueError,'Created blob'):self.claim()

    def test_live_blob_content_changed_detected_fresh(self):
        lease=self.complete();meta=j.replay(lease.checkpoint.document)['cases'][0]['artifacts']['payload.bin']
        self.store.read_artifact(meta['publication'])
        def hook(m,p,result):
            if m=='fetch' and '/blobs/' in p['url'] and result['size']==r.CHUNK:
                result['content']=base64.b64encode(b'z'*r.CHUNK).decode()
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'blob content hash'):self.store.read_artifact(meta['publication'])

    def test_missing_remote_blob_rejected(self):
        lease=self.complete();meta=j.replay(lease.checkpoint.document)['cases'][0]['artifacts']['witness.json']
        del self.git.blobs[r.git_object('blob',b'{}')]
        with self.assertRaises(r.Stopped):self.fresh().read_artifact(meta['publication'])

    def test_other_nonce_cannot_register_same_bytes(self):
        lease=self.claim();cp=lease.checkpoint;pub=self.store.publish_artifact(cp,'witness.json',b'{}')
        bad=copy.deepcopy(cp.document);bad['events']=[]
        event=copy.deepcopy(cp.document['events'][0]['event']);event['nonce']=str(uuid.uuid4());bad=j.append(bad,event)
        path=r.PREFIX+'/ledger.json';self.git.head=self.git.commit(self.git.head,self.git.tree({**self.git.flat[self.git.commits[self.git.head]['tree']['sha']],path:self.git.blob(canonical(bad))}))
        cp=self.store.read();event={'kind':'artifact','nonce':event['nonce'],'name':'witness.json','size':2,'sha256':hashlib.sha256(b'{}').hexdigest(),'publication':pub}
        with self.assertRaisesRegex(ValueError,'another case, nonce or name'):self.store.publish(cp.revision,j.append(cp.document,event))

    def test_existing_unregistered_artifact_cannot_overwrite(self):
        lease=self.claim();self.store.publish_artifact(lease.checkpoint,'witness.json',b'{}')
        with self.assertRaisesRegex(ValueError,'overwrite'):self.store.publish_artifact(lease.checkpoint,'witness.json',b'{}')

    def test_call_cap_halts_without_extra_request(self):
        self.client.calls=r.LIMITS['calls']
        with self.assertRaises(r.Stopped):self.store.read()
        self.assertEqual(self.git.calls,[])

    def test_returned_byte_cap_halts_without_retry(self):
        self.client.response_bytes=r.LIMITS['response_bytes']
        with self.assertRaisesRegex(r.Stopped,'capacity'):self.store.read()
        self.assertTrue(self.client.stopped)

    def test_transport_cannot_change_destination_or_force(self):
        for params in ({'repository_full_name':r.REPO,'branch_name':'main','force':False},
                       {'repository_full_name':r.REPO,'branch_name':r.BRANCH,'force':True}):
            with self.assertRaisesRegex(ValueError,'pinned'):self.client.call('update_ref',**params)
        self.assertEqual(self.git.calls,[])

    def test_finish_counts_external_verification_latency(self):
        lease=self.claim(clock=lambda:0.);lease.write_artifact('witness.json',b'{}');lease.write_artifact('payload.bin',b'x')
        tick=[0.];lease.clock=lambda:tick[0];read=self.store.read_artifact
        def slow(pub,**kw):tick[0]+=46.;return read(pub,**kw)
        self.store.read_artifact=slow
        with self.assertRaisesRegex(ValueError,'active-time'):lease.finish()
        self.assertNotEqual(j.replay(self.store.read().document)['cases'][0]['status'],'completed')

if __name__=='__main__':unittest.main()
