"""Write-ahead case consumption, immutable artifacts and non-resumable leases.

A Store supplies read()->Checkpoint and publish(expected_revision, document).
It must enforce CAS against durable, independently readable storage. Only the
engineering DirectoryStore is implemented here. A scientific store must also
verify its externally published freeze/allocation via verify_execution().
Scientific artifact publication/readback and prior completed evidence are
separate mandatory adapter methods; local scratch never supplies durability.
Never reconstruct a lease from disk or turn an interrupted case into EMPTY.
"""
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import re
import time
import uuid

from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest, _sha

SCHEMA = 'radio-whole-cadence-consumption-v1'
_TOKEN = object()
ZERO = '0' * 64
GROUP_LEDGER_FINALIZATION_RESERVE = 512*1024
GROUP_MAX_LEDGER_SNAPSHOT = 128*1024
BINDING_KEYS = {'case_identity', 'plan_sha256', 'context_sha256',
                'source_contract_sha256', 'noise_law_sha256', 'role'}
CAPS = {'active_milliseconds': 7200000, 'evidence_bytes': 1024**3,
        'ledger_reserve_bytes': 8*1024**2, 'rss_bytes': 512*1024**2,
        'modelled_array_bytes': 256*1024**2}


def clone(value):
    return json.loads(canonical(value))


def validate_manifest(m):
    fields = {'schema', 'mode', 'namespace', 'execution_binding_sha256',
              'allocation_sha256', 'cases', 'caps', 'required_artifacts'}
    if 'artifact_groups' in m: fields.add('artifact_groups')
    if set(m) != fields:
        raise ValueError('Exact consumption manifest required')
    if m['schema'] != SCHEMA or m['mode'] not in ('engineering', 'scientific') or not m['namespace']:
        raise ValueError('Consumption manifest domain changed')
    for k in ('execution_binding_sha256', 'allocation_sha256'):
        _sha(m[k], k)
    if set(m['caps']) != set(CAPS) or any(type(v) is not int or not 0 < v <= CAPS[k]
                                         for k,v in m['caps'].items()):
        raise ValueError('Finite positive bounded integer caps required')
    if m['caps']['ledger_reserve_bytes'] >= m['caps']['evidence_bytes']:
        raise ValueError('No artifact capacity remains')
    if not m['cases'] or len(m['cases']) > 151:
        raise ValueError('A bounded ordered case inventory is required')
    ids = set()
    for c in m['cases']:
        if set(c) != BINDING_KEYS:
            raise ValueError('Exact case binding required')
        for k,v in c.items():
            if k != 'role': _sha(v,k)
        if c['role'] not in ('calibration','evaluation','engineering') or c['case_identity'] in ids:
            raise ValueError('Duplicate case or unsupported role')
        ids.add(c['case_identity'])
    if m['mode'] == 'scientific' and [c['role'] for c in m['cases']] != ['calibration']*127+['evaluation']*24:
        raise ValueError('Scientific allocation requires the ordered 127/24 inventory')
    if m['mode'] == 'engineering' and any(c['role'] != 'engineering' for c in m['cases']):
        raise ValueError('Engineering ledger cannot consume scientific roles')
    names = m['required_artifacts']
    if not names or len(names) != len(set(names)):
        raise ValueError('Distinct required artifacts needed')
    for name in names: artifact_name(name)
    if 'artifact_groups' in m:
        groups=m['artifact_groups']
        if m['mode']!='engineering' or not isinstance(groups,dict) or len(groups)!=1:
            raise ValueError('One engineering-only dynamic artifact group required')
        if m['caps']['ledger_reserve_bytes']<=GROUP_LEDGER_FINALIZATION_RESERVE:
            raise ValueError('Dynamic journal needs its internal closure reserve')
        for label,g in groups.items():
            if (not isinstance(label,str) or not re.fullmatch('[a-z][a-z0-9_]{0,31}',label)
                    or set(g)!={'prefix','seal','max_files','reserved_artifacts','binding_sha256','failure_finalization_milliseconds'}
                    or not re.fullmatch('[a-z][a-z0-9]{0,24}-',g['prefix'])
                    or type(g['max_files']) is not int or not 1<=g['max_files']<=1024
                    or not isinstance(g['reserved_artifacts'],dict) or g['seal'] not in g['reserved_artifacts']):
                raise ValueError('Bounded engineering group policy required')
            if type(g['failure_finalization_milliseconds']) is not int or not 0<g['failure_finalization_milliseconds']<=5000:
                raise ValueError('Bounded failure-only finalization window required')
            _sha(g['binding_sha256'],'group binding')
            if any(n.startswith(g['prefix']) for n in names):
                raise ValueError('Group prefix overlaps fixed artifacts')
            for name,amount in g['reserved_artifacts'].items():
                if name not in names or type(amount) is not int or not 0<amount<=262144:
                    raise ValueError('Reserved closure artifact must be fixed and bounded')
    return m


