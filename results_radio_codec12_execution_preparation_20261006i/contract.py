"""Authenticated, source-only codec12 inputs. No dispatch or native imports."""
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from types import ModuleType
import sys

MIB = 1024 ** 2
H_COMMIT = "071de0428bdc50955a239ce5f7374c00d03e35a9"
H_ROOT = "results_radio_codec12_preparation_20261006h/"
H_PINS = {
    "PLAN.json": (8906, "67d9c3df076d09aff7701ccdd7f60eb3aaa00d4564e4d2f1706c0d4d3344207c"),
    "INPUT_MANIFEST.json": (3174, "83fc53fe9c5e11ce5eb55f1e471da55c2f9d5b4d85fe3dddb6e7d4f148f57dce"),
    "SELECTED_CODE.json": (3279, "371f991700822f60881d03f5696cbaf808cf8f99c2ceeef105c6d39826f05777"),
    "metadata_law_control.py": (4696, "36281a3414dd3ffba012e15c893a963bd47403540c50e939b943b9cd547207d6"),
}
LABELS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ROLES = ("calibration", "validation")
RECEIVER = "results_radio_scientific_execution_prospective_20261003a/receiver_telescope_adapter.py"
BASIS = "results_radio_scientific_execution_prospective_20261003a/preserved-basis.json"
METADATA_PATHS = {
    "source_metadata": "config/radio_hd189733_source_preparation_20260927.json",
    "window_design": "results_radio_hd189733_geometry_2026-09-27/window_geometry.json",
    "window_contract": "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json",
    "receiver_bank_records": "results_radio_hd189733_receiver_2026-09-28/bank_records.json",
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON member")
        out[key] = value
    return out


def parse(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def same(left, right):
    if canonical(left) != canonical(right):
        raise ValueError("canonical type/value differs")


def raw_pin(raw):
    return {"bytes": len(raw), "sha256": sha(raw),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def authenticate(raw, pin):
    if type(raw) is not bytes or type(pin) is not dict or set(pin) != {"bytes", "sha256"}:
        raise ValueError("external raw pin required")
    if type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= 2 * MIB:
        raise ValueError("external raw byte bound")
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("external raw pin differs")
    return parse(raw)


def read(root, relative, maximum=2 * MIB):
    """Reject traversal, symlink ancestors, hardlinks and unstable held files."""
    root = Path(root)
    pure = PurePosixPath(relative)
    if not root.is_absolute() or root.resolve() != root or pure.is_absolute() or pure.as_posix() != relative or ".." in pure.parts:
        raise ValueError("canonical contained path required")
    path = root
    for part in pure.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink component refused")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
            raise ValueError("ordinary bounded single-link input required")
        raw = handle.read(maximum + 1)
        after = os.fstat(handle.fileno())
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        current = path.lstat()
        if len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key)
                                            or getattr(before, key) != getattr(current, key) for key in fields):
            raise ValueError("input changed while reading")
    return raw


def inspect_documents(raws):
    """Exact H raw pins, not a rewritten ready version of the original plan."""
    if set(raws) != set(H_PINS):
        raise ValueError("exact four H documents required")
    for name, (size, digest) in H_PINS.items():
        if type(raws[name]) is not bytes or len(raws[name]) != size or sha(raws[name]) != digest:
            raise ValueError("immutable H document changed: " + name)
    plan, manifest, selection = (parse(raws[name]) for name in ("PLAN.json", "INPUT_MANIFEST.json", "SELECTED_CODE.json"))
    if plan["execution_enabled"] is not False or plan["status"] != "SOURCE_ONLY_NO_DISPATCH":
        raise ValueError("H preparation authority changed")
    same(plan["input_manifest_sha256"], sha(raws["INPUT_MANIFEST.json"]))
    same(plan["selection_manifest_sha256"], sha(raws["SELECTED_CODE.json"]))
    return plan, manifest, selection


def selected_nodes(raw, selection):
    wanted = selection["assignments"] + selection["functions"] + selection["classes"]
    found = {}
    for node in ast.parse(raw).body:
        name = node.name if isinstance(node, (ast.ClassDef, ast.FunctionDef)) else (
            node.targets[0].id if isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name) else None)
        if name in wanted:
            if name in found:
                raise ValueError("duplicate selected node")
            found[name] = node
    if set(found) != set(wanted):
        raise ValueError("missing selected node")
    return [found[name] for name in wanted]


def load_memory(name, raw, display_path):
    """Compile authenticated memory; never reopen source during import."""
    if name in sys.modules:
        raise ValueError("fresh module namespace required")
    module = ModuleType(name)
    module.__file__ = str(display_path)
    sys.modules[name] = module
    try:
        exec(compile(raw, str(display_path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def verify_inputs(repo_root):
    root = Path(repo_root)
    raws = {name: read(root, H_ROOT + name) for name in H_PINS}
    plan, manifest, selection = inspect_documents(raws)
    contents, total = {}, 0
    for relative, expected in manifest["files"].items():
        raw = read(root, relative)
        same(raw_pin(raw), expected)
        total += len(raw)
        if total > 4 * MIB:
            raise ValueError("authority byte budget exceeded")
        contents[relative] = raw
    same(total, manifest["total_raw_bytes"])
    for relative, spec in selection["source_selections"].items():
        same(raw_pin(contents[relative]), spec["raw_file_pin"])
        lines = contents[relative].decode().splitlines(keepends=True)
        nodes = selected_nodes(contents[relative], spec)
        for node, expected in zip(nodes, spec["nodes"]):
            segment = "".join(lines[node.lineno - 1:node.end_lineno]).encode()
            same({"name": node.name if hasattr(node, "name") else node.targets[0].id,
                  "node_type": type(node).__name__, "first_line": node.lineno, "last_line": node.end_lineno,
                  "bytes": len(segment), "sha256": sha(segment)}, expected)
    return {"plan": plan, "manifest": manifest, "selection": selection,
            "contents": contents, "h_raws": raws, "authority_bytes": total}


def verify_receiver_contexts(inputs):
    """Run the maintained metadata validator for both roles; never its loader."""
    name = "_codec12_I_receiver_metadata"
    module = load_memory(name, inputs["contents"][RECEIVER], RECEIVER)
    try:
        raw = {key: inputs["contents"][path] for key, path in METADATA_PATHS.items()}
        pins = {key: {field: inputs["manifest"]["files"][path][field] for field in ("bytes", "sha256")}
                for key, path in METADATA_PATHS.items()}
        basis = parse(inputs["contents"][BASIS])["basis"]
        contexts = {role: module.validate_receiver_metadata(raw, pins, expected_basis=basis, role=role) for role in ROLES}
        for i, handoff in enumerate(inputs["plan"]["scope"]["ordered_handoffs"]):
            same([handoff["handoff_index"], handoff["role"], handoff["scan"]], [i, ROLES[i // 6], LABELS[i % 6]])
            same(handoff["receiver_context_sha256"], contexts[handoff["role"]]["context_sha256"])
            same(handoff["receiver_bank_sha256"], contexts[handoff["role"]]["receiver_bank_sha256"])
        return contexts
    finally:
        sys.modules.pop(name, None)


if __name__ == "__main__":
    raise SystemExit("SOURCE_ONLY: invoke the separate preflight; no control dispatcher exists")
