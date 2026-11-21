#!/usr/bin/env python3
"""Generate the 6 publication figures (240 DPI) for SETI Phase D096 (V5.4)."""

from __future__ import annotations

import csv
import gzip
import json
import math
import pathlib
import sys
from collections import Counter
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = pathlib.Path(__file__).resolve().parent
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

from analyze import _decode_arr_any, _decode_wave_any
from v5_4_detector import compute_running_continuum, get_inst_config

RES = WS / "results"
FIG_DIR = RES / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
BUNDLE_PATH = WS / "bounded_inputs" / "d096_bounded_bundle.json.gz"

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
    "savefig.dpi": 240,
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm_arm(arm: dict[str, Any], inst: str) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    w_a = _decode_wave_any(arm["wave"])
    w_um = w_a * 1e-4
    fl = _decode_arr_any(arm["flux"])
    at = _decode_arr_any(arm.get("atran"))
    cfg = get_inst_config(inst, float(arm.get("rp", 2700.0)))
    cr, ce = compute_running_continuum(w_a, fl, cfg)
    cont = np.where(cr > 0.0, cr, ce)
    fn = np.where(np.isfinite(fl) & np.isfinite(cont) & (cont > 0.0), fl / cont, np.nan)
    return w_um, fn, at


def _save(fig: plt.Figure, filename: str) -> None:
    out = FIG_DIR / filename
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
    print(f"Saved {out} ({out.stat().st_size} bytes)")