def group_budget(manifest, artifacts, cap):
    """Charge every file plus all still-unused closure reservations."""
    groups=manifest.get('artifact_groups',{})
    if not groups:return
    allowed=set(manifest['required_artifacts']);held=0
    for g in groups.values():
        members={n for n in artifacts if n.startswith(g['prefix'])}
        if len(members)>g['max_files']:raise ValueError('Dynamic artifact count exhausted')
        allowed.update(members)
        for name,amount in g['reserved_artifacts'].items():
            if name in artifacts:
                if artifacts[name]['size']>amount:raise ValueError('Closure artifact exceeds reservation')
            else:held+=amount
    if set(artifacts)-allowed:raise ValueError('Artifact outside fixed inventory and bounded groups')
    if sum(v['size'] for v in artifacts.values())+held>cap:
        raise ValueError('Case budget would consume reserved closure bytes')


def required_inventory(manifest, artifacts):
    required=set(manifest['required_artifacts'])
    if not manifest.get('artifact_groups'):return set(artifacts)==required
    allowed=set(required)
    for g in manifest['artifact_groups'].values():
        allowed.update(n for n in artifacts if n.startswith(g['prefix']))
    return required<=set(artifacts)<=allowed


def group_seal(checkpoint, label, *, complete):
    if type(complete) is not bool:raise ValueError('Explicit group completion required')
    manifest=checkpoint.document['manifest'];g=manifest['artifact_groups'][label]
    case=replay(checkpoint.document)['cases'][-1]
    members={n:{'size':r['size'],'sha256':r['sha256']} for n,r in case['artifacts'].items() if n.startswith(g['prefix'])}
    return {'schema':'radio-engineering-artifact-group-v1','case_identity':case['binding']['case_identity'],
        'policy_sha256':digest(g),'complete':complete,'artifacts':members,
        'stored_bytes':sum(r['size'] for r in members.values()),'scientific_admission_authorized':False}


def artifact_name(name):
    if (not isinstance(name,str) or not name or name in ('.','..') or '/' in name
            or '\\' in name or len(name)>160 or any(ord(c)<32 for c in name)):
        raise ValueError('Plain artifact filename required')
    return name


def genesis(manifest):
    manifest = clone(validate_manifest(manifest))
    return {'schema':SCHEMA, 'manifest':manifest, 'manifest_sha256':digest(manifest), 'events':[]}


