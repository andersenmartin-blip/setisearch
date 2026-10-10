#!/usr/bin/env python3
"""One fixed, saved-patch-only descriptive diagnostic; run only after public freeze."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["MPLBACKEND"] = "Agg"

ROOT = Path(__file__).resolve().parents[2]
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
ANCHOR = 158766416
C0 = 158334976
FCH1 = 1876464843.75
DF = -2.835503418452676
TSAMP = 17.986224128
WIDTHS = (1, 3, 5, 9)
IDS = tuple(f"{origin}_drift_rank_{rank:02d}" for origin in ONS for rank in (1, 2, 3))
CPU_CAP = 40
WALL_CAP = 1800
RAM_CAP = 4 * 1024**3


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summary(values):
    require(values.shape == (16,), "Every summary must retain exactly sixteen rows")
    first, last = float(values[:8].mean()), float(values[8:].mean())
    return {"all_16_rows": values.tolist(), "mean": float(values.mean()),
            "median": float(np.median(values)), "positive_rows": int(np.count_nonzero(values > 0)),
            "first_8_mean": first, "last_8_mean": last, "minimum_half_mean": min(first, last)}


def byte_equal(left, right):
    return left.dtype == right.dtype and left.shape == right.shape and left.tobytes(order="C") == right.tobytes(order="C")


def check_float(array, shape, dtype, label):
    require(array.shape == shape and array.dtype == np.dtype(dtype), f"Invalid {label} shape/dtype")
    require(np.isfinite(array).all(), f"Nonfinite {label}")


def load_inputs(scope):
    for pin in scope["input_files"]:
        path = ROOT / pin["path"]
        require(path.is_file() and path.stat().st_size == pin["bytes"], f"Missing/wrong-size input: {pin['path']}")
        require(digest(path) == pin["sha256"], f"Input SHA mismatch: {pin['path']}")
    source = json.loads((ROOT / scope["source_manifest_path"]).read_text())
    profiles = json.loads((ROOT / scope["old_profile_json_path"]).read_text())
    normalization = json.loads((ROOT / scope["normalization_path"]).read_text())
    require(source["physical_channel_interval_half_open"] == [C0, C0 + 1048576], "Wrong native chunk")
    require((source["fch1_hz"], source["df_hz"], source["tsamp_s"]) == (FCH1, DF, TSAMP), "Wrong physical geometry")
    require(len(source["sources"]) == 6 and {s["label"] for s in source["sources"]} == set(SCANS), "Wrong six source identities")
    headers = {s["label"]: s["current_header"]["data_attributes"] for s in source["sources"]}
    require(all(headers[s]["tsamp"] == TSAMP and headers[s]["fch1"] * 1e6 == FCH1
                and headers[s]["foff"] * 1e6 == DF for s in SCANS), "Header geometry mismatch")
    first_start = min(headers[s]["tstart"] for s in SCANS)
    row = np.arange(16)
    common_time = np.asarray([(headers[s]["tstart"] - first_start) * 86400 + row * TSAMP for s in SCANS])
    require(normalization["source_channel0"] == C0, "Wrong normalization origin")
    row_medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS], dtype=np.float64)
    check_float(row_medians, (6, 16), "float64", "retained row medians")
    require((row_medians > 0).all(), "Row medians must be positive")
    selected = [record for record in profiles if record["selected_track"]["family"] == "drift"]
    require(len(selected) == 9 and {r["selected_track"]["track_id"] for r in selected} == set(IDS), "Wrong nine selected drift identities")
    indexed = {r["selected_track"]["track_id"]: r for r in selected}
    records = [indexed[track_id] for track_id in IDS]
    require([r["selected_track"] for r in records] == scope["selected_tracks"], "Selected metadata differ from frozen scope")
    anchor_track = records[3]["selected_track"]
    require(anchor_track["source_reference_channel"] == ANCHOR and anchor_track["drift_hz_s"] == 0
            and anchor_track["width_channels"] == 1, "Wrong previously published ON2 rank01 anchor")
    physical_channels = ANCHOR + np.arange(-10, 11, dtype=np.int64)
    copied_centers, copied_center_power, old_times = [], [], []
    physical_raw = physical_norm = None
    patch_checks = []
    for record in records:
        track = record["selected_track"]
        track_id, width = track["track_id"], track["width_channels"]
        require(width in (1, 3) and track["originating_role"] == "ON" and track["originating_scan"] in ONS, "Wrong original selection")
        require(record["fixed_frequency_shift_channels"] == 0, "Old shifted profile is forbidden")
        path = ROOT / scope["old_profile_directory"] / record["patch"]["path"]
        before = digest(path)
        require(before == record["patch"]["sha256"], f"Old full patch pin mismatch: {track_id}")
        require(path.stat().st_size == record["patch"]["bytes"], f"Old full patch size mismatch: {track_id}")
        dt = np.asarray([(headers[s]["tstart"] - first_start) * 86400 + (row + .5) * TSAMP
                         - track["reference_seconds_from_anchor"] for s in SCANS])
        base = (track["reference_frequency_hz"] - FCH1) / DF
        predicted = np.rint(base + track["drift_hz_s"] * dt / DF).astype(np.int64)
        json_profiles = record["scan_profiles"]
        require(len(json_profiles) == 6 and [p["scan_id"] for p in json_profiles] == list(SCANS), "Wrong old scan profile order")
        json_centers = np.asarray([p["frozen_source_channel_centers"] for p in json_profiles], dtype=np.int64)
        require(np.array_equal(predicted, json_centers), f"Old fixed geometry mismatch: {track_id}")
        with np.load(path, allow_pickle=False) as saved:
            raw = saved["raw_power"]
            normalized = saved["row_normalized_power"]
            medians = saved["saved_full_chunk_row_medians"]
            centers = saved["frozen_source_channel_centers"]
            center_power = saved["center_row_normalized_power"]
            saved_times = saved["times_seconds_from_reference"]
            check_float(raw, (6, 16, 129), "float32", "saved raw power")
            check_float(normalized, (6, 16, 129), "float64", "saved normalized power")
            check_float(medians, (6, 16), "float64", "saved medians")
            check_float(center_power, (6, 16), "float64", "copied original moving center power")
            check_float(saved_times, (6, 16), "float64", "old reference times")
            require(centers.shape == (6, 16) and centers.dtype == np.dtype("int64"), "Invalid saved centers")
            require(np.array_equal(saved["scans"], np.asarray(SCANS)), "Wrong saved scan order")
            require(np.array_equal(saved["source_channel_offsets"], np.arange(-64, 65)), "Wrong old ±64 context")
            require(saved["source_channel0"].item() == C0 and saved["df_hz"].item() == DF, "Wrong saved source geometry")
            require(saved["reference_frequency_hz"].item() == track["reference_frequency_hz"]
                    and saved["drift_hz_s"].item() == track["drift_hz_s"]
                    and saved["width_channels"].item() == width and saved["fixed_source_channel_shift"].item() == 0,
                    "Old selected reference/width/drift changed")
            require(byte_equal(medians, row_medians) and (medians > 0).all(), "Retained median mismatch")
            require(byte_equal(saved_times, dt) and np.array_equal(centers, predicted), "Old saved time/center mismatch")
            indices = physical_channels[None, None, :] - centers[:, :, None] + 64
            require(indices.min() >= 0 and indices.max() < 129, "Missing common physical context; no extension allowed")
            gathered_raw = np.take_along_axis(raw, indices, axis=2)
            gathered_norm = np.take_along_axis(normalized, indices, axis=2)
            renormalized = gathered_raw.astype(np.float64) / medians[:, :, None]
            require(byte_equal(renormalized, gathered_norm), "Copied normalized cells differ from saved-median normalization")
            if physical_raw is None:
                physical_raw, physical_norm = gathered_raw.copy(), gathered_norm.copy()
            else:
                require(byte_equal(physical_raw, gathered_raw) and byte_equal(physical_norm, gathered_norm),
                        "Nine old patches disagree on the same physical raw/normalized cells; fail closed")
            copied_centers.append(centers.copy())
            copied_center_power.append(center_power.copy())
            old_times.append(saved_times.copy())
        after = digest(path)
        require(before == after, "Old patch changed during read")
        patch_checks.append({"track_id": track_id, "path": str(path.relative_to(ROOT)), "sha256_before": before,
                             "sha256_after": after, "anchor_offset_min": int((ANCHOR - predicted).min()),
                             "anchor_offset_max": int((ANCHOR - predicted).max()), "physical_cells_byte_equal": True})
    return (records, common_time, row_medians, physical_channels, physical_raw, physical_norm,
            np.asarray(copied_centers), np.asarray(copied_center_power), np.asarray(old_times), patch_checks)


def make_plots(out, frequencies, common_time, normalized, flank, reference, moving, matched_reference, differences, records):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FormatStrFormatter
    labels = ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")
    order = np.argsort(frequencies)
    freq_mhz = frequencies[order] / 1e6
    edge = abs(DF) / 2e6
    image = normalized - flank[:, :, None]
    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    fig.subplots_adjust(left=.10, right=.88, bottom=.09, top=.91, hspace=.46, wspace=.30)
    for i, ax in enumerate(axes.flat):
        im = ax.imshow(image[i][:, order], origin="lower", aspect="auto", interpolation="nearest",
                       extent=(freq_mhz[0] - edge, freq_mhz[-1] + edge, -.5, 15.5), vmin=-.5, vmax=3., cmap="viridis")
        ax.set_title(f"{labels[i]} · first midpoint {common_time[i, 0]:.1f} s", fontsize=10)
        ax.set_xlabel("Physical frequency (MHz)", fontsize=9)
        ax.set_ylabel("Saved time row", fontsize=9)
        ax.set_xticks(np.linspace(freq_mhz[0], freq_mhz[-1], 3))
        ax.xaxis.set_major_formatter(FormatStrFormatter("%.6f"))
        ax.tick_params(labelsize=8)
    cax = fig.add_axes([.91, .15, .016, .70])
    fig.colorbar(im, cax=cax, extend="both", label="Normalized power minus static flank")
    fig.suptitle("One common physical 21-channel context · all six scans", fontsize=12)
    fig.savefig(out / "COMMON_PHYSICAL_WATERFALL.png", dpi=120)
    plt.close(fig)

    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True)
    fig.subplots_adjust(left=.12, right=.97, bottom=.09, top=.90, hspace=.46, wspace=.22)
    values = reference[:2]
    lower, upper = float(values.min()), float(values.max())
    margin = max(.05, .08 * (upper - lower))
    for i, ax in enumerate(axes.flat):
        for j, width in enumerate((1, 3)):
            ax.plot(np.arange(16) * TSAMP, reference[j, i], marker="o", markersize=3, linewidth=1, label=f"width {width}")
        ax.set_ylim(min(0, lower) - margin, max(0, upper) + margin)
        ax.axhline(0, color="black", linewidth=.6)
        ax.set_title(labels[i], fontsize=11)
        ax.set_xlabel("Seconds from scan's first midpoint", fontsize=9)
        ax.set_ylabel("Center minus\nstatic flank", fontsize=9)
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=9)
    fig.suptitle("Fixed channel 158766416 · widths 1 and 3 · all 16 rows", fontsize=12)
    fig.savefig(out / "FIXED_REFERENCE_TIME.png", dpi=120)
    plt.close(fig)

    mean_delta = differences.mean(axis=2)
    fig, ax = plt.subplots(figsize=(13, 10))
    fig.subplots_adjust(left=.20, right=.84, bottom=.10, top=.90)
    im = ax.imshow(mean_delta, aspect="auto", vmin=-2.5, vmax=2.5, cmap="RdBu_r")
    ax.set_xticks(np.arange(6), labels)
    row_labels = [f"ON{r['selected_track']['originating_scan'][5]} r{r['selected_track']['display_rank']} (w{r['selected_track']['width_channels']})" for r in records]
    ax.set_yticks(np.arange(9), row_labels)
    for i in range(9):
        for j in range(6):
            ax.text(j, i, f"S {matched_reference[i, j].mean():.3f}\nD {moving[i, j].mean():.3f}\nΔ {mean_delta[i, j]:+.3f}",
                    ha="center", va="center", fontsize=8)
    ax.set_xlabel("Scan at the same physical background", fontsize=10)
    ax.set_ylabel("Previously selected drift case", fontsize=10)
    ax.set_title("S: fixed stationary mean · D: original drifting mean · Δ: S−D\nSame fourteen-channel physical flank; no refit", fontsize=12)
    cax = fig.add_axes([.88, .16, .022, .66])
    fig.colorbar(im, cax=cax, extend="both", label="Signed difference in normalized power")
    fig.savefig(out / "SAME_BACKGROUND_MEAN_DIFFERENCE.png", dpi=120)
    plt.close(fig)


def measure(scope, out):
    (records, common_time, medians, channels, raw, normalized, centers, moving_center,
     old_times, patch_checks) = load_inputs(scope)
    offsets = np.arange(-10, 11)
    flank = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
    fixed_center = np.asarray([normalized[:, :, 10 - w // 2:11 + w // 2].mean(axis=2) for w in WIDTHS])
    reference = fixed_center - flank[None, :, :]
    moving_residual = moving_center - flank[None, :, :]
    matched_reference = np.asarray([reference[WIDTHS.index(r["selected_track"]["width_channels"])] for r in records])
    differences = matched_reference - moving_residual
    frequencies = FCH1 + channels * DF
    payload = out / "COMMON_ANCHOR_AND_COMPARISONS.npz"
    np.savez_compressed(payload, raw_power=raw, row_normalized_power=normalized,
        saved_full_chunk_row_medians=medians, static_physical_flank_median=flank,
        scans=np.asarray(SCANS), source_channels=channels, source_channel_offsets=offsets,
        physical_frequency_hz=frequencies, times_seconds_from_visit_first_midpoint=common_time,
        reference_width_channels=np.asarray(WIDTHS), fixed_reference_center_normalized_power=fixed_center,
        fixed_reference_center_minus_static_flank=reference, original_track_ids=np.asarray(IDS),
        original_selected_width_channels=np.asarray([r["selected_track"]["width_channels"] for r in records]),
        original_saved_moving_centers=centers, original_saved_times_seconds_from_reference=old_times,
        original_copied_center_row_normalized_power=moving_center,
        original_drifting_center_minus_static_flank=moving_residual,
        stationary_minus_original_drifting=differences,
        original_saved_profile_mean=np.asarray([[p["mean_center_minus_flank"] for p in r["scan_profiles"]] for r in records]),
        anchor_source_channel=ANCHOR, anchor_frequency_hz=FCH1 + ANCHOR * DF, df_hz=DF,
        tsamp_s=TSAMP, source_channel0=C0)
    fixed_records = [{"scan_id": scan, "role": "ON" if scan in ONS else "OFF", "width_channels": width,
                      "anchor_source_channel": ANCHOR, "summary": summary(reference[j, i])}
                     for j, width in enumerate(WIDTHS) for i, scan in enumerate(SCANS)]
    comparisons = []
    for j, record in enumerate(records):
        scans = []
        for i, scan in enumerate(SCANS):
            old = record["scan_profiles"][i]
            scans.append({"scan_id": scan, "fixed_stationary_same_background": summary(matched_reference[j, i]),
                          "original_drifting_same_background": summary(moving_residual[j, i]),
                          "stationary_minus_original_drifting": summary(differences[j, i]),
                          "original_saved_mean_different_track_aligned_129_channel_background": old["mean_center_minus_flank"],
                          "original_frozen_source_channel_centers": centers[j, i].tolist()})
        comparisons.append({"selected_track": record["selected_track"], "scan_comparisons": scans})
    result = {"schema": "SETI_FIXED_DRIFT_ANCHOR_RESULT_V1", "status": "COMPLETE_DESCRIPTIVE_ONLY",
              "anchor_source_channel": ANCHOR, "anchor_frequency_hz": FCH1 + ANCHOR * DF,
              "physical_source_channel_interval_inclusive": [ANCHOR - 10, ANCHOR + 10],
              "flank_offsets": offsets[np.abs(offsets) > 3].tolist(), "reference_widths": list(WIDTHS),
              "all_rows_retained": 16, "same_physical_cells_in_all_nine_saved_patches": True,
              "unique_common_raw_cells": int(raw.size), "fixed_reference_scan_width_count": len(fixed_records),
              "original_drift_case_scan_comparison_count": 54, "fixed_reference": fixed_records,
              "original_drift_cases": comparisons, "limitations": scope["limitations"],
              "common_array_file": {"path": payload.name, "sha256": digest(payload), "bytes": payload.stat().st_size}}
    write_json(out / "DRIFT_ANCHOR_RESULT.json", result)
    make_plots(out, frequencies, common_time, normalized, flank, reference, moving_residual, matched_reference, differences, records)
    for pin in scope["input_files"]:
        require(digest(ROOT / pin["path"]) == pin["sha256"], "Input changed during diagnostic")
    return {"old_patch_checks": patch_checks, "nine_way_raw_cell_sha256": hashlib.sha256(raw.tobytes(order="C")).hexdigest(),
            "nine_way_normalized_cell_sha256": hashlib.sha256(normalized.tobytes(order="C")).hexdigest(),
            "all_nine_raw_and_normalized_physical_copies_byte_equal": True,
            "normalization_exactly_equal_using_saved_row_medians": True,
            "original_center_power_copied_without_remeasurement": True,
            "all_original_input_hashes_unchanged_after_execution": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, default=Path(__file__).with_name("analysis_scope.json"))
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--outdir", type=Path, default=ROOT / "results/radio_drift_anchor_20261010/measurement")
    args = parser.parse_args()
    cpu0, wall0 = time.process_time(), time.monotonic()
    require(digest(args.scope) == args.expected_scope_sha256, "Public scope SHA mismatch")
    scope = json.loads(args.scope.read_text())
    require(digest(Path(__file__)) == scope["script_sha256"], "Public script SHA mismatch")
    require(scope["anchor_source_channel"] == ANCHOR and scope["reference_widths"] == list(WIDTHS), "Wrong fixed scope")
    require(scope["CPU_cap_s"] == CPU_CAP and scope["wall_cap_s"] == WALL_CAP and scope["RAM_cap_bytes"] == RAM_CAP, "Wrong resource limits")
    for package, version in scope["runtime_versions"].items():
        require(importlib.metadata.version(package) == version, f"Runtime version mismatch: {package}")
    args.outdir.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def stop(signum, frame):
        raise TimeoutError(f"Resource stop signal {signum}")
    signal.signal(signal.SIGXCPU, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(WALL_CAP)
    global np
    receipt = {"schema": "SETI_FIXED_DRIFT_ANCHOR_EXECUTION_V1", "scope_sha256": args.expected_scope_sha256,
               "script_sha256": scope["script_sha256"], "single_process_no_retry": True, "new_source_bytes": 0}
    try:
        import numpy as np
        receipt.update(measure(scope, args.outdir))
        receipt["status"] = "COMPLETE_DESCRIPTIVE_ONLY"
    except Exception as exc:
        receipt.update(status="INCOMPLETE_NO_RETRY", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        receipt["output_files"] = [{"path": p.name, "sha256": digest(p), "bytes": p.stat().st_size}
                                   for p in sorted(args.outdir.iterdir()) if p.is_file()]
        receipt.update(cpu_s=time.process_time() - cpu0, wall_s=time.monotonic() - wall0,
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        if receipt["cpu_s"] > CPU_CAP or receipt["wall_s"] > WALL_CAP or receipt["peak_rss_bytes"] > RAM_CAP:
            receipt["status"] = "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
        write_json(args.outdir / "EXECUTION_RECEIPT.json", receipt)
        signal.alarm(0)
    require(receipt["status"] == "COMPLETE_DESCRIPTIVE_ONLY",
            "Resource limit exceeded; completed measurements do not certify bounded execution")
    print(json.dumps({k: receipt[k] for k in ("status", "cpu_s", "wall_s", "peak_rss_bytes", "new_source_bytes")}))


if __name__ == "__main__":
    main()
