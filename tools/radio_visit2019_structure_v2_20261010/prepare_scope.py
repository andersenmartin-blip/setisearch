#!/usr/bin/env python3
"""Once-only metadata scope assembly. Does not read cached prefix binaries."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
FAMILY = "radio_visit2019_structure_v2_20261010"
TOOLS = ROOT / "tools" / FAMILY
PROOFS = ("OFFICIAL_IMPLEMENTATION_COMPATIBILITY.json", "INDEPENDENT_SOURCE_REVIEW.json",
          "PLANNER_INDEPENDENT_SOURCE_REVIEW.json",
          "HDF5_TYPED_METADATA_TOY_FIXTURE_V3.py", "TOY_FIXTURE_RESULT.json",
          "PLANNER_AUTHOR_SOURCE_REVIEW.json")
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
    parser.add_argument("--initial-family", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--root-go-metadata-only-after-initial-closed", action="store_true")
    args = parser.parse_args()
    require(args.root_go_metadata_only_after_initial_closed, "Root initial-process closure GO required")
    INITIAL = args.initial_family
    require(re.fullmatch(r'radio_visit2019_s[0-9]+_blc[0-9]+_headers_20261010', INITIAL)
            and re.fullmatch(r'[0-9a-f]{64}', args.expected_manifest_sha256),
            "Exact new separately admitted transport manifest required")
    new(TOOLS / "SCOPE_PREPARATION_STARTED_ONCE.json", {"status": "STARTED_METADATA_ONLY_ONCE_NO_RETRY"})
    initial = ROOT / "results" / INITIAL / "initial"
    manifest_path = ROOT / "tools" / INITIAL / "SIX_SOURCE_IDENTITIES.json"
    initial_scope = ROOT / "tools" / INITIAL / "initial_scope.json"
    execution_path, result_path = initial / "EXECUTION_RECEIPT.json", initial / "HEADER_RESULT.json"
    execution, result, identities = read(execution_path), read(result_path), read(manifest_path)
    original = read(initial_scope)
    require(pin(manifest_path)["sha256"] == args.expected_manifest_sha256
            and original["schema"] == "SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_SCOPE_V1"
            and original["candidate_metadata_sha256"] == args.expected_manifest_sha256
            and original["candidate_metadata_path"] == str(manifest_path.relative_to(ROOT))
            and original["sources"] == identities["files"]
            and identities["family_id"] == INITIAL,
            "Exact source manifest/scope binding differs")
    prefix_bytes = original["prefix_bytes"]
    require(type(prefix_bytes) is int and 4096 <= prefix_bytes <= 65536 and prefix_bytes % 512 == 0,
            "Frozen actual prefix extent differs")
    root_admission_path = ROOT / original["root_admission_path"]
    root = read(root_admission_path)
    require(root_admission_path.resolve() == root_admission_path
            and root_admission_path.parent == ROOT / "results" / INITIAL
            and root_admission_path.name == "ROOT_ADMISSION.json"
            and pin(root_admission_path)["sha256"] == execution["root_admission_sha256"],
            "Initial actual root admission pin differs")
    metadata_paths = [manifest_path, initial_scope, execution_path, result_path, root_admission_path]
    before_pins = [pin(p) for p in metadata_paths]
    require(execution["HEADER_RESULT_sha256"] == pin(result_path)["sha256"]
            and execution["resource_caps_satisfied"] is True and execution["no_retry"] is True
            and execution["status"] == result["status"] == "COMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_VALUES_ADMISSION"
            and result["schema"] == "SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_RESULT_V1"
            and result["all_six_exact_prefix_pairs_complete"] is True
            and execution["scope_sha256"] == pin(initial_scope)["sha256"]
            and execution["wrapper_sha256"] == original["wrapper_sha256"]
            and len(result["sources"]) == len(identities["files"]) == 6
            and result["application_BODY_bytes_received"] == result["application_BODY_charged_upper_bound_bytes"] == 6 * prefix_bytes,
            "Initial complete cached-prefix metadata provenance differs")
    sources = []
    for saved, identity in zip(result["sources"], identities["files"]):
        require(all(saved[k] == identity[k] for k in ("source_id", "url", "ordered_index")), "Source order differs")
        prefix = saved["retained_prefix"]
        path = ROOT / prefix["path"]
        require(path.resolve() == path and path.parent == initial / saved["source_id"]
                and path.name == "PREFIX.bin" and not path.is_symlink()
                and path.stat().st_size == prefix["bytes"] == prefix_bytes,
                "Declared retained prefix path/size differs")
        # PREFIX.bin bytes are intentionally not opened by this scope producer.
        entry = {k: identity[k] for k in ("source_id", "url", "ordered_index")}
        for key, name in (("HEAD_receipt_pin", "HEAD_RECEIPT.json"),
                          ("PREFIX_receipt_pin", "PREFIX_RECEIPT.json"),
                          ("HEADER_receipt_pin", "HEADER_RECEIPT.json")):
            entry[key] = pin(path.parent / name)
            metadata_paths.append(path.parent / name)
            before_pins.append(entry[key])
        require(read(path.parent / "HEADER_RECEIPT.json") == saved,
                "Per-source HEADER result copy differs")
        entry["prefix_pin"] = prefix
        sources.append(entry)
    dependencies = {p["path"]: p for p in
                    (pin(TOOLS / name) for name in ("planner.py", "structure.py", "METHOD.md",
                                                   "FIELD_SCHEMA.json", "prepare_scope.py") + PROOFS)}
    parser_sha = pin(TOOLS / "structure.py")["sha256"]
    fixture_sha = pin(TOOLS / "HDF5_TYPED_METADATA_TOY_FIXTURE_V3.py")["sha256"]
    pure_peer = read(TOOLS / "INDEPENDENT_SOURCE_REVIEW.json")
    require(pure_peer["schema"] == "SETI_VISIT2019_TYPED_PARSER_V2_SOURCE_ONLY_PEER_REVIEW_V1"
            and pure_peer["status"] == "PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES"
            and pure_peer["parser_sha256"] == parser_sha and pure_peer["fixture_sha256"] == fixture_sha,
            "Exact parser/fixture source peer binding differs")
    for filename, schema in (("PLANNER_INDEPENDENT_SOURCE_REVIEW.json", "SETI_VISIT2019_TYPED_TRANSPORT_PLANNER_V2_SOURCE_PEER_REVIEW_V1"),
                             ("PLANNER_AUTHOR_SOURCE_REVIEW.json", "SETI_VISIT2019_TYPED_TRANSPORT_PLANNER_V2_AUTHOR_SOURCE_REVIEW_V1")):
        review = read(TOOLS / filename)
        require(review["schema"] == schema and review["status"] == "PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES"
                and review["planner_sha256"] == pin(TOOLS / "planner.py")["sha256"]
                and review["preparer_sha256"] == pin(Path(__file__).resolve())["sha256"]
                and review["parser_sha256"] == parser_sha and review["fixture_sha256"] == fixture_sha,
                "Exact planner/preparer source review binding differs")
    toy = read(TOOLS / "TOY_FIXTURE_RESULT.json")
    require(toy["status"] == "PASS_SYNTHETIC_ONLY_HDF5_TYPED_METADATA_FIXTURES_V3"
            and toy["passed_cases"] == 24
            and toy["structure_source_pin"]["sha256"] == parser_sha
            and toy["fixture_source_sha256"] == fixture_sha,
            "Actual final24-case toy binding differs")
    scope = {"schema": "SETI_VISIT2019_TYPED_STRUCTURE_PLAN_SCOPE_V2",
             "initial_family": INITIAL, "cache_prefix_bytes": prefix_bytes,
             "initial_root_admission_schema": root["schema"],
             "script_sha256": pin(TOOLS / "planner.py")["sha256"],
             "parser_sha256": pin(TOOLS / "structure.py")["sha256"],
             "sources": sources, "source_id_manifest_pin": pin(manifest_path),
             "initial_scope_pin": pin(initial_scope), "initial_execution_pin": pin(execution_path),
             "initial_header_result_pin": pin(result_path),
             "output_directory": "results/" + FAMILY + "/measurement",
             "shared_workspace_roots": [str(ROOT.parent), "/workspace/scratch/5bf3860dacd6"],
             "limits": LIMITS, "pinned_provenance_dependencies": dependencies,
             "prefix_binaries_read_by_scope_preparer": False}
    require([pin(p) for p in metadata_paths] == before_pins, "Metadata changed during scope preparation")
    require(time.process_time() <= 5, "Metadata scope preparation CPU cap exceeded")
    (ROOT / "results" / FAMILY).mkdir(exist_ok=True)
    new(TOOLS / "scope.json", scope)
    receipt = {"status": "COMPLETE_METADATA_SCOPE_PREPARATION_NO_PREFIX_BINARY_READ",
               "scope_pin": pin(TOOLS / "scope.json"), "source_pin": pin(Path(__file__).resolve()),
               "input_metadata_end_pins": [pin(p) for p in metadata_paths],
               "process_CPU_seconds": time.process_time() - start,
               "source_PREFIX_bin_read": False, "parser_or_planner_imported": False, "HTTP_requests": 0}
    new(TOOLS / "SCOPE_PREPARATION_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
