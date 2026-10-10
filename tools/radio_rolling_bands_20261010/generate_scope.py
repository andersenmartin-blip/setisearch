"""Build final scope from exact metadata contracts; never open scientific arrays.

The contract input is a two-key JSON map155/157. Each entry supplies only paths:
source_manifest_path, acquisition_script_path, acquisition_scope_path,
compact_directory, acquisition_summary_path. Their SHA pins are generated here.
Exact manifest/index acquisition files must exist before scope generation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "tools/radio_rolling_bands_20261010/native_search.py"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    started = time.process_time()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", required=True)
    parser.add_argument("--output", default=str(ROOT/"tools/radio_rolling_bands_20261010/scope.json"))
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("prospective_native_constants", ROOT/SCRIPT)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    compile((ROOT/SCRIPT).read_text(), SCRIPT, "exec")
    for name, expected in cfg.VERSIONS.items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("Package metadata differs: "+name)
    contracts_path = Path(args.contracts).resolve()
    if not contracts_path.is_relative_to(ROOT):
        raise ValueError("Metadata contracts must be inside this repository")
    input_contracts = json.loads(contracts_path.read_text())
    if set(input_contracts) != {"155", "157"}:
        raise ValueError("Both fresh source chunks must be described together")
    pinned = {name: digest(ROOT/name) for name in
              (cfg.HISTORICAL_SOURCE_PATH, cfg.FRESH_PATH, cfg.DETECTOR_PATH, cfg.GAP_PATH, cfg.ACTIVATION_PATH)}
    known = {cfg.HISTORICAL_SOURCE_PATH: cfg.HISTORICAL_SOURCE_SHA, cfg.FRESH_PATH: cfg.FRESH_SHA,
             cfg.DETECTOR_PATH: cfg.DETECTOR_SHA, cfg.GAP_PATH: cfg.GAP_SHA, cfg.ACTIVATION_PATH: cfg.ACTIVATION_SHA}
    if pinned != known:
        raise ValueError("Original code/source/activation identities differ")
    pinned[contracts_path.relative_to(ROOT).as_posix()] = digest(contracts_path)
    contracts = {}
    previous = json.loads((ROOT/cfg.HISTORICAL_SOURCE_PATH).read_text())
    for chunk in cfg.CHUNKS:
        values = dict(input_contracts[str(chunk)])
        expected_fields = {"source_manifest_path", "acquisition_script_path", "acquisition_scope_path",
                           "compact_directory", "acquisition_summary_path"}
        if set(values) != expected_fields:
            raise ValueError("Metadata contract has unexpected or missing fields")
        source0 = chunk*cfg.COUNT
        for key, name in tuple(values.items()):
            path = Path(name)
            if (path.is_absolute() or ".." in path.parts or not (ROOT/path).resolve().is_relative_to(ROOT)):
                raise ValueError("Require root-relative confined input paths")
            if key.endswith("_path") and key != "acquisition_summary_path":
                sha = digest(ROOT/name)
                values[key.replace("_path", "_sha256")] = sha
                pinned[name] = sha
        source = json.loads((ROOT/values["source_manifest_path"]).read_text())
        acquisition_scope = json.loads((ROOT/values["acquisition_scope_path"]).read_text())
        if (acquisition_scope["native_chunk_index"] != chunk
                or acquisition_scope["source_manifest"] != values["source_manifest_path"]
                or acquisition_scope["output_directory"] != values["compact_directory"]):
            raise ValueError("Acquisition scope source/chunk/directory binding differs")
        for name, expected in acquisition_scope["pinned_files"].items():
            if digest(ROOT/name) != expected or (name in pinned and pinned[name] != expected):
                raise ValueError("Pinned acquisition reader or source dependency differs")
            pinned[name] = expected
        if (source["physical_channel_interval_half_open"] != [source0, source0+cfg.COUNT]
                or source["native_chunk_index"] != chunk or source["new_band_values_opened"] is not False
                or source["protected_prior_native_chunk_values_opened"] is not False
                or [s["label"] for s in source["sources"]] != list(cfg.SCANS)):
            raise ValueError("Source metadata does not describe the fixed native chunk")
        for item, old in zip(source["sources"], previous["sources"]):
            if any(item[k] != old[k] for k in ("label", "role", "url", "etag", "source_file_bytes", "current_header")):
                raise ValueError("New frequency chunks must preserve historical source/header identity")
            rows = item["chunks"]
            if (len(rows) != 16 or [r["time_row"] for r in rows] != list(range(16))
                    or any(r["chunk_origin"] != [i, 0, source0] or r["decoded_size"] != cfg.COUNT*4
                           or r["filter_mask"] != 0 or r["stored_size"] <= 0
                           for i, r in enumerate(rows))):
                raise ValueError("Need96 exact metadata-supported payload ranges per source chunk")
        values["source_channel_interval_half_open"] = [source0, source0+cfg.COUNT]
        values["exact96_source_chunk_range_descriptors"] = {s["label"]: s["chunks"] for s in source["sources"]}
        contracts[str(chunk)] = values
    activation = json.loads((ROOT/cfg.ACTIVATION_PATH).read_text())
    selection = activation["immutable_metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":"))+"\n").encode()
    if hashlib.sha256(canonical).hexdigest() != cfg.SELECTION_SHA:
        raise ValueError("Immutable four-batch metadata selection changed")
    scope = {
        "schema": "SETI_TWO_NEW_NATIVE_CHUNKS_FOUR_FIXED_127_CORE_BATCHES_V1",
        "script_sha256": digest(ROOT/SCRIPT), "scope_generator_sha256": digest(__file__),
        "scope_prepared_before_any_new155157_source_values": True,
        "source_chunk_ids": list(cfg.CHUNKS), "source_chunk_channel_count": cfg.COUNT,
        "metadata_selection_canonical_SHA256": cfg.SELECTION_SHA, "immutable_metadata_selection": selection,
        "rows_per_scan": 16, "scan_order": list(cfg.SCANS), "origin_scan_order": list(cfg.ONS),
        "fch1_hz": cfg.FCH1, "df_hz": cfg.DF, "tsamp_s": cfg.TSAMP,
        "safe_q_interval_inclusive": [1, 254], "batch_q": [list(qs) for qs in cfg.BATCH_Q],
        "batch_core_count": 127, "core_channel_count": cfg.CORE_COUNT,
        "crop_halo_channels": cfg.CROP_HALO, "expected_scan_tiles_per_batch": 381,
        "carriers_per_ON_per_batch": 520192, "safe_carriers_per_ON_per_chunk_if_both_complete": 1040384,
        "safe_native_chunk_fraction_if_both_complete": 0.9921875,
        "expected_total_scan_tiles_if_all_four_complete": 1524,
        "expected_total_ON_carrier_origin_entries_if_all_four_complete": 6242304,
        "expected_total_hypothesis_entries_if_all_four_complete": 9525755904,
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": list(cfg.WIDTHS), "valid_hypotheses_per_carrier": 1526,
        "rank_count_per_ON_per_batch": cfg.TOP, "display_suppression_channels": 3,
        "fixed_profile_ranks_per_ON_per_batch": 3, "expected_profile_count_per_batch": 9,
        "expected_total_profiles_if_all_four_complete": 36,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
        "profile_identity_fields": ["source_chunk_id", "batch_id", "track_id"],
        "CPU_cap_s_per_batch": cfg.CPU_CAP, "wall_cap_s_per_batch": cfg.WALL_CAP,
        "memory_cap_bytes_per_batch": cfg.MEMORY_CAP,
        "stage_CPU_planning_allocation_s": 9200, "stage_numeric_reserved_CPU_s": 8000,
        "stage_prep_QA_package_CPU_s": {"preparation": 400, "QA": 400, "packaging_publication": 400},
        "analysis_attempts_per_chunk_batch": 1, "numeric_retry_authorized": False,
        "old_holdouts_reopened": False, "original_A_B_failures_unchanged": True,
        "protected_old_native_chunks_not_read": [156, 159],
        "OFF_veto": False, "unqualified_exploratory_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "runtime_package_versions": cfg.VERSIONS, "pinned_dependency_files": pinned,
        "pinned_dependency_file_bytes": {p: (ROOT/p).stat().st_size for p in pinned},
        "chunk_contracts": contracts,
        "new_telescope_HTTP_requests_during_analysis": 0, "new_telescope_BODY_bytes_during_analysis": 0,
        "acquisition_requires_separate_prospective_public_freeze": True,
        "future_receipt_pin_binding": "Source manifest and acquisition code/scope SHAs fixed before values; completed receipt SHA and all6 compact/96 decoded-row pins preserved per job in INPUT_PINS.json",
        "output_directories": [f"results/radio_rolling_bands_20261010/chunk{c}/batch_{b:02d}/measurement"
                               for c in cfg.CHUNKS for b in (1, 2)],
        "ranking": "Each batch and ON separately: lexsort(-robust_score, absolute channel), greedy separation >3; no global reranking",
        "detector": "Exactly pinned detector.search_scan and Config(widths=(1,3));763 numpy.linspace drift points; original source-frame np.rint, strict > winning-width/drift tie updates",
        "normalization": "Detector core normalization unchanged; six full-chunk row medians computed as original np.median(float32,axis=1).astype(float64), saved before profiles",
        "profile_function": "Call exactly pinned gap_search.fixed_profiles; only native C0 and new saved NORMALIZATION path globals bound to selected chunk/job; no body edits",
        "compact_loader": "Call exactly pinned fresh_search.load_power; only native C0 global bound to selected chunk; all6 compact SHA and96 decoded-row SHA verified",
        "checkpoint_layout": "Persist each complete carrier map and full original normalization once per scan/core, then atomically update checkpoint with path/hash/bytes",
        "partial_failure": "Keep all completed tiles and fixed profiles; failure receipt with exact counts; no retry, alternate directory or cap widening",
        "limitations": [
            "All six scans are one2016-03-17 historical visit, not independent visits",
            "All four carrier lists and algorithms fixed before any new155/157 values, but no independent validation claim",
            "Reference-carrier coverage only for763 linear drifts and widths1/3; q0/q255 edges remain unsearched; crop/track halos overlap",
            "Four batch-local rankings are separate; selected profiles and correlated hypotheses are selection conditional",
            "Robust scores are not calibrated SNR, FAP, flux, EIRP or sensitivity",
            "Exact unchanged OFF predictions are descriptive; small predicted OFF residual does not prove absence of nearby OFF structure",
            "No qualified OFF veto, sky/origin classification, old holdout access, barycentric correction, other widths or nonlinear tracks; protected native chunks156/159 remain closed",
            "Whole original source-file MD5 remains unverified despite exact compact and decoded-row verification"]}
    output = Path(args.output)
    output.write_text(json.dumps(scope, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"script_sha256": scope["script_sha256"], "scope_sha256": digest(output),
                      "generator_sha256": scope["scope_generator_sha256"],
                      "metadata_generation_CPU_s": time.process_time()-started}))


if __name__ == "__main__":
    main()
