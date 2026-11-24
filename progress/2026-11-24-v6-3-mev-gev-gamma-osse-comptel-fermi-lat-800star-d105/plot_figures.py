#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D105 (V6.3) Six-Figure Publication Suite (fig121-fig126, 240 DPI, metadata={}):
  - fig121: CGRO OSSE Soft-MeV Gamma-Ray Survey (26 Obs; 50 keV - 9.09 MeV)
  - fig122: CGRO COMPTEL MeV Gamma-Ray Survey (20 Targets across 8 VP; 0.75 - 30.0 MeV)
  - fig123: Fermi LAT Pass-8 GeV Survey (40 Targets; 30 MeV - 300 GeV) & 33.979-Octave HE Ladder
  - fig124: Solar Neighborhood 230 <10 pc Census (+24 Brand-New Stars) & Optical 4-Gen Funnel
  - fig125: Orbits #175-#180 & 72-Campaign Coherent DRIFT_V63 + COMB_DRIFT_V63 Synthesis
  - fig126: Global 50.878-Octave, 806-Star, 107 SCIENCE / 129 Multi-Phase Bridge Synthesis
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
    "font.size": 8.2,
    "axes.titlesize": 9.0,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.0,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 6.6,
    "figure.titlesize": 10.6,
})


def _load_mod(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_csv(res_dir: Path, name: str) -> list[dict[str, str]]:
    with (res_dir / name).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fig_dir: Path, fname: str) -> Path:
    out = fig_dir / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14, metadata={})
    plt.close(fig)
    return out


def _fmt_power_kw(v: float) -> str:
    if not math.isfinite(v) or v <= 0.0:
        return "N/A"
    if v < 1e-18:
        return f"{v * 1e21:.2f} aW"
    if v < 1e-15:
        return f"{v * 1e18:.2f} fW"
    if v < 1e-12:
        return f"{v * 1e15:.2f} pW"
    if v < 1e-9:
        return f"{v * 1e12:.2f} nW"
    if v < 1e-6:
        return f"{v * 1e9:.2f} uW"
    if v < 1e-3:
        return f"{v * 1e6:.3f} mW"
    if v < 1.0:
        return f"{v * 1e3:.2f} W"
    if v < 1e3:
        return f"{v:.3f} kW"
    if v < 1e6:
        return f"{v / 1e3:.2f} MW"
    if v < 1e9:
        return f"{v / 1e6:.2f} GW"
    if v < 1e12:
        return f"{v / 1e9:.2f} TW"
    if v < 1e15:
        return f"{v / 1e12:.2f} PW"
    return f"{v:.2e} kW"


