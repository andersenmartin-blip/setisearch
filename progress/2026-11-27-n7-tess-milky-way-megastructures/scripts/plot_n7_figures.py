#!/usr/bin/env python3
"""Generate 6 publication-quality 300-DPI PNGs for Spor N7 (TESS Milky Way Megastructures)."""
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
from astropy.io import fits
from scipy.ndimage import median_filter

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n7_20261127_tess_milky_way_megastructures"
INP = ROOT / "inputs_n7_20261127"
RES = WS / "results"
FIG_WS = WS / "figures"
FIG_GIT = ROOT / "setisearch/progress/2026-11-27-n7-tess-milky-way-megastructures/figures"

plt.rcParams.update({
    "font.size": 9.4,
    "axes.titlesize": 10.6,
    "axes.labelsize": 9.8,
    "xtick.labelsize": 8.6,
    "ytick.labelsize": 8.6,
    "legend.fontsize": 8.0,
    "figure.titlesize": 12.2,
})


def save_both(fig: plt.Figure, name: str) -> None:
    FIG_WS.mkdir(parents=True, exist_ok=True)
    FIG_GIT.mkdir(parents=True, exist_ok=True)
    for d in (FIG_WS, FIG_GIT):
        fig.savefig(d / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {name}", flush=True)


def fig01_sky_and_distance(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    mw = [r for r in cat if float(r["dist_pc"]) <= 50000.0 and float(r["dist_pc"]) > 0 and r["star"] != "HD139139"]
    vet_mw_stars = {r["star"] for r in vet if r["vetting_class"] != "EXTRAGALACTIC_AGN_CONTROL"}

    fig = plt.figure(figsize=(12.8, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0])

    ax1 = fig.add_subplot(gs[0, 0], projection="mollweide")
    ra = np.array([((float(r["ra_j2000"]) + 180.0) % 360.0) - 180.0 for r in mw])
    dec = np.array([float(r["dec_j2000"]) for r in mw])
    dist = np.array([float(r["dist_pc"]) for r in mw])
    lon = -np.radians(ra)
    lat = np.radians(dec)

    sc = ax1.scatter(lon, lat, c=np.log10(np.clip(dist, 1.0, 2000.0)), cmap="viridis", s=20, alpha=0.82, edgecolors="#111", lw=0.2, label=f"Milky Way TESS Stars (n={len(mw)})")
    # Overlay triggers
    tr = [r for r in mw if r["star"] in vet_mw_stars]
    tra = -np.radians(np.array([((float(r["ra_j2000"]) + 180.0) % 360.0) - 180.0 for r in tr]))
    tdec = np.radians(np.array([float(r["dec_j2000"]) for r in tr]))
    ax1.scatter(tra, tdec, marker="*", s=78, c="#D55E00", edgecolors="#111", lw=0.5, zorder=5, label=f"Astrophysical Triggers Vetted to 0 ETI (n={len(tr)})")

    ax1.grid(True, alpha=0.35, ls=":")
    cbar = fig.colorbar(sc, ax=ax1, orientation="horizontal", pad=0.08, fraction=0.05)
    cbar.set_label(r"Heliocentric Distance $\log_{10}(d / \mathrm{pc})$ [1.3 pc – 755 pc]")
    ax1.set_title("All-Sky Milky Way TESS 2-Min Cohort (6 Extragalactic Controls Excluded)")
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, -0.34), ncol=1, framealpha=0.95)

    # Panel 2: Distance histogram by cohort
    ax2 = fig.add_subplot(gs[0, 1])
    bins = np.linspace(0.0, 3.0, 22)
    c10 = [math.log10(max(1.0, float(r["dist_pc"]))) for r in mw if r["within_10pc"] == "True"]
    chost = [math.log10(max(1.0, float(r["dist_pc"]))) for r in mw if int(r["n_exoplanets"] or 0) > 0 and r["within_10pc"] != "True"]
    cetz = [math.log10(max(1.0, float(r["dist_pc"]))) for r in mw if r["within_10pc"] != "True" and int(r["n_exoplanets"] or 0) == 0]
    ax2.hist([c10, chost, cetz], bins=bins, stacked=True,
             color=["#009E73", "#0072B2", "#E69F00"], edgecolor="#111", lw=0.5,
             label=[f"<10 pc Solar Neighborhood (n={len(c10)})", f"Exoplanet Hosts >10 pc (n={len(chost)})", f"ETZ / Ellipsoid / Bench >10 pc (n={len(cetz)})"])
    ax2.axvline(1.0, color="#B00020", ls="--", lw=1.2, label="10 pc Boundary")
    ax2.set_xlabel(r"Heliocentric Distance $\log_{10}(d / \mathrm{pc})$")
    ax2.set_ylabel("Milky Way Stars with SPOC 2-Min Data")
    ax2.set_title("Distance & Priority Cohort Breakdown (8.64M Cadences)")
    ax2.set_ylim(0, 148)
    ax2.grid(axis="y", alpha=0.25, ls=":")
    ax2.legend(loc="upper right", fontsize=7.9, framealpha=0.95)

    fig.suptitle("Spor N7: Milky Way NASA TESS 2-Minute Space Photometry Sample (558 Stars, 0 ETI)", fontweight="bold")
    save_both(fig, "figN7_01_milky_way_tess_sky_and_distance.png")


