"""Immutable method and input gates shared by the separate D002 phase."""
import csv
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / "work_harps_20261101"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def table(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def csvout(path, data, fields=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gates(public=True):
    freeze = json.loads((HERE / "FREEZE.json").read_text())
    for name, expected in freeze["source_hashes"].items():
        assert sha(ROOT / name) == expected, "Frozen source changed: " + name
    if public:
        readback = json.loads((HERE / "PUBLIC_METHOD_READBACK.json").read_text())
        assert readback["freeze_sha256"] == sha(HERE / "FREEZE.json")
        assert readback["all_method_files_exact"] and readback["method_commit"]
        assert readback["new_science_values_read_at_readback"] == 0
    return freeze


def inputs():
    freeze = gates()
    selected = table(HERE / "metadata/VERIFIED_COHORT54.csv")
    records = json.loads((HERE / "acquisition/MANIFEST.json").read_text())
    byid = {r["dp_id"]: r for r in records}
    assert len(selected) == len(records) == len(byid) == 54
    for row in selected:
        record = byid[row["dp_id"]]
        if record.get("sha256"):
            assert sha(HERE / record["relative_path"]) == record["sha256"], row["dp_id"]
    return freeze, selected, byid


def methods():
    reader = load_module("d002_original_reader", BASE / "code/harps_detector.py")
    detector = load_module("d002_original_v2", BASE / "v2/code/profile_detector.py")
    config = json.loads((BASE / "v2/code/CONFIG.json").read_text())
    return reader.read_spectrum, detector.analyze_arrays, config, detector
