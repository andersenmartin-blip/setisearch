"""Harmless real-guard tests; only standard-library fake children."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("leaf_supervisor", ROOT / "leaf_supervisor.py")
SUPERVISOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SUPERVISOR)


class GuardTests(unittest.TestCase):
    def setUp(self):
        evidence_root = os.environ.get("RADIO_ENGINEERING_OUTPUT")
        self.temp = None if evidence_root else tempfile.TemporaryDirectory()
        self.output = Path(evidence_root)/self._testMethodName if evidence_root else Path(self.temp.name)
        if evidence_root:
            self.output.mkdir()
        self.python = Path(sys.executable).resolve()
        self.guard = ROOT / "leaf_guard"
        self.limit = dict(SUPERVISOR.DEFAULT_LIMITS,
            child_wall_seconds=2, address_space_bytes=128*1024**2,
            cpu_seconds=2, per_file_bytes=8*1024**2, stdout_bytes=65536,
            stderr_bytes=65536, artifact_bytes=16*1024**2,
            read_reserve_bytes=64*1024**2, sample_interval_seconds=0.005,
            python_path=str(self.python),
            python_sha256=hashlib.sha256(self.python.read_bytes()).hexdigest(),
            guard_path=str(self.guard),
            guard_sha256=hashlib.sha256(self.guard.read_bytes()).hexdigest(),
            exec_seal_path=str(ROOT/"exec_seal.so"),
            exec_seal_sha256=hashlib.sha256((ROOT/"exec_seal.so").read_bytes()).hexdigest(),
            phase2_path=str(ROOT/"phase2_bootstrap.py"),
            phase2_sha256=hashlib.sha256((ROOT/"phase2_bootstrap.py").read_bytes()).hexdigest(),
            artifact_root=str(self.output))

    def tearDown(self):
        if self.temp is not None:
            self.temp.cleanup()

    def run_code(self, code, **changes):
        return SUPERVISOR.run_leaf([str(self.python), "-I", "-B", "-S", "-c", code],
            {"PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1"},
            self.output, self.output / "fake", dict(self.limit, **changes),
            time.monotonic()+3)

    def test_print_success_and_terminal_counters_wait4(self):
        result = self.run_code("print('harmless stdlib leaf')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertEqual(result["wait4"]["returncode"], 0)
        self.assertTrue(result["wait4"]["exact_direct_child_wait4"])
        self.assertGreater(result["wait4"]["maxrss_bytes"], 0)
        if result["terminal_proc"]["available"]:
            self.assertEqual(result["terminal_proc"]["status"]["State"].split()[0], "Z")
            self.assertTrue(result["terminal_proc"]["io"]["rchar"] > 0)
        else:
            self.assertTrue(result["terminal_proc"]["no_substituted_counters"])
        self.assertEqual(result["guard_status"]["no_new_privs"], 1)
        self.assertEqual(result["guard_status"]["seccomp_mode"], 2)
        self.assertTrue(result["phase2_status"]["exec_denied"])
        self.assertTrue(result["child_reaped"])
        self.assertGreater(result["proc_metadata_read_charge_bytes"], 0)
        self.assertLessEqual(result["proc_metadata_read_charge_bytes"],
                             result["limits"]["proc_metadata_budget_bytes"])
        if not result["terminal_proc"]["available"]:
            self.assertEqual(result["proc_child_metadata_read_charge_bytes"], 0)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"harmless stdlib leaf\n")
        self.assertFalse(result["runtime_qualified"])
        self.assertFalse(result["scientific_authority"])
        with self.assertRaises(ProcessLookupError):
            os.kill(result["pid"], 0)

    def test_socket_denied(self):
        result = self.run_code("import socket\ntry: socket.socket()\nexcept PermissionError: print('socket_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"socket_refused\n")

    def test_fork_denied(self):
        result = self.run_code("import os\ntry: os.fork()\nexcept PermissionError: print('fork_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"fork_refused\n")

    def test_thread_denied(self):
        result = self.run_code("import threading\ntry: threading.Thread(target=lambda:None).start()\nexcept RuntimeError: print('thread_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"thread_refused\n")

    def test_nonzero_retains_raw_stderr(self):
        result = self.run_code("import sys; print('terminal failure',file=sys.stderr); sys.exit(7)")
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["wait4"]["returncode"], 7)
        raw = Path(result["output"]["stderr"]["path"]).read_bytes()
        self.assertTrue(raw.startswith(SUPERVISOR.PHASE2_MARKER))
        self.assertTrue(raw.endswith(b"terminal failure\n"))

    def test_deadline_preserves_wait4_and_raw_output(self):
        result = self.run_code("import time; print('before deadline',flush=True); time.sleep(2)",
                               child_wall_seconds=0.2)
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertIn("leaf_wall_deadline", result["failures"])
        self.assertTrue(result["wait4"]["exact_direct_child_wait4"])
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"before deadline\n")

    def test_output_overflow_retained_and_fails(self):
        result = self.run_code("import os; os.write(1,b'X'*100000)", stdout_bytes=4096)
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertIn("stdout_limit_crossed", result["failures"])
        raw = Path(result["output"]["stdout"]["path"]).read_bytes()
        self.assertEqual(len(raw), result["output"]["stdout"]["bytes"])
        self.assertGreater(len(raw), 4096)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result["output"]["stdout"]["sha256"])

    def test_second_exec_refused(self):
        result = self.run_code("import os\ntry: os.execve('/usr/bin/true',['true'],{})\nexcept PermissionError: print('exec_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"exec_refused\n")

    def test_limit_keys_reject_unknown_before_spawn(self):
        with self.assertRaisesRegex(ValueError, "exact supervisor limit keys"):
            self.run_code("print('never spawned')", unknown_budget=1)

    def test_pin_read_budget_rejects_before_spawn(self):
        result = self.run_code("print('never spawned')", pin_read_budget_bytes=1)
        self.assertEqual(result["child_dispatches"], 0)
        self.assertEqual(result["status"], "FAILED_CLOSED")

    def test_wrong_pin_retains_actual_read_charge_without_spawn(self):
        result = self.run_code("print('never spawned')", python_sha256="0"*64)
        self.assertEqual(result["child_dispatches"], 0)
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["pin_read_charge_bytes"], self.python.stat().st_size)
        self.assertLessEqual(result["pin_read_charge_bytes"], result["limits"]["pin_read_budget_bytes"])


if __name__ == "__main__":
    unittest.main()
