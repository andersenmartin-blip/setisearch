"""Harmless real-guard tests; only standard-library fake children."""
import hashlib
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import sys
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

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
        self.assertEqual(result["guard_status"]["parent_death_signal"], int(signal.SIGKILL))
        self.assertEqual(result["guard_status"]["expected_parent_pid"], os.getpid())
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

    def test_parent_death_policy_cannot_be_cleared(self):
        code = ("import ctypes,errno,os\n"
                "lib=ctypes.CDLL(None,use_errno=True)\n"
                "assert lib.prctl(1,0,0,0,0)==-1 and ctypes.get_errno()==errno.EPERM\n"
                "try: os.setuid(os.getuid())\n"
                "except PermissionError: print('credential_change_refused')\n"
                "else: raise RuntimeError('credential syscall remained eligible')\n")
        result = self.run_code(code)
        self.assertEqual(result["status"], "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY", result)
        self.assertTrue(result["guard_status"]["pdeathsig_clear_denied"])
        self.assertTrue(result["guard_status"]["credential_mutation_denied"])
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(),
                         b"credential_change_refused\n")

    def test_expected_parent_mismatch_refused_before_python(self):
        actual_parent = os.getpid()
        with mock.patch.object(SUPERVISOR.os, "getpid", return_value=actual_parent+100000):
            result = self.run_code("print('must never execute')")
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["child_exit_code"], 125)
        self.assertTrue(result["child_reaped"])
        self.assertEqual(Path(result["output"]["stdout"]["path"]).read_bytes(), b"")
        self.assertIn(b"expected_parent_before_pdeathsig",
                      Path(result["output"]["stderr"]["path"]).read_bytes())

    def test_guarded_leaf_dies_when_supervisor_owner_dies(self):
        # Subreaping gives this test exact terminal ownership of the detached
        # leaf after its direct owner dies; no process is left for an init reaper.
        libc = ctypes.CDLL(None, use_errno=True)
        previous_subreaper = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous_subreaper),0,0,0), 0)
        self.assertEqual(libc.prctl(36, 1,0,0,0), 0)
        owner = None
        leaf_pid = None
        leaf_reaped = False
        owner_limits = dict(self.limit, child_wall_seconds=2)
        leaf_code = ("import ctypes,json,os,time\n"
                     "lib=ctypes.CDLL(None); sig=ctypes.c_int()\n"
                     "assert lib.prctl(2,ctypes.byref(sig),0,0,0)==0\n"
                     "print(json.dumps({'leaf_pid':os.getpid(),'owner_pid':os.getppid(),"
                     "'pdeathsig_after_exec':sig.value}),flush=True)\n"
                     "time.sleep(2)\n")
        owner_code = ("import importlib.util,time\n"
            f"spec=importlib.util.spec_from_file_location('supervisor',{str(ROOT/'leaf_supervisor.py')!r})\n"
            "module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)\n"
            f"module.run_leaf({[str(self.python),'-I','-B','-S','-c',leaf_code]!r},"
            f"{{'PATH':'/usr/bin:/bin','PYTHONNOUSERSITE':'1'}},{str(self.output)!r},"
            f"{str(self.output/'owned-leaf')!r},{owner_limits!r},time.monotonic()+3)\n")
        (self.output/"owner_driver.py").write_text(owner_code)
        stdout_path = self.output/"owned-leaf.stdout.bin"
        try:
            with (self.output/"owner.stdout.bin").open("xb") as out, \
                 (self.output/"owner.stderr.bin").open("xb") as err:
                owner = subprocess.Popen([str(self.python),"-I","-B","-S","-c",owner_code],
                    stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                    env={"PATH":"/usr/bin:/bin"}, start_new_session=True)
                ready_deadline = time.monotonic()+1
                while not stdout_path.exists() or b"\n" not in stdout_path.read_bytes():
                    if time.monotonic() >= ready_deadline:
                        self.fail("guarded leaf did not become ready")
                    time.sleep(0.005)
                ready = json.loads(stdout_path.read_bytes().splitlines()[0])
                leaf_pid = ready["leaf_pid"]
                self.assertEqual(ready["owner_pid"], owner.pid)
                self.assertEqual(ready["pdeathsig_after_exec"], int(signal.SIGKILL))
                triggered = time.monotonic()
                owner.kill()
                self.assertEqual(owner.wait(timeout=1), -int(signal.SIGKILL))
                terminal_deadline = triggered+1
                while os.waitid(os.P_PID,leaf_pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None:
                    if time.monotonic() >= terminal_deadline:
                        self.fail("detached leaf survived its owner")
                    time.sleep(0.005)
                pid,status,usage = os.wait4(leaf_pid,0)
                leaf_reaped = True
                proof = dict(schema="radio-parent-death-engineering-v1", owner_pid=owner.pid,
                    leaf_pid=pid, pdeathsig_after_exec=ready["pdeathsig_after_exec"],
                    leaf_returncode=os.waitstatus_to_exitcode(status), wait4_raw_status=status,
                    wait4_maxrss_bytes=usage.ru_maxrss*1024, leaf_reaped=True,
                    observed_seconds_after_owner_death=time.monotonic()-triggered,
                    scientific_authority=False, no_scientific_imports=True)
                (self.output/"parent-death-proof.json").write_text(json.dumps(proof,indent=2)+"\n")
                self.assertEqual(proof["leaf_returncode"], -int(signal.SIGKILL))
                self.assertGreater(proof["wait4_maxrss_bytes"], 0)
        finally:
            if owner is not None and owner.poll() is None:
                owner.kill()
                owner.wait(timeout=1)
            if leaf_pid is not None and not leaf_reaped:
                try:
                    os.kill(leaf_pid,signal.SIGKILL)
                    os.wait4(leaf_pid,0)
                except (ProcessLookupError,ChildProcessError):
                    pass
            self.assertEqual(libc.prctl(36,previous_subreaper.value,0,0,0),0)


if __name__ == "__main__":
    unittest.main()
