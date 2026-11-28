#!/usr/bin/env python3
"""Plot 6 publication-grade 300-DPI PNGs for Spor N11B (HARPS Single-Epoch Transient Optical Laser SETI)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta as sp_beta

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
RES = WS / "results"
FIG = WS / "figures"

plt.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "legend.fontsize": 8.0,
    "figure.facecolor": "white",
    "axes.facecolor": "#fafafa",
    "axes.grid": True,
    "grid.alpha": 0.28,
})


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    star_rows = load_csv(RES / "N11B_STAR_SUMMARY.csv")
    peak_rows = load_csv(RES / "N11B_PEAK_DIAGNOSTICS.csv")
    s2 = json.loads((RES / "N11B_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N11B_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n11b_cutouts.npz")

    # Fig 01: HARPS 20-Epoch BERV Baselines & 10-sigma Beamed Laser Power Limits
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.2))
    stars = [r["star"] for r in star_rows]
    ys = np.arange(len(stars))[::-1]
    bervs = [float(r["berv_span_kms"]) for r in star_rows]
    yrs = [float(r["mjd_span_days"]) / 365.25 for r in star_rows]
    bars = ax1.barh(ys, bervs, color="#377eb8", edgecolor="black", height=0.56, label="BERV Span (km/s)")
    for b, bv, yr in zip(bars, bervs, yrs):
        ax1.text(bv + 1.0, b.get_y() + b.get_height() / 2, f"{bv:.1f} km/s ({yr:.1f} yr)", va="center", ha="left", fontsize=8.3, fontweight="bold")
    ax1.set_yticks(ys)
    ax1.set_yticklabels([f"{r['common_name']} ({int(r['n_exoplanets'])} pl)" for r in star_rows], fontsize=8.8)
    ax1.set_xlim(0, 76)
    ax1.set_xlabel("Barycentric Earth Radial Velocity (BERV) Span (km/s)")
    ax1.set_title("A. 160 HARPS Phase-3 Epochs Across 8 Milky Way Hosts")

    dists = [float(r["dist_pc"]) for r in star_rows]
    ptx = [float(r["p_tx_10sig_kw"]) for r in star_rows]
    ax2.scatter(dists, ptx, s=85, color="#1b9e77", edgecolor="black", zorder=4, label="10σ Monochromatic Laser Limit (D_tx=10 m)")
    offsets = {
        "PROXIMACEN": (8, -2),
        "BARNARDSSTAR": (-78, -14),
        "ROSS128": (8, 5),
        "GJ1061": (10, -4),
        "YZCET": (10, -4),
        "GJ273": (8, 5),
        "GJ667C": (-48, 8),
        "L9859": (-45, -14),
    }
    for d, p, st in zip(dists, ptx, stars):
        ox, oy = offsets.get(st, (5, 5))
        lbl = f"{st} ({p:.2f} kW)" if p >= 1.0 else f"{st} ({p*1000:.0f} W)"
        ax2.annotate(lbl, (d, p), xytext=(ox, oy), textcoords="offset points", fontsize=8.0,
                     arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6) if st in ("BARNARDSSTAR", "GJ1061", "ROSS128") else None)
    ax2.set_yscale("log")
    ax2.set_ylim(0.05, 15.0)
    ax2.set_xlim(0.5, 12.0)
    ax2.set_xlabel("Distance (pc)")
    ax2.set_ylabel("Minimum Detectable Laser Power (kW, D_tx=10 m)")
    ax2.set_title("B. Single-Epoch Optical Laser Sensitivity (108 W – 6.87 kW)")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.94)
    fig.suptitle("Spor N11B: 160 ESO HARPS Spectra Over Multi-Year BERV Baselines & Laser Sensitivity", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11B_01_harps_epochs_berv_and_power.png", dpi=300)
    plt.close(fig)

    # Fig 02: 1,200-Trial Head-to-Head Benchmark + Proxima Cen Real-Noise Injection Cutouts
    fig = plt.figure(figsize=(13.4, 7.8))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.1, 1.0], hspace=0.38, wspace=0.25)
    ax_top = fig.add_subplot(gs[0, :])
    morphs = ["TRANSIENT_PSF_LASER", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"]
    mlbls = [
        "Single-Epoch PSF Laser\n(True Positives, 400 trials)",
        "1–2 px Sharp Cosmic Ray\n(False Positive Rate, 400 trials)",
        "2.6–5.5× Broad Stellar Flare\n(False Positive Rate, 400 trials)",
    ]
    pm = s2["injections"]["per_morphology"]
    n11b_r = [100.0 * pm[m]["n11b_rate"] for m in morphs]
    cls_r = [100.0 * pm[m]["classical_stack_rate"] for m in morphs]
    xb = np.arange(3)
    b1 = ax_top.bar(xb - 0.17, n11b_r, width=0.33, color="#1b9e77", edgecolor="black", label="Spor N11B LOEO + PSF Matched-Filter + Shape Gate")
    b2 = ax_top.bar(xb + 0.17, cls_r, width=0.33, color="#d95f02", edgecolor="black", label="Classical 20-Epoch Static Median Stack (Blinded to Transients)")
    for rct, v in zip(b1, n11b_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.8, color="#0d5c46")
    for rct, v in zip(b2, cls_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.8, color="#8f3900")
    ax_top.set_xticks(xb)
    ax_top.set_xticklabels(mlbls, fontsize=9.5)
    ax_top.set_ylim(0, 120)
    ax_top.set_ylabel("Trigger Rate (%)")
    ax_top.set_title("A. 1,200-Trial Real HARPS Noise Benchmark: 92.0% Transient Laser Completeness at 0.0% CR / Flare FPR")
    ax_top.legend(loc="upper right", frameon=True, framealpha=0.95)

    ititles = ["B1. PSF Laser (PASS, 0.90–1.10× PSF)", "B2. Sharp Cosmic Ray (Vetoed by FWHM/pix)", "B3. Broad Stellar Flare (Vetoed >1.5× PSF)"]
    dlam = (np.arange(51) - 25) * 0.01
    for ci, m in enumerate(morphs):
        ax = fig.add_subplot(gs[1, ci])
        rz = npz[f"INJ_{m}_RESZ"]
        zmf = npz[f"INJ_{m}_ZMF"]
        stz = npz[f"INJ_{m}_STACKZ"]
        ax.step(dlam, rz, where="mid", color="#7570b3", lw=1.2, alpha=0.85, label="Pixel Z (LOEO)")
        ax.plot(dlam, zmf, color="#1b9e77", lw=1.8, label="PSF Z_mf (LOEO)")
        ax.plot(dlam, stz, color="#d95f02", lw=1.4, ls="--", label="Median Stack Z")
        ax.axhline(10.0, color="#333333", ls=":", lw=0.9)
        ax.set_title(ititles[ci], fontsize=9.2)
        ax.set_xlabel("Δλ (Å)")
        if ci == 0:
            ax.set_ylabel("Residual SNR (σ)")
            ax.legend(loc="upper left", fontsize=7.5, frameon=True)
    fig.suptitle("Spor N11B: Overcoming Multi-Epoch Median Blindness & Cosmic-Ray Confusion in HARPS", fontweight="bold", y=0.985)
    fig.savefig(FIG / "figN11B_02_head_to_head_transient_benchmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Fig 03: Real Proxima Cen TiO Molecular Forest Subtraction (LOEO Proof)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13.2, 6.0), sharex=True, gridspec_kw={"height_ratios": [1.3, 1.0]})
    t_lam = npz["TIO_LAM"]
    ep0 = npz["TIO_EP0_NORM"]
    tmpl = npz["TIO_TEMPLATE"]
    res0 = npz["TIO_RESIDUAL"]
    ax1.plot(t_lam, ep0, color="#377eb8", lw=0.9, alpha=0.8, label="Proxima Cen Single Epoch 0 (Normalized)")
    ax1.plot(t_lam, tmpl, color="#111111", lw=1.1, label="19-Epoch LOEO Static Median Template T_loeo")
    ax1.set_ylabel("Normalized Flux")
    ax1.set_title("A. Dense M5.5V TiO Molecular Forest (6155–6180 Å): Static Stellar Spectrum Repeats Identically Across Epochs")
    ax1.legend(loc="upper right", frameon=True)

    ax2.plot(t_lam, res0, color="#1b9e77", lw=0.9, label=f"LOEO Differential Residual (MAD σ = {1.4826*np.median(np.abs(res0)):.4f})")
    ax2.axhline(0.0, color="#333333", ls="--", lw=0.9)
    ax2.set_ylim(-0.35, 0.35)
    ax2.set_xlabel("Barycentric Wavelength (Å)")
    ax2.set_ylabel("Residual Flux (Ep0 - T_loeo)")
    ax2.set_title("B. Complete Cancellation of Stellar TiO Absorption Enabling Single-Epoch Laser Search Inside Line Forests")
    ax2.legend(loc="upper right", frameon=True)
    fig.suptitle("Spor N11B: High-Contrast Leave-One-Epoch-Out Stellar Forest Cancellation on Real HARPS Data", fontweight="bold", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "figN11B_03_loeo_tio_forest_subtraction.png", dpi=300)
    plt.close(fig)

    # Fig 04: 463 Z>=10 HARPS Peaks PSF Shape Diagnostics & Stage 3 Veto Breakdown
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4))
    cat_styles = {
        "SHARP_COSMIC_RAY": ("#e41a1c", "o", "Sharp Cosmic Ray (<0.8× PSF)"),
        "BROAD_OR_DISTORTED": ("#984ea3", "^", "Broad Flare / Distortion (>1.5× PSF)"),
        "PERSISTENT_N_GT_3": ("#ff7f00", "D", "Persistent Stellar/Sky (N>3)"),
        "T1_TRANSIENT_LASER_PASS": ("#1b9e77", "*", "T1 Transient Candidates (to Stage 3)"),
    }
    for cat, (col, mk, lbl) in cat_styles.items():
        sub = [p for p in peak_rows if p["stage2_status"] == cat]
        if sub:
            fr = [float(p["fwhm_ratio"]) for p in sub]
            rg = [float(p["r_gauss"]) for p in sub]
            sz = 95 if cat == "T1_TRANSIENT_LASER_PASS" else 28
            ax1.scatter(fr, rg, s=sz, color=col, marker=mk, alpha=0.8, label=f"{lbl} ({len(sub)})", zorder=4 if cat == "T1_TRANSIENT_LASER_PASS" else 2)
    ax1.add_patch(plt.Rectangle((0.80, 0.88), 0.70, 0.12, fill=False, edgecolor="#1b9e77", lw=2.0, ls="--", label="Locked PSF Box [0.80–1.50, r>=0.88]"))
    ax1.set_xlim(0.15, 3.8)
    ax1.set_ylim(0.65, 1.02)
    ax1.set_xlabel("Fitted FWHM / HARPS PSF FWHM Ratio")
    ax1.set_ylabel("Core Gaussian Fit Correlation (r_gauss)")
    ax1.set_title("A. All 463 Z_mf >= 10 HARPS Peaks (4800–6900 Å)")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=7.6)

    vb = s3["veto_breakdown"]
    v_items = sorted([(k, v) for k, v in vb.items() if v > 0], key=lambda kv: kv[1], reverse=True)
    v_labels = [k.replace("_", " ").title().replace("Simcal Fiber B Wave Bleed", "Simultaneous Fiber-B\nThAr/FP Bleed (STAR,WAVE)").replace("Terrestrial Airglow Or Telluric", "Terrestrial Sky / O2-H2O\n([OI], NaD, Cross-Star)").replace("Single Exposure Cosmic Ray Nonrepeating", "Non-Repeating Cosmic Ray\n(Live ESO Follow-up <3σ)").replace("Chromospheric M Dwarf Flare", "Chromospheric M-Dwarf Flare\n(Hα/Hβ & Active Lines)").replace("Isolated Single Exp Cosmic Ray Uncorroborated", "Solitary 1-of-20 Cosmic Ray\n(No Archive Adj. Exposure)") for k, _ in v_items]
    v_vals = [v for _, v in v_items]
    yv = np.arange(len(v_items))[::-1]
    cols_v = ["#377eb8", "#e41a1c", "#ff7f00", "#984ea3", "#66a61e", "#7f0000"][:len(v_items)]
    bars2 = ax2.barh(yv, v_vals, color=cols_v, edgecolor="black", height=0.56)
    for b, v in zip(bars2, v_vals):
        ax2.text(v + 0.6, b.get_y() + b.get_height() / 2, str(v), va="center", ha="left", fontweight="bold", fontsize=9.2)
    ax2.set_yticks(yv)
    ax2.set_yticklabels(v_labels, fontsize=8.3)
    ax2.set_xlim(0, max(v_vals) + 6 if v_vals else 10)
    ax2.set_xlabel("Vetted T1 Triggers (Total = 60 -> 0 Verified ETI)")
    ax2.set_title("B. Stage 3 Forensic Vetting Including Live Adjacent HARPS Check")
    fig.suptitle("Spor N11B: PSF Shape Discrimination (463 -> 60) & Live-Archive Stage 3 Vetting (60 -> 0 ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11B_04_shape_diagnostics_and_stage3_veto.png", dpi=300)
    plt.close(fig)

    # Fig 05: Vetting Funnel & Exact Bayesian Zero-ETI Bounds
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    stages = [
        "All Z_mf >= 10\n(4800–6900 Å,\n160 Spectra)",
        "Transient & PSF\n(N_ep <= 3,\n0.8–1.5× PSF)",
        "Unvetoed After\nSky/ThAr/Flare\n& ESO Follow-up",
        "Verified\nOptical\nLaser ETI",
    ]
    scounts = [s2["peaks_z10_before_shape_veto"], s2["stage2_t1_triggers_total"], s3["verified_eti_candidates"], s3["verified_eti_candidates"]]
    xs = np.arange(len(stages))
    b_f = ax1.bar(xs, [max(c, 0.22) if c == 0 else c for c in scounts], bottom=0.15, color=["#377eb8", "#7570b3", "#ff7f00", "#1b9e77"], edgecolor="black", width=0.52)
    ax1.set_yscale("log")
    ax1.set_ylim(0.15, 1600)
    for b, c in zip(b_f, scounts):
        y_txt = (c * 1.25) if c > 0 else 0.55
        ax1.text(b.get_x() + b.get_width() / 2, y_txt, str(c), ha="center", va="bottom", fontweight="bold", fontsize=10.5)
    ax1.set_xticks(xs)
    ax1.set_xticklabels(stages, fontsize=8.2)
    ax1.set_ylabel("Trigger Count (log)")
    ax1.set_title("A. Multi-Stage Transient Optical Laser Vetting Funnel (463 -> 0 ETI)")

    bl = s2["provisional_zero_eti_bayesian_bounds"]
    bl_lbls = ["Stars Raw\n(N=8)", "Stars Eff\n(N_eff=7.36)", "Epochs Raw\n(N=160)", "Epochs Eff\n(N_eff=147.2)"]
    jf = [bl["stars_raw_8"]["jeffreys_f95_pct"], bl["stars_eff"]["jeffreys_f95_pct"], bl["epochs_raw_160"]["jeffreys_f95_pct"], bl["epochs_eff"]["jeffreys_f95_pct"]]
    un = [bl["stars_raw_8"]["uniform_f95_pct"], bl["stars_eff"]["uniform_f95_pct"], bl["epochs_raw_160"]["uniform_f95_pct"], bl["epochs_eff"]["uniform_f95_pct"]]
    xb2 = np.arange(4)
    ax2.bar(xb2 - 0.18, jf, width=0.35, color="#1b9e77", edgecolor="black", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax2.bar(xb2 + 0.18, un, width=0.35, color="#7570b3", edgecolor="black", label="Uniform Beta(1, N_eff+1)")
    for i, (jv, uv) in enumerate(zip(jf, un)):
        ax2.text(i - 0.18, jv * 1.15, f"{jv:.2f}%", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
        ax2.text(i + 0.18, uv * 1.15, f"{uv:.2f}%", ha="center", va="bottom", fontsize=8.0)
    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 65)
    ax2.set_xticks(xb2)
    ax2.set_xticklabels(bl_lbls, fontsize=8.8)
    ax2.set_ylabel("95% Upper Prevalence Limit f_95 (%)")
    ax2.set_title("B. Bayesian Zero-ETI Bounds for Single-Epoch Optical Lasers")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.94)
    fig.suptitle("Spor N11B: Complete Vetting Collapse (463 -> 60 -> 0 ETI) & Prevalence Constraints", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11B_05_vetting_funnel_and_bayesian_f95.png", dpi=300)
    plt.close(fig)

    # Fig 06: N10 + N11A + N11B Milky Way Blind-Spot Synthesis
    fig, ax = plt.subplots(1, 1, figsize=(12.6, 5.4))
    cats = [
        "Classical Baselines\n(turboSETI 1-Bin / Median Stack)",
        "Spor N10: Broadband GBT L-Band\n(36 HDF5, 6 <5pc M-Dwarfs, 1,200 inj.)",
        "Spor N11A Primary: 2.8 Hz Water Hole\n(54 HTTP-Range Slices, 9 <=6pc, Gajjar)",
        "Spor N11B: HARPS Optical Transient Laser\n(160 Spectra, 8 <11pc Hosts, 400 inj.)",
    ]
    vals = [0.0, 90.33, 92.5, 92.0]
    cols = ["#d95f02", "#377eb8", "#7570b3", "#1b9e77"]
    yp = np.arange(len(cats))[::-1]
    bars = ax.barh(yp, vals, color=cols, edgecolor="black", height=0.54)
    notes = ["0.0% Blind-Spot Recovery", "0 ETI (136 vetoed) | 171–621 GW", "0 ETI (576 blocks; 55.2% 3-cls) | 5.4–29.8 GW", "0 ETI (60 vetoed) | 0.11–6.87 kW"]
    for b, v, nt in zip(bars, vals, notes):
        ax.text(v + 1.4, b.get_y() + b.get_height() / 2, f"{v:.1f}%  —  {nt}", va="center", ha="left", fontweight="bold", fontsize=8.9)
    ax.set_yticks(yp)
    ax.set_yticklabels(cats, fontsize=9.1)
    ax.set_xlim(0, 158)
    ax.set_xlabel("Verified Injection Completeness on Real Observatory Noise (%)")
    ax.set_title("Milky Way Blind-Spot Trilogy (N10 + N11A + N11B): >90% Completeness Across Radio & Optical Blind Spots -> 0 ETI")
    fig.tight_layout()
    fig.savefig(FIG / "figN11B_06_n10_n11a_n11b_blindspot_synthesis.png", dpi=300)
    plt.close(fig)
    print("[N11B Plot] Saved all 6 figures cleanly to", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
