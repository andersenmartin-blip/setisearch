"""Tiny synthetic metadata/source fixtures; no protected invocation or data."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/radio_native_v3_public_source_proof.py'
spec = importlib.util.spec_from_file_location('public_source_proof', SOURCE)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_object(kind, data):
    return hashlib.sha1(kind.encode('ascii') + b' ' + str(len(data)).encode('ascii')
                        + b'\0' + data).hexdigest()


def recursive_tree(files):
    """Construct small real Git object metadata, including complete ancestors."""
    entries = {path: {'path': path, 'mode': '100644', 'type': 'blob',
                      'sha': git_object('blob', data), 'size': len(data)}
               for path, data in files.items()}
    return finish_tree(entries)


def finish_tree(entries):
    entries = copy.deepcopy(entries)
    directories = {''}
    for path in list(entries):
        parent = str(Path(path).parent)
        while parent != '.':
            directories.add(parent)
            parent = str(Path(parent).parent)
    tree_sha = {}
    for directory in sorted(directories, key=lambda value: (value.count('/'), len(value)), reverse=True):
        direct = [entry for path, entry in entries.items()
                  if (path.rsplit('/', 1)[0] if '/' in path else '') == directory]
        direct.sort(key=lambda entry: entry['path'].rsplit('/', 1)[-1].encode()
                    + (b'/' if entry['type'] == 'tree' else b''))
        body = b''
        for entry in direct:
            body += (entry['mode'].lstrip('0').encode('ascii') + b' '
                     + entry['path'].rsplit('/', 1)[-1].encode() + b'\0'
                     + bytes.fromhex(entry['sha']))
        tree_sha[directory] = git_object('tree', body)
        if directory:
            entries[directory] = {'path': directory, 'mode': '040000', 'type': 'tree',
                                  'sha': tree_sha[directory]}
    return {'sha': tree_sha[''], 'truncated': False,
            'tree': [entries[path] for path in sorted(entries)]}


class PublicSourceProofTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='public-source-proof-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        self.files = {'scripts/control.py': b'print("metadata-only")\n',
                      'config/input.json': b'{"synthetic":true}\n'}
        for path, data in self.files.items():
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        self.freeze = {'schema': proof.FREEZE_SCHEMA,
                       'freeze_kind': 'COMPLETE_RUNNER_BROKER_RUNTIME',
                       'mode': 'PROSPECTIVE_ENGINEERING_ONLY',
                       **{field: False for field in proof.AUTHORITY_FIELDS},
                       'transport_qualification': None,
                       'repository_code_inventory': ['scripts/control.py'],
                       'code_sha256s': {'scripts/control.py': sha256(self.files['scripts/control.py'])},
                       'input_file_inventory': ['config/input.json'],
                       'input_sha256s': {'config/input.json': sha256(self.files['config/input.json'])}}
        self.tree = recursive_tree(self.files)
        self.commit = {'sha': '1' * 40, 'tree': {'sha': self.tree['sha']}}

    def arguments(self, *, freeze_raw=None, tree_raw=None, commit_raw=None):
        paths = {}
        for name, value, raw in (('freeze', self.freeze, freeze_raw),
                                 ('commit_readback', self.commit, commit_raw),
                                 ('tree_readback', self.tree, tree_raw)):
            data = json.dumps(value, sort_keys=True).encode() if raw is None else raw
            path = self.base / (name + '.json')
            path.write_bytes(data)
            paths[name + '_path'] = str(path)
            paths[name + '_sha256'] = sha256(data)
        return {'root': str(self.root), **paths,
                'expected_commit': self.commit['sha'], 'expected_tree': self.tree['sha'],
                'expected_code_count': len(self.freeze['repository_code_inventory']),
                'expected_input_count': len(self.freeze['input_file_inventory']),
                'expected_unique_count': len(set(self.freeze['code_sha256s'])
                                             | set(self.freeze['input_sha256s']))}

    def run_proof(self, **kwargs):
        return proof.prove_source_bytes(**self.arguments(**kwargs))

    def refuse(self, substring, **kwargs):
        with self.assertRaisesRegex((ValueError, OSError), substring):
            self.run_proof(**kwargs)

    def rehash_tree(self, entries):
        self.tree = finish_tree(entries)
        self.commit['tree']['sha'] = self.tree['sha']

    def test_valid_proof_binds_every_frozen_path_without_authority(self):
        result = self.run_proof()
        self.assertEqual(result['status'], 'PASS_SELECTED_FROZEN_BYTE_EQUIVALENCE')
        self.assertEqual(result['selected_unique_path_count'], 2)
        self.assertEqual(result['canonical_git_tree_objects_verified'], 3)
        self.assertEqual(result['selected_logical_bytes'], sum(map(len, self.files.values())))
        self.assertEqual({row['path'] for row in result['files']}, set(self.files))
        self.assertTrue(result['all_selected_frozen_paths_equal'])
        for field in ('scientific_execution_authorized', 'transport_integration_qualified',
                      'complete_runtime_freeze_validated', 'scientific_source_certificate_validated',
                      'all_public_blobs_individually_http_downloaded'):
            self.assertIs(result[field], False)
        self.assertEqual(result['project_module_imports'], 0)

    def test_unselected_blob_contents_are_never_read(self):
        # Its public metadata is present, but its local pathname does not exist.
        self.tree = recursive_tree({**self.files, 'unopened/observation.h5': b'not fetched'})
        self.commit['tree']['sha'] = self.tree['sha']
        result = self.run_proof()
        self.assertEqual(result['selected_unique_path_count'], 2)
        self.assertEqual(result['unselected_public_blob_content_reads'], 0)

    def test_truncated_or_nonboolean_tree_refused(self):
        for value in (True, None, 0):
            with self.subTest(value=value):
                self.tree['truncated'] = value
                self.refuse('complete immutable recursive Git tree')

    def test_duplicate_tree_paths_refused(self):
        self.tree['tree'].append(copy.deepcopy(self.tree['tree'][0]))
        self.refuse('Duplicate recursive Git tree path')

    def test_missing_selected_public_path_refused(self):
        self.tree = recursive_tree({'scripts/control.py': self.files['scripts/control.py']})
        self.commit['tree']['sha'] = self.tree['sha']
        self.refuse('Frozen path missing')

    def test_missing_ancestor_and_false_root_sha_refused(self):
        original = copy.deepcopy(self.tree)
        self.tree['tree'] = [entry for entry in self.tree['tree'] if entry['path'] != 'config']
        self.refuse('recursive Git ancestry')
        self.tree = original
        self.tree['tree'][0]['sha'] = '2' * 40
        self.refuse('Canonical Git tree object hash differs')

    def test_public_symlink_submodule_and_directory_selected_paths_refused(self):
        original = copy.deepcopy(self.tree)
        for mode, kind in (('120000', 'blob'), ('160000', 'commit'), ('040000', 'tree')):
            with self.subTest(mode=mode):
                entries = {entry['path']: entry for entry in original['tree']}
                entry = entries['scripts/control.py']
                entry['mode'], entry['type'] = mode, kind
                if kind == 'tree':
                    entry.pop('size')
                    entry['sha'] = git_object('tree', b'')
                self.rehash_tree(entries)
                self.refuse('Frozen public path must be a regular Git blob')

    def test_unsafe_selected_and_public_paths_refused(self):
        for path in ('../outside.py', '/absolute.py', 'scripts//x.py', 'scripts/./x.py',
                     'scripts/x\\y.py', 'scripts/x\x00.py'):
            with self.subTest(path=path):
                original = copy.deepcopy(self.freeze)
                self.freeze['repository_code_inventory'] = [path]
                self.freeze['code_sha256s'] = {path: '0' * 64}
                self.refuse('Canonical repository-relative path')
                self.freeze = original
        self.tree['tree'].append({'path': '../unselected', 'type': 'blob',
                                  'mode': '100644', 'sha': '0' * 40, 'size': 0})
        self.refuse('Canonical repository-relative path')

    def test_local_symlink_and_ancestor_symlink_refused(self):
        path = self.root / 'scripts/control.py'
        moved = self.base / 'outside.py'
        path.rename(moved)
        path.symlink_to(moved)
        self.refuse('Too many levels of symbolic links')
        path.unlink()
        moved.rename(path)
        folder = self.root / 'scripts'
        outside_folder = self.base / 'outside-scripts'
        folder.rename(outside_folder)
        folder.symlink_to(outside_folder, target_is_directory=True)
        self.refuse('Not a directory|Too many levels')

    def test_hardlink_and_nonregular_local_paths_refused(self):
        source = self.root / 'scripts/control.py'
        os.link(source, self.base / 'aliased.py')
        self.refuse('Sole-link regular file')
        (self.base / 'aliased.py').unlink()
        source.unlink()
        os.mkfifo(source)
        self.refuse('Sole-link regular file')

    def test_wrong_local_sha256_blob_sha_and_public_size_refused(self):
        original = copy.deepcopy(self.freeze)
        self.freeze['code_sha256s']['scripts/control.py'] = '0' * 64
        self.refuse('Local SHA256 differs from freeze')
        self.freeze = original
        entries = {entry['path']: entry for entry in self.tree['tree']}
        entries['scripts/control.py']['sha'] = '2' * 40
        self.rehash_tree(entries)
        self.refuse('canonical Git blob SHA differs')
        entries['scripts/control.py']['sha'] = git_object('blob', self.files['scripts/control.py'])
        entries['scripts/control.py']['size'] += 1
        self.rehash_tree(entries)
        self.refuse('byte length differs from public tree')

    def test_inventory_duplicates_and_map_joins_refused(self):
        self.freeze['repository_code_inventory'].append('scripts/control.py')
        self.refuse('Exact sorted inventory/hash-map join')
        self.freeze['repository_code_inventory'] = []
        self.refuse('Exact sorted inventory/hash-map join')

    def test_independent_counts_and_conflicting_overlap_refused(self):
        arguments = self.arguments()
        for field in ('expected_code_count', 'expected_input_count', 'expected_unique_count'):
            with self.subTest(field=field):
                changed = {**arguments, field: arguments[field] + 1}
                with self.assertRaisesRegex(ValueError, 'pinned .*count differs'):
                    proof.prove_source_bytes(**changed)
        self.freeze['input_sha256s']['scripts/control.py'] = '0' * 64
        self.freeze['input_file_inventory'] = sorted(self.freeze['input_sha256s'])
        self.refuse('Overlapping code/input identities conflict')

    def test_consistent_overlap_reads_one_unique_file_and_git_directory_sort(self):
        self.freeze['input_sha256s']['scripts/control.py'] = self.freeze['code_sha256s']['scripts/control.py']
        self.freeze['input_file_inventory'] = sorted(self.freeze['input_sha256s'])
        # Git sorts a directory named foo after the file foo.bar.
        self.tree = recursive_tree({**self.files, 'foo/bar': b'a', 'foo.bar': b'b', 'foo0': b'c'})
        self.commit['tree']['sha'] = self.tree['sha']
        result = self.run_proof()
        self.assertEqual(result['shared_code_input_path_count'], 1)
        self.assertEqual(result['input_path_count'], 2)
        self.assertEqual(result['selected_unique_path_count'], 2)

    def test_mutation_between_selected_reads_refused(self):
        original_read = proof._read_file
        def changing_read(path, directories, expected_signature=None, **kwargs):
            result = original_read(path, directories, expected_signature, **kwargs)
            if path == str(self.root / 'config/input.json'):
                (self.root / 'scripts/control.py').write_bytes(b'changed\n')
            return result
        with mock.patch.object(proof, '_read_file', side_effect=changing_read):
            self.refuse('File changed before read')

    def test_mutation_of_already_read_file_refused_by_common_window(self):
        original_read = proof._read_file
        def changing_read(path, directories, expected_signature=None, **kwargs):
            result = original_read(path, directories, expected_signature, **kwargs)
            if path == str(self.root / 'scripts/control.py'):
                (self.root / 'config/input.json').write_bytes(b'{"changed":true}\n')
            return result
        with mock.patch.object(proof, '_read_file', side_effect=changing_read):
            self.refuse('common observation window')

    def test_mutation_during_read_refused(self):
        arguments = self.arguments()
        source = self.root / 'scripts/control.py'
        wanted_inode = source.stat().st_ino
        original_read = os.read
        changed = False
        def changing_read(descriptor, count):
            nonlocal changed
            block = original_read(descriptor, count)
            if os.fstat(descriptor).st_ino == wanted_inode and block and not changed:
                changed = True
                source.write_bytes(self.files['scripts/control.py'])
            return block
        with mock.patch.object(proof.os, 'read', side_effect=changing_read):
            with self.assertRaisesRegex(ValueError, 'changed during read'):
                proof.prove_source_bytes(**arguments)

    def test_metadata_hash_commit_tree_pin_and_duplicate_json_keys_refused(self):
        arguments = self.arguments()
        for field in ('freeze_sha256', 'commit_readback_sha256', 'tree_readback_sha256'):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'Raw metadata SHA256 differs'):
                    proof.prove_source_bytes(**{**arguments, field: '0' * 64})
        with self.assertRaisesRegex(ValueError, 'commit/tree readback differs'):
            proof.prove_source_bytes(**{**arguments, 'expected_commit': '2' * 40})
        with self.assertRaisesRegex(ValueError, 'commit/tree readback differs'):
            proof.prove_source_bytes(**{**arguments, 'expected_tree': '2' * 40})
        raw = json.dumps(self.tree).encode()
        raw = b'{"sha":"' + self.tree['sha'].encode() + b'",' + raw[1:]
        self.refuse('Duplicate JSON object key', tree_raw=raw)

    def test_authority_relative_root_and_duplicate_metadata_paths_refused(self):
        self.freeze['scientific_execution_authorized'] = True
        self.refuse('Freeze cannot confer execution')
        self.freeze['scientific_execution_authorized'] = False
        arguments = self.arguments()
        with self.assertRaisesRegex(ValueError, 'Strict canonical absolute path'):
            proof.prove_source_bytes(**{**arguments, 'root': 'relative'})
        with self.assertRaisesRegex(ValueError, 'Distinct freeze/commit/tree metadata'):
            proof.prove_source_bytes(**{**arguments, 'commit_readback_path': arguments['freeze_path']})

    def test_cli_requires_external_pins_and_prints_only_bounded_proof(self):
        arguments = self.arguments()
        flags = []
        for key, value in arguments.items():
            key = {'freeze_path': 'freeze', 'commit_readback_path': 'commit-readback',
                   'tree_readback_path': 'tree-readback'}.get(key, key.replace('_', '-'))
            flags += ['--' + key, str(value)]
        with mock.patch('sys.stdout') as stdout:
            self.assertEqual(proof.main(flags), 0)
        result = json.loads(stdout.write.call_args.args[0])
        self.assertEqual(result['selected_unique_path_count'], 2)
        self.assertNotIn('print("metadata-only")', stdout.write.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
