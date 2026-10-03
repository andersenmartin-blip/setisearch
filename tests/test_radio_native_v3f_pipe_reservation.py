"""Prospective tiny-child reservation tests; no protected control invocation.

The frozen e fixture is read only for the original differential scenario.
The corrected fixture is the actual prospective f module selected in CODE_FILES.
All actual children are tiny isolated Python programs in temporary case roots.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'results_radio_native_v3_compact_eight_input_control_20261003e/frozen-code/scripts/radio_native_v3_compact_eight_case_resource_fixture.py'
CANDIDATE_SOURCE = ROOT/'scripts/radio_native_v3f_compact_eight_case_resource_fixture.py'
EXPECTED_PIN = {'bytes':147886, 'sha256':'1052e92361c9fed84d4edde65c2f46eef3a51990ad91c544e35c879fe9aa94e1'}
FROZEN_SOURCE = SOURCE
BEFORE = """        # A source-pinned supervisor can emit at most output_cap per pipe.
        # Reserve both retained log bounds before giving it writable fds.
        check_case_metadata_write(stdout_path,2*output_cap)"""
AFTER = """        # Pipe output stays in bounded memory; only capped stderr is retained.
        # File-backed output retains both logs under the existing bounds.
        check_case_metadata_write(stdout_path,
            min(output_cap,LOG_LIMIT) if pipe_output else 2*output_cap)"""


def pin(path):
    raw = path.read_bytes()
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def load(patched):
    if patched:
        module = ModuleType("prospective_f_pipe_fixture")
        module.__file__ = str(CANDIDATE_SOURCE)
        exec(compile(CANDIDATE_SOURCE.read_bytes(),str(CANDIDATE_SOURCE),"exec"),module.__dict__)
        return module
    raw = SOURCE.read_bytes()
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} != EXPECTED_PIN:
        raise RuntimeError('Expected immutable baseline source differs')
    text = raw.decode()
    if text.count(BEFORE) != 1:
        raise RuntimeError('Unique baseline reservation statement required')
    module = ModuleType('prospective_pipe_candidate' if patched else 'immutable_e_baseline')
    module.__file__ = str(SOURCE)
    exec(compile(text,str(SOURCE),'exec'),module.__dict__)
    return module


ORIGINAL = load(False)
CANDIDATE = load(True)
BASELINE_FROZEN_PIN = pin(FROZEN_SOURCE)
SCENARIOS = []


class PipeReservationTests(unittest.TestCase):
    def scenario(self, *, patched=True, pipe_output=True, output_cap=2*1024**2,
                 stdout_bytes=0, stderr_bytes=1, prefill_bytes=1671168,
                 identity_inside_case=True):
        module = CANDIDATE if patched else ORIGINAL
        with tempfile.TemporaryDirectory(prefix='prospective-pipe-test-') as temporary:
            base = Path(temporary)
            case_root = base/'cases/case00'
            root = case_root/'command-observations'
            root.mkdir(parents=True)
            if os.statvfs(root).f_frsize != module.CAPACITY_BLOCK_BYTES:
                self.skipTest('Regression requires the frozen 4096-byte capacity filesystem')
            if prefill_bytes:
                (case_root/'synthetic-prefill.bin').write_bytes(b'0'*prefill_bytes)
            identity_path = root/'tiny-identity.json' if identity_inside_case else base/'tiny-identity.json'
            program = (
                "import json,os,sys,time; "
                "f=open(sys.argv[1],'x'); "
                "json.dump({'procfs_pid':int(os.readlink('/proc/self')),'namespace_pid':os.getpid()},f); "
                "f.flush();os.fsync(f.fileno());f.close(); "
                "time.sleep(0.015); "
                "sys.stdout.buffer.write(b'o'*int(sys.argv[2]));sys.stdout.buffer.flush(); "
                "sys.stderr.buffer.write(b'e'*int(sys.argv[3]));sys.stderr.buffer.flush(); "
                "time.sleep(0.025)"
            )
            argv = [str(Path(sys.executable).resolve()),'-I','-S','-B','-c',program,
                    str(identity_path),str(stdout_bytes),str(stderr_bytes)]
            successful = True
            returned = None
            try:
                returned = module.observe_process(argv,root,'command-0',identity_path,
                    deadline=time.monotonic()+5,output_cap=output_cap,
                    pipe_output=pipe_output,sample_retention_limit=2)
            except RuntimeError:
                successful = False
            observed = json.loads((root/'command-0-observation.json').read_bytes())
            summary = {
                'patched':patched, 'pipe_output':pipe_output, 'output_cap':output_cap,
                'stdout_bytes_requested':stdout_bytes,'stderr_bytes_requested':stderr_bytes,
                'synthetic_prefill_bytes':prefill_bytes,'successful':successful,
                'reason':observed['reason'],
                'child_launched':observed['bound_child_identity'] is not None,
                'direct_child_reaped':observed['direct_child_reaped'],
                'complete_pipe_output':observed['complete_pipe_output'],
                'observed_output_bytes':observed['observed_output_bytes'],
                'retained_stdout_log_bytes':(root/'command-0-stdout.log').stat().st_size if (root/'command-0-stdout.log').exists() else None,
                'retained_stderr_log_bytes':(root/'command-0-stderr.log').stat().st_size if (root/'command-0-stderr.log').exists() else None,
                'returned_stdout_bytes':None if returned is None else len(returned[1]),
                'returned_stderr_bytes':None if returned is None else len(returned[2])}
            SCENARIOS.append(summary)
            self.assertFalse(observed['execution_authorized'])
            self.assertEqual(observed['scientific_cases_run'],0)
            self.assertEqual(observed['telescope_reads'],0)
            self.assertEqual(observed['actual_connector_calls'],0)
            return summary

    def assert_prelaunch_capacity_failure(self, summary):
        self.assertFalse(summary['successful'])
        self.assertFalse(summary['child_launched'])
        self.assertFalse(summary['direct_child_reaped'])
        self.assertIn('capacity exceeded before write',summary['reason'])

    def assert_success(self, summary):
        self.assertTrue(summary['successful'])
        self.assertTrue(summary['child_launched'])
        self.assertTrue(summary['direct_child_reaped'])
        self.assertIsNone(summary['reason'])

    def test_original_large_pipe_preflight_rejects_even_empty_case(self):
        self.assert_prelaunch_capacity_failure(self.scenario(patched=False,prefill_bytes=0))

    def test_corrected_pipe_fits_used_metadata_bucket(self):
        summary = self.scenario()
        self.assert_success(summary)
        self.assertTrue(summary['complete_pipe_output'])
        self.assertEqual(summary['retained_stdout_log_bytes'],0)
        self.assertEqual(summary['retained_stderr_log_bytes'],1)

    def test_file_backed_large_cap_still_rejects_before_launch(self):
        self.assert_prelaunch_capacity_failure(self.scenario(pipe_output=False))

    def test_file_backed_default_cap_retains_both_logs(self):
        summary = self.scenario(pipe_output=False,output_cap=CANDIDATE.LOG_LIMIT,
                                stdout_bytes=17,stderr_bytes=19)
        self.assert_success(summary)
        self.assertEqual(summary['retained_stdout_log_bytes'],17)
        self.assertEqual(summary['retained_stderr_log_bytes'],19)

    def test_full_stdout_cap_is_returned_without_duplicate_disk_log(self):
        summary = self.scenario(stdout_bytes=2*1024**2,stderr_bytes=CANDIDATE.LOG_LIMIT)
        self.assert_success(summary)
        self.assertEqual(summary['observed_output_bytes'],{'stdout':2*1024**2,'stderr':CANDIDATE.LOG_LIMIT})
        self.assertEqual(summary['returned_stdout_bytes'],2*1024**2)
        self.assertEqual(summary['retained_stdout_log_bytes'],0)
        self.assertEqual(summary['retained_stderr_log_bytes'],CANDIDATE.LOG_LIMIT)

    def test_stderr_above_log_limit_remains_bounded_in_disk_retention(self):
        summary = self.scenario(stderr_bytes=CANDIDATE.LOG_LIMIT+1)
        self.assert_success(summary)
        self.assertEqual(summary['returned_stderr_bytes'],CANDIDATE.LOG_LIMIT+1)
        self.assertEqual(summary['retained_stderr_log_bytes'],CANDIDATE.LOG_LIMIT)

    def test_small_pipe_cap_retains_exact_emitted_bytes(self):
        summary = self.scenario(output_cap=8,stdout_bytes=8,stderr_bytes=8)
        self.assert_success(summary)
        self.assertEqual(summary['observed_output_bytes'],{'stdout':8,'stderr':8})
        self.assertEqual(summary['retained_stderr_log_bytes'],8)

    def test_stdout_above_pipe_cap_closes_and_reaps(self):
        summary = self.scenario(output_cap=8,stdout_bytes=9,stderr_bytes=0)
        self.assertFalse(summary['successful'])
        self.assertTrue(summary['direct_child_reaped'])
        self.assertEqual(summary['reason'],'Bounded child output cap exceeded')
        self.assertFalse(summary['complete_pipe_output'])

    def test_stderr_above_pipe_cap_closes_and_reaps(self):
        summary = self.scenario(output_cap=8,stderr_bytes=9)
        self.assertFalse(summary['successful'])
        self.assertTrue(summary['direct_child_reaped'])
        self.assertEqual(summary['reason'],'Bounded child output cap exceeded')
        self.assertEqual(summary['retained_stderr_log_bytes'],8)

    def test_exact_one_block_pipe_reservation_fits(self):
        # The child publishes identity outside the bucket so this boundary
        # independently measures exactly one allocated retained log block.
        summary = self.scenario(output_cap=1,stderr_bytes=1,
            prefill_bytes=CANDIDATE.CASE_OTHER_METADATA_BUDGET_BYTES-CANDIDATE.CAPACITY_BLOCK_BYTES,
            identity_inside_case=False)
        self.assert_success(summary)
        self.assertEqual(summary['retained_stderr_log_bytes'],1)

    def test_full_bucket_rejects_one_byte_pipe_reservation(self):
        self.assert_prelaunch_capacity_failure(self.scenario(output_cap=1,
            prefill_bytes=CANDIDATE.CASE_OTHER_METADATA_BUDGET_BYTES,
            identity_inside_case=False))

    def test_source_and_frozen_e_source_are_unchanged(self):
        self.assertEqual(pin(SOURCE),EXPECTED_PIN)
        self.assertEqual(pin(FROZEN_SOURCE),BASELINE_FROZEN_PIN)


if __name__ == '__main__':
    unittest.main()
