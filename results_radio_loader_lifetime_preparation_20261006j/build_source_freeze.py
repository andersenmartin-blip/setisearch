"""Inert J source snapshot; self-excluded, no executable allocation or gate."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main():
    files = [pin(path) for path in sorted(HERE.iterdir()) if path.is_file()
             and path.name not in ("SOURCE_FREEZE.json", "PUBLICATION_MANIFEST.json", "PUBLIC_READBACK.json")]
    value = {"schema": "loader-J-inert-source-freeze-v1", "status": "SOURCE_COMPONENT_NO_COLLECTOR_NO_DISPATCH",
             "authority_commit": "71d0073faac7cd1a487e950f28a6f74b7daf75ab", "files": files,
             "file_count": len(files), "total_raw_bytes": sum(row["bytes"] for row in files),
             "source_snapshot_is_executable_freeze": False, "self_excluded": True,
             "execution_enabled": False, "allocation_or_activation_created": False}
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with (HERE / "SOURCE_FREEZE.json").open("xb") as handle: handle.write(raw)
    print(json.dumps({"files": len(files), "bytes": value["total_raw_bytes"], "sha256": hashlib.sha256(raw).hexdigest()}))


if __name__ == "__main__":
    main()
