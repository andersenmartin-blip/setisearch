#!/usr/bin/env python3
"""Generate 6 publication-quality 300-DPI PNGs for Spor N9 (Gaia DR3 Dark Companions)."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n9_20261127_gaia_dr3_dark_companions"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch/progress/2026-11-27-n9-gaia-dr3-dark-companions/figures"

plt.rcParams.update({
    "font.size": 9.4,
    "axes.titlesize": 10.6,
    "axes.labelsize": 9.8,
    "xtick.labelsize": 8.6,
    "ytick.labelsize": 8.6,
    "legend.fontsize": 8.0,
    "figure.titlesize": 12.2,
})


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    for d in (FIG_WS, FIG_GIT):
        fig.savefig(d / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}", flush=True)


def fig01_cmd_and_25yr_coverage(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    mw = [r for r in cat if r["is_bh_benchmark"] == "False" and math.isfinite(_f(r["bp_rp"])) and math.isfinite(_f(r["phot_g_mean_mag"])) and _f(r["parallax"], 0) > 0]
    trig_st = {r["star"] for r in vet if r["is_bh_benchmark"] == "False"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    # Panel 1: Gaia DR3 Observational CMD
    def mg_bprp(rows):
        bprp = np.array([_f(r["bp_rp"]) for r in rows])
        mg = np.array([_f(r["phot_g_mean_mag"]) + 5.0 * math.log10(_f(r["parallax"]) / 100.0) for r in rows])
        return bprp, mg

    q_rows = [r for r in mw if r["star"] not in trig_st]
    t_rows = [r for r in mw if r["star"] in trig_st]
    ax1.scatter(*mg_bprp(q_rows), s=14, c="#0072B2", alpha=0.55, label=f"Quiet Milky Way Stars (n={len(q_rows)})")
    ax1.scatter(*mg_bprp(t_rows), s=44, marker="*", c="#D55E00", edgecolors="#111", lw=0.45, zorder=5, label=f"Dynamical / RUWE Triggers -> 0 ETI (n={len(t_rows)})")
    bh1 = [r for r in cat if r["star"] == "GAIA_BH1" and math.isfinite(_f(r["bp_rp"]))]
    if bh1:
        ax1.scatter(*mg_bprp(bh1), s=150, marker="D", c="#B00020", edgecolors="#111", lw=0.7, zorder=6, label="Gaia BH1 Positive Benchmark")

    ax1.invert_yaxis()
    ax1.set_xlim(-0.5, 5.2)
    ax1.set_ylim(18.0, -7.5)
    ax1.set_xlabel(r"Gaia DR3 Color $G_{\mathrm{BP}} - G_{\mathrm{RP}}$ (mag)")
    ax1.set_ylabel(r"Absolute Magnitude $M_G$ (mag)")
    ax1.set_title("Gaia DR3 Color-Magnitude Diagram Across Pure Milky Way Sample")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="lower left", fontsize=7.8, framealpha=0.95)

    # Panel 2: Distance vs 25-year Kervella M2(10 AU) sensitivity
    kv = [r for r in mw if math.isfinite(_f(r["kervella_m2_10au_mjup"])) and _f(r["kervella_m2_10au_mjup"]) > 0]
    kv_q = [r for r in kv if r["star"] not in trig_st]
    kv_t = [r for r in kv if r["star"] in trig_st]
    ax2.scatter([_f(r["dist_pc"]) for r in kv_q], [_f(r["kervella_m2_10au_mjup"]) for r in kv_q], s=16, c="#009E73", alpha=0.6, label=f"25-Yr Normal Baseline (n={len(kv_q)})")
    ax2.scatter([_f(r["dist_pc"]) for r in kv_t], [_f(r["kervella_m2_10au_mjup"]) for r in kv_t], s=48, marker="*", c="#D55E00", edgecolors="#111", lw=0.45, zorder=5, label=f"PMa Dynamical Triggers -> 0 ETI (n={len(kv_t)})")
    ax2.axhline(1466.0, color="#B00020", ls="--", lw=1.2, label=r"Chandrasekhar Mass ($1.4\,M_\odot \approx 1,466\,M_{\mathrm{Jup}}$)")
    ax2.axhline(80.0, color="#0072B2", ls=":", lw=1.1, label=r"Hydrogen-Burning Limit ($\sim 80\,M_{\mathrm{Jup}}$)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(1.2, 600.0)
    ax2.set_ylim(0.2, 5000.0)
    ax2.set_xlabel("Heliocentric Distance d (pc)")
    ax2.set_ylabel(r"Kervella 10 AU Companion Mass Proxy $M_2$ ($M_{\mathrm{Jup}}$)")
    ax2.set_title("25-Year Hipparcos-Gaia Companion Mass Diagnostic (n=529)")
    ax2.grid(True, which="both", alpha=0.22, ls=":")
    ax2.legend(loc="lower right", fontsize=7.6, framealpha=0.95)

    fig.suptitle("Spor N9: Pure Milky Way Gaia DR3 CMD & 25-Year Dynamical Baseline (996 Stars)", fontweight="bold")
    save_both(fig, "figN9_01_milky_way_cmd_and_pma_mass_plane.png")


def fig02_hgca_vs_kervella(cat: list[dict[str, Any]]) -> None:
    mw = [r for r in cat if r["is_bh_benchmark"] == "False" and math.isfinite(_f(r["hgca_chi2"])) and math.isfinite(_f(r["kervella_snr"]))]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    nontrig = [r for r in mw if r["triggered"] == "False"]
    trig = [r for r in mw if r["triggered"] == "True"]
    ax1.scatter([max(0.05, _f(r["kervella_snr"])) for r in nontrig], [max(0.05, _f(r["hgca_chi2"])) for r in nontrig], s=16, c="#0072B2", alpha=0.6, label=f"Dynamically Quiet (n={len(nontrig)})")
    ax1.scatter([max(0.05, _f(r["kervella_snr"])) for r in trig], [max(0.05, _f(r["hgca_chi2"])) for r in trig], s=50, marker="*", c="#D55E00", edgecolors="#111", lw=0.45, zorder=5, label=f"25-Yr Binary/Planet/AGB Pulls (n={len(trig)})")
    ax1.axvline(10.0, color="#B00020", ls="--", lw=1.2, label="Kervella PMa SNR >= 10")
    ax1.axhline(50.0, color="#D55E00", ls=":", lw=1.2, label="Brandt HGCA chi2 >= 50")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Kervella Hipparcos-Gaia PMa SNR")
    ax1.set_ylabel(r"Brandt HGCA Acceleration $\chi^2$")
    ax1.set_title("Cross-Calibration of Independent 25-Yr Acceleration Catalogs")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="upper left", fontsize=7.8)

    # Panel 2: Gaia RUWE vs Gmag (D3 Gate)
    all_g = [r for r in cat if r["is_bh_benchmark"] == "False" and math.isfinite(_f(r["ruwe"])) and math.isfinite(_f(r["phot_g_mean_mag"]))]
    gq = [r for r in all_g if r["trig_d3"] == "False"]
    gt = [r for r in all_g if r["trig_d3"] == "True"]
    ax2.scatter([_f(r["phot_g_mean_mag"]) for r in gq], [_f(r["ruwe"]) for r in gq], s=14, c="#009E73", alpha=0.55, label=f"Normal Single/Quiet RUWE (n={len(gq)})")
    ax2.scatter([_f(r["phot_g_mean_mag"]) for r in gt], [_f(r["ruwe"]) for r in gt], s=50, marker="^", c="#D55E00", edgecolors="#111", lw=0.5, zorder=5, label=f"Resolved/Disk/Binary RUWE >= 2.5 (n={len(gt)})")
    ax2.axhline(2.5, color="#B00020", ls="--", lw=1.2, label="Gate D3 RUWE >= 2.5")
    ax2.axvline(5.0, color="#777777", ls=":", lw=1.1, label="Bright Saturation Cut G < 5.0")
    ax2.set_yscale("log")
    ax2.set_xlim(1.5, 19.5)
    ax2.set_ylim(0.5, 65.0)
    ax2.set_xlabel("Gaia DR3 G Magnitude (mag)")
    ax2.set_ylabel("Gaia DR3 RUWE")
    ax2.set_title("Astrometric Goodness-of-Fit (RUWE) vs. Apparent Brightness")
    ax2.grid(True, which="both", alpha=0.22, ls=":")
    ax2.legend(loc="upper right", fontsize=7.7)

    fig.suptitle("25-Year Proper-Motion Anomaly & Gaia DR3 Astrometric Wobble Diagnostics", fontweight="bold")
    save_both(fig, "figN9_02_hgca_kervella_and_ruwe_diagnostics.png")


def fig03_nss_dark_mass_plane(cat: list[dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(11.2, 5.2), constrained_layout=True)

    nss = [r for r in cat if r["in_tbooc"] == "True" or r["in_tbosb1"] == "True"]
    sci_nss = [r for r in nss if r["is_bh_benchmark"] == "False"]
    bh1 = [r for r in nss if r["star"] == "GAIA_BH1"]

    def get_m(r):
        return _f(r["m2_ast_proxy_msun"], _f(r["fm_msun"], 0.01))

    if sci_nss:
        ax.scatter([_f(r["nss_period_d"], 100.0) for r in sci_nss], [get_m(r) for r in sci_nss],
                   s=95, c="#0072B2", edgecolors="#111", lw=0.6, zorder=4, label=f"Milky Way NSS Stellar/BD Binaries (n={len(sci_nss)})")
        for r in sci_nss:
            ax.annotate(r["star"], xy=(_f(r["nss_period_d"], 100.0), get_m(r)), xytext=(6, 4), textcoords="offset points", fontsize=8.2)
    if bh1:
        ax.scatter([_f(bh1[0]["nss_period_d"])], [get_m(bh1[0])],
                   s=190, marker="D", c="#B00020", edgecolors="#111", lw=0.8, zorder=6, label="Positive Benchmark Recovered: Gaia BH1 (185.8 d, 11.1 Msun proxy)")
        ax.annotate("GAIA BH1 (Positive BH Control)", xy=(_f(bh1[0]["nss_period_d"]), get_m(bh1[0])), xytext=(-150, -14), textcoords="offset points", fontsize=8.5, fontweight="bold", color="#8B0000")

    ax.axhline(1.4, color="#B00020", ls="--", lw=1.4, label=r"Chandrasekhar Dark Compact-Object Gate ($M_2 \geq 1.4\,M_\odot$): 0 Science Triggers")
    ax.axhline(0.5, color="#D55E00", ls=":", lw=1.2, label=r"Spectroscopic Mass Function Gate ($f(M) \geq 0.5\,M_\odot$)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1.0, 2500.0)
    ax.set_ylim(5e-5, 40.0)
    ax.set_xlabel("Gaia DR3 NSS Orbital Period (days)")
    ax.set_ylabel(r"Dark Companion Mass Proxy $M_2$ / $f(M)$ ($M_\odot$)")
    ax.set_title("Gaia DR3 Two-Body Dark Mass Plane: Gaia BH1 Benchmark vs. Milky Way Cohort (0 Dark ETI)")
    ax.grid(True, which="both", alpha=0.25, ls=":")
    ax.legend(loc="upper left", fontsize=8.0, framealpha=0.95)
    save_both(fig, "figN9_03_gaia_nss_dark_companion_mass_plane.png")


def fig04_veto_funnel(s2: dict[str, Any], s3: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(11.6, 5.4), constrained_layout=True)
    vc = s3["vetting_class_counts"]
    stages = [
        ("Pure Milky Way Master Stars", s2["pure_milky_way_stars_total"], "#0072B2"),
        ("Gaia DR3 Astrometry Matched", s2["gaia_dr3_matched"], "#56B4E9"),
        ("25-Yr Hipparcos-Gaia (HGCA/Kerv.)", s2["baseline_25yr_hgca_kervella_matched"], "#009E73"),
        ("Positive Benchmark (Gaia BH1)", vc.get("POSITIVE_BH_BENCHMARK_RECOVERED", 0), "#CC79A7"),
        ("Science Dark-Mass Gate D1 (>=1.4 Msun)", s3["science_dark_mass_d1_triggers"], "#B00020"),
        ("Stage 2 Sci Triggers (PMa / RUWE)", s2["stage2_triggers_science_mw"], "#E69F00"),
        ("Luminous Binaries / Multiples", vc.get("KNOWN_LUMINOUS_STELLAR_BINARY_OR_SATURATION", 0) + vc.get("RESOLVED_OR_NSS_LUMINOUS_BINARY", 0), "#D55E00"),
        ("Exoplanets & Brown Dwarfs", vc.get("KNOWN_EXOPLANET_OR_BROWN_DWARF_PULL", 0), "#009E73"),
        ("YSO Disk / AGB Jitter & Controls", vc.get("YSO_DISK_OR_AGB_PHOTOCENTER_JITTER", 0) + vc.get("CALIBRATION_CONTROL_BINARY_OR_EVOLVED", 0), "#999999"),
        ("Verified Milky Way Dark ETI", s3["verified_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    ax.barh(ys, vals, height=0.62, color=[c for _, _, c in stages], edgecolor="#111")
    ax.set_xscale("log")
    ax.set_xlim(0.5, 2500)
    ax.set_yticks(ys)
    ax.set_yticklabels([s for s, _, _ in stages], fontsize=8.8)
    for y, (_, v, _) in zip(ys, stages):
        ax.text(max(v, 0.85) * 1.15, y, f"{v}", va="center", fontweight="bold", fontsize=9.0)
    ax.set_xlabel("Milky Way Stars (log scale)")
    ax.set_title("Spor N9 Forensic Astrometric Vetting Funnel (996 MW Stars -> 127 PMa/RUWE -> 0 Dark ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.25, ls=":")
    save_both(fig, "figN9_04_astrometric_vetting_funnel.png")


def fig05_injections_and_f95(s2: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    inj = s2["injections"]
    x = np.array([1, 2, 3, 4])
    y1 = [inj["gate_d1_dark_mass"][k]["completeness"] * 100.0 for k in ("0.1", "0.5", "2.0", "6.0")]
    y2 = [inj["gate_d2_25yr_pma"][k]["completeness"] * 100.0 for k in ("3", "10", "25", "60")]
    y3 = [inj["gate_d3_ruwe_accel"][k]["completeness"] * 100.0 for k in ("1.5", "2.5", "5.0", "12.0")]

    ax1.plot(x, y1, "-o", lw=2.0, color="#B00020", label=f"D1 Dark Mass Orbit (>=0.5 Msun: {inj['completeness_d1_ge_0p5msun']*100:.1f}%)")
    ax1.plot(x, y2, "-s", lw=2.0, color="#0072B2", label=f"D2 25-Yr PMa Pull (SNR>=25: {inj['completeness_d2_snr_ge_25']*100:.1f}%)")
    ax1.plot(x, y3, "-^", lw=2.0, color="#009E73", label=f"D3 RUWE Wobble (>=2.5: {inj['completeness_d3_ruwe_ge_2p5']*100:.1f}%)")
    ax1.axvline(2.0, color="#555", ls=":", lw=1.2, label=f"Nominal Gate (Mean Eff={inj['completeness_mean_astrometry']*100:.1f}%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["Sub-Thresh", "Gate Edge", "Moderate", "Strong"], fontsize=8.4)
    ax1.set_ylim(-5, 110)
    ax1.set_ylabel("Injection Recovery Completeness (%)")
    ax1.set_title("1,200-Trial Dark-Companion & Dynamical Pull Injections")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="lower right", fontsize=7.6)

    bl = s2["bayesian_limits_zero_eti"]
    cohorts = [
        ("Pure MW\nRaw (996)", bl["all_pure_mw_996_raw"]),
        ("Pure MW\nEff (873.2)", bl["all_pure_mw_eff"]),
        ("25-Yr PMa\n(529)", bl["pma_25yr_baseline"]),
        ("Exoplanet\nHosts (327)", bl["exoplanet_hosts"]),
        ("<10 pc\n(267)", bl["within_10pc"]),
    ]
    bx = np.arange(len(cohorts))
    w = 0.25
    jf = [c[1]["jeffreys_f95_pct"] for c in cohorts]
    uf = [c[1]["uniform_f95_pct"] for c in cohorts]
    cp = [c[1]["clopper_pearson_f95_pct"] for c in cohorts]
    ax2.bar(bx - w, jf, width=w, color="#0072B2", edgecolor="#111", lw=0.6, label="Jeffreys Beta(0.5, N+0.5)")
    ax2.bar(bx, uf, width=w, color="#E69F00", edgecolor="#111", lw=0.6, label="Uniform Bayes Beta(1, N+1)")
    ax2.bar(bx + w, cp, width=w, color="#009E73", edgecolor="#111", lw=0.6, label="Clopper-Pearson 95%")
    for xi, jv, uv in zip(bx, jf, uf):
        ax2.text(xi - w, jv + 0.03, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
        ax2.text(xi + 0.05, uv + 0.03, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
    ax2.set_xticks(bx)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.2)
    ax2.set_ylim(0, 1.45)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ (%)")
    ax2.set_title("Milky Way Dynamical Zero-ETI 95% Prevalence Bounds")
    ax2.grid(axis="y", alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=7.8)

    fig.suptitle("Spor N9 Astrometric Injection Calibration & Milky Way Dark-Companion Bounds", fontweight="bold")
    save_both(fig, "figN9_05_injection_recovery_and_bayesian_f95.png")


def fig06_grand_milky_way_synthesis(s2: dict[str, Any]) -> None:
    bl = s2["bayesian_limits_zero_eti"]
    rows = [
        ("Spor N2: Rubin SSOFT + Trails", "Solar System (1 - 40 AU)", 0.1403, "#CC79A7", "K-I Probes & Orbits"),
        ("Spor N3: Rubin V2+V3 DDF", "Galactic Field (2,100 stars)", 0.1133, "#0072B2", "Optical Transient/Dim"),
        ("Spor N1C: VASCO Multi-Decade", "1950-2023 Optical (1,197 stars)", 0.1603, "#009E73", "K-II Vanishing Stars"),
        ("Spor N4: 71.92-Oct Radio Bridge", "54 MHz-3 GHz + FRB (1,083 stars)", 0.1772, "#D55E00", "Radio Beacons / FRB"),
        ("Spor N5: 10-Yr Secular IR+Opt", "2010-2024 NEOWISE/ZTF (1,083 stars)", 0.1772, "#E69F00", "Dyson Shell Construction"),
        ("Spor N7: TESS 2-Min Space Phot.", "Pure Milky Way (555 / 374.3 eff)", 0.5115, "#56B4E9", "Megadips, Beacons, Flashes"),
        ("Spor N8: MW ATNF Pulsars + GC", "Galaxy-Wide Pulsars (2,501 / 2,409 eff)", 0.0797, "#999999", "Precision Timing & Death Line"),
        ("Spor N9: Gaia DR3 + 25-Yr PMa", "Pure Milky Way (996 / 873.2 eff)", bl["all_pure_mw_eff"]["jeffreys_f95_pct"], "#B00020", "Dark Companions & Astrometry"),
    ]
    fig, ax = plt.subplots(figsize=(12.8, 5.8), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    vals = [r[2] for r in rows]
    ax.barh(ys, vals, height=0.60, color=[r[3] for r in rows], edgecolor="#111", lw=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r[0]}\n[{r[1]}]" for r in rows], fontsize=8.4)
    ax.set_xlim(0, 0.98)
    for y, (_, _, v, _, desc) in zip(ys, rows):
        ax.text(v + 0.012, y, f"Jeffreys f95 = {v:.4f}%  ({desc})", va="center", ha="left", fontsize=8.2)
    ax.set_xlabel(r"95% Jeffreys Bayesian Upper Limit $f_{95}$ (%) Across Strictly Milky Way Campaigns (0 ETI)")
    ax.set_title("Complete Milky Way Multi-Messenger, Timing & Dynamical SETI Synthesis (N1-N5, N7-N9: 0 ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.25, ls=":")
    save_both(fig, "figN9_06_grand_milky_way_seti_synthesis.png")


def main() -> int:
    cat = list(csv.DictReader((RES / "N9_MILKY_WAY_ASTROMETRY_CATALOG.csv").open("r", encoding="utf-8")))
    vet = list(csv.DictReader((RES / "N9_CANDIDATES_VETTED.csv").open("r", encoding="utf-8")))
    s2 = json.loads((RES / "N9_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N9_STAGE3_VETTING.json").read_text(encoding="utf-8"))

    fig01_cmd_and_25yr_coverage(cat, vet)
    fig02_hgca_vs_kervella(cat)
    fig03_nss_dark_mass_plane(cat)
    fig04_veto_funnel(s2, s3)
    fig05_injections_and_f95(s2)
    fig06_grand_milky_way_synthesis(s2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
