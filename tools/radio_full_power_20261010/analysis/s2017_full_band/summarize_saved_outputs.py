"""Summarize all three authenticated extension batches from saved JSON only.

Requires actual COMPLETE receipts, combined QA PASS and root GO. Does not
open HDF5/NPZ, fit tracks, select new tracks, or recompute detector scores.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
BATCHES = ("batch01", "batch02", "batch03")
SCOPE_SHAS = dict(zip(BATCHES, (
    "551083a9ba56bf960fa49e8868047f8016ba9a70a3a7b1df1a54333af8d56c9c",
    "d9b499662e8766058a74ac794225fd95a34d208a07f5a7e289ce306e8c957d68",
    "72c82c8fb36c26ce2f22d68d5e57a34e7c841ab7e0c83050f5b67e8f1459f759")))
DRIVER_SHA = "5ce9d5f861e06691183cf43fd4351bfe8a09b97763c3bd23add82ad338864554"
FREEZE = "76fb1da5a0af22d6182daed90e4bdca92f2470f8"
PRIOR_SEARCH_SHA = "3fe2b007a552b149a68f5d81bde3f9911c8d4ba0d3a31695356c76706cf7f27f"
PRIOR_QA_SHA = "e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f"
COMMON_CHANNEL = 179830784
FCH1, DF, TSAMP, C0, COUNT, CORE = 2802832031.25, -2.7939677238464355, 18.253611008, 179306496, 1048576, 4096
QA_COUNTS = {"batch_families": 3, "maps": 759, "map_normalization_records": 759,
    "carrier_maximum_records": 3108864, "valid_hypothesis_records": 4880916480,
    "top20_entries": 180, "patches": 27, "scan_profiles": 162, "time_row_occurrences": 2592,
    "retained_raw_patch_cells": 334368, "compact_files": 6, "decoded_rows": 96,
    "previously_source_qualified_full_row_medians_authenticated": 96,
    "ON_core_row_medians_recomputed": 12144, "raw_cells_bitwise_checked": 334368}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def coverage(cores, maps, profiles):
    carriers = cores * CORE
    return {"distinct_reference_cores_per_ON": cores, "completed_ON_maps": maps,
        "reference_carriers_per_ON": carriers, "ON_carrier_origin_entries": carriers * 3,
        "correlated_drift_width_combinations": carriers * 3 * 1570,
        "nominal_reference_carrier_bandwidth_per_ON_hz": carriers * abs(DF),
        "native_chunk_fraction_of_reference_carriers": carriers / COUNT,
        "native_chunk_percent_of_reference_carriers": carriers / COUNT * 100,
        "fixed_profiles": profiles, "scan_profiles": profiles * 6,
        "integration_row_occurrences": profiles * 6 * 16,
        "retained_raw_patch_cell_occurrences": profiles * 6 * 16 * 129}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--expected-qa-sha256", required=True)
    for batch in BATCHES:
        parser.add_argument("--expected-" + batch + "-receipt-sha256", required=True)
    parser.add_argument("--root-go-after-complete-and-qa", action="store_true", required=True)
    args = parser.parse_args()
    check(args.root_go_after_complete_and_qa, "Root GO after all COMPLETE receipts and combined QA required")
    root = Path(args.root).resolve()
    base = root / "analysis/s2017_full_band"
    out = base / "summary"
    check(not out.exists(), "Refuse summary namespace reuse or overwrite")
    pins = {}

    def read(path, expected_sha=None, declared=None):
        path = Path(path).resolve()
        check(path.is_relative_to(root) and path.suffix == ".json", "Only confined saved JSON may be read")
        raw = path.read_bytes()
        pin = {"sha256": sha(raw), "bytes": len(raw)}
        if expected_sha is not None:
            check(re.fullmatch("[0-9a-f]{64}", expected_sha) and pin["sha256"] == expected_sha,
                  "Exact reviewed JSON SHA differs: " + str(path))
        if declared is not None:
            check(pin == declared, "Combined QA saved-JSON pin differs: " + str(path))
        key = str(path)
        check(key not in pins or pins[key] == pin, "JSON changed between reads")
        pins[key] = pin
        return json.loads(raw)

    qa_path = base / "results/review/QA_RECEIPT.json"
    qa = read(qa_path, args.expected_qa_sha256)
    check(qa["schema"] == "SETI_S2017_THREE_INTERIOR_BATCHES_SAVED_OUTPUT_SOURCE_QA_V1"
          and qa["status"] == "PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS"
          and qa["driver_sha256"] == DRIVER_SHA and qa["public_freeze_commit"] == FREEZE
          and qa["counts"] == QA_COUNTS and qa["scope_SHA256s"] == SCOPE_SHAS
          and qa["detector_or_score_rerun"] is False and qa["fixed_track_optimization_applied"] is False
          and qa["new_telescope_HTTP_requests"] == qa["new_telescope_BODY_bytes"] == qa["cost_DKK"] == 0,
          "Actual matching complete combined saved-output/source QA PASS required")
    prior_search = read(root / "analysis/new_visit_recovery/results/search/EXECUTION_RECEIPT.json", PRIOR_SEARCH_SHA)
    prior_qa = read(root / "analysis/new_visit_recovery/results/review/QA_RECEIPT.json", PRIOR_QA_SHA)
    check(prior_qa["search_receipt_sha256"] == PRIOR_SEARCH_SHA and prior_qa["counts"]["maps"] == 3
          and prior_qa["counts"]["patches"] == 9 and prior_qa["counts"]["raw_cells_bitwise_checked"] == 111456
          and prior_search["search_summary"]["completed_ON_maps"] == 3,
          "Previously completed q128 source QA/search required")
    batches, cases, rows, allqs = [], [], [], []
    half_context = {kind: {"positive_in_both_halves": 0, "total": 0} for kind in ("origin_ON", "other_ON", "OFF")}
    for batch in BATCHES:
        scope = read(base / "scopes" / (batch + ".json"), SCOPE_SHAS[batch])
        expected_receipt = getattr(args, "expected_" + batch + "_receipt_sha256")
        directory = base / "results" / batch
        receipt = read(directory / "EXECUTION_RECEIPT.json", expected_receipt)
        check(qa["search_receipt_SHA256s"][batch] == expected_receipt
              and receipt["status"] == "COMPLETE_S2017_PREVIOUSLY_UNSEARCHED_INTERIOR_BATCH_EXPLORATORY_ONLY"
              and receipt["scope_sha256"] == SCOPE_SHAS[batch] and receipt["driver_sha256"] == DRIVER_SHA
              and receipt["public_freeze_commit"] == FREEZE and receipt["batch_id"] == batch
              and receipt["q128_search_receipt_sha256"] == PRIOR_SEARCH_SHA
              and receipt["q128_QA_receipt_sha256"] == PRIOR_QA_SHA,
              "Actual root-reviewed COMPLETE batch required")
        qs = scope["core_q_indices"]
        allqs.extend(qs)
        search = receipt["search_summary"]
        check(search["completed_ON_maps"] == len(qs) * 3 and search["carriers_per_ON"] == len(qs) * CORE
              and search["drift_grid_count"] == 785 and search["widths_channels"] == [1, 3]
              and receipt["fixed_profile_summary"]["profile_count"] == 9
              and receipt["new_telescope_HTTP_requests"] == receipt["new_telescope_BODY_bytes"] == receipt["cost_DKK"] == 0,
              "Actual fixed batch coverage/accounting differs")
        def saved(name):
            path = (directory / name).resolve()
            key = path.relative_to(root).as_posix()
            check(key in qa["all_input_byte_pins"], "Combined QA lacks saved JSON byte pin")
            return read(path, declared=qa["all_input_byte_pins"][key])
        tops = saved("DRIFT_TOP20.json")
        profiles = saved("FIXED_TOP3_PROFILES.json")
        check(pins[str(directory / "DRIFT_TOP20.json")]["sha256"] == receipt["fixed_profile_summary"]["source_top20_sha256"],
              "Saved top20 selection source hash differs")
        check(set(tops) == set(ONS) and all(len(tops[on]) == 20 for on in ONS) and len(profiles) == 9,
              "Complete saved top20/top3 inventory required")
        check([p["selected_track"] for p in profiles] == [t for on in ONS for t in tops[on][:3]],
              "Only the original fixed top3 identities may be summarized")
        ranking = {}
        for on in ONS:
            channels = [t["source_reference_channel"] for t in tops[on]]
            scores = [t["maximum_robust_box_track_score"] for t in tops[on]]
            ranking[on] = {"top20_count": 20, "saved_score_min": min(scores), "saved_score_max": max(scores),
                "reference_channel_limits_inclusive": [min(channels), max(channels)],
                "reference_frequency_limits_hz": sorted([FCH1 + DF * min(channels), FCH1 + DF * max(channels)]),
                "selected_core_q_values": sorted({t["reference_core_tile"] for t in tops[on]})}
        for record in profiles:
            track = record["selected_track"]
            measures = record["scan_profiles"]
            check([m["scan_id"] for m in measures] == list(SCANS), "Saved six-scan order differs")
            case = {"batch_id": batch, "selected_track": track, "saved_patch_byte_pin": record["patch"], "scan_profiles": []}
            for measure in measures:
                scan = measure["scan_id"]
                centers = measure["frozen_source_channel_centers"]
                residuals = measure["all_16_center_minus_flank_rows"]
                check(len(centers) == len(residuals) == 16 and all(math.isfinite(v) for v in residuals),
                      "Saved all-row profile geometry differs")
                intersects = [i for i, center in enumerate(centers) if abs(center - COMMON_CHANNEL) <= track["width_channels"] // 2]
                kind = "origin_ON" if scan == track["originating_scan"] else "other_ON" if scan in ONS else "OFF"
                first, last = measure["first_eight_mean_center_minus_flank"], measure["last_eight_mean_center_minus_flank"]
                half_context[kind]["total"] += 1
                half_context[kind]["positive_in_both_halves"] += int(first > 0 and last > 0)
                case["scan_profiles"].append({**measure,
                    "rows_whose_frozen_width_box_contains_q128_common_stationary_channel": intersects,
                    "geometry_is_saved_coordinates_only_no_track_fit": True})
                rows.append({"visit": "visit20170428_Sband", "native_chunk": 171, "batch_id": batch,
                    "track_id": track["track_id"], "originating_scan": track["originating_scan"],
                    "display_rank": track["display_rank"], "reference_core_q": track["reference_core_tile"],
                    "reference_frequency_hz": track["reference_frequency_hz"], "source_reference_channel": track["source_reference_channel"],
                    "drift_hz_s": track["drift_hz_s"], "width_channels": track["width_channels"],
                    "saved_robust_rank_score": track["maximum_robust_box_track_score"], "scan_id": scan,
                    "scan_context": kind, "saved_mean_center_minus_flank": measure["mean_center_minus_flank"],
                    "saved_first_eight_mean": first, "saved_last_eight_mean": last,
                    "saved_positive_rows": measure["positive_rows"],
                    "q128_common_line_box_intersection_rows": json.dumps(intersects)})
            cases.append(case)
        batches.append({"batch_id": batch, "scope_sha256": SCOPE_SHAS[batch], "execution_receipt_sha256": expected_receipt,
            "core_q_indices": qs, "search_summary": search, "coverage": coverage(len(qs), len(qs) * 3, 9),
            "ranking_context": ranking, "resources": {k: receipt[k] for k in (
                "process_CPU_seconds_including_imports", "wall_seconds_including_imports", "peak_RSS_bytes",
                "CPU_cap_s", "wall_cap_s", "memory_cap_bytes_per_process", "memory_cap_bytes_aggregate", "simultaneous_job_slot")},
            "new_HTTP_requests": 0, "new_BODY_bytes": 0, "cost_DKK": 0})
    check(allqs == [q for q in range(1, 255) if q != 128] and len(set(allqs)) == 253
          and len(cases) == 27 and len(rows) == 162, "Exact three-batch saved summary inventory required")
    summary = {"schema": "SETI_S2017_FULL_INTERIOR_SAVED_JSON_SUMMARY_V1",
        "status": "COMPLETE_SAVED_SUMMARY_WITH_ACTUAL_COMBINED_PASS_QA", "target": "HIP98505 / HD189733",
        "visit": "2017-04-28 / AGBT17A_999_55", "visit_label": "visit20170428_Sband",
        "public_freeze_commit": FREEZE, "combined_QA_receipt_sha256": args.expected_qa_sha256,
        "combined_QA_status": qa["status"], "combined_QA_counts": qa["counts"],
        "previous_q128_search_receipt_sha256": PRIOR_SEARCH_SHA, "previous_q128_QA_receipt_sha256": PRIOR_QA_SHA,
        "scan_order": list(SCANS), "native_chunk": 171, "native_chunk_channels": COUNT,
        "native_chunk_nominal_bandwidth_hz": COUNT * abs(DF), "frame": {"fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP},
        "extension_coverage": coverage(253, 759, 27), "prior_q128_coverage": coverage(1, 3, 9),
        "combined_reference_carrier_coverage": coverage(254, 762, 36),
        "combined_native_reference_channel_interval_half_open": [C0 + CORE, C0 + 255 * CORE],
        "unsearched_native_reference_edge_q": [0, 255], "batches": batches, "fixed_profiles": cases,
        "saved_half_sign_context": half_context,
        "q128_common_stationary_channel": COMMON_CHANNEL, "q128_common_stationary_frequency_hz": FCH1 + DF * COMMON_CHANNEL,
        "coverage_counts_reference_carriers_not_drift_halos_or_sensitivity": True,
        "ranking_score_is_calibrated_SNR": False, "false_alarm_probability_known": False,
        "qualified_OFF_veto": False, "qualified_sky_detection": False, "general_null_result": False,
        "independent_visits": 1, "administrative_batches_are_independent_visits": False,
        "same_frequency_replication_of_old_Lband_cases": False,
        "new_track_selection_fits_detector_or_measurement_runs": 0,
        "new_HDF5_NPZ_or_HTTP_reads": 0}
    for name, pin in pins.items():
        path = Path(name)
        check(path.stat().st_size == pin["bytes"] and sha(path.read_bytes()) == pin["sha256"], "Saved JSON changed during summary")
    out.mkdir()
    summary_path, csv_path = out / "FULL_BAND_SUMMARY.json", out / "FULL_BAND_PROFILE_MEANS.csv"
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    with csv_path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    receipt = {"schema": "SETI_S2017_FULL_INTERIOR_SAVED_JSON_SUMMARY_RECEIPT_V1",
        "status": "COMPLETE_SAVED_JSON_ONLY_SUMMARY", "code_sha256": sha(Path(__file__).read_bytes()),
        "input_byte_pins": pins, "output_byte_pins": {str(p): {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
            for p in (summary_path, csv_path)}, "fixed_identities": 27, "six_scan_records": 162,
        "new_fits_detector_track_selection_or_measurement_runs": 0, "HDF5_NPZ_HTTP_reads": 0}
    (out / "FULL_BAND_SUMMARY_RECEIPT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": summary["status"], "fixed_profiles": 27, "scan_profiles": 162, "output": str(out)}))


if __name__ == "__main__":
    main()
