"""Isolated source-freeze preflight. This entry point has no execution mode."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from types import ModuleType

CAP = 2 * 1024**2
REQUIRED_MODULES = {"contract.py", "codec12_control.py", "preflight.py", "run_preflight.py"}


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate freeze member")
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite freeze")))


def read(path, maximum=CAP):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.is_symlink():
        raise ValueError("canonical ordinary frozen file required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
            raise ValueError("bounded single-link file required")
        raw = handle.read(maximum + 1); after = os.fstat(handle.fileno()); current = path.lstat()
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        if len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key)
                                          or getattr(before, key) != getattr(current, key) for key in fields):
            raise ValueError("frozen file identity changed")
        return raw


def authenticate(raw, expected):
    if type(expected) is not dict or set(expected) != {"bytes", "sha256"} or type(expected["bytes"]) is not int:
        raise ValueError("external freeze pin required")
    if type(raw) is not bytes or not 0 < len(raw) <= CAP or len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("external freeze pin differs")


def verify_source_freeze(root, raw, external_pin):
    authenticate(raw, external_pin)
    freeze = parse(raw)
    if (type(freeze) is not dict or set(freeze) != {"schema", "status", "execution_enabled", "authority_commit", "files", "total_raw_bytes", "self_hash_excluded", "original_inputs"}
            or freeze["schema"] != "codec12-I-source-freeze-v1"
            or freeze["status"] != "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME"
            or freeze["execution_enabled"] is not False or freeze["self_hash_excluded"] is not True
            or freeze["authority_commit"] != "071de0428bdc50955a239ce5f7374c00d03e35a9"
            or type(freeze["files"]) is not dict or not REQUIRED_MODULES <= set(freeze["files"])
            or type(freeze["total_raw_bytes"]) is not int or not 0 < freeze["total_raw_bytes"] <= 4 * 1024**2):
        raise ValueError("exact inert source freeze required")
    contents, total = {}, 0
    for relative, pin in freeze["files"].items():
        pure = PurePosixPath(relative)
        if pure.is_absolute() or pure.as_posix() != relative or ".." in pure.parts or relative == "SOURCE_FREEZE.json":
            raise ValueError("frozen source path escapes or hashes itself")
        value = read(root / relative)
        if type(pin) is not dict or set(pin) != {"bytes", "sha256", "git_blob_sha1"}:
            raise ValueError("exact source artifact pin required")
        authenticate(value, {key: pin[key] for key in ("bytes", "sha256")})
        blob = hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()
        if blob != pin["git_blob_sha1"]:
            raise ValueError("source artifact Git blob differs")
        contents[relative] = value; total += len(value)
        if total > 4 * 1024**2:
            raise ValueError("source integrity read ceiling")
    if total != freeze["total_raw_bytes"]:
        raise ValueError("source aggregate bytes differ")
    return freeze, contents


def _load(name, path, raw):
    if name in sys.modules:
        raise ValueError("fresh authenticated module required")
    module = ModuleType(name); module.__file__ = str(path); sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--source-freeze-bytes", type=int, required=True)
    parser.add_argument("--source-freeze-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError("isolated -I -B preflight required")
    root = Path(__file__).resolve().parent
    if args.source_freeze != root / "SOURCE_FREEZE.json":
        raise ValueError("fixed source-freeze path required")
    freeze, contents = verify_source_freeze(root, read(args.source_freeze),
        {"bytes": args.source_freeze_bytes, "sha256": args.source_freeze_sha256})
    contract = _load("contract", root / "contract.py", contents["contract.py"])
    preflight = _load("_codec12_I_preflight", root / "preflight.py", contents["preflight.py"])
    result = preflight.inspect(args.repo_root)
    contract.same(contract.sha(contract.canonical(freeze["original_inputs"])), result["original_input_manifest_sha256"])
    result["source_artifacts_verified"] = len(contents)
    result["source_integrity_bytes"] = freeze["total_raw_bytes"]
    result["source_freeze_sha256"] = args.source_freeze_sha256
    print(contract.canonical(result).decode(), end="")


if __name__ == "__main__":
    main()
