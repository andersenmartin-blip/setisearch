"""Separate exploratory zero-drift inventory of already acquired source chunk152.

No GETs, qualification, calibrated SNR or drift-complete sensitivity. Inputs:
--source-manifest original metadata JSON; --arrays-dir completed acquisition
with six <scan_id>.compact.h5 and acquisition_summary.json; --outdir new dir.
Outputs: six full-column spectra NPZ, row normalization JSON, ON top20 JSON,
up to18 six-scan fixed-frequency PNG, complete receipt or preserved failure.
Frozen choices: all1048576 columns/16rows, row-median division, collapsed
median501 baseline, residual median/MAD, display NMS32 and edge margin250,
top6 perON waterfall halfwidth512, common raw/row-median color scale0.6..1.6.
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
import numpy as np
from scipy.ndimage import median_filter
import h5py
import hdf5plugin  # Registers the supported bitshuffle/LZ4 decoder.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHANNEL0, COUNT, ROWS = 159383552, 1048576, 16
SOURCE_SHA256 = "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for body in iter(lambda: f.read(1024 * 1024), b""):
            h.update(body)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def peaks(z):
    chosen = []
    eligible = np.arange(250, COUNT - 250)
    order = eligible[np.lexsort((eligible, -z[eligible]))]
    for i in order:
        index = int(i)
        if all(abs(index - previous) > 32 for previous in chosen):
            chosen.append(index)
        if len(chosen) == 20:
            break
    return chosen


def inspect_file(path, item, requests):
    with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
        data = handle["data"]
        if data.shape != (ROWS, 1, COUNT) or data.dtype != np.dtype("<f4") or data.chunks != (1, 1, COUNT):
            raise ValueError("Unexpected complete physical chunk geometry/type")
        original = item["current_header"]["hdf5_filters"][0]
        actual = data.id.get_create_plist().get_filter(0)
        if data.id.get_create_plist().get_nfilters() != 1 or actual[:2] != tuple(original[:2]) or tuple(actual[2][2:]) != tuple(original[2][2:]):
            raise ValueError("Compact-file filter semantics differ from source")
        for chunk in item["chunks"]:
            row = chunk["time_row"]
            receipt = requests[(item["label"], row)]
            mask, body = data.id.read_direct_chunk((row, 0, 0))
            if (mask != 0 or len(body) != chunk["stored_size"] or
                    receipt["request_range"] != chunk["byte_range"] or
                    receipt["expected_etag"] != item["etag"] or
                    receipt["status"] != "EXACT_SOURCE_RANGE_RECEIVED" or
                    hashlib.sha256(body).hexdigest() != receipt["raw_sha256"] or
                    receipt.get("compact_raw_roundtrip_sha256") != receipt["raw_sha256"]):
                raise ValueError("Stored compressed chunk does not match original received payload")


def plot_fixed(items, arrays, row_levels, anchor, peak, path):
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    center = peak["source_channel"] - CHANNEL0
    lo, hi = max(0, center - 512), min(COUNT, center + 513)
    image = None
    for ax, item in zip(axes.flat, items):
        label = item["label"]
        h = item["current_header"]["data_attributes"]
        with h5py.File(arrays / f"{label}.compact.h5", "r", rdcc_nbytes=8 * 1024**2) as handle:
            power = np.asarray(handle["data"][:, 0, lo:hi], dtype=np.float64)
        normalized = power / np.asarray(row_levels[label])[:, None]
        f0 = h["fch1"] + h["foff"] * (CHANNEL0 + lo - .5)
        f1 = h["fch1"] + h["foff"] * (CHANNEL0 + hi - .5)
        t0 = (h["tstart"] - anchor) * 86400
        image = ax.imshow(normalized, aspect="auto", origin="lower", interpolation="nearest",
                          extent=[f0, f1, t0, t0 + ROWS * h["tsamp"]],
                          vmin=.6, vmax=1.6, cmap="magma")
        ax.axvline(peak["frequency_mhz"], color="cyan", linewidth=.8)
        ax.set_title(f"{label} ({item['role'].upper()})", fontsize=10)
        ax.set_xlabel("Absolute frequency (MHz)")
        ax.ticklabel_format(axis="x", style="plain", useOffset=False)
        ax.set_ylabel("Seconds from MJD anchor")
    fig.colorbar(image, ax=list(axes.flat), label="Raw power / full-chunk row median (shared clipped scale)")
    fig.suptitle(f"{peak['peak_id']}: zero-drift ranked spectral peak; not a detection\nMJD anchor {anchor:.12f}", fontsize=11)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def inventory(args):
    out, arrays = Path(args.outdir), Path(args.arrays_dir)
    start, cpu = time.monotonic(), time.process_time()
    source_path = Path(args.source_manifest)
    if digest(source_path) != SOURCE_SHA256:
        raise ValueError("Original metadata manifest differs from the pinned source")
    source = json.loads(source_path.read_text())
    summary_path = arrays / "acquisition_summary.json"
    acquired = json.loads(summary_path.read_text())
    if acquired["status"] != "SIX_SCANS_ACQUIRED_EXPLORATORY_ONLY":
        raise ValueError("Original bounded acquisition is not complete")
    items = source["sources"]
    requests = {(r["scan_id"], int(r["time_row"])): r for r in acquired["value_read_requests"]}
    if len(items) != 6 or len(requests) != 96 or len(acquired["value_read_requests"]) != 96:
        raise ValueError("Six sources / exactly96 original range receipts required")
    if [x["role"].upper() for x in items] != ["ON", "OFF"] * 3:
        raise ValueError("Original alternating source sequence changed")
    row_levels, tops, file_hashes, scan_receipts, selected = {}, {}, {}, [], []
    anchor = min(x["current_header"]["data_attributes"]["tstart"] for x in items)
    for item in items:
        label = item["label"]
        path = arrays / f"{label}.compact.h5"
        inspect_file(path, item, requests)
        file_hashes[label] = digest(path)
        with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
            power = np.asarray(handle["data"][:, 0, :], dtype=np.float64)
        if not np.isfinite(power).all() or (power < 0).any():
            raise ValueError(f"{label}: full physical chunk contains invalid powers")
        levels = np.median(power, axis=1)
        if not np.isfinite(levels).all() or (levels <= 0).any():
            raise ValueError("Invalid full-chunk row median")
        row_levels[label] = levels.tolist()
        power /= levels[:, None]
        mean = power.mean(axis=0)
        del power
        baseline = median_filter(mean, size=501, mode="nearest")
        residual = mean - baseline
        location = float(np.median(residual))
        scale = float(1.4826 * np.median(np.abs(residual - location)))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid global collapsed-spectrum residual MAD")
        z = (residual - location) / scale
        np.savez_compressed(out / f"{label}_full_chunk_spectrum.npz",
                            row_normalized_mean_power=mean, running_median_baseline=baseline,
                            robust_collapsed_residual_units=z, row_power_medians=levels,
                            residual_location=location, residual_MAD_scale=scale,
                            source_channel0=CHANNEL0, source_channel_count=COUNT)
        h = item["current_header"]["data_attributes"]
        info = {"scan_id": label, "role": item["role"].upper(), "complete_rows": ROWS,
                "column_count": COUNT, "finite_nonnegative_powers_checked": ROWS * COUNT,
                "channel_edge_band_width_hz": COUNT * abs(h["foff"]) * 1e6,
                "first_channel_center_mhz": h["fch1"] + h["foff"] * CHANNEL0,
                "last_channel_center_mhz": h["fch1"] + h["foff"] * (CHANNEL0 + COUNT - 1),
                "integration_exposure_seconds": ROWS * h["tsamp"],
                "collapsed_residual_location": location, "collapsed_residual_MAD_scale": scale}
        scan_receipts.append(info)
        if item["role"].upper() == "ON":
            top = []
            for rank, index in enumerate(peaks(z), 1):
                peak = {"peak_id": f"{label}_broad_rank_{rank:02d}", "originating_scan": label,
                        "display_rank": rank, "source_channel": CHANNEL0 + index,
                        "frequency_mhz": h["fch1"] + h["foff"] * (CHANNEL0 + index),
                        "robust_collapsed_residual_units": float(z[index]),
                        "row_normalized_mean_power": float(mean[index]),
                        "status": "EXPLORATORY_ZERO_DRIFT_RANKED_PEAK_UNCLASSIFIED"}
                top.append(peak)
                if rank <= 6:
                    selected.append(peak)
            tops[label] = top
        save(out / "normalization.json", {"row_medians_over_full_physical_chunk": row_levels})
        save(out / "top20_per_on.json", tops)
        save(out / "scan_inventory.json", scan_receipts)
        print("INVENTORIED", label, COUNT, "columns", flush=True)
    for peak in selected:
        plot_fixed(items, arrays, row_levels, anchor, peak, out / f"{peak['peak_id']}.png")
    receipt = {"status": "COMPLETED_EXPLORATORY_BROAD_ZERO_DRIFT_INVENTORY",
               "source_manifest_sha256": SOURCE_SHA256, "acquisition_summary_sha256": digest(summary_path),
               "script_sha256": digest(__file__), "original_compact_file_sha256": file_hashes,
               "all96_local_compressed_chunk_hashes_matched_received_source_payloads": True,
               "new_HTTP_requests": 0, "new_external_source_bytes": 0,
               "new_full_chunk_local_decodes": 6, "total_source_powers_checked": 6 * ROWS * COUNT,
               "MJD_anchor": anchor, "physical_source_channel_interval_half_open": [CHANNEL0, CHANNEL0 + COUNT],
               "scan_inventory": scan_receipts, "complete_drift_search": False,
               "qualification_or_OFF_veto": False, "calibrated_SNR_FAP_flux_EIRP": False,
               "old_failures_reclassified": False, "independent_observing_visits": 1,
               "display_NMS_source_channels": 32, "display_edge_margin_channels": 250,
               "fixed_frequency_waterfall_halfwidth_channels": 512, "waterfall_count": len(selected),
               "limitations": ["Only the zero-drift full-time projection is inventoried",
                               "Drifting, short-duration or broad signals may be suppressed or missed",
                               "Ranked peaks and residual units have uncalibrated significance",
                               "One historical visit; no discovery or qualified sky-null conclusion"],
               "analysis_wall_seconds": time.monotonic() - start,
               "analysis_CPU_seconds": time.process_time() - cpu,
               "process_CPU_seconds_including_imports": time.process_time(),
               "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    save(out / "BROAD_INVENTORY_RECEIPT.json", receipt)
    print(json.dumps(receipt, allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-manifest", "arrays-dir", "outdir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CPU, (200, 205))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError("Broad inventory wall limit")
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(600)
    try:
        inventory(args)
    except BaseException as exc:
        save(Path(args.outdir) / "BROAD_INVENTORY_FAILURE.json", {"status": "FAILED_EXPLORATORY_BROAD_INVENTORY",
             "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
