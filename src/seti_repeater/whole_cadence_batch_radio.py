"""Bounded batch-content engineering adapter; closed predecessor code is unchanged."""
import base64
import hashlib
import json
import time
import uuid
from . import whole_cadence_remote_radio as old
from . import whole_cadence_ascii_radio as ascii_codec
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest,_sha
from .whole_cadence_journal_radio import clone,artifact_name
REPO=old.REPO
BRANCH=old.BRANCH
PREFIX='results_radio_whole_cadence_batch_2026-09-29/live01'
LIMITS={'calls':160,'response_bytes':16*1024**2,'seconds':600}
SCHEMA='radio-batched-engineering-journal-v1'
MAX_LEDGER_HISTORY=65536
MAX_EVIDENCE=2*1024**2
Stopped=old.Stopped
git_sha=old.git_sha
git_object=old.git_object
safe_path=old.safe_path

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
        if method not in ('fetch','fetch_file','create_tree','create_commit','update_ref'):
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
        if method=='create_tree':
            entries=params['tree_elements']
            if not entries or len(entries)>16:raise ValueError('Bounded batch inventory required')
            for e in entries:
                if (set(e)!={'path','mode','type','content'} or not e['path'].startswith(PREFIX+'/')
                    or e['mode']!='100644' or e['type']!='blob' or not isinstance(e['content'],str)
                    or not e['content'].isascii()):raise ValueError('Pinned ASCII content entries only')
                safe_path(e['path'])
            if len({e['path'] for e in entries})!=len(entries):raise ValueError('Duplicate batch path')
            if len(canonical(params))>1048576:raise ValueError('Batch request cap exceeded')
        try:
            if self.calls>=LIMITS['calls'] or self.clock()-self.started>LIMITS['seconds']:
                raise ValueError('Tool-call/time capacity exhausted')
            self.calls+=1
            event={'index':self.calls,'method':method,'request_sha256':digest(params),
                'request_json_bytes':len(canonical(params)),'started_seconds':self.clock()-self.started};self.events.append(event)
            result=self.invoke(method,params)
            payload=canonical(result);self.response_bytes+=len(payload)
            event['ended_seconds']=self.clock()-self.started
            event.update(response_sha256=hashlib.sha256(payload).hexdigest(),response_json_bytes=len(payload))
            if self.response_bytes>LIMITS['response_bytes'] or self.clock()-self.started>LIMITS['seconds']:
                raise ValueError('Returned JSON/time capacity exhausted; publication may have landed')
            if not isinstance(result,dict):raise ValueError('Object tool response required')
            return result
        except BaseException as error:
            self.stopped=True;self.events.append({'stopped':repr(error),'quota_may_be_spent':True,'automatic_retry':False})
            raise Stopped('Tool operation stopped without retry: '+str(error)) from error


def validate_manifest(m):
    if set(m)!={'schema','mode','namespace','execution_binding_sha256','recipe_sha256','cases'} or m['schema']!=SCHEMA or m['mode']!='ENGINEERING_ONLY' or m['namespace']!=PREFIX:
        raise ValueError('Exact engineering-only manifest required')
    for k in ('execution_binding_sha256','recipe_sha256'):_sha(m[k],k)
    if len(m['cases'])!=1:raise ValueError('One preregistered engineering case required')
    for i,c in enumerate(m['cases']):
        expected={'ordinal':i,'case_identity':c.get('case_identity'),'milliseconds':80000,
            'physical_bytes':1048576,'failure_bytes':8192,
            'required_artifacts':['witness.json','payload.bin']}
        if c!=expected or any(type(c[k]) is not int for k in ('ordinal','milliseconds','physical_bytes','failure_bytes')):
            raise ValueError('Exact nonrefundable case quotas required')
        _sha(c['case_identity'],'case')
    return m


def genesis(m):return {'manifest':clone(validate_manifest(m)),'events':[]}