def fig02_megadips_and_asymmetry(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    vet_by_star = {r["star"]: r["vetting_class"] for r in vet}
    mw = [r for r in cat if float(r["dist_pc"]) <= 50000.0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    quiet = [r for r in mw if r["triggered"] == "False"]
    pl = [r for r in mw if vet_by_star.get(r["star"]) == "KNOWN_TRANSITING_EXOPLANET"]
    yso = [r for r in mw if vet_by_star.get(r["star"]) == "YSO_OR_PROTOPLANETARY_DISK_DIPPER"]
    other_a = [r for r in mw if r["trig_a"] == "True" and r["star"] not in {x["star"] for x in pl + yso}]

    def xy_a(rows):
        return [max(1e-4, float(r["dip_depth"])) * 100.0 for r in rows], [max(1.0, float(r["dip_snr"])) for r in rows]

    ax1.scatter(*xy_a(quiet), s=15, c="#999999", alpha=0.55, label=f"Quiet Stars (n={len(quiet)})")
    ax1.scatter(*xy_a(pl), s=48, c="#009E73", edgecolors="#111", lw=0.5, zorder=4, label=f"Known Transiting Exoplanets (n={len(pl)})")
    ax1.scatter(*xy_a(yso), s=60, marker="^", c="#D55E00", edgecolors="#111", lw=0.6, zorder=5, label=f"YSO / Protoplanetary Disks (n={len(yso)})")
    ax1.scatter(*xy_a(other_a), s=52, marker="s", c="#0072B2", edgecolors="#111", lw=0.5, zorder=4, label=f"Blends / Starspots / Binaries (n={len(other_a)})")

    ax1.axvline(0.5, color="#B00020", ls="--", lw=1.2, label="Gate A Depth >= 0.5% (5,000 ppm)")
    ax1.axhline(12.0, color="#B00020", ls=":", lw=1.2, label="Gate A SNR >= 12")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.015, 40.0)
    ax1.set_ylim(2.0, 900.0)
    ax1.set_xlabel("Boxcar Maximum Dip Depth (%)")
    ax1.set_ylabel("Boxcar Dip Signal-to-Noise Ratio (SNR)")
    ax1.set_title("Channel A: Deep / Megastructure Transit Plane (0 Unexplained)")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="upper left", fontsize=7.6, framealpha=0.95)

    # Panel 2: Dip asymmetry vs CROWDSAP
    trig_a_mw = [r for r in mw if r["trig_a"] == "True"]
    ax2.scatter([float(r["dip_asym"]) for r in quiet], [float(r["crowdsap"]) for r in quiet], s=14, c="#999999", alpha=0.45, label="Quiet Stars")
    ax2.scatter([float(r["dip_asym"]) for r in pl], [float(r["crowdsap"]) for r in pl], s=48, c="#009E73", edgecolors="#111", lw=0.5, label="Transiting Exoplanets (Symmetric)")
    ax2.scatter([float(r["dip_asym"]) for r in yso], [float(r["crowdsap"]) for r in yso], s=60, marker="^", c="#D55E00", edgecolors="#111", lw=0.6, label="YSO Disk Dippers (Asymmetric)")
    ax2.scatter([float(r["dip_asym"]) for r in other_a], [float(r["crowdsap"]) for r in other_a], s=48, marker="s", c="#0072B2", edgecolors="#111", lw=0.5, label="Blends / Starspots / Artifacts")
    for r in trig_a_mw:
        if r["star"] in ("SZ90", "GQLUP", "RYTAU"):
            ax2.annotate(r["star"], xy=(float(r["dip_asym"]), float(r["crowdsap"])), xytext=(5, -10), textcoords="offset points", fontsize=7.8)
        elif r["star"] == "HD145718":
            ax2.annotate(r["star"], xy=(float(r["dip_asym"]), float(r["crowdsap"])), xytext=(6, -16), textcoords="offset points", fontsize=7.8)

    ax2.axhline(0.85, color="#B00020", ls="--", lw=1.1, label="Aperture Contamination Flag (CROWDSAP < 0.85)")
    ax2.set_xlim(-0.03, 1.03)
    ax2.set_ylim(-0.02, 1.06)
    ax2.set_xlabel(r"Transit Asymmetry $|t_{\mathrm{egress}} - t_{\mathrm{ingress}}| / (t_{\mathrm{egress}} + t_{\mathrm{ingress}})$")
    ax2.set_ylabel("TESS Aperture Purity CROWDSAP")
    ax2.set_title("Asymmetry & Aperture Contamination Diagnostic")
    ax2.grid(True, alpha=0.25, ls=":")
    ax2.legend(loc="lower left", fontsize=7.7, framealpha=0.95)

    fig.suptitle("Channel A: Megastructure Occultation Search Across Milky Way Stars", fontweight="bold")
    save_both(fig, "figN7_02_megastructure_dip_and_asymmetry_plane.png")


