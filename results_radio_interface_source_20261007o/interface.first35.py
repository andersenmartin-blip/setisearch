"""Explicit wire-v2 / J / I / H structural projection. No native authority.

Only manufactured transport and ordinary fixture files are tested. A matching
projection cannot authenticate a callback, observer, process or codec result.
"""
import array
import ast
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
from types import ModuleType

MANIFEST_SHA256 = '1dcbbed438b110a7073f205371b940a04fbb6647140cb034bb0fba5910f4e95e'
MANIFEST_BYTES = 2193
PARENT = 'e6028af895bbaa5e558336ccf9b584353ea56eb6'
J_PATH = 'results_radio_loader_lifetime_preparation_20261006j/loader_lifetime.py'
L_PATH = 'results_radio_loader_collector_source_20261006l/receiver.py'
N_PATH = 'results_radio_callback_barrier_source_20261006n/acknowledgment.py'
I_CONTRACT = 'results_radio_codec12_execution_preparation_20261006i/contract.py'
I_PRODUCER = 'results_radio_codec12_execution_preparation_20261006i/codec12_control.py'
H_ROOT = 'results_radio_codec12_preparation_20261006h/'
OBJECT_BYTES = 1024 ** 2
FD_READ_BYTES = 8 * 1024 ** 2
RAW_BYTES = 8 * 1024 ** 2
MAX_EVENTS = 4096
MAX_PACKET = 2148


class Refusal(ValueError): pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(raw): return hashlib.sha256(raw).hexdigest()


def read_contexts(root):
    """Bounded held source reads only; no package/archive/native object reads."""
    root = Path(root)
    if not root.is_absolute() or root.resolve() != root:
        raise Refusal('canonical source root required')

    def read(relative, cap):
        path = root
        for part in Path(relative).parts:
            path = path / part
            if path.is_symlink(): raise Refusal('source symlink refused')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= cap:
                raise Refusal('bounded ordinary single-link source required')
            raw = handle.read(cap + 1)
            after = os.fstat(handle.fileno()); current = path.lstat()
            fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k)
                                                or getattr(before, k) != getattr(current, k) for k in fields):
                raise Refusal('held source changed')
        return raw

    manifest = read('results_radio_interface_source_20261007o/CONTEXT_INPUT_MANIFEST.json', MANIFEST_BYTES)
    info = inspect_manifest(manifest)
    raws = {name: read(name, pin['bytes']) for name, pin in info['files'].items()}
    return raws, manifest


def inspect_manifest(raw):
    if type(raw) is not bytes or len(raw) != MANIFEST_BYTES or digest(raw) != MANIFEST_SHA256:
        raise Refusal('exact prospectively published context manifest required')
    info = json.loads(raw)
    if info['authority_commit'] != PARENT or info['source_context_only'] is not True:
        raise Refusal('source-context authority differs')
    return info


