#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D107 (V6.5) Six-Figure Publication Suite (fig133-fig138, 240 DPI, metadata={}):
  - fig133: IceCube 10-Yr (IC40-IC86_VII, 0.1 TeV-10 PeV) 54-Target Neutrino Flux & L_nu_iso Survey
  - fig134: Swift BAT 157m (14-195 keV, 30 Targets) & Swift XRT PC/WT (0.3-10 keV, 20 Targets) Survey
  - fig135: Quad-Messenger 16 Cyg B Exoplanet Bridge, AGN/CV Controls, & Multimessenger Candidate Funnel
  - fig136: Orbits #187-#192 (ESPRESSO/HARPS/NIRPS), 4-Gen Funnel, & 84-Campaign DRIFT_V65 + COMB_DRIFT_V65
  - fig137: 28-Suite Calibration Scorecard (6,051 Trials -> 74,232 Cumulative; V6.5 IceCube/BAT/XRT >= 98.75%)
  - fig138: Global 904-Star Quad-Messenger Synthesis (60.845 EM Octaves + TeV-PeV Neutrinos, 145 Bridges, 262 <10 pc)
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
    "legend.fontsize": 6.5,
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
    ax.set_xticklabels(lbls, fontsize=6.4)
    ax.set_ylim(0, 120)
    ax.set_ylabel("Pass / Rejection Rate (%)")
    ax.set_title(title)
    for b, k in zip(bars, keys):
        p, t = cls_counts[k]
        ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=7.0, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.25)


