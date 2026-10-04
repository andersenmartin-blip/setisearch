"""One bounded metadata-only preparation; never a collector invocation."""

import hashlib
import json
import os
import signal
import stat
import sys
import time

ROOT = "/workspace/scratch/d804553c0e89/setisearch-status-20261004"
OUT_DIR = ROOT + "/results_radio_runtime_capture_preparation_20261004b"
OUT_PATH = OUT_DIR + "/runtime-preread-pins.json"
PLAN_PATH = ROOT + "/results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json"
OLD_PATH = ROOT + "/results_radio_runtime_capture_preparation_20261004a/runtime-preread-pins.json"
PLAN_SHA256 = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
IDENTITY = "e3d5aae494ef041c668a9fbec11edc2ac821a0e27bef15588181d166e125736c"
BASE = "/opt/codex/runtimes/codex-primary-runtime/dependencies/python"
STDLIB = BASE + "/lib/python3.12"
PYTHON_PATH = BASE + "/bin/python3.12"
METADATA = STDLIB + "/site-packages/numpy-2.3.5.dist-info"
LOADER_NAMES = (
    "ld-linux-x86-64.so.2", "libpthread.so.0", "libdl.so.2", "libutil.so.1",
    "libm.so.6", "librt.so.1", "libc.so.6", "libgcc_s.so.1",
    "libstdc++.so.6", "libz.so.1",
)
LIMITS = {
    "total_regular_content_bytes": 64 * 1024 * 1024,
    "regular_file_bytes": 64 * 1024 * 1024,
    "selected_file_count": 1024,
    "regular_content_file_count": 1024,
    "enumerated_entries": 16384,
    "entries_per_directory": 2048,
    "held_directories": 512,
    "enumeration_depth": 32,
    "path_utf8_bytes": 4096,
    "explicit_symlink_resolutions": 64,
    "output_bytes": 1024 * 1024,
    "post_bootstrap_wall_seconds": 45,
    "read_chunk_bytes": 1024 * 1024,
}
KEYS = ("st_dev", "st_ino", "st_mode", "st_size", "st_nlink", "st_mtime_ns", "st_ctime_ns")
STATE = {"regular_content_bytes": 0, "selected_content_bytes": 0,
         "enumerated_entries": 0, "symlink_resolutions": 0,
         "regular_content_files": 0, "selected_file_count": 0}
SYMLINK_BINDINGS = []
START = time.monotonic()


class PrereadError(Exception):
    pass


def check_time():
    if time.monotonic() - START >= LIMITS["post_bootstrap_wall_seconds"]:
        raise PrereadError("post-bootstrap wall deadline exceeded")


def alarm_handler(signum, frame):
    raise PrereadError("post-bootstrap SIGALRM deadline exceeded")


def identity(st):
    return tuple(getattr(st, key) for key in KEYS)


def st_object(st):
    return dict(zip(KEYS, identity(st)))


def checked_path(path):
    if not isinstance(path, str) or not path.startswith("/") or os.path.normpath(path) != path:
        raise PrereadError("non-canonical absolute path")
    if len(path.encode("utf-8")) > LIMITS["path_utf8_bytes"] or "\x00" in path:
        raise PrereadError("path length or NUL rejected")
    return path


class Guard:
    """Hold no-follow ancestors and compare descriptor/name identities."""

    def __init__(self):
        self.directories = {}

    def directory(self, path):
        checked_path(path)
        check_time()
        if path in self.directories:
            return self.directories[path][0]
        if len(self.directories) >= LIMITS["held_directories"]:
            raise PrereadError("held directory count exceeded")
        if path == "/":
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            named = os.stat(path, follow_symlinks=False)
        else:
            parent = self.directory(os.path.dirname(path))
            name = os.path.basename(path)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode):
                raise PrereadError("non-directory or symlink ancestor: " + path)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        held = os.fstat(fd)
        if not stat.S_ISDIR(held.st_mode) or identity(held) != identity(named):
            os.close(fd)
            raise PrereadError("ancestor descriptor/name mismatch: " + path)
        if len(self.directories) >= LIMITS["held_directories"]:
            os.close(fd)
            raise PrereadError("held directory count exceeded after ancestor descent")
        self.directories[path] = (fd, held)
        return fd

    def stat_path(self, path):
        checked_path(path)
        parent = self.directory(os.path.dirname(path))
        return os.stat(os.path.basename(path), dir_fd=parent, follow_symlinks=False)

    def verify(self):
        for path, (fd, before) in self.directories.items():
            check_time()
            if path == "/":
                named = os.stat(path, follow_symlinks=False)
            else:
                parent = self.directories[os.path.dirname(path)][0]
                named = os.stat(os.path.basename(path), dir_fd=parent, follow_symlinks=False)
            if identity(before) != identity(os.fstat(fd)) or identity(before) != identity(named):
                raise PrereadError("ancestor changed: " + path)

    def provenance(self):
        return [{"path": path, **st_object(st)} for path, (_, st) in sorted(self.directories.items())]

    def close(self):
        for fd, _ in reversed(list(self.directories.values())):
            os.close(fd)
        self.directories.clear()