def fig03_beacons_and_flashes(cat: list[dict[str, Any]], vet: list[dict[str, Any]]) -> None:
    vet_by_star = {r["star"]: r["vetting_class"] for r in vet}
    mw = [r for r in cat if float(r["dist_pc"]) <= 50000.0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    quiet_b = [r for r in mw if r["trig_b"] == "False" and float(r["beacon_freq_cpd"]) > 0]
    trig_b = [r for r in mw if r["trig_b"] == "True"]
    ips = [r for r in trig_b if vet_by_star.get(r["star"]) == "ACCRETING_WD_INTERMEDIATE_POLAR_SPIN"]
    puls = [r for r in trig_b if vet_by_star.get(r["star"]) in ("STELLAR_PULSATION_OR_AGB_RSG", "MAGNETIC_WHITE_DWARF_ROTATION")]
    rots = [r for r in trig_b if r not in ips and r not in puls]

    ax1.scatter([float(r["beacon_freq_cpd"]) for r in quiet_b], [float(r["fft_snr"]) for r in quiet_b], s=14, c="#999999", alpha=0.5, label=f"Below Gate B (n={len(quiet_b)})")
    ax1.scatter([float(r["beacon_freq_cpd"]) for r in ips], [float(r["fft_snr"]) for r in ips], s=70, marker="D", c="#CC79A7", edgecolors="#111", lw=0.6, zorder=5, label=f"Accreting WD IP Spin Controls (n={len(ips)})")
    ax1.scatter([float(r["beacon_freq_cpd"]) for r in puls], [float(r["fft_snr"]) for r in puls], s=68, marker="^", c="#0072B2", edgecolors="#111", lw=0.6, zorder=5, label=f"dSct/bCep/Mag-WD Pulsators (n={len(puls)})")
    ax1.scatter([float(r["beacon_freq_cpd"]) for r in rots], [float(r["fft_snr"]) for r in rots], s=60, marker="*", c="#D55E00", edgecolors="#111", lw=0.5, zorder=4, label=f"Rotators/Binaries/YSOs (n={len(rots)})")

    offsets = {"V1223SGR": (-40, 6), "PQGEM": (-34, 6), "HIP99770": (-52, 2), "HD131835": (-50, 2), "SIGMASCO": (6, 4), "LAWD96": (6, 4)}
    for r in trig_b:
        if r["star"] in offsets:
            ax1.annotate(r["star"], xy=(float(r["beacon_freq_cpd"]), float(r["fft_snr"])), xytext=offsets[r["star"]], textcoords="offset points", fontsize=7.6)

    ax1.axhline(15.0, color="#B00020", ls="--", lw=1.2, label="Gate B FFT SNR >= 15 (SAP >= 8)")
    ax1.set_xscale("log")
    ax1.set_xlim(1.8, 340.0)
    ax1.set_ylim(0.5, 56.0)
    ax1.set_xlabel("Fourier Peak Frequency (cycles / day)")
    ax1.set_ylabel("Narrow-Band FFT Peak SNR")
    ax1.set_title("Channel B: Coherent Optical Periodic Beacon Search (2–300 cpd)")
    ax1.grid(True, which="both", alpha=0.22, ls=":")
    ax1.legend(loc="upper right", fontsize=7.5, framealpha=0.95)

    # Panel 2: Channel C Flashes (fred_ratio vs flash_amp)
    fl = [r for r in mw if float(r["flash_amp"]) > 0]
    trig_c = [r for r in fl if r["trig_c"] == "True"]
    non_tc = [r for r in fl if r["trig_c"] == "False"]

    ax2.scatter([float(r["fred_ratio"]) for r in non_tc], [float(r["flash_amp"]) * 100.0 for r in non_tc], s=24, c="#999999", alpha=0.65, label=f"Classical Asymmetric M-Flares (n={len(non_tc)})")
    ax2.scatter([float(r["fred_ratio"]) for r in trig_c], [float(r["flash_amp"]) * 100.0 for r in trig_c], s=55, marker="*", c="#D55E00", edgecolors="#111", lw=0.5, zorder=5, label=f"Channel C Flare Triggers -> 0 ETI (n={len(trig_c)})")
    ax2.axvline(1.8, color="#B00020", ls="--", lw=1.2, label="Anti-FRED Gate (t_decay/t_rise <= 1.8)")
    ax2.axhline(1.0, color="#0072B2", ls=":", lw=1.2, label="Flash Amplitude >= 1.0%")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlim(0.25, 20.0)
    ax2.set_ylim(0.3, 250.0)
    ax2.set_xlabel(r"Pulse Decay/Rise Asymmetry ($t_{\mathrm{decay}} / t_{\mathrm{rise}}$)")
    ax2.set_ylabel("Peak Flash Flux Excess (%)")
    ax2.set_title("Channel C: Optical Flash & Anti-FRED Flare Veto (43/43 M/K Flares)")
    ax2.grid(True, which="both", alpha=0.22, ls=":")
    ax2.legend(loc="upper right", fontsize=7.8, framealpha=0.95)

    fig.suptitle("Channels B & C: Coherent Optical Beacons & Impulsive Flashes in the Milky Way", fontweight="bold")
    save_both(fig, "figN7_03_coherent_optical_beacon_fft_and_flashes.png")


def _load_lc_window(fits_file: str) -> tuple[np.ndarray, np.ndarray]:
    with fits.open(INP / "tess_lc" / fits_file, memmap=False) as hdul:
        tab = hdul[1].data
        t = np.asarray(tab["TIME"], dtype=np.float64)
        pdc = np.asarray(tab["PDCSAP_FLUX"], dtype=np.float64)
        q = np.asarray(tab["QUALITY"], dtype=np.int64)
    m = (q == 0) & np.isfinite(t) & np.isfinite(pdc) & (pdc > 0)
    t, f = t[m], pdc[m] / np.median(pdc[m])
    o = np.argsort(t)
    return t[o] - t[o][0], f[o]


def fig04_lightcurves_and_funnel(cat: list[dict[str, Any]], s3: dict[str, Any]) -> None:
    by_s = {r["star"]: r for r in cat}
    fig = plt.figure(figsize=(12.8, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, width_ratios=[1.25, 1.0])

    # Panel A: HD 145718 (YSO UX Ori 18.5% dip)
    ax1 = fig.add_subplot(gs[0, 0])
    t, f = _load_lc_window(by_s["HD145718"]["primary_fits_file"])
    ax1.plot(t[::3], f[::3], ".", ms=1.6, color="#D55E00", alpha=0.75)
    ax1.set_title(f"Channel A Example: HD 145718 (UX Ori YSO Disk, 18.5% Dip, Sec {by_s['HD145718']['primary_sector']})", fontsize=9.3)
    ax1.set_ylabel("Norm. Flux")
    ax1.grid(True, alpha=0.25, ls=":")

    # Panel B: HD 209458 (Exoplanet transits)
    ax2 = fig.add_subplot(gs[1, 0])
    t, f = _load_lc_window(by_s["HD209458"]["primary_fits_file"])
    ax2.plot(t[::2], f[::2], ".", ms=1.6, color="#009E73", alpha=0.75)
    ax2.set_title(f"Transiting Exoplanet Benchmark: HD 209458 b (1.6% Transits, P=3.52 d, Sec {by_s['HD209458']['primary_sector']})", fontsize=9.3)
    ax2.set_ylabel("Norm. Flux")
    ax2.grid(True, alpha=0.25, ls=":")

    # Panel C: LAWD 96 (phase-folded 2.694 h magnetic WD spin wave!)
    ax3 = fig.add_subplot(gs[2, 0])
    t, f = _load_lc_window(by_s["LAWD96"]["primary_fits_file"])
    # Detrend slowly over 1 d to isolate 2.694 h (f=8.90713 cpd) coherent spin wave
    f_det = f - median_filter(f, size=361, mode="nearest") + 1.0
    freq = float(by_s["LAWD96"]["beacon_freq_cpd"])
    phase = (t * freq) % 1.0
    pbins = np.linspace(0, 1, 26)
    pmids = 0.5 * (pbins[:-1] + pbins[1:])
    pvals = [np.median(f_det[(phase >= pbins[i]) & (phase < pbins[i + 1])]) for i in range(25)]
    ax3.plot(phase, (f_det - 1.0) * 100.0, ".", ms=1.2, color="#999999", alpha=0.35, label="2-min Cadences")
    ax3.plot(pmids, (np.array(pvals) - 1.0) * 100.0, "-o", ms=4, lw=1.8, color="#0072B2", label="Phase-Folded Median")
    ax3.set_ylim(-1.6, 1.6)
    ax3.set_title(f"Channel B Folded: LAWD 96 Magnetic WD Rotation (f={freq:.4f} cpd, P=2.69 h)", fontsize=9.3)
    ax3.set_xlabel("Rotational Phase")
    ax3.set_ylabel("Flux Var (%)")
    ax3.grid(True, alpha=0.25, ls=":")
    ax3.legend(loc="upper right", fontsize=7.6)

    # Panel D: Vetting Funnel
    ax_f = fig.add_subplot(gs[:, 1])
    vc = s3["vetting_class_counts"]
    stages = [
        ("TESS 2-min Downloaded", 565, "#0072B2"),
        ("Pure Milky Way Targets", s3["pure_milky_way_stars_analyzed"], "#56B4E9"),
        ("Priority MW Master Cohort", s3["pure_milky_way_master_stars"], "#009E73"),
        ("Stage 2 Triggers (Total)", s3["stage2_triggers_vetted"], "#E69F00"),
        ("M-Dwarf Flares & Active Spots", vc.get("STELLAR_FLARE_OR_ACTIVE_MDWARF_ROTATION", 0) + vc.get("BLENDED_APERTURE_OR_STARSPOT_ROTATION", 0) + vc.get("BLENDED_APERTURE_ROTATOR_OR_BINARY", 0), "#D55E00"),
        ("Known Transiting Exoplanets", vc.get("KNOWN_TRANSITING_EXOPLANET", 0), "#009E73"),
        ("YSO / Protoplanetary Disks", vc.get("YSO_OR_PROTOPLANETARY_DISK_DIPPER", 0), "#E69F00"),
        ("IP WD Spins & Pulsators", vc.get("ACCRETING_WD_INTERMEDIATE_POLAR_SPIN", 0) + vc.get("STELLAR_PULSATION_OR_AGB_RSG", 0) + vc.get("MAGNETIC_WHITE_DWARF_ROTATION", 0), "#CC79A7"),
        ("WD Blend / PDC-SAP / Bench", vc.get("PDC_SAP_DETRENDING_OR_BLENDED_WD_ARTIFACT", 0) + vc.get("CALIBRATION_BENCHMARK_ASTROPHYSICS", 0), "#999999"),
        ("Extragalactic AGN Excluded", vc.get("EXTRAGALACTIC_AGN_CONTROL", 0), "#777777"),
        ("Verified Milky Way ETI", s3["verified_eti_candidates"], "#B00020"),
    ]
    ys = np.arange(len(stages))[::-1]
    vals = [max(v, 0.7) for _, v, _ in stages]
    ax_f.barh(ys, vals, color=[c for _, _, c in stages], height=0.62, edgecolor="#111")
    ax_f.set_xscale("log")
    ax_f.set_xlim(0.5, 1800)
    ax_f.set_yticks(ys)
    ax_f.set_yticklabels([s for s, _, _ in stages], fontsize=8.4)
    for y, (_, v, _) in zip(ys, stages):
        ax_f.text(max(v, 0.85) * 1.18, y, f"{v}", va="center", fontweight="bold", fontsize=8.8)
    ax_f.set_xlabel("Milky Way Stars (log scale)")
    ax_f.set_title("Spor N7 Stage 2 -> Stage 3 Vetting Funnel (0 ETI)")
    ax_f.grid(axis="x", alpha=0.25, ls=":")

    fig.suptitle("Representative TESS 2-Min Light Curves & Multi-Sector Forensic Vetting", fontweight="bold")
    save_both(fig, "figN7_04_tess_lightcurve_gallery_and_veto_funnel.png")


def fig05_injections_and_f95(s2: dict[str, Any], s3: dict[str, Any]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2), constrained_layout=True)

    inj = s2["injections"]
    # Plot completeness across normalized supra-threshold index [0.4x, 1x, 2x, 5x] for all 3 channels
    xa = np.array([0.4, 1.0, 2.0, 5.0])
    ya = np.array([inj["channel_a_megadip"][k]["completeness"] * 100.0 for k in ("0.002", "0.005", "0.01", "0.025")])
    yb = np.array([inj["channel_b_beacon"][k]["completeness"] * 100.0 for k in ("200", "500", "1000", "2500")])
    yc = np.array([inj["channel_c_flash"][k]["completeness"] * 100.0 for k in ("0.005", "0.01", "0.025", "0.05")])

    ax1.plot(xa, ya, "-o", lw=2.0, color="#0072B2", label=f"Ch.A Arnold Megadip (ge 0.5%: {inj['completeness_a_ge_5000ppm']*100:.1f}%)")
    ax1.plot(xa, yb, "-s", lw=2.0, color="#009E73", label=f"Ch.B Optical Beacon (ge 500ppm: {inj['completeness_b_ge_500ppm']*100:.1f}%)")
    ax1.plot(xa, yc, "-^", lw=2.0, color="#D55E00", label=f"Ch.C Light-Sail Flash (ge 1.0%: {inj['completeness_c_ge_1pct']*100:.1f}%)")
    ax1.axvline(1.0, color="#B00020", ls=":", lw=1.3, label=f"Threshold Gate (Overall Eff={inj['completeness_overall_supra_threshold']*100:.1f}%)")
    ax1.set_xscale("log")
    ax1.set_xticks(xa)
    ax1.set_xticklabels(["0.4x Gate\n(Sub-Thresh)", "1.0x Gate\n(Threshold)", "2.0x Gate", "5.0x Gate"], fontsize=8.2)
    ax1.set_ylim(-5, 110)
    ax1.set_ylabel("Injection Recovery Completeness (%)")
    ax1.set_title("1,200-Trial Real-TESS Noise Injection Recovery")
    ax1.grid(True, alpha=0.25, ls=":")
    ax1.legend(loc="lower right", fontsize=7.6, framealpha=0.95)

    bl = s3["bayesian_limits_pure_milky_way_zero_eti"]
    cohorts = [
        ("Pure MW\nRaw (555)", bl["all_pure_mw_master_raw"]),
        ("Pure MW\nEff (374.3)", bl["all_pure_mw_master_eff"]),
        ("Exoplanet\nHosts (296)", bl["exoplanet_hosts"]),
        ("<10 pc\n(224)", bl["within_10pc"]),
        ("ETZ MW\n(136)", bl["etz_pure_mw"]),
    ]
    x = np.arange(len(cohorts))
    w = 0.25
    jf = [c[1]["jeffreys_f95_pct"] for c in cohorts]
    uf = [c[1]["uniform_f95_pct"] for c in cohorts]
    cp = [c[1]["clopper_pearson_f95_pct"] for c in cohorts]
    ax2.bar(x - w, jf, width=w, color="#0072B2", edgecolor="#111", lw=0.6, label="Jeffreys Beta(0.5, N+0.5)")
    ax2.bar(x, uf, width=w, color="#E69F00", edgecolor="#111", lw=0.6, label="Uniform Bayes Beta(1, N+1)")
    ax2.bar(x + w, cp, width=w, color="#009E73", edgecolor="#111", lw=0.6, label="Clopper-Pearson 95%")
    for xi, jv, uv in zip(x, jf, uf):
        ax2.text(xi - w, jv + 0.04, f"{jv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
        ax2.text(xi + 0.05, uv + 0.04, f"{uv:.2f}%", ha="center", va="bottom", fontsize=7.4, rotation=42)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[0] for c in cohorts], fontsize=8.3)
    ax2.set_ylim(0, 2.75)
    ax2.set_ylabel(r"95% Upper Limit $f_{95}$ (%)")
    ax2.set_title("Pure Milky Way Zero-ETI 95% Prevalence Bounds")
    ax2.grid(axis="y", alpha=0.25, ls=":")
    ax2.legend(loc="upper left", fontsize=7.8)

    fig.suptitle("Spor N7 Calibration (1,200 Injections) & Milky Way Bayesian Upper Limits", fontweight="bold")
    save_both(fig, "figN7_05_injection_recovery_and_bayesian_f95.png")


