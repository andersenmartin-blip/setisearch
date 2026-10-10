"""Prepare metadata/opaque-byte pins for saved-output verification; no arrays opened.

The original four searches, output files and terminal statuses are never changed.
No NumPy, HDF5, detector, profile or HTTP code is imported or executed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_next_bands_20261010"
RESULTS = "results/radio_next_bands_20261010"
OLD_SCOPE = TOOLS + "/scope.json"
OLD_WRAPPER = TOOLS + "/native_search.py"
OLD_SCOPE_SHA = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
OLD_WRAPPER_SHA = "f189abc0a27503cbf2a35b1c63626ef2d3847728894a0a4fcfce9b16da36800b"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
ACCEPT = RESULTS + "/acceptance"
MANIFEST = ACCEPT + "/ORIGINAL_OUTPUT_BYTES_MANIFEST.json"
META = ACCEPT + "/TERMINAL_METADATA_REVIEW.json"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((ROOT/name).read_text())


def pin(name):
    path = ROOT/name
    return {"path": name, "sha256": digest(path), "bytes": path.stat().st_size}


def write_new(name, value):
    path = ROOT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def metadata_inventory():
    began = time.process_time()
    assert digest(ROOT/OLD_SCOPE) == OLD_SCOPE_SHA
    assert digest(ROOT/OLD_WRAPPER) == OLD_WRAPPER_SHA
    scope = read(OLD_SCOPE)
    for name, sha in scope["pinned_dependency_files"].items():
        assert digest(ROOT/name) == sha, name
    jobs, files = [], []
    for chunk in (153, 154):
        for batch in (1, 2):
            base = f"{RESULTS}/chunk{chunk}/batch_{batch:02d}/measurement"
            destination = f"{ACCEPT}/chunk{chunk}/batch_{batch:02d}"
            qs = list(range(1, 128)) if batch == 1 else list(range(128, 255))
            failed = (chunk, batch) != (153, 2)
            terminal_name = base + ("/FAILURE_RECEIPT.json" if failed else "/EXECUTION_RECEIPT.json")
            terminal, checkpoint = read(terminal_name), read(base+"/DRIFT_CHECKPOINT.json")
            expected_status = "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY" if failed else "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
            assert terminal["status"] == expected_status
            assert terminal["source_chunk_id"] == chunk and terminal["batch_id"] == batch
            assert terminal["fixed_batch_q"] == qs
            if failed:
                assert terminal["error_type"] == "ResourceLimitExceeded"
                assert terminal["error"] == "Measured use exceeds frozen native-band batch caps"
                assert terminal["completed_scan_tiles"] == 381 and terminal["completed_profiles"] == 9
                assert terminal["checkpoint_sha256"] == digest(ROOT/base/"DRIFT_CHECKPOINT.json")
                assert terminal["profile_checkpoint_sha256"] == digest(ROOT/base/"FIXED_TOP3_PROFILES.json")
                assert terminal["retry_authorized"] is False
                assert not (ROOT/base/"EXECUTION_RECEIPT.json").exists()
            else:
                assert terminal["scope_sha256"] == OLD_SCOPE_SHA
                assert terminal["script_sha256"] == OLD_WRAPPER_SHA
                assert terminal["search_summary"]["completed_scan_tiles"] == 381
                assert terminal["fixed_profile_summary"]["profile_count"] == 9
                assert not (ROOT/base/"FAILURE_RECEIPT.json").exists()
            usage = {key: terminal[key] for key in ("process_CPU_seconds_including_imports", "wall_seconds_including_imports", "peak_RSS_bytes")}
            assert (usage["process_CPU_seconds_including_imports"] > 1500) == failed
            assert usage["wall_seconds_including_imports"] <= 1800
            assert usage["peak_RSS_bytes"] <= 4*1024**3
            assert checkpoint["source_chunk_id"] == chunk and checkpoint["batch_id"] == batch
            assert checkpoint["complete"] is True
            assert checkpoint["fixed_batch_q"] == qs
            assert checkpoint["completed_scan_tiles"] == checkpoint["expected_scan_tiles"] == 381
            assert checkpoint["completed_q_by_ON"] == {label: qs for label in ONS}
            receipts = checkpoint["completed_receipts"]
            assert len(receipts) == 381
            assert {(r["scan_id"], r["reference_core_q"]) for r in receipts} == {(label, q) for label in ONS for q in qs}
            for item in receipts:
                assert item["tile_index"] == qs.index(item["reference_core_q"])
                assert item["searched_carriers"] == 4096 and item["valid_hypotheses_per_carrier"] == 1526
                for pathkey, hashkey, sizekey in (("path", "sha256", "bytes"), ("normalization_path", "normalization_sha256", "normalization_bytes")):
                    path = ROOT/base/item[pathkey]
                    assert path.resolve().is_relative_to((ROOT/base).resolve())
                    assert path.stat().st_size == item[sizekey] and digest(path) == item[hashkey]
            inputs = read(base+"/INPUT_PINS.json")
            assert inputs["source_chunk_id"] == chunk and inputs["batch_id"] == batch
            assert inputs["scope_sha256"] == OLD_SCOPE_SHA and inputs["script_sha256"] == OLD_WRAPPER_SHA
            context = scope["chunk_contracts"][str(chunk)]
            assert inputs["source_manifest_sha256"] == context["source_manifest_sha256"]
            assert inputs["acquisition_summary_sha256"] == digest(ROOT/context["acquisition_summary_path"])
            assert len(inputs["compact_files_and_96_decoded_row_pins"]) == 6
            for scan in inputs["compact_files_and_96_decoded_row_pins"]:
                assert scan["shape"] == [16, 1, 1048576]
                assert scan["source_channel0"] == chunk*1048576
                assert [r["time_row"] for r in scan["decoded_rows"]] == list(range(16))
            tops, profiles = read(base+"/DRIFT_TOP20.json"), read(base+"/FIXED_TOP3_PROFILES.json")
            assert set(tops) == set(ONS) and all(len(tops[label]) == 20 for label in ONS)
            assert len(profiles) == 9
            expected_ids = {(label, rank) for label in ONS for rank in (1, 2, 3)}
            actual_ids = set()
            for record in profiles:
                selected = record["selected_track"]
                assert selected["source_chunk_id"] == chunk and selected["batch_id"] == batch
                label, rank = selected["originating_scan"], selected["display_rank"]
                actual_ids.add((label, rank))
                assert selected["track_id"] == f"{label}_gap_drift_rank_{rank:02d}"
                scan_profiles = record["scan_profiles"]
                assert [r["scan_id"] for r in scan_profiles] == list(SCANS)
                for scan in scan_profiles:
                    for key in ("all_16_center_minus_flank_rows", "all_16_raw_width_mean_power", "frozen_source_channel_centers"):
                        assert len(scan[key]) == 16
                patch = record["patch"]
                path = ROOT/base/patch["path"]
                assert path.resolve().is_relative_to((ROOT/base).resolve())
                assert path.stat().st_size == patch["bytes"] and digest(path) == patch["sha256"]
            assert actual_ids == expected_ids
            norm = read(base+"/NORMALIZATION.json")
            assert set(norm) == {"method", "row_power_medians", "source_channel0"}
            assert norm["source_channel0"] == chunk*1048576
            assert set(norm["row_power_medians"]) == set(SCANS)
            assert all(len(norm["row_power_medians"][label]) == 16 for label in SCANS)
            names = [base+"/"+name for name in ("INPUT_PINS.json", "DRIFT_CHECKPOINT.json", "DRIFT_TOP20.json", "FIXED_TOP3_PROFILES.json", "NORMALIZATION.json")]+[terminal_name]
            input_pins = [pin(name) for name in names]
            terminal_pin = {**pin(terminal_name), "kind": "failure" if failed else "execution"}
            jobs.append({"source_chunk_id": chunk, "batch_id": batch,
                "original_measurement_directory": base, "acceptance_directory": destination,
                "original_terminal_receipt": terminal_pin,
                "original_terminal_receipt_path": terminal_name,
                "original_terminal_receipt_sha256": terminal_pin["sha256"],
                "original_terminal_kind": terminal_pin["kind"],
                "original_numeric_job_status": expected_status,
                "original_resource_compliance": "FAIL_CPU_ONLY" if failed else "PASS",
                "original_resource_caps": {"CPU_cap_s": 1500, "wall_cap_s": 1800, "memory_cap_bytes": 4*1024**3},
                "original_measured_resource_use": usage,
                "expected_acceptance_status": "SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE" if failed else "SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE",
                "expected_QA_status": "PASS_COMPLETE_SAVED_OUTPUTS_WITH_ORIGINAL_CPU_CAP_EXCEEDED" if failed else "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS",
                "input_file_sha256": {p["path"]: p["sha256"] for p in input_pins},
                "input_file_bytes": {p["path"]: p["bytes"] for p in input_pins},
                "fixed_batch_q": qs, "expected_maps": 381, "expected_normalization_files": 381,
                "expected_top20_records": 60, "expected_profiles": 9, "expected_scan_profiles": 54,
                "expected_time_row_occurrences": 864, "expected_raw_patch_cell_occurrences": 111456})
            for path in sorted((ROOT/base).rglob("*")):
                if path.is_file():
                    files.append(pin(path.relative_to(ROOT).as_posix()))
    cpu_sum = sum(j["original_measured_resource_use"]["process_CPU_seconds_including_imports"] for j in jobs)
    assert abs(cpu_sum-6229.877042642) < 1e-9
    write_new(MANIFEST, {"schema": "IMMUTABLE_ORIGINAL_FOUR_JOB_OUTPUT_BYTES_V1", "files": files,
        "opaque_bytes_only": True, "NPZ_or_HDF5_arrays_opened": False, "original_files_written": False})
    result = {"status": "PASS_TERMINAL_METADATA_AND_OPAQUE_OUTPUT_BYTE_HASHES_ONLY",
        "scope_path": OLD_SCOPE, "scope_sha256": OLD_SCOPE_SHA, "wrapper_path": OLD_WRAPPER, "wrapper_sha256": OLD_WRAPPER_SHA,
        "job_contracts": jobs, "original_numeric_CPU_seconds_sum": cpu_sum,
        "original_resource_failure_count": 3, "original_COMPLETE_count": 1,
        "map_count": 1524, "normalization_file_count": 1524, "profile_count": 36,
        "scan_profile_count": 216, "time_row_occurrences": 3456, "raw_patch_cell_occurrences": 445824,
        "original_output_bytes_manifest": pin(MANIFEST),
        "control_flow": "run_search then fixed_profiles then all end-pin checks then measured cap gate at frozen wrapper line371; original COMPLETE gate/receipt not reached for three failures",
        "scientific_array_integrity_QA_passed_here": False, "science_values_inspected_here": False,
        "NPZ_or_HDF5_arrays_opened": False, "original_files_written": False,
        "saved_scoring_reexecuted": False, "profiles_remeasured": False,
        "new_telescope_HTTP_requests": 0, "new_telescope_BODY_bytes": 0,
        "preparer_script": pin(Path(__file__).relative_to(ROOT).as_posix()),
        "metadata_process_CPU_seconds": time.process_time()-began}
    write_new(META, result)
    print(json.dumps({"metadata_receipt": pin(META), "opaque_manifest": pin(MANIFEST), "CPU_s": result["metadata_process_CPU_seconds"], "original_numeric_CPU_sum_s": cpu_sum}))


def prospective_scope(code_pins_path):
    began = time.process_time()
    meta, old = read(META), read(OLD_SCOPE)
    assert meta["status"] == "PASS_TERMINAL_METADATA_AND_OPAQUE_OUTPUT_BYTE_HASHES_ONLY"
    codes = json.loads(Path(code_pins_path).read_text())
    required_codes = {RESULTS+"/review/qa_saved_after_resource_exception.py", TOOLS+"/summarize_verified_saved.py", TOOLS+"/plots_qualified_saved.py", TOOLS+"/package_verified_saved.py"}
    assert required_codes.issubset(codes)
    for name, sha in codes.items():
        assert digest(ROOT/name) == sha, name
    dependencies = {**old["pinned_dependency_files"], **codes, OLD_SCOPE: OLD_SCOPE_SHA,
        OLD_WRAPPER: OLD_WRAPPER_SHA, META: digest(ROOT/META), MANIFEST: digest(ROOT/MANIFEST),
        Path(__file__).relative_to(ROOT).as_posix(): digest(__file__)}
    recovery_scope_path = TOOLS+"/PATH_PREFLIGHT_RECOVERY_SCOPE.json"
    recovery = read(recovery_scope_path)
    dependencies[recovery_scope_path] = digest(ROOT/recovery_scope_path)
    for name in (RESULTS+"/PATH_PREFLIGHT_PRESERVATION_RECEIPT.json", RESULTS+"/review/PATH_PREFLIGHT_PEER_REVIEW.json"):
        dependencies[name] = digest(ROOT/name)
    for path in sorted((ROOT/RESULTS/"preflight_failures").rglob("*.json")):
        dependencies[path.relative_to(ROOT).as_posix()] = digest(path)
    for context in old["chunk_contracts"].values():
        for name in (context["acquisition_summary_path"], str(Path(context["compact_directory"])/"ACQUISITION_OUTPUT_QA_RECEIPT.json")):
            dependencies[name] = digest(ROOT/name)
    qa = RESULTS+"/review/qa_saved_after_resource_exception.py"
    result = {"schema": "SAVED_OUTPUT_VERIFICATION_AFTER_ORIGINAL_RESOURCE_CAP_FAILURE_V1",
        "status": "PROSPECTIVE_SAVED_OUTPUT_VERIFICATION_NO_NUMERIC_RETRY",
        "original_scope_sha256": OLD_SCOPE_SHA, "original_wrapper_sha256": OLD_WRAPPER_SHA,
        "original_scope_path": OLD_SCOPE, "original_wrapper_path": OLD_WRAPPER,
        "original_scientific_freeze_commit": "d1bfe755e205e99b3c93544f4af84cc8d4585938",
        "path_preflight_recovery_freeze_commit": "8f88b722c9508d4e209c3df540407029b80c3203",
        "original_output_bytes_manifest": meta["original_output_bytes_manifest"],
        "terminal_metadata_review": pin(META), "job_contracts": meta["job_contracts"],
        "qa_script_path": qa, "qa_script_sha256": codes[qa],
        "pinned_dependency_files": dependencies,
        "additional_stage_CPU_cap_s": 3000,
        "saved_QA_CPU_cap_s_per_job": 75, "saved_QA_wall_cap_s_per_job": 300, "saved_QA_memory_cap_bytes_per_job": 2*1024**3,
        "supplemental_source_audit_CPU_cap_s": 20,
        "original_numeric_CPU_seconds_sum": meta["original_numeric_CPU_seconds_sum"],
        "original_resource_failure_count": 3, "original_COMPLETE_count": 1,
        "per_job_CPU_failures_preserved": True, "original_global_stage_overrun_inferred": False,
        "root_fullpower_authorized_resource_overrun_acceptance": True,
        "original_terminal_files_and_statuses_unchanged": True,
        "new_detector_or_profile_passes": 0, "saved_scoring_reexecuted": False,
        "new_normalization_computed": False, "profiles_remeasured": False,
        "new_top20_or_top3_selection": False,
        "saved_rank_reconstruction_only_for_integrity_QA": True,
        "old_source_loader_called_for_scientific_remeasurement": False,
        "source_array_reads_only_in_separately_authorized_supplemental_raw_cell_audit": True,
        "new_telescope_HTTP_requests": 0, "new_telescope_BODY_bytes": 0,
        "new_source_channels_or_holdouts": 0, "protected_chunks_closed": [156, 159],
        "expected_maps": 1524, "expected_normalization_files": 1524, "expected_top20_records": 240,
        "expected_profiles": 36, "expected_scan_profiles": 216,
        "expected_time_row_occurrences": 3456, "expected_raw_patch_cell_occurrences": 445824,
        "carrier_origin_entries": 6242304, "evaluated_hypothesis_combinations": 9525755904,
        "code_invocations_per_original_job_including_preflight": 2,
        "actual_numeric_searches_per_original_job": 1, "additional_numeric_searches": 0,
        "additional_fixed_profile_projection_passes": 0,
        "independent_visits": 1, "unqualified_exploratory_only": True,
        "sky_pilot_qualification": False, "original_A_B_failures_unchanged": True,
        "ON_OFF_exchangeability_or_null_probability_assumed": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "whole_original_source_MD5_verified": False,
        "root_public_freeze_and_explicit_saved_value_GO_required_before_QA": True,
        "old_ALL_COMPLETE_helpers_unchanged": True,
        "acceptance_receipt_statuses": ["SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE", "SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE"],
        "semantics": "Saved-byte and saved-math verification admits retained output only; it does not reverse the three original1500CPU failures, create originalCOMPLETE receipts, or qualify a sky signal.",
        "resource_meter": "Original actual CPU is accounted separately; this3000CPU cap limits additional saved-output processing and does not retrospectively change original1500CPU caps.",
        "scope_generation_CPU_seconds": time.process_time()-began}
    path = TOOLS+"/SAVED_OUTPUT_ACCEPTANCE_SCOPE.json"
    write_new(path, result)
    print(json.dumps({"scope": pin(path), "scope_generation_CPU_s": result["scope_generation_CPU_seconds"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inventory", "scope"))
    parser.add_argument("--code-pins")
    args = parser.parse_args()
    if args.mode == "inventory":
        metadata_inventory()
    else:
        if not args.code_pins:
            parser.error("scope mode requires --code-pins with all final saved-only helper hashes")
        prospective_scope(args.code_pins)
