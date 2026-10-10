#!/usr/bin/env python3
"""Once-only metadata scope assembly. Does not read cached prefix binaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
FAMILY = "radio_visit2019_blc66_structure_20261010"
INITIAL = "radio_visit2019_blc66_headers_20261010"
TOOLS = ROOT / "tools" / FAMILY
PROOFS = ("OFFICIAL_FORMAT_RESEARCH.json", "INDEPENDENT_SOURCE_REVIEW.json",
          "TOY_FIXTURE_SOURCE_PEER.json", "HDF5_TYPED_METADATA_TOY_FIXTURE_V2.py",
          "TOY_FIXTURE_RESULT.json", "PLANNER_AUTHOR_SOURCE_REVIEW.json")
LIMITS = {"CPU_seconds": 20, "wall_seconds": 300, "memory_bytes": 536870912,
          "output_bytes": 4194304, "shared_workspace_bytes": 12884901888}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pin(path):
    require(not path.is_symlink() and path.is_file() and path.resolve() == path,
            "Expected canonical regular metadata/source file")
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_text())


def new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    start = time.process_time()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-go-metadata-only-after-initial-closed", action="store_true")
    args = parser.parse_args()
    require(args.root_go_metadata_only_after_initial_closed, "Root initial-process closure GO required")
    new(TOOLS / "SCOPE_PREPARATION_STARTED_ONCE.json", {"status": "STARTED_METADATA_ONLY_ONCE_NO_RETRY"})
    initial = ROOT / "results" / INITIAL / "initial"
    manifest_path = ROOT / "tools" / INITIAL / "SIX_SOURCE_IDENTITIES.json"
    initial_scope = ROOT / "tools" / INITIAL / "initial_scope.json"
    execution_path, result_path = initial / "EXECUTION_RECEIPT.json", initial / "HEADER_RESULT.json"
    execution, result, identities = read(execution_path), read(result_path), read(manifest_path)
    require(execution["HEADER_RESULT_sha256"] == pin(result_path)["sha256"]
            and execution["resource_caps_satisfied"] is True and execution["no_retry"] is True
            and execution["status"] == result["status"]
            and len(result["sources"]) == len(identities["files"]) == 6
            and result["application_BODY_bytes_received"] == 24576,
            "Initial complete cached-prefix metadata provenance differs")
    sources = []
    for saved, identity in zip(result["sources"], identities["files"]):
        require(all(saved[k] == identity[k] for k in ("source_id", "url", "ordered_index")), "Source order differs")
        prefix = saved["retained_prefix"]
        path = ROOT / prefix["path"]
        require(path.resolve() == path and path.parent == initial / saved["source_id"]
                and path.name == "PREFIX.bin" and not path.is_symlink()
                and path.stat().st_size == prefix["bytes"] == 4096,
                "Declared retained prefix path/size differs")
        # PREFIX.bin bytes are intentionally not opened by this scope producer.
        entry = {k: identity[k] for k in ("source_id", "url", "ordered_index")}
        for key, name in (("HEAD_receipt_pin", "HEAD_RECEIPT.json"),
                          ("PREFIX_receipt_pin", "PREFIX_RECEIPT.json"),
                          ("HEADER_receipt_pin", "HEADER_RECEIPT.json")):
            entry[key] = pin(path.parent / name)
        require(read(path.parent / "HEADER_RECEIPT.json") == saved,
                "Per-source HEADER result copy differs")
        entry["prefix_pin"] = prefix
        sources.append(entry)
    dependencies = {p["path"]: p for p in
                    (pin(TOOLS / name) for name in ("planner.py", "structure.py", "METHOD.md",
                                                   "FIELD_SCHEMA.json", "prepare_scope.py") + PROOFS)}
    require(read(TOOLS / "INDEPENDENT_SOURCE_REVIEW.json")["status"].startswith("PASS"), "Source peer missing")
    toy = read(TOOLS / "TOY_FIXTURE_RESULT.json")
    require(toy["status"] == "PASS_SYNTHETIC_ONLY_HDF5_TYPED_METADATA_FIXTURES_V2"
            and toy["passed_cases"] == 22
            and toy["structure_source_pin"]["sha256"] == pin(TOOLS / "structure.py")["sha256"],
            "Actual final22-case toy binding differs")
    scope = {"schema": "SETI_VISIT2019_TYPED_STRUCTURE_PLAN_SCOPE_V1",
             "script_sha256": pin(TOOLS / "planner.py")["sha256"],
             "parser_sha256": pin(TOOLS / "structure.py")["sha256"],
             "sources": sources, "source_id_manifest_pin": pin(manifest_path),
             "initial_scope_pin": pin(initial_scope), "initial_execution_pin": pin(execution_path),
             "initial_header_result_pin": pin(result_path),
             "output_directory": "results/" + FAMILY + "/measurement",
             "shared_workspace_roots": [str(ROOT.parent), "/workspace/scratch/5bf3860dacd6"],
             "limits": LIMITS, "pinned_provenance_dependencies": dependencies,
             "prefix_binaries_read_by_scope_preparer": False}
    require(time.process_time() <= 5, "Metadata scope preparation CPU cap exceeded")
    (ROOT / "results" / FAMILY).mkdir(exist_ok=True)
    new(TOOLS / "scope.json", scope)
    receipt = {"status": "COMPLETE_METADATA_SCOPE_PREPARATION_NO_PREFIX_BINARY_READ",
               "scope_pin": pin(TOOLS / "scope.json"), "source_pin": pin(Path(__file__).resolve()),
               "input_metadata_end_pins": [pin(p) for p in (manifest_path, initial_scope, execution_path, result_path)],
               "process_CPU_seconds": time.process_time() - start,
               "source_PREFIX_bin_read": False, "parser_or_planner_imported": False, "HTTP_requests": 0}
    new(TOOLS / "SCOPE_PREPARATION_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
