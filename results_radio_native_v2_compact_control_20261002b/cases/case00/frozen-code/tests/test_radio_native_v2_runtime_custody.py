import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

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

    @unittest.skipUnless(os.environ.get('RUN_RUNTIME_CUSTODY_HOST_AUDIT') == '1', 'Explicit host-wide audit only; default tests use tiny files')
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

    def test_same_byte_sole_link_replacement_is_refused_with_preserved_mtime_and_mode(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            expected=M.build_manifest(**args); before=material.stat(); raw=material.read_bytes()
            held=os.open(material,os.O_RDONLY)
            try:
                material.unlink(); material.write_bytes(raw); os.chmod(material,before.st_mode&0o7777)
                os.utime(material,ns=(before.st_atime_ns,before.st_mtime_ns))
                self.assertNotEqual(material.stat().st_ino,before.st_ino)
                with self.assertRaisesRegex(ValueError,'Material runtime custody'):
                    M.validate_material_runtime(expected,expected_manifest_sha256=M.manifest_sha256(expected))
            finally: os.close(held)

    def test_whole_git_group_recreated_same_bytes_and_topology_is_refused(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            expected=M.build_manifest(**args); before=git.stat(); raw=git.read_bytes(); held=os.open(git,os.O_RDONLY)
            try:
                helper.unlink(); git.unlink(); git.write_bytes(raw); helper.hardlink_to(git)
                os.chmod(git,before.st_mode&0o7777); os.utime(git,ns=(before.st_atime_ns,before.st_mtime_ns))
                self.assertEqual(git.stat().st_nlink,2); self.assertNotEqual(git.stat().st_ino,before.st_ino)
                with self.assertRaisesRegex(ValueError,'manifest differs'): M.validate_manifest(expected,**args)
            finally: os.close(held)

    def test_material_only_check_never_opens_git_or_enumerates_roots(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            expected=M.build_manifest(**args); helper.unlink(); git.unlink()
            original=M._observe; opened=[]
            def observe(path,**kwargs): opened.append(str(path)); return original(path,**kwargs)
            with mock.patch.object(M,'_observe',side_effect=observe),mock.patch.object(M.os,'scandir',side_effect=AssertionError('No activation root scan')):
                receipt=M.validate_material_runtime(expected,expected_manifest_sha256=M.manifest_sha256(expected))
            self.assertEqual(opened,[str(material)])
            self.assertEqual(receipt['activation_only_runtime_paths_opened'],0)
            self.assertFalse(receipt['complete_runtime_topology_rechecked'])
            self.assertFalse(receipt['execution_authorized'])

    def test_duplicate_spellings_and_symlink_ancestors_cannot_close_hidden_alias(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            helper.unlink(); (root/'hidden').hardlink_to(git)
            for alias in (args['alias_roots'][0]+'/.',args['alias_roots'][0]+'/',args['alias_roots'][0].replace('/','//',1)):
                changed=copy.deepcopy(args); changed['alias_roots']=sorted([args['alias_roots'][0],alias])
                with self.subTest(alias=alias),self.assertRaises(ValueError): M.build_manifest(**changed)
            link=root/'ancestor-alias'; link.symlink_to(root/'bin',target_is_directory=True)
            with self.assertRaises(OSError): M.read_material_pin(str(link/'git'))

    def test_bounded_inventory_rejects_alias_fifo_hardlink_and_cardinality(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'good.py').write_bytes(b'x')
            self.assertEqual(M.bounded_inventory(str(root),suffixes={'.py'}),[str(root/'good.py')])
            for kind in ('symlink','fifo','hardlink'):
                bad=root/'bad.py'
                if kind=='symlink': bad.symlink_to(root/'good.py')
                elif kind=='fifo': os.mkfifo(bad)
                else: bad.hardlink_to(root/'good.py')
                with self.subTest(kind=kind),self.assertRaises(ValueError): M.bounded_inventory(str(root),suffixes={'.py'})
                bad.unlink()
            (root/'extra.py').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'inventory exceeded'): M.bounded_inventory(str(root),maximum=1)

    def test_hash_mutation_alias_stat_race_and_stale_manifest_sha_refused(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            expected=M.build_manifest(**args)
            with self.assertRaisesRegex(ValueError,'manifest SHA'):
                M.validate_material_runtime(expected,expected_manifest_sha256='0'*64)
            original=M.os.pread; changed=[False]
            def mutate(fd,amount,offset):
                data=original(fd,amount,offset)
                if not changed[0]:
                    changed[0]=True; material.write_bytes(b'changed-during-pread')
                return data
            with mock.patch.object(M.os,'pread',side_effect=mutate),self.assertRaises(ValueError): M._pin(material)

    def test_alias_substitution_between_lstat_and_open_is_refused(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            original=M._observe; changed=[False]
            def swap(path,**kwargs):
                if kwargs.get('expected_identity') is not None and str(path)==str(helper) and not changed[0]:
                    changed[0]=True; helper.unlink(); helper.write_bytes(git.read_bytes())
                return original(path,**kwargs)
            with mock.patch.object(M,'_observe',side_effect=swap),self.assertRaisesRegex(ValueError,'enumerated inode|identity changed'):
                M.build_manifest(**args)

    def test_strict_metadata_types_group_membership_and_authority_are_not_self_attested(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            expected=M.build_manifest(**args)
            for key,value in (('nlink',True),('bytes',float(expected['runtime_files'][str(material)]['bytes'])),('mode',True)):
                changed=copy.deepcopy(expected); changed['runtime_files'][str(material)][key]=value
                with self.subTest(key=key),self.assertRaises(ValueError): M.validate_manifest_structure(changed,**args)
            changed=copy.deepcopy(expected); changed['activation_only_paths'].append(str(material)); changed['activation_only_paths'].sort()
            with self.assertRaisesRegex(ValueError,'lifecycle/root policy'): M.validate_manifest_structure(changed,**args)
            changed=copy.deepcopy(expected); changed['execution_authorized']=0
            with self.assertRaisesRegex(ValueError,'cannot grant authority'): M.validate_manifest_structure(changed,**args)

    def test_held_hardlink_inode_is_hashed_once_not_once_per_alias(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            original=M.os.pread; calls=[]
            def count(fd,amount,offset): calls.append(os.fstat(fd).st_ino); return original(fd,amount,offset)
            with mock.patch.object(M.os,'pread',side_effect=count): M.build_manifest(**args)
            self.assertEqual(calls.count(git.stat().st_ino),1)

    def test_last_material_recheck_cannot_leave_earlier_git_group_stale(self):
        temporary,root,git,helper,material,args=self.fixture()
        with temporary:
            original=M._observe; seen=[0]
            def add_late_alias(path,**kwargs):
                observed=original(path,**kwargs)
                if str(path)==str(material):
                    seen[0]+=1
                    if seen[0]==2: (root/'hidden-late-alias').hardlink_to(git)
                return observed
            with mock.patch.object(M,'_observe',side_effect=add_late_alias),self.assertRaisesRegex(ValueError,'after final inventory recheck'):
                M.build_manifest(**args)


if __name__ == '__main__':
    unittest.main()
