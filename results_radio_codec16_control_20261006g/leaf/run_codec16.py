"""One externally admitted codec16 engineering leaf; imports are lazy.

The complete leaf manifest and fresh dispatch are pinned by the outer scope.
This entry point provides no allocation, supervisor or scientific admission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from types import ModuleType

MIB = 1024 ** 2
MANIFEST_NAME = "LEAF_FILES.json"
REQUIRED = {"run_codec16.py", "codec16_control.py", "preparation.py",
            "retained-draft/PLAN.json", "retained-draft/INPUT_MANIFEST.json",
            "retained-draft/SELECTED_CODE.json"}
DISPATCH_KEYS = {"schema", "scope_id", "plan_sha256", "input_manifest_sha256",
                 "selection_sha256", "runtime_prefix", "outer_supervisor_scope_sha256",
                 "engineering_execution_authorized"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def _pin(raw, expected, *, allow_empty=False):
    if (type(expected) is not dict or set(expected) != {"bytes", "sha256"}
            or type(expected["bytes"]) is not int or not (0 if allow_empty else 1) <= expected["bytes"] <= 2 * MIB
            or type(expected["sha256"]) is not str or not HEX.fullmatch(expected["sha256"])
            or len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]):
        raise ValueError("external raw pin differs")
    return raw


def read_regular(path, maximum=2 * MIB, *, allow_empty=False):
    if path.is_symlink():
        raise ValueError("ordinary file required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or not (0 if allow_empty else 1) <= before.st_size <= maximum:
            raise ValueError("ordinary bounded input required")
        raw = handle.read(maximum + 1)
        after = os.fstat(handle.fileno())
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError("input changed while reading")
        return raw


def verify_leaf(root, manifest_raw, expected_manifest_pin):
    _pin(manifest_raw, expected_manifest_pin)
    manifest = parse(manifest_raw)
    if (type(manifest) is not dict or set(manifest) != {"schema", "files", "total_raw_bytes", "self_hash_excluded"}
            or manifest["schema"] != "codec16-G-leaf-artifacts-v1"
            or manifest["self_hash_excluded"] is not True
            or type(manifest["files"]) is not dict or not REQUIRED <= set(manifest["files"])
            or type(manifest["total_raw_bytes"]) is not int or not 0 < manifest["total_raw_bytes"] <= 4 * MIB):
        raise ValueError("complete codec16 G leaf manifest required")
    files, observed, total = {}, set(), 0
    for path in root.rglob("*"):
        st = path.lstat()
        if stat.S_ISDIR(st.st_mode):
            continue
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("ordinary leaf artifact tree required")
        relative = path.relative_to(root).as_posix()
        if relative != MANIFEST_NAME:
            observed.add(relative)
    if observed != set(manifest["files"]):
        raise ValueError("leaf file inventory differs")
    for relative, expected in manifest["files"].items():
        pure = PurePosixPath(relative)
        if (pure.is_absolute() or pure.as_posix() != relative or ".." in pure.parts
                or relative == MANIFEST_NAME):
            raise ValueError("leaf input path escapes its root")
        path = root / relative
        if path.resolve() != path or not path.resolve().is_relative_to(root):
            raise ValueError("leaf input path relocated")
        raw = read_regular(path, allow_empty=True)
        # Empty retained log files are allowed; effectful documents are nonempty.
        if len(raw) == 0 and relative in REQUIRED:
            raise ValueError("unexpected empty runtime leaf artifact")
        _pin(raw, expected, allow_empty=True)
        total += len(raw)
        if total > 4 * MIB:
            raise ValueError("leaf integrity read envelope exceeded")
        files[relative] = raw
    if total != manifest["total_raw_bytes"]:
        raise ValueError("leaf aggregate bytes differ")
    return files


def inspect_dispatch(raw, expected_pin, files):
    dispatch = parse(_pin(raw, expected_pin))
    if (type(dispatch) is not dict or set(dispatch) != DISPATCH_KEYS
            or dispatch["schema"] != "codec16-fresh-engineering-dispatch-v1"
            or dispatch["engineering_execution_authorized"] is not True
            or type(dispatch["scope_id"]) is not str
            or not re.fullmatch(r"codec16-[a-z0-9-]{1,80}", dispatch["scope_id"])
            or type(dispatch["runtime_prefix"]) is not str
            or not Path(dispatch["runtime_prefix"]).is_absolute()
            or type(dispatch["outer_supervisor_scope_sha256"]) is not str
            or not HEX.fullmatch(dispatch["outer_supervisor_scope_sha256"])):
        raise ValueError("fresh external engineering dispatch required")
    mapping = {"plan_sha256": "PLAN.json", "input_manifest_sha256": "INPUT_MANIFEST.json",
               "selection_sha256": "SELECTED_CODE.json"}
    for key, name in mapping.items():
        if dispatch[key] != hashlib.sha256(files["retained-draft/" + name]).hexdigest():
            raise ValueError("dispatch differs from retained draft input pin")
    return dispatch


def inspect_output(output, root):
    if (not output.is_absolute() or output.resolve() != output or not output.parent.is_dir()
            or output.exists() or output.is_symlink() or output.is_relative_to(root)):
        raise ValueError("fresh ordinary output path outside leaf tree required")


def _load(name, path, authenticated_raw):
    if name in sys.modules:
        raise ValueError("fresh leaf module namespace required")
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(authenticated_raw, str(path), "exec"), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--dispatch-bytes", type=int, required=True)
    parser.add_argument("--dispatch-sha256", required=True)
    parser.add_argument("--leaf-manifest", type=Path, required=True)
    parser.add_argument("--leaf-manifest-bytes", type=int, required=True)
    parser.add_argument("--leaf-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError("isolated -I -B leaf interpreter required")
    root = Path(__file__).resolve().parent
    if args.leaf_manifest != root / MANIFEST_NAME:
        raise ValueError("manifest must be the pinned leaf manifest")
    inspect_output(args.output, root)
    files = verify_leaf(root, read_regular(args.leaf_manifest),
                        {"bytes": args.leaf_manifest_bytes, "sha256": args.leaf_manifest_sha256})
    dispatch_raw = read_regular(args.dispatch)
    dispatch_pin = {"bytes": args.dispatch_bytes, "sha256": args.dispatch_sha256}
    dispatch = inspect_dispatch(dispatch_raw, dispatch_pin, files)
    if Path(sys.prefix).resolve() != Path(dispatch["runtime_prefix"]).resolve():
        raise ValueError("exact runtime prefix required")
    _load("preparation", root / "preparation.py", files["preparation.py"])
    control = _load("codec16_control", root / "codec16_control.py", files["codec16_control.py"])
    raw = {name: files["retained-draft/" + name] for name in ("PLAN.json", "INPUT_MANIFEST.json", "SELECTED_CODE.json")}
    pins = {name: {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()} for name, value in raw.items()}
    result = control.produce(root / "retained-draft", args.output,
                             plan_raw=raw["PLAN.json"], expected_plan_pin=pins["PLAN.json"],
                             manifest_raw=raw["INPUT_MANIFEST.json"], expected_manifest_pin=pins["INPUT_MANIFEST.json"],
                             selection_raw=raw["SELECTED_CODE.json"], expected_selection_pin=pins["SELECTED_CODE.json"],
                             dispatch_raw=dispatch_raw, expected_dispatch_pin=dispatch_pin)
    print(json.dumps({"status": result["status"], "scope_id": result["scope_id"],
                      "rows": len(result["rows"]), "scientific_readiness": False}, sort_keys=True))


if __name__ == "__main__":
    main()
