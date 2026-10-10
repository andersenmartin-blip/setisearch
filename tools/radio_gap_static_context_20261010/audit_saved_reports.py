"""Audit saved report/CSV/proposal only; never load scientific binary arrays."""
import time
import csv
import hashlib
import json
import math
import resource
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results/radio_gap_static_context_20261010"
START_WALL = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
READ_PATHS = []


def load(relative):
    path = BASE / relative
    READ_PATHS.append(path)
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


profiles = load("measurement/STATIC_CONTEXT_PROFILES.json")
findings = load("measurement/DESCRIPTIVE_FINDINGS.json")
execution = load("measurement/EXECUTION_RECEIPT.json")
plotting = load("figures/PLOTTING_RECEIPT.json")
proposal = load("PROPOSAL.json")
ledger = load("RESOURCE_LEDGER.json")
report_path = ROOT / "RADIO_GAP_STATIC_CONTEXT_REPORT_2026-10-10.md"
report = report_path.read_text()
proposal_path = BASE / "RADIO_NEXT_COMPUTE_PROPOSAL_2026-10-10.md"
proposal_text = proposal_path.read_text()
report_rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
               for line in report.splitlines() if line.startswith("|")]
table_fields = 0
csv_fields = 0


def rounded(value):
    return f"{value:.6f}".replace(".", ",")


def check_table(label, values):
    global table_fields
    row = [label] + values
    assert sum(candidate == row for candidate in report_rows) == 1, row
    table_fields += len(values)


metrics = {
    "static": "static_center_minus_static_flank",
    "moving_same_static_background": "copied_moving_center_minus_same_static_flank",
    "static_minus_moving": "signed_static_minus_copied_moving_center",
    "moving_original_background": "saved_moving_center_minus_original_moving_flank",
}
lookup = {}
assert profiles["complete"] and profiles["completed_cases"] == profiles["expected_cases"] == 9
for case in profiles["records"]:
    track = case["selected_track"]
    label = "ON" + track["originating_scan"][5] + " r" + str(track["display_rank"]) + " (w" + str(track["width_channels"]) + ")"
    scans = {scan["scan_id"]: scan for scan in case["scan_profiles"]}
    assert len(scans) == 6
    check_table(label, [str(track["source_reference_channel"])] + [rounded(scan[metrics["static"]]["mean"]) for scan in case["scan_profiles"]])
    check_table(label, [rounded(scan[metrics["static_minus_moving"]]["mean"]) for scan in case["scan_profiles"]])
    origin = scans[track["originating_scan"]]
    n = int(track["originating_scan"][5])
    preceding = "Ikke observeret" if n == 1 else rounded(scans[f"epoch{n-1}_off"][metrics["static"]]["mean"])
    check_table(label, [rounded(origin[metrics[k]]["mean"]) for k in ["static", "moving_same_static_background", "static_minus_moving"]] + [rounded(origin[metrics["static"]]["minimum_half_mean"]), preceding, rounded(scans[f"epoch{n}_off"][metrics["static"]]["mean"])])
    for scan in case["scan_profiles"]:
        lookup[track["track_id"], scan["scan_id"]] = (case, scan)

group_labels = {"Alle": "all_54", "ON, alle cases": "all_ON_27", "OFF, alle cases": "all_OFF_27", "Origin-ON": "originating_ON_9", "Tilstødende OFF": "adjacent_OFF_15"}
for label, key in group_labels.items():
    group = findings["groups"][key]
    check_table(label, [str(group[k]) for k in ["case_scan_occurrences", "static_mean_positive", "static_both_halves_positive"]] + [" / ".join(str(group[k]) for k in ["signed_mean_positive", "signed_mean_zero", "signed_mean_negative"]), rounded(group["signed_mean_median"]), rounded(group["signed_mean_minimum"]) + " / " + rounded(group["signed_mean_maximum"])])