class Context:
    def __init__(self, raws, manifest):
        info = inspect_manifest(manifest)
        if type(raws) is not dict or set(raws) != set(info['files']):
            raise Refusal('all nine exact source contexts required')
        for name, pin in info['files'].items():
            raw = raws[name]
            if type(raw) is not bytes or len(raw) != pin['bytes'] or digest(raw) != pin['sha256']:
                raise Refusal('immutable source-context drift: ' + name)
        self.raws = dict(raws); self.manifest = info

        def module(label, path):
            out = ModuleType('_radio_O_source_' + label)
            exec(compile(self.raws[path], path, 'exec'), out.__dict__)
            return out

        self.J = module('J', J_PATH); self.L = module('L', L_PATH)
        self.N = module('N', N_PATH); self.I = module('I_contract', I_CONTRACT)
        # Only the original public refusing function is compiled from I. The
        # producer's imports and every private/native function remain unexecuted.
        nodes = [node for node in ast.parse(self.raws[I_PRODUCER]).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'produce']
        if len(nodes) != 1: raise Refusal('one exact public I refusal function required')
        source = ast.Module(body=nodes, type_ignores=[])
        scope = {}; exec(compile(source, I_PRODUCER + ':public-produce-only', 'exec'), scope)
        self.I_public_produce = scope['produce']
        self.plan_binding()  # pin the original H status/order before transport

    def plan_binding(self):
        h_raws = {name: self.raws[H_ROOT + name] for name in self.I.H_PINS}
        plan, _, _ = self.I.inspect_documents(h_raws)
        scopes = plan['scope']['ordered_handoffs']
        if (len(scopes) != 12 or plan['scope']['primary'] != 'neighbor9'
                or plan['scope']['target'] != 'HD189733/HIP98505'):
            raise Refusal('original selected twelve-handoff source scope differs')
        for i, scope in enumerate(scopes):
            self.I.same([scope['handoff_index'], scope['role'], scope['scan']],
                        [i, self.I.ROLES[i // 6], self.I.LABELS[i % 6]])
        return {'schema': 'radio-O-HI-planned-source-binding-v1',
                'authority_commit': PARENT, 'H_plan_sha256': digest(h_raws['PLAN.json']),
                'I_producer_source_sha256': digest(self.raws[I_PRODUCER]),
                'H_status': plan['status'], 'H_execution_enabled': plan['execution_enabled'],
                'ordered_handoffs': json.loads(canonical(scopes)), 'planned_handoffs': 12,
                'actual_handoffs': 0, 'actual_codec_journal_events': 0,
                'codec_certificate': False, 'native_runtime_science_authority': False}


class SourceInterface:
    """Retain actual received fixture bytes/fds and explicit derived J events.

    EOF/wait values are fixture claims only. No positive ACK is sent, no native
    observer is implemented, and public release/dispatch cannot grant authority.
    """
    def __init__(self, context, process, executable, expected_files):
        self.context = context
        context.J.identity(process)
        self.fd_state = context.L.Receiver(process.get('local_pid'), executable, expected_files)
        self.j_state = context.J.LoaderLedger(process, executable, expected_files)
        self.process = json.loads(canonical(process))
        self.raw_records = []; self.projections = []; self.failures = []
        self.raw_bytes = 0; self.poisoned = False; self.finished = False
        self.last_fixture_ack_identity = None

    def decode(self, raw):
        identity = self.context.N.event_identity(raw)
        values = self.context.N.EVENT.unpack_from(raw)
        keys = ('magic', 'version', 'kind', 'sequence', 'pid', 'generation', 'namespace', 'load_base',
                'device', 'inode', 'bytes', 'mode', 'flags', 'mtime_ns', 'ctime_ns',
                'monotonic_ns', 'name_len', 'path_len')
        event = dict(zip(keys, values))
        if event['monotonic_ns'] == 0 or event['namespace'] != 0:
            raise Refusal('nonzero time and original base namespace required')
        tail = raw[100:]; split = event['name_len']
        try: event['loader_name'] = tail[:split].decode(); event['resolved_path'] = tail[split:].decode()
        except UnicodeError as exc: raise Refusal('unaltered UTF8 names required') from exc
        if event['kind'] != self.context.L.OPEN:
            if any(event[k] for k in ('load_base', 'device', 'inode', 'bytes', 'mode',
                                     'mtime_ns', 'ctime_ns', 'name_len', 'path_len')):
                raise Refusal('unexpected non-open fields')
        elif event['flags'] != 0:
            raise Refusal('unexpected object-open flags')
        return event, identity

    def project(self, event):
        L = self.context.L; kind = event['kind']; gen = event['generation']
        added = ['fixture process/start-time/namespace identity supplied to O']
        if kind == L.HANDSHAKE:
            name = 'handshake'
            payload = {'source_freeze_sha256': self.context.J.SOURCE_FREEZE_SHA256,
                       'loader_interface_version': 2}
            added.append('J expected source-context handshake value; absent from N wire')
        elif kind == L.OPEN:
            name = 'object_open'; held = self.fd_state.objects[gen]
            payload = {'object_id': gen, 'namespace_id': event['namespace'],
                       'loader_name': event['loader_name'], 'resolved_path': event['resolved_path'],
                       'file_pin': dict(held['file_pin'])}
            added.append('file pin checked by held ordinary fd; not mapped-inode evidence')
        elif kind == L.PREINIT: name = 'preinit'; payload = {'main_object_id': gen}
        elif kind == L.CLOSE: name = 'object_close'; payload = {'object_id': gen}
        else: raise Refusal('unrepresentable ACTIVITY/VETO is retained, never dropped into J')
        raw = canonical({'sequence': self.j_state.count, 'previous_sha256': self.j_state.previous,
                         'monotonic_ns': event['monotonic_ns'], 'process': self.process,
                         'kind': name, 'payload': payload})
        record = {'wire_sequence': event['sequence'], 'wire_version': 2,
                  'raw_packet_sha256': self.raw_records[-1]['sha256'],
                  'J_event_hex': raw.hex(), 'J_event_sha256': digest(raw),
                  'added_by_adapter_not_N_producer_claim': added,
                  'collector_authentication': False}
        # Preserve attempted projection even when original J rejects an alias.
        self.projections.append(record); self.j_state.consume(raw)

    def receive_fixture(self, channel):
        if self.poisoned or self.finished or self.fd_state.eof:
            raise Refusal('failed/closed source interface cannot resume')
        received = []; owned = False; raw = b''; record = None
        try:
            if channel.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
                raise Refusal('sequenced packet fixture channel required')
            raw, ancillary, flags, _ = channel.recvmsg(MAX_PACKET + 1, socket.CMSG_SPACE(16), socket.MSG_CMSG_CLOEXEC)
            self.raw_bytes += len(raw)
            record = {'raw_hex': raw.hex(), 'bytes': len(raw), 'sha256': digest(raw),
                      'receive_flags': flags, 'manufactured_transport': True,
                      'received_descriptors': 0, 'descriptors_retained': False}
            self.raw_records.append(record)
            bad = False
            for level, kind, body in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    width = array.array('i').itemsize; whole = len(body) // width * width
                    values = array.array('i'); values.frombytes(body[:whole]); received.extend(values)
                    if whole != len(body): bad = True
                else: bad = True
            record['received_descriptors'] = len(received)
            if bad or flags & ~(socket.MSG_EOR | socket.MSG_CMSG_CLOEXEC):
                raise Refusal('ancillary/truncation/unknown receive flags')
            if self.raw_bytes > RAW_BYTES or self.fd_state.sequence >= MAX_EVENTS:
                raise Refusal('finite raw/event source envelope exceeded')
            if not raw:
                if received or self.fd_state.phase != 'running': raise Refusal('EOF without complete fixture startup')
                self.fd_state.eof = True; record['EOF_is_not_native_wait_proof'] = True; return False
            event, identity = self.decode(raw)
            state = self.fd_state
            if (event['sequence'] != state.sequence or event['pid'] != state.pid
                    or event['monotonic_ns'] < state.time):
                raise Refusal('wire sequence/process/time differs')
            if event['kind'] in (self.context.L.ACTIVITY, self.context.L.VETO):
                raise Refusal('unrepresentable ACTIVITY/VETO is retained, never dropped into J')
            if event['kind'] == self.context.L.OPEN:
                if event['bytes'] > OBJECT_BYTES or state.read_bytes + event['bytes'] > FD_READ_BYTES:
                    raise Refusal('manufactured ordinary-object read envelope exceeded')
            state.transition(event, received)
            owned = event['kind'] == self.context.L.OPEN
            record['descriptors_retained'] = owned
            self.project(event)
            state.sequence += 1; state.time = event['monotonic_ns']
            self.last_fixture_ack_identity = identity
            record['accepted_structural_projection_only'] = True
            return True
        except BaseException as exc:
            self.poisoned = True; self.fd_state.poisoned = True
            self.failures.append({'reason': str(exc), 'raw_hex': raw.hex(),
                                  'received_descriptors': len(received), 'retained': owned})
            raise
        finally:
            if not owned:
                for fd in received: os.close(fd)

    def finish_fixture(self, waited_pid, exit_code):
        """Construct a labeled fixture terminal projection; never a C end event."""
        try:
            if self.poisoned or self.finished: raise Refusal('failed/closed interface cannot finish again')
            fd_receipt = self.fd_state.finish(waited_pid, exit_code)
            raw = canonical({'sequence': self.j_state.count, 'previous_sha256': self.j_state.previous,
                             'monotonic_ns': self.fd_state.time + 1, 'process': self.process,
                             'kind': 'collector_end', 'payload': {'event_loss_count': 0, 'exit_code': exit_code}})
            self.projections.append({'J_event_hex': raw.hex(), 'J_event_sha256': digest(raw),
                                     'wire_sequence': None, 'raw_packet_sha256': None,
                                     'added_by_adapter_not_N_producer_claim':
                                     ['fixture terminal constructed from unauthenticated external waited_pid/exit_code'],
                                     'N_collector_end_packet_observed': False, 'collector_authentication': False})
            self.j_state.consume(raw); j_receipt = self.j_state.finish()
            binding = self.context.plan_binding(); self.finished = True
            return json.loads(canonical({'schema': 'radio-O-explicit-source-interface-v1',
                    'status': 'MANUFACTURED_STRUCTURAL_PROJECTION_ONLY_NO_AUTHENTICATED_COLLECTION',
                    'authority_commit': PARENT, 'N_wire_version': 2, 'L_wire_v1_bytes_rewritten': False,
                    'raw_transport': self.raw_records, 'raw_received_bytes': self.raw_bytes,
                    'J_projection_provenance': self.projections, 'J_structural_receipt': j_receipt,
                    'held_fd_fixture_receipt': fd_receipt, 'HI_source_binding': binding,
                    'terminal_wait': {'waited_pid': waited_pid, 'exit_code': exit_code,
                                      'origin': 'externally supplied unauthenticated fixture', 'native_wait_observed': False},
                    'collector_authentication': False, 'mapped_inode_binding': False,
                    'runtime_qualified': False, 'codec_certificate': False, 'positive_ACKs_sent': 0,
                    'native_or_science_authority': False, 'H_allocation': False}))
        except BaseException as exc:
            self.poisoned = True
            self.failures.append({'terminal_refusal': str(exc), 'native_wait_observed': False})
            raise

    def evidence(self):
        return json.loads(canonical({'raw_records': self.raw_records, 'projections': self.projections,
                    'failures': self.failures, 'poisoned': self.poisoned, 'finished': self.finished,
                    'held_fixture_read_bytes': self.fd_state.read_bytes,
                    'retained_generations': [{k: v for k, v in row.items() if k != 'fd'}
                                             for _, row in sorted(self.fd_state.objects.items())],
                    'native_callback_observations': 0, 'positive_ACKs_sent': 0,
                    'native_runtime_codec_science_authority': False}))

    def close_fixture_descriptors(self): self.fd_state.close_retained_descriptors()


def release(*args, **kwargs): raise Refusal('O has no authenticated production observer; positive release closed')
def dispatch(*args, **kwargs): raise Refusal('O source interface grants no native/codec/science dispatch')
