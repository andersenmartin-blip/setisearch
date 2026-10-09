"""One bounded exploratory stationary contrast pass over saved six-scan spectra.

No telescope requests, source-chunk decoding, drift rescoring or qualification.
Scope must pin this script, the original manifest and six extracted NPZ hashes.
The ranking preserves each ON independently; OFF evidence is not a sky veto.
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
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = ("epoch1_on", "epoch2_on", "epoch3_on")
ADJACENT = {
    "epoch1_on": ("epoch1_off",),
    "epoch2_on": ("epoch1_off", "epoch2_off"),
    "epoch3_on": ("epoch2_off", "epoch3_off"),
}
CHANNEL0, COUNT = 159383552, 1048576
DF_HZ, FCH1_HZ = -2.835503418452676, 1876464843.75
SOURCE_SHA256 = "6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec"
WIDTHS, OFF_HALO, EDGE, NMS, TOP, PLOTS = (1, 3), 32, 283, 32, 20, 3
CPU_CAP, WALL_CAP, MEMORY_CAP = 45, 120, 1536 * 1024**2


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for body in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(body)
    return value.hexdigest()


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def frequency(index):
    return FCH1_HZ + DF_HZ * (CHANNEL0 + int(index))


def width_mean(values, width):
    if width == 1:
        return values
    # Nearest-end extension is numerical padding only. All selected indices
    # exclude the larger frozen EDGE margin, including the OFF witness halo.
    padded = np.pad(values, (1, 1), mode="edge")
    return (padded[:-2] + padded[1:-1] + padded[2:]) / 3.0


def load_inputs(args):
    scope_path, source_path = Path(args.scope), Path(args.source_manifest)
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Helper differs from frozen scope")
    if scope["source_manifest_sha256"] != SOURCE_SHA256 or digest(source_path) != SOURCE_SHA256:
        raise ValueError("Original source metadata pin differs")
    for key, expected in (("channel0", CHANNEL0), ("count", COUNT), ("df_hz", DF_HZ), ("fch1_hz", FCH1_HZ)):
        if scope[key] != expected:
            raise ValueError(f"Frozen scope grid differs: {key}")
    choices = {
        "widths_channels": list(WIDTHS),
        "eligible_relative_channel_interval_half_open": [EDGE, COUNT - EDGE],
        "adjacent_OFF_by_ON": {key: list(value) for key, value in ADJACENT.items()},
        "OFF_frequency_neighborhood_halfwidth_channels": OFF_HALO,
        "display_NMS_channels": NMS,
        "display_top_ranks_per_ON": TOP,
        "spectral_profile_plots_per_ON": PLOTS,
        "plot_halfwidth_channels": 128,
    }
    if any(scope.get(key) != value for key, value in choices.items()):
        raise ValueError("Scope and implemented comparison choices differ")
    limits = scope["limits"]
    if (limits["job_CPU_limit_s"], limits["job_wall_limit_s"], limits["job_memory_limit_bytes"]) != (CPU_CAP, WALL_CAP, MEMORY_CAP):
        raise ValueError("Scope and implemented job limits differ")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    items = source["sources"]
    if [item["label"] for item in items] != list(SCANS) or [item["role"].upper() for item in items] != ["ON", "OFF"] * 3:
        raise ValueError("Pinned source is not the original alternating six scans")
    for item in items:
        header = item["current_header"]["data_attributes"]
        if not math.isclose(header["fch1"] * 1e6, FCH1_HZ, rel_tol=0, abs_tol=1e-6) or not math.isclose(header["foff"] * 1e6, DF_HZ, rel_tol=0, abs_tol=1e-12):
            raise ValueError("A source scan has a different absolute frequency grid")
    expected_hashes = scope["spectra_sha256"]
    if set(expected_hashes) != set(SCANS):
        raise ValueError("Scope must pin exactly six NPZ spectra")
    spectra, old_on_z, normalization, verified = {}, {}, {}, {}
    for scan in SCANS:
        path = Path(args.spectra_dir) / f"{scan}_full_chunk_spectrum.npz"
        sha = digest(path)
        if sha != expected_hashes[scan]:
            raise ValueError(f"Saved spectrum differs from frozen member hash: {scan}")
        verified[scan] = {"archive_member": f"broad_inventory/{path.name}", "sha256": sha, "bytes": path.stat().st_size}
        with np.load(path, allow_pickle=False) as saved:
            if np.asarray(saved["source_channel0"]).shape != () or np.asarray(saved["source_channel_count"]).shape != ():
                raise ValueError("Saved spectrum grid is not scalar")
            if int(saved["source_channel0"]) != CHANNEL0 or int(saved["source_channel_count"]) != COUNT:
                raise ValueError("Saved spectrum has a different source grid")
            mean = np.asarray(saved["row_normalized_mean_power"], dtype=np.float64)
            baseline = np.asarray(saved["running_median_baseline"], dtype=np.float64)
            if mean.shape != (COUNT,) or baseline.shape != (COUNT,):
                raise ValueError("Saved mean/baseline length differs")
            if not np.isfinite(mean).all() or not np.isfinite(baseline).all() or (mean < 0).any() or (baseline <= 0).any():
                raise ValueError("Saved mean/baseline contains invalid values")
            excess = mean / baseline - 1.0
            if not np.isfinite(excess).all():
                raise ValueError("Fractional excess is not finite")
            spectra[scan] = excess
            if scan in ONS:
                z = np.asarray(saved["robust_collapsed_residual_units"], dtype=np.float64)
                if z.shape != (COUNT,) or not np.isfinite(z).all():
                    raise ValueError("Saved ON context spectrum contains invalid values")
                old_on_z[scan] = z
            normalization[scan] = {
                "residual_location": float(saved["residual_location"]),
                "residual_MAD_scale": float(saved["residual_MAD_scale"]),
                "row_power_medians": np.asarray(saved["row_power_medians"], dtype=np.float64).tolist(),
            }
        print("VERIFIED_SAVED_SPECTRUM", scan, flush=True)
    return scope, spectra, old_on_z, normalization, verified


def witness(values, center):
    lo, hi = center - OFF_HALO, center + OFF_HALO + 1
    segment = values[lo:hi]
    best = float(np.max(segment))
    # Deterministic ties: closest to selected frequency, then lower channel.
    tied = np.flatnonzero(segment == best) + lo
    index = int(tied[np.lexsort((tied, np.abs(tied - center)))][0])
    return {"source_channel": CHANNEL0 + index, "offset_channels": index - center,
            "frequency_hz": frequency(index), "offset_hz": DF_HZ * (index - center),
            "fractional_excess": best}


def ranked_tracks(on, maximum, winning, smooth, old_z):
    eligible = np.arange(EDGE, COUNT - EDGE)
    order = eligible[np.lexsort((eligible, -maximum[eligible]))]
    selected, indices = [], []
    for candidate in order:
        index = int(candidate)
        if any(abs(index - previous) <= NMS for previous in indices):
            continue
        width = int(winning[index])
        off = {scan: {"exact_frequency_fractional_excess": float(smooth[width][scan][index]),
                      "neighborhood_maximum": witness(smooth[width][scan], index)}
               for scan in ADJACENT[on]}
        selected.append({
            "ranked_id": f"{on}_contrast_rank_{len(selected) + 1:02d}",
            "originating_on": on, "display_rank": len(selected) + 1,
            "source_channel": CHANNEL0 + index, "frequency_hz": frequency(index),
            "frequency_mhz": frequency(index) / 1e6, "winning_width_channels": width,
            "signed_contrast_fractional_units": float(maximum[index]),
            "on_fractional_excess_same_width": float(smooth[width][on][index]),
            "adjacent_off_evidence": off,
            "original_width1_ON_collapsed_residual_units_context_only": float(old_z[index]),
            "all_six_exact_frequency_fractional_excess_same_width": {scan: float(smooth[width][scan][index]) for scan in SCANS},
            "status": "EXPLORATORY_STATIONARY_ON_OFF_CONTRAST_RANK_UNCLASSIFIED",
        })
        indices.append(index)
        if len(selected) == TOP:
            break
    return selected


def plot_profiles(record, smooth, path):
    center = record["source_channel"] - CHANNEL0
    width = record["winning_width_channels"]
    lo, hi = center - 128, center + 129
    offsets = DF_HZ * (np.arange(lo, hi) - center)
    profiles = {scan: smooth[width][scan][lo:hi] for scan in SCANS}
    smallest = min(float(np.min(values)) for values in profiles.values())
    largest = max(float(np.max(values)) for values in profiles.values())
    margin = max((largest - smallest) * .08, 1e-4)
    fig, axes = plt.subplots(3, 2, figsize=(12, 8), sharex=True, sharey=True, constrained_layout=True)
    for ax, scan in zip(axes.flat, SCANS):
        ax.plot(offsets, profiles[scan], linewidth=.8, color="#1763a6" if scan.endswith("_on") else "#ad4c16")
        ax.axvline(0, color="black", linewidth=.7, linestyle="--")
        evidence = record["adjacent_off_evidence"].get(scan)
        if evidence:
            item = evidence["neighborhood_maximum"]
            ax.scatter([item["offset_hz"]], [item["fractional_excess"]], s=20, color="#aa1122", zorder=4)
        ax.set_title(scan + (" (originating ON)" if scan == record["originating_on"] else ""), fontsize=10)
        ax.set_xlim(-128 * abs(DF_HZ), 128 * abs(DF_HZ))
        ax.set_ylim(smallest - margin, largest + margin)
        ax.set_xlabel("Frequency offset from selected reference (Hz)")
        ax.set_ylabel("Fractional spectral excess")
        ax.grid(alpha=.2)
    fig.suptitle(f"{record['ranked_id']} — saved time-averaged spectral profiles\n"
                 f"Reference {record['frequency_mhz']:.9f} MHz; width {width} channels; "
                 f"signed ON−OFF contrast {record['signed_contrast_fractional_units']:.6g}\n"
                 "Red dots: adjacent-OFF maxima within ±32 channels. Exploratory ranking; not a detection.", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def run(args, started):
    scope, spectra, old_z, normalization, verified = load_inputs(args)
    smooth = {width: {scan: width_mean(spectra[scan], width) for scan in SCANS} for width in WIDTHS}
    off_maximum = {width: {scan: maximum_filter1d(smooth[width][scan], size=2 * OFF_HALO + 1, mode="nearest")
                           for scan in SCANS if scan.endswith("_off")} for width in WIDTHS}
    tops, score_files, summaries = {}, {}, {}
    out = Path(args.outdir)
    for on in ONS:
        scores = {}
        for width in WIDTHS:
            controls = ADJACENT[on]
            envelope = off_maximum[width][controls[0]]
            if len(controls) == 2:
                envelope = np.maximum(envelope, off_maximum[width][controls[1]])
            scores[width] = smooth[width][on] - envelope
            if not np.isfinite(scores[width]).all():
                raise ValueError("Contrast array contains non-finite values")
        maximum = np.maximum(scores[1], scores[3])
        winning = np.where(scores[3] > scores[1], 3, 1).astype(np.uint8)
        name = f"{on}_full_chunk_stationary_contrast.npz"
        np.savez_compressed(out / name, D1=scores[1], D3=scores[3], maxD=maximum, winning_width=winning,
                            source_channel0=CHANNEL0, source_channel_count=COUNT,
                            df_hz=DF_HZ, fch1_hz=FCH1_HZ,
                            eligible_local_index0=EDGE, eligible_local_index_stop=COUNT - EDGE)
        score_files[on] = {"path": name, "sha256": digest(out / name), "bytes": (out / name).stat().st_size}
        tops[on] = ranked_tracks(on, maximum, winning, smooth, old_z[on])
        selected = maximum[EDGE:COUNT - EDGE]
        summaries[on] = {"eligible_source_channels": COUNT - 2 * EDGE,
                         "eligible_width_hypotheses": len(WIDTHS) * (COUNT - 2 * EDGE),
                         "positive_maxD_channels_descriptive_only": int(np.count_nonzero(selected > 0)),
                         "largest_signed_contrast": float(np.max(selected)),
                         "smallest_signed_contrast": float(np.min(selected))}
        print("COMPLETED_STATIONARY_CONTRAST", on, summaries[on]["largest_signed_contrast"], flush=True)
    save(out / "top20_per_on.json", tops)
    plot_files = []
    for on in ONS:
        for record in tops[on][:PLOTS]:
            name = record["ranked_id"] + ".png"
            plot_profiles(record, smooth, out / name)
            plot_files.append({"path": name, "sha256": digest(out / name)})
    receipt = {
        "status": "COMPLETED_EXPLORATORY_STATIONARY_ON_OFF_CONTRAST",
        "scope_sha256": digest(args.scope), "script_sha256": digest(__file__),
        "source_manifest_sha256": digest(args.source_manifest),
        "verified_saved_spectrum_members": verified,
        "adjacent_OFF_mapping": {key: list(value) for key, value in ADJACENT.items()},
        "fractional_excess_definition": "row_normalized_mean_power / running_median_baseline - 1",
        "score_definition": "mean_width(e_ON) minus maximum of mean_width(e_adjacent_OFF) within ±32 source channels",
        "widths_channels": list(WIDTHS), "winner_tie_rule": "width1", "OFF_halo_channels": OFF_HALO,
        "eligible_local_index_interval_half_open": [EDGE, COUNT - EDGE],
        "eligible_source_channel_interval_half_open": [CHANNEL0 + EDGE, CHANNEL0 + COUNT - EDGE],
        "eligible_carriers_per_ON": COUNT - 2 * EDGE,
        "eligible_channel_edge_bandwidth_hz": (COUNT - 2 * EDGE) * abs(DF_HZ),
        "all_full_arrays_signed_finite": True,
        "full_array_edge_values": "Numerical padding retained; outside eligible interval excluded from ranking and summaries",
        "display_NMS_channels": NMS, "display_top_per_ON": TOP,
        "plot_count": len(plot_files), "plot_halfwidth_channels": 128,
        "ONs_ranked_independently": True, "OFF_veto_or_qualification": False,
        "new_HTTP_requests": 0, "new_telescope_source_bytes": 0,
        "new_source_chunk_decodes": 0, "new_drift_rescoring": 0,
        "original_failure_statuses_changed": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sky_sensitivity": False,
        "independent_observing_visits": 1, "ON_summary": summaries,
        "saved_original_normalization_context": normalization,
        "score_files": score_files, "plots": plot_files,
        "limitations": [
            "Post-data exploratory prioritization with correlated channel/width trials; ranks are not probabilities",
            "Each scan has its own row normalization and running baseline; gain/background changes can cause apparent excess",
            "OFF windows can contain unrelated lines; the control envelope is evidence, not a sky veto",
            "Only time-averaged stationary spectral projections are compared; drifting or brief signals can be diluted",
            "Width3 scores average fractional excess; original width1 ON residual units are context only",
            "ON1 has only a following OFF; no preceding OFF exists in this acquired sequence",
            "One historical visit; no discovery or qualified sky-null conclusion",
        ],
        "caps": {"CPU_seconds": CPU_CAP, "wall_seconds": WALL_CAP, "address_space_bytes": MEMORY_CAP},
        "process_CPU_seconds_including_imports": time.process_time(),
        "wall_seconds_including_imports": time.monotonic() - started,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    save(out / "STATIONARY_CONTRAST_RECEIPT.json", receipt)
    print(json.dumps(receipt, allow_nan=False), flush=True)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("scope", "spectra-dir", "source-manifest", "outdir"):
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    Path(args.outdir).mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError("Frozen stationary contrast CPU/wall cap reached")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        global np, maximum_filter1d, plt
        import numpy as np
        from scipy.ndimage import maximum_filter1d
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        run(args, started)
    except BaseException as exc:
        save(Path(args.outdir) / "STATIONARY_CONTRAST_FAILURE.json", {
            "status": "FAILED_EXPLORATORY_STATIONARY_CONTRAST", "error_type": type(exc).__name__,
            "error": str(exc), "retry_authorized": False,
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic() - started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        })
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
