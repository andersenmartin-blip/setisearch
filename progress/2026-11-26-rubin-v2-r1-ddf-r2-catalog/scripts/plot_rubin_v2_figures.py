#!/usr/bin/env python3
"""
Generate 6 publication-grade 300-DPI figures (figR01-figR06) for Rubin V2 (Spor R1 & R2)
in both workspace figures/ and setisearch progress figures/.
"""
from __future__ import annotations

import collections
import csv
import json
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_rubin_v2_20261126_r1_ddf_and_r2_catalog")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_rubin_v2_20261126")
RESULTS = WS / "results"
FIGS = WS / "figures"
REPO_FIGS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/setisearch/progress/2026-11-26-rubin-v2-r1-ddf-r2-catalog/figures")

plt.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.2,
    "figure.facecolor": "white",
    "axes.facecolor": "#fcfcfd",
    "axes.grid": True,
    "grid.alpha": 0.25,
})


def load_all_data():
    stats = json.loads((INPUTS / "metadata" / "fink_2026_stats_combined.json").read_text(encoding="utf-8"))
    summary = json.loads((RESULTS / "R1_R2_DETECTOR_SUMMARY.json").read_text(encoding="utf-8"))
    r1_cohort = list(csv.DictReader((RESULTS / "R1_COHORT_FROZEN.csv").open(encoding="utf-8")))
    r1_src_sum = list(csv.DictReader((RESULTS / "R1_SOURCES_OBJECT_SUMMARY.csv").open(encoding="utf-8")))
    triage = list(csv.DictReader((RESULTS / "R1_FINAL_CANDIDATE_TRIAGE.csv").open(encoding="utf-8")))
    r2_stars = list(csv.DictReader((RESULTS / "R2_SOUTHERN_538STARS_FROZEN.csv").open(encoding="utf-8")))
    r2_matches = list(csv.DictReader((RESULTS / "R2_CATALOG_MATCHES.csv").open(encoding="utf-8")))
    vet = json.loads((RESULTS / "STAGE3_CUTOUT_AND_SIMBAD_VETTING.json").read_text(encoding="utf-8"))

    raw_src = []
    for p in sorted((INPUTS / "fink_sources").glob("r1_sources_*.json")):
        if not p.name.endswith(".receipt.json"):
            raw_src.extend(json.loads(p.read_text(encoding="utf-8"), parse_int=str))
    raw_fp = []
    for p in sorted((INPUTS / "fink_fp").glob("r1_fp_*.json")):
        if not p.name.endswith(".receipt.json"):
            raw_fp.extend(json.loads(p.read_text(encoding="utf-8"), parse_int=str))
    return stats, summary, r1_cohort, r1_src_sum, triage, r2_stars, r2_matches, vet, raw_src, raw_fp


