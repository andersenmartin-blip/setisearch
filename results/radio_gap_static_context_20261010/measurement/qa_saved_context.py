"""One bounded saved-output/CSV audit; no HDF5 reads or detector rescoring."""
import csv
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
BASE = OUT.parent
CPU_CAP, WALL_CAP, RAM_CAP = 3, 120, 4*1024**3
FREEZE = "1fbb2fcf328581a7ceffda97d6db36850c4ba8ea"
CODE_SHA = "5a72c346151123aa52d59d3b2c1fdc0e2e301a5537ffd752a0bb7109d84fc0d9"
SCOPE_SHA = "d5e3f9981e564ea6f933184d9de63aaf2edc28ae29f0c5e061885b2dc7387881"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
IDS = tuple(f"{s}_gap_drift_rank_{r:02d}" for s in SCANS[::2] for r in (1, 2, 3))
METRICS = ("static_center_minus_static_flank", "copied_moving_center_minus_same_static_flank",
           "signed_static_minus_copied_moving_center", "saved_moving_center_minus_original_moving_flank")
SHORT = ("static", "moving_same_static_background", "static_minus_moving", "moving_original_background")
STATS = ("mean", "median", "positive_rows", "first_eight_mean", "last_eight_mean", "minimum_half_mean")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def exact(a, b):
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def row_summary(saved, values):
    require(values.shape == (16,), "Missing summary rows")
    require(exact(np.asarray(saved["all_16_rows"]), values), "JSON metric rows differ")
    first, last = values[:8].mean(), values[8:].mean()
    expected = (values.mean(), np.median(values), np.count_nonzero(values > 0), first, last, min(first, last))
    for name, value in zip(STATS, expected):
        require(saved[name] == value, "JSON metric differs: " + name)


def audit_csv(records):
    with (OUT/"STATIC_CONTEXT_54_SCAN_SUMMARIES.csv").open(newline="") as handle:
        scans = list(csv.DictReader(handle))
    with (OUT/"STATIC_CONTEXT_864_TIME_ROWS.csv").open(newline="") as handle:
        times = list(csv.DictReader(handle))
    require(len(scans) == 54 and len(times) == 864, "Wrong CSV row counts")
    scalar_float_checks = time_float_checks = integer_checks = 0
    k = 0
    for record in records:
        track = record["selected_track"]
        for saved in record["scan_profiles"]:
            row = scans[k]
            require(row["track_id"] == track["track_id"] and row["scan_id"] == saved["scan_id"], "CSV scan identity differs")
            require(row["original_originating_scan"] == track["originating_scan"], "CSV origin differs")
            require(int(row["fixed_reference_channel"]) == record["fixed_physical_reference_channel"], "CSV reference differs")
            require(int(row["original_width_channels"]) == record["static_width_channels"], "CSV width differs")
            for metric, short in zip(METRICS, SHORT):
                for statistic in STATS:
                    value = row[f"{short}_{statistic}"]
                    if statistic == "positive_rows":
                        require(int(value) == saved[metric][statistic], "CSV count differs"); integer_checks += 1
                    else:
                        require(float(value).hex() == float(saved[metric][statistic]).hex(), "CSV scalar float lost precision")
                        scalar_float_checks += 1
            for i in range(16):
                time_row = times[k*16+i]
                require(time_row["track_id"] == track["track_id"] and time_row["scan_id"] == saved["scan_id"] and int(time_row["time_row"]) == i, "CSV time identity differs")
                require(int(time_row["fixed_reference_channel"]) == record["fixed_physical_reference_channel"] and int(time_row["original_width_channels"]) == record["static_width_channels"], "CSV time geometry differs")
                require(int(time_row["saved_moving_center_channel"]) == saved["saved_moving_source_channel_centers"][i], "CSV moving center differs")
                values = {"static_center_normalized_power": saved["all_16_static_center_row_normalized_power"][i],
                          "copied_moving_center_normalized_power": saved["all_16_copied_moving_center_row_normalized_power"][i],
                          "static_flank_normalized_power": saved["all_16_static_flank_row_normalized_power"][i],
                          "original_moving_flank_normalized_power": saved["all_16_original_moving_flank_row_normalized_power"][i]}
                values.update({short+"_residual": saved[metric]["all_16_rows"][i] for metric, short in zip(METRICS, SHORT)})
                for name, expected in values.items():
                    require(float(time_row[name]).hex() == float(expected).hex(), "CSV time float lost precision")
                    time_float_checks += 1
            k += 1
    return {"CSV_scan_rows_checked": 54, "CSV_time_rows_checked": 864,
            "CSV_scalar_float_roundtrips": scalar_float_checks, "CSV_time_float_roundtrips": time_float_checks,
            "CSV_positive_count_integer_checks": integer_checks,
            "all_CSV_identities_order_geometry_and_float_bits_match_JSON": True}


