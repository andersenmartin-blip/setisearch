#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D108 Publication Figure Generator (`fig139–fig144`, 240-DPI PNGs):
  - fig139_d108_ixpe_spectropolarimetry_2_8kev.png
  - fig140_d108_erosita_dr1_allsky_111stars.png
  - fig141_d108_rxte_hexte_pca_broadband_2_250kev.png
  - fig142_d108_v66_calibration_32suites_6891trials.png
  - fig143_d108_drift_v66_comb_90campaigns.png
  - fig144_d108_1004star_panchromatic_synthesis.png
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RES = WS / "results"
FIG_DIR = RES / "figures"

plt.rcParams.update({
    "figure.dpi": 240,
    "savefig.dpi": 240,
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / name
    fig.savefig(out, dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out.name}")
    return out


def make_fig139_ixpe(ixpe_rows: list[dict[str, str]], he_cands: list[dict[str, str]], eirp_rows: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6), constrained_layout=True)

    # Panel A: Stokes I vs Stokes (Q,U) flux upper limits across 17 targets
    rows_s = sorted(ixpe_rows, key=lambda r: float(r["flux_lim_i_cgs"]))
    stars = [r["star"] for r in rows_s]
    fi = np.array([float(r["flux_lim_i_cgs"]) for r in rows_s])
    fp = np.array([float(r["flux_lim_pol_cgs"]) for r in rows_s])
    y = np.arange(len(stars))
    ax = axes[0, 0]
    ax.hlines(y, fi, fp, color="#64748b", lw=1.6, alpha=0.8)
    ax.scatter(fi, y, color="#1d4ed8", s=34, zorder=4, label=r"Stokes $I$ 6$\sigma$ flux limit")
    ax.scatter(fp, y, color="#dc2626", marker="D", s=28, zorder=4, label=r"Stokes $(Q,U)$ polarized 6$\sigma$ limit")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(stars, fontsize=8.0)
    ax.set_xlabel(r"$6\sigma$ Narrowband Flux Upper Limit (erg cm$^{-2}$ s$^{-1}$)")
    ax.set_title("A. IXPE 2–8 keV Stokes I vs Polarized (Q,U) Sensitivity (17 Targets)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.92)

    # Panel B: Broadband 2-8 keV MDP99% vs On-Source Counts
    ax = axes[0, 1]
    ev_on = np.array([float(r["n_events_on"]) for r in ixpe_rows])
    mdp = np.array([float(r["mdp99_broad_pct"]) for r in ixpe_rows])
    is_new = np.array([r["is_prior_bridge"] == "False" for r in ixpe_rows])
    ax.scatter(ev_on[~is_new], mdp[~is_new], c="#0f766e", s=46, label="Prior Panchromatic Bridges (12)")
    ax.scatter(ev_on[is_new], mdp[is_new], c="#d97706", marker="^", s=58, label="New IXPE Control Targets (5)")
    for r in sorted(ixpe_rows, key=lambda x: float(x["mdp99_broad_pct"]))[:5]:
        ax.annotate(r["star"], (float(r["n_events_on"]), float(r["mdp99_broad_pct"])),
                    xytext=(6, 4), textcoords="offset points", fontsize=7.5)
    for r in sorted(ixpe_rows, key=lambda x: -float(x["mdp99_broad_pct"]))[:2]:
        ax.annotate(r["star"], (float(r["n_events_on"]), float(r["mdp99_broad_pct"])),
                    xytext=(6, -6), textcoords="offset points", fontsize=7.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Extracted 3-DU On-Source Events (r ≤ 60\")")
    ax.set_ylabel("Broadband 2–8 keV MDP$_{99}$ (%)")
    ax.set_title(r"B. IXPE Modulation Sensitivity ($\mathrm{MDP}_{99}$ = 2.09% on Vela X-1)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92)

    # Panel C: Per-band Modulation Efficiency & Polarized vs Intensity EIRP
    ax = axes[1, 0]
    ix_eirp = [r for r in eirp_rows if r["instrument"] == "IXPE_GPD"]
    bands = ["IXPE_2P5KEV", "IXPE_4P0KEV", "IXPE_6P0KEV"]
    blabels = ["2.5 keV\n(ARF=76.6, μ=0.23)", "4.0 keV\n(ARF=34.9, μ=0.38)", "6.0 keV\n(ARF=12.2, μ=0.47)"]
    data_b = [[float(r["flux_lim_erg_cm2_s"]) for r in ix_eirp if r["band_id"] == b] for b in bands]
    bp = ax.boxplot(data_b, positions=[0, 1, 2], widths=0.5, patch_artist=True)
    for patch, col in zip(bp["boxes"], ["#60a5fa", "#34d399", "#f59e0b"]):
        patch.set_facecolor(col)
        patch.set_alpha(0.75)
    ax.set_yscale("log")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(blabels, fontsize=8.0)
    ax.set_ylabel(r"Intensity $6\sigma$ Flux Limit (erg cm$^{-2}$ s$^{-1}$)")
    ax.set_title("C. IXPE 3-Band Effective Area vs Sensitivity Trade-off")

    # Panel D: IXPE Gate G3/G4/G5 Triage Breakdown of Raw Stokes-I Extrema
    ax = axes[1, 1]
    ix_c = [c for c in he_cands if c["instrument"] == "IXPE_GPD"]
    cat_counts = {
        "G3 Fe/S/Si/Ar\nAtlas Veto": sum(1 for c in ix_c if "G3_" in c["stage2_triage_status"]),
        "G4 3-DU/Split\nVeto": sum(1 for c in ix_c if "G4_" in c["stage2_triage_status"]),
        "G5 Line Width\nVeto": sum(1 for c in ix_c if "G5_" in c["stage2_triage_status"]),
        "Stage-2 AGN/PSR\nContinuum": sum(1 for c in ix_c if c["qualified_v66"] == "True"),
        "Verified ETI": 0,
    }
    cats = list(cat_counts.keys())
    vals = list(cat_counts.values())
    colors = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#16a34a"]
    bars = ax.bar(range(len(cats)), vals, color=colors, width=0.62, edgecolor="#1e293b", lw=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2.0, v + 0.6, str(v), ha="center", va="bottom", fontweight="bold", fontsize=8.5)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontsize=7.8)
    ax.set_ylim(0, max(vals + [5]) * 1.18)
    ax.set_ylabel("Count across 46 Raw Stokes-I Extrema")
    ax.set_title("D. IXPE Multi-Gate & Polarimetric Triage (0 Verified ETI)")

    fig.suptitle("Phase D108 V6.6 — IXPE 2–8 keV X-Ray Spectro-Polarimetric SETI Search (17 Targets, 2.19M Events)", fontsize=12.0, fontweight="bold")
    _save(fig, "fig139_d108_ixpe_spectropolarimetry_2_8kev.png")


def make_fig140_erosita(ero_rows: list[dict[str, str]], cohort_rows: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6), constrained_layout=True)

    c_by_star = {r["canonical_target"]: r for r in cohort_rows if r["instrument"] == "EROSITA_DR1"}
    ras = np.array([float(c_by_star[r["star"]]["s_ra"]) for r in ero_rows])
    decs = np.array([float(c_by_star[r["star"]]["s_dec"]) for r in ero_rows])
    ra_wrap = np.where(ras > 180.0, ras - 360.0, ras)
    sub10 = np.array([r["within_10pc"] == "True" for r in ero_rows])
    br = np.array([r["is_prior_bridge"] == "True" for r in ero_rows])

    # Panel A: All-Sky footprint (note eROSITA-DE German sky hemisphere l_gal bias / Dec/RA coverage)
    ax = axes[0, 0]
    m_10_20 = (~sub10) & (~br)
    ax.scatter(ra_wrap[m_10_20], decs[m_10_20], c="#2563eb", s=26, alpha=0.85, label="New 10–20 pc (83)")
    ax.scatter(ra_wrap[sub10], decs[sub10], c="#dc2626", marker="*", s=110, zorder=5, label="< 10 pc Targets (9: 4 new + 5 br.)")
    ax.scatter(ra_wrap[br & (~sub10)], decs[br & (~sub10)], c="#059669", marker="s", s=34, zorder=4, label="Prior Bridges >10 pc (19)")
    ax.axhline(0.0, color="#94a3b8", lw=0.8, ls=":")
    ax.axvline(0.0, color="#94a3b8", lw=0.8, ls=":")
    ax.set_xlim(-185, 185)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Right Ascension (deg, wrapped [-180, +180])")
    ax.set_ylabel("Declination (deg)")
    ax.set_title("A. SRG/eROSITA-DE DR1 Western Galactic Hemisphere Cohort (111 Targets)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92)

    # Panel B: Distance vs 10m EIRP Limit across <10 pc, 10-20 pc, and Bridges
    ax = axes[0, 1]
    d_pc = np.array([float(r["dist_pc"]) for r in ero_rows])
    pkw = np.array([float(r["p_beam_10m_kw"]) for r in ero_rows])
    ax.scatter(d_pc[m_10_20], pkw[m_10_20], c="#2563eb", s=28, alpha=0.85, label="New 10–20 pc")
    ax.scatter(d_pc[sub10], pkw[sub10], c="#dc2626", marker="*", s=110, zorder=5, label="< 10 pc")
    ax.scatter(d_pc[br & (~sub10)], pkw[br & (~sub10)], c="#059669", marker="s", s=34, zorder=4, label="Prior Bridges")
    ero_ann_offsets = {
        "EPSERI": (6, 4, "left", None),
        "SCRJ06307643A": (7, -6, "left", None),
        "ERO_8855002381": (-36, 48, "left", {"arrowstyle": "-", "lw": 0.7, "color": "#475569"}),
        "ZETDOR": (8, -6, "left", None),
    }
    for r in sorted(ero_rows, key=lambda x: float(x["p_beam_10m_kw"]))[:4]:
        dx, dy, ha_b, ap_b = ero_ann_offsets.get(r["star"], (6, -4, "left", None))
        ax.annotate(r["star"], (float(r["dist_pc"]), float(r["p_beam_10m_kw"])),
                    xytext=(dx, dy), textcoords="offset points", ha=ha_b, fontsize=7.5, arrowprops=ap_b)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Distance (pc)")
    ax.set_ylabel(r"10 m Transmitter EIRP Limit $P_{\mathrm{10m}}$ (kW)")
    ax.set_title("B. eROSITA-DR1 0.2–8 keV Scaling (eps Eri: 5.98 mW at 10 m)")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92)

    # Panel C: Distribution of Flux Limits & TM Odd/Even Coincidence Exposure Fraction
    ax = axes[1, 0]
    sptm = np.array([float(r["split_p_tm"]) for r in ero_rows])
    ax.hist(sptm, bins=18, color="#0284c7", edgecolor="#0f172a", alpha=0.85)
    ax.axvline(4.0 / 7.0, color="#dc2626", ls="--", lw=1.6, label=f"Nominal 4/7 Odd TMs ({4/7:.3f})")
    ax.set_xlabel(r"Odd-TM Exposure Fraction $t_{\mathrm{TM1,3,4,6}} / t_{\mathrm{all}}$")
    ax.set_ylabel("Number of Targets")
    ax.set_title("C. Hardware TM1,3,4,6 vs TM2,5,7 Duty-Cycle Calibration")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92)

    # Panel D: Background Scaling alpha_bg vs Exposure Time
    ax = axes[1, 1]
    exps_s = np.array([float(r["exposure_s"]) for r in ero_rows])
    abg = np.array([float(r["alpha_bg"]) for r in ero_rows])
    flim = np.array([float(r["flux_lim_erg_cm2_s"]) for r in ero_rows])
    sc = ax.scatter(exps_s, flim, c=np.clip(abg, 0.008, 0.02), cmap="viridis", s=34, alpha=0.88)
    cb = fig.colorbar(sc, ax=ax, shrink=0.92)
    cb.set_label(r"BACKSCAL Ratio $\alpha_{\mathrm{bg}}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("020 Source Exposure Time (s)")
    ax.set_ylabel(r"$6\sigma$ Flux Limit at 1.5 keV (erg cm$^{-2}$ s$^{-1}$)")
    ax.set_title("D. Poisson Flux Sensitivity vs Survey Depth (111 Targets, 0 ETI)")

    fig.suptitle("Phase D108 V6.6 — SRG/eROSITA-DE DR1 All-Sky 0.2–8.0 keV Search (111 Targets)", fontsize=12.0, fontweight="bold")
    _save(fig, "fig140_d108_erosita_dr1_allsky_111stars.png")


def make_fig141_rxte(hexte_rows: list[dict[str, str]], pca_rows: list[dict[str, str]], eirp_rows: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6), constrained_layout=True)

    # Panel A: PCA vs HEXTE Matched 10m EIRP across 16 targets
    ax = axes[0, 0]
    p_map = {r["star"]: float(r["p_beam_10m_kw"]) for r in pca_rows}
    h_map = {r["star"]: float(r["p_beam_10m_kw"]) for r in hexte_rows}
    stars = sorted(p_map.keys())
    pv = np.array([p_map[s] for s in stars])
    hv = np.array([h_map[s] for s in stars])
    is_sci = np.array([next(r["role"] == "SCIENCE" for r in pca_rows if r["star"] == s) for s in stars])
    ax.scatter(pv[is_sci], hv[is_sci], c="#059669", s=56, label="SCIENCE Targets (6 incl. AR Lac)")
    ax.scatter(pv[~is_sci], hv[~is_sci], c="#7c3aed", marker="D", s=44, label="CONTROL Targets (10)")
    lo, hi = min(pv.min(), hv.min()) * 0.4, max(pv.max(), hv.max()) * 2.5
    ax.plot([lo, hi], [lo, hi], color="#475569", ls="--", lw=1.2, label="1:1 Parity")
    rx_offsets = {
        "AUMIC": (-2, 10, "left"),
        "HD34029": (7, -10, "left"),
        "ARLAC": (6, 1, "left"),
        "EXHYA": (6, 3, "left"),
        "CYGX1": (6, 2, "left"),
        "MRK421": (-7, -9, "right"),
    }
    for s, (dx, dy, ha_r) in rx_offsets.items():
        ax.annotate(s, (p_map[s], h_map[s]), xytext=(dx, dy), textcoords="offset points", ha=ha_r, fontsize=7.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(r"RXTE PCA (2–60 keV) $P_{\mathrm{10m}}$ (kW)")
    ax.set_ylabel(r"RXTE HEXTE (15–250 keV) $P_{\mathrm{10m}}$ (kW)")
    ax.set_title("A. Dual-Instrument PCA + HEXTE 10 m EIRP Across 16 Targets")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92)

    # Panel B: Broadband Flux Sensitivity Curves (4 keV -> 180 keV) for Science Targets
    ax = axes[0, 1]
    rx_eirp = [r for r in eirp_rows if r["instrument"] in ("RXTE_PCA", "RXTE_HEXTE")]
    for st, col, mk in [("HD34029", "#1d4ed8", "o"), ("AUMIC", "#dc2626", "s"), ("ABDOR", "#059669", "^"), ("ARLAC", "#d97706", "D")]:
        pts = [(det_kev(float(r["wave_bary_a"])), float(r["flux_lim_erg_cm2_s"])) for r in rx_eirp if r["star"] == st]
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=mk, lw=1.8, ms=5, color=col, label=st)
    ax.axvspan(15.0, 60.0, color="#cbd5e1", alpha=0.35, label="PCA–HEXTE Overlap (15–60 keV)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Photon Energy (keV)")
    ax.set_ylabel(r"$6\sigma$ Narrowband Flux Limit (erg cm$^{-2}$ s$^{-1}$)")
    ax.set_title("B. Continuous 4–180 keV Narrowband Flux Curves")
    ax.legend(loc="lower right", frameon=True, framealpha=0.92)

    # Panel C: RXTE PCA Total Effective Area (PCU Count) Distribution
    ax = axes[1, 0]
    aeff_p = np.array([float(r["aeff_cm2"]) for r in pca_rows])
    fl_p = np.array([float(r["flux_lim_erg_cm2_s"]) for r in pca_rows])
    exp_p = np.array([float(r["exposure_s"]) for r in pca_rows])
    ax.scatter(exp_p, fl_p, c=aeff_p, cmap="plasma", s=60, edgecolor="#0f172a", lw=0.6)
    for r in pca_rows:
        if r["star"] in ("ABDOR", "HD34029", "ARLAC", "HD22468"):
            ax.annotate(r["star"], (float(r["exposure_s"]), float(r["flux_lim_erg_cm2_s"])),
                        xytext=(6, 4), textcoords="offset points", fontsize=7.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("PCA Std2 Exposure Time (s)")
    ax.set_ylabel(r"Best PCA $6\sigma$ Flux Limit (erg cm$^{-2}$ s$^{-1}$)")
    ax.set_title("C. RXTE PCA Sensitivity vs Exposure (1–5 Active PCUs)")

    # Panel D: RXTE HEXTE Cluster A vs Cluster B Rocking Net Counts
    ax = axes[1, 1]
    st_h = [r["star"] for r in sorted(hexte_rows, key=lambda x: abs(float(x["net_cts_a"])), reverse=True)]
    na = [max(1.0, abs(float(next(r["net_cts_a"] for r in hexte_rows if r["star"] == s)))) for s in st_h]
    nb = [max(1.0, abs(float(next(r["net_cts_b"] for r in hexte_rows if r["star"] == s)))) for s in st_h]
    yh = np.arange(len(st_h))
    ax.barh(yh - 0.18, na, height=0.35, color="#0284c7", label="|Net Counts| Cluster A")
    ax.barh(yh + 0.18, nb, height=0.35, color="#ea580c", label="|Net Counts| Cluster B")
    ax.set_xscale("log")
    ax.set_yticks(yh)
    ax.set_yticklabels(st_h, fontsize=7.8)
    ax.set_xlabel("Absolute Background-Subtracted Counts (15–250 keV)")
    ax.set_title("D. HEXTE Dual-Cluster A/B ON-OFF Rocking Balance (0 ETI)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92)

    fig.suptitle("Phase D108 V6.6 — RXTE PCA (2–60 keV) & HEXTE (15–250 keV) Broadband Search (16 Targets)", fontsize=12.0, fontweight="bold")
    _save(fig, "fig141_d108_rxte_hexte_pca_broadband_2_250kev.png")


def det_kev(wave_a: float) -> float:
    return 12.39841984 / max(1e-6, wave_a)


def make_fig142_cal(summary: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.8), constrained_layout=True)
    suites = summary["synthetic_calibration_6891_trials"]["suites"]
    names = list(suites.keys())
    rates = [100.0 * suites[n]["passed"] / suites[n]["total"] for n in names]
    short_names = [n.replace("CALIBRATION_", "").replace("_CALIBRATION", "") for n in names]

    # Panel A: New V6.6 Suites (first 4) pass-rate bar comparison
    ax = axes[0, 0]
    v66_n = short_names[:4]
    v66_r = rates[:4]
    bars = ax.bar(range(4), v66_r, color=["#2563eb", "#0284c7", "#059669", "#7c3aed"], width=0.55)
    ax.axhline(97.5, color="#dc2626", ls="--", lw=1.4, label="Required Gate (97.5%)")
    for b, n, r in zip(bars, names[:4], v66_r):
        s = suites[n]
        ax.text(b.get_x() + b.get_width() / 2.0, r + 0.15, f"{s['passed']}/{s['total']}\n({r:.2f}%)", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
    ax.set_xticks(range(4))
    ax.set_xticklabels(["IXPE Pol\n(240)", "eROSITA DR1\n(240)", "RXTE HEXTE\n(180)", "RXTE PCA\n(180)"], fontsize=8.5)
    ax.set_ylim(95.0, 101.2)
    ax.set_ylabel("Pass Rate (%)")
    ax.set_title("A. New V6.6 X-Ray Spectro-Polarimetric & Broadband Suites (832/840)")
    ax.legend(loc="lower right", frameon=True)

    # Panel B: Class-by-Class Breakdown of New IXPE & eROSITA Suites
    ax = axes[0, 1]
    bd_ix = suites["CALIBRATION_V66_IXPE_POLARIMETRY_240"]["breakdown"]
    bd_er = suites["CALIBRATION_V66_EROSITA_DR1_240"]["breakdown"]
    items = [
        ("IXPE Pol Beacon (60)", 59 / 60 * 100),
        ("IXPE Unpol Beacon (40)", 38 / 40 * 100),
        ("IXPE DU/PA/Atlas/Null (140)", 140 / 140 * 100),
        ("eROSITA Clean (80)", 76 / 80 * 100),
        ("eROSITA TM/Atlas/Null (160)", 160 / 160 * 100),
        ("HEXTE All Classes (180)", 180 / 180 * 100),
        ("PCA All Classes (180)", 179 / 180 * 100),
    ]
    lbls = [x[0] for x in items]
    pvals = [x[1] for x in items]
    yy = np.arange(len(items))
    ax.barh(yy, pvals, color=["#1d4ed8", "#3b82f6", "#60a5fa", "#0284c7", "#38bdf8", "#059669", "#7c3aed"], height=0.6)
    ax.axvline(97.5, color="#dc2626", ls="--", lw=1.2)
    for yi, pv in zip(yy, pvals):
        ax.text(min(99.6, pv - 3.8), yi, f"{pv:.1f}%", va="center", color="white", fontweight="bold", fontsize=8.0)
    ax.set_yticks(yy)
    ax.set_yticklabels(lbls, fontsize=8.0)
    ax.set_xlim(88.0, 100.8)
    ax.set_xlabel("Sub-class Accuracy (%)")
    ax.set_title("B. Sub-Class Recovery & Veto Specificity Breakdown")

    # Panel C: All 32 Suites Uniform Compliance >= 97.5%
    ax = axes[1, 0]
    y32 = np.arange(len(names))
    cols32 = ["#2563eb" if i < 4 else "#64748b" for i in range(len(names))]
    ax.barh(y32, rates, color=cols32, height=0.72)
    ax.axvline(97.5, color="#dc2626", ls="--", lw=1.3, label="97.5% Floor")
    ax.set_yticks(y32[::2])
    ax.set_yticklabels([short_names[i] for i in range(0, len(names), 2)], fontsize=7.0)
    ax.set_xlim(96.0, 100.5)
    ax.set_xlabel("Suite Pass Rate (%)")
    ax.set_title("C. All 32 Calibration Suites (6,854 / 6,891 = 99.46% Pass)")
    ax.set_ylim(33.8, -0.8)
    ax.legend(loc="lower right", frameon=True, framealpha=0.95)

    # Panel D: Cumulative Trial Progression D094 -> D108 (81,123 Total)
    ax = axes[1, 1]
    ph_lbls = ["D094", "D096", "D098", "D100", "D102", "D104", "D106", "D107", "D108"]
    cum_trials = [30291, 33883, 37945, 42427, 47489, 54051, 68181, 74232, 81123]
    ax.plot(range(len(ph_lbls)), [c / 1e3 for c in cum_trials], marker="o", color="#0f766e", lw=2.2, ms=6)
    ax.fill_between(range(len(ph_lbls)), 0, [c / 1e3 for c in cum_trials], color="#99f6e4", alpha=0.45)
    for xi, cv in enumerate(cum_trials):
        if xi in (0, 4, 6, 8):
            ax.annotate(f"{cv:,}", (xi, cv / 1e3), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.0, fontweight="bold")
    ax.set_xticks(range(len(ph_lbls)))
    ax.set_xticklabels(ph_lbls, fontsize=8.5)
    ax.set_ylabel("Cumulative Calibration Trials (× 1,000)")
    ax.set_title("D. Cumulative Calibration Verification Trajectory (81,123 Trials)")

    fig.suptitle("Phase D108 V6.6 — Full 32-Suite Calibration Verification (6,891 Phase Trials / 81,123 Cumulative)", fontsize=12.0, fontweight="bold")
    _save(fig, "fig142_d108_v66_calibration_32suites_6891trials.png")


def make_fig143_drift(dr90: list[dict[str, str]], cd90: list[dict[str, str]], orb6: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6), constrained_layout=True)

    # Panel A: 90 Campaigns Pixel-Trajectory Integrals by Instrument
    ax = axes[0, 0]
    inst_g = sorted({r["instrument"] for r in dr90})
    px_by_i = [sum(float(r["n_pixel_trajectory_integrals"]) for r in dr90 if r["instrument"] == i) / 1e9 for i in inst_g]
    cnt_i = [sum(1 for r in dr90 if r["instrument"] == i) for i in inst_g]
    ax.barh(range(len(inst_g)), px_by_i, color="#0284c7", alpha=0.88)
    for idx, (pv, ci) in enumerate(zip(px_by_i, cnt_i)):
        ax.text(pv + 0.08, idx, f"{pv:.2f}B ({ci} camp.)", va="center", fontsize=8.0)
    ax.set_yticks(range(len(inst_g)))
    ax.set_yticklabels([i.replace("ESO_", "") for i in inst_g], fontsize=8.5)
    ax.set_xlim(0, max(px_by_i) * 1.32)
    ax.set_xlabel(r"Pixel-Trajectory Integrals Evaluated ($\times 10^9$)")
    ax.set_title("A. DRIFT_V66 Compute Volume Across All 90 Keplerian Campaigns")

    # Panel B: Baseline vs Trajectories Highlighting Orbits #193-#198
    ax = axes[0, 1]
    dt_r = np.array([float(r["dt_baseline_days"]) for r in dr90])
    tr_r = np.array([float(r["n_trajectories_evaluated"]) for r in dr90])
    is_live = np.array([r["phase_source"] == "D108" for r in dr90])
    ax.scatter(dt_r[~is_live], tr_r[~is_live], c="#64748b", s=28, alpha=0.75, label="Retrograde 84 Campaigns (T–Z, AA–AG)")
    ax.scatter(dt_r[is_live], tr_r[is_live], c="#dc2626", marker="*", s=130, zorder=5, label="New D108 Orbits #193–#198")
    orb_offsets = {
        "TOI244": (-4, -14),
        "GJ317": (-2, 10),
        "GJ1252": (7, -11),
        "TOI198": (6, 6),
        "GJ3293": (-4, 9),
        "7CMA": (6, 6),
    }
    for r in orb6:
        b = float(r["baseline_days"])
        row_d = next(x for x in dr90 if x["phase_source"] == "D108" and x["star"] == r["star"])
        dx, dy = orb_offsets.get(r["star"], (4, 4))
        ax.annotate(r["star"], (b, float(row_d["n_trajectories_evaluated"])), xytext=(dx, dy), textcoords="offset points", ha="center" if dx < 0 else "left", fontsize=7.5)
    ax.set_xscale("log")
    ax.set_xlabel("Orbital Temporal Baseline (days)")
    ax.set_ylabel("Keplerian + Taylor Trajectories")
    ax.set_title("B. Orbit Baselines up to 4,300 Days (11.8 yr on 7 CMa HARPS)")
    ax.legend(loc="lower right", frameon=True)

    # Panel C: Drifting Comb Triage Across 90 Campaigns
    ax = axes[1, 0]
    raw_c = [float(r["comb_raw_candidates"]) for r in cd90]
    qual_c = [float(r["comb_qualified_v66"]) for r in cd90]
    ord_x = np.arange(len(cd90))
    ax.plot(ord_x, raw_c, color="#0284c7", lw=1.2, alpha=0.8, label=f"Raw Coherent Comb (Σ={int(sum(raw_c)):,})")
    ax.plot(ord_x, qual_c, color="#d97706", lw=1.5, label=f"Pre-Stage-2 Qualified (Σ={int(sum(qual_c)):,})")
    ax.axhline(0, color="#16a34a", lw=2.0, label="Verified ETI (0)")
    ax.axvspan(-0.5, 5.5, color="#fee2e2", alpha=0.45, label="Live D108 Orbits (#193–#198)")
    ax.set_xlabel("Campaign Index (1–6 Live D108, 7–90 Retrograde)")
    ax.set_ylabel("Candidate Count")
    ax.set_title("C. COMB_DRIFT_V66 Coherent Comb Funnel (5,803 -> 222 -> 0 ETI)")
    ax.legend(loc="upper right", frameon=True, fontsize=7.5)

    # Panel D: Funnel Summary for Dual V6.6 Search
    ax = axes[1, 1]
    labels = ["Kepler Traj.\n(125.5k)", "Kepler Raw\n(33.4k)", "Comb Traj.\n(19.2k)", "Comb Qual.\n(222)", "Verified ETI\n(0)"]
    vals = [125549, 33424, 19201, 222, 0]
    bars = ax.bar(range(5), [max(1, v) for v in vals], color=["#1d4ed8", "#0284c7", "#0d9488", "#d97706", "#16a34a"], width=0.58)
    ax.set_yscale("log")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2.0, max(1.3, v * 1.15), f"{v:,}", ha="center", va="bottom", fontweight="bold", fontsize=8.0)
    ax.set_xticks(range(5))
    ax.set_xticklabels(labels, fontsize=8.0)
    ax.set_ylim(0.8, 3e5)
    ax.set_ylabel("Count (log scale)")
    ax.set_title("D. Zero Verified ETI Across 15.63B Pixel Integrals & 90 Campaigns")

    fig.suptitle("Phase D108 V6.6 — 90-Campaign Coherent Eccentric Keplerian & Drifting Comb Synthesis", fontsize=12.0, fontweight="bold")
    _save(fig, "fig143_d108_drift_v66_comb_90campaigns.png")


