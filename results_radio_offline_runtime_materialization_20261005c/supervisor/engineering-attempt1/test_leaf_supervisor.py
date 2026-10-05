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
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.python = Path(sys.executable).resolve()
        self.guard = ROOT / "leaf_guard"
        self.limit = dict(SUPERVISOR.DEFAULT_LIMITS,
            child_wall_seconds=2, address_space_bytes=128*1024**2,
            cpu_seconds=2, per_file_bytes=8*1024**2, stdout_bytes=65536,
            stderr_bytes=65536, artifact_storage_bytes=16*1024**2,
            read_reserve_bytes=64*1024**2, sample_interval_seconds=0.005,
            python_path=str(self.python),
            python_sha256=hashlib.sha256(self.python.read_bytes()).hexdigest(),
            guard_path=str(self.guard),
            guard_sha256=hashlib.sha256(self.guard.read_bytes()).hexdigest(),
            artifact_root=str(self.output))

    def tearDown(self):
        self.temp.cleanup()

    def run_code(self, code, **changes):
        return SUPERVISOR.run_leaf([str(self.python), "-I", "-B", "-S", "-c", code],
            {"PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1"},
            self.output, self.output / "fake", dict(self.limit, **changes),
            time.monotonic()+3)

    def test_print_success_and_terminal_counters_wait4(self):
        result = self.run_code("print('harmless stdlib leaf')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED", result)
        self.assertEqual(result["wait4"]["returncode"], 0)
        self.assertTrue(result["wait4"]["exact_direct_child_wait4"])
        self.assertGreater(result["wait4"]["maxrss_bytes"], 0)
        self.assertEqual(result["terminal_proc"]["status"]["State"].split()[0], "Z")
        self.assertTrue(result["terminal_proc"]["io"]["rchar"] > 0)
        self.assertEqual(result["guard_status"]["no_new_privs"], 1)
        self.assertEqual(result["guard_status"]["seccomp_mode"], 2)
        self.assertEqual(result["admitted_exec_count"], 1)
        self.assertEqual(result["completed_exec_events"], 1)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"harmless stdlib leaf\n")
        self.assertFalse(result["runtime_qualified"])
        self.assertFalse(result["scientific_authority"])
        with self.assertRaises(ProcessLookupError):
            os.kill(result["pid"], 0)

    def test_socket_denied(self):
        result = self.run_code("import socket\ntry: socket.socket()\nexcept PermissionError: print('socket_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"socket_refused\n")

    def test_fork_denied(self):
        result = self.run_code("import os\ntry: os.fork()\nexcept PermissionError: print('fork_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"fork_refused\n")

    def test_thread_denied(self):
        result = self.run_code("import threading\ntry: threading.Thread(target=lambda:None).start()\nexcept RuntimeError: print('thread_refused')")
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED", result)
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"thread_refused\n")

    def test_nonzero_retains_raw_stderr(self):
        result = self.run_code("import sys; print('terminal failure',file=sys.stderr); sys.exit(7)")
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["wait4"]["returncode"], 7)
        self.assertEqual(Path(result["output"]["stderr"]["path"]).read_bytes(), b"terminal failure\n")

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
        result = self.run_code("import os; os.execve('/usr/bin/true',['true'],{})")
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertIn("additional_exec_refused", result["failures"])


if __name__ == "__main__":
    unittest.main()
