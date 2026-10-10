"""Independently audit one completed full-safe batch from saved outputs only.

No source HDF5 is opened and no detector or source-loader module is imported.
Ranking is reconstructed from saved carrier maxima; cheap profile algebra is
checked against retained patches. This is not a search/profile rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

CPU_CAP, WALL_CAP, MEMORY_CAP = 180, 300, 2 * 1024**3
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
C0, COUNT = 158334976, 1048576
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
SCRIPT_SHA = "8758f48de05e139431196c958c9e20b4bd6c24200fc57906245cc91ac4cfe56f"
SCOPE_SHA = "1e77f78f5c957082da3eebdb1c70641b6ba7687ce2996578ccb5a9caf0287d22"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def same(actual, expected, message):
    check(np.array_equal(actual, expected), message)


def check_ref(out, filename, expected_hash, expected_size):
    path = out / filename
    check(path.resolve().is_relative_to(out.resolve()), "Reference escapes output directory")
    check(path.stat().st_size == expected_size, "Saved file size differs: " + filename)
    check(digest(path) == expected_hash, "Saved file hash differs: " + filename)
    return path


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / f"results/radio_full_safe_20261010/batch_{args.batch:02d}/measurement"
    receipt_path = out / "QA_RECEIPT.json"
    check(not receipt_path.exists() and not (out / "QA_FAILURE_RECEIPT.json").exists(),
          "QA is performed once per completed batch")

    def deadline(signum, frame):
        raise TimeoutError("Saved-output QA CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    global np
    import numpy as np

    counts = {"maps": 0, "normalization_files": 0, "carrier_maximum_records": 0,
              "top20_entries": 0, "patches": 0, "scan_profiles": 0, "time_rows": 0,
              "retained_raw_patch_cells": 0, "binary_and_normalization_hashes": 0}
    try:
        scope_path = root / "tools/radio_full_safe_20261010/scope.json"
        wrapper_path = root / "tools/radio_full_safe_20261010/full_safe_search.py"
        check(digest(scope_path) == SCOPE_SHA and digest(wrapper_path) == SCRIPT_SHA,
              "Public frozen common scope/wrapper identity differs")
        scope = read_json(scope_path)
        for name, sha in scope["pinned_dependency_files"].items():
            check(digest(root / name) == sha, "Metadata/code pin differs: " + name)
        result = read_json(out / "EXECUTION_RECEIPT.json")
        check(result["status"] == "COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY",
              "Completed scientific job required")
        check(result["batch_id"] == args.batch, "Batch identity differs")
        check(result["scope_sha256"] == SCOPE_SHA and result["script_sha256"] == SCRIPT_SHA,
              "Execution receipt scope/wrapper identity differs")
        qs = scope["batch_q"][args.batch - 1]
        expected_pairs = [(scan, i, q) for i, q in enumerate(qs) for scan in ONS]
        check(len(qs) == 107 and result["fixed_batch_q"] == qs, "Fixed core selection differs")
        summary = result["search_summary"]
        for field, expected in (("batch_id", args.batch), ("completed_scan_tiles", 321),
                                ("new_core_count", 107), ("searched_q", qs),
                                ("carriers_per_ON", 438272), ("known_previous_core_count", 40),
                                ("previous_plus_this_batch_unique_carriers_per_ON", 147 * 4096),
                                ("completion_of_other_batch_inferred", False), ("drift_grid_count", 763),
                                ("widths_channels", [1, 3]), ("display_suppression_channels", 3),
                                ("reference_core_intervals_half_open", [[C0 + q * 4096, C0 + (q + 1) * 4096] for q in qs])):
            check(summary[field] == expected, "Search summary differs: " + field)
        for field, expected in (("source_manifest_sha256", scope["source_manifest_sha256"]),
                                ("acquisition_summary_sha256", scope["acquisition_summary_sha256"]),
                                ("proposal_sha256", scope["proposal_sha256"]),
                                ("metadata_selection_canonical_SHA256", scope["metadata_selection_canonical_SHA256"]),
                                ("one_historical_visit", True), ("source_values_previously_exposed", True),
                                ("blind_or_independent_validation", False), ("qualified_sky_pilot", False),
                                ("OFF_veto_applied", False), ("old_A_B_failure_statuses_changed", False),
                                ("old_holdouts_reopened", False), ("numeric_retry_authorized", False),
                                ("completion_of_other_batch_inferred", False)):
            check(result[field] == expected, "Scientific execution contract differs: " + field)
        for field, cap in (("process_CPU_seconds_including_imports", 1200),
                           ("wall_seconds_including_imports", 1800), ("peak_RSS_bytes", 4294967296)):
            check(0 < result[field] <= cap, "Execution measured resource cap differs: " + field)
        check(result["new_telescope_HTTP_requests_during_analysis"] == 0
              and result["new_telescope_BODY_bytes_during_analysis"] == 0,
              "Unexpected source requests declared")
        acquisition = read_json(root / "results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json")
        expected_inputs = {r["scan_id"]: r for r in acquisition["decoded_files"]}
        verified = result["verified_source_inputs"]
        check(len(verified) == 6 and set(verified) == set(SCANS),
              "Six runtime-verified inputs required")
        for scan, item in verified.items():
            original = expected_inputs[scan]
            check(item == {"path": original["array_file"], "file_sha256": original["file_sha256"],
                           "bytes": original["bytes"]}, "Verified input receipt differs")
        source = read_json(root / "tools/radio_fresh_band_20261009/source_manifest.json")
        headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
        anchor = min(h["tstart"] for h in headers.values())
        check(result["MJD_anchor"] == anchor, "Time anchor differs")
        drift_grid = np.linspace(-4.0, 4.0, 763)
        checkpoint_path = out / "DRIFT_CHECKPOINT.json"
        checkpoint = read_json(checkpoint_path)
        check(checkpoint["batch_id"] == args.batch and checkpoint["fixed_batch_q"] == qs,
              "Checkpoint batch/core identity differs")
        check(checkpoint["complete"] and checkpoint["completed_scan_tiles"] == 321
              and checkpoint["expected_scan_tiles"] == 321, "Incomplete map checkpoint")
        entries = checkpoint["completed_receipts"]
        check([(r["scan_id"], r["tile_index"], r["reference_core_q"]) for r in entries] == expected_pairs,
              "Map receipt order or identity differs")
        for scan in ONS:
            check(checkpoint["completed_q_by_ON"][scan] == qs
                  and checkpoint["completed_core_count_by_ON"][scan] == 107,
                  "Checkpoint ON inventory differs")
        saved = {scan: [] for scan in ONS}
        map_keys = {"frequency_hz_at_tref", "maximum_robust_box_track_score", "winning_drift_hz_s",
                    "winning_width_channels", "valid_hypothesis_count", "source_reference_channels", "drift_grid_hz_s"}
        for r in entries:
            first = C0 + r["reference_core_q"] * 4096
            channels = np.arange(first, first + 4096)
            check(r["reference_channel_interval_half_open"] == [first, first + 4096]
                  and r["core_start_relative_channel"] == r["reference_core_q"] * 4096
                  and r["searched_carriers"] == 4096 and r["valid_hypotheses_per_carrier"] == 1526,
                  "Map coordinate/count receipt differs")
            path = check_ref(out, r["path"], r["sha256"], r["bytes"])
            normpath = check_ref(out, r["normalization_path"], r["normalization_sha256"], r["normalization_bytes"])
            normalization = read_json(normpath)
            check(set(normalization) == {"row_power_median", "row_residual_median",
                                         "row_winsorized_residual_location", "row_residual_MAD_scale",
                                         "normalization_unmasked_counts", "normalization_source_channels"},
                  "Normalization JSON schema differs")
            same(np.asarray(normalization["normalization_source_channels"]), channels, "Normalization core differs")
            same(np.asarray(normalization["normalization_unmasked_counts"]), np.full(16, 4096), "Normalization mask counts differ")
            for field in ("row_power_median", "row_residual_median", "row_winsorized_residual_location", "row_residual_MAD_scale"):
                values = np.asarray(normalization[field])
                check(values.shape == (16,) and np.isfinite(values).all(), "Invalid normalization rows: " + field)
                if field in ("row_power_median", "row_residual_MAD_scale"):
                    check((values > 0).all(), "Nonpositive normalization scale")
            with np.load(path, allow_pickle=False) as z:
                check(set(z.files) == map_keys, "Map array schema differs")
                m = {k: z[k] for k in z.files}
            for field, dtype in (("frequency_hz_at_tref", "<f8"), ("maximum_robust_box_track_score", "<f8"),
                                 ("winning_drift_hz_s", "<f8"), ("winning_width_channels", "<i2"),
                                 ("valid_hypothesis_count", "<i8"), ("source_reference_channels", "<i8"),
                                 ("drift_grid_hz_s", "<f8")):
                check(m[field].dtype == np.dtype(dtype), "Map precision/schema differs: " + field)
            same(m["source_reference_channels"], channels, "Map source channels differ")
            same(m["frequency_hz_at_tref"], FCH1 + DF * channels, "Map source frequencies differ")
            same(m["drift_grid_hz_s"], drift_grid, "Map drift grid differs")
            same(m["valid_hypothesis_count"], np.full(4096, 1526), "Incomplete saved hypothesis validity")
            for field in ("maximum_robust_box_track_score", "winning_drift_hz_s", "winning_width_channels"):
                check(m[field].shape == (4096,) and np.isfinite(m[field]).all(), "Nonfinite/map shape differs: " + field)
            check(np.isin(m["winning_drift_hz_s"], drift_grid).all(), "Winner outside frozen drift grid")
            check(np.isin(m["winning_width_channels"], (1, 3)).all(), "Winner outside frozen widths")
            saved[r["scan_id"]].append(m)
            counts["maps"] += 1; counts["normalization_files"] += 1
            counts["carrier_maximum_records"] += 4096; counts["binary_and_normalization_hashes"] += 2

        tops_path = out / "DRIFT_TOP20.json"
        tops = read_json(tops_path)
        check(set(tops) == set(ONS), "Top20 origin inventory differs")
        for scan in ONS:
            channels = np.concatenate([m["source_reference_channels"] for m in saved[scan]])
            scores = np.concatenate([m["maximum_robust_box_track_score"] for m in saved[scan]])
            drifts = np.concatenate([m["winning_drift_hz_s"] for m in saved[scan]])
            widths = np.concatenate([m["winning_width_channels"] for m in saved[scan]])
            chosen = []
            for index in np.lexsort((channels, -scores)):
                j = int(index)
                if all(abs(int(channels[j]) - int(channels[k])) > 3 for k in chosen):
                    chosen.append(j)
                if len(chosen) == 20:
                    break
            check(len(tops[scan]) == 20, "Top20 count differs")
            for rank, (track, j) in enumerate(zip(tops[scan], chosen), 1):
                expected = {"track_id": scan + "_gap_drift_rank_%02d" % rank,
                            "family": "gap_drift", "batch_id": args.batch,
                            "originating_scan": scan, "originating_role": "ON", "display_rank": rank,
                            "source_reference_channel": int(channels[j]),
                            "reference_frequency_hz": FCH1 + DF * int(channels[j]),
                            "reference_seconds_from_anchor": (headers[scan]["tstart"] - anchor) * 86400 + .5 * TSAMP,
                            "drift_hz_s": float(drifts[j]), "width_channels": int(widths[j]),
                            "maximum_robust_box_track_score": float(scores[j]),
                            "reference_core_tile": j // 4096, "reference_core_q": qs[j // 4096],
                            "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
                check(track == expected, "Saved top20 differs from unchanged tie/NMS reconstruction")
                counts["top20_entries"] += 1
        profile_summary = result["fixed_profile_summary"]
        check(profile_summary["source_top20_sha256"] == digest(tops_path)
              and profile_summary["profile_count"] == 9 and profile_summary["all_rows_retained"] == 16
              and profile_summary["plot_count"] == 0
              and not profile_summary["shift_frequency_drift_width_optimization_applied"],
              "Profile family summary differs")
        fullnorm_path = root / "results/radio_fresh_band_20261009/stationary/NORMALIZATION.json"
        check(profile_summary["saved_normalization_sha256"] == digest(fullnorm_path), "Full-chunk normalization pin differs")
        fullnorm = read_json(fullnorm_path)
        rowmedians = np.asarray([fullnorm["row_power_medians"][scan] for scan in SCANS])
        records_path = out / "FIXED_TOP3_PROFILES.json"
        records = read_json(records_path)
        expected_tracks = [t for scan in ONS for t in tops[scan][:3]]
        check(len(records) == 9 and [r["selected_track"] for r in records] == expected_tracks,
              "Fixed top3 profile selection differs")
        patch_keys = {"raw_power", "row_normalized_power", "saved_full_chunk_row_medians",
                      "frozen_source_channel_centers", "source_channel_offsets", "times_seconds_from_reference",
                      "center_row_normalized_power", "fixed_flank_median_row_normalized_power",
                      "center_minus_flank_each_row", "mean_fixed_track_frequency_profile", "scans",
                      "df_hz", "source_channel0", "reference_frequency_hz", "drift_hz_s", "width_channels", "fixed_source_channel_shift"}
        offsets = np.arange(-64, 65)
        for record in records:
            track = record["selected_track"]
            path = check_ref(out, record["patch"]["path"], record["patch"]["sha256"], record["patch"]["bytes"])
            with np.load(path, allow_pickle=False) as z:
                check(set(z.files) == patch_keys, "Profile patch schema differs")
                a = {k: z[k] for k in z.files}
            raw = a["raw_power"]
            check(raw.shape == (6, 16, 129) and raw.dtype == np.dtype("<f4")
                  and np.isfinite(raw).all() and (raw >= 0).all(), "Invalid saved raw patch")
            same(a["scans"], np.asarray(SCANS), "Patch scan identities differ")
            same(a["source_channel_offsets"], offsets, "Patch offsets differ")
            same(a["saved_full_chunk_row_medians"], rowmedians, "Patch row medians differ")
            for field, expected in (("df_hz", DF), ("source_channel0", C0),
                                    ("reference_frequency_hz", track["reference_frequency_hz"]),
                                    ("drift_hz_s", track["drift_hz_s"]), ("width_channels", track["width_channels"]),
                                    ("fixed_source_channel_shift", 0)):
                check(a[field].shape == () and a[field].item() == expected, "Patch scalar differs: " + field)
            dt = np.asarray([(headers[scan]["tstart"] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                             - track["reference_seconds_from_anchor"] for scan in SCANS])
            base = (track["reference_frequency_hz"] - FCH1) / DF
            centers = np.rint(base + track["drift_hz_s"] * dt / DF).astype(np.int64)
            same(a["times_seconds_from_reference"], dt, "Patch actual header times differ")
            same(a["frozen_source_channel_centers"], centers, "Patch absolute rounded centers differ")
            check(centers.min() - C0 - 64 >= 0 and centers.max() - C0 + 64 < COUNT,
                  "Patch geometry exceeds retained source chunk")
            normalized = raw.astype(np.float64) / rowmedians[:, :, None]
            baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
            radius = track["width_channels"] // 2
            center = normalized[:, :, 64 - radius:65 + radius].mean(axis=2)
            residual = center - baseline
            mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
            same(a["row_normalized_power"], normalized, "Saved patch normalization differs")
            same(a["fixed_flank_median_row_normalized_power"], baseline, "Saved fixed flank differs")
            same(a["center_row_normalized_power"], center, "Saved width box differs")
            same(a["center_minus_flank_each_row"], residual, "Saved residual differs")
            same(a["mean_fixed_track_frequency_profile"], mean_profile, "Saved mean frequency profile differs")
            check(record["fixed_frequency_shift_channels"] == 0
                  and record["classification"] == "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE",
                  "Unchanged descriptive profile contract differs")
            check(len(record["scan_profiles"]) == 6, "Six profile scan summaries required")
            for i, profile in enumerate(record["scan_profiles"]):
                expected = {"scan_id": SCANS[i], "mean_center_minus_flank": float(residual[i].mean()),
                            "median_center_minus_flank": float(np.median(residual[i])),
                            "positive_rows": int(np.count_nonzero(residual[i] > 0)),
                            "first_eight_mean_center_minus_flank": float(residual[i, :8].mean()),
                            "last_eight_mean_center_minus_flank": float(residual[i, 8:].mean()),
                            "all_16_center_minus_flank_rows": residual[i].tolist(),
                            "all_16_raw_width_mean_power": raw[i, :, 64 - radius:65 + radius].mean(axis=1).tolist(),
                            "frozen_source_channel_centers": centers[i].tolist()}
                check(profile == expected, "Saved scan JSON metrics differ from retained patch")
                counts["scan_profiles"] += 1; counts["time_rows"] += 16
            counts["patches"] += 1; counts["retained_raw_patch_cells"] += raw.size
            counts["binary_and_normalization_hashes"] += 1
        check(counts["maps"] == 321 and counts["carrier_maximum_records"] == 1314816
              and counts["top20_entries"] == 60 and counts["patches"] == 9
              and counts["scan_profiles"] == 54 and counts["time_rows"] == 864, "QA inventory incomplete")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
                    "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and measured["wall_seconds"] <= WALL_CAP and measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Measured saved-output QA resource cap exceeded")
        receipt = {"status": "PASS_COMPLETE_SAVED_BATCH_OUTPUTS", "batch_id": args.batch,
                   "freeze_commit": args.freeze_commit, "public_scope_sha256": SCOPE_SHA,
                   "public_wrapper_sha256": SCRIPT_SHA, "qa_script_sha256": digest(Path(__file__)),
                   "execution_receipt_sha256": digest(out / "EXECUTION_RECEIPT.json"),
                   "checkpoint_sha256": digest(checkpoint_path), "top20_sha256": digest(tops_path),
                   "profile_JSON_sha256": digest(records_path), "counts": counts,
                   "fixed_batch_q": qs, "metadata_code_pins_checked": len(scope["pinned_dependency_files"]),
                   "cap_CPU_s_this_QA": CPU_CAP, "cap_CPU_s_two_QAs_combined": 400,
                   "combined_two_QA_process_caps_s": 360,
                   "separate_joint_source_cell_audit_CPU_cap_s": 20,
                   "prior_measured_static_components_CPU_s": 1.145850565,
                   "cap_wall_s_this_QA": WALL_CAP, "cap_memory_bytes": MEMORY_CAP,
                   **measured, "source_HDF5_reads": 0, "detector_rescoring_runs": 0,
                   "new_profile_projection_runs": 0, "new_HTTP_requests": 0,
                   "QA_math": "Reconstruct tie/NMS from saved maxima; verify stored patch algebra and JSON metrics only.",
                   "raw_source_authenticity_limit": "This saved-output QA does not reread HDF5 source cells. The separate joint SOURCE_CELL_QA_RECEIPT.json records the authorized independent source-cell audit when completed.",
                   "scope_limit": "One exposed visit, batch-dependent selected profiles; no origin or calibrated significance inference."}
        temporary = receipt_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        temporary.replace(receipt_path)
        print(json.dumps(receipt, allow_nan=False), flush=True)
    except BaseException as exc:
        failure = {"status": "QA_INCOMPLETE_OR_FAILED_NO_RETRY", "batch_id": args.batch,
                   "error_type": type(exc).__name__, "error": str(exc), "partial_counts": counts,
                   "process_CPU_seconds_including_imports": time.process_time(),
                   "wall_seconds": time.monotonic() - started,
                   "source_HDF5_reads": 0, "detector_rescoring_runs": 0}
        (out / "QA_FAILURE_RECEIPT.json").write_text(json.dumps(failure, indent=2, allow_nan=False) + "\n")
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
