"""New activation tests in disposable synthetic local Git repositories only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import activation_gate as gate


class Fixture:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='synthetic-gate-')
        self.temp = Path(self.temporary.name)
        self.root = self.temp / 'checkout'; self.root.mkdir()
        self.git('init', '-q')
        self.git('symbolic-ref', 'HEAD', 'refs/heads/' + gate.BRANCH)
        self.rows = []
        for path in gate.SOURCES:
            raw = ('synthetic source only: ' + path + '\n').encode()
            self.write(path, raw)
            self.rows.append({'path': path, 'bytes': len(raw),
                              'sha256': hashlib.sha256(raw).hexdigest()})
        self.manifest = {'schema': 'radio-hosted-cas-control-freeze-v1',
                         'namespace': gate.NAMESPACE, 'repository': gate.REPOSITORY,
                         'branch': gate.BRANCH, 'source_files': self.rows,
                         'limits': copy.deepcopy(gate.LIMITS)}
        self.marker = {'schema': 'radio-hosted-cas-control-activation-v1',
                       'namespace': gate.NAMESPACE, 'repository': gate.REPOSITORY,
                       'branch': gate.BRANCH, 'preparation': '0' * 40,
                       'manifest_sha256': '0' * 64,
                       'source_readback_sha256': '0' * 64,
                       'allocation': copy.deepcopy(gate.ALLOCATION)}
        self.environment = {'GITHUB_REPOSITORY': gate.REPOSITORY,
                            'GITHUB_REF': 'refs/heads/' + gate.BRANCH,
                            'GITHUB_EVENT_NAME': 'push', 'GITHUB_RUN_ATTEMPT': '1',
                            'GITHUB_SHA': '0' * 40, 'GITHUB_RUN_ID': '123456'}

    def git(self, *args):
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('GIT_')}
        environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                           GIT_CONFIG_SYSTEM='/dev/null')
        result = subprocess.run(['git', '-c', 'user.name=Synthetic fixture',
                                 '-c', 'user.email=fixture@example.invalid',
                                 '-C', str(self.root), *args], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, timeout=10)
        return result.stdout.decode().strip()

    def write(self, path, raw):
        target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def prepare(self):
        raw = gate.canonical(self.manifest) + b'\n'
        self.write(gate.MANIFEST, raw)
        self.git('add', '.'); self.git('commit', '-qm', 'Synthetic preparation')
        self.preparation = self.git('rev-parse', 'HEAD')
        self.marker['preparation'] = self.preparation
        self.marker['manifest_sha256'] = hashlib.sha256(raw).hexdigest()
        self.marker['source_readback_sha256'] = hashlib.sha256(
            gate.canonical(self.manifest['source_files'])).hexdigest()

    def activate(self, raw=None):
        self.write(gate.MARKER, raw if raw is not None else gate.canonical(self.marker) + b'\n')
        self.git('add', '.'); self.git('commit', '-qm', 'Synthetic marker activation')
        self.activation = self.git('rev-parse', 'HEAD')
        self.environment['GITHUB_SHA'] = self.activation

    def verify(self):
        return gate.verify(self.root, self.environment)


class ActivationGateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture(); self.addCleanup(self.fixture.temporary.cleanup)

    def test_exact_first_attempt_and_proof_shape(self):
        f = self.fixture; f.prepare(); f.activate(); proof = f.verify()
        self.assertEqual(proof, {'schema': 'radio-hosted-cas-control-activation-proof-v1',
                                'repository': gate.REPOSITORY, 'branch': gate.BRANCH,
                                'namespace': gate.NAMESPACE, 'activation': f.activation,
                                'preparation': f.preparation,
                                'manifest_sha256': f.marker['manifest_sha256'],
                                'run_id': '123456', 'source_files': f.rows})
        self.assertNotIn('scientific_execution_authorized', proof)

    def test_wrong_context_or_repeated_attempt(self):
        f = self.fixture; f.prepare(); f.activate()
        for key, value in (('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_REF', 'refs/heads/main'),
                           ('GITHUB_EVENT_NAME', 'workflow_dispatch'), ('GITHUB_RUN_ATTEMPT', '2'),
                           ('GITHUB_RUN_ID', '0123'), ('GITHUB_SHA', 'A' * 40)):
            with self.subTest(key=key):
                changed = dict(f.environment); changed[key] = value
                with self.assertRaises(ValueError):
                    gate.verify(f.root, changed)

    def test_wrong_head(self):
        f = self.fixture; f.prepare(); f.activate(); f.environment['GITHUB_SHA'] = f.preparation
        with self.assertRaises(ValueError):
            f.verify()

    def test_marker_extra_field_and_allocation_boolean(self):
        f = self.fixture; f.prepare(); f.marker['scientific_execution_authorized'] = True; f.activate()
        with self.assertRaises(ValueError):
            f.verify()
        del f.marker['scientific_execution_authorized']; f.marker['allocation']['attempts'] = True
        f.write(gate.MARKER, gate.canonical(f.marker))
        with self.assertRaises(ValueError):
            f.verify()

    def test_marker_duplicate_json_field(self):
        f = self.fixture; f.prepare()
        raw = gate.canonical(f.marker)
        f.activate(b'{"schema":"duplicate",' + raw[1:])
        with self.assertRaises(ValueError):
            f.verify()

    def test_wrong_manifest_digest(self):
        f = self.fixture; f.prepare(); f.marker['manifest_sha256'] = 'f' * 64; f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_wrong_source_readback_digest(self):
        f = self.fixture; f.prepare(); f.marker['source_readback_sha256'] = 'f' * 64; f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_source_set_and_order_strict(self):
        f = self.fixture; f.manifest['source_files'] = list(reversed(f.rows)); f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_manifest_extra_fields_and_original_limits(self):
        f = self.fixture; f.manifest['limits']['control_api_calls'] = 41; f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_duplicate_source_and_bad_length(self):
        f = self.fixture; f.manifest['source_files'][0]['bytes'] = True; f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_source_local_tamper(self):
        f = self.fixture; f.prepare(); f.activate(); f.write(gate.SOURCES[0], b'changed')
        with self.assertRaises(ValueError):
            f.verify()

    def test_source_git_executable_mode(self):
        f = self.fixture
        os.chmod(f.root / gate.SOURCES[0], 0o755)
        f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_marker_must_be_sole_addition(self):
        f = self.fixture; f.prepare(); f.write('unselected.txt', b'extra'); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_marker_was_already_in_preparation(self):
        f = self.fixture; f.write(gate.MARKER, b'old'); f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_preexisting_runtime_state(self):
        f = self.fixture; f.write(gate.PREFIX + '/service-state.json', b'{}'); f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_preexisting_claim_or_terminal_state(self):
        f = self.fixture; f.write(gate.PREFIX + '/claims/claimed.json', b'{}'); f.prepare(); f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_selected_source_symlink(self):
        f = self.fixture; f.prepare(); f.activate()
        selected = f.root / gate.SOURCES[0]; original = selected.read_bytes()
        selected.unlink(); target = f.temp / 'source-copy'; target.write_bytes(original)
        selected.symlink_to(target)
        with self.assertRaises(ValueError):
            f.verify()

    def test_wrong_or_multiple_parent(self):
        f = self.fixture; f.prepare(); f.marker['preparation'] = 'f' * 40; f.activate()
        with self.assertRaises(ValueError):
            f.verify()

    def test_persistence_exclusive_and_fsynced(self):
        f = self.fixture; f.prepare(); f.activate(); proof = f.verify()
        output = f.temp / 'activation-proof.json'
        gate.persist(proof, output, root=f.root, runner_temp=f.temp)
        self.assertEqual(json.loads(output.read_bytes()), proof)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            gate.persist(proof, output, root=f.root, runner_temp=f.temp)
        with self.assertRaises(ValueError):
            gate.persist(proof, f.root / 'proof.json', root=f.root, runner_temp=f.temp)

    def test_development_log_is_not_runtime_state(self):
        f = self.fixture; f.write(gate.PREFIX + '/gate-development-tests01.log', b'synthetic log')
        f.prepare(); f.activate(); self.assertEqual(f.verify()['preparation'], f.preparation)


if __name__ == '__main__':
    unittest.main()
