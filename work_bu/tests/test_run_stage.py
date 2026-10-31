"""Artificial metadata/byte tests only; never open astronomical arrays."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'run_stage.py'
spec = importlib.util.spec_from_file_location('bu_capture_under_test', SOURCE)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class TestStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.planpath, self.freeze = self.root/'plan.json', self.root/'freeze.json'
        self.input = self.root/'artificial_input.txt'
        self.input.write_text('artificial fixture, not an astronomical array\n')
        self.header = self.root/'header.json'; self.header.write_text('{}\n')
        sources = {str(path): stage.sha(path) for path in
                   (SOURCE, stage.CAPTURE_SOURCE, stage.ARCHIVE_SOURCE, stage.PARTIAL_SOURCE)}
        self.plan = {'source_sha256': sources, 'metadata_evidence': [], 'scans': [
            {'path': str(self.input), 'input_sha256': stage.sha(self.input),
             'header_path': str(self.header), 'header_sha256': stage.sha(self.header)} for _ in range(5)]}
        self.plan.update(runtime={'python_executable': stage.sys.executable,
                                  'python_version': stage.platform.python_version(),
                                  'python_executable_sha256': stage.sha(stage.sys.executable)},
                         caps=stage.CAPS, overall_storage_cap_bytes=stage.OVERALL_STORED_BYTES,
                         isolation_root=str(stage.ISOLATION))
        self.planpath.write_text(json.dumps(self.plan))
        self.freeze.write_text(json.dumps({'exact_readback_verified': True,
                                          'plan_sha256': stage.sha(self.planpath)}))

    def test_public_gate_requires_exact_readback_and_plan_bytes(self):
        stage.binding_pins(self.planpath, self.freeze)
        self.freeze.write_text(json.dumps({'exact_readback_verified': False,
                                          'plan_sha256': stage.sha(self.planpath)}))
        with self.assertRaisesRegex(ValueError, 'exact verified readback'):
            stage.binding_pins(self.planpath, self.freeze)
        self.freeze.write_text(json.dumps({'exact_readback_verified': True,
                                          'plan_sha256': '0'*64}))
        with self.assertRaisesRegex(ValueError, 'exact plan bytes'):
            stage.binding_pins(self.planpath, self.freeze)

    def fixture_worker(self, corrupt=False):
        execution, isolation = self.root/'execution', self.root/'isolation'
        output, isolated = execution/'batch1'/'payload', isolation/'batch1'
        output.parent.mkdir(parents=True); isolation.mkdir()
        archive = stage.archive_tools()
        def prepare(path):
            Path(path).mkdir(exist_ok=False)
            return {'test_only_artificial_isolation': str(path)}
        archive.prepare_isolation = prepare
        self.plan['isolation_root'] = str(isolation)
        self.planpath.write_text(json.dumps(self.plan))
        self.freeze.write_text(json.dumps({'exact_readback_verified': True,
                                          'plan_sha256': stage.sha(self.planpath)}))
        def run(plan, out, batch):
            out.mkdir()
            archive.save_json(out/'ARTIFICIAL_COMPLETE.json', {'batch': batch, 'absolute_path': str(out)})
            if corrupt:
                self.input.write_text('changed artificial fixture\n')
            return {'status': 'ARTIFICIAL_ONLY'}
        fake = types.SimpleNamespace(run_batch=run, audit_batch=lambda *args:
                                     {'status': 'PASS_BOUNDED_SAVED_RESULT_AUDIT', 'artificial_only': True})
        with patch.object(stage, 'EXECUTION', execution), patch.object(stage, 'ISOLATION', isolation), \
             patch.object(stage, 'archive_tools', return_value=archive), \
             patch.object(stage, 'module_at', return_value=fake), contextlib.redirect_stdout(io.StringIO()) as log:
            code = stage.worker(1, output, isolated, self.planpath, self.freeze)
        result = json.loads((output/'RESULT.json').read_text())
        terminal = json.loads(log.getvalue().splitlines()[-1])
        self.assertEqual(terminal['result_sha256'], stage.sha(output/'RESULT.json'))
        return code, result, output, isolated, archive

    def test_closed_archive_export_retains_absolute_path_and_rejects_mutation(self):
        code, result, output, isolated, archive = self.fixture_worker()
        self.assertEqual(code, 0); self.assertEqual(result['status'], 'PASS')
        self.assertEqual((isolated/'evidence.zip').read_bytes(), (output/'EVIDENCE.zip').read_bytes())
        with zipfile.ZipFile(output/'EVIDENCE.zip') as saved:
            record = json.loads(saved.read('ARTIFICIAL_COMPLETE.json'))
            self.assertEqual(record['absolute_path'], str(isolated/'contents'))
            self.assertIn('BOUNDED_AUDIT.json', saved.namelist())
        with (output/'EVIDENCE.zip').open('r+b') as stream:
            stream.seek(0); stream.write(b'BROKEN')
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            archive.verify_archive(output/'EVIDENCE.zip', result['archive']['members'])

    def test_input_change_fails_without_erasing_failed_evidence(self):
        code, result, output, isolated, archive = self.fixture_worker(corrupt=True)
        self.assertEqual(code, 1); self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['errors']); self.assertTrue(isolated.is_dir())
        with zipfile.ZipFile(output/'EVIDENCE.zip') as saved:
            self.assertIn('BU_FAILURE.json', saved.namelist())
        with self.assertRaises(FileExistsError):
            archive.save_json(output/'RESULT.json', {})


if __name__ == '__main__':
    unittest.main()
