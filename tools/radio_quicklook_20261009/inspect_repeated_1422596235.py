"""Inspect the frozen 1422.596235 MHz HIP98505 feature in cached data."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (30, 35))
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

import h5py
import hdf5plugin  # noqa: F401
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPECTED_HASHES = {
    "source_manifest": "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec",
    "normalization": "773a01afd658d0134a2f9b418350f915ffdc0b8690739279a4fd2723bc1be132",
    "broad_receipt": "866de0dd7a07f17c1678a23cf04d66640b7ee6c5f398756cb8d3bccf84168dd6",
}


def read_json(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frequency_hz(header, channel):
    return (header["fch1"] + header["foff"] * channel) * 1e6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start_wall, start_cpu = time.monotonic(), time.process_time()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("wall bound")))
    signal.alarm(180)

    scope_path = args.repo_root / "tools/radio_quicklook_20261009/repeated_1422596235_scope.json"
    triage_path = args.repo_root / "results/radio_quicklook_20261009/SIGNAL_TRIAGE.json"
    source_path = args.cache_root / "pilot_source_20261008/primary/source_manifest.json"
    norm_path = args.cache_root / "results/radio_quicklook_20261009/broad_inventory/normalization.json"
    broad_path = args.cache_root / "results/radio_quicklook_20261009/broad_inventory/BROAD_INVENTORY_RECEIPT.json"
    arrays_path = args.cache_root / "results/radio_quicklook_20261009/arrays"

    scope, scope_hash = read_json(scope_path)
    triage, triage_hash = read_json(triage_path)
    source, source_hash = read_json(source_path)
    norm, norm_hash = read_json(norm_path)
    broad, broad_hash = read_json(broad_path)
    if {"source_manifest": source_hash, "normalization": norm_hash, "broad_receipt": broad_hash} != EXPECTED_HASHES:
        raise ValueError("Cached evidence identity differs")
    groups = {group["group_id"]: group for group in triage["groups"]}
    selected = [groups[group_id] for group_id in scope["candidate_group_ids"]]
    if [group["representative"]["source_reference_channel"] for group in selected] != scope["candidate_representative_source_channels"]:
        raise ValueError("Frozen representatives differ")
    if any(group["representative"]["winning_drift_hz_s"] != 0 for group in selected):
        raise ValueError("Expected the saved repeated zero-drift family")
    if set(scope["candidate_group_ids"]) & set(triage["manual_review_flagged_group_ids"]):
        raise ValueError("Selected group was already a manual flag")

    args.output.mkdir(parents=True, exist_ok=False)
    lo, hi = scope["display_source_channel_interval_half_open"]
    signal_lo, signal_hi = scope["candidate_source_channel_interval_half_open"]
    flank_ranges = (
        tuple(scope["lower_flank_source_channel_interval_half_open"]),
        tuple(scope["upper_flank_source_channel_interval_half_open"]),
    )
    origin = scope["source_channel_origin"]
    source_index = {item["label"]: item for item in source["sources"]}
    if list(source_index) != scope["scan_ids_in_order"]:
        raise ValueError("Scan order differs")

    scans, rows, summaries, receipts = {}, [], [], []
    for scan_id in scope["scan_ids_in_order"]:
        item = source_index[scan_id]
        with h5py.File(arrays_path / f"{scan_id}.compact.h5", "r", rdcc_nbytes=80 * 1024**2) as handle:
            data = handle["data"]
            if (
                data.shape != (16, 1, 1048576)
                or data.dtype != np.dtype("<f4")
                or data.attrs["original_source_url"] != item["url"]
                or data.attrs["original_source_etag"] != item["etag"]
                or int(data.attrs["original_source_frequency_chunk_origin"]) != origin
            ):
                raise ValueError(f"Cached identity differs for {scan_id}")
            raw = np.asarray(data[:, 0, lo - origin:hi - origin], dtype="<f4")
        if raw.shape != (16, hi - lo) or not np.isfinite(raw).all() or (raw < 0).any():
            raise ValueError(f"Invalid narrow slice for {scan_id}")
        levels = np.asarray(norm["row_medians_over_full_physical_chunk"][scan_id], dtype=np.float64)
        excess = raw.astype(np.float64) / levels[:, None] - 1.0
        scans[scan_id] = excess
        receipts.append({
            "scan_id": scan_id,
            "selected_source_interval_half_open": [lo, hi],
            "application_powers_read": int(raw.size),
            "raw_slice_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
        })

        candidate = excess[:, signal_lo - lo:signal_hi - lo]
        flanks = np.concatenate([excess[:, a - lo:b - lo] for a, b in flank_ranges], axis=1)
        indices = np.argmax(candidate, axis=1)
        peaks = candidate[np.arange(16), indices]
        flank_medians = np.median(flanks, axis=1)
        channels = signal_lo + indices
        header = item["current_header"]["data_attributes"]
        for row in range(16):
            rows.append({
                "scan_id": scan_id,
                "role": item["role"].upper(),
                "time_row": row,
                "peak_source_channel": int(channels[row]),
                "peak_frequency_hz": frequency_hz(header, int(channels[row])),
                "peak_normalized_excess": float(peaks[row]),
                "adjacent_flank_median_normalized_excess": float(flank_medians[row]),
                "peak_minus_flank_median": float(peaks[row] - flank_medians[row]),
            })
        collapsed = np.median(candidate, axis=0)
        index = int(np.argmax(collapsed))
        summaries.append({
            "scan_id": scan_id,
            "role": item["role"].upper(),
            "median_row_peak_normalized_excess": float(np.median(peaks)),
            "median_row_adjacent_flank_normalized_excess": float(np.median(flank_medians)),
            "median_row_peak_minus_flank": float(np.median(peaks - flank_medians)),
            "minimum_row_peak_minus_flank": float(np.min(peaks - flank_medians)),
            "collapsed_median_peak_source_channel": signal_lo + index,
            "collapsed_median_peak_frequency_hz": frequency_hz(header, signal_lo + index),
            "collapsed_median_peak_normalized_excess": float(collapsed[index]),
        })

    csv_path = args.output / "ROW_PROFILES.csv"
    with csv_path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    header0 = source_index["epoch1_on"]["current_header"]["data_attributes"]
    frequencies = np.asarray([frequency_hz(header0, channel) / 1e6 for channel in range(lo, hi)])
    values = np.concatenate([array.ravel() for array in scans.values()])
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for axis, scan_id in zip(axes.flat, scope["scan_ids_in_order"]):
        item = source_index[scan_id]
        header = item["current_header"]["data_attributes"]
        t0 = (header["tstart"] - header0["tstart"]) * 86400
        image = axis.imshow(
            scans[scan_id], origin="lower", aspect="auto", interpolation="nearest",
            extent=[frequencies[0], frequencies[-1], t0, t0 + 16 * header["tsamp"]],
            cmap="magma", vmin=float(np.quantile(values, 0.05)), vmax=float(np.quantile(values, 0.995)),
        )
        axis.axvline(frequency_hz(header, 160066324) / 1e6, color="cyan", linewidth=0.8, label="1422.596235 MHz")
        axis.set_title(f"{scan_id} ({item['role'].upper()})")
        axis.set_xlabel("Frequency (MHz; descending channel axis)")
        axis.set_ylabel("Seconds from first ON start")
        axis.ticklabel_format(axis="x", useOffset=False, style="plain")
    axes.flat[0].legend(fontsize=7)
    fig.colorbar(image, ax=list(axes.flat), label="Cached power / saved row median - 1 (shared clipped scale)")
    fig.suptitle("HIP98505 repeated 1422.596235 MHz feature")
    figure_path = args.output / "repeated_1422596235.png"
    fig.savefig(figure_path, dpi=120)
    plt.close(fig)

    on = [item["median_row_peak_normalized_excess"] for item in summaries if item["role"] == "ON"]
    off = [item["median_row_peak_normalized_excess"] for item in summaries if item["role"] == "OFF"]
    disposition = (
        "NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED"
        if min(off) > 0 and max(off) >= min(on)
        else "NO_ON_EXCLUSIVITY_ESTABLISHED_ORIGIN_UNRESOLVED"
    )
    result = {
        "status": "COMPLETED_REPEATED_1422596235_SIX_SCAN_TIME_RESOLVED_INSPECTION",
        "disposition": disposition,
        "qualification": "Exploratory authentic-signal inspection; original A/B qualification remains FAIL_CLOSED.",
        "scope_sha256": scope_hash,
        "triage_sha256": triage_hash,
        "source_manifest_sha256": source_hash,
        "saved_row_normalization_sha256": norm_hash,
        "broad_receipt_sha256": broad_hash,
        "script_sha256": file_hash(Path(__file__)),
        "selection": scope["selection"],
        "candidate_group_ids": scope["candidate_group_ids"],
        "scan_summaries": summaries,
        "read_slices": receipts,
        "application_powers_read": sum(item["application_powers_read"] for item in receipts),
        "new_GETs": 0,
        "new_external_bytes": 0,
        "new_detector_scores": 0,
        "new_drift_or_width_trials": 0,
        "CPU_seconds_including_analysis_and_render": time.process_time() - start_cpu,
        "wall_seconds": time.monotonic() - start_wall,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "reservation_CPU_seconds": scope["reservation"]["CPU_seconds"],
        "no_reservation_refund": True,
        "limitations": [
            "All six scans are one historical visit, not independent-visit confirmation.",
            "The feature was selected from saved data; this is descriptive, not calibrated significance.",
            "Adjacent flanks are local display context, not a calibrated noise distribution.",
            "OFF response does not determine a terrestrial, instrumental, or celestial origin.",
        ],
    }
    result_path = args.output / "RESULT.json"
    with result_path.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    checksum_path = args.output / "SHA256SUMS"
    with checksum_path.open("x") as handle:
        for path in (result_path, csv_path, figure_path):
            handle.write(f"{file_hash(path)}  {path.name}\n")
    signal.alarm(0)
    print(json.dumps({
        "status": result["status"], "disposition": disposition,
        "CPU_seconds": result["CPU_seconds_including_analysis_and_render"],
        "wall_seconds": result["wall_seconds"],
    }))


if __name__ == "__main__":
    main()
