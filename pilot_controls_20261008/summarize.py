"""Summarize already-observed case outcomes; never generate or score controls."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(cases, outcomes, panel):
    selected = [c for c in cases if c["panel"] == panel]
    ids = [c["case_id"] for c in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate frozen case identities")
    observed = {}
    for item in outcomes:
        if item["case_id"] in observed:
            raise ValueError("Duplicate observed case outcome")
        if item["case_id"] not in set(ids):
            raise ValueError("Outcome outside this frozen panel")
        observed[item["case_id"]] = item
    missing = sorted(set(ids) - observed.keys())
    failed = [identity for identity, item in observed.items()
              if not item.get("data_integrity_ok", False) or item.get("failure")]
    summary = {"panel": panel, "complete": not missing and not failed,
               "missing_case_ids": missing, "failed_case_ids": failed,
               "case_count_expected": len(ids), "case_count_observed": len(observed),
               "families": {}, "resource_observed": {
                   "wall_seconds_sum": sum(float(x.get("wall_s", 0)) for x in observed.values()),
                   "cpu_seconds_sum": sum(float(x.get("cpu_s", 0)) for x in observed.values())}}
    for family in sorted({c["family"] for c in selected}):
        members = [c for c in selected if c["family"] == family]
        results = [observed[c["case_id"]] for c in members if c["case_id"] in observed]
        summary["families"][family] = {
            "expected": len(members), "observed": len(results),
            "any_localized_on_recovered": sum(bool(x.get("any_localized_on_recovered")) for x in results),
            "all_active_on_recovered": sum(bool(x.get("all_active_on_recovered")) for x in results),
            "all_primary_on_detected_before_off": sum(bool(x.get("rfi_pre_off_all_active_detected", x.get("pre_OFF_all_active_recovery", False))) for x in results),
            "cadences_with_any_survivor": sum(int(x.get("survivor_count", 0)) > 0 for x in results)}
    # DEV is a development view, never an independent scientific gate.
    if panel == "DEV":
        summary["scientific_gate"] = "NOT_EVALUATED_DEVELOPMENT_ONLY"
        return summary
    recovered = lambda c: bool(observed.get(c["case_id"], {}).get("all_active_on_recovered", False))
    operating = [c for c in selected if c["family"] == "operating"]
    subgroup = {"activity": {}, "drift": {}, "intrinsic_width": {}}
    for dimension, key in (("activity", "active_scan_indices"), ("drift", "drift_hz_s"),
                           ("intrinsic_width", "intrinsic_width_channels")):
        groups = {}
        for c in operating:
            group = json.dumps(c[key], separators=(",", ":"))
            groups.setdefault(group, []).append(c)
        subgroup[dimension] = {name: {"expected": len(group), "recovered": sum(recovered(c) for c in group)}
                               for name, group in groups.items()}
    family_results = summary["families"]
    checks = {"complete_and_integrity": summary["complete"],
              "strong_14_of_14": family_results["strong"]["all_active_on_recovered"] == 14,
              "operating_at_least_44_of_48": family_results["operating"]["all_active_on_recovered"] >= 44,
              "each_activity_at_least_7_of_8": all(x["recovered"] >= 7 for x in subgroup["activity"].values()),
              "each_drift_at_least_10_of_12": all(x["recovered"] >= 10 for x in subgroup["drift"].values()),
              "each_width_at_least_22_of_24": all(x["recovered"] >= 22 for x in subgroup["intrinsic_width"].values()),
              "matched_rfi_no_surviving_cadence": family_results["matched_rfi"]["cadences_with_any_survivor"] == 0,
              "matched_rfi_all_primary_on_detected_before_off": family_results["matched_rfi"]["all_primary_on_detected_before_off"] == 24,
              "noise_at_most_one_surviving_cadence": family_results["noise"]["cadences_with_any_survivor"] <= 1}
    summary.update(subgroups=subgroup, checks=checks,
                   scientific_gate="PASS_EXPLORATORY_SCOPE_ONLY" if all(checks.values()) else "FAIL_CLOSED")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--panel", choices=("DEV", "VAL_A", "VAL_B"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = summarize(json.loads(Path(args.cases).read_text()),
                       json.loads(Path(args.outcomes).read_text()), args.panel)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
