#!/usr/bin/env python3
"""Two JSON-only figures for nine fixed original gap-reference contexts.

Read only completed STATIC_CONTEXT_PROFILES.json and EXECUTION_RECEIPT.json.
Display saved S, D and signed S-D means and all129 static physical frequency
profile samples for allsixscans. No source/NPZ access, new measurements,
peak fitting, recentering, masking, optimization, classification or OFF veto.
"""
import argparse
import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path

CPU_START = time.process_time()
WALL_START = time.monotonic()
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SUCCESS = "COMPLETE_NINE_GAP_STATIC_PHYSICAL_CONTEXT_EXPLORATORY_ONLY"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
SHORT = ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")
REFERENCES = (158358343, 158355634, 158879966, 159145548, 159144660,
              159014473, 158489515, 158490607, 159145372)
WIDTHS = (3, 3, 3, 1, 1, 1, 1, 1, 1)
EXPECTED_TRACK_IDS = tuple(f"epoch{epoch}_on_gap_drift_rank_{rank:02d}"
                           for epoch in (1, 2, 3) for rank in (1, 2, 3))
METRICS = ("static_center_minus_static_flank",
           "copied_moving_center_minus_same_static_flank",
           "signed_static_minus_copied_moving_center")
COLORS = ("#1565a8", "#1565a8", "#2b7d46", "#2b7d46", "#7a469b", "#7a469b")
STYLES = ("-", "--", "-", "--", "-", "--")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_sequence(values, length, name):
    if len(values) != length or not all(math.isfinite(value) for value in values):
        raise ValueError(f"Missing/non-finite saved {name}")


