"""Tiny filesystem refusal/readback fixtures, no original E or data generation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('public_lossless_reconstruct_v2.py')
SPEC = importlib.util.spec_from_file_location('offline_decoder_v2', SOURCE)
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


class OutputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='offline-v2-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / 'repo'
        self.case = self.repo / decoder.SCOPE_NAME / 'cases' / 'case00'
        self.case.mkdir(parents=True)
        self.private = self.repo / '.private-journal'
        self.private.mkdir()
        (self.private / 'original').write_bytes(b'unchanged private fixture')
        self.recipe = self.case / 'original-recipe.py'
        self.recipe.write_bytes(b'# original recipe is never executed\n')
        self.prepared = self.case / 'prepared.json'
        metadata = {'schema': 'radio-native-v2-offline-maximum-prepared-v1',
            'control_case_identity': {'namespace': decoder.NAMESPACE, 'case_ordinal': 0,
                'source_case_id': decoder.NAMESPACE + '/case00',
                'native_case_binding_verified': False, 'source_sha256': '1' * 64},
            'scope': str(self.case), 'python': '/fixture/unused-python',
            'source_bytes': decoder.SOURCE_BYTES}
        self.prepared.write_bytes(decoder.canonical(metadata))
        self.arguments = {'prepared': str(self.prepared),
            'prepared_sha256': hashlib.sha256(self.prepared.read_bytes()).hexdigest(),
            'original_recipe': str(self.recipe),
            'original_recipe_sha256': hashlib.sha256(self.recipe.read_bytes()).hexdigest(),
            'original_repository_root': str(self.repo)}

    def refused_before_counter(self, output, **changes):
        original_private = (self.private / 'original').read_bytes()
        with mock.patch.object(decoder, 'counter_bytes', side_effect=AssertionError('data reconstruction reached')) as counter:
            with self.assertRaises((ValueError, OSError)):
                decoder.reconstruct(**{**self.arguments, 'output_root': str(output), **changes})
            self.assertEqual(counter.call_count, 0)
        self.assertEqual((self.private / 'original').read_bytes(), original_private)

    def open_output(self, name='output'):
        output = decoder.OutputRoot(str(self.base / name), str(self.repo), {})
        self.addCleanup(output.close)
        return output

    def test_entire_repository_and_private_descendants_refused_before_counter(self):
        for destination in (self.repo, self.repo / 'new', self.case / 'new', self.private / 'new'):
            with self.subTest(destination=destination):
                self.refused_before_counter(destination)
                if destination.name == 'new':
                    self.assertFalse(destination.exists())

    def test_noncanonical_outputs_refused_before_counter(self):
        for destination in ('relative', str(self.base) + '/../alias', str(self.base) + '//alias', str(self.base) + '/a\\b'):
            with self.subTest(destination=destination):
                self.refused_before_counter(destination)

    def test_existing_and_symlink_roots_refused_without_content_change(self):
        destination = self.base / 'existing'
        destination.mkdir()
        (destination / 'keep').write_bytes(b'keep')
        self.refused_before_counter(destination)
        self.assertEqual((destination / 'keep').read_bytes(), b'keep')
        alias = self.base / 'alias'
        alias.symlink_to(self.private, target_is_directory=True)
        self.refused_before_counter(alias)
        self.assertEqual(sorted(path.name for path in self.private.iterdir()), ['original'])

    def test_symlink_ancestors_to_protected_or_outside_tree_refused(self):
        outside = self.base / 'outside'
        outside.mkdir()
        for target, label in ((self.repo, 'protected-alias'), (outside, 'outside-alias')):
            alias = self.base / label
            alias.symlink_to(target, target_is_directory=True)
            self.refused_before_counter(alias / 'new')
            self.assertFalse((target / 'new').exists())

    def test_physical_directory_alias_identity_refused_before_root_creation(self):
        parent = self.base / 'physical-alias-parent'
        parent.mkdir()
        info = parent.stat()
        with mock.patch.object(decoder, 'protected_directory_identities', return_value={(info.st_dev, info.st_ino)}):
            self.refused_before_counter(parent / 'new')
        self.assertFalse((parent / 'new').exists())

    def test_independent_repository_root_mismatch_refused_before_counter(self):
        wrong = self.base / 'wrong-repository'
        wrong.mkdir()
        self.refused_before_counter(self.base / 'fresh', original_repository_root=str(wrong))

    def test_metadata_symlink_and_hardlink_refused_before_counter(self):
        alias = self.case / 'symlink-prepared.json'
        alias.symlink_to(self.prepared)
        self.refused_before_counter(self.base / 'fresh', prepared=str(alias))
        hardlink = self.case / 'hardlink-prepared.json'
        os.link(self.prepared, hardlink)
        self.refused_before_counter(self.base / 'fresh')

    def test_held_parent_replacement_refused_before_mkdir(self):
        parent = self.base / 'parent'
        parent.mkdir()
        output = decoder.OutputRoot(str(parent / 'fresh'), str(self.repo), {})
        self.addCleanup(output.close)
        parent.rename(self.base / 'old-parent')
        parent.mkdir()
        with self.assertRaisesRegex(ValueError, 'ancestry changed'):
            output.create()
        self.assertFalse((parent / 'fresh').exists())
        self.assertFalse((self.base / 'old-parent/fresh').exists())

    def test_owner_only_bounded_output_and_terminal_readback(self):
        output = self.open_output()
        output.create()
        output.write('deterministic-source.bin', b'tiny test bytes')
        output.finish()
        self.assertEqual((self.base / 'output').stat().st_mode & 0o777, 0o700)
        file = self.base / 'output/deterministic-source.bin'
        self.assertEqual(file.stat().st_mode & 0o777, 0o400)
        self.assertEqual(file.stat().st_uid, os.geteuid())
        self.assertEqual(file.stat().st_nlink, 1)

    def test_changed_output_root_mode_refused_before_file_write(self):
        output = self.open_output()
        output.create()
        os.chmod(self.base / 'output', 0o755)
        with self.assertRaisesRegex(ValueError, 'ownership changed'):
            output.write('deterministic-source.bin', b'tiny')
        self.assertFalse((self.base / 'output/deterministic-source.bin').exists())

    def test_fixed_names_existing_files_bounds_and_unknown_entries_refused(self):
        output = self.open_output()
        output.create()
        with self.assertRaisesRegex(ValueError, 'fixed offline output'):
            output.write('../escape', b'tiny')
        with self.assertRaisesRegex(ValueError, 'fixed offline output'):
            output.write('offline-reconstruction.json', b'x' * (decoder.MAX_RECEIPT_BYTES + 1))
        existing = self.base / 'output/deterministic-source.bin'
        existing.write_bytes(b'not overwritten')
        with self.assertRaises(FileExistsError):
            output.write('deterministic-source.bin', b'tiny')
        self.assertEqual(existing.read_bytes(), b'not overwritten')
        with self.assertRaisesRegex(ValueError, 'Unknown entry'):
            output.finish()

    def test_hardlinked_written_file_and_same_length_content_change_refused(self):
        output = self.open_output()
        output.create()
        output.write('deterministic-source.bin', b'tiny')
        file = self.base / 'output/deterministic-source.bin'
        alias = self.base / 'hardlink-output'
        os.link(file, alias)
        with self.assertRaisesRegex(ValueError, 'Sole-link regular'):
            output.finish()
        alias.unlink()
        os.chmod(file, 0o600)
        file.write_bytes(b'else')
        os.chmod(file, 0o400)
        with self.assertRaisesRegex(ValueError, 'identity/content changed'):
            output.finish()


if __name__ == '__main__':
    unittest.main()
