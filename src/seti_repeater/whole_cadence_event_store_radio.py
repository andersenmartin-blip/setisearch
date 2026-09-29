"""Fresh local engineering event store preserving every original journal revision.

All immutable events AND pointer versions count. Read-only recovery cannot
create a publisher or lease. Existing full-snapshot stores remain untouched.
"""
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
from types import MappingProxyType
import uuid

from . import whole_cadence_journal_radio as j
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest

SCHEMA='radio-local-engineering-event-store-v1'
MAX_FILES=4096
MAX_EVENTS=1536
_TOKEN=object()


def inventory(path):
    path=Path(path)
    if path.is_symlink() or not path.is_dir():raise ValueError('Regular event store required')
    files={};size=0
    for p in path.rglob('*'):
        if p.is_symlink():raise ValueError('Symlink in event journal')
        if p.is_file():
            size+=p.stat().st_size
            if size>j.CAPS['ledger_reserve_bytes'] or len(files)>=MAX_FILES:
                raise ValueError('Event journal hard inventory bound exceeded')
            files[p.relative_to(path).as_posix()]=p.read_bytes()
        elif not p.is_dir():raise ValueError('Nonregular journal member')
    return files


def load(raw):
    value=json.loads(raw)
    if canonical(value)!=raw:raise ValueError('Noncanonical event journal bytes')
    return value


def pointer(genesis_sha,doc,last_event_sha,previous_pointer_sha):
    return canonical({'schema':SCHEMA,'genesis_sha256':genesis_sha,
        'event_count':len(doc['events']),'revision_sha256':digest(doc),
        'revision_bytes':len(canonical(doc)),'last_event_sha256':last_event_sha,
        'previous_pointer_sha256':previous_pointer_sha,'execution_restart_authorized':False})


@dataclass(frozen=True)
class History:
    genesis_sha256:str
    pointer_sha256:str
    revision_bytes:tuple
    files:object
    orphan_paths:tuple

    def summary(self):
        return {'versions':len(self.revision_bytes),'stored_bytes':sum(map(len,self.files.values())),
            'original_revision_bytes':sum(map(len,self.revision_bytes)),
            'latest_revision_sha256':j.hashlib.sha256(self.revision_bytes[-1]).hexdigest(),
            'pointer_sha256':self.pointer_sha256,'genesis_sha256':self.genesis_sha256,
            'orphan_paths':list(self.orphan_paths),'execution_restart_authorized':False,
            'scientific_admission_authorized':False}


def restore(files,*,expected_genesis_sha256,expected_pointer_sha256,allow_orphans=False):
    files=dict(files);j._sha(expected_genesis_sha256,'genesis');j._sha(expected_pointer_sha256,'pointer')
    if len(files)>MAX_FILES or sum(map(len,files.values()))>j.CAPS['ledger_reserve_bytes']:
        raise ValueError('Event store hard bound exceeded')
    head=files['HEAD']
    if head!=expected_pointer_sha256.encode()+b'\n':raise ValueError('Independent current pointer differs')
    genesis=files['genesis.json'];doc=load(genesis);j.replay(doc)
    if (digest(doc)!=expected_genesis_sha256 or doc['events'] or doc['manifest']['mode']!='engineering'
            or not doc['manifest'].get('artifact_groups')):
        raise ValueError('Exact engineering group genesis required')
    pointers=sorted(n for n in files if re.fullmatch(r'pointers/[0-9]{4}\.json',n))
    matches=[n for n in pointers if j.hashlib.sha256(files[n]).hexdigest()==expected_pointer_sha256]
    if len(matches)!=1:raise ValueError('Unique current pointer version required')
    final=load(files[matches[0]]);count=final.get('event_count')
    if type(count) is not int or not 0<=count<=MAX_EVENTS or matches[0]!=f'pointers/{count:04d}.json':
        raise ValueError('Bounded pointer count required')
    used={'HEAD','LOCK','genesis.json'};previous=j.ZERO;last_event=j.ZERO;revisions=[]
    for index in range(count+1):
        if index:
            name=f'events/{index-1:04d}.json';raw=files[name];row=load(raw)
            if (set(row)!={'schema','index','before_revision_sha256','after_revision_sha256','after_revision_bytes','previous_event_sha256','record'}
                    or row['schema']!=SCHEMA or row['index']!=index-1
                    or row['before_revision_sha256']!=digest(doc) or row['previous_event_sha256']!=last_event):
                raise ValueError('Event chain differs')
            following=j.append(doc,row['record']['event']);encoded=canonical(following)
            if (following['events'][-1]!=row['record'] or j.hashlib.sha256(encoded).hexdigest()!=row['after_revision_sha256']
                    or len(encoded)!=row['after_revision_bytes'] or len(encoded)>j.GROUP_MAX_LEDGER_SNAPSHOT):
                raise ValueError('Original revision identity differs')
            doc=following;last_event=j.hashlib.sha256(raw).hexdigest();used.add(name)
        name=f'pointers/{index:04d}.json';raw=files[name]
        if raw!=pointer(expected_genesis_sha256,doc,last_event,previous):raise ValueError('Original pointer history differs')
        previous=j.hashlib.sha256(raw).hexdigest();used.add(name);revisions.append(canonical(doc))
    if previous!=expected_pointer_sha256 or files.get('LOCK')!=b'':raise ValueError('Current pointer or lock changed')
    orphans=tuple(sorted(set(files)-used))
    if orphans and not allow_orphans:raise ValueError('Uncommitted event journal members')
    if sum(map(len,files.values()))>doc['manifest']['caps']['ledger_reserve_bytes']:
        raise ValueError('Complete event/pointer inventory exceeds reservation')
    return History(expected_genesis_sha256,expected_pointer_sha256,tuple(revisions),MappingProxyType(files),orphans)


