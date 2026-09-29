"""Incremental engineering journal, immutable recovery, and fail-closed publication.

The original journal state machine is unchanged. Genesis is stored once; each
event carries both original revision digests and a link to its predecessor.
Every historical pointer version is charged, even though Git may compress it.
Readers reconstruct bytes only. No scientific store, RNG lease, or resume API.
"""
from dataclasses import dataclass
import hashlib
import json
import time

from . import whole_cadence_journal_radio as j
from . import whole_cadence_remote_radio as git
from . import whole_cadence_batch_radio as batch
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest, _sha

ROOT = 'results_radio_incremental_journal_2026-09-29'
PREFIXES = tuple(ROOT + '/' + name for name in ('complete01', 'lost01'))
SCHEMA = 'radio-incremental-engineering-journal-v1'
LIMITS = {'calls': 240, 'request_bytes': 4*1024**2,
          'response_bytes': 16*1024**2, 'seconds': 600}
LEDGER_CAP = 65536
ARTIFACT_CAP = 4096
MAX_EVENTS = 16
Stopped = git.Stopped


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(raw):
    if not isinstance(raw, bytes):
        raise ValueError('Canonical byte payload required')
    result = json.loads(raw)
    if canonical(result) != raw:
        raise ValueError('Noncanonical journal bytes')
    return result


def validate_genesis(raw, expected_sha256):
    _sha(expected_sha256, 'independent genesis')
    if sha(raw) != expected_sha256:
        raise ValueError('Genesis differs from independent freeze')
    doc = load(raw)
    j.replay(doc)
    m = doc['manifest']
    if (doc['events'] or m['mode'] != 'engineering'
            or m['namespace'] not in PREFIXES or len(m['cases']) != 1
            or m['required_artifacts'] != ['witness.json']
            or m['caps']['ledger_reserve_bytes'] != LEDGER_CAP):
        raise ValueError('Only fresh fixed engineering genesis admitted')
    return doc


def pointer(doc, genesis_sha256, last_chunk_sha256):
    return canonical({'schema': SCHEMA, 'genesis_sha256': genesis_sha256,
        'event_count': len(doc['events']), 'last_chunk_sha256': last_chunk_sha256,
        'revision_sha256': digest(doc), 'revision_bytes': len(canonical(doc)),
        'restoration_only': True, 'execution_restart_authorized': False})


@dataclass(frozen=True)
class History:
    """Verified immutable bytes; deliberately has no write/consume/lease methods."""
    genesis: bytes
    chunks: tuple
    head: bytes
    revisions: tuple
    ledger_bytes: int

    @property
    def document(self):
        return load(self.revisions[-1])

    def summary(self):
        return {'versions': len(self.revisions), 'ledger_bytes': self.ledger_bytes,
            'full_snapshot_bytes': sum(map(len, self.revisions)),
            'revision_sha256s': [sha(x) for x in self.revisions],
            'revision_bytes': [len(x) for x in self.revisions],
            'states': [c['status'] for c in j.replay(self.document)['cases']],
            'execution_restart_authorized': False, 'scientific_execution_authorized': False}