summary_path = BASE / "measurement/STATIC_CONTEXT_54_SCAN_SUMMARIES.csv"
with summary_path.open(newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == len(lookup) == 54
assert len({(row["track_id"], row["scan_id"]) for row in rows}) == 54
for row in rows:
    case, scan = lookup[row["track_id"], row["scan_id"]]
    for prefix, key in metrics.items():
        for metric in ["mean", "median", "positive_rows", "first_eight_mean", "last_eight_mean", "minimum_half_mean"]:
            assert float(row[prefix + "_" + metric]) == scan[key][metric]
            csv_fields += 1
    assert row["original_originating_scan"] == case["selected_track"]["originating_scan"]
    assert int(row["fixed_reference_channel"]) == case["fixed_physical_reference_channel"]
    assert int(row["original_width_channels"]) == case["static_width_channels"]

time_path = BASE / "measurement/STATIC_CONTEXT_864_TIME_ROWS.csv"
with time_path.open(newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == 864 and len({(r["track_id"], r["scan_id"], r["time_row"]) for r in rows}) == 864
time_keys = {"static_center_normalized_power": "all_16_static_center_row_normalized_power", "copied_moving_center_normalized_power": "all_16_copied_moving_center_row_normalized_power", "static_flank_normalized_power": "all_16_static_flank_row_normalized_power", "original_moving_flank_normalized_power": "all_16_original_moving_flank_row_normalized_power", "fixed_reference_channel": "fixed_physical_source_channel_centers", "saved_moving_center_channel": "saved_moving_source_channel_centers"}
for row in rows:
    case, scan = lookup[row["track_id"], row["scan_id"]]
    index = int(row["time_row"])
    for column, key in time_keys.items():
        assert float(row[column]) == scan[key][index]
        csv_fields += 1
    for prefix, key in metrics.items():
        assert float(row[prefix + "_residual"]) == scan[key]["all_16_rows"][index]
        csv_fields += 1
    assert int(row["original_width_channels"]) == case["static_width_channels"]

selection = proposal["metadata_selection"]
expected_q = sorted(set(range(1, 255)) - set(1 + 8*j for j in range(32)) - set(5 + 8*k for k in [0, 4, 8, 12, 16, 20, 24, 28]))
assert selection["remaining_q_ascending"] == expected_q and len(expected_q) == 214
assert selection["batch_q"] == [expected_q[:107], expected_q[107:]]
for batch, relative, absolute in zip(selection["batch_q"], selection["batch_channel_intervals_relative_half_open"], selection["batch_channel_intervals_absolute_half_open"]):
    assert len(batch) == len(relative) == len(absolute) == 107
    for q, r, a in zip(batch, relative, absolute):
        assert r == [q*4096, (q+1)*4096] and a == [158334976+r[0], 158334976+r[1]]
        assert r[0]-4000 >= 0 and r[1]+4000 <= 1048576
assert hashlib.sha256((json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest() == proposal["metadata_selection_canonical_SHA256"]
geometry = proposal["geometry"]["all_six_scan_fixed_profile_geometry"]
times = geometry["actual_scan_first_and_last_midpoint_seconds_from_anchor"]
references = geometry["actual_ON_reference_midpoints_seconds_from_anchor"]
dt = max(abs(value-reference) for bounds in times.values() for value in bounds for reference in references.values())
assert dt == geometry["maximum_absolute_time_delta_s"]
displacement = 4*dt/2.835503418452676
assert abs(displacement-geometry["maximum_unrounded_projected_shift_channels"]) < 1e-9
assert math.ceil(displacement) == 2707 and math.ceil(displacement)+64 == 2771 < 4000
assert 4096-2771 == geometry["conservative_projected_patch_minimum_relative_channel"] == 1325
assert 1044479+2771 == geometry["conservative_projected_patch_maximum_relative_channel_inclusive"] == 1047250 < 1048576
coverage = proposal["coverage_if_both_jobs_complete"]
assert coverage["new_reference_channels_per_ON"] == 214*4096 == 876544
assert coverage["all_safe_unique_reference_channels_per_ON"] == 254*4096 == 1040384
assert coverage["total_safe_fraction"] == 254/256 == 0.9921875
assert coverage["expected_completed_scan_core_tiles"] == 642
assert proposal["status"] == "UNAPPROVED_NOT_RUN" and proposal["additional_CPU_requested_s"] == 3600
assert proposal["currently_authorized_total_CPU_s"] == 43200 and proposal["prospective_authorized_total_CPU_s_only_after_approval"] == 46800
assert sum(proposal["planned_allocation_CPU_s"].values()) == 3600
assert not proposal["new_CPU_reservation_made_by_this_proposal"] and not proposal["new_numerical_execution_made_by_this_proposal"]
assert "IKKE GODKENDT" in proposal_text and "IKKE KØRT" in proposal_text and "99,21875" in proposal_text
assert plotting["cpu_cap_seconds"] == 6 and plotting["measured_plotting_CPU_seconds"] == 7.613888828
assert not plotting["plotting_CPU_cap_honored"] and plotting["no_plotting_rerun_or_scientific_rerun"]
assert "overskred sin 6 CPU-s" in report and "7,613889" in report and "der blev ikke tegnet igen" in report
assert execution["process_CPU_seconds_including_imports"] < 20 and execution["one_historical_visit"] and not execution["old_holdouts_reopened"]
assert ledger["remaining_CPU_after_reservation_s"] == 2.705144981004196 and ledger["activity_reservation_CPU_s"] == 60
assert "FAIL_CLOSED" in report and "ikke blind eller uafhængig validering" in report

receipt = {
    "schema": "SETI_GAP_STATIC_CONTEXT_SAVED_TEXT_CSV_PROPOSAL_AUDIT_V1",
    "status": "PASS_SAVED_TEXT_CSV_PROPOSAL_ONLY",
    "audit_mode": "Saved JSON/CSV/report/proposal only; no HDF5, NPZ, detector rescore, science remeasurement or numerical rerun.",
    "script_sha256": sha(Path(__file__)),
    "report_sha256_at_scientific_text_audit": sha(report_path),
    "report_scientific_prefix_excluding_final_delivery_paragraph_sha256": hashlib.sha256(report.rsplit("\n\n", 1)[0].encode()).hexdigest(),
    "delivery_metadata_may_change_after_audit": True,
    "proposal_JSON_sha256": sha(BASE / "PROPOSAL.json"),
    "proposal_MD_sha256": sha(proposal_path),
    "evidence_hashes": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in READ_PATHS + [summary_path, time_path]],
    "report_table_fields_checked": table_fields,
    "CSV_numeric_fields_roundtrip_equal_to_saved_JSON": csv_fields,
    "summary_rows": 54,
    "time_rows": 864,
    "proposal_geometry": {"remaining_safe_cores": 214, "batch_sizes": [107, 107], "total_safe_fraction": 254/256, "all_six_scan_maximum_dt_s": dt, "conservative_shift_plus_patch_channels": 2771, "conservative_projected_patch_range_inclusive": [1325, 1047250]},
    "proposal_state": "UNAPPROVED_NOT_RUN; requests 3600 additional CPU seconds, prospective total 46800 only after explicit approval; creates no reservation or numerical execution.",
    "plotting_cap_exceeded_explicitly_reported": True,
    "plotting_CPU_s": 7.613888828,
    "plotting_CPU_cap_s": 6,
    "plotting_or_science_rerun": False,
    "material_issues": [],
    "CPU_budget_s": 1,
    "process_CPU_s_including_imports": time.process_time(),
    "prior_read_only_inspection_body_CPU_s": 0.020954368,
    "wall_s": time.monotonic()-START_WALL,
    "whole_agent_CPU_measured": False,
}
assert receipt["process_CPU_s_including_imports"] + receipt["prior_read_only_inspection_body_CPU_s"] < 1
out = BASE / "CLAIMS_AUDIT_RECEIPT.json"
out.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "receipt": str(out), "receipt_sha256": sha(out), "script_sha256": receipt["script_sha256"], "CPU_s": receipt["process_CPU_s_including_imports"], "report_table_fields": table_fields, "CSV_numeric_fields": csv_fields}))