def save_both(fig: plt.Figure, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    REPO_FIGS.mkdir(parents=True, exist_ok=True)
    p1 = FIGS / name
    p2 = REPO_FIGS / name
    fig.savefig(p1, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    shutil.copy2(p1, p2)


def make_fig1(stats, r2_stars, r2_matches):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.8), gridspec_kw={"width_ratios": [1.05, 1.15]})
    months = [f"2026{m:02d}" for m in range(2, 12)]
    labels = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
    alerts_m = [sum(int(x.get("f:alerts", 0)) for x in stats[ym]) / 1e6 for ym in months]
    nights_n = [len(stats[ym]) for ym in months]

    x = np.arange(len(months))
    colors = ["#4c78a8" if m != "202611" else "#e45756" for m in months]
    colors[8] = "#f58518"  # Oct
    bars = ax1.bar(x, alerts_m, color=colors, edgecolor="#222222", linewidth=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("Fink LSST Alerts (Millions)")
    ax1.set_title("2026 Fink LSST Stream Activity (87 Nights, 16.25M Alerts)")
    ax1.set_ylim(0, max(alerts_m) * 1.24)
    for idx, (b, ni, am) in enumerate(zip(bars, nights_n, alerts_m)):
        if ni > 0:
            ax1.text(b.get_x() + b.get_width() / 2, am + 0.18, f"{ni}n", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
        else:
            ax1.text(b.get_x() + b.get_width() / 2, 0.12, "0n", ha="center", va="bottom", fontsize=7.8, color="#666666")
    ax1.annotate("Nov 2 Pilot\n(2 Oct nights only)", xy=(8, alerts_m[8]), xytext=(6.2, 5.2),
                 arrowprops=dict(arrowstyle="->", color="#f58518", lw=1.2), fontsize=8.0,
                 bbox=dict(boxstyle="round,pad=0.25", fc="#fff8ec", ec="#f58518"))
    ax1.annotate("Nov 5-15 Recovery\n(+11 nights, 0.77M alerts)", xy=(9, alerts_m[9]), xytext=(5.9, 7.6),
                 arrowprops=dict(arrowstyle="->", color="#e45756", lw=1.2), fontsize=8.0,
                 bbox=dict(boxstyle="round,pad=0.25", fc="#fff0f0", ec="#e45756"))

    # Sky distribution
    ra_s = [float(r["ra_deg"]) for r in r2_stars]
    dec_s = [float(r["dec_deg"]) for r in r2_stars]
    ax2.scatter(ra_s, dec_s, s=14, color="#6b8ba4", alpha=0.65, label=f"Spor R2: {len(r2_stars)} Southern SETI Stars (Dec <= +15°)")
    ddfs = [("COSMOS (182)", 150.119, 2.2058, "#e45756", (15, 12)),
            ("EDFS-b (100)", 63.600, -48.000, "#54a24b", (14, -18)),
            ("ELAIS-S1 (18)", 9.450, -44.000, "#b279a2", (14, 14))]
    for lbl, r0, d0, col, offs in ddfs:
        ax2.scatter([r0], [d0], s=140, marker="*", color=col, edgecolor="black", linewidth=0.7, zorder=6, label=f"Spor R1 DDF: {lbl}")
        ax2.annotate(lbl, xy=(r0, d0), xytext=offs, textcoords="offset points", fontsize=8.2, fontweight="bold", color=col)
    if r2_matches:
        m0 = r2_matches[0]
        ax2.scatter([float(m0["star_ra_deg"])], [float(m0["star_dec_deg"])], s=95, marker="D", fc="none", ec="#ff9900", lw=1.8, zorder=7,
                    label=f"R2 Match <=10\": {m0['star']} (9.59\" offset)")
    ax2.axhline(15.0, color="#333333", ls="--", lw=0.9, alpha=0.7)
    ax2.axhline(5.0, color="#888888", ls=":", lw=0.8, alpha=0.7)
    ax2.text(352, 16.5, "LSST Northern Limit (Dec <= +15°)", ha="left", fontsize=7.6, color="#333333")
    ax2.set_xlim(360, 0)
    ax2.set_ylim(-88, 28)
    ax2.set_xlabel("Right Ascension ICRS [deg]")
    ax2.set_ylabel("Declination ICRS [deg]")
    ax2.set_title("Sky Coverage: Spor R1 Deep Drilling Fields & Spor R2 538 Stars")
    ax2.legend(loc="lower left", framealpha=0.92, ncol=1, fontsize=7.6)

    fig.tight_layout(w_pad=2.4)
    save_both(fig, "figR01_rubin2026_cadence_and_sky.png")


def make_fig2(r1_cohort, r1_src_sum, triage, summary):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.9), gridspec_kw={"width_ratios": [1.1, 1.05]})
    sum_map = {r["diaObjectId"]: r for r in r1_src_sum}
    tri_map = {r["diaObjectId"]: r for r in triage}

    field_cfg = {"COSMOS": ("#e45756", "o"), "EDFS_B": ("#4c78a8", "s"), "ELAIS_S1": ("#54a24b", "^")}
    for fn, (col, mk) in field_cfg.items():
        sub = [r for r in r1_cohort if r["field"] == fn and r.get("bp_rp")]
        bprp = [float(r["bp_rp"]) for r in sub]
        gmag = [float(r["phot_g_mean_mag"]) for r in sub]
        ax1.scatter(bprp, gmag, s=20, c=col, marker=mk, alpha=0.45, label=f"{fn} ({len(sub)} Gaia stars)")

    # Highlight LONO-evaluable /sources stars & triggers
    ev_x, ev_y = [], []
    for r in r1_cohort:
        sr = sum_map.get(r["diaObjectId"])
        if sr and int(sr["eval_rows_lono"]) > 0 and r.get("bp_rp"):
            ev_x.append(float(r["bp_rp"]))
            ev_y.append(float(r["phot_g_mean_mag"]))
    ax1.scatter(ev_x, ev_y, s=36, fc="none", ec="#222222", lw=0.8, label=f"LONO Evaluable /sources (N={summary['r1_sources']['evaluable_objects_lono']})")

    for t in triage:
        if not t.get("bp_rp"):
            continue
        x0, y0 = float(t["bp_rp"]), float(t["phot_g_mean_mag"])
        disp = t["final_disposition"]
        if "FLARE" in disp:
            ax1.scatter([x0], [y0], s=110, marker="*", c="#ffbf00", ec="black", lw=0.8, zorder=8, label="Confirmed M-Dwarf Flare (1)")
        elif "PERIODIC" in disp:
            ax1.scatter([x0], [y0], s=55, marker="D", fc="none", ec="#9467bd", lw=1.6, zorder=7)
    ax1.scatter([], [], s=55, marker="D", fc="none", ec="#9467bd", lw=1.6, label="Periodic Variable Confirmed (4)")
    ax1.invert_yaxis()
    ax1.set_xlabel("Gaia DR3 BP - RP [mag]")
    ax1.set_ylabel("Gaia DR3 G [mag]")
    ax1.set_title("Spor R1 Gaia DR3 CMD (300 Unblended Stars, 16 <= G <= 21)")
    ax1.legend(loc="lower left", framealpha=0.92, fontsize=7.8)

    # Panel 2: Feasibility Comparison Nov 2 Pilot vs Rubin V2 R1
    cats = ["Nov 2 Pilot\n/sources", "Nov 2 Pilot\n/fp (Forced)", "Rubin V2 R1\nCausal /sources", "Rubin V2 R1\nLONO /sources", "Rubin V2 R1\nCausal /fp", "Rubin V2 R1\nLONO /fp"]
    vals = [
        2,
        4,
        summary["r1_sources"]["evaluable_objects_causal"],
        summary["r1_sources"]["evaluable_objects_lono"],
        summary["r1_fp"]["evaluable_objects_causal"],
        summary["r1_fp"]["evaluable_objects_lono"],
    ]
    bar_cols = ["#999999", "#b8b8b8", "#72b7b2", "#4c78a8", "#f58518", "#e45756"]
    yb = np.arange(len(cats))
    b2 = ax2.barh(yb, vals, color=bar_cols, edgecolor="#222222", linewidth=0.6)
    ax2.axvline(50, color="#111111", ls="--", lw=1.3, label="Minimum Pilot Threshold (N = 50 Stars)")
    ax2.set_yticks(yb)
    ax2.set_yticklabels(cats)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 310)
    ax2.set_xlabel("Evaluable Unique Stars (Passing Baseline Visits/Dates & SNR >= 10)")
    ax2.set_title("Rubin V2 Resolves Nov 2 Sample Bottleneck (>50 Stars in Both Streams)")
    for b, v in zip(b2, vals):
        ax2.text(v + 5, b.get_y() + b.get_height() / 2, f"{v} stars", va="center", ha="left", fontsize=8.5, fontweight="bold")
    ax2.legend(loc="lower right", framealpha=0.92)

    fig.tight_layout()
    save_both(fig, "figR02_r1_gaia_cmd_and_depth_comparison.png")


