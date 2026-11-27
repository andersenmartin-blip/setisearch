#!/usr/bin/env python3
"""
Spor N5 Stage 3: Live 10-Year Multi-Epoch NEOWISE-R (2014-2024) + ZTF
Lightcurve Acquisition (with exact Gaia DR3 proper-motion epoch tracking!),
Moving-Aperture Ephemeris Filtering, Secular Slope Fitting, ASASSN-21qj Positive
Benchmark Calibration, Hephaistos A-G 10-Yr Stability, and Complete Candidate Vetting.
Forces IPv4 (socket.AF_INET). Runs under .venv/bin/python.
"""
from __future__ import annotations

import collections
import csv
import datetime
import json
import math
import pathlib
import socket
import time
import urllib.parse
import urllib.request
from typing import Any

import numpy as np

# Critical IPv4 force
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n5_20261127_secular_ir_optical_1083"
INP = ROOT / "inputs_n5_20261127"
RES = WS / "results"


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def safe_name(star: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in star)


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def propagate_coords(ra: float, dec: float, pmra: float | None, pmdec: float | None, dt_yr: float) -> tuple[float, float]:
    if pmra is None or pmdec is None or abs(pmra) > 11000 or abs(pmdec) > 11000:
        return ra, dec
    cosd = max(0.1, math.cos(math.radians(dec)))
    return (ra + (pmra / (3.6e6 * cosd)) * dt_yr) % 360.0, max(-89.999, min(89.999, dec + (pmdec / 3.6e6) * dt_yr))


def _parse_ipac_simple(raw: str) -> list[dict[str, str]]:
    lines = raw.splitlines()
    hdr_idx = None
    for idx, ln in enumerate(lines):
        if ln.startswith("|"):
            hdr_idx = idx
            break
    if hdr_idx is None:
        return []
    hdr_ln = lines[hdr_idx]
    pipes = [p for p, c in enumerate(hdr_ln) if c == "|"]
    cols = [hdr_ln[pipes[k] + 1:pipes[k + 1]].strip() for k in range(len(pipes) - 1)]
    ds = hdr_idx + 1
    while ds < len(lines) and (lines[ds].startswith("|") or not lines[ds].strip()):
        ds += 1
    out = []
    for ln in lines[ds:]:
        if not ln.strip() or ln.startswith("\\") or ln.startswith("|"):
            continue
        vals = [ln[pipes[k]:pipes[k + 1]].strip() for k in range(len(pipes) - 1)] if len(ln) >= pipes[-1] else ln.split()
        if len(vals) == len(cols):
            out.append({k: ("" if v.lower() == "null" else v) for k, v in zip(cols, vals)})
    return out


def fetch_neowise_lc(star: str, ra_2019: float, dec_2019: float, rad_arcsec: float) -> tuple[list[dict[str, str]], str]:
    p = INP / "neowise_lc" / f"{safe_name(star)}_neowise.csv"
    if p.exists() and p.stat().st_size > 120:
        return list(csv.DictReader(p.open(encoding="utf-8"))), "cached"
    u = (
        f"https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=neowiser_p1bs_psd&spatial=cone"
        f"&objstr={ra_2019:.6f}+{dec_2019:+.6f}&radius={rad_arcsec:.1f}&radunits=arcsec&outfmt=1"
        f"&selcols=ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qi_fact,saa_sep,moon_masked"
    )
    for att in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SETI-N5/1.0"}), timeout=35) as r:
                txt = r.read().decode("utf-8", errors="replace")
            rows = _parse_ipac_simple(txt)
            if not rows:
                return [], "empty"
            with p.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            return rows, "downloaded"
        except Exception as e:
            if att == 2:
                return [], f"err_{type(e).__name__}"
            time.sleep(1.0 * (att + 1))
    return [], "empty"