def restore(genesis, chunks, head, *, expected_genesis_sha256, expected_head_sha256,
            ledger_cap=LEDGER_CAP):
    if type(ledger_cap) is not int or not 0 < ledger_cap <= LEDGER_CAP:
        raise ValueError('Bounded integer ledger cap required')
    _sha(expected_head_sha256, 'independent pointer')
    if sha(head) != expected_head_sha256:
        raise ValueError('Pointer differs from immutable external pin')
    doc = validate_genesis(genesis, expected_genesis_sha256)
    supplied = load(head)
    count = supplied.get('event_count')
    if (type(count) is not int or not 0 <= count <= MAX_EVENTS
            or len(chunks) != count):
        raise ValueError('Complete bounded event prefix required')
    previous = j.ZERO
    revisions = [genesis]
    charged = len(genesis) + len(pointer(doc, expected_genesis_sha256, previous))
    for index, raw in enumerate(chunks):
        rec = load(raw)
        if (set(rec) != {'schema', 'index', 'previous_chunk_sha256', 'before_sha256',
                         'after_sha256', 'after_bytes', 'record'}
                or rec['schema'] != SCHEMA or type(rec['index']) is not int
                or rec['index'] != index or rec['previous_chunk_sha256'] != previous
                or rec['before_sha256'] != digest(doc)):
            raise ValueError('Chunk chain, prefix or prior revision differs')
        following = j.append(doc, rec['record']['event'])
        payload = canonical(following)
        if (rec['record'] != following['events'][-1]
                or rec['after_sha256'] != sha(payload)
                or type(rec['after_bytes']) is not int or rec['after_bytes'] != len(payload)):
            raise ValueError('Original revision checkpoint differs')
        previous = sha(raw)
        charged += len(raw) + len(pointer(following, expected_genesis_sha256, previous))
        revisions.append(payload)
        doc = following
    if pointer(doc, expected_genesis_sha256, previous) != head:
        raise ValueError('Final pointer, authority or original revision differs')
    if charged > ledger_cap:
        raise ValueError('Cumulative unique chunks and all pointer versions exceed cap')
    return History(genesis, tuple(chunks), head, tuple(revisions), charged)


def initial(raw):
    validate_genesis(raw, sha(raw))
    h = pointer(load(raw), sha(raw), j.ZERO)
    return restore(raw, (), h, expected_genesis_sha256=sha(raw), expected_head_sha256=sha(h))


def extend(history, event, *, ledger_cap=LEDGER_CAP):
    # Revalidate bytes, so a manually constructed dataclass is no authority.
    history = restore(history.genesis, history.chunks, history.head,
        expected_genesis_sha256=sha(history.genesis), expected_head_sha256=sha(history.head),
        ledger_cap=ledger_cap)
    before = history.document
    after = j.append(before, event)
    raw = canonical({'schema': SCHEMA, 'index': len(history.chunks),
        'previous_chunk_sha256': j.ZERO if not history.chunks else sha(history.chunks[-1]),
        'before_sha256': digest(before), 'after_sha256': digest(after),
        'after_bytes': len(canonical(after)), 'record': after['events'][-1]})
    h = pointer(after, sha(history.genesis), sha(raw))
    return restore(history.genesis, history.chunks + (raw,), h,
        expected_genesis_sha256=sha(history.genesis), expected_head_sha256=sha(h), ledger_cap=ledger_cap)


class Meter:
    """Shared across writer and read-only recovery. Failed calls are charged."""
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.calls = self.request_bytes = self.response_bytes = 0
        self.events = []

    def summary(self):
        return {'calls': self.calls, 'request_bytes': self.request_bytes,
            'response_bytes': self.response_bytes, 'seconds': self.clock()-self.started}


