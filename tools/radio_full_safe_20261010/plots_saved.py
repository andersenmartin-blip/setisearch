#!/usr/bin/env python3
"""Two figures from pinned saved JSON only, after explicit root authorization.

Coverage uses receipt metadata, and the heatmap uses the unchanged saved six-scan
fixed-profile means. No HDF5/NPZ access, residual calculation, optimization,
global reranking, scientific classification, or qualified OFF veto.

The --pins JSON is an exact mapping of root-relative input paths to SHA256s.
It must pin the activation scope, final executable scope, and all batch JSONs
actually opened. BOTH_COMPLETE requires both complete nine-profile batches.
PARTIAL, authorized separately by the parent, displays exact completed tile
metadata and only profiles from batches whose full completion contract passes.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

WALL_START = time.monotonic()
CPU_CAP = 60
MEMORY_CAP = 4 * 1024**3
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP))
resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
SHORT = ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")
ONS = SCANS[::2]
STAGE = "results/radio_full_safe_20261010"
ACTIVATION = "tools/radio_full_safe_20261010/ACTIVATION_SCOPE.json"
SUCCESS = "COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PinnedJSON:
    def __init__(self, root, pins_path):
        self.root = root.resolve()
        self.pins_path = pins_path.resolve()
        self.pins_sha = digest(self.pins_path)
        self.pins = json.loads(self.pins_path.read_text())
        if not isinstance(self.pins, dict) or not self.pins:
            raise ValueError("Pins must be a nonempty root-relative path -> SHA256 mapping")
        self.opened = {}
        for name, expected in self.pins.items():
            path = self.root / name
            if (Path(name).is_absolute() or ".." in Path(name).parts
                    or path.suffix != ".json" or len(expected) != 64
                    or any(c not in "0123456789abcdef" for c in expected)):
                raise ValueError("Invalid JSON pin mapping")

    def present(self, name):
        return name in self.pins

    def load(self, name):
        if name not in self.pins:
            raise ValueError(f"Missing explicit input pin: {name}")
        path = self.root / name
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != self.pins[name]:
            raise ValueError(f"Input SHA256 mismatch: {name}")
        self.opened[name] = {"sha256": actual, "bytes": len(raw)}
        return json.loads(raw)

    def verify_unchanged(self):
        if digest(self.pins_path) != self.pins_sha:
            raise ValueError("Input-pin file changed during plotting")
        for name, item in self.opened.items():
            if digest(self.root / name) != item["sha256"]:
                raise ValueError(f"Saved scientific JSON changed during plotting: {name}")


def exact_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected integer {label}")
    return value


def unique_q(values, label, expected_count):
    if not isinstance(values, list) or len(values) != expected_count:
        raise ValueError(f"Incorrect scoped {label} count")
    if any(exact_int(q, label) < 1 or q > 254 for q in values):
        raise ValueError(f"Unsafe scoped {label} core")
    if len(set(values)) != len(values) or values != sorted(values):
        raise ValueError(f"Scoped {label} must contain unique ascending cores")
    return set(values)


def activation_geometry(activation):
    s = activation["immutable_metadata_selection"]
    if (s["source_chunk_channel_count"] != 1048576
            or s["core_channel_count"] != 4096
            or s["safe_q_interval_inclusive"] != [1, 254]):
        raise ValueError("Native-chunk coverage geometry changed")
    interval = s["source_channel_interval_half_open"]
    if len(interval) != 2 or interval[1] - interval[0] != 1048576:
        raise ValueError("Invalid native source-channel interval")
    prior = unique_q(s["prior_q"], "prior", 32)
    gap = unique_q(s["previous_gap_q"], "previous_gap", 8)
    batches = [unique_q(values, f"batch_{i + 1:02d}", 107)
               for i, values in enumerate(s["batch_q"])]
    if len(batches) != 2:
        raise ValueError("Expected exactly two new batches")
    groups = [prior, gap, *batches]
    if any(a & b for i, a in enumerate(groups) for b in groups[i + 1:]):
        raise ValueError("Prospective core sets overlap")
    if set.union(*groups) != set(range(1, 255)):
        raise ValueError("Prospective core sets do not partition all safe interior cores")
    return {"old": prior | gap, "prior": prior, "gap": gap,
            "batches": batches, "source_first": interval[0], "core_size": 4096,
            "native_core_count": 256, "source_interval": interval}


def load_checkpoint(data, batch_id, geometry):
    if exact_int(data["batch_id"], "batch_id") != batch_id:
        raise ValueError("Checkpoint batch identity mismatch")
    if data["expected_scan_tiles"] != 321:
        raise ValueError("Checkpoint expected-tile count changed")
    entries = data["completed_receipts"]
    if data["completed_scan_tiles"] != len(entries):
        raise ValueError("Checkpoint completed-tile count mismatch")
    result = {scan: set() for scan in ONS}
    scoped = geometry["batches"][batch_id - 1]
    ordered_q = sorted(scoped)
    if data["fixed_batch_q"] != ordered_q:
        raise ValueError("Checkpoint scoped core list differs from immutable batch selection")
    for entry in entries:
        scan = entry["scan_id"]
        q = exact_int(entry["reference_core_q"], "reference_core_q")
        if scan not in ONS or q not in scoped or q in result[scan]:
            raise ValueError("Invalid or duplicate completed scan/core receipt")
        if entry["tile_index"] != ordered_q.index(q):
            raise ValueError("Receipt tile index differs from fixed scoped ordering")
        start = geometry["source_first"] + q * 4096
        if (entry["core_start_relative_channel"] != q * 4096
                or entry["reference_channel_interval_half_open"] != [start, start + 4096]
                or entry["searched_carriers"] != 4096
                or entry["valid_hypotheses_per_carrier"] != 1526):
            raise ValueError("Completed receipt has an incomplete carrier/grid contract")
        result[scan].add(q)
    full = all(result[scan] == scoped for scan in ONS)
    if data["complete"] is not full:
        raise ValueError("Checkpoint completeness flag differs from actual core receipts")
    return result, full


def load_profiles(profiles, top20, execution, batch_id, geometry, inputs, prefix):
    summary = execution["fixed_profile_summary"]
    if (execution["one_historical_visit"] is not True
            or execution["OFF_veto_applied"] is not False
            or execution["qualified_sky_pilot"] is not False
            or execution["calibrated_SNR_FAP_flux_EIRP_or_sensitivity"] is not False):
        raise ValueError("Scientific limitation flags changed")
    if (summary["profile_count"] != 9 or summary["all_rows_retained"] != 16
            or summary["shift_frequency_drift_width_optimization_applied"] is not False
            or summary["source_top20_sha256"] != inputs.pins[prefix + "DRIFT_TOP20.json"]):
        raise ValueError("Fixed-profile provenance/completeness contract changed")
    if set(top20) != set(ONS) or any(len(top20[scan]) != 20 for scan in ONS):
        raise ValueError("Expected all three saved top20 lists within each completed batch")
    expected = [top20[scan][rank] for scan in ONS for rank in range(3)]
    for index, track in enumerate(expected):
        if (track["originating_scan"] != ONS[index // 3]
                or exact_int(track["display_rank"], "display_rank") != index % 3 + 1):
            raise ValueError("Saved top3 must retain ranks1/2/3 within its actual originating ON")
    if (len(profiles) != 9
            or [record["selected_track"] for record in profiles] != expected):
        raise ValueError("Profiles differ from saved top3 perON within this batch")
    cases, means, labels = [], [], []
    seen = set()
    for record in profiles:
        track = record["selected_track"]
        if (exact_int(track["batch_id"], "selected_track.batch_id") != batch_id
                or track["track_id"] in seen
                or track["family"] != "gap_drift"
                or track["originating_role"] != "ON"
                or track["originating_scan"] not in ONS
                or track["display_rank"] not in (1, 2, 3)
                or track["width_channels"] not in (1, 3)
                or exact_int(track["reference_core_q"], "selected_track.reference_core_q")
                    not in geometry["batches"][batch_id - 1]
                or record["fixed_frequency_shift_channels"] != 0):
            raise ValueError("Saved fixed-track identity/geometry contract changed")
        seen.add(track["track_id"])
        if any(not math.isfinite(track[key]) for key in ("reference_frequency_hz", "drift_hz_s")):
            raise ValueError("Nonfinite saved track label")
        q = track["reference_core_q"]
        channel = exact_int(track["source_reference_channel"], "source_reference_channel")
        first = geometry["source_first"] + q * 4096
        if not first <= channel < first + 4096:
            raise ValueError("Selected reference channel lies outside its scoped core")
        rows = record["scan_profiles"]
        if [row["scan_id"] for row in rows] != list(SCANS):
            raise ValueError("Expected all six unchanged ordered scan profiles")
        for row in rows:
            values = row["all_16_center_minus_flank_rows"]
            if len(values) != 16 or not all(math.isfinite(v) for v in values):
                raise ValueError("Missing/nonfinite saved 16-row profile")
            if not math.isfinite(row["mean_center_minus_flank"]):
                raise ValueError("Nonfinite saved scan mean")
        origin = SHORT[SCANS.index(track["originating_scan"])]
        short = f"B{batch_id:02d} {origin} r{track['display_rank']}"
        detail = (f"{track['reference_frequency_hz'] / 1e6:.6f} MHz · "
                  f"{track['drift_hz_s']:+.6f} Hz/s · w{track['width_channels']} · q{q}")
        labels.append(short + "\n" + detail)
        means.append([row["mean_center_minus_flank"] for row in rows])
        cases.append({"batch_id": batch_id, "track_id": track["track_id"],
                      "short_label": short, "originating_scan": track["originating_scan"],
                      "display_rank_within_batch_ON": track["display_rank"],
                      "reference_core_q": q, "source_reference_channel": channel,
                      "reference_frequency_hz": track["reference_frequency_hz"],
                      "drift_hz_s": track["drift_hz_s"],
                      "width_channels": track["width_channels"]})
    return cases, means, labels


def load_batches(inputs, geometry, success_status, disposition, scope_name):
    coverage, batch_summary, cases, means, labels = [], [], [], [], []
    for batch_id in (1, 2):
        prefix = f"{STAGE}/batch_{batch_id:02d}/measurement/"
        ck_name = prefix + "DRIFT_CHECKPOINT.json"
        actual = {scan: set() for scan in ONS}
        complete = False
        status = "NO_CHECKPOINT_PINNED"
        if inputs.present(ck_name):
            actual, full = load_checkpoint(inputs.load(ck_name), batch_id, geometry)
            execution_name = prefix + "EXECUTION_RECEIPT.json"
            if inputs.present(execution_name):
                execution = inputs.load(execution_name)
                if (exact_int(execution["batch_id"], "execution.batch_id") != batch_id
                        or execution["fixed_batch_q"] != sorted(geometry["batches"][batch_id - 1])):
                    raise ValueError("Execution batch identity mismatch")
                status = execution["status"]
                complete = full and status == success_status
                if status == success_status and not full:
                    raise ValueError("Successful execution lacks all completed core receipts")
                if complete:
                    if execution["scope_sha256"] != inputs.pins[scope_name]:
                        raise ValueError("Execution uses a different final scientific scope")
                    new_cases, new_means, new_labels = load_profiles(
                        inputs.load(prefix + "FIXED_TOP3_PROFILES.json"),
                        inputs.load(prefix + "DRIFT_TOP20.json"), execution,
                        batch_id, geometry, inputs, prefix)
                    cases.extend(new_cases)
                    means.extend(new_means)
                    labels.extend(new_labels)
            else:
                status = "CHECKPOINT_ONLY_FULL" if full else "CHECKPOINT_ONLY_PARTIAL"
                failure_name = prefix + "FAILURE_RECEIPT.json"
                if inputs.present(failure_name):
                    failure = inputs.load(failure_name)
                    if (exact_int(failure["batch_id"], "failure.batch_id") != batch_id
                            or failure["fixed_batch_q"] != sorted(geometry["batches"][batch_id - 1])):
                        raise ValueError("Failure receipt batch identity/scope mismatch")
                    status = failure["status"]
        if disposition == "BOTH_COMPLETE" and not complete:
            raise ValueError(f"BOTH_COMPLETE requires the exact successful batch_{batch_id:02d} contract")
        coverage.append(actual)
        batch_summary.append({"batch_id": batch_id, "receipt_status": status,
                              "complete_numerical_and_profile_contract": complete,
                              "completed_core_q_by_ON": {s: sorted(actual[s]) for s in ONS},
                              "expected_cores_per_ON": 107,
                              "profiles_displayed": 9 if complete else 0})
    if not cases:
        raise ValueError("No completed batch fixed-profile contract; obtain a separate partial plotting decision")
    return coverage, batch_summary, cases, np.asarray(means, dtype=np.float64), labels


def plot_coverage(output, geometry, coverage, batch_summary, disposition):
    # State0=excluded edge,1=prior40,2=batch01 done,3=batch02 done,4=not completed.
    raster = np.full((3, 256), 4, dtype=np.int8)
    raster[:, [0, 255]] = 0
    for row, scan in enumerate(ONS):
        raster[row, sorted(geometry["old"])] = 1
        for batch_index in (0, 1):
            raster[row, sorted(coverage[batch_index][scan])] = batch_index + 2
    colors = ["#292f36", "#929da7", "#197fa3", "#cf7b27", "#f0f0f0"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-.5, 5.5), cmap.N)
    fig, ax = plt.subplots(figsize=(14.5, 6.4))
    ax.imshow(raster, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest",
              extent=(-.5, 255.5, 2.5, -.5))
    counts = []
    ylabels = []
    for scan in ONS:
        new = coverage[0][scan] | coverage[1][scan]
        total = geometry["old"] | new
        count = len(total)
        counts.append({"scan_id": scan, "prior_cores": 40,
                       "new_completed_cores": len(new), "total_reference_cores": count,
                       "reference_channels": count * 4096,
                       "native_chunk_fraction": count / 256,
                       "all_safe_core_coverage_complete": count == 254})
        label = SHORT[SCANS.index(scan)]
        ylabels.append(f"{label}\n{count}/256 cores ({count / 256:.5%})")
    ax.set_yticks(range(3), ylabels, fontsize=10)
    ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
    ax.set_xlabel("Reference core q (4096 native channels per core)", fontsize=11, labelpad=10)
    ax.set_xlim(-.5, 255.5)
    ax.set_ylim(2.5, -.5)
    ax.axvline(127.5, color="black", linewidth=.6, alpha=.45)
    ax.set_title("Full safe-core drift stage: exact reference-carrier coverage\n"
                 "Receipt-completed new cores plus the previously completed 40 cores", fontsize=13, pad=17)
    legends = [Patch(facecolor=c, edgecolor="#555555", linewidth=.5, label=l)
               for c, l in zip(colors, ("Excluded edge cores", "Prior 32 + gap 8",
                                        "Batch 01 completed", "Batch 02 completed",
                                        "Scoped, no completed receipt"))]
    fig.legend(handles=legends, loc="upper center", bbox_to_anchor=(.55, .855),
               ncol=3, frameon=False, fontsize=9)
    batch_lines = [f"B{item['batch_id']:02d}: " + ", ".join(
        f"{SHORT[SCANS.index(scan)]} {len(coverage[item['batch_id'] - 1][scan])}/107"
        for scan in ONS) + (" · complete" if item["complete_numerical_and_profile_contract"]
                           else " · completion contract not met")
        for item in batch_summary]
    fig.text(.55, .145, "\n".join(batch_lines), ha="center", va="center", fontsize=10)
    fig.text(.55, .055,
             "Target: 254/256 cores = 99.21875% of this native chunk for the fixed grid and widths1/3.\n"
             "One historical visit · reference-carrier coverage is not survey or sensitivity completeness.\n"
             "Two edge cores excluded · trajectory/read halos may overlap · "
             + ("both batches complete" if disposition == "BOTH_COMPLETE" else "explicit partial-result display"),
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.20, right=.98, top=.70, bottom=.255)
    path = output / "FULL_SAFE_COVERAGE.png"
    fig.savefig(path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned saved JSON full-safe renderer",
                          "Description": "Administrative completed-core receipt coverage only"})
    plt.close(fig)
    return path, {"coverage_by_ON": counts,
                  "raster_int8_sha256": hashlib.sha256(raster.tobytes()).hexdigest(),
                  "prior_coverage_basis": "Pinned activation scope prior32 and previously completed gap8",
                  "new_coverage_basis": "Exact checkpoint completed_receipts scan_id/reference_core_q only",
                  "coverage_denominator": 256, "core_channel_count": 4096}


def plot_means(output, means, labels, cases, disposition):
    n = len(cases)
    limit = max(float(np.max(np.abs(means))) * 1.05, 1e-9)
    fig, ax = plt.subplots(figsize=(14.6, max(10.2, .62 * n + 3.1)))
    im = ax.imshow(means, cmap="RdBu_r", vmin=-limit, vmax=limit,
                   interpolation="nearest", aspect="auto")
    ax.set_xticks(range(6), SHORT, fontsize=11)
    ax.set_yticks(range(n), labels, fontsize=9)
    ax.set_xlabel("Scan evaluated on the same saved fixed path (all six scans)",
                  fontsize=10, labelpad=12)
    ax.set_xlim(-.5, 5.5)
    ax.set_ylim(n - .5, -.5)
    for row in range(n):
        if row and cases[row]["batch_id"] != cases[row - 1]["batch_id"]:
            ax.axhline(row - .5, color="#333333", linewidth=1.6, linestyle="--")
        for col in range(6):
            rgba = im.cmap(im.norm(means[row, col]))
            luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
            ax.text(col, row, f"{means[row, col]:+.3f}", ha="center", va="center",
                    fontsize=10, color="black" if luminance > .55 else "white")
    color = fig.colorbar(im, ax=ax, fraction=.038, pad=.028)
    color.set_label("Saved mean center minus fixed flank\n(row-normalized power; not SNR)",
                    fontsize=10, labelpad=11)
    title = "Full safe-core stage: saved fixed-profile means across all six scans"
    subtitle = (f"{n} selected paths · top3 perON within each completed batch · "
                "one historical visit")
    ax.set_title(title + "\n" + subtitle, fontsize=12, pad=17)
    fig.text(.56, .030,
             "Batch-specific display ranks · no cross-batch reranking · fixed shift0 · post-selection description.\n"
             "All six exact-path means retained; adjacent OFF controls are described in the report/JSON.\n"
             "No qualified OFF veto or origin classification; small exact-path OFF means do not rule out nearby features."
             + ("\nPartial result: only batches with complete saved profile contracts are shown."
                if disposition == "PARTIAL" else ""),
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.36, right=.90, top=.905, bottom=.105)
    path = output / "FULL_SAFE_FIXED_PROFILE_MEANS.png"
    fig.savefig(path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned saved JSON full-safe renderer",
                          "Description": "Unchanged saved six-scan means; no numerical processing or ranking"})
    plt.close(fig)
    return path, {"symmetric_color_limits": [-limit, limit],
                  "actual_minimum_saved_mean": float(np.min(means)),
                  "actual_maximum_saved_mean": float(np.max(means)),
                  "all_actual_saved_means_inside_color_limits": bool(np.all(np.abs(means) < limit)),
                  "saved_mean_count_displayed": int(means.size),
                  "saved_means_float64_sha256": hashlib.sha256(means.tobytes()).hexdigest(),
                  "selection": "Unchanged saved top3 perON separately within each completed batch",
                  "cross_batch_reranking": False, "profile_NPZ_read": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--pins", required=True, type=Path)
    parser.add_argument("--final-scope", required=True,
                        help="Root-relative final executable scope JSON path, pinned in --pins")
    parser.add_argument("--success-status", default=SUCCESS, choices=(SUCCESS,),
                        help="Exact final batch execution success status from the frozen implementation")
    parser.add_argument("--authorized-disposition", required=True,
                        choices=("BOTH_COMPLETE", "PARTIAL"))
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.outdir or root / STAGE / "figures").resolve()
    if output.exists():
        raise ValueError("Output directory already exists: preserve figures; no automatic rerun")
    inputs = PinnedJSON(root, args.pins)
    activation = inputs.load(ACTIVATION)
    geometry = activation_geometry(activation)
    # The final executable scope is pinned/read for byte identity and provenance.
    # Its numerical outcome values are neither calculated nor opened here.
    final_scope = inputs.load(args.final_scope)
    if final_scope["immutable_metadata_selection"] != activation["immutable_metadata_selection"]:
        raise ValueError("Final executable scope changed the prospective activation core selections")
    coverage, batch_summary, cases, means, labels = load_batches(
        inputs, geometry, args.success_status, args.authorized_disposition, args.final_scope)
    inputs.verify_unchanged()
    output.mkdir(parents=True, exist_ok=False)
    paths = [plot_coverage(output, geometry, coverage, batch_summary, args.authorized_disposition),
             plot_means(output, means, labels, cases, args.authorized_disposition)]
    inputs.verify_unchanged()
    cpu = time.process_time()
    cap_pass = cpu <= CPU_CAP
    receipt = {
        "schema": "SETI_FULL_SAFE_SAVED_JSON_PLOTTING_V1",
        "status": ("COMPLETE_TWO_SAVED_JSON_PUBLICATION_FIGURES" if cap_pass else
                   "COMPLETE_TWO_FIGURES_PLOTTING_CPU_CAP_EXCEEDED_NO_RETRY"),
        "authorized_disposition": args.authorized_disposition,
        "script_sha256": digest(Path(__file__)),
        "input_pins_sha256": inputs.pins_sha, "input_json": inputs.opened,
        "input_json_byte_unchanged": True,
        "final_scientific_scope_path": args.final_scope,
        "final_scientific_scope_sha256": inputs.pins[args.final_scope],
        "scientific_rerun_or_residual_recomputation": False,
        "source_H5_or_NPZ_access": False, "new_optimization_or_classification": False,
        "cross_batch_reranking": False, "qualified_OFF_veto": False,
        "one_historical_visit": True, "blind_validation": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "case_count": len(cases), "scan_mean_count": int(means.size),
        "batch_summary": batch_summary, "cases": cases,
        "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
        "process_CPU_seconds_including_imports": cpu,
        "cpu_cap_seconds": CPU_CAP, "measured_CPU_within_cap": cap_pass,
        "CPU_excess_seconds": max(0.0, cpu - CPU_CAP),
        "OS_RLIMIT_CPU_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
        "wall_seconds": time.monotonic() - WALL_START,
        "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "plots": [{"path": path.name, "sha256": digest(path),
                   "bytes": path.stat().st_size, **details} for path, details in paths],
        "visual_QA": "Pending separate actual-PNG original-detail inspection receipt",
        "limitations": [
            "Coverage counts reference carriers of one native chunk for the fixed grid/widths, not survey/sensitivity completeness",
            "Old and new reference-core selections are disjoint, while read/trajectory halos can overlap",
            "All scans belong to one historical visit; scan labels are not independent visits",
            "Post-selection means are descriptive; small fixed-path OFF values do not establish absence of nearby OFF features",
            "No global ranking, qualified OFF veto, origin classification, probability or general null claim"],
    }
    receipt_path = output / "PLOTTING_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "case_count": len(cases),
                      "process_CPU_seconds": cpu, "measured_CPU_within_cap": cap_pass,
                      "receipt_sha256": digest(receipt_path),
                      "script_sha256": receipt["script_sha256"],
                      "plots": [item["path"] for item in receipt["plots"]]}))


if __name__ == "__main__":
    main()
