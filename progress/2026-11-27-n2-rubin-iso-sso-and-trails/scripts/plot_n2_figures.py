#!/usr/bin/env python3
"""
Generate all 6 300-DPI publication figures for Spor N2 (figN2_01 through figN2_06)
in both workspace figures/ and setisearch/progress/2026-11-27-n2-rubin-iso-sso-and-trails/figures/.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import shutil
from typing import Any

from astropy.io import fits
from astropy.visualization import ImageNormalize, ZScaleInterval
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n2_20261127_rubin_iso_sso_and_trails"
INP = ROOT / "inputs_n2_20261127"
RES = WS / "results"
FIGS = WS / "figures"
REPO_FIGS = ROOT / "setisearch" / "progress" / "2026-11-27-n2-rubin-iso-sso-and-trails" / "figures"

plt.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "legend.fontsize": 8.2,
    "figure.facecolor": "white",
    "axes.facecolor": "#fbfbfd",
    "axes.grid": True,
    "grid.alpha": 0.28,
})


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _save_fig(fig: plt.Figure, fname: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    REPO_FIGS.mkdir(parents=True, exist_ok=True)
    p1 = FIGS / fname
    p2 = REPO_FIGS / fname
    fig.savefig(p1, dpi=300, bbox_inches="tight", pad_inches=0.14)
    shutil.copy2(p1, p2)
    plt.close(fig)
    print(f"Saved {fname}: {p1.stat().st_size:,} B")


def fig1_hyperbolic_and_nongrav() -> None:
    hyp = list(csv.DictReader((RES / "N2A_HYPERBOLIC_CENSUS.csv").open(encoding="utf-8")))
    vet = {r["spkid"]: r for r in csv.DictReader((RES / "N2A_DETAILED_VETTED.csv").open(encoding="utf-8"))}
    ng = list(csv.DictReader((RES / "N2A_NONGRAV_ASTEROIDS.csv").open(encoding="utf-8")))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.6), constrained_layout=True)

    # Panel 1: |a_au| vs e
    xs_oort, ys_oort = [], []
    for r in hyp:
        e_v, a_v = _f(r["e"]), _f(r["a_au"])
        if e_v is None or a_v is None or a_v >= 0:
            continue
        if r["classification"] == "PLANET_PERTURBED_OORT_HYPERBOLIC":
            xs_oort.append(e_v)
            ys_oort.append(abs(a_v))
    ax1.scatter(xs_oort, ys_oort, s=16, alpha=0.55, color="#4e79a7", label=f"Oort-perturbed comets (N={len(xs_oort)}, v_inf < 10 km/s)", zorder=2)

    # Line for v_inf = 10 km/s -> |a| = MU_SUN / (10^2 * AU_KM) = 8.8712 AU
    a_10 = 1.32712440018e11 / (100.0 * 1.495978707e8)
    ax1.axhline(a_10, color="#b07aa1", ls="--", lw=1.4, label=f"v_inf = 10 km/s threshold (|a| = {a_10:.2f} AU)")

    iso_styles = {
        "2025 N1": ("#d62728", "D", "3I/ATLAS (58.0 km/s)", (-55, 10)),
        "2019 Q4": ("#e15759", "^", "2I/Borisov (32.3 km/s)", (10, -10)),
        "2017 U1": ("#f28e2b", "s", "1I/'Oumuamua (26.4 km/s)", (12, 2)),
        "2023 F2": ("#59a14f", "v", "C/2023 F2 (SOHO 1d)", (10, 9)),
        "1999 U2": ("#76b7b2", "v", "C/1999 U2 (SOHO 1d)", (-8, -16)),
    }
    for r in hyp:
        if r["pdes"] in iso_styles:
            c, m, lbl, off = iso_styles[r["pdes"]]
            ev, av = float(r["e"]), abs(float(r["a_au"]))
            ax1.scatter([ev], [av], s=85, color=c, marker=m, edgecolor="black", lw=0.8, zorder=5, label=lbl)
            ax1.annotate(lbl.split(" (")[0], (ev, av), xytext=off, textcoords="offset points", fontsize=8.5, fontweight="bold", color=c)

    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.92, 8.2)
    ax1.set_ylim(0.14, None)
    ax1.set_xlabel("Eccentricity e (log scale)")
    ax1.set_ylabel("|Semimajor Axis a| [AU] (log scale)")
    ax1.set_title("N2A: All 526 JPL SBDB Hyperbolic Orbits (e > 1.0)")
    ax1.legend(loc="upper right", framealpha=0.92, fontsize=7.8)

    # Panel 2: Diameter vs (A/m)_SRP
    cls_colors = {
        "YARKOVSKY_THERMAL_DRIFT": ("#7f7f7f", "o", 14, 0.38, "Yarkovsky Drift (N=596)"),
        "DARK_COMET_OR_ACTIVE_ASTEROID_ANOMALY": ("#d62728", "s", 46, 0.90, "Dark Comets / Active Ast. (N=16)"),
        "METER_SCALE_SRP_OR_MINIMOON": ("#1f77b4", "^", 52, 0.90, "Meter-Scale SRP / Mini-Moons (N=13)"),
    }
    for cls_k, (col, mrk, sz, alp, lbl) in cls_colors.items():
        dx, dy = [], []
        for r in ng:
            if r["classification"] != cls_k:
                continue
            d_m = _f(r["d_est_m"])
            am = _f(r["am_srp_m2_kg"])
            if d_m and am and d_m > 0 and am > 0:
                dx.append(d_m)
                dy.append(am)
        ax2.scatter(dx, dy, s=sz, color=col, marker=mrk, alpha=alp, edgecolor="black" if sz > 20 else "none", lw=0.6, label=lbl, zorder=3 if sz > 20 else 2)

    # Add 1I/'Oumuamua manually from N2A_HYPERBOLIC_CENSUS
    for r in hyp:
        if r["pdes"] == "2017 U1":
            d1, am1 = float(r["d_est_m"]), float(r["am_srp_m2_kg"])
            ax2.scatter([d1], [am1], s=110, color="#ff7f0e", marker="*", edgecolor="black", lw=0.9, zorder=6, label="1I/'Oumuamua (outgassing/ISO)")
            ax2.annotate("1I/'Oumuamua", (d1, am1), xytext=(8, -4), textcoords="offset points", fontsize=8.5, fontweight="bold", color="#d95f02")

    # Label key benchmarks cleanly with arrows where crowded
    labels_ng = {"457175": ("362P/2008 GO98", (-78, -14)), "2020 CD3": ("2020 CD3 (mini-moon)", (14, 24)), "2016 NJ33": ("2016 NJ33 (dark comet)", (10, 6))}
    for r in ng:
        if r["pdes"] in labels_ng and _f(r["d_est_m"]) and _f(r["am_srp_m2_kg"]) and float(r["am_srp_m2_kg"]) > 0:
            txt, off = labels_ng[r["pdes"]]
            ap = dict(arrowstyle="-", lw=0.7, color="#444444") if r["pdes"] == "2020 CD3" else None
            ax2.annotate(txt, (float(r["d_est_m"]), float(r["am_srp_m2_kg"])), xytext=off, textcoords="offset points", fontsize=8.0, arrowprops=ap)

    d_grid = np.logspace(0, 4.5, 200)
    am_rock = 3.0 / (2.0 * 2500.0 * d_grid)
    ax2.plot(d_grid, am_rock, "k--", lw=1.3, label="Solid rock SRP limit (rho=2500 kg/m³)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Estimated Diameter D [m] (p_V = 0.14)")
    ax2.set_ylabel("Effective Area-to-Mass Ratio (A/m)_SRP [m²/kg]")
    ax2.set_title("N2A: Non-Gravitational Acceleration Physics Across 625 Asteroids + 1I")
    ax2.legend(loc="lower left", framealpha=0.92, fontsize=7.8)

    fig.suptitle("Spor N2A — Hyperbolic Interstellar Objects & Non-Gravitational Small-Body Physics", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN2_01_hyperbolic_and_nongrav_census.png")


def fig2_ssoft_anomaly_landscape() -> None:
    well = list(csv.DictReader((RES / "N2B_SSOFT_WELL_SAMPLED.csv").open(encoding="utf-8")))
    vet = {r["sso_name"]: r for r in csv.DictReader((RES / "N2B_SSOFT_VETTED.csv").open(encoding="utf-8"))}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5), constrained_layout=True)

    # Panel 1: rms vs chi2red
    bg_rms, bg_chi = [], []
    tr_rms, tr_chi, tr_lbl = [], [], []
    for r in well:
        rm = _f(r["rms"])
        ch = _f(r["chi2red"])
        if rm is None or ch is None or ch <= 0:
            continue
        if r["trig_phot_high_rms"] == "True":
            tr_rms.append(rm)
            tr_chi.append(ch)
            tr_lbl.append(r["sso_name"])
        else:
            bg_rms.append(rm)
            bg_chi.append(ch)

    ax1.scatter(bg_rms, bg_chi, s=12, alpha=0.45, color="#4e79a7", label=f"Normal well-sampled SSOs (N={len(bg_rms)})")
    ax1.scatter(tr_rms, tr_chi, s=42, color="#d62728", edgecolor="black", lw=0.6, zorder=4, label=f"Photometric triggers (N={len(tr_rms)}: vetted 100%)")
    ax1.axvline(0.25, color="#d62728", ls="--", lw=1.2)
    ax1.axhline(100.0, color="#d62728", ls="--", lw=1.2)
    phot_offs = [(-50, 8), (-62, -13), (-55, 8), (-55, -12)]
    for (rm, ch, nm), off in zip(sorted(zip(tr_rms, tr_chi, tr_lbl), reverse=True)[:4], phot_offs):
        ax1.annotate(nm, (rm, ch), xytext=off, textcoords="offset points", fontsize=8.0, fontweight="bold")

    ax1.set_yscale("log")
    ax1.set_xlabel("SHG1G2 Lightcurve Residual RMS [mag]")
    ax1.set_ylabel("Reduced Chi-Square (chi2red, log)")
    ax1.set_title("N2B: Photometric Scatter Screen (1,368 Rubin SSOs, n_obs >= 10)")
    ax1.legend(loc="lower right", framealpha=0.92)

    # Panel 2: mean_astrometry vs std_astrometry
    bg_m, bg_s, tr_m, tr_s, tr_nm = [], [], [], [], []
    for r in well:
        ma = _f(r["mean_astrometry"])
        sa = _f(r["std_astrometry"])
        if ma is None or sa is None:
            continue
        if r["trig_astrom_scatter"] == "True":
            tr_m.append(ma)
            tr_s.append(sa)
            tr_nm.append(r["sso_name"])
        else:
            bg_m.append(ma)
            bg_s.append(sa)

    ax2.scatter(bg_m, bg_s, s=12, alpha=0.45, color="#59a14f", label=f"Baseline astrometry (N={len(bg_m)})")
    ax2.scatter(tr_m, tr_s, s=42, color="#ff7f0e", edgecolor="black", lw=0.6, zorder=4, label=f"Astrometric triggers (N={len(tr_m)}: vetted 100%)")
    ax2.axvline(0.20, color="#ff7f0e", ls="--", lw=1.2)
    ax2.axhline(0.08, color="#ff7f0e", ls="--", lw=1.2)
    for ma, sa, nm in sorted(zip(tr_m, tr_s, tr_nm), key=lambda t: t[0] + t[1], reverse=True)[:4]:
        ax2.annotate(nm, (ma, sa), xytext=(-54, 7 if sa < 0.25 else -12), textcoords="offset points", fontsize=8.0, fontweight="bold")

    ax2.text(0.03, 0.96, "Note: 90.2% of SHG1G2 fits pile up at\noptimizer bound R = 0.30 (model artifact)", transform=ax2.transAxes,
             va="top", fontsize=8.0, bbox=dict(boxstyle="round,pad=0.3", fc="#fff7e6", ec="#e6ab02"))
    ax2.set_xlabel("Mean Astrometric Offset vs Ephemeris [arcsec]")
    ax2.set_ylabel("Std Astrometric Offset [arcsec]")
    ax2.set_title("N2B: Astrometric Residual Screen (47 Vetted -> Ephemeris/Arc)")
    ax2.legend(loc="upper left", bbox_to_anchor=(0.015, 0.80), framealpha=0.92)

    fig.suptitle("Spor N2B — Fink Vera Rubin LSST SSOFT Anomaly Landscape (N = 1,368, n_obs >= 10)", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN2_02_rubin_ssoft_anomaly_landscape.png")


def fig3_sso_top_outliers_lightcurves() -> None:
    vet = list(csv.DictReader((RES / "N2B_SSOFT_VETTED.csv").open(encoding="utf-8")))
    # Pick top 3 astrometric and top 3 photometric outliers with lightcurves
    ast_top = [r for r in vet if r["trig_astrom_scatter"] == "True" and int(r["fink_sso_n_epochs"]) >= 5][:3]
    phot_top = [r for r in vet if r["trig_phot_high_rms"] == "True" and int(r["fink_sso_n_epochs"]) >= 5][:3]
    picks = ast_top + phot_top

    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.0), constrained_layout=True)
    band_cols = {"u": "#9467bd", "g": "#2ca02c", "r": "#d62728", "i": "#ff7f0e", "z": "#8c564b", "y": "#17becf"}

    for ax, r in zip(axes.ravel(), picks):
        num = r["sso_number"]
        ident = num if (num and num.lower() != "nan") else r["sso_name"]
        safe = ident.replace("/", "_").replace(" ", "_")
        lp = INP / "sso_lightcurves" / f"sso_{safe}.json"
        pts = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else []
        if not pts:
            safe2 = r["sso_name"].replace("/", "_").replace(" ", "_")
            lp2 = INP / "sso_lightcurves" / f"sso_{safe2}.json"
            pts = json.loads(lp2.read_text(encoding="utf-8")) if lp2.exists() else []

        mjd0 = min((_f(p.get("r:midpointMjdTai")) or 61340.0) for p in pts) if pts else 61340.0
        for band in ("u", "g", "r", "i", "z", "y"):
            bx, by, be = [], [], []
            for p in pts:
                if p.get("r:band") != band:
                    continue
                fx, fe, mjd = _f(p.get("r:psfFlux")), _f(p.get("r:psfFluxErr")), _f(p.get("r:midpointMjdTai"))
                if fx and fx > 0 and mjd is not None:
                    bx.append(mjd - mjd0)
                    by.append(-2.5 * math.log10(fx) + 31.4)
                    be.append(1.0857 * (fe / fx) if (fe and fe > 0) else 0.05)
            if bx:
                ax.errorbar(bx, by, yerr=be, fmt="o", ms=4.5, lw=0.9, color=band_cols.get(band, "k"), label=f"{band} ({len(bx)})", alpha=0.88)

        ax.invert_yaxis()
        tag = "ASTROM" if r["trig_astrom_scatter"] == "True" else "PHOT"
        short_disp = r["stage3_disposition"].replace("KNOWN_SSO_EPHEMERIS_OR_ORBIT_ARC_RESIDUAL", "Orbit/Ephemeris Resid.").replace("ROTATING_ELONGATED_ASTEROID_LIGHTCURVE_MODULATION", "Rotating Asteroid").replace("MULTIBAND_OUTLIER_OR_EDGE_BADPIX_IN_SHG1G2", "Band-Mix / Outlier").replace("ASTEROID_COLOR_STEP_OR_BAND_MIXING_IN_SHG1G2", "Color-Step SHG1G2")
        ax.set_title(f"[{tag}] {r['sso_name']} ({r['jpl_orbit_class']})\nN={r['fink_sso_n_epochs']} | span={r['cross_band_color_span']}m | {short_disp}", fontsize=9.0)
        ax.set_xlabel("Days since first Rubin detection")
        ax.set_ylabel("Rubin PSF Mag [AB]")
        ax.legend(loc="best", fontsize=7.5, ncol=2)

    fig.suptitle("Spor N2B — Real Vera Rubin Multi-Band Lightcurves of Top 6 SSOFT Outliers", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN2_03_rubin_sso_top_outliers_lightcurves.png")


def fig4_faint_trails_kinematics() -> None:
    vet = list(csv.DictReader((RES / "N2C_FAINT_TRAILS_VETTED.csv").open(encoding="utf-8")))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5), constrained_layout=True)

    disp_map = {
        "KNOWN_LINKED_RUBIN_SSO": ("#2ca02c", "s", 46, "Linked Rubin SSO (N=12)"),
        "SKYBOT_KNOWN_SOLAR_SYSTEM_OBJECT": ("#1f77b4", "^", 68, "Unlinked -> IMCCE SkyBoT Match"),
        "STATIC_TEMPLATE_OR_RECURRING_ARTIFACT": ("#9467bd", "X", 70, "Static/Template Artifact"),
        "UNLINKED_FAST_NEO_OR_MBA_SINGLE_PASS_CANDIDATE": ("#d62728", "o", 52, "Unlinked Fast NEO/MBA w/ FITS Cutout (N=16)"),
        "UNLINKED_FAST_MOVER_NO_CUTOUT_VET": ("#ff7f0e", "o", 26, "Unlinked Fast Mover (Single-Pass, Rel>=0.70)"),
        "LOW_RELIABILITY_TRAIL_FILTERED": ("#7f7f7f", ".", 24, "Low-Reliability Trail (<0.70)"),
    }
    for dk, (col, mrk, sz, lbl) in disp_map.items():
        sub = [r for r in vet if r["stage3_disposition"] == dk]
        if not sub:
            continue
        ax1.scatter([float(r["trail_mag_ab"]) for r in sub], [float(r["ang_rate_deg_day"]) for r in sub],
                    s=sz, color=col, marker=mrk, alpha=0.88, edgecolor="black" if sz >= 45 else "none", lw=0.6, label=f"{lbl.split(' (')[0]} (N={len(sub)})")
        ax2.scatter([abs(float(r["ecliptic_lat_deg"])) for r in sub], [float(r["ang_rate_deg_day"]) for r in sub],
                    s=sz, color=col, marker=mrk, alpha=0.88, edgecolor="black" if sz >= 45 else "none", lw=0.6, label=f"{lbl.split(' (')[0]} (N={len(sub)})")

    ax1.axhline(0.5, color="#555555", ls=":", lw=1.2, label="MBA upper (~0.5 deg/day)")
    ax1.text(0.02, 0.96, "All 113/113 in NEO/ISO range [1.29–6.70 deg/d] (GEO=360, LEO>40000 deg/d off-scale)", transform=ax1.transAxes, va="top", fontsize=7.8, color="#333333")
    ax1.set_ylim(0, 7.6)
    ax1.set_xlabel("Rubin Trail Magnitude [AB mag]")
    ax1.set_ylabel("Angular Sky Speed [deg / day]")
    ax1.set_title("N2C: All 113 Fink faint_trails — Speed vs Magnitude")
    ax1.legend(loc="lower left", bbox_to_anchor=(0.01, 0.08), fontsize=7.5, framealpha=0.92)

    ax2.set_ylim(0, 7.6)
    ax2.set_xlabel("Absolute Ecliptic Latitude |beta| [deg]")
    ax2.set_ylabel("Angular Sky Speed [deg / day]")
    ax2.set_title("N2C: Ecliptic Latitude vs Sky Speed (Stage 3 Vetted)")
    ax2.legend(loc="upper right", fontsize=7.6, framealpha=0.92)

    fig.suptitle("Spor N2C — Vera Rubin faint_trails Kinematics & Multi-Archive Disposition (Zero LEO/GEO Satellites)", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN2_04_rubin_faint_trails_kinematics.png")


def _load_fits_2d(p: pathlib.Path) -> np.ndarray | None:
    if not p.exists():
        return None
    with fits.open(p, memmap=False) as hdul:
        for h in hdul:
            if h.data is not None and h.data.ndim == 2:
                return np.asarray(h.data, dtype=float)
    return None


def fig5_faint_trails_cutout_gallery() -> None:
    vet = list(csv.DictReader((RES / "N2C_FAINT_TRAILS_VETTED.csv").open(encoding="utf-8")))
    unl = [r for r in vet if r["stage3_disposition"] in ("UNLINKED_FAST_NEO_OR_MBA_SINGLE_PASS_CANDIDATE", "SKYBOT_KNOWN_SOLAR_SYSTEM_OBJECT") and r["diff_cutout_peak_snr"]][:4]
    lnk = [r for r in vet if r["stage3_disposition"] == "KNOWN_LINKED_RUBIN_SSO" and r["diff_cutout_peak_snr"]][:2]
    picks = unl + lnk

    fig, axes = plt.subplots(len(picks), 3, figsize=(10.5, 2.75 * len(picks)), constrained_layout=True)
    for row_i, r in enumerate(picks):
        sid = r["diaSourceId"]
        files = sorted((INP / "cutouts").glob(f"n2c_*_{sid}_Science.fits"))
        base = files[0].name.rsplit("_Science.fits", 1)[0] if files else ""
        for col_i, kind in enumerate(("Science", "Template", "Difference")):
            ax = axes[row_i, col_i]
            fp = INP / "cutouts" / f"{base}_{kind}.fits"
            img = _load_fits_2d(fp)
            if img is not None:
                fin = img[np.isfinite(img)]
                norm = ImageNormalize(fin, interval=ZScaleInterval()) if fin.size > 10 else None
                ax.imshow(np.nan_to_num(img, nan=0.0), origin="lower", cmap="gray_r" if kind != "Difference" else "magma", norm=norm)
            ax.set_xticks([])
            ax.set_yticks([])
            if row_i == 0:
                ax.set_title(f"Rubin {kind} Cutout", fontweight="bold")
            if col_i == 0:
                role = "LINKED CTRL" if r["linked_sso"] == "True" else "UNLINKED"
                ax.set_ylabel(f"{role}\n{r['ang_rate_deg_day'][:4]} deg/d\nSNR={r['diff_cutout_peak_snr']} | a/b={r['diff_elongation_ab']}", fontsize=8.2, fontweight="bold")

    fig.suptitle("Spor N2C — Real Vera Rubin FITS Cutout Gallery (4 Fastest Unlinked Trails + 2 Linked Controls)", fontsize=11.5, fontweight="bold")
    _save_fig(fig, "figN2_05_rubin_faint_trails_fits_gallery.png")


def fig6_injection_and_unified_bounds() -> None:
    st3 = json.loads((RES / "N2_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n2b = st3["n2b_rubin_ssoft"]
    n2a = st3["n2a_iso_and_nongrav"]
    n2c = st3["n2c_faint_trails"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5), constrained_layout=True)

    # Panel 1: Injection-recovery curves (1,200 trials)
    phot_x = sorted(float(k) for k in n2b["phot_injection_grid"])
    phot_y = [100.0 * n2b["phot_injection_grid"][str(x)]["completeness"] for x in phot_x]
    ast_x = sorted(float(k) for k in n2b["astrom_injection_grid"])
    ast_y = [100.0 * n2b["astrom_injection_grid"][str(x)]["completeness"] for x in ast_x]

    ax1.plot(phot_x, phot_y, "o-", lw=2.2, ms=6.5, color="#d62728", label="Photometric glint/pulse Δm [mag] (600 trials)")
    for x, y in zip(phot_x, phot_y):
        off = (10, -4) if y < 5 else (0, 7)
        ax1.annotate(f"{y:.0f}%", (x, y), xytext=off, textcoords="offset points", ha="center", fontsize=8.0, color="#d62728")

    ax1_top = ax1.twiny()
    ax1_top.plot(ast_x, ast_y, "s--", lw=2.2, ms=6.5, color="#1f77b4", label="Astrometric non-grav drift δ_ast [arcsec] (600 trials)")
    ax1_top.set_xlabel("Injected Astrometric Drift δ_ast [arcsec]", color="#1f77b4")
    ax1_top.tick_params(axis="x", colors="#1f77b4")
    ax1_top.grid(False)

    ax1.set_ylim(-5, 113)
    ax1.set_xlabel("Injected Photometric Pulse Amplitude Δm [mag]", color="#d62728")
    ax1.set_ylabel("Detection Completeness [%]")
    ax1.set_title("N2B: 1,200 Synthetic Injection-Recovery Trials", pad=10)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_top.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=8.0, framealpha=0.92)

    # Panel 2: Bayesian f95 bounds
    cats = [
        f"N2A Hyperbolic\n(N={n2a['hyperbolic_total']})",
        f"N2A Non-Grav Ast.\n(N={n2a['nongrav_asteroids_total']})",
        f"N2B SSOFT Phot\n(N_eff={n2b['bounds_well_sampled_phot_dm_ge_1p0']['n_eff']:.0f})",
        f"N2B SSOFT Astrom\n(N_eff={n2b['bounds_well_sampled_astrom_drift_ge_0p20']['n_eff']:.0f})",
        f"N2C faint_trails\n(N={n2c['trails_vetted_total']})",
    ]
    b_objs = [
        n2a["bounds_hyperbolic_eti"],
        n2a["bounds_nongrav_asteroids_eti"],
        n2b["bounds_well_sampled_phot_dm_ge_1p0"],
        n2b["bounds_well_sampled_astrom_drift_ge_0p20"],
        n2c["bounds_trails_eti"],
    ]
    x = np.arange(len(cats))
    w = 0.25
    j_vals = [b["jeffreys_f95_pct"] for b in b_objs]
    u_vals = [b["uniform_f95_pct"] for b in b_objs]
    c_vals = [b["clopper_pearson_f95_pct"] for b in b_objs]

    b1 = ax2.bar(x - w, j_vals, width=w, color="#1f77b4", label="Jeffreys Beta (0.5, N+0.5)")
    b2 = ax2.bar(x, u_vals, width=w, color="#ff7f0e", label="Uniform Bayes (1, N+1)")
    b3 = ax2.bar(x + w, c_vals, width=w, color="#2ca02c", label="Clopper-Pearson Frequentist")
    for bars in (b1, b2, b3):
        for bar in bars:
            hv = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2, hv + 0.05, f"{hv:.2f}%", ha="center", va="bottom", fontsize=7.2, rotation=90)

    ax2.set_ylim(0, max(c_vals) * 1.32)
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, fontsize=8.2)
    ax2.set_ylabel("95% Upper Limit f_95 [%] (k = 0 ETI)")
    ax2.set_title("Spor N2 Unified Zero-ETI Upper Limits (Jeffreys / Uniform / CP)")
    ax2.legend(loc="upper left", framealpha=0.92)

    fig.suptitle("Spor N2 — Injection Completeness & Exact Analytical Bayesian Zero-ETI Bounds", fontsize=12, fontweight="bold")
    _save_fig(fig, "figN2_06_n2_injection_and_unified_bounds.png")


def main() -> int:
    fig1_hyperbolic_and_nongrav()
    fig2_ssoft_anomaly_landscape()
    fig3_sso_top_outliers_lightcurves()
    fig4_faint_trails_kinematics()
    fig5_faint_trails_cutout_gallery()
    fig6_injection_and_unified_bounds()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
