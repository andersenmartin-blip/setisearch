"""Compare a reviewed report/summary/CSV to saved JSON; no signal remeasurement."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import resource
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = "results/radio_rolling_bands_20261010"
REPORT = "RADIO_ROLLING_BANDS_REPORT_2026-10-10.md"
REPORT_SHA = "c913fd4a9ca3b19e52b87dcdf7a4e422092ccb3f187b05a569b0f4770963df20"
SUMMARY = BASE+"/summary/SAVED_SUMMARY.json"
CSV = BASE+"/summary/PROFILE_SUMMARY.csv"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]


def digest(name):
    return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT/name).read_text())


def fmt(value):
    return f"{value:.6f}".replace(".", ",")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-authorized-read-only-report-review", action="store_true", required=True)
    parser.parse_args()
    assert digest(REPORT) == REPORT_SHA
    report = (ROOT/REPORT).read_text()
    summary = load(SUMMARY)
    assert summary["all_original_numeric_executions_COMPLETE"] is True
    assert summary["original_execution_statuses_rewritten"] is False
    assert summary["fully_audited_summary_complete"] is True
    assert summary["completed_scan_tiles"] == 1524 and summary["profile_count"] == 36
    assert summary["ON_carrier_origin_entries"] == 6242304
    assert summary["evaluated_hypothesis_combinations"] == 9525755904
    for field in ("qualified_sky_pilot", "origin_classification", "independent_trials_claim",
                  "calibrated_SNR_FAP_flux_EIRP_or_sensitivity", "general_null_result_claim",
                  "original_full_source_file_MD5_verified", "old_holdouts_reopened"):
        assert summary[field] is False
    assert summary["one_historical_visit"] is True and summary["visit_date"] == "2016-03-17"
    records, input_shas = {}, {REPORT: REPORT_SHA, SUMMARY: digest(SUMMARY), CSV: digest(CSV)}
    top_count = 0
    for chunk in (155, 157):
        for batch in (1, 2):
            directory = f"{BASE}/chunk{chunk}/batch_{batch:02d}/measurement"
            profile_name, top_name = directory+"/FIXED_TOP3_PROFILES.json", directory+"/DRIFT_TOP20.json"
            profiles, tops = load(profile_name), load(top_name)
            input_shas.update({profile_name: digest(profile_name), top_name: digest(top_name)})
            assert set(tops) == set(ONS) and all(len(tops[s]) == 20 for s in ONS)
            top_count += sum(len(v) for v in tops.values())
            assert [x["selected_track"] for x in profiles] == [t for s in ONS for t in tops[s][:3]]
            for record in profiles:
                t = record["selected_track"]
                key = (chunk, batch, t["originating_scan"], t["display_rank"])
                assert key not in records
                records[key] = record
    assert len(records) == 36 and top_count == 240
    for chunk in (155,157):
        for batch in (1,2):
            tops=load(f"{BASE}/chunk{chunk}/batch_{batch:02d}/measurement/DRIFT_TOP20.json")
            for origin in ONS:
                assert [t["display_rank"] for t in tops[origin]] == list(range(1,21))
                assert [t["track_id"] for t in tops[origin]] == [origin+"_gap_drift_rank_%02d"%k for k in range(1,21)]
                assert all(t["source_chunk_id"]==chunk and t["batch_id"]==batch and t["originating_scan"]==origin for t in tops[origin])
        high=[records[(chunk,1,on,1)]["scan_profiles"][0]["mean_center_minus_flank"] for on in ONS]
        assert max(records[(chunk,2,on,k)]["scan_profiles"][i]["mean_center_minus_flank"] for i,on in zip((0,2,4),ONS) for k in (1,2,3)) < min(high)
    for item in summary["profiles"]:
        key = (item["source_chunk_id"], item["batch_id"], item["originating_scan"], item["display_rank_within_batch_and_ON"])
        record = records[key]
        t = record["selected_track"]
        for field in ("source_reference_channel", "reference_frequency_hz", "reference_seconds_from_anchor", "drift_hz_s", "width_channels"):
            assert item[field] == t[field]
        assert item["saved_robust_score"] == t["maximum_robust_box_track_score"]
        expected_measures = {s["scan_id"]: {k: v for k, v in s.items() if k != "scan_id"} for s in record["scan_profiles"]}
        assert item["all_six_fixed_scan_measures"] == expected_measures
        assert item["origin_ON"] == expected_measures[t["originating_scan"]]
        assert item["batch_execution_complete"] is True
    with (ROOT/CSV).open() as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 36
    for row in csv_rows:
        key = (int(row["source_chunk_id"]), int(row["batch_id"]), row["originating_scan"], int(row["display_rank"]))
        record = records[key]
        byscan = {s["scan_id"]: s for s in record["scan_profiles"]}
        for scan in SCANS:
            assert float(row[scan+"_mean_center_minus_flank"]) == byscan[scan]["mean_center_minus_flank"]
    table_keys = set()
    stationary_table = []
    for line in report.splitlines():
        if not line.startswith("|"):
            continue
        cells = [x.strip() for x in line.strip("|").split("|")]
        if len(cells) == 9 and re.fullmatch(r"ON[123]/[123]", cells[2]):
            chunk, batch = int(cells[0]), int(cells[1])
            on_index, rank = map(int, re.findall(r"\d", cells[2]))
            key = (chunk, batch, f"epoch{on_index}_on", rank)
            assert key not in table_keys
            table_keys.add(key)
            record = records[key]
            t = record["selected_track"]
            byscan = {s["scan_id"]: s for s in record["scan_profiles"]}
            before = "—" if on_index == 1 else fmt(byscan[f"epoch{on_index-1}_off"]["mean_center_minus_flank"])
            after = fmt(byscan[f"epoch{on_index}_off"]["mean_center_minus_flank"])
            assert cells[3:] == [fmt(t["reference_frequency_hz"]/1e6), fmt(t["drift_hz_s"]),
                str(t["width_channels"]), fmt(byscan[t["originating_scan"]]["mean_center_minus_flank"]), before, after]
        if len(cells) == 7 and re.fullmatch(r"(?:155|157) / \d+,\d+", cells[0]):
            stationary_table.append(cells)
    assert table_keys == set(records) and len(stationary_table) == 2
    for cells, family in zip(stationary_table, ((155, 1), (157, 1))):
        group = [records[(family[0], family[1], s, 1)] for s in ONS]
        tracks = [g["selected_track"] for g in group]
        assert len({t["source_reference_channel"] for t in tracks}) == 1
        assert all(t["drift_hz_s"] == 0 and t["width_channels"] == 1 for t in tracks)
        byscan = {s["scan_id"]: s for s in group[0]["scan_profiles"]}
        assert all(g["scan_profiles"] == group[0]["scan_profiles"] for g in group)
        assert int(cells[0].split(" / ")[0]) == family[0]
        assert float(cells[0].split(" / ")[1].replace(",", ".")) == tracks[0]["reference_frequency_hz"]/1e6
        assert cells[1:] == [fmt(byscan[s]["mean_center_minus_flank"]) for s in SCANS]
        nearby = [records[(family[0],family[1],s,k)]["selected_track"] for s in ONS for k in (2,3)]
        assert all(abs(t["source_reference_channel"]-tracks[0]["source_reference_channel"]) <= 4 and t["drift_hz_s"] != 0 for t in nearby)
        assert all(byscan[s]["mean_center_minus_flank"] > 0 for s in SCANS)
    for name, sha in input_shas.items():
        assert digest(name) == sha
    receipt = {"status": "PASS_SCIENTIFIC_CLAIMS_SAVED_JSON_AND_REPORT_ONLY",
        "report_path": REPORT, "exact_reviewed_report_sha256": REPORT_SHA,
        "input_sha256": input_shas, "saved_top20_records": top_count,
        "profile_records_checked": 36, "all_six_saved_scan_metric_copies_checked": 216,
        "saved_time_row_occurrences_retained_in_verified_copies": 3456,
        "CSV_rows_checked": 36, "CSV_saved_scan_means_checked": 216,
        "report_profile_rows_checked": 36, "report_static_reference_rows_checked": 2,
        "report_static_reference_means_checked": 12,
        "original_numeric_COMPLETE_count": 4, "original_numeric_CPU_failure_count": 0,
        "manual_narrative_review": {"postselection_and_one_visit_explicit": True,
            "two_strong_stationary_regions_present_in_all_ON_OFF": True,
            "moving_exact_OFF_does_not_rule_out_nearby_stationary_structure": True,
            "36_selected_paths_not_independent_discoveries": True,
            "batch2_paths_remain_postselection_unresolved": True,
            "rank_score_distinct_from_saved_mean_residual": True,
            "saved_rank_integrity_reconstruction_distinct_from_new_selection": True,
            "no_origin_or_calibrated_significance_claim": True,
            "whole_original_source_MD5_not_claimed": True},
        "scientific_array_or_source_HTTP_access": False,
        "detector_or_profile_reexecution": False, "new_scientific_measurements": False,
        "figure_visual_QA_performed_here": False, "archive_or_durable_save_claims_reviewed_here": False,
        "process_CPU_seconds_including_imports": time.process_time(),
        "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    assert receipt["process_CPU_seconds_including_imports"] < 10
    path = ROOT/BASE/"review/SCIENTIFIC_CLAIMS_REVIEW.json"
    with path.open("x") as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"receipt_path": str(path.relative_to(ROOT)), "receipt_sha256": digest(path.relative_to(ROOT).as_posix()),
                      "report_sha256": REPORT_SHA, "process_CPU_s": time.process_time()}))


if __name__ == "__main__":
    main()
