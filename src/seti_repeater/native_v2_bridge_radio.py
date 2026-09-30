"""Bounded, durable filesystem bridge. This component grants no execution.

Reservations are immutable and precede a worker request. An unsealed item
retains its complete reservation, including after process loss. Files are never
overwritten and a failed write closes the store. The byte limits count logical
file bytes; filesystem allocation and process RSS need separate measurement.
"""
from contextlib import contextmanager
import base64
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import time

from .empty_null_radio import canonical

SCHEMA = 'radio-native-v2-filesystem-bridge-v1'
CHUNK_BYTES = 24576
READ_BYTES = 32768
MAX_INPUT_BYTES = 98304
METADATA_RESERVATION = 4096
MIB = 1024 ** 2
LIMITS = {'host_receipt': 1536*MIB, 'python_receipt': 512*MIB,
          'runner_state': 16*MIB, 'request': 384*MIB, 'response': 512*MIB,
          'git_projection': 512*MIB, 'bridge_receipt': 1536*MIB,
          'metadata': 16*MIB, 'items': 2048, 'item_bytes': 64*MIB}
CASE_LIMITS = {'host_receipt': 192*MIB, 'python_receipt': 64*MIB,
               'runner_state': 2*MIB, 'request': 48*MIB, 'response': 64*MIB,
               'git_projection': 64*MIB, 'bridge_receipt': 192*MIB}
KINDS = tuple(CASE_LIMITS)


def _integer(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Bounded integer required: ' + name)
    return value


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact SHA256 required')
    return value


def _id(value):
    if not isinstance(value, str) or not re.fullmatch('[a-z0-9_-]{1,80}', value):
        raise ValueError('Safe exclusive bridge item identity required')
    return value


def _absolute(value):
    if (not isinstance(value, str) or not value.startswith('/') or value == '/'
            or any(p in ('', '.', '..') for p in value[1:].split('/'))
            or '\\' in value or any(ord(c) < 32 for c in value)):
        raise ValueError('Canonical absolute filesystem path required')
    return value


def _regular(fd):
    value = os.fstat(fd)
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise ValueError('Exclusive regular file required')
    return value


def _directory(path):
    """Open each absolute ancestor with NOFOLLOW; do not resolve symlinks."""
    if path == '/': return os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    parts = _absolute(path)[1:].split('/')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in parts:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd); raise


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        amount = os.write(fd, view)
        if amount <= 0:
            raise OSError('Incomplete durable write')
        view = view[amount:]


def _exclusive(directory, name, data, mode=0o400):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 mode, dir_fd=directory)
    try:
        _write_all(fd, data); os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(directory)


def _read_small(directory, name, cap=METADATA_RESERVATION):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        size = _regular(fd).st_size
        if size > cap:
            raise ValueError('Bridge metadata exceeds frozen bound')
        data = os.read(fd, size + 1)
        if len(data) != size:
            raise ValueError('Bridge metadata changed while reading')
        return data
    finally:
        os.close(fd)


def _json_small(directory, name):
    raw = _read_small(directory, name)
    value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError('Canonical immutable bridge metadata required')
    return value


def _exists(directory, name):
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


