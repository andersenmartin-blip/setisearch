#!/usr/bin/env python3
"""
Generate 6 publication-quality 300-DPI PNG figures for Spor N4
(SPOR_N4_LOWFREQ_RADIO_BRIDGE_1083) in both WS/figures and
setisearch/progress/2026-11-27-n4-lowfreq-radio-bridge-1083/figures.
"""
from __future__ import annotations

import collections
import csv
import json
import math
import pathlib
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from astropy.io import fits

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n4_20261127_lowfreq_radio_bridge_1083"
INP = ROOT / "inputs_n4_20261127"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch" / "progress" / "2026-11-27-n4-lowfreq-radio-bridge-1083" / "figures"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11.5,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9.0,
    "figure.titlesize": 13,
})


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_WS / name, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_GIT / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}")


def fig01_em_ladder(summary: dict[str, Any]) -> None:
    bands = [
        ("LoLSS (54 MHz)", 54e6, 78e6, 12, "#D55E00", "Spor N4 New Radio Bridge"),
        ("VLSSr (74 MHz)", 73.8e6, 75.5e6, 774, "#D55E00", "Spor N4 New Radio Bridge"),
        ("LoTSS DR3 (144 MHz)", 120e6, 168e6, 533, "#D55E00", "Spor N4 New Radio Bridge"),
        ("TGSS ADR1 (150 MHz)", 140e6, 156e6, 956, "#D55E00", "Spor N4 New Radio Bridge"),
        ("CHIME/FRB (400-800 MHz)", 400e6, 800e6, 605, "#E69F00", "Spor N4 FRB/Transient"),
        ("SUMSS / RACS (843-1368 MHz)", 843e6, 1368e6, 1083, "#D55E00", "Spor N4 New Radio Bridge"),
        ("NVSS / FIRST (1.4 GHz)", 1.35e9, 1.45e9, 866, "#D55E00", "Spor N4 New Radio Bridge"),
        ("VLASS 1.2 (3.0 GHz)", 2.0e9, 4.0e9, 74, "#CC79A7", "Spor N4 FITS Cutouts"),
        ("SKA / BL / GBT (v7 Bridge)", 1.0e9, 3.5e10, 1083, "#0072B2", "Prior v7 (62.58 Octaves)"),
        ("Sub-mm / FIR / IR (v7)", 1.0e11, 1.0e14, 1083, "#0072B2", "Prior v7 (62.58 Octaves)"),
        ("Optical / LSST DP1 (N1-N3)", 3.0e14, 1.0e15, 1083, "#009E73", "Rubin DP1 + Optical"),
        ("UV / X-ray / Gamma (v7)", 1.5e15, 2.4e25, 1083, "#0072B2", "Prior v7 (62.58 Octaves)"),
        ("VHE / PeV (HAWC/LHAASO)", 2.4e25, 2.418e29, 1083, "#0072B2", "Prior v7 (62.58 Octaves)"),
    ]
    fig, ax = plt.subplots(figsize=(11.5, 6.2), constrained_layout=True)
    y_pos = np.arange(len(bands))[::-1]
    for y, (lbl, f0, f1, ncov, col, grp) in zip(y_pos, bands):
        width = max(math.log10(f1) - math.log10(f0), 0.16)
        x0 = math.log10(f0)
        ax.barh(y, width, left=x0, height=0.64, color=col, alpha=0.88, edgecolor="#1A1A1A", linewidth=0.7)
        ax.text(x0 + width + 0.18, y, f"{lbl}  [n={ncov}]", va="center", ha="left", fontsize=8.8)

    # Highlight prior v7 boundary (35 GHz ~ 10.54 log10 Hz? Actually prior min freq was ALMA/radio ~ 1 GHz = 9.0, 62.582 octaves below 1 PeV)
    prior_min_hz = summary["panchromatic_span"]["highest_energy_ev"] / 4.135667696e-15 / (2.0 ** 62.582)
    ax.axvline(math.log10(prior_min_hz), color="#0072B2", linestyle="--", linewidth=1.4, label=f"Prior v7.0 Lower Edge (~{prior_min_hz/1e9:.2f} GHz, 62.582 oct)")
    ax.axvline(math.log10(54e6), color="#D55E00", linestyle="-", linewidth=1.6, label=f"Spor N4 LoLSS Edge (54 MHz -> {summary['panchromatic_span']['em_octaves']:.2f} oct)")

    ax.set_yticks([])
    ax.set_xlim(7.2, 33.8)
    ax.set_xlabel(r"$\log_{10}(\nu / \mathrm{Hz})$  [Frequency across 21.65 decades = 71.92 EM Octaves]")
    ax.set_title("Panchromatic Electromagnetic Coverage Ladder: 54 MHz to 1.000 PeV (71.9233 EM Octaves across 1,083 Stars)")
    ax.grid(axis="x", alpha=0.3, linestyle=":")
    ax.legend(loc="upper right", framealpha=0.95)
    save_both(fig, "figN4_01_panchromatic_em_ladder_72oct.png")


