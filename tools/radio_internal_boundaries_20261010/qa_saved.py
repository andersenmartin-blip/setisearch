"""Once-only integrity QA of one completed joined-boundary saved-output family.

No source HDF5 is read and no detector or source-loader module is imported.
Saved maxima reconstruct only the frozen display rank; retained patches check
the old fixed-profile algebra using the saved joined-pair row denominator.
The denominator's source-median authenticity is not independently remeasured.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 300, 2 * 1024**3
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
PAIRS = {"153_154": (153, 154), "154_155": (154, 155), "157_158": (157, 158)}
NATIVE_COUNT, COUNT, QS = 1048576, 2097152, [255, 256]
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
FULLNORM_METHOD = "median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)"
TOOLS = "tools/radio_internal_boundaries_20261010"
RESULTS = "results/radio_internal_boundaries_20261010"
EXPECTED_COUNTS = {"maps": 6, "normalization_files": 6, "carrier_maximum_records": 24576,
                   "top20_entries": 60, "patches": 9, "scan_profiles": 54, "time_rows": 864,
                   "retained_raw_patch_cells": 111456, "binary_and_normalization_hashes": 21}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def same(actual, expected, message):
    check(np.array_equal(actual, expected), message)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pair", choices=tuple(PAIRS), required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    left, right = PAIRS[args.pair]
    pair_id, C0, qs = "pair" + args.pair, left * NATIVE_COUNT, QS
    out = root / RESULTS / pair_id / "measurement"
    review = root / RESULTS / pair_id / "review"
    review.mkdir(parents=True, exist_ok=True)
    receipt_path, failure_path, lock = (review / name for name in
                                      ("QA_RECEIPT.json", "QA_FAILURE_RECEIPT.json", "QA_STARTED.json"))
    check(not any(path.exists() for path in (receipt_path, failure_path, lock)), "Saved QA is authorized once per pair")
    check(len(args.freeze_commit) == 40 and all(c in "0123456789abcdef" for c in args.freeze_commit),
          "Exact public freeze commit required")
    with lock.open("x") as stream:
        json.dump({"status": "STARTED_ONCE_ONLY_JOINED_BOUNDARY_SAVED_QA", "pair_id": pair_id,
                   "freeze_commit": args.freeze_commit, "script_sha256": digest(Path(__file__))}, stream)
        stream.write("\n")

    def deadline(signum, frame):
        raise TimeoutError("Joined-boundary saved QA CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    counts = {key: 0 for key in EXPECTED_COUNTS}
    json_pins, output_pins = {}, {}

    def confined(path):
        path = path.resolve()
        check(path.is_relative_to(root), "Input reference escapes project root")
        return path

    def read_json(path, expected_sha=None, expected_size=None):
        path = confined(path)
        raw = path.read_bytes()
        pin = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        check(expected_sha is None or pin["sha256"] == expected_sha, "JSON SHA differs: " + str(path))
        check(expected_size is None or pin["bytes"] == expected_size, "JSON size differs: " + str(path))
        check(path not in json_pins or json_pins[path] == pin, "JSON admission changed: " + str(path))
        json_pins[path] = pin
        return json.loads(raw)

    def check_ref(directory, filename, expected_hash, expected_size):
        path = confined(directory / filename)
        check(path.is_relative_to(directory.resolve()), "Saved output reference escapes pair directory")
        pin = {"sha256": expected_hash, "bytes": expected_size}
        check(path.stat().st_size == expected_size and digest(path) == expected_hash, "Saved output bytes differ: " + filename)
        check(path not in output_pins or output_pins[path] == pin, "Conflicting saved output byte declarations")
        output_pins[path] = pin
        return path

    def read_output_bytes(path):
        raw = path.read_bytes()
        pin = output_pins[path.resolve()]
        check(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
              "Loaded NPZ bytes differ from admitted output pin")
        return raw

    try:
        scope_path = confined(args.scope)
        scope_sha = args.expected_scope_sha256
        check(len(scope_sha) == 64 and all(c in "0123456789abcdef" for c in scope_sha), "Exact frozen scope SHA required")
        scope = read_json(scope_path, scope_sha)
        check(scope["saved_QA_CPU_cap_s_per_pair"] == CPU_CAP
              and scope["saved_QA_wall_cap_s_per_pair"] == WALL_CAP
              and scope["saved_QA_memory_cap_bytes_per_pair"] == MEMORY_CAP,
              "Frozen saved-QA caps differ from implemented constants")
        own_path = Path(__file__).resolve()
        own_sha = digest(own_path)
        dependencies = scope["pinned_dependency_files"]
        own_name = own_path.relative_to(root).as_posix()
        check(dependencies[own_name] == {"sha256": own_sha, "bytes": own_path.stat().st_size}, "Frozen QA code identity differs")
        for name, pin in dependencies.items():
            path = confined(root / name)
            check(path.suffix.lower() not in (".h5", ".hdf5", ".npz", ".npy"), "Saved-only QA dependency must be code or metadata")
            check(set(pin) == {"sha256", "bytes"} and path.stat().st_size == pin["bytes"]
                  and digest(path) == pin["sha256"], "Frozen metadata/code dependency differs: " + name)
        check(set(scope["pair_contracts"]) == {"pair" + p for p in PAIRS}, "Only the three fixed retained pairs are admitted")
        check(set(scope["chunk_contracts"]) == {"153", "154", "155", "157", "158"}, "Protected and unretained neighbors remain closed")
        pair = scope["pair_contracts"][pair_id]
        check(pair["source_chunk_ids"] == [left, right] and pair["source_channel0"] == C0
              and pair["source_channel_count"] == COUNT and pair["joined_reference_core_q"] == qs
              and root / pair["measurement_directory"] == out, "Pair identity or fixed geometry differs")
        wrapper_path = confined(root / scope["script_path"])
        wrapper_sha = scope["script_sha256"]
        check(digest(wrapper_path) == wrapper_sha, "Frozen boundary wrapper differs")
        check(not (out / "FAILURE_RECEIPT.json").exists(), "A completed pair cannot have an original numerical failure receipt")
        execution_path = out / "EXECUTION_RECEIPT.json"
        result = read_json(execution_path)
        execution_sha = json_pins[execution_path.resolve()]["sha256"]
        check(result["status"] == "COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY"
              and result["pair_id"] == pair_id and result["scope_sha256"] == scope_sha
              and result["script_sha256"] == wrapper_sha and result["fixed_pair_q"] == qs
              and result["source_chunk_ids"] == [left, right] and result["source_channel0"] == C0
              and result["source_channel_count"] == COUNT
              and result["public_freeze_commit"] == args.freeze_commit,
              "Exact completed frozen pair required")
        six_names = ("EXECUTION_RECEIPT.json", "INPUT_PINS.json", "DRIFT_CHECKPOINT.json",
                     "DRIFT_TOP20.json", "FIXED_TOP3_PROFILES.json", "NORMALIZATION.json")
        expected_measurement_names = set(six_names)
        expected_measurement_names.update(scan + "_tile_%02d_%s" % (i, suffix)
                                          for i in (0, 1) for scan in ONS
                                          for suffix in ("all_carriers.npz", "normalization.json"))
        expected_measurement_names.update("profiles/" + scan + "_gap_drift_rank_%02d.npz" % rank
                                          for scan in ONS for rank in (1, 2, 3))
        check(len(expected_measurement_names) == 27
              and {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()} == expected_measurement_names,
              "Exactly the27 completed measurement files are required; no extras or partial temporary files")
        for field, cap in (("process_CPU_seconds_including_imports", 120), ("wall_seconds_including_imports", 1800),
                           ("peak_RSS_bytes", 4 * 1024**3)):
            check(0 < result[field] <= cap, "Numeric pair resource cap differs: " + field)
        for field, expected in (("new_HTTP_requests", 0), ("new_BODY_bytes", 0), ("cost_DKK", 0),
                                ("qualified_sky_pilot", False), ("OFF_veto_applied", False),
                                ("original_scopes_terminal_statuses_and_outputs_modified", False), ("old_holdouts_reopened", False),
                                ("numeric_retry_authorized", False)):
            check(result[field] == expected, "Frozen exploratory contract differs: " + field)
        summary = result["search_summary"]
        for field, expected in (("pair_id", pair_id), ("completed_scan_tiles", 6), ("new_core_count", 2),
                                ("searched_q", qs), ("carriers_per_ON", 8192), ("drift_grid_count", 763),
                                ("widths_channels", [1, 3]), ("display_suppression_channels", 3),
                                ("reference_core_intervals_half_open", [[C0 + q * 4096, C0 + (q + 1) * 4096] for q in qs])):
            check(summary[field] == expected, "Completed pair search summary differs: " + field)
        input_pins_path = out / "INPUT_PINS.json"
        input_pins = read_json(input_pins_path)
        check(input_pins["pair_id"] == pair_id and input_pins["scope_sha256"] == scope_sha
              and input_pins["script_sha256"] == wrapper_sha
              and input_pins["source_chunk_ids"] == [left, right]
              and input_pins["source_channel0"] == C0 and input_pins["source_channel_count"] == COUNT
              and input_pins["public_freeze_commit"] == args.freeze_commit,
              "Pair runtime input-pins identity differs")
        sources, expected_source_inputs, acquisition_shas = [], {}, {}
        for chunk in (left, right):
            context = scope["chunk_contracts"][str(chunk)]
            source_path = root / context["source_manifest_path"]
            source = read_json(source_path, dependencies[context["source_manifest_path"]]["sha256"])
            acquisition_path = root / context["acquisition_summary_path"]
            acquisition = read_json(acquisition_path, dependencies[context["acquisition_summary_path"]]["sha256"])
            acquisition_sha = json_pins[acquisition_path.resolve()]["sha256"]
            acquisition_shas[str(chunk)] = acquisition_sha
            aq_path = root / context["acquisition_QA_path"]
            aq = read_json(aq_path, dependencies[context["acquisition_QA_path"]]["sha256"])
            check(acquisition["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
                  and acquisition["source_channel0"] == chunk * NATIVE_COUNT
                  and acquisition["physical_channel_interval_half_open"] == [chunk * NATIVE_COUNT, (chunk + 1) * NATIVE_COUNT]
                  and acquisition["source_manifest_sha256"] == dependencies[context["source_manifest_path"]]["sha256"],
                  "Exact retained acquisition required")
            check(aq["status"] == "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
                  and aq["source_chunk_id"] == chunk and aq["acquisition_result_sha256"] == acquisition_sha,
                  "Retained acquisition QA identity differs")
            decoded = acquisition["decoded_files"]
            check(len(decoded) == 6 and [r["scan_id"] for r in decoded] == list(SCANS)
                  and all(r["shape"] == [16, 1, NATIVE_COUNT] and r["source_channel0"] == chunk * NATIVE_COUNT
                          and [row["time_row"] for row in r["decoded_rows"]] == list(range(16)) for r in decoded),
                  "All twelve source files and192 row declarations must be pinned")
            expected_source_inputs[str(chunk)] = {"source_manifest_sha256": dependencies[context["source_manifest_path"]]["sha256"],
                "acquisition_summary_sha256": acquisition_sha, "acquisition_QA_sha256": json_pins[aq_path.resolve()]["sha256"],
                "compact_files_and_96_decoded_row_pins": decoded}
            verified = result["verified_source_inputs"][str(chunk)]
            check(set(verified) == set(SCANS), "Six runtime-verified compacts per native side required")
            for r in decoded:
                check(verified[r["scan_id"]] == {"path": r["array_file"], "file_sha256": r["file_sha256"], "bytes": r["bytes"]},
                      "Runtime verified native compact differs")
            check(source["physical_channel_interval_half_open"] == [chunk * NATIVE_COUNT, (chunk + 1) * NATIVE_COUNT]
                  and [r["label"] for r in source["sources"]] == list(SCANS), "Retained manifest identity differs")
            sources.append(source)
        check(input_pins["source_inputs"] == expected_source_inputs, "Exact runtime manifests/acquisitions/192 source-row pins differ")
        check(result["source_inputs"] == expected_source_inputs, "Completed execution source receipt pins differ")
        admission = input_pins["runtime_admission_receipts"]
        check(admission == result["runtime_admission_receipts"], "Completed execution late runtime pins differ")
        if pair_id == "pair157_158":
            gate = scope["runtime_158_admission"]
            expected_admission = {j[k] for j in gate["jobs"] for k in ("execution_receipt_path", "QA_receipt_path")}
            expected_admission.add(gate["source_audit_receipt_path"])
            check(len(gate["jobs"]) == 2 and {j["batch_id"] for j in gate["jobs"]} == {1, 2}
                  and len(expected_admission) == 5 and set(admission) == expected_admission,
                  "Both original158 completed executions, saved QAs and source audit must be runtime pinned")
            for name, pin in admission.items():
                read_json(root / name, pin["sha256"], pin["bytes"])
            old_counts = {"maps": 381, "normalization_files": 381, "carrier_maximum_records": 1560576,
                          "top20_entries": 60, "patches": 9, "scan_profiles": 54, "time_rows": 864,
                          "retained_raw_patch_cells": 111456, "binary_and_normalization_hashes": 771}
            for job in gate["jobs"]:
                ep, qp = root / job["execution_receipt_path"], root / job["QA_receipt_path"]
                e, q = read_json(ep), read_json(qp)
                check(e["status"] == "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
                      and e["source_chunk_id"] == 158 and e["batch_id"] == job["batch_id"]
                      and e["scope_sha256"] == gate["original_scope_sha256"]
                      and e["script_sha256"] == gate["original_script_sha256"]
                      and e["search_summary"]["completed_scan_tiles"] == 381
                      and e["fixed_profile_summary"]["profile_count"] == 9,
                      "Late original158 numerical completion differs")
                check(q["status"] == "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
                      and q["source_chunk_id"] == 158 and q["batch_id"] == job["batch_id"]
                      and q["public_scope_sha256"] == gate["original_scope_sha256"]
                      and q["public_wrapper_sha256"] == gate["original_script_sha256"]
                      and q["execution_receipt_sha256"] == admission[job["execution_receipt_path"]]["sha256"]
                      and q["qa_script_sha256"] == gate["saved_QA_script_sha256"] and q["counts"] == old_counts,
                      "Late original158 independent saved QA differs")
            a = read_json(root / gate["source_audit_receipt_path"])
            check(a["status"] == "PASS_18_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE"
                  and a["public_scope_sha256"] == gate["original_scope_sha256"]
                  and a["public_wrapper_sha256"] == gate["original_script_sha256"]
                  and a["audit_script_sha256"] == gate["source_audit_script_sha256"]
                  and a["counts"] == {"compact_files": 6, "decoded_rows": 96, "patches": 18,
                                       "scan_profiles": 108, "time_rows": 1728, "raw_cells_bitwise_checked": 222912},
                  "Late original158 source-cell authentication differs")
        else:
            check(admission == {}, "Late158 receipts must not be fabricated for another pair")
        check(set(result["verified_source_inputs"]) == {str(left), str(right)}, "Unexpected runtime native source side")
        for a, b in zip(sources[0]["sources"], sources[1]["sources"]):
            check(all(a[k] == b[k] for k in ("label", "role", "url", "etag", "source_file_bytes", "current_header")),
                  "Pair must retain identical source scan identities and exact headers")
        headers = {r["label"]: r["current_header"]["data_attributes"] for r in sources[0]["sources"]}
        anchor = min(h["tstart"] for h in headers.values())
        check(result["MJD_anchor"] == anchor, "Pair actual header time anchor differs")
        checkpoint_path = out / "DRIFT_CHECKPOINT.json"
        checkpoint = read_json(checkpoint_path)
        check(checkpoint["pair_id"] == pair_id and checkpoint["fixed_pair_q"] == qs
              and checkpoint["complete"] is True and checkpoint["completed_scan_tiles"] == 6
              and checkpoint["expected_scan_tiles"] == 6, "Complete six-map checkpoint required")
        expected_pairs = [(scan, i, q) for i, q in enumerate(qs) for scan in ONS]
        global np
        import numpy as np
        check(np.__version__ == "2.3.5", "Frozen saved-QA NumPy version differs")
        drift_grid = np.linspace(-4.0, 4.0, 763)
        entries = checkpoint["completed_receipts"]
        check([(r["scan_id"], r["tile_index"], r["reference_core_q"]) for r in entries] == expected_pairs,
              "Map receipt order or identity differs")
        for scan in ONS:
            check(checkpoint["completed_q_by_ON"][scan] == qs
                  and checkpoint["completed_core_count_by_ON"][scan] == 2,
                  "Checkpoint ON inventory differs")
        saved = {scan: [] for scan in ONS}
        map_keys = {"frequency_hz_at_tref", "maximum_robust_box_track_score", "winning_drift_hz_s",
                    "winning_width_channels", "valid_hypothesis_count", "source_reference_channels", "drift_grid_hz_s"}
        for r in entries:
            first = C0 + r["reference_core_q"] * 4096
            channels = np.arange(first, first + 4096)
            check(r["reference_channel_interval_half_open"] == [first, first + 4096]
                  and r["core_start_relative_channel"] == r["reference_core_q"] * 4096
                  and r["searched_carriers"] == 4096 and r["valid_hypotheses_per_carrier"] == 1526,
                  "Map coordinate/count receipt differs")
            path = check_ref(out, r["path"], r["sha256"], r["bytes"])
            normpath = check_ref(out, r["normalization_path"], r["normalization_sha256"], r["normalization_bytes"])
            normalization = read_json(normpath, r["normalization_sha256"], r["normalization_bytes"])
            check(set(normalization) == {"row_power_median", "row_residual_median",
                                         "row_winsorized_residual_location", "row_residual_MAD_scale",
                                         "normalization_unmasked_counts", "normalization_source_channels"},
                  "Normalization JSON schema differs")
            same(np.asarray(normalization["normalization_source_channels"]), channels, "Normalization core differs")
            same(np.asarray(normalization["normalization_unmasked_counts"]), np.full(16, 4096), "Normalization mask counts differ")
            for field in ("row_power_median", "row_residual_median", "row_winsorized_residual_location", "row_residual_MAD_scale"):
                values = np.asarray(normalization[field])
                check(values.shape == (16,) and np.isfinite(values).all(), "Invalid normalization rows: " + field)
                if field in ("row_power_median", "row_residual_MAD_scale"):
                    check((values > 0).all(), "Nonpositive normalization scale")
            with np.load(io.BytesIO(read_output_bytes(path)), allow_pickle=False) as z:
                check(set(z.files) == map_keys, "Map array schema differs")
                m = {k: z[k] for k in z.files}
            for field, dtype in (("frequency_hz_at_tref", "<f8"), ("maximum_robust_box_track_score", "<f8"),
                                 ("winning_drift_hz_s", "<f8"), ("winning_width_channels", "<i2"),
                                 ("valid_hypothesis_count", "<i8"), ("source_reference_channels", "<i8"),
                                 ("drift_grid_hz_s", "<f8")):
                check(m[field].dtype == np.dtype(dtype), "Map precision/schema differs: " + field)
            same(m["source_reference_channels"], channels, "Map source channels differ")
            same(m["frequency_hz_at_tref"], FCH1 + DF * channels, "Map source frequencies differ")
            same(m["drift_grid_hz_s"], drift_grid, "Map drift grid differs")
            same(m["valid_hypothesis_count"], np.full(4096, 1526), "Incomplete saved hypothesis validity")
            for field in ("maximum_robust_box_track_score", "winning_drift_hz_s", "winning_width_channels"):
                check(m[field].shape == (4096,) and np.isfinite(m[field]).all(), "Nonfinite/map shape differs: " + field)
            check(np.isin(m["winning_drift_hz_s"], drift_grid).all(), "Winner outside frozen drift grid")
            check(np.isin(m["winning_width_channels"], (1, 3)).all(), "Winner outside frozen widths")
            saved[r["scan_id"]].append(m)
            counts["maps"] += 1; counts["normalization_files"] += 1
            counts["carrier_maximum_records"] += 4096; counts["binary_and_normalization_hashes"] += 2

        tops_path = out / "DRIFT_TOP20.json"
        tops = read_json(tops_path, result["fixed_profile_summary"]["source_top20_sha256"])
        check(set(tops) == set(ONS), "Top20 origin inventory differs")
        for scan in ONS:
            channels = np.concatenate([m["source_reference_channels"] for m in saved[scan]])
            scores = np.concatenate([m["maximum_robust_box_track_score"] for m in saved[scan]])
            drifts = np.concatenate([m["winning_drift_hz_s"] for m in saved[scan]])
            widths = np.concatenate([m["winning_width_channels"] for m in saved[scan]])
            chosen = []
            for index in np.lexsort((channels, -scores)):
                j = int(index)
                if all(abs(int(channels[j]) - int(channels[k])) > 3 for k in chosen):
                    chosen.append(j)
                if len(chosen) == 20:
                    break
            check(len(tops[scan]) == 20, "Top20 count differs")
            for rank, (track, j) in enumerate(zip(tops[scan], chosen), 1):
                expected = {"track_id": scan + "_gap_drift_rank_%02d" % rank,
                            "family": "internal_boundary_drift", "pair_id": pair_id,
                            "source_chunk_id": left if qs[j // 4096] == 255 else right,
                            "source_native_core_q": 255 if qs[j // 4096] == 255 else 0,
                            "originating_scan": scan, "originating_role": "ON", "display_rank": rank,
                            "source_reference_channel": int(channels[j]),
                            "reference_frequency_hz": FCH1 + DF * int(channels[j]),
                            "reference_seconds_from_anchor": (headers[scan]["tstart"] - anchor) * 86400 + .5 * TSAMP,
                            "drift_hz_s": float(drifts[j]), "width_channels": int(widths[j]),
                            "maximum_robust_box_track_score": float(scores[j]),
                            "reference_core_tile": j // 4096, "reference_core_q": qs[j // 4096],
                            "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
                check(track == expected, "Saved top20 differs from unchanged tie/NMS reconstruction")
                counts["top20_entries"] += 1
        profile_summary = result["fixed_profile_summary"]
        check(profile_summary["source_top20_sha256"] == digest(tops_path)
              and profile_summary["profile_count"] == 9 and profile_summary["all_rows_retained"] == 16
              and profile_summary["plot_count"] == 0
              and not profile_summary["shift_frequency_drift_width_optimization_applied"],
              "Profile family summary differs")
        fullnorm_path = out / "NORMALIZATION.json"
        check(profile_summary["saved_normalization_sha256"] == digest(fullnorm_path), "Joined-pair profile normalization pin differs")
        fullnorm = read_json(fullnorm_path, result["saved_normalization_sha256"])
        check(result["saved_normalization_sha256"] == digest(fullnorm_path)
              and fullnorm["source_channel0"] == C0, "Joined-pair profile normalization source pin differs")
        check(set(fullnorm) == {"method", "row_power_medians", "source_channel0", "source_channel_count", "source_chunk_ids"}
              and fullnorm["method"] == FULLNORM_METHOD
              and fullnorm["source_channel_count"] == COUNT and fullnorm["source_chunk_ids"] == [left, right]
              and set(fullnorm["row_power_medians"]) == set(SCANS),
              "Joined-pair profile normalization schema differs")
        rowmedians = np.asarray([fullnorm["row_power_medians"][scan] for scan in SCANS])
        check(rowmedians.shape == (6, 16) and np.isfinite(rowmedians).all() and (rowmedians > 0).all(),
              "Invalid six-scan joined-pair profile row medians")
        records_path = out / "FIXED_TOP3_PROFILES.json"
        records = read_json(records_path)
        expected_tracks = [t for scan in ONS for t in tops[scan][:3]]
        check(len(records) == 9 and [r["selected_track"] for r in records] == expected_tracks,
              "Fixed top3 profile selection differs")
        patch_keys = {"raw_power", "row_normalized_power", "saved_full_chunk_row_medians",
                      "frozen_source_channel_centers", "source_channel_offsets", "times_seconds_from_reference",
                      "center_row_normalized_power", "fixed_flank_median_row_normalized_power",
                      "center_minus_flank_each_row", "mean_fixed_track_frequency_profile", "scans",
                      "df_hz", "source_channel0", "reference_frequency_hz", "drift_hz_s", "width_channels", "fixed_source_channel_shift"}
        offsets = np.arange(-64, 65)
        for record in records:
            track = record["selected_track"]
            path = check_ref(out, record["patch"]["path"], record["patch"]["sha256"], record["patch"]["bytes"])
            with np.load(io.BytesIO(read_output_bytes(path)), allow_pickle=False) as z:
                check(set(z.files) == patch_keys, "Profile patch schema differs")
                a = {k: z[k] for k in z.files}
            schema = {
                "raw_power": ("<f4", (6, 16, 129)), "row_normalized_power": ("<f8", (6, 16, 129)),
                "saved_full_chunk_row_medians": ("<f8", (6, 16)), "frozen_source_channel_centers": ("<i8", (6, 16)),
                "source_channel_offsets": ("<i8", (129,)), "times_seconds_from_reference": ("<f8", (6, 16)),
                "center_row_normalized_power": ("<f8", (6, 16)), "fixed_flank_median_row_normalized_power": ("<f8", (6, 16)),
                "center_minus_flank_each_row": ("<f8", (6, 16)), "mean_fixed_track_frequency_profile": ("<f8", (6, 129)),
                "scans": ("<U10", (6,)), "df_hz": ("<f8", ()), "source_channel0": ("<i8", ()),
                "reference_frequency_hz": ("<f8", ()), "drift_hz_s": ("<f8", ()), "width_channels": ("<i8", ()),
                "fixed_source_channel_shift": ("<i8", ())}
            for field, (dtype, shape) in schema.items():
                check(a[field].dtype == np.dtype(dtype) and a[field].shape == shape, "Saved patch dtype/shape differs: " + field)
            raw = a["raw_power"]
            check(raw.shape == (6, 16, 129) and raw.dtype == np.dtype("<f4")
                  and np.isfinite(raw).all() and (raw >= 0).all(), "Invalid saved raw patch")
            same(a["scans"], np.asarray(SCANS), "Patch scan identities differ")
            same(a["source_channel_offsets"], offsets, "Patch offsets differ")
            same(a["saved_full_chunk_row_medians"], rowmedians, "Patch row medians differ")
            for field, expected in (("df_hz", DF), ("source_channel0", C0),
                                    ("reference_frequency_hz", track["reference_frequency_hz"]),
                                    ("drift_hz_s", track["drift_hz_s"]), ("width_channels", track["width_channels"]),
                                    ("fixed_source_channel_shift", 0)):
                check(a[field].shape == () and a[field].item() == expected, "Patch scalar differs: " + field)
            dt = np.asarray([(headers[scan]["tstart"] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                             - track["reference_seconds_from_anchor"] for scan in SCANS])
            base = (track["reference_frequency_hz"] - FCH1) / DF
            centers = np.rint(base + track["drift_hz_s"] * dt / DF).astype(np.int64)
            same(a["times_seconds_from_reference"], dt, "Patch actual header times differ")
            same(a["frozen_source_channel_centers"], centers, "Patch absolute rounded centers differ")
            check(centers.min() - C0 - 64 >= 0 and centers.max() - C0 + 64 < COUNT,
                  "Patch geometry exceeds retained joined pair")
            normalized = raw.astype(np.float64) / rowmedians[:, :, None]
            baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
            radius = track["width_channels"] // 2
            center = normalized[:, :, 64 - radius:65 + radius].mean(axis=2)
            residual = center - baseline
            mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
            same(a["row_normalized_power"], normalized, "Saved patch normalization differs")
            same(a["fixed_flank_median_row_normalized_power"], baseline, "Saved fixed flank differs")
            same(a["center_row_normalized_power"], center, "Saved width box differs")
            same(a["center_minus_flank_each_row"], residual, "Saved residual differs")
            same(a["mean_fixed_track_frequency_profile"], mean_profile, "Saved mean frequency profile differs")
            check(record["fixed_flank_offsets"] == "absolute channel offset > 3 within +/-64", "Frozen profile flank declaration differs")
            check(record["fixed_frequency_shift_channels"] == 0
                  and record["classification"] == "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE",
                  "Unchanged descriptive profile contract differs")
            check(len(record["scan_profiles"]) == 6, "Six profile scan summaries required")
            for i, profile in enumerate(record["scan_profiles"]):
                expected = {"scan_id": SCANS[i], "mean_center_minus_flank": float(residual[i].mean()),
                            "median_center_minus_flank": float(np.median(residual[i])),
                            "positive_rows": int(np.count_nonzero(residual[i] > 0)),
                            "first_eight_mean_center_minus_flank": float(residual[i, :8].mean()),
                            "last_eight_mean_center_minus_flank": float(residual[i, 8:].mean()),
                            "all_16_center_minus_flank_rows": residual[i].tolist(),
                            "all_16_raw_width_mean_power": raw[i, :, 64 - radius:65 + radius].mean(axis=1).tolist(),
                            "frozen_source_channel_centers": centers[i].tolist()}
                check(profile == expected, "Saved scan JSON metrics differ from retained patch")
                counts["scan_profiles"] += 1; counts["time_rows"] += 16
            counts["patches"] += 1; counts["retained_raw_patch_cells"] += raw.size
            counts["binary_and_normalization_hashes"] += 1
        check(counts == {"maps": 6, "normalization_files": 6, "carrier_maximum_records": 24576,
                         "top20_entries": 60, "patches": 9, "scan_profiles": 54, "time_rows": 864,
                         "retained_raw_patch_cells": 111456, "binary_and_normalization_hashes": 21},
              "QA inventory incomplete")
        check(len(output_pins) == 21, "Exactly six maps, six tile-normalizations and nine patches required")
        check({p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()} == expected_measurement_names,
              "Completed measurement inventory changed during saved QA")
        for path, pin in json_pins.items():
            check(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"],
                  "Opened JSON changed during saved QA: " + str(path))
        for path, pin in output_pins.items():
            check(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"],
                  "Saved output bytes changed during QA: " + str(path))
        for name, pin in dependencies.items():
            path = confined(root / name)
            check(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"],
                  "Frozen metadata/code changed during QA: " + name)
        check(digest(own_path) == own_sha and digest(wrapper_path) == wrapper_sha, "QA/wrapper code changed during QA")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
                    "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(0 < measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and 0 < measured["wall_seconds"] <= WALL_CAP and 0 < measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Measured saved-output QA resource cap exceeded")
        main_json_pins = {(out / name).relative_to(root).as_posix(): json_pins[(out / name).resolve()]["sha256"]
                          for name in six_names}
        receipt = {"status": "PASS_COMPLETE_SAVED_JOINED_BOUNDARY_OUTPUTS", "pair_id": pair_id,
                   "source_chunk_ids": [left, right], "source_channel0": C0, "source_channel_count": COUNT,
                   "freeze_commit": args.freeze_commit, "public_scope_sha256": scope_sha,
                   "public_wrapper_sha256": wrapper_sha, "qa_script_sha256": own_sha,
                   "execution_receipt_sha256": execution_sha,
                   "acquisition_summary_sha256": acquisition_shas,
                   "INPUT_PINS_sha256": json_pins[input_pins_path.resolve()]["sha256"],
                   "checkpoint_sha256": json_pins[checkpoint_path.resolve()]["sha256"],
                   "top20_sha256": json_pins[tops_path.resolve()]["sha256"],
                   "profile_JSON_sha256": json_pins[records_path.resolve()]["sha256"],
                   "saved_normalization_sha256": json_pins[fullnorm_path.resolve()]["sha256"],
                   "input_json_sha256": main_json_pins, "counts": counts, "fixed_pair_q": qs,
                   "profile_identity_fields": ["pair_id", "track_id"],
                   "output_byte_pins": [{"path": path.relative_to(root).as_posix(), **pin}
                                        for path, pin in sorted(output_pins.items())],
                   "opened_json_pins": [{"path": path.relative_to(root).as_posix(), **pin}
                                        for path, pin in sorted(json_pins.items())],
                   "metadata_code_pins_checked": len(dependencies),
                   "cap_CPU_s_this_QA": CPU_CAP, "cap_stage_QA_allocation_CPU_s": 120,
                   "combined_three_saved_QA_process_caps_s": 60, "separate_joint_source_QA_process_cap_s": 60,
                   "cap_wall_s_this_QA": WALL_CAP, "cap_memory_bytes": MEMORY_CAP,
                   **measured, "source_HDF5_reads": 0, "detector_rescoring_runs": 0,
                   "new_profile_projection_runs": 0, "new_HTTP_requests": 0, "new_SOURCE_BODY_bytes": 0,
                   "new_source_normalization_runs": 0,
                   "original_scopes_and_terminal_statuses_modified": False,
                   "original_scopes_terminal_statuses_and_outputs_modified": False,
                   "old_A_B_failure_statuses_changed": False, "qualified_sky_pilot": False,
                   "QA_math": "Frozen tie/NMS integrity reconstruction from saved maxima; unchanged retained-patch algebra and scan JSON.",
                   "profile_normalization_definition": FULLNORM_METHOD,
                   "normalization_authenticity_limit": "Saved denominator schema/positivity and consistent use checked; source row medians not independently remeasured.",
                   "raw_source_authenticity_limit": "Separate joint source-cell QA authenticates raw patches when independently authorized and completed.",
                   "scope_limit": "One exposed visit; pair-selected descriptive profiles; original statuses preserved; no calibrated sky inference."}
        with receipt_path.open("x") as stream:
            stream.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"QA_receipt": str(receipt_path), "status": receipt["status"], "pair_id": pair_id,
                          **measured}, allow_nan=False), flush=True)
    except BaseException as exc:
        failure = {"status": "QA_INCOMPLETE_OR_FAILED_NO_RETRY", "pair_id": pair_id,
                   "error_type": type(exc).__name__, "error": str(exc), "partial_counts": counts,
                   "process_CPU_seconds_including_imports": time.process_time(),
                   "wall_seconds": time.monotonic() - started, "source_HDF5_reads": 0,
                   "detector_rescoring_runs": 0, "new_profile_projection_runs": 0}
        with failure_path.open("x") as stream:
            stream.write(json.dumps(failure, indent=2, allow_nan=False) + "\n")
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
