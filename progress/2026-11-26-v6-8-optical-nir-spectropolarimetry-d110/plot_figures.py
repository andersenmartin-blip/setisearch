#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D110 Publication Figure Generator (`fig151–fig156`, 240-DPI PNGs):
  - fig151_d110_polarimetric_cohort_stokes_coverage.png
  - fig152_d110_stokes_null_zeeman_diagnostics.png
  - fig153_d110_p1_p5_cascade_and_16cygb_pentaregime.png
  - fig154_d110_polarized_eirp_and_qu_mdp99_limits.png
  - fig155_d110_v68_calibration_37suites_96345trials.png
  - fig156_d110_unified_panchromatic_bayesian_ftx_polarimetry.png
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
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


def make_fig151_cohort_coverage(spec: list[dict[str, str]], cohort: list[dict[str, str]], summary: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Panel A: Distance vs RA across 49 D110 targets (41 bridges + 8 brand-new)
    ax = axes[0]
    by_star_role: dict[str, dict[str, Any]] = {}
    for r in cohort:
        st = r["canonical_target"]
        d = by_star_role.setdefault(st, {
            "ra": float(r["s_ra"]), "dist": float(r["dist_pc"]),
            "new": r["is_prior_bridge"] != "True", "insts": set(), "stokes": set(),
        })
        d["insts"].add(r["instrument"])
        d["stokes"].add(r["stokes"])

    groups = [
        ("Prior Bridges (Opt/NIR Pol, 41)", lambda v: not v["new"] and len(v["insts"]) == 1, "#1d4ed8", "o", 42),
        ("Multi-Facility Bridges (Opt+NIR)", lambda v: not v["new"] and len(v["insts"]) >= 2, "#7c3aed", "D", 64),
        ("Brand-New Polarimetric Stars (8, sep >= 850\")", lambda v: v["new"], "#dc2626", "*", 130),
    ]
    for lbl, pred, col, mk, sz in groups:
        sub = [(k, v) for k, v in by_star_role.items() if pred(v)]
        if not sub:
            continue
        ax.scatter([v["ra"] for _, v in sub], [v["dist"] for _, v in sub], s=sz, c=col, marker=mk, alpha=0.88, edgecolors="white", linewidths=0.5, label=lbl, zorder=4)

    for tag, dx, dy in [("16CYGB", 4, 6), ("HD102195", -14, 9), ("V410TAU", 4, -10), ("53CAM", 5, 5), ("ADLEO", 4, -10), ("EVLAC", 4, -10)]:
        if tag in by_star_role:
            v = by_star_role[tag]
            ax.annotate(tag, (v["ra"], v["dist"]), xytext=(dx, dy), textcoords="offset points", fontsize=7.3, fontweight="bold")
    ax.axvline(180.0, color="#94a3b8", ls=":", lw=1.0)
    ax.set_yscale("log")
    ax.set_xlim(-10, 370)
    ax.set_xlabel("Right Ascension (deg)")
    ax.set_ylabel("Distance (pc)")
    ax.set_title("A. Phase D110 Cohort: 49 Stars (41 Bridges + 8 Brand-New -> 1,012 Total)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.92)

    # Panel B: Stokes (Q, U, V) breakdown across 3 Polarimetric Facilities
    ax = axes[1]
    insts = ["CFHT_ESPADONS_POL", "TBL_NARVAL", "CFHT_SPIROU_POL"]
    ilbls = ["CFHT ESPaDOnS\n(Optical)", "TBL NARVAL\n(67th Spec / 97th Arm)", "CFHT SPIRou\n(NIR YJHK)"]
    cnt_q = [sum(1 for r in spec if r["instrument"] == i and r["stokes"] == "Q") for i in insts]
    cnt_u = [sum(1 for r in spec if r["instrument"] == i and r["stokes"] == "U") for i in insts]
    cnt_v = [sum(1 for r in spec if r["instrument"] == i and r["stokes"] == "V") for i in insts]
    x = np.arange(len(insts))
    w = 0.25
    b1 = ax.bar(x - w, cnt_q, width=w, color="#0284c7", label="Stokes Q (Linear)")
    b2 = ax.bar(x, cnt_u, width=w, color="#059669", label="Stokes U (Linear)")
    b3 = ax.bar(x + w, cnt_v, width=w, color="#ea580c", label="Stokes V (Circular)")
    for bars in (b1, b2, b3):
        for b in bars:
            h = int(b.get_height())
            if h > 0:
                ax.text(b.get_x() + b.get_width() / 2, h + 0.5, f"{h}", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(ilbls)
    ax.set_ylim(0, max(cnt_v) + 6)
    ax.set_ylabel("Number of Valid Polarimetric Spectra")
    c_inf = summary["cohort"]
    ax.set_title(f"B. Stokes Parameter Distribution ({c_inf['analyzed_valid_observations_d110']} Spectra, {c_inf['paired_qu_sets_d110']} Paired Q/U Sets)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92)

    _save(fig, "fig151_d110_polarimetric_cohort_stokes_coverage.png")


def make_fig152_stokes_diagnostics(spec: list[dict[str, str]], cands: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Panel A: Empirical Stokes MAD vs Formal Pipeline Error Floor
    ax = axes[0]
    for inst, lbl, col, mk in [
        ("CFHT_ESPADONS_POL", "ESPaDOnS Optical", "#1d4ed8", "o"),
        ("TBL_NARVAL", "TBL NARVAL Optical", "#059669", "^"),
        ("CFHT_SPIROU_POL", "SPIRou NIR", "#dc2626", "s"),
    ]:
        sub = [r for r in spec if r["instrument"] == inst]
        mx = [max(1e-5, float(r["med_err"])) * 100.0 for r in sub]
        my = [max(1e-5, float(r["med_mad_p"])) * 100.0 for r in sub]
        ax.scatter(mx, my, s=36, c=col, marker=mk, alpha=0.85, edgecolors="white", linewidths=0.4, label=f"{lbl} (n={len(sub)})")
    lims = [0.02, 10.0]
    ax.plot(lims, lims, "k--", lw=1.2, alpha=0.65, label="1:1 Photon-Noise Limit")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Formal Stokes Pipeline Uncertainty (%)")
    ax.set_ylabel("Empirical Stokes P/I MAD Floor (%)")
    ax.set_title("A. Dual-Beam Polarimetric Noise Calibration Across 87 Spectra")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92)

    # Panel B: P1 Triggers in Physics Triage Plane (Unipolarity Ratio vs Opposite-Wing Zeeman S-curve Ratio)
    ax = axes[1]
    if cands:
        null_rej = [c for c in cands if int(c["p2_pass"]) == 0]
        zee_rej = [c for c in cands if int(c["p2_pass"]) == 1 and int(c["p3_pass"]) == 0]
        other_rej = [c for c in cands if int(c["p3_pass"]) == 1]
        if null_rej:
            ax.scatter([float(c["unipolarity_ratio"]) for c in null_rej], [min(1.5, float(c["opposite_wing_ratio"])) for c in null_rej], s=22, c="#94a3b8", marker="x", alpha=0.75, label=f"P2 Null N1/N2 Vetoed ({len(null_rej)})")
        if zee_rej:
            ax.scatter([float(c["unipolarity_ratio"]) for c in zee_rej], [min(1.5, float(c["opposite_wing_ratio"])) for c in zee_rej], s=26, c="#ea580c", marker="^", alpha=0.82, label=f"P3 Zeeman/Unpol Vetoed ({len(zee_rej)})")
        if other_rej:
            ax.scatter([float(c["unipolarity_ratio"]) for c in other_rej], [min(1.5, float(c["opposite_wing_ratio"])) for c in other_rej], s=32, c="#2563eb", marker="o", alpha=0.88, label=f"P4/P5 + Stage-2 Vetoed ({len(other_rej)})")
    else:
        ax.text(0.5, 0.5, "Zero P1 triggers above z>=7 across all 87 spectra", transform=ax.transAxes, ha="center", va="center")
    ax.axvline(0.55, color="#059669", ls="--", lw=1.2, label="Unipolarity Threshold (U >= 0.55)")
    ax.axhline(0.38, color="#dc2626", ls=":", lw=1.2, label="Max Opposite-Wing Ratio (0.38)")
    ax.set_xlim(-0.04, 1.05)
    ax.set_ylim(-0.05, 1.55)
    ax.set_xlabel("Signed Polarization Unipolarity Ratio |Sum(P)| / Sum(|P|)")
    ax.set_ylabel("Opposite-Polarity Zeeman Wing Ratio")
    ax.set_title("B. Gate P2-P4 Zeeman Antisymmetry & Null Veto Diagnostics (0 ETI)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92, fontsize=7.6)

    _save(fig, "fig152_d110_stokes_null_zeeman_diagnostics.png")


def make_fig153_cascade_pentaregime(summary: dict[str, Any], bridge_path: Path, u1012: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Panel A: V6.8 Funnel
    ax = axes[0]
    tri = summary["polarimetric_search_and_triage"]
    stages = ["P1 |z_P|>=7\nRaw Peaks", "P2 Null\nN1/N2 Veto", "P3 Zeeman &\nUnpol Veto", "P4 Emiss.\nExcess", "P5 Telluric\n+ LSF Pre-S2", "Verified\nETI"]
    vals = [
        int(tri["p1_raw_peaks"]),
        int(tri["p2_null_vetoed_pass"]),
        int(tri["p3_zeeman_vetoed_pass"]),
        int(tri["p4_unpol_emission_vetoed_pass"]),
        int(tri["p5_telluric_lsf_pass_pre_stage2"]),
        0,
    ]
    x = np.arange(len(stages))
    cols = ["#475569", "#0284c7", "#0d9488", "#d97706", "#7c3aed", "#16a34a"]
    bars = ax.bar(x, [max(0.5, v) for v in vals], color=cols, width=0.62, alpha=0.9)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, max(0.5, v) * 1.15, f"{v:,}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(0.3, max(100.0, max(vals) * 3.5))
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=8.0)
    ax.set_ylabel("Polarimetric Candidate Count (+0.5 floor for 0)")
    ax.set_title(f"A. POL_V68 Physics Cascade ({tri['pol_comb_qualified_pre_stage2']} Pol Combs -> 0 ETI)")

    # Panel B: 16 Cyg B Penta-Regime Bridge (Optical + NIR + X-ray + Gamma + Spectropolarimetry)
    ax = axes[1]
    br_rows = _read_csv(bridge_path)
    cyg_rows = [r for r in br_rows if r["star"] == "16CYGB" and r.get("wave_um") and r.get("p_beam_10m_kw")]
    w_um = [float(r["wave_um"]) for r in cyg_rows]
    l_iso = [float(r["l_iso_mw"]) for r in cyg_rows]
    # Split non-D110 vs D110 TBL_NARVAL
    prev_w = [float(r["wave_um"]) for r in cyg_rows if r["phase_id"] != "D110"]
    prev_l = [float(r["l_iso_mw"]) for r in cyg_rows if r["phase_id"] != "D110"]
    d110_w = [float(r["wave_um"]) for r in cyg_rows if r["phase_id"] == "D110"]
    d110_l = [float(r["l_iso_mw"]) for r in cyg_rows if r["phase_id"] == "D110"]
    if prev_w:
        ax.scatter(prev_w, prev_l, s=42, c="#1d4ed8", alpha=0.82, label=f"16 Cyg B Prior Opt/NIR/X/Gamma ({len(prev_w)} pts)")
    if d110_w:
        ax.scatter(d110_w, d110_l, s=110, c="#dc2626", marker="*", zorder=5, label=f"D110 TBL NARVAL Pol Bridge ({len(d110_w)} band)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Wavelength (um)")
    ax.set_ylabel(r"Isotropic Luminosity Limit $L_{\mathrm{iso}}$ (MW)")
    cyg_u = next(r for r in u1012 if r["star"] == "16CYGB")
    ax.set_title(f"B. 16 Cyg B Penta-Regime Closure (Best Opt P_10m={float(cyg_u['min_optical_10m_kw']):.3f} kW)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92, fontsize=8.0)

    _save(fig, "fig153_d110_p1_p5_cascade_and_16cygb_pentaregime.png")


def make_fig154_polarized_limits(eirp: list[dict[str, str]], paired_qu: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Panel A: Polarized C12 P_10m vs Wavelength across 3 instruments
    ax = axes[0]
    for inst, lbl, col, mk in [
        ("CFHT_ESPADONS_POL", "CFHT ESPaDOnS Opt", "#1d4ed8", "o"),
        ("TBL_NARVAL", "TBL NARVAL Opt", "#059669", "^"),
        ("CFHT_SPIROU_POL", "CFHT SPIRou NIR", "#dc2626", "s"),
    ]:
        sub = [r for r in eirp if r["instrument"] == inst]
        # deterministic jitter by index
        xs = [float(r["wave_bary_a"]) / 1e4 * (1.0 + 0.012 * ((i % 7) - 3) / 3.0) for i, r in enumerate(sub)]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax.scatter(xs, ys, s=22, c=col, marker=mk, alpha=0.68, label=f"{lbl} ({len(sub)} bands)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Rest/Vacuum Wavelength (um)")
    ax.set_ylabel(r"Polarized Laser 7-Sigma $P_{10\mathrm{m}}$ Limit (kW)")
    ax.set_title("A. Exact C12 Planck-Anchored Polarized Radiometry (0.41-2.30 um)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.92)

    # Panel B: Paired (Q, U) MDP99 (%) & Linear EIRP across 16 Sets
    ax = axes[1]
    pq_s = sorted(paired_qu, key=lambda x: float(x["mdp99_lin_pct"]))
    y = np.arange(len(pq_s))
    vals = [float(r["mdp99_lin_pct"]) for r in pq_s]
    cols = ["#dc2626" if r["regime"] == "NIR" else ("#059669" if r["instrument"] == "TBL_NARVAL" else "#2563eb") for r in pq_s]
    bars = ax.barh(y, vals, color=cols, height=0.68, alpha=0.88)
    for b, r in zip(bars, pq_s):
        ax.text(float(r["mdp99_lin_pct"]) + 0.04, b.get_y() + b.get_height() / 2, f"{float(r['mdp99_lin_pct']):.3f}%", va="center", fontsize=7.5)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['star']} ({r['instrument'].split('_')[1][:4]})" for r in pq_s], fontsize=7.8)
    ax.set_xlim(0, max(vals) * 1.25)
    ax.set_xlabel("Paired (Q, U) Linear Polarization 99% MDP99 (%)")
    ax.set_title(f"B. Paired (Q, U) Linear Polarization Sensitivities ({len(pq_s)} Pairs, Med={np.median(vals):.3f}%)")

    _save(fig, "fig154_d110_polarized_eirp_and_qu_mdp99_limits.png")


def make_fig155_calibrations(summary: dict[str, Any]) -> None:
    suites = summary["synthetic_calibration_7911_trials"]["suites"]
    names = list(suites.keys())
    rates = [100.0 * suites[k]["passed"] / suites[k]["total"] for k in names]
    labs = [k.replace("CALIBRATION_", "").replace("_", " ") for k in names]
    cols = ["#dc2626" if "V68_" in k else "#2563eb" for k in names]

    fig, ax = plt.subplots(figsize=(11.6, 10.2), constrained_layout=True)
    y = np.arange(len(names))[::-1]
    ax.barh(y, rates, color=cols, height=0.72, alpha=0.88)
    ax.axvline(97.5, color="#0f172a", ls="--", lw=1.4, label="97.5% Gate Floor")
    for yi, k, rt in zip(y, names, rates):
        ax.text(min(100.2, rt + 0.25), yi, f"{suites[k]['passed']}/{suites[k]['total']} ({rt:.1f}%)", va="center", fontsize=7.2)
    ax.set_xlim(93.0, 103.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labs, fontsize=7.4)
    ax.set_xlabel("Injection-Recovery & Veto Pass Rate (%)")
    cal_b = summary["synthetic_calibration_7911_trials"]
    cum_t = summary["unified_1012star_panchromatic_v6_8_synthesis"]["total_calibration_trials_d079_d110"]
    ax.set_title(f"Phase D110 (V6.8): All 37 Calibration Suites ({cal_b['total_passed']}/{cal_b['total_trials']} Trials; {cum_t:,} Cumulative)")
    ax.legend(loc="lower left", frameon=True, framealpha=0.92)
    _save(fig, "fig155_d110_v68_calibration_37suites_96345trials.png")


def make_fig156_unified_ftx(sep: list[dict[str, str]], ftx: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), constrained_layout=True)

    # Panel A: 1,012-Star Scale Separation
    ax = axes[0]
    bm = [r for r in sep if r["has_beamed"] == "True"]
    ax.scatter([float(r["dist_pc"]) for r in bm], [float(r["min_beamed_uv_opt_ir_mm_10m_kw"]) for r in bm], s=14, c="#2563eb", alpha=0.58, label=f"Beamed UV-mm (n={len(bm)}, 0 HE/nu)")
    he = [r for r in sep if r["has_he_em"] == "True"]
    nu = [r for r in sep if r["has_neutrino"] == "True"]
    ax.scatter([float(r["dist_pc"]) for r in he], [float(r["min_he_l_iso_mw"]) for r in he], s=16, c="#ea580c", marker="^", alpha=0.62, label=f"HE X/gamma L_iso (n={len(he)})")
    ax.scatter([float(r["dist_pc"]) for r in nu], [float(r["min_icecube_l_nu_iso_mw"]) for r in nu], s=26, c="#16a34a", marker="D", alpha=0.78, label=f"IceCube nu_mu L_iso (n={len(nu)})")
    ax.axvline(10.0, color="#0f172a", ls=":", lw=1.1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Distance (pc)")
    ax.set_ylabel(r"Beamed $P_{10\mathrm{m}}$ (kW)  /  Isotropic $L_{\mathrm{iso}}$ (MW)")
    ax.set_title("A. Unified 1,012-Star Physical Scale Separation (D079-D110)")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=7.6)

    # Panel B: Bayesian f95 vs P10m including OPT_NIR_POLARIMETRY_V68
    ax = axes[1]
    n_tot = {r["cohort"]: int(r["n_cohort_total"]) for r in ftx}
    cohorts = [
        ("ALL_SCIENCE_EM", f"All Sci EM (n={n_tot['ALL_SCIENCE_EM']})", "#1d4ed8", "-o"),
        ("EXOPLANET_HOSTS_300", f"Exoplanet Hosts (n={n_tot['EXOPLANET_HOSTS_300']})", "#059669", "-s"),
        ("SOLAR_10PC_SCIENCE", f"<10 pc Sci EM (n={n_tot['SOLAR_10PC_SCIENCE']})", "#d97706", "-^"),
        ("SOLAR_10PC_HOSTS_61", f"<10 pc Hosts (n={n_tot['SOLAR_10PC_HOSTS_61']})", "#7c3aed", "-D"),
        ("OPT_NIR_POLARIMETRY_V68", f"Opt/NIR Polarimetry V6.8 (n={n_tot['OPT_NIR_POLARIMETRY_V68']})", "#dc2626", "-*"),
    ]
    p_vals = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 50.0, 100.0, 1000.0]
    for cid, lbl, col, fmt in cohorts:
        ys = [float(next(x["f95_uniform_pct"] for x in ftx if x["cohort"] == cid and x["power_threshold"] == f"{pv:g}" and float(x["duty_cycle_eta"]) == 1.0)) for pv in p_vals]
        ax.plot(p_vals, ys, fmt, color=col, lw=1.8, ms=5.5, label=lbl)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.3, 120)
    ax.set_xlabel(r"Beamed Laser Threshold $P_{10\mathrm{m}}$ (kW)")
    ax.set_ylabel(r"Bayesian 95% Upper Limit $f_{\mathrm{tx}}$ (%) [Uniform]")
    ax.set_title("B. Bayesian f_tx Occurrence Limits (Uniform, eta_duty=1.0)")
    ax.legend(loc="lower left", frameon=True, framealpha=0.92, fontsize=7.6)

    _save(fig, "fig156_d110_unified_panchromatic_bayesian_ftx_polarimetry.png")


def main() -> int:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    cohort = _read_csv(WS / "FROZEN_COHORT_D110.csv")
    spec = _read_csv(RES / "POLARIMETRIC_SPECTRA_SUMMARY_D110.csv")
    cands = _read_csv(RES / "POLARIMETRIC_CANDIDATE_LEDGER_D110.csv")
    eirp = _read_csv(RES / "POLARIZED_EIRP_UPPER_LIMITS_D110.csv")
    paired_qu = _read_csv(RES / "PAIRED_QU_LINEAR_POLARIZATION_D110.csv")
    u1012 = _read_csv(RES / "UNIFIED_PANCHROMATIC_V6_8_SYNTHESIS_1012STARS.csv")
    sep = _read_csv(RES / "PHYSICAL_SCALE_SEPARATION_1012STARS_D110.csv")
    ftx = _read_csv(RES / "BAYESIAN_FTX_OCCURRENCE_LIMITS_D110.csv")
    br_fname = summary["unified_1012star_panchromatic_v6_8_synthesis"]["panchromatic_bridge_filename"]

    make_fig151_cohort_coverage(spec, cohort, summary)
    make_fig152_stokes_diagnostics(spec, cands)
    make_fig153_cascade_pentaregime(summary, RES / br_fname, u1012)
    make_fig154_polarized_limits(eirp, paired_qu)
    make_fig155_calibrations(summary)
    make_fig156_unified_ftx(sep, ftx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