def replay(document):
    """Validate an append-only state machine; incomplete is never a maximum."""
    if set(document) != {'schema','manifest','manifest_sha256','events'} or document['schema'] != SCHEMA:
        raise ValueError('Wrong consumption ledger schema')
    m = validate_manifest(document['manifest'])
    if digest(m) != document['manifest_sha256']:
        raise ValueError('Consumption manifest changed')
    if len(canonical(document)) > m['caps']['ledger_reserve_bytes']:
        raise ValueError('Ledger evidence reservation exhausted')
    state = {'cases':[], 'reserved_milliseconds':0, 'reserved_artifact_bytes':0,
             'archived_artifact_bytes':0, 'head':ZERO, 'attempt_failed':False}
    for i, record in enumerate(document['events']):
        if set(record) != {'index','previous','event','sha256'}:
            raise ValueError('Invalid event record')
        if (type(record['index']) is not int or record['index'] != i
                or record['previous'] != state['head']
                or digest({k:v for k,v in record.items() if k!='sha256'}) != record['sha256']):
            raise ValueError('Journal chain changed')
        e=record['event']; kind=e.get('kind')
        last=state['cases'][-1] if state['cases'] else None
        if state['attempt_failed']:
            raise ValueError('Attempt already closed after failure')
        if kind == 'consume':
            if set(e) != {'kind','binding','milliseconds','artifact_bytes','nonce'}:
                raise ValueError('Consumption fields changed')
            if last and last['status'] != 'completed':
                raise ValueError('Prior case incomplete; no continuation')
            ordinal=len(state['cases'])
            if ordinal>=len(m['cases']) or e['binding']!=m['cases'][ordinal]:
                raise ValueError('Case order, identity or plan binding changed')
            for k in ('milliseconds','artifact_bytes'):
                if type(e[k]) is not int or e[k]<=0: raise ValueError('Positive integer reservation required')
            if str(uuid.UUID(e['nonce'])) != e['nonce']:
                raise ValueError('Process-local nonce changed')
            state['reserved_milliseconds']+=e['milliseconds']
            state['reserved_artifact_bytes']+=e['artifact_bytes']
            group_budget(m,{},e['artifact_bytes'])
            if (state['reserved_milliseconds']>m['caps']['active_milliseconds']
                    or state['reserved_artifact_bytes']+m['caps']['ledger_reserve_bytes']>m['caps']['evidence_bytes']):
                raise ValueError('Cumulative resource reservation exhausted')
            state['cases'].append({'binding':e['binding'],'nonce':e['nonce'],
                'milliseconds':e['milliseconds'],'artifact_bytes':e['artifact_bytes'],
                'status':'consumed','artifacts':{},'rng_started':False,
                'consumption_event_sha256':record['sha256']})
        else:
            if not last or e.get('nonce')!=last['nonce'] or last['status'] in ('completed','failed'):
                raise ValueError('No active case for event')
            if kind == 'rng_start':
                if set(e)!={'kind','nonce','plan_sha256'} or last['rng_started'] or e['plan_sha256']!=last['binding']['plan_sha256']:
                    raise ValueError('RNG already started or plan changed')
                if m['mode']!='scientific':raise ValueError('Engineering cannot start proposed Gaussian RNG')
                last['rng_started']=True;last['status']='started'
            elif kind == 'artifact':
                fields={'kind','nonce','name','size','sha256'}
                if m['mode']=='scientific' or 'publication' in e:fields.add('publication')
                if set(e)!=fields:raise ValueError('Artifact fields changed')
                name=artifact_name(e['name']);_sha(e['sha256'],'artifact')
                if any(g['seal'] in last['artifacts'] and name.startswith(g['prefix'])
                       for g in m.get('artifact_groups',{}).values()):
                    raise ValueError('Sealed dynamic group cannot append files')
                if name in last['artifacts'] or type(e['size']) is not int or e['size']<0:
                    raise ValueError('Duplicate artifact or invalid length')
                if m['mode']=='scientific' and not last['rng_started']:
                    raise ValueError('Scientific artifact before renderer start')
                last['artifacts'][name]={'size':e['size'],'sha256':e['sha256']}
                if 'publication' in e:
                    pub=e['publication']
                    if (set(pub)!={'location','revision','sha256'} or not pub['location']
                            or not pub['revision'] or pub['sha256']!=e['sha256']):
                        raise ValueError('External artifact publication differs')
                    last['artifacts'][name]['publication']=pub
                used=sum(v['size'] for v in last['artifacts'].values())
                group_budget(m,last['artifacts'],last['artifact_bytes'])
                if used>last['artifact_bytes']:raise ValueError('Case evidence reservation exhausted')
                state['archived_artifact_bytes']+=e['size']
            elif kind == 'finish':
                if set(e)!={'kind','nonce','outcome','elapsed_milliseconds','reason'} or e['outcome'] not in ('completed','failed'):
                    raise ValueError('Completion fields changed')
                elapsed=e['elapsed_milliseconds']
                if type(elapsed) is not int or elapsed<0 or not isinstance(e['reason'],str):
                    raise ValueError('Invalid completion accounting')
                if e['outcome']=='completed':
                    if (not required_inventory(m,last['artifacts']) or elapsed>last['milliseconds']
                            or (m['mode']=='scientific' and not last['rng_started'])):
                        raise ValueError('Incomplete evidence/time/renderer cannot complete')
                last['status']=e['outcome'];last['elapsed_milliseconds']=elapsed
                state['attempt_failed']=e['outcome']=='failed'
            else:
                raise ValueError('Unknown consumption event')
        state['head']=record['sha256']
    return state


