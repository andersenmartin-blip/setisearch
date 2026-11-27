#!/usr/bin/env python3
"""
Spor N4 Locked Prospective Analyzer (METHOD_LOCK & IMPLEMENTATION_LOCK):
All-Sky Low-Frequency Radio Bridge (54 MHz - 3.0 GHz + CHIME/FRB) across all
1,083 Master Catalog Stars (table1_master_catalog_1083stars.csv), extending
panchromatic EM coverage from 62.58 octaves to 71.9204 EM octaves.
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
WS = ROOT / "analysis_workspace" / "work_n4_20261127_lowfreq_radio_bridge_1083"
INP = ROOT / "inputs_n4_20261127"
RES = WS / "results"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"

# Exact SI / IAU physical constants
PC_TO_M = 3.0856775814913673e16
MJY_TO_W_M2_HZ = 1e-29
H_PLANCK_EV_S = 4.135667696e-15
NU_MAX_1PEV_HZ = 1.0e15 / H_PLANCK_EV_S       # 2.417989242e29 Hz (1.000 PeV)
NU_LOLSS_HZ = 54.0e6                          # 54 MHz
NU_LOTSS_HZ = 144.0e6                         # 144 MHz

SURVEYS: dict[str, dict[str, Any]] = {
    "LOLSS_54": {
        "file": "astron/lolss_54mhz_matches.csv",
        "freq_mhz": 54.0,
        "match_arcsec": 30.0,
        "footprint_arcsec": 5400.0,   # <= 1.5 deg empirical catalog presence
        "rms_mjy": 4.0,
        "sigma5_mjy": 20.0,
    },
    "VLSSR_74": {
        "file": "heasarc/vlssr_74mhz_matches.csv",
        "freq_mhz": 74.0,
        "match_arcsec": 45.0,
        "footprint_arcsec": 5400.0,
        "dec_min": -30.0,
        "dec_max": 90.0,
        "rms_mjy": 100.0,
        "sigma5_mjy": 500.0,
    },
    "LOTSS_DR3_144": {
        "file": "astron/lotss_dr3_144mhz_matches.csv",
        "freq_mhz": 144.0,
        "match_arcsec": 15.0,
        "footprint_arcsec": 1800.0,   # <= 0.5 deg empirical DR3 presence
        "rms_mjy": 0.10,
        "sigma5_mjy": 0.50,
    },
    "TGSS_150": {
        "file": "astron/tgss_150mhz_matches.csv",
        "freq_mhz": 150.0,
        "match_arcsec": 25.0,
        "footprint_arcsec": 3600.0,
        "dec_min": -53.0,
        "dec_max": 90.0,
        "rms_mjy": 3.5,
        "sigma5_mjy": 17.5,
    },
    "SUMSS_843": {
        "file": "heasarc/sumss_843mhz_matches.csv",
        "freq_mhz": 843.0,
        "match_arcsec": 25.0,
        "footprint_arcsec": 3600.0,
        "dec_min": -90.0,
        "dec_max": -30.0,
        "rms_mjy": 1.2,
        "sigma5_mjy": 6.0,
    },
    "RACS_LOW_888": {
        "file": "casda/racs_low_888mhz_matches.csv",
        "freq_mhz": 888.0,
        "match_arcsec": 15.0,
        "footprint_arcsec": 1800.0,
        "dec_min": -90.0,
        "dec_max": 49.0,
        "rms_mjy": 0.30,
        "sigma5_mjy": 1.50,
    },
    "RACS_MID_1367": {
        "file": "casda/racs_mid_1367mhz_matches.csv",
        "freq_mhz": 1367.5,
        "match_arcsec": 15.0,
        "footprint_arcsec": 1800.0,
        "dec_min": -90.0,
        "dec_max": 49.0,
        "rms_mjy": 0.20,
        "sigma5_mjy": 1.00,
    },
    "NVSS_1400": {
        "file": "heasarc/nvss_1400mhz_matches.csv",
        "freq_mhz": 1400.0,
        "match_arcsec": 25.0,
        "footprint_arcsec": 3600.0,
        "dec_min": -40.0,
        "dec_max": 90.0,
        "rms_mjy": 0.45,
        "sigma5_mjy": 2.25,
    },
    "FIRST_1400": {
        "file": "heasarc/first_1400mhz_matches.csv",
        "freq_mhz": 1400.0,
        "match_arcsec": 10.0,
        "footprint_arcsec": 1800.0,
        "rms_mjy": 0.15,
        "sigma5_mjy": 0.75,
    },
}


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


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


def _write_csv(path: pathlib.Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def load_footprint_and_matches(stars_by_name: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], dict[str, set[str]]]:
    matches: dict[str, dict[str, list[dict[str, Any]]]] = {s: collections.defaultdict(list) for s in stars_by_name}
    covered: dict[str, set[str]] = {sk: set() for sk in SURVEYS}

    for sk, meta in SURVEYS.items():
        fp = INP / meta["file"]
        if fp.exists():
            for row in csv.DictReader(fp.open(encoding="utf-8")):
                st = row["star"]
                if st not in stars_by_name:
                    continue
                sep = _f(row.get("sep_arcsec"))
                if sep is not None and sep <= meta["footprint_arcsec"]:
                    covered[sk].add(st)
                if sep is not None and sep <= meta["match_arcsec"]:
                    matches[st][sk].append({**row, "survey": sk, "freq_mhz": meta["freq_mhz"], "sep_f": sep})
        # Also mark standard declination coverage for full-footprint surveys (VLSSr, TGSS, SUMSS, RACS, NVSS)
        if "dec_min" in meta and "dec_max" in meta:
            dmin, dmax = meta["dec_min"], meta["dec_max"]
            for st, srow in stars_by_name.items():
                dec = float(srow["dec_deg"])
                if dmin <= dec <= dmax:
                    covered[sk].add(st)
        # Check footprint files if provided separately (lolss_footprint.csv / lotss_dr3_footprint.csv / first_footprint.csv)
        fp_extra = fp.parent / f"{sk.lower()}_footprint.csv"
        if fp_extra.exists():
            for row in csv.DictReader(fp_extra.open(encoding="utf-8")):
                if row.get("in_footprint") == "True" and row["star"] in stars_by_name:
                    covered[sk].add(row["star"])

    for st in matches:
        for sk in matches[st]:
            matches[st][sk].sort(key=lambda r: r["sep_f"])
    return matches, covered


def load_chime_crossmatch(stars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tsv_p = INP / "chime" / "chime_frb_cat1.tsv"
    if not tsv_p.exists():
        return []
    lines = [l for l in tsv_p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip() and not l.startswith("#")]
    if len(lines) < 3:
        return []
    hdr = lines[0].split("\t")
    # Skip unit & dashes rows (lines 1 and 2)
    data_start = 3 if (len(lines) >= 3 and set(lines[2].replace("\t", "").strip()).issubset({"-", " "})) else 1
    bursts = []
    for ln in lines[data_start:]:
        cols = ln.split("\t")
        if len(cols) < len(hdr):
            continue
        rec = dict(zip(hdr, [c.strip() for c in cols]))
        ra = _f(rec.get("RAJ2000"))
        dec = _f(rec.get("DEJ2000"))
        era = _f(rec.get("e_RAJ2000")) or 0.25
        edec = _f(rec.get("e_DEJ2000")) or 0.25
        if ra is not None and dec is not None:
            bursts.append({
                "frb": rec.get("FRB", ""),
                "ra": ra,
                "dec": dec,
                "err_deg": max(0.5, 3.0 * math.hypot(era, edec)),
                "dm": _f(rec.get("DM")) or 0.0,
                "fluence": _f(rec.get("Fluence")),
                "peak_flux": _f(rec.get("PeakFlux")),
                "rep": rec.get("Rep", ""),
            })

    xm_rows = []
    for s in stars:
        sra, sdec = float(s["ra_deg"]), float(s["dec_deg"])
        for b in bursts:
            if abs(sdec - b["dec"]) > b["err_deg"]:
                continue
            sep_deg = angsep_arcsec(sra, sdec, b["ra"], b["dec"]) / 3600.0
            if sep_deg <= b["err_deg"]:
                xm_rows.append({
                    "star": s["star"],
                    "common_name": s["common_name"],
                    "role": s["role"],
                    "dist_pc": s["dist_pc"],
                    "ra_deg": s["ra_deg"],
                    "dec_deg": s["dec_deg"],
                    "frb_name": b["frb"],
                    "frb_ra": b["ra"],
                    "frb_dec": b["dec"],
                    "sep_deg": round(sep_deg, 4),
                    "err_radius_3sig_deg": round(b["err_deg"], 4),
                    "dm_pc_cm3": b["dm"],
                    "fluence_jy_ms": b["fluence"] if b["fluence"] is not None else "",
                    "repeater": b["rep"],
                })
    return xm_rows


def main() -> int:
    master_stars = list(csv.DictReader(TABLE1.open(encoding="utf-8")))
    stars_by_name = {r["star"]: r for r in master_stars}
    matches, covered = load_footprint_and_matches(stars_by_name)
    chime_matches = load_chime_crossmatch(master_stars)

    summary_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    deepest_survey_pool: list[tuple[str, float, float]] = []  # (survey_key, rms_mjy, dist_pc)
    min_freq_all: list[float] = []

    for s in master_stars:
        st = s["star"]
        dist_pc = _f(s["dist_pc"]) or 100.0
        cov_surveys = [sk for sk in SURVEYS if st in covered[sk]]
        cov_chime = float(s["dec_deg"]) >= -11.0

        # Identify deepest covering continuum survey (lowest 5-sigma sensitivity in mJy)
        if cov_surveys:
            best_sk = min(cov_surveys, key=lambda sk: SURVEYS[sk]["sigma5_mjy"])
            lowest_f = min(SURVEYS[sk]["freq_mhz"] for sk in cov_surveys)
        else:
            best_sk = "NONE"
            lowest_f = 1400.0
        min_freq_all.append(lowest_f)

        best_meta = SURVEYS.get(best_sk, {"rms_mjy": 0.5, "sigma5_mjy": 2.5, "freq_mhz": 1400.0})
        s5_best = best_meta["sigma5_mjy"]
        # If local RMS provided on detection, record matched flux; for survey non-detection limit use nominal 5-sigma
        st_matches = matches[st]
        n_matched_surveys = len(st_matches)
        matched_list = []
        for sk, mlist in sorted(st_matches.items(), key=lambda kv: SURVEYS[kv[0]]["freq_mhz"]):
            m0 = mlist[0]
            flx = _f(m0.get("total_flux_mjy")) or _f(m0.get("peak_flux_mjy")) or 0.0
            matched_list.append(f"{sk}:{flx:.2f}mJy@{m0['sep_f']:.1f}\"")
            candidate_rows.append({
                "star": st,
                "common_name": s["common_name"],
                "role": s["role"],
                "subrole": s["subrole"],
                "dist_pc": s["dist_pc"],
                "within_10pc": s["within_10pc"],
                "star_ra_deg": s["ra_deg"],
                "star_dec_deg": s["dec_deg"],
                "survey": sk,
                "freq_mhz": SURVEYS[sk]["freq_mhz"],
                "source_name": m0.get("source_name", ""),
                "src_ra_deg": m0.get("ra", ""),
                "src_dec_deg": m0.get("dec", ""),
                "sep_arcsec": round(m0["sep_f"], 3),
                "total_flux_mjy": m0.get("total_flux_mjy", ""),
                "peak_flux_mjy": m0.get("peak_flux_mjy", ""),
                "rms_mjy": m0.get("rms_mjy", ""),
            })

        # Luminosity & EIRP upper limits at 5-sigma of deepest covering survey
        d_m = dist_pc * PC_TO_M
        l_nu = 4.0 * math.pi * (d_m ** 2) * (s5_best * MJY_TO_W_M2_HZ)
        eirp_1hz = l_nu * 1.0
        p_100mhz = l_nu * 1.0e8
        deepest_survey_pool.append((best_sk, best_meta["rms_mjy"], dist_pc))

        summary_rows.append({
            "star": st,
            "common_name": s["common_name"],
            "role": s["role"],
            "subrole": s["subrole"],
            "ra_deg": s["ra_deg"],
            "dec_deg": s["dec_deg"],
            "dist_pc": s["dist_pc"],
            "within_10pc": s["within_10pc"],
            "n_lowfreq_surveys_covering": len(cov_surveys),
            "chime_frb_covered": cov_chime,
            "lowest_freq_mhz": lowest_f,
            "deepest_survey": best_sk,
            "deepest_freq_mhz": best_meta["freq_mhz"],
            "deepest_5sigma_mjy": s5_best,
            "l_nu_5sigma_w_hz": f"{l_nu:.6e}",
            "eirp_1hz_w": f"{eirp_1hz:.6e}",
            "p_100mhz_w": f"{p_100mhz:.6e}",
            "n_matched_radio_surveys": n_matched_surveys,
            "matched_surveys_detail": "; ".join(matched_list),
            "covering_surveys": "+".join(sorted(cov_surveys, key=lambda x: SURVEYS[x]["freq_mhz"])),
        })

    _write_csv(RES / "N4_MASTER_1083_RADIO_SUMMARY.csv", list(summary_rows[0].keys()), summary_rows)
    if candidate_rows:
        _write_csv(RES / "N4_RADIO_MATCH_CANDIDATES.csv", list(candidate_rows[0].keys()), candidate_rows)
    else:
        _write_csv(RES / "N4_RADIO_MATCH_CANDIDATES.csv", ["star", "survey", "sep_arcsec", "total_flux_mjy"], [])
    if chime_matches:
        _write_csv(RES / "N4_CHIME_FRB_CROSSMATCH.csv", list(chime_matches[0].keys()), chime_matches)
    else:
        _write_csv(RES / "N4_CHIME_FRB_CROSSMATCH.csv", ["star", "frb_name", "sep_deg", "dm_pc_cm3"], [])

    # 1,200 seeded synthetic injection-recovery trials across 200 real stars x 6 fluxes
    rng = random.Random(20261127)
    idx_pool = list(range(len(summary_rows)))
    rng.shuffle(idx_pool)
    inj_indices = idx_pool[:200]
    flux_grid = [0.3, 0.5, 1.0, 2.0, 5.0, 15.0]  # mJy
    grid_stats = {str(s_inj): {"trials": 0, "recovered": 0} for s_inj in flux_grid}

    for ix in inj_indices:
        _, rms, _ = deepest_survey_pool[ix]
        thresh = 5.0 * rms
        for s_inj in flux_grid:
            s_obs = s_inj + rng.gauss(0.0, rms)
            grid_stats[str(s_inj)]["trials"] += 1
            if s_obs >= thresh:
                grid_stats[str(s_inj)]["recovered"] += 1

    for v in grid_stats.values():
        v["completeness"] = round(v["recovered"] / max(1, v["trials"]), 4)
    comp_ge_2mjy = sum(grid_stats[str(x)]["recovered"] for x in (2.0, 5.0, 15.0)) / sum(grid_stats[str(x)]["trials"] for x in (2.0, 5.0, 15.0))
    comp_all = sum(v["recovered"] for v in grid_stats.values()) / sum(v["trials"] for v in grid_stats.values())

    # Panchromatic span calculation
    global_min_freq = min(min_freq_all)
    octaves_span = math.log2(NU_MAX_1PEV_HZ / (global_min_freq * 1e6))
    energy_ratio = NU_MAX_1PEV_HZ / (global_min_freq * 1e6)

    n_sci = sum(1 for r in summary_rows if r["role"] == "SCIENCE")
    n_10pc = sum(1 for r in summary_rows if r["within_10pc"] == "True")
    n_lotss = len(covered["LOTSS_DR3_144"])
    n_lolss = len(covered["LOLSS_54"])
    n_racs = len(covered["RACS_LOW_888"] | covered["RACS_MID_1367"])
    n_chime = sum(1 for r in summary_rows if r["chime_frb_covered"])

    # Conservative Bayesian zero-ETI limits (k=0 after Stage 3 vetting) using comp_ge_2mjy (plus unattenuated sub-cohort counts)
    bounds = {
        "all_1083_stars_s_ge_2mjy": bayesian_zero_bounds(len(summary_rows) * comp_ge_2mjy),
        "science_787_stars_s_ge_2mjy": bayesian_zero_bounds(n_sci * comp_ge_2mjy),
        "within_10pc_267_stars": bayesian_zero_bounds(float(n_10pc)),
        "lotss_dr3_144mhz_covered": bayesian_zero_bounds(float(n_lotss)),
        "racs_888_1367mhz_covered": bayesian_zero_bounds(float(n_racs)),
        "chime_frb_400_800mhz_covered": bayesian_zero_bounds(float(n_chime)),
    }

    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyzer_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "master_stars_total": len(summary_rows),
        "science_stars": n_sci,
        "within_10pc_stars": n_10pc,
        "min_covering_surveys_per_star": min(r["n_lowfreq_surveys_covering"] for r in summary_rows),
        "median_covering_surveys_per_star": sorted(r["n_lowfreq_surveys_covering"] for r in summary_rows)[len(summary_rows) // 2],
        "panchromatic_span": {
            "lowest_freq_mhz": global_min_freq,
            "highest_energy_ev": 1.0e15,
            "em_octaves": round(octaves_span, 4),
            "prior_v7_octaves": 62.582,
            "energy_ratio": float(f"{energy_ratio:.4e}"),
        },
        "survey_coverage_counts": {sk: len(covered[sk]) for sk in SURVEYS},
        "chime_frb_covered_stars": n_chime,
        "chime_frb_ellipse_overlaps": len(chime_matches),
        "radio_match_candidate_rows": len(candidate_rows),
        "unique_matched_stars": len({r["star"] for r in candidate_rows}),
        "injection_trials_total": 1200,
        "injection_completeness_all": round(comp_all, 4),
        "injection_completeness_s_ge_2mjy": round(comp_ge_2mjy, 4),
        "injection_grid": grid_stats,
        "bayesian_limits_zero_eti": bounds,
    }
    (RES / "N4_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
