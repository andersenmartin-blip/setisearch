"""Tiny read-only adapter tests; no project journal or workload is consumed."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


history = load('scripts/radio_native_v2_historical_observation.py', 'history_adapter_tests')
fixture = load('scripts/radio_native_v2_compact_eight_case_resource_fixture.py', 'history_fixture_tests')


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def contract():
    root = history.ORIGINAL_REPOSITORY_ROOT
    scope = root + '/results_tiny_current_scope'
    plan = {'invocation_repository_root': root,
        'invocation_ledger_root': root + history.PROSPECTIVE_LEDGER_DIRECTORY,
        'retained_storage_component_roles': copy.deepcopy(history.JOINT_HISTORY_COMPONENT_ROLES),
        'historical_storage_original_identity_continuity_qualified': False,
        'historical_storage_inputs': copy.deepcopy(history.HISTORICAL_INPUT_PINS),
        'code_files': {**copy.deepcopy(history.HISTORICAL_INPUT_PINS),
            history.STORAGE_SOURCE: copy.deepcopy(history.STORAGE_IMPLEMENTATION_PIN)}}
    freeze = {'input_sha256s': {path: pin['sha256']
        for path, pin in history.HISTORICAL_INPUT_PINS.items()}}
    return root, scope, plan, freeze


class HistoricalRootAndContractTests(unittest.TestCase):
    def test_exact_original_root_and_distinct_d_root_are_mandatory(self):
        root, scope, plan, freeze = contract()
        self.assertEqual(history.validate_contract(plan, freeze,
            repository_root=root, execution_scope=scope), root)
        for other in (root + '/relocated', root + '/', '/tmp/unchecked-root'):
            with self.subTest(root=other), self.assertRaises(ValueError):
                history.validate_root(plan, other, scope)
        for field, value in (('invocation_repository_root', '/tmp/unchecked-root'),
                ('invocation_ledger_root', root + '/.radio-native-v2-invocation-ledger')):
            changed = copy.deepcopy(plan); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                history.validate_root(changed, root, scope)

    def test_current_scope_cannot_escape_the_independent_root(self):
        root, scope, plan, _ = contract()
        for other in (root, root + '/../outside', '/tmp/other-control', root + '-alias/control'):
            with self.subTest(scope=other), self.assertRaises(ValueError):
                history.validate_root(plan, root, other)

    def test_every_historical_input_needs_exact_plan_and_input_freeze_pin(self):
        root, scope, plan, freeze = contract()
        self.assertEqual(len(history.INPUT_PATHS), 19)
        for path in history.INPUT_PATHS:
            for section in ('map', 'material', 'freeze'):
                changed_plan = copy.deepcopy(plan); changed_freeze = copy.deepcopy(freeze)
                target = {'map': changed_plan['historical_storage_inputs'],
                    'material': changed_plan['code_files'],
                    'freeze': changed_freeze['input_sha256s']}[section]
                del target[path]
                with self.subTest(path=path, section=section), self.assertRaises(ValueError):
                    history.validate_contract(changed_plan, changed_freeze,
                        repository_root=root, execution_scope=scope)

    def test_restored_content_cannot_claim_original_identity_continuity(self):
        root, scope, plan, freeze = contract()
        for value in (True, None, 0, 'qualified'):
            changed = copy.deepcopy(plan)
            changed['historical_storage_original_identity_continuity_qualified'] = value
            with self.subTest(value=value), mock.patch.object(history, '_module') as component:
                with self.assertRaisesRegex(ValueError, 'continuity remains unqualified'):
                    history.observe_historical_storage('/tmp/unchecked-code', plan=changed,
                        freeze=freeze, repository_root=root, execution_scope=scope)
                component.assert_not_called()

    def test_missing_relabelled_or_extra_component_roles_refuse_before_source_io(self):
        root, scope, plan, freeze = contract()
        for name in history.JOINT_HISTORY_COMPONENT_ROLES:
            changed = copy.deepcopy(plan); del changed['retained_storage_component_roles'][name]
            with self.subTest(name=name), mock.patch.object(history, '_module') as component:
                with self.assertRaisesRegex(ValueError, 'mandatory b/c historical'):
                    history.observe_historical_storage('/tmp/unchecked-code', plan=changed,
                        freeze=freeze, repository_root=root, execution_scope=scope)
                component.assert_not_called()
        for name, role in (('historical_c_scope', 'historical_ledger'),
                ('unreviewed_retained_scope', 'historical_scope')):
            changed = copy.deepcopy(plan); changed['retained_storage_component_roles'][name] = role
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'mandatory b/c historical'):
                history.validate_contract(changed, freeze, repository_root=root, execution_scope=scope)

    def test_current_scope_cannot_reuse_or_nest_either_spent_scope_or_journal(self):
        root, scope, plan, _ = contract()
        for retained in (history.HISTORICAL_SCOPE, history.HISTORICAL_C_SCOPE,
                history.HISTORICAL_LEDGER, history.HISTORICAL_C_LEDGER):
            for candidate in (retained, retained + '/new-child'):
                with self.subTest(scope=candidate), self.assertRaisesRegex(ValueError, 'permanently spent'):
                    history.validate_root(plan, root, candidate)

    def test_plan_cannot_select_storage_implementation_or_extra_history(self):
        root, scope, plan, freeze = contract()
        for section, key, value in (('code_files', history.STORAGE_SOURCE,
                {'bytes': 1, 'sha256': '0' * 64}),
                ('historical_storage_inputs', 'unchecked-extra.json',
                {'bytes': 1, 'sha256': '0' * 64})):
            changed = copy.deepcopy(plan); changed[section][key] = value
            with self.subTest(section=section), self.assertRaises(ValueError):
                history.validate_contract(changed, freeze,
                    repository_root=root, execution_scope=scope)

    def test_missing_history_is_refused_before_any_source_load(self):
        root, scope, plan, freeze = contract(); plan.pop('historical_storage_inputs')
        with mock.patch.object(history, '_module') as component:
            with self.assertRaisesRegex(ValueError, 'mandatory'):
                history.observe_historical_storage('/tmp/unchecked-code', plan=plan,
                    freeze=freeze, repository_root=root, execution_scope=scope)
            component.assert_not_called()

    def test_registered_material_inventory_covers_all_history_sources_and_tests(self):
        self.assertEqual(set(fixture.HISTORICAL_INPUT_PATHS), set(history.INPUT_PATHS))
        self.assertTrue(set(history.INPUT_PATHS).issubset(fixture.CODE_FILES))
        for path in (history.SELF, history.STORAGE_SOURCE,
                'scripts/radio_native_v2_prospective_spending.py',
                'tests/test_radio_native_v2_historical_observation.py'):
            self.assertIn(path, fixture.CODE_FILES)
        self.assertEqual(history.HISTORICAL_INPUT_MAP_SHA256,
            hashlib.sha256(history.canonical(history.HISTORICAL_INPUT_PINS)).hexdigest())


class HeldHistoricalSourceTests(unittest.TestCase):
    def test_raw_input_requires_exact_pin_sole_link_and_nofollow_ancestors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; source.write_bytes(b'tiny history\n')
            expected = raw_pin(source.read_bytes())
            self.assertEqual(history.read_raw(str(source), expected), b'tiny history\n')
            with self.assertRaises(ValueError):
                history.read_raw(str(source), {**expected, 'sha256': '0' * 64})
            alias = root / 'alias'; os.link(source, alias)
            with self.assertRaises(ValueError): history.read_raw(str(source), expected)
            alias.unlink()
            nested = root / 'nested'; nested.mkdir(); (nested / 'source').write_bytes(b'tiny history\n')
            link = root / 'linked'; link.symlink_to(nested, target_is_directory=True)
            with self.assertRaises(ValueError): history.read_raw(str(link / 'source'), expected)

    def test_unpinned_historical_source_is_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'unchecked.py'; marker = root / 'executed'
            source.write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
            with self.assertRaises(ValueError):
                history._module(str(root), 'unchecked.py', {'bytes': source.stat().st_size, 'sha256': '0' * 64})
            self.assertFalse(marker.exists())


class JoinedObservationBoundaryTests(unittest.TestCase):
    def test_current_d_inventory_must_bind_scope_and_exact_root_before_history_read(self):
        root, scope, plan, freeze = contract()
        good = {'control_scope': scope, 'ledger_root': plan['invocation_ledger_root']}
        for field, value in (('control_scope', scope + '-other'),
                ('ledger_root', root + '/.radio-native-v2-invocation-ledger')):
            changed = dict(good); changed[field] = value
            with mock.patch.object(history, 'observe_historical_storage') as observed:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    history.observe_joined_storage('/tmp/code', plan=plan, freeze=freeze,
                        repository_root=root, execution_scope=scope, prospective_ledger=changed)
                observed.assert_not_called()

    def test_join_passes_all_five_exact_component_labels_and_roles_to_storage(self):
        root, scope, plan, freeze = contract()
        components = {name: {'sentinel': name} for name in history.JOINT_HISTORY_COMPONENT_ROLES
            if name != 'prospective_ledger'}
        prospective = {'control_scope': scope, 'ledger_root': plan['invocation_ledger_root']}
        storage = mock.Mock(); storage.join_retained_storage_components.return_value = {'schema': 'synthetic-join'}
        with mock.patch.object(history, 'observe_historical_storage',
                return_value=(storage, copy.deepcopy(components))):
            joined = history.observe_joined_storage('/tmp/code', plan=plan, freeze=freeze,
                repository_root=root, execution_scope=scope, prospective_ledger=prospective)
        args, kwargs = storage.join_retained_storage_components.call_args
        self.assertEqual(set(args[0]), set(history.JOINT_HISTORY_COMPONENT_ROLES))
        self.assertEqual(kwargs['expected_component_roles'], history.JOINT_HISTORY_COMPONENT_ROLES)
        self.assertEqual(kwargs['expected_observation_pins'],
            {name: history.value_pin(value) for name, value in args[0].items()})
        self.assertEqual(joined['current_control_scope'], scope)

    def test_d_journal_mutation_on_historical_entry_refuses_join(self):
        self.exercise_window(mutate=True)

    def test_unchanged_d_is_reobserved_on_both_sides_of_historical_window(self):
        self.exercise_window(mutate=False)

    def test_mutable_passed_d_snapshot_cannot_erase_before_history_pin(self):
        root, scope, plan, freeze = contract()
        before = {'allocated_bytes': 512}
        after = {'allocated_bytes': 1024}
        def historical(*args, **kwargs):
            kwargs['prospective_ledger']['allocated_bytes'] = 1024
            return {'sentinel': 'must refuse'}
        with mock.patch.object(fixture, 'invocation_spending_module',
                return_value={'observe_spend_storage': mock.Mock(side_effect=[before, after])}), \
                mock.patch.object(fixture, 'historical_observation_module',
                return_value={'observe_joined_storage': historical}):
            with self.assertRaisesRegex(ValueError, 'changed during historical'):
                fixture.observe_authenticated_invocation_storage(ROOT, plan, freeze, {}, {},
                    execution_scope=scope, repository_root=root)
        self.assertEqual(before, {'allocated_bytes': 512})

    def exercise_window(self, *, mutate):
        root, scope, plan, freeze = contract()
        live = {'control_scope': scope, 'ledger_root': plan['invocation_ledger_root'], 'allocated_bytes': 512}
        events = []; joined = {'current_control_scope': scope, 'sentinel': 'joined'}
        def observe(*args, **kwargs):
            events.append('d')
            self.assertEqual(kwargs['repository_root'], root)
            return copy.deepcopy(live)
        def historical(*args, **kwargs):
            events.append('historical')
            self.assertEqual(kwargs['prospective_ledger']['allocated_bytes'], 512)
            if mutate: live['allocated_bytes'] = 1024
            return joined
        with mock.patch.object(fixture, 'invocation_spending_module',
                return_value={'observe_spend_storage': observe}), \
                mock.patch.object(fixture, 'historical_observation_module',
                return_value={'observe_joined_storage': historical}):
            if mutate:
                with self.assertRaisesRegex(ValueError, 'changed during historical'):
                    fixture.observe_authenticated_invocation_storage(ROOT, plan, freeze, {}, {},
                        execution_scope=scope, repository_root=root)
            else:
                self.assertIs(fixture.observe_authenticated_invocation_storage(ROOT, plan, freeze, {}, {},
                    execution_scope=scope, repository_root=root), joined)
        self.assertEqual(events, ['d', 'historical', 'd'])


class RetainedCObservationTests(unittest.TestCase):
    """Real pinned c metadata; tiny mocked read-only observer calls only."""
    def context(self):
        import json
        relatives = (history.C_RECEIPT, history.C_WITNESS, history.C_PUBLIC_MANIFEST,
            history.C_TERMINAL_INVENTORY, history.C_ORIGINAL_LEDGER_REVIEW,
            *[history.C_HISTORY_PREFIX + suffix for suffix in ('scope-manifest.json',
                'ledger-manifest.json', 'scope-observation.json', 'ledger-observation.json')])
        return {relative: json.loads((ROOT / relative).read_bytes()) for relative in relatives}

    def execute(self, context, *, changed_spend=False):
        old = mock.Mock()
        exact = context[history.C_ORIGINAL_LEDGER_REVIEW]['actual_c_ledger']
        changed = copy.deepcopy(exact); changed['allocated_bytes'] = exact['allocated_bytes'] + 512
        old.observe_spend_storage.side_effect = [copy.deepcopy(exact), changed if changed_spend else copy.deepcopy(exact)]
        storage = mock.Mock()
        storage.observe_retained_scope.side_effect = [
            copy.deepcopy(context[history.C_HISTORY_PREFIX + 'scope-observation.json']),
            copy.deepcopy(context[history.C_HISTORY_PREFIX + 'ledger-observation.json'])]
        with mock.patch.object(history, '_module', return_value=old):
            value = history._observe_c(storage, str(ROOT), context)
        return value, old, storage

    def test_exact_retained_c_public_closure_empty_cases_and_journal_are_bound(self):
        value, old, storage = self.execute(self.context())
        self.assertEqual(set(value), {'historical_c_scope', 'historical_c_ledger'})
        self.assertEqual(old.observe_spend_storage.call_count, 2)
        self.assertEqual(storage.observe_retained_scope.call_count, 2)
        self.assertEqual([call.args[0] for call in storage.observe_retained_scope.call_args_list],
            [history.HISTORICAL_C_SCOPE, history.HISTORICAL_C_LEDGER])
        self.assertTrue(all(call.kwargs['repository_root'] == history.ORIGINAL_REPOSITORY_ROOT
            for call in old.observe_spend_storage.call_args_list))

    def test_c_journal_change_during_scope_observation_refuses(self):
        with self.assertRaisesRegex(ValueError, 'Historical c spend/storage changed'):
            self.execute(self.context(), changed_spend=True)

    def test_c_case_directory_omission_public_file_change_or_relabelled_scope_refuses(self):
        context = self.context()
        missing_case = copy.deepcopy(context)
        manifest = missing_case[history.C_HISTORY_PREFIX + 'scope-manifest.json']
        manifest['rows'] = [row for row in manifest['rows'] if row['path'] != 'cases/case07']
        changed_file = copy.deepcopy(context)
        changed_file[history.C_PUBLIC_MANIFEST]['files'][next(index for index, row in
            enumerate(changed_file[history.C_PUBLIC_MANIFEST]['files'])
            if row['path'].startswith('results_radio_native_v2_compact_control_20261002c/'))]['sha256'] = '0' * 64
        relabelled = copy.deepcopy(context)
        relabelled[history.C_HISTORY_PREFIX + 'scope-manifest.json']['scope'] = history.HISTORICAL_SCOPE
        for changed in (missing_case, changed_file, relabelled):
            with self.subTest(context=next(key for key in changed if changed[key] != context[key])), \
                    self.assertRaises(ValueError):
                self.execute(changed)


if __name__ == '__main__':
    unittest.main()
