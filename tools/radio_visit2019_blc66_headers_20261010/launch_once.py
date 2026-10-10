"""Once-only full-process meter for the separately frozen initial header worker.

Inert on import. This launcher has no HTTP/HDF5/value API. It can launch only the
exact pinned worker after root's distinct source/admission bindings and GO.
Original child metadata status and actual process termination remain separate
from the outer whole-process resource gate. Failed attempts are never retried.
"""
from __future__ import annotations
import time
WALL_STARTED = time.monotonic()
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_visit2019_blc66_headers_20261010"
RESULTS = "results/radio_visit2019_blc66_headers_20261010"
WORKER = ROOT / TOOLS / "header_probe_v1.py"
SCOPE = ROOT / TOOLS / "initial_scope.json"
ADMISSION = ROOT / RESULTS / "ROOT_ADMISSION.json"
INITIAL = ROOT / RESULTS / "initial"
OUTPUT = ROOT / RESULTS / "command_attempt"
WORKER_SHA = "401948c7facf7af6f3ed4aaa572a142d8b6e6ceab498d9d4951756c7d2e62381"
SCOPE_SHA = "5e3c19e59cc831f5ba0a5a8dc61035753ceba12b246b153d05c28cdfbdc05a99"
CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 600, 536870912
TERMINATION_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


