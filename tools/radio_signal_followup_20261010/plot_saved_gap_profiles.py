#!/usr/bin/env python3
"""Two publication figures from saved JSON only; no source or NPZ access.

Plots all54 saved six-scan profile means and all288 origin/paired-OFF
residual rows for the already selected nine fixed profiles. No selection,
optimization, residual recomputation, scientific classification or OFF veto.
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
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
SHORT = ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")
ONS = SCANS[::2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(folder):
    names = ("FIXED_TOP3_PROFILES.json", "DRIFT_TOP20.json", "EXECUTION_RECEIPT.json")
    pinned = {name: digest(folder / name) for name in names}
    profiles, top20, execution = [json.loads((folder / name).read_text()) for name in names]
    if execution["status"] != "COMPLETED_EIGHT_GAP_DRIFT_CORES_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY":
        raise ValueError("Gap execution is not complete")
    if execution["one_historical_visit"] is not True or execution["OFF_veto_applied"] is not False:
        raise ValueError("Expected one-visit descriptive profile contract")
    summary = execution["profile_summary"]
    if summary["profile_count"] != 9 or summary["all_rows_retained"] != 16:
        raise ValueError("Expected nine complete16-row profiles")
    if summary["shift_frequency_drift_width_optimization_applied"] is not False:
        raise ValueError("Fixed-profile contract changed")
    if summary["source_top20_sha256"] != pinned["DRIFT_TOP20.json"]:
        raise ValueError("Selected top20 JSON differs from execution pin")
    expected = [top20[origin][rank] for origin in ONS for rank in range(3)]
    if len(profiles) != 9 or [p["selected_track"] for p in profiles] != expected:
        raise ValueError("Saved profile selection differs from fixed top3 perON")
    means, paired, labels, cases = [], [], [], []
    for profile in profiles:
        track = profile["selected_track"]
        if profile["fixed_frequency_shift_channels"] != 0:
            raise ValueError("Fixed frequency shift must remain zero")
        if track["family"] != "gap_drift" or track["originating_role"] != "ON":
            raise ValueError("Expected saved ON-origin gap drift cases")
        if track["originating_scan"] not in ONS or track["display_rank"] not in (1, 2, 3):
            raise ValueError("Invalid saved selection label")
        if track["width_channels"] not in (1, 3):
            raise ValueError("Saved width outside existing contract")
        for key in ("reference_frequency_hz", "drift_hz_s"):
            if not math.isfinite(track[key]):
                raise ValueError("Non-finite saved label")
        rows = profile["scan_profiles"]
        if [row["scan_id"] for row in rows] != list(SCANS):
            raise ValueError("Saved profile must include allsix ordered scans")
        for row in rows:
            if len(row["all_16_center_minus_flank_rows"]) != 16:
                raise ValueError("Missing saved residual rows")
            values = [row["mean_center_minus_flank"], *row["all_16_center_minus_flank_rows"]]
            if not all(math.isfinite(value) for value in values):
                raise ValueError("Non-finite saved plot value")
        origin_index = SCANS.index(track["originating_scan"])
        means.append([row["mean_center_minus_flank"] for row in rows])
        paired.append([rows[origin_index]["all_16_center_minus_flank_rows"],
                       rows[origin_index + 1]["all_16_center_minus_flank_rows"]])
        name = f"{SHORT[origin_index]} r{track['display_rank']}"
        detail = (f"{track['reference_frequency_hz'] / 1e6:.6f} MHz · "
                  f"{track['drift_hz_s']:+.6f} Hz/s · w{track['width_channels']}")
        labels.append(name + "\n" + detail)
        cases.append({"track_id": track["track_id"], "short_label": name,
                      "origin_scan": SCANS[origin_index],
                      "paired_OFF_scan": SCANS[origin_index + 1],
                      "reference_frequency_hz": track["reference_frequency_hz"],
                      "drift_hz_s": track["drift_hz_s"],
                      "width_channels": track["width_channels"]})
    return pinned, np.asarray(means), np.asarray(paired), labels, cases


def plot_means(out, means, labels):
    limit = max(float(np.max(np.abs(means))) * 1.08, 1e-9)
    fig, ax = plt.subplots(figsize=(14.4, 10.8))
    im = ax.imshow(means, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(6), SHORT, fontsize=11)
    ax.set_yticks(range(9), labels, fontsize=9)
    ax.set_xlabel("Scan evaluated along the same fixed selected path", fontsize=11, labelpad=12)
    for row in range(9):
        for col in range(6):
            rgba = im.cmap(im.norm(means[row, col]))
            luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
            ax.text(col, row, f"{means[row, col]:+.3f}", ha="center", va="center",
                    fontsize=10, color="black" if luminance > .55 else "white")
    color = fig.colorbar(im, ax=ax, fraction=.046, pad=.025)
    color.set_label("Saved mean center minus fixed flank\n(row-normalized power)", fontsize=10)
    ax.set_title("Gap drift: fixed profile means across all six scans\n"
                 "Selected top3 perON · one historical visit · descriptive", fontsize=12, pad=17)
    fig.text(.54, .025, "Fixed shift0 · post-selection display · no qualified OFF veto",
             ha="center", fontsize=10)
    fig.subplots_adjust(left=.34, right=.91, top=.90, bottom=.10)
    path = out / "GAP_FIXED_PROFILE_MEANS.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Saved JSON gap-profile renderer",
                          "Description": "54unchanged saved profile means; visual display only"})
    plt.close(fig)
    return path, {"symmetric_color_limits": [-limit, limit],
                  "saved_mean_count_displayed": 54,
                  "saved_means_float64_sha256": hashlib.sha256(means.tobytes()).hexdigest()}


def plot_rows(out, paired, cases):
    lower = min(0.0, float(np.min(paired)))
    upper = max(0.0, float(np.max(paired)))
    margin = max((upper - lower) * .08, .005)
    limits = [lower - margin, upper + margin]
    fig, axes = plt.subplots(3, 3, figsize=(15, 10.8), sharex=True, sharey=True)
    handles = None
    for index, (ax, values, case) in enumerate(zip(axes.flat, paired, cases)):
        on, = ax.plot(range(16), values[0], color="#1565a8", marker="o", markersize=3,
                      linewidth=1.1, label="Origin ON")
        off, = ax.plot(range(16), values[1], color="#af591f", marker="o", markersize=3,
                       linewidth=1.1, label="Paired OFF")
        handles = (on, off)
        ax.axhline(0, color="gray", linewidth=.65)
        ax.set_ylim(*limits)
        ax.set_xlim(-.4, 15.4)
        ax.set_xticks((0, 4, 8, 12, 15))
        ax.tick_params(labelsize=9)
        pair_name = SHORT[SCANS.index(case["paired_OFF_scan"])]
        ax.set_title(f"{case['short_label']} · paired {pair_name}\n"
                     f"{case['reference_frequency_hz'] / 1e6:.6f} MHz · "
                     f"{case['drift_hz_s']:+.3f} Hz/s · w{case['width_channels']}",
                     fontsize=9, loc="left", pad=9)
        ax.grid(alpha=.2)
        if index % 3 == 0:
            ax.set_ylabel("Center minus fixed flank\n(row-normalized power)", fontsize=10)
        if index >= 6:
            ax.set_xlabel("Saved time row (each scan)", fontsize=10)
    fig.suptitle("Gap drift: all16 saved rows in origin ON and paired OFF\n"
                 "Nine post-selected fixed profiles · one historical visit", fontsize=12, y=.985)
    fig.legend(handles, ("Origin ON", "Paired OFF"), ncol=2, loc="upper center",
               bbox_to_anchor=(.5, .935), fontsize=10)
    fig.text(.53, .018, "Each scan has its own row sequence · common y scale · descriptive comparison",
             ha="center", fontsize=10)
    fig.subplots_adjust(left=.08, right=.98, bottom=.10, top=.86, hspace=.42, wspace=.17)
    path = out / "GAP_ORIGIN_PAIRED_OFF_ROWS.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Saved JSON gap-profile renderer",
                          "Description": "288unchanged saved residual rows; no source decoding or scientific processing"})
    plt.close(fig)
    return path, {"common_y_limits_all_nine_panels": limits,
                  "saved_residual_rows_displayed": 288,
                  "saved_paired_rows_float64_sha256": hashlib.sha256(paired.tobytes()).hexdigest(),
                  "time_axis": "Saved row index0..15; each scan's own sequence, no inferred physical times"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement-dir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.measurement_dir.resolve(), args.outdir.resolve()
    if output.exists():
        raise ValueError("Output directory must not already exist; no plotting rerun")
    pinned, means, paired, labels, cases = load_contract(source)
    output.mkdir(parents=True)
    paths = [plot_means(output, means, labels), plot_rows(output, paired, cases)]
    if pinned != {name: digest(source / name) for name in pinned}:
        raise ValueError("A saved scientific JSON changed during plotting")
    receipt = {"status": "COMPLETE_TWO_SAVED_JSON_PUBLICATION_FIGURES",
               "scope": __doc__, "input_json_sha256": pinned,
               "script_sha256": digest(Path(__file__)), "input_json_byte_unchanged": True,
               "scientific_rerun_or_residual_recomputation": False,
               "source_H5_or_NPZ_access": False, "new_optimization_or_classification": False,
               "qualified_OFF_veto": False, "one_historical_visit": True,
               "case_count": 9, "scan_mean_count": 54, "paired_residual_row_count": 288,
               "cases": cases, "matplotlib_version": matplotlib.__version__,
               "numpy_version": np.__version__, "cpu_cap_seconds": 10,
               "process_CPU_seconds_including_imports": time.process_time() - CPU_START,
               "wall_seconds": time.monotonic() - WALL_START,
               "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               "plots": [{"path": path.name, "sha256": digest(path),
                          "bytes": path.stat().st_size, **details} for path, details in paths],
               "visual_QA": "Pending actual PNG original-detail inspection"}
    receipt_path = output / "PLOTTING_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"],
                      "process_CPU_seconds": receipt["process_CPU_seconds_including_imports"],
                      "script_sha256": receipt["script_sha256"],
                      "receipt_sha256": digest(receipt_path),
                      "plots": [path.name for path, _ in paths]}))


if __name__ == "__main__":
    main()
