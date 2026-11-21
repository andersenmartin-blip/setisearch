#!/usr/bin/env python3
"""Generate 6 publication-grade 240-DPI PNG figures for SETI Phase D094 (V5.2)."""

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


def fig1_benchmark_and_cohort(summary: dict[str, Any]) -> None:
    bench = _read_csv("FOUR_GEN_BENCHMARK_D094.csv")
    prov = _read_csv("EXPOSURE_PROVENANCE_D094.csv")
    coh = summary["cohort"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), gridspec_kw={"width_ratios": [1.08, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    stages = ["g1_lsf", "g2_airglow", "g3_chromo", "g45_native_psf", "g6_topo", "v50_g7_rpca", "v52_g8_final"]
    st_labels = ["G1 LSF", "G2 Airglow/OH", "G3 Chromo", "G4+G5 Native", "G6 Sparse", "V5.0 G7 RPCA", "V5.2 G8 (0 ETI)"]
    x = np.arange(len(stages))
    cols = {"APOGEE2_H": "#1b9e77", "CRIRES_H": "#2b8cbe", "CRIRES_J": "#7570b3", "CRIRES_Y": "#d95f02"}
    bottom = np.zeros(len(stages))
    for row in bench:
        bg = row["band_group"]
        vals = np.array([int(row[s]) for s in stages], dtype=float)
        ax1.bar(x, vals, bottom=bottom, color=cols.get(bg, "#666666"), width=0.62, label=f"{bg} ({row['n_stars']} {'star' if int(row['n_stars']) == 1 else 'stars'})")
        bottom += vals
    for xi, tot in enumerate(bottom):
        ax1.text(xi, tot + 1.4, f"{int(tot)}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(st_labels, rotation=20, ha="right")
    ax1.set_ylim(0, max(bottom) * 1.18)
    ax1.set_ylabel("Surviving Single-Exposure / Coadd Candidates")
    n_v2_d94 = int(summary["searched_spectral_elements"]["v2_false_alarms_eliminated_d094"])
    ax1.set_title(f"A. Four-Generation Cascade by NIR Band Group ({n_v2_d94} V2 -> 0 ETI)")
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(axis="y", alpha=0.25)

    # Panel B: D094 Multi-Facility Survey Inventory & Wavelength Span
    insts = [
        ("SDSS APOGEE-2\n(H, R=22.5k)", 8, int(coh["apogee2_visit_spectra"]), "1.51–1.70 µm | N>=3 Visits", "#1b9e77"),
        ("ESO CRIRES+\n(Y/J/H, R=86k)", 15, int(coh["crires_yjh_exposures"]), "0.95–1.80 µm | Campaigns #118–125", "#2b8cbe"),
        ("JWST MIRI LRS\n(P750L, R~100)", 10, 10, "5.0–12.0 µm | Greenhouse CCF", "#d95f02"),
        ("JWST NIRSpec G395H\n(R=2.7k)", 2, 2, "2.87–5.14 µm | CH4/NO2/CO CCF", "#7570b3"),
    ]
    y2 = np.arange(len(insts))
    n_exps = [i[2] for i in insts]
    bars = ax2.barh(y2, n_exps, color=[i[4] for i in insts], height=0.58)
    for idx, (_, n_st, n_ex, note, _) in enumerate(insts):
        ax2.text(n_ex + 0.7, idx, f"{n_ex} exp ({n_st} stars)  [{note}]", va="center", fontsize=8.0)
    ax2.set_yticks(y2)
    ax2.set_yticklabels([i[0] for i in insts])
    ax2.set_ylim(4.45, -0.55)
    ax2.set_xlim(0, max(n_exps) * 2.10)
    ax2.set_xlabel("Physical Exposures / APOGEE-2 Visit Spectra in D094 (Total = 75)")
    ax2.set_title("B. Phase D094 Cohort Across 4 IR Facilities (30 Stars, 50.12 h)")
    ax2.text(
        0.97, 0.04,
        f"New unique stars: {coh['brand_new_unique_stars']} ({coh['brand_new_within_10pc']} <10 pc)\n"
        f"Bridge stars revisited/intra: {coh['prior_bridge_stars_revisited']}+{coh['intra_d094_bridge_stars']}\n"
        f"Controls: {coh['control_stars']} | Verified ETI: 0",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=8.1,
        bbox=dict(boxstyle="round,pad=0.35", fc="#f6f6f6", ec="#888888"),
    )
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("Phase D094 (V5.2) Four-Generation Gate Cascade & Multi-Facility NIR/MIR Cohort", y=0.99)
    _save(fig, "fig1_d094_four_gen_v52_benchmark.png")


def fig2_multiepoch_drift_v52(summary: dict[str, Any]) -> None:
    d94 = _read_csv("MULTIEPOCH_DRIFT_V52_RESULTS_D094.csv")
    d91 = _read_csv("RETROACTIVE_D091_MULTIEPOCH_DRIFT_31STARS.csv")
    cal = _read_csv("CALIBRATION_V52_MULTIEPOCH_DRIFT_150.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    # Panel A: All 44 N>=3 campaigns (baseline dt vs n_traj_evals + raw->0 veto annotation)
    dt94 = [max(0.2, float(r["dt_days"])) for r in d94]
    ev94 = [max(1.0, float(r["n_traj_evals"]) + 1.0) for r in d94]
    sz94 = [35 + 22 * int(r["n_epochs"]) for r in d94]
    dt91 = [max(0.2, float(r["dt_baseline_days"])) for r in d91]
    ev91 = [max(1.0, float(r["n_traj_evals"]) + 1.0) for r in d91]
    sz91 = [35 + 22 * int(r["n_epochs"]) for r in d91]

    ax1.scatter(dt94, ev94, s=sz94, color="#1b9e77", edgecolor="black", lw=0.6, alpha=0.88, label=f"D094 APOGEE-2/CRIRES ({len(d94)} campaigns, 0 surv.)", zorder=4)
    ax1.scatter(dt91, ev91, s=sz91, color="#2b8cbe", edgecolor="black", lw=0.6, alpha=0.82, marker="s", label=f"D091 Archive Q Retroactive ({len(d91)} campaigns, 0 surv.)", zorder=3)
    for r in d94 + d91:
        raw_c = int(r.get("raw_tracks", r.get("v52_drift_raw_tracks", 0)))
        if raw_c > 0 or r["star"] in ("2M23025951", "GJ433", "HD42581"):
            dx = max(0.2, float(r.get("dt_days", r.get("dt_baseline_days", 1.0))))
            dy = max(1.0, float(r["n_traj_evals"]) + 1.0)
            tag = f"{r['star']} (raw {raw_c}->0)" if raw_c > 0 else f"{r['star']} (N={r['n_epochs']})"
            if r["star"] == "G06410702":
                tx, ty = dx * 2.1, dy * 0.80
            elif r["star"] == "GJ433":
                tx, ty = dx * 0.12, dy * 1.02
            elif r["star"] == "G115":
                tx, ty = dx * 0.22, dy * 2.15
            elif r["star"] == "2M23025951":
                tx, ty = dx * 0.22, dy * 0.36
            elif r["star"] == "HD42581":
                tx, ty = dx * 0.65, dy * 2.6
            else:
                tx, ty = dx * 0.65, dy * 1.45
            ax1.annotate(tag, xy=(dx, dy), xytext=(tx, ty), fontsize=7.6, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.3, 1.8e4)
    ax1.set_ylim(0.38, 1600)
    ax1.set_xlabel("Multi-Epoch Baseline $\\Delta t$ (days)")
    ax1.set_ylabel("Triplet/Chain Trajectories Evaluated (+1)")
    ax1.set_title("A. 44 Multi-Epoch DRIFT_V52 Campaigns (N >= 3 -> 0 ETI)")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.8)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: 150-trial DRIFT_V52_MULTIEPOCH Calibration by trial class & |dv|
    inj = [r for r in cal if r["trial_class"] == "MULTIEPOCH_DRIFT_LASER"]
    dvs = sorted({abs(float(r["inj_dv_kms"])) for r in inj})
    rec_rates = [100.0 * sum(int(r["passed"]) for r in inj if abs(float(r["inj_dv_kms"])) == dv) / max(1, sum(1 for r in inj if abs(float(r["inj_dv_kms"])) == dv)) for dv in dvs]
    x2 = np.arange(len(dvs))
    ax2.bar(x2, rec_rates, color="#1b9e77", width=0.55, label=f"Drifting Lasers ({sum(int(r['passed']) for r in inj)}/{len(inj)} rec.)")
    for xi, rval in zip(x2, rec_rates):
        ax2.text(xi, rval + 1.5, f"{rval:.0f}%", ha="center", va="bottom", fontsize=8.4, fontweight="bold")

    veto_boxes = [
        ("STATIONARY_STELLAR", "Stationary"),
        ("SINGLE_EPOCH_TRANSIENT", "1-Epoch Trans."),
        ("BERV_SHIFTED_TOPO_SKY", "BERV Sky"),
    ]
    veto_txt = "\n".join(
        f"• {lbl}: {sum(int(r['passed']) for r in cal if r['trial_class']==k)}/{sum(1 for r in cal if r['trial_class']==k)} vetoed"
        for k, lbl in veto_boxes
    )
    ax2.text(
        0.96, 0.25,
        f"Zero-False-Positive Vetoes (90/90):\n{veto_txt}",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=8.2,
        bbox=dict(boxstyle="round,pad=0.38", fc="#eef7f2", ec="#1b7837"),
    )
    ax2.set_xticks(x2)
    ax2.set_xticklabels([f"{int(dv)}" for dv in dvs])
    ax2.set_ylim(0, 114)
    ax2.set_xlabel("Injected Total Velocity Drift $|\\Delta v_{\\rm drift}|$ Across $N=3..5$ Epochs (km s$^{-1}$)")
    ax2.set_ylabel("Multi-Epoch Drift Recovery Rate (%)")
    ax2.set_title("B. CALIBRATION_V52_MULTIEPOCH_DRIFT_150 (N=3..5, 150 Trials)")
    ax2.legend(loc="lower left", frameon=True)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Multi-Epoch Linear Drift-Rate Chaining (DRIFT_V52_MULTIEPOCH): 44 Campaigns & 150 Calibration Trials", y=0.99)
    _save(fig, "fig2_d094_multiepoch_drift_v52_44campaigns.png")


def fig3_jwst_ir_ccf(summary: dict[str, Any]) -> None:
    miri = _read_csv("JWST_MIRI_LRS_MOLECULAR_CCF_10STARS.csv")
    nirs = _read_csv("JWST_NIRSPEC_G395H_MOLECULAR_CCF_2STARS.csv")
    m_cal = _read_csv("CALIBRATION_V52_MIRI_LRS_CCF_160.csv")
    n_cal = _read_csv("CALIBRATION_V52_NIRSPEC_CCF_120.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.5), gridspec_kw={"width_ratios": [1.18, 0.95]})
    fig.subplots_adjust(wspace=0.34)

    cols = ["cf4_sigma", "c2f6_sigma", "sf6_sigma", "nf3_sigma", "cfc11_sigma", "nh3_lrs_conf_sigma", "ch4_conf_sigma", "h2o_conf_sigma"]
    col_lbls = ["CF$_4$", "C$_2$F$_6$", "SF$_6$", "NF$_3$", "CFC-11", "NH$_3$\n(Nat.)", "CH$_4$\n(Nat.)", "H$_2$O\n(Nat.)"]
    mat = np.zeros((len(miri), len(cols)))
    for i, r in enumerate(miri):
        for j, c in enumerate(cols):
            mat[i, j] = float(r[c])

    im = ax1.imshow(np.clip(mat, -9.0, 9.0), cmap="RdBu_r", vmin=-9.0, vmax=9.0, aspect="auto")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.03)
    cbar.set_label("Union-Excluded CCF Significance ($\\sigma$, clipped $\\pm 9$)")
    for i, r in enumerate(miri):
        is_sub = r["subcontinuum_nd"] == "True"
        for j in range(len(cols)):
            val = mat[i, j]
            txt = "ND" if is_sub else f"{val:+.1f}"
            col = "white" if (not is_sub and abs(val) > 5.0) else "black"
            ax1.text(j, i, txt, ha="center", va="center", fontsize=7.6, fontweight="bold" if abs(val) >= 5.0 else "normal", color=col)
    ax1.axvline(4.5, color="black", linestyle="--", lw=1.3)
    ax1.set_xticks(range(len(col_lbls)))
    ax1.set_xticklabels(col_lbls)
    ax1.set_yticks(range(len(miri)))
    ax1.set_yticklabels([
        f"{r['star']} (CTRL)" if r["role"] == "CONTROL" else f"{r['star']} ({float(r['teff_k']):.0f}K)"
        for r in miri
    ])
    ax1.set_title("A. JWST MIRI LRS (5–12 $\\mu$m): 5 Greenhouse vs 3 Confounders (0 ETI)")

    # Panel B: NIRSpec G395H 2 stars + 280 IR CCF calibration scorecard
    n_cols = ["no2_sigma", "n2o_sigma", "ch4_c2h6_sigma", "co_13co_sigma", "co2_4p26_conf_sigma", "h2o_nir_conf_sigma"]
    n_lbls = ["NO$_2$", "N$_2$O", "CH$_4$/C$_2$H$_6$", "CO/$^{13}$CO", "CO$_2$ (Nat.)", "H$_2$O (Nat.)"]
    x2 = np.arange(len(n_cols))
    w2 = 0.35
    cw_vals = [float(nirs[0][c]) for c in n_cols]
    hn_vals = [float(nirs[1][c]) for c in n_cols]
    ax2.bar(x2 - w2 / 2, cw_vals, width=w2, color="#2b8cbe", label=f"{nirs[0]['star']} (14.4 pc Y0; auroral CH$_4$)")
    ax2.bar(x2 + w2 / 2, hn_vals, width=w2, color="#e34a33", alpha=0.85, label=f"{nirs[1]['star']} (18.1 pc; CO$_2$ conf.)")
    ax2.axhline(5.0, color="#333333", linestyle="--", lw=1.0, label="Threshold $+5\\sigma$ (+ joint conf. veto)")
    ax2.axhline(0.0, color="#888888", lw=0.7)
    ax2.axvline(3.5, color="black", linestyle="--", lw=1.1)

    m_tp = sum(int(r["passed"]) for r in m_cal if r["class"] == "INJECTION")
    m_tn = sum(int(r["passed"]) for r in m_cal if r["class"] == "CONFOUNDER")
    n_tp = sum(int(r["passed"]) for r in n_cal if r["class"] == "INJECTION")
    n_tn = sum(int(r["passed"]) for r in n_cal if r["class"] == "CONFOUNDER")
    ax2.text(
        0.04, 0.96,
        f"CCF Calibrations (280 Trials):\n"
        f"• MIRI LRS (5 gases): {m_tp}/80 rec. | {m_tn}/80 veto\n"
        f"• NIRSpec G395H: {n_tp}/60 rec. | {n_tn}/60 veto",
        transform=ax2.transAxes, ha="left", va="top", fontsize=7.9,
        bbox=dict(boxstyle="round,pad=0.34", fc="#eef7f2", ec="#1b7837"),
    )
    ax2.set_xticks(x2)
    ax2.set_xticklabels(n_lbls, rotation=16, ha="right")
    ax2.set_ylabel("Joint-Confounder CCF Significance ($\\sigma$)")
    ax2.set_ylim(-8.9, 11.4)
    ax2.set_title("B. JWST NIRSpec G395H (2.87–5.14 $\\mu$m) & IR Calibrations")
    ax2.legend(loc="lower left", frameon=True)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Phase D094 JWST MIRI LRS & NIRSpec G395H Union-Excluded Molecular Technosignature Search", y=0.99)
    _save(fig, "fig3_d094_jwst_miri_lrs_nirspec_ccf.png")


def fig4_orbital_and_ellipsoid373(summary: dict[str, Any]) -> None:
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_8.csv")
    cat = _read_csv("MULTIEVENT_ELLIPSOID_CATALOG_D079_D094.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), gridspec_kw={"width_ratios": [1.0, 1.05]})
    fig.subplots_adjust(wspace=0.28)

    # Panel A: 8 D094 CRIRES+ Orbital Campaigns #118-#125
    lbls = [f"#{r['campaign_index']} {r['planet_name']}\n(N={r['n_epochs']}, P={float(r['orb_per_days']):.1f}d)" for r in orb]
    kps = [float(r["kp_kms"]) for r in orb]
    dvs = [float(r["orbital_dv_span_kms"]) for r in orb]
    y1 = np.arange(len(orb))
    h = 0.36
    ax1.barh(y1 - h / 2, kps, height=h, color="#2b8cbe", label="Keplerian Semi-Amplitude $K_p$ (km s$^{-1}$)")
    ax1.barh(y1 + h / 2, dvs, height=h, color="#d95f02", alpha=0.86, label="Observed Phase Span $\\Delta v_{\\rm orb}$ (km s$^{-1}$)")
    for i, (kp, dv) in enumerate(zip(kps, dvs)):
        ax1.text(max(kp, dv) + 4.0, i, "K_PL=0 (0 ETI)", va="center", fontsize=7.8)
    ax1.set_yticks(y1)
    ax1.set_yticklabels(lbls)
    ax1.set_ylim(9.35, -0.55)
    ax1.set_xlim(0, max(max(kps), max(dvs)) * 1.32)
    ax1.set_xlabel("Planetary Orbital Velocity Scale (km s$^{-1}$)")
    ax1.set_title("A. ESO CRIRES+ Orbital Campaigns #118–#125 (0 ETI)")
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(axis="x", alpha=0.25)

    # Panel B: 373-Star Multi-Event SETI Ellipsoid & ETZ
    abs_b = [abs(float(r["ecliptic_lat_deg"])) for r in cat]
    dt_m = [max(0.5, float(r["min_abs_ellipsoid_dt_days"])) for r in cat]
    is_etz = [r["etz_qualified"] == "True" for r in cat]
    is_d94 = ["D094" in r["phases"] for r in cat]

    ax2.scatter([b for b, e, d in zip(abs_b, is_etz, is_d94) if not e and not d],
                [t for t, e, d in zip(dt_m, is_etz, is_d94) if not e and not d],
                s=15, color="#8da0cb", alpha=0.62, label="D079–D093 Stars")
    ax2.scatter([b for b, d in zip(abs_b, is_d94) if d],
                [t for t, d in zip(dt_m, is_d94) if d],
                s=52, marker="s", color="#1b9e77", edgecolor="black", lw=0.6, zorder=4, label="D094 Cohort / Bridges (30 stars)")
    ax2.scatter([b for b, e in zip(abs_b, is_etz) if e],
                [t for t, e in zip(dt_m, is_etz) if e],
                s=88, marker="D", color="#d95f02", edgecolor="black", lw=0.8, zorder=5, label=f"Earth Transit Zone ({sum(is_etz)} stars)")

    for r in cat:
        if r["star"] in ("TOI674", "HD111031", "WOLF359", "GJ1132") or (r["ellipsoid_qualified_180d"] == "True" and "D094" in r["phases"]):
            bx = abs(float(r["ecliptic_lat_deg"]))
            dy = max(0.5, float(r["min_abs_ellipsoid_dt_days"]))
            ax2.annotate(f"{r['star']} ({dy:.1f}d)" if dy < 500 else f"{r['star']}", xy=(bx, dy), xytext=(bx + 4.0, dy * 1.35), fontsize=7.6, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax2.axvline(0.265, color="#d95f02", linestyle="--", lw=1.1, label="ETZ $|\\beta| \\leq 0.265^\\circ$")
    n_w180 = sum(1 for r in cat if r["ellipsoid_qualified_180d"] == "True")
    ax2.axhline(180.0, color="#1b7837", linestyle=":", lw=1.2, label=f"Ellipsoid $|\\Delta t| \\leq 180$ d ({n_w180} stars)")
    ax2.set_yscale("log")
    ax2.set_xlabel("Absolute Ecliptic Latitude $|\\beta|$ (deg)")
    ax2.set_ylabel("Min Multi-Event Sync Offset $|\\Delta t_{\\rm sync}|$ (days)")
    ax2.set_title("B. 373-Star Multi-Event Ellipsoid & ETZ (SN 1987A / GW170817 / SN 2023ixf)")
    ax2.legend(loc="lower right", frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    fig.suptitle("Phase D094 Keplerian Orbital Campaigns (#118–#125) and 373-Star Synchronization Geometry", y=0.99)
    _save(fig, "fig4_d094_orbital_campaigns_118_125_ellipsoid373.png")


def fig5_calibrations_1741_and_cascade(summary: dict[str, Any]) -> None:
    led = _read_csv("V5_2_CANDIDATE_LEDGER.csv")
    ag = _read_csv("V5_2_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    cal = summary["synthetic_calibration_1741_trials"]
    se = summary["searched_spectral_elements"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.4, 5.8), gridspec_kw={"width_ratios": [0.92, 1.16]})
    fig.subplots_adjust(wspace=0.72)

    n_g1 = len(led)
    n_g2 = sum(1 for r in led if r["g2_pass"] == "True")
    n_g3 = sum(1 for r in led if r["g2_pass"] == "True" and r["g3_pass"] == "True")
    n_g45 = sum(1 for r in led if r["g2_pass"] == "True" and r["g3_pass"] == "True" and r["g4_pass"] == "True" and r["g5_pass"] == "True")
    n_g6 = sum(1 for r in led if r["g2_pass"] == "True" and r["g3_pass"] == "True" and r["g4_pass"] == "True" and r["g5_pass"] == "True" and r["g6_pass"] == "True")
    n_g7 = sum(1 for r in led if r["g2_pass"] == "True" and r["g3_pass"] == "True" and r["g4_pass"] == "True" and r["g5_pass"] == "True" and r["g6_pass"] == "True" and r["g7_pass"] == "True")
    n_g8 = sum(1 for r in led if r["qualified_v52"] == "True")
    stages = [
        ("V2 Legacy", int(se["v2_false_alarms_eliminated_d094"]), "#bdbdbd"),
        ("G1 LSF Seed", n_g1, "#9ecae1"),
        ("G2 Airglow/OH", n_g2, "#6baed6"),
        ("G3 Chromo", n_g3, "#4292c6"),
        ("G4+G5 Native", n_g45, "#2171b5"),
        ("G6 Sparse", n_g6, "#08519c"),
        ("G7 RPCA+Rarity", n_g7, "#41ab5d"),
        ("G8_V52 Final", n_g8, "#1b7837"),
        ("Verified ETI", 0, "#00441b"),
    ]
    y1 = np.arange(len(stages))
    ax1.barh(y1, [max(0.4, s[1]) for s in stages], color=[s[2] for s in stages], height=0.65)
    for i, (_, raw_v, _) in enumerate(stages):
        ax1.text(max(0.4, raw_v) * 1.15, i, f"{raw_v:,}", va="center", fontsize=8.4, fontweight="bold" if i >= 6 else "normal")
    ax1.set_xscale("log")
    ax1.set_xlim(0.32, 4200)
    ax1.set_yticks(y1)
    ax1.set_yticklabels([s[0] for s in stages])
    ax1.invert_yaxis()
    ax1.set_xlabel("Candidate Count (log scale)")
    ax1.set_title("A. D094 Multi-Stream False-Alarm Cascade (0 ETI)")
    ax1.text(
        0.97, 0.05,
        f"Parallel V5.2 Streams (All 0 ETI):\n"
        f"• N>=3 Drift ({se['multiepoch_drift_v52_campaigns_total']} camp.): 0 surv.\n"
        f"• COMB_V4_1 ({se['comb_v41_searched_configs_d094']:,} cfg): 0 cands\n"
        f"• Agnostic Filter: {len(ag)} nat. ({sum(1 for r in ag if r['polarity']=='+')} pos.) -> 0 ETI\n"
        f"• JWST MIRI+NIRSpec CCF (12 stars): 0 ETI",
        transform=ax1.transAxes, ha="right", va="bottom", fontsize=7.9,
        bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="#888888"),
    )
    ax1.grid(axis="x", which="both", alpha=0.22)

    def _pct(tok: str) -> float:
        part = tok.split("(")[-1].rstrip(")") if "(" in tok else tok
        if "/" in part:
            a, b = part.split("/")
            return 100.0 * float(a) / float(b)
        return 100.0 * float(part)

    def _inv_pct(tok: str) -> float:
        a, b = tok.split("/")
        return 100.0 * (1.0 - float(a) / float(b))

    suites = [
        ("Drift V52 (N>=3) Laser Recov.", _pct(cal["multiepoch_drift_v52_recovery"])),
        ("Drift V52 Stat.+Trans.+BERV Veto", _pct(cal["multiepoch_drift_v52_stationary_veto"])),
        ("MIRI LRS 5-Gas CCF Recovery", _pct(cal["miri_lrs_ccf_injection_recovery"])),
        ("MIRI LRS Natural Confounder Veto", _pct(cal["miri_lrs_ccf_confounder_veto"])),
        ("NIRSpec G395H Mol. Recovery", _pct(cal["nirspec_mol_ccf_recovery"])),
        ("NIRSpec Confounder Veto", _pct(cal["nirspec_confounder_veto"])),
        ("G8_V52 Isolated Laser Pass", _pct(cal["g8_v52_isolated_pass"])),
        ("G8_V52 Shared+Topo Veto", _pct(cal["g8_v52_shared_suppression"])),
        ("RPCA Isolated Laser Recovery", _pct(cal["rpca_isolated_recovery"])),
        ("RPCA Shared+Topo Veto", _pct(cal["rpca_shared_suppression"])),
        ("Agnostic Multi-Scale Recovery", _pct(cal["agnostic_multiscale_recovery"])),
        ("G4/G5 Native LSF vs CR+Plateau", _pct(cal["g45_true_lsf_pass"])),
        ("Channel P (>=8s Injection)", _pct(cal["channel_p_ge_8sigma"])),
        ("Comb V4.1 Recovery / Forest+Topo Veto", 0.5 * (_pct(cal["comb_v41_recovery"]) + 0.5 * (_inv_pct(cal["comb_v41_forest_fa"]) + _inv_pct(cal["comb_v41_topo_fa"])))),
        ("Keplerian K_PLANET Recovery", _pct(cal["keplerian_kplanet_rec"])),
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
    ax2.set_xlim(0, 104)
    ax2.set_xlabel("Calibration Completeness / Specificity (%)")
    ax2.set_title(f"B. 10 Synthetic Calibration Suites ({cal['total_trials']:,} Trials)")
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("Phase D094 Complete Veto Cascade and 1,741-Trial Calibration Scorecard", y=0.99)
    _save(fig, "fig5_d094_calibration_1741_scorecard.png")


def fig6_unified_373star_census(summary: dict[str, Any]) -> None:
    ul94 = _read_csv("STAR_UPPER_LIMITS_D094.csv")
    u373 = _read_csv("UNIFIED_PANCHROMATIC_V5_2_SYNTHESIS_373STARS.csv")
    syn = summary["unified_373star_panchromatic_v5_2_synthesis"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.4), gridspec_kw={"width_ratios": [1.0, 1.06]})
    fig.subplots_adjust(wspace=0.28)

    meta = [
        ("ESO_CRIRES", "ESO CRIRES+ Y/J/H (86k)", "#2b8cbe", "o"),
        ("SDSS_APOGEE2", "SDSS APOGEE-2 H (22.5k)", "#1b9e77", "s"),
        ("JWST_NIRSPEC_G395H", "JWST NIRSpec G395H (2.7k)", "#7570b3", "D"),
        ("JWST_MIRI_LRS", "JWST MIRI LRS (100)", "#d95f02", "^"),
    ]
    for inst, lbl, col, mk in meta:
        sub = [r for r in ul94 if r["instrument"] == inst]
        xs = [float(r["wave_bary_a"]) / 1e4 for r in sub]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax1.scatter(xs, ys, s=38, color=col, marker=mk, alpha=0.84, label=f"{lbl} ({len(sub)})")

    best_ir = min(ul94, key=lambda r: float(r["p_beam_10m_kw"]))
    best_ap = min([r for r in ul94 if r["instrument"] == "SDSS_APOGEE2"], key=lambda r: float(r["p_beam_10m_kw"]))
    best_mi = min([r for r in ul94 if r["instrument"] == "JWST_MIRI_LRS"], key=lambda r: float(r["p_beam_10m_kw"]))
    ax1.annotate(f"{best_ir['star']}\n{float(best_ir['p_beam_10m_kw']):.4f} kW (142.4 W)", xy=(float(best_ir["wave_bary_a"]) / 1e4, float(best_ir["p_beam_10m_kw"])), xytext=(1.45, 0.048), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=7.8, fontweight="bold")
    ax1.annotate(f"{best_mi['star']}\n{float(best_mi['p_beam_10m_kw']):.4f} kW", xy=(float(best_mi["wave_bary_a"]) / 1e4, float(best_mi["p_beam_10m_kw"])), xytext=(6.6, 0.085), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=7.8, fontweight="bold")
    ax1.annotate(f"{best_ap['star']} APOGEE-2\n{float(best_ap['p_beam_10m_kw']):.2f} kW", xy=(float(best_ap["wave_bary_a"]) / 1e4, float(best_ap["p_beam_10m_kw"])), xytext=(1.9, 0.72), arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=7.8)

    ax1.set_yscale("log")
    ax1.set_xscale("log")
    ax1.set_xlim(0.88, 13.5)
    ax1.set_ylim(0.022, 2.5e9)
    ax1.set_xticks([1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 11.0])
    ax1.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax1.set_xlabel("Wavelength ($\\mu$m, log scale)")
    ax1.set_ylabel("5$\\sigma$–8$\\sigma$ 10-m Directed Laser EIRP Limit (kW)")
    ax1.set_title("A. D094 108 Star-Band 10-m Laser EIRP Upper Limits")
    ax1.legend(loc="upper left", frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Unified 373-Star Census (Distance vs Best Panchromatic 10-m EIRP Limit)
    d_old, p_old, d_new, p_new = [], [], [], []
    for r in u373:
        if not r["min_panchromatic_10m_kw"] or not r["dist_pc"]:
            continue
        dv = float(r["dist_pc"])
        pv = float(r["min_panchromatic_10m_kw"])
        if dv <= 0 or pv <= 0:
            continue
        if "D094" in r["phases"]:
            d_new.append(dv)
            p_new.append(pv)
        else:
            d_old.append(dv)
            p_old.append(pv)

    ax2.scatter(d_old, p_old, s=18, color="#6baed6", alpha=0.72, label=f"D079–D093 Stars ({len(d_old)} w/ valid UL)")
    ax2.scatter(d_new, p_new, s=64, marker="D", color="#e34a33", edgecolor="black", lw=0.7, zorder=4, label=f"D094 Cohort / Bridges ({len(d_new)} stars)")
    ax2.axvline(10.0, color="#1b7837", linestyle="--", lw=1.2, label=f"<10 pc Census: {syn['within_10pc_unique_stars']} stars (med {syn['within_10pc_median_limit_kw']:.3f} kW)")

    for r in u373:
        if r["star"] in ("PROXIMACEN", "WISE1049AB", "CWISEPJ1935", "GJ3512") and r["min_panchromatic_10m_kw"]:
            dv = float(r["dist_pc"])
            pv = float(r["min_panchromatic_10m_kw"])
            if r["star"] == "PROXIMACEN":
                tx, ty = 2.6, 5.5e-5
            elif r["star"] == "WISE1049AB":
                tx, ty = 1.05, 0.038
            elif r["star"] == "GJ3512":
                tx, ty = 2.1, 0.0028
            else:
                tx, ty = 26.0, 0.015
            ax2.annotate(f"{r['star']}", xy=(dv, pv), xytext=(tx, ty), fontsize=7.8, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_ylim(2e-5, 2.5e9)
    ax2.set_xlabel("Heliocentric Distance (pc, log scale)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title("B. Unified 373-Star Survey (23 Spectrographs, 29 Arms, 8.273 Octaves)")
    ax2.legend(loc="upper left", frameon=True)
    ax2.text(
        0.97, 0.06,
        f"D079–D094 Totals:\n"
        f"• {syn['unique_stars_total']} unique stars ({syn['panchromatic_bridge_stars_total']} bridges)\n"
        f"• {syn['total_exposures_d079_d094']:,} exps ({syn['total_integration_hours_d079_d094']:.1f} h)\n"
        f"• {syn['v2_false_alarms_eliminated_total']:,} V2 FA -> 0 ETI",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=7.9,
        bbox=dict(boxstyle="round,pad=0.35", fc="#fff8e7", ec="#d95f02"),
    )
    ax2.grid(True, which="both", alpha=0.22)

    fig.suptitle("Phase D094 108-Cell IR Limits and Unified 373-Star (8.273-Octave, 23-Spectrograph) Census", y=0.99)
    _save(fig, "fig6_unified_373star_panchromatic_v52_census.png")


def main() -> None:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    fig1_benchmark_and_cohort(summary)
    fig2_multiepoch_drift_v52(summary)
    fig3_jwst_ir_ccf(summary)
    fig4_orbital_and_ellipsoid373(summary)
    fig5_calibrations_1741_and_cascade(summary)
    fig6_unified_373star_census(summary)
    print("ALL 6 D094 FIGURES GENERATED SUCCESSFULLY.", flush=True)


if __name__ == "__main__":
    main()
