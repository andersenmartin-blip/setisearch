#!/usr/bin/env python3
"""Plot 6 publication-grade 300-DPI PNGs for Spor N10 (BL GBT L-band ABACAD Blind-Spot SETI)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad"
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
    cad_rows = load_csv(RES / "N10_CADENCE_SUMMARY.csv")
    vet_rows = load_csv(RES / "N10_CANDIDATES_VETTED.csv")
    tile_rows = load_csv(RES / "N10_TILE_DIAGNOSTICS.csv")
    s2 = json.loads((RES / "N10_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N10_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n10_cutouts.npz")

    # ------------------------------------------------------------------
    # Fig 01: GBT L-band RFI Landscape & EIRP Sensitivity vs Distance
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4))
    colors = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
    for idx, r in enumerate(cad_rows):
        st = r["star"]
        fq = npz[f"BP_FREQ_{st}"]
        rf = npz[f"BP_RFI_{st}"] * 100.0
        order = np.argsort(fq)
        ax1.plot(fq[order], rf[order], lw=1.35, alpha=0.88, color=colors[idx], label=f"{st} ({float(r['dist_pc']):.2f} pc)")

    ax1.axvspan(1195, 1345, color="#888888", alpha=0.22, label="GBT Notch (1195-1345 MHz)")
    ax1.axvspan(1420.0, 1660.0, color="#1f78b4", alpha=0.08, label="SETI Water Hole (1.42-1.66 GHz)")
    for f_mark, txt, y_t in [
        (1176.45, "GPS L5", 1.25),
        (1420.41, "HI 21cm", 1.25),
        (1545.0, "Inmarsat", 1.25),
        (1575.42, "GPS L1", 1.25),
        (1621.0, "Iridium", 1.25),
    ]:
        ax1.axvline(f_mark, color="#444444", ls="--", lw=0.85, alpha=0.7)
        ax1.text(f_mark + 5, y_t, txt, rotation=90, va="bottom", ha="left", fontsize=7.6, color="#222222",
                 bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.75))
    ax1.set_yscale("symlog", linthresh=0.02)
    ax1.set_ylim(0, 32.0)
    ax1.set_xlim(1080, 1920)
    ax1.set_xlabel("Frequency (MHz)")
    ax1.set_ylabel("Channel RFI Occupancy (>5σ, %)")
    ax1.set_title("A. Real GBT L-Band Spectral & RFI Landscape (6 Cadences)")
    ax1.legend(loc="upper right", ncol=2, frameon=True, framealpha=0.95, fontsize=7.6)

    dists = [float(r["dist_pc"]) for r in cad_rows]
    e_w1 = [float(r["eirp_w1_gw"]) for r in cad_rows]
    e_w16 = [float(r["eirp_w16_gw"]) for r in cad_rows]
    e_bur = [float(r["eirp_burst_gw"]) for r in cad_rows]
    ax2.scatter(dists, e_w1, s=75, color="#1b9e77", marker="o", label="M1 Narrow (W=1, 2.86 kHz, 10σ)")
    ax2.scatter(dists, e_w16, s=75, color="#7570b3", marker="s", label="M1 Plasma-Broadened (W=16, 45.8 kHz, 10σ)")
    ax2.scatter(dists, e_bur, s=80, color="#d95f02", marker="^", label="M2 Short Burst (τ=8.6s, W=4, 12σ)")
    offsets = {"GJ411": (5, -11), "GJ65A": (5, -11), "GJ54.1": (-22, -13), "GJ273": (6, -10), "GJ687": (5, -11), "GJ1002": (-12, -13)}
    for d, ew, st in zip(dists, e_w1, [r["star"] for r in cad_rows]):
        ox, oy = offsets.get(st, (5, -11))
        ax2.annotate(st, (d, ew), xytext=(ox, oy), textcoords="offset points", fontsize=8.2)
    ax2.axhline(20000.0, color="#b2182b", ls=":", lw=1.25, label="Arecibo 2.38 GHz Planetary Radar (~20 TW)")
    ax2.set_yscale("log")
    ax2.set_ylim(100, 75000)
    ax2.set_xlabel("Distance (pc)")
    ax2.set_ylabel("Minimum Detectable Isotropic EIRP (GW)")
    ax2.set_title("B. Radiometer EIRP Sensitivity Limits (GBT SEFD = 10 Jy)")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=7.8)
    fig.suptitle("Spor N10: Real Breakthrough Listen GBT L-Band Coverage Across Six < 5 pc M-Dwarfs", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN10_01_lband_rfi_landscape_and_eirp.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 02: 1,200-Trial Head-to-Head Blind-Spot Benchmark + Real Waterfalls
    # ------------------------------------------------------------------
    fig = plt.figure(figsize=(13.4, 8.0))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.15, 1.0], hspace=0.36, wspace=0.24)
    ax_top = fig.add_subplot(gs[0, :])

    morphs = ["PLASMA_BROADENED", "CURVED_DRIFT", "SHORT_BURST", "FHSS_HOPPING"]
    labels_m = [
        "Plasma-Broadened\n(Gajjar σ_f=5-14 bins)",
        "Curved Drift\n(Quadratic d²f/dt² ≠ 0)",
        "Short Burst\n(1.5-5% Duty Cycle)",
        "Frequency-Hopping\n(8-Hop FHSS Grid)",
    ]
    pm = s2["injections"]["per_morphology"]
    n10_rates = [100.0 * pm[m]["n10_rate"] for m in morphs]
    cls_rates = [100.0 * pm[m]["classical_1bin_rate"] for m in morphs]
    x = np.arange(len(morphs))
    w_bar = 0.34
    b1 = ax_top.bar(x - w_bar / 2, n10_rates, width=w_bar, color="#1b9e77", edgecolor="#111111", label="Spor N10 Blind-Spot Detector (M1–M4, Mean 90.3%)")
    b2 = ax_top.bar(x + w_bar / 2, cls_rates, width=w_bar, color="#d95f02", edgecolor="#111111", label="Classical 1-Bin Linear Baseline (turboSETI-analog, Mean 0.0%)")
    for rect, val in zip(b1, n10_rates):
        ax_top.text(rect.get_x() + rect.get_width() / 2, val + 2.2, f"{val:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.5, color="#0d5c46")
    for rect, val in zip(b2, cls_rates):
        ax_top.text(rect.get_x() + rect.get_width() / 2, val + 2.2, f"{val:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.5, color="#8f3900")
    ax_top.set_xticks(x)
    ax_top.set_xticklabels(labels_m, fontsize=9.5)
    ax_top.set_ylim(0, 128)
    ax_top.set_ylabel("Injection Recovery Rate (%)")
    ax_top.set_title("A. 1,200 Real-Noise Injections: Blind-Spot Multi-Morphology Recovery vs. Classical 1-Bin Linear Pipeline")
    ax_top.legend(loc="upper center", ncol=2, frameon=True, framealpha=0.96, fontsize=8.8)

    inj_titles = ["B1. Injected Plasma-Broadened (A1)", "B2. Injected Curved-Drift (A1)", "B3. Injected Short-Burst (A1)", "B4. Injected 8-Hop FHSS (A1)"]
    for ci, m in enumerate(morphs):
        ax = fig.add_subplot(gs[1, ci])
        arr = npz[f"INJ_{m}"][0]
        vmax = max(float(np.percentile(arr, 99.2)), 3.2)
        ax.imshow(arr, aspect="auto", origin="lower", cmap="viridis", vmin=-1.5, vmax=vmax)
        ax.set_title(inj_titles[ci], fontsize=9.0)
        ax.set_xlabel("Rel. Channel (2.86 kHz)")
        if ci == 0:
            ax.set_ylabel("Time Step (~1.07s)")

    fig.suptitle("Spor N10 Signature Benchmark: Resolving Classical Radio-SETI Blind Spots on Real GBT L-Band Noise", fontweight="bold", y=0.985)
    fig.savefig(FIG / "figN10_02_head_to_head_blindspot_benchmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 03: Real ABACAD Waterfall Forensic Comparisons
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(3, 6, figsize=(14.0, 7.6), sharex=True, sharey=True)
    scan_roles = ["A1 (ON)", "B1 (OFF)", "A2 (ON)", "C1 (OFF)", "A3 (ON)", "D1 (OFF)"]
    row_specs = [
        ("CTRL_GJ54.1", "RFI Control (GJ 54.1)\nShared ON+OFF Terrestrial"),
        ("TRIG_GJ273_M1_BROAD_CURVED_1647_537", "GJ 273 @ 1647.54 MHz\nCross-Cadence Satellite Pass"),
        ("TRIG_GJ687_M1_BROAD_CURVED_1421_102", "GJ 687 @ 1421.10 MHz\nGalactic HI 21-cm Gradient"),
    ]
    for ri, (key, row_lbl) in enumerate(row_specs):
        cube = npz[key]
        vmax = min(float(np.percentile(cube, 99.3)), 14.0)
        for ci in range(6):
            ax = axes[ri, ci]
            ax.imshow(cube[ci], aspect="auto", origin="lower", cmap="magma", vmin=-2.0, vmax=max(vmax, 4.0))
            if ri == 0:
                ax.set_title(scan_roles[ci], color=("#0b5394" if ci in (0, 2, 4) else "#666666"))
            if ci == 0:
                ax.set_ylabel(f"{row_lbl}\nTime Step", fontsize=8.3)
            if ri == 2:
                ax.set_xlabel("Rel. Chan (128)")
    fig.suptitle("Spor N10: Real GBT ABACAD ON–OFF Spectrogram Cutouts (Vetoed Controls, Satellite Pass & Galactic HI)", fontweight="bold", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "figN10_03_abacad_real_waterfalls.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 04: M3 (AC2D) & M4 (Kurtosis) Diagnostics
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    ac_on = np.array([float(r["ac2d_on2"]) for r in tile_rows])
    ac_off = np.array([float(r["ac2d_off_max"]) for r in tile_rows])
    k_on = np.array([float(r["k99_on_min_z"]) for r in tile_rows])
    k_off = np.array([float(r["k99_off_max_z"]) for r in tile_rows])

    m3_trig = (ac_on >= 14.0) & (ac_off < 11.0) & (ac_on / np.maximum(ac_off, 1.0) >= 2.0)
    ax1.scatter(np.clip(ac_off[~m3_trig], 0, 120), np.clip(ac_on[~m3_trig], 0, 120), s=10, alpha=0.45, color="#4daf4a", label=f"Clean / Vetoed Tiles (n={int(np.sum(~m3_trig))})")
    ax1.scatter(ac_off[m3_trig], ac_on[m3_trig], s=75, color="#e41a1c", marker="D", edgecolor="black", label=f"M3 Stage 2 Triggers (n={int(np.sum(m3_trig))}: Iridium & 1500 MHz Edge)")
    ax1.axhline(14.0, color="#333333", ls="--", lw=1.0, label="M3 ON Threshold (14.0)")
    ax1.axvline(11.0, color="#7f0000", ls=":", lw=1.1, label="M3 OFF Veto (11.0)")
    for row in [r for r in vet_rows if r["channel"] == "M3_FHSS_AC2D"]:
        freq_m = float(row["freq_mhz"])
        off_xy = (10, 6) if freq_m > 1550 else (10, -10)
        lbl = f"{freq_m:.2f} MHz ({'Iridium MSS' if freq_m > 1550 else '1500 MHz Node Edge'})"
        ax1.annotate(lbl, (float(row["snr_off_max"]), float(row["snr_on_2nd"])), xytext=off_xy, textcoords="offset points", fontsize=8.0, fontweight="bold")
    ax1.set_xlim(4, 105)
    ax1.set_ylim(4, 105)
    ax1.set_xlabel("OFF Max 2D-Autocorrelation (B1, C1, D1)")
    ax1.set_ylabel("ON 2nd-Best 2D-Autocorrelation (A1, A2, A3)")
    ax1.set_title("A. M3 Frequency-Hopping 2D-Autocorrelation Diagnostic (2,829 Tiles)")
    ax1.legend(loc="upper right", frameon=True, framealpha=0.92)

    ax2.scatter(np.clip(k_off, -3, 120), np.clip(k_on, -3, 120), s=10, alpha=0.45, color="#377eb8", label="All 2,829 Clean 512-Ch Tiles")
    ax2.axhline(8.0, color="#333333", ls="--", lw=1.0, label="M4 Kurtosis ON Threshold (+8σ)")
    ax2.axvline(4.0, color="#7f0000", ls=":", lw=1.1, label="M4 Kurtosis OFF Veto (+4σ)")
    ax2.fill_between([0, 4.0], 8.0, 120, color="#e41a1c", alpha=0.07, label="M4 ETI Candidate Region (0 Hits)")
    ax2.set_xlim(-3, 85)
    ax2.set_ylim(-3, 85)
    ax2.set_xlabel("OFF Max Spectral Kurtosis Z-Score")
    ax2.set_ylabel("ON Min Spectral Kurtosis Z-Score")
    ax2.set_title("B. M4 Non-Gaussian Spectral Kurtosis Diagnostic (0 M4 Triggers)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.92)
    fig.suptitle("Spor N10: M3 2D-Autocorrelation & M4 Spectral Kurtosis Diagnostics Across 2,829 Tiles", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN10_04_entropy_kurtosis_and_ac2d_diagnostics.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 05: Stage 2 -> Stage 3 Forensic Funnel & Bayesian Jeffreys f95
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4))
    brk = s3["forensic_breakdown"]
    cat_labels = [
        "Galactic HI 21-cm\n(1420.4 MHz)",
        "Inmarsat GEO MSS\n(1525-1560 MHz)",
        "GPS L1 / Galileo\n(1575.4 MHz)",
        "GPS L5 / Galileo E5\n(1176.5 MHz)",
        "Iridium / Globalstar\n(1610-1626 MHz)",
        "ADS-B & Radar\n(1090 & 1380 MHz)",
        "METSAT / SARSAT / PCS\n(1647, 1700, 1909 MHz)",
        "1500 MHz PFB Edge\n(Instrumental)",
        "Verified Radio ETI\nCandidates",
    ]
    cat_vals = [
        brk.get("GALACTIC_HI_21CM_LINE_EMISSION", 0),
        brk.get("INMARSAT_GEO_MSS_DOWNLINK", 0),
        brk.get("GNSS_GPS_L1_SATELLITE_RFI", 0),
        brk.get("GNSS_GPS_L5_GALILEO_E5_RFI", 0),
        brk.get("IRIDIUM_GLOBALSTAR_MSS_RFI", 0),
        brk.get("ADS_B_DME_AVIATION_TRANSPONDER", 0) + brk.get("FAA_RADAR_OR_GPS_L3_RFI", 0),
        brk.get("METSAT_AWS1_WEATHER_SAT_1700MHZ", 0) + brk.get("SATELLITE_MET_OR_SAR_1647MHZ_RFI", 0) + brk.get("PCS_DECT_TERRESTRIAL_1909MHZ", 0),
        brk.get("INSTRUMENTAL_PFB_NODE_EDGE_1500MHZ", 0),
        0,
    ]
    y_pos = np.arange(len(cat_labels))[::-1]
    bar_cols = ["#4575b4"] + ["#e08214"] * 6 + ["#8c510a", "#1b7837"]
    bars = ax1.barh(y_pos, cat_vals, color=bar_cols, edgecolor="#222222", height=0.65)
    for b, val in zip(bars, cat_vals):
        ax1.text(val + 0.6, b.get_y() + b.get_height() / 2, str(val), va="center", ha="left", fontweight="bold")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(cat_labels, fontsize=8.5)
    ax1.set_xlim(0, 38)
    ax1.set_xlabel("Stage 2 Triggers Vetoed")
    ax1.set_title("A. Stage 2 → Stage 3 Forensic Veto Breakdown (136 → 0 ETI)")

    b_names = ["Star-Level Raw\n(N=6)", "Star-Level Eff.\n(N_eff=5.42)", "Broadened Tile\n(N_eff=2,650)", "FHSS Tile\n(N_eff=2,772)", "All Star×Tile\n(N_eff=2,555.5)"]
    from scipy.stats import beta as sp_beta
    n_effs = [6.0, 5.42, 2829 * 0.9367, 2829 * 0.98, 2829 * 0.9033]
    jf_vals = [100.0 * sp_beta.ppf(0.95, 0.5, ne + 0.5) for ne in n_effs]
    un_vals = [100.0 * sp_beta.ppf(0.95, 1.0, ne + 1.0) for ne in n_effs]
    xb = np.arange(len(b_names))
    ax2.bar(xb - 0.18, jf_vals, width=0.35, color="#1b9e77", edgecolor="black", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax2.bar(xb + 0.18, un_vals, width=0.35, color="#7570b3", edgecolor="black", label="Uniform Beta(1, N_eff+1)")
    for i, (jv, uv) in enumerate(zip(jf_vals, un_vals)):
        ax2.text(i - 0.18, jv * 1.12, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
        ax2.text(i + 0.18, uv * 1.12, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.8)
    ax2.set_yscale("log")
    ax2.set_ylim(0.04, 90)
    ax2.set_xticks(xb)
    ax2.set_xticklabels(b_names, fontsize=8.3)
    ax2.set_ylabel("95% Upper Prevalence Limit f_95 (%)")
    ax2.set_title("B. Exact Bayesian Zero-ETI Blind-Spot Prevalence Bounds")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.92)
    fig.suptitle("Spor N10: 136 → 0 Forensic Clearance & Exact Bayesian Null Limits", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN10_05_vetting_funnel_and_bayesian_f95.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 06: Unified Strictly Milky Way Blind-Spot SETI Synthesis
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4))
    stars_lbl = [f"{r['star']} ({float(r['dist_pc']):.2f} pc, {r['n_exoplanets']} pl.)" for r in cad_rows]
    regimes = ["N4 Radio\n54-3000 MHz", "N5 10-Yr\nMid-IR", "N7 TESS\n2-min", "N9 Gaia\n25-yr PMa", "N10 GBT\nBroad/Curved", "N10 GBT\nBurst/FHSS"]
    mat = np.ones((len(stars_lbl), len(regimes)))
    ax1.imshow(mat, aspect="auto", cmap=matplotlib.colors.ListedColormap(["#e5f5e0"]))
    for r_i in range(len(stars_lbl)):
        for c_j in range(len(regimes)):
            txt = "0 ETI\n" + ("1.1-1.9 GHz" if c_j >= 4 else "Verified")
            ax1.text(c_j, r_i, txt, ha="center", va="center", fontsize=8.0, fontweight="bold", color="#00441b",
                     bbox=dict(boxstyle="round,pad=0.24", fc="#a1d99b", ec="#006d2c", lw=0.8))
    ax1.set_xticks(np.arange(len(regimes)))
    ax1.set_xticklabels(regimes, fontsize=8.0)
    ax1.set_yticks(np.arange(len(stars_lbl)))
    ax1.set_yticklabels(stars_lbl[::-1], fontsize=8.6)
    ax1.set_title("A. Same 6 < 5 pc M-Dwarfs Verified Across Milky Way Tracks")
    ax1.grid(False)

    cats = [
        "Overall Blind-Spot\nMean (1,200 Trials)",
        "Gajjar Plasma-\nBroadened\n(10-180 kHz)",
        "Curved Orbital\nAcceleration\n(d²f/dt² ≠ 0)",
        "Intermittent\nShort Bursts\n(2-27 s Packets)",
        "Spread-Spectrum\n8-Hop FHSS /\n2D AC2D",
    ]
    y_c = np.arange(len(cats))[::-1]
    cls_cov = [0.0, 0.0, 0.0, 0.0, 0.0]
    n10_cov = [90.3, 93.7, 81.3, 88.3, 98.0]
    ax2.barh(y_c + 0.16, n10_cov, height=0.30, color="#1b9e77", edgecolor="black", label="Spor N10 Multi-Morphology Pipeline")
    ax2.barh(y_c - 0.16, cls_cov, height=0.30, color="#d95f02", edgecolor="black", label="Classical Linear 1-Bin Baseline")
    for yy, nv, cv in zip(y_c, n10_cov, cls_cov):
        ax2.text(nv + 1.5, yy + 0.16, f"{nv:.1f}%", va="center", ha="left", fontsize=8.5, fontweight="bold", color="#0d5c46")
        ax2.text(cv + 1.5, yy - 0.16, f"{cv:.1f}%", va="center", ha="left", fontsize=8.5, color="#8f3900")
    ax2.set_yticks(y_c)
    ax2.set_yticklabels(cats, fontsize=8.5)
    ax2.set_xlim(0, 118)
    ax2.set_ylim(-0.6, 4.9)
    ax2.set_xlabel("Verified Injection Recovery Rate (%)")
    ax2.set_title("B. Measured Blind-Spot Benchmark Expansion (1,200 Trials)")
    ax2.legend(loc="lower right", frameon=True, framealpha=0.95)
    fig.suptitle("Spor N10: Strictly Milky Way Blind-Spot Radio-SETI Integrated with N4–N9", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN10_06_milky_way_blindspot_synthesis.png", dpi=300)
    plt.close(fig)
    print("[N10 Plot] Saved all 6 polished figures cleanly to", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
