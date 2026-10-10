"""Metadata-only scope generation; never import NumPy or open observation arrays."""
import hashlib
import importlib.util
import json
from pathlib import Path
import py_compile
import time

START = time.process_time()
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    script = HERE/"full_safe_search.py"
    spec = importlib.util.spec_from_file_location("full_safe_metadata_constants_only", script)
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    dependencies = (wrapper.SOURCE_PATH, wrapper.NORMALIZATION_PATH, wrapper.FRESH_PATH,
                    wrapper.FRESH_SCOPE_PATH, wrapper.DETECTOR_PATH, wrapper.GAP_PATH,
                    wrapper.GAP_SCOPE_PATH, wrapper.PROPOSAL_PATH, wrapper.ACTIVATION_PATH,
                    wrapper.ACQUISITION_PATH)
    pins = {path: digest(ROOT/path) for path in dependencies}
    for path, sha in ((wrapper.SOURCE_PATH, wrapper.SOURCE_SHA), (wrapper.FRESH_PATH, wrapper.FRESH_SHA),
                      (wrapper.DETECTOR_PATH, wrapper.DETECTOR_SHA), (wrapper.GAP_PATH, wrapper.GAP_SHA),
                      (wrapper.PROPOSAL_PATH, wrapper.PROPOSAL_SHA), (wrapper.ACQUISITION_PATH, wrapper.ACQUISITION_SHA)):
        if pins[path] != sha:
            raise ValueError("Restored metadata/code pin differs: " + path)
    proposal = json.loads((ROOT/wrapper.PROPOSAL_PATH).read_text())
    activation = json.loads((ROOT/wrapper.ACTIVATION_PATH).read_text())
    acquisition = json.loads((ROOT/wrapper.ACQUISITION_PATH).read_text())
    selection = proposal["metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (hashlib.sha256(canonical).hexdigest() != wrapper.SELECTION_SHA
            or selection != activation["immutable_metadata_selection"]
            or selection["prior_q"] != list(wrapper.PRIOR_Q)
            or selection["previous_gap_q"] != list(wrapper.OLD_GAP_Q)
            or selection["remaining_q_ascending"] != list(wrapper.NEW_Q)
            or selection["batch_q"] != [list(qs) for qs in wrapper.BATCH_Q]):
        raise ValueError("Prospective 107+107 selection differs")
    scope = {
        "schema": "SETI_TWO_FIXED_107_SAFE_CORE_BATCHES_V1",
        "status": "AUTHORIZED_COMMON_TWO_BATCH_SCOPE_PUBLIC_FREEZE_PENDING_NOT_RUN",
        "script_path": str(script.relative_to(ROOT)), "script_sha256": digest(script),
        "scope_generator_path": str(Path(__file__).relative_to(ROOT)), "scope_generator_sha256": digest(Path(__file__)),
        "source_manifest_sha256": wrapper.SOURCE_SHA,
        "acquisition_summary_sha256": wrapper.ACQUISITION_SHA,
        "proposal_sha256": wrapper.PROPOSAL_SHA,
        "activation_scope_sha256": pins[wrapper.ACTIVATION_PATH],
        "metadata_selection_canonical_SHA256": wrapper.SELECTION_SHA,
        "canonical_selection_serialization": "UTF-8 json.dumps(selection, sort_keys=True, separators=(comma,colon)) plus newline",
        "immutable_metadata_selection": selection,
        "pinned_dependency_files": pins,
        "pinned_dependency_bytes": {path: (ROOT/path).stat().st_size for path in dependencies},
        "compact_files_and_96_decoded_row_pins": acquisition["decoded_files"],
        "scope_generation_reads_compact_HDF5_or_profile_NPZ": False,
        "runtime_compact_and_row_verification": "Unchanged fresh.load_power: six compact SHA256 checks, exact attrs/C0/shape/type and all96 decoded-row SHA256 checks once per job.",
        "whole_original_telescope_file_MD5_verified": False,
        "source_channel_interval_half_open": [wrapper.C0, wrapper.C0+wrapper.COUNT],
        "count": wrapper.COUNT, "rows_per_scan": 16,
        "scan_order": list(wrapper.SCANS), "origin_scan_order": list(wrapper.ONS),
        "fch1_hz": wrapper.FCH1, "df_hz": wrapper.DF, "tsamp_s": wrapper.TSAMP,
        "safe_q_interval_inclusive": [1, 254], "prior_q": list(wrapper.PRIOR_Q),
        "previous_gap_q": list(wrapper.OLD_GAP_Q), "remaining_q_ascending": list(wrapper.NEW_Q),
        "batch_q": [list(qs) for qs in wrapper.BATCH_Q],
        "both_batch_lists_frozen_before_either_outcome": True,
        "batch_core_count": 107, "core_channel_count": wrapper.CORE_COUNT,
        "crop_halo_channels": wrapper.CROP_HALO,
        "output_directories": [f"results/radio_full_safe_20261010/batch_{i:02d}/measurement" for i in (1, 2)],
        "expected_scan_tiles_per_batch": 321, "carriers_per_ON_per_batch": 438272,
        "expected_new_core_count_both_batches": 214,
        "expected_new_reference_carriers_per_ON_both_batches": 876544,
        "expected_safe_reference_carriers_per_ON_including_prior40_if_both_complete": 1040384,
        "conditional_safe_reference_fraction": 0.9921875,
        "edge_q_remaining_unsearched": [0, 255],
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": list(wrapper.WIDTHS), "valid_hypotheses_per_carrier": 1526,
        "rank_count_per_ON_per_batch": 20, "display_suppression_channels": 3,
        "fixed_profile_ranks_per_ON_per_batch": 3, "expected_profile_count_per_batch": 9,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
        "all_profile_scans_and_rows": [6, 16],
        "geometry_metadata_only": proposal["geometry"],
        "search_algorithm": {
            "detector": "Unchanged pinned pilot_engine_20261008.detector.search_scan and Config(widths=(1,3)).",
            "source_frame": "frequencies=FCH1+DF*np.arange(first,stop); original detector computes base=(frequencies−FCH1)/DF and rint in absolute source frame before crop-origin subtraction.",
            "origin_time": "dt=np.arange(16)*TSAMP; each ON first midpoint reference remains (tstart−anchor)*86400+0.5*TSAMP.",
            "preprocessing": "Same4096native core row normalization,501channel median filter,empirical MAD scale,winsorized location and original masking.",
            "detector_ties": "Original strict improvement value>best; width1 precedes3, drift grid ascending and original tiled argmax tie behavior retained.",
            "rank_ties": "np.lexsort((absolute_source_channels,−scores)); descending score then ascending absolute channel; accept separation>3; fixed20 perON perbatch.",
            "profile_math": "Direct call to unchanged pinned old gap.fixed_profiles, injected np without invoking old module main; scalar frequency from unchanged fresh.frequency(int(channel)).",
            "profile_selection": "All3 ON origins, ranks1–3 from each new batch top20; frequencies/rates/widths are data-selected, selection rule fixed before these outcomes.",
            "cross_batch_ranking": False,
        },
        "retention": {
            "every_tile": "All4096 score maxima,winning drifts,widths,actual valid counts,source channels,reference frequencies and763drift grid in original NPZ layout.",
            "normalization": "Full unchanged normalization JSON per scan tile, including all4096source channels; checkpoint preserves file/hash/size references.",
            "checkpoint": "Atomic JSON after each completed scan tile; actual completed q perON and all receipts; no resume/retry.",
            "profiles": "Original raw float32,normalized float64,rowmedians,absolute frozen centers,all16 residuals and129meanprofile arrays for all6scans,unchanged old NPZ schema.",
            "track_identity": "Preserve old gap trackID/family strings; use(batch_id,track_id) and batch_01/02 paths to identify distinct ranked families.",
            "partial_failure": "Keep all outputs/checkpoints; FAILURE_RECEIPT includes completed tile/profile counts; incomplete files are never claimed as committed tiles.",
        },
        "runtime_package_versions": wrapper.VERSIONS,
        "CPU_cap_s_per_batch": 1200, "wall_cap_s_per_batch": 1800,
        "memory_cap_bytes_per_batch": 4294967296,
        "stage_CPU_planning_allocation_s": activation["stage_CPU_planning_allocation_s"],
        "new_telescope_HTTP_request_cap": 0, "new_telescope_BODY_byte_cap": 0,
        "analysis_attempts_per_batch": 1, "numeric_retry_authorized": False,
        "old_holdouts_reopened": False, "original_A_B_failures_unchanged": True,
        "OFF_veto": False, "unqualified_exploratory_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "source_values_previously_exposed": True, "blind_or_independent_validation": False,
        "new_numeric_runs_during_scope_generation": 0,
        "limitations": [
            "One historical 2016-03-17 visit; scan epoch labels do not identify independent visits.",
            "Source values were previously opened; prospective only for these new drift hypotheses.",
            "Batch-dependent selected maxima and overlapping hypotheses/profiles are correlated; no independent-trial or calibrated probability claim.",
            "Carrier cores are disjoint from prior32/gap8 and each other; crop and projected-track halos may overlap.",
            "99.21875percent coverage is conditional on both jobs completing plus prior40,for reference carriers of one native chunk and exactly this grid/width family,not survey or sensitivity completeness.",
            "Two edge cores remain unsearched; no new observations or source-frequency chunk acquired.",
            "A small OFF value at a frozen predicted channel does not establish absence of nearby OFF structure; no optimized shift or veto.",
            "All original A/B failure statuses remain FAIL_CLOSED,qualified sky pilot blocked,old holdouts closed.",
            "No SNR/FAP,flux/EIRP/sensitivity,origin classification,general null claim,barycentric correction,nonlinear track or injection-recovery certification.",
            "Exact compact and96row pins validate retained source parts;whole original telescope-file MD5 remains unverified.",
            "Measured CPU/wall/RSS caps must pass as well as321valid completed scan tiles and9profiles; preserve partial results without retries.",
        ],
    }
    py_compile.compile(str(script), doraise=True)
    target = HERE/"scope.json"
    target.write_text(json.dumps(scope, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"script_sha256": digest(script), "scope_sha256": digest(target),
        "scope_generator_sha256": digest(Path(__file__)), "syntax": "PASS",
        "metadata_only_scope_CPU_s": time.process_time()-START,
        "scientific_array_reads": 0, "numerical_jobs_invoked": 0}, indent=2))


if __name__ == "__main__":
    main()
