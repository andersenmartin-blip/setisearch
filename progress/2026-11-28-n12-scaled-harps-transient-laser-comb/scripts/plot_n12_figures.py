#!/usr/bin/env python3
"""Plot 6 publication-grade 300-DPI PNGs for Spor N12 (Scaled 32-Star HARPS Optical Laser + Comb SETI)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb"
WS11B = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
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
    n12_stars = load_csv(RES / "N12_STAR_SUMMARY.csv")
    n11b_stars = load_csv(WS11B / "results/N11B_STAR_SUMMARY.csv")
    peak_rows = load_csv(RES / "N12_PEAK_DIAGNOSTICS.csv")
    s2 = json.loads((RES / "N12_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N12_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    s2_11b = json.loads((WS11B / "results/N11B_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3_11b = json.loads((WS11B / "results/N11B_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n12_cutouts.npz")

    # Fig 01: Combined 32-Star (N11B + N12) Sample Baselines & Laser Power Sensitivity
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4))
    gk = [r for r in n12_stars if r["sp_type"][0] in ("G", "K")]
    md_12 = [r for r in n12_stars if r["sp_type"][0] not in ("G", "K")]

    for grp, col, mk, lbl in [
        (gk, "#d95f02", "D", f"N12 G/K Solar-Type ({len(gk)} hosts, tau Cet/eps Eri)"),
        (md_12, "#377eb8", "o", f"N12 M-Dwarfs ({len(md_12)} hosts, <9.5 pc)"),
        (n11b_stars, "#1b9e77", "s", f"N11B M-Dwarfs ({len(n11b_stars)} hosts, <11 pc)"),
    ]:
        yrs = [float(r["mjd_span_days"]) / 365.25 for r in grp]
        bv = [float(r["berv_span_kms"]) for r in grp]
        dists = [float(r["dist_pc"]) for r in grp]
        ptx = [float(r["p_tx_10sig_kw"]) for r in grp]
        ax1.scatter(yrs, bv, s=75, color=col, marker=mk, edgecolor="black", alpha=0.88, label=lbl)
        ax2.scatter(dists, ptx, s=75, color=col, marker=mk, edgecolor="black", alpha=0.88, label=lbl)

    ax1.set_xlabel("Multi-Epoch HARPS Time Baseline (years)")
    ax1.set_ylabel("Barycentric Earth Radial Velocity (BERV) Span (km/s)")
    ax1.set_title("A. 640 HARPS Epochs Across 32 Hosts (76 Exoplanets)")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=7.8)

    highlight_offsets = {
        "PROXIMACEN": (7, -6),
        "BARNARDSSTAR": (-8, -14),
        "EPSERI": (-48, -10),
        "TAUCET": (7, 3),
        "HD217987": (-55, 8),
        "HD209100": (8, -9),
        "HD20794": (7, 4),
        "GJ667C": (7, 4),
        "L9859": (-45, -14),
    }
    for r in n12_stars + n11b_stars:
        st = r["star"]
        if st in highlight_offsets:
            d, p = float(r["dist_pc"]), float(r["p_tx_10sig_kw"])
            ox, oy = highlight_offsets[st]
            ax2.annotate(st, (d, p), xytext=(ox, oy), textcoords="offset points", fontsize=7.6, fontweight="bold")
    ax2.set_yscale("log")
    ax2.set_xlim(0.5, 11.6)
    ax2.set_ylim(0.05, 800)
    ax2.set_xlabel("Distance (pc)")
    ax2.set_ylabel("10σ Single-Epoch Beamed Laser Limit (kW, D_tx=10 m)")
    ax2.set_title("B. Optical Laser Power Thresholds (G/K vs. M-Dwarf Contrast)")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=7.6)
    fig.suptitle("Spor N12 + N11B: 32 Nearby Milky Way Exoplanet Hosts (640 HARPS Spectra, 76 Planets -> 0 ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN12_01_32star_sample_berv_and_power.png", dpi=300)
    plt.close(fig)

    # Fig 02: 1,200-Trial Benchmark (T1 Laser + T2 Multi-Line Comb vs Classical Stack & CR/Flare FPR)
    fig = plt.figure(figsize=(14.2, 8.0))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.12, 1.0], hspace=0.38, wspace=0.28)
    ax_top = fig.add_subplot(gs[0, :])
    morphs = ["TRANSIENT_PSF_LASER", "SUBTHRESHOLD_OPTICAL_COMB", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"]
    mlbls = [
        "Single-Epoch PSF Laser\n(T1, 400 trials)",
        "8-Tooth Sub-Threshold Comb\n(T2 @ 7.0–9.0σ, 400 trials)",
        "1–2 px Sharp Cosmic Ray\n(FPR Test, 200 trials)",
        "2.6–5.5× Broad Stellar Flare\n(FPR Test, 200 trials)",
    ]
    pm = s2["injections"]["per_morphology"]
    n12_r = [100.0 * pm[m]["n12_rate"] for m in morphs]
    cls_r = [100.0 * pm[m]["classical_stack_rate"] for m in morphs]
    xb = np.arange(4)
    b1 = ax_top.bar(xb - 0.17, n12_r, width=0.33, color="#1b9e77", edgecolor="black", label="Spor N12 Dual-Channel LOEO + PSF + Comb Detector (T1 + T2)")
    b2 = ax_top.bar(xb + 0.17, cls_r, width=0.33, color="#d95f02", edgecolor="black", label="Classical 20-Epoch Static Median Stack (Blinded to Transients)")
    for rct, v in zip(b1, n12_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.6, color="#0d5c46")
    for rct, v in zip(b2, cls_r):
        ax_top.text(rct.get_x() + rct.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=9.6, color="#8f3900")
    ax_top.set_xticks(xb)
    ax_top.set_xticklabels(mlbls, fontsize=9.2)
    ax_top.set_ylim(0, 122)
    ax_top.set_ylabel("Trigger Rate (%)")
    ax_top.set_title("A. 1,200-Trial Real HARPS Benchmark Across All 24 G/K/M Stars: High T1+T2 Recovery at Near-Zero FPR")
    ax_top.legend(loc="upper right", frameon=True, framealpha=0.95)

    ititles = ["B1. PSF Laser (T1 PASS)", "B2. Comb Tooth (T2 PASS)", "B3. Sharp CR (Vetoed)", "B4. Broad Flare (Vetoed)"]
    keys_b = ["TRANSIENT_PSF_LASER", "SUBTHRESHOLD_COMB", "COSMIC_RAY_1_2PX", "BROAD_STELLAR_FLARE"]
    dlam = (np.arange(51) - 25) * 0.01
    for ci, kb in enumerate(keys_b):
        ax = fig.add_subplot(gs[1, ci])
        ax.step(dlam, npz[f"INJ_{kb}_RESZ"], where="mid", color="#7570b3", lw=1.1, alpha=0.85, label="Pixel Z")
        ax.plot(dlam, npz[f"INJ_{kb}_ZMF"], color="#1b9e77", lw=1.8, label="PSF Z_mf")
        ax.plot(dlam, npz[f"INJ_{kb}_STACKZ"], color="#d95f02", lw=1.3, ls="--", label="Stack Z")
        ax.axhline(10.0 if ci != 1 else 5.5, color="#333333", ls=":", lw=0.9)
        ax.set_title(ititles[ci], fontsize=9.2)
        ax.set_xlabel("Δλ (Å)")
        if ci == 0:
            ax.set_ylabel("SNR (σ)")
            ax.legend(loc="upper left", fontsize=7.4, frameon=True)
    fig.suptitle("Spor N12: Detecting Single-Epoch Lasers (T1) & Sub-Threshold Optical Combs (T2) on Real tau Cet/M-Dwarf Noise", fontweight="bold", y=0.985)
    fig.savefig(FIG / "figN12_02_head_to_head_t1_t2_benchmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Fig 03: G8.5V Solar-Type (tau Cet Mg I b) vs M1V (GJ 887 TiO Forest) LOEO Residuals
    fig, axes = plt.subplots(2, 2, figsize=(13.6, 6.2), sharex="col")
    for col_i, (pref, title_s, reg) in enumerate([
        ("TAUCET", "tau Cet (G8.5V, V=3.50) Mg I b Triplet Region", "5165–5190 Å"),
        ("GJ887", "GJ 887 / HD 217987 (M1V, V=7.56) Dense Line Forest", "6155–6180 Å"),
    ]):
        lam_c = npz[f"{pref}_LAM"]
        ep0 = npz[f"{pref}_EP0_NORM"]
        tmpl = npz[f"{pref}_TEMPLATE"]
        res0 = npz[f"{pref}_RESIDUAL"]
        mad_r = 1.4826 * float(np.median(np.abs(res0)))
        axes[0, col_i].plot(lam_c, ep0, color="#377eb8", lw=0.9, alpha=0.8, label="Epoch 0 (Norm)")
        axes[0, col_i].plot(lam_c, tmpl, color="#111111", lw=1.05, label="19-Epoch LOEO Template")
        axes[0, col_i].set_title(f"{title_s} ({reg})")
        axes[0, col_i].legend(loc="lower right", fontsize=7.8, frameon=True)
        axes[1, col_i].plot(lam_c, res0, color="#1b9e77", lw=0.9, label=f"Residual MAD σ = {mad_r:.5f}")
        axes[1, col_i].axhline(0.0, color="#333333", ls="--", lw=0.9)
        axes[1, col_i].set_ylim(-0.08 if col_i == 0 else -0.15, 0.08 if col_i == 0 else 0.15)
        axes[1, col_i].set_xlabel("Barycentric Wavelength (Å)")
        axes[1, col_i].legend(loc="upper right", fontsize=8.0, frameon=True)
    axes[0, 0].set_ylabel("Normalized Flux")
    axes[1, 0].set_ylabel("Differential Residual")
    fig.suptitle("Spor N12: High-Precision Stellar Line Cancellation Across Both G/K Solar Analogs & M-Dwarfs", fontweight="bold", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "figN12_03_gk_vs_mdwarf_loeo_residuals.png", dpi=300)
    plt.close(fig)

    # Fig 04: Shape Diagnostics Across 480 HARPS Spectra & Stage 3 Veto Breakdown
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4))
    cat_styles = {
        "SHARP_COSMIC_RAY": ("#e41a1c", "o", "Sharp Cosmic Ray (<0.8× PSF)"),
        "BROAD_OR_DISTORTED": ("#984ea3", "^", "Broad Flare / Distortion (>1.5× PSF)"),
        "PERSISTENT_N_GT_3": ("#ff7f00", "D", "Persistent Stellar/Sky (N>3)"),
        "T1_TRANSIENT_LASER_PASS": ("#1b9e77", "*", "T1 Transient Candidates (to Stage 3)"),
    }
    for cat, (col, mk, lbl) in cat_styles.items():
        sub = [p for p in peak_rows if p["stage2_status"] == cat]
        if sub:
            ax1.scatter([float(p["fwhm_ratio"]) for p in sub], [float(p["r_gauss"]) for p in sub],
                        s=90 if cat == "T1_TRANSIENT_LASER_PASS" else 24, color=col, marker=mk, alpha=0.8,
                        label=f"{lbl} ({len(sub)})", zorder=4 if cat == "T1_TRANSIENT_LASER_PASS" else 2)
    ax1.add_patch(plt.Rectangle((0.80, 0.88), 0.70, 0.12, fill=False, edgecolor="#1b9e77", lw=2.0, ls="--", label="Locked PSF Box [0.80–1.50, r>=0.88]"))
    ax1.set_xlim(0.15, 3.8)
    ax1.set_ylim(0.65, 1.02)
    ax1.set_xlabel("Fitted FWHM / HARPS PSF FWHM Ratio")
    ax1.set_ylabel("Core Gaussian Fit Correlation (r_gauss)")
    ax1.set_title(f"A. All {len(peak_rows)} Z_mf >= 10 Peaks Across 480 HARPS Spectra")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=7.6)

    vb = s3["veto_breakdown"]
    v_items = sorted([(k, v) for k, v in vb.items() if v > 0], key=lambda kv: kv[1], reverse=True)
    v_labels = [k.replace("_", " ").title() for k, _ in v_items]
    v_vals = [v for _, v in v_items]
    yv = np.arange(len(v_items))[::-1]
    cols_v = ["#377eb8", "#e41a1c", "#ff7f00", "#984ea3", "#66a61e", "#a65628", "#f781bf"][:len(v_items)]
    bars2 = ax2.barh(yv, v_vals, color=cols_v, edgecolor="black", height=0.56)
    for b, v in zip(bars2, v_vals):
        ax2.text(v + max(v_vals) * 0.015, b.get_y() + b.get_height() / 2, str(v), va="center", ha="left", fontweight="bold", fontsize=9.2)
    ax2.set_yticks(yv)
    ax2.set_yticklabels(v_labels, fontsize=8.0)
    ax2.set_xlim(0, max(v_vals) * 1.15 if v_vals else 10)
    ax2.set_xlabel(f"Vetted Stage 2 Triggers (Total = {s3['stage2_triggers_vetted']} -> 0 ETI)")
    ax2.set_title("B. Stage 3 Forensic Vetting (Sky/ThAr/Flare & ESO Follow-up)", fontsize=10.0)
    fig.suptitle(f"Spor N12: Multi-Epoch Vetting & Live HARPS Corroboration ({len(peak_rows)} -> {s3['stage2_triggers_vetted']} -> 0 ETI)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN12_04_shape_diagnostics_and_stage3_veto.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Fig 05: Unified 32-Star / 640-Epoch Funnel & Bayesian f_95 Sharpening (N11B -> N11B+N12)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4))
    u_peaks = s2["peaks_z10_before_shape_veto"] + s2_11b["peaks_z10_before_shape_veto"]
    u_trig = s2["stage2_triggers_total"] + s2_11b["stage2_t1_triggers_total"]
    u_eti = s3["verified_eti_candidates"] + s3_11b["verified_eti_candidates"]
    stages = [
        "All Z_mf >= 10 Peaks\n(32 Hosts, 640 Spectra)",
        "Pass Transient, PSF\n& Comb Gate (T1+T2)",
        "Unvetoed After Sky,\nThAr, Flare & Follow-up",
        "Verified\nOptical Laser ETI",
    ]
    scounts = [u_peaks, u_trig, u_eti, u_eti]
    xs = np.arange(len(stages))
    b_f = ax1.bar(xs, [max(c, 0.25) if c == 0 else c for c in scounts], bottom=0.15, color=["#377eb8", "#7570b3", "#ff7f00", "#1b9e77"], edgecolor="black", width=0.52)
    ax1.set_yscale("log")
    ax1.set_ylim(0.15, max(u_peaks * 3, 5000))
    for b, c in zip(b_f, scounts):
        ax1.text(b.get_x() + b.get_width() / 2, (c * 1.25) if c > 0 else 0.65, str(c), ha="center", va="bottom", fontweight="bold", fontsize=10.2)
    ax1.set_xticks(xs)
    ax1.set_xticklabels(stages, fontsize=8.2)
    ax1.set_ylabel("Trigger Count (log)")
    ax1.set_title("A. Unified 32-Star / 640-Epoch Vetting Funnel -> 0 ETI")

    bl = s2["provisional_zero_eti_bayesian_bounds"]
    bl_11b = s2_11b["provisional_zero_eti_bayesian_bounds"]
    lbls_b = ["N11B 8 Stars\n(N_eff=7.36)", "N12 24 Stars\n(Eff)", "Unified 32 Stars\n(Eff)", "Unified 640 Ep.\n(Eff)"]
    jf = [bl_11b["stars_eff"]["jeffreys_f95_pct"], bl["n12_stars_eff"]["jeffreys_f95_pct"], bl["unified_32stars_eff"]["jeffreys_f95_pct"], bl["unified_640epochs_eff"]["jeffreys_f95_pct"]]
    un = [bl_11b["stars_eff"]["uniform_f95_pct"], bl["n12_stars_eff"]["uniform_f95_pct"], bl["unified_32stars_eff"]["uniform_f95_pct"], bl["unified_640epochs_eff"]["uniform_f95_pct"]]
    xb2 = np.arange(4)
    ax2.bar(xb2 - 0.18, jf, width=0.35, color="#1b9e77", edgecolor="black", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax2.bar(xb2 + 0.18, un, width=0.35, color="#7570b3", edgecolor="black", label="Uniform Beta(1, N_eff+1)")
    for i, (jv, uv) in enumerate(zip(jf, un)):
        ax2.text(i - 0.18, jv * 1.15, f"{jv:.2f}%", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
        ax2.text(i + 0.18, uv * 1.15, f"{uv:.2f}%", ha="center", va="bottom", fontsize=8.0)
    ax2.set_yscale("log")
    ax2.set_ylim(0.15, 65)
    ax2.set_xticks(xb2)
    ax2.set_xticklabels(lbls_b, fontsize=8.6)
    ax2.set_ylabel("95% Upper Prevalence Limit f_95 (%)")
    ax2.set_title("B. 4× Sharpening of Transient Optical Laser Bounds (N11B -> N12)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.94)
    fig.suptitle("Spor N12 + N11B Unified Synthesis: Zero Optical Laser ETI Across 32 Nearby Hosts (640 Spectra)", fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "figN12_05_unified_32star_640epoch_bayesian_f95.png", dpi=300)
    plt.close(fig)

    # Fig 06: Milky Way Blind-Spot Quadrilogy (N10 + N11A + N11B + N12)
    fig, ax = plt.subplots(1, 1, figsize=(13.2, 5.8))
    cats = [
        "Classical Baselines\n(turboSETI 1-Bin / Median Stack)",
        "Spor N10: Broadband GBT L-Band\n(36 HDF5, 6 <5pc M-Dwarfs)",
        "Spor N11A Primary: 2.8 Hz Water Hole\n(54 HTTP-Range Slices, 9 <=6pc, Gajjar)",
        "Spor N11B: HARPS Optical Laser\n(160 Spectra, 8 <11pc M-Dwarfs)",
        "Spor N12: Scaled G/K/M Optical Laser (T1)\n(480 Spectra, 24 <9.5pc Hosts)",
        "Spor N12: Sub-Threshold Optical Comb (T2)\n(8 Teeth @ 7.0–9.0σ in Single Epoch)",
    ]
    vals = [0.0, 90.33, 92.5, 92.0, s2["injections"]["laser_completeness"] * 100.0, s2["injections"]["subthreshold_comb_completeness"] * 100.0]
    cols = ["#d95f02", "#377eb8", "#7570b3", "#66a61e", "#1b9e77", "#e7298a"]
    yp = np.arange(len(cats))[::-1]
    bars = ax.barh(yp, vals, color=cols, edgecolor="black", height=0.56)
    notes = [
        "0.0% Blind-Spot Recovery",
        "0 ETI (136 vetoed) | 171–621 GW",
        "0 ETI (576 blocks; 55.2% 3-cls) | 5.4–29.8 GW",
        "0 ETI (60 vetoed) | 0.11–6.87 kW",
        f"0 ETI ({s3['stage2_triggers_vetted']} vetoed) | Unified 32★ / 640 Ep.",
        "0 ETI | Invisible to Single-Line & Stack!",
    ]
    for b, v, nt in zip(bars, vals, notes):
        ax.text(v + 1.4, b.get_y() + b.get_height() / 2, f"{v:.1f}%  —  {nt}", va="center", ha="left", fontweight="bold", fontsize=8.8)
    ax.set_yticks(yp)
    ax.set_yticklabels(cats, fontsize=8.9)
    ax.set_xlim(0, 158)
    ax.set_xlabel("Verified Injection Completeness on Real Observatory Noise (%)")
    ax.set_title("Milky Way Blind-Spot Quadrilogy (N10 + N11A + N11B + N12): High Completeness Across Unsearched Regimes -> 0 ETI")
    fig.tight_layout()
    fig.savefig(FIG / "figN12_06_milky_way_blindspot_quadrilogy.png", dpi=300)
    plt.close(fig)
    print("[N12 Plot] Saved all 6 figures cleanly to", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
