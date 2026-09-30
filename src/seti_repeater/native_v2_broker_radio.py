"""Bounded inline-tree broker for terminal native-v2 cases during execution.

Exact source files are framed, split into base64 text chunks and submitted in a
single Git tree mutation.  The transport is injected.  Readback is one grouped
operation and restores every original byte.  Ambiguity stops the whole broker;
it never grants restart, RNG or scientific authority.
"""
import base64
from dataclasses import asdict,dataclass
import hashlib
import json
import math
import re
import resource
import time
from types import MappingProxyType
from urllib.parse import quote

from .empty_null_radio import canonical
from . import event_archive_remote_radio as archive
from . import physical_evidence_v2_radio as physical
from . import whole_cadence_event_store_radio as events
from . import whole_cadence_journal_radio as journal

REPO=archive.REPO
BRANCH=archive.BRANCH
ROOT_PREFIX='results_radio_native_v2_engineering_20260930a/live01'
SCHEMA='radio-native-v2-inline-terminal-archive-v1'
BROKER_PROTOCOL='radio-native-v2-inline-broker-accounting-v2'
CHUNK_BYTES=1024*1024
MAX_SOURCE_BYTES=26*1024**2
MANIFEST_RESERVE_BYTES=512*1024
RESPONSE_RESERVATIONS=MappingProxyType({'fetch':4*1024**2,
    'create_tree':1024**2,'create_commit':65536,'update_ref':16384,
    'fetch_files':48*1024**2})


@dataclass(frozen=True)
class Limits:
    calls:int=64
    request_bytes:int=48*1024**2
    response_bytes:int=64*1024**2
    stored_bytes:int=36*1024**2
    files:int=28
    seconds:int=600
    peak_rss_bytes:int=512*1024**2

    def validate(self):
        hard=asdict(Limits())
        if any(type(value) is not int or not 0<value<=hard[name]
               for name,value in asdict(self).items()):
            raise ValueError('Finite prospective per-case broker limits required')
        return self


@dataclass(frozen=True)
class CumulativeLimits:
    cases:int=8
    calls:int=512
    request_bytes:int=384*1024**2
    response_bytes:int=512*1024**2
    stored_bytes:int=288*1024**2
    seconds:int=4800
    peak_rss_bytes:int=512*1024**2


@dataclass(frozen=True)
class Bundle:
    ordinal:int
    prefix:str
    files:object
    manifest_bytes:bytes
    freeze_bytes:bytes
    limits:Limits

    @property
    def sha256(self):return hashlib.sha256(self.freeze_bytes).hexdigest()


def capacity_record():
    chunks=math.ceil(MAX_SOURCE_BYTES/CHUNK_BYTES)
    full=4*math.ceil(CHUNK_BYTES/3)
    final_raw=MAX_SOURCE_BYTES-(chunks-1)*CHUNK_BYTES
    encoded=(chunks-1)*full+4*math.ceil(final_raw/3)
    stored=encoded+MANIFEST_RESERVE_BYTES+65
    create_tree_request=stored+1024*1024
    grouped_response=4*math.ceil(stored/3)+1024*1024
    if (chunks+2>Limits().files or stored>Limits().stored_bytes
            or create_tree_request>Limits().request_bytes
            or grouped_response>Limits().response_bytes):
        raise ValueError('Worst-case inline broker envelope exceeds frozen limits')
    return {'schema':'radio-native-v2-inline-broker-capacity-v1','source_bytes':MAX_SOURCE_BYTES,
        'chunk_bytes':CHUNK_BYTES,'chunks':chunks,'remote_files':chunks+2,
        'encoded_chunk_bytes':encoded,'manifest_reserve_bytes':MANIFEST_RESERVE_BYTES,
        'stored_bytes_including_head_and_manifest_reserve':stored,
        'create_tree_request_bytes_including_framing_reserve':create_tree_request,
        'grouped_response_bytes_including_framing_reserve':grouped_response,
        'per_case_limits':asdict(Limits()),'cumulative_limits':asdict(CumulativeLimits()),
        'scientific_admission_authorized':False}


def _copy(values):
    if not isinstance(values,(dict,MappingProxyType)):raise ValueError('Explicit source byte map required')
    result={}
    for name,data in values.items():
        archive.safe_path(name)
        if not isinstance(data,bytes):raise ValueError('Immutable source bytes required')
        result[name]=data
    return result


