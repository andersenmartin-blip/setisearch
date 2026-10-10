"""Freeze only a saved-output verification contract; no science arrays opened.

The executed metadata producer remains byte unchanged for provenance. This
separate generator checks that producer, its original pins and its manifest
binding before emitting one new prospective scope with five saved-only helpers.
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
ACCEPT = RESULTS+"/acceptance"
OLD_SCOPE = TOOLS+"/scope.json"
OLD_WRAPPER = TOOLS+"/native_search.py"
OLD_SCOPE_SHA = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
OLD_WRAPPER_SHA = "f189abc0a27503cbf2a35b1c63626ef2d3847728894a0a4fcfce9b16da36800b"
PRODUCER = TOOLS+"/prepare_saved_output_acceptance.py"
PRODUCER_SHA = "c40ca385277cae3e0e02c0dc28f9176463ab7e0507ee90ce2e94fa4164f98c0e"
META = ACCEPT+"/TERMINAL_METADATA_REVIEW.json"
META_SHA = "32cfc34d4a642bde320d06c7e203fc3bcfae8a60e0a193bf6fe2bb16da2a7ece"
MANIFEST = ACCEPT+"/ORIGINAL_OUTPUT_BYTES_MANIFEST.json"
MANIFEST_SHA = "bf5ec0d4768d4ea1b3de9e84d2a2bf151dca7872d15add0b8d32290d4d709546"
QA = RESULTS+"/review/qa_saved_after_resource_exception.py"
AUDIT = RESULTS+"/review/source_cell_audit_saved_acceptance.py"
REQUIRED_CODES = {QA, AUDIT, TOOLS+"/summarize_verified_saved.py",
                  TOOLS+"/plots_qualified_saved.py", TOOLS+"/package_verified_saved.py"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((ROOT/name).read_text())


def pin(name):
    return {"path": name, "sha256": digest(ROOT/name), "bytes": (ROOT/name).stat().st_size}


def generate(code_pins_path):
    original = {OLD_SCOPE: OLD_SCOPE_SHA, OLD_WRAPPER: OLD_WRAPPER_SHA,
                PRODUCER: PRODUCER_SHA, META: META_SHA, MANIFEST: MANIFEST_SHA}
    for name, sha in original.items():
        assert digest(ROOT/name) == sha, name
    old, meta = read(OLD_SCOPE), read(META)
    assert meta["scope_sha256"] == OLD_SCOPE_SHA and meta["wrapper_sha256"] == OLD_WRAPPER_SHA
    assert meta["preparer_script"] == pin(PRODUCER)
    assert meta["original_output_bytes_manifest"] == pin(MANIFEST)
    assert meta["status"] == "PASS_TERMINAL_METADATA_AND_OPAQUE_OUTPUT_BYTE_HASHES_ONLY"
    manifest = read(MANIFEST)
    assert manifest["schema"] == "IMMUTABLE_ORIGINAL_FOUR_JOB_OUTPUT_BYTES_V1"
    assert len(manifest["files"]) == 3108 and len({p["path"] for p in manifest["files"]}) == 3108
    for job in meta["job_contracts"]:
        assert sum(p["path"].startswith(job["original_measurement_directory"]+"/") for p in manifest["files"]) == 777
        assert job["original_terminal_receipt"]["sha256"] == job["original_terminal_receipt_sha256"]
        assert job["original_terminal_receipt"]["path"] == job["original_terminal_receipt_path"]
        for name, sha in job["input_file_sha256"].items():
            assert digest(ROOT/name) == sha and (ROOT/name).stat().st_size == job["input_file_bytes"][name], name
        inputs = read(job["original_measurement_directory"]+"/INPUT_PINS.json")
        context = old["chunk_contracts"][str(job["source_chunk_id"])]
        assert digest(ROOT/context["acquisition_summary_path"]) == inputs["acquisition_summary_sha256"]
    codes = json.loads(Path(code_pins_path).read_text())
    assert set(codes) == REQUIRED_CODES, "Exactly all five final saved-only helpers must be pinned"
    for name, sha in codes.items():
        assert digest(ROOT/name) == sha, name
    dependencies = {**old["pinned_dependency_files"], **original, **codes,
        Path(__file__).relative_to(ROOT).as_posix(): digest(__file__),
        TOOLS+"/SAVED_OUTPUT_ACCEPTANCE_PLAN.md": digest(ROOT/TOOLS/"SAVED_OUTPUT_ACCEPTANCE_PLAN.md"),
        TOOLS+"/SAVED_OUTPUT_ACCEPTANCE_REPRODUCTION.md": "b77b4c1f261c5f220c52a6bc89dd167c55b502a81f1353f7b8a7f4c178dc36e7"}
    for job in meta["job_contracts"]:
        for name, sha in job["input_file_sha256"].items():
            assert name not in dependencies or dependencies[name] == sha, name
            dependencies[name] = sha
    math_review = ACCEPT+"/QA_SCIENTIFIC_MATH_STATIC_IDENTITY.json"
    dependencies[math_review] = digest(ROOT/math_review)
    for name, sha in old["pinned_dependency_files"].items():
        assert digest(ROOT/name) == sha, name
    recovery_scope_path = TOOLS+"/PATH_PREFLIGHT_RECOVERY_SCOPE.json"
    dependencies[recovery_scope_path] = digest(ROOT/recovery_scope_path)
    assert dependencies[recovery_scope_path] == "a1a6856f6a27e6f20deaaa894de88a3138e25460686c78cdda949b3e566ee268"
    recovery = read(recovery_scope_path)
    for name in (RESULTS+"/PATH_PREFLIGHT_PRESERVATION_RECEIPT.json", RESULTS+"/review/PATH_PREFLIGHT_PEER_REVIEW.json"):
        dependencies[name] = digest(ROOT/name)
    preserved = sorted((ROOT/RESULTS/"preflight_failures").rglob("*.json"))
    assert len(preserved) == 8
    expected_preserved = {item["preserved_directory"]+"/"+name: sha
        for item in recovery["failures"] for name, sha in item["preserved_file_sha256"].items()}
    assert {path.relative_to(ROOT).as_posix() for path in preserved} == set(expected_preserved)
    for path in preserved:
        name = path.relative_to(ROOT).as_posix()
        assert digest(path) == expected_preserved[name], name
        dependencies[name] = expected_preserved[name]
    for context in old["chunk_contracts"].values():
        for name in (context["acquisition_summary_path"], str(Path(context["compact_directory"])/"ACQUISITION_OUTPUT_QA_RECEIPT.json")):
            dependencies[name] = digest(ROOT/name)
    result = {"schema": "SAVED_OUTPUT_VERIFICATION_AFTER_ORIGINAL_RESOURCE_CAP_FAILURE_V1",
        "status": "PROSPECTIVE_SAVED_OUTPUT_VERIFICATION_NO_NUMERIC_RETRY",
        "original_scope_sha256": OLD_SCOPE_SHA, "original_wrapper_sha256": OLD_WRAPPER_SHA,
        "original_scope_path": OLD_SCOPE, "original_wrapper_path": OLD_WRAPPER,
        "original_scientific_freeze_commit": "d1bfe755e205e99b3c93544f4af84cc8d4585938",
        "path_preflight_recovery_freeze_commit": "8f88b722c9508d4e209c3df540407029b80c3203",
        "original_output_bytes_manifest": meta["original_output_bytes_manifest"],
        "terminal_metadata_review": pin(META), "job_contracts": meta["job_contracts"],
        "qa_script_path": QA, "qa_script_sha256": codes[QA],
        "source_audit_script_path": AUDIT, "source_audit_script_sha256": codes[AUDIT],
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
        "semantics": "Saved-byte and saved-math verification admits retained output only; it does not reverse the three original 1500 CPU failures, create original COMPLETE receipts, or qualify a sky signal.",
        "resource_meter": "Original actual CPU is accounted separately; this 3000 CPU cap limits additional saved-output processing and does not retrospectively change original 1500 CPU caps.",
        "scope_generation_process_CPU_seconds_including_stdlib_imports": time.process_time()}
    # Admission pins are checked again immediately before emitting the contract.
    for name, sha in dependencies.items():
        assert digest(ROOT/name) == sha, name
    for job in meta["job_contracts"]:
        for name, size in job["input_file_bytes"].items():
            assert (ROOT/name).stat().st_size == size, name
    path = ROOT/TOOLS/"SAVED_OUTPUT_ACCEPTANCE_SCOPE.json"
    with path.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"scope": pin(path.relative_to(ROOT).as_posix()),
                      "process_CPU_s": time.process_time(), "numeric_arrays_opened": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-pins", required=True)
    args = parser.parse_args()
    generate(args.code_pins)