def resolve(path):
    """Explicit, bounded metadata-only canonicalization for named aliases."""
    checked_path(path)
    components = path.split("/")[1:]
    resolved = "/"
    while components:
        check_time()
        name = components.pop(0)
        if name in ("", "."):
            continue
        if name == "..":
            resolved = os.path.dirname(resolved)
            continue
        candidate = os.path.join(resolved, name)
        checked_path(candidate)
        before = os.lstat(candidate)
        if stat.S_ISLNK(before.st_mode):
            STATE["symlink_resolutions"] += 1
            if STATE["symlink_resolutions"] > LIMITS["explicit_symlink_resolutions"]:
                raise PrereadError("symlink resolution cap exceeded")
            target = os.readlink(candidate)
            if identity(before) != identity(os.lstat(candidate)):
                raise PrereadError("alias changed during resolution: " + candidate)
            SYMLINK_BINDINGS.append({"path": candidate, "target": target, **st_object(before)})
            if len(target.encode("utf-8")) > LIMITS["path_utf8_bytes"]:
                raise PrereadError("symlink target length exceeded")
            components = target.split("/") + components
            if target.startswith("/"):
                resolved = "/"
        else:
            resolved = candidate
    return checked_path(resolved)


def read_regular(guard, path, role, retain=False, selected=False):
    checked_path(path)
    check_time()
    if STATE["regular_content_files"] >= LIMITS["regular_content_file_count"]:
        raise PrereadError("total regular content file count exceeded")
    parent = guard.directory(os.path.dirname(path))
    name = os.path.basename(path)
    named_before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISREG(named_before.st_mode):
        raise PrereadError("named input is not a regular file: " + path)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if identity(before) != identity(named_before) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise PrereadError("regular sole-link descriptor/name identity rejected: " + path)
        permissions = format(before.st_mode & 0o7777, "04o")
        if permissions not in ("0644", "0755"):
            raise PrereadError("selected file mode rejected: " + path)
        if before.st_size < 0 or before.st_size > LIMITS["regular_file_bytes"]:
            raise PrereadError("regular file size cap exceeded: " + path)
        if STATE["regular_content_bytes"] + before.st_size > LIMITS["total_regular_content_bytes"]:
            raise PrereadError("total regular content cap would be exceeded: " + path)
        digest = hashlib.sha256()
        chunks = [] if retain else None
        remaining = before.st_size
        while remaining:
            check_time()
            raw = os.read(fd, min(LIMITS["read_chunk_bytes"], remaining))
            if not raw:
                raise PrereadError("file ended before frozen length: " + path)
            STATE["regular_content_bytes"] += len(raw)
            if selected:
                STATE["selected_content_bytes"] += len(raw)
            digest.update(raw)
            if retain:
                chunks.append(raw)
            remaining -= len(raw)
        after = os.fstat(fd)
        named_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if identity(before) != identity(after) or identity(before) != identity(named_after):
            raise PrereadError("file changed during hash pass: " + path)
        STATE["regular_content_files"] += 1
        if selected:
            STATE["selected_file_count"] += 1
        record = {"path": path, "role": role, "bytes": before.st_size,
                  "sha256": digest.hexdigest(),
                  "mode": "100755" if permissions == "0755" else "100644",
                  "filesystem_mode": permissions}
        return record, b"".join(chunks) if retain else None, st_object(before)
    finally:
        os.close(fd)


def auxiliary(path):
    guard = Guard()
    try:
        record, raw, st = read_regular(guard, path, "preparation-input", retain=True)
        guard.verify()
        return record, raw, {"file": st, "ancestors": guard.provenance()}
    finally:
        guard.close()


def entries(guard, directory):
    fd = guard.directory(directory)
    rows = []
    with os.scandir(fd) as iterator:
        for row in iterator:
            check_time()
            STATE["enumerated_entries"] += 1
            if STATE["enumerated_entries"] > LIMITS["enumerated_entries"]:
                raise PrereadError("total enumeration entry cap exceeded")
            rows.append(row.name)
            if len(rows) > LIMITS["entries_per_directory"]:
                raise PrereadError("per-directory enumeration entry cap exceeded")
    return sorted(rows)