def fig02_allsky_coverage(star_rows: list[dict[str, Any]]) -> None:
    ras = np.array([float(r["ra_deg"]) for r in star_rows])
    decs = np.array([float(r["dec_deg"]) for r in star_rows])
    covs = np.array([int(r["n_lowfreq_surveys_covering"]) for r in star_rows])
    roles = np.array([r["role"] for r in star_rows])

    # Convert RA [0,360] -> Aitoff lon [-pi, pi] shifted (RA=180 at center 0, decreasing right or standard astro)
    lon = np.radians(((ras + 180.0) % 360.0) - 180.0)
    lat = np.radians(decs)

    fig = plt.figure(figsize=(11.5, 5.8), constrained_layout=True)
    ax = fig.add_subplot(111, projection="aitoff")
    ax.grid(True, alpha=0.35, linestyle=":")

    sc_mask = roles == "SCIENCE"
    ct_mask = roles == "CONTROL"
    sc = ax.scatter(lon[sc_mask], lat[sc_mask], c=covs[sc_mask], cmap="viridis", vmin=3, vmax=9,
                    s=26, alpha=0.9, edgecolors="#111111", linewidths=0.3, label="Science Targets (n=787)")
    ax.scatter(lon[ct_mask], lat[ct_mask], c=covs[ct_mask], cmap="viridis", vmin=3, vmax=9,
               s=34, marker="^", alpha=0.85, edgecolors="#B00020", linewidths=0.45, label="Control Targets (n=296)")

    # Declination domain lines
    lons_line = np.linspace(-np.pi, np.pi, 360)
    ax.plot(lons_line, np.full_like(lons_line, np.radians(49.0)), color="#D55E00", ls="--", lw=1.1, label="RACS North Limit (+49 deg)")
    ax.plot(lons_line, np.full_like(lons_line, np.radians(-30.0)), color="#CC79A7", ls="-.", lw=1.1, label="SUMSS North / VLSSr South (-30 deg)")
    ax.plot(lons_line, np.full_like(lons_line, np.radians(-10.0)), color="#009E73", ls=":", lw=1.3, label="LoTSS DR3 / CHIME South (-10 deg)")

    cbar = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.05)
    cbar.set_label("Covering Live Radio Surveys per Star (min=3, median=5, max=9)")
    ax.set_title("All-Sky Radio Survey Coverage Across 1,083 Master Stars (Aitoff Equatorial, 100% Covered >= 3 Surveys)", pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=3, framealpha=0.95)
    save_both(fig, "figN4_02_allsky_radio_coverage_1083.png")