def fig01_panchromatic_425stars(summary: dict[str, Any]) -> None:
    syn = _read_csv("UNIFIED_PANCHROMATIC_V5_4_SYNTHESIS_425STARS.csv")
    br = _read_csv("PANCHROMATIC_BRIDGE_52STARS_V54.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.2, 5.9), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(wspace=0.25)

    # Panel A: Distance vs min panchromatic 10m EIRP
    d_prior, p_prior = [], []
    d_br_re, p_br_re = [], []
    d_d096_inst: dict[str, tuple[list[float], list[float]]] = {}
    inst_palette = {
        "JWST_NIRISS_SOSS": ("JWST NIRISS/SOSS (D096)", "#e7298a", "P", 70),
        "JWST_NIRSPEC_G140H": ("JWST NIRSpec/G140H (D096)", "#7570b3", "s", 58),
        "CARMENES_VIS": ("CARMENES VIS (D096)", "#1b9e77", "^", 62),
        "SOFIA_EXES": ("SOFIA EXES Mid-IR (D096)", "#d95f02", "o", 62),
        "SDSS_APOGEE2": ("SDSS APOGEE-2 N>=14 (D096)", "#a6761d", "v", 60),
    }

    for r in syn:
        dist = float(r["dist_pc"]) if r["dist_pc"] else math.nan
        pkw = float(r["min_panchromatic_10m_kw"]) if r["min_panchromatic_10m_kw"] else math.nan
        if not (math.isfinite(dist) and math.isfinite(pkw) and dist > 0 and pkw > 0):
            continue
        phases = r["phases"]
        insts = r["instruments"]
        if "D096" not in phases:
            d_prior.append(dist)
            p_prior.append(pkw)
        elif ";" in phases:
            d_br_re.append(dist)
            p_br_re.append(pkw)
        else:
            # Brand-new D096 star
            picked = "SOFIA_EXES"
            for ik in inst_palette:
                if ik in insts:
                    picked = ik
                    break
            d_d096_inst.setdefault(picked, ([], []))
            d_d096_inst[picked][0].append(dist)
            d_d096_inst[picked][1].append(pkw)

    ax1.scatter(d_prior, p_prior, s=16, c="#a6bddb", alpha=0.72, edgecolor="none", label="Prior D079–D095 (395 new)", zorder=2)
    ax1.scatter(d_br_re, p_br_re, s=62, c="#6a51a3", marker="D", edgecolor="black", lw=0.6, label="D096 Revisited Bridges (6)", zorder=4)
    for ik, (lbl, col, mk, sz) in inst_palette.items():
        if ik in d_d096_inst:
            xs, ys = d_d096_inst[ik]
            ax1.scatter(xs, ys, s=sz, c=col, marker=mk, edgecolor="black", lw=0.6, label=f"{lbl} ({len(xs)})", zorder=5)

    ax1.axvline(10.0, color="#1b7837", ls="--", lw=1.2, alpha=0.85)
    ax1.text(10.8, 2.0e14, "10 pc Solar\nNeighborhood\n(165 stars)", color="#1b7837", fontsize=8.0, ha="left", va="top")
    med10 = float(summary["unified_425star_panchromatic_v5_4_synthesis"]["within_10pc_median_limit_kw"])
    ax1.axhline(med10, color="#2b8cbe", ls=":", lw=1.25)
    ax1.text(180.0, med10 * 1.45, f"<10 pc Median: {med10:.2f} kW", color="#045a8d", fontsize=8.0, ha="left")

    # Callouts positioned cleanly in low-density areas
    ax1.annotate("SIMP 0136 (6.1 pc)\n39.7 W (SOSS 0.85 µm)", xy=(6.13, 0.039712), xytext=(1.05, 0.0014),
                 fontsize=7.6, fontweight="bold", color="#980043",
                 arrowprops=dict(arrowstyle="->", color="#980043", lw=0.9))
    ax1.annotate("LP 731-58 (114 W)\nCARMENES 0.53 µm", xy=(4.49, 0.114498), xytext=(120.0, 0.0030),
                 fontsize=7.5, color="#006d2c",
                 arrowprops=dict(arrowstyle="->", color="#006d2c", lw=0.85))
    ax1.annotate("Sirius (2.67 pc)\nEXES 202.4 kW (opt 114 W)", xy=(2.67, 0.114), xytext=(1.05, 4500.0),
                 fontsize=7.5, color="#a63603",
                 arrowprops=dict(arrowstyle="->", color="#a63603", lw=0.85))
    ax1.annotate("NGC 1068\n(14.4 Mpc AGN ctrl)", xy=(1.44e7, 6.558e15), xytext=(1.5e4, 2.0e14),
                 fontsize=7.6, color="#555555",
                 arrowprops=dict(arrowstyle="->", color="#555555", lw=0.8))

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.8, 3.0e7)
    ax1.set_ylim(5e-4, 5e16)
    ax1.set_xlabel("Heliocentric Distance (pc)")
    ax1.set_ylabel("Best 10-m Optical/IR Laser Beam EIRP Limit (kW)")
    ax1.set_title("A. 425-Star Panchromatic Distance–EIRP Sensitivity (0 Verified ETI)")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.3, ncol=1)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: 8.709-Octave Panchromatic Bridge SEDs across 52 Bridges (719 cells)
    by_star_br: dict[str, list[tuple[float, float, str]]] = {}
    for r in br:
        by_star_br.setdefault(r["star"], []).append((float(r["wave_um"]), float(r["p_beam_10m_kw"]), r["phase_id"]))

    hi_bridges = {
        "SIRIUS": ("Sirius (UV/Opt/NIR + EXES 7.2 µm)", "#d95f02", "o"),
        "HD62509": ("Pollux / HD 62509 (+ EXES 6.9 µm)", "#e6ab02", "s"),
        "ALFTAU": ("Aldebaran (+ EXES 7.0 µm)", "#a6761d", "^"),
        "ARCTURUS": ("Arcturus (+ EXES 7.7–19 µm)", "#1b9e77", "D"),
        "VHS1256B": ("VHS 1256 b (MIRI + NIRSpec G140H)", "#7570b3", "P"),
    }
    first_bg = True
    for st, pts in by_star_br.items():
        pts_s = sorted(pts, key=lambda x: x[0])
        xs = [p[0] for p in pts_s]
        ys = [p[1] for p in pts_s]
        if st not in hi_bridges:
            ax2.plot(xs, ys, color="#b3cde3", lw=0.8, alpha=0.55, label="47 Prior Calibrated Bridges" if first_bg else None, zorder=2)
            first_bg = False

    for st, (lbl, col, mk) in hi_bridges.items():
        if st in by_star_br:
            pts_s = sorted(by_star_br[st], key=lambda x: x[0])
            ax2.plot([p[0] for p in pts_s], [p[1] for p in pts_s], color=col, marker=mk, ms=4.8, lw=1.6, label=lbl, zorder=5)

    ax2.axvspan(5.6, 26.2, color="#fee0b6", alpha=0.28, label="D096 SOFIA/EXES Band (5.6–26.1 µm)")
    ax2.axvspan(0.68, 2.83, color="#e7d4e8", alpha=0.28, label="D096 JWST SOSS / G140H (0.68–2.83 µm)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.08, 45.0)
    ax2.set_ylim(2e-2, 5e7)
    ax2.set_xlabel("Rest/Barycentric Wavelength (µm) — 8.709 Octaves Total")
    ax2.set_ylabel("10-m Beam EIRP Limit (kW)")
    ax2.set_title("B. 52 Calibrated Bridges (719 Cells; +BD+60 1753 = 53 Multi-Phase)")
    ax2.legend(loc="upper left", frameon=True, fontsize=7.2)
    ax2.grid(True, which="both", alpha=0.20)

    fig.suptitle("Phase D096 (V5.4): Unified 425-Star Panchromatic Search Across 27 Spectrographs & 8.709 Octaves", y=0.99)
    _save(fig, "fig01_d096_panchromatic_425stars_8p71octaves.png")


def fig02_sofia_exes_midir(summary: dict[str, Any], bundle: dict[str, Any]) -> None:
    exes_rows = _read_csv("SOFIA_EXES_MIDIR_ECHELLE_17STARS.csv")
    cal_exes = _read_csv("CALIBRATION_V54_SOFIA_EXES_180.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.4, 10.2))
    fig.subplots_adjust(wspace=0.36, hspace=0.34)

    exes_exps = {e["star"]: e for e in bundle["exposures"] if e["instrument"] == "SOFIA_EXES"}

    # Panel A: SIRIUS SOFIA/EXES real order + ATRAN
    e_sir = exes_exps["SIRIUS"]
    arm_s = e_sir["arms"][min(4, len(e_sir["arms"]) - 1)]
    ws, fns, ats = _norm_arm(arm_s, "SOFIA_EXES")
    ms = np.isfinite(fns)
    ax1.plot(ws[ms], fns[ms], color="#2b8cbe", lw=0.95, label="Sirius EXES Normalized Flux")
    if ats is not None:
        ax1_t = ax1.twinx()
        ax1_t.plot(ws[ms], ats[ms], color="#d95f02", lw=0.85, ls="--", alpha=0.8, label="ATRAN Telluric Trans.")
        ax1_t.set_ylim(0.0, 1.15)
        ax1_t.set_ylabel("ATRAN Transmission", color="#d95f02")
        ax1_t.tick_params(axis="y", colors="#d95f02")
    ax1.axhline(1.0, color="#555555", lw=0.8, ls=":")
    ax1.set_ylim(0.55, 1.45)
    ax1.set_xlabel("SOFIA/EXES Vacuum Wavelength (µm)")
    ax1.set_ylabel("Continuum-Normalized Flux")
    ax1.set_title(f"A. Sirius (α CMa, 2.67 pc) EXES Order #{arm_s.get('order', 5)} (R = 93,246)")
    ax1.legend(loc="lower left", frameon=True, fontsize=8.0)
    ax1.grid(alpha=0.22)

    # Panel B: HR 7957 (or Betelgeuse) interior EXES G45 PSF veto example (avoiding steep order-edge rollover)
    e_hr = exes_exps["HR7957"]
    best_pk, wb, fnb = 0.0, np.empty(0), np.empty(0)
    for arm in e_hr["arms"]:
        wu, fn, _ = _norm_arm(arm, "SOFIA_EXES")
        pad = max(10, len(wu) // 10)
        if len(wu) <= 2 * pad:
            continue
        wu_i, fn_i = wu[pad:-pad], fn[pad:-pad]
        fin = fn_i[np.isfinite(fn_i)]
        if len(fin) and float(np.max(fin)) > best_pk:
            best_pk = float(np.max(fin)); wb = wu_i; fnb = fn_i
    mb = np.isfinite(fnb)
    ax2.plot(wb[mb], fnb[mb], color="#7570b3", lw=1.0, label="η Cep (HR 7957) EXES 5.64 µm Order")
    ipk = int(np.nanargmax(np.where(mb, fnb, -1.0)))
    pk_val = float(fnb[ipk])
    x_txt = wb[ipk + max(8, len(wb) // 6)] if ipk < len(wb) // 2 else wb[max(0, ipk - len(wb) // 3)]
    ax2.annotate(f"Narrow spike ({pk_val:.2f}x)\nvetoed by G45 PSF",
                 xy=(wb[ipk], pk_val), xytext=(x_txt, pk_val * 0.96),
                 fontsize=7.8, arrowprops=dict(arrowstyle="->", color="#b30000", lw=0.9), color="#b30000")
    ax2.axhline(1.0, color="#555555", lw=0.8, ls=":")
    ax2.set_ylim(max(0.4, float(np.nanpercentile(fnb[mb], 1)) * 0.88), pk_val * 1.15)
    ax2.set_xlabel("SOFIA/EXES Vacuum Wavelength (µm)")
    ax2.set_ylabel("Continuum-Normalized Flux")
    ax2.set_title("B. η Cep EXES Order: 24 Narrow G1 Spikes Vetoed by G45 Native PSF")
    ax2.legend(loc="lower right", frameon=True, fontsize=8.0)
    ax2.grid(alpha=0.22)

    # Panel C: Calibration 180 + Gate Funnel
    n_las = sum(1 for r in cal_exes if r["class"] == "CLEAN_LASER" and r["passed"] == "1")
    n_atr = sum(1 for r in cal_exes if r["class"] == "ATRAN_ARTIFACT" and r["passed"] == "1")
    n_cr = sum(1 for r in cal_exes if r["class"] == "COSMIC_RAY_1PX" and r["passed"] == "1")
    n_nat = sum(1 for r in cal_exes if r["class"] == "NATURAL_ATLAS_LINE" and r["passed"] == "1")
    suites = [
        (f"Cal: Laser Rec. ({n_las}/60)", n_las / 60.0 * 100.0, "#1b9e77"),
        (f"Cal: ATRAN Veto ({n_atr}/40)", n_atr / 40.0 * 100.0, "#2b8cbe"),
        (f"Cal: Cosmic-Ray Veto ({n_cr}/40)", n_cr / 40.0 * 100.0, "#2b8cbe"),
        (f"Cal: Natural Line Veto ({n_nat}/40)", n_nat / 40.0 * 100.0, "#2b8cbe"),
        ("Sky G1->G2 Pass (149/149)", 100.0, "#7570b3"),
        ("Sky G45 Reject (148/149)", 148.0 / 149.0 * 100.0, "#d95f02"),
        ("Sky G6 Qualified (0/149)", 0.0, "#e34a33"),
    ]
    ylbls = [s[0] for s in suites][::-1]
    vals = [s[1] for s in suites][::-1]
    cols = [s[2] for s in suites][::-1]
    y_pos = np.arange(len(ylbls))
    bars = ax3.barh(y_pos, vals, color=cols, edgecolor="black", lw=0.6)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(ylbls, fontsize=8.3)
    ax3.set_xlim(0, 118)
    for b, v in zip(bars, vals):
        ax3.text(v + 1.8, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=8.0, fontweight="bold")
    ax3.set_xlabel("Percentage (%)")
    ax3.set_title("C. SOFIA/EXES 180-Trial Calibration & 348-Order Gate Funnel")
    ax3.grid(axis="x", alpha=0.22)

    # Panel D: 17-star EIRP Limits sorted
    ex_s = sorted(exes_rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    names = [f"{r['star']} ({r['best_band'].replace('EXES_', '')})" for r in ex_s]
    pvals = [float(r["best_p_beam_10m_kw"]) for r in ex_s]
    bcols = ["#636363" if r["role"] == "CONTROL" else ("#1b9e77" if r["panchromatic_bridge"] == "True" else "#d95f02") for r in ex_s]
    yp = np.arange(len(names))
    ax4.barh(yp, pvals, color=bcols, edgecolor="black", lw=0.55)
    ax4.set_xscale("log")
    ax4.set_yticks(yp)
    ax4.set_yticklabels(names, fontsize=7.6)
    ax4.set_xlim(50, 1e18)
    ax4.set_xlabel("8-σ 10-m Mid-IR Laser Beam EIRP Limit (kW)")
    ax4.set_title("D. 17 SOFIA/EXES Targets: 348 Orders Scanned -> 0 Qualified ETI")
    ax4.grid(axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D096 Stream 1: SOFIA/EXES High-Resolution Mid-IR Echelon-Echelle Search (5.6–26.1 µm)", y=0.99)
    _save(fig, "fig02_d096_sofia_exes_midir_echelle_17stars.png")


def fig03_coherent_shift_stack(summary: dict[str, Any]) -> None:
    cal = _read_csv("CALIBRATION_V54_COHERENT_SHIFT_STACK_240.csv")
    camps = _read_csv("DRIFT_V54_COHERENT_SHIFT_STACK_20CAMPAIGNS.csv")
    cands = _read_csv("DRIFT_V54_COHERENT_CANDIDATE_LEDGER.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.4, 10.2))
    fig.subplots_adjust(wspace=0.34, hspace=0.36)

    # Panel A: 240-trial calibration
    cls_defs = [
        ("SUBTHRESH_CURVED", "Curved Recovery", "#1b9e77"),
        ("SUBTHRESH_PERIODIC", "Periodic Recovery", "#2b8cbe"),
        ("STATIONARY_VETO", "Stationary Veto", "#7570b3"),
        ("TRANSIENT_VETO", "1-Epoch Transient Veto", "#d95f02"),
        ("BERV_SKY_VETO", "BERV Sky Veto", "#e7298a"),
    ]
    xl, yv, cl = [], [], []
    for key, lbl, col in cls_defs:
        sub = [r for r in cal if r["class"] == key]
        n_p = sum(1 for r in sub if r["passed"] == "1")
        xl.append(f"{lbl}\n({n_p}/{len(sub)})")
        yv.append(100.0 * n_p / max(1, len(sub)))
        cl.append(col)
    xp = np.arange(len(xl))
    bars = ax1.bar(xp, yv, color=cl, edgecolor="black", lw=0.6)
    ax1.set_xticks(xp)
    ax1.set_xticklabels(xl, rotation=12, ha="right", fontsize=8.0)
    ax1.set_ylim(0, 115)
    for b, v in zip(bars, yv):
        ax1.text(b.get_x() + b.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", fontsize=8.2, fontweight="bold")
    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_title("A. DRIFT_V54 Synthetic Calibration Suite (240 Trials)")
    ax1.grid(axis="y", alpha=0.22)

    # Panel B: 20 N>=4 Campaigns trajectory-pixel integrals
    cs = sorted(camps, key=lambda r: int(r["n_pixel_trajectory_integrals"]))
    c_names = [f"{r['star']} ({r['n_epochs']}ep)" for r in cs]
    c_int = [int(r["n_pixel_trajectory_integrals"]) for r in cs]
    c_raw = [int(r["raw_coherent_survivors"]) for r in cs]
    c_cols = ["#1b9e77" if r["phase_source"] == "D096" else ("#7570b3" if "D095" in r["phase_source"] else "#d95f02") for r in cs]
    yc = np.arange(len(cs))
    ax2.barh(yc, c_int, color=c_cols, edgecolor="black", lw=0.5)
    ax2.set_xscale("log")
    ax2.set_xlim(5e5, 8e8)
    ax2.set_yticks(yc)
    ax2.set_yticklabels(c_names, fontsize=7.5)
    for i, (val, rc) in enumerate(zip(c_int, c_raw)):
        ax2.text(val * 1.15, i, f"raw={rc}->0 ETI", va="center", fontsize=7.2)
    ax2.set_xlabel("Pixel-Trajectory Integrals Evaluated (Log Scale)")
    ax2.set_title("B. 20 N>=4 Campaigns (6 D096 + 9 D095 U + 5 D094 T = 203.8M Int.)")
    ax2.grid(axis="x", which="both", alpha=0.22)

    # Panel C: Stage-2 Forensic Breakdown of 765 raw CSS hits
    cnt = Counter(r["stage2_triage_status"] for r in cands)
    veto_map = [
        ("STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH", f"Sub-Photospheric Trough ({cnt['STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH']})", "#80b1d3"),
        ("STAGE2_VETO_SPURIOUS_EPOCH_SUBSET", f"Spurious Epoch Subset ({cnt['STAGE2_VETO_SPURIOUS_EPOCH_SUBSET']})", "#fdb462"),
        ("STAGE2_VETO_OH_SKY_OR_TELLURIC", f"OH Sky / CO2 Telluric Hop ({cnt['STAGE2_VETO_OH_SKY_OR_TELLURIC']})", "#fb8072"),
        ("STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND", f"Stationary / Abs. Band ({cnt['STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND']})", "#bebada"),
        ("STAGE2_VETO_NON_LSF_SHAPE", f"Non-LSF Stack Shape ({cnt['STAGE2_VETO_NON_LSF_SHAPE']})", "#b3de69"),
    ]
    vlbl = [x[1] for x in veto_map][::-1]
    vcnt = [cnt[x[0]] for x in veto_map][::-1]
    vcol = [x[2] for x in veto_map][::-1]
    yv3 = np.arange(len(vlbl))
    b3 = ax3.barh(yv3, vcnt, color=vcol, edgecolor="black", lw=0.6)
    ax3.set_xscale("log")
    ax3.set_xlim(1, 2000)
    ax3.set_yticks(yv3)
    ax3.set_yticklabels(vlbl, fontsize=8.3)
    for b, cval in zip(b3, vcnt):
        ax3.text(cval * 1.18, b.get_y() + b.get_height() / 2, f"{cval} / 765", va="center", fontsize=8.0, fontweight="bold")
    ax3.set_xlabel("Candidate Count (Log Scale) — 0/765 Verified ETI")
    ax3.set_title("C. Stage-2 Physical Triage of 765 NaN-Safe Shift-Stack Survivors")
    ax3.grid(axis="x", which="both", alpha=0.22)

    # Panel D: Topocentric CO2 telluric invariance on 2M17012756 across BERV -26..+29 km/s
    ep_labels = ["ep0\n(BERV +1.2)", "ep1\n(BERV -20.5)", "ep2\n(BERV +29.3)", "ep3\n(BERV -26.0)"]
    rest_peaks = [15785.00, 15783.80, 15778.16, 15774.61]
    topo_peaks = [15783.52, 15783.47, 15775.20, 15774.56]
    ye = np.arange(len(ep_labels))
    ax4.scatter(rest_peaks, ye, s=75, c="#d95f02", marker="o", edgecolor="black", label="Apparent Stellar-Rest Shift (linear v_dot)", zorder=4)
    ax4.scatter(topo_peaks, ye, s=75, c="#1b9e77", marker="s", edgecolor="black", label="True Topocentric Frame (Fixed Earth CO2)", zorder=5)
    ax4.plot(rest_peaks, ye, color="#d95f02", lw=1.3, ls="--", alpha=0.8)
    for xco2 in (15775.0, 15779.3, 15783.5):
        ax4.axvline(xco2, color="#1b9e77", lw=1.0, ls=":", alpha=0.65)
    ax4.text(15775.4, 0.15, "Fixed Telluric\nCO2 R-ladder\n(trep=4/4 veto)", color="#006d2c", fontsize=7.8)
    ax4.set_yticks(ye)
    ax4.set_yticklabels(ep_labels, fontsize=8.2)
    ax4.set_xlim(15771.5, 15787.0)
    ax4.set_ylim(-0.5, 4.15)
    ax4.set_xlabel("Vacuum Wavelength (Å)")
    ax4.set_title("D. 2M1701-2756 (Control): Topocentric Telluric CO2 Hopping Explained")
    ax4.legend(loc="upper right", frameon=True, fontsize=7.4)
    ax4.grid(alpha=0.22)

    fig.suptitle("Phase D096 Stream 3: Coherent Multi-Epoch Shift-Stack Search Across 20 N >= 4 APOGEE-2 & CARMENES Campaigns", y=0.99)
    _save(fig, "fig03_d096_coherent_shift_stack_drift_v54.png")


def fig04_jwst_soss_g140h(summary: dict[str, Any], bundle: dict[str, Any]) -> None:
    cal_j = _read_csv("CALIBRATION_V54_JWST_SOSS_G140H_120.csv")
    led = _read_csv("V5_4_CANDIDATE_LEDGER.csv")
    jwst_exps = {e["star"]: e for e in bundle["exposures"] if "JWST" in e["instrument"]}

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.46, hspace=0.35)

    # Panel A: SIMP 0136 NIRISS/SOSS Order 1
    e_simp = jwst_exps["SIMP0136"]
    arm1 = e_simp["arms"][0]
    w1, fn1, _ = _norm_arm(arm1, "JWST_NIRISS_SOSS")
    m1 = np.isfinite(fn1) & (w1 >= 0.70) & (w1 <= 2.82)
    ax1.plot(w1[m1], np.clip(fn1[m1], 0.0, 2.5), color="#e7298a", lw=0.75, label="SIMP 0136 SOSS Order 1 (6.13 pc)")
    for wj in (0.7367, 2.1356):
        ax1.axvline(wj, color="#980043", ls=":", lw=1.0, alpha=0.8)
    ax1.text(0.86, 1.85, "SOSS 0.85 µm\nBest Limit: 39.7 W", color="#980043", fontsize=8.0, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.25", fc="#fff5f9", ec="#e7298a"))
    ax1.text(2.15, 2.05, "J2: Order 1/2/3\nCross-Order\n(r >= 0.997)", color="#b30000", fontsize=7.6)
    ax1.set_xlim(0.70, 2.85)
    ax1.set_ylim(0.1, 2.55)
    ax1.set_xlabel("JWST NIRISS/SOSS Wavelength (µm)")
    ax1.set_ylabel("Normalized Flux F / C")
    ax1.set_title("A. SIMP J0136+0933 (T2.5 Brown Dwarf): Deepest Optical/IR Limit (39.7 W)")
    ax1.legend(loc="lower right", frameon=True, fontsize=8.0)
    ax1.grid(alpha=0.22)

    # Panel B: VHS 1256 b + BD601753 NIRSpec/G140H
    e_vhs = jwst_exps["VHS1256B"]
    wv, fv, _ = _norm_arm(e_vhs["arms"][0], "JWST_NIRSPEC_G140H")
    mv = np.isfinite(fv)
    ax2.plot(wv[mv], np.clip(fv[mv], 0.0, 2.2), color="#7570b3", lw=0.7, label="VHS 1256 b NIRSpec/G140H (12.7 pc)")
    ax2.axvspan(1.440, 1.465, color="#fdb462", alpha=0.45, label="J3: NRS1–NRS2 Detector Gap Edge")
    ax2.axvline(1.16305, color="#b30000", ls="--", lw=1.0, label="J4: Unflagged CR Spike (err_rat=17.5)")
    ax2.axvline(1.064, color="#1b7837", ls=":", lw=1.1, label="1.064 µm Nd:YAG Band (34.5 kW)")
    ax2.set_xlim(0.95, 1.88)
    ax2.set_ylim(0.0, 2.25)
    ax2.set_xlabel("JWST NIRSpec/G140H Wavelength (µm)")
    ax2.set_ylabel("Normalized Flux F / C")
    ax2.set_title("B. VHS J1256-1257 b (G140H): 34.5 kW Limit & J3/J4 Detector Artifact Vetoes")
    ax2.legend(loc="lower left", frameon=True, fontsize=7.5)
    ax2.grid(alpha=0.22)

    # Panel C: Calibration 120
    n_sl = sum(1 for r in cal_j if r["class"] == "SPACE_LASER" and r["passed"] == "1")
    n_hp = sum(1 for r in cal_j if r["class"] == "HOT_PIXEL_1PX" and r["passed"] == "1")
    n_br = sum(1 for r in cal_j if r["class"] == "BROAD_OR_HI_VETO" and r["passed"] == "1")
    c_defs = [
        ("SPACE_LASER", f"Synthetic Laser Rec.\n({n_sl}/60)", "#1b9e77", 60, n_sl),
        ("HOT_PIXEL_1PX", f"Hot-Pixel / CR Veto\n({n_hp}/30)", "#d95f02", 30, n_hp),
        ("BROAD_OR_HI_VETO", f"Broad Molecular Veto\n({n_br}/30)", "#2b8cbe", 30, n_br),
    ]
    cx = np.arange(len(c_defs))
    cy = [100.0 * nv / d for _, _, _, d, nv in c_defs]
    b_c = ax3.bar(cx, cy, color=[x[2] for x in c_defs], edgecolor="black", lw=0.6, width=0.52)
    ax3.set_xticks(cx)
    ax3.set_xticklabels([x[1] for x in c_defs], fontsize=8.2)
    ax3.set_ylim(0, 115)
    for b, v in zip(b_c, cy):
        ax3.text(b.get_x() + b.get_width() / 2, v + 2.0, f"{v:.1f}%", ha="center", fontsize=8.5, fontweight="bold")
    ax3.set_ylabel("Pass Rate (%)")
    ax3.set_title("C. JWST NIRISS/SOSS & NIRSpec/G140H Calibration (120 Trials)")
    ax3.grid(axis="y", alpha=0.22)

    # Panel D: J1-J5 Stage-2 Veto Breakdown across 19 Raw Survivors
    jcnt = Counter(r["stage2_triage_status"] for r in led)
    j_defs = [
        ("STAGE2_VETO_JWST_FIXED_SLIT_UNDERSAMPLING_WIGGLE", "J5: Fixed-Slit Wiggle\n(BD601753, HD54306)"),
        ("STAGE2_VETO_JWST_SOSS_CROSS_ORDER_CONTAMINANT", "J2: SOSS Cross-Order\n(SIMP0136)"),
        ("STAGE2_VETO_JWST_DETECTOR_GAP_EDGE", "J3: NRS1–NRS2 Gap\n(VHS1256B)"),
        ("STAGE2_VETO_JWST_UNFLAGGED_CR_ERROR_SPIKE", "J4: Unflagged CR Spike\n(VHS1256B)"),
        ("STAGE2_VETO_JWST_NEGATIVE_CONTINUUM", "J1: Neg. Continuum\n(HD59533)"),
    ]
    jlbl = [x[1] for x in j_defs][::-1]
    jval = [jcnt[x[0]] for x in j_defs][::-1]
    jcol = ["#e7298a", "#fb8072", "#fdb462", "#80b1d3", "#bebada"]
    yj = np.arange(len(jlbl))
    bj = ax4.barh(yj, jval, color=jcol, edgecolor="black", lw=0.6)
    ax4.set_yticks(yj)
    ax4.set_yticklabels(jlbl, fontsize=8.0)
    ax4.set_xlim(0, 17.5)
    for b, v in zip(bj, jval):
        ax4.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v} / 19 -> 0 ETI", va="center", fontsize=8.0, fontweight="bold")
    ax4.set_xlabel("Stage-1 Raw Survivors Rejected by Stage-2 J1–J5 Physics")
    ax4.set_title("D. 19 Raw JWST Stage-1 Candidates -> 100% Explained, 0 Verified ETI")
    ax4.grid(axis="x", alpha=0.22)

    fig.suptitle("Phase D096 Stream 4: JWST NIRISS/SOSS & NIRSpec/G140H Search (13 Control + 6 Science Hits -> 0 ETI)", y=0.99)
    _save(fig, "fig04_d096_jwst_niriss_soss_g140h_triage.png")


def fig05_carmenes_apogee2_orbits_comb() -> None:
    fg = _read_csv("FOUR_GEN_BENCHMARK_D096.csv")
    v51 = _read_csv("BLIND_DRIFT_V51_RESULTS_D096.csv")
    v52 = _read_csv("MULTIEPOCH_DRIFT_V52_RESULTS_D096.csv")
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_5.csv")
    cmb = _read_csv("ALLSKY_COMB_V4_1_UNIFIED_D079_D096.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.6, 10.2))
    fig.subplots_adjust(wspace=0.46, hspace=0.35)

    # Panel A: 4-Gen Gate Funnel
    gates = ["g1_lsf", "g2_airglow", "g3_chromo", "g45_native_psf", "g6_topo", "v50_g7_rpca", "v54_g8_final", "stage2_verified_eti"]
    glbls = ["G1", "G2+OH", "G3", "G4/G5", "G6", "G7", "G8", "ETI"]
    gx = np.arange(len(gates))
    w_bar = 0.36
    row_c = [r for r in fg if r["instrument"] == "CARMENES_VIS"][0]
    row_a = [r for r in fg if r["instrument"] == "SDSS_APOGEE2"][0]
    vc = [max(0.4, int(row_c[g])) for g in gates]
    va = [max(0.4, int(row_a[g])) for g in gates]
    b1 = ax1.bar(gx - w_bar / 2, vc, width=w_bar, color="#1b9e77", edgecolor="black", lw=0.6, label="CARMENES VIS (3 stars)")
    b2 = ax1.bar(gx + w_bar / 2, va, width=w_bar, color="#d95f02", edgecolor="black", lw=0.6, label="SDSS APOGEE-2 (4 stars)")
    ax1.set_yscale("log")
    ax1.set_ylim(0.3, 600)
    ax1.set_xticks(gx)
    ax1.set_xticklabels(glbls, fontsize=8.3)
    for b, raw_v in zip(b1, [int(row_c[g]) for g in gates]):
        ax1.text(b.get_x() + b.get_width() / 2, max(0.45, raw_v) * 1.15, str(raw_v), ha="center", fontsize=7.5, fontweight="bold")
    for b, raw_v in zip(b2, [int(row_a[g]) for g in gates]):
        ax1.text(b.get_x() + b.get_width() / 2, max(0.45, raw_v) * 1.15, str(raw_v), ha="center", fontsize=7.5, fontweight="bold")
    ax1.set_ylabel("Surviving Peaks (Log Scale; 0 plotted at 0.4 floor)")
    ax1.set_title("A. Four-Generation Cascade Funnel (SERVAL RV + Full Ch-P Gating -> 0 ETI)")
    ax1.legend(loc="upper right", frameon=True, fontsize=8.0)
    ax1.grid(axis="y", which="both", alpha=0.22)

    # Panel B: Blind Drift V51 & V52 Stage-1 Raw -> Stage-2 0
    stars_d = [r["star"] for r in v51]
    raw51 = [int(r["raw_survivors"]) for r in v51]
    v52_map = {r["star"]: int(r["raw_survivors"]) for r in v52}
    raw52 = [v52_map.get(s, 0) for s in stars_d]
    xd = np.arange(len(stars_d))
    ax2.bar(xd - 0.18, raw51, width=0.35, color="#e7298a", edgecolor="black", lw=0.5, label="V51 Raw Pairs (17 -> 0 via Airglow/Telluric)")
    ax2.bar(xd + 0.18, raw52, width=0.35, color="#7570b3", edgecolor="black", lw=0.5, label="V52 Linear Raw (17 -> 0 via F1/LSF)")
    ax2.set_xticks(xd)
    ax2.set_xticklabels(stars_d, rotation=20, ha="right", fontsize=8.0)
    ax2.set_ylim(0, 15.5)
    for i, (r51, r52) in enumerate(zip(raw51, raw52)):
        ax2.text(i - 0.18, r51 + 0.25, str(r51), ha="center", fontsize=7.5)
        ax2.text(i + 0.18, r52 + 0.25, str(r52), ha="center", fontsize=7.5)
    ax2.set_ylabel("Raw Stage-1 Drift Hits (Verified ETI = 0)")
    ax2.set_title("B. BLIND_DRIFT_V51 (20.7M Evals) & DRIFT_V52 Triage -> 0 Survivors")
    ax2.legend(loc="upper right", frameon=True, fontsize=7.6)
    ax2.grid(axis="y", alpha=0.22)

    # Panel C: Orbital Campaigns #134-#138
    o_per = [float(r["orb_per_days"]) for r in orb]
    o_dv = [float(r["orbital_dv_span_kms"]) for r in orb]
    o_col = ["#1b9e77" if r["instrument"] == "CARMENES_VIS" else "#d95f02" for r in orb]
    ax3.scatter(o_per, o_dv, s=95, c=o_col, edgecolor="black", lw=0.7, zorder=4)
    orb_layout = {
        "138": ((14, 10), "left", "bottom"),
        "137": ((8, -46), "left", "top"),
        "136": ((20, -4), "left", "center"),
        "134": ((-6, 16), "center", "bottom"),
        "135": ((6, -24), "center", "top"),
    }
    for r in orb:
        off, ha_v, va_v = orb_layout.get(str(r["campaign_index"]), ((8, 0), "left", "center"))
        ax3.annotate(f"#{r['campaign_index']} {r['planet_name']}\n(K_p={float(r['kp_kms']):.1f} km/s, 0 ETI)",
                     xy=(float(r["orb_per_days"]), float(r["orbital_dv_span_kms"])),
                     xytext=off, textcoords="offset points", ha=ha_v, va=va_v, fontsize=7.4,
                     arrowprops=dict(arrowstyle="-", lw=0.7, color="#555555"))
    ax3.set_xscale("log")
    ax3.set_xlim(2.0, 150.0)
    ax3.set_ylim(30.0, 335.0)
    ax3.set_xlabel("Known Exoplanet Orbital Period (days)")
    ax3.set_ylabel("Peak-to-Peak Planet Doppler Span (km/s)")
    ax3.set_title("C. Orbital Campaigns #134–#138 (138 Cumulative; 81/81 K_PLANET Cal)")
    ax3.grid(True, which="both", alpha=0.22)

    # Panel D: Unified 448-Stack All-Sky Comb D079-D096
    by_ph = Counter(r["phase_id"] for r in cmb)
    phs = sorted(by_ph.keys())
    counts = [by_ph[p] for p in phs]
    cols_ph = ["#d95f02" if p == "D096" else "#2b8cbe" for p in phs]
    xp4 = np.arange(len(phs))
    ax4.bar(xp4, counts, color=cols_ph, edgecolor="black", lw=0.45)
    ax4.set_ylim(0, max(counts) * 1.30)
    ax4.set_xticks(xp4[::2])
    ax4.set_xticklabels(phs[::2], rotation=35, ha="right", fontsize=7.2)
    ax4.set_ylabel("Comb Stacks Evaluated (0 Verified ETI Comb)")
    ax4.set_title(f"D. Unified All-Sky Comb Search: {len(cmb)} Stacks D079–D096 (HNLIB 85->0)")
    ax4.text(0.03, 0.80, "Total Stacks: 448 (441 prior + 7 D096)\nD096 Configs Scanned: 846,168\nVerified ETI Combs: 0",
             transform=ax4.transAxes, fontsize=8.0, bbox=dict(boxstyle="round,pad=0.3", fc="#f7fbff", ec="#2b8cbe"))
    ax4.grid(axis="y", alpha=0.22)

    fig.suptitle("Phase D096 Stream 2: CARMENES VIS & APOGEE-2 Four-Gen Funnel, V51/V52 Drift, Campaigns #134–#138, & 448 Comb Stacks", y=0.99)
    _save(fig, "fig05_d096_carmenes_apogee2_orbits_and_comb.png")


def fig06_ellipsoid_425_calibration(summary: dict[str, Any]) -> None:
    ell = _read_csv("MULTIEVENT_ELLIPSOID_425STARS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.6, 6.0), gridspec_kw={"width_ratios": [1.02, 1.0]})
    fig.subplots_adjust(wspace=0.52)

    # Panel A: Ellipsoid |ecliptic_lat| vs min_abs_ellipsoid_dt_days
    bg_x, bg_y, d96_x, d96_y, etz_x, etz_y = [], [], [], [], [], []
    for r in ell:
        lat = abs(float(r["ecliptic_lat_deg"])) if r["ecliptic_lat_deg"] else math.nan
        dt = float(r["min_abs_ellipsoid_dt_days"]) if r["min_abs_ellipsoid_dt_days"] else math.nan
        if not (math.isfinite(lat) and math.isfinite(dt)):
            continue
        dt_plot = max(0.05, dt)
        if r["etz_qualified"] == "True":
            etz_x.append(lat); etz_y.append(dt_plot)
        elif "D096" in r["phases"]:
            d96_x.append(lat); d96_y.append(dt_plot)
        else:
            bg_x.append(lat); bg_y.append(dt_plot)

    ax1.axhspan(0.03, 180.0, color="#e5f5e0", alpha=0.55, label="<= 180 d Ellipsoid Window (36 stars)")
    ax1.axvspan(-1.5, 2.0, color="#deebf7", alpha=0.60, label="|β| <= 2° ETZ Strip (15 stars)")
    ax1.scatter(bg_x, bg_y, s=16, c="#9ecae1", edgecolor="none", label="Prior D079–D095", zorder=2)
    ax1.scatter(d96_x, d96_y, s=46, c="#d95f02", marker="o", edgecolor="black", lw=0.5, label="D096 Targets", zorder=4)
    ax1.scatter(etz_x, etz_y, s=68, c="#1b7837", marker="*", edgecolor="black", lw=0.55, label="ETZ Qualified (15)", zorder=5)
    ax1.axhline(180.0, color="#1b7837", ls="--", lw=1.1)
    ax1.axvline(2.0, color="#2b8cbe", ls="--", lw=1.1)
    ax1.set_yscale("log")
    ax1.set_xlim(-3.0, 91.0)
    ax1.set_ylim(0.04, 3e5)
    ax1.set_xlabel("|Ecliptic Latitude β| (deg)")
    ax1.set_ylabel("min |Δt| to SN 1987A / GW170817 / SN 2023ixf Ellipsoid (days)")
    ax1.set_title("A. Multi-Event SETI Ellipsoid Across All 425 Stars (15 ETZ, 36 <= 180 d)")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.6)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: 1,851-Trial Calibration Summary
    cal_suites = [
        ("SOFIA_EXES Laser (59/60)", 59 / 60 * 100, "#1b9e77"),
        ("SOFIA_EXES Confounders (120/120)", 100.0, "#1b9e77"),
        ("COHERENT_SS Curved/Per (111/120)", 111 / 120 * 100, "#2b8cbe"),
        ("COHERENT_SS Vetoes (120/120)", 100.0, "#2b8cbe"),
        ("JWST SOSS/G140H Laser (57/60)", 57 / 60 * 100, "#7570b3"),
        ("JWST HotPx+Broad Veto (60/60)", 100.0, "#7570b3"),
        ("G8 PCA-kNN Novelty (118/120)", 118 / 120 * 100, "#d95f02"),
        ("RPCA Rarity Score (179/180)", 179 / 180 * 100, "#d95f02"),
        ("Agnostic Multi-Scale (120/120)", 100.0, "#a6761d"),
        ("G4/G5 Native PSF (108/108)", 100.0, "#a6761d"),
        ("Channel P Injection (537/540)", 537 / 540 * 100, "#e7298a"),
        ("COMB V4.1 Synth (162/162)", 100.0, "#66a61e"),
        ("Keplerian K_PLANET (81/81)", 100.0, "#66a61e"),
    ]
    yl = [c[0] for c in cal_suites][::-1]
    vv = [c[1] for c in cal_suites][::-1]
    cc = [c[2] for c in cal_suites][::-1]
    yp2 = np.arange(len(yl))
    b2 = ax2.barh(yp2, vv, color=cc, edgecolor="black", lw=0.55)
    ax2.set_yticks(yp2)
    ax2.set_yticklabels(yl, fontsize=7.9)
    ax2.set_xlim(75.0, 108.0)
    for b, v in zip(b2, vv):
        ax2.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=7.8, fontweight="bold")
    ax2.axvline(95.0, color="#555555", ls=":", lw=1.0)
    ax2.set_xlabel("Suite Pass / Specificity Rate (%)")
    ax2.set_title("B. D096 1,851-Trial Calibration (37,911 Cumulative D079–D096 Trials)")
    ax2.grid(axis="x", alpha=0.22)

    fig.suptitle("Phase D096 (V5.4): 425-Star Multi-Event SETI Ellipsoid & 1,851-Trial Synthetic Validation", y=0.99)
    _save(fig, "fig06_d096_multievent_ellipsoid_425stars_cal.png")


def main() -> None:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    bundle = json.loads(gzip.decompress(BUNDLE_PATH.read_bytes()).decode("utf-8"))
    fig01_panchromatic_425stars(summary)
    fig02_sofia_exes_midir(summary, bundle)
    fig03_coherent_shift_stack(summary)
    fig04_jwst_soss_g140h(summary, bundle)
    fig05_carmenes_apogee2_orbits_comb()
    fig06_ellipsoid_425_calibration(summary)
    print("ALL 6 D096 FIGURES GENERATED CLEANLY.")


if __name__ == "__main__":
    main()
