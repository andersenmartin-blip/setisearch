#!/usr/bin/env python3
"""Generate 4 publication-grade 220-DPI PNG figures for Phase D086
(PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIGS = HERE / "figures"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def plot_fig1_cascade_and_g6(summary: dict[str, Any], g6_rows: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), dpi=220)
    fc = summary["false_alarm_cascade"]
    stages = ["Legacy V2\n(No Tmplt)", "V3.7 G1\n(+LSF/F1)", "After G2\n(Airglow/O3)", "After G3/G4\n(Chromo/Ord)", "Pre-G6\n(+G5 11px)", "Post-G6\n(Sparse)", "Verified\nETI"]
    vals = [
        max(1, fc["v2_legacy_false_alarms"]),
        max(1, fc["v37_total_ledger_g1_candidates"]),
        max(1, fc["v37_after_g2"]),
        max(1, fc["v37_after_g4"]),
        max(1, fc["v37_pre_g6_passed_g1_to_g5"]),
        max(1, fc["automated_qualified_control"] + fc["automated_qualified_science"]),
        0,
    ]
    colors = ["#7f8c8d", "#3498db", "#2980b9", "#8e44ad", "#d35400", "#c0392b", "#27ae60"]
    bars = ax1.bar(stages, [max(0.4, v) for v in vals], color=colors, edgecolor="black", linewidth=0.7)
    ax1.set_yscale("log")
    ax1.set_ylim(0.25, max(vals) * 3.0)
    ax1.set_ylabel("Candidate / False-Alarm Count (log scale)")
    ax1.set_title("A. D086 V3.7 False-Alarm Cascade Across 181 Spectra\n(UVES_NUV + ESPRESSO + HARPS)")
    ax1.grid(axis="y", alpha=0.25)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2.0, max(0.55, v) * 1.15, f"{v}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax1.tick_params(axis="x", labelsize=8)

    classes = [
        ("TRUE_BARYCENTRIC_STELLAR_LASER", "True Stellar\nLaser Pass"),
        ("UNLISTED_STATIONARY_SKY_OH_LINE", "Sky OH Line\nRejection"),
        ("STATIONARY_DETECTOR_WARM_PIXEL", "Detector Warm\nPixel Rejection"),
        ("INTRA_STAR_BERV_STATIONARY_GHOST", "Intra-Star BERV\nGhost Rejection"),
    ]
    x = np.arange(len(classes))
    w = 0.35
    d_rates, s_rates = [], []
    for k, _ in classes:
        sub = [r for r in g6_rows if r["trial_class"] == k]
        is_true = k == "TRUE_BARYCENTRIC_STELLAR_LASER"
        d_rates.append(100.0 * sum(1 for r in sub if (r["g6_v35_dense_pass"] == "True") == is_true) / max(1, len(sub)))
        s_rates.append(100.0 * sum(1 for r in sub if (r["g6_v36_sparse_pass"] == "True") == is_true) / max(1, len(sub)))
    b1 = ax2.bar(x - w / 2, d_rates, w, label="Dense Atlas (V3.5)", color="#e67e22", edgecolor="black", linewidth=0.7)
    b2 = ax2.bar(x + w / 2, s_rates, w, label="Sparse Atlas (V3.6+)", color="#1f77b4", edgecolor="black", linewidth=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[1] for c in classes], fontsize=8.5)
    ax2.set_ylim(0, 118)
    ax2.set_ylabel("Pass / Rejection Rate (%)")
    ax2.set_title("B. Gate G6 Benchmark (240 Synthetic Trials)\nSparse Non-Local vs Dense Telluric Atlas")
    ax2.legend(loc="lower right", fontsize=8.5)
    ax2.grid(axis="y", alpha=0.25)
    for bars_grp in (b1, b2):
        for bar in bars_grp:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2.0, h + 1.8, f"{h:.1f}%", ha="center", va="bottom", fontsize=7.5)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig2_comb_v41_and_13star_bridge(
    comb_cal: list[dict[str, str]],
    reg_rows: list[dict[str, str]],
    br13: list[dict[str, str]],
    out_path: Path,
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5), dpi=220)

    # Panel A: COMB_V4 vs COMB_V4_1 Benchmark + D085 Regression
    sigmas = sorted({float(r["tooth_snr_inj"]) for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB"})
    rec_v4 = [100.0 * sum(1 for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) == s and r["comb_v4_hit"] == "True") / max(1, sum(1 for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) == s)) for s in sigmas]
    rec_v41 = [100.0 * sum(1 for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) == s and r["comb_v41_hit"] == "True") / max(1, sum(1 for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) == s)) for s in sigmas]
    ax1.plot(sigmas, rec_v4, "o--", color="#e67e22", linewidth=1.8, label="COMB_V4 (D085) True 6-Tooth Recovery")
    ax1.plot(sigmas, rec_v41, "s-", color="#1b9e77", linewidth=2.2, label="COMB_V4_1 (D086) True 6-Tooth Recovery")

    for_v4 = 100.0 * sum(1 for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB" and r["comb_v4_hit"] == "True") / max(1, sum(1 for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"))
    for_v41 = 100.0 * sum(1 for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB" and r["comb_v41_hit"] == "True") / max(1, sum(1 for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"))
    d85_before = len(reg_rows)
    d85_after = sum(1 for r in reg_rows if r["comb_v41_retained"] == "True")
    ax1.axvspan(3.75, 7.2, color="#1b9e77", alpha=0.07)
    ax1.text(
        0.04, 0.22,
        f"Dense Forest Pseudocomb FPR:\n  COMB_V4={for_v4:.1f}% -> COMB_V4_1={for_v41:.1f}%\n"
        f"D085 Regression Check:\n  {d85_before} false alarms -> {d85_after} survivors",
        transform=ax1.transAxes, fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8f9fa", edgecolor="#7f8c8d"),
    )
    ax1.set_xlabel("Injected Per-Tooth S/N")
    ax1.set_ylabel("Recovery Rate (%)")
    ax1.set_ylim(-5, 108)
    ax1.set_title("A. COMB_V4_1 Head-to-Head Calibration (486 Trials)\n+ Read-Only D085 Regression (19 -> 0)")
    ax1.legend(loc="lower right", fontsize=8.2)
    ax1.grid(alpha=0.25)

    # Panel B: 13-Star Panchromatic Bridge (0.305 - 2.48 um) with Proxima Cen Tri-Regime highlight!
    by_star: dict[str, list[tuple[float, float]]] = {}
    for r in br13:
        by_star.setdefault(r["star"], []).append((float(r["wave_um"]), float(r["p_beam_10m_kw"])))
    cmap = plt.cm.tab20(np.linspace(0.0, 1.0, max(1, len(by_star))))
    for idx, (st, pts) in enumerate(sorted(by_star.items())):
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        is_prox = (st == "PROXIMACEN")
        ax2.plot(
            xs, ys,
            marker="*" if is_prox else "o",
            markersize=9 if is_prox else 4.5,
            linewidth=2.4 if is_prox else 1.2,
            color="#c0392b" if is_prox else cmap[idx],
            alpha=1.0 if is_prox else 0.78,
            label=f"{st} (Tri-Regime)" if is_prox else st,
            zorder=10 if is_prox else 4,
        )
    ax2.set_yscale("log")
    ax2.axvspan(0.305, 0.38, color="#8e44ad", alpha=0.09, label="New UVES NUV (0.305-0.38 um)")
    ax2.set_xlabel("Barycentric Wavelength (um)")
    ax2.set_ylabel("8-sigma CW Beam Power Limit P_10m (kW)")
    ax2.set_title("B. 13 Panchromatic Bridge Stars (>3 Octaves: 0.305-2.48 um)\nProxima Cen spans NUV + Optical + NIR")
    ax2.legend(loc="upper right", ncol=2, fontsize=6.8)
    ax2.grid(True, which="both", alpha=0.22)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig3_completeness_and_limits(
    cb_rows: list[dict[str, str]],
    ul_rows: list[dict[str, str]],
    out_path: Path,
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4), dpi=220)

    inst_styles = [
        ("UVES_NUV", "CHANNEL_T_TRANSIENT_1EPOCH", "#8e44ad", "o-", "UVES NUV Ch. T"),
        ("ESPRESSO", "CHANNEL_T_TRANSIENT_1EPOCH", "#2980b9", "s-", "ESPRESSO Ch. T"),
        ("HARPS", "CHANNEL_T_TRANSIENT_1EPOCH", "#d35400", "^-", "HARPS Ch. T"),
        ("UVES_NUV", "CHANNEL_P_PERSISTENT_MULTIEPOCH", "#8e44ad", "o--", "UVES NUV Ch. P"),
        ("HARPS", "CHANNEL_P_PERSISTENT_MULTIEPOCH", "#d35400", "^--", "HARPS Ch. P"),
    ]
    for inst, mode, col, sty, lbl in inst_styles:
        sigs = sorted({float(r["sigma_mult"]) for r in cb_rows if r["instrument"] == inst and r["mode"] == mode})
        if not sigs:
            continue
        vals = []
        for s in sigs:
            sub = [r for r in cb_rows if r["instrument"] == inst and r["mode"] == mode and float(r["sigma_mult"]) == s]
            vals.append(100.0 * sum(int(r["n_recovered"]) for r in sub) / max(1, sum(int(r["n_trials"]) for r in sub)))
        ax1.plot(sigs, vals, sty, color=col, linewidth=1.7, label=lbl)
    ax1.set_xlabel("Injected Peak Amplitude (sigma_MAD)")
    ax1.set_ylabel("Injection-Recovery Completeness (%)")
    ax1.set_ylim(0, 105)
    ax1.set_title("A. D086 NUV + Optical Detection Completeness\n(1,620 Single-Line Calibration Trials)")
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(alpha=0.25)

    inst_c = {"UVES_NUV": ("#8e44ad", "D"), "ESPRESSO": ("#2980b9", "s"), "HARPS": ("#e67e22", "o")}
    for inst in ("UVES_NUV", "ESPRESSO", "HARPS"):
        sub = [r for r in ul_rows if r["instrument"] == inst]
        xs = [float(r["wave_bary_air_A"]) / 1e4 for r in sub]
        ys = [float(r["p_beam_10m_w"]) for r in sub]
        col, mk = inst_c[inst]
        ax2.scatter(xs, ys, s=26, c=col, marker=mk, alpha=0.80, edgecolors="black", linewidths=0.3, label=f"{inst} ({len(sub)} cells)")
    best = min(ul_rows, key=lambda r: float(r["p_beam_10m_w"]))
    bx, by = float(best["wave_bary_air_A"]) / 1e4, float(best["p_beam_10m_w"])
    ax2.annotate(
        f"Best: {best['star']} ({best['band_id']})\n{by:.1f} W (10 m tx)",
        xy=(bx, by), xytext=(bx + 0.04, by * 2.2),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.8), fontsize=8, fontweight="bold",
    )
    ax2.set_yscale("log")
    ax2.set_xlabel("Barycentric Wavelength (um)")
    ax2.set_ylabel("8-sigma CW Transmitter Limit P_10m (W)")
    ax2.set_title(f"B. D086 Upper Limits Across {len(ul_rows)} Clean Spectral Cells\n(Gaia DR3 G_BP for NUV, G for Optical)")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, which="both", alpha=0.22)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig4_175star_synthesis(
    u175: list[dict[str, str]],
    mm181: list[dict[str, str]],
    cohort_rows: list[dict[str, str]],
    out_path: Path,
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5), dpi=220)
    d86_stars = {r["canonical_target"]: r["instrument"] for r in cohort_rows}

    dists_p, lims_p = [], []
    dists_u, lims_u, dists_eh, lims_eh = [], [], [], []
    for r in u175:
        if not r.get("min_panchromatic_10m_kw"):
            continue
        d = float(r["dist_pc"])
        lk = float(r["min_panchromatic_10m_kw"]) * 1000.0
        st = r["star"]
        if st in d86_stars:
            if d86_stars[st] == "UVES_NUV":
                dists_u.append(d); lims_u.append(lk)
            else:
                dists_eh.append(d); lims_eh.append(lk)
        else:
            dists_p.append(d); lims_p.append(lk)

    ax1.scatter(dists_p, lims_p, s=22, c="#95a5a6", alpha=0.65, label=f"Prior D079-D085 ({len(dists_p)} stars)")
    ax1.scatter(dists_eh, lims_eh, s=36, c="#2980b9", marker="s", edgecolors="black", linewidths=0.4, label=f"D086 ESPRESSO/HARPS ({len(dists_eh)} stars)")
    ax1.scatter(dists_u, lims_u, s=46, c="#8e44ad", marker="D", edgecolors="black", linewidths=0.4, label=f"D086 UVES_NUV ({len(dists_u)} stars)")
    ax1.axvline(10.0, color="#c0392b", linestyle="--", linewidth=1.2, label="10 pc Solar Neighborhood (90 stars)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Gaia DR3 Distance (pc)")
    ax1.set_ylabel("Best 10 m Beam Power Limit P_10m (W)")
    ax1.set_title("A. 175-Star All-Sky Survey (>3 Octaves: 0.305-2.515 um)\n8 Spectrographs | 90 Stars <10 pc | 0 ETI Detections")
    ax1.legend(loc="upper left", fontsize=7.8)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Cumulative Survey Milestones (Exposures, Stars, <10 pc, MM overlaps)
    cats = ["Unique\nStars", "Within\n10 pc", "Panchrom.\nBridges", "Orbital\nCampaigns", "Multi-Mess.\nOverlaps"]
    d85_vals = [150, 73, 8, 40, 14]
    d86_vals = [len(u175), sum(1 for r in u175 if r["within_10pc"] == "True"), 13, 50, sum(1 for r in mm181 if r["multimessenger_overlap"] == "True")]
    x = np.arange(len(cats))
    w = 0.36
    b1 = ax2.bar(x - w / 2, d85_vals, w, label="Through D085 (Optical+NIR)", color="#95a5a6", edgecolor="black", linewidth=0.7)
    b2 = ax2.bar(x + w / 2, d86_vals, w, label="Through D086 (+UVES NUV+Opt)", color="#1f77b4", edgecolor="black", linewidth=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, fontsize=8.5)
    ax2.set_ylabel("Survey Count")
    ax2.set_title(f"B. Survey Expansion Through D086\n(1,190 Exposures | 181 Multi-Messenger Systems)")
    ax2.legend(loc="upper right", fontsize=8.5)
    ax2.grid(axis="y", alpha=0.25)
    for grp in (b1, b2):
        for bar in grp:
            h = int(round(bar.get_height()))
            ax2.text(bar.get_x() + bar.get_width() / 2.0, h + 1.5, f"{h}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    g6_rows = read_csv(RES / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    comb_cal = read_csv(RES / "COMB_V4_1_CALIBRATION_486.csv")
    reg_rows = read_csv(RES / "D085_COMB_V4_1_REGRESSION_19.csv")
    br13 = read_csv(RES / "PANCHROMATIC_BRIDGE_13STARS.csv")
    cb_rows = read_csv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    ul_rows = read_csv(RES / "STAR_UPPER_LIMITS_D086.csv")
    u175 = read_csv(RES / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv")
    mm181 = read_csv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_181SYSTEMS.csv")
    cohort = read_csv(HERE / "FROZEN_COHORT_D086.csv")

    f1 = FIGS / "fig19_d086_nuv_opt_cascade_and_g6.png"
    f2 = FIGS / "fig20_d086_comb_v41_and_13star_bridge.png"
    f3 = FIGS / "fig21_d086_nuv_opt_completeness_and_limits.png"
    f4 = FIGS / "fig22_d086_allsky_175star_90_10pc_and_181system_synthesis.png"

    plot_fig1_cascade_and_g6(summary, g6_rows, f1)
    plot_fig2_comb_v41_and_13star_bridge(comb_cal, reg_rows, br13, f2)
    plot_fig3_completeness_and_limits(cb_rows, ul_rows, f3)
    plot_fig4_175star_synthesis(u175, mm181, cohort, f4)
    print(f"[plot_figures] Wrote 4 figures into {FIGS}", flush=True)


if __name__ == "__main__":
    main()
