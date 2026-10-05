"""One bounded static source snapshot. Never imports or executes pip."""

import ast
import base64
import hashlib
import json
import os
import signal
import stat
import sys
import time

ROOT = "/workspace/scratch/d804553c0e89/setisearch-status-20261004"
NAMESPACE = "results_radio_runtime_bootstrap_preparation_20261005a"
OUT_DIR = ROOT + "/" + NAMESPACE
OUT_PATH = OUT_DIR + "/installer-preread.json"
BASIS = OUT_DIR + "/installer-basis"
RUNTIME_PATH = ROOT + "/results_radio_runtime_capture_preparation_20261004b/runtime-preread-pins.json"
RUNTIME_SHA256 = "b5fe9e7b6cba36d726ecfe4c9bcd3d7bd5ff884cd1a3f6ecd7cb999005d27cac"
PLAN_PATH = ROOT + "/results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json"
PLAN_SHA256 = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
BASE = "/opt/codex/runtimes/codex-primary-runtime/dependencies/python"
SITE = BASE + "/lib/python3.12/site-packages"
LIMITS = {
    "explicit_regular_bytes": 128 * 1024 * 1024,
    "regular_file_bytes": 64 * 1024 * 1024,
    "explicit_regular_files": 2048,
    "enumerated_entries": 16384,
    "entries_per_directory": 4096,
    "held_directories": 1024,
    "enumeration_depth": 32,
    "path_utf8_bytes": 4096,
    "manifest_bytes": 4 * 1024 * 1024,
    "post_bootstrap_wall_seconds": 60,
    "read_chunk_bytes": 1024 * 1024,
}
KEYS = ("st_dev", "st_ino", "st_mode", "st_size", "st_nlink", "st_mtime_ns", "st_ctime_ns")
START = time.monotonic()
STATE = {"explicit_regular_bytes": 0, "explicit_regular_files": 0,
         "enumerated_entries": 0, "eof_probe_calls": 0,
         "eof_probe_bytes_returned": 0, "completed_seed_copies": 0,
         "copied_raw_bytes": 0, "stored_representation_bytes": 0}


class PrereadError(Exception):
    pass


def check_time():
    if time.monotonic() - START >= LIMITS["post_bootstrap_wall_seconds"]:
        raise PrereadError("post-bootstrap deadline exceeded")


def deadline(signum, frame):
    raise PrereadError("post-bootstrap SIGALRM deadline exceeded")


def identity(st):
    return tuple(getattr(st, key) for key in KEYS)


def identity_object(st):
    return dict(zip(KEYS, identity(st)))


def checked_path(path):
    if not isinstance(path, str) or not path.startswith("/") or os.path.normpath(path) != path:
        raise PrereadError("path must be canonical and absolute")
    if "\0" in path or len(path.encode("utf-8")) > LIMITS["path_utf8_bytes"]:
        raise PrereadError("path length or NUL rejected")
    return path


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class Guard:
    """Keep no-follow descriptors for every source ancestor until final verification."""

    def __init__(self):
        self.directories = {}

    def directory(self, path):
        checked_path(path)
        check_time()
        if path in self.directories:
            return self.directories[path][0]
        if len(self.directories) >= LIMITS["held_directories"]:
            raise PrereadError("held-directory cap exceeded")
        if path == "/":
            before = os.stat(path, follow_symlinks=False)
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        else:
            parent = self.directory(os.path.dirname(path))
            name = os.path.basename(path)
            before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise PrereadError("non-directory or symlink ancestor: " + path)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        held = os.fstat(fd)
        if not stat.S_ISDIR(held.st_mode) or identity(held) != identity(before):
            os.close(fd)
            raise PrereadError("ancestor name/descriptor mismatch: " + path)
        if len(self.directories) >= LIMITS["held_directories"]:
            os.close(fd)
            raise PrereadError("held-directory cap exceeded during descent")
        self.directories[path] = (fd, before)
        return fd

    def verify(self):
        for path, (fd, before) in self.directories.items():
            check_time()
            if path == "/":
                named = os.stat(path, follow_symlinks=False)
            else:
                parent = self.directories[os.path.dirname(path)][0]
                named = os.stat(os.path.basename(path), dir_fd=parent, follow_symlinks=False)
            if identity(before) != identity(os.fstat(fd)) or identity(before) != identity(named):
                raise PrereadError("source ancestor changed: " + path)

    def provenance(self):
        return [{"path": path, **identity_object(before)}
                for path, (_, before) in sorted(self.directories.items())]

    def close(self):
        for fd, _ in reversed(list(self.directories.values())):
            os.close(fd)
        self.directories.clear()


