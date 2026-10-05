"""Linux stdlib two-phase guarded supervisor; direct-child observations only."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

DEFAULT_LIMITS = dict(child_wall_seconds=120, address_space_bytes=1024**3,
    cpu_seconds=100, per_file_bytes=128*1024**2, stdout_bytes=2*1024**2,
    stderr_bytes=2*1024**2, read_reserve_bytes=512*1024**2,
    artifact_bytes=1536*1024**2, pin_read_budget_bytes=32*1024**2,
    proc_metadata_budget_bytes=32*1024**2,
    sample_interval_seconds=0.02, cleanup_seconds=10)
LIMIT_KEYS = frozenset(DEFAULT_LIMITS) | frozenset(
    name+suffix for name in ("python", "guard", "exec_seal", "phase2")
    for suffix in ("_path", "_sha256")) | {"artifact_root"}
CHUNK = 65536
MONOTONE_IO = ("rchar", "wchar", "syscr", "syscw", "read_bytes", "write_bytes")
PHASE2_MARKER = b"RADIO_PHASE2_ACTIVATED "


def _pinned_fd(path, expected, read_budget, charge):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("pinned file must be canonical and absolute")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("pinned file is not regular")
        if before.st_size > read_budget:
            raise ValueError("held-file pin read budget exceeded before read")
        digest = hashlib.sha256()
        charged = 0
        while charged < read_budget:
            chunk = os.read(fd, min(CHUNK, read_budget-charged))
            if not chunk:
                break
            charged += len(chunk)
            charge(len(chunk))
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns) or digest.hexdigest() != expected:
            raise ValueError("file pin mismatch")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd, dict(path=str(path), sha256=digest.hexdigest(), bytes=before.st_size,
                        device=before.st_dev, inode=before.st_ino, read_charge_bytes=charged)
    except BaseException:
        os.close(fd)
        raise


def _proc(pid, read_metadata):
    self_status = read_metadata(Path("/proc/self/status"), child=False)
    self_pid = int(next(line.split(":",1)[1] for line in self_status.splitlines()
                        if line.startswith("Pid:")))
    if self_pid != os.getpid():
        raise FileNotFoundError("proc mount and child wait PID namespaces differ")
    raw = {name: read_metadata(Path("/proc", str(pid), name), child=True)
           for name in ("io", "status", "stat")}
    counters = {k: int(v.strip()) for k, v in
                (line.split(":", 1) for line in raw["io"].splitlines())}
    status = {k: v.strip() for k, v in
              (line.split(":", 1) for line in raw["status"].splitlines() if ":" in line)}
    return dict(available=True, raw=raw, io=counters, status=status,
                proc_pid_view=pid, identity_scope="local_pid_view_observation")


def _storage(root, deadline):
    total = 0
    for path in root.rglob("*"):
        if time.monotonic() >= deadline:
            raise TimeoutError("storage sample deadline")
        st = path.lstat()
        if stat.S_ISREG(st.st_mode):
            total += st.st_size
        elif not stat.S_ISDIR(st.st_mode):
            raise ValueError("nonregular artifact entry")
    return total


def _wrapped_argv(argv, limits):
    options, index = [], 1
    while index < len(argv) and argv[index] in ("-I", "-B", "-S", "-s", "-E", "-u"):
        options.append(argv[index])
        index += 1
    if "-I" not in options or "-B" not in options or index >= len(argv):
        raise ValueError("frozen isolated Python driver arguments required")
    if argv[index] == "-c" and index+1 < len(argv):
        mode, payload, remaining = "code", argv[index+1], argv[index+2:]
    elif not argv[index].startswith("-"):
        mode, payload, remaining = "path", argv[index], argv[index+1:]
    else:
        raise ValueError("unsupported Python driver")
    return [argv[0], *options, limits["phase2_path"], limits["exec_seal_path"],
            limits["exec_seal_sha256"], mode, payload, *remaining]


def run_leaf(argv, env, cwd, outputprefix, limits, global_deadline):
    """Wrap plain pinned Python argv; return exact wait4 and retained streams.

    Required pins: python_path/sha256, guard_path/sha256,
    exec_seal_path/sha256, phase2_path/sha256; artifact_root counts all output.
    global_deadline is absolute monotonic time for active execution. The root
    separately reserves its finalization interval. Proc counters are candid
    observations, and can be unavailable in mismatched PID namespaces.
    No Popen wait/poll/communicate is used. Missing proc counters are never zero.
    """
    if not isinstance(limits, dict) or frozenset(limits) != LIMIT_KEYS:
        raise ValueError("exact supervisor limit keys required; no ignored/default budgets")
    limit = dict(limits)
    if any(type(limit[k]) not in (int, float) or limit[k] <= 0 for k in DEFAULT_LIMITS):
        raise ValueError("positive explicit supervisor budgets required")
    if any(type(limit[k]) is not int for k in DEFAULT_LIMITS
           if k not in ("child_wall_seconds", "sample_interval_seconds", "cleanup_seconds")):
        raise ValueError("integer byte/CPU ceilings required")
    prefix, cwd, artifact_root = Path(outputprefix), Path(cwd), Path(limit["artifact_root"])
    if not all(p.is_absolute() and p.resolve() == p for p in (prefix, cwd, artifact_root)):
        raise ValueError("canonical absolute paths required")
    if not cwd.is_dir() or not artifact_root.is_dir() or not prefix.parent.is_dir():
        raise ValueError("existing working/output directories required")
    if not prefix.is_relative_to(artifact_root) or not argv or argv[0] != limit["python_path"]:
        raise ValueError("output root or pinned Python argv mismatch")
    if time.monotonic() >= global_deadline:
        raise ValueError("global active allocation already expired")
    record = dict(schema="radio-direct-leaf-custody-v1", status="FAILED_CLOSED",
        argv=list(argv), cwd=str(cwd), limits=limit, runtime_qualified=False,
        scientific_authority=False, full_native_io_custody=False,
        no_descendants_eligible=True, failures=[], observation_limits=[],
        proc_samples=[], terminal_proc=None, guard_status=None, phase2_status=None,
        wait4=None, output={}, child_dispatches=0, child_reaped=False,
        child_exit_code=None, guarded_leaf=False, failure=None,
        wait4_direct_child_ru_maxrss_bytes=None, pin_read_charge_bytes=0,
        proc_metadata_read_charge_bytes=0, proc_child_metadata_read_charge_bytes=0,
        opaque_child_read_reserve_bytes=limit["read_reserve_bytes"],
        enforcement="kernel_AS_CPU_per_file; two_phase_seccomp; sampled_IO_storage_output")
    handles, launch_fds, process = {}, [], None
    selector = selectors.DefaultSelector()
    killed, terminal = False, None
    guard_bytes = bytearray()
    stderr_head = bytearray()
    next_sample, previous_io = 0.0, None
    io_available = True
    cleanup_deadline = global_deadline + limit["cleanup_seconds"]

    def read_metadata(path, child):
        remaining = limit["proc_metadata_budget_bytes"]-record["proc_metadata_read_charge_bytes"]
        if remaining <= 0:
            raise ValueError("proc metadata read budget exhausted")
        cap = min(65536, remaining)
        with path.open("rb") as stream:
            raw = stream.read(cap)
        record["proc_metadata_read_charge_bytes"] += len(raw)
        if child:
            record["proc_child_metadata_read_charge_bytes"] += len(raw)
        if len(raw) == cap:
            raise ValueError("proc metadata file reached bounded read capacity")
        return raw.decode("utf-8")

    def fail(reason):
        nonlocal killed
        if reason not in record["failures"]:
            record["failures"].append(reason)
        if process is not None and process.returncode is None and not killed:
            killed = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def drain(best_effort=False):
        for key, _mask in selector.select(0):
            fd, kind = key.fd, key.data
            try:
                chunk = os.read(fd, CHUNK)
                if not chunk:
                    selector.unregister(fd)
                    os.close(fd)
                    continue
                if kind == "guard":
                    guard_bytes.extend(chunk)
                    if len(guard_bytes) > 4096:
                        fail("guard_status_overflow")
                else:
                    stream, digest = handles[kind]
                    info = record["output"][kind]
                    info["received_bytes"] += len(chunk)
                    if kind == "stderr" and len(stderr_head) < 4096:
                        stderr_head.extend(chunk[:4096-len(stderr_head)])
                    offset = 0
                    while offset < len(chunk):
                        written = stream.write(memoryview(chunk)[offset:])
                        if not written or written > len(chunk)-offset:
                            raise OSError("invalid/short stream write contract")
                        digest.update(memoryview(chunk)[offset:offset+written])
                        info["bytes"] += written
                        offset += written
                    if info["received_bytes"] > limit[kind+"_bytes"]:
                        fail(kind+"_limit_crossed")
            except BlockingIOError:
                pass
            except Exception as exc:
                fail("stream_"+kind+"_"+type(exc).__name__)
                if not best_effort:
                    raise

    def proc_observation(terminal=False):
        nonlocal io_available, previous_io
        try:
            sample = _proc(process.pid, read_metadata)
            sample["monotonic"] = time.monotonic()
            counters = sample["io"]
            if previous_io is not None and any(counters[k] < previous_io[k] for k in MONOTONE_IO):
                fail("nonmonotone_proc_io")
            previous_io = counters
            if counters["rchar"] > limit["read_reserve_bytes"] or counters["read_bytes"] > limit["read_reserve_bytes"]:
                fail("observed_read_reserve_crossed")
            return sample
        except (FileNotFoundError, ProcessLookupError, PermissionError) as exc:
            io_available = False
            note = "proc_io_unavailable_local_pid_view_"+type(exc).__name__
            if note not in record["observation_limits"]:
                record["observation_limits"].append(note)
            return dict(available=False, local_wait_pid=process.pid, error=type(exc).__name__,
                        terminal=terminal, no_substituted_counters=True)

    def terminal_capture_and_reap():
        record["terminal_observed_monotonic"] = time.monotonic()
        try:
            record["terminal_proc"] = proc_observation(terminal=True)
        except BaseException as exc:
            record["terminal_proc"] = dict(available=False, error=type(exc).__name__,
                                          no_substituted_counters=True)
            record["observation_limits"].append("terminal_proc_capture_failed_"+type(exc).__name__)
        pid, status, usage = os.wait4(process.pid, 0)
        process.returncode = os.waitstatus_to_exitcode(status)
        record["wait4"] = dict(pid=pid, raw_status=status, returncode=process.returncode,
            user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
            maxrss_kib=usage.ru_maxrss, maxrss_bytes=usage.ru_maxrss*1024,
            inblock=usage.ru_inblock, oublock=usage.ru_oublock,
            voluntary_switches=usage.ru_nvcsw, involuntary_switches=usage.ru_nivcsw,
            exact_direct_child_wait4=True)
        record["child_exit_code"] = process.returncode
        record["child_reaped"] = True
        record["wait4_direct_child_ru_maxrss_bytes"] = usage.ru_maxrss*1024

    try:
        pinned = {}
        def pin_charge(count):
            record["pin_read_charge_bytes"] += count
        for name in ("python", "guard", "exec_seal", "phase2"):
            fd, pin = _pinned_fd(limit[name+"_path"], limit[name+"_sha256"],
                limit["pin_read_budget_bytes"]-record["pin_read_charge_bytes"], pin_charge)
            launch_fds.append(fd)
            pinned[name] = fd
            record[name+"_pin"] = pin
        for kind in ("stdout", "stderr"):
            path = prefix.with_name(prefix.name+"."+kind+".bin")
            handles[kind] = (path.open("xb", buffering=0), hashlib.sha256())
            record["output"][kind] = dict(path=str(path), bytes=0, received_bytes=0, sha256=None)
        status_read, status_write = os.pipe2(os.O_CLOEXEC)
        launch_fds.extend((status_read, status_write))
        wrapped = _wrapped_argv(argv, limit)
        record["wrapped_python_argv"] = wrapped
        command = [limit["guard_path"], "--python-fd", str(pinned["python"]),
            "--status-fd", str(status_write), "--address-space", str(limit["address_space_bytes"]),
            "--cpu-seconds", str(limit["cpu_seconds"]), "--file-bytes", str(limit["per_file_bytes"]),
            "--guard-fd", str(pinned["guard"]), "--", *wrapped]
        record["started_monotonic"] = time.monotonic()
        deadline = min(record["started_monotonic"]+limit["child_wall_seconds"], global_deadline)
        record["absolute_deadline"] = deadline
        cleanup_deadline = min(deadline+limit["cleanup_seconds"], global_deadline+limit["cleanup_seconds"])
        process = subprocess.Popen(command, executable="/proc/self/fd/"+str(pinned["guard"]),
            env=dict(env), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            pass_fds=(pinned["python"], pinned["guard"], status_write), close_fds=True)
        record["pid"] = process.pid
        record["child_dispatches"] = 1
        for fd in list(launch_fds):
            if fd != status_read:
                os.close(fd)
                launch_fds.remove(fd)
        for stream, kind in ((process.stdout,"stdout"),(process.stderr,"stderr")):
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
                fail("leaf_wall_deadline")
            terminal = os.waitid(os.P_PID, process.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT)
            if terminal is not None:
                break
            if now >= cleanup_deadline:
                raise TimeoutError("terminal observation deadline")
            if now >= next_sample:
                if io_available:
                    record["proc_samples"].append(proc_observation())
                if _storage(artifact_root, cleanup_deadline) > limit["artifact_bytes"]:
                    fail("sampled_artifact_storage_crossed")
                next_sample = now+limit["sample_interval_seconds"]
            selector.select(min(limit["sample_interval_seconds"], max(0, deadline-now)))
        terminal_capture_and_reap()
        while selector.get_map() and time.monotonic() < cleanup_deadline:
            drain()
            selector.select(0.001)
        if selector.get_map():
            fail("terminal_stream_drain_incomplete")
        try:
            guard = json.loads(guard_bytes)
            required = dict(schema="radio-leaf-guard-v1", no_new_privs=1, seccomp_mode=2,
                descendants_denied=True, sockets_denied=True, async_io_denied=True, phase2_required=True)
            if guard != required:
                raise ValueError("phase1 readiness mismatch")
            record["guard_status"] = guard
            first_line = bytes(stderr_head).split(b"\n",1)[0]
            if not first_line.startswith(PHASE2_MARKER):
                raise ValueError("phase2 marker missing")
            phase2 = json.loads(first_line[len(PHASE2_MARKER):])
            if phase2 != dict(schema="radio-leaf-phase2-v1", no_new_privs=1,
                seccomp_mode=2, exec_denied=True, scientific_imports_started=False):
                raise ValueError("phase2 readiness mismatch")
            record["phase2_status"] = phase2
            record["guarded_leaf"] = True
        except Exception as exc:
            fail("two_phase_guard_admission_"+type(exc).__name__)
        if process.returncode != 0:
            fail("nonzero_leaf_exit")
        if _storage(artifact_root, cleanup_deadline) > limit["artifact_bytes"]:
            fail("terminal_artifact_storage_crossed")
    except BaseException as exc:
        fail("supervisor_"+type(exc).__name__)
        if process is not None and process.returncode is None:
            try:
                while os.waitid(os.P_PID, process.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None:
                    drain(best_effort=True)
                    if time.monotonic() >= cleanup_deadline:
                        raise TimeoutError("cleanup terminal deadline")
                    selector.select(0.005)
                # No draining failure can bypass this mandatory wait4 path.
                terminal_capture_and_reap()
            except BaseException as cleanup_exc:
                record["failures"].append("terminal_cleanup_"+type(cleanup_exc).__name__)
            while selector.get_map() and time.monotonic() < cleanup_deadline:
                drain(best_effort=True)
                selector.select(0.001)
    finally:
        for fd in launch_fds:
            try:
                os.close(fd)
            except OSError as exc:
                record["failures"].append("launch_fd_close_"+type(exc).__name__)
        for key in list(selector.get_map().values()):
            try:
                selector.unregister(key.fd)
                os.close(key.fd)
            except OSError as exc:
                record["failures"].append("stream_fd_close_"+type(exc).__name__)
        selector.close()
        for kind,(stream,digest) in handles.items():
            try:
                stream.flush()
                os.fsync(stream.fileno())
            except OSError as exc:
                record["failures"].append("stream_finalize_"+kind+"_"+type(exc).__name__)
            finally:
                try:
                    stream.close()
                except OSError as exc:
                    record["failures"].append("stream_close_"+kind+"_"+type(exc).__name__)
                record["output"][kind]["sha256"] = digest.hexdigest()
        record["ended_monotonic"] = time.monotonic()
        if "started_monotonic" in record:
            record["complete_direct_leaf_seconds"] = record["ended_monotonic"]-record["started_monotonic"]
        if not record["failures"] and record["child_reaped"] and record["guarded_leaf"]:
            record["status"] = "GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY"
        record["failure"] = None if not record["failures"] else ";".join(record["failures"])
        destination = prefix.with_name(prefix.name+".custody.json")
        try:
            payload = (json.dumps(record,indent=2,sort_keys=True)+"\n").encode()
            if _storage(artifact_root, cleanup_deadline)+len(payload) > limit["artifact_bytes"]:
                record["failures"].append("custody_storage_reserve_crossed")
                record["status"] = "FAILED_CLOSED"
                record["failure"] = ";".join(record["failures"])
                payload = (json.dumps(record,indent=2,sort_keys=True)+"\n").encode()
            with destination.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception as exc:
            record["failures"].append("custody_persistence_"+type(exc).__name__)
            record["status"] = "FAILED_CLOSED"
            record["failure"] = ";".join(record["failures"])
    return record
