#!/usr/bin/env python3
"""
Phase D099 (V5.7) Publication Figure Generator (fig85-fig90, 240 DPI).
Reads strictly from locked D099 outputs and bounded_inputs/d099_bounded_bundle.json.gz.
"""

from __future__ import annotations

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

WS99 = Path(__file__).resolve().parent
RES = WS99 / "results"
FIG_DIR = RES / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

if str(WS99) not in sys.path:
    sys.path.insert(0, str(WS99))

import analyze as az

plt.rcParams.update({
    "font.size": 8.5,
    "axes.titlesize": 9.8,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.8,
    "xtick.labelsize": 7.6,
    "ytick.labelsize": 7.6,
    "legend.fontsize": 7.3,
    "figure.facecolor": "white",
    "axes.facecolor": "#fbfcfd",
    "axes.edgecolor": "#4a5568",
    "grid.color": "#cbd5e0",
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fname: str) -> None:
    out = FIG_DIR / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
    print(f"[FIG] Wrote {out.name} ({out.stat().st_size:,} B)")


def fig85_jcmt_mm(bundle: dict[str, Any]) -> None:
    rows = _read_csv("JCMT_MM_HETERODYNE_18STARS.csv")
    cal = _read_csv("CALIBRATION_V57_JCMT_MM_180.csv")
    sp_cands = [r for r in _read_csv("V5_7_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"].startswith("JCMT")]
    exps = [e for e in bundle["exposures"] if e["instrument"].startswith("JCMT")]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.32, hspace=0.34)

    # Panel A: Real JCMT Spectra (OCETI 230 GHz 12CO J=2-1, IRC+10216 218 GHz, LKCA15 356.7 GHz)
    oceti_230 = next(e for e in exps if e["star"] == "OCETI" and "2013" in e["dp_id"])
    fq_230 = az._decode_wave_any(oceti_230["freq_ghz"]) if "u" in oceti_230["freq_ghz"] else az._decode_arr_any(oceti_230["freq_ghz"])
    tk_230 = az._decode_arr_any(oceti_230["temp_k"])
    m_230 = np.isfinite(fq_230) & np.isfinite(tk_230)
    dv_co = (fq_230[m_230] - 230.538) / 230.538 * -az.C_KMS
    ord_dv = np.argsort(dv_co)
    ax1.plot(dv_co[ord_dv], tk_230[m_230][ord_dv] + 2.0, lw=1.0, color="#b30000", label="O Ceti 230 GHz (+2 K; 12CO J=2-1, 79.8σ -> G3 Veto)")

    # Overlay IRC+10216 shifted onto velocity scale around central freq
    irc = next(e for e in exps if e["star"] == "IRC10216")
    fq_ir = az._decode_wave_any(irc["freq_ghz"]) if "u" in irc["freq_ghz"] else az._decode_arr_any(irc["freq_ghz"])
    tk_ir = az._decode_arr_any(irc["temp_k"])
    m_ir = np.isfinite(fq_ir) & np.isfinite(tk_ir)
    f0_ir = float(np.median(fq_ir[m_ir]))
    dv_ir = (fq_ir[m_ir] - f0_ir) / f0_ir * -az.C_KMS
    oi = np.argsort(dv_ir)
    ax1.plot(dv_ir[oi], tk_ir[m_ir][oi] + 13.5, lw=0.85, color="#2b8cbe", alpha=0.9, label="IRC+10216 218 GHz (+13.5 K, molecular forest)")

    # Overlay LkCa 15 HARP 356.7 GHz flat continuum noise floor
    lk = next(e for e in exps if e["star"] == "LKCA15")
    fq_lk = az._decode_wave_any(lk["freq_ghz"]) if "u" in lk["freq_ghz"] else az._decode_arr_any(lk["freq_ghz"])
    tk_lk = az._decode_arr_any(lk["temp_k"])
    m_lk = np.isfinite(fq_lk) & np.isfinite(tk_lk)
    f0_lk = float(np.median(fq_lk[m_lk]))
    dv_lk = (fq_lk[m_lk] - f0_lk) / f0_lk * -az.C_KMS
    ol = np.argsort(dv_lk)
    ax1.plot(dv_lk[ol], tk_lk[m_lk][ol] - 4.5, lw=0.75, color="#1b9e77", alpha=0.9, label="LkCa 15 HARP 356.7 GHz (-4.5 K, best HARP 2.04 GW)")
    ax1.set_xlim(-120.0, 120.0)
    ax1.set_ylim(-8.5, 22.0)
    ax1.set_xlabel("Relative Doppler Velocity Offset Δv (km/s)")
    ax1.set_ylabel("Antenna Temperature T_A* (K, offset)")
    ax1.set_title("A. JCMT Heterodyne Sub-mm/mm Spectra (O Ceti 12CO, IRC+10216, LkCa 15)")
    ax1.legend(loc="upper left", fontsize=6.9, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: 180-trial Calibration Suite by Class
    cls_counts = {}
    for r in cal:
        c = r["class"]
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    c_names = list(cls_counts.keys())
    c_rates = [100.0 * cls_counts[k][0] / cls_counts[k][1] for k in c_names]
    short_c = [k.replace("_VETO", "").replace("NARROW_MM_", "").replace("_", "\n") for k in c_names]
    bars = ax2.bar(np.arange(len(c_names)), c_rates, color=["#1b9e77", "#7570b3", "#d95f02", "#636363"], edgecolor="black", lw=0.7)
    ax2.set_ylim(0.0, 114.0)
    ax2.set_xticks(np.arange(len(c_names)))
    ax2.set_xticklabels(short_c, fontsize=7.6)
    ax2.set_ylabel("Calibration Pass Rate (%)")
    ax2.set_title("B. V5.7 JCMT Millimeter Calibration Suite (180/180 = 100.00%)")
    for b, k in zip(bars, c_names):
        p, t = cls_counts[k]
        ax2.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: Stage-2 Triage of all JCMT Raw Candidates
    jcmt_label_map = {
        "G2_JCMT_STANDING_WAVE_RIPPLE": "G2 JCMT Standing Wave Ripple",
        "G5_JCMT_BROAD_MOLECULAR_ENVELOPE": "G5 JCMT Broad Molecular Envelope",
        "G3_JCMT_MOLECULAR_ATLAS:12CO_J2-1": "G3 Molecular Atlas: 12CO J=2-1",
        "VERIFIED ETI": "Verified ETI",
    }
    vr_cnt = Counter(r["stage2_triage_status"].replace("STAGE2_VETO_", "") for r in sp_cands)
    vr_cnt["VERIFIED ETI"] = sum(int(r["verified_eti"]) for r in sp_cands)
    v_labels = list(vr_cnt.keys())
    v_vals = [vr_cnt[k] for k in v_labels]
    y3 = np.arange(len(v_labels))
    cols3 = ["#2b8cbe" if "ETI" not in k else "#b30000" for k in v_labels]
    ax3.barh(y3, v_vals, color=cols3, edgecolor="black", lw=0.6)
    ax3.set_yticks(y3)
    ax3.set_yticklabels([jcmt_label_map.get(k, k) for k in v_labels], fontsize=7.4)
    ax3.set_xlim(0, max(v_vals) * 1.25)
    for yi, vv in enumerate(v_vals):
        ax3.text(vv + 0.4, yi, str(vv), va="center", fontsize=8.0, fontweight="bold")
    ax3.set_xlabel("Candidate Count (23 Cubes, 18 Stars)")
    ax3.set_title(f"C. JCMT Stage-2 Veto Funnel ({len(sp_cands)} Raw -> 0 Qualified)")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: 18-Star JCMT EIRP Limits (log scale)
    srows = sorted(rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    y4 = np.arange(len(srows))
    cols4 = ["#636363" if r["role"] == "CONTROL" else ("#1b9e77" if "HARP" in r["instruments"] or "691" in r["best_band"] else "#2b8cbe") for r in srows]
    ax4.barh(y4, [float(r["best_p_beam_10m_kw"]) for r in srows], color=cols4, edgecolor="black", lw=0.5)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['best_band'].replace('JCMT_', '')})" for r in srows], fontsize=6.9)
    ax4.set_xlim(1e6, 3e17)
    ax4.set_xlabel("8-σ 10-m Equivalent Beam EIRP Limit (kW)")
    ax4.set_title("D. 18-Star JCMT 0.43–1.40 mm Limits (Best: LkCa 15 2.04 GW)")
    ax4.text(0.50, 0.14, "Longest Wavelength Frontier:\nO Ceti 213.93 GHz = 1,401.36 µm\n(13.919 octaves from 0.0905 µm)\nBest 230 GHz: HD 163296 (4.22 GW)",
             transform=ax4.transAxes, fontsize=7.3, fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#fff8f0", ec="#d95f02"))
    ax4.grid(True, axis="x", which="both", alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): JCMT Submillimeter & Millimeter Heterodyne Search Across 18 Stellar Systems", fontsize=11.5, fontweight="bold", y=0.985)
    _save(fig, "fig85_d099_jcmt_mm_heterodyne_18stars.png")


def fig86_sofia_exes(bundle: dict[str, Any]) -> None:
    rows = _read_csv("SOFIA_EXES_MIDIR_13STARS.csv")
    cal = _read_csv("CALIBRATION_V57_SOFIA_EXES_180.csv")
    cands = [r for r in _read_csv("V5_7_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "SOFIA_EXES"]
    exps = [e for e in bundle["exposures"] if e["instrument"] == "SOFIA_EXES"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.32, hspace=0.34)

    # Panel A: R Leo (circumstellar molecular forest) + ATRAN transmission
    rleo = next(e for e in exps if e["star"] == "RLEO")
    wl = az._decode_arr_any(rleo["wave_um"])
    fl = az._decode_arr_any(rleo["flux_jy"])
    at = az._decode_arr_any(rleo["atran"])
    m = np.isfinite(wl) & np.isfinite(fl)
    l1, = ax1.plot(wl[m], fl[m] / np.nanmedian(fl[m]), lw=0.75, color="#b30000", label="R Leo 7.36–7.62 µm (49 broad ro-vib lines -> G4/G5 veto)")
    ax1_r = ax1.twinx()
    l2, = ax1_r.plot(wl[m], at[m], lw=0.6, color="#2b8cbe", alpha=0.55, label="ATRAN Telluric Transmission")
    ax1.set_ylim(-0.08, 1.56)
    ax1_r.set_ylim(0.0, 1.25)
    ax1_r.set_ylabel("ATRAN Atmospheric Transmission", color="#2b8cbe")
    ax1.set_xlabel("Wavelength (µm)")
    ax1.set_ylabel("Continuum-Normalized Flux (Jy / med)")
    ax1.set_title("A. SOFIA/EXES R≈90,000 Mid-IR Echelle: R Leo + ATRAN Joint Model")
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], loc="upper left", fontsize=6.9, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: EXES 180-trial calibration suite
    cls_counts = {}
    for r in cal:
        c = r["class"]
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    c_names = list(cls_counts.keys())
    c_rates = [100.0 * cls_counts[k][0] / cls_counts[k][1] for k in c_names]
    bars = ax2.bar(np.arange(len(c_names)), c_rates, color=["#1b9e77", "#7570b3", "#d95f02", "#636363"], edgecolor="black", lw=0.7)
    ax2.set_ylim(0.0, 114.0)
    ax2.set_xticks(np.arange(len(c_names)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in c_names], fontsize=7.4)
    ax2.set_ylabel("Pass Rate (%)")
    ax2.set_title("B. SOFIA/EXES Calibration (179/180 = 99.44% Total)")
    for b, k in zip(bars, c_names):
        p, t = cls_counts[k]
        ax2.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: Stage-2 Triage of all 88 EXES Raw Candidates
    exes_lmap = {
        "G5_EXES_1PX_CR": "G5 EXES 1-px CR",
        "G5_EXES_BROAD_FEATURE": "G5 EXES Broad Feature",
        "G4_EXES_LSF_FAIL": "G4 EXES LSF Fail",
        "VERIFIED ETI": "Verified ETI",
    }
    vr_cnt = Counter(r["stage2_triage_status"].replace("STAGE2_VETO_", "") for r in cands)
    vr_cnt["VERIFIED ETI"] = sum(int(r["verified_eti"]) for r in cands)
    v_labels = list(vr_cnt.keys())
    v_vals = [vr_cnt[k] for k in v_labels]
    y3 = np.arange(len(v_labels))
    cols3 = ["#d95f02" if "BROAD" in k else ("#b30000" if "ETI" in k else "#2b8cbe") for k in v_labels]
    ax3.barh(y3, v_vals, color=cols3, edgecolor="black", lw=0.6)
    ax3.set_yticks(y3)
    ax3.set_yticklabels([exes_lmap.get(k, k) for k in v_labels], fontsize=7.6)
    ax3.set_xlim(0, max(v_vals) * 1.22)
    for yi, vv in enumerate(v_vals):
        ax3.text(vv + 1.2, yi, str(vv), va="center", fontsize=8.0, fontweight="bold")
    ax3.set_xlabel("Candidate Count Across 13 MRD Echelle Targets")
    ax3.set_title(f"C. SOFIA/EXES Automated Veto Funnel ({len(cands)} Raw -> 0 ETI)")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: 13-Star EXES EIRP Limits
    srows = sorted(rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    y4 = np.arange(len(srows))
    cols4 = ["#636363" if r["role"] == "CONTROL" else "#1b9e77" for r in srows]
    ax4.barh(y4, [float(r["best_p_beam_10m_kw"]) for r in srows], color=cols4, edgecolor="black", lw=0.5)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['best_band']})" for r in srows], fontsize=7.4)
    ax4.set_xlim(1e4, 2e9)
    ax4.set_xlabel("8-σ 10-m Mid-IR Laser EIRP Limit (kW)")
    ax4.set_title("D. 13-Star SOFIA/EXES Limits (Best: μ UMa 33.88 MW)")
    ax4.text(0.50, 0.14, "Gray = Control Targets\nGreen = Science Targets\nBest: μ UMa (33,883 kW @ 7 µm)\nAB Aur (582,498 kW @ 18 µm)",
             transform=ax4.transAxes, fontsize=7.3, fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#f7fcf5", ec="#1b9e77"))
    ax4.grid(True, axis="x", which="both", alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): SOFIA/EXES High-Resolution Mid-IR Echelle Survey (5.70–25.31 µm, 13 Stars)", fontsize=11.5, fontweight="bold", y=0.985)
    _save(fig, "fig86_d099_sofia_exes_midir_13stars.png")


def fig87_irtf_spex(bundle: dict[str, Any]) -> None:
    rows = _read_csv("IRTF_SPEX_NIR_26STARS.csv")
    cal = _read_csv("CALIBRATION_V57_IRTF_SPEX_180.csv")
    eirp = [r for r in _read_csv("EIRP_UPPER_LIMITS_D099.csv") if r["instrument"] == "IRTF_SPEX"]
    exps = [e for e in bundle["exposures"] if e["instrument"] == "IRTF_SPEX"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.32, hspace=0.34)

    # Panel A: 0.80-5.43 um IRTF/SpeX spectra for DX Cnc, EZ Aqr, HD 219134
    for st_s, lbl, col, mult in [
        ("HD219134", "HD 219134 (6.54 pc K3V, best QCL 3.5 µm 2,087 kW)", "#2b8cbe", 1.0),
        ("EZAQR", "EZ Aqr (3.41 pc M5V × 10, 180.8 kW @ J)", "#d95f02", 10.0),
        ("DXCNC", "DX Cnc (3.58 pc M6V × 10, 57.0 kW @ J)", "#1b9e77", 10.0),
    ]:
        ex = next(e for e in exps if e["star"] == st_s)
        wu = az._decode_arr_any(ex["wave_um"])
        fw = az._decode_arr_any(ex["flux_wm2um"])
        m = np.isfinite(wu) & np.isfinite(fw) & (fw > 0.0)
        step = max(1, int(np.sum(m) // 1800))
        ax1.plot(wu[m][::step], fw[m][::step] * mult, lw=0.85, color=col, label=lbl)
    ax1.axvspan(3.30, 3.80, color="#fed9a6", alpha=0.35, label="3.5 µm QCL L'-Band Window")
    ax1.axvspan(4.50, 5.10, color="#ccebc5", alpha=0.35, label="4.7 µm M-Band Window")
    ax1.set_yscale("log")
    ax1.set_xlim(0.75, 5.55)
    ax1.set_xlabel("IRTF/SpeX Wavelength (µm)")
    ax1.set_ylabel("Spectral Flux Density (scaled W/m²/µm)")
    ax1.set_title("A. Continuous 0.80–5.43 µm IRTF/SpeX SEDs & QCL Laser Windows")
    ax1.legend(loc="lower left", fontsize=6.9, frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: 180-trial calibration suite
    cls_counts = {}
    for r in cal:
        c = r["class"]
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    c_names = list(cls_counts.keys())
    c_rates = [100.0 * cls_counts[k][0] / cls_counts[k][1] for k in c_names]
    bars = ax2.bar(np.arange(len(c_names)), c_rates, color=["#1b9e77", "#7570b3", "#d95f02", "#636363"], edgecolor="black", lw=0.7)
    ax2.set_ylim(0.0, 114.0)
    ax2.set_xticks(np.arange(len(c_names)))
    ax2.set_xticklabels([k.replace("_VETO", "").replace("_", "\n") for k in c_names], fontsize=7.5)
    ax2.set_ylabel("Pass Rate (%)")
    ax2.set_title("B. V5.7 IRTF/SpeX Calibration (180/180 = 100.00%, 1 Raw -> 0 ETI)")
    for b, k in zip(bars, c_names):
        p, t = cls_counts[k]
        ax2.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: Per-band EIRP Box/Scatter across J, H, K, QCL 3.5 um, M 4.7 um
    bands = ["SPEX_J_125UM", "SPEX_H_165UM", "SPEX_K_220UM", "SPEX_QCL_350UM", "SPEX_M_470UM"]
    b_vals = [[float(r["p_beam_10m_kw"]) for r in eirp if r["band_id"] == bd] for bd in bands]
    for bi, vals in enumerate(b_vals, 1):
        xs = np.full(len(vals), bi) + np.linspace(-0.18, 0.18, max(1, len(vals)))
        ax3.scatter(xs, vals, s=26, color="#2b8cbe", edgecolor="black", lw=0.4, alpha=0.8)
        if vals:
            ax3.hlines(np.median(vals), bi - 0.25, bi + 0.25, color="#b30000", lw=2.0)
    ax3.set_yscale("log")
    ax3.set_xticks(np.arange(1, len(bands) + 1))
    ax3.set_xticklabels(["J\n(1.25 µm)", "H\n(1.65 µm)", "K\n(2.20 µm)", "QCL\n(3.50 µm)", "M\n(4.70 µm)"], fontsize=7.8)
    ax3.set_ylabel("8-σ 10-m EIRP Limit (kW)")
    ax3.set_title("C. Band-Resolved EIRP Sensitivity Across 26 SpeX Stars")
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: Top 16 Tightest SpeX EIRP Limits
    srows = sorted(rows, key=lambda r: float(r["best_p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(srows))
    cols4 = ["#636363" if r["role"] == "CONTROL" else "#1b9e77" for r in srows]
    ax4.barh(y4, [float(r["best_p_beam_10m_kw"]) for r in srows], color=cols4, edgecolor="black", lw=0.5)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['best_band'].replace('SPEX_', '')})" for r in srows], fontsize=7.0)
    ax4.set_xlim(2e1, 1e6)
    ax4.set_xlabel("8-σ 10-m Near-IR/QCL Laser EIRP Limit (kW)")
    ax4.set_title("D. Tightest IRTF/SpeX Limits (Top 16 of 26; Best: DX Cnc 57.0 kW)")
    ax4.grid(True, axis="x", which="both", alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): IRTF/SpeX 0.80–5.43 µm Near-IR & QCL Window Survey (26 Targets)", fontsize=11.5, fontweight="bold", y=0.985)
    _save(fig, "fig87_d099_irtf_spex_nir_qcl_26stars.png")


def fig88_keplerian_36campaigns() -> None:
    d36 = _read_csv("DRIFT_V57_KEPLERIAN_JERK_36CAMPAIGNS.csv")
    led = _read_csv("DRIFT_V57_KEPLERIAN_CANDIDATE_LEDGER.csv")
    cal = _read_csv("CALIBRATION_V57_KEPLERIAN_JERK_300.csv")
    orb = json.loads((WS99 / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))["campaigns"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.33, hspace=0.35)

    # Panel A: 300-trial Keplerian Jerk Benchmark (V5.7 Keplerian vs Taylor Baseline on Multi-Rev)
    classes = ["MULTI_REV_KEPLERIAN_2_10YR", "SUBTHRESH_CUBIC_JERK", "SUBTHRESH_PERIODIC", "STATIONARY_VETO", "TRANSIENT_VETO", "BERV_SKY_VETO"]
    v57_rates, tay_rates = [], []
    for cl in classes:
        sub = [r for r in cal if r["class"] == cl]
        v57_rates.append(100.0 * sum(int(r["passed"]) for r in sub) / max(1, len(sub)))
        tay_rates.append(100.0 * sum(int(int(r["observed" if "MULTI" not in cl else "taylor_only_obs"]) == int(r["expected"])) for r in sub) / max(1, len(sub)))

    x1 = np.arange(len(classes))
    w = 0.36
    b1 = ax1.bar(x1 - w / 2, v57_rates, width=w, color="#1b9e77", edgecolor="black", lw=0.7, label="V5.7 Coherent Keplerian + Jerk (300/300)")
    b2 = ax1.bar(x1 + w / 2, tay_rates, width=w, color="#d95f02", edgecolor="black", lw=0.7, label="Taylor Jerk Only Baseline (36/60 multi-rev)")
    ax1.set_ylim(0.0, 132.0)
    ax1.set_xticks(x1)
    ax1.set_xticklabels(["Multi-Rev\n2–10 yr\nKeplerian", "Cubic Jerk\n3D", "Short\nPeriodic", "Stationary\nVeto", "Transient\nVeto", "BERV/Sky\nVeto"], fontsize=7.4)
    ax1.set_ylabel("Calibration Accuracy (%)")
    ax1.set_title("A. V5.7 Multi-Year Calibration (300/300 vs 60% Multi-Rev Taylor)")
    for bi in b1:
        ax1.text(bi.get_x() + bi.get_width() / 2, bi.get_height() + 1.5, f"{bi.get_height():.0f}%", ha="center", va="bottom", fontsize=7.0, fontweight="bold")
    ax1.text(b2[0].get_x() + b2[0].get_width() / 2, b2[0].get_height() + 1.5, f"{tay_rates[0]:.0f}%", ha="center", va="bottom", fontsize=7.0, fontweight="bold", color="#b30000")
    ax1.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax1.grid(True, axis="y", alpha=0.25)

    # Panel B: GJ 422 b (10.8 yr) & HD 113538 b,c (21.1 yr) Orbital Velocity Tracks Across Epochs
    for st_o, col, mkr, lbl in [
        ("GJ422", "#b30000", "o", "GJ 422 b (P=20.129 d, K_p=55.16 km/s, 10.8 yr)"),
        ("HD113538", "#2b8cbe", "s", "HD 113538 b (P=663.2 d, K_p=20.42 km/s, 21.1 yr)"),
    ]:
        oc = orb[st_o]
        ex_list = oc["exposures"]
        t0 = ex_list[0]["mjd_obs"]
        ts = np.array([(x["mjd_obs"] - t0) / 365.25 for x in ex_list])
        vs = np.array([x["planet_orbital_rv_kms"] for x in ex_list])
        ax2.scatter(ts, vs, s=54, color=col, marker=mkr, edgecolor="black", zorder=4, label=lbl)
        t_dense = np.linspace(0.0, ts[-1], 600)
        # plot envelope / instantaneous curve for HD113538 (slow 663 d) or phase points connected for GJ422
        if st_o == "HD113538":
            p_y = oc["orb_per_days"] / 365.25
            ph0 = ex_list[0]["signed_phase"] * 2.0 * math.pi
            ax2.plot(t_dense, oc["kp_kms"] * np.sin(2.0 * math.pi * t_dense / p_y + ph0), lw=1.0, ls="--", color=col, alpha=0.65)
        else:
            ax2.fill_between([0.0, ts[-1]], -oc["kp_kms"], oc["kp_kms"], color=col, alpha=0.07)
    ax2.axhline(0.0, color="gray", lw=0.8, ls=":")
    ax2.set_xlabel("Baseline Elapsed Since Epoch 0 (years)")
    ax2.set_ylabel("Predicted Exoplanet LOS Orbital Velocity (km/s)")
    ax2.set_title("B. Multi-Decade Orbital Regimes (#144 GJ 422 & #145 HD 113538)")
    ax2.legend(loc="lower right", fontsize=7.0, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: Branch Breakdown Across 36 Campaigns (10,852 raw survivors)
    br_cnt = Counter(r["branch"] for r in led)
    br_names = ["CUBIC_JERK_STACK_V57", "KEPLERIAN_COHERENT_STACK_V57", "CURVED_STACK_V57", "LINEAR_STACK_V57", "PERIODIC_STACK_V57"]
    br_vals = [br_cnt.get(b, 0) for b in br_names]
    br_lbls = ["Cubic Jerk\nV5.7", "Keplerian\nCoherent V5.7", "Quadratic\nCurved", "Linear\nDrift", "Short\nPeriodic"]
    y3 = np.arange(len(br_names))
    ax3.barh(y3, br_vals, color=["#2b8cbe", "#7570b3", "#1b9e77", "#636363", "#d95f02"], edgecolor="black", lw=0.6)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(br_lbls, fontsize=7.6)
    ax3.set_xlim(0, max(br_vals) * 1.24)
    for yi, vv in enumerate(br_vals):
        ax3.text(vv + 100, yi, f"{vv:,}", va="center", fontsize=8.0, fontweight="bold")
    ax3.set_xlabel("Raw Coherent Candidates Across 36 Campaigns")
    ax3.set_title(f"C. 36-Campaign Coherent Branch Breakdown ({len(led):,} Raw Hits)")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: Stage-2 Physics Triage Elimination Funnel
    d_lmap = {
        "SUBPHOTOSPHERIC_TROUGH": "Subphotospheric Trough",
        "OH_SKY_OR_TELLURIC": "OH Sky or Telluric",
        "STATIONARY_OR_ABSORPTION_BAND": "Stationary or Absorption Band",
        "LOWCONT_CR_RINGING": "Low-Cont CR Ringing",
        "SPURIOUS_EPOCH_SUBSET": "Spurious Epoch Subset",
        "NON_LSF_SHAPE": "Non-LSF Shape",
        "VERIFIED ETI": "Verified ETI",
    }
    st_cnt = Counter(r["stage2_triage_status"].replace("STAGE2_VETO_", "") for r in led)
    st_cnt["VERIFIED ETI"] = sum(1 for r in led if str(r["verified_eti"]).lower() in ("true", "1"))
    s_items = sorted(st_cnt.items(), key=lambda kv: -kv[1])
    y4 = np.arange(len(s_items))
    s_vals = [kv[1] for kv in s_items]
    ax4.barh(y4, [max(1, v) for v in s_vals], color=["#b30000" if "ETI" in kv[0] else "#636363" for kv in s_items], edgecolor="black", lw=0.6)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([d_lmap.get(kv[0], kv[0]) for kv in s_items], fontsize=7.1)
    ax4.set_xlim(0.7, max(s_vals) * 6.0)
    for yi, (_, vv) in enumerate(s_items):
        ax4.text(max(1.2, vv * 1.15), yi, f"{vv:,}", va="center", fontsize=7.8, fontweight="bold")
    ax4.set_xlabel("Candidate Count (Log Scale)")
    ax4.set_title("D. 36-Campaign Stage-2 Elimination (10,852 Raw -> 0 Verified ETI)")
    ax4.grid(True, axis="x", which="both", alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): Coherent Keplerian + 3D Jerk Search Across 36 Campaigns (6 ESO + 30 D094–D098)", fontsize=11.4, fontweight="bold", y=0.985)
    _save(fig, "fig88_d099_keplerian_jerk_36campaigns.png")


def fig89_panchromatic_516stars(bundle: dict[str, Any]) -> None:
    s_json = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    eirp99 = _read_csv("EIRP_UPPER_LIMITS_D099.csv")
    u516 = _read_csv("UNIFIED_PANCHROMATIC_V5_7_SYNTHESIS_516STARS.csv")
    s175 = _read_csv("SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_175STARS.csv")
    f4g = _read_csv("FOUR_GEN_BENCHMARK_D099.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: 13.919-Octave Panchromatic EIRP Ladder (0.0905 - 1,401.36 um)
    b_rows = _read_csv("PANCHROMATIC_BRIDGE_71STARS_V57.csv")
    # Plot prior multi-regime points from Bridge 71 (0.11 - 671 um) + all D099 points (0.41 - 1,401.36 um)
    for r in b_rows:
        if r["phase_id"] != "D099":
            try:
                ax1.scatter(float(r["wave_um"]), float(r["p_beam_10m_kw"]), s=11, color="#bdbdbd", alpha=0.55, zorder=1)
            except Exception:
                pass
    ax1.scatter([float(r["wave_um"]) for r in b_rows if r["phase_id"] != "D099"][:1],
                [float(r["p_beam_10m_kw"]) for r in b_rows if r["phase_id"] != "D099"][:1],
                s=16, color="#969696", label="D079–D098 Bridges (FUV 0.0905–670.69 µm)")

    inst_style = {
        "ESO_UVES": ("#1b9e77", "o", "D099 ESO UVES (0.41–0.68 µm)"),
        "ESO_HARPS": ("#66a61e", "s", "D099 ESO HARPS (0.41–0.68 µm)"),
        "IRTF_SPEX": ("#2b8cbe", "^", "D099 IRTF SpeX (1.25–4.70 µm)"),
        "SOFIA_EXES": ("#e7298a", "D", "D099 SOFIA EXES (5.7–25.3 µm)"),
        "JCMT_HARP": ("#7570b3", "P", "D099 JCMT HARP (434–908 µm)"),
        "JCMT_MM_230GHZ": ("#b30000", "*", "D099 JCMT 230 GHz (1,296–1,401.4 µm)"),
    }
    for ik, (col, mk, lbl) in inst_style.items():
        sub = [r for r in eirp99 if r["instrument"] == ik]
        ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=26 if mk != "*" else 42, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.07, 2200.0)
    ax1.set_xlabel("Wavelength (µm; 13.919 Octaves, 0.0905–1,401.36 µm)")
    ax1.set_ylabel("8-σ 10-m Equivalent Beam EIRP Limit (kW)")
    ax1.set_title("A. Unbroken 13.919-Octave Sensitivity Frontier (36 Spectrographs)")
    ax1.legend(loc="upper left", fontsize=6.4, frameon=True, ncol=1)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-516 Sky Map (RA/Dec) highlighting D099 new 43 + bridges 71 + ESO 6
    coh99 = {r["canonical_target"]: r for r in list(csv.DictReader((WS99 / "FROZEN_COHORT_D099.csv").open()))}
    # Use MULTIEVENT_ELLIPSOID_516STARS.csv which has ra_deg, dec_deg for all 516!
    ell = _read_csv("MULTIEVENT_ELLIPSOID_516STARS.csv")
    new43 = {e["star"] for e in bundle["exposures"] if "D099" in e.get("phases", "D099")}
    # determine strictly brand-new 43 vs prior 473
    all99_st = {e["star"] for e in bundle["exposures"]}
    prior_st = {r["star"] for r in json.loads((WS99 / "PRIOR_V5_6_PHASES_SNAPSHOT.json").read_text())["prior_unified_473_rows"]}
    brand43 = all99_st - prior_st
    b71_st = {r["star"] for r in b_rows}

    ra_p, dec_p = [], []
    ra_n, dec_n = [], []
    ra_b, dec_b = [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand43:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in b71_st:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=14, color="#969696", alpha=0.6, label=f"Prior D079–D098 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=30, color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Panchromatic Bridges ({len(b71_st)})")
    ax2.scatter(ra_n, dec_n, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D099 Brand-New ({len(brand43)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension α (deg, wrapped)")
    ax2.set_ylabel("Declination δ (deg)")
    ax2.set_title("B. All-Sky Distribution Across 516 Unique Stellar Systems")
    ax2.legend(loc="lower left", fontsize=7.0, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: <10 pc Solar Neighborhood Histogram (175 stars, median 1.4627 kW)
    lims10 = [float(r["min_panchromatic_10m_kw"]) for r in s175 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    ax3.hist(np.log10(lims10), bins=22, color="#1b9e77", edgecolor="black", alpha=0.82)
    med10 = float(np.median(lims10))
    ax3.axvline(math.log10(med10), color="#b30000", ls="--", lw=1.6, label=f"Median: {med10:.4f} kW (175 stars <10 pc)")
    ax3.set_xlabel("log10(Minimum Panchromatic 10-m Laser EIRP Limit / kW)")
    ax3.set_ylabel("Target Count")
    ax3.set_title("C. Solar Neighborhood (<10 pc, 175 Stars) Sensitivity Distribution")
    ax3.legend(loc="upper right", fontsize=7.2, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: V5.7 Synthetic Calibration Scorecard (2,151 Trials)
    syn = s_json["synthetic_calibration_2151_trials"]
    sc_lbls = ["JCMT mm\n(180)", "SOFIA EXES\n(180)", "IRTF SpeX\n(180)", "Kepler+Jerk\n(300)", "Gate G8\n(120)", "RPCA G7\n(180)", "Agnostic\n(120)", "G4/G5\n(108)", "Inj-Rec\n(540)", "Comb v4.1\n(162)", "Kep Orb\n(81)"]
    sc_keys = ["jcmt_mm_180", "sofia_exes_180", "irtf_spex_180", "keplerian_jerk_300", "g8_pass", "rpca_pass", "agnostic_pass", "g4g5_pass", "injection_540", "comb_v41_162", "keplerian_81"]
    sc_pct = [100.0 * float(syn[k].split("(")[1].rstrip(")")) for k in sc_keys]
    y4 = np.arange(len(sc_lbls))
    ax4.barh(y4, sc_pct, color="#2b8cbe", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(sc_lbls, fontsize=6.7)
    ax4.set_xlim(88.0, 102.5)
    ax4.invert_yaxis()
    for yi, pk in enumerate(sc_keys):
        ax4.text(90.5, yi, syn[pk], va="center", fontsize=6.8, color="white", fontweight="bold")
    ax4.set_xlabel("Suite Pass Rate (%)")
    ax4.set_title("D. D099 11-Suite Calibration Scorecard (2,151 Trials; Cum. 44,124)")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): 516 Stellar Systems Across 13.919 Octaves & 2,151 Calibration Trials (0 Verified ETI)", fontsize=11.4, fontweight="bold", y=0.985)
    _save(fig, "fig89_d099_panchromatic_516stars_13p92octaves.png")


def fig90_bridges_and_milestone() -> None:
    b71 = _read_csv("PANCHROMATIC_BRIDGE_71STARS_V57.csv")
    s_json = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.8, 6.2))
    fig.subplots_adjust(wspace=0.34, top=0.84, bottom=0.16)

    # Panel A: D099 14 Science Bridges (5 Newly Promoted + 9 Deepened) Across 6 Spectral Regimes
    focus_stars = ["BETELGEUSE", "IRC10216", "OCETI", "ABAUR", "HD163296", "RCAS", "VYCMA", "RLEO", "TXCAM", "55CNC", "61CYGB", "DXCNC", "HD115617", "HD219134"]
    reg_bins = [
        ("UV\n(0.09-0.38µm)", 0.05, 0.38),
        ("Optical\n(0.38-0.95µm)", 0.38, 0.95),
        ("NIR/QCL\n(0.95-5.0µm)", 0.95, 5.0),
        ("Mid-IR\n(5.0-45µm)", 5.0, 45.0),
        ("Far-IR/THz\n(45-350µm)", 45.0, 350.0),
        ("Submm/mm\n(350-1402µm)", 350.0, 1500.0),
    ]
    mat = np.full((len(focus_stars), len(reg_bins)), np.nan)
    for r in b71:
        st = r["star"]
        if st not in focus_stars:
            continue
        i = focus_stars.index(st)
        wu = float(r["wave_um"])
        pkw = float(r["p_beam_10m_kw"])
        for j, (_, lo, hi) in enumerate(reg_bins):
            if lo <= wu < hi:
                v = math.log10(max(1e-6, pkw))
                if not math.isfinite(mat[i, j]) or v < mat[i, j]:
                    mat[i, j] = v
    cmap = matplotlib.colormaps["viridis_r"].copy()
    cmap.set_bad(color="#f1f5f9")
    im = ax1.imshow(mat, aspect="auto", cmap=cmap, vmin=-2.0, vmax=11.0)
    ax1.set_xticks(np.arange(len(reg_bins)))
    ax1.set_xticklabels([rb[0] for rb in reg_bins], fontsize=7.2)
    ax1.set_yticks(np.arange(len(focus_stars)))
    new5 = {"HD163296", "RCAS", "VYCMA", "RLEO", "TXCAM"}
    ax1.set_yticklabels([f"{st} *" if st in new5 else st for st in focus_stars], fontsize=7.6)
    for i in range(len(focus_stars)):
        for j in range(len(reg_bins)):
            if math.isfinite(mat[i, j]):
                ax1.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center", fontsize=6.6, color="white" if mat[i, j] < 5.0 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.03)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.5)
    ax1.set_title("A. 14 D099 Science Bridges Across UV–mm (* = +5 Newly Promoted -> 71)")

    # Panel B: Cumulative Campaign Scaling Curve Across Key Milestones Breaking 500+ Stars
    # Grounded verified campaign anchors: D079 (start) .. D094..D098 (Archives T-X) .. D099 (516)
    snap = json.loads((WS99 / "PRIOR_V5_6_PHASES_SNAPSHOT.json").read_text())
    x_lbls = ["D079\nHARPS", "D094\nV5.2", "D095\nV5.3", "D096\nV5.4", "D097\nV5.5", "D098\nV5.6", "D099\nV5.7"]
    # Exact verified cumulative unique stars/octaves:
    # From PRIOR_V5_6_PHASES_SNAPSHOT we have D098=473 (12.855 oct, 33 insts), D099=516 (13.919 oct, 36 insts)
    # Use observed counts from Archives T-X and unified table phase prefixes!
    u516 = _read_csv("UNIFIED_PANCHROMATIC_V5_7_SYNTHESIS_516STARS.csv")
    phase_order = ["D079", "D094", "D095", "D096", "D097", "D098", "D099"]
    milestones = []
    for p_cap in phase_order:
        cnt = sum(1 for r in u516 if any(tok.strip() <= p_cap for tok in r["phases"].split("+")))
        milestones.append(cnt)
    ax2.plot(np.arange(len(phase_order)), milestones, "-o", color="#1b9e77", lw=2.2, ms=7.5, markeredgecolor="black")
    ax2.axhline(500.0, color="#b30000", ls="--", lw=1.4, label="500-Star Panchromatic Milestone")
    for xi, mv in enumerate(milestones):
        ax2.annotate(f"{mv}", xy=(xi, mv), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.0, fontweight="bold")
    ax2.set_xticks(np.arange(len(phase_order)))
    ax2.set_xticklabels(x_lbls, fontsize=7.6)
    ax2.set_ylim(0.0, 575.0)
    ax2.set_ylabel("Cumulative Unique Stellar Systems")
    ax2.set_title("B. Campaign Growth to 516 Unique Systems (36 Insts, 13.919 Octaves)")
    ax2.legend(loc="lower right", fontsize=7.5, frameon=True)
    ax2.grid(True, alpha=0.25)

    fig.suptitle("Phase D099 (V5.7): 71 Pan-Chromatic Science Bridges & Breaking the 500-System Frontier (516 Stars)", fontsize=11.4, fontweight="bold", y=0.97)
    _save(fig, "fig90_d099_bridge_71stars_and_milestone_500plus.png")


def main() -> int:
    bundle = json.loads(gzip.decompress((WS99 / "bounded_inputs" / "d099_bounded_bundle.json.gz").read_bytes()).decode("utf-8"))
    fig85_jcmt_mm(bundle)
    fig86_sofia_exes(bundle)
    fig87_irtf_spex(bundle)
    fig88_keplerian_36campaigns()
    fig89_panchromatic_516stars(bundle)
    fig90_bridges_and_milestone()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
