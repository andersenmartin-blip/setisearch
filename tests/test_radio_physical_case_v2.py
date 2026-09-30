"""Local v2 parent qualification: exact bytes, bounded closure and no restart."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import physical_case_v2_radio as p
from seti_repeater import physical_case_radio as p1
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater import physical_evidence_radio as e1
from seti_repeater import whole_cadence_event_store_radio as s
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_journal import manifest


class PhysicalCaseV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tick = 0.
        self.base = {'base.bin': b'original deterministic base bytes'}
        self.cap = 1024**2
        self.configure()

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self):
        self.m = manifest(1, (*self.base, p.SEAL, p.OUTCOME))
        self.m['caps']['evidence_bytes'] = max(4*1024**2, self.cap+1024**2)
        self.m['caps']['ledger_reserve_bytes'] = 1024**2
        self.config = e.configuration('physical-case-v2-tests',
            self.m['cases'][0]['case_identity'], self.m['cases'][0]['plan_sha256'],
            self.base, budget_bytes=self.cap-sum(p.CLOSURE_RESERVES.values()))
        self.m['artifact_groups'] = p.policy(self.config)

    def claim(self, *, store_type=s.EventDirectoryStore):
        self.store = store_type.create(self.root/'journal', self.m)
        self.original_revisions = [canonical(self.store.read().document)]
        publish = self.store.publish

        def retain_original(revision, document):
            publish(revision, document)
            self.original_revisions.append(canonical(document))

        self.store.publish = retain_original
        cp = self.store.read()
        lease = j.consume(self.store, expected_revision=cp.revision,
            expected_manifest_sha256=digest(self.m), binding=self.m['cases'][0],
            milliseconds=4000, artifact_bytes=self.cap,
            directory=self.root/'case', clock=lambda: self.tick)
        for name, data in self.base.items():
            lease.write_artifact(name, data)
        return lease

    def start(self):
        return p.PhysicalCase(self.claim(), self.config, existing_artifacts=self.base)

    def doc(self, count=1, *, complete=False):
        return {'retention': {'case_identity': self.config['case_identity']},
            'rows': [{'i': i, 'value': i/7} for i in range(count)],
            'complete': complete}

    def history(self):
        pointer = (self.store.path/'HEAD').read_text().strip()
        return s.read_history(self.store.path,
            expected_genesis_sha256=self.store.genesis_sha256,
            expected_pointer_sha256=pointer)

    def assert_history_exact(self, checkpoint):
        history = self.history()
        self.assertEqual(list(history.revision_bytes), self.original_revisions)
        self.assertEqual(history.revision_bytes[-1], canonical(checkpoint.document))
        self.assertEqual(len(history.revision_bytes), len(checkpoint.document['events'])+1)
        self.assertEqual(len(list((self.store.path/'pointers').iterdir())),
            len(history.revision_bytes))
        self.assertEqual(history.summary()['stored_bytes'],
            sum(path.stat().st_size for path in self.store.path.rglob('*') if path.is_file()))
        self.assertFalse(history.summary()['execution_restart_authorized'])
        self.assertFalse(history.summary()['scientific_admission_authorized'])
        self.assertFalse(hasattr(history, 'publish'))
        self.assertFalse(hasattr(history, 'consume'))

    def test_completed_event_case_registers_exact_flat_inventory_and_all_revisions(self):
        case = self.start()
        first = self.doc(129)
        case.writer.checkpoint('rows', first)
        parts_before = {name for name in e._inventory(case.lease.directory)
            if name.startswith('physical-part-')}
        case.writer.checkpoint('unchanged', first)
        self.assertEqual(parts_before, {name for name in e._inventory(case.lease.directory)
            if name.startswith('physical-part-')})
        final = self.doc(129, complete=True)
        case.writer.close('completed', 'complete', snapshot=final)
        cp = case.finish()
        view, check = p.inspect_case(cp, case.lease.directory)
        self.assertEqual([view.snapshot(i) for i in range(3)],
            [canonical(first), canonical(first), canonical(final)])
        state = j.replay(cp.document)['cases'][0]
        files = e._inventory(case.lease.directory)
        self.assertEqual(set(files), set(state['artifacts']))
        for name, raw in files.items():
            self.assertEqual(state['artifacts'][name]['size'], len(raw))
            self.assertEqual(state['artifacts'][name]['sha256'], e.sha(raw))
        self.assertEqual(check['artifact_bytes'], sum(map(len, files.values())))
        self.assertEqual(check['artifact_bytes'], view.charged_bytes+
            len(files[p.SEAL])+len(files[p.OUTCOME]))
        self.assertEqual(j.replay(cp.document)['archived_artifact_bytes'], check['artifact_bytes'])
        self.assertEqual(check['status'], 'completed')
        self.assertTrue(check['registered_inventory_exact'])
        self.assertFalse(check['execution_restart_authorized'])
        self.assertFalse(check['scientific_admission_authorized'])
        self.assertFalse(state['rng_started'])
        self.assertTrue(all(path.is_file() for path in case.lease.directory.iterdir()))
        self.assert_history_exact(cp)

    def test_each_v2_checkpoint_registers_parts_as_one_journal_event(self):
        case=self.start();before=len(case.lease.checkpoint.document['events'])
        document=self.doc(e.ROWS_PER_GROUP*3+1)
        case.writer.checkpoint('batched_parts',document)
        events=case.lease.checkpoint.document['events'][before:]
        self.assertEqual(len(events),1);self.assertEqual(events[0]['event']['kind'],'artifact_batch')
        names=[row['name'] for row in events[0]['event']['artifacts']]
        self.assertIn('physical-checkpoint-0000.json',names)
        self.assertGreaterEqual(sum(name.startswith('physical-part-') for name in names),4)
        physical={e.nested_name(name):raw for name,raw in e._inventory(case.lease.directory).items()
            if name.startswith('physical-')}
        view=e.inspect_files(physical,expected_config_sha256=case.writer.config_sha)
        self.assertEqual(view.snapshot(0),canonical(document))

    def test_large_checkpoint_splits_only_journal_events_not_file_receipts(self):
        case=self.start();before=len(case.lease.checkpoint.document['events'])
        document=self.doc(e.ROWS_PER_GROUP*(j.GROUP_ARTIFACT_BATCH_MAX+1))
        case.writer.checkpoint('multi_batch_parts',document)
        events=case.lease.checkpoint.document['events'][before:]
        self.assertEqual(len(events),2)
        self.assertTrue(all(row['event']['kind']=='artifact_batch' for row in events))
        names=[item['name'] for row in events for item in row['event']['artifacts']]
        self.assertEqual(len(names),len(set(names)))
        state=j.replay(case.lease.checkpoint.document)['cases'][-1]
        self.assertEqual(set(names),set(state['artifacts'])-set(self.base)-{'physical-reservation.json'})
        physical={e.nested_name(name):raw for name,raw in e._inventory(case.lease.directory).items()
            if name.startswith('physical-')}
        view=e.inspect_files(physical,expected_config_sha256=case.writer.config_sha)
        self.assertEqual(view.snapshot(0),canonical(document))

    def test_failed_event_case_preserves_all_failed_snapshots_and_revisions(self):
        case = self.start()
        first, final = self.doc(129), self.doc(130)
        case.writer.checkpoint('before_failure', first)
        case.writer.close('failed', 'historical_failure', snapshot=final)
        cp = case.finish(reason='retained deterministic failure')
        view, check = p.inspect_case(cp, case.lease.directory)
        self.assertEqual([view.snapshot(i) for i in range(2)],
            [canonical(first), canonical(final)])
        self.assertEqual(check['status'], 'failed')
        self.assertEqual(view.summary()['status'], 'failed')
        self.assertFalse(check['can_read_complete_evidence'])
        self.assertFalse(check['incomplete_is_statistical_empty'])
        seal = json.loads((case.lease.directory/p.SEAL).read_bytes())
        self.assertFalse(seal['complete'])
        self.assert_history_exact(cp)

    def test_snapshot_above_24_mib_streams_original_digest_without_aggregate_read(self):
        self.cap = e.MAX_BYTES
        self.configure()
        case = self.start()
        document = self.doc(0, complete=True)
        # The same small value is reused across several independently framed
        # top-level list groups; no individual logical value approaches 24 MiB.
        value = 'deterministic-compressible-value-'*1024
        document.update(left=[value]*448, right=[value]*448)
        expected_hash = hashlib.sha256()
        expected_size = 0
        encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False)
        for piece in encoder.iterencode(document):
            raw = piece.encode()
            expected_hash.update(raw)
            expected_size += len(raw)
        self.assertGreater(expected_size, e.MAX_VALUE_BYTES)
        case.writer.close('completed', 'large_complete', snapshot=document)
        cp = case.finish()
        view, check = p.inspect_case(cp, case.lease.directory)
        with self.assertRaisesRegex(ValueError, 'iter_snapshot'):
            view.snapshot(0)
        actual_hash = hashlib.sha256()
        actual_size = 0
        with patch.object(e.ReadOnlyEvidence, 'snapshot',
                side_effect=AssertionError('aggregate read is forbidden')):
            for raw in view.iter_snapshot(0):
                self.assertLessEqual(len(raw), e.PART_BYTES)
                actual_hash.update(raw)
                actual_size += len(raw)
        self.assertEqual(actual_size, expected_size)
        self.assertEqual(actual_hash.hexdigest(), expected_hash.hexdigest())
        row = json.loads(view.checkpoint_bytes[0])
        self.assertEqual(row['snapshot_bytes'], expected_size)
        self.assertEqual(row['snapshot_sha256'], expected_hash.hexdigest())
        self.assertLess(check['artifact_bytes'], 100000)
        self.assertEqual(check['case_cap_bytes'], 18*1024**2)
        self.assert_history_exact(cp)

    def test_v1_readers_reject_v2_even_with_matching_independent_pin(self):
        case = self.start()
        case.writer.close('completed', 'complete', snapshot=self.doc(complete=True))
        cp = case.finish()
        with self.assertRaises(ValueError):
            p1.inspect_case(cp, case.lease.directory)
        files = {e.nested_name(name): raw for name, raw in e._inventory(case.lease.directory).items()
            if name.startswith('physical-')}
        with self.assertRaises(ValueError):
            e1.inspect_files(files, expected_config_sha256=case.writer.config_sha)

    def test_byte_capacity_refusal_writes_nothing_and_preserves_both_footers(self):
        case = self.start()
        case.writer.checkpoint('small', self.doc())
        document = self.doc()
        document['payload'] = ''.join(hashlib.sha256(str(i).encode()).hexdigest()
            for i in range(24576))
        before = e._inventory(case.lease.directory)
        revision = case.lease.checkpoint.revision
        with self.assertRaises(e.EvidenceCapacity):
            case.writer.checkpoint('over_capacity', document)
        self.assertEqual(e._inventory(case.lease.directory), before)
        self.assertEqual(case.lease.checkpoint.revision, revision)
        self.assertTrue(case.writer.capacity_failed)
        case.writer.close('failed', 'capacity')
        cp = case.finish(reason='byte capacity')
        view, check = p.inspect_case(cp, case.lease.directory)
        self.assertEqual(view.summary()['status'], 'failed')
        self.assertLessEqual(check['artifact_bytes'], self.cap)
        footer = json.loads(view.footer_bytes)
        self.assertIsNotNone(footer['capacity_failure'])
        self.assertLessEqual(len(view.footer_bytes), e.FOOTER_RESERVE)
        for name, reserve in p.CLOSURE_RESERVES.items():
            self.assertLessEqual((case.lease.directory/name).stat().st_size, reserve)

    def test_default_1024_file_cap_refuses_entire_batch_before_first_part(self):
        self.cap = 2*1024**2
        self.configure()
        self.assertEqual(self.m['artifact_groups']['physical']['max_files'], 1024)
        case = self.start()
        document = self.doc(0)
        document['rows'] = list(range(e.ROWS_PER_GROUP*1023))
        before = e._inventory(case.lease.directory)
        revision = case.lease.checkpoint.revision
        with self.assertRaises(e.EvidenceCapacity):
            case.writer.checkpoint('too_many_parts', document)
        self.assertEqual(e._inventory(case.lease.directory), before)
        self.assertEqual(case.lease.checkpoint.revision, revision)
        case.writer.close('failed', 'file_count')
        cp = case.finish(reason='file count capacity')
        view, check = p.inspect_case(cp, case.lease.directory)
        self.assertEqual(view.summary()['checkpoints'], 0)
        self.assertEqual(check['status'], 'failed')

    def test_outer_reservations_cannot_be_spent_by_dynamic_member(self):
        lease = self.claim()
        before = e._inventory(lease.directory)
        with self.assertRaisesRegex(ValueError, 'reserved closure'):
            lease.write_artifact('physical-too-large',
                b'x'*(self.cap-sum(p.CLOSURE_RESERVES.values())))
        self.assertEqual(e._inventory(lease.directory), before)

    def test_parent_case_above_18_mib_rejected_before_reservation_write(self):
        self.cap = e.MAX_BYTES+1
        self.configure()
        lease = self.claim()
        before = e._inventory(lease.directory)
        with self.assertRaisesRegex(ValueError, '18 MiB'):
            p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
        self.assertEqual(e._inventory(lease.directory), before)

    def test_full_config_budget_cannot_hide_outer_closure_reserves(self):
        self.config['budget_bytes'] = self.cap
        self.m['artifact_groups'] = p.policy(self.config)
        lease = self.claim()
        before = e._inventory(lease.directory)
        with self.assertRaisesRegex(ValueError, 'closure reserves'):
            p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
        self.assertEqual(e._inventory(lease.directory), before)

    def test_prospective_config_and_registered_base_byte_pins_are_exact(self):
        lease = self.claim()
        before = e._inventory(lease.directory)
        variants = [({**self.config, 'namespace': 'changed'}, self.base),
            (self.config, {}), (self.config, {'base.bin': b'changed bytes'})]
        for config, base in variants:
            with self.subTest(config=config['namespace'], base=base):
                with self.assertRaises(ValueError):
                    p.PhysicalCase(lease, config, existing_artifacts=base)
                self.assertEqual(e._inventory(lease.directory), before)

    def test_wrong_case_or_plan_cannot_enter_even_with_recomputed_prospective_pin(self):
        for field in ('case_identity', 'plan_sha256'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary)
                self.configure()
                self.config[field] = digest({'wrong': field})
                self.m['artifact_groups'] = p.policy(self.config)
                lease = self.claim()
                before = e._inventory(lease.directory)
                with self.assertRaises(ValueError):
                    p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
                self.assertEqual(e._inventory(lease.directory), before)

    def test_schema_change_cannot_enter_with_recomputed_prospective_pin(self):
        self.config['schema'] = e1.SCHEMA
        self.m['artifact_groups'] = p.policy(self.config)
        lease = self.claim()
        before = e._inventory(lease.directory)
        with self.assertRaises(ValueError):
            p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
        self.assertEqual(e._inventory(lease.directory), before)

    def test_exact_physical_policy_required_before_reservation_write(self):
        def wrong_label(groups):
            groups['other'] = groups.pop('physical')

        def wrong_prefix(groups):
            groups['physical']['prefix'] = 'another-'

        def wrong_reserve(groups):
            groups['physical']['reserved_artifacts'][p.OUTCOME] -= 1

        def wrong_window(groups):
            groups['physical']['failure_finalization_milliseconds'] -= 1

        for edit in (wrong_label, wrong_prefix, wrong_reserve, wrong_window):
            with self.subTest(edit=edit.__name__), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary)
                self.configure()
                edit(self.m['artifact_groups'])
                lease = self.claim()
                before = e._inventory(lease.directory)
                with self.assertRaises(ValueError):
                    p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
                self.assertEqual(e._inventory(lease.directory), before)

    def test_full_snapshot_store_cannot_be_v2_parent_authority(self):
        lease = self.claim(store_type=j.DirectoryStore)
        before = e._inventory(lease.directory)
        with self.assertRaisesRegex(ValueError, 'event engineering parent'):
            p.PhysicalCase(lease, self.config, existing_artifacts=self.base)
        self.assertEqual(e._inventory(lease.directory), before)

    def test_scientific_manifest_cannot_enable_v2_physical_policy(self):
        scientific = copy.deepcopy(self.m)
        scientific['mode'] = 'scientific'
        scientific['cases'] = [{**self.m['cases'][0],
            'case_identity': digest({'case': i}),
            'role': 'calibration' if i < 127 else 'evaluation'} for i in range(151)]
        with self.assertRaisesRegex(ValueError, 'engineering-only'):
            j.validate_manifest(scientific)
        self.assertFalse((self.root/'journal').exists())

    def test_lost_artifact_journal_ack_retains_bytes_and_stops_both_authorities(self):
        case = self.start()
        case.writer.checkpoint('retained_prefix', self.doc(2))
        before_count = len(self.history().revision_bytes)
        original = self.store.publish

        def lost_ack(revision, document):
            original(revision, document)
            raise OSError('lost artifact journal acknowledgement')

        with patch.object(self.store, 'publish', side_effect=lost_ack):
            with self.assertRaises(OSError):
                case.writer.checkpoint('uncertain_batch', self.doc(3))
        self.assertTrue(case.lease.broken)
        self.assertTrue(case.writer.poisoned)
        self.assertEqual(len(self.history().revision_bytes), before_count+1)
        cp = self.store.read()
        self.assert_history_exact(cp)
        recovered, check = p.inspect_case(cp, case.lease.directory)
        physical = {e.nested_name(name): raw
            for name, raw in e._inventory(case.lease.directory).items()
            if name.startswith('physical-')}
        view = e.inspect_files(physical, expected_config_sha256=case.writer.config_sha)
        self.assertEqual(len(view.orphan_paths), 0)
        self.assertEqual([view.snapshot(i) for i in range(2)],
            [canonical(self.doc(2)),canonical(self.doc(3))])
        self.assertEqual(recovered.summary(),view.summary())
        self.assertEqual(check['status'], 'consumed')
        self.assertFalse(check['execution_restart_authorized'])
        self.assertFalse(check['can_read_complete_evidence'])
        self.assertFalse(hasattr(view, 'checkpoint'))
        with self.assertRaises(e.EvidenceStopped):
            case.writer.checkpoint('retry', self.doc())
        with self.assertRaises(ValueError):
            case.lease.write_failure_artifact(p.OUTCOME, b'{}')
        result = case.fail(OSError('uncertain'))
        self.assertEqual(result['parent_status'], 'uncertain')
        self.assertFalse(result['outer_footer_written'])
        self.assertNotEqual(j.replay(self.store.read().document)['cases'][0]['status'], 'completed')

    def test_symlink_inventory_fault_poison_is_irreversible_after_file_removal(self):
        case = self.start()
        link = case.lease.directory/'unexpected-link'
        link.symlink_to(case.lease.directory/'base.bin')
        with self.assertRaises(ValueError):
            case.writer.checkpoint('bad_inventory', self.doc())
        self.assertTrue(case.writer.poisoned)
        link.unlink()
        with self.assertRaises(e.EvidenceStopped):
            case.writer.checkpoint('retry', self.doc())
        self.assertEqual(case.writer.count, 0)

    def test_timeout_has_only_bounded_reserved_outer_failure_closure(self):
        case = self.start()
        case.writer.checkpoint('retained', self.doc(2))
        self.tick = 5.
        result = case.fail(TimeoutError('fixed active-time deadline'))
        self.assertEqual(result['parent_status'], 'failed')
        self.assertTrue(result['outer_footer_written'])
        footer = (case.lease.directory/p.OUTCOME).read_bytes()
        self.assertLessEqual(len(footer), p.CLOSURE_RESERVES[p.OUTCOME])
        self.assertIsNotNone(json.loads(footer)['physical_closure_error'])
        self.assertFalse((case.lease.directory/'partial_physical_or_retention.json').exists())
        self.assertFalse((case.lease.directory/e.flat_name('outcome.json')).exists())
        with self.assertRaises(ValueError):
            case.lease.write_artifact('physical-retry', b'x')
        self.assert_history_exact(self.store.read())

    def test_finished_case_cannot_create_another_writer_or_reconsume(self):
        case = self.start()
        case.writer.close('completed', 'complete', snapshot=self.doc(complete=True))
        cp = case.finish()
        with self.assertRaises(e.EvidenceStopped):
            case.writer.checkpoint('again', self.doc())
        with self.assertRaises(ValueError):
            p.PhysicalCase(case.lease, self.config, existing_artifacts=self.base)
        with self.assertRaises(ValueError):
            j.consume(self.store, expected_revision=cp.revision,
                expected_manifest_sha256=digest(self.m), binding=self.m['cases'][0],
                milliseconds=1000, artifact_bytes=self.cap, directory=self.root/'retry')
        self.assertFalse((self.root/'retry').exists())


if __name__ == '__main__':
    unittest.main()
