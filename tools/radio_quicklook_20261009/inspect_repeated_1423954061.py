"""Inspect one prospectively frozen repeated HIP98505 feature in cached data."""

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
import hdf5plugin  # noqa: F401 - registers the cached HDF5 codec
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


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def channel_frequency_hz(header, source_channel):
    return (header["fch1"] + header["foff"] * source_channel) * 1e6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started_wall = time.monotonic()
    started_cpu = time.process_time()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("wall bound")))
    signal.alarm(180)

    scope_path = args.repo_root / "tools/radio_quicklook_20261009/repeated_1423954061_scope.json"
    triage_path = args.repo_root / "results/radio_quicklook_20261009/SIGNAL_TRIAGE.json"
    source_path = args.cache_root / "pilot_source_20261008/primary/source_manifest.json"
    normalization_path = args.cache_root / "results/radio_quicklook_20261009/broad_inventory/normalization.json"
    broad_path = args.cache_root / "results/radio_quicklook_20261009/broad_inventory/BROAD_INVENTORY_RECEIPT.json"
    arrays_path = args.cache_root / "results/radio_quicklook_20261009/arrays"

    scope, scope_hash = read_json(scope_path)
    triage, triage_hash = read_json(triage_path)
    source, source_hash = read_json(source_path)
    normalization, normalization_hash = read_json(normalization_path)
    broad, broad_hash = read_json(broad_path)
    observed_hashes = {
        "source_manifest": source_hash,
        "normalization": normalization_hash,
        "broad_receipt": broad_hash,
    }
    if observed_hashes != EXPECTED_HASHES:
        raise ValueError(f"Cached evidence identity differs: {observed_hashes}")
    if triage["status"] != "COMPLETED_SAVED_MAXIMA_DESCRIPTIVE_TRIAGE":
        raise ValueError("Expected completed saved-maxima triage")
    if set(scope["candidate_group_ids"]) & set(triage["manual_review_flagged_group_ids"]):
        raise ValueError("Candidate overlaps an already reviewed manual flag")

    group_index = {group["group_id"]: group for group in triage["groups"]}
    candidates = [group_index[group_id] for group_id in scope["candidate_group_ids"]]
    controls = [group_index[group_id] for group_id in scope["control_group_ids"]]
    for group in candidates:
        if group["representative"]["source_reference_channel"] != scope["candidate_representative_source_channel"]:
            raise ValueError("Candidate representatives do not agree")
    for group in controls:
        if group["representative"]["source_reference_channel"] not in (282 + 159587000, 283 + 159587000):
            raise ValueError("Control representative differs")

    unreviewed = [
        group for group in triage["groups"]
        if group["group_id"] not in set(triage["manual_review_flagged_group_ids"])
        and group["maximum_OFF_saved_projection_units"] > 0
    ]
    ratio_order = sorted(
        unreviewed,
        key=lambda group: group["representative"]["maximum_saved_score"] / group["maximum_OFF_saved_projection_units"],
        reverse=True,
    )
    selected_rank = next(
        index + 1 for index, group in enumerate(ratio_order)
        if group["group_id"] == "epoch2_on_contiguous_0005"
    )

    args.output.mkdir(parents=True, exist_ok=False)
    lo, hi = scope["display_source_channel_interval_half_open"]
    candidate_lo, candidate_hi = scope["candidate_source_channel_interval_half_open"]
    control_lo, control_hi = scope["control_source_channel_interval_half_open"]
    origin = scope["source_channel_origin"]
    source_index = {item["label"]: item for item in source["sources"]}
    if list(source_index) != scope["scan_ids_in_order"]:
        raise ValueError("Source scan order differs from frozen scope")

    scans = {}
    read_receipts = []
    row_records = []
    summary_records = []
    for scan_id in scope["scan_ids_in_order"]:
        item = source_index[scan_id]
        compact_path = arrays_path / f"{scan_id}.compact.h5"
        with h5py.File(compact_path, "r", rdcc_nbytes=80 * 1024**2) as handle:
            data = handle["data"]
            if (
                data.shape != (16, 1, 1048576)
                or data.dtype != np.dtype("<f4")
                or data.attrs["original_source_url"] != item["url"]
                or data.attrs["original_source_etag"] != item["etag"]
                or int(data.attrs["original_source_frequency_chunk_origin"]) != origin
            ):
                raise ValueError(f"Cached source geometry/identity differs for {scan_id}")
            raw = np.asarray(data[:, 0, lo - origin:hi - origin], dtype="<f4")
        if raw.shape != (16, hi - lo) or not np.isfinite(raw).all() or (raw < 0).any():
            raise ValueError(f"Invalid narrow cached slice for {scan_id}")
        levels = np.asarray(normalization["row_medians_over_full_physical_chunk"][scan_id], dtype=np.float64)
        normalized_excess = raw.astype(np.float64) / levels[:, None] - 1.0
        scans[scan_id] = normalized_excess
        read_receipts.append({
            "scan_id": scan_id,
            "selected_source_interval_half_open": [lo, hi],
            "application_powers_read": int(raw.size),
            "raw_slice_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
        })

        header = item["current_header"]["data_attributes"]
        for band_name, band_lo, band_hi in (
            ("candidate", candidate_lo, candidate_hi),
            ("control", control_lo, control_hi),
        ):
            band = normalized_excess[:, band_lo - lo:band_hi - lo]
            peak_indices = np.argmax(band, axis=1)
            peak_values = band[np.arange(16), peak_indices]
            peak_channels = peak_indices + band_lo
            for row in range(16):
                row_records.append({
                    "scan_id": scan_id,
                    "role": item["role"].upper(),
                    "time_row": row,
                    "band": band_name,
                    "peak_source_channel": int(peak_channels[row]),
                    "peak_frequency_hz": channel_frequency_hz(header, int(peak_channels[row])),
                    "peak_normalized_excess": float(peak_values[row]),
                })
            collapsed = np.median(band, axis=0)
            collapsed_index = int(np.argmax(collapsed))
            summary_records.append({
                "scan_id": scan_id,
                "role": item["role"].upper(),
                "band": band_name,
                "median_row_peak_normalized_excess": float(np.median(peak_values)),
                "minimum_row_peak_normalized_excess": float(np.min(peak_values)),
                "maximum_row_peak_normalized_excess": float(np.max(peak_values)),
                "collapsed_median_peak_source_channel": band_lo + collapsed_index,
                "collapsed_median_peak_frequency_hz": channel_frequency_hz(header, band_lo + collapsed_index),
                "collapsed_median_peak_normalized_excess": float(collapsed[collapsed_index]),
            })

    csv_path = args.output / "ROW_PROFILES.csv"
    with csv_path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row_records[0]))
        writer.writeheader()
        writer.writerows(row_records)

    reference_header = source_index["epoch1_on"]["current_header"]["data_attributes"]
    frequencies_mhz = np.array([channel_frequency_hz(reference_header, channel) for channel in range(lo, hi)]) / 1e6
    all_values = np.concatenate([value.ravel() for value in scans.values()])
    vmax = float(np.quantile(all_values, 0.995))
    vmin = float(np.quantile(all_values, 0.05))
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for axis, scan_id in zip(axes.flat, scope["scan_ids_in_order"]):
        item = source_index[scan_id]
        header = item["current_header"]["data_attributes"]
        t0 = (header["tstart"] - reference_header["tstart"]) * 86400
        image = axis.imshow(
            scans[scan_id], origin="lower", aspect="auto", interpolation="nearest",
            extent=[frequencies_mhz[0], frequencies_mhz[-1], t0, t0 + 16 * header["tsamp"]],
            cmap="magma", vmin=vmin, vmax=vmax,
        )
        candidate_frequency = channel_frequency_hz(header, scope["candidate_representative_source_channel"]) / 1e6
        control_frequency = channel_frequency_hz(header, scope["control_representative_source_channel"]) / 1e6
        axis.axvline(candidate_frequency, color="cyan", linewidth=0.8, label="1423.954061 MHz feature")
        axis.axvline(control_frequency, color="lime", linewidth=0.8, label="1423.954560 MHz control")
        axis.set_title(f"{scan_id} ({item['role'].upper()})")
        axis.set_xlabel("Frequency (MHz; descending channel axis)")
        axis.set_ylabel("Seconds from first ON start")
        axis.ticklabel_format(axis="x", useOffset=False, style="plain")
    axes.flat[0].legend(fontsize=7, loc="upper left")
    fig.colorbar(image, ax=list(axes.flat), label="Cached power / saved row median - 1 (shared clipped scale)")
    fig.suptitle("HIP98505 repeated 1423.954061 MHz feature and nearby stationary control")
    figure_path = args.output / "repeated_1423954061.png"
    fig.savefig(figure_path, dpi=120)
    plt.close(fig)

    candidate_summary = [record for record in summary_records if record["band"] == "candidate"]
    on_medians = [record["median_row_peak_normalized_excess"] for record in candidate_summary if record["role"] == "ON"]
    off_medians = [record["median_row_peak_normalized_excess"] for record in candidate_summary if record["role"] == "OFF"]
    conclusion = (
        "NO_ON_EXCLUSIVITY_STRONG_OFF_COUNTEREVIDENCE_ORIGIN_UNRESOLVED"
        if min(off_medians) > 0 and max(off_medians) >= min(on_medians)
        else "NO_ON_EXCLUSIVITY_ESTABLISHED_ORIGIN_UNRESOLVED"
    )
    candidate_frequency = channel_frequency_hz(reference_header, scope["candidate_representative_source_channel"])
    control_frequency = channel_frequency_hz(reference_header, scope["control_representative_source_channel"])
    record = {
        "status": "COMPLETED_REPEATED_1423954061_SIX_SCAN_TIME_RESOLVED_INSPECTION",
        "disposition": conclusion,
        "qualification": "Exploratory authentic-signal inspection; original A/B qualification remains FAIL_CLOSED.",
        "scope_sha256": scope_hash,
        "triage_sha256": triage_hash,
        "source_manifest_sha256": source_hash,
        "saved_row_normalization_sha256": normalization_hash,
        "broad_receipt_sha256": broad_hash,
        "script_sha256": sha256(Path(__file__)),
        "selection": {
            "exploratory_data_selected": True,
            "criterion": "Maximum saved ON score divided by maximum saved OFF projection among groups not already manually reviewed.",
            "selected_reference_group_id": "epoch2_on_contiguous_0005",
            "selected_rank": selected_rank,
            "selected_ratio": group_index["epoch2_on_contiguous_0005"]["representative"]["maximum_saved_score"] / group_index["epoch2_on_contiguous_0005"]["maximum_OFF_saved_projection_units"],
            "repeated_candidate_group_ids": scope["candidate_group_ids"],
        },
        "candidate_reference_frequency_hz": candidate_frequency,
        "control_reference_frequency_hz": control_frequency,
        "candidate_below_control_hz": control_frequency - candidate_frequency,
        "scan_summaries": summary_records,
        "read_slices": read_receipts,
        "application_powers_read": sum(item["application_powers_read"] for item in read_receipts),
        "new_GETs": 0,
        "new_external_bytes": 0,
        "new_detector_scores": 0,
        "new_drift_or_width_trials": 0,
        "CPU_seconds_including_analysis_and_render": time.process_time() - started_cpu,
        "wall_seconds": time.monotonic() - started_wall,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "reservation_CPU_seconds": scope["reservation"]["CPU_seconds"],
        "no_reservation_refund": True,
        "limitations": [
            "All six scans belong to one historical visit; this is not independent-visit confirmation.",
            "The feature was selected from saved data, so this inspection is descriptive and not a calibrated significance test.",
            "OFF response is counterevidence to ON exclusivity, not proof of terrestrial interference or any other physical origin.",
            "Saved optimized-track scores and these normalized narrow-slice powers have different statistics.",
        ],
    }
    result_path = args.output / "RESULT.json"
    with result_path.open("x") as handle:
        json.dump(record, handle, indent=2, allow_nan=False)
        handle.write("\n")

    checksum_path = args.output / "SHA256SUMS"
    with checksum_path.open("x") as handle:
        for path in (result_path, csv_path, figure_path):
            handle.write(f"{sha256(path)}  {path.name}\n")

    signal.alarm(0)
    print(json.dumps({
        "status": record["status"],
        "disposition": record["disposition"],
        "CPU_seconds": record["CPU_seconds_including_analysis_and_render"],
        "wall_seconds": record["wall_seconds"],
    }))


if __name__ == "__main__":
    main()
