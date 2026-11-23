#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D102 (V6.0) Publication Figure Generator (fig103-fig108, 240 DPI).
Reads strictly from D102 Stage-2 results and bounded_inputs/d102_bounded_bundle.json.gz.
Deterministic PNG output (`metadata={}`) across clean-room re-renders.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 8.4,
    "axes.titlesize": 9.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.5,
    "xtick.labelsize": 7.4,
    "ytick.labelsize": 7.4,
    "legend.fontsize": 6.9,
    "figure.facecolor": "white",
    "axes.facecolor": "#fbfcfd",
    "axes.edgecolor": "#4a5568",
    "grid.color": "#cbd5e0",
})


def _read_csv(res_dir: Path, name: str) -> list[dict[str, str]]:
    with (res_dir / name).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fmt_power_kw(v: float) -> str:
    if v < 1e-4:
        return f"{v * 1e6:.2f} mW"
    if v < 1.0:
        return f"{v * 1e3:.2f} W"
    if v < 100.0:
        return f"{v:.3f} kW"
    return f"{v:.1f} kW"


def _save(fig: plt.Figure, fig_dir: Path, fname: str) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    out = fig_dir / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14, metadata={})
    plt.close(fig)
    print(f"[FIG] Wrote {out.name} ({out.stat().st_size:,} B)")


