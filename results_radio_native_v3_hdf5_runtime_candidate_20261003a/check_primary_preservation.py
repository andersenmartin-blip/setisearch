"""Read-only byte preservation check; no SETI modules or scientific inputs."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path("/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive")
OUTPUT = ROOT / "results_radio_native_v3_hdf5_runtime_candidate_20261003a"
CAPTURE = ROOT / "results_radio_native_v3_execution_preparation_20261003a/execution-preparation-attempt-2"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pin(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def compare(mapping):
    missing = []
    mismatched = []
    matches = 0
    for name, expected in sorted(mapping.items()):
        path = Path(name)
        if not path.is_file():
            missing.append(name)
            continue
        observed = sha(path)
        expected_sha = expected if isinstance(expected, str) else expected["sha256"]
        if observed != expected_sha or (isinstance(expected, dict) and path.stat().st_size != expected["bytes"]):
            mismatched.append({"path": name, "expected_sha256": expected_sha, "observed_sha256": observed})
        else:
            matches += 1
    return {"expected_count": len(mapping), "matching_count": matches, "missing": missing, "mismatches": mismatched,
            "pass": not missing and not mismatched}


if not sys.dont_write_bytecode or not sys.flags.isolated:
    raise RuntimeError("preservation check requires -I -B")
freeze_path = CAPTURE / "complete-freeze.json"
plan_path = CAPTURE / "plan.json"
freeze = json.loads(freeze_path.read_bytes())
plan = json.loads(plan_path.read_bytes())
runtime = compare(freeze["runtime_sha256s"])
supplement = compare(plan["engineering_runtime_supplement"]["files"])
stdlib = Path("/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12")
current_pyc = {str(p) for p in stdlib.rglob("*.pyc") if "site-packages" not in p.parts}
expected_pyc = {name for name in plan["engineering_runtime_supplement"]["files"] if name.endswith(".pyc")}
source = ROOT / "src/seti_repeater/prospective_source_metadata_radio.py"
tree = ast.parse(source.read_bytes())
assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id == "MISSING_FIELDS" for target in node.targets)]
if len(assignments) != 1:
    raise RuntimeError("scientific source MISSING_FIELDS assignment differs")
fields = ast.literal_eval(assignments[0].value)
expected_source = "2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360"
source_pin = pin(source)
source_unchanged = source_pin["bytes"] == 31819 and source_pin["sha256"] == expected_source
result = {"schema": "radio-native-v3-hdf5-candidate-primary-preservation-v1", "authority": "candidate-preparation-only",
          "frozen_runtime_reference": pin(freeze_path), "frozen_plan_reference": pin(plan_path),
          "frozen_runtime_byte_comparison": runtime, "engineering_supplement_byte_comparison": supplement,
          "primary_stdlib_bytecode_inventory": {"expected_count": len(expected_pyc), "observed_count": len(current_pyc),
          "added": sorted(current_pyc - expected_pyc), "missing": sorted(expected_pyc - current_pyc),
          "pass": current_pyc == expected_pyc}, "scientific_source": source_pin,
          "scientific_source_unchanged": source_unchanged,
          "scientific_gate_extraction": "AST literal only; no project module imported",
          "scientific_missing_fields": list(fields), "scientific_missing_field_count": len(fields),
          "scientific_gates_changed": not source_unchanged,
          "frozen_primary_material_changed": not (runtime["pass"] and supplement["pass"] and current_pyc == expected_pyc),
          "candidate_qualification_is_source_admission": False}
result["pass"] = runtime["pass"] and supplement["pass"] and current_pyc == expected_pyc and source_unchanged and len(fields) == 11
raw = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
target = OUTPUT / "primary-preservation.json"
with target.open("xb") as handle:
    handle.write(raw)
    handle.flush()
    os.fsync(handle.fileno())
print(json.dumps({"pass": result["pass"], "report": pin(target), "runtime_matches": runtime["matching_count"],
                  "supplement_matches": supplement["matching_count"], "bytecode_count": len(current_pyc),
                  "missing_scientific_gates": len(fields)}, sort_keys=True))
if not result["pass"]:
    raise SystemExit(1)
