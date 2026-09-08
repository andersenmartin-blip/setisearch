"""Reassemble the published M43Z ledger without changing any original byte."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "results_m43z_joint_controls/ledger_parts"

def main():
    index = json.loads((PARTS / "index.json").read_text())
    chunks = []
    for entry in index["parts"]:
        name = entry["path"]
        if Path(name).name != name:
            raise ValueError("Invalid part path")
        data = (PARTS / name).read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Part mismatch: {name}")
        chunks.append(data)
    data = b"".join(chunks)
    if len(data) != index["bytes"] or hashlib.sha256(data).hexdigest() != index["sha256"]:
        raise ValueError("Ledger mismatch")
    destination = ROOT / "results_m43z_joint_controls/case_audits.jsonl.gz"
    if destination.exists():
        if destination.read_bytes() != data:
            raise ValueError("Existing ledger differs; preserved without overwrite")
    else:
        temporary = destination.with_suffix(".gz.reconstructing")
        temporary.write_bytes(data)
        temporary.replace(destination)
    print(f"Verified original ledger: {len(data)} bytes; SHA256 {index['sha256']}")

if __name__ == "__main__":
    main()