@dataclass(frozen=True)
class Checkpoint:
    document: dict
    revision: str
    location: dict


def append(document,event):
    state=replay(document);out=clone(document)
    row={'index':len(out['events']),'previous':state['head'],'event':clone(event)}
    row['sha256']=digest(row);out['events'].append(row);replay(out)
    return out


def publish(store,before,event):
    after=append(before.document,event)
    store.publish(before.revision,after)
    check=store.read()
    if (check.revision==before.revision or check.document!=after or check.location!=before.location):
        raise ValueError('Publication/readback ambiguous; permission remains closed')
    return check


def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def durable_write(path,payload):
    with Path(path).open('xb') as stream:
        if stream.write(payload)!=len(payload):raise OSError('Short evidence write')
        stream.flush();os.fsync(stream.fileno())
    sync_dir(Path(path).parent)


class DirectoryStore:
    """Atomic local engineering store with retained immutable revisions.

    This is NOT an external scientific publication adapter. Copying this store
    does not create another allocation, nor does a local digest prove GitHub.
    """
    def __init__(self,path): self.path=Path(path)

    @classmethod
    def create(cls,path,manifest):
        if manifest['mode']!='engineering':raise ValueError('Local store is engineering-only')
        document=genesis(manifest)
        if manifest.get('artifact_groups') and len(canonical(document))+65+GROUP_LEDGER_FINALIZATION_RESERVE>manifest['caps']['ledger_reserve_bytes']:
            raise ValueError('Genesis would consume journal closure reserve')
        store=cls(path);store.path.mkdir(parents=True,exist_ok=False)
        (store.path/'revisions').mkdir();sync_dir(store.path.parent)
        revision=digest(document)
        durable_write(store.path/'revisions'/revision,canonical(document))
        durable_write(store.path/'HEAD',revision.encode()+b'\n')
        durable_write(store.path/'LOCK',b'')
        return store

    def read(self):
        raw=(self.path/'HEAD').read_bytes()
        if len(raw)!=65 or not raw.endswith(b'\n'):raise ValueError('Torn store head')
        revision=raw[:-1].decode();_sha(revision,'store head')
        data=(self.path/'revisions'/revision).read_bytes();doc=json.loads(data)
        if canonical(doc)!=data or digest(doc)!=revision:raise ValueError('Stored revision changed')
        replay(doc)
        if doc['manifest']['mode']!='engineering':raise ValueError('Local store is engineering-only')
        return Checkpoint(doc,revision,{'kind':'local-engineering','path':str(self.path.resolve())})

    def publish(self,expected_revision,document):
        with (self.path/'LOCK').open('rb') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            before=self.read()
            if before.revision!=expected_revision:raise ValueError('Store CAS conflict')
            if (document['manifest']!=before.document['manifest']
                    or document['events'][:-1]!=before.document['events']
                    or len(document['events'])!=len(before.document['events'])+1):
                raise ValueError('Store only appends one event; no reset/refund')
            replay(document);self.check_publication_capacity(document);revision=digest(document)
            durable_write(self.path/'revisions'/revision,canonical(document))
            temporary=self.path/('HEAD.'+str(uuid.uuid4()))
            durable_write(temporary,revision.encode()+b'\n')
            os.replace(temporary,self.path/'HEAD');sync_dir(self.path)

    def check_publication_capacity(self,document):
        m=document['manifest']
        if not m.get('artifact_groups'):return
        raw=canonical(document)
        if len(raw)>GROUP_MAX_LEDGER_SNAPSHOT:raise ValueError('Dynamic journal snapshot bound exhausted')
        event=document['events'][-1]['event'];reserved={n for g in m['artifact_groups'].values() for n in g['reserved_artifacts']}
        closing=event['kind']=='finish' or event['kind']=='artifact' and event['name'] in reserved
        used=0
        for p in self.path.rglob('*'):
            if p.is_symlink():raise ValueError('Symlink in journal inventory')
            if p.is_file():used+=p.stat().st_size
            elif not p.is_dir():raise ValueError('Nonregular journal inventory')
        held=0 if closing else GROUP_LEDGER_FINALIZATION_RESERVE
        # All original revisions plus the transient new HEAD file are charged.
        if used+len(raw)+65+held>m['caps']['ledger_reserve_bytes']:
            raise ValueError('Cumulative journal history would consume closure reserve')