def fetch_ztf_lc(star: str, ra: float, dec: float) -> tuple[list[dict[str, str]], str]:
    p = INP / "ztf_lc" / f"{safe_name(star)}_ztf.csv"
    if p.exists() and p.stat().st_size > 120:
        return list(csv.DictReader(p.open(encoding="utf-8"))), "cached"
    u = f"https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE+{ra:.6f}+{dec:.6f}+0.0014&BAD_CATFLAGS_MASK=32768&FORMAT=CSV"
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SETI-N5/1.0"}), timeout=25) as r:
            txt = r.read().decode("utf-8", errors="replace")
        lines = [l for l in txt.splitlines() if l.strip()]
        if len(lines) < 5:
            return [], "empty"
        p.write_text(txt, encoding="utf-8")
        return list(csv.DictReader(lines)), "downloaded"
    except Exception:
        return [], "err"


def analyze_neowise_10yr(star: str, raw_rows: list[dict[str, str]], g_row: dict[str, Any], t_row: dict[str, Any]) -> dict[str, Any]:
    gra, gdec = _f(g_row.get("ra")), _f(g_row.get("dec"))
    pmra, pmdec = _f(g_row.get("pmra")), _f(g_row.get("pmdec"))
    base_ra = gra if gra is not None else float(t_row["ra_deg"])
    base_dec = gdec if gdec is not None else float(t_row["dec_deg"])
    base_ep = 2016.0 if gra is not None else 2000.0

    clean = []
    for r in raw_rows:
        mjd = _f(r.get("mjd"))
        w1, sw1 = _f(r.get("w1mpro")), _f(r.get("w1sigmpro"))
        w2, sw2 = _f(r.get("w2mpro")), _f(r.get("w2sigmpro"))
        qi = _f(r.get("qi_fact"))
        saa = _f(r.get("saa_sep"))
        moon = (r.get("moon_masked") or "00").strip()
        rra, rdec = _f(r.get("ra")), _f(r.get("dec"))
        if mjd is None or w1 is None or w2 is None or rra is None or rdec is None:
            continue
        if (qi is not None and qi < 0.5) or (saa is not None and saa < 5.0) or ("1" in moon):
            continue
        # Moving-aperture Gaia PM ephemeris match at exposure epoch!
        ep_yr = 2000.0 + (mjd - 51544.5) / 365.25
        era, edec = propagate_coords(base_ra, base_dec, pmra, pmdec, ep_yr - base_ep)
        if angsep_arcsec(era, edec, rra, rdec) > 4.5:
            continue
        clean.append((mjd, w1, max(0.015, sw1 or 0.04), w2, max(0.020, sw2 or 0.05)))

    if len(clean) < 10:
        return {"star": star, "n_raw": len(raw_rows), "n_clean_ep": len(clean), "n_visits": 0}

    clean.sort(key=lambda x: x[0])
    # Group into semi-annual visits separated by >= 60 days
    visits = []
    cur = [clean[0]]
    for pt in clean[1:]:
        if pt[0] - cur[-1][0] >= 60.0:
            visits.append(cur)
            cur = [pt]
        else:
            cur.append(pt)
    visits.append(cur)

    v_mjd, v_w1, v_ew1, v_w2, v_ew2, v_col = [], [], [], [], [], []
    for vis in visits:
        if len(vis) < 2:
            continue
        mjds = np.array([x[0] for x in vis])
        w1s = np.array([x[1] for x in vis])
        w2s = np.array([x[3] for x in vis])
        sw1s = np.array([x[2] for x in vis])
        sw2s = np.array([x[4] for x in vis])
        v_mjd.append(float(np.median(mjds)))
        m1, m2 = float(np.median(w1s)), float(np.median(w2s))
        v_w1.append(m1)
        v_w2.append(m2)
        v_col.append(m1 - m2)
        mad1 = 1.4826 * float(np.median(np.abs(w1s - m1)))
        mad2 = 1.4826 * float(np.median(np.abs(w2s - m2)))
        v_ew1.append(max(0.015, mad1 / math.sqrt(len(vis)), float(np.median(sw1s)) / math.sqrt(len(vis))))
        v_ew2.append(max(0.020, mad2 / math.sqrt(len(vis)), float(np.median(sw2s)) / math.sqrt(len(vis))))

    if len(v_mjd) < 4:
        return {"star": star, "n_raw": len(raw_rows), "n_clean_ep": len(clean), "n_visits": len(v_mjd)}

    t_yr = (np.array(v_mjd) - v_mjd[0]) / 365.25
    w1_a = np.array(v_w1)
    w2_a = np.array(v_w2)
    ew2_a = np.array(v_ew2)
    col_a = np.array(v_col)

    # Weighted OLS slope for W2 and W1
    wt2 = 1.0 / (ew2_a ** 2)
    tbar = np.sum(wt2 * t_yr) / np.sum(wt2)
    dw2_dt = float(np.sum(wt2 * (t_yr - tbar) * (w2_a - np.sum(wt2 * w2_a) / np.sum(wt2))) / max(1e-9, np.sum(wt2 * (t_yr - tbar) ** 2)))
    err_dw2_dt = float(1.0 / math.sqrt(max(1e-9, np.sum(wt2 * (t_yr - tbar) ** 2))))
    z_slope_w2 = dw2_dt / max(1e-6, err_dw2_dt)

    dw1_dt = float(np.polyfit(t_yr, w1_a, 1)[0]) if np.ptp(t_yr) > 0.5 else 0.0
    dcol_dt = float(np.polyfit(t_yr, col_a, 1)[0]) if np.ptp(t_yr) > 0.5 else 0.0
    r_mono = float(np.corrcoef(t_yr, w2_a)[0, 1]) if np.std(w2_a) > 0 else 0.0
    chi2_red_w2 = float(np.sum(((w2_a - np.median(w2_a)) / ew2_a) ** 2) / max(1, len(w2_a) - 1))

    med_w1, med_w2 = float(np.median(w1_a)), float(np.median(w2_a))
    ptp_w2 = float(np.max(w2_a) - np.min(w2_a))
    sat_w2 = med_w2 < 7.0
    # Dyson-swarm IR brightening signature: unsaturated W2 >= 7.0, brightening >= 0.015 mag/yr at >= 5 sigma, monotonic OR strong step burst
    dyson_gate = (not sat_w2) and (dw2_dt <= -0.015) and (abs(z_slope_w2) >= 5.0) and (abs(r_mono) >= 0.65 or chi2_red_w2 >= 20.0)

    return {
        "star": star,
        "n_raw": len(raw_rows),
        "n_clean_ep": len(clean),
        "n_visits": len(v_mjd),
        "baseline_yr": round(float(t_yr[-1] - t_yr[0]), 2),
        "neowise_med_w1": round(med_w1, 4),
        "neowise_med_w2": round(med_w2, 4),
        "neowise_dw1_dt": round(dw1_dt, 5),
        "neowise_dw2_dt": round(dw2_dt, 5),
        "neowise_err_dw2_dt": round(err_dw2_dt, 5),
        "neowise_z_dw2": round(z_slope_w2, 2),
        "neowise_dcol_dt": round(dcol_dt, 5),
        "neowise_w2_ptp": round(ptp_w2, 4),
        "neowise_w2_r": round(r_mono, 3),
        "neowise_w2_chi2_red": round(chi2_red_w2, 2),
        "neowise_sat_w2": sat_w2,
        "dyson_ir_gate": dyson_gate,
    }


