"""Small read-only preparation negatives; no generator or case is launched."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import radio_native_v2_compact_preparation_audit as audit


class CompactPreparationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative in {*audit.fixture.CODE_FILES, audit.freezer.SELF}:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((audit.REPO / relative).read_bytes())
        self.runtime_root = self.root / 'runtime'
        self.runtime_root.mkdir()
        self.git = self.runtime_root / 'git'
        self.git.write_bytes(b'tiny installed Git identity')
        self.helper = self.runtime_root / 'git-helpers' / 'git-audit'
        self.helper.parent.mkdir()
        self.helper.write_bytes(b'tiny installed Git helper')
        self.library = self.runtime_root / 'libfixture.so'
        self.library.write_bytes(b'tiny required external library')
        self.cache = self.runtime_root / 'stdlib.pyc'
        self.cache.write_bytes(b'tiny independent stdlib bytecode pin')
        self.supplement = {
            'schema': audit.fixture.SCHEMA + '-engineering-runtime-supplement',
            'files': {str(self.cache): audit.pin(self.cache)},
            'repository_bytecode_copied': False,
            'child_python_flags': ['-I', '-S', '-B'],
            'child_repository_imports_use_fresh_source_only': True,
            'scientific_runtime_qualified': False,
        }
        self.start_patch(mock.patch.object(audit.fixture, 'runtime_supplement',
                                          side_effect=lambda: copy.deepcopy(self.supplement)))
        self.start_patch(mock.patch.object(audit, 'expected_supplement',
                                          side_effect=lambda: copy.deepcopy(self.supplement)))
        self.plan = copy.deepcopy(audit.fixture.build_plan(self.root))
        executable_paths = {
            'python': self.plan['runtime_executables']['python']['path'],
            'node': self.plan['runtime_executables']['node']['path'],
            'git': str(self.git),
        }
        files = sorted([*executable_paths.values(), str(self.helper), str(self.library)])
        self.runtime = {
            'runtime_file_inventory': files,
            'runtime_sha256s': {path: audit.pin(path)['sha256'] for path in files},
            'executables': {
                name: {'invocation': path, 'resolved': path,
                       'sha256': audit.pin(path)['sha256'],
                       'version': {'node': 'small-measured-version'} if name == 'node' else
                            sys.version if name == 'python' else 'git fixture 1'}
                for name, path in executable_paths.items()
            },
            'git_exec_path': str(self.helper.parent),
            'git_runtime_file_inventory': [str(self.helper)],
            'git_node_elf_inventory': [str(self.library)],
            'unavailable_unused_python_extensions': {},
            'python': sys.version, 'numpy': audit.np.__version__,
        }
        self.tracked = sorted(str(path.relative_to(self.root))
            for folder in ('src/seti_repeater', 'scripts')
            for path in (self.root / folder).rglob('*') if path.is_file())
        self.start_patch(mock.patch.object(audit, '_command', side_effect=self.command))
        self.runtime_mock = self.start_patch(mock.patch.object(audit, 'expected_runtime',
            side_effect=lambda: copy.deepcopy(self.runtime)))
        code = audit.repository_inventory(self.root)
        inputs = sorted(path for path in audit.fixture.CODE_FILES if path.startswith('tests/'))
        self.freeze = {
            'schema': audit.freezer.SCHEMA, 'freeze_kind': audit.freezer.FREEZE_KIND,
            'mode': 'PROSPECTIVE_ENGINEERING_ONLY', 'namespace': audit.freezer.NAMESPACE,
            **{name: False for name in audit.freezer.DISABLED},
            'transport_qualification': None,
            'repository_code_inventory': code,
            'code_sha256s': {path: audit.pin(self.root / path)['sha256'] for path in code},
            'input_file_inventory': inputs,
            'input_sha256s': {path: audit.pin(self.root / path)['sha256'] for path in inputs},
            **copy.deepcopy(self.runtime),
            'environment_fingerprints': audit.environment_fingerprints(),
            'coverage': dict(audit.COVERAGE),
        }
        # None of the production execution helpers may be entered by an audit.
        for name in ('run_control', 'control_worker', 'verifier_worker',
                     'command_worker', 'exec_command_child', 'observe_process'):
            self.start_patch(mock.patch.object(audit.fixture, name,
                side_effect=AssertionError('Preparation audit must not invoke worker: ' + name)))
        for name in ('default_rng', 'RandomState', 'Generator'):
            self.start_patch(mock.patch.object(audit.np.random, name,
                side_effect=AssertionError('Preparation audit must not construct RNG')))

    def start_patch(self, patch):
        self.addCleanup(patch.stop)
        return patch.start()

    def command(self, argv, *, cwd=None):
        if argv[:4] == ['git', '--no-replace-objects', 'ls-files', '-z']:
            self.assertEqual(Path(cwd), self.root)
            return ('\0'.join(self.tracked) + '\0').encode()
        raise AssertionError('No runtime or mutation subprocess expected: ' + repr(argv))

    def audit(self, *, freeze=True, **kwargs):
        return audit.audit(self.plan, self.freeze if freeze else None, repo=self.root, **kwargs)

    def test_plan_only_is_honestly_incomplete_and_creates_nothing(self):
        before = sorted(str(path) for path in self.root.rglob('*'))
        result = self.audit(freeze=False)
        self.assertFalse(result['original_freezer_structural_validation_verified'])
        self.assertFalse(result['independent_original_local_runtime_scope_verified'])
        self.assertFalse(result['materialized_code_and_derived_pins_verified'])
        self.assertFalse(result['complete_execution_runtime_closure_qualified'])
        self.assertFalse(result['all_five_execution_blockers_closed'])
        self.assertEqual(len(result['remaining_execution_blockers']), 5)
        self.assertIn('Exact current complete original runner/broker freeze.', result['missing_evidence'])
        self.runtime_mock.assert_not_called()
        self.assertEqual(sorted(str(path) for path in self.root.rglob('*')), before)

    def test_full_named_scope_verifies_without_authorization_or_completion_claim(self):
        original = copy.deepcopy(self.plan), copy.deepcopy(self.freeze)
        result = self.audit()
        self.assertTrue(result['independent_original_local_runtime_scope_verified'])
        self.assertTrue(result['original_freezer_structural_validation_verified'])
        self.assertTrue(result['parent_environment_allowlist_fingerprints_verified'])
        self.assertEqual(result['runtime_and_supplement_union_files'], len(self.runtime['runtime_sha256s']) + 1)
        for key, value in audit.AUTHORITY.items():
            self.assertEqual(result[key], value, key)
        self.assertFalse(result['complete_parent_environment_frozen'])
        self.assertFalse(result['exact_material_child_argv_independently_admitted'])
        self.assertFalse(result['public_immutable_preread_verified'])
        self.assertFalse(result['complete_execution_runtime_closure_qualified'])
        self.assertIn(str(Path(audit.__file__).resolve()), result['audit_implementation_code_pins'])
        self.assertFalse(result['audit_implementation_pins_bound_by_freeze'])
        self.assertEqual((self.plan, self.freeze), original)
        self.runtime_mock.assert_called_once_with()

    def test_stale_auditor_implementation_identity_is_refused(self):
        pins = copy.deepcopy(audit.AUDIT_IMPLEMENTATION_PINS)
        pins[str(Path(audit.__file__).resolve())]['sha256'] = '0' * 64
        with mock.patch.object(audit, 'AUDIT_IMPLEMENTATION_PINS', pins):
            with self.assertRaisesRegex(ValueError, 'audit implementation bytes after import'):
                self.audit()

    def test_consistent_runtime_subset_is_refused_by_independent_expected_closure(self):
        # Delete an external library from both map and list. Original structural
        # validation accepts this consistent subset; independent enumeration must
        # discover that it omits a required actual dependency.
        del self.freeze['runtime_sha256s'][str(self.library)]
        self.freeze['runtime_file_inventory'].remove(str(self.library))
        self.freeze['git_node_elf_inventory'] = []
        audit.freezer.validate_freeze(self.freeze)
        with self.assertRaisesRegex(ValueError, 'runtime closure field runtime_file_inventory'):
            self.audit()

    def test_consistent_code_subset_is_refused_by_actual_checkout_enumeration(self):
        relative = 'scripts/radio_native_v2_local_git.js'
        del self.freeze['code_sha256s'][relative]
        self.freeze['repository_code_inventory'].remove(relative)
        audit.freezer.validate_freeze(self.freeze)
        with self.assertRaisesRegex(ValueError, 'repository code inventory'):
            self.audit()

    def test_extra_untracked_source_and_missing_tracked_source_fail(self):
        extra = self.root / 'scripts/new-local-runtime.js'
        extra.write_bytes(b'new actual imported source')
        with self.assertRaisesRegex(ValueError, 'repository code inventory'):
            self.audit()
        extra.unlink()
        # The removed tracked file is outside the plan's material subset, so it
        # specifically exercises complete repository discovery.
        path = self.root / 'scripts/tracked-but-not-plan.py'
        self.tracked.append(str(path.relative_to(self.root)))
        with self.assertRaisesRegex(ValueError, 'absent from independent inventory'):
            self.audit()

    def test_missing_original_freezer_fields_and_claimed_coverage_are_refused(self):
        for field in ('coverage', 'git_exec_path', 'executables', 'numpy'):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.freeze); del changed[field]
                with self.assertRaises(ValueError):
                    audit.audit(self.plan, changed, repo=self.root)
        self.freeze['coverage']['operating_system_kernel_frozen'] = True
        with self.assertRaisesRegex(ValueError, 'original freezer coverage'):
            self.audit()

    def test_authorizing_freeze_claim_and_numeric_false_impostor_are_refused(self):
        for value in (True, 0, None, 'false'):
            with self.subTest(value=value):
                changed = copy.deepcopy(self.freeze); changed['execution_authorized'] = value
                with self.assertRaisesRegex(ValueError, 'cannot grant execution'):
                    audit.audit(self.plan, changed, repo=self.root)
        self.plan['rng_draws'] = False  # False must not pass as the integer zero.
        with self.assertRaisesRegex(ValueError, 'entire current prospective plan'):
            self.audit()

    def test_changed_runtime_and_missing_runtime_bytes_are_refused(self):
        self.library.write_bytes(b'stale runtime changed after freeze')
        with self.assertRaisesRegex(ValueError, 'external runtime bytes changed'):
            self.audit()
        self.library.unlink()
        with self.assertRaises(FileNotFoundError):
            self.audit()

    def test_current_runtime_versions_and_executable_invocations_are_refused(self):
        for field, value in (('version', {'node': 'different version'}),
                             ('invocation', str(self.root / 'wrong-node'))):
            with self.subTest(field=field):
                current = copy.deepcopy(self.runtime)
                current['executables']['node'][field] = value
                with mock.patch.object(audit, 'expected_runtime', return_value=current):
                    with self.assertRaisesRegex(ValueError, 'runtime closure field executables'):
                        self.audit()

    def test_exact_parent_allowlist_is_required_and_current_values_rechecked(self):
        del self.freeze['environment_fingerprints']['NODE_OPTIONS']
        with self.assertRaisesRegex(ValueError, 'Exact runtime environment fingerprint inventory'):
            self.audit()
        self.freeze['environment_fingerprints'] = audit.environment_fingerprints()
        with mock.patch.dict(os.environ, {'NODE_OPTIONS': '--new-unfrozen-setting'}):
            with self.assertRaisesRegex(ValueError, 'parent environment fingerprints'):
                self.audit()

    def test_child_environment_or_python_flags_drift_is_refused(self):
        self.plan['child_environment']['LD_PRELOAD'] = '/unfrozen/library.so'
        with self.assertRaises(ValueError):
            self.audit()
        self.plan = copy.deepcopy(audit.fixture.build_plan(self.root))
        self.plan['engineering_runtime_supplement']['child_python_flags'] = ['-I', '-S']
        with self.assertRaises(ValueError):
            self.audit()

    def test_stale_supplement_inventory_is_refused_despite_current_named_bytes(self):
        # Keep the old plan and its own builder internally self-consistent, while
        # the independent supplement discovery sees a newly installed file.
        current = copy.deepcopy(self.supplement)
        other = self.runtime_root / 'new-stdlib.pyc'; other.write_bytes(b'new bytecode')
        current['files'][str(other)] = audit.pin(other)
        with mock.patch.object(audit, 'expected_supplement', return_value=current):
            with self.assertRaisesRegex(ValueError, 'supplement inventory/bytes/flags'):
                self.audit()

    def test_supplement_and_base_overlap_must_join_one_identical_pin(self):
        self.supplement['files'][str(self.library)] = audit.pin(self.library)
        self.plan = copy.deepcopy(audit.fixture.build_plan(self.root))
        result = self.audit()
        self.assertEqual(result['runtime_and_supplement_union_files'], len(self.runtime['runtime_sha256s']) + 1)
        wrong = copy.deepcopy(self.supplement)
        wrong['files'][str(self.library)] = {'bytes': 3, 'sha256': '0' * 64}
        self.plan['engineering_runtime_supplement'] = wrong
        with self.assertRaises(ValueError):
            self.audit()

    def test_missing_test_input_pin_is_refused(self):
        self.freeze['input_file_inventory'] = []
        self.freeze['input_sha256s'] = {}
        with self.assertRaisesRegex(ValueError, 'omitted prospective material/test pin'):
            self.audit()

    def test_prospective_and_derived_pin_changes_fail_before_workers(self):
        self.plan['derived_code']['prepare.py']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.audit()
        self.plan = copy.deepcopy(audit.fixture.build_plan(self.root))
        path = self.root / audit.fixture.CODE_FILES[0]
        path.write_bytes(path.read_bytes() + b'\n// changed source bytes\n')
        with self.assertRaisesRegex(ValueError, 'prospective code pins'):
            self.audit()

    def test_materialized_pins_are_optional_but_missing_or_modified_files_fail(self):
        code = self.root / 'materialized-code'; sources = self.root / 'materialized-derived'
        sources.mkdir()
        for relative in audit.fixture.CODE_FILES:
            target = code / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((self.root / relative).read_bytes())
        for name, raw in audit.fixture.templates((self.root / audit.fixture.CODE_FILES[0]).read_text()).items():
            (sources / name).write_bytes(raw)
        result = self.audit(materialized_code_root=code, derived_root=sources)
        self.assertTrue(result['materialized_code_and_derived_pins_verified'])
        (sources / 'prepare.py').write_bytes(b'unadmitted different generator')
        with self.assertRaisesRegex(ValueError, 'materialized derived source prepare.py'):
            self.audit(materialized_code_root=code, derived_root=sources)
        (sources / 'prepare.py').unlink()
        with self.assertRaises(FileNotFoundError):
            self.audit(materialized_code_root=code, derived_root=sources)
        with self.assertRaisesRegex(ValueError, 'Both materialized'):
            self.audit(derived_root=sources)

    def test_repository_symlink_hardlink_and_parent_aliases_are_refused(self):
        original = self.root / audit.fixture.CODE_FILES[0]
        raw = original.read_bytes()
        alternate = self.root / 'same-code'; alternate.write_bytes(raw)
        original.unlink(); original.symlink_to(alternate)
        with self.assertRaises(OSError):
            self.audit()
        original.unlink(); os.link(alternate, original)
        with self.assertRaisesRegex(ValueError, 'hardlink aliases'):
            self.audit()
        original.unlink(); original.write_bytes(raw)
        alias = self.root / 'alias'; alias.symlink_to(self.root / 'scripts', target_is_directory=True)
        with self.assertRaises(OSError):
            audit.pin(alias / Path(audit.fixture.CODE_FILES[0]).name)

    def test_external_runtime_path_alias_and_fifo_are_refused(self):
        alias = self.runtime_root / 'library-alias'; alias.symlink_to(self.library)
        del self.freeze['runtime_sha256s'][str(self.library)]
        self.freeze['runtime_sha256s'][str(alias)] = audit.pin(self.library)['sha256']
        self.freeze['runtime_file_inventory'] = sorted(self.freeze['runtime_sha256s'])
        self.freeze['git_node_elf_inventory'] = [str(alias)]
        with self.assertRaisesRegex(ValueError, 'Runtime inventory path alias'):
            self.audit()
        fifo = self.runtime_root / 'fifo'; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'regular audit file'):
            audit.pin(fifo)

    def test_json_duplicate_keys_and_nonfinite_claims_are_refused(self):
        evidence = self.root / 'evidence.json'
        for raw in (b'{"execution_authorized":false,"execution_authorized":true}',
                    b'{"measured":NaN}'):
            evidence.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                audit.read_json(evidence)


class IndependentRuntimeEnumerationTests(unittest.TestCase):
    def test_git_node_elf_closure_recursively_discovers_unlisted_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'node'; first = root / 'first.so'; second = root / 'second.so'
            script = root / 'git-script-helper'
            for path in (executable, first, second):
                path.write_bytes(b'\x7fELFtiny independently observed fixture')
            script.write_bytes(b'#!/unqualified/interpreter\n')
            graph = {executable: {first}, first: {second}, second: set()}
            calls = []
            def ldd(path, *, allow_missing=False):
                calls.append(path)
                return graph[path], []
            with mock.patch.object(audit, '_ldd', side_effect=ldd), \
                    mock.patch.object(audit.freezer, 'elf_dependencies',
                        side_effect=AssertionError('Original closure cannot supply independent expected closure')):
                files = audit._elf_closure({executable, script})
            self.assertEqual(files, {executable, first, second})
            self.assertEqual(set(calls), files)
            self.assertNotIn(script, calls)

    def test_python_inventory_finds_new_sources_and_transitive_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); stdlib = root / 'stdlib'; numpy = root / 'numpy'
            stdlib.mkdir(); numpy.mkdir()
            python = root / 'python'; python.write_bytes(b'python')
            source = stdlib / 'new_source.py'; source.write_bytes(b'newly installed source')
            extension = stdlib / 'new_extension.so'; extension.write_bytes(b'extension')
            package = numpy / '__init__.py'; package.write_bytes(b'numpy')
            dependency = root / 'required.so'; dependency.write_bytes(b'transitive dependency')
            ignored = stdlib / '__pycache__'; ignored.mkdir(); (ignored / 'old.pyc').write_bytes(b'cache')
            def ldd(path, *, allow_missing=False):
                return ({dependency} if path == extension else set()), []
            with mock.patch.object(audit.sysconfig, 'get_path', return_value=str(stdlib)), \
                    mock.patch.object(audit.np, '__file__', str(package)), \
                    mock.patch.object(audit.sys, 'executable', str(python)), \
                    mock.patch.object(audit, '_ldd', side_effect=ldd), \
                    mock.patch.object(audit.freezer, 'runtime_inventory', side_effect=AssertionError('Original inventory cannot supply independent expected closure')), \
                    mock.patch.object(audit.freezer.python_runtime, 'runtime_inventory', side_effect=AssertionError('Historical inventory cannot supply independent expected closure')):
                files, unavailable = audit._python_inventory()
            self.assertEqual(files, {python, source, extension, package, dependency})
            self.assertEqual(unavailable, {})

    def test_missing_loaded_optional_extension_cannot_be_treated_as_unused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); extension = root / 'loaded.so'; extension.write_bytes(b'optional extension')
            numpy = root / 'numpy'; numpy.mkdir(); package = numpy / '__init__.py'; package.write_bytes(b'')
            with mock.patch.object(audit.sysconfig, 'get_path', return_value=str(root)), \
                    mock.patch.object(audit.np, '__file__', str(package)), \
                    mock.patch.object(audit.sys, 'executable', str(extension)), \
                    mock.patch.object(audit, '_ldd', return_value=(set(), ['missing.so => not found'])), \
                    mock.patch.object(audit, '_loaded_files', return_value={str(extension)}):
                with self.assertRaisesRegex(ValueError, 'Loaded Python extension'):
                    audit._python_inventory()


if __name__ == '__main__':
    unittest.main()
