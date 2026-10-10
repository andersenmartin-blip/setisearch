"""One frozen eight-core gap drift search, followed by fixed top-three profiles.

Importing this wrapper opens no observation values. Source values were opened
previously for stationary work; these drift hypotheses have not been searched.
Everything is descriptive, from one historical visit, with no qualified veto.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
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
C0, COUNT = 158334976, 1048576
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
WIDTHS, CORE_COUNT, CROP_HALO, TOP = (1, 3), 4096, 4000, 20
GAP_K = (0, 4, 8, 12, 16, 20, 24, 28)
STARTS = tuple((5 + 8*k)*CORE_COUNT for k in GAP_K)
PRIOR_STARTS = tuple((1 + 8*k)*CORE_COUNT for k in range(32))
CPU_CAP, WALL_CAP, MEMORY_CAP = 90, 1800, 4*1024**3
SOURCE_PATH = "tools/radio_fresh_band_20261009/source_manifest.json"
NORMALIZATION_PATH = "results/radio_fresh_band_20261009/stationary/NORMALIZATION.json"
FRESH_PATH = "tools/radio_fresh_band_20261009/fresh_search.py"
DETECTOR_PATH = "pilot_engine_20261008/detector.py"
SOURCE_SHA = "d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c"
ACQUISITION_SHA = "da165fe31ac4a70167b06f83b8f667fbb8604b595c642d3610fec68788bebf37"


class ResourceLimitExceeded(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    temporary.replace(target)


def load_contract(args):
    if digest(args.scope) != args.expected_scope_sha256:
        raise ValueError("Scope differs from the publicly frozen execution SHA")
    scope = json.loads(Path(args.scope).read_text())
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Gap wrapper differs from prospective freeze")
    expected = {
        "schema": "SETI_EIGHT_PREVIOUSLY_UNSEARCHED_GAP_DRIFT_CORES_V1",
        "source_manifest_sha256": SOURCE_SHA,
        "acquisition_summary_sha256": ACQUISITION_SHA,
        "source_channel_interval_half_open": [C0, C0+COUNT],
        "rows_per_scan": 16, "scan_order": list(SCANS), "origin_scan_order": list(ONS),
        "count": COUNT, "fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP,
        "gap_indices_k": list(GAP_K), "new_core_start_relative_channels": list(STARTS),
        "prior_core_start_relative_channels": list(PRIOR_STARTS),
        "core_channel_count": CORE_COUNT, "crop_halo_channels": CROP_HALO,
        "new_core_count": 8, "expected_scan_tiles": 24, "carriers_per_ON": 32768,
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": list(WIDTHS), "valid_hypotheses_per_carrier": 1526,
        "rank_count_per_ON": TOP, "display_suppression_channels": 3,
        "fixed_profile_ranks_per_ON": 3, "expected_profile_count": 9,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
        "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
        "new_telescope_HTTP_request_cap": 0, "new_telescope_BODY_byte_cap": 0,
        "numeric_retry_authorized": False, "old_holdouts_reopened": False,
        "original_A_B_failures_unchanged": True, "OFF_veto": False,
        "unqualified_exploratory_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
    }
    if any(scope.get(k) != v for k, v in expected.items()):
        raise ValueError("Scope differs from implemented frozen gap search")
    pinned = scope["pinned_dependency_files"]
    required_pins = {SOURCE_PATH, NORMALIZATION_PATH, FRESH_PATH, DETECTOR_PATH,
                     "tools/radio_fresh_band_20261009/analysis_scope.json"}
    if set(pinned) != required_pins:
        raise ValueError("Exactly the five existing metadata/code dependencies must be pinned")
    for name, expected_sha in pinned.items():
        if digest(ROOT/name) != expected_sha:
            raise ValueError("Pinned dependency differs: " + name)
    if pinned[SOURCE_PATH] != SOURCE_SHA or digest(args.acquisition_summary) != ACQUISITION_SHA:
        raise ValueError("Source acquisition identity differs")
    versions = {"numpy": "2.3.5", "scipy": "1.17.0", "matplotlib": "3.10.8",
                "h5py": "3.15.1", "hdf5plugin": "7.1.0"}
    if scope.get("runtime_package_versions") != versions:
        raise ValueError("Frozen runtime version declarations differ")
    for name, version in versions.items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Runtime package differs: " + name)
    for start in STARTS:
        if start-CROP_HALO < 0 or start+CORE_COUNT+CROP_HALO > COUNT:
            raise ValueError("New search crop exceeds retained native chunk")
        if any(max(start, old) < min(start+CORE_COUNT, old+CORE_COUNT) for old in PRIOR_STARTS):
            raise ValueError("A new carrier core overlaps an already searched carrier core")
    if any(max(a, b) < min(a+CORE_COUNT, b+CORE_COUNT)
           for i, a in enumerate(STARTS) for b in STARTS[i+1:]):
        raise ValueError("New carrier cores overlap each other")
    source = json.loads((ROOT/SOURCE_PATH).read_text())
    if [r["label"] for r in source["sources"]] != list(SCANS):
        raise ValueError("Six original chronologically selected scans required")
    if [r["role"].upper() for r in source["sources"]] != ["ON", "OFF"]*3:
        raise ValueError("Original alternating scan roles required")
    anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
    previous_end = -math.inf
    for r in source["sources"]:
        h = r["current_header"]["data_attributes"]
        for observed, target, tolerance in ((h["fch1"]*1e6, FCH1, 1e-6),
                (h["foff"]*1e6, DF, 1e-12), (h["tsamp"], TSAMP, 1e-12)):
            if not math.isclose(observed, target, rel_tol=0, abs_tol=tolerance):
                raise ValueError("Actual header grid differs")
        start = (h["tstart"]-anchor)*86400
        if start < previous_end:
            raise ValueError("Scan sequence overlaps or is not chronological")
        previous_end = start+16*TSAMP
    acquisition = json.loads(Path(args.acquisition_summary).read_text())
    if acquisition.get("status") != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY":
        raise ValueError("Complete original acquisition required")
    if acquisition.get("source_manifest_sha256") != SOURCE_SHA:
        raise ValueError("Acquisition source metadata pin differs")
    if acquisition.get("physical_channel_interval_half_open") != [C0, C0+COUNT]:
        raise ValueError("Wrong native chunk acquisition")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or {r["scan_id"] for r in decoded} != set(SCANS):
        raise ValueError("Exactly six unique compact inputs required")
    normalization = json.loads((ROOT/NORMALIZATION_PATH).read_text())
    if normalization["source_channel0"] != C0:
        raise ValueError("Wrong retained full-chunk normalization")
    return scope, source, acquisition, normalization, float(anchor)


def run_search(fresh, arrays, source, anchor, out):
    from pilot_engine_20261008.detector import Scan, Config, search_scan
    cfg = Config(widths=WIDTHS)
    drifts = np.linspace(-4.0, 4.0, 763)
    dt = np.arange(16)*TSAMP
    mismatch = float((drifts[1]-drifts[0])*dt[-1]/(2*abs(DF)))
    if mismatch > .5+1e-12:
        raise ValueError("Drift-grid half mismatch exceeds half a native channel")
    all_results = {s: [] for s in ONS}
    receipts = []
    for tile_index, core_relative in enumerate(STARTS):
        first, stop = C0+core_relative, C0+core_relative+CORE_COUNT
        crop0, cropstop = core_relative-CROP_HALO, core_relative+CORE_COUNT+CROP_HALO
        for label in ONS:
            item = next(r for r in source["sources"] if r["label"] == label)
            h = item["current_header"]["data_attributes"]
            scan = Scan(label, "ON", arrays[label][:, crop0:cropstop], h["tstart"], TSAMP,
                        FCH1, DF, C0+crop0, np.arange(first, stop))
            frequencies = FCH1+DF*np.arange(first, stop)
            result, _ = search_scan(scan, frequencies, dt, drifts, cfg)
            if not np.isfinite(result["maximum_robust_box_track_score"]).all():
                raise ValueError("Nonfinite drift maxima")
            if not np.all(result["valid_hypothesis_count"] == 1526):
                raise ValueError("Incomplete drift hypotheses")
            numeric = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
            numeric["source_reference_channels"] = np.arange(first, stop)
            numeric["drift_grid_hz_s"] = drifts
            path = out/(label+"_tile_%02d_all_carriers.npz" % tile_index)
            np.savez(path, **numeric)
            receipts.append({"scan_id": label, "tile_index": tile_index,
                "gap_index_k": GAP_K[tile_index], "core_start_relative_channel": core_relative,
                "reference_channel_interval_half_open": [first, stop],
                "searched_carriers": CORE_COUNT, "valid_hypotheses_per_carrier": 1526,
                "path": path.name, "sha256": digest(path), "bytes": path.stat().st_size,
                "normalization": result["normalization"]})
            all_results[label].append(result)
            save(out/"DRIFT_CHECKPOINT.json", {"completed_scan_tiles": len(receipts),
                "expected_scan_tiles": 24, "complete": len(receipts) == 24,
                "completed_receipts": receipts})
            print("COMPLETED_GAP_DRIFT_TILE", label, tile_index, flush=True)
    tops = {}
    for label in ONS:
        results = all_results[label]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in results])
        winning_drift = np.concatenate([r["winning_drift_hz_s"] for r in results])
        winning_width = np.concatenate([r["winning_width_channels"] for r in results])
        channels = np.concatenate([np.arange(C0+x, C0+x+CORE_COUNT) for x in STARTS])
        order = np.lexsort((channels, -scores))
        chosen = []
        for j in order:
            j = int(j)
            if all(abs(int(channels[j])-int(channels[k])) > 3 for k in chosen):
                chosen.append(j)
            if len(chosen) == TOP:
                break
        if len(chosen) != TOP:
            raise ValueError("Incomplete top20 display family")
        h = next(r["current_header"]["data_attributes"] for r in source["sources"] if r["label"] == label)
        ref = (h["tstart"]-anchor)*86400+.5*TSAMP
        tops[label] = [{"track_id": label+"_gap_drift_rank_%02d" % rank,
            "family": "gap_drift", "originating_scan": label, "originating_role": "ON",
            "display_rank": rank, "source_reference_channel": int(channels[j]),
            "reference_frequency_hz": fresh.frequency(channels[j]),
            "reference_seconds_from_anchor": float(ref),
            "drift_hz_s": float(winning_drift[j]), "width_channels": int(winning_width[j]),
            "maximum_robust_box_track_score": float(scores[j]),
            "reference_core_tile": j//CORE_COUNT,
            "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
            for rank, j in enumerate(chosen, 1)]
    save(out/"DRIFT_TOP20.json", tops)
    return tops, {"completed_scan_tiles": len(receipts), "sparse_core_count": 8,
        "carriers_per_ON": 32768, "new_channel_edge_bandwidth_per_ON_hz": 32768*abs(DF),
        "new_native_chunk_fraction_searched": 32768/COUNT,
        "prior_plus_new_unique_carriers_per_ON": 163840,
        "prior_plus_new_native_chunk_fraction_searched": 163840/COUNT,
        "sparse_core_intervals_half_open": [[C0+x, C0+x+CORE_COUNT] for x in STARTS],
        "drift_grid_count": 763, "widths_channels": list(WIDTHS),
        "half_grid_mismatch_channels": mismatch, "display_suppression_channels": 3,
        "reference_time": "each ON's own first integration midpoint",
        "score_definition": "unchanged detector row-MAD standardized odd-box track sum / sqrt(Nrow*width)",
        "normalization": "each 4096-carrier static core, each row, unchanged 501-channel filtering"}


def fixed_profiles(arrays, source, normalization, tops, anchor, out):
    row_medians = np.asarray([normalization["row_power_medians"][s] for s in SCANS])
    if row_medians.shape != (6, 16) or not np.isfinite(row_medians).all() or (row_medians <= 0).any():
        raise ValueError("Invalid retained full-chunk row medians")
    headers = {r["label"]: r["current_header"]["data_attributes"] for r in source["sources"]}
    offsets = np.arange(-64, 65)
    flank = np.abs(offsets) > 3
    profiles_dir = out/"profiles"
    profiles_dir.mkdir()
    records = []
    for origin in ONS:
        for track in tops[origin][:3]:
            dt = np.asarray([(headers[s]["tstart"]-anchor)*86400+(np.arange(16)+.5)*TSAMP
                    - track["reference_seconds_from_anchor"] for s in SCANS])
            base = (track["reference_frequency_hz"]-FCH1)/DF
            centers = np.rint(base+track["drift_hz_s"]*dt/DF).astype(np.int64)
            indices = centers[:, :, None]-C0+offsets[None, None, :]
            if indices.min() < 0 or indices.max() >= COUNT:
                raise ValueError("Fixed six-scan profile exceeds acquired chunk")
            raw = np.asarray([arrays[s][np.arange(16)[:, None], indices[i]] for i, s in enumerate(SCANS)])
            normalized = raw.astype(np.float64)/row_medians[:, :, None]
            baseline = np.median(normalized[:, :, flank], axis=2)
            radius = track["width_channels"]//2
            center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
            residual = center-baseline
            mean_profile = np.mean(normalized-baseline[:, :, None], axis=1)
            if not np.isfinite(residual).all() or not np.isfinite(mean_profile).all():
                raise ValueError("Nonfinite fixed profile")
            patch_path = profiles_dir/(track["track_id"]+".npz")
            np.savez(patch_path, raw_power=raw, row_normalized_power=normalized,
                saved_full_chunk_row_medians=row_medians, frozen_source_channel_centers=centers,
                source_channel_offsets=offsets, times_seconds_from_reference=dt,
                center_row_normalized_power=center,
                fixed_flank_median_row_normalized_power=baseline,
                center_minus_flank_each_row=residual,
                mean_fixed_track_frequency_profile=mean_profile, scans=np.asarray(SCANS),
                df_hz=DF, source_channel0=C0,
                reference_frequency_hz=track["reference_frequency_hz"],
                drift_hz_s=track["drift_hz_s"], width_channels=track["width_channels"],
                fixed_source_channel_shift=0)
            records.append({"selected_track": track, "fixed_frequency_shift_channels": 0,
                "fixed_flank_offsets": "absolute channel offset > 3 within +/-64",
                "patch": {"path": "profiles/"+patch_path.name, "sha256": digest(patch_path),
                          "bytes": patch_path.stat().st_size},
                "scan_profiles": [{"scan_id": s,
                    "mean_center_minus_flank": float(residual[i].mean()),
                    "median_center_minus_flank": float(np.median(residual[i])),
                    "positive_rows": int(np.count_nonzero(residual[i] > 0)),
                    "first_eight_mean_center_minus_flank": float(residual[i, :8].mean()),
                    "last_eight_mean_center_minus_flank": float(residual[i, 8:].mean()),
                    "all_16_center_minus_flank_rows": residual[i].tolist(),
                    "all_16_raw_width_mean_power": raw[i, :, 64-radius:65+radius].mean(axis=1).tolist(),
                    "frozen_source_channel_centers": centers[i].tolist()}
                    for i, s in enumerate(SCANS)],
                "classification": "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"})
            save(out/"FIXED_TOP3_PROFILES.json", records)
            print("COMPLETED_GAP_FIXED_PROFILE", track["track_id"], flush=True)
    if len(records) != 9:
        raise ValueError("Incomplete frozen nine-profile family")
    return {"profile_count": len(records), "plot_count": 0, "all_rows_retained": 16,
        "source_top20_sha256": digest(out/"DRIFT_TOP20.json"),
        "saved_normalization_sha256": digest(ROOT/NORMALIZATION_PATH),
        "shift_frequency_drift_width_optimization_applied": False,
        "raw_patch_alignment": "rounded absolute source channels along exact fixed selected track in each actual scan",
        "time_profile_units": "width-mean raw power/full-chunk row median minus fixed flank median",
        "mean_profile_units": "mean track-aligned row-normalized power minus each row fixed flank median"}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("scope", "expected-scope-sha256", "compact-dir", "acquisition-summary", "outdir"):
        parser.add_argument("--"+flag, required=True)
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise TimeoutError("Gap analysis bounded CPU/wall deadline reached")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        scope, source, acquisition, normalization, anchor = load_contract(args)
        global np
        import numpy as np
        spec = importlib.util.spec_from_file_location("unchanged_fresh_search", ROOT/FRESH_PATH)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        fresh.np = np
        arrays, verified = fresh.load_power(args, source, acquisition)
        tops, search_summary = run_search(fresh, arrays, source, anchor, out)
        profile_summary = fixed_profiles(arrays, source, normalization, tops, anchor, out)
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if (measured["process_CPU_seconds_including_imports"] > CPU_CAP
                or measured["wall_seconds_including_imports"] > WALL_CAP
                or measured["peak_RSS_bytes"] > MEMORY_CAP):
            raise ResourceLimitExceeded("Measured process resource use exceeds frozen job caps")
        result = {"status": "COMPLETED_EIGHT_GAP_DRIFT_CORES_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY",
            "verified_inputs": verified, "search_summary": search_summary,
            "profile_summary": profile_summary, "scope_sha256": digest(args.scope),
            "script_sha256": digest(__file__), "source_manifest_sha256": SOURCE_SHA,
            "acquisition_summary_sha256": ACQUISITION_SHA,
            "new_telescope_HTTP_requests_during_analysis": 0,
            "new_telescope_BODY_bytes_during_analysis": 0, "MJD_anchor": anchor,
            "one_historical_visit": True, "source_values_already_opened_stationary": True,
            "prospective_for_new_gap_drift_outcomes": True, "blind_source_values": False,
            "qualified_sky_pilot": False, "OFF_veto_applied": False,
            "old_A_B_failure_statuses_changed": False, "old_holdouts_reopened": False,
            "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
            "numeric_retry_authorized": False,
            **measured,
            "limitations": [
                "Eight previously unsearched carrier cores; the rest of each gap remains unsearched",
                "Old and new carrier cores are disjoint; crop/trajectory halos may overlap",
                "Source values were already opened for stationary work; prospective only for these drift outcomes",
                "One historical visit; epoch1/2/3 are scan labels, not independent visits",
                "Post-selection ranks and correlated hypotheses; robust score is not calibrated SNR or a probability",
                "Fixed OFF predictions are descriptive and do not implement a qualified OFF veto",
                "A small OFF value at an exact predicted channel does not establish absence of a nearby OFF feature",
                "No barycentric correction, nonlinear tracks, other widths, injection recovery or false-alarm calibration"]}
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps(result, allow_nan=False), flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status":
            "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY" if isinstance(exc, (ResourceLimitExceeded, TimeoutError))
            else "INCOMPLETE_GAP_DRIFT_ANALYSIS_NO_RETRY",
            "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False,
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
