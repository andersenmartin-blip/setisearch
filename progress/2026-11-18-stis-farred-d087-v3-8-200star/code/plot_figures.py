#!/usr/bin/env python3
"""
Generate the 4 publication-grade 220-DPI figures (fig23..fig26) for Phase D087:
  - fig23_d087_panchromatic_coverage_and_200star_limits.png
  - fig24_d087_g4_v38_regression_and_comb_v4_1.png
  - fig25_d087_synthetic_calibration_1971_g6_240.png
  - fig26_d087_stis_farred_rv_berv_and_orbital10.png
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RESULTS = WS / "results"
FIG_DIR = WS / "figures"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 8.5,
        "figure.dpi": 220,
    })

    summary = json.loads((RESULTS / "SUMMARY.json").read_text(encoding="utf-8"))
    u200 = load_csv(RESULTS / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv")
    ul_rows = load_csv(RESULTS / "STAR_UPPER_LIMITS_D087.csv")
    reg_rows = load_csv(RESULTS / "D086_G4_V38_FIBERB_REGRESSION_577.csv")
    comb_cal = load_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv")
    inj = load_csv(RESULTS / "INJECTION_RECOVERY_1620.csv")
    kep = load_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = load_csv(RESULTS / "DETECTOR_V38_G4G5_CALIBRATION_216.csv")
    g6 = load_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    prov = load_csv(RESULTS / "EXPOSURE_PROVENANCE_201.csv")
    rv_sum = load_csv(RESULTS / "STAR_RV_SUMMARY_33.csv")
    orb_rows = load_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv")

    # ---------------- Figure 23: >4 Octave Coverage Ladder + 200-Star / 103-<10pc Limits ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    arms = [
        ("HST_STIS E140M (Space)", 0.1145, 0.1710, "#4e79a7", "R=45,800 [D087 New]"),
        ("UVES_NUV (Paranal)", 0.305, 0.456, "#59a14f", "R=41k-71k [D086]"),
        ("HARPS / HARPS-N", 0.378, 0.691, "#76b7b2", "R=115,000 [D079-D086]"),
        ("ESPRESSO HR/UHR", 0.379, 0.786, "#2c7fb8", "R=140k/190k [D080-D087]"),
        ("CARMENES_VIS", 0.520, 1.060, "#edc948", "R=94,600 [D084]"),
        ("UVES_RED (Paranal)", 0.5655, 1.0425, "#e15759", "R=42k-107k [D087 New]"),
        ("NIRPS_HE (YJHK-blue)", 0.980, 1.800, "#f28e2b", "R=70,000 [D082]"),
        ("CFHT SPIRou (YJHK)", 0.955, 2.515, "#b07aa1", "R=70,000 [D085]"),
        ("VLT CRIRES+ (K)", 1.960, 2.480, "#9c755f", "R=100,000 [D083]"),
    ]
    for yi, (lbl, w0, w1, col, note) in enumerate(arms):
        ax1.barh(yi, w1 - w0, left=w0, height=0.62, color=col, edgecolor="#222", linewidth=0.7, alpha=0.9)
        ax1.text(w1 * 1.04 if w1 < 1.9 else 1.88, yi, note, va="center", ha="left" if w1 < 1.9 else "right", fontsize=8.2, color="#111")
    ax1.set_xscale("log")
    ax1.set_xlim(0.10, 3.8)
    ax1.set_yticks(range(len(arms)))
    ax1.set_yticklabels([a[0] for a in arms])
    ax1.invert_yaxis()
    ax1.set_xlabel("Barycentric Wavelength (microns, log scale)")
    ax1.set_title("9-Spectrograph Coverage: 0.1145-2.515 um (4.46 Octaves)")
    ax1.axvline(0.1145, color="#4e79a7", linestyle="--", linewidth=0.9, alpha=0.6)
    ax1.axvline(0.305, color="#555", linestyle=":", linewidth=0.9, alpha=0.6)
    ax1.grid(True, axis="x", which="both", alpha=0.25)

    # Right panel: Upper limits vs distance for all 200 stars + D087 FUV / FarRed highlights
    d_all, p_all, d_10, p_10 = [], [], [], []
    for r in u200:
        if r.get("min_panchromatic_10m_kw"):
            dv, pv = float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"])
            if r["within_10pc"] == "True":
                d_10.append(dv)
                p_10.append(pv)
            else:
                d_all.append(dv)
                p_all.append(pv)
    ax2.scatter(d_all, p_all, s=22, color="#9aa4b2", alpha=0.65, label=f">10 pc (n={len(d_all)})")
    ax2.scatter(d_10, p_10, s=28, color="#2b5c8f", alpha=0.80, label=f"<10 pc Panchromatic (n={len(p_10)} / 103 total)")

    # Overlay D087 STIS FUV and UVES_RED best limits per star
    stis_best, uves_best = {}, {}
    for ur in ul_rows:
        st, kw, dp_v = ur["star"], float(ur["p_beam_10m_kw"]), float(ur["dist_pc"])
        if ur["instrument"] == "HST_STIS":
            if st not in stis_best or kw < stis_best[st][1]:
                stis_best[st] = (dp_v, kw)
        elif ur["instrument"] == "UVES_RED":
            if st not in uves_best or kw < uves_best[st][1]:
                uves_best[st] = (dp_v, kw)
    ax2.scatter([v[0] for v in stis_best.values()], [v[1] for v in stis_best.values()], marker="*", s=95, color="#4e79a7", edgecolor="#111", linewidth=0.6, zorder=5, label="D087 HST_STIS FUV (n=10)")
    ax2.scatter([v[0] for v in uves_best.values()], [v[1] for v in uves_best.values()], marker="^", s=65, color="#e15759", edgecolor="#111", linewidth=0.6, zorder=5, label="D087 UVES_RED Far-Red (n=10)")
    ax2.axvline(10.0, color="#444", linestyle="--", linewidth=1.0, label="10 pc Solar Neighborhood Boundary")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Gaia DR3 Distance (pc)")
    ax2.set_ylabel("8-sigma 10 m Beam Limit P_beam (kW)")
    ax2.set_title("200-Star Echelle Survey Radiometric Limits (V3.0-V3.8)")
    ax2.grid(True, which="both", alpha=0.25)
    ax2.legend(loc="lower right", framealpha=0.92)
    fig.suptitle("Phase D087: Panchromatic 4.46-Octave Expansion & 200-Star Radiometric Reach", fontweight="bold")
    fig.savefig(FIG_DIR / "fig23_d087_panchromatic_coverage_and_200star_limits.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 24: Gate G4_V38 Regression (577->0) & COMB_V4_1 Calibration ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.2), constrained_layout=True)

    ratios = np.asarray([max(1.0, float(r["fb_over_fa_cont"])) for r in reg_rows], dtype=np.float64)
    bins = np.logspace(0.0, np.log10(max(ratios) * 1.15), 24)
    ax1.hist(ratios, bins=bins, color="#e15759", edgecolor="#222", alpha=0.85, label=f"D086 Fiber-B Bleeds (n={len(ratios)} -> 0 pass G4_V38)")
    ax1.axvline(1.5, color="#111", linestyle="--", linewidth=1.6, label="G4_V38 Threshold (F_B,pk / F_A,med = 1.5)")
    ax1.set_xscale("log")
    ax1.set_xlabel("Simultaneous Calibration Fiber-B Peak / Fiber-A Continuum")
    ax1.set_ylabel("D086 CAL/CALB False-Alarm Candidates")
    ax1.set_title("G4_V38 Regression: 577 -> 0 D086 Fiber-B Bleeds (100.0% Veto)")
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(loc="upper right", framealpha=0.92)

    # Right: COMB_V4 vs COMB_V4_1 calibration across the 486 D087 trials
    cats = ["TRUE_6TOOTH\n(>=3.8 sig)", "SINGLE_LINE\nMASQ.", "TOPO_ROVIB\nPSEUDO", "DENSE_FOREST\nPSEUDO"]
    v4_rates, v41_rates = [], []
    for cl, fn in (
        ("TRUE_6TOOTH_STELLAR_COMB", lambda r: float(r["tooth_snr_inj"]) >= 3.8),
        ("SINGLE_BRIGHT_LINE_MASQUERADE", lambda r: True),
        ("STATIONARY_TOPO_ROVIB_PSEUDOCOMB", lambda r: True),
        ("DENSE_MOLECULAR_FOREST_PSEUDOCOMB", lambda r: True),
    ):
        sub = [r for r in comb_cal if r["trial_class"] == cl and fn(r)]
        v4_rates.append(sum(1 for r in sub if r["comb_v4_hit"] == "True") / len(sub))
        v41_rates.append(sum(1 for r in sub if r["comb_v41_hit"] == "True") / len(sub))
    x = np.arange(len(cats))
    w = 0.36
    ax2.bar(x - w / 2, [100 * v for v in v4_rates], width=w, color="#bab0ac", edgecolor="#222", label="COMB_V4 (No Intertooth/Crowding Filter)")
    ax2.bar(x + w / 2, [100 * v for v in v41_rates], width=w, color="#2b5c8f", edgecolor="#222", label="COMB_V4_1 (D087 Active: 0% FPR)")
    for xi, (a, b) in enumerate(zip(v4_rates, v41_rates)):
        ax2.text(xi - w / 2, 100 * a + 2.0, f"{100*a:.1f}%", ha="center", va="bottom", fontsize=8.5)
        ax2.text(xi + w / 2, 100 * b + 2.0, f"{100*b:.1f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats)
    ax2.set_ylim(0, 118)
    ax2.set_ylabel("Trigger Rate (%) across 486 Trials")
    ax2.set_title("COMB_V4 vs COMB_V4_1 Across STIS + UVES_RED + ESPRESSO")
    ax2.grid(True, axis="y", alpha=0.25)
    ax2.legend(loc="upper right", framealpha=0.92)
    fig.suptitle("Phase D087 Detector Upgrades: G4_V38 Fiber-B Veto & COMB_V4_1 Forest Immunity", fontweight="bold")
    fig.savefig(FIG_DIR / "fig24_d087_g4_v38_regression_and_comb_v4_1.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 25: 1,971 + 240 Synthetic Calibration Benchmarks ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.2), constrained_layout=True)

    sig_lvls = [5.0, 6.5, 8.0, 10.0, 14.0]
    styles = [
        ("HST_STIS", "CHANNEL_T_TRANSIENT_1EPOCH", "#4e79a7", "-", "o", "STIS E140M (T)"),
        ("UVES_RED", "CHANNEL_T_TRANSIENT_1EPOCH", "#e15759", "-", "s", "UVES_RED (T)"),
        ("ESPRESSO", "CHANNEL_T_TRANSIENT_1EPOCH", "#2b5c8f", "-", "^", "ESPRESSO (T)"),
        ("HST_STIS", "CHANNEL_P_PERSISTENT_COADD", "#4e79a7", "--", "o", "STIS E140M (P)"),
        ("UVES_RED", "CHANNEL_P_PERSISTENT_COADD", "#e15759", "--", "s", "UVES_RED (P)"),
        ("ESPRESSO", "CHANNEL_P_PERSISTENT_COADD", "#2b5c8f", "--", "^", "ESPRESSO (P)"),
    ]
    for inst, mode, col, ls, mk, lbl in styles:
        ys = []
        for s in sig_lvls:
            sub = [r for r in inj if r["instrument"] == inst and r["mode"] == mode and abs(float(r["sigma_mult"]) - s) < 0.1]
            ys.append(100.0 * sum(1 for r in sub if r["recovered"] == "True") / max(1, len(sub)))
        ax1.plot(sig_lvls, ys, color=col, linestyle=ls, marker=mk, linewidth=1.8, markersize=5.5, label=lbl)
    ax1.set_xlabel("Injected Signal Amplitude (sigma_MAD)")
    ax1.set_ylabel("Automated End-to-End Recovery (%)")
    ax1.set_ylim(-4, 108)
    ax1.set_title("1,620 Injection-Recovery Trials (T + P Across All 3 Instruments)")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="lower right", ncol=2, framealpha=0.92)

    # Right: Keplerian, G4G5, G6_V36 vs V35 comparison bars
    b_labels = [
        "Kep T_DIFF\n(>=6.5s)", "Kep K_PLANET\n(>=6.5s)",
        "G45 True\nLaser Pass", "G5 Spike\nRej.", "G5 Plateau\nRej.",
        "G6 True\nLaser", "G6 Sky/Px/\nIntra Rej."
    ]
    k65 = [r for r in kep if float(r["exp_sigma_mult"]) >= 6.5]
    vals = [
        100.0 * sum(1 for r in k65 if r["tdiff_uncomp_recovered"] == "True") / len(k65),
        100.0 * sum(1 for r in k65 if r["kplanet_dedop_recovered"] == "True") / len(k65),
        100.0 * summary["synthetic_calibration_2697_trials"]["g45_true_laser_pass"],
        100.0 * summary["synthetic_calibration_2697_trials"]["g5_cosmic_hotpx_rejection"],
        100.0 * summary["synthetic_calibration_2697_trials"]["g5_plateau_rejection"],
        100.0 * sum(1 for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER" and r["g6_v36_sparse_pass"] == "True") / max(1, sum(1 for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER")),
        100.0 * sum(1 for r in g6 if r["trial_class"] != "TRUE_BARYCENTRIC_STELLAR_LASER" and r["g6_v36_sparse_pass"] == "False") / max(1, sum(1 for r in g6 if r["trial_class"] != "TRUE_BARYCENTRIC_STELLAR_LASER")),
    ]
    cols_b = ["#bab0ac", "#2b5c8f", "#59a14f", "#59a14f", "#59a14f", "#4e79a7", "#e15759"]
    bars = ax2.bar(np.arange(len(b_labels)), vals, color=cols_b, edgecolor="#222", width=0.62)
    for bi, val in enumerate(vals):
        ax2.text(bi, val + 2.0, f"{val:.1f}%", ha="center", va="bottom", fontsize=8.3, fontweight="bold")
    ax2.set_xticks(np.arange(len(b_labels)))
    ax2.set_xticklabels(b_labels, fontsize=8.5)
    ax2.set_ylim(0, 115)
    ax2.set_ylabel("Benchmark Rate (%)")
    ax2.set_title("Keplerian Tracking (135), Morphology G4_V38+G5 (216) & G6_V36 (240)")
    ax2.grid(True, axis="y", alpha=0.25)
    fig.suptitle("Phase D087 Synthetic Calibration Suite (2,697 Total Trials Across V3.8)", fontweight="bold")
    fig.savefig(FIG_DIR / "fig25_d087_synthetic_calibration_1971_g6_240.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 26: RV/BERV Kinematics & 10 Orbital Campaigns ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.2), constrained_layout=True)

    inst_cols = {"HST_STIS": "#4e79a7", "UVES_RED": "#e15759", "ESPRESSO": "#2b5c8f"}
    for inst in ("HST_STIS", "UVES_RED", "ESPRESSO"):
        sub = [r for r in prov if r["instrument"] == inst]
        bervs = [float(r["berv_kms"]) for r in sub]
        diffs = [float(r["berv_diff_stdlib_kms"]) for r in sub]
        ax1.scatter(bervs, diffs, s=26, color=inst_cols[inst], alpha=0.82, label=f"{inst} (n={len(sub)})")
    ax1.axhline(0.50, color="#222", linestyle="--", linewidth=1.1, label="Paranal Surface Gate (0.50 km/s)")
    ax1.axhline(8.50, color="#4e79a7", linestyle=":", linewidth=1.2, label="HST LEO Orbital Gate (8.50 km/s)")
    ax1.set_xlabel("Archive Header BERV / -V_HELIO (km/s)")
    ax1.set_ylabel("|Header - Pure-Stdlib Earth/Obs RV| (km/s)")
    ax1.set_title("201-Exposure Frame Verification: Paranal + HST LEO")
    ax1.set_yscale("log")
    ax1.set_ylim(1e-4, 25.0)
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(loc="lower right", framealpha=0.92, fontsize=8.0)

    # Right: 10 Orbital campaigns Kp vs orbital_dv_span
    orb_sorted = sorted(orb_rows, key=lambda r: float(r["kp_kms"]))
    y_pos = np.arange(len(orb_sorted))
    kps = [float(r["kp_kms"]) for r in orb_sorted]
    dvs = [float(r["orbital_dv_span_kms"]) for r in orb_sorted]
    bar_cols = ["#9aa4b2" if r["role"] == "CONTROL" else ("#4e79a7" if r["instrument"] == "HST_STIS" else "#2b5c8f") for r in orb_sorted]
    ax2.barh(y_pos - 0.16, kps, height=0.32, color=bar_cols, edgecolor="#222", label="Keplerian K_p (km/s)")
    ax2.barh(y_pos + 0.16, dvs, height=0.32, color="#f28e2b", edgecolor="#222", alpha=0.9, label="IN_WINDOW Delta-v Span (km/s)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{r['star']} ({r['instrument']})" + (" [CTRL]" if r["role"] == "CONTROL" else (" [UHR+HR]" if r["star"] == "GJ3138" else "")) for r in orb_sorted], fontsize=8.5)
    ax2.set_xlabel("Orbital Velocity Scale (km/s)")
    ax2.set_title("D087 Orbital Campaigns #51-#60 (0 Verified ETI in All 10)")
    ax2.grid(True, axis="x", alpha=0.25)
    ax2.legend(loc="lower right", framealpha=0.92)
    fig.suptitle("Phase D087 Astrometric/LEO Frame Integrity & 10 Orbital Campaigns", fontweight="bold")
    fig.savefig(FIG_DIR / "fig26_d087_stis_farred_rv_berv_and_orbital10.png", dpi=220)
    plt.close(fig)
    print("[plot_figures] Wrote fig23..fig26 successfully at 220 DPI.", flush=True)


if __name__ == "__main__":
    main()
