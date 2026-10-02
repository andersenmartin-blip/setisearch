import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('runtime_custody',
    ROOT / 'scripts/radio_native_v2_runtime_custody.py')
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class RuntimeCustodyTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(); root = Path(temporary.name)
        bin_root = root / 'bin'; core_root = root / 'core'
        bin_root.mkdir(); core_root.mkdir()
        git = bin_root / 'git'; git.write_bytes(b'git-runtime')
        helper = core_root / 'git-helper'; helper.hardlink_to(git)
        material = root / 'python'; material.write_bytes(b'material-runtime')
        paths = sorted(map(str, (git, helper, material)))
        hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (git, helper, material)}
        args = {'runtime_paths': paths, 'runtime_sha256s': hashes,
            'activation_only_paths': sorted(map(str, (git, helper))),
            'alias_roots': sorted(map(str, (bin_root, core_root)))}
        return temporary, root, git, helper, material, args

    def test_exact_closed_group_and_sole_link_material_pass(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            manifest = M.build_manifest(**args)
            self.assertTrue(M.validate_manifest(manifest, **args))
            self.assertEqual(manifest['hardlinked_inventory_paths'], 2)
            self.assertEqual(manifest['hardlink_alias_closure_paths'], 2)
            self.assertTrue(manifest['material_runtime_sole_link_verified'])

    def test_hidden_alias_outside_roots_is_refused(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            (root / 'hidden').hardlink_to(git)
            with self.assertRaisesRegex(ValueError, 'hidden or missing aliases'):
                M.build_manifest(**args)

    def test_unexpected_material_hardlink_is_refused(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            alias = root / 'material-alias'; alias.hardlink_to(material)
            with self.assertRaisesRegex(ValueError, 'must be sole-link'):
                M.build_manifest(**args)

    def test_added_alias_changes_frozen_manifest(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            expected = M.build_manifest(**args)
            extra = Path(args['alias_roots'][0]) / 'git-extra'; extra.hardlink_to(git)
            with self.assertRaisesRegex(ValueError, 'manifest differs'):
                M.validate_manifest(expected, **args)

    def test_relinked_same_bytes_changes_frozen_manifest(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            expected = M.build_manifest(**args)
            helper.unlink(); helper.write_bytes(git.read_bytes())
            args['runtime_sha256s'][str(helper)] = hashlib.sha256(helper.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'manifest differs'):
                M.validate_manifest(expected, **args)

    def test_hash_drift_is_refused(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            material.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                M.build_manifest(**args)

    def test_symlink_runtime_is_refused(self):
        temporary, root, git, helper, material, args = self.fixture()
        with temporary:
            link = root / 'link'; link.symlink_to(material)
            args['runtime_paths'] = sorted(args['runtime_paths'] + [str(link)])
            args['runtime_sha256s'][str(link)] = hashlib.sha256(material.read_bytes()).hexdigest()
            with self.assertRaises(OSError):
                M.build_manifest(**args)

    def test_current_freeze_matches_bounded_protocol_audit(self):
        freeze = json.loads((ROOT / 'config/radio_native_v2_activation_environment_20261002d.runtime.json').read_bytes())
        activation = sorted(set(freeze['git_runtime_file_inventory'])
            | {freeze['executables']['git']['resolved']})
        manifest = M.build_manifest(runtime_paths=freeze['runtime_file_inventory'],
            runtime_sha256s=freeze['runtime_sha256s'],
            activation_only_paths=activation,
            alias_roots=['/usr/local/bin', '/usr/local/libexec/git-core'])
        self.assertEqual(manifest['runtime_inventory_paths'], 1366)
        self.assertEqual(manifest['hardlinked_inventory_paths'], 151)
        self.assertEqual(manifest['hardlink_alias_closure_paths'], 157)
        self.assertEqual(len(manifest['hardlink_groups']), 6)
        self.assertTrue(manifest['material_runtime_sole_link_verified'])


if __name__ == '__main__':
    unittest.main()
