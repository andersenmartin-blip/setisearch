#!/usr/bin/env python3
"""Generate 6 publication-quality 300-DPI PNGs for Spor N8 (Galactic Center & ATNF Pulsars)."""
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
WS = ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars"
INP = ROOT / "inputs_n8_20261127"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch/progress/2026-11-27-n8-galactic-center-and-pulsars/figures"

plt.rcParams.update({
    "font.size": 9.4,
    "axes.titlesize": 10.6,
    "axes.labelsize": 9.8,
    "xtick.labelsize": 8.6,
    "ytick.labelsize": 8.6,
    "legend.fontsize": 8.0,
    "figure.titlesize": 12.2,
})


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    for d in (FIG_WS, FIG_GIT):
        fig.savefig(d / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}", flush=True)


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fig01_sky_and_bulge(psr: list[dict[str, Any]], fermi: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    fig = plt.figure(figsize=(12.8, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.42, 1.0])

    ax1 = fig.add_subplot(gs[0, 0], projection="mollweide")
    glon = np.array([_f(r["glon_signed"], 0.0) for r in psr])
    glat = np.array([_f(r["GLAT"], 0.0) for r in psr])
    ax1.scatter(-np.radians(glon), np.radians(glat), s=10, c="#0072B2", alpha=0.55, label=f"Milky Way ATNF Pulsars (n={len(psr)})")

    gc = [r for r in psr if r["in_gc_core"] == "True"]
    ax1.scatter(-np.radians([_f(r["glon_signed"]) for r in gc]), np.radians([_f(r["GLAT"]) for r in gc]),
                s=20, c="#009E73", alpha=0.85, label=f"GC Core Pulsars |l|<=5, |b|<=2 (n={len(gc)})")

    tr = [r for r in vet if r["domain"] == "ATNF_PULSAR"]
    tlon = []
    tlat = []
    for r in tr:
        g = _f(r["glon"], 0.0)
        tlon.append(-(g - 360.0 if g > 180 else g))
        tlat.append(_f(r["glat"], 0.0))
    ax1.scatter(np.radians(tlon), np.radians(tlat), marker="*", s=110, c="#D55E00", edgecolors="#111", lw=0.6, zorder=5,
                label=f"Stage 2 Pulsar Triggers -> 0 ETI (n={len(tr)})")
    ax1.grid(True, alpha=0.32, ls=":")
    ax1.set_title("Galactic Coordinates: 2,501 Milky Way ATNF Pulsars (LMC/SMC Excluded)")
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.26), ncol=2, framealpha=0.95, fontsize=8.1)

    # Panel 2: Bulge Fermi zoom
    ax2 = fig.add_subplot(gs[0, 1])
    fl_assoc = [r for r in fermi if r["unassociated"] == "False"]
    fl_un = [r for r in fermi if r["unassociated"] == "True"]

    def sgn_l(rows):
        return [(_f(r["GLON"]) - 360.0 if _f(r["GLON"]) > 180.0 else _f(r["GLON"])) for r in rows]

    ax2.scatter(sgn_l(fl_assoc), [_f(r["GLAT"]) for r in fl_assoc], s=42, marker="s", c="#009E73", edgecolors="#111", lw=0.5, label=f"Associated 4FGL (n={len(fl_assoc)})")
    ax2.scatter(sgn_l(fl_un), [_f(r["GLAT"]) for r in fl_un], s=38, c="#E69F00", edgecolors="#111", lw=0.45, alpha=0.85, label=f"Unassociated Bulge 4FGL (n={len(fl_un)})")
    ax2.scatter([0.0], [-0.046], marker="*", s=160, c="#B00020", edgecolors="#111", lw=0.6, zorder=6, label="Sgr A* Galactic Center")
    ax2.invert_xaxis()
    ax2.set_xlim(10.5, -10.5)
    ax2.set_ylim(-5.3, 5.3)
    ax2.set_xlabel("Galactic Longitude l (deg)")
    ax2.set_ylabel("Galactic Latitude b (deg)")
    ax2.set_title("Galactic Bulge Fermi-LAT 4FGL-DR3 (|l|<=10, |b|<=5: 222 Sources)")
    ax2.grid(True, alpha=0.28, ls=":")
    ax2.legend(loc="upper right", fontsize=7.8, framealpha=0.95)

    fig.suptitle("Spor N8: Strictly Milky Way ATNF Pulsar & Galactic Bulge Gamma-Ray Census", fontweight="bold")
    save_both(fig, "figN8_01_milky_way_pulsar_and_bulge_sky.png")


