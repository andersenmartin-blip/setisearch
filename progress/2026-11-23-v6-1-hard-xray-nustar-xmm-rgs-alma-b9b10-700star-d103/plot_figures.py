#!/usr/bin/env python3
"""
Phase D103 (V6.1) Publication Figure Generator (`fig109`–`fig114`, 240 DPI, metadata={}).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import pathlib
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.4,
    "axes.titlesize": 9.2,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.2,
    "xtick.labelsize": 7.6,
    "ytick.labelsize": 7.6,
    "legend.fontsize": 6.8,
    "figure.facecolor": "white",
    "axes.facecolor": "#fcfcfd",
    "axes.edgecolor": "#4a5568",
    "axes.linewidth": 0.85,
})


def _load_mod(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_csv(res_dir: Path, fname: str) -> list[dict[str, str]]:
    with (res_dir / fname).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fig_dir: Path, fname: str) -> None:
    fig.savefig(fig_dir / fname, dpi=240, bbox_inches="tight", pad_inches=0.14, metadata={})
    plt.close(fig)


def _fmt_power_kw(p_kw: float) -> str:
    p_w = p_kw * 1000.0
    if p_w < 1.0:
        return f"{p_w * 1000.0:.2f} mW"
    if p_w < 1000.0:
        return f"{p_w:.2f} W"
    if p_kw < 1000.0:
        return f"{p_kw:.2f} kW"
    return f"{p_kw / 1000.0:.2f} MW"


def _cal_bars(ax: plt.Axes, rows: list[dict[str, str]], title: str, replace_map: dict[str, str] | None = None) -> None:
    by_c: dict[str, list[int]] = {}
    for r in rows:
        c = r.get("class") or r.get("suite") or "ALL"
        by_c.setdefault(c, [0, 0])
        by_c[c][0] += int(r["passed"])
        by_c[c][1] += 1
    classes = list(by_c.keys())
    pcts = [100.0 * by_c[c][0] / max(1, by_c[c][1]) for c in classes]
    labels = []
    for c in classes:
        s = c
        if replace_map and c in replace_map:
            s = replace_map[c]
        else:
            s = c.replace("_VETO", "").replace("_", "\n")
        labels.append(s)
    pal = ["#1b9e77", "#2b8cbe", "#7570b3", "#d95f02", "#e7298a", "#66a61e"]
    x = np.arange(len(classes))
    bars = ax.bar(x, pcts, color=[pal[i % len(pal)] for i in range(len(classes))], edgecolor="black", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.7)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Pass Rate (%)")
    ax.set_title(title)
    for b, c in zip(bars, classes):
        p, t = by_c[c]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig109_nustar_hard_xray(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    nu_obs = _read_csv(res_dir, "NUSTAR_HARD_XRAY_POISSON_19OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V61_NUSTAR_POISSON_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_1_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "NUSTAR_FPMA_FPMB"]
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V61_NUSTAR_POISSON_240
    _cal_bars(
        ax1, cal,
        f"A. NuSTAR Dual-FPM Poisson Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.1f}%)",
        replace_map={
            "CLEAN_DUAL_FPM_BEACON": "Clean\nFPMA+B",
            "SINGLE_FPM_GLITCH_VETO": "Single-FPM\nGlitch",
            "NUSTAR_ATLAS_VETO": "NuSTAR\nAtlas",
            "POISSON_CONTINUUM_NULL": "Continuum\nNull",
            "BROAD_COMPTON_OR_1BIN_VETO": "Broad / 1-Bin\nHump",
        },
    )

    # Panel B: Archival NuSTAR FPMA+FPMB Spectrum (AU Mic or nearest SCIENCE target)
    nu_exps = [e for e in bundle["exposures"] if e["instrument"] == "NUSTAR_FPMA_FPMB"]
    pref = next((e for e in nu_exps if e["star"] == "AUMIC"), None) or next((e for e in nu_exps if e["role"] == "SCIENCE"), nu_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"])
    ona = az._decode_arr_any(pref["on_a_c"])
    onb = az._decode_arr_any(pref["on_b_c"])
    ax2.step(ek, ona, where="mid", color="#1a365d", lw=0.95, alpha=0.88, label=f"FPMA (exp={float(pref['exp_a']):.0f}s)")
    ax2.step(ek, onb, where="mid", color="#d95f02", lw=0.85, alpha=0.78, label=f"FPMB (exp={float(pref['exp_b']):.0f}s)")
    ymax_nu = max(1.0, float(np.max(ona)))
    for e_line, x_mul, y_frac, lbl in [(6.40, 0.90, 0.85, "Fe Ka"), (6.70, 1.04, 0.58, "Fe XXV"), (10.5, 1.03, 0.85, "W/Au inst.")]:
        ax2.axvline(e_line, color="#7570b3", ls=":", lw=0.8, alpha=0.8)
        ax2.text(e_line * x_mul, ymax_nu * y_frac, lbl, rotation=90, va="top", fontsize=6.4, color="#553c9a")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(3.0, 79.0)
    ax2.set_xlabel("Photon Energy (keV, log scale)")
    ax2.set_ylabel("Counts per Spectral Channel")
    ax2.set_title(f"B. Archival NuSTAR Dual-FPM Spectrum ({pref['star']}, 3-79 keV)")
    ax2.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Dual-FPM Li & Ma S_LiMa vs log10(FPMA/FPMB Binomial p) for Raw Peaks
    if sc:
        snrs = [float(r["snr"]) for r in sc]
        pvals = [-math.log10(max(1e-12, float(r["beam_conc"]) if r.get("beam_conc") else 1.0)) for r in sc]
        cols = ["#b30000" if r["qualified_v61"] == "True" else "#2b8cbe" for r in sc]
        ax3.scatter(snrs, pvals, s=42, c=cols, edgecolor="black", lw=0.5, zorder=4)
        ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0, label="S_LiMa >= 6.0 Threshold")
        ax3.axhline(2.0, color="#d95f02", ls="--", lw=1.0, label="Dual-FPM Consistency Threshold")
        ax3.set_title(f"C. NuSTAR Dual-FPM Li & Ma Candidates ({len(sc)} Raw -> 0 Verified ETI)")
        ax3.legend(loc="upper right", fontsize=6.8, frameon=True)
    else:
        ax3.text(0.5, 0.5, "0 Raw NuSTAR Candidates Above Threshold", ha="center", va="center", transform=ax3.transAxes, fontsize=9.5, fontweight="bold")
        ax3.set_title("C. NuSTAR Dual-FPM Li & Ma Candidates (0 Raw -> 0 ETI)")
    ax3.set_xlabel("Joint Li & Ma Significance (S_LiMa)")
    ax3.set_ylabel("-log10(Dual-FPM Binomial p-value)")
    ax3.grid(True, alpha=0.22)

    # Panel D: Top 16 NuSTAR 3-79 keV 10-m EIRP Bounds
    nu_sorted = sorted(nu_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(nu_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in nu_sorted]
    ax4.barh(y4, vals4, color=["#1a365d" if r["role"] == "SCIENCE" else "#718096" for r in nu_sorted], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in nu_sorted], fontsize=6.9)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.4, max(vals4) * 28.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.4, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    best_nu = nu_sorted[0]
    ax4.set_title(f"D. Best 16 NuSTAR Hard X-Ray EIRP Bounds ({best_nu['star']} {_fmt_power_kw(float(best_nu['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D103 (V6.1): NASA NuSTAR Hard X-Ray Dual-FPM Survey (19 Observations; 3-79 keV; 0.157-4.13 A; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig109_d103_nustar_hard_xray_poisson_3_79kev.png")


def fig110_xmm_newton_rgs(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    xm_obs = _read_csv(res_dir, "XMM_NEWTON_RGS_26OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V61_XMM_RGS_180.csv")
    spec_a = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D103.json").read_text())
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Unbroken Hard-to-Soft X-Ray + EUV Ladder (0.157 A to 699.8 A = 12.122 octaves)
    bands_he = [
        ("NuSTAR FPMA+FPMB\n(3-79 keV; D103)", 0.1569, 4.1328, "#1a365d"),
        ("Chandra HETG MEG+HEG\n(0.4-10 keV; D102)", 1.24, 31.0, "#2b8cbe"),
        ("XMM-Newton RGS1+RGS2\n(5-38 A; D103)", 5.0, 38.0, "#d95f02"),
        ("Chandra LETG HRC-S\n(0.07-10 keV; D102)", 1.24, 175.0, "#1b9e77"),
        ("EUVE DS/S Spectrometer\n(70-700 A; D102)", 70.0, 699.80, "#7570b3"),
    ]
    ax1.axvspan(699.80, 905.0, color="#fed7d7", alpha=0.75, label="ISM H Photoionization Wall (700-905 A)")
    for yi, (lbl, a_lo, a_hi, col) in enumerate(bands_he):
        ax1.plot([a_lo, a_hi], [yi, yi], color=col, lw=8.5, solid_capstyle="butt")
    ax1.set_yticks(np.arange(len(bands_he)))
    ax1.set_yticklabels([b[0] for b in bands_he], fontsize=7.0)
    ax1.set_xscale("log")
    ax1.set_xlim(0.10, 1500.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Wavelength (Angstrom, log scale)")
    ax1.set_title(f"A. Unbroken NuSTAR-XMM-Chandra-EUVE Ladder ({spec_a['high_energy_unbroken_octaves']:.3f} Octaves)")
    ax1.legend(loc="lower left", fontsize=6.9, frameon=True)
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Archival XMM RGS1+RGS2 Spectrum with coronal lines
    xm_exps = [e for e in bundle["exposures"] if e["instrument"] == "XMM_RGS"]
    pref = next((e for e in xm_exps if e["star"] == "AUMIC"), None) or next((e for e in xm_exps if e["role"] == "SCIENCE"), xm_exps[0])
    wr = az._decode_arr_any(pref["wave_a_c"])
    c1 = az._decode_arr_any(pref["cts_r1_c"])
    c2 = az._decode_arr_any(pref["cts_r2_c"])
    g1 = az._decode_arr_any(pref["good_r1_c"]) > 0.5
    g2 = az._decode_arr_any(pref["good_r2_c"]) > 0.5
    ax2.plot(wr[g1], c1[g1], color="#2b8cbe", lw=0.75, alpha=0.88, label="RGS1 ON Counts")
    ax2.plot(wr[g2], c2[g2], color="#d95f02", lw=0.70, alpha=0.75, label="RGS2 ON Counts")
    ymax_r = max(1.0, float(np.nanmax(np.concatenate([c1[g1], c2[g2]]))))
    for wl, clbl in [(12.13, "Ne X"), (13.45, "Ne IX"), (15.01, "Fe XVII"), (18.97, "O VIII"), (21.60, "O VII"), (33.74, "C VI")]:
        ax2.axvline(wl, color="#7570b3", ls=":", lw=0.8, alpha=0.8)
        ax2.text(wl + 0.25, ymax_r * 0.90, clbl, rotation=90, va="top", fontsize=6.3, color="#553c9a")
    ax2.set_xlim(5.0, 38.0)
    ax2.set_xlabel("Wavelength (Angstrom)")
    ax2.set_ylabel("Counts per RGS Channel")
    ax2.set_title(f"B. Archival XMM-Newton RGS1+RGS2 Spectrum ({pref['star']}, Coronal Atlas Vetoes)")
    ax2.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: CALIBRATION_V61_XMM_RGS_180
    _cal_bars(
        ax3, cal,
        f"C. XMM-Newton Dual-RGS Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_DUAL_RGS_BEACON": "Clean\nRGS1+RGS2",
            "SINGLE_RGS_OR_CHIPGAP_VETO": "Single-RGS /\nChip Gap",
            "CORONAL_RGS_ATLAS_VETO": "Coronal\nAtlas",
            "BROAD_WIND_OR_1BIN_VETO": "Broad Wind /\n1-Bin",
        },
    )

    # Panel D: Top 16 XMM-Newton RGS 10-m EIRP Bounds
    xm_sorted = sorted(xm_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(xm_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in xm_sorted]
    ax4.barh(y4, vals4, color=["#d95f02" if r["role"] == "SCIENCE" else "#718096" for r in xm_sorted], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in xm_sorted], fontsize=6.9)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.4, max(vals4) * 28.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.4, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    best_xm = xm_sorted[0]
    ax4.set_title(f"D. Best 16 XMM-Newton RGS EIRP Bounds ({best_xm['star']} {_fmt_power_kw(float(best_xm['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D103 (V6.1): ESA/NASA XMM-Newton RGS Grating Survey (26 Dual-RGS Obs; 5-38 A; {spec_a['high_energy_unbroken_octaves']} HE Octaves; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig110_d103_xmm_newton_rgs_high_res_xray.png")


def fig111_alma_b9_b10(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    alma_rows = _read_csv(res_dir, "ALMA_B9_B10_CUBES_D103.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_1_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"].startswith("ALMA_")]
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Frequency Coverage across all 20 Band 9 & Band 10 Cubes
    ax1.axvspan(552.0, 602.0, color="#fed7d7", alpha=0.60, label="Telluric H2O 557 GHz Wall")
    ax1.axvspan(720.0, 787.0, color="#feebc8", alpha=0.75, label="Atmospheric H2O 752 GHz Gap")
    ax1.axvspan(950.0, 995.0, color="#fed7d7", alpha=0.60, label="Telluric H2O 988 GHz Wall")
    rows_s = sorted(alma_rows, key=lambda r: (r["instrument"], float(r["min_freq_ghz"])))
    seen_b = set()
    bcfg = {
        "ALMA_B9_0P4MM": ("ALMA Band 9 (602-720 GHz, 10 cubes)", "#2b8cbe"),
        "ALMA_B10_0P3MM": ("ALMA Band 10 (787-950 GHz, 10 cubes)", "#b30000"),
    }
    for yi, r in enumerate(rows_s):
        f0, f1 = float(r["min_freq_ghz"]), float(r["max_freq_ghz"])
        lbl, col = bcfg[r["instrument"]]
        use_l = lbl if r["instrument"] not in seen_b else None
        seen_b.add(r["instrument"])
        ax1.plot([f0, f1], [yi, yi], color=col, lw=4.5, label=use_l)
        if abs(f1 - f0) < 12.0:
            ax1.scatter([(f0 + f1) / 2.0], [yi], color=col, s=26, edgecolor="black", lw=0.45, zorder=4)
    ax1.set_yticks(np.arange(len(rows_s)))
    ax1.set_yticklabels([r["star"] for r in rows_s], fontsize=6.4)
    ax1.set_xlim(555.0, 990.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Observing Frequency (GHz)")
    ax1.set_title("A. All 20 ALMA D103 Cubes Across Bands 9 & 10 (Completing 9/9 Receiver Bands)")
    ax1.legend(loc="lower right", fontsize=6.3, frameon=True)
    ax1.grid(True, axis="x", alpha=0.22)

    # Panel B: Spatial Compactness vs OFF-Annulus Ratio for ALMA Peaks
    ax2.fill_between([0.75, 1.35], -0.02, 0.22, color="#c6f6d5", alpha=0.55, label="Unresolved Point-Source Pass Box")
    ax2.axvline(1.35, color="#b30000", ls="--", lw=1.0)
    ax2.axhline(0.22, color="#b30000", ls="--", lw=1.0)
    if sc:
        ratios = [float(r["spatial_fwhm_ratio"]) for r in sc]
        offs = [float(r["off95_to_on"]) for r in sc]
        cols = ["#b30000" if "B10" in r["instrument"] else "#2b8cbe" for r in sc]
        ax2.scatter(ratios, offs, s=44, c=cols, edgecolor="black", lw=0.5, zorder=4, label=f"{len(sc)} Raw ALMA B9/B10 Peaks (0 Verified ETI)")
        ax2.set_xlim(0.7, max(max(ratios) * 1.15, 3.0))
        ax2.set_ylim(-0.04, max(max(offs) * 1.12, 0.9))
    else:
        ax2.set_xlim(0.7, 3.0)
        ax2.set_ylim(-0.04, 0.9)
        ax2.text(1.85, 0.48, "0 Raw ALMA B9/B10 Peaks\nAbove 6-sigma Threshold\n(20/20 Clean Noise Floors)", ha="center", va="center", fontsize=8.8, fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7fafc", edgecolor="#4a5568", lw=0.8))
    ax2.set_xlabel("Spatial FWHM Ratio (Observed / Synthesized Beam)")
    ax2.set_ylabel("OFF-Annulus 95th Percentile / ON-Beam Peak")
    ax2.set_title(f"B. ALMA G4+G6 Spatial Compactness & Annulus Veto ({len(sc)} Raw -> 0 ETI)")
    ax2.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: CALIBRATION_V59_ALMA_INTERFEROMETRIC_240
    _cal_bars(
        ax3, cal,
        f"C. ALMA Interferometric Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={"CLEAN_ALMA_BEACON": "Clean\nALMA", "EXTENDED_DISK_GAS": "Extended\nDisk", "OFFSOURCE_BIRDIE": "Off-Source\nBirdie", "MM_MOLECULAR_ATLAS": "Mol.\nAtlas", "SINGLE_CHAN_GIBBS": "Single-Ch\nGibbs"},
    )

    # Panel D: Archival ALMA Band 10 or Band 9 ON-beam vs OFF-95% profile
    al_exps = [e for e in bundle["exposures"] if e["instrument"].startswith("ALMA_B")]
    pref = next((e for e in al_exps if e["instrument"] == "ALMA_B10_0P3MM" and e["role"] == "SCIENCE"), None) or next((e for e in al_exps if e["instrument"] == "ALMA_B10_0P3MM"), al_exps[0])
    f_arr = az._decode_arr_any(pref["freq_ghz_c"])
    s_on = az._decode_arr_any(pref["s_on_jy_c"]) * 1000.0
    s_off95 = az._decode_arr_any(pref["s_off_95_jy_c"]) * 1000.0
    ax4.plot(f_arr, s_on, color="#2b8cbe", lw=1.1, label="ON-Target Synthesized Beam (mJy)")
    ax4.plot(f_arr, s_off95, color="#d95f02", lw=0.95, alpha=0.85, label="OFF-Source Annulus 95% (mJy)")
    ax4.axhline(0.0, color="black", lw=0.6)
    ax4.set_xlabel("Frequency (GHz)")
    ax4.set_ylabel("Flux Density (mJy / beam)")
    ax4.set_title(f"D. Archival ALMA Profile: {pref['star']} ({pref['instrument'].replace('_', ' ')})")
    ax4.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax4.grid(True, alpha=0.22)

    fig.suptitle("Phase D103 (V6.1): ALMA Sub-mm Bands 9 & 10 Survey (20 Cubes; Complete 9-Band B1, B3-B10 Closure; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig111_d103_alma_band9_band10_complete_closure.png")


def fig112_drift_and_comb_60campaigns(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6_D103.csv")
    ek60 = _read_csv(res_dir, "DRIFT_V61_ECCENTRIC_KEPLERIAN_60CAMPAIGNS.csv")
    cd60 = _read_csv(res_dir, "COMB_DRIFT_V61_60CAMPAIGNS.csv")
    cal_dc = _read_csv(res_dir, "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Drifting-Comb V6.1 Calibration vs Static V4.1 Baseline
    cls_map: dict[str, list[int]] = {}
    for r in cal_dc:
        c = r["class"]
        cls_map.setdefault(c, [0, 0])
        cls_map[c][0] += int(r["passed"])
        cls_map[c][1] += 1
    lbls_a = ["V6.1 Kepler\nComb (60)", "V6.1 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
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
    cal_dc_p = sum(int(r["passed"]) for r in cal_dc)
    ax1.set_title(f"A. Coherent Drifting-Comb Calibration ({cal_dc_p}/{len(cal_dc)} = {100.0*cal_dc_p/len(cal_dc):.2f}%)")
    for b, t in zip(bars1, txt_a):
        ax1.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, t, ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax1.grid(True, axis="y", alpha=0.25)

    # Panel B: Live Orbital Campaigns #163-#168 Planetary RV Curves
    pal = ["#b30000", "#2b8cbe", "#1b9e77", "#d95f02", "#7570b3", "#636363"]
    ymin_v, ymax_v = 0.0, 0.0
    for idx_o, r in enumerate(o6):
        st = r["star"]
        om = orb_json["campaigns"][st]
        ph = np.linspace(0.01, 0.99, 250)
        p_d = float(om["orb_per_days"])
        e_v = float(om["orb_ecc"])
        w_r = math.radians(float(om["orb_omega_deg"]))
        kp = float(om["kp_kms"])
        vr_ms = 1000.0 * np.asarray([float(det_mod.solve_kepler_eccentric_rv(np.array([p_i * p_d]), p_d, e_v, w_r, 0.0, kp)[0]) for p_i in ph], dtype=np.float64)
        ymin_v = min(ymin_v, float(np.min(vr_ms)))
        ymax_v = max(ymax_v, float(np.max(vr_ms)))
        ax2.plot(ph, vr_ms, lw=1.65, color=pal[idx_o % len(pal)], label=f"#{r['campaign_index']} {st} (P={p_d:.1f}d, e={e_v:.2f}, Kp={kp*1e3:.2f} m/s)")
    pad_y = max(1.0, 0.22 * (ymax_v - ymin_v))
    ax2.set_ylim(ymin_v - 0.55 * pad_y, ymax_v + 1.45 * pad_y)
    ax2.set_xlabel("Orbital Phase phi")
    ax2.set_ylabel("Planetary Keplerian RV (m/s)")
    ax2.set_title("B. ESO ESPRESSO + HARPS Orbits #163-#168 (Multi-Epoch Planetary Kinematics)")
    ax2.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: All 60 Cumulative DRIFT_V61 Campaigns
    x60 = np.arange(len(ek60))
    ax3.bar(x60, [int(r["n_trajectories_evaluated"]) for r in ek60], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x60, [int(r["raw_coherent_survivors"]) for r in ek60], color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Raw Survivors ({sum_raw['drift_v61_60campaigns_raw_survivors']:,})")
    ax3.bar(x60, [int(r["stage2_verified_eti"]) for r in ek60], color="#1b9e77", label="Verified ETI (0/60)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek60) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D103, 7-12 D102, ..., 56-60 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    ax3.set_title(f"C. 60-Campaign DRIFT_V61 ({sum_raw['drift_v61_60campaigns_trajectories']:,} Traj / {sum_raw['drift_v61_60campaigns_pixel_integrals']/1e9:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 60 Cumulative COMB_DRIFT_V61 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd60])
    qual_cd = np.asarray([int(r["comb_qualified_v61"]) for r in cd60])
    ax4.plot(x60, raw_cd, "-o", ms=3.0, color="#d95f02", lw=1.05, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v61_60campaigns_raw_candidates']:,})")
    ax4.plot(x60, qual_cd, "-s", ms=3.0, color="#7570b3", lw=1.05, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v61_60campaigns_qualified_pre_stage2']})")
    ax4.plot(x60, np.zeros_like(x60), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/60)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#60 Across D094-D103)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 60-Campaign COMB_DRIFT_V61 ({sum_raw['comb_drift_v61_60campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax4.grid(True, alpha=0.22)

    pix_b = sum_raw["drift_v61_60campaigns_pixel_integrals"] / 1e9
    fig.suptitle(f"Phase D103 (V6.1): Orbits #163-#168 & 60-Campaign Coherent DRIFT_V61 + COMB_DRIFT_V61 ({pix_b:.2f}B Pixel Integrals; 0 ETI)", fontsize=11.0, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig112_d103_drift_v61_and_comb_60campaigns.png")


def fig113_panchromatic_29octaves(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json["unified_709star_panchromatic_v6_1_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp103 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D103.csv")
    ell = _read_csv(res_dir, "MULTIEVENT_ELLIPSOID_709STARS.csv")
    s188 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_188STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 0.0000157-8,556.42 um Sensitivity Frontier
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Photoionization Wall (700-905 A)")
    ax1.axvspan(381.9, 416.4, color="#edf2f7", alpha=0.80, zorder=0, label="Telluric H2O B9-B10 Gap (720-787 GHz)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D103" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=9, color="#bdbdbd", alpha=0.50, zorder=1, label="D079-D102 (0.00012-8,556.4 um)")

    inst_groups = [
        ("NUSTAR_FPMA_FPMB", "#1a365d", "^", "D103 NuSTAR (0.0157-0.41 nm)"),
        ("XMM_RGS", "#2b8cbe", "v", "D103 XMM RGS (0.50-3.80 nm)"),
        ("ESO_ESPRESSO", "#1b9e77", "o", "D103 ESPRESSO (0.42-0.76 um)"),
        ("ESO_HARPS", "#66a61e", "s", "D103 HARPS (0.41-0.58 um)"),
        ("ALMA_B10_0P3MM", "#b30000", "*", "D103 ALMA B10 (316-381 um)"),
        ("ALMA_B9_0P4MM", "#e7298a", "D", "D103 ALMA B9 (416-498 um)"),
    ]
    for ik, col, mk, lbl in inst_groups:
        sub = [r for r in eirp103 if r["instrument"] == ik]
        ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=26 if mk != "*" else 56, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(9e-6, 25000.0)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma 10-m EIRP Limit (kW)")
    ax1.set_title(f"A. Unified {syn['spectrographs']}-Spectrograph Sensitivity Frontier ({syn['total_octave_span']} Octaves)")
    ax1.legend(loc="lower right", fontsize=5.6, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-709 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V6_0_PHASES_SNAPSHOT.json").read_text())["prior_unified_656_rows"]}
    all103_st = {e["star"] for e in bundle["exposures"]}
    brand53 = all103_st - prior_st
    bridges17 = all103_st & prior_st
    ra_p, dec_p, ra_b, dec_b, ra_n, dec_n = [], [], [], [], [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand53:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in bridges17:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D102 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D103 Bridges / Revisited ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D103 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.9, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: <10 pc Solar Neighborhood (188 Stars)
    lims10 = [float(r["min_panchromatic_10m_kw"]) for r in s188 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med10 = float(np.median(lims10))
    ax3.hist(np.log10(lims10), bins=24, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax3.axvline(math.log10(med10), color="#b30000", ls="--", lw=1.6, label=f"Median: {med10:.4f} kW ({len(s188)} stars <10 pc)")
    ax3.set_xlabel("log10(Minimum Panchromatic 10-m EIRP Limit / kW)")
    ax3.set_ylabel("Target Count")
    ax3.set_title(f"C. Solar Neighborhood (<10 pc, {len(s188)} Stars; Best {_fmt_power_kw(min(lims10))})")
    ax3.legend(loc="upper left", fontsize=7.0, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: All 15 D103 Calibration Suites (3,111 Trials; 54,528 Cumulative)
    cal_sum = s_json["synthetic_calibration_3111_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V61_", "V6.1 ")
        .replace("CALIBRATION_V60_", "V6.0 ")
        .replace("CALIBRATION_V59_", "V5.9 ")
        .replace("CALIBRATION_V58_", "")
        .replace("CALIBRATION_", "")
        .replace("DETECTOR_V58_", "")
        .replace("_CALIBRATION", "")
        .replace("_", " ")
        for k in s_names
    ]
    y4 = np.arange(len(s_names))
    ax4.barh(y4, s_pcts, color=["#b30000" if "V6.1" in s else "#2b8cbe" for s in short_s], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(short_s, fontsize=5.8)
    ax4.set_xlim(92.0, 102.0)
    ax4.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax4.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=5.8, color="white", fontweight="bold")
    ax4.set_xlabel("Suite Pass Rate (%)")
    ax4.set_title(f"D. D103 15-Suite Calibration ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d103']:,})")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle(f"Phase D103 (V6.1): {syn['unique_stars_total']} Stellar Systems Across {syn['total_octave_span']} Octaves ({syn['high_energy_unbroken_octaves']} NuSTAR-XMM-Chandra-EUVE Octaves; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig113_d103_global_29p02_octave_709star_frontier.png")


def fig114_bridge_and_709star_synthesis(res_dir: Path, fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    syn = s_json["unified_709star_panchromatic_v6_1_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    u709 = _read_csv(res_dir, "UNIFIED_PANCHROMATIC_V6_1_SYNTHESIS_709STARS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.0, 7.2))
    fig.subplots_adjust(wspace=0.35, top=0.84, bottom=0.16)

    # Panel A: Cross-band Bridge Matrix Heatmap for flagship D103 & panchromatic bridge stars
    regs = [
        ("Hard X\nNuSTAR", 1e-5, 4.5e-4),
        ("Soft X\nXMM/CXO", 4.5e-4, 0.0176),
        ("EUV\n70-700A", 0.007, 0.072),
        ("FUV/NUV\nHST/IUE", 0.090, 0.32),
        ("Optical\n0.32-1um", 0.32, 1.0),
        ("NIR\n1-5um", 1.0, 5.0),
        ("Mid-IR\n5-30um", 5.0, 30.0),
        ("Far-IR\n30-310um", 30.0, 310.0),
        ("Sub-mm\nALMA\nB7-B10", 310.0, 1100.0),
        ("mm\nALMA\nB1-B6", 1100.0, 9000.0),
    ]
    by_star: dict[str, list[tuple[float, float]]] = {}
    for br in b_rows:
        st = br["star"]
        if not br.get("wave_um") or not br.get("p_beam_10m_kw"):
            continue
        by_star.setdefault(st, []).append((float(br["wave_um"]), float(br["p_beam_10m_kw"])))

    def _reg_score(st: str) -> int:
        pts = by_star.get(st, [])
        return sum(1 for _, w0, w1 in regs if any(w0 <= w <= w1 for w, _ in pts))

    priority_stars = [
        "AUMIC", "PROXIMACEN", "ADLEO", "BETELGEUSE", "SIRIUSA", "EPSERI", "VEGA",
        "FOMALHAUT", "ALPCENA", "61CYGB", "ALPCENB", "TAUCET", "GJ876", "HR8799",
        "TWA07", "HD163296", "NGC7469", "NGC1068", "ETACAR", "BETPIC",
    ]
    focus = [s for s in priority_stars if _reg_score(s) >= 2]
    for s in sorted(by_star, key=_reg_score, reverse=True):
        if s not in focus and len(focus) < 16:
            focus.append(s)
    focus = focus[:16]

    mat = np.full((len(focus), len(regs)), np.nan, dtype=np.float64)
    for r_i, st in enumerate(focus):
        for c_i, (_, w0, w1) in enumerate(regs):
            vals = [math.log10(max(1e-9, pk)) for w, pk in by_star.get(st, []) if w0 <= w <= w1]
            if vals:
                mat[r_i, c_i] = min(vals)

    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad("#edf2f7")
    im = ax1.imshow(mat, aspect="auto", cmap=cmap, vmin=-6.0, vmax=6.0)
    ax1.set_xticks(np.arange(len(regs)))
    ax1.set_xticklabels([r[0] for r in regs], fontsize=6.2)
    ax1.set_yticks(np.arange(len(focus)))
    ax1.set_yticklabels(focus, fontsize=7.0)
    for ri in range(len(focus)):
        for ci in range(len(regs)):
            v = mat[ri, ci]
            if math.isfinite(v):
                ax1.text(ci, ri, f"{v:+.1f}", ha="center", va="center", fontsize=5.3, color="white" if v < 0.0 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.02)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.5)
    ax1.set_title(f"A. Panchromatic Bridge Limits ({syn['multi_phase_targets_total']} Multi-Phase Targets; {syn['panchromatic_bridge_cells_total']} Cells)")

    # Panel B: Epoch-by-Epoch Survey Scale & Octave Closure Summary
    # Show verified milestone progression from D100 -> D101 -> D102 -> D103 and role breakdown
    roles = ["SCIENCE\n(Exoplanets/HZ/<10pc)", "CONTROL\n(AGNs/Clouds/0-pl)"]
    r_cnts = [syn["science_stars_total"], syn["control_stars_total"]]
    ax2.barh([0, 1], r_cnts, color=["#1b9e77", "#7570b3"], edgecolor="black", lw=0.7, height=0.52)
    for yi, v in enumerate(r_cnts):
        ax2.text(v + 8, yi, f"{v} targets", va="center", fontsize=7.6, fontweight="bold")

    ax2.barh([2.3], [syn["within_10pc_unique_stars"]], color="#2b8cbe", edgecolor="black", lw=0.7, height=0.52)
    ax2.text(syn["within_10pc_unique_stars"] + 8, 2.3, f"{syn['within_10pc_unique_stars']} <10 pc (med. {syn['within_10pc_median_limit_kw']:.4f} kW)", va="center", fontsize=7.4, fontweight="bold")

    ax2.barh([3.3], [syn["planet_host_stars_total"]], color="#d95f02", edgecolor="black", lw=0.7, height=0.52)
    ax2.text(syn["planet_host_stars_total"] + 8, 3.3, f"{syn['planet_host_stars_total']} hosts ({syn['confirmed_exoplanets_total']} planets)", va="center", fontsize=7.4, fontweight="bold")

    ax2.set_yticks([0, 1, 2.3, 3.3])
    ax2.set_yticklabels(["Science Sample", "Control Sample", "<10 pc Sample", "Planet Hosts"], fontsize=7.4)
    ax2.set_xlim(0, max(r_cnts) * 1.48)
    ax2.invert_yaxis()
    ax2.set_xlabel("Stellar / Astrophysical Target Count (D079-D103)")
    ax2.set_title(f"B. V6.1 709-Star Census ({syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms; {syn['total_octave_span']} Octaves)")
    info_box = (
        f"Archives A-AC: {syn['companion_archives_total']} phases (D079-D103)\n"
        f"Exposures: {syn['total_exposures_d079_d103']:,} ({syn['total_integration_hours_d079_d103']:,.1f} h)\n"
        f"Cal. Trials: {syn['total_calibration_trials_d079_d103']:,} | V2 Vetoed: {syn['v2_false_alarms_eliminated_total']:,}\n"
        f"ALMA Complete: B1, B3-B10 (9/9) | HE Unbroken: {syn['high_energy_unbroken_octaves']} oct.\n"
        f"Orbits: #{syn['cumulative_orbital_campaigns']} | Comb Stacks: {syn['cumulative_comb_stacks']} | ETI: 0"
    )
    ax2.text(
        0.98, 0.62, info_box, transform=ax2.transAxes, ha="right", va="center",
        fontsize=6.9, bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7fafc", edgecolor="#4a5568", lw=0.8),
    )
    ax2.grid(True, axis="x", alpha=0.22)

    fig.suptitle(f"Phase D103 (V6.1): 709-Star Panchromatic Bridge Synthesis (0.0000157-8,556.42 um; 49 Spectrographs / 79 Arms; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.96)
    _save(fig, fig_dir, "fig114_d103_panchromatic_bridge_and_709star_synthesis.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    az = _load_mod(ws / "analyze.py", "analyze_v61")
    det = _load_mod(ws / "v6_1_detector.py", "v6_1_detector")
    with gzip.open(ws / "bounded_inputs/d103_bounded_bundle.json.gz", "rb") as gz:
        bundle = json.loads(gz.read().decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig109_nustar_hard_xray(res_dir, bundle, az, fig_dir)
    fig110_xmm_newton_rgs(res_dir, bundle, az, fig_dir)
    fig111_alma_b9_b10(res_dir, bundle, az, fig_dir)
    fig112_drift_and_comb_60campaigns(res_dir, orb_json, det, fig_dir)
    fig113_panchromatic_29octaves(res_dir, ws, bundle, fig_dir)
    fig114_bridge_and_709star_synthesis(res_dir, fig_dir)
    print(f"Rendered 6 D103 figures -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
