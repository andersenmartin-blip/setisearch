"""Real isolated subprocess tests of source authority; no samples or network."""
import hashlib
import importlib._bootstrap_external as import_external
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from unittest.mock import patch

import radio_native_v2_source_loader as loader


class SourceLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stdlib = Path(sysconfig.get_path('stdlib'))
        cls.runtime = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in stdlib.rglob('*.py')
                       if 'site-packages' not in path.relative_to(stdlib).parts
                       and '__pycache__' not in path.parts}
        executable = str(Path(sys.executable).resolve())
        cls.runtime[executable] = hashlib.sha256(Path(executable).read_bytes()).hexdigest()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'src/seti_repeater').mkdir(parents=True)
        self.entry = self.root / loader.SELF
        self.entry.write_bytes(Path(loader.__file__).read_bytes())
        self.package = self.root / 'src/seti_repeater/__init__.py'
        self.package.write_bytes(b'"""Isolated fixture package."""\n')
        self.module = self.root / 'src/seti_repeater/fixture.py'
        self.module.write_bytes(b'import json\nVALUE = 1\n')
        python = str(Path(sys.executable).resolve())
        self.freeze = {'mode': 'PROSPECTIVE_ENGINEERING_ONLY',
                       **{key: False for key in loader.DISABLED},
                       'runtime_sha256s': dict(self.runtime),
                       'code_sha256s': {
                           str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in (self.entry, self.package, self.module)},
                       'executables': {
                           'python': {'invocation': sys.executable, 'resolved': python,
                                      'sha256': self.runtime[python], 'version': sys.version},
                           'git': {'invocation': '/usr/bin/git'},
                           'node': {'invocation': '/usr/bin/node'},
                       }}
        self.freeze_path = self.root / 'freeze.json'
        self.refresh()

    def refresh(self):
        self.raw = json.dumps(self.freeze, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=True).encode()
        self.freeze_path.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()

    def run_preflight(self, **kwargs):
        return loader.launch_preflight(self.root, self.freeze_path, self.sha,
                                       modules=('seti_repeater.fixture',), **kwargs)

    def test_actual_subprocess_loads_only_frozen_source(self):
        before = list((self.root / 'src').rglob('*.pyc'))
        proof = self.run_preflight()
        self.assertTrue(proof['source_only_imports_verified'])
        self.assertFalse(proof['public_freeze_verified'])
        self.assertFalse(proof['bytecode_cache_read'])
        self.assertFalse(proof['bytecode_cache_write'])
        self.assertTrue(all(proof[key] is False for key in loader.DISABLED))
        self.assertEqual(proof['source_inventory']['seti_repeater.fixture']['kind'],
                         'DIRECT_SOURCE_BYTES')
        self.assertEqual(proof['source_inventory']['json']['kind'], 'DIRECT_SOURCE_BYTES')
        self.assertEqual(proof['bootstrap_origin'],
                         'PINNED_PYTHON_PLUS_THREE_PRELAUNCH_VERIFIED_STARTUP_SOURCES')
        self.assertTrue(proof['startup_cache_prefix_fresh_and_empty'])
        self.assertEqual(proof['source_inventory']['encodings']['kind'],
                         'PRELAUNCH_VERIFIED_CPYTHON_STARTUP_SOURCE')
        self.assertEqual(before, list((self.root / 'src').rglob('*.pyc')))

    def test_timestamp_valid_hostile_pyc_is_ignored(self):
        # This cache would be accepted by ordinary CPython despite good source.
        stamp = int(self.module.stat().st_mtime)
        hostile = compile('import json\nVALUE = 2\n', str(self.module), 'exec')
        cache = Path(importlib.util.cache_from_source(str(self.module)))
        cache.parent.mkdir()
        cache.write_bytes(import_external._code_to_timestamp_pyc(
            hostile, stamp, self.module.stat().st_size))
        control = subprocess.check_output(
            [sys.executable, '-I', '-S', '-B', '-c',
             'import sys;sys.path.insert(0,sys.argv[1]);'
             'from seti_repeater.fixture import VALUE;print(VALUE)', str(self.root / 'src')],
            text=True)
        self.assertEqual(control.strip(), '2')
        # Source-only preflight imports a module that asserts the frozen value.
        checker = self.root / 'src/seti_repeater/check.py'
        checker.write_bytes(b'from .fixture import VALUE\nassert VALUE == 1\n')
        self.freeze['code_sha256s']['src/seti_repeater/check.py'] = hashlib.sha256(checker.read_bytes()).hexdigest()
        self.refresh()
        proof = loader.launch_preflight(self.root, self.freeze_path, self.sha,
                                        modules=('seti_repeater.check',))
        self.assertEqual(proof['source_inventory']['seti_repeater.fixture']['sha256'],
                         self.freeze['code_sha256s']['src/seti_repeater/fixture.py'])

    def test_bytecode_only_import_refused(self):
        cache = self.module.with_suffix('.pyc')
        cache.write_bytes(import_external._code_to_timestamp_pyc(
            compile('VALUE = 2\n', str(self.module), 'exec'), 0, 10))
        self.module.unlink()
        del self.freeze['code_sha256s']['src/seti_repeater/fixture.py']
        self.freeze['code_sha256s']['src/seti_repeater/fixture.pyc'] = hashlib.sha256(cache.read_bytes()).hexdigest()
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Bytecode/non-source module refused'):
            self.run_preflight()

    def test_hostile_pythonpath_and_sitecustomize_are_isolated(self):
        hostile = self.root / 'hostile'
        (hostile / 'seti_repeater').mkdir(parents=True)
        marker = self.root / 'unwanted-side-effect'
        payload = 'open(' + repr(str(marker)) + ',"w").write("executed")\n'
        (hostile / 'sitecustomize.py').write_text(payload)
        (hostile / 'seti_repeater/__init__.py').write_text(payload)
        (self.root / 'sitecustomize.py').write_text(payload)
        (hostile / 'hooks.pth').write_text('import sitecustomize\n')
        with patch.dict(os.environ, {'PYTHONPATH': str(hostile), 'PYTHONHOME': '/absent',
                                     'PYTHONSTARTUP': str(hostile / 'sitecustomize.py'),
                                     'LD_PRELOAD': '/absent-hostile-loader.so'}):
            proof = self.run_preflight()
        self.assertTrue(proof['environment_isolated'])
        self.assertTrue(proof['site_hooks_disabled'])
        self.assertFalse(marker.exists())
        self.assertNotIn(str(hostile), proof['restricted_search_roots'])

    def test_source_mismatch_refused_before_source_side_effect(self):
        marker = self.root / 'unwanted-side-effect'
        self.module.write_text('open(' + repr(str(marker)) + ',"w").write("executed")\n')
        with self.assertRaisesRegex(ValueError, 'Frozen local dependency differs'):
            self.run_preflight()
        self.assertFalse(marker.exists())

    def test_module_omitted_from_freeze_is_not_executed(self):
        del self.freeze['code_sha256s']['src/seti_repeater/fixture.py']
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Import origin absent from freeze'):
            self.run_preflight()

    def test_source_symlink_refused(self):
        data = self.module.read_bytes()
        self.module.unlink()
        outside = self.root / 'outside.py'
        outside.write_bytes(data)
        self.module.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Code symlinks/source escapes refused'):
            self.run_preflight()

    def test_changed_runtime_dependency_refused_before_fixture(self):
        self.freeze['runtime_sha256s'][next(path for path in self.runtime if path.endswith('/json/__init__.py'))] = '0' * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Frozen local dependency differs'):
            self.run_preflight()

    def test_python_executable_identity_mismatch_refused_before_launch(self):
        self.freeze['executables']['python']['sha256'] = '0' * 64
        self.refresh()
        with patch.object(subprocess, 'run', side_effect=AssertionError('Must refuse before child')):
            with self.assertRaisesRegex(ValueError, 'Pinned launch executable/entrypoint differs'):
                self.run_preflight()

    def test_entrypoint_identity_mismatch_refused_before_launch(self):
        self.entry.write_text('raise AssertionError("untrusted entry")\n')
        with patch.object(subprocess, 'run', side_effect=AssertionError('Must refuse before child')):
            with self.assertRaisesRegex(ValueError, 'Pinned launch executable/entrypoint differs'):
                self.run_preflight()

    def test_freeze_hash_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, 'freeze bytes differ'):
            loader.launch_preflight(self.root, self.freeze_path, '0' * 64,
                                    modules=('seti_repeater.fixture',))

    def test_enabled_permission_refused_before_launch(self):
        self.freeze['rng_authorized'] = True
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'grants no authority'):
            self.run_preflight()

    def test_direct_child_without_isolation_refused(self):
        result = subprocess.run([sys.executable, str(self.entry), '--child', str(self.root),
                                 str(self.freeze_path), self.sha, 'seti_repeater.fixture'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires Python -I -S -B', result.stderr)

    def test_bootstrap_json_duplicate_or_unsupported_number_refused(self):
        import _json
        for raw in (b'{"a":1,"a":2}', b'{"a":1.0}', b'{"a":01}', b'{"a":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                loader._child_json(raw, _json.scanstring)

    def test_verified_typing_namespace_aliases_are_bound_to_source(self):
        self.module.write_bytes(b'import typing\n')
        self.freeze['code_sha256s']['src/seti_repeater/fixture.py'] = hashlib.sha256(self.module.read_bytes()).hexdigest()
        self.refresh()
        proof = self.run_preflight()
        self.assertEqual(set(proof['derived_module_alias_inventory']), {'typing.io', 'typing.re'})
        self.assertEqual(proof['derived_module_alias_inventory']['typing.io']['source_sha256'],
                         proof['source_inventory']['typing']['sha256'])

    def test_arbitrary_specless_alias_refused(self):
        self.module.write_bytes(b'import sys\nsys.modules["untracked_alias"] = object()\n')
        self.freeze['code_sha256s']['src/seti_repeater/fixture.py'] = hashlib.sha256(self.module.read_bytes()).hexdigest()
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Loaded module has no pinned import origin'):
            self.run_preflight()


class SourceHelperTests(unittest.TestCase):
    """Operational source-only helper launch controls with a metadata fixture."""
    setUpClass = SourceLoaderTests.__dict__['setUpClass']
    setUp = SourceLoaderTests.setUp
    refresh = SourceLoaderTests.refresh

    def prepare_fixture(self):
        self.helper = self.root / 'scripts/radio_native_v2_fixture_helper.py'
        self.helper.write_bytes(b'import json\nimport sys\n'
                               b'def main():\n'
                               b'    raw=sys.stdin.buffer.read()\n'
                               b'    print(json.dumps({"payload":raw.decode(),"policy":'
                               b'sys._radio_native_v2_source_policy_preflight}))\n')
        self.freeze['code_sha256s']['scripts/radio_native_v2_fixture_helper.py'] = hashlib.sha256(
            self.helper.read_bytes()).hexdigest()
        self.refresh()
        plan = loader.prepare_helper_launch(self.root, self.freeze_path, self.sha,
                                             module='radio_native_v2_fixture_helper')
        self.addCleanup(lambda: __import__('shutil').rmtree(plan['startup_cache_prefix']))
        return plan

    def run_helper(self, plan, payload=b'bounded-command\npayload'):
        return subprocess.run([plan['executable'], *plan['args']], env=plan['env'], cwd=self.root,
                              input=payload, capture_output=True, timeout=30)

    def test_source_helper_preserves_stdin_and_returns_bound_component_proof(self):
        plan = self.prepare_fixture()
        result = self.run_helper(plan)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        record = json.loads(result.stdout)
        self.assertEqual(record['payload'], 'bounded-command\npayload')
        proof = record['policy']
        self.assertEqual(proof['mode'], 'LOCAL_HELPER_SOURCE_COMPONENT_ONLY')
        self.assertEqual(proof['helper_bootstrap_sha256'], plan['source_policy_sha256'])
        self.assertEqual(proof['entrypoint_sha256'], plan['source_loader_sha256'])
        self.assertEqual(proof['freeze_sha256'], plan['freeze_sha256'])
        self.assertTrue(proof['source_only_imports_verified'])
        self.assertFalse(plan['source_qualified'])
        self.assertTrue(all(proof[key] is False for key in loader.DISABLED))
        self.assertEqual(list(Path(plan['startup_cache_prefix']).rglob('*')), [])

    def test_source_helper_refuses_hostile_timestamp_pyc(self):
        plan = self.prepare_fixture()
        cache = Path(importlib.util.cache_from_source(str(self.helper)))
        cache.parent.mkdir()
        hostile = compile('raise AssertionError("untrusted pyc executed")\n', str(self.helper), 'exec')
        cache.write_bytes(import_external._code_to_timestamp_pyc(
            hostile, int(self.helper.stat().st_mtime), self.helper.stat().st_size))
        result = self.run_helper(plan)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        proof = json.loads(result.stdout)['policy']
        self.assertEqual(proof['source_inventory']['radio_native_v2_fixture_helper']['kind'],
                         'DIRECT_SOURCE_BYTES')

    def test_source_helper_uses_original_loader_buffer_after_path_replacement(self):
        plan = self.prepare_fixture()
        self.entry.write_bytes(b'raise AssertionError("untrusted replacement loader executed")\n')
        # File equality still fails before helper execution; the replacement
        # entrypoint source is never compiled or executed.
        result = self.run_helper(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Pinned source-loader entrypoint differs', result.stderr)
        self.assertNotIn(b'untrusted replacement loader executed', result.stderr)

    def test_source_helper_missing_source_or_wrong_bootstrap_buffer_refused(self):
        plan = self.prepare_fixture()
        self.helper.write_bytes(b'raise AssertionError("changed helper executed")\n')
        result = self.run_helper(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Frozen local dependency differs', result.stderr)
        self.assertNotIn(b'changed helper executed', result.stderr)


if __name__ == '__main__':
    unittest.main()