def make_fig3(summary, raw_src, r1_cohort):
    import sys
    sys.path.insert(0, str(WS / "scripts"))
    import rubin_v2_detector as det

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.9), gridspec_kw={"width_ratios": [1.05, 1.15]})

    # Heatmap/table of injection completeness (conditional vs duty cycle)
    inj = summary["injection_sources"]
    labels = [
        "Dim 0.30m (1h)", "Dim 0.30m (24h)", "Dim 0.30m (168h)",
        "Dim 0.60m (1h)", "Dim 0.60m (24h)", "Dim 0.60m (168h)",
        "Dim 1.00m (1h)", "Dim 1.00m (24h)", "Dim 1.00m (168h)",
        "Flash 0.50m (30s)", "Flash 0.50m (1h)",
        "Flash 1.00m (30s)", "Flash 1.00m (1h)",
        "Flash 2.00m (30s)", "Flash 2.00m (1h)",
    ]
    keys = [
        ("0.30mag_1.000h", "dim"), ("0.30mag_24.000h", "dim"), ("0.30mag_168.000h", "dim"),
        ("0.60mag_1.000h", "dim"), ("0.60mag_24.000h", "dim"), ("0.60mag_168.000h", "dim"),
        ("1.00mag_1.000h", "dim"), ("1.00mag_24.000h", "dim"), ("1.00mag_168.000h", "dim"),
        ("0.50mag_0.008h", "flash"), ("0.50mag_1.000h", "flash"),
        ("1.00mag_0.008h", "flash"), ("1.00mag_1.000h", "flash"),
        ("2.00mag_0.008h", "flash"), ("2.00mag_1.000h", "flash"),
    ]
    cond_vals = [inj[f"{k2}_conditional"]["grid"][k1]["completeness"] * 100.0 for k1, k2 in keys]
    duty_vals = [inj[f"{k2}_duty_cycle"]["grid"][k1]["completeness"] * 100.0 for k1, k2 in keys]

    yy = np.arange(len(labels))
    h = 0.38
    ax1.barh(yy - h / 2, cond_vals, height=h, color="#4c78a8", label="Conditional on Sampled Epoch")
    ax1.barh(yy + h / 2, duty_vals, height=h, color="#f58518", label="Full-Span Survey Duty Cycle")
    ax1.set_yticks(yy)
    ax1.set_yticklabels(labels, fontsize=7.8)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 118)
    ax1.set_xlabel("Injection-Recovery Completeness [%] (1,200 Trials/Regime)")
    ax1.set_title("Empirical Injection Completeness (/sources, LONO)")
    for i, (cv, dv) in enumerate(zip(cond_vals, duty_vals)):
        ax1.text(cv + 1.2, i - h / 2, f"{cv:.0f}%", va="center", fontsize=6.8, color="#23456b")
        ax1.text(dv + 1.2, i + h / 2, f"{dv:.1f}%", va="center", fontsize=6.8, color="#a85506")
    ax1.legend(loc="upper right", framealpha=0.92, fontsize=7.6)

    # Panel 2: Empirical score cloud (flux ratio vs signed Z = -Z_dim)
    res_src = det.analyze_stream(r1_cohort, raw_src, "sources", "r:diaSourceId")
    pts = res_src["all_scored_lono"]
    ratios = np.array([max(0.05, p["flux_ratio"]) for p in pts])
    zs = np.array([p["z_flash"] for p in pts])  # +Z = brighter, -Z = dimmer
    dim_m = np.array([p["trig_dim"] for p in pts])
    fl_m = np.array([p["trig_flash"] for p in pts])
    norm_m = (~dim_m) & (~fl_m)

    ax2.scatter(ratios[norm_m], zs[norm_m], s=7, c="#8fa3b0", alpha=0.45, label=f"Null Epochs ({int(np.sum(norm_m))})")
    ax2.scatter(ratios[dim_m], zs[dim_m], s=32, c="#e45756", edgecolor="black", lw=0.5, label=f"Dimming Triggers (30 rows / 16 obj; Vetted)")
    ax2.scatter(ratios[fl_m], zs[fl_m], s=55, c="#ffbf00", marker="*", edgecolor="black", lw=0.6, label="M-Dwarf Flare Triggers (3 rows / 1 obj)")

    ax2.axvline(det.RATIO_DIM_MAX, color="#e45756", ls="--", lw=1.1)
    ax2.axvline(det.RATIO_FLASH_MIN, color="#d98b00", ls="--", lw=1.1)
    ax2.axhline(-det.Z_DIM_MIN, color="#e45756", ls=":", lw=1.1)
    ax2.axhline(det.Z_FLASH_MIN, color="#d98b00", ls=":", lw=1.1)
    ax2.set_xscale("log")
    ax2.set_xlim(0.25, 3.3)
    ax2.set_ylim(-36, 17.5)
    ax2.set_xlabel("Science Flux Ratio F / F0 (Log Scale)")
    ax2.set_ylabel("Signed Robust Deviation Z [(F - F0) / sigma_tot]")
    ax2.set_title("2,926 Evaluable /sources Epochs Across 85 Gaia Stars")
    ax2.text(0.27, -33.5, "Dimming Gate\n(<=0.759, Z<=-5)", fontsize=7.6, color="#b82525",
             bbox=dict(boxstyle="round,pad=0.2", fc="#fff2f2", ec="#e45756"))
    ax2.text(1.66, 13.5, "Flash Gate\n(>=1.585, Z>=+6)", fontsize=7.6, color="#9e6300",
             bbox=dict(boxstyle="round,pad=0.2", fc="#fff9e6", ec="#d98b00"))
    ax2.legend(loc="lower right", framealpha=0.92, fontsize=7.8)

    fig.tight_layout()
    save_both(fig, "figR03_injection_recovery_and_null_scores.png")


