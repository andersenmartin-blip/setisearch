#!/usr/bin/env python3
"""
Spor N2 Locked Prospective Analyzer (METHOD_LOCK & IMPLEMENTATION_LOCK):
- N2A: NASA/JPL SBDB Hyperbolic Objects (e > 1.0) + Non-Grav Asteroids & Dark Comets (A1/A2/A3 -> (A/m)_SRP)
- N2B: Fink Vera Rubin LSST SSOFT (SHG1G2) Photometric/Astrometric Outliers + 1,200 Synthetic Injections
- N2C: Fink Vera Rubin LSST faint_trails Fast Moving Streak Screen
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import math
import pathlib
import random
from typing import Any

# Exact physical constants (SI / IAU)
MU_SUN_KM3_S2 = 1.32712440018e11
AU_KM = 1.495978707e8
AU_M = 1.495978707e11
DAY_S = 86400.0
AU_DAY2_TO_M_S2 = AU_M / (DAY_S ** 2)
P_SOLAR_1AU_PA = 4.56e-6
EPS_J2000_DEG = 23.4392911

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n2_20261127_rubin_iso_sso_and_trails"
INP = ROOT / "inputs_n2_20261127"
RES = WS / "results"

# Prospective locked thresholds
THRESHOLDS = {
    "n2a_iso_vinf_kms_min": 10.0,
    "n2a_nongrav_strong_au_d2": 1e-12,
    "n2a_meter_scale_h_min": 27.0,
    "n2a_high_am_m2_kg": 0.005,
    "n2b_min_obs": 10,
    "n2b_r_boundary_eps": 0.3001,
    "n2b_phot_rms_min": 0.25,
    "n2b_phot_chi2red_min": 100.0,
    "n2b_astrom_std_arcsec_min": 0.08,
    "n2b_astrom_mean_arcsec_min": 0.20,
    "n2c_unlinked_min_reliability": 0.70,
}


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).lower() in ("nan", "null", "none"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _norm_key(s: Any) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().upper().split())


def _betainc_reg(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc_reg(b, a, 1.0 - x)
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(ln_bt)
    max_iter = 200
    eps = 3e-14
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return bt * h / a


def _beta_ppf_zero(alpha_post: float, beta_post: float, q: float = 0.95) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if _betainc_reg(alpha_post, beta_post, mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def bayesian_zero_bounds(n_eff: float) -> dict[str, float]:
    """Exact 95% upper bounds for k=0 detections on effective sample n_eff."""
    if n_eff <= 0.0:
        return {"n_eff": 0.0, "jeffreys_f95_pct": 100.0, "uniform_f95_pct": 100.0, "clopper_pearson_f95_pct": 100.0}
    j95 = 100.0 * _beta_ppf_zero(0.5, n_eff + 0.5, 0.95)
    u95 = 100.0 * (1.0 - (0.05 ** (1.0 / (n_eff + 1.0))))
    cp95 = 100.0 * (1.0 - (0.05 ** (1.0 / n_eff)))
    return {
        "n_eff": round(n_eff, 4),
        "jeffreys_f95_pct": round(j95, 4),
        "uniform_f95_pct": round(u95, 4),
        "clopper_pearson_f95_pct": round(cp95, 4),
    }


def _write_csv(path: pathlib.Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def build_ssoft_lookup(ssoft_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lut: dict[str, dict[str, Any]] = {}
    for r in ssoft_rows:
        for k in ("sso_number", "sso_name", "designation"):
            v = _norm_key(r.get(k))
            if v and v != "NAN":
                lut[v] = r
    return lut


def _match_ssoft(pdes: str, full_name: str, lut: dict[str, dict[str, Any]]) -> str:
    for cand in (_norm_key(pdes), _norm_key(full_name)):
        if cand and cand in lut:
            row = lut[cand]
            return f"{row.get('sso_number','')}|{row.get('sso_name','')}"
    return ""


def _compute_nongrav_metrics(row_dict: dict[str, Any]) -> dict[str, Any]:
    a1 = _f(row_dict.get("A1"))
    a2 = _f(row_dict.get("A2"))
    a3 = _f(row_dict.get("A3"))
    vals = [v for v in (a1, a2, a3) if v is not None]
    max_ag = max((abs(v) for v in vals), default=0.0)
    a_rad = abs(a1) * AU_DAY2_TO_M_S2 if a1 is not None else 0.0
    a_tot = math.sqrt(sum(v * v for v in vals)) * AU_DAY2_TO_M_S2 if vals else 0.0
    am_ref_a = a_rad if a1 is not None else a_tot
    am_srp = am_ref_a / P_SOLAR_1AU_PA if am_ref_a > 0.0 else 0.0
    h_mag = _f(row_dict.get("H"))
    d_est = (1329000.0 / math.sqrt(0.14)) * (10.0 ** (-0.2 * h_mag)) if h_mag is not None else None
    am_rock = (3.0 / (2.0 * 2500.0 * d_est)) if (d_est and d_est > 0.0) else None
    ratio_am = (am_srp / am_rock) if (am_rock and am_rock > 0.0) else None
    return {
        "a1": a1,
        "a2": a2,
        "a3": a3,
        "max_ag": max_ag,
        "a_rad_1au_ms2": a_rad,
        "a_tot_1au_ms2": a_tot,
        "am_srp_m2_kg": am_srp,
        "d_est_m": d_est,
        "am_rock_m2_kg": am_rock,
        "srp_ratio_am_to_rock": ratio_am,
    }


def _classify_nongrav(orbit_class: str, full_name: str, e_val: float | None, i_val: float | None, h_mag: float | None, max_ag: float, am_srp: float) -> str:
    fn = str(full_name or "").strip()
    oc = str(orbit_class or "").strip().upper()
    if max_ag < THRESHOLDS["n2a_nongrav_strong_au_d2"]:
        return "YARKOVSKY_THERMAL_DRIFT"
    if oc in ("HYP", "JFC", "HTC", "COM", "ETC", "CTc") or fn.startswith(("C/", "P/", "D/")):
        return "ACTIVE_COMET_OUTGASSING"
    if h_mag is not None and h_mag >= THRESHOLDS["n2a_meter_scale_h_min"]:
        if am_srp > THRESHOLDS["n2a_high_am_m2_kg"] and e_val is not None and i_val is not None and e_val < 0.2 and i_val < 10.0:
            return "HIGH_AM_SRP_OR_ARTIFICIAL_DEBRIS_CANDIDATE"
        return "METER_SCALE_SRP_OR_MINIMOON"
    return "DARK_COMET_OR_ACTIVE_ASTEROID_ANOMALY"


def run_n2a(ssoft_lut: dict[str, dict[str, Any]]) -> dict[str, Any]:
    hyp_raw = json.loads((INP / "sbdb" / "jpl_hyperbolic_e_gt_1.json").read_text(encoding="utf-8"))
    ng_raw = json.loads((INP / "sbdb" / "jpl_nongrav_asteroids.json").read_text(encoding="utf-8"))

    hf = hyp_raw["fields"]
    hyp_rows_out = []
    iso_count = 0
    hyp_class_counts: dict[str, int] = {}

    for rec in hyp_raw["data"]:
        d = dict(zip(hf, rec))
        a_au = _f(d.get("a"))
        e_val = _f(d.get("e"))
        v_inf = math.sqrt(MU_SUN_KM3_S2 / (abs(a_au) * AU_KM)) if (a_au is not None and a_au < 0.0) else 0.0
        hcls = "CONFIRMED_INTERSTELLAR_OBJECT" if v_inf >= THRESHOLDS["n2a_iso_vinf_kms_min"] else "PLANET_PERTURBED_OORT_HYPERBOLIC"
        if hcls == "CONFIRMED_INTERSTELLAR_OBJECT":
            iso_count += 1
        hyp_class_counts[hcls] = hyp_class_counts.get(hcls, 0) + 1
        ng = _compute_nongrav_metrics(d)
        ssoft_m = _match_ssoft(d.get("pdes", ""), d.get("full_name", ""), ssoft_lut)
        hyp_rows_out.append({
            "spkid": d.get("spkid", ""),
            "full_name": str(d.get("full_name", "")).strip(),
            "pdes": d.get("pdes", ""),
            "orbit_class": d.get("class", ""),
            "e": f"{e_val:.6f}" if e_val is not None else "",
            "q_au": f"{_f(d.get('q')):.6f}" if _f(d.get("q")) is not None else "",
            "i_deg": f"{_f(d.get('i')):.4f}" if _f(d.get("i")) is not None else "",
            "a_au": f"{a_au:.6f}" if a_au is not None else "",
            "H": f"{_f(d.get('H')):.2f}" if _f(d.get("H")) is not None else "",
            "v_inf_kms": f"{v_inf:.4f}",
            "A1": f"{ng['a1']:.6e}" if ng["a1"] is not None else "",
            "A2": f"{ng['a2']:.6e}" if ng["a2"] is not None else "",
            "A3": f"{ng['a3']:.6e}" if ng["a3"] is not None else "",
            "a_rad_1au_ms2": f"{ng['a_rad_1au_ms2']:.6e}",
            "a_tot_1au_ms2": f"{ng['a_tot_1au_ms2']:.6e}",
            "am_srp_m2_kg": f"{ng['am_srp_m2_kg']:.6e}",
            "d_est_m": f"{ng['d_est_m']:.3f}" if ng["d_est_m"] is not None else "",
            "am_rock_m2_kg": f"{ng['am_rock_m2_kg']:.6e}" if ng["am_rock_m2_kg"] is not None else "",
            "srp_ratio_am_to_rock": f"{ng['srp_ratio_am_to_rock']:.4f}" if ng["srp_ratio_am_to_rock"] is not None else "",
            "first_obs": d.get("first_obs", ""),
            "last_obs": d.get("last_obs", ""),
            "n_obs_used": d.get("n_obs_used", ""),
            "in_fink_ssoft": bool(ssoft_m),
            "fink_sso_match": ssoft_m,
            "classification": hcls,
        })

    hyp_rows_out.sort(key=lambda r: float(r["v_inf_kms"]), reverse=True)
    cols_n2a = list(hyp_rows_out[0].keys()) if hyp_rows_out else []
    _write_csv(RES / "N2A_HYPERBOLIC_CENSUS.csv", cols_n2a, hyp_rows_out)

    nf = ng_raw["fields"]
    ng_rows_out = []
    ng_class_counts: dict[str, int] = {}
    screen_rows = [r for r in hyp_rows_out if float(r["v_inf_kms"]) >= THRESHOLDS["n2a_iso_vinf_kms_min"]]

    for rec in ng_raw["data"]:
        d = dict(zip(nf, rec))
        e_val = _f(d.get("e"))
        i_val = _f(d.get("i"))
        a_val = _f(d.get("a"))
        h_mag = _f(d.get("H"))
        ng = _compute_nongrav_metrics(d)
        cls_label = _classify_nongrav(d.get("class", ""), d.get("full_name", ""), e_val, i_val, h_mag, ng["max_ag"], ng["am_srp_m2_kg"])
        ng_class_counts[cls_label] = ng_class_counts.get(cls_label, 0) + 1
        ssoft_m = _match_ssoft(d.get("pdes", ""), d.get("full_name", ""), ssoft_lut)
        row_out = {
            "spkid": d.get("spkid", ""),
            "full_name": str(d.get("full_name", "")).strip(),
            "pdes": d.get("pdes", ""),
            "orbit_class": d.get("class", ""),
            "e": f"{e_val:.6f}" if e_val is not None else "",
            "q_au": f"{_f(d.get('q')):.6f}" if _f(d.get("q")) is not None else "",
            "i_deg": f"{i_val:.4f}" if i_val is not None else "",
            "a_au": f"{a_val:.6f}" if a_val is not None else "",
            "H": f"{h_mag:.2f}" if h_mag is not None else "",
            "v_inf_kms": f"{math.sqrt(MU_SUN_KM3_S2 / (abs(a_val) * AU_KM)):.4f}" if (a_val is not None and a_val < 0.0) else "0.0000",
            "A1": f"{ng['a1']:.6e}" if ng["a1"] is not None else "",
            "A2": f"{ng['a2']:.6e}" if ng["a2"] is not None else "",
            "A3": f"{ng['a3']:.6e}" if ng["a3"] is not None else "",
            "a_rad_1au_ms2": f"{ng['a_rad_1au_ms2']:.6e}",
            "a_tot_1au_ms2": f"{ng['a_tot_1au_ms2']:.6e}",
            "am_srp_m2_kg": f"{ng['am_srp_m2_kg']:.6e}",
            "d_est_m": f"{ng['d_est_m']:.3f}" if ng["d_est_m"] is not None else "",
            "am_rock_m2_kg": f"{ng['am_rock_m2_kg']:.6e}" if ng["am_rock_m2_kg"] is not None else "",
            "srp_ratio_am_to_rock": f"{ng['srp_ratio_am_to_rock']:.4f}" if ng["srp_ratio_am_to_rock"] is not None else "",
            "first_obs": d.get("first_obs", ""),
            "last_obs": d.get("last_obs", ""),
            "n_obs_used": d.get("n_obs_used", ""),
            "in_fink_ssoft": bool(ssoft_m),
            "fink_sso_match": ssoft_m,
            "classification": cls_label,
        }
        ng_rows_out.append(row_out)
        if ng["max_ag"] >= THRESHOLDS["n2a_nongrav_strong_au_d2"] and str(row_out["spkid"]) not in {str(x["spkid"]) for x in screen_rows}:
            screen_rows.append(row_out)

    ng_rows_out.sort(key=lambda r: float(r["a_tot_1au_ms2"]), reverse=True)
    _write_csv(RES / "N2A_NONGRAV_ASTEROIDS.csv", cols_n2a, ng_rows_out)
    screen_rows.sort(key=lambda r: (float(r["v_inf_kms"]), float(r["a_tot_1au_ms2"])), reverse=True)
    _write_csv(RES / "N2A_ISO_AND_DARK_COMET_SCREEN.csv", cols_n2a, screen_rows)

    return {
        "hyperbolic_total": len(hyp_rows_out),
        "confirmed_interstellar_objects": iso_count,
        "hyperbolic_classes": hyp_class_counts,
        "nongrav_asteroids_total": len(ng_rows_out),
        "nongrav_classes": ng_class_counts,
        "iso_and_strong_nongrav_screen_count": len(screen_rows),
        "hyperbolic_in_fink_ssoft": sum(1 for r in hyp_rows_out if r["in_fink_ssoft"]),
        "nongrav_in_fink_ssoft": sum(1 for r in ng_rows_out if r["in_fink_ssoft"]),
    }


def run_n2b(ssoft_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_rows = len(ssoft_rows)
    r_vals_all = [_f(r.get("R")) for r in ssoft_rows if _f(r.get("R")) is not None]
    r_boundary_all = sum(1 for v in r_vals_all if v <= THRESHOLDS["n2b_r_boundary_eps"])

    well_rows = []
    triggers = []
    r_boundary_well = 0
    n_trig_phot = 0
    n_trig_astrom = 0

    for r in ssoft_rows:
        n_obs = _f(r.get("n_obs"))
        rms = _f(r.get("rms"))
        chi2red = _f(r.get("chi2red"))
        std_ast = _f(r.get("std_astrometry"))
        mean_ast = _f(r.get("mean_astrometry"))
        r_ax = _f(r.get("R"))
        med_err = _f(r.get("median_error_phot"))
        if n_obs is None or n_obs < THRESHOLDS["n2b_min_obs"] or rms is None:
            continue
        if r_ax is not None and r_ax <= THRESHOLDS["n2b_r_boundary_eps"]:
            r_boundary_well += 1

        trig_phot = bool(rms >= THRESHOLDS["n2b_phot_rms_min"] and (chi2red is not None and chi2red >= THRESHOLDS["n2b_phot_chi2red_min"]))
        trig_ast = bool((std_ast is not None and std_ast >= THRESHOLDS["n2b_astrom_std_arcsec_min"]) or (mean_ast is not None and mean_ast >= THRESHOLDS["n2b_astrom_mean_arcsec_min"]))
        if trig_phot:
            n_trig_phot += 1
        if trig_ast:
            n_trig_astrom += 1

        chi_term = math.log10(max(1.0, chi2red if chi2red is not None else 1.0)) - 2.0
        ast_term = (max(0.0, ((std_ast or 0.0) - 0.05) / 0.03) + max(0.0, ((mean_ast or 0.0) - 0.15) / 0.05))
        phot_term = max(0.0, (rms - 0.25) / 0.05) + max(0.0, chi_term)
        anom_score = (3.0 if trig_ast else 0.0) + ast_term + phot_term

        row_clean = {
            "sso_number": str(r.get("sso_number", "")).strip(),
            "sso_name": str(r.get("sso_name", "")).strip(),
            "designation": str(r.get("designation", "")).strip(),
            "n_obs": int(round(n_obs)),
            "n_days": f"{_f(r.get('n_days')):.2f}" if _f(r.get("n_days")) is not None else "",
            "rms": f"{rms:.6f}",
            "chi2red": f"{chi2red:.4f}" if chi2red is not None else "",
            "median_error_phot": f"{med_err:.6f}" if med_err is not None else "",
            "R": f"{r_ax:.6f}" if r_ax is not None else "",
            "obliquity": f"{_f(r.get('obliquity')):.3f}" if _f(r.get("obliquity")) is not None else "",
            "std_astrometry": f"{std_ast:.6f}" if std_ast is not None else "",
            "mean_astrometry": f"{mean_ast:.6f}" if mean_ast is not None else "",
            "H_g": f"{_f(r.get('H_g')):.4f}" if _f(r.get("H_g")) is not None else "",
            "H_r": f"{_f(r.get('H_r')):.4f}" if _f(r.get("H_r")) is not None else "",
            "H_i": f"{_f(r.get('H_i')):.4f}" if _f(r.get("H_i")) is not None else "",
            "flag": r.get("flag", ""),
            "trig_phot_high_rms": trig_phot,
            "trig_astrom_scatter": trig_ast,
            "anomaly_score": f"{anom_score:.4f}",
        }
        well_rows.append(row_clean)
        if trig_phot or trig_ast:
            triggers.append(row_clean)

    well_rows.sort(key=lambda x: float(x["anomaly_score"]), reverse=True)
    triggers.sort(key=lambda x: (1 if x["trig_astrom_scatter"] else 0, float(x["anomaly_score"])), reverse=True)

    cols = list(well_rows[0].keys()) if well_rows else []
    _write_csv(RES / "N2B_SSOFT_WELL_SAMPLED.csv", cols, well_rows)
    _write_csv(RES / "N2B_SSOFT_ANOMALY_TRIGGERS.csv", cols, triggers)

    # 1,200 seeded synthetic injection-recovery trials across 100 real Rubin SSOFT objects
    rng = random.Random(20261127)
    sample_pool = list(well_rows)
    rng.shuffle(sample_pool)
    inj_objects = sample_pool[:min(100, len(sample_pool))]

    phot_amps = [0.4, 0.7, 1.0, 1.5, 2.0, 3.0]
    ast_drifts = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
    phot_grid: dict[str, dict[str, Any]] = {str(dm): {"trials": 0, "recovered": 0} for dm in phot_amps}
    ast_grid: dict[str, dict[str, Any]] = {str(da): {"trials": 0, "recovered": 0} for da in ast_drifts}

    for obj in inj_objects:
        n_pts = int(obj["n_obs"])
        sig_e = _f(obj["median_error_phot"]) or 0.04
        sig_e = max(0.005, sig_e)
        base_std_ast = _f(obj["std_astrometry"]) or 0.02
        base_mean_ast = _f(obj["mean_astrometry"]) or 0.04
        k_pulse = max(2, int(round(0.25 * n_pts)))

        for dm in phot_amps:
            resids = [rng.gauss(0.0, sig_e) for _ in range(n_pts)]
            for idx in rng.sample(range(n_pts), min(k_pulse, n_pts)):
                resids[idx] += dm
            mu = sum(resids) / n_pts
            c_res = [x - mu for x in resids]
            sim_rms = math.sqrt(sum(x * x for x in c_res) / n_pts)
            sim_chi2red = sum((x / sig_e) ** 2 for x in c_res) / max(1, n_pts - 4)
            ok = (sim_rms >= THRESHOLDS["n2b_phot_rms_min"]) and (sim_chi2red >= THRESHOLDS["n2b_phot_chi2red_min"])
            phot_grid[str(dm)]["trials"] += 1
            if ok:
                phot_grid[str(dm)]["recovered"] += 1

        for da in ast_drifts:
            jit_std = abs(rng.gauss(0.0, 0.005))
            sim_std = math.sqrt(base_std_ast ** 2 + da ** 2 + jit_std ** 2)
            sim_mean = math.sqrt(base_mean_ast ** 2 + (0.6 * da) ** 2)
            ok = (sim_std >= THRESHOLDS["n2b_astrom_std_arcsec_min"]) or (sim_mean >= THRESHOLDS["n2b_astrom_mean_arcsec_min"])
            ast_grid[str(da)]["trials"] += 1
            if ok:
                ast_grid[str(da)]["recovered"] += 1

    strong_phot_tr = sum(phot_grid[str(x)]["trials"] for x in (1.0, 1.5, 2.0, 3.0))
    strong_phot_rec = sum(phot_grid[str(x)]["recovered"] for x in (1.0, 1.5, 2.0, 3.0))
    comp_phot_strong = strong_phot_rec / max(1, strong_phot_tr)

    strong_ast_tr = sum(ast_grid[str(x)]["trials"] for x in (0.20, 0.30, 0.50))
    strong_ast_rec = sum(ast_grid[str(x)]["recovered"] for x in (0.20, 0.30, 0.50))
    comp_ast_strong = strong_ast_rec / max(1, strong_ast_tr)

    all_inj_trials = sum(v["trials"] for v in phot_grid.values()) + sum(v["trials"] for v in ast_grid.values())
    all_inj_rec = sum(v["recovered"] for v in phot_grid.values()) + sum(v["recovered"] for v in ast_grid.values())

    n_well = len(well_rows)
    return {
        "ssoft_total_rows": total_rows,
        "ssoft_r_boundary_pileup_all": r_boundary_all,
        "ssoft_r_boundary_fraction_all": round(r_boundary_all / max(1, len(r_vals_all)), 4),
        "well_sampled_n_obs_ge10": n_well,
        "ssoft_r_boundary_pileup_well": r_boundary_well,
        "ssoft_r_boundary_fraction_well": round(r_boundary_well / max(1, n_well), 4),
        "triggers_total": len(triggers),
        "triggers_phot_high_rms": n_trig_phot,
        "triggers_astrom_scatter": n_trig_astrom,
        "injection_objects_sampled": len(inj_objects),
        "injection_trials_total": all_inj_trials,
        "injection_recovered_all_grid": all_inj_rec,
        "injection_completeness_all_grid": round(all_inj_rec / max(1, all_inj_trials), 4),
        "phot_injection_grid": {k: {**v, "completeness": round(v["recovered"] / max(1, v["trials"]), 4)} for k, v in phot_grid.items()},
        "astrom_injection_grid": {k: {**v, "completeness": round(v["recovered"] / max(1, v["trials"]), 4)} for k, v in ast_grid.items()},
        "completeness_phot_dm_ge_1p0": round(comp_phot_strong, 4),
        "completeness_astrom_drift_ge_0p20": round(comp_ast_strong, 4),
        "bounds_well_sampled_phot_dm_ge_1p0": bayesian_zero_bounds(n_well * comp_phot_strong),
        "bounds_well_sampled_astrom_drift_ge_0p20": bayesian_zero_bounds(n_well * comp_ast_strong),
    }


def _classify_trail_rate(rate_deg_day: float) -> str:
    if rate_deg_day < 0.5:
        return "MBA_SLOW"
    if rate_deg_day <= 15.0:
        return "FAST_NEO_OR_ISO_REGIME"
    if rate_deg_day <= 400.0:
        return "HEO_MEO_GEO_REGIME"
    return "LEO_SATELLITE_REGIME"


def run_n2c() -> dict[str, Any]:
    ft_raw = json.loads((INP / "faint_trails" / "fink_faint_trails.json").read_text(encoding="utf-8"))
    eps_rad = math.radians(EPS_J2000_DEG)
    all_rows = []
    unlinked_clean = []
    regime_counts: dict[str, int] = {}

    for r in ft_raw:
        ra = _f(r.get("r:ra")) or 0.0
        dec = _f(r.get("r:dec")) or 0.0
        t_len = _f(r.get("r:trailLength")) or 0.0
        exp_t = _f(r.get("r:exposureTime")) or 30.0
        t_flux = _f(r.get("r:trailFlux"))
        p_flux = _f(r.get("r:psfFlux"))
        rel = _f(r.get("r:reliability")) or 0.0
        sso_id = r.get("r:ssObjectId")
        linked = sso_id not in (None, 0, "0", "")

        ang_s = t_len / exp_t if exp_t > 0.0 else 0.0
        ang_dd = ang_s * 24.0
        t_mag = (-2.5 * math.log10(t_flux) + 31.4) if (t_flux is not None and t_flux > 0.0) else None
        p_mag = (-2.5 * math.log10(p_flux) + 31.4) if (p_flux is not None and p_flux > 0.0) else None
        fratio = (t_flux / p_flux) if (t_flux is not None and p_flux is not None and p_flux > 0.0) else None

        ra_r = math.radians(ra)
        dec_r = math.radians(dec)
        sin_beta = max(-1.0, min(1.0, math.sin(dec_r) * math.cos(eps_rad) - math.cos(dec_r) * math.sin(eps_rad) * math.sin(ra_r)))
        ecl_lat = math.degrees(math.asin(sin_beta))
        kreg = _classify_trail_rate(ang_dd)
        regime_counts[kreg] = regime_counts.get(kreg, 0) + 1

        row_out = {
            "diaSourceId": str(r.get("r:diaSourceId", "")),
            "diaObjectId": str(r.get("r:diaObjectId", "")),
            "ra_deg": f"{ra:.6f}",
            "dec_deg": f"{dec:.6f}",
            "ecliptic_lat_deg": f"{ecl_lat:.4f}",
            "midpointMjdTai": f"{_f(r.get('r:midpointMjdTai')):.6f}" if _f(r.get("r:midpointMjdTai")) is not None else "",
            "band": r.get("r:band", ""),
            "exposureTime_s": f"{exp_t:.4f}",
            "trailLength_arcsec": f"{t_len:.5f}",
            "trailAngle_deg": f"{_f(r.get('r:trailAngle')):.3f}" if _f(r.get("r:trailAngle")) is not None else "",
            "ang_rate_arcsec_s": f"{ang_s:.6f}",
            "ang_rate_deg_day": f"{ang_dd:.6f}",
            "trailFlux_nJy": f"{t_flux:.3f}" if t_flux is not None else "",
            "psfFlux_nJy": f"{p_flux:.3f}" if p_flux is not None else "",
            "trail_mag_ab": f"{t_mag:.3f}" if t_mag is not None else "",
            "psf_mag_ab": f"{p_mag:.3f}" if p_mag is not None else "",
            "flux_ratio_trail_psf": f"{fratio:.4f}" if fratio is not None else "",
            "reliability": f"{rel:.4f}",
            "glint_trail": bool(r.get("r:glint_trail")),
            "ssObjectId": str(sso_id or 0),
            "linked_sso": linked,
            "xm_gaiadr3": str(r.get("f:xm_gaiadr3_DR3Name", "")),
            "xm_simbad": str(r.get("f:xm_simbad_otype", "")),
            "kinematic_regime": kreg,
        }
        all_rows.append(row_out)
        if (not linked) and rel >= THRESHOLDS["n2c_unlinked_min_reliability"]:
            unlinked_clean.append(row_out)

    all_rows.sort(key=lambda x: float(x["ang_rate_deg_day"]), reverse=True)
    unlinked_clean.sort(key=lambda x: float(x["ang_rate_deg_day"]), reverse=True)
    cols = list(all_rows[0].keys()) if all_rows else []
    _write_csv(RES / "N2C_FAINT_TRAILS_ALL.csv", cols, all_rows)
    _write_csv(RES / "N2C_FAINT_TRAILS_UNLINKED_CLEAN.csv", cols, unlinked_clean)

    rates = [float(x["ang_rate_deg_day"]) for x in all_rows]
    return {
        "faint_trails_total": len(all_rows),
        "linked_sso_count": sum(1 for x in all_rows if x["linked_sso"]),
        "unlinked_total": sum(1 for x in all_rows if not x["linked_sso"]),
        "unlinked_clean_rel_ge_0p70": len(unlinked_clean),
        "glint_trail_true": sum(1 for x in all_rows if x["glint_trail"]),
        "kinematic_regimes": regime_counts,
        "ang_rate_deg_day_min": round(min(rates), 4) if rates else 0.0,
        "ang_rate_deg_day_median": round(sorted(rates)[len(rates) // 2], 4) if rates else 0.0,
        "ang_rate_deg_day_max": round(max(rates), 4) if rates else 0.0,
    }


def main() -> int:
    ssoft_rows = json.loads((INP / "ssoft" / "fink_ssoft_shg1g2.json").read_text(encoding="utf-8"))
    ssoft_lut = build_ssoft_lookup(ssoft_rows)
    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyzer_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "n2a_iso_and_nongrav": run_n2a(ssoft_lut),
        "n2b_rubin_ssoft": run_n2b(ssoft_rows),
        "n2c_faint_trails": run_n2c(),
    }
    (RES / "N2_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
