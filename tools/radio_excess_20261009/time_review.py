"""Bounded, fixed-channel time inspection of seven preselected cached profiles.

This helper measures and displays the selected width-one channel and fixed
flanking background. It makes no detector, drift, frequency or time-window
search, sends no requests, and does not change any qualification decision.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
SELECTED = (
    ("epoch1_on_contrast_rank_01", "epoch1_on", 160115804),
    ("epoch1_on_contrast_rank_02", "epoch1_on", 159485702),
    ("epoch1_on_contrast_rank_03", "epoch1_on", 160214486),
    ("epoch2_on_contrast_rank_01", "epoch2_on", 159543371),
    ("epoch2_on_contrast_rank_03", "epoch2_on", 160178146),
    ("epoch3_on_contrast_rank_01", "epoch3_on", 159552005),
    ("epoch3_on_contrast_rank_03", "epoch3_on", 159835573),
)
CHANNEL0, COUNT, ROWS = 159383552, 1048576, 16
DF_HZ, FCH1_HZ, TSAMP = -2.835503418452676, 1876464843.75, 17.986224128
HALF_WIDTH, EXCLUSION, WIDTH = 64, 3, 1
COLOR_LIMITS = (0.6, 1.6)
CHUNK_CACHE_BYTES = 80 * 1024**2
CPU_CAP, WALL_CAP, MEMORY_CAP = 25, 120, 1536 * 1024**2
SOURCE_SHA256 = "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec"
BROAD_SHA256 = "866de0dd7a07f17c1678a23cf04d66640b7ee6c5f398756cb8d3bccf84168dd6"
ACQUISITION_SHA256 = "2e380f79fc45b8f1288876656ee8a71b605f140d4c9130e543f30afe6fae8eac"


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for body in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(body)
    return result.hexdigest()


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def frequency(channel):
    return FCH1_HZ + DF_HZ * int(channel)


def pinned_json(path, expected, name):
    if digest(path) != expected:
        raise ValueError(f"Pinned {name} differs")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_inputs(args):
    scope = json.loads(Path(args.scope).read_text(encoding="utf-8"))
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Helper differs from frozen scope")
    pins = (("source_manifest_sha256", SOURCE_SHA256),
            ("broad_receipt_sha256", BROAD_SHA256),
            ("acquisition_summary_sha256", ACQUISITION_SHA256))
    if any(scope.get(key) != expected for key, expected in pins):
        raise ValueError("Frozen original provenance pins differ")
    choices = {
        "channel0": CHANNEL0, "count": COUNT,
        "df_hz": DF_HZ, "fch1_hz": FCH1_HZ, "tsamp_s": TSAMP,
        "time_rows": ROWS, "selection_count": len(SELECTED),
        "selected_width_channels": WIDTH,
        "slice_halfwidth_channels": HALF_WIDTH,
        "background_exclusion_halfwidth_channels": EXCLUSION,
        "background_flank_offsets_inclusive": [EXCLUSION + 1, HALF_WIDTH],
        "waterfall_color_limits": list(COLOR_LIMITS),
        "hdf5_chunk_cache_bytes_per_file": CHUNK_CACHE_BYTES,
    }
    if any(scope.get(key) != value for key, value in choices.items()):
        raise ValueError("Scope and implemented fixed measurement choices differ")
    limits = scope["limits"]
    if (limits["job_CPU_limit_s"], limits["job_wall_limit_s"], limits["job_memory_limit_bytes"]) != (CPU_CAP, WALL_CAP, MEMORY_CAP):
        raise ValueError("Scope and implemented job limits differ")

    source = pinned_json(args.source_manifest, SOURCE_SHA256, "source metadata")
    sources = source["sources"]
    if [item["label"] for item in sources] != list(SCANS) or [item["role"].upper() for item in sources] != ["ON", "OFF"] * 3:
        raise ValueError("Source is not the original alternating six scans")
    for item in sources:
        header = item["current_header"]["data_attributes"]
        if (not math.isclose(header["fch1"] * 1e6, FCH1_HZ, rel_tol=0, abs_tol=1e-6)
                or not math.isclose(header["foff"] * 1e6, DF_HZ, rel_tol=0, abs_tol=1e-12)
                or header["tsamp"] != TSAMP
                or item["current_header"]["dataset_shape"][:2] != [ROWS, 1]):
            raise ValueError("A source scan has different frequency/time grid or axes")
    acquisition = pinned_json(scope["acquisition_summary_path"], ACQUISITION_SHA256, "original acquisition summary")
    if (acquisition["status"] != "SIX_SCANS_ACQUIRED_EXPLORATORY_ONLY"
            or acquisition["original_qualification"] != "FAIL_CLOSED_UNCHANGED"
            or [item["scan_id"] for item in acquisition["decoded_files"]] != list(SCANS)):
        raise ValueError("Acquisition provenance is not the original exploratory six scans")
    broad = pinned_json(scope["broad_receipt_path"], BROAD_SHA256, "broad inventory receipt")
    expected_hashes = scope["compact_h5_sha256"]
    if (set(expected_hashes) != set(SCANS)
            or broad["original_compact_file_sha256"] != expected_hashes
            or broad["source_manifest_sha256"] != SOURCE_SHA256
            or broad["acquisition_summary_sha256"] != ACQUISITION_SHA256
            or broad["all96_local_compressed_chunk_hashes_matched_received_source_payloads"] is not True
            or broad["physical_source_channel_interval_half_open"] != [CHANNEL0, CHANNEL0 + COUNT]):
        raise ValueError("Compact HDF5 pins do not match original received-source provenance")

    normalization = pinned_json(args.normalization, scope["normalization_sha256"], "saved full-chunk row normalization")
    saved_medians = normalization["row_medians_over_full_physical_chunk"]
    if set(saved_medians) != set(SCANS):
        raise ValueError("Saved row normalization must contain exactly six scans")
    medians = np.asarray([saved_medians[scan] for scan in SCANS], dtype=np.float64)
    if medians.shape != (len(SCANS), ROWS) or not np.isfinite(medians).all() or not (medians > 0).all():
        raise ValueError("Saved row normalization contains invalid values")
    selection = pinned_json(args.selection, scope["selection_sha256"], "fixed profile selection")
    if (not isinstance(selection, list) or len(selection) != len(SELECTED)
            or [(item["ranked_id"], item["originating_on"], item["source_channel"]) for item in selection] != list(SELECTED)):
        raise ValueError("Selection differs from the seven frozen unreviewed profiles")
    for item in selection:
        channel = item["source_channel"]
        if (item["winning_width_channels"] != WIDTH
                or not math.isclose(item["frequency_hz"], frequency(channel), rel_tol=0, abs_tol=1e-6)
                or channel - CHANNEL0 - HALF_WIDTH < 0
                or channel - CHANNEL0 + HALF_WIDTH >= COUNT):
            raise ValueError("Selected profile width, frequency or slice bounds differ")
    verified = {}
    for scan in SCANS:
        path = Path(args.arrays_dir) / f"{scan}.compact.h5"
        sha = digest(path)
        if sha != expected_hashes[scan]:
            raise ValueError(f"Cached compact HDF5 differs: {scan}")
        verified[scan] = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha}
    return scope, sources, selection, medians, verified


def read_slices(args, selection):
    # Keep each file open for all seven reads. The cache can hold its complete
    # 16-row physical chunk (64 MiB), avoiding repeated decoder work per patch.
    slices = np.empty((len(selection), len(SCANS), ROWS, 2 * HALF_WIDTH + 1), dtype=np.float32)
    for scan_index, scan in enumerate(SCANS):
        path = Path(args.arrays_dir) / f"{scan}.compact.h5"
        with h5py.File(path, "r", rdcc_nbytes=CHUNK_CACHE_BYTES, rdcc_nslots=521, rdcc_w0=0.0) as saved:
            data = saved["data"]
            if (data.shape != (ROWS, 1, COUNT) or data.dtype != np.dtype("float32")
                    or data.chunks != (1, 1, COUNT)):
                raise ValueError(f"Cached data has different shape, dtype or chunks: {scan}")
            pipeline = data.id.get_create_plist()
            if pipeline.get_nfilters() != 1:
                raise ValueError(f"Cached data has different filter count: {scan}")
            filter_id, _, parameters, _ = pipeline.get_filter(0)
            if filter_id != 32008 or list(parameters) not in ([0, 3, 4, 0, 2], [0, 4, 4, 0, 2]):
                raise ValueError(f"Cached data has different bitshuffle/LZ4 parameters: {scan}")
            for case_index, record in enumerate(selection):
                center = record["source_channel"] - CHANNEL0
                patch = np.asarray(data[:, 0, center - HALF_WIDTH:center + HALF_WIDTH + 1], dtype=np.float32)
                if patch.shape != (ROWS, 2 * HALF_WIDTH + 1) or not np.isfinite(patch).all() or (patch < 0).any():
                    raise ValueError(f"Selected power patch is invalid: {scan}, {record['ranked_id']}")
                slices[case_index, scan_index] = patch
        print("READ_FIXED_TIME_PATCHES", scan, len(selection), flush=True)
    return slices


def contribution(values):
    positive = np.maximum(values, 0)
    total = float(np.sum(positive))
    order = np.lexsort((np.arange(ROWS), -positive))
    result = {"positive_residual_sum": total,
              "largest_positive_row_indices_zero_based": [int(index) for index in order[:4] if positive[index] > 0]}
    for count in (1, 4):
        numerator = float(np.sum(positive[order[:count]]))
        result[f"largest_{count}_positive_row_residual_sum"] = numerator
        result[f"largest_{count}_fraction_of_positive_residual_sum"] = numerator / total if total > 0 else None
    return result


def write_figure(fig, path):
    with Path(path).open("xb") as handle:
        fig.savefig(handle, format="png", dpi=110)
    plt.close(fig)


def plot_waterfalls(record, normalized, path):
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
    half_edge_hz = (HALF_WIDTH + 0.5) * abs(DF_HZ)
    for ax, scan, image in zip(axes.flat, SCANS, normalized):
        shown = ax.imshow(image[:, ::-1], origin="lower", aspect="auto", interpolation="nearest",
                          extent=[-half_edge_hz, half_edge_hz, 0, ROWS * TSAMP],
                          vmin=COLOR_LIMITS[0], vmax=COLOR_LIMITS[1], cmap="viridis")
        ax.axvline(0, color="white", linewidth=.7, linestyle="--")
        ax.set_title(scan + (" — selected originating ON" if scan == record["originating_on"] else ""), fontsize=10)
        ax.set_xlabel("Frequency offset from fixed selected channel (Hz)")
        ax.set_ylabel("Time since this scan's start (s)")
    fig.colorbar(shown, ax=list(axes.flat), shrink=.85, label="Raw power / saved full-chunk row median; clipped 0.6–1.6")
    fig.suptitle(f"{record['ranked_id']} — fixed ±{HALF_WIDTH}-channel patches in all six scans\n"
                 f"Reference {record['frequency_hz'] / 1e6:.9f} MHz; all {ROWS} original integrations; width 1\n"
                 "Display only: no drift alignment, frequency adjustment, time selection or detection decision.", fontsize=10)
    write_figure(fig, path)


def plot_time_profiles(record, centers, backgrounds, path):
    times = (np.arange(ROWS) + .5) * TSAMP
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
    smallest, largest = float(min(np.min(centers), np.min(backgrounds))), float(max(np.max(centers), np.max(backgrounds)))
    margin = max((largest - smallest) * .06, 0.02)
    for ax, scan, center, background in zip(axes.flat, SCANS, centers, backgrounds):
        ax.plot(times, center, "o-", color="#1763a6", linewidth=.9, markersize=3, label="Fixed selected channel")
        ax.plot(times, background, "s-", color="#b46116", linewidth=.9, markersize=2.5, label="Median of fixed flanks")
        ax.set_title(scan + (" — selected originating ON" if scan == record["originating_on"] else ""), fontsize=10)
        ax.set_xlim(0, ROWS * TSAMP)
        ax.set_ylim(smallest - margin, largest + margin)
        ax.set_xlabel("Integration midpoint since this scan's start (s)")
        ax.set_ylabel("Raw power / saved full-chunk row median")
        ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=8)
    fig.suptitle(f"{record['ranked_id']} — all {ROWS} fixed-channel time samples in each scan\n"
                 f"Reference {record['frequency_hz'] / 1e6:.9f} MHz; flank offsets ±4…±64 channels\n"
                 "Shared vertical scale; descriptive selected-profile inspection, not an independent detection test.", fontsize=10)
    write_figure(fig, path)


def run(args, started):
    scope, sources, selection, medians, verified = load_inputs(args)
    raw = read_slices(args, selection)
    normalized = raw.astype(np.float64) / medians[None, :, :, None]
    offsets = np.arange(-HALF_WIDTH, HALF_WIDTH + 1)
    flanks = np.abs(offsets) > EXCLUSION
    centers = normalized[:, :, :, HALF_WIDTH]
    backgrounds = np.median(normalized[:, :, :, flanks], axis=-1)
    residuals = centers - backgrounds
    if not np.isfinite(normalized).all() or not np.isfinite(residuals).all():
        raise ValueError("Normalized fixed patches are not finite")
    out = Path(args.outdir)
    records, output_files = [], []
    for case_index, selected in enumerate(selection):
        record = {"selected_profile": selected, "scan_measurements": {},
                  "measurement_definition": "selected-center raw power minus median of fixed flanks, each divided by the saved full-chunk row median",
                  "background_flank_offsets_inclusive": [EXCLUSION + 1, HALF_WIDTH],
                  "all_original_time_rows_retained": ROWS,
                  "classification": "DESCRIPTIVE_FIXED_CHANNEL_TIME_REVIEW_ONLY"}
        for scan_index, scan in enumerate(SCANS):
            raw_patch = np.asarray(raw[case_index, scan_index], dtype="<f4", order="C")
            values = residuals[case_index, scan_index]
            item = {
                "role": "ON" if scan.endswith("_on") else "OFF",
                "originating_selected_ON": scan == selected["originating_on"],
                "raw_slice_sha256": hashlib.sha256(raw_patch.tobytes(order="C")).hexdigest(),
                "raw_slice_hash_encoding": "little-endian float32, C order, shape [16,129]",
                "center_row_normalized_power": centers[case_index, scan_index].tolist(),
                "fixed_flank_median_row_normalized_power": backgrounds[case_index, scan_index].tolist(),
                "center_minus_flank_each_row": values.tolist(),
                "mean_center_minus_flank": float(np.mean(values)),
                "median_center_minus_flank": float(np.median(values)),
                "positive_center_minus_flank_rows": int(np.count_nonzero(values > 0)),
                "time_midpoints_since_scan_start_s": ((np.arange(ROWS) + .5) * TSAMP).tolist(),
                "original_observation_header_tstart_utc": sources[scan_index]["observation_header_tstart_utc"],
                "contribution_of_largest_positive_rows_descriptive_not_veto": contribution(values),
            }
            record["scan_measurements"][scan] = item
        stem = selected["ranked_id"]
        npz = out / (stem + "_fixed_time_patch.npz")
        with npz.open("xb") as handle:
            np.savez_compressed(handle, raw_power=raw[case_index], row_normalized_power=normalized[case_index],
                                saved_full_chunk_row_medians=medians, center_row_normalized_power=centers[case_index],
                                fixed_flank_median_row_normalized_power=backgrounds[case_index],
                                center_minus_flank_each_row=residuals[case_index],
                                source_channel=selected["source_channel"], source_channel0=CHANNEL0,
                                source_channel_count=COUNT, source_channel_offsets=offsets,
                                frequency_offsets_hz=offsets * DF_HZ, scans=np.asarray(SCANS),
                                originating_on=selected["originating_on"], width_channels=WIDTH,
                                time_midpoints_since_scan_start_s=(np.arange(ROWS) + .5) * TSAMP,
                                tsamp_s=TSAMP, df_hz=DF_HZ, fch1_hz=FCH1_HZ)
        images = [out / (stem + "_waterfalls.png"), out / (stem + "_time_profiles.png")]
        plot_waterfalls(selected, normalized[case_index], images[0])
        plot_time_profiles(selected, centers[case_index], backgrounds[case_index], images[1])
        record["saved_patch"] = {"path": npz.name, "sha256": digest(npz), "bytes": npz.stat().st_size}
        record["plots"] = [{"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size} for path in images]
        records.append(record)
        output_files.extend([record["saved_patch"], *record["plots"]])
        print("COMPLETED_FIXED_TIME_REVIEW", stem, flush=True)
    measurements = out / "TIME_REVIEW.json"
    save(measurements, records)
    receipt = {
        "status": "COMPLETED_EXPLORATORY_FIXED_CHANNEL_TIME_REVIEW",
        "scope_sha256": digest(args.scope), "script_sha256": digest(__file__),
        "source_manifest_sha256": digest(args.source_manifest),
        "acquisition_summary_sha256": scope["acquisition_summary_sha256"],
        "broad_receipt_sha256": scope["broad_receipt_sha256"],
        "normalization_sha256": digest(args.normalization), "selection_sha256": digest(args.selection),
        "verified_compact_HDF5_files": verified,
        "selection_count": len(selection), "selected_width_channels": WIDTH,
        "selected_source_channels": [item["source_channel"] for item in selection],
        "all_six_scan_roles_and_all_16_time_rows_retained": True,
        "source_patch_shape_per_selection": [len(SCANS), ROWS, 2 * HALF_WIDTH + 1],
        "requested_fixed_patch_reads": len(selection) * len(SCANS),
        "raw_powers_retained": int(raw.size),
        "hdf5_chunk_cache_bytes_per_file": CHUNK_CACHE_BYTES,
        "decoder_cache_policy": "One file open for all seven patches; cache holds the 16 full physical chunks. Physical decode count is not instrumented.",
        "background_flank_channels_per_row": int(np.count_nonzero(flanks)),
        "background_exclusion_halfwidth_channels": EXCLUSION,
        "measurement_definition": "Fixed selected channel / saved row median minus median of fixed flank channels / saved row median",
        "largest_positive_row_contributions": "Fractions of the sum of positive residuals; descriptive only, no threshold or veto",
        "normalization_reestimated": False, "time_selection_or_frequency_adjustment": False,
        "new_HTTP_requests": 0, "new_external_source_bytes": 0,
        "new_detector_scoring_or_drift_search": False,
        "original_failure_statuses_changed": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sky_sensitivity": False,
        "independent_observing_visits": 1,
        "patch_count": len(selection), "plot_count": 2 * len(selection),
        "outputs": output_files,
        "measurements": {"path": measurements.name, "sha256": digest(measurements), "bytes": measurements.stat().st_size},
        "limitations": [
            "Profiles were selected after inspecting the same time-averaged spectra; this is not independent validation",
            "A fixed frequency can dilute drifting emission; this helper does not optimize alignment",
            "Full-chunk row normalization does not calibrate gain or physical flux",
            "The fixed flanks can contain unrelated signals or structure; residual signs are descriptive",
            "Only seven selected profiles in one historical observing visit are inspected",
            "No profile classification, qualification pass, discovery, FAP, or qualified sky-null conclusion is issued",
        ],
        "versions": {"numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
                     "hdf5plugin": importlib.metadata.version("hdf5plugin"), "matplotlib": matplotlib.__version__},
        "caps": {"CPU_seconds": CPU_CAP, "wall_seconds": WALL_CAP, "address_space_bytes": MEMORY_CAP},
        "process_CPU_seconds_including_imports": time.process_time(),
        "wall_seconds_including_imports": time.monotonic() - started,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    save(out / "TIME_REVIEW_RECEIPT.json", receipt)
    print(json.dumps(receipt, allow_nan=False), flush=True)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("scope", "source-manifest", "arrays-dir", "normalization", "selection", "outdir"):
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)

    def deadline(signum, frame):
        raise TimeoutError("Frozen fixed-channel time-review CPU/wall cap reached")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        global np, h5py, matplotlib, plt
        import numpy as np
        import hdf5plugin  # Register the supported normal HDF5 bitshuffle/LZ4 decoder.
        import h5py
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        run(args, started)
    except BaseException as exc:
        save(Path(args.outdir) / "TIME_REVIEW_FAILURE.json", {
            "status": "FAILED_EXPLORATORY_FIXED_CHANNEL_TIME_REVIEW",
            "error_type": type(exc).__name__, "error": str(exc),
            "retry_authorized": False,
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic() - started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        })
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