def make_fig4(raw_src, raw_fp):
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.2))
    by_s = collections.defaultdict(list)
    by_f = collections.defaultdict(list)
    for r in raw_src:
        by_s[(str(r.get("r:diaObjectId")), str(r.get("r:band")))].append(r)
    for r in raw_fp:
        by_f[(str(r.get("r:diaObjectId")), str(r.get("r:band")))].append(r)

    def clean_pts(oid, b):
        import sys
        sys.path.insert(0, str(WS / "scripts"))
        import rubin_v2_detector as det
        s = [(float(r["r:midpointMjdTai"]), float(r["r:scienceFlux"]), float(r["r:scienceFluxErr"]))
             for r in by_s[(oid, b)] if det.check_source_quality(r)[0]]
        f = [(float(r["r:midpointMjdTai"]), float(r["r:scienceFlux"]), float(r["r:scienceFluxErr"]))
             for r in by_f[(oid, b)] if det.check_fp_quality(r)[0]]
        return np.array(sorted(s)), np.array(sorted(f))

    # (a) 313871014203228340 i-band: DIA centroid bias vs unitary /fp
    ax = axes[0, 0]
    s, f = clean_pts("313871014203228340", "i")
    f0_fp = np.median(f[:, 1])
    ax.axhspan(0.95, 1.05, color="#d9ecff", alpha=0.5, label="Unitary Forced Photometry +/-5%")
    ax.scatter(f[:, 0] - 61000, f[:, 1] / f0_fp, s=16, c="#5c7fa3", marker="D", alpha=0.55, label=f"/fp Forced Phot ({len(f)} pts, steady ~1.00)")
    ax.scatter(s[:, 0] - 61000, s[:, 1] / f0_fp, s=26, c="#e45756", alpha=0.85, label=f"/sources Clean ({len(s)} pts, dips at 61091/95)")
    ax.axhline(0.7586, color="#c92a2a", ls="--", lw=1.0, label="Dim Threshold (0.759)")
    ax.set_title("(a) 313871014203228340 (COSMOS i): /sources Bias vs Unitary /fp")
    ax.set_xlabel("MJD - 61000 [d]")
    ax.set_ylabel("Normalized Science Flux Ratio")
    ax.set_ylim(0.45, 1.25)
    ax.legend(loc="lower right", fontsize=7.4, framealpha=0.92)

    # (b) 313972182854139942 r+g band M-dwarf flare in BOTH /sources and /fp
    ax = axes[0, 1]
    sr, fr = clean_pts("313972182854139942", "r")
    sg, fg = clean_pts("313972182854139942", "g")
    f0_r = np.median(sr[:, 1]); f0_g = np.median(sg[:, 1])
    ax.scatter(fr[:, 0] - 61000, fr[:, 1] / f0_r, s=16, c="#e45756", marker="D", alpha=0.45, label=f"/fp r-band ({len(fr)} pts)")
    ax.scatter(sr[:, 0] - 61000, sr[:, 1] / f0_r, s=28, c="#c92a2a", alpha=0.9, label=f"/sources r-band (Peak 1.96x, Z=+11.9)")
    ax.scatter(sg[:, 0] - 61000, sg[:, 1] / f0_g, s=28, c="#4c78a8", marker="^", alpha=0.85, label=f"/sources g-band (Peak 1.70x, Z=+7.1)")
    ax.axhline(1.5849, color="#d98b00", ls="--", lw=1.0, label="Flash Threshold (1.585)")
    ax.set_title("(b) 313972182854139942 (COSMOS, BP-RP=2.62): Confirmed M-Dwarf Flare")
    ax.set_xlabel("MJD - 61000 [d]")
    ax.set_ylabel("Normalized Science Flux Ratio")
    ax.set_ylim(0.6, 2.25)
    ax.legend(loc="upper left", fontsize=7.4, framealpha=0.92)

    # (c) 313893023224168464 EDFS_B periodic variable folded P=0.112356 d
    ax = axes[1, 0]
    si, fi = clean_pts("313893023224168464", "i")
    P1 = 0.112356
    f0_i = np.median(fi[:, 1])
    ax.scatter((fi[:, 0] / P1) % 1.0, fi[:, 1] / f0_i, s=16, c="#8fa3b0", marker="D", alpha=0.45, label=f"/fp i-band ({len(fi)} pts)")
    ax.scatter((si[:, 0] / P1) % 1.0, si[:, 1] / f0_i, s=26, c="#9467bd", alpha=0.85, label=f"/sources i-band ({len(si)} pts)")
    ax.axhline(0.7586, color="#c92a2a", ls="--", lw=1.0)
    ax.set_title("(c) 313893023224168464 (EDFS_B): Phase-Folded Variable (P=0.1124 d)")
    ax.set_xlabel("Orbital / Pulsational Phase (P = 0.112356 d, FAP = 1.8e-34)")
    ax.set_ylabel("Normalized i-Band Flux")
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.92)

    # (d) 313980948723007593 COSMOS periodic variable folded P=4.99338 d
    ax = axes[1, 1]
    sg2, fg2 = clean_pts("313980948723007593", "g")
    P2 = 4.99338
    f0_g2 = np.median(fg2[:, 1])
    ax.scatter((fg2[:, 0] / P2) % 1.0, fg2[:, 1] / f0_g2, s=16, c="#8fa3b0", marker="D", alpha=0.45, label=f"/fp g-band ({len(fg2)} pts)")
    ax.scatter((sg2[:, 0] / P2) % 1.0, sg2[:, 1] / f0_g2, s=26, c="#2ca02c", alpha=0.85, label=f"/sources g-band ({len(sg2)} pts)")
    ax.axhline(0.7586, color="#c92a2a", ls="--", lw=1.0)
    ax.set_title("(d) 313980948723007593 (COSMOS): Phase-Folded Variable (P=4.993 d)")
    ax.set_xlabel("Phase (P = 4.99338 d, FAP = 1.1e-10)")
    ax.set_ylabel("Normalized g-Band Flux")
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.92)

    fig.tight_layout()
    save_both(fig, "figR04_r1_top_dimming_and_flash_lightcurves.png")