class Store:
    """Multi-process ledger with exclusive reservations and bounded uploads."""
    def __init__(self, root):
        self.root = _absolute(os.fspath(root))

    @classmethod
    def create(cls, root, *, limits=None, case_limits=None):
        root = _absolute(os.fspath(root))
        limits = dict(LIMITS if limits is None else limits)
        case_limits = dict(CASE_LIMITS if case_limits is None else case_limits)
        for value, hard in ((limits, LIMITS), (case_limits, CASE_LIMITS)):
            if set(value) != set(hard) or any(type(value[k]) is not int or
                    not 0 < value[k] <= hard[k] for k in hard):
                raise ValueError('Complete finite frozen bridge limits required')
        parent, name = root.rsplit('/', 1)
        pfd = _directory(parent or '/') if parent else os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.mkdir(name, 0o700, dir_fd=pfd); os.fsync(pfd)
        finally:
            os.close(pfd)
        rfd = _directory(root)
        try:
            manifest = {'schema': SCHEMA, 'limits': limits,
                        'case_limits': case_limits, 'automatic_retry': False,
                        'execution_authorized': False,
                        'scientific_execution_authorized': False,
                        'logical_file_bytes_only': True}
            _exclusive(rfd, 'manifest.json', canonical(manifest))
            _exclusive(rfd, 'LOCK', b'', mode=0o600)
            os.mkdir('items', 0o700, dir_fd=rfd); os.fsync(rfd)
        finally:
            os.close(rfd)
        return cls(root)

    @contextmanager
    def _locked(self, *, writing=False):
        rfd = _directory(self.root)
        lock = None; items = None
        try:
            lock = os.open('LOCK', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=rfd)
            _regular(lock); fcntl.flock(lock, fcntl.LOCK_EX)
            manifest = _json_small(rfd, 'manifest.json')
            if manifest.get('schema') != SCHEMA:
                raise ValueError('Exact bridge manifest required')
            for key, hard in (('limits', LIMITS), ('case_limits', CASE_LIMITS)):
                actual = manifest.get(key)
                if not isinstance(actual, dict) or set(actual) != set(hard) or any(
                        type(actual[k]) is not int or not 0 < actual[k] <= hard[k] for k in hard):
                    raise ValueError('Immutable bridge limits differ')
            if writing and _exists(rfd, 'STOPPED.json'):
                raise RuntimeError('Filesystem bridge stopped; no retry')
            items = os.open('items', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=rfd)
            yield rfd, items, manifest
        finally:
            if items is not None: os.close(items)
            if lock is not None: os.close(lock)
            os.close(rfd)

    def _stop(self, rfd, error):
        if not _exists(rfd, 'STOPPED.json'):
            _exclusive(rfd, 'STOPPED.json', canonical({'schema': SCHEMA,
                'reason': str(error)[:1024], 'automatic_retry': False}))

    @staticmethod
    def _item(items, identity):
        return os.open(_id(identity), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                       dir_fd=items)

    def _status(self, rfd, items, manifest):
        totals = {k: {'known_bytes': 0, 'unknown_bytes': 0, 'charged_bytes': 0,
                      'items': 0} for k in (*KINDS, 'metadata')}
        cases = [{k: 0 for k in KINDS} for _ in range(8)]
        summaries = []
        names = sorted(os.listdir(items))
        if len(names) > manifest['limits']['items']:
            raise ValueError('Frozen bridge item count exceeded')
        for name in names:
            fd = self._item(items, name)
            try:
                if not set(os.listdir(fd)) <= {'intent.json','part','sealing.json','sealed.json','claimed.json'}:
                    raise ValueError('Unexpected duplicate or uncharged item file')
                intent = _json_small(fd, 'intent.json')
                if intent['id'] != name or intent['kind'] not in KINDS:
                    raise ValueError('Exact bridge reservation required')
                size = _integer(intent['reserved_bytes'], manifest['limits']['item_bytes'], 'reservation')
                case = intent['case_ordinal']
                if case is not None: _integer(case, 7, 'case')
                sealed = _exists(fd, 'sealed.json')
                marker = _json_small(fd, 'sealed.json') if sealed else None
                actual = marker['bytes'] if sealed else 0
                if sealed:
                    _integer(actual, size, 'sealed bytes'); _sha(marker['sha256'])
                    payload_fd = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if _regular(payload_fd).st_size != actual:
                            raise ValueError('Sealed payload size differs')
                    finally: os.close(payload_fd)
                charged = actual if sealed else size
                row = totals[intent['kind']]
                row['known_bytes'] += actual
                row['unknown_bytes'] += 0 if sealed else size
                row['charged_bytes'] += charged; row['items'] += 1
                if case is not None: cases[case][intent['kind']] += charged
                metadata = len(canonical(intent)) + (len(canonical(marker)) if sealed else 0)
                if _exists(fd,'claimed.json'): metadata+=len(_read_small(fd,'claimed.json'))
                if _exists(fd,'sealing.json'): metadata+=len(_read_small(fd,'sealing.json'))
                if metadata>METADATA_RESERVATION: raise ValueError('Item metadata reservation exceeded')
                totals['metadata']['known_bytes'] += metadata
                totals['metadata']['unknown_bytes'] += METADATA_RESERVATION-metadata
                totals['metadata']['charged_bytes'] += METADATA_RESERVATION
                totals['metadata']['items'] += 1
                summaries.append({'id': name, 'kind': intent['kind'], 'case_ordinal': case,
                                  'sealed': sealed, 'reserved_bytes': size,
                                  'bytes': actual, 'sha256': marker['sha256'] if sealed else None})
            finally: os.close(fd)
        # Manifest/lock/stop bytes are a fixed bounded independent ledger tail.
        fixed = len(_read_small(rfd, 'manifest.json'))
        if _exists(rfd, 'STOPPED.json'): fixed += len(_read_small(rfd, 'STOPPED.json'))
        totals['metadata']['known_bytes'] += fixed
        totals['metadata']['unknown_bytes'] += METADATA_RESERVATION
        totals['metadata']['charged_bytes'] += fixed + METADATA_RESERVATION
        for kind, row in totals.items():
            if row['charged_bytes'] > manifest['limits'][kind]:
                raise ValueError('Frozen bridge bucket exceeded: ' + kind)
        if any(case[k] > manifest['case_limits'][k] for case in cases for k in KINDS):
            raise ValueError('Frozen per-case bridge bucket exceeded')
        return {'schema': SCHEMA, 'limits': manifest['limits'],
                'case_limits': manifest['case_limits'], 'buckets': totals,
                'cases': cases, 'item_count': len(names), 'items': summaries,
                'stopped': _exists(rfd, 'STOPPED.json'), 'automatic_retry': False,
                'execution_authorized': False, 'logical_file_bytes_only': True}

    def status(self):
        with self._locked() as (rfd, items, manifest):
            return self._status(rfd, items, manifest)

    def stop(self,error):
        with self._locked() as (rfd,items,manifest): self._stop(rfd,error)

    def claim(self,identity):
        """One durable host claim; an expired worker request cannot dispatch."""
        raw=self.payload(identity); packet=json.loads(raw)
        if canonical(packet)!=raw or packet.get('schema')!=SCHEMA:
            raise ValueError('Exact canonical worker request required')
        with self._locked(writing=True) as (rfd,items,manifest):
            fd=None
            try:
                fd=self._item(items,identity); intent=_json_small(fd,'intent.json')
                if intent['kind']!='request' or _exists(fd,'claimed.json'):
                    raise ValueError('Exclusive fresh request claim required; no retry')
                end=packet.get('deadline_monotonic_seconds')
                if type(end) not in (float,int) or not math.isfinite(end) or end<=time.monotonic():
                    raise TimeoutError('Worker request expired before host dispatch')
                marker={'schema':SCHEMA,'id':identity,'request_sha256':hashlib.sha256(raw).hexdigest(),
                        'claimed':True,'automatic_retry':False}
                _exclusive(fd,'claimed.json',canonical(marker))
                remaining=end-time.monotonic()
                if remaining<=0: raise TimeoutError('Worker request expired during durable claim')
                return {**marker,'remaining_seconds':remaining}
            except BaseException as error:
                self._stop(rfd,error); raise
            finally:
                if fd is not None: os.close(fd)

    def reserve(self, identity, kind, size, sha256=None, case_ordinal=None):
        identity = _id(identity)
        if kind not in KINDS: raise ValueError('Known independent bridge bucket required')
        if sha256 is not None: _sha(sha256)
        if case_ordinal is not None: _integer(case_ordinal, 7, 'case')
        with self._locked(writing=True) as (rfd, items, manifest):
            try:
                size = _integer(size, manifest['limits']['item_bytes'], 'reservation')
                state = self._status(rfd, items, manifest)
                if (_exists(items, identity) or state['item_count'] >= manifest['limits']['items']
                        or state['buckets'][kind]['charged_bytes']+size > manifest['limits'][kind]
                        or state['buckets']['metadata']['charged_bytes']+METADATA_RESERVATION > manifest['limits']['metadata']
                        or (case_ordinal is not None and state['cases'][case_ordinal][kind]+size > manifest['case_limits'][kind])):
                    raise ValueError('Exclusive reservation cannot fit frozen bridge budget')
                intent = {'schema': SCHEMA, 'id': identity, 'kind': kind,
                          'reserved_bytes': size, 'expected_sha256': sha256,
                          'case_ordinal': case_ordinal, 'automatic_retry': False}
                os.mkdir(identity, 0o700, dir_fd=items); os.fsync(items)
                fd = self._item(items, identity)
                try:
                    _exclusive(fd, 'intent.json', canonical(intent))
                    _exclusive(fd, 'part', b'', mode=0o600)
                finally: os.close(fd)
                return {'id': identity, 'reserved_bytes': size, 'durable': True}
            except BaseException as error:
                self._stop(rfd, error); raise

    def append(self, identity, offset, data):
        if not isinstance(data, bytes) or not 0 < len(data) <= CHUNK_BYTES:
            raise ValueError('Nonempty bounded binary chunk required')
        with self._locked(writing=True) as (rfd, items, manifest):
            fd = None; payload = None
            try:
                fd = self._item(items, identity); intent = _json_small(fd, 'intent.json')
                _integer(offset, intent['reserved_bytes'], 'offset')
                if _exists(fd, 'payload') or _exists(fd, 'sealing.json') or _exists(fd, 'sealed.json'):
                    raise ValueError('Bridge item already finalized; no retry')
                payload = os.open('part', os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=fd)
                if _regular(payload).st_size != offset or offset+len(data) > intent['reserved_bytes']:
                    raise ValueError('Exact sequential reserved chunk required; no retry')
                _write_all(payload, data); os.fsync(payload); os.fsync(fd)
                return {'id': identity, 'offset': offset+len(data), 'durable': True}
            except BaseException as error:
                self._stop(rfd, error); raise
            finally:
                if payload is not None: os.close(payload)
                if fd is not None: os.close(fd)

    def seal(self, identity, *, size=None, sha256=None):
        if sha256 is not None: _sha(sha256)
        with self._locked(writing=True) as (rfd, items, manifest):
            fd = None; payload = None
            try:
                fd = self._item(items, identity); intent = _json_small(fd, 'intent.json')
                if _exists(fd, 'payload') or _exists(fd, 'sealing.json') or _exists(fd, 'sealed.json'):
                    raise ValueError('Bridge item already finalized; no retry')
                payload = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                actual = _regular(payload).st_size
                _integer(actual, intent['reserved_bytes'], 'actual bytes')
                if size is not None and (type(size) is not int or size != actual):
                    raise ValueError('Final item byte count differs')
                hasher = hashlib.sha256()
                while block := os.read(payload, CHUNK_BYTES): hasher.update(block)
                digest = hasher.hexdigest()
                if ((intent['expected_sha256'] is not None and digest != intent['expected_sha256'])
                        or (sha256 is not None and digest != sha256)):
                    raise ValueError('Final item SHA256 differs')
                if intent['expected_sha256'] is None and (size is None or sha256 is None):
                    raise ValueError('Unpinned reservation needs independently supplied final bytes and SHA256')
                marker = {'schema': SCHEMA, 'id': identity, 'bytes': actual,
                          'sha256': digest, 'durable': True}
                # The one authoritative file retains its original name. The
                # final marker seals it; no rename/link/unlink or deletion
                # credit is required across tool workspace snapshots.
                _exclusive(fd,'sealing.json',canonical(marker))
                os.fsync(payload); os.fchmod(payload, 0o400); os.fsync(payload); os.fsync(fd)
                _exclusive(fd, 'sealed.json', canonical(marker))
                return {**marker, 'path': self.root+'/items/'+identity+'/part'}
            except BaseException as error:
                self._stop(rfd, error); raise
            finally:
                if payload is not None: os.close(payload)
                if fd is not None: os.close(fd)

    def read(self, identity, offset=0, length=READ_BYTES):
        _integer(length, READ_BYTES, 'read length')
        with self._locked() as (rfd, items, manifest):
            fd = self._item(items, identity); payload = None
            try:
                marker = _json_small(fd, 'sealed.json')
                _integer(offset, marker['bytes'], 'read offset')
                if _exists(fd,'payload'): raise ValueError('Unexpected duplicate or uncharged item file')
                payload = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                if _regular(payload).st_size != marker['bytes']:
                    raise ValueError('Immutable payload size differs')
                os.lseek(payload, offset, os.SEEK_SET)
                data = os.read(payload, min(length, marker['bytes']-offset))
                return {'id': identity, 'offset': offset, 'bytes': len(data), 'total_bytes': marker['bytes'],
                        'sha256': marker['sha256'], 'content_base64': base64.b64encode(data).decode('ascii'),
                        'next_offset': offset+len(data), 'eof': offset+len(data)==marker['bytes']}
            finally:
                if payload is not None: os.close(payload)
                os.close(fd)

    def write(self, identity, kind, data, *, case_ordinal=None):
        """Reserve all bytes first, then bounded durable chunks; no retries."""
        if not isinstance(data, bytes): raise ValueError('Exact binary payload required')
        digest = hashlib.sha256(data).hexdigest()
        self.reserve(identity, kind, len(data), digest, case_ordinal)
        for offset in range(0, len(data), CHUNK_BYTES):
            self.append(identity, offset, data[offset:offset+CHUNK_BYTES])
        return self.seal(identity, size=len(data), sha256=digest)

    def payload(self, identity):
        """Load an already independently bounded item; verify its exact digest."""
        chunks = []; offset = 0
        while True:
            row = self.read(identity, offset)
            block = base64.b64decode(row['content_base64'], validate=True)
            chunks.append(block); offset = row['next_offset']
            if row['eof']: break
        data = b''.join(chunks)
        if len(data) != row['total_bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Final immutable bridge readback differs')
        return data


