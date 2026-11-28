#!/usr/bin/env python3
"""Generate all 6 publication-quality 300-DPI figures for Spor N14."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS11B = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser/results"
WS12 = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb/results"
WS13 = ROOT / "analysis_workspace/work_n13_20261128_scaled_waterhole_plasma_dechirp_comb/results"
WS14 = ROOT / "analysis_workspace/work_n14_20261128_300star_harps_transient_comb"
RES = WS14 / "results"
FIG = WS14 / "figures"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.2,
    "figure.titlesize": 12.0,
    "figure.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def spt_bucket(sp: str) -> str:
    s = (sp or "").strip().upper()
    if s.startswith("M"):
        return "M"
    if s.startswith("K"):
        return "K"
    if s.startswith("G"):
        return "G"
    return "F/A"


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    n11b_stars = load_csv(WS11B / "N11B_STAR_SUMMARY.csv")
    n12_stars = load_csv(WS12 / "N12_STAR_SUMMARY.csv")
    n14_stars = load_csv(RES / "N14_STAR_SUMMARY.csv")
    diags = load_csv(RES / "N14_PEAK_DIAGNOSTICS.csv")
    vetted = load_csv(RES / "N14_CANDIDATES_VETTED.csv")

    s14 = json.loads((RES / "N14_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    v14 = json.loads((RES / "N14_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    s13 = json.loads((WS13 / "N13_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s12 = json.loads((WS12 / "N12_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s11b = json.loads((WS11B / "N11B_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    npz = np.load(RES / "n14_cutouts.npz", allow_pickle=True)

    # ------------------------------------------------------------------
    # Fig 1: 300-Star Distance & Beamed 10-sigma Laser Power Census
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.4), gridspec_kw={"width_ratios": [1.35, 1.0]})

    d14 = np.array([float(r["dist_pc"]) for r in n14_stars])
    p14 = np.array([float(r["p_tx_10sig_kw"]) for r in n14_stars])
    c14 = [spt_bucket(r.get("sp_type", "")) for r in n14_stars]
    pal = {"M": "#0d9488", "K": "#d97706", "G": "#2563eb", "F/A": "#7c3aed"}
    for cls in ("M", "K", "G", "F/A"):
        m = np.array([x == cls for x in c14])
        if np.any(m):
            ax1.scatter(d14[m], p14[m], s=26, alpha=0.80, color=pal[cls], edgecolors="white", linewidths=0.35, label=f"N14 {cls} ({int(np.sum(m))})")

    d12 = np.array([float(r["dist_pc"]) for r in n12_stars])
    p12 = np.array([float(r["p_tx_10sig_kw"]) for r in n12_stars])
    ax1.scatter(d12, p12, s=46, marker="s", color="#ea580c", edgecolors="black", linewidths=0.6, label="N12 <9.5 pc (24)", zorder=4)

    d11 = np.array([float(r["dist_pc"]) for r in n11b_stars])
    p11 = np.array([float(r["p_tx_10sig_kw"]) for r in n11b_stars])
    ax1.scatter(d11, p11, s=64, marker="D", color="#dc2626", edgecolors="black", linewidths=0.7, label="N11B <11 pc (8)", zorder=5)

    all_p = np.concatenate([p11, p12, p14])
    med_all = float(np.median(all_p))
    ax1.axhline(med_all, color="#334155", ls="--", lw=1.1, label=f"300-star median = {med_all:.1f} kW")
    ax1.annotate("Proxima Cen\n(1.30 pc, 0.11 kW)", xy=(1.302, 0.1077), xytext=(5.5, 0.12),
                 arrowprops=dict(arrowstyle="->", color="#991b1b", lw=1.0), fontsize=8.0, color="#991b1b", fontweight="bold")
    ax1.annotate("GJ 1061 (0.16 kW)", xy=(3.674, 0.1567), xytext=(9.2, 0.45),
                 arrowprops=dict(arrowstyle="->", color="#991b1b", lw=0.9), fontsize=7.8, color="#991b1b")
    ax1.set_yscale("log")
    ax1.set_xlabel("Heliocentric Distance [pc]")
    ax1.set_ylabel("Beamed 10$\\sigma$ Laser Threshold ($D_{\\mathrm{tx}}=10$ m) [kW]")
    ax1.set_title("300 Confirmed Exoplanet Hosts: Optical Sensitivity vs Distance")
    ax1.set_xlim(0.0, 52.0)
    ax1.set_ylim(0.05, 3e4)
    ax1.legend(loc="lower right", ncol=2, frameon=True, framealpha=0.9)

    # Right panel: Exoplanets & Stars across N11B+N12+N14 spectral classes
    all_rows = (
        [{"cls": "M", "n_ep": int(r["n_exoplanets"])} for r in n11b_stars]
        + [{"cls": spt_bucket(r.get("sp_type", "")), "n_ep": int(r["n_exoplanets"])} for r in n12_stars]
        + [{"cls": spt_bucket(r.get("sp_type", "")), "n_ep": int(r["n_exoplanets"])} for r in n14_stars]
    )
    classes = ["F/A", "G", "K", "M"]
    n_hosts_c = [sum(1 for r in all_rows if r["cls"] == c) for c in classes]
    n_pl_c = [sum(r["n_ep"] for r in all_rows if r["cls"] == c) for c in classes]
    x = np.arange(len(classes))
    w = 0.36
    b1 = ax2.bar(x - w / 2, n_hosts_c, width=w, color="#1d4ed8", alpha=0.88, label="Host Stars (Total 300)")
    b2 = ax2.bar(x + w / 2, n_pl_c, width=w, color="#0d9488", alpha=0.88, label="Confirmed Exoplanets (Total 508)")
    for rect in list(b1) + list(b2):
        h = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width() / 2, h + 4, f"{int(h)}", ha="center", va="bottom", fontsize=8.3, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(classes)
    ax2.set_ylabel("Count")
    ax2.set_ylim(0, max(n_pl_c) * 1.18)
    ax2.set_title("Unified 300-Star / 508-Exoplanet / 2,784-Epoch Sample")
    ax2.legend(loc="upper left", frameon=True)

    fig.suptitle("Spor N14: 300-Star Milky Way HARPS Optical Laser & Comb Census (0.11 kW – 12.8 MW)")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "figN14_01_300star_distance_and_power_census.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 2: 1,200-Trial Head-to-Head 8-Epoch Benchmark
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2), gridspec_kw={"width_ratios": [1.1, 1.15]})

    inj = s14["injections"]["per_morphology"]
    cats = [
        ("TRANSIENT_PSF_LASER", "Single-Epoch\nLaser (T1, 400)"),
        ("SUBTHRESHOLD_OPTICAL_COMB", "Sub-Thresh\nComb (T2, 400)"),
        ("COSMIC_RAY_1_2PX", "Cosmic Ray\nFPR (200)"),
        ("BROAD_STELLAR_FLARE", "Broad Stellar\nFlare FPR (200)"),
    ]
    n14_rates = [inj[k]["n14_rate"] * 100.0 for k, _ in cats]
    cls_rates = [inj[k]["classical_stack_rate"] * 100.0 for k, _ in cats]
    n14_lbls = [f"{inj[k]['n14_positive']}/{inj[k]['trials']}\n({inj[k]['n14_rate']*100:.2f}%)" for k, _ in cats]

    xb = np.arange(len(cats))
    bw = 0.36
    bars_n14 = ax1.bar(xb - bw / 2, n14_rates, width=bw, color=["#0d9488", "#2563eb", "#64748b", "#64748b"], label="N14 8-Epoch LOEO+PSF & Comb")
    bars_cls = ax1.bar(xb + bw / 2, cls_rates, width=bw, color="#dc2626", alpha=0.80, label="Classical Static Median Stack")
    for idx_b, rect in enumerate(bars_n14):
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width() / 2, max(h, 1.0) + 1.8, n14_lbls[idx_b], ha="center", va="bottom", fontsize=7.9, fontweight="bold")
    for rect in bars_cls:
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width() / 2, h + 1.5, f"{h:.1f}%", ha="center", va="bottom", fontsize=7.8, color="#991b1b")
    ax1.set_xticks(xb)
    ax1.set_xticklabels([c[1] for c in cats])
    ax1.set_ylabel("Trigger Rate [%]")
    ax1.set_ylim(0, 114)
    ax1.set_title("1,200-Trial Real-Data HARPS Injection & Artifact Stress Test")
    ax1.legend(loc="upper right", frameon=True)

    # Right panel: Representative 51-px injection cutouts around target wavelength
    dx_a = (np.arange(51, dtype=np.float64) - 25.0) * 0.01
    ax2.plot(dx_a, np.asarray(npz["INJ_COSMIC_RAY_1_2PX_RESZ"], dtype=np.float64), color="#f59e0b", ls=":", lw=1.8, label="Cosmic Ray 1-2 px (Raw $Z_{\\mathrm{res}}$, Rejected by FWHM)")
    ax2.plot(dx_a, np.asarray(npz["INJ_TRANSIENT_PSF_LASER_ZMF"], dtype=np.float64), color="#0d9488", ls="-", lw=2.2, label="T1 Laser Cutout (N14 LOEO $Z_{\\mathrm{MF}}$)")
    ax2.plot(dx_a, np.asarray(npz["INJ_SUBTHRESHOLD_COMB_ZMF"], dtype=np.float64), color="#2563eb", ls="-.", lw=1.9, label="T2 Sub-Threshold Comb Tooth ($Z_{\\mathrm{MF}}$)")
    ax2.plot(dx_a, np.asarray(npz["INJ_TRANSIENT_PSF_LASER_STACKZ"], dtype=np.float64), color="#dc2626", ls="--", lw=1.9, label="T1 Laser in Classical Median Stack ($Z \\approx 0$)")
    ax2.axhline(10.0, color="#0f172a", ls=":", lw=1.0, label="T1 Stage 2 Threshold ($Z=10$)")
    ax2.axhline(6.0, color="#64748b", ls=":", lw=1.0, label="T2 Comb Floor ($Z=6$)")
    ax2.set_xlim(-0.25, 0.25)
    ax2.set_ylim(-2.0, 26.0)
    ax2.set_xlabel("Wavelength Offset $\\Delta\\lambda$ [$\\AA$] ($0.01\\,\\AA$/px)")
    ax2.set_ylabel("Matched / Residual Significance [$\\sigma$]")
    ax2.set_title("Cutout Signal Separation: 8-Epoch LOEO vs Static Stack")
    ax2.legend(loc="upper right", frameon=True, fontsize=7.5)

    fig.suptitle("Spor N14 Benchmark: 92.75% T1 & 88.75% T2 Completeness vs 0.00% Classical Stacking & 0.00% FPR")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "figN14_02_head_to_head_8epoch_benchmark.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 3: F / G / K / M Leave-One-Epoch-Out Stellar Cancellation Gallery
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 7.6), sharex=False)
    for ax, cls_key, title_cls, col_res in [
        (axes[0, 0], "F", "F-Dwarf Example", "#7c3aed"),
        (axes[0, 1], "G", "Solar-Type G-Dwarf Example", "#2563eb"),
        (axes[1, 0], "K", "K-Dwarf Example", "#d97706"),
        (axes[1, 1], "M", "M-Dwarf Example", "#0d9488"),
    ]:
        st_name = str(npz[f"SHOW_{cls_key}_STAR"][0])
        lam = np.asarray(npz[f"SHOW_{cls_key}_LAM"], dtype=np.float64)
        ep0 = np.asarray(npz[f"SHOW_{cls_key}_EP0"], dtype=np.float32)
        tmpl = np.asarray(npz[f"SHOW_{cls_key}_TMPL"], dtype=np.float32)
        res = np.asarray(npz[f"SHOW_{cls_key}_RES"], dtype=np.float32) * 100.0
        ok = np.isfinite(ep0) & np.isfinite(tmpl) & np.isfinite(res)
        rms = float(np.sqrt(np.mean(res[ok] ** 2))) if np.any(ok) else 0.0
        ax.plot(lam[ok], ep0[ok], color="#94a3b8", lw=0.9, label="Single HARPS Epoch")
        ax.plot(lam[ok], tmpl[ok], color="#0f172a", lw=1.0, ls="--", alpha=0.85, label="7-Epoch LOEO Template")
        ax.plot(lam[ok], res[ok] / 100.0 + 0.15, color=col_res, lw=1.0, label=f"LOEO Residual (+0.15 offset, RMS={rms:.2f}%)")
        ax.axhline(0.15, color="#475569", ls=":", lw=0.7)
        ax.set_title(f"{title_cls}: {st_name}")
        ax.set_ylabel("Normalized Flux")
        ax.set_xlabel("Barycentric Wavelength [$\\AA$]")
        ax.set_ylim(-0.05, 1.28)
        ax.legend(loc="lower right", fontsize=7.6, frameon=True)

    fig.suptitle("Spor N14 Multi-Epoch LOEO Template Cancellation Across F / G / K / M Host Stars")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "figN14_03_fgkm_loeo_subtraction_gallery.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 4: Stage 2 PSF Shape Diagnostics & Stage 3 Forensic Waterfall
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.5), gridspec_kw={"width_ratios": [1.15, 1.1]})

    fwhm_r = np.array([float(r["fwhm_ratio"]) for r in diags])
    rg = np.array([float(r["r_gauss"]) for r in diags])
    st2 = [r["stage2_status"] for r in diags]
    for status, lbl, col, sz, alph in [
        ("SHARP_COSMIC_RAY", "Sharp Cosmic Ray Veto", "#dc2626", 10, 0.45),
        ("BROAD_OR_DISTORTED", "Broad / Distorted Veto", "#f59e0b", 12, 0.55),
        ("NEGATIVE_DEFECT", "Negative Wing / Ringing Veto", "#8b5cf6", 12, 0.55),
        ("PERSISTENT_N_GT_3", "Persistent Line (n > 3)", "#0284c7", 14, 0.65),
        ("T1_TRANSIENT_LASER_PASS", "Stage 2 T1 PSF Pass", "#0d9488", 18, 0.78),
    ]:
        m = np.array([s == status for s in st2])
        if np.any(m):
            ax1.scatter(np.clip(fwhm_r[m], 0.1, 3.8), rg[m], s=sz, color=col, alpha=alph, label=f"{lbl} ({int(np.sum(m))})")
    rect = Rectangle((0.78, 0.88), 1.50 - 0.78, 1.00 - 0.88, fill=False, edgecolor="#0f172a", ls="--", lw=1.4, label="PSF Selection Box")
    ax1.add_patch(rect)
    ax1.set_xlim(0.15, 3.2)
    ax1.set_ylim(0.55, 1.015)
    ax1.set_xlabel("Measured Width Ratio ($\\sigma_{\\mathrm{fit}} / \\sigma_{\\mathrm{PSF}}$)")
    ax1.set_ylabel("Matched PSF Gaussian Correlation $r_{\\mathrm{gauss}}$")
    ax1.set_title(f"Stage 2 Shape Filtering on {len(diags):,} Raw $Z \\geq 10$ Peaks")
    ax1.legend(loc="lower right", fontsize=7.6, frameon=True)

    # Right panel: Stage 3 veto horizontal bars
    vmap = v14["veto_breakdown"]
    pretty = {
        "TERRESTRIAL_AIRGLOW_OR_TELLURIC": "Airglow / Telluric (Topo)",
        "SIMCAL_FIBER_B_WAVE_BLEED": "Fiber-B SimCal (STAR,WAVE)",
        "SINGLE_EXPOSURE_COSMIC_RAY_NONREPEATING": "ESO Neighbor Non-Rep CR",
        "ISOLATED_SINGLE_EXP_COSMIC_RAY_UNCORROBORATED": "Isolated Uncorroborated CR",
        "CHROMOSPHERIC_STELLAR_FLARE": "Chromospheric Flare (T1)",
        "CHROMOSPHERIC_FLARE_COMB": "Chromospheric Flare (T2)",
        "NONREPEATING_COMB_NOISE_EXCURSION": "Non-Rep Comb Noise (T2)",
        "INSTRUMENT_MODE_RESOLUTION_MISMATCH": "HARPS EGGS vs HAM Mode",
        "ECHELLE_ORDER_STITCH_STEP_ARTIFACT": "Echelle Order Stitch Step",
        "SINGLE_EXPOSURE_SPIKE_DECAYED_NONREPEATING": "Decayed Single-Exp Spike",
        "ISOLATED_UNCORROBORATED_COMB_EXCURSION": "Isolated Uncorr. Comb (T2)",
    }
    items = sorted(vmap.items(), key=lambda kv: kv[1])
    lbls = [pretty.get(k, k) for k, _ in items] + ["Verified ETI Candidates"]
    cnts = [v for _, v in items] + [0]
    cols_bar = ["#3b82f6" if c > 0 else "#dc2626" for c in cnts]
    y_pos = np.arange(len(lbls))
    ax2.barh(y_pos, cnts, color=cols_bar, alpha=0.88)
    for yi, cv in enumerate(cnts):
        ax2.text(cv + 8, yi, f"{cv}", va="center", ha="left", fontsize=8.5, fontweight="bold", color=("#991b1b" if cv == 0 else "#0f172a"))
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(lbls, fontsize=8.0)
    ax2.set_xlim(0, max(cnts) * 1.18)
    ax2.set_xlabel("Trigger Count Vetted")
    ax2.set_title(f"Stage 3 Forensic Resolution ({len(vetted)} Triggers -> 0 ETI)")

    fig.suptitle("Spor N14 Dual-Stage Artifact Rejection: 5,472 Raw Peaks -> 923 Stage 2 Triggers -> 0 ETI")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "figN14_04_shape_diagnostics_and_stage3_veto.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 5: Sub-1% Bayesian f_95 Breakthrough (N11B -> N12 -> N14 -> 300 Stars)
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2))

    stages = [
        ("N11B Only\n(8 stars)", s11b["provisional_zero_eti_bayesian_bounds"]["stars_raw_8"]["jeffreys_f95_pct"],
         s11b["provisional_zero_eti_bayesian_bounds"]["stars_eff"]["jeffreys_f95_pct"],
         s11b["provisional_zero_eti_bayesian_bounds"]["stars_eff"]["uniform_f95_pct"]),
        ("N11B+N12\n(32 stars)", s12["provisional_zero_eti_bayesian_bounds"]["unified_32stars_raw"]["jeffreys_f95_pct"],
         s12["provisional_zero_eti_bayesian_bounds"]["unified_32stars_eff"]["jeffreys_f95_pct"],
         s12["provisional_zero_eti_bayesian_bounds"]["unified_32stars_eff"]["uniform_f95_pct"]),
        ("N14 New Only\n(268 stars)", s14["provisional_zero_eti_bayesian_bounds"]["n14_stars_raw_268"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["n14_stars_eff"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["n14_stars_eff"]["uniform_f95_pct"]),
        ("Unified Census\n(300 stars)", s14["provisional_zero_eti_bayesian_bounds"]["unified_300stars_raw"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["unified_300stars_eff"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["unified_300stars_eff"]["uniform_f95_pct"]),
    ]
    xs = np.arange(len(stages))
    jraw = [x[1] for x in stages]
    jeff = [x[2] for x in stages]
    ueff = [x[3] for x in stages]
    w5 = 0.26
    b_jr = ax1.bar(xs - w5, jraw, width=w5, color="#0d9488", label="Jeffreys $f_{95}$ (Raw $N$)")
    b_je = ax1.bar(xs, jeff, width=w5, color="#2563eb", label="Jeffreys $f_{95}$ ($N_{\\mathrm{eff}}$)")
    b_ue = ax1.bar(xs + w5, ueff, width=w5, color="#64748b", alpha=0.80, label="Uniform $f_{95}$ ($N_{\\mathrm{eff}}$)")
    ax1.axhline(1.0, color="#dc2626", ls="--", lw=1.4, label="1.0% Sub-Percent Barrier")
    for idx_r, rect in enumerate(list(b_jr) + list(b_je) + list(b_ue)):
        h = rect.get_height()
        y_off = 1.18 if idx_r in (4, 5, 6, 7) else 1.07
        ax1.text(rect.get_x() + rect.get_width() / 2, h * y_off, f"{h:.2f}%", ha="center", va="bottom", fontsize=6.7, fontweight="bold")
    ax1.set_yscale("log")
    ax1.set_xticks(xs)
    ax1.set_xticklabels([x[0] for x in stages])
    ax1.set_ylabel("95% Upper Limit on Optical Laser Hosts $f_{95}$ [%]")
    ax1.set_ylim(0.3, 60.0)
    ax1.set_title("Stellar Host Scaling: Breaking the Sub-1% Threshold")
    ax1.legend(loc="upper right", fontsize=8.0, frameon=True)

    # Right panel: Epoch-level scaling
    estages = [
        ("N11B (160 ep)", s11b["provisional_zero_eti_bayesian_bounds"]["epochs_eff"]["jeffreys_f95_pct"],
         s11b["provisional_zero_eti_bayesian_bounds"]["epochs_eff"]["uniform_f95_pct"]),
        ("N11B+N12 (640 ep)", s12["provisional_zero_eti_bayesian_bounds"]["unified_640epochs_eff"]["jeffreys_f95_pct"],
         s12["provisional_zero_eti_bayesian_bounds"]["unified_640epochs_eff"]["uniform_f95_pct"]),
        ("N14 New (2,144 ep)", s14["provisional_zero_eti_bayesian_bounds"]["n14_epochs_eff"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["n14_epochs_eff"]["uniform_f95_pct"]),
        ("Unified (2,784 ep)", s14["provisional_zero_eti_bayesian_bounds"]["unified_2784epochs_eff"]["jeffreys_f95_pct"],
         s14["provisional_zero_eti_bayesian_bounds"]["unified_2784epochs_eff"]["uniform_f95_pct"]),
    ]
    xe = np.arange(len(estages))
    w6 = 0.34
    bj = ax2.bar(xe - w6 / 2, [x[1] for x in estages], width=w6, color="#0d9488", label="Jeffreys $f_{95}$ (Effective Epochs)")
    bu = ax2.bar(xe + w6 / 2, [x[2] for x in estages], width=w6, color="#475569", alpha=0.80, label="Uniform $f_{95}$ (Effective Epochs)")
    for rect in list(bj) + list(bu):
        h = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width() / 2, h + 0.04, f"{h:.4f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax2.set_xticks(xe)
    ax2.set_xticklabels([x[0] for x in estages])
    ax2.set_ylabel("Per-Epoch Transient Laser Duty-Cycle Limit $f_{95}$ [%]")
    ax2.set_ylim(0, max(x[2] for x in estages) * 1.22)
    ax2.set_title("Per-Epoch Scaling Across 2,784 HARPS Spectra ($N_{\\mathrm{eff}}=2,597.76$)")
    ax2.legend(loc="upper right", fontsize=8.0, frameon=True)

    fig.suptitle("Sub-1% Breakthrough: 300 Milky Way Exoplanet Hosts Yield Jeffreys $f_{95} = 0.6377\\%$ Raw ($0.6854\\%$ Eff.)")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "figN14_05_sub1pct_bayesian_f95_breakthrough.png", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Fig 6: Milky Way Blind-Spot Hexalogy Overview (N7–N14)
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(13.0, 5.2))
    tracks = [
        ("N7: NASA TESS 2-min\n(558 Milky Way Stars)", 558, "f95=0.35% raw / 0.51% eff\n8.64M cadences -> 0 ETI", "#0284c7"),
        ("N8: GC + ATNF Pulsars\n(2,501 Pulsars + 222 Bulge)", 2501, "f95=0.077% / 0.080% eff\n0.86% Bulge gamma -> 0 ETI", "#7c3aed"),
        ("N9: Gaia DR3 + HGCA/PMa\n(996 Stars + Gaia BH1)", 996, "f95=0.193% / 0.220% eff\nDark >=1.4 M_sun -> 0 ETI", "#9333ea"),
        ("N10: Raw BL GBT ABACAD\n(6 <5 pc M-Dwarfs, 4.1 GHz)", 6, "90.3% vs 0.0% classical\n136 triggers vetted -> 0 ETI", "#ea580c"),
        ("N11A+N13: Water-Hole 2.8 Hz\n(33 Stars, 198 H5 Scans)", 33, f"96.42% v2 | f95={s13['provisional_zero_eti_bayesian_bounds']['unified_33stars_eff']['jeffreys_f95_pct']:.2f}% eff\n2,112 clean blocks -> 0 ETI", "#d97706"),
        ("N11B+N12+N14: HARPS\n(300 Hosts / 508 Planets)", 300, f"92.75% T1 & 88.75% T2\nf95={s14['provisional_zero_eti_bayesian_bounds']['unified_300stars_eff']['jeffreys_f95_pct']:.4f}% eff -> 0 ETI", "#0d9488"),
    ]
    yt = np.arange(len(tracks))
    vals = [t[1] for t in tracks]
    cols = [t[3] for t in tracks]
    ax.barh(yt, vals, color=cols, alpha=0.88, height=0.62)
    ax.set_xscale("log")
    for idx_t, (name, val, note, col) in enumerate(tracks):
        ax.text(val * 1.18, idx_t, note.replace("\n", "  |  "), va="center", ha="left", fontsize=8.2, fontweight="bold", color="#0f172a")
    ax.set_yticks(yt)
    ax.set_yticklabels([t[0] for t in tracks], fontsize=8.8)
    ax.set_xlim(3.0, 2.5e5)
    ax.set_xlabel("Milky Way Targets Analyzed (Log Scale)")
    ax.set_title("Six Strictly Milky Way Blind-Spot Tracks (Spor N7–N14): 0 Verified ETI Across All Regimes")
    fig.tight_layout()
    fig.savefig(FIG / "figN14_06_milky_way_blindspot_hexalogy.png", dpi=300)
    plt.close(fig)

    print("Generated 6 figures in", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
