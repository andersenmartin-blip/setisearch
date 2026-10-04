"""Disjoint tiny synthetic process tests; no live GitHub calls or credentials."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('fresh_hosted_cas_supervisor', Path(__file__).with_name('supervisor.py'))
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='radio-supervisor-synthetic-')
        self.root = Path(self.temporary.name)
        self.source = self.root / 'synthetic-child.py'
        self.source.write_text('import os\nos.write(1,b"complete\\x00stdout")\nos.write(2,b"exact\\xffstderr")\n')
        self.output = self.root / 'fresh-output'
        self.proof = self.root / 'gate-proof.json'
        self.sources = frozenset(('synthetic-child.py',))
        self.bind()

    def tearDown(self):
        self.temporary.cleanup()

    def bind(self):
        raw = self.source.read_bytes()
        rows = [{'path': 'synthetic-child.py', 'bytes': len(raw),
                 'sha256': hashlib.sha256(raw).hexdigest()}]
        freeze = {'schema': 'radio-hosted-cas-control-freeze-v1',
            'namespace': supervisor.NAMESPACE, 'repository': supervisor.REPOSITORY,
            'branch': supervisor.BRANCH, 'source_files': rows, 'limits': {'synthetic': True}}
        folder = self.root / 'config'
        folder.mkdir(exist_ok=True)
        freeze_raw = supervisor.canonical(freeze)
        (folder / 'radio_hosted_cas_control_20261004a.freeze.json').write_bytes(freeze_raw)
        proof = {'schema': 'radio-hosted-cas-control-activation-proof-v1',
            'repository': supervisor.REPOSITORY, 'branch': supervisor.BRANCH,
            'namespace': supervisor.NAMESPACE, 'activation': 'a' * 40,
            'preparation': 'b' * 40, 'manifest_sha256': hashlib.sha256(freeze_raw).hexdigest(),
            'run_id': '123', 'source_files': rows}
        self.proof.write_bytes(supervisor.canonical(proof))

    def run_child(self, *, environment=None, limits=None):
        values = {'child_seconds': 1.5, 'reap_seconds': 1.0,
                  'sample_seconds': 0.01, 'metadata_reserve': 65536}
        values.update(limits or {})
        return supervisor.supervise(self.output, self.proof,
            repository_root=self.root, injected_command=[sys.executable, '-I', '-B', str(self.source)],
            synthetic_environment=environment or {}, expected_sources=self.sources,
            limits=values, runtime_paths=[Path(sys.executable).resolve()])

    def terminal(self):
        return json.loads((self.output / 'terminal.json').read_bytes())

    def outcome(self):
        return json.loads((self.output / 'supervisor-outcome.json').read_bytes())

    def test_full_binary_streams_reaping_and_selected_runtime(self):
        self.assertEqual(self.run_child(), 0)
        self.assertEqual((self.output / 'stdout.bin').read_bytes(), b'complete\x00stdout')
        self.assertEqual((self.output / 'stderr.bin').read_bytes(), b'exact\xffstderr')
        terminal = self.terminal()
        self.assertTrue(terminal['direct_child_reaped'])
        self.assertEqual(terminal['direct_child']['exit_code'], 0)
        self.assertGreater(terminal['direct_child']['wait4_max_rss_bytes'], 0)
        self.assertTrue(terminal['selected_runtime_before_after_match'])
        self.assertFalse(terminal['scientific_authority'])
        self.assertTrue(terminal['procfs']['sampled_RSS_is_not_complete_peak_or_enforced_kernel_limit'])
        self.assertEqual(self.outcome()['status'], 'COMPONENT_OBSERVED')

    def test_nonzero_preserves_complete_exact_failure(self):
        self.source.write_text('import os\nos.write(2,b"failed\\x00exact")\nraise SystemExit(7)\n')
        self.bind()
        self.assertEqual(self.run_child(), 7)
        self.assertEqual((self.output / 'stderr.bin').read_bytes(), b'failed\x00exact')
        self.assertEqual(self.terminal()['direct_child']['exit_code'], 7)
        self.assertTrue(self.terminal()['streams']['stderr']['full_retained'])
        self.assertEqual(self.outcome()['status'], 'CLOSED_FAILED')

    def test_whole_child_timeout_reaps_and_retains_partial_stream(self):
        self.source.write_text('import os,time\nos.write(1,b"started")\ntime.sleep(10)\n')
        self.bind()
        self.assertNotEqual(self.run_child(limits={'child_seconds': 0.15}), 0)
        terminal = self.terminal()
        self.assertEqual(terminal['failure'], 'whole_child_deadline')
        self.assertTrue(terminal['direct_child_reaped'])
        self.assertLess(terminal['whole_child_elapsed_seconds'], 1.15)
        self.assertEqual((self.output / 'stdout.bin').read_bytes(), b'started')

    def test_stream_limit_retains_exact_bounded_prefix(self):
        self.source.write_text('import os,time\nos.write(1,b"a"*200)\ntime.sleep(10)\n')
        self.bind()
        self.assertNotEqual(self.run_child(limits={'stream_bytes': 64, 'combined_bytes': 128}), 0)
        self.assertEqual((self.output / 'stdout.bin').read_bytes(), b'a' * 64)
        terminal = self.terminal()
        self.assertEqual(terminal['failure'], 'raw_stream_limit')
        self.assertFalse(terminal['streams']['stdout']['full_retained'])
        self.assertTrue(terminal['direct_child_reaped'])

    def test_combined_stream_limit(self):
        self.source.write_text('import os,time\nos.write(1,b"a"*50)\nos.write(2,b"b"*50)\ntime.sleep(10)\n')
        self.bind()
        self.assertNotEqual(self.run_child(limits={'stream_bytes': 64, 'combined_bytes': 80}), 0)
        terminal = self.terminal()
        self.assertEqual(sum(row['bytes'] for row in terminal['streams'].values()), 80)
        self.assertEqual(terminal['failure'], 'raw_stream_limit')

    def test_inherited_environment_not_passed(self):
        self.source.write_text('import os\nassert "UNRELATED_PARENT_SECRET" not in os.environ\nassert "PYTHONPATH" not in os.environ\nassert os.environ["SELECTED"]=="value"\n')
        self.bind()
        with mock.patch.dict(os.environ, {'UNRELATED_PARENT_SECRET': 'never-record-this', 'PYTHONPATH': '/bad/path'}):
            self.assertEqual(self.run_child(environment={'SELECTED': 'value'}), 0)
        payload = b''.join(path.read_bytes() for path in self.output.rglob('*') if path.is_file())
        self.assertNotIn(b'never-record-this', payload)
        self.assertNotIn(b'/bad/path', payload)

    def test_occupied_scope_refused_without_second_launch(self):
        self.assertEqual(self.run_child(), 0)
        before = (self.output / 'terminal.json').read_bytes()
        with self.assertRaises(ValueError):
            self.run_child()
        self.assertEqual((self.output / 'terminal.json').read_bytes(), before)

    def test_invalid_proof_or_source_refused_before_claim(self):
        self.source.write_text('raise SystemExit(0)\n')
        with self.assertRaises(ValueError):
            self.run_child()
        self.assertFalse(self.output.exists())

    def test_changed_freeze_refused_before_claim(self):
        path = self.root / 'config/radio_hosted_cas_control_20261004a.freeze.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.run_child()
        self.assertFalse(self.output.exists())

    def test_duplicate_proof_keys_refused(self):
        raw = self.proof.read_text().strip()
        self.proof.write_text(raw[:-1] + ',"run_id":"123"}')
        with self.assertRaises(ValueError):
            self.run_child()
        self.assertFalse(self.output.exists())

    def test_symlink_input_and_destination_refused(self):
        link = self.root / 'proof-link'
        link.symlink_to(self.proof)
        with self.assertRaises(ValueError):
            supervisor.supervise(self.output, link, repository_root=self.root)
        self.output.symlink_to(self.root / 'uncreated')
        with self.assertRaises(ValueError):
            self.run_child()

    def test_child_symlink_member_closes_failed(self):
        self.source.write_text('from pathlib import Path\nimport time\nPath("fresh-output/bad-link").symlink_to("/tmp")\ntime.sleep(10)\n')
        self.bind()
        self.assertNotEqual(self.run_child(), 0)
        self.assertEqual(self.outcome()['status'], 'CLOSED_FAILED')
        self.assertTrue(self.terminal()['direct_child_reaped'])
        self.assertTrue((self.output / 'bad-link').is_symlink())

    def test_storage_includes_directory_allocations_and_closes_on_limit(self):
        self.source.write_text('from pathlib import Path\nimport time\nPath("fresh-output/large.bin").write_bytes(b"x"*200000)\ntime.sleep(10)\n')
        self.bind()
        self.assertNotEqual(self.run_child(limits={'storage_bytes': 160000, 'metadata_reserve': 32768}), 0)
        self.assertTrue((self.output / 'large.bin').exists())
        self.assertTrue(self.terminal()['direct_child_reaped'])
        self.assertEqual(self.outcome()['failure'], 'retained_storage_limit')

    def test_source_change_during_child_is_failure(self):
        self.source.write_text('from pathlib import Path\np=Path(__file__)\np.write_text("changed source\\n")\n')
        self.bind()
        self.assertNotEqual(self.run_child(), 0)
        self.assertEqual(self.outcome()['failure'], 'source_or_selected_runtime_readback_failed')
        self.assertFalse(self.terminal()['selected_sources_before_after_match'])

    def test_descendant_sampling_and_orphan_reaping(self):
        self.source.write_text('import subprocess,time\nsubprocess.Popen(["/bin/sleep","10"])\ntime.sleep(.2)\n')
        self.bind()
        self.assertNotEqual(self.run_child(), 0)
        terminal = self.terminal()
        self.assertGreaterEqual(len(terminal['procfs']['individual_process_peaks']), 2)
        self.assertEqual(terminal['failure'], 'descendants_survived_direct_child')
        self.assertGreaterEqual(len(terminal['wait4_dispositions']), 2)
        self.assertTrue(terminal['direct_child_reaped'])

    def test_bad_synthetic_limits_and_live_credential_refused(self):
        with self.assertRaises(ValueError):
            self.run_child(limits={'child_seconds': 200})
        with self.assertRaises(ValueError):
            self.run_child(environment={'GITHUB_TOKEN': 'not-a-live-token'})
        self.assertFalse(self.output.exists())

    def test_child_environment_matches_only_selected_metadata(self):
        proof = json.loads(self.proof.read_bytes())
        environment = {'GITHUB_SHA': proof['activation'],
            'GITHUB_REPOSITORY': supervisor.REPOSITORY,
            'GITHUB_REF': 'refs/heads/' + supervisor.BRANCH,
            'GITHUB_EVENT_NAME': 'push', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_RUN_ID': proof['run_id'], 'GITHUB_TOKEN': 'test-placeholder',
            'GITHUB_WORKFLOW_REF': supervisor.REPOSITORY + '/.github/workflows/radio_hosted_cas_control_20261004a.yml@refs/heads/' + supervisor.BRANCH,
            'UNRELATED': 'never-included', 'PYTHONPATH': '/bad'}
        with mock.patch.dict(os.environ, environment, clear=True):
            selected = supervisor.child_environment(proof)
            self.assertEqual(set(selected), set(supervisor.GHA_KEYS) | {'GITHUB_TOKEN', 'PATH', 'LC_ALL', 'TZ'})
            self.assertNotIn('UNRELATED', selected)
            os.environ['GITHUB_RUN_ATTEMPT'] = '2'
            with self.assertRaises(ValueError):
                supervisor.child_environment(proof)


if __name__ == '__main__':
    unittest.main()
