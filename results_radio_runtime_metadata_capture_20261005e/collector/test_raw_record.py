"""Inert real PathDistribution layouts; no scientific imports or child launches."""
import base64
import copy
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('collector_raw_record_inert', ROOT / 'collect_runtime_identity.py')
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


def expected_row(path, raw):
    digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode('ascii')
    return [path, 'sha256=' + digest, str(len(raw))]


class RawRecordTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.venv = Path(self.directory.name) / 'venv'
        self.site = self.venv / 'lib/python3.12/site-packages'
        (self.site / 'bin').mkdir(parents=True)
        self.record_rows, self.distributions = {}, {}
        self.inputs = {'schema': 'seti-installed-raw-record-inputs-v1', 'venv_root': str(self.venv), 'records': {}}
        for name, version in collector.COHORT.items():
            info = self.site / (name + '-' + version + '.dist-info')
            info.mkdir()
            raw = ('Name: ' + name + '\nVersion: ' + version + '\n').encode()
            (info / 'METADATA').write_bytes(raw)
            self.record_rows[name] = [expected_row(info.name + '/METADATA', raw), [info.name + '/RECORD', '', '']]
            self.distributions[name] = importlib.metadata.PathDistribution(info)
        rows = []
        for index, name in enumerate(('f2py', 'numpy-config')):
            raw = (b'# INERT NEVER EXECUTED ' + bytes([65 + index]) * 224)[:224]
            path = self.site / 'bin' / name
            path.write_bytes(raw)
            path.chmod(0o755)
            declared = '../../bin/' + name
            record_row = expected_row(declared, raw)
            self.record_rows['numpy'].insert(index, record_row)
            rows.append({'record_path': declared, 'declared_location': str((self.site / declared).resolve()),
                         'actual_installed_path': str(path), 'record_hash': record_row[1],
                         'record_size': len(raw), 'actual_pin': {'path': str(path), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest(), 'mode': 0o755}})
        self.relocations = {'schema': 'seti-exact-target-record-relocations-v1', 'distribution': 'numpy',
                            'distribution_version': '2.3.5', 'venv_root': str(self.venv), 'rows': rows}
        for name in collector.COHORT:
            self.write_record(name)

    def tearDown(self):
        self.directory.cleanup()

    def write_record(self, name, raw=None):
        info = self.distributions[name]._path
        if raw is None:
            stream = io.StringIO(newline='')
            csv.writer(stream, lineterminator='\n').writerows(self.record_rows[name])
            raw = stream.getvalue().encode('utf-8')
        path = info / 'RECORD'
        path.write_bytes(raw)
        self.inputs['records'][name] = {'version': collector.COHORT[name], 'record_pin': {
            'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'mode': path.stat().st_mode & 0o777}}
        return raw

    def inventory(self, name='numpy', reader=None, distribution=None):
        return collector.distribution_inventory(name, distribution or self.distributions[name], self.venv,
                    reader or collector.BoundedReader(), self.relocations, self.inputs)

    def test_real_stdlib_files_omits_two_rows_but_complete_raw_inventory_verifies_both(self):
        dist = self.distributions['numpy']
        projected = list(map(str, dist.files))
        self.assertEqual(len(projected), 2)
        reader = collector.BoundedReader()
        result = self.inventory(reader=reader)
        self.assertEqual(result['file_count'], 4)
        self.assertEqual(result['verified_generated_script_relocations'], 2)
        self.assertEqual(result['stdlib_distribution_files_projection']['presence_filtered_paths'], projected)
        self.assertEqual(result['stdlib_distribution_files_projection']['omitted_declared_paths'],
                         ['../../bin/f2py', '../../bin/numpy-config'])
        source = result['raw_record_source']
        raw = (dist._path / 'RECORD').read_bytes()
        self.assertEqual(base64.b64decode(source['raw_base64']), raw)
        self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(reader.charged_bytes, len(raw) + 448)
        self.assertEqual(result['files'], self.inventory()['files'])
        self.assertTrue(all(row['record_relocation']['whole_script_bytes_verified']
                            for row in result['files'] if row['record_relocation']))

    def test_presence_projection_retains_unsorted_raw_record_order_and_row_witnesses(self):
        self.record_rows['numpy'].reverse()
        self.write_record('numpy')
        actual = list(map(str, self.distributions['numpy'].files))
        self.assertNotEqual(actual, sorted(actual))
        result = self.inventory()
        projection = result['stdlib_distribution_files_projection']
        self.assertEqual(projection['presence_filtered_paths'], actual)
        self.assertEqual(projection['path_order'], 'raw_RECORD_row_order')
        ordinals = {r['record_path']: r['raw_record_row_ordinal'] for r in result['files']}
        self.assertEqual(ordinals, {r[0]: i for i, r in enumerate(self.record_rows['numpy'], 1)})

    def test_inventory_never_consults_distribution_files_property(self):
        class NoFiles(importlib.metadata.PathDistribution):
            @property
            def files(self):
                raise AssertionError('presence-filtered files must not be consulted')
        result = self.inventory(distribution=NoFiles(self.distributions['numpy']._path))
        self.assertEqual(result['file_count'], 4)

    def test_current_record_hash_or_size_mutation_refused_before_script_read(self):
        for column, value in ((1, 'sha256=' + 'A' * 43), (2, '225')):
            original = self.record_rows['numpy'][0][column]
            self.record_rows['numpy'][0][column] = value
            raw = self.write_record('numpy')
            reader = collector.BoundedReader()
            with self.assertRaisesRegex(collector.Refusal, 'current generated script RECORD row'):
                self.inventory(reader=reader)
            self.assertEqual(reader.charged_bytes, len(raw))
            self.record_rows['numpy'][0][column] = original
            self.write_record('numpy')

    def test_actual_script_content_or_mode_mutation_refused(self):
        path = self.site / 'bin/f2py'
        original = path.read_bytes()
        path.write_bytes(b'Z' * 224)
        with self.assertRaisesRegex(collector.Refusal, 'whole bytes differ'):
            self.inventory()
        path.write_bytes(original)
        path.chmod(0o644)
        with self.assertRaisesRegex(collector.Refusal, 'whole bytes differ'):
            self.inventory()

    def test_duplicate_unknown_unused_and_wrong_relocation_input_fail_closed(self):
        for change, error in ((lambda v: v['rows'].__setitem__(1, v['rows'][0]), 'unknown or duplicate'),
                              (lambda v: v['rows'][0].__setitem__('record_path', '../../bin/unknown'), 'unknown or duplicate'),
                              (lambda v: v['rows'][0].__setitem__('actual_installed_path', str(self.venv / 'other')), 'path differs')):
            changed = copy.deepcopy(self.relocations)
            change(changed)
            with self.assertRaisesRegex(collector.Refusal, error):
                collector._validate_record_relocations(changed, self.venv)
        self.record_rows['numpy'].pop(0)
        self.write_record('numpy')
        with self.assertRaisesRegex(collector.Refusal, 'row was unused'):
            self.inventory()

    def test_unknown_and_duplicate_raw_paths_get_no_fallback(self):
        original = copy.deepcopy(self.record_rows['numpy'])
        self.record_rows['numpy'].append(expected_row('../../bin/unknown', b'inert'))
        self.write_record('numpy')
        with self.assertRaisesRegex(collector.Refusal, 'unknown target RECORD relocation'):
            self.inventory()
        self.record_rows['numpy'] = original + [original[0]]
        self.write_record('numpy')
        with self.assertRaisesRegex(collector.Refusal, 'duplicate distribution RECORD path'):
            self.inventory()

    def test_declared_file_appearing_or_actual_symlink_refused(self):
        declared = self.site / '../../bin/f2py'
        declared.parent.mkdir(parents=True)
        declared.write_bytes(b'inert newly appearing file')
        with self.assertRaisesRegex(collector.Refusal, 'unexpectedly exists'):
            self.inventory()
        declared.unlink()
        actual = self.site / 'bin/f2py'
        actual.unlink()
        actual.symlink_to(self.site / 'bin/numpy-config')
        with self.assertRaisesRegex(collector.Refusal, 'namespace alias'):
            self.inventory()

    def test_input_json_bounds_exact_raw_pins_and_duplicate_keys(self):
        for filename, value, read in [('record-inputs.json', self.inputs, collector._read_record_inputs),
                                     ('relocations.json', self.relocations, collector._read_record_relocations)]:
            path = Path(self.directory.name) / filename
            raw = json.dumps(value).encode()
            path.write_bytes(raw)
            reader = collector.BoundedReader()
            parsed, pin = read(path, reader, self.venv)
            self.assertEqual(parsed, value)
            self.assertEqual(pin['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(reader.charged_bytes, len(raw))
            path.write_bytes(b'x' * 65537)
            with self.assertRaisesRegex(collector.Refusal, 'per-file read cap'):
                read(path, collector.BoundedReader(), self.venv)
            path.write_text(json.dumps(value)[:-1] + ',"schema":"duplicate"}')
            with self.assertRaisesRegex(collector.Refusal, 'duplicate .*JSON key'):
                read(path, collector.BoundedReader(), self.venv)

    def test_pinned_record_whole_body_and_mode_refused(self):
        path = self.distributions['numpy']._path / 'RECORD'
        original = path.read_bytes()
        path.write_bytes(original.replace(b'METADATA', b'METADATX'))
        with self.assertRaisesRegex(collector.Refusal, 'whole bytes differ'):
            self.inventory()
        path.write_bytes(original)
        path.chmod(0o600)
        with self.assertRaisesRegex(collector.Refusal, 'whole bytes differ'):
            self.inventory()

    def test_metadata_owner_and_record_alias_refused(self):
        with self.assertRaisesRegex(collector.Refusal, 'metadata path differs'):
            self.inventory(distribution=self.distributions['h5py'])
        path = self.distributions['numpy']._path / 'RECORD'
        raw = path.read_bytes()
        path.unlink()
        other = path.parent / 'other-record'
        other.write_bytes(raw)
        path.symlink_to(other)
        with self.assertRaisesRegex(collector.Refusal, 'namespace alias'):
            self.inventory()

    def test_missing_ordinary_row_is_not_silently_filtered(self):
        path = self.distributions['numpy']._path / 'METADATA'
        # Keep version independently known to avoid testing unrelated metadata absence.
        ordinary = self.site / 'missing.txt'
        self.record_rows['numpy'].insert(2, expected_row('missing.txt', b'inert'))
        self.write_record('numpy')
        self.assertNotIn('missing.txt', list(map(str, self.distributions['numpy'].files)))
        with self.assertRaisesRegex(collector.Refusal, 'missing ordinary file'):
            self.inventory()
        self.assertTrue(path.exists())
        self.assertFalse(ordinary.exists())

    def test_strict_csv_utf8_path_and_field_schema(self):
        own = b'numpy-2.3.5.dist-info/RECORD,,\n'
        cases = [b'"unterminated,,\n' + own, b'x,y,z,extra\n' + own, b'\xff,,\n' + own,
                 b'./x,sha256=' + b'A' * 43 + b',1\n' + own,
                 b'x//y,sha256=' + b'A' * 43 + b',1\n' + own,
                 b'/x,sha256=' + b'A' * 43 + b',1\n' + own,
                 b'x\\y,sha256=' + b'A' * 43 + b',1\n' + own,
                 b'x\x00y,sha256=' + b'A' * 43 + b',1\n' + own]
        for raw in cases:
            with self.subTest(raw=raw[:30]), self.assertRaises(collector.Refusal):
                collector._parse_raw_record(raw, 'numpy')

    def test_canonical_hash_size_unique_self_row_and_member_bounds(self):
        own = b'numpy-2.3.5.dist-info/RECORD,,\n'
        cases = [b'x,,\n' + own, b'x,sha256=' + b'A' * 42 + b'B,1\n' + own,
                 b'x,md5=' + b'A' * 43 + b',1\n' + own,
                 b'x,sha256=' + b'A' * 43 + b',01\n' + own,
                 b'x,sha256=' + b'A' * 43 + b',134217729\n' + own,
                 own + own, b'x,sha256=' + b'A' * 43 + b',1\n',
                 b'numpy-2.3.5.dist-info/RECORD,sha256=' + b'A' * 43 + b',1\n']
        for raw in cases:
            with self.subTest(raw=raw[:30]), self.assertRaises(collector.Refusal):
                collector._parse_raw_record(raw, 'numpy')

    def test_complete_record_read_and_parser_are_finitely_bounded(self):
        with self.assertRaisesRegex(collector.Refusal, 'read budget cannot fit'):
            self.inventory(reader=collector.BoundedReader(limit=1))
        with self.assertRaisesRegex(collector.Refusal, 'finite raw RECORD'):
            collector._parse_raw_record(b'x' * (collector.MAX_RECORD_BYTES + 1), 'numpy')
        raw = b''.join(('x' + str(i) + ',sha256=' + 'A' * 43 + ',1\n').encode()
                       for i in range(collector.MAX_FILES + 1))
        with self.assertRaisesRegex(collector.Refusal, 'row count'):
            collector._parse_raw_record(raw, 'numpy')

    def test_changed_record_between_inventory_observations_cannot_reuse_original_pin(self):
        before = self.inventory()
        path = self.distributions['numpy']._path / 'RECORD'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(collector.Refusal, 'whole bytes differ'):
            self.inventory()
        self.assertTrue(before['raw_record_source']['authoritative_complete_raw_rows'])


if __name__ == '__main__':
    unittest.main()