def make_fig5(vet):
    details = {d["diaObjectId"]: d for d in vet["cutout_details"]}
    rows_show = [
        ("313774269504422076", "313774269504422076 (g)\nDipole Veto (Ratio=0.89)"),
        ("313972182854139942", "313972182854139942 (r)\nM-Dwarf Flare (27.7σ)"),
        ("313871014203228340", "313871014203228340 (i)\nPSF Bias (Unitary /fp)"),
        ("313699505148526678", "R2 GJ 27.1 Companion (g)\n9.59\" Field Offset"),
    ]
    fig, axes = plt.subplots(4, 3, figsize=(10.6, 11.4))
    for r_idx, (oid, title_lbl) in enumerate(rows_show):
        d = details.get(oid)
        for c_idx, kind in enumerate(("Science", "Template", "Difference")):
            ax = axes[r_idx, c_idx]
            ax.grid(False)
            if d and d["stamps"].get(kind, {}).get("valid_fits"):
                fp = Path(d["stamps"][kind]["fits_path"])
                with fits.open(fp) as hdul:
                    img = next(np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2)
                if img.ndim > 2:
                    img = img.reshape((-1, img.shape[-2], img.shape[-1]))[0]
                fin = img[np.isfinite(img)]
                med = float(np.median(fin))
                mad = max(1e-6, 1.4826 * float(np.median(np.abs(fin - med))))
                if kind == "Difference":
                    v = max(5.0 * mad, float(np.percentile(np.abs(fin - med), 99.3)))
                    ax.imshow(np.arcsinh((img - med) / (2.0 * mad)), origin="lower", cmap="RdBu_r", vmin=-np.arcsinh(v / (2.0 * mad)), vmax=np.arcsinh(v / (2.0 * mad)))
                else:
                    disp = np.arcsinh(np.maximum(0.0, (img - med)) / (2.0 * mad))
                    vmax = float(np.percentile(disp[np.isfinite(disp)], 99.5))
                    ax.imshow(disp, origin="lower", cmap="viridis", vmin=0.0, vmax=max(0.5, vmax))
                cy, cx = img.shape[0] // 2, img.shape[1] // 2
                ax.plot([cx], [cy], marker="+", ms=9, color="#00ff88" if kind != "Difference" else "black", mew=1.2)
            if r_idx == 0:
                ax.set_title(kind, fontsize=10.5, fontweight="bold")
            if c_idx == 0:
                ax.set_ylabel(title_lbl, fontsize=8.2, fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])

    fig.suptitle("Official LSST FITS Cutout Vetting Gallery (Fink /api/v1/cutouts)", fontsize=12.0, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    save_both(fig, "figR05_fits_cutout_vetting_gallery.png")


def make_fig6(summary, r2_stars, r2_matches):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.0), gridspec_kw={"width_ratios": [1.0, 1.15]})

    # Panel 1: R2 Southern Catalog Breakdown by Declination Band & Match Outcome
    decs = np.array([float(r["dec_deg"]) for r in r2_stars])
    dists = np.array([min(2000.0, max(1.0, float(r["dist_pc"]))) for r in r2_stars])
    near_10 = np.array([r["within_10pc"] == "True" for r in r2_stars])
    ax1.scatter(decs[~near_10], dists[~near_10], s=18, c="#4c78a8", alpha=0.65, label=f"d > 10 pc ({int(np.sum(~near_10))} stars)")
    ax1.scatter(decs[near_10], dists[near_10], s=26, c="#54a24b", alpha=0.80, label=f"Solar Neighborhood <=10 pc ({int(np.sum(near_10))} stars)")
    if r2_matches:
        m0 = r2_matches[0]
        ax1.scatter([float(m0["star_dec_deg"])], [float(m0["dist_pc"])], s=140, marker="*", c="#ffbf00", ec="black", lw=0.8, zorder=7,
                    label=f"Match <=10\": {m0['star']} (9.59\" offset, clean)")
        ax1.annotate(f"{m0['star']} (23.6 pc)\n1 Fink src @ 9.59\" offset",
                     xy=(float(m0["star_dec_deg"]), float(m0["dist_pc"])),
                     xytext=(float(m0["star_dec_deg"]) + 8, float(m0["dist_pc"]) * 3.8),
                     arrowprops=dict(arrowstyle="->", color="#b8860b", lw=1.2), fontsize=8.0,
                     bbox=dict(boxstyle="round,pad=0.25", fc="#fff9e6", ec="#d98b00"))
    ax1.set_yscale("log")
    ax1.set_xlim(-88, 18)
    ax1.set_ylim(1.0, 3500)
    ax1.set_xlabel("Declination [deg]")
    ax1.set_ylabel("Distance [pc] (Capped at 2,000 pc)")
    ax1.set_title("Spor R2: All 538 Southern SETI Stars Queried (100% HTTP 200)")
    ax1.text(-84, 1500, "537/538 = 0 Fink alerts\n(bright hosts saturate LSST r<=16\nor lack alerted transients)",
             fontsize=8.0, bbox=dict(boxstyle="round,pad=0.3", fc="#f4f6f9", ec="#7a8b99"))
    ax1.legend(loc="lower left", fontsize=7.8, framealpha=0.92)

    # Panel 2: Exact Analytical Bayesian f95 Upper Limits (k=0 Verified ETI)
    lim = summary["bayesian_limits"]
    regimes = [
        ("R1 /fp Flash Cond.\n(N_eval=254, N_eff=216.5)", "fp_flash_conditional"),
        ("R1 /fp Dim Cond.\n(N_eval=254, N_eff=202.6)", "fp_dim_conditional"),
        ("R1 /sources Flash Cond.\n(N_eval=85, N_eff=55.6)", "sources_flash_conditional"),
        ("R1 /sources Dim Cond.\n(N_eval=85, N_eff=43.5)", "sources_dim_conditional"),
        ("R1 /sources Dim Duty\n(N_eval=85, N_eff=6.66)", "sources_dim_duty_cycle"),
    ]
    yr = np.arange(len(regimes))
    unif = [lim[k]["uniform_f95_pct"] for _, k in regimes]
    jeff = [lim[k]["jeffreys_f95_pct"] for _, k in regimes]
    cp = [lim[k]["clopper_pearson_f95_pct"] for _, k in regimes]

    w = 0.25
    ax2.barh(yr - w, jeff, height=w, color="#4c78a8", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax2.barh(yr, unif, height=w, color="#f58518", label="Uniform Beta(1, N_eff+1)")
    ax2.barh(yr + w, cp, height=w, color="#54a24b", label="Clopper-Pearson")
    ax2.set_yticks(yr)
    ax2.set_yticklabels([r[0] for r in regimes], fontsize=7.9)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 44)
    ax2.set_xlabel("Bayesian 95% Prevalence Upper Limit f95 [%] (0 Verified ETI)")
    ax2.set_title("Rubin V2 Null Occurrence-Rate Bounds (After Cutout & FP Vetting)")
    for i, (jv, uv) in enumerate(zip(jeff, unif)):
        ax2.text(jv + 0.5, i - w, f"{jv:.2f}%", va="center", fontsize=7.4, color="#23456b", fontweight="bold")
        ax2.text(uv + 0.5, i, f"{uv:.2f}%", va="center", fontsize=7.4, color="#a85506")
    ax2.legend(loc="upper right", fontsize=8.0, framealpha=0.94)

    fig.tight_layout()
    save_both(fig, "figR06_r2_catalog_crossmatch_and_bayesian_f95.png")


def main() -> int:
    stats, summary, r1_cohort, r1_src_sum, triage, r2_stars, r2_matches, vet, raw_src, raw_fp = load_all_data()
    make_fig1(stats, r2_stars, r2_matches)
    make_fig2(r1_cohort, r1_src_sum, triage, summary)
    make_fig3(summary, raw_src, r1_cohort)
    make_fig4(raw_src, raw_fp)
    make_fig5(vet)
    make_fig6(summary, r2_stars, r2_matches)
    print("Generated all 6 300-DPI figures (figR01-figR06).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
