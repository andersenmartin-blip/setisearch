#!/usr/bin/env python3
"""Generate 4 publication-quality 180 DPI figures for Phase D084 (NORTHERN_V3_5)
and the 125-star / 136-system all-sky panchromatic SETI synthesis.
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
from matplotlib.colors import Normalize
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


def plot_fig1_cascade_and_g6(summary: dict[str, Any], led_rows: list[dict[str, str]], g6_rows: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=180)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=0.19, wspace=0.28)

    fc = summary["false_alarm_cascade"]
    stages = [
        "Legacy V2\nBenchmark",
        "V3.5 G1\n(Matched+F1)",
        "V3.5 G2\n(Telluric/OH)",
        "V3.5 G3\n(>=3Ep/Star)",
        "V3.5 G4\n(OrderOvlp)",
        "V3.5 G5\n(2D CCD)",
        "V3.5 G6\n(Topo/Pix)",
        "Verified\nETI",
    ]
    counts = [
        int(fc["v2_legacy_false_alarms"]),
        int(fc["v35_total_ledger_g1_candidates"]),
        int(fc["v35_after_g2"]),
        int(fc["v35_after_g3"]),
        int(fc["v35_after_g4"]),
        int(fc["v35_pre_g6_passed_g1_to_g5"]),
        int(fc["automated_qualified_control"]) + int(fc["automated_qualified_science"]),
        int(fc["verified_eti_detections"]),
    ]
    plot_vals = [max(0.65, float(c)) for c in counts]
    colors = ["#c0392b", "#e67e22", "#d35400", "#f39c12", "#2980b9", "#8e44ad", "#16a085", "#1f3a52"]

    bars = ax1.bar(np.arange(len(stages)), plot_vals, color=colors, edgecolor="#222222", linewidth=0.7, zorder=3)
    ax1.set_yscale("log")
    ax1.set_ylim(0.5, max(50.0, max(counts) * 5.5))
    ax1.set_xticks(np.arange(len(stages)))
    ax1.set_xticklabels(stages, rotation=24, ha="right", fontsize=8.0)
    ax1.set_ylabel("Accepted / Remaining Candidates (log scale; 0 shown at floor)")
    ax1.set_title("A. Northern V3.5 Gate Cascade (183 Exposures)")
    ax1.axhline(1.0, color="#666666", linestyle=":", linewidth=0.8)

    for b, cnt in zip(bars, counts):
        y_txt = max(0.75, float(cnt)) * 1.25
        ax1.text(b.get_x() + b.get_width() * 0.5, y_txt, f"{cnt:,}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#111111")

    # Panel B: Gate G6_V35 180-trial cross-star coincidence benchmark + inst breakdown
    classes = [
        ("TRUE_BARYCENTRIC_STELLAR_LASER", "True Barycentric\nStellar Laser\n(Expected PASS)", True, "#1b7837"),
        ("UNLISTED_STATIONARY_SKY_OH_LINE", "Unlisted Night-Sky\nOH Emission\n(Expected VETO)", False, "#d95f02"),
        ("STATIONARY_CCD_WARM_PIXEL_DEFECT", "Fixed Detector\nWarm Pixel\n(Expected VETO)", False, "#7570b3"),
    ]
    sigmas = [6.0, 10.0, 16.0]
    x = np.arange(len(classes))
    w = 0.24
    for j, sg in enumerate(sigmas):
        rates = []
        for cls, _, exp_pass, _ in classes:
            sub = [r for r in g6_rows if r["trial_class"] == cls and float(r["sigma_inj"]) == sg]
            ok = sum(1 for r in sub if (r["g6_pass"] == "True") == exp_pass)
            rates.append(100.0 * ok / max(1, len(sub)))
        b2 = ax2.bar(x + (j - 1) * w, rates, width=w * 0.9, label=f"{int(sg)} sigma (n=20/cls)", color=["#66c2a5", "#3288bd", "#1b7837"][j] if False else ["#5aae61", "#2166ac", "#2b4263"][j], edgecolor="#222222", linewidth=0.6, zorder=3)
        for bi, rv in zip(b2, rates):
            ax2.text(bi.get_x() + bi.get_width() * 0.5, rv + 1.8, f"{rv:.0f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    ax2.set_ylim(0, 118)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[1] for c in classes], fontsize=8.2)
    ax2.set_ylabel("Correct Classification Rate (%)")
    ax2.set_title("B. Gate G6_V35 Coincidence Benchmark (180 Trials)")
    ax2.legend(loc="lower right", framealpha=0.92)

    fig.suptitle("Phase D084 (NORTHERN_V3_5): V2-to-V3.5 False-Alarm Cascade & Gate G6 Performance", y=0.96)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_fig2_calibration(inj_rows: list[dict[str, str]], kep_rows: list[dict[str, str]], cb_rows: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 5.6), dpi=180, gridspec_kw={"width_ratios": [1.0, 1.15]})
    fig.subplots_adjust(left=0.06, right=0.94, top=0.84, bottom=0.14, wspace=0.52)

    # Panel A: Completeness vs Sigma curves across channels
    sig_tp = sorted({float(r["sigma_mult"]) for r in inj_rows})
    for inst, mode, lbl, col, mk, ls in [
        ("HARPS_N", "CHANNEL_T_TRANSIENT_1EPOCH", "Ch. T (HARPS-N R=115k)", "#1b7837", "o", "-"),
        ("CARMENES_VIS", "CHANNEL_T_TRANSIENT_1EPOCH", "Ch. T (CARMENES_VIS R=94.6k)", "#2166ac", "s", "-"),
        ("HARPS_N", "CHANNEL_P_PERSISTENT_5EPOCH", "Ch. P 5-epoch (HARPS-N)", "#762a83", "^", "--"),
        ("CARMENES_VIS", "CHANNEL_P_PERSISTENT_5EPOCH", "Ch. P 5-epoch (CARMENES_VIS)", "#d95f02", "v", "--"),
    ]:
        ys = []
        for s in sig_tp:
            sub = [r for r in inj_rows if r["instrument"] == inst and r["mode"] == mode and float(r["sigma_mult"]) == s]
            ys.append(100.0 * sum(1 for r in sub if r["recovered"] == "True") / max(1, len(sub)))
        ax1.plot(sig_tp, ys, marker=mk, linestyle=ls, color=col, linewidth=2.0, markersize=5.5, label=lbl)

    sig_k = sorted({float(r["exp_sigma_mult"]) for r in kep_rows})
    ys_td = [100.0 * sum(1 for r in kep_rows if float(r["exp_sigma_mult"]) == s and r["tdiff_uncomp_recovered"] == "True") / 27.0 for s in sig_k]
    ys_kp = [100.0 * sum(1 for r in kep_rows if float(r["exp_sigma_mult"]) == s and r["kplanet_dedop_recovered"] == "True") / 27.0 for s in sig_k]
    ax1.plot(sig_k, ys_td, marker="x", linestyle=":", color="#7f7f7f", linewidth=1.8, markersize=5.5, label="Ch. T_DIFF (Uncomp. Kep.)")
    ax1.plot(sig_k, ys_kp, marker="D", linestyle="-.", color="#b2182b", linewidth=2.0, markersize=5.0, label="Ch. K_PLANET (Dedoppler)")

    ax1.set_xlim(2.8, 21.0)
    ax1.set_ylim(-4, 108)
    ax1.set_xlabel("Injected Amplitude (local MAD sigma multiple)")
    ax1.set_ylabel("Pipeline Recovery Completeness (%)")
    ax1.set_title("A. Multi-Channel Injection Recovery (1,755 Trials)")
    ax1.legend(loc="upper left", framealpha=0.92, fontsize=7.3)

    # Panel B: 18 Benchmark Laser Bands (9 HARPS-N + 9 CARMENES_VIS) Ch. T completeness heatmap
    t_bands = sorted({(r["instrument"], r["band_id"], float(r["center_vac_A"])) for r in cb_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"}, key=lambda x: (0 if x[0] == "HARPS_N" else 1, x[2]))
    s_grid = sorted({float(r["sigma_mult"]) for r in cb_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH"})
    mat = np.zeros((len(t_bands), len(s_grid)), dtype=np.float64)
    ylabels = []
    for i, (inst, bid, cw) in enumerate(t_bands):
        tag = "HN" if inst == "HARPS_N" else "CV"
        short_id = "_".join(bid.split("_")[:2])
        ylabels.append(f"[{tag}] {short_id} ({cw/10.0:.0f} nm)")
        for j, sv in enumerate(s_grid):
            row = [r for r in cb_rows if r["instrument"] == inst and r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and r["band_id"] == bid and float(r["sigma_mult"]) == sv][0]
            mat[i, j] = 100.0 * float(row["completeness"])

    im = ax2.imshow(mat, aspect="auto", cmap="YlGnBu", vmin=0.0, vmax=100.0)
    ax2.set_xticks(np.arange(len(s_grid)))
    ax2.set_xticklabels([f"{int(s)} sig" for s in s_grid])
    ax2.set_yticks(np.arange(len(t_bands)))
    ax2.set_yticklabels(ylabels, fontsize=7.5)
    ax2.axhline(8.5, color="#111111", linewidth=1.6, linestyle="--")
    ax2.set_xlabel("Channel T Injected Signal Significance")
    ax2.set_title("B. 18-Band Wavelength Completeness (HARPS-N Top / CARMENES Bottom)")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            ax2.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=7.0, fontweight="bold", color=("white" if v >= 58.0 else "#111111"))
    cbar = fig.colorbar(im, ax=ax2, pad=0.02, fraction=0.04)
    cbar.set_label("Completeness (%)", fontsize=8.5)

    fig.suptitle("Phase D084 Prospective Calibration Matrix (2,151 Control Trials Across HARPS-N & CARMENES_VIS)", y=0.96)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_fig3_10pc_limits(s53: list[dict[str, str]], ul_rows: list[dict[str, str]], out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.3), dpi=180)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.84, bottom=0.14, wspace=0.25)

    # Panel A: All 53 stars < 10 pc (35 South + 18 North)
    south_all = [(float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"]), r["common_name"], r["instruments"]) for r in s53 if r["hemisphere"] == "SOUTHERN" and r["min_panchromatic_10m_kw"]]
    north_hn = [(float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"]), r["common_name"]) for r in s53 if r["hemisphere"] == "NORTHERN" and "HARPS_N" in r["instruments"] and r["min_panchromatic_10m_kw"]]
    north_ca = [(float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"]), r["common_name"]) for r in s53 if r["hemisphere"] == "NORTHERN" and "CARMENES_VIS" in r["instruments"] and r["min_panchromatic_10m_kw"]]
    ctrl_10pc = [(float(r["dist_pc"]), r["common_name"], r["hemisphere"]) for r in s53 if not r["min_panchromatic_10m_kw"]]

    if south_all:
        ax1.scatter([x[0] for x in south_all], [x[1] for x in south_all], s=48, c="#7f8c8d", marker="o", alpha=0.80, edgecolor="#222222", linewidth=0.6, label=f"South D079-D083 (<10 pc sci, n={len(south_all)})", zorder=3)
    if north_hn:
        ax1.scatter([x[0] for x in north_hn], [x[1] for x in north_hn], s=72, c="#1b7837", marker="^", edgecolor="#111111", linewidth=0.8, label=f"North D084 HARPS-N (n={len(north_hn)} sci)", zorder=4)
    if north_ca:
        ax1.scatter([x[0] for x in north_ca], [x[1] for x in north_ca], s=72, c="#2166ac", marker="s", edgecolor="#111111", linewidth=0.8, label=f"North D084 CARMENES_VIS (n={len(north_ca)} sci)", zorder=4)

    ax1.set_yscale("log")
    ax1.set_xlim(0.7, 10.4)
    ax1.set_ylim(0.004, 300.0)
    landmarks_abs = {
        "Proxima Centauri": ("Proxima Cen", 1.75, 0.007, "left"),
        "Barnard's Star": ("Barnard's Star", 1.15, 0.046, "left"),
        "Wolf 359 (CN Leo)": ("Wolf 359", 1.05, 0.19, "left"),
        "Lalande 21185": ("Lalande 21185", 1.05, 3.8, "left"),
        "Lalande 21185 (GJ 411)": ("Lalande 21185", 1.05, 3.8, "left"),
        "61 Cygni A": ("61 Cyg A", 3.1, 8.2, "left"),
        "61 Cyg A": ("61 Cyg A", 3.1, 8.2, "left"),
        "DX Cnc (GJ 1111)": ("DX Cnc (73.9 W)", 4.3, 0.042, "left"),
        "GJ 687": ("GJ 687", 5.2, 0.42, "left"),
        "AD Leo (GJ 388)": ("AD Leo", 5.6, 5.2, "left"),
        "AD Leo": ("AD Leo", 5.6, 5.2, "left"),
        "HD 219134": ("HD 219134", 7.1, 13.5, "left"),
    }
    seen_lbl = set()
    for r in s53:
        nm = r["common_name"]
        if nm in landmarks_abs and r["min_panchromatic_10m_kw"]:
            lbl_t, tx, ty, ha_s = landmarks_abs[nm]
            if lbl_t in seen_lbl:
                continue
            seen_lbl.add(lbl_t)
            dp = float(r["dist_pc"])
            pk = float(r["min_panchromatic_10m_kw"])
            ax1.annotate(lbl_t, xy=(dp, pk), xytext=(tx, ty), ha=ha_s, fontsize=7.2, fontweight="bold" if r["hemisphere"] == "NORTHERN" else "normal", color="#111111", arrowprops={"arrowstyle": "-", "color": "#555555", "lw": 0.65})

    ax1.text(10.15, 0.0055, f"+ {len(ctrl_10pc)} zero-planet calibration controls\n(incl. sig Dra, Ross 248, GJ 412 A, GJ 380)", ha="right", va="bottom", fontsize=7.1, bbox={"boxstyle": "round,pad=0.25", "facecolor": "#f8f9fa", "edgecolor": "#bbbbbb"})
    ax1.set_xlabel("Gaia DR3 Distance d (pc)")
    ax1.set_ylabel("Best 8-sigma 10 m CW Laser Power Limit (kW)")
    ax1.set_title("A. All-Sky < 10 pc Census (53 Unique Stars: 35 South + 18 North)")
    ax1.legend(loc="upper left", framealpha=0.92, fontsize=7.5)

    # Panel B: Spectral-band coverage across the 189 D084 science upper-limit cells (395 - 1059 nm)
    by_b: dict[tuple[str, float, str], list[float]] = {}
    for u in ul_rows:
        key = (u["instrument"], float(u["wave_bary_vac_A"]) / 10.0, u["radiometric_anchor"])
        by_b.setdefault(key, []).append(float(u["p_beam_10m_kw"]))

    for inst, mk, col, lbl in [
        ("HARPS_N", "^", "#1b7837", "HARPS-N 9 bands (Gaia G < 850 nm)"),
        ("CARMENES_VIS", "s", "#2166ac", "CARMENES_VIS 9 bands (G < 850 nm; 2MASS J >= 850 nm)"),
    ]:
        xs, meds, p25s, p75s = [], [], [], []
        for (ins, wnm, _), vals in sorted(by_b.items(), key=lambda kv: kv[0][1]):
            if ins != inst:
                continue
            arr = np.asarray(vals, dtype=np.float64)
            xs.append(wnm)
            meds.append(float(np.median(arr)))
            p25s.append(float(np.percentile(arr, 25)))
            p75s.append(float(np.percentile(arr, 75)))
        xs_a, med_a, p25_a, p75_a = np.array(xs), np.array(meds), np.array(p25s), np.array(p75s)
        ax2.plot(xs_a, med_a, marker=mk, color=col, linewidth=2.0, markersize=6.5, label=lbl, zorder=4)
        ax2.fill_between(xs_a, p25_a, p75_a, color=col, alpha=0.16, zorder=2)

    ax2.axvline(850.0, color="#c0392b", linestyle="--", linewidth=1.3, label="Gaia G / 2MASS J split (850 nm)")
    ax2.axvspan(995.0, 1085.0, color="#f39c12", alpha=0.12, zorder=1, label="CARMENES VIS/NIR dichroic roll-off (>995 nm)")
    ax2.axvline(1064.0, color="#7f7f7f", linestyle=":", linewidth=1.2)
    ax2.text(1058.0, 1.4, "1064 nm\nNd:YAG", ha="right", fontsize=7.2, color="#444444")
    ax2.set_yscale("log")
    ax2.set_xlim(370, 1085)
    ax2.set_ylim(0.4, 900.0)
    ax2.set_xlabel("Benchmark Laser Wavelength (nm)")
    ax2.set_ylabel("Median [IQR] 8-sigma 10 m Laser Power (kW)")
    ax2.set_title("B. Dual-Band Radiometric Limits Across 189 Science Cells")
    ax2.legend(loc="upper left", framealpha=0.92, fontsize=7.2)

    fig.suptitle("Phase D084 Sensitivity & Full 53-Star (< 10 pc) Solar-Neighborhood Panchromatic Census", y=0.96)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_fig4_125star_136system_sky(
    u125: list[dict[str, str]],
    mm136: list[dict[str, str]],
    cohort_rows: list[dict[str, str]],
    prior_snap: dict[str, Any],
    summary: dict[str, Any],
    out_path: Path,
) -> None:
    fig = plt.figure(figsize=(14.0, 5.4), dpi=180)
    ax1 = fig.add_axes([0.04, 0.14, 0.54, 0.72], projection="mollweide")
    ax2 = fig.add_axes([0.64, 0.16, 0.33, 0.68])

    # Build RA/Dec lookup: D084 directly from FROZEN_COHORT_D084; prior 100 stars from exclusion registry
    ra_dec_map: dict[str, tuple[float, float]] = {}
    for r in cohort_rows:
        ra_dec_map[r["canonical_target"]] = (float(r["s_ra"]), float(r["s_dec"]))

    pe = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    for entry in pe["excluded_targets_coordinate_registry"]:
        lbl = str(entry["label"]).split("(")[0].strip()
        if lbl not in ra_dec_map:
            ra_dec_map[lbl] = (float(entry["ra_deg"]), float(entry["dec_deg"]))

    # Also read prior D079-D083 frozen cohorts cleanly for exact 100 southern coordinates
    for ws_name, csv_name in [
        ("work_harps_20261114_d079_v3_calibrated_search", "FROZEN_COHORT_D079.csv"),
        ("work_echelle_20261114_d080_v3_1_exoplanet_survey", "FROZEN_COHORT_D080.csv"),
        ("work_echelle_20261115_d081_v3_2_transit_kinematics_and_10pc_survey", "FROZEN_COHORT_D081.csv"),
        ("work_nirps_20261115_d082_v3_3_near_ir_and_panchromatic_survey", "FROZEN_COHORT_D082.csv"),
        ("work_crires_20261115_d083_v3_4_kband_and_100star_synthesis", "FROZEN_COHORT_D083.csv"),
    ]:
        p_csv = HERE.parent / ws_name / csv_name
        if p_csv.is_file():
            for row in read_csv(p_csv):
                st = row.get("canonical_target", "").strip()
                if st and row.get("s_ra") and row.get("s_dec"):
                    ra_dec_map[st] = (float(row["s_ra"]), float(row["s_dec"]))

    def _to_moll(ra_d: float, dec_d: float) -> tuple[float, float]:
        # Standard astronomy RA: center RA=12h (180 deg -> 0 rad), East to left or standard [-pi, pi]
        lon = math.radians(((ra_d + 180.0) % 360.0) - 180.0)
        lat = math.radians(dec_d)
        return lon, lat

    s_xy, n_xy, ov_xy = [], [], []
    mm_ov_set = {r["system_id"] for r in mm136 if r["multimessenger_overlap"] == "True"}
    for r in u125:
        st = r["star"]
        if st not in ra_dec_map:
            continue
        lon, lat = _to_moll(*ra_dec_map[st])
        if st in mm_ov_set:
            ov_xy.append((lon, lat, st))
        elif r["hemisphere"] == "NORTHERN":
            n_xy.append((lon, lat, st))
        else:
            s_xy.append((lon, lat, st))

    ax1.grid(True, alpha=0.30, linestyle="--")
    # Celestial equator
    eq_ra = np.linspace(-math.pi, math.pi, 180)
    ax1.plot(eq_ra, np.zeros_like(eq_ra), color="#444444", linewidth=1.0, linestyle=":", label="Celestial Equator (Dec=0)")
    ax1.scatter([x[0] for x in s_xy], [x[1] for x in s_xy], s=32, c="#7f8c8d", alpha=0.80, marker="o", edgecolor="#222222", linewidth=0.5, label=f"South D079-D083 (non-MM, n={len(s_xy)})", zorder=3)
    ax1.scatter([x[0] for x in n_xy], [x[1] for x in n_xy], s=52, c="#2166ac", marker="^", edgecolor="#111111", linewidth=0.7, label=f"North D084 (non-MM, n={len(n_xy)})", zorder=4)
    ax1.scatter([x[0] for x in ov_xy], [x[1] for x in ov_xy], s=105, c="#d95f02", marker="*", edgecolor="#111111", linewidth=0.7, label=f"Echelle+Radio/TESS Overlap (n={len(ov_xy)})", zorder=5)

    ov_lbls = {
        "PROXIMACEN": ("Proxima", 0.0, +0.11),
        "HD219134": ("HD 219134", 0.0, +0.09),
        "16CYGB": ("16 Cyg B", -0.22, -0.09),
        "HD87883": ("HD 87883", 0.0, -0.14),
        "L9859": ("L 98-59", 0.0, +0.09),
        "GJ581": ("GJ 581", +0.18, -0.11),
    }
    for lon, lat, st in ov_xy:
        if st in ov_lbls:
            txt_l, dl, db = ov_lbls[st]
            ax1.text(lon + dl, lat + db, txt_l, fontsize=6.8, fontweight="bold", ha="center", color="#8c2d04")

    ax1.set_title("A. All-Sky 125-Star Echelle + 13 Multi-Messenger Overlap Distribution", pad=12)
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.03, -0.18), ncol=2, fontsize=7.4, framealpha=0.92)

    # Panel B: Program growth curve D079 -> D084 across 7 spectrographs
    phases = ["D079\n(V3)", "D080\n(V3.1)", "D081\n(V3.2)", "D082\n(V3.3)", "D083\n(V3.4)", "D084\n(V3.5)"]
    cum_stars = [20, 44, 65, 80, 100, 125]
    cum_10pc = [10, 10, 29, 31, 35, 53]
    cum_ovlp = [1, 1, 2, 2, 4, 13]
    px = np.arange(len(phases))
    w = 0.27
    b_st = ax2.bar(px - w, cum_stars, width=w, color="#2b5c8f", edgecolor="#222222", label="Unique Stars (-> 125)")
    b_10 = ax2.bar(px, cum_10pc, width=w, color="#1b7837", edgecolor="#222222", label="< 10 pc Census (-> 53)")
    b_mm = ax2.bar(px + w, cum_ovlp, width=w, color="#d95f02", edgecolor="#222222", label="MM Overlaps (-> 13)")

    for b in b_st:
        ax2.text(b.get_x() + b.get_width() * 0.5, b.get_height() + 2.0, f"{int(b.get_height())}", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    for b in b_10:
        ax2.text(b.get_x() + b.get_width() * 0.5, b.get_height() + 2.0, f"{int(b.get_height())}", ha="center", va="bottom", fontsize=7.2, color="#1b7837", fontweight="bold")
    for b in b_mm:
        ax2.text(b.get_x() + b.get_width() * 0.5, b.get_height() + 2.0, f"{int(b.get_height())}", ha="center", va="bottom", fontsize=7.2, color="#a63603", fontweight="bold")

    ax2.set_ylim(0, 168)
    ax2.set_xticks(px)
    ax2.set_xticklabels(phases, fontsize=8.0)
    ax2.set_ylabel("Cumulative Count")
    ax2.set_title("B. Six-Spectrograph V3 Campaign Growth")
    ax2.legend(loc="upper left", fontsize=7.4, framealpha=0.92)
    ax2.text(0.03, 0.72, "Total: 832 exposures\n10,692 control trials\n136 stellar systems\nVerified ETI = 0", transform=ax2.transAxes, ha="left", va="top", fontsize=7.5, fontweight="bold", bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fff8e7", "edgecolor": "#c0392b"})

    fig.suptitle("All-Sky V3.0-V3.5 Panchromatic Echelle SETI Program (388-2469 nm, 125 Stars / 136 Systems)", y=0.96)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    led_rows = read_csv(RES / "V3_5_CANDIDATE_LEDGER.csv")
    g6_rows = read_csv(RES / "G6_TOPO_COINCIDENCE_CALIBRATION_180.csv")
    inj_rows = read_csv(RES / "INJECTION_RECOVERY_1620.csv")
    kep_rows = read_csv(RES / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    cb_rows = read_csv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    s53 = read_csv(RES / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv")
    ul_rows = read_csv(RES / "STAR_UPPER_LIMITS_189.csv")
    u125 = read_csv(RES / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv")
    mm136 = read_csv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv")
    cohort_rows = read_csv(HERE / "FROZEN_COHORT_D084.csv")
    prior_snap = json.loads((HERE / "PRIOR_V3_PHASES_SNAPSHOT.json").read_text(encoding="utf-8"))

    plot_fig1_cascade_and_g6(summary, led_rows, g6_rows, FIG_DIR / "fig1_northern_cascade_and_g6_coincidence.png")
    plot_fig2_calibration(inj_rows, kep_rows, cb_rows, FIG_DIR / "fig2_dual_observatory_calibration_2151.png")
    plot_fig3_10pc_limits(s53, ul_rows, FIG_DIR / "fig3_allsky_53star_10pc_panchromatic_limits.png")
    plot_fig4_125star_136system_sky(u125, mm136, cohort_rows, prior_snap, summary, FIG_DIR / "fig4_allsky_125star_136system_synthesis.png")
    print("[plot_figures.py] Generated 4 180-DPI figures in results/figures/")


if __name__ == "__main__":
    main()
