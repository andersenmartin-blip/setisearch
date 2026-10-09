"""Inspect two frozen HIP98505 features in the existing compact HDF5 cache."""

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
resource.setrlimit(resource.RLIMIT_CPU, (40, 45))
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frequency_hz(header, channel):
    return (header["fch1"] + header["foff"] * channel) * 1e6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started_wall, started_cpu = time.monotonic(), time.process_time()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("wall bound")))
    signal.alarm(180)

    scope_path = args.repo_root / "tools/radio_quicklook_20261009/remaining_features_scope.json"
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
    for feature in scope["features"]:
        selected = [groups[group_id] for group_id in feature["group_ids"]]
        if set(feature["group_ids"]) & set(triage["manual_review_flagged_group_ids"]):
            raise ValueError("Feature overlaps previous manual flag")
        signal_lo, signal_hi = feature["signal_source_channel_interval_half_open"]
        if any(not signal_lo <= group["representative"]["source_reference_channel"] < signal_hi for group in selected):
            raise ValueError("Saved representative is outside frozen signal band")

    args.output.mkdir(parents=True, exist_ok=False)
    source_index = {item["label"]: item for item in source["sources"]}
    if list(source_index) != scope["scan_ids_in_order"]:
        raise ValueError("Scan order differs")
    origin = scope["source_channel_origin"]
    arrays, receipts = {}, []
    for scan_id in scope["scan_ids_in_order"]:
        item = source_index[scan_id]
        arrays[scan_id] = {}
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
            levels = np.asarray(norm["row_medians_over_full_physical_chunk"][scan_id], dtype=np.float64)
            for feature in scope["features"]:
                lo, hi = feature["display_source_channel_interval_half_open"]
                raw = np.asarray(data[:, 0, lo - origin:hi - origin], dtype="<f4")
                if raw.shape != (16, hi - lo) or not np.isfinite(raw).all() or (raw < 0).any():
                    raise ValueError(f"Invalid slice for {scan_id}/{feature['feature_id']}")
                arrays[scan_id][feature["feature_id"]] = raw.astype(np.float64) / levels[:, None] - 1.0
                receipts.append({
                    "scan_id": scan_id, "feature_id": feature["feature_id"],
                    "selected_source_interval_half_open": [lo, hi],
                    "application_powers_read": int(raw.size),
                    "raw_slice_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
                })

    rows, summaries = [], []
    for feature in scope["features"]:
        fid = feature["feature_id"]
        lo, hi = feature["display_source_channel_interval_half_open"]
        signal_lo, signal_hi = feature["signal_source_channel_interval_half_open"]
        flanks = (
            tuple(feature["lower_flank_source_channel_interval_half_open"]),
            tuple(feature["upper_flank_source_channel_interval_half_open"]),
        )
        for scan_id in scope["scan_ids_in_order"]:
            item = source_index[scan_id]
            header = item["current_header"]["data_attributes"]
            displayed = arrays[scan_id][fid]
            candidate = displayed[:, signal_lo - lo:signal_hi - lo]
            context = np.concatenate([displayed[:, a - lo:b - lo] for a, b in flanks], axis=1)
            indices = np.argmax(candidate, axis=1)
            peaks = candidate[np.arange(16), indices]
            context_medians = np.median(context, axis=1)
            channels = signal_lo + indices
            for row in range(16):
                rows.append({
                    "feature_id": fid, "scan_id": scan_id, "role": item["role"].upper(), "time_row": row,
                    "peak_source_channel": int(channels[row]),
                    "peak_frequency_hz": frequency_hz(header, int(channels[row])),
                    "peak_normalized_excess": float(peaks[row]),
                    "adjacent_flank_median_normalized_excess": float(context_medians[row]),
                    "peak_minus_flank_median": float(peaks[row] - context_medians[row]),
                })
            collapsed = np.median(candidate, axis=0)
            index = int(np.argmax(collapsed))
            summaries.append({
                "feature_id": fid, "scan_id": scan_id, "role": item["role"].upper(),
                "median_row_peak_normalized_excess": float(np.median(peaks)),
                "median_row_peak_minus_flank": float(np.median(peaks - context_medians)),
                "minimum_row_peak_minus_flank": float(np.min(peaks - context_medians)),
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
    figures = []
    for feature in scope["features"]:
        fid = feature["feature_id"]
        lo, hi = feature["display_source_channel_interval_half_open"]
        frequency_axis = np.asarray([frequency_hz(header0, channel) / 1e6 for channel in range(lo, hi)])
        values = np.concatenate([arrays[scan_id][fid].ravel() for scan_id in scope["scan_ids_in_order"]])
        fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
        for axis, scan_id in zip(axes.flat, scope["scan_ids_in_order"]):
            item = source_index[scan_id]
            header = item["current_header"]["data_attributes"]
            t0 = (header["tstart"] - header0["tstart"]) * 86400
            image = axis.imshow(
                arrays[scan_id][fid], origin="lower", aspect="auto", interpolation="nearest",
                extent=[frequency_axis[0], frequency_axis[-1], t0, t0 + 16 * header["tsamp"]],
                cmap="magma", vmin=float(np.quantile(values, 0.05)), vmax=float(np.quantile(values, 0.995)),
            )
            marker = frequency_hz(header, feature["marker_source_channel"]) / 1e6
            axis.axvline(marker, color="cyan", linewidth=0.8, label=f"{marker:.6f} MHz")
            axis.set_title(f"{scan_id} ({item['role'].upper()})")
            axis.set_xlabel("Frequency (MHz; descending channel axis)")
            axis.set_ylabel("Seconds from first ON start")
            axis.ticklabel_format(axis="x", useOffset=False, style="plain")
        axes.flat[0].legend(fontsize=7)
        fig.colorbar(image, ax=list(axes.flat), label="Cached power / saved row median - 1 (shared clipped scale)")
        fig.suptitle(f"HIP98505 {fid}")
        figure_path = args.output / f"{fid}.png"
        fig.savefig(figure_path, dpi=120)
        plt.close(fig)
        figures.append(figure_path)

    dispositions = {}
    for feature in scope["features"]:
        subset = [item for item in summaries if item["feature_id"] == feature["feature_id"]]
        on = [item["median_row_peak_normalized_excess"] for item in subset if item["role"] == "ON"]
        off = [item["median_row_peak_normalized_excess"] for item in subset if item["role"] == "OFF"]
        dispositions[feature["feature_id"]] = (
            "NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED"
            if min(off) > 0 and max(off) >= min(on)
            else "NO_ON_EXCLUSIVITY_ESTABLISHED_ORIGIN_UNRESOLVED"
        )
    result = {
        "status": "COMPLETED_TWO_REMAINING_PRIORITIZED_FEATURES_SIX_SCAN_TIME_RESOLVED_INSPECTION",
        "dispositions": dispositions,
        "qualification": "Exploratory authentic-signal inspection; original A/B qualification remains FAIL_CLOSED.",
        "scope_sha256": scope_hash, "triage_sha256": triage_hash,
        "source_manifest_sha256": source_hash, "saved_row_normalization_sha256": norm_hash,
        "broad_receipt_sha256": broad_hash, "script_sha256": digest(Path(__file__)),
        "scan_summaries": summaries, "read_slices": receipts,
        "application_powers_read": sum(item["application_powers_read"] for item in receipts),
        "new_GETs": 0, "new_external_bytes": 0, "new_detector_scores": 0, "new_drift_or_width_trials": 0,
        "CPU_seconds_including_analysis_and_render": time.process_time() - started_cpu,
        "wall_seconds": time.monotonic() - started_wall,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "reservation_CPU_seconds": scope["reservation"]["CPU_seconds"], "no_reservation_refund": True,
        "limitations": [
            "All scans are one historical visit; neither feature has independent-visit confirmation.",
            "Features were selected from saved data; results are descriptive, not calibrated significance.",
            "Adjacent flanks are local context, not a calibrated noise distribution.",
            "OFF response does not determine physical origin."
        ],
    }
    result_path = args.output / "RESULT.json"
    with result_path.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    checksum_path = args.output / "SHA256SUMS"
    with checksum_path.open("x") as handle:
        for path in (result_path, csv_path, *figures):
            handle.write(f"{digest(path)}  {path.name}\n")
    signal.alarm(0)
    print(json.dumps({
        "status": result["status"], "dispositions": dispositions,
        "CPU_seconds": result["CPU_seconds_including_analysis_and_render"], "wall_seconds": result["wall_seconds"]
    }))


if __name__ == "__main__":
    main()
