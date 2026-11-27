#!/usr/bin/env python3
"""Prospectively locked Milky Way Gaia DR3 NSS, HGCA & Kervella dark-companion analyzer (Spor N9)."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import betaincinv

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n9_20261127_gaia_dr3_dark_companions"
INP = ROOT / "inputs_n9_20261127"
RES = WS / "results"

# Locked Prospective Thresholds (Chandrasekhar / 25-yr dynamical acceleration / astrometric wobble)
D1_MIN_FM_MSUN = 0.5
D1_MIN_M2_PROXY_MSUN = 1.4
D2_MIN_HGCA_CHI2 = 50.0
D2_MIN_KERVELLA_SNR = 10.0
D3_MIN_RUWE = 2.5
D3_MIN_GMAG_SAT = 5.0

INJECTION_SEED = 20261129


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def jeffreys_f95(n_eff: float) -> float:
    return float(betaincinv(0.5, float(n_eff) + 0.5, 0.95)) if n_eff > 0 else 1.0


def uniform_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / (float(n_eff) + 1.0))) if n_eff > 0 else 1.0


def clopper_pearson_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / float(n_eff))) if n_eff > 0 else 1.0


def eval_target(fm: float, m2_est: float, hgca_chi2: float, kerv_snr: float, ruwe: float, gmag: float, has_acc: bool) -> dict[str, Any]:
    d1 = (math.isfinite(fm) and fm >= D1_MIN_FM_MSUN) or (math.isfinite(m2_est) and m2_est >= D1_MIN_M2_PROXY_MSUN)
    d2 = (math.isfinite(hgca_chi2) and hgca_chi2 >= D2_MIN_HGCA_CHI2) or (math.isfinite(kerv_snr) and kerv_snr >= D2_MIN_KERVELLA_SNR)
    ruwe_ok = math.isfinite(ruwe) and ruwe >= D3_MIN_RUWE and (not math.isfinite(gmag) or gmag >= D3_MIN_GMAG_SAT)
    d3 = ruwe_ok or has_acc
    reasons = []
    if d1:
        reasons.append("N9_DARK_MASS_ORBIT")
    if d2:
        reasons.append("N9_PMA_25YR_ACCELERATION")
    if d3:
        reasons.append("N9_EXTREME_RUWE_OR_ACCEL")
    return {"trig_d1": d1, "trig_d2": d2, "trig_d3": d3, "triggered": bool(reasons), "reasons": "|".join(reasons)}


def run_injections() -> dict[str, Any]:
    rng = np.random.default_rng(INJECTION_SEED)
    # 400 synthetic dark-mass orbits (f(M) levels)
    g1: dict[str, Any] = {}
    for fm0 in (0.1, 0.5, 2.0, 6.0):
        rec = 0
        for _ in range(100):
            fm = float(fm0 + rng.normal(0.0, 0.08 * fm0))
            if eval_target(fm, float("nan"), float("nan"), float("nan"), 1.0, 11.0, False)["trig_d1"]:
                rec += 1
        g1[str(fm0)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    # 400 synthetic 25-yr PMa dark pulls (snrPMa levels)
    g2: dict[str, Any] = {}
    for s0 in (3.0, 10.0, 25.0, 60.0):
        rec = 0
        for _ in range(100):
            sn = float(s0 + rng.normal(0.0, 1.2))
            if eval_target(float("nan"), float("nan"), float("nan"), sn, 1.0, 9.0, False)["trig_d2"]:
                rec += 1
        g2[str(int(s0))] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    # 400 synthetic astrometric wobble anomalies (RUWE levels)
    g3: dict[str, Any] = {}
    for rw0 in (1.5, 2.5, 5.0, 12.0):
        rec = 0
        for _ in range(100):
            rw = float(rw0 + rng.normal(0.0, 0.2))
            if eval_target(float("nan"), float("nan"), float("nan"), float("nan"), rw, 10.5, False)["trig_d3"]:
                rec += 1
        g3[str(rw0)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    c1 = sum(g1[k]["recovered"] for k in ("0.5", "2.0", "6.0")) / 300.0
    c2 = sum(g2[k]["recovered"] for k in ("25", "60")) / 200.0
    c3 = sum(g3[k]["recovered"] for k in ("2.5", "5.0", "12.0")) / 300.0
    return {
        "trials_total": 1200,
        "gate_d1_dark_mass": g1,
        "gate_d2_25yr_pma": g2,
        "gate_d3_ruwe_accel": g3,
        "completeness_d1_ge_0p5msun": round(c1, 4),
        "completeness_d2_snr_ge_25": round(c2, 4),
        "completeness_d3_ruwe_ge_2p5": round(c3, 4),
        "completeness_mean_astrometry": round((c1 + c2 + c3) / 3.0, 4),
    }


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    targets = list(csv.DictReader((INP / "milky_way_astrometry_targets.csv").open("r", encoding="utf-8")))
    tbooc = {r["Source"]: r for r in csv.DictReader((INP / "gaia_nss/nss_tbooc.csv").open("r", encoding="utf-8"))}
    tbosb1 = {r["Source"]: r for r in csv.DictReader((INP / "gaia_nss/nss_tbosb1.csv").open("r", encoding="utf-8"))}
    acc7 = {r["Source"]: r for r in csv.DictReader((INP / "gaia_nss/nss_acc7.csv").open("r", encoding="utf-8"))}
    acc9 = {r["Source"]: r for r in csv.DictReader((INP / "gaia_nss/nss_acc9.csv").open("r", encoding="utf-8"))}
    hgca = {r["Gaia"]: r for r in csv.DictReader((INP / "hgca/brandt_hgca.csv").open("r", encoding="utf-8"))}
    kerv = {r["GaiaEDR3"]: r for r in csv.DictReader((INP / "kervella/kervella_pma.csv").open("r", encoding="utf-8"))}

    cat_rows: list[dict[str, Any]] = []
    trig_rows: list[dict[str, Any]] = []

    for r in targets:
        sid = r["source_id"].strip()
        ruwe = _f(r.get("ruwe"))
        gmag = _f(r.get("phot_g_mean_mag"))
        plx = _f(r.get("parallax"))
        nss_flag = int(_f(r.get("non_single_star"), 0.0) or 0)
        ipd_m = int(_f(r.get("ipd_frac_multi_peak"), 0.0) or 0)

        sb = tbosb1.get(sid, {})
        orb = tbooc.get(sid, {})
        hg = hgca.get(sid, {})
        kv = kerv.get(sid, {})
        has_acc = (sid in acc7) or (sid in acc9)

        # Spectroscopic SB1 mass function f(M) = 1.0361e-7 * (1-e^2)^1.5 * K1^3 * P_day
        fm = float("nan")
        if sb:
            k1 = _f(sb.get("K1"))
            per = _f(sb.get("Per"))
            ecc = _f(sb.get("ecc"), 0.0)
            if math.isfinite(k1) and math.isfinite(per) and per > 0:
                fm = 1.0361e-7 * ((max(0.0, 1.0 - ecc ** 2)) ** 1.5) * (abs(k1) ** 3) * per

        # Astrometric total binary mass proxy from Thiele-Innes / semimajor photocenter axis (assuming q<<1 => M2 ~ M_tot ~ a_AU^3 / P_yr^2)
        m2_ast_proxy = float("nan")
        per_o = _f(orb.get("Per"))
        plx_o = _f(orb.get("Plx"), plx)
        amaj = _f(orb.get("amaj"))
        if orb and math.isfinite(per_o) and per_o > 0 and math.isfinite(plx_o) and plx_o > 0:
            if not math.isfinite(amaj):
                # Fallback from Thiele-Innes A,B,F,G (mas)
                a_ti, b_ti, f_ti, g_ti = _f(orb.get("ATI"), 0.0), _f(orb.get("BTI"), 0.0), _f(orb.get("FTI"), 0.0), _f(orb.get("GTI"), 0.0)
                u = 0.5 * (a_ti ** 2 + b_ti ** 2 + f_ti ** 2 + g_ti ** 2)
                v = a_ti * g_ti - b_ti * f_ti
                amaj = math.sqrt(max(0.0, u + math.sqrt(max(0.0, u ** 2 - v ** 2))))
            if math.isfinite(amaj) and amaj > 0:
                p_yr = per_o / 365.25
                a_au = amaj / plx_o
                m2_ast_proxy = (a_au ** 3) / (p_yr ** 2)

        hgca_chi2 = _f(hg.get("chi2"))
        kerv_snr = max(_f(kv.get("snrPMaH2EG3b"), float("nan")), _f(kv.get("snrPMaH2EG3a"), float("nan")))
        if not math.isfinite(kerv_snr):
            kerv_snr = _f(kv.get("snrPMaHG1"))
        m2_10au_mj = _f(kv.get("M210au"))

        ev = eval_target(fm, m2_ast_proxy, hgca_chi2, kerv_snr, ruwe, gmag, has_acc)
        row = {
            "star": r["star"],
            "common_name": r["common_name"],
            "is_bh_benchmark": r["is_bh_benchmark"],
            "within_10pc": r["within_10pc"],
            "n_exoplanets": r["n_exoplanets"],
            "dist_pc": r["dist_pc"],
            "source_id": sid,
            "phot_g_mean_mag": round(gmag, 4) if math.isfinite(gmag) else "",
            "bp_rp": r.get("bp_rp", ""),
            "parallax": round(plx, 4) if math.isfinite(plx) else "",
            "ruwe": round(ruwe, 4) if math.isfinite(ruwe) else "",
            "ipd_frac_multi_peak": ipd_m,
            "non_single_star": nss_flag,
            "in_tbooc": sid in tbooc,
            "in_tbosb1": sid in tbosb1,
            "in_acc7_acc9": has_acc,
            "in_hgca": sid in hgca,
            "in_kervella": sid in kerv,
            "nss_period_d": round(per_o if math.isfinite(per_o) else _f(sb.get("Per")), 3) if (math.isfinite(per_o) or sb) else "",
            "fm_msun": round(fm, 5) if math.isfinite(fm) else "",
            "m2_ast_proxy_msun": round(m2_ast_proxy, 4) if math.isfinite(m2_ast_proxy) else "",
            "hgca_chi2": round(hgca_chi2, 2) if math.isfinite(hgca_chi2) else "",
            "kervella_snr": round(kerv_snr, 2) if math.isfinite(kerv_snr) else "",
            "kervella_m2_10au_mjup": round(m2_10au_mj, 2) if math.isfinite(m2_10au_mj) else "",
            **ev,
        }
        cat_rows.append(row)
        if ev["triggered"]:
            trig_rows.append(row)

    with (RES / "N9_MILKY_WAY_ASTROMETRY_CATALOG.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cat_rows[0].keys()))
        w.writeheader()
        w.writerows(cat_rows)

    with (RES / "N9_STAGE2_TRIGGERS.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cat_rows[0].keys()))
        w.writeheader()
        w.writerows(trig_rows)

    mw = [r for r in cat_rows if r["is_bh_benchmark"] == "False"]
    n_mw = len(mw)
    n_gaia = sum(1 for r in mw if r["source_id"] != "")
    n_25yr = sum(1 for r in mw if r["in_hgca"] or r["in_kervella"])
    n_10pc = sum(1 for r in mw if r["within_10pc"] == "True")
    n_hosts = sum(1 for r in mw if int(r["n_exoplanets"] or 0) > 0)

    inj = run_injections()
    eff = inj["completeness_mean_astrometry"]

    def lim(n_val: float) -> dict[str, float]:
        return {
            "n_eff": round(float(n_val), 4),
            "jeffreys_f95_pct": round(jeffreys_f95(n_val) * 100.0, 4),
            "uniform_f95_pct": round(uniform_f95(n_val) * 100.0, 4),
            "clopper_pearson_f95_pct": round(clopper_pearson_f95(n_val) * 100.0, 4),
        }

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "analyzer_sha256": sha256_file(Path(__file__)),
        "pure_milky_way_stars_total": n_mw,
        "bh_benchmarks_total": sum(1 for r in cat_rows if r["is_bh_benchmark"] == "True"),
        "gaia_dr3_matched": n_gaia,
        "baseline_25yr_hgca_kervella_matched": n_25yr,
        "gaia_nss_orbit_or_acc_matched": sum(1 for r in mw if r["in_tbooc"] or r["in_tbosb1"] or r["in_acc7_acc9"]),
        "bh_benchmarks_recovered_d1": sum(1 for r in trig_rows if r["is_bh_benchmark"] == "True" and r["trig_d1"]),
        "stage2_triggers_total": len(trig_rows),
        "stage2_triggers_science_mw": sum(1 for r in trig_rows if r["is_bh_benchmark"] == "False"),
        "stage2_gate_counts": {
            "N9_DARK_MASS_ORBIT": sum(1 for r in trig_rows if r["trig_d1"]),
            "N9_PMA_25YR_ACCELERATION": sum(1 for r in trig_rows if r["trig_d2"]),
            "N9_EXTREME_RUWE_OR_ACCEL": sum(1 for r in trig_rows if r["trig_d3"]),
        },
        "injections": inj,
        "bayesian_limits_zero_eti": {
            "all_pure_mw_996_raw": lim(n_mw),
            "all_pure_mw_eff": lim(n_mw * eff),
            "gaia_dr3_matched": lim(n_gaia),
            "pma_25yr_baseline": lim(n_25yr),
            "within_10pc": lim(n_10pc),
            "exoplanet_hosts": lim(n_hosts),
        },
    }
    (RES / "N9_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