class Client:
    def __init__(self, invoke, *, meter=None, read_only=False):
        self.invoke = invoke
        self.meter = meter if meter is not None else Meter()
        self.read_only = read_only
        self.stopped = False

    def readonly_recovery(self):
        # Same finite meter and invoke, no reset; method allowlist excludes writes.
        return Client(self.invoke, meter=self.meter, read_only=True)

    def call(self, method, **params):
        if self.stopped:
            raise Stopped('Client stopped; only a separate read-only recovery is permitted')
        allowed = ('fetch', 'fetch_file') if self.read_only else (
            'fetch', 'fetch_file', 'create_tree', 'create_commit', 'update_ref')
        if method not in allowed:
            raise ValueError('Operation outside client authority')
        if method == 'fetch':
            url = params.get('url', '')
            if not url.startswith('https://api.github.com/repos/'+git.REPO+'/git/'):
                raise ValueError('Read destination differs')
        elif params.get('repository_full_name') != git.REPO:
            raise ValueError('Repository differs')
        if method == 'fetch_file':
            git.safe_path(params['path']); git.git_sha(params['ref'])
            if not any(params['path'].startswith(p+'/') for p in PREFIXES) or params.get('encoding') != 'base64':
                raise ValueError('Immutable incremental namespace read required')
        if method == 'update_ref' and (params.get('branch_name') != git.BRANCH or params.get('force') is not False):
            raise ValueError('Only the fixed fast-forward branch is admitted')
        if method == 'create_tree':
            entries = params['tree_elements']
            if not 1 <= len(entries) <= 3 or len({e['path'] for e in entries}) != len(entries):
                raise ValueError('Bounded distinct event/pointer/artifact batch required')
            for e in entries:
                if (set(e) != {'path', 'mode', 'type', 'content'} or e['mode'] != '100644'
                        or e['type'] != 'blob' or not isinstance(e['content'], str)
                        or not e['content'].isascii()
                        or not any(e['path'].startswith(p+'/') for p in PREFIXES)):
                    raise ValueError('Fixed ASCII content namespace required')
                git.safe_path(e['path'])
        request_size = len(canonical(params))
        if request_size > 65536:
            raise ValueError('Single request cap exceeded before dispatch')
        # Reserve a finite reply before dispatch; charge it fully if reply is lost.
        reserve = 1048576 if method == 'fetch' else 131072
        m = self.meter
        event = None
        try:
            if (m.calls >= LIMITS['calls'] or m.clock()-m.started > LIMITS['seconds']
                    or m.request_bytes+request_size > LIMITS['request_bytes']
                    or m.response_bytes+reserve > LIMITS['response_bytes']):
                raise ValueError('Cumulative transport capacity exhausted before dispatch')
            m.calls += 1; m.request_bytes += request_size; m.response_bytes += reserve
            event = {'index': m.calls, 'method': method, 'request_sha256': digest(params),
                'request_bytes': request_size, 'response_reserved_bytes': reserve,
                'started_seconds': m.clock()-m.started, 'read_only': self.read_only}
            m.events.append(event)
            result = self.invoke(method, params)
            raw = canonical(result)
            event.update(response_bytes=len(raw), response_sha256=sha(raw), ended_seconds=m.clock()-m.started)
            # Oversized observed replies are charged in full, never clipped.
            m.response_bytes += len(raw)-reserve
            if len(raw) > reserve or m.clock()-m.started > LIMITS['seconds'] or not isinstance(result, dict):
                raise ValueError('Reply cap/time/type failed after dispatch')
            return result
        except BaseException as error:
            self.stopped = True
            if event is not None:
                event.update(error=repr(error), automatic_retry=False)
            raise Stopped('Stopped without retry: '+str(error)) from error


