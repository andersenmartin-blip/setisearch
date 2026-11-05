#!/usr/bin/env python3
"""Recount published tables and select a separate metadata-only continuation.

No FITS, image, spectral array, API, or detector is opened by this program.
Reproduction writes to a fresh output directory; historical products are immutable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
B = "work_harps_20261101/"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads((ROOT / path).read_text())


def rows(path):
    with (ROOT / path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_csv(path, data):
    assert data, str(path)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def truth(value):
    assert value in ("True", "False"), value
    return value == "True"


def run(out):
    scope = read_json(str((HERE / "SCOPE.json").relative_to(ROOT)))
    for name, expected in scope["source_hashes"].items():
        assert digest(ROOT / name) == expected, "Changed source: " + name
    assert digest(HERE / "audit_delivery.py") == scope["code_sha256"]
    assert not out.exists(), "Use a fresh output directory"

    # Each record is joined by identity, never by a potentially stale prose total.
    definitions = [
        ("initial100", "selection/MAIN100.csv", "production/EXPOSURE_SUMMARY.csv",
         "acquisition/DOWNLOAD_MANIFEST.json", "main_unopened", "exptime_seconds",
         "searched_samples", None),
        ("v2_first100", "v2/selection/MAIN100.csv", "v2/production/EXPOSURES.csv",
         "v2/acquisition/DOWNLOAD_MANIFEST.json", "v2_main_unopened", "exposure_seconds",
         "v1_searched", "v2_searched"),
        ("extension02", "v2/extension02/MAIN100.csv", "v2/extension02/production/EXPOSURES.csv",
         "v2/extension02/acquisition/DOWNLOAD_MANIFEST.json", "extension02_unopened",
         "exposure_seconds", "v1_searched", "v2_searched"),
    ]
    exposure_ledger, cohort_ledger, inputs = [], [], []
    all_selected = []
    all_raw = []
    for cohort, selection, production, manifest, role, time_key, v1_key, v2_key in definitions:
        chosen = rows(B + selection)
        produced = rows(B + production)
        acquired = read_json(B + manifest)
        inputs.extend(dict(r, source_manifest=B + manifest) for r in acquired)
        lookup = {r["dp_id"]: r for r in acquired if r["role"] == role}
        pr = {r["dp_id"]: r for r in produced}
        assert len(chosen) == len(produced) == len(pr) == len(lookup) == 100
        assert {r["dp_id"] for r in chosen} == set(pr) == set(lookup)
        sub = []
        for r in chosen:
            p, a = pr[r["dp_id"]], lookup[r["dp_id"]]
            assert a["header_status"] == "PASS_METADATA_ONLY"
            assert a["download_status"] == "DOWNLOADED"
            assert all(a["checks"].values())
            assert a["sha256"] == p["input_sha256"]
            assert r["canonical_target"] == p["canonical_target"] == a["canonical_target"]
            assert len(a["raw_progenitor_ids"]) == 1
            assert abs(Decimal(p[time_key]) - Decimal(r["t_exptime"])) <= Decimal("0.02")
            assert abs(Decimal(p[time_key]) - Decimal(str(a["primary_header"]["EXPTIME"]))) <= Decimal("0.02")
            assert a["primary_header"]["SPECSYS"] == "BARYCENT"
            assert a["extension_header"]["TUNIT1"].lower() == "angstrom"
            assert a["extension_header"]["TUCD1"] == "em.wl;obs.atmos"
            assert abs(float(a["primary_header"]["SPEC_BIN"]) * 10 - .01) < 1e-10
            if cohort == "initial100":
                assert p["status"] == "COMPLETED"
            item = dict(cohort=cohort, target=r["canonical_target"], dp_id=r["dp_id"],
                        raw_id=a["raw_progenitor_ids"][0], metadata_mjd=r["t_min"],
                        night_key=math.floor(float(r["t_min"]) - .5),
                        exposure_seconds=p[time_key], input_sha256=p["input_sha256"],
                        v1_searched_samples=int(p[v1_key]),
                        v2_searched_samples=int(p[v2_key]) if v2_key else 0,
                        v2_applied=bool(v2_key), configured_air_angstrom_min=3800,
                        configured_air_angstrom_max=6900, grid_step_angstrom=.01,
                        v1_searched_bin_width_sum_angstrom=str(Decimal(p[v1_key]) * Decimal(".01")),
                        v2_searched_bin_width_sum_angstrom=str(Decimal(p[v2_key]) * Decimal(".01")) if v2_key else "",
                        status="COMPLETED_FROM_PUBLISHED_TABLES", source_table=B + production)
            exposure_ledger.append(item)
            sub.append(item)
            all_raw.extend(a["raw_progenitor_ids"])
        all_selected.extend(chosen)
        cohort_ledger.append(dict(cohort=cohort, exposures=len(sub), targets=len({r["target"] for r in sub}),
                                 exposure_seconds=str(sum(Decimal(r["exposure_seconds"]) for r in sub)),
                                 v1_searched_samples=sum(r["v1_searched_samples"] for r in sub),
                                 v2_searched_samples=sum(r["v2_searched_samples"] for r in sub)))
    assert len({r["dp_id"] for r in exposure_ledger}) == len(set(all_raw)) == 300
    assert len({(r["canonical_target"], Decimal(r["t_min"])) for r in all_selected}) == 300
    assert len(inputs) == len({r["dp_id"] for r in inputs}) == 309
    assert len({x for r in inputs for x in r["raw_progenitor_ids"]}) == 309

    current = rows(B + "v2/CURRENT_V2_DISPOSITIONS.csv")
    old = rows(B + "v2/production/V2_DISPOSITIONS.csv")
    newer = rows(B + "v2/extension02/production/V2_DISPOSITIONS.csv")
    originals = {f"V2-{i:04d}": r for i, r in enumerate(old, 1)}
    originals.update({r["candidate_id"]: r for r in newer})
    live = {r["review_id"]: r for r in current}
    assert len(current) == len(live) == len(originals) == 669
    assert set(live) == set(originals)
    queue = read_json("work_harps_20261105_c037_context/scientific_review/ORIGINAL_QUEUE_CLOSURE.json")
    q = {r["candidate_id"]: r for r in queue["records"]}
    assert len(q) == 90 and queue["remaining_original_routes_after_current"] == []
    assert set(q) == {r["review_id"] for r in current if r["review_id"].startswith("V2E2-") and r["current_code"] == "U"}
    dispositions = []
    for r in current:
        original = originals[r["review_id"]]
        assert r["dp_id"] == original["dp_id"]
        assert r["input_sha256"] == original["input_sha256"]
        assert abs(float(r["fitted_center_bary_air_angstrom"]) - float(original["fitted_center_angstrom"])) < 1e-9
        assert r["final_physical_origin_confirmed"] == "False"
        assert r["current_code"] in "AOUM"
        route = q.get(r["review_id"])
        dispositions.append(dict(r, original_production_status=original["origin_status"],
                                 evidence_record_locator=r["evidence_table"] + " :: " + r["review_id"],
                                 original_queue_group=route["core_overlap_group"] if route else "",
                                 original_queue_diagnostic_status=route["diagnostic_routing_status"] if route else "NOT_IN_THIS_90_ROW_QUEUE",
                                 physical_classification_changed=False))
    counts = dict(sorted(Counter(r["current_code"] for r in current).items()))
    recorded_status = read_json(B + "v2/CURRENT_STATUS.json")
    assert counts == {k:v for k,v in recorded_status["current_all_V2_counts"].items() if v}
    assert counts == {"A": 403, "M": 35, "O": 46, "U": 185}

    # V1 is a separate trigger catalogue; its twelve later hits reuse V2 events.
    first = rows(B + "production/HIT_DISPOSITIONS.csv")
    first_review = {r["hit_id"]: r for r in rows(B + "triage_followup/FOLLOWUP_DISPOSITIONS.csv")}
    v1 = []
    for r in first:
        review = first_review[r["hit_id"]]
        assert review["dp_id"] == r["dp_id"] and review["final_origin_confirmed"] == "False"
        v1.append(dict(trigger_id=r["hit_id"], cohort="initial100", target=r["canonical_target"], dp_id=r["dp_id"],
                       air_bary_angstrom=r["wave_peak_angstrom"], input_sha256=r["input_sha256"],
                       current_provisional_disposition=review["followup_status"], evidence=review["evidence"],
                       v2_match_id="", match_distance_angstrom="", physical_origin_confirmed=False))
    for path, prefix, cohort in [("v2/production/V1_HITS.csv", "V1B", "v2_first100"),
                                ("v2/extension02/production/V1_HITS.csv", "V1E2", "extension02")]:
        for i, r in enumerate(rows(B + path), 1):
            matched = [s for s in current if s["dp_id"] == r["dp_id"] and abs(float(s["fitted_center_bary_air_angstrom"]) - float(r["wave_peak_angstrom"])) <= .02000001]
            assert len(matched) == 1
            s = matched[0]
            assert r["input_sha256"] == s["input_sha256"]
            v1.append(dict(trigger_id=f"{prefix}-{i:04d}", cohort=cohort, target=r["canonical_target"], dp_id=r["dp_id"],
                           air_bary_angstrom=r["wave_peak_angstrom"], input_sha256=r["input_sha256"],
                           current_provisional_disposition=s["current_disposition"], evidence="Same-exposure V2 match; " + s["evidence_table"],
                           v2_match_id=s["review_id"], match_distance_angstrom=abs(float(s["fitted_center_bary_air_angstrom"]) - float(r["wave_peak_angstrom"])),
                           physical_origin_confirmed=False))
    assert len(v1) == 22 and sum(bool(r["v2_match_id"]) for r in v1) == 12

    controls = []
    first_trials = rows(B + "validation/results_frozen_20261101/trials.csv")
    second_trials = rows(B + "v2/validation/results/TRIALS.csv")
    assert len(first_trials) == 48 and len(second_trials) == 192
    assert len({(r["geometry_id"], r["amplitude_factor"]) for r in first_trials}) == 48
    assert len({(r["background"], r["anchor_angstrom"], r["phase"], r["amplitude"]) for r in second_trials}) == 192
    for trials, label, amp, rec_key, control_key in [
        (first_trials, "V1_original48", "amplitude_factor", "recovered", "control_hit"),
        (second_trials, "V1_on_fresh192", "amplitude", "v1_recovered", "v1_control_hit"),
        (second_trials, "V2_on_fresh192", "amplitude", "v2_recovered", "v2_control_hit")]:
        for group_key in (amp, "anchor_angstrom"):
            for value in sorted({r[group_key] for r in trials}, key=float):
                group = [r for r in trials if r[group_key] == value]
                controls.append(dict(design=label, grouping="amplitude" if group_key == amp else "anchor_angstrom",
                                     value=value, evaluated=len(group), recovered=sum(truth(r[rec_key]) for r in group),
                                     matching_unmodified_control_hits=sum(truth(r[control_key]) for r in group)))
    for source, label in [("validation/results_frozen_20261101/summary.json", "V1_original48"),
                          ("v2/validation/results/SUMMARY.json", "V2_on_fresh192")]:
        summary = read_json(B + source)
        for a in summary["by_amplitude"]:
            key = "amplitude_factor" if "amplitude_factor" in a else "amplitude"
            row = next(c for c in controls if c["design"] == label and c["grouping"] == "amplitude" and float(c["value"]) == float(a[key]))
            assert row["recovered"] == (a["recovered"] if label == "V1_original48" else a["v2"])
    assert not any(r["matching_unmodified_control_hits"] for r in controls)
    blue = sum(3800 <= float(r["fitted_center_bary_air_angstrom"]) < 4000 for r in current)
    historical_reproduction = {
        "initial100": read_json(B + "review/PRODUCTION_NUMERICAL_REVIEW.json"),
        "v2_first100": read_json(B + "v2/review/NUMERICAL_CHECKS.json"),
        "extension02": read_json(B + "v2/extension02/audit/SUMMARY.json"),
    }
    assert all(r["status"].startswith("PASS") for r in historical_reproduction.values())
    assert len(historical_reproduction["v2_first100"]["full_exposure_repeats"]) == 5
    mapping = read_json(B + "v2/extension02/mapping_followup_remaining_20261102/SUMMARY.json")
    assert mapping["total_mapping_limited_records"] == 35
    assert mapping["status"] == "COMPLETE_DESCRIPTIVE_ALL35_REMAIN_M"

    # A fresh route is fixed from already published catalogue metadata only.
    feasibility = read_json(B + "expansion/FEASIBILITY.json")
    for path, expected in feasibility["output_csv_hashes"].items():
        if path in ("EXTRA_ELIGIBLE_METADATA.csv", "TARGET_INVENTORY.csv"):
            assert digest(ROOT / B / "expansion" / path) == expected
    prior_targets = {r["target"] for r in exposure_ledger} | {"HD100508", "HD203608"}
    prior_ids = {r["dp_id"] for r in inputs}
    prior_keys = {(r["canonical_target"], Decimal(r["t_min"])) for r in all_selected}
    upstream = read_json(B + "literature/UPSTREAM_REFERENCED_IDS.json")
    groups = defaultdict(dict)
    for r in rows(B + "expansion/EXTRA_ELIGIBLE_METADATA.csv"):
        name = r["canonical_target"]
        if name in prior_targets or r["dp_id"] in prior_ids or (name, Decimal(r["t_min"])) in prior_keys:
            continue
        assert r["category"] == "other_HD"
        assert r["dp_id"] not in upstream["ADP"]
        assert r["instrument_name"] == "HARPS" and r["n_obs"] == "1" and r["multi_ob"] == "S"
        assert Decimal(r["snr"]) >= 50 and Decimal(r["t_exptime"]) >= 300 and Decimal(r["t_min"]) >= 58849
        assert r["obs_release_date"] <= "2026-11-01T00:00:00Z"
        key = Decimal(r["t_min"])
        if key not in groups[name] or r["dp_id"] > groups[name][key]["dp_id"]:
            groups[name][key] = r
    eligible = {}
    for name, rr in groups.items():
        rr = sorted(rr.values(), key=lambda r: (Decimal(r["t_min"]), r["dp_id"]))
        if len(rr) >= 5 and len({math.floor(float(r["t_min"]) - .5) for r in rr}) >= 3:
            eligible[name] = rr
    names = sorted(eligible)
    assert len(names) >= 12
    control_names, main_names = names[:2], names[2:12]
    selected = []
    for name in control_names + main_names:
        rr = eligible[name]
        bynight = {}
        for r in rr:
            bynight.setdefault(math.floor(float(r["t_min"]) - .5), r)
        first = list(bynight.values())
        n = 2 if name in control_names else 5
        if len(first) >= n:
            picked = [first[round(i * (len(first) - 1) / (n - 1))] for i in range(n)]
        else:
            picked = first[:]
            picked.extend(r for r in rr if r not in picked)
            picked = sorted(picked[:n], key=lambda r: Decimal(r["t_min"]))
        for r in picked:
            selected.append(dict(r, role="fresh_control_only" if name in control_names else "fresh_main_unopened",
                                 night_key=math.floor(float(r["t_min"]) - .5),
                                 source_metadata=B + "expansion/EXTRA_ELIGIBLE_METADATA.csv",
                                 raw_provenance_status="PENDING_BEFORE_ANY_SCIENCE_FLUX",
                                 prior_search_overlap="UNKNOWN_OUTSIDE_PINNED_REFERENCE_INVENTORY"))
    assert len(selected) == len({r["dp_id"] for r in selected}) == 54
    assert not ({r["dp_id"] for r in selected} & prior_ids)
    assert not ({r["canonical_target"] for r in selected} & prior_targets)
    excluded = [dict(dp_id=r["dp_id"], target=r["canonical_target"], role=r["role"],
                     raw_ids=json.dumps(r["raw_progenitor_ids"]), input_sha256=r["sha256"],
                     source_manifest=r["source_manifest"]) for r in inputs]
    seconds = sum(Decimal(r["exposure_seconds"]) for r in exposure_ledger)
    summary = dict(schema="SETI_D001_PUBLISHED_DELIVERY_AUDIT_V1", status="PASS_METADATA_AND_TABLE_RECONCILIATION",
                   source_base_commit=scope["source_base_commit"], source_files_verified=len(scope["source_hashes"]),
                   unique_main_exposures=300, distinct_main_target_labels=len({r["target"] for r in exposure_ledger}),
                   main_exposure_seconds=str(seconds), main_exposure_hours=float(seconds / 3600),
                   v1_exposures=300, v2_exposures=200,
                   v1_exposure_seconds=str(seconds), v2_exposure_seconds=str(sum(Decimal(r["exposure_seconds"]) for r in exposure_ledger if r["v2_applied"])),
                   v1_searched_samples=sum(r["v1_searched_samples"] for r in exposure_ledger),
                   v2_searched_samples=sum(r["v2_searched_samples"] for r in exposure_ledger),
                   configured_air_bary_angstrom=[3800, 6900], searched_grid_step_angstrom=.01,
                   searched_bin_width_scope="Sums over exposure-specific eligible resampled bins, not a unique wavelength span, independent resolution elements, or continuous monitoring.",
                   historical_fits_rehashed_now=False, historical_detector_or_science_array_reruns=0,
                   saved_reproduction_receipts_present_and_passing=list(historical_reproduction),
                   v1_triggers=len(v1), v1_later_triggers_with_same_exposure_v2_match=12, v2_triggers=len(current),
                   v2_current_provisional_codes=counts, physical_labels_changed=0,
                   raw_review_unreviewed=0, mapping_diagnostic_records=35, mapping_codes_retained=35,
                   original90_queue_rows=90, original90_unfinished_diagnostic_routes=0,
                   original90_is_not_all185_unresolved_features=True,
                   controls=dict(v1_original_trials=48, v1_original_background_stars=1, v1_original_unique_patches=12,
                                 v1_original_recovered=11, v2_fresh_paired_trials=192, v2_background_stars=1,
                                 v2_unique_patches=16, v2_paired_geometries=48, v2_lowest_anchor_angstrom=4231.19,
                                 extension02_specific_validation=False),
                   blue3800to4000_v2_trigger_rows=blue, blue_control_coverage_measured=False,
                   rubin=read_json("work_rubin_20261102/COMBINED_STATUS.json"),
                   week_status="OPTICAL_MINIMUM_DELIVERY_COMPONENTS_PRESENT_WITH_STATED_SENSITIVITY_AND_ORIGIN_LIMITS;_RUBIN_LIMITED_FEASIBILITY_MINIMUM50_UNMET",
                   optical_week_calendar="2026-11-01 through 2026-11-07; this is an interim consolidation on November5, not an elapsed-day7 claim",
                   qualified_laser_candidate_established=False, calibrated_survey_null=False,
                   independent_researcher_or_agent_review_of_this_audit=False)
    prospective = dict(schema="SETI_D001_FRESH_TARGET_ROUTE_V1", status="FIXED_METADATA_COHORT_REQUIRES_SEPARATE_PUBLIC_METHOD_AND_PROVENANCE_GATES",
                       source_base_commit=scope["source_base_commit"], selection_science_arrays_read=0, network_queries=0,
                       eligible_fresh_target_labels=names, control_target_labels=control_names, main_target_labels=main_names,
                       control_exposures=4, main_exposures=50, main_targets=10,
                       main_exposure_seconds=str(sum(Decimal(r["t_exptime"]) for r in selected if r["role"] == "fresh_main_unopened")),
                       excluded_original_targets=sorted(prior_targets), registered_prior_input_ids=len(prior_ids),
                       later_followup_target_exclusion="All later bounded HARPS follow-up targets are in the excluded original20 roster; their extra historical reference epochs do not re-enter this fresh-target route.",
                       raw_identity_exclusion_pending=True, no_flux_download_or_analysis_under_this_audit=True,
                       selection_rule=scope["fresh_target_selection_rule"], candidate_replacement_allowed=False,
                       future_control_design=dict(background_spectra=4, background_stars=2,
                                                  anchors_air_bary_angstrom=[3807.13,3861.29,4233.17,4932.47,5779.53,6617.31],
                                                  phases=[0,.25,.5], amplitudes_original101_population_std=[4,8,16,32],
                                                  trials=288, unique_patches=24, paired_geometries=72,
                                                  line_fwhm="center/115000", unchanged_V2_detector=True,
                                                  recovery_rule="accepted fitted center within0.02000001 Angstrom; record unchanged matched controls separately",
                                                  adaptation_after_control_or_main_values=False,
                                                  interpretation="Conditional reduced1D recovery across two fresh stars and blue/red anchors; not full instrument completeness or a global false-alarm rate."),
                       required_next_gates=["Verify current selected ADP metadata and raw provenance against prior inputs and pinned references; retain any failures without replacements.",
                                            "Publish and read back a separate complete acquisition/header/control/main-analysis method before new science values.",
                                            "Archive exact acquired bytes; analyze only admitted headers; preserve every failed input, control miss, trigger and incomplete outcome."],
                       spending_limit_DKK=0, no_paid_service_or_new_account_or_researcher_contact=True,
                       rubin_route_reopened=False, no_background_science_running=True)
    out.mkdir(parents=True)
    for name, rr in [("EXPOSURE_LEDGER.csv", exposure_ledger), ("COHORT_COVERAGE.csv", cohort_ledger),
                     ("V2_CURRENT_DISPOSITIONS_669.csv", dispositions), ("V1_DISPOSITIONS_22.csv", v1),
                     ("CONTROL_RECOVERY.csv", controls), ("PRIOR309_EXCLUSIONS.csv", excluded),
                     ("FRESH_METADATA_COHORT54.csv", selected)]:
        write_csv(out / name, rr)
    write_json(out / "DELIVERY_AUDIT.json", summary)
    write_json(out / "FRESH_ROUTE_PLAN.json", prospective)
    write_json(out / "OUTPUT_HASHES.json", {p.name:digest(p) for p in sorted(out.iterdir())})
    print(json.dumps({k:summary[k] for k in ["status","unique_main_exposures","main_exposure_seconds","v1_searched_samples","v2_searched_samples","blue3800to4000_v2_trigger_rows"]}))
    print(json.dumps({k:prospective[k] for k in ["status","control_target_labels","main_target_labels","main_exposures","main_exposure_seconds"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    run(parser.parse_args().out)
