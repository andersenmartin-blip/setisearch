"""Linux stdlib supervisor; only direct guarded leaves, no qualification."""
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

DEFAULT_LIMITS = dict(child_wall_seconds=240, address_space_bytes=1024**3,
    cpu_seconds=240, per_file_bytes=128*1024**2, stdout_bytes=4*1024**2,
    stderr_bytes=4*1024**2, read_reserve_bytes=1024**3,
    artifact_storage_bytes=1536*1024**2, sample_interval_seconds=0.02)
PTRACE_CONT = 7
PTRACE_SETOPTIONS = 0x4200
PTRACE_O_TRACEEXEC = 0x10
PTRACE_O_TRACESECCOMP = 0x80
PTRACE_O_EXITKILL = 0x100000
PTRACE_EVENT_EXEC = 4
PTRACE_EVENT_SECCOMP = 7
CHUNK = 65536
_libc = ctypes.CDLL(None, use_errno=True)
_libc.ptrace.restype = ctypes.c_long
_libc.ptrace.argtypes = (ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)


def _ptrace(request, pid, data=0):
    if _libc.ptrace(request, pid, None, ctypes.c_void_p(data)) == -1:
        raise OSError(ctypes.get_errno(), "ptrace refused")


def _pinned_fd(path, expected):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("pinned executable must be canonical and absolute")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("pinned executable is not regular")
        digest = hashlib.sha256()
        while chunk := os.read(fd, CHUNK):
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns) or digest.hexdigest() != expected:
            raise ValueError("executable pin mismatch")
        return fd, dict(path=str(path), sha256=digest.hexdigest(), bytes=before.st_size,
                        device=before.st_dev, inode=before.st_ino)
    except BaseException:
        os.close(fd)
        raise


def _proc(pid):
    raw = {}
    for name in ("io", "status", "stat"):
        raw[name] = Path("/proc", str(pid), name).read_text()
    counters = {k: int(v.strip()) for k, v in
                (line.split(":", 1) for line in raw["io"].splitlines())}
    status = {k: v.strip() for k, v in
              (line.split(":", 1) for line in raw["status"].splitlines() if ":" in line)}
    return dict(raw=raw, io=counters, status=status)


def _storage(root):
    total = 0
    for path in root.rglob("*"):
        st = path.lstat()
        if stat.S_ISREG(st.st_mode):
            total += st.st_size
        elif not stat.S_ISDIR(st.st_mode):
            raise ValueError("nonregular artifact entry")
    return total


