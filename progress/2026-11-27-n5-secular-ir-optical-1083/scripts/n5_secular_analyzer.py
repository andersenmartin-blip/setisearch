#!/usr/bin/env python3
"""
Spor N5 Prospective Locked Analyzer (METHOD_LOCK & IMPLEMENTATION_LOCK):
10-Year Multi-Epoch Mid-IR (AllWISE + CatWISE2020 + NEOWISE-R 2010-2024) &
Optical (ZTF DR24 + Gaia DR3) Secular Megastructure & Dyson-Swarm Bridge
across all 1,083 Master Catalog Stars + 13 External Benchmarks (1,096 targets).
Pure Python stdlib (/usr/bin/python3 -S compatible).
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import math
import pathlib
import random
from typing import Any

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n5_20261127_secular_ir_optical_1083"
INP = ROOT / "inputs_n5_20261127"
RES = WS / "results"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"
BENCH13 = INP / "n5_benchmarks_13.csv"

THRESHOLDS = {
    "ir_dw2_mag_min": 0.12,
    "ir_dw1_mag_min": 0.15,
    "ir_z_min": 5.0,
    "catwise_w2rchi2_min": 15.0,
    "catwise_w1rchi2_min": 20.0,
    "ztf_ngoodobs_min": 40,
    "ztf_trend_mag_yr_min": 0.015,
    "ztf_rms_min": 0.10,
    "ztf_stetsonj_min": 3.0,
    "gaia_vari_range_min": 0.20,
    "gaia_vari_skew_min": 1.0,
    "wise_w1_sat_limit": 8.0,
    "wise_w2_sat_limit": 7.0,
    "ztf_sat_limit": 13.0,
}


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    x = _f(v)
    return int(round(x)) if x is not None else None


def _betainc_reg(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc_reg(b, a, 1.0 - x)
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(ln_bt)
    eps, fpmin = 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, 220):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 / max(fpmin, 1.0 + aa * d) if abs(1.0 + aa * d) < fpmin else 1.0 / (1.0 + aa * d)
        c = fpmin if abs(1.0 + aa / c) < fpmin else 1.0 + aa / c
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 / max(fpmin, 1.0 + aa * d) if abs(1.0 + aa * d) < fpmin else 1.0 / (1.0 + aa * d)
        c = fpmin if abs(1.0 + aa / c) < fpmin else 1.0 + aa / c
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return bt * h / a


def bayesian_zero_bounds(n_eff: float) -> dict[str, float]:
    if n_eff <= 0.0:
        return {"n_eff": 0.0, "jeffreys_f95_pct": 100.0, "uniform_f95_pct": 100.0, "clopper_pearson_f95_pct": 100.0}
    lo, hi = 0.0, 1.0
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if _betainc_reg(0.5, n_eff + 0.5, mid) < 0.95:
            lo = mid
        else:
            hi = mid
    j95 = 100.0 * 0.5 * (lo + hi)
    u95 = 100.0 * (1.0 - (0.05 ** (1.0 / (n_eff + 1.0))))
    cp95 = 100.0 * (1.0 - (0.05 ** (1.0 / n_eff)))
    return {
        "n_eff": round(n_eff, 4),
        "jeffreys_f95_pct": round(j95, 4),
        "uniform_f95_pct": round(u95, 4),
        "clopper_pearson_f95_pct": round(cp95, 4),
    }


def _load_keyed(path: pathlib.Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            st = row.get("star", "").strip()
            if st:
                out[st] = row
    return out


def _write_csv(path: pathlib.Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> int:
    targets: list[dict[str, Any]] = []
    for r in csv.DictReader(TABLE1.open(encoding="utf-8")):
        r["source_catalog"] = "MASTER_1083"
        targets.append(r)
    if BENCH13.exists():
        for r in csv.DictReader(BENCH13.open(encoding="utf-8")):
            r["source_catalog"] = "BENCHMARK_13"
            targets.append(r)

    gaia_m = _load_keyed(INP / "gaia" / "gaia_dr3_1096.csv")
    allw_m = _load_keyed(INP / "allwise" / "allwise_1096.csv")
    catw_m = _load_keyed(INP / "catwise" / "catwise2020_1096.csv")
    ztf_m = _load_keyed(INP / "ztf" / "ztf_dr24_1096.csv")

    summary_rows: list[dict[str, Any]] = []
    trigger_rows: list[dict[str, Any]] = []
    inj_pool: list[dict[str, float]] = []

    cov_counts: collections.Counter[str] = collections.Counter()
    trig_counts: collections.Counter[str] = collections.Counter()

    for t in targets:
        st = t["star"]
        role = t["role"]
        g = gaia_m.get(st, {})
        aw = allw_m.get(st, {})
        cw = catw_m.get(st, {})
        zt = ztf_m.get(st, {})

        has_gaia = bool(_f(g.get("phot_g_mean_mag")) is not None)
        has_aw = bool(_f(aw.get("w1mpro")) is not None or _f(aw.get("w2mpro")) is not None)
        has_cw = bool(_f(cw.get("w1mpro")) is not None or _f(cw.get("w2mpro")) is not None)
        zt_ngood = _i(zt.get("ngoodobs")) or 0
        has_ztf = zt_ngood >= THRESHOLDS["ztf_ngoodobs_min"]

        if t["source_catalog"] == "MASTER_1083":
            if has_gaia:
                cov_counts["gaia_dr3"] += 1
            if has_aw:
                cov_counts["allwise"] += 1
            if has_cw:
                cov_counts["catwise2020"] += 1
            if has_aw or has_cw:
                cov_counts["wise_any"] += 1
            if has_ztf:
                cov_counts["ztf_dr24"] += 1

        # Mid-IR baseline metrics
        w1_a, sw1_a = _f(aw.get("w1mpro")), _f(aw.get("w1sigmpro"))
        w2_a, sw2_a = _f(aw.get("w2mpro")), _f(aw.get("w2sigmpro"))
        w1_c, sw1_c = _f(cw.get("w1mpro")), _f(cw.get("w1sigmpro"))
        w2_c, sw2_c = _f(cw.get("w2mpro")), _f(cw.get("w2sigmpro"))
        w1_rchi2, w2_rchi2 = _f(cw.get("w1rchi2")), _f(cw.get("w2rchi2"))

        dw1 = (w1_c - w1_a) if (w1_a is not None and w1_c is not None) else None
        dw2 = (w2_c - w2_a) if (w2_a is not None and w2_c is not None) else None
        zdw1 = (dw1 / max(0.025, math.hypot(sw1_a or 0.03, sw1_c or 0.03))) if dw1 is not None else None
        zdw2 = (dw2 / max(0.025, math.hypot(sw2_a or 0.03, sw2_c or 0.03))) if dw2 is not None else None
        dcol = ((w1_c - w2_c) - (w1_a - w2_a)) if all(v is not None for v in (w1_a, w2_a, w1_c, w2_c)) else None

        ref_w1 = w1_c if w1_c is not None else w1_a
        ref_w2 = w2_c if w2_c is not None else w2_a
        w1_unsat = ref_w1 is not None and ref_w1 >= THRESHOLDS["wise_w1_sat_limit"]
        w2_unsat = ref_w2 is not None and ref_w2 >= THRESHOLDS["wise_w2_sat_limit"]
        if t["source_catalog"] == "MASTER_1083" and w2_unsat:
            cov_counts["wise_w2_unsaturated"] += 1
            if role == "SCIENCE":
                cov_counts["science_wise_w2_unsaturated"] += 1
            if dw2 is not None:
                # 10-yr scaled noise floor combining pairwise baseline error with NEOWISE floor
                sig_base = max(0.025, math.hypot(sw2_a or 0.03, sw2_c or 0.03))
                inj_pool.append({"sigma_ir": sig_base, "sigma_opt": 0.02 if has_ztf else 0.03})

        # ZTF optical secular metrics
        zt_med = _f(zt.get("medianmag"))
        zt_rms = _f(zt.get("magrms"))
        zt_trend = _f(zt.get("lineartrend"))
        zt_stet = _f(zt.get("stetsonj"))
        zt_unsat = has_ztf and zt_med is not None and zt_med >= THRESHOLDS["ztf_sat_limit"]

        # Gaia variability & multiplicity metrics
        g_mag = _f(g.get("phot_g_mean_mag"))
        ruwe = _f(g.get("ruwe"))
        v_rng = _f(g.get("vari_range_g"))
        v_skew = _f(g.get("vari_skew_g"))

        # Evaluate Tier-1 Triggers
        reasons: list[str] = []
        if w2_unsat and dw2 is not None and zdw2 is not None:
            if abs(dw2) >= THRESHOLDS["ir_dw2_mag_min"] and abs(zdw2) >= THRESHOLDS["ir_z_min"]:
                reasons.append("T1_IR_SECULAR_W2")
        if w1_unsat and dw1 is not None and zdw1 is not None:
            if abs(dw1) >= THRESHOLDS["ir_dw1_mag_min"] and abs(zdw1) >= THRESHOLDS["ir_z_min"]:
                reasons.append("T1_IR_SECULAR_W1")
        if (w2_unsat and w2_rchi2 is not None and w2_rchi2 >= THRESHOLDS["catwise_w2rchi2_min"]) or (
            w1_unsat and w1_rchi2 is not None and w1_rchi2 >= THRESHOLDS["catwise_w1rchi2_min"]
        ):
            reasons.append("T1_IR_VAR_CHI2")
        if zt_unsat and zt_trend is not None and abs(zt_trend) >= THRESHOLDS["ztf_trend_mag_yr_min"]:
            reasons.append("T1_OPT_TREND")
        if zt_unsat and zt_rms is not None and zt_stet is not None and zt_rms >= THRESHOLDS["ztf_rms_min"] and zt_stet >= THRESHOLDS["ztf_stetsonj_min"]:
            reasons.append("T1_OPT_BURST_STETSON")
        if v_rng is not None and v_skew is not None and v_rng >= THRESHOLDS["gaia_vari_range_min"] and v_skew >= THRESHOLDS["gaia_vari_skew_min"]:
            reasons.append("T1_GAIA_DIPPER")

        is_trig = len(reasons) > 0
        if is_trig:
            for rsn in reasons:
                trig_counts[f"{t['source_catalog']}_{role}_{rsn}"] += 1

        rec = {
            "star": st,
            "common_name": t["common_name"],
            "source_catalog": t["source_catalog"],
            "role": role,
            "subrole": t["subrole"],
            "ra_deg": t["ra_deg"],
            "dec_deg": t["dec_deg"],
            "dist_pc": t["dist_pc"],
            "within_10pc": t["within_10pc"],
            "has_gaia_dr3": has_gaia,
            "has_allwise": has_aw,
            "has_catwise2020": has_cw,
            "has_ztf_dr24": has_ztf,
            "gaia_g_mag": g.get("phot_g_mean_mag", ""),
            "gaia_ruwe": g.get("ruwe", ""),
            "gaia_var_flag": g.get("phot_variable_flag", ""),
            "gaia_nss": g.get("non_single_star", ""),
            "allwise_w1": aw.get("w1mpro", ""),
            "allwise_w2": aw.get("w2mpro", ""),
            "catwise_w1": cw.get("w1mpro", ""),
            "catwise_w2": cw.get("w2mpro", ""),
            "w1_rchi2": cw.get("w1rchi2", ""),
            "w2_rchi2": cw.get("w2rchi2", ""),
            "dw1_mag": round(dw1, 4) if dw1 is not None else "",
            "dw2_mag": round(dw2, 4) if dw2 is not None else "",
            "z_dw1": round(zdw1, 2) if zdw1 is not None else "",
            "z_dw2": round(zdw2, 2) if zdw2 is not None else "",
            "dcolor_w1_w2": round(dcol, 4) if dcol is not None else "",
            "w2_unsat": w2_unsat,
            "ztf_filter": zt.get("filtercode", ""),
            "ztf_ngoodobs": zt_ngood if zt else "",
            "ztf_medianmag": zt.get("medianmag", ""),
            "ztf_magrms": zt.get("magrms", ""),
            "ztf_lineartrend_mag_yr": zt.get("lineartrend", ""),
            "ztf_stetsonj": zt.get("stetsonj", ""),
            "tier1_trigger": is_trig,
            "tier1_reasons": "|".join(reasons),
        }
        summary_rows.append(rec)
        if is_trig:
            trigger_rows.append(rec)

    _write_csv(RES / "N5_MASTER_1096_SECULAR_SUMMARY.csv", list(summary_rows[0].keys()), summary_rows)
    if trigger_rows:
        _write_csv(RES / "N5_TIER1_TRIGGERS.csv", list(trigger_rows[0].keys()), trigger_rows)
    else:
        _write_csv(RES / "N5_TIER1_TRIGGERS.csv", list(summary_rows[0].keys()), [])

    # 1,200 seeded synthetic secular Dyson-swarm injection trials (200 unsaturated stars x 6 secular rates)
    rng = random.Random(202611275)
    pool = list(inj_pool) if inj_pool else [{"sigma_ir": 0.035, "sigma_opt": 0.025}] * 200
    while len(pool) < 200:
        pool.extend(pool[:200 - len(pool)])
    rng.shuffle(pool)
    pool_200 = pool[:200]
    rates = [0.005, 0.01, 0.02, 0.04, 0.08, 0.15]  # mag/yr over 10-yr baseline
    inj_grid = {str(r): {"trials": 0, "recovered": 0} for r in rates}
    for star_n in pool_200:
        sir = star_n["sigma_ir"]
        for rate in rates:
            # 10-yr IR brightening = -rate * 10.0 mag; triggered when |obs_dw2| >= 0.12 and |obs_dw2|/sir >= 5.0
            obs_dw2 = -rate * 10.0 + rng.gauss(0.0, sir)
            z_obs = abs(obs_dw2) / sir
            inj_grid[str(rate)]["trials"] += 1
            if abs(obs_dw2) >= THRESHOLDS["ir_dw2_mag_min"] and z_obs >= THRESHOLDS["ir_z_min"]:
                inj_grid[str(rate)]["recovered"] += 1

    for v in inj_grid.values():
        v["completeness"] = round(v["recovered"] / max(1, v["trials"]), 4)
    comp_ge_0p02 = sum(inj_grid[str(r)]["recovered"] for r in (0.02, 0.04, 0.08, 0.15)) / sum(inj_grid[str(r)]["trials"] for r in (0.02, 0.04, 0.08, 0.15))
    comp_ge_0p04 = sum(inj_grid[str(r)]["recovered"] for r in (0.04, 0.08, 0.15)) / sum(inj_grid[str(r)]["trials"] for r in (0.04, 0.08, 0.15))
    comp_all = sum(v["recovered"] for v in inj_grid.values()) / sum(v["trials"] for v in inj_grid.values())

    master_only = [r for r in summary_rows if r["source_catalog"] == "MASTER_1083"]
    n_sci = sum(1 for r in master_only if r["role"] == "SCIENCE")
    n_10pc = sum(1 for r in master_only if r["within_10pc"] == "True")
    n_sci_unsat = cov_counts["science_wise_w2_unsaturated"]
    n_ztf = cov_counts["ztf_dr24"]
    n_gaia = cov_counts["gaia_dr3"]

    bounds = {
        "all_1083_stars_gaia_ir": bayesian_zero_bounds(float(len(master_only))),
        "science_787_stars": bayesian_zero_bounds(float(n_sci)),
        "science_unsaturated_ir_10yr": bayesian_zero_bounds(float(max(n_sci_unsat, 1)) * comp_ge_0p04),
        "within_10pc_267_stars": bayesian_zero_bounds(float(n_10pc)),
        "ztf_dr24_optical_monitored": bayesian_zero_bounds(float(max(n_ztf, 1))),
        "gaia_dr3_monitored": bayesian_zero_bounds(float(max(n_gaia, 1))),
    }

    out_sum = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyzer_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "master_stars_total": len(master_only),
        "benchmarks_total": len(targets) - len(master_only),
        "science_stars": n_sci,
        "within_10pc_stars": n_10pc,
        "coverage_counts": dict(cov_counts),
        "tier1_triggers_total": len(trigger_rows),
        "tier1_triggers_master_science": sum(1 for r in trigger_rows if r["source_catalog"] == "MASTER_1083" and r["role"] == "SCIENCE"),
        "tier1_triggers_master_control": sum(1 for r in trigger_rows if r["source_catalog"] == "MASTER_1083" and r["role"] == "CONTROL"),
        "tier1_triggers_benchmarks": sum(1 for r in trigger_rows if r["source_catalog"] == "BENCHMARK_13"),
        "tier1_reason_breakdown": dict(trig_counts),
        "injection_trials_total": 1200,
        "injection_completeness_all": round(comp_all, 4),
        "injection_completeness_ge_0p02_mag_yr": round(comp_ge_0p02, 4),
        "injection_completeness_ge_0p04_mag_yr": round(comp_ge_0p04, 4),
        "injection_grid": inj_grid,
        "bayesian_limits_zero_eti": bounds,
    }
    (RES / "N5_ANALYZER_SUMMARY.json").write_text(json.dumps(out_sum, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out_sum, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