class Reader:
    """Only immutable Git reads, using the existing verified tree/blob decoder."""
    _get = git.GitStore._get
    _head = git.GitStore._head
    _commit = git.GitStore._commit
    _tree = git.GitStore._tree
    _file = git.GitStore._file
    _blob = git.GitStore._blob

    def __init__(self, client, prefix, genesis_sha256):
        if prefix not in PREFIXES:
            raise ValueError('Unknown prospective namespace')
        _sha(genesis_sha256, 'genesis')
        self.client = client; self.prefix = prefix; self.genesis_sha256 = genesis_sha256
        self.trees = {}; self.commits = {}; self.blobs = {}; self.blob_paths = {}

    def read(self, commit, *, expected_pointer_sha256=None):
        git.git_sha(commit)
        def readfile(path, cap):
            h = self._file(commit, self.prefix+'/'+path)
            return self._blob(h, cap, fresh=True)
        genesis = readfile('genesis.json', LEDGER_CAP)
        h = readfile('head.json', 2048)
        info = load(h); count = info.get('event_count')
        if type(count) is not int or not 0 <= count <= MAX_EVENTS:
            raise ValueError('Invalid prefix count before read')
        chunks = tuple(readfile(f'events/{i:04d}.json', LEDGER_CAP) for i in range(count))
        history = restore(genesis, chunks, h, expected_genesis_sha256=self.genesis_sha256,
            expected_head_sha256=expected_pointer_sha256 or sha(h))
        if history.document['manifest']['namespace'] != self.prefix:
            raise ValueError('Namespace binding differs')
        # A stale pointer inside a newer tree must not hide an already retained
        # event or artifact. Account for every physical file in this namespace.
        tree = self._commit(commit)['tree']
        for part in self.prefix.split('/'):
            entry = self._tree(tree).get(part)
            if entry is None or (entry['mode'], entry['type']) != ('040000','tree'):
                raise ValueError('Missing ordinary namespace directory')
            tree = entry['sha']
        found = set()
        def walk(tree_sha, prefix='', depth=0):
            if depth > 3:
                raise ValueError('Unexpected namespace tree depth')
            for name, entry in self._tree(tree_sha).items():
                path = prefix+name
                if (entry['mode'], entry['type']) == ('040000','tree'):
                    walk(entry['sha'], path+'/', depth+1)
                elif (entry['mode'], entry['type']) == ('100644','blob'):
                    found.add(path)
                    if len(found) > MAX_EVENTS+3:
                        raise ValueError('Unexpected namespace file inventory')
                else:
                    raise ValueError('Nonordinary namespace entry')
        walk(tree)
        expected = {'genesis.json','head.json'} | {f'events/{i:04d}.json' for i in range(count)}
        for case in j.replay(history.document)['cases']:
            expected |= {'artifacts/'+case['binding']['case_identity']+'/'+name for name in case['artifacts']}
        if found != expected:
            raise ValueError('Pointer omits retained event/artifact or inventory is incomplete')
        return history

    def verify_artifacts(self, commit, history):
        used = 0; artifacts = {}
        for case in j.replay(history.document)['cases']:
            for name, rec in case['artifacts'].items():
                path = self.prefix+'/artifacts/'+case['binding']['case_identity']+'/'+name
                payload = self._blob(self._file(commit, path), ARTIFACT_CAP, fresh=True)
                if len(payload) != rec['size'] or sha(payload) != rec['sha256']:
                    raise ValueError('External artifact differs from journal receipt')
                used += len(payload); artifacts[path] = payload
        if used > ARTIFACT_CAP:
            raise ValueError('Cumulative artifacts exceed prospective cap')
        return artifacts