def audit():
    code = ROOT/"tools/radio_gap_static_context_20261010/static_context.py"
    scope_path = ROOT/"tools/radio_gap_static_context_20261010/scope.json"
    require(sha(code) == CODE_SHA and sha(scope_path) == SCOPE_SHA, "Frozen implementation changed")
    scope = json.loads(scope_path.read_text())
    for name, expected in scope["pinned_dependency_files"].items():
        require(sha(ROOT/name) == expected, "Pinned old dependency changed")
    runtime = {name: importlib.metadata.version(name) for name in scope["runtime_package_versions"]}
    require(runtime == scope["runtime_package_versions"], "Pinned runtime changed")
    execution_path = OUT/"EXECUTION_RECEIPT.json"
    execution = json.loads(execution_path.read_text())
    require(execution["status"] == "COMPLETE_NINE_GAP_STATIC_PHYSICAL_CONTEXT_EXPLORATORY_ONLY", "Numeric job incomplete")
    require(execution["script_sha256"] == CODE_SHA and execution["scope_sha256"] == SCOPE_SHA, "Execution identity differs")
    require(execution["process_CPU_seconds_including_imports"] <= 20 and execution["wall_seconds_including_imports"] <= 1800 and execution["peak_RSS_bytes"] <= RAM_CAP, "Scientific job cap exceeded")
    require(execution["new_telescope_HTTP_requests"] == execution["new_telescope_BODY_bytes"] == 0, "Unexpected telescope access")
    require(execution["summary"]["old_moving_raw_cells_byte_checked"] == 111456, "Reported source comparison incomplete")
    require(len(execution["summary"]["verified_original_patches"]) == 9, "Missing source-checked patches")
    source = json.loads((ROOT/"tools/radio_fresh_band_20261009/source_manifest.json").read_text())
    acquisition = json.loads((ROOT/"results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json").read_text())
    decoded = {x["scan_id"]: x for x in acquisition["decoded_files"]}
    require(set(execution["verified_source_inputs"]) == set(SCANS), "Wrong verified source identities")
    for scan in SCANS:
        require(execution["verified_source_inputs"][scan]["file_sha256"] == decoded[scan]["file_sha256"], "Reported source file identity differs")
        require([r["time_row"] for r in decoded[scan]["decoded_rows"]] == list(range(16)), "Missing retained row identities")
    summary = execution["summary"]
    bundle = OUT/summary["array_bundle"]["path"]
    require(bundle.stat().st_size == summary["array_bundle"]["bytes"] and sha(bundle) == summary["array_bundle"]["sha256"], "Bundle pin changed")
    json_path = OUT/"STATIC_CONTEXT_PROFILES.json"
    require(sha(json_path) == summary["profile_JSON_sha256"], "Scientific JSON pin changed")
    result = json.loads(json_path.read_text())
    require(result["complete"] and result["completed_cases"] == result["expected_cases"] == 9, "Result family incomplete")
    records = result["records"]
    require(len(records) == 9 and [r["selected_track"]["track_id"] for r in records] == list(IDS), "Wrong result identity/order")
    old = json.loads((ROOT/"results/radio_gap_drift_20261010/measurement/FIXED_TOP3_PROFILES.json").read_text())
    normalization = json.loads((ROOT/"results/radio_fresh_band_20261009/stationary/NORMALIZATION.json").read_text())
    medians = np.asarray([normalization["row_power_medians"][scan] for scan in SCANS])
    with np.load(bundle, allow_pickle=False) as saved:
        a = {key: saved[key] for key in saved.files}
    for name, values in a.items():
        if values.dtype.kind in "iuf":
            require(np.isfinite(values).all(), "Nonfinite bundle array: "+name)
    require(a["static_raw_power"].shape == (9, 6, 16, 129) and a["static_raw_power"].dtype == np.dtype("float32"), "Wrong static raw shape/type")
    require(a["static_row_normalized_power"].shape == (9, 6, 16, 129) and a["static_row_normalized_power"].dtype == np.dtype("float64"), "Wrong normalized shape/type")
    require((a["static_raw_power"] >= 0).all(), "Negative static raw power")
    require(exact(a["saved_full_chunk_row_medians"], medians), "Median copy changed")
    require((medians > 0).all(), "Nonpositive median")
    require(exact(a["static_row_normalized_power"], a["static_raw_power"].astype(np.float64)/medians[None, :, :, None]), "Static normalization algebra differs")
    require(np.array_equal(a["track_ids"], IDS) and np.array_equal(a["scan_order"], SCANS), "Bundle identities differ")
    offsets = np.arange(-64, 65)
    references = np.asarray(scope["fixed_reference_channels"])
    require(np.array_equal(a["source_channel_offsets"], offsets), "Static offsets differ")
    require(np.array_equal(a["original_width_channels"], scope["original_widths_channels"]), "Original widths differ")
    require(np.array_equal(a["static_physical_channel_grid"], references[:, None]+offsets[None]), "Physical grid differs")
    require(exact(a["static_physical_frequency_hz"], 1876464843.75-2.835503418452676*(references[:, None]+offsets[None])), "Physical frequencies differ")
    require(a["fixed_static_frequency_shift_channels"].item() == 0, "Static frequency shifted")
    backgrounds = np.median(a["static_row_normalized_power"][:, :, :, np.abs(offsets)>3], axis=3)
    require(exact(a["static_fixed_flank_median_row_normalized_power"], backgrounds), "Static flank algebra differs")
    require(exact(a["static_mean_frequency_profile_minus_static_flank"], np.mean(a["static_row_normalized_power"]-backgrounds[:, :, :, None], axis=2)), "Static mean profiles differ")
    headers = {s["label"]: s["current_header"]["data_attributes"] for s in source["sources"]}
    anchor = min(headers[s]["tstart"] for s in SCANS)
    copy_count = metric_count = 0
    for j, record in enumerate(records):
        track = record["selected_track"]
        require(track == old[j]["selected_track"], "Old selection changed")
        require(record["fixed_physical_reference_channel"] == references[j] and record["static_width_channels"] == scope["original_widths_channels"][j], "Static selection differs")
        require(record["static_frequency_shift_channels"] == 0 and record["source_channel_offsets"] == offsets.tolist(), "Static geometry changed")
        old_path = ROOT/"results/radio_gap_drift_20261010/measurement/profiles"/(IDS[j]+".npz")
        require(sha(old_path) == old[j]["patch"]["sha256"], "Original patch changed")
        with np.load(old_path, allow_pickle=False) as prior:
            require(sorted(prior.files) == summary["original_moving_array_keys_preserved"], "Missing old array")
            for key in prior.files:
                require(exact(a["saved_moving_"+key][j], prior[key]), "Old array was changed: "+key)
                copy_count += 1
        dt = np.asarray([(headers[s]["tstart"]-anchor)*86400+(np.arange(16)+.5)*17.986224128-track["reference_seconds_from_anchor"] for s in SCANS])
        centers = np.rint((track["reference_frequency_hz"]-1876464843.75)/-2.835503418452676+track["drift_hz_s"]*dt/-2.835503418452676).astype(np.int64)
        require(exact(a["saved_moving_times_seconds_from_reference"][j], dt), "Old reference times differ")
        require(np.array_equal(a["saved_moving_frozen_source_channel_centers"][j], centers), "Old moving geometry differs")
        require(np.array_equal(a["static_frozen_source_channel_centers"][j], np.full((6,16), references[j], dtype=np.int64)), "Static centers moved")
        radius = record["static_width_channels"]//2
        center = a["static_row_normalized_power"][j, :, :, 64-radius:65+radius].mean(axis=2)
        require(exact(a["static_center_row_normalized_power"][j], center), "Static box center differs")
        moving = a["saved_moving_center_row_normalized_power"][j]
        values = (center-backgrounds[j], moving-backgrounds[j], center-moving, a["saved_moving_center_minus_flank_each_row"][j])
        fields = ("static_center_minus_static_flank_each_row", "copied_moving_center_minus_same_static_flank_each_row", "signed_static_minus_copied_moving_center_each_row", "saved_moving_center_minus_flank_each_row")
        for field, expected in zip(fields, values):
            require(exact(a[field][j], expected), "Metric array algebra differs")
        require(np.allclose(values[2], values[0]-values[1], rtol=0, atol=1e-12), "Shared-background cancellation differs")
        require(len(record["scan_profiles"]) == 6, "Missing scan profiles")
        for i, scan in enumerate(record["scan_profiles"]):
            require(scan["scan_id"] == SCANS[i], "Wrong scan order")
            for metric, value in zip(METRICS, values):
                row_summary(scan[metric], value[i]); metric_count += 1
            for field, expected in (("all_16_static_center_row_normalized_power", center[i]),
                                    ("all_16_copied_moving_center_row_normalized_power", moving[i]),
                                    ("all_16_static_flank_row_normalized_power", backgrounds[j,i]),
                                    ("all_16_original_moving_flank_row_normalized_power", a["saved_moving_fixed_flank_median_row_normalized_power"][j,i]),
                                    ("mean_static_physical_frequency_profile_minus_static_flank", a["static_mean_frequency_profile_minus_static_flank"][j,i])):
                require(exact(np.asarray(scan[field]), expected), "JSON center/flank/frequency samples differ")
            require(scan["fixed_physical_source_channel_centers"] == [int(references[j])]*16, "JSON fixed coordinates differ")
            require(np.array_equal(scan["saved_moving_source_channel_centers"], centers[i]), "JSON moving coordinates differ")
    require(copy_count == 153 and metric_count == 216, "Incomplete copy/metric audit")
    csv_checks = audit_csv(records)
    plot = json.loads((BASE/"figures/PLOTTING_RECEIPT.json").read_text())
    plot_assessment = "CAP_EXCEEDED_NO_RETRY" if plot["process_CPU_seconds_including_imports"] > plot["cpu_cap_seconds"] else "WITHIN_REPORTED_CAP"
    require(plot_assessment == "CAP_EXCEEDED_NO_RETRY", "Expected reported plot overrun is missing")
    require(plot["input_JSON_sha256"]["STATIC_CONTEXT_PROFILES.json"] == sha(json_path), "Plot input pin differs")
    for pin in plot["plots"]:
        fp = BASE/"figures"/pin["path"]
        require(sha(fp) == pin["sha256"] and fp.stat().st_size == pin["bytes"], "Original plot bytes changed")
    for name, expected in scope["pinned_dependency_files"].items():
        require(sha(ROOT/name) == expected, "Old dependency changed during QA")
    return {"old_array_byte_exact_copy_comparisons": copy_count, "case_count_checked": 9,
            "case_scan_count_checked": 54, "metric_summary_count_checked": metric_count,
            "metric_row_occurrences_checked": metric_count*16, "scalar_metric_checks": metric_count*6,
            "all_saved_numeric_arrays_finite": True, "all_pinned_old_files_unchanged": True,
            "static_mean_frequency_samples_checked": 9*6*129,
            "scientific_job_within_all_reported_caps": True, "reported_source_raw_comparison_cells": 111456,
            "source_raw_provenance_recheck_mode": "Original completed job receipt and unchanged input/code pins; no independent HDF5 reread.",
            "runtime_versions": runtime, **csv_checks,
            "original_plot_receipt_status_preserved": plot["status"],
            "plot_CPU_s": plot["process_CPU_seconds_including_imports"], "plot_CPU_cap_s": plot["cpu_cap_seconds"],
            "derived_plot_resource_assessment": plot_assessment,
            "plot_overrun_does_not_change_scientific_job_PASS": True,
            "plot_retry_or_rerender_performed": False,
            "whole_activity_CPU_estimated_or_measured_by_this_audit": False}


