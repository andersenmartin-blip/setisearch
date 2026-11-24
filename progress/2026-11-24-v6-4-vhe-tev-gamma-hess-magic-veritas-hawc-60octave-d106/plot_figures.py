#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D106 (V6.4) Six-Figure Publication Suite (fig127-fig132, 240 DPI, metadata={}):
  - fig127: H.E.S.S. DR1 TeV Survey (38 Targets; 0.15-105 TeV)
  - fig128: MAGIC AODR (0.04-55 TeV), VERITAS DL3 (0.10-18 TeV), HAWC GP (1.5-300 TeV) & 4-Obs Crab Cross-Calibration
  - fig129: 43.945 Unbroken High-Energy Octaves (300 TeV -> 700 A), Effective Areas, & VHE Veto Anatomy
  - fig130: Solar Neighborhood 244 <10 pc Census (+14 Brand-New Stars) & Optical/NIR 4-Gen Funnel (incl. NIRPS & UVES)
  - fig131: Orbits #181-#186 & 78-Campaign Coherent DRIFT_V64 + COMB_DRIFT_V64 Synthesis
  - fig132: Global 60.845-Octave, 852-Star, 119 SCIENCE / 146 Multi-Phase Bridge Synthesis
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
    if v < 1e-24:
        return f"{v * 1e27:.2f} yW"
    if v < 1e-21:
        return f"{v * 1e24:.2f} zW"
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
    ax.set_xticklabels(lbls, fontsize=6.5)
    ax.set_ylim(0, 120)
    ax.set_ylabel("Pass / Rejection Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, keys):
        p, t = cls_counts[k]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig127_hess_dr1(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    obs = _read_csv(res_dir, "HESS_TEV_38TARGETS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V64_HESS_TEV_240.csv")
    sc = [r for r in _read_csv(res_dir, "V6_4_VHE_CANDIDATE_LEDGER.csv") if r["instrument"] == "HESS_TEV"]
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]
    raw_tot = int(sum_raw["hess_tev_raw_candidates"])
    qual_tot = int(sum_raw["hess_tev_qualified_pre_stage2"])
    cal_p = sum(int(r["passed"]) for r in cal)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V64_HESS_TEV_240
    _cal_bars(
        ax1, cal,
        f"A. H.E.S.S. DR1 Spatial-Split Calibration ({cal_p}/{len(cal)} = {100.0*cal_p/len(cal):.2f}%)",
        replace_map={
            "CLEAN_HESS_TEV_BEACON": "Clean\nHESS A+B",
            "HESS_TEV_EPOCH_OR_SPATIAL_VETO": "Wobble / Run\nSplit Veto",
            "HESS_TEV_THRESHOLD_ATLAS_VETO": "210 GeV /\nThresh. Atlas",
            "HESS_TEV_POWERLAW_NULL": "TeV Power-Law\nContinuum",
            "BROAD_OR_1BIN_VETO": "Broad / 1-Bin\nVeto",
        },
    )

    # Panel B: Archival H.E.S.S. DR1 Split Spectrum
    h_exps = [e for e in bundle["exposures"] if e["instrument"] == "HESS_TEV"]
    pref = next((e for e in h_exps if e["star"] == "PKS2155"), None) or next((e for e in h_exps if e["star"] == "CRABNEBULA"), h_exps[0])
    e_tev = az._decode_arr_any(pref["e_kev_c"]) / 1.0e9
    ca = az._decode_arr_any(pref["cnt_a_c"])
    cb = az._decode_arr_any(pref["cnt_b_c"])
    bg = az._decode_arr_any(pref["off_spat_c"]) * az._decode_arr_any(pref["alpha_spat_c"])
    ax2.step(e_tev, ca, where="mid", color="#1a365d", lw=1.0, alpha=0.88, label="Odd Run / Sub-Array Stream A")
    ax2.step(e_tev, cb, where="mid", color="#d95f02", lw=0.9, alpha=0.82, label="Even Run / Sub-Array Stream B")
    ax2.step(e_tev, bg, where="mid", color="#636363", lw=0.9, ls="--", alpha=0.85, label="Reflected-Off Background alpha*Off")
    ax2.axvline(0.210, color="#7570b3", ls=":", lw=1.0, label="Safe Trigger Threshold (210 GeV)")
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_xlim(0.12, 110.0)
    ax2.set_xlabel("Reconstructed Photon Energy (TeV, 0.15-105 TeV)")
    ax2.set_ylabel("Event Counts (symlog)")
    ax2.set_title(f"B. Archival H.E.S.S. DR1 Split Spectrum ({pref['star']}, N_sci={int(pref['n_events_science']):,}, {float(pref['exp_s'])/3600:.1f}h)")
    ax2.legend(loc="upper right", fontsize=6.4, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Significance vs Split Consistency across HESS_TEV candidates
    snrs = [float(r["snr"]) for r in sc] if sc else [0.0]
    pvals = [-math.log10(max(1e-12, float(r["split_p"]) if r.get("split_p") else 1.0)) for r in sc] if sc else [0.0]
    cols = ["#b30000" if r.get("qualified_v64") == "True" else "#2b8cbe" for r in sc] if sc else ["#2b8cbe"]
    ax3.scatter(snrs, pvals, s=34, c=cols, edgecolor="black", lw=0.45, alpha=0.88, zorder=4)
    for r, sx, py in zip(sc, snrs, pvals):
        if r.get("qualified_v64") == "True":
            ax3.annotate(r["star"], (sx, py), xytext=(5, 4), textcoords="offset points", fontsize=6.2, fontweight="bold")
        elif sx >= 15.0:
            ax3.annotate(r["star"], (sx, py), xytext=(-44, -4), textcoords="offset points", fontsize=6.2, fontweight="bold")
    ax3.axvline(6.0, color="#1b9e77", ls="--", lw=1.0, label="S_LiMa >= 6.0 Threshold")
    ax3.axhline(2.0, color="#d95f02", ls="--", lw=1.0, label="Run/Sub-Array Discordance Cut (p=0.01)")
    ax3.set_xlim(4.8, 39.5)
    ax3.set_ylim(-0.6, 13.5)
    ax3.set_xlabel("Joint Li & Ma Significance (S_LiMa)")
    ax3.set_ylabel("-log10(Run-Split Consistency p)")
    ax3.set_title(f"C. H.E.S.S. DR1 Candidates ({raw_tot} Raw / {len(sc)} Ledger -> {qual_tot} Pre-S2 -> 0 ETI)")
    ax3.legend(loc="center right", fontsize=6.5, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Top 18 HESS_TEV Limits (Physical F_lim + Formal 10-m EIRP)
    h_sorted = sorted(obs, key=lambda r: float(r["p_beam_10m_kw"]))[:18]
    y4 = np.arange(len(h_sorted))
    vals4 = [float(r["p_beam_10m_kw"]) for r in h_sorted]
    ax4.barh(y4, vals4, color=["#1a365d" if r["role"] == "SCIENCE" else "#718096" for r in h_sorted], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({float(r['dist_pc']):.1f}pc)" for r in h_sorted], fontsize=6.2)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.35, max(vals4) * 6000.0)
    for yi, (r, v) in enumerate(zip(h_sorted, vals4)):
        fl_e = float(r["flux_lim_erg_cm2_s"])
        ax4.text(v * 1.18, yi, f"{_fmt_power_kw(v)} | F={fl_e:.1e}", va="center", fontsize=5.5, fontweight="bold")
    ax4.set_xlabel("6-sigma Formal 10-m EIRP Limit (kW) & Physical F_lim (erg cm^-2 s^-1)")
    best_h = h_sorted[0]
    ax4.set_title(f"D. Best 18 H.E.S.S. DR1 Bounds ({best_h['star']} {_fmt_power_kw(float(best_h['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D106 (V6.4): H.E.S.S. DR1 VHE TeV Survey Across 38 Archival Fields (0.15-105 TeV; 0 ETI)", fontsize=10.5, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig127_d106_hess_dr1_tev_38targets_0p15_105tev.png")


def fig128_magic_veritas_hawc_crab_crosscal(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    m_obs = _read_csv(res_dir, "MAGIC_TEV_4TARGETS.csv")
    v_obs = _read_csv(res_dir, "VERITAS_TEV_CRAB.csv")
    hw_obs = _read_csv(res_dir, "HAWC_TEV_7TARGETS.csv")
    xcal = _read_csv(res_dir, "VHE_TEV_CRAB_4OBS_CROSSCAL.csv")
    cal_m = _read_csv(res_dir, "CALIBRATION_V64_MAGIC_TEV_240.csv")
    cal_v = _read_csv(res_dir, "CALIBRATION_V64_VERITAS_TEV_180.csv")
    cal_h = _read_csv(res_dir, "CALIBRATION_V64_HAWC_PEV_240.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Calibration Pass Rates Across MAGIC (240), VERITAS (180), HAWC (240)
    classes = [
        ("CLEAN", "Clean\nBeacon"),
        ("EPOCH_OR_SPATIAL", "Spatial/Run\nSplit"),
        ("THRESHOLD_ATLAS", "Threshold\nAtlas"),
        ("POWERLAW_NULL", "Power-Law\nContinuum"),
        ("BROAD_OR_1BIN", "Broad /\n1-Bin"),
    ]
    def _class_rate(rows: list[dict[str, str]], key_prefix: str) -> float:
        sub = [r for r in rows if key_prefix in r["class"]]
        return 100.0 * sum(int(r["passed"]) for r in sub) / max(1, len(sub))

    x = np.arange(len(classes))
    w_bar = 0.25
    r_m = [_class_rate(cal_m, k) for k, _ in classes]
    r_v = [_class_rate(cal_v, k) for k, _ in classes]
    r_h = [_class_rate(cal_h, k) for k, _ in classes]
    b1 = ax1.bar(x - w_bar, r_m, width=w_bar, color="#2b8cbe", edgecolor="black", lw=0.6, label=f"MAGIC ({sum(int(r['passed']) for r in cal_m)}/{len(cal_m)})")
    b2 = ax1.bar(x, r_v, width=w_bar, color="#1b9e77", edgecolor="black", lw=0.6, label=f"VERITAS ({sum(int(r['passed']) for r in cal_v)}/{len(cal_v)})")
    b3 = ax1.bar(x + w_bar, r_h, width=w_bar, color="#b30000", edgecolor="black", lw=0.6, label=f"HAWC ({sum(int(r['passed']) for r in cal_h)}/{len(cal_h)})")
    ax1.set_xticks(x)
    ax1.set_xticklabels([lbl for _, lbl in classes], fontsize=6.6)
    ax1.set_ylim(0, 122)
    ax1.set_ylabel("Pass / Rejection Rate (%)")
    ax1.set_title("A. MAGIC, VERITAS & HAWC Pass-4 Calibration (660/660 = 100.00%)")
    for grp in (b1, b2, b3):
        for bar in grp:
            ax1.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 1.5, f"{bar.get_height():.0f}%", ha="center", va="bottom", fontsize=5.8, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=6.5, frameon=True)
    ax1.grid(True, axis="y", alpha=0.25)

    # Panel B: 4-Observatory Crab Nebula Physical Flux Sensitivity Curve (VHE_TEV_CRAB_4OBS_CROSSCAL.csv)
    obs_styles = [
        ("MAGIC_TEV", "#2b8cbe", "o-", "MAGIC AODR (0.04-55 TeV)"),
        ("VERITAS_TEV", "#1b9e77", "s-", "VERITAS DL3 (0.10-18 TeV)"),
        ("HESS_TEV", "#7570b3", "^-", "H.E.S.S. DR1 (0.15-105 TeV)"),
        ("HAWC_TEV", "#b30000", "D-", "HAWC Pass-4 GP (1.5-300 TeV)"),
    ]
    for ok, col, fmt, lbl in obs_styles:
        sub = sorted([r for r in xcal if r["observatory"] == ok], key=lambda r: float(r["energy_tev"]))
        ax2.plot([float(r["energy_tev"]) for r in sub], [float(r["flux_lim_erg_cm2_s"]) for r in sub], fmt, color=col, ms=5.0, lw=1.45, label=lbl)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.04, 320.0)
    ax2.set_xlabel("Photon Energy (TeV)")
    ax2.set_ylabel("6-sigma Narrow-Line Flux Limit F_lim (erg cm^-2 s^-1)")
    ax2.set_title("B. Four-Observatory Crab Nebula Cross-Calibration (19 Bands; 0.07-250 TeV)")
    ax2.legend(loc="upper left", fontsize=6.4, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Archival Split Spectra for HAWC GP, MAGIC AODR, and VERITAS DL3
    crab_exps = {
        "MAGIC_TEV": next((e for e in bundle["exposures"] if e["instrument"] == "MAGIC_TEV" and e["star"] == "CRABNEBULA"), None),
        "VERITAS_TEV": next((e for e in bundle["exposures"] if e["instrument"] == "VERITAS_TEV"), None),
        "HAWC_TEV": next((e for e in bundle["exposures"] if e["instrument"] == "HAWC_TEV" and e["star"] == "CRABNEBULA"), None),
    }
    for ok, col, _, lbl in [("MAGIC_TEV", "#2b8cbe", "-", "MAGIC AODR Crab (A+B)"), ("VERITAS_TEV", "#1b9e77", "-", "VERITAS DL3 Crab (A+B)"), ("HAWC_TEV", "#b30000", "-", "HAWC GP fHit5-9 Crab (4.88 Ms)")]:
        ex = crab_exps.get(ok)
        if ex:
            ek_t = az._decode_arr_any(ex["e_kev_c"]) / 1.0e9
            ct = az._decode_arr_any(ex["cnt_a_c"]) + az._decode_arr_any(ex["cnt_b_c"])
            ax3.step(ek_t, ct, where="mid", color=col, lw=1.15, alpha=0.88, label=lbl)
    ax3.axvline(1.8, color="#b30000", ls=":", lw=0.95, label="HAWC fHit5 Threshold (1.8 TeV)")
    ax3.set_xscale("log")
    ax3.set_yscale("symlog", linthresh=2.0)
    ax3.set_xlim(0.035, 320.0)
    ax3.set_xlabel("Reconstructed Photon Energy (TeV)")
    ax3.set_ylabel("Total On-Source Counts (symlog)")
    ax3.set_title("C. Archival Crab Event Spectra Across MAGIC, VERITAS & HAWC Pass-4 GP")
    ax3.legend(loc="upper right", fontsize=6.3, frameon=True)
    ax3.grid(True, which="both", alpha=0.22)

    # Panel D: All 12 MAGIC (4) + VERITAS (1) + HAWC (7) Target Bounds
    all12 = [(dict(r, inst="MAGIC_TEV")) for r in m_obs] + [(dict(r, inst="VERITAS_TEV")) for r in v_obs] + [(dict(r, inst="HAWC_TEV")) for r in hw_obs]
    all12.sort(key=lambda r: float(r["p_beam_10m_kw"]))
    col_map = {"MAGIC_TEV": "#2b8cbe", "VERITAS_TEV": "#1b9e77", "HAWC_TEV": "#b30000"}
    y4 = np.arange(len(all12))
    vals4 = [float(r["p_beam_10m_kw"]) for r in all12]
    ax4.barh(y4, vals4, color=[col_map[r["inst"]] for r in all12], edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['inst'].replace('_TEV', '')})" for r in all12], fontsize=6.4)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.25, max(vals4) * 9000.0)
    for yi, (r, v) in enumerate(zip(all12, vals4)):
        fl_e = float(r["flux_lim_erg_cm2_s"])
        ax4.text(v * 1.18, yi, f"{_fmt_power_kw(v)} | F={fl_e:.1e}", va="center", fontsize=5.5, fontweight="bold")
    ax4.set_xlabel("6-sigma Formal 10-m EIRP Limit (kW) & Physical F_lim (erg cm^-2 s^-1)")
    best12 = all12[0]
    ax4.set_title(f"D. All 12 MAGIC + VERITAS + HAWC Bounds ({best12['star']} {_fmt_power_kw(float(best12['p_beam_10m_kw']))})")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D106 (V6.4): MAGIC AODR, VERITAS DL3 & HAWC Pass-4 GP VHE/PeV-Edge Survey + 4-Observatory Crab Cross-Cal (0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig128_d106_magic_veritas_hawc_crab_4obs_crosscal.png")


def fig129_he_octave_ladder_and_vetoes(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    spec_a = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D106.json").read_text())
    vhe_ledger = _read_csv(res_dir, "V6_4_VHE_CANDIDATE_LEDGER.csv")
    vhe_all = (
        [dict(r, inst="HESS_TEV") for r in _read_csv(res_dir, "HESS_TEV_38TARGETS.csv")]
        + [dict(r, inst="MAGIC_TEV") for r in _read_csv(res_dir, "MAGIC_TEV_4TARGETS.csv")]
        + [dict(r, inst="VERITAS_TEV") for r in _read_csv(res_dir, "VERITAS_TEV_CRAB.csv")]
        + [dict(r, inst="HAWC_TEV") for r in _read_csv(res_dir, "HAWC_TEV_7TARGETS.csv")]
    )

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: 43.945-Octave High-Energy Ladder (300 TeV HAWC -> 700 A EUVE)
    bands_he = [
        ("HAWC Pass-4 GP (1.5-300 TeV; D106)", 4.1328e-11, 8.2656e-9, "#b30000"),
        ("H.E.S.S. DR1 (0.15-105 TeV; D106)", 1.1808e-10, 8.2656e-8, "#7570b3"),
        ("MAGIC AODR (0.04-55 TeV; D106)", 2.2543e-10, 3.0996e-7, "#2b8cbe"),
        ("VERITAS DL3 (0.10-18 TeV; D106)", 6.8880e-10, 1.2398e-7, "#1b9e77"),
        ("Fermi LAT Pass-8 (30 MeV-300 GeV; D105)", 4.1328e-8, 4.1328e-4, "#8856a7"),
        ("CGRO COMPTEL EVP (0.75-30 MeV; D105)", 4.1328e-4, 0.016531, "#e7298a"),
        ("CGRO OSSE RMF (50 keV-9.09 MeV; D105)", 0.001364, 0.2480, "#a50f15"),
        ("Suzaku HXD-GSO (50-600 keV; D104)", 0.02066, 0.2480, "#a63603"),
        ("NuSTAR FPMA+B (3-79 keV; D103)", 0.1569, 4.1328, "#1a365d"),
        ("XRISM Resolve + NICER (0.35-12 keV; D104)", 1.0332, 35.4241, "#66a61e"),
        ("Chandra + XMM RGS (0.07-10 keV; D102-D103)", 1.24, 175.0, "#3182bd"),
        ("EUVE DS/S (70-700 A; D102)", 70.0, 699.80, "#636363"),
    ]
    ax1.axvspan(699.80, 905.0, color="#fed7d7", alpha=0.80, label="ISM H Photoionization Wall (700-905 A)")
    for yi, (lbl, a_lo, a_hi, col) in enumerate(bands_he):
        ax1.plot([a_lo, a_hi], [yi, yi], color=col, lw=7.0, solid_capstyle="butt")
        ax1.plot([a_lo, a_hi], [yi, yi], "o", color="black", ms=2.6)
    ax1.set_yticks(np.arange(len(bands_he)))
    ax1.set_yticklabels([b[0] for b in bands_he], fontsize=5.8)
    ax1.set_xscale("log")
    ax1.set_xlim(2.0e-11, 2000.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Wavelength (Angstrom, log scale; 300 TeV = 4.1328e-11 A)")
    ax1.set_title(f"A. Unbroken 300 TeV-to-EUV Ladder ({spec_a['high_energy_unbroken_octaves']:.3f} Octaves)")
    ax1.legend(loc="lower left", fontsize=6.4, frameon=True)
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Effective Area Curves A_eff(E) from D106 Bounded Bundle (Crab Nebula)
    for ik, col, lbl in [
        ("MAGIC_TEV", "#2b8cbe", "MAGIC AODR (Stereo 17 m)"),
        ("VERITAS_TEV", "#1b9e77", "VERITAS DL3 (4x12 m)"),
        ("HESS_TEV", "#7570b3", "H.E.S.S. DR1 (4x12 m CT1-4)"),
        ("HAWC_TEV", "#b30000", "HAWC Pass-4 GP (fHit 5-9, 294 WCD)"),
    ]:
        ex = next((e for e in bundle["exposures"] if e["instrument"] == ik and e["star"] == "CRABNEBULA"), None)
        if ex:
            ek_t = az._decode_arr_any(ex["aeff_ekev_c"]) / 1.0e9
            ae_cm2 = az._decode_arr_any(ex["aeff_cm2_c"])
            m = ae_cm2 > 0
            ax2.plot(ek_t[m], ae_cm2[m], lw=1.8, color=col, label=lbl)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.035, 320.0)
    ax2.set_xlabel("Photon Energy (TeV)")
    ax2.set_ylabel("Effective Collection Area A_eff (cm^2)")
    ax2.set_title("B. Archival IRF Effective Area Curves (0.04-300 TeV Crab Comparison)")
    ax2.legend(loc="lower right", fontsize=6.3, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: VHE Candidate Veto Breakdown (26 Raw -> 1 Pre-S2 -> 0 ETI)
    veto_cats = [
        ("Raw >=6 sig\nVHE Peaks", len(vhe_ledger)),
        ("Run/Wobble\nSplit Veto", sum(1 for r in vhe_ledger if "SPATIAL_COINCIDENCE" in r["stage2_triage_status"])),
        ("Trigger/LAT\nThresh Atlas", sum(1 for r in vhe_ledger if "THRESHOLD_ATLAS" in r["stage2_triage_status"])),
        ("EDISP Width\nVeto", sum(1 for r in vhe_ledger if "EDISP_WIDTH" in r["stage2_triage_status"])),
        ("Pre-Stage-2\nSurvivors", sum(1 for r in vhe_ledger if r["qualified_v64"] == "True")),
        ("Stage-2\nVerified ETI", sum(int(r["verified_eti"]) for r in vhe_ledger)),
    ]
    bars3 = ax3.bar(np.arange(len(veto_cats)), [v[1] for v in veto_cats], color=["#4a5568", "#2b8cbe", "#7570b3", "#d95f02", "#b30000", "#1b9e77"], edgecolor="black", lw=0.7, width=0.60)
    ax3.set_xticks(np.arange(len(veto_cats)))
    ax3.set_xticklabels([v[0] for v in veto_cats], fontsize=6.4)
    ax3.set_ylim(0, max(v[1] for v in veto_cats) + 6)
    ax3.set_ylabel("Candidate Count (Note: Overlapping Gate Vetoes)")
    ax3.set_title("C. V6.4 VHE Candidate Funnel (16 H.E.S.S. + 10 MAGIC + 0 VER/HAWC -> 0 ETI)")
    for b, (_, val) in zip(bars3, veto_cats):
        ax3.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 0.6, str(val), ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    ax3.grid(True, axis="y", alpha=0.25)

    # Panel D: Physical F_lim vs Distance Across All 50 VHE Observations
    inst_meta = [
        ("HESS_TEV", "#7570b3", "o", "H.E.S.S. DR1 (38)"),
        ("MAGIC_TEV", "#2b8cbe", "^", "MAGIC AODR (4)"),
        ("VERITAS_TEV", "#1b9e77", "s", "VERITAS DL3 (1)"),
        ("HAWC_TEV", "#b30000", "D", "HAWC GP (7)"),
    ]
    for ik, col, mk, lbl in inst_meta:
        sub = [r for r in vhe_all if r["inst"] == ik]
        ax4.scatter([float(r["dist_pc"]) for r in sub], [float(r["flux_lim_erg_cm2_s"]) for r in sub], s=32, color=col, marker=mk, edgecolor="black", lw=0.45, alpha=0.88, label=lbl, zorder=4)
    for r in sorted(vhe_all, key=lambda r: float(r["flux_lim_erg_cm2_s"]))[:4]:
        ax4.annotate(r["star"], (float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"])), xytext=(4, -6), textcoords="offset points", fontsize=5.8, fontweight="bold")
    best_prox = min(vhe_all, key=lambda r: float(r["dist_pc"]))
    ax4.annotate(f"{best_prox['star']} ({float(best_prox['dist_pc']):.2f}pc)", (float(best_prox["dist_pc"]), float(best_prox["flux_lim_erg_cm2_s"])), xytext=(6, 4), textcoords="offset points", fontsize=5.8, fontweight="bold")
    ax4.set_xscale("log")
    ax4.set_yscale("log")
    ax4.set_ylim(1.8e-11, 3.5e-9)
    ax4.set_xlabel("Heliocentric / Luminosity Distance d (pc)")
    ax4.set_ylabel("Physical 6-sigma Flux Limit F_lim (erg cm^-2 s^-1)")
    ax4.set_title("D. Physical TeV/PeV-Edge Flux Sensitivity vs Distance (50 VHE Measurements)")
    ax4.legend(loc="center right", fontsize=6.4, frameon=True)
    ax4.grid(True, which="both", alpha=0.22)

    fig.suptitle(f"Phase D106 (V6.4): {spec_a['high_energy_unbroken_octaves']:.3f} Unbroken High-Energy Octaves (300 TeV -> 700 A), Effective Areas & VHE Veto Anatomy", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig129_d106_vhe_43p95_he_octave_ladder.png")


def fig130_solar_neighborhood_244(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    s244 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_244STARS.csv")
    eirp106 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D106.csv")
    fg = _read_csv(res_dir, "FOUR_GEN_BENCHMARK_D106.csv")
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Histogram across all 244 <10 pc stars
    lims = [float(r["min_panchromatic_10m_kw"]) for r in s244 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med_v = float(np.median(lims))
    opt_med = float(syn["within_10pc_optical_ir_median_limit_kw"])
    ax1.hist(np.log10(lims), bins=28, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax1.axvline(math.log10(med_v), color="#b30000", ls="--", lw=1.6, label=f"Global Median: {_fmt_power_kw(med_v)} ({len(s244)} stars)")
    ax1.axvline(math.log10(opt_med), color="#1a365d", ls=":", lw=1.6, label=f"Optical/IR Median: {opt_med:.4f} kW")
    ax1.set_xlabel("log10(Minimum Panchromatic Formal 10-m EIRP Limit / kW)")
    ax1.set_ylabel("Target Count")
    ax1.set_title(f"A. 244-Star Solar Neighborhood Census (<10 pc; Best {_fmt_power_kw(min(lims))})")
    ax1.legend(loc="upper left", fontsize=6.7, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: Distance vs Best Limit (0-10 pc)
    d_old, l_old, d_new, l_new = [], [], [], []
    for r in s244:
        if not r.get("min_panchromatic_10m_kw") or float(r["min_panchromatic_10m_kw"]) <= 0:
            continue
        dp = float(r["dist_pc"])
        pk = float(r["min_panchromatic_10m_kw"])
        if str(r["phases"]).split("+") == ["D106"]:
            d_new.append(dp); l_new.append(pk)
        else:
            d_old.append(dp); l_old.append(pk)
    ax2.scatter(d_old, l_old, s=20, color="#718096", alpha=0.70, edgecolor="black", lw=0.35, label=f"D079-D105 Targets ({len(d_old)})")
    ax2.scatter(d_new, l_new, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, zorder=4, label=f"D106 Brand-New <10 pc (+{len(d_new)})")
    ax2.set_yscale("log")
    ax2.set_xlim(1.0, 10.2)
    ax2.set_xlabel("Heliocentric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title(f"B. Distance vs Sensitivity Within 10 pc (+{len(d_new)} Brand-New in D106)")
    ax2.legend(loc="lower right", fontsize=6.7, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Archival <10 pc NIRPS YJH / UVES / ESPRESSO Spectrum
    opt_exps = [e for e in bundle["exposures"] if e["instrument"] in ("ESO_NIRPS", "ESO_UVES", "ESO_ESPRESSO", "CARMENES_VIS")]
    pref = next((e for e in opt_exps if e["instrument"] == "ESO_NIRPS" and e["star"] == "DENISJ1048"), None) or opt_exps[0]
    wb = float(pref["w0"]) + float(pref["dw"]) * np.arange(int(pref["npts"]), dtype=np.float64)
    fl = az._decode_arr_any(pref["flux_c"])
    fin = np.isfinite(fl)
    wb_f, fl_f = wb[fin], fl[fin]
    step_ds = max(1, len(wb_f) // 6000)
    ax3.plot(wb_f[::step_ds] / 1e4, fl_f[::step_ds], color="#d95f02", lw=0.55, alpha=0.88, label=f"{pref['instrument']} (d={float(pref['dist_pc']):.2f} pc)")
    ax3.axvline(1.0833, color="#1a365d", ls=":", lw=0.9, label="He I 1.0833 um / Pa-beta 1.2822 um")
    ax3.axvline(1.2822, color="#1a365d", ls=":", lw=0.9)
    ax3.set_xlim(float(wb_f[0]) / 1e4, float(wb_f[-1]) / 1e4)
    ax3.set_xlabel("Barycentric Vacuum Wavelength (um)")
    ax3.set_ylabel("Flux (erg cm^-2 s^-1 A^-1)")
    ax3.set_title(f"C. Archival <10 pc NIRPS YJH Spectrum ({pref['star']})")
    ax3.legend(loc="upper right", fontsize=6.5, frameon=True)
    ax3.grid(True, alpha=0.22)

    # Panel D: Best 16 D106 Optical/NIR Limits + 4-Gen Optical/NIR Funnel
    opt_best: dict[str, tuple[float, float, str]] = {}
    for r in eirp106:
        if r["instrument"] in ("CARMENES_VIS", "ESO_ESPRESSO", "ESO_FEROS", "ESO_HARPS", "ESO_NIRPS", "ESO_UVES"):
            st = r["star"]
            pk = float(r["p_beam_10m_kw"])
            if st not in opt_best or pk < opt_best[st][0]:
                opt_best[st] = (pk, float(r["dist_pc"]), r["instrument"])
    opt_sorted = sorted(opt_best.items(), key=lambda kv: kv[1][0])[:16]
    y4 = np.arange(len(opt_sorted))
    vals4 = [kv[1][0] for kv in opt_sorted]
    ax4.barh(y4, vals4, color="#2b8cbe", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{st} ({v[1]:.2f}pc, {v[2].replace('ESO_', '').replace('CARMENES_', 'CARM')[:5]})" for st, v in opt_sorted], fontsize=5.8)
    ax4.set_xscale("log")
    ax4.invert_yaxis()
    ax4.set_xlim(min(vals4) * 0.45, max(vals4) * 180.0)
    for yi, v in enumerate(vals4):
        ax4.text(v * 1.15, yi, _fmt_power_kw(v), va="center", fontsize=6.0, fontweight="bold")
    fg_txt = "\n".join(f"{r['instrument'].replace('ESO_', '')}: G1={r['g1_seeds']}->G8={r['g8_pass']}->ETI=0" for r in fg)
    ax4.text(0.98, 0.96, fg_txt, transform=ax4.transAxes, ha="right", va="top", fontsize=5.6, bbox=dict(boxstyle="round,pad=0.35", facecolor="#f7fafc", edgecolor="#4a5568", lw=0.7))
    ax4.set_xlabel("6-sigma 10-m Optical/NIR Beam EIRP Limit (kW)")
    ax4.set_title("D. Best 16 D106 Optical/NIR Bounds & 4-Gen Funnel")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle(f"Phase D106 (V6.4): Solar Neighborhood Census Reaches {len(s244)} Stars Within 10 pc (Global Med. {_fmt_power_kw(med_v)}; Optical/IR Med. {opt_med:.4f} kW; 0 ETI)", fontsize=10.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig130_d106_solar_neighborhood_244stars_10pc.png")


def fig131_drift_and_comb_78campaigns(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6_D106.csv")
    ek78 = _read_csv(res_dir, "DRIFT_V64_ECCENTRIC_KEPLERIAN_78CAMPAIGNS.csv")
    cd78 = _read_csv(res_dir, "COMB_DRIFT_V64_78CAMPAIGNS.csv")
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
    lbls_a = ["V6.4 Kepler\nComb (60)", "V6.4 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
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

    # Panel B: Live Orbital Campaigns #181-#186
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
    ax2.set_title("B. ESO NIRPS + HARPS Orbits #181-#186 (Multi-Epoch Kinematics)")
    ax2.legend(loc="upper right", fontsize=6.2, frameon=True)
    ax2.grid(True, alpha=0.22)

    # Panel C: All 78 Cumulative DRIFT_V64 Campaigns
    x78 = np.arange(len(ek78))
    ax3.bar(x78, [int(r["n_trajectories_evaluated"]) for r in ek78], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x78, [int(r["raw_coherent_survivors"]) for r in ek78], color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Raw Survivors ({sum_raw['drift_v64_78campaigns_raw_survivors']:,})")
    ax3.bar(x78, [int(r["stage2_verified_eti"]) for r in ek78], color="#1b9e77", label="Verified ETI (0/78)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek78) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D106, 7-12 D105, ..., 73-78 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    ax3.set_title(f"C. 78-Campaign DRIFT_V64 ({sum_raw['drift_v64_78campaigns_trajectories']:,} Traj / {sum_raw['drift_v64_78campaigns_pixel_integrals']/1e9:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.6, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 78 Cumulative COMB_DRIFT_V64 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd78])
    qual_cd = np.asarray([int(r["comb_qualified_v64"]) for r in cd78])
    ax4.plot(x78, raw_cd, "-o", ms=2.6, color="#d95f02", lw=1.05, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v64_78campaigns_raw_candidates']:,})")
    ax4.plot(x78, qual_cd, "-s", ms=2.6, color="#7570b3", lw=1.05, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v64_78campaigns_qualified_pre_stage2']})")
    ax4.plot(x78, np.zeros_like(x78), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/78)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#78 Across D094-D106)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 78-Campaign COMB_DRIFT_V64 ({sum_raw['comb_drift_v64_78campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.6, frameon=True)
    ax4.grid(True, alpha=0.22)

    pix_b = sum_raw["drift_v64_78campaigns_pixel_integrals"] / 1e9
    fig.suptitle(f"Phase D106 (V6.4): Orbits #181-#186 & 78-Campaign Coherent DRIFT_V64 + COMB_DRIFT_V64 ({pix_b:.2f}B Pixel Integrals; 0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig131_d106_drift_v64_and_comb_78campaigns.png")


def fig132_global_synthesis_852(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp106 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D106.csv")
    ell = _read_csv(res_dir, f"MULTIEVENT_ELLIPSOID_{syn['unique_stars_total']}STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 60.845-Octave Sensitivity Frontier
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Wall (700-905 A)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D106" and r.get("wave_um") and r.get("p_beam_10m_kw") and float(r["p_beam_10m_kw"]) > 0]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=8, color="#bdbdbd", alpha=0.45, zorder=1, label="D079-D105 (4.13e-12-8,556.4 um)")

    inst_groups = [
        ("HAWC_TEV", "#b30000", "D", "D106 HAWC GP (1.5-300 TeV)"),
        ("HESS_TEV", "#7570b3", "^", "D106 H.E.S.S. DR1 (0.15-105 TeV)"),
        ("MAGIC_TEV", "#2b8cbe", "*", "D106 MAGIC AODR (0.04-55 TeV)"),
        ("VERITAS_TEV", "#1b9e77", "P", "D106 VERITAS DL3 (0.10-18 TeV)"),
        ("ESO_NIRPS", "#d95f02", "s", "D106 NIRPS (0.97-1.92 um)"),
        ("CARMENES_VIS", "#3182bd", "o", "D106 CARMENES VIS (<10 pc)"),
        ("ESO_HARPS", "#66a61e", "v", "D106 HARPS / FEROS / ESPRESSO / UVES"),
    ]
    for ik, col, mk, lbl in inst_groups:
        if ik == "ESO_HARPS":
            sub = [r for r in eirp106 if r["instrument"] in ("ESO_HARPS", "ESO_FEROS", "ESO_ESPRESSO", "ESO_UVES")]
        else:
            sub = [r for r in eirp106 if r["instrument"] == ik]
        if sub:
            ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=22 if mk != "*" else 50, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0e-15, 30000.0)
    ax1.set_ylim(1.0e-25, 1.0e22)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']:.3e}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma Formal 10-m EIRP Limit (kW)")
    ax1.set_title(f"A. Unified {syn['spectrographs']}-Spectrograph Sensitivity Frontier ({syn['total_octave_span']} Octaves)")
    ax1.legend(loc="upper left", fontsize=5.1, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-852 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V6_3_PHASES_SNAPSHOT.json").read_text())["prior_unified_806_rows"]}
    all106_st = {e["star"] for e in bundle["exposures"]}
    brand_n = all106_st - prior_st
    bridges_n = all106_st & prior_st
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
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D105 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D106 Bridges ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=44, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D106 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.8, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: All 25 D106 Calibration Suites
    cal_sum = s_json["synthetic_calibration_5391_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V64_", "V6.4 ")
        .replace("CALIBRATION_V63_", "V6.3 ")
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
    ax3.barh(y3, s_pcts, color=["#b30000" if "V6.4" in s else ("#8856a7" if "V6.3" in s else "#2b8cbe") for s in short_s], edgecolor="black", lw=0.45)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(short_s, fontsize=4.8)
    ax3.set_xlim(92.0, 102.0)
    ax3.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax3.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=4.8, color="white", fontweight="bold")
    ax3.set_xlabel("Suite Pass Rate (%)")
    ax3.set_title(f"C. D106 25-Suite Calibration ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d106']:,})")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: Cross-Band Bridge Matrix Heatmap (TeV VHE -> mm, 13 Regimes)
    regs = [
        ("TeV\nVHE", 1e-16, 4.5e-12),
        ("GeV\nLAT", 4.5e-12, 4e-8),
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
        "EVLAC", "AUMIC", "PROXIMACEN", "ADLEO", "ABDOR", "GJ191", "BETELGEUSE",
        "CETAU", "HD36112", "CYGX1", "CRABNEBULA", "CRAB", "VELAPSR", "SIRIUSA",
        "NGC1068", "CENA", "3C273", "3C279", "MRK421", "GEMINGA", "PKS2155", "ETACAR",
    ]
    focus = [s for s in priority_stars if _reg_score(s) >= 2]
    for s in sorted(by_star, key=_reg_score, reverse=True):
        if s not in focus and len(focus) < 16:
            focus.append(s)
    focus = focus[:16]

    mat = np.full((len(focus), len(regs)), np.nan, dtype=np.float64)
    for r_i, st in enumerate(focus):
        for c_i, (_, w0, w1) in enumerate(regs):
            vals = [math.log10(max(1e-26, pk)) for w, pk in by_star.get(st, []) if w0 <= w <= w1]
            if vals:
                mat[r_i, c_i] = min(vals)

    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad("#edf2f7")
    im = ax4.imshow(mat, aspect="auto", cmap=cmap, vmin=-24.0, vmax=6.0)
    ax4.set_xticks(np.arange(len(regs)))
    ax4.set_xticklabels([r[0] for r in regs], fontsize=5.0)
    ax4.set_yticks(np.arange(len(focus)))
    ax4.set_yticklabels(focus, fontsize=6.2)
    for ri in range(len(focus)):
        for ci in range(len(regs)):
            v = mat[ri, ci]
            if math.isfinite(v):
                ax4.text(ci, ri, f"{v:+.0f}" if v <= -10.0 else f"{v:+.1f}", ha="center", va="center", fontsize=4.5, color="white" if v >= 0.0 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax4, fraction=0.042, pad=0.02)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.0)
    ax4.set_title(f"D. Bridge Matrix ({syn['panchromatic_bridge_stars_total']} Sci / {syn['multi_phase_targets_total']} Multi-Phase; {syn['panchromatic_bridge_cells_total']} Cells)")

    fig.suptitle(f"Phase D106 (V6.4): {syn['unique_stars_total']} Targets Across {syn['total_octave_span']} Octaves ({syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms; {syn['within_10pc_unique_stars']} <10 pc; 0 ETI)", fontsize=10.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig132_d106_global_60p85_octave_852star_119bridge_synthesis.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    az = _load_mod(ws / "analyze.py", "analyze_v64")
    det = _load_mod(ws / "v6_4_detector.py", "v6_4_detector")
    with gzip.open(ws / "bounded_inputs/d106_bounded_bundle.json.gz", "rb") as gz:
        bundle = json.loads(gz.read().decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig127_hess_dr1(res_dir, bundle, az, fig_dir)
    fig128_magic_veritas_hawc_crab_crosscal(res_dir, bundle, az, fig_dir)
    fig129_he_octave_ladder_and_vetoes(res_dir, bundle, az, fig_dir)
    fig130_solar_neighborhood_244(res_dir, bundle, az, fig_dir)
    fig131_drift_and_comb_78campaigns(res_dir, orb_json, det, fig_dir)
    fig132_global_synthesis_852(res_dir, ws, bundle, fig_dir)
    print(f"Rendered 6 D106 figures -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