def replay(doc):
    if set(doc)!={'manifest','events'}:raise ValueError('Exact journal fields required')
    m=validate_manifest(doc['manifest']);cases=[];head='0'*64;charged_history=len(canonical(genesis(m)))
    for i,row in enumerate(doc['events']):
        if set(row)!={'index','previous','event','sha256'} or type(row['index']) is not int or row['index']!=i or row['previous']!=head or digest({k:v for k,v in row.items() if k!='sha256'})!=row['sha256']:
            raise ValueError('Journal chain changed')
        e=row['event'];kind=e['kind'];last=cases[-1] if cases else None
        if kind=='consume':
            if set(e)!={'kind','case_identity','nonce'} or len(cases)>=1 or (last and last['status']!='archived'):
                raise ValueError('Case exhausted or previous case incomplete/failed')
            c=m['cases'][len(cases)]
            if c['case_identity']!=e['case_identity'] or str(uuid.UUID(e['nonce']))!=e['nonce']:raise ValueError('Case identity/nonce changed')
            cases.append({'case':c,'nonce':e['nonce'],'status':'consumed','artifacts':{}})
        elif kind=='seal':
            if (not last or last['status']!='consumed' or set(e)!={'kind','case_identity','nonce','outcome','reason','work_milliseconds','artifacts'}
                    or e['case_identity']!=last['case']['case_identity'] or e['nonce']!=last['nonce']):raise ValueError('No active case for seal')
            if e['outcome'] not in ('archived','failed') or not isinstance(e['reason'],str) or len(e['reason'].encode())>1024:
                raise ValueError('Bounded seal outcome/reason required; never EMPTY')
            if type(e['work_milliseconds']) is not int or not 0<=e['work_milliseconds']<=last['case']['milliseconds']:
                raise ValueError('Case work-time cap exceeded')
            names=set(last['case']['required_artifacts']) if e['outcome']=='archived' else {'failure.json'}
            if set(e['artifacts'])!=names:raise ValueError('Complete declared artifact inventory required')
            used=0
            for name,a in e['artifacts'].items():
                artifact_name(name)
                if set(a)!={'manifest_sha256','raw_bytes','raw_sha256','physical_bytes','parts'}:raise ValueError('Exact artifact accounting required')
                for k in ('manifest_sha256','raw_sha256'):_sha(a[k],k)
                for k in ('raw_bytes','physical_bytes'):
                    if type(a[k]) is not int or a[k]<0:raise ValueError('Nonnegative integer artifact accounting required')
                if not a['parts'] or 'manifest.json' not in a['parts']:raise ValueError('Missing envelope manifest')
                for path,v in a['parts'].items():
                    artifact_name(path)
                    if set(v)!={'bytes','sha256'} or type(v['bytes']) is not int or v['bytes']<0:raise ValueError('Invalid physical part receipt')
                    _sha(v['sha256'],'part')
                if sum(v['bytes'] for v in a['parts'].values())!=a['physical_bytes'] or a['parts']['manifest.json']['sha256']!=a['manifest_sha256']:
                    raise ValueError('Physical artifact bytes/manifest pin differ')
                used+=a['physical_bytes']
            cap=last['case']['physical_bytes'] if e['outcome']=='archived' else last['case']['failure_bytes']
            if used>cap:raise ValueError('Physical case/failure reserve exceeded')
            last.update(status=e['outcome'],artifacts=clone(e['artifacts']),work_milliseconds=e['work_milliseconds'],reason=e['reason'])
        else:raise ValueError('Unknown event')
        charged_history+=len(canonical({'manifest':m,'events':doc['events'][:i+1]}));head=row['sha256']
        if charged_history>MAX_LEDGER_HISTORY:raise ValueError('Cumulative ledger history cap exceeded')
    reserved=sum(c['case']['physical_bytes']+c['case']['failure_bytes'] for c in cases)+MAX_LEDGER_HISTORY
    used=sum(a['physical_bytes'] for c in cases for a in c['artifacts'].values())+charged_history
    if reserved>MAX_EVIDENCE or used>MAX_EVIDENCE:raise ValueError('Global physical evidence cap exceeded')
    return {'cases':cases,'head':head,'ledger_history_bytes':charged_history,'reserved_physical_bytes':reserved,
        'used_physical_bytes':used,'scientific_execution_authorized':False}


def append(doc,event):
    state=replay(doc);result=clone(doc);row={'index':len(doc['events']),'previous':state['head'],'event':clone(event)}
    row['sha256']=digest(row);result['events'].append(row);replay(result);return result


def pack(case,payloads,outcome):
    if outcome not in ('archived','failed'):raise ValueError('Explicit archive/failure outcome required')
    cap=case['physical_bytes'] if outcome=='archived' else case['failure_bytes'];parts={};records={};used=0
    names=set(case['required_artifacts']) if outcome=='archived' else {'failure.json'}
    if set(payloads)!=names:raise ValueError('Complete fixed payload names required')
    for name,data in sorted(payloads.items()):
        encoded,receipt=ascii_codec.encode(data,case_identity=case['case_identity'],name=name,physical_byte_cap=cap-used)
        records[name]={'manifest_sha256':receipt['manifest_sha256'],'raw_bytes':len(data),'raw_sha256':hashlib.sha256(data).hexdigest(),
            'physical_bytes':receipt['physical_stored_bytes'],'parts':{p:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for p,v in encoded.items()}}
        for p,value in encoded.items():parts[PREFIX+'/artifacts/'+case['case_identity']+'/'+name+'/'+p]=value
        used+=receipt['physical_stored_bytes']
    return parts,records