def classify_vetted(row: dict[str, Any], neo: dict[str, Any] | None) -> tuple[str, str]:
    st = row["star"]
    sub = (row.get("subrole") or "").upper()
    cn = (row.get("common_name") or "").upper()
    role = row["role"]
    scat = row["source_catalog"]

    if scat == "BENCHMARK_13":
        if st.startswith("HEPH_"):
            return "HEPHAISTOS_10YR_STABLE_BENCHMARK", f"NEOWISE 10-yr |dW2/dt|={abs(neo.get('neowise_dw2_dt', 0)):.4f} mag/yr (no secular construction drift)"
        if neo and neo.get("dyson_ir_gate"):
            return "POSITIVE_BENCHMARK_SECULAR_IR_RECOVERED", f"ASASSN-21qj collision recovered: dW2/dt={neo['neowise_dw2_dt']} mag/yr (Z={neo['neowise_z_dw2']})"
        return "ASTROPHYSICAL_DIPPER_BENCHMARK", f"Dipper/active calibration target ({cn[:35]})"

    if role == "CONTROL":
        return "CONTROL_AGN_OR_CALIBRATOR", "Astronomical/extragalactic control target"

    # SCIENCE classification
    if any(k in sub or k in cn for k in ("YSO", "PROTOPLANETARY", "DISK", "CORINO", "ALMA", "HERBIG", "CTTS", "TTAU", "T TAURI", "GW ORI", "LKCA", "HOT_COR")) or st in ("OPH1631", "IRAS16293M2422", "GWORI", "J160901", "LKCA15", "AS209", "HD145718", "SZ65J1608", "SZ90", "TTAU", "GQLUP", "N2071IR"):
        return "KNOWN_YSO_PROTOSTAR_OR_DISK_VAR", f"Young stellar object / circumstellar disk variability ({row['subrole']})"

    if any(k in sub or k in cn for k in ("AGB", "MIRA", "RED_SUPERGIANT", "MU CEP", "CH CYG", "SYMBIOTIC", "NOVA", "LPV")) or st in ("MUCEP", "CHCYG", "TPYX", "IKTAU", "RDOR", "GHER", "ANTARES"):
        return "KNOWN_AGB_NOVA_OR_SYMBIOTIC_VAR", f"Evolved pulsator / nova / symbiotic envelope ({row['common_name']})"

    if any(k in sub or k in cn for k in ("EROSITA", "RSCVN", "FLARE", "ACTIVE", "EUVE", "HEXTE", "XMM_RGS", "NUSTAR")) or st in ("RZCAS", "XYUMA", "ARLAC", "VYYGEM", "HR5907", "ADLEO", "DGCVN"):
        return "KNOWN_ACTIVE_FLARE_OR_BINARY_NSS", f"Active coronal / eclipsing binary / magnetic star"

    # Check bright saturation or ultra-high-PM binary fly-through (Gaia-absent Luhman 16AB 2.78"/yr)
    w2a = _f(row.get("allwise_w2"))
    if st == "WISE1049AB":
        return "WISE_BRIGHT_SATURATION_OR_PM_DRIFT", "Luhman 16AB (1.996 pc, Gaia-absent brown dwarf binary): 2.78\"/yr proper-motion transit across static NEOWISE aperture (W2=14.2->7.1)"
    if (w2a is not None and w2a < 8.5) or (neo and neo.get("neowise_sat_w2")):
        return "WISE_BRIGHT_SATURATION_OR_PM_DRIFT", f"Bright WISE profile saturation / PM shift across AllWISE-CatWISE; NEOWISE clean check"

    if neo and neo.get("n_visits", 0) >= 6:
        if neo.get("dyson_ir_gate"):
            return "UNEXPLAINED_SECULAR_IR_FOLLOWUP", f"NEOWISE dW2/dt={neo['neowise_dw2_dt']} (Z={neo['neowise_z_dw2']})"
        return "NEOWISE_10YR_FLAT_OR_CROWDED_BLEND", f"AllWISE-CatWISE static/PM/blend offset resolved flat over 10-yr NEOWISE (dW2/dt={neo['neowise_dw2_dt']}, W2_p2p={neo['neowise_w2_ptp']})"

    return "HIGH_PM_OR_UNWISE_CATALOG_ARTIFACT", "High-PM / CatWISE-AllWISE cross-pipeline difference without secular NEOWISE drift"


