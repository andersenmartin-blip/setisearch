#!/usr/bin/env python3
"""
Generate 6 publication-quality 300-DPI PNG figures for Spor N5
(SPOR_N5_10YR_SECULAR_IR_OPTICAL_1083) in WS/figures and
setisearch/progress/2026-11-27-n5-secular-ir-optical-1083/figures.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n5_20261127_secular_ir_optical_1083"
INP = ROOT / "inputs_n5_20261127"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch" / "progress" / "2026-11-27-n5-secular-ir-optical-1083" / "figures"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11.2,
    "axes.labelsize": 10.2,
    "xtick.labelsize": 9.2,
    "ytick.labelsize": 9.2,
    "legend.fontsize": 8.6,
    "figure.titlesize": 12.8,
})


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_WS / name, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_GIT / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}")


def load_visit_lc(star: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = INP / "neowise_lc" / f"{''.join(c if c.isalnum() or c in ('_','-') else '_' for c in star)}_neowise.csv"
    if not p.exists():
        return np.array([]), np.array([]), np.array([])
    pts = []
    for r in csv.DictReader(p.open(encoding="utf-8")):
        mjd, w1, w2 = _f(r.get("mjd")), _f(r.get("w1mpro")), _f(r.get("w2mpro"))
        qi, saa = _f(r.get("qi_fact")), _f(r.get("saa_sep"))
        moon = (r.get("moon_masked") or "00").strip()
        if mjd and w1 and w2 and (qi is None or qi >= 0.5) and (saa is None or saa >= 5.0) and ("1" not in moon):
            pts.append((mjd, w1, w2))
    if not pts:
        return np.array([]), np.array([]), np.array([])
    pts.sort(key=lambda x: x[0])
    visits, cur = [], [pts[0]]
    for pt in pts[1:]:
        if pt[0] - cur[-1][0] >= 60.0:
            visits.append(cur)
            cur = [pt]
        else:
            cur.append(pt)
    visits.append(cur)
    yrs, w1m, w2m = [], [], []
    for v in visits:
        if len(v) >= 2:
            yrs.append(2000.0 + (float(np.median([x[0] for x in v])) - 51544.5) / 365.25)
            w1m.append(float(np.median([x[1] for x in v])))
            w2m.append(float(np.median([x[2] for x in v])))
    return np.array(yrs), np.array(w1m), np.array(w2m)


def fig01_coverage_and_ruwe(master_rows: list[dict[str, Any]], neo_rows: list[dict[str, Any]]) -> None:
    fig = plt.figure(figsize=(12.6, 5.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0])

    ax1 = fig.add_subplot(gs[0, 0], projection="aitoff")
    ax1.grid(True, alpha=0.32, ls=":")
    neo_set = {r["star"] for r in neo_rows}

    ras = np.array([float(r["ra_deg"]) for r in master_rows if r["source_catalog"] == "MASTER_1083"])
    decs = np.array([float(r["dec_deg"]) for r in master_rows if r["source_catalog"] == "MASTER_1083"])
    ztfs = np.array([r["has_ztf_dr24"] == "True" for r in master_rows if r["source_catalog"] == "MASTER_1083"])
    lons = np.radians(((ras + 180.0) % 360.0) - 180.0)
    lats = np.radians(decs)

    ax1.scatter(lons[~ztfs], lats[~ztfs], s=14, c="#56B4E9", alpha=0.72, label=f"AllWISE / Gaia DR3 Only (n={(~ztfs).sum()})")
    ax1.scatter(lons[ztfs], lats[ztfs], s=18, c="#0072B2", alpha=0.85, label=f"ZTF DR24 + WISE + Gaia (n={ztfs.sum()})")

    # Highlight NEOWISE-R 10-yr LC stars & Benchmarks
    ns_ras = [float(r["ra_deg"]) for r in master_rows if r["star"] in neo_set and r["source_catalog"] == "MASTER_1083"]
    ns_decs = [float(r["dec_deg"]) for r in master_rows if r["star"] in neo_set and r["source_catalog"] == "MASTER_1083"]
    ax1.scatter(np.radians(((np.array(ns_ras) + 180.0) % 360.0) - 180.0), np.radians(ns_decs),
                s=42, marker="D", facecolors="none", edgecolors="#D55E00", lw=1.1, label=f"10-yr NEOWISE-R Vetted (n={len(ns_ras)})")

    bm_ras = [float(r["ra_deg"]) for r in master_rows if r["source_catalog"] == "BENCHMARK_13"]
    bm_decs = [float(r["dec_deg"]) for r in master_rows if r["source_catalog"] == "BENCHMARK_13"]
    ax1.scatter(np.radians(((np.array(bm_ras) + 180.0) % 360.0) - 180.0), np.radians(bm_decs),
                s=75, marker="*", c="#E69F00", edgecolors="#111111", lw=0.6, zorder=5, label="13 Benchmarks (incl. ASASSN-21qj, Heph A-G)")

    lons_line = np.linspace(-np.pi, np.pi, 360)
    ax1.plot(lons_line, np.full_like(lons_line, np.radians(-30.0)), color="#B00020", ls="--", lw=1.0, label="ZTF South Limit (-30 deg)")
    ax1.set_title("All-Sky Gaia + WISE + ZTF + NEOWISE-R Footprint (N=1,096)", pad=18)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=2, fontsize=8.0, framealpha=0.95)

    ax2 = fig.add_subplot(gs[0, 1])
    xs, ys, cs = [], [], []
    for r in master_rows:
        ru = _f(r.get("gaia_ruwe"))
        chi = _f(r.get("w2_rchi2"))
        if ru and chi and ru > 0 and chi > 0:
            xs.append(ru)
            ys.append(chi)
            cs.append("#D55E00" if r["tier1_trigger"] == "True" else "#0072B2")
    ax2.scatter(xs, ys, c=cs, s=18, alpha=0.72, edgecolors="#111111", lw=0.25)
    ax2.axvline(1.4, color="#444444", ls="--", lw=1.1, label="Gaia RUWE = 1.4 (Binary/Astrometric Threshold)")
    ax2.axhline(15.0, color="#D55E00", ls=":", lw=1.2, label="CatWISE2020 w2rchi2 = 15 (Tier-1 IR Var Gate)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Gaia DR3 RUWE")
    ax2.set_ylabel(r"CatWISE2020 $\chi^2_{\nu, W2}$")
    ax2.set_title("Astrometric Multiplicity (RUWE) vs. Multi-Epoch IR Scatter")
    ax2.grid(True, which="both", alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=8.0, framealpha=0.95)

    fig.suptitle("Spor N5 All-Sky Coverage & Gaia DR3 / CatWISE2020 Diagnostic Space", fontweight="bold")
    save_both(fig, "figN5_01_allsky_10yr_coverage_and_ruwe.png")


def fig02_ir_drift_vs_color(neo_rows: list[dict[str, Any]], vet_rows: list[dict[str, Any]], master_rows: list[dict[str, Any]]) -> None:
    vet_cls = {r["star"]: r["vetting_class"] for r in vet_rows}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.2), constrained_layout=True)

    # Panel 1: NEOWISE 10-yr dW2/dt vs d(W1-W2)/dt (unsaturated W2 >= 7.0)
    for r in neo_rows:
        if r.get("neowise_sat_w2") == "True" or not r.get("neowise_dw2_dt"):
            continue
        st = r["star"]
        if st == "WISE1049AB":
            continue  # PM aperture fly-through plotted cleanly in Fig 04
        dw2 = float(r["neowise_dw2_dt"])
        dcol = float(r["neowise_dcol_dt"])
        cls = vet_cls.get(st, "QUIET_BASELINE")
        if st == "ASASSN_21QJ":
            ax1.scatter(dcol, dw2, s=160, marker="*", c="#B00020", edgecolors="#111", lw=0.8, zorder=6, label="ASASSN-21qj (Collision Positive Benchmark)")
            ax1.annotate("ASASSN-21qj", xy=(dcol, dw2), xytext=(8, 6), textcoords="offset points", fontsize=8.5, fontweight="bold", color="#B00020")
        elif st.startswith("HEPH_"):
            ax1.scatter(dcol, dw2, s=48, marker="s", c="#E69F00", edgecolors="#111", lw=0.6, zorder=5)
        elif "YSO" in cls or "AGB" in cls:
            ax1.scatter(dcol, dw2, s=40, marker="^", c="#009E73", edgecolors="#111", lw=0.5, alpha=0.9)
            if dw2 <= -0.02:
                ax1.annotate(st, xy=(dcol, dw2), xytext=(5, -10), textcoords="offset points", fontsize=7.8)
        else:
            ax1.scatter(dcol, dw2, s=26, c="#0072B2", alpha=0.75, edgecolors="#111", lw=0.3)

    # Dummy legend entries for scatter groups
    ax1.scatter([], [], s=48, marker="s", c="#E69F00", edgecolors="#111", label="Hephaistos A-G (Flat 10-yr)")
    ax1.scatter([], [], s=40, marker="^", c="#009E73", edgecolors="#111", label="Known YSO / Dwarf Nova")
    ax1.scatter([], [], s=26, c="#0072B2", edgecolors="#111", label="Quiet / Flat Science & Control")

    ax1.axhline(-0.015, color="#B00020", ls="--", lw=1.2, label="Secular Brightening Gate (dW2/dt <= -0.015)")
    ax1.axvline(0.0, color="#666666", ls=":", lw=1.0)
    ax1.axhline(0.0, color="#666666", ls=":", lw=1.0)
    ax1.set_xlim(-0.018, 0.026)
    ax1.set_ylim(-0.060, 0.032)
    ax1.set_xlabel(r"NEOWISE-R 10-Yr Color Trend $d(W1 - W2)/dt$ (mag yr$^{-1}$, + = Reddening)")
    ax1.set_ylabel(r"NEOWISE-R 10-Yr W2 Slope $dW2/dt$ (mag yr$^{-1}$, - = Brightening)")
    ax1.set_title("10-Year NEOWISE-R Secular Slope vs. Thermal Reddening")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="upper right", fontsize=7.8, framealpha=0.95)

    # Panel 2: AllWISE -> CatWISE dW2 vs d(W1-W2) across unsaturated Science stars
    for r in master_rows:
        if r["source_catalog"] != "MASTER_1083" or r["w2_unsat"] != "True" or not r.get("dw2_mag") or not r.get("dcolor_w1_w2"):
            continue
        dw2 = float(r["dw2_mag"])
        dcol = float(r["dcolor_w1_w2"])
        col = "#D55E00" if r["tier1_trigger"] == "True" else "#0072B2"
        ax2.scatter(dcol, dw2, s=16, c=col, alpha=0.7)
    ax2.scatter([], [], s=24, c="#0072B2", label="Quiescent Unsaturated Stars")
    ax2.scatter([], [], s=24, c="#D55E00", label="Tier-1 Triggers (PM/YSO/Evolved)")
    ax2.axhline(-0.12, color="#B00020", ls="--", lw=1.2, label=r"Tier-1 Brightening Gate ($\Delta W2 \leq -0.12$ mag)")
    ax2.axhline(0.0, color="#666", ls=":", lw=0.9)
    ax2.axvline(0.0, color="#666", ls=":", lw=0.9)
    ax2.set_xlim(-1.5, 2.5)
    ax2.set_ylim(-1.2, 3.2)
    ax2.set_xlabel(r"AllWISE $\to$ CatWISE2020 Color Shift $\Delta(W1 - W2)$ (mag)")
    ax2.set_ylabel(r"AllWISE $\to$ CatWISE2020 Shift $\Delta W2$ (mag)")
    ax2.set_title("Baseline AllWISE-to-CatWISE Mid-IR Diagnostic (Unsaturated W2 >= 7)")
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=8.2, framealpha=0.95)

    fig.suptitle("10-Year Mid-IR Brightening & Thermal Reddening Diagnostics (Zero Unexplained Science Drift)", fontweight="bold")
    save_both(fig, "figN5_02_10yr_ir_drift_vs_optical_trend.png")


def fig03_benchmarks_and_hephaistos(neo_rows: list[dict[str, Any]]) -> None:
    targets = [
        ("ASASSN_21QJ", "ASASSN-21qj (Collision: W2 Jump -0.87 mag)"),
        ("KIC_8462852", "KIC 8462852 (Boyajian's Star: Flat IR)"),
        ("KH_15D", "KH 15D (Circumbinary Occulter)"),
        ("HEPH_A", "Hephaistos A (10.4-yr Flat IR)"),
        ("HEPH_D", "Hephaistos D (10.5-yr Flat IR)"),
        ("HEPH_G", "Hephaistos G (Radio AGN Blend: Flat IR)"),
    ]
    by_s = {r["star"]: r for r in neo_rows}
    fig, axes = plt.subplots(2, 3, figsize=(13.0, 6.4), constrained_layout=True)
    for ax, (st, ttl) in zip(axes.flat, targets):
        yrs, w1, w2 = load_visit_lc(st)
        if len(yrs) > 0:
            ax.plot(yrs, w1, "o-", ms=4, lw=1.2, color="#0072B2", label="W1 (3.4 um)")
            ax.plot(yrs, w2, "s-", ms=4, lw=1.3, color="#D55E00", label="W2 (4.6 um)")
            ax.invert_yaxis()
        met = by_s.get(st, {})
        dw2s = met.get("neowise_dw2_dt", "")
        zs = met.get("neowise_z_dw2", "")
        sub_txt = f"dW2/dt={dw2s} mag/yr (Z={zs})" if dw2s != "" else f"Periodic Disk Eclipses (Visits={len(yrs)}, p2p>3 mag)"
        ax.set_title(f"{ttl}\n{sub_txt}", fontsize=8.8)
        ax.grid(True, alpha=0.25, ls=":")
        ax.legend(loc="best", fontsize=7.5)
        ax.set_xlabel("Year")
        ax.set_ylabel("Mag (Vega)")
    fig.suptitle("NEOWISE-R 10-Year (2014-2024) Semi-Annual Lightcurves: Benchmarks & Hephaistos Candidates", fontweight="bold")
    save_both(fig, "figN5_03_neowise_10yr_benchmark_and_hephaistos.png")


def fig04_science_vetting(neo_rows: list[dict[str, Any]], summary: dict[str, Any], s3: dict[str, Any]) -> None:
    targets = [
        ("J160901", "2MASS J16090141 (Upper Sco YSO Disk)"),
        ("SSCYG", "SS Cygni (Dwarf Nova Cataclysmic)"),
        ("OGLETR111", "OGLE-TR-111 (NEOWISE Flat; Crowded Blend)"),
        ("WISE1049AB", "Luhman 16AB (2.78\"/yr PM Aperture Fly-Through)"),
    ]
    by_s = {r["star"]: r for r in neo_rows}
    fig = plt.figure(figsize=(12.8, 6.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 1.3])
    for idx, (st, ttl) in enumerate(targets):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        yrs, w1, w2 = load_visit_lc(st)
        if len(yrs) > 0:
            ax.plot(yrs, w1, "o-", ms=4, lw=1.2, color="#0072B2", label="W1 (3.4 um)")
            ax.plot(yrs, w2, "s-", ms=4, lw=1.3, color="#D55E00", label="W2 (4.6 um)")
            ax.invert_yaxis()
        met = by_s.get(st, {})
        ax.set_title(f"{ttl}\nVisits={met.get('n_visits','')}, p2p={met.get('neowise_w2_ptp','')} mag", fontsize=8.8)
        ax.grid(True, alpha=0.25, ls=":")
        ax.legend(loc="best", fontsize=7.5)
        if idx // 2 == 1:
            ax.set_xlabel("Year")
        if idx % 2 == 0:
            ax.set_ylabel("Mag (Vega)")

    ax_f = fig.add_subplot(gs[:, 2])
    vc = s3["science_tier1_vetted_counts"]
    stages = [
        ("Master Catalog (All)", 1083, "#0072B2"),
        ("Science Targets", 787, "#0072B2"),
        ("Tier-1 Science Triggers", summary["tier1_triggers_master_science"], "#E69F00"),
        ("WISE Bright Sat / PM", vc.get("WISE_BRIGHT_SATURATION_OR_PM_DRIFT", 0) + vc.get("HIGH_PM_OR_UNWISE_CATALOG_ARTIFACT", 0), "#999999"),
        ("NEOWISE Flat / Blend", vc.get("NEOWISE_10YR_FLAT_OR_CROWDED_BLEND", 0), "#56B4E9"),
        ("Known YSO / Disk / AGB", vc.get("KNOWN_YSO_PROTOSTAR_OR_DISK_VAR", 0) + vc.get("KNOWN_AGB_NOVA_OR_SYMBIOTIC_VAR", 0), "#009E73"),
        ("Known Flare / Binary", vc.get("KNOWN_ACTIVE_FLARE_OR_BINARY_NSS", 0), "#CC79A7"),
        ("Verified ETI Candidates", s3["verified_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    ax_f.barh(ys, vals, color=[c for _, _, c in stages], height=0.62, edgecolor="#111")
    ax_f.set_xscale("log")
    ax_f.set_xlim(0.5, 4000)
    ax_f.set_yticks(ys)
    ax_f.set_yticklabels([s for s, _, _ in stages], fontsize=8.8)
    for y, (_, v, _) in zip(ys, stages):
        ax_f.text(max(v, 0.8) * 1.18, y, f"{v}", va="center", fontweight="bold", fontsize=9.0)
    ax_f.set_xlabel("Count (log scale)")
    ax_f.set_title("Spor N5 Vetting Funnel\n(1,083 -> 160 -> 0 ETI)")
    ax_f.grid(axis="x", alpha=0.28, ls=":")

    fig.suptitle("Stage 3 10-Year NEOWISE-R Vetting of Key Science Triggers & Secular Funnel", fontweight="bold")
    save_both(fig, "figN5_04_science_triggers_neowise_ztf_vetting.png")


def fig05_injections_and_limits(summary: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.1), constrained_layout=True)

    ig = summary["injection_grid"]
    rates = sorted(ig.keys(), key=lambda k: float(k))
    xs = np.array([float(k) for k in rates])
    ys = np.array([ig[k]["completeness"] * 100.0 for k in rates])
    errs = 100.0 * np.sqrt(np.clip((ys / 100.0) * (1.0 - ys / 100.0) / 200.0, 0.0, 1.0))

    ax1.errorbar(xs, ys, yerr=errs, fmt="-o", color="#0072B2", lw=2.0, ms=7, capsize=4, label="1,200-Trial Secular Injection Recovery (200/bin)")
    ax1.axvline(0.04, color="#D55E00", ls=":", lw=1.4, label=f"0.04 mag/yr ({ig['0.04']['completeness']*100:.1f}% Single-Star / >=92.3% above)")
    for x, y in zip(xs, ys):
        ax1.text(x, y + 3.5, f"{y:.1f}%", ha="center", va="bottom", fontsize=8.4)
    ax1.set_xscale("log")
    ax1.set_ylim(-5, 114)
    ax1.set_xlabel(r"Injected 10-Year Secular Brightening Rate $|dW2/dt|$ (mag yr$^{-1}$)")
    ax1.set_ylabel("Catalog Detection Completeness (%)")
    ax1.set_title("10-Year Secular Megastructure Injection Recovery (N=1,200)")
    ax1.grid(True, which="both", alpha=0.28, ls=":")
    ax1.legend(loc="lower right", fontsize=8.2)

    bl = summary["bayesian_limits_zero_eti"]
    cohorts = [
        ("All Stars\n(n=1,083)", bl["all_1083_stars_gaia_ir"]),
        ("Gaia DR3\n(n=1,041)", bl["gaia_dr3_monitored"]),
        ("Science\n(n=787)", bl["science_787_stars"]),
        ("<10 pc\n(n=267)", bl["within_10pc_267_stars"]),
        ("Unsat IR\n(n_eff=259)", bl["science_unsaturated_ir_10yr"]),
        ("ZTF DR24\n(n=218)", bl["ztf_dr24_optical_monitored"]),
    ]
    x = np.arange(len(cohorts))
    w = 0.25
    jf = [c[1]["jeffreys_f95_pct"] for c in cohorts]
    uf = [c[1]["uniform_f95_pct"] for c in cohorts]
    cp = [c[1]["clopper_pearson_f95_pct"] for c in cohorts]

    ax2.bar(x - w, jf, width=w, color="#0072B2", edgecolor="#111", lw=0.6, label="Jeffreys Beta(0.5, N+0.5)")
    ax2.bar(x, uf, width=w, color="#E69F00", edgecolor="#111", lw=0.6, label="Uniform Bayes Beta(1, N+1)")
    ax2.bar(x + w, cp, width=w, color="#009E73", edgecolor="#111", lw=0.6, label="Clopper-Pearson 95%")
    for xi, jv, uv in zip(x, jf, uf):
        ax2.text(xi - w, jv + 0.02, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=45)
        ax2.text(xi + 0.05, uv + 0.02, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=45)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.4)
    ax2.set_ylim(0, 1.65)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ on Secular ETI (%)")
    ax2.set_title(r"Zero-Detection 95% Bayesian Prevalence Upper Limits ($f_{95}$)")
    ax2.grid(axis="y", alpha=0.28, ls=":")
    ax2.legend(loc="upper left", fontsize=8.3)

    fig.suptitle("Spor N5 Secular Injection Calibration & Bayesian Null Constraints", fontweight="bold")
    save_both(fig, "figN5_05_injection_recovery_and_bayesian_f95.png")


def fig06_unified_landscape(summary: dict[str, Any]) -> None:
    campaigns = [
        ("Spor R1+R2: Rubin V2 DDF\n(n_eff=254 LONO /fp)", 0.8800, "Optical Transient (days)", "#56B4E9"),
        ("Spor N1B: Blind Dysons\n(n=260 DDF, gamma>=0.05)", 0.7427, "Static MIR Waste Heat", "#E69F00"),
        ("Spor N1C: VASCO Gaia\n(n=1,197 Vanishing Stars)", 0.1603, "Multi-Decade Disappearance", "#009E73"),
        ("Spor N2: Rubin SSOFT\n(n=1,368 High-Obs Orbits)", 0.1403, "Solar System Anomalies", "#CC79A7"),
        ("Spor N3: Rubin V2+V3\n(n_eff=1,809 LONO /fp)", 0.1133, "2,100-Star Optical DDF", "#0072B2"),
        ("Spor N4: Radio Bridge\n(n=1,083, 54 MHz-3 GHz)", summary["bayesian_limits_zero_eti"]["all_1083_stars_gaia_ir"]["jeffreys_f95_pct"], "71.92 EM Octaves", "#D55E00"),
        ("Spor N5: 10-Yr Secular\n(n=1,083, IR + Optical)", summary["bayesian_limits_zero_eti"]["all_1083_stars_gaia_ir"]["jeffreys_f95_pct"], "10-Yr Swarm Construction", "#B00020"),
    ]
    fig, ax = plt.subplots(figsize=(11.8, 5.5), constrained_layout=True)
    ys = np.arange(len(campaigns))[::-1]
    vals = [c[1] for c in campaigns]
    cols = [c[3] for c in campaigns]
    ax.barh(ys, vals, height=0.62, color=cols, edgecolor="#111", lw=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([c[0] for c in campaigns], fontsize=9.0)
    ax.set_xlim(0, 1.48)
    for y, (_, v, desc, _) in zip(ys, campaigns):
        ax.text(v + 0.018, y, f"Jeffreys f95 = {v:.4f}%  [{desc} -> 0 ETI]", va="center", ha="left", fontsize=8.8)
    ax.set_xlabel(r"95% Jeffreys Bayesian Upper Limit $f_{95}$ (%) on ETI Technosignature Prevalence (Zero Detections)")
    ax.set_title("Unified SETI Constraints Across Extended Campaigns R1+R2 & N1-N5 (All Verified Zero ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.28, ls=":")
    save_both(fig, "figN5_06_unified_5track_seti_landscape_n1_to_n5.png")


def main() -> int:
    summary = json.loads((RES / "N5_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N5_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    master_rows = list(csv.DictReader((RES / "N5_MASTER_1096_SECULAR_SUMMARY.csv").open(encoding="utf-8")))
    neo_rows = list(csv.DictReader((RES / "N5_NEOWISE_10YR_LC_METRICS.csv").open(encoding="utf-8")))
    vet_rows = list(csv.DictReader((RES / "N5_CANDIDATES_VETTED.csv").open(encoding="utf-8")))

    fig01_coverage_and_ruwe(master_rows, neo_rows)
    fig02_ir_drift_vs_color(neo_rows, vet_rows, master_rows)
    fig03_benchmarks_and_hephaistos(neo_rows)
    fig04_science_vetting(neo_rows, summary, s3)
    fig05_injections_and_limits(summary)
    fig06_unified_landscape(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
