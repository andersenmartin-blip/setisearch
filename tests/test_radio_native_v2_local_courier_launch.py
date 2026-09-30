"""Real pinned controller/helper launch controls in a closed harmless fixture."""
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
from unittest import mock

import radio_native_v2_local_courier_launch as courier_launcher
import radio_native_v2_node_loader as node_loader
import radio_native_v2_source_loader as source_loader


class LocalCourierLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = str(Path(os.environ.get('CODEX_PRIMARY_RUNTIME_NODE')
                            or shutil.which('node')).resolve())
        cls.git = str(Path(shutil.which('git')).resolve())
        cls.python = str(Path(sys.executable).resolve())
        cls.runtime = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                       for path in (cls.node, cls.git, cls.python)}
        stdlib = Path(sysconfig.get_path('stdlib'))
        cls.runtime.update({str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in stdlib.rglob('*.py')
                            if 'site-packages' not in path.relative_to(stdlib).parts
                            and '__pycache__' not in path.parts})
        cls.versions = json.loads(subprocess.check_output(
            [cls.node, '-p', 'JSON.stringify(process.versions)'], env={'LANG': 'C.UTF-8'}))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'scripts').mkdir()
        self.driver = self.root / 'scripts/radio_native_v2_local_courier.js'
        self.driver.write_text("""'use strict';
module.exports.main=options=>{
 const fs=require('node:fs'),cp=require('node:child_process');
 const raw=fs.readFileSync(0,'utf8');
 const helper=cp.spawnSync(options.helperLaunch.executable,options.helperLaunch.args,
   {env:options.helperLaunch.env,input:raw,maxBuffer:1024*1024});
 if(helper.status!==0||helper.stderr.length)throw Error('source helper failed: '+helper.stderr);
 process.stdout.write(JSON.stringify({options,stdin:raw,helper:JSON.parse(helper.stdout),
   source_policy:globalThis.__radioNativeV2SourcePolicy})+'\\n');
};
""")
        for name in ('local_worker', 'local_transport', 'local_git', 'broker_host'):
            (self.root / ('scripts/radio_native_v2_'+name+'.js')).write_text('module.exports={};\n')
        for module in (node_loader, source_loader, courier_launcher):
            (self.root / 'scripts' / Path(module.__file__).name).write_bytes(Path(module.__file__).read_bytes())
        (self.root / 'scripts/radio_native_v2_local_worker_helper.py').write_bytes(
            b'import json\nimport sys\n'
            b'def main():\n'
            b'    raw=sys.stdin.buffer.read()\n'
            b'    print(json.dumps({"input":raw.decode(),"source_loader_preflight":'
            b'sys._radio_native_v2_source_policy_preflight}))\n')
        self.freeze = {'mode': 'PROSPECTIVE_ENGINEERING_ONLY',
                       **{key: False for key in node_loader.DISABLED},
                       'runtime_sha256s': dict(self.runtime),
                       'code_sha256s': {str(path.relative_to(self.root)):
                                      hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in self.root.glob('scripts/*')},
                       'executables': {
                           'python': {'invocation': sys.executable, 'resolved': self.python,
                                      'sha256': self.runtime[self.python], 'version': sys.version},
                           'node': {'invocation': self.node, 'resolved': self.node,
                                    'sha256': self.runtime[self.node], 'version': self.versions},
                           'git': {'invocation': self.git, 'resolved': self.git,
                                   'sha256': self.runtime[self.git], 'version': 'unused'},
                       }}
        self.freeze_path = self.root / 'freeze.json'
        raw = json.dumps(self.freeze, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.freeze_path.write_bytes(raw)
        self.freeze_sha = hashlib.sha256(raw).hexdigest()
        self.config = {'fixture_namespace': 'results_radio_native_v2_local_transport_20260930a/live01',
                       'cases': 1, 'root': str(self.root), 'python': sys.executable,
                       'gitPath': self.git, 'storeRoot': str(self.root / 'store'),
                       'start_arguments_template': {'cmd': 'fixed-prospective-fixture-start __CONFIG_SHA256__',
                                                    'max_output_tokens': 400000,
                                                    'yield_time_ms': 1000, 'tty': True}}
        self.config_path = self.root / 'config.json'
        self.refresh_config()

    def refresh_config(self):
        raw = json.dumps(self.config, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.config_path.write_bytes(raw)
        self.config_sha = hashlib.sha256(raw).hexdigest()

    def prepare(self):
        plan = courier_launcher.prepare(self.root, self.freeze_path, self.freeze_sha,
                                        self.config_path, self.config_sha)
        configuration = json.loads(plan['arguments'][3])
        helper = configuration['entrypoint']['options']['helperLaunch']
        cache = helper['startup_cache_prefix']
        self.addCleanup(lambda: shutil.rmtree(cache))
        return plan, configuration, helper

    def test_real_combined_launch_preserves_stdin_and_exact_helper_source_policy(self):
        plan, configuration, helper = self.prepare()
        self.assertLessEqual(max(len(argument.encode()) for argument in plan['arguments']),
                             node_loader.MAX_ARGUMENT_BYTES)
        self.assertEqual(len(configuration['source_paths']), 5)
        result = subprocess.run(plan['arguments'], cwd=plan['cwd'], env=plan['environment'],
                                input=b'exact-small-command\n', capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        record = json.loads(result.stdout)
        startup = json.loads(record['options']['startRequest'])
        self.assertEqual(startup['tool'], 'exec_command')
        self.assertEqual(startup['arguments']['cmd'],
                         'fixed-prospective-fixture-start '+self.config_sha)
        self.assertNotIn('start_arguments_template', record['options'])
        self.assertEqual(record['stdin'], 'exact-small-command\n')
        self.assertEqual(record['helper']['input'], record['stdin'])
        proof = record['helper']['source_loader_preflight']
        self.assertEqual(proof['freeze_sha256'], self.freeze_sha)
        self.assertEqual(proof['entrypoint_sha256'], helper['source_loader_sha256'])
        self.assertEqual(proof['helper_bootstrap_sha256'], helper['source_policy_sha256'])
        self.assertTrue(proof['source_only_imports_verified'])
        self.assertEqual(record['source_policy']['freeze_sha256'], self.freeze_sha)
        self.assertTrue(all(proof[key] is False for key in node_loader.DISABLED))
        self.assertTrue(all(record['source_policy'][key] is False for key in node_loader.DISABLED))
        self.assertEqual(list(Path(helper['startup_cache_prefix']).rglob('*')), [])

    def test_wrong_config_hash_refused_before_helper_cache_creation(self):
        with self.assertRaisesRegex(ValueError, 'Bounded exact prospective controller configuration required'):
            courier_launcher.prepare(self.root, self.freeze_path, self.freeze_sha,
                                     self.config_path, '0' * 64)

    def test_case_or_namespace_expansion_refused(self):
        for key, value in (('cases', 8), ('fixture_namespace', 'unreserved-other-scope'),
                           ('root', '/elsewhere')):
            with self.subTest(key=key):
                original = self.config[key]
                self.config[key] = value
                self.refresh_config()
                with self.assertRaisesRegex(ValueError, 'fixed single-case prospective fixture'):
                    self.prepare()
                self.config[key] = original
                self.refresh_config()

    def network_options(self):
        (self.root / 'config').mkdir()
        certificate = b'harmless fixed test certificate\n'
        (self.root / courier_launcher.CA_PATH).write_bytes(certificate)
        policy = {'schema': courier_launcher.NETWORK_SCHEMA, 'repository': 'andersenmartin-blip/setisearch',
                  'operation': 'git_fetch', 'proxy_policy': dict(courier_launcher.PROXY_POLICY),
                  'tls_ca': {'path': courier_launcher.CA_PATH, 'bytes': len(certificate),
                             'sha256': hashlib.sha256(certificate).hexdigest()},
                  'automatic_retry': False, 'execution_authorized': False,
                  'reservation_authorized': False, 'scientific_execution_authorized': False}
        policy_path = self.root / 'config/radio_native_v2_local_git_network_20260930.json'
        raw = json.dumps(policy, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        policy_path.write_bytes(raw)
        self.config.update(gitNetworkConfigPath=str(policy_path),
                           gitNetworkConfigSha256=hashlib.sha256(raw).hexdigest())
        self.refresh_config()
        return policy_path

    def test_current_proxy_is_selected_once_and_no_other_environment_is_injected(self):
        self.network_options()
        for endpoint in ('http://127.0.0.1:12345', 'http://127.0.0.1:54321'):
            with self.subTest(endpoint=endpoint), mock.patch.dict(os.environ, {
                    'HTTPS_PROXY': endpoint, 'HTTP_PROXY': 'http://elsewhere.invalid:8888',
                    'ALL_PROXY': 'socks5h://elsewhere.invalid:9999', 'GIT_SSL_NO_VERIFY': '1'}):
                plan, configuration, _ = self.prepare()
                options = configuration['entrypoint']['options']
                self.assertEqual(options['gitNetworkRuntimeProxy'], endpoint)
                self.assertFalse(any('PROXY' in key or key == 'GIT_SSL_NO_VERIFY'
                                     for key in plan['environment']))
                self.assertFalse(any(key in options for key in ('HTTP_PROXY', 'ALL_PROXY', 'GIT_SSL_NO_VERIFY')))

    def test_network_proxy_and_certificate_must_match_policy_before_launch(self):
        policy = self.network_options()
        for endpoint in ('http://user:pass@127.0.0.1:12345', 'http://localhost:12345',
                         'http://127.0.0.1:65536', 'http://127.0.0.1:12345/',
                         'http://127.0.0.1:12345?x=1', 'socks5h://127.0.0.1:12345'):
            with self.subTest(endpoint=endpoint), mock.patch.dict(os.environ, {'HTTPS_PROXY': endpoint}):
                with self.assertRaisesRegex(ValueError, 'exact loopback'):
                    self.prepare()
        with mock.patch.dict(os.environ, {'HTTPS_PROXY': 'http://127.0.0.1:12345'}):
            ca = self.root / courier_launcher.CA_PATH
            ca.write_bytes(b'drifted')
            with self.assertRaisesRegex(ValueError, 'sole network input|drifted'):
                self.prepare()
        self.assertTrue(policy.exists())

    def test_fixed_config_cannot_supply_stale_runtime_proxy(self):
        self.network_options()
        self.config['gitNetworkRuntimeProxy'] = 'http://127.0.0.1:12345'
        self.refresh_config()
        with self.assertRaisesRegex(ValueError, 'this launcher environment'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
