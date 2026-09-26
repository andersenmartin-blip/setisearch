"""Fresh synthetic downstream fixture for the direct eccentric factor table."""
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

from seti_repeater import exposure_radio as exposure
from seti_repeater import factors_radio as direct
from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native
from radio_direct_factors_fixture import inputs as factor_inputs

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/radio_direct_downstream_engineering_20260926.json"
OUT = ROOT / "results_radio_direct_downstream_2026-09-26"


def write(name, value):
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (OUT / name).write_bytes(gzip.compress(payload, mtime=0) if name.endswith(".gz") else payload)


def setup():
    cfg = json.loads(CONFIG.read_text())
    old_cfg, source, banks, _ = factor_inputs()
    bank = banks[cfg["coordinate_scenario"]]
    if cfg["primary"] != "neighbor9" or cfg["native_channels"] != old_cfg["native_channels"]:
        raise ValueError("direct downstream engineering design changed primary or native geometry")
    scans = [{"epoch": i // 2 + 1, "kind": item["role"], "label": item["label"],
              "expected_header": {"dataset_shape": [16, 1, cfg["native_channels"]]},
              "source_domain": "synthetic"} for i, item in enumerate(source["scans"])]
    design = json.loads((ROOT / "results_radio_motion_2026-09-26/prospective_design.json").read_text())
    window = next(item for item in design["windows"] if item["role"] == "validation")
    grid = core.make_proxy_carrier_grid(
        window["proposed_first_on_midpoint_carrier_center_hz"] / 1e6,
        design["proposed_grid"]["carrier_spacing_hz"], cfg["score_half_bins"],
        cfg["support_guard_bins"])
    geometry = core.NativeFrequencyGeometry(
        window["native_frequency_low_hz"], design["proposed_grid"]["carrier_spacing_hz"],
        cfg["native_channels"])
    context = pipeline.Context(scans=scans, factors=bank, grid=grid,
        window="radio-direct-downstream-validation-engineering-20260926",
        maximum_records=cfg["maximum_records_per_role"],
        memory_limit_bytes=cfg["modelled_array_limit_bytes"])
    return cfg, context, geometry


def sources(context, geometry, seed, case, *, calibration=False):
    cfg = json.loads(CONFIG.read_text()); rng = np.random.default_rng(seed)
    output = {}; raw_hashes = {}
    for scan in context.scans:
        raw = np.asarray(100 + rng.standard_normal((16, geometry.channel_count)), dtype="<f4")
        if calibration:
            raw[:, ::cfg["calibration_comb_spacing_channels"]] += np.float32(
                cfg["calibration_comb_addition_per_channel"])
        epochs = case[scan["kind"] + "_epochs"]
        if scan["epoch"] - 1 in epochs:
            t = cfg["truth_template_index"]
            starts = direct.for_scan(context.factor_contract.factors, scan["label"], sample="start")[t]
            ends = direct.for_scan(context.factor_contract.factors, scan["label"], sample="end")[t]
            q = context.grid.score_hz[cfg["truth_score_index"]]
            a = (q * starts - geometry.raw_zero_hz) / geometry.channel_width_hz
            b = (q * ends - geometry.raw_zero_hz) / geometry.channel_width_hz
            raw = exposure.add_linear_exposure(
                raw, a, b, intrinsic_width_channels=case["intrinsic_width_channels"],
                total_power=cfg["injection_total_digital_power_per_row"])
        raw_hashes[scan["label"]] = native.array_hash(raw)
        output[scan["label"]] = native.normalize_synthetic_rows(
            lambda row, values=raw: values[row], geometry, 16,
            input_orientation="ascending", scope={"kind": "synthetic",
                "scan": scan["label"],
                "direct_factor_bank_sha256": context.factor_contract.factors.identity,
                "fixture_seed": seed, "case": case["name"],
                "calibration_comb": calibration,
                "finite_exposure_injection_before_normalization": True})
    return output, raw_hashes


def account(report, context, case):
    cfg = json.loads(CONFIG.read_text())
    records = report["detector"]["retained"]["on"]
    decisions = {item["record_id"]: item for item in report["detector"]["decisions"]}
    factors = context.factor_contract.matrix_for_kind("on")
    truth = context.grid.score_hz[cfg["truth_score_index"]] * factors[cfg["truth_template_index"]]
    eligible = []
    for record in records:
        track = record["proxy_carrier_hz"] * factors[record["template_index"]]
        if (set(record["active_epochs_zero_based"]).issubset(case["on_epochs"])
                and float(np.max(np.abs(track - truth))) <= 2 * context.grid.channel_width_hz):
            eligible.append(record["record_id"])
    physical = [rid for rid in eligible if decisions[rid]["passes_evaluated_physical_vetoes"]]
    final = [rid for rid in physical if decisions[rid]["meets_diagnostic_rank_cut"]]
    all_final = [rid for rid, d in decisions.items()
                 if d["passes_evaluated_physical_vetoes"] and d["meets_diagnostic_rank_cut"]]
    return {"retained_associated_ids": eligible, "physical_associated_ids": physical,
        "final_associated_ids": final, "recovered": bool(final),
        "all_final_member_count": len(all_final), "all_on_member_count": len(records),
        "all_off_member_count": len(report["detector"]["retained"]["off"]),
        "cluster_count": len(report["clusters"])}