class ExternalTermination(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__("Outer launcher received termination signal " + str(signum))


def terminate_into_cleanup(signum, frame):
    raise ExternalTermination(signum)


def protect_final_cleanup():
    # Repeated external signals cannot interrupt child reap or the final receipt.
    for signum in TERMINATION_SIGNALS:
        signal.signal(signum, signal.SIG_IGN)


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": sha(raw)}


def write_new(path, obj):
    raw = (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def wait_child(pid, launched):
    """wait4 reaps the actual PID once and includes final interpreter close."""
    timeout = False
    killed = False
    termination_started = None
    while True:
        try:
            found, status, usage = os.wait4(pid, os.WNOHANG)
        except InterruptedError:
            continue
        if found:
            return status, usage, timeout, killed
        elapsed = time.monotonic() - WALL_STARTED
        if not timeout and elapsed > WALL_CAP:
            timeout = True
            termination_started = time.monotonic()
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        elif timeout and not killed and time.monotonic() - termination_started > 2:
            killed = True
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-launcher-sha256", required=True)
    parser.add_argument("--public-freeze-commit", required=True,
                        help="Exact original worker/scope public freeze commit")
    parser.add_argument("--launcher-public-freeze-commit", required=True)
    parser.add_argument("--expected-root-admission-sha256", required=True)
    parser.add_argument("--root-go-header-metadata-only", action="store_true")
    args = parser.parse_args()
    require(args.root_go_header_metadata_only, "Explicit root header-only GO required")
    for value in (args.expected_launcher_sha256, args.expected_root_admission_sha256):
        require(re.fullmatch(r"[0-9a-f]{64}", value), "Exact SHA256 required")
    for value in (args.public_freeze_commit, args.launcher_public_freeze_commit):
        require(re.fullmatch(r"[0-9a-f]{40}", value), "Exact public commit required")
    self_pin, worker_pin, scope_pin, admission_pin = (
        pin(Path(__file__).resolve()), pin(WORKER), pin(SCOPE), pin(ADMISSION))
    require(self_pin["sha256"] == args.expected_launcher_sha256, "Launcher pin changed")
    require(worker_pin["sha256"] == WORKER_SHA and scope_pin["sha256"] == SCOPE_SHA,
            "Frozen worker/scope changed")
    require(admission_pin["sha256"] == args.expected_root_admission_sha256,
            "Root admission pin changed")
    admission = json.loads(ADMISSION.read_bytes())
    require(admission.get("schema") == "SETI_VISIT2019_BLC66_ROOT_INITIAL_HEADER_ADMISSION_V1"
            and admission.get("status") == "PASS_FINITE_HEADER_ONLY_NO_REPLAY_ROOT_ADMISSION"
            and admission.get("scope_sha256") == SCOPE_SHA
            and admission.get("wrapper_sha256") == WORKER_SHA
            and admission.get("source_public_freeze_commit") == args.public_freeze_commit
            and admission.get("header_metadata_only_authorized") is True,
            "Exact active root admission required")
    require(not INITIAL.exists(), "Original initial directory exists; no launch/retry")
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    OUTPUT.mkdir(exist_ok=False)
    directory_fd = os.open(OUTPUT, os.O_RDONLY | os.O_DIRECTORY)
    fcntl.flock(directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.fsync(directory_fd)
    cmd = [sys.executable, str(WORKER), "--scope", str(SCOPE),
           "--expected-scope-sha256", SCOPE_SHA, "--expected-wrapper-sha256", WORKER_SHA,
           "--public-freeze-commit", args.public_freeze_commit,
           "--root-admission", str(ADMISSION),
           "--expected-root-admission-sha256", args.expected_root_admission_sha256,
           "--root-go-header-metadata-only"]
    receipt = {
        "schema": "SETI_VISIT2019_FULL_CHILD_COMMAND_RESOURCE_RECEIPT_V1",
        "status": "CREATE_ONLY_COMMAND_ATTEMPT_IN_PROGRESS",
        "started_UTC": utc(), "launcher": self_pin, "worker": worker_pin,
        "scope": scope_pin, "root_admission": admission_pin,
        "source_public_freeze_commit": args.public_freeze_commit,
        "launcher_public_freeze_commit": args.launcher_public_freeze_commit,
        "CPU_cap_seconds_including_launcher_and_child": CPU_CAP,
        "whole_launch_wall_cap_seconds": WALL_CAP,
        "per_process_peak_RSS_cap_bytes": MEMORY_CAP,
        "command": cmd, "child_started": False, "retry": False,
        "source_values_admission": "BLOCKED_PROTECTED_REGISTRY_UNRESOLVED",
        "actual_process_termination_only_no_invented_external_tool_session": True}
    write_new(OUTPUT / "LAUNCH_INPUT_RECEIPT.json", receipt)
    child = None
    try:
        for signum in TERMINATION_SIGNALS:
            signal.signal(signum, terminate_into_cleanup)
        env = os.environ.copy()
        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                     "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
            env[name] = "1"
        with (OUTPUT / "STDOUT.txt").open("xb") as stdout, (OUTPUT / "STDERR.txt").open("xb") as stderr:
            launched = time.monotonic()
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, TERMINATION_SIGNALS)
            try:
                # Assign the child before a pending parent signal can run its
                # handler; the child restores the original mask before exec.
                child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, start_new_session=True,
                                         preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, old_mask))
                receipt["child_started"] = True
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            status, child_usage, timeout, killed = wait_child(child.pid, launched)
            child_wall = time.monotonic() - launched
            actual_return_code = os.waitstatus_to_exitcode(status)
            child.returncode = actual_return_code
            stdout.flush(); os.fsync(stdout.fileno())
            stderr.flush(); os.fsync(stderr.fileno())
        self_usage = resource.getrusage(resource.RUSAGE_SELF)
        child_cpu = child_usage.ru_utime + child_usage.ru_stime
        launcher_cpu = self_usage.ru_utime + self_usage.ru_stime
        child_rss = child_usage.ru_maxrss * 1024
        launcher_rss = self_usage.ru_maxrss * 1024
        outer_wall = time.monotonic() - WALL_STARTED
        cap_pass = (not timeout and child_cpu + launcher_cpu <= CPU_CAP
                    and child_wall <= WALL_CAP
                    and outer_wall <= WALL_CAP
                    and max(child_rss, launcher_rss) <= MEMORY_CAP)
        receipt.update({
            "status": ("PASS_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED" if cap_pass
                       else "FAIL_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED"),
            "actual_child_return_code": actual_return_code,
            "actual_child_exit_code": os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
            "actual_child_terminating_signal": os.WTERMSIG(status) if os.WIFSIGNALED(status) else None,
            "child_wall_timeout": timeout, "child_group_SIGKILL_after_timeout": killed,
            "whole_child_process_CPU_seconds_including_imports_and_close": child_cpu,
            "launcher_process_CPU_seconds_including_imports_before_receipt": launcher_cpu,
            "combined_process_CPU_seconds_before_receipt": child_cpu + launcher_cpu,
            "whole_child_wall_seconds_until_reaped": child_wall,
            "launcher_wall_seconds_since_module_start_before_receipt": outer_wall,
            "whole_child_peak_RSS_bytes": child_rss, "launcher_peak_RSS_bytes": launcher_rss,
            "resource_caps_satisfied": cap_pass,
            "resource_PASS_does_not_imply_complete_headers_or_source_values_admission": True})
        for path in (INITIAL / "EXECUTION_RECEIPT.json", INITIAL / "HEADER_RESULT.json"):
            if path.is_file():
                p = pin(path)
                require(p["bytes"] <= 2 * 1024 ** 2, "Child metadata receipt cap exceeded")
                data = json.loads(path.read_bytes())
                receipt[path.name] = {"pin": p, "original_status": data.get("status")}
        for path, expected in ((Path(__file__).resolve(), self_pin), (WORKER, worker_pin),
                               (SCOPE, scope_pin), (ADMISSION, admission_pin)):
            require(pin(path) == expected, "Pinned launch input changed during process")
        receipt["output_pins"] = [pin(OUTPUT / "STDOUT.txt"), pin(OUTPUT / "STDERR.txt")]
        return_code = 0 if cap_pass else 2
    except BaseException as error:
        protect_final_cleanup()
        if isinstance(error, ExternalTermination):
            receipt["external_launcher_termination_signal"] = error.signum
        # Preserve an actual started child without launching another attempt.
        if child is not None and child.returncode is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                status, used = None, None
                _, status, used = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
                receipt["actual_child_return_code"] = child.returncode
                receipt["whole_child_process_CPU_seconds_including_imports_and_close"] = used.ru_utime + used.ru_stime
                receipt["whole_child_peak_RSS_bytes"] = used.ru_maxrss * 1024
            except ChildProcessError:
                receipt["child_reaping_evidence_unavailable"] = True
        receipt.update(status="FAILED_CLOSED_OUTER_METER_NO_RETRY",
                       error_type=type(error).__name__, error=str(error), resource_caps_satisfied=False)
        return_code = 2
    finally:
        protect_final_cleanup()
        receipt["finished_UTC"] = utc()
        write_new(OUTPUT / "COMMAND_RESOURCES.json", receipt)
        os.close(directory_fd)
    print(json.dumps({"status": receipt["status"], "actual_child_return_code": receipt.get("actual_child_return_code"),
                      "resource_caps_satisfied": receipt.get("resource_caps_satisfied"), "retry": False}))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
