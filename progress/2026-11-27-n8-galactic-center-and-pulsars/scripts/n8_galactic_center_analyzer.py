#!/usr/bin/env python3
"""Prospectively locked Milky Way Galactic Center & ATNF Pulsar analyzer (Spor N8)."""
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
WS = ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars"
INP = ROOT / "inputs_n8_20261127"
RES = WS / "results"

# Locked Prospective Thresholds
P1_MAX_NEG_P1 = -1.0e-17
P2_DEATHLINE_LOG_B_P2_MIN = 10.6
P3_ULTRA_LONG_P0_SEC = 15.0
P3_CONST_TOL_INT = 1.0e-6
P3_CONST_TOL_PI = 1.0e-5

G_MIN_SIG = 10.0
G1_MAX_PLGAM = 1.85
G1_MIN_CURV = 5.0
G2_MIN_VARIND = 100.0

INJECTION_SEED = 20261128


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


def angsep_deg(ra1: float, dec1: float, ra2: np.ndarray, dec2: np.ndarray) -> np.ndarray:
    r1, d1 = math.radians(ra1), math.radians(dec1)
    r2, d2 = np.radians(ra2), np.radians(dec2)
    ca = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2)
    return np.degrees(np.arccos(np.clip(ca, -1.0, 1.0)))


def jeffreys_f95(n_eff: float) -> float:
    return float(betaincinv(0.5, float(n_eff) + 0.5, 0.95)) if n_eff > 0 else 1.0


def uniform_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / (float(n_eff) + 1.0))) if n_eff > 0 else 1.0


def clopper_pearson_f95(n_eff: float) -> float:
    return 1.0 - (0.05 ** (1.0 / float(n_eff))) if n_eff > 0 else 1.0


def eval_pulsar(p0: float, p1: float, bsurf: float, s1400: float, s400: float) -> dict[str, Any]:
    trig_p1 = math.isfinite(p1) and (p1 < P1_MAX_NEG_P1)
    log_b_p2 = float("nan")
    trig_p2 = False
    has_radio = (math.isfinite(s1400) and s1400 > 0) or (math.isfinite(s400) and s400 > 0)
    if has_radio and math.isfinite(p0) and p0 > 0 and math.isfinite(bsurf) and bsurf > 0:
        log_b_p2 = math.log10(bsurf / (p0 ** 2))
        trig_p2 = log_b_p2 < P2_DEATHLINE_LOG_B_P2_MIN

    trig_p3 = False
    if math.isfinite(p0) and p0 > 0:
        if p0 >= P3_ULTRA_LONG_P0_SEC:
            trig_p3 = True
        elif p0 >= 0.1 and (abs(p0 - round(p0)) < P3_CONST_TOL_INT or abs(p0 - math.pi) < P3_CONST_TOL_PI):
            trig_p3 = True

    reasons = []
    if trig_p1:
        reasons.append("N8_PSR_SPINUP_ANOMALY")
    if trig_p2:
        reasons.append("N8_PSR_DEATHLINE_VIOLATION")
    if trig_p3:
        reasons.append("N8_PSR_ULTRA_LONG_OR_HARMONIC")
    return {
        "log_b_p2": round(log_b_p2, 4) if math.isfinite(log_b_p2) else "",
        "trig_p1": trig_p1,
        "trig_p2": trig_p2,
        "trig_p3": trig_p3,
        "triggered": bool(reasons),
        "reasons": "|".join(reasons),
    }


def eval_fermi(cl1: str, sig: float, plgam: float, curv: float, varind: float) -> dict[str, Any]:
    unassoc = cl1.strip().lower() in ("", "unk", "unid", "none", "---")
    trig_g1 = unassoc and math.isfinite(sig) and sig >= G_MIN_SIG and math.isfinite(plgam) and plgam < G1_MAX_PLGAM and math.isfinite(curv) and curv >= G1_MIN_CURV
    trig_g2 = unassoc and math.isfinite(sig) and sig >= G_MIN_SIG and math.isfinite(varind) and varind >= G2_MIN_VARIND
    reasons = []
    if trig_g1:
        reasons.append("N8_FERMI_UNASSOC_HARD_CURVED")
    if trig_g2:
        reasons.append("N8_FERMI_UNASSOC_EXTREME_VAR")
    return {
        "unassociated": unassoc,
        "trig_g1": trig_g1,
        "trig_g2": trig_g2,
        "triggered": bool(reasons),
        "reasons": "|".join(reasons),
    }


