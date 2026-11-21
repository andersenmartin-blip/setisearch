#!/usr/bin/env python3
"""Generate 6 publication-grade 240-DPI PNG figures for SETI Phase D095 (V5.3)."""

from __future__ import annotations

import csv
import gzip
import json
import math
import pathlib
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from analyze import _decode_float_arr, _decode_wave, _unpack_exposure_spectrum
import v5_3_detector as det

WS = pathlib.Path(__file__).resolve().parent
RES = WS / "results"
FIG_DIR = RES / "figures"
BUNDLE = WS / "bounded_inputs" / "d095_bounded_bundle.json.gz"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.2,
    "axes.titlesize": 10.2,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.2,
    "xtick.labelsize": 8.4,
    "ytick.labelsize": 8.4,
    "legend.fontsize": 7.8,
    "figure.titlesize": 11.8,
    "figure.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 240,
})


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, fname: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / fname
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    print(f"Wrote {out}", flush=True)


def fig01_panchromatic_401stars(summary: dict[str, Any]) -> None:
    ul95 = _read_csv("EIRP_UPPER_LIMITS_D095.csv")
    u401 = _read_csv("UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv")
    syn = summary["unified_401star_panchromatic_v5_3_synthesis"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.6), gridspec_kw={"width_ratios": [1.0, 1.08]})
    fig.subplots_adjust(wspace=0.27)

    meta = [
        ("GEMINI_GHOST", "GEMINI GHOST Blue+Red (R=56k)", "#2b8cbe", "o"),
        ("SDSS_APOGEE2", "SDSS APOGEE-2 H (R=22.5k)", "#1b9e77", "s"),
        ("SPITZER_IRS", "Spitzer IRS SL+LL (5.2–37.9 µm)", "#d95f02", "^"),
    ]
    for inst, lbl, col, mk in meta:
        sub = [r for r in ul95 if r["instrument"] == inst]
        xs = [float(r["wave_bary_a"]) / 1e4 for r in sub]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax1.scatter(xs, ys, s=36, color=col, marker=mk, alpha=0.82, label=f"{lbl} ({len(sub)})")

    best_gh = min([r for r in ul95 if r["instrument"] == "GEMINI_GHOST"], key=lambda r: float(r["p_beam_10m_kw"]))
    best_ap = min([r for r in ul95 if r["instrument"] == "SDSS_APOGEE2"], key=lambda r: float(r["p_beam_10m_kw"]))
    best_sp = min([r for r in ul95 if r["instrument"] == "SPITZER_IRS"], key=lambda r: float(r["p_beam_10m_kw"]))

    ax1.annotate(
        f"{best_gh['star']} ({best_gh['band_id']})\n{float(best_gh['p_beam_10m_kw']):.2f} kW",
        xy=(float(best_gh["wave_bary_a"]) / 1e4, float(best_gh["p_beam_10m_kw"])),
        xytext=(0.55, 0.08),
        arrowprops=dict(arrowstyle="->", lw=0.8),
        fontsize=7.8, fontweight="bold",
    )
    ax1.annotate(
        f"{best_ap['star']} ({best_ap['band_id']})\n{float(best_ap['p_beam_10m_kw']):.2f} kW",
        xy=(float(best_ap["wave_bary_a"]) / 1e4, float(best_ap["p_beam_10m_kw"])),
        xytext=(1.75, 0.35),
        arrowprops=dict(arrowstyle="->", lw=0.8),
        fontsize=7.8,
    )
    ax1.annotate(
        f"{best_sp['star']} ({best_sp['band_id']})\n{float(best_sp['p_beam_10m_kw']):.3f} kW",
        xy=(float(best_sp["wave_bary_a"]) / 1e4, float(best_sp["p_beam_10m_kw"])),
        xytext=(11.5, 0.032),
        arrowprops=dict(arrowstyle="->", lw=0.8),
        fontsize=7.8, fontweight="bold",
    )

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.34, 42.0)
    ax1.set_ylim(0.015, 2.0e14)
    ax1.set_xticks([0.4, 0.7, 1.0, 1.6, 3.0, 6.5, 18.0, 34.5])
    ax1.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax1.set_xlabel("Wavelength (µm, log scale)")
    ax1.set_ylabel("10-m Directed Laser EIRP Upper Limit (kW)")
    ax1.set_title(f"A. D095 {len(ul95)} Star-Band 10-m EIRP Upper Limits (0.38–34.5 µm)")
    ax1.legend(loc="upper left", frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: 401-Star Distance vs Best Panchromatic Limit
    d_old, p_old, d_new, p_new = [], [], [], []
    for r in u401:
        if not r["min_panchromatic_10m_kw"] or not r["dist_pc"]:
            continue
        dv, pv = float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"])
        if dv <= 0 or pv <= 0:
            continue
        if "D095" in r["phases"]:
            d_new.append(dv)
            p_new.append(pv)
        else:
            d_old.append(dv)
            p_old.append(pv)

    ax2.scatter(d_old, p_old, s=16, color="#6baed6", alpha=0.72, label=f"D079–D094 Stars ({len(d_old)})")
    ax2.scatter(d_new, p_new, s=62, marker="D", color="#d95f02", edgecolor="black", lw=0.65, zorder=4, label=f"D095 Cohort & Bridges ({len(d_new)})")
    ax2.axvline(10.0, color="#1b7837", linestyle="--", lw=1.2, label=f"<10 pc Census: {syn['within_10pc_unique_stars']} stars (med {syn['within_10pc_median_limit_kw']:.3f} kW)")

    ann_targets = {
        "PROXIMACEN": (2.5, 8e-5),
        "TAUCET": (1.55, 2.8e-2),
        "SIRIUS": (2.2, 6e-1),
        "FOMALHAUT": (14.5, 4.5e-2),
        "GJ3801": (18.0, 6.0e-1),
    }
    for r in u401:
        if r["star"] in ann_targets and r["min_panchromatic_10m_kw"]:
            dv, pv = float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"])
            tx, ty = ann_targets[r["star"]]
            ax2.annotate(r["star"], xy=(dv, pv), xytext=(tx, ty), fontsize=7.6, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(1.0, 1e8)
    ax2.set_ylim(2e-5, 2.0e14)
    ax2.set_xlabel("Heliocentric Distance (pc, log scale)")
    ax2.set_ylabel("Best Panchromatic 10-m EIRP Limit (kW)")
    ax2.set_title("B. Unified 401-Star Survey (25 Spectrographs, 33 Arms, 8.709 Octaves)")
    ax2.legend(loc="upper left", frameon=True)
    ax2.text(
        0.97, 0.05,
        f"D079–D095 Landmark Totals:\n"
        f"• {syn['unique_stars_total']} unique stars ({syn['panchromatic_bridge_stars_total']} bridges, {syn['panchromatic_bridge_cells_total']} cells)\n"
        f"• {syn['total_exposures_d079_d095']:,} exposures ({syn['total_integration_hours_d079_d095']:.1f} h)\n"
        f"• {syn['cumulative_orbital_campaigns']} orbital camp. | {syn['total_calibration_trials_d079_d095']:,} cal. trials\n"
        f"• 0.0905–37.86 µm (8.709 oct.) -> 0 ETI",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=7.8,
        bbox=dict(boxstyle="round,pad=0.35", fc="#fff8e7", ec="#d95f02"),
    )
    ax2.grid(True, which="both", alpha=0.22)

    fig.suptitle("Phase D095 (V5.3): 401-Star Panchromatic Survey & 8.709-Octave (0.0905–37.86 µm) Synthesis", y=0.99)
    _save(fig, "fig01_d095_panchromatic_401stars_8p71octaves.png")


def fig02_curved_periodic_drift(summary: dict[str, Any]) -> None:
    d_all = _read_csv("DRIFT_V53_CURVED_PERIODIC_RESULTS.csv")
    cal = _read_csv("CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.5), gridspec_kw={"width_ratios": [1.08, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    src_meta = [
        ("D095", "D095 APOGEE-2 N=6..26 (9 camp., 0 surv.)", "#1b9e77", "o"),
        ("D091_ARCHIVE_Q", "D091 Archive Q N>=4 Retro (12 camp., 0 surv.)", "#2b8cbe", "s"),
        ("D094_ARCHIVE_T", "D094 Archive T N>=4 Retro (5 camp., 0 surv.)", "#d95f02", "D"),
    ]
    for src, lbl, col, mk in src_meta:
        sub = [r for r in d_all if r["phase_source"] == src]
        dt = [max(0.2, float(r["dt_baseline_days"])) for r in sub]
        ev = [max(1.0, float(int(r["n_curved_evals"]) + int(r["n_periodic_evals"]) + 1)) for r in sub]
        sz = [40 + 11 * int(r["n_epochs"]) for r in sub]
        ax1.scatter(dt, ev, s=sz, color=col, marker=mk, edgecolor="black", lw=0.6, alpha=0.86, label=lbl, zorder=4 if src == "D095" else 3)

    ann = {
        ("D095", "KEPLER1869"): (0.04, 1.5),
        ("D095", "KEPLER37"): (0.35, 3.2),
        ("D095", "2M00100614"): (0.08, 0.25),
        ("D091_ARCHIVE_Q", "HD213885"): (0.14, 1.6),
        ("D091_ARCHIVE_Q", "KEPLER156"): (1.5, 2.4),
    }
    for r in d_all:
        key = (r["phase_source"], r["star"])
        if key in ann:
            dx = max(0.2, float(r["dt_baseline_days"]))
            dy = max(1.0, float(int(r["n_curved_evals"]) + int(r["n_periodic_evals"]) + 1))
            mx, my = ann[key]
            raw_t = int(r["raw_nonlinear_tracks"])
            tag = f"{r['star']} (N={r['n_epochs']}, raw {raw_t}->0)" if raw_t > 0 else f"{r['star']} (N={r['n_epochs']})"
            ax1.annotate(tag, xy=(dx, dy), xytext=(dx * mx, dy * my), fontsize=7.6, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(1.2, 1.2e4)
    ax1.set_ylim(0.5, 4.0e7)
    ax1.set_xlabel("Multi-Epoch Baseline $\\Delta t$ (days, log scale)")
    ax1.set_ylabel("Curved + Periodic Search Evaluations (+1, log scale)")
    ax1.set_title(f"A. DRIFT_V53 Across All {len(d_all)} N>=4 Campaigns (0 Survivors)")
    ax1.legend(loc="upper left", frameon=True)
    ax1.grid(True, which="both", alpha=0.22)

    classes = [
        ("CURVED_QUADRATIC", "Curved\nQuadratic\nRecov. (60)", "#1b9e77"),
        ("PERIODIC_ORBITAL", "Periodic\nOrbital\nRecov. (60)", "#2b8cbe"),
        ("STATIONARY_STELLAR", "Stationary\nStellar\nVeto (40)", "#7570b3"),
        ("SINGLE_EPOCH_TRANSIENT", "1-Epoch\nTransient\nVeto (40)", "#7570b3"),
        ("BERV_SKY_CONFOUNDER", "BERV Sky\nConfounder\nVeto (40)", "#7570b3"),
    ]
    x2 = np.arange(len(classes))
    rates = []
    for k, _, _ in classes:
        sub = [r for r in cal if r["trial_class"] == k]
        rates.append(100.0 * sum(int(r["passed"]) for r in sub) / max(1, len(sub)))
    ax2.bar(x2, rates, color=[c[2] for c in classes], width=0.58)
    for xi, rv, (k, _, _) in zip(x2, rates, classes):
        sub = [r for r in cal if r["trial_class"] == k]
        p = sum(int(r["passed"]) for r in sub)
        ax2.text(xi, rv + 1.4, f"{rv:.1f}%\n({p}/{len(sub)})", ha="center", va="bottom", fontsize=7.9, fontweight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels([c[1] for c in classes])
    ax2.set_ylim(0, 118)
    ax2.set_ylabel("Completeness / Specificity (%)")
    ax2.set_title("B. CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240 (240 Trials)")
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Phase D095 DRIFT_V53_CURVED_AND_PERIODIC: 26 N>=4 Multi-Epoch Campaigns & 240 Calibration Trials", y=0.99)
    _save(fig, "fig02_d095_curved_periodic_drift_v53.png")


def fig03_ghost_sky_and_orbits(summary: dict[str, Any], bundle: dict[str, Any]) -> None:
    gsky = _read_csv("GHOST_SKY_FIBER_VETO_SUMMARY.csv")
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_8.csv")

    fig = plt.figure(figsize=(15.4, 7.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.42, wspace=0.52)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    # Panel A: GHOST simultaneous sky-IFU veto by star
    y1 = np.arange(len(gsky))
    seeds = [int(r["g1_seeds"]) for r in gsky]
    vet_g1 = [int(r["sky_fiber_vetoed_standalone"]) for r in gsky]
    vet_g2 = [int(r["sky_fiber_vetoed_post_g2"]) for r in gsky]
    ax1.barh(y1 - 0.20, seeds, height=0.38, color="#6baed6", label="G1 LSF Seeds")
    ax1.barh(y1 + 0.20, vet_g1, height=0.38, color="#d95f02", label="Simult. HDU[4..5] Sky-IFU Vetoed")
    for i, (sd, vg1, vg2, r) in enumerate(zip(seeds, vet_g1, vet_g2, gsky)):
        raw_s1 = int(r.get("v53_stage1_raw", 0))
        note = f"{sd} -> {vg1} sky (raw {raw_s1}->0 ETI)" if raw_s1 > 0 else f"{sd} -> {vg1} sky (0 ETI)"
        ax1.text(max(sd, vg1) + 1.0, i, note, va="center", fontsize=7.5)
    ax1.set_yticks(y1)
    ax1.set_yticklabels([f"{r['star']} ({r['n_epochs']} ep)" for r in gsky])
    ax1.set_ylim(len(gsky) + 0.6, -0.6)
    ax1.set_xlim(0, 108)
    ax1.set_xlabel("Candidate Seed Count")
    ax1.set_title("A. GEMINI_GHOST Simultaneous Sky-IFU Veto (7 Targets, 13 Exps)")
    ax1.legend(loc="lower right", frameon=True, fontsize=7.4)
    ax1.grid(axis="x", alpha=0.25)

    # Panel B: 8 Orbital Campaigns #126-#133
    y2 = np.arange(len(orb))
    kps = [float(r["kp_kms"]) for r in orb]
    dvs = [float(r["orbital_dv_span_kms"]) for r in orb]
    ax2.barh(y2 - 0.19, kps, height=0.36, color="#2b8cbe", label="$K_p$ Semi-Amplitude (km s$^{-1}$)")
    ax2.barh(y2 + 0.19, dvs, height=0.36, color="#1b9e77", alpha=0.86, label="Observed $\\Delta v_{\\rm orb}$ Span (km s$^{-1}$)")
    for i, (kp, dv) in enumerate(zip(kps, dvs)):
        ax2.text(max(kp, dv) + 4.0, i, "0 ETI", va="center", fontsize=7.6)
    ax2.set_yticks(y2)
    ax2.set_yticklabels([f"#{r['campaign_index']} {r['planet_name']} (N={r['n_epochs']})" for r in orb])
    ax2.set_ylim(len(orb) + 0.8, -0.6)
    ax2.set_xlim(0, 445)
    ax2.set_xlabel("Orbital Velocity Scale (km s$^{-1}$)")
    ax2.set_title("B. Orbital Campaigns #126–#133 (Cumulative = 133 -> 0 ETI)")
    ax2.legend(loc="upper right", frameon=True, fontsize=7.4)
    ax2.grid(axis="x", alpha=0.25)

    # Panel C & D: Forensic Stage-2 Profiles directly from bundle (dp_id = GHOST.S...)
    cfg_g = det.get_inst_config("GEMINI_GHOST", 56000.0)
    ltt_u = None
    mas_u = None
    for ex in bundle["exposures"]:
        if ex["dp_id"] == "GHOST.S20240827S0062":
            ltt_u = _unpack_exposure_spectrum(ex, cfg_g, compute_cont=True)
        elif ex["dp_id"] == "GHOST.S20240702S0246":
            mas_u = _unpack_exposure_spectrum(ex, cfg_g, compute_cont=True)

    if ltt_u is not None:
        w, fl, cont = ltt_u["arms"][0]["w_bary"], ltt_u["arms"][0]["flux"], ltt_u["arms"][0]["cont"]
        m = (w >= 4295.0) & (w <= 4322.0) & np.isfinite(fl)
        ax3.plot(w[m], fl[m], color="#2b8cbe", lw=0.85, label="LTT 9779 Native Flux (ADU)")
        ax3.plot(w[m], cont[m], color="#d95f02", lw=1.2, ls="--", label="Block-60 Running Cont. (~1.4 Å)")
        p95_outer = float(np.percentile(fl[(w >= 4312.0) & (w <= 4320.0) & np.isfinite(fl)], 95.0))
        ax3.axhline(p95_outer, color="#1b7837", lw=1.2, ls=":", label=f"4312–4320 Å Photosphere ({p95_outer:.0f} ADU)")
        ax3.axvline(4305.138, color="#e34a33", lw=1.1, alpha=0.85)
        ax3.annotate("CH G-band crest\n(F_pk/P95=0.941)", xy=(4305.14, 3438.0), xytext=(4296.0, 3850.0), fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.75))
        ax3.set_ylim(0, max(float(np.max(fl[m])) * 1.25, 4500.0))
        ax3.set_xlabel("Barycentric Vacuum Wavelength (Å)")
        ax3.set_ylabel("Flux (ADU)")
        ax3.set_title("C. Stage-2 Veto #1: LTT 9779 4305.28 Å Sub-Photospheric Crest")
        ax3.legend(loc="lower right", frameon=True, fontsize=7.2)
        ax3.grid(alpha=0.22)

    if mas_u is not None:
        red_arm = [a for a in mas_u["arms"] if "RED" in a["arm"]][0]
        w, fl = red_arm["w_bary"], red_arm["flux"]
        m = (w >= 8605.7) & (w <= 8607.3) & np.isfinite(fl)
        ax4.plot(w[m], fl[m], color="#d95f02", marker="o", ms=3.5, lw=1.25, label="MASCARA-1 S0246_red001 (N=1 CR split core)")
        ax4.axhline(16050.0, color="#555555", ls="--", lw=1.0, label="Local Continuum (~16,050 ADU)")
        ax4.annotate("Split M-core\n17,168 / 16,928 / 17,072", xy=(8606.484, 17168.0), xytext=(8605.76, 17050.0), fontsize=7.4, arrowprops=dict(arrowstyle="->", lw=0.8))
        ax4.text(
            0.97, 0.06,
            "CADC Same-Night Adjacent Exposures (+28..34 min):\n"
            "S0267=1.008x | S0268=1.010x | S0270=1.005x | S0271=1.017x\n"
            "-> Flat continuum (100% transient cosmic-ray veto)",
            transform=ax4.transAxes, ha="right", va="bottom", fontsize=7.2,
            bbox=dict(boxstyle="round,pad=0.3", fc="#eef7f2", ec="#1b7837"),
        )
        ax4.set_ylim(15550.0, 17750.0)
        ax4.set_xlabel("Barycentric Vacuum Wavelength (Å)")
        ax4.set_ylabel("Flux (ADU)")
        ax4.set_title("D. Stage-2 Veto #2: MASCARA-1 8606.48 Å Single-Exp DRAGONS CR")
        ax4.legend(loc="upper right", frameon=True, fontsize=7.2)
        ax4.grid(alpha=0.22)

    fig.suptitle("Phase D095 GEMINI_GHOST Simultaneous Sky-IFU Veto, Orbital Campaigns #126–#133, and Stage-2 Physical Triage", y=0.99)
    _save(fig, "fig03_d095_ghost_sky_fiber_veto_and_orbits.png")


def fig04_spitzer_dyson_vs_silicate(summary: dict[str, Any], bundle: dict[str, Any]) -> None:
    sp18 = _read_csv("SPITZER_IRS_CCF_AND_DYSON_18STARS.csv")
    cal = _read_csv("CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.5), gridspec_kw={"width_ratios": [1.08, 1.0]})
    fig.subplots_adjust(wspace=0.28)

    # Panel A: Real Spitzer IRS Normalized SEDs comparing silicate dust disks vs clean photospheres + synthetic 220K Dyson curve
    sp_map = {r["star"]: r for r in sp18}
    show_stars = [
        ("HD69830", f"HD 69830 (Warm Silicate Belt, {float(sp_map['HD69830']['silicate_excess_sigma']):.1f}$\\sigma$)", "#d95f02", 1.8),
        ("HR8799", f"HR 8799 (Debris + Cold Dust, {float(sp_map['HR8799']['silicate_excess_sigma']):.1f}$\\sigma$)", "#7570b3", 1.5),
        ("FOMALHAUT", f"Fomalhaut (Kuiper Analog, {float(sp_map['FOMALHAUT']['silicate_excess_sigma']):.1f}$\\sigma$)", "#e7298a", 1.5),
        ("TAUCET", "$\\tau$ Ceti (Clean Photosphere Ref.)", "#1b9e77", 1.3),
    ]
    exp_by_star = {ex["star"]: ex for ex in bundle["exposures"] if ex["instrument"] == "SPITZER_IRS"}
    for st, lbl, col, lw in show_stars:
        ex = exp_by_star[st]
        w_um = _decode_wave(ex["arms"][0]["wave"]) / 1e4
        f_jy = _decode_float_arr(ex["arms"][0]["flux_jy"])
        assert f_jy is not None
        ref = float(np.nanmedian(f_jy[(w_um >= 5.5) & (w_um <= 7.0) & np.isfinite(f_jy)]))
        f_norm = (f_jy / max(1e-12, ref)) * ((w_um / 6.0) ** 2)
        m = np.isfinite(f_norm) & (w_um >= 5.3) & (w_um <= 36.5)
        ax1.plot(w_um[m], f_norm[m], color=col, lw=lw, label=lbl)

    wg = np.linspace(5.5, 36.5, 220)
    lm = wg * 1e-6
    b_p = 1.0 / ((lm ** 3) * np.expm1((6.62607e-34 * 2.99792e8) / (lm * 1.38065e-23 * 5500.0)))
    b_d = 1.0 / ((lm ** 3) * np.expm1((6.62607e-34 * 2.99792e8) / (lm * 1.38065e-23 * 210.0)))
    mod_dyson = (1.0 + 0.08 * ((5500.0 / 210.0) ** 4) * (b_d / b_p))
    ax1.plot(wg, mod_dyson, color="black", ls="--", lw=1.4, label="Synthetic 210 K Smooth Dyson Blackbody ($\\gamma=0.08$)")
    ax1.axvspan(8.5, 12.2, color="#fee0b6", alpha=0.35, label="9.8–11.3 µm Silicate Emission Band")
    ax1.axvspan(17.5, 25.0, color="#fddbc7", alpha=0.25)
    ax1.set_yscale("log")
    ax1.set_xlim(5.2, 37.0)
    ax1.set_ylim(0.5, 95.0)
    ax1.set_xlabel("Spitzer IRS Wavelength (µm)")
    ax1.set_ylabel("$(\\lambda / 6\\,\\mu\\mathrm{m})^2\\,F_\\nu(\\lambda)/F_\\nu(6\\,\\mu\\mathrm{m})$ (Photosphere = 1)")
    ax1.set_title("A. Spitzer IRS Spectral Discrimination: Silicate Dust vs Dyson Blackbody")
    ax1.legend(loc="upper left", frameon=True, fontsize=7.5)
    ax1.grid(True, which="both", alpha=0.22)

    # Panel B: Silicate Excess Sigma vs Dyson Blackbody SNR Across All 18 Targets
    sil_s = [float(r["silicate_excess_sigma"]) for r in sp18]
    dys_s = [float(r["dyson_snr_excess"]) for r in sp18]
    cols_b = ["#d95f02" if r["dyson_status"] == "NATURAL_SILICATE_OR_DEBRIS_EXCESS" else ("#7570b3" if r["role"] == "CONTROL" else "#2b8cbe") for r in sp18]
    ax2.scatter(sil_s, dys_s, s=64, c=cols_b, edgecolor="black", lw=0.65, zorder=4)
    ax2.axvline(3.0, color="#d95f02", ls="--", lw=1.2, label="Silicate Veto ($\\sigma_{\\rm sil} > 3.0$)")
    ax2.axhline(6.0, color="#1b7837", ls=":", lw=1.2, label="Dyson Excess Threshold ($> 6.0\\sigma$)")
    ann_b = {
        "HD69830": (-24.0, 1100.0),
        "HR8799": (4.0, 1250.0),
        "FOMALHAUT": (6.0, 1450.0),
        "SIRIUS": (8.0, -400.0),
        "HD10647": (6.0, 800.0),
    }
    for r in sp18:
        if r["star"] in ann_b:
            sx, sy = float(r["silicate_excess_sigma"]), float(r["dyson_snr_excess"])
            dx, dy = ann_b[r["star"]]
            ax2.annotate(f"{r['star']} ({sx:.1f}$\\sigma$)", xy=(sx, sy), xytext=(sx + dx, sy + dy), fontsize=7.6, arrowprops=dict(arrowstyle="->", lw=0.7), zorder=6)

    dy_tp = sum(int(r["passed"]) for r in cal if r["trial_class"] == "DYSON_WASTE_BB")
    sil_tn = sum(int(r["passed"]) for r in cal if r["trial_class"] == "SILICATE_DEBRIS_DISK")
    ax2.set_ylim(-500, 9200)
    ax2.text(
        0.97, 0.34,
        f"18-Star Empirical Summary:\n"
        f"• Dyson Candidates: 0/18\n"
        f"• Strong Silicate Bands: HD69830, HR8799, FOMALHAUT\n"
        f"Calib (120 Dyson+Silicate Trials):\n"
        f"• Dyson 100–400 K Recov: {dy_tp}/60 ({100*dy_tp/60:.1f}%)\n"
        f"• Silicate Debris Veto: {sil_tn}/60 ({100*sil_tn/60:.1f}%)",
        transform=ax2.transAxes, ha="right", va="center", fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.35", fc="#eef7f2", ec="#1b7837"),
    )
    ax2.set_xlabel("Silicate 10 + 18–24 µm Excess Significance ($\\sigma_{\\rm sil}$)")
    ax2.set_ylabel("Dyson Waste-Heat Continuum Excess SNR ($\\sigma_{\\rm Dyson}$)")
    ax2.set_title("B. All 18 Spitzer IRS Targets in Silicate vs Dyson Plane (0 Dyson ETI)")
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(alpha=0.25)

    fig.suptitle("Phase D095 Spitzer IRS (5.2–37.86 µm) Dyson Sphere Waste-Heat vs Silicate Debris-Belt Discrimination", y=0.99)
    _save(fig, "fig04_d095_spitzer_irs_dyson_vs_silicate.png")


def fig05_spitzer_greenhouse_and_eirp(summary: dict[str, Any]) -> None:
    sp18 = _read_csv("SPITZER_IRS_CCF_AND_DYSON_18STARS.csv")
    ul95 = [r for r in _read_csv("EIRP_UPPER_LIMITS_D095.csv") if r["instrument"] == "SPITZER_IRS"]
    cal = _read_csv("CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.8), gridspec_kw={"width_ratios": [1.12, 1.0]})
    fig.subplots_adjust(wspace=0.34)

    cols = ["cf4_sigma", "c2f6_sigma", "sf6_sigma", "nf3_sigma", "cfc11_sigma", "cfc12_sigma", "max_confounder_sigma"]
    lbls = ["CF$_4$", "C$_2$F$_6$", "SF$_6$", "NF$_3$", "CFC-11", "CFC-12", "Max Nat.\nConf."]
    mat = np.zeros((len(sp18), len(cols)))
    for i, r in enumerate(sp18):
        for j, c in enumerate(cols):
            mat[i, j] = float(r[c])
    im = ax1.imshow(np.clip(mat, 0.0, 9.0), cmap="YlOrRd", vmin=0.0, vmax=9.0, aspect="auto")
    cbar = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.03)
    cbar.set_label("|CCF Significance| ($\\sigma$, clipped at 9)")
    for i in range(len(sp18)):
        for j in range(len(cols)):
            v = mat[i, j]
            ax1.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.2, color="white" if v >= 5.5 else "black", fontweight="bold" if v >= 5.0 else "normal")
    ax1.axvline(5.5, color="black", ls="--", lw=1.2)
    ax1.set_xticks(range(len(lbls)))
    ax1.set_xticklabels(lbls)
    ax1.set_yticks(range(len(sp18)))
    ax1.set_yticklabels([f"{r['star']} ({'CTRL' if r['role']=='CONTROL' else str(int(round(float(r['teff_k']))))+'K'})" for r in sp18], fontsize=7.7)
    ax1.set_title("A. Spitzer IRS 18 Stars × 6 Greenhouse Gases vs Natural Confounders (0 ETI)")

    bands = ["S1_65000", "S2_106000", "S3_180000", "S4_260000", "S5_345000"]
    b_um = ["6.5 µm", "10.6 µm\n(CO$_2$)", "18.0 µm", "26.0 µm", "34.5 µm"]
    data_box = [[float(r["p_beam_10m_kw"]) for r in ul95 if r["band_id"] == b] for b in bands]
    pos = np.arange(len(bands))
    ax2.boxplot(data_box, positions=pos, widths=0.45, patch_artist=True, boxprops=dict(facecolor="#9ecae1", color="#08519c"), medianprops=dict(color="#d95f02", lw=1.8))
    for i, vals in enumerate(data_box):
        xs = np.full(len(vals), float(pos[i])) + np.linspace(-0.12, 0.12, len(vals))
        ax2.scatter(xs, vals, s=18, color="#08519c", alpha=0.75, zorder=4)
    ax2.set_yscale("log")
    ax2.set_xticks(pos)
    ax2.set_xticklabels(b_um)
    best_sp = min(ul95, key=lambda r: float(r["p_beam_10m_kw"]))
    ax2.set_ylim(4e2, 8e7)
    ax2.set_ylabel("3$\\sigma$ 10-m Directed Laser EIRP Limit (kW)")
    ax2.set_title(f"B. Spitzer IRS 5-Band 10-m EIRP (Best: {best_sp['star']} {float(best_sp['p_beam_10m_kw']):.4f} kW)")
    g_tp = sum(int(r["passed"]) for r in cal if r["trial_class"] == "GAS_INJECTION")
    c_tn = sum(int(r["passed"]) for r in cal if r["trial_class"] == "SPECTRAL_CONFOUNDER")
    ax2.text(
        0.03, 0.96,
        f"CCF Calibration (120 Trials):\n"
        f"• 6-Gas Injections: {g_tp}/60 ({100*g_tp/60:.1f}%)\n"
        f"• Natural Confounders: {c_tn}/60 ({100*c_tn/60:.1f}% vetoed)",
        transform=ax2.transAxes, ha="left", va="top", fontsize=7.8,
        bbox=dict(boxstyle="round,pad=0.34", fc="#eef7f2", ec="#1b7837"),
    )
    ax2.grid(axis="y", which="both", alpha=0.22)

    fig.suptitle("Phase D095 Spitzer IRS Union-Excluded 6-Gas Greenhouse CCF & 5-Band (6.5–34.5 µm) 10-m EIRP Limits", y=0.99)
    _save(fig, "fig05_d095_spitzer_irs_greenhouse_ccf_and_eirp.png")


def fig06_ellipsoid401_and_cal1911(summary: dict[str, Any]) -> None:
    ell = _read_csv("MULTIEVENT_ELLIPSOID_401STARS.csv")
    led = _read_csv("V5_3_CANDIDATE_LEDGER.csv")
    cal = summary["synthetic_calibration_1911_trials"]
    se = summary["searched_spectral_elements"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.6, 5.8), gridspec_kw={"width_ratios": [1.0, 1.15]})
    fig.subplots_adjust(wspace=0.58)

    abs_b = [abs(float(r["ecliptic_lat_deg"])) for r in ell]
    dt_m = [max(0.5, float(r["min_abs_ellipsoid_dt_days"])) for r in ell]
    is_etz = [r["etz_qualified"] == "True" for r in ell]
    is_d95 = ["D095" in r["phases"] for r in ell]

    ax1.scatter([b for b, e, d in zip(abs_b, is_etz, is_d95) if not e and not d], [t for t, e, d in zip(dt_m, is_etz, is_d95) if not e and not d], s=14, color="#8da0cb", alpha=0.60, label="D079–D094 Stars")
    ax1.scatter([b for b, d in zip(abs_b, is_d95) if d], [t for t, d in zip(dt_m, is_d95) if d], s=50, marker="s", color="#1b9e77", edgecolor="black", lw=0.6, zorder=4, label="D095 Cohort & Bridges (35)")
    ax1.scatter([b for b, e in zip(abs_b, is_etz) if e], [t for t, e in zip(dt_m, is_etz) if e], s=85, marker="D", color="#d95f02", edgecolor="black", lw=0.75, zorder=5, label=f"Earth Transit Zone ({sum(is_etz)} stars)")

    for r in ell:
        if r["star"] in ("2M00100614", "HD69830", "HD111031", "WOLF359"):
            bx = abs(float(r["ecliptic_lat_deg"]))
            dy = max(0.5, float(r["min_abs_ellipsoid_dt_days"]))
            ax1.annotate(f"{r['star']}", xy=(bx, dy), xytext=(bx + 5.5, dy * 1.45), fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.7))

    ax1.axvline(0.265, color="#d95f02", ls="--", lw=1.1, label="ETZ $|\\beta| \\leq 0.265^\\circ$")
    n_w180 = sum(1 for r in ell if r["ellipsoid_qualified_180d"] == "True")
    ax1.axhline(180.0, color="#1b7837", ls=":", lw=1.2, label=f"Ellipsoid $\\leq 180$ d ({n_w180} stars)")
    ax1.set_yscale("log")
    ax1.set_xlabel("Absolute Ecliptic Latitude $|\\beta|$ (deg)")
    ax1.set_ylabel("Min Multi-Event Sync Offset $|\\Delta t_{\\rm sync}|$ (days)")
    ax1.set_title(f"A. {len(ell)}-Star Multi-Event Ellipsoid & ETZ ({sum(is_etz)} ETZ / {n_w180} <=180d)")
    ax1.legend(loc="upper right", frameon=True, fontsize=7.5)
    ax1.grid(True, which="both", alpha=0.22)

    def _pct(tok: str) -> float:
        part = tok.split("(")[-1].rstrip(")") if "(" in tok else tok
        if "/" in part:
            a, b = part.split("/")
            return 100.0 * float(a) / float(b)
        return 100.0 * float(part)

    def _inv_pct(tok: str) -> float:
        a, b = tok.split("/")
        return 100.0 * (1.0 - float(a) / float(b))

    suites = [
        ("Drift V53 Curved Recov.", _pct(cal["curved_drift_v53_recovery"])),
        ("Drift V53 Periodic Recov.", _pct(cal["periodic_drift_v53_recovery"])),
        ("Drift V53 Stat./Trans./BERV Veto", (_pct(cal["cp_drift_stationary_veto"]) + _pct(cal["cp_drift_transient_veto"]) + _pct(cal["cp_drift_berv_sky_veto"])) / 3.0),
        ("Spitzer IRS 6-Gas CCF", _pct(cal["spitzer_gas_ccf_recovery"])),
        ("Spitzer IRS Dyson BB Recov.", _pct(cal["spitzer_dyson_bb_recovery"])),
        ("Spitzer Conf. + Silicate Veto", 0.5 * (_pct(cal["spitzer_spectral_conf_veto"]) + _pct(cal["spitzer_silicate_debris_veto"]))),
        ("GHOST Sky-IFU Clean Pass", _pct(cal["ghost_sky_fiber_clean_pass"])),
        ("GHOST Sky-IFU Airglow Veto", _pct(cal["ghost_sky_fiber_airglow_veto"])),
        ("G8_V53 Isolated / Shared+Topo Veto", 0.5 * (_pct(cal["g8_v53_isolated_pass"]) + _pct(cal["g8_v53_shared_suppression"]))),
        ("RPCA Rarity Recov. & Veto", 0.5 * (_pct(cal["rpca_isolated_recovery"]) + _pct(cal["rpca_shared_suppression"]))),
        ("Agnostic Multi-Scale Recov.", _pct(cal["agnostic_multiscale_recovery"])),
        ("G4+G5 Native LSF / CR+Plateau", _pct(cal["g45_true_lsf_pass"])),
        ("Channel P Injection (>=8s)", _pct(cal["channel_p_ge_8sigma"])),
        ("COMB V4.1 Recov. & Forest Veto", 0.5 * (_pct(cal["comb_v41_recovery"]) + 0.5 * (_inv_pct(cal["comb_v41_forest_fa"]) + _inv_pct(cal["comb_v41_topo_fa"])))),
        ("Keplerian K_PLANET Recovery", _pct(cal["keplerian_kplanet_rec"])),
    ]
    y2 = np.arange(len(suites))
    vals2 = [v for _, v in suites]
    cols2 = ["#1b9e77" if v >= 95.0 else "#2b8cbe" for v in vals2]
    ax2.barh(y2, vals2, color=cols2, height=0.68)
    for i, v in enumerate(vals2):
        ax2.text(v - 1.8 if v > 84 else v + 1.5, i, f"{v:.1f}%", va="center", ha="right" if v > 84 else "left", color="white" if v > 84 else "black", fontsize=7.6, fontweight="bold")
    ax2.set_yticks(y2)
    ax2.set_yticklabels([n for n, _ in suites], fontsize=7.9)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 104)
    ax2.set_xlabel("Completeness / Specificity (%)")
    n_raw_s1 = sum(1 for r in led if r["qualified_v53"] == "True")
    n_ver_eti = sum(1 for r in led if r["verified_eti"] == "True")
    ax2.set_title(f"B. {cal['total_trials']:,} Cal. Trials (Stage-1 {n_raw_s1} -> Stage-2 {n_ver_eti} ETI)")
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("Phase D095 401-Star Multi-Event Ellipsoid Geometry & 1,911-Trial V5.3 Calibration Scorecard", y=0.99)
    _save(fig, "fig06_d095_multievent_ellipsoid_401stars_cal.png")


def main() -> None:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    with gzip.open(BUNDLE, "rt", encoding="utf-8") as gz:
        bundle = json.load(gz)
    fig01_panchromatic_401stars(summary)
    fig02_curved_periodic_drift(summary)
    fig03_ghost_sky_and_orbits(summary, bundle)
    fig04_spitzer_dyson_vs_silicate(summary, bundle)
    fig05_spitzer_greenhouse_and_eirp(summary)
    fig06_ellipsoid401_and_cal1911(summary)
    print("ALL 6 D095 FIGURES GENERATED SUCCESSFULLY.", flush=True)


if __name__ == "__main__":
    main()
