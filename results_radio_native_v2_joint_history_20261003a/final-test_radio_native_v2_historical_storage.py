"""Tiny inert retained storage probes; no real marker/ledger/control inputs."""
import copy
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import radio_native_v2_historical_storage as storage


def pin(value):
    raw = storage.canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def metadata(path):
    info = path.lstat()
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'allocated_bytes': info.st_blocks * 512,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def fixture_manifest(root, role='historical_scope'):
    # Fixture-only manifest generation is independent of the observer API.
    rows = []
    for path in sorted([root, *root.rglob('*')], key=lambda path: path.relative_to(root).as_posix()):
        row = {'path': path.relative_to(root).as_posix(),
            'kind': 'directory' if path.is_dir() else 'file', 'metadata': metadata(path)}
        if row['kind'] == 'file':
            raw = path.read_bytes()
            row['raw_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    return {'schema': storage.MANIFEST_SCHEMA, 'role': role, 'scope': str(root), 'rows': rows}


class HistoricalStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = self.root / 'failed-scope'
        self.scope.mkdir()
        (self.scope / 'retained').mkdir()
        self.file = self.scope / 'retained' / 'source.bin'
        self.file.write_bytes(b'abcd')
        self.manifest = fixture_manifest(self.scope)
        self.expected_pin = pin(self.manifest)

    def observe(self, manifest=None, expected_pin=None, scope=None):
        return storage.observe_retained_scope(self.scope if scope is None else scope,
            self.manifest if manifest is None else manifest,
            expected_manifest_pin=self.expected_pin if expected_pin is None else expected_pin)

    def old_ledger(self):
        root = self.root / 'historical-b-ledger'
        root.mkdir(); (root / 'spent.json').write_bytes(b'{"spent":true}\n')
        manifest = fixture_manifest(root, 'historical_ledger')
        return storage.observe_retained_scope(root, manifest, expected_manifest_pin=pin(manifest))

    def new_ledger(self):
        # Exact existing spend-storage representation, without consuming a spend.
        root = self.root / 'prospective-c-ledger'
        root.mkdir(); (root / 'spent.json').write_bytes(b'{"spent":true}\n')
        rows = [{'path': str(root), 'kind': 'directory', **metadata(root)},
            {'path': str(root / 'spent.json'), 'kind': 'file', **metadata(root / 'spent.json')}]
        return {'schema': storage.LEDGER_STORAGE_SCHEMA, 'ledger_root': str(root),
            'control_scope': str(self.root / 'prospective-control-not-created'),
            'activation_receipt_sha256': '1' * 64, 'invocation_spending_sha256': '2' * 64,
            'rows': rows, 'logical_bytes': sum(row['bytes'] for row in rows),
            'allocated_bytes': sum(row['allocated_bytes'] for row in rows),
            'entry_count': 2, 'witness_bindings_verified': True,
            'ledger_inventory_exact': True, 'current_observation_stable': True}

    def inputs(self):
        return self.observe(), self.old_ledger(), self.new_ledger()

    def join(self, values, pins=None):
        labels = ('historical_scope', 'historical_ledger', 'prospective_ledger')
        if pins is None: pins = dict(zip(labels, map(pin, values)))
        return storage.join_historical_storage(*values, expected_observation_pins=pins)

    def test_exact_descriptor_observation_is_read_only_and_charges_directories(self):
        snapshots = {path: metadata(path) for path in [self.scope, self.scope / 'retained', self.file]}
        original_open = os.open
        def read_only_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            self.assertTrue(flags & os.O_NOFOLLOW)
            return original_open(path, flags, *args, **kwargs)
        with mock.patch.object(storage.os, 'open', side_effect=read_only_open):
            observed = self.observe()
            self.assertEqual(observed, self.observe())
        self.assertEqual(observed['entry_count'], 3)
        self.assertEqual(observed['logical_bytes'], sum(info['bytes'] for info in snapshots.values()))
        self.assertEqual(observed['allocated_bytes'], sum(info['allocated_bytes'] for info in snapshots.values()))
        self.assertEqual(snapshots, {path: metadata(path) for path in snapshots})
        self.assertEqual(observed['manifest_sha256'], self.expected_pin['sha256'])
        self.assertFalse(observed['execution_authorized'])
        self.assertEqual(self.file.read_bytes(), b'abcd')

    def test_wrong_external_pin_rejects_before_filesystem_access(self):
        wrong = {**self.expected_pin, 'sha256': '0' * 64}
        with mock.patch.object(storage.os, 'open', side_effect=AssertionError('no disk access')):
            with self.assertRaisesRegex(ValueError, 'independently retained'):
                self.observe(expected_pin=wrong)

    def test_authenticated_manifest_is_detached_from_mutable_caller(self):
        original_open = os.open; changed = False
        def mutate_caller(path, flags, *args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                self.manifest['rows'][-1]['metadata']['bytes'] = 900
                self.manifest['rows'][-1]['raw_pin']['sha256'] = '0' * 64
            return original_open(path, flags, *args, **kwargs)
        with mock.patch.object(storage.os, 'open', side_effect=mutate_caller):
            observed = self.observe()
        self.assertEqual(observed['rows'][-1]['bytes'], 4)
        self.assertEqual(observed['rows'][-1]['raw_pin']['sha256'], hashlib.sha256(b'abcd').hexdigest())

    def test_mutated_headers_at_authentication_boundary_reject_before_disk(self):
        authenticate = storage._authenticate
        changes = {'schema': 'unreviewed-schema', 'role': 'unreviewed-role',
            'scope': str(self.root / 'different-authenticated-scope'), 'rows': []}
        for field, value in changes.items():
            with self.subTest(field=field):
                manifest = copy.deepcopy(self.manifest)
                changed = copy.deepcopy(manifest); changed[field] = value
                authenticated_pin = pin(changed)
                def mutate_at_authentication(original, expected_pin):
                    original[field] = value
                    return authenticate(original, expected_pin)
                with mock.patch.object(storage, '_authenticate', side_effect=mutate_at_authentication):
                    with mock.patch.object(storage.os, 'open', side_effect=AssertionError('no disk access')):
                        with self.assertRaisesRegex(ValueError, 'bounded retained storage manifest'):
                            self.observe(manifest=manifest, expected_pin=authenticated_pin)

    def test_same_size_changed_content_and_updated_metadata_still_rejects_raw_pin(self):
        self.file.write_bytes(b'wxyz')
        changed = copy.deepcopy(self.manifest)
        changed['rows'][-1]['metadata'] = metadata(self.file)
        with self.assertRaisesRegex(ValueError, 'raw file differs'):
            self.observe(manifest=changed, expected_pin=pin(changed))

    def test_changed_content_or_mode_rejects_retained_metadata(self):
        self.file.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            self.observe()

    def test_empty_file_raw_pin_is_verified(self):
        self.file.write_bytes(b'')
        empty = fixture_manifest(self.scope)
        observed = self.observe(manifest=empty, expected_pin=pin(empty))
        self.assertEqual(observed['rows'][-1]['raw_pin'], {'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()})

    def test_unexpected_file_dotfile_directory_or_fifo_rejected_without_read(self):
        for name, kind in (('unlisted', 'file'), ('.hidden', 'file'), ('subdir', 'directory'), ('pipe', 'fifo')):
            with self.subTest(kind=kind, name=name):
                path = self.scope / 'retained' / name
                if kind == 'directory': path.mkdir()
                elif kind == 'fifo': os.mkfifo(path)
                else: path.write_bytes(b'unexpected')
                manifest = copy.deepcopy(self.manifest)
                manifest['rows'][1]['metadata'] = metadata(self.scope / 'retained')
                with mock.patch.object(storage.os, 'read', side_effect=AssertionError('extra file never read')):
                    with self.assertRaisesRegex(ValueError, 'Unexpected'):
                        self.observe(manifest=manifest, expected_pin=pin(manifest))
                if kind == 'directory': path.rmdir()
                else: path.unlink()

    def test_symlink_and_fifo_replacements_are_not_opened_as_files(self):
        for kind in ('symlink', 'fifo'):
            with self.subTest(kind=kind):
                self.file.unlink()
                if kind == 'symlink': self.file.symlink_to(self.root / 'absent-target')
                else: os.mkfifo(self.file)
                manifest = copy.deepcopy(self.manifest)
                manifest['rows'][1]['metadata'] = metadata(self.scope / 'retained')
                with self.assertRaisesRegex(ValueError, 'Special, symlink or hardlink'):
                    self.observe(manifest=manifest, expected_pin=pin(manifest))
                self.file.unlink(); self.file.write_bytes(b'abcd')

    def test_hardlink_outside_scope_is_rejected(self):
        os.link(self.file, self.root / 'outside-alias')
        with self.assertRaisesRegex(ValueError, 'Special, symlink or hardlink'):
            self.observe()

    def test_symlink_ancestor_is_rejected(self):
        alias = self.root / 'alias'; alias.symlink_to(self.scope, target_is_directory=True)
        manifest = copy.deepcopy(self.manifest); manifest['scope'] = str(alias)
        with self.assertRaisesRegex(ValueError, 'ancestor directory'):
            self.observe(manifest=manifest, expected_pin=pin(manifest), scope=alias)

    def test_symlink_swap_between_named_stat_and_open_fails_closed(self):
        original_open = os.open
        def swap(path, flags, *args, **kwargs):
            if path == 'source.bin':
                self.file.unlink(); self.file.symlink_to(self.root / 'absent-target')
            return original_open(path, flags, *args, **kwargs)
        with mock.patch.object(storage.os, 'open', side_effect=swap):
            with self.assertRaises((ValueError, OSError)):
                self.observe()

    def test_late_mutation_of_already_read_file_is_detected_with_held_descriptor(self):
        last = self.scope / 'retained' / 'z.bin'; last.write_bytes(b'last')
        manifest = fixture_manifest(self.scope); original_read = os.read
        def mutate(fd, count):
            raw = original_read(fd, count)
            if raw == b'last': self.file.write_bytes(b'wxyz')
            return raw
        with mock.patch.object(storage.os, 'read', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'metadata changed'):
                self.observe(manifest=manifest, expected_pin=pin(manifest))

    def test_scope_rebinding_during_read_is_detected(self):
        original_read = os.read; moved = False
        def rebind(fd, count):
            nonlocal moved
            raw = original_read(fd, count)
            if raw and not moved:
                moved = True; self.scope.rename(self.root / 'moved-scope'); self.scope.mkdir()
            return raw
        with mock.patch.object(storage.os, 'read', side_effect=rebind):
            with self.assertRaisesRegex(ValueError, '(metadata|named identity) changed'):
                self.observe()

    def test_duplicate_manifest_inode_and_integer_overflow_reject_before_disk(self):
        for kind in ('alias', 'overflow', 'too_many'):
            with self.subTest(kind=kind):
                manifest = copy.deepcopy(self.manifest)
                if kind == 'alias':
                    manifest['rows'][-1]['metadata']['inode'] = manifest['rows'][0]['metadata']['inode']
                elif kind == 'overflow':
                    manifest['rows'][-1]['metadata']['allocated_bytes'] = storage.MAX_INTEGER + 1
                else: manifest['rows'] *= storage.MAX_ENTRIES // len(manifest['rows']) + 1
                with mock.patch.object(storage.os, 'open', side_effect=AssertionError('no disk access')):
                    with self.assertRaises(ValueError):
                        self.observe(manifest=manifest, expected_pin=pin(manifest))

    def test_canonical_paths_and_unexpected_manifest_fields_are_rejected(self):
        for path in ('/tmp//bad', '/tmp/../bad', '/tmp/./bad', '/tmp/bad\\name', '/tmp/bad\nname', '/'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError): self.observe(scope=path)
        manifest = {**self.manifest, 'execution_authorized': True}
        with self.assertRaises(ValueError): self.observe(manifest=manifest, expected_pin=pin(manifest))

    def test_join_charges_three_disjoint_components_exactly_once_without_io(self):
        values = self.inputs()
        with mock.patch.object(storage.os, 'open', side_effect=AssertionError('pure join')):
            joined = self.join(values)
        self.assertEqual(joined['entry_count'], 7)
        for field in ('logical_bytes', 'allocated_bytes'):
            self.assertEqual(joined[field], sum(value[field] for value in values))
        self.assertEqual(len({(row['device'], row['inode']) for row in joined['rows']}), 7)
        self.assertEqual([row['role'] for row in joined['components']],
            ['historical_scope', 'historical_ledger', 'prospective_ledger'])
        for field in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'):
            self.assertIs(joined[field], False)
        self.assertTrue(joined['charged_once'])

    def test_changed_observation_fails_external_pin_even_with_plausible_flags(self):
        values = self.inputs(); pins = dict(zip(('historical_scope', 'historical_ledger', 'prospective_ledger'), map(pin, values)))
        values[2]['activation_receipt_sha256'] = '3' * 64
        with self.assertRaisesRegex(ValueError, 'independently retained'):
            self.join(values, pins=pins)

    def test_even_pinned_forged_totals_and_boolean_values_fail(self):
        baseline = self.inputs()
        for field in ('logical_bytes', 'allocated_bytes', 'entry_count'):
            values = copy.deepcopy(baseline); values[2][field] += 1
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'totals differ'): self.join(values)
        values = copy.deepcopy(baseline); values[2]['rows'][1]['bytes'] = True
        with self.assertRaisesRegex(ValueError, 'exact integer'): self.join(values)

    def test_even_pinned_inode_alias_and_canonical_root_overlap_fail(self):
        baseline = self.inputs(); values = copy.deepcopy(baseline)
        values[2]['rows'][1]['device'] = values[0]['rows'][-1]['device']
        values[2]['rows'][1]['inode'] = values[0]['rows'][-1]['inode']
        with self.assertRaisesRegex(ValueError, 'device/inode alias'): self.join(values)
        values = copy.deepcopy(baseline); old = values[2]['ledger_root']
        nested = values[0]['scope'] + '/nested-ledger'; values[2]['ledger_root'] = nested
        for row in values[2]['rows']: row['path'] = nested + row['path'][len(old):]
        with self.assertRaisesRegex(ValueError, 'roots overlap'): self.join(values)

    def test_prospective_control_overlap_and_unverified_ledger_fail(self):
        baseline = self.inputs(); values = copy.deepcopy(baseline)
        values[2]['control_scope'] = values[0]['scope'] + '/prospective'
        with self.assertRaisesRegex(ValueError, 'control scope overlaps'): self.join(values)
        values = copy.deepcopy(baseline); values[2]['witness_bindings_verified'] = False
        with self.assertRaisesRegex(ValueError, 'authenticated prospective'): self.join(values)

    def test_same_component_duplicate_inode_or_escaped_row_fail(self):
        baseline = self.inputs(); values = copy.deepcopy(baseline)
        values[2]['rows'][1]['inode'] = values[2]['rows'][0]['inode']
        with self.assertRaisesRegex(ValueError, 'Duplicate storage inode'): self.join(values)
        values = copy.deepcopy(baseline); values[2]['rows'][1]['path'] = str(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'escapes'): self.join(values)

    def test_combined_storage_exceeding_original_bound_is_rejected(self):
        values = self.inputs()
        current = sum(value['allocated_bytes'] for value in values)
        delta = storage.MAX_STORAGE_BYTES - current + 1
        values[0]['rows'][0]['allocated_bytes'] += delta
        values[0]['allocated_bytes'] += delta
        with self.assertRaisesRegex(ValueError, 'joined storage'): self.join(values)

    def test_combined_entry_capacity_32768_is_not_relaxed(self):
        values = self.inputs(); historical = values[0]
        template = {field: 0 for field in storage.METADATA_FIELDS}
        template.update(device=123456789, inode=100000, mode=0o700, nlink=2)
        rows = [{'path': historical['scope'], 'kind': 'directory', **template}]
        for index in range(storage.MAX_ENTRIES - 2):
            rows.append({'path': historical['scope'] + '/d' + str(index), 'kind': 'directory',
                **template, 'inode': 100001 + index})
        historical.update(rows=rows, logical_bytes=0, allocated_bytes=0, entry_count=len(rows))
        self.assertEqual(storage.MAX_ENTRIES, 32768)
        self.assertEqual(storage.MAX_STORAGE_BYTES, 1536 * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, 'joined storage'): self.join(values)


class JointRetainedStorageTests(unittest.TestCase):
    """Two inert retained controls plus distinct future journal, never spending."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.roles = storage.JOINT_HISTORY_COMPONENT_ROLES.copy()
        self.values = {}
        self.manifests = {}
        for label, role in self.roles.items():
            root = self.root / label
            root.mkdir()
            if role == 'prospective_ledger':
                record = root / 'synthetic-spent-record'
                record.write_bytes(b'inert prospective journal fixture')
                rows = [{'path': str(root), 'kind': 'directory', **metadata(root)},
                    {'path': str(record), 'kind': 'file', **metadata(record)}]
                self.values[label] = {
                    'schema': storage.LEDGER_STORAGE_SCHEMA, 'ledger_root': str(root),
                    'control_scope': str(self.root / 'prospective-d-not-created'),
                    'activation_receipt_sha256': '1' * 64,
                    'invocation_spending_sha256': '2' * 64,
                    'rows': rows, 'logical_bytes': sum(row['bytes'] for row in rows),
                    'allocated_bytes': sum(row['allocated_bytes'] for row in rows),
                    'entry_count': len(rows), 'witness_bindings_verified': True,
                    'ledger_inventory_exact': True, 'current_observation_stable': True}
            else:
                if role == 'historical_scope':
                    (root / 'retained').mkdir()
                    (root / 'retained' / 'closed-data').write_bytes(label.encode('ascii'))
                else:
                    (root / 'synthetic-spent-record').write_bytes(label.encode('ascii'))
                manifest = fixture_manifest(root, role)
                self.manifests[label] = manifest
                self.values[label] = storage.observe_retained_scope(root, manifest,
                    expected_manifest_pin=pin(manifest))
        self.pins = {label: pin(value) for label, value in self.values.items()}

    def join(self, values=None, pins=None, roles=None):
        values = self.values if values is None else values
        if pins is None:
            pins = {label: pin(value) for label, value in values.items()}
        return storage.join_retained_storage_components(values,
            expected_observation_pins=pins,
            expected_component_roles=self.roles if roles is None else roles)

    def replace_root(self, value, replacement):
        field = 'ledger_root' if value['schema'] == storage.LEDGER_STORAGE_SCHEMA else 'scope'
        old = value[field]; value[field] = replacement
        for row in value['rows']:
            row['path'] = replacement + row['path'][len(old):]

    def test_complete_five_member_join_charges_every_scope_and_journal_once_without_io(self):
        with mock.patch.object(storage.os, 'open', side_effect=AssertionError('pure join')):
            joined = self.join()
        self.assertEqual(joined['schema'], storage.JOIN_COMPONENT_SCHEMA)
        self.assertEqual([component['role'] for component in joined['components']], list(self.roles))
        self.assertEqual({component['role']: component['observation_role']
            for component in joined['components']}, self.roles)
        self.assertEqual(joined['entry_count'], 12)
        self.assertEqual(joined['entry_count'], sum(value['entry_count'] for value in self.values.values()))
        for field in ('logical_bytes', 'allocated_bytes'):
            self.assertEqual(joined[field], sum(value[field] for value in self.values.values()))
        self.assertEqual(len({(row['device'], row['inode']) for row in joined['rows']}), 12)
        self.assertEqual({row['component'] for row in joined['rows']}, set(self.roles))
        self.assertIs(joined['charged_once'], True)
        self.assertIs(joined['read_only'], True)
        for field in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved'):
            self.assertIs(joined[field], False)
        self.assertFalse((self.root / 'prospective-d-not-created').exists())

    def test_missing_historical_c_scope_or_journal_fails_even_with_regenerated_pins(self):
        for missing in (('historical_c_scope',), ('historical_c_ledger',),
                ('historical_c_scope', 'historical_c_ledger')):
            with self.subTest(missing=missing):
                values = {label: value for label, value in self.values.items() if label not in missing}
                with mock.patch.object(storage.os, 'open', side_effect=AssertionError('no disk access')):
                    with self.assertRaisesRegex(ValueError, 'complete independently required'):
                        self.join(values)

    def test_missing_or_additional_pins_and_component_labels_fail(self):
        values = copy.deepcopy(self.values); values['unexpected'] = values['historical_b_scope']
        with self.assertRaisesRegex(ValueError, 'complete independently required'):
            self.join(values)
        for label in self.roles:
            with self.subTest(label=label):
                pins = self.pins.copy(); del pins[label]
                with self.assertRaisesRegex(ValueError, 'complete independently required'):
                    self.join(pins=pins)
        values = copy.deepcopy(self.values)
        values['substitute_c_scope'] = values.pop('historical_c_scope')
        with self.assertRaisesRegex(ValueError, 'complete independently required'):
            self.join(values)

    def test_authenticated_wrong_historical_c_role_is_rejected(self):
        for label in ('historical_c_scope', 'historical_c_ledger'):
            with self.subTest(label=label):
                values = copy.deepcopy(self.values)
                values[label]['role'] = 'historical_ledger' if self.roles[label] == 'historical_scope' else 'historical_scope'
                with self.assertRaisesRegex(ValueError, 'read-only historical'):
                    self.join(values)

    def test_duplicate_scope_or_journal_is_refused_under_distinct_required_labels(self):
        for old, duplicate in (('historical_b_scope', 'historical_c_scope'),
                ('historical_b_ledger', 'historical_c_ledger'),
                ('historical_c_ledger', 'prospective_ledger')):
            with self.subTest(old=old, duplicate=duplicate):
                values = copy.deepcopy(self.values)
                if duplicate != 'prospective_ledger':
                    values[duplicate] = copy.deepcopy(values[old])
                else:
                    self.replace_root(values[duplicate], values[old]['scope'])
                with self.assertRaisesRegex(ValueError, 'roots overlap'):
                    self.join(values)

    def test_cross_component_scope_and_journal_inode_aliases_fail_even_when_repinned(self):
        for first, second in (('historical_b_scope', 'historical_c_scope'),
                ('historical_b_ledger', 'historical_c_ledger'),
                ('historical_c_scope', 'prospective_ledger')):
            with self.subTest(first=first, second=second):
                values = copy.deepcopy(self.values)
                source = values[first]['rows'][-1]; target = values[second]['rows'][-1]
                for field in ('device', 'inode'):
                    target[field] = source[field]
                with self.assertRaisesRegex(ValueError, 'device/inode alias'):
                    self.join(values)

    def test_nested_retained_c_journal_and_prospective_roots_are_refused(self):
        for parent, child in (('historical_b_scope', 'historical_c_scope'),
                ('historical_c_scope', 'historical_c_ledger'),
                ('historical_c_ledger', 'prospective_ledger')):
            with self.subTest(parent=parent, child=child):
                values = copy.deepcopy(self.values)
                self.replace_root(values[child], values[parent]['scope'] + '/nested')
                with self.assertRaisesRegex(ValueError, 'roots overlap'):
                    self.join(values)

    def test_future_control_overlap_with_either_c_component_is_refused(self):
        for label in ('historical_c_scope', 'historical_c_ledger'):
            with self.subTest(label=label):
                values = copy.deepcopy(self.values)
                values['prospective_ledger']['control_scope'] = values[label]['scope'] + '/future'
                with self.assertRaisesRegex(ValueError, 'control scope overlaps'):
                    self.join(values)

    def test_historical_c_observation_drift_rejects_independent_byte_pin(self):
        for label in ('historical_c_scope', 'historical_c_ledger'):
            with self.subTest(label=label):
                values = copy.deepcopy(self.values)
                values[label]['rows'][-1]['raw_pin']['sha256'] = '3' * 64
                with self.assertRaisesRegex(ValueError, 'independently retained'):
                    self.join(values, pins=self.pins)

    def test_current_historical_c_file_drift_refuses_its_held_manifest(self):
        label = 'historical_c_scope'
        manifest = self.manifests[label]
        root = Path(manifest['scope'])
        path = root / 'retained' / 'closed-data'
        path.write_bytes(b'x' * path.stat().st_size)
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            storage.observe_retained_scope(root, manifest, expected_manifest_pin=pin(manifest))

    def test_even_repinned_historical_c_unstable_or_authorized_flags_are_refused(self):
        for label in ('historical_c_scope', 'historical_c_ledger'):
            for field in ('authenticated_manifest_matched', 'current_observation_stable', 'read_only', 'execution_authorized'):
                with self.subTest(label=label, field=field):
                    values = copy.deepcopy(self.values)
                    values[label][field] = field == 'execution_authorized'
                    with self.assertRaisesRegex(ValueError, 'read-only historical'):
                        self.join(values)

    def test_role_map_requires_exact_labels_paired_history_and_one_prospective(self):
        invalid = [[], {}, {**self.roles, 'bad/name': 'historical_scope'},
            {**self.roles, 'unknown': 'other'},
            {**self.roles, 'another_future': 'prospective_ledger'},
            {label: role for label, role in self.roles.items() if label != 'historical_c_ledger'}]
        for roles in invalid:
            with self.subTest(roles=roles):
                with self.assertRaises(ValueError):
                    self.join(roles=roles)

    def test_ledger_checks_follow_roles_even_for_labels_without_ledger_suffix(self):
        values = {'b_scope': self.values['historical_b_scope'],
            'b_journal': self.values['historical_b_ledger'],
            'c_scope': self.values['historical_c_scope'],
            'c_journal': copy.deepcopy(self.values['historical_c_ledger']),
            'future_journal': self.values['prospective_ledger']}
        roles = dict(zip(values, self.roles.values()))
        self.assertEqual(self.join(values, roles=roles)['entry_count'], 12)
        value = values['c_journal']; root = value['scope']
        extra = {**value['rows'][0], 'path': root + '/extra-directory', 'inode': 999999999}
        value['rows'].append(extra)
        value['entry_count'] += 1
        value['logical_bytes'] += extra['bytes']; value['allocated_bytes'] += extra['allocated_bytes']
        with self.assertRaisesRegex(ValueError, 'Exactly one ledger root directory'):
            self.join(values, roles=roles)

    def test_combined_five_member_charge_keeps_original_whole_storage_cap(self):
        values = copy.deepcopy(self.values)
        delta = storage.MAX_STORAGE_BYTES - sum(value['allocated_bytes'] for value in values.values()) + 1
        values['historical_c_scope']['rows'][0]['allocated_bytes'] += delta
        values['historical_c_scope']['allocated_bytes'] += delta
        with self.assertRaisesRegex(ValueError, 'joined storage'):
            self.join(values)
        self.assertEqual(storage.MAX_STORAGE_BYTES, 1536 * 1024 * 1024)
        self.assertEqual(storage.MAX_ENTRIES, 32768)

    def test_authenticated_snapshots_and_requirements_are_detached_from_caller_mutation(self):
        values = copy.deepcopy(self.values); pins = copy.deepcopy(self.pins)
        roles = self.roles.copy(); original = storage._authenticate; changed = False
        def mutate_later(value, expected_pin):
            nonlocal changed
            authenticated = original(value, expected_pin)
            if not changed:
                changed = True
                values['historical_b_scope']['rows'][0]['allocated_bytes'] = storage.MAX_STORAGE_BYTES
                roles['historical_c_scope'] = 'historical_ledger'
                pins['historical_c_scope']['sha256'] = '0' * 64
            return authenticated
        with mock.patch.object(storage, '_authenticate', side_effect=mutate_later):
            joined = self.join(values, pins=pins, roles=roles)
        self.assertEqual(joined['allocated_bytes'], sum(value['allocated_bytes'] for value in self.values.values()))
        self.assertEqual({component['role']: component['observation_role']
            for component in joined['components']}, self.roles)


if __name__ == '__main__':
    unittest.main()