def read_history(path,*,expected_genesis_sha256,expected_pointer_sha256,allow_orphans=False):
    return restore(inventory(path),expected_genesis_sha256=expected_genesis_sha256,
        expected_pointer_sha256=expected_pointer_sha256,allow_orphans=allow_orphans)


class EventDirectoryStore:
    def __init__(self,path,genesis_sha256,token=None):
        if token is not _TOKEN:raise ValueError('Only exclusive create can open a publisher')
        self.path=Path(path);self.genesis_sha256=genesis_sha256;self.stopped=False
        self._cached_files=None;self._cached_doc=None

    @classmethod
    def create(cls,path,manifest):
        doc=j.genesis(manifest)
        if manifest['mode']!='engineering' or not manifest.get('artifact_groups'):
            raise ValueError('Engineering group allocation required')
        raw=canonical(doc);g=digest(doc);p=pointer(g,doc,j.ZERO,j.ZERO)
        if len(raw)+len(p)+65+j.GROUP_LEDGER_FINALIZATION_RESERVE>manifest['caps']['ledger_reserve_bytes']:
            raise ValueError('Genesis would consume journal closure reserve')
        store=cls(path,g,_TOKEN);store.path.mkdir(parents=True,exist_ok=False)
        (store.path/'events').mkdir();(store.path/'pointers').mkdir();j.sync_dir(store.path.parent)
        for name,data in [('genesis.json',raw),('pointers/0000.json',p),('LOCK',b''),('HEAD',j.hashlib.sha256(p).hexdigest().encode()+b'\n')]:
            j.durable_write(store.path/name,data)
        store._cached_files=inventory(store.path);store._cached_doc=j.clone(doc)
        return store

    def read(self):
        files=inventory(self.path)
        if files!=self._cached_files:
            head=files['HEAD']
            if len(head)!=65 or not head.endswith(b'\n'):raise ValueError('Torn event head')
            history=restore(files,expected_genesis_sha256=self.genesis_sha256,expected_pointer_sha256=head[:-1].decode())
            self._cached_files=files;self._cached_doc=load(history.revision_bytes[-1])
        doc=j.clone(self._cached_doc)
        return j.Checkpoint(doc,digest(doc),{'kind':'local-engineering-incremental','path':str(self.path.resolve())})

    def _proposed(self,document):
        before=self.read()
        if (document['manifest']!=before.document['manifest'] or len(document['events'])!=len(before.document['events'])+1
                or document['events'][:-1]!=before.document['events']):
            raise ValueError('Only one append; no reset or refund')
        j.replay(document);index=len(before.document['events']);raw=canonical(document)
        if index>=MAX_EVENTS or len(raw)>j.GROUP_MAX_LEDGER_SNAPSHOT:raise ValueError('Event or original revision bound exhausted')
        old_pointer=load(self._cached_files[f'pointers/{index:04d}.json'])
        record=canonical({'schema':SCHEMA,'index':index,'before_revision_sha256':before.revision,
            'after_revision_sha256':digest(document),'after_revision_bytes':len(raw),
            'previous_event_sha256':old_pointer['last_event_sha256'],'record':document['events'][-1]})
        p=pointer(self.genesis_sha256,document,j.hashlib.sha256(record).hexdigest(),self._cached_files['HEAD'][:-1].decode())
        return {f'events/{index:04d}.json':record,f'pointers/{index+1:04d}.json':p},p

    def check_publication_capacity(self,document):
        if self.stopped:raise ValueError('Event publisher uncertain; no retry')
        new,_=self._proposed(document);m=document['manifest'];event=document['events'][-1]['event']
        reserved={n for g in m['artifact_groups'].values() for n in g['reserved_artifacts']}
        closing=event['kind']=='finish' or event['kind']=='artifact' and event['name'] in reserved
        held=0 if closing else j.GROUP_LEDGER_FINALIZATION_RESERVE
        if (sum(map(len,self._cached_files.values()))+sum(map(len,new.values()))+65+held>m['caps']['ledger_reserve_bytes']
                or len(self._cached_files)+len(new)+1>MAX_FILES):
            raise ValueError('Cumulative events and all pointer versions exceed reservation')

    def publish(self,expected_revision,document):
        if self.stopped:raise ValueError('Event publisher uncertain; no retry')
        with (self.path/'LOCK').open('rb') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            before=self.read()
            if before.revision!=expected_revision:raise ValueError('Event store CAS conflict')
            self.check_publication_capacity(document);new,p=self._proposed(document)
            try:
                for name,data in new.items():j.durable_write(self.path/name,data)
                head=j.hashlib.sha256(p).hexdigest().encode()+b'\n'
                temporary=self.path/('HEAD.'+str(uuid.uuid4()));j.durable_write(temporary,head)
                os.replace(temporary,self.path/'HEAD');j.sync_dir(self.path)
                self._cached_files={**self._cached_files,**new,'HEAD':head};self._cached_doc=j.clone(document)
            except BaseException:
                self.stopped=True;raise
