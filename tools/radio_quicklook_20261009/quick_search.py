"""Bounded exploratory telescope quicklook; importing this file opens no data.

This separately frozen single-scan family preserves the old detector module.
It reuses only preprocess/search_scan; it does not call the old cadence
qualification, threshold gates, OFF veto or recovery evaluator. Scores are
empirical robust box-track statistics, never calibrated SNR/significance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pilot_engine_20261008.detector import Config, Scan, preprocess, search_scan

FAMILY = "EXPLORATORY_SINGLE_SCAN_WIDTH_1_3_NO_OFF_VETO"
VMIN, VMAX = -3.0, 10.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def box_arrays(z: np.ndarray, widths=(1, 3)) -> dict:
    prefix = np.zeros((z.shape[0], z.shape[1] + 1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    return {w: prefix[:, w:] - prefix[:, :-w] for w in widths}


def display_indices(scores: np.ndarray, count=20) -> list[int]:
    """Fixed display-only suppression within three reference carrier channels."""
    order = np.lexsort((np.arange(len(scores)), -scores))
    selected = []
    for index in order:
        i = int(index)
        if all(abs(i - j) > 3 for j in selected):
            selected.append(i)
        if len(selected) == count:
            break
    return selected


def fixed_witness(scan: Scan, boxes: dict, dt: np.ndarray, frequency: float,
                  drift: float, width: int) -> dict:
    base = (frequency - scan.fch1_hz) / scan.df_hz
    witnesses = []
    for shift in (-1, 0, 1):
        centers = np.rint(base + drift * dt / scan.df_hz + shift).astype(np.int64)
        local = centers - scan.source_channel0 - width // 2
        if local.min() < 250 or local.max() >= boxes[width].shape[1] - 250:
            raise ValueError(f"{scan.scan_id}: fixed witness lacks preprocessing halo")
        row_sum = boxes[width][np.arange(len(dt)), local]
        contribution = row_sum / math.sqrt(len(dt) * width)
        witnesses.append({"source_channel_shift": shift,
                          "robust_box_track_score": float(contribution.sum()),
                          "row_score_contributions": contribution.tolist(),
                          "source_channel_centers": centers.tolist()})
    best = max(witnesses, key=lambda x: x["robust_box_track_score"])
    positive = np.maximum(np.asarray(best["row_score_contributions"]), 0)
    total = float(positive.sum())
    concentration = {"definition": "fractions of positive row score contributions; descriptive, not event duration",
                     "largest_row_fraction": float(positive.max() / total) if total else None,
                     "largest_two_rows_fraction": float(np.sort(positive)[-2:].sum() / total) if total else None}
    return {"scan_id": scan.scan_id, "role": scan.role,
            "times_seconds_from_track_reference": dt.tolist(),
            "fixed_drift_hz_s": drift, "fixed_width_channels": width,
            "all_three_frequency_shifts": witnesses,
            "largest_of_three_shift_scores": best,
            "time_concentration": concentration,
            "used_for_veto_or_classification": False}


def waterfall(scans: list[Scan], z_arrays: dict, anchor: float,
              band: tuple[int, int], path: Path) -> None:
    fig, axes = plt.subplots(6, 1, figsize=(12, 13), constrained_layout=True)
    image = None
    for ax, scan in zip(axes, scans):
        lo, hi = (x - scan.source_channel0 for x in band)
        f0 = (scan.fch1_hz + scan.df_hz * (band[0] - .5)) / 1e6
        f1 = (scan.fch1_hz + scan.df_hz * (band[1] - .5)) / 1e6
        t0 = (scan.tstart_mjd - anchor) * 86400
        image = ax.imshow(z_arrays[scan.scan_id][:, lo:hi], aspect="auto", origin="lower",
                          interpolation="nearest", extent=[f0, f1, t0, t0 + 16 * scan.tsamp_s],
                          vmin=VMIN, vmax=VMAX, cmap="magma")
        ax.set_title(f"{scan.scan_id} ({scan.role}), actual observation times", fontsize=10)
        ax.set_ylabel("Seconds from anchor")
    axes[-1].set_xlabel("Absolute frequency (MHz); native channel order descends")
    fig.colorbar(image, ax=axes, label="Robust residual units (shared clipped scale; not SNR)")
    fig.suptitle(f"HD 189733: one historical visit; MJD anchor {anchor:.12f}")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def track_plot(scans: list[Scan], z_arrays: dict, anchor: float,
               track: dict, path: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    image = None
    for ax, scan in zip(axes.flat, scans):
        mids = (scan.tstart_mjd - anchor) * 86400 + (np.arange(16) + .5) * scan.tsamp_s
        dt = mids - track["reference_seconds_from_anchor"]
        predicted = track["reference_frequency_hz"] + track["drift_hz_s"] * dt
        source = (predicted - scan.fch1_hz) / scan.df_hz
        start = int(np.floor(source.min())) - 24
        stop = int(np.ceil(source.max())) + 25
        lo, hi = start - scan.source_channel0, stop - scan.source_channel0
        if lo < 0 or hi > scan.power.shape[1]:
            raise ValueError(f"{scan.scan_id}: track display exceeds acquired crop")
        f0 = (scan.fch1_hz + scan.df_hz * (start - .5)) / 1e6
        f1 = (scan.fch1_hz + scan.df_hz * (stop - .5)) / 1e6
        t0 = (scan.tstart_mjd - anchor) * 86400
        image = ax.imshow(z_arrays[scan.scan_id][:, lo:hi], aspect="auto", origin="lower",
                          interpolation="nearest", extent=[f0, f1, t0, t0 + 16 * scan.tsamp_s],
                          vmin=VMIN, vmax=VMAX, cmap="magma")
        ax.plot(predicted / 1e6, mids, color="cyan", linewidth=1.0, label="Fixed ON-predicted center")
        ax.set_title(f"{scan.scan_id} ({scan.role})", fontsize=10)
        ax.set_xlabel("Absolute frequency (MHz)")
        ax.ticklabel_format(axis="x", style="plain", useOffset=False)
        ax.set_ylabel("Seconds from MJD anchor")
    axes.flat[0].legend(fontsize=7)
    fig.colorbar(image, ax=list(axes.flat), label="Robust residual units (shared clipped scale; not SNR)")
    fig.suptitle(f"{track['track_id']}: {track['drift_hz_s']:.6f} Hz/s, width {track['width_channels']}\n"
                 f"Exploratory ranked track; no OFF veto; MJD anchor {anchor:.12f}", fontsize=11)
    fig.savefig(path, dpi=115)
    plt.close(fig)


def analyze(args) -> dict:
    out = Path(args.outdir)
    started = time.monotonic()
    scope = json.loads((ROOT / 'tools/radio_quicklook_20261009/scope.json').read_text())
    for name, expected in scope['pinned_files'].items():
        if sha256(ROOT / name) != expected:
            raise ValueError('Frozen code/source mismatch: ' + name)
    source_path = Path(args.source_manifest)
    source = json.loads(source_path.read_text())
    arrays_dir = Path(args.arrays_dir)
    acquisition_path = arrays_dir / "acquisition_summary.json"
    acquisition = json.loads(acquisition_path.read_text())
    if acquisition['status'] != 'SIX_SCANS_ACQUIRED_EXPLORATORY_ONLY':
        raise ValueError('Complete exploratory acquisition is required')
    channel0 = int(acquisition["source_channel0"])
    crop = tuple(map(int, acquisition["crop_channel_interval_half_open"]))
    if crop[0] != channel0 or crop != (159901792, 159913888):
        raise ValueError("Acquisition crop differs from the prospective quicklook crop")
    band = tuple(map(int, source["band"]["reference_channel_interval_half_open"]))
    if band != (159905792, 159909888):
        raise ValueError("Metadata-selected reference band changed")
    records = source["sources"]
    if len(records) != 6 or [r["role"].upper() for r in records] != ["ON", "OFF"] * 3:
        raise ValueError("Exactly the selected ordered six-scan cadence is required")
    decoded = {r["scan_id"]: r for r in acquisition["decoded_files"]}
    if set(decoded) != {r["label"] for r in records}:
        raise ValueError("Incomplete or unexpected acquired scan set")
    cfg = Config(widths=(1, 3))  # New frozen family; do not call the old Config.check().
    scans, z_arrays, boxes_by_scan, normalizations, input_hashes = [], {}, {}, {}, {}
    for record in records:
        label = record["label"]
        array_path = arrays_dir / f"{label}.npy"
        digest = sha256(array_path)
        expected = decoded[label].get("file_sha256", decoded[label].get("sha256"))
        if expected is None or digest != expected:
            raise ValueError(f"{label}: decoded array checksum absent or mismatched")
        power = np.load(array_path, allow_pickle=False)
        if power.shape != (16, crop[1] - crop[0]) or power.dtype != np.dtype("float32"):
            raise ValueError(f"{label}: wrong complete crop shape/type")
        expected_array = decoded[label].get("array_sha256")
        if expected_array is not None and hashlib.sha256(power.tobytes()).hexdigest() != expected_array:
            raise ValueError(f"{label}: decoded power checksum mismatched")
        h = record["current_header"]["data_attributes"]
        scan = Scan(label, record["role"].upper(), power, float(h["tstart"]), float(h["tsamp"]),
                    float(h["fch1"]) * 1e6, float(h["foff"]) * 1e6, channel0,
                    np.arange(band[0], band[1], dtype=np.int64))
        z, mask, normalization = preprocess(scan, cfg)
        if not mask.all():
            raise ValueError("Quicklook family expects complete unmasked arrays")
        scans.append(scan)
        z_arrays[label] = z
        boxes_by_scan[label] = box_arrays(z)
        normalizations[label] = {k: v for k, v in normalization.items() if k != "normalization_source_channels"}
        input_hashes[label] = digest
    anchor = min(s.tstart_mjd for s in scans)
    previous_end = -math.inf
    for scan in scans:
        start = (scan.tstart_mjd - anchor) * 86400
        if start < previous_end:
            raise ValueError("Scan sequence is not chronological or integrations overlap")
        previous_end = start + 16 * scan.tsamp_s
    write_json(out / "normalization.json", {"normalization_source_channel_interval_half_open": list(band),
               "normalization_source_channel_count": 4096, "per_scan": normalizations})
    waterfall(scans, z_arrays, anchor, band, out / "six_scan_waterfall.png")
    drifts = np.linspace(-4, 4, 763)
    tops, tracks, search_receipts = {}, [], []
    for scan in scans:
        if scan.role != "ON":
            continue
        times = np.arange(16) * scan.tsamp_s
        span = float(times[-1])
        mismatch = float((drifts[1] - drifts[0]) * span / (2 * abs(scan.df_hz)))
        if mismatch > .5 + 1e-12:
            raise ValueError("Single-scan half-grid mismatch exceeds half a native channel")
        frequencies = scan.fch1_hz + scan.df_hz * np.arange(band[0], band[1])
        result, _ = search_scan(scan, frequencies, times, drifts, cfg)
        expected_hypotheses = len(drifts) * len(cfg.widths)
        scores = result["maximum_robust_box_track_score"]
        if not np.isfinite(scores).all() or not np.all(result["valid_hypothesis_count"] == expected_hypotheses):
            raise ValueError(f"{scan.scan_id}: incomplete single-scan search")
        numeric = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
        numeric["source_reference_channels"] = np.arange(band[0], band[1])
        numeric["drift_grid_hz_s"] = drifts
        np.savez_compressed(out / f"{scan.scan_id}_all_carrier_maxima.npz", **numeric)
        ref = (scan.tstart_mjd - anchor) * 86400 + .5 * scan.tsamp_s
        top = []
        for rank, i in enumerate(display_indices(scores), 1):
            track = {"track_id": f"{scan.scan_id}_rank_{rank:02d}", "originating_scan": scan.scan_id,
                     "display_rank": rank, "source_reference_channel": band[0] + i,
                     "reference_frequency_hz": float(frequencies[i]),
                     "reference_seconds_from_anchor": float(ref),
                     "reference_mjd": float(anchor + ref / 86400),
                     "drift_hz_s": float(result["winning_drift_hz_s"][i]),
                     "width_channels": int(result["winning_width_channels"][i]),
                     "maximum_robust_box_track_score": float(scores[i]),
                     "status": "EXPLORATORY_RANKED_TRACK_UNCLASSIFIED"}
            top.append(track.copy())
            if rank <= 6:
                track["six_scan_fixed_track_witnesses"] = []
                for target in scans:
                    mids = (target.tstart_mjd - anchor) * 86400 + (np.arange(16) + .5) * target.tsamp_s
                    track["six_scan_fixed_track_witnesses"].append(fixed_witness(
                        target, boxes_by_scan[target.scan_id], mids - ref,
                        track["reference_frequency_hz"], track["drift_hz_s"], track["width_channels"]))
                track_plot(scans, z_arrays, anchor, track, out / f"{track['track_id']}.png")
                tracks.append(track)
        tops[scan.scan_id] = top
        search_receipts.append({"scan_id": scan.scan_id, "reference_mjd": float(anchor + ref / 86400),
                                "searched_native_carriers": len(scores), "drift_trials": len(drifts),
                                "hypotheses_per_carrier": expected_hypotheses,
                                "widths_channels": [1, 3], "drift_step_hz_s": float(drifts[1] - drifts[0]),
                                "scan_midpoint_span_s": span, "maximum_half_grid_mismatch_channels": mismatch,
                                "channel_edge_band_width_hz": float(len(scores) * abs(scan.df_hz)),
                                "scan_integration_exposure_s": 16 * scan.tsamp_s})
        write_json(out / "top20_per_on.json", tops)
        write_json(out / "selected_track_witnesses.json", tracks)
    receipt = {"status": "COMPLETED_EXPLORATORY_TELESCOPE_SIGNAL_QUICKLOOK", "family": FAMILY,
               "qualified_sky_pilot": False, "old_A_B_failures_reclassified": False,
               "OFF_veto_applied": False, "calibrated_SNR_FAP_flux_EIRP": False,
               "one_historical_visit": True, "mjd_anchor": anchor,
               "source_manifest_sha256": sha256(source_path),
               "acquisition_summary_sha256": sha256(acquisition_path),
               "decoded_array_sha256": input_hashes, "script_sha256": sha256(Path(__file__)),
               "reused_detector_sha256": sha256(ROOT / "pilot_engine_20261008/detector.py"),
               "searches": search_receipts, "display_track_count": sum(map(len, tops.values())),
               "fixed_track_inspection_count": len(tracks),
               "display_suppression": "within three reference channels; display only; all carrier maxima retained",
               "fixed_track_frequency_shift_choices": [-1, 0, 1],
               "plot_robust_residual_scale": {"vmin": VMIN, "vmax": VMAX, "shared": True, "not_SNR": True},
               "limitations": ["Uncalibrated exploratory statistic and selected ranked tracks",
                               "Single linear topocentric drift per track; no barycentric or curved-track model",
                               "Widths 1/3 only; other widths not searched",
                               "Per-ON reference band is defined at each scan's own first midpoint",
                               "Crossscan fixed predictions may miss variable or nonlinear emission",
                               "Scores/time concentration do not prove celestial origin or artifact duration",
                               "No OFF veto, detection classification, recovery/FAP qualification or sky null inference"],
               "analysis_function_wall_seconds_excluding_import_startup": time.monotonic() - started,
               "process_CPU_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
               "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    write_json(out / "SEARCH_RECEIPT.json", receipt)
    return receipt


def main() -> None:
    def deadline(signum, frame):
        raise TimeoutError('Exploratory search wall deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    resource.setrlimit(resource.RLIMIT_CPU, (500, 510))
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--arrays-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)
    try:
        receipt = analyze(args)
    except Exception as exc:
        out = Path(args.outdir)
        if out.is_dir() and not (out / "SEARCH_RECEIPT.json").exists():
            write_json(out / "SEARCH_FAILURE.json", {"status": "FAILED_EXPLORATORY_SEARCH",
                       "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False})
        raise
    print(json.dumps(receipt, allow_nan=False))


if __name__ == "__main__":
    main()