def read_regular(guard, path, retain=False):
    checked_path(path)
    check_time()
    if STATE["explicit_regular_files"] >= LIMITS["explicit_regular_files"]:
        raise PrereadError("explicit regular-file cap exceeded")
    parent = guard.directory(os.path.dirname(path))
    name = os.path.basename(path)
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISREG(named.st_mode) or named.st_nlink != 1:
        raise PrereadError("input is not a sole-link regular file: " + path)
    if named.st_size < 0 or named.st_size > LIMITS["regular_file_bytes"]:
        raise PrereadError("per-file cap exceeded: " + path)
    permissions = format(named.st_mode & 0o7777, "04o")
    if permissions not in ("0644", "0755"):
        raise PrereadError("source permissions rejected: " + path)
    if STATE["explicit_regular_bytes"] + named.st_size + 1 > LIMITS["explicit_regular_bytes"]:
        raise PrereadError("explicit byte cap would be exceeded: " + path)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if identity(before) != identity(named):
            raise PrereadError("source descriptor/name mismatch: " + path)
        digest = hashlib.sha256()
        blob = hashlib.sha1(b"blob " + str(before.st_size).encode("ascii") + b"\0")
        chunks = [] if retain else None
        remaining = before.st_size
        while remaining:
            check_time()
            raw = os.read(fd, min(remaining, LIMITS["read_chunk_bytes"]))
            STATE["explicit_regular_bytes"] += len(raw)
            if not raw:
                raise PrereadError("source ended before frozen length: " + path)
            digest.update(raw)
            blob.update(raw)
            if retain:
                chunks.append(raw)
            remaining -= len(raw)
        check_time()
        extra = os.read(fd, 1)
        STATE["eof_probe_calls"] += 1
        STATE["explicit_regular_bytes"] += len(extra)
        STATE["eof_probe_bytes_returned"] += len(extra)
        if extra:
            raise PrereadError("source grew beyond frozen length: " + path)
        after = os.fstat(fd)
        named_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if identity(before) != identity(after) or identity(before) != identity(named_after):
            raise PrereadError("source changed during read: " + path)
        STATE["explicit_regular_files"] += 1
        row = {"path": path, "bytes": before.st_size, "sha256": digest.hexdigest(),
               "mode": "100755" if permissions == "0755" else "100644",
               "filesystem_mode": permissions, "git_blob": blob.hexdigest(),
               "source_identity": identity_object(before)}
        return row, b"".join(chunks) if retain else None
    finally:
        os.close(fd)


def auxiliary(path, expected_sha):
    guard = Guard()
    try:
        row, raw = read_regular(guard, path, retain=True)
        if row["sha256"] != expected_sha:
            raise PrereadError("comparison input SHA differs: " + path)
        guard.verify()
        row["held_ancestors"] = guard.provenance()
        return row, raw
    finally:
        guard.close()


def entries(guard, directory):
    rows = []
    with os.scandir(guard.directory(directory)) as iterator:
        for entry in iterator:
            check_time()
            STATE["enumerated_entries"] += 1
            if STATE["enumerated_entries"] > LIMITS["enumerated_entries"]:
                raise PrereadError("enumeration cap exceeded")
            if len(rows) >= LIMITS["entries_per_directory"]:
                raise PrereadError("per-directory entry cap exceeded")
            if entry.name in (".", "..") or "/" in entry.name:
                raise PrereadError("invalid directory entry")
            rows.append((entry.name, entry.stat(follow_symlinks=False)))
    return sorted(rows, key=lambda row: row[0])


def selected_pip_paths(guard, root, exclusions, depth=0):
    if depth > LIMITS["enumeration_depth"]:
        raise PrereadError("enumeration depth cap exceeded")
    result = []
    for name, info in entries(guard, root):
        path = checked_path(root + "/" + name)
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise PrereadError("symlink or special installer entry rejected: " + path)
        if name == "__pycache__" or name.endswith(".pyc"):
            exclusions.append({"path": path, "reason": "ambient bytecode is not selected or read",
                               "identity": identity_object(info)})
            continue
        if stat.S_ISDIR(info.st_mode):
            result.extend(selected_pip_paths(guard, path, exclusions, depth + 1))
        else:
            if info.st_nlink != 1:
                raise PrereadError("hard-linked installer input rejected: " + path)
            result.append(path)
    return result