def fig06_milky_way_synthesis(s3: dict[str, Any]) -> None:
    bl = s3["bayesian_limits_pure_milky_way_zero_eti"]
    rows = [
        ("Spor N2: Rubin SSOFT + Trails", "Solar System (1 - 40 AU)", 0.1403, "#CC79A7", "K-I Probes & Orbits"),
        ("Spor N3: Rubin V2+V3 DDF", "Galactic Field (2,100 stars)", 0.1133, "#0072B2", "Optical Transient/Dim"),
        ("Spor N1C: VASCO Multi-Decade", "1950-2023 Optical (1,197 stars)", 0.1603, "#009E73", "K-II Vanishing Stars"),
        ("Spor N4: 71.92-Oct Radio Bridge", "54 MHz-3 GHz + FRB (1,083 stars)", 0.1772, "#D55E00", "Radio Beacons / FRB"),
        ("Spor N5: 10-Yr Secular IR+Opt", "2010-2024 NEOWISE/ZTF (1,083 stars)", 0.1772, "#E69F00", "Dyson Shell Construction"),
        ("Spor N7: TESS 2-Min Space Phot.", "Pure Milky Way (555 / 374.3 eff)", bl["all_pure_mw_master_eff"]["jeffreys_f95_pct"], "#B00020", "Megadips, 2-300cpd Beacons, Flashes"),
    ]
    fig, ax = plt.subplots(figsize=(12.6, 5.2), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    vals = [r[2] for r in rows]
    ax.barh(ys, vals, height=0.60, color=[r[3] for r in rows], edgecolor="#111", lw=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r[0]}\n[{r[1]}]" for r in rows], fontsize=8.6)
    ax.set_xlim(0, 0.98)
    for y, (_, _, v, _, desc) in zip(ys, rows):
        ax.text(v + 0.012, y, f"Jeffreys f95 = {v:.4f}%  ({desc})", va="center", ha="left", fontsize=8.4)
    ax.set_xlabel(r"95% Jeffreys Bayesian Upper Limit $f_{95}$ (%) on Galactic ETI Prevalence (0 ETI)")
    ax.set_title("Milky Way SETI Multi-Timescale & Multi-Wavelength Synthesis (2 min to 73 yr, 0 ETI)", fontweight="bold")
    ax.grid(axis="x", alpha=0.25, ls=":")
    save_both(fig, "figN7_06_milky_way_unified_seti_landscape.png")


def main() -> int:
    cat = list(csv.DictReader((RES / "N7_TESS_MILKY_WAY_CATALOG.csv").open("r", encoding="utf-8")))
    vet = list(csv.DictReader((RES / "N7_CANDIDATES_VETTED.csv").open("r", encoding="utf-8")))
    s2 = json.loads((RES / "N7_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((RES / "N7_STAGE3_VETTING.json").read_text(encoding="utf-8"))

    fig01_sky_and_distance(cat, vet)
    fig02_megadips_and_asymmetry(cat, vet)
    fig03_beacons_and_flashes(cat, vet)
    fig04_lightcurves_and_funnel(cat, s3)
    fig05_injections_and_f95(s2, s3)
    fig06_milky_way_synthesis(s3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
