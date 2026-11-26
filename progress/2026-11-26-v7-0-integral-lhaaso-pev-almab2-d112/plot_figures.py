#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""Generate the 6 V7.0 / Phase D112 publication-grade 300-DPI figures (fig163-fig168)."""
from __future__ import annotations

import base64
import csv
import gzip
import json
import lzma
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

WS = Path(__file__).resolve().parent
RES = WS / "results"
BUN = WS / "bounded_inputs/d112_bounded_bundle.json.gz"

plt.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.0,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})


def _unpack_f64l(s: str) -> np.ndarray:
    raw = lzma.decompress(base64.b85decode(s.split(":", 1)[1].encode("ascii")))
    return np.frombuffer(raw, dtype="<f8").copy()


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    bundle = json.loads(gzip.decompress(BUN.read_bytes()).decode("utf-8"))
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    obs_by_dp = {o["dp_id"]: o for o in bundle["observations"]}

    # -----------------------------------------------------------------------
    # fig163: INTEGRAL 511 keV & Hard X-ray/Soft-Gamma Sensitivity & Gates
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    fig.suptitle(
        "D112 (V7.0) INTEGRAL 511 keV, IBIS/ISGRI, JEM-X & SPI Survey (62 Real Spectra, Verified ETI = 0)",
        fontsize=11.5, fontweight="bold",
    )

    ax = axes[0]
    int_sum = _read_csv("INTEGRAL_SPECTRA_SUMMARY_D112.csv")
    int_511 = _read_csv("INTEGRAL_511KEV_UPPER_LIMITS_D112.csv")
    inst_colors = {
        "INTEGRAL_IBIS_ISGRI": ("#1f77b4", "o", "IBIS/ISGRI (13-971 keV, n=35)"),
        "INTEGRAL_JEMX": ("#2ca02c", "^", "JEM-X2 (3-35 keV, n=16)"),
        "INTEGRAL_SPI": ("#d62728", "s", "SPI Ge (20-540 keV, n=11)"),
    }
    for inst_k, (col, mk, lbl) in inst_colors.items():
        sub = [r for r in int_sum if r["instrument"] == inst_k]
        xs = [float(r["dist_pc"]) for r in sub]
        ys = [float(r["flux_lim_erg_cm2_s"]) for r in sub]
        ax.scatter(xs, ys, c=col, marker=mk, s=42, alpha=0.82, edgecolors="k", linewidths=0.4, label=lbl, zorder=3)
    # Highlight 511 keV e+/e- UL cohort on ISGRI/SPI
    c511 = [r for r in int_511 if r["covers_511kev"] == "True"]
    ax.scatter(
        [float(r["dist_pc"]) for r in c511],
        [float(r["flux_lim_511kev_erg_cm2_s"]) for r in c511],
        facecolors="none", edgecolors="#ff7f0e", s=85, linewidths=1.1,
        label=f"511 keV e+/e- UL (n={len(c511)})", zorder=2,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Target Luminosity Distance [pc]")
    ax.set_ylabel(r"6$\sigma$ Narrowband Flux Limit [erg cm$^{-2}$ s$^{-1}$]")
    ax.set_title("A. Narrowband & 511 keV Annihilation Line Sensitivity")
    ax.legend(loc="lower right", framealpha=0.92)

    ax = axes[1]
    # Gate funnel + Stage-2 veto summary
    gates = [
        ("I1 Raw\n(|z|>=6)", sum(int(r["i1_raw_peaks"]) for r in int_sum)),
        ("I2 Qual/ARF", sum(int(r["i2_qual_arf_pass"]) for r in int_sum)),
        ("I3 Atlas\n(511/FeK/Act)", sum(int(r["i3_atlas_pass"]) for r in int_sum)),
        ("I4 Cont/Wing", sum(int(r["i4_continuum_ghost_pass"]) for r in int_sum)),
        ("I5 Pre-S2", sum(int(r["i5_qualified_count"]) for r in int_sum)),
        ("Verified\nETI", 0),
    ]
    gx = np.arange(len(gates))
    gvals = [v for _, v in gates]
    gcols = ["#4c72b0", "#4c72b0", "#dd8452", "#dd8452", "#c44e52", "#2ca02c"]
    bars = ax.bar(gx, gvals, color=gcols, edgecolor="black", linewidth=0.6, width=0.62)
    for b, v in zip(bars, gvals):
        ax.text(b.get_x() + b.get_width() / 2.0, v + 0.6, str(v), ha="center", va="bottom", fontweight="bold", fontsize=9)
    ax.set_xticks(gx)
    ax.set_xticklabels([g for g, _ in gates])
    ax.set_ylim(0, max(gvals) * 1.22 + 2)
    ax.set_ylabel("Spectral Bin Candidates Across 62 Spectra")
    ax.set_title("B. INTEGRAL I1-I5 Vetting Funnel (Stage-2 Compton/Mask -> 0 ETI)")
    ax.annotate(
        "6 pre-Stage-2 residuals on\nCas A, Circinus, Mrk 501, NGC 3227,\nV1223 Sgr, X Per -> broadband Compton\nreflection / mask coded tail (ETI = 0)",
        xy=(4, 6), xytext=(2.4, max(gvals) * 0.72),
        arrowprops=dict(arrowstyle="->", color="#444", lw=1.0),
        fontsize=8.2, bbox=dict(boxstyle="round,pad=0.35", fc="#fff8e8", ec="#cc9933", lw=0.8),
    )
    fig.savefig(RES / "fig163_d112_integral_511kev_and_hard_xray_limits.png", bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # fig164: 1LHAASO PeV Frontier & Multi-Messenger UHE SEDs (up to 1.000 PeV)
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    fig.suptitle(
        r"D112 (V7.0) 1LHAASO PeV Multi-Messenger Survey: 1–1,000 TeV (1.000 PeV, $\lambda_{\min}=1.24\times10^{-15}\,\mu$m)",
        fontsize=11.5, fontweight="bold",
    )

    ax = axes[0]
    bench_dps = [
        ("1LHAASO_J0534+2200_WCDA", "Crab J0534+2200 (WCDA)", "#1f77b4", "--"),
        ("1LHAASO_J0534+2200_KM2A", "Crab J0534+2200 (KM2A -> 1 PeV)", "#1f77b4", "-"),
        ("1LHAASO_J2108+5153_WCDA", "J2108+5153u (WCDA)", "#d62728", "--"),
        ("1LHAASO_J2108+5153_KM2A", "J2108+5153u (KM2A+Zenodo)", "#d62728", "-"),
        ("1LHAASO_J1908+0615_KM2A", "MGRO J1908+06 (KM2A)", "#2ca02c", "-"),
        ("1LHAASO_J1104+3810_WCDA", "Mrk 421 Blazar (WCDA)", "#9467bd", "--"),
    ]
    for dp, lbl, col, ls in bench_dps:
        if dp not in obs_by_dp:
            continue
        lp = obs_by_dp[dp]["lhaaso_pack"]
        etev = _unpack_f64l(lp["e_tev_b85"])
        eflux = _unpack_f64l(lp["e2_flux_b85"])
        eerr = _unpack_f64l(lp["e2_err_b85"])
        is_ul = np.asarray(lp["is_ul_list"], dtype=bool)
        det_m = ~is_ul
        if np.any(det_m):
            ax.errorbar(etev[det_m], eflux[det_m], yerr=eerr[det_m], fmt="o" if ls == "-" else "^", linestyle=ls, color=col, markersize=4.2, linewidth=1.3, label=lbl, capsize=2.0)
        if np.any(is_ul):
            ax.plot(etev[is_ul], eflux[is_ul], "v", color=col, markersize=5.0, alpha=0.8)
    ax.axvline(25.0, color="gray", linestyle=":", linewidth=1.2)
    ax.text(26.5, 2e-10, "25 TeV\nWCDA/KM2A\nstitch veto", fontsize=7.8, color="#444")
    ax.axvline(1000.0, color="#b22222", linestyle="-.", linewidth=1.2)
    ax.text(920.0, 2.5e-14, "1.000 PeV\nFrontier", ha="right", fontsize=8.0, color="#b22222", fontweight="bold")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.8, 1300.0)
    ax.set_ylim(1e-14, 1e-9)
    ax.set_xlabel("Photon Energy E [TeV]")
    ax.set_ylabel(r"$E^2 \, dN/dE$ [erg cm$^{-2}$ s$^{-1}$]")
    ax.set_title("A. Representative 1LHAASO WCDA + KM2A PeV SEDs (29 Sources)")
    ax.legend(loc="lower left", fontsize=7.5, framealpha=0.92)

    ax = axes[1]
    lh_sum = _read_csv("LHAASO_PEV_SUMMARY_D112.csv")
    km2a_rows = [r for r in lh_sum if r["instrument"] == "LHAASO_KM2A"]
    wcda_rows = [r for r in lh_sum if r["instrument"] == "LHAASO_WCDA"]
    ax.scatter([float(r["r39_deg"]) for r in wcda_rows], [float(r["l_iso_mw"]) for r in wcda_rows], c="#1f77b4", marker="^", s=45, alpha=0.85, edgecolors="k", lw=0.4, label="LHAASO_WCDA (1-25 TeV, n=29)")
    ax.scatter([float(r["r39_deg"]) for r in km2a_rows], [float(r["l_iso_mw"]) for r in km2a_rows], c="#d62728", marker="o", s=45, alpha=0.85, edgecolors="k", lw=0.4, label="LHAASO_KM2A (25-1,000 TeV, n=29)")
    ax.axvline(0.35, color="#cc6600", linestyle="--", linewidth=1.3, label="L3 Extended Halo Veto (r39 > 0.35 deg)")
    ax.axvspan(0.35, max(float(r["r39_deg"]) for r in lh_sum) + 0.1, color="#ffe8cc", alpha=0.35)
    ax.set_yscale("log")
    ax.set_xlabel("39% Containment Angular Radius r39 [deg]")
    ax.set_ylabel(r"6$\sigma$ Narrowband $L_{\mathrm{iso}}$ Upper Limit [MW]")
    ax.set_title("B. Extended PeVatron Halo Veto (L3) & UHE Luminosity Bounds")
    ax.legend(loc="upper right", fontsize=7.8, framealpha=0.92)
    fig.savefig(RES / "fig164_d112_lhaaso_1pev_frontier_and_sed.png", bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # fig165: ALMA Band 2 SV Arp 220 Closure & 10/10 ALMA Band Matrix
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 7.6), constrained_layout=True)
    fig.suptitle(
        "D112 (V7.0) ALMA Band 2 Science Verification (Arp 220, 2011.0.00026.SV) & 10/10 ALMA Receiver Band Closure",
        fontsize=11.5, fontweight="bold",
    )
    b2_cubes = []
    for dp in ("ALMA_B2_SV_ARP220_X36", "ALMA_B2_SV_ARP220_X52"):
        for cp in obs_by_dp[dp]["alma_cubes"]:
            b2_cubes.append(cp)
    b2_cubes.sort(key=lambda c: float(_unpack_f64l(c["freq_ghz_b85"])[0]))
    titles_spw = [
        "A. X36 SPW51 (86.45-88.32 GHz, HCN/HCO+ B2 Core)",
        "B. X36 SPW111 (106.96-108.83 GHz, HC3N/CS ULIRG)",
        "C. X52 SPW29 (112.25-114.12 GHz, CN/13CO Edge)",
    ]
    for idx, (ax, cp, tit) in enumerate(zip([axes[0, 0], axes[0, 1], axes[1, 0]], b2_cubes, titles_spw)):
        fq = _unpack_f64l(cp["freq_ghz_b85"])
        son = _unpack_f64l(cp["s_on_jy_b85"]) * 1e3  # mJy/beam
        soff = _unpack_f64l(cp["s_off_jy_b85"]) * 1e3
        ax.plot(fq, son, color="#1f77b4", lw=1.1, label="On-nucleus beam (mJy/bm)")
        ax.plot(fq, soff, color="#ff7f0e", lw=0.9, alpha=0.85, label="Off-nucleus annulus (mJy/bm)")
        ax.axhline(7.0 * cp["noise_jy"] * 1e3, color="#d62728", ls=":", lw=1.0, label=f"7σ narrow thresh ({7.0*cp['noise_jy']*1e3:.1f} mJy)")
        ax.set_title(tit)
        ax.set_xlabel("Observed Frequency [GHz]")
        ax.set_ylabel("Mean Flux Density [mJy/beam]")
        ax.legend(loc="upper right", fontsize=7.5, framealpha=0.9)

    ax = axes[1, 1]
    alma_bands = [
        ("B1", 35, 50, "D101", "#4c72b0"),
        ("B2 (SV)", 67, 116, "D112 NEW", "#d62728"),
        ("B3", 84, 116, "D101", "#4c72b0"),
        ("B4", 125, 163, "D101", "#4c72b0"),
        ("B5", 163, 211, "D101", "#4c72b0"),
        ("B6", 211, 275, "D102", "#4c72b0"),
        ("B7", 275, 373, "D102", "#4c72b0"),
        ("B8", 385, 500, "D102", "#4c72b0"),
        ("B9", 602, 720, "D103", "#4c72b0"),
        ("B10", 787, 950, "D103", "#4c72b0"),
    ]
    y_pos = np.arange(len(alma_bands))
    for yi, (bn, flo, fhi, ph, col) in enumerate(alma_bands):
        ax.barh(yi, fhi - flo, left=flo, height=0.62, color=col, edgecolor="k", lw=0.6, alpha=0.88)
        ax.text(fhi + 12, yi, f"{bn}: {flo}-{fhi} GHz ({ph})", va="center", fontsize=7.8, fontweight="bold" if "NEW" in ph else "normal", color=col if "NEW" in ph else "#222")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([b[0] for b in alma_bands])
    ax.set_xlim(0, 1280)
    ax.set_xlabel("Frequency Coverage [GHz]")
    ax.set_title("D. 10/10 ALMA Receiver Band Completion Architecture (B1-B10)")
    fig.savefig(RES / "fig165_d112_alma_band2_sv_arp220_closure.png", bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # fig166: 62.582-Octave Continuous EM & Multi-Messenger Span (D079-D112)
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(13.2, 5.8), constrained_layout=True)
    bands_em = [
        ("LHAASO_KM2A (D112 NEW)", 1.239842e-15, 4.95937e-14, "#b22222", "HE_ISOTROPIC"),
        ("LHAASO_WCDA (D112 NEW)", 4.95937e-14, 1.23984e-12, "#d62728", "HE_ISOTROPIC"),
        ("HAWC / HESS / MAGIC / VERITAS", 4.1328e-15, 6.20e-11, "#e377c2", "HE_ISOTROPIC"),
        ("Fermi-LAT / CGRO COMPTEL / OSSE", 1.24e-12, 2.48e-8, "#8c564b", "HE_ISOTROPIC"),
        ("INTEGRAL SPI+ISGRI+JEMX (D112 NEW)", 1.277e-9, 4.133e-4, "#ff7f0e", "HE_ISOTROPIC"),
        ("NuSTAR / RXTE / Suzaku / XRISM / Swift", 6.2e-9, 4.1e-3, "#bcbd22", "HE_ISOTROPIC"),
        ("Chandra / XMM / eROSITA / IXPE / EUVE", 1.2e-4, 0.06998, "#17becf", "HE_ISOTROPIC"),
        ("FUSE / HST STIS / IUE (Lyman-UV)", 0.0912, 0.320, "#1f77b4", "BEAMED"),
        ("ESPRESSO / HARPS / FEROS / UVES / GHOST (Opt)", 0.305, 1.05, "#2ca02c", "BEAMED"),
        ("NIRPS / CARMENES / APOGEE / SPIRou / CRIRES+", 0.96, 2.50, "#1b9e77", "BEAMED"),
        ("JWST NIRSpec G395H/M + MIRI + Spitzer + ISO + SOFIA", 2.87, 325.0, "#7570b3", "BEAMED"),
        ("Herschel PACS/SPIRE/HIFI + JCMT (FIR-Submm)", 55.0, 3530.0, "#66a61e", "BEAMED"),
        ("ALMA B1-B10 incl. B2 SV (D112: 10/10 Bands)", 315.5, 8556.418, "#e7298a", "BEAMED"),
    ]
    yp = np.arange(len(bands_em))[::-1]
    for y, (lbl, wlo, whi, col, reg) in zip(yp, bands_em):
        ax.barh(y, np.log10(whi) - np.log10(wlo), left=np.log10(wlo), height=0.64, color=col, edgecolor="k", lw=0.6, alpha=0.88)
        ax.text(np.log10(whi) + 0.25, y, lbl, va="center", fontsize=8.1, fontweight="bold" if "D112 NEW" in lbl else "normal")
    ax.axvline(np.log10(1.239842e-15), color="#b22222", ls="--", lw=1.1)
    ax.axvline(np.log10(8556.41831), color="#e7298a", ls="--", lw=1.1)
    ax.set_yticks([])
    ax.set_xlim(-16.0, 12.2)
    ax.set_xlabel(r"$\log_{10}(\lambda / \mu\mathrm{m})$   [1.000 PeV LHAASO = $-14.907$  $\leftrightarrow$  35 GHz ALMA B1 = $+3.932$]")
    ax.set_title(
        "D112 (V7.0) 62.582-Octave EM Survey Architecture: 72 Spectrographs, 104 Arms, 1,083 Stars\n"
        "(45.682 Unbroken HE Octaves + 14.693 Lyman-to-mm Octaves + IceCube Multi-Messenger Neutrinos)",
        fontsize=11.0, fontweight="bold",
    )
    ax.text(-15.5, 0.35, "Unbroken HE:\n45.682 oct\n(1 PeV - 18 eV)", fontsize=8.2, bbox=dict(fc="#fff0f0", ec="#b22222", boxstyle="round,pad=0.3"))
    fig.savefig(RES / "fig166_d112_62p6_octave_panchromatic_continuity.png", bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # fig167: Physical Scale Separation (1,083 Stars) & Bayesian f_tx
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2), constrained_layout=True)
    fig.suptitle(
        "D112 (V7.0) Strict Physical Scale Separation (1,083 Stars) & Bayesian Occurrence Rate Limits",
        fontsize=11.5, fontweight="bold",
    )
    sep = _read_csv("PHYSICAL_SCALE_SEPARATION_1083STARS_D112.csv")
    ax = axes[0]
    b_d, b_p, h_d, h_p, n_d, n_p = [], [], [], [], [], []
    for r in sep:
        d = float(r["dist_pc"])
        if r["has_beamed"] == "True" and r["min_beamed_l_iso_mw"]:
            b_d.append(d); b_p.append(float(r["min_beamed_l_iso_mw"]))
        if r["has_he_em"] == "True" and r["min_he_l_iso_mw"]:
            h_d.append(d); h_p.append(float(r["min_he_l_iso_mw"]))
        if r["has_neutrino"] == "True" and r["min_icecube_l_nu_iso_mw"]:
            n_d.append(d); n_p.append(float(r["min_icecube_l_nu_iso_mw"]))
    ax.scatter(b_d, b_p, c="#1f77b4", s=16, alpha=0.65, label=f"Beamed Opt/IR/mm L_iso eq. (n={len(b_d)})")
    ax.scatter(h_d, h_p, c="#d62728", s=22, marker="^", alpha=0.72, label=f"HE Isotropic EM incl. INTEGRAL+LHAASO (n={len(h_d)})")
    ax.scatter(n_d, n_p, c="#2ca02c", s=26, marker="s", alpha=0.78, label=f"IceCube Neutrino 33 zero-EM preserved (n={len(n_d)})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Distance [pc]")
    ax.set_ylabel(r"Isotropic Luminosity Upper Limit $L_{\mathrm{iso}}$ [MW]")
    ax.set_title("A. Regime-Separated Sensitivity Across 10 Orders of Distance")
    ax.legend(loc="lower right", fontsize=7.6, framealpha=0.92)

    ax = axes[1]
    ftx = _read_csv("BAYESIAN_FTX_OCCURRENCE_LIMITS_D112.csv")
    b_rows = [r for r in ftx if r["cohort"] == "ALL_SCIENCE_EM" and r["power_threshold"] != "ANY_CALIBRATED"]
    for eta, col, ls in [("1.0", "#1f77b4", "-o"), ("0.5", "#ff7f0e", "--s"), ("0.1", "#2ca02c", "-.^"), ("0.01", "#d62728", ":d")]:
        sub = [r for r in b_rows if r["duty_cycle_eta"] == eta]
        xs = [float(r["power_threshold"]) for r in sub]
        ys = [float(r["f95_uniform_pct"]) for r in sub]
        ax.plot(xs, ys, ls, color=col, lw=1.6, markersize=5, label=f"All Sci EM (duty eta={eta})")
    ax.axhline(0.5048, color="#1f77b4", ls=":", lw=1.0, alpha=0.7, label="All Sci EM ANY_CAL f95=0.5048%")
    ax.axhline(0.8484, color="#8c564b", ls="--", lw=1.0, alpha=0.7, label="All HE Iso ANY_CAL f95=0.8484%")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.35, 260.0)
    ax.set_xlabel(r"10 m Collimated EIRP Threshold [kW]")
    ax.set_ylabel(r"95% Credible Upper Limit $f_{\mathrm{tx}}$ [%]")
    ax.set_title("B. Bayesian Occurrence Bounds vs Power & Duty Cycle")
    ax.legend(loc="upper right", fontsize=7.6, framealpha=0.94, ncol=1)
    fig.savefig(RES / "fig167_d112_physical_scale_separation_and_ftx_1083stars.png", bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # fig168: All 43 Calibration Suites (113,967 cum.) & CWTFM Haystack Benchmark
    # -----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4), constrained_layout=True)
    fig.suptitle(
        "D112 (V7.0) 43/43 Synthetic Calibration Suites (9,072/9,111 = 99.57%, 113,967 Cumulative) & CWTFM Benchmark",
        fontsize=11.3, fontweight="bold",
    )
    ax = axes[0]
    cal = summary["synthetic_calibration_9111_trials"]["suites"]
    # Plot V7.0 3 suites + aggregate across D102-D112 eras cleanly
    snames = list(cal.keys())
    srates = [100.0 * cal[k]["passed"] / cal[k]["total"] for k in snames]
    s_cols = ["#d62728" if k.startswith("CALIBRATION_V70") else ("#ff7f0e" if k.startswith("CALIBRATION_V69") else "#4c72b0") for k in snames]
    ax.scatter(np.arange(len(snames)), srates, c=s_cols, s=36, edgecolor="k", lw=0.4, zorder=3)
    ax.axhline(97.5, color="#b22222", ls="--", lw=1.2, label="Strict 97.5% Gate Threshold")
    ax.set_ylim(96.5, 100.4)
    ax.set_xlabel("Calibration Suite Index (1-3: New V7.0; 4-43: Legacy D081-D111)")
    ax.set_ylabel("Pass Rate [%]")
    ax.set_title(f"A. All 43/43 Calibration Suites Pass >=97.5% (Cum: {summary['unified_panchromatic_v7_0_synthesis']['total_calibration_trials_d079_d112']:,})")
    p_v70 = mpatches.Patch(color="#d62728", label="D112 V7.0 (INTEGRAL 240/240, LHAASO 240/240, ALMA B2 119/120)")
    p_leg = mpatches.Patch(color="#4c72b0", label="D081-D111 Regressions (40 Suites)")
    ax.legend(handles=[p_v70, p_leg], loc="lower left", fontsize=7.6, framealpha=0.92)

    ax = axes[1]
    cw = _read_csv("CWTFM_COSMIC_HAYSTACK_BENCHMARK_D112.csv")
    c_lbls = [r["survey_or_cohort"].replace("_V70", "").replace("LIT_", "") for r in cw]
    c_oct = [float(r["spectral_octaves"]) for r in cw]
    c_n = [max(1, int(r["n_stars"])) for r in cw]
    c_cols = ["#d62728" if r["is_this_work"] == "True" else "#7f7f7f" for r in cw]
    ax.scatter(c_oct, c_n, c=c_cols, s=90, edgecolor="k", lw=0.6, zorder=3)
    offsets = [(-6, 12, "right"), (-6, -15, "right"), (8, 5, "left"), (0, 11, "center"), (0, -15, "center"), (8, -10, "left"), (8, 6, "left")]
    for (x, y, lb, (dx, dy, ha)) in zip(c_oct, c_n, c_lbls, offsets):
        ax.annotate(lb, xy=(x, y), xytext=(dx, dy), textcoords="offset points", fontsize=7.4, ha=ha)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.22, 160.0)
    ax.set_ylim(0.65, 16000.0)
    ax.set_xlabel("Continuous/Bracketed Spectral Octave Span")
    ax.set_ylabel("Target Sample Size [Stars / Sources]")
    ax.set_title("B. Survey Sample Size vs Octave Span (62.582-Octave D112 Leap)")
    fig.savefig(RES / "fig168_d112_43suites_calibration_and_haystack.png", bbox_inches="tight")
    plt.close(fig)
    print("Generated all 6 D112 figures (fig163-fig168) cleanly.")


if __name__ == "__main__":
    main()
