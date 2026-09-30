"""Versioned compressed engineering checkpoints with bounded fieldwise readback.

Immutable content-addressed parts are shared by snapshots. All original snapshot
hashes and lengths remain recoverable. A footer uses space reserved at creation;
an oversized state is never silently labelled complete. Readers cannot resume a
writer, consume a case, draw random values, or grant scientific admission.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import resource
import time
import base64
import zlib
from types import MappingProxyType

from .empty_null_radio import canonical
from .whole_cadence_journal_radio import durable_write, sync_dir
from .physical_evidence_radio import flat_name, nested_name

SCHEMA = 'radio-physical-evidence-checkpoints-v2-zlib'
MAX_VALUE_BYTES = 24*1024**2
MAX_SNAPSHOT_BYTES = 128000000
MAX_BYTES = 18*1024**2
FOOTER_RESERVE = 65536
PART_BYTES = 1024**2
ROWS_PER_GROUP = 128
CHECKPOINT_ROWS = 1024
MAX_CHECKPOINTS = 128
MAX_FILES = 8192
ZERO = '0'*64
_TOKEN = object()


def sha(raw): return hashlib.sha256(raw).hexdigest()


class EvidenceStopped(ValueError):
    pass


class EvidenceCapacity(EvidenceStopped):
    pass


def _hash(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError('SHA256 binding required')
    return value


def _config(c):
    if set(c) != {'schema','namespace','case_identity','plan_sha256','engineering_only',
                  'budget_bytes','footer_reserve_bytes','existing_artifacts',
                  'part_bytes','rows_per_group','checkpoint_limit','logical_value_limit_bytes','logical_snapshot_limit_bytes'}:
        raise ValueError('Exact physical evidence reservation required')
    if c['schema']!=SCHEMA or c['engineering_only'] is not True:
        raise ValueError('Local evidence is engineering-only')
    if not isinstance(c['namespace'],str) or not re.fullmatch('[a-z0-9][a-z0-9_./-]{1,150}',c['namespace']):
        raise ValueError('Explicit bounded engineering namespace required')
    for name in ('case_identity','plan_sha256'):_hash(c[name])
    if (type(c['budget_bytes']) is not int or not FOOTER_RESERVE<c['budget_bytes']<=MAX_BYTES
            or c['footer_reserve_bytes']!=FOOTER_RESERVE or c['part_bytes']!=PART_BYTES
            or c['rows_per_group']!=ROWS_PER_GROUP
            or c['logical_value_limit_bytes']!=MAX_VALUE_BYTES or c['logical_snapshot_limit_bytes']!=MAX_SNAPSHOT_BYTES
            or type(c['checkpoint_limit']) is not int
            or not 1<=c['checkpoint_limit']<=MAX_CHECKPOINTS):
        raise ValueError('Prospective evidence limits changed')
    if not isinstance(c['existing_artifacts'],dict):raise ValueError('Existing artifact inventory required')
    for name,r in c['existing_artifacts'].items():
        if (not isinstance(name,str) or not name or '/' in name or '\\' in name
                or set(r)!={'bytes','sha256'} or type(r['bytes']) is not int or r['bytes']<0):
            raise ValueError('Bounded named prior case artifact required')
        _hash(r['sha256'])
    if sum(r['bytes'] for r in c['existing_artifacts'].values())+FOOTER_RESERVE>=c['budget_bytes']:
        raise ValueError('No physical evidence capacity remains')
    return c


def configuration(namespace, case_identity, plan_sha256, existing_artifacts, *,
                  budget_bytes=MAX_BYTES, checkpoint_limit=MAX_CHECKPOINTS):
    if any(not isinstance(data,bytes) for data in existing_artifacts.values()):
        raise ValueError('Actual existing artifact bytes required for accounting')
    return _config({'schema':SCHEMA,'namespace':namespace,'case_identity':case_identity,
        'plan_sha256':plan_sha256,'engineering_only':True,'budget_bytes':budget_bytes,
        'footer_reserve_bytes':FOOTER_RESERVE,'part_bytes':PART_BYTES,
        'rows_per_group':ROWS_PER_GROUP,'checkpoint_limit':checkpoint_limit,
        'existing_artifacts':{k:{'bytes':len(v),'sha256':sha(v)} for k,v in existing_artifacts.items()},
        'logical_value_limit_bytes':MAX_VALUE_BYTES,'logical_snapshot_limit_bytes':MAX_SNAPSHOT_BYTES})


def _inventory(path):
    if path.is_symlink() or not path.is_dir():raise ValueError('Regular evidence root required')
    result={};total=0
    for p in path.rglob('*'):
        if p.is_symlink():raise ValueError('Symlink in immutable evidence')
        if p.is_file():
            total+=p.stat().st_size
            if total>MAX_BYTES or len(result)>=MAX_FILES:raise ValueError('Physical evidence inventory exceeds hard bounds')
            result[p.relative_to(path).as_posix()]=p.read_bytes()
        elif not p.is_dir():raise ValueError('Nonregular evidence member')
    return result


def _raw_descriptor(data, parts):
    if not 0<len(data)<=MAX_VALUE_BYTES:
        raise EvidenceCapacity('Logical value exceeds fixed 24-MiB bound')
    hashes=[]
    for offset in range(0,len(data),PART_BYTES):
        encoded=base64.b64encode(zlib.compress(data[offset:offset+PART_BYTES],6))
        h=sha(encoded)
        if h in parts and parts[h]!=encoded:raise ValueError('Content hash collision')
        parts[h]=encoded;hashes.append(h)
    return {'kind':'zlib-base64','parts':hashes,'bytes':len(data),'sha256':sha(data)}


def _encode(document):
    if not isinstance(document,dict) or any(not isinstance(k,str) or len(k)>256 for k in document):
        raise ValueError('Bounded string-keyed physical snapshot required')
    fields={};parts={}
    for key,value in sorted(document.items()):
        if isinstance(value,list):
            if len(value)>1000000:raise EvidenceCapacity('Logical list item bound exceeded')
            fields[key]={'kind':'list','items':len(value),'groups':[
                _raw_descriptor(canonical(value[i:i+ROWS_PER_GROUP]),parts)
                for i in range(0,len(value),ROWS_PER_GROUP)]}
        else:fields[key]=_raw_descriptor(canonical(value),parts)
    return fields,parts


def _expanded_size(fields):
    if not isinstance(fields,dict):raise ValueError('Bounded field map required')
    total=2+max(0,len(fields)-1)
    for key,d in fields.items():
        if not isinstance(key,str) or len(key)>256 or not isinstance(d,dict):raise ValueError('Field descriptor required')
        total+=len(canonical(key))+1
        if d.get('kind')=='zlib-base64':sizes=[d.get('bytes')];extra=0
        elif d.get('kind')=='list' and isinstance(d.get('groups'),list):
            if any(not isinstance(g,dict) for g in d['groups']):raise ValueError('List group descriptor required')
            sizes=[g.get('bytes') for g in d['groups']];extra=2-2*len(sizes)+max(0,len(sizes)-1)
        else:raise ValueError('Unknown field expansion')
        if any(type(n) is not int or not 0<n<=MAX_VALUE_BYTES for n in sizes):
            raise ValueError('Bounded logical value lengths required')
        total+=sum(sizes)+extra
        if total>MAX_SNAPSHOT_BYTES:raise ValueError('Logical snapshot expansion exceeds fixed bound')
    return total


def _raw(d,files,used):
    if set(d)!={'kind','parts','bytes','sha256'} or d['kind']!='zlib-base64':
        raise ValueError('Compressed value descriptor changed')
    _hash(d['sha256'])
    if type(d['bytes']) is not int or not 0<d['bytes']<=MAX_VALUE_BYTES or not isinstance(d['parts'],list):
        raise ValueError('Bounded logical value required')
    if len(d['parts'])!=(d['bytes']+PART_BYTES-1)//PART_BYTES:
        raise ValueError('Value part inventory differs')
    pieces=[]
    for i,h in enumerate(d['parts']):
        name='parts/'+_hash(h);encoded=files[name];used.add(name)
        if sha(encoded)!=h or len(encoded)>2*PART_BYTES:raise ValueError('Encoded part differs or exceeds bound')
        compressed=base64.b64decode(encoded,validate=True)
        wanted=PART_BYTES if i<len(d['parts'])-1 else d['bytes']-i*PART_BYTES
        decoder=zlib.decompressobj();piece=decoder.decompress(compressed,wanted+1)
        if len(piece)!=wanted or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('Compressed part expansion/termination differs')
        pieces.append(piece)
    data=b''.join(pieces)
    if sha(data)!=d['sha256']:raise ValueError('Logical value bytes differ')
    value=json.loads(data)
    if canonical(value)!=data:raise ValueError('Noncanonical logical value')
    return data,len(value) if isinstance(value,list) else None


def _iter_decode(fields,files,used):
    _expanded_size(fields)
    yield b'{'
    for index,(key,d) in enumerate(sorted(fields.items())):
        if index:yield b','
        yield canonical(key)+b':'
        if d.get('kind')=='zlib-base64':
            value,_=_raw(d,files,used)
            for i in range(0,len(value),PART_BYTES):yield value[i:i+PART_BYTES]
        elif d.get('kind')=='list':
            if set(d)!={'kind','items','groups'} or type(d['items']) is not int or not 0<=d['items']<=1000000:
                raise ValueError('Bounded list descriptor required')
            if len(d['groups'])!=(d['items']+ROWS_PER_GROUP-1)//ROWS_PER_GROUP:
                raise ValueError('List group inventory differs')
            yield b'['
            for i,g in enumerate(d['groups']):
                data,count=_raw(g,files,used)
                if count!=(ROWS_PER_GROUP if i<len(d['groups'])-1 else d['items']-i*ROWS_PER_GROUP):
                    raise ValueError('List group length differs')
                if i:yield b','
                for offset in range(1,len(data)-1,PART_BYTES):yield data[offset:min(offset+PART_BYTES,len(data)-1)]
            yield b']'
        else:raise ValueError('Unknown evidence descriptor')
    yield b'}'


def _verified_digest(fields,files):
    used=set();h=hashlib.sha256();size=0
    for piece in _iter_decode(fields,files,used):h.update(piece);size+=len(piece)
    return h.hexdigest(),size,used


@dataclass(frozen=True)
class ReadOnlyEvidence:
    config_bytes: bytes
    checkpoint_bytes: tuple
    files: dict
    orphan_paths: tuple
    footer_bytes: bytes | None
    stored_bytes: int
    charged_bytes: int
    verified_values: object

    def iter_snapshot(self,index):
        if type(index) is not int or not 0<=index<len(self.checkpoint_bytes):
            raise ValueError('Checkpoint index outside history')
        c=json.loads(self.checkpoint_bytes[index])
        yield from _iter_decode(c['fields'],self.files,set())

    def snapshot(self,index):
        if type(index) is not int or not 0<=index<len(self.checkpoint_bytes):
            raise ValueError('Checkpoint index outside history')
        c=json.loads(self.checkpoint_bytes[index])
        if c['snapshot_bytes']>MAX_VALUE_BYTES:
            raise ValueError('Large snapshot requires iter_snapshot; aggregate materialization refused')
        return b''.join(self.iter_snapshot(index))

    def summary(self):
        footer=None if self.footer_bytes is None else json.loads(self.footer_bytes)
        return {'checkpoints':len(self.checkpoint_bytes),'stored_bytes':self.stored_bytes,
                'charged_case_bytes':self.charged_bytes,'orphan_paths':list(self.orphan_paths),
                'status':None if footer is None else footer['status'],
                'latest_checkpoint_sha256':ZERO if not self.checkpoint_bytes else sha(self.checkpoint_bytes[-1]),
                'execution_restart_authorized':False,'scientific_admission_authorized':False}


def inspect(path, *, expected_config_sha256, expected_last_checkpoint_sha256=None, allow_orphans=False):
    """Validate every checkpoint; crash recovery exposes orphans, never resumes."""
    return inspect_files(_inventory(Path(path)),expected_config_sha256=expected_config_sha256,
        expected_last_checkpoint_sha256=expected_last_checkpoint_sha256,allow_orphans=allow_orphans)


def inspect_files(files, *, expected_config_sha256, expected_last_checkpoint_sha256=None, allow_orphans=False):
    """Same read-only verification over a bounded already-read immutable map."""
    files=dict(files)
    if len(files)>MAX_FILES or any(not isinstance(v,bytes) for v in files.values()) or sum(map(len,files.values()))>MAX_BYTES:
        raise ValueError('Physical evidence inventory exceeds hard bounds')
    config_raw=files['reservation.json']
    if sha(config_raw)!=_hash(expected_config_sha256):raise ValueError('Independent reservation pin differs')
    c=_config(json.loads(config_raw))
    if canonical(c)!=config_raw:raise ValueError('Noncanonical reservation')
    names=sorted(n for n in files if n.startswith('checkpoints/'))
    if len(names)>c['checkpoint_limit'] or names!=[f'checkpoints/{i:04d}.json' for i in range(len(names))]:
        raise ValueError('Checkpoint gap, overflow, or unexpected filename')
    used={'reservation.json'};previous=ZERO;checkpoints=[]
    for i,name in enumerate(names):
        try:
            raw=files[name];r=json.loads(raw)
            if (canonical(r)!=raw or set(r)!={'schema','index','previous','reservation_sha256','stage','snapshot_sha256','snapshot_bytes','fields'}
                    or r['schema']!=SCHEMA or r['index']!=i or r['previous']!=previous
                    or r['reservation_sha256']!=expected_config_sha256 or not isinstance(r['stage'],str)
                    or len(r['stage'])>80 or type(r['snapshot_bytes']) is not int or not 0<r['snapshot_bytes']<=MAX_SNAPSHOT_BYTES):
                raise ValueError('Checkpoint chain/binding changed')
            logical_sha,logical_bytes,part_names=_verified_digest(r['fields'],files)
            if logical_sha!=r['snapshot_sha256'] or logical_bytes!=r['snapshot_bytes']:raise ValueError('Checkpoint logical bytes differ')
            used.update(part_names);used.add(name);previous=sha(raw);checkpoints.append(raw)
        except (ValueError,KeyError,TypeError):
            if not allow_orphans:raise
            break
    if expected_last_checkpoint_sha256 is not None and previous!=_hash(expected_last_checkpoint_sha256):
        raise ValueError('Latest checkpoint differs from independent pin')
    footer=files.get('outcome.json')
    if footer is not None:
        f=json.loads(footer)
        if (canonical(f)!=footer or len(footer)>FOOTER_RESERVE or f.get('schema')!=SCHEMA
                or f.get('reservation_sha256')!=expected_config_sha256 or f.get('last_checkpoint_sha256')!=previous
                or f.get('checkpoint_count')!=len(checkpoints) or f.get('status') not in ('completed','failed')
                or f.get('execution_restart_authorized') is not False or f.get('scientific_admission_authorized') is not False):
            raise ValueError('Outcome binding/status changed')
        if f['status']=='completed':
            if not checkpoints:raise ValueError('Incomplete physical evidence cannot complete')
            complete,_=_raw(json.loads(checkpoints[-1])['fields']['complete'],files,set())
            if complete!=b'true':raise ValueError('Incomplete physical evidence cannot complete')
        used.add('outcome.json')
    orphans=tuple(sorted(set(files)-used))
    if orphans and not allow_orphans:raise ValueError('Uncommitted or unexpected evidence files: '+','.join(orphans))
    stored=sum(map(len,files.values()));charged=stored+sum(r['bytes'] for r in c['existing_artifacts'].values())
    if charged>c['budget_bytes']:raise ValueError('Complete cumulative case evidence budget exceeded')
    return ReadOnlyEvidence(config_raw,tuple(checkpoints),MappingProxyType(files),orphans,footer,stored,charged,MappingProxyType({}))


class Writer:
    """Fresh process-local writer. Existing directories cannot be resumed."""
    def __init__(self,path,config,token=None):
        if token is not _TOKEN:raise ValueError('Only exclusive create may start a writer')
        self.path=Path(path);self.config=json.loads(canonical(config));self.config_raw=canonical(config)
        self.config_sha=sha(self.config_raw);self.started=time.monotonic();self.closed=False;self.poisoned=False
        self.capacity_failed=False
        self.expected={'reservation.json':self.config_raw};self.previous=ZERO;self.count=0
        self.existing_bytes=sum(r['bytes'] for r in config['existing_artifacts'].values())
        self.last_failure=None
        self.lease=None

    @classmethod
    def create(cls,path,config,*,existing_artifacts):
        _config(config)
        if configuration(config['namespace'],config['case_identity'],config['plan_sha256'],existing_artifacts,
                         budget_bytes=config['budget_bytes'],checkpoint_limit=config['checkpoint_limit'])!=config:
            raise ValueError('Already charged artifact bytes differ from reservation')
        writer=cls(path,config,_TOKEN)
        if len(writer.config_raw)+writer.existing_bytes+FOOTER_RESERVE>config['budget_bytes']:
            raise ValueError('Reservation and failure footer exceed case budget')
        writer.path.mkdir(parents=True,exist_ok=False)
        (writer.path/'parts').mkdir();(writer.path/'checkpoints').mkdir();sync_dir(writer.path)
        durable_write(writer.path/'reservation.json',writer.config_raw)
        return writer

    @classmethod
    def create_for_lease(cls,lease,config,*,existing_artifacts):
        from . import whole_cadence_journal_radio as j
        from .whole_cadence_event_store_radio import EventDirectoryStore
        if (type(lease) is not j.Lease or lease.manifest['mode']!='engineering'
                or type(lease.store) is not EventDirectoryStore):
            raise ValueError('Fresh local event engineering parent lease required')
        lease.budget();lease._current();_config(config)
        binding=lease.case['binding']
        if any(config[key]!=binding[key] for key in ('case_identity','plan_sha256')):
            raise ValueError('Physical case/plan identity differs from fresh parent binding')
        groups=lease.manifest.get('artifact_groups',{})
        if set(groups)!={'physical'}:raise ValueError('Fixed physical group required')
        group=groups['physical']
        if (group['prefix']!='physical-'
                or j.group_binding(group,binding['case_identity'])!=sha(canonical(config))):
            raise ValueError('Physical reservation differs from prospective parent binding')
        from .physical_case_v2_radio import matches_policy, CLOSURE_RESERVES
        if not matches_policy(group,config):
            raise ValueError('Exact prospective physical closure policy required')
        if any(name.startswith('physical-') or name in CLOSURE_RESERVES for name in existing_artifacts):
            raise ValueError('Original base artifact overlaps physical or closure inventory')
        state=j.replay(lease.checkpoint.document)['cases'][-1]
        if set(state['artifacts'])!=set(existing_artifacts):
            raise ValueError('Exact already-registered inventory required')
        for name,data in existing_artifacts.items():
            if (lease.directory/name).read_bytes()!=data:
                raise ValueError('Existing parent bytes differ')
        j.verify_archive(lease.checkpoint,lease.directory,
            case_index=len(j.replay(lease.checkpoint.document)['cases'])-1)
        held=sum(group['reserved_artifacts'].values())
        if (lease.case['artifact_bytes']>MAX_BYTES
                or config['budget_bytes']!=lease.case['artifact_bytes']-held):
            raise ValueError('Physical budget must retain all outer closure reserves within 18 MiB')
        if configuration(config['namespace'],config['case_identity'],config['plan_sha256'],existing_artifacts,
                budget_bytes=config['budget_bytes'],checkpoint_limit=config['checkpoint_limit'])!=config:
            raise ValueError('Physical existing artifact binding differs')
        writer=cls(lease.directory,config,_TOKEN);writer.lease=lease
        writer._write('reservation.json',writer.config_raw)
        return writer

    def _write(self,path,data):
        if self.lease is None:durable_write(self.path/path,data)
        else:self.lease.write_artifact(flat_name(path),data)

    def _write_many(self,values):
        if not values:return
        if self.lease is None:
            for path,data in values.items():durable_write(self.path/path,data)
        else:
            from .whole_cadence_journal_radio import GROUP_ARTIFACT_BATCH_MAX
            rows=sorted(values.items())
            for offset in range(0,len(rows),GROUP_ARTIFACT_BATCH_MAX):
                self.lease.write_artifacts({flat_name(path):data
                    for path,data in rows[offset:offset+GROUP_ARTIFACT_BATCH_MAX]})

    def _files(self):
        if self.lease is None:return _inventory(self.path)
        from . import whole_cadence_journal_radio as j
        self.lease.budget();self.lease._current()
        j.verify_archive(self.lease.checkpoint,self.path,
            case_index=len(j.replay(self.lease.checkpoint.document)['cases'])-1)
        return {nested_name(n):data for n,data in _inventory(self.path).items()
                if n.startswith('physical-')}

    def _current(self,*,allow_capacity=False):
        if self.closed or self.poisoned:raise EvidenceStopped('Writer closed or uncertain; no retry')
        if self.capacity_failed and not allow_capacity:raise EvidenceCapacity('Capacity failure is final; only failed closure allowed')
        try:
            if canonical(self.config)!=self.config_raw or self._files()!=self.expected:
                raise EvidenceStopped('Existing evidence or reservation changed')
        except BaseException:
            self.poisoned=True
            raise

    def receipt(self):
        return {'reservation_sha256':self.config_sha,'last_checkpoint_sha256':self.previous,
                'checkpoint_count':self.count,'stored_bytes':sum(map(len,self.expected.values())),
                'charged_case_bytes':self.existing_bytes+sum(map(len,self.expected.values())),
                'uncertain_write':self.poisoned,'closed':self.closed,
                'capacity_failed':self.capacity_failed,
                'execution_restart_authorized':False,'scientific_admission_authorized':False}

    def checkpoint(self,stage,document):
        self._current()
        if not isinstance(stage,str) or len(stage)>80:raise ValueError('Bounded stage label required')
        raw=canonical(document)
        if len(raw)>MAX_SNAPSHOT_BYTES:
            self.capacity_failed=True;raise EvidenceCapacity('Logical snapshot exceeds fixed maximum')
        if self.count>=self.config['checkpoint_limit']:
            self.capacity_failed=True;raise EvidenceCapacity('Checkpoint reservation exhausted')
        if document.get('retention',{}).get('case_identity')!=self.config['case_identity']:
            raise ValueError('Physical snapshot case differs from reservation')
        try:
            fields,parts=_encode(document)
        except EvidenceCapacity:
            self.capacity_failed=True
            raise
        row={'schema':SCHEMA,'index':self.count,'previous':self.previous,'reservation_sha256':self.config_sha,
             'stage':stage,'snapshot_sha256':sha(raw),'snapshot_bytes':len(raw),'fields':fields}
        encoded=canonical(row);name=f'checkpoints/{self.count:04d}.json'
        new={'parts/'+h:data for h,data in parts.items() if 'parts/'+h not in self.expected}
        new[name]=encoded
        proposed=self.existing_bytes+sum(map(len,self.expected.values()))+sum(map(len,new.values()))+FOOTER_RESERVE
        max_files=MAX_FILES if self.lease is None else self.lease.manifest['artifact_groups']['physical']['max_files']
        if proposed>self.config['budget_bytes'] or len(self.expected)+len(new)+1>max_files:
            self.capacity_failed=True
            self.last_failure={'kind':'capacity','uncommitted_snapshot_sha256':sha(raw),'uncommitted_snapshot_bytes':len(raw),
                               'would_charge_bytes_including_footer_reserve':proposed}
            raise EvidenceCapacity('Checkpoint cannot fit without consuming reserved failure footer')
        try:
            # Parts precede their commit record. A failure poisons the only writer;
            # recovery can expose a committed prefix and explicitly counted orphans.
            self._write_many(new)
            self.expected.update(new)
            self.previous=sha(encoded);self.count+=1
            return self.receipt()
        except BaseException:
            self.poisoned=True;raise

    def close(self,status,stage,reason='',*,snapshot=None):
        if self.closed:raise EvidenceStopped('Already closed')
        if status not in ('completed','failed'):raise ValueError('Explicit completion/failure status required')
        saved=False
        if snapshot is not None and not self.poisoned and not self.capacity_failed:
            try:self.checkpoint(stage,snapshot);saved=True
            except EvidenceCapacity:
                if status=='completed':raise
            except BaseException:
                self.poisoned=True
                if status=='completed':raise
        if status=='completed' and (snapshot is None or snapshot.get('complete') is not True or not saved):
            raise ValueError('Complete final physical snapshot required')
        if self.poisoned:
            self.closed=True
            return {**self.receipt(),'status':'uncertain','final_snapshot_saved':False}
        self._current(allow_capacity=True)
        footer={'schema':SCHEMA,'reservation_sha256':self.config_sha,'last_checkpoint_sha256':self.previous,
                'checkpoint_count':self.count,'status':status,'stage':str(stage)[:80],
                'reason':str(reason)[:4096],'reason_sha256':sha(str(reason).encode()),
                'final_snapshot_saved':saved,'capacity_failure':self.last_failure,
                'elapsed_seconds':time.monotonic()-self.started,
                'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                'execution_restart_authorized':False,'scientific_admission_authorized':False}
        data=canonical(footer)
        if len(data)>FOOTER_RESERVE:raise EvidenceCapacity('Reserved small failure footer exceeded')
        try:self._write('outcome.json',data);self.expected['outcome.json']=data
        except BaseException:self.poisoned=True;self.closed=True;raise
        self.closed=True
        return {**self.receipt(),'status':status,'final_snapshot_saved':saved}
