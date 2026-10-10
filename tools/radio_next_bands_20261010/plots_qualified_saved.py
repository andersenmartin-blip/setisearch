#!/usr/bin/env python3
"""Two saved-output verification figures after prospective scope and root GO.

Coverage uses receipt metadata, and the heatmap uses the unchanged saved six-scan
fixed-profile means. No HDF5/NPZ access, residual calculation, optimization,
global reranking, scientific classification, or qualified OFF veto.

The --pins JSON is an exact mapping of root-relative input paths to SHA256s.
The frozen original renderer is preserved. Three original resource failures
remain failures; one original numerical completion remains a completion.
Admission requires separate exact saved-output verification/acceptance receipts
and QA pins under the public acceptance scope. No original status is rewritten.
All four saved-output admissions are required. This is saved-output verification,
not sky-pilot qualification or resource compliance of the original failed jobs.
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
CHUNKS = (153, 154)
STAGE = "results/radio_next_bands_20261010"
ACTIVATION = "tools/radio_next_bands_20261010/ACTIVATION_SCOPE.json"
SCOPE = "tools/radio_next_bands_20261010/scope.json"
SCOPE_SHA256 = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
NUMERIC_FREEZE_COMMIT = "d1bfe755e205e99b3c93544f4af84cc8d4585938"
RECOVERY_FREEZE_COMMIT = "8f88b722c9508d4e209c3df540407029b80c3203"
ORIGINAL_PLOT = "tools/radio_next_bands_20261010/plots_saved.py"
ORIGINAL_PLOT_SHA256 = "044dd2b5ee3d89f127abb6508bc8c4383a087b64ae27da716f85e99a96ddbd6d"
ACCEPTANCE_SCOPE = "tools/radio_next_bands_20261010/SAVED_OUTPUT_ACCEPTANCE_SCOPE.json"
SUCCESS = "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
FAILURE = "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
ACCEPTED_FAILURE = "SAVED_OUTPUT_VERIFIED_ORIGINAL_RESOURCE_FAILURE"
ACCEPTED_COMPLETE = "SAVED_OUTPUT_VERIFIED_ORIGINAL_COMPLETE"
QA_FAILURE = "PASS_COMPLETE_SAVED_OUTPUTS_WITH_ORIGINAL_CPU_CAP_EXCEEDED"
QA_COMPLETE = "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"


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

    def pin_only(self, name):
        if name not in self.pins:
            raise ValueError(f"Missing explicit JSON pin: {name}")
        path = self.root / name
        actual = digest(path)
        if actual != self.pins[name]:
            raise ValueError(f"Input SHA256 mismatch: {name}")
        self.opened[name] = {"sha256": actual, "bytes": path.stat().st_size,
                             "read_mode": "SHA256 only; no JSON value decoding"}

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
    if (s["native_chunk_indices"] != list(CHUNKS)
            or s["core_channels"] != 4096
            or s["full_safe_q_ascending"] != list(range(1, 255))
            or s["scan_order"] != list(SCANS)):
        raise ValueError("Native-chunk coverage geometry changed")
    intervals = s["physical_chunk_intervals_half_open"]
    expected_intervals = [[c * 1048576, (c + 1) * 1048576] for c in CHUNKS]
    if intervals != expected_intervals:
        raise ValueError("Invalid native source-channel intervals")
    batches = [unique_q(values, f"batch_{i + 1:02d}", 127)
               for i, values in enumerate(s["batch_q"])]
    if len(batches) != 2:
        raise ValueError("Expected exactly two new batches")
    if batches[0] & batches[1]:
        raise ValueError("Prospective core sets overlap")
    if set.union(*batches) != set(range(1, 255)):
        raise ValueError("Prospective core sets do not partition all safe interior cores")
    return {"batches": batches, "core_size": 4096, "native_core_count": 256,
            "source_first_by_chunk": {chunk: interval[0] for chunk, interval in zip(CHUNKS, intervals)},
            "source_intervals_by_chunk": dict(zip(CHUNKS, intervals))}


def load_checkpoint(data, chunk_id, batch_id, geometry):
    if (exact_int(data["source_chunk_id"], "source_chunk_id") != chunk_id
            or exact_int(data["batch_id"], "batch_id") != batch_id):
        raise ValueError("Checkpoint chunk/batch identity mismatch")
    if data["expected_scan_tiles"] != 381:
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
        start = geometry["source_first_by_chunk"][chunk_id] + q * 4096
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


def load_profiles(profiles, top20, admission, chunk_id, batch_id, geometry):
    if set(top20) != set(ONS) or any(len(top20[scan]) != 20 for scan in ONS):
        raise ValueError("Expected all three original saved top20 lists within each batch")
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
        if (exact_int(track["source_chunk_id"], "selected_track.source_chunk_id") != chunk_id
                or exact_int(track["batch_id"], "selected_track.batch_id") != batch_id
                or track["track_id"] in seen
                or track["family"] != "native_chunk_drift"
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
        first = geometry["source_first_by_chunk"][chunk_id] + q * 4096
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
        short = (f"C{chunk_id} B{batch_id:02d} {origin} r{track['display_rank']} · "
                 f"original {admission['original_display_status']} / saved verified")
        detail = (f"{track['reference_frequency_hz'] / 1e6:.6f} MHz · "
                  f"{track['drift_hz_s']:+.6f} Hz/s · w{track['width_channels']} · q{q}")
        labels.append(short + "\n" + detail)
        means.append([row["mean_center_minus_flank"] for row in rows])
        cases.append({"source_chunk_id": chunk_id, "batch_id": batch_id, "track_id": track["track_id"],
                      "short_label": short, "originating_scan": track["originating_scan"],
                      "display_rank_within_batch_ON": track["display_rank"],
                      "reference_core_q": q, "source_reference_channel": channel,
                      "reference_frequency_hz": track["reference_frequency_hz"],
                      "drift_hz_s": track["drift_hz_s"],
                      "width_channels": track["width_channels"]})
        cases[-1].update({"original_numeric_job_status": admission["original_numeric_job_status"],
                         "original_display_status": admission["original_display_status"],
                         "saved_output_acceptance_status": admission["acceptance_status"],
                         "saved_output_QA_status": admission["QA_status"]})
    return cases, means, labels


def load_batches(inputs, geometry, acceptance_scope, acceptance_scope_sha256):
    coverage = {chunk: [] for chunk in CHUNKS}
    batch_summary, cases, means, labels = [], [], [], []
    for chunk_id, batch_id in ((c, b) for c in CHUNKS for b in (1, 2)):
        prefix = f"{STAGE}/chunk{chunk_id}/batch_{batch_id:02d}/measurement/"
        acceptance_dir = f"{STAGE}/acceptance/chunk{chunk_id}/batch_{batch_id:02d}"
        acceptance_name = acceptance_dir + "/SAVED_OUTPUT_ACCEPTANCE_RECEIPT.json"
        admission = inputs.load(acceptance_name)
        if (exact_int(admission["source_chunk_id"], "admission.source_chunk_id") != chunk_id
                or exact_int(admission["batch_id"], "admission.batch_id") != batch_id
                or admission["acceptance_scope_sha256"] != acceptance_scope_sha256
                or admission["saved_scoring_reexecuted"] is not False
                or admission["profiles_remeasured"] is not False):
            raise ValueError("Saved-output admission identity/scope/no-remeasurement contract changed")
        matches = [job for job in acceptance_scope["job_contracts"]
                   if job["original_measurement_directory"] == prefix.rstrip("/")]
        if len(matches) != 1 or matches[0]["acceptance_directory"] != acceptance_dir:
            raise ValueError("Public acceptance scope does not bind this exact original/derivative directory")
        contract = matches[0]
        required_json = [prefix + name for name in ("DRIFT_CHECKPOINT.json", "DRIFT_TOP20.json",
                         "FIXED_TOP3_PROFILES.json", "INPUT_PINS.json", "NORMALIZATION.json")]
        for name in required_json:
            if (admission["input_json_sha256"].get(name) != inputs.pins.get(name)
                    or contract["input_file_sha256"].get(name) != inputs.pins.get(name)):
                raise ValueError("Original saved JSON differs from acceptance/scope pins")
            inputs.pin_only(name)
            if inputs.opened[name]["bytes"] != contract["input_file_bytes"][name]:
                raise ValueError("Original saved JSON bytes differ from prospective acceptance inventory")
        terminal_info = admission["original_terminal_receipt"]
        terminal_name = terminal_info["path"]
        if (terminal_name != contract["original_terminal_receipt_path"]
                or terminal_info["sha256"] != contract["original_terminal_receipt_sha256"]
                or terminal_info["sha256"] != inputs.pins.get(terminal_name)):
            raise ValueError("Original terminal receipt differs from acceptance/public scope")
        terminal = inputs.load(terminal_name)
        if (inputs.opened[terminal_name]["bytes"] != terminal_info["bytes"]
                or terminal["status"] != admission["original_numeric_job_status"]
                or exact_int(terminal["source_chunk_id"], "terminal.source_chunk_id") != chunk_id
                or exact_int(terminal["batch_id"], "terminal.batch_id") != batch_id
                or terminal["fixed_batch_q"] != sorted(geometry["batches"][batch_id - 1])):
            raise ValueError("Original terminal status/identity was changed or misattributed")
        original_status = terminal["status"]
        if original_status == SUCCESS:
            expected_admission, expected_qa, display_status = ACCEPTED_COMPLETE, QA_COMPLETE, "COMPLETE"
            if terminal_name != prefix + "EXECUTION_RECEIPT.json" or terminal["scope_sha256"] != SCOPE_SHA256:
                raise ValueError("Original complete receipt has wrong provenance")
        elif original_status == FAILURE:
            expected_admission, expected_qa, display_status = ACCEPTED_FAILURE, QA_FAILURE, "FAILED"
            if terminal_name != prefix + "FAILURE_RECEIPT.json" or terminal["error_type"] != "ResourceLimitExceeded":
                raise ValueError("Expected preserved original resource exception")
        else:
            raise ValueError("Unexpected original terminal status; no saved-output admission")
        qa_info = admission["QA_receipt"]
        qa_name = qa_info["path"]
        if (admission["status"] != expected_admission
                or qa_name != acceptance_dir + "/QA_RECEIPT.json"
                or qa_info["passed"] is not True or qa_info["status"] != expected_qa
                or qa_info["sha256"] != inputs.pins.get(qa_name)):
            raise ValueError("Saved-output acceptance/QA status does not match preserved original disposition")
        qa = inputs.load(qa_name)
        if (qa["status"] != qa_info["status"]
                or inputs.opened[qa_name]["bytes"] != qa_info["bytes"]):
            raise ValueError("Actual saved-output QA differs from acceptance receipt pin")
        actual, full = load_checkpoint(inputs.load(prefix + "DRIFT_CHECKPOINT.json"), chunk_id, batch_id, geometry)
        if not full:
            raise ValueError("Saved-output verification requires all381 actual completed map receipts")
        metadata = {"original_numeric_job_status": original_status,
                    "original_display_status": display_status,
                    "acceptance_status": admission["status"], "QA_status": qa_info["status"]}
        new_cases, new_means, new_labels = load_profiles(
            inputs.load(prefix + "FIXED_TOP3_PROFILES.json"), inputs.load(prefix + "DRIFT_TOP20.json"),
            metadata, chunk_id, batch_id, geometry)
        cases.extend(new_cases)
        means.extend(new_means)
        labels.extend(new_labels)
        coverage[chunk_id].append(actual)
        batch_summary.append({"source_chunk_id": chunk_id, "batch_id": batch_id,
                              "original_numeric_job_status": original_status,
                              "original_display_status": display_status,
                              "original_numeric_job_complete": original_status == SUCCESS,
                              "saved_output_verification_status": admission["status"],
                              "saved_output_verification_passed": True,
                              "saved_output_QA_status": qa_info["status"],
                              "original_terminal_receipt": terminal_info,
                              "acceptance_receipt_path": acceptance_name,
                              "acceptance_receipt_sha256": inputs.pins[acceptance_name],
                              "completed_core_q_by_ON": {s: sorted(actual[s]) for s in ONS},
                              "actual_saved_map_receipts": sum(len(actual[s]) for s in ONS),
                              "expected_saved_map_receipts": 381,
                              "expected_cores_per_ON": 127,
                              "profiles_displayed": 9})
    if len(cases) != 36:
        raise ValueError("Expected exactly36 saved-output-verified fixed profiles")
    return coverage, batch_summary, cases, np.asarray(means, dtype=np.float64), labels


def plot_coverage(output, geometry, coverage, batch_summary, disposition):
    # State0=excluded edge,1=batch01 done,2=batch02 done,3=not completed.
    raster = np.full((6, 256), 3, dtype=np.int8)
    raster[:, [0, 255]] = 0
    for row, (chunk_id, scan) in enumerate((c, s) for c in CHUNKS for s in ONS):
        for batch_index in (0, 1):
            raster[row, sorted(coverage[chunk_id][batch_index][scan])] = batch_index + 1
    colors = ["#292f36", "#197fa3", "#cf7b27", "#f0f0f0"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-.5, 4.5), cmap.N)
    fig, ax = plt.subplots(figsize=(14.8, 8.5))
    ax.imshow(raster, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest",
              extent=(-.5, 255.5, 5.5, -.5))
    counts = []
    ylabels = []
    for chunk_id, scan in ((c, s) for c in CHUNKS for s in ONS):
        total = coverage[chunk_id][0][scan] | coverage[chunk_id][1][scan]
        count = len(total)
        counts.append({"source_chunk_id": chunk_id, "scan_id": scan,
                       "completed_reference_cores": count,
                       "reference_channels": count * 4096,
                       "native_chunk_fraction": count / 256,
                       "all_safe_core_coverage_complete": count == 254})
        label = SHORT[SCANS.index(scan)]
        ylabels.append(f"Chunk{chunk_id} {label}\n{count}/256 cores ({count / 256:.5%})")
    ax.set_yticks(range(6), ylabels, fontsize=10)
    ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
    ax.set_xlabel("Reference core q (4096 native channels per core)", fontsize=11, labelpad=10)
    ax.set_xlim(-.5, 255.5)
    ax.set_ylim(5.5, -.5)
    ax.axvline(127.5, color="black", linewidth=.6, alpha=.45)
    ax.axhline(2.5, color="black", linewidth=1.3, linestyle="--")
    ax.set_title("Two native bands: verified saved reference-carrier coverage\n"
                 "Actual saved ON/core receipts · original terminal statuses retained", fontsize=13, pad=17)
    legends = [Patch(facecolor=c, edgecolor="#555555", linewidth=.5, label=l)
               for c, l in zip(colors, ("Excluded edge cores", "Batch 01 saved maps", "Batch 02 saved maps",
                                        "No saved map receipt"))]
    fig.legend(handles=legends, loc="upper center", bbox_to_anchor=(.55, .855),
               ncol=4, frameon=False, fontsize=9)
    batch_lines = [f"C{item['source_chunk_id']} B{item['batch_id']:02d}: "
                   f"{item['actual_saved_map_receipts']}/381 saved map receipts · "
                   f"original {item['original_display_status']} · saved-output verification PASS"
                   for item in batch_summary]
    original_complete_count = sum(item["original_numeric_job_complete"] for item in batch_summary)
    fig.text(.55, .135, "\n".join(batch_lines), ha="center", va="center", fontsize=9)
    fig.text(.55, .055,
             "Target per band: 254/256 cores = 99.21875% for this fixed drift grid and widths1/3.\n"
             "One historical visit · reference-carrier coverage is not survey or sensitivity completeness.\n"
             "Two edge cores excluded per band · trajectory/read halos may overlap · "
             f"{4 - original_complete_count} original resource failures + "
             f"{original_complete_count} original completion; all4 saved outputs verified",
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.20, right=.98, top=.75, bottom=.255)
    path = output / "NEXT_BANDS_COVERAGE.png"
    fig.savefig(path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned saved JSON next-band renderer",
                          "Description": "Saved-map receipt coverage with unchanged original job statuses"})
    plt.close(fig)
    return path, {"coverage_by_ON": counts,
                  "raster_int8_sha256": hashlib.sha256(raster.tobytes()).hexdigest(),
                  "new_coverage_basis": "Exact checkpoint completed_receipts scan_id/reference_core_q only",
                  "original_job_statuses_rewritten": False,
                  "saved_output_verification_implies_original_resource_compliance": False,
                  "source_chunk_count": 2, "no_other_chunk_coverage_inferred": True,
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
        if row and cases[row]["source_chunk_id"] != cases[row - 1]["source_chunk_id"]:
            ax.axhline(row - .5, color="#222222", linewidth=2.1)
        elif row and cases[row]["batch_id"] != cases[row - 1]["batch_id"]:
            ax.axhline(row - .5, color="#333333", linewidth=1.4, linestyle="--")
        for col in range(6):
            rgba = im.cmap(im.norm(means[row, col]))
            luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
            ax.text(col, row, f"{means[row, col]:+.3f}", ha="center", va="center",
                    fontsize=10, color="black" if luminance > .55 else "white")
    color = fig.colorbar(im, ax=ax, fraction=.038, pad=.028)
    color.set_label("Saved mean center minus fixed flank\n(row-normalized power; not SNR)",
                    fontsize=10, labelpad=11)
    title = "Verified saved outputs: fixed-profile means across all six scans"
    subtitle = (f"{n} selected paths · original top3 perON within each chunk/batch · "
                "one historical visit")
    ax.set_title(title + "\n" + subtitle, fontsize=12, pad=17)
    fig.text(.56, .030,
             "Chunk/batch-specific display ranks · no global reranking · fixed shift0 · post-selection description.\n"
             "All six exact-path means retained; adjacent OFF controls are described in the report/JSON.\n"
             "No OFF veto or origin classification; small exact-path OFF means do not rule out nearby features."
             "\nOriginal failures remain failures; saved-output verification is separate from original resource compliance.",
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.36, right=.90, top=.905, bottom=.105)
    path = output / "NEXT_BANDS_FIXED_PROFILE_MEANS.png"
    fig.savefig(path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned saved JSON next-band renderer",
                          "Description": "Unchanged saved six-scan means; no numerical processing or ranking"})
    plt.close(fig)
    return path, {"symmetric_color_limits": [-limit, limit],
                  "actual_minimum_saved_mean": float(np.min(means)),
                  "actual_maximum_saved_mean": float(np.max(means)),
                  "all_actual_saved_means_inside_color_limits": bool(np.all(np.abs(means) < limit)),
                  "saved_mean_count_displayed": int(means.size),
                  "saved_means_float64_sha256": hashlib.sha256(means.tobytes()).hexdigest(),
                  "selection": "Unchanged saved top3 perON separately within each native chunk/batch",
                  "profile_identity_fields": ["source_chunk_id", "batch_id", "track_id"],
                  "cross_batch_reranking": False, "profile_NPZ_read": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--pins", required=True, type=Path)
    parser.add_argument("--final-scope", default=SCOPE, choices=(SCOPE,),
                        help="Root-relative final executable scope JSON path, pinned in --pins")
    parser.add_argument("--acceptance-scope", default=ACCEPTANCE_SCOPE, choices=(ACCEPTANCE_SCOPE,))
    parser.add_argument("--expected-acceptance-scope-sha256", required=True)
    parser.add_argument("--acceptance-freeze-commit", required=True,
                        help="Exact public prospective saved-output acceptance freeze commit")
    parser.add_argument("--authorized-disposition", required=True,
                        choices=("ALL_SAVED_VERIFIED",))
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.outdir or root / STAGE / "figures").resolve()
    if output.exists():
        raise ValueError("Output directory already exists: preserve figures; no automatic rerun")
    if digest(root / ORIGINAL_PLOT) != ORIGINAL_PLOT_SHA256:
        raise ValueError("Frozen original renderer changed; preserve its original bytes")
    if (len(args.acceptance_freeze_commit) != 40
            or any(c not in "0123456789abcdef" for c in args.acceptance_freeze_commit)):
        raise ValueError("Expected exact prospective acceptance public commit")
    inputs = PinnedJSON(root, args.pins)
    if inputs.pins.get(SCOPE) != SCOPE_SHA256:
        raise ValueError("Common scientific scope differs from the exact prospective public freeze pin")
    if inputs.pins.get(args.acceptance_scope) != args.expected_acceptance_scope_sha256:
        raise ValueError("Acceptance scope differs from root's exact public freeze pin")
    activation = inputs.load(ACTIVATION)
    geometry = activation_geometry(activation)
    # The final executable scope is pinned/read for byte identity and provenance.
    # Its numerical outcome values are neither calculated nor opened here.
    final_scope = inputs.load(args.final_scope)
    if final_scope["immutable_metadata_selection"] != activation["immutable_metadata_selection"]:
        raise ValueError("Final executable scope changed the prospective activation core selections")
    if (final_scope["source_chunk_ids"] != list(CHUNKS)
            or final_scope["expected_scan_tiles_per_batch"] != 381
            or final_scope["expected_total_scan_tiles_if_all_four_complete"] != 1524
            or final_scope["expected_total_profiles_if_all_four_complete"] != 36):
        raise ValueError("Final scope's per-band output geometry changed")
    if (final_scope["OFF_veto"] is not False
            or final_scope["unqualified_exploratory_only"] is not True
            or final_scope["calibrated_SNR_FAP_flux_EIRP_or_sensitivity"] is not False):
        raise ValueError("Original exploratory scientific limitation flags changed")
    acceptance_scope = inputs.load(args.acceptance_scope)
    if (acceptance_scope["original_scope_sha256"] != SCOPE_SHA256
            or acceptance_scope["original_wrapper_sha256"] != final_scope["script_sha256"]
            or len(acceptance_scope["job_contracts"]) != 4):
        raise ValueError("Prospective acceptance scope does not bind the exact original four-job science")
    coverage, batch_summary, cases, means, labels = load_batches(
        inputs, geometry, acceptance_scope, args.expected_acceptance_scope_sha256)
    inputs.verify_unchanged()
    if digest(root / ORIGINAL_PLOT) != ORIGINAL_PLOT_SHA256:
        raise ValueError("Frozen original renderer changed during saved-output plotting")
    output.mkdir(parents=True, exist_ok=False)
    paths = [plot_coverage(output, geometry, coverage, batch_summary, args.authorized_disposition),
             plot_means(output, means, labels, cases, args.authorized_disposition)]
    inputs.verify_unchanged()
    if digest(root / ORIGINAL_PLOT) != ORIGINAL_PLOT_SHA256:
        raise ValueError("Frozen original renderer changed during saved-output rendering")
    cpu = time.process_time()
    cap_pass = cpu <= CPU_CAP
    receipt = {
        "schema": "SETI_NEXT_NATIVE_BANDS_VERIFIED_SAVED_JSON_PLOTTING_V1",
        "status": ("COMPLETE_TWO_VERIFIED_SAVED_JSON_PUBLICATION_FIGURES" if cap_pass else
                   "COMPLETE_TWO_FIGURES_PLOTTING_CPU_CAP_EXCEEDED_NO_RETRY"),
        "authorized_disposition": args.authorized_disposition,
        "script_sha256": digest(Path(__file__)),
        "input_pins_sha256": inputs.pins_sha, "input_json": inputs.opened,
        "input_json_byte_unchanged": True,
        "final_scientific_scope_path": args.final_scope,
        "final_scientific_scope_sha256": inputs.pins[args.final_scope],
        "prospective_numeric_freeze_commit": NUMERIC_FREEZE_COMMIT,
        "prospective_absolute_path_recovery_freeze_commit": RECOVERY_FREEZE_COMMIT,
        "acceptance_scope_path": args.acceptance_scope,
        "acceptance_scope_sha256": args.expected_acceptance_scope_sha256,
        "prospective_acceptance_freeze_commit": args.acceptance_freeze_commit,
        "frozen_original_plot_script_sha256": ORIGINAL_PLOT_SHA256,
        "frozen_original_plot_script_byte_unchanged": True,
        "original_numeric_job_statuses_rewritten": False,
        "original_complete_job_count": sum(b["original_numeric_job_complete"] for b in batch_summary),
        "original_resource_failure_count": sum(not b["original_numeric_job_complete"] for b in batch_summary),
        "all_four_saved_outputs_verified": True,
        "saved_output_verification_is_sky_qualification": False,
        "saved_output_verification_implies_original_resource_compliance": False,
        "source_chunk_ids": list(CHUNKS),
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
            "Coverage counts reference carriers separately in chunks153/154 for the fixed grid/widths, not survey/sensitivity completeness",
            "The two batch reference-core selections within each native chunk are disjoint, while read/trajectory halos can overlap",
            "All scans belong to one historical visit; scan labels are not independent visits",
            "Post-selection means are descriptive; small fixed-path OFF values do not establish absence of nearby OFF features",
            "Original numeric terminal statuses/cap failures are preserved; saved-output verification is separate and does not establish original resource compliance",
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