@lru_cache(maxsize=1)
def panel():
    cfg, context, geometry = setup()
    blank = {"name": "calibration", "on_epochs": [], "off_epochs": [],
             "intrinsic_width_channels": 1}
    calibration_sources, calibration_raw = sources(
        context, geometry, cfg["calibration_seed"], blank, calibration=True)
    calibration_run = pipeline.NativeRun(context, calibration_sources)
    calibration_store = calibration_run.build_store()
    shifts = core.make_scramble_shift_table(
        cfg["scramble_count"], 3, context.grid.score_bin_count,
        seed=cfg["scramble_seed"], minimum_shift_bins=cfg["minimum_shift_bins"])
    calibration = calibration_run.calibrate(
        calibration_store, shifts=shifts, minimum_shift_bins=cfg["minimum_shift_bins"],
        reference_floor=cfg["reference_floor"], quantile=cfg["quantile"],
        rank_ceiling=cfg["rank_ceiling"])
    reports = {}; outcomes = {}; runs = {}; raw_receipts = {"calibration": calibration_raw}
    for case in cfg["cases"]:
        case_sources, hashes = sources(context, geometry, case["seed"], case)
        run = pipeline.NativeRun(context, case_sources); store = run.build_store()
        report = run.execute(store, calibration)
        reports[case["name"]] = report; outcomes[case["name"]] = account(report, context, case)
        runs[case["name"]] = (run, store); raw_receipts[case["name"]] = hashes
    identities = [tuple(sorted(item.source_ids.items())) for item, _ in runs.values()]
    if len(set(identities)) != len(identities) or tuple(sorted(calibration_run.source_ids.items())) in identities:
        raise ValueError("development/calibration/evaluation source identities are not disjoint")
    return {"config": cfg, "context": context, "calibration": calibration,
        "calibration_run": calibration_run, "calibration_store": calibration_store,
        "reports": reports, "outcomes": outcomes, "runs": runs,
        "raw_receipts": raw_receipts}


def main():
    OUT.mkdir(exist_ok=True); p = panel()
    write("reports.json.gz", p["reports"])
    write("raw_receipts.json", p["raw_receipts"])
    summaries = {}
    for name, outcome in p["outcomes"].items():
        decisions = p["reports"][name]["detector"]["decisions"]
        dispositions = {}
        for item in decisions:
            key = item["physical_disposition"]
            dispositions[key] = dispositions.get(key, 0) + 1
        summaries[name] = {
            "recovered": outcome["recovered"],
            "retained_associated_count": len(outcome["retained_associated_ids"]),
            "physical_associated_count": len(outcome["physical_associated_ids"]),
            "final_associated_count": len(outcome["final_associated_ids"]),
            "all_on_member_count": outcome["all_on_member_count"],
            "all_off_member_count": outcome["all_off_member_count"],
            "all_final_member_count": outcome["all_final_member_count"],
            "cluster_count": outcome["cluster_count"],
            "physical_disposition_counts": dispositions,
            "complete_report_sha256": p["reports"][name]["report_sha256"],
        }
    result = {"schema": "radio-direct-downstream-qualification-v1",
        "status": "DIRECT_DOWNSTREAM_ENGINEERING_COMPLETE",
        "direct_factor_contract_sha256": p["context"].factor_contract.identity,
        "direct_factor_bank_sha256": p["context"].factor_contract.factors.identity,
        "templates": len(p["context"].bank), "cases": summaries,
        "calibration_null_count": len(p["calibration"].accumulator.null_maxima),
        "calibration_receipt_sha256": p["calibration"].receipt_sha256,
        "complete_detector_stages": ["calibration", "retention", "matched_off",
            "single_adjacent_off", "receiver_frame", "rank", "clustering"],
        "legacy_factor_basis_constructed": False,
        "legacy_detector_module_modified": False,
        "fresh_disjoint_calibration_and_evaluation_source_identities": True,
        "engineering_control_gate_passed": False,
        "engineering_control_gate_failure": "matched_on_off has 13 unassociated final members",
        "all_triggers_vetoes_and_limits_retained_in": "reports.json.gz",
        "complete_reports_gzip_sha256": hashlib.sha256((OUT / "reports.json.gz").read_bytes()).hexdigest(),
        "cross_window_calibration_transfer_qualified": False,
        "physical_model_qualified": False, "source_pointing_resolved": False,
        "scientific_candidate_selection_authorized": False,
        "telescope_values_opened": False, "telescope_requests": 0}
    write("result.json", result)
    print(json.dumps({"status": result["status"], "cases": {
        name: {key: value for key, value in item.items()
               if key in ("recovered", "all_on_member_count", "all_off_member_count",
                          "all_final_member_count", "cluster_count")}
        for name, item in summaries.items()},
        "engineering_control_gate_passed": False}, indent=2))


if __name__ == "__main__":
    main()
