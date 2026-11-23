#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D101 (V5.9) Publication Figure Generator (fig97-fig102, 240 DPI).
Reads strictly from D101 Stage-2 results and bounded_inputs/d101_bounded_bundle.json.gz.
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
    "axes.titlesize": 9.6,
    "axes.titleweight": "bold",
    "axes.labelsize": 8.6,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.0,
    "figure.facecolor": "white",
    "axes.facecolor": "#fbfcfd",
    "axes.edgecolor": "#4a5568",
    "grid.color": "#cbd5e0",
})


def _read_csv(res_dir: Path, name: str) -> list[dict[str, str]]:
    with (res_dir / name).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fig_dir: Path, fname: str) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    out = fig_dir / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.14, metadata={})
    plt.close(fig)
    print(f"[FIG] Wrote {out.name} ({out.stat().st_size:,} B)")


def _cal_bars(ax: plt.Axes, cal_rows: list[dict[str, str]], title: str, replace_map: dict[str, str] | None = None, class_col: str = "class") -> None:
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
    bars = ax.bar(np.arange(len(c_names)), c_rates, color=[palette[i % len(palette)] for i in range(len(c_names))], edgecolor="black", lw=0.7)
    ax.set_ylim(0.0, 118.0)
    ax.set_xticks(np.arange(len(c_names)))
    ax.set_xticklabels(short_c, fontsize=7.0)
    ax.set_ylabel("Calibration Pass Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, c_names):
        p, t = cls_counts[k]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig97_alma_gap_closure(res_dir: Path, fig_dir: Path) -> None:
    rows = _read_csv(res_dir, "ALMA_MM_INTERFEROMETRIC_58STARS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.32, hspace=0.36)

    # Panel A: Frequency coverage of all 62 ALMA cubes closing D100's 1.40-3.44 mm gap
    band_cfg = [
        ("ALMA_B1_7MM", "Band 1 (7 mm; 35.0-44.0 GHz)", "#b30000"),
        ("ALMA_B3_3MM", "Band 3 (3 mm; 93.9-115.8 GHz)", "#d95f02"),
        ("ALMA_B4_2MM", "Band 4 (2 mm; 126.2-158.9 GHz)", "#2b8cbe"),
        ("ALMA_B5_2MM", "Band 5 (2 mm; 163.4-210.9 GHz)", "#1b9e77"),
    ]
    # Shaded terrestrial O2 absorption windows and JCMT Band-3 range
    ax1.axvspan(50.0, 68.0, color="#fed7d7", alpha=0.65, label="Terrestrial O2 60 GHz Opaque")
    ax1.axvspan(116.0, 121.5, color="#feebc8", alpha=0.75, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(77.746, 87.215, color="#e2e8f0", alpha=0.60, label="D100 JCMT 'Alaihi (77.7-87.2 GHz)")
    rows_sorted = sorted(rows, key=lambda r: (r["instrument"], float(r["min_freq_ghz"])))
    for yi, r in enumerate(rows_sorted):
        col = next(c for b, _, c in band_cfg if b == r["instrument"])
        ax1.plot([float(r["min_freq_ghz"]), float(r["max_freq_ghz"])], [yi, yi], lw=2.3, color=col)
    for b, lbl, col in band_cfg:
        ax1.plot([], [], lw=3.0, color=col, label=lbl)
    ax1.set_xlim(28.0, 222.0)
    ax1.set_ylim(-2, len(rows_sorted) + 2)
    ax1.set_xlabel("Observing Frequency (GHz; 35.037 GHz = 8,556.42 um <-> 210.905 GHz = 1,421.46 um)")
    ax1.set_ylabel("ALMA Archival Spectral Cube Index (62 Cubes)")
    ax1.set_title("A. ALMA B1/B3/B4/B5 Gap Closure & 8.56 mm Long-Wave Extension")
    ax1.legend(loc="lower right", fontsize=6.4, frameon=True, ncol=2)
    ax1.grid(True, alpha=0.22)

    # Panel B: CALIBRATION_V59_ALMA_INTERFEROMETRIC_240
    _cal_bars(
        ax2, cal, "B. V5.9 ALMA Interferometric Calibration (240/240 = 100.0%)",
        {"ALMA_CLEAN_POINT_BEACON": "Clean Point\nBeacon", "EXTENDED_DISK_EMISSION": "Extended\nDisk", "OFFSOURCE_BIRDIE_SIDELOBE": "Off-Source\nSidelobe", "MM_MOLECULAR_ATLAS": "MM Mol.\nAtlas", "SINGLE_CHAN_GIBBS_SW": "1-Ch Gibbs\n/ SW"},
    )

    # Panel C: Science Best 10-m EIRP Limits vs Distance by ALMA Band
    sci_rows = [r for r in rows if r["role"] == "SCIENCE"]
    for b, lbl, col in band_cfg:
        sub = [r for r in sci_rows if r["instrument"] == b]
        ax3.scatter([float(r["dist_pc"]) for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=36, color=col, edgecolor="black", lw=0.5, label=f"{lbl} ({len(sub)})", alpha=0.88)
    hl = [("AUMIC", "AU Mic\n187.0 kW", (12, -16)), ("BETPIC", "beta Pic\n503.1 kW", (10, 6)), ("HD163296", "HD 163296\n3,290 kW", (8, -14)), ("PDS70", "PDS 70\n75.8 MW", (-65, 16))]
    for st_k, txt, off in hl:
        cand_h = sorted([r for r in sci_rows if r["star"] == st_k], key=lambda x: float(x["p_beam_10m_kw"]))
        if cand_h:
            r0 = cand_h[0]
            ax3.annotate(txt, (float(r0["dist_pc"]), float(r0["p_beam_10m_kw"])), xytext=off, textcoords="offset points", fontsize=6.8, fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.6, color="#333333"))
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.set_xlabel("Heliocentric Distance d (pc)")
    ax3.set_ylabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    ax3.set_title(f"C. Science ALMA 10-m Beam EIRP Sensitivity ({len(sci_rows)} Cubes)")
    ax3.legend(loc="lower right", fontsize=6.7, frameon=True)
    ax3.grid(True, which="both", alpha=0.22)

    # Panel D: Cube 6-sigma Flux Density Limit vs Effective Spectral Resolution
    for b, lbl, col in band_cfg:
        sub = [r for r in rows if r["instrument"] == b]
        ax4.scatter([float(r["rp_eff"]) for r in sub], [float(r["flux_lim_mjy_6sig"]) for r in sub], s=34, color=col, edgecolor="black", lw=0.5, label=b.replace("_", " "), alpha=0.86)
    ax4.set_xscale("log")
    ax4.set_yscale("log")
    ax4.set_xlabel("Effective Spectral Resolving Power R_eff = c / (FWHM_chan * dv_chan)")
    ax4.set_ylabel("6-sigma Point-Source Sensitivity (mJy)")
    ax4.set_title("D. All-62 Cube Radiometric Flux Limit vs Effective Resolution")
    ax4.legend(loc="upper right", fontsize=7.0, frameon=True)
    ax4.grid(True, which="both", alpha=0.22)

    fig.suptitle("Phase D101 (V5.9): ALMA Band 1/3/4/5 Interferometric Gap Closure Across 62 Spectral Cubes & 58 Targets (0 ETI)", fontsize=11.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig97_d101_alma_band1_gap_closure_58stars.png")


def fig98_alma_spatial_spectral_vetoes(res_dir: Path, bundle: dict[str, Any], az: Any, fig_dir: Path) -> None:
    sp_cands = [r for r in _read_csv(res_dir, "V5_9_SPACE_CANDIDATE_LEDGER.csv") if str(r["instrument"]).startswith("ALMA_")]
    exps = [e for e in bundle["exposures"] if str(e["instrument"]).startswith("ALMA_")]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Circinus Galaxy Band 1 spw25 ON-beam vs OFF-annulus p95 spectrum (8.56 mm Frontier)
    circ = next(e for e in exps if e["star"] == "CIRCINUSGAL")
    fq_c = az._decode_arr_any(circ["freq_ghz_c"])
    on_c = az._decode_arr_any(circ["s_on_jy_c"]) * 1e3
    off_c = az._decode_arr_any(circ["s_off_95_jy_c"]) * 1e3
    ord_c = np.argsort(fq_c)
    ax1.plot(fq_c[ord_c], on_c[ord_c], lw=0.7, color="#1b9e77", label="ON-beam 1-px core (median-subtracted mJy)")
    ax1.plot(fq_c[ord_c], off_c[ord_c], lw=0.7, color="#636363", alpha=0.75, label="OFF-annulus 95th pct (mJy)")
    ax1.set_xlabel("Observing Frequency (GHz; Band 1 spw25 -> max wave 8,556.42 um)")
    ax1.set_ylabel("Spectral Flux Density (mJy)")
    ax1.set_title("A. Band 1 Frontier Cube: Circinus Galaxy spw25 (35.037-35.506 GHz; 0 Peaks)")
    ax1.legend(loc="upper right", fontsize=6.9, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: GW Ori (Band 4 SO) & Beta Pic (Band 3 CO 1-0) ON vs OFF comparison
    gw = next(e for e in exps if e["star"] == "GWORI" and e["instrument"] == "ALMA_B4_2MM")
    bp = next(e for e in exps if e["star"] == "BETPIC")
    for ex_i, col_i, off_y, lbl_i in [
        (gw, "#2b8cbe", 0.0, "GW Ori Band 4 SO(3_4-2_3) 138.172 GHz (G3 MM Atlas)"),
        (bp, "#d95f02", 1.35, "beta Pic Band 3 CO(1-0) 115.271 GHz (G3 + G4 Extended)"),
    ]:
        fq = az._decode_arr_any(ex_i["freq_ghz_c"])
        on = az._decode_arr_any(ex_i["s_on_jy_c"])
        off = az._decode_arr_any(ex_i["s_off_95_jy_c"])
        pk_i = int(np.nanargmax(on))
        pk_f = float(fq[pk_i])
        base = float(np.nanmedian(on))
        scale = max(1e-6, float(on[pk_i]) - base)
        df_mhz = (fq - pk_f) * 1000.0
        m_w = np.abs(df_mhz) <= 150.0
        o_w = np.argsort(df_mhz[m_w])
        ax2.plot(df_mhz[m_w][o_w], (on[m_w][o_w] - base) / scale + off_y, lw=1.1, color=col_i, label=lbl_i)
        ax2.plot(df_mhz[m_w][o_w], (off[m_w][o_w] - base) / scale + off_y, lw=0.85, ls=":", color="#4a5568")
    ax2.set_ylim(-0.25, 2.75)
    ax2.set_xlabel("Frequency Offset from Peak Channel (MHz; dotted = OFF-annulus p95)")
    ax2.set_ylabel("Peak-Normalized Amplitude + Offset")
    ax2.set_title("B. Astrophysical Molecular Emission in ALMA Cubes (GW Ori & beta Pic)")
    ax2.legend(loc="upper right", fontsize=6.7, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: Spatial-Spectral Decision Plane (beam_conc vs off95_to_on)
    ax3.fill_between([0.85, 1.05], -0.04, 0.22, color="#d4edda", alpha=0.60, label="Unresolved Point-Source Pass Box")
    ax3.axvline(0.85, color="#1b9e77", ls="--", lw=1.1)
    ax3.axhline(0.22, color="#d95f02", ls="--", lw=1.1)
    cat_styles = [
        ("G3_", "#7570b3", "D", "G3 MM Mol. Atlas"),
        ("G4_", "#d95f02", "s", "G4 Extended Disk"),
        ("STAGE2_", "#b30000", "o", "S2 Unrepeated Line"),
    ]
    for pfx, col, mk, lbl in cat_styles:
        sub = [r for r in sp_cands if str(r["stage2_triage_status"]).startswith(pfx)]
        if sub:
            ax3.scatter([float(r["beam_conc"]) for r in sub], [float(r["off95_to_on"]) for r in sub], s=50, color=col, marker=mk, edgecolor="black", lw=0.6, label=f"{lbl} ({len(sub)})", zorder=4)
    ax3.set_xlim(0.15, 1.04)
    ax3.set_ylim(-0.04, 0.90)
    ax3.set_xlabel("Beam Flux Concentration Fraction (s_on vs spatial peak-box)")
    ax3.set_ylabel("OFF-Annulus 95th-Percentile / ON-Beam Peak Ratio")
    ax3.set_title(f"C. Interferometric Spatial-Spectral Discrimination ({len(sp_cands)} Raw Peaks)")
    ax3.legend(loc="upper left", fontsize=6.8, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: Stage-1/2 Veto Breakdown
    vr_cnt = Counter(r["stage2_triage_status"].split(":")[0].replace("STAGE2_VETO_", "S2: ").replace("G3_ALMA_MM_MOLECULAR_ATLAS", "G3 MM Mol. Atlas").replace("G4_ALMA_BEAM_COMPACTNESS|G6_ALMA_OFFSOURCE_ANNULUS_VETO", "G4+G6 Extended/Annulus").replace("G4_ALMA_BEAM_COMPACTNESS", "G4 Extended Disk").replace("S2: UNREPEATED_SINGLE_CUBE_OR_MASKED_LINE", "S2: Unrepeated Line") for r in sp_cands)
    vr_cnt["Verified ETI"] = sum(int(r["verified_eti"]) for r in sp_cands)
    keys4 = list(vr_cnt.keys())
    vals4 = [vr_cnt[k] for k in keys4]
    y4 = np.arange(len(keys4))
    ax4.barh(y4, vals4, color=["#b30000" if k == "Verified ETI" else "#2b8cbe" for k in keys4], edgecolor="black", lw=0.6)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(keys4, fontsize=7.4)
    ax4.set_xlim(0, max(max(vals4), 1) * 1.25)
    for yi, vv in enumerate(vals4):
        ax4.text(vv + 0.15, yi, str(vv), va="center", fontsize=8.0, fontweight="bold")
    ax4.set_xlabel("Candidate Count (62 ALMA Cubes -> 0 Verified ETI)")
    ax4.set_title(f"D. ALMA V5.9 Stage-1 + Stage-2 Funnel ({len(sp_cands)} Raw -> 3 S2 -> 0 ETI)")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle("Phase D101 (V5.9): ALMA Interferometric Spatial-Spectral Sidelobe, Disk, & Molecular-Line Forensics", fontsize=11.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig98_d101_alma_spatial_spectral_vetoes.png")


def fig99_eso_espresso_harps(res_dir: Path, orb_json: dict[str, Any], az: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6.csv")
    fg = _read_csv(res_dir, "FOUR_GEN_BENCHMARK_D101.csv")
    eirp = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D101.csv")
    comp = _read_csv(res_dir, "CALIBRATION_COMPLETENESS_BY_BAND.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.33, hspace=0.38)

    # Panel A: Orbits #151-#156 Planetary RV Curves Across 6 Epochs
    pal = ["#b30000", "#2b8cbe", "#1b9e77", "#d95f02", "#7570b3", "#636363"]
    for idx_o, r in enumerate(o6):
        st = r["star"]
        om = orb_json["campaigns"][st]
        ph = np.linspace(0.01, 0.99, 250)
        p_d = float(om["orb_per_days"])
        e_v = float(om["orb_ecc"])
        w_r = math.radians(float(om["orb_omega_deg"]))
        kp = float(om["kp_kms"])
        vr_c = np.asarray([float(az.det.solve_kepler_eccentric_rv(np.array([p_i * p_d]), p_d, e_v, w_r, 0.0, kp)[0]) for p_i in ph], dtype=np.float64)
        ax1.plot(ph, vr_c, lw=1.7, color=pal[idx_o % len(pal)], label=f"#{r['campaign_index']} {st} (P={p_d:.1f}d, e={e_v:.2f}, Kp={kp:.1f})")
    ax1.set_xlabel("Orbital Phase phi")
    ax1.set_ylabel("Planetary Keplerian RV (km/s)")
    ax1.set_title("A. Live Orbital Campaigns #151-#156 (Up to GJ 3222 e=0.929 & HD 140901 21.6 yr)")
    ax1.legend(loc="upper right", fontsize=6.6, frameon=True)
    ax1.grid(True, alpha=0.25)

    # Panel B: 4-Gen G1-G8 Funnel
    gates = ["g1_seeds", "g2_pass", "g3_pass", "g45_pass", "g6_pass", "g7_pass", "g8_pass", "stage2_verified_eti"]
    g_lbls = ["G1\nSeeds", "G2\nSky", "G3\nChr", "G4+G5\nLSF", "G6\nTopo", "G7\nRPCA", "G8\nkNN", "Verif.\nETI"]
    x2 = np.arange(len(gates))
    w_bar = 0.36
    for i, fg_r in enumerate(fg):
        vals = [int(fg_r[g]) for g in gates]
        ax2.bar(x2 + (i - 0.5) * w_bar, vals, width=w_bar, color="#7570b3" if "ESPRESSO" in fg_r["instrument"] else "#1b9e77", edgecolor="black", lw=0.6, label=f"{fg_r['instrument']} ({fg_r['n_stars']} stars / {fg_r['n_exposures']} exp)")
        for xi, vv in zip(x2 + (i - 0.5) * w_bar, vals):
            if vv > 0 or g_lbls[int(round(xi))] == "Verif.\nETI":
                ax2.text(xi, vv + 0.7, str(vv), ha="center", va="bottom", fontsize=7.0, fontweight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(g_lbls, fontsize=7.0)
    ax2.set_ylim(0, max(max(int(r["g1_seeds"]) for r in fg) * 1.22, 5))
    ax2.set_ylabel("Surviving Candidate Count")
    ax2.set_title("B. ESO ESPRESSO (R=140k) + HARPS 4-Gen G1-G8 Funnel (0 ETI)")
    ax2.legend(loc="upper right", fontsize=7.2, frameon=True)
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: Per-star Optical Best 10-m EIRP Bounds
    eso_best: dict[tuple[str, str], float] = {}
    for r in eirp:
        if r["instrument"].startswith("ESO_"):
            k = (r["star"], r["instrument"])
            eso_best[k] = min(eso_best.get(k, float("inf")), float(r["p_beam_10m_kw"]))
    eb_items = sorted(eso_best.items(), key=lambda x: x[1])
    y3 = np.arange(len(eb_items))
    ax3.barh(y3, [v for _, v in eb_items], color=["#7570b3" if ins == "ESO_ESPRESSO" else "#1b9e77" for (_, ins), _ in eb_items], edgecolor="black", lw=0.6)
    ax3.set_yticks(y3)
    ax3.set_yticklabels([f"{st} ({ins.replace('ESO_', '')})" for (st, ins), _ in eb_items], fontsize=7.4)
    ax3.set_xscale("log")
    for yi, (_, vv) in enumerate(eb_items):
        ax3.text(vv * 1.08, yi, f"{vv:.3f} kW", va="center", fontsize=7.2, fontweight="bold")
    ax3.set_xlim(0.2, max(v for _, v in eb_items) * 2.5)
    ax3.set_xlabel("6-sigma 10-m Equivalent Beam EIRP Limit (kW)")
    ax3.set_title("C. All 9 ESO Stars 10-m Optical EIRP Sensitivity (Best: GL 479 0.355 kW)")
    ax3.grid(True, axis="x", which="both", alpha=0.25)

    # Panel D: INJECTION_RECOVERY_540 Completeness across 19 Bands
    y4 = np.arange(len(comp))
    ax4.barh(y4, [100.0 * float(r["completeness_p"]) for r in comp], color=["#d95f02" if r["instrument"].startswith("ALMA_") else "#2b8cbe" for r in comp], edgecolor="black", lw=0.45)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([r["band_id"] for r in comp], fontsize=6.4)
    ax4.set_xlim(0, 116)
    ax4.invert_yaxis()
    for yi, r in enumerate(comp):
        ax4.text(101.0, yi, f"{r['n_pass']}/{r['n_trials']}", va="center", fontsize=6.5, fontweight="bold")
    ax4.set_xlabel("Injection Recovery Pass Rate (%)")
    ax4.set_title("D. 19-Band Optical+ALMA Injection Recovery (540/540 = 100.0%)")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle("Phase D101 (V5.9): ESO ESPRESSO (R=140,000) & HARPS Orbits #151-#156 + 19-Band Completeness", fontsize=11.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig99_d101_eso_espresso_harps_orbits_151_156.png")


def fig100_comb_drift_v59(res_dir: Path, fig_dir: Path) -> None:
    cd48 = _read_csv(res_dir, "COMB_DRIFT_V59_48CAMPAIGNS.csv")
    ek48 = _read_csv(res_dir, "DRIFT_V59_ECCENTRIC_KEPLERIAN_48CAMPAIGNS.csv")
    cal_dc = _read_csv(res_dir, "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    sum_j = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: CALIBRATION_V59_DRIFTING_COMB_240 vs Static V4.1 Baseline
    cls_map = {}
    for r in cal_dc:
        c = r["class"]
        cls_map.setdefault(c, [0, 0])
        cls_map[c][0] += int(r["passed"])
        cls_map[c][1] += 1
    labels_a = ["V5.9 Kepler\nComb (60)", "V5.9 Linear\nComb (60)", "Static V4.1 on\n120 Drifting", "Stationary\nVeto (40)", "Transient\nVeto (40)", "BERV/Noise\nVeto (40)"]
    vals_a = [
        100.0 * cls_map["KEPLERIAN_DRIFTING_COMB"][0] / cls_map["KEPLERIAN_DRIFTING_COMB"][1],
        100.0 * cls_map["LINEAR_ACCEL_DRIFTING_COMB"][0] / cls_map["LINEAR_ACCEL_DRIFTING_COMB"][1],
        100.0 * sum(int(r["v41_static_obs"]) for r in cal_dc[:120]) / 120.0,
        100.0 * cls_map["STATIONARY_ETALON_COMB_VETO"][0] / cls_map["STATIONARY_ETALON_COMB_VETO"][1],
        100.0 * cls_map["SINGLE_EPOCH_TRANSIENT_COMB_VETO"][0] / cls_map["SINGLE_EPOCH_TRANSIENT_COMB_VETO"][1],
        100.0 * cls_map["BERV_SKY_OR_NOISE_COMB_VETO"][0] / cls_map["BERV_SKY_OR_NOISE_COMB_VETO"][1],
    ]
    txt_a = ["60/60", "60/60", f"{sum(int(r['v41_static_obs']) for r in cal_dc[:120])}/120", "40/40", "40/40", "40/40"]
    cols_a = ["#1b9e77", "#2b8cbe", "#b30000", "#636363", "#636363", "#636363"]
    bars = ax1.bar(np.arange(len(labels_a)), vals_a, color=cols_a, edgecolor="black", lw=0.7)
    ax1.set_xticks(np.arange(len(labels_a)))
    ax1.set_xticklabels(labels_a, fontsize=7.0)
    ax1.set_ylim(0, 118)
    for b, t_s in zip(bars, txt_a):
        ax1.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, t_s, ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax1.set_ylabel("Calibration Recovery / Veto Rate (%)")
    ax1.set_title("A. V5.9 Coherent Drifting Comb Calibration (240/240 vs Static V4.1 9.2%)")
    ax1.grid(True, axis="y", alpha=0.25)

    # Panel B: 48-Campaign COMB_DRIFT_V59 Trajectories & Candidates
    ord_x = np.arange(1, len(cd48) + 1)
    comb_traj = [max(1, int(r["comb_trajectories_evaluated"])) for r in cd48]
    cols_b = ["#b30000" if r["phase_source"] == "D101" else "#2b8cbe" for r in cd48]
    ax2.bar(ord_x, comb_traj, color=cols_b, edgecolor="black", lw=0.4, alpha=0.88)
    ax2.plot([], [], color="#b30000", lw=6, label="Live D101 Campaigns (#1-#6)")
    ax2.plot([], [], color="#2b8cbe", lw=6, label="Retroactive Archives T-Z (#7-#48)")
    ax2.set_xlabel("Multi-Epoch Campaign Index (#1-#48 Across Phases D094-D101)")
    ax2.set_ylabel("Comb-Drift Velocity Trajectories Evaluated")
    ax2.set_title(f"B. COMB_DRIFT_V59 Across All 48 Campaigns ({sum_j['comb_drift_v59_48campaigns_trajectories']:,} Trajectories)")
    ax2.legend(loc="upper right", fontsize=7.2, frameon=True)
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: DRIFT_V59 Eccentric Keplerian Pixel Integrals vs Comb Raw Candidates across 48 campaigns
    n_ek = np.asarray([int(r["n_trajectories_evaluated"]) for r in ek48], dtype=np.float64)
    n_pix = np.asarray([int(r["n_pixel_trajectory_integrals"]) / 1e8 for r in ek48], dtype=np.float64)
    for is_live, col, lbl in [(True, "#b30000", "D101 Live (6)"), (False, "#1b9e77", "Archives T-Z Retro (42)")]:
        m = np.asarray([r["phase_source"] == "D101" for r in ek48]) == is_live
        ax3.scatter(n_ek[m], n_pix[m], s=55 if is_live else 36, color=col, edgecolor="black", lw=0.5, label=lbl, zorder=4 if is_live else 2)
    ax3.set_xlabel("DRIFT_V59 Trajectories Evaluated per Campaign")
    ax3.set_ylabel("Pixel-Trajectory Integrals (x 10^8)")
    ax3.set_title(f"C. DRIFT_V59 Scale Across 48 Campaigns ({sum_j['drift_v59_48campaigns_pixel_integrals']/1e9:.2f}B Pixel Integrals)")
    ax3.legend(loc="upper left", fontsize=7.3, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: Stage-2 Triage Summary for Both Multi-Epoch Engines (0 ETI)
    labels_d = ["DRIFT_V59\nRaw Survivors", "COMB_DRIFT_V59\nRaw Candidates", "COMB_DRIFT_V59\nPre-Stage2 Qual.", "Static COMB_V4_1\nD101 Candidates", "Verified ETI\n(All 48 Campaigns)"]
    vals_d = [
        int(sum_j["drift_v59_48campaigns_raw_survivors"]),
        int(sum_j["comb_drift_v59_48campaigns_raw_candidates"]),
        int(sum_j["comb_drift_v59_48campaigns_qualified_pre_stage2"]),
        int(sum_j["comb_v4_1_candidates"]),
        0,
    ]
    y4 = np.arange(len(labels_d))
    ax4.barh(y4, [max(0.8, v) if v > 0 else 0.0 for v in vals_d], color=["#7570b3", "#2b8cbe", "#d95f02", "#636363", "#b30000"], edgecolor="black", lw=0.6)
    ax4.set_xscale("symlog", linthresh=10.0)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(labels_d, fontsize=7.3)
    ax4.set_xlim(0, 60000)
    ax4.invert_yaxis()
    for yi, vv in enumerate(vals_d):
        ax4.text(vv + (1.2 if vv == 0 else vv * 0.15), yi, f"{vv:,}", va="center", fontsize=8.0, fontweight="bold")
    ax4.set_xlabel("Candidate Count Across 48 Campaigns (symlog scale)")
    ax4.set_title("D. 48-Campaign Stage-2 Veto Resolution -> 0 Verified ETI")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle("Phase D101 (V5.9): Coherent Drifting-Comb (COMB_DRIFT_V59) & DRIFT_V59 Across 48 Campaigns (D094-D101)", fontsize=11.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig100_d101_comb_drift_v59_48campaigns.png")


def fig101_panchromatic_613stars(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    syn = s_json["unified_613star_panchromatic_v5_9_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp101 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D101.csv")
    s180 = _read_csv(res_dir, "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_180STARS.csv")
    ell = _read_csv(res_dir, "MULTIEVENT_ELLIPSOID_613STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15.8, 10.6))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Full 0.0905-8,556.42 um (16.529 octaves) with shaded terrestrial O2 walls
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz (2.47-2.58 mm)")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.70, zorder=0, label="Terrestrial O2 60 GHz (4.41-6.00 mm)")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D101" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=10, color="#bdbdbd", alpha=0.55, zorder=1, label="D079-D100 (0.0905-3,856.05 um)")

    inst_style = {
        "ESO_ESPRESSO": ("#7570b3", "v", "D101 ESPRESSO (0.42-0.76 um)"),
        "ESO_HARPS": ("#66a61e", "o", "D101 HARPS (0.41-0.58 um)"),
        "ALMA_B5_2MM": ("#1b9e77", "s", "D101 ALMA B5 (1.42-1.83 mm)"),
        "ALMA_B4_2MM": ("#2b8cbe", "D", "D101 ALMA B4 (1.89-2.38 mm)"),
        "ALMA_B3_3MM": ("#d95f02", "^", "D101 ALMA B3 (2.59-3.19 mm)"),
        "ALMA_B1_7MM": ("#b30000", "*", "D101 ALMA B1 (6.81-8.56 mm)"),
    }
    for ik, (col, mk, lbl) in inst_style.items():
        sub = [r for r in eirp101 if r["instrument"] == ik]
        ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=26 if mk != "*" else 52, color=col, marker=mk, edgecolor="black", lw=0.35, label=lbl, zorder=4)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.06, 12500.0)
    ax1.set_xlabel(f"Wavelength (um; {syn['min_wave_um']}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("6-sigma / 8-sigma 10-m EIRP Limit (kW)")
    ax1.set_title("A. Unified 41-Spectrograph Sensitivity Frontier (16.529 Octaves)")
    ax1.legend(loc="upper left", fontsize=6.1, frameon=True, ncol=1)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-613 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V5_8_PHASES_SNAPSHOT.json").read_text())["prior_unified_560_rows"]}
    all101_st = {e["star"] for e in bundle["exposures"]}
    brand53 = all101_st - prior_st
    bridges14 = all101_st & prior_st
    ra_p, dec_p, ra_b, dec_b, ra_n, dec_n = [], [], [], [], [], []
    for r in ell:
        ra = ((float(r["ra_deg"]) + 180.0) % 360.0) - 180.0
        dc = float(r["dec_deg"])
        if r["star"] in brand53:
            ra_n.append(ra); dec_n.append(dc)
        elif r["star"] in bridges14:
            ra_b.append(ra); dec_b.append(dc)
        else:
            ra_p.append(ra); dec_p.append(dc)
    ax2.scatter(ra_p, dec_p, s=12, color="#969696", alpha=0.58, label=f"Earlier D079-D100 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=36, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D101 Bridges / Revisited ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=46, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D101 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title("B. All-Sky Distribution Across 613 Analyzed Targets (472 Sci / 141 Ctrl)")
    ax2.legend(loc="lower left", fontsize=7.0, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: <10 pc Solar Neighborhood (180 Stars)
    lims10 = [float(r["min_panchromatic_10m_kw"]) for r in s180 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
    med10 = float(np.median(lims10))
    ax3.hist(np.log10(lims10), bins=22, color="#1b9e77", edgecolor="black", alpha=0.82)
    ax3.axvline(math.log10(med10), color="#b30000", ls="--", lw=1.6, label=f"Median: {med10:.4f} kW (180 stars <10 pc)")
    ax3.set_xlabel("log10(Minimum Panchromatic 10-m Laser EIRP Limit / kW)")
    ax3.set_ylabel("Target Count")
    ax3.set_title("C. Solar Neighborhood (<10 pc, 180 Stars) Sensitivity Distribution")
    ax3.legend(loc="upper right", fontsize=7.2, frameon=True)
    ax3.grid(True, alpha=0.25)

    # Panel D: D101 11-Suite Calibration Scorecard (2,271 Trials; 48,726 Cumulative)
    cal_sum = s_json["synthetic_calibration_2271_trials"]
    suites = cal_sum["suites"]
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [k.replace("CALIBRATION_V59_", "V59 ").replace("CALIBRATION_V58_", "").replace("CALIBRATION_", "").replace("DETECTOR_V58_", "").replace("_CALIBRATION", "").replace("_", " ") for k in s_names]
    y4 = np.arange(len(s_names))
    ax4.barh(y4, s_pcts, color="#2b8cbe", edgecolor="black", lw=0.5)
    ax4.set_yticks(y4)
    ax4.set_yticklabels(short_s, fontsize=6.4)
    ax4.set_xlim(92.0, 102.0)
    ax4.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax4.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=6.5, color="white", fontweight="bold")
    ax4.set_xlabel("Suite Pass Rate (%)")
    ax4.set_title(f"D. D101 11-Suite Calibration ({cal_sum['total_passed']}/{cal_sum['total_trials']} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cum. {syn['total_calibration_trials_d079_d101']:,})")
    ax4.grid(True, axis="x", alpha=0.25)

    fig.suptitle(f"Phase D101 (V5.9): 613 Stellar Systems Across 16.529 Octaves (13.919 Unbroken + ALMA B1/B3/B4/B5 -> 8,556.42 um; 0 ETI)", fontsize=11.1, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig101_d101_panchromatic_613stars_16p53octaves.png")


def fig102_bridge_synthesis(res_dir: Path, fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    syn = s_json["unified_613star_panchromatic_v5_9_synthesis"]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    u613 = _read_csv(res_dir, "UNIFIED_PANCHROMATIC_V5_9_SYNTHESIS_613STARS.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.8, 6.6))
    fig.subplots_adjust(wspace=0.34, top=0.84, bottom=0.16)

    # Panel A: UV-to-8.56mm Bridge Heatmap for D101 ALMA bridge stars + canonical anchors
    focus = ["AUMIC", "BETPIC", "HD163296", "HD100546", "HD141569", "ABAUR", "IRC10216", "VYCMA", "RDOR", "PDS70", "HD169142", "HLTAU", "HD36112", "OH231P8"]
    promoted5 = {"HD169142", "HD36112", "HLTAU", "OH231P8", "RDOR"}
    reg_bins = [
        ("UV\n(0.09-0.38)", 0.05, 0.38),
        ("Optical\n(0.38-0.95)", 0.38, 0.95),
        ("NIR/QCL\n(0.95-5)", 0.95, 5.0),
        ("Mid-IR\n(5-45)", 5.0, 45.0),
        ("Far-IR/THz\n(45-1402)", 45.0, 1410.0),
        ("B5/B4/B3\n(1421-3856)", 1410.0, 4000.0),
        ("ALMA B1\n(6807-8556)", 6000.0, 9000.0),
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
                v = math.log10(max(1e-6, pkw))
                if not math.isfinite(mat[i, j]) or v < mat[i, j]:
                    mat[i, j] = v
    cmap = matplotlib.colormaps["viridis_r"].copy()
    cmap.set_bad(color="#f1f5f9")
    im = ax1.imshow(mat, aspect="auto", cmap=cmap, vmin=-1.5, vmax=10.5)
    ax1.set_xticks(np.arange(len(reg_bins)))
    ax1.set_xticklabels([rb[0] for rb in reg_bins], fontsize=6.6)
    ax1.set_yticks(np.arange(len(focus)))
    ax1.set_yticklabels([f"{st} *" if st in promoted5 else st for st in focus], fontsize=7.4)
    for i in range(len(focus)):
        for j in range(len(reg_bins)):
            if math.isfinite(mat[i, j]):
                ax1.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center", fontsize=6.4, color="black" if mat[i, j] < 3.5 else "white", fontweight="bold")
    cb = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.03)
    cb.set_label("log10(Best 10-m EIRP Limit / kW)", fontsize=7.5)
    ax1.set_title(f"A. D101 Science Bridges UV-to-8.56mm (* = +5 Multi-Phase -> {syn['panchromatic_bridge_stars_total']} Bridges)")

    # Panel B: Cumulative Survey Trajectory D079-D101
    phase_order = ["D079", "D084", "D089", "D094", "D097", "D099", "D100", "D101"]
    x_lbls = ["D079\nV3", "D084\nV3.5", "D089\nV4.0", "D094\nV5.2", "D097\nV5.5", "D099\nV5.7", "D100\nV5.8", "D101\nV5.9"]
    milestones = []
    for p_cap in phase_order:
        cnt = sum(1 for r in u613 if any(tok.strip() <= p_cap for tok in r["phases"].split("+")))
        milestones.append(cnt)
    ax2.plot(np.arange(len(phase_order)), milestones, "-o", color="#b30000", lw=2.3, ms=8.0, markeredgecolor="black")
    for xi, mv in enumerate(milestones):
        ax2.annotate(f"{mv}", xy=(xi, mv), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.0, fontweight="bold")
    ax2.set_xticks(np.arange(len(phase_order)))
    ax2.set_xticklabels(x_lbls, fontsize=7.2)
    ax2.set_ylim(0.0, 760.0)
    ax2.set_ylabel("Cumulative Unique Analyzed Stars")
    ax2.set_title("B. Survey Growth D079-D101 (613 Stars; 27 Archives A-Z, AA; 0 ETI)")
    ax2.text(
        0.03, 0.63,
        f"Unified Survey Totals (D079-D101):\n"
        f"- 613 Analyzed Stars ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)\n"
        f"- {syn['planet_host_stars_total']} Hosts / {syn['confirmed_exoplanets_total']} Exoplanets\n"
        f"- 180 <10 pc (med {syn['within_10pc_median_limit_kw']:.4f} kW)\n"
        f"- {syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms\n"
        f"- {syn['total_exposures_d079_d101']:,} Exposures ({syn['total_integration_hours_d079_d101']:.1f} h)\n"
        f"- {syn['total_calibration_trials_d079_d101']:,} Calibration Trials\n"
        f"- {syn['cumulative_orbital_campaigns']} Orbits | 48 DRIFT+COMB_DRIFT | {syn['cumulative_comb_stacks']} Stacks\n"
        f"- Verified ETI Detections: {syn['verified_eti_detections_total']}",
        transform=ax2.transAxes, fontsize=6.9,
        bbox=dict(boxstyle="round,pad=0.35", fc="#f8fafc", ec="#b30000"),
    )
    ax2.grid(True, alpha=0.25)

    fig.suptitle(f"Phase D101 (V5.9): {syn['panchromatic_bridge_stars_total']} Science Bridges ({syn['panchromatic_bridge_cells_total']} Cells), 27 Archives A-Z, AA & 613-Star Synthesis", fontsize=11.1, fontweight="bold", y=0.97)
    _save(fig, fig_dir, "fig102_d101_bridge_synthesis_d079_d101.png")


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

    bundle = json.loads(gzip.decompress((ws / "bounded_inputs" / "d101_bounded_bundle.json.gz").read_bytes()).decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig97_alma_gap_closure(res_dir, fig_dir)
    fig98_alma_spatial_spectral_vetoes(res_dir, bundle, az, fig_dir)
    fig99_eso_espresso_harps(res_dir, orb_json, az, fig_dir)
    fig100_comb_drift_v59(res_dir, fig_dir)
    fig101_panchromatic_613stars(res_dir, ws, bundle, fig_dir)
    fig102_bridge_synthesis(res_dir, fig_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