def fig133_icecube_10yr(res_dir: Path, bundle: dict[str, Any], az: Any, det: Any, fig_dir: Path) -> None:
    ic = _read_csv(res_dir, "ICECUBE_10YR_54TARGETS.csv")
    cal = _read_csv(res_dir, "CALIBRATION_V65_ICECUBE_NEUTRINO_240.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Differential Neutrino Flux Sensitivity Curves Phi_nu,lim(E)
    exp_map = {e["star"]: e for e in bundle["exposures"] if e["instrument"] == "ICECUBE_10YR"}
    focus_a = [
        ("16CYGB",   "#1b9e77", "-",  2.2, "16 Cyg B (Quad-Messenger Bridge, dec=+50.5)"),
        ("HD165341", "#2b8cbe", "-",  1.9, "70 Oph / HD 165341 (<10 pc, dec=+2.5)"),
        ("47UMA",    "#7570b3", "--", 1.7, "47 UMa (Radio+Orbital Bridge, dec=+40.4)"),
        ("NGC1068",  "#b30000", "-",  1.8, "NGC 1068 (Seyfert-2 Control, dec=-0.01)"),
        ("TXS0506",  "#d95f02", ":",  1.8, "TXS 0506+056 (Blazar Control, dec=+5.7)"),
        ("MRK421",   "#636363", "-.", 1.6, "Mrk 421 (Blazar Control, dec=+38.2)"),
    ]
    for st, col, ls, lw, lbl in focus_a:
        ex = exp_map.get(st)
        if not ex:
            continue
        spec_d = {
            "valid": True, "e_gev": az._decode_arr_any(ex["e_gev_c"]),
            "cnt_a": az._decode_arr_any(ex["cnt_a_c"]), "cnt_b": az._decode_arr_any(ex["cnt_b_c"]),
            "off_dec_ring": az._decode_arr_any(ex["off_dec_ring_c"]), "alpha_ring": az._decode_arr_any(ex["alpha_ring_c"]),
            "aeff_e_gev": az._decode_arr_any(ex["aeff_e_gev_c"]), "aeff_cm2_exposure_s": az._decode_arr_any(ex["aeff_exp_c"]),
            "t_live_s": float(ex["t_live_s"]), "split_p_a": float(ex["split_p_a"]),
        }
        res_s = det.scan_icecube_10yr_v65(spec_d, star=st, dist_pc=float(ex["dist_pc"]), role=ex["role"], dp_id=ex["dp_id"])
        pts = sorted((float(u["energy_tev"]), float(u["phi_nu_lim_cm2_s"])) for u in res_s["band_best_ul"].values())
        ax1.plot([p[0] for p in pts], [p[1] for p in pts], ls=ls, marker="o", ms=4.5, lw=lw, color=col, label=lbl)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Neutrino Energy E_nu (TeV)")
    ax1.set_ylabel("6-sigma Fluence-Rate Upper Limit Phi_nu,lim (cm^-2 s^-1)")
    ax1.set_title("A. IceCube 10-Yr (3,577.9 Live-Days) Point-Source Neutrino Limits")
    ax1.legend(loc="upper right", fontsize=6.0, frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Declination vs Neutrino Isotropic Luminosity Limit L_nu,iso Across All 54 Targets
    groups = [
        ("QM",   [r for r in ic if r["star"] == "16CYGB"], "#1b9e77", "*", 140, "16 Cyg B (Quad-Messenger)"),
        ("S10",  [r for r in ic if r["role"] == "SCIENCE" and r["within_10pc"] == "True"], "#2b8cbe", "o", 38, "Science <10 pc (18 + 6 bridges)"),
        ("SBR",  [r for r in ic if r["role"] == "SCIENCE" and r["within_10pc"] == "False" and r["star"] != "16CYGB"], "#7570b3", "^", 40, "Science Exoplanet Hosts / Bridges"),
        ("CTL",  [r for r in ic if r["role"] == "CONTROL"], "#b30000", "D", 55, "Control AGNs (NGC 1068, Mrk 421, TXS 0506)"),
    ]
    for _, sub, col, mk, sz, lbl in groups:
        if sub:
            ax2.scatter([float(r["dec_deg"]) for r in sub], [float(r["l_nu_iso_mw"]) for r in sub], s=sz, color=col, marker=mk, edgecolor="black", lw=0.5, alpha=0.90, label=lbl, zorder=4)
    for st_a, dx, dy in [("16CYGB", 6, 9), ("HD165341", 12, -10), ("ROSS128", 10, 26), ("NGC1068", 6, -12), ("TXS0506", 6, -12)]:
        m_a = [r for r in ic if r["star"] == st_a]
        if m_a:
            r0 = m_a[0]
            ax2.annotate(r0["star"], (float(r0["dec_deg"]), float(r0["l_nu_iso_mw"])), xytext=(dx, dy), textcoords="offset points", fontsize=6.0, fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.6, color="#4a5568") if st_a in ("ROSS128", "HD165341") else None)
    ax2.set_yscale("log")
    ax2.set_ylim(1.2e14, 5.0e32)
    ax2.set_xlabel("Declination delta (deg)")
    ax2.set_ylabel("6-sigma Isotropic Neutrino Luminosity L_nu,iso (MW)")
    ax2.set_title("B. Declination-Dependent L_nu,iso (54 Targets; Min <10 pc = 4.68e14 MW)")
    ax2.legend(loc="center right", fontsize=6.0, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Calibration Suite V65A
    p_ic = sum(int(r["passed"]) for r in cal)
    _cal_bars(ax3, cal, f"C. IceCube Neutrino Calibration ({p_ic}/{len(cal)} = {100.0*p_ic/len(cal):.2f}%)", {
        "CLEAN_NEUTRINO_LINE": "Clean nu\nLine (80)",
        "TEMPORAL_OR_RING_VETO": "Split/Ring\nVeto (40)",
        "ATMOSPHERIC_THRESHOLD_VETO": "Atm/Knee\nVeto (40)",
        "POWERLAW_ASTRO_NULL": "Astro PL\nNull (40)",
        "BROAD_OR_1BIN_VETO": "Broad/1-Bin\nVeto (40)",
    })

    # Panel D: On-Cone (1.5 deg) vs Scaled Off-RA Ring Background Counts
    on_c = [int(r["n_cone_1p5deg"]) for r in ic]
    bg_c = [float(r["alpha_ring"]) * int(r["n_dec_ring"]) for r in ic]
    cols_d = ["#b30000" if r["role"] == "CONTROL" else ("#1b9e77" if r["star"] == "16CYGB" else "#2b8cbe") for r in ic]
    szs_d = [85 if r["role"] == "CONTROL" or r["star"] == "16CYGB" else 28 for r in ic]
    ax4.scatter(bg_c, on_c, s=szs_d, c=cols_d, edgecolor="black", lw=0.45, alpha=0.88, zorder=4)
    lo_xy, hi_xy = 95.0, 415.0
    ax4.plot([lo_xy, hi_xy], [lo_xy, hi_xy], "--", color="black", lw=1.2, label="1:1 Null Background Expectation")
    for st_l, dx, dy in [("NGC1068", -105, 8), ("TXS0506", -100, -14), ("16CYGB", -82, 22), ("MRK421", 8, -12)]:
        rr = next((x for x in ic if x["star"] == st_l), None)
        if rr:
            bx = float(rr["alpha_ring"]) * int(rr["n_dec_ring"])
            by = int(rr["n_cone_1p5deg"])
            ax4.annotate(f"{st_l} ({by} vs {bx:.1f})", (bx, by), xytext=(dx, dy), textcoords="offset points", fontsize=6.0, fontweight="bold", arrowprops=dict(arrowstyle="->", lw=0.7, color="#2d3748"))
    ax4.set_xlim(lo_xy, hi_xy)
    ax4.set_ylim(lo_xy, hi_xy)
    ax4.set_xlabel("Expected Same-Declination Ring Background (alpha * N_ring)")
    ax4.set_ylabel("Observed 1.5-deg Cone Muon-Neutrino Events (N_on)")
    ax4.set_title("D. 10-Yr Cone vs Ring Counts Across 54 Targets (21 Raw -> 0 Qual -> 0 ETI)")
    ax4.legend(loc="upper left", fontsize=6.6, frameon=True)
    ax4.grid(True, alpha=0.22)

    fig.suptitle("Phase D107 (V6.5A): IceCube 10-Yr All-Sky Neutrino Point-Source Search (54 Targets; 1,134,450 Events; 0 Verified ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig133_d107_icecube_10yr_neutrino_limits.png")


def fig134_swift_bat_xrt(res_dir: Path, bundle: dict[str, Any], az: Any, det_mod: Any, fig_dir: Path) -> None:
    bat = _read_csv(res_dir, "SWIFT_BAT_157M_30TARGETS.csv")
    xrt = _read_csv(res_dir, "SWIFT_XRT_20TARGETS.csv")
    c_bat = _read_csv(res_dir, "CALIBRATION_V65_SWIFT_BAT_240.csv")
    c_xrt = _read_csv(res_dir, "CALIBRATION_V65_SWIFT_XRT_180.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Swift BAT 157m Top-20 Tightest Physical Flux Limits (or all 30 sorted)
    bat_s = sorted(bat, key=lambda r: float(r["flux_lim_erg_cm2_s"]))
    y1 = np.arange(len(bat_s))
    fl_b = [float(r["flux_lim_erg_cm2_s"]) for r in bat_s]
    cols_b = ["#1b9e77" if r["role"] == "SCIENCE" else "#b30000" for r in bat_s]
    ax1.barh(y1, fl_b, color=cols_b, edgecolor="black", lw=0.35, alpha=0.90)
    ax1.set_yticks(y1)
    ax1.set_yticklabels([f"{r['star']} ({r['best_band_id']})" for r in bat_s], fontsize=5.0)
    ax1.set_xscale("log")
    ax1.set_xlim(min(fl_b) * 0.7, max(fl_b) * 6.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("6-sigma Hard X-Ray Line Flux Limit F_lim (erg cm^-2 s^-1; 14-195 keV)")
    ax1.set_title("A. Swift-BAT 157-Month 30-Target Survey (Green=Science, Red=Control)")
    for yi, r in enumerate(bat_s):
        if int(r["n_qualified_pre_stage2"]) > 0 or yi in (0, 2, len(bat_s) - 1):
            tag = " [S2-triage]" if int(r["n_qualified_pre_stage2"]) > 0 else ""
            ax1.text(float(r["flux_lim_erg_cm2_s"]) * 1.07, yi, f"{float(r['flux_lim_erg_cm2_s']):.2e}{tag}", va="center", fontsize=4.7, fontweight="bold")
    ax1.grid(True, axis="x", which="both", alpha=0.22)

    # Panel B: Swift XRT 20 Targets F_lim vs Distance (PC vs WT)
    for xm, mk, sz in [("PC", "o", 48), ("WT", "^", 62)]:
        sub = [r for r in xrt if r["xrt_mode"] == xm]
        ax2.scatter(
            [float(r["dist_pc"]) for r in sub],
            [float(r["flux_lim_erg_cm2_s"]) for r in sub],
            s=sz, c=["#2b8cbe" if r["role"] == "SCIENCE" else "#d95f02" for r in sub],
            marker=mk, edgecolor="black", lw=0.55, alpha=0.92,
            label=f"XRT {xm} ({len(sub)}: Sci/Ctrl)", zorder=4,
        )
    for st_x, dx, dy in [
        ("TRAPPIST1", 6, -6), ("PROXIMACEN", 6, -4), ("BARNARDSSTAR", -22, 18),
        ("RTCRU", 10, 12), ("GKPER", 6, -9), ("IIPEG", 8, 6), ("MRK421", -52, -12), ("TXS0506", -66, -12),
    ]:
        rr = next((r for r in xrt if r["star"] == st_x), None)
        if rr:
            ax2.annotate(f"{st_x} ({rr['xrt_mode']})", (float(rr["dist_pc"]), float(rr["flux_lim_erg_cm2_s"])), xytext=(dx, dy), textcoords="offset points", fontsize=5.8, fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.6, color="#4a5568") if st_x in ("BARNARDSSTAR", "RTCRU") else None)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_ylim(2.2e-14, 1.8e-11)
    ax2.set_xlabel("Distance d (pc)")
    ax2.set_ylabel("6-sigma Soft X-Ray Line Flux Limit F_lim (erg cm^-2 s^-1)")
    ax2.set_title("B. Swift-XRT 0.3-10 keV PC/WT Limits (20 Targets; 0 Pre-S2 -> 0 ETI)")
    ax2.legend(loc="lower right", fontsize=6.4, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Paired BAT + XRT Calibration Performance
    p_b = sum(int(r["passed"]) for r in c_bat)
    p_x = sum(int(r["passed"]) for r in c_xrt)
    cats_c = [
        ("BAT Clean\nLine (80)", sum(int(r["passed"]) for r in c_bat if r["class"] == "CLEAN_BAT_HARDX_LINE"), 80),
        ("BAT Half-\nMission (40)", sum(int(r["passed"]) for r in c_bat if "HALF" in r["class"]), 40),
        ("BAT W/Pb\nEdge (40)", sum(int(r["passed"]) for r in c_bat if "BACKGROUND" in r["class"]), 40),
        ("BAT Broad\nHump (40)", sum(int(r["passed"]) for r in c_bat if "HUMP" in r["class"]), 40),
        ("XRT Clean\nLine (60)", sum(int(r["passed"]) for r in c_xrt if r["class"] == "CLEAN_XRT_BEACON"), 60),
        ("XRT Split/\nSpat (30)", sum(int(r["passed"]) for r in c_xrt if "SPLIT" in r["class"]), 30),
        ("XRT Coronal\nAtlas (30)", sum(int(r["passed"]) for r in c_xrt if "CORONAL" in r["class"]), 30),
        ("XRT Broad/\n1-Bin (30)", sum(int(r["passed"]) for r in c_xrt if "BROAD" in r["class"]), 30),
    ]
    x3 = np.arange(len(cats_c))
    pct3 = [100.0 * p / max(1, t) for _, p, t in cats_c]
    cols3 = ["#2b8cbe"] * 4 + ["#7570b3"] * 4
    bars3 = ax3.bar(x3, pct3, color=cols3, edgecolor="black", lw=0.65, width=0.65)
    ax3.set_xticks(x3)
    ax3.set_xticklabels([c[0] for c in cats_c], fontsize=5.8)
    ax3.set_ylim(0, 122)
    ax3.set_ylabel("Pass / Rejection Rate (%)")
    ax3.set_title(f"C. V6.5 X-Ray Calibrations: BAT {p_b}/{len(c_bat)} ({100*p_b/len(c_bat):.2f}%) | XRT {p_x}/{len(c_xrt)} ({100*p_x/len(c_xrt):.2f}%)")
    for b, (_, p, t) in zip(bars3, cats_c):
        ax3.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2.0, f"{p}/{t}", ha="center", va="bottom", fontsize=6.4, fontweight="bold")
    ax3.grid(True, axis="y", alpha=0.25)

    # Panel D: Broadband 0.3-195 keV Dual-Instrument BAT+XRT SED Limits Across 8 New & Control Bridges
    eirp = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D107.csv")
    dual_stars = ["RTCRU", "GKPER", "V1223SGR", "V709CAS", "NGC1068", "MRK421", "3C273", "CENA"]
    pal_d = ["#1b9e77", "#2b8cbe", "#7570b3", "#d95f02", "#b30000", "#e7298a", "#66a61e", "#4a5568"]
    for idx_s, st in enumerate(dual_stars):
        pts = sorted(
            (det_mod.KEV_ANGSTROM / float(r["wave_bary_a"]), float(r["flux_lim_erg_cm2_s"]))
            for r in eirp if r["star"] == st and r["instrument"] in ("SWIFT_BAT", "SWIFT_XRT")
        )
        if pts:
            ax4.plot([p[0] for p in pts], [p[1] for p in pts], "-o", ms=3.8, lw=1.35, color=pal_d[idx_s % len(pal_d)], label=st)
    ax4.axvline(12.0, ls=":", color="black", alpha=0.5, label="XRT / BAT Interface (0.3-10 vs 14-195 keV)")
    ax4.set_xscale("log")
    ax4.set_yscale("log")
    ax4.set_xlabel("Photon Energy E (keV)")
    ax4.set_ylabel("6-sigma Narrow-Line Flux Limit F_lim (erg cm^-2 s^-1)")
    ax4.set_title("D. Dual Swift XRT + BAT Broadband X-Ray Limits (0.3-195 keV; 8 Bridges)")
    ax4.legend(loc="upper left", fontsize=5.8, ncol=2, frameon=True)
    ax4.grid(True, which="both", alpha=0.22)

    fig.suptitle("Phase D107 (V6.5B/C): Swift-BAT 157-Month (30 Targets) & Swift-XRT PC/WT CCD (20 Targets) Broadband X-Ray Survey (0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig134_d107_swift_bat_xrt_xray_bridges.png")


def fig135_quad_messenger(res_dir: Path, det_mod: Any, fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]
    br = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    qm = _read_csv(res_dir, "QUAD_MESSENGER_16CYGB_AND_CONTROLS_D107.csv")
    mm = _read_csv(res_dir, "V6_5_MULTIMESSENGER_CANDIDATE_LEDGER.csv")
    eirp = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D107.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: 16 Cyg B Quad-Messenger Broadband Energy Flux Panorama (1.4 GHz -> Opt/NIR/UV -> IceCube 0.5-1000 TeV)
    em_16 = sorted((float(r["wave_um"]), float(r["flux_lim_erg_cm2_s"])) for r in br if r["star"] == "16CYGB" and r.get("wave_um") and r.get("flux_lim_erg_cm2_s"))
    ev_16_eV = [det_mod.KEV_ANGSTROM / (w * 1e4) * 1e3 for w, _ in em_16]
    # Include 1.42 GHz L-band radio energy scale (~5.87e-6 eV) if radio point present, else convert from wave_um
    ax1.scatter(ev_16_eV, [f for _, f in em_16], s=42, color="#2b8cbe", edgecolor="black", lw=0.5, label=f"16CYGB EM Bridges ({len(em_16)} Bands: UV/Opt/IR/Radio)")
    nu_16 = sorted((float(r["energy_tev"]) * 1e12, float(r["flux_lim_erg_cm2_s"])) for r in qm if r["star"] == "16CYGB" and r["messenger"] == "NEUTRINO_ICECUBE_10YR")
    ax1.plot([p[0] for p in nu_16], [p[1] for p in nu_16], "-*", ms=9, lw=1.9, color="#1b9e77", label="16CYGB IceCube 10-Yr Neutrinos (0.5 TeV-1 PeV)")
    ax1.axvspan(1.5, 3.5, color="#fefcbf", alpha=0.65, label="Optical TESS + Echelle Monitoring Band")
    ax1.annotate("IC_50TEV:\n4.53e-12 erg/cm2/s\nL_nu=2.42e16 MW", (5.0e13, 4.529e-12), xytext=(-85, 22), textcoords="offset points", fontsize=6.1, fontweight="bold", arrowprops=dict(arrowstyle="->", lw=0.8))
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Particle / Photon Energy E (eV; Radio 5.9e-6 eV -> Optical 2 eV -> Neutrino 1 PeV)")
    ax1.set_ylabel("6-sigma Narrow-Feature Flux Limit F_lim (erg cm^-2 s^-1)")
    ax1.set_title("A. First Quad-Messenger Exoplanet Bridge: 16 Cyg B (HD 186427, 21.13 pc)")
    ax1.legend(loc="lower right", fontsize=6.0, frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Differential Neutrino Energy Flux E * Phi_nu,lim Across Benchmark Targets
    ic_all = _read_csv(res_dir, "ICECUBE_10YR_54TARGETS.csv")
    # Plot NGC1068, TXS0506, MRK421, 16CYGB from QUAD_MESSENGER CSV (plus 54-star distribution at best grid point)
    for st_b, col_b, mk_b in [("16CYGB", "#1b9e77", "*"), ("NGC1068", "#b30000", "D"), ("TXS0506", "#d95f02", "^"), ("MRK421", "#7570b3", "s")]:
        pts_b = sorted((float(r["energy_tev"]), float(r["energy_tev"]) * float(r["phi_nu_lim_cm2_s"])) for r in qm if r["star"] == st_b and r["messenger"] == "NEUTRINO_ICECUBE_10YR")
        ax2.plot([p[0] for p in pts_b], [p[1] for p in pts_b], marker=mk_b, ms=5.5, lw=1.6, color=col_b, label=f"{st_b}")
    ax2.scatter([float(r["best_energy_tev"]) for r in ic_all], [float(r["e_phi_nu_lim_tev_cm2_s"]) for r in ic_all], s=18, color="#4a5568", alpha=0.60, zorder=3, label="Best-Band Point Across All 54 IceCube Targets")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Neutrino Energy E_nu (TeV)")
    ax2.set_ylabel("6-sigma Energy Flux E_nu * Phi_nu,lim (TeV cm^-2 s^-1)")
    ax2.set_title("B. Quad-Messenger & Control Energy-Flux Sensitivity (IceCube 0.5-1000 TeV)")
    ax2.legend(loc="upper right", fontsize=6.2, frameon=True)
    ax2.grid(True, which="both", alpha=0.22)

    # Panel C: Multimessenger Candidate Funnel & Gate Vetoes
    n_ic_raw = sum(1 for r in mm if r["instrument"] == "ICECUBE_10YR")
    n_bat_raw = sum(1 for r in mm if r["instrument"] == "SWIFT_BAT")
    n_xrt_raw = sum(1 for r in mm if r["instrument"] == "SWIFT_XRT")
    n_bat_pre = sum(1 for r in mm if r["instrument"] == "SWIFT_BAT" and r["qualified_v65"] == "True")
    cats_m = [
        ("IceCube Raw\nPeaks (21)", n_ic_raw, "#2b8cbe"),
        ("IceCube Pre-S2\nSurvivors", 0, "#1b9e77"),
        ("BAT Raw\nPeaks (38)", n_bat_raw, "#d95f02"),
        ("BAT Pre-S2\nHumps (7)", n_bat_pre, "#b30000"),
        ("XRT Raw\nNMS Peaks (56*)", n_xrt_raw, "#7570b3"),
        ("XRT Pre-S2\nSurvivors", 0, "#1b9e77"),
        ("Total D107 MM\nVerified ETI", sum(int(r["verified_eti"]) for r in mm), "#1b9e77"),
    ]
    bars_m = ax3.bar(np.arange(len(cats_m)), [c[1] for c in cats_m], color=[c[2] for c in cats_m], edgecolor="black", lw=0.7, width=0.62)
    ax3.set_xticks(np.arange(len(cats_m)))
    ax3.set_xticklabels([c[0] for c in cats_m], fontsize=6.1)
    ax3.set_ylim(0, max(c[1] for c in cats_m) + 12)
    ax3.set_ylabel("Ledger Candidate Count")
    ax3.set_title("C. Multimessenger Triage Funnel (115 Ledger Rows* -> 7 BAT -> 0 Verified ETI)")
    for b, (_, val, _) in zip(bars_m, cats_m):
        ax3.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 1.0, str(val), ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    ax3.text(0.98, 0.90, "*XRT triggered 63 raw local extrema\nmerged to 56 NMS ledger entries.", transform=ax3.transAxes, ha="right", va="top", fontsize=5.8, bbox=dict(boxstyle="round,pad=0.3", fc="#f7fafc", ec="#cbd5e0"))
    ax3.grid(True, axis="y", alpha=0.25)

    # Panel D: Best 10-m Formal EM EIRP Bounds Across D107 EM Instruments (BAT, XRT, ESPRESSO, HARPS, NIRPS)
    best_em = {}
    for r in eirp:
        ik = r["instrument"]
        pk = float(r["p_beam_10m_kw"])
        if ik not in best_em or pk < best_em[ik][0]:
            best_em[ik] = (pk, r["star"], r["band_id"])
    inst_ord = sorted(best_em.keys(), key=lambda k: best_em[k][0])
    y4 = np.arange(len(inst_ord))
    vals4 = [best_em[k][0] for k in inst_ord]
    ax4.barh(y4, vals4, color=["#7570b3", "#2b8cbe", "#1b9e77", "#d95f02", "#b30000"][:len(inst_ord)], edgecolor="black", lw=0.7, height=0.58)
    ax4.set_yticks(y4)
    ax4.set_yticklabels([f"{k}\n({best_em[k][1]})" for k in inst_ord], fontsize=6.8)
    ax4.set_xscale("log")
    ax4.set_xlim(min(vals4) * 0.2, max(vals4) * 150.0)
    ax4.invert_yaxis()
    for yi, k in enumerate(inst_ord):
        v, st_i, bid_i = best_em[k]
        ax4.text(v * 1.25, yi, f"{_fmt_power_kw(v)} [{bid_i}]", va="center", fontsize=6.6, fontweight="bold")
    ax4.set_xlabel("Best Formal 10-m EM EIRP Limit (kW; IceCube Excluded by Zero-EM Policy)")
    ax4.set_title("D. D107 Best Formal 10-m EM Limits (C12 EM Closure max_rel_err = 0.00e+00)")
    ax4.grid(True, axis="x", which="both", alpha=0.22)

    fig.suptitle("Phase D107 (V6.5): 16 Cyg B First Quad-Messenger Exoplanet Bridge, Controls & Multimessenger Triage (0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig135_d107_quad_messenger_16cygb_and_controls.png")


def fig136_orbits_and_84drift(res_dir: Path, orb_json: dict[str, Any], det_mod: Any, fig_dir: Path) -> None:
    o6 = _read_csv(res_dir, "ORBITAL_CAMPAIGN_RESULTS_6_D107.csv")
    fg = _read_csv(res_dir, "FOUR_GEN_BENCHMARK_D107.csv")
    ek84 = _read_csv(res_dir, "DRIFT_V65_ECCENTRIC_KEPLERIAN_84CAMPAIGNS.csv")
    cd84 = _read_csv(res_dir, "COMB_DRIFT_V65_84CAMPAIGNS.csv")
    sum_raw = json.loads((res_dir / "SUMMARY.json").read_text())["raw_hits_and_triage"]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.0, 10.8))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Live Orbital Campaigns #187-#192
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
        ax1.plot(ph, vr_ms, lw=1.65, color=pal[idx_o % len(pal)], label=f"#{r['campaign_index']} {st} ({r['instrument'].replace('ESO_', '')}, P={p_d:.1f}d, Kp={kp*1e3:.1f}m/s)")
    pad_y = max(2.0, 0.24 * (ymax_v - ymin_v))
    ax1.set_ylim(ymin_v - 0.55 * pad_y, ymax_v + 1.85 * pad_y)
    ax1.set_xlabel("Orbital Phase phi")
    ax1.set_ylabel("Planetary Keplerian RV (m/s)")
    ax1.set_title("A. ESO ESPRESSO + HARPS + NIRPS Orbits #187-#192 (30 Spectra, CONJ+INTM+QUAD)")
    ax1.legend(loc="upper right", fontsize=6.0, frameon=True)
    ax1.grid(True, alpha=0.22)

    # Panel B: 4-Gen Optical/NIR Benchmark Funnel Across ESPRESSO, HARPS, NIRPS
    stages = [("G1", "g1_seeds"), ("G2", "g2_pass"), ("G3", "g3_pass"), ("G45", "g45_pass"), ("G6", "g6_pass"), ("G7", "g7_pass"), ("G8", "g8_pass"), ("ETI", "stage2_verified_eti")]
    x2 = np.arange(len(stages))
    width_b = 0.25
    cols_fg = {"ESO_ESPRESSO": "#2b8cbe", "ESO_HARPS": "#1b9e77", "ESO_NIRPS": "#d95f02"}
    for idx_i, rf in enumerate(fg):
        vals_f = [int(rf[k]) for _, k in stages]
        ax2.bar(x2 + (idx_i - 1) * width_b, vals_f, width=width_b, color=cols_fg.get(rf["instrument"], "#636363"), edgecolor="black", lw=0.5, label=f"{rf['instrument']} ({rf['n_exposures']} exp)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels([s[0] for s in stages], fontsize=7.2)
    ax2.set_yscale("symlog", linthresh=2.0)
    ax2.set_ylabel("Survivor Count (Symlog)")
    ax2.set_title(f"B. 4-Generation Screening Across Orbits #187-#192 ({sum_raw['optical_4gen_g1_seeds']} G1 -> 0 G8 -> 0 ETI)")
    ax2.legend(loc="upper right", fontsize=6.5, frameon=True)
    ax2.grid(True, axis="y", alpha=0.22)

    # Panel C: All 84 Cumulative DRIFT_V65 Campaigns
    x84 = np.arange(len(ek84))
    ax3.bar(x84, [int(r["n_trajectories_evaluated"]) for r in ek84], color="#cbd5e0", edgecolor="#718096", lw=0.4, label="Kepler Trajectories")
    ax3.bar(x84, [int(r["raw_coherent_survivors"]) for r in ek84], color="#2b8cbe", edgecolor="black", lw=0.4, label=f"Raw Survivors ({sum_raw['drift_v65_84campaigns_raw_survivors']:,})")
    ax3.bar(x84, [int(r["stage2_verified_eti"]) for r in ek84], color="#1b9e77", label="Verified ETI (0/84)")
    ax3.set_yscale("log")
    ax3.set_ylim(0.8, max(int(r["n_trajectories_evaluated"]) for r in ek84) * 3.0)
    ax3.set_xlabel("Campaign Order (1-6 D107, 7-12 D106, ..., 79-84 D094)")
    ax3.set_ylabel("Count (Log Scale)")
    pix_b = sum_raw["drift_v65_84campaigns_pixel_integrals"] / 1e9
    ax3.set_title(f"C. 84-Campaign DRIFT_V65 ({sum_raw['drift_v65_84campaigns_trajectories']:,} Traj / {pix_b:.2f}B Pix -> 0 ETI)")
    ax3.legend(loc="upper right", fontsize=6.5, frameon=True)
    ax3.grid(True, axis="y", which="both", alpha=0.22)

    # Panel D: All 84 Cumulative COMB_DRIFT_V65 Campaigns
    raw_cd = np.asarray([int(r["comb_raw_candidates"]) for r in cd84])
    qual_cd = np.asarray([int(r["comb_qualified_v65"]) for r in cd84])
    ax4.plot(x84, raw_cd, "-o", ms=2.4, color="#d95f02", lw=1.05, label=f"Raw Comb-Drift Candidates ({sum_raw['comb_drift_v65_84campaigns_raw_candidates']:,})")
    ax4.plot(x84, qual_cd, "-s", ms=2.4, color="#7570b3", lw=1.05, label=f"Pre-S2 Qualified ({sum_raw['comb_drift_v65_84campaigns_qualified_pre_stage2']})")
    ax4.plot(x84, np.zeros_like(x84), "--", color="#1b9e77", lw=1.5, label="Stage-2 Verified ETI (0/84)")
    ax4.set_yscale("symlog", linthresh=5.0)
    ax4.set_xlabel("Campaign Order (#1-#84 Across D094-D107)")
    ax4.set_ylabel("Comb Candidate Count (Symlog)")
    ax4.set_title(f"D. 84-Campaign COMB_DRIFT_V65 ({sum_raw['comb_drift_v65_84campaigns_trajectories']:,} Traj -> 0 ETI)")
    ax4.legend(loc="upper right", fontsize=6.5, frameon=True)
    ax4.grid(True, alpha=0.22)

    fig.suptitle(f"Phase D107 (V6.5): Orbits #187-#192 & 84-Campaign Coherent DRIFT_V65 + COMB_DRIFT_V65 ({pix_b:.2f}B Pixel Integrals; 0 ETI)", fontsize=10.3, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig136_d107_orbital_campaigns_187_192_and_84drift.png")


def fig137_calibration_28suites(res_dir: Path, fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    cal_sum = s_json["synthetic_calibration_6051_trials"]
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]
    suites = cal_sum["suites"]
    band_comp = _read_csv(res_dir, "CALIBRATION_COMPLETENESS_BY_BAND.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.5, 11.2))
    fig.subplots_adjust(wspace=0.35, hspace=0.34)

    # Panel A: All 28 Calibration Suites Horizontal Scorecard
    s_names = list(suites.keys())
    s_pcts = [100.0 * suites[k]["passed"] / max(1, suites[k]["total"]) for k in s_names]
    short_s = [
        k.replace("CALIBRATION_V65_", "V6.5 ")
        .replace("CALIBRATION_V64_", "V6.4 ")
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
    y1 = np.arange(len(s_names))
    bar_c = ["#1b9e77" if "V6.5" in s else ("#b30000" if "V6.4" in s else "#2b8cbe") for s in short_s]
    ax1.barh(y1, s_pcts, color=bar_c, edgecolor="black", lw=0.45)
    ax1.axvline(95.0, ls="--", color="black", lw=1.0, label="95% Required Threshold")
    ax1.set_yticks(y1)
    ax1.set_yticklabels(short_s, fontsize=4.6)
    ax1.set_xlim(92.0, 102.0)
    ax1.invert_yaxis()
    for yi, k in enumerate(s_names):
        p, t = suites[k]["passed"], suites[k]["total"]
        pct_i = s_pcts[yi]
        ax1.text(pct_i - 0.25, yi, f"{p}/{t} ({pct_i:.1f}%)", va="center", ha="right", fontsize=4.5, color="white", fontweight="bold")
    ax1.set_xlabel("Suite Pass Rate (%)")
    ax1.set_title(f"A. All 28 D107 Suites ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; All >=97.5%)")
    ax1.legend(loc="lower left", fontsize=6.4, frameon=True)
    ax1.grid(True, axis="x", alpha=0.25)

    # Panel B: Zoom on the 3 New V6.5 Calibration Suites Breakdown
    v65_keys = [
        ("ICECUBE_NEUTRINO_240", "V6.5A IceCube\n(237/240 = 98.75%)", "#1b9e77"),
        ("SWIFT_BAT_240",        "V6.5B Swift BAT\n(239/240 = 99.58%)", "#d95f02"),
        ("SWIFT_XRT_180",        "V6.5C Swift XRT\n(178/180 = 98.89%)", "#7570b3"),
    ]
    x2 = np.arange(len(v65_keys))
    vals_2 = [100.0 * suites[f"CALIBRATION_V65_{k}"]["passed"] / suites[f"CALIBRATION_V65_{k}"]["total"] for k, _, _ in v65_keys]
    bars2 = ax2.bar(x2, vals_2, color=[c for _, _, c in v65_keys], edgecolor="black", lw=0.75, width=0.52)
    ax2.axhline(95.0, ls="--", color="red", lw=1.1, label="95.0% Certification Gate")
    ax2.set_xticks(x2)
    ax2.set_xticklabels([l for _, l, _ in v65_keys], fontsize=7.4)
    ax2.set_ylim(88.0, 103.5)
    ax2.set_ylabel("Pass / Veto Accuracy (%)")
    ax2.set_title("B. New D107 V6.5 Calibration Suites (654/660 = 99.09%)")
    for b, v in zip(bars2, vals_2):
        ax2.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 0.35, f"{v:.2f}%", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
    ax2.legend(loc="lower right", fontsize=6.6, frameon=True)
    ax2.grid(True, axis="y", alpha=0.25)

    # Panel C: Injection-Recovery Band Completeness (540/540 Across Optical & ALMA Bands)
    yb = np.arange(len(band_comp))
    cp_b = [100.0 * float(r["completeness_p"]) for r in band_comp]
    ax3.barh(yb, cp_b, color="#2b8cbe", edgecolor="black", lw=0.45)
    ax3.set_yticks(yb)
    ax3.set_yticklabels([f"{r['instrument'].replace('ESO_', '')}:{r['band_id']}" for r in band_comp], fontsize=4.8)
    ax3.set_xlim(85.0, 104.0)
    ax3.invert_yaxis()
    for yi, r in enumerate(band_comp):
        ax3.text(99.5, yi, f"{r['n_pass']}/{r['n_trials']}", va="center", ha="right", fontsize=4.7, color="white", fontweight="bold")
    ax3.set_xlabel("Completeness (%)")
    ax3.set_title("C. INJECTION_RECOVERY_540 Completeness by Spectral Band (540/540 = 100%)")
    ax3.grid(True, axis="x", alpha=0.25)

    # Panel D: Cumulative Trials Progression Toward 74,232 Trials
    milestones = [
        ("D092\nV5.0", 9879),
        ("D097\nV5.5", 22992),
        ("D101\nV5.9", 40881),
        ("D103\nV6.1", 52281),
        ("D105\nV6.3", 62790),
        ("D106\nV6.4", 68181),
        ("D107\nV6.5", syn["total_calibration_trials_d079_d107"]),
    ]
    xm = np.arange(len(milestones))
    ym = [m[1] for m in milestones]
    ax4.plot(xm, ym, "-D", color="#1b9e77", lw=2.0, ms=6.5, markeredgecolor="black")
    ax4.fill_between(xm, ym, color="#1b9e77", alpha=0.14)
    ax4.set_xticks(xm)
    ax4.set_xticklabels([m[0] for m in milestones], fontsize=7.0)
    ax4.set_ylim(0, max(ym) * 1.15)
    ax4.set_ylabel("Cumulative Synthetic Calibration Trials")
    ax4.set_title(f"D. Cumulative Calibration Verification Trajectory ({syn['total_calibration_trials_d079_d107']:,} Total Trials)")
    for xi, yi in zip(xm, ym):
        ax4.annotate(f"{yi:,}", (xi, yi), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=6.6, fontweight="bold")
    ax4.grid(True, alpha=0.25)

    fig.suptitle(f"Phase D107 (V6.5): 28-Suite Calibration Verification ({cal_sum['total_passed']:,}/{cal_sum['total_trials']:,} = {100.0*cal_sum['total_passed']/cal_sum['total_trials']:.2f}%; Cumulative {syn['total_calibration_trials_d079_d107']:,} Trials)", fontsize=10.2, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig137_d107_calibration_28suites_6051trials.png")


def fig138_global_synthesis_904(res_dir: Path, ws_dir: Path, bundle: dict[str, Any], fig_dir: Path) -> None:
    s_json = json.loads((res_dir / "SUMMARY.json").read_text())
    syn = s_json[next(k for k in s_json if k.startswith("unified_") and k.endswith("_synthesis"))]
    b_rows = _read_csv(res_dir, syn["panchromatic_bridge_filename"])
    eirp107 = _read_csv(res_dir, "EIRP_UPPER_LIMITS_D107.csv")
    ic = _read_csv(res_dir, "ICECUBE_10YR_54TARGETS.csv")
    sub10 = _read_csv(res_dir, f"SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_{syn['within_10pc_unique_stars']}STARS.csv")
    ell = _read_csv(res_dir, f"MULTIEVENT_ELLIPSOID_{syn['unique_stars_total']}STARS.csv")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16.2, 11.0))
    fig.subplots_adjust(wspace=0.33, hspace=0.36)

    # Panel A: Global 60.845-Octave EM Sensitivity Frontier + TeV-PeV Neutrino Messenger Note
    ax1.axvspan(0.06998, 0.0905, color="#cbd5e0", alpha=0.75, zorder=0, label="ISM H Wall (700-905 A)")
    ax1.axvspan(2467.5, 2584.4, color="#feebc8", alpha=0.75, zorder=0, label="Terrestrial O2 118.75 GHz Wall")
    ax1.axvspan(4408.7, 5995.8, color="#fed7d7", alpha=0.65, zorder=0, label="Terrestrial O2 60 GHz Wall")
    prior_pts = [(float(r["wave_um"]), float(r["p_beam_10m_kw"])) for r in b_rows if r["phase_id"] != "D107" and r.get("wave_um") and r.get("p_beam_10m_kw") and float(r["p_beam_10m_kw"]) > 0]
    ax1.scatter([p[0] for p in prior_pts], [p[1] for p in prior_pts], s=8, color="#bdbdbd", alpha=0.45, zorder=1, label="D079-D106 EM Bridges (4.13e-15-8,556.4 um)")

    for ik, col, mk, lbl in [
        ("SWIFT_BAT",    "#b30000", "D", "D107 Swift-BAT 157m (14-195 keV)"),
        ("SWIFT_XRT",    "#7570b3", "^", "D107 Swift-XRT PC/WT (0.3-10 keV)"),
        ("ESO_ESPRESSO", "#2b8cbe", "o", "D107 ESPRESSO Orbits #187, #190"),
        ("ESO_HARPS",    "#1b9e77", "v", "D107 HARPS Orbits #188, #191, #192"),
        ("ESO_NIRPS",    "#d95f02", "s", "D107 NIRPS Orbit #189 (GJ 328)"),
    ]:
        sub = [r for r in eirp107 if r["instrument"] == ik]
        if sub:
            ax1.scatter([float(r["wave_bary_a"]) / 1e4 for r in sub], [float(r["p_beam_10m_kw"]) for r in sub], s=26, color=col, marker=mk, edgecolor="black", lw=0.4, label=lbl, zorder=4)
    ax1.text(0.98, 0.04, "QUAD-MESSENGER UPGRADE:\n60.845 EM Octaves\n+ 1.4 GHz Radio + TESS\n+ 0.1 TeV-10 PeV Neutrinos\n(IceCube 10-Yr: 54 Targets,\nPhi_nu >= 7.78e-15 cm^-2 s^-1;\nNO 10-m EM beam formula)", transform=ax1.transAxes, ha="right", va="bottom", fontsize=5.8, bbox=dict(boxstyle="round,pad=0.35", fc="#f0fff4", ec="#2f855a"))
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.0e-15, 30000.0)
    ax1.set_ylim(1.0e-25, 1.0e22)
    ax1.set_xlabel(f"EM Wavelength (um; {syn['min_wave_um']:.3e}-{syn['max_wave_um']:.2f} um = {syn['total_octave_span']} Octaves)")
    ax1.set_ylabel("Formal 10-m EM EIRP Limit (kW)")
    ax1.set_title(f"A. Unified {syn['spectrographs']}-Spectrograph / {syn['spectral_arms']}-Arm EM Frontier ({syn['total_octave_span']} Oct)")
    ax1.legend(loc="upper left", fontsize=5.2, frameon=True, ncol=2)
    ax1.grid(True, which="both", alpha=0.20)

    # Panel B: All-904 Star Sky Map
    prior_st = {r["star"] for r in json.loads((ws_dir / "PRIOR_V6_4_PHASES_SNAPSHOT.json").read_text())["prior_unified_852_rows"]}
    all107_st = {e["star"] for e in bundle["exposures"]}
    brand_n = all107_st - prior_st
    bridges_n = all107_st & prior_st
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
    ax2.scatter(ra_p, dec_p, s=11, color="#969696", alpha=0.55, label=f"Earlier D079-D106 ({len(ra_p)})")
    ax2.scatter(ra_b, dec_b, s=34, color="#2b8cbe", edgecolor="black", lw=0.45, label=f"D107 Bridges ({len(ra_b)})")
    ax2.scatter(ra_n, dec_n, s=44, color="#b30000", marker="^", edgecolor="black", lw=0.5, label=f"D107 Brand-New ({len(ra_n)})")
    ax2.set_xlim(-185, 185)
    ax2.set_ylim(-90, 90)
    ax2.set_xlabel("Right Ascension alpha (deg, wrapped)")
    ax2.set_ylabel("Declination delta (deg)")
    ax2.set_title(f"B. All-Sky Distribution Across {syn['unique_stars_total']} Targets ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl)")
    ax2.legend(loc="lower left", fontsize=6.6, frameon=True)
    ax2.grid(True, alpha=0.25)

    # Panel C: Solar Neighborhood 262 <10 pc Census (+18 IceCube Brand-New)
    d10 = []
    kw_opt10 = []
    col10 = []
    for r in sub10:
        d_v = float(r["dist_pc"])
        p_pan = r.get("min_panchromatic_10m_kw", "")
        if p_pan:
            d10.append(d_v)
            kw_opt10.append(float(p_pan))
            col10.append("#1b9e77" if r.get("n_exposures_icecube_10yr", "0") != "0" else "#2b8cbe")
    ax3.scatter(d10, kw_opt10, s=26, c=col10, edgecolor="black", lw=0.4, alpha=0.86, label=f"EM-Bounded <10 pc ({len(d10)} Stars; Opt Med={syn['within_10pc_optical_ir_median_limit_kw']:.4f} kW)")
    ax3.axhline(float(syn["within_10pc_median_limit_kw"]), ls="--", color="#b30000", lw=1.2, label=f"Global <10 pc Median = {syn['within_10pc_median_limit_kw']:.4f} kW (N={syn['within_10pc_unique_stars']} tot)")
    ax3.annotate("24 IceCube <10 pc Targets\n(+18 Brand-New Stars\nwith Neutrino Limits)", xy=(6.5, 1e-18), xytext=(1.35, 1e-17), fontsize=6.2, fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="#f0fff4", ec="#1b9e77"))
    ax3.set_yscale("log")
    ax3.set_xlabel("Heliocentric Distance d (pc)")
    ax3.set_ylabel("Deepest Formal 10-m EM EIRP Limit (kW)")
    ax3.set_title(f"C. Solar Neighborhood {syn['within_10pc_unique_stars']} <10 pc Stars (+18 Brand-New via IceCube)")
    ax3.legend(loc="lower right", fontsize=6.0, frameon=True)
    ax3.grid(True, which="both", alpha=0.22)

    # Panel D: Cross-Band EM Bridge Matrix (13 EM Regimes across Focus Bridges incl. 16CYGB, RTCRU, GKPER, NGC1068, MRK421)
    regs = [
        ("TeV\nVHE", 1e-16, 4.5e-12),
        ("GeV\nLAT", 4.5e-12, 4e-8),
        ("MeV/BAT\n50-30e3", 4e-8, 2.5e-4),
        ("Hard X\n1-80keV", 1.5e-4, 1.24e-3),
        ("Soft X\nXRT/CXO", 1.24e-3, 0.0176),
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
    for row in b_rows:
        st = row["star"]
        if not row.get("wave_um") or not row.get("p_beam_10m_kw") or float(row["p_beam_10m_kw"]) <= 0:
            continue
        by_star.setdefault(st, []).append((float(row["wave_um"]), float(row["p_beam_10m_kw"])))
    ic_set = {r["star"] for r in ic}

    def _reg_score(st: str) -> int:
        pts = by_star.get(st, [])
        return sum(1 for _, w0, w1 in regs if any(w0 <= w <= w1 for w, _ in pts)) + (2 if st in ic_set else 0)

    priority_stars = [
        "16CYGB", "EVLAC", "AUMIC", "PROXIMACEN", "ABDOR", "TRAPPIST1", "IIPEG", "CHCYG",
        "GAMMACAS", "RTCRU", "GKPER", "NGC1068", "MRK421", "CENA", "3C273", "CYGX1",
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
    ax4.set_xticklabels([r[0] for r in regs], fontsize=4.9)
    ax4.set_yticks(np.arange(len(focus)))
    ax4.set_yticklabels([f"{s}{'*' if s in ic_set else ''}" for s in focus], fontsize=6.0)
    for ri in range(len(focus)):
        for ci in range(len(regs)):
            v = mat[ri, ci]
            if math.isfinite(v):
                ax4.text(ci, ri, f"{v:+.0f}" if v <= -10.0 else f"{v:+.1f}", ha="center", va="center", fontsize=4.5, color="white" if v >= 0.0 else "black", fontweight="bold")
    cb = fig.colorbar(im, ax=ax4, fraction=0.042, pad=0.02)
    cb.set_label("log10(Best 10-m EM EIRP Limit / kW) [* = +IceCube nu]", fontsize=6.6)
    ax4.set_title(f"D. Bridge Matrix ({syn['panchromatic_bridge_stars_total']} Sci / {syn['multi_phase_targets_total']} Multi-Phase; {syn['panchromatic_bridge_cells_total']} Cells)")

    fig.suptitle(f"Phase D107 (V6.5): {syn['unique_stars_total']} Targets Across {syn['total_octave_span']} Octaves + TeV-PeV Neutrinos ({syn['spectrographs']} Spectrographs / {syn['spectral_arms']} Arms; {syn['within_10pc_unique_stars']} <10 pc; 0 ETI)", fontsize=9.8, fontweight="bold", y=0.985)
    _save(fig, fig_dir, "fig138_d107_unified_904star_quadmessenger_synthesis.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    az = _load_mod(ws / "analyze.py", "analyze_v65")
    det = _load_mod(ws / "v6_5_detector.py", "v6_5_detector")
    with gzip.open(ws / "bounded_inputs/d107_bounded_bundle.json.gz", "rb") as gz:
        bundle = json.loads(gz.read().decode("utf-8"))
    orb_json = json.loads((ws / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))

    fig133_icecube_10yr(res_dir, bundle, az, det, fig_dir)
    fig134_swift_bat_xrt(res_dir, bundle, az, det, fig_dir)
    fig135_quad_messenger(res_dir, det, fig_dir)
    fig136_orbits_and_84drift(res_dir, orb_json, det, fig_dir)
    fig137_calibration_28suites(res_dir, fig_dir)
    fig138_global_synthesis_904(res_dir, ws, bundle, fig_dir)
    print(f"Rendered 6 D107 figures -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
