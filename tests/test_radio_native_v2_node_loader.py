"""Real Node subprocess source-loader controls; no native cases, RNG or network."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from unittest.mock import patch

import radio_native_v2_node_loader as loader


class NodeLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = str(Path(os.environ.get('CODEX_PRIMARY_RUNTIME_NODE')
                            or shutil.which('node')).resolve())
        cls.git = str(Path(shutil.which('git')).resolve())
        cls.versions = json.loads(subprocess.check_output(
            [cls.node, '-p', 'JSON.stringify(process.versions)'], env={'LANG': 'C.UTF-8'}))
        cls.runtime = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                       for path in (cls.node, cls.git)}

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'scripts').mkdir()
        self.entry = self.root / loader.SELF
        self.entry.write_bytes(Path(loader.__file__).read_bytes())
        self.module = self.root / 'scripts/radio_native_v2_fixture.js'
        self.module.write_text("const path=require('node:path');module.exports={value:1};\n")
        self.freeze = {'mode': 'PROSPECTIVE_ENGINEERING_ONLY',
                       **{key: False for key in loader.DISABLED},
                       'runtime_sha256s': dict(self.runtime),
                       'code_sha256s': {},
                       'executables': {
                           'node': {'invocation': self.node, 'resolved': self.node,
                                    'sha256': self.runtime[self.node], 'version': self.versions},
                           'git': {'invocation': self.git, 'resolved': self.git,
                                   'sha256': self.runtime[self.git], 'version': 'unused'},
                       }}
        self.freeze_path = self.root / 'freeze.json'
        self.refresh()

    def refresh(self):
        self.freeze['code_sha256s'] = {str(path.relative_to(self.root)):
                                     hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in (self.entry, *self.root.glob('scripts/*.js'))}
        self.raw = json.dumps(self.freeze, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=True).encode()
        self.freeze_path.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()

    def launch(self, **kwargs):
        return loader.launch_preflight(self.root, self.freeze_path, self.sha,
                                       modules=('scripts/radio_native_v2_fixture.js',), **kwargs)

    def plan(self, **kwargs):
        return loader.prepare_launch(self.root, self.freeze_path, self.sha,
                                     modules=('scripts/radio_native_v2_fixture.js',), **kwargs)

    def run_plan(self, plan, input=None):
        return subprocess.run(plan['arguments'], cwd=plan['cwd'], env=plan['environment'],
                              input=input, capture_output=True, timeout=30)

    def test_real_node_preflight_uses_exact_buffers_and_no_authority(self):
        proof = self.launch()
        self.assertTrue(proof['source_buffers_hashed_before_compile'])
        self.assertTrue(proof['environment_isolated'])
        self.assertFalse(proof['stdin_consumed_by_bootstrap'])
        self.assertFalse(proof['public_freeze_verified'])
        self.assertFalse(proof['qualified_transport_execution'])
        self.assertFalse(proof['hostile_code_sandbox'])
        self.assertTrue(all(proof[key] is False for key in loader.DISABLED))
        self.assertEqual(proof['requested_builtins'], ['path'])
        self.assertEqual(proof['node_versions'], self.versions)
        self.assertEqual(proof['source_inventory']['scripts/radio_native_v2_fixture.js']['sha256'],
                         self.freeze['code_sha256s']['scripts/radio_native_v2_fixture.js'])

    def test_hostile_node_environment_and_preload_are_not_inherited(self):
        marker = self.root / 'hostile-ran'
        hostile = self.root / 'hostile.js'
        hostile.write_text("require('fs').writeFileSync("+json.dumps(str(marker))+",'ran');\n")
        with patch.dict(os.environ, {'NODE_OPTIONS': '--require '+str(hostile),
                                     'NODE_PATH': str(self.root), 'PATH': '/absent',
                                     'LD_PRELOAD': '/absent-hostile.so',
                                     'OPENSSL_CONF': str(hostile)}):
            proof = self.launch()
        self.assertTrue(proof['environment_isolated'])
        self.assertFalse(marker.exists())
        self.assertEqual(set(self.plan()['environment']), {'LANG', 'LC_ALL', 'TZ'})

    def test_relative_pinned_dependency_loads_exact_source(self):
        dependency = self.root / 'scripts/radio_native_v2_dependency.js'
        dependency.write_text("module.exports={value:17};\n")
        self.module.write_text("if(require('./radio_native_v2_dependency').value!==17)throw Error('bad source');\n")
        self.refresh()
        proof = self.launch()
        self.assertEqual(set(proof['source_inventory']),
                         {'scripts/radio_native_v2_fixture.js', 'scripts/radio_native_v2_dependency.js'})

    def test_path_mutation_after_prepare_uses_original_prehashed_buffer(self):
        plan = self.plan()
        marker = self.root / 'substituted-source-ran'
        self.module.write_text("require('fs').writeFileSync("+json.dumps(str(marker))+",'ran');\n")
        result = self.run_plan(plan)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertFalse(marker.exists())
        proof = json.loads(result.stdout)
        self.assertEqual(proof['source_inventory']['scripts/radio_native_v2_fixture.js']['sha256'],
                         self.freeze['code_sha256s']['scripts/radio_native_v2_fixture.js'])

    def test_corrupt_transferred_buffer_refused_before_compile(self):
        marker = self.root / 'corrupt-source-ran'
        plan = self.plan()
        plan['arguments'][-1] = base64.b64encode(
            ("require('fs').writeFileSync("+json.dumps(str(marker))+",'ran');").encode()).decode()
        result = self.run_plan(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Pinned Node source bytes differ', result.stderr)
        self.assertFalse(marker.exists())

    def test_unpinned_package_builtin_addon_and_global_bypass_refused(self):
        requests = ("require('fs-extra')", "require('node:module')", "require('node:vm')",
                    "require('./absent.node')", "globalThis.require('fs')",
                    "process.getBuiltinModule('module')", "process.dlopen({},'absent.node')")
        for request in requests:
            with self.subTest(request=request):
                self.module.write_text(request+';\n')
                self.refresh()
                with self.assertRaisesRegex(ValueError, 'refused|Only approved|absent from exact'):
                    self.launch()

    def test_dependency_omitted_from_buffers_refused_even_if_file_is_present(self):
        dependency = self.root / 'scripts/radio_native_v2_dependency.js'
        dependency.write_text("throw Error('Must never compile this dependency');\n")
        self.module.write_text("require('./radio_native_v2_dependency');\n")
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'absent from exact frozen source buffers'):
            self.launch(source_paths=('scripts/radio_native_v2_fixture.js',))

    def test_existing_unfrozen_global_node_modules_are_ignored(self):
        package = self.root / 'node_modules/unfrozen'
        package.mkdir(parents=True)
        marker = self.root / 'package-ran'
        (package / 'index.js').write_text("require('fs').writeFileSync("+json.dumps(str(marker))+",'ran');\n")
        self.module.write_text("require('unfrozen');\n")
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Only approved'):
            self.launch()
        self.assertFalse(marker.exists())

    def test_source_symlink_refused_before_child(self):
        outside = self.root / 'outside.js'
        outside.write_bytes(self.module.read_bytes())
        self.module.unlink()
        self.module.symlink_to(outside)
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'symlink/escape refused'):
            self.plan()

    def test_changed_runtime_and_node_or_git_executable_pins_refused(self):
        self.freeze['runtime_sha256s'][self.node] = '0' * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'runtime dependency differs'):
            self.plan()
        self.freeze['runtime_sha256s'][self.node] = self.runtime[self.node]
        self.freeze['executables']['git']['sha256'] = '0' * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Node/Git executable differs'):
            self.plan()

    def test_node_version_mismatch_refused_inside_real_child(self):
        self.freeze['executables']['node']['version'] = {**self.versions, 'node': '0.0.0'}
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Node version differs'):
            self.launch()

    def test_freeze_or_launcher_bytes_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, 'freeze bytes differ'):
            loader.prepare_launch(self.root, self.freeze_path, '0' * 64,
                                  modules=('scripts/radio_native_v2_fixture.js',))
        self.entry.write_text('raise AssertionError("untrusted launcher")\n')
        with self.assertRaisesRegex(ValueError, 'launcher source differs'):
            self.plan()

    def test_enabled_permission_refused_before_launch(self):
        self.freeze['rng_authorized'] = True
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'grants no authority'):
            self.plan()

    def test_stdin_available_and_operational_source_record_is_immutable(self):
        self.module.write_text("""module.exports.start=options=>{
 const fs=require('node:fs');
 const policy=globalThis.__radioNativeV2SourcePolicy;
 if(!Object.isFrozen(policy)||!Object.isFrozen(policy.source_inventory))throw Error('mutable policy');
 if(policy.source_buffers_hashed_before_compile!==true)throw Error('missing source policy');
 const input=fs.readFileSync(0,'utf8');
 process.stdout.write(JSON.stringify({input,options,policy})+'\\n');
};
""")
        self.refresh()
        plan = self.plan(entrypoint={'module': 'scripts/radio_native_v2_fixture.js',
                                     'export': 'start', 'options': {'fixture': True}})
        result = self.run_plan(plan, b'courier-input\n')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        record = json.loads(result.stdout)
        self.assertEqual(record['input'], 'courier-input\n')
        self.assertEqual(record['options'], {'fixture': True})
        self.assertEqual(record['policy']['schema'], loader.SCHEMA)
        self.assertFalse(record['policy']['execution_authorized'])

    def test_late_operational_import_is_pinned_and_new_snapshot_includes_it(self):
        dependency = self.root / 'scripts/radio_native_v2_dependency.js'
        dependency.write_text("module.exports={value:19};\n")
        self.module.write_text("""module.exports.start=()=>{
 const before=globalThis.__radioNativeV2SourcePolicy;
 const value=require('./radio_native_v2_dependency').value;
 const after=globalThis.__radioNativeV2SourcePolicy;
 process.stdout.write(JSON.stringify({before,after,value})+'\\n');
};
""")
        self.refresh()
        plan = self.plan(entrypoint={'module': 'scripts/radio_native_v2_fixture.js',
                                     'export': 'start', 'options': {}})
        result = self.run_plan(plan)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        record = json.loads(result.stdout)
        self.assertEqual(record['value'], 19)
        self.assertNotIn('scripts/radio_native_v2_dependency.js', record['before']['source_inventory'])
        self.assertIn('scripts/radio_native_v2_dependency.js', record['after']['source_inventory'])
        self.assertIn('scripts/radio_native_v2_dependency.js', record['before']['available_source_buffer_inventory'])

    def test_pinned_node_file_hash_git_and_source_only_python_spawn_work(self):
        import radio_native_v2_source_loader as python_loader
        stdlib = Path(sysconfig.get_path('stdlib'))
        self.freeze['runtime_sha256s'].update({str(path.resolve()):
            hashlib.sha256(path.read_bytes()).hexdigest() for path in stdlib.rglob('*.py')
            if 'site-packages' not in path.relative_to(stdlib).parts and '__pycache__' not in path.parts})
        python = str(Path(sys.executable).resolve())
        python_sha = hashlib.sha256(Path(python).read_bytes()).hexdigest()
        self.freeze['runtime_sha256s'][python] = python_sha
        self.freeze['executables']['python'] = {
            'invocation': sys.executable, 'resolved': python, 'sha256': python_sha, 'version': sys.version}
        source_loader_path = self.root / python_loader.SELF
        source_loader_path.write_bytes(Path(python_loader.__file__).read_bytes())
        helper = self.root / 'scripts/radio_native_v2_fixture_helper.py'
        helper.write_bytes(b'import json\nimport sys\n'
                           b'def main():\n'
                           b'    raw=sys.stdin.buffer.read()\n'
                           b'    print(json.dumps({"payload":raw.decode(),"policy":'
                           b'sys._radio_native_v2_source_policy_preflight}))\n')
        self.refresh()
        self.freeze['code_sha256s'][python_loader.SELF] = hashlib.sha256(source_loader_path.read_bytes()).hexdigest()
        self.freeze['code_sha256s']['scripts/radio_native_v2_fixture_helper.py'] = hashlib.sha256(helper.read_bytes()).hexdigest()
        self.raw = json.dumps(self.freeze, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.freeze_path.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()
        helper_plan = python_loader.prepare_helper_launch(self.root, self.freeze_path, self.sha,
                                                          module='radio_native_v2_fixture_helper')
        self.addCleanup(lambda: shutil.rmtree(helper_plan['startup_cache_prefix']))
        self.module.write_text("""module.exports.start=options=>{
 const cp=require('node:child_process'),fs=require('node:fs'),crypto=require('node:crypto');
 const git=cp.spawnSync(options.git,['--version'],{env:options.plan.env});
 if(git.status!==0||git.stderr.length)throw Error('pinned Git spawn failed');
 const child=cp.spawnSync(options.plan.executable,options.plan.args,
   {env:options.plan.env,input:Buffer.from('local-only-command'),maxBuffer:1024*1024});
 if(child.status!==0||child.stderr.length)throw Error('pinned Python spawn failed: '+child.stderr);
 const raw=fs.readFileSync(options.file),digest=crypto.createHash('sha256').update(raw).digest('hex');
 process.stdout.write(JSON.stringify({git:git.stdout.toString(),child:JSON.parse(child.stdout),digest})+'\\n');
};
""")
        # The helper freeze must pin the final caller module as well.
        self.freeze['code_sha256s']['scripts/radio_native_v2_fixture.js'] = hashlib.sha256(self.module.read_bytes()).hexdigest()
        self.raw = json.dumps(self.freeze, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.freeze_path.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()
        shutil.rmtree(helper_plan['startup_cache_prefix'])
        # Reuse the cleanup path only after re-creating it through the launcher.
        cache = helper_plan['startup_cache_prefix']
        Path(cache).mkdir(mode=0o700)
        helper_plan = python_loader.prepare_helper_launch(self.root, self.freeze_path, self.sha,
                                                          module='radio_native_v2_fixture_helper',cache_prefix=cache)
        plan = self.plan(entrypoint={'module': 'scripts/radio_native_v2_fixture.js', 'export': 'start',
                                    'options': {'git': self.git, 'plan': helper_plan, 'file': str(helper)}})
        result = self.run_plan(plan)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        record = json.loads(result.stdout)
        self.assertTrue(record['git'].startswith('git version '))
        self.assertEqual(record['digest'], hashlib.sha256(helper.read_bytes()).hexdigest())
        self.assertEqual(record['child']['payload'], 'local-only-command')
        self.assertTrue(record['child']['policy']['source_only_imports_verified'])
        self.assertEqual(record['child']['policy']['freeze_sha256'], self.sha)

    def test_extra_node_preload_argument_refused(self):
        plan = self.plan()
        plan['arguments'].insert(1, '--trace-warnings')
        result = self.run_plan(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'preload/extra executable arguments refused', result.stderr)

    def test_large_source_buffer_refused_before_child(self):
        self.module.write_bytes(b'//' + b'x' * loader.MAX_SOURCE_BYTES)
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'buffer cap'):
            self.plan()


if __name__ == '__main__':
    unittest.main()
