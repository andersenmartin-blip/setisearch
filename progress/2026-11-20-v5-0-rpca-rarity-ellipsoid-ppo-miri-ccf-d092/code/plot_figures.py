#!/usr/bin/env python3
"""
Phase D092 Publication Figure Generator (`V5.0`):
Generates 6 multi-panel publication figures (>= 220 DPI) in `figures/`.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RES = WS / "results"
FIGS = WS / "figures"

plt.rcParams.update({
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
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _save(fig: plt.Figure, name: str, dpi: int = 240) -> None:
    out = FIGS / name
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out.name} ({out.stat().st_size:,} B)", flush=True)


def fig1_rpca_and_d091_regression(summary: dict[str, Any]) -> None:
    retro = _read_csv("RETROACTIVE_D091_RPCA_REGRESSION.csv")
    ledger = _read_csv("V5_0_CANDIDATE_LEDGER.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), constrained_layout=True)

    # Panel A: D091 Retroactive RPCA+G7 suppression (2,362 -> 28)
    stars = ["SCR1845", "LP94420", "GJ1128", "HD213885", "Others (23 stars)"]
    top_set = {"SCR1845", "LP94420", "GJ1128", "HD213885"}
    before = [
        sum(1 for r in retro if r["star"] == s) if s != "Others (23 stars)" else sum(1 for r in retro if r["star"] not in top_set)
        for s in stars
    ]
    after = [
        sum(1 for r in retro if r["star"] == s and r["g7_pass"] == "True") if s != "Others (23 stars)" else sum(1 for r in retro if r["star"] not in top_set and r["g7_pass"] == "True")
        for s in stars
    ]
    x = np.arange(len(stars))
    w = 0.36
    b1 = ax1.bar(x - w / 2, [max(0.5, v) for v in before], w, color="#4C78A8", label="D091 V4.2 Qualified (Total = 2,362)")
    b2 = ax1.bar(x + w / 2, [max(0.5, v) for v in after], w, color="#E45756", label="V5.0 RPCA + G7 Survivors (Total = 28; 98.8% suppressed)")
    ax1.set_yscale("log")
    ax1.set_ylim(0.4, 4500)
    ax1.set_xticks(x)
    ax1.set_xticklabels(stars, rotation=14, ha="right")
    ax1.set_ylabel("Qualified Single-Line Triggers (log scale)")
    ax1.set_title("(a) Retroactive D091 RPCA + Rarity Suppression (2,362 -> 28)")
    ax1.grid(axis="y", alpha=0.25)
    for rect, val in zip(b1, before):
        ax1.text(rect.get_x() + rect.get_width() / 2, max(0.6, val) * 1.15, f"{val}", ha="center", va="bottom", fontsize=8, color="#264b73", fontweight="bold")
    for rect, val in zip(b2, after):
        ax1.text(rect.get_x() + rect.get_width() / 2, max(0.65, val) * 1.15, f"{val}", ha="center", va="bottom", fontsize=8, color="#9e2a29", fontweight="bold")
    ax1.legend(loc="upper right", frameon=True, framealpha=0.92)

    # Panel B: D092 V4.2 pre-G7 candidates (815) in (z_rpca, rarity_score) plane
    v42 = [r for r in ledger if r["qualified_v42_laser"] == "True" and r["z_rpca"] != ""]
    zv = np.array([max(0.2, float(r["z_rpca"])) for r in v42])
    rv = np.array([float(r["rarity_score"]) for r in v42])
    ok = np.array([r["qualified_v50_laser"] == "True" for r in v42])
    ax2.scatter(zv[~ok], rv[~ok], s=14, alpha=0.50, color="#7F8C8D", label=f"V5.0 G7 Vetoed from V4.2 (n={int((~ok).sum())})")
    ax2.scatter(zv[ok], rv[ok], s=22, alpha=0.82, color="#D62728", edgecolor="black", linewidth=0.35, label=f"V5.0 G7 Auto-Qualified (n={int(ok.sum())}; 0 ETI)")
    ax2.axvline(6.0, color="#1F77B4", linestyle="--", linewidth=1.2)
    ax2.axhline(0.65, color="#1F77B4", linestyle="--", linewidth=1.2)
    ax2.axvspan(6.0, 400.0, ymin=0.65 / 1.08, ymax=1.0, color="#2CA02C", alpha=0.07)
    ax2.text(7.2, 0.96, "G7 Pass Box\nz_rpca >= 6.0 & rarity >= 0.65", fontsize=8.5, color="#196F3D", fontweight="bold", va="top")
    ax2.set_xscale("log")
    ax2.set_xlim(0.25, 420.0)
    ax2.set_ylim(-0.04, 1.08)
    ax2.set_xlabel("RPCA + Teff-LOSO Residual SNR (|z_rpca|, log scale)")
    ax2.set_ylabel("Rarity Score (1 - f_rest)(1 - f_topo)")
    ax2.set_title("(b) D092 Gate G7_V50 Decision Plane Across 815 V4.2 Survivors")
    ax2.grid(alpha=0.25)
    ax2.legend(loc="lower left", frameon=True, framealpha=0.92)

    fig.suptitle("Phase D092 V5.0 Engine 1 & 2: Unsupervised Masked RPCA + Teff-LOSO & Cross-Star Rarity Filtering", fontsize=11.5)
    _save(fig, "fig1_d092_rpca_decomposition_and_d091_regression.png")


def fig2_geometric_sync() -> None:
    geom = _read_csv("GEOMETRIC_SYNC_TRACKS_D092.csv")
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_9.csv")

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.0, 4.9), constrained_layout=True)

    # (a) Ecliptic latitude ETZ track
    geom_sorted = sorted(geom, key=lambda r: abs(float(r["ecliptic_lat_deg"])))
    ys = np.arange(len(geom_sorted))
    abeta = [max(0.005, abs(float(r["ecliptic_lat_deg"]))) for r in geom_sorted]
    etz_ok = [r["etz_qualified"] == "True" for r in geom_sorted]
    cols1 = ["#1B9E77" if ok else "#95A5A6" for ok in etz_ok]
    ax1.barh(ys, abeta, color=cols1, height=0.72)
    ax1.axvline(0.264, color="#D95F02", linestyle="--", linewidth=1.4, label="ETZ |beta| <= 0.264 deg (n=5)")
    ax1.set_xscale("log")
    ax1.set_xlim(0.004, 120.0)
    ax1.set_yticks(ys)
    ax1.set_yticklabels([r["star"] for r in geom_sorted], fontsize=7.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Abs. Ecliptic Latitude |beta| (deg, log)")
    ax1.set_title("(a) Earth Transit Zone (ETZ) Targets")
    ax1.grid(axis="x", alpha=0.25)
    ax1.legend(loc="lower right", frameon=True, fontsize=7.5)

    # (b) SN 1987A SETI Ellipsoid
    geom_ell = sorted(geom, key=lambda r: float(r["min_abs_sn1987a_dt_days"]))
    ys2 = np.arange(len(geom_ell))
    dts = [max(1.0, float(r["min_abs_sn1987a_dt_days"])) for r in geom_ell]
    ell_ok = [r["ellipsoid_qualified"] == "True" for r in geom_ell]
    cols2 = ["#7570B3" if ok else "#BDC3C7" for ok in ell_ok]
    ax2.barh(ys2, dts, color=cols2, height=0.72)
    ax2.axvline(180.0, color="#E7298A", linestyle="--", linewidth=1.4, label="Ellipsoid |dt| <= 180 d (n=6 <10pc)")
    ax2.set_xscale("log")
    ax2.set_xlim(8.0, 80000.0)
    ax2.set_yticks(ys2)
    ax2.set_yticklabels([f"{r['star']} ({float(r['dist_pc']):.1f}pc)" for r in geom_ell], fontsize=6.6)
    ax2.invert_yaxis()
    ax2.set_xlabel("Min |MJD_obs - MJD_SN1987A| (days, log)")
    ax2.set_title("(b) SN 1987A SETI Ellipsoid Timing")
    ax2.grid(axis="x", alpha=0.25)
    ax2.legend(loc="lower right", frameon=True, fontsize=7.5)

    # (c) 9 Multi-Planet PPO Orbital Campaigns (#101-#109)
    cnames = [f"#{r['campaign_number']} {r['star']} ({r['n_planets_in_system']}pl)" for r in orb]
    dvs = [float(r["orbital_dv_span_kms"]) for r in orb]
    ppos = [max(1e-5, float(r["min_ppo_align_score"])) for r in orb]
    insts = [r["instrument"] for r in orb]
    imap = {"ESO_HARPS": "#1F77B4", "ESO_FEROS": "#FF7F0E", "ESO_CRIRES": "#2CA02C"}
    y3 = np.arange(len(orb))
    ax3.barh(y3, dvs, color=[imap[i] for i in insts], height=0.62)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(cnames, fontsize=8.0)
    ax3.invert_yaxis()
    ax3.set_xlim(0, 395.0)
    ax3.set_xlabel("Orbital RV Span Delta_v (km/s)")
    ax3.set_title("(c) 9 PPO Campaigns (#101-#109; 0 K_PLANET / 0 ETI)")
    ax3.grid(axis="x", alpha=0.25)
    for yi, dv, pp in zip(y3, dvs, ppos):
        lbl = f"{dv:.1f} km/s (PPO={pp:.4f})" if pp < 0.1 else f"{dv:.1f} km/s (transit)"
        ax3.text(dv + 4.5, yi, lbl, va="center", fontsize=7.2, color="#222222")
    from matplotlib.patches import Patch
    ax3.legend(handles=[Patch(color=imap[k], label=k.replace("ESO_", "")) for k in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES")], loc="lower right", frameon=True, fontsize=7.5)

    fig.suptitle("Phase D092 Geometric Synchronization Tracks: ETZ (5 Stars), SN 1987A Ellipsoid (6 <10pc Stars), and 9 PPO Multi-Planet Systems", fontsize=11.3)
    _save(fig, "fig2_d092_geometric_sync_etz_ellipsoid_ppo.png")


def _parse_pct(s: str) -> float:
    if "(" in s:
        return 100.0 * float(s.split("(")[1].rstrip(")"))
    a, b = s.split("/")
    return 100.0 * float(a) / float(b)


def fig3_agnostic_and_calibration(summary: dict[str, Any]) -> None:
    cal = summary["synthetic_calibration_1351_trials"]
    ag = _read_csv("V5_0_AGNOSTIC_MULTISCALE_SURVIVORS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.6), constrained_layout=True)

    metrics = [
        ("RPCA Isolated (>=6s)", _parse_pct(cal["rpca_isolated_laser_recovery"]), "#1F77B4"),
        ("RPCA Shared Rej.", _parse_pct(cal["rpca_shared_leak_suppression"]), "#1F77B4"),
        ("RPCA Topo Rej.", _parse_pct(cal["rpca_topo_repeat_suppression"]), "#1F77B4"),
        ("Agnostic Multi-Scale", _parse_pct(cal["agnostic_multiscale_recovery"]), "#9467BD"),
        ("MIRI Greenhouse Rec.", _parse_pct(cal["miri_greenhouse_recovery"]), "#8C564B"),
        ("MIRI Confounder Rej.", _parse_pct(cal["miri_confounder_veto"]), "#8C564B"),
        ("Ch.T >=8s Completeness", _parse_pct(cal["channel_t_ge_8sigma"]), "#2CA02C"),
        ("Ch.P >=8s Completeness", _parse_pct(cal["channel_p_ge_8sigma"]), "#2CA02C"),
        ("K_PLANET >=6.5s", _parse_pct(cal["keplerian_kplanet_ge_6p5sigma"]), "#2CA02C"),
        ("G4+G5 True / Artifact Rej.", _parse_pct(cal["g5_cosmic_hotpx_rejection"]), "#E377C2"),
        ("COMB V4.1 (>=3.8s)", _parse_pct(cal["comb_v41_6tooth_ge_3p8sigma_recovery"]), "#FF7F0E"),
        ("COMB V4.1 Forest/Topo Rej.", 100.0 - _parse_pct(cal["comb_v41_forest_false_alarm"]), "#FF7F0E"),
    ]
    y = np.arange(len(metrics))
    vals = [m[1] for m in metrics]
    cols = [m[2] for m in metrics]
    ax1.barh(y, vals, color=cols, height=0.66)
    ax1.axvline(90.0, color="#666666", linestyle=":", linewidth=1.0)
    ax1.set_xlim(0, 115.0)
    ax1.set_yticks(y)
    ax1.set_yticklabels([m[0] for m in metrics], fontsize=8.3)
    ax1.invert_yaxis()
    ax1.set_xlabel("Recovery / Rejection Accuracy (%) across 1,351 Trials")
    ax1.set_title("(a) V5.0 Prospective Synthetic Calibration Scorecard (7 Suites)")
    ax1.grid(axis="x", alpha=0.25)
    for yi, v in zip(y, vals):
        ax1.text(v + 1.2, yi, f"{v:.1f}%", va="center", fontsize=8.0, fontweight="bold")

    # (b) Agnostic multi-scale survivors
    kmap = {"gaussian": "o", "boxcar_drift": "s"}
    imap = {"ESO_HARPS": "#1F77B4", "ESO_FEROS": "#FF7F0E", "ESO_CRIRES": "#2CA02C"}
    for inst in ("ESO_HARPS", "ESO_FEROS", "ESO_CRIRES"):
        for kern in ("gaussian", "boxcar_drift"):
            sub = [r for r in ag if r["instrument"] == inst and r["kernel"] == kern]
            if not sub:
                continue
            ws = [float(r["wave_rest_a"]) / 1e4 for r in sub]
            zs = [float(r["z_multi"]) for r in sub]
            sz = [18 + 6 * float(r["scale_lsf"]) for r in sub]
            ax2.scatter(ws, zs, s=sz, marker=kmap[kern], color=imap[inst], alpha=0.80, edgecolor="black", linewidth=0.4,
                        label=f"{inst.replace('ESO_', '')} ({kern.replace('_drift', '')})")

    ax2.axhline(7.5, color="#D62728", linestyle="--", linewidth=1.0)
    ax2.axhline(-7.5, color="#D62728", linestyle="--", linewidth=1.0)
    ax2.axhline(0.0, color="#7F8C8D", linewidth=0.6)
    # Annotate top features without overlap or axis clipping
    tops = sorted(ag, key=lambda r: -abs(float(r["z_multi"])))[:5]
    offsets = [(-0.22, 6), (0.06, 22), (0.06, 2), (0.06, -15), (-0.23, -12)]
    for t, (dx, dy) in zip(tops[:5], offsets):
        wx = float(t["wave_rest_a"]) / 1e4
        zy = float(t["z_multi"])
        ax2.annotate(f"{t['star']} ({float(t['wave_rest_a']):.0f}A)", xy=(wx, zy),
                     xytext=(wx + dx, zy + dy), fontsize=7.4,
                     arrowprops=dict(arrowstyle="->", lw=0.7, color="#333333"))
    ax2.set_xlim(0.33, 1.15)
    ax2.set_ylim(-55, 168)
    ax2.set_xlabel("Stellar Rest Wavelength (um)")
    ax2.set_ylabel("Signed Multi-Scale Matched-Filter SNR (z_multi)")
    ax2.set_title("(b) Dual-Polarity Agnostic Matched Filter (107 Natural Survivors; 0 ETI)")
    ax2.grid(alpha=0.25)
    ax2.legend(loc="lower left", ncol=2, fontsize=7.4, frameon=True, framealpha=0.92)

    fig.suptitle("Phase D092 Calibration Benchmark (1,351 Synthetic Trials) and V5.0 Agnostic Multi-Scale Survey (14,274 Evaluations)", fontsize=11.3)
    _save(fig, "fig3_d092_agnostic_multiscale_and_calibration.png")


def fig4_miri_greenhouse_ccf() -> None:
    miri = _read_csv("MIRI_GREENHOUSE_CCF_D090_15TARGETS.csv")
    stars = sorted({r["star"] for r in miri})
    mols = ["CF4", "C2F6", "SF6", "NF3"]

    sig_mat = np.full((len(stars), len(mols)), np.nan)
    pass_mat = np.zeros((len(stars), len(mols)), dtype=bool)
    d5_mat = np.full((len(stars), len(mols)), np.nan)
    lookup = {(r["star"], r["molecule"]): r for r in miri}
    for i, s in enumerate(stars):
        for j, m in enumerate(mols):
            r = lookup[(s, m)]
            if r["covered"] == "True":
                sig_mat[i, j] = float(r["ccf_sigma_abs"])
                pass_mat[i, j] = r["passes_ccf"] == "True"
                if r["delta_min_5sigma"]:
                    d5_mat[i, j] = float(r["delta_min_5sigma"]) * 100.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 6.2), constrained_layout=True)

    masked = np.ma.masked_invalid(sig_mat)
    im = ax1.imshow(masked, cmap="RdBu_r", vmin=-18, vmax=18, aspect="auto")
    ax1.set_xticks(np.arange(len(mols)))
    ax1.set_xticklabels(["CF4\n(7.80/15.8um)", "C2F6\n(8.98/14.0um)", "SF6\n(10.55um)", "NF3\n(11.02um)"])
    ax1.set_yticks(np.arange(len(stars)))
    ylabels = [f"{s} {'(C)' if lookup[(s, 'C2F6')]['role']=='CONTROL' else ''}" for s in stars]
    ax1.set_yticklabels(ylabels, fontsize=8.3)
    for i in range(len(stars)):
        for j in range(len(mols)):
            v = sig_mat[i, j]
            if not np.isfinite(v):
                txt, col = "N/A", "#666666"
            else:
                star_flag = "*" if pass_mat[i, j] else ""
                txt = f"{v:+.1f}{star_flag}"
                col = "white" if abs(v) > 9.5 else "black"
            ax1.text(j, i, txt, ha="center", va="center", fontsize=7.6, color=col, fontweight="bold" if pass_mat[i, j] else "normal")
    cb = fig.colorbar(im, ax=ax1, shrink=0.86, pad=0.02)
    cb.set_label("Matched-Template CCF Significance (sigma)")
    ax1.set_title("(a) 15-Target JWST MIRI MRS Greenhouse Gas CCF (* = Disk/DOG Flag)")

    # (b) 5-sigma fractional band-depth sensitivity across all 15 targets
    x = np.arange(len(stars))
    mcols = {"CF4": "#1F77B4", "C2F6": "#D62728", "SF6": "#2CA02C", "NF3": "#FF7F0E"}
    for j, m in enumerate(mols):
        vals = d5_mat[:, j]
        ok = np.isfinite(vals)
        ax2.plot(x[ok], vals[ok], marker="o", markersize=5.0, linewidth=1.4, color=mcols[m], label=f"{m} (med {np.nanmedian(vals):.2f}%)")
    ax2.set_yscale("log")
    ax2.set_ylim(0.5, 220.0)
    ax2.set_xticks(x)
    ax2.set_xticklabels(stars, rotation=38, ha="right", fontsize=8.0)
    ax2.set_ylabel("5-sigma Fractional Absorption Depth Limit delta_min (%)")
    ax2.set_title("(b) 5-sigma Technosignature Sensitivity (0.07 um Edge-Trimmed MIRI)")
    ax2.grid(alpha=0.25)
    ax2.legend(loc="upper left", frameon=True, framealpha=0.92)

    fig.suptitle("Phase D092 V5.0 Engine 4: Retroactive JWST MIRI MRS CFC/SF6/NF3 CCF Search Across 15 Stars (60 Cells; 0 Verified ETI)", fontsize=11.3)
    _save(fig, "fig4_d092_miri_greenhouse_ccf_15targets.png")


def fig5_upper_limits_and_335stars(summary: dict[str, Any]) -> None:
    u335 = _read_csv("UNIFIED_PANCHROMATIC_V5_0_SYNTHESIS_335STARS.csv")
    br = _read_csv("PANCHROMATIC_BRIDGE_35STARS_V50.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.5), constrained_layout=True)

    # (a) 335 stars distance vs min_panchromatic_10m_kw
    prior_d, prior_p, d92_h_d, d92_h_p, d92_f_d, d92_f_p, d92_c_d, d92_c_p = [], [], [], [], [], [], [], []
    for r in u335:
        if not r["min_panchromatic_10m_kw"] or not r["dist_pc"]:
            continue
        d = float(r["dist_pc"])
        p = max(1e-5, float(r["min_panchromatic_10m_kw"]))
        ph = r["phases"]
        insts = r["instruments"]
        if "D092" in ph:
            if "ESO_CRIRES" in insts:
                d92_c_d.append(d); d92_c_p.append(p)
            elif "ESO_FEROS" in insts:
                d92_f_d.append(d); d92_f_p.append(p)
            else:
                d92_h_d.append(d); d92_h_p.append(p)
        else:
            prior_d.append(d); prior_p.append(p)

    ax1.scatter(prior_d, prior_p, s=16, alpha=0.45, color="#95A5A6", label=f"Prior D079-D091 Stars (n={len(prior_d)})")
    ax1.scatter(d92_h_d, d92_h_p, s=42, color="#1F77B4", edgecolor="black", linewidth=0.5, label=f"D092 HARPS (n={len(d92_h_d)}; best 0.52 kW)")
    ax1.scatter(d92_f_d, d92_f_p, s=42, color="#FF7F0E", edgecolor="black", linewidth=0.5, label=f"D092 FEROS (n={len(d92_f_d)}; best 0.50 kW)")
    ax1.scatter(d92_c_d, d92_c_p, s=55, marker="D", color="#2CA02C", edgecolor="black", linewidth=0.5, label=f"D092 CRIRES Y (n={len(d92_c_d)}; best 1.19 kW)")
    ax1.axvline(10.0, color="#D62728", linestyle="--", linewidth=1.2)
    med10 = float(summary["unified_335star_panchromatic_v5_0_synthesis"]["within_10pc_median_limit_kw"])
    ax1.axhline(med10, color="#8E44AD", linestyle=":", linewidth=1.3, label=f"<10 pc Median = {med10:.3f} kW (n=146)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0, 2200.0)
    ax1.set_ylim(4e-5, 4e6)
    ax1.set_xlabel("Distance d (pc, log scale)")
    ax1.set_ylabel("Best 8-sigma 10 m CW Transmitter EIRP Limit (kW)")
    ax1.set_title("(a) Unified 335-Star Survey Sensitivity (D079-D092; 146 <10 pc)")
    ax1.grid(alpha=0.25)
    ax1.legend(loc="lower right", fontsize=7.6, frameon=True, framealpha=0.92)

    # (b) Panchromatic SED bridge (highlight TRAPPIST1, K218, PROXIMACEN, BETPIC, LAWD37, 16CYGB)
    hi_stars = {
        "PROXIMACEN": ("#D62728", "Proxima Cen (0.097 W - 1.5 um)"),
        "TRAPPIST1": ("#2CA02C", "TRAPPIST-1 (+D092 CRIRES Y)"),
        "K218": ("#9467BD", "K2-18 (+D092 CRIRES Y)"),
        "BETPIC": ("#1F77B4", "beta Pic (0.092 - 23.5 um)"),
        "LAWD37": ("#FF7F0E", "LAWD 37 (0.36 - 23.5 um)"),
    }
    by_s = {}
    for r in br:
        by_s.setdefault(r["star"], []).append((float(r["wave_um"]), max(1e-5, float(r["p_beam_10m_kw"])), r["phase_id"]))
    for st, pts in by_s.items():
        if st in hi_stars:
            continue
        pts.sort()
        ax2.plot([p[0] for p in pts], [p[1] for p in pts], color="#D0D3D4", linewidth=0.75, alpha=0.55)
    for st, (col, lbl) in hi_stars.items():
        pts = sorted(by_s.get(st, []))
        if not pts:
            continue
        ax2.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", markersize=3.6, linewidth=1.6, color=col, label=lbl)
        d92_pts = [p for p in pts if p[2] == "D092"]
        if d92_pts:
            ax2.scatter([p[0] for p in d92_pts], [p[1] for p in d92_pts], s=65, marker="*", color="gold", edgecolor="black", linewidth=0.5, zorder=6)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.08, 30.0)
    ax2.set_ylim(5e-5, 2e5)
    ax2.set_xlabel("Wavelength (um, log scale)")
    ax2.set_ylabel("8-sigma 10 m EIRP Limit (kW)")
    ax2.set_title("(b) 37 Panchromatic Bridges (631 Cells; Stars = D092 CRIRES Y)")
    ax2.grid(alpha=0.25)
    ax2.legend(loc="upper left", fontsize=7.6, frameon=True, framealpha=0.92)

    fig.suptitle("Phase D092 Upper Limits & Unified 335-Star, 8.273-Octave Panchromatic Synthesis (D079-D092; 2,133 Exposures; 0 ETI)", fontsize=11.3)
    _save(fig, "fig5_d092_panchromatic_upper_limits_335stars.png")


def fig6_cascade_and_forensic(summary: dict[str, Any]) -> None:
    diag = json.loads((RES / "FORENSIC_D092_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    cas = diag["cascade"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 5.5), constrained_layout=True)

    # (a) False-alarm cascade log bar
    stages = [
        ("V2 Legacy", cas["v2_legacy_false_alarms"], "#95A5A6"),
        ("V4.2 G1", cas["v42_total_ledger_g1_candidates"], "#5D6D7E"),
        ("G2 Airglow", cas["v42_after_g2"], "#3498DB"),
        ("G3 Chromo", cas["v42_after_g3"], "#2E86C1"),
        ("G4 Profile", cas["v42_after_g4"], "#1F618D"),
        ("G5 Detector", cas["v42_pre_g6_passed_g1_to_g5"], "#8E44AD"),
        ("V4.2 G6", cas["v42_qualified_before_g7"], "#E67E22"),
        ("V5.0 G7", cas["v50_qualified_control"] + cas["v50_qualified_science"], "#D62728"),
        ("Verified ETI", 0, "#2CA02C"),
    ]
    x = np.arange(len(stages))
    vals_plot = [max(0.4, s[1]) for s in stages]
    bars = ax1.bar(x, vals_plot, color=[s[2] for s in stages], width=0.66)
    ax1.set_yscale("log")
    ax1.set_ylim(0.3, 45000)
    ax1.set_xticks(x)
    ax1.set_xticklabels([s[0] for s in stages], rotation=22, ha="right", fontsize=8.3)
    ax1.set_ylabel("Trigger / Survivor Count (log scale)")
    ax1.set_title("(a) D092 False-Alarm Rejection Cascade (15,147 -> 146 -> 0 ETI)")
    ax1.grid(axis="y", alpha=0.25)
    for b, (_, raw_v, _) in zip(bars, stages):
        ax1.text(b.get_x() + b.get_width() / 2, max(0.52, raw_v) * 1.15, f"{raw_v:,}", ha="center", va="bottom", fontsize=8.0, fontweight="bold")

    # (b) 4-stream forensic triage stacked breakdown
    st4 = diag["forensic_4stream_counts"]
    streams = [
        ("V5.0 G7 Singles\n(n=146)", st4["v50_g7_survivors"]),
        ("Agnostic Filter\n(n=107)", st4["agnostic_multiscale_survivors"]),
        ("COMB_V4_1\n(n=64)", st4["comb_v41_candidates"]),
        ("MIRI CCF Flagged\n(n=4/60)", st4["miri_greenhouse_flagged"]),
    ]
    cat_map = {
        "M_DWARF_FLARE_OR_MOLECULAR": "Cool M-dwarf / TiO / Molecular",
        "M_DWARF_MOLECULAR_OR_PSEUDOCONTINUUM": "Cool M-dwarf / TiO / Molecular",
        "FEROS_BLUE_UV_ROLLOFF_OR_ORDER_EDGE": "FEROS Blue UV Roll-off / Congestion",
        "FEROS_BLUE_UV_ROLLOFF": "FEROS Blue UV Roll-off / Congestion",
        "FEROS_BLUE_UV_LINE_CONGESTION": "FEROS Blue UV Roll-off / Congestion",
        "FAST_ROTATOR_F_SUBGIANT_PHOTOSPHERE": "Fast Rotator F-Subgiant (HD 56986)",
        "TELLURIC_OR_O2_H2O_BAND": "Telluric / O2 / H2O / Chromospheric",
        "CHROMOSPHERIC_LINE_CORE_OR_WING": "Telluric / O2 / H2O / Chromospheric",
        "CHROMOSPHERIC_LINE_WING": "Telluric / O2 / H2O / Chromospheric",
        "CRIRES_DETECTOR_CHIP_EDGE_OR_TELLURIC": "CRIRES Y-Band Chip Edge / Telluric",
        "PRZYBYLSKI_CHEMICALLY_PECULIAR_LANTHANIDE": "Przybylski Star Lanthanide (HD 101065)",
        "SINGLE_EPOCH_ARCHIVAL_RESIDUAL": "Single-Epoch / Continuum Residual",
        "PERSISTENT_PHOTOSPHERIC_PSEUDOCONTINUUM": "Single-Epoch / Continuum Residual",
        "PHOTOSPHERIC_OR_CONTINUUM_RESIDUAL": "Single-Epoch / Continuum Residual",
        "CIRCUMSTELLAR_SILICATE_DISK": "MIRI Disk / Extragalactic DOG",
        "FAINT_EXTRAGALACTIC_DOG_CONTINUUM": "MIRI Disk / Extragalactic DOG",
    }
    palette = {
        "Single-Epoch / Continuum Residual": "#7F8C8D",
        "FEROS Blue UV Roll-off / Congestion": "#3498DB",
        "Cool M-dwarf / TiO / Molecular": "#E67E22",
        "Fast Rotator F-Subgiant (HD 56986)": "#9B59B6",
        "Telluric / O2 / H2O / Chromospheric": "#1ABC9C",
        "CRIRES Y-Band Chip Edge / Telluric": "#2ECC71",
        "Przybylski Star Lanthanide (HD 101065)": "#E74C3C",
        "MIRI Disk / Extragalactic DOG": "#F1C40F",
    }
    agg_streams = []
    for _, counts in streams:
        c = Counter()
        for k, v in counts.items():
            c[cat_map[k]] += v
        agg_streams.append(c)

    y2 = np.arange(len(streams))
    left = np.zeros(len(streams))
    for grp, col in palette.items():
        widths = np.array([ag[grp] for ag in agg_streams], dtype=float)
        if np.any(widths > 0):
            ax2.barh(y2, widths, left=left, color=col, height=0.56, label=grp)
            left += widths
    for yi, tot in zip(y2, left):
        ax2.text(tot + 2.5, yi, f"{int(tot)} (0 ETI)", va="center", fontsize=8.3, fontweight="bold")
    ax2.set_xlim(0, 185)
    ax2.set_yticks(y2)
    ax2.set_yticklabels([s[0] for s in streams], fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Candidate Count Across All 4 Detection Streams")
    ax2.set_title("(b) Four-Stream Forensic Physical Triage (321 Triggers -> 0 ETI)")
    ax2.grid(axis="x", alpha=0.25)
    ax2.legend(loc="lower right", fontsize=7.4, frameon=True, framealpha=0.94)

    fig.suptitle("Phase D092 Complete Rejection Cascade & Multi-Stream Forensic Audit (0 Verified Technosignatures)", fontsize=11.3)
    _save(fig, "fig6_d092_candidate_vetting_triage_and_cascade.png")


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    fig1_rpca_and_d091_regression(summary)
    fig2_geometric_sync()
    fig3_agnostic_and_calibration(summary)
    fig4_miri_greenhouse_ccf()
    fig5_upper_limits_and_335stars(summary)
    fig6_cascade_and_forensic(summary)


if __name__ == "__main__":
    main()
