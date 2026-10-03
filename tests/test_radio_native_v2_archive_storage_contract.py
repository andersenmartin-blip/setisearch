"""Inert adversarial tests; only temporary metadata-copy roots are observed."""
import copy
import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import radio_native_v2_archive_storage_contract as archive
import radio_native_v2_historical_storage as storage


def pin(value):
    raw = storage.canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def metadata(path):
    info = path.lstat()
    return {'device': info.st_dev, 'inode': info.st_ino,
        'mode': stat.S_IMODE(info.st_mode), 'nlink': info.st_nlink,
        'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
        'allocated_bytes': info.st_blocks * 512,
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def observe(root):
    rows = []
    for path in sorted([root, *root.rglob('*')],
            key=lambda item: item.relative_to(root).as_posix()):
        row = {'path': path.relative_to(root).as_posix(),
            'kind': 'directory' if path.is_dir() else 'file', 'metadata': metadata(path)}
        if row['kind'] == 'file':
            raw = path.read_bytes()
            row['raw_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    manifest = {'schema': storage.MANIFEST_SCHEMA, 'role': 'historical_scope',
        'scope': str(root), 'rows': rows}
    return storage.observe_retained_scope(str(root), manifest, expected_manifest_pin=pin(manifest))


class ArchiveStorageContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='seti-archive-copy-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.roots = {}; self.observations = {}; self.files = {}; self.pins = {}
        for label in archive.LABELS:
            root = self.root / (label + '-metadata-copy'); root.mkdir()
            (root / 'evidence').mkdir()
            (root / 'evidence' / 'receipt.json').write_bytes(b'{"copy":"' + label.encode() + b'"}\n')
            (root / 'public-spend-record-copy.json').write_bytes(b'{"public_copy":true}\n')
            self.roots[label] = str(root)
            value = observe(root); self.observations[label] = value; self.pins[label] = pin(value)
            self.files[label] = {row['path'][len(str(root)) + 1:]: row['raw_pin'].copy()
                for row in value['rows'] if row['kind'] == 'file'}

    def join(self, observations=None, *, roots=None, files=None, pins=None):
        return archive.join_archival_metadata_storage(
            self.observations if observations is None else observations,
            expected_archive_roots=self.roots if roots is None else roots,
            expected_file_pins=self.files if files is None else files,
            expected_observation_pins=self.pins if pins is None else pins)

    def repinned(self, changed):
        return {label: pin(changed[label]) for label in archive.LABELS}

    def test_exact_current_copies_charge_files_and_directories_once_without_authority(self):
        result = self.join()
        self.assertEqual([item['role'] for item in result['components']],
            ['archival_b_metadata_copy', 'archival_c_metadata_copy'])
        for field in ('logical_bytes', 'allocated_bytes', 'entry_count'):
            self.assertEqual(result[field], sum(value[field] for value in self.observations.values()))
        self.assertEqual(result['entry_count'], 8)
        self.assertEqual(len({(row['device'], row['inode']) for row in result['rows']}), 8)
        for field, value in result.items():
            if type(value) is bool:
                self.assertIs(value, field in ('charged_once', 'read_only', 'point_in_time_accounting_only'))
        self.assertFalse(result['archive_closure_proved'])
        self.assertFalse(result['missing_original_storage_accounted'])

    def test_each_independent_requirement_and_observation_requires_literal_b_c_set(self):
        for argument, values in (('observations', self.observations), ('roots', self.roots),
                ('files', self.files), ('pins', self.pins)):
            for replace in ('missing', 'extra', 'renamed'):
                changed = copy.deepcopy(values)
                if replace == 'missing': changed.pop('c')
                elif replace == 'extra': changed['d'] = copy.deepcopy(changed['c'])
                else: changed['d'] = changed.pop('c')
                with self.subTest(argument=argument, change=replace):
                    with self.assertRaisesRegex(ValueError, 'b/c'):
                        self.join(**{argument: changed})

    def test_observation_drift_and_changed_independent_pin_are_refused(self):
        changed = copy.deepcopy(self.observations); changed['b']['logical_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'independently retained'):
            self.join(changed)
        pins = copy.deepcopy(self.pins); pins['c']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'independently retained'):
            self.join(pins=pins)

    def test_missing_extra_or_changed_expected_file_pins_are_refused(self):
        for change in ('missing', 'extra', 'hash'):
            files = copy.deepcopy(self.files)
            if change == 'missing': files['b'].pop('evidence/receipt.json')
            elif change == 'extra': files['c']['unchecked.json'] = next(iter(files['c'].values())).copy()
            else: files['c']['evidence/receipt.json']['sha256'] = '0' * 64
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, 'file membership'):
                    self.join(files=files)

    def test_unrelated_empty_directory_is_not_charged_as_an_accepted_copy(self):
        (Path(self.roots['b']) / 'unrelated-empty').mkdir()
        changed = copy.deepcopy(self.observations); changed['b'] = observe(Path(self.roots['b']))
        with self.assertRaisesRegex(ValueError, 'required file ancestor'):
            self.join(changed, pins=self.repinned(changed))

    def test_transport_role_scope_and_authority_cannot_drift_even_when_repinned(self):
        for field, value in (('role', 'historical_ledger'), ('scope', self.roots['c']),
                ('read_only', False), ('current_observation_stable', False),
                ('authenticated_manifest_matched', False), ('execution_authorized', True)):
            changed = copy.deepcopy(self.observations); changed['b'][field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'transport'):
                    self.join(changed, pins=self.repinned(changed))

    def test_independent_root_drift_and_archive_root_overlap_are_refused(self):
        roots = dict(self.roots); roots['b'] += '-other'
        with self.assertRaisesRegex(ValueError, 'transport'): self.join(roots=roots)
        for root in (self.roots['b'], self.roots['b'] + '/nested'):
            roots = dict(self.roots); roots['c'] = root
            with self.assertRaisesRegex(ValueError, 'roots overlap'): self.join(roots=roots)

    def test_original_repository_root_ancestor_and_descendant_are_refused(self):
        original = archive.ORIGINAL_REPOSITORY_ROOT
        for root in (original, original + '/public-copy', str(Path(original).parent)):
            roots = dict(self.roots); roots['b'] = root
            with self.subTest(root=root):
                with self.assertRaisesRegex(ValueError, 'original repository'):
                    self.join(roots=roots)

    def test_private_journal_directory_and_spent_record_names_are_refused(self):
        for relative in ('.radio-native-v2-invocation-ledger-20261002c/copy.json',
                'spent-' + 'a' * 64 + '.json',
                'nested/spent-' + 'b' * 64 + '.json'):
            files = copy.deepcopy(self.files)
            files['c'] = {relative: next(iter(files['c'].values())).copy()}
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(ValueError, 'private journal'):
                    self.join(files=files)
        roots = dict(self.roots); roots['b'] = str(self.root / '.radio-native-v2-invocation-ledger-20261003d')
        with self.assertRaisesRegex(ValueError, 'private journal'): self.join(roots=roots)

    def test_cross_copy_inode_alias_is_refused_even_with_authentic_new_observation_pin(self):
        changed = copy.deepcopy(self.observations)
        source = changed['b']['rows'][0]; target = changed['c']['rows'][0]
        target['device'], target['inode'] = source['device'], source['inode']
        with self.assertRaisesRegex(ValueError, 'inode alias'):
            self.join(changed, pins=self.repinned(changed))

    def test_sole_link_and_exact_totals_are_required(self):
        for field, delta in (('nlink', 1), ('bytes', 1)):
            changed = copy.deepcopy(self.observations)
            row = next(row for row in changed['b']['rows'] if row['kind'] == 'file')
            row[field] += delta
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.join(changed, pins=self.repinned(changed))

    def test_canonical_paths_sorted_rows_and_file_directory_conflicts_are_refused(self):
        for relative in ('../escape.json', './copy.json', 'a//copy.json', '/copy.json', '.'):
            files = copy.deepcopy(self.files); files['b'] = {relative: next(iter(files['b'].values())).copy()}
            with self.subTest(relative=relative):
                with self.assertRaises(ValueError): self.join(files=files)
        files = copy.deepcopy(self.files); files['b']['evidence'] = next(iter(files['b'].values())).copy()
        with self.assertRaisesRegex(ValueError, 'also be a required directory'): self.join(files=files)
        changed = copy.deepcopy(self.observations); changed['b']['rows'].reverse()
        with self.assertRaisesRegex(ValueError, 'sorted'):
            self.join(changed, pins=self.repinned(changed))

    def test_nonstring_file_keys_cannot_be_coerced_to_archive_paths_by_json(self):
        files = copy.deepcopy(self.files); files['b'] = {1: next(iter(files['b'].values())).copy()}
        with self.assertRaisesRegex(ValueError, 'exact-string'):
            self.join(files=files)

    def test_combined_original_storage_and_entry_bounds_are_enforced(self):
        with mock.patch.object(archive, 'MAX_JOIN_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'bound exceeded'): self.join()
        with mock.patch.object(archive, 'MAX_INVENTORY_ENTRIES', 7):
            with self.assertRaisesRegex(ValueError, 'bound exceeded'): self.join()
        files = copy.deepcopy(self.files); files['b']['evidence/receipt.json']['bytes'] = archive.MAX_METADATA_FILE_BYTES + 1
        with self.assertRaisesRegex(ValueError, 'metadata file pin'): self.join(files=files)

    def test_returned_rows_and_pins_are_detached_from_all_caller_inputs(self):
        result = self.join(); retained = copy.deepcopy(result)
        self.observations['b']['rows'][0]['bytes'] += 1
        self.files['b']['evidence/receipt.json']['sha256'] = '0' * 64
        self.pins['c']['sha256'] = '0' * 64
        self.roots['b'] += '-moved'
        self.assertEqual(result, retained)


if __name__ == '__main__':
    unittest.main()
