"""Two prospectively fixed safe-core batches; execute each once after public freeze.

Importing this wrapper reads no source values. The detector, source loader,
scalar frequency conversion and fixed-profile implementation remain unchanged.
Both batch lists are frozen before either new search outcome is inspected.
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
PRIOR_Q = tuple(1 + 8*k for k in range(32))
OLD_GAP_Q = tuple(5 + 32*k for k in range(8))
NEW_Q = tuple(q for q in range(1, 255) if q not in PRIOR_Q and q not in OLD_GAP_Q)
BATCH_Q = (NEW_Q[:107], NEW_Q[107:])
CPU_CAP, WALL_CAP, MEMORY_CAP = 1200, 1800, 4*1024**3
SOURCE_PATH = "tools/radio_fresh_band_20261009/source_manifest.json"
NORMALIZATION_PATH = "results/radio_fresh_band_20261009/stationary/NORMALIZATION.json"
FRESH_PATH = "tools/radio_fresh_band_20261009/fresh_search.py"
FRESH_SCOPE_PATH = "tools/radio_fresh_band_20261009/analysis_scope.json"
DETECTOR_PATH = "pilot_engine_20261008/detector.py"
GAP_PATH = "tools/radio_gap_drift_20261010/gap_search.py"
GAP_SCOPE_PATH = "tools/radio_gap_drift_20261010/scope.json"
PROPOSAL_PATH = "results/radio_gap_static_context_20261010/PROPOSAL.json"
ACTIVATION_PATH = "tools/radio_full_safe_20261010/ACTIVATION_SCOPE.json"
ACQUISITION_PATH = "results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json"
COMPACT_DIR = "results/radio_fresh_band_20261009/arrays"
SOURCE_SHA = "d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c"
ACQUISITION_SHA = "da165fe31ac4a70167b06f83b8f667fbb8604b595c642d3610fec68788bebf37"
DETECTOR_SHA = "1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45"
FRESH_SHA = "1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102"
GAP_SHA = "b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58"
PROPOSAL_SHA = "5401dee42b81ae03a19284721140cb453c4a71685f6ecec09bb71eb51ab36d1d"
SELECTION_SHA = "81bdd9b01d32c5d1fffd54df30d036a2aab29035c8d9e29d21b564e166d67120"
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
        raise ValueError("Full-safe wrapper differs from prospective freeze")
    expected = {
        "schema": "SETI_TWO_FIXED_107_SAFE_CORE_BATCHES_V1",
        "source_manifest_sha256": SOURCE_SHA, "acquisition_summary_sha256": ACQUISITION_SHA,
        "proposal_sha256": PROPOSAL_SHA, "metadata_selection_canonical_SHA256": SELECTION_SHA,
        "source_channel_interval_half_open": [C0, C0+COUNT], "count": COUNT,
        "rows_per_scan": 16, "scan_order": list(SCANS), "origin_scan_order": list(ONS),
        "fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP,
        "safe_q_interval_inclusive": [1, 254], "prior_q": list(PRIOR_Q),
        "previous_gap_q": list(OLD_GAP_Q), "remaining_q_ascending": list(NEW_Q),
        "batch_q": [list(qs) for qs in BATCH_Q], "batch_core_count": 107,
        "core_channel_count": CORE_COUNT, "crop_halo_channels": CROP_HALO,
        "expected_scan_tiles_per_batch": 321, "carriers_per_ON_per_batch": 438272,
        "drift_grid": {"first_hz_s": -4, "last_hz_s": 4, "count": 763},
        "widths_channels": list(WIDTHS), "valid_hypotheses_per_carrier": 1526,
        "rank_count_per_ON_per_batch": TOP, "display_suppression_channels": 3,
        "fixed_profile_ranks_per_ON_per_batch": 3, "expected_profile_count_per_batch": 9,
        "fixed_profile_shift_channels": 0, "profile_halfwidth_channels": 64,
        "CPU_cap_s_per_batch": CPU_CAP, "wall_cap_s_per_batch": WALL_CAP,
        "memory_cap_bytes_per_batch": MEMORY_CAP,
        "new_telescope_HTTP_request_cap": 0, "new_telescope_BODY_byte_cap": 0,
        "analysis_attempts_per_batch": 1, "numeric_retry_authorized": False,
        "old_holdouts_reopened": False, "original_A_B_failures_unchanged": True,
        "OFF_veto": False, "unqualified_exploratory_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "runtime_package_versions": VERSIONS,
        "output_directories": [f"results/radio_full_safe_20261010/batch_{i:02d}/measurement" for i in (1, 2)],
    }
    if any(scope.get(k) != value for k, value in expected.items()):
        raise ValueError("Scope differs from implemented fixed full-safe family")
    required_pins = {SOURCE_PATH, NORMALIZATION_PATH, FRESH_PATH, FRESH_SCOPE_PATH, DETECTOR_PATH,
                     GAP_PATH, GAP_SCOPE_PATH, PROPOSAL_PATH, ACTIVATION_PATH, ACQUISITION_PATH}
    pinned = scope["pinned_dependency_files"]
    if set(pinned) != required_pins:
        raise ValueError("Exactly ten metadata/code/acquisition dependencies must be pinned")
    for name, sha in pinned.items():
        if digest(ROOT/name) != sha:
            raise ValueError("Pinned dependency differs: " + name)
    if (pinned[SOURCE_PATH] != SOURCE_SHA or pinned[ACQUISITION_PATH] != ACQUISITION_SHA
            or pinned[DETECTOR_PATH] != DETECTOR_SHA or pinned[FRESH_PATH] != FRESH_SHA
            or pinned[GAP_PATH] != GAP_SHA or pinned[PROPOSAL_PATH] != PROPOSAL_SHA):
        raise ValueError("Existing source/implementation identities differ")
    if Path(args.acquisition_summary).resolve() != (ROOT/ACQUISITION_PATH).resolve():
        raise ValueError("Use the fixed acquisition receipt path")
    if Path(args.compact_dir).resolve() != (ROOT/COMPACT_DIR).resolve():
        raise ValueError("Use the fixed compact input directory")
    if Path(args.outdir).resolve() != (ROOT/expected["output_directories"][args.batch-1]).resolve():
        raise ValueError("Use the unique fixed directory for this batch; alternate retries forbidden")
    for name, version in VERSIONS.items():
        if importlib.metadata.version(name) != version:
            raise ValueError("Runtime package differs: " + name)
    proposal = json.loads((ROOT/PROPOSAL_PATH).read_text())
    activation = json.loads((ROOT/ACTIVATION_PATH).read_text())
    selection = proposal["metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (hashlib.sha256(canonical).hexdigest() != SELECTION_SHA
            or selection != scope["immutable_metadata_selection"]
            or selection != activation["immutable_metadata_selection"]
            or activation["metadata_selection_canonical_SHA256"] != SELECTION_SHA):
        raise ValueError("Both batch lists must match the prior immutable metadata selection")
    if not activation["user_authorization"]["approved_3600_CPU_stage"]:
        raise ValueError("The metadata proposal alone does not authorize this stage")
    if (selection["prior_q"] != list(PRIOR_Q) or selection["previous_gap_q"] != list(OLD_GAP_Q)
            or selection["remaining_q_ascending"] != list(NEW_Q)
            or selection["batch_q"] != [list(qs) for qs in BATCH_Q]):
        raise ValueError("Safe-core inventory or 107+107 split changed")
    for q in NEW_Q:
        start = q*CORE_COUNT
        if start-CROP_HALO < 0 or start+CORE_COUNT+CROP_HALO > COUNT:
            raise ValueError("Safe-core crop exceeds retained chunk")
    source = json.loads((ROOT/SOURCE_PATH).read_text())
    if [r["label"] for r in source["sources"]] != list(SCANS):
        raise ValueError("Six original chronological scans required")
    if [r["role"].upper() for r in source["sources"]] != ["ON", "OFF"]*3:
        raise ValueError("Original alternating roles required")
    anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
    previous_end = -math.inf
    for item in source["sources"]:
        header = item["current_header"]["data_attributes"]
        for observed, target, tolerance in ((header["fch1"]*1e6, FCH1, 1e-6),
                (header["foff"]*1e6, DF, 1e-12), (header["tsamp"], TSAMP, 1e-12)):
            if not math.isclose(observed, target, rel_tol=0, abs_tol=tolerance):
                raise ValueError("Actual header grid differs")
        start = (header["tstart"]-anchor)*86400
        if start < previous_end:
            raise ValueError("Scan sequence overlaps or is not chronological")
        previous_end = start+16*TSAMP
    acquisition = json.loads((ROOT/ACQUISITION_PATH).read_text())
    if (acquisition.get("status") != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
            or acquisition.get("source_manifest_sha256") != SOURCE_SHA
            or acquisition.get("physical_channel_interval_half_open") != [C0, C0+COUNT]):
        raise ValueError("Complete original native-chunk acquisition required")
    decoded = acquisition["decoded_files"]
    if len(decoded) != 6 or {r["scan_id"] for r in decoded} != set(SCANS):
        raise ValueError("Exactly six unique compact inputs required")
    if decoded != scope["compact_files_and_96_decoded_row_pins"]:
        raise ValueError("Compact or decoded-row identity differs from common scope")
    if any(r["shape"] != [16, 1, COUNT] or r["source_channel0"] != C0
           or [row["time_row"] for row in r["decoded_rows"]] != list(range(16)) for r in decoded):
        raise ValueError("All 96 exact rows and source offsets required")
    normalization = json.loads((ROOT/NORMALIZATION_PATH).read_text())
    if normalization["source_channel0"] != C0:
        raise ValueError("Wrong retained full-chunk normalization")
    return scope, source, acquisition, normalization, float(anchor)


def checkpoint(out, batch_id, qs, receipts):
    completed = {scan: [r["reference_core_q"] for r in receipts if r["scan_id"] == scan] for scan in ONS}
    save(out/"DRIFT_CHECKPOINT.json", {"batch_id": batch_id, "fixed_batch_q": list(qs),
        "completed_scan_tiles": len(receipts), "expected_scan_tiles": 321,
        "complete": len(receipts) == 321, "completed_q_by_ON": completed,
        "completed_core_count_by_ON": {scan: len(values) for scan, values in completed.items()},
        "completed_receipts": receipts})


def run_search(fresh, arrays, source, anchor, out, batch_id, qs):
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
    checkpoint(out, batch_id, qs, receipts)
    for tile_index, core_relative in enumerate(starts):
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
            checkpoint(out, batch_id, qs, receipts)
            print("COMPLETED_FULL_SAFE_DRIFT_TILE", batch_id, label, tile_index, qs[tile_index], flush=True)
    tops = {}
    for label in ONS:
        results = all_results[label]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in results])
        winning_drift = np.concatenate([r["winning_drift_hz_s"] for r in results])
        winning_width = np.concatenate([r["winning_width_channels"] for r in results])
        channels = np.concatenate([np.arange(C0+x, C0+x+CORE_COUNT) for x in starts])
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
            "family": "gap_drift", "batch_id": batch_id, "originating_scan": label, "originating_role": "ON",
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
    return tops, {"batch_id": batch_id, "completed_scan_tiles": len(receipts), "new_core_count": len(starts),
        "searched_q": list(qs), "carriers_per_ON": carriers,
        "new_channel_edge_bandwidth_per_ON_hz": carriers*abs(DF),
        "new_native_chunk_fraction_searched_this_batch": carriers/COUNT,
        "known_previous_core_count": 40, "previous_plus_this_batch_unique_carriers_per_ON": (40+len(starts))*CORE_COUNT,
        "completion_of_other_batch_inferred": False,
        "reference_core_intervals_half_open": [[C0+x, C0+x+CORE_COUNT] for x in starts],
        "drift_grid_count": 763, "widths_channels": list(WIDTHS),
        "half_grid_mismatch_channels": mismatch, "display_suppression_channels": 3,
        "reference_time": "each ON's own first integration midpoint",
        "score_definition": "unchanged detector row-MAD standardized odd-box track sum / sqrt(Nrow*width)",
        "normalization": "each 4096-carrier static core, each row, unchanged 501-channel filtering",
        "normalization_receipt_layout": "Full unchanged normalization values persisted once per tile, checkpoint hash references"}


def partial_counts(out):
    checkpoint_path = out/"DRIFT_CHECKPOINT.json"
    profile_path = out/"FIXED_TOP3_PROFILES.json"
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
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    for flag in ("scope", "expected-scope-sha256", "compact-dir", "acquisition-summary", "outdir"):
        parser.add_argument("--"+flag, required=True)
    args = parser.parse_args()
    expected_out = ROOT/f"results/radio_full_safe_20261010/batch_{args.batch:02d}/measurement"
    if Path(args.outdir).resolve() != expected_out.resolve():
        raise ValueError("One fixed output directory per batch is required")
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=False)
    def deadline(signum, frame):
        raise ResourceLimitExceeded("Full-safe batch CPU/wall deadline reached")
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        scope, source, acquisition, normalization, anchor = load_contract(args)
        global np
        import numpy as np
        fresh = load_module("unchanged_full_safe_source_loader", FRESH_PATH)
        old_gap = load_module("unchanged_gap_fixed_profiles", GAP_PATH)
        fresh.np = np
        old_gap.np = np
        arrays, verified = fresh.load_power(args, source, acquisition)
        tops, search_summary = run_search(fresh, arrays, source, anchor, out, args.batch, BATCH_Q[args.batch-1])
        profile_summary = old_gap.fixed_profiles(arrays, source, normalization, tops, anchor, out)
        for name, sha in scope["pinned_dependency_files"].items():
            if digest(ROOT/name) != sha:
                raise ValueError("Pinned metadata/code changed during batch: " + name)
        if digest(args.scope) != args.expected_scope_sha256 or digest(__file__) != scope["script_sha256"]:
            raise ValueError("Public common scope or executable changed during batch")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if (measured["process_CPU_seconds_including_imports"] > CPU_CAP
                or measured["wall_seconds_including_imports"] > WALL_CAP or measured["peak_RSS_bytes"] > MEMORY_CAP):
            raise ResourceLimitExceeded("Measured use exceeds frozen batch caps")
        if search_summary["completed_scan_tiles"] != 321 or profile_summary["profile_count"] != 9:
            raise ValueError("Incomplete batch search/profile family")
        result = {"status": "COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY", "batch_id": args.batch,
            "fixed_batch_q": list(BATCH_Q[args.batch-1]), "search_summary": search_summary,
            "fixed_profile_summary": profile_summary, "verified_source_inputs": verified,
            "scope_sha256": digest(args.scope), "script_sha256": digest(__file__),
            "proposal_sha256": PROPOSAL_SHA, "metadata_selection_canonical_SHA256": SELECTION_SHA,
            "source_manifest_sha256": SOURCE_SHA, "acquisition_summary_sha256": ACQUISITION_SHA,
            "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
            "new_telescope_HTTP_requests_during_analysis": 0, "new_telescope_BODY_bytes_during_analysis": 0,
            "MJD_anchor": anchor, "one_historical_visit": True, "source_values_previously_exposed": True,
            "prospective_for_these_new_drift_hypotheses": True, "blind_or_independent_validation": False,
            "qualified_sky_pilot": False, "OFF_veto_applied": False,
            "old_A_B_failure_statuses_changed": False, "old_holdouts_reopened": False,
            "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
            "numeric_retry_authorized": False, "completion_of_other_batch_inferred": False,
            **measured, "limitations": scope["limitations"]}
        save(out/"EXECUTION_RECEIPT.json", result)
        print(json.dumps(result, allow_nan=False), flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json", {"status": "INCOMPLETE_RESOURCE_LIMIT_NO_RETRY"
            if isinstance(exc, (ResourceLimitExceeded, TimeoutError)) else "INCOMPLETE_FULL_SAFE_BATCH_NO_RETRY",
            "batch_id": args.batch, "fixed_batch_q": list(BATCH_Q[args.batch-1]),
            "error_type": type(exc).__name__, "error": str(exc), "retry_authorized": False,
            "partial_outputs_preserved": True, **partial_counts(out),
            "process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_including_imports": time.monotonic()-started,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
