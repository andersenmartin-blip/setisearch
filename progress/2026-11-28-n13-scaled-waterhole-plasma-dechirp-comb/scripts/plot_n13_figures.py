#!/usr/bin/env python3
"""Plot 6 publication-grade 300-DPI PNGs for Spor N13 (Scaled 33-Star Milky Way Water-Hole SETI v2)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n13_20261128_scaled_waterhole_plasma_dechirp_comb"
WS11A = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
WS11B = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
WS12 = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb"
WS10 = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad"
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
    cad_13 = load_csv(RES / "N13_CADENCE_SUMMARY.csv")
    cad_11a = load_csv(WS11A / "results/N11A_CADENCE_SUMMARY.csv")
    diag_rows = load_csv(RES / "N13_BLOCK_DIAGNOSTICS.csv")
    s2 = json.loads((RES / "N13_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s11a = json.loads((WS11A / "results/N11A_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s10 = json.loads((WS10 / "results/N10_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s11b = json.loads((WS11B / "results/N11B_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s12 = json.loads((WS12 / "results/N12_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n13_cutouts.npz")

    # Fig 01: Combined 33-Star Sample & W=1 / W=16 / W=64 EIRP Sensitivity
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.5))
    d13 = [float(r["dist_pc"]) for r in cad_13]
    e1_13 = [float(r["eirp_w1_gw"]) for r in cad_13]
    e16_13 = [float(r["eirp_w16_45hz_gw"]) for r in cad_13]
    e64_13 = [float(r["eirp_w64_179hz_gw"]) for r in cad_13]
    d11 = [float(r["dist_pc"]) for r in cad_11a]
    e1_11 = [float(r["eirp_w1_gw"]) for r in cad_11a]

    ax1.scatter(d13, e1_13, s=70, color="#1b9e77", edgecolor="black", marker="o", label="N13 W=1 bin (~2.8 Hz, 24 new stars)")
    ax1.scatter(d11, e1_11, s=68, color="#377eb8", edgecolor="black", marker="s", label="N11A W=1 bin (2.8 Hz, 9 M-dwarfs)")
    ax1.scatter(d13, e16_13, s=48, color="#7570b3", alpha=0.78, marker="^", label="N13 W=16 (~45 Hz Gajjar Plasma)")
    ax1.scatter(d13, e64_13, s=48, color="#d95f02", alpha=0.72, marker="v", label="N13 W=64 (~180 Hz Broad)")

    # Highlight bridges with star markers
    bridges = [r for r in cad_13 if "N11B" in r["bridge_tracks"] or "N12" in r["bridge_tracks"]]
    ax1.scatter([float(r["dist_pc"]) for r in bridges], [float(r["eirp_w1_gw"]) for r in bridges],
                s=170, facecolors="none", edgecolors="#e7298a", linewidths=2.0, label="HARPS+GBT Bridge Stars (6)")

    ann_off = {
        "GJ699": (7, -11),
        "GJ406": (-12, -16),
        "GJ244": (8, -9),
        "GJ447": (7, -8),
        "GJ411": (-34, 10),
        "GJ628": (7, -10),
        "HIP64924": (6, -14),
        "HIP17378": (-52, 8),
        "HIP72659": (-36, 9),
    }
    for r in cad_13 + cad_11a:
        st = r["star"]
        if st in ann_off:
            ox, oy = ann_off[st]
            lbl = f"{st}"
            ax1.annotate(lbl, (float(r["dist_pc"]), float(r["eirp_w1_gw"])), xytext=(ox, oy),
                         textcoords="offset points", fontsize=7.6, fontweight="bold")
    ax1.set_yscale("log")
    ax1.set_xlim(1.2, 9.7)
    ax1.set_ylim(1.5, 1100.0)
    ax1.set_xlabel("Distance (pc)")
    ax1.set_ylabel("10σ Fine Water-Hole EIRP Limit (GW)")
    ax1.set_title("A. 33-Star Milky Way Water-Hole Sensitivity (2.8–68.6 GW)")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=7.5)

    # Panel B: Spectral Type mix & clean bandwidth across N13's 24 new stars (198 total scans -> 97.2 MHz)
    by_sp = {"A (Sirius/Altair)": 0.0, "G (61 Vir/Xi Boo)": 0.0, "K (40 Eri/61 Cyg B/d Eri)": 0.0, "M-Dwarfs": 0.0}
    cnt_sp = {"A (Sirius/Altair)": 0, "G (61 Vir/Xi Boo)": 0, "K (40 Eri/61 Cyg B/d Eri)": 0, "M-Dwarfs": 0}
    for r in cad_13:
        sp = r["sp_type"][0]
        bw = float(r["bw_clean_mhz"])
        if sp == "A":
            k = "A (Sirius/Altair)"
        elif sp == "G":
            k = "G (61 Vir/Xi Boo)"
        elif sp == "K":
            k = "K (40 Eri/61 Cyg B/d Eri)"
        else:
            k = "M-Dwarfs"
        by_sp[k] += bw
        cnt_sp[k] += 1
    labels_b = [f"{k}\n({cnt_sp[k]} stars)" for k in by_sp]
    vals_b = list(by_sp.values())
    cols_b = ["#e7298a", "#d95f02", "#7570b3", "#1b9e77"]
    xb = np.arange(len(labels_b))
    bars = ax2.bar(xb, vals_b, color=cols_b, edgecolor="black", width=0.52)
    for b, v in zip(bars, vals_b):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.1, f"{v:.1f} MHz", ha="center", va="bottom", fontweight="bold", fontsize=9.0)
    ax2.set_xticks(xb)
    ax2.set_xticklabels(labels_b, fontsize=8.4)
    ax2.set_ylim(0, max(vals_b) * 1.2)
    ax2.set_ylabel("Clean Water-Hole Bandwidth Scanned (MHz)")
    ax2.set_title(f"B. Diverse A/G/K/M Cohort in N13 ({s2['total_clean_bw_mhz']:.1f} New / {s2['unified_clean_bw_mhz']:.1f} MHz Total)")
    fig.suptitle("Spor N13 + N11A: 33 Solar-Neighborhood Stars (198 GBT .0000.h5 Scans, 2.80 TiB -> 0 ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN13_01_33star_waterhole_sample_and_eirp.png", dpi=300)
    plt.close(fig)

    # Fig 02: 1,400-Trial Benchmark v2 (N13 G1/G2/G3 vs N11A v1 & Classical 1-Bin + Null FPR)
    fig = plt.figure(figsize=(14.0, 8.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.12, 1.0], hspace=0.38, wspace=0.25)
    ax_top = fig.add_subplot(gs[0, :])
    cats = ["GAJJAR_PLASMA_10_350HZ", "FINE_CURVED_ORBITAL", "FINE_HARMONIC_COMB", "NULL_NOISE_FPR"]
    clbls = [
        "Gajjar Plasma-Broadened\n(17–126 Hz σ_f, 400 trials)",
        "Curved Orbital Drift (G2 v2)\n(d2=±24..46 bins, 400 trials)",
        "10-Tooth Harmonic Comb (G3 v2)\n(224–727 Hz lag, 400 trials)",
        "Pure-Noise Null FPR Check\n(200 uninjected real-noise trials)",
    ]
    pm = s2["injections"]["per_morphology"]
    n13_r = [100.0 * pm[c]["n13_rate"] for c in cats]
    cls_r = [100.0 * pm[c]["classical_1bin_rate"] for c in cats]
    # Also compare N11A v1 rates for the 3 signal classes
    n11a_pm = s11a["injections"]["per_morphology"]
    n11a_r = [100.0 * n11a_pm[c]["n11a_rate"] if c in n11a_pm else 0.0 for c in cats]

    xb = np.arange(4)
    b1 = ax_top.bar(xb - 0.25, n13_r, width=0.24, color="#1b9e77", edgecolor="black", label=f"Spor N13 Blind-Spot v2 (Mean = {100*s2['injections']['n13_mean_completeness']:.2f}%, Null FPR = 0.00%)")
    b2 = ax_top.bar(xb, n11a_r, width=0.24, color="#7570b3", edgecolor="black", label="Spor N11A v1 Baseline (Mean = 55.17%)")
    b3 = ax_top.bar(xb + 0.25, cls_r, width=0.24, color="#d95f02", edgecolor="black", label="Classical 1-Bin Linear (turboSETI-analog, 0.00%)")
    for rct, v in zip(b1, n13_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=8.8, color="#0d5c46")
    for i, (rct, v) in enumerate(zip(b2, n11a_r)):
        lbl = f"{v:.1f}%" if i < 3 else "N/A"
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, lbl, ha="center", va="bottom", fontweight="bold", fontsize=8.4, color="#494285")
    for rct, v in zip(b3, cls_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=8.8, color="#8f3900")
    ax_top.set_xticks(xb)
    ax_top.set_xticklabels(clbls, fontsize=9.0)
    ax_top.set_ylim(0, 126)
    ax_top.set_ylabel("Trigger Rate (%)")
    ax_top.set_title("A. 1,400-Trial Real GBT Water-Hole Benchmark: Upgraded v2 vs. N11A v1 & Classical 1-Bin")
    ax_top.legend(loc="upper right", frameon=True, framealpha=0.95, fontsize=8.0)

    ititles = ["B1. Gajjar Plasma (G1: 93.8%)", "B2. Parabolic De-Chirp (G2 v2: 99.8%)", "B3. 10-Tooth Comb (G3 v2: 95.8%)"]
    for ci, m in enumerate(["GAJJAR_PLASMA_10_350HZ", "FINE_CURVED_ORBITAL", "FINE_HARMONIC_COMB"]):
        ax = fig.add_subplot(gs[1, ci])
        arr = npz[f"INJ_{m}"][0]
        vmax = max(float(np.percentile(arr, 99.2)), 3.2)
        ax.imshow(arr, aspect="auto", origin="lower", cmap="viridis", vmin=-1.5, vmax=vmax)
        ax.set_title(ititles[ci], fontsize=9.2)
        ax.set_xlabel("Rel. Fine Chan (~2.8 Hz/bin)")
        if ci == 0:
            ax.set_ylabel("Time Step (18s)")
    fig.suptitle("Spor N13: Solving Orbital Curvature (9.8% -> 99.8%) & Fine Combs (63.3% -> 95.8%) at Zero FPR", fontweight="bold", y=0.985)
    fig.savefig(FIG / "figN13_02_head_to_head_v2_benchmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Fig 03: Real Iconic-Star ABACAD Bandpass RFI & Clean Water-Hole Noise (Barnard's Star, Sirius, 61 Vir, 40 Eri A)
    fig, axes = plt.subplots(2, 2, figsize=(13.6, 6.2), sharex=False)
    for ax, (st, lbl, col) in zip(axes.flat, [
        ("GJ699", "Barnard's Star (GJ 699, M4V, 1.83 pc)", "#1b9e77"),
        ("GJ244", "Sirius A/B (GJ 244, A1V, 2.64 pc)", "#377eb8"),
        ("HIP64924", "61 Virginis (HIP 64924, G5V, 8.50 pc)", "#d95f02"),
        ("HIP19849", "40 Eridani A (HIP 19849, K0.5V, 5.01 pc)", "#7570b3"),
    ]):
        fq = npz[f"BP_FREQ_{st}"]
        rf = npz[f"BP_RFI_{st}"] * 100.0
        order = np.argsort(fq)
        ax.plot(fq[order], rf[order], color=col, lw=1.35)
        ax.fill_between(fq[order], 0.0, rf[order], color=col, alpha=0.16)
        ax.set_title(f"{lbl} — Mean >5σ RFI = {float(np.mean(rf)):.4f}%")
        ax.set_ylabel("RFI (>5σ, %)")
        ax.set_xlabel("Water-Hole Frequency (MHz)")
        ax.set_ylim(0, max(0.06, float(np.max(rf)) * 1.25))
    fig.suptitle("Spor N13: Ultra-Clean Fine Water-Hole Bandpass Quality Across Iconic Milky Way Stars", fontweight="bold", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "figN13_03_iconic_star_abacad_waterfalls.png", dpi=300)
    plt.close(fig)

    # Fig 04: G3 v2 Comb Score & RFI Floor Across All 1,536 Clean Blocks
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.2))
    c_on = np.array([float(r["comb_on2"]) for r in diag_rows])
    c_off = np.array([float(r["comb_off_max"]) for r in diag_rows])
    rfi_pct = np.array([float(r["rfi_5sig_pct"]) for r in diag_rows])
    ax1.scatter(c_off, c_on, s=14, alpha=0.55, color="#377eb8", label=f"All {len(diag_rows)} Fine Blocks (0 Triggers)")
    mx = max(float(np.max(c_on)), float(np.max(c_off)), 40.0) * 1.25
    ax1.plot([3.0, mx], [3.0, mx], color="#888888", ls="-.", lw=0.95, alpha=0.8, label="1:1 Terrestrial RFI Diagonal (ON = OFF)")
    ax1.axhline(14.0, color="#333333", ls="--", lw=1.1, label="G3 v2 Comb ON Threshold (14.0)")
    ax1.axvline(10.0, color="#7f0000", ls=":", lw=1.1, label="G3 v2 Comb OFF Veto (10.0)")
    ax1.fill_between([3.0, 10.0], 14.0, mx, color="#e41a1c", alpha=0.08, label="G3 ETI Region (0 Hits)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(3.0, mx)
    ax1.set_ylim(3.0, mx)
    ax1.set_xlabel("OFF Max Comb v2 Score (log)")
    ax1.set_ylabel("ON 2nd-Best Comb v2 Score (log)")
    ax1.set_title(f"A. G3 Comb v2 Across {len(diag_rows)} Blocks (OFF Veto Neutralizes Shared RFI)")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=7.5)

    rfi_clip = np.clip(rfi_pct, 0.0, 0.15)
    ax2.hist(rfi_clip, bins=32, color="#4daf4a", edgecolor="#111111", alpha=0.85)
    ax2.axvline(float(np.median(rfi_pct)), color="#b2182b", ls="--", lw=1.5, label=f"Median >5σ RFI = {float(np.median(rfi_pct)):.4f}%")
    ax2.set_xlabel("Per-Block >5σ RFI Occupancy (%, capped @ 0.15%)")
    ax2.set_ylabel("Number of 16,384-Ch Blocks")
    ax2.set_title(f"B. Noise-Floor Distribution Across All {len(diag_rows)} Blocks (0 ETI)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.95)
    fig.suptitle("Spor N13: Stage 2/3 Spectral-Comb & Noise-Floor Verification (1,536 Blocks -> 0 ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN13_04_rfi_comb_and_stage3_diagnostics.png", dpi=300)
    plt.close(fig)

    # Fig 05: Unified 33-Star / 2,112-Block Bayesian f_95 Sharpening (N11A -> N13 -> Unified)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4))
    bl = s2["provisional_zero_eti_bayesian_bounds"]
    bl11 = s11a["bayesian_zero_eti_bounds"]
    lbls_b = ["N11A 9 Stars\n(3-Class Eff)", "N13 24 Stars\n(v2 Eff)", "Unified 33 Stars\n(Eff)", "Unified 33 Stars\n(Raw)", "Unified 2,112 Blk\n(Eff)"]
    jf = [
        bl11["stars_eff"]["jeffreys_f95_pct"],
        bl["n13_stars_eff"]["jeffreys_f95_pct"],
        bl["unified_33stars_eff"]["jeffreys_f95_pct"],
        bl["unified_33stars_raw"]["jeffreys_f95_pct"],
        bl["unified_2112blocks_eff"]["jeffreys_f95_pct"],
    ]
    un = [
        bl11["stars_eff"]["uniform_f95_pct"],
        bl["n13_stars_eff"]["uniform_f95_pct"],
        bl["unified_33stars_eff"]["uniform_f95_pct"],
        bl["unified_33stars_raw"]["uniform_f95_pct"],
        bl["unified_2112blocks_eff"]["uniform_f95_pct"],
    ]
    xi = np.arange(len(lbls_b))
    ax1.bar(xi - 0.18, jf, width=0.35, color="#1b9e77", edgecolor="black", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax1.bar(xi + 0.18, un, width=0.35, color="#7570b3", edgecolor="black", label="Uniform Beta(1, N_eff+1)")
    for i, (jv, uv) in enumerate(zip(jf, un)):
        ax1.text(i - 0.18, jv * 1.15, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
        ax1.text(i + 0.18, uv * 1.15, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.8)
    ax1.set_yscale("log")
    ax1.set_ylim(0.05, 95)
    ax1.set_xticks(xi)
    ax1.set_xticklabels(lbls_b, fontsize=8.2)
    ax1.set_ylabel("95% Upper Prevalence Limit f_95 (%)")
    ax1.set_title("A. 4.7× Sharpening of Fine Water-Hole Null Bounds (N11A -> N13)")
    ax1.legend(loc="upper right", frameon=True, framealpha=0.95)

    # Panel B: Top 12 most sensitive stars in N13 (sorted by W=1 EIRP)
    top12 = sorted(cad_13, key=lambda r: float(r["eirp_w1_gw"]))[:12]
    ys = np.arange(len(top12))[::-1]
    ax2.barh(ys, [float(r["eirp_w1_gw"]) for r in top12], color="#1b9e77", edgecolor="black", height=0.58, label="W=1 (~2.8 Hz) 10σ EIRP")
    for yy, r in zip(ys, top12):
        ax2.text(float(r["eirp_w1_gw"]) + 0.35, yy, f"{float(r['eirp_w1_gw']):.2f} GW", va="center", ha="left", fontsize=8.0, fontweight="bold")
    ax2.set_yticks(ys)
    ax2.set_yticklabels([f"{r['star']} ({r['common_name'].split('(')[0].strip()}, {float(r['dist_pc']):.2f} pc)" for r in top12], fontsize=8.0)
    ax2.set_xlim(0, 22.5)
    ax2.set_xlabel("10σ Fine Water-Hole EIRP Limit (GW)")
    ax2.set_title("B. 12 Nearest / Deepest Targets in N13 (0 ETI Across All 24)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.95)
    fig.suptitle("Spor N13: Combined 33-Star Milky Way Fine Water-Hole Upper Limits (0 Verified ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN13_05_unified_33star_bayesian_f95.png", dpi=300)
    plt.close(fig)

    # Fig 06: Unified Milky Way Blind-Spot Pentalogy (N10 + N11A + N11B + N12 + N13)
    fig, ax = plt.subplots(figsize=(13.6, 6.2))
    cats_p = [
        "Classical Baselines\n(turboSETI 1-Bin / Median Stack)",
        "Spor N10: Broadband GBT L-Band\n(36 HDF5, 6 <5pc M-Dwarfs, 4 Morph.)",
        "Spor N11A: 2.8 Hz Water Hole v1\n(54 Sliced Scans, 9 <=6pc M-Dwarfs)",
        "Spor N11B: HARPS Optical Laser\n(160 Spectra, 8 <11pc M-Dwarfs)",
        "Spor N12: Scaled HARPS Optical T1\n(480 Spectra, 24 <9.5pc G/K/M)",
        "Spor N12: Optical Comb T2\n(8 Teeth @ 7–9σ, Sub-Threshold)",
        "Spor N13: Scaled 33-Star Water Hole\n(144 New / 198 Total Scans, G1–G3 v2)",
    ]
    vals_p = [
        0.0,
        100.0 * s10["injections"]["n10_mean_completeness"],
        100.0 * s11a["injections"]["per_morphology"]["GAJJAR_PLASMA_10_350HZ"]["n11a_rate"],
        100.0 * s11b["injections"]["laser_completeness"],
        100.0 * s12["injections"]["laser_completeness"],
        100.0 * s12["injections"]["subthreshold_comb_completeness"],
        100.0 * s2["injections"]["n13_mean_completeness"],
    ]
    notes_p = [
        "0.0% Blind-Spot Recovery Across Radio & Optical",
        "0 ETI (136 vetoed) | 171–621 GW EIRP",
        "0 ETI (576 blks) | 5.4–29.8 GW EIRP",
        "0 ETI (60 vetoed) | 0.11–6.87 kW",
        "0 ETI (650 vetoed) | Unified 32★ / 640 Ep.",
        "0 ETI | Invisible to Single-Line & Stack!",
        f"0 ETI (1,536 blks; 2,112 tot.) | Unified 33★ / {s2['unified_clean_bw_mhz']:.1f} MHz",
    ]
    cols_p = ["#999999", "#377eb8", "#7570b3", "#66a61e", "#1b9e77", "#e7298a", "#e6ab02"]
    yp = np.arange(len(cats_p))[::-1]
    bars_p = ax.barh(yp, vals_p, color=cols_p, edgecolor="black", height=0.58)
    for b, v, nt in zip(bars_p, vals_p, notes_p):
        ax.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.2f}%  —  {nt}", va="center", ha="left", fontweight="bold", fontsize=8.6)
    ax.set_yticks(yp)
    ax.set_yticklabels(cats_p, fontsize=8.8)
    ax.set_xlim(0, 178)
    ax.set_xlabel("Verified Injection Completeness on Real Observatory Noise (%)")
    ax.set_title("Milky Way Blind-Spot Pentalogy (N10 + N11A + N11B + N12 + N13): Unsearched Regimes -> 0 ETI")
    fig.tight_layout()
    fig.savefig(FIG / "figN13_06_milky_way_blindspot_pentalogy.png", dpi=300)
    plt.close(fig)
    print("[N13 Plot] Saved all 6 figures cleanly to", FIG, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
