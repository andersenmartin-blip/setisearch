"""Tiny current metadata custody checks; no spend or workload execution."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v3_custody_tests',
    ROOT / 'scripts/radio_native_v3_custody_observation.py')
custody = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(custody)


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def contract(root):
    source_pin = raw_pin((ROOT / custody.SELF).read_bytes())
    plan = {'namespace': 'radio-native-v3-control-activation-transition-20261003e',
        'invocation_repository_root': str(root),
        'invocation_ledger_root': str(root / custody.CURRENT_LEDGER_DIRECTORY),
        'current_public_claim_path': custody.CURRENT_PUBLIC_CLAIM_PATH,
        'historical_storage_original_identity_continuity_qualified': False,
        'missing_original_storage_accounted': False,
        'original_identity_continuity_proved': False,
        'retained_storage_component_roles': copy.deepcopy(custody.RETAINED_COMPONENT_ROLES),
        'historical_storage_inputs': copy.deepcopy(custody.ARCHIVAL_INPUT_PINS),
        'code_files': {**copy.deepcopy(custody.ARCHIVAL_INPUT_PINS), custody.SELF: source_pin}}
    freeze = {'input_sha256s': {path: pin['sha256']
        for path, pin in custody.ARCHIVAL_INPUT_PINS.items()},
        'code_sha256s': {custody.SELF: source_pin['sha256']}}
    return str(root / 'results_v3_tiny_scope'), plan, freeze


def populate(root):
    # Only the fixed metadata files (< 0.5 MiB), never native input data.
    for source, relative in custody.SOURCE_TO_CURRENT_COPY.items():
        expected = custody.ARCHIVAL_SOURCE_PINS[source]
        raw = (ROOT / source).read_bytes()
        if raw_pin(raw) != expected:
            raise AssertionError('Retained source metadata pin differs: ' + relative)
        target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def ledger_inventory(root, scope):
    ledger = str(root / custody.CURRENT_LEDGER_DIRECTORY)
    metadata = {'device': 123456, 'inode': 50000001, 'mode': 0o700,
        'nlink': 2, 'uid': os.geteuid(), 'gid': os.getegid(), 'bytes': 4096,
        'allocated_bytes': 4096, 'mtime_ns': 1, 'ctime_ns': 1}
    rows = [{'path': ledger, 'kind': 'directory', **metadata},
        {'path': ledger + '/dispatch-' + 'a' * 64 + '.json', 'kind': 'file',
            **metadata, 'inode': 50000003, 'mode': 0o600, 'nlink': 1, 'bytes': 100,
            'allocated_bytes': 4096},
        {'path': ledger + '/spent-' + 'a' * 64 + '.json', 'kind': 'file',
            **metadata, 'inode': 50000002, 'mode': 0o600, 'nlink': 1, 'bytes': 100,
            'allocated_bytes': 4096}]
    return {'schema': custody.LEDGER_STORAGE_SCHEMA, 'control_scope': scope,
        'ledger_root': ledger, 'activation_receipt_sha256': 'b' * 64,
        'invocation_spending_sha256': 'c' * 64, 'rows': rows,
        'logical_bytes': 4296, 'allocated_bytes': 12288, 'entry_count': 3,
        'witness_bindings_verified': True, 'ledger_inventory_exact': True,
        'current_observation_stable': True}


def public_spending(root, scope):
    claim = {'state': 'SPENT_BEFORE_DISPATCH', 'tiny_synthetic_metadata': True}
    return {'schema': custody.PUBLIC_SPENDING_SCHEMA,
        'local_witness': {'control_scope': scope,
            'ledger_root': str(root / custody.CURRENT_LEDGER_DIRECTORY)},
        'public_claim': claim, 'public_claim_sha256': hashlib.sha256(custody.canonical(claim)).hexdigest(),
        'dispatch_witness': None}


def retain_envelope(root, spending):
    path = root / custody.CURRENT_PUBLIC_CLAIM_PATH; path.parent.mkdir(parents=True, exist_ok=True)
    normalized = copy.deepcopy(spending); normalized['dispatch_witness'] = None
    path.write_bytes(custody.canonical(normalized) + b'\n')
    for relative in (custody.CURRENT_LAUNCH_CONFIG_PATH, custody.CURRENT_OBSERVER_CAPSULE_PATH):
        (root / relative).write_bytes(custody.canonical({'synthetic_tiny_bootstrap_metadata': Path(relative).name}) + b'\n')


class CurrentRootContractTests(unittest.TestCase):
    def test_current_root_replaces_original_as_independent_caller_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); scope, plan, freeze = contract(root)
            self.assertEqual(custody.validate_contract(plan, freeze,
                repository_root=str(root), execution_scope=scope), str(root))
            with self.assertRaisesRegex(ValueError, 'independently authenticated current'):
                custody.validate_root(plan, str(root) + '-different', None)
            for other in (custody.ORIGINAL_REPOSITORY_ROOT,
                    custody.ORIGINAL_REPOSITORY_ROOT + '/copy',
                    str(Path(custody.ORIGINAL_REPOSITORY_ROOT).parent)):
                with self.subTest(root=other), self.assertRaisesRegex(ValueError, 'original'):
                    custody.validate_root(plan, other)
            self.assertEqual(custody.validate_current_root(str(root)), str(root))
            with self.assertRaisesRegex(ValueError, 'historical scope'):
                custody.validate_current_root(str(root / custody.HISTORICAL_RELATIVE_ROOTS[0]))

    def test_no_original_filesystem_queries_occur_during_path_refusal(self):
        scope, plan, _ = contract(Path('/tmp/current-custody'))
        with mock.patch.object(custody.os, 'open') as opened:
            with self.assertRaises(ValueError):
                custody.validate_root(plan, custody.ORIGINAL_REPOSITORY_ROOT, scope)
            opened.assert_not_called()

    def test_every_old_namespace_marker_and_commit_is_permanently_refused(self):
        scope, plan, _ = contract(Path('/tmp/current-custody'))
        for namespace, marker, commit in custody.SPENT_ACTIVATIONS:
            for field, value in (('namespace', namespace), ('marker_path', marker),
                    ('activation_commit', commit)):
                changed = dict(plan); changed[field] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'spent'):
                    custody.validate_root(changed, '/tmp/current-custody', scope)
        namespace, marker = custody.RETIRED_PREPARATION_IDENTITIES[0]
        for field, value in (('namespace', namespace), ('marker_path', marker)):
            changed = dict(plan); changed[field] = value
            with self.assertRaisesRegex(ValueError, 'retired'):
                custody.validate_root(changed, '/tmp/current-custody', scope)

    def test_current_scope_cannot_reuse_old_scopes_or_journals_or_new_ledger(self):
        root = Path('/tmp/current-custody'); _, plan, _ = contract(root)
        for relative in (*custody.HISTORICAL_RELATIVE_ROOTS, custody.CURRENT_LEDGER_DIRECTORY):
            for suffix in ('', '/child'):
                with self.subTest(path=relative + suffix), self.assertRaises(ValueError):
                    custody.validate_root(plan, str(root), str(root / relative) + suffix)
        for scope in ('/tmp/outside', str(root), str(root / 'config'), str(root / 'results_radio_native_v2_joint_history_20261003a')):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                custody.validate_root(plan, str(root), scope)

    def test_exact_nineteen_metadata_pins_and_source_freeze_are_required(self):
        scope, plan, freeze = contract(Path('/tmp/current-custody'))
        self.assertEqual(len(custody.INPUT_PATHS), 19)
        self.assertEqual(set(custody.SOURCE_TO_CURRENT_COPY), set(custody.ARCHIVAL_SOURCE_PINS))
        self.assertEqual({custody.SOURCE_TO_CURRENT_COPY[path]: pin
            for path, pin in custody.ARCHIVAL_SOURCE_PINS.items()}, custody.ARCHIVAL_INPUT_PINS)
        self.assertEqual(custody.ARCHIVAL_INPUT_MAP_SHA256,
            hashlib.sha256(custody.canonical(custody.ARCHIVAL_INPUT_PINS)).hexdigest())
        for relative in custody.INPUT_PATHS:
            for section in ('inputs', 'material', 'freeze'):
                changed_plan = copy.deepcopy(plan); changed_freeze = copy.deepcopy(freeze)
                target = {'inputs': changed_plan['historical_storage_inputs'],
                    'material': changed_plan['code_files'], 'freeze': changed_freeze['input_sha256s']}[section]
                del target[relative]
                with self.subTest(path=relative, section=section), self.assertRaises(ValueError):
                    custody.validate_contract(changed_plan, changed_freeze,
                        repository_root='/tmp/current-custody', execution_scope=scope)
        changed = copy.deepcopy(freeze); changed['code_sha256s'][custody.SELF] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'custody source'):
            custody.validate_contract(plan, changed, repository_root='/tmp/current-custody', execution_scope=scope)

    def test_copies_never_qualify_missing_history_or_identity_continuity(self):
        scope, plan, freeze = contract(Path('/tmp/current-custody'))
        for field in ('historical_storage_original_identity_continuity_qualified',
                'missing_original_storage_accounted', 'original_identity_continuity_proved'):
            for bad in (True, 0, None, 'qualified'):
                changed = copy.deepcopy(plan); changed[field] = bad
                with self.subTest(field=field, bad=bad), mock.patch.object(custody, '_read_snapshot') as read:
                    with self.assertRaises(ValueError):
                        custody.observe_historical_storage('/tmp/current-custody', plan=changed, freeze=freeze,
                            repository_root='/tmp/current-custody', execution_scope=scope)
                    read.assert_not_called()


class NoFollowReadTests(unittest.TestCase):
    def test_pins_hardlinks_and_symlink_ancestors_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); leaf = root / 'tiny.json'; leaf.write_bytes(b'{"x":1}\n')
            expected = raw_pin(leaf.read_bytes())
            self.assertEqual(custody.read_raw(str(leaf), expected), b'{"x":1}\n')
            with self.assertRaises(ValueError):
                custody.read_raw(str(leaf), {**expected, 'sha256': '0' * 64})
            linked = root / 'alias'; os.link(leaf, linked)
            with self.assertRaisesRegex(ValueError, 'sole-link'):
                custody.read_raw(str(leaf), expected)
            linked.unlink(); linked.symlink_to(leaf)
            with self.assertRaises(ValueError): custody.read_raw(str(linked), expected)
            nested = root / 'nested'; nested.mkdir(); (nested / 'tiny.json').write_bytes(b'{"x":1}\n')
            ancestor_link = root / 'ancestor'; ancestor_link.symlink_to(nested, target_is_directory=True)
            with self.assertRaises(ValueError): custody.read_raw(str(ancestor_link / 'tiny.json'), expected)

    def test_same_length_midread_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            leaf = Path(directory) / 'tiny'; leaf.write_bytes(b'old metadata\n')
            expected = raw_pin(leaf.read_bytes()); original = custody.os.read; changed = False
            def mutate(fd, length):
                nonlocal changed
                raw = original(fd, length)
                if not changed:
                    leaf.write_bytes(b'new metadata\n'); changed = True
                return raw
            with mock.patch.object(custody.os, 'read', side_effect=mutate):
                with self.assertRaisesRegex(ValueError, 'changed'):
                    custody.read_raw(str(leaf), expected)


class TinyArchiveJoinTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); populate(self.root)
        self.scope, self.plan, self.freeze = contract(self.root)
        self.spending = public_spending(self.root, self.scope)
        retain_envelope(self.root, self.spending)

    def observe(self):
        return custody.observe_historical_storage(str(self.root), plan=self.plan,
            freeze=self.freeze, repository_root=str(self.root), execution_scope=self.scope)

    def join(self, components):
        return custody.join_retained_storage_components(components,
            expected_observation_pins={label: custody.value_pin(value) for label, value in components.items()},
            expected_component_roles=custody.RETAINED_COMPONENT_ROLES)

    def components(self):
        _, components = self.observe()
        components['current_ledger'] = ledger_inventory(self.root, self.scope)
        components['current_claim'] = custody.observe_current_claim(self.plan, self.spending,
            repository_root=str(self.root), execution_scope=self.scope)
        return components

    def test_reads_only_current_fixed_files_and_no_archived_code_executes(self):
        original = custody._read_snapshot; paths = []
        def read(path, expected):
            paths.append(path); return original(path, expected)
        with mock.patch.object(custody, '_read_snapshot', side_effect=read):
            _, components = self.observe()
        self.assertEqual(set(paths), {str(self.root / path) for path in custody.INPUT_PATHS})
        self.assertEqual(len(paths), 38)
        self.assertEqual(sum(sum(row['kind'] == 'file' for row in value['rows'])
            for value in components.values()), 19)
        for value in components.values():
            self.assertFalse(value['original_identity_continuity_proved'])
            self.assertFalse(value['missing_original_storage_accounted'])
            self.assertTrue(value['selected_metadata_only'])

    def test_join_charges_selected_archives_and_one_new_ledger_once(self):
        components = self.components(); joined = self.join(components)
        self.assertEqual(joined['logical_bytes'], sum(value['logical_bytes'] for value in components.values()))
        self.assertEqual(joined['allocated_bytes'], sum(value['allocated_bytes'] for value in components.values()))
        self.assertEqual(joined['entry_count'], len(joined['rows']))
        self.assertEqual({row['component'] for row in joined['rows']}, set(custody.RETAINED_COMPONENT_ROLES))
        self.assertTrue(joined['charged_once'])
        archive_roots = []
        for label in custody.ARCHIVAL_COPY_ROOTS:
            expected_root = str(self.root / custody.ARCHIVAL_COPY_ROOTS[label])
            archive_roots.append(expected_root)
            rows = components[label]['rows']
            self.assertIn(expected_root, {row['path'] for row in rows if row['kind'] == 'directory'})
            self.assertTrue(all(row['path'] == expected_root or row['path'].startswith(expected_root + '/') for row in rows))
        self.assertFalse(custody._overlap(*archive_roots))
        for field in ('execution_authorized', 'whole_control_qualified', 'lifetime_accounting_proved',
                'original_identity_continuity_proved', 'missing_original_storage_accounted'):
            self.assertIs(joined[field], False)

    def test_missing_archival_file_is_not_replaced_by_original_or_other_copy(self):
        (self.root / custody.INPUT_PATHS[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'membership'): self.observe()

    def test_earlier_file_change_during_archive_window_is_detected(self):
        original = custody._read_snapshot; calls = 0
        first = self.root / next(iter(custody.ARCHIVAL_INPUT_PINS))
        def mutate(path, expected):
            nonlocal calls
            result = original(path, expected); calls += 1
            if calls == len(custody.INPUT_PATHS): first.write_bytes(b'tampered\n')
            return result
        with mock.patch.object(custody, '_read_snapshot', side_effect=mutate):
            with self.assertRaises(ValueError): self.observe()

    def test_components_cannot_omit_relabel_add_files_or_add_directories(self):
        components = self.components()
        del components['archive_c_metadata_copy']
        with self.assertRaises(ValueError): self.join(components)
        components = self.components(); value = components['archive_b_metadata_copy']
        value['role'] = 'historical_scope'
        with self.assertRaises(ValueError): self.join(components)
        for kind in ('file', 'directory'):
            components = self.components(); value = components['archive_b_metadata_copy']
            row = copy.deepcopy(next(row for row in value['rows'] if row['kind'] == kind))
            row['path'] = str(self.root / 'unselected' / kind); row['inode'] += 50000000
            value['rows'].append(row); value['rows'].sort(key=lambda item: item['path'])
            value['logical_bytes'] += row['bytes']; value['allocated_bytes'] += row['allocated_bytes']; value['entry_count'] += 1
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'membership'):
                self.join(components)

    def test_full_copy_root_membership_rejects_unselected_file_or_directory(self):
        copy_root = self.root / custody.ARCHIVAL_COPY_ROOTS['archive_b_metadata_copy']
        extra_file = copy_root / 'extra'; extra_file.write_bytes(b'tiny\n')
        with self.assertRaisesRegex(ValueError, 'membership'): self.observe()
        extra_file.unlink(); extra_dir = copy_root / 'empty-unselected-directory'; extra_dir.mkdir()
        with self.assertRaisesRegex(ValueError, 'membership'): self.observe()
        extra_dir.rmdir()
        self.observe()

    def test_join_rejects_cross_component_inode_alias_and_forged_totals(self):
        components = self.components(); archive = components['archive_b_metadata_copy']['rows'][0]
        current = components['current_ledger']['rows'][0]
        current.update(device=archive['device'], inode=archive['inode'])
        with self.assertRaisesRegex(ValueError, 'alias'): self.join(components)
        components = self.components(); components['current_ledger']['allocated_bytes'] -= 1
        with self.assertRaisesRegex(ValueError, 'totals'): self.join(components)

    def test_ledger_scope_root_and_admission_flags_are_mandatory(self):
        for field, value in (('control_scope', self.scope + '-other'),
                ('ledger_root', str(self.root / '.radio-native-v2-invocation-ledger')),
                ('witness_bindings_verified', False), ('ledger_inventory_exact', False)):
            ledger = ledger_inventory(self.root, self.scope); ledger[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                custody.observe_joined_storage(str(self.root), plan=self.plan, freeze=self.freeze,
                    repository_root=str(self.root), execution_scope=self.scope, prospective_ledger=ledger,
                    public_spending=self.spending)

    def test_joined_observer_binds_exact_retained_predispatch_envelope(self):
        running = copy.deepcopy(self.spending); running['dispatch_witness'] = {'tiny_synthetic_dispatch': True}
        joined = custody.observe_joined_storage(str(self.root), plan=self.plan, freeze=self.freeze,
            repository_root=str(self.root), execution_scope=self.scope,
            prospective_ledger=ledger_inventory(self.root, self.scope), public_spending=running)
        self.assertEqual(joined['schema'], custody.JOIN_SCHEMA)
        self.assertEqual([row['path'] for row in joined['rows']], sorted(row['path'] for row in joined['rows']))
        claim_files = [row for row in joined['rows'] if row['component'] == 'current_claim'
            and row['path'] == str(self.root / custody.CURRENT_PUBLIC_CLAIM_PATH)]
        self.assertEqual(len(claim_files), 1)
        self.assertEqual(claim_files[0]['raw_pin'], raw_pin((self.root / custody.CURRENT_PUBLIC_CLAIM_PATH).read_bytes()))

    def test_claim_envelope_cannot_be_missing_reformatted_or_contain_extra_directory_entries(self):
        path = self.root / custody.CURRENT_PUBLIC_CLAIM_PATH
        expected = path.read_bytes()
        for raw in (expected.rstrip(b'\n'), expected + b' ', b'{}\n'):
            path.write_bytes(raw)
            with self.subTest(raw=raw[-20:]), self.assertRaises(ValueError):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)
        path.write_bytes(expected)
        extra = path.parent / 'unaccounted'; extra.write_text('tiny')
        with self.assertRaisesRegex(ValueError, 'membership'):
            custody.observe_current_claim(self.plan, self.spending,
                repository_root=str(self.root), execution_scope=self.scope)
        extra.unlink(); path.unlink()
        with self.assertRaises(ValueError):
            custody.observe_current_claim(self.plan, self.spending,
                repository_root=str(self.root), execution_scope=self.scope)

    def test_claim_envelope_hash_local_scope_and_exact_fields_are_mandatory(self):
        cases = []
        changed = copy.deepcopy(self.spending); changed['public_claim_sha256'] = '0' * 64; cases.append(changed)
        changed = copy.deepcopy(self.spending); changed['local_witness']['control_scope'] += '-other'; cases.append(changed)
        changed = copy.deepcopy(self.spending); changed['local_witness']['ledger_root'] += '-other'; cases.append(changed)
        changed = copy.deepcopy(self.spending); changed['unexpected'] = True; cases.append(changed)
        cases.extend([None, {}])
        for changed in cases:
            with self.subTest(envelope=changed), self.assertRaises(ValueError):
                custody.observe_current_claim(self.plan, changed,
                    repository_root=str(self.root), execution_scope=self.scope)

    def test_bootstrap_three_file_inventory_is_metadata_only_and_charged_in_full(self):
        # Labels inside an untrusted config/capsule are content to measure,
        # never evidence that an outer independently pinned admission passed.
        for relative in (custody.CURRENT_LAUNCH_CONFIG_PATH, custody.CURRENT_OBSERVER_CAPSULE_PATH):
            (self.root / relative).write_bytes(custody.canonical({
                'execution_authorized': True, 'self_pin': '0' * 64}) + b'\n')
        observed = custody.observe_current_claim(self.plan, self.spending,
            repository_root=str(self.root), execution_scope=self.scope)
        self.assertEqual(observed['entry_count'], 4)
        self.assertEqual({row['path'] for row in observed['rows'] if row['kind'] == 'file'},
            {str(self.root / relative) for relative in custody.CURRENT_PREDISPATCH_PATHS})
        self.assertEqual(observed['logical_bytes'], sum(row['bytes'] for row in observed['rows']))
        self.assertEqual(observed['allocated_bytes'], sum(row['allocated_bytes'] for row in observed['rows']))
        self.assertIs(observed['execution_authorized'], False)
        self.assertIs(observed['bootstrap_origin_qualified'], False)
        self.assertIs(observed['metadata_only'], True)
        for row in observed['rows']:
            if row['kind'] == 'file':
                self.assertEqual(row['raw_pin'], raw_pin(Path(row['path']).read_bytes()))

    def test_each_bootstrap_file_required_before_and_after_synthetic_dispatch(self):
        running = copy.deepcopy(self.spending); running['dispatch_witness'] = {'synthetic_dispatch': True}
        for relative in (custody.CURRENT_LAUNCH_CONFIG_PATH, custody.CURRENT_OBSERVER_CAPSULE_PATH):
            path = self.root / relative; retained = path.read_bytes(); path.unlink()
            for spending in (self.spending, running):
                with self.subTest(path=relative, dispatched=spending['dispatch_witness'] is not None), self.assertRaisesRegex(ValueError, 'membership'):
                    custody.observe_current_claim(self.plan, spending,
                        repository_root=str(self.root), execution_scope=self.scope)
            path.write_bytes(retained)

    def test_bootstrap_canonical_json_object_and_numeric_bound_are_required(self):
        path = self.root / custody.CURRENT_LAUNCH_CONFIG_PATH; retained = path.read_bytes()
        invalid = (b'', b'[]\n', b'{"x": 1}\n', b'{"x":1,"x":1}\n',
            b'{"x":NaN}\n', b'{"x":1}', b'{"x":1}\n\n')
        for raw in invalid:
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)
        with path.open('wb') as stream:
            # A sparse metadata-only scratch file checks the scan limit without
            # constructing or reading any full engineering input.
            stream.truncate(custody.MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, 'sole-link'):
            custody.observe_current_claim(self.plan, self.spending,
                repository_root=str(self.root), execution_scope=self.scope)
        path.write_bytes(retained)

    def test_bootstrap_symlink_hardlink_and_special_file_are_refused(self):
        for relative in (custody.CURRENT_LAUNCH_CONFIG_PATH, custody.CURRENT_OBSERVER_CAPSULE_PATH):
            path = self.root / relative; retained = path.read_bytes()
            source = self.root / 'external-tiny-bootstrap'; source.write_bytes(retained)
            path.unlink(); path.symlink_to(source)
            with self.subTest(path=relative, type='symlink'), self.assertRaises(ValueError):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)
            path.unlink(); os.link(source, path)
            with self.subTest(path=relative, type='hardlink'), self.assertRaisesRegex(ValueError, 'sole-link'):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)
            path.unlink(); source.unlink(); os.mkfifo(path)
            with self.subTest(path=relative, type='fifo'), self.assertRaisesRegex(ValueError, 'sole-link'):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)
            path.unlink(); path.write_bytes(retained)

    def test_bootstrap_directory_symlink_is_refused(self):
        directory = (self.root / custody.CURRENT_PUBLIC_CLAIM_PATH).parent
        relocated = self.root / 'relocated-tiny-bootstrap'; directory.rename(relocated)
        directory.symlink_to(relocated, target_is_directory=True)
        with self.assertRaises(ValueError):
            custody.observe_current_claim(self.plan, self.spending,
                repository_root=str(self.root), execution_scope=self.scope)

    def test_bootstrap_change_between_first_read_and_stable_recheck_is_detected(self):
        original = custody._read_snapshot; changed = False
        config_path = self.root / custody.CURRENT_LAUNCH_CONFIG_PATH
        def mutate(path, expected=None):
            nonlocal changed
            result = original(path, expected)
            if not changed and path.endswith('/observer-capsule.json'):
                config_path.write_bytes(custody.canonical({'changed_bootstrap_metadata': True}) + b'\n')
                changed = True
            return result
        with mock.patch.object(custody, '_read_snapshot', side_effect=mutate):
            with self.assertRaises(ValueError):
                custody.observe_current_claim(self.plan, self.spending,
                    repository_root=str(self.root), execution_scope=self.scope)

    def test_bootstrap_join_cannot_drop_metadata_or_promote_its_origin(self):
        components = self.components(); claim = components['current_claim']
        removed = next(row for row in claim['rows'] if row['path'].endswith('/launch-config.json'))
        claim['rows'].remove(removed); claim['logical_bytes'] -= removed['bytes']
        claim['allocated_bytes'] -= removed['allocated_bytes']; claim['entry_count'] -= 1
        with self.assertRaisesRegex(ValueError, 'file/directory observation'): self.join(components)
        for field, value in (('metadata_only', False), ('bootstrap_origin_qualified', True), ('execution_authorized', True)):
            components = self.components(); components['current_claim'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.join(components)

    def test_current_ledger_cannot_drop_dispatch_or_relocate_record(self):
        components = self.components(); ledger = components['current_ledger']
        removed = ledger['rows'].pop(1)
        ledger['logical_bytes'] -= removed['bytes']; ledger['allocated_bytes'] -= removed['allocated_bytes']; ledger['entry_count'] -= 1
        with self.assertRaisesRegex(ValueError, 'claim and dispatch'): self.join(components)
        components = self.components(); row = components['current_ledger']['rows'][1]
        row['path'] = row['path'].replace('/dispatch-', '/other-')
        components['current_ledger']['rows'].sort(key=lambda row: row['path'])
        with self.assertRaisesRegex(ValueError, 'filenames'): self.join(components)

    def test_independent_observation_pin_cannot_be_replaced_by_submitted_content(self):
        components = self.components()
        pins = {label: custody.value_pin(value) for label, value in components.items()}
        components['current_ledger']['activation_receipt_sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'independently held'):
            custody.join_retained_storage_components(components,
                expected_observation_pins=pins, expected_component_roles=custody.RETAINED_COMPONENT_ROLES)


if __name__ == '__main__':
    unittest.main()