class Worker:
    """Concrete runner callbacks using one immutable numbered IPC request.

    A host polls pending requests, reads their bounded chunks, and fills the
    pre-reserved response item. No worker operation is automatically repeated.
    This does not verify a public freeze or reservation and cannot start Runner.
    """
    RESPONSE_RESERVATIONS = {'invoke:fetch': 4*MIB, 'invoke:create_tree': MIB,
        'invoke:create_commit': 65536, 'invoke:update_ref': 16384,
        'invoke:fetch_files': 48*MIB, 'prepare_transport': MIB,
        'finish_transport': MIB, 'transport_usage': MIB}

    def __init__(self, store, *, seconds=30, poll_seconds=0.02):
        if not isinstance(store, Store) or not math.isfinite(seconds) or not 0 < seconds <= 30:
            raise ValueError('Concrete store and bounded worker deadline required')
        if not math.isfinite(poll_seconds) or not 0 < poll_seconds <= .1:
            raise ValueError('Bounded polling interval required')
        self.store=store; self.seconds=seconds; self.poll_seconds=poll_seconds
        self.ordinal=0; self.case_ordinal=None; self.stopped=False
        self.receipts={}; self.state_ordinal=0; self.invoke_ordinal=0

    def _call(self, operation, params):
        if self.stopped: raise RuntimeError('Worker bridge stopped; no retry')
        if operation not in self.RESPONSE_RESERVATIONS: raise ValueError('Fixed bridge operation required')
        ordinal=self.ordinal; self.ordinal+=1
        identity='request-'+str(ordinal).zfill(6)
        response='response-'+str(ordinal).zfill(6)
        receipt='python-'+str(ordinal).zfill(6)
        try:
            end=time.monotonic()+self.seconds
            reservation=self.RESPONSE_RESERVATIONS[operation]
            self.store.reserve(response, 'response', reservation, case_ordinal=self.case_ordinal)
            if operation.startswith('invoke:'):
                self.store.reserve(receipt, 'python_receipt', reservation, case_ordinal=self.case_ordinal)
                self.receipts[ordinal]={'id':receipt,'operation':operation[7:],
                                       'request':canonical(params), 'response_id':response,
                                       'invoke_ordinal':self.invoke_ordinal}
                self.invoke_ordinal+=1
            request=canonical({'schema':SCHEMA,'ordinal':ordinal,'operation':operation,
                'params':params,'response_id':response,'response_reserved_bytes':reservation,
                'case_ordinal':self.case_ordinal,'automatic_retry':False,
                'deadline_monotonic_seconds':end})
            self.store.write(identity,'request',request,case_ordinal=self.case_ordinal)
            while time.monotonic()<end:
                row=next(x for x in self.store.status()['items'] if x['id']==response)
                if row['sealed']:
                    raw=self.store.payload(response); result=json.loads(raw)
                    if canonical(result)!=raw or not isinstance(result,dict):
                        raise ValueError('Exact canonical response object required')
                    return result
                time.sleep(min(self.poll_seconds,max(0,end-time.monotonic())))
            raise TimeoutError('Worker reply uncertain; no retry')
        except BaseException as error:
            self.stopped=True; self.store.stop(error); raise

    def invoke(self, operation, params):
        return self._call('invoke:'+operation, params)

    def prepare_transport(self, freeze_json, bundle_sha256):
        freeze=json.loads(freeze_json)
        _integer(freeze['ordinal'],7,'case')
        self.case_ordinal=freeze['ordinal']
        return self._call('prepare_transport',{'freeze_json':freeze_json,'bundle_sha256':bundle_sha256})

    def finish_transport(self):
        return self._call('finish_transport',{})

    def transport_usage(self):
        return self._call('transport_usage',{})

    def persist(self, ordinal, operation, request, result):
        """DurableInvoker callback consumes the slot reserved before dispatch."""
        candidates=[x for x in self.receipts.values() if x['invoke_ordinal']==ordinal and x['operation']==operation and
                    x['request']==request and not x.get('used')]
        if self.stopped or not candidates: raise ValueError('Exact outstanding pre-reserved Python receipt required')
        entry=candidates[0]; entry['used']=True
        raw=canonical(result); identity=entry['id']
        try:
            # The immutable IPC response also independently binds this result.
            if self.store.payload(entry['response_id'])!=raw:
                raise ValueError('Durable original response differs from Python receipt')
            for offset in range(0,len(raw),CHUNK_BYTES):
                self.store.append(identity,offset,raw[offset:offset+CHUNK_BYTES])
            self.store.seal(identity,size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        except BaseException:
            self.stopped=True; raise

    def persist_state(self, record):
        raw=canonical(record); identity='state-'+str(self.state_ordinal).zfill(6)
        self.state_ordinal+=1
        self.store.write(identity,'runner_state',raw,case_ordinal=self.case_ordinal)
        return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def git_projection(store, identity, spool_path, commit, paths, files, case_ordinal=None):
    """Verify untouched Git --batch bytes before durable base64 projection."""
    if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):
        raise ValueError('Exact immutable Git commit required')
    if not isinstance(paths,list) or paths!=sorted(set(paths)) or set(files)!=set(paths):
        raise ValueError('Exact ordered immutable path inventory required')
    # Every projected byte can be reserved from metadata before opening the
    # spool. JSON keys and blob IDs are small; base64 size is exact.
    projected_bytes=2
    for index,path in enumerate(paths):
        if (not isinstance(path,str) or path.startswith('/') or '\\' in path
                or any(p in ('','.','..') for p in path.split('/'))):
            raise ValueError('Safe immutable Git path required')
        pin=files[path]
        if set(pin)!= {'blob','bytes','sha256'} or not re.fullmatch('[0-9a-f]{40}',str(pin['blob'])):
            raise ValueError('Exact frozen Git blob pin required')
        _sha(pin['sha256']); _integer(pin['bytes'],64*MIB,'blob bytes')
        projected_bytes+=(1 if index else 0)+len(canonical(path))+1+len(b'{"content":"')+4*((pin['bytes']+2)//3)+len(b'","sha":"'+pin['blob'].encode('ascii')+b'"}')
    store.reserve(identity,'git_projection',projected_bytes,case_ordinal=case_ordinal)
    buffer=bytearray(); offset=0; projected_sha=hashlib.sha256()
    def emit(raw):
        nonlocal offset
        projected_sha.update(raw)
        view=memoryview(raw)
        while view:
            count=min(CHUNK_BYTES-len(buffer),len(view)); buffer.extend(view[:count]); view=view[count:]
            if len(buffer)==CHUNK_BYTES:
                store.append(identity,offset,bytes(buffer)); offset+=len(buffer); buffer.clear()
    spool_path=_absolute(spool_path)
    parent,name=spool_path.rsplit('/',1); directory=_directory(parent)
    fd=None
    try:
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        _regular(fd); original=hashlib.sha256(); total=0
        stream=os.fdopen(os.dup(fd),'rb')
        try:
            emit(b'{')
            for index,path in enumerate(paths):
                pin=files[path]
                header=stream.readline(256)
                expected=(pin['blob']+' blob '+str(pin['bytes'])+'\n').encode('ascii')
                if header!=expected: raise ValueError('Exact Git --batch blob header required')
                original.update(header); total+=len(header)
                remaining=pin['bytes']; sha=hashlib.sha256()
                blob=hashlib.sha1(('blob '+str(remaining)+'\0').encode('ascii'))
                emit((b',' if index else b'')+canonical(path)+b':{"content":"')
                while remaining:
                    block=stream.read(min(CHUNK_BYTES,remaining))
                    if not block: raise ValueError('Truncated raw Git blob')
                    original.update(block); sha.update(block); blob.update(block)
                    emit(base64.b64encode(block)); remaining-=len(block); total+=len(block)
                newline=stream.read(1); original.update(newline); total+=len(newline)
                if newline!=b'\n' or sha.hexdigest()!=pin['sha256'] or blob.hexdigest()!=pin['blob']:
                    raise ValueError('Raw Git bytes differ from immutable blob pins')
                emit(b'","sha":"'+pin['blob'].encode('ascii')+b'"}')
            if stream.read(1): raise ValueError('Unexpected trailing raw Git batch bytes')
            emit(b'}')
        finally: stream.close()
        if os.fstat(fd).st_size!=total: raise ValueError('Raw Git spool changed while reading')
        os.fsync(fd); os.fsync(directory)
        if buffer: store.append(identity,offset,bytes(buffer)); offset+=len(buffer)
        if offset!=projected_bytes: raise ValueError('Exact reserved Git projection size differs')
        receipt=store.seal(identity,size=projected_bytes,sha256=projected_sha.hexdigest())
        return {'projection':receipt,'commit':commit,'single_cat_file_batch':True,
                'raw_git_receipt':{'path':spool_path,'bytes':total,
                                   'sha256':original.hexdigest(),'durable':True}}
    except BaseException as error:
        with store._locked() as (rfd,items,manifest): store._stop(rfd,error)
        raise
    finally:
        if fd is not None: os.close(fd)
        os.close(directory)


def _dispatch(value):
    """One CLI command; returned payloads are bounded chunks or metadata."""
    if not isinstance(value,dict): raise ValueError('Exact bridge command object required')
    action=value['action']; store=Store(value['root'])
    if action=='create':
        Store.create(value['root'],limits=value.get('limits'),case_limits=value.get('case_limits'))
        return {'schema':SCHEMA,'created':True,'execution_authorized':False}
    if action=='reserve':
        return store.reserve(value['id'],value['kind'],value['bytes'],value.get('sha256'),value.get('case_ordinal'))
    if action=='append':
        raw=value['content_base64']
        if not isinstance(raw,str) or len(raw)>4*((CHUNK_BYTES+2)//3):
            raise ValueError('Bounded canonical base64 chunk required')
        data=base64.b64decode(raw,validate=True)
        if base64.b64encode(data).decode('ascii')!=raw:
            raise ValueError('Canonical base64 chunk required')
        return store.append(value['id'],value['offset'],data)
    if action=='seal': return store.seal(value['id'],size=value.get('bytes'),sha256=value.get('sha256'))
    if action=='claim': return store.claim(value['id'])
    if action=='read': return store.read(value['id'],value.get('offset',0),value.get('length',CHUNK_BYTES))
    if action=='status':
        state=store.status(); state.pop('items')
        return state
    if action=='pending':
        state=store.status(); sealed={x['id'] for x in state['items'] if x['sealed']}
        pending=[x for x in state['items'] if x['kind']=='request' and x['sealed'] and
                 x['id'].replace('request-','response-',1) not in sealed]
        return {'schema':SCHEMA,'pending':pending[:1], 'pending_count':len(pending),'stopped':state['stopped']}
    if action=='git_projection':
        return git_projection(store,value['id'],value['spool_path'],value['commit'],
                              value['paths'],value['files'],value.get('case_ordinal'))
    raise ValueError('Fixed bridge action required')


def dispatch(value):
    """Retain the preceding complete supporting reply before the next action.

    Request byte count and SHA are links to the host's full request record.
    They are not a claim that its full tool request bytes were stored here.
    The final supporting acknowledgement remains outside this closure.
    """
    if not isinstance(value,dict): raise ValueError('Exact bridge command required')
    supports=value.get('support_receipts',[])
    if not isinstance(supports,list) or len(supports)>1:
        raise ValueError('One bounded preceding supporting reply required')
    store=Store(value['root'])
    for row in supports:
        expected={'ordinal','request_bytes','request_sha256','response_json','response_bytes','response_sha256'}
        if not isinstance(row,dict) or set(row)!=expected:
            raise ValueError('Exact supporting raw reply receipt fields required')
        _integer(row['ordinal'],40000,'support ordinal')
        _integer(row['request_bytes'],MAX_INPUT_BYTES+4096,'support request bytes')
        _sha(row['request_sha256']); _sha(row['response_sha256'])
        if not isinstance(row['response_json'],str): raise ValueError('Untouched serialized raw supporting reply required')
        raw=row['response_json'].encode('utf-8')
        if len(raw)>65536 or len(raw)!=row['response_bytes'] or hashlib.sha256(raw).hexdigest()!=row['response_sha256']:
            raise ValueError('Supporting raw reply size or SHA differs')
        store.write('support-'+str(row['ordinal']).zfill(8),'bridge_receipt',canonical(row))
    result=_dispatch(value)
    return {'result':result,'support_receipts_persisted':len(supports)}
