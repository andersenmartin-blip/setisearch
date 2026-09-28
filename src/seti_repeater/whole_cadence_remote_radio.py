"""Actual Git-object publisher for a separately pinned engineering case ledger.

The authenticated tool transport is injected. This implementation has no token
handling, no arbitrary repository/branch selector and NO scientific activation.
Logical revisions are ledger Git-blob IDs. Every physical commit uses a fresh
exact parent, a unique attempt ID and force=false, with immutable readback.
"""
import base64
import hashlib
import json
import re
import time
import uuid
from urllib.parse import quote
from . import whole_cadence_journal_radio as journal
from .whole_cadence_reference_radio import digest,_sha
from .empty_null_radio import canonical

REPO='andersenmartin-blip/setisearch'
BRANCH='m43-support-qualification'
PREFIX='results_radio_whole_cadence_remote_2026-09-28/live02'
CHUNK=256*1024
LIMITS={'calls':300,'response_bytes':32*1024**2,'seconds':1800}


def git_sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{40}',value):raise ValueError('Invalid Git SHA')
    return value


def git_object(kind,payload):
    return hashlib.sha1(kind.encode()+b' '+str(len(payload)).encode()+b'\0'+payload).hexdigest()


def safe_path(path):
    if not isinstance(path,str) or any(p in ('','.','..') for p in path.split('/')) or '\\' in path or any(ord(c)<32 for c in path):
        raise ValueError('Unsafe Git path')
    return path


class Stopped(RuntimeError):pass


class Client:
    """One bounded authenticated tool session. No automatic retries."""
    def __init__(self,invoke,*,clock=time.monotonic,prior_usage=None):
        prior=prior_usage or {'calls':0,'response_bytes':0,'seconds':0}
        if set(prior)!=set(LIMITS) or any(type(v) is not int or not 0<=v<=LIMITS[k] for k,v in prior.items()):
            raise ValueError('Bounded conservative prior resource charges required')
        self.invoke=invoke;self.clock=clock;self.started=clock()-prior['seconds']
        self.calls=prior['calls'];self.response_bytes=prior['response_bytes']
        self.events=[];self.stopped=False

    def call(self,method,**params):
        if self.stopped:raise Stopped('Transport already stopped; inspect retained evidence')
        if method not in ('fetch','fetch_file','create_blob','create_tree','create_commit','update_ref'):
            raise ValueError('Unsupported Git tool operation')
        if method=='fetch':
            if not params['url'].startswith('https://api.github.com/repos/'+REPO+'/git/'):
                raise ValueError('Only pinned Git database GET requests allowed')
        elif params.get('repository_full_name')!=REPO:raise ValueError('Repository changed')
        if method=='fetch_file':
            safe_path(params['path']);git_sha(params['ref'])
            if not params['path'].startswith(PREFIX+'/') or params.get('encoding')!='base64':
                raise ValueError('Pinned immutable engineering file/base64 required')
        if method=='update_ref' and (params.get('branch_name')!=BRANCH or params.get('force') is not False):
            raise ValueError('Only pinned fast-forward branch updates allowed')
        if method=='create_tree' and any(not e['path'].startswith(PREFIX+'/') or e['mode']!='100644'
                or e['type']!='blob' or 'content' in e for e in params['tree_elements']):
            raise ValueError('Publication path/mode differs from engineering namespace')
        if method=='create_tree':
            for e in params['tree_elements']:safe_path(e['path'])
        try:
            if self.calls>=LIMITS['calls'] or self.clock()-self.started>LIMITS['seconds']:
                raise ValueError('Tool-call/time capacity exhausted')
            self.calls+=1
            event={'index':self.calls,'method':method,'request_sha256':digest(params),
                'request_json_bytes':len(canonical(params))};self.events.append(event)
            result=self.invoke(method,params)
            payload=canonical(result);self.response_bytes+=len(payload)
            event.update(response_sha256=hashlib.sha256(payload).hexdigest(),response_json_bytes=len(payload))
            if self.response_bytes>LIMITS['response_bytes'] or self.clock()-self.started>LIMITS['seconds']:
                raise ValueError('Returned JSON/time capacity exhausted; publication may have landed')
            if not isinstance(result,dict):raise ValueError('Object tool response required')
            return result
        except BaseException as error:
            self.stopped=True;self.events.append({'stopped':repr(error),'quota_may_be_spent':True,'automatic_retry':False})
            raise Stopped('Tool operation stopped without retry: '+str(error)) from error


