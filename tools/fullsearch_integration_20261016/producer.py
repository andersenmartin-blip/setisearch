#!/usr/bin/env python3
"""Once-only complete detector execution on a frozen engineering fixture.

This is a new namespace, not admission or reopening of any scientific bank.  No
old main, generator or random API is called.  Actual parent whole-child resource
closure is only known after this process exits; status/data_integrity/resource
closure fields are intentionally left for the documented parent/summary bridge.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

STARTED = time.monotonic()
HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
LEGACY = SOURCE / "analysis/sixscan_burst_20261015"
sys.path.insert(0, str(HERE))
from fixture import IDENTITY, MODE, build_inputs, fixture_spec, recipe, truths

LOG_CAP = 64 * 1024
RECEIPT_CAP = 4 * 1024 ** 2


class BoundedText:
    """Bound controlled Python logs; native fd writers remain a parent gate."""
    def __init__(self, stream):
        self.stream, self.remaining, self.overflow = stream, LOG_CAP, False
    def write(self, text):
        text = str(text); raw = text.encode("utf-8", errors="replace")
        kept = raw[:self.remaining]; self.remaining -= len(kept)
        self.overflow |= len(kept) != len(raw)
        self.stream.write(kept.decode("utf-8", errors="ignore")); return len(text)
    def flush(self): self.stream.flush()
    def isatty(self): return False


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""): value.update(block)
    return value.hexdigest()


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    require(len(raw) <= RECEIPT_CAP, "Producer side receipt exceeds4MiB bound")
    with Path(path).open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def import_path(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def authenticate_scope(scope_path, expected_sha256):
    require(sha(scope_path) == expected_sha256, "Exact frozen engineering scope bytes required")
    scope = json.loads(Path(scope_path).read_text())
    require(scope.get("mode") == MODE and scope.get("identity") == IDENTITY,
            "New engineering namespace/mode required")
    pins = scope.get("source_pins", scope.get("code_pins"))
    require(isinstance(pins, list) and pins, "Frozen source pins required before numerical imports")
    observed = {}
    for pin in pins:
        relative = Path(pin["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe source pin")
        path = (SOURCE / relative).resolve()
        require(SOURCE in path.parents, "Pin must resolve inside source checkout")
        require(relative.as_posix() not in observed, "Duplicate frozen source pin")
        require(path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"],
                "Frozen source pin differs: " + relative.as_posix())
        observed[relative.as_posix()] = {"bytes": pin["bytes"], "sha256": pin["sha256"]}
    required = {"tools/fullsearch_integration_20261016/producer.py",
        "tools/fullsearch_integration_20261016/fixture.py", "tools/science_payload_20261016/payload.py",
        "analysis/sixscan_burst_20261015/worker.py", "analysis/sixscan_burst_20261015/detector.py",
        "analysis/sixscan_burst_20261015/contract.json"}
    require(required <= observed.keys(), "Incomplete producer prerequisite source freeze")
    return scope, observed


def legacy_pins():
    return {name: {"sha256": sha(LEGACY / name), "bytes": (LEGACY / name).stat().st_size}
            for name in ("worker.py", "detector.py", "qa.py", "summarize.py", "contract.json")}


def census(result):
    hits = result["all_ON_threshold_hypotheses"]
    return {"ON_hit_count": len(hits),
        "OFF_matched_ON_hit_count": sum(h["disposition"] == "OFF_MATCHED" for h in hits),
        "OFF_surviving_ON_hit_count": sum(h["disposition"] == "SURVIVOR_EXPLORATORY" for h in hits),
        "maximum_pre_OFF_ON_score": result["maximum_pre_OFF_ON_score"],
        "drift_grid_count": len(result["geometry"]["drift_grid_hz_s"]),
        "OFF_halo_channels": result["geometry"]["OFF_reference_halo_channels"],
        "scans": [{"scan_id": m["scan_id"], "role": m["role"],
            "retained_shape": list(m["scores"].shape),
            "original_grid_hypotheses": int(m["total_original_hypothesis_count"].sum()),
            "unique_native_hypotheses": int(m["total_unique_native_hypothesis_count"].sum()),
            "maximum_retained_score": float(m["scores"].max())}
            for m in result["scan_maps"]],
        "OFF_inventory_rows": {name: cert["inventory_rows"]
                               for name, cert in result["OFF_inventory_certificates"].items()},
        "rank_status": "NOT_APPLIED_NO_CALIBRATION"}


def produce(folder, *, payload_cap, scope_path, scope_sha256):
    # Read/hash metadata and claim a new engineering directory before numerical
    # imports or input construction. Parent guards/reserves the entire child.
    scope, observed = authenticate_scope(scope_path, scope_sha256)
    require(type(payload_cap) is int and payload_cap > 0, "Positive enforced payload cap required")
    require(payload_cap == scope["resources"]["payload_cap_bytes"],
            "Payload CLI cap differs from the exact frozen engineering scope")
    folder = Path(folder).resolve(); folder.mkdir()
    save(folder / "ENGINEERING_CLAIM.json", {"identity": IDENTITY, "mode": MODE,
         "scope_sha256": scope_sha256, "status": "CLAIMED_ONCE_BEFORE_NUMERICAL_IMPORTS",
         "no_retry_or_redraw": True, "scientific_admission": False})
    worker = import_path(LEGACY / "worker.py", "fullsearch_engineering_legacy_worker")
    import numpy as np
    detector = import_path(LEGACY / "detector.py", "fullsearch_engineering_legacy_detector")
    transport = import_path(SOURCE / "tools/science_payload_20261016/payload.py",
                            "fullsearch_engineering_payload")
    contract = json.loads((LEGACY / "contract.json").read_text())
    raw = build_inputs(np, contract)
    metadata = contract["geometry"]["scan_metadata"]
    authenticated = worker.authenticate_arrays(raw, metadata, contract["geometry"], np)
    scans, corefirst = worker.scan_inputs(raw, metadata, contract["geometry"], detector, np)
    for value in raw: value.flags.writeable = False
    truth, diagnostic_truth = truths(contract, worker.canonical_truth, authenticated)
    admission = {"status": "FROZEN_ENGINEERING_FIXTURE_ONLY_NOT_SCIENTIFIC_ADMISSION", "mode": MODE,
        "identity": IDENTITY, "scope_sha256": scope_sha256, "observed_source_pins": observed,
        "checked_before_numerical_imports_and_fixture_construction": True,
        "old_GO_or_scientific_admission_reused": False, "old_scientific_identity_reused": False,
        "scientific_admission": False, "scientific_bank_admission": False, "qualified_SETI_detection": False,
        "original_A_B": "FAIL_CLOSED", "original_pilot_admitted": False, "new_observation": False}
    print(json.dumps({"stage": "ACTUAL_COMPLETE_SEARCH_STARTED", "identity": IDENTITY,
                      "raw_shapes": [list(a.shape) for a in raw]}), flush=True)
    result = detector.search_cadence(scans, corefirst, detector.Config())
    # This is the original full-case inventory check, not a narrowed fixture
    # substitute: all4096/halo carriers, top5 maps and every OFF record persist.
    worker.verify_result_inventory(result, metadata, corefirst, np)
    require(worker.authenticate_arrays(raw, metadata, contract["geometry"], np) == authenticated,
            "Actual search changed deterministic input bytes")
    result["calibrationglobal_ON_max"] = result["maximum_pre_OFF_ON_score"]
    result["recovery"] = detector.recovery(result, truth)
    result["fixture_diagnostic_recovery"] = {name: detector.recovery(result, value)
                                             for name, value in diagnostic_truth.items()}
    result.update(case_index=0, exposed=False, case_id=IDENTITY, input_array_hashes=authenticated,
        no_retry_or_redraw=True, generation_call_count=0, admission=admission,
        engineering_fixture=True, deterministic_counterhash_fixture_construction_count=1,
        rank_status="NOT_APPLIED_NO_CALIBRATION")
    require(result["recovery"]["all_active_ON_pre_OFF_recovered"] is True,
            "Fixed primary probe was not recovered before OFF")
    require(result["recovery"]["all_active_ON_final_recovered"] is True,
            "Fixed isolated primary probe was not recovered after OFF")
    matched = result["fixture_diagnostic_recovery"]["matched"]
    require(matched["all_active_ON_pre_OFF_recovered"] is True,
            "Fixed matched probe was not recovered before OFF")
    require(matched["at_least_one_active_ON_final_recovered"] is False,
            "Fixed ON/OFF matched probe unexpectedly survived OFF")
    actual_census = census(result)
    require(actual_census["OFF_matched_ON_hit_count"] > 0 and actual_census["OFF_surviving_ON_hit_count"] > 0,
            "Both actual matched and surviving ON hypotheses required")
    require(sum(actual_census["OFF_inventory_rows"].values()) > 0,
            "At least one actual complete OFF inventory must be nonempty")
    require(actual_census["drift_grid_count"] == 5723,
            "Exact frozen full global drift grid5723 required")
    encoded, arrays, descriptors = worker.json_and_array_store(result, np)
    payload_value = {"worker_json": encoded, "worker_arrays": arrays, "legacy_descriptors": descriptors,
        "truth": truth, "case": recipe(), "admission": admission,
        "inputs": {s["scan_id"]: a for s, a in zip(metadata, raw)},
        "fixture_spec": fixture_spec(contract), "diagnostic_truth_by_track": diagnostic_truth, "contract": contract}
    print(json.dumps({"stage": "ACTUAL_COMPLETE_SEARCH_FINISHED_SERIALIZING", "census": actual_census,
                      "legacy_array_count": len(arrays)}), flush=True)
    payload_receipt = transport.write_payload(folder / "payload", payload_value, cap=payload_cap)
    require(sha(scope_path) == scope_sha256, "Frozen engineering scope changed during producer")
    authenticate_scope(scope_path, scope_sha256)
    receipt = {"schema": "SETI_FULLSEARCH_PAYLOAD_ENGINEERING_PRODUCER_V1",
        "identity": IDENTITY, "status": "PRODUCED_COMPLETE_SEARCH_ENGINEERING_ONLY", "mode": MODE,
        "scope_sha256": scope_sha256, "legacy_code_pins": legacy_pins(),
        "payload_receipt": payload_receipt, "legacy_array_count": len(arrays),
        "input_hashes": authenticated, "output_census": actual_census,
        "actual_full_search_performed": True, "actual_legacy_inventory_verifier_called": True,
        "complete_full_case_arrays_and_descriptors_retained": True,
        "fixed_fixture_intended_behaviors_observed": {"primary_pre_OFF": True, "primary_after_OFF": True,
                                                    "matched_pre_OFF": True, "matched_after_OFF": False},
        "closure_fields_left_for_exact_parent_guard_bridge": ["status", "data_integrity_ok", "resource_receipt"],
        "RNG_called": False, "old_scientific_mains_called": False, "generator_called": False,
        "calibration_panel_run": False, "rank_status": "NOT_APPLIED_NO_CALIBRATION",
        "raw_fixture_construction_count": 1, "wall_s_before_parent_reap": time.monotonic() - STARTED,
        "producer_self_measurement_is_not_parent_resource_acceptance": True,
        "scientific_admission": False, "scientific_bank_admission": False, "qualified_SETI_detection": False,
        "original_A_B": "FAIL_CLOSED", "new_observation": False}
    save(folder / "PRODUCER.json", receipt)
    print(json.dumps({"status": receipt["status"], "legacy_array_count": len(arrays),
                      "payload_bytes": payload_receipt["payload_bytes"],
                      "ON_hits": actual_census["ON_hit_count"],
                      "OFF_inventory_rows": actual_census["OFF_inventory_rows"]}), flush=True)
    return receipt


def main():
    stdout, stderr = BoundedText(sys.stdout), BoundedText(sys.stderr)
    sys.stdout, sys.stderr = stdout, stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--payload-cap", type=int, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--scope-sha256", required=True)
    args = parser.parse_args()
    produce(args.folder, payload_cap=args.payload_cap, scope_path=args.scope,
            scope_sha256=args.scope_sha256)
    require(not stdout.overflow and not stderr.overflow, "Controlled Python log quota exceeded")


if __name__ == "__main__":
    main()
