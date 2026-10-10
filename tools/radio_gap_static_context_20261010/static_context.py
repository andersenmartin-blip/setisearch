"""Fixed physical-channel context for nine previously selected moving tracks.

This is one bounded descriptive pass. No detection, peak search, reranking,
refitting, veto, or qualification occurs. Importing opens no observation values.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
C0, COUNT = 158334976, 1048576
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
REFS = (158358343, 158355634, 158879966, 159145548, 159144660,
        159014473, 158489515, 158490607, 159145372)
WIDTHS = (3, 3, 3, 1, 1, 1, 1, 1, 1)
TRACK_IDS = tuple(s+"_gap_drift_rank_%02d" % r for s in ONS for r in (1, 2, 3))
CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 1800, 4*1024**3
SOURCE_PATH = "tools/radio_fresh_band_20261009/source_manifest.json"
FRESH_PATH = "tools/radio_fresh_band_20261009/fresh_search.py"
DETECTOR_PATH = "pilot_engine_20261008/detector.py"
NORMALIZATION_PATH = "results/radio_fresh_band_20261009/stationary/NORMALIZATION.json"
OLD_PROFILE_JSON_PATH = "results/radio_gap_drift_20261010/measurement/FIXED_TOP3_PROFILES.json"
OLD_PATCH_DIR = "results/radio_gap_drift_20261010/measurement/profiles"
ACQUISITION_PATH = "results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json"
SOURCE_SHA = "d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c"
ACQUISITION_SHA = "da165fe31ac4a70167b06f83b8f667fbb8604b595c642d3610fec68788bebf37"
OLD_KEYS = {"raw_power", "row_normalized_power", "saved_full_chunk_row_medians",
    "frozen_source_channel_centers", "source_channel_offsets", "times_seconds_from_reference",
    "center_row_normalized_power", "fixed_flank_median_row_normalized_power",
    "center_minus_flank_each_row", "mean_fixed_track_frequency_profile", "scans",
    "df_hz", "source_channel0", "reference_frequency_hz", "drift_hz_s",
    "width_channels", "fixed_source_channel_shift"}


class ResourceLimitExceeded(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024**2), b""):
            h.update(b)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix+".tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    temporary.replace(target)


def contract(args):
    if digest(args.scope) != args.expected_scope_sha256:
        raise ValueError("Scope differs from publicly frozen execution SHA")
    scope = json.loads(Path(args.scope).read_text())
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Static context code differs from freeze")
    expected = {"schema": "SETI_NINE_GAP_TRACKS_FIXED_PHYSICAL_CONTEXT_V1",
        "source_manifest_sha256": SOURCE_SHA, "acquisition_summary_sha256": ACQUISITION_SHA,
        "source_channel_interval_half_open": [C0, C0+COUNT], "count": COUNT,
        "rows_per_scan": 16, "scan_order": list(SCANS), "track_ids": list(TRACK_IDS),
        "fixed_reference_channels": list(REFS), "original_widths_channels": list(WIDTHS),
        "fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP,
        "case_count": 9, "case_scan_count": 54, "profile_halfwidth_channels": 64,
        "static_flank_channel_count": 122, "fixed_frequency_shift_channels": 0,
        "old_moving_raw_cell_count_checked": 111456,
        "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
        "runtime_package_versions": {"numpy": "2.3.5", "h5py": "3.15.1", "hdf5plugin": "7.1.0"},
        "numeric_retry_authorized": False, "plots_inside_job": 0,
        "reranking_refitting_new_drift_search": False,
        "new_telescope_HTTP_request_cap": 0, "new_telescope_BODY_byte_cap": 0,
        "old_holdouts_reopened": False, "original_A_B_failures_unchanged": True,
        "qualified_sky_pilot": False, "OFF_veto": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False}
    if any(scope.get(k) != v for k, v in expected.items()):
        raise ValueError("Declared context family differs from implementation")
    pins = scope["pinned_dependency_files"]
    expected_paths = {SOURCE_PATH, FRESH_PATH, DETECTOR_PATH, NORMALIZATION_PATH,
                      OLD_PROFILE_JSON_PATH, ACQUISITION_PATH}
    expected_paths.update(OLD_PATCH_DIR+"/"+t+".npz" for t in TRACK_IDS)
    if set(pins) != expected_paths:
        raise ValueError("All and only fifteen input/code dependency files must be pinned")
    for name, sha in pins.items():
        if digest(ROOT/name) != sha:
            raise ValueError("Pinned input or code differs: "+name)
    if pins[SOURCE_PATH] != SOURCE_SHA or pins[ACQUISITION_PATH] != ACQUISITION_SHA:
        raise ValueError("Original source metadata/acquisition identity lost")
    if Path(args.acquisition_summary).resolve() != (ROOT/ACQUISITION_PATH).resolve():
        raise ValueError("Acquisition argument must select pinned original receipt")
    if Path(args.compact_dir).resolve() != (ROOT/ACQUISITION_PATH).parent.resolve():
        raise ValueError("Compact directory must select pinned original inputs")
    for name, version in expected["runtime_package_versions"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Runtime package differs: "+name)
    source = json.loads((ROOT/SOURCE_PATH).read_text())
    if [s["label"] for s in source["sources"]] != list(SCANS):
        raise ValueError("Original chronological six-scan sequence required")
    if [s["role"].upper() for s in source["sources"]] != ["ON", "OFF"]*3:
        raise ValueError("Original alternating scan roles required")
    anchor = min(s["current_header"]["data_attributes"]["tstart"] for s in source["sources"])
    previous_end = -math.inf
    for s in source["sources"]:
        h = s["current_header"]["data_attributes"]
        for observed, target, tolerance in ((h["fch1"]*1e6, FCH1, 1e-6),
                (h["foff"]*1e6, DF, 1e-12), (h["tsamp"], TSAMP, 1e-12)):
            if not math.isclose(observed, target, rel_tol=0, abs_tol=tolerance):
                raise ValueError("Original source grid differs")
        start = (h["tstart"]-anchor)*86400
        if start < previous_end:
            raise ValueError("Scans overlap or chronology differs")
        previous_end = start+16*TSAMP
    acquisition = json.loads((ROOT/ACQUISITION_PATH).read_text())
    if acquisition.get("status") != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY":
        raise ValueError("Complete original acquisition required")
    if (acquisition.get("source_manifest_sha256") != SOURCE_SHA or
            acquisition.get("physical_channel_interval_half_open") != [C0, C0+COUNT]):
        raise ValueError("Wrong acquired source chunk")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or {r["scan_id"] for r in decoded} != set(SCANS):
        raise ValueError("Exactly six unique source compact files required")
    normalization = json.loads((ROOT/NORMALIZATION_PATH).read_text())
    if normalization["source_channel0"] != C0:
        raise ValueError("Wrong retained full-chunk normalization")
    old_profiles = json.loads((ROOT/OLD_PROFILE_JSON_PATH).read_text())
    if len(old_profiles) != 9 or [r["selected_track"]["track_id"] for r in old_profiles] != list(TRACK_IDS):
        raise ValueError("Exactly original nine top-three selected tracks required")
    for i, p in enumerate(old_profiles):
        t = p["selected_track"]
        if t["source_reference_channel"] != REFS[i] or t["width_channels"] != WIDTHS[i]:
            raise ValueError("Original selected physical channel or width differs")
        if p["fixed_frequency_shift_channels"] != 0:
            raise ValueError("Original moving profile frequency was shifted")
        old_path = OLD_PATCH_DIR+"/"+TRACK_IDS[i]+".npz"
        if p["patch"]["sha256"] != pins[old_path]:
            raise ValueError("Original selected profile receipt differs")
        if [r["scan_id"] for r in p["scan_profiles"]] != list(SCANS):
            raise ValueError("Original profile scan order differs")
    return scope, source, acquisition, normalization, old_profiles, float(anchor)


def row_metrics(values):
    return {"mean": float(values.mean()), "median": float(np.median(values)),
        "positive_rows": int(np.count_nonzero(values > 0)),
        "first_eight_mean": float(values[:8].mean()), "last_eight_mean": float(values[8:].mean()),
        "minimum_half_mean": float(min(values[:8].mean(), values[8:].mean())),
        "all_16_rows": values.tolist()}


def measure(arrays, source, normalization, old_profiles, anchor, out):
    medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS], dtype=np.float64)
    if medians.shape != (6, 16) or not np.isfinite(medians).all() or (medians <= 0).any():
        raise ValueError("Invalid retained full-chunk row medians")
    headers = {s["label"]: s["current_header"]["data_attributes"] for s in source["sources"]}
    offsets = np.arange(-64, 65)
    flank = np.abs(offsets) > 3
    if np.count_nonzero(flank) != 122:
        raise ValueError("Fixed flank must contain 122 channels")
    static_raw, static_normalized, static_centers, static_background = [], [], [], []
    static_center_power, static_residual, moving_common_residual, signed_static_minus_moving, static_mean_profile = [], [], [], [], []
    moving_original = {k: [] for k in sorted(OLD_KEYS)}
    records, verified_patches = [], []
    checked_cells = 0
    for case_index, p in enumerate(old_profiles):
        track = p["selected_track"]
        reference, width = REFS[case_index], WIDTHS[case_index]
        path = ROOT/OLD_PATCH_DIR/(TRACK_IDS[case_index]+".npz")
        before_sha = digest(path)
        with np.load(path, allow_pickle=False) as old:
            if set(old.files) != OLD_KEYS:
                raise ValueError("Saved moving patch array set differs")
            copied = {k: old[k].copy() for k in sorted(OLD_KEYS)}
        if digest(path) != before_sha:
            raise ValueError("Saved moving patch changed during context pass")
        raw = copied["raw_power"]
        if raw.shape != (6, 16, 129) or raw.dtype != np.dtype("<f4"):
            raise ValueError("Saved moving raw shape/type differs")
        if copied["row_normalized_power"].shape != (6, 16, 129) or copied["row_normalized_power"].dtype != np.float64:
            raise ValueError("Saved moving normalized shape/type differs")
        if (copied["center_row_normalized_power"].shape != (6, 16) or
            copied["fixed_flank_median_row_normalized_power"].shape != (6, 16) or
            copied["center_minus_flank_each_row"].shape != (6, 16) or
            copied["mean_fixed_track_frequency_profile"].shape != (6, 129)):
            raise ValueError("Saved moving measured-array shape differs")
        if (not np.array_equal(copied["scans"], np.asarray(SCANS)) or
            not np.array_equal(copied["source_channel_offsets"], offsets) or
            not np.array_equal(copied["saved_full_chunk_row_medians"], medians)):
            raise ValueError("Saved moving profile coordinates or normalization differs")
        for key, expected in (("df_hz", DF), ("source_channel0", C0),
            ("reference_frequency_hz", track["reference_frequency_hz"]),
            ("drift_hz_s", track["drift_hz_s"]), ("width_channels", width),
            ("fixed_source_channel_shift", 0)):
            if copied[key].shape != () or copied[key].item() != expected:
                raise ValueError("Saved moving scalar differs: "+key)
        if track["reference_frequency_hz"] != FCH1+DF*reference:
            raise ValueError("Physical reference channel identity differs")
        dt = np.asarray([(headers[s]["tstart"]-anchor)*86400+(np.arange(16)+.5)*TSAMP
              -track["reference_seconds_from_anchor"] for s in SCANS])
        if not np.array_equal(copied["times_seconds_from_reference"], dt):
            raise ValueError("Saved moving actual scan times differ")
        predicted = np.rint((track["reference_frequency_hz"]-FCH1)/DF
                              +track["drift_hz_s"]*dt/DF).astype(np.int64)
        if not np.array_equal(copied["frozen_source_channel_centers"], predicted):
            raise ValueError("Saved moving channel predictions differ")
        indices = predicted[:, :, None]-C0+offsets[None, None, :]
        if indices.min() < 0 or indices.max() >= COUNT:
            raise ValueError("Old moving prediction exceeds source chunk")
        sampled = np.asarray([arrays[s][np.arange(16)[:, None], indices[i]] for i, s in enumerate(SCANS)])
        if sampled.dtype != raw.dtype or sampled.tobytes() != raw.tobytes():
            raise ValueError("Old saved moving raw cells differ from retained source bytes")
        checked_cells += sampled.size
        for i, s in enumerate(SCANS):
            if copied["center_minus_flank_each_row"][i].tolist() != p["scan_profiles"][i]["all_16_center_minus_flank_rows"]:
                raise ValueError("Saved moving residual differs from original JSON receipt")
        for k, values in copied.items():
            if values.dtype.kind in "iuf" and not np.isfinite(values).all():
                raise ValueError("Nonfinite old saved array: "+k)
            if moving_original[k] and (values.shape != moving_original[k][0].shape or values.dtype != moving_original[k][0].dtype):
                raise ValueError("Copied old array stacking would alter shape/type: "+k)
            moving_original[k].append(values)
        channels = reference+offsets
        if channels.min() < C0 or channels.max() >= C0+COUNT:
            raise ValueError("Fixed physical patch exceeds source chunk")
        physical_raw = np.asarray([arrays[s][:, channels-C0] for s in SCANS])
        normalized = physical_raw.astype(np.float64)/medians[:, :, None]
        background = np.median(normalized[:, :, flank], axis=2)
        radius = width//2
        center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
        residual = center-background
        common_moving = copied["center_row_normalized_power"]-background
        signed_difference = center-copied["center_row_normalized_power"]
        if not np.allclose(signed_difference, residual-common_moving, rtol=0, atol=1e-12):
            raise ValueError("Signed comparison differs from common-background subtraction")
        mean_profile = np.mean(normalized-background[:, :, None], axis=1)
        if not all(np.isfinite(x).all() for x in (normalized, background, center, residual, common_moving, signed_difference, mean_profile)):
            raise ValueError("Nonfinite physical context")
        static_raw.append(physical_raw); static_normalized.append(normalized)
        static_centers.append(np.full((6, 16), reference, dtype=np.int64))
        static_background.append(background); static_center_power.append(center)
        static_residual.append(residual); moving_common_residual.append(common_moving)
        signed_static_minus_moving.append(signed_difference)
        static_mean_profile.append(mean_profile)
        verified_patches.append({"track_id": TRACK_IDS[case_index], "path": str(path.relative_to(ROOT)),
            "sha256_before": before_sha, "sha256_after": digest(path),
            "raw_cells_byte_equal_to_retained_source": int(sampled.size),
            "all_old_arrays_copied_without_modification": True})
        records.append({"selected_track": track, "fixed_physical_reference_channel": reference,
            "static_width_channels": width, "static_frequency_shift_channels": 0,
            "source_channel_offsets": offsets.tolist(), "df_hz": DF,
            "static_flank": "median of122normalized physical offsets with abs(offset)>3 inside +/-64, per row",
            "saved_moving_arrays_copied_unchanged": True,
            "scan_profiles": [{"scan_id": s,
                "static_center_minus_static_flank": row_metrics(residual[i]),
                "copied_moving_center_minus_same_static_flank": row_metrics(common_moving[i]),
                "signed_static_minus_copied_moving_center": row_metrics(signed_difference[i]),
                "saved_moving_center_minus_original_moving_flank": row_metrics(copied["center_minus_flank_each_row"][i]),
                "mean_static_physical_frequency_profile_minus_static_flank": mean_profile[i].tolist(),
                "all_16_static_center_row_normalized_power": center[i].tolist(),
                "all_16_copied_moving_center_row_normalized_power": copied["center_row_normalized_power"][i].tolist(),
                "all_16_static_flank_row_normalized_power": background[i].tolist(),
                "all_16_original_moving_flank_row_normalized_power": copied["fixed_flank_median_row_normalized_power"][i].tolist(),
                "fixed_physical_source_channel_centers": [reference]*16,
                "saved_moving_source_channel_centers": predicted[i].tolist()}
                for i, s in enumerate(SCANS)],
            "classification": "UNRESOLVED_EXPLORATORY_STATIC_CONTEXT_NO_SKY_INFERENCE"})
        save(out/"STATIC_CONTEXT_PROFILES.json", {"completed_cases": len(records),
             "expected_cases": 9, "complete": len(records) == 9, "records": records})
        print("COMPLETED_GAP_STATIC_CONTEXT", TRACK_IDS[case_index], flush=True)
    if checked_cells != 111456 or len(records) != 9:
        raise ValueError("Incomplete source-checked physical context family")
    output_arrays = {"track_ids": np.asarray(TRACK_IDS), "scan_order": np.asarray(SCANS),
        "static_raw_power": np.asarray(static_raw), "static_row_normalized_power": np.asarray(static_normalized),
        "static_frozen_source_channel_centers": np.asarray(static_centers),
        "source_channel_offsets": offsets, "saved_full_chunk_row_medians": medians,
        "static_fixed_flank_median_row_normalized_power": np.asarray(static_background),
        "static_center_row_normalized_power": np.asarray(static_center_power),
        "static_center_minus_static_flank_each_row": np.asarray(static_residual),
        "copied_moving_center_minus_same_static_flank_each_row": np.asarray(moving_common_residual),
        "signed_static_minus_copied_moving_center_each_row": np.asarray(signed_static_minus_moving),
        "static_mean_frequency_profile_minus_static_flank": np.asarray(static_mean_profile),
        "static_physical_channel_grid": np.asarray(REFS)[:, None]+offsets[None, :],
        "static_physical_frequency_hz": FCH1+DF*(np.asarray(REFS)[:, None]+offsets[None, :]),
        "original_width_channels": np.asarray(WIDTHS), "fixed_static_frequency_shift_channels": 0}
    output_arrays.update({"saved_moving_"+k: np.asarray(v) for k, v in moving_original.items()})
    patch = out/"ALL_NINE_STATIC_AND_COPIED_MOVING_PROFILES.npz"
    np.savez_compressed(patch, **output_arrays)
    return {"case_count": 9, "case_scan_count": 54, "time_row_occurrences_per_metric": 864,
        "old_moving_raw_cells_byte_checked": checked_cells, "verified_original_patches": verified_patches,
        "array_bundle": {"path": patch.name, "sha256": digest(patch), "bytes": patch.stat().st_size},
        "profile_JSON_sha256": digest(out/"STATIC_CONTEXT_PROFILES.json"),
        "original_moving_array_keys_preserved": sorted(OLD_KEYS),
        "original_moving_numbers_modified_or_remeasured": False,
        "all_reference_channels_and_widths_fixed_before_job": True,
        "all_static_and_moving_comparisons_use_same_new_static_flank": True,
        "signed_static_minus_moving_matches_common_background_subtraction_atol": 1e-12,
        "old_moving_original_flank_and_residual_also_preserved": True,
        "new_peak_statistics_or_detection": False, "plot_count": 0}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("scope", "expected-scope-sha256", "compact-dir", "acquisition-summary", "outdir"):
        parser.add_argument("--"+flag, required=True)
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError("Static context CPU or wall deadline reached")
    signal.signal(signal.SIGALRM, deadline);signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        scope, source, acquisition, normalization, old_profiles, anchor = contract(args)
        global np
        import numpy as np
        spec = importlib.util.spec_from_file_location("unchanged_fresh_loader", ROOT/FRESH_PATH)
        fresh = importlib.util.module_from_spec(spec);spec.loader.exec_module(fresh);fresh.np = np
        arrays, verified = fresh.load_power(args, source, acquisition)
        summary = measure(arrays, source, normalization, old_profiles, anchor, out)
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if (measured["process_CPU_seconds_including_imports"] > CPU_CAP or
            measured["wall_seconds_including_imports"] > WALL_CAP or measured["peak_RSS_bytes"] > MEMORY_CAP):
            raise ResourceLimitExceeded("Measured use exceeds frozen static-context caps")
        result = {"status": "COMPLETE_NINE_GAP_STATIC_PHYSICAL_CONTEXT_EXPLORATORY_ONLY",
            "summary": summary, "verified_source_inputs": verified,
            "scope_sha256": digest(args.scope), "script_sha256": digest(__file__),
            "source_manifest_sha256": SOURCE_SHA, "acquisition_summary_sha256": ACQUISITION_SHA,
            "saved_normalization_sha256": digest(ROOT/NORMALIZATION_PATH),
            "old_profiles_JSON_sha256": digest(ROOT/OLD_PROFILE_JSON_PATH),
            "MJD_anchor": anchor, **measured,
            "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
            "one_historical_visit": True, "source_values_and_old_gap_drift_outcomes_already_opened": True,
            "prospective_for_new_fixed_static_context_metrics_only": True,
            "blind_or_independent_validation": False, "numeric_retry_authorized": False,
            "new_telescope_HTTP_requests": 0, "new_telescope_BODY_bytes": 0,
            "qualified_sky_pilot": False, "OFF_veto_applied": False,
            "A_B_status": "FAIL_CLOSED_UNCHANGED", "old_holdouts_reopened": False,
            "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
            "limitations": [
                "Fixed physical reference is the original first-midpoint channel, not a fitted stationary feature",
                "Static +/-64native-channel window spans only +/-181.47221878097126Hz and does not contain all moving trajectories",
                "Common static flank is a new comparison background; original moving center/flank/residual remain separately unchanged",
                "Distant moving centers can sample a different bandpass or continuum; common-background difference has no calibrated significance",
                "Weak or absent OFF excess in the fixed physical window does not establish absence elsewhere in OFF",
                "Selection used previous drift maxima; nine cases and their summaries are dependent and descriptive",
                "One historical visit; epoch1/2/3 label scans, not independent visits",
                "No new drift search, local maxima, refit, threshold, SNR/FAP calibration, veto or origin claim"]}
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps(result, allow_nan=False), flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status":
            "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY" if isinstance(exc, (ResourceLimitExceeded, TimeoutError))
            else "INCOMPLETE_STATIC_CONTEXT_NO_RETRY",
            "error_type": type(exc).__name__, "error": str(exc), "numeric_retry_authorized": False,
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
