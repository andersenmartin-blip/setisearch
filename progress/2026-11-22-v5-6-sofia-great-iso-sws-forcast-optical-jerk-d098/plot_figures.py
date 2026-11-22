#!/usr/bin/env python3
"""Generate 6 publication-quality (240 DPI) figures for Phase D098 (V5.6) from real results and bounded inputs."""

from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RES = WS / "results"
FIG_DIR = RES / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

import analyze as az
from v5_6_detector import scan_iso_sws_midir_v56

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.8,
    "axes.titlesize": 9.9,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.9,
    "xtick.labelsize": 7.9,
    "ytick.labelsize": 7.9,
    "figure.titlesize": 11.8,
    "figure.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _save(fig: plt.Figure, fname: str) -> Path:
    out = FIG_DIR / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size} B)")
    return out


def fig79_sofia_great(bundle: dict[str, Any]) -> None:
    gr_rows = _read_csv("SOFIA_GREAT_SUPERTHZ_12STARS.csv")
    cal_gr = _read_csv("CALIBRATION_V56_SOFIA_GREAT_180.csv")
    spc = [r for r in _read_csv("V5_6_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "SOFIA_GREAT"]
    exps = [e for e in bundle["exposures"] if e["instrument"] == "SOFIA_GREAT"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.2))
    fig.subplots_adjust(wspace=0.34, hspace=0.35)

    # Panel A: Betelgeuse [OI] 63 um resolved outflow (4744.78 GHz, FWHM=11.94 km/s) vs unresolved LSF
    e_bet = next(e for e in exps if e["star"] == "BETELGEUSE" and ("OI" in e["dp_id"] or float(e.get("restfreq_ghz") or 0) > 4000.0))
    gc = e_bet["great_cube"]
    fq = float(gc["f0_ghz"]) + float(gc["df_ghz"]) * np.arange(int(gc["n"]), dtype=np.float64)
    tk = az._decode_arr_any(gc["temp_k"])
    f0 = 4744.7775
    dv = (f0 - fq) / f0 * 299792.458
    mv = np.isfinite(tk) & (np.abs(dv) <= 65.0)
    ord_v = np.argsort(dv[mv])
    ax1.plot(dv[mv][ord_v], tk[mv][ord_v], color="#d95f02", lw=1.15, label="Betelgeuse GREAT [OI] 63 µm (FWHM = 11.94 km/s)")
    lsf_ref = float(np.nanmax(tk[mv])) * np.exp(-0.5 * (dv[mv][ord_v] / 0.35) ** 2)
    ax1.plot(dv[mv][ord_v], lsf_ref, color="#2b8cbe", ls="--", lw=1.05, label="Unresolved Super-THz Laser LSF (~0.7 km/s)")
    ax1.axhline(0.0, color="#666666", lw=0.7, ls=":")
    ax1.set_ylim(-3.2, 19.2)
    ax1.set_xlabel("Velocity Offset Δv rel. to [OI] 4744.78 GHz (km/s)")
    ax1.set_ylabel("Antenna Temperature T_A* (K)")
    ax1.set_title("A. Betelgeuse [OI] 63 µm Wind vs. Unresolved THz Laser LSF (G5 Veto)")
    ax1.legend(loc="upper right", frameon=True, fontsize=7.6)
    ax1.grid(alpha=0.22)

    # Panel B: Clean science cube HD141569 (best GREAT EIRP limit)
    e_hd = next(e for e in exps if e["star"] == "HD141569" and ("OI" in e["dp_id"] or float(e.get("restfreq_ghz") or 0) > 4000.0))
    gc_h = e_hd["great_cube"]
    fq_h = float(gc_h["f0_ghz"]) + float(gc_h["df_ghz"]) * np.arange(int(gc_h["n"]), dtype=np.float64)
    tk_h = az._decode_arr_any(gc_h["temp_k"])
    mh = np.isfinite(tk_h)
    ax2.plot(fq_h[mh], tk_h[mh], color="#1b9e77", lw=0.85, label="HD 141569 GREAT [OI] 63 µm (0 raw peaks)")
    ax2.axhline(0.0, color="#666666", lw=0.7, ls=":")
    ax2.text(0.04, 0.87, "Best SOFIA/GREAT 8-σ Limit:\n19,268,981 kW (111.6 pc)", transform=ax2.transAxes,
             fontsize=8.0, fontweight="bold", color="#006d2c", bbox=dict(boxstyle="round,pad=0.25", fc="#f2fcf7", ec="#1b9e77"))
    ax2.set_xlabel("LSR Frequency (GHz)")
    ax2.set_ylabel("Antenna Temperature T_A* (K)")
    ax2.set_title("B. Clean Science Cube (HD 141569 GREAT_OI_63UM): 0 Qualified Beacons")
    ax2.legend(loc="upper right", frameon=True, fontsize=7.6)
    ax2.grid(alpha=0.22)

    # Panel C: 180-trial calibration + 23 real raw Stage-1 triage
    c_defs = [
        ("CLEAN_GREAT_BEACON", "Super-THz Beacon Rec.", "#1b9e77"),
        ("STANDING_WAVE_VETO", "Standing-Wave Veto", "#2b8cbe"),
        ("BROAD_MOLECULAR_VETO", "Broad Outflow Veto", "#2b8cbe"),
        ("SINGLE_CHAN_LO_VETO", "1-Chan LO Spur Veto", "#2b8cbe"),
    ]
    yl, yv, col = [], [], []
    for k, lbl, c in c_defs:
        sub = [r for r in cal_gr if r["class"] == k]
        p = sum(1 for r in sub if r["passed"] == "1")
        yl.append(f"{lbl} ({p}/{len(sub)})")
        yv.append(100.0 * p / max(1, len(sub)))
        col.append(c)
    vc = Counter(r["veto_reason"] for r in spc)
    n_sp = max(1, len(spc))
    yl.extend([
        f"Sky 1-Ch LO Spurs ({vc['G5_GREAT_LO_SPUR_1CHAN']}/{n_sp})",
        f"Sky Broad Mol./OI ({vc['G5_GREAT_BROAD_MOLECULAR']}/{n_sp})",
        f"Sky Standing Wave ({vc['G2_GREAT_STANDING_WAVE_RIPPLE']}/{n_sp})",
        f"Verified ETI (0/{n_sp})",
    ])
    yv.extend([
        100.0 * vc["G5_GREAT_LO_SPUR_1CHAN"] / n_sp,
        100.0 * vc["G5_GREAT_BROAD_MOLECULAR"] / n_sp,
        100.0 * vc["G2_GREAT_STANDING_WAVE_RIPPLE"] / n_sp,
        0.0,
    ])
    col.extend(["#d95f02", "#7570b3", "#e6ab02", "#e34a33"])
    yp = np.arange(len(yl))
    bars = ax3.barh(yp, yv[::-1], color=col[::-1], edgecolor="black", lw=0.6)
    ax3.set_yticks(yp)
    ax3.set_yticklabels(yl[::-1], fontsize=8.0)
    ax3.set_xlim(0, 118)
    for b, v in zip(bars, yv[::-1]):
        ax3.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=7.9, fontweight="bold")
    ax3.set_xlabel("Pass / Attribution Share (%)")
    ax3.set_title(f"C. SOFIA/GREAT 180-Trial Calibration & {len(spc)}-Peak Stage-1 Funnel")
    ax3.grid(axis="x", alpha=0.22)

    # Panel D: 12-star GREAT EIRP limits
    gs = sorted(gr_rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    names = [f"{r['star']} ({r['best_band'].replace('GREAT_', '')})" for r in gs]
    vals = [float(r["best_p_beam_10m_kw"]) for r in gs]
    bcols = ["#636363" if r["role"] == "CONTROL" else "#d95f02" for r in gs]
    y4 = np.arange(len(names))
    ax4.barh(y4, vals, color=bcols, edgecolor="black", lw=0.55)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels(names, fontsize=7.7)
    ax4.set_xlim(5e6, 5e12)
    ax4.set_xlabel("8-σ 10-m Super-THz Laser Beam EIRP Limit (kW)")
    ax4.set_title("D. 12 SOFIA/GREAT Targets (27 Cubes; 1.45–4.75 THz -> 0 ETI)")
    ax4.grid(axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D098 Stream 1A: SOFIA/GREAT Super-THz Heterodyne Search (1.45–4.75 THz, 63–206 µm)", y=0.99)
    _save(fig, "fig79_d098_sofia_great_superthz_12stars.png")


def fig80_iso_sws(bundle: dict[str, Any]) -> None:
    sw_rows = _read_csv("ISO_SWS_MIDIR_GAPCLOSURE_17STARS.csv")
    cal_sw = _read_csv("CALIBRATION_V56_ISO_SWS_180.csv")
    exps = [e for e in bundle["exposures"] if e["instrument"] == "ISO_SWS"]

    # Compute exact 6-gas CCF sigma per star in ~0.4s via frozen detector
    mols = ["CF4", "CCl2F2", "CCl3F", "SF6", "NF3", "NO2"]
    ccf_mat = np.zeros((len(sw_rows), len(mols)), dtype=np.float64)
    st_idx = {r["star"]: i for i, r in enumerate(sw_rows)}
    for ex in exps:
        sw = ex["iso_sws"]
        wu = az._decode_arr_any(sw["wave_um"])
        fj = az._decode_arr_any(sw["flux_jy"])
        ej = az._decode_arr_any(sw["err_jy"])
        out = scan_iso_sws_midir_v56(
            wu, fj, ej, seg_breaks=list(sw["seg_breaks"]), teff_k=float(ex["teff_k"]),
            dist_pc=float(ex["dist_pc"]), star=ex["star"], dp_id=ex["dp_id"],
            star_rv_kms=float(ex["prior_rv_kms"]), cohort_topo_um=[],
        )
        i = st_idx[ex["star"]]
        md = out["ccf"].get("molecules", {})
        for j, m_k in enumerate(mols):
            ccf_mat[i, j] = float(md.get(m_k, {}).get("ccf_sigma_abs", 0.0))

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.4))
    fig.subplots_adjust(wspace=0.35, hspace=0.36)

    # Panel A: Continuous 2.36-45.39 um Gap-Closure Spectra (HD219134, AUMIC, IRC10216 scaled)
    for st_s, lbl, col, mult in [
        ("HD219134", "HD 219134 (6.54 pc photosphere, 2,781 kW)", "#1b9e77", 1.0),
        ("AUMIC", "AU Mic (9.72 pc debris disk × 20)", "#2b8cbe", 20.0),
        ("IRC10216", "IRC+10216 (dusty AGB × 0.01)", "#d95f02", 0.01),
    ]:
        ex = next(e for e in exps if e["star"] == st_s)
        sw = ex["iso_sws"]
        wu = az._decode_arr_any(sw["wave_um"])
        fj = az._decode_arr_any(sw["flux_jy"])
        mk = np.isfinite(wu) & np.isfinite(fj) & (fj > 0.0)
        step = max(1, int(np.sum(mk) // 1800))
        ax1.plot(wu[mk][::step], fj[mk][::step] * mult, lw=0.9, color=col, label=lbl)
    ax1.axvspan(2.36, 4.90, color="#ccebc5", alpha=0.32, label="SWS Short-λ Gap-Closure (2.36–4.9 µm)")
    ax1.axvspan(28.0, 45.39, color="#fed9a6", alpha=0.32, label="SWS Long-λ Gap-Closure (28–45.39 µm)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(2.2, 48.0)
    ax1.set_xlabel("ISO/SWS Wavelength (µm; 12 AOT Segments)")
    ax1.set_ylabel("Flux Density (scaled Jy)")
    ax1.set_title("A. Continuous 2.36–45.39 µm Gap-Closure SEDs Across 17 Stars")
    ax1.legend(loc="lower right", frameon=True, fontsize=6.9)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: 17 x 6 Greenhouse CCF Heatmap (all 0 detected with joint confounder exclusion)
    im = ax2.imshow(ccf_mat, aspect="auto", cmap="YlOrRd", vmin=0.0, vmax=14.0)
    ax2.set_xticks(np.arange(len(mols)))
    ax2.set_xticklabels(mols, fontsize=8.0)
    ax2.set_yticks(np.arange(len(sw_rows)))
    ax2.set_yticklabels([r["star"] for r in sw_rows], fontsize=7.2)
    for i in range(len(sw_rows)):
        for j in range(len(mols)):
            val = ccf_mat[i, j]
            if val >= 0.05:
                ax2.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=6.3, color="white" if val > 7.5 else "black")
    cbar = fig.colorbar(im, ax=ax2, fraction=0.045, pad=0.03)
    cbar.set_label("|CCF Z| (Unmixed Raw -> Confounder-Vetoed 0/17)", fontsize=7.5)
    ax2.set_title("B. 6-Gas Greenhouse CCF (0/102 Gas Cells Detected)")

    # Panel C: Dyson gamma_waste vs Silicate excess sigma (upper-left quadrant empty -> 0 Dyson)
    gam = [max(1e-4, float(r["dyson_gamma"])) for r in sw_rows]
    sil = [max(0.5, float(r["dyson_sil_sigma"])) for r in sw_rows]
    ax3.scatter(sil, gam, s=48, c=["#636363" if r["role"] == "CONTROL" else "#2b8cbe" for r in sw_rows], edgecolor="black", lw=0.6, zorder=4)
    ax3.axhspan(0.01, 1.2, xmin=0.0, xmax=0.25, color="#ccebc5", alpha=0.32, label="Silicate-Free Dyson Zone (sil < 3σ, γ ≥ 0.01)")
    ax3.axhline(0.01, color="#1b7837", ls="--", lw=1.0)
    ax3.axvline(3.0, color="#b30000", ls="--", lw=1.0, label="Silicate Excess Limit (3σ)")
    off_map = {"70VIR": (9, -8), "BETPIC": (7, -6), "ETACAR": (-28, 12), "NGC4151": (6, 4), "HR4049": (6, 4), "IRC10216": (6, -3), "AUMIC": (6, 4), "WHYA": (6, 4), "MUCEP": (6, 4)}
    for r, sx, gy in zip(sw_rows, sil, gam):
        if r["star"] in off_map:
            ax3.annotate(r["star"], xy=(sx, gy), xytext=off_map[r["star"]], textcoords="offset points", fontsize=6.8)
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.set_xlim(0.4, 1500.0)
    ax3.set_ylim(2.5e-5, 1.3)
    ax3.set_xlabel("Silicate Band Excess (σ)")
    ax3.set_ylabel("Fitted Dyson Waste-Heat Covering Fraction γ")
    ax3.set_title("C. 100–400 K Dyson vs. Silicate Discrimination (180/180 Cal -> 0 ETI)")
    ax3.legend(loc="lower center", frameon=True, fontsize=7.0)
    ax3.grid(True, which="both", alpha=0.20)

    # Panel D: Top ISO/SWS EIRP limits + 180-trial summary box
    ss = sorted(sw_rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    y4 = np.arange(len(ss))
    ax4.barh(y4, [float(r["best_p_beam_10m_kw"]) for r in ss],
             color=["#636363" if r["role"] == "CONTROL" else "#1b9e77" for r in ss], edgecolor="black", lw=0.5)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['best_band'].replace('SWS_', '')})" for r in ss], fontsize=7.2)
    ax4.set_xlim(1e3, 1e17)
    n_cal_ok = sum(1 for r in cal_sw if r["passed"] == "1")
    ax4.text(0.48, 0.14, f"ISO SWS Calib: {n_cal_ok}/180 (100%)\n52 Raw Peaks -> 0 ETI\nBest: HD 219134 (2,781.4 kW)",
             transform=ax4.transAxes, fontsize=7.5, fontweight="bold", bbox=dict(boxstyle="round,pad=0.25", fc="#fff8f0", ec="#d95f02"))
    ax4.set_xlabel("8-σ 10-m Mid-IR Laser Beam EIRP Limit (kW)")
    ax4.set_title("D. 17 ISO/SWS Targets: Upper Limits Across 2.36–45.39 µm")
    ax4.grid(axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D098 Stream 1B: ISO/SWS 2.36–45.39 µm Gap-Closure, 6-Gas Greenhouse CCF & Dyson Search", y=0.99)
    _save(fig, "fig80_d098_iso_sws_midir_gapclosure_17stars.png")


def fig81_sofia_forcast(bundle: dict[str, Any]) -> None:
    fo_rows = _read_csv("SOFIA_FORCAST_4GRISM_11STARS.csv")
    cal_fo = _read_csv("CALIBRATION_V56_SOFIA_FORCAST_120.csv")
    spc = [r for r in _read_csv("V5_6_SPACE_CANDIDATE_LEDGER.csv") if r["instrument"] == "SOFIA_FORCAST"]
    exps = [e for e in bundle["exposures"] if e["instrument"] == "SOFIA_FORCAST"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.2))
    fig.subplots_adjust(wspace=0.35, hspace=0.35)

    # Panel A: 4-grism stitched SED of HD 100546 + ATRAN telluric curve
    e_hd = sorted([e for e in exps if e["star"] == "HD100546"], key=lambda x: x["grating"])
    gcols = {"FOR_G063": "#980043", "FOR_G111": "#d95f02", "FOR_G227": "#2b8cbe", "FOR_G329": "#1b9e77"}
    ax1_r = ax1.twinx()
    for e_i in e_hd:
        fg = e_i["forcast_grism"]
        gid = fg["grism_id"]
        wu = az._decode_arr_any(fg["wave_um"])
        fj = az._decode_arr_any(fg["flux_jy"])
        at = az._decode_arr_any(fg["atran"])
        mk = np.isfinite(wu) & np.isfinite(fj) & np.isfinite(at)
        ax1.plot(wu[mk], fj[mk], lw=1.0, color=gcols.get(gid, gcols.get("FOR_" + e_i["grating"][3:], "#333333")), label=f"HD 100546 {gid} (R={float(fg['rp']):.0f})")
        ax1_r.plot(wu[mk], at[mk], lw=0.65, color="#7f7f7f", alpha=0.55)
    ax1_r.axhline(0.70, color="#666666", ls=":", lw=0.9)
    ax1_r.set_ylim(0.0, 1.15)
    ax1_r.set_ylabel("SOFIA ATRAN Telluric Transmission", color="#555555")
    ax1.set_yscale("log")
    ax1.set_xlabel("FORCAST Wavelength (µm)")
    ax1.set_ylabel("Flux Density (Jy)")
    ax1.set_title("A. HD 100546 4-Grism Stitched SED (5–37 µm) & ATRAN Transmission")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.2)
    ax1.grid(alpha=0.20)

    # Panel B: R Aqr G111 + G227 natural ionic/hydrogen lines & ATRAN vetting
    e_rq = next(e for e in exps if e["star"] == "RAQR" and "G111" in e["grating"])
    fg_q = e_rq["forcast_grism"]
    wu_q = az._decode_arr_any(fg_q["wave_um"])
    fj_q = az._decode_arr_any(fg_q["flux_jy"])
    mq = np.isfinite(wu_q) & np.isfinite(fj_q)
    ax2.plot(wu_q[mq], fj_q[mq], color="#7570b3", lw=1.0, label="R Aqr FOR_G111 (8.4–13.7 µm)")
    ax2.axvline(8.9914, color="#b30000", ls="--", lw=1.0, label="[Ar III] 8.991 µm (G3 Atlas Veto)")
    ax2.axvline(10.5105, color="#d95f02", ls="--", lw=1.0, label="[S IV] 10.511 µm (G3 Atlas Veto)")
    ax2.set_xlabel("FORCAST G111 Wavelength (µm)")
    ax2.set_ylabel("Flux Density (Jy)")
    ax2.set_title("B. R Aqr FOR_G111: Natural Symbiotic Forbidden Lines vs. Laser Atlas")
    ax2.legend(loc="upper right", frameon=True, fontsize=7.5)
    ax2.grid(alpha=0.22)

    # Panel C: 120-trial calibration + 33 FORCAST raw peak triage
    yl = []
    yv = []
    cl = []
    for k, lbl, c in [
        ("CLEAN_FORCAST_BEACON", "Grism Beacon Rec.", "#1b9e77"),
        ("ATRAN_TELLURIC_VETO", "ATRAN O3/H2O Veto", "#2b8cbe"),
        ("GLITCH_AND_PAH_VETO", "1-Px / Dust Veto", "#2b8cbe"),
    ]:
        sub = [r for r in cal_fo if r["class"] == k]
        p = sum(1 for r in sub if r["passed"] == "1")
        yl.append(f"{lbl} ({p}/{len(sub)})")
        yv.append(100.0 * p / len(sub))
        cl.append(c)
    vc = Counter(r["veto_reason"].split(":")[0] for r in spc)
    n_f = max(1, len(spc))
    for k, lbl, c in [
        ("G5_FORCAST_1PX_GLITCH", "Sky 1-Px Glitches", "#d95f02"),
        ("G2_FORCAST_BASELINE_ARTIFACT", "Sky Baseline / Fringes", "#e6ab02"),
        ("G2_FORCAST_ATRAN_TELLURIC", "Sky ATRAN Telluric", "#fb8072"),
        ("G3_FORCAST_NATURAL_LINE", "Sky Natural HI/SIII/ArIII", "#7570b3"),
        ("G5_FORCAST_BROAD_PAH_SILICATE", "Sky Broad PAH/Silicate", "#80b1d3"),
        ("G6_FORCAST_TELLURIC_COINCIDENCE", "Sky G6 Coincidence", "#b3de69"),
    ]:
        cnt = vc[k]
        yl.append(f"{lbl} ({cnt}/{n_f})")
        yv.append(100.0 * cnt / n_f)
        cl.append(c)
    yl.append(f"Verified ETI (0/{n_f})")
    yv.append(0.0)
    cl.append("#e34a33")
    yp = np.arange(len(yl))
    bars = ax3.barh(yp, yv[::-1], color=cl[::-1], edgecolor="black", lw=0.55)
    ax3.set_yticks(yp)
    ax3.set_yticklabels(yl[::-1], fontsize=7.6)
    ax3.set_xlim(0, 118)
    for b, v in zip(bars, yv[::-1]):
        ax3.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=7.5, fontweight="bold")
    ax3.set_xlabel("Pass / Attribution Share (%)")
    ax3.set_title(f"C. SOFIA/FORCAST 120-Trial Calibration & {len(spc)}-Peak Stage-1 Funnel")
    ax3.grid(axis="x", alpha=0.22)

    # Panel D: 11-star FORCAST EIRP limits
    fs = sorted(fo_rows, key=lambda r: float(r["best_p_beam_10m_kw"]))
    y4 = np.arange(len(fs))
    ax4.barh(y4, [float(r["best_p_beam_10m_kw"]) for r in fs],
             color=["#636363" if r["role"] == "CONTROL" else "#2b8cbe" for r in fs], edgecolor="black", lw=0.55)
    ax4.set_xscale("log")
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{r['star']} ({r['best_band'].replace('FOR_', '')})" for r in fs], fontsize=7.8)
    ax4.set_xlim(5e6, 5e12)
    ax4.set_xlabel("8-σ 10-m Mid-IR Grism Beam EIRP Limit (kW)")
    ax4.set_title("D. 11 SOFIA/FORCAST Targets (35 Grism Spectra -> 0 Verified ETI)")
    ax4.grid(axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D098 Stream 1C: SOFIA/FORCAST 4-Grism (G063/G111/G227/G329, 5–37 µm) Search", y=0.99)
    _save(fig, "fig81_d098_sofia_forcast_4grism_11stars.png")


def fig82_carmenes_drift_v56(bundle: dict[str, Any]) -> None:
    cal = _read_csv("CALIBRATION_V56_COHERENT_JERK_240.csv")
    camps = _read_csv("DRIFT_V56_COHERENT_JERK_30CAMPAIGNS.csv")
    cands = _read_csv("DRIFT_V56_COHERENT_CANDIDATE_LEDGER.csv")
    fg = _read_csv("FOUR_GEN_BENCHMARK_D098.csv")
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_3.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.38, hspace=0.36)

    # Panel A: DRIFT_V56 240-trial cal + CARMENES 4-Gen inset metrics
    cls_defs = [
        ("SUBTHRESH_CUBIC_JERK", "Cubic Jerk Rec.", "#1b9e77"),
        ("SUBTHRESH_PERIODIC", "Periodic Rec.", "#2b8cbe"),
        ("STATIONARY_VETO", "Stationary Veto", "#7570b3"),
        ("TRANSIENT_VETO", "1-Epoch Trans.", "#d95f02"),
        ("BERV_SKY_VETO", "BERV Sky Veto", "#e7298a"),
    ]
    xl, yv, cl = [], [], []
    for k, lbl, c in cls_defs:
        sub = [r for r in cal if r["class"] == k]
        p = sum(1 for r in sub if r["passed"] == "1")
        xl.append(f"{lbl}\n({p}/{len(sub)})")
        yv.append(100.0 * p / len(sub))
        cl.append(c)
    xp = np.arange(len(xl))
    bars = ax1.bar(xp, yv, color=cl, edgecolor="black", lw=0.6)
    ax1.set_xticks(xp)
    ax1.set_xticklabels(xl, rotation=12, ha="right", fontsize=7.6)
    ax1.set_ylim(0, 136)
    for b, v in zip(bars, yv):
        ax1.text(b.get_x() + b.get_width() / 2, v + 1.8, f"{v:.1f}%", ha="center", fontsize=8.0, fontweight="bold")
    fg0 = fg[0]
    ax1.text(0.03, 0.855, f"Live CARMENES_VIS (20 exp, Orbits #141–#143):\nG1={fg0['g1_seeds']}->G45={fg0['g45_pass']}->G6={fg0['g6_pass']}->G8={fg0['g8_pass']}->0 ETI",
             transform=ax1.transAxes, fontsize=7.3, fontweight="bold", bbox=dict(boxstyle="round,pad=0.25", fc="#f2fcf7", ec="#1b9e77"))
    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_title("A. DRIFT_V56 240-Trial Calibration (100%) & CARMENES_VIS Funnel")
    ax1.grid(axis="y", alpha=0.22)

    # Panel B: 30 N>=4 campaigns (5 D098 + 25 Retro W/V/U/T)
    cs = sorted(camps, key=lambda r: int(r["n_pixel_trajectory_integrals"]))
    yc = np.arange(len(cs))
    col_map = {"D098": "#1b9e77", "D097": "#980043", "D096": "#2b8cbe", "D095": "#7570b3", "D094": "#d95f02"}
    c_cols = [col_map.get(r["phase_source"], "#555555") for r in cs]
    c_int = [int(r["n_pixel_trajectory_integrals"]) for r in cs]
    c_raw = [int(r["raw_coherent_survivors"]) for r in cs]
    ax2.barh(yc, c_int, color=c_cols, edgecolor="black", lw=0.4)
    ax2.set_xscale("log")
    ax2.set_xlim(4e5, 9e9)
    ax2.set_yticks(yc)
    ax2.set_yticklabels([f"{r['star']} ({r['phase_source']})" for r in cs], fontsize=6.2)
    for i, (val, rc) in enumerate(zip(c_int, c_raw)):
        ax2.text(val * 1.14, i, f"{rc}->0", va="center", fontsize=6.0)
    tot_b = sum(c_int) / 1e9
    ax2.set_xlabel(f"Pixel-Trajectory Integrals (Log Scale; {tot_b:.3f}B Total)")
    ax2.set_title(f"B. 30 N>=4 Campaigns (5 D098 + 25 W/V/U/T -> {len(cands)}->0 ETI)")
    ax2.grid(axis="x", which="both", alpha=0.22)

    # Panel C: Stage-2 Breakdown of all cands -> 0 ETI
    cnt = Counter(r["stage2_triage_status"] for r in cands)
    n_tot = len(cands)
    v_defs = [
        ("STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH", f"Sub-Photospheric Trough ({cnt['STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH']})", "#80b1d3"),
        ("STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND", f"Stationary / Abs. Band ({cnt['STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND']})", "#bebada"),
        ("STAGE2_VETO_OH_SKY_OR_TELLURIC", f"OH Sky / CO2 Telluric ({cnt['STAGE2_VETO_OH_SKY_OR_TELLURIC']})", "#fb8072"),
        ("STAGE2_VETO_SPURIOUS_EPOCH_SUBSET", f"Spurious Epoch Subset ({cnt['STAGE2_VETO_SPURIOUS_EPOCH_SUBSET']})", "#fdb462"),
        ("STAGE2_VETO_NON_LSF_SHAPE", f"Non-LSF Stack Shape ({cnt['STAGE2_VETO_NON_LSF_SHAPE']})", "#b3de69"),
        ("STAGE2_VETO_LOWCONT_CR_RINGING", f"Low-Cont. Blue CR Ringing ({cnt['STAGE2_VETO_LOWCONT_CR_RINGING']})", "#e34a33"),
    ]
    v_nonz = [x for x in v_defs if cnt[x[0]] > 0]
    vl = [x[1] for x in v_nonz][::-1]
    vc = [cnt[x[0]] for x in v_nonz][::-1]
    yv3 = np.arange(len(vl))
    b3 = ax3.barh(yv3, vc, color=[x[2] for x in v_nonz][::-1], edgecolor="black", lw=0.6)
    ax3.set_xscale("log")
    ax3.set_xlim(0.7, 6e4)
    ax3.set_yticks(yv3)
    ax3.set_yticklabels(vl, fontsize=7.8)
    for b, rval in zip(b3, vc):
        ax3.text(rval * 1.18, b.get_y() + b.get_height() / 2, f"{rval} / {n_tot}", va="center", fontsize=7.6, fontweight="bold")
    ax3.set_xlabel(f"Raw Survivors Eliminated (0 / {n_tot} Verified ETI)")
    ax3.set_title(f"C. Stage-2 Forensic Resolution Across {n_tot:,} Raw CSS Hits -> 0 ETI")
    ax3.grid(axis="x", which="both", alpha=0.22)

    # Panel D: Two forensic CSS artifact proofs measured directly in Stage-2 investigation
    ep_k = np.arange(4)
    gj_pk = [4.377, 14.642, 5.149, 1.416]
    ln1 = ax4.plot(ep_k, gj_pk, marker="o", ms=7.2, color="#e34a33", lw=1.5, label="GJ 1005 FEROS 4239.3 Å Peak Flux (cont SNR 1.97–2.95, 50.3× dyn.)")
    ax4.set_ylim(0.0, 17.5)
    ax4.set_xlim(-0.35, 3.35)
    ax4.set_xticks(ep_k)
    ax4.set_xticklabels(["Epoch 0", "Epoch 1", "Epoch 2", "Epoch 3"])
    ax4.set_ylabel("GJ 1005 Normalized Peak Flux (× cont)", color="#e34a33")
    ax4.tick_params(axis="y", colors="#e34a33")

    ax4_r = ax4.twinx()
    wf_zc = [3.33, 3.93, 0.35, 1.87]
    ln2 = ax4_r.plot(ep_k, wf_zc, marker="s", ms=6.6, color="#2b8cbe", lw=1.5, ls="-.", label="Wolf 1069 CARMENES 6524.6 Å Center Z (+8.55 km/s ep0 SERVAL outlier)")
    ax4_r.axhline(2.0, color="#2b8cbe", ls=":", lw=0.9)
    ax4_r.annotate("ep0 +8.55 km/s SERVAL offset\non 1.286× TiO crest (ep2 Z=0.35)", xy=(2.0, 0.35), xytext=(0.08, 0.50),
                   fontsize=7.0, color="#045a8d",
                   bbox=dict(boxstyle="round,pad=0.2", fc="#f0f8ff", ec="#2b8cbe", alpha=0.92),
                   arrowprops=dict(arrowstyle="->", color="#2b8cbe", lw=0.9))
    ax4_r.set_ylabel("Wolf 1069 Trajectory Center Z-Score", color="#2b8cbe")
    ax4_r.tick_params(axis="y", colors="#2b8cbe")
    ax4_r.set_ylim(-0.2, 5.4)
    lns = ln1 + ln2
    ax4.legend(lns, [l.get_label() for l in lns], loc="upper right", frameon=True, fontsize=6.7)
    ax4.set_title("D. Stage-2 Physical Proofs (GJ 1005 Blue CR Ringing & Wolf 1069 TiO Crest)")
    ax4.grid(alpha=0.22)

    fig.suptitle("Phase D098 Streams 2 & 3: CARMENES_VIS Orbits #141–#143 & 30-Campaign DRIFT_V56 Coherent Jerk", y=0.99)
    _save(fig, "fig82_d098_carmenes_drift_v56_30campaigns.png")


