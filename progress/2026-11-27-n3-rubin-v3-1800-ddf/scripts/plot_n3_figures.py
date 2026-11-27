#!/usr/bin/env python3
"""
Generate all 6 300-DPI publication figures for Spor N3 (figN3_01 through figN3_06)
in both workspace figures/ and setisearch/progress/2026-11-27-n3-rubin-v3-1800-ddf/figures/.
"""
from __future__ import annotations

import collections
import csv
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any

from astropy.io import fits
from astropy.visualization import ImageNormalize, ZScaleInterval
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rubin_v3_detector as det

ROOT = det.ROOT
WS = det.WS
INP = det.INP
RES = det.RES
FIGS = WS / "figures"
REPO_FIGS = ROOT / "setisearch" / "progress" / "2026-11-27-n3-rubin-v3-1800-ddf" / "figures"
RV2_RES = ROOT / "analysis_workspace" / "work_rubin_v2_20261126_r1_ddf_and_r2_catalog" / "results"

plt.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "legend.fontsize": 8.0,
    "figure.facecolor": "white",
    "axes.facecolor": "#fbfbfd",
    "axes.grid": True,
    "grid.alpha": 0.28,
})


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _save_fig(fig: plt.Figure, fname: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    REPO_FIGS.mkdir(parents=True, exist_ok=True)
    p1, p2 = FIGS / fname, REPO_FIGS / fname
    fig.savefig(p1, dpi=300, bbox_inches="tight", pad_inches=0.14)
    shutil.copy2(p1, p2)
    plt.close(fig)
    print(f"Saved {fname}: {p1.stat().st_size:,} B")


def fig1_cohort_and_cmd() -> None:
    n3_coh = list(csv.DictReader((RES / "N3_COHORT_1800_FROZEN.csv").open(encoding="utf-8")))
    r1_coh = list(csv.DictReader((RV2_RES / "R1_COHORT_FROZEN.csv").open(encoding="utf-8")))
    coconf = list(csv.DictReader((RES / "N3_V3_COCONFIRMED_CANDIDATES.csv").open(encoding="utf-8")))
    cc_oids = {r["diaObjectId"] for r in coconf}

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.9), constrained_layout=True)

    # Panel 1 & 2: COSMOS & EDFS_B footprints (R1 vs N3)
    for ax, fld, tit in [(axes[0], "COSMOS", "COSMOS Footprint (N3=737, R1=182)"), (axes[1], "EDFS_B", "EDFS_B Footprint (N3=1,063, R1=100)")]:
        sub_r1 = [r for r in r1_coh if r["field"] == fld]
        sub_n3 = [r for r in n3_coh if r["field"] == fld]
        ax.scatter([float(r["ra_deg"]) for r in sub_n3], [float(r["dec_deg"]) for r in sub_n3], s=9, alpha=0.6, color="#1f77b4", label=f"N3 V3 Stars (N={len(sub_n3)})")
        ax.scatter([float(r["ra_deg"]) for r in sub_r1], [float(r["dec_deg"]) for r in sub_r1], s=18, alpha=0.85, color="#ff7f0e", marker="^", label=f"Prior R1 Stars (N={len(sub_r1)})")
        sub_cc = [r for r in sub_n3 if r["diaObjectId"] in cc_oids]
        if sub_cc:
            ax.scatter([float(r["ra_deg"]) for r in sub_cc], [float(r["dec_deg"]) for r in sub_cc], s=130, marker="*", color="#d62728", edgecolor="black", lw=0.8, zorder=6, label="V3 Co-Confirmed M-Flare")
        ax.set_xlabel("RA [deg]")
        ax.set_ylabel("Dec [deg]")
        ax.set_title(tit)
        ax.invert_xaxis()
        ax.legend(loc="best", framealpha=0.92, fontsize=7.6)

    # Panel 3: Gaia CMD (BP-RP vs G_mag)
    bp_n3, g_n3 = [], []
    for r in n3_coh:
        b, g = _f(r["bp_rp"]), _f(r["phot_g_mean_mag"])
        if b is not None and g is not None:
            bp_n3.append(b)
            g_n3.append(g)
    bp_r1, g_r1 = [], []
    for r in r1_coh:
        b, g = _f(r["bp_rp"]), _f(r["phot_g_mean_mag"])
        if b is not None and g is not None:
            bp_r1.append(b)
            g_r1.append(g)

    axes[2].scatter(bp_n3, g_n3, s=8, alpha=0.45, color="#1f77b4", label="N3 Zero-Overlap (N=1,800)")
    axes[2].scatter(bp_r1, g_r1, s=16, alpha=0.75, color="#ff7f0e", marker="^", label="R1 Cohort (N=300)")
    for r in coconf:
        b, g = _f(r["bp_rp"]), _f(r["phot_g_mean_mag"])
        if b and g:
            axes[2].scatter([b], [g], s=140, color="#d62728", marker="*", edgecolor="black", lw=0.8, zorder=6, label="313980945231249489 (M-Flare)")
            axes[2].annotate("M-Dwarf Flare\n(BP-RP=2.63)", (b, g), xytext=(-105, -20), textcoords="offset points", fontsize=8.0, fontweight="bold", color="#d62728", bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#d62728", alpha=0.90), arrowprops=dict(arrowstyle="->", lw=0.9, color="#d62728"))
    axes[2].invert_yaxis()
    axes[2].set_xlabel("Gaia DR3 BP - RP Color [mag]")
    axes[2].set_ylabel("Gaia G Magnitude [mag]")
    axes[2].set_title("Gaia DR3 Color-Magnitude Selection (2,100 Total)")
    axes[2].legend(loc="lower left", framealpha=0.92, fontsize=7.6)

    fig.suptitle("Spor N3 — 1,800 Zero-Overlap Gaia-Isolated Vera Rubin DDF Stars (+ 300 Prior R1)", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN3_01_cohort_1800_footprint_and_cmd.png")


def fig2_v3_veto_performance(res_src: dict[str, Any], res_fp: dict[str, Any], det_sum: dict[str, Any], st3: dict[str, Any]) -> None:
    vf = det_sum["v3_veto_funnel"]
    fp_lookup = res_fp["scored_lookup_by_obj_band"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Left: All 152 raw /sources triggers (offset vs reliability), colored by V3 stage disposition
    g_x, g_y, u_x, u_y, c_x, c_y = [], [], [], [], [], []
    for t in res_src["triggers_dim"] + res_src["triggers_flash"]:
        off = t.get("centroid_offset_arcsec")
        rel = t.get("reliability")
        if off is None or rel is None:
            continue
        if off > det.V3_MAX_CENTROID_OFFSET_ARCSEC or rel < det.V3_MIN_RELIABILITY:
            g_x.append(off)
            g_y.append(rel)
        else:
            fp_obs = fp_lookup.get((t["diaObjectId"], t["band"]), [])
            best_fp = None
            best_dt = 999.0
            for f in fp_obs:
                if f["evaluable"]:
                    dt = abs(f["mjd"] - t["mjd"])
                    if dt <= det.V3_CROSS_MATCH_DT_DAYS and dt < best_dt:
                        best_dt = dt
                        best_fp = f
            conf = bool(best_fp and ((t["channel"] == "DIM" and best_fp["flux_ratio"] <= det.V3_FP_DIM_CONFIRM_RATIO) or (t["channel"] == "FLASH" and best_fp["flux_ratio"] >= det.V3_FP_FLASH_CONFIRM_RATIO)))
            if conf:
                c_x.append(off)
                c_y.append(rel)
            else:
                u_x.append(off)
                u_y.append(rel)

    ax1.scatter(g_x, g_y, s=28, alpha=0.7, color="#7f7f7f", label=f"Gate 1 Veto: Astrom/Rel (N={len(g_x)})")
    ax1.scatter(u_x, u_y, s=72, marker="s", color="#ff7f0e", edgecolor="black", lw=0.7, zorder=4, label=f"Gate 2 Veto: Unconfirmed in /fp (N={len(u_x)})")
    ax1.scatter(c_x, c_y, s=160, marker="*", color="#d62728", edgecolor="black", lw=0.8, zorder=6, label=f"V3 Co-Confirmed M-Flare (N={len(c_x)} epochs / 1 obj)")
    ax1.axvline(0.40, color="#1f77b4", ls="--", lw=1.4, label='Gate 1: Offset <= 0.40"')
    ax1.axhline(0.50, color="#2ca02c", ls="--", lw=1.4, label="Gate 1: Reliability >= 0.50")
    if c_x:
        ax1.annotate("313980945231249489\n(off=0.012\", rel=0.95)", (c_x[0], c_y[0]), xytext=(16, -34), textcoords="offset points", fontsize=8.0, fontweight="bold", color="#d62728", bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#d62728", alpha=0.92), arrowprops=dict(arrowstyle="->", lw=0.9, color="#d62728"))
    ax1.set_xlim(-0.04, 1.35)
    ax1.set_ylim(-0.04, 1.06)
    ax1.set_xlabel("Per-Epoch DIA Centroid Offset from Object Median [arcsec]")
    ax1.set_ylabel("Rubin Fink Reliability Score [0–1]")
    ax1.set_title("V3 Gate 1 & Gate 2 Separation Across All 152 Raw /sources Triggers")
    ax1.legend(loc="center right", framealpha=0.92, fontsize=7.8)

    # Right: Funnel bar chart
    stages = [
        f"Raw /sources\nTriggers\n(V2 Baseline)",
        f"Pass Gate 1\n(Offset <= 0.40\"\n& Rel >= 0.50)",
        f"Pass Gate 2\n(/fp Cross-Stream\nConfirmed)",
        f"Confirmed\nM-Dwarf Flare\n(Natural)",
        f"Unexplained\nSETI / ETI\nAnomaly",
    ]
    vals = [vf["raw_sources_triggers"], vf["raw_sources_triggers"] - vf["veto_astrom_or_rel_src"], vf["v3_coconfirmed_epochs"], vf["v3_coconfirmed_epochs"], 0]
    cols = ["#7f7f7f", "#ff7f0e", "#1f77b4", "#2ca02c", "#d62728"]
    bars = ax2.bar(np.arange(len(stages)), vals, color=cols, edgecolor="black", lw=0.7)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, max(1.5, v) + 3, str(v), ha="center", va="bottom", fontweight="bold", fontsize=10)
    ax2.set_ylim(0, max(vals) * 1.18)
    ax2.set_xticks(np.arange(len(stages)))
    ax2.set_xticklabels(stages, fontsize=8.0)
    ax2.set_ylabel("Trigger Epochs (N = 1,800 Stars)")
    ax2.set_title("V3 False-Positive Suppression Funnel (152 -> 6 -> 2 -> 0 ETI)")

    fp_aud = st3.get("fp_top30_raw_outlier_audit", {})
    txt = "Top 30 raw /fp outliers root-cause:\n" + "\n".join(f"• {k.replace('RAW_SOURCES_FLAGGED_','').replace('_',' ')}: {v}" for k, v in fp_aud.items())
    ax2.text(0.38, 0.72, txt, transform=ax2.transAxes, fontsize=7.6, va="top", bbox=dict(boxstyle="round,pad=0.35", fc="#fff7e6", ec="#e6ab02"))

    fig.suptitle("Spor N3 — Upgraded Rubin V3 Cross-Stream & Astrometric Veto Performance", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN3_02_v3_cross_stream_veto_performance.png")


def fig3_top_lightcurves(raw_src: list[dict[str, Any]], raw_fp: list[dict[str, Any]], st3: dict[str, Any]) -> None:
    # Build per-oid raw lookups
    s_by = collections.defaultdict(list)
    for r in det.dedup_rows(raw_src, "r:diaSourceId", "sources"):
        s_by[str(r.get("r:diaObjectId") or "")].append(r)
    f_by = collections.defaultdict(list)
    for r in det.dedup_rows(raw_fp, "r:diaForcedSourceId", "fp"):
        f_by[str(r.get("r:diaObjectId") or "")].append(r)

    # Pick 6 distinct illustrative objects from cutout_reports: coconf first, then veto_unconf, then veto_astrom
    picks: list[tuple[str, str, str]] = []
    seen = set()
    for rep in st3["cutout_reports"]:
        oid = rep["diaObjectId"]
        if oid in seen:
            continue
        seen.add(oid)
        picks.append((oid, rep["vet_group"], f"{rep['channel']} {rep['band']}-band z={rep['z_flash'] if rep['channel']=='FLASH' else rep['z_dim']}"))
        if len(picks) >= 6:
            break

    fig, axes = plt.subplots(2, 3, figsize=(14.2, 8.2), constrained_layout=True)
    bcols = {"u": "#9467bd", "g": "#2ca02c", "r": "#d62728", "i": "#ff7f0e", "z": "#8c564b", "y": "#17becf"}

    for ax, (oid, grp, note) in zip(axes.ravel(), picks):
        fp_pts = f_by.get(oid, [])
        src_pts = [x for x in s_by.get(oid, []) if det.check_source_quality(x)[0]]
        all_m = [det.safe_float(x.get("r:midpointMjdTai")) for x in fp_pts + src_pts]
        all_m = [m for m in all_m if m is not None]
        m0 = min(all_m) if all_m else 61000.0

        for band in ("g", "r", "i", "z"):
            fx, fy, fe = [], [], []
            for p in fp_pts:
                if p.get("r:band") == band:
                    m, f, e = det.safe_float(p.get("r:midpointMjdTai")), det.safe_float(p.get("r:scienceFlux")), det.safe_float(p.get("r:scienceFluxErr"))
                    if m and f is not None and e:
                        fx.append(m - m0); fy.append(f); fe.append(e)
            if fx:
                ax.errorbar(fx, fy, yerr=fe, fmt=".", ms=4, alpha=0.45, lw=0.7, color=bcols[band], label=f"/fp {band}")
            sx, sy = [], []
            for p in src_pts:
                if p.get("r:band") == band:
                    m, f = det.safe_float(p.get("r:midpointMjdTai")), det.safe_float(p.get("r:scienceFlux"))
                    if m and f is not None:
                        sx.append(m - m0); sy.append(f)
            if sx:
                ax.scatter(sx, sy, s=26, marker="^", edgecolor="black", lw=0.5, color=bcols[band], zorder=5, label=f"/sources {band}")

        g_lbl = {"coconf": "V3 CO-CONFIRMED M-FLARE", "veto_unconf": "V3 VETO: UNCONFIRMED IN /fp", "veto_astrom": "V3 VETO: ASTROM/REL FAIL"}.get(grp, grp)
        ax.set_title(f"[{g_lbl}]\noid={oid}\n{note}", fontsize=8.6, fontweight="bold" if grp == "coconf" else "normal")
        ax.set_xlabel("Days since first epoch")
        ax.set_ylabel("Rubin Difference / PSF Science Flux [nJy]")
        ax.legend(loc="best", fontsize=7.0, ncol=2)

    fig.suptitle("Spor N3 — /sources vs Forced Photometry (/fp) Lightcurves: 1 True M-Dwarf Flare vs V3-Vetoed Artifacts", fontsize=11.8, fontweight="bold")
    _save_fig(fig, "figN3_03_n3_top_coconfirmed_lightcurves.png")


def _load_2d(p: Path) -> np.ndarray | None:
    if not p.exists():
        return None
    with fits.open(p, memmap=False) as hdul:
        for h in hdul:
            if h.data is not None and h.data.ndim == 2:
                return np.asarray(h.data, dtype=float)
    return None


def fig4_cutout_gallery(st3: dict[str, Any]) -> None:
    # Select 2 coconf (g & r flare) + 1 veto_astrom FLASH + 2 veto_astrom DIM (negative/dipole contrast)
    cc_rows = [r for r in st3["cutout_reports"] if r["vet_group"] == "coconf" and "Difference" in r["cutout_metrics"]][:2]
    va_fl = [r for r in st3["cutout_reports"] if r["vet_group"] == "veto_astrom" and r["channel"] == "FLASH" and "Difference" in r["cutout_metrics"]][:1]
    va_dm = [r for r in st3["cutout_reports"] if r["vet_group"] == "veto_astrom" and r["channel"] == "DIM" and "Difference" in r["cutout_metrics"]][:2]
    rows = cc_rows + va_fl + va_dm

    fig, axes = plt.subplots(len(rows), 3, figsize=(10.5, 2.75 * len(rows)), constrained_layout=True)
    for ri, r in enumerate(rows):
        sid = r["diaSourceId"]
        cm = r["cutout_metrics"]
        for ci, kind in enumerate(("Science", "Template", "Difference")):
            ax = axes[ri, ci]
            fp = INP / "fink_cutouts" / cm[kind]["file"]
            img = _load_2d(fp)
            if img is not None:
                fin = img[np.isfinite(img)]
                norm = ImageNormalize(fin, interval=ZScaleInterval()) if fin.size > 10 else None
                ax.imshow(np.nan_to_num(img, nan=0.0), origin="lower", cmap="gray_r" if kind != "Difference" else "coolwarm", norm=norm)
            ax.set_xticks([]); ax.set_yticks([])
            if ri == 0:
                ax.set_title(f"Rubin {kind} Cutout", fontweight="bold")
            if ci == 0:
                tag = {"coconf": "V3 CO-CONF M-FLARE", "veto_unconf": "V3 VETO (NO /fp)", "veto_astrom": "V3 VETO (AST/REL)"}[r["vet_group"]]
                dsnr = cm["Difference"]["center_pos_snr"]
                np_rat = cm["Difference"]["neg_pos_ratio"]
                ax.set_ylabel(f"{tag}\n{r['band']} z={r['z_flash'] if r['channel']=='FLASH' else r['z_dim']}\nDiffSNR={dsnr} | neg/pos={np_rat}", fontsize=7.8, fontweight="bold")

    fig.suptitle("Spor N3 — Real Vera Rubin FITS Cutout Gallery (Co-Confirmed M-Flare vs V3-Vetoed Controls)", fontsize=11.5, fontweight="bold")
    _save_fig(fig, "figN3_04_n3_fits_cutout_gallery.png")


def fig5_injection_recovery(det_sum: dict[str, Any]) -> None:
    ins, inf = det_sum["injection_sources"], det_sum["injection_fp"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.2), constrained_layout=True)

    for ax, ch_key, tit, xlab in [
        (ax1, "dim_conditional", "Channel A — Boyajian-Like Dimming Injections (2,400/stream)", "Injected Dimming Depth Δm [mag]"),
        (ax2, "flash_conditional", "Channel B — Optical Flash / Laser Pulse Injections (2,400/stream)", "Injected Flash Amplitude Δm [mag]"),
    ]:
        gs = ins[ch_key]["grid"]
        gf = inf[ch_key]["grid"]
        xs = sorted(float(k) for k in gf)
        yf = [100.0 * gf[f"{x:.2f}"]["completeness"] for x in xs]
        ys = [100.0 * gs[f"{x:.2f}"]["completeness"] for x in xs]
        ax.plot(xs, yf, "s-", lw=2.3, ms=6.5, color="#1f77b4", label=f"/fp Stream (4,800 trials; mean={inf[ch_key]['completeness_all']*100:.1f}%)")
        ax.plot(xs, ys, "o--", lw=2.1, ms=6.0, color="#d62728", label=f"/sources Stream (4,800 trials; mean={ins[ch_key]['completeness_all']*100:.1f}%)")
        for x, y1, y2 in zip(xs, yf, ys):
            ax.annotate(f"{y1:.1f}%", (x, y1), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7.8, color="#1f77b4")
            ax.annotate(f"{y2:.1f}%", (x, y2), xytext=(8, -14), textcoords="offset points", ha="center", fontsize=7.8, color="#d62728")
        ax.set_ylim(15, 108)
        ax.set_xlabel(xlab)
        ax.set_ylabel("Injection Recovery Completeness [%]")
        ax.set_title(tit)
        ax.legend(loc="lower right", framealpha=0.92)

    fig.suptitle("Spor N3 — Empirical Injection-Recovery Calibration (9,600 Seeded Trials Across 400 Stars/Stream)", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN3_05_n3_injection_recovery_4800.png")


def fig6_unified_bounds(det_sum: dict[str, Any]) -> None:
    rv2 = json.loads((RV2_RES / "R1_R2_DETECTOR_SUMMARY.json").read_text(encoding="utf-8"))
    r1l = rv2["bayesian_limits"]
    n3l = det_sum["bayesian_limits_n3"]
    cmbl = det_sum["bayesian_limits_combined_v2_v3_2100stars"]

    # Compare Jeffreys Beta (0.5, N_eff+0.5) & Uniform (1, N_eff+1) across campaigns
    labels = [
        "Rubin V2 R1\n/sources\n(N_eff=56)",
        "Rubin V2 R1\n/fp\n(N_eff=217)",
        "Rubin V3 N3\n/sources\n(N_eff=364)",
        "Rubin V3 N3\n/fp\n(N_eff=1,477)",
        "Combined V2+V3\n/fp Flash\n(N_eff=1,694)",
        "Master Spec.\nALL_SCIENCE_EM\n(1,083 stars)",
        "Spor N1 Blind\nDyson g>=0.05\n(N_eff=257)",
        "Spor N2 SSOFT\nAstrom drift\n(N_eff=1,368)",
    ]
    j_vals = [
        r1l["sources_flash_conditional"]["jeffreys_f95_pct"],
        r1l["fp_flash_conditional"]["jeffreys_f95_pct"],
        n3l["sources_flash"]["jeffreys_f95_pct"],
        n3l["fp_flash"]["jeffreys_f95_pct"],
        cmbl["fp_flash"]["jeffreys_f95_pct"],
        0.3243,
        0.7427,
        0.1403,
    ]
    u_vals = [
        r1l["sources_flash_conditional"]["uniform_f95_pct"],
        r1l["fp_flash_conditional"]["uniform_f95_pct"],
        n3l["sources_flash"]["uniform_f95_pct"],
        n3l["fp_flash"]["uniform_f95_pct"],
        cmbl["fp_flash"]["uniform_f95_pct"],
        0.5048,
        1.1526,
        0.2186,
    ]

    fig, ax = plt.subplots(figsize=(13.6, 5.4), constrained_layout=True)
    x = np.arange(len(labels))
    w = 0.34
    b1 = ax.bar(x - w / 2, j_vals, width=w, color="#1f77b4", edgecolor="black", lw=0.6, label="Jeffreys Beta (0.5, N_eff + 0.5)")
    b2 = ax.bar(x + w / 2, u_vals, width=w, color="#ff7f0e", edgecolor="black", lw=0.6, label="Uniform Bayes (1, N_eff + 1)")
    for b in list(b1) + list(b2):
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 0.14, f"{h:.2f}%", ha="center", va="bottom", fontsize=7.6, rotation=90, bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.82))

    ax.axhline(0.3243, color="#2ca02c", ls="--", lw=1.3, label="Main 1,083-Star Spectroscopic EM Benchmark (0.3243% Jeffreys)")
    ax.axvline(4.5, color="#888888", ls=":", lw=1.2)
    ax.set_ylim(0, max(u_vals) * 1.24)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.2)
    ax.set_ylabel("95% Upper Limit on ETI Incidence f_95 [%] (k = 0 ETI)")
    ax.set_title("Spor N3 — Rubin Scaling Progression (300 -> 1,800 -> 2,100 Stars) vs Master SETI Benchmarks", fontsize=11.5, fontweight="bold")
    ax.legend(loc="upper right", framealpha=0.92)
    _save_fig(fig, "figN3_06_unified_rubin_v2_v3_and_master_bounds.png")


def main() -> int:
    cohort = list(csv.DictReader((RES / "N3_COHORT_1800_FROZEN.csv").open(encoding="utf-8")))
    det_sum = json.loads((RES / "N3_DETECTOR_SUMMARY.json").read_text(encoding="utf-8"))
    st3 = json.loads((RES / "N3_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    raw_src = det.load_batches("n3_sources_")
    raw_fp = det.load_batches("n3_fp_")
    res_src = det.analyze_stream(cohort, raw_src, "sources", "r:diaSourceId")
    res_fp = det.analyze_stream(cohort, raw_fp, "fp", "r:diaForcedSourceId")

    fig1_cohort_and_cmd()
    fig2_v3_veto_performance(res_src, res_fp, det_sum, st3)
    fig3_top_lightcurves(raw_src, raw_fp, st3)
    fig4_cutout_gallery(st3)
    fig5_injection_recovery(det_sum)
    fig6_unified_bounds(det_sum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