def prefix(ordinal,case_identity):
    journal._sha(case_identity,'case identity')
    if type(ordinal) is not int or not 0<=ordinal<8:raise ValueError('Eight ordered broker cases only')
    return ROOT_PREFIX+f'/case{ordinal:02d}-{case_identity[:16]}'


def restore(stored_files,*,expected_manifest_sha256,expected_prefix):
    files=_copy(stored_files);archive.safe_path(expected_prefix)
    raw=files[expected_prefix+'/manifest.json'];journal._sha(expected_manifest_sha256,'manifest')
    if (physical.sha(raw)!=expected_manifest_sha256
            or files[expected_prefix+'/HEAD']!=expected_manifest_sha256.encode()+b'\n'):
        raise ValueError('Independent inline archive manifest/HEAD differs')
    manifest=json.loads(raw)
    if (canonical(manifest)!=raw or manifest.get('schema')!=SCHEMA
            or manifest.get('prefix')!=expected_prefix or manifest.get('chunk_bytes')!=CHUNK_BYTES
            or manifest.get('execution_restart_authorized') is not False
            or manifest.get('scientific_admission_authorized') is not False):
        raise ValueError('Exact native-v2 inline archive manifest required')
    chunks=manifest['chunks'];expected=[expected_prefix+f'/chunk{i:04d}.b64' for i in range(len(chunks))]
    if set(files)!={expected_prefix+'/manifest.json',expected_prefix+'/HEAD',*expected}:
        raise ValueError('Exact inline stored inventory differs')
    payload=bytearray()
    for path,record in zip(expected,chunks,strict=True):
        data=files[path]
        if record!={'path':path,'stored_bytes':len(data),'stored_sha256':physical.sha(data)}:
            raise ValueError('Inline chunk receipt differs')
        try:decoded=base64.b64decode(data,validate=True)
        except Exception as error:raise ValueError('Invalid inline base64 chunk') from error
        if len(decoded)>CHUNK_BYTES:raise ValueError('Decoded inline chunk exceeds bound')
        payload.extend(decoded)
    if len(payload)!=manifest['source_bytes'] or physical.sha(payload)!=manifest['source_sha256']:
        raise ValueError('Inline payload identity differs')
    result={}
    offset=0
    for path,record in manifest['sources'].items():
        if (record.get('offset')!=offset or set(record)!={'offset','bytes','sha256'}
                or type(record['bytes']) is not int or record['bytes']<0):
            raise ValueError('Canonical contiguous source framing required')
        data=bytes(payload[offset:offset+record['bytes']]);offset+=record['bytes']
        if len(data)!=record['bytes'] or physical.sha(data)!=record['sha256']:
            raise ValueError('Restored source bytes differ')
        result[path]=data
    if offset!=len(payload):raise ValueError('Unreferenced inline payload suffix')
    return MappingProxyType(result)


