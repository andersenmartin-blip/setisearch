"""Stdlib-only one-time complete leaf artifact manifest creation."""
import hashlib
import json
from pathlib import Path
import stat
import sys


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError("source-only manifest builder requires -I -B")
    root = Path(__file__).resolve().parent
    destination = root / "LEAF_FILES.json"
    files = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or path.resolve() != path:
            raise ValueError("ordinary complete leaf artifact tree required")
        if path == destination:
            raise ValueError("leaf manifest already created")
        if not 0 <= info.st_size <= 2 * 1024**2:
            raise ValueError("individual leaf artifact byte bound")
        raw = path.read_bytes()
        if len(raw) != info.st_size:
            raise ValueError("leaf artifact changed")
        files[path.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    total = sum(pin["bytes"] for pin in files.values())
    if not 0 < total <= 4 * 1024**2:
        raise ValueError("leaf manifest aggregate byte bound")
    value = {"schema": "codec16-G-leaf-artifacts-v1", "files": files,
             "total_raw_bytes": total, "self_hash_excluded": True}
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with destination.open("xb") as handle:
        handle.write(raw)
    print(json.dumps({"path": str(destination), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "files": len(files), "total_artifact_raw_bytes": total}, sort_keys=True))


if __name__ == "__main__":
    main()