def run_injections() -> dict[str, Any]:
    rng = np.random.default_rng(INJECTION_SEED)
    # 400 synthetic field pulsar spin-up beacons (P1 levels)
    g_p1: dict[str, Any] = {}
    for p1_val in (-1e-18, -1e-17, -1e-16, -1e-15):
        rec = 0
        for _ in range(100):
            obs_p1 = float(p1_val + rng.normal(0.0, 2e-18))
            if eval_pulsar(0.05, obs_p1, 1e9, 0.5, float("nan"))["trig_p1"]:
                rec += 1
        g_p1[f"{p1_val:.0e}"] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    # 400 synthetic deathline violation beacons (log10(B/P^2))
    g_p2: dict[str, Any] = {}
    for lb in (11.2, 10.5, 9.8, 9.0):
        rec = 0
        for _ in range(100):
            p0 = float(rng.uniform(0.5, 10.0))
            log_bp2 = float(lb + rng.normal(0.0, 0.15))
            bsurf = (10.0 ** log_bp2) * (p0 ** 2)
            if eval_pulsar(p0, 1e-16, bsurf, 1.0, float("nan"))["trig_p2"]:
                rec += 1
        g_p2[str(lb)] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    # 400 synthetic Galactic Bulge unassociated hard-curved GeV beacons (Sig levels)
    g_f: dict[str, Any] = {}
    for sig_val in (5.0, 10.0, 20.0, 40.0):
        rec = 0
        for _ in range(100):
            obs_sig = float(sig_val + rng.normal(0.0, 1.2))
            if eval_fermi("", obs_sig, 1.5, 8.0, 25.0)["trig_g1"]:
                rec += 1
        g_f[str(int(sig_val))] = {"trials": 100, "recovered": rec, "completeness": round(rec / 100.0, 4)}

    c_p1 = sum(g_p1[k]["recovered"] for k in ("-1e-16", "-1e-15")) / 200.0
    c_p2 = sum(g_p2[k]["recovered"] for k in ("10.5", "9.8", "9.0")) / 300.0
    c_f = sum(g_f[k]["recovered"] for k in ("20", "40")) / 200.0
    return {
        "trials_total": 1200,
        "gate_p1_spinup": g_p1,
        "gate_p2_deathline": g_p2,
        "gate_g1_fermi_bulge": g_f,
        "completeness_p1_strong": round(c_p1, 4),
        "completeness_p2_below_deathline": round(c_p2, 4),
        "completeness_fermi_sig_ge_20": round(c_f, 4),
        "completeness_psr_mean": round(0.5 * (c_p1 + c_p2), 4),
    }


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    psr_rows = list(csv.DictReader((INP / "atnf/atnf_milky_way_pulsars.csv").open("r", encoding="utf-8")))
    fermi_rows = list(csv.DictReader((INP / "fermi/fermi_4fgl_galactic_bulge.csv").open("r", encoding="utf-8")))
    nvss_rows = list(csv.DictReader((INP / "radio/nvss_galactic_center.csv").open("r", encoding="utf-8")))
    csc_rows = list(csv.DictReader((INP / "xray/csc2_galactic_center.csv").open("r", encoding="utf-8")))

    psr_ra = np.array([_f(r["ra_deg"]) for r in psr_rows], dtype=float)
    psr_dec = np.array([_f(r["dec_deg"]) for r in psr_rows], dtype=float)
    nvss_ra = np.array([_f(r["ra_deg"]) for r in nvss_rows], dtype=float) if nvss_rows else np.array([])
    nvss_dec = np.array([_f(r["dec_deg"]) for r in nvss_rows], dtype=float) if nvss_rows else np.array([])
    csc_ra = np.array([_f(r["ra_deg"]) for r in csc_rows], dtype=float) if csc_rows else np.array([])
    csc_dec = np.array([_f(r["dec_deg"]) for r in csc_rows], dtype=float) if csc_rows else np.array([])

    psr_cat: list[dict[str, Any]] = []
    trig_rows: list[dict[str, Any]] = []
    n_gc_core = 0
    for r in psr_rows:
        glon = _f(r.get("GLON"), 180.0)
        glat = _f(r.get("GLAT"), 90.0)
        if glon > 180.0:
            glon -= 360.0
        in_gc_core = abs(glon) <= 5.0 and abs(glat) <= 2.0
        if in_gc_core:
            n_gc_core += 1

        ev = eval_pulsar(_f(r.get("P0")), _f(r.get("P1")), _f(r.get("Bsurf")), _f(r.get("S1400")), _f(r.get("S400")))
        out = {**r, "glon_signed": round(glon, 4), "in_gc_core": in_gc_core, **ev}
        psr_cat.append(out)
        if ev["triggered"]:
            trig_rows.append({
                "domain": "ATNF_PULSAR",
                "name": r["PSRJ"],
                "ra_deg": r["ra_deg"],
                "dec_deg": r["dec_deg"],
                "glon": r.get("GLON", ""),
                "glat": r.get("GLAT", ""),
                "p0_s": r.get("P0", ""),
                "p1": r.get("P1", ""),
                "bsurf": r.get("Bsurf", ""),
                "log_b_p2": ev["log_b_p2"],
                "assoc": r.get("Assoc", ""),
                "psr_type": r.get("Type", ""),
                "fermi_sig": "",
                "fermi_plgam": "",
                "fermi_curv": "",
                "fermi_varind": "",
                "fermi_cl1": "",
                "gc_counterparts": "",
                "trigger_reasons": ev["reasons"],
            })

    fermi_cat: list[dict[str, Any]] = []
    n_unassoc = 0
    for r in fermi_rows:
        ra, dec = _f(r["ra_deg"]), _f(r["dec_deg"])
        rad = max(_f(r.get("amaj95"), 0.05), 0.05)
        n_psr_m = int(np.sum(angsep_deg(ra, dec, psr_ra, psr_dec) <= rad)) if len(psr_ra) else 0
        n_nvss_m = int(np.sum(angsep_deg(ra, dec, nvss_ra, nvss_dec) <= rad)) if len(nvss_ra) else 0
        n_csc_m = int(np.sum(angsep_deg(ra, dec, csc_ra, csc_dec) <= rad)) if len(csc_ra) else 0
        curv = max(_f(r.get("SigCurv1"), 0.0), _f(r.get("SigCurv2"), 0.0))
        sig = _f(r.get("Sig"), 0.0)
        plgam = _f(r.get("PLGam"), 99.0)
        varind = _f(r.get("VarInd"), 0.0)
        ev = eval_fermi(r.get("Cl1", ""), sig, plgam, curv, varind)
        if ev["unassociated"]:
            n_unassoc += 1
        out = {**r, "psr_matches": n_psr_m, "nvss_matches": n_nvss_m, "csc2_matches": n_csc_m, "max_curv": round(curv, 3), **ev}
        fermi_cat.append(out)
        if ev["triggered"]:
            trig_rows.append({
                "domain": "FERMI_BULGE_4FGL",
                "name": r["4FGL"],
                "ra_deg": r["ra_deg"],
                "dec_deg": r["dec_deg"],
                "glon": r.get("GLON", ""),
                "glat": r.get("GLAT", ""),
                "p0_s": "",
                "p1": "",
                "bsurf": "",
                "log_b_p2": "",
                "assoc": r.get("Assoc1", ""),
                "psr_type": "",
                "fermi_sig": round(sig, 2),
                "fermi_plgam": round(plgam, 3),
                "fermi_curv": round(curv, 2),
                "fermi_varind": round(varind, 2),
                "fermi_cl1": r.get("Cl1", ""),
                "gc_counterparts": f"PSR={n_psr_m}|NVSS={n_nvss_m}|CSC2={n_csc_m}",
                "trigger_reasons": ev["reasons"],
            })

    with (RES / "N8_MILKY_WAY_PULSARS_CATALOG.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(psr_cat[0].keys()))
        w.writeheader()
        w.writerows(psr_cat)

    with (RES / "N8_BULGE_FERMI_CATALOG.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fermi_cat[0].keys()))
        w.writeheader()
        w.writerows(fermi_cat)

    trig_fields = [
        "domain", "name", "ra_deg", "dec_deg", "glon", "glat", "p0_s", "p1", "bsurf", "log_b_p2",
        "assoc", "psr_type", "fermi_sig", "fermi_plgam", "fermi_curv", "fermi_varind", "fermi_cl1",
        "gc_counterparts", "trigger_reasons",
    ]
    with (RES / "N8_STAGE2_TRIGGERS.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=trig_fields)
        w.writeheader()
        w.writerows(trig_rows)

    inj = run_injections()
    n_psr = len(psr_cat)
    n_fermi = len(fermi_cat)
    n_eff_psr = n_psr * inj["completeness_psr_mean"]

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
        "milky_way_pulsars_total": n_psr,
        "galactic_center_core_pulsars": n_gc_core,
        "fermi_bulge_sources_total": n_fermi,
        "fermi_bulge_unassociated": n_unassoc,
        "nvss_gc_radio_sources": len(nvss_rows),
        "csc2_gc_xray_sources": len(csc_rows),
        "stage2_triggers_total": len(trig_rows),
        "stage2_gate_counts": {
            "N8_PSR_SPINUP_ANOMALY": sum(1 for x in psr_cat if x["trig_p1"]),
            "N8_PSR_DEATHLINE_VIOLATION": sum(1 for x in psr_cat if x["trig_p2"]),
            "N8_PSR_ULTRA_LONG_OR_HARMONIC": sum(1 for x in psr_cat if x["trig_p3"]),
            "N8_FERMI_UNASSOC_HARD_CURVED": sum(1 for x in fermi_cat if x["trig_g1"]),
            "N8_FERMI_UNASSOC_EXTREME_VAR": sum(1 for x in fermi_cat if x["trig_g2"]),
        },
        "injections": inj,
        "bayesian_limits_zero_eti": {
            "all_mw_pulsars_raw": lim(n_psr),
            "all_mw_pulsars_eff": lim(n_eff_psr),
            "gc_core_pulsars": lim(n_gc_core),
            "fermi_bulge_all": lim(n_fermi),
            "fermi_bulge_unassociated": lim(n_unassoc),
        },
    }
    (RES / "N8_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