def fig03_eirp_distance(star_rows: list[dict[str, Any]], vlass_rows: list[dict[str, Any]]) -> None:
    sci = [r for r in star_rows if r["role"] == "SCIENCE" and float(r["dist_pc"]) <= 2000.0]
    dists = np.array([float(r["dist_pc"]) for r in sci])
    eirp_hz = np.array([float(r["eirp_1hz_w"]) for r in sci])
    surv = np.array([r["deepest_survey"] for r in sci])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.2), constrained_layout=True)

    cmap_s = {
        "LOTSS_DR3_144": ("LoTSS DR3 (144 MHz)", "#0072B2"),
        "FIRST_1400": ("FIRST (1.4 GHz)", "#009E73"),
        "RACS_MID_1367": ("RACS-mid (1.37 GHz)", "#E69F00"),
        "RACS_LOW_888": ("RACS-low (888 MHz)", "#D55E00"),
        "NVSS_1400": ("NVSS (1.4 GHz)", "#56B4E9"),
        "SUMSS_843": ("SUMSS (843 MHz)", "#CC79A7"),
    }
    for key, (lbl, col) in cmap_s.items():
        m = surv == key
        if m.any():
            ax1.scatter(dists[m], eirp_hz[m], s=22, alpha=0.82, color=col, label=f"{lbl} (n={m.sum()})")

    # Overlay VLASS 3 GHz FITS photometry for SCIENCE stars
    v_sci = [r for r in vlass_rows if r["role"] == "SCIENCE"]
    if v_sci:
        ax1.scatter([float(r["dist_pc"]) for r in v_sci],
                    [float(r["eirp_5sig_1hz_w_hz"]) for r in v_sci],
                    s=34, marker="D", facecolors="none", edgecolors="#111111", linewidths=1.0,
                    label=f"VLASS 1.2 FITS 3 GHz (n={len(v_sci)})", zorder=5)

    ax1.axhline(2.2e13, color="#B00020", ls="--", lw=1.2, label="Arecibo 2.38 GHz Planetary Radar (~2e13 W/Hz equiv 1 Hz)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Distance d (pc)")
    ax1.set_ylabel(r"5$\sigma$ Narrowband Radio EIRP Limit (W Hz$^{-1}$)")
    ax1.set_title("Per-Star Narrowband Radio EIRP Depth vs. Distance")
    ax1.grid(True, which="both", alpha=0.25, ls=":")
    ax1.legend(loc="lower right", fontsize=8.0, framealpha=0.92)

    # Panel 2: Broadband 100 MHz radio luminosity limit vs Kardashev benchmarks across < 10 pc & all Science
    eirp_bb = eirp_hz * 1.0e8  # 100 MHz bandwidth
    near = dists <= 10.0
    bins = np.logspace(12.5, 22.5, 28)
    ax2.hist(eirp_bb, bins=bins, color="#56B4E9", alpha=0.65, edgecolor="#111111", label=f"All Science (n={len(sci)})")
    ax2.hist(eirp_bb[near], bins=bins, color="#D55E00", alpha=0.85, edgecolor="#111111", label=f"Solar Neighborhood <=10 pc (n={near.sum()})")
    ax2.axvline(1e16, color="#444444", ls=":", lw=1.3, label=r"Earth Radar / Beacon Scale ($10^{16}$ W)")
    ax2.axvline(3.8e26, color="#B00020", ls="--", lw=1.3, label=r"Kardashev Type II ($3.8\times 10^{26}$ W, far right)")
    ax2.set_xscale("log")
    ax2.set_xlabel(r"5$\sigma$ Broadband EIRP Limit ($\Delta\nu = 100$ MHz, W)")
    ax2.set_ylabel("Number of Stars")
    ax2.set_title("100 MHz Radio Luminosity Bounds (10+ Orders Below Kardashev II)")
    ax2.set_xlim(1e12, 1e24)
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    fig.suptitle("Spor N4 All-Sky Radio EIRP Sensitivity Across 787 Science Targets", fontweight="bold")
    save_both(fig, "figN4_03_eirp_sensitivity_vs_distance.png")


