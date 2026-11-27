#!/usr/bin/env python3
"""
Spor N6 Prospective Locked Analyzer (METHOD_LOCK & IMPLEMENTATION_LOCK):
Extragalactic Kardashev Type III (G-hat Waste-Heat + Garrett q_22 Radio-IR Correlation)
Search across the Local Supercluster (HECATE D <= 40 Mpc, logM_* >= 9.0) +
All-Sky Live Radio Surveys (NVSS 1.4 GHz, RACS-low 888 MHz, RACS-mid 1367.5 MHz,
LoTSS DR3 144 MHz).
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
WS = ROOT / "analysis_workspace" / "work_n6_20261127_kardashev_iii_supercluster"
INP = ROOT / "inputs_n6_20261127"
RES = WS / "results"
HECATE_CSV = INP / "hecate" / "hecate_local_supercluster.csv"

C_UM_S = 2.99792458e14
VEGA_BANDS = {
    "K":  {"nu": C_UM_S / 2.159,  "f0_jy": 666.7},
    "W1": {"nu": C_UM_S / 3.368,  "f0_jy": 309.540},
    "W2": {"nu": C_UM_S / 4.618,  "f0_jy": 171.787},
    "W3": {"nu": C_UM_S / 12.082, "f0_jy": 31.674},
    "W4": {"nu": C_UM_S / 22.194, "f0_jy": 8.363},
}

RADIO_SURVEYS = {
    "NVSS_1400":     {"file": "radio/nvss_1400mhz_galaxies.csv",     "freq_ghz": 1.400,  "dec_min": -40.0, "dec_max": 90.0, "sigma5_mjy": 2.25},
    "RACS_MID_1367": {"file": "radio/racs_mid_1367mhz_galaxies.csv", "freq_ghz": 1.3675, "dec_min": -90.0, "dec_max": 49.0, "sigma5_mjy": 1.00},
    "RACS_LOW_888":  {"file": "radio/racs_low_888mhz_galaxies.csv",  "freq_ghz": 0.888,  "dec_min": -90.0, "dec_max": 49.0, "sigma5_mjy": 1.50},
    "LOTSS_DR3_144": {"file": "radio/lotss_dr3_144mhz_galaxies.csv", "freq_ghz": 0.144,  "dec_min": -10.0, "dec_max": 90.0, "sigma5_mjy": 0.50},
}

K3_GATES = {
    "gamma_iii_rq_min": 0.25,
    "w1_minus_w4_min": 5.0,
    "q22_radio_quiet_min": 2.0,
    "w1_minus_w2_agn_max": 0.8,
    "gamma_iii_extreme_min": 0.50,
}


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def mag_to_jy(mag: float, band: str) -> float:
    return VEGA_BANDS[band]["f0_jy"] * (10.0 ** (-0.4 * mag))


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


def load_radio_matches() -> tuple[dict[str, dict[str, list[dict[str, Any]]]], dict[str, set[str]]]:
    matches: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    covered: dict[str, set[str]] = {sk: set() for sk in RADIO_SURVEYS}
    for sk, meta in RADIO_SURVEYS.items():
        fp = INP / meta["file"]
        if fp.exists():
            for row in csv.DictReader(fp.open(encoding="utf-8")):
                pgc = row["pgc"].strip()
                if row.get("total_flux_mjy"):
                    matches[pgc][sk].append(row)
                    covered[sk].add(pgc)
        fp_cov = fp.parent / f"{sk.lower()}_footprint.csv"
        if fp_cov.exists():
            for row in csv.DictReader(fp_cov.open(encoding="utf-8")):
                if row.get("in_footprint") == "True":
                    covered[sk].add(row["pgc"].strip())
    return matches, covered


def _write_csv(path: pathlib.Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> int:
    galaxies = list(csv.DictReader(HECATE_CSV.open(encoding="utf-8")))
    radio_matches, radio_covered = load_radio_matches()

    cat_rows: list[dict[str, Any]] = []
    trig_rows: list[dict[str, Any]] = []
    cov_counts: collections.Counter[str] = collections.Counter()
    trig_counts: collections.Counter[str] = collections.Counter()
    inj_pool: list[dict[str, float]] = []

    mstar_total = 0.0
    q22_det_vals: list[float] = []
    gamma_vals: list[float] = []

    for g in galaxies:
        pgc = g["PGC"].strip()
        ra, dec = float(g["RAJ2000"]), float(g["DEJ2000"])
        dist_mpc = float(g["D"])
        logm = float(g["logMtot"])
        mstar = 10.0 ** logm
        mstar_total += mstar
        maj_arcsec = (_f(g.get("MajAxis")) or 1.0) * 60.0
        ap_arcsec = max(30.0, min(90.0, 0.5 * maj_arcsec))

        kmag = float(g["Kmag"])
        w1 = float(g["W1mag"])
        w2 = float(g["W2mag"])
        w3 = float(g["W3mag"])
        w4 = float(g["W4mag"])

        fk = mag_to_jy(kmag, "K")
        fw1 = mag_to_jy(w1, "W1")
        fw3 = mag_to_jy(w3, "W3")
        fw4 = mag_to_jy(w4, "W4")
        f22_mjy = fw4 * 1000.0

        # Wright/Griffith waste-heat fraction G-hat proxy
        l_nir_proxy = 2.5 * (VEGA_BANDS["K"]["nu"] * fk + VEGA_BANDS["W1"]["nu"] * fw1)
        l_mir_proxy = VEGA_BANDS["W3"]["nu"] * fw3 + VEGA_BANDS["W4"]["nu"] * fw4
        gamma_iii = l_mir_proxy / max(1e-30, l_nir_proxy + l_mir_proxy)
        gamma_vals.append(gamma_iii)

        # Radio coverage & equivalent 1.4 GHz flux (scale alpha = -0.7 across surveys)
        cov_list: list[str] = []
        best_lim_14_mjy = 9999.0
        for sk, meta in RADIO_SURVEYS.items():
            in_cov = (pgc in radio_covered[sk]) or (sk != "LOTSS_DR3_144" and meta["dec_min"] <= dec <= meta["dec_max"])
            if in_cov:
                cov_list.append(sk)
                cov_counts[sk] += 1
                eq_lim = meta["sigma5_mjy"] * ((1.400 / meta["freq_ghz"]) ** -0.7)
                if eq_lim < best_lim_14_mjy:
                    best_lim_14_mjy = eq_lim

        s14_eq_mjy: float | None = None
        radio_survey_used = "UPPER_LIMIT"
        for sk in ("NVSS_1400", "RACS_MID_1367", "RACS_LOW_888", "LOTSS_DR3_144"):
            hits = [h for h in radio_matches.get(pgc, {}).get(sk, []) if float(h["sep_arcsec"]) <= ap_arcsec]
            if hits:
                raw_sum = sum(max(0.0, float(h["total_flux_mjy"])) for h in hits)
                if raw_sum > 0.0:
                    s14_eq_mjy = raw_sum * ((1.400 / RADIO_SURVEYS[sk]["freq_ghz"]) ** -0.7)
                    radio_survey_used = sk
                    break

        radio_detected = s14_eq_mjy is not None
        s14_val = s14_eq_mjy if s14_eq_mjy is not None else best_lim_14_mjy
        q22 = math.log10(max(1e-6, f22_mjy) / max(1e-6, s14_val))
        if radio_detected:
            cov_counts["radio_detected"] += 1
            q22_det_vals.append(q22)

        inj_pool.append({"fk": fk, "fw1": fw1, "fw3": fw3, "fw4": fw4, "s14_lim": best_lim_14_mjy})

        w1_w2 = w1 - w2
        w1_w4 = w1 - w4
        agnh = (g.get("AGNh") or "").strip()

        reasons: list[str] = []
        if (
            gamma_iii >= K3_GATES["gamma_iii_rq_min"]
            and w1_w4 >= K3_GATES["w1_minus_w4_min"]
            and q22 >= K3_GATES["q22_radio_quiet_min"]
            and agnh != "1"
            and w1_w2 < K3_GATES["w1_minus_w2_agn_max"]
        ):
            reasons.append("K3_RADIO_QUIET_WASTE_HEAT")
        if gamma_iii >= K3_GATES["gamma_iii_extreme_min"]:
            reasons.append("K3_EXTREME_GHAT_50PCT")

        is_trig = len(reasons) > 0
        for rsn in reasons:
            trig_counts[rsn] += 1

        rec = {
            "PGC": pgc,
            "NED": g.get("NED", ""),
            "ra_deg": round(ra, 6),
            "dec_deg": round(dec, 6),
            "dist_mpc": round(dist_mpc, 4),
            "logMtot": round(logm, 4),
            "maj_axis_arcsec": round(maj_arcsec, 1),
            "Kmag": round(kmag, 3),
            "W1mag": round(w1, 3),
            "W2mag": round(w2, 3),
            "W3mag": round(w3, 3),
            "W4mag": round(w4, 3),
            "W1_W2": round(w1_w2, 3),
            "W1_W4": round(w1_w4, 3),
            "f22_mjy": round(f22_mjy, 3),
            "gamma_iii": round(gamma_iii, 5),
            "n_radio_covering": len(cov_list),
            "radio_detected": radio_detected,
            "radio_survey_used": radio_survey_used,
            "s14_eq_or_lim_mjy": round(s14_val, 4),
            "q22": round(q22, 4),
            "logSFRh": g.get("logSFRh", ""),
            "F60um": g.get("F60um", ""),
            "F100um": g.get("F100um", ""),
            "Nuclear": g.get("Nuclear", ""),
            "AGNs17": g.get("AGNs17", ""),
            "AGNh": agnh,
            "k3_trigger": is_trig,
            "k3_reasons": "|".join(reasons),
        }
        cat_rows.append(rec)
        if is_trig:
            trig_rows.append(rec)

    _write_csv(RES / "N6_SUPERCLUSTER_K3_CATALOG.csv", list(cat_rows[0].keys()), cat_rows)
    if trig_rows:
        _write_csv(RES / "N6_K3_TRIGGERS.csv", list(trig_rows[0].keys()), trig_rows)
    else:
        _write_csv(RES / "N6_K3_TRIGGERS.csv", list(cat_rows[0].keys()), [])

    # 1,200 seeded synthetic Kardashev Type III radio-quiet waste-heat injections
    rng = random.Random(202611276)
    pool = list(inj_pool)
    rng.shuffle(pool)
    pool_200 = pool[:min(200, len(pool))]
    while len(pool_200) < 200:
        pool_200.append(pool[len(pool_200) % len(pool)])

    gammas_inj = [0.05, 0.10, 0.20, 0.30, 0.50, 0.75]
    inj_grid = {str(gi): {"trials": 0, "recovered": 0} for gi in gammas_inj}
    for gal in pool_200:
        l_star_0 = 2.5 * (VEGA_BANDS["K"]["nu"] * gal["fk"] + VEGA_BANDS["W1"]["nu"] * gal["fw1"])
        for gi in gammas_inj:
            # Transfer fraction gi of starlight into 300 K waste heat (0.45 in W3, 0.55 in W4) without adding radio flux
            l_waste = gi * l_star_0
            l_nir_new = max(1e-25, (1.0 - gi) * l_star_0)
            fw3_new = gal["fw3"] + (0.45 * l_waste) / VEGA_BANDS["W3"]["nu"]
            fw4_new = gal["fw4"] + (0.55 * l_waste) / VEGA_BANDS["W4"]["nu"]
            w1_new = -2.5 * math.log10(max(1e-12, (1.0 - gi) * gal["fw1"]) / VEGA_BANDS["W1"]["f0_jy"])
            w4_new = -2.5 * math.log10(max(1e-12, fw4_new) / VEGA_BANDS["W4"]["f0_jy"])
            g_obs = max(0.0, min(1.0, (0.45 * l_waste + 0.55 * l_waste) / (l_nir_new + l_waste) + rng.gauss(0.0, 0.015)))
            q22_obs = math.log10(max(1e-6, fw4_new * 1000.0) / max(1e-6, gal["s14_lim"]))
            inj_grid[str(gi)]["trials"] += 1
            if g_obs >= K3_GATES["gamma_iii_rq_min"] and (w1_new - w4_new) >= K3_GATES["w1_minus_w4_min"] and q22_obs >= K3_GATES["q22_radio_quiet_min"]:
                inj_grid[str(gi)]["recovered"] += 1

    for v in inj_grid.values():
        v["completeness"] = round(v["recovered"] / max(1, v["trials"]), 4)
    comp_ge_0p30 = sum(inj_grid[str(x)]["recovered"] for x in (0.30, 0.50, 0.75)) / sum(inj_grid[str(x)]["trials"] for x in (0.30, 0.50, 0.75))

    n_gal = len(cat_rows)
    n_mw = sum(1 for r in cat_rows if r["logMtot"] >= 10.0)
    n_d20 = sum(1 for r in cat_rows if r["dist_mpc"] <= 20.0)
    n_rdet = sum(1 for r in cat_rows if r["radio_detected"])
    n_stars_est = 1.5 * mstar_total

    bounds = {
        "all_local_supercluster_galaxies": bayesian_zero_bounds(float(n_gal) * comp_ge_0p30),
        "milky_way_mass_logM_ge_10": bayesian_zero_bounds(float(n_mw)),
        "nearby_20mpc_galaxies": bayesian_zero_bounds(float(n_d20)),
        "radio_detected_q22_galaxies": bayesian_zero_bounds(float(n_rdet)),
    }

    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyzer_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "galaxies_total": n_gal,
        "milky_way_mass_galaxies": n_mw,
        "nearby_20mpc_galaxies": n_d20,
        "total_stellar_mass_msun": float(f"{mstar_total:.4e}"),
        "estimated_total_stars_monitored": float(f"{n_stars_est:.4e}"),
        "per_star_k3_jeffreys_f95": float(f"{1.92 / n_stars_est:.4e}") if n_stars_est > 0 else None,
        "radio_coverage_counts": dict(cov_counts),
        "min_radio_surveys_per_galaxy": min(r["n_radio_covering"] for r in cat_rows),
        "q22_radio_detected_median": round(sorted(q22_det_vals)[len(q22_det_vals) // 2], 4) if q22_det_vals else None,
        "gamma_iii_median": round(sorted(gamma_vals)[len(gamma_vals) // 2], 5) if gamma_vals else None,
        "k3_triggers_total": len(trig_rows),
        "k3_trigger_breakdown": dict(trig_counts),
        "injection_trials_total": 1200,
        "injection_completeness_ge_0p30": round(comp_ge_0p30, 4),
        "injection_grid": inj_grid,
        "bayesian_limits_zero_k3": bounds,
    }
    (RES / "N6_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
