#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D111 (V6.9) Publication Figure Generator (`fig157–fig162`, 240-DPI PNGs):
  - fig157_d111_lm_midir_survey_sky_and_coverage.png
  - fig158_d111_qcl_lm_eirp_limits.png
  - fig159_d111_molecular_ccf_heatmap.png
  - fig160_d111_confounder_regression_spectra.png
  - fig161_d111_v69_calibration_40suites.png
  - fig162_d111_bayesian_ftx_and_cwtfm_v69.png
"""
from __future__ import annotations

import base64
import csv
import gzip
import json
import lzma
import math
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


def make_fig157_cohort_sky(cohort: list[dict[str, str]], spec: list[dict[str, str]], summary: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.4), constrained_layout=True)

    ax = axes[0]
    by_star: dict[str, dict[str, Any]] = {}
    for r in cohort:
        st = r["canonical_target"]
        d = by_star.setdefault(st, {
            "ra": float(r["s_ra"]), "dist": float(r["dist_pc"]),
            "new": r["is_prior_bridge"] != "True", "insts": set(),
        })
        d["insts"].add(r["instrument"])

    groups = [
        ("Single-Arm Prior Bridges", lambda v: not v["new"] and len(v["insts"]) == 1, "#1d4ed8", "o", 42),
        ("Multi-Arm IR Bridges (2-3 Arms)", lambda v: not v["new"] and len(v["insts"]) >= 2, "#7c3aed", "D", 66),
        ("Brand-New Exoplanet Hosts (27, sep >= 651\")", lambda v: v["new"], "#dc2626", "*", 130),
    ]
    for lbl, pred, col, mk, sz in groups:
        sub = [v for v in by_star.values() if pred(v)]
        if sub:
            ax.scatter([v["ra"] for v in sub], [v["dist"] for v in sub], s=sz, c=col, marker=mk, alpha=0.88, edgecolors="white", linewidths=0.5, label=lbl, zorder=4)

    for tag, dx, dy in [("WISE0855", 6, -4), ("ALPCENA", 5, 5), ("HD209100", -48, 8), ("EPSERI", 6, 4), ("16CYGB", 6, 6), ("HIP65426", 4, 11), ("HD206893", -42, -12)]:
        if tag in by_star:
            v = by_star[tag]
            ax.annotate(tag, (v["ra"], v["dist"]), xytext=(dx, dy), textcoords="offset points", fontsize=7.3, fontweight="bold")
    ax.axvline(180.0, color="#94a3b8", ls=":", lw=1.0)
    ax.set_yscale("log")
    ax.set_xlim(-12, 372)
    ax.set_xlabel("Right Ascension (deg)")
    ax.set_ylabel("Distance (pc)")
    ax.set_title("A. Phase D111 Cohort: 73 Stars (46 Bridges + 27 New -> 1,039 Total)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.92, fontsize=7.8)

    ax = axes[1]
    insts = ["ESO_CRIRES_PLUS", "JWST_NIRSPEC_G395H", "JWST_NIRSPEC_G395M", "JWST_MIRI_MRS"]
    ilbls = ["ESO CRIRES+\nK (1.95-2.49 um)", "JWST NIRSpec\nG395H (2.87-5.27 um)", "JWST NIRSpec G395M\n(98th Spectral Arm)", "JWST MIRI/MRS\n(4.90-18.0 um)"]
    br_cnt = [sum(1 for r in spec if r["instrument"] == i and r["is_prior_bridge"] == "True") for i in insts]
    nw_cnt = [sum(1 for r in spec if r["instrument"] == i and r["is_prior_bridge"] != "True") for i in insts]
    x = np.arange(len(insts))
    w = 0.36
    b1 = ax.bar(x - w / 2, br_cnt, width=w, color="#0284c7", label="Prior Panchromatic Bridges")
    b2 = ax.bar(x + w / 2, nw_cnt, width=w, color="#dc2626", label="Brand-New Exoplanet Hosts")
    for bars in (b1, b2):
        for b in bars:
            h = int(b.get_height())
            if h > 0:
                ax.text(b.get_x() + b.get_width() / 2, h + 0.5, f"{h}", ha="center", va="bottom", fontsize=8.0, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(ilbls, fontsize=8.0)
    ax.set_ylim(0, max(br_cnt) + 7)
    ax.set_ylabel("Number of Valid Calibrated Spectra")
    ax.set_title(f"B. Spectral Arm Breakdown ({len(spec)} Spectra across 1.95-18.0 um)")
    ax.legend(loc="upper right", frameon=True, framealpha=0.92)
    _save(fig, "fig157_d111_lm_midir_survey_sky_and_coverage.png")


def make_fig158_qcl_eirp_limits(eirp: list[dict[str, str]], spec: list[dict[str, str]], summary: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.4), constrained_layout=True)

    ax = axes[0]
    styles = [
        ("ESO_CRIRES_PLUS", "ESO CRIRES+ K (R=43k-86k)", "#1d4ed8", "o"),
        ("JWST_NIRSPEC_G395H", "JWST NIRSpec G395H (R=2,700)", "#059669", "^"),
        ("JWST_NIRSPEC_G395M", "JWST NIRSpec G395M (98th Arm)", "#7c3aed", "D"),
        ("JWST_MIRI_MRS", "JWST MIRI/MRS (R~2,500)", "#ea580c", "s"),
    ]
    for inst, lbl, col, mk in styles:
        sub = [r for r in eirp if r["instrument"] == inst]
        xs = [float(r["wave_um"]) * (1.0 + 0.014 * ((i % 7) - 3) / 3.0) for i, r in enumerate(sub)]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax.scatter(xs, ys, s=28, c=col, marker=mk, alpha=0.75, label=f"{lbl} ({len(sub)} bands)")

    # Highlight record limits with zero x-tick overlap
    for inst_k, txt_lbl, dx, dy in [
        ("JWST_NIRSPEC_G395M", "WISE0855\n1.73 W @ 3.1 um", -44, 24),
        ("JWST_NIRSPEC_G395H", "SIMP0136\n5.36 W @ 3.5 um", 14, 18),
        ("ESO_CRIRES_PLUS", "WISE1049AB\n0.13 kW @ 2.15 um", 10, 14),
        ("JWST_MIRI_MRS", "WISE0855\n0.52 kW @ 10.6 um", -72, -12),
    ]:
        b = summary["best_10m_eirp_limits_kw"][inst_k]
        ax.scatter([b["wave_um"]], [b["p_beam_10m_kw"]], s=110, facecolors="none", edgecolors="#0f172a", linewidths=1.6, zorder=6)
        ax.annotate(txt_lbl, (b["wave_um"], b["p_beam_10m_kw"]), xytext=(dx, dy), textcoords="offset points", fontsize=7.3, fontweight="bold", arrowprops=dict(arrowstyle="->", lw=0.8, color="#334155"))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(7e-4, 2.0e6)
    ax.set_xticks([2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 12.0])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel(r"Canonical IR QCL Wavelength ($\mu$m)")
    ax.set_ylabel(r"7-Sigma Laser EIRP Upper Limit $P_{10\mathrm{m}}$ (kW)")
    ax.set_title("A. Exact C12 Radiometric QCL Laser Limits (1.95-11.8 um, err=0.0)")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=7.6)

    ax = axes[1]
    q = summary["qcl_and_molecular_ccf_search"]
    stages = ["Q1 z>=7\nRaw Peaks", "Q2 Edge &\nCR Veto", "Q3 IR Astro\nAtlas Veto", "Q4 Sky/OH\nVeto", "Q5 Morph &\nWidth Pre-S2", "Verified\nETI"]
    vals = [int(q["q1_raw_peaks"]), int(q["q2_edge_cr_pass"]), int(q["q3_atlas_pass"]), int(q["q4_sky_pass"]), int(q["q5_pass_pre_stage2"]), 0]
    x = np.arange(len(stages))
    cols = ["#475569", "#0284c7", "#0d9488", "#d97706", "#7c3aed", "#16a34a"]
    bars = ax.bar(x, [max(0.5, v) for v in vals], color=cols, width=0.62, alpha=0.90)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, max(0.5, v) * 1.15, f"{v:,}", ha="center", va="bottom", fontsize=8.4, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(0.3, max(vals) * 3.8)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=8.0)
    ax.set_ylabel("Narrowband IR Candidate Count (+0.5 floor for 0)")
    ax.set_title(f"B. QCL_LM_V69 Physics Cascade ({len(spec)} Spectra -> 0 Verified ETI)")
    _save(fig, "fig158_d111_qcl_lm_eirp_limits.png")


def make_fig159_mol_heatmap(mol_rows: list[dict[str, str]]) -> None:
    all_species = [
        "CH4_C2H6_3P32", "NO2_3P44", "PH3_4P30", "N2O_4P50", "CO_13CO_4P67", "OCS_PF3_4P85",
        "NO2_6P20", "CF4_7P80", "N2O_7P78", "CFC12_MULTI", "SF6_10P55", "NF3_11P02", "PF3_11P21", "CFC11_11P82",
    ]
    by_star_sp: dict[tuple[str, str], float] = {}
    cov_counts: dict[str, int] = defaultdict(int)
    sp_star_sets: dict[str, set[str]] = defaultdict(set)
    for r in mol_rows:
        try:
            dl = float(r["depth_lim_5sig_pct"])
        except Exception:
            continue
        if not math.isfinite(dl):
            continue
        st, sp = r["star"], r["species"]
        if (st, sp) not in by_star_sp or dl < by_star_sp[(st, sp)]:
            by_star_sp[(st, sp)] = dl
        cov_counts[st] += 1
        sp_star_sets[sp].add(st)

    species_order = [sp for sp in all_species if len(sp_star_sets.get(sp, set())) >= 1]
    top_stars = sorted(cov_counts.keys(), key=lambda s: (-sum(1 for sp in species_order[6:] if (s, sp) in by_star_sp), -cov_counts[s], min(by_star_sp[(s, sp)] for sp in species_order if (s, sp) in by_star_sp), s))[:24]
    mat = np.full((len(top_stars), len(species_order)), np.nan, dtype=np.float64)
    for i, st in enumerate(top_stars):
        for j, sp in enumerate(species_order):
            if (st, sp) in by_star_sp:
                mat[i, j] = by_star_sp[(st, sp)]

    fig, ax = plt.subplots(figsize=(13.2, 7.6), constrained_layout=True)
    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad(color="#f1f5f9")
    im = ax.imshow(np.log10(np.clip(mat, 0.2, 100.0)), aspect="auto", cmap=cmap, vmin=np.log10(0.3), vmax=np.log10(60.0))
    for i in range(len(top_stars)):
        for j in range(len(species_order)):
            v = mat[i, j]
            if math.isfinite(v):
                txt_col = "white" if v < 5.0 else "#0f172a"
                ax.text(j, i, f"{v:.1f}" if v < 20 else f"{v:.0f}", ha="center", va="center", fontsize=6.6, color=txt_col, fontweight="bold")
    ax.set_xticks(np.arange(len(species_order)))
    ax.set_xticklabels([s.replace("_", "\n") for s in species_order], fontsize=7.2)
    ax.set_yticks(np.arange(len(top_stars)))
    ax.set_yticklabels(top_stars, fontsize=7.6)
    ax.grid(False)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label(r"$\log_{10}$(5-Sigma Molecular Band-Depth Upper Limit %)")
    ax.set_title("JWST NIRSpec & MIRI/MRS 5-Sigma Industrial Technosignature Sensitivity (24 Multi-Band Targets, 0 Verified ETI)")
    _save(fig, "fig159_d111_molecular_ccf_heatmap.png")


def make_fig160_confounder_spectra() -> None:
    bundle = json.loads(gzip.decompress((WS / "bounded_inputs/d111_bounded_bundle.json.gz").read_bytes()).decode("utf-8"))
    blobs = {st: lzma.decompress(base64.b85decode(v.split(":", 1)[1])) for st, v in bundle["star_blobs"].items()}

    def _get_spec(star: str, inst: str, subband_sub: str = "") -> tuple[np.ndarray, np.ndarray]:
        for ex in bundle["exposures"]:
            if ex["star"] == star and ex["instrument"] == inst and (not subband_sub or subband_sub in ex["miri_subband"]):
                bl = blobs[star]
                w = np.frombuffer(bl, "<f4", count=ex["refs"]["W"]["npts"], offset=ex["refs"]["W"]["offset"]).astype(np.float64)
                f = np.frombuffer(bl, "<f4", count=ex["refs"]["F"]["npts"], offset=ex["refs"]["F"]["offset"]).astype(np.float64)
                return w, f
        raise RuntimeError(f"Missing {star} {inst} {subband_sub}")

    fig, axes = plt.subplots(2, 2, figsize=(13.6, 8.2), constrained_layout=True)

    # Panel A: HIP65426 NIRSpec G395H around 4.30 um PH3 vs CO2/CO confounder
    w, f = _get_spec("HIP65426", "JWST_NIRSPEC_G395H")
    m = (w >= 3.90) & (w <= 5.05) & np.isfinite(f)
    ax = axes[0, 0]
    ax.plot(w[m], f[m], color="#1d4ed8", lw=0.85, label="HIP 65426 NIRSpec G395H")
    ax.axvspan(4.20, 4.38, color="#dc2626", alpha=0.14, label="PH3_4P30 / CO2 4.26 um Blend")
    ax.axvline(4.30, color="#dc2626", ls="--", lw=1.0)
    ax.axvline(4.67, color="#059669", ls=":", lw=1.2, label="CO v=1-0 (4.67 um)")
    ax.set_xlabel(r"Wavelength ($\mu$m)"); ax.set_ylabel("Flux Density (Jy)")
    ax.set_title("A. HIP 65426 (G395H): Pre-S2 PH3 Trigger -> Photospheric CO/CO2 Blend")
    ax.legend(loc="upper right", frameon=True, fontsize=7.5)

    # Panel B: REDRECT NIRSpec G395M around 4.50 um N2O vs PAH/CO emission
    w, f = _get_spec("REDRECT", "JWST_NIRSPEC_G395M")
    m = (w >= 3.10) & (w <= 5.05) & np.isfinite(f)
    ax = axes[0, 1]
    ax.plot(w[m], f[m], color="#7c3aed", lw=0.90, label="Red Rectangle (G395M, 98th Arm)")
    ax.axvspan(4.40, 4.60, color="#dc2626", alpha=0.14, label="N2O_4P50 Continuum Trough")
    ax.axvline(3.29, color="#d97706", ls="-.", lw=1.1, label="PAH 3.3 um & 4.67 um CO/UIR")
    ax.axvline(4.67, color="#d97706", ls="-.", lw=1.1)
    ax.set_xlabel(r"Wavelength ($\mu$m)"); ax.set_ylabel("Flux Density (Jy)")
    ax.set_title("B. Red Rectangle (G395M): PAH/CO Bandgap Continuum -> Vetoed (0 ETI)")
    ax.legend(loc="upper right", frameon=True, fontsize=7.5)

    # Panel C: GJ504 MIRI/MRS CH3-SHORT around 11.82 um CFC-11 vs MRS fringe/NH3
    w, f = _get_spec("GJ504", "JWST_MIRI_MRS", "CH3-SHORT")
    m = (w >= 11.55) & (w <= 13.45) & np.isfinite(f)
    ax = axes[1, 0]
    ax.plot(w[m], f[m], color="#059669", lw=0.95, label="GJ 504 MIRI/MRS CH3-SHORT")
    ax.axvspan(11.65, 12.10, color="#dc2626", alpha=0.14, label="Edge Fringe / NH3 Trough (11.82 um)")
    ax.axvline(12.28, color="#ea580c", ls=":", lw=1.1, label="H2 S(2) / Hu-alpha Atlas")
    ax.set_xlabel(r"Wavelength ($\mu$m)"); ax.set_ylabel("Flux Density (Jy)")
    ax.set_title("C. GJ 504 (MIRI CH3-SHORT): Fringe/Band-Edge Slope -> Vetoed (0 ETI)")
    ax.legend(loc="upper left", frameon=True, fontsize=7.5)

    # Panel D: ALPCENA MIRI/MRS CH1-SHORT periodic MRS detector fringing near 5.45-5.52 um
    w, f = _get_spec("ALPCENA", "JWST_MIRI_MRS", "CH1-SHORT")
    m = (w >= 5.40) & (w <= 5.56) & np.isfinite(f)
    ax = axes[1, 1]
    ax.plot(w[m], f[m], color="#ea580c", lw=1.1, marker=".", ms=3.5, label="Alf Cen A MIRI/MRS CH1-SHORT")
    for fw in (5.4628, 5.4716, 5.4804, 5.4884):
        ax.axvline(fw, color="#0f172a", ls="--", lw=0.8, alpha=0.65)
    ax.text(5.475, float(np.median(f[m])) * 1.015, "MRS ~0.0085 um Fringe Combs", fontsize=7.6, ha="center", fontweight="bold", bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85))
    ax.set_xlabel(r"Wavelength ($\mu$m)"); ax.set_ylabel("Flux Density (Jy)")
    ax.set_title("D. Alf Cen A (MIRI CH1-SHORT): Dichroic Fringe Comb Residuals")
    ax.legend(loc="lower right", frameon=True, fontsize=7.5)

    _save(fig, "fig160_d111_confounder_regression_spectra.png")


def make_fig161_calibrations(summary: dict[str, Any]) -> None:
    suites = summary["synthetic_calibration_8511_trials"]["suites"]
    names = list(suites.keys())
    rates = [100.0 * suites[k]["passed"] / suites[k]["total"] for k in names]
    labs = [k.replace("CALIBRATION_", "").replace("_", " ") for k in names]
    cols = ["#dc2626" if "V69_" in k else "#2563eb" for k in names]

    fig, ax = plt.subplots(figsize=(11.8, 10.8), constrained_layout=True)
    y = np.arange(len(names))[::-1]
    ax.barh(y, rates, color=cols, height=0.72, alpha=0.88)
    ax.axvline(97.5, color="#0f172a", ls="--", lw=1.4, label="97.5% Gate Floor")
    for yi, k, rt in zip(y, names, rates):
        ax.text(min(100.25, rt + 0.25), yi, f"{suites[k]['passed']}/{suites[k]['total']} ({rt:.1f}%)", va="center", fontsize=7.1)
    ax.set_xlim(93.0, 103.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labs, fontsize=7.2)
    ax.set_xlabel("Injection-Recovery & Veto Pass Rate (%)")
    cal_b = summary["synthetic_calibration_8511_trials"]
    cum_t = summary["unified_panchromatic_v6_9_synthesis"]["total_calibration_trials_d079_d111"]
    ax.set_title(f"Phase D111 (V6.9): All 40 Calibration Suites ({cal_b['total_passed']}/{cal_b['total_trials']} Trials; {cum_t:,} Cumulative)")
    ax.legend(loc="lower left", frameon=True, framealpha=0.92)
    _save(fig, "fig161_d111_v69_calibration_40suites.png")


def make_fig162_ftx_cwtfm(sep: list[dict[str, str]], ftx: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.4), constrained_layout=True)

    ax = axes[0]
    bm = [r for r in sep if r["has_beamed"] == "True"]
    he = [r for r in sep if r["has_he_em"] == "True"]
    nu = [r for r in sep if r["has_neutrino"] == "True"]
    ax.scatter([float(r["dist_pc"]) for r in bm], [float(r["min_beamed_uv_opt_ir_mm_10m_kw"]) for r in bm], s=14, c="#2563eb", alpha=0.58, label=f"Beamed UV-mm (n={len(bm)}, 0 HE/nu)")
    ax.scatter([float(r["dist_pc"]) for r in he], [float(r["min_he_l_iso_mw"]) for r in he], s=16, c="#ea580c", marker="^", alpha=0.62, label=f"HE X/gamma L_iso (n={len(he)})")
    ax.scatter([float(r["dist_pc"]) for r in nu], [float(r["min_icecube_l_nu_iso_mw"]) for r in nu], s=26, c="#16a34a", marker="D", alpha=0.78, label=f"IceCube nu_mu L_iso (n={len(nu)})")
    ax.axvline(10.0, color="#0f172a", ls=":", lw=1.1)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Distance (pc)")
    ax.set_ylabel(r"Beamed $P_{10\mathrm{m}}$ (kW)  /  Isotropic $L_{\mathrm{iso}}$ (MW)")
    ax.set_title("A. Unified 1,039-Star Physical Scale Separation (D079-D111)")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=7.6)

    ax = axes[1]
    n_tot = {r["cohort"]: int(r["n_cohort_total"]) for r in ftx}
    host_k = next(k for k in n_tot if k.startswith("EXOPLANET_HOSTS_"))
    host10_k = next(k for k in n_tot if k.startswith("SOLAR_10PC_HOSTS_"))
    cohorts = [
        ("ALL_SCIENCE_EM", f"All Sci EM (n={n_tot['ALL_SCIENCE_EM']})", "#1d4ed8", "-o"),
        (host_k, f"Exoplanet Hosts (n={n_tot[host_k]})", "#059669", "-s"),
        ("SOLAR_10PC_SCIENCE", f"<10 pc Sci EM (n={n_tot['SOLAR_10PC_SCIENCE']})", "#d97706", "-^"),
        (host10_k, f"<10 pc Hosts (n={n_tot[host10_k]})", "#7c3aed", "-D"),
        ("LM_MIDIR_QCL_V69", f"IR QCL K/L/M/N V6.9 (n={n_tot['LM_MIDIR_QCL_V69']})", "#dc2626", "-*"),
        ("JWST_MOL_CCF_V69", f"JWST Mol CCF V6.9 (n={n_tot['JWST_MOL_CCF_V69']})", "#0f766e", "-P"),
    ]
    p_vals = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 50.0, 100.0, 1000.0]
    for cid, lbl, col, fmt in cohorts:
        ys = [float(next(x["f95_uniform_pct"] for x in ftx if x["cohort"] == cid and x["power_threshold"] == f"{pv:g}" and float(x["duty_cycle_eta"]) == 1.0)) for pv in p_vals]
        ax.plot(p_vals, ys, fmt, color=col, lw=1.7, ms=5.0, label=lbl)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_ylim(0.3, 125)
    ax.set_xlabel(r"Beamed Laser Threshold $P_{10\mathrm{m}}$ (kW)")
    ax.set_ylabel(r"Bayesian 95% Upper Limit $f_{\mathrm{tx}}$ (%) [Uniform]")
    ax.set_title("B. Bayesian f_tx Occurrence Limits (Uniform, eta_duty=1.0)")
    ax.legend(loc="lower left", frameon=True, framealpha=0.92, fontsize=7.3)

    _save(fig, "fig162_d111_bayesian_ftx_and_cwtfm_v69.png")


def main() -> int:
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    cohort = _read_csv(WS / "FROZEN_COHORT_D111.csv")
    spec = _read_csv(RES / "QCL_SPECTRA_SUMMARY_D111.csv")
    eirp = _read_csv(RES / "QCL_IR_EIRP_UPPER_LIMITS_D111.csv")
    mol = _read_csv(RES / "MOLECULAR_SPECIES_LIMITS_D111.csv")
    sep = _read_csv(RES / "PHYSICAL_SCALE_SEPARATION_1039STARS_D111.csv")
    ftx = _read_csv(RES / "BAYESIAN_FTX_OCCURRENCE_LIMITS_D111.csv")

    make_fig157_cohort_sky(cohort, spec, summary)
    make_fig158_qcl_eirp_limits(eirp, spec, summary)
    make_fig159_mol_heatmap(mol)
    make_fig160_confounder_spectra()
    make_fig161_calibrations(summary)
    make_fig162_ftx_cwtfm(sep, ftx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