def fig04_vlass_and_funnel(vlass_rows: list[dict[str, Any]], vetting: dict[str, Any]) -> None:
    # Pick 6 illustrative cutouts: top 3 active radio stars + OBJECT_D + 2 nearest unmatched <5pc stars
    desired = ["TTAU", "ARLAC", "J22012+283", "OBJECT_D", "BARNARDS", "WOLF359"]
    by_st = {r["star"]: r for r in vlass_rows}
    chosen = [by_st[s] for s in desired if s in by_st]
    for r in vlass_rows:
        if len(chosen) >= 6:
            break
        if r not in chosen:
            chosen.append(r)

    fig = plt.figure(figsize=(12.6, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 1.35])

    for idx, row in enumerate(chosen[:6]):
        ax = fig.add_subplot(gs[idx // 3, idx % 3])
        fp = INP / "vlass_cutouts" / row["fits_file"]
        with fits.open(fp) as hdul:
            dat = np.array(hdul[0].data, dtype=float)
        mad = 1.4826 * np.nanmedian(np.abs(dat - np.nanmedian(dat)))
        if mad < 0.02:
            dat = dat * 1000.0
        vmax = max(0.8, np.nanpercentile(dat, 99.5))
        vmin = -0.35 * vmax if vmax < 2.0 else -0.5
        ax.imshow(dat, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax, extent=[-24, 24, -24, 24])
        c1 = patches.Circle((0, 0), 3.0, fill=False, edgecolor="#00FFFF", lw=1.2, ls="-")
        c2 = patches.Circle((0, 0), 12.0, fill=False, edgecolor="#FFFFFF", lw=0.8, ls="--")
        ax.add_patch(c1)
        ax.add_patch(c2)
        ax.set_title(f"{row['star']} ({float(row['dist_pc']):.1f} pc)\nPk={float(row['central_peak_mjy']):.2f} mJy (SNR {float(row['central_snr']):.1f})", fontsize=8.8)
        if idx // 3 == 1:
            ax.set_xlabel("dRA (arcsec)")
        if idx % 3 == 0:
            ax.set_ylabel("dDec (arcsec)")

    # Right-hand vertical Veto Funnel
    ax_f = fig.add_subplot(gs[:, 3])
    vc = vetting["vetting_class_counts"]
    stages = [
        ("Master Catalog Stars", 1083, "#0072B2"),
        ("Covered >=3 Surveys", 1083, "#0072B2"),
        ("All Catalog Match Rows", vetting["total_matched_rows_stage2"], "#56B4E9"),
        ("Unique Matched Stars", vetting["unique_matched_stars_total"], "#E69F00"),
        ("Control AGN/PN (Removed)", vc.get("CONTROL_ACTIVE_GALAXY_OR_CALIBRATOR", 0), "#999999"),
        ("Science Matched Stars", vetting["unique_matched_science_stars"], "#D55E00"),
        ("Known Coronal/YSO Stars", vc.get("KNOWN_CORONAL_FLARE_OR_RSCVN_STAR", 0) + vc.get("KNOWN_YSO_DISK_JET_OR_EVOLVED_STAR", 0), "#009E73"),
        ("Offset / Field AGN", vc.get("BACKGROUND_EXTRAGALACTIC_RADIO_SOURCE", 0), "#CC79A7"),
        ("Verified ETI Candidates", vetting["verified_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    cols = [c for _, _, c in stages]
    ax_f.barh(ys, vals, color=cols, height=0.65, edgecolor="#111111", linewidth=0.7)
    ax_f.set_xscale("log")
    ax_f.set_xlim(0.5, 5000)
    ax_f.set_yticks(ys)
    ax_f.set_yticklabels([s for s, _, _ in stages], fontsize=8.8)
    for y, (_, v, _) in zip(ys, stages):
        ax_f.text(max(v, 0.8) * 1.18, y, f"{v}", va="center", ha="left", fontweight="bold", fontsize=9.0)
    ax_f.set_xlabel("Count (log scale)")
    ax_f.set_title("VLASS 1.2 + Multi-Band\nVetting Funnel (0 ETI)")
    ax_f.grid(axis="x", alpha=0.28, ls=":")

    fig.suptitle("VLASS 1.2 (3.0 GHz) FITS Cutout Verification & Stage 3 Radio Vetting Funnel", fontweight="bold")
    save_both(fig, "figN4_04_vlass_cutouts_and_vetting_funnel.png")


def fig05_injections_and_limits(summary: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.1), constrained_layout=True)

    ig = summary["injection_grid"]
    fluxes = sorted(ig.keys(), key=lambda k: float(k))
    xs = np.array([float(k) for k in fluxes])
    ys = np.array([ig[k]["completeness"] * 100.0 for k in fluxes])
    # Wilson/binomial 68% error bars on 200 trials
    errs = 100.0 * np.sqrt(np.clip((ys / 100.0) * (1.0 - ys / 100.0) / 200.0, 0.0, 1.0))

    ax1.errorbar(xs, ys, yerr=errs, fmt="-o", color="#0072B2", lw=2.0, markersize=7, capsize=4, label="1,200-Trial Injection Recovery (200/bin)")
    ax1.axhline(100.0, color="#009E73", ls="--", lw=1.1)
    ax1.axvline(2.0, color="#D55E00", ls=":", lw=1.4, label=r"$S_{\nu} = 2.0$ mJy (100.0% Recovery)")
    for x, y in zip(xs, ys):
        ax1.text(x, y + 3.5, f"{y:.1f}%", ha="center", va="bottom", fontsize=8.5)
    ax1.set_xscale("log")
    ax1.set_ylim(-5, 114)
    ax1.set_xlabel(r"Injected Point-Source Radio Flux Density $S_\nu$ (mJy)")
    ax1.set_ylabel("Catalog Detection Completeness (%)")
    ax1.set_title("Synthetic Point-Source Radio Injection Recovery (N=1,200)")
    ax1.grid(True, which="both", alpha=0.28, ls=":")
    ax1.legend(loc="lower right", fontsize=8.8)

    # Panel 2: Bayesian 95% upper limits across cohorts
    bl = summary["bayesian_limits_zero_eti"]
    cohorts = [
        ("All Stars\n(n=1,083)", bl["all_1083_stars_s_ge_2mjy"]),
        ("RACS Covered\n(n=978)", bl["racs_888_1367mhz_covered"]),
        ("Science\n(n=787)", bl["science_787_stars_s_ge_2mjy"]),
        ("CHIME/FRB\n(n=605)", bl["chime_frb_400_800mhz_covered"]),
        ("LoTSS DR3\n(n=533)", bl["lotss_dr3_144mhz_covered"]),
        ("<10 pc\n(n=267)", bl["within_10pc_267_stars"]),
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
        ax2.text(xi - w, jv + 0.02, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.5, rotation=45)
        ax2.text(xi + 0.05, uv + 0.02, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.5, rotation=45)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.5)
    ax2.set_ylim(0, 1.38)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ on Radio ETI (%)")
    ax2.set_title(r"Zero-Detection 95% Bayesian Prevalence Upper Limits ($f_{95}$)")
    ax2.grid(axis="y", alpha=0.28, ls=":")
    ax2.legend(loc="upper left", fontsize=8.3, framealpha=0.95)

    fig.suptitle("Spor N4 Injection Completeness Calibration & Bayesian Null Constraints", fontweight="bold")
    save_both(fig, "figN4_05_injection_completeness_and_bayesian_f95.png")


def fig06_alpha_and_chime(vetted_rows: list[dict[str, Any]], chime_rows: list[dict[str, Any]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.2), constrained_layout=True)

    # Panel 1: Spectral index alpha vs angular offset
    cls_styles = {
        "CONTROL_ACTIVE_GALAXY_OR_CALIBRATOR": ("Control AGN / Blazar / PN", "#999999", "^"),
        "KNOWN_CORONAL_FLARE_OR_RSCVN_STAR": ("Known Coronal / Flare / RS CVn", "#0072B2", "o"),
        "KNOWN_YSO_DISK_JET_OR_EVOLVED_STAR": ("Known YSO / Jet / Symbiotic", "#009E73", "s"),
        "BACKGROUND_EXTRAGALACTIC_RADIO_SOURCE": ("Background Field / AGN Offset", "#D55E00", "X"),
    }
    for cls_k, (lbl, col, mk) in cls_styles.items():
        sub = [r for r in vetted_rows if r["vetting_class"] == cls_k and r["spectral_index_alpha"] != ""]
        if sub:
            seps = [float(r["min_sep_arcsec"]) for r in sub]
            alps = [float(r["spectral_index_alpha"]) for r in sub]
            ax1.scatter(seps, alps, c=col, marker=mk, s=42, alpha=0.88, edgecolors="#111111", linewidths=0.45, label=f"{lbl} (n={len(sub)})")

    ax1.axhline(-0.7, color="#D55E00", ls="--", lw=1.2, label=r"Optically Thin Synchrotron ($\alpha = -0.7$)")
    ax1.axhline(0.6, color="#009E73", ls=":", lw=1.2, label=r"Thermal Wind / Free-Free ($\alpha = +0.6$)")
    ax1.set_xlim(-0.5, 23.0)
    ax1.set_ylim(-2.6, 2.6)
    ax1.set_xlabel("Minimum Optical-to-Radio Offset (arcsec)")
    ax1.set_ylabel(r"Multi-Band Radio Spectral Index $\alpha$ ($S_\nu \propto \nu^\alpha$)")
    ax1.set_title(r"Radio Spectral Index $\alpha$ vs. Astrometric Offset (N=112 Multi-Band)")
    ax1.grid(True, alpha=0.28, ls=":")
    ax1.legend(loc="lower right", fontsize=8.0, framealpha=0.95)

    # Panel 2: CHIME/FRB DM vs Stellar Distance Foreground
    sci_c = [r for r in chime_rows if r["role"] == "SCIENCE"]
    ctl_c = [r for r in chime_rows if r["role"] == "CONTROL" and float(r["dist_pc"]) < 10000.0]

    ds_s = np.array([float(r["dist_pc"]) for r in sci_c])
    dm_s = np.array([float(r["dm_pc_cm3"]) for r in sci_c])
    ax2.scatter(ds_s, dm_s, c="#0072B2", s=50, edgecolors="#111111", linewidths=0.5, label=f"Science CHIME Overlaps (n={len(sci_c)})", zorder=4)
    if ctl_c:
        ax2.scatter([float(r["dist_pc"]) for r in ctl_c], [float(r["dm_pc_cm3"]) for r in ctl_c],
                    c="#E69F00", marker="^", s=55, edgecolors="#111111", linewidths=0.5, label=f"Galactic Control Overlaps (n={len(ctl_c)})", zorder=4)

    d_grid = np.logspace(0.3, 3.3, 100)
    dm_line = np.minimum(150.0, 0.05 * d_grid)
    ax2.plot(d_grid, dm_line, color="#B00020", lw=2.0, ls="--", label=r"Max Stellar Foreground $DM_{\rm star}$ ($0.05\,d_{\rm pc}$)")
    ax2.fill_between(d_grid, 0.05, dm_line, color="#B00020", alpha=0.12, label="Galactic Stellar DM Allowed Region")

    # Label 2 extreme examples cleanly without overlapping markers
    for r in sci_c:
        if r["star"] == "PROCYON":
            ax2.annotate(f"PROCYON ({float(r['dm_excess_ratio']):,.0f}x)",
                         xy=(float(r["dist_pc"]), float(r["dm_pc_cm3"])),
                         xytext=(-8, 16), textcoords="offset points", fontsize=8.0,
                         arrowprops=dict(arrowstyle="-", color="#444444", lw=0.7))
        elif r["star"] == "POLARIS" and float(r["dm_pc_cm3"]) > 1000.0:
            ax2.annotate(f"POLARIS ({float(r['dm_excess_ratio']):.0f}x)",
                         xy=(float(r["dist_pc"]), float(r["dm_pc_cm3"])),
                         xytext=(8, 6), textcoords="offset points", fontsize=8.0)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(2.0, 2000.0)
    ax2.set_ylim(0.08, 4000.0)
    ax2.set_xlabel("Target Stellar Distance (pc)")
    ax2.set_ylabel(r"Observed CHIME/FRB Dispersion Measure DM (pc cm$^{-3}$)")
    ax2.set_title("CHIME/FRB Catalog 1 Overlap Veto: Extragalactic DM Excess (32x-4,079x)")
    ax2.grid(True, which="both", alpha=0.28, ls=":")
    ax2.legend(loc="lower right", fontsize=8.0, framealpha=0.95)

    fig.suptitle("Spectral Index Diagnostics & CHIME/FRB Extragalactic Dispersion Measure Veto", fontweight="bold")
    save_both(fig, "figN4_06_spectral_index_and_chime_dm_veto.png")


def main() -> int:
    summary = json.loads((RES / "N4_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    vetting = json.loads((RES / "N4_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    star_rows = list(csv.DictReader((RES / "N4_MASTER_1083_RADIO_SUMMARY.csv").open(encoding="utf-8")))
    vlass_rows = list(csv.DictReader((RES / "N4_VLASS_CUTOUT_PHOTOMETRY.csv").open(encoding="utf-8")))
    vetted_rows = list(csv.DictReader((RES / "N4_RADIO_CANDIDATES_VETTED.csv").open(encoding="utf-8")))
    chime_rows = list(csv.DictReader((RES / "N4_CHIME_FRB_VETTED.csv").open(encoding="utf-8")))

    fig01_em_ladder(summary)
    fig02_allsky_coverage(star_rows)
    fig03_eirp_distance(star_rows, vlass_rows)
    fig04_vlass_and_funnel(vlass_rows, vetting)
    fig05_injections_and_limits(summary)
    fig06_alpha_and_chime(vetted_rows, chime_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