class Store(old.GitStore):
    """Reuse verified Git-object traversal, with a distinct atomic ASCII writer."""
    def __init__(self,client,manifest,*,execution_verifier):
        validate_manifest(manifest);self.manifest=canonical(manifest);self.manifest_sha=digest(manifest)
        self.client=client;self.execution_verifier=execution_verifier;self.trees={};self.commits={};self.blobs={};self.blob_paths={}
        self.stopped=False;self.receipts=[];self.last_head=None;self.active=None;self.case_timings=[]

    @property
    def location(self):return PREFIX+'/ledger.json'

    def read(self):
        if self.stopped:raise Stopped('Scope stopped; no retry')
        try:
            self.last_head=self._head();sha=self._file(self.last_head,self.location)
            raw=self._blob(sha,MAX_LEDGER_HISTORY,fresh=True);doc=json.loads(raw)
            if canonical(doc)!=raw or canonical(doc['manifest'])!=self.manifest:raise ValueError('Pinned journal manifest changed')
            replay(doc);return doc,sha
        except BaseException:self.stopped=True;raise

    def verify_execution(self):
        if hashlib.sha256(self.manifest).hexdigest()!=self.manifest_sha:raise ValueError('Execution manifest changed')
        # The general file snapshot verifier accepts only this engineering bridge.
        self.execution_verifier({'mode':'engineering','execution_binding_sha256':json.loads(self.manifest)['execution_binding_sha256']})

    def _expected_tree(self,oldsha,changes):
        original={} if oldsha is None else self._tree(oldsha)
        entries={k:dict(v) for k,v in original.items()};grouped={}
        for path,sha in changes.items():
            first,sep,tail=path.partition('/');grouped.setdefault(first,{})[tail if sep else '']=sha
        for first,remaining in grouped.items():
            prior=original.get(first)
            if '' in remaining:
                if len(remaining)!=1:raise ValueError('File/directory path collision')
                if prior and (prior['mode'],prior['type'])!=('100644','blob'):
                    raise ValueError('Existing leaf mode changed')
                entries[first]={'mode':'100644','type':'blob','sha':remaining['']}
            else:
                if prior and (prior['mode'],prior['type'])!=('040000','tree'):
                    raise ValueError('Nonordinary ancestor in batch')
                sha=self._expected_tree(None if prior is None else prior['sha'],remaining)
                entries[first]={'mode':'040000','type':'tree','sha':sha}
        order=sorted(entries,key=lambda n:(n+('/' if entries[n]['type']=='tree' else '')).encode())
        data=b''.join(entries[n]['mode'].lstrip('0').encode()+b' '+n.encode()+b'\0'+bytes.fromhex(entries[n]['sha']) for n in order)
        sha=git_object('tree',data);self.candidate_trees[sha]=entries;return sha

    def _atomic(self,head,payloads):
        if self.stopped:raise Stopped('Scope stopped')
        candidate=None
        try:
            self.verify_execution()
            if self._head()!=head:raise ValueError('Fresh branch changed before publication')
            before=self._commit(head);changes={};entries=[]
            for path,data in sorted(payloads.items()):
                safe_path(path)
                if not path.startswith(PREFIX+'/') or not isinstance(data,bytes) or not data.isascii():raise ValueError('Pinned ASCII evidence only')
                if path!=self.location:self._assert_absent(head,path)
                changes[path]=git_object('blob',data)
                entries.append({'path':path,'mode':'100644','type':'blob','content':data.decode('ascii')})
            self.candidate_trees={};expected=self._expected_tree(before['tree'],changes)
            result=self.client.call('create_tree',repository_full_name=REPO,base_tree_sha=before['tree'],tree_elements=entries)
            if git_sha(result['sha'])!=expected:raise ValueError('Server tree differs from exact locally computed tree')
            # These caches derive from verified parent trees and are admitted only
            # after the server returns the identical content-addressed root.
            self.trees.update(self.candidate_trees)
            made=self.client.call('create_commit',repository_full_name=REPO,parent_sha=head,tree_sha=expected,
                message='Batched engineering atomic publication '+str(uuid.uuid4()))
            candidate=git_sha(made['sha'])
            if self._commit(candidate)!={'tree':expected,'parents':[head]}:raise ValueError('Candidate parent/tree changed')
            if self._head()!=head:raise ValueError('Branch advanced before update')
            moved=self.client.call('update_ref',repository_full_name=REPO,branch_name=BRANCH,sha=candidate,force=False)
            if moved.get('success') is not True:raise ValueError('Unconfirmed fast-forward')
            for path,data in payloads.items():
                sha=self._file(candidate,path)
                if self._blob(sha,max(1,len(data)),fresh=True)!=data:raise ValueError('Immutable ASCII readback differs')
            if self._head()!=candidate:raise ValueError('Head changed after publication')
            receipt={'parent':head,'commit':candidate,'tree':expected,'files':changes,'bytes':sum(map(len,payloads.values())),
                'exact_tree_computed_from_verified_parent':True,'content_entries':True,
                'immutable_readback_verified':True,'force':False}
            self.receipts.append(receipt);return receipt
        except BaseException as error:
            self.stopped=True;self.receipts.append({'candidate':candidate,'error':repr(error),'no_retry':True});raise

    def _assert_absent(self,head,path):
        tree=self._commit(head)['tree'];names=path.split('/')
        for i,name in enumerate(names):
            entry=self._tree(tree).get(name)
            if entry is None:return
            if i==len(names)-1:raise ValueError('Immutable artifact overwrite prohibited, regardless of mode')
            if (entry['mode'],entry['type'])!=('040000','tree'):raise ValueError('Nonordinary artifact ancestor')
            tree=entry['sha']

    def read_archives(self,doc,head):
        restored={}
        for c in replay(doc)['cases']:
            for name,rec in c['artifacts'].items():
                prefix=PREFIX+'/artifacts/'+c['case']['case_identity']+'/'+name+'/'
                parts={}
                for path,meta in rec['parts'].items():
                    sha=self._file(head,prefix+path);data=self._blob(sha,max(1,meta['bytes']),fresh=True)
                    if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Remote physical part changed')
                    parts[path]=data
                payload=ascii_codec.decode(parts,expected_manifest_sha256=rec['manifest_sha256'],case_identity=c['case']['case_identity'],name=name,physical_byte_cap=rec['physical_bytes'])
                if len(payload)!=rec['raw_bytes'] or hashlib.sha256(payload).hexdigest()!=rec['raw_sha256']:raise ValueError('Remote logical artifact differs')
                restored[c['case']['case_identity']+'/'+name]=payload
        return restored

    def consume(self,index):
        if self.active is not None:raise ValueError('Existing process-local capability cannot be replaced')
        if type(index) is not int or not index==0:raise ValueError('Case index exhausted')
        if index and len(self.case_timings)!=index:
            raise ValueError('Previous process-local finalization incomplete; no fresh-process continuation')
        started=self.client.clock()
        before,revision=self.read();state=replay(before)
        if len(state['cases'])!=index:raise ValueError('Case already consumed or out of order')
        if state['cases']:self.read_archives(before,self.last_head)
        case=before['manifest']['cases'][index];nonce=str(uuid.uuid4())
        after=append(before,{'kind':'consume','case_identity':case['case_identity'],'nonce':nonce})
        self._atomic(self.last_head,{self.location:canonical(after)})
        self.active={'checkpoint_sha256':digest(after),'started':started,'case':case}
        self._check_case_time()
        return after,case,nonce

    def _check_case_time(self):
        elapsed=self.client.clock()-self.active['started']
        if elapsed*1000>self.active['case']['milliseconds']:
            self.stopped=True;raise Stopped('Case end-to-end time exceeded; no subsequent work or retry')
        return elapsed

    def seal(self,checkpoint,payloads,outcome,reason,work_milliseconds):
        if self.active is None or digest(checkpoint)!=self.active['checkpoint_sha256']:
            raise ValueError('Original process-local capability required; no crash resume')
        self._check_case_time()
        before,_=self.read()
        if before!=checkpoint:raise ValueError('Consumed checkpoint changed')
        state=replay(before);case=state['cases'][-1]
        parts,records=pack(case['case'],payloads,outcome)
        after=append(before,{'kind':'seal','case_identity':case['case']['case_identity'],'nonce':case['nonce'],
            'outcome':outcome,'reason':reason,'work_milliseconds':work_milliseconds,'artifacts':records})
        self._atomic(self.last_head,{**parts,self.location:canonical(after)})
        elapsed=self._check_case_time()
        self.case_timings.append({'case_identity':case['case']['case_identity'],'end_to_end_seconds':elapsed,
            'includes_consume_seal_readback':True,'outcome':outcome})
        self.active=None
        return after
