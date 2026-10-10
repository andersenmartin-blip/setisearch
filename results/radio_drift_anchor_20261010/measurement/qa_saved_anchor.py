"""Bounded independent QA of saved anchor products; no search or HDF5 reads."""
import hashlib
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
SCRIPT_SHA = "930a89ee67b4a417917e1874629a595a644f0727077af02bfb370f7f18f0dbb5"
SCOPE_SHA = "f037f6b838ae964047584595b5ce79c5a3b7df4f2316c381c266c1c0d154ae0c"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
IDS = tuple(f"{s}_drift_rank_{r:02d}" for s in SCANS[::2] for r in (1, 2, 3))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def exact(left, right):
    return left.shape == right.shape and left.dtype == right.dtype and left.tobytes() == right.tobytes()


def check_summary(saved, values):
    require(values.shape == (16,), "Summary lost time rows")
    require(exact(np.asarray(saved["all_16_rows"], dtype=np.float64), values), "JSON residual rows differ")
    first, last = values[:8].mean(), values[8:].mean()
    expected = {"mean": values.mean(), "median": np.median(values),
                "positive_rows": np.count_nonzero(values > 0), "first_8_mean": first,
                "last_8_mean": last, "minimum_half_mean": min(first, last)}
    for key, value in expected.items():
        require(saved[key] == value, "Saved summary metric differs: " + key)


