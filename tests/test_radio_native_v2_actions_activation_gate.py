import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'activation_gate', ROOT / 'scripts/radio_native_v2_actions_activation_gate.py')
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class ActivationGateTests(unittest.TestCase):
    def prepare(self, root):
        def run(*args):
            return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        run('init', '-q')
        run('config', 'user.name', 'Engineering fixture')
        run('config', 'user.email', 'engineering@example.invalid')
        files = []
        for relative in sorted(GATE.REQUIRED_FILES):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixed engineering fixture\n')
            data = path.read_bytes()
            files.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'namespace': GATE.NAMESPACE, 'files': files,
                    **{key: False for key in GATE.DISABLED}}
        raw = (json.dumps(manifest, sort_keys=True) + '\n').encode()
        (root / GATE.MANIFEST).write_bytes(raw)
        run('add', '.')
        run('commit', '-qm', 'Preparation')
        preparation = run('rev-parse', 'HEAD')
        manifest_sha = hashlib.sha256(raw).hexdigest()
        marker = {'namespace': GATE.NAMESPACE, 'activate': True,
                  'preparation_commit': preparation, 'manifest_sha256': manifest_sha,
                  'independent_readback': {'commit': preparation, 'verified': True,
                                           'manifest_sha256': manifest_sha, 'files': files},
                  **{key: False for key in GATE.DISABLED}}
        (root / GATE.MARKER).write_text(json.dumps(marker) + '\n')
        run('add', GATE.MARKER)
        run('commit', '-qm', 'Single marker activation')
        environment = {'GITHUB_REPOSITORY': GATE.REPOSITORY,
                       'GITHUB_REF': 'refs/heads/' + GATE.BRANCH,
                       'GITHUB_EVENT_NAME': 'push', 'GITHUB_RUN_ATTEMPT': '1',
                       'GITHUB_SHA': run('rev-parse', 'HEAD')}
        return environment, run

    def test_exact_marker_only_activation_and_no_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            environment, _ = self.prepare(Path(directory))
            result = GATE.verify(directory, environment)
            self.assertTrue(result['verified'])
            self.assertTrue(all(result[key] is False for key in GATE.DISABLED))

    def test_rerun_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            environment, _ = self.prepare(Path(directory))
            environment['GITHUB_RUN_ATTEMPT'] = '2'
            with self.assertRaises(ValueError):
                GATE.verify(directory, environment)

    def test_modified_preparation_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment, _ = self.prepare(root)
            (root / sorted(GATE.REQUIRED_FILES)[0]).write_text('changed\n')
            with self.assertRaises(ValueError):
                GATE.verify(root, environment)

    def test_marker_republication_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment, run = self.prepare(root)
            (root / GATE.MARKER).write_text((root / GATE.MARKER).read_text() + ' ')
            run('add', GATE.MARKER)
            run('commit', '-qm', 'Attempt reuse')
            environment['GITHUB_SHA'] = run('rev-parse', 'HEAD')
            with self.assertRaises(ValueError):
                GATE.verify(root, environment)


if __name__ == '__main__':
    unittest.main()