def fig02_p_pdot(psr: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    pos = [r for r in psr if _f(r.get("P0"), 0) > 0 and _f(r.get("P1"), -1) > 0]
    neg = [r for r in psr if _f(r.get("P0"), 0) > 0 and _f(r.get("P1"), 1) < 0]

    ax1.scatter([_f(r["P0"]) for r in pos], [_f(r["P1"]) for r in pos], s=11, c="#0072B2", alpha=0.55, label=f"Normal Spin-Down P1 > 0 (n={len(pos)})")
    pgrid = np.logspace(-3, 1.5, 100)
    # Chen & Ruderman / Spor N8 death line: Bsurf = 3.2e19 * sqrt(P*P1) => P1 = ((10**10.6 * P^2) / 3.2e19)^2 / P
    p1_death = (((10.0 ** 10.6) * (pgrid ** 2)) / 3.2e19) ** 2 / pgrid
    ax1.plot(pgrid, p1_death, "--", color="#B00020", lw=1.4, label=r"Death Line $\log_{10}(B/P^2) = 10.6$")
    ax1.axvline(15.0, color="#CC79A7", ls=":", lw=1.3, label="Ultra-Long Period Gate (P0 >= 15 s)")

    j2144 = [r for r in vet if r["name"] == "J2144-3933"]
    if j2144:
        ax1.scatter([_f(j2144[0]["p0_s"])], [_f(j2144[0]["p1"])], s=140, marker="*", c="#D55E00", edgecolors="#111", lw=0.7, zorder=6, label="PSR J2144-3933 (8.51s Young+1999)")
        ax1.annotate("J2144-3933\n(Young+1999)", xy=(_f(j2144[0]["p0_s"]), _f(j2144[0]["p1"])), xytext=(6, -24), textcoords="offset points", fontsize=8.0)

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1e-3, 35.0)
    ax1.set_ylim(1e-22, 1e-9)
    ax1.set_xlabel("Spin Period P0 (s)")
    ax1.set_ylabel(r"Spin-Down Rate $\dot{P} > 0$ (s/s)")
    ax1.set_title(r"Classic $P-\dot{P}$ Diagram Across Milky Way Pulsars")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="lower right", fontsize=7.6, framealpha=0.95)

    # Panel 2: Negative P1 (spin-up) distribution
    neg_gc = [r for r in neg if "GC:" in (r.get("Assoc") or "").upper()]
    neg_f = [r for r in neg if "GC:" not in (r.get("Assoc") or "").upper()]
    ax2.scatter([_f(r["P0"]) for r in neg_gc], [abs(_f(r["P1"])) for r in neg_gc], s=36, marker="^", c="#009E73", edgecolors="#111", lw=0.45, label=f"Globular Cluster Potential (n={len(neg_gc)})")
    ax2.scatter([_f(r["P0"]) for r in neg_f], [abs(_f(r["P1"])) for r in neg_f], s=36, marker="o", c="#E69F00", edgecolors="#111", lw=0.45, label=f"Field Negative P1 (n={len(neg_f)})")
    j1144 = [r for r in neg_f if r["PSRJ"] == "J1144-6146"]
    if j1144:
        ax2.annotate("J1144-6146\n(0.43sig noise)", xy=(_f(j1144[0]["P0"]), abs(_f(j1144[0]["P1"]))), xytext=(-75, -18), textcoords="offset points", fontsize=8.0)
    ax2.axhline(1e-17, color="#B00020", ls="--", lw=1.3, label=r"Spin-Up Anomaly Gate $|\dot{P}| > 10^{-17}$")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(1e-3, 10.0)
    ax2.set_ylim(1e-22, 1e-15)
    ax2.set_xlabel("Spin Period P0 (s)")
    ax2.set_ylabel(r"Apparent Spin-Up $|\dot{P}|$ for $\dot{P} < 0$ (s/s)")
    ax2.set_title("Apparent Spin-Up Pulsars (All Resolved: GC or Timing Noise)")
    ax2.grid(True, which="both", alpha=0.22, ls=":")
    ax2.legend(loc="lower right", fontsize=7.8, framealpha=0.95)

    fig.suptitle("Spor N8 Channel P: Pulsar Timing, Death Line & Spin-Up Diagnostics (0 ETI)", fontweight="bold")
    save_both(fig, "figN8_02_pulsar_p_pdot_and_spinup_diagnostics.png")


