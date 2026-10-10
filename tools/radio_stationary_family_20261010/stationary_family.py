"""One descriptive expansion of the already selected stationary top20 family.

Nine completed ON top3 patches are reused without remeasurement. Exactly 111
remaining selected cases use the retained native chunk and saved row medians.
The scope is prospective for these derived metrics, after source/ranks were
already exposed. Import opens no values; no source HTTP or search is present.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[2]
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
CONTROLS = {"epoch1_on": ("epoch1_off",), "epoch2_on": ("epoch1_off", "epoch2_off"),
    "epoch3_on": ("epoch2_off", "epoch3_off"), "epoch1_off": ("epoch1_on", "epoch2_on"),
    "epoch2_off": ("epoch2_on", "epoch3_on"), "epoch3_off": ("epoch3_on",)}
WEAK_IDS = ("epoch1_on_stationary_rank_03", "epoch2_on_stationary_rank_01",
    "epoch2_on_stationary_rank_02", "epoch2_on_stationary_rank_03",
    "epoch3_on_stationary_rank_01", "epoch3_on_stationary_rank_02")
C0, COUNT, HALF = 158334976, 1048576, 64
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
CPU_CAP, WALL_CAP, MEMORY_CAP = 80, 1800, 4*1024**3
METRIC_NAMES = ("mean_center_minus_flank", "median_center_minus_flank", "positive_rows",
    "first_8_rows_mean", "last_8_rows_mean", "minimum_of_half_means",
    "channel0_minus_immediate_neighbor_mean", "selected_width_center_minus_outer_neighbor_mean",
    "selected_width_center_minus_median_noncentral_profile", "support_mean_width3",
    "support_mean_width5", "support_mean_width9")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for piece in iter(lambda: handle.read(1024**2), b""):
            h.update(piece)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix+".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")
    temporary.replace(target)


def contract(args):
    scope = json.loads(Path(args.scope).read_text())
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("New helper differs from derivative-metric freeze")
    for path, expected in scope["pinned_files"].items():
        if digest(ROOT/path) != expected:
            raise ValueError("Frozen input/method differs: " + path)
    for name, version in scope["runtime_versions"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Frozen package version differs: " + name)
    required = {"source_channel_interval_half_open": [C0, C0+COUNT], "rows_per_scan": 16,
        "scans": list(SCANS), "source_channel_offsets": list(range(-HALF, HALF+1)),
        "selected_widths_channels": [1, 3], "fixed_drift_hz_s": 0.0,
        "fixed_source_channel_shift": 0, "flank_exclusion_absolute_offset_lte": 3,
        "reused_case_count": 9, "newly_measured_case_count": 111, "total_case_count": 120,
        "metrics": list(METRIC_NAMES), "weak_case_ids": list(WEAK_IDS),
        "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
        "maximum_plot_count": 10, "source_values_and_original_ranks_previously_opened": True}
    if any(scope.get(k) != v for k, v in required.items()):
        raise ValueError("Declared derivative family differs from implemented choices")
    load = lambda key: json.loads((ROOT/scope["input_paths"][key]).read_text())
    source, acquisition = load("source_manifest"), load("acquisition")
    ranks, normalization, old_profiles = load("stationary_top20"), load("normalization"), load("old_profiles")
    if set(ranks) != set(SCANS) or any(len(ranks[s]) != 20 for s in SCANS):
        raise ValueError("Complete six-origin stationary top20 family required")
    tracks = [track for origin in SCANS for track in ranks[origin]]
    if len({r["track_id"] for r in tracks}) != 120:
        raise ValueError("Exactly 120 distinct saved stationary profile IDs required")
    for origin in SCANS:
        for rank, track in enumerate(ranks[origin], 1):
            if (track["family"] != "stationary" or track["originating_scan"] != origin or
                    track["display_rank"] != rank or track["track_id"] != origin+"_stationary_rank_%02d" % rank or
                    track["width_channels"] not in (1, 3) or track["drift_hz_s"] != 0.0):
                raise ValueError("Original rank/width/family identity differs")
            if not C0+283 <= track["source_reference_channel"] < C0+COUNT-283:
                raise ValueError("Original selected channel outside eligible stationary family")
            if abs(track["reference_frequency_hz"]-(FCH1+DF*track["source_reference_channel"])) > 1e-6:
                raise ValueError("Absolute selected source frequency differs")
    if [r["label"] for r in source["sources"]] != list(SCANS):
        raise ValueError("Original six-scan source metadata required")
    if acquisition["status"] != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY":
        raise ValueError("Original complete acquisition required")
    if acquisition["source_manifest_sha256"] != scope["pinned_files"][scope["input_paths"]["source_manifest"]]:
        raise ValueError("Acquisition metadata identity differs")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or {r["scan_id"] for r in decoded} != set(SCANS):
        raise ValueError("Six unique retained compact files required")
    if acquisition["physical_channel_interval_half_open"] != [C0, C0+COUNT]:
        raise ValueError("Retained native frequency chunk differs")
    medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS], dtype=np.float64)
    if normalization["source_channel0"] != C0 or medians.shape != (6, 16) or not np.isfinite(medians).all() or (medians <= 0).any():
        raise ValueError("Invalid retained full-chunk row normalization")
    previous = {r["selected_track"]["track_id"]: r for r in old_profiles if r["selected_track"]["family"] == "stationary"}
    expected_reuse = {track["track_id"] for s in ONS for track in ranks[s][:3]}
    if set(previous) != expected_reuse or set(scope["reused_patch_sha256"]) != expected_reuse:
        raise ValueError("Exactly the original nine stationary ON top3 cases must be reused")
    headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
    anchor = min(h["tstart"] for h in headers.values())
    for h in headers.values():
        if (abs(h["fch1"]*1e6-FCH1) > 1e-6 or abs(h["foff"]*1e6-DF) > 1e-12 or
                abs(h["tsamp"]-TSAMP) > 1e-12):
            raise ValueError("Original header geometry differs")
    return scope, source, acquisition, tracks, medians, previous, headers, anchor


def retained_power(scope, source, acquisition):
    import h5py
    import hdf5plugin  # Same installed source filter, no installation here.
    arrays, verified = {}, {}
    sources = {r["label"]: r for r in source["sources"]}
    for item in acquisition["decoded_files"]:
        label = item["scan_id"]
        path = ROOT/scope["input_paths"]["compact_dir"]/item["array_file"]
        sha = digest(path)
        if sha != item["file_sha256"] or sha != scope["compact_file_sha256"][label]:
            raise ValueError("Retained compact file hash differs: " + label)
        with h5py.File(path, "r", rdcc_nbytes=8*1024**2) as handle:
            data = handle["data"]
            if data.shape != (16, 1, COUNT) or data.dtype != np.dtype("<f4"):
                raise ValueError("Retained compact dataset shape/type differs")
            if (int(data.attrs["original_source_frequency_chunk_origin"]) != C0 or
                    data.attrs["original_source_url"] != sources[label]["url"] or
                    data.attrs["original_source_etag"] != sources[label]["etag"]):
                raise ValueError("Retained source-channel/source identity differs")
            power = data[:, 0, :]
        if not np.isfinite(power).all() or (power < 0).any():
            raise ValueError("Retained power must remain finite and nonnegative")
        if [r["time_row"] for r in item["decoded_rows"]] != list(range(16)):
            raise ValueError("Acquisition decoded-row checksums are incomplete")
        for i, row in enumerate(item["decoded_rows"]):
            if row["decoded_bytes"] != COUNT*4 or hashlib.sha256(power[i].tobytes()).hexdigest() != row["decoded_sha256"]:
                raise ValueError("Retained decoded row differs: " + label)
        arrays[label] = power
        verified[label] = {"path": str(path.relative_to(ROOT)), "sha256": sha, "bytes": path.stat().st_size}
    return arrays, verified


def reused_patch(scope, item, medians):
    track = item["selected_track"]
    path = ROOT/scope["input_paths"]["old_patch_dir"]/item["patch"]["path"]
    before = digest(path)
    if before != item["patch"]["sha256"] or before != scope["reused_patch_sha256"][track["track_id"]]:
        raise ValueError("Original reused patch differs")
    with np.load(path, allow_pickle=False) as old:
        fields = {key: old[key].copy() for key in ("raw_power", "row_normalized_power",
            "center_row_normalized_power", "fixed_flank_median_row_normalized_power",
            "center_minus_flank_each_row", "mean_fixed_track_frequency_profile")}
        if (old["raw_power"].shape != (6, 16, 129) or old["raw_power"].dtype != np.dtype("float32") or
                not np.array_equal(old["saved_full_chunk_row_medians"], medians) or
                not np.array_equal(old["scans"], np.asarray(SCANS)) or
                not np.array_equal(old["source_channel_offsets"], np.arange(-64, 65)) or
                not np.all(old["frozen_source_channel_centers"] == track["source_reference_channel"]) or
                int(old["width_channels"]) != track["width_channels"] or float(old["drift_hz_s"]) != 0.0 or
                int(old["fixed_source_channel_shift"]) != 0):
            raise ValueError("Original reused patch geometry/normalization differs")
    for key, values in fields.items():
        if not np.isfinite(values).all():
            raise ValueError("Original reused patch contains nonfinite values: " + key)
    old_stats = {r["scan_id"]: r for r in item["scan_profiles"]}
    if set(old_stats) != set(SCANS):
        raise ValueError("Original reused scan summaries incomplete")
    for i, label in enumerate(SCANS):
        if not np.array_equal(fields["center_minus_flank_each_row"][i], old_stats[label]["all_16_center_minus_flank_rows"]):
            raise ValueError("Reused residual rows differ from original saved JSON")
    return fields, old_stats, {"path": str(path.relative_to(ROOT)), "sha256_before": before,
        "sha256_after": digest(path), "remeasured": False, "copied_array_sha256": {
            key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in fields.items()}}


def new_patch(track, arrays, medians):
    index = track["source_reference_channel"]-C0
    raw = np.asarray([arrays[s][:, index-HALF:index+HALF+1] for s in SCANS])
    if raw.shape != (6, 16, 129):
        raise ValueError("Frozen new patch lacks full channel/row context")
    normalized = raw.astype(np.float64)/medians[:, :, None]
    flank = np.abs(np.arange(-64, 65)) > 3
    background = np.median(normalized[:, :, flank], axis=2)
    h = track["width_channels"]//2
    center = normalized[:, :, 64-h:65+h].mean(axis=2)
    residual = center-background
    mean_profile = np.mean(normalized-background[:, :, None], axis=1)
    return {"raw_power": raw, "row_normalized_power": normalized,
        "center_row_normalized_power": center, "fixed_flank_median_row_normalized_power": background,
        "center_minus_flank_each_row": residual, "mean_fixed_track_frequency_profile": mean_profile}


def metrics(values, width, old_stats=None):
    residual = values["center_minus_flank_each_row"]
    e = values["mean_fixed_track_frequency_profile"]
    result = []
    flank = np.abs(np.arange(-64, 65)) > 3
    h = width//2
    for i, label in enumerate(SCANS):
        r, profile = residual[i], e[i]
        if old_stats is None:
            mean, median, positive = float(r.mean()), float(np.median(r)), int(np.count_nonzero(r > 0))
        else:
            old = old_stats[label]
            mean, median, positive = old["mean_center_minus_flank"], old["median_center_minus_flank"], old["positive_rows"]
        first, last = float(r[:8].mean()), float(r[8:].mean())
        box = float(profile[64-h:65+h].mean())
        record = {"scan_id": label, "scan_role": "ON" if label.endswith("_on") else "OFF",
            "mean_center_minus_flank": mean, "median_center_minus_flank": median, "positive_rows": positive,
            "first_8_rows_mean": first, "last_8_rows_mean": last, "minimum_of_half_means": min(first, last),
            "channel0_minus_immediate_neighbor_mean": float(profile[64]-(profile[63]+profile[65])/2),
            "selected_width_center_minus_outer_neighbor_mean": float(box-(profile[63-h]+profile[65+h])/2),
            "selected_width_center_minus_median_noncentral_profile": float(box-np.median(profile[flank])),
            "support_mean_width3": float(profile[63:66].mean()),
            "support_mean_width5": float(profile[62:67].mean()),
            "support_mean_width9": float(profile[60:69].mean()),
            "all_16_center_minus_flank_rows": r.tolist(),
            "original_mean_median_positive_count_reused": old_stats is not None}
        result.append(record)
    return result


def describe(records):
    result = {}
    for role in ("ON", "OFF"):
        for width in (1, 3):
            rows = [r["origin_measurements"] for r in records if r["origin_role"] == role and r["original_selected_width"] == width]
            stats = {"case_count": len(rows), "selection_conditional_not_independent_null_trials": True}
            stats["stratum_status"] = "OBSERVED_SELECTED_PROFILES" if rows else "EMPTY_UNSUPPORTED_COMPARISON"
            if rows:
                stats["all_16_positive_rows_case_count"] = sum(r["positive_rows"] == 16 for r in rows)
                stats["metrics"] = {}
                for name in METRIC_NAMES:
                    a = np.asarray([r[name] for r in rows])
                    stats["metrics"][name] = {"minimum": float(a.min()), "median": float(np.median(a)),
                        "maximum": float(a.max()), "first_quartile": float(np.percentile(a, 25)),
                        "third_quartile": float(np.percentile(a, 75))}
            result[role+"_width"+str(width)] = stats
    return result


def summaries_plot(records, path, keys, title):
    import matplotlib.pyplot as plt
    groups = [(role, width) for width in (1, 3) for role in ("ON", "OFF")]
    fig, axes = plt.subplots(1, len(keys), figsize=(6*len(keys), 5), squeeze=False)
    for ax, key in zip(axes.flat, keys):
        values = [[r["origin_measurements"][key] for r in records if r["origin_role"] == role and r["original_selected_width"] == width] for role, width in groups]
        for i, v in enumerate(values, 1):
            if v:
                ax.boxplot([v], positions=[i], widths=.45, tick_labels=[""])
        ax.set_xticks(range(1, 5), [f"{role}, w{width}\nn={len(v)}"+(" (empty)" if not v else "") for (role, width), v in zip(groups, values)])
        ax.axhline(0, color="gray", linewidth=.7)
        ax.set_title(key.replace("_", " ").replace("selected width center minus outer neighbor mean", "Selected box minus outer neighbors").replace("channel0 minus immediate neighbor mean", "Channel 0 minus nearest neighbors"), fontsize=10, wrap=True)
        ax.set_ylabel("Additive row-normalized units")
        ax.grid(alpha=.2, axis="y")
    fig.suptitle(title+"\nOriginal selected top20 family; descriptive", fontsize=12)
    fig.subplots_adjust(left=.09, right=.98, bottom=.17, top=.78, wspace=.35)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def make_plots(records, times, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plots = []
    specifications = [(["mean_center_minus_flank"], "ORIGIN_MEAN_BY_ROLE_WIDTH.png", "Mean by original role and width"),
        (["minimum_of_half_means"], "ORIGIN_MIN_HALF_BY_ROLE_WIDTH.png", "Lower of fixed first/last half means"),
        (["channel0_minus_immediate_neighbor_mean", "selected_width_center_minus_outer_neighbor_mean"], "ORIGIN_SHAPE_BY_ROLE_WIDTH.png", "Fixed central and neighboring-channel shape")]
    for keys, name, title in specifications:
        summaries_plot(records, out/name, keys, title)
        plots.append(name)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    extrema = [r["origin_measurements"][key] for r in records for key in ("first_8_rows_mean", "last_8_rows_mean")]
    lo, hi = min(extrema), max(extrema)
    margin = max((hi-lo)*.06, .001)
    for ax, width in zip(axes, (1, 3)):
        for role, color in (("ON", "#1565a8"), ("OFF", "#af591f")):
            subset = [r["origin_measurements"] for r in records if r["origin_role"] == role and r["original_selected_width"] == width]
            ax.scatter([r["first_8_rows_mean"] for r in subset], [r["last_8_rows_mean"] for r in subset], label=f"{role} n={len(subset)}", color=color, s=18, alpha=.8)
        ax.plot([lo-margin, hi+margin], [lo-margin, hi+margin], color="gray", linestyle="--", linewidth=.7)
        ax.set_xlim(lo-margin, hi+margin); ax.set_ylim(lo-margin, hi+margin)
        ax.set_title(f"Original selected width {width}"); ax.set_xlabel("First 8 rows mean")
        ax.set_ylabel("Last 8 rows mean"); ax.legend(fontsize=9); ax.grid(alpha=.2)
    fig.suptitle("Two fixed time halves; selected top20 family\nAdditive normalized units; no probability calibration")
    fig.subplots_adjust(left=.08, right=.97, top=.80, bottom=.14, wspace=.28)
    name = "ORIGIN_FIXED_HALF_COMPARISON.png"; fig.savefig(out/name, dpi=120); plt.close(fig); plots.append(name)
    by_id = {r["profile_id"]: (i, r) for i, r in enumerate(records)}
    for profile_id in WEAK_IDS:
        i, case = by_id[profile_id]
        fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True)
        rows = case["scan_measurements"]
        data = np.asarray([r["all_16_center_minus_flank_rows"] for r in rows])
        lo, hi = min(0.0, float(data.min())), max(0.0, float(data.max()))
        margin = max((hi-lo)*.06, .002)
        for ax, label, values, dt in zip(axes.flat, SCANS, data, times[i]):
            color = "#1565a8" if label.endswith("_on") else "#af591f"
            ax.plot(dt, values, marker="o", markersize=3, linewidth=.85, color=color)
            ax.axhline(0, color="gray", linewidth=.7); ax.set_ylim(lo-margin, hi+margin)
            ax.set_title(label+(" (origin)" if label == case["origin_scan"] else ""), loc="left", fontsize=10)
            ax.set_ylabel("Normalized power\nminus fixed flank"); ax.grid(alpha=.2)
        for ax in axes[-1]: ax.set_xlabel("Seconds from origin first midpoint")
        fig.suptitle(f"{profile_id}\n{case['frequency_MHz']:.9f} MHz; original width {case['original_selected_width']}; all 16 rows", fontsize=12)
        fig.subplots_adjust(left=.13, right=.97, bottom=.08, top=.88, hspace=.48, wspace=.24)
        name = profile_id+"_all_six_times.png"; fig.savefig(out/name, dpi=120); plt.close(fig); plots.append(name)
    return [{"path": name, "sha256": digest(out/name), "bytes": (out/name).stat().st_size} for name in plots]


def run(args):
    scope, source, acquisition, tracks, medians, previous, headers, anchor = contract(args)
    arrays, verified = retained_power(scope, source, acquisition)
    offsets = np.arange(-64, 65)
    containers = {key: [] for key in ("raw_power", "row_normalized_power", "center_row_normalized_power",
        "fixed_flank_median_row_normalized_power", "center_minus_flank_each_row", "mean_fixed_track_frequency_profile")}
    cases, flat, reused, times = [], [], {}, []
    for track in tracks:
        profile_id, origin = track["track_id"], track["originating_scan"]
        if profile_id in previous:
            if previous[profile_id]["selected_track"] != track:
                raise ValueError("Reused original selected track metadata differs")
            fields, old_stats, receipt = reused_patch(scope, previous[profile_id], medians)
            reused[profile_id] = receipt
            source_type = "REUSED_COMPLETE_PRIOR_STATIONARY_ON_TOP3_PATCH"
        else:
            fields, old_stats = new_patch(track, arrays, medians), None
            source_type = "NEW_FIXED_PROJECTION_FROM_RETAINED_NATIVE_CHUNK"
        scans = metrics(fields, track["width_channels"], old_stats)
        for key in containers: containers[key].append(fields[key])
        origin_measurements = scans[SCANS.index(origin)]
        controls = {r["scan_id"]: {key: r[key] for key in METRIC_NAMES} for r in scans if r["scan_id"] in CONTROLS[origin]}
        max_control_mean = max(r["mean_center_minus_flank"] for r in controls.values())
        case = {"profile_id": profile_id, "origin_scan": origin,
            "origin_role": "ON" if origin.endswith("_on") else "OFF", "display_rank": track["display_rank"],
            "source_channel": track["source_reference_channel"], "frequency_MHz": track["reference_frequency_hz"]/1e6,
            "original_selected_width": track["width_channels"], "profile_source": source_type,
            "original_selected_track": track, "origin_measurements": origin_measurements,
            "scan_measurements": scans, "fixed_adjacent_controls": controls,
            "origin_mean_minus_largest_fixed_control_mean": origin_measurements["mean_center_minus_flank"]-max_control_mean,
            "classification": "UNRESOLVED_DESCRIPTIVE_SELECTED_PROFILE"}
        cases.append(case)
        for r in scans:
            flat.append({"profile_id": profile_id, "origin_scan": origin, "origin_role": case["origin_role"],
                "original_selected_width": track["width_channels"], "profile_source": source_type, **r})
        ref = (headers[origin]["tstart"]-anchor)*86400+.5*TSAMP
        times.append(np.asarray([(headers[s]["tstart"]-anchor)*86400+(np.arange(16)+.5)*TSAMP-ref for s in SCANS]))
    if len(reused) != 9 or len(cases) != 120 or len(flat) != 720:
        raise ValueError("Incomplete fixed selected family")
    out = Path(args.outdir)
    payload = {key: np.asarray(value) for key, value in containers.items()}
    payload.update(saved_full_chunk_row_medians=medians, source_channel_offsets=offsets,
        scans=np.asarray(SCANS), profile_ids=np.asarray([r["profile_id"] for r in cases]),
        originating_scans=np.asarray([r["origin_scan"] for r in cases]),
        selected_source_channels=np.asarray([r["source_channel"] for r in cases]),
        original_selected_widths=np.asarray([r["original_selected_width"] for r in cases]),
        reference_frequency_hz=np.asarray([track["reference_frequency_hz"] for track in tracks]),
        times_seconds_from_origin_first_midpoint=np.asarray(times), source_channel0=C0,
        source_channel_count=COUNT, df_hz=DF, fixed_drift_hz_s=0.0, fixed_source_channel_shift=0)
    archive = out/"ALL_120_FIXED_STATIONARY_PATCHES.npz"
    np.savez_compressed(archive, **payload)
    save(out/"ALL_720_SCAN_PROFILE_ROWS.json", flat)
    save(out/"ALL_120_STATIONARY_CASES.json", cases)
    summaries = describe(cases)
    weak_cases = [next(r for r in cases if r["profile_id"] == profile_id) for profile_id in WEAK_IDS]
    save(out/"SIX_FIXED_WEAK_CASES.json", weak_cases)
    plots = make_plots(cases, np.asarray(times), out)
    after = {r["profile_id"]: digest(ROOT/scope["input_paths"]["old_patch_dir"]/previous[r["profile_id"]]["patch"]["path"]) for r in cases if r["profile_id"] in previous}
    if any(after[key] != value["sha256_before"] for key, value in reused.items()):
        raise ValueError("A reused source patch changed during the job")
    result = {"status": "COMPLETED_DESCRIPTIVE_STATIONARY_TOP20_FAMILY",
        "case_count": 120, "origin_ON_case_count": 60, "origin_OFF_case_count": 60,
        "scan_profile_count": 720, "rows_per_scan_profile": 16, "reused_prior_cases": 9,
        "newly_measured_fixed_cases": 111, "unique_exact_source_channels": len({r["source_channel"] for r in cases}),
        "scope_sha256": digest(args.scope), "script_sha256": digest(__file__), "verified_retained_compacts": verified,
        "reused_patch_identity": reused, "summary_by_origin_role_and_original_width": summaries,
        "fixed_weak_case_ids": list(WEAK_IDS), "full_family_payload": {"path": archive.name, "sha256": digest(archive), "bytes": archive.stat().st_size},
        "plots": plots, "plot_count": len(plots), "MJD_anchor": anchor,
        "already_exposed_source_values_and_ranks": True, "prospective_for_new_derived_metrics_only": True,
        "one_historical_visit": True, "new_source_HTTP_requests": 0, "new_telescope_source_bytes": 0,
        "new_search_or_width_drift_frequency_optimization": False, "old_holdouts_reopened": False,
        "old_A_B_status": "FAIL_CLOSED_UNCHANGED", "qualified_sky_pilot": False,
        "FAP_SNR_flux_sensitivity_or_origin_inference": False,
        "limitations": ["Top20 selection-conditional panel, not the complete million-carrier search family or calibrated null",
            "Origin ON/OFF labels describe selection; shared controls, repeated channels and differing epochs prevent exchangeability or independence",
            "OFF spectra are not certified noise; no rank or half-window statistic gives a probability",
            "Original widths remain fixed; support means and neighbor contrasts do not rerank or estimate a physical linewidth",
            "Nine prior patches and their saved original means/medians/counts/residuals/profiles are reused without remeasurement",
            "Each full-chunk row normalization and local flank is scan-specific; gain/background variation can create apparent contrasts",
            "Only stationary selected tracks and two fixed eight-row halves; no event timing fit or new signal search"]}
    save(out/"FAMILY_RESULT.json", result)
    return result


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError("Descriptive family CPU/wall bound reached")
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        global np
        import numpy as np
        result = run(args)
        result.update(process_CPU_seconds_including_imports=time.process_time(),
            wall_seconds_including_imports=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps({key: value for key, value in result.items() if key not in
            ("summary_by_origin_role_and_original_width", "reused_patch_identity", "plots")}, allow_nan=False))
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status": "INCOMPLETE_DESCRIPTIVE_STATIONARY_TOP20_FAMILY",
            "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False,
            "process_CPU_seconds_including_imports": time.process_time(), "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