def load_contract(source, profiles_pin, execution_pin):
    names = ("STATIC_CONTEXT_PROFILES.json", "EXECUTION_RECEIPT.json")
    pins = {names[0]: profiles_pin, names[1]: execution_pin}
    for name, pin in pins.items():
        if digest(source / name) != pin:
            raise ValueError(f"Saved JSON pin differs: {name}")
    profiles = json.loads((source / names[0]).read_text())
    execution = json.loads((source / names[1]).read_text())
    if execution["status"] != SUCCESS:
        raise ValueError("Static-context scientific execution is not complete")
    if (profiles["complete"] is not True or profiles["completed_cases"] != 9
            or profiles["expected_cases"] != 9 or len(profiles["records"]) != 9):
        raise ValueError("Expected nine complete saved static cases")
    records = profiles["records"]
    if tuple(record["selected_track"]["track_id"] for record in records) != EXPECTED_TRACK_IDS:
        raise ValueError("Case ordering/selection differs from original nine gap top3")
    saved_means, static_profiles, labels, metadata = [], [], [], []
    offsets_hz = None
    df_hz = None
    for index, record in enumerate(records):
        track = record["selected_track"]
        if (record["fixed_physical_reference_channel"] != REFERENCES[index]
                or track["source_reference_channel"] != REFERENCES[index]
                or record["static_width_channels"] != WIDTHS[index]
                or track["width_channels"] != WIDTHS[index]):
            raise ValueError("Original reference or selected width changed")
        if record["source_channel_offsets"] != list(range(-64, 65)):
            raise ValueError("Expected all129 unmasked static channel offsets")
        this_df = record["df_hz"]
        if not math.isfinite(this_df) or abs(this_df - (-2.835503418452676)) > 1e-12:
            raise ValueError("Native negative frequency increment differs")
        if df_hz is None:
            df_hz = this_df
            offsets_hz = np.asarray(record["source_channel_offsets"], dtype=float) * df_hz
        elif this_df != df_hz:
            raise ValueError("Inconsistent saved frequency increments")
        if track["originating_scan"] != SCANS[2 * (index // 3)] or track["display_rank"] != index % 3 + 1:
            raise ValueError("Original origin/rank labels differ")
        if not all(math.isfinite(track[key]) for key in ("reference_frequency_hz", "drift_hz_s")):
            raise ValueError("Non-finite original case labels")
        scans = record["scan_profiles"]
        if [scan["scan_id"] for scan in scans] != list(SCANS):
            raise ValueError("Expected allsix ordered saved scan profiles")
        mean_rows, frequency_rows = [], []
        for scan in scans:
            means = []
            for key in METRICS:
                metric = scan[key]
                if not math.isfinite(metric["mean"]):
                    raise ValueError("Non-finite saved summary mean")
                finite_sequence(metric["all_16_rows"], 16, key + " rows")
                means.append(metric["mean"])
            profile = scan["mean_static_physical_frequency_profile_minus_static_flank"]
            finite_sequence(profile, 129, "static physical frequency profile")
            mean_rows.append(means)
            frequency_rows.append(profile)
        saved_means.append(mean_rows)
        static_profiles.append(frequency_rows)
        short = f"ON{index // 3 + 1} r{index % 3 + 1}"
        detail = (f"{track['reference_frequency_hz'] / 1e6:.6f} MHz · "
                  f"{track['drift_hz_s']:+.6f} Hz/s · w{WIDTHS[index]}")
        labels.append(short + "\n" + detail)
        metadata.append({"track_id": track["track_id"], "short_label": short,
                         "fixed_original_reference_channel": REFERENCES[index],
                         "reference_frequency_hz": track["reference_frequency_hz"],
                         "original_drift_hz_s": track["drift_hz_s"],
                         "original_width_channels": WIDTHS[index]})
    # Negative DF makes the saved channel-order frequency sequence descending.
    # Sort only its display order; retain every original profile sample.
    order = np.argsort(offsets_hz)
    if len(set(order.tolist())) != 129 or not np.all(np.diff(offsets_hz[order]) > 0):
        raise ValueError("Frequency display order is not strictly ascending")
    return pins, np.asarray(saved_means), np.asarray(static_profiles), offsets_hz, order, labels, metadata


def means_figure(output, saved, labels):
    delta = saved[:, :, 2]
    limit = max(float(np.max(np.abs(delta))) * 1.05, 1e-12)
    fig, ax = plt.subplots(figsize=(15, 11.8))
    image = ax.imshow(delta, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(6), SHORT, fontsize=10)
    ax.set_yticks(range(9), labels, fontsize=8.8)
    ax.set_xlabel("Scan at the same fixed original physical reference", fontsize=10, labelpad=10)
    for case in range(9):
        for scan in range(6):
            rgba = image.cmap(image.norm(delta[case, scan]))
            light = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
            s, d, difference = saved[case, scan]
            ax.text(scan, case, f"S {s:+.3f}\nD {d:+.3f}\nΔ {difference:+.3f}",
                    ha="center", va="center", fontsize=9,
                    color="black" if light > .55 else "white")
    color = fig.colorbar(image, ax=ax, fraction=.046, pad=.025)
    color.set_label("Saved static − moving center mean\n(same static flank; normalized power)", fontsize=10)
    ax.set_title("Nine original gap references: static S and moving D on the same static background\n"
                 "Cell annotations: saved S, D and Δ = S − D · one historical visit", fontsize=11.5, pad=15)
    fig.text(.55, .025,
             "Fixed original first-midpoint reference ±64 channels · post-selected, descriptive comparison",
             ha="center", fontsize=9.5)
    fig.subplots_adjust(left=.34, right=.92, top=.90, bottom=.10)
    path = output / "STATIC_MOVING_SAME_BACKGROUND_MEANS.png"
    fig.savefig(path, dpi=130, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "JSON-only static context display",
                          "Description": "54saved cells with162saved mean annotations; no scientific recomputation"})
    plt.close(fig)
    return path, {"summary_cell_count": 54, "saved_mean_annotations": 162,
                  "symmetric_color_limits": [-limit, limit],
                  "delta_values_hidden_or_clipped": False,
                  "saved_mean_values_float64_sha256": hashlib.sha256(saved.tobytes()).hexdigest()}


def profiles_figure(output, profiles, offsets, order, cases):
    frequency = offsets[order]
    fig, axes = plt.subplots(3, 3, figsize=(15.4, 11.6), sharex=True, sharey=False)
    handles = None
    limits = []
    for ax, values, case in zip(axes.flat, profiles, cases):
        lower = min(0.0, float(np.min(values)))
        upper = max(0.0, float(np.max(values)))
        margin = max((upper - lower) * .08, .002)
        ylimits = [lower - margin, upper + margin]
        limits.append(ylimits)
        this_handles = []
        for scan in range(6):
            line, = ax.plot(frequency, values[scan, order], color=COLORS[scan],
                            linestyle=STYLES[scan], linewidth=1.05, label=SHORT[scan])
            this_handles.append(line)
        handles = this_handles
        ax.axhline(0, color="gray", linewidth=.65)
        ax.axvline(0, color="gray", linewidth=.65, linestyle=":")
        ax.set_xlim(float(frequency[0]), float(frequency[-1]))
        ax.set_ylim(*ylimits)
        ax.set_xticks((-150, -75, 0, 75, 150))
        ax.tick_params(labelsize=8.5)
        ax.grid(alpha=.18)
        ax.set_title(f"{case['short_label']} · original reference\n"
                     f"{case['reference_frequency_hz'] / 1e6:.6f} MHz · "
                     f"{case['original_drift_hz_s']:+.3f} Hz/s · w{case['original_width_channels']}",
                     fontsize=9, loc="left", pad=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean normalized power\nminus static flank", fontsize=9.5)
    for ax in axes[-1]:
        ax.set_xlabel("Frequency offset from original reference (Hz)", fontsize=9)
    extent = max(abs(float(frequency[0])), abs(float(frequency[-1])))
    fig.suptitle("Fixed physical frequency context: all six scans at each original reference\n"
                 "129 saved channels per scan · solid ON / dashed OFF · ascending frequency", fontsize=12, y=.99)
    fig.legend(handles, SHORT, ncol=6, loc="upper center", bbox_to_anchor=(.5, .943), fontsize=10)
    fig.text(.54, .022,
             f"Original first-midpoint reference ±{extent:.3f} Hz; this is not a fitted stationary-line center.\n"
             "Each case has its own y scale · no cross-case amplitude comparison · one post-selected historical visit",
             ha="center", fontsize=9.4)
    fig.subplots_adjust(left=.08, right=.98, bottom=.12, top=.855, hspace=.40, wspace=.24)
    path = output / "STATIC_PHYSICAL_FREQUENCY_PROFILES.png"
    fig.savefig(path, dpi=130, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "JSON-only static context display",
                          "Description": "All6966saved profile samples; frequency display sortedascending withoutrecentring"})
    plt.close(fig)
    return path, {"saved_profile_sample_count": int(profiles.size),
                  "case_count": 9, "scans_per_case": 6, "samples_per_scan": 129,
                  "native_negative_DF_reordered_for_ascending_display": True,
                  "display_channel_order_indices": order.tolist(),
                  "frequency_offset_range_hz": [float(frequency[0]), float(frequency[-1])],
                  "all_samples_retained_no_mask_or_recentering": True,
                  "per_case_y_limits": limits,
                  "cross_case_y_scale_shared": False,
                  "saved_profiles_float64_sha256": hashlib.sha256(profiles.tobytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement-dir", required=True, type=Path)
    parser.add_argument("--profiles-sha256", required=True)
    parser.add_argument("--execution-sha256", required=True)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.measurement_dir.resolve(), args.outdir.resolve()
    if output.exists():
        raise ValueError("Output directory must not already exist; no plotting rerun")
    pins, saved, profiles, offsets, order, labels, cases = load_contract(
        source, args.profiles_sha256, args.execution_sha256)
    output.mkdir(parents=True)
    files = [means_figure(output, saved, labels),
             profiles_figure(output, profiles, offsets, order, cases)]
    if pins != {name: digest(source / name) for name in pins}:
        raise ValueError("Saved scientific JSON changed during plotting")
    receipt = {"status": "COMPLETE_TWO_STATIC_CONTEXT_JSON_ONLY_FIGURES",
               "scope": __doc__, "input_JSON_sha256": pins,
               "input_JSON_byte_unchanged": True, "plot_script_sha256": digest(Path(__file__)),
               "scientific_measurements_or_optimization_rerun": False,
               "source_H5_or_NPZ_access": False, "new_peak_fit_recenter_or_mask": False,
               "qualified_OFF_veto_or_whole_track_absence_claim": False,
               "one_historical_visit": True, "cpu_cap_seconds": 6,
               "process_CPU_seconds_including_imports": time.process_time() - CPU_START,
               "wall_seconds": time.monotonic() - WALL_START,
               "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
               "cases": cases,
               "plots": [{"path": path.name, "sha256": digest(path),
                          "bytes": path.stat().st_size, **details} for path, details in files],
               "visual_QA": "Pending original-detail views of actual completedPNG files"}
    receipt_path = output / "PLOTTING_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"],
                      "process_CPU_seconds": receipt["process_CPU_seconds_including_imports"],
                      "plot_script_sha256": receipt["plot_script_sha256"],
                      "receipt_sha256": digest(receipt_path),
                      "plots": [path.name for path, _ in files]}))


if __name__ == "__main__":
    main()
