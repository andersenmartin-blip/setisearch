"""Real tiny publication/collision/crash checks, no protected control."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import radio_native_v2_preparation_suite_store as store


class AttemptStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.results = self.root / 'results'; self.results.mkdir()
        self.repo = self.root / 'repo'; (self.repo / 'src').mkdir(parents=True)
        self.source = self.repo / 'src' / 'tiny.py'; self.source.write_bytes(b'x = 1\n')
        raw = self.source.read_bytes()
        pins = {'src/tiny.py':{'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}}
        self.value = {'schema':store.SCHEMA, 'attempt':1, 'status':'PASSED',
            'test_count':1, 'failures':0, 'errors':0, 'skipped':0,
            'source_snapshot_unchanged':True, 'source_and_test_pins':pins,
            'initial_source_and_test_pins':copy.deepcopy(pins)}

    def raw(self, attempt=1, **changes):
        value = copy.deepcopy(self.value); value.update(attempt=attempt, **changes)
        return store.canonical(value) + b'\n'

    def publish(self, attempt=1, **changes):
        raw = self.raw(attempt, **changes)
        receipt = store.record_attempt(self.results, attempt, raw)
        return raw, receipt

    def select(self, attempt=1, raw=None):
        raw = raw if raw is not None else self.raw(attempt)
        return store.read_selected_summary(self.results, attempt,
            hashlib.sha256(raw).hexdigest(), self.repo)

    def test_two_passing_attempts_preserve_existing_shared_alias_and_select_exact_second(self):
        alias = self.results / 'final-suite-summary.json'; alias.write_bytes(b'old retained alias\n')
        first, _ = self.publish(1); second, receipt = self.publish(2)
        value, pin = self.select(2, second)
        self.assertEqual(value['attempt'], 2)
        self.assertEqual(pin['sha256'], hashlib.sha256(second).hexdigest())
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), first)
        self.assertEqual(alias.read_bytes(), b'old retained alias\n')
        self.assertFalse(receipt['shared_alias_created_or_changed'])
        self.assertFalse(receipt['execution_authorized'])
        self.assertFalse(any(p.name.endswith('.pending') for p in self.results.iterdir()))

    def test_failed_attempt_is_retained_but_not_selected(self):
        first, _ = self.publish()
        failed, _ = self.publish(2, status='FAILED', errors=1)
        with self.assertRaisesRegex(ValueError, 'Failed attempt'):
            self.select(2, failed)
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), first)
        self.assertEqual((self.results / store.attempt_name(2)).read_bytes(), failed)

    def test_same_attempt_collision_refuses_before_any_write(self):
        raw, _ = self.publish()
        with mock.patch.object(store.os, 'write', side_effect=AssertionError('No overwrite')):
            with self.assertRaises(FileExistsError):
                store.record_attempt(self.results, 1, self.raw(test_count=2))
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), raw)
        self.assertEqual(len(list(self.results.iterdir())), 1)

    def test_counter_type_aliases_and_false_pass_refused_before_output(self):
        for changes in ({'errors':False}, {'failures':0.0}, {'test_count':True},
                {'skipped':1}, {'errors':1}, {'test_count':0}, {'source_snapshot_unchanged':False}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                store.record_attempt(self.results, 1, self.raw(**changes))
        self.assertEqual(list(self.results.iterdir()), [])

    def test_duplicate_noncanonical_and_nonfinite_json_refused(self):
        cases = [self.raw()[:-1], b'{"attempt":1,"attempt":1}\n',
            self.raw().replace(b'"test_count":1', b'"test_count":NaN'),
            self.raw().replace(b'"test_count":1', b'"test_count":1e999')]
        for raw in cases:
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                store.record_attempt(self.results, 1, raw)
        self.assertEqual(list(self.results.iterdir()), [])

    def test_explicit_digest_and_source_drift_are_independent_selection_gates(self):
        raw, _ = self.publish()
        with self.assertRaisesRegex(ValueError, 'independent raw digest'):
            store.read_selected_summary(self.results, 1, '0'*64, self.repo)
        self.source.write_bytes(b'x = 2\n')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.select(raw=raw)
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), raw)

    def test_summary_symlink_and_hardlink_aliases_refused(self):
        raw, _ = self.publish()
        target = self.results / store.attempt_name(1)
        alias = self.results / 'alias'; os.link(target, alias)
        with self.assertRaisesRegex(ValueError, 'sole-link'):
            self.select(raw=raw)
        alias.unlink(); target.rename(alias); target.symlink_to(alias)
        with self.assertRaises(OSError):
            self.select(raw=raw)

    def test_source_parent_symlink_and_file_hardlink_refused(self):
        raw, _ = self.publish()
        alias = self.repo / 'alias.py'; os.link(self.source, alias)
        with self.assertRaisesRegex(ValueError, 'sole-link'):
            self.select(raw=raw)
        alias.unlink(); directory = self.repo / 'src'; directory.rename(self.repo / 'physical')
        directory.symlink_to(self.repo / 'physical', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Directory aliases'):
            self.select(raw=raw)

    def test_unsafe_source_paths_and_invalid_pin_types_refused_before_output(self):
        for path in ('../outside.py', '/outside.py', 'src//tiny.py', 'src/./tiny.py', 'src/evil\x00.py'):
            value = copy.deepcopy(self.value)
            value['source_and_test_pins'] = {path:next(iter(value['source_and_test_pins'].values()))}
            value['initial_source_and_test_pins'] = copy.deepcopy(value['source_and_test_pins'])
            with self.subTest(path=path), self.assertRaises(ValueError):
                store.record_attempt(self.results, 1, store.canonical(value)+b'\n')
        value = copy.deepcopy(self.value)
        value['source_and_test_pins']['src/tiny.py']['bytes'] = 6.0
        with self.assertRaises(ValueError):
            store.record_attempt(self.results, 1, store.canonical(value)+b'\n')
        self.assertEqual(list(self.results.iterdir()), [])

    def test_file_fsync_failure_retains_pending_without_final_name(self):
        with mock.patch.object(store.os, 'fsync', side_effect=OSError('Injected fsync failure')):
            with self.assertRaises(OSError):
                store.record_attempt(self.results, 1, self.raw())
        self.assertFalse((self.results / store.attempt_name(1)).exists())
        pending = self.results / ('.'+store.attempt_name(1)+'.pending')
        self.assertEqual(pending.read_bytes(), self.raw())
        with self.assertRaises(FileExistsError):
            store.record_attempt(self.results, 1, self.raw())

    def test_concurrent_destination_creation_never_overwrites_winner(self):
        original = store.os.link
        def race(*args, **kwargs):
            (self.results / store.attempt_name(1)).write_bytes(b'concurrent winner\n')
            return original(*args, **kwargs)
        with mock.patch.object(store.os, 'link', side_effect=race), self.assertRaises(FileExistsError):
            store.record_attempt(self.results, 1, self.raw())
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), b'concurrent winner\n')
        self.assertTrue((self.results / ('.'+store.attempt_name(1)+'.pending')).exists())

    def test_directory_fsync_failure_cannot_leave_selectable_publication(self):
        original = store.os.fsync; calls = 0
        def fail_second(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('Injected directory fsync failure')
            return original(fd)
        with mock.patch.object(store.os, 'fsync', side_effect=fail_second), self.assertRaises(OSError):
            store.record_attempt(self.results, 1, self.raw())
        self.assertEqual((self.results / store.attempt_name(1)).stat().st_nlink, 2)
        with self.assertRaisesRegex(ValueError, 'sole-link'):
            self.select()

    def test_pending_unlink_failure_cannot_leave_selectable_publication(self):
        with mock.patch.object(store.os, 'unlink', side_effect=OSError('Injected cleanup failure')):
            with self.assertRaises(OSError):
                store.record_attempt(self.results, 1, self.raw())
        with self.assertRaisesRegex(ValueError, 'sole-link'):
            self.select()

    def test_short_writes_preserve_exact_complete_bytes_and_fsync(self):
        original = store.os.write
        with mock.patch.object(store.os, 'write', side_effect=lambda fd, raw:original(fd, raw[:7])), \
                mock.patch.object(store.os, 'fsync', wraps=store.os.fsync) as sync:
            raw, _ = self.publish()
        self.assertEqual(sync.call_count, 3)
        self.assertEqual((self.results / store.attempt_name(1)).read_bytes(), raw)
        self.select(raw=raw)

    def test_read_path_replacement_is_not_accepted_as_original_evidence(self):
        raw, _ = self.publish(); target = self.results / store.attempt_name(1)
        original = store.os.read; replaced = False
        def replace(fd, count):
            nonlocal replaced
            result = original(fd, count)
            if not replaced:
                replaced = True; target.rename(self.results / 'retained-original')
                target.write_bytes(raw)
            return result
        with mock.patch.object(store.os, 'read', side_effect=replace), self.assertRaisesRegex(ValueError, 'changed'):
            self.select(raw=raw)

    def test_directory_replacement_during_staging_cannot_report_success(self):
        original = store.os.fsync; replaced = False
        def replace(fd):
            nonlocal replaced
            result = original(fd)
            if not replaced:
                replaced = True; self.results.rename(self.root / 'retained-directory'); self.results.mkdir()
            return result
        with mock.patch.object(store.os, 'fsync', side_effect=replace), self.assertRaisesRegex(ValueError, 'directory changed'):
            store.record_attempt(self.results, 1, self.raw())
        self.assertEqual(list(self.results.iterdir()), [])
        self.assertTrue(any(p.name.endswith('.pending') for p in (self.root / 'retained-directory').iterdir()))

    def test_oversize_summary_and_invalid_attempts_have_no_output(self):
        with self.assertRaises(ValueError):
            store.record_attempt(self.results, 1, b'x'*(store.MAX_BYTES+1))
        for attempt in (0, -1, True, 1.0, store.MAX_ATTEMPT+1):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                store.record_attempt(self.results, attempt, self.raw())
        self.assertEqual(list(self.results.iterdir()), [])

    def test_results_directory_alias_is_refused_without_external_writes(self):
        alias = self.root / 'alias'; alias.symlink_to(self.results, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Directory aliases'):
            store.record_attempt(alias, 1, self.raw())
        self.assertEqual(list(self.results.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
