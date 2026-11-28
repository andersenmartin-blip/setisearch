#!/usr/bin/env python3
"""Plot 6 publication-grade 300-DPI PNGs for Spor N11A (2.794 Hz Fine Water-Hole Gajjar Plasma SETI)."""
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
WS = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
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
    cad_rows = load_csv(RES / "N11A_CADENCE_SUMMARY.csv")
    diag_rows = load_csv(RES / "N11A_BLOCK_DIAGNOSTICS.csv")
    s2 = json.loads((RES / "N11A_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n11a_cutouts.npz")

    # Fig 01: Ultra-Quiet 2.794 Hz Water-Hole RFI Occupancy & 5.4-30 GW EIRP Sensitivity
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.2))
    cmap = plt.cm.tab10
    for idx, r in enumerate(cad_rows):
        st = r["star"]
        fq = npz[f"BP_FREQ_{st}"]
        rf = npz[f"BP_RFI_{st}"] * 100.0
        order = np.argsort(fq)
        ax1.plot(fq[order], rf[order], lw=1.25, alpha=0.85, color=cmap(idx % 10), label=f"{st} ({float(r['dist_pc']):.2f} pc)")
    ax1.axvline(1423.828, color="#555555", ls="--", lw=1.0, label="BLC Coarse-Channel DC Edge")
    ax1.set_xlabel("Frequency in Fine Water Hole (MHz)")
    ax1.set_ylabel("Channel RFI Occupancy (>5σ, %)")
    ax1.set_title("A. Ultra-Quiet 2.794 Hz Water Hole Across 9 Stars (54 Scans)")
    ax1.set_ylim(0, 0.095)
    ax1.legend(loc="upper left", ncol=2, frameon=True, framealpha=0.94, fontsize=7.5)

    dists = [float(r["dist_pc"]) for r in cad_rows]
    ew1 = [float(r["eirp_w1_gw"]) for r in cad_rows]
    ew16 = [float(r["eirp_w16_45hz_gw"]) for r in cad_rows]
    ew64 = [float(r["eirp_w64_179hz_gw"]) for r in cad_rows]
    ax2.scatter(dists, ew1, s=70, color="#1b9e77", marker="o", label="W=1 bin (2.8 Hz, 10σ)")
    ax2.scatter(dists, ew16, s=70, color="#7570b3", marker="s", label="W=16 bins (45 Hz Gajjar Plasma, 10σ)")
    ax2.scatter(dists, ew64, s=75, color="#d95f02", marker="^", label="W=64 bins (179 Hz Broad, 10σ)")
    star_offsets = {
        "GJ411": (5, -8),
        "GJ65A": (5, -10),
        "GJ866": (5, -8),
        "GJ54.1": (-28, -12),
        "GJ273": (5, -8),
        "GJ687": (-28, 7),
        "GJ1245AC": (5, -12),
        "GJ1002": (-30, 7),
        "HIP1242": (-30, -11),
    }
    for d, ew, st in zip(dists, ew1, [r["star"] for r in cad_rows]):
        ox, oy = star_offsets.get(st, (4, -10))
        ax2.annotate(st, (d, ew), xytext=(ox, oy), textcoords="offset points", fontsize=7.8)
    ax2.set_yscale("log")
    ax2.set_ylim(3.0, 500.0)
    ax2.set_xlabel("Distance (pc)")
    ax2.set_ylabel("Minimum Detectable Isotropic EIRP (GW)")
    ax2.set_title("B. 40× Deeper EIRP Sensitivity (5.4–29.8 GW, GBT SEFD=10 Jy)")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.94, fontsize=8.0)
    fig.suptitle("Spor N11A: Fine 2.794 Hz GBT Water-Hole Coverage & EIRP Limits Across Nine < 6 pc M-Dwarfs", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11A_01_fine_waterhole_and_eirp.png", dpi=300)
    plt.close(fig)

    # Fig 02: 1,200-Trial Head-to-Head Benchmark + Real 2.794 Hz Injected Waterfalls
    fig = plt.figure(figsize=(13.4, 7.8))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.1, 1.0], hspace=0.36, wspace=0.24)
    ax_top = fig.add_subplot(gs[0, :])
    morphs = ["GAJJAR_PLASMA_10_350HZ", "FINE_HARMONIC_COMB", "FINE_CURVED_ORBITAL"]
    mlbls = [
        "Gajjar Plasma-Broadened\n(17–126 Hz σ_f, Primary G1)",
        "Fine Harmonic Frequency Comb\n(10 Teeth @ 224–727 Hz, G3)",
        "Fine Curved Drift\n(Δd1=16 Grid vs W=1 Line, G2)",
    ]
    pm = s2["injections"]["per_morphology"]
    n11a_r = [100.0 * pm[m]["n11a_rate"] for m in morphs]
    cls_r = [100.0 * pm[m]["classical_1bin_rate"] for m in morphs]
    xb = np.arange(3)
    b1 = ax_top.bar(xb - 0.17, n11a_r, width=0.33, color="#1b9e77", edgecolor="black", label="Spor N11A Multi-Scale + Comb Detector (G1–G3)")
    b2 = ax_top.bar(xb + 0.17, cls_r, width=0.33, color="#d95f02", edgecolor="black", label="Classical 1-Bin Linear Baseline (turboSETI-analog, 0.0%)")
    for rct, v in zip(b1, n11a_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.8, color="#0d5c46")
    for rct, v in zip(b2, cls_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.8, color="#8f3900")
    ax_top.set_xticks(xb)
    ax_top.set_xticklabels(mlbls, fontsize=9.5)
    ax_top.set_ylim(0, 125)
    ax_top.set_ylabel("Injection Recovery Rate (%)")
    ax_top.set_title("A. 1,200 Real-Noise 2.794 Hz Injections: Blind-Spot vs. Classical 1-Bin Linear Pipeline")
    ax_top.legend(loc="upper center", ncol=2, frameon=True, framealpha=0.95)

    ititles = ["B1. Injected Gajjar Plasma (A1)", "B2. Injected 10-Tooth Comb (A1)", "B3. Injected Fine Curved Track (A1)"]
    for ci, m in enumerate(morphs):
        ax = fig.add_subplot(gs[1, ci])
        arr = npz[f"INJ_{m}"][0]
        vmax = max(float(np.percentile(arr, 99.0)), 3.0)
        ax.imshow(arr, aspect="auto", origin="lower", cmap="viridis", vmin=-1.5, vmax=vmax)
        ax.set_title(ititles[ci], fontsize=9.2)
        ax.set_xlabel("Rel. Fine Chan (2.79 Hz/bin)")
        if ci == 0:
            ax.set_ylabel("Time Step (18.25s)")
    fig.suptitle("Spor N11A: Resolving Gajjar Stellar-Wind Plasma Broadening at 2.794 Hz Resolution", fontweight="bold", y=0.985)
    fig.savefig(FIG / "figN11A_02_head_to_head_gajjar_benchmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Fig 03: Real Quiet ABACAD 2.794 Hz Waterfalls (6 scans x 2 injected/noise comparisons)
    fig, axes = plt.subplots(2, 6, figsize=(14.0, 5.4), sharex=True, sharey=True)
    roles = ["A1 (ON)", "B1 (OFF)", "A2 (ON)", "C1 (OFF)", "A3 (ON)", "D1 (OFF)"]
    for ci in range(6):
        c_gaj = npz["INJ_GAJJAR_PLASMA_10_350HZ"][ci]
        c_cmb = npz["INJ_FINE_HARMONIC_COMB"][ci]
        axes[0, ci].imshow(c_gaj, aspect="auto", origin="lower", cmap="magma", vmin=-2.0, vmax=4.0)
        axes[1, ci].imshow(c_cmb, aspect="auto", origin="lower", cmap="magma", vmin=-2.0, vmax=4.0)
        axes[0, ci].set_title(roles[ci], color=("#0b5394" if ci in (0, 2, 4) else "#666666"))
        axes[1, ci].set_xlabel("Rel. Chan (2.79 Hz)")
    axes[0, 0].set_ylabel("Gajjar Broadened\n(ON-only vs Real OFF)")
    axes[1, 0].set_ylabel("10-Tooth Harmonic Comb\n(ON-only vs Real OFF)")
    fig.suptitle("Spor N11A: 2.794 Hz Real-Background ABACAD Spectrogram Architecture (A1-B1-A2-C1-A3-D1)", fontweight="bold", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "figN11A_03_abacad_fine_waterfalls.png", dpi=300)
    plt.close(fig)

    # Fig 04: G3 Comb & RFI Floor Diagnostics Across All 576 Clean Blocks
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.1))
    c_on = np.array([float(r["comb_on2"]) for r in diag_rows])
    c_off = np.array([float(r["comb_off_max"]) for r in diag_rows])
    rfi_pct = np.array([float(r["rfi_5sig_pct"]) for r in diag_rows])
    ax1.scatter(c_off, c_on, s=16, alpha=0.6, color="#377eb8", label="All 576 Fine Blocks (0 Triggers)")
    ax1.plot([3.8, 300.0], [3.8, 300.0], color="#888888", ls="-.", lw=0.9, alpha=0.75, label="1:1 Terrestrial RFI Diagonal (ON = OFF)")
    ax1.axhline(14.0, color="#333333", ls="--", lw=1.1, label="G3 Comb ON Threshold (14.0)")
    ax1.axvline(10.0, color="#7f0000", ls=":", lw=1.1, label="G3 Comb OFF Veto (10.0)")
    ax1.fill_between([3.5, 10.0], 14.0, 320.0, color="#e41a1c", alpha=0.08, label="G3 ETI Region (0 Hits)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(3.5, 320.0)
    ax1.set_ylim(3.5, 320.0)
    ax1.set_xlabel("OFF Max Harmonic Comb Score (log)")
    ax1.set_ylabel("ON 2nd-Best Harmonic Comb Score (log)")
    ax1.set_title("A. G3 Spectral Comb Across 576 Blocks (OFF Veto Catches 227 Shared RFI)")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.94, fontsize=7.6)

    ax2.hist(rfi_pct, bins=30, color="#4daf4a", edgecolor="#111111", alpha=0.85)
    ax2.axvline(float(np.median(rfi_pct)), color="#b2182b", ls="--", lw=1.4, label=f"Median >5σ RFI = {float(np.median(rfi_pct)):.4f}%")
    ax2.set_xlabel("Per-Block >5σ RFI Occupancy (%)")
    ax2.set_ylabel("Number of 16,384-Ch Blocks")
    ax2.set_title("B. Ultra-Clean Fine Water-Hole Noise Quality (576 Blocks)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.94)
    fig.suptitle("Spor N11A: Clean Fine Water-Hole Quality & Comb Diagnostics (576 Blocks, 0 Triggers)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11A_04_comb_and_noise_diagnostics.png", dpi=300)
    plt.close(fig)

    # Fig 05: Bayesian Zero-ETI Bounds (Primary Gajjar vs Combined & Block Level)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    labels_b = [
        "Stars Raw\n(N=9)",
        "Gajjar Plasma\nEff (N_eff=8.33)",
        "3-Morph Mean\nEff (N_eff=4.97)",
        "Blocks Comb\nEff (N_eff=317.8)",
        "Gajjar Blocks\nEff (N_eff=532.8)",
    ]
    neffs = [9.0, 9.0 * 0.925, 4.965, 317.76, 576.0 * 0.925]
    jf = [100.0 * sp_beta.ppf(0.95, 0.5, ne + 0.5) for ne in neffs]
    un = [100.0 * sp_beta.ppf(0.95, 1.0, ne + 1.0) for ne in neffs]
    xi = np.arange(len(labels_b))
    ax1.bar(xi - 0.18, jf, width=0.35, color="#1b9e77", edgecolor="black", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax1.bar(xi + 0.18, un, width=0.35, color="#7570b3", edgecolor="black", label="Uniform Beta(1, N_eff+1)")
    for i, (jv, uv) in enumerate(zip(jf, un)):
        ax1.text(i - 0.18, jv * 1.13, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
        ax1.text(i + 0.18, uv * 1.13, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.8)
    ax1.set_yscale("log")
    ax1.set_ylim(0.2, 85)
    ax1.set_xticks(xi)
    ax1.set_xticklabels(labels_b, fontsize=8.2)
    ax1.set_ylabel("95% Upper Prevalence Limit f_95 (%)")
    ax1.set_title("A. Exact Bayesian Zero-ETI Bounds (Fine 2.794 Hz Regime)")
    ax1.legend(loc="upper right", frameon=True, framealpha=0.94)

    # Bandwidth & EIRP gain N10 -> N11A
    stars_s = [r["star"] for r in cad_rows]
    ys = np.arange(len(stars_s))[::-1]
    ax2.barh(ys, [float(r["eirp_w1_gw"]) for r in cad_rows], color="#1b9e77", edgecolor="black", height=0.55, label="Spor N11A Fine 2.8 Hz EIRP (5.4–29.8 GW)")
    for yy, val in zip(ys, [float(r["eirp_w1_gw"]) for r in cad_rows]):
        ax2.text(val + 0.6, yy, f"{val:.2f} GW", va="center", ha="left", fontsize=8.3, fontweight="bold")
    ax2.set_yticks(ys)
    ax2.set_yticklabels([f"{r['star']} ({float(r['dist_pc']):.2f} pc)" for r in cad_rows], fontsize=8.6)
    ax2.set_xlim(0, 38)
    ax2.set_xlabel("10σ Fine Water-Hole EIRP Sensitivity (GW)")
    ax2.set_title("B. Per-Star Physical Sensitivity (0 ETI Across All 9 Targets)")
    ax2.legend(loc="lower right", frameon=True, framealpha=0.94)
    fig.suptitle("Spor N11A: Zero-ETI Limits Across 9 < 6 pc M-Dwarfs in the Fine Water Hole", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN11A_05_bayesian_f95_and_sensitivity.png", dpi=300)
    plt.close(fig)

    # Fig 06: Radio Blind-Spot Synthesis N10 (2.86 kHz Broad Band) + N11A (2.79 Hz Gajjar Water Hole)
    fig, ax = plt.subplots(1, 1, figsize=(12.6, 5.6))
    cats = [
        "Classical Linear 1-Bin (turboSETI)\non N11A/N10 Blind-Spot Classes",
        "Spor N11A: Fine Curved Drift\n(400 trials; Δd1=16 coarse grid)",
        "Spor N11A: 3-Morphology Combined Mean\n(1,200 real-noise trials)",
        "Spor N11A: Fine Harmonic Comb\n10 Teeth @ 224–727 Hz (400 trials)",
        "Spor N10: Broadband GBT L-Band\n(Broad/Curved/Burst/FHSS, 1,200 trials)",
        "Spor N11A Primary: Gajjar Plasma\n10–350 Hz at 2.79–2.84 Hz (400 trials)",
    ]
    vals = [0.0, 9.75, 55.17, 63.25, 90.33, 92.5]
    cols = ["#d95f02", "#e6ab02", "#7570b3", "#66a61e", "#377eb8", "#1b9e77"]
    yp = np.arange(len(cats))[::-1]
    bars = ax.barh(yp, vals, color=cols, edgecolor="black", height=0.56)
    for b, v in zip(bars, vals):
        ax.text(v + 1.4, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", ha="left", fontweight="bold", fontsize=9.5)
    ax.set_yticks(yp)
    ax.set_yticklabels(cats, fontsize=9.1)
    ax.set_xlim(0, 112)
    ax.set_xlabel("Verified Injection Recovery on Real GBT L-Band Noise (%)")
    ax.set_title("Spor N10 + N11A: Honest Radio Blind-Spot Recovery Comparison (0.76 TiB Fine Sliced -> 0 ETI)")
    fig.tight_layout()
    fig.savefig(FIG / "figN11A_06_n10_n11a_radio_synthesis.png", dpi=300)
    plt.close(fig)
    print("[N11A Plot] Saved all 6 figures cleanly to", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