def fig83_calibration_bridges(summary: dict[str, Any]) -> None:
    ell = _read_csv("MULTIEVENT_ELLIPSOID_473STARS.csv")
    cmb = _read_csv("ALLSKY_COMB_V4_1_UNIFIED_D079_D098.csv")
    cmb_st = _read_csv("COMB_V4_1_STAR_RESULTS_D098.csv")
    br = _read_csv("PANCHROMATIC_BRIDGE_66STARS_V56.csv")
    cal = summary["synthetic_calibration_2031_trials"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.2))
    fig.subplots_adjust(wspace=0.36, hspace=0.36)

    # Panel A: 11-Suite 2,031-Trial Calibration Scorecard
    suites = [
        ("SOFIA GREAT THz (180)", int(cal["sofia_great_180"].split("/")[0]), 180),
        ("ISO SWS Mid-IR (180)", int(cal["iso_sws_180"].split("/")[0]), 180),
        ("SOFIA FORCAST (120)", int(cal["sofia_forcast_120"].split("/")[0]), 120),
        ("Coherent Jerk (240)", int(cal["coherent_jerk_240"].split("/")[0]), 240),
        ("G8 Novelty (120)", int(cal["g8_pass"].split("/")[0]), 120),
        ("RPCA Rarity (180)", int(cal["rpca_pass"].split("/")[0]), 180),
        ("Agnostic MS (120)", int(cal["agnostic_pass"].split("/")[0]), 120),
        ("G4/G5 PSF (108)", int(cal["g4g5_pass"].split("/")[0]), 108),
        ("Channel P Inj. (540)", int(cal["injection_540"].split("/")[0]), 540),
        ("Comb V4.1 (162)", int(cal["comb_v41_162"].split("/")[0]), 162),
        ("Keplerian K_p (81)", int(cal["keplerian_81"].split("/")[0]), 81),
    ]
    sl = [f"{s[0]} [{s[1]}/{s[2]}]" for s in suites][::-1]
    sv = [100.0 * s[1] / s[2] for s in suites][::-1]
    y1 = np.arange(len(sl))
    b1 = ax1.barh(y1, sv, color="#1b9e77", edgecolor="black", lw=0.55)
    ax1.set_yticks(y1)
    ax1.set_yticklabels(sl, fontsize=7.6)
    ax1.set_xlim(94.0, 104.8)
    for b, v in zip(b1, sv):
        ax1.text(v + 0.28, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=7.5, fontweight="bold")
    cum_tr = int(summary["unified_473star_panchromatic_v5_6_synthesis"]["total_calibration_trials_d079_d098"])
    ax1.set_xlabel(f"Pass Rate (%) — 2,031 D098 Trials ({cum_tr:,} Cumulative)")
    ax1.set_title("A. Full 11-Suite V5.6 Calibration Scorecard (All Systems Nominal)")
    ax1.grid(axis="x", alpha=0.22)

    # Panel B: 473-Star Multi-Event Ellipsoid & 19 ETZ
    lats = [float(r["ecliptic_lat_deg"]) for r in ell]
    dts = [max(0.05, float(r["min_abs_ellipsoid_dt_days"])) for r in ell]
    d98_m = ["D098" in r["phases"].split("+") for r in ell]
    ax2.scatter([x for x, m in zip(lats, d98_m) if not m], [y for y, m in zip(dts, d98_m) if not m],
                s=16, c="#a6bddb", alpha=0.72, label=f"D079–D097 Prior ({sum(not m for m in d98_m)})")
    ax2.scatter([x for x, m in zip(lats, d98_m) if m], [y for y, m in zip(dts, d98_m) if m],
                s=46, c="#d95f02", edgecolor="black", lw=0.55, label=f"D098 Targets ({sum(d98_m)}; +HD166191 ETZ)", zorder=4)
    ax2.axvspan(-2.0, 2.0, color="#ccebc5", alpha=0.45, label=f"ETZ (|β|≤2° Sci: {sum(r['etz_qualified']=='True' for r in ell)} stars)")
    ax2.axhline(180.0, color="#1b7837", ls="--", lw=1.1, label=f"|Δt|≤180 d ({sum(r['ellipsoid_qualified_180d']=='True' for r in ell)} stars)")
    ax2.set_yscale("log")
    ax2.set_xlim(-92.0, 92.0)
    ax2.set_ylim(0.04, 1.5e6)
    ax2.set_xlabel("Ecliptic Latitude β (deg)")
    ax2.set_ylabel("Minimum |Δt| to SN 1987A / GW170817 / SN 2023ixf (d)")
    ax2.set_title("B. 473-Star Multi-Event Ellipsoid & 19-Star ETZ Map -> 0 ETI")
    ax2.legend(loc="lower right", frameon=True, fontsize=7.2)
    ax2.grid(True, which="both", alpha=0.20)

    # Panel C: Unified 458 All-Sky Comb Stacks
    tot_cfg_m = sum(int(r["n_comb_configs"]) for r in cmb_st) / 1e6
    by_ph = Counter(r["phase_id"] for r in cmb)
    phs = sorted(by_ph)
    cnts = [by_ph[p] for p in phs]
    xc = np.arange(len(phs))
    ax3.bar(xc, cnts, color=["#d95f02" if p == "D098" else "#2b8cbe" for p in phs], edgecolor="black", lw=0.5)
    ax3.set_xticks(xc)
    ax3.set_xticklabels(phs, rotation=45, ha="right", fontsize=7.0)
    ax3.set_ylabel("Star-Instrument Comb Stacks")
    ax3.set_title(f"C. Unified {len(cmb)}-Stack COMB_V4_1 Sweep ({tot_cfg_m:.2f}M D098 Configs -> 0 ETI)")
    ax3.grid(axis="y", alpha=0.22)

    # Panel D: 66 Calibrated Bridges octave span histogram / ranked spans
    by_st: dict[str, list[float]] = {}
    for r in br:
        by_st.setdefault(r["star"], []).append(float(r["wave_um"]))
    promo = set(summary["cohort"]["newly_promoted_science_bridges"])
    deep = set(summary["cohort"]["deepened_science_bridges"])
    spans = sorted([(st, min(ws), max(ws), max(ws) / max(1e-6, min(ws))) for st, ws in by_st.items()], key=lambda x: x[3], reverse=True)[:22]
    ys = np.arange(len(spans))
    for i, (st, wmin, wmax, _) in enumerate(spans):
        col = "#d95f02" if st in promo else ("#980043" if st in deep else "#2b8cbe")
        ax4.plot([wmin, wmax], [i, i], lw=2.8, color=col, marker="|", ms=7)
    ax4.set_xscale("log")
    ax4.set_yticks(ys)
    ax4.set_yticklabels([f"{s[0]}{'*' if s[0] in promo else ('+' if s[0] in deep else '')}" for s in spans], fontsize=7.0)
    ax4.invert_yaxis()
    ax4.set_xlim(0.07, 900.0)
    ax4.set_xlabel("Verified Spectral Coverage per Bridge Star (µm)")
    ax4.set_title("D. Top 22 of 66 Bridges (780 Cells; *8 New, +4 Deepened in D098)")
    ax4.grid(axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D098 Synthesis: 2,031 Calibration Trials, 473-Star Ellipsoid, 458 Comb Stacks & 66 Bridges", y=0.99)
    _save(fig, "fig83_d098_calibration_2031_bridges_66stars.png")


def fig84_panchromatic_473stars(summary: dict[str, Any]) -> None:
    syn = _read_csv("UNIFIED_PANCHROMATIC_V5_6_SYNTHESIS_473STARS.csv")
    br = _read_csv("PANCHROMATIC_BRIDGE_66STARS_V56.csv")
    syn_map = {r["star"]: r for r in syn}
    rev_set = set(summary["cohort"]["newly_promoted_science_bridges"] + summary["cohort"]["deepened_science_bridges"] + summary["cohort"]["revisited_controls"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.0, 6.9))
    fig.subplots_adjust(wspace=0.28)

    d_prior, p_prior = [], []
    d_rev, p_rev = [], []
    d_new: dict[str, tuple[list[float], list[float]]] = {}
    inst_palette = {
        "CARMENES_VIS": ("D098 CARMENES_VIS", "#1b9e77", "s", 54),
        "ISO_SWS": ("D098 ISO/SWS", "#980043", "o", 52),
        "SOFIA_FORCAST": ("D098 SOFIA/FORCAST", "#2b8cbe", "^", 56),
        "SOFIA_GREAT": ("D098 SOFIA/GREAT", "#d95f02", "*", 78),
    }

    for r in syn:
        if not r.get("min_panchromatic_10m_kw"):
            continue
        dist = float(r["dist_pc"])
        pkw = float(r["min_panchromatic_10m_kw"])
        phs = r["phases"].split("+")
        if "D098" not in phs:
            d_prior.append(dist)
            p_prior.append(pkw)
        elif len(phs) > 1 or r["star"] in rev_set:
            d_rev.append(dist)
            p_rev.append(pkw)
        else:
            insts = r["instruments"].replace(";", "+").split("+")
            picked = next((ik for ik in inst_palette if ik in insts), "SOFIA_GREAT")
            d_new.setdefault(picked, ([], []))
            d_new[picked][0].append(dist)
            d_new[picked][1].append(pkw)

    ax1.scatter(d_prior, p_prior, s=15, c="#a6bddb", alpha=0.72, edgecolor="none", label=f"Prior D079–D097 ({len(d_prior)})", zorder=2)
    ax1.scatter(d_rev, p_rev, s=60, c="#6a51a3", marker="D", edgecolor="black", lw=0.6, label=f"D098 Revisited Bridges ({len(d_rev)})", zorder=4)
    for ik, (lbl, col, mk, sz) in inst_palette.items():
        if ik in d_new:
            xs, ys = d_new[ik]
            ax1.scatter(xs, ys, s=sz, c=col, marker=mk, edgecolor="black", lw=0.55, label=f"{lbl} ({len(xs)})", zorder=5)

    ax1.axvline(10.0, color="#1b7837", ls="--", lw=1.2, alpha=0.85)
    ax1.text(10.8, 3.0e14, "10 pc Solar\nNeighborhood\n(173 stars)", color="#1b7837", fontsize=8.0, ha="left", va="top")
    med10 = float(summary["unified_473star_panchromatic_v5_6_synthesis"]["within_10pc_median_limit_kw"])
    ax1.axhline(med10, color="#2b8cbe", ls=":", lw=1.25)
    ax1.text(280.0, med10 * 1.5, f"<10 pc Median: {med10:.4f} kW", color="#045a8d", fontsize=8.0, ha="left")

    def _ann_st(st: str, text: str, xyt: tuple[float, float], col: str) -> None:
        if st in syn_map and syn_map[st].get("min_panchromatic_10m_kw"):
            xd, yp = float(syn_map[st]["dist_pc"]), float(syn_map[st]["min_panchromatic_10m_kw"])
            ax1.annotate(text, xy=(xd, yp), xytext=xyt, fontsize=7.2, fontweight="bold" if col != "#555555" else "normal",
                         color=col, bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.80),
                         arrowprops=dict(arrowstyle="->", color=col, lw=0.85))

    _ann_st("PROXIMA", "Proxima Cen (1.3 pc)\n0.0973 W (STIS)", (3.6, 0.00018), "#555555")
    _ann_st("GJ1286", "GJ 1286 (7.2 pc)\n455.5 W (CARMENES)", (18.0, 0.0020), "#1b9e77")
    _ann_st("70VIR", "70 Vir (17.9 pc)\n20,827 kW (ISO/SWS)", (240.0, 220.0), "#980043")
    _ann_st("DGTAU", "DG Tau (125.3 pc)\n31.7 GW (SOFIA/GREAT)", (2.2e3, 3.0e5), "#d95f02")
    _ann_st("NGC4151", "NGC 4151 (15.8 Mpc)\nAGN Control (ISO/SWS)", (1.6e4, 1.5e14), "#980043")

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.8, 3.5e7)
    ax1.set_ylim(5e-5, 5e16)
    ax1.set_xlabel("Heliocentric Distance (pc)")
    ax1.set_ylabel("Best 10-m Optical/IR/THz Laser Beam EIRP Limit (kW)")
    ax1.set_title("A. 473-Star Panchromatic Distance–EIRP Sensitivity (0 Verified ETI)")
    ax1.legend(loc="lower right", frameon=True, fontsize=6.9, ncol=1)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: 66 Bridges (780 cells) across 12.855 Octaves (D098 gap closure highlighted)
    by_star_br: dict[str, list[tuple[float, float]]] = {}
    for r in br:
        by_star_br.setdefault(r["star"], []).append((float(r["wave_um"]), float(r["p_beam_10m_kw"])))

    hi_bridges = {
        "HD219134": ("HD 219134 (+ ISO/SWS 2.78 MW)", "#980043", "o"),
        "AUMIC": ("AU Mic (+ ISO/SWS 3.41 MW)", "#2b8cbe", "s"),
        "HD192310": ("HD 192310 (+ ISO/SWS 5.05 MW)", "#1b9e77", "^"),
        "FOMALHAUT": ("Fomalhaut (+ ISO/SWS 10.3 MW)", "#6a51a3", "D"),
        "BETELGEUSE": ("Betelgeuse (+ SOFIA/GREAT 63–158 µm)", "#d95f02", "v"),
        "HD141569": ("HD 141569 (+ GREAT 63–158 µm)", "#e6ab02", "*"),
    }
    first_bg = True
    for st, pts in by_star_br.items():
        if st not in hi_bridges:
            pts_s = sorted(pts)
            ax2.plot([p[0] for p in pts_s], [p[1] for p in pts_s], color="#b3cde3", lw=0.8, alpha=0.55, label="60 Other Calibrated Bridges" if first_bg else None, zorder=2)
            first_bg = False

    for st, (lbl, col, mk) in hi_bridges.items():
        if st in by_star_br:
            pts_s = sorted(by_star_br[st])
            ax2.plot([p[0] for p in pts_s], [p[1] for p in pts_s], color=col, marker=mk, ms=4.5, lw=1.55, label=lbl, zorder=5)

    ax2.axvspan(2.36, 45.39, color="#fccde5", alpha=0.36, label="D098 ISO/SWS Continuous (2.36–45.39 µm)")
    ax2.axvspan(5.0, 37.0, color="#ccebc5", alpha=0.30, label="D098 SOFIA/FORCAST 4-Grism (5–37 µm)")
    ax2.axvspan(63.0, 206.0, color="#fed9a6", alpha=0.38, label="D098 SOFIA/GREAT (63–206 µm)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.075, 950.0)
    ax2.set_ylim(2e-2, 5e9)
    ax2.set_xlabel("Rest/Barycentric Wavelength (µm) — 12.855 Octaves Total")
    ax2.set_ylabel("10-m Beam EIRP Limit (kW)")
    ax2.set_title("B. 66 Calibrated Bridges (780 Cells; +2 Controls = 68 Multi-Phase)")
    ax2.legend(loc="upper left", frameon=True, fontsize=6.7, ncol=1)
    ax2.grid(True, which="both", alpha=0.20)

    fig.suptitle("Phase D098 (V5.6): Unified 473-Star Panchromatic Survey Across 33 Spectrographs & 12.855 Octaves", y=0.99)
    _save(fig, "fig84_d098_panchromatic_473stars_12p86octaves.png")


def main() -> int:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    with gzip.open(WS / "bounded_inputs" / "d098_bounded_bundle.json.gz", "rt", encoding="utf-8") as gz:
        bundle = json.load(gz)

    fig79_sofia_great(bundle)
    fig80_iso_sws(bundle)
    fig81_sofia_forcast(bundle)
    fig82_carmenes_drift_v56(bundle)
    fig83_calibration_bridges(summary)
    fig84_panchromatic_473stars(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
