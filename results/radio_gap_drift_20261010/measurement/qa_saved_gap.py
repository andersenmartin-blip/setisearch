"""Saved-result integrity and algebra QA; never rescores tracks or reads HDF5."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CPU_CAP, WALL_CAP, RAM_CAP = 20, 120, 4 * 1024**3
FREEZE = "ada64c4d46ead59b92f8e65ae2ce6aa4d13d0759"
SCRIPT_SHA = "b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58"
SCOPE_SHA = "c226ad41a87f344f71a642e0e7129657f00e44684db74d50124f075fd35d7a44"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
C0, COUNT, FCH1, DF, TSAMP = 158334976, 1048576, 1876464843.75, -2.835503418452676, 17.986224128
STARTS = (20480, 151552, 282624, 413696, 544768, 675840, 806912, 937984)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def exact(left, right):
    return left.shape == right.shape and left.dtype == right.dtype and left.tobytes() == right.tobytes()


def audit():
    scope_path = ROOT / "tools/radio_gap_drift_20261010/scope.json"
    script_path = ROOT / "tools/radio_gap_drift_20261010/gap_search.py"
    require(sha(scope_path) == SCOPE_SHA and sha(script_path) == SCRIPT_SHA, "Frozen code/scope changed")
    scope = json.loads(scope_path.read_text())
    pin_checks = []
    for name, expected in scope["pinned_dependency_files"].items():
        require(sha(ROOT / name) == expected, "Dependency changed")
        pin_checks.append({"path": name, "sha256": expected, "unchanged": True})
    runtime = {}
    for package, expected in scope["runtime_package_versions"].items():
        runtime[package] = importlib.metadata.version(package)
        require(runtime[package] == expected, "Runtime version changed")
    acquisition_path = ROOT / scope["acquisition_summary_path"]
    require(sha(acquisition_path) == scope["acquisition_summary_sha256"], "Acquisition summary changed")
    acquisition = json.loads(acquisition_path.read_text())
    execution = json.loads((OUT / "EXECUTION_RECEIPT.json").read_text())
    require(execution["status"] == "COMPLETED_EIGHT_GAP_DRIFT_CORES_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY", "Original job incomplete")
    require(execution["script_sha256"] == SCRIPT_SHA and execution["scope_sha256"] == SCOPE_SHA, "Execution pins changed")
    require(execution["process_CPU_seconds_including_imports"] <= 90 and execution["wall_seconds_including_imports"] <= 1800 and execution["peak_RSS_bytes"] <= RAM_CAP, "Original job exceeded cap")
    require(execution["new_telescope_HTTP_requests_during_analysis"] == execution["new_telescope_BODY_bytes_during_analysis"] == 0, "Unexpected telescope access")
    require(not execution["qualified_sky_pilot"] and not execution["OFF_veto_applied"] and not execution["numeric_retry_authorized"], "Qualification contract changed")
    decoded = {r["scan_id"]: r for r in acquisition["decoded_files"]}
    require(set(execution["verified_inputs"]) == set(SCANS), "Wrong verified scan identities")
    for scan in SCANS:
        require(execution["verified_inputs"][scan]["file_sha256"] == decoded[scan]["file_sha256"], "Recorded compact identity changed")
        require(execution["verified_inputs"][scan]["path"] == decoded[scan]["array_file"], "Recorded compact path changed")
    checkpoint = json.loads((OUT / "DRIFT_CHECKPOINT.json").read_text())
    require(checkpoint["complete"] and checkpoint["completed_scan_tiles"] == checkpoint["expected_scan_tiles"] == 24, "Checkpoint incomplete")
    require(len(checkpoint["completed_receipts"]) == 24, "Wrong map receipt count")
    grid = np.linspace(-4.0, 4.0, 763)
    prior = tuple((1 + 8*k)*4096 for k in range(32))
    require(all(not max(n, p) < min(n+4096, p+4096) for n in STARTS for p in prior), "Old/new carrier overlap")
    require(len(set(c for n in STARTS for c in range(n, n+4096))) == 32768, "New carrier overlap")
    maps = {s: [] for s in ONS}
    binary_checks = []
    for k, rec in enumerate(checkpoint["completed_receipts"]):
        tile, origin_index = divmod(k, 3)
        origin = ONS[origin_index]
        first, stop = C0 + STARTS[tile], C0 + STARTS[tile] + 4096
        require(rec["scan_id"] == origin and rec["tile_index"] == tile, "Wrong checkpoint order")
        require(rec["gap_index_k"] == tile*4 and rec["core_start_relative_channel"] == STARTS[tile], "Wrong gap identity")
        require(rec["reference_channel_interval_half_open"] == [first, stop], "Wrong map interval")
        require(rec["searched_carriers"] == 4096 and rec["valid_hypotheses_per_carrier"] == 1526, "Wrong map counts")
        path = OUT / rec["path"]
        require(path.stat().st_size == rec["bytes"] and sha(path) == rec["sha256"], "Map digest changed")
        binary_checks.append({"path": rec["path"], "sha256": rec["sha256"], "unchanged": True})
        with np.load(path, allow_pickle=False) as saved:
            data = {name: saved[name] for name in saved.files}
        channels = np.arange(first, stop)
        require(np.array_equal(data["source_reference_channels"], channels), "Wrong map channels")
        require(exact(data["frequency_hz_at_tref"], FCH1 + DF*channels), "Wrong map frequencies")
        require(exact(data["drift_grid_hz_s"], grid), "Drift grid changed")
        for name in ("maximum_robust_box_track_score", "winning_drift_hz_s", "winning_width_channels", "valid_hypothesis_count"):
            require(data[name].shape == (4096,) and np.isfinite(data[name]).all(), "Invalid complete map: " + name)
        require(np.isin(data["winning_drift_hz_s"], grid).all(), "Winner outside frozen drift grid")
        require(np.isin(data["winning_width_channels"], [1, 3]).all(), "Winner outside frozen widths")
        require((data["valid_hypothesis_count"] == 1526).all(), "Incomplete hypothesis count")
        norm = rec["normalization"]
        require(np.array_equal(norm["normalization_source_channels"], channels), "Wrong normalization core")
        for name in ("row_power_median", "row_residual_median", "row_winsorized_residual_location", "row_residual_MAD_scale", "normalization_unmasked_counts"):
            values = np.asarray(norm[name])
            require(values.shape == (16,) and np.isfinite(values).all(), "Invalid checkpoint normalization")
        require((np.asarray(norm["row_power_median"]) > 0).all() and (np.asarray(norm["row_residual_MAD_scale"]) > 0).all(), "Invalid normalization scale")
        require(((np.asarray(norm["normalization_unmasked_counts"]) > 0) & (np.asarray(norm["normalization_unmasked_counts"]) <= 4096)).all(), "Invalid normalization support")
        maps[origin].append(data)
    tops_path = OUT / "DRIFT_TOP20.json"
    require(sha(tops_path) == execution["profile_summary"]["source_top20_sha256"], "Top20 hash changed")
    tops = json.loads(tops_path.read_text())
    require(set(tops) == set(ONS) and all(len(tops[s]) == 20 for s in ONS), "Wrong top20 counts")
    source = json.loads((ROOT / "tools/radio_fresh_band_20261009/source_manifest.json").read_text())
    headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
    anchor = min(headers[s]["tstart"] for s in SCANS)
    for origin in ONS:
        data = maps[origin]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in data])
        channels = np.concatenate([r["source_reference_channels"] for r in data])
        drifts = np.concatenate([r["winning_drift_hz_s"] for r in data])
        widths = np.concatenate([r["winning_width_channels"] for r in data])
        chosen = []
        for j in np.lexsort((channels, -scores)):
            if all(abs(int(channels[j])-int(channels[old])) > 3 for old in chosen):
                chosen.append(int(j))
            if len(chosen) == 20:
                break
        for rank, j in enumerate(chosen, 1):
            rec = tops[origin][rank-1]
            require(rec["track_id"] == f"{origin}_gap_drift_rank_{rank:02d}" and rec["display_rank"] == rank, "Rank identity changed")
            require(rec["source_reference_channel"] == channels[j] and rec["maximum_robust_box_track_score"] == scores[j], "Saved maximum sorting differs")
            require(rec["drift_hz_s"] == drifts[j] and rec["width_channels"] == widths[j], "Winner metadata differs")
            require(rec["reference_frequency_hz"] == FCH1 + DF*channels[j], "Top20 frequency differs")
            require(rec["reference_seconds_from_anchor"] == (headers[origin]["tstart"]-anchor)*86400+.5*TSAMP, "Top20 reference time differs")
            require(rec["reference_core_tile"] == j//4096 and rec["family"] == "gap_drift", "Top20 core/family differs")
    profiles = json.loads((OUT / "FIXED_TOP3_PROFILES.json").read_text())
    expected_tracks = [track for origin in ONS for track in tops[origin][:3]]
    require(len(profiles) == 9 and [r["selected_track"] for r in profiles] == expected_tracks, "Wrong nine profile selections")
    normalization_path = ROOT / "results/radio_fresh_band_20261009/stationary/NORMALIZATION.json"
    require(sha(normalization_path) == execution["profile_summary"]["saved_normalization_sha256"], "Profile normalization pin changed")
    normalization = json.loads(normalization_path.read_text())
    medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS])
    require(medians.shape == (6, 16) and np.isfinite(medians).all() and (medians > 0).all(), "Invalid profile medians")
    scan_summaries = 0
    for record in profiles:
        track = record["selected_track"]
        path = OUT / record["patch"]["path"]
        require(path.stat().st_size == record["patch"]["bytes"] and sha(path) == record["patch"]["sha256"], "Profile patch changed")
        binary_checks.append({"path": record["patch"]["path"], "sha256": record["patch"]["sha256"], "unchanged": True})
        with np.load(path, allow_pickle=False) as saved:
            a = {k: saved[k] for k in saved.files}
        for key, value in a.items():
            if np.issubdtype(value.dtype, np.number):
                require(np.isfinite(value).all(), "Nonfinite profile array")
        require(a["raw_power"].shape == (6, 16, 129) and a["raw_power"].dtype == np.dtype("float32"), "Wrong profile raw shape/type")
        require(a["row_normalized_power"].shape == (6, 16, 129) and a["row_normalized_power"].dtype == np.dtype("float64"), "Wrong profile normalized shape/type")
        require(exact(a["saved_full_chunk_row_medians"], medians), "Wrong profile median copy")
        require(exact(a["row_normalized_power"], a["raw_power"].astype(np.float64)/medians[:, :, None]), "Profile normalization algebra differs")
        require(np.array_equal(a["scans"], SCANS) and np.array_equal(a["source_channel_offsets"], np.arange(-64, 65)), "Wrong profile scan/offset identities")
        dt = np.asarray([(headers[s]["tstart"]-anchor)*86400+(np.arange(16)+.5)*TSAMP-track["reference_seconds_from_anchor"] for s in SCANS])
        centers = np.rint((track["reference_frequency_hz"]-FCH1)/DF + track["drift_hz_s"]*dt/DF).astype(np.int64)
        require(exact(a["times_seconds_from_reference"], dt) and np.array_equal(a["frozen_source_channel_centers"], centers), "Profile time/center geometry differs")
        require(centers.min()-64 >= C0 and centers.max()+64 < C0+COUNT, "Profile exceeds retained source chunk")
        require(a["df_hz"].item() == DF and a["source_channel0"].item() == C0 and a["fixed_source_channel_shift"].item() == 0, "Profile source geometry differs")
        for key in ("reference_frequency_hz", "drift_hz_s", "width_channels"):
            require(a[key].item() == track[key], "Profile selection differs")
        flank = np.median(a["row_normalized_power"][:, :, np.abs(np.arange(-64, 65)) > 3], axis=2)
        radius = track["width_channels"]//2
        center = a["row_normalized_power"][:, :, 64-radius:65+radius].mean(axis=2)
        residual = center-flank
        mean_profile = np.mean(a["row_normalized_power"]-flank[:, :, None], axis=1)
        for key, expected in (("fixed_flank_median_row_normalized_power", flank), ("center_row_normalized_power", center),
                              ("center_minus_flank_each_row", residual), ("mean_fixed_track_frequency_profile", mean_profile)):
            require(exact(a[key], expected), "Profile algebra differs: " + key)
        require(len(record["scan_profiles"]) == 6 and record["fixed_frequency_shift_channels"] == 0, "Wrong profile summary contract")
        for i, scan in enumerate(SCANS):
            rec = record["scan_profiles"][i]
            require(rec["scan_id"] == scan, "Wrong scan summary identity")
            require(exact(np.asarray(rec["all_16_center_minus_flank_rows"]), residual[i]), "JSON residual rows differ")
            require(np.array_equal(rec["frozen_source_channel_centers"], centers[i]), "JSON profile centers differ")
            raw_center = a["raw_power"][i, :, 64-radius:65+radius].mean(axis=1)
            require(exact(np.asarray(rec["all_16_raw_width_mean_power"], dtype=np.float32), raw_center), "JSON raw center means differ")
            for key, expected in (("mean_center_minus_flank", residual[i].mean()), ("median_center_minus_flank", np.median(residual[i])),
                                  ("positive_rows", np.count_nonzero(residual[i] > 0)),
                                  ("first_eight_mean_center_minus_flank", residual[i, :8].mean()),
                                  ("last_eight_mean_center_minus_flank", residual[i, 8:].mean())):
                require(rec[key] == expected, "Saved profile metric differs")
            scan_summaries += 1
    summary = execution["search_summary"]
    require(summary["completed_scan_tiles"] == 24 and summary["carriers_per_ON"] == 32768, "Search summary counts differ")
    require(summary["prior_plus_new_unique_carriers_per_ON"] == 163840 and summary["prior_plus_new_native_chunk_fraction_searched"] == .15625, "Coverage summary differs")
    require(execution["profile_summary"]["profile_count"] == 9 and execution["profile_summary"]["all_rows_retained"] == 16, "Profile summary counts differ")
    for name, expected in scope["pinned_dependency_files"].items():
        require(sha(ROOT / name) == expected, "Dependency changed during QA")
    require(sha(acquisition_path) == scope["acquisition_summary_sha256"], "Acquisition metadata changed during QA")
    return {"metadata_dependency_checks": pin_checks, "runtime_package_versions": runtime,
            "binary_product_checks": binary_checks, "binary_product_count": len(binary_checks),
            "complete_scan_core_maps_checked": 24, "complete_carrier_maximum_records_checked": 98304,
            "valid_hypotheses_per_carrier_checked": 1526, "all_drift_winners_on_frozen_grid": True,
            "old_and_new_carrier_cores_disjoint": True, "top20_rank_records_reconstructed_from_saved_maxima": 60,
            "detector_rescoring_performed": False, "fixed_profile_count_checked": 9,
            "profile_scan_summaries_checked": scan_summaries, "profile_residual_rows_checked": scan_summaries*16,
            "raw_profile_cells_checked": 9*6*16*129, "all_profile_arrays_and_metrics_match_saved_JSON": True,
            "all_pinned_metadata_and_code_unchanged": True, "source_HDF5_reads": 0}


if __name__ == "__main__":
    cpu0, wall0 = time.process_time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def stop(signum, frame):
        raise TimeoutError("Saved gap QA resource cap reached")
    signal.signal(signal.SIGXCPU, stop); signal.signal(signal.SIGALRM, stop); signal.alarm(WALL_CAP)
    import numpy as np
    receipt = {"schema": "SETI_SAVED_GAP_DRIFT_INDEPENDENT_QA_V1", "public_freeze_commit": FREEZE,
               "reviewed_script_sha256": SCRIPT_SHA, "reviewed_scope_sha256": SCOPE_SHA,
               "pre_execution_static_review": "PASS", "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP,
               "RAM_cap_bytes": RAM_CAP, "input_mode": "Saved maps, profiles and JSON only; no HDF5 read, detector rescore or analysis rerun.",
               "QA_script_sha256": sha(Path(__file__))}
    try:
        receipt.update(audit()); receipt["status"] = "PASS_SAVED_OUTPUTS_ONLY"
    except Exception as exc:
        receipt.update(status="FAIL_SAVED_OUTPUTS_ONLY", error_type=type(exc).__name__, error=str(exc)); raise
    finally:
        receipt.update(process_CPU_s=time.process_time()-cpu0, wall_s=time.monotonic()-wall0,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        if receipt["process_CPU_s"] > CPU_CAP or receipt["wall_s"] > WALL_CAP or receipt["peak_RSS_bytes"] > RAM_CAP:
            receipt["status"] = "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
        (OUT/"QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
        signal.alarm(0)
    require(receipt["status"] == "PASS_SAVED_OUTPUTS_ONLY", "QA did not pass")
    print(json.dumps({k:receipt[k] for k in ("status", "process_CPU_s", "wall_s", "peak_RSS_bytes", "binary_product_count")}))
