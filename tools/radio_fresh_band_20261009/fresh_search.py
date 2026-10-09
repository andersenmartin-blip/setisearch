"""Prospective exploratory search of one previously unopened native chunk.

Stationary and sparse drifting families are separate, bounded phases. Importing
this module opens no telescope values. No OFF veto or sky qualification exists.
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
import sys
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
ADJACENT = {
    "epoch1_on": ("epoch1_off",),
    "epoch2_on": ("epoch1_off", "epoch2_off"),
    "epoch3_on": ("epoch2_off", "epoch3_off"),
    "epoch1_off": ("epoch1_on", "epoch2_on"),
    "epoch2_off": ("epoch2_on", "epoch3_on"),
    "epoch3_off": ("epoch3_on",),
}
C0, COUNT, EDGE = 158334976, 1048576, 283
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
WIDTHS, HALO, TOP = (1, 3), 32, 20
CPU_CAPS = {"stationary": 60, "drift": 350, "profiles": 60}
WALL_CAP, MEMORY_CAP = 1800, 4 * 1024**3


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024**2), b""):
            h.update(b)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    temporary.replace(target)


def frequency(channel):
    return FCH1 + DF * int(channel)


def load_contract(args):
    scope = json.loads(Path(args.scope).read_text())
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Analysis helper differs from prospective freeze")
    for name, expected in scope["pinned_dependency_files"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen dependency differs: " + name)
    versions = {**scope["current_runtime_package_versions"], **scope["required_source_codec_versions"]}
    for name, expected in versions.items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("Runtime package differs from prospective freeze: " + name)
    expected = {
        "source_channel_interval_half_open": [C0, C0 + COUNT],
        "count": COUNT, "rows_per_scan": 16, "fch1_hz": FCH1, "df_hz": DF,
        "tsamp_s": TSAMP, "widths_channels": list(WIDTHS),
        "stationary_eligible_local_interval_half_open": [EDGE, COUNT - EDGE],
        "stationary_control_halfwidth_channels": HALO,
        "control_mapping": {k: list(v) for k, v in ADJACENT.items()},
        "drift_core_start_relative_channels": [(1 + 8*k)*4096 for k in range(32)],
        "drift_core_channel_count": 4096, "drift_crop_halo_channels": 4000,
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "CPU_caps_s": CPU_CAPS, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
        "rank_count": TOP, "profile_ranks_per_origin_and_family": 3,
        "profile_origin_labels": list(ONS), "expected_profile_count": 18,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
    }
    if any(scope.get(k) != v for k, v in expected.items()):
        raise ValueError("Declared analysis family differs from implemented choices")
    if digest(args.source_manifest) != args.source_manifest_sha256:
        raise ValueError("Source metadata hash differs from admitted value")
    if scope.get("source_manifest_sha256") != args.source_manifest_sha256:
        raise ValueError("Analysis freeze must pin the original prospective metadata")
    source = json.loads(Path(args.source_manifest).read_text())
    if [r["label"] for r in source["sources"]] != list(SCANS):
        raise ValueError("Exactly six chronologically selected scans required")
    if [r["role"].upper() for r in source["sources"]] != ["ON", "OFF"] * 3:
        raise ValueError("Original alternating scan roles required")
    previous_end = -math.inf
    anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
    for r in source["sources"]:
        h = r["current_header"]["data_attributes"]
        for observed, expected_value, tolerance in ((h["fch1"]*1e6, FCH1, 1e-6),
                (h["foff"]*1e6, DF, 1e-12), (h["tsamp"], TSAMP, 1e-12)):
            if not math.isclose(observed, expected_value, rel_tol=0, abs_tol=tolerance):
                raise ValueError("Actual header grid differs")
        start = (h["tstart"] - anchor)*86400
        if start < previous_end:
            raise ValueError("Scan sequence overlaps or is not chronological")
        previous_end = start + 16*TSAMP
    acquisition = json.loads(Path(args.acquisition_summary).read_text())
    if acquisition.get("status") != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY":
        raise ValueError("Complete acquisition is required")
    if acquisition.get("source_manifest_sha256") != scope["source_manifest_sha256"]:
        raise ValueError("Acquisition source pin differs")
    if acquisition.get("physical_channel_interval_half_open") != [C0, C0 + COUNT]:
        raise ValueError("Wrong native chunk acquisition")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or len({r["scan_id"] for r in decoded}) != 6:
        raise ValueError("Exactly six unique acquired compact H5 files required")
    if set(r["scan_id"] for r in decoded) != set(SCANS):
        raise ValueError("Incomplete or unexpected compact H5 scan set")
    return scope, source, acquisition, float(anchor)


def load_power(args, source, acquisition, labels=SCANS):
    import h5py
    import hdf5plugin  # Register exactly the existing source filter.
    records = {r["scan_id"]: r for r in acquisition["decoded_files"]}
    headers = {r["label"]: r for r in source["sources"]}
    arrays, verified = {}, {}
    for label in labels:
        record, item = records[label], headers[label]
        path = Path(args.compact_dir) / record["array_file"]
        sha = digest(path)
        if sha != record["file_sha256"]:
            raise ValueError("Compact file differs from acquisition receipt: " + label)
        with h5py.File(path, "r", rdcc_nbytes=8*1024**2) as handle:
            data = handle["data"]
            if data.shape != (16, 1, COUNT) or data.dtype != np.dtype("<f4"):
                raise ValueError("Incomplete compact data shape/type")
            if int(data.attrs["original_source_frequency_chunk_origin"]) != C0:
                raise ValueError("Absolute native source-channel offset was lost")
            if (data.attrs["original_source_url"] != item["url"] or
                    data.attrs["original_source_etag"] != item["etag"]):
                raise ValueError("Source identity attributes differ")
            arrays[label] = data[:, 0, :]
        if not np.isfinite(arrays[label]).all() or (arrays[label] < 0).any():
            raise ValueError("Complete finite nonnegative power is required")
        rows = record["decoded_rows"]
        if [r["time_row"] for r in rows] != list(range(16)):
            raise ValueError("Acquisition must retain every decoded row checksum")
        for i, row in enumerate(rows):
            if row["decoded_bytes"] != COUNT*4 or hashlib.sha256(arrays[label][i].tobytes()).hexdigest() != row["decoded_sha256"]:
                raise ValueError("Decoded row differs from acquisition checksum: " + label)
        verified[label] = {"path": record["array_file"], "file_sha256": sha, "bytes": path.stat().st_size}
        print("VERIFIED_FRESH_CHUNK", label, flush=True)
    return arrays, verified


def width_mean(x, width):
    if width == 1:
        return x
    p = np.pad(x, (1, 1), mode="edge")
    return (p[:-2] + p[1:-1] + p[2:]) / 3.0


def select_indices(values, eligible, suppression):
    order = eligible[np.lexsort((eligible, -values[eligible]))]
    selected = []
    for candidate in order:
        i = int(candidate)
        if all(abs(i - previous) > suppression for previous in selected):
            selected.append(i)
        if len(selected) == TOP:
            break
    return selected


def stationary(args, source, acquisition, anchor):
    from scipy.ndimage import median_filter, maximum_filter1d
    arrays, verified = load_power(args, source, acquisition)
    out = Path(args.outdir)
    spectra, row_medians, spectrum_files = {}, {}, {}
    for label in SCANS:
        p = arrays[label]
        medians = np.median(p, axis=1).astype(np.float64)
        if not np.isfinite(medians).all() or (medians <= 0).any():
            raise ValueError("Invalid full-chunk row normalization")
        normalized_mean = np.mean(p.astype(np.float64)/medians[:, None], axis=0)
        baseline = median_filter(normalized_mean, size=501, mode="nearest")
        if (baseline <= 0).any():
            raise ValueError("Invalid stationary running-median baseline")
        excess = normalized_mean/baseline - 1.0
        if not np.isfinite(excess).all():
            raise ValueError("Nonfinite stationary fractional excess")
        spectra[label], row_medians[label] = excess, medians
        path = out / (label + "_full_chunk_spectrum.npz")
        np.savez(path, row_normalized_mean_power=normalized_mean,
                 running_median_baseline=baseline, fractional_excess=excess,
                 row_power_medians=medians, source_channel0=C0,
                 source_channel_count=COUNT, df_hz=DF, fch1_hz=FCH1)
        spectrum_files[label] = {"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
    save(out / "NORMALIZATION.json", {"method": "median of all 1048576 native channels in each row",
            "row_power_medians": {k: v.tolist() for k, v in row_medians.items()},
            "spectrum_files": spectrum_files, "source_channel0": C0})
    del arrays
    smooth = {w: {s: width_mean(spectra[s], w) for s in SCANS} for w in WIDTHS}
    envelopes = {w: {s: maximum_filter1d(smooth[w][s], size=65, mode="nearest")
                    for s in SCANS} for w in WIDTHS}
    tops, score_files, summaries = {}, {}, {}
    eligible = np.arange(EDGE, COUNT - EDGE)
    for origin in SCANS:
        scores = {}
        for w in WIDTHS:
            controls = ADJACENT[origin]
            envelope = envelopes[w][controls[0]]
            if len(controls) == 2:
                envelope = np.maximum(envelope, envelopes[w][controls[1]])
            scores[w] = smooth[w][origin] - envelope
        maximum = np.maximum(scores[1], scores[3])
        winning = np.where(scores[3] > scores[1], 3, 1).astype(np.uint8)
        if not np.isfinite(maximum).all():
            raise ValueError("Nonfinite signed contrast array")
        path = out / (origin + "_stationary_signed_maps.npz")
        np.savez(path, D1=scores[1], D3=scores[3], maxD=maximum, winning_width=winning,
            source_channel0=C0, source_channel_count=COUNT, df_hz=DF, fch1_hz=FCH1,
            eligible_local_index0=EDGE, eligible_local_index_stop=COUNT - EDGE)
        score_files[origin] = {"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
        ranks = []
        for rank, i in enumerate(select_indices(maximum, eligible, 32), 1):
            w = int(winning[i])
            controls = {}
            for s in ADJACENT[origin]:
                segment = smooth[w][s][i-HALO:i+HALO+1]
                tied = np.flatnonzero(segment == segment.max()) + i-HALO
                best = int(tied[np.lexsort((tied, np.abs(tied-i)))][0])
                controls[s] = {"exact_frequency_fractional_excess": float(smooth[w][s][i]),
                    "neighborhood_maximum_fractional_excess": float(smooth[w][s][best]),
                    "witness_source_channel": C0+best, "witness_offset_channels": best-i}
            h = next(r["current_header"]["data_attributes"] for r in source["sources"] if r["label"] == origin)
            ranks.append({"track_id": origin + "_stationary_rank_%02d" % rank,
                "family": "stationary", "originating_scan": origin,
                "originating_role": "ON" if origin.endswith("_on") else "OFF",
                "display_rank": rank, "source_reference_channel": C0+i,
                "reference_frequency_hz": frequency(C0+i),
                "reference_seconds_from_anchor": (h["tstart"]-anchor)*86400+.5*TSAMP,
                "drift_hz_s": 0.0, "width_channels": w,
                "signed_contrast_fractional_units": float(maximum[i]),
                "origin_fractional_excess_same_width": float(smooth[w][origin][i]),
                "adjacent_control_evidence": controls,
                "all_six_exact_frequency_fractional_excess_same_width": {s: float(smooth[w][s][i]) for s in SCANS},
                "status": "EXPLORATORY_RANK_UNCLASSIFIED"})
        tops[origin] = ranks
        summaries[origin] = {"eligible_carriers": len(eligible),
            "eligible_width_hypotheses": 2*len(eligible),
            "positive_maxD_carriers_descriptive_only": int(np.count_nonzero(maximum[eligible] > 0)),
            "largest_signed_contrast": float(maximum[eligible].max())}
        save(out / "STATIONARY_TOP20.json", tops)
        save(out / "STATIONARY_CHECKPOINT.json", {"completed_origins": list(tops),
             "score_files": score_files, "summaries": summaries, "complete": len(tops) == 6})
        print("COMPLETED_FRESH_STATIONARY", origin, summaries[origin], flush=True)
    return {"status": "COMPLETED_FRESH_EXPLORATORY_STATIONARY_AND_RECIPROCAL_CONTROLS",
        "verified_inputs": verified, "score_files": score_files, "spectrum_files": spectrum_files,
        "summaries": summaries, "eligible_carriers_per_origin": len(eligible),
        "eligible_channel_edge_bandwidth_hz": len(eligible)*abs(DF),
        "full_array_edges": "Numerical padding retained; excluded from eligible ranking",
        "score_definition": "width-mean fractional excess at origin minus greatest adjacent control width-mean within +/-32 channels",
        "fractional_excess_definition": "mean of full-chunk row-median normalized power / 501-channel running median - 1",
        "display_suppression_channels": 32, "control_mapping": ADJACENT}


def drift(args, source, acquisition, anchor):
    from pilot_engine_20261008.detector import Scan, Config, search_scan
    arrays, verified = load_power(args, source, acquisition, ONS)
    out = Path(args.outdir)
    cfg = Config(widths=WIDTHS)
    drifts = np.linspace(-4.0, 4.0, 763)
    dt = np.arange(16)*TSAMP
    mismatch = float((drifts[1]-drifts[0])*dt[-1]/(2*abs(DF)))
    if mismatch > .5 + 1e-12:
        raise ValueError("Drift-grid half mismatch exceeds half a native channel")
    all_results = {s: [] for s in ONS}
    receipts = []
    starts = [(1+8*k)*4096 for k in range(32)]
    for tile_index, core_relative in enumerate(starts):
        first, stop = C0+core_relative, C0+core_relative+4096
        crop0, cropstop = core_relative-4000, core_relative+4096+4000
        for label in ONS:
            item = next(r for r in source["sources"] if r["label"] == label)
            h = item["current_header"]["data_attributes"]
            scan = Scan(label, "ON", arrays[label][:, crop0:cropstop], h["tstart"], TSAMP,
                FCH1, DF, C0+crop0, np.arange(first, stop))
            frequencies = FCH1 + DF*np.arange(first, stop)
            result, _ = search_scan(scan, frequencies, dt, drifts, cfg)
            if not np.isfinite(result["maximum_robust_box_track_score"]).all():
                raise ValueError("Nonfinite drift maxima")
            if not np.all(result["valid_hypothesis_count"] == 1526):
                raise ValueError("Incomplete drifting family")
            numeric = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
            numeric["source_reference_channels"] = np.arange(first, stop)
            numeric["drift_grid_hz_s"] = drifts
            path = out / (label + "_tile_%02d_all_carriers.npz" % tile_index)
            np.savez(path, **numeric)
            meta = {"scan_id": label, "tile_index": tile_index,
                "reference_channel_interval_half_open": [first, stop], "searched_carriers": 4096,
                "valid_hypotheses_per_carrier": 1526, "path": path.name,
                "sha256": digest(path), "bytes": path.stat().st_size,
                "normalization": result["normalization"]}
            receipts.append(meta)
            all_results[label].append(result)
            save(out / "DRIFT_CHECKPOINT.json", {"completed_scan_tiles": len(receipts),
                "expected_scan_tiles": 96, "complete": len(receipts) == 96,
                "completed_receipts": receipts})
            print("COMPLETED_FRESH_DRIFT_TILE", label, tile_index, flush=True)
    tops = {}
    for label in ONS:
        results = all_results[label]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in results])
        winning_drift = np.concatenate([r["winning_drift_hz_s"] for r in results])
        winning_width = np.concatenate([r["winning_width_channels"] for r in results])
        channels = np.concatenate([np.arange(C0+x, C0+x+4096) for x in starts])
        order = np.lexsort((channels, -scores))
        chosen = []
        for j in order:
            j = int(j)
            if all(abs(int(channels[j])-int(channels[k])) > 3 for k in chosen):
                chosen.append(j)
            if len(chosen) == TOP:
                break
        h = next(r["current_header"]["data_attributes"] for r in source["sources"] if r["label"] == label)
        ref = (h["tstart"]-anchor)*86400+.5*TSAMP
        tops[label] = [{"track_id": label + "_drift_rank_%02d" % rank,
            "family": "drift", "originating_scan": label, "originating_role": "ON",
            "display_rank": rank, "source_reference_channel": int(channels[j]),
            "reference_frequency_hz": frequency(channels[j]), "reference_seconds_from_anchor": float(ref),
            "drift_hz_s": float(winning_drift[j]), "width_channels": int(winning_width[j]),
            "maximum_robust_box_track_score": float(scores[j]),
            "reference_core_tile": j//4096, "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
            for rank, j in enumerate(chosen, 1)]
    save(out / "DRIFT_TOP20.json", tops)
    return {"status": "COMPLETED_FRESH_EXPLORATORY_SPARSE_DRIFT_SEARCH",
        "verified_inputs": verified, "completed_scan_tiles": 96,
        "sparse_core_count": 32, "carriers_per_ON": 131072,
        "channel_edge_bandwidth_per_ON_hz": 131072*abs(DF),
        "native_chunk_fraction_searched": 131072/COUNT,
        "sparse_core_intervals_half_open": [[C0+x, C0+x+4096] for x in starts],
        "drift_grid_count": 763, "widths_channels": list(WIDTHS),
        "half_grid_mismatch_channels": mismatch, "display_suppression_channels": 3,
        "reference_time": "each ON's own first integration midpoint",
        "score_definition": "unchanged detector row-MAD standardized odd-box track sum / sqrt(Nrow*width)",
        "normalization": "each 4096-carrier static core, each row, with unchanged 501-channel filtering",
        "full_drift_band_search": False, "OFF_veto_applied": False}


def profile_plots(track, raw, normalized, centers, dt, row_medians, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    offsets = np.arange(-64, 65)
    flank = np.abs(offsets) > 3
    baseline = np.median(normalized[:, :, flank], axis=2)
    width, radius = track["width_channels"], track["width_channels"]//2
    center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
    residual = center - baseline
    mean_profile = np.mean(normalized-baseline[:, :, None], axis=1)
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), constrained_layout=True)
    ymin, ymax = min(0.0, float(residual.min())), max(0.0, float(residual.max()))
    margin = max((ymax-ymin)*.07, .002)
    for ax, label, values, times in zip(axes.flat, SCANS, residual, dt):
        ax.plot(times, values, marker="o", markersize=3, linewidth=.8)
        ax.axhline(0, color="black", linewidth=.6)
        ax.set_ylim(ymin-margin, ymax+margin)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Seconds from originating scan first midpoint")
        ax.set_ylabel("Row-normalized center minus fixed flank median")
        ax.grid(alpha=.2)
    fig.suptitle(track["track_id"] + ": all 16 rows, exact frozen track; descriptive only", fontsize=11)
    time_path = path.with_name(path.name + "_time.png")
    fig.savefig(time_path, dpi=105)
    plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
    for ax, label, values in zip(axes.flat, SCANS, mean_profile):
        ax.plot(offsets*DF, values, linewidth=.8)
        ax.axvline(0, color="black", linewidth=.6, linestyle="--")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Frequency offset from fixed predicted channel (Hz)")
        ax.set_ylabel("Mean row-normalized power minus each row's fixed flank")
        ax.grid(alpha=.2)
    fig.suptitle(track["track_id"] + ": track-aligned mean profiles; no frequency adjustment", fontsize=11)
    mean_path = path.with_name(path.name + "_mean.png")
    fig.savefig(mean_path, dpi=105)
    plt.close(fig)
    return center, baseline, residual, mean_profile, [time_path, mean_path]


def profiles(args, source, acquisition, anchor):
    arrays, verified = load_power(args, source, acquisition)
    stationary_dir, drift_dir = Path(args.stationary_dir), Path(args.drift_dir)
    normalization = json.loads((stationary_dir/"NORMALIZATION.json").read_text())
    if normalization["source_channel0"] != C0:
        raise ValueError("Wrong fixed full-chunk normalization")
    row_medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS])
    if row_medians.shape != (6, 16) or not np.isfinite(row_medians).all() or (row_medians <= 0).any():
        raise ValueError("Invalid retained normalization")
    ranks = []
    for directory, name in ((stationary_dir, "STATIONARY_TOP20.json"), (drift_dir, "DRIFT_TOP20.json")):
        tops = json.loads((directory/name).read_text())
        expected_origins = SCANS if name == "STATIONARY_TOP20.json" else ONS
        if set(tops) != set(expected_origins) or any(len(tops[s]) != 20 for s in expected_origins):
            raise ValueError("Complete original top20 rank families are required")
        for origin in ONS:
            ranks.extend(tops[origin][:3])
    if len(ranks) != 18:
        raise ValueError("Exactly eighteen frozen ON-origin profile cases are required")
    headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
    out, records = Path(args.outdir), []
    for track in ranks:
        dt = np.asarray([(headers[s]["tstart"]-anchor)*86400 + (np.arange(16)+.5)*TSAMP
              - track["reference_seconds_from_anchor"] for s in SCANS])
        base = (track["reference_frequency_hz"]-FCH1)/DF
        centers = np.rint(base + track["drift_hz_s"]*dt/DF).astype(np.int64)
        indices = centers[:, :, None]-C0+np.arange(-64, 65)[None, None, :]
        if indices.min() < 0 or indices.max() >= COUNT:
            raise ValueError("A fixed six-scan prediction exceeds acquired native chunk")
        raw = np.asarray([arrays[s][np.arange(16)[:, None], indices[i]] for i, s in enumerate(SCANS)])
        normalized = raw.astype(np.float64)/row_medians[:, :, None]
        stem = out/track["track_id"]
        center, baseline, residual, mean_profile, plot_paths = profile_plots(track, raw, normalized,
             centers, dt, row_medians, stem)
        patch_path = stem.with_suffix(".npz")
        np.savez(patch_path, raw_power=raw, row_normalized_power=normalized,
            saved_full_chunk_row_medians=row_medians, frozen_source_channel_centers=centers,
            source_channel_offsets=np.arange(-64, 65), times_seconds_from_reference=dt,
            center_row_normalized_power=center, fixed_flank_median_row_normalized_power=baseline,
            center_minus_flank_each_row=residual, mean_fixed_track_frequency_profile=mean_profile,
            scans=np.asarray(SCANS), df_hz=DF, source_channel0=C0,
            reference_frequency_hz=track["reference_frequency_hz"], drift_hz_s=track["drift_hz_s"],
            width_channels=track["width_channels"], fixed_source_channel_shift=0)
        records.append({"selected_track": track,
            "fixed_frequency_shift_channels": 0, "fixed_flank_offsets": "absolute channel offset > 3 within +/-64",
            "patch": {"path": patch_path.name, "sha256": digest(patch_path), "bytes": patch_path.stat().st_size},
            "plots": [{"path": p.name, "sha256": digest(p)} for p in plot_paths],
            "scan_profiles": [{"scan_id": s, "mean_center_minus_flank": float(residual[i].mean()),
                "median_center_minus_flank": float(np.median(residual[i])),
                "positive_rows": int(np.count_nonzero(residual[i] > 0)),
                "all_16_center_minus_flank_rows": residual[i].tolist(),
                "all_16_raw_width_mean_power": raw[i, :, 64-track["width_channels"]//2:65+track["width_channels"]//2].mean(axis=1).tolist(),
                "frozen_source_channel_centers": centers[i].tolist()} for i, s in enumerate(SCANS)],
            "classification": "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"})
        save(out/"FIXED_TOP3_PROFILES.json", records)
        print("COMPLETED_FRESH_FIXED_PROFILE", track["track_id"], flush=True)
    return {"status": "COMPLETED_FRESH_FIXED_TOP3_SIX_SCAN_PROFILES", "verified_inputs": verified,
        "profile_count": len(records), "plot_count": 2*len(records), "all_rows_retained": 16,
        "source_top20_sha256": {"stationary": digest(stationary_dir/"STATIONARY_TOP20.json"),
            "drift": digest(drift_dir/"DRIFT_TOP20.json")},
        "saved_normalization_sha256": digest(stationary_dir/"NORMALIZATION.json"),
        "shift_frequency_drift_width_optimization_applied": False,
        "raw_patch_alignment": "rounded absolute source channels along exact fixed selected track in each actual scan",
        "time_profile_units": "width-mean raw power/full-chunk row median minus fixed flank median",
        "mean_profile_units": "mean of track-aligned row-normalized power minus each row fixed flank median"}


def main():
    started = time.monotonic()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=list(CPU_CAPS), required=True)
    for flag in ("scope", "source-manifest", "source-manifest-sha256", "compact-dir", "acquisition-summary", "outdir"):
        p.add_argument("--" + flag, required=True)
    p.add_argument("--stationary-dir")
    p.add_argument("--drift-dir")
    args = p.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError("Fresh analysis bounded CPU/wall deadline reached")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAPS[args.phase], CPU_CAPS[args.phase]+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        global np
        import numpy as np
        scope, source, acquisition, anchor = load_contract(args)
        result = globals()[args.phase](args, source, acquisition, anchor)
        result.update({"phase": args.phase, "scope_sha256": digest(args.scope),
            "script_sha256": digest(__file__), "source_manifest_sha256": digest(args.source_manifest),
            "acquisition_summary_sha256": digest(args.acquisition_summary),
            "one_historical_visit": True, "qualified_sky_pilot": False, "OFF_veto_applied": False,
            "old_A_B_failure_statuses_changed": False, "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
            "new_telescope_HTTP_requests_during_analysis": 0, "MJD_anchor": anchor,
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            "limitations": ["Exploratory post-selection ranks across correlated channels, widths and drifts",
                "Robust scores and positive row counts are not probabilities or calibrated SNR",
                "One visit; the labels epoch1/2/3 denote scans, not separate visits",
                "OFF controls provide descriptive evidence without a qualified veto or sky-origin classification",
                "Drift coverage is exactly 32 separated 4096-channel cores; intervening carriers were not drift searched",
                "No barycentric correction, nonlinear tracks, other widths, injection recovery or false-alarm calibration"]})
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps(result, allow_nan=False), flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status": "INCOMPLETE_FRESH_EXPLORATORY_ANALYSIS",
            "phase": args.phase, "error_type": type(exc).__name__, "error": str(exc),
            "retry_authorized": False, "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
