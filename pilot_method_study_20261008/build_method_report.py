#!/usr/bin/env python3
"""Build descriptive figures/report only from closed, independently audited JSON.

Preparation/import is inert. No generator, detector, scientific pipeline, source
reader, telescope array, retained numeric map, network request, or admission is
used. Plotting imports occur only after all 64 METHOD_STUDY outcomes close and
their independent audit and the closed B evidence match exact file digests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
LEVELS = (10.0, 12.0, 16.0, 24.0)
DRIFTS = (-4.0, -1.25, 1.25, 4.0)
WIDTHS = (1, 3)
ACTIVITIES = ((4,), (0, 2, 4))
METHOD_CASES_SHA256 = "554a54d9ddfa1c0f82f0932ee93ba2bb652542588c65fbd4be56c144b7c4d2f4"
B_CASES_SHA256 = "93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c"
ACTIVITY_NAMES = {(4,): "single_third_ON", (0, 2, 4): "all_three_ON"}
EXPECTED_B_FAMILIES = {"strong": 14, "operating": 48, "matched_rfi": 24,
                       "noise": 32, "single_row_transient": 12, "near_off_contamination": 12}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError("Empty report table")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def markdown_table(headers: list[str], rows: list[list]) -> str:
    def text(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |",
                       "| " + " | ".join("---" for _ in headers) + " |"]
                      + ["| " + " | ".join(text(value) for value in row) + " |" for row in rows])


def check_marker(marker: dict, panel: str, count: int, status: str) -> None:
    if (marker.get("status") != status or marker.get("panel") != panel
            or marker.get("case_count_expected") != count or marker.get("case_count_observed") != count
            or marker.get("all_children_reaped") is not True
            or marker.get("no_retry_or_redraw") is not True):
        raise ValueError(f"Complete durable closed {panel} marker required before reading outcomes")
    if panel == "METHOD_STUDY" and (marker.get("qualification") is not False
            or marker.get("scientific_gate") != "EXPLORATORY_METHOD_STUDY_ONLY"
            or marker.get("cpu_budget_passed") is not True):
        raise ValueError("METHOD_STUDY marker must remain descriptive and resource-complete")


def validate_inputs(method_output: Path, b_output: Path, audit_path: Path) -> tuple[dict, dict]:
    # Outcomes are not read or hashed until both panels' final markers exist and
    # the independent complete-study audit has explicitly succeeded.
    method_marker = read_json(method_output / "COMMITTED_PANEL.json")
    b_marker = read_json(b_output / "COMMITTED_PANEL.json")
    check_marker(method_marker, "METHOD_STUDY", 64, "COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY")
    check_marker(b_marker, "VAL_B", 142, "CLOSED_FAIL")
    audit = read_json(audit_path)
    if (audit.get("status") != "PASS_INDEPENDENT_METHOD_STUDY_OUTPUT_AUDIT"
            or audit.get("panel") != "METHOD_STUDY" or audit.get("independent_audit") is not True
            or audit.get("case_count_expected") != 64 or audit.get("case_count_observed") != 64
            or audit.get("complete") is not True or audit.get("qualification") is not False):
        raise ValueError("Independent complete METHODS64 output audit required before report plotting")
    paths = {"method_cases": ROOT / "pilot_method_study_20261008/method_cases.json",
             "b_cases": ROOT / "pilot_controls_20261008/validation_b_cases.json",
             "method_outcomes": method_output / "outcomes.json", "method_summary": method_output / "summary.json",
             "method_resource_receipt": method_output / "resource_receipt.json",
             "method_completion": method_output / "COMMITTED_PANEL.json",
             "b_outcomes": b_output / "outcomes.json", "b_summary": b_output / "summary.json",
             "b_resource_receipt": b_output / "resource_receipt.json", "b_completion": b_output / "COMMITTED_PANEL.json"}
    observed = {key: digest(path) for key, path in paths.items()}
    if (observed["method_cases"] != METHOD_CASES_SHA256 or observed["b_cases"] != B_CASES_SHA256
            or any(audit.get("sha256", {}).get(key) != value for key, value in observed.items())):
        raise ValueError("Independent audit does not bind these exact closed metadata inputs")
    for marker, prefix in ((method_marker, "method"), (b_marker, "b")):
        for name in ("outcomes", "summary", "resource_receipt"):
            if marker.get(name + "_SHA256") != observed[prefix + "_" + name]:
                raise ValueError("Final panel marker and retained aggregate bytes disagree")
    values = {key: read_json(path) for key, path in paths.items()
              if key not in {"method_completion", "b_completion"}}
    values.update(method_completion=method_marker, b_completion=b_marker, audit=audit)
    method_summary = values["method_summary"]
    if (method_summary.get("panel") != "METHOD_STUDY" or method_summary.get("complete") is not True
            or method_summary.get("status") != "COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY"
            or method_summary.get("case_count_expected") != 64 or method_summary.get("case_count_observed") != 64
            or method_summary.get("missing_case_ids") != [] or method_summary.get("failed_case_ids") != []
            or method_summary.get("scientific_gate") != "EXPLORATORY_METHOD_STUDY_ONLY"
            or method_summary.get("qualification") is not False
            or method_summary.get("A_remains_FAIL_CLOSED") is not True
            or method_summary.get("B_remains_FAIL_CLOSED") is not True
            or method_summary.get("telescope_values_opened") is not False):
        raise ValueError("Closed complete descriptive method summary required")
    b_summary = values["b_summary"]
    if (b_summary.get("panel") != "VAL_B" or b_summary.get("scientific_gate") != "FAIL_CLOSED"
            or b_summary.get("case_count_expected") != 142 or b_summary.get("case_count_observed") != 142
            or b_summary.get("missing_case_ids") != []):
        raise ValueError("All 142 retained B attempts and unchanged failed qualification required")
    if (values["method_resource_receipt"].get("all_children_reaped") is not True
            or values["method_resource_receipt"].get("cpu_budget_passed") is not True):
        raise ValueError("Method output resource closure must precede plotting")
    observed["independent_audit"] = digest(audit_path)
    return values, observed


def validate_cases_outcomes(cases: list[dict], outcomes: list[dict], panel: str, count: int) -> dict:
    if (len(cases) != count or len(outcomes) != count
            or len({c["case_id"] for c in cases}) != count
            or len({o["case_id"] for o in outcomes}) != count
            or {c["case_id"] for c in cases} != {o["case_id"] for o in outcomes}
            or any(c.get("panel") != panel or o.get("panel") != panel
                   for c, o in zip(cases, outcomes))
            or any(hashlib.sha256(c["case_id"].encode("ascii")).hexdigest() != c["seed_sha256"] for c in cases)):
        raise ValueError(f"Complete distinct frozen {panel} metadata identities required")
    observed = {o["case_id"]: o for o in outcomes}
    if any(observed[c["case_id"]].get("family") != c["family"] for c in cases):
        raise ValueError("Case family and retained outcome differ")
    return observed


def response_counts(outcomes: list[dict]) -> dict:
    valid = [o for o in outcomes if o.get("data_integrity_ok") is True and not o.get("failure")]
    return {"expected": len(outcomes), "observed": len(outcomes), "integrity_valid": len(valid),
            "pre_OFF_all_active_recovery": sum(o["pre_OFF_all_active_recovery"] is True for o in valid),
            "final_all_active_recovery": sum(o["all_active_on_recovered"] is True for o in valid),
            "final_any_active_recovery": sum(o["any_localized_on_recovered"] is True for o in valid),
            "all_active_recovery_lost_after_OFF": sum(o["pre_OFF_all_active_recovery"] is True
                                                       and o["all_active_on_recovered"] is not True for o in valid)}


def build_method_tables(cases: list[dict], outcomes: list[dict], summary: dict) -> tuple[list, list]:
    observed = validate_cases_outcomes(cases, outcomes, "METHOD_STUDY", 64)
    expected_grid = set(itertools.product(LEVELS, DRIFTS, WIDTHS, ACTIVITIES))
    actual_grid = {(float(c["nominal_ideal_box_score"]), float(c["drift_hz_s"]),
                    int(c["intrinsic_width_channels"]), tuple(c["active_scan_indices"])) for c in cases}
    if len(actual_grid) != 64 or actual_grid != expected_grid:
        raise ValueError("Exactly one realization per prespecified strength/drift/width/activity cell required")
    cells = []
    for case in cases:
        outcome = observed[case["case_id"]]
        if (case.get("family") != "method_signal" or case.get("eligibility_case") is not False
                or outcome.get("data_integrity_ok") is not True or outcome.get("failure")):
            raise ValueError("All 64 cells must be integrity-valid before figures are produced")
        for key in ("all_active_on_recovered", "any_localized_on_recovered",
                    "pre_OFF_all_active_recovery", "pre_OFF_any_active_recovery"):
            if not isinstance(outcome.get(key), bool):
                raise ValueError("Recovery metadata must contain explicit Boolean responses")
        if (outcome["all_active_on_recovered"] and not outcome["any_localized_on_recovered"]
                or outcome["all_active_on_recovered"] and not outcome["pre_OFF_all_active_recovery"]
                or outcome["any_localized_on_recovered"] and not outcome["pre_OFF_any_active_recovery"]):
            raise ValueError("Retained recovery stages are inconsistent")
        cells.append({"case_id": case["case_id"], "nominal_ideal_box_score": case["nominal_ideal_box_score"],
                      "drift_hz_s": case["drift_hz_s"], "intrinsic_width_channels": case["intrinsic_width_channels"],
                      "activity": ACTIVITY_NAMES[tuple(case["active_scan_indices"])],
                      "reference_native_offset": case["reference_native_offset"],
                      "pre_OFF_all_active_recovered": outcome["pre_OFF_all_active_recovery"],
                      "pre_OFF_any_active_recovered": outcome["pre_OFF_any_active_recovery"],
                      "final_all_active_recovered": outcome["all_active_on_recovered"],
                      "final_any_active_recovered": outcome["any_localized_on_recovered"],
                      "ON_threshold_carrier_count": outcome["ON_threshold_carrier_count"],
                      "surviving_ON_carrier_count": outcome["survivor_count"],
                      "loss_stage_by_active_ON_scan": outcome.get("loss_stage_by_active_ON_scan", {}),
                      "ON_global_maximum_robust_score_by_scan": outcome.get("ON_global_maximum_robust_score_by_scan", {}),
                      "cpu_s": outcome["cpu_s"], "wall_s": outcome["wall_s"],
                      "peak_rss_bytes": outcome["peak_rss_bytes"]})
    if summary.get("counts") != response_counts(outcomes):
        raise ValueError("Descriptive summary totals differ from complete retained outcomes")
    for label, key in (("declared_ideal_score", "nominal_ideal_box_score"), ("drift_hz_s", "drift_hz_s"),
                       ("intrinsic_width_channels", "intrinsic_width_channels"),
                       ("active_scan_indices", "active_scan_indices"),
                       ("reference_native_offset", "reference_native_offset")):
        grouped = {}
        for case in cases:
            group = json.dumps(case[key], separators=(",", ":"))
            grouped.setdefault(group, []).append(observed[case["case_id"]])
        recomputed = {group: response_counts(members) for group, members in grouped.items()}
        if summary.get("groups", {}).get(label) != recomputed:
            raise ValueError("Descriptive summary group differs from closed valid-cell counts")
    aggregates = []
    for dimension, values, field in (("strength", LEVELS, "nominal_ideal_box_score"),
                                     ("drift", DRIFTS, "drift_hz_s")):
        for activity, width, value in itertools.product(ACTIVITY_NAMES.values(), WIDTHS, values):
            members = [c for c in cells if c["activity"] == activity
                       and c["intrinsic_width_channels"] == width and float(c[field]) == value]
            if len(members) != 4:
                raise ValueError("Every fixed activity/width strength/drift aggregate requires exactly four cells")
            aggregates.append({"dimension": dimension, "activity": activity,
                               "intrinsic_width_channels": width, "factor_value": value,
                               "expected": 4, "valid": 4,
                               "final_all_active_recovered": sum(c["final_all_active_recovered"] for c in members),
                               "final_any_active_recovered": sum(c["final_any_active_recovered"] for c in members),
                               "pre_OFF_all_active_recovered": sum(c["pre_OFF_all_active_recovered"] for c in members),
                               "pre_OFF_any_active_recovered": sum(c["pre_OFF_any_active_recovered"] for c in members)})
    return cells, aggregates


def build_b_tables(cases: list[dict], outcomes: list[dict], summary: dict) -> list[dict]:
    observed = validate_cases_outcomes(cases, outcomes, "VAL_B", 142)
    if {family: sum(c["family"] == family for c in cases) for family in EXPECTED_B_FAMILIES} != EXPECTED_B_FAMILIES:
        raise ValueError("Complete frozen B family definitions required")
    rows = []
    for family in ("matched_rfi", "noise", "single_row_transient", "near_off_contamination", "strong", "operating"):
        members = [observed[c["case_id"]] for c in cases if c["family"] == family]
        valid = [o for o in members if o.get("data_integrity_ok") is True and not o.get("failure")]
        frozen = summary.get("families", {}).get(family, {})
        if frozen.get("expected") != len(members) or frozen.get("observed") != len(members):
            raise ValueError("Closed B family summary omits retained outcomes")
        rows.append({"family": family, "expected": len(members), "observed": len(members),
                     "integrity_valid": len(valid), "integrity_failed": len(members) - len(valid),
                     "pre_OFF_all_active_recovery": None if family == "noise" else
                         sum(bool(o.get("rfi_pre_off_all_active_detected", o.get("pre_OFF_all_active_recovery", False))) for o in valid),
                     "final_all_active_recovery": None if family == "noise" else sum(o.get("all_active_on_recovered") is True for o in valid),
                     "final_any_active_recovery": None if family == "noise" else sum(o.get("any_localized_on_recovered") is True for o in valid),
                     "cadences_with_any_survivor": sum(int(o.get("survivor_count", 0)) > 0 for o in valid),
                     "raw_ON_threshold_carriers": sum(int(o.get("ON_threshold_carrier_count", 0)) for o in valid),
                     "surviving_ON_carriers": sum(int(o.get("survivor_count", 0)) for o in valid)})
    return rows


def build_loss_stage_table(cells: list[dict]) -> list[dict]:
    stages = ("LOCALIZED_SURVIVOR", "LOCALIZED_HITS_OFF_VETOED",
              "NO_ON_THRESHOLD_HIT", "ON_HITS_NOT_LOCALIZED")
    rows = []
    for activity, width in itertools.product(ACTIVITY_NAMES.values(), WIDTHS):
        members = [c for c in cells if c["activity"] == activity and c["intrinsic_width_channels"] == width]
        expected_active_ids = {"epoch3_on"} if activity == "single_third_ON" else {"epoch1_on", "epoch2_on", "epoch3_on"}
        labels = []
        for member in members:
            retained = member["loss_stage_by_active_ON_scan"]
            if set(retained) != expected_active_ids or any(value not in stages for value in retained.values()):
                raise ValueError("Original audited per-active-ON loss-stage labels required for descriptive report")
            labels.extend(retained.values())
        rows.append({"activity": activity, "intrinsic_width_channels": width,
                     "case_count": len(members), "originating_ON_scan_count": len(labels),
                     **{stage: labels.count(stage) for stage in stages}})
    return rows


def build_marginal_table(cases: list[dict], outcomes: list[dict]) -> list[dict]:
    observed = {o["case_id"]: o for o in outcomes}
    rows = []
    for dimension, field in (("nominal_ideal_box_score", "nominal_ideal_box_score"),
                             ("drift_hz_s", "drift_hz_s"),
                             ("intrinsic_width_channels", "intrinsic_width_channels"),
                             ("active_scan_indices", "active_scan_indices"),
                             ("reference_native_offset", "reference_native_offset")):
        groups = {}
        for case in cases:
            factor = json.dumps(case[field], separators=(",", ":"))
            groups.setdefault(factor, []).append(observed[case["case_id"]])
        for factor, members in groups.items():
            counts = response_counts(members)
            valid = [o for o in members if o.get("data_integrity_ok") is True and not o.get("failure")]
            rows.append({"dimension": dimension, "factor_value": factor, **counts,
                         "pre_OFF_any_active_recovery": sum(o["pre_OFF_any_active_recovery"] is True for o in valid)})
    return rows


def render_report(cells: list[dict], aggregates: list[dict], b_rows: list[dict], values: dict,
                  figures: dict, hashes: dict, losses: list[dict], marginals: list[dict]) -> str:
    all_count = sum(c["final_all_active_recovered"] for c in cells)
    any_count = sum(c["final_any_active_recovered"] for c in cells)
    sections = ["# Descriptive fixed-method recovery study\n",
                f"All 64 prespecified synthetic cells completed and passed independent retained-output audit. "
                f"Final all-active recovery was observed in **{all_count}/64** cells; final any-active recovery "
                f"was observed in **{any_count}/64** cells. These are descriptive counts. Both original validation "
                "A and B remain **FAIL_CLOSED**; this study has no qualification authority and uses no telescope values.\n",
                "## Interpretation\n",
                "There is one independent synthetic realization per exact strength, drift, width and activity cell. "
                "Each plotted strength/drift aggregate fixes width and activity and pools four cells across the other "
                "factor (**n=4**, not four repeated draws at the same setting). Binary cell panels have **n=1 per cell**. "
                "No probabilities, confidence intervals, sensitivity interpolation or false-alarm bounds are estimated.\n",
                "The nominal input level is the declared noise-free ideal box projection in Gamma16 noise units "
                "(raw sigma 0.25); it is neither measured detector S/N nor physical flux. All-active recovery across "
                "three ON scans is stricter than single-third-ON recovery; any-active recovery is a union. The two "
                "activity groups have independent noise draws and do not provide a paired causal comparison. "
                "Width means intrinsic injected width (1 or 3 channels), not winning search width.\n",
                "The design followed observed B losses, so it is an exploratory method study rather than blind "
                "validation. Placement is a deterministic balanced blocking factor, with one placement/seed per "
                "cell; placement interactions are not independently identified.\n", "## Figures\n"]
    for figure in figures["figures"]:
        response = "Final all-active recovery" if figure["response"] == "final_all_active_recovered" else "Final any-active recovery"
        title = response + (": exact binary cells" if figure["kind"] == "exact_binary_cell_responses" else
                            " versus " + ("nominal input level" if figure["dimension"] == "strength" else "drift"))
        paths = {item["format"]: Path(item["path"]).name for item in figure["files"]}
        caption = ("One realization per exact cell (n=1); binary observed response." if figure["kind"] == "exact_binary_cell_responses" else
                   "Discrete observed counts out of four distinct cells; width/activity fixed, opposite factor pooled. No interpolated curve or uncertainty estimate.")
        sections.append(f"### {title}\n\n![{title}]({paths['png']})\n\n"
                        f"[Vector PDF]({paths['pdf']}). {caption}\n")
    sections.extend(["## Strength and drift aggregate counts\n",
                     markdown_table(["Factor", "Activity", "Width", "Value", "Valid / expected", "All-active final", "Any-active final"],
                         [[a["dimension"], a["activity"], a["intrinsic_width_channels"], a["factor_value"], "4 / 4",
                           f"{a['final_all_active_recovered']}/4", f"{a['final_any_active_recovered']}/4"] for a in aggregates]),
                     "\n\nThe complete 64-cell table and before/after OFF counts are retained in CSV and JSON.\n",
                     "## Marginal descriptive counts\n",
                     markdown_table(["Factor", "Value", "Valid / expected", "Pre-OFF all-active", "Pre-OFF any-active", "Final all-active", "Final any-active"],
                         [[r["dimension"], r["factor_value"], f"{r['integrity_valid']}/{r['expected']}",
                           r["pre_OFF_all_active_recovery"], r["pre_OFF_any_active_recovery"],
                           r["final_all_active_recovery"], r["final_any_active_recovery"]] for r in marginals]),
                     "\n\nLevel, drift, and placement marginals each pool 16 distinct cells; width and activity "
                     "marginals each pool 32. They mix the other factors and remain observed descriptive counts, "
                     "not repeated-realization response estimates.\n",
                     "## Retained originating-ON loss stages\n",
                     markdown_table(["Activity", "Width", "Cases", "Originating ON scans", "Localized survivor", "Localized but OFF-vetoed", "No ON threshold hit", "ON hits not localized"],
                         [[r["activity"], r["intrinsic_width_channels"], r["case_count"], r["originating_ON_scan_count"],
                           r["LOCALIZED_SURVIVOR"], r["LOCALIZED_HITS_OFF_VETOED"], r["NO_ON_THRESHOLD_HIT"],
                           r["ON_HITS_NOT_LOCALIZED"]] for r in losses]),
                     "\n\nThese stage labels are read from the original audited outcomes; no detector is rerun. "
                     "Multiple active ON scans within a cadence are not independent replicated cells. ON "
                     "global maximum robust box-track scores are retained per cell in the report data for threshold misses.\n",
                     "## Complete closed B evidence\n",
                     "All 142 prespecified B attempts are retained. The original B scientific summary remains "
                     "FAIL_CLOSED. The following tables include every RFI, noise and diagnostic family, plus the "
                     "strong/operating families for context. Recovery and hit counts use integrity-valid cases; "
                     "invalid attempts remain separate and are not treated as measured nonrecovery. Noise has no "
                     "injected active-ON recovery truth (shown as —).\n",
                     markdown_table(["B family", "Valid / expected", "Failed", "Pre-OFF all-active", "Final all-active", "Final any-active", "Cadences with survivor"],
                         [[r["family"], f"{r['integrity_valid']}/{r['expected']}", r["integrity_failed"],
                           "—" if r["pre_OFF_all_active_recovery"] is None else r["pre_OFF_all_active_recovery"],
                           "—" if r["final_all_active_recovery"] is None else r["final_all_active_recovery"],
                           "—" if r["final_any_active_recovery"] is None else r["final_any_active_recovery"],
                           r["cadences_with_any_survivor"]] for r in b_rows]),
                     "\n\n" + markdown_table(["B family", "Raw ON threshold carriers", "Surviving ON carriers"],
                         [[r["family"], r["raw_ON_threshold_carriers"], r["surviving_ON_carriers"]] for r in b_rows]),
                     "\n\nThese are retained counts from failed qualification. In particular, noise/RFI survivor "
                     "counts are not calibrated sky probabilities or false-alarm limits.\n",
                     "### Original B checks\n",
                     markdown_table(["Prespecified check", "Closed B result"],
                         [[key, "PASS" if value is True else "FAIL"] for key, value in sorted(values["b_summary"]["checks"].items())]),
                     "\n\nThe original closed B summary, all its checks, and input SHA256 provenance are retained "
                     "verbatim in `report_data.json`. This report does not change them.\n"])
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method-output", type=Path, default=ROOT / "results/radio_pilot_method_study_20261008")
    parser.add_argument("--b-output", type=Path, default=ROOT / "results/radio_pilot_val_b_20261008")
    parser.add_argument("--audit", type=Path, default=ROOT / "pilot_protocol_20261008/review/COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    started = time.monotonic()
    if args.output.exists():
        raise FileExistsError("Report output already exists")
    if any(args.output.resolve().is_relative_to(p.resolve()) for p in (args.method_output, args.b_output)):
        raise ValueError("Report output must be separate from retained panel evidence")
    values, hashes = validate_inputs(args.method_output, args.b_output, args.audit)
    cells, aggregates = build_method_tables(values["method_cases"], values["method_outcomes"], values["method_summary"])
    b_rows = build_b_tables(values["b_cases"], values["b_outcomes"], values["b_summary"])
    losses = build_loss_stage_table(cells)
    marginals = build_marginal_table(values["method_cases"], values["method_outcomes"])
    args.output.mkdir(parents=True, exist_ok=False)
    renderer_path = Path(__file__).with_name("method_figures.py")
    spec = importlib.util.spec_from_file_location("fixed_descriptive_method_figures", renderer_path)
    if spec is None or spec.loader is None:
        raise ValueError("Missing standalone fixed figure renderer")
    renderer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = renderer
    spec.loader.exec_module(renderer)
    figures = renderer.render_figures(aggregates, cells, args.output)
    csv_cells = [{key: json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
                  for key, value in cell.items()} for cell in cells]
    write_csv(args.output / "method_cells.csv", csv_cells)
    write_csv(args.output / "strength_drift_counts.csv", aggregates)
    write_csv(args.output / "closed_B_family_counts.csv", b_rows)
    write_csv(args.output / "originating_ON_loss_stages.csv", losses)
    write_csv(args.output / "method_marginal_counts.csv", marginals)
    write_json(args.output / "report_data.json", {"status": "DESCRIPTIVE_REPORT_AFTER_CLOSED_INDEPENDENT_AUDIT",
               "qualification": False, "scientific_gate": "EXPLORATORY_METHOD_STUDY_ONLY",
               "methods_expected_observed_valid": [64, 64, 64], "n_per_exact_factor_cell": 1,
               "n_per_fixed_activity_width_strength_or_drift_aggregate": 4,
               "method_cells": cells, "strength_drift_aggregates": aggregates, "closed_B_family_counts": b_rows,
               "originating_ON_loss_stages": losses,
               "method_marginal_group_counts": marginals,
               "original_closed_method_summary": values["method_summary"],
               "original_closed_B_summary": values["b_summary"], "input_sha256": hashes,
               "independent_audit": values["audit"], "figures": figures,
               "script_sha256": {"report": digest(Path(__file__)), "figures": digest(renderer_path)}})
    (args.output / "METHOD_STUDY_REPORT.md").write_text(render_report(cells, aggregates, b_rows, values, figures, hashes, losses, marginals))
    usage = resource.getrusage(resource.RUSAGE_SELF)
    write_json(args.output / "report_resource_receipt.json", {"wall_s": time.monotonic() - started,
               "whole_process_cpu_s": usage.ru_utime + usage.ru_stime, "peak_rss_bytes": usage.ru_maxrss * 1024,
               "activity": "Closed JSON metadata aggregation and descriptive matplotlib report only"})
    manifest = {p.name: {"SHA256": digest(p), "size_bytes": p.stat().st_size}
                for p in sorted(args.output.iterdir()) if p.is_file()}
    write_json(args.output / "report_artifact_manifest.json", manifest)
    print(json.dumps({"status": "DESCRIPTIVE_REPORT_CREATED", "qualification": False,
                      "output": str(args.output.resolve()), "method_cells": 64}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