def prepare_bundle(physical_files,journal_files,base_files,*,ordinal,
        expected_config_sha256,expected_last_checkpoint_sha256,
        expected_genesis_sha256,expected_pointer_sha256,
        expected_parent_sha,expected_parent_tree_sha,limits=Limits()):
    limits.validate();physical_files,journal_files,base_files=map(_copy,(physical_files,journal_files,base_files))
    pins={'config_sha256':expected_config_sha256,
        'last_checkpoint_sha256':expected_last_checkpoint_sha256,
        'genesis_sha256':expected_genesis_sha256,'pointer_sha256':expected_pointer_sha256}
    for name,value in pins.items():journal._sha(value,name)
    summary=archive._validated_maps(physical_files,journal_files,base_files,pins)
    target=prefix(ordinal,summary['case_identity'])
    sources={group+'/'+name:data for group,values in
        [('base',base_files),('journal',journal_files),('physical',physical_files)]
        for name,data in sorted(values.items())}
    if len(sources)!=len(base_files)+len(journal_files)+len(physical_files):
        raise ValueError('Source group/path collision')
    payload=bytearray();records={}
    for path,data in sorted(sources.items()):
        records[path]={'offset':len(payload),'bytes':len(data),'sha256':physical.sha(data)}
        payload.extend(data)
    if len(payload)>MAX_SOURCE_BYTES:raise ValueError('Case plus cumulative journal source cap exceeded')
    chunks=[];files={}
    for index,start in enumerate(range(0,len(payload),CHUNK_BYTES)):
        path=target+f'/chunk{index:04d}.b64';data=base64.b64encode(payload[start:start+CHUNK_BYTES])
        files[path]=data;chunks.append({'path':path,'stored_bytes':len(data),'stored_sha256':physical.sha(data)})
    manifest=canonical({'schema':SCHEMA,'mode':'ENGINEERING_ONLY','repository':REPO,'branch':BRANCH,
        'prefix':target,'ordinal':ordinal,'case_identity':summary['case_identity'],'pins':pins,
        'source_summary':summary,'sources':records,'source_bytes':len(payload),
        'source_sha256':physical.sha(payload),'chunk_bytes':CHUNK_BYTES,'chunks':chunks,
        'execution_restart_authorized':False,'scientific_admission_authorized':False})
    if len(manifest)>MANIFEST_RESERVE_BYTES:raise ValueError('Inline manifest reserve exhausted')
    files[target+'/manifest.json']=manifest;files[target+'/HEAD']=physical.sha(manifest).encode()+b'\n'
    if (len(files)>limits.files or sum(map(len,files.values()))>limits.stored_bytes
            or len(chunks)>math.ceil(MAX_SOURCE_BYTES/CHUNK_BYTES)):
        raise ValueError('Inline remote file/stored-byte cap exceeded')
    restored=restore(files,expected_manifest_sha256=physical.sha(manifest),expected_prefix=target)
    if restored!=sources:raise ValueError('Prepared exact inline source reconstruction differs')
    freeze=canonical({'schema':SCHEMA,'mode':'ENGINEERING_ONLY','repository':REPO,'branch':BRANCH,
        'broker_protocol':BROKER_PROTOCOL,'per_operation_response_reservations':dict(RESPONSE_RESERVATIONS),
        'ordinal':ordinal,'prefix':target,'parent':archive.git_sha(expected_parent_sha),
        'parent_tree':archive.git_sha(expected_parent_tree_sha),'limits':asdict(limits),
        'files':{path:{'bytes':len(data),'sha256':physical.sha(data),
            'blob':archive.git_object('blob',data)} for path,data in sorted(files.items())},
        'manifest_sha256':physical.sha(manifest),'single_inline_tree_request':True,
        'single_grouped_readback':True,'force':False,'automatic_retry':False,
        'execution_restart_authorized':False,'scientific_admission_authorized':False})
    return Bundle(ordinal,target,MappingProxyType(files),manifest,freeze,limits)


class Stopped(RuntimeError):pass


class DurableInvoker:
    """Persist each returned raw transport object before parsing it.

    ``persist`` receives the call ordinal, operation, exact canonical request
    bytes and the untouched result object.  It must durably save that object and
    return its canonical byte length and SHA256.  Any transport or persistence
    ambiguity permanently stops this adapter; callers cannot retry it.
    """
    def __init__(self,invoke,persist):
        if not callable(invoke) or not callable(persist):
            raise ValueError('Callable transport and durable receipt sink required')
        self.transport=invoke;self.persist=persist;self.stopped=False;self.records=[]

    def invoke(self,operation,params):
        if self.stopped:raise Stopped('Durable transport stopped; no retry')
        try:
            request=canonical(params) # preflight before the external call
        except BaseException as error:
            self.stopped=True;raise Stopped('Transport request is not canonical JSON') from error
        ordinal=len(self.records)
        try:
            result=self.transport(operation,params)
        except BaseException as error:
            self.stopped=True;raise Stopped('Transport response is uncertain; no retry') from error
        try:
            saved=self.persist(ordinal,operation,request,result)
        except BaseException as error:
            self.stopped=True;raise Stopped('Raw transport receipt persistence is uncertain; no retry') from error
        try:
            response=canonical(result)
            expected={'bytes':len(response),'sha256':hashlib.sha256(response).hexdigest()}
            if saved!=expected or not isinstance(result,dict):
                raise ValueError('Durable raw transport receipt differs')
        except BaseException as error:
            self.stopped=True;raise Stopped('Persisted transport response is invalid; no retry') from error
        self.records.append({'ordinal':ordinal,'operation':operation,
            'request_bytes':len(request),'request_sha256':hashlib.sha256(request).hexdigest(),
            'response_bytes':expected['bytes'],'response_sha256':expected['sha256']})
        return result