def select_stdlib(guard, selected, cohort, directory, depth=0):
    if depth > LIMITS["enumeration_depth"]:
        raise PrereadError("stdlib enumeration depth exceeded")
    for name in entries(guard, directory):
        path = checked_path(os.path.join(directory, name))
        st = guard.stat_path(path)
        if stat.S_ISLNK(st.st_mode):
            continue
        if stat.S_ISDIR(st.st_mode):
            if name not in ("site-packages", "__pycache__"):
                select_stdlib(guard, selected, cohort, path, depth + 1)
        elif stat.S_ISREG(st.st_mode) and not name.endswith((".pyc", ".pyo")):
            selected[path] = "elf" if name.endswith(".so") else "runtime"
            cohort.add(path)
            if len(selected) > LIMITS["selected_file_count"]:
                raise PrereadError("selected file count exceeded")


def path_existence(path):
    checked_path(path)
    check_time()
    try:
        observed = os.lstat(path)
    except FileNotFoundError:
        return {"path": path, "exists": False, "operation": "lstat", "content_opened": False,
                "result": "ENOENT: named path or an ancestor absent"}
    return {"path": path, "exists": True, "operation": "lstat", "content_opened": False,
            "is_symlink": stat.S_ISLNK(observed.st_mode), **st_object(observed)}


