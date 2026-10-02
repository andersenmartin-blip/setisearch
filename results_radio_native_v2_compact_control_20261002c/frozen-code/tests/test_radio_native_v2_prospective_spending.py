"""Tiny inert spending tests: no real marker, control or telescope inputs."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import radio_native_v2_prospective_spending as spending


def synthetic_receipt(scope):
    return {'schema': spending.RECEIPT_SCHEMA, 'namespace': spending.NAMESPACE,
        'activation_commit': '1'*40, 'activation_tree': '2'*40,
        'activation_parent': '3'*40, 'marker_blob': '4'*40,
        'marker_path': spending.MARKER, 'marker_sha256': '5'*64,
        'plan_sha256': '6'*64, 'complete_freeze_sha256': '7'*64,
        'execution_preread_sha256': '8'*64,
        'runtime_custody_manifest_sha256': '9'*64,
        'control_scope': str(scope), 'activation_public_readback_verified': True,
        'activation_only_runtime_complete': True, 'one_control_invocation': True,
        **{key: False for key in spending.DISABLED}}


def process_attempt(receipt, scope, ledger, repository_root, barrier, pipe):
    try:
        barrier.wait(timeout=10)
        spending.consume_once(receipt, execution_scope=scope, ledger_root=ledger,
            repository_root=repository_root, receipt_validator=lambda value: True)
        pipe.send('accepted')
    except Exception as failure:
        pipe.send(type(failure).__name__)
    finally:
        pipe.close()


class InvocationSpendingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = self.root/'scope-not-created'
        self.repository_root = self.root
        self.ledger = Path(spending.ledger_root_for_repository(self.repository_root))
        self.ledger.mkdir(mode=0o700)
        self.receipt = synthetic_receipt(self.scope)

    def consume(self, receipt=None, **changes):
        kwargs = {'execution_scope': str(self.scope), 'ledger_root': str(self.ledger),
            'repository_root': str(self.repository_root), 'receipt_validator': lambda value: True}
        kwargs.update(changes)
        return spending.consume_once(self.receipt if receipt is None else receipt, **kwargs)

    def verify(self, witness, receipt=None, **changes):
        kwargs = {'execution_scope': str(self.scope), 'ledger_root': str(self.ledger),
            'repository_root': str(self.repository_root)}
        kwargs.update(changes)
        return spending.verify_spend_witness(witness,
            self.receipt if receipt is None else receipt, **kwargs)

    def record_path(self):
        _, _, name = spending._receipt(self.receipt, str(self.scope))
        return self.ledger/name

    def test_consume_durable_readback_and_worker_rechecks_without_scope(self):
        witness = self.consume()
        self.assertFalse(self.scope.exists())
        raw = self.record_path().read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), witness['record_sha256'])
        self.assertTrue(witness['durable_before_workload'])
        before = self.record_path().stat()
        self.assertTrue(self.verify(witness)); self.assertTrue(self.verify(witness))
        self.assertEqual(before, self.record_path().stat())
        with self.assertRaisesRegex(ValueError, 'already spent'):
            self.consume()

    def test_changed_scope_replay_remains_denied(self):
        self.consume()
        another = self.root/'another-absent-scope'
        receipt = synthetic_receipt(another)
        with self.assertRaisesRegex(ValueError, 'already spent'):
            self.consume(receipt, execution_scope=str(another))
        self.assertFalse(another.exists())

    def test_changed_commit_replay_remains_denied(self):
        self.consume()
        receipt = copy.deepcopy(self.receipt); receipt['activation_commit'] = 'a'*40
        with self.assertRaisesRegex(ValueError, 'already spent'):
            self.consume(receipt)

    def test_sixteen_concurrent_thread_attempts_accept_exactly_one(self):
        def attempt(_):
            try: self.consume(); return 'accepted'
            except ValueError: return 'denied'
        with ThreadPoolExecutor(max_workers=16) as executor:
            outcomes = list(executor.map(attempt, range(16)))
        self.assertEqual(outcomes.count('accepted'), 1)
        self.assertEqual(outcomes.count('denied'), 15)
        self.assertEqual(len(list(self.ledger.iterdir())), 1)

    def test_four_concurrent_process_attempts_accept_exactly_one(self):
        context = multiprocessing.get_context('fork')
        barrier = context.Barrier(4); processes = []; receivers = []
        for _ in range(4):
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=process_attempt,
                args=(self.receipt, str(self.scope), str(self.ledger),
                    str(self.repository_root), barrier, sender))
            process.start(); sender.close()
            processes.append(process); receivers.append(receiver)
        try:
            outcomes = []
            for receiver in receivers:
                self.assertTrue(receiver.poll(15), 'bounded tiny process result required')
                outcomes.append(receiver.recv())
            for process in processes:
                process.join(timeout=15)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(outcomes.count('accepted'), 1)
            self.assertEqual(outcomes.count('ValueError'), 3)
        finally:
            for receiver in receivers: receiver.close()
            for process in processes:
                if process.is_alive(): process.terminate(); process.join(timeout=5)

    def test_admission_failure_precedes_all_ledger_mutations(self):
        calls = []
        def validator(receipt): calls.append(receipt); return False
        with self.assertRaisesRegex(ValueError, 'Independent activation'):
            self.consume(receipt_validator=validator)
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(self.ledger.iterdir()), [])
        for invalid in (None, 1, lambda value: 1):
            with self.assertRaises(ValueError): self.consume(receipt_validator=invalid)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_receipt_validator_exception_leaves_no_claim(self):
        def validator(receipt): raise RuntimeError('synthetic admission refusal')
        with self.assertRaises(RuntimeError): self.consume(receipt_validator=validator)
        self.assertFalse(self.record_path().exists())

    def test_receipt_mutation_during_admission_denied_without_claim(self):
        def validator(receipt):
            receipt['plan_sha256'] = 'a'*64
            return True
        with self.assertRaisesRegex(ValueError, 'changed during independent admission'):
            self.consume(receipt_validator=validator)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_claim_mutation_after_readback_denied_without_witness(self):
        read = spending._read_record
        def altered(directory, name):
            result = read(directory, name)
            self.record_path().write_bytes(b'after-readback mutation')
            return result
        with mock.patch.object(spending, '_read_record', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'changed after readback'): self.consume()
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_both_historical_namespaces_markers_and_commits_permanently_denied(self):
        for namespace, marker, commit in spending.SPENT_ACTIVATIONS:
            for key, value in (('namespace', namespace), ('marker_path', marker),
                    ('activation_commit', commit)):
                receipt = copy.deepcopy(self.receipt); receipt[key] = value
                with self.subTest(key=key, value=value):
                    with mock.patch.object(spending, '_directory') as directory:
                        with self.assertRaisesRegex(ValueError, 'permanently spent'):
                            self.consume(receipt)
                        directory.assert_not_called()

    def test_exact_historical_identities_are_pinned(self):
        self.assertEqual(spending.SPENT_ACTIVATIONS, (
            ('radio-native-v2-control-activation-transition-20261002a',
                'config/radio_native_v2_control_activation_20261002a.activate.json',
                'ba1b6c918931a02a84cd23e0e14057bd9f700e40'),
            ('radio-native-v2-control-activation-transition-20261002b',
                'config/radio_native_v2_control_activation_20261002b.activate.json',
                '1bc31d49b2552de10c3fbabb7bc106618a44a241')))

    def test_historical_receipts_refuse_worker_and_storage_apis_before_directory_io(self):
        witness = self.consume()
        for namespace, marker, commit in spending.SPENT_ACTIVATIONS:
            for key, value in (('namespace', namespace), ('marker_path', marker),
                    ('activation_commit', commit)):
                receipt = copy.deepcopy(self.receipt); receipt[key] = value
                for operation in (self.verify, self.observe):
                    with self.subTest(key=key, value=value, operation=operation.__name__):
                        with mock.patch.object(spending, '_directory') as directory:
                            with self.assertRaisesRegex(ValueError, 'permanently spent'):
                                operation(witness, receipt)
                            directory.assert_not_called()

    def test_missing_extra_wrong_type_and_authority_receipts_denied(self):
        changes = [('schema', 'wrong'), ('namespace', 'wrong'),
            ('marker_path', 'config/another.activate.json'), ('control_scope', '/another'),
            ('activation_commit', '1'*39), ('plan_sha256', 'G'*64),
            ('activation_only_runtime_complete', False), ('one_control_invocation', 1)]
        changes.extend((key, True) for key in spending.DISABLED)
        for key, value in changes:
            with self.subTest(key=key):
                receipt = copy.deepcopy(self.receipt); receipt[key] = value
                with self.assertRaises(ValueError): self.consume(receipt)
        receipt = copy.deepcopy(self.receipt); receipt.pop('marker_blob')
        with self.assertRaises(ValueError): self.consume(receipt)
        receipt = copy.deepcopy(self.receipt); receipt['extra'] = False
        with self.assertRaises(ValueError): self.consume(receipt)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_existing_empty_partial_malformed_records_permanently_refuse(self):
        for raw in (b'', b'{', b'not JSON', b'{}\n'):
            # Each fixture is a distinct, inert temporary ledger. The component
            # itself never deletes or rearms a failed record.
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                repository = Path(directory)
                ledger = Path(spending.ledger_root_for_repository(repository))
                ledger.mkdir(mode=0o700)
                path = ledger/self.record_path().name; path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'already spent'):
                    self.consume(ledger_root=str(ledger), repository_root=str(repository))
                self.assertEqual(path.read_bytes(), raw)

    def test_existing_symlink_hardlink_directory_and_fifo_refuse_without_io(self):
        for kind in ('symlink', 'hardlink', 'directory', 'fifo'):
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                repository = Path(directory)
                ledger = Path(spending.ledger_root_for_repository(repository))
                ledger.mkdir(mode=0o700); path = ledger/self.record_path().name
                original = self.root/('original-'+kind); original.write_bytes(b'inert')
                if kind == 'symlink': path.symlink_to(original)
                elif kind == 'hardlink': os.link(original, path)
                elif kind == 'directory': path.mkdir()
                else: os.mkfifo(path)
                with self.assertRaisesRegex(ValueError, 'already spent'):
                    self.consume(ledger_root=str(ledger), repository_root=str(repository))
                self.assertEqual(original.read_bytes(), b'inert')

    def test_failed_first_fsync_retains_empty_claim_and_never_returns_witness(self):
        with mock.patch.object(spending.os, 'fsync', side_effect=OSError('synthetic fsync failure')):
            with self.assertRaises(OSError): self.consume()
        self.assertTrue(self.record_path().exists())
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_failed_final_directory_fsync_retains_complete_claim(self):
        actual = os.fsync; count = 0
        def fsync(fd):
            nonlocal count
            count += 1
            if count == 4: raise OSError('synthetic final directory fsync failure')
            return actual(fd)
        with mock.patch.object(spending.os, 'fsync', side_effect=fsync):
            with self.assertRaises(OSError): self.consume()
        self.assertEqual(count, 4)
        self.assertEqual(json.loads(self.record_path().read_bytes())['state'], 'SPENT_BEFORE_WORKLOAD')
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_partial_write_failure_retains_claim(self):
        actual = os.write; count = 0
        def write(fd, raw):
            nonlocal count
            count += 1
            if count == 1: return actual(fd, raw[:7])
            raise OSError('synthetic partial write failure')
        with mock.patch.object(spending.os, 'write', side_effect=write):
            with self.assertRaises(OSError): self.consume()
        self.assertEqual(self.record_path().read_bytes(), b'{"activ')
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_zero_length_write_refuses_and_retains_claim(self):
        with mock.patch.object(spending.os, 'write', return_value=0):
            with self.assertRaisesRegex(ValueError, 'Incomplete'): self.consume()
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_file_and_directory_fsync_complete_before_readback_or_witness(self):
        events = []; actual_sync = os.fsync; actual_read = spending._read_record
        def fsync(fd): events.append('fsync'); return actual_sync(fd)
        def read(*args): events.append('readback'); return actual_read(*args)
        with (mock.patch.object(spending.os, 'fsync', side_effect=fsync),
                mock.patch.object(spending, '_read_record', side_effect=read)):
            witness = self.consume(); events.append('witness')
        self.assertEqual(events, ['fsync', 'fsync', 'fsync', 'fsync', 'readback', 'witness'])
        self.assertTrue(witness['durable_before_workload'])

    def test_record_corruption_partial_json_and_duplicate_keys_deny_worker(self):
        witness = self.consume()
        for raw in (b'{', b'{}\n', b'{"schema":"a","schema":"b"}\n', b'NaN\n'):
            self.record_path().write_bytes(raw)
            with self.assertRaises((ValueError, OSError)): self.verify(witness)
        with self.assertRaisesRegex(ValueError, 'already spent'): self.consume()

    def test_record_hardlink_mode_change_symlink_and_missing_deny_worker(self):
        witness = self.consume(); original = self.record_path().read_bytes()
        self.record_path().chmod(0o644)
        with self.assertRaises(ValueError): self.verify(witness)
        self.record_path().chmod(0o600)
        os.link(self.record_path(), self.root/'record-alias')
        with self.assertRaises(ValueError): self.verify(witness)
        self.record_path().unlink()
        with self.assertRaises(OSError): self.verify(witness)
        source = self.root/'replacement'; source.write_bytes(original); source.chmod(0o600)
        self.record_path().symlink_to(source)
        with self.assertRaises(OSError): self.verify(witness)

    def test_same_bytes_record_replacement_is_detected_by_held_identity(self):
        witness = self.consume(); raw = self.record_path().read_bytes()
        replacement = self.ledger/'replacement'; replacement.write_bytes(raw); replacement.chmod(0o600)
        replacement.replace(self.record_path())
        with self.assertRaisesRegex(ValueError, 'record differs'): self.verify(witness)

    def test_witness_receipt_scope_ledger_and_identity_tampering_deny_worker(self):
        witness = self.consume()
        for key, value in (('record_name', '../other'), ('record_sha256', 'a'*64),
                ('activation_receipt_sha256', 'a'*64), ('durable_before_workload', 1),
                ('control_scope', '/another'), ('ledger_root', '/another'),
                ('activation_commit', 'a'*40), ('schema', 'wrong')):
            changed = copy.deepcopy(witness); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.verify(changed)
        for key in ('record_identity', 'ledger_identity'):
            changed = copy.deepcopy(witness); changed[key]['inode'] += 1
            with self.assertRaises(ValueError): self.verify(changed)
            changed[key]['inode'] = True
            with self.assertRaises(ValueError): self.verify(changed)
        receipt = copy.deepcopy(self.receipt); receipt['plan_sha256'] = 'a'*64
        with self.assertRaises(ValueError): self.verify(witness, receipt)

    def test_ledger_is_not_created_and_insecure_or_symlink_ledgers_deny(self):
        absent_repository = self.root/'absent-repository'
        absent = Path(spending.ledger_root_for_repository(absent_repository))
        with self.assertRaises(OSError):
            self.consume(ledger_root=str(absent), repository_root=str(absent_repository))
        self.assertFalse(absent.exists())
        self.ledger.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private 0700'): self.consume()
        self.ledger.chmod(0o700)
        target = self.root/'ledger-target'; self.ledger.rename(target)
        self.ledger.symlink_to(target, target_is_directory=True)
        with self.assertRaises(OSError): self.consume()

    def test_ledger_directory_replacement_denies_worker(self):
        witness = self.consume()
        self.ledger.rename(self.root/'old-ledger'); self.ledger.mkdir(mode=0o700)
        (self.ledger/self.record_path().name).write_bytes(
            (self.root/'old-ledger'/self.record_path().name).read_bytes())
        with self.assertRaisesRegex(ValueError, 'directory identity'): self.verify(witness)

    def test_canonical_paths_and_scope_overlap_denied_before_io(self):
        paths = ('relative', '/a/../b', '/a/./b', '/a//b', '/', '/a\\b', '/a\n', '/a/')
        for path in paths:
            with self.assertRaises(ValueError): self.consume(ledger_root=path)
        for path in (str(self.scope), str(self.scope/'ledger')):
            with self.assertRaises(ValueError): self.consume(ledger_root=path)
        with self.assertRaises(ValueError): self.consume(execution_scope=str(self.ledger/'scope'))
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_original_repository_policy_is_pure_and_has_no_rearm_api(self):
        root = str(self.root/'repository-not-created')
        self.assertEqual(spending.ledger_root_for_repository(root),
            root+'/.radio-native-v2-invocation-ledger-20261002c')
        self.assertFalse(Path(root).exists())
        for name in ('rearm', 'delete', 'reset', 'remove_record', 'retry'):
            self.assertFalse(hasattr(spending, name))

    def test_all_public_spend_apis_require_explicit_repository_root(self):
        witness = self.consume()
        kwargs = {'execution_scope': str(self.scope), 'ledger_root': str(self.ledger)}
        with self.assertRaisesRegex(TypeError, 'repository_root'):
            spending.consume_once(self.receipt, receipt_validator=lambda value: True, **kwargs)
        for operation in (spending.verify_spend_witness, spending.observe_spend_storage):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(TypeError, 'repository_root'):
                    operation(witness, self.receipt, **kwargs)

    def test_original_root_binding_refuses_wrong_root_and_alias_before_directory_io(self):
        cases = (
            {'ledger_root': str(self.root/'private-ledger')},
            {'repository_root': str(self.root/'other-original')},
            {'repository_root': str(self.root)+'/.'},
            {'repository_root': str(self.root)+'/../other'},
            {'ledger_root': str(self.root/'alias'/spending.LEDGER_DIRECTORY)})
        for changes in cases:
            with self.subTest(changes=changes):
                admission = mock.Mock(return_value=True)
                with mock.patch.object(spending, '_directory') as directory:
                    with self.assertRaises(ValueError):
                        self.consume(receipt_validator=admission, **changes)
                    directory.assert_not_called(); admission.assert_not_called()
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_worker_and_storage_refuse_wrong_explicit_original_root_before_io(self):
        witness = self.consume()
        for operation in (self.verify, self.observe):
            with self.subTest(operation=operation.__name__):
                with mock.patch.object(spending, '_directory') as directory:
                    with self.assertRaisesRegex(ValueError, 'pinned original repository ledger'):
                        operation(witness, repository_root=str(self.root/'wrong-original'))
                    directory.assert_not_called()

    def test_all_apis_refuse_historical_ledger_root_without_reading_or_modifying_it(self):
        witness = self.consume()
        historical = self.root/'.radio-native-v2-invocation-ledger'
        historical.mkdir(mode=0o700)
        retained = historical/'historical-spent.json'; retained.write_bytes(b'inert retained history')
        for operation in (self.consume, lambda **kw: self.verify(witness, **kw),
                lambda **kw: self.observe(witness, **kw)):
            with mock.patch.object(spending, '_directory') as directory:
                with self.assertRaisesRegex(ValueError, 'pinned original repository ledger'):
                    operation(ledger_root=str(historical))
                directory.assert_not_called()
        self.assertEqual(retained.read_bytes(), b'inert retained history')
        self.assertEqual(list(historical.iterdir()), [retained])

    def test_root_is_not_inferred_from_scope_or_witness(self):
        witness = self.consume()
        scope_root = self.root/'workload'/'frozen-code'
        scope_ledger = Path(spending.ledger_root_for_repository(scope_root))
        for operation in (lambda **kw: self.verify(witness, **kw),
                lambda **kw: self.observe(witness, **kw)):
            with mock.patch.object(spending, '_directory') as directory:
                with self.assertRaisesRegex(ValueError, 'pinned original repository ledger'):
                    operation(ledger_root=str(scope_ledger))
                directory.assert_not_called()
        receipt = synthetic_receipt(self.scope)
        with mock.patch.object(spending, '_directory') as directory:
            with self.assertRaisesRegex(ValueError, 'outside the per-invocation scope'):
                self.consume(receipt, repository_root=str(self.scope),
                    ledger_root=spending.ledger_root_for_repository(self.scope))
            directory.assert_not_called()
        self.assertFalse(scope_root.exists()); self.assertFalse(self.scope.exists())

    def test_preclaim_unexpected_entries_refuse_before_exclusive_creation(self):
        actual_open = os.open
        for kind in ('file', 'hidden', 'directory', 'symlink', 'fifo'):
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                repository = Path(directory)
                ledger = Path(spending.ledger_root_for_repository(repository))
                ledger.mkdir(mode=0o700)
                extra = ledger/('.hidden' if kind == 'hidden' else 'extra')
                if kind in ('file', 'hidden'): extra.write_bytes(b'inert unexpected entry')
                elif kind == 'directory': extra.mkdir()
                elif kind == 'symlink': extra.symlink_to('/absent-synthetic-target')
                else: os.mkfifo(extra)
                with (self.subTest(kind=kind),
                        mock.patch.object(spending.os, 'open', wraps=actual_open) as opened,
                        mock.patch.object(spending, '_read_record') as read):
                    with self.assertRaisesRegex(ValueError, 'Empty invocation ledger'):
                        self.consume(ledger_root=str(ledger), repository_root=str(repository))
                    self.assertFalse(any(call.args[1] & os.O_EXCL for call in opened.call_args_list))
                    read.assert_not_called()
                self.assertEqual([item.name for item in ledger.iterdir()], [extra.name])

    def test_preexisting_claim_keeps_spent_reason_even_with_extra_entries(self):
        self.record_path().write_bytes(b'{')
        (self.ledger/'.extra').write_bytes(b'inert')
        with mock.patch.object(spending, '_read_record') as read:
            with self.assertRaisesRegex(ValueError, 'already spent'):
                self.consume()
            read.assert_not_called()
        self.assertEqual(self.record_path().read_bytes(), b'{')

    def test_extra_entry_after_durable_readback_denies_witness_and_keeps_claim_spent(self):
        actual_read = spending._read_record
        def read(directory, name):
            result = actual_read(directory, name)
            (self.ledger/'.late-extra').write_bytes(b'inert concurrent extra')
            return result
        with mock.patch.object(spending, '_read_record', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'Exact one-record'):
                self.consume()
        self.assertEqual(json.loads(self.record_path().read_bytes())['state'], 'SPENT_BEFORE_WORKLOAD')
        with self.assertRaisesRegex(ValueError, 'already spent'):
            self.consume()

    def test_worker_verification_requires_exact_inventory(self):
        witness = self.consume()
        (self.ledger/'.extra').write_bytes(b'inert')
        with self.assertRaisesRegex(ValueError, 'Exact one-record'):
            self.verify(witness)

    def observe(self, witness, receipt=None, **changes):
        kwargs = {'execution_scope': str(self.scope), 'ledger_root': str(self.ledger),
            'repository_root': str(self.repository_root)}
        kwargs.update(changes)
        return spending.observe_spend_storage(witness,
            self.receipt if receipt is None else receipt, **kwargs)

    def test_storage_observation_counts_current_file_and_directory_bytes_blocks(self):
        witness = self.consume(); witness_before = copy.deepcopy(witness)
        raw_before = self.record_path().read_bytes()
        observed = self.observe(witness)
        self.assertEqual(observed['schema'], spending.STORAGE_SCHEMA)
        self.assertEqual(observed['ledger_root'], str(self.ledger))
        self.assertEqual(observed['control_scope'], str(self.scope))
        self.assertEqual(observed['invocation_spending_sha256'], spending._digest(witness))
        self.assertEqual(observed['activation_receipt_sha256'], spending._digest(self.receipt))
        self.assertEqual(observed['entry_count'], 2)
        self.assertTrue(observed['witness_bindings_verified'])
        self.assertTrue(observed['ledger_inventory_exact'])
        self.assertTrue(observed['current_observation_stable'])
        for row, path, kind in zip(observed['rows'], (self.ledger, self.record_path()),
                ('directory', 'file')):
            info = path.stat()
            self.assertEqual(row['path'], str(path)); self.assertEqual(row['kind'], kind)
            self.assertEqual(row['bytes'], info.st_size)
            self.assertEqual(row['allocated_bytes'], info.st_blocks*512)
            self.assertEqual(row['device'], info.st_dev); self.assertEqual(row['inode'], info.st_ino)
            self.assertEqual(row['mode'], stat.S_IMODE(info.st_mode))
            self.assertEqual(row['mtime_ns'], info.st_mtime_ns)
            self.assertEqual(row['ctime_ns'], info.st_ctime_ns)
        self.assertEqual(observed['logical_bytes'],
            self.ledger.stat().st_size + self.record_path().stat().st_size)
        self.assertEqual(observed['allocated_bytes'],
            (self.ledger.stat().st_blocks+self.record_path().stat().st_blocks)*512)
        self.assertEqual(observed, self.observe(witness))
        self.assertEqual(witness, witness_before)
        self.assertEqual(self.record_path().read_bytes(), raw_before)
        self.assertFalse(self.scope.exists())

    def test_storage_observation_reauthenticates_receipt_witness_scope_and_ledger(self):
        witness = self.consume()
        changed = copy.deepcopy(witness); changed['record_sha256'] = 'a'*64
        with self.assertRaises(ValueError): self.observe(changed)
        changed_receipt = copy.deepcopy(self.receipt); changed_receipt['plan_sha256'] = 'a'*64
        with self.assertRaises(ValueError): self.observe(witness, changed_receipt)
        with self.assertRaises(ValueError): self.observe(witness, execution_scope='/another-scope')
        other = self.root/'other-ledger'; other.mkdir(mode=0o700)
        with self.assertRaises(ValueError): self.observe(witness, ledger_root=str(other))
        self.assertEqual(list(other.iterdir()), [])

    def test_storage_observation_rejects_all_extra_including_hidden_and_special_entries(self):
        witness = self.consume()
        for kind in ('file', 'hidden', 'directory', 'symlink', 'fifo'):
            with self.subTest(kind=kind):
                name = '.hidden' if kind == 'hidden' else 'extra'
                path = self.ledger/name
                if kind in ('file', 'hidden'): path.write_bytes(b'never ignored')
                elif kind == 'directory': path.mkdir()
                elif kind == 'symlink': path.symlink_to('/absent-synthetic-target')
                else: os.mkfifo(path)
                try:
                    with self.assertRaises(ValueError): self.observe(witness)
                finally:
                    if kind == 'directory': path.rmdir()
                    else: path.unlink()

    def test_storage_observation_rejects_record_alias_corruption_and_missing_entry(self):
        witness = self.consume()
        alias = self.root/'spend-alias'; os.link(self.record_path(), alias)
        with self.assertRaises(ValueError): self.observe(witness)
        alias.unlink()
        self.record_path().write_bytes(b'changed storage bytes')
        with self.assertRaises(ValueError): self.observe(witness)
        self.record_path().unlink()
        with self.assertRaises(OSError): self.observe(witness)

    def test_storage_observation_detects_directory_inventory_mutation_during_scan(self):
        witness = self.consume(); actual = spending._ledger_names; calls = 0
        def names(directory, name):
            nonlocal calls
            calls += 1
            result = actual(directory, name)
            if calls == 1: (self.ledger/'.late-extra').write_bytes(b'late')
            return result
        with mock.patch.object(spending, '_ledger_names', side_effect=names):
            with self.assertRaisesRegex(ValueError, 'one-record'): self.observe(witness)

    def test_storage_observation_detects_directory_size_or_block_drift(self):
        witness = self.consume(); actual = spending._storage_identity; calls = 0
        def identity(info):
            nonlocal calls
            value = actual(info)
            if stat.S_ISDIR(info.st_mode):
                calls += 1
                if calls == 2: value['allocated_bytes'] += 512
            return value
        with mock.patch.object(spending, '_storage_identity', side_effect=identity):
            with self.assertRaisesRegex(ValueError, 'directory storage changed'): self.observe(witness)

    def test_storage_observation_detects_file_block_drift_under_unchanged_witness(self):
        witness = self.consume(); actual = spending._storage_identity; calls = 0
        def identity(info):
            nonlocal calls
            value = actual(info)
            if stat.S_ISREG(info.st_mode):
                calls += 1
                if calls == 3: value['allocated_bytes'] += 512
            return value
        with mock.patch.object(spending, '_storage_identity', side_effect=identity):
            with self.assertRaisesRegex(ValueError, 'record storage changed'): self.observe(witness)

    def test_storage_observation_bounds_directory_size_before_enumeration(self):
        witness = self.consume(); actual = spending._storage_identity
        def identity(info):
            value = actual(info)
            if stat.S_ISDIR(info.st_mode):
                value['bytes'] = spending.MAX_LEDGER_DIRECTORY_BYTES+1
            return value
        # Witness verification performs its own exact-inventory scan first. The
        # later storage observation must refuse its size bound before another.
        with (mock.patch.object(spending, '_storage_identity', side_effect=identity),
                mock.patch.object(spending, '_ledger_names', wraps=spending._ledger_names) as scan):
            with self.assertRaisesRegex(ValueError, 'Bounded leaf'): self.observe(witness)
            self.assertEqual(scan.call_count, 1)

    def test_storage_observation_denies_ledger_root_replacement_after_authenticated_read(self):
        witness = self.consume(); actual = spending.verify_spend_witness
        def verify(*args, **kwargs):
            result = actual(*args, **kwargs)
            self.ledger.rename(self.root/'old-observed-ledger')
            self.ledger.mkdir(mode=0o700)
            (self.ledger/self.record_path().name).write_bytes(
                (self.root/'old-observed-ledger'/self.record_path().name).read_bytes())
            return result
        with mock.patch.object(spending, 'verify_spend_witness', side_effect=verify):
            with self.assertRaisesRegex(ValueError, 'directory identity'): self.observe(witness)


if __name__ == '__main__':
    unittest.main()
