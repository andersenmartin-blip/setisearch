"""New O integration controls only; manufactured packets and retained files."""
import array
import builtins
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import threading
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location('radio_O_tested', HERE / 'interface.py')
o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
RAWS, MANIFEST = o.read_contexts(ROOT)
CTX = o.Context(RAWS, MANIFEST)
EVIDENCE = []


def pin(raw): return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ContextTests(unittest.TestCase):
    def setUp(self): self.inputs = []
    def tearDown(self):
        EVIDENCE.append({'test': self.id(), 'inputs': self.inputs,
                         'native_runtime_codec_science_authority': False})

    def mutated(self, path, transform):
        raws = dict(RAWS); raws[path] = transform(raws[path])
        self.inputs.append({'context_path': path, 'changed_raw_hex': raws[path].hex()})
        return raws

    def test_exact_plan_binding_retains_all_twelve_roles_windows_and_banks(self):
        b = CTX.plan_binding()
        self.assertEqual(b['planned_handoffs'], 12); self.assertEqual(b['actual_handoffs'], 0)
        self.assertEqual([x['chunk_index'] for x in b['ordered_handoffs']], [159] * 6 + [156] * 6)
        self.assertEqual(len({x['receiver_bank_sha256'] for x in b['ordered_handoffs']}), 2)
        self.assertEqual(b['H_execution_enabled'], False); self.assertFalse(b['codec_certificate'])

    def test_changed_I_producer_raw_refused_before_source_execution(self):
        raws = self.mutated(o.I_PRODUCER, lambda b: b + b'\n')
        with self.assertRaises(o.Refusal): o.Context(raws, MANIFEST)

    def test_H_role_bank_transplant_refused(self):
        def change(raw):
            v = json.loads(raw); v['scope']['ordered_handoffs'][0] = v['scope']['ordered_handoffs'][6]
            return o.canonical(v)
        with self.assertRaises(o.Refusal): o.Context(self.mutated(o.H_ROOT + 'PLAN.json', change), MANIFEST)

    def test_H_false_to_zero_status_change_refused(self):
        def change(raw):
            v = json.loads(raw); v['execution_enabled'] = 0; return o.canonical(v)
        with self.assertRaises(o.Refusal): o.Context(self.mutated(o.H_ROOT + 'PLAN.json', change), MANIFEST)

    def test_missing_context_cannot_be_substituted_by_manifest(self):
        raws = dict(RAWS); raws.pop(o.J_PATH); self.inputs.append({'omitted': o.J_PATH})
        with self.assertRaises(o.Refusal): o.Context(raws, MANIFEST)

    def test_self_rehashed_manifest_has_no_external_authority(self):
        v = json.loads(MANIFEST); v['files'][o.J_PATH]['sha256'] = 'a' * 64
        raw = o.canonical(v); self.inputs.append({'self_rehashed_manifest_hex': raw.hex()})
        with self.assertRaises(o.Refusal): o.Context(RAWS, raw)

    def test_original_I_public_produce_refuses(self):
        with self.assertRaisesRegex(ValueError, 'BLOCKED'): CTX.I_public_produce()

    def test_original_N_positive_release_refuses(self):
        with self.assertRaisesRegex(ValueError, 'positive release closed'): CTX.N.release()

    def test_context_loading_does_not_import_native_scientific_packages(self):
        prior = builtins.__import__; attempts = []
        def guard(name, *args, **kwargs):
            if name.split('.')[0] in ('numpy', 'h5py', 'hdf5plugin'):
                attempts.append(name); raise AssertionError('native scientific import attempted')
            return prior(name, *args, **kwargs)
        builtins.__import__ = guard
        try: loaded = o.Context(RAWS, MANIFEST); self.assertEqual(loaded.plan_binding()['actual_handoffs'], 0)
        finally: builtins.__import__ = prior
        self.inputs.append({'native_import_attempts': attempts}); self.assertEqual(attempts, [])


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.folder = HERE / 'FIXTURE_INPUTS' / self._testMethodName
        self.folder.mkdir(parents=True, exist_ok=False)
        self.main = self.folder / 'ordinary-main.bin'; self.plugin = self.folder / 'ordinary-transient.bin'
        for path, raw in ((self.main, b'ordinary manufactured main; not executable\n'),
                          (self.plugin, b'ordinary manufactured transient; not a library\n')):
            with path.open('xb') as out: out.write(raw)
        self.process = {'local_pid': 1234, 'outer_pid': 5678, 'starttime_ticks': 910,
                        'namespace_device': 11, 'namespace_inode': 12}
        self.expected = {str(p): pin(p.read_bytes()) for p in (self.main, self.plugin)}
        self.target = o.SourceInterface(CTX, self.process, str(self.main), self.expected)
        self.a, self.b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.inputs = []; self.receipt = None

    def tearDown(self):
        record = {'test': self.id(), 'inputs': self.inputs, 'interface_evidence': self.target.evidence(),
                  'receipt': self.receipt, 'ordinary_retained_inputs':
                  [{'path': str(p.relative_to(ROOT)), 'raw_hex': p.read_bytes().hex(), 'pin': pin(p.read_bytes())}
                   for p in (self.main, self.plugin)], 'native_runtime_codec_science_authority': False}
        EVIDENCE.append(record)
        self.target.close_fixture_descriptors(); self.a.close(); self.b.close()

    def packet(self, kind, sequence, generation=0, path=None, name=None, **changes):
        fields = dict(magic=b'RLA1', version=2, kind=kind, sequence=sequence, pid=1234, generation=generation,
                      namespace=0, load_base=0, device=0, inode=0, bytes=0, mode=0, flags=2 if kind==1 else 0,
                      mtime_ns=0, ctime_ns=0, monotonic_ns=sequence+1)
        if path is not None:
            st = path.stat(); fields.update(CTX.L.identity(st)); fields['load_base'] = 4096
            name = str(path) if name is None else name
        else: name = ''; path = ''
        fields.update(changes); n = name.encode(); p = str(path).encode()
        ordered = ('magic', 'version', 'kind', 'sequence', 'pid', 'generation', 'namespace', 'load_base',
                   'device', 'inode', 'bytes', 'mode', 'flags', 'mtime_ns', 'ctime_ns', 'monotonic_ns')
        return CTX.N.EVENT.pack(*(fields[k] for k in ordered), len(n), len(p)) + n + p

    def send(self, raw, path=None, ancillary=None):
        self.inputs.append({'packet_hex': raw.hex(), 'ordinary_fd_source': str(path) if path else None})
        fd = os.open(path, os.O_RDONLY) if path else None
        try:
            records = ancillary if ancillary is not None else (
                [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [fd]))] if fd is not None else [])
            self.b.sendmsg([raw], records)
        finally:
            if fd is not None: os.close(fd)
        return self.target.receive_fixture(self.a)

    def startup(self):
        self.send(self.packet(1, 0)); self.send(self.packet(2, 1, 1, self.main, ''), self.main)
        self.send(self.packet(3, 2, 1))

    def eof(self):
        self.b.shutdown(socket.SHUT_WR); self.assertFalse(self.target.receive_fixture(self.a))

    def complete(self):
        self.startup(); self.send(self.packet(2, 3, 2, self.plugin), self.plugin)
        self.send(self.packet(4, 4, 2)); self.eof()
        self.receipt = self.target.finish_fixture(1234, 0); return self.receipt

    def test_v2_raw_packets_preserved_and_transient_generation_retained(self):
        r = self.complete()
        self.assertFalse(r['L_wire_v1_bytes_rewritten'])
        self.assertEqual(r['raw_transport'][0]['raw_hex'], self.inputs[0]['packet_hex'])
        self.assertEqual(r['J_structural_receipt']['transient_generations_retained'], 1)
        self.assertEqual(r['held_fd_fixture_receipt']['transient_generations_retained'], 1)
        self.assertEqual(r['HI_source_binding']['actual_handoffs'], 0)

    def test_projection_labels_added_handshake_identity_and_terminal(self):
        r = self.complete(); p = r['J_projection_provenance']
        self.assertIn('absent from N wire', ' '.join(p[0]['added_by_adapter_not_N_producer_claim']))
        self.assertIsNone(p[-1]['wire_sequence']); self.assertFalse(p[-1]['N_collector_end_packet_observed'])
        self.assertFalse(r['terminal_wait']['native_wait_observed'])
        for record in p: self.assertFalse(record['collector_authentication'])

    def test_old_wire_is_not_rewritten(self):
        raw = self.packet(1, 0, version=1)
        with self.assertRaises(ValueError): self.send(raw)
        self.assertEqual(self.target.evidence()['raw_records'][0]['raw_hex'], raw.hex())

    def test_wrong_process_refused(self):
        with self.assertRaises(ValueError): self.send(self.packet(1, 0, pid=1235))

    def test_out_of_order_wire_refused(self):
        with self.assertRaises(ValueError): self.send(self.packet(1, 1))

    def test_time_regression_refused(self):
        self.send(self.packet(1, 0, monotonic_ns=10))
        with self.assertRaises(ValueError): self.send(self.packet(2, 1, 1, self.main, ''), self.main)

    def test_fd_substitution_refused_without_leak(self):
        self.send(self.packet(1, 0)); before = len(os.listdir('/proc/self/fd'))
        with self.assertRaises(ValueError): self.send(self.packet(2, 1, 1, self.main, ''), self.plugin)
        self.assertEqual(len(os.listdir('/proc/self/fd')), before)

    def test_descriptor_attached_to_handshake_is_closed(self):
        before = len(os.listdir('/proc/self/fd'))
        with self.assertRaises(ValueError): self.send(self.packet(1, 0), self.main)
        self.assertEqual(len(os.listdir('/proc/self/fd')), before)

    def test_ancillary_truncation_descriptors_closed(self):
        fd = os.open(self.main, os.O_RDONLY); before = len(os.listdir('/proc/self/fd'))
        try:
            with self.assertRaises(ValueError):
                self.send(self.packet(1, 0), ancillary=[(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i',[fd]*20))])
            self.assertEqual(len(os.listdir('/proc/self/fd')), before)
        finally: os.close(fd)

    def test_truncated_payload_refused_and_received_prefix_retained(self):
        raw = self.packet(1, 0) + b'x' * 5000
        with self.assertRaises(ValueError): self.send(raw)
        record = self.target.evidence()['raw_records'][0]
        self.assertTrue(record['receive_flags'] & socket.MSG_TRUNC)
        self.assertNotEqual(record['raw_hex'], raw.hex())

    def test_extra_namespace_not_normalized_away(self):
        with self.assertRaises(ValueError): self.send(self.packet(1, 0, namespace=1))

    def test_activity_is_retained_and_refused_not_skipped(self):
        self.startup(); raw = self.packet(6, 3, 1)
        with self.assertRaisesRegex(ValueError, 'never dropped'): self.send(raw)
        self.assertEqual(self.target.raw_records[-1]['raw_hex'], raw.hex())
        self.assertEqual(len(self.target.projections), 3)

    def test_veto_is_retained_and_refused_not_skipped(self):
        with self.assertRaisesRegex(ValueError, 'never dropped'): self.send(self.packet(5, 0, flags=4))

    def test_alias_J_refusal_retains_fd_and_attempted_projection(self):
        self.send(self.packet(1, 0)); self.send(self.packet(2, 1, 1, self.main, ''), self.main)
        self.send(self.packet(3, 2, 1)); alias = str(self.folder / 'unqualified-alias')
        with self.assertRaisesRegex(ValueError, 'loader-name resolution'):
            self.send(self.packet(2, 3, 2, self.plugin, alias), self.plugin)
        self.assertEqual(len(self.target.fd_state.objects), 2)
        os.fstat(self.target.fd_state.objects[2]['fd'])
        self.assertFalse(self.target.projections[-1]['collector_authentication'])

    def test_generation_reuse_refused(self):
        self.startup()
        with self.assertRaises(ValueError): self.send(self.packet(2, 3, 1, self.plugin), self.plugin)

    def test_EOF_before_preinit_is_not_complete(self):
        self.send(self.packet(1, 0)); self.b.shutdown(socket.SHUT_WR)
        with self.assertRaises(ValueError): self.target.receive_fixture(self.a)

    def test_wait_before_EOF_refused(self):
        self.startup()
        with self.assertRaises(ValueError): self.target.finish_fixture(1234, 0)

    def test_boolean_wait_exit_refused(self):
        self.startup(); self.eof()
        with self.assertRaises(ValueError): self.target.finish_fixture(1234, False)

    def test_wrong_fixture_wait_pid_refused(self):
        self.startup(); self.eof()
        with self.assertRaises(ValueError): self.target.finish_fixture(1235, 0)

    def test_claimed_successful_wait_does_not_qualify_native_runtime(self):
        r = self.complete()
        self.assertFalse(r['runtime_qualified']); self.assertFalse(r['native_or_science_authority'])
        self.assertFalse(r['codec_certificate']); self.assertFalse(r['H_allocation'])
        self.assertEqual(r['positive_ACKs_sent'], 0)

    def test_public_dispatch_release_refuse_after_complete_join(self):
        r = self.complete()
        with self.assertRaises(o.Refusal): o.dispatch(r)
        with self.assertRaises(o.Refusal): o.release(r)

    def test_poisoned_interface_cannot_resume(self):
        with self.assertRaises(ValueError): self.send(self.packet(1, 0, version=1))
        before = len(self.target.raw_records)
        with self.assertRaises(ValueError): self.send(self.packet(1, 0))
        self.assertEqual(len(self.target.raw_records), before)

    def test_completed_interface_cannot_resume_or_reissue_receipt(self):
        self.complete()
        with self.assertRaises(ValueError): self.target.receive_fixture(self.a)
        with self.assertRaises(ValueError): self.target.finish_fixture(1234, 0)

    def test_source_process_booleans_refused_before_transport(self):
        wrong = dict(self.process, namespace_inode=True); self.inputs.append({'process': wrong})
        with self.assertRaises(ValueError): o.SourceInterface(CTX, wrong, str(self.main), self.expected)

    def test_mutated_H_after_transport_refuses_join_and_retains_partial(self):
        context = o.Context(RAWS, MANIFEST); self.target.close_fixture_descriptors()
        self.target = o.SourceInterface(context, self.process, str(self.main), self.expected)
        self.startup(); self.eof(); context.raws[o.H_ROOT + 'PLAN.json'] += b'\n'
        with self.assertRaises(ValueError): self.target.finish_fixture(1234, 0)
        self.assertTrue(self.target.poisoned); self.assertTrue(self.target.projections[-1])

    def test_fixture_ACK_roundtrip_has_no_positive_production_release(self):
        errors = []; accepted = []; sent = self.packet(1, 0)
        def producer():
            try:
                self.b.sendmsg([sent]); barrier = CTX.N.SourceBarrier()
                accepted.append(barrier.wait_fixture(self.b, CTX.N.event_identity(sent), 1))
            except BaseException as exc: errors.append(str(exc))
        thread = threading.Thread(target=producer); thread.start()
        self.target.receive_fixture(self.a)
        identity = self.target.last_fixture_ack_identity; raw = CTX.N.fixture_ack_bytes(identity, 1)
        self.inputs.append({'manufactured_event_hex': sent.hex(), 'test_only_fixture_ACK_hex': raw.hex()})
        with self.assertRaises(o.Refusal): o.release(self.target)
        self.a.sendmsg([raw]); thread.join(2)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
        self.assertFalse(accepted[0]['observer_authentication'])
        self.assertEqual(self.target.evidence()['positive_ACKs_sent'], 0)


if __name__ == '__main__':
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ContextTests),
                               unittest.defaultTestLoader.loadTestsFromTestCase(InterfaceTests)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raw = o.canonical({'schema':'radio-O-retained-manufactured-integration-controls-v1',
                      'prospective_parent': o.PARENT, 'tests': EVIDENCE, 'cases': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors),
                      'source_context_explicit_read_bytes': len(MANIFEST) + sum(map(len, RAWS.values())),
                      'native_callback_observations': 0, 'actual_codec_handoffs': 0,
                      'native_runtime_codec_science_authority': False})
    if len(raw) > 32 * 1024 ** 2: raise ValueError('prospective evidence ceiling')
    with (HERE / 'COHORT-1.json').open('xb') as out: out.write(raw)
    raise SystemExit(0 if result.wasSuccessful() else 1)