def _cal_bars(
    ax: plt.Axes,
    cal_rows: list[dict[str, str]],
    title: str,
    replace_map: dict[str, str] | None = None,
    class_col: str = "class",
) -> None:
    cls_counts: dict[str, list[int]] = {}
    for r in cal_rows:
        c = r[class_col]
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    c_names = list(cls_counts.keys())
    c_rates = [100.0 * cls_counts[k][0] / max(1, cls_counts[k][1]) for k in c_names]
    short_c = []
    for k in c_names:
        lbl = k.replace("_VETO", "")
        if replace_map:
            for a, b in replace_map.items():
                lbl = lbl.replace(a, b)
        short_c.append(lbl.replace("_", "\n"))
    palette = ["#1b9e77", "#7570b3", "#d95f02", "#636363", "#2b8cbe", "#e7298a", "#a6761d"]
    bars = ax.bar(
        np.arange(len(c_names)), c_rates,
        color=[palette[i % len(palette)] for i in range(len(c_names))],
        edgecolor="black", lw=0.7,
    )
    ax.set_ylim(0.0, 120.0)
    ax.set_xticks(np.arange(len(c_names)))
    ax.set_xticklabels(short_c, fontsize=6.9)
    ax.set_ylabel("Calibration Pass Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, c_names):
        p, t = cls_counts[k]
        ax.text(
            b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0,
            f"{p}/{t}", ha="center", va="bottom", fontsize=7.5, fontweight="bold",
        )
    ax.grid(True, axis="y", alpha=0.25)


def fig103_chandra_xray_poisson(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    ch_obs = _read_csv(res_dir, "CHANDRA_XRAY_POISSON_24OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V60_CHANDRA_POISSON_240.csv")
    sc = _read_csv(res_dir, "V6_0_SPACE_CANDIDATE_LEDGER.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Archival EV Lac Chandra HETG MEG +1 vs -1 Coincidence Spectrum
    ev_rec = next(e for e in bundle["exposures"] if e["star"] == "EVLAC" and e["instrument"] == "CHANDRA_HETG")
    arm_meg = ev_rec["arms"].get("MEG") or next(iter(ev_rec["arms"].values()))
    w_meg = az._decode_arr_any(arm_meg["wave_a_c"])
    p_meg = az._decode_arr_any(arm_meg["plus_cts_c"])
    m_meg = az._decode_arr_any(arm_meg["minus_cts_c"])
    mask_m = (w_meg >= 5.0) & (w_meg <= 24.0)
    ord_m = np.argsort(w_meg[mask_m])
    wx = w_meg[mask_m][ord_m]
    ax1.step(wx, p_meg[mask_m][ord_m], where="mid", color="#2b8cbe", lw=0.95, alpha=0.9, label="Order m=+1 Counts")
    ax1.step(wx, -m_meg[mask_m][ord_m], where="mid", color="#d95f02", lw=0.95, alpha=0.85, label="Order m=-1 (-Counts)")
    ax1.axhline(0.0, color="black", lw=0.7)
    for w_ln, lbl in [(12.13, "Ne X 12.1A"), (15.01, "Fe XVII 15.0A"), (18.97, "O VIII 19.0A"), (21.60, "O VII 21.6A")]:
        ax1.axvline(w_ln, color="#718096", ls="--", lw=0.75, alpha=0.75)
        ax1.text(w_ln + 0.14, np.nanmax(p_meg[mask_m]) * 0.88, lbl, rotation=90, va="top", ha="left", fontsize=6.5, color="#2d3748")
    ax1.set_xlim(5.0, 24.0)
    ax1.set_xlabel("Wavelength (Angstrom)")
    ax1.set_ylabel("Dispersion Counts (+1 Top / -1 Bottom)")
    ax1.set_title("A. Archival Chandra HETG/MEG +1/-1 Coincidence Spectrum (EV Lac, 100.0 ks)")
    ax1.legend(loc="lower right", fontsize=6.9, frameon=True)
    ax1.grid(True, alpha=0.22)

    # Panel B: CALIBRATION_V60_CHANDRA_POISSON_240
    _cal_bars(
        ax2, cal,
        "B. Chandra Poisson Li & Ma (1983) Calibration (238/240 = 99.17%; 0/180 FA)",
        replace_map={"CLEAN_XRAY_BEACON": "Clean X-Ray\nBeacon", "SINGLE_ORDER_HOTPIX": "1-Order\nHotpix", "CORONAL_ATLAS": "Coronal\nAtlas", "POISSON_NULL": "Poisson\nNull", "BROAD_WIND": "Broad\nWind"},
    )

    # Panel C: Sorted Nearby & Disk Chandra 10-m EIRP Bounds (exclude far >1e5 pc AGN clutter on label axis or show best 18 + annotations cleanly)
    ch_sorted = sorted(ch_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:18]
    y3 = np.arange(len(ch_sorted))
    vals3 = [float(r["p_beam_10m_kw"]) for r in ch_sorted]
    cols3 = ["#2b8cbe" if r["instrument"] == "CHANDRA_HETG" else "#1b9e77" for r in ch_sorted]
    ax3.barh(y3, vals3, color=cols3, edgecolor="black", lw=0.5)
    ax3.set_yticks(y3)
    ax3.set_yticklabels([f"{r['star']} ({'HETG' if 'HETG' in r['instrument'] else 'LETG'})" for r in ch_sorted], fontsize=6.8)
    ax3.set_xscale("log")
    ax3.invert_yaxis()
    ax3.set_xlim(2e-7, max(vals3) * 18.0)
    for yi, r in enumerate(ch_sorted):
        v = float(r["p_beam_10m_kw"])
        ax3.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.4, fontweight="bold")
    ax3.set_xlabel("Poisson 6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    ax3.set_title("C. Nearest 18 Chandra HETG+LETG EIRP Limits (Best: EV Lac 0.60 mW @ 2 A)")
    ax3.grid(True, axis="x", which="both", alpha=0.22)

    # Panel D: Chandra Candidate & Veto Funnel across 24 ObsIDs
    ch_cands = [r for r in sc if r["instrument"].startswith("CHANDRA_")]
    n_tot_c = len(ch_cands)
    n_g4 = sum(1 for r in ch_cands if "G4_CHANDRA_ORDER_COINCIDENCE" not in r["stage2_triage_status"])
    n_g3 = sum(1 for r in ch_cands if "G4_CHANDRA_ORDER_COINCIDENCE" not in r["stage2_triage_status"] and "G3_XRAY_CORONAL_ATLAS" not in r["stage2_triage_status"])
    n_g5 = sum(1 for r in ch_cands if r["qualified_v60"] == "True")
    n_eti = sum(1 for r in ch_cands if int(r["verified_eti"]) > 0)
    f_lbls = ["Raw Li&Ma\n>=6 sigma", "Pass G4\n(+1/-1 Ord)", "Pass G3\n(Not Coronal)", "Pass G5\n(Pre-S2 Qual)", "Stage-2\nVerified ETI"]
    f_vals = [n_tot_c, n_g4, n_g3, n_g5, n_eti]
    f_cols = ["#636363", "#d95f02", "#7570b3", "#2b8cbe", "#1b9e77"]
    bars4 = ax4.bar(np.arange(len(f_lbls)), f_vals, color=f_cols, edgecolor="black", lw=0.7)
    ax4.set_xticks(np.arange(len(f_lbls)))
    ax4.set_xticklabels(f_lbls, fontsize=7.2)
    ax4.set_ylim(0, n_tot_c * 1.18)
    ax4.set_ylabel("X-Ray Candidate Count")
    ax4.set_title(f"D. 24-ObsID Chandra G3/G4/G5 + Stage-2 Funnel (596 Raw / {n_tot_c} Ledger -> 0 ETI)")
    for b, fv in zip(bars4, f_vals):
        ax4.text(b.get_x() + b.get_width() / 2.0, fv + n_tot_c * 0.02, str(fv), ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax4.grid(True, axis="y", alpha=0.25)

    fig.suptitle("Phase D102 (V6.0): NASA Chandra HETG/LETG X-Ray Grating Poisson Search (24 ObsIDs; 1.2-175 A; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig103_d102_chandra_xray_poisson_24obs.png")


def fig104_euve_extreme_uv(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    eu_obs = _read_csv(res_dir, "EUVE_EXTREME_UV_24OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V60_EUVE_180.csv")
    spec_a = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D102.json").read_text())

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Unbroken High-Energy Continuity (0.00012-0.06998 um = 9.186 octaves) + ISM H Wall
    bands_he = [
        ("Chandra HEG\n(1.2-16 A)", 1.201, 16.0, "#2b8cbe"),
        ("Chandra MEG\n(2.5-31.5 A)", 2.50, 31.498, "#1f78b4"),
        ("Chandra LETG\n(1.2-175 A)", 1.206, 174.994, "#1b9e77"),
        ("EUVE DS/S\n(70.05-699.8 A)", 70.05, 699.80, "#7570b3"),
        ("IUE / HST Lyman\n(>=905 A)", 905.0, 1600.0, "#636363"),
    ]
    ax1.axvspan(70.05, 174.994, color="#c6f6d5", alpha=0.65, label="LETG + EUVE Overlap (70-175 A)")
    ax1.axvspan(699.80, 905.0, color="#fed7d7", alpha=0.75, label="ISM H Photoionization Wall (700-905 A)")
    for yi, (lbl, a_lo, a_hi, col) in enumerate(bands_he):
        ax1.plot([a_lo, a_hi], [yi, yi], color=col, lw=8.0, solid_capstyle="butt")
    ax1.set_yticks(np.arange(len(bands_he)))
    ax1.set_yticklabels([b[0] for b in bands_he], fontsize=7.2)
    ax1.set_xscale("log")
    ax1.set_xlim(0.8, 2200.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Wavelength (Angstrom, log scale)")
    ax1.set_title(f"A. Unbroken X-Ray-to-EUV Continuity ({spec_a['high_energy_unbroken_octaves']:.3f} Octaves to ISM H Edge)")
    ax1.legend(loc="lower left", fontsize=7.0, frameon=True)
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Archival EUVE Spectrum (AD Leo or V711 Tau / HD22468) with geocoronal + coronal vetoes
    eu_rec = next((e for e in bundle["exposures"] if e["instrument"] == "EUVE_DS_S" and e["star"] == "AUMIC"), None) or next(e for e in bundle["exposures"] if e["instrument"] == "EUVE_DS_S")
    we = az._decode_arr_any(eu_rec["wave_a_c"])
    fe = az._decode_arr_any(eu_rec["flux_cgs_c"])
    ok_e = np.isfinite(we) & np.isfinite(fe) & (we >= 75.0) & (we <= 650.0)
    ax2.plot(we[ok_e], np.maximum(fe[ok_e], -1e-13) * 1e12, color="#4a5568", lw=0.75, label=f"{eu_rec['star']} EUVE DS/S")
    ax2.axvspan(297.0, 311.0, color="#fed7d7", alpha=0.70, label="Geocoronal He II 304 A Veto")
    ax2.axvspan(576.0, 592.0, color="#feebc8", alpha=0.75, label="Geocoronal He I 584 A Veto")
    for c_w, clbl in [(108.4, "Fe XIX"), (142.2, "Fe XXI"), (172.2, "O V"), (284.1, "Fe XV"), (335.4, "Fe XVI")]:
        ax2.axvline(c_w, color="#7570b3", ls=":", lw=0.8, alpha=0.8)
        ax2.text(c_w + 3.0, np.nanmax(fe[ok_e]) * 1e12 * 0.90, clbl, rotation=90, va="top", fontsize=6.4, color="#553c9a")
    ax2.set_xlim(75.0, 650.0)
    ax2.set_xlabel("Wavelength (Angstrom)")
    ax2.set_ylabel("Flux (10^-12 erg/cm^2/s/A)")
    ax2.set_title(f"B. Archival EUVE Spectrum ({eu_rec['star']}): Coronal Lines & Geocoronal Walls")
    ax2.legend(loc="upper right", fontsize=6.6, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: CALIBRATION_V60_EUVE_180
    _cal_bars(
        ax3, cal,
        "C. EUVE EUV Narrow-Line + Coronal Calibration (180/180 = 100.0%)",
        replace_map={"CLEAN_EUV_BEACON": "Clean EUV\nBeacon", "GEOCORONAL_AIRGLOW": "Geocoronal\nAirglow", "CORONAL_ATLAS": "Coronal\nAtlas", "SPIKE_OR_SEAM": "Spike &\nSeam"},
    )

    # Panel D: Top 16 Nearest EUVE EIRP Bounds
    eu_sorted = sorted(eu_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(eu_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in eu_sorted]
    ax4.barh(y4, vals4, color="#7570b3", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in eu_sorted], fontsize=6.9)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.4, max(vals4) * 22.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.4, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    ax4.set_title("D. Best 16 EUVE 10-m EIRP Bounds (Proxima 0.41 W, alp Cen A 0.42 W)")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D102 (V6.0): NASA EUVE Extreme-UV Survey (24 Targets; 70-700 A; 9.186 Unbroken Octaves; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig104_d102_euve_extreme_uv_and_letg_overlap.png")


def fig105_alma_mm_unbroken_seams(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    alma_rows = _read_csv(res_dir, "ALMA_MM_SEAMS_D102.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_0_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"].startswith("ALMA_")]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Frequency Coverage across all 22 ALMA_V60 Cubes + D101 Band Map (B3..B8)
    ax1.axvspan(50.0, 68.0, color="#fed7d7", alpha=0.65, label="O2 60 GHz Opaque")
    ax1.axvspan(115.8, 125.0, color="#feebc8", alpha=0.75, label="O2 118.75 GHz Wall")
    band_cfg = {
        "ALMA_B3_3MM": ("B3 (84-95 GHz)", "#d95f02"),
        "ALMA_B4_2MM": ("B4 (125-175 GHz)", "#2b8cbe"),
        "ALMA_B5_2MM": ("B5 (175-197 GHz)", "#1b9e77"),
        "ALMA_B6_1MM": ("B6 (211-246 GHz)", "#7570b3"),
        "ALMA_B7_0P9MM": ("B7 (333-344 GHz)", "#e7298a"),
        "ALMA_B8_0P7MM": ("B8 (482-484 GHz)", "#b30000"),
    }
    rows_s = sorted(alma_rows, key=lambda r: (r["instrument"], float(r["min_freq_ghz"])))
    seen_b = set()
    for yi, r in enumerate(rows_s):
        f0, f1 = float(r["min_freq_ghz"]), float(r["max_freq_ghz"])
        lbl, col = band_cfg[r["instrument"]]
        use_l = lbl if r["instrument"] not in seen_b else None
        seen_b.add(r["instrument"])
        ax1.plot([f0, f1], [yi, yi], color=col, lw=4.5, label=use_l)
        if abs(f1 - f0) < 5.0:
            ax1.scatter([(f0 + f1) / 2.0], [yi], color=col, s=24, edgecolor="black", lw=0.4, zorder=4)
    ax1.set_yticks(np.arange(len(rows_s)))
    ax1.set_yticklabels([r["star"] for r in rows_s], fontsize=6.3)
    ax1.set_xlim(30.0, 515.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Observing Frequency (GHz)")
    ax1.set_title("A. All 22 ALMA_V60 Cubes Across Bands 3, 4, 5, 6, 7 & B8 NGC7469 (482.6 GHz)")
    ax1.legend(loc="upper right", fontsize=6.4, frameon=True, ncol=2)
    ax1.grid(True, axis="x", alpha=0.22)

    # Panel B: Spatial Compactness vs OFF-Source Annulus Ratio for all 25 ALMA Peaks
    ratios = [float(r["spatial_fwhm_ratio"]) for r in sc]
    offs = [float(r["off95_to_on"]) for r in sc]
    ax2.fill_between([0.75, 1.35], -0.02, 0.22, color="#c6f6d5", alpha=0.55, label="Unresolved Point-Source Pass Box")
    ax2.scatter(ratios, offs, s=44, c=["#e7298a" if "B7" in r["instrument"] else "#2b8cbe" for r in sc], edgecolor="black", lw=0.5, zorder=4, label=f"25 Raw ALMA Peaks (0 Verified ETI)")
    ax2.axvline(1.35, color="#b30000", ls="--", lw=1.0)
    ax2.axhline(0.22, color="#b30000", ls="--", lw=1.0)
    ax2.set_xlim(0.7, max(max(ratios) * 1.15, 3.0))
    ax2.set_ylim(-0.04, max(max(offs) * 1.12, 0.9))
    ax2.set_xlabel("Spatial FWHM Ratio (Observed / Synthesized Beam)")
    ax2.set_ylabel("OFF-Annulus 95th Percentile / ON-Beam Peak")
    ax2.set_title("B. ALMA G4+G6 Spatial Compactness & Annulus Veto (25 Raw -> 0 ETI)")
    ax2.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: CALIBRATION_V59_ALMA_INTERFEROMETRIC_240
    _cal_bars(
        ax3, cal,
        "C. ALMA Interferometric Calibration (239/240 = 99.58%; 60/60 Clean)",
        replace_map={"CLEAN_ALMA_BEACON": "Clean\nALMA", "EXTENDED_DISK_GAS": "Extended\nDisk", "OFFSOURCE_BIRDIE": "Off-Source\nBirdie", "MM_MOLECULAR_ATLAS": "Mol.\nAtlas", "SINGLE_CHAN_GIBBS": "Single-Ch\nGibbs"},
    )

    # Panel D: Archival ALMA B8 NGC7469 or B7 Fomalhaut / B6 AU Mic ON-beam vs OFF-95% profile
    fom_rec = next((e for e in bundle["exposures"] if e["star"] == "FOMALHAUT" and e["instrument"] == "ALMA_B7_0P9MM"), None) or next(e for e in bundle["exposures"] if e["instrument"].startswith("ALMA_"))
    f_arr = az._decode_arr_any(fom_rec["freq_ghz_c"])
    s_on = az._decode_arr_any(fom_rec["s_on_jy_c"]) * 1000.0
    s_off95 = az._decode_arr_any(fom_rec["s_off_95_jy_c"]) * 1000.0
    ax4.plot(f_arr, s_on, color="#2b8cbe", lw=1.1, label="ON-Target Synthesized Beam (mJy)")
    ax4.plot(f_arr, s_off95, color="#d95f02", lw=0.95, alpha=0.85, label="OFF-Source Annulus 95% (mJy)")
    ax4.axhline(0.0, color="black", lw=0.6)
    ax4.set_xlabel("Frequency (GHz)")
    ax4.set_ylabel("Flux Density (mJy / beam)")
    ax4.set_title(f"D. Archival ALMA Profile: {fom_rec['star']} ({fom_rec['instrument'].replace('_', ' ')}; Clean Noise Ceiling)")
    ax4.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax4.grid(True, alpha=0.22)

    fig.suptitle("Phase D102 (V6.0): ALMA_V60 Unbroken Millimeter Closure & Band-8 Frontier (22 Cubes; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig105_d102_alma_mm_unbroken_seams_and_b8.png")


def fig106_drift_and_comb_54campaigns(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6.csv")
    ek54 = _read_csv(res_dir, "DRIFT_V60_ECCENTRIC_KEPLERIAN_54CAMPAIGNS.csv")
    cd54 = _read_csv(res_dir, "COMB_DRIFT_V60_54CAMPAIGNS.csv")
    cal_dc = _read_csv(res_dir, "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Drifting-Comb V6.0 Calibration vs Static V4.1 Baseline
    cls_map: dict[str, list[int]] = {}
    for r in cal_dc:
        c = r["class"]
        cls_map.setdefault(c, [0, 0])
        cls_map[c][0] += int(r["passed"])
        cls_map[c][1] += 1
    lbls_a = ["V6.0 Kepler\nComb (60)", "V6.0 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
    vals_a = [
        100.0 * cls_map["KEPLERIAN_DRIFTING_COMB"][0] / cls_map["KEPLERIAN_DRIFTING_COMB"][1],
        100.0 * cls_map["LINEAR_ACCEL_DRIFTING_COMB"][0] / cls_map["LINEAR_ACCEL_DRIFTING_COMB"][1],
        100.0 * sum(int(r["v41_static_obs"]) for r in cal_dc[:120]) / 120.0,
        100.0 * cls_map["STATIONARY_ETALON_COMB_VETO"][0] / cls_map["STATIONARY_ETALON_COMB_VETO"][1],
        100.0 * cls_map["SINGLE_EPOCH_TRANSIENT_COMB_VETO"][0] / cls_map["SINGLE_EPOCH_TRANSIENT_COMB_VETO"][1],
        100.0 * cls_map["BERV_SKY_OR_NOISE_COMB_VETO"][0] / cls_map["BERV_SKY_OR_NOISE_COMB_VETO"][1],
    ]
    txt_a = [
        f"{cls_map['KEPLERIAN_DRIFTING_COMB'][0]}/{cls_map['KEPLERIAN_DRIFTING_COMB'][1]}",
        f"{cls_map['LINEAR_ACCEL_DRIFTING_COMB'][0]}/{cls_map['LINEAR_ACCEL_DRIFTING_COMB'][1]}",
        f"{sum(int(r['v41_static_obs']) for r in cal_dc[:120])}/120",
        f"{cls_map['STATIONARY_ETALON_COMB_VETO'][0]}/{cls_map['STATIONARY_ETALON_COMB_VETO'][1]}",
        f"{cls_map['SINGLE_EPOCH_TRANSIENT_COMB_VETO'][0]}/{cls_map['SINGLE_EPOCH_TRANSIENT_COMB_VETO'][1]}",
        f"{cls_map['BERV_SKY_OR_NOISE_COMB_VETO'][0]}/{cls_map['BERV_SKY_OR_NOISE_COMB_VETO'][1]}",
    ]
    bars1 = ax1.bar(np.arange(6), vals_a, color=["#1b9e77", "#2b8cbe", "#b30000", "#7570b3", "#d95f02", "#636363"], edgecolor="black", lw=0.7)
    ax1.set_xticks(np.arange(6))
    ax1.set_xticklabels(lbls_a, fontsize=6.9)
    ax1.set_ylim(0, 120)
    ax1.set_ylabel("Detection / Rejection Rate (%)")
    ax1.set_title("A. Coherent Drifting-Comb Calibration (236/240 = 98.33% vs 9.2% Static V4.1)")
    for b, t in zip(bars1, txt_a):
        ax1.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, t, ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax1.grid(True, axis="y", alpha=0.25)

    # Panel B: Live Orbital Campaigns #157-#162 Planetary RV Curves (in m/s for clarity)
    pal = ["#b30000", "#2b8cbe", "#1b9e77", "#d95f02", "#7570b3", "#636363"]
    for idx_o, r in enumerate(o6):
        st = r["star"]
        om = orb_json["campaigns"][st]
        ph = np.linspace(0.01, 0.99, 250)
        p_d = float(om["orb_per_days"])
        e_v = float(om["orb_ecc"])
        w_r = math.radians(float(om["orb_omega_deg"]))
        kp = float(om["kp_kms"])
        vr_ms = 1000.0 * np.asarray([float(det_mod.solve_kepler_eccentric_rv(np.array([p_i * p_d]), p_d, e_v, w_r, 0.0, kp)[0]) for p_i in ph], dtype=np.float64)
        ax2.plot(ph, vr_ms, lw=1.65, color=pal[idx_o % len(pal)], label=f"#{r['campaign_index']} {st} (P={p_d:.1f}d, e={e_v:.2f}, Kp={kp*1e3:.2f} m/s)")
    ax2.set_ylim(-5.8, 4.6)
    ax2.set_xlabel("Orbital Phase phi")
    ax2.set_ylabel("Planetary Keplerian RV (m/s)")
    ax2.set_title("B. ESO ESPRESSO + HARPS Orbits #157-#162 (Including GJ 163 e=0.373, 5,027 d)")
    ax2.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: All 54 Cumulative DRIFT_V60 Campaigns
    x54 = np.arange(len(ek54))
    ax3.bar(x54, [int(r["n_trajectories_evaluated"]) for r in ek54], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x54, [int(r["raw_coherent_survivors"]) for r in ek54], color="#2b8cbe", edgecolor="black", lw=0.4, label="Raw Survivors (15,186)")
    ax3.bar(x54, [int(r["stage2_verified_eti"]) for r in ek54], color="#1b9e77", label="Verified ETI (0/54)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek54) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D102, 7-12 D101, 13-18 D100, ..., 50-54 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    ax3.set_title(f"C. 54-Campaign DRIFT_V60 ({sum_raw['drift_v60_54campaigns_trajectories']:,} Traj / {sum_raw['drift_v60_54campaigns_pixel_integrals']/1e9:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 54 Cumulative COMB_DRIFT_V60 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd54])
    qual_cd = np.asarray([int(r["comb_qualified_v60"]) for r in cd54])
    ax4.plot(x54, raw_cd, "-o", ms=3.2, color="#d95f02", lw=1.1, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v60_54campaigns_raw_candidates']:,})")
    ax4.plot(x54, qual_cd, "-s", ms=3.2, color="#7570b3", lw=1.1, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v60_54campaigns_qualified_pre_stage2']})")
    ax4.plot(x54, np.zeros_like(x54), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/54)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#54 Across D094-D102)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 54-Campaign COMB_DRIFT_V60 ({sum_raw['comb_drift_v60_54campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax4.grid(True, alpha=0.22)

    fig.suptitle("Phase D102 (V6.0): Orbits #157-#162 & 54-Campaign Coherent DRIFT_V60 + COMB_DRIFT_V60 (7.24B Pixel Integrals; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig106_d102_drift_v60_and_comb_54campaigns.png")


def fig107_panchromatic_26octaves(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json["unified_656star_panchromatic_v6_0_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp102 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D102.csv")
    ell = _read_csv(res_dir, "MULTIEVENT_ELLIPSOID_656STARS.csv")
    s183 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_183STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 0.00012-8,556.42 um (26.086 Octaves) Sensitivity Frontier
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Photoionization Wall (700-905 A)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D102" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=9, color="#bdbdbd", alpha=0.50, zorder=1, label="D079-D101 (0.0905-8,556.4 um)")

    inst_groups = [
        ("CHANDRA_HETG", "#1a365d", "^", "D102 Chandra HETG (0.12-3.1 nm)"),
        ("CHANDRA_LETG", "#2b8cbe", "v", "D102 Chandra LETG (0.12-17.5 nm)"),
        ("EUVE_DS_S", "#7570b3", "P", "D102 EUVE (7-70 nm)"),
        ("ESO_ESPRESSO", "#1b9e77", "o", "D102 ESPRESSO (0.42-0.76 um)"),
        ("ESO_HARPS", "#66a61e", "s", "D102 HARPS (0.41-0.58 um)"),
        ("ALMA_B8_0P7MM", "#b30000", "*", "D102 ALMA B8 (621 um)"),
        ("ALMA_B7_0P9MM", "#e7298a", "D", "D102 ALMA B7 (871-901 um)"),
        ("ALMA_B6_1MM", "#d95f02", "d", "D102 ALMA B6 (1.22-1.42 mm)"),
        ("ALMA_B5_2MM", "#a6761d", "p", "D102 ALMA B5 (1.52-1.71 mm)"),
        ("ALMA_B4_2MM", "#2c5282", "h", "D102 ALMA B4 (1.71-2.40 mm)"),
        ("ALMA_B3_3MM", "#718096", "X", "D102 ALMA B3 (3.17-3.56 mm)"),
    ]
    for ik, col, mk, lbl in inst_groups:
        sub = [r for r in eirp102 if r["instrument"] == ik]
        ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=24 if mk != "*" else 56, color=col, marker=mk, edgecolor="black", lw=0.3, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(7e-5, 25000.0)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma 10-m EIRP Limit (kW)")
    ax1.set_title("A. Unified 45-Spectrograph Sensitivity Frontier (26.086 Octaves)")
    ax1.legend(loc="lower right", fontsize=5.4, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-656 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V5_9_PHASES_SNAPSHOT.json").read_text())["prior_unified_613_rows"]}
    all102_st = {e["star"] for e in bundle["exposures"]}
    brand43 = all102_st - prior_st
    bridges24 = all102_st & prior_st
    ra_p, dec_p, ra_b, dec_b, ra_n, dec_n = [], [], [], [], [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand43:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in bridges24:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D101 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D102 Bridges / Revisited ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D102 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.9, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: <10 pc Solar Neighborhood (183 Stars)
    lims10 = [float(r["min_panchromatic_10m_kw"]) for r in s183 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med10 = float(np.median(lims10))
    ax3.hist(np.log10(lims10), bins=24, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax3.axvline(math.log10(med10), color="#b30000", ls="--", lw=1.6, label=f"Median: {med10:.4f} kW ({len(s183)} stars <10 pc)")
    ax3.set_xlabel("log10(Minimum Panchromatic 10-m EIRP Limit / kW)")
    ax3.set_ylabel("Target Count")
    ax3.set_title(f"C. Solar Neighborhood (<10 pc, {len(s183)} Stars; Best 0.60 mW @ Chandra HETG)")
    ax3.legend(loc="upper left", fontsize=7.0, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: All 13 D102 Calibration Suites (2,691 Trials; 51,417 Cumulative)
    cal_sum = s_json["synthetic_calibration_2691_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V60_", "V6.0 ")
        .replace("CALIBRATION_V59_", "V5.9 ")
        .replace("CALIBRATION_V58_", "")
        .replace("CALIBRATION_", "")
        .replace("DETECTOR_V58_", "")
        .replace("_CALIBRATION", "")
        .replace("_", " ")
        for k in s_names
    ]
    y4 = np.arange(len(s_names))
    ax4.barh(y4, s_pcts, color=["#b30000" if "V6.0" in s else "#2b8cbe" for s in short_s], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(short_s, fontsize=6.1)
    ax4.set_xlim(92.0, 102.0)
    ax4.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax4.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=6.1, color="white", fontweight="bold")
    ax4.set_xlabel("Suite Pass Rate (%)")
    ax4.set_title(f"D. D102 13-Suite Calibration ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d102']:,})")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle(f"Phase D102 (V6.0): {syn['unique_stars_total']} Stellar Systems Across {syn['total_octave_span']} Octaves ({syn['high_energy_unbroken_octaves']} X-Ray/EUV + {syn['lyman_to_mm_b4_low_octaves']} Lyman-mm -> 8,556.42 um; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig107_d102_global_26p09_octave_panchromatic_frontier.png")


def fig108_bridge_synthesis(res_dir: Path, fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    syn = s_json["unified_656star_panchromatic_v6_0_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    u656 = _read_csv(res_dir, "UNIFIED_PANCHROMATIC_V6_0_SYNTHESIS_656STARS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.0, 6.8))
    fig.subplots_adjust(wspace=0.35, top=0.84, bottom=0.16)

    # Panel A: X-Ray -> EUV -> UV -> Optical -> NIR -> Mid-IR -> Far-IR/Sub-mm -> ALMA mm Bridge Heatmap
    focus = [
        "PROXIMACEN", "EVLAC", "AUMIC", "ALPCENA", "61CYGB", "EPSERI",
        "ADLEO", "LALANDE21185", "WOLF359", "SIRIUS", "PROCYON", "TAUCET",
        "FOMALHAUT", "TWHYA", "IMLUP", "HD101584", "HD139614",
    ]
    new_d102_br = {r["star"] for r in b_rows if r["phase_id"] == "D102"}
    reg_bins = [
        ("X-Ray\n(0.1-7nm)", 0.0001, 0.007),
        ("EUV\n(7-70nm)", 0.007, 0.07),
        ("UV\n(0.09-0.38)", 0.07, 0.38),
        ("Opt\n(0.38-0.95)", 0.38, 0.95),
        ("NIR\n(0.95-5)", 0.95, 5.0),
        ("Mid/Far-IR\n(5-600)", 5.0, 600.0),
        ("ALMA mm\n(0.6-8.6mm)", 600.0, 9000.0),
    ]
    mat = np.full((len(focus), len(reg_bins)), np.nan)
    for r in b_rows:
        st = r["star"]
        if st not in focus or not r.get("wave_um") or not r.get("p_beam_10m_kw"):
            continue
        i = focus.index(st)
        wu = float(r["wave_um"])
        pkw = float(r["p_beam_10m_kw"])
        for j, (_, lo, hi) in enumerate(reg_bins):
            if lo <= wu < hi:
                v = math.log10(max(1e-7, pkw))
                if not math.isfinite(mat[i, j]) or v < mat[i, j]:
                    mat[i, j] = v
    cmap = matplotlib.colormaps["viridis_r"].copy()
    cmap.set_bad(color="#f1f5f9")
    im = ax1.imshow(mat, aspect="auto", cmap=cmap, vmin=-6.5, vmax=7.5)
    ax1.set_xticks(np.arange(len(reg_bins)))
    ax1.set_xticklabels([rb[0] for rb in reg_bins], fontsize=6.4)
    ax1.set_yticks(np.arange(len(focus)))
    ax1.set_yticklabels([f"{st} *" if st in new_d102_br else st for st in focus], fontsize=7.0)
    for i in range(len(focus)):
        for j in range(len(reg_bins)):
            if math.isfinite(mat[i, j]):
                ax1.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center", fontsize=6.0, color="black" if mat[i, j] < 1.0 else "white", fontweight="bold")
    cb = fig.colorbar(im, ax=ax1, fraction=0.045, pad=0.03)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.5)
    ax1.set_title(f"A. D102 Panchromatic Bridges: X-Ray to 8.56mm ({syn['panchromatic_bridge_stars_total']} Sci Bridges; * = D102)")

    # Panel B: Cumulative Survey Trajectory D079-D102
    phase_order = ["D079", "D084", "D089", "D094", "D097", "D099", "D100", "D101", "D102"]
    x_lbls = ["D079\nV3", "D084\nV3.5", "D089\nV4.0", "D094\nV5.2", "D097\nV5.5", "D099\nV5.7", "D100\nV5.8", "D101\nV5.9", "D102\nV6.0"]
    milestones = [sum(1 for r in u656 if any(tok.strip() <= p_cap for tok in r["phases"].split("+"))) for p_cap in phase_order]
    ax2.plot(np.arange(len(phase_order)), milestones, "-o", color="#b30000", lw=2.3, ms=7.8, markeredgecolor="black")
    for xi, mv in enumerate(milestones):
        ax2.annotate(f"{mv}", xy=(xi, mv), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7.8, fontweight="bold")
    ax2.set_xticks(np.arange(len(phase_order)))
    ax2.set_xticklabels(x_lbls, fontsize=6.9)
    ax2.set_ylim(0.0, 820.0)
    ax2.set_ylabel("Cumulative Unique Analyzed Stars")
    ax2.set_title(f"B. Survey Growth D079-D102 ({syn['unique_stars_total']} Stars; {syn['companion_archives_total']} Archives A-Z, AA-AB; 0 ETI)")
    ax2.text(
        0.025, 0.59,
        f"Unified Survey Totals (D079-D102):\n"
        f"- {syn['unique_stars_total']} Stars ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)\n"
        f"- {syn['planet_host_stars_total']} Hosts / {syn['confirmed_exoplanets_total']} Exoplanets\n"
        f"- {syn['within_10pc_unique_stars']} <10 pc (med {syn['within_10pc_median_limit_kw']:.4f} kW)\n"
        f"- {syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms\n"
        f"- {syn['total_exposures_d079_d102']:,} Exposures ({syn['total_integration_hours_d079_d102']:.1f} h)\n"
        f"- {syn['total_calibration_trials_d079_d102']:,} Calibration Trials\n"
        f"- {syn['cumulative_orbital_campaigns']} Orbits | 54 DRIFT+COMB_DRIFT | {syn['cumulative_comb_stacks']} Stacks\n"
        f"- Verified ETI Detections: {syn['verified_eti_detections_total']}",
        transform=ax2.transAxes, fontsize=6.7,
        bbox=dict(boxstyle="round,pad=0.33", fc="#f8fafc", ec="#b30000"),
    )
    ax2.grid(True, alpha=0.25)

    fig.suptitle(f"Phase D102 (V6.0): {syn['panchromatic_bridge_stars_total']} Science Bridges ({syn['panchromatic_bridge_cells_total']} Cells), {syn['companion_archives_total']} Companion Archives & {syn['unique_stars_total']}-Star Synthesis", fontsize=10.9, fontweight="bold", y=0.97)
    _save(fig, fig_dir, "fig108_d102_656star_synthesis_bridges_and_calibrations.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", "--workspace-dir", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    if str(ws) not in sys.path:
        sys.path.insert(0, str(ws))
    import analyze as az
    import v6_0_detector as det

    bundle = json.loads(gzip.decompress((ws / "bounded_inputs" / "d102_bounded_bundle.json.gz").read_bytes()).decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig103_chandra_xray_poisson(res_dir, bundle, az, fig_dir)
    fig104_euve_extreme_uv(res_dir, bundle, az, fig_dir)
    fig105_alma_mm_unbroken_seams(res_dir, bundle, az, fig_dir)
    fig106_drift_and_comb_54campaigns(res_dir, orb_json, det, fig_dir)
    fig107_panchromatic_26octaves(res_dir, ws, bundle, fig_dir)
    fig108_bridge_synthesis(res_dir, fig_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