def fig03_fermi_and_gc_core(fermi: list[dict[str, Any]], nvss: list[dict[str, Any]], csc: list[dict[str, Any]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    un = [r for r in fermi if r["unassociated"] == "True"]
    asoc = [r for r in fermi if r["unassociated"] == "False"]

    ax1.scatter([_f(r["PLGam"]) for r in asoc], [max(0.1, _f(r["max_curv"], 0.1)) for r in asoc], s=32, marker="s", c="#009E73", edgecolors="#111", lw=0.4, label=f"Associated 4FGL (n={len(asoc)})")
    ax1.scatter([_f(r["PLGam"]) for r in un], [max(0.1, _f(r["max_curv"], 0.1)) for r in un], s=28, c="#0072B2", alpha=0.75, label=f"Unassociated Bulge (n={len(un)})")
    ax1.axvline(1.85, color="#B00020", ls="--", lw=1.2, label="Hard Photon Index (PLGam < 1.85)")
    ax1.axhline(5.0, color="#D55E00", ls=":", lw=1.2, label="Spectral Curvature >= 5 sigma")
    ax1.text(1.42, 16.0, "Beamed Hard-Curved Gate\n0 Unassociated Triggers\n(Sig>=10 & PLGam<1.85)", ha="center", va="center", fontsize=8.0, color="#8B0000",
             bbox=dict(boxstyle="round,pad=0.35", fc="#FFF5F5", ec="#B00020", lw=0.8))
    ax1.set_yscale("log")
    ax1.set_xlim(1.0, 3.6)
    ax1.set_ylim(0.08, 45.0)
    ax1.set_xlabel(r"Fermi-LAT Power-Law Photon Index $\Gamma$")
    ax1.set_ylabel("Spectral Curvature Significance (sigma)")
    ax1.set_title("Galactic Bulge Fermi-LAT 4FGL Spectral Space (222 Sources)")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="lower right", fontsize=7.8, framealpha=0.95)

    # Panel 2: Core 0.5 deg around Sgr A* (CSC2 + NVSS + Fermi)
    dra_c = [(_f(r["ra_deg"]) - 266.4168) * math.cos(math.radians(-29.0078)) * 60.0 for r in csc]
    ddec_c = [(_f(r["dec_deg"]) + 29.0078) * 60.0 for r in csc]
    ax2.scatter(dra_c[::2], ddec_c[::2], s=3, c="#999999", alpha=0.35, label=f"Chandra CSC2 X-Ray (n={len(csc)})")
    dra_n, ddec_n = [], []
    for r in nvss:
        dx = (_f(r["ra_deg"]) - 266.4168) * math.cos(math.radians(-29.0078)) * 60.0
        dy = (_f(r["dec_deg"]) + 29.0078) * 60.0
        if abs(dx) <= 32 and abs(dy) <= 32:
            dra_n.append(dx)
            ddec_n.append(dy)
    ax2.scatter(dra_n, ddec_n, s=16, c="#0072B2", alpha=0.65, label=f"NVSS 1.4 GHz Radio (<32': n={len(dra_n)})")
    ax2.scatter([0.0], [0.0], marker="*", s=180, c="#B00020", edgecolors="#111", lw=0.7, zorder=6, label="Sgr A* Galactic Nucleus")
    ax2.set_xlim(32.0, -32.0)
    ax2.set_ylim(-32.0, 32.0)
    ax2.set_xlabel("dRA from Sgr A* (arcmin)")
    ax2.set_ylabel("dDec from Sgr A* (arcmin)")
    ax2.set_title("Central 1-Deg Sgr A* Multi-Messenger Context")
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="upper right", fontsize=7.6, framealpha=0.95)

    fig.suptitle("Galactic Bulge Fermi-LAT Diagnostics & Central Sgr A* X-Ray/Radio Field", fontweight="bold")
    save_both(fig, "figN8_03_fermi_bulge_and_gc_core_overlays.png")


