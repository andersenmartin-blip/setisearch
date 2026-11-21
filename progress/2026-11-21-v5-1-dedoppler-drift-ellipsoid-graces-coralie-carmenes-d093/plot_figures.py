#!/usr/bin/env python3
"""Generate 6 publication-grade 240-DPI PNG figures for SETI Phase D093 (V5.1)."""

from __future__ import annotations

import csv
import json
import math
import pathlib
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

WS = pathlib.Path(__file__).resolve().parent
RES = WS / "results"
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
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 240,
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fname: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
    print(f"Wrote {out}", flush=True)


def fig1_blind_drift_and_orbital(summary: dict[str, Any]) -> None:
    cal_drift = _read_csv("CALIBRATION_V51_BLIND_DRIFT_120.csv")
    emp_drift = _read_csv("BLIND_DRIFT_V51_CANDIDATES.csv")
    orb_rows = _read_csv("ORBITAL_CAMPAIGN_RESULTS_8.csv")
    kep_cal = _read_csv("KEPLERIAN_TRACK_CALIBRATION_81.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    # Panel A: Synthetic Blind Drift recovery vs empirical D093 drift pairs
    inj_dv = [abs(float(r["dv_inj_kms"])) for r in cal_drift if r["trial_class"] == "DRIFTING_LASER"]
    inj_z = [float(r["z_drift_comb"]) for r in cal_drift if r["trial_class"] == "DRIFTING_LASER"]
    stat_z = [float(r["z_drift_comb"]) for r in cal_drift if r["trial_class"] == "STATIONARY_LINE"]
    tr_z = [float(r["z_drift_comb"]) for r in cal_drift if r["trial_class"] == "SINGLE_EPOCH_TRANSIENT"]

    emp_rej_dv = [abs(float(r["dv_kms"])) for r in emp_drift if r["g8_pass"] != "True"]
    emp_rej_z = [float(r["z_drift_comb"]) for r in emp_drift if r["g8_pass"] != "True"]
    emp_acc_dv = [abs(float(r["dv_kms"])) for r in emp_drift if r["g8_pass"] == "True"]
    emp_acc_z = [float(r["z_drift_comb"]) for r in emp_drift if r["g8_pass"] == "True"]

    ax1.scatter(inj_dv, inj_z, s=34, color="#1b9e77", alpha=0.85, label="Calib. Drifting Lasers (60/60 rec.)", zorder=3)
    ax1.scatter(emp_rej_dv, emp_rej_z, s=26, color="#7570b3", alpha=0.65, marker="s", label=f"Emp. D093 Drift Pairs (G8-fail/conf., {len(emp_rej_dv)})", zorder=2)
    ax1.scatter(emp_acc_dv, emp_acc_z, s=90, color="#d95f02", edgecolor="black", marker="*", label=f"Emp. G8-passed Chance Coinc. ({len(emp_acc_dv)}, 0 ETI)", zorder=4)
    ax1.axhline(7.5, color="#333333", linestyle="--", linewidth=1.1, label="Threshold $z_{\\rm comb} = 7.5$")
    ax1.axvline(5.0, color="#666666", linestyle=":", linewidth=1.1, label="Min drift $|\\Delta v| = 5\\;{\\rm km\\,s^{-1}}$")
    ax1.annotate(
        f"Stationary (0/30 FA)\n1-Epoch Transient (0/30 FA)\nMax z_comb = {max(stat_z + tr_z):.2f}",
        xy=(15, 2.2), xytext=(78, 3.2),
        fontsize=8.2, bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4", ec="#999999"),
    )
    ax1.set_xlabel("Absolute Inter-Epoch Velocity Drift $|\\Delta v|$ (km s$^{-1}$)")
    ax1.set_ylabel("Combined Two-Epoch Drift Significance $z_{\\rm comb}$")
    ax1.set_title("A. Blind Linear Drift-Rate Search ($1.115\\times10^8$ Evals)")
    ax1.set_xlim(-5, 235)
    ax1.set_ylim(0, max(inj_z + emp_rej_z + emp_acc_z + [24.0]) * 1.24)
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(alpha=0.25)

    # Panel B: 8 Keplerian Orbital Campaigns + Keplerian track calibration inset box
    labels = [f"#{r['campaign_number']} {r['star']}\n({r['instrument'].split('_')[-1]})" for r in orb_rows]
    spans = [float(r["orbital_dv_span_kms"]) for r in orb_rows]
    kps = [float(r["kp_kms"]) for r in orb_rows]
    y_pos = np.arange(len(labels))
    h = 0.36
    ax2.barh(y_pos - h / 2, kps, height=h, color="#2b8cbe", label="Keplerian $K_p$ (km s$^{-1}$)")
    ax2.barh(y_pos + h / 2, spans, height=h, color="#e34a33", alpha=0.85, label="Observed In-Window $\\Delta v$ Span (km s$^{-1}$)")
    for i, (kp, sp) in enumerate(zip(kps, spans)):
        ax2.text(max(kp, sp) + 4.0, i, "V5.1=0 (0 ETI)", va="center", fontsize=7.8, color="#222222")

    n_td = sum(1 for r in kep_cal if r["tdiff_uncomp_recovered"] == "True")
    n_kp = sum(1 for r in kep_cal if r["kplanet_dedop_recovered"] == "True")
    ax2.text(
        0.97, 0.25,
        f"Calib (81 trials): T_DIFF {n_td}/81 | K_PLANET {n_kp}/81\nEmpirical #110–#117: 0 qualified",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=8.0,
        bbox=dict(boxstyle="round,pad=0.35", fc="#fff8e7", ec="#d95f02"),
    )
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels)
    ax2.invert_yaxis()
    ax2.set_xlim(0, max(max(kps), max(spans)) * 1.38)
    ax2.set_xlabel("Planetary Orbital Velocity Scale (km s$^{-1}$)")
    ax2.set_title("B. 8 New Exoplanet Orbital Campaigns (#110–#117)")
    ax2.legend(loc="lower right", bbox_to_anchor=(0.98, 0.41), frameon=True)
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("D093 Blind Drift-Rate (DRIFT_V51) Search and Orbital Planet-Rest Campaigns", y=0.99)
    _save(fig, "fig1_d093_blind_drift_and_graces_transits.png")