def _cal_bars(ax: plt.Axes, cal_rows: list[dict[str, str]], title: str, replace_map: dict[str, str]) -> None:
    cls_counts: dict[str, list[int]] = {}
    for r in cal_rows:
        c = r.get("class", "ALL")
        cls_counts.setdefault(c, [0, 0])
        cls_counts[c][0] += int(r["passed"])
        cls_counts[c][1] += 1
    keys = list(cls_counts.keys())
    pcts = [100.0 * cls_counts[k][0] / max(1, cls_counts[k][1]) for k in keys]
    lbls = [replace_map.get(k, k.replace("_", "\n")) for k in keys]
    x = np.arange(len(keys))
    pal = ["#1b9e77", "#d95f02", "#7570b3", "#2b8cbe", "#636363", "#b30000"]
    bars = ax.bar(x, pcts, color=[pal[i % len(pal)] for i in range(len(keys))], edgecolor="black", lw=0.7, width=0.62)
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=6.6)
    ax.set_ylim(0, 120)
    ax.set_ylabel("Pass / Rejection Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, keys):
        p, t = cls_counts[k]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig121_cgro_osse(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    obs = _read_csv(res_dir, "CGRO_OSSE_26OBS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V63_CGRO_OSSE_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_3_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "CGRO_OSSE"]
    raw_tot = int(json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]["cgro_osse_raw_candidates"])
    qual_tot = int(json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]["cgro_osse_qualified_pre_stage2"])
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V63_CGRO_OSSE_240
    _cal_bars(
        ax1, cal,
        f"A. CGRO OSSE Sub-Period Split Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_OSSE_MEV_BEACON": "Clean\nOSSE A+B",
            "SINGLE_SUBPERIOD_GLITCH_VETO": "Single Sub-Per.\nGlitch Veto",
            "OSSE_NUCLEAR_ATLAS_VETO": "511 keV / 12C*\nNuclear Atlas",
            "OSSE_POWERLAW_NULL": "Power-Law\nContinuum",
            "BROAD_OR_1BIN_VETO": "Broad / 1-Bin\nVeto",
        },
    )

    # Panel B: Archival CGRO OSSE Spectrum (3C273 or CYGX1)
    o_exps = [e for e in bundle["exposures"] if e["instrument"] == "CGRO_OSSE"]
    pref = next((e for e in o_exps if e["star"] == "CYGX1"), None) or next((e for e in o_exps if e["role"] == "SCIENCE"), o_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"])
    ra = az._decode_arr_any(pref["rate_a_c"])
    rb = az._decode_arr_any(pref["rate_b_c"])
    ax2.step(ek, ra, where="mid", color="#1a365d", lw=0.95, alpha=0.88, label="Sub-Period Stream A")
    ax2.step(ek, rb, where="mid", color="#d95f02", lw=0.85, alpha=0.78, label="Sub-Period Stream B")
    ymax_o = max(0.05, float(max(np.max(np.abs(ra)), np.max(np.abs(rb)))))
    for e_l, xm, yf, lbl in [(511.0, 1.04, 0.90, "e+e- 511 keV"), (2223.0, 1.04, 0.72, "n-p 2.223 MeV"), (4438.0, 1.04, 0.56, "12C* 4.438 MeV"), (6129.0, 0.88, 0.80, "16O* 6.129 MeV")]:
        ax2.axvline(e_l, color="#7570b3", ls=":", lw=0.9, alpha=0.85)
        ax2.text(e_l * xm, ymax_o * yf, lbl, rotation=90, va="top", fontsize=6.2, color="#553c9a")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=1e-3)
    ax2.set_xlim(50.0, 9090.0)
    ax2.set_xlabel("Photon Energy (keV, 50 keV - 9.09 MeV)")
    ax2.set_ylabel("Background-Subtracted Rate (cnt/s/keV)")
    ax2.set_title(f"B. Archival CGRO OSSE Split Spectrum ({pref['star']}, exp={float(pref['exp_s']):.0f}s)")
    ax2.legend(loc="lower left", fontsize=6.8, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Significance vs Sub-Period Binomial Consistency
    snrs = [float(r["snr"]) for r in sc] if sc else [0.0]
    pvals = [-math.log10(max(1e-12, float(r["split_p"]) if r.get("split_p") else 1.0)) for r in sc] if sc else [0.0]
    cols = ["#b30000" if r.get("qualified_v63") == "True" else "#2b8cbe" for r in sc] if sc else ["#2b8cbe"]
    ax3.scatter(snrs, pvals, s=26, c=cols, edgecolor="black", lw=0.35, alpha=0.85, zorder=4)
    ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0, label="S_LiMa >= 6.0 Threshold")
    ax3.axhline(2.0, color="#d95f02", ls="--", lw=1.0, label="Sub-Period Discordance Cut (p=0.01)")
    ax3.set_xlabel("Joint Sub-Period Significance (S_OSSE)")
    ax3.set_ylabel("-log10(Sub-Period Split Consistency p)")
    ax3.set_title(f"C. CGRO OSSE Candidates ({raw_tot} Raw / {len(sc)} Ledger -> {qual_tot} Pre-S2 -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Top 18 CGRO OSSE Limits (Physical F_lim + Formal 10-m EIRP)
    o_sorted = sorted(obs, key=lambda r: float(r["p_beam_10m_kw"]))[:18]
    y4 = np.arange(len(o_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in o_sorted]
    ax4.barh(y4, vals4, color=["#1a365d" if r["role"] == "SCIENCE" else "#718096" for r in o_sorted], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["star"] for r in o_sorted], fontsize=6.5)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 4000.0)
    for yi, (r, v) in enumerate(zip(o_sorted, vals4)):
        fl_e = float(r["flux_lim_erg_cm2_s"])
        ax4.text(v * 1.18, yi, f"{_fmt_power_kw(v)} | F={fl_e:.1e}", va="center", fontsize=5.6, fontweight="bold")
    ax4.set_xlabel("6-sigma Formal 10-m EIRP Limit (kW) & Physical F_lim (erg cm^-2 s^-1)")
    best_o = o_sorted[0]
    ax4.set_title(f"D. Best 18 CGRO OSSE Bounds ({best_o['star']} {_fmt_power_kw(float(best_o['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D105 (V6.3): NASA CGRO OSSE Soft-MeV Gamma-Ray Survey (26 Observations; 50 keV - 9.09 MeV; 0 ETI)", fontsize=10.6, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig121_d105_cgro_osse_soft_mev_gamma_50kev_9mev.png")


def fig122_cgro_comptel(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    obs = _read_csv(res_dir, "CGRO_COMPTEL_20TARGETS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V63_CGRO_COMPTEL_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_3_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "CGRO_COMPTEL"]
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]
    raw_tot = int(sum_raw["cgro_comptel_raw_candidates"])
    qual_tot = int(sum_raw["cgro_comptel_qualified_pre_stage2"])
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V63_CGRO_COMPTEL_240
    _cal_bars(
        ax1, cal,
        f"A. CGRO COMPTEL EVP Event-Pair Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_COMPTEL_ARM_BEACON": "Clean\nCOMPTEL A+B",
            "UNALIGNED_ARM_OR_TJD_VETO": "TJD Split /\nUnaligned ARM",
            "COMPTEL_NUCLEAR_ATLAS_VETO": "1.81 / 2.22\nMeV Atlas",
            "COMPTEL_CONTINUUM_NULL": "MeV\nContinuum",
            "BROAD_OR_1BIN_VETO": "Broad / 1-Bin\nVeto",
        },
    )

    # Panel B: Archival CGRO COMPTEL EVP Spectrum
    c_exps = [e for e in bundle["exposures"] if e["instrument"] == "CGRO_COMPTEL"]
    pref = next((e for e in c_exps if e["star"] == "3C273"), None) or next((e for e in c_exps if e["role"] == "SCIENCE"), c_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"]) / 1000.0
    ca = az._decode_arr_any(pref["cnt_a_c"])
    cb = az._decode_arr_any(pref["cnt_b_c"])
    bg = az._decode_arr_any(pref["off_spat_c"]) * az._decode_arr_any(pref["alpha_spat_c"])
    ax2.step(ek, ca, where="mid", color="#1a365d", lw=1.0, alpha=0.88, label="First-Half VP Counts (On A)")
    ax2.step(ek, cb, where="mid", color="#d95f02", lw=0.9, alpha=0.82, label="Second-Half VP Counts (On B)")
    ax2.step(ek, bg, where="mid", color="#636363", lw=0.9, ls="--", alpha=0.85, label="Annulus Background alpha*Off")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(0.75, 30.0)
    ax2.axvline(1.809, color="#7570b3", ls=":", lw=0.9, label="26Al 1.809 / n-p 2.223 MeV")
    ax2.axvline(2.223, color="#7570b3", ls=":", lw=0.9)
    ax2.set_xlabel("Compton-Scatter Energy E_tot (MeV, 0.75-30 MeV)")
    ax2.set_ylabel("ARM-Filtered Event Counts (symlog)")
    ax2.set_title(f"B. Archival CGRO COMPTEL EVP Split Spectrum ({pref['star']}, raw={int(pref['n_events_raw']):,})")
    ax2.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Candidate Scatter
    snrs = [float(r["snr"]) for r in sc] if sc else [0.0]
    pvals = [-math.log10(max(1e-12, float(r["split_p"]) if r.get("split_p") else 1.0)) for r in sc] if sc else [0.0]
    cols = ["#b30000" if r.get("qualified_v63") == "True" else "#2b8cbe" for r in sc] if sc else ["#2b8cbe"]
    ax3.scatter(snrs, pvals, s=28, c=cols, edgecolor="black", lw=0.35, alpha=0.85, zorder=4)
    ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0, label="S_LiMa >= 6.0 Threshold")
    ax3.axhline(2.0, color="#d95f02", ls="--", lw=1.0, label="Half-VP Consistency Cut (p=0.01)")
    ax3.set_xlabel("Joint Li & Ma Significance (S_LiMa)")
    ax3.set_ylabel("-log10(Time-Split Binomial p)")
    ax3.set_title(f"C. COMPTEL Candidates ({raw_tot} Raw / {len(sc)} Ledger -> {qual_tot} Pre-S2 -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: All 20 CGRO COMPTEL Bounds
    c_sorted = sorted(obs, key=lambda r: float(r["p_beam_10m_kw"]))[:20]
    y4 = np.arange(len(c_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in c_sorted]
    ax4.barh(y4, vals4, color=["#2b8cbe" if r["role"] == "SCIENCE" else "#718096" for r in c_sorted], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({float(r['offaxis_deg']):.1f}d)" for r in c_sorted], fontsize=6.2)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 5000.0)
    for yi, (r, v) in enumerate(zip(c_sorted, vals4)):
        fl_e = float(r["flux_lim_erg_cm2_s"])
        ax4.text(v * 1.18, yi, f"{_fmt_power_kw(v)} | F={fl_e:.1e}", va="center", fontsize=5.4, fontweight="bold")
    ax4.set_xlabel("6-sigma Formal 10-m EIRP Limit (kW) & Physical F_lim (erg cm^-2 s^-1)")
    best_c = c_sorted[0]
    ax4.set_title(f"D. All 20 CGRO COMPTEL Bounds ({best_c['star']} {_fmt_power_kw(float(best_c['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D105 (V6.3): NASA CGRO COMPTEL MeV Survey Across 8 Phase-01 Viewing Periods (20 Targets; 0.75-30.0 MeV; 0 ETI)", fontsize=10.4, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig122_d105_cgro_comptel_mev_0p75_30mev.png")


def fig123_fermi_lat_and_he_ladder(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    obs = _read_csv(res_dir, "FERMI_LAT_40TARGETS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V63_FERMI_LAT_240.csv")
    spec_a = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D105.json").read_text())
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Unbroken 300 GeV -> 700 A High-Energy Octave Ladder (~33.979 Octaves)
    bands_he = [
        ("Fermi LAT Pass-8\n(30 MeV-300 GeV; D105)", 4.1328e-5, 0.41328, "#8856a7"),
        ("CGRO COMPTEL EVP\n(0.75-30.0 MeV; D105)", 4.1328e-4, 0.016531, "#e7298a"),
        ("CGRO OSSE RMF\n(50 keV-9.09 MeV; D105)", 0.001364, 0.2480, "#b30000"),
        ("Suzaku HXD-GSO\n(50-600 keV; D104)", 0.02066, 0.2480, "#a63603"),
        ("NuSTAR FPMA+B\n(3-79 keV; D103)", 0.1569, 4.1328, "#1a365d"),
        ("XRISM Resolve OPEN\n(1.7-12 keV; D104)", 1.0332, 7.2932, "#2b8cbe"),
        ("NICER XTI 52-MPU\n(0.35-10 keV; D104)", 1.2398, 35.4241, "#66a61e"),
        ("Chandra HETG/LETG\n+ XMM RGS (D102-D103)", 1.24, 175.0, "#1b9e77"),
        ("EUVE DS/S\n(70-700 A; D102)", 70.0, 699.80, "#7570b3"),
    ]
    ax1.axvspan(699.80, 905.0, color="#fed7d7", alpha=0.75, label="ISM H Photoionization Wall (700-905 A)")
    for yi, (lbl, a_lo, a_hi, col) in enumerate(bands_he):
        ax1.plot([a_lo, a_hi], [yi, yi], color=col, lw=7.5, solid_capstyle="butt")
        ax1.plot([a_lo, a_hi], [yi, yi], "o", color="black", ms=3.0)
    ax1.set_yticks(np.arange(len(bands_he)))
    ax1.set_yticklabels([b[0] for b in bands_he], fontsize=6.1)
    ax1.set_xscale("log")
    ax1.set_xlim(2.0e-5, 1600.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Wavelength (Angstrom, log scale; 300 GeV = 4.1328e-5 A)")
    ax1.set_title(f"A. Unbroken GeV-to-EUV Ladder ({spec_a['high_energy_unbroken_octaves']:.3f} Octaves)")
    ax1.legend(loc="lower left", fontsize=6.6, frameon=True)
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Archival Fermi LAT Split Spectrum
    f_exps = [e for e in bundle["exposures"] if e["instrument"] == "FERMI_LAT"]
    pref = next((e for e in f_exps if e["star"] == "3C279"), None) or next((e for e in f_exps if e["role"] == "SCIENCE"), f_exps[0])
    ek = az._decode_arr_any(pref["e_kev_c"]) / 1000.0
    ca = az._decode_arr_any(pref["cnt_a_c"])
    cb = az._decode_arr_any(pref["cnt_b_c"])
    bg = az._decode_arr_any(pref["off_spat_c"]) * az._decode_arr_any(pref["alpha_spat_c"])
    ax2.step(ek, ca, where="mid", color="#1b9e77", lw=1.0, alpha=0.88, label="Odd Weeks w011,w013,w015,w017 (A)")
    ax2.step(ek, cb, where="mid", color="#d95f02", lw=0.9, alpha=0.82, label="Even Weeks w010,w012,w014,w016 (B)")
    ax2.step(ek, bg, where="mid", color="#636363", lw=0.9, ls="--", alpha=0.85, label="Annulus Background alpha*Off")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(30.0, 3.0e5)
    ax2.set_xlabel("Photon Energy (MeV, 30 MeV - 300 GeV)")
    ax2.set_ylabel("Pass-8 Front+Back Event Counts (symlog)")
    ax2.set_title(f"B. Archival Fermi LAT Weekly Split Spectrum ({pref['star']}, GTI={float(pref['gti_s'])/1e6:.2f} Ms)")
    ax2.legend(loc="upper right", fontsize=6.3, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: CALIBRATION_V63_FERMI_LAT_240
    _cal_bars(
        ax3, cal,
        f"C. Fermi LAT Pass-8 Dual-Week Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_FERMI_LAT_BEACON": "Clean\nLAT A+B",
            "CONVERTER_OR_DIFFUSE_VETO": "Week Split /\nDiffuse Veto",
            "LAT_PION_EARTHLIMB_VETO": "pi0 / 511 keV\nEarth-Limb",
            "LAT_POWERLAW_NULL": "Power-Law\nContinuum",
            "BROAD_OR_1BIN_VETO": "Broad / 1-Bin\nVeto",
        },
    )

    # Panel D: Top 16 Fermi LAT 10-m EIRP & Physical Flux Bounds
    f_sorted = sorted(obs, key=lambda r: float(r["p_beam_10m_kw"]))[:16]
    y4 = np.arange(len(f_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in f_sorted]
    ax4.barh(y4, vals4, color=["#1b9e77" if r["role"] == "SCIENCE" else "#718096" for r in f_sorted], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({float(r['dist_pc']):.1f}pc)" for r in f_sorted], fontsize=6.4)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 5000.0)
    for yi, (r, v) in enumerate(zip(f_sorted, vals4)):
        fl_e = float(r["flux_lim_erg_cm2_s"])
        ax4.text(v * 1.18, yi, f"{_fmt_power_kw(v)} | F={fl_e:.1e}", va="center", fontsize=5.6, fontweight="bold")
    ax4.set_xlabel("6-sigma Formal 10-m EIRP Limit (kW) & Physical F_lim (erg cm^-2 s^-1)")
    best_f = f_sorted[0]
    ax4.set_title(f"D. Best 16 Fermi LAT Bounds ({best_f['star']} {_fmt_power_kw(float(best_f['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D105 (V6.3): NASA Fermi LAT Pass-8 P305 Survey (40 Targets; 30 MeV - 300 GeV) & {spec_a['high_energy_unbroken_octaves']:.3f} Unbroken High-Energy Octaves (0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig123_d105_fermi_lat_gev_33p98_he_octave_ladder.png")


def fig124_solar_neighborhood_230(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    s230 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_230STARS.csv")
    eirp105 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D105.csv")
    fg = _read_csv(res_dir, "FOUR_GEN_BENCHMARK_D105.csv")
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Histogram across all 230 <10 pc stars
    lims = [float(r["min_panchromatic_10m_kw"]) for r in s230 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med_v = float(np.median(lims))
    opt_med = float(syn["within_10pc_optical_ir_median_limit_kw"])
    ax1.hist(np.log10(lims), bins=28, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax1.axvline(math.log10(med_v), color="#b30000", ls="--", lw=1.6, label=f"Global Median: {_fmt_power_kw(med_v)} ({len(s230)} stars)")
    ax1.axvline(math.log10(opt_med), color="#1a365d", ls=":", lw=1.6, label=f"Optical/IR Median: {opt_med:.4f} kW")
    ax1.set_xlabel("log10(Minimum Panchromatic Formal 10-m EIRP Limit / kW)")
    ax1.set_ylabel("Target Count")
    ax1.set_title(f"A. 230-Star Solar Neighborhood Census (<10 pc; Best {_fmt_power_kw(min(lims))})")
    ax1.legend(loc="upper left", fontsize=6.7, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: Distance vs Best Limit (0-10 pc)
    d_old, l_old, d_new, l_new = [], [], [], []
    for r in s230:
        if not r.get("min_panchromatic_10m_kw") or float(r["min_panchromatic_10m_kw"]) <= 0:
            continue
        dp = float(r["dist_pc"])
        pk = float(r["min_panchromatic_10m_kw"])
        if str(r["phases"]).split("+") == ["D105"]:
            d_new.append(dp); l_new.append(pk)
        else:
            d_old.append(dp); l_old.append(pk)
    ax2.scatter(d_old, l_old, s=20, color="#718096", alpha=0.70, edgecolor="black", lw=0.35, label=f"D079-D104 Targets ({len(d_old)})")
    ax2.scatter(d_new, l_new, s=44, color="#b30000", marker="^", edgecolor="black", lw=0.5, zorder=4, label=f"D105 Brand-New <10 pc (+{len(d_new)})")
    ax2.set_yscale("log")
    ax2.set_xlim(1.0, 10.2)
    ax2.set_xlabel("Heliocentric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title(f"B. Distance vs Sensitivity Within 10 pc (+{len(d_new)} Brand-New in D105)")
    ax2.legend(loc="lower right", fontsize=6.7, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Archival CARMENES_VIS / ESO_FEROS <10 pc Spectrum
    opt_exps = [e for e in bundle["exposures"] if e["instrument"] in ("CARMENES_VIS", "ESO_FEROS", "ESO_HARPS") and not e["is_prior_bridge"]]
    pref = next((e for e in opt_exps if e["star"] == "J07403-174"), opt_exps[0])
    wb = float(pref["w0"]) + float(pref["dw"]) * np.arange(int(pref["npts"]), dtype=np.float64)
    fl = az._decode_arr_any(pref["flux_c"])
    step_ds = max(1, len(wb) // 6000)
    ax3.plot(wb[::step_ds], fl[::step_ds], color="#2b8cbe", lw=0.55, alpha=0.88, label=f"{pref['instrument']} (d={float(pref['dist_pc']):.2f} pc)")
    ax3.axvline(6564.61, color="#b30000", ls=":", lw=0.9, label="H-alpha (6564.6 A)")
    ax3.set_xlim(float(wb[0]), float(wb[-1]))
    ax3.set_xlabel("Barycentric Wavelength (Angstrom)")
    ax3.set_ylabel("Relative Flux")
    ax3.set_title(f"C. Archival <10 pc Echelle Spectrum ({pref['star']})")
    ax3.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Best 16 D105 Optical <10 pc & Orbit Host Limits + 4-Gen Summary
    opt_best: dict[str, tuple[float, float, str]] = {}
    for r in eirp105:
        if r["instrument"] in ("CARMENES_VIS", "ESO_ESPRESSO", "ESO_FEROS", "ESO_HARPS"):
            st = r["star"]
            pk = float(r["p_beam_10m_kw"])
            if st not in opt_best or pk < opt_best[st][0]:
                opt_best[st] = (pk, float(r["dist_pc"]), r["instrument"])
    opt_sorted = sorted(opt_best.items(), key=lambda kv: kv[1][0])[:16]
    y4 = np.arange(len(opt_sorted))
    vals4 = [kv[1][0] for kv in opt_sorted]
    ax4.barh(y4, vals4, color="#2b8cbe", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{st} ({v[1]:.2f}pc, {v[2].replace('ESO_', '')[:4]})" for st, v in opt_sorted], fontsize=6.0)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.45, max(vals4) * 80.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.15, yi, _fmt_power_kw(v), va="center", fontsize=6.1, fontweight="bold")
    fg_txt = "\n".join(f"{r['instrument']}: G1={r['g1_seeds']}->G8={r['g8_pass']}->ETI=0" for r in fg)
    ax4.text(0.98, 0.96, fg_txt, transform=ax4.transAxes, ha="right", va="top", fontsize=5.8, bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7fafc", edgecolor="#4a5568", lw=0.7))
    ax4.set_xlabel("6-sigma 10-m Optical Beam EIRP Limit (kW)")
    ax4.set_title("D. Best 16 D105 Optical Limits & 4-Gen Optical Funnel")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D105 (V6.3): Solar Neighborhood Census Reaches {len(s230)} Stars Within 10 pc (Global Med. {_fmt_power_kw(med_v)}; Optical Med. {opt_med:.4f} kW; 0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig124_d105_solar_neighborhood_230stars_10pc.png")


def fig125_drift_and_comb_72campaigns(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6_D105.csv")
    ek72 = _read_csv(res_dir, "DRIFT_V63_ECCENTRIC_KEPLERIAN_72CAMPAIGNS.csv")
    cd72 = _read_csv(res_dir, "COMB_DRIFT_V63_72CAMPAIGNS.csv")
    cal_dc = _read_csv(res_dir, "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Coherent Drifting-Comb Calibration
    cls_map: dict[str, list[int]] = {}
    for r in cal_dc:
        c = r["class"]
        cls_map.setdefault(c, [0, 0])
        cls_map[c][0] += int(r["passed"])
        cls_map[c][1] += 1
    lbls_a = ["V6.3 Kepler\nComb (60)", "V6.3 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
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

    # Panel B: Live Orbital Campaigns #175-#180
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
    pad_y = max(1.0, 0.24 * (ymax_v - ymin_v))
    ax2.set_ylim(ymin_v - 0.55 * pad_y, ymax_v + 1.85 * pad_y)
    ax2.set_xlabel("Orbital Phase phi")
    ax2.set_ylabel("Planetary Keplerian RV (m/s)")
    ax2.set_title("B. ESO ESPRESSO + HARPS Orbits #175-#180 (Multi-Epoch Kinematics)")
    ax2.legend(loc="upper right", fontsize=6.3, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: All 72 Cumulative DRIFT_V63 Campaigns
    x72 = np.arange(len(ek72))
    ax3.bar(x72, [int(r["n_trajectories_evaluated"]) for r in ek72], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x72, [int(r["raw_coherent_survivors"]) for r in ek72], color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Raw Survivors ({sum_raw['drift_v63_72campaigns_raw_survivors']:,})")
    ax3.bar(x72, [int(r["stage2_verified_eti"]) for r in ek72], color="#1b9e77", label="Verified ETI (0/72)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek72) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D105, 7-12 D104, ..., 67-72 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    ax3.set_title(f"C. 72-Campaign DRIFT_V63 ({sum_raw['drift_v63_72campaigns_trajectories']:,} Traj / {sum_raw['drift_v63_72campaigns_pixel_integrals']/1e9:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 72 Cumulative COMB_DRIFT_V63 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd72])
    qual_cd = np.asarray([int(r["comb_qualified_v63"]) for r in cd72])
    ax4.plot(x72, raw_cd, "-o", ms=2.7, color="#d95f02", lw=1.05, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v63_72campaigns_raw_candidates']:,})")
    ax4.plot(x72, qual_cd, "-s", ms=2.7, color="#7570b3", lw=1.05, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v63_72campaigns_qualified_pre_stage2']})")
    ax4.plot(x72, np.zeros_like(x72), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/72)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#72 Across D094-D105)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 72-Campaign COMB_DRIFT_V63 ({sum_raw['comb_drift_v63_72campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax4.grid(True, alpha=0.22)

    pix_b = sum_raw["drift_v63_72campaigns_pixel_integrals"] / 1e9
    fig.suptitle(f"Phase D105 (V6.3): Orbits #175-#180 & 72-Campaign Coherent DRIFT_V63 + COMB_DRIFT_V63 ({pix_b:.2f}B Pixel Integrals; 0 ETI)", fontsize=10.4, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig125_d105_drift_v63_and_comb_72campaigns.png")


def fig126_global_synthesis_806(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp105 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D105.csv")
    ell = _read_csv(res_dir, f"MULTIEVENT_ELLIPSOID_{syn['unique_stars_total']}STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 50.878-Octave Sensitivity Frontier
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Wall (700-905 A)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D105" and r.get("wave_um") and r.get("p_beam_10m_kw") and float(r["p_beam_10m_kw"]) > 0]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=8, color="#bdbdbd", alpha=0.48, zorder=1, label="D079-D104 (0.00000207-8,556.4 um)")

    inst_groups = [
        ("FERMI_LAT", "#8856a7", "*", "D105 Fermi LAT (30 MeV-300 GeV)"),
        ("CGRO_COMPTEL", "#e7298a", "P", "D105 CGRO COMPTEL (0.75-30 MeV)"),
        ("CGRO_OSSE", "#b30000", "^", "D105 CGRO OSSE (50 keV-9.09 MeV)"),
        ("CARMENES_VIS", "#2b8cbe", "o", "D105 CARMENES VIS (<10 pc)"),
        ("ESO_ESPRESSO", "#d95f02", "s", "D105 ESPRESSO Orbits"),
        ("ESO_FEROS", "#1b9e77", "v", "D105 FEROS (<10 pc)"),
        ("ESO_HARPS", "#66a61e", "D", "D105 HARPS (<10 pc & Orbits)"),
    ]
    for ik, col, mk, lbl in inst_groups:
        sub = [r for r in eirp105 if r["instrument"] == ik]
        if sub:
            ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=24 if mk != "*" else 52, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0e-12, 30000.0)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma Formal 10-m EIRP Limit (kW)")
    ax1.set_title(f"A. Unified {syn['spectrographs']}-Spectrograph Sensitivity Frontier ({syn['total_octave_span']} Octaves)")
    ax1.legend(loc="lower right", fontsize=5.2, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-806 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V6_2_PHASES_SNAPSHOT.json").read_text())["prior_unified_755_rows"]}
    all105_st = {e["star"] for e in bundle["exposures"]}
    brand_n = all105_st - prior_st
    bridges_n = all105_st & prior_st
    ra_p, dec_p, ra_b, dec_b, ra_n, dec_n = [], [], [], [], [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand_n:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in bridges_n:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D104 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D105 Bridges ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=44, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D105 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.8, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: All 21 D105 Calibration Suites
    cal_sum = s_json["synthetic_calibration_4491_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V63_", "V6.3 ")
        .replace("CALIBRATION_V62_", "V6.2 ")
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
    ax3.barh(y3, s_pcts, color=["#8856a7" if "V6.3" in s else "#2b8cbe" for s in short_s], edgecolor="black", lw=0.45)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(short_s, fontsize=5.1)
    ax3.set_xlim(92.0, 102.0)
    ax3.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax3.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=5.0, color="white", fontweight="bold")
    ax3.set_xlabel("Suite Pass Rate (%)")
    ax3.set_title(f"C. D105 21-Suite Calibration ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d105']:,})")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: Cross-Band Bridge Matrix Heatmap (GeV LAT -> mm, 12 Regimes)
    regs = [
        ("GeV\nLAT", 1e-12, 4e-8),
        ("MeV\nCMP/OSS", 4e-8, 2.5e-5),
        ("Hard X\nNuST", 1.5e-5, 4.5e-4),
        ("Soft X\nXR/NI/CX", 4.5e-4, 0.0176),
        ("EUV\nEUVE", 0.007, 0.072),
        ("UV\nHST/IUE", 0.090, 0.32),
        ("Opt\n0.3-1", 0.32, 1.0),
        ("NIR\n1-5", 1.0, 5.0),
        ("MIR\n5-30", 5.0, 30.0),
        ("FIR\n30-310", 30.0, 310.0),
        ("Submm\nB7-10", 310.0, 1100.0),
        ("mm\nB1-6", 1100.0, 9000.0),
    ]
    by_star: dict[str, list[tuple[float, float]]] = {}
    for br in b_rows:
        st = br["star"]
        if not br.get("wave_um") or not br.get("p_beam_10m_kw") or float(br["p_beam_10m_kw"]) <= 0:
            continue
        by_star.setdefault(st, []).append((float(br["wave_um"]), float(br["p_beam_10m_kw"])))

    def _reg_score(st: str) -> int:
        pts = by_star.get(st, [])
        return sum(1 for _, w0, w1 in regs if any(w0 <= w <= w1 for w, _ in pts))

    priority_stars = [
        "EVLAC", "AUMIC", "PROXIMACEN", "ADLEO", "ABDOR", "SIGMAGEM", "BETELGEUSE",
        "CYGX1", "CRAB", "VELAPSR", "SIRIUSA", "EPSERI", "VEGA", "FOMALHAUT",
        "NGC1068", "CENA", "3C273", "3C279", "MRK421", "ETACAR",
    ]
    focus = [s for s in priority_stars if _reg_score(s) >= 2]
    for s in sorted(by_star, key=_reg_score, reverse=True):
        if s not in focus and len(focus) < 16:
            focus.append(s)
    focus = focus[:16]

    mat = np.full((len(focus), len(regs)), np.nan, dtype=np.float64)
    for r_i, st in enumerate(focus):
        for c_i, (_, w0, w1) in enumerate(regs):
            vals = [math.log10(max(1e-25, pk)) for w, pk in by_star.get(st, []) if w0 <= w <= w1]
            if vals:
                mat[r_i, c_i] = min(vals)

    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad("#edf2f7")
    im = ax4.imshow(mat, aspect="auto", cmap=cmap, vmin=-19.0, vmax=6.0)
    ax4.set_xticks(np.arange(len(regs)))
    ax4.set_xticklabels([r[0] for r in regs], fontsize=5.3)
    ax4.set_yticks(np.arange(len(focus)))
    ax4.set_yticklabels(focus, fontsize=6.4)
    for ri in range(len(focus)):
        for ci in range(len(regs)):
            v = mat[ri, ci]
            if math.isfinite(v):
                ax4.text(ci, ri, f"{v:+.1f}", ha="center", va="center", fontsize=4.7, color="white" if v >= 0.5 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax4, fraction=0.042, pad=0.02)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.0)
    ax4.set_title(f"D. Bridge Matrix ({syn['panchromatic_bridge_stars_total']} Sci / {syn['multi_phase_targets_total']} Multi-Phase; {syn['panchromatic_bridge_cells_total']} Cells)")

    fig.suptitle(f"Phase D105 (V6.3): {syn['unique_stars_total']} Targets Across {syn['total_octave_span']} Octaves ({syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms; {syn['within_10pc_unique_stars']} <10 pc; 0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig126_d105_global_50p88_octave_806star_107bridge_synthesis.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    az = _load_mod(ws / "analyze.py", "analyze_v63")
    det = _load_mod(ws / "v6_3_detector.py", "v6_3_detector")
    with gzip.open(ws / "bounded_inputs/d105_bounded_bundle.json.gz", "rb") as gz:
        bundle = json.loads(gz.read().decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig121_cgro_osse(res_dir, bundle, az, fig_dir)
    fig122_cgro_comptel(res_dir, bundle, az, fig_dir)
    fig123_fermi_lat_and_he_ladder(res_dir, bundle, az, fig_dir)
    fig124_solar_neighborhood_230(res_dir, bundle, az, fig_dir)
    fig125_drift_and_comb_72campaigns(res_dir, orb_json, det, fig_dir)
    fig126_global_synthesis_806(res_dir, ws, bundle, fig_dir)
    print(f"Rendered 6 D105 figures -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