def run_leaf(argv, env, cwd, outputprefix, limits, global_deadline):
    """Return terminal direct-child custody, retaining output also on failure.

    Required pins in limits: python_path, python_sha256, guard_path,
    guard_sha256; artifact_root identifies the complete allocation's output
    tree. global_deadline is an absolute time.monotonic() deadline. There is
    no Popen polling/wait/communicate; WNOWAIT capture precedes exact wait4.
    IO/storage/output enforcement is sampled, with explicit overshoot failure.
    """
    limit = dict(DEFAULT_LIMITS, **limits)
    prefix, cwd = Path(outputprefix), Path(cwd)
    artifact_root = Path(limit["artifact_root"])
    if not prefix.is_absolute() or not cwd.is_absolute() or not artifact_root.is_absolute():
        raise ValueError("absolute paths required")
    if prefix.resolve() != prefix or artifact_root.resolve() != artifact_root:
        raise ValueError("canonical output paths required")
    if not cwd.is_dir() or not artifact_root.is_dir() or not prefix.parent.is_dir():
        raise ValueError("existing working/output directories required")
    if not prefix.is_relative_to(artifact_root):
        raise ValueError("output must belong to the counted artifact root")
    if not argv or str(Path(argv[0])) != limit["python_path"]:
        raise ValueError("argv must start with the pinned Python")
    if time.monotonic() >= global_deadline:
        raise ValueError("global allocation already expired")
    record = dict(schema="radio-direct-leaf-custody-v1", status="FAILED_CLOSED",
        argv=list(argv), cwd=str(cwd), limits=limit, runtime_qualified=False,
        scientific_authority=False, no_descendants_eligible=True,
        enforcement="sampled_IO_storage_output; kernel_AS_CPU_per_file; traced_exec",
        failures=[], proc_samples=[], trace_events=[], guard_status=None,
        terminal_proc=None, wait4=None, output={})
    handles, launch_fds, process = {}, [], None
    selector = selectors.DefaultSelector()
    killed = False
    terminal = None
    next_sample = 0.0
    status_bytes = bytearray()
    exec_admitted = 0
    traced_execs = 0
    samples_last = None

    def failure(reason):
        nonlocal killed
        if reason not in record["failures"]:
            record["failures"].append(reason)
        if process is not None and not killed:
            killed = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def drain():
        for key, _mask in selector.select(0):
            fd, kind = key.fd, key.data
            try:
                chunk = os.read(fd, CHUNK)
            except BlockingIOError:
                continue
            if not chunk:
                selector.unregister(fd)
                os.close(fd)
                continue
            if kind == "guard":
                status_bytes.extend(chunk)
                if len(status_bytes) > 4096:
                    failure("guard_status_overflow")
            else:
                stream, digest = handles[kind]
                stream.write(chunk)
                stream.flush()
                digest.update(chunk)
                info = record["output"][kind]
                info["bytes"] += len(chunk)
                if info["bytes"] > limit[kind + "_bytes"]:
                    failure(kind + "_limit_crossed")

    try:
        python_fd, record["python_pin"] = _pinned_fd(limit["python_path"], limit["python_sha256"])
        launch_fds.append(python_fd)
        guard_fd, record["guard_pin"] = _pinned_fd(limit["guard_path"], limit["guard_sha256"])
        launch_fds.append(guard_fd)
        for kind in ("stdout", "stderr"):
            path = prefix.with_name(prefix.name + "." + kind + ".bin")
            stream = path.open("xb", buffering=0)
            handles[kind] = (stream, hashlib.sha256())
            record["output"][kind] = dict(path=str(path), bytes=0, sha256=None)
        status_read, status_write = os.pipe2(os.O_CLOEXEC)
        launch_fds.extend((status_read, status_write))
        command = [str(limit["guard_path"]), "--python-fd", str(python_fd),
            "--status-fd", str(status_write), "--address-space", str(limit["address_space_bytes"]),
            "--cpu-seconds", str(limit["cpu_seconds"]), "--file-bytes", str(limit["per_file_bytes"]),
            "--guard-fd", str(guard_fd), "--", *argv]
        record["started_monotonic"] = time.monotonic()
        deadline = min(record["started_monotonic"] + limit["child_wall_seconds"], global_deadline)
        record["absolute_deadline"] = deadline
        process = subprocess.Popen(command, executable="/proc/self/fd/" + str(guard_fd),
            env=dict(env), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            pass_fds=(python_fd, guard_fd, status_write), close_fds=True)
        record["pid"] = process.pid
        # Parent pins remain open only until the guarded launch exists.
        for fd in (python_fd, guard_fd, status_write):
            os.close(fd)
            launch_fds.remove(fd)
        for stream, kind in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            fd = os.dup(stream.fileno())
            stream.close()
            os.set_blocking(fd, False)
            selector.register(fd, selectors.EVENT_READ, kind)
        os.set_blocking(status_read, False)
        selector.register(status_read, selectors.EVENT_READ, "guard")
        launch_fds.remove(status_read)
        while terminal is None:
            drain()
            now = time.monotonic()
            if now >= deadline:
                failure("leaf_wall_deadline")
            observed = os.waitid(os.P_PID, process.pid,
                os.WEXITED | os.WSTOPPED | os.WNOHANG | os.WNOWAIT)
            if observed is not None:
                if observed.si_code in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED):
                    terminal = observed
                    break
                # Consume only a nonterminal tracing stop, never an exit.
                stopped = os.waitid(os.P_PID, process.pid, os.WSTOPPED | os.WNOHANG)
                if stopped is not None:
                    event = stopped.si_status >> 8
                    sig = stopped.si_status & 255
                    record["trace_events"].append(dict(event=event, signal=sig,
                        monotonic=time.monotonic()))
                    if len(record["trace_events"]) == 1 and sig == signal.SIGSTOP and event == 0:
                        _ptrace(PTRACE_SETOPTIONS, process.pid,
                            PTRACE_O_TRACEEXEC | PTRACE_O_TRACESECCOMP | PTRACE_O_EXITKILL)
                        _ptrace(PTRACE_CONT, process.pid)
                    elif event == PTRACE_EVENT_SECCOMP:
                        drain()
                        if exec_admitted or killed:
                            failure("additional_exec_refused")
                        else:
                            try:
                                guard = json.loads(status_bytes)
                                required = dict(schema="radio-leaf-guard-v1", no_new_privs=1,
                                    seccomp_mode=2, descendants_denied=True, sockets_denied=True,
                                    async_io_denied=True, exec_trace_required=True)
                                if guard != required:
                                    raise ValueError("wrong guard readiness")
                                record["guard_status"] = guard
                                proc = _proc(process.pid)
                                if proc["status"].get("NoNewPrivs") != "1" or proc["status"].get("Seccomp") != "2":
                                    raise ValueError("kernel filter readiness missing")
                                record["preexec_proc"] = proc
                                exec_admitted = 1
                                _ptrace(PTRACE_CONT, process.pid)
                            except Exception:
                                failure("guard_admission_failed")
                    elif event == PTRACE_EVENT_EXEC:
                        traced_execs += 1
                        if exec_admitted != 1 or traced_execs != 1:
                            failure("exec_event_mismatch")
                        else:
                            _ptrace(PTRACE_CONT, process.pid)
                    elif sig == signal.SIGTRAP:
                        failure("unexpected_trace_stop")
                    else:
                        _ptrace(PTRACE_CONT, process.pid, sig)
            if now >= next_sample and terminal is None:
                try:
                    sample = _proc(process.pid)
                    sample["monotonic"] = now
                    io = sample["io"]
                    if samples_last is not None and any(io[k] < samples_last[k] for k in io):
                        failure("nonmonotone_proc_io")
                    samples_last = io
                    record["proc_samples"].append(sample)
                    if io["rchar"] > limit["read_reserve_bytes"] or io["read_bytes"] > limit["read_reserve_bytes"]:
                        failure("sampled_read_reserve_crossed")
                    if _storage(artifact_root) > limit["artifact_storage_bytes"]:
                        failure("sampled_artifact_storage_crossed")
                except (FileNotFoundError, ProcessLookupError):
                    pass  # A concurrent exit is captured under WNOWAIT next.
                except Exception as exc:
                    failure("proc_or_storage_sample_" + type(exc).__name__)
                next_sample = now + limit["sample_interval_seconds"]
            selector.select(min(limit["sample_interval_seconds"], max(0, deadline-now)))
        record["terminal_observed_monotonic"] = time.monotonic()
        try:
            record["terminal_proc"] = _proc(process.pid)
            final_io = record["terminal_proc"]["io"]
            if samples_last is not None and any(final_io[k] < samples_last[k] for k in final_io):
                failure("nonmonotone_terminal_proc_io")
            if final_io["rchar"] > limit["read_reserve_bytes"] or final_io["read_bytes"] > limit["read_reserve_bytes"]:
                failure("terminal_read_reserve_crossed")
        except Exception as exc:
            failure("terminal_proc_unavailable_" + type(exc).__name__)
        pid, status, usage = os.wait4(process.pid, 0)
        process.returncode = os.waitstatus_to_exitcode(status)
        record["wait4"] = dict(pid=pid, raw_status=status, returncode=process.returncode,
            user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
            maxrss_kib=usage.ru_maxrss, maxrss_bytes=usage.ru_maxrss*1024,
            inblock=usage.ru_inblock, oublock=usage.ru_oublock,
            voluntary_switches=usage.ru_nvcsw, involuntary_switches=usage.ru_nivcsw,
            exact_direct_child_wait4=True)
        while selector.get_map():
            drain()
        record["ended_monotonic"] = time.monotonic()
        record["complete_direct_leaf_seconds"] = record["ended_monotonic"] - record["started_monotonic"]
        record["admitted_exec_count"] = exec_admitted
        record["completed_exec_events"] = traced_execs
        if process.returncode != 0:
            failure("nonzero_leaf_exit")
        if exec_admitted != 1 or traced_execs != 1 or record["guard_status"] is None:
            failure("guarded_exec_not_complete")
        if _storage(artifact_root) > limit["artifact_storage_bytes"]:
            failure("terminal_artifact_storage_crossed")
        if not record["failures"]:
            record["status"] = "GUARDED_LEAF_COMPLETED"
    except BaseException as exc:
        failure("supervisor_" + type(exc).__name__)
        # Exception cleanup still owns terminal /proc -> wait4, never Popen.wait.
        if process is not None and process.returncode is None:
            try:
                while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    drain()
                    selector.select(0.01)
                try:
                    record["terminal_proc"] = _proc(process.pid)
                except Exception as terminal_exc:
                    record["failures"].append("terminal_proc_unavailable_" + type(terminal_exc).__name__)
                pid, status, usage = os.wait4(process.pid, 0)
                process.returncode = os.waitstatus_to_exitcode(status)
                record["wait4"] = dict(pid=pid, raw_status=status, returncode=process.returncode,
                    user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
                    maxrss_kib=usage.ru_maxrss, maxrss_bytes=usage.ru_maxrss*1024,
                    inblock=usage.ru_inblock, oublock=usage.ru_oublock,
                    exact_direct_child_wait4=True)
                while selector.get_map():
                    drain()
            except BaseException as cleanup_exc:
                record["failures"].append("terminal_cleanup_" + type(cleanup_exc).__name__)
    finally:
        for fd in launch_fds:
            os.close(fd)
        for key in list(selector.get_map().values()):
            selector.unregister(key.fd)
            os.close(key.fd)
        selector.close()
        for kind, (stream, digest) in handles.items():
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            record["output"][kind]["sha256"] = digest.hexdigest()
        record.setdefault("ended_monotonic", time.monotonic())
        if "started_monotonic" in record:
            record["complete_direct_leaf_seconds"] = record["ended_monotonic"]-record["started_monotonic"]
        destination = prefix.with_name(prefix.name + ".custody.json")
        with destination.open("x") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return record
