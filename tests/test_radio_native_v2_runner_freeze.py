"""Deterministic local-Git identity tests; no reservations or sample draws."""
from dataclasses import FrozenInstanceError
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import radio_native_v2_runner_freeze as f
from seti_repeater.empty_null_radio import canonical


class PublishedRunnerFreezeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'src/seti_repeater').mkdir(parents=True)
        (self.root / 'scripts').mkdir()
        (self.root / 'runtime/git-helpers').mkdir(parents=True)
        (self.root / 'runtime/git-bin').mkdir()
        self.files = {
            'src/seti_repeater/a.py': b'VALUE = 1\n',
            f.HOST_ADAPTER: b'module.exports = {};\n',
            f.SELF: b'# deterministic helper fixture\n',
            f.CUSTODY_SELF: b'# deterministic custody helper fixture\n',
            'input.json': b'{"prospective":true}',
        }
        for path, content in self.files.items():
            (self.root / path).write_bytes(content)
        self.runtime_paths = {}
        for name in ('python', 'git', 'node', 'extension.so', 'dependency.so'):
            path = self.root / 'runtime' / ('git-bin/git' if name == 'git' else name)
            path.write_bytes(('measured deterministic ' + name).encode())
            self.runtime_paths[name] = str(path)
        self.helper = self.root / 'runtime/git-helpers/git-read'
        self.helper.write_bytes(b'deterministic installed Git helper')
        self.git_environment = {
            **os.environ, 'GIT_AUTHOR_NAME': 'Engineering fixture',
            'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Engineering fixture',
            'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
        }
        self.git('init', '-q')
        for name in ('default_rng', 'RandomState', 'Generator'):
            mocked = patch.object(np.random, name,
                                  side_effect=AssertionError('Freeze must not construct RNG'))
            mocked.start()
            self.addCleanup(mocked.stop)
        runtime_patch = patch.object(f, 'runtime_inventory', side_effect=self.runtime)
        runtime_patch.start()
        self.addCleanup(runtime_patch.stop)
        loaded_patch = patch.object(f.python_runtime, 'loaded_files', return_value=set())
        loaded_patch.start()
        self.addCleanup(loaded_patch.stop)
        self.freeze = f.capture(self.root, ['input.json'])
        self.commit, self.sha256 = self.publish(self.freeze)
        self.verifier = f.PublishedFreeze(self.root, self.commit, 'freeze.json', self.sha256)
        self.manifest = {'mode': 'engineering', 'namespace': f.NAMESPACE,
                         'execution_binding_sha256': self.sha256}

    def runtime(self):
        paths = sorted([*self.runtime_paths.values(), str(self.helper)])
        versions = {'python': f.sys.version, 'git': 'git deterministic fixture',
                    'node': {'node': 'deterministic fixture'}}
        return {
            'runtime_file_inventory': paths,
            'runtime_sha256s': {path: f.sha_file(path) for path in paths},
            'executables': {
                name: {'invocation': self.runtime_paths[name],
                       'resolved': self.runtime_paths[name],
                       'sha256': f.sha_file(self.runtime_paths[name]),
                       'version': versions[name]}
                for name in ('python', 'git', 'node')
            },
            'git_exec_path': str(self.helper.parent),
            'git_runtime_file_inventory': [str(self.helper)],
            'git_node_elf_inventory': [self.runtime_paths['dependency.so']],
            'unavailable_unused_python_extensions': {
                self.runtime_paths['extension.so']: ['fixture_optional.so => not found']},
            'python': f.sys.version, 'numpy': np.__version__,
        }

    def git(self, *arguments):
        return subprocess.check_output(['git', *arguments], cwd=self.root,
                                       env=self.git_environment, text=True)

    def publish(self, freeze, raw=None):
        raw = canonical(freeze) if raw is None else raw
        (self.root / 'freeze.json').write_bytes(raw)
        self.git('add', '.')
        self.git('commit', '-qm', 'prospective fixture')
        return self.git('rev-parse', 'HEAD').strip(), hashlib.sha256(raw).hexdigest()

    def test_capture_and_readback_pin_python_javascript_inputs_and_runtime(self):
        out = self.verifier.verify(self.manifest)
        self.assertEqual(out['freeze_kind'], 'COMPLETE_RUNNER_BROKER_RUNTIME')
        self.assertTrue(out['exact_immutable_git_readback_verified'])
        self.assertTrue(out['local_runtime_files_verified'])
        self.assertFalse(out['remote_publication_verified'])
        self.assertEqual(out['published_files'], 5)
        self.assertEqual(out['runtime_files'], 6)
        self.assertTrue(all(out[key] is False for key in f.DISABLED))

    def test_old_preparation_freeze_refused_even_with_enabled_claims(self):
        old = {'schema': 'radio-whole-cadence-engineering-executable-files-v1',
               'mode': 'ENGINEERING_ONLY', 'execution_authorized': True}
        commit, sha256 = self.publish(old)
        with self.assertRaisesRegex(ValueError, 'preparation freeze refused'):
            f.PublishedFreeze(self.root, commit, 'freeze.json', sha256)

    def test_supplied_transport_receipt_cannot_grant_authority(self):
        with self.assertRaisesRegex(ValueError, 'supplied dictionary is insufficient'):
            f.capture(self.root, ['input.json'], transport_qualification={
                'transport_integration_qualified': True,
                'exact_public_readback_verified': True})
        self.freeze['transport_qualification'] = {'qualified': True}
        with self.assertRaisesRegex(ValueError, 'cannot qualify'):
            f.validate_freeze(self.freeze)

    def test_any_enabled_authority_flag_refused(self):
        for name in f.DISABLED:
            with self.subTest(flag=name):
                changed = self.verifier.freeze
                changed[name] = True
                with self.assertRaisesRegex(ValueError, 'cannot grant execution'):
                    f.validate_freeze(changed)

    def test_execution_stays_disabled_after_successful_verification(self):
        self.verifier.verify(self.manifest)
        for call in (f.refuse_execution, self.verifier.require_execution_authority):
            with self.assertRaisesRegex(ValueError, 'PROSPECTIVE_NOT_EXECUTABLE'):
                call(exact_public_readback_verified=True,
                     transport_integration_qualified=True)

    def test_verified_state_and_metadata_copy_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.verifier.expected = '0' * 64
        self.assertFalse(hasattr(self.verifier, '__dict__'))
        metadata = self.verifier.freeze
        metadata['execution_authorized'] = True
        metadata['code_sha256s'][f.HOST_ADAPTER] = '0' * 64
        self.assertFalse(self.verifier.verify()['execution_authorized'])

    def test_mutable_git_ref_or_abbreviated_commit_refused(self):
        for commit in ('HEAD', self.commit[:12], self.commit.upper()):
            with self.subTest(commit=commit):
                with self.assertRaisesRegex(ValueError, 'Immutable full Git'):
                    f.PublishedFreeze(self.root, commit, 'freeze.json', self.sha256)

    def test_wrong_published_freeze_hash_refused(self):
        with self.assertRaisesRegex(ValueError, 'freeze bytes differ'):
            f.PublishedFreeze(self.root, self.commit, 'freeze.json', '0' * 64)

    def test_noncanonical_published_json_refused_despite_matching_hash(self):
        raw = json.dumps(self.freeze, indent=2).encode()
        commit, sha256 = self.publish(self.freeze, raw=raw)
        with self.assertRaisesRegex(ValueError, 'Canonical published'):
            f.PublishedFreeze(self.root, commit, 'freeze.json', sha256)

    def test_changed_published_javascript_is_detected_before_local_check(self):
        (self.root / f.HOST_ADAPTER).write_bytes(b'module.exports = {changed:true};\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'changed published JavaScript')
        with self.assertRaisesRegex(ValueError, 'Published runner/broker dependency differs'):
            f.PublishedFreeze(self.root, self.git('rev-parse', 'HEAD').strip(),
                              'freeze.json', self.sha256)

    def test_missing_published_input_blob_refused(self):
        self.git('rm', '-q', 'input.json')
        self.git('commit', '-qm', 'missing published input')
        with self.assertRaisesRegex(ValueError, 'not a Git blob'):
            f.PublishedFreeze(self.root, self.git('rev-parse', 'HEAD').strip(),
                              'freeze.json', self.sha256)

    def test_git_replace_refs_cannot_substitute_immutable_commit(self):
        (self.root / f.HOST_ADAPTER).write_bytes(b'changed replacement object\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'replacement target')
        replacement = self.git('rev-parse', 'HEAD').strip()
        self.git('replace', self.commit, replacement)
        self.assertIn('changed replacement', self.git('show', self.commit + ':' + f.HOST_ADAPTER))
        verifier = f.PublishedFreeze(self.root, self.commit, 'freeze.json', self.sha256)
        (self.root / f.HOST_ADAPTER).write_bytes(self.files[f.HOST_ADAPTER])
        self.assertTrue(verifier.verify()['exact_immutable_git_readback_verified'])

    def test_changed_local_javascript_refused(self):
        (self.root / f.HOST_ADAPTER).write_bytes(b'changed local host\n')
        with self.assertRaisesRegex(ValueError, 'Local runner/broker code/input changed'):
            self.verifier.verify()

    def test_missing_tracked_code_refused_in_capture_and_verify(self):
        (self.root / 'src/seti_repeater/a.py').unlink()
        for call in (lambda: f.capture(self.root, ['input.json']), self.verifier.verify):
            with self.assertRaisesRegex(ValueError, 'Tracked runner/broker code missing'):
                call()

    def test_new_javascript_module_invalidates_inventory(self):
        (self.root / 'scripts/new.mjs').write_bytes(b'export const value = 1;\n')
        with self.assertRaisesRegex(ValueError, 'code inventory changed'):
            self.verifier.verify()

    def test_changed_and_missing_inputs_refused(self):
        path = self.root / 'input.json'
        path.write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'code/input changed'):
            self.verifier.verify()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing/escaping local freeze dependency'):
            self.verifier.verify()

    def test_changed_and_missing_runtime_bytes_refused(self):
        path = Path(self.runtime_paths['node'])
        path.write_bytes(b'changed local Node runtime')
        with self.assertRaisesRegex(ValueError, 'runtime dependency bytes changed'):
            self.verifier.verify()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'runtime dependency bytes changed'):
            self.verifier.verify()

    def test_added_runtime_dependency_refused_by_reenumeration(self):
        current = self.runtime()
        added = str(self.root / 'runtime/new-import.so')
        current['runtime_file_inventory'] = sorted([*current['runtime_file_inventory'], added])
        current['runtime_sha256s'][added] = '0' * 64
        with patch.object(f, 'runtime_inventory', return_value=current):
            with self.assertRaisesRegex(ValueError, 'runtime inventory/identity changed'):
                self.verifier.verify()

    def test_executable_resolution_and_versions_are_rechecked(self):
        for key in ('resolved', 'version'):
            with self.subTest(key=key):
                current = self.runtime()
                current['executables']['node'][key] = 'changed deterministic runtime'
                with patch.object(f, 'runtime_inventory', return_value=current):
                    with self.assertRaisesRegex(ValueError, 'identity changed: executables'):
                        self.verifier.verify()

    def test_runtime_environment_drift_refused(self):
        changed = f.environment_fingerprints()
        changed['NODE_OPTIONS'] = '0' * 64
        with patch.object(f, 'environment_fingerprints', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'Runtime environment changed'):
                self.verifier.verify()

    def test_loaded_optional_unavailable_extension_refused(self):
        with patch.object(f.python_runtime, 'loaded_files',
                          return_value={self.runtime_paths['extension.so']}):
            with self.assertRaisesRegex(ValueError, 'Unavailable optional Python extension'):
                self.verifier.verify()

    def test_science_mode_wrong_namespace_or_manifest_binding_refused(self):
        for key, value in (('mode', 'scientific'), ('namespace', 'other-scope'),
                           ('execution_binding_sha256', '0' * 64)):
            with self.subTest(key=key):
                manifest = {**self.manifest, key: value}
                with self.assertRaisesRegex(ValueError, 'manifest/freeze binding changed'):
                    self.verifier.verify(manifest)

    def test_inventory_hash_omission_and_conflicting_input_pin_refused(self):
        changed = self.verifier.freeze
        del changed['code_sha256s'][f.HOST_ADAPTER]
        with self.assertRaisesRegex(ValueError, 'inventory/hash map differs'):
            f.validate_freeze(changed)
        changed = self.verifier.freeze
        changed['input_sha256s'][f.HOST_ADAPTER] = '0' * 64
        changed['input_file_inventory'] = sorted(changed['input_sha256s'])
        with self.assertRaisesRegex(ValueError, 'Conflicting code/input identities'):
            f.validate_freeze(changed)

    def test_noncanonical_or_escaping_input_path_refused(self):
        for path in ('../input.json', '/input.json', 'scripts//host.js',
                     'scripts/host\n.js', 'scripts/host\t.js'):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, 'repository-relative file path'):
                    f.capture(self.root, [path])

    def test_fresh_capture_pins_canonical_custody_and_historical_metadata_requires_explicit_current_gate(self):
        manifest=self.freeze['runtime_custody_manifest']
        self.assertEqual(self.freeze['runtime_custody_manifest_sha256'],hashlib.sha256(canonical(manifest)).hexdigest())
        self.assertEqual(manifest['schema'],f.custody.SCHEMA)
        self.assertEqual(set(manifest['activation_only_paths']),{self.runtime_paths['git'],str(self.helper)})
        self.assertEqual(manifest['runtime_files'][self.runtime_paths['dependency.so']]['lifecycle'],'material')
        historical=copy.deepcopy(self.freeze)
        for field in f.CUSTODY_FIELDS: del historical[field]
        self.assertIs(f.validate_freeze(historical),historical)
        with self.assertRaisesRegex(ValueError,'historical freeze is not admissible'):
            f.validate_freeze(historical,require_runtime_custody=True)

    def test_custody_field_omission_tampering_reclassification_and_unknown_fields_refused(self):
        for field in f.CUSTODY_FIELDS:
            changed=copy.deepcopy(self.freeze); del changed[field]
            with self.subTest(field=field),self.assertRaises(ValueError): f.validate_freeze(changed)
        changed=copy.deepcopy(self.freeze); changed['runtime_custody_manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'custody manifest SHA'): f.validate_freeze(changed)
        changed=copy.deepcopy(self.freeze); manifest=changed['runtime_custody_manifest']
        manifest['activation_only_paths']=sorted([*manifest['activation_only_paths'],self.runtime_paths['python']])
        manifest['runtime_files'][self.runtime_paths['python']]['lifecycle']='activation_only'
        manifest['material_runtime_paths']-=1
        changed['runtime_custody_manifest_sha256']=f.custody.manifest_sha256(manifest)
        with self.assertRaisesRegex(ValueError,'lifecycle/root policy'): f.validate_freeze(changed)
        changed=copy.deepcopy(self.freeze); changed['activation_only_runtime_complete']=True
        with self.assertRaisesRegex(ValueError,'supported complete freeze fields'): f.validate_freeze(changed)

    def test_shared_git_discovered_library_and_node_executable_cannot_be_activation_only(self):
        changed=copy.deepcopy(self.freeze)
        changed['git_runtime_file_inventory']=sorted([str(self.helper),self.runtime_paths['dependency.so'],self.runtime_paths['node']])
        policy=f.runtime_custody_arguments(changed)
        self.assertNotIn(self.runtime_paths['dependency.so'],policy['activation_only_paths'])
        self.assertNotIn(self.runtime_paths['node'],policy['activation_only_paths'])
        alias=self.root/'library-extra-alias'; alias.hardlink_to(Path(self.runtime_paths['dependency.so']))
        with self.assertRaisesRegex(ValueError,'must be sole-link'):
            f.custody.build_manifest(**policy)

    def test_material_wrapper_never_runs_git_or_discovers_runtime_after_receipt(self):
        Path(self.runtime_paths['git']).unlink(); self.helper.unlink()
        with patch.object(f,'runtime_inventory',side_effect=AssertionError('No Git runtime discovery')), \
                patch.object(f,'repository_inventory',side_effect=AssertionError('No Git ls-files')), \
                patch.object(f.subprocess,'check_output',side_effect=AssertionError('No Git subprocess')), \
                patch.object(f.custody.os,'scandir',side_effect=AssertionError('No alias root enumeration')):
            receipt=f.validate_material_runtime_custody(self.freeze)
        self.assertEqual(receipt['activation_only_runtime_paths_opened'],0)
        self.assertEqual(receipt['material_runtime_paths_checked'],4)
        self.assertFalse(receipt['execution_authorized'])

    def test_activation_wrapper_rechecks_runtime_metadata_not_just_bytes(self):
        f.validate_activation_runtime_custody(self.freeze)
        path=Path(self.runtime_paths['node']); info=path.stat(); raw=path.read_bytes(); held=os.open(path,os.O_RDONLY)
        try:
            path.unlink(); path.write_bytes(raw); os.utime(path,ns=(info.st_atime_ns,info.st_mtime_ns))
            with self.assertRaisesRegex(ValueError,'manifest differs'): f.validate_activation_runtime_custody(self.freeze)
            with self.assertRaisesRegex(ValueError,'Material runtime custody'): f.validate_material_runtime_custody(self.freeze)
        finally: os.close(held)

    def test_source_input_and_repository_ancestor_aliases_are_refused(self):
        original=self.root/'input.json'; alias=self.root/'input-alias'; alias.hardlink_to(original)
        with self.assertRaisesRegex(ValueError,'must be sole-link'): f.capture(self.root,['input.json'])
        alias.unlink(); source=self.root/'scripts/alias.py'; source.symlink_to(self.root/'src/seti_repeater/a.py')
        with self.assertRaisesRegex(ValueError,'alias or special'): f.capture(self.root,['input.json'])
        source.unlink(); alternate=self.root.parent/(self.root.name+'-alias'); alternate.symlink_to(self.root,target_is_directory=True)
        self.addCleanup(alternate.unlink)
        with self.assertRaises(OSError): f.capture(alternate,['input.json'])


class RuntimeClosureTests(unittest.TestCase):
    def test_runtime_inventory_merges_python_numpy_git_node_and_elf_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helpers = root / 'git-helpers'
            helpers.mkdir()
            helper = helpers / 'git-helper'
            helper.write_bytes(b'installed helper')
            paths = {}
            for name in ('python', 'git', 'node', 'numpy-extension.so', 'closure.so'):
                path = root / name
                path.write_bytes(name.encode())
                paths[name] = str(path)
            unavailable = {paths['numpy-extension.so']: ['optional.so => not found']}
            def executable(name):
                return {'invocation': paths[name], 'resolved': paths[name],
                        'sha256': f.sha_file(paths[name]), 'version': name}
            # Other tests use a minimal measured runtime; this test exercises
            # the actual closure assembler with deterministic local files.
            with patch.object(f.python_runtime, 'runtime_inventory',
                              return_value=([paths['numpy-extension.so']], unavailable)), \
                 patch.object(f, 'executable_identity', side_effect=executable), \
                 patch.object(f, 'elf_dependencies', return_value=[paths['closure.so']]), \
                 patch.object(f.subprocess, 'check_output', return_value=str(helpers)):
                result = f.runtime_inventory()
            self.assertEqual(result['runtime_file_inventory'], sorted([*paths.values(), str(helper)]))
            self.assertEqual(result['unavailable_unused_python_extensions'], unavailable)
            self.assertEqual(result['git_runtime_file_inventory'], [str(helper)])
            self.assertEqual(result['git_node_elf_inventory'], [paths['closure.so']])
            for path in result['runtime_file_inventory']:
                self.assertEqual(result['runtime_sha256s'][path], f.sha_file(path))

    def test_elf_resolution_recurses_and_refuses_missing_transitive_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / name for name in ('node', 'libfirst.so', 'libsecond.so')]
            for path in paths:
                path.write_bytes(b'\x7fELF deterministic library')
            def ldd(arguments, **kwargs):
                current = paths.index(Path(arguments[-1]))
                output = ('lib => ' + str(paths[current + 1]) + ' (0x1000)\n'
                          if current < 2 else 'statically linked\n')
                return subprocess.CompletedProcess(arguments, 0, output, '')
            with patch.object(f.subprocess, 'run', side_effect=ldd) as run:
                self.assertEqual(f.elf_dependencies([paths[0]]), sorted(map(str, paths)))
                self.assertEqual(run.call_count, 3)
            missing = subprocess.CompletedProcess([], 0, 'missing.so => not found\n', '')
            with patch.object(f.subprocess, 'run', return_value=missing):
                with self.assertRaisesRegex(ValueError, 'Unresolved/uninspectable'):
                    f.elf_dependencies([paths[0]])


if __name__ == '__main__':
    unittest.main()