def consume(store,*,expected_revision,expected_manifest_sha256,binding,
            milliseconds,artifact_bytes,directory,clock=time.monotonic):
    before=store.read();replay(before.document)
    if before.document['manifest'].get('artifact_groups'):
        from .whole_cadence_event_store_radio import EventDirectoryStore
        if type(store) not in (DirectoryStore,EventDirectoryStore):
            raise ValueError('Dynamic groups currently qualify only explicit local engineering stores')
    if before.revision!=expected_revision or before.document['manifest_sha256']!=expected_manifest_sha256:
        raise ValueError('Independent publication checkpoint differs')
    if before.document['manifest']['mode']=='scientific' or before.location.get('kind')=='github-published-engineering':
        if before.document['manifest']['mode']=='scientific' and before.location.get('kind')!='github-published-scientific':
            raise ValueError('External scientific store required')
        store.verify_execution(before.document['manifest'])
        if any(c['status']=='completed' for c in replay(before.document)['cases']):
            store.verify_completed_evidence(before)
    started=clock()
    after=publish(store,before,{'kind':'consume','binding':binding,'milliseconds':milliseconds,
        'artifact_bytes':artifact_bytes,'nonce':str(uuid.uuid4())})
    # Consumption stays charged even if local allocation fails or the process dies.
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False);sync_dir(directory.parent)
    return Lease(store,after,directory,clock,started,_TOKEN)