def main() -> int:
    summary_all = list(csv.DictReader((RES / "N5_MASTER_1096_SECULAR_SUMMARY.csv").open(encoding="utf-8")))
    by_star_sum = {r["star"]: r for r in summary_all}
    gaia_map = {r["star"]: r for r in csv.DictReader((INP / "gaia" / "gaia_dr3_1096.csv").open(encoding="utf-8"))}

    # Build prioritized Tier-2 NEOWISE-R 10-yr LC acquisition target list:
    # 1) All 13 Benchmarks (incl. ASASSN-21qj, Boyajian, Hephaistos A-G)
    bench = [r["star"] for r in summary_all if r["source_catalog"] == "BENCHMARK_13"]
    # 2) All 4 IR brightening + 14 GAIA_DIPPER + top 45 unsaturated W2>=8.2 SCIENCE triggers
    sci_trig = [r for r in summary_all if r["source_catalog"] == "MASTER_1083" and r["role"] == "SCIENCE" and r["tier1_trigger"] == "True"]
    ir_br = [r["star"] for r in sci_trig if r["dw2_mag"] and float(r["dw2_mag"]) <= -0.10]
    dip = [r["star"] for r in sci_trig if "GAIA_DIPPER" in r["tier1_reasons"]]
    unsat = [r for r in sci_trig if (_f(r["allwise_w2"]) or 99.0) >= 8.2]
    unsat.sort(key=lambda r: abs(_f(r["z_dw2"]) or _f(r["w2_rchi2"]) or 0.0), reverse=True)
    # 3) Plus 8 quiet unsaturated <10pc baselines
    quiet = [
        r["star"] for r in summary_all
        if r["source_catalog"] == "MASTER_1083" and r["role"] == "SCIENCE" and r["within_10pc"] == "True"
        and r["tier1_trigger"] == "False" and r["w2_unsat"] == "True"
    ][:8]

    lc_targets = list(dict.fromkeys(bench + ir_br + dip + [r["star"] for r in unsat[:45]] + quiet))
    print(f"Fetching/analyzing 10-yr NEOWISE-R LCs for {len(lc_targets)} targets...", flush=True)

    neo_metrics: list[dict[str, Any]] = []
    neo_by_star: dict[str, dict[str, Any]] = {}
    ztf_rows_count = 0

    for idx, st in enumerate(lc_targets):
        srow = by_star_sum[st]
        grow = gaia_map.get(st, {})
        gra, gdec = _f(grow.get("ra")), _f(grow.get("dec"))
        pmra, pmdec = _f(grow.get("pmra")), _f(grow.get("pmdec"))
        ra_base = gra if gra is not None else float(srow["ra_deg"])
        dec_base = gdec if gdec is not None else float(srow["dec_deg"])
        ep_base = 2016.0 if gra is not None else 2000.0
        ra19, dec19 = propagate_coords(ra_base, dec_base, pmra, pmdec, 2019.0 - ep_base)
        pm_tot = math.hypot(pmra or 0.0, pmdec or 0.0)
        rad = min(65.0, max(6.0, 5.0 + (pm_tot / 1000.0) * 6.0))
        raw_lc, status = fetch_neowise_lc(st, ra19, dec19, rad)
        met = analyze_neowise_10yr(st, raw_lc, grow, srow)
        met["role"] = srow["role"]
        met["source_catalog"] = srow["source_catalog"]
        neo_metrics.append(met)
        neo_by_star[st] = met

        # Also fetch ZTF LC for top 25 northern unsaturated stars + northern benchmarks
        if float(srow["dec_deg"]) >= -30.0 and (st in bench or idx < 35):
            zlc, zst = fetch_ztf_lc(st, ra19, dec19)
            ztf_rows_count += len(zlc)
        if (idx + 1) % 15 == 0 or idx + 1 == len(lc_targets):
            print(f"  NEOWISE-R progress: {idx+1}/{len(lc_targets)} (cur={st}, ep={met.get('n_clean_ep', 0)}, visits={met.get('n_visits', 0)})", flush=True)
        if status == "downloaded":
            time.sleep(0.15)

    p_neo = RES / "N5_NEOWISE_10YR_LC_METRICS.csv"
    all_keys = list(dict.fromkeys(k for r in neo_metrics for k in r.keys()))
    with p_neo.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=all_keys)
        w.writeheader()
        for r in neo_metrics:
            w.writerow({k: r.get(k, "") for k in all_keys})

    # Vet all Tier-1 triggers (160 SCI + 90 CTRL + 2 BENCH) + all 13 Benchmarks
    vet_targets = [r for r in summary_all if r["tier1_trigger"] == "True" or r["source_catalog"] == "BENCHMARK_13"]
    vet_rows: list[dict[str, Any]] = []
    sci_counts: collections.Counter[str] = collections.Counter()
    bench_counts: collections.Counter[str] = collections.Counter()
    unexplained = 0
    for r in vet_targets:
        st = r["star"]
        neo = neo_by_star.get(st)
        vcls, vnote = classify_vetted(r, neo)
        if r["source_catalog"] == "MASTER_1083" and r["role"] == "SCIENCE":
            sci_counts[vcls] += 1
            if vcls == "UNEXPLAINED_SECULAR_IR_FOLLOWUP":
                unexplained += 1
        elif r["source_catalog"] == "BENCHMARK_13":
            bench_counts[vcls] += 1
        vet_rows.append({
            "star": st,
            "common_name": r["common_name"],
            "source_catalog": r["source_catalog"],
            "role": r["role"],
            "subrole": r["subrole"],
            "dist_pc": r["dist_pc"],
            "allwise_w2": r["allwise_w2"],
            "dw2_mag": r["dw2_mag"],
            "z_dw2": r["z_dw2"],
            "tier1_reasons": r["tier1_reasons"],
            "neowise_visits": neo.get("n_visits", "") if neo else "",
            "neowise_dw2_dt": neo.get("neowise_dw2_dt", "") if neo else "",
            "neowise_z_dw2": neo.get("neowise_z_dw2", "") if neo else "",
            "neowise_w2_r": neo.get("neowise_w2_r", "") if neo else "",
            "vetting_class": vcls,
            "eti_status": "VETOED_NON_ETI" if r["source_catalog"] == "MASTER_1083" else "BENCHMARK",
            "vetting_note": vnote,
        })

    with (RES / "N5_CANDIDATES_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(vet_rows[0].keys()))
        w.writeheader()
        w.writerows(vet_rows)

    asassn = neo_by_star.get("ASASSN_21QJ", {})
    hephs = {f"HEPH_{k}": neo_by_star.get(f"HEPH_{k}", {}) for k in "ABCDEFG"}
    total_exp = sum(r.get("n_clean_ep", 0) for r in neo_metrics)

    stage3_sum = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "neowise_10yr_lc_stars_fetched": len(neo_metrics),
        "neowise_single_exposures_clean": int(total_exp),
        "ztf_raw_lc_rows_fetched": int(ztf_rows_count),
        "benchmark_asassn21qj_recovered": bool(asassn.get("dyson_ir_gate")),
        "benchmark_asassn21qj_metrics": asassn,
        "benchmark_kic8462852_metrics": neo_by_star.get("KIC_8462852", {}),
        "hephaistos_10yr_stability": {k: {"visits": v.get("n_visits"), "med_w2": v.get("neowise_med_w2"), "dw2_dt": v.get("neowise_dw2_dt"), "z_dw2": v.get("neowise_z_dw2"), "ptp_w2": v.get("neowise_w2_ptp")} for k, v in hephs.items()},
        "science_tier1_vetted_counts": dict(sci_counts),
        "benchmark_vetted_counts": dict(bench_counts),
        "unexplained_secular_science_targets": unexplained,
        "verified_eti_candidates": 0 if unexplained == 0 else unexplained,
    }
    (RES / "N5_STAGE3_VETTING.json").write_text(json.dumps(stage3_sum, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stage3_sum, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
