import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings
import zipfile

PATH = Path(__file__).resolve().parents[1]/'isolated_worker.py'
spec = importlib.util.spec_from_file_location('bt_isolated_worker_tests', PATH)
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)


class IsolatedWorkerTests(unittest.TestCase):
    def test_a04_wrapper_leaves_exclusive_output_creation_to_frozen_module(self):
        # This is a protocol mock: it opens no saved score or scientific input.
        with tempfile.TemporaryDirectory(prefix='seti_bt_test_', dir='/dev/shm') as isolated_root, \
                tempfile.TemporaryDirectory() as destination:
            out, isolated = Path(destination)/'new', Path(isolated_root)/'a04'
            def fake_frozen_run(scan_dirs, case, output, base_dirs, pins):
                self.assertFalse(output.exists(), 'Frozen BQ must exclusively create its output directory')
                output.mkdir(parents=True, exist_ok=False)
                (output/'current_associations.jsonl').write_bytes(b'{"test_only":true}\n')
                (output/'legacy_associations.jsonl').write_bytes(b'{"test_only":true}\n')
                return {'status': 'PASS', 'child_stream_closure': {'status': 'PASS'},
                        'test_only_protocol_mock': True}
            run = mock.Mock(side_effect=fake_frozen_run)
            frozen = SimpleNamespace(run_closed_assessment=run,
                closure=SimpleNamespace(evaluate_closure=mock.Mock(return_value={'effective_status': 'PASS'})))
            plan = {'scan_dirs': [], 'base_scan_dirs': [], 'case': {'case_id': 'A04'},
                    'input_pins': [], 'source_pins': []}
            with mock.patch.object(bt, 'source_and_input_pins', return_value=(plan, [], [])), \
                    mock.patch.object(bt, 'load_module', return_value=frozen):
                result = bt.run_isolated('a04', out, isolated)
            self.assertEqual(result['status'], 'PASS', result['errors'])
            run.assert_called_once()
            with zipfile.ZipFile(out/'EVIDENCE.zip') as archive:
                assessment = json.loads(archive.read('ASSESSMENT.json'))
            self.assertTrue(assessment['test_only_protocol_mock'])

    def test_tiny_original_br_fixture_archived_and_exported(self):
        with tempfile.TemporaryDirectory(prefix='seti_bt_test_', dir='/dev/shm') as isolated_root, \
                tempfile.TemporaryDirectory() as destination:
            out, isolated = Path(destination)/'new', Path(isolated_root)/'fixture'
            result = bt.run_isolated('fixture', out, isolated, fixture_records=3)
            self.assertEqual(result['status'], 'PASS', result['errors'])
            self.assertTrue(result['source_pins_verified_after'])
            self.assertTrue(result['final_pins_verified_after_export'])
            self.assertEqual(result['input_pins_before'], [])
            self.assertTrue(isolated.exists())
            receipt = result['archive']
            verified = bt.verify_archive(out/receipt['path'], receipt['members'])
            self.assertEqual(verified['sha256'], receipt['sha256'])
            self.assertEqual(verified['bytes'], receipt['bytes'])
            names = {item['path'] for item in receipt['members']}
            self.assertTrue({'RESULT.json', 'FILE_MONITOR.json', 'payload/fixture_0.jsonl',
                             'payload/fixture_1.jsonl', 'BT_SOURCE_INPUT_BINDINGS.json'} <= names)
            with zipfile.ZipFile(out/'EVIDENCE.zip') as archive:
                assessment = json.loads(archive.read('RESULT.json'))
            self.assertEqual(assessment['records_per_stream'], 3)
            self.assertEqual(assessment['status'], 'PASS')

    def make_archive(self, root):
        contents = root/'contents'
        contents.mkdir()
        (contents/'sample.json').write_bytes(b'{"sample":123}\n')
        receipt = bt.create_archive(contents, root/'evidence.zip')
        return root/'evidence.zip', receipt

    def test_archive_truncation_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path, receipt = self.make_archive(Path(folder))
            with path.open('r+b') as stream:
                stream.truncate(path.stat().st_size-20)
            with self.assertRaises((ValueError, zipfile.BadZipFile)):
                bt.verify_archive(path, receipt['members'])

    def test_archive_missing_member_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, receipt = self.make_archive(root)
            new = root/'missing.zip'
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(new, 'x') as target:
                target.writestr(bt.MANIFEST_NAME, source.read(bt.MANIFEST_NAME))
            with self.assertRaises(ValueError):
                bt.verify_archive(new, receipt['members'])

    def test_duplicate_archive_member_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path, receipt = self.make_archive(Path(folder))
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(path, 'a') as archive:
                    archive.writestr('sample.json', b'{"sample":123}\n')
            with self.assertRaises(ValueError):
                bt.verify_archive(path, receipt['members'])

    def test_mutated_member_with_valid_crc_fails_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, receipt = self.make_archive(root)
            new = root/'mutated.zip'
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(new, 'x') as target:
                for name in source.namelist():
                    raw = source.read(name)
                    target.writestr(name, raw.replace(b'123', b'124') if name == 'sample.json' else raw)
            with self.assertRaises(ValueError):
                bt.verify_archive(new, receipt['members'])

    def test_unsafe_manifest_name_rejected(self):
        member = {'path': '../outside', 'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()}
        with self.assertRaises(ValueError):
            bt.validate_manifest([member])

    def test_symlink_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, receipt = self.make_archive(root)
            new = root/'symlink.zip'
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(new, 'x') as target:
                for name in source.namelist():
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = (0o120777 if name == 'sample.json' else 0o100600) << 16
                    target.writestr(info, source.read(name))
            with self.assertRaises(ValueError):
                bt.verify_archive(new, receipt['members'])

    def test_export_is_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, receipt = self.make_archive(root)
            destination = root/'export.zip'
            bt.export_archive(source, destination, receipt)
            with self.assertRaises(FileExistsError):
                bt.export_archive(source, destination, receipt)

    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                bt.run_isolated('fixture', Path(folder), Path('/dev/shm/seti_bt_unused/fixture'), 1)

    def test_a04_cannot_accept_altered_fixture_count(self):
        with self.assertRaises(ValueError):
            bt.run_isolated('a04', Path('/tmp/no-output'), Path('/dev/shm/no-isolation/a04'), 2)

    def test_preexisting_isolation_is_never_modified(self):
        with tempfile.TemporaryDirectory(prefix='seti_bt_test_', dir='/dev/shm') as isolated_root, \
                tempfile.TemporaryDirectory() as destination:
            isolated = Path(isolated_root)/'existing'
            contents = isolated/'contents'
            contents.mkdir(parents=True)
            sentinel = contents/'sentinel.json'
            sentinel.write_bytes(b'{"preserved":true}\n')
            result = bt.run_isolated('fixture', Path(destination)/'new', isolated, fixture_records=1)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIsNone(result['archive'])
            self.assertFalse(result['isolated_files_retained'])
            self.assertEqual([p.name for p in contents.iterdir()], ['sentinel.json'])
            self.assertEqual(sentinel.read_bytes(), b'{"preserved":true}\n')

    def test_resource_limits_cannot_be_relaxed(self):
        for which in (resource.RLIMIT_CPU, resource.RLIMIT_AS, resource.RLIMIT_FSIZE):
            with mock.patch.object(bt.resource, 'getrlimit', return_value=(90, 91)), \
                    mock.patch.object(bt.resource, 'setrlimit') as setter:
                bt.tighten_limit(which, 180)
                setter.assert_called_once_with(which, (90, 91))

    def test_wrong_source_pin_fails(self):
        path = 'work_br/stream_closure.py'
        pin = {'path': path, 'bytes': (bt.REPO/path).stat().st_size, 'sha256': '0'*64}
        with self.assertRaises(ValueError):
            bt.verify_pins([pin])

    def test_insufficient_tmpfs_capacity_stops_before_identity_creation(self):
        with tempfile.TemporaryDirectory(prefix='seti_bt_test_', dir='/dev/shm') as isolated_root:
            target = Path(isolated_root)/'fixture'
            with mock.patch.object(bt.os, 'statvfs', return_value=SimpleNamespace(f_bavail=1, f_frsize=4096)):
                with self.assertRaises(ValueError):
                    bt.prepare_isolation(target)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