class GitStore:
    def __init__(self,client,spec_bytes,expected_spec_sha256,*,execution_verifier):
        if hashlib.sha256(spec_bytes).hexdigest()!=expected_spec_sha256:raise ValueError('Independent store specification differs')
        spec=json.loads(spec_bytes)
        if (set(spec)!={'schema','mode','repository','branch','prefix','manifest_sha256','genesis_sha256','case_reservations'}
                or spec['schema']!='radio-whole-cadence-github-store-v1' or spec['mode']!='engineering'
                or spec['repository']!=REPO or spec['branch']!=BRANCH or spec['prefix']!=PREFIX):
            raise ValueError('Only the pinned engineering store is available; scientific mode unactivated')
        for key in ('manifest_sha256','genesis_sha256'):_sha(spec[key],key)
        self.client=client;self.spec=canonical(spec);self.spec_sha=expected_spec_sha256
        self.execution_verifier=execution_verifier;self.trees={};self.commits={};self.blobs={}
        self.stopped=False;self.receipts=[];self.last_head=None;self.blob_paths={}

    @property
    def location(self):return {'kind':'github-published-engineering','repository':REPO,'branch':BRANCH,'path':PREFIX+'/ledger.json'}

    def _get(self,path):return self.client.call('fetch',url='https://api.github.com/repos/'+REPO+'/git/'+path)

    def _head(self):
        r=self._get('ref/heads/'+quote(BRANCH,safe=''))
        if r.get('ref')!='refs/heads/'+BRANCH or r.get('object',{}).get('type')!='commit':raise ValueError('Branch identity/type changed')
        return git_sha(r['object']['sha'])

    def _commit(self,sha):
        git_sha(sha)
        if sha not in self.commits:
            r=self._get('commits/'+sha)
            if r.get('sha')!=sha:raise ValueError('Commit object differs')
            self.commits[sha]={'tree':git_sha(r['tree']['sha']),'parents':[git_sha(p['sha']) for p in r['parents']]}
        return self.commits[sha]

    def _tree(self,sha):
        git_sha(sha)
        if sha in self.trees:return self.trees[sha]
        r=self._get('trees/'+sha)
        if r.get('sha')!=sha or r.get('truncated') is not False:raise ValueError('Missing/truncated Git tree')
        entries={}
        allowed={('040000','tree'),('100644','blob'),('100755','blob'),('120000','blob'),('160000','commit')}
        for v in r['tree']:
            name=v['path']
            if not isinstance(name,str) or name in ('','.','..') or '/' in name or '\0' in name or name in entries:
                raise ValueError('Invalid Git tree name')
            if (v['mode'],v['type']) not in allowed:raise ValueError('Invalid Git tree mode')
            entries[name]={'mode':v['mode'],'type':v['type'],'sha':git_sha(v['sha'])}
        order=sorted(entries,key=lambda n:(n+('/' if entries[n]['type']=='tree' else '')).encode())
        raw=b''.join(entries[n]['mode'].lstrip('0').encode()+b' '+n.encode()+b'\0'+bytes.fromhex(entries[n]['sha']) for n in order)
        if git_object('tree',raw)!=sha:raise ValueError('Git tree content hash differs')
        self.trees[sha]=entries;return entries

    def _file(self,commit,path):
        safe_path(path);tree=self._commit(commit)['tree'];parts=path.split('/')
        for i,name in enumerate(parts):
            e=self._tree(tree).get(name)
            expected=('100644','blob') if i==len(parts)-1 else ('040000','tree')
            if e is None or (e['mode'],e['type'])!=expected:raise ValueError('Missing or nonordinary pinned Git path: '+path)
            tree=e['sha']
        self.blob_paths[tree]=(commit,path)
        return tree

    def _blob(self,sha,cap,*,fresh=False):
        git_sha(sha)
        if fresh or sha not in self.blobs:
            commit,path=self.blob_paths[sha]
            r=self.client.call('fetch_file',repository_full_name=REPO,path=path,ref=commit,encoding='base64')
            if r.get('sha')!=sha or r.get('encoding')!='base64':
                raise ValueError('Git blob size/encoding/identity differs')
            encoded=r['content'].replace('\n','').replace('\r','')
            if len(encoded)>4*((cap+2)//3):raise ValueError('Encoded Git blob exceeds cap')
            data=base64.b64decode(encoded,validate=True)
            if len(data)>cap or git_object('blob',data)!=sha:raise ValueError('Git blob content hash differs')
            self.blobs[sha]=data
        data=self.blobs[sha]
        if len(data)>cap:raise ValueError('Cached blob exceeds requested cap')
        return data

    def _checkpoint(self,head):
        sha=self._file(head,self.location['path']);data=self._blob(sha,8*1024**2,fresh=True)
        doc=json.loads(data)
        if canonical(doc)!=data:raise ValueError('Noncanonical ledger')
        self._validate(doc)
        return journal.Checkpoint(doc,sha,self.location)

    def _validate(self,doc):
        journal.replay(doc);spec=json.loads(self.spec)
        if (doc['manifest']['mode']!='engineering' or doc['manifest_sha256']!=spec['manifest_sha256']
                or digest(journal.genesis(doc['manifest']))!=spec['genesis_sha256']):
            raise ValueError('Remote ledger manifest/genesis changed')
        cases=journal.replay(doc)['cases']
        if len(spec['case_reservations'])!=len(doc['manifest']['cases']):raise ValueError('Exact reservation inventory required')
        for case,quota in zip(cases,spec['case_reservations']):
            if quota!={'case_identity':case['binding']['case_identity'],'milliseconds':case['milliseconds'],'artifact_bytes':case['artifact_bytes']}:
                raise ValueError('Remote case-specific reservation differs')
            for meta in case['artifacts'].values():
                if 'publication' not in meta:raise ValueError('Remote evidence requires publication receipt')

    def read(self):
        if self.stopped:raise Stopped('Remote store stopped; no retry')
        try:
            self.last_head=self._head();return self._checkpoint(self.last_head)
        except BaseException:
            self.stopped=True;raise

    def verify_execution(self,manifest):
        if digest(manifest)!=json.loads(self.spec)['manifest_sha256']:raise ValueError('Execution manifest changed')
        return self.execution_verifier(manifest)

    def _delta(self,oldsha,newsha,changes,*,add_only):
        old={} if oldsha is None else self._tree(oldsha);new=self._tree(newsha)
        grouped={}
        for path,value in changes.items():
            first,sep,tail=path.partition('/');grouped.setdefault(first,{})[tail if sep else '']=value
        if {k:v for k,v in old.items() if k not in grouped}!={k:v for k,v in new.items() if k not in grouped}:
            raise ValueError('Candidate tree changed an unrelated path')
        for first,remaining in grouped.items():
            entry=new.get(first)
            if '' in remaining:
                if len(remaining)!=1 or entry!={'mode':'100644','type':'blob','sha':remaining['']}:
                    raise ValueError('Candidate leaf differs')
                if add_only and first in old:raise ValueError('Artifact overwrite prohibited')
            else:
                if entry is None or entry['mode']!='040000' or entry['type']!='tree':raise ValueError('Candidate directory differs')
                prior=old.get(first)
                if prior and (prior['mode'],prior['type'])!=('040000','tree'):raise ValueError('Ancestor mode differs')
                self._delta(None if prior is None else prior['sha'],entry['sha'],remaining,add_only=add_only)

    def _write(self,head,payloads,*,add_only):
        if self.stopped:raise Stopped('Remote store stopped')
        candidate=None
        try:
            if self._head()!=head:raise ValueError('Fresh branch checkpoint changed')
            before=self._commit(head);changes={}
            for path,data in payloads.items():
                safe_path(path)
                if not path.startswith(PREFIX+'/') or not isinstance(data,bytes):raise ValueError('Pinned namespace/bytes required')
                sha=git_object('blob',data)
                made=self.client.call('create_blob',repository_full_name=REPO,content=base64.b64encode(data).decode(),encoding='base64')
                if made.get('sha')!=sha:raise ValueError('Created blob differs')
                changes[path]=sha
            tree=self.client.call('create_tree',repository_full_name=REPO,base_tree_sha=before['tree'],
                tree_elements=[{'path':p,'mode':'100644','type':'blob','sha':sha} for p,sha in sorted(changes.items())])
            tree_sha=git_sha(tree['sha']);self._delta(before['tree'],tree_sha,changes,add_only=add_only)
            made=self.client.call('create_commit',repository_full_name=REPO,parent_sha=head,tree_sha=tree_sha,
                message='Whole-cadence engineering publication '+str(uuid.uuid4()))
            candidate=git_sha(made['sha'])
            if self._commit(candidate)!={'tree':tree_sha,'parents':[head]}:raise ValueError('Candidate parent/tree differs')
            if self._head()!=head:raise ValueError('Branch advanced before fast-forward update')
            updated=self.client.call('update_ref',repository_full_name=REPO,branch_name=BRANCH,sha=candidate,force=False)
            if updated.get('success') is not True:raise ValueError('Unconfirmed branch update')
            for path,data in payloads.items():
                sha=self._file(candidate,path)
                # Do not populate blob cache from uploads. This must be an actual
                # immutable remote GET, verified by Git blob hash and exact bytes.
                if self._blob(sha,max(len(data),1))!=data:raise ValueError('Published bytes differ')
            if self._head()!=candidate:raise ValueError('Post-publication head changed; inspect without retry')
            receipt={'parent':head,'commit':candidate,'tree':tree_sha,'files':changes,
                'force':False,'only_declared_paths_changed':True,'immutable_bytes_read_back':True}
            self.receipts.append(receipt);self.last_head=candidate;return receipt
        except BaseException as error:
            self.stopped=True;self.receipts.append({'candidate':candidate,'error':repr(error),
                'quota_may_be_spent':True,'automatic_retry':False});raise

    def publish(self,expected_revision,document):
        before=self.read()
        if before.revision!=expected_revision:raise ValueError('Logical ledger checkpoint changed')
        if (document['manifest']!=before.document['manifest'] or len(document['events'])!=len(before.document['events'])+1
                or document['events'][:-1]!=before.document['events']):raise ValueError('Remote ledger is append-only')
        self._validate(document);self.verify_execution(document['manifest'])
        event=document['events'][-1]['event']
        if event['kind']=='artifact':
            case=journal.replay(document)['cases'][-1]
            expected={'case_identity':case['binding']['case_identity'],'nonce':case['nonce'],'name':event['name']}
            data=self.read_artifact(event['publication'],expected=expected)
            if len(data)!=event['size'] or hashlib.sha256(data).hexdigest()!=event['sha256']:
                raise ValueError('Artifact publication is not bound to registered evidence')
        if event['kind']=='finish' and event['outcome']=='completed':self.verify_completed_evidence(journal.Checkpoint(document,'candidate',self.location))
        self._write(self.last_head,{self.location['path']:canonical(document)},add_only=False)

    def publish_artifact(self,checkpoint,name,payload):
        before=self.read()
        if before!=checkpoint:raise ValueError('Artifact ledger checkpoint changed')
        state=journal.replay(before.document);case=state['cases'][-1];journal.artifact_name(name)
        if case['status'] not in ('consumed','started') or name not in before.document['manifest']['required_artifacts']:
            raise ValueError('Artifact not in an active declared case')
        if name in case['artifacts'] or len(payload)+sum(x['size'] for x in case['artifacts'].values())>case['artifact_bytes']:
            raise ValueError('Artifact already registered or case cap exceeded')
        prefix=PREFIX+'/artifacts/'+case['binding']['case_identity']+'/'+name
        chunks={prefix+f'/chunk{i:04d}.bin':payload[o:o+CHUNK] for i,o in enumerate(range(0,len(payload),CHUNK))}
        manifest={'schema':'radio-git-chunked-artifact-v1','case_identity':case['binding']['case_identity'],
            'nonce':case['nonce'],'name':name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
            'chunks':[{'path':p,'bytes':len(v),'blob':git_object('blob',v),'sha256':hashlib.sha256(v).hexdigest()} for p,v in chunks.items()]}
        path=prefix+'/manifest.json';result=self._write(self.last_head,{**chunks,path:canonical(manifest)},add_only=True)
        publication={'location':{'repository':REPO,'path':path,'manifest_blob':result['files'][path]},
            'revision':result['commit'],'sha256':manifest['sha256']}
        if self.read_artifact(publication)!=payload:raise ValueError('Artifact aggregate readback differs')
        return publication

    def read_artifact(self,publication,*,expected=None):
        if set(publication)!={'location','revision','sha256'}:raise ValueError('Artifact publication receipt differs')
        location=publication['location'];commit=git_sha(publication['revision']);_sha(publication['sha256'],'artifact SHA256')
        if (set(location)!={'repository','path','manifest_blob'} or location['repository']!=REPO
                or not location['path'].startswith(PREFIX+'/artifacts/')):raise ValueError('Artifact location differs')
        path=safe_path(location['path']);sha=self._file(commit,path)
        if sha!=git_sha(location['manifest_blob']):raise ValueError('Artifact manifest blob changed')
        manifest=json.loads(self._blob(sha,65536,fresh=True))
        if (set(manifest)!={'schema','case_identity','nonce','name','bytes','sha256','chunks'}
                or manifest['schema']!='radio-git-chunked-artifact-v1' or manifest['sha256']!=publication['sha256']):
            raise ValueError('Artifact manifest differs')
        _sha(manifest['case_identity'],'artifact case');journal.artifact_name(manifest['name'])
        if str(uuid.UUID(manifest['nonce']))!=manifest['nonce']:raise ValueError('Artifact nonce differs')
        if path!=PREFIX+'/artifacts/'+manifest['case_identity']+'/'+manifest['name']+'/manifest.json':
            raise ValueError('Artifact path is not bound to its case/name')
        if expected is not None and any(manifest.get(k)!=v for k,v in expected.items()):
            raise ValueError('Artifact belongs to another case, nonce or name')
        if type(manifest['bytes']) is not int or not 0<=manifest['bytes']<=18*1024**2:raise ValueError('Artifact capacity exceeded')
        prefix=path.rsplit('/',1)[0];parts=[]
        if len(manifest['chunks'])!=(manifest['bytes']+CHUNK-1)//CHUNK:raise ValueError('Chunk count differs')
        for i,c in enumerate(manifest['chunks']):
            if (set(c)!={'path','bytes','blob','sha256'} or c['path']!=prefix+f'/chunk{i:04d}.bin'
                    or type(c['bytes']) is not int or c['bytes']!=min(CHUNK,manifest['bytes']-i*CHUNK)):
                raise ValueError('Chunk order/size differs')
            actual=self._file(commit,c['path'])
            if actual!=git_sha(c['blob']):raise ValueError('Chunk tree binding differs')
            data=self._blob(actual,CHUNK,fresh=True)
            if len(data)!=c['bytes'] or hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('Chunk payload differs')
            parts.append(data)
        payload=b''.join(parts)
        if len(payload)!=manifest['bytes'] or hashlib.sha256(payload).hexdigest()!=publication['sha256']:
            raise ValueError('Artifact aggregate differs')
        return payload

    def verify_completed_evidence(self,checkpoint):
        for case in journal.replay(checkpoint.document)['cases']:
            if case['status']=='completed':
                for name,meta in case['artifacts'].items():
                    expected={'case_identity':case['binding']['case_identity'],'nonce':case['nonce'],'name':name}
                    data=self.read_artifact(meta['publication'],expected=expected)
                    if len(data)!=meta['size'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:
                        raise ValueError('Completed remote evidence differs')
