"""Two new native chunks, each two fixed 127-core batches, after public freeze.

Importing this module reads no files or scientific values. The pinned detector,
compact loader, scalar frequency conversion and fixed-profile function remain
unchanged; their native source origin is explicitly bound to the selected chunk.
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
CHUNKS, COUNT = (153, 154), 1048576
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
WIDTHS, CORE_COUNT, CROP_HALO, TOP = (1, 3), 4096, 4000, 20
BATCH_Q = (tuple(range(1, 128)), tuple(range(128, 255)))
CPU_CAP, WALL_CAP, MEMORY_CAP = 1500, 1800, 4*1024**3
HISTORICAL_SOURCE_PATH = "tools/radio_fresh_band_20261009/source_manifest.json"
FRESH_PATH = "tools/radio_fresh_band_20261009/fresh_search.py"
DETECTOR_PATH = "pilot_engine_20261008/detector.py"
GAP_PATH = "tools/radio_gap_drift_20261010/gap_search.py"
ACTIVATION_PATH = "tools/radio_next_bands_20261010/ACTIVATION_SCOPE.json"
ACTIVATION_SHA = "f69420b5444dc1109bafa2d33fef4d334c20b468cb50cf5ee0fecfb9d79936d4"
SELECTION_SHA = "d47604f9539486692569e9ecd810775d86574b0547102708d9469c57b1da2fd7"
HISTORICAL_SOURCE_SHA = "d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c"
DETECTOR_SHA = "1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45"
FRESH_SHA = "1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102"
GAP_SHA = "b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58"
VERSIONS = {"numpy": "2.3.5", "scipy": "1.17.0", "matplotlib": "3.10.8",
            "h5py": "3.15.1", "hdf5plugin": "7.1.0"}


class ResourceLimitExceeded(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
    temporary.replace(target)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_contract(args):
    if digest(args.scope) != args.expected_scope_sha256:
        raise ValueError("Scope differs from publicly frozen execution SHA")
    scope = json.loads(Path(args.scope).read_text())
    if digest(__file__) != scope["script_sha256"]:
        raise ValueError("Native-band executable differs from prospective freeze")
    expected = {
        "schema": "SETI_TWO_NEW_NATIVE_CHUNKS_FOUR_FIXED_127_CORE_BATCHES_V1",
        "metadata_selection_canonical_SHA256": SELECTION_SHA,
        "source_chunk_ids": list(CHUNKS), "source_chunk_channel_count": COUNT,
        "rows_per_scan": 16, "scan_order": list(SCANS), "origin_scan_order": list(ONS),
        "fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP,
        "safe_q_interval_inclusive": [1, 254], "batch_q": [list(qs) for qs in BATCH_Q],
        "batch_core_count": 127, "core_channel_count": CORE_COUNT,
        "crop_halo_channels": CROP_HALO, "expected_scan_tiles_per_batch": 381,
        "carriers_per_ON_per_batch": 520192,
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": list(WIDTHS), "valid_hypotheses_per_carrier": 1526,
        "rank_count_per_ON_per_batch": TOP, "display_suppression_channels": 3,
        "fixed_profile_ranks_per_ON_per_batch": 3, "expected_profile_count_per_batch": 9,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
        "CPU_cap_s_per_batch": CPU_CAP, "wall_cap_s_per_batch": WALL_CAP,
        "memory_cap_bytes_per_batch": MEMORY_CAP, "analysis_attempts_per_chunk_batch": 1,
        "numeric_retry_authorized": False, "old_holdouts_reopened": False,
        "protected_old_native_chunks_not_read": [156, 159],
        "original_A_B_failures_unchanged": True, "OFF_veto": False,
        "unqualified_exploratory_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "runtime_package_versions": VERSIONS,
        "new_telescope_HTTP_requests_during_analysis": 0,
        "new_telescope_BODY_bytes_during_analysis": 0,
        "output_directories": [f"results/radio_next_bands_20261010/chunk{c}/batch_{b:02d}/measurement"
                               for c in CHUNKS for b in (1, 2)],
    }
    if any(scope.get(k) != value for k, value in expected.items()):
        raise ValueError("Scope differs from implemented fixed new native-band family")
    required = {HISTORICAL_SOURCE_PATH: HISTORICAL_SOURCE_SHA, FRESH_PATH: FRESH_SHA,
                DETECTOR_PATH: DETECTOR_SHA, GAP_PATH: GAP_SHA, ACTIVATION_PATH: ACTIVATION_SHA}
    pinned = scope["pinned_dependency_files"]
    if any(pinned.get(name) != sha for name, sha in required.items()):
        raise ValueError("Original source and numerical implementation pins differ")
    for name, sha in pinned.items():
        if digest(ROOT/name) != sha:
            raise ValueError("Pinned dependency differs: " + name)
    for name, version in VERSIONS.items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Runtime package differs: " + name)
    activation = json.loads((ROOT/ACTIVATION_PATH).read_text())
    selection = activation["immutable_metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":"))+"\n").encode()
    if (hashlib.sha256(canonical).hexdigest() != SELECTION_SHA
            or scope["immutable_metadata_selection"] != selection
            or selection["native_chunk_indices"] != list(CHUNKS)
            or selection["batch_q"] != [list(qs) for qs in BATCH_Q]
            or activation["numeric_CPU_cap_s_per_batch"] != CPU_CAP
            or activation["planned_numeric_batch_count"] != 4
            or not activation["zero_cost_continuation_authorized"]):
        raise ValueError("All four lists and rolling-stage authorization must match the immutable activation")
    contexts = scope["chunk_contracts"]
    if set(contexts) != {str(c) for c in CHUNKS}:
        raise ValueError("Both fresh chunk contracts must be frozen together")
    context = contexts[str(args.chunk)]
    source0 = args.chunk*COUNT
    if context["source_channel_interval_half_open"] != [source0, source0+COUNT]:
        raise ValueError("Native chunk ID differs from physical source channels")
    for key in ("source_manifest_path", "acquisition_script_path", "acquisition_scope_path"):
        if pinned.get(context[key]) != context[key.replace("_path", "_sha256")]:
            raise ValueError("Prospective source/acquisition pin differs")
    if Path(args.compact_dir).resolve() != (ROOT/context["compact_directory"]).resolve():
        raise ValueError("Use the fixed chunk compact directory")
    if Path(args.acquisition_summary).resolve() != (ROOT/context["acquisition_summary_path"]).resolve():
        raise ValueError("Use the fixed chunk acquisition receipt")
    out = ROOT/f"results/radio_next_bands_20261010/chunk{args.chunk}/batch_{args.batch:02d}/measurement"
    if Path(args.outdir).resolve() != out.resolve():
        raise ValueError("Use one fixed output directory per chunk/batch; retries forbidden")
    source = json.loads((ROOT/context["source_manifest_path"]).read_text())
    previous = json.loads((ROOT/HISTORICAL_SOURCE_PATH).read_text())
    if (source["physical_channel_interval_half_open"] != [source0, source0+COUNT]
            or source["native_chunk_index"] != args.chunk or source["new_band_values_opened"] is not False
            or source["protected_prior_native_chunk_values_opened"] is not False
            or [r["label"] for r in source["sources"]] != list(SCANS)
            or [r["role"].upper() for r in source["sources"]] != ["ON", "OFF"]*3):
        raise ValueError("Exactly the six original chronological source scans are required")
    anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
    previous_end = -math.inf
    for item, original in zip(source["sources"], previous["sources"]):
        if any(item[key] != original[key] for key in ("label", "url", "etag", "source_file_bytes", "current_header")):
            raise ValueError("Fresh frequency chunks must preserve the same original source identities")
        h = item["current_header"]["data_attributes"]
        start = (h["tstart"]-anchor)*86400
        if start < previous_end:
            raise ValueError("Scan sequence is not chronological")
        previous_end = start+16*TSAMP
        chunks = item["chunks"]
        if (len(chunks) != 16 or [r["time_row"] for r in chunks] != list(range(16))
                or any(r["chunk_origin"] != [i, 0, source0] or r["filter_mask"] != 0
                       or r["decoded_size"] != COUNT*4 or r["stored_size"] <= 0
                       or r["byte_offset"] < 0 or r["byte_offset"]+r["stored_size"] > item["source_file_bytes"]
                       or r["byte_range"] != f"bytes={r['byte_offset']}-{r['byte_offset']+r['stored_size']-1}"
                       for i, r in enumerate(chunks))):
            raise ValueError("Saved metadata must describe every exact native row payload")
    acquisition = json.loads(Path(args.acquisition_summary).read_text())
    if (acquisition.get("status") != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
            or acquisition.get("source_manifest_sha256") != context["source_manifest_sha256"]
            or acquisition.get("script_sha256") != context["acquisition_script_sha256"]
            or acquisition.get("scope_sha256") != context["acquisition_scope_sha256"]
            or acquisition.get("source_channel0") != source0
            or acquisition.get("physical_channel_interval_half_open") != [source0, source0+COUNT]):
        raise ValueError("Acquisition receipt differs from prospectively frozen source and acquisition pipeline")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or {r["scan_id"] for r in decoded} != set(SCANS):
        raise ValueError("Exactly six unique completed compact inputs required")
    if any(r["shape"] != [16, 1, COUNT] or r["source_channel0"] != source0
           or [row["time_row"] for row in r["decoded_rows"]] != list(range(16)) for r in decoded):
        raise ValueError("All 96 exact decoded rows and native origins are required")
    return scope, context, source, acquisition, float(anchor), source0


def normalization(arrays, source0, out):
    row_medians = {s: np.median(arrays[s], axis=1).astype(np.float64) for s in SCANS}
    if any(not np.isfinite(v).all() or (v <= 0).any() for v in row_medians.values()):
        raise ValueError("Invalid full-chunk row normalization")
    result = {"method": "median of all 1048576 native channels in each row",
              "row_power_medians": {s: v.tolist() for s, v in row_medians.items()},
              "source_channel0": source0}
    save(out/"NORMALIZATION.json", result)
    return result


def checkpoint(out, chunk_id, batch_id, qs, receipts):
    completed = {scan: [r["reference_core_q"] for r in receipts if r["scan_id"] == scan] for scan in ONS}
    save(out/"DRIFT_CHECKPOINT.json", {"source_chunk_id": chunk_id, "batch_id": batch_id,
        "fixed_batch_q": list(qs), "completed_scan_tiles": len(receipts), "expected_scan_tiles": 381,
        "complete": len(receipts) == 381, "completed_q_by_ON": completed,
        "completed_core_count_by_ON": {scan: len(values) for scan, values in completed.items()},
        "completed_receipts": receipts})


def run_search(fresh, arrays, source, anchor, out, chunk_id, batch_id, qs, source0):
    from pilot_engine_20261008 import detector
    if Path(detector.__file__).resolve() != (ROOT/DETECTOR_PATH).resolve():
        raise ValueError("Detector import resolved outside the pinned project")
    Scan, Config, search_scan = detector.Scan, detector.Config, detector.search_scan
    cfg = Config(widths=WIDTHS)
    drifts = np.linspace(-4.0, 4.0, 763)
    dt = np.arange(16)*TSAMP
    mismatch = float((drifts[1]-drifts[0])*dt[-1]/(2*abs(DF)))
    if mismatch > .5+1e-12:
        raise ValueError("Drift-grid half mismatch exceeds half a native channel")
    starts = tuple(q*CORE_COUNT for q in qs)
    all_results = {s: [] for s in ONS}
    receipts = []
    checkpoint(out, chunk_id, batch_id, qs, receipts)
    for tile_index, core_relative in enumerate(starts):
        first, stop = source0+core_relative, source0+core_relative+CORE_COUNT
        crop0, cropstop = core_relative-CROP_HALO, core_relative+CORE_COUNT+CROP_HALO
        for label in ONS:
            item = next(r for r in source["sources"] if r["label"] == label)
            h = item["current_header"]["data_attributes"]
            scan = Scan(label, "ON", arrays[label][:, crop0:cropstop], h["tstart"], TSAMP,
                        FCH1, DF, source0+crop0, np.arange(first, stop))
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
            normalization_path = out/(label+"_tile_%02d_normalization.json" % tile_index)
            save(normalization_path, result["normalization"])
            receipts.append({"scan_id": label, "tile_index": tile_index,
                "reference_core_q": qs[tile_index], "core_start_relative_channel": core_relative,
                "reference_channel_interval_half_open": [first, stop],
                "searched_carriers": CORE_COUNT, "valid_hypotheses_per_carrier": 1526,
                "path": path.name, "sha256": digest(path), "bytes": path.stat().st_size,
                "normalization_path": normalization_path.name, "normalization_sha256": digest(normalization_path),
                "normalization_bytes": normalization_path.stat().st_size})
            all_results[label].append(result)
            checkpoint(out, chunk_id, batch_id, qs, receipts)
            print("COMPLETED_NATIVE_BAND_DRIFT_TILE", chunk_id, batch_id, label, tile_index, qs[tile_index], flush=True)
    tops = {}
    for label in ONS:
        results = all_results[label]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in results])
        winning_drift = np.concatenate([r["winning_drift_hz_s"] for r in results])
        winning_width = np.concatenate([r["winning_width_channels"] for r in results])
        channels = np.concatenate([np.arange(source0+x, source0+x+CORE_COUNT) for x in starts])
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
            "family": "native_chunk_drift", "source_chunk_id": chunk_id, "batch_id": batch_id, "originating_scan": label, "originating_role": "ON",
            "display_rank": rank, "source_reference_channel": int(channels[j]),
            "reference_frequency_hz": fresh.frequency(channels[j]),
            "reference_seconds_from_anchor": float(ref),
            "drift_hz_s": float(winning_drift[j]), "width_channels": int(winning_width[j]),
            "maximum_robust_box_track_score": float(scores[j]),
            "reference_core_tile": j//CORE_COUNT, "reference_core_q": qs[j//CORE_COUNT],
            "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
            for rank, j in enumerate(chosen, 1)]
    save(out/"DRIFT_TOP20.json", tops)
    carriers = len(starts)*CORE_COUNT
    return tops, {"source_chunk_id": chunk_id, "batch_id": batch_id, "completed_scan_tiles": len(receipts), "new_core_count": len(starts),
        "searched_q": list(qs), "carriers_per_ON": carriers,
        "new_channel_edge_bandwidth_per_ON_hz": carriers*abs(DF),
        "new_native_chunk_fraction_searched_this_batch": carriers/COUNT,
        "known_previous_core_count_in_this_chunk": 0,
        "completion_of_other_batch_inferred": False,
        "reference_core_intervals_half_open": [[source0+x, source0+x+CORE_COUNT] for x in starts],
        "drift_grid_count": 763, "widths_channels": list(WIDTHS),
        "half_grid_mismatch_channels": mismatch, "display_suppression_channels": 3,
        "reference_time": "each ON's own first integration midpoint",
        "score_definition": "unchanged detector row-MAD standardized odd-box track sum / sqrt(Nrow*width)",
        "normalization": "each 4096-carrier static core, each row, unchanged 501-channel filtering",
        "normalization_receipt_layout": "Full unchanged normalization values persisted once per tile, checkpoint hash references"}


def partial_counts(out):
    checkpoint_path, profile_path = out/"DRIFT_CHECKPOINT.json", out/"FIXED_TOP3_PROFILES.json"
    values = {"completed_scan_tiles": 0, "completed_profiles": 0}
    if checkpoint_path.is_file():
        state = json.loads(checkpoint_path.read_text())
        values.update(completed_scan_tiles=state["completed_scan_tiles"],
                      completed_q_by_ON=state["completed_q_by_ON"], checkpoint_sha256=digest(checkpoint_path))
    if profile_path.is_file():
        values.update(completed_profiles=len(json.loads(profile_path.read_text())),
                      profile_checkpoint_sha256=digest(profile_path))
    return values


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk", type=int, choices=CHUNKS, required=True)
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    for flag in ("scope", "expected-scope-sha256", "compact-dir", "acquisition-summary", "outdir"):
        parser.add_argument("--"+flag, required=True)
    args = parser.parse_args()
    expected_out = ROOT/f"results/radio_next_bands_20261010/chunk{args.chunk}/batch_{args.batch:02d}/measurement"
    if Path(args.outdir).resolve() != expected_out.resolve():
        raise ValueError("One fixed output directory per chunk/batch is required")
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise ResourceLimitExceeded("Native-band batch CPU/wall deadline reached")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        scope, context, source, acquisition, anchor, source0 = load_contract(args)
        acquisition_sha = digest(args.acquisition_summary)
        save(out/"INPUT_PINS.json", {"source_chunk_id": args.chunk, "batch_id": args.batch,
             "scope_sha256": args.expected_scope_sha256, "script_sha256": digest(__file__),
             "source_manifest_sha256": context["source_manifest_sha256"],
             "acquisition_summary_sha256": acquisition_sha,
             "compact_files_and_96_decoded_row_pins": acquisition["decoded_files"]})
        global np
        import numpy as np
        fresh = load_module("unchanged_new_band_source_loader", FRESH_PATH)
        old_gap = load_module("unchanged_new_band_fixed_profiles", GAP_PATH)
        fresh.np, fresh.C0 = np, source0
        old_gap.np, old_gap.C0 = np, source0
        old_gap.NORMALIZATION_PATH = (out/"NORMALIZATION.json").relative_to(ROOT).as_posix()
        arrays, verified = fresh.load_power(args, source, acquisition)
        row_normalization = normalization(arrays, source0, out)
        tops, search_summary = run_search(fresh, arrays, source, anchor, out, args.chunk,
                                          args.batch, BATCH_Q[args.batch-1], source0)
        profile_summary = old_gap.fixed_profiles(arrays, source, row_normalization, tops, anchor, out)
        for name, sha in scope["pinned_dependency_files"].items():
            if digest(ROOT/name) != sha:
                raise ValueError("Pinned metadata/code changed during batch: " + name)
        if (digest(args.scope) != args.expected_scope_sha256 or digest(__file__) != scope["script_sha256"]
                or digest(args.acquisition_summary) != acquisition_sha):
            raise ValueError("Scope, executable or acquisition receipt changed during batch")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if (measured["process_CPU_seconds_including_imports"] > CPU_CAP
                or measured["wall_seconds_including_imports"] > WALL_CAP or measured["peak_RSS_bytes"] > MEMORY_CAP):
            raise ResourceLimitExceeded("Measured use exceeds frozen native-band batch caps")
        if search_summary["completed_scan_tiles"] != 381 or profile_summary["profile_count"] != 9:
            raise ValueError("Incomplete batch search/profile family")
        result = {"status": "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY",
            "source_chunk_id": args.chunk, "batch_id": args.batch,
            "profile_identity_fields": ["source_chunk_id", "batch_id", "track_id"],
            "fixed_batch_q": list(BATCH_Q[args.batch-1]), "search_summary": search_summary,
            "fixed_profile_summary": profile_summary, "verified_source_inputs": verified,
            "scope_sha256": digest(args.scope), "script_sha256": digest(__file__),
            "source_manifest_sha256": context["source_manifest_sha256"],
            "acquisition_summary_sha256": acquisition_sha,
            "saved_normalization_sha256": digest(out/"NORMALIZATION.json"),
            "metadata_selection_canonical_SHA256": scope["metadata_selection_canonical_SHA256"],
            "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
            "new_telescope_HTTP_requests_during_analysis": 0, "new_telescope_BODY_bytes_during_analysis": 0,
            "MJD_anchor": anchor, "one_historical_visit": True,
            "source_chunk_values_received_after_prospective_freeze": True,
            "blind_or_independent_validation": False, "qualified_sky_pilot": False,
            "OFF_veto_applied": False, "old_A_B_failure_statuses_changed": False,
            "old_holdouts_reopened": False, "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
            "whole_original_source_MD5_verified": False, "numeric_retry_authorized": False,
            "completion_of_other_chunk_or_batch_inferred": False, **measured,
            "limitations": scope["limitations"]}
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps(result, allow_nan=False), flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status": "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
            if isinstance(exc, (ResourceLimitExceeded, TimeoutError)) else "INCOMPLETE_NEW_NATIVE_BATCH_NO_RETRY",
            "source_chunk_id": args.chunk, "batch_id": args.batch,
            "fixed_batch_q": list(BATCH_Q[args.batch-1]), "error_type": type(exc).__name__,
            "error": str(exc), "retry_authorized": False, "partial_outputs_preserved": True,
            **partial_counts(out), "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()

