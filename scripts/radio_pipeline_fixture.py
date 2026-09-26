"""Deterministic raw-native engineering panel. Truth never enters the detector."""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as transfer
from seti_repeater import pipeline_radio as radio

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT/"config/radio_pipeline_engineering_20260926.json"


def context(config, **overrides):
    scans = [{"epoch": e+1, "kind": kind, "label": f"epoch{e+1}_{kind}",
              "expected_header": {"dataset_shape": [16, 1, config["native_channels"]]},
              "source_domain": "synthetic"}
             for e in range(3) for kind in ("on", "off")]
    labels = [core.FactorLabel(s, scan["label"], r) for s, scan in enumerate(scans) for r in range(16)]
    times = np.array([66000+(s*400+r+.5)/86400 for s in range(6) for r in range(16)], dtype="<f8")
    base = np.array([1+(s-2.5)*15e-9+(r-7.5)*.3e-9 for s in range(6) for r in range(16)], dtype="<f8")
    orbit = np.column_stack([np.sin(np.arange(96)/10)*5e-9, np.cos(np.arange(96)/13)*2e-9])
    basis = core.make_factor_basis_from_arrays(times, labels, base, orbit, expected_sha256=None)
    parent = [{"template_index": 0, "coefficient_x": 0., "coefficient_y": 0.},
              {"template_index": 1, "coefficient_x": 1., "coefficient_y": 0.}]
    grid = core.make_proxy_carrier_grid(config["center_mhz"], config["channel_width_hz"],
                                      config["score_half_bins"], config["support_guard_bins"])
    return radio.Context(scans=scans, basis=basis, parent_bank=parent, grid=grid,
        window="radio-synthetic-integration-20260926",
        **({"maximum_records": config["maximum_records_per_role"],
            "memory_limit_bytes": config["modelled_array_limit_bytes"]} | overrides))


def make_sources(c, config, seed, case, *, calibration_comb=False):
    rng = np.random.default_rng(seed)
    n = config["native_channels"]
    geometry = core.NativeFrequencyGeometry(config["center_mhz"]*1e6-n//2, config["channel_width_hz"], n)
    sources, raw_rows = {}, {}
    for scan in c.scans:
        label = scan["label"]
        raw = np.asarray(100+rng.standard_normal((16, n)), dtype="<f4")
        if calibration_comb:
            comb = config["calibration_only_comb"]
            raw[:, ::comb["spacing_native_channels"]] += np.float32(comb["raw_addition_per_channel"])
        if scan["epoch"]-1 in case[scan["kind"]+"_epochs"]:
            f = core.factor_table_for_scan(c.table, c.basis, label)[config["truth_template"]]
            centers = np.rint((c.grid.score_hz[config["truth_score_index"]]*f-geometry.raw_zero_hz)
                              / geometry.channel_width_hz).astype(np.int64)
            half = case["width"]//2
            for row, center in enumerate(centers):
                raw[row, center-half:center+half+1] += np.float32(case["raw_addition_per_channel"])
        raw_rows[label] = raw
        sources[label] = transfer.normalize_synthetic_rows(lambda r: raw[r], geometry, 16,
            input_orientation="ascending", scope={"kind": "synthetic", "fixture_seed": seed,
                "scan": label, "case": case["name"], "calibration_comb": calibration_comb,
                "placement": "raw-powers-before-normalization"})
    return sources, raw_rows


def account_truth(report, c, truth):
    """Post-detection accounting; never changes member decisions or clusters."""
    records = report["detector"]["retained"]["on"]
    decisions = {d["record_id"]: d for d in report["detector"]["decisions"]}
    factors = core.factor_matrix_for_kind(c.table, c.basis, c.scans, "on")
    target = c.grid.score_hz[truth["score_index"]]*factors[truth["template_index"]]
    eligible = []
    for r in records:
        track = r["proxy_carrier_hz"]*factors[r["template_index"]]
        if (set(r["active_epochs_zero_based"]).issubset(truth["active_epochs"])
                and float(np.max(np.abs(track-target))) <= 2*c.grid.channel_width_hz):
            eligible.append(r["record_id"])
    physical = [r for r in eligible if decisions[r]["passes_evaluated_physical_vetoes"]]
    final = [r for r in physical if decisions[r]["meets_diagnostic_rank_cut"]]
    all_final = [r for r, d in decisions.items() if d["passes_evaluated_physical_vetoes"] and d["meets_diagnostic_rank_cut"]]
    associated_clusters = [g["cluster_sha256"] for g in report["clusters"] if set(g["member_ids"]) & set(eligible)]
    unassociated_final_clusters = [g["cluster_sha256"] for g in report["clusters"]
                                  if g["diagnostic_final_ids"] and g["cluster_sha256"] not in associated_clusters]
    return {"truth": truth, "retained_associated_ids": eligible, "physical_associated_ids": physical,
            "final_associated_ids": final, "unassociated_final_ids": sorted(set(all_final)-set(final)),
            "associated_cluster_ids": associated_clusters, "unassociated_final_cluster_ids": unassociated_final_clusters,
            "recovered": bool(final), "all_final_member_count": len(all_final),
            "all_on_member_count": len(records), "all_off_member_count": len(report["detector"]["retained"]["off"]),
            "cluster_count": len(report["clusters"])}


@lru_cache(maxsize=1)
def panel():
    cfg = json.loads(DESIGN.read_text())
    if cfg["primary"] != radio.METHOD["primary"] or cfg["source_domain"] != "synthetic":
        raise ValueError("engineering design changed domain or primary")
    c = context(cfg)
    calibration_sources, raw = make_sources(c, cfg, cfg["calibration_seed"], cfg["cases"][0], calibration_comb=True)
    baseline = radio.NativeRun.from_synthetic(c, calibration_sources)
    store = baseline.build_store()
    shifts = core.make_scramble_shift_table(cfg["scramble_count"], 3, c.grid.score_bin_count,
        seed=cfg["scramble_seed"], minimum_shift_bins=cfg["minimum_shift_bins"])
    calibration = baseline.calibrate(store, shifts=shifts, minimum_shift_bins=cfg["minimum_shift_bins"],
        reference_floor=cfg["reference_floor"], quantile=cfg["quantile"], rank_ceiling=cfg["rank_ceiling"])
    reports, outcomes, evaluation_runs = {}, {}, {}
    # Every predeclared case completes even if its recovery/control outcome fails.
    for case in cfg["cases"]:
        sources, _ = make_sources(c, cfg, cfg["evaluation_seed"], case)
        run = radio.NativeRun.from_synthetic(c, sources)
        values = run.build_store()
        result = run.execute(values, calibration)
        reports[case["name"]] = result
        evaluation_runs[case["name"]] = (run, values)
        truth = {"template_index": cfg["truth_template"], "score_index": cfg["truth_score_index"],
                 "active_epochs": case["on_epochs"]}
        outcomes[case["name"]] = account_truth(result, c, truth)
    return dict(config=cfg, context=c, calibration=calibration, calibration_run=baseline,
                calibration_store=store, calibration_raw=raw, reports=reports, outcomes=outcomes,
                evaluation_runs=evaluation_runs)


if __name__ == "__main__":
    result = panel()
    print(json.dumps({name: {k: v for k, v in o.items() if k.endswith("count") or k == "recovered"}
                      for name, o in result["outcomes"].items()}, indent=2))