def seed_copy(row, raw):
    relative = row["path"][len(SITE) + 1:]
    if not relative or relative.startswith("/") or ".." in relative.split("/"):
        raise PrereadError("installer seed path rejected")
    try:
        raw.decode("utf-8")
        encoding = "utf8"
        representation = raw
        stored_relative = relative
        permissions = int(row["filesystem_mode"], 8)
    except UnicodeDecodeError:
        encoding = "base64"
        representation = base64.b64encode(raw) + b"\n"
        stored_relative = relative + ".base64"
        permissions = 0o644
    destination = BASIS + "/" + stored_relative
    os.makedirs(os.path.dirname(destination), mode=0o755, exist_ok=True)
    parent = os.open(os.path.dirname(destination), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        fd = os.open(os.path.basename(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     permissions, dir_fd=parent)
        try:
            os.fchmod(fd, permissions)
            view = memoryview(representation)
            while view:
                check_time()
                wrote = os.write(fd, view)
                if wrote <= 0:
                    raise PrereadError("seed write made no progress")
                view = view[wrote:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent)
    finally:
        os.close(parent)
    STATE["completed_seed_copies"] += 1
    STATE["copied_raw_bytes"] += len(raw)
    STATE["stored_representation_bytes"] += len(representation)
    row.update({"repository_path": NAMESPACE + "/installer-basis/" + stored_relative,
                "repository_artifact_path": NAMESPACE + "/installer-basis/" + stored_relative,
                "seed_relative_path": relative, "relative_path": relative, "stored_encoding": encoding,
                "stored_bytes": len(representation),
                "stored_sha256": hashlib.sha256(representation).hexdigest(),
                "stored_git_blob": git_blob(representation),
                "stored_mode": "100755" if permissions == 0o755 else "100644",
                "repository_bytes": len(representation),
                "repository_sha256": hashlib.sha256(representation).hexdigest(),
                "repository_git_blob": git_blob(representation)})
    return row


def static_version(metadata, init):
    fields = {}
    for line in metadata.decode("utf-8").splitlines():
        if line.startswith(("Name:", "Version:")):
            key, value = line.split(":", 1)
            if key in fields:
                raise PrereadError("duplicate installer metadata identity field")
            fields[key] = value.strip()
    if fields.get("Name", "").lower() != "pip" or not fields.get("Version"):
        raise PrereadError("installer metadata identity absent")
    if len(init) > 64 * 1024:
        raise PrereadError("pip __init__ exceeds static AST limit")
    values = []
    for node in ast.parse(init.decode("utf-8"), filename="pip/__init__.py").body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                raise PrereadError("pip __version__ is not a static string")
            values.append(node.value.value)
    if values != [fields["Version"]]:
        raise PrereadError("pip METADATA and static __version__ differ")
    return fields["Version"]


def write_manifest(result):
    raw = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    if len(raw) > LIMITS["manifest_bytes"]:
        raise PrereadError("manifest byte cap exceeded")
    fd = os.open(OUT_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    try:
        os.fchmod(fd, 0o644)
        view = memoryview(raw)
        while view:
            check_time()
            wrote = os.write(fd, view)
            if wrote <= 0:
                raise PrereadError("manifest write made no progress")
            view = view[wrote:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(OUT_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {"path": OUT_PATH, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob": git_blob(raw)}


def main():
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(LIMITS["post_bootstrap_wall_seconds"])
    guard = Guard()
    try:
        if os.path.lexists(OUT_PATH) or os.path.lexists(BASIS):
            raise PrereadError("exclusive manifest or installer basis already exists; no retry")
        plan_pin, plan_raw = auxiliary(PLAN_PATH, PLAN_SHA256)
        runtime_pin, runtime_raw = auxiliary(RUNTIME_PATH, RUNTIME_SHA256)
        json.loads(plan_raw)
        previous = json.loads(runtime_raw)
        previous_rows = previous["selected_files"]
        if len(previous_rows) != 765 or sum(row["bytes"] for row in previous_rows) != 53792770:
            raise PrereadError("retained runtime cohort count or bytes differ")
        paths = [row["path"] for row in previous_rows]
        if len(set(paths)) != 765 or paths != sorted(paths):
            raise PrereadError("retained runtime cohort paths are not unique and sorted")
        runtime_rows = []
        for old in previous_rows:
            row, _ = read_regular(guard, old["path"])
            for key in ("path", "bytes", "sha256", "mode", "filesystem_mode"):
                if row[key] != old[key]:
                    raise PrereadError("current runtime cohort differs at " + old["path"] + ":" + key)
            row["role"] = old["role"]
            runtime_rows.append(row)
        site_names = entries(guard, SITE)
        matches = [(name, info) for name, info in site_names if name.startswith("pip-") and name.endswith(".dist-info")]
        if len(matches) != 1 or not stat.S_ISDIR(matches[0][1].st_mode):
            raise PrereadError("exactly one non-symlink pip dist-info directory required")
        pip_dir = [info for name, info in site_names if name == "pip"]
        if len(pip_dir) != 1 or not stat.S_ISDIR(pip_dir[0].st_mode):
            raise PrereadError("pip package must be a non-symlink directory")
        distribution = matches[0][0]
        exclusions = []
        selected = sorted(selected_pip_paths(guard, SITE + "/pip", exclusions) +
                          selected_pip_paths(guard, SITE + "/" + distribution, exclusions))
        if not selected or len(selected) != len(set(selected)):
            raise PrereadError("installer source inventory empty or duplicated")
        os.mkdir(BASIS, mode=0o755)
        installer_rows = []
        metadata = None
        init = None
        for path in selected:
            row, raw = read_regular(guard, path, retain=True)
            installer_rows.append(seed_copy(row, raw))
            if path == SITE + "/" + distribution + "/METADATA":
                metadata = raw
            if path == SITE + "/pip/__init__.py":
                init = raw
        if metadata is None or init is None:
            raise PrereadError("installer static identity inputs absent")
        version = static_version(metadata, init)
        if distribution != "pip-" + version + ".dist-info":
            raise PrereadError("installer directory basename and static version differ")
        guard.verify()
        result = {
            "schema": "radio-runtime-bootstrap-installer-preread-v1",
            "status": "PREPARED_STATIC_SOURCE_SNAPSHOT_ONLY",
            "authority": "prospective runtime and installer-source pins only; no bootstrap, install, download, live reservation, scientific authority or runtime certificate",
            "reader_execution_scope": "CPython primary -I -B -S; stdlib only; pip and selected native packages were not imported or executed",
            "limits": LIMITS,
            "explicit_read_accounting": dict(STATE),
            "read_accounting_scope": "explicit regular content returned by this reader, including two comparison inputs and EOF probes; excludes implicit CPython/stdlib bootstrap and kernel/provider reads",
            "elapsed_post_bootstrap_before_manifest_seconds": time.monotonic() - START,
            "elapsed_scope": "clock begins after reader stdlib imports; includes explicit reads, enumeration, source copying, static parsing and final source verification; excludes manifest write/final CLI print and provider elapsed time",
            "source_input_pins": [plan_pin, runtime_pin],
            "runtime_selected_file_count": len(runtime_rows),
            "runtime_selected_file_bytes": sum(row["bytes"] for row in runtime_rows),
            "runtime_comparison": {"same_exact_765_cohort": True, "changed_rows": [], "added_paths": [], "removed_paths": []},
            "runtime_selected_files": runtime_rows,
            "pip_source_root": SITE,
            "pip_distribution": distribution,
            "pip_version_static": version,
            "pip_version_method": "one Name and Version in raw METADATA, compared to one top-level __version__ string assignment in pip/__init__.py AST; no import",
            "installer_source_file_count": len(installer_rows),
            "installer_source_raw_bytes": sum(row["bytes"] for row in installer_rows),
            "installer_stored_representation_bytes": sum(row["stored_bytes"] for row in installer_rows),
            "installer_source_files": installer_rows,
            "excluded_ambient_bytecode_entries": exclusions,
            "excluded_bytecode_scope": "excluded __pycache__ directories are not descended into; .pyc entries are not read or copied",
            "held_source_ancestor_identity_provenance": guard.provenance(),
            "source_identity_law": "all selected regular files are sole-link and opened through held no-follow ancestors; name and descriptor metadata compared before/after each full read; held ancestors rechecked at the end",
            "seed_publication_law": "UTF-8 rows retain exact raw source bytes; other rows retain canonical base64 plus newline, decoded using row stored_encoding to seed_relative_path; raw and stored hashes/Git blob IDs are separate",
            "seed_execution_requirement": "future reviewed bootstrap must reconstruct all rows into a fresh isolated source seed, validate every raw digest and mode, and run CPython -I -B -S with fresh seed on sys.path; ambient .pyc is not this basis",
            "genuine_bootstrap_invocations": 0,
            "genuine_installer_invocations": 0,
            "genuine_capture_invocations": 0,
            "new_live_reservation": False,
            "scientific_authority": False,
            "scientific_fields_pending": 11,
        }
        pin = write_manifest(result)
        print(json.dumps({"status": result["status"], "output": pin,
                          "pip_version_static": version,
                          "runtime_files": len(runtime_rows), "installer_files": len(installer_rows),
                          "explicit_read_accounting": STATE}, sort_keys=True))
    finally:
        guard.close()
        signal.alarm(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "CLOSED_FAILED_STATIC_PREREAD", "error_type": type(exc).__name__,
                          "error": str(exc), "explicit_read_accounting": STATE,
                          "elapsed_post_bootstrap_seconds": time.monotonic() - START,
                          "partial_seed_copies_must_be_retained": True, "automatic_retry": False}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