def main():
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, LIMITS["post_bootstrap_wall_seconds"])
    plan_record, plan_raw, plan_provenance = auxiliary(PLAN_PATH)
    if plan_record["sha256"] != PLAN_SHA256:
        raise PrereadError("original materialization plan SHA256 mismatch")
    plan = json.loads(plan_raw)
    old_record, old_raw, old_provenance = auxiliary(OLD_PATH)
    old = json.loads(old_raw)
    guard = Guard()
    try:
        selected = {PYTHON_PATH: "elf"}
        cohort = set()
        select_stdlib(guard, selected, cohort, STDLIB)
        aliases = []
        for name in LOADER_NAMES:
            alias = "/usr/lib/x86_64-linux-gnu/" + name
            target = resolve(alias)
            aliases.append({"requested_path": alias, "resolved_path": target})
            selected[target] = "elf"
        for name in ("METADATA", "WHEEL", "RECORD"):
            selected[METADATA + "/" + name] = "runtime"
        release_path = resolve("/etc/os-release")
        for path in ("/etc/ld.so.cache", "/etc/ld.so.conf", release_path):
            selected[path] = "input"
        for name in entries(guard, "/etc/ld.so.conf.d"):
            if name.endswith(".conf"):
                selected[resolve("/etc/ld.so.conf.d/" + name)] = "input"
        if len(selected) > LIMITS["selected_file_count"]:
            raise PrereadError("final selected file count exceeded")
        records = []
        file_provenance = []
        os_release = None
        for path, role in sorted(selected.items()):
            record, raw, st = read_regular(guard, path, role, retain=path == release_path, selected=True)
            records.append(record)
            file_provenance.append({"path": path, **st})
            if path == release_path:
                os_release = raw.decode("utf-8")
        missing = [STDLIB + "/site-packages/" + name for name in
                   ("h5py", "h5py-3.16.0.dist-info", "hdf5plugin", "hdf5plugin-7.1.0.dist-info")]
        missing.append(plan["availability"]["observation"]["candidate_root"])
        missing.extend(row["recorded_download_path"] for row in plan["availability"]["observation"]["wheels"])
        missing = sorted(set(missing))
        if len(missing) != 8:
            raise PrereadError("original missing-path cohort is not eight")
        existence = [path_existence(path) for path in missing]
        for binding in SYMLINK_BINDINGS:
            check_time()
            named = os.lstat(binding["path"])
            target = os.readlink(binding["path"])
            if st_object(named) != {key: binding[key] for key in KEYS} or target != binding["target"] or identity(named) != identity(os.lstat(binding["path"])):
                raise PrereadError("symlink alias changed after selection: " + binding["path"])
        guard.verify()
        old_rows = {row["path"]: row for row in old["selected_files"]}
        if len(old_rows) != len(old["selected_files"]):
            raise PrereadError("old selected cohort has duplicate paths")
        new_rows = {row["path"]: row for row in records}
        comparison = {
            "old_manifest_path": OLD_PATH, "old_manifest_sha256": old_record["sha256"],
            "old_file_count": len(old_rows), "old_selected_bytes": sum(row["bytes"] for row in old_rows.values()),
            "added_paths": sorted(new_rows.keys() - old_rows.keys()),
            "removed_paths": sorted(old_rows.keys() - new_rows.keys()),
            "changed_rows": [{"path": path, "old": old_rows[path], "new": new_rows[path]}
                             for path in sorted(new_rows.keys() & old_rows.keys()) if old_rows[path] != new_rows[path]],
            "same_selected_cohort": old_rows == new_rows,
        }
        obj = {
            "schema": "radio-runtime-metadata-prospective-preread-pins-v1",
            "capture_identity": IDENTITY,
            "origin": "new bounded read-only preparation of current regular-file pins; no actual collector capture or runtime qualification",
            "python_path": PYTHON_PATH, "selected_files": records,
            "selected_file_count": len(records), "selected_file_bytes": sum(row["bytes"] for row in records),
            "stdlib_regular_cohort_count": len(cohort),
            "stdlib_cohort_selection": "all regular non-symlink files outside site-packages/cache/bytecode; counts derived from current enumeration",
            "stdlib_zero_byte_files": sum(new_rows[path]["bytes"] == 0 for path in cohort),
            "numpy_scope": "three static distribution metadata files hashed only; no package/native cohort or import",
            "loader_paths": ["/usr/lib/x86_64-linux-gnu", BASE + "/lib"], "loader_aliases": aliases,
            "resolved_symlink_identity_provenance": SYMLINK_BINDINGS,
            "distributions": [{"name": "numpy", "metadata_path": METADATA + "/METADATA",
                               "wheel_path": METADATA + "/WHEEL", "record_path": METADATA + "/RECORD",
                               "expected_version": "2.3.5"}],
            "missing_paths": missing, "missing_paths_lstat": existence,
            "os_release_utf8": os_release,
            "os_release_content_source": "retained from the one selected-file read of " + release_path,
            "limits": LIMITS, "explicit_read_accounting": dict(STATE),
            "read_accounting_scope": "explicit reader regular-file content only; implicit interpreter/source/module/loader/kernel/provider IO and filesystem metadata/enumeration IO excluded",
            "preread_inputs": [plan_record, old_record],
            "preread_input_provenance": [{"path": PLAN_PATH, **plan_provenance}, {"path": OLD_PATH, **old_provenance}],
            "selected_file_identity_provenance": file_provenance,
            "held_ancestor_identity_provenance": guard.provenance(),
            "comparison_to_previous_preread": comparison,
            "authority": "prospective preread pins only; no adopted collector observation, scientific authority, live allocation or runtime certificate",
            "original_materialization_plan_authority": plan["authority"],
            "genuine_collector_or_supervisor_invocations": 0,
            "new_live_reservation": False, "engineering_subtotal_seconds": 970,
            "engineering_subtotal_logical_mib": 48, "scientific_fields_pending": 11,
            "reader_execution_scope": "trusted primary -I -B -S bootstrap executes the primary interpreter; hashing selected interpreter bytes adds no target execution or loading",
            "elapsed_post_bootstrap_before_output_seconds": time.monotonic() - START,
        }
        raw = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(raw) > LIMITS["output_bytes"]:
            raise PrereadError("preread metadata output cap exceeded")
        check_time()
        # Verify runtime ancestor stability once more after serialization.
        guard.verify()
        fd = os.open(OUT_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
        with os.fdopen(fd, "wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        check_time()
        signal.setitimer(signal.ITIMER_REAL, 0)
        print(json.dumps({"status": "PREREAD_COMPLETED", "capture_identity": IDENTITY,
                          "files": len(records), "selected_bytes": obj["selected_file_bytes"],
                          "explicit_regular_content_bytes": STATE["regular_content_bytes"],
                          "stdlib_regular_cohort_count": len(cohort), "zero_files": obj["stdlib_zero_byte_files"],
                          "manifest_bytes": len(raw), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                          "same_selected_cohort": comparison["same_selected_cohort"],
                          "missing_lstat_absent_count": sum(not row["exists"] for row in existence),
                          "elapsed_post_bootstrap_through_output_seconds": time.monotonic() - START}, sort_keys=True))
    finally:
        guard.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        message = str(exc)
        if len(message.encode("utf-8")) > 4096:
            message = "error text exceeded 4096-byte reporting cap"
        print(json.dumps({"status": "PREREAD_CLOSED_FAILED", "error_type": type(exc).__name__,
                          "error": message, "explicit_read_accounting": STATE,
                          "elapsed_post_bootstrap_seconds": time.monotonic() - START,
                          "automatic_retry": False}, sort_keys=True), file=sys.stderr)
        sys.exit(1)