class Session:
    """One process-local engineering session; every failure poisons it permanently."""
    _expected_tree = batch.Store._expected_tree
    _assert_absent = batch.Store._assert_absent
    _head = Reader._head
    _get = Reader._get
    _commit = Reader._commit
    _tree = Reader._tree
    _file = Reader._file
    _blob = Reader._blob

    def __init__(self, client, prefix, genesis, *, freeze_commit, execution_verifier):
        self.reader = Reader(client, prefix, sha(genesis))
        self.client = client; self.prefix = prefix; self.genesis = genesis
        self.freeze_commit = git.git_sha(freeze_commit)
        self.execution_verifier = execution_verifier
        self.trees = {}; self.commits = {}; self.blobs = {}; self.blob_paths = {}
        self.stopped = False; self.closed = False; self.history = None; self.head = None
        self.receipts = []; self.artifact_bytes = 0; self.started = None

    def begin(self):
        if self.stopped or self.closed or self.history is not None:
            raise Stopped('Session cannot begin or resume twice')
        try:
            self.execution_verifier()
            self.head = self._head()
            # Later unrelated commits may retain this fresh genesis; pin both
            # freeze and current bytes. Any consumed namespace is unrestartable.
            frozen = self.reader.read(self.freeze_commit)
            current = self.reader.read(self.head)
            if current.genesis != self.genesis or current.chunks or current.head != frozen.head:
                raise ValueError('Only unconsumed frozen genesis permits begin; no resume')
            self.history = current; self.started = self.client.meter.clock()
            return current
        except BaseException:
            self.stopped = True
            raise

    def append(self, event, *, artifact=None, lose_acknowledgement=False):
        if self.stopped or self.closed or self.history is None:
            raise Stopped('No active session; recovery never recreates a writer')
        candidate = None
        try:
            self.execution_verifier()
            if self.client.meter.clock()-self.started > 120:
                raise ValueError('Engineering session time exhausted')
            following = extend(self.history, event)
            payloads = {self.prefix+f'/events/{len(self.history.chunks):04d}.json': following.chunks[-1],
                        self.prefix+'/head.json': following.head}
            added = 0
            if event['kind'] == 'artifact':
                if (not isinstance(artifact, bytes) or not artifact.isascii()
                        or event['size'] != len(artifact) or event['sha256'] != sha(artifact)):
                    raise ValueError('Exact ASCII artifact required with receipt')
                case = j.replay(following.document)['cases'][-1]
                path = self.prefix+'/artifacts/'+case['binding']['case_identity']+'/'+event['name']
                payloads[path] = artifact; added = len(artifact)
            elif artifact is not None:
                raise ValueError('Artifact bytes without event forbidden')
            if self.artifact_bytes+added > ARTIFACT_CAP:
                raise ValueError('Cumulative artifact capacity exhausted before mutation')
            if event['kind'] == 'consume' and (event['milliseconds'] != 120000 or event['artifact_bytes'] != ARTIFACT_CAP):
                raise ValueError('Exact fixed engineering reservation required')
            if self._head() != self.head:
                raise ValueError('Branch advanced before publication')
            before = self._commit(self.head)
            changes = {}
            for path, payload in payloads.items():
                if path != self.prefix+'/head.json':
                    self._assert_absent(self.head, path)
                changes[path] = git.git_object('blob', payload)
            self.candidate_trees = {}
            expected_tree = self._expected_tree(before['tree'], changes)
            made = self.client.call('create_tree', repository_full_name=git.REPO, base_tree_sha=before['tree'],
                tree_elements=[{'path':p, 'mode':'100644', 'type':'blob', 'content':v.decode('ascii')}
                               for p,v in sorted(payloads.items())])
            if git.git_sha(made['sha']) != expected_tree:
                raise ValueError('Server tree differs from exact preserved parent tree')
            self.trees.update(self.candidate_trees)
            made = self.client.call('create_commit', repository_full_name=git.REPO, parent_sha=self.head,
                tree_sha=expected_tree, message='Incremental engineering journal '+self.prefix.rsplit('/',1)[-1]
                    +' event '+str(len(self.history.chunks)))
            candidate = git.git_sha(made['sha'])
            if self._commit(candidate) != {'tree':expected_tree,'parents':[self.head]}:
                raise ValueError('Candidate tree/parent differs')
            if self._head() != self.head:
                raise ValueError('Concurrent branch advance; no rebase or retry')
            receipt = {'parent': self.head, 'candidate': candidate, 'tree': expected_tree,
                'files': changes, 'publication_bytes': sum(map(len,payloads.values())),
                'expected_pointer_sha256': sha(following.head), 'phase': 'before_update'}
            self.receipts.append(receipt)
            reply = self.client.call('update_ref', repository_full_name=git.REPO, branch_name=git.BRANCH,
                sha=candidate, force=False)
            if lose_acknowledgement:
                # Deliberate application-boundary fault. Transport response is
                # retained by the broker; it must not grant session authority.
                receipt['phase'] = 'injected_acknowledgement_loss'
                raise OSError('Injected loss of successful update response at session boundary')
            if reply.get('success') is not True:
                raise ValueError('Publication not acknowledged')
            for path, expected in payloads.items():
                raw = self._blob(self._file(candidate,path), max(1,len(expected)), fresh=True)
                if raw != expected:
                    raise ValueError('Immutable postpublication bytes differ')
            if self._head() != candidate:
                raise ValueError('Postpublication branch changed')
            if self.client.meter.clock()-self.started > 120:
                raise ValueError('Publication exceeded complete session time cap')
            receipt.update(phase='immutable_bytes_verified', ledger_bytes=following.ledger_bytes,
                artifact_bytes=self.artifact_bytes+added)
            self.head = candidate; self.history = following; self.artifact_bytes += added
            if event['kind'] == 'finish':
                self.closed = True
            return following
        except BaseException as error:
            self.stopped = True
            self.receipts.append({'candidate':candidate, 'error':repr(error), 'automatic_retry':False,
                                  'consumption_may_have_landed':True})
            raise
