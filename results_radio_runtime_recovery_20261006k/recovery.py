"""Original-byte administrative recovery only; no install/import/native dispatch.

The original C expected bytes are immutable. Missing/mismatched members remain
unrecovered. This operation never reuses a historical inode witness or ledger.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time

AUTHORITY = "bdd987501871033f1827c7ab865d52c36e2883f3"
MANIFEST_PIN = {"bytes": 347163, "sha256": "78d731b895f75c835c936e6f8b1b2afa36944bf8cf8a11544d5a5d57d257bd59"}
FIXED_SOURCES = {
    "site_packages": "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages",
    "python": "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12",
}
LIMITS = {"expected_files": 1038, "expected_bytes": 299652798,
          "read_bytes": 1024 ** 3, "artifact_bytes": 384 * 1024 ** 2,
          "per_file_bytes": 128 * 1024 ** 2, "wall_seconds": 120,
          "cpu_seconds": 60, "address_space_bytes": 256 * 1024 ** 2,
          "descriptor_limit": 64}
PREFIX = "venv/lib/python3.12/site-packages/"


class Refusal(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def same(a, b):
    if canonical(a) != canonical(b): raise Refusal("exact type/value differs")


def _unique(pairs):
    out = {}
    for name, value in pairs:
        if name in out: raise Refusal("duplicate JSON member")
        out[name] = value
    return out


def parse(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(Refusal("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Refusal("invalid JSON") from exc


def relative(name):
    if (type(name) is not str or not name.startswith("venv/") or "\0" in name
            or str(PurePosixPath(name)) != name or ".." in PurePosixPath(name).parts
            or len(name.encode()) > 4096):
        raise Refusal("canonical contained venv file required")
    return PurePosixPath(name)


def expected_rows(raw):
    same(pin(raw), MANIFEST_PIN)
    value = parse(raw)
    if value["status"] != "INSTALLED_BYTES_VERIFIED_NO_PACKAGE_IMPORT":
        raise Refusal("original installed-byte disposition differs")
    rows = sorted((row for row in value["inventory"]["entries"] if row["path"].startswith("venv/")),
                  key=lambda row: row["path"])
    validate_rows(rows, LIMITS["expected_files"], LIMITS["expected_bytes"])
    return rows


def validate_rows(rows, count, total):
    if (type(count) is not int or type(total) is not int or not 0 <= count <= LIMITS["expected_files"]
            or not 0 <= total <= LIMITS["artifact_bytes"]
            or type(rows) is not list or len(rows) != count):
        raise Refusal("fixed original row count differs")
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {"path", "bytes", "sha256", "mode"}:
            raise Refusal("exact original row fields required")
        relative(row["path"])
        if row["path"] in seen: raise Refusal("duplicate original path")
        seen.add(row["path"])
        if (type(row["bytes"]) is not int or not 0 <= row["bytes"] <= LIMITS["per_file_bytes"]
                or type(row["mode"]) is not int or row["mode"] not in (0o644, 0o755)
                or type(row["sha256"]) is not str or len(row["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in row["sha256"])):
            raise Refusal("original size/mode/hash bound differs")
    if any(str(parent) in seen for name in seen for parent in PurePosixPath(name).parents):
        raise Refusal("file/directory path collision")
    if sum(row["bytes"] for row in rows) != total or total > LIMITS["artifact_bytes"]:
        raise Refusal("original aggregate bytes differ")


def source_for(name, sources):
    relative(name)
    if name == "venv/bin/python": return Path(sources["python"])
    if name.startswith(PREFIX): return Path(sources["site_packages"]) / name[len(PREFIX):]
    return None


def signature(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns]


def ordinary_path(path):
    """No symlink component is eligible; no silent canonical rebinding."""
    if not path.is_absolute(): raise Refusal("absolute source required")
    for part in (path, *path.parents):
        if part.is_symlink(): raise Refusal("source symlink component")


class Budget:
    def __init__(self):
        self.started = time.monotonic()
        self.read = self.written = 0
    def check(self):
        if time.monotonic() - self.started > LIMITS["wall_seconds"]: raise Refusal("copy wall bound")
    def charge(self, read=0, written=0):
        self.read += read; self.written += written; self.check()
        if self.read > LIMITS["read_bytes"] or self.written > LIMITS["artifact_bytes"]:
            raise Refusal("copy read/artifact bound")
    def reserve(self, read=0, written=0):
        self.check()
        if self.read + read > LIMITS["read_bytes"] or self.written + written > LIMITS["artifact_bytes"]:
            raise Refusal("copy read/artifact bound")


def copy_member(row, source, root, budget):
    result = {"path": row["path"], "expected": dict(row), "source": str(source) if source else None}
    budget.check()
    if source is None:
        return {**result, "status": "NO_DECLARED_CURRENT_SOURCE"}
    try:
        ordinary_path(source)
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError as exc:
        return {**result, "status": "MISSING_CURRENT_SOURCE", "errno": exc.errno}
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode): raise Refusal("ordinary source file required")
        result["source_identity"] = signature(before)
        if before.st_size != row["bytes"]:
            return {**result, "status": "SOURCE_SIZE_MISMATCH", "observed_bytes": before.st_size}
        target = root / "candidate" / row["path"]
        # Every unverified copy remains nonexecutable in the separate staging tree.
        staging = root / "retained-staging" / row["path"]
        staging.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        digest = hashlib.sha256(); copied = 0
        with os.fdopen(write_fd, "wb") as output:
            while True:
                request = min(65536, row["bytes"] + 1 - copied)
                budget.reserve(read=request)
                raw = handle.read(request)
                budget.charge(read=len(raw))
                if not raw: break
                copied += len(raw)
                if copied > row["bytes"]: raise Refusal("source grew while copying")
                budget.reserve(written=len(raw))
                count = output.write(raw)
                budget.charge(written=count)
                if count != len(raw): raise Refusal("short staging write")
                digest.update(raw)
            output.flush(); os.fsync(output.fileno())
        after = os.fstat(handle.fileno())
        ordinary_path(source)
        if (signature(before) != signature(after)
                or signature(os.stat(source, follow_symlinks=False)) != signature(before)):
            raise Refusal("held/named source identity drift")
    actual = {"bytes": copied, "sha256": digest.hexdigest()}
    result.update(observed=actual, retained_staging=str(staging.relative_to(root)))
    if copied != row["bytes"] or actual["sha256"] != row["sha256"]:
        return {**result, "status": "SOURCE_HASH_MISMATCH_RETAINED"}
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink(): raise Refusal("exclusive candidate path required")
    # The root is private and was newly created by this call. No foreign output
    # path is admitted. Moving a retained staged file does not erase its bytes.
    os.rename(staging, target)
    os.chmod(target, row["mode"], follow_symlinks=False)
    info = os.stat(target, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != row["mode"]:
        raise Refusal("candidate file identity/mode differs")
    return {**result, "status": "ORIGINAL_BYTES_COPIED_CURRENT_IDENTITY",
            "candidate_path": str(target.relative_to(root)), "candidate_identity": signature(info),
            "retained_staging": None}


def recover(rows, sources, root):
    root = Path(root)
    validate_rows(rows, len(rows), sum(row["bytes"] for row in rows))
    if not root.is_absolute() or root.is_symlink(): raise Refusal("absolute new output root required")
    ordinary_path(root)
    if type(sources) is not dict or set(sources) != {"site_packages", "python"}:
        raise Refusal("explicit source mapping required")
    for source in sources.values(): ordinary_path(Path(source))
    root.mkdir(mode=0o700, exist_ok=False)
    budget = Budget(); outcomes = []
    journal = os.open(root / "COPY.events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    def emit(value):
        raw = canonical(value); budget.reserve(written=len(raw))
        written = os.write(journal, raw); budget.charge(written=written)
        if written != len(raw): raise Refusal("short event write")
        os.fsync(journal)
    try:
        for index, row in enumerate(rows):
            value = copy_member(row, source_for(row["path"], sources), root, budget)
            outcomes.append(value); emit({"index": index, "outcome": value})
    except BaseException as exc:
        try: emit({"failure": type(exc).__name__, "error": str(exc), "completed_members": len(outcomes)})
        except BaseException as persist: exc.add_note("secondary event persistence failure: " + repr(persist))
        raise
    finally:
        os.close(journal)
    copied = [row for row in outcomes if row["status"] == "ORIGINAL_BYTES_COPIED_CURRENT_IDENTITY"]
    result = {"schema": "radio-original-byte-recovery-K-result-v1",
              "status": "PARTIAL_ORIGINAL_BYTES_CURRENT_STORAGE_UNQUALIFIED" if len(copied) != len(rows) else "ORIGINAL_BYTES_PRESENT_RUNTIME_UNQUALIFIED",
              "authority_commit": AUTHORITY, "original_manifest_pin": MANIFEST_PIN,
              "expected_files": len(rows), "copied_files": len(copied),
              "copied_original_bytes": sum(row["observed"]["bytes"] for row in copied),
              "missing_or_mismatched": len(rows) - len(copied), "outcomes": outcomes,
              "read_bytes": budget.read, "written_bytes_before_result": budget.written,
              "measured_seconds": time.monotonic() - budget.started, "limits": dict(LIMITS),
              "old_inode_custody_or_ledger_reused": False, "recovered_interpreter_executions": 0,
              "native_package_imports": 0, "pip_or_package_installs": 0, "kernel_traces_collected": 0,
              "runtime_qualified": False, "codec_certificate_issued": False,
              "native_or_scientific_allocation_created": False, "spectra_opened": False}
    raw = canonical(result)
    budget.reserve(written=len(raw))
    fd = os.open(root / "RESULT.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        written = os.write(fd, raw); budget.charge(written=written)
        if written != len(raw): raise Refusal("short result write")
        os.fsync(fd)
    finally: os.close(fd)
    return result


def verify_candidate(root, result):
    """Independent body rehash; accepts a partial copy, never qualifies runtime."""
    root = Path(root); ordinary_path(root)
    candidate = root / "candidate"
    expected = {row["candidate_path"]: row for row in result["outcomes"]
                if row["status"] == "ORIGINAL_BYTES_COPIED_CURRENT_IDENTITY"}
    found = set(); reads = 0
    for path in sorted(candidate.rglob("*")) if candidate.exists() else []:
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode): continue
        name = str(path.relative_to(root))
        if name not in expected: raise Refusal("unexpected candidate entry")
        ordinary_path(path)
        row = expected[name]
        if signature(info) != row["candidate_identity"]: raise Refusal("candidate custody changed")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as handle:
            digest = hashlib.sha256(); size = 0
            before = os.fstat(handle.fileno())
            if signature(before) != row["candidate_identity"]:
                raise Refusal("held candidate identity differs")
            while True:
                raw = handle.read(65536)
                if not raw: break
                reads += len(raw); size += len(raw)
                if reads + result["read_bytes"] > LIMITS["read_bytes"]:
                    raise Refusal("copy plus independent read bound")
                digest.update(raw)
            if signature(before) != signature(os.fstat(handle.fileno())):
                raise Refusal("candidate changed while reviewing")
        same({"bytes": size, "sha256": digest.hexdigest()}, row["observed"])
        if signature(path.lstat()) != row["candidate_identity"]:
            raise Refusal("candidate named identity changed")
        found.add(name)
    if found != set(expected): raise Refusal("candidate membership differs")
    return {"status": "INDEPENDENT_PARTIAL_BYTES_VERIFIED_RUNTIME_UNQUALIFIED",
            "files": len(found), "read_bytes": reads, "runtime_qualified": False,
            "historical_inode_continuity": False, "execution_authority": False}


def native_dispatch(*args, **kwargs):
    raise Refusal("copy recovery grants no runtime or native execution authority")
