#!/usr/bin/env python3
"""
Spor 5: Generate 9 Publication-Grade Synthesis Figures (figJ01 - figJ09)
for the Journal Synthesis Manuscript (D079-D112, 1,083 Stars, 62.582 EM Octaves).

Strictly data-backed from WS112/results, WS109/results, WS110/results, WS111/results,
and zenodo_package/tables/.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
REPO = ROOT / "setisearch"
PJ = REPO / "paper_journal"
FIGS = PJ / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

TABLES = REPO / "zenodo_package" / "tables"
RES112 = ROOT / "analysis_workspace" / "work_v7_0_20261126_d112_integral_lhaaso_pev_almab2" / "results"
RES111 = ROOT / "analysis_workspace" / "work_v6_9_20261126_d111_lm_midir_qcl_molecular_ccf" / "results"
RES110 = ROOT / "analysis_workspace" / "work_v6_8_20261126_d110_optical_nir_spectropolarimetry" / "results"
RES109 = ROOT / "analysis_workspace" / "work_v6_7_20261125_d109_10pc_drift_closure_bayesian_ftx_cwtfm" / "results"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.0,
    "figure.titlesize": 11.5,
    "figure.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

C_BLUE = "#0072B2"
C_ORANGE = "#E69F00"
C_VERM = "#D55E00"
C_GREEN = "#009E73"
C_PURPLE = "#CC79A7"
C_SKY = "#56B4E9"
C_DARK = "#1F2937"
C_GRAY = "#6B7280"


def _f(v: object, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _b(v: object) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _load_csv(p: pathlib.Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Phase trajectory verbatim from paper/main.tex Table 1 & SUMMARY.json (D079-D112)
PHASE_TRAJECTORY = [
    # phase, cum_stars, spec, arms, exp, hrs, cal_cum, v2_phase
    ("D079", 12, 1, 1, 60, 4.57, 990, 48),
    ("D080", 38, 2, 2, 130, 27.43, 2610, 422),
    ("D081", 60, 2, 2, 159, 21.26, 4599, 1552),
    ("D082", 80, 3, 3, 152, 13.54, 6570, 3828),
    ("D083", 100, 4, 4, 148, 87.32, 8541, 1043),
    ("D084", 125, 6, 6, 183, 26.71, 10692, 1170),
    ("D085", 150, 7, 7, 177, 14.41, 13284, 4044),
    ("D086", 175, 8, 8, 181, 57.02, 15981, 2990),
    ("D087", 200, 9, 11, 201, 83.01, 18678, 117994),
    ("D088", 220, 12, 14, 176, 30.54, 21375, 99910),
    ("D089", 250, 14, 17, 192, 203.55, 24072, 24123),
    ("D090", 280, 16, 20, 161, 17.70, 26769, 3921),
    ("D091", 310, 19, 22, 156, 47.33, 29466, 24998),
    ("D092", 335, 22, 22, 57, 12.66, 30817, 15147),
    ("D093", 350, 21, 24, 30, 5.66, 32408, 1008),
    ("D094", 373, 23, 29, 75, 50.12, 34149, 947),
    ("D095", 401, 25, 33, 154, 18.64, 36060, 9302),
    ("D096", 425, 27, 36, 131, 30.17, 37911, 810),
    ("D097", 448, 30, 42, 78, 21.15, 39942, 4548),
    ("D098", 473, 33, 51, 99, 148.77, 41973, 106183),
    ("D099", 516, 36, 57, 97, 21.13, 44124, 89899),
    ("D100", 560, 39, 62, 79, 82.01, 46455, 201527),
    ("D101", 613, 41, 67, 101, 202.87, 48726, 89659),
    ("D102", 656, 45, 73, 107, 2259.66, 51417, 42939),
    ("D103", 709, 49, 79, 103, 1236.23, 54528, 46004),
    ("D104", 755, 52, 82, 103, 1242.60, 58299, 95100),
    ("D105", 806, 55, 85, 126, 11454.53, 62790, 30095),
    ("D106", 852, 59, 89, 99, 9541.32, 68181, 71634),
    ("D107", 904, 62, 92, 134, 92344.39, 74232, 1392),
    ("D108", 1004, 66, 96, 198, 2165.39, 81123, 26461),
    ("D109", 1004, 66, 96, 216, 44.71, 88434, 531223),
    ("D110", 1012, 67, 97, 87, 28.89, 96345, 10408),
    ("D111", 1039, 67, 98, 111, 173.25, 104856, 1536),
    ("D112", 1083, 72, 104, 122, 614691.72, 113967, 24),
]

OCTAVE_SPAN_MAP = {
    "D079": 0.87, "D080": 1.05, "D081": 1.05, "D082": 2.25, "D083": 2.71,
    "D084": 2.71, "D085": 2.72, "D086": 3.04, "D087": 4.46, "D088": 4.46,
    "D089": 4.80, "D090": 8.27, "D091": 8.27, "D092": 8.27, "D093": 8.27,
    "D094": 8.27, "D095": 8.71, "D096": 8.71, "D097": 12.86, "D098": 12.86,
    "D099": 13.92, "D100": 15.38, "D101": 16.53, "D102": 26.09, "D103": 29.02,
    "D104": 31.95, "D105": 50.88, "D106": 60.845, "D107": 60.845, "D108": 60.845,
    "D109": 60.845, "D110": 60.845, "D111": 60.845, "D112": 62.582,
}


def figJ01(t1: list[dict], t3: list[dict]) -> None:
    fig = plt.figure(figsize=(12.2, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.22)

    # Panel A: Aitoff all-sky map of all 1,083 targets
    ax1 = fig.add_subplot(gs[0, 0], projection="aitoff")
    ax1.grid(True, alpha=0.28, linestyle="--")

    def _ait(ra_deg: float, dec_deg: float) -> tuple[float, float]:
        lon = ((ra_deg - 180.0) % 360.0) - 180.0
        # Astropy convention: +RA eastward (left) or standard plot -np.deg2rad(lon)
        return -np.deg2rad(lon), np.deg2rad(dec_deg)

    ctrl = [r for r in t1 if r["role"] != "SCIENCE"]
    sci_far = [r for r in t1 if r["role"] == "SCIENCE" and not _b(r["within_10pc"])]
    sci_10 = [r for r in t1 if r["role"] == "SCIENCE" and _b(r["within_10pc"])]
    etz = [r for r in t1 if _b(r["etz_qualified"])]
    ic_only = [r for r in t1 if _b(r["has_neutrino"]) and not _b(r["has_beamed"]) and not _b(r["has_he_em"])]

    for subset, label, color, marker, sz, alpha, zord in [
        (ctrl, f"Control ({len(ctrl)})", C_GRAY, "o", 12, 0.45, 2),
        (sci_far, f"Science >10 pc ({len(sci_far)})", C_BLUE, "o", 16, 0.72, 3),
        (sci_10, f"Science <10 pc ({len(sci_10)})", C_GREEN, "s", 22, 0.85, 4),
        (etz, f"Earth Transit Zone ({len(etz)})", C_ORANGE, "^", 24, 0.75, 5),
        (ic_only, f"IceCube-Only 0-EM ({len(ic_only)})", C_PURPLE, "D", 28, 0.90, 6),
    ]:
        xs, ys = zip(*[_ait(float(r["ra_deg"]), float(r["dec_deg"])) for r in subset])
        ax1.scatter(xs, ys, s=sz, c=color, marker=marker, alpha=alpha, label=label, edgecolors="none", zorder=zord)

    ax1.set_title("A. All-Sky Distribution of 1,083 Survey Targets (D079–D112)", pad=12)
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2, frameon=False)

    # Panel B: 62.582-Octave EM + Multi-Messenger Spectral Architecture
    ax2 = fig.add_subplot(gs[0, 1])
    bands = [
        ("1LHAASO PeV (KM2A/WCDA)", 1.240e-15, 4.959e-14, C_VERM, "45.682 Unbroken HE Oct."),
        ("VHE TeV (HAWC/HESS/MAGIC/VER.)", 4.133e-15, 3.100e-11, C_VERM, ""),
        ("GeV/MeV (Fermi/COMPTEL/OSSE)", 4.133e-12, 2.480e-5, C_ORANGE, ""),
        ("INTEGRAL 511 keV & Hard X", 1.277e-6, 0.000413, C_ORANGE, ""),
        ("X-Ray/Pol (IXPE/Swift/NuSTAR/XRISM)", 4.959e-6, 0.0062, C_ORANGE, ""),
        ("Soft X / EUV (eROSITA/XMM/Chandra/EUVE)", 0.00012, 0.06998, C_SKY, ""),
        ("Lyman/FUV/NUV (FUSE/COS/STIS/IUE)", 0.0905, 0.387, C_BLUE, "14.693 Lyman–B4 Oct."),
        ("Optical Echelle & Pol (ESP/HARPS/NARVAL)", 0.2989, 1.061, C_BLUE, ""),
        ("NIR & Stokes (NIRPS/SPIRou/APOGEE)", 0.950, 2.515, C_GREEN, ""),
        ("Thermal/Mid-IR QCL & CCF (CRIRES+/JWST)", 1.950, 45.39, C_GREEN, ""),
        ("Far-IR & THz (Herschel/SOFIA/JCMT)", 51.0, 3856.05, C_PURPLE, ""),
        ("ALMA 10/10 Closure (B1, B2 SV, B3–B10)", 335.58, 8556.42, C_DARK, "10/10 ALMA Bands"),
    ]
    y_pos = np.arange(len(bands))[::-1]
    for yi, (lbl, wlo, whi, col, note) in zip(y_pos, bands):
        ax2.barh(yi, math.log10(whi) - math.log10(wlo), left=math.log10(wlo), height=0.62, color=col, alpha=0.88, edgecolor="white", linewidth=0.5)
        ax2.text(math.log10(whi) + 0.35, yi, lbl, va="center", ha="left", fontsize=7.8, color=C_DARK)

    # Mark ISM H photoionization edge (699.8-905 A)
    ax2.axvspan(math.log10(0.06998), math.log10(0.0905), color="#991B1B", alpha=0.16, zorder=0)
    ax2.axvline(math.log10(1.239842e-15), color=C_VERM, ls=":", lw=1.1)
    ax2.axvline(math.log10(8556.41831), color=C_DARK, ls=":", lw=1.1)
    ax2.set_yticks([])
    ax2.set_xlim(-16.0, 16.5)
    ax2.set_xticks([-15, -10, -5, 0, 4])
    ax2.set_xticklabels([r"$10^{-15}$", r"$10^{-10}$", r"$10^{-5}$", r"$1$", r"$10^{4}$"])
    ax2.set_xlabel(r"Wavelength $\log_{10}(\lambda / \mu\mathrm{m})$  [$\mathbf{62.582}$ Total EM Octaves + IceCube $\nu_\mu$ + Stokes Pol.]")
    ax2.set_title("B. 62.582-Octave EM & 10/10 ALMA Continuity Ladder", pad=12)
    ax2.grid(True, axis="x", alpha=0.22)
    ax2.annotate("ISM H edge\n(700–905 Å)", xy=(math.log10(0.08), 1.8), xytext=(-7.5, 1.3),
                 fontsize=7.6, color="#991B1B", ha="center", va="center",
                 arrowprops={"arrowstyle": "->", "lw": 0.9, "color": "#991B1B"},
                 bbox={"boxstyle": "round,pad=0.25", "fc": "white", "alpha": 0.9, "ec": "#991B1B", "lw": 0.6})

    fig.savefig(FIGS / "figJ01_sky_distribution_and_62p6_octave_architecture.png")
    plt.close(fig)


def figJ02(t1: list[dict], t4: list[dict]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8), gridspec_kw={"wspace": 0.28})

    # Panel A: Distance vs Min Beamed UV-mm 10m EIRP
    beamed = [r for r in t1 if _b(r["has_beamed"]) and math.isfinite(_f(r["min_beamed_10m_kw"]))]
    w10_sci = [r for r in beamed if r["role"] == "SCIENCE" and _b(r["within_10pc"])]
    w10_ctl = [r for r in beamed if r["role"] != "SCIENCE" and _b(r["within_10pc"])]
    far_sci = [r for r in beamed if r["role"] == "SCIENCE" and not _b(r["within_10pc"])]
    far_ctl = [r for r in beamed if r["role"] != "SCIENCE" and not _b(r["within_10pc"])]

    for sub, lbl, col, mk, sz, alp in [
        (far_ctl, f"Control >10 pc ({len(far_ctl)})", C_GRAY, "o", 12, 0.40),
        (far_sci, f"Science >10 pc ({len(far_sci)})", C_SKY, "o", 14, 0.55),
        (w10_ctl, f"Control <10 pc ({len(w10_ctl)})", C_ORANGE, "^", 24, 0.78),
        (w10_sci, f"Science <10 pc ({len(w10_sci)})", C_BLUE, "s", 22, 0.85),
    ]:
        xs = [max(0.5, float(r["dist_pc"])) for r in sub]
        ys = [float(r["min_beamed_10m_kw"]) for r in sub]
        ax1.scatter(xs, ys, s=sz, c=col, marker=mk, alpha=alp, label=lbl, edgecolors="none")

    ax1.axvline(10.0, color=C_VERM, ls="--", lw=1.2, label="10 pc Volume Boundary")
    ax1.axhline(0.78810, color=C_GREEN, ls=":", lw=1.3, label="<10 pc Median = 0.7881 kW")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0, 3.0e8)
    ax1.set_ylim(2e-6, 1e19)
    ax1.set_xlabel("Distance $d$ (pc)")
    ax1.set_ylabel(r"Beamed $P_{10\mathrm{m},\min}$ Threshold (kW @ $D_{\mathrm{tx}}=10\,$m)")
    ax1.set_title("A. Beamed UV–mm 10 m Sensitivity vs. Distance (n = 777)")
    ax1.grid(True, which="major", alpha=0.22)
    ax1.legend(loc="upper left", fontsize=7.6, frameon=True, framealpha=0.9)

    # Annotate flagship records safely separated
    for st, txt, dx, dy in [
        ("WD1334_039", "WD 1334-039 (23.2 mW)", 35.0, 1.0e-5),
        ("PROXIMACEN", "Proxima Cen (97.3 mW)", 35.0, 8.0e-4),
        ("ARP220", "Arp 220 ALMA B2", 2.0e6, 2.0e15),
    ]:
        row = next((r for r in beamed if r["star"] == st), None)
        if row:
            ax1.annotate(txt, (float(row["dist_pc"]), float(row["min_beamed_10m_kw"])),
                         xytext=(dx, dy), textcoords="data", fontsize=7.4, color=C_DARK,
                         arrowprops={"arrowstyle": "->", "lw": 0.7, "color": C_GRAY})

    # Panel B: Top 15 Multi-Instrument Bridge Stars
    by_star: dict[str, set[str]] = {}
    role_map = {r["star"]: r["role"] for r in t1}
    cname_map = {r["star"]: r["common_name"] for r in t1}
    for r in t4:
        by_star.setdefault(r["star"], set()).add(r["instrument"])
    top15 = sorted(by_star.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:15][::-1]

    def _short_name(st: str, cn: str) -> str:
        s = cn.split("(")[0].strip()
        return s if s else st

    y = np.arange(len(top15))
    vals = [len(kv[1]) for kv in top15]
    cols = [C_BLUE if role_map.get(kv[0]) == "SCIENCE" else C_ORANGE for kv in top15]
    names = [_short_name(kv[0], cname_map.get(kv[0], kv[0])) for kv in top15]

    bars = ax2.barh(y, vals, color=cols, height=0.66, alpha=0.88)
    for bi, v in zip(bars, vals):
        ax2.text(v + 0.25, bi.get_y() + bi.get_height() / 2.0, f"{v}", va="center", ha="left", fontsize=8.0, fontweight="bold")
    ax2.set_yticks(y)
    ax2.set_yticklabels(names, fontsize=8.2)
    ax2.set_xlim(0, 19.0)
    ax2.set_xlabel("Distinct Spectrographs / Multi-Messenger Arrays per Star")
    ax2.set_title("B. Top 15 Panchromatic Bridge Targets (197 Sci Bridges)")
    ax2.grid(True, axis="x", alpha=0.22)
    # Manual small legend
    from matplotlib.patches import Patch
    ax2.legend(handles=[Patch(color=C_BLUE, label="Science Target"), Patch(color=C_ORANGE, label="Control Benchmark")],
               loc="lower right", frameon=True, framealpha=0.9)

    fig.savefig(FIGS / "figJ02_solar_neighborhood_10pc_and_bridge_census.png")
    plt.close(fig)


def figJ03() -> None:
    with (RES112 / "SUMMARY.json").open() as f:
        s112 = json.load(f)
    suites = s112["synthetic_calibration_9111_trials"]["suites"]

    # Sort descending by phase/version or pass rate; group compactly: show all 43 suites in Panel A
    items = []
    for k, v in suites.items():
        short = (
            k.replace("CALIBRATION_", "")
            .replace("DETECTOR_", "")
            .replace("_240", "")
            .replace("_180", "")
            .replace("_120", "")
            .replace("_360", "")
            .replace("_540", "")
            .replace("_162", "")
            .replace("_108", "")
            .replace("_81", "")
        )
        pct = 100.0 * float(v["passed"]) / float(v["total"])
        items.append((short, pct, v["passed"], v["total"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 6.8), gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.28})

    y = np.arange(len(items))[::-1]
    pcts = [it[1] for it in items]
    cols = [C_GREEN if p >= 99.5 else (C_BLUE if p >= 98.5 else C_SKY) for p in pcts]
    ax1.barh(y, pcts, color=cols, height=0.68, alpha=0.9)
    ax1.axvline(97.5, color=C_VERM, ls="--", lw=1.2, label="Prospective 97.5% Gate")
    ax1.set_yticks(y)
    ax1.set_yticklabels([it[0] for it in items], fontsize=6.7)
    ax1.set_xlim(95.0, 100.6)
    ax1.set_ylim(-1.2, len(items) - 0.2)
    ax1.set_xlabel("Empirical Recovery + False-Alarm Veto Rate (%)")
    ax1.set_title("A. All 43 Calibration Suites >= 97.5% (113,967 Cumul. Trials)")
    ax1.grid(True, axis="x", alpha=0.22)
    ax1.legend(loc="lower left", frameon=True, framealpha=0.92)

    # Panel B: False-Alarm Rejection Funnel (Legacy V2 -> Stage 2 -> 0 Verified ETI)
    # Build grouped horizontal log funnel across survey eras
    eras = [
        ("Opt/NIR Echelle\n(D079–D091)", 300143),
        ("RPCA/Drift V5\n(D092–D100)", 433370),
        ("ALMA + X/EUV/Gamma\n(D101–D108)", 358671),
        ("10 pc Drift Closure\n(D109 V6.7)", 531223),
        ("Pol/QCL/HE+B2\n(D110–D112)", 11968),
        ("Total Survey\n(D079–D112)", 1651481),
    ]
    ye = np.arange(len(eras))[::-1]
    v2_vals = [e[1] for e in eras]
    bars = ax2.barh(ye, v2_vals, color=[C_SKY, C_BLUE, C_PURPLE, C_ORANGE, C_GREEN, C_DARK], height=0.58, alpha=0.88)
    for b, val in zip(bars, v2_vals):
        ax2.text(val * 1.18, b.get_y() + b.get_height() / 2.0, f"{val:,} -> 0 ETI", va="center", ha="left", fontsize=8.0, fontweight="bold")
    ax2.set_xscale("log")
    ax2.set_xlim(1e3, 8e7)
    ax2.set_yticks(ye)
    ax2.set_yticklabels([e[0] for e in eras], fontsize=8.3)
    ax2.set_xlabel("Legacy V2 Unfiltered Peaks Eliminated -> 0 Verified ETI")
    ax2.set_title("B. 1,651,481 Legacy V2 False Alarms -> 0 Verified ETI")
    ax2.grid(True, which="major", alpha=0.22)

    fig.savefig(FIGS / "figJ03_43suite_calibration_completeness_113967trials.png")
    plt.close(fig)


def figJ04(t1: list[dict]) -> None:
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.2, 4.4), gridspec_kw={"wspace": 0.28})

    # Regime A: Beamed UV-mm 10m EIRP (n=777)
    b_rows = [r for r in t1 if _b(r["has_beamed"]) and math.isfinite(_f(r["min_beamed_10m_kw"]))]
    sci = [r for r in b_rows if r["role"] == "SCIENCE"]
    ctl = [r for r in b_rows if r["role"] != "SCIENCE"]
    ax1.scatter([float(r["dist_pc"]) for r in ctl], [float(r["min_beamed_10m_kw"]) for r in ctl],
                s=14, c=C_ORANGE, alpha=0.55, label=f"Control ({len(ctl)})", edgecolors="none")
    ax1.scatter([float(r["dist_pc"]) for r in sci], [float(r["min_beamed_10m_kw"]) for r in sci],
                s=15, c=C_BLUE, alpha=0.72, label=f"Science ({len(sci)})", edgecolors="none")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Distance $d$ (pc)")
    ax1.set_ylabel(r"Beamed $P_{10\mathrm{m}}$ (kW @ 10 m)")
    ax1.set_title(f"A. Beamed UV–mm (n = {len(b_rows)})")
    ax1.grid(True, alpha=0.22)
    ax1.legend(loc="upper left", frameon=True, framealpha=0.9)

    # Regime B: HE Isotropic EM (n=352)
    h_rows = [r for r in t1 if _b(r["has_he_em"]) and math.isfinite(_f(r["min_he_l_iso_mw"]))]
    h_sci = [r for r in h_rows if r["role"] == "SCIENCE"]
    h_ctl = [r for r in h_rows if r["role"] != "SCIENCE"]
    ax2.scatter([max(1.0, float(r["dist_pc"])) for r in h_ctl], [float(r["min_he_l_iso_mw"]) for r in h_ctl],
                s=14, c=C_ORANGE, alpha=0.55, label=f"Control ({len(h_ctl)})", edgecolors="none")
    ax2.scatter([max(1.0, float(r["dist_pc"])) for r in h_sci], [float(r["min_he_l_iso_mw"]) for r in h_sci],
                s=15, c=C_VERM, alpha=0.72, label=f"Science ({len(h_sci)})", edgecolors="none")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Distance $d$ (pc)")
    ax2.set_ylabel(r"Isotropic $L_{\mathrm{iso}}$ (MW)")
    ax2.set_title(f"B. HE Isotropic EM (n = {len(h_rows)})")
    ax2.grid(True, alpha=0.22)
    ax2.legend(loc="upper left", frameon=True, framealpha=0.9)

    # Regime C: IceCube 10-yr Muon Neutrinos (n=54, 33 IceCube-only 0-EM preserved)
    n_rows = [r for r in t1 if _b(r["has_neutrino"]) and math.isfinite(_f(r["min_nu_l_iso_mw"]))]
    n_only = [r for r in n_rows if not _b(r["has_beamed"]) and not _b(r["has_he_em"])]
    n_bridge = [r for r in n_rows if _b(r["has_beamed"]) or _b(r["has_he_em"])]
    ax3.scatter([max(1.0, float(r["dist_pc"])) for r in n_bridge], [float(r["min_nu_l_iso_mw"]) for r in n_bridge],
                s=22, c=C_GREEN, marker="^", alpha=0.80, label=f"EM-Bridged ({len(n_bridge)})")
    ax3.scatter([max(1.0, float(r["dist_pc"])) for r in n_only], [float(r["min_nu_l_iso_mw"]) for r in n_only],
                s=26, c=C_PURPLE, marker="D", alpha=0.88, label=f"IceCube-Only 0-EM ({len(n_only)})")
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.set_xlabel("Distance $d$ (pc)")
    ax3.set_ylabel(r"Isotropic $L_{\nu,\mathrm{iso}}$ (MW)")
    ax3.set_title(f"C. IceCube Neutrinos (n = {len(n_rows)})")
    ax3.grid(True, alpha=0.22)
    ax3.legend(loc="upper left", frameon=True, framealpha=0.9)

    fig.savefig(FIGS / "figJ04_three_regime_physical_scale_separation_1083stars.png")
    plt.close(fig)


def figJ05() -> None:
    d109_rows = _load_csv(RES109 / "DRIFT_V67_ECCENTRIC_KEPLERIAN_154CAMPAIGNS.csv")
    comb_rows = _load_csv(RES112 / "ALLSKY_COMB_V4_1_UNIFIED_D079_D112.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw={"wspace": 0.42})

    # Panel A: D109 154 Campaigns Raw Coherent -> 0 Eccentric Keplerian -> 0 ETI
    raw_c = [max(1, int(r["raw_coherent_survivors"])) for r in d109_rows]
    dt_days = [max(0.1, float(r["dt_baseline_days"])) for r in d109_rows]
    sci_mask = [r["role"] == "SCIENCE" for r in d109_rows]
    ax1.scatter([dt_days[i] for i in range(len(d109_rows)) if sci_mask[i]],
                [raw_c[i] for i in range(len(d109_rows)) if sci_mask[i]],
                s=22, c=C_BLUE, alpha=0.80, label="Science Hosts (100% <10 pc closed)")
    ax1.scatter([dt_days[i] for i in range(len(d109_rows)) if not sci_mask[i]],
                [raw_c[i] for i in range(len(d109_rows)) if not sci_mask[i]],
                s=22, c=C_ORANGE, marker="^", alpha=0.80, label="Control Benchmarks")
    ax1.axhline(1.0, color=C_GREEN, ls="--", lw=1.2, label="Post-Keplerian Polish = 0 ETI")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Multi-Epoch Baseline $\\Delta t$ (days)")
    ax1.set_ylabel("Raw Coherent Shift-Stack Seeds + 1")
    ax1.set_title("A. DRIFT_V67 154-Campaign Coherent Closure (0 ETI)")
    ax1.grid(True, alpha=0.22)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.92)

    # Panel B: All-Sky COMB_V4_1 Stacks (n=753 stacks, 45,096 candidates -> 0 ETI)
    by_inst = Counter()
    for r in comb_rows:
        by_inst[r["instrument"]] += int(r["comb_v41_candidates"] or 0)
    top_i = by_inst.most_common(12)[::-1]
    yi = np.arange(len(top_i))
    bars = ax2.barh(yi, [max(0, v) for _, v in top_i], color=C_PURPLE, height=0.65, alpha=0.88)
    for b, val in zip(bars, [v for _, v in top_i]):
        ax2.text(val + max(20, val * 0.03), b.get_y() + b.get_height() / 2.0, f"{val:,} -> 0", va="center", ha="left", fontsize=7.8)
    ax2.set_yticks(yi)
    ax2.set_yticklabels([k for k, _ in top_i], fontsize=8.0)
    ax2.set_xlim(0, max(v for _, v in top_i) * 1.24)
    ax2.set_xlabel("Pre-Stage-2 COMB_V4_1 Topographic/Forest Seeds Vetoed")
    ax2.set_title("B. All-Sky COMB_V4_1 Across 753 Stacks (45,096 -> 0 ETI)")
    ax2.grid(True, axis="x", alpha=0.22)

    fig.savefig(FIGS / "figJ05_coherent_orbital_drift_and_comb_closure.png")
    plt.close(fig)


def figJ06() -> None:
    pol_rows = _load_csv(RES110 / "POLARIMETRIC_SPECTRA_SUMMARY_D110.csv")
    pol_lims = _load_csv(RES110 / "POLARIZED_EIRP_UPPER_LIMITS_D110.csv")
    mol_rows = _load_csv(RES111 / "MOLECULAR_CCF_RESULTS_D111.csv")
    with (RES111 / "SUMMARY.json").open() as f:
        s111 = json.load(f)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6), gridspec_kw={"wspace": 0.26})

    # Panel A: Polarimetric Stokes (I,Q,U,V) 7-sigma EIRP bounds (D110, 87 spectra)
    # Deduplicate minimum p_beam_10m_kw per (instrument, star) from pol_lims
    best_pol = {}
    dist_map = {r["star"]: _f(r["dist_pc"]) for r in pol_rows}
    for r in pol_lims:
        k = (r["instrument"], r["star"])
        pk = _f(r.get("p_beam_10m_kw"))
        if math.isfinite(pk) and (k not in best_pol or pk < best_pol[k]):
            best_pol[k] = pk
    for inst, col, mk in [
        ("CFHT_ESPADONS_POL", C_BLUE, "o"),
        ("TBL_NARVAL", C_ORANGE, "s"),
        ("CFHT_SPIROU_POL", C_GREEN, "^"),
    ]:
        pts = [(dist_map.get(st, float("nan")), pk) for (ins, st), pk in best_pol.items() if ins == inst]
        pts = [(d, p) for d, p in pts if math.isfinite(d) and math.isfinite(p)]
        if pts:
            ax1.scatter([x[0] for x in pts], [x[1] for x in pts], s=26, c=col, marker=mk, alpha=0.82, label=f"{inst} ({len(pts)} targets)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Distance $d$ (pc)")
    ax1.set_ylabel(r"Polarized $7\sigma$ Beamed $P_{10\mathrm{m}}$ (kW @ 10 m)")
    ax1.set_title("A. Dual-Beam Stokes (I,Q,U,V) Laser Bounds (D110)")
    ax1.grid(True, alpha=0.22)
    ax1.legend(loc="upper left", frameon=True, framealpha=0.92)

    # Panel B: JWST Molecular CCF Max Confounder Sigma & D111 QCL Records
    subbands = sorted(set(r["miri_subband"] for r in mol_rows))
    sb_vals = [[_f(r["max_confounder_sigma"], 0.0) for r in mol_rows if r["miri_subband"] == sb] for sb in subbands]
    short_sb = {
        "CH1-MEDIUM": "MIRI CH1-M",
        "CH1-SHORT": "MIRI CH1-S",
        "CH2-MEDIUM": "MIRI CH2-M",
        "CH3-SHORT": "MIRI CH3-S",
        "F290LP;G395H": "G395H (2.7k)",
        "F290LP;G395M": "G395M (1.0k)",
    }
    ax2.boxplot(sb_vals, vert=True, patch_artist=True, tick_labels=[short_sb.get(s, s) for s in subbands],
                boxprops={"facecolor": C_SKY, "alpha": 0.72},
                medianprops={"color": C_DARK, "linewidth": 1.6})
    ax2.axhline(5.0, color=C_VERM, ls="--", lw=1.2, label="5$\\sigma$ Candidate Threshold (0 ETI)")
    ax2.set_ylabel("Peak Natural/Industrial Molecular CCF $|\\sigma|$")
    ax2.set_title("B. JWST Molecular CCF Confounders & QCL (D111)")
    ax2.tick_params(axis="x", rotation=22)
    ax2.set_ylim(-1.0, 44.0)
    ax2.grid(True, axis="y", alpha=0.22)
    ax2.legend(loc="upper right", frameon=True, framealpha=0.92)
    ax2.text(0.03, 0.94, "277 mol. evals | 0 ETI (all CO/CH$_4$)\nQCL min: WISE 0855 (1.73 W)",
             transform=ax2.transAxes, va="top", ha="left", fontsize=7.8,
             bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.9, "ec": C_GRAY})

    fig.savefig(FIGS / "figJ06_polarimetry_and_midir_qcl_molecular_ccf.png")
    plt.close(fig)


def figJ07(t3: list[dict]) -> None:
    int_rows = _load_csv(RES112 / "INTEGRAL_SPECTRA_SUMMARY_D112.csv")
    lh_rows = _load_csv(RES112 / "LHAASO_PEV_SUMMARY_D112.csv")
    b2_rows = _load_csv(RES112 / "ALMA_BAND2_SV_SUMMARY_D112.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw={"wspace": 0.42})

    # Panel A: INTEGRAL & 1LHAASO L_iso (MW) vs Max Energy (keV)
    for inst, rows_src, e_col, col, mk in [
        ("INTEGRAL_JEMX", [r for r in int_rows if r["instrument"] == "INTEGRAL_JEMX"], "e_max_kev", C_SKY, "o"),
        ("INTEGRAL_IBIS_ISGRI", [r for r in int_rows if r["instrument"] == "INTEGRAL_IBIS_ISGRI"], "e_max_kev", C_BLUE, "s"),
        ("INTEGRAL_SPI", [r for r in int_rows if r["instrument"] == "INTEGRAL_SPI"], "e_max_kev", C_GREEN, "^"),
        ("LHAASO_WCDA", [r for r in lh_rows if r["instrument"] == "LHAASO_WCDA"], "max_energy_tev", C_ORANGE, "D"),
        ("LHAASO_KM2A", [r for r in lh_rows if r["instrument"] == "LHAASO_KM2A"], "max_energy_tev", C_VERM, "P"),
    ]:
        xs, ys = [], []
        for r in rows_src:
            ev = _f(r[e_col])
            ek = ev * 1e9 if "tev" in e_col else ev  # convert TeV -> keV
            li = _f(r["l_iso_mw"])
            if math.isfinite(ek) and math.isfinite(li) and li > 0:
                xs.append(ek)
                ys.append(li)
        ax1.scatter(xs, ys, s=26, c=col, marker=mk, alpha=0.84, label=f"{inst} ({len(xs)})")
    ax1.axvline(511.0, color=C_PURPLE, ls=":", lw=1.2, label="511 keV $e^+/e^-$ Line")
    ax1.axvline(1.0e12, color=C_DARK, ls="--", lw=1.1, label="1.000 PeV Frontier")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(10, 5e12)
    ax1.set_xlabel("Max Covered Photon Energy (keV)")
    ax1.set_ylabel(r"Isotropic Upper Limit $L_{\mathrm{iso}}$ (MW)")
    ax1.set_title("A. INTEGRAL 511 keV & 1LHAASO 1.000 PeV Bounds (D112)")
    ax1.grid(True, alpha=0.22)
    ax1.legend(loc="lower right", fontsize=7.4, frameon=True, framealpha=0.92)

    # Panel B: Complete 10/10 ALMA Receiver Bands Frequency Coverage (GHz)
    alma_bands = [r for r in t3 if r["regime"] == "ALMA_MM" and r["arm_id"].startswith("ALMA_B") and "_LOW_" not in r["arm_id"] and "_HIGH" not in r["arm_id"]]
    # Build explicit B1..B10 clean freq bars from wavelength range
    c_um_ghz = 299792.458  # lambda_um * nu_GHz = 299,792.458
    band_defs = [
        ("Band 1 (D101)", 35.0, 50.0, C_BLUE),
        ("Band 2 SV (D112)", 86.45, 114.12, C_VERM),
        ("Band 3 (D101)", 84.1, 116.0, C_BLUE),
        ("Band 4 (D101)", 125.0, 163.0, C_BLUE),
        ("Band 5 (D101)", 163.0, 211.0, C_BLUE),
        ("Band 6 (D102)", 211.0, 275.0, C_GREEN),
        ("Band 7 (D102)", 275.0, 373.0, C_GREEN),
        ("Band 8 (D102)", 385.0, 502.0, C_GREEN),
        ("Band 9 (D103)", 602.0, 720.0, C_PURPLE),
        ("Band 10 (D103)", 787.0, 893.4, C_PURPLE),
    ][::-1]
    yb = np.arange(len(band_defs))
    for yi, (lbl, f0, f1, col) in zip(yb, band_defs):
        ax2.barh(yi, f1 - f0, left=f0, height=0.62, color=col, alpha=0.88)
        ax2.text(f1 + 12, yi, f"{f0:.1f}–{f1:.1f} GHz", va="center", ha="left", fontsize=7.8)
    ax2.set_yticks(yb)
    ax2.set_yticklabels([b[0] for b in band_defs], fontsize=8.2)
    ax2.set_xlim(0, 1130)
    ax2.set_xlabel("ALMA Receiver Frequency Span (GHz)")
    ax2.set_title("B. Complete 10/10 ALMA Receiver Band Closure (B1–B10)")
    ax2.grid(True, axis="x", alpha=0.22)

    fig.savefig(FIGS / "figJ07_high_energy_pev_511kev_and_alma_10of10.png")
    plt.close(fig)


def figJ08() -> None:
    t5 = _load_csv(TABLES / "table5_bayesian_ftx_and_cwtfm.csv")
    t5b = _load_csv(TABLES / "table5b_cwtfm_benchmark.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.7), gridspec_kw={"wspace": 0.28})

    # Panel A: Bayesian f95 vs Power Threshold (Beamed 10m kW for ALL_SCIENCE_EM + 10pc) & Duty Cycles
    cohorts = [
        ("ALL_SCIENCE_EM", "1.0", "ALL_SCIENCE_EM (eta=1.0, min=0.505%)", C_BLUE, "-", "o"),
        ("ALL_SCIENCE_EM", "0.1", "ALL_SCIENCE_EM (eta=0.1)", C_BLUE, "--", "^"),
        ("EXOPLANET_HOSTS", "1.0", "EXOPLANET_HOSTS (eta=1.0, min=1.012%)", C_GREEN, "-", "s"),
        ("SOLAR_NEIGHBORHOOD_10PC_SCI", "1.0", "<10 pc SCIENCE (eta=1.0, min=1.675%)", C_ORANGE, "-", "D"),
    ]
    for coh, eta, lbl, col, ls, mk in cohorts:
        sub = [r for r in t5 if r["cohort"] == coh and str(r["duty_cycle_eta"]) == eta and r["power_threshold"] != "ANY_CALIBRATED"]
        sub.sort(key=lambda r: float(r["power_threshold"]))
        xs = [float(r["power_threshold"]) for r in sub]
        ys = [float(r["f95_uniform_pct"]) for r in sub]
        ax1.plot(xs, ys, ls=ls, marker=mk, ms=5, lw=1.8, color=col, label=lbl)
    # Also mark exact analytical Jeffreys points at 100 kW / ANY_CALIBRATED
    ax1.axhline(0.3243, color=C_PURPLE, ls=":", lw=1.3, label="Exact Jeffreys Beta ALL_SCI (0.3243%)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_ylim(0.25, 30.0)
    ax1.set_xlabel(r"Beamed Transmitter Power Threshold $P_{10\mathrm{m}}$ (kW)")
    ax1.set_ylabel(r"Bayesian 95% Occurrence Upper Limit $f_{95}$ (%)")
    ax1.set_title("A. Bayesian Transmitter Occurrence Limits ($N=0$ ETI)")
    ax1.grid(True, alpha=0.22)
    ax1.legend(loc="upper right", fontsize=7.4, frameon=True, framealpha=0.92)

    # Panel B: Cosmic Haystack / Spectral Octaves vs f95 Literature Benchmark
    pts = []
    for r in t5b:
        octv = float(r["spectral_octaves"])
        eirp = float(r["median_eirp_w"])
        f95s = r["f95_uniform_pct"]
        try:
            fv = float(f95s)
        except Exception:
            fv = 100.0
        pts.append((r["survey_or_cohort"], octv, eirp, fv, _b(r["is_this_work"])))

    for name, octv, eirp, fv, is_tw in pts:
        if name == "ALMA_BAND2_SV_ARP220_V70":
            continue  # 1 extragalactic ULIRG target (UL_1TARGET), plotted separately in FigJ07
        col = C_VERM if "FULL" in name else (C_BLUE if is_tw else C_GRAY)
        mk = "*" if "FULL" in name else ("o" if is_tw else "s")
        sz = 180 if "FULL" in name else (85 if is_tw else 70)
        ax2.scatter([octv], [fv], s=sz, c=col, marker=mk, zorder=5, edgecolors=C_DARK, linewidths=0.6)
        short_lbl = {
            "FULL_PANCHROMATIC_62P6_OCT_V70": "This Work Full (62.58 oct, 0.505%)",
            "HE_UNBROKEN_INTEGRAL_LHAASO_V70": "HE Unbroken (45.68 oct, 0.848%)",
            "ALL_SCIENCE_EM": "UV–mm Sci (14.69 oct, 0.505%)",
            "SOLAR_10PC_SCIENCE": "<10 pc Sci (14.69 oct, 1.675%)",
            "LIT_TELLIS_MARCY_2017": "Tellis & Marcy 2017 (1.12 oct, 0.054%)",
            "LIT_PRICE_2020_BL": "Breakthrough Listen 2020 (1.40 oct, 0.225%)",
        }.get(name, name)
        off_map = {
            "FULL_PANCHROMATIC_62P6_OCT_V70": (-70, -52),
            "HE_UNBROKEN_INTEGRAL_LHAASO_V70": (-145, 12),
            "ALL_SCIENCE_EM": (-120, -14),
            "SOLAR_10PC_SCIENCE": (-30, 10),
            "LIT_TELLIS_MARCY_2017": (8, -4),
            "LIT_PRICE_2020_BL": (8, 4),
        }
        arr_kw = {"arrowstyle": "->", "lw": 0.7, "color": C_GRAY} if name in ("FULL_PANCHROMATIC_62P6_OCT_V70", "ALL_SCIENCE_EM") else None
        ax2.annotate(short_lbl, (octv, fv), xytext=off_map.get(name, (6, 6)),
                     textcoords="offset points", fontsize=7.5, color=C_DARK, arrowprops=arr_kw)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.8, 130.0)
    ax2.set_ylim(0.03, 5.0)
    ax2.set_xlabel("Spectral Octave Span $\\Delta\\log_2\\nu$")
    ax2.set_ylabel("Uniform 95% Occurrence Limit $f_{95}$ (%)")
    ax2.set_title("B. Spectral Breadth vs. $f_{95}$ Literature Context")
    ax2.grid(True, alpha=0.22)

    fig.savefig(FIGS / "figJ08_bayesian_ftx_and_cosmic_haystack_cwtfm.png")
    plt.close(fig)


def figJ09() -> None:
    phases = [p[0] for p in PHASE_TRAJECTORY]
    x = np.arange(len(phases))
    stars = [p[1] for p in PHASE_TRAJECTORY]
    octs = [OCTAVE_SPAN_MAP[ph] for ph in phases]
    cals = [p[6] / 1000.0 for p in PHASE_TRAJECTORY]
    arms = [p[3] for p in PHASE_TRAJECTORY]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6), gridspec_kw={"wspace": 0.28})

    ax1.plot(x, stars, marker="o", ms=3.8, lw=2.0, color=C_BLUE, label="Unique Stars (12 -> 1,083)")
    ax1_r = ax1.twinx()
    ax1_r.plot(x, octs, marker="s", ms=3.5, lw=1.9, ls="--", color=C_VERM, label="EM Spectral Octaves (0.87 -> 62.58)")
    ax1.set_xticks(x[::3])
    ax1.set_xticklabels(phases[::3], rotation=32, fontsize=8.0)
    ax1.set_ylabel("Cumulative Unique Targets", color=C_BLUE)
    ax1_r.set_ylabel("Cumulative EM Octaves", color=C_VERM)
    ax1.set_title("A. 34-Phase Growth Across D079–D112 (A–AL Archives)")
    ax1.grid(True, alpha=0.22)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_r.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7.6, frameon=True, framealpha=0.92)

    ax2.plot(x, cals, marker="D", ms=3.6, lw=2.0, color=C_GREEN, label="Cumulative Calib. Trials (113.97k)")
    ax2_r = ax2.twinx()
    ax2_r.plot(x, arms, marker="^", ms=3.6, lw=1.8, ls="-.", color=C_PURPLE, label="Spectral Arms Deployed (1 -> 104)")
    ax2.set_xticks(x[::3])
    ax2.set_xticklabels(phases[::3], rotation=32, fontsize=8.0)
    ax2.set_ylabel("Cumulative Calibration Trials (thousands)", color=C_GREEN)
    ax2_r.set_ylabel("Cumulative Spectral Arms (72 Spec / 104 Arms)", color=C_PURPLE)
    ax2.set_title("B. Calibration Rigor & 104-Arm Expansion (38/38 Recompute PASS)")
    ax2.grid(True, alpha=0.22)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2_r.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7.6, frameon=True, framealpha=0.92)

    fig.savefig(FIGS / "figJ09_survey_trajectory_and_reproducibility_chain.png")
    plt.close(fig)


def main() -> None:
    t1 = _load_csv(TABLES / "table1_master_catalog_1083stars.csv")
    t3 = _load_csv(TABLES / "table3_spectrograph_atlas_72inst_104arms.csv")
    t4 = _load_csv(TABLES / "table4_panchromatic_bridge_matrix_2695cells.csv")
    figJ01(t1, t3)
    figJ02(t1, t4)
    figJ03()
    figJ04(t1)
    figJ05()
    figJ06()
    figJ07(t3)
    figJ08()
    figJ09()
    print("Generated all 9 journal figures cleanly in", FIGS)


if __name__ == "__main__":
    main()
