#!/usr/bin/env python3
"""
Generate 6 publication-grade 300-DPI figures (figN01-figN06) for Spor N1
(Project Hephaistos II, Blind DDF Dyson Survey, and Multi-Decade VASCO Screen).
"""
from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n1_20261126_dyson_hephaistos_and_vasco")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n1_20261126")
RESULTS = WS / "results"
FIGS = WS / "figures"
REPO_FIGS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/setisearch/progress/2026-11-26-n1-dyson-hephaistos-and-vasco/figures")

plt.rcParams.update({
    "font.size": 9.2,
    "axes.titlesize": 10.0,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.0,
    "xtick.labelsize": 8.2,
    "ytick.labelsize": 8.2,
    "legend.fontsize": 7.8,
    "figure.facecolor": "white",
    "axes.facecolor": "#fcfcfd",
    "axes.grid": True,
    "grid.alpha": 0.25,
})


def save_both(fig: plt.Figure, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    REPO_FIGS.mkdir(parents=True, exist_ok=True)
    p1 = FIGS / name
    p2 = REPO_FIGS / name
    fig.savefig(p1, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    shutil.copy2(p1, p2)


def _norm_img(img: np.ndarray, signed: bool = False):
    fin = img[np.isfinite(img)]
    if len(fin) == 0:
        return img, 0.0, 1.0
    med = float(np.median(fin))
    mad = max(1e-8, 1.4826 * float(np.median(np.abs(fin - med))))
    disp = np.arcsinh(np.maximum(0.0, img - med) / (2.0 * mad)) if not signed else np.arcsinh((img - med) / (2.0 * mad))
    vmin = 0.0 if not signed else -float(np.percentile(np.abs(disp[np.isfinite(disp)]), 99.5))
    vmax = float(np.percentile(disp[np.isfinite(disp)], 99.5)) if not signed else -vmin
    return disp, vmin, max(vmin + 0.3, vmax)


def plot_fig1_heph_seds():
    import sys
    sys.path.insert(0, str(WS / "scripts"))
    import n1_analyzer as na

    heph = list(csv.DictReader((RESULTS / "N1A_HEPHAISTOS_7CANDIDATES.csv").open(encoding="utf-8")))
    gaia_rows = {r["source_id"]: r for r in na.load_tap_table(INPUTS / "hephaistos" / "hephaistos_gaia.csv")}
    tm_rows = na.load_tap_table(INPUTS / "hephaistos" / "hephaistos_2mass.csv")
    wise_rows = na.load_tap_table(INPUTS / "hephaistos" / "hephaistos_allwise.csv")

    fig, axes = plt.subplots(2, 4, figsize=(15.0, 7.6))
    axes_flat = axes.ravel()
    wgrid = np.geomspace(0.42, 26.0, 200)

    for idx, row in enumerate(heph):
        ax = axes_flat[idx]
        lbl = row["label"]
        gid = row["gaia_source_id"]
        g = gaia_rows[gid]
        gra, gdec = float(g["ra"]), float(g["dec"])
        pmra, pmdec = na.safe_float(g.get("pmra")), na.safe_float(g.get("pmdec"))
        ra2m, dec2m = na.propagate_coords(gra, gdec, pmra, pmdec, 2000.0 - 2016.0)
        raw_w, dec_w = na.propagate_coords(gra, gdec, pmra, pmdec, 2010.5 - 2016.0)
        b2m = min([t for t in tm_rows if na.angsep_arcsec(ra2m, dec2m, float(t["ra"]), float(t["dec"])) <= 4.0], key=lambda t: na.angsep_arcsec(ra2m, dec2m, float(t["ra"]), float(t["dec"])))
        bw = min([w for w in wise_rows if na.angsep_arcsec(raw_w, dec_w, float(w["ra"]), float(w["dec"])) <= 5.0], key=lambda w: na.angsep_arcsec(raw_w, dec_w, float(w["ra"]), float(w["dec"])))
        _, waves, fluxes, errs = na.build_sed_arrays(g, b2m, bw)

        t1 = float(row["t_star_1"])
        lom1 = float(row["log_om_star_1"])
        td = float(row["t_ds_k"])
        lomd = float(row["log_om_ds_1"])
        m_star = (10.0 ** lom1) * na.bnu_jy(wgrid, t1)
        m_ds = (10.0 ** lomd) * na.bnu_jy(wgrid, td)
        m_tot = m_star + m_ds

        ax.plot(wgrid, m_star * 1e3, color="#4c78a8", ls="--", lw=1.2, label=f"Photosphere ({t1:.0f} K)")
        ax.plot(wgrid, m_ds * 1e3, color="#f58518", ls=":", lw=1.3, label=f"IR Comp ({td:.0f} K, γ={float(row['gamma']):.3f})")
        ax.plot(wgrid, m_tot * 1e3, color="#111111", lw=1.5, label="Total SED Fit")
        ax.errorbar(waves, fluxes * 1e3, yerr=errs * 1e3, fmt="o", ms=4.5, color="#e45756", ecolor="#333333", capsize=2, zorder=5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.4, 28)
        ymin = max(1e-3, float(np.min(fluxes * 1e3)) * 0.25)
        ymax = float(np.max(fluxes * 1e3)) * 3.5
        ax.set_ylim(ymin, ymax)
        short_disp = {
            "UNBLENDED_IN_DR10_NEEDS_JWST_OR_ALMA": "0 DR10 blends",
            "EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF": f"{row['ls_extended_galaxies_le8arcsec']} ext. gal. in PSF",
            "NEARBY_FAINT_NEIGHBOR_IN_WISE_PSF": "1 faint neighbor",
            "RADIO_AGN_AND_GALAXY_BLEND_IN_WISE_PSF": "127σ AGN + 6 gal.",
        }.get(row["disposition"], row["disposition"])
        ax.set_title(f"Cand {lbl} ({row['dist_pc']} pc) | {short_disp}", fontsize=8.8)
        ax.set_xlabel("Wavelength [µm]")
        ax.set_ylabel("Flux Density [mJy]")
        ax.legend(loc="lower right", fontsize=6.9, framealpha=0.9)

    ax_sum = axes_flat[7]
    ax_sum.axis("off")
    lines = ["Project Hephaistos II Audit Summary (7/7):", ""]
    for row in heph:
        lines.append(f"• {row['label']}: Δχ²={float(row['delta_chi2']):.1f}, γ={float(row['gamma']):.3f}, W3/M0={row['w3_excess_ratio']}x")
        lines.append(f"   DR10 ext={row['ls_extended_galaxies_le8arcsec']} | VLASS SNR={row['vlass_peak_snr'] or 'South<-40°'}")
    lines.extend(["", "Conclusion: 6/7 show clear DR10 blends /", "127σ radio AGN; Candidate A unblended in", "DR10 (2.56σ VLASS), 0 verified ETI."])
    ax_sum.text(0.03, 0.96, "\n".join(lines), va="top", ha="left", fontsize=8.4, family="monospace",
                bbox=dict(boxstyle="round,pad=0.45", fc="#f4f6f9", ec="#7a8b99"))

    fig.suptitle("Spor N1A: Project Hephaistos II (A–G) 10-Band Optical–Mid-IR Blackbody SED Fits", fontsize=12.0, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    save_both(fig, "figN01_hephaistos_7candidates_seds.png")


def plot_fig2_heph_cutouts():
    heph = list(csv.DictReader((RESULTS / "N1A_HEPHAISTOS_7CANDIDATES.csv").open(encoding="utf-8")))
    fig, axes = plt.subplots(7, 4, figsize=(11.2, 16.5))
    cols = [("dss2", "DSS2 Red (~1990s)"), ("ls_dr10", "Legacy DR10 Opt (~2020)"), ("unwise", "unWISE NEO7 W1/W2"), ("vlass", "VLASS 1.2 (3 GHz Radio)")]

    for r_idx, row in enumerate(heph):
        lbl = row["label"]
        for c_idx, (cname, ctitle) in enumerate(cols):
            ax = axes[r_idx, c_idx]
            ax.grid(False)
            fp = INPUTS / "cutouts" / f"heph_{lbl}_{cname}.fits"
            if fp.exists() and fp.read_bytes()[:6] == b"SIMPLE":
                with fits.open(fp) as hdul:
                    img = next(np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2)
                if img.ndim > 2:
                    # RGB or multi-band: take r-band (index 1 if 3 bands) or mean
                    img = img[1] if img.shape[0] >= 2 else img[0]
                disp, vmin, vmax = _norm_img(img, signed=(cname == "vlass"))
                cmap = "RdBu_r" if cname == "vlass" else "viridis"
                ax.imshow(disp, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
                cy, cx = img.shape[0] // 2, img.shape[1] // 2
                ax.plot([cx], [cy], marker="+", ms=9, color="#00ff88" if cname != "vlass" else "black", mew=1.2)
                if cname == "vlass":
                    snr = float(row["vlass_peak_snr"] or 0.0)
                    txt_c = "#b80000" if snr >= 10 else "#222222"
                    ax.text(0.05, 0.88, f"Peak {snr:.1f}σ", transform=ax.transAxes, fontsize=7.8, fontweight="bold",
                            color=txt_c, bbox=dict(boxstyle="round,pad=0.18", fc="white", alpha=0.85))
            else:
                ax.set_facecolor("#eeeeee")
                ax.text(0.5, 0.5, "South of\nVLASS (-40°)", ha="center", va="center", fontsize=8.2, color="#444444")
            if r_idx == 0:
                ax.set_title(ctitle, fontsize=9.8, fontweight="bold")
            if c_idx == 0:
                ax.set_ylabel(f"Cand {lbl}\nG={row['g_mag']}", fontsize=8.8, fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])

    fig.suptitle("Spor N1A: Multi-Survey FITS Cutout Atlas for Hephaistos A–G (Optical Blends & G 127σ AGN)", fontsize=11.5, fontweight="bold", y=0.996)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    save_both(fig, "figN02_hephaistos_multiband_cutouts.png")


def plot_fig3_n1b_color_and_inj():
    stars = list(csv.DictReader((RESULTS / "N1B_BLIND_ALL_STARS.csv").open(encoding="utf-8")))
    summary = json.loads((RESULTS / "N1_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    heph = list(csv.DictReader((RESULTS / "N1A_HEPHAISTOS_7CANDIDATES.csv").open(encoding="utf-8")))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.0), gridspec_kw={"width_ratios": [1.1, 1.0]})

    bprp = np.array([float(s["bp_rp"]) for s in stars])
    w13 = np.array([float(s["w1_w3"]) for s in stars])
    trig = np.array([s["triggered"] == "True" for s in stars])

    ax1.scatter(bprp[~trig], w13[~trig], s=18, c="#4c78a8", alpha=0.65, label=f"Blind N1B Null Stars (N={int(np.sum(~trig))})")
    ax1.scatter(bprp[trig], w13[trig], s=75, c="#e45756", marker="^", ec="black", lw=0.7, zorder=6, label="N1B Blind Triggers (3 -> 3/3 Gal. Blends)")
    ax1.scatter([float(h["bp_rp"]) for h in heph], [float(h["w1_w3"]) for h in heph], s=70, c="#ffbf00", marker="*", ec="black", lw=0.7, zorder=7, label="Hephaistos A–G Reference")
    ax1.axhline(1.0, color="#c92a2a", ls="--", lw=1.1, label="Dyson Excess Gate (W1 - W3 >= 1.0 mag)")
    ax1.set_xlabel("Gaia DR3 Color BP - RP [mag]")
    ax1.set_ylabel("AllWISE Color W1 - W3 [mag]")
    ax1.set_title("Spor N1B: 260 Parallax-Clean Stars in 3 Rubin DDFs vs Hephaistos A–G")
    ax1.set_ylim(-1.2, 3.8)
    ax1.legend(loc="upper left", fontsize=7.6, framealpha=0.92)

    # Panel 2: Injection completeness heatmap (4 gammas x 3 T_DS)
    grid_data = summary["n1b_blind_dyson"]["injection_grid"]
    gammas = [0.01, 0.05, 0.15, 0.30]
    temps = [150, 300, 500]
    mat = np.array([[grid_data[f"gamma_{g:.2f}_T_{t}K"]["completeness"] * 100.0 for t in temps] for g in gammas])
    ax2.grid(False)
    im = ax2.imshow(mat, cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")
    ax2.set_xticks(np.arange(len(temps)))
    ax2.set_xticklabels([f"{t} K" for t in temps])
    ax2.set_yticks(np.arange(len(gammas)))
    ax2.set_yticklabels([f"γ = {g:.2f}" for g in gammas])
    ax2.set_xlabel("Dyson Sphere Waste-Heat Temperature [K]")
    ax2.set_ylabel("Covering Fraction γ = L_DS / L_tot")
    ax2.set_title("1,200 Synthetic Dyson SED Injection Trials (99.0% for γ >= 0.05)")
    for i in range(len(gammas)):
        for j in range(len(temps)):
            val = mat[i, j]
            ax2.text(j, i, f"{val:.0f}%", ha="center", va="center", fontweight="bold", fontsize=10.5, color="white" if val > 55 else "#111111")
    fig.colorbar(im, ax=ax2, label="Recovery Completeness [%]")

    fig.tight_layout()
    save_both(fig, "figN03_n1b_blind_wise_color_and_injections.png")


def plot_fig4_n1b_vetted():
    import sys
    sys.path.insert(0, str(WS / "scripts"))
    import n1_analyzer as na

    vet = list(csv.DictReader((RESULTS / "N1B_BLIND_DYSON_VETTED.csv").open(encoding="utf-8")))
    fig, axes = plt.subplots(len(vet), 3, figsize=(12.8, 3.8 * len(vet)))
    if len(vet) == 1:
        axes = np.array([axes])
    wgrid = np.geomspace(0.42, 26.0, 200)

    # Load field Gaia/2MASS/WISE for plotting exact SED points
    for r_idx, row in enumerate(vet):
        fn = row["field"]
        gid = row["gaia_source_id"]
        g = next(x for x in na.load_tap_table(INPUTS / "dyson_blind" / f"gaia_{fn}.csv") if x["source_id"] == gid)
        tm = na.load_tap_table(INPUTS / "dyson_blind" / f"twomass_{fn}.csv")
        wise = na.load_tap_table(INPUTS / "dyson_blind" / f"allwise_{fn}.csv")
        gra, gdec = float(g["ra"]), float(g["dec"])
        pmra, pmdec = na.safe_float(g.get("pmra")), na.safe_float(g.get("pmdec"))
        r2, d2 = na.propagate_coords(gra, gdec, pmra, pmdec, 2000.0 - 2016.0)
        rw, dw = na.propagate_coords(gra, gdec, pmra, pmdec, 2010.5 - 2016.0)
        bt = min(tm, key=lambda t: na.angsep_arcsec(r2, d2, float(t["ra"]), float(t["dec"])))
        bw = min(wise, key=lambda w: na.angsep_arcsec(rw, dw, float(w["ra"]), float(w["dec"])))
        _, waves, fluxes, errs = na.build_sed_arrays(g, bt, bw)

        ax_s = axes[r_idx, 0]
        m_s = (10.0 ** float(row["log_om_star_1"])) * na.bnu_jy(wgrid, float(row["t_star_1"]))
        m_d = (10.0 ** float(row["log_om_ds_1"])) * na.bnu_jy(wgrid, float(row["t_ds_k"]))
        ax_s.plot(wgrid, m_s * 1e3, color="#4c78a8", ls="--", lw=1.2, label=f"Star ({float(row['t_star_1']):.0f}K)")
        ax_s.plot(wgrid, (m_s + m_d) * 1e3, color="#111111", lw=1.4, label=f"Total Fit (γ={float(row['gamma']):.3f})")
        ax_s.errorbar(waves, fluxes * 1e3, yerr=errs * 1e3, fmt="o", ms=4.5, color="#e45756", ecolor="#222222", capsize=2)
        ax_s.set_xscale("log")
        ax_s.set_yscale("log")
        ax_s.set_xlabel("Wavelength [µm]")
        ax_s.set_ylabel("Flux [mJy]")
        ax_s.set_title(f"{fn} {gid[:12]}... ({row['dist_pc']} pc)\n{row['ls_tractor_extended_10arcsec']} DR10 Gal., W3ratio={row['max_neighbor_w3_ratio']}x", fontsize=8.4)
        ax_s.legend(loc="lower right", fontsize=7.0)

        for c_idx, (cname, ctitle) in enumerate([("ls_dr10", "Legacy DR10 Optical (33\")"), ("unwise", "unWISE NEO7 (88\")")], start=1):
            ax = axes[r_idx, c_idx]
            ax.grid(False)
            fp = INPUTS / "cutouts" / f"n1b_{gid}_{cname}.fits"
            if fp.exists() and fp.read_bytes()[:6] == b"SIMPLE":
                with fits.open(fp) as hdul:
                    img = next(np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2)
                if img.ndim > 2:
                    img = img[1] if img.shape[0] >= 2 else img[0]
                disp, vmin, vmax = _norm_img(img)
                ax.imshow(disp, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
                cy, cx = img.shape[0] // 2, img.shape[1] // 2
                ax.plot([cx], [cy], marker="+", ms=10, color="#00ff88", mew=1.3)
            ax.set_title(ctitle, fontsize=8.8)
            ax.set_xticks([])
            ax.set_yticks([])

    fig.suptitle("Spor N1B: All 3 Blind Dyson Triggers Resolved as Background Galaxies in WISE PSF", fontsize=11.5, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    save_both(fig, "figN04_n1b_blind_candidates_seds_and_cutouts.png")


def plot_fig5_n1c_vasco():
    vet = list(csv.DictReader((RESULTS / "N1C_VASCO_VETTED.csv").open(encoding="utf-8")))
    summary = json.loads((RESULTS / "N1_STAGE3_VETTING.json").read_text(encoding="utf-8"))

    fig = plt.figure(figsize=(13.2, 7.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.1, 1.0])

    # Top-left (colspan=2): Gaia vs Legacy DR10 + PS1 COSMOS accounting bar
    ax1 = fig.add_subplot(gs[0, :2])
    cats = ["Gaia DR3 Stars\n(3 DDFs, 100% DR10 Match)", "Pan-STARRS1 DR2\n(Real Deblended, 100%)", "PS1 r-Only Ghosts\n(i=-999 Sentinel, Vetted)"]
    vals = [
        summary["n1c_vasco"]["gaia_stars_screened_0p46deg_3ddfs"],
        summary["n1c_vasco"].get("ps1_valid_multiband_or_dss2_screened", 347),
        25,
    ]
    cols = ["#4c78a8", "#54a24b", "#e45756"]
    b = ax1.barh(np.arange(3), vals, color=cols, edgecolor="#222222", lw=0.6)
    ax1.set_yticks(np.arange(3))
    ax1.set_yticklabels(cats)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 1420)
    ax1.set_xlabel("Screened Point Sources (2012–2020 Baseline)")
    ax1.set_title("Spor N1C VASCO Screening: 0 True Disappeared Stars After Cutout Vetting")
    for bar, v in zip(b, vals):
        ax1.text(v + 20, bar.get_y() + bar.get_height() / 2, f"{v}", va="center", fontweight="bold")

    # Top-right (colspan=2): Cutout SNR scatter (LS DR10 vs DSS2 Red for all 27 PS1 triggers)
    ax2 = fig.add_subplot(gs[0, 2:])
    ls_snrs = np.array([max(0.5, float(v["ls_dr10_center_snr"] or 0.5)) for v in vet])
    ds_snrs = np.array([max(0.5, float(v["dss2_center_snr"] or 0.5)) for v in vet])
    real_m = np.array(["PRESENT_IN_DR10" in v["final_disposition"] for v in vet])
    ax2.scatter(ds_snrs[~real_m], ls_snrs[~real_m], s=34, c="#e45756", ec="black", lw=0.5, label=f"PS1 r-Only Ghosts (i=-999, N={int(np.sum(~real_m))})")
    ax2.scatter(ds_snrs[real_m], ls_snrs[real_m], s=75, c="#54a24b", marker="D", ec="black", lw=0.6, label=f"Real Deblended Stars in DR10+DSS2 (N={int(np.sum(real_m))})")
    ax2.axvline(4.5, color="#666666", ls="--", lw=1.0)
    ax2.axhline(5.0, color="#666666", ls="--", lw=1.0)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("DSS2 Red (~1990s) Center Stamp SNR")
    ax2.set_ylabel("Legacy DR10 (~2020) Center Stamp SNR")
    ax2.set_title("All 27 PS1 vs DR10 Candidates: DSS2 vs Legacy DR10 Stamp SNR")
    ax2.legend(loc="upper left", fontsize=7.6)

    # Bottom row: 2 pairs of cutouts (1 Real Deblended Star + 1 PS1 Sentinel Ghost)
    ex_real = next(v for v in vet if "PRESENT_IN_DR10" in v["final_disposition"])
    ex_ghost = next(v for v in vet if "PS1_SENTINEL" in v["final_disposition"])
    panels = [
        (gs[1, 0], f"n1c_{ex_real['source_id']}_dss2.fits", f"Real Star {ex_real['source_id'][:10]}\nDSS2 Red (SNR={ex_real['dss2_center_snr']})"),
        (gs[1, 1], f"n1c_{ex_real['source_id']}_ls_dr10.fits", f"Same Star in Legacy DR10\n(SNR={ex_real['ls_dr10_center_snr']})"),
        (gs[1, 2], f"n1c_{ex_ghost['source_id']}_dss2.fits", f"PS1 Ghost {ex_ghost['source_id'][:10]}\nDSS2 Red (SNR={ex_ghost['dss2_center_snr']}, Absent)"),
        (gs[1, 3], f"n1c_{ex_ghost['source_id']}_ls_dr10.fits", f"Same Pos in Legacy DR10\n(SNR={ex_ghost['ls_dr10_center_snr']}, Absent)"),
    ]
    for loc, fname, ttl in panels:
        ax = fig.add_subplot(loc)
        ax.grid(False)
        fp = INPUTS / "cutouts" / fname
        with fits.open(fp) as hdul:
            img = next(np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2)
        if img.ndim > 2:
            img = img[1] if img.shape[0] >= 2 else img[0]
        disp, vmin, vmax = _norm_img(img)
        ax.imshow(disp, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
        cy, cx = img.shape[0] // 2, img.shape[1] // 2
        ax.plot([cx], [cy], marker="+", ms=9, color="#00ff88", mew=1.2)
        ax.set_title(ttl, fontsize=8.3)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.tight_layout()
    save_both(fig, "figN05_n1c_vasco_gaia_ps1_legacy_comparison.png")


def plot_fig6_bayesian_bounds():
    summary = json.loads((RESULTS / "N1_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    b_n1b = summary["n1b_blind_dyson"]["bounds_all_clean_gamma_ge_0p05"]
    b_gaia = summary["n1c_vasco"]["bounds_gaia_vanishing"]
    b_ps1_valid = summary["n1c_vasco"].get("bounds_ps1_valid_multiband_vanishing", summary["n1c_vasco"]["bounds_ps1_vanishing"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.8), gridspec_kw={"width_ratios": [1.0, 1.15]})

    # Left: Disposition breakdown across N1A (7) + N1B (3) + N1C (27)
    labels = [
        "N1A Hephaistos\n(N=7)",
        "N1B Blind Triggers\n(N=3 of 260)",
        "N1C Gaia Vanishing\n(N=1,197)",
        "N1C PS1 Flagged\n(N=27 of 372)",
    ]
    astro_blend = [6, 3, 0, 2]     # Blends / Radio AGN / Real DR10 deblended stars
    artifact = [0, 0, 0, 25]       # PS1 sentinel r-only ghosts absent in DSS2/DR10
    unresolved_opt = [1, 0, 0, 0]  # Hephaistos A needs JWST/ALMA
    y = np.arange(len(labels))
    ax1.barh(y, astro_blend, color="#4c78a8", label="Resolved Gal. Blend / Radio AGN / Bright Halo")
    ax1.barh(y, artifact, left=astro_blend, color="#e45756", label="PS1 Sentinel r-Only Ghost (Absent in DSS2)")
    left2 = np.array(astro_blend) + np.array(artifact)
    ax1.barh(y, unresolved_opt, left=left2, color="#f58518", label="Unblended in DR10 (Cand. A; 2.56σ VLASS)")
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 34)
    ax1.set_xlabel("Candidate / Trigger Count")
    ax1.set_title("Multi-Pillar Candidate Disposition Accounting (0 Verified ETI)")
    ax1.legend(loc="upper right", fontsize=7.5, framealpha=0.93)

    # Right: Exact Analytical Bayesian f95
    regimes = [
        (f"N1C VASCO Gaia DR3→DR10\n(N={b_gaia['n_eval']}, 0 Vanished)", b_gaia),
        (f"N1C VASCO PS1→DR10 Valid\n(N={b_ps1_valid['n_eval']}, 0 Vanished)", b_ps1_valid),
        (f"N1B Blind Dyson (γ >= 0.05)\n(N={b_n1b['n_eval']}, N_eff={b_n1b['n_eff']:.1f})", b_n1b),
    ]
    yr = np.arange(len(regimes))
    jeff = [r[1]["jeffreys_f95_pct"] for r in regimes]
    unif = [r[1]["uniform_f95_pct"] for r in regimes]
    cp = [r[1]["clopper_pearson_f95_pct"] for r in regimes]
    w = 0.25
    ax2.barh(yr - w, jeff, height=w, color="#4c78a8", label="Jeffreys Beta(0.5, N_eff+0.5)")
    ax2.barh(yr, unif, height=w, color="#f58518", label="Uniform Beta(1, N_eff+1)")
    ax2.barh(yr + w, cp, height=w, color="#54a24b", label="Clopper-Pearson")
    ax2.set_yticks(yr)
    ax2.set_yticklabels([r[0] for r in regimes])
    ax2.invert_yaxis()
    ax2.set_xlim(0, 1.55)
    ax2.set_xlabel("Bayesian 95% Prevalence Upper Limit f95 [%] (0 Verified ETI)")
    ax2.set_title("Spor N1 Dyson-Sphere & Vanishing-Star Null Bounds")
    for i, (jv, uv) in enumerate(zip(jeff, unif)):
        ax2.text(jv + 0.025, i - w, f"{jv:.3f}%", va="center", fontsize=8.0, fontweight="bold", color="#23456b")
        ax2.text(uv + 0.025, i, f"{uv:.3f}%", va="center", fontsize=8.0, color="#a85506")
    ax2.legend(loc="upper right", fontsize=7.8, framealpha=0.93)

    fig.tight_layout()
    save_both(fig, "figN06_n1_unified_bayesian_bounds.png")


def main() -> int:
    plot_fig1_heph_seds()
    plot_fig2_heph_cutouts()
    plot_fig3_n1b_color_and_inj()
    plot_fig4_n1b_vetted()
    plot_fig5_n1c_vasco()
    plot_fig6_bayesian_bounds()
    print("Generated all 6 Spor N1 300-DPI figures (figN01-figN06).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