class Lease:
    def __init__(self,store,checkpoint,directory,clock,started,token=None):
        if token is not _TOKEN:raise ValueError('Only a newly published consumption can create a lease')
        self.store=store;self.checkpoint=checkpoint;self.directory=directory
        self.clock=clock;self.started=started;self.closed=False;self.broken=False
        self.case=clone(replay(checkpoint.document)['cases'][-1])
        self._case_sha=digest(self.case)
        self.manifest=clone(checkpoint.document['manifest']);self.manifest_sha=digest(self.manifest)
        self._elapsed=0
        self.failure_finalization_started=None

    def _current(self):
        if self.closed or self.broken:raise ValueError('Lease is closed or uncertain')
        now=self.store.read()
        if (now!=self.checkpoint or digest(self.manifest)!=self.manifest_sha
                or digest(self.case)!=self._case_sha
                or self.manifest_sha!=now.document['manifest_sha256']):
            self.broken=True;raise ValueError('Execution lease/checkpoint changed')
        return now

    def _event(self,event):
        before=self._current()
        try:self.checkpoint=publish(self.store,before,{'nonce':self.case['nonce'],**event})
        except BaseException:
            self.broken=True;raise

    def budget(self,modelled_array_bytes=0):
        if self.closed or self.broken:raise ValueError('Lease is closed or uncertain')
        if self.failure_finalization_started is not None:raise ValueError('Failure finalization cannot resume work')
        if digest(self.case)!=self._case_sha or digest(self.manifest)!=self.manifest_sha:
            self.broken=True;raise ValueError('Lease case or caps changed')
        elapsed=(self.clock()-self.started)*1000
        if not math.isfinite(elapsed) or elapsed<self._elapsed or elapsed>self.case['milliseconds']:
            raise ValueError('Reserved active-time budget exhausted or clock regressed')
        self._elapsed=elapsed
        if type(modelled_array_bytes) is not int or not 0<=modelled_array_bytes<=self.manifest['caps']['modelled_array_bytes']:
            raise ValueError('Modelled array capacity exceeded')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>self.manifest['caps']['rss_bytes']:
            raise ValueError('RSS capacity exceeded')
        return elapsed

    def begin_gaussian(self,plan):
        self.budget();before=self._current();m=before.document['manifest']
        if m['mode']!='scientific' or before.location.get('kind')!='github-published-scientific':
            raise ValueError('PROPOSED_NOT_ACTIVATED: scientific publication and allocation required')
        r=plan.record();c=r['case']
        binding={'case_identity':c['identity'],'plan_sha256':r['plan_sha256'],
            'context_sha256':c['context_sha256'],'source_contract_sha256':c['source_contract_sha256'],
            'noise_law_sha256':c['noise_law_sha256'],'role':c['role']}
        if binding!=self.case['binding']:raise ValueError('Draw/consumption binding differs')
        # External adapter checks read-back freeze, current transitive files,
        # runtime binaries and exact proposal/allocation immediately before RNG.
        self.store.verify_execution(m)
        if any(c['status']=='completed' for c in replay(before.document)['cases']):
            self.store.verify_completed_evidence(before)
        self._event({'kind':'rng_start','plan_sha256':r['plan_sha256']})
        self.budget()
        return {'manifest_sha256':self.manifest_sha,
                'consumption_event_sha256':self.case['consumption_event_sha256'],
                'rng_start_revision':self.checkpoint.revision,
                'execution_binding_sha256':m['execution_binding_sha256'],
                'allocation_sha256':m['allocation_sha256']}

    def write_artifact(self,name,payload):
        self.budget();return self._write_artifact(name,payload)

    def write_failure_artifact(self,name,payload):
        groups=self.manifest.get('artifact_groups',{})
        matching=[g for g in groups.values() if name in g['reserved_artifacts']]
        if self.manifest['mode']!='engineering' or len(matching)!=1:
            raise ValueError('Only prospectively reserved engineering closure files allowed')
        now=self.clock()
        if self.failure_finalization_started is None:self.failure_finalization_started=now
        elapsed=(now-self.failure_finalization_started)*1000
        if not math.isfinite(elapsed) or elapsed<0 or elapsed>matching[0]['failure_finalization_milliseconds']:
            raise ValueError('Failure finalization window exhausted')
        self._write_artifact(name,payload)
        elapsed=(self.clock()-self.failure_finalization_started)*1000
        if not math.isfinite(elapsed) or elapsed<0 or elapsed>matching[0]['failure_finalization_milliseconds']:
            self.broken=True;raise ValueError('Failure finalization exceeded its fixed window')

    def _write_artifact(self,name,payload):
        self._current();name=artifact_name(name)
        if not isinstance(payload,bytes):raise ValueError('Immutable artifact bytes required')
        state=replay(self.checkpoint.document)['cases'][-1]
        if any(g['seal'] in state['artifacts'] and name.startswith(g['prefix'])
               for g in self.manifest.get('artifact_groups',{}).values()):
            raise ValueError('Sealed dynamic group cannot append files')
        actual={p.name for p in self.directory.iterdir()}
        if actual!=set(state['artifacts']):raise ValueError('Unregistered/missing partial artifact; case incomplete')
        if name in actual:raise ValueError('Artifact already exists; no overwrite')
        if sum(v['size'] for v in state['artifacts'].values())+len(payload)>self.case['artifact_bytes']:
            raise ValueError('Case evidence reservation exhausted')
        group_budget(self.manifest,{**state['artifacts'],name:{'size':len(payload)}},self.case['artifact_bytes'])
        event={'kind':'artifact','name':name,'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        if self.manifest.get('artifact_groups'):
            self.store.check_publication_capacity(append(self.checkpoint.document,{'nonce':self.case['nonce'],**event}))
        try:
            durable_write(self.directory/name,payload)
            if self.manifest['mode']=='scientific' or self.checkpoint.location.get('kind')=='github-published-engineering':
                publication=self.store.publish_artifact(self._current(),name,payload)
                if (publication.get('sha256')!=event['sha256']
                        or self.store.read_artifact(publication)!=payload):
                    raise ValueError('External artifact bytes not verified; case incomplete')
                event['publication']=publication
            self._event(event)
        except BaseException:
            self.broken=True;raise

    def finish(self,outcome='completed',reason=''):
        if outcome=='completed':
            self.budget();verify_archive(self.checkpoint,self.directory,case_index=len(replay(self.checkpoint.document)['cases'])-1,require_complete_groups=True)
            if self.manifest['mode']=='scientific' or self.checkpoint.location.get('kind')=='github-published-engineering':
                current=replay(self.checkpoint.document)['cases'][-1]
                for name,meta in current['artifacts'].items():
                    if self.store.read_artifact(meta['publication'])!=(self.directory/name).read_bytes():
                        raise ValueError('External artifact missing/changed before completion')
            # Include external evidence verification, not only the earlier work.
            # Final commit/readback latency remains separately measured by the
            # caller; this event cannot attest its own future publication time.
            self.budget()
        elapsed=(self.clock()-self.started)*1000
        if not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid finish clock')
        self._event({'kind':'finish','outcome':outcome,'elapsed_milliseconds':math.ceil(elapsed),'reason':str(reason)})
        self.closed=True
        return self.checkpoint


def verify_archive(checkpoint,directory,*,case_index,require_complete_groups=False):
    state=replay(checkpoint.document);case=state['cases'][case_index];directory=Path(directory)
    if not directory.is_dir() or directory.is_symlink():raise ValueError('Archive directory missing or symlinked')
    if {p.name for p in directory.iterdir()}!=set(case['artifacts']):
        raise ValueError('Unregistered, missing or partial archive')
    for name,rec in case['artifacts'].items():
        p=directory/name
        if p.is_symlink() or not p.is_file():raise ValueError('Archive must contain regular immutable files')
        data=p.read_bytes()
        if len(data)!=rec['size'] or hashlib.sha256(data).hexdigest()!=rec['sha256']:
            raise ValueError('Archive bytes differ')
    for label,g in checkpoint.document['manifest'].get('artifact_groups',{}).items():
        if g['seal'] not in case['artifacts']:
            if require_complete_groups:raise ValueError('Dynamic group seal missing')
            continue
        raw=(directory/g['seal']).read_bytes();seal=json.loads(raw)
        members={n:{'size':r['size'],'sha256':r['sha256']} for n,r in case['artifacts'].items() if n.startswith(g['prefix'])}
        expected={'schema':'radio-engineering-artifact-group-v1','case_identity':case['binding']['case_identity'],
            'policy_sha256':digest(g),'complete':seal.get('complete'),'artifacts':members,
            'stored_bytes':sum(r['size'] for r in members.values()),'scientific_admission_authorized':False}
        if (type(seal.get('complete')) is not bool or seal!=expected or canonical(seal)!=raw
                or require_complete_groups and seal['complete'] is not True):
            raise ValueError('Dynamic group seal inventory or completion differs')
    return {'case_identity':case['binding']['case_identity'],'status':case['status'],
        'artifact_count':len(case['artifacts']),'artifact_bytes':sum(v['size'] for v in case['artifacts'].values()),
        'execution_restart_authorized':False,'can_read_complete_evidence':case['status']=='completed',
        'incomplete_is_statistical_empty':False}
