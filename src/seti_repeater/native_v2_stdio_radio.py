"""Persistent, bounded local Store pipe service; no execution authority.

Each command is a canonical ASCII JSON line, followed by exactly ``bytes``
binary bytes for ``put``. Uploads use the existing Store's bounded durable
chunks internally, with one acknowledgement for the whole item. ``get`` is
for a local pipe: its acknowledgement line precedes exactly ``binary_bytes``
bytes. Large local payloads never need a shell argument or a tool stdout.

The full command header and a pre-reserved acknowledgement are charged to
the unchanged bridge_receipt bucket. The acknowledged result is fsynced before
being emitted. This does not durably store a tool's own final reply: complete
tool request/reply envelopes must separately be supplied as immutable ``put``
items, and a lost outer acknowledgement must close its caller without retry.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
import signal
import time

from .empty_null_radio import canonical
from . import native_v2_bridge_radio as bridge

SCHEMA = 'radio-native-v2-persistent-store-stdio-v1'
HEADER_BYTES = bridge.MAX_INPUT_BYTES
ACK_BYTES = 65536
MAX_COMMANDS = 512
MAX_SECONDS = 4800
OPERATION_SECONDS = 120


@contextmanager
def _timeout(seconds):
    """Own the service timer; refuse an unrelated timer rather than disable it."""
    previous = signal.getsignal(signal.SIGALRM)
    timer = signal.getitimer(signal.ITIMER_REAL)
    if timer != (0.0, 0.0):
        raise RuntimeError('Independent timer active; stdio service refused')
    def expired(signum, frame):
        raise TimeoutError('Bounded stdio command deadline exceeded; no retry')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _read_exact(stream, size):
    """Read at most one existing Store chunk; short pipe reads are legal."""
    output = bytearray()
    while len(output) < size:
        part = stream.read(size - len(output))
        if not part:
            raise EOFError('Incomplete declared stdio payload; no retry')
        output.extend(part)
    return bytes(output)


def _write_stream(stream, data):
    view = memoryview(data)
    while view:
        amount = stream.write(view)
        if amount is None or amount <= 0:
            raise OSError('Incomplete stdio output; acknowledgement uncertain')
        view = view[amount:]


class StdioService:
    """One irrevocable local service session using the original Store limits."""
    def __init__(self, store, *, session_id='stdio-session', seconds=MAX_SECONDS,
                 operation_seconds=OPERATION_SECONDS, commands=MAX_COMMANDS):
        if not isinstance(store, bridge.Store):
            raise ValueError('Concrete bounded filesystem Store required')
        for value, maximum in ((seconds, MAX_SECONDS),
                               (operation_seconds, OPERATION_SECONDS)):
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 < value <= maximum):
                raise ValueError('Finite hard service deadline required')
        bridge._integer(commands, MAX_COMMANDS, 'commands')
        if commands == 0:
            raise ValueError('Nonzero bounded command count required')
        self.store = store
        self.session_id = bridge._id(session_id)
        if len(self.session_id) > 48:
            raise ValueError('Bounded session identity suffix space required')
        self.ordinal = 0
        self.commands = commands
        self.operation_seconds = operation_seconds
        self.end = time.monotonic() + seconds
        self.closed = False
        self.store.write(self.session_id, 'bridge_receipt', canonical({
            'schema': SCHEMA, 'session_id': self.session_id,
            'commands': commands, 'seconds': seconds,
            'operation_seconds': operation_seconds,
            'execution_authorized': False, 'automatic_retry': False}))

    def _names(self):
        suffix = str(self.ordinal).zfill(6)
        return self.session_id + '-command-' + suffix, self.session_id + '-ack-' + suffix

    def _header(self, stream):
        raw = stream.readline(HEADER_BYTES + 2)
        if not raw:
            raise EOFError('Service EOF before explicit close; no retry')
        if not raw.endswith(b'\n') or len(raw) - 1 > HEADER_BYTES:
            raise ValueError('Bounded newline-framed stdio header required')
        encoded = raw[:-1]
        value = json.loads(encoded)
        if (not isinstance(value, dict) or canonical(value) != encoded
                or not encoded.isascii()):
            raise ValueError('Exact canonical ASCII stdio header required')
        common = {'schema', 'ordinal', 'action', 'case_ordinal'}
        extra = {'put': {'id', 'kind', 'bytes', 'sha256', 'reservation'},
                 'get': {'id'}, 'dispatch': {'command'}, 'close': set()}
        if (value.get('schema') != SCHEMA or type(value.get('ordinal')) is not int
                or value['ordinal'] != self.ordinal
                or value.get('action') not in extra
                or set(value) != common | extra[value['action']]):
            raise ValueError('Exact fresh stdio command identity and fields required')
        if value['case_ordinal'] is not None:
            bridge._integer(value['case_ordinal'], 7, 'case')
        return value, encoded

    def _put(self, value, stream):
        identity = bridge._id(value['id'])
        size = bridge._integer(value['bytes'], bridge.LIMITS['item_bytes'], 'payload bytes')
        digest = bridge._sha(value['sha256'])
        if value['kind'] not in bridge.KINDS or value['reservation'] not in ('new', 'existing'):
            raise ValueError('Existing fixed Store bucket and reservation mode required')
        if value['reservation'] == 'new':
            self.store.reserve(identity, value['kind'], size, digest, value['case_ordinal'])
        else:
            with self.store._locked(writing=True) as (rfd, items, manifest):
                fd = self.store._item(items, identity)
                try:
                    intent = bridge._json_small(fd, 'intent.json')
                    if (intent['kind'] != value['kind'] or intent['case_ordinal'] != value['case_ordinal']
                            or size > intent['reserved_bytes']
                            or intent['expected_sha256'] not in (None, digest)
                            or bridge._exists(fd, 'sealing.json') or bridge._exists(fd, 'sealed.json')):
                        raise ValueError('Exact unconsumed existing Store reservation required')
                    payload = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if bridge._regular(payload).st_size != 0:
                            raise ValueError('Existing reservation has partial payload; no retry')
                    finally:
                        os.close(payload)
                finally:
                    os.close(fd)
        hasher = hashlib.sha256()
        offset = 0
        while offset < size:
            block = _read_exact(stream, min(bridge.CHUNK_BYTES, size - offset))
            hasher.update(block)
            self.store.append(identity, offset, block)
            offset += len(block)
        if hasher.hexdigest() != digest:
            raise ValueError('Exact streamed payload SHA256 differs; no retry')
        return self.store.seal(identity, size=size, sha256=digest)

    def _dispatch(self, value):
        command = value['command']
        fields = {'pending': {'action'}, 'status': {'action'},
                  'claim': {'action', 'id'},
                  'git_projection': {'action', 'id', 'spool_path', 'commit',
                                     'paths', 'files', 'case_ordinal'}}
        if (not isinstance(command, dict) or 'root' in command
                or command.get('action') not in fields
                or set(command) != fields[command['action']]):
            raise ValueError('Fixed local metadata/projection action and pinned root required')
        if command.get('action') == 'git_projection':
            if command.get('case_ordinal') != value['case_ordinal']:
                raise ValueError('Exact projection case binding required')
        return bridge._dispatch({**command, 'root': self.store.root})

    @contextmanager
    def _get(self, value):
        """Verify the complete immutable item before its first outgoing byte."""
        payload = None
        try:
            with self.store._locked() as (rfd, items, manifest):
                fd = self.store._item(items, value['id'])
                try:
                    intent = bridge._json_small(fd, 'intent.json')
                    marker = bridge._json_small(fd, 'sealed.json')
                    if intent['case_ordinal'] != value['case_ordinal'] or bridge._exists(fd, 'payload'):
                        raise ValueError('Exact immutable local read case/file required')
                    payload = os.open('part', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    if bridge._regular(payload).st_size != marker['bytes']:
                        raise ValueError('Immutable local read size differs')
                    hasher = hashlib.sha256()
                    while block := os.read(payload, bridge.CHUNK_BYTES):
                        hasher.update(block)
                    if hasher.hexdigest() != marker['sha256']:
                        raise ValueError('Immutable local read digest differs before output')
                    os.lseek(payload, 0, os.SEEK_SET)
                finally:
                    os.close(fd)
            # The pinned sealed descriptor remains open; acknowledgement
            # persistence must acquire the Store lock independently.
            yield {**marker, 'binary_bytes': marker['bytes']}, payload
        finally:
            if payload is not None:
                os.close(payload)

    def _ack(self, identity, result):
        encoded = canonical({'schema': SCHEMA, 'ordinal': self.ordinal,
                             'result': result, 'automatic_retry': False})
        if len(encoded) > ACK_BYTES:
            raise ValueError('Bounded metadata acknowledgement exceeded')
        for offset in range(0, len(encoded), bridge.CHUNK_BYTES):
            self.store.append(identity, offset, encoded[offset:offset + bridge.CHUNK_BYTES])
        self.store.seal(identity, size=len(encoded), sha256=hashlib.sha256(encoded).hexdigest())
        return encoded + b'\n'

    def one(self, reader, writer):
        if self.closed:
            raise RuntimeError('Stdio session permanently closed')
        if self.ordinal >= self.commands:
            self.closed = True
            self.store.stop('Stdio command count exhausted; no retry')
            raise RuntimeError('Stdio command count exhausted; no retry')
        try:
            remaining = min(self.operation_seconds, self.end - time.monotonic())
            if remaining <= 0:
                raise TimeoutError('Stdio session deadline exhausted; no retry')
            with _timeout(remaining):
                value, raw = self._header(reader)
                command_id, ack_id = self._names()
                # Both intents are durable before any upload/action starts.
                self.store.write(command_id, 'bridge_receipt', raw, case_ordinal=value['case_ordinal'])
                self.store.reserve(ack_id, 'bridge_receipt', ACK_BYTES, case_ordinal=value['case_ordinal'])
                if value['action'] == 'get':
                    with self._get(value) as (result, fd):
                        _write_stream(writer, self._ack(ack_id, result))
                        outgoing = hashlib.sha256()
                        outgoing_bytes = 0
                        while block := os.read(fd, bridge.CHUNK_BYTES):
                            outgoing.update(block)
                            outgoing_bytes += len(block)
                            _write_stream(writer, block)
                        if (outgoing_bytes != result['binary_bytes']
                                or outgoing.hexdigest() != result['sha256']
                                or bridge._regular(fd).st_size != result['binary_bytes']):
                            raise ValueError('Immutable read changed during output; no retry')
                        writer.flush()
                else:
                    if value['action'] == 'put':
                        result = self._put(value, reader)
                    elif value['action'] == 'dispatch':
                        result = self._dispatch(value)
                    else:
                        result = {'closed': True, 'execution_authorized': False}
                    _write_stream(writer, self._ack(ack_id, result))
                    writer.flush()
                self.ordinal += 1
                self.closed = value['action'] == 'close'
                return not self.closed
        except BaseException as error:
            self.closed = True
            self.store.stop(error)
            raise

    def serve(self, reader, writer):
        while self.one(reader, writer):
            pass
        return self.ordinal