class Publisher:
    """One terminal-case publication; any uncertain call permanently stops it."""
    def __init__(self,bundle,invoke,*,expected_bundle_sha256,clock=time.monotonic):
        if not isinstance(bundle,Bundle) or bundle.sha256!=expected_bundle_sha256:
            raise ValueError('Independent immutable broker bundle pin differs')
        freeze=json.loads(bundle.freeze_bytes)
        if (canonical(freeze)!=bundle.freeze_bytes or freeze['limits']!=asdict(bundle.limits)
                or freeze.get('broker_protocol')!=BROKER_PROTOCOL
                or freeze.get('per_operation_response_reservations')!=dict(RESPONSE_RESERVATIONS)
                or set(freeze['files'])!=set(bundle.files)
                or any(freeze['files'][path]!={'bytes':len(data),'sha256':physical.sha(data),
                    'blob':archive.git_object('blob',data)} for path,data in bundle.files.items())):
            raise ValueError('Prepared inline broker bundle changed')
        restore(bundle.files,expected_manifest_sha256=freeze['manifest_sha256'],expected_prefix=bundle.prefix)
        self.bundle=bundle;self.freeze=freeze;self.invoke=invoke;self.clock=clock;self.started=clock()
        self.calls=self.request_bytes=self.response_bytes=0;self.attempted=self.stopped=self.update_attempted=False
        self.response_charged_bytes=self.unknown_response_bytes=self.unknown_response_count=0
        self.events=[]
        self.trees={};self.receipt=None

    def _call(self,operation,**params):
        if self.stopped:raise Stopped('Broker stopped; no retry')
        request=canonical(params);limits=self.bundle.limits
        reservation=RESPONSE_RESERVATIONS[operation]
        if (self.calls>=limits.calls or self.request_bytes+len(request)>limits.request_bytes
                or self.clock()-self.started>limits.seconds
                or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>limits.peak_rss_bytes):
            raise ValueError('Frozen broker call/request/time bound exhausted')
        if self.response_charged_bytes+reservation>limits.response_bytes:
            raise ValueError('Frozen broker response capacity cannot reserve operation reply')
        self.calls+=1;self.request_bytes+=len(request)
        self.response_charged_bytes+=reservation
        event={'call':self.calls,'operation':operation,'request_bytes':len(request),
            'request_sha256':physical.sha(request),'response_reserved_bytes':reservation,
            'response_charged_bytes':reservation,'response_unknown':True}
        self.events.append(event)
        try:
            result=self.invoke(operation,params);response=canonical(result)
        except BaseException:
            self.unknown_response_bytes+=reservation;self.unknown_response_count+=1
            raise
        self.response_bytes+=len(response);self.response_charged_bytes+=len(response)-reservation
        event.update(response_bytes=len(response),response_sha256=physical.sha(response),
            response_charged_bytes=len(response),response_unknown=False)
        if (len(response)>reservation or self.response_charged_bytes>limits.response_bytes
                or self.clock()-self.started>limits.seconds
                or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>limits.peak_rss_bytes):
            raise ValueError('Frozen broker response/time/RSS bound exhausted')
        if not isinstance(result,dict):raise ValueError('Object broker response required')
        return result

    def _get(self,path):return self._call('fetch',url='https://api.github.com/repos/'+REPO+'/git/'+path)

    def _head(self):
        value=self._get('ref/heads/'+quote(BRANCH,safe=''))
        if value.get('ref')!='refs/heads/'+BRANCH or value.get('object',{}).get('type')!='commit':
            raise ValueError('Broker branch identity/type differs')
        return archive.git_sha(value['object']['sha'])

    def _commit(self,sha):
        value=self._get('commits/'+archive.git_sha(sha))
        if value.get('sha')!=sha:raise ValueError('Broker commit readback differs')
        return {'tree':archive.git_sha(value['tree']['sha']),
            'parents':[archive.git_sha(parent['sha']) for parent in value['parents']]}

    def _tree(self,sha):
        sha=archive.git_sha(sha)
        if sha in self.trees:return self.trees[sha]
        value=self._get('trees/'+sha)
        if value.get('sha')!=sha or value.get('truncated') is not False:
            raise ValueError('Missing/truncated broker tree readback')
        result={};allowed={('040000','tree'),('100644','blob'),('100755','blob'),('120000','blob'),('160000','commit')}
        for row in value['tree']:
            name=archive.safe_path(row['path'])
            if '/' in name or name in result or (row['mode'],row['type']) not in allowed:
                raise ValueError('Broker tree entry differs')
            result[name]={'mode':row['mode'],'type':row['type'],'sha':archive.git_sha(row['sha'])}
        order=sorted(result,key=lambda name:(name+('/' if result[name]['type']=='tree' else '')).encode())
        raw=b''.join(result[name]['mode'].lstrip('0').encode()+b' '+name.encode()+b'\0'
            +bytes.fromhex(result[name]['sha']) for name in order)
        if archive.git_object('tree',raw)!=sha:raise ValueError('Exact broker tree content hash differs')
        self.trees[sha]=result;return result

    def _fresh(self,tree):
        for part in self.bundle.prefix.split('/'):
            row=self._tree(tree).get(part)
            if row is None:return
            if (row['mode'],row['type'])!=('040000','tree'):raise ValueError('Broker namespace ancestor differs')
            tree=row['sha']
        raise ValueError('Immutable broker namespace already exists')

    def _delta(self,before_sha,after_sha,changes):
        before={} if before_sha is None else self._tree(before_sha);after=self._tree(after_sha);groups={}
        for path,value in changes.items():
            first,sep,tail=path.partition('/');groups.setdefault(first,{})[tail if sep else '']=value
        if ({name:value for name,value in before.items() if name not in groups}
                != {name:value for name,value in after.items() if name not in groups}):
            raise ValueError('Broker candidate changed unrelated path')
        for first,remaining in groups.items():
            old,new=before.get(first),after.get(first)
            if '' in remaining:
                if len(remaining)!=1 or old is not None or new!={'mode':'100644','type':'blob','sha':remaining['']}:
                    raise ValueError('Broker leaf overwrite/content differs')
            else:
                if (new is None or (new['mode'],new['type'])!=('040000','tree')
                        or old is not None and (old['mode'],old['type'])!=('040000','tree')):
                    raise ValueError('Broker candidate directory differs')
                self._delta(None if old is None else old['sha'],new['sha'],remaining)

    def publish(self):
        if self.attempted or self.stopped:raise Stopped('One broker attempt only; no retry')
        self.attempted=True;candidate=None
        try:
            parent,parent_tree=self.freeze['parent'],self.freeze['parent_tree']
            if self._head()!=parent or self._commit(parent)['tree']!=parent_tree:
                raise ValueError('Frozen broker parent/tree conflicts')
            self._fresh(parent_tree)
            elements=[{'path':path,'mode':'100644','type':'blob','content':data.decode('ascii')}
                for path,data in sorted(self.bundle.files.items())]
            made=self._call('create_tree',repository_full_name=REPO,base_tree_sha=parent_tree,tree_elements=elements)
            tree=archive.git_sha(made['sha']);changes={path:pin['blob'] for path,pin in self.freeze['files'].items()}
            self._delta(parent_tree,tree,changes)
            made=self._call('create_commit',repository_full_name=REPO,parent_sha=parent,
                tree_sha=tree,message='Native v2 terminal case '+str(self.bundle.ordinal)+' '+self.bundle.sha256)
            candidate=archive.git_sha(made['sha'])
            if self._commit(candidate)!={'tree':tree,'parents':[parent]} or self._head()!=parent:
                raise ValueError('Broker candidate parent/tree or late head differs')
            self.update_attempted=True
            updated=self._call('update_ref',repository_full_name=REPO,branch_name=BRANCH,sha=candidate,force=False)
            if updated.get('success') is not True:raise ValueError('Unconfirmed broker fast-forward update')
            grouped=self._call('fetch_files',repository_full_name=REPO,ref=candidate,
                paths=sorted(self.bundle.files),encoding='base64')
            if set(grouped)!=set(self.bundle.files):raise ValueError('Grouped broker readback inventory differs')
            readback={}
            for path,data in self.bundle.files.items():
                row=grouped[path]
                if set(row)!={'sha','content'} or row['sha']!=changes[path]:
                    raise ValueError('Grouped broker readback blob differs')
                raw=base64.b64decode(row['content'],validate=True)
                if raw!=data:raise ValueError('Grouped broker readback bytes differ')
                readback[path]=raw
            original=restore(readback,expected_manifest_sha256=self.freeze['manifest_sha256'],
                expected_prefix=self.bundle.prefix)
            if self._head()!=candidate:raise ValueError('Broker post-publication head differs')
            self.receipt={'schema':SCHEMA,'ordinal':self.bundle.ordinal,'bundle_sha256':self.bundle.sha256,
                'broker_protocol':BROKER_PROTOCOL,
                'parent':parent,'commit':candidate,'tree':tree,'stored_files':len(readback),
                'stored_bytes':sum(map(len,readback.values())),'restored_source_files':len(original),
                'exact_tree_delta_verified':True,'single_inline_tree_request':True,
                'single_grouped_readback':True,'force':False,'automatic_retry':False,
                'execution_restart_authorized':False,'scientific_admission_authorized':False,
                'usage':self.usage()}
            return self.receipt
        except BaseException as error:
            self.stopped=True;self.receipt={'ordinal':self.bundle.ordinal,'candidate':candidate,
                'error':repr(error),'update_may_have_landed':self.update_attempted,
                'broker_protocol':BROKER_PROTOCOL,'bundle_sha256':self.bundle.sha256,
                'stored_bytes':sum(map(len,self.bundle.files.values())),
                'stored_bytes_conservative':True,
                'automatic_retry':False,'execution_restart_authorized':False,
                'scientific_admission_authorized':False,'usage':self.usage()}
            raise Stopped('Broker publication stopped without retry: '+str(error)) from error

    def usage(self):return {'calls':self.calls,'request_bytes':self.request_bytes,
        'response_bytes':self.response_bytes,'response_charged_bytes':self.response_charged_bytes,
        'unknown_response_bytes':self.unknown_response_bytes,'unknown_response_count':self.unknown_response_count,
        'elapsed_seconds':self.clock()-self.started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}


