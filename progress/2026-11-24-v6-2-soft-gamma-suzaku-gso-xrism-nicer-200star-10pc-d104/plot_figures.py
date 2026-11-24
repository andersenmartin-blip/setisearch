#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D104 (`V6.2`) Publication Figure Generator (`fig115–fig120` @ 240 DPI).
Generates:
  - fig115_d104_suzaku_hxd_gso_soft_gamma_50_600kev.png
  - fig116_d104_xrism_resolve_microcalorimeter_open.png
  - fig117_d104_nicer_xti_and_15p05_he_octave_ladder.png
  - fig118_d104_solar_neighborhood_206stars_carmenes_10pc.png
  - fig119_d104_drift_v62_and_comb_66campaigns.png
  - fig120_d104_global_31p95_octave_755star_bridge_synthesis.png
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.dpi": 240,
    "savefig.dpi": 240,
    "font.size": 8.5,
    "axes.titlesize": 9.8,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _read_csv(res_dir: Path, name: str) -> list[dict[str, str]]:
    with (res_dir / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_mod(path: Path, mod_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _save(fig: plt.Figure, fig_dir: Path, name: str) -> None:
    fig.savefig(fig_dir / name, dpi=240, bbox_inches="tight", pad_inches=0.22, metadata={})
    plt.close(fig)


def _fmt_power_kw(p_kw: float) -> str:
    if p_kw < 1e-3:
        mw = p_kw * 1e6
        if mw >= 100.0:
            return f"{mw:.1f} mW"
        if mw >= 10.0:
            return f"{mw:.2f} mW"
        return f"{mw:.4f} mW"
    if p_kw < 1.0:
        return f"{p_kw * 1e3:.2f} W"
    if p_kw < 1000.0:
        return f"{p_kw:.2f} kW"
    return f"{p_kw:,.0f} kW"


def _cal_bars(ax: plt.Axes, rows: list[dict[str, str]], title: str, replace_map: dict[str, str]) -> None:
    cls_counts: dict[str, list[int]] = {}
    for r in rows:
        c = r["class"]
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    keys = list(cls_counts.keys())
    pcts = [100.0 * cls_counts[k][0] / cls_counts[k][1] for k in keys]
    lbls = [replace_map.get(k, k) for k in keys]
    x = np.arange(len(keys))
    pal = ["#1b9e77", "#d95f02", "#7570b3", "#2b8cbe", "#636363"]
    bars = ax.bar(x, pcts, color=pal[:len(keys)], edgecolor="black", lw=0.7, width=0.62)
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=7.0)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Pass / Rejection Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, keys):
        p, t = cls_counts[k]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig115_suzaku_hxd_gso(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    suz_obs = _read_csv(res_dir, "SUZAKU_HXD_GSO_18OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V62_SUZAKU_GSO_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_2_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "SUZAKU_HXD_GSO"]
    raw_tot = int(json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]["suzaku_gso_raw_candidates"])
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V62_SUZAKU_GSO_240
    _cal_bars(
        ax1, cal,
        f"A. Suzaku HXD-GSO Dual-Well Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_DUAL_WELL_BEACON": "Clean\nWell A+B",
            "SINGLE_WELL_GLITCH_VETO": "Single-Well\nGlitch",
            "GSO_ACTIVATION_ATLAS_VETO": "Gd/I-123\nActivation",
            "SOFT_GAMMA_CONTINUUM_NULL": "Gamma\nContinuum",
            "BROAD_COMPTON_OR_1BIN_VETO": "Broad / 1-Bin\nHump",
        },
    )

    # Panel B: Archival Suzaku HXD-GSO Dual-Well Spectrum (ABDOR Science or EVLAC)
    gso_exps = [e for e in bundle["exposures"] if e["instrument"] == "SUZAKU_HXD_GSO"]
    pref = next((e for e in gso_exps if e["star"] == "ABDOR"), None) or next((e for e in gso_exps if e["role"] == "SCIENCE"), gso_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"])
    ona = az._decode_arr_any(pref["cnt_a_c"])
    onb = az._decode_arr_any(pref["cnt_b_c"])
    ax2.step(ek, ona, where="mid", color="#1a365d", lw=0.95, alpha=0.88, label="Even-UNITID Sub-Stream A")
    ax2.step(ek, onb, where="mid", color="#d95f02", lw=0.85, alpha=0.78, label="Odd-UNITID Sub-Stream B")
    ymax_g = max(10.0, float(max(np.max(ona), np.max(onb))))
    for e_l, xm, yf, lbl in [(66.8, 1.03, 0.90, "152Gd/153Gd 67 keV"), (155.0, 1.03, 0.85, "Gd/GSO 155 keV"), (191.0, 1.03, 0.62, "123I 191 keV"), (511.0, 0.88, 0.88, "e+e- 511 keV")]:
        ax2.axvline(e_l, color="#7570b3", ls=":", lw=0.9, alpha=0.85)
        ax2.text(e_l * xm, ymax_g * yf, lbl, rotation=90, va="top", fontsize=6.3, color="#553c9a")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(50.0, 600.0)
    ax2.set_xlabel("Photon Energy (keV, 50-600 keV)")
    ax2.set_ylabel("Counts per 2-keV GSO Channel (log)")
    ax2.set_title(f"B. Archival Suzaku HXD-GSO Split Spectrum ({pref['star']}, exp={float(pref['exp_s']):.0f}s)")
    ax2.legend(loc="lower left", fontsize=6.8, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Li & Ma Significance vs Dual-Well Binomial Consistency
    snrs = [float(r["snr"]) for r in sc]
    pvals = [-math.log10(max(1e-12, float(r["split_p"]) if r.get("split_p") else 1.0)) for r in sc]
    cols = ["#b30000" if r["qualified_v62"] == "True" else "#2b8cbe" for r in sc]
    ax3.scatter(snrs, pvals, s=26, c=cols, edgecolor="black", lw=0.35, alpha=0.85, zorder=4)
    ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0, label="S_LiMa >= 6.0 Threshold")
    ax3.axhline(2.0, color="#d95f02", ls="--", lw=1.0, label="Sub-Stream Discordance Cut (p=0.01)")
    ax3.set_xlabel("Joint Li & Ma Significance (S_LiMa)")
    ax3.set_ylabel("-log10(Dual-Well Split Binomial p)")
    ax3.set_title(f"C. Suzaku GSO Candidates ({raw_tot} Raw / {len(sc)} Ledger -> 0 Pre-S2 -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: All 18 Suzaku HXD-GSO 10-m EIRP Bounds
    gso_sorted = sorted(suz_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:18]
    y4 = np.arange(len(gso_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in gso_sorted]
    ax4.barh(y4, vals4, color=["#1a365d" if r["role"] == "SCIENCE" else "#718096" for r in gso_sorted], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in gso_sorted], fontsize=6.6)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 35.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.1, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    best_g = gso_sorted[0]
    ax4.set_title(f"D. All 18 Suzaku GSO Soft-Gamma EIRP Bounds ({best_g['star']} {_fmt_power_kw(float(best_g['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D104 (V6.2): NASA/JAXA Suzaku HXD-GSO Soft-Gamma Survey (18 Observations; 50-600 keV; 0.0207-0.2480 A; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig115_d104_suzaku_hxd_gso_soft_gamma_50_600kev.png")


def fig116_xrism_resolve(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    xr_obs = _read_csv(res_dir, "XRISM_RESOLVE_20OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V62_XRISM_RESOLVE_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_2_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "XRISM_RESOLVE"]
    raw_tot = int(json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]["xrism_resolve_raw_candidates"])
    cal_p = sum(int(r["passed"]) for r in cal)
    qual_n = sum(1 for r in sc if r["qualified_v62"] == "True")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V62_XRISM_RESOLVE_240
    _cal_bars(
        ax1, cal,
        f"A. XRISM Resolve Microcalorimeter Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_MICROCAL_BEACON": "Clean\nCheckerboard",
            "CHECKERBOARD_PIXEL_VETO": "Even/Odd\nPixel Split",
            "RESOLVE_ATLAS_VETO": "Coronal +\n55Fe/Si Atlas",
            "RESOLVE_CONTINUUM_NULL": "X-Ray\nContinuum",
            "BROAD_WIND_OR_1BIN_VETO": "Broad / 1-Bin\nVeto",
        },
    )

    # Panel B: Archival XRISM Resolve OPEN Spectrum (SIGMAGEM)
    xr_exps = [e for e in bundle["exposures"] if e["instrument"] == "XRISM_RESOLVE"]
    pref = next((e for e in xr_exps if e["star"] == "SIGMAGEM"), None) or next((e for e in xr_exps if e["role"] == "SCIENCE"), xr_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"])
    ona = az._decode_arr_any(pref["cnt_a_c"])
    onb = az._decode_arr_any(pref["cnt_b_c"])
    ax2.step(ek, ona, where="mid", color="#1a365d", lw=0.75, alpha=0.88, label="Even-PIXEL Sub-Array")
    ax2.step(ek, onb, where="mid", color="#2b8cbe", lw=0.70, alpha=0.75, label="Odd-PIXEL Sub-Array (Pixel 12 Excl.)")
    ymax_x = max(5.0, float(max(np.max(ona), np.max(onb))))
    for e_l, yf, lbl in [(1.740, 0.90, "Si Ka 1.74"), (2.461, 0.65, "S XV 2.46"), (3.140, 0.55, "Ar XVII 3.14"), (6.400, 0.88, "Fe Ka 6.40"), (6.700, 0.62, "Fe XXV 6.70"), (6.970, 0.42, "Fe XXVI 6.97")]:
        ax2.axvline(e_l, color="#7570b3", ls=":", lw=0.8, alpha=0.8)
        ax2.text(e_l * 1.015, ymax_x * yf, lbl, rotation=90, va="top", fontsize=6.1, color="#553c9a")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(1.70, 12.0)
    ax2.set_ylim(bottom=0.0, top=ymax_x * 1.85)
    ax2.set_xlabel("Photon Energy (keV, FILTER='OPEN', 4.5 eV FWHM)")
    ax2.set_ylabel("Counts per 2-eV Resolve Channel")
    ax2.set_title(f"B. Archival XRISM Resolve OPEN Spectrum ({pref['star']}, Excl. Cal Pix12={pref.get('n_cal_pixel12_excluded', 0)})")
    ax2.legend(loc="upper left", fontsize=6.5, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: XRISM Resolve Candidates (Raw vs Pre-S2 Si-Ka/AGN/Coronal Vetoes)
    snrs = [float(r["snr"]) for r in sc]
    pvals = [-math.log10(max(1e-12, float(r["split_p"]) if r.get("split_p") else 1.0)) for r in sc]
    cols = ["#b30000" if r["qualified_v62"] == "True" else "#2b8cbe" for r in sc]
    ax3.scatter(snrs, pvals, s=30, c=cols, edgecolor="black", lw=0.4, alpha=0.88, zorder=4)
    ax3.scatter([], [], s=30, c="#b30000", edgecolor="black", lw=0.4, label=f"Pre-S2 ({qual_n}: Si Ka 1.74 keV / Redshifted AGN / S XVI)")
    ax3.scatter([], [], s=30, c="#2b8cbe", edgecolor="black", lw=0.4, label=f"Stage-1 Atlas/Pixel Vetoed ({len(sc) - qual_n})")
    ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0)
    ax3.set_xlabel("Joint Li & Ma Significance (S_LiMa)")
    ax3.set_ylabel("-log10(Checkerboard Pixel Binomial p)")
    ax3.set_title(f"C. XRISM Resolve Candidates ({raw_tot} Raw / {len(sc)} Ledger -> {qual_n} Pre-S2 -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Top 16 XRISM Resolve 10-m EIRP Bounds
    xr_sorted = sorted(xr_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(xr_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in xr_sorted]
    ax4.barh(y4, vals4, color=["#2b8cbe" if r["role"] == "SCIENCE" else "#718096" for r in xr_sorted], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in xr_sorted], fontsize=6.9)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 32.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.3, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    best_x = xr_sorted[0]
    ax4.set_title(f"D. Best 16 XRISM Resolve EIRP Bounds ({best_x['star']} {_fmt_power_kw(float(best_x['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D104 (V6.2): XRISM Resolve 4.5 eV Microcalorimeter Survey (20 OPEN Obs; 1.7-12 keV; Strict Pixel!=12; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig116_d104_xrism_resolve_microcalorimeter_open.png")


def fig117_nicer_and_he_ladder(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    ni_obs = _read_csv(res_dir, "NICER_XTI_20OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V62_NICER_XTI_180.csv")
    spec_a = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D104.json").read_text())
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: 15.048 Unbroken Soft-Gamma-to-EUV Ladder (0.02066 A to 699.8 A)
    bands_he = [
        ("Suzaku HXD-GSO\n(50-600 keV; D104)", 0.02066, 0.2480, "#b30000"),
        ("NuSTAR FPMA+FPMB\n(3-79 keV; D103)", 0.1569, 4.1328, "#1a365d"),
        ("XRISM Resolve OPEN\n(1.7-12 keV; D104)", 1.0332, 7.2932, "#e7298a"),
        ("NICER XTI 52-MPU\n(0.35-10 keV; D104)", 1.2398, 35.4241, "#66a61e"),
        ("Chandra HETG\n(0.4-10 keV; D102)", 1.24, 31.0, "#2b8cbe"),
        ("XMM-Newton RGS\n(5-38 A; D103)", 5.0, 38.0, "#d95f02"),
        ("Chandra LETG\n(0.07-10 keV; D102)", 1.24, 175.0, "#1b9e77"),
        ("EUVE DS/S\n(70-700 A; D102)", 70.0, 699.80, "#7570b3"),
    ]
    ax1.axvspan(699.80, 905.0, color="#fed7d7", alpha=0.75, label="ISM H Photoionization Wall (700-905 A)")
    for yi, (lbl, a_lo, a_hi, col) in enumerate(bands_he):
        ax1.plot([a_lo, a_hi], [yi, yi], color=col, lw=8.0, solid_capstyle="butt")
    ax1.set_yticks(np.arange(len(bands_he)))
    ax1.set_yticklabels([b[0] for b in bands_he], fontsize=6.6)
    ax1.set_xscale("log")
    ax1.set_xlim(0.012, 1600.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Wavelength (Angstrom, log scale)")
    ax1.set_title(f"A. Unbroken Soft-Gamma-to-EUV Ladder ({spec_a['high_energy_unbroken_octaves']:.3f} Octaves)")
    ax1.legend(loc="lower left", fontsize=6.8, frameon=True)
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Archival NICER XTI Split Spectrum (YZCET)
    ni_exps = [e for e in bundle["exposures"] if e["instrument"] == "NICER_XTI"]
    pref = next((e for e in ni_exps if e["star"] == "YZCET"), None) or next((e for e in ni_exps if e["role"] == "SCIENCE"), ni_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"])
    ona = az._decode_arr_any(pref["cnt_a_c"])
    onb = az._decode_arr_any(pref["cnt_b_c"])
    ax2.step(ek, ona, where="mid", color="#1b9e77", lw=0.95, alpha=0.88, label="Even-MPU Sub-Array (26 detectors)")
    ax2.step(ek, onb, where="mid", color="#d95f02", lw=0.85, alpha=0.78, label="Odd-MPU Sub-Array (26 detectors)")
    ymax_n = max(5.0, float(max(np.max(ona), np.max(onb))))
    for e_l, yf, lbl in [(0.57, 0.88, "O VII"), (0.65, 0.68, "O VIII"), (0.826, 0.90, "Fe XVII"), (1.02, 0.56, "Ne X"), (6.70, 0.78, "Fe XXV")]:
        ax2.axvline(e_l, color="#7570b3", ls=":", lw=0.8, alpha=0.8)
        ax2.text(e_l * 1.03, ymax_n * yf, lbl, rotation=90, va="top", fontsize=6.3, color="#553c9a")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(0.35, 10.0)
    ax2.set_ylim(bottom=0.0, top=ymax_n * 1.45)
    ax2.set_xlabel("Photon Energy (keV, 0.35-10.0 keV)")
    ax2.set_ylabel("Counts per 20-eV NICER Channel")
    ax2.set_title(f"B. Archival NICER XTI MPU-Split Spectrum ({pref['star']}, d={float(pref['dist_pc']):.2f} pc)")
    ax2.legend(loc="lower left", fontsize=6.6, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: CALIBRATION_V62_NICER_XTI_180
    _cal_bars(
        ax3, cal,
        f"C. NICER XTI Dual-MPU Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_MPU_BEACON": "Clean\nMPU A+B",
            "SINGLE_MPU_GLITCH_VETO": "Single-MPU\nGlitch",
            "NICER_ATLAS_VETO": "Coronal / Au\nAtlas",
            "BROAD_OR_NULL_VETO": "Broad / Null\nVeto",
        },
    )

    # Panel D: Top 16 NICER XTI 10-m EIRP Bounds
    ni_sorted = sorted(ni_obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(ni_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in ni_sorted]
    ax4.barh(y4, vals4, color=["#1b9e77" if r["role"] == "SCIENCE" else "#718096" for r in ni_sorted], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({float(r['dist_pc']):.1f}pc)" for r in ni_sorted], fontsize=6.5)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 32.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.18, yi, _fmt_power_kw(v), va="center", fontsize=6.2, fontweight="bold")
    ax4.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    best_n = ni_sorted[0]
    ax4.set_title(f"D. Best 16 NICER XTI EIRP Bounds ({best_n['star']} {_fmt_power_kw(float(best_n['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D104 (V6.2): NASA NICER XTI Timing-X-Ray Survey & {spec_a['high_energy_unbroken_octaves']:.3f} Unbroken High-Energy Octaves (0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig117_d104_nicer_xti_and_15p05_he_octave_ladder.png")


def fig118_solar_neighborhood_206(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    s206 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_206STARS.csv")
    eirp104 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D104.csv")
    fg = _read_csv(res_dir, "FOUR_GEN_BENCHMARK_D104.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Histogram of 206 <10 pc panchromatic limits
    lims = [float(r["min_panchromatic_10m_kw"]) for r in s206 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med_v = float(np.median(lims))
    ax1.hist(np.log10(lims), bins=25, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax1.axvline(math.log10(med_v), color="#b30000", ls="--", lw=1.6, label=f"Median: {med_v:.4f} kW ({len(s206)} stars <10 pc)")
    ax1.set_xlabel("log10(Minimum Panchromatic 10-m EIRP Limit / kW)")
    ax1.set_ylabel("Target Count")
    ax1.set_title(f"A. >200-Star Solar Neighborhood Milestone ({len(s206)} Stars <10 pc; Best {_fmt_power_kw(min(lims))})")
    ax1.legend(loc="upper left", fontsize=6.9, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: Distance vs Minimum 10-m EIRP Limit (0-10 pc)
    d_old, l_old, d_new, l_new = [], [], [], []
    new_pts = []
    for r in s206:
        if not r.get("min_panchromatic_10m_kw") or float(r["min_panchromatic_10m_kw"]) <= 0:
            continue
        dp = float(r["dist_pc"])
        pk = float(r["min_panchromatic_10m_kw"])
        phs = str(r["phases"]).split("+")
        if phs == ["D104"]:
            d_new.append(dp); l_new.append(pk); new_pts.append((dp, pk, r["star"]))
        else:
            d_old.append(dp); l_old.append(pk)
    ax2.scatter(d_old, l_old, s=22, color="#718096", alpha=0.70, edgecolor="black", lw=0.35, label=f"D079-D103 Finite Limits ({len(d_old)})")
    ax2.scatter(d_new, l_new, s=44, color="#b30000", marker="^", edgecolor="black", lw=0.5, zorder=4, label=f"D104 Brand-New <10 pc (+{len(d_new)} stars)")
    ax2.set_yscale("log")
    ax2.set_xlim(1.0, 10.2)
    ax2.set_xlabel("Heliocentric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title("B. Distance vs Sensitivity Within 10 pc (+18 New Targets in D104)")
    ax2.legend(loc="lower right", fontsize=6.9, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Representative Archival CARMENES VIS Spectrum (J12189+111)
    cm_exps = [e for e in bundle["exposures"] if e["instrument"] == "CARMENES_VIS"]
    pref = next((e for e in cm_exps if e["star"] == "J12189+111"), cm_exps[0])
    wb = float(pref["w0"]) + float(pref["dw"]) * np.arange(int(pref["npts"]), dtype=np.float64)
    fl = az._decode_arr_any(pref["flux_c"])
    step_ds = max(1, len(wb) // 6000)
    ax3.plot(wb[::step_ds], fl[::step_ds], color="#2b8cbe", lw=0.55, alpha=0.88, label=f"CARMENES VIS (d={float(pref['dist_pc']):.2f} pc, 520-960 nm)")
    ax3.axvline(6564.61, color="#b30000", ls=":", lw=0.9, label="H-alpha (6564.6 A)")
    ax3.set_xlim(5200.0, 9600.0)
    ax3.set_xlabel("Barycentric Wavelength (Angstrom)")
    ax3.set_ylabel("Relative / Blaze-Normalized Flux")
    ax3.set_title(f"C. Archival CARMENES VIS <10 pc Spectrum ({pref['star']}, Best 0.1905 kW)")
    ax3.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Top 16 CARMENES VIS <10 pc Optical 10-m EIRP Limits + 4-Gen Summary
    cm_best: dict[str, float] = {}
    cm_dist: dict[str, float] = {}
    for r in eirp104:
        if r["instrument"] == "CARMENES_VIS":
            st = r["star"]
            pk = float(r["p_beam_10m_kw"])
            if st not in cm_best or pk < cm_best[st]:
                cm_best[st] = pk
                cm_dist[st] = float(r["dist_pc"])
    cm_sorted = sorted(cm_best.items(), key=lambda kv: kv[1])[:16]
    y4 = np.arange(len(cm_sorted))
    vals4 = [kv[1] for kv in cm_sorted]
    ax4.barh(y4, vals4, color="#2b8cbe", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{st} ({cm_dist[st]:.2f}pc)" for st, _ in cm_sorted], fontsize=6.5)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.45, max(vals4) * 18.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.15, yi, f"{v:.3f} kW", va="center", fontsize=6.2, fontweight="bold")
    fg_txt = "\n".join(f"{r['instrument']}: G1={r['g1_seeds']}->G8={r['g8_pass']}->ETI=0" for r in fg)
    ax4.text(0.98, 0.16, fg_txt, transform=ax4.transAxes, ha="right", va="bottom", fontsize=6.1, bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7fafc", edgecolor="#4a5568", lw=0.7))
    ax4.set_xlabel("6-sigma 10-m Optical Beam EIRP Limit (kW)")
    ax4.set_title("D. All 16 CARMENES VIS <10 pc Limits & 4-Gen Optical Funnel")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D104 (V6.2): Crossing 200 Stars Within 10 pc ({len(s206)} Unique Targets; +16 CARMENES VIS + Wolf 424 + AP Col; 0 ETI)", fontsize=10.6, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig118_d104_solar_neighborhood_206stars_carmenes_10pc.png")


def fig119_drift_and_comb_66campaigns(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6_D104.csv")
    ek66 = _read_csv(res_dir, "DRIFT_V62_ECCENTRIC_KEPLERIAN_66CAMPAIGNS.csv")
    cd66 = _read_csv(res_dir, "COMB_DRIFT_V62_66CAMPAIGNS.csv")
    cal_dc = _read_csv(res_dir, "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Coherent Drifting-Comb Calibration vs Static V4.1 Baseline
    cls_map: dict[str, list[int]] = {}
    for r in cal_dc:
        c = r["class"]
        cls_map.setdefault(c, [0, 0])
        cls_map[c][0] += int(r["passed"])
        cls_map[c][1] += 1
    lbls_a = ["V6.2 Kepler\nComb (60)", "V6.2 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
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

    # Panel B: Live Orbital Campaigns #169-#174 Planetary RV Curves
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
        ax2.plot(ph, vr_ms, lw=1.65, color=pal[idx_o % len(pal)], label=f"#{r['campaign_index']} {st} (N={r['n_epochs']}, P={p_d:.1f}d, Kp={kp*1e3:.1f} m/s)")
    pad_y = max(1.0, 0.22 * (ymax_v - ymin_v))
    ax2.set_ylim(ymin_v - 0.55 * pad_y, ymax_v + 1.45 * pad_y)
    ax2.set_xlabel("Orbital Phase phi")
    ax2.set_ylabel("Planetary Keplerian RV (m/s)")
    ax2.set_title("B. ESO ESPRESSO + HARPS Orbits #169-#174 (Multi-Epoch Planetary Kinematics)")
    ax2.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: All 66 Cumulative DRIFT_V62 Campaigns
    x66 = np.arange(len(ek66))
    ax3.bar(x66, [int(r["n_trajectories_evaluated"]) for r in ek66], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x66, [int(r["raw_coherent_survivors"]) for r in ek66], color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Raw Survivors ({sum_raw['drift_v62_66campaigns_raw_survivors']:,})")
    ax3.bar(x66, [int(r["stage2_verified_eti"]) for r in ek66], color="#1b9e77", label="Verified ETI (0/66)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek66) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D104, 7-12 D103, ..., 61-66 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    ax3.set_title(f"C. 66-Campaign DRIFT_V62 ({sum_raw['drift_v62_66campaigns_trajectories']:,} Traj / {sum_raw['drift_v62_66campaigns_pixel_integrals']/1e9:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 66 Cumulative COMB_DRIFT_V62 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd66])
    qual_cd = np.asarray([int(r["comb_qualified_v62"]) for r in cd66])
    ax4.plot(x66, raw_cd, "-o", ms=2.8, color="#d95f02", lw=1.05, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v62_66campaigns_raw_candidates']:,})")
    ax4.plot(x66, qual_cd, "-s", ms=2.8, color="#7570b3", lw=1.05, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v62_66campaigns_qualified_pre_stage2']})")
    ax4.plot(x66, np.zeros_like(x66), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/66)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#66 Across D094-D104)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 66-Campaign COMB_DRIFT_V62 ({sum_raw['comb_drift_v62_66campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.8, frameon=True)
    ax4.grid(True, alpha=0.22)

    pix_b = sum_raw["drift_v62_66campaigns_pixel_integrals"] / 1e9
    fig.suptitle(f"Phase D104 (V6.2): Orbits #169-#174 & 66-Campaign Coherent DRIFT_V62 + COMB_DRIFT_V62 ({pix_b:.2f}B Pixel Integrals; 0 ETI)", fontsize=10.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig119_d104_drift_v62_and_comb_66campaigns.png")


def fig120_global_synthesis_755(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json["unified_755star_panchromatic_v6_2_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp104 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D104.csv")
    ell = _read_csv(res_dir, "MULTIEVENT_ELLIPSOID_755STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 0.000002066-8,556.42 um Sensitivity Frontier (31.947 Octaves)
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Wall (700-905 A)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D104" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=9, color="#bdbdbd", alpha=0.48, zorder=1, label="D079-D103 (0.0000157-8,556.4 um)")

    inst_groups = [
        ("SUZAKU_HXD_GSO", "#b30000", "*", "D104 Suzaku GSO (50-600 keV)"),
        ("XRISM_RESOLVE", "#e7298a", "^", "D104 XRISM Resolve (1.7-12 keV)"),
        ("NICER_XTI", "#1b9e77", "v", "D104 NICER XTI (0.35-10 keV)"),
        ("CARMENES_VIS", "#2b8cbe", "o", "D104 CARMENES VIS (<10 pc)"),
        ("ESO_ESPRESSO", "#d95f02", "s", "D104 ESPRESSO Orbits"),
        ("ESO_HARPS", "#66a61e", "D", "D104 HARPS Orbits"),
    ]
    for ik, col, mk, lbl in inst_groups:
        sub = [r for r in eirp104 if r["instrument"] == ik]
        ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=24 if mk != "*" else 52, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.1e-6, 25000.0)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma 10-m EIRP Limit (kW)")
    ax1.set_title(f"A. Unified {syn['spectrographs']}-Spectrograph Sensitivity Frontier ({syn['total_octave_span']} Octaves)")
    ax1.legend(loc="lower right", fontsize=5.5, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-755 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V6_1_PHASES_SNAPSHOT.json").read_text())["prior_unified_709_rows"]}
    all104_st = {e["star"] for e in bundle["exposures"]}
    brand46 = all104_st - prior_st
    bridges18 = all104_st & prior_st
    ra_p, dec_p, ra_b, dec_b, ra_n, dec_n = [], [], [], [], [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand46:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in bridges18:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D103 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D104 Bridges ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D104 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.9, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: All 18 D104 Calibration Suites (3,771 Trials; 58,299 Cumulative)
    cal_sum = s_json["synthetic_calibration_3771_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V62_", "V6.2 ")
        .replace("CALIBRATION_V61_", "V6.1 ")
        .replace("CALIBRATION_V60_", "V6.0 ")
        .replace("CALIBRATION_V59_", "V5.9 ")
        .replace("CALIBRATION_V58_", "")
        .replace("CALIBRATION_", "")
        .replace("DETECTOR_V58_", "")
        .replace("_CALIBRATION", "")
        .replace("_", " ")
        for k in s_names
    ]
    y3 = np.arange(len(s_names))
    ax3.barh(y3, s_pcts, color=["#b30000" if "V6.2" in s else "#2b8cbe" for s in short_s], edgecolor="black", lw=0.45)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(short_s, fontsize=5.4)
    ax3.set_xlim(92.0, 102.0)
    ax3.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax3.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=5.4, color="white", fontweight="bold")
    ax3.set_xlabel("Suite Pass Rate (%)")
    ax3.set_title(f"C. D104 18-Suite Calibration ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d104']:,})")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: Cross-Band Bridge Matrix Heatmap (Soft Gamma -> mm, 11 Regimes)
    regs = [
        ("Soft g\nGSO", 1e-6, 1.5e-5),
        ("Hard X\nNuSTAR", 1.5e-5, 4.5e-4),
        ("Soft X\nXMM/XR/NI", 4.5e-4, 0.0176),
        ("EUV\nEUVE", 0.007, 0.072),
        ("UV\nHST/IUE", 0.090, 0.32),
        ("Opt\n0.3-1", 0.32, 1.0),
        ("NIR\n1-5", 1.0, 5.0),
        ("MIR\n5-30", 5.0, 30.0),
        ("FIR\n30-310", 30.0, 310.0),
        ("Sub-mm\nB7-10", 310.0, 1100.0),
        ("mm\nB1-6", 1100.0, 9000.0),
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
        "EVLAC", "AUMIC", "PROXIMACEN", "ADLEO", "ABDOR", "SIGMAGEM", "BETELGEUSE",
        "SIRIUSA", "EPSERI", "VEGA", "FOMALHAUT", "ALPCENA", "61CYGB", "TAUCET",
        "SSCYG", "ETACAR", "NGC1068", "NGC4945", "CENA", "IC4329A",
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
    im = ax4.imshow(mat, aspect="auto", cmap=cmap, vmin=-6.5, vmax=6.0)
    ax4.set_xticks(np.arange(len(regs)))
    ax4.set_xticklabels([r[0] for r in regs], fontsize=5.8)
    ax4.set_yticks(np.arange(len(focus)))
    ax4.set_yticklabels(focus, fontsize=6.6)
    for ri in range(len(focus)):
        for ci in range(len(regs)):
            v = mat[ri, ci]
            if math.isfinite(v):
                ax4.text(ci, ri, f"{v:+.1f}", ha="center", va="center", fontsize=5.0, color="white" if v < 0.0 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax4, fraction=0.042, pad=0.02)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.2)
    ax4.set_title(f"D. Panchromatic Bridge Matrix ({syn['multi_phase_targets_total']} Multi-Phase Targets; {syn['panchromatic_bridge_cells_total']} Cells)")

    fig.suptitle(f"Phase D104 (V6.2): {syn['unique_stars_total']} Targets Across {syn['total_octave_span']} Octaves ({syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms; {syn['within_10pc_unique_stars']} <10 pc; 0 ETI)", fontsize=10.6, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig120_d104_global_31p95_octave_755star_bridge_synthesis.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    az = _load_mod(ws / "analyze.py", "analyze_v62")
    det = _load_mod(ws / "v6_2_detector.py", "v6_2_detector")
    with gzip.open(ws / "bounded_inputs/d104_bounded_bundle.json.gz", "rb") as gz:
        bundle = json.loads(gz.read().decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig115_suzaku_hxd_gso(res_dir, bundle, az, fig_dir)
    fig116_xrism_resolve(res_dir, bundle, az, fig_dir)
    fig117_nicer_and_he_ladder(res_dir, bundle, az, fig_dir)
    fig118_solar_neighborhood_206(res_dir, bundle, az, fig_dir)
    fig119_drift_and_comb_66campaigns(res_dir, orb_json, det, fig_dir)
    fig120_global_synthesis_755(res_dir, ws, bundle, fig_dir)
    print(f"Rendered 6 D104 figures -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
