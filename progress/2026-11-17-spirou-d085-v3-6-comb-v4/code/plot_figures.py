#!/usr/bin/env python3
"""Generate 4 publication-quality 220 DPI figures for Phase D085 (SPIROU_V3_6_AND_COMB_V4)
and the 150-star / 73 < 10 pc / 160-system all-sky panchromatic SETI synthesis.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG_DIR = RES / "figures"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.0,
    "figure.titlesize": 12.0,
    "figure.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def plot_fig1_cascade_and_g6(summary: dict[str, Any], g6_rows: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.3), dpi=220)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=0.20, wspace=0.26)

    fc = summary["false_alarm_cascade"]
    stages = [
        "Legacy V2\nBenchmark",
        "V3.6 G1\n(Matched+F1)",
        "V3.6 G2\n(Recon/OH)",
        "V3.6 G3\n(Native/Ridge)",
        "V3.6 G4\n(FiberA/B+Ord)",
        "V3.6 G5\n(H4RG LSF)",
        "V3.6 G6\n(Sparse)",
        "Verified\nETI",
    ]
    counts = [
        int(fc["v2_legacy_false_alarms"]),
        int(fc["v36_total_ledger_g1_candidates"]),
        int(fc["v36_after_g2"]),
        int(fc["v36_after_g3"]),
        int(fc["v36_after_g4"]),
        int(fc["v36_pre_g6_passed_g1_to_g5"]),
        int(fc["automated_qualified_control"]) + int(fc["automated_qualified_science"]),
        int(fc["verified_eti_detections"]),
    ]
    vals = [max(0.65, float(c)) for c in counts]
    cols = ["#c0392b", "#e67e22", "#d35400", "#f39c12", "#2980b9", "#8e44ad", "#16a085", "#1f3a52"]
    bars = ax1.bar(np.arange(len(stages)), vals, color=cols, edgecolor="#222222", linewidth=0.7, zorder=3)
    ax1.set_yscale("log")
    ax1.set_ylim(0.5, max(80.0, max(counts) * 5.0))
    ax1.set_xticks(np.arange(len(stages)))
    ax1.set_xticklabels(stages, rotation=24, ha="right", fontsize=8.0)
    ax1.set_ylabel("Accepted / Remaining Candidates (log scale)")
    ax1.set_title("A. SPIRou YJHK Single-Line Cascade (177 Exposures)")
    ax1.axhline(1.0, color="#666666", linestyle=":", linewidth=0.8)
    for b, cnt in zip(bars, counts):
        ax1.text(b.get_x() + b.get_width() * 0.5, max(0.75, float(cnt)) * 1.25, f"{cnt:,}", ha="center", va="bottom", fontsize=8.2, fontweight="bold")

    # Panel B: Head-to-Head 240-Trial G6_V35 Dense vs G6_V36 Sparse Benchmark
    classes = [
        ("TRUE_BARYCENTRIC_STELLAR_LASER", "True Barycentric\nStellar Laser\n(Expect PASS)", "True"),
        ("UNLISTED_STATIONARY_SKY_OH_LINE", "Unlisted Sky\nOH Emission\n(Expect VETO)", "False"),
        ("STATIONARY_H4RG_WARM_PIXEL", "Fixed H4RG\nWarm Pixel\n(Expect VETO)", "False"),
        ("INTRA_STAR_BERV_STATIONARY_GHOST", "Same-Star BERV-\nStationary Ghost\n(Expect VETO)", "False"),
    ]
    x = np.arange(len(classes))
    w = 0.34
    v35_rates, v36_rates = [], []
    for cls, _, exp_s in classes:
        sub = [r for r in g6_rows if r["trial_class"] == cls]
        v35_rates.append(100.0 * sum(1 for r in sub if r["g6_v35_dense_pass"] == exp_s) / max(1, len(sub)))
        v36_rates.append(100.0 * sum(1 for r in sub if r["g6_v36_sparse_pass"] == exp_s) / max(1, len(sub)))

    b1 = ax2.bar(x - w / 2, v35_rates, width=w * 0.92, label=f"Dense G6_V35 ({summary['g6_atlas_compression']['dense_v35_atlas_peaks']:,} peaks)", color="#95a5a6", edgecolor="#222222", linewidth=0.7, zorder=3)
    b2 = ax2.bar(x + w / 2, v36_rates, width=w * 0.92, label=f"Sparse G6_V36 ({summary['g6_atlas_compression']['sparse_v36_atlas_peaks']:,} peaks)", color="#1b7837", edgecolor="#222222", linewidth=0.7, zorder=3)
    for bi in list(b1) + list(b2):
        rv = bi.get_height()
        ax2.text(bi.get_x() + bi.get_width() * 0.5, rv + 1.8, f"{rv:.0f}%", ha="center", va="bottom", fontsize=7.8, fontweight="bold")

    ax2.set_ylim(0, 118)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[1] for c in classes], fontsize=8.0)
    ax2.set_ylabel("Correct Classification Rate (%)")
    ax2.set_title("B. Gate G6_V35 vs Sparse G6_V36 Benchmark (240 Trials)")
    ax2.legend(loc="lower right", framealpha=0.92)

    fig.suptitle("Phase D085 (SPIROU_V3_6_AND_COMB_V4): False-Alarm Cascade & Sparse Gate G6_V36 Upgrade", y=0.96)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig2_comb_and_bridge(comb_cal: list[dict[str, str]], br8: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.4), dpi=220)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=0.15, wspace=0.26)

    # Panel A: 381-trial V4 COMB Calibration
    snrs = sorted({float(r["tooth_snr_inj"]) for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB"})
    for dnu, col, mk in [(25.0, "#1b7837", "o"), (50.0, "#2166ac", "s"), (100.0, "#d95f02", "^")]:
        ys = []
        for s in snrs:
            sub = [r for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["dnu_ghz"]) == dnu and float(r["tooth_snr_inj"]) == s]
            ys.append(100.0 * sum(1 for r in sub if r["comb_hit"] == "True") / max(1, len(sub)))
        ax1.plot(snrs, ys, marker=mk, color=col, linewidth=2.0, markersize=6.0, label=f"6-Tooth Comb dnu={int(dnu)} GHz")

    ax1.axvline(7.0, color="#c0392b", linestyle="--", linewidth=1.4, label="Single-line Channel P floor (7.0 sigma)")
    ax1.axvspan(3.5, 6.8, color="#27ae60", alpha=0.10, label="Sub-threshold multi-line gain zone")
    fpr_1l = 100.0 * sum(1 for r in comb_cal if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE" and r["comb_hit"] == "True") / 48.0
    fpr_ro = 100.0 * sum(1 for r in comb_cal if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB" and r["comb_hit"] == "True") / 45.0
    ax1.text(0.97, 0.08, f"Falsified Masquerades:\n  20-sig 1-Line FPR = {fpr_1l:.1f}% (n=48)\n  Topo Ro-Vib FPR = {fpr_ro:.1f}% (n=45)", transform=ax1.transAxes, ha="right", va="bottom", fontsize=7.8, bbox={"boxstyle": "round,pad=0.3", "facecolor": "#f8f9fa", "edgecolor": "#7f8c8d"})
    ax1.set_xlim(1.5, 7.6)
    ax1.set_ylim(-5, 108)
    ax1.set_xlabel("Injected Per-Tooth Signal-to-Noise Ratio (sigma/tooth)")
    ax1.set_ylabel("V4 COMB Recovery Rate (%)")
    ax1.set_title("A. Channel 5 V4 Frequency-Comb Calibration (381 Trials)")
    ax1.legend(loc="center right", bbox_to_anchor=(0.98, 0.52), framealpha=0.92, fontsize=7.4)

    # Panel B: Northern Dichroic-Gap Closure on Wolf 359, Lalande 21185, DX Cnc, GJ 486
    north_styles = [
        ("DXCNC", "DX Cnc (3.58 pc)", "#1b7837", "o"),
        ("WOLF359", "Wolf 359 (2.41 pc)", "#2166ac", "s"),
        ("LALANDE21185", "Lalande 21185 (2.55 pc)", "#d95f02", "^"),
        ("GJ486", "GJ 486 (8.08 pc)", "#762a83", "D"),
    ]
    for st, lbl, col, mk in north_styles:
        carm = sorted([(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in br8 if r["star"] == st and r["instrument"] == "CARMENES_VIS"])
        spir = sorted([(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in br8 if r["star"] == st and r["instrument"] == "SPIROU"])
        if carm:
            ax2.plot([x[0] for x in carm], [x[1] for x in carm], linestyle=":", marker=mk, markersize=4.5, color=col, alpha=0.75, linewidth=1.6)
        if spir:
            ax2.plot([x[0] for x in spir], [x[1] for x in spir], linestyle="-", marker=mk, markersize=5.2, color=col, linewidth=2.0, label=lbl)

    ax2.axvspan(0.995, 1.07, color="#f39c12", alpha=0.16, label="CARMENES VIS >995 nm dichroic roll-off")
    ax2.axvline(1.0641, color="#555555", linestyle="--", linewidth=1.0)
    ax2.text(1.055, 0.055, "1064.1 nm", rotation=90, ha="right", va="bottom", fontsize=7.2, color="#333333")
    ax2.set_yscale("log")
    ax2.set_xlim(0.50, 2.45)
    ax2.set_ylim(0.04, 350.0)
    ax2.set_xlabel("Vacuum Wavelength (um)")
    ax2.set_ylabel("8-sigma 10 m CW Laser Power Limit (kW)")
    ax2.set_title("B. Northern < 10 pc Dichroic-Gap Bridge (CARMENES_VIS dotted / SPIRou solid)")
    ax2.legend(loc="lower right", framealpha=0.92, fontsize=7.6)

    fig.suptitle("Phase D085 Innovations: Sub-Threshold V4 Comb Search & 0.52-2.45 um Dichroic Gap Closure", y=0.96)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig3_yjhk_limits(cb_rows: list[dict[str, str]], ul_rows: list[dict[str, str]], comb_cal: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.4), dpi=220, gridspec_kw={"width_ratios": [1.0, 1.15]})
    fig.subplots_adjust(left=0.13, right=0.96, top=0.84, bottom=0.15, wspace=0.35)

    # Panel A: 9-Band SPIRou Channel T Completeness Heatmap
    t_bands = sorted({(r["band_id"], float(r["center_vac_A"])) for r in cb_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"}, key=lambda x: x[1])
    s_grid = sorted({float(r["sigma_mult"]) for r in cb_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"})
    mat = np.zeros((len(t_bands), len(s_grid)), dtype=np.float64)
    yl = []
    for i, (bid, cw) in enumerate(t_bands):
        short_id = "_".join(bid.split("_")[:2])
        yl.append(f"{short_id} ({cw/10.0:.0f} nm)")
        for j, sv in enumerate(s_grid):
            row = [r for r in cb_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["band_id"] == bid and float(r["sigma_mult"]) == sv][0]
            mat[i, j] = 100.0 * float(row["completeness"])

    im = ax1.imshow(mat, aspect="auto", cmap="YlGnBu", vmin=0.0, vmax=100.0)
    ax1.set_xticks(np.arange(len(s_grid)))
    ax1.set_xticklabels([f"{int(s)} sig" for s in s_grid])
    ax1.set_yticks(np.arange(len(t_bands)))
    ax1.set_yticklabels(yl, fontsize=7.8)
    ax1.set_xlabel("Injected Signal Significance (Channel T)")
    ax1.set_title("A. SPIRou 9-Band YJHK Injection Completeness")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            ax1.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=7.5, fontweight="bold", color=("white" if v >= 58.0 else "#111111"))
    fig.colorbar(im, ax=ax1, pad=0.02, fraction=0.045, label="Completeness (%)")

    # Panel B: 300 Upper Limits vs Distance by Wavelength Band Group
    groups = [
        ("Y-band (0.995-1.064 um)", lambda w: w < 11500.0, "#2166ac", "o"),
        ("J-band (1.215-1.310 um)", lambda w: 11500.0 <= w < 14500.0, "#1b7837", "s"),
        ("H-band (1.522-1.662 um)", lambda w: 14500.0 <= w < 18800.0, "#d95f02", "^"),
        ("K-band (2.040-2.345 um)", lambda w: w >= 18800.0, "#762a83", "D"),
    ]
    for lbl, pred, col, mk in groups:
        xs = [float(u["dist_pc"]) for u in ul_rows if pred(float(u["wave_bary_vac_A"]))]
        ys = [float(u["p_beam_10m_kw"]) for u in ul_rows if pred(float(u["wave_bary_vac_A"]))]
        ax2.scatter(xs, ys, s=30, c=col, marker=mk, alpha=0.72, edgecolor="#111111", linewidth=0.45, label=lbl, zorder=3)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(2.0, 46.0)
    ax2.set_ylim(0.25, 250.0)
    best_u = min(ul_rows, key=lambda u: float(u["p_beam_10m_kw"]))
    ax2.annotate(f"Best: {best_u['common_name']}\n({float(best_u['p_beam_10m_w']):.0f} W @ {float(best_u['wave_bary_vac_A'])/10:.0f} nm)", xy=(float(best_u["dist_pc"]), float(best_u["p_beam_10m_kw"])), xytext=(4.8, 0.35), fontsize=7.6, fontweight="bold", arrowprops={"arrowstyle": "->", "color": "#222222", "lw": 0.8})
    ax2.axvline(10.0, color="#555555", linestyle="--", linewidth=1.0)
    ax2.text(9.5, 160.0, "< 10 pc", ha="right", fontsize=7.5, color="#444444")
    ax2.set_xlabel("Gaia DR3 Distance d (pc)")
    ax2.set_ylabel("8-sigma 10 m CW Laser Power Limit (kW)")
    ax2.set_title("B. 300 YJHK Upper Limits (25 Science Stars x 12 Bands)")
    ax2.legend(loc="lower right", framealpha=0.92, fontsize=7.5)

    fig.suptitle("Phase D085 SPIRou Radiometric Calibration & 300-Cell YJHK Upper Limits (0.995-2.345 um)", y=0.96)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_fig4_150star_synthesis(u150: list[dict[str, str]], mm160: list[dict[str, str]], cohort_rows: list[dict[str, str]], out_path: Path) -> None:
    fig = plt.figure(figsize=(14.4, 5.5), dpi=220)
    ax1 = fig.add_axes([0.04, 0.14, 0.54, 0.72], projection="mollweide")
    ax2 = fig.add_axes([0.64, 0.16, 0.33, 0.68])

    ra_dec_map: dict[str, tuple[float, float]] = {}
    for r in cohort_rows:
        ra_dec_map[r["canonical_target"]] = (float(r["s_ra"]), float(r["s_dec"]))
    pe = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    for entry in pe["excluded_targets_coordinate_registry"]:
        lbl = str(entry["label"]).split("(")[0].strip()
        if lbl not in ra_dec_map:
            ra_dec_map[lbl] = (float(entry["ra_deg"]), float(entry["dec_deg"]))
    for ws_name, csv_name in [
        ("work_harps_20261114_d079_v3_calibrated_search", "FROZEN_COHORT_D079.csv"),
        ("work_echelle_20261114_d080_v3_1_exoplanet_survey", "FROZEN_COHORT_D080.csv"),
        ("work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey", "FROZEN_COHORT_D081.csv"),
        ("work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey", "FROZEN_COHORT_D082.csv"),
        ("work_crires_20261115_d083_v3_4_kband_and_100star_synthesis", "FROZEN_COHORT_D083.csv"),
        ("work_northern_20261115_d084_v3_5_harpsn_carmenes_survey", "FROZEN_COHORT_D084.csv"),
    ]:
        p_csv = HERE.parent / ws_name / csv_name
        if p_csv.is_file():
            for row in read_csv(p_csv):
                st = row.get("canonical_target", "").strip()
                if st and row.get("s_ra") and row.get("s_dec"):
                    ra_dec_map[st] = (float(row["s_ra"]), float(row["s_dec"]))

    def _to_moll(ra_d: float, dec_d: float) -> tuple[float, float]:
        lon = math.radians(((ra_d + 180.0) % 360.0) - 180.0)
        return lon, math.radians(dec_d)

    prior_xy, d85_xy, ov_xy = [], [], []
    d85_set = {r["canonical_target"] for r in cohort_rows}
    mm_ov_set = {r["system_id"] for r in mm160 if r["multimessenger_overlap"] == "True"}
    for r in u150:
        st = r["star"]
        if st not in ra_dec_map:
            continue
        lon, lat = _to_moll(*ra_dec_map[st])
        if st in mm_ov_set:
            ov_xy.append((lon, lat, st))
        elif st in d85_set:
            d85_xy.append((lon, lat, st))
        else:
            prior_xy.append((lon, lat, st))

    ax1.grid(True, alpha=0.30, linestyle="--")
    eq_ra = np.linspace(-math.pi, math.pi, 180)
    ax1.plot(eq_ra, np.zeros_like(eq_ra), color="#444444", linewidth=1.0, linestyle=":", label="Celestial Equator")
    ax1.scatter([x[0] for x in prior_xy], [x[1] for x in prior_xy], s=28, c="#7f8c8d", alpha=0.78, marker="o", edgecolor="#222222", linewidth=0.45, label=f"D079-D084 Echelle (n={len(prior_xy)})", zorder=3)
    ax1.scatter([x[0] for x in d85_xy], [x[1] for x in d85_xy], s=58, c="#1b7837", marker="^", edgecolor="#111111", linewidth=0.65, label=f"D085 SPIRou YJHK (n={len(d85_xy)} non-MM)", zorder=4)
    ax1.scatter([x[0] for x in ov_xy], [x[1] for x in ov_xy], s=110, c="#d95f02", marker="*", edgecolor="#111111", linewidth=0.65, label=f"Echelle+Radio/TESS Overlap (n={len(ov_xy)})", zorder=5)
    for lon, lat, st in ov_xy:
        if st in ("PROXIMACEN", "RHOCRB", "HD219134", "16CYGB"):
            lbl = {"PROXIMACEN": "Proxima", "RHOCRB": "rho CrB (NEW)", "HD219134": "HD 219134", "16CYGB": "16 Cyg B"}[st]
            dl, db = (-0.28, -0.10) if st == "16CYGB" else (0.0, 0.10)
            ax1.text(lon + dl, lat + db, lbl, fontsize=6.9, fontweight="bold", ha="center", color="#8c2d04")

    ax1.set_title("A. All-Sky 150-Star Echelle + 14 Multi-Messenger Overlap Map", pad=12)
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.03, -0.18), ncol=2, fontsize=7.4, framealpha=0.92)

    phases = ["D079", "D080", "D081", "D082", "D083", "D084", "D085"]
    cum_stars = [12, 38, 60, 80, 100, 125, 150]
    cum_10pc = [0, 3, 18, 29, 35, 53, 73]
    cum_ovlp = [0, 0, 1, 4, 4, 13, 14]
    px = np.arange(len(phases))
    w = 0.27
    b_st = ax2.bar(px - w, cum_stars, width=w, color="#2b5c8f", edgecolor="#222222", label="Unique Stars (-> 150)")
    b_10 = ax2.bar(px, cum_10pc, width=w, color="#1b7837", edgecolor="#222222", label="< 10 pc Census (-> 73)")
    b_mm = ax2.bar(px + w, cum_ovlp, width=w, color="#d95f02", edgecolor="#222222", label="MM Overlaps (-> 14)")
    for b in list(b_st) + list(b_10) + list(b_mm):
        ax2.text(b.get_x() + b.get_width() * 0.5, b.get_height() + 2.0, f"{int(b.get_height())}", ha="center", va="bottom", fontsize=7.0, fontweight="bold")
    ax2.set_ylim(0, 192)
    ax2.set_xticks(px)
    ax2.set_xticklabels(phases, fontsize=8.0)
    ax2.set_ylabel("Cumulative Count")
    ax2.set_title("B. Seven-Spectrograph V3->V4 Growth")
    ax2.legend(loc="upper left", fontsize=7.4, framealpha=0.92)
    ax2.text(0.03, 0.72, "1,009 exposures | 7 spectrographs\n13,284 calibration trials\n160 systems | Verified ETI = 0", transform=ax2.transAxes, ha="left", va="top", fontsize=7.4, fontweight="bold", bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fff8e7", "edgecolor": "#c0392b"})

    fig.suptitle("All-Sky V3.0-V4.0 Panchromatic SETI Program (0.38-2.51 um, 150 Stars / 160 Systems)", y=0.96)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    g6_rows = read_csv(RES / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    comb_cal = read_csv(RES / "COMB_V4_CALIBRATION_381.csv")
    cb_rows = read_csv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    ul_rows = read_csv(RES / "STAR_UPPER_LIMITS_300.csv")
    br8 = read_csv(RES / "PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv")
    u150 = read_csv(RES / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv")
    mm160 = read_csv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv")
    cohort_rows = read_csv(HERE / "FROZEN_COHORT_D085.csv")

    plot_fig1_cascade_and_g6(summary, g6_rows, FIG_DIR / "fig1_d085_spirou_cascade_and_g6_v36_upgrade.png")
    plot_fig2_comb_and_bridge(comb_cal, br8, FIG_DIR / "fig2_d085_comb_v4_calibration_and_northern_bridge.png")
    plot_fig3_yjhk_limits(cb_rows, ul_rows, comb_cal, FIG_DIR / "fig3_d085_yjhk_completeness_and_300_upper_limits.png")
    plot_fig4_150star_synthesis(u150, mm160, cohort_rows, FIG_DIR / "fig4_d085_allsky_150star_73_10pc_and_160system_synthesis.png")
    print("[plot_figures.py] Generated 4 220-DPI figures in results/figures/")


if __name__ == "__main__":
    main()