class CumulativeBroker:
    """Ordered eight-case accounting; any failure stops all later cases."""
    def __init__(self,invoke,*,clock=time.monotonic,limits=CumulativeLimits()):
        if limits!=CumulativeLimits():raise ValueError('Cumulative broker limits changed')
        self.invoke=invoke;self.clock=clock;self.started=clock();self.limits=limits
        self.receipts=[];self.failed_attempt=None;self.stopped=False

    def publish(self,bundle):
        if self.stopped:raise Stopped('Cumulative broker stopped; no retry')
        if bundle.ordinal!=len(self.receipts):raise ValueError('Terminal cases must publish in fixed order')
        prior=self.usage();case=bundle.limits
        if (prior['cases']+1>self.limits.cases or prior['calls']+case.calls>self.limits.calls
                or prior['request_bytes']+case.request_bytes>self.limits.request_bytes
                or prior['response_charged_bytes']+case.response_bytes>self.limits.response_bytes
                or prior['stored_bytes']+case.stored_bytes>self.limits.stored_bytes
                or prior['elapsed_seconds']+case.seconds>self.limits.seconds
                or prior['peak_rss_bytes']>self.limits.peak_rss_bytes):
            self.stopped=True;raise Stopped('Cannot reserve next broker case inside cumulative bounds')
        publisher=Publisher(bundle,self.invoke,expected_bundle_sha256=bundle.sha256,clock=self.clock)
        try:receipt=publisher.publish()
        except BaseException:
            self.failed_attempt=publisher.receipt;self.stopped=True;raise
        totals=self.usage(extra=receipt)
        if (totals['cases']>self.limits.cases or totals['calls']>self.limits.calls
                or totals['request_bytes']>self.limits.request_bytes
                or totals['response_charged_bytes']>self.limits.response_bytes
                or totals['stored_bytes']>self.limits.stored_bytes
                or totals['elapsed_seconds']>self.limits.seconds
                or totals['peak_rss_bytes']>self.limits.peak_rss_bytes):
            self.failed_attempt=receipt;self.stopped=True
            raise Stopped('Cumulative broker budget exhausted; no next case')
        self.receipts.append(receipt);return receipt

    def usage(self,extra=None):
        rows=[*self.receipts,*([] if self.failed_attempt is None else [self.failed_attempt]),
            *([] if extra is None else [extra])]
        return {'cases':len(rows),'calls':sum(r['usage']['calls'] for r in rows),
            'request_bytes':sum(r['usage']['request_bytes'] for r in rows),
            'response_bytes':sum(r['usage']['response_bytes'] for r in rows),
            'response_charged_bytes':sum(r['usage']['response_charged_bytes'] for r in rows),
            'unknown_response_bytes':sum(r['usage']['unknown_response_bytes'] for r in rows),
            'unknown_response_count':sum(r['usage']['unknown_response_count'] for r in rows),
            'stored_bytes':sum(r['stored_bytes'] for r in rows),
            'elapsed_seconds':self.clock()-self.started,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
