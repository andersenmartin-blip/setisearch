#!/usr/bin/env python3
"""
Generate 6 publication-quality 300-DPI PNG figures for Spor N6
(SPOR_N6_KARDASHEV_III_LOCAL_SUPERCLUSTER) in WS/figures and
setisearch/progress/2026-11-27-n6-kardashev-iii-supercluster/figures.
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
import matplotlib.patches as patches
import numpy as np
from astropy.io import fits
from PIL import Image

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n6_20261127_kardashev_iii_supercluster"
INP = ROOT / "inputs_n6_20261127"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch" / "progress" / "2026-11-27-n6-kardashev-iii-supercluster" / "figures"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11.2,
    "axes.labelsize": 10.2,
    "xtick.labelsize": 9.2,
    "ytick.labelsize": 9.2,
    "legend.fontsize": 8.5,
    "figure.titlesize": 12.8,
})


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_WS / name, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_GIT / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}")


def fig01_supercluster_map(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    ras = np.array([float(r["ra_deg"]) for r in cat])
    decs = np.array([float(r["dec_deg"]) for r in cat])
    dists = np.array([float(r["dist_mpc"]) for r in cat])
    lons = np.radians(((ras + 180.0) % 360.0) - 180.0)
    lats = np.radians(decs)

    fig = plt.figure(figsize=(11.8, 5.8), constrained_layout=True)
    ax = fig.add_subplot(111, projection="aitoff")
    ax.grid(True, alpha=0.32, ls=":")
    sc = ax.scatter(lons, lats, c=dists, cmap="viridis_r", vmin=1.0, vmax=40.0, s=16, alpha=0.82, edgecolors="#111", lw=0.2, label=f"HECATE Local Supercluster Galaxies (N={len(cat)})")

    v_lons = np.radians(((np.array([float(r["ra_deg"]) for r in vet]) + 180.0) % 360.0) - 180.0)
    v_lats = np.radians(np.array([float(r["dec_deg"]) for r in vet]))
    ax.scatter(v_lons, v_lats, s=110, marker="*", c="#D55E00", edgecolors="#111", lw=0.7, zorder=6, label=f"Stage 2 K-III Triggers Vetted to 0 ETI (n={len(vet)})")

    cbar = fig.colorbar(sc, ax=ax, shrink=0.74, pad=0.05)
    cbar.set_label("Galaxy Distance D (Mpc, 0.5-40.0 Mpc)")
    ax.set_title("Local Supercluster Galaxies (HECATE, N=1,381, M* = 2.75e13 Msun ~ 4.13e13 Stars)", pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.20), ncol=2, framealpha=0.95)
    save_both(fig, "figN6_01_local_supercluster_allsky_map.png")


def fig02_garrett_q22(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.2), constrained_layout=True)

    det = [r for r in cat if r["radio_detected"] == "True" and r["k3_trigger"] == "False"]
    ulim = [r for r in cat if r["radio_detected"] == "False" and r["k3_trigger"] == "False"]
    trig_set = {r["PGC"]: r for r in vet}

    # Panel 1: S_22um vs S_1.4GHz_eq (Garrett 2015 plane)
    ax1.scatter([float(r["f22_mjy"]) for r in ulim], [float(r["s14_eq_or_lim_mjy"]) for r in ulim],
                s=14, marker="v", c="#999999", alpha=0.45, label=f"Radio 5-sigma Upper Limits (n={len(ulim)})")
    ax1.scatter([float(r["f22_mjy"]) for r in det], [float(r["s14_eq_or_lim_mjy"]) for r in det],
                s=18, c="#0072B2", alpha=0.72, label=f"Radio-Detected Galaxies (n={len(det)}, med q22=0.99)")
    ax1.scatter([float(r["f22_mjy"]) for r in vet], [float(r["s14_eq_or_lim_mjy"]) for r in vet],
                s=85, marker="*", c="#D55E00", edgecolors="#111", lw=0.6, zorder=5, label=f"All 11 K-III Triggers (All Radio-Detected, 0 ETI)")

    f22_grid = np.logspace(0.0, 5.2, 100)
    ax1.plot(f22_grid, f22_grid / 10.0 ** 0.99, color="#111111", lw=1.6, ls="-", label=r"Garrett Starburst Correlation ($q_{22} = 0.99$)")
    ax1.plot(f22_grid, f22_grid / 10.0 ** 2.00, color="#B00020", lw=1.5, ls="--", label=r"Radio-Quiet Type III Gate ($q_{22} = 2.0$, 10x deficit)")
    ax1.fill_between(f22_grid, 0.01, f22_grid / 10.0 ** 2.0, color="#B00020", alpha=0.07)

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0, 2e5)
    ax1.set_ylim(0.1, 2e4)
    ax1.set_xlabel(r"WISE W4 22 $\mu$m Flux Density $S_{22\,\mu\mathrm{m}}$ (mJy)")
    ax1.set_ylabel(r"1.4 GHz-Equivalent Radio Flux / 5$\sigma$ Limit (mJy)")
    ax1.set_title("Garrett (2015) Radio-Infrared Correlation Across 1,381 Galaxies")
    ax1.grid(True, which="both", alpha=0.25, ls=":")
    ax1.legend(loc="upper left", fontsize=7.9, framealpha=0.95)

    # Panel 2: q_22 vs gamma_III
    ax2.scatter([float(r["gamma_iii"]) for r in ulim], [float(r["q22"]) for r in ulim],
                s=14, marker="v", c="#999999", alpha=0.45, label="Radio Upper Limit (Lower Bound q22)")
    ax2.scatter([float(r["gamma_iii"]) for r in det], [float(r["q22"]) for r in det],
                s=18, c="#0072B2", alpha=0.72, label="Radio Detected (Exact q22)")
    for r in vet:
        ax2.scatter(float(r["gamma_iii"]), float(r["q22"]), s=90, marker="*", c="#D55E00", edgecolors="#111", lw=0.6, zorder=5)
        if r["NED"].strip() in ("MESSIER 077", "NGC 4355", "UGC 05776"):
            offset = (8, 4) if r["NED"].strip() == "UGC 05776" else (-30, -14)
            ax2.annotate(r["NED"].strip(), xy=(float(r["gamma_iii"]), float(r["q22"])), xytext=offset, textcoords="offset points", fontsize=7.8)

    ax2.axvline(0.25, color="#D55E00", ls=":", lw=1.3, label=r"Waste-Heat Gate ($\gamma_{\mathrm{III}} \geq 0.25$)")
    ax2.axhline(2.0, color="#B00020", ls="--", lw=1.3, label=r"Radio-Quiet Gate ($q_{22} \geq 2.0$)")
    rect = patches.Rectangle((0.25, 2.0), 0.72, 2.0, facecolor="#B00020", alpha=0.07)
    ax2.add_patch(rect)
    ax2.text(0.60, 3.35, "Radio-Silent K-III\n0 Unexplained\n(All 11 Starburst/AGN)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#8B0000")
    ax2.set_xlim(0.0, 0.95)
    ax2.set_ylim(-1.6, 3.8)
    ax2.set_xlabel(r"Mid-IR Waste-Heat Fraction $\gamma_{\mathrm{III}}$ ($\hat{G}$ Proxy)")
    ax2.set_ylabel(r"$q_{22} = \log_{10}(S_{22\,\mu\mathrm{m}} / S_{1.4\,\mathrm{GHz,eq}})$")
    ax2.set_title("Type III Waste-Heat vs. Radio-IR Excess Diagnostic")
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="lower right", fontsize=8.0, framealpha=0.95)

    fig.suptitle(r"Extragalactic Garrett $q_{22}$ & Wright $\hat{G}$ Selection Across the Local Supercluster", fontweight="bold")
    save_both(fig, "figN6_02_garrett_q22_radio_ir_correlation.png")


def fig03_ghat_and_wise(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 5.2), constrained_layout=True)
    quiet = [r for r in cat if r["k3_trigger"] == "False"]

    ax1.scatter([float(r["logMtot"]) for r in quiet], [float(r["gamma_iii"]) for r in quiet],
                s=16, c="#0072B2", alpha=0.65, label=f"Normal / Star-Forming Galaxies (n={len(quiet)})")
    ax1.scatter([float(r["logMtot"]) for r in vet], [float(r["gamma_iii"]) for r in vet],
                s=90, marker="*", c="#D55E00", edgecolors="#111", lw=0.6, zorder=5, label=f"K-III Triggers (All 11 Vetted: Starburst/AGN)")
    for r in vet:
        nm = r["NED"].strip()
        if nm in ("NGC 4355", "MESSIER 077", "NGC 4194"):
            off = (-54, 4) if nm == "NGC 4355" else (6, 4)
            ax1.annotate(nm, xy=(float(r["logMtot"]), float(r["gamma_iii"])), xytext=off, textcoords="offset points", fontsize=8.0)

    ax1.axhline(0.25, color="#D55E00", ls=":", lw=1.2, label="25% Waste-Heat Gate")
    ax1.axhline(0.50, color="#B00020", ls="--", lw=1.2, label="50% Extreme Waste-Heat Gate")
    ax1.axvline(10.0, color="#009E73", ls="-.", lw=1.1, label="Milky Way Mass Threshold (logM* >= 10)")
    ax1.set_xlim(8.9, 11.7)
    ax1.set_ylim(-0.02, 1.08)
    ax1.set_xlabel(r"Total Stellar Mass $\log_{10}(M_* / M_\odot)$")
    ax1.set_ylabel(r"Mid-IR Waste-Heat Fraction $\gamma_{\mathrm{III}}$")
    ax1.set_title("Galaxy Stellar Mass vs. Mid-IR Waste-Heat Fraction (0 K-III)")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="upper right", fontsize=7.8, framealpha=0.95)

    # Panel 2: WISE W1-W2 vs W1-W4
    ax2.scatter([float(r["W1_W4"]) for r in quiet], [float(r["W1_W2"]) for r in quiet],
                s=16, c="#0072B2", alpha=0.65, label="Normal Supercluster Galaxies")
    ax2.scatter([float(r["W1_W4"]) for r in vet], [float(r["W1_W2"]) for r in vet],
                s=90, marker="*", c="#D55E00", edgecolors="#111", lw=0.6, zorder=5, label="Vetted AGN/CON & Compact Starbursts")
    ax2.axhline(0.8, color="#B00020", ls="--", lw=1.2, label="Stern WISE AGN Wedge (W1-W2 >= 0.8)")
    ax2.axvline(5.0, color="#D55E00", ls=":", lw=1.2, label="Warm Dust / Type III Threshold (W1-W4 >= 5.0)")
    ax2.set_xlim(1.2, 10.6)
    ax2.set_ylim(-0.4, 1.6)
    ax2.set_xlabel("WISE W1 - W4 Color (mag)")
    ax2.set_ylabel("WISE W1 - W2 Color (mag)")
    ax2.set_title("WISE Color-Color Diagnostic: Starbursts vs. AGN Wedge")
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=8.0, framealpha=0.95)

    fig.suptitle(r"Wright $\hat{G}$ Waste-Heat Distribution & WISE Infrared Color Separation", fontweight="bold")
    save_both(fig, "figN6_03_ghat_waste_heat_and_wise_colors.png")


def fig04_cutouts_and_funnel(phot: list[dict[str, Any]], s3: dict[str, Any]) -> None:
    # Show 3 paired VLASS (3 GHz) + Legacy DR10 optical cutouts + right-hand Funnel
    by_pgc = {r["PGC"]: r for r in phot}
    chosen_pgcs = []
    for p in ("10266", "40762", "49191", "31601", "40564"):
        if p in by_pgc and by_pgc[p].get("ls_jpg") and len(chosen_pgcs) < 3:
            chosen_pgcs.append(p)
    for r in phot:
        if len(chosen_pgcs) >= 3:
            break
        if r.get("ls_jpg") and r["PGC"] not in chosen_pgcs:
            chosen_pgcs.append(r["PGC"])

    fig = plt.figure(figsize=(12.8, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(3, 3, width_ratios=[1, 1, 1.35])

    for row_i, pgc in enumerate(chosen_pgcs):
        r = by_pgc[pgc]
        # Optical DR10 JPEG
        ax_o = fig.add_subplot(gs[row_i, 0])
        img = Image.open(INP / "ls_cutouts" / r["ls_jpg"])
        ax_o.imshow(img)
        ax_o.set_xticks([])
        ax_o.set_yticks([])
        ax_o.set_title(f"{r['NED'].strip()} (Opt DR10)\nD={float(r['dist_mpc']):.1f} Mpc, g={float(r['gamma_iii']):.2f}", fontsize=8.4)

        # VLASS 3 GHz FITS
        ax_v = fig.add_subplot(gs[row_i, 1])
        with fits.open(INP / "vlass_cutouts" / r["fits_file"]) as hdul:
            dat = np.array(hdul[0].data, dtype=float)
        mad = 1.4826 * np.nanmedian(np.abs(dat - np.nanmedian(dat)))
        if mad < 0.02:
            dat = dat * 1000.0
        vmax = max(0.8, np.nanpercentile(dat, 99.6))
        vmin = -0.25 * vmax if vmax < 3.0 else -0.5
        ax_v.imshow(dat, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax, extent=[-24, 24, -24, 24])
        ax_v.add_patch(patches.Circle((0, 0), 7.5, fill=False, edgecolor="#00FFFF", lw=1.0))
        ax_v.set_title(f"VLASS 1.2 (3 GHz): Pk={float(r['vlass_peak_mjy']):.2f} mJy\nSNR={float(r['vlass_snr']):.1f}, q22_VL={r['q22_vlass_3ghz_scaled']}", fontsize=8.4)
        if row_i == 2:
            ax_v.set_xlabel("dRA (arcsec)")
        ax_v.set_ylabel("dDec (\")", fontsize=8.0)

    # Funnel
    ax_f = fig.add_subplot(gs[:, 2])
    vc = s3["vetting_class_counts"]
    stages = [
        ("HECATE Local Supercluster", s3["galaxies_analyzed_stage2"], "#0072B2"),
        ("Milky-Way Mass (logM>=10)", 627, "#56B4E9"),
        ("All-Sky Radio Covered", s3["galaxies_analyzed_stage2"], "#009E73"),
        ("K-III Stage 2 Triggers", s3["k3_triggers_total"], "#E69F00"),
        ("Live Radio Counterparts", s3["k3_triggers_with_live_radio_detection"], "#D55E00"),
        ("AGN / CON Core (W1-W2/X)", vc.get("KNOWN_AGN_SEYFERT_OR_CON", 0), "#999999"),
        ("BCD / Markarian HII", vc.get("COMPACT_DWARF_STARBURST_OR_HII", 0), "#CC79A7"),
        ("FIR Starburst Spiral", vc.get("KNOWN_STARBURST_OR_BARRED_SPIRAL", 0), "#009E73"),
        ("Verified K-III ETI", s3["verified_k3_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    ax_f.barh(ys, vals, color=[c for _, _, c in stages], height=0.62, edgecolor="#111")
    ax_f.set_xscale("log")
    ax_f.set_xlim(0.5, 4500)
    ax_f.set_yticks(ys)
    ax_f.set_yticklabels([s for s, _, _ in stages], fontsize=8.5)
    for y, (_, v, _) in zip(ys, stages):
        ax_f.text(max(v, 0.8) * 1.18, y, f"{v}", va="center", fontweight="bold", fontsize=9.0)
    ax_f.set_xlabel("Galaxies (log scale)")
    ax_f.set_title("Kardashev Type III Vetting Funnel\n(1,381 Galaxies -> 11 -> 0 ETI)")
    ax_f.grid(axis="x", alpha=0.28, ls=":")

    fig.suptitle("Legacy DR10 Optical + VLASS 1.2 (3 GHz) Nuclear Radio Verification & K-III Funnel", fontweight="bold")
    save_both(fig, "figN6_04_vlass_optical_cutouts_and_veto_funnel.png")


def fig05_injections_and_f95(summary: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.1), constrained_layout=True)

    ig = summary["injection_grid"]
    gs_vals = sorted(ig.keys(), key=lambda k: float(k))
    xs = np.array([float(k) * 100.0 for k in gs_vals])
    ys = np.array([ig[k]["completeness"] * 100.0 for k in gs_vals])
    errs = 100.0 * np.sqrt(np.clip((ys / 100.0) * (1.0 - ys / 100.0) / 200.0, 0.0, 1.0))

    ax1.errorbar(xs, ys, yerr=errs, fmt="-o", color="#0072B2", lw=2.0, ms=7, capsize=4, label="1,200-Trial Radio-Quiet Type III Injections")
    ax1.axvline(30.0, color="#D55E00", ls=":", lw=1.4, label=f"gamma >= 30% ({summary['injection_completeness_ge_0p30']*100:.2f}% Completeness)")
    for x, y in zip(xs, ys):
        ax1.text(x, y + 3.5, f"{y:.1f}%", ha="center", va="bottom", fontsize=8.4)
    ax1.set_ylim(-5, 114)
    ax1.set_xlim(0, 82)
    ax1.set_xlabel(r"Injected Radio-Quiet Galaxy Starlight Capture $\gamma_{\mathrm{III}}$ (%)")
    ax1.set_ylabel("Catalog Detection Completeness (%)")
    ax1.set_title("Kardashev Type III Waste-Heat Injection Recovery (N=1,200)")
    ax1.grid(True, alpha=0.28, ls=":")
    ax1.legend(loc="lower right", fontsize=8.2)

    bl = summary["bayesian_limits_zero_k3"]
    cohorts = [
        ("All Supercluster\n(n_eff=1,280)", bl["all_local_supercluster_galaxies"]),
        ("Radio Detected\n(n=839)", bl["radio_detected_q22_galaxies"]),
        ("Milky Way Mass+\n(n=627, logM>=10)", bl["milky_way_mass_logM_ge_10"]),
        ("Nearby <=20 Mpc\n(n=373)", bl["nearby_20mpc_galaxies"]),
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
        ax2.text(xi - w, jv + 0.015, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.8, rotation=40)
        ax2.text(xi + 0.05, uv + 0.015, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.8, rotation=40)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.6)
    ax2.set_ylim(0, 1.02)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ on Type III Galaxies (%)")
    ax2.set_title(r"Zero-Detection 95% Bayesian Prevalence Upper Limits ($f_{95}$)")
    ax2.grid(axis="y", alpha=0.28, ls=":")
    ax2.legend(loc="upper left", fontsize=8.3)

    fig.suptitle("Spor N6 Type III Injection Calibration & Extragalactic Bayesian Null Bounds", fontweight="bold")
    save_both(fig, "figN6_05_k3_injection_recovery_and_bayesian_f95.png")


def fig06_kardashev_synthesis(summary: dict[str, Any]) -> None:
    # Unified Scale Map from 1 AU Solar System -> Local Supercluster 40 Mpc across K-I, K-II, K-III
    rows = [
        ("Spor N2: Rubin SSOFT + Trails", "1 - 40 AU (Solar System)", 0.1403, "#CC79A7", "K-I Probes & Orbits"),
        ("Spor N3: Rubin V2+V3 Optical DDF", "10 pc - 10 kpc (2,100 stars)", 0.1133, "#0072B2", "K-I/II Optical Transients"),
        ("Spor N1C: VASCO Multi-Decade", "1 pc - 10 kpc (1,197 stars)", 0.1603, "#009E73", "K-II Vanishing Stars"),
        ("Spor N4: 71.92-Oct Radio Bridge", "1.3 pc - 3 kpc (1,083 stars)", 0.1772, "#D55E00", "K-II 54 MHz-3 GHz + FRB"),
        ("Spor N5: 10-Yr Secular IR+Opt", "1.3 pc - 3 kpc (1,083 stars)", 0.1772, "#E69F00", "K-II 2010-2024 Construction"),
        ("Spor N6: Local Supercluster K-III", "0.5 - 40 Mpc (1,381 galaxies)", summary["bayesian_limits_zero_k3"]["all_local_supercluster_galaxies"]["jeffreys_f95_pct"], "#B00020", "K-III: ~4.1e13 stars, 0 ETI"),
    ]
    fig, ax = plt.subplots(figsize=(12.2, 5.2), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    vals = [r[2] for r in rows]
    ax.barh(ys, vals, height=0.60, color=[r[3] for r in rows], edgecolor="#111", lw=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r[0]}\n[{r[1]}]" for r in rows], fontsize=8.8)
    ax.set_xlim(0, 0.34)
    for y, (_, _, v, _, desc) in zip(ys, rows):
        ax.text(v + 0.005, y, f"Jeffreys f95 = {v:.4f}%  ({desc})", va="center", ha="left", fontsize=8.8)
    ax.set_xlabel(r"95% Jeffreys Bayesian Upper Limit $f_{95}$ (%) on ETI Prevalence (All Verified 0 ETI)")
    ax.set_title("Grand SETI Scale Synthesis: Kardashev Type I -> Type II -> Type III (1 AU to 40 Mpc, 0 ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.28, ls=":")
    save_both(fig, "figN6_06_kardashev_scale_synthesis_k1_to_k3.png")


def main() -> int:
    summary = json.loads((RES / "N6_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N6_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    cat = list(csv.DictReader((RES / "N6_SUPERCLUSTER_K3_CATALOG.csv").open(encoding="utf-8")))
    vet = list(csv.DictReader((RES / "N6_K3_CANDIDATES_VETTED.csv").open(encoding="utf-8")))
    phot = list(csv.DictReader((RES / "N6_VLASS_GALAXY_PHOTOMETRY.csv").open(encoding="utf-8")))

    fig01_supercluster_map(cat, vet)
    fig02_garrett_q22(cat, vet)
    fig03_ghat_and_wise(cat, vet)
    fig04_cutouts_and_funnel(phot, s3)
    fig05_injections_and_f95(summary)
    fig06_kardashev_synthesis(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