def fig2_rpca_g8_and_d088(summary: dict[str, Any]) -> None:
    patch_cal = _read_csv("CALIBRATION_V51_PATCH_NOVELTY_120.csv")
    d88 = summary["retroactive_d088_northern_regression"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    classes = [
        ("ISOLATED_LSF_LASER", "Isolated LSF Laser\n(39/40 pass)", "#1b9e77"),
        ("SHARED_PHOTOSPHERIC_PATCH", "Shared Photospheric\n(0/40 pass)", "#7570b3"),
        ("TOPO_BLAZE_ARTIFACT", "Topo / Blaze Artifact\n(0/40 pass)", "#d95f02"),
    ]
    data = [[float(r["novelty_z"]) for r in patch_cal if r["trial_class"] == c] for c, _, _ in classes]
    rng = np.random.default_rng(7)
    bp = ax1.boxplot(data, positions=[1, 2, 3], widths=0.45, patch_artist=True, showfliers=False)
    for box, (_, _, col) in zip(bp["boxes"], classes):
        box.set(facecolor=col, alpha=0.35, edgecolor=col, linewidth=1.3)
    for med in bp["medians"]:
        med.set(color="black", linewidth=1.5)
    for idx, (vals, (_, _, col)) in enumerate(zip(data, classes), 1):
        jit = rng.normal(0.0, 0.06, len(vals))
        ax1.scatter(np.full(len(vals), idx) + jit, vals, s=18, color=col, alpha=0.8, zorder=3)
    ax1.axhline(3.5, color="#b2182b", linestyle="--", linewidth=1.2, label="Threshold $\\mathrm{novelty\\_z} = 3.5$")
    ax1.set_xticks([1, 2, 3])
    ax1.set_xticklabels([lbl for _, lbl, _ in classes])
    ax1.set_ylabel("Gate G8_V51b Standardized Patch Novelty $z$")
    ax1.set_title("A. Gate G8_V51b Patch-Novelty Calibration (120 Trials)")
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(axis="y", alpha=0.25)

    # Panel B: Retroactive D088 Northern Regression
    stars_d88 = ["GJ625", "LALANDE21185", "HD114710", "HD157881", "TOTAL\n(All 4 Stars)"]
    v39_c = [d88["top_d088_stars_before_after"][s]["v39"] for s in ["GJ625", "LALANDE21185", "HD114710", "HD157881"]] + [d88["d088_v39_qualified_input"]]
    v50_c = [d88["top_d088_stars_before_after"][s]["v50_g7"] for s in ["GJ625", "LALANDE21185", "HD114710", "HD157881"]] + [d88["d088_v50_g7_survivors"]]
    v51_c = [d88["top_d088_stars_before_after"][s]["v51_g7_g8"] for s in ["GJ625", "LALANDE21185", "HD114710", "HD157881"]] + [d88["d088_v51_g7_g8_survivors"]]

    x = np.arange(len(stars_d88))
    w = 0.25
    b1 = ax2.bar(x - w, v39_c, width=w, color="#9e9ac8", label="D088 V3.9 Input (20)")
    b2 = ax2.bar(x, v50_c, width=w, color="#41b6c4", label="After G7_V50 RPCA (13)")
    b3 = ax2.bar(x + w, v51_c, width=w, color="#1b7837", label="After G7 + G8_V51b (1)")
    for bars in (b1, b2, b3):
        for bar in bars:
            val = int(bar.get_height())
            ax2.text(bar.get_x() + bar.get_width() / 2, val + 0.3, str(val), ha="center", va="bottom", fontsize=8.0)

    ax2.annotate(
        "95.0% False-Alarm Reduction\nSole survivor: LALANDE21185\n(7690.48 Å O$_2$ A-band; 0 ETI)",
        xy=(1 + w, 1.0), xytext=(0.45, 13.5),
        arrowprops=dict(arrowstyle="->", color="#444444", lw=1.0),
        fontsize=8.1, bbox=dict(boxstyle="round,pad=0.35", fc="#eef7f2", ec="#1b7837"),
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(stars_d88)
    ax2.set_ylim(0, max(v39_c) * 1.18)
    ax2.set_ylabel("Qualified Narrowband Candidates")
    ax2.set_title("B. Retroactive Northern D088 Suppression (4,727 G1 Records)")
    ax2.legend(loc="upper left", frameon=True)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Gate G8_V51b Patch-Novelty Calibration and Retroactive D088 Suppression", y=0.99)
    _save(fig, "fig2_d093_rpca_rarity_g8_patch_and_d088_regression.png")


def fig3_nirspec_and_agnostic() -> None:
    nir_rows = _read_csv("JWST_NIRSPEC_G395H_MOLECULAR_CCF_44CELLS.csv")
    ag_cal = _read_csv("CALIBRATION_V51_AGNOSTIC_MULTISCALE_120.csv")
    ag_emp = _read_csv("V5_1_AGNOSTIC_MULTISCALE_SURVIVORS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), gridspec_kw={"width_ratios": [1.15, 0.95]})
    fig.subplots_adjust(wspace=0.30)

    stars = []
    seen = set()
    for r in nir_rows:
        if r["star"] not in seen:
            seen.add(r["star"])
            stars.append(r["star"])
    mols = ["NO2", "N2O", "CH4_C2H6", "CO_13CO"]
    mat = np.zeros((len(stars), len(mols)), dtype=float)
    passed = np.zeros((len(stars), len(mols)), dtype=bool)
    roles = {}
    for r in nir_rows:
        i = stars.index(r["star"])
        j = mols.index(r["molecule"])
        mat[i, j] = float(r["ccf_sigma_abs"])
        passed[i, j] = r["passes_ccf"] == "True"
        roles[r["star"]] = r["role"]

    im = ax1.imshow(mat, cmap="RdBu_r", vmin=-9.0, vmax=9.0, aspect="auto")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.03)
    cbar.set_label("Joint-Confounder CCF Significance ($\\sigma$)")
    for i in range(len(stars)):
        for j in range(len(mols)):
            val = mat[i, j]
            txt = f"{val:+.1f}"
            fw = "bold" if passed[i, j] else "normal"
            col = "white" if abs(val) > 5.2 else "black"
            ax1.text(j, i, txt, ha="center", va="center", fontsize=8.0, fontweight=fw, color=col)
            if passed[i, j]:
                ax1.add_patch(plt.Rectangle((j - 0.48, i - 0.48), 0.96, 0.96, fill=False, ec="gold", lw=2.2))

    ax1.set_xticks(range(len(mols)))
    ax1.set_xticklabels(["NO$_2$\n(4.56 ppm)", "N$_2$O\n(5.76 ppm)", "CH$_4$+C$_2$H$_6$\n(3.31 ppm)", "CO/$^{13}$CO\n(3.72 ppm)"])
    ax1.set_yticks(range(len(stars)))
    ax1.set_yticklabels([f"{s} ({'CTRL' if roles[s]=='CONTROL' else 'SCI'})" for s in stars])
    ax1.set_title("A. JWST NIRSpec G395H CCF (11 Targets $\\times$ 4 Gases)")

    # Panel B: Agnostic Multi-Scale Matched Filter calibration + 3 empirical survivors
    scales = [2.0, 4.0, 8.0, 14.0]
    g_z = [float(r["z_multi"]) for r in ag_cal if r["kernel"] == "gaussian"]
    g_s = [float(r["scale_lsf"]) for r in ag_cal if r["kernel"] == "gaussian"]
    b_z = [float(r["z_multi"]) for r in ag_cal if r["kernel"] != "gaussian"]
    b_s = [float(r["scale_lsf"]) for r in ag_cal if r["kernel"] != "gaussian"]
    ax2.scatter(np.array(g_s) - 0.25, [abs(z) for z in g_z], s=30, color="#2b8cbe", alpha=0.75, label="Calib Gaussian $\\pm$ (60/60 rec.)")
    ax2.scatter(np.array(b_s) + 0.25, [abs(z) for z in b_z], s=30, marker="^", color="#7570b3", alpha=0.75, label="Calib Boxcar $\\pm$ (60/60 rec.)")

    emp_s = [float(r["scale_lsf"]) for r in ag_emp]
    emp_z = [abs(float(r["z_multi"])) for r in ag_emp]
    ax2.scatter(emp_s, emp_z, s=95, marker="*", color="#d95f02", edgecolor="black", zorder=5, label=f"Emp. D093 Survivors ({len(ag_emp)}, 0 ETI)")
    for r in ag_emp:
        zy = abs(float(r["z_multi"]))
        sx = float(r["scale_lsf"])
        if zy > 20.0:
            tx, ty = sx + 1.0, zy - 0.3
        elif abs(float(r["wave_rest_a"]) - 4907.475) < 5.0:
            tx, ty = sx + 3.4, zy + 4.4
        else:
            tx, ty = sx + 3.4, zy - 3.0
        ax2.annotate(f"{r['star']} ({float(r['wave_rest_a']):.0f} Å)", xy=(sx, zy), xytext=(tx, ty), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.0)

    ax2.axhline(7.5, color="#b2182b", linestyle="--", lw=1.1, label="Threshold $|z_{\\rm multi}| = 7.5$")
    ax2.set_xticks(scales)
    ax2.set_xticklabels(["2 LSF", "4 LSF", "8 LSF", "14 LSF"])
    ax2.set_xlabel("Matched-Filter Kernel Scale ($\\sigma_{\\rm LSF}$)")
    ax2.set_ylabel("Absolute Multi-Scale Score $|z_{\\rm multi}|$")
    ax2.set_title("B. Agnostic Multi-Scale Matched Filter (120/120 Calib)")
    ax2.set_xlim(0.5, 15.8)
    ax2.set_ylim(5, max(emp_z + [abs(z) for z in g_z + b_z]) * 1.15)
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(alpha=0.25)

    fig.suptitle("JWST NIRSpec G395H Technosignature Atmosphere CCF and Agnostic Multi-Scale Search", y=0.99)
    _save(fig, "fig3_d093_nirspec_g395h_molecular_ccf_and_agnostic.png")


def fig4_ellipsoid_and_etz() -> None:
    cat = _read_csv("MULTIEVENT_ELLIPSOID_CATALOG_D079_D093.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    fig.subplots_adjust(wspace=0.26)

    abs_beta = [abs(float(r["ecliptic_lat_deg"])) for r in cat]
    dt_min = [max(0.5, float(r["min_abs_ellipsoid_dt_days"])) for r in cat]
    is_etz = [r["etz_qualified"] == "True" for r in cat]
    is_d93 = ["D093" in r["phases"] for r in cat]

    other_x = [b for b, e, d in zip(abs_beta, is_etz, is_d93) if not e and not d]
    other_y = [dt for dt, e, d in zip(dt_min, is_etz, is_d93) if not e and not d]
    d93_x = [b for b, e, d in zip(abs_beta, is_etz, is_d93) if d]
    d93_y = [dt for dt, e, d in zip(dt_min, is_etz, is_d93) if d]
    etz_x = [b for b, e in zip(abs_beta, is_etz) if e]
    etz_y = [dt for dt, e in zip(dt_min, is_etz) if e]

    ax1.scatter(other_x, other_y, s=16, color="#8da0cb", alpha=0.65, label="D079–D092 Stars (non-ETZ)")
    ax1.scatter(d93_x, d93_y, s=50, marker="s", color="#e78ac3", edgecolor="black", lw=0.6, label="D093 New Cohort (15 stars)")
    ax1.scatter(etz_x, etz_y, s=90, marker="D", color="#d95f02", edgecolor="black", lw=0.8, zorder=4, label="ETZ $|\\beta|\\leq 0.264^\\circ$ (10 stars)")

    for r in cat:
        if r["star"] in ("ROSS64", "HD111031", "HD206301", "WOLF359"):
            bx = abs(float(r["ecliptic_lat_deg"]))
            dy = max(0.5, float(r["min_abs_ellipsoid_dt_days"]))
            ox, oy = (bx + 4.5, dy * 1.45) if r["star"] != "HD206301" else (bx + 4.5, dy * 0.72)
            ax1.annotate(f"{r['star']} ({dy:.1f} d)" if dy < 500 else f"{r['star']} (ETZ)", xy=(bx, dy), xytext=(ox, oy), arrowprops=dict(arrowstyle="->", lw=0.8, color="#333333"), fontsize=8.0)

    ax1.axvline(0.264, color="#d95f02", linestyle="--", lw=1.1, label="Earth Transit Zone $|\\beta|=0.264^\\circ$")
    ax1.axhline(180.0, color="#1b9e77", linestyle=":", lw=1.2, label="Ellipsoid Window $|\\Delta t|\\leq 180$ d (33 stars)")
    ax1.set_yscale("log")
    ax1.set_xlabel("Absolute Ecliptic Latitude $|\\beta|$ (deg)")
    ax1.set_ylabel("Minimum Multi-Event Synchronization Offset $|\\Delta t_{\\rm sync}|$ (days)")
    ax1.set_title("A. ETZ Geometry & 3-Event Ellipsoid (350 Unique Stars)")
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Sorted minimum |dt| for the 33 stars <= 180 days + event counts
    within180 = sorted([r for r in cat if r["ellipsoid_qualified_180d"] == "True"], key=lambda r: float(r["min_abs_ellipsoid_dt_days"]))
    ev_colors = {"SN1987A": "#2b8cbe", "GW170817": "#e34a33", "SN2023ixf": "#1b9e77"}
    idx180 = np.arange(len(within180))
    vals180 = [float(r["min_abs_ellipsoid_dt_days"]) for r in within180]
    cols180 = [ev_colors.get(r["nearest_event"], "#666666") for r in within180]
    ax2.bar(idx180, vals180, color=cols180, edgecolor="none", alpha=0.88)
    leg_handles = []
    for ev, col in ev_colors.items():
        cnt = sum(1 for r in within180 if r["nearest_event"] == ev)
        leg_handles.append(Patch(facecolor=col, label=f"{ev} ({cnt} stars)"))
    for i, r in enumerate(within180):
        if r["star"] == "HD111031":
            ax2.annotate(f"HD111031\n({float(r['min_abs_ellipsoid_dt_days']):.1f} d)", xy=(i, float(r["min_abs_ellipsoid_dt_days"])), xytext=(i + 1.0, 42.0), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=7.8, fontweight="bold")
        elif r["star"] == "ROSS64":
            ax2.annotate(f"ROSS64\n({float(r['min_abs_ellipsoid_dt_days']):.1f} d)", xy=(i, float(r["min_abs_ellipsoid_dt_days"])), xytext=(max(0, i - 9), 186.0), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=7.8, fontweight="bold")
    ax2.axhline(180.0, color="#333333", linestyle="--", lw=1.0)
    ax2.set_xlabel("Stars Ranked by Closest SETI Ellipsoid Passage (n = 33)")
    ax2.set_ylabel("$|\\Delta t_{\\rm sync}|$ to Nearest Reference Event (days)")
    ax2.set_title("B. 33 Stars Within $\\pm 180$-Day Ellipsoid Synchronization Window")
    ax2.set_ylim(0, 222)
    ax2.legend(handles=leg_handles, loc="upper left", frameon=True)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("D079–D093 Multi-Event SETI Ellipsoid (SN 1987A / GW170817 / SN 2023ixf) & ETZ Catalog", y=0.99)
    _save(fig, "fig4_d093_multievent_ellipsoid_and_etz_synchronization.png")


def fig5_upper_limits_and_10pc() -> None:
    ul93 = _read_csv("STAR_UPPER_LIMITS_D093.csv")
    s153 = _read_csv("SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_153STARS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.3))
    fig.subplots_adjust(wspace=0.27)

    inst_meta = [
        ("CARMENES_VIS", "CARMENES_VIS (6 stars)", "#1b9e77", "o"),
        ("ESO_CORALIE", "ESO_CORALIE (5 stars)", "#2b8cbe", "s"),
        ("GEMINI_GRACES", "GEMINI_GRACES (4 stars)", "#d95f02", "^"),
    ]
    for inst, lbl, col, mk in inst_meta:
        sub = [r for r in ul93 if r["instrument"] == inst]
        xs = [float(r["wave_bary_a"]) / 1e4 for r in sub]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax1.scatter(xs, ys, s=42, color=col, marker=mk, alpha=0.85, label=lbl)

    best_gj = min([r for r in ul93 if r["star"] == "GJ3512"], key=lambda r: float(r["p_beam_10m_kw"]))
    best_co = min([r for r in ul93 if r["instrument"] == "ESO_CORALIE"], key=lambda r: float(r["p_beam_10m_kw"]))
    best_gr = min([r for r in ul93 if r["instrument"] == "GEMINI_GRACES"], key=lambda r: float(r["p_beam_10m_kw"]))
    ax1.annotate(f"GJ3512 M1_5320\n{float(best_gj['p_beam_10m_kw']):.4f} kW (267.6 W)", xy=(float(best_gj["wave_bary_a"]) / 1e4, float(best_gj["p_beam_10m_kw"])), xytext=(0.398, 2.2), arrowprops=dict(arrowstyle="->", lw=0.9), fontsize=8.0, fontweight="bold")
    ax1.annotate(f"HD217107\n{float(best_co['p_beam_10m_kw']):.1f} kW", xy=(float(best_co["wave_bary_a"]) / 1e4, float(best_co["p_beam_10m_kw"])), xytext=(0.43, 62.0), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.0)
    ax1.annotate(f"WASP52\n{float(best_gr['p_beam_10m_kw']):.1f} kW", xy=(float(best_gr["wave_bary_a"]) / 1e4, float(best_gr["p_beam_10m_kw"])), xytext=(0.68, 95.0), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.0)

    ax1.set_yscale("log")
    ax1.set_xlim(0.385, 0.91)
    ax1.set_xlabel("Wavelength ($\\mu$m)")
    ax1.set_ylabel("8$\\sigma$ 10-m Directed Laser EIRP Limit (kW)")
    ax1.set_title("A. D093 60 Star-Band 10-m Laser EIRP Upper Limits")
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: 153 Solar Neighborhood <10 pc Stars (131 valid EIRP bounds)
    d_old = [float(r["dist_pc"]) for r in s153 if r["min_panchromatic_10m_kw"] and "D093" not in r["phases"]]
    p_old = [float(r["min_panchromatic_10m_kw"]) for r in s153 if r["min_panchromatic_10m_kw"] and "D093" not in r["phases"]]
    d_93 = [float(r["dist_pc"]) for r in s153 if r["min_panchromatic_10m_kw"] and "D093" in r["phases"]]
    p_93 = [float(r["min_panchromatic_10m_kw"]) for r in s153 if r["min_panchromatic_10m_kw"] and "D093" in r["phases"]]

    ax2.scatter(d_old, p_old, s=26, color="#6baed6", alpha=0.75, label=f"D079–D092 <10 pc ({len(d_old)} valid)")
    ax2.scatter(d_93, p_93, s=68, marker="D", color="#e34a33", edgecolor="black", lw=0.7, zorder=4, label=f"D093 Brand-New <10 pc ({len(d_93)} stars)")
    med_10pc = float(np.median(p_old + p_93))
    ax2.axhline(med_10pc, color="#1b7837", linestyle="--", lw=1.2, label=f"Median <10 pc Limit = {med_10pc:.3f} kW")

    for r in s153:
        if r["star"] in ("GJ3512", "ROSS64", "PROXIMACEN"):
            dist = float(r["dist_pc"])
            pval = float(r["min_panchromatic_10m_kw"])
            if r["star"] == "ROSS64":
                tx, ty = 6.25, 0.14
            elif r["star"] == "GJ3512":
                tx, ty = 7.4, 0.025
            else:
                tx, ty = 1.9, 0.00028
            ax2.annotate(f"{r['star']}", xy=(dist, pval), xytext=(tx, ty), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.0)

    ax2.set_yscale("log")
    ax2.set_xlabel("Heliocentric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title("B. 10-pc Solar-Neighborhood Atlas (153 Unique Stars, 0.09–13.4 $\\mu$m)")
    ax2.set_xlim(0.8, 10.4)
    ax2.legend(loc="lower right", frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    fig.suptitle("D093 60-Cell EIRP Upper Limits and 8.273-Octave 350-Star Panchromatic Atlas", y=0.99)
    _save(fig, "fig5_d093_upper_limits_and_350star_8p27octave_atlas.png")


def fig6_cascade_and_calibrations(summary: dict[str, Any]) -> None:
    cas = summary["false_alarm_cascade"]
    cal = summary["synthetic_calibration_1591_trials"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.4, 5.7), gridspec_kw={"width_ratios": [0.95, 1.12]})
    fig.subplots_adjust(wspace=0.72)

    stages = [
        ("V2 Legacy", cas["v2_legacy_false_alarms"], "#bdbdbd"),
        ("V3 / G1", cas["v42_total_ledger_g1_candidates"], "#9ecae1"),
        ("G2–G3", cas["v42_after_g3"], "#6baed6"),
        ("G4 Native", cas["v42_after_g4"], "#4292c6"),
        ("G5+G6 (V4.2)", cas["v42_qualified_before_g7"], "#2171b5"),
        ("G7_V50 RPCA", cas["v50_qualified_before_g8"], "#41ab5d"),
        ("G8_V51b Patch", cas["v51_qualified_control"] + cas["v51_qualified_science"], "#1b7837"),
        ("Verified ETI", 0, "#00441b"),
    ]
    y1 = np.arange(len(stages))
    vals1 = [max(0.4, s[1]) for s in stages]
    ax1.barh(y1, vals1, color=[s[2] for s in stages], edgecolor="none")
    for i, (_, raw_v, _) in enumerate(stages):
        ax1.text(max(0.4, raw_v) * 1.15, i, f"{raw_v:,}", va="center", fontsize=8.4, fontweight="bold" if i >= 5 else "normal")
    ax1.set_xscale("log")
    ax1.set_xlim(0.35, 6500)
    ax1.set_yticks(y1)
    ax1.set_yticklabels([s[0] for s in stages])
    ax1.invert_yaxis()
    ax1.set_xlabel("Candidate Count (log scale, 0 shown as bar floor)")
    ax1.set_title("A. D093 V5.1 Narrowband False-Alarm Cascade")
    ax1.text(
        0.96, 0.05,
        f"Parallel V5.1 Streams (All 0 ETI):\n• Blind Drift: {cas['drift_v51_candidates']} pairs -> 0\n• Agnostic: {cas['v51_agnostic_survivors']} surv. -> 0\n• Comb V4.1: {cas['comb_v41_automated_candidates']} cands\n• NIRSpec CCF: {cas['nirspec_ccf_cells_44_detections']}/44 (GJ504 CH4)",
        transform=ax1.transAxes, ha="right", va="bottom", fontsize=7.9,
        bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="#888888"),
    )
    ax1.grid(axis="x", which="both", alpha=0.22)

    def _frac(s: str) -> float:
        tok = s.split("(")[-1].rstrip(")") if "(" in s else s
        if "/" in tok:
            a, b = tok.split("/")
            return 100.0 * float(a) / float(b)
        return 100.0 * float(tok)

    # Rejection metrics shown as true-negative specificity (1 - FA) for clarity
    suites = [
        ("Blind Drift Laser Recov. (60/60)", _frac(cal["blind_drift_recovery"])),
        ("Blind Drift Stat.+Trans. Veto (60/60)", 100.0),
        ("G8_V51b Isolated Laser Pass (39/40)", _frac(cal["g8_patch_isolated_laser_pass"])),
        ("G8_V51b Confounder Veto (80/80)", 100.0),
        ("RPCA Isolated Recovery (56/60)", _frac(cal["rpca_isolated_laser_recovery"])),
        ("RPCA Shared+Topo Veto (120/120)", 100.0),
        ("Agnostic Multi-Scale Recov. (120/120)", _frac(cal["agnostic_multiscale_recovery"])),
        ("NIRSpec Mol. Recovery (80/80)", _frac(cal["nirspec_mol_ccf_recovery"])),
        ("NIRSpec Confounder Veto (80/80)", _frac(cal["nirspec_confounder_veto"])),
        ("Channel T >=8s Recov. (150/162)", _frac(cal["channel_t_ge_8sigma"])),
        ("Channel P >=8s Recov. (157/162)", _frac(cal["channel_p_ge_8sigma"])),
        ("Keplerian K_PLANET Recov. (80/81)", _frac(cal["keplerian_kplanet_ge_6p5sigma"])),
        ("G4/G5 LSF vs CR+Plateau (108/108)", 100.0),
        ("Comb V4.1 (>=3.8s + Veto, 144/144)", 100.0),
    ]
    y2 = np.arange(len(suites))
    vals2 = [v for _, v in suites]
    cols2 = ["#1b9e77" if v >= 99.0 else "#2b8cbe" for v in vals2]
    ax2.barh(y2, vals2, color=cols2, height=0.68)
    for i, v in enumerate(vals2):
        ax2.text(v - 1.5 if v > 85 else v + 1.5, i, f"{v:.1f}%", va="center", ha="right" if v > 85 else "left", color="white" if v > 85 else "black", fontsize=7.8, fontweight="bold")
    ax2.set_yticks(y2)
    ax2.set_yticklabels([n for n, _ in suites])
    ax2.invert_yaxis()
    ax2.set_xlim(0, 103)
    ax2.set_xlabel("Calibration Completeness / Specificity (%)")
    ax2.set_title("B. 9 Synthetic Calibration Suites (1,591 Trials Total)")
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("D093 Five-Stream Veto Cascade and 1,591-Trial Calibration Verification", y=0.99)
    _save(fig, "fig6_d093_five_stream_cascade_and_1591_calibration.png")


def main() -> None:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    fig1_blind_drift_and_orbital(summary)
    fig2_rpca_g8_and_d088(summary)
    fig3_nirspec_and_agnostic()
    fig4_ellipsoid_and_etz()
    fig5_upper_limits_and_10pc()
    fig6_cascade_and_calibrations(summary)
    print("ALL 6 D093 FIGURES GENERATED SUCCESSFULLY.", flush=True)


if __name__ == "__main__":
    main()