def make_fig144_synthesis(uni: list[dict[str, str]], br_rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.8), constrained_layout=True)

    # Panel A: 60.845-Octave Spectral Landscape + Neutrino Messenger + Polarization
    ax = axes[0, 0]
    by_reg = [
        ("HAWC TeV–PeV", 3e-15, 2e-12),
        ("HESS/MAGIC/VER", 1e-14, 3e-11),
        ("Fermi LAT GeV", 4e-12, 4e-8),
        ("BAT+HEXTE Hard-X", 5e-6, 9e-5),
        ("IXPE 2–8 keV Pol.", 1.5e-4, 6.2e-4),
        ("eROSITA+PCA+XRT", 1.2e-4, 6.2e-3),
        ("Opt/NIR Echelle", 0.32, 2.5),
        ("JWST+SOFIA IR", 2.9, 630.0),
        ("ALMA 9-Band mm", 316.0, 8556.0),
    ]
    for yi, (lbl, wlo, whi) in enumerate(by_reg):
        col = "#dc2626" if "IXPE" in lbl else ("#0284c7" if ("eROSITA" in lbl or "BAT" in lbl) else "#1e3a8a")
        ax.hlines(yi, wlo, whi, color=col, lw=6.0)
        ax.text(max(whi * 1.4, 1e-13), yi, lbl, va="center", fontsize=8.0)
    ax.set_xscale("log")
    ax.set_xlim(1e-15, 1e6)
    ax.set_yticks([])
    ax.set_xlabel("Photon Wavelength (μm)  [+ IceCube 0.1 TeV–10 PeV Neutrinos]")
    ax.set_title("A. 60.845-Octave Panchromatic + Polarimetry + Neutrino Coverage")

    # Panel B: Historic Unique Star Milestone Crossing 1,004 (267 <10 pc)
    ax = axes[0, 1]
    ph_s = ["D085", "D090", "D095", "D100", "D102", "D104", "D106", "D107", "D108"]
    u_tot = [154, 307, 401, 560, 656, 755, 852, 904, 1004]
    u_10 = [85, 134, 161, 176, 183, 206, 244, 262, 267]
    x = np.arange(len(ph_s))
    ax.plot(x, u_tot, marker="o", lw=2.3, color="#1d4ed8", label="All Analyzed Stars (1,004)")
    ax.plot(x, u_10, marker="s", lw=2.0, color="#059669", label="< 10 pc Solar Neighborhood (267)")
    ax.axhline(1000.0, color="#dc2626", ls="--", lw=1.2, label="1,000-Star Survey Benchmark")
    ax.annotate("1,004", (len(ph_s) - 1, 1004), xytext=(-14, -14), textcoords="offset points", fontweight="bold", color="#1d4ed8")
    ax.annotate("267", (len(ph_s) - 1, 267), xytext=(-12, 8), textcoords="offset points", fontweight="bold", color="#059669")
    ax.set_xticks(x)
    ax.set_xticklabels(ph_s, fontsize=8.0)
    ax.set_ylabel("Cumulative Unique Analyzed Stars")
    ax.set_title("B. Crossing 1,004 Unique Stars Across Phases D079–D108")
    ax.legend(loc="upper left", frameon=True, fontsize=8.0)

    # Panel C: Multi-Phase Panchromatic Bridge Landscape (2,334 cells)
    ax = axes[1, 0]
    em_br = [r for r in br_rows if r["instrument"] != "ICECUBE_10YR" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    wu = np.array([float(r["wave_um"]) for r in em_br])
    pkw = np.array([float(r["p_beam_10m_kw"]) for r in em_br])
    is_d108 = np.array([r["phase_id"] == "D108" for r in em_br])
    ax.scatter(wu[~is_d108], pkw[~is_d108], c="#94a3b8", s=8, alpha=0.55, label=f"Prior EM Bridge Cells ({int(np.sum(~is_d108))})")
    ax.scatter(wu[is_d108], pkw[is_d108], c="#dc2626", s=16, alpha=0.85, label=f"New D108 EM Bridge Cells ({int(np.sum(is_d108))})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Wavelength (μm)")
    ax.set_ylabel(r"10 m Transmitter EIRP $P_{\mathrm{10m}}$ (kW)")
    ax.set_title("C. 155 SCIENCE Panchromatic Bridges (2,334 Cells incl. 126 ν_μ Zero-EM)")
    ax.legend(loc="lower left", frameon=True, fontsize=8.0)

    # Panel D: <10 pc EIRP Depth Distribution (267 Solar-Neighborhood Stars)
    ax = axes[1, 1]
    sub10_kw = [float(r["min_panchromatic_10m_kw"]) for r in uni if r["within_10pc"] == "True" and r["min_panchromatic_10m_kw"]]
    ax.hist(np.log10(sub10_kw), bins=28, color="#0d9488", edgecolor="#0f172a", alpha=0.85)
    med_kw = float(summary["unified_1004star_panchromatic_v6_6_synthesis"]["within_10pc_median_limit_kw"])
    opt_med = float(summary["unified_1004star_panchromatic_v6_6_synthesis"]["within_10pc_optical_ir_median_limit_kw"])
    ax.axvline(math.log10(med_kw), color="#dc2626", lw=1.8, ls="--", label=f"Global Median: {med_kw:.4f} kW")
    ax.axvline(math.log10(opt_med), color="#1d4ed8", lw=1.6, ls=":", label=f"Optical-IR Median: {opt_med:.4f} kW")
    ax.set_xlabel(r"$\log_{10}(P_{\mathrm{10m}}\,/\,\mathrm{kW})$ across 267 Stars within 10 pc")
    ax.set_ylabel("Stars per bin")
    ax.set_title("D. Solar Neighborhood (< 10 pc) Panchromatic Sensitivity (267 Stars)")
    ax.legend(loc="upper left", frameon=True, fontsize=8.0)

    fig.suptitle("Phase D108 V6.6 — 1,004-Star, 66-Spectrograph, 60.845-Octave Panchromatic & Polarimetric Synthesis", fontsize=12.0, fontweight="bold")
    _save(fig, "fig144_d108_1004star_panchromatic_synthesis.png")


def main() -> int:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    ixpe_rows = _read_csv(RES / "IXPE_POLARIMETRY_17TARGETS.csv")
    ero_rows = _read_csv(RES / "EROSITA_DR1_111TARGETS.csv")
    hexte_rows = _read_csv(RES / "RXTE_HEXTE_16TARGETS.csv")
    pca_rows = _read_csv(RES / "RXTE_PCA_16TARGETS.csv")
    he_cands = _read_csv(RES / "V6_6_HIGH_ENERGY_CANDIDATE_LEDGER.csv")
    eirp_rows = _read_csv(RES / "EIRP_UPPER_LIMITS_D108.csv")
    cohort_rows = _read_csv(WS / "FROZEN_COHORT_D108.csv")
    dr90 = _read_csv(RES / "DRIFT_V66_ECCENTRIC_KEPLERIAN_90CAMPAIGNS.csv")
    cd90 = _read_csv(RES / "COMB_DRIFT_V66_90CAMPAIGNS.csv")
    orb6 = _read_csv(RES / "ORBITAL_CAMPAIGN_RESULTS_6_D108.csv")
    uni = _read_csv(RES / "UNIFIED_PANCHROMATIC_V6_6_SYNTHESIS_1004STARS.csv")
    br_rows = _read_csv(RES / "PANCHROMATIC_BRIDGE_155STARS_V66.csv")

    make_fig139_ixpe(ixpe_rows, he_cands, eirp_rows)
    make_fig140_erosita(ero_rows, cohort_rows)
    make_fig141_rxte(hexte_rows, pca_rows, eirp_rows)
    make_fig142_cal(summary)
    make_fig143_drift(dr90, cd90, orb6)
    make_fig144_synthesis(uni, br_rows, summary)
    print("All 6 Phase D108 figures (fig139-fig144) rendered cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