def fig04_counterparts_and_funnel(fermi: list[dict[str, Any]], s2: dict[str, Any], s3: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    # Panel 1: Fermi Bulge significance vs variability index
    un = [r for r in fermi if r["unassociated"] == "True"]
    asoc = [r for r in fermi if r["unassociated"] == "False"]
    ax1.scatter([max(1.0, _f(r["Sig"], 1.0)) for r in asoc], [max(0.5, _f(r["VarInd"], 0.5)) for r in asoc], s=32, marker="s", c="#009E73", edgecolors="#111", lw=0.4, label=f"Associated 4FGL (n={len(asoc)})")
    ax1.scatter([max(1.0, _f(r["Sig"], 1.0)) for r in un], [max(0.5, _f(r["VarInd"], 0.5)) for r in un], s=26, c="#0072B2", alpha=0.72, label=f"Unassociated Bulge (n={len(un)})")
    ax1.axvline(10.0, color="#B00020", ls="--", lw=1.2, label="Significance >= 10 sigma")
    ax1.axhline(100.0, color="#D55E00", ls=":", lw=1.2, label="Extreme Variability (VarInd >= 100)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(3.5, 450.0)
    ax1.set_ylim(0.4, 800.0)
    ax1.set_xlabel("Fermi-LAT Detection Significance (sigma)")
    ax1.set_ylabel("Fermi-LAT Variability Index")
    ax1.set_title("Galactic Bulge Variability Diagnostic (0 Unassoc Beacons)")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="upper left", fontsize=7.8, framealpha=0.95)

    # Panel 2: Veto Funnel
    vc = s3["vetting_class_counts"]
    stages = [
        ("Milky Way ATNF Pulsars", s2["milky_way_pulsars_total"], "#0072B2"),
        ("Chandra CSC2 GC X-Ray", s2["csc2_gc_xray_sources"], "#56B4E9"),
        ("NVSS 1.4 GHz GC Radio", s2["nvss_gc_radio_sources"], "#009E73"),
        ("Fermi Bulge 4FGL-DR3", s2["fermi_bulge_sources_total"], "#E69F00"),
        ("GC Core Pulsars (|l|<=5)", s2["galactic_center_core_pulsars"], "#0072B2"),
        ("Stage 2 Triggers Total", s3["stage2_triggers_vetted"], "#D55E00"),
        ("GC Potential (M15 A & D)", vc.get("GLOBULAR_CLUSTER_GRAVITATIONAL_ACCEL", 0), "#CC79A7"),
        ("0.43sig Timing Noise (J1144)", vc.get("TIMING_NOISE_UNSIGNIFICANT_P1", 0), "#999999"),
        ("Slow Pulsar J2144-3933", vc.get("CURVED_SPACETIME_SLOW_RADIO_PULSAR", 0), "#009E73"),
        ("Verified Galactic ETI", s3["verified_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    ax2.barh(ys, vals, color=[c for _, _, c in stages], height=0.62, edgecolor="#111")
    ax2.set_xscale("log")
    ax2.set_xlim(0.5, 25000)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([s for s, _, _ in stages], fontsize=8.4)
    for y, (_, v, _) in zip(ys, stages):
        ax2.text(max(v, 0.85) * 1.18, y, f"{v}", va="center", fontweight="bold", fontsize=8.8)
    ax2.set_xlabel("Galactic Sources (log scale)")
    ax2.set_title("Spor N8 Multi-Messenger Galactic Veto Funnel (0 ETI)")
    ax2.grid(axis="x", alpha=0.25, ls=":")

    fig.suptitle("Spor N8 Galactic Bulge Variability & Multi-Messenger Vetting Funnel", fontweight="bold")
    save_both(fig, "figN8_04_bulge_variability_and_veto_funnel.png")


def fig05_injections_and_f95(s2: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    inj = s2["injections"]
    x = np.array([1, 2, 3, 4])
    yp1 = [inj["gate_p1_spinup"][k]["completeness"] * 100.0 for k in ("-1e-18", "-1e-17", "-1e-16", "-1e-15")]
    yp2 = [inj["gate_p2_deathline"][k]["completeness"] * 100.0 for k in ("11.2", "10.5", "9.8", "9.0")]
    yg1 = [inj["gate_g1_fermi_bulge"][k]["completeness"] * 100.0 for k in ("5", "10", "20", "40")]

    ax1.plot(x, yp1, "-o", lw=2.0, color="#0072B2", label=f"P1 Spin-Up (Strong={inj['completeness_p1_strong']*100:.1f}%)")
    ax1.plot(x, yp2, "-s", lw=2.0, color="#009E73", label=f"P2 Deathline (Mean={inj['completeness_p2_below_deathline']*100:.1f}%)")
    ax1.plot(x, yg1, "-^", lw=2.0, color="#D55E00", label=f"G1 Fermi Bulge (Sig>=20={inj['completeness_fermi_sig_ge_20']*100:.1f}%)")
    ax1.axvline(2.0, color="#B00020", ls=":", lw=1.2, label="Nominal Gate Transition")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["Sub-Thresh", "Gate Edge", "Moderate", "Strong"], fontsize=8.4)
    ax1.set_ylim(-5, 110)
    ax1.set_ylabel("Injection Recovery Completeness (%)")
    ax1.set_title("1,200-Trial Galactic Beacon & Pulsar Injection Recovery")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="lower right", fontsize=7.7)

    bl = s2["bayesian_limits_zero_eti"]
    cohorts = [
        ("MW Pulsars\nRaw (2,501)", bl["all_mw_pulsars_raw"]),
        ("MW Pulsars\nEff (2,409.2)", bl["all_mw_pulsars_eff"]),
        ("Fermi Bulge\nAll (222)", bl["fermi_bulge_all"]),
        ("Fermi Bulge\nUnassoc (168)", bl["fermi_bulge_unassociated"]),
        ("GC Core\nPulsars (104)", bl["gc_core_pulsars"]),
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
        ax2.text(xi - w, jv + 0.05, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
        ax2.text(xi + 0.05, uv + 0.05, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
    ax2.set_xticks(bx)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.1)
    ax2.set_ylim(0, 3.45)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ (%)")
    ax2.set_title("Milky Way Zero-ETI 95% Prevalence Bounds (Pulsars & Bulge)")
    ax2.grid(axis="y", alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=7.8)

    fig.suptitle("Spor N8 Injection Calibration & Galactic Center Bayesian Upper Limits", fontweight="bold")
    save_both(fig, "figN8_05_injection_recovery_and_bayesian_f95.png")


def fig06_galactic_synthesis(s2: dict[str, Any]) -> None:
    bl = s2["bayesian_limits_zero_eti"]
    rows = [
        ("Spor N2: Rubin SSOFT + Trails", "Solar System (1 - 40 AU)", 0.1403, "#CC79A7", "K-I Probes & Orbits"),
        ("Spor N3: Rubin V2+V3 DDF", "Galactic Field (2,100 stars)", 0.1133, "#0072B2", "Optical Transient/Dim"),
        ("Spor N1C: VASCO Multi-Decade", "1950-2023 Optical (1,197 stars)", 0.1603, "#009E73", "K-II Vanishing Stars"),
        ("Spor N4: 71.92-Oct Radio Bridge", "54 MHz-3 GHz + FRB (1,083 stars)", 0.1772, "#D55E00", "Radio Beacons / FRB"),
        ("Spor N5: 10-Yr Secular IR+Opt", "2010-2024 NEOWISE/ZTF (1,083 stars)", 0.1772, "#E69F00", "Dyson Shell Construction"),
        ("Spor N7: TESS 2-Min Space Phot.", "Pure Milky Way (555 / 374.3 eff)", 0.5115, "#56B4E9", "Megadips, Beacons, Flashes"),
        ("Spor N8: MW ATNF Pulsars + GC", "Galaxy-Wide Pulsars (2,501 / 2,409 eff)", bl["all_mw_pulsars_eff"]["jeffreys_f95_pct"], "#B00020", "Precision Timing & Death Line"),
    ]
    fig, ax = plt.subplots(figsize=(12.6, 5.4), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    vals = [r[2] for r in rows]
    ax.barh(ys, vals, height=0.60, color=[r[3] for r in rows], edgecolor="#111", lw=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r[0]}\n[{r[1]}]" for r in rows], fontsize=8.5)
    ax.set_xlim(0, 0.98)
    for y, (_, _, v, _, desc) in zip(ys, rows):
        ax.text(v + 0.012, y, f"Jeffreys f95 = {v:.4f}%  ({desc})", va="center", ha="left", fontsize=8.3)
    ax.set_xlabel(r"95% Jeffreys Bayesian Upper Limit $f_{95}$ (%) Across Milky Way Campaigns (0 ETI)")
    ax.set_title("Milky Way SETI Synthesis: Solar System -> Disk -> Galactic Center (0 ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.25, ls=":")
    save_both(fig, "figN8_06_milky_way_gc_synthesis.png")


def main() -> int:
    psr = list(csv.DictReader((RES / "N8_MILKY_WAY_PULSARS_CATALOG.csv").open("r", encoding="utf-8")))
    fermi = list(csv.DictReader((RES / "N8_BULGE_FERMI_CATALOG.csv").open("r", encoding="utf-8")))
    vet = list(csv.DictReader((RES / "N8_CANDIDATES_VETTED.csv").open("r", encoding="utf-8")))
    nvss = list(csv.DictReader((INP / "radio/nvss_galactic_center.csv").open("r", encoding="utf-8")))
    csc = list(csv.DictReader((INP / "xray/csc2_galactic_center.csv").open("r", encoding="utf-8")))
    s2 = json.loads((RES / "N8_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N8_STAGE3_VETTING.json").read_text(encoding="utf-8"))

    fig01_sky_and_bulge(psr, fermi, vet)
    fig02_p_pdot(psr, vet)
    fig03_fermi_and_gc_core(fermi, nvss, csc)
    fig04_counterparts_and_funnel(fermi, s2, s3)
    fig05_injections_and_f95(s2)
    fig06_galactic_synthesis(s2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