if __name__ == "__main__":
    cpu0, wall0 = time.process_time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def stop(signum, frame):
        raise TimeoutError("Saved-output QA cap reached")
    signal.signal(signal.SIGXCPU, stop); signal.signal(signal.SIGALRM, stop); signal.alarm(WALL_CAP)
    import numpy as np
    receipt = {"schema":"SETI_NINE_GAP_STATIC_CONTEXT_INDEPENDENT_SAVED_OUTPUT_QA_V1", "public_freeze_commit":FREEZE,
               "pre_execution_static_review":"PASS", "reviewed_script_sha256":CODE_SHA, "reviewed_scope_sha256":SCOPE_SHA,
               "QA_script_sha256":sha(Path(__file__)), "CPU_cap_s":CPU_CAP, "wall_cap_s":WALL_CAP, "RAM_cap_bytes":RAM_CAP,
               "input_mode":"Saved NPZ/JSON/CSV and byte hashes only; zero HDF5 reads, detector rescoring or analysis reruns."}
    try:
        receipt.update(audit());receipt["status"]="PASS_SCIENTIFIC_SAVED_OUTPUTS_PLOT_CAP_EXCEEDED_RECORDED"
    except Exception as exc:
        receipt.update(status="FAIL_SAVED_OUTPUT_QA", error_type=type(exc).__name__, error=str(exc));raise
    finally:
        receipt.update(process_CPU_s=time.process_time()-cpu0, wall_s=time.monotonic()-wall0,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        if receipt["process_CPU_s"] > CPU_CAP or receipt["wall_s"] > WALL_CAP or receipt["peak_RSS_bytes"] > RAM_CAP:
            receipt["status"]="INCOMPLETE_QA_RESOURCE_LIMIT_NO_RETRY"
        (OUT/"QA_RECEIPT.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        signal.alarm(0)
    require(receipt["status"]=="PASS_SCIENTIFIC_SAVED_OUTPUTS_PLOT_CAP_EXCEEDED_RECORDED", "QA did not pass")
    print(json.dumps({k:receipt[k] for k in ("status","process_CPU_s","wall_s","peak_RSS_bytes","old_array_byte_exact_copy_comparisons","metric_summary_count_checked")}))