def audit():
    scope_path = ROOT / "tools/radio_drift_anchor_20261010/analysis_scope.json"
    script_path = ROOT / "tools/radio_drift_anchor_20261010/drift_anchor.py"
    require(sha(scope_path) == SCOPE_SHA and sha(script_path) == SCRIPT_SHA, "Frozen code/scope changed")
    scope = json.loads(scope_path.read_text())
    input_checks = []
    for pin in scope["input_files"]:
        p = ROOT / pin["path"]
        require(p.stat().st_size == pin["bytes"] and sha(p) == pin["sha256"], "Input pin changed")
        input_checks.append({"path": pin["path"], "sha256": pin["sha256"], "unchanged": True})
    execution = json.loads((OUT / "EXECUTION_RECEIPT.json").read_text())
    require(execution["status"] == "COMPLETE_DESCRIPTIVE_ONLY", "Incomplete original execution")
    require(execution["scope_sha256"] == SCOPE_SHA and execution["script_sha256"] == SCRIPT_SHA, "Execution pin mismatch")
    require(execution["cpu_s"] <= 40 and execution["wall_s"] <= 1800 and execution["peak_rss_bytes"] <= RAM_CAP, "Original job cap exceeded")
    require(execution["new_source_bytes"] == 0, "Unexpected source bytes")
    require(len(execution["output_files"]) == 5, "Expected five original scientific/display products")
    output_checks = []
    for pin in execution["output_files"]:
        p = OUT / pin["path"]
        require(p.stat().st_size == pin["bytes"] and sha(p) == pin["sha256"], "Output pin mismatch")
        output_checks.append({"path": pin["path"], "sha256": pin["sha256"], "unchanged": True})
    result = json.loads((OUT / "DRIFT_ANCHOR_RESULT.json").read_text())
    require(result["status"] == "COMPLETE_DESCRIPTIVE_ONLY", "Wrong result status")
    require(result["fixed_reference_scan_width_count"] == 24 and result["original_drift_case_scan_comparison_count"] == 54, "Wrong result counts")
    require(result["unique_common_raw_cells"] == 2016 and result["all_rows_retained"] == 16, "Wrong common cell count")
    require(result["anchor_source_channel"] == 158766416 and result["reference_widths"] == [1, 3, 5, 9], "Changed fixed definitions")
    require(len(result["fixed_reference"]) == 24 and len(result["original_drift_cases"]) == 9, "Missing records")
    require([r["selected_track"]["track_id"] for r in result["original_drift_cases"]] == list(IDS), "Wrong case order")
    with np.load(OUT / "COMMON_ANCHOR_AND_COMPARISONS.npz", allow_pickle=False) as saved:
        a = {k: saved[k] for k in saved.files}
    for key, value in a.items():
        if np.issubdtype(value.dtype, np.number):
            require(np.isfinite(value).all(), "Nonfinite saved array: " + key)
    require(a["raw_power"].shape == (6, 16, 21) and a["raw_power"].dtype == np.dtype("float32"), "Wrong raw shape/type")
    require(a["row_normalized_power"].shape == (6, 16, 21) and a["row_normalized_power"].dtype == np.dtype("float64"), "Wrong normalized shape/type")
    require(np.array_equal(a["scans"], SCANS) and np.array_equal(a["original_track_ids"], IDS), "Wrong saved identities")
    channels = 158766416 + np.arange(-10, 11)
    require(np.array_equal(a["source_channels"], channels), "Wrong physical channels")
    require(np.array_equal(a["source_channel_offsets"], np.arange(-10, 11)), "Wrong physical offsets")
    require(exact(a["physical_frequency_hz"], 1876464843.75 + channels * -2.835503418452676), "Wrong frequencies")
    require(a["anchor_frequency_hz"].item() == result["anchor_frequency_hz"], "Wrong anchor frequency")
    source = json.loads((ROOT / scope["source_manifest_path"]).read_text())
    headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
    earliest = min(headers[s]["tstart"] for s in SCANS)
    times = np.asarray([(headers[s]["tstart"] - earliest) * 86400 + np.arange(16) * 17.986224128 for s in SCANS])
    require(exact(a["times_seconds_from_visit_first_midpoint"], times), "Wrong common time axis")
    old_records = json.loads((ROOT / scope["old_profile_json_path"]).read_text())
    old = {r["selected_track"]["track_id"]: r for r in old_records}
    copies = 0
    for j, track_id in enumerate(IDS):
        record = old[track_id]
        with np.load(ROOT / scope["old_profile_directory"] / record["patch"]["path"], allow_pickle=False) as prior:
            centers = prior["frozen_source_channel_centers"]
            indices = channels[None, None, :] - centers[:, :, None] + 64
            require(indices.min() >= 0 and indices.max() < 129, "Out-of-range physical gather")
            for key in ("raw_power", "row_normalized_power"):
                require(exact(a[key], np.take_along_axis(prior[key], indices, axis=2)), "Common physical copy differs")
                copies += 1
            require(exact(a["saved_full_chunk_row_medians"], prior["saved_full_chunk_row_medians"]), "Median copy differs")
            require(exact(a["original_saved_moving_centers"][j], centers), "Moving centers changed")
            require(exact(a["original_saved_times_seconds_from_reference"][j], prior["times_seconds_from_reference"]), "Moving reference times changed")
            require(exact(a["original_copied_center_row_normalized_power"][j], prior["center_row_normalized_power"]), "Moving center power changed")
        require(result["original_drift_cases"][j]["selected_track"] == record["selected_track"], "Selection metadata changed")
        require(len(result["original_drift_cases"][j]["scan_comparisons"]) == 6, "Missing comparison scans")
        for i, scan in enumerate(SCANS):
            copied_old = record["scan_profiles"][i]["mean_center_minus_flank"]
            require(a["original_saved_profile_mean"][j, i] == copied_old, "Old mean array changed")
            comparison = result["original_drift_cases"][j]["scan_comparisons"][i]
            require(comparison["scan_id"] == scan, "Wrong comparison scan")
            require(comparison["original_saved_mean_different_track_aligned_129_channel_background"] == copied_old, "Old-background JSON mean changed")
            require(np.array_equal(comparison["original_frozen_source_channel_centers"], a["original_saved_moving_centers"][j, i]), "JSON centers changed")
    require(exact(a["row_normalized_power"], a["raw_power"].astype(np.float64) / a["saved_full_chunk_row_medians"][:, :, None]), "Normalization identity fails")
    flank = np.median(a["row_normalized_power"][:, :, np.abs(np.arange(-10, 11)) > 3], axis=2)
    require(exact(flank, a["static_physical_flank_median"]), "Static flank differs")
    require(result["flank_offsets"] == [-10, -9, -8, -7, -6, -5, -4, 4, 5, 6, 7, 8, 9, 10], "Wrong flank identities")
    fixed = np.asarray([a["row_normalized_power"][:, :, 10-w//2:11+w//2].mean(axis=2) for w in (1, 3, 5, 9)])
    require(exact(fixed, a["fixed_reference_center_normalized_power"]), "Fixed center algebra differs")
    require(exact(fixed - flank[None], a["fixed_reference_center_minus_static_flank"]), "Fixed residual algebra differs")
    moving = a["original_copied_center_row_normalized_power"] - flank[None]
    require(exact(moving, a["original_drifting_center_minus_static_flank"]), "Moving residual algebra differs")
    widths = [old[track_id]["selected_track"]["width_channels"] for track_id in IDS]
    require(np.array_equal(a["original_selected_width_channels"], widths), "Changed original widths")
    matched = np.asarray([a["fixed_reference_center_minus_static_flank"][(1, 3, 5, 9).index(w)] for w in widths])
    require(exact(matched - moving, a["stationary_minus_original_drifting"]), "Difference algebra differs")
    summaries = 0
    for k, rec in enumerate(result["fixed_reference"]):
        wi, si = divmod(k, 6)
        require(rec["width_channels"] == (1, 3, 5, 9)[wi] and rec["scan_id"] == SCANS[si], "Wrong static summary identity")
        require(rec["role"] == ("ON" if si % 2 == 0 else "OFF"), "Wrong static role")
        check_summary(rec["summary"], a["fixed_reference_center_minus_static_flank"][wi, si]); summaries += 1
    for j, case in enumerate(result["original_drift_cases"]):
        for i, rec in enumerate(case["scan_comparisons"]):
            for field, values in (("fixed_stationary_same_background", matched[j, i]),
                                  ("original_drifting_same_background", moving[j, i]),
                                  ("stationary_minus_original_drifting", a["stationary_minus_original_drifting"][j, i])):
                check_summary(rec[field], values); summaries += 1
    require(exact(a["stationary_minus_original_drifting"][3], np.zeros((6, 16))), "Exact zero-drift anchor copy should give zero difference")
    require(hashlib.sha256(a["raw_power"].tobytes()).hexdigest() == execution["nine_way_raw_cell_sha256"], "Common raw digest differs")
    require(hashlib.sha256(a["row_normalized_power"].tobytes()).hexdigest() == execution["nine_way_normalized_cell_sha256"], "Common normalized digest differs")
    for pin in scope["input_files"]:
        require(sha(ROOT / pin["path"]) == pin["sha256"], "Input changed during QA")
    return {"input_checks": input_checks, "output_checks": output_checks,
            "physical_raw_and_normalized_copy_comparisons": copies, "unique_common_raw_cells": 2016,
            "summary_count_checked": summaries, "summary_row_occurrences_checked": summaries * 16,
            "summary_scalar_metrics_checked": summaries * 6,
            "all_old_input_hashes_unchanged": True, "all_saved_numeric_arrays_finite": True,
            "copied_original_center_powers_and_old_background_means_unchanged": True,
            "exact_zero_drift_anchor_copy_difference_is_zero": True}


if __name__ == "__main__":
    cpu0, wall0 = time.process_time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def stop(signum, frame):
        raise TimeoutError("Saved-output QA resource cap reached")
    signal.signal(signal.SIGXCPU, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(WALL_CAP)
    import numpy as np
    receipt = {"schema": "SETI_SAVED_DRIFT_ANCHOR_INDEPENDENT_QA_V1", "public_freeze_commit": FREEZE,
               "reviewed_script_sha256": SCRIPT_SHA, "reviewed_scope_sha256": SCOPE_SHA,
               "pre_execution_static_review": "PASS", "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP,
               "RAM_cap_bytes": RAM_CAP, "input_mode": "Saved NPZ and JSON products only; no HDF5/source read, detector rescore or analysis rerun.",
               "QA_script_sha256": sha(Path(__file__))}
    try:
        receipt.update(audit()); receipt["status"] = "PASS_SAVED_OUTPUTS_ONLY"
    except Exception as exc:
        receipt.update(status="FAIL_SAVED_OUTPUTS_ONLY", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        receipt.update(process_CPU_s=time.process_time() - cpu0, wall_s=time.monotonic() - wall0,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        if receipt["process_CPU_s"] > CPU_CAP or receipt["wall_s"] > WALL_CAP or receipt["peak_RSS_bytes"] > RAM_CAP:
            receipt["status"] = "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
        (OUT / "QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        signal.alarm(0)
    require(receipt["status"] == "PASS_SAVED_OUTPUTS_ONLY", "QA did not pass")
    print(json.dumps({k: receipt[k] for k in ("status", "process_CPU_s", "wall_s", "peak_RSS_bytes", "summary_count_checked")}))
