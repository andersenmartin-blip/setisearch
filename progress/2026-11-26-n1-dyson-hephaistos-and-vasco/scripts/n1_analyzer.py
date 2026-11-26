#!/usr/bin/env python3
"""
Locked Spor N1 Physical Analysis Engine:
  - N1A: Multi-wavelength blackbody SED + Partial Dyson Sphere fitting and
         multi-survey deblending / VLASS 3 GHz radio / Rubin vetting of the
         7 Project Hephaistos II candidates (A-G; Suazo et al. 2024).
  - N1B: Blind Gaia DR3 + 2MASS + AllWISE Dyson-sphere search across 3 Rubin DDFs
         (COSMOS, EDFS_B, ELAIS_S1) with 1,200 synthetic SED injection trials
         and exact analytical Bayesian f95 bounds.
  - N1C: Multi-decade VASCO vanishing & extreme-dimming screen comparing
         Gaia DR3 (J2016->2020) + Pan-STARRS1 DR2 (~2012) vs DESI Legacy DR10 (~2020)
         and Rubin/Fink 2026.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
from scipy.optimize import least_squares
from scipy.stats import beta as scipy_beta

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n1_20261126_dyson_hephaistos_and_vasco")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n1_20261126")
RESULTS = WS / "results"

H_PLANCK = 6.62607015e-34
C_LIGHT = 2.99792458e8
K_BOLTZ = 1.380649e-23

# Effective wavelengths (um) and Vega flux zero-points (Jy)
BAND_INFO: dict[str, tuple[float, float]] = {
    "BP": (0.5036, 3552.01),
    "G": (0.6218, 3228.75),
    "RP": (0.7769, 2554.95),
    "J": (1.235, 1594.0),
    "H": (1.662, 1024.0),
    "K": (2.159, 666.7),
    "W1": (3.3526, 309.54),
    "W2": (4.6028, 171.787),
    "W3": (11.5608, 31.674),
    "W4": (22.0883, 8.363),
}

HEPHAISTOS_7 = [
    ("A", "3496509309189181184"),
    ("B", "4843191593270342656"),
    ("C", "4649396037451459712"),
    ("D", "2660349163149053824"),
    ("E", "3190232820489766656"),
    ("F", "2956570141274256512"),
    ("G", "2644370304260053376"),
]

DDFS = [
    ("COSMOS", 150.1190, 2.2058),
    ("EDFS_B", 63.6000, -48.0000),
    ("ELAIS_S1", 9.4500, -44.0000),
]


def safe_float(val: Any) -> float | None:
    if val is None or val == "" or str(val).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(val)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def propagate_coords(ra_deg: float, dec_deg: float, pmra_masyr: float | None, pmdec_masyr: float | None, dt_years: float) -> tuple[float, float]:
    pmra = pmra_masyr or 0.0
    pmdec = pmdec_masyr or 0.0
    cos_d = max(0.05, math.cos(math.radians(dec_deg)))
    return (ra_deg + (pmra * dt_years) / (3600000.0 * cos_d), dec_deg + (pmdec * dt_years) / 3600000.0)


def load_tap_table(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    txt = raw.decode("utf-8", errors="replace").lstrip()
    if txt.startswith("<"):
        tab = parse_single_table(io.BytesIO(raw))
        cols = tab.colnames
        rows: list[dict[str, str]] = []
        for rec in tab.array:
            d = {}
            for c in cols:
                v = rec[c]
                if isinstance(v, (bytes, np.bytes_)):
                    v = v.decode("utf-8", errors="replace")
                elif np.ma.is_masked(v):
                    v = ""
                d[str(c)] = str(v)
            rows.append(d)
        return rows
    return list(csv.DictReader(io.StringIO(txt)))


def bnu_jy(wave_um: np.ndarray, t_k: float) -> np.ndarray:
    """Planck B_nu in Jy / sr = W m^-2 Hz^-1 sr^-1 * 1e26."""
    nu = C_LIGHT / (wave_um * 1e-6)
    x = np.clip((H_PLANCK * nu) / (K_BOLTZ * t_k), 1e-6, 700.0)
    b_si = (2.0 * H_PLANCK * (nu ** 3) / (C_LIGHT ** 2)) / np.expm1(x)
    return b_si * 1e26


def mag_to_jy_err(band: str, mag: float, mag_err: float | None, sys_frac: float = 0.05) -> tuple[float, float]:
    _, f0 = BAND_INFO[band]
    flux = f0 * (10.0 ** (-0.4 * mag))
    me = mag_err if (mag_err is not None and mag_err > 0) else 0.03
    stat_err = 0.921034 * flux * me
    tot_err = math.hypot(stat_err, sys_frac * flux)
    return flux, tot_err


def build_sed_arrays(row_g: dict[str, Any], row_2m: dict[str, Any] | None, row_w: dict[str, Any] | None) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    bands: list[str] = []
    waves: list[float] = []
    fluxes: list[float] = []
    errs: list[float] = []

    def add(b: str, m: float | None, me: float | None):
        if m is None:
            return
        w, _ = BAND_INFO[b]
        f, e = mag_to_jy_err(b, m, me, sys_frac=0.05)
        bands.append(b)
        waves.append(w)
        fluxes.append(f)
        errs.append(e)

    # Gaia DR3 optical (phot_g_mean_flux_over_error -> sigma_m ~ 1.0857 / SNR)
    gmag = safe_float(row_g.get("phot_g_mean_mag"))
    bpmag = safe_float(row_g.get("phot_bp_mean_mag"))
    rpmag = safe_float(row_g.get("phot_rp_mean_mag"))
    add("BP", bpmag, 0.02)
    add("G", gmag, 0.02)
    add("RP", rpmag, 0.02)

    if row_2m:
        add("J", safe_float(row_2m.get("j_m")), safe_float(row_2m.get("j_msigcom")))
        add("H", safe_float(row_2m.get("h_m")), safe_float(row_2m.get("h_msigcom")))
        add("K", safe_float(row_2m.get("k_m")), safe_float(row_2m.get("k_msigcom")))

    if row_w:
        w1 = safe_float(row_w.get("w1mpro"))
        w1e = safe_float(row_w.get("w1sigmpro"))
        w2 = safe_float(row_w.get("w2mpro"))
        w2e = safe_float(row_w.get("w2sigmpro"))
        w3 = safe_float(row_w.get("w3mpro"))
        w3e = safe_float(row_w.get("w3sigmpro"))
        w3snr = safe_float(row_w.get("w3snr")) or 0.0
        w4 = safe_float(row_w.get("w4mpro"))
        w4e = safe_float(row_w.get("w4sigmpro"))
        w4snr = safe_float(row_w.get("w4snr")) or 0.0
        add("W1", w1, w1e)
        add("W2", w2, w2e)
        if w3 is not None and w3snr >= 2.0:
            add("W3", w3, w3e)
        if w4 is not None and w4snr >= 3.0:
            add("W4", w4, w4e)

    return bands, np.array(waves, dtype=float), np.array(fluxes, dtype=float), np.array(errs, dtype=float)


def fit_blackbody_dyson(waves: np.ndarray, fluxes: np.ndarray, errs: np.ndarray, t_init: float = 3500.0) -> dict[str, Any]:
    """Fit Model 0 (single stellar BB) and Model 1 (stellar BB + Dyson Sphere BB)."""
    # Use optical + NIR (wave <= 5 um) scale estimate for initial stellar Omega
    opt_idx = int(np.argmin(np.abs(waves - 1.235)))
    b_init = float(bnu_jy(np.array([waves[opt_idx]]), t_init)[0])
    log_om0 = math.log10(max(1e-30, fluxes[opt_idx] / max(1e-30, b_init)))

    def res0(p):
        t_s, log_om = p
        mod = (10.0 ** log_om) * bnu_jy(waves, t_s)
        return (fluxes - mod) / errs

    fit0 = least_squares(res0, x0=[t_init, log_om0], bounds=([2300.0, -35.0], [10000.0, -10.0]), max_nfev=150)
    chi2_0 = float(np.sum(fit0.fun ** 2))
    t_s0, log_om_s0 = float(fit0.x[0]), float(fit0.x[1])

    def res1(p):
        t_s, log_om_s, t_d, log_om_d = p
        mod = (10.0 ** log_om_s) * bnu_jy(waves, t_s) + (10.0 ** log_om_d) * bnu_jy(waves, t_d)
        return (fluxes - mod) / errs

    best_fit1 = None
    best_chi2_1 = 1e30
    for td0 in (220.0, 380.0):
        b_ir = float(bnu_jy(np.array([11.5608]), td0)[0])
        om_ir0 = math.log10(max(1e-26, fluxes[-1] * 0.5 / max(1e-30, b_ir)))
        om_ir0 = min(-8.0, max(-30.0, om_ir0))
        f1 = least_squares(res1, x0=[t_s0, log_om_s0, td0, om_ir0], bounds=([2300.0, -35.0, 100.0, -30.0], [10000.0, -10.0, 700.0, -8.0]), max_nfev=250)
        c1 = float(np.sum(f1.fun ** 2))
        if c1 < best_chi2_1:
            best_chi2_1 = c1
            best_fit1 = f1

    t_s1, log_om_s1, t_ds, log_om_ds = [float(x) for x in best_fit1.x]
    # Luminosity covering fraction gamma = L_ds / (L_star + L_ds)
    l_star = (10.0 ** log_om_s1) * (t_s1 ** 4)
    l_ds = (10.0 ** log_om_ds) * (t_ds ** 4)
    gamma = float(l_ds / max(1e-60, l_star + l_ds))
    delta_chi2 = max(0.0, chi2_0 - best_chi2_1)
    # Fractional excess at W3 (~11.56 um) relative to single photosphere Model 0
    mod0_vals = (10.0 ** log_om_s0) * bnu_jy(waves, t_s0)
    w3_idx = [i for i, w in enumerate(waves) if 9.0 <= w <= 14.0]
    w3_excess_ratio = float(fluxes[w3_idx[0]] / max(1e-20, mod0_vals[w3_idx[0]])) if w3_idx else float("nan")

    return {
        "n_bands": int(len(waves)),
        "t_star_0": round(t_s0, 1),
        "chi2_0": round(chi2_0, 3),
        "t_star_1": round(t_s1, 1),
        "log_om_star_1": round(log_om_s1, 4),
        "t_ds_k": round(t_ds, 1),
        "log_om_ds_1": round(log_om_ds, 4),
        "chi2_1": round(best_chi2_1, 3),
        "delta_chi2": round(delta_chi2, 3),
        "gamma": round(gamma, 5),
        "w3_excess_ratio": round(w3_excess_ratio, 3) if math.isfinite(w3_excess_ratio) else None,
    }


def vlass_peak_snr(fits_path: Path) -> dict[str, Any]:
    if not fits_path.exists():
        return {"vlass_covered": False, "vlass_peak_snr": None, "vlass_peak_mjy": None}
    raw = fits_path.read_bytes()
    if raw[:6] != b"SIMPLE":
        return {"vlass_covered": False, "vlass_peak_snr": None, "vlass_peak_mjy": None}
    with fits.open(io.BytesIO(raw)) as hdul:
        img = next((np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2), None)
    if img is None:
        return {"vlass_covered": False, "vlass_peak_snr": None, "vlass_peak_mjy": None}
    if img.ndim > 2:
        img = img.reshape((-1, img.shape[-2], img.shape[-1]))[0]
    fin = img[np.isfinite(img)]
    if len(fin) < 25 or float(np.std(fin)) == 0.0:
        return {"vlass_covered": False, "vlass_peak_snr": None, "vlass_peak_mjy": None}
    h, w = img.shape
    cy, cx = h // 2, w // 2
    med = float(np.median(fin))
    mad = max(1e-12, 1.4826 * float(np.median(np.abs(fin - med))))
    # Search inner 21x21 px (~21"x21" at 1"/px -> radius ~10") for radio peak
    y0, y1 = max(0, cy - 10), min(h, cy + 11)
    x0, x1 = max(0, cx - 10), min(w, cx + 11)
    sub = np.where(np.isfinite(img[y0:y1, x0:x1]), img[y0:y1, x0:x1] - med, 0.0)
    iy, ix = np.unravel_index(int(np.argmax(sub)), sub.shape)
    peak_jy = float(sub[iy, ix])
    offset_px = float(math.hypot((x0 + ix) - cx, (y0 + iy) - cy))
    return {
        "vlass_covered": True,
        "vlass_peak_snr": round(peak_jy / mad, 2),
        "vlass_peak_mjy": round(peak_jy * 1e3, 3),
        "vlass_offset_arcsec": round(offset_px * 1.0, 2),
    }


def optical_fits_detection(fits_path: Path) -> dict[str, Any]:
    if not fits_path.exists():
        return {"valid": False, "center_snr": None}
    raw = fits_path.read_bytes()
    if raw[:6] != b"SIMPLE":
        return {"valid": False, "center_snr": None}
    with fits.open(io.BytesIO(raw)) as hdul:
        img = next((np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2), None)
    if img is None:
        return {"valid": False, "center_snr": None}
    if img.ndim > 2:
        # Take r or mean of g/r/i/z slices
        img = np.nanmean(img.reshape((-1, img.shape[-2], img.shape[-1])), axis=0)
    fin = img[np.isfinite(img)]
    if len(fin) < 25:
        return {"valid": False, "center_snr": None}
    med = float(np.median(fin))
    mad = max(1e-12, 1.4826 * float(np.median(np.abs(fin - med))))
    h, w = img.shape
    cy, cx = h // 2, w // 2
    box = img[max(0, cy - 3):min(h, cy + 4), max(0, cx - 3):min(w, cx + 4)] - med
    peak = float(np.nanmax(box)) if np.any(np.isfinite(box)) else 0.0
    return {"valid": True, "center_snr": round(peak / mad, 2)}


def bayesian_bounds(n_eval: int, n_eff: float, k: int = 0) -> dict[str, Any]:
    if n_eff <= 0:
        return {"n_eval": int(n_eval), "n_eff": 0.0, "uniform_f95_pct": 100.0, "jeffreys_f95_pct": 100.0, "clopper_pearson_f95_pct": 100.0}
    u95 = float(scipy_beta.ppf(0.95, k + 1.0, n_eff + 1.0)) * 100.0
    j95 = float(scipy_beta.ppf(0.95, k + 0.5, n_eff + 0.5)) * 100.0
    cp95 = (1.0 - 0.05 ** (1.0 / max(1.0, n_eff))) * 100.0
    return {
        "n_eval": int(n_eval),
        "n_eff": round(float(n_eff), 3),
        "uniform_f95_pct": round(u95, 4),
        "jeffreys_f95_pct": round(j95, 4),
        "clopper_pearson_f95_pct": round(cp95, 4),
    }


def analyze_n1a_hephaistos() -> list[dict[str, Any]]:
    gaia_rows = {r["source_id"]: r for r in load_tap_table(INPUTS / "hephaistos" / "hephaistos_gaia.csv")}
    tm_rows = load_tap_table(INPUTS / "hephaistos" / "hephaistos_2mass.csv")
    wise_rows = load_tap_table(INPUTS / "hephaistos" / "hephaistos_allwise.csv")
    ls_rows = load_tap_table(INPUTS / "hephaistos" / "hephaistos_ls_dr10.csv")
    fink_data = json.loads((INPUTS / "hephaistos" / "hephaistos_fink_matches.json").read_text(encoding="utf-8"), parse_int=str)
    simbad_data = json.loads((INPUTS / "hephaistos" / "hephaistos_simbad.json").read_text(encoding="utf-8"))

    out_rows = []
    for label, gid in HEPHAISTOS_7:
        g = gaia_rows[gid]
        gra, gdec = float(g["ra"]), float(g["dec"])
        pmra, pmdec = safe_float(g.get("pmra")), safe_float(g.get("pmdec"))
        plx = safe_float(g.get("parallax")) or 0.0
        dist_pc = round(1000.0 / plx, 2) if plx > 0 else None

        # Best 2MASS (epoch ~2000.0) & AllWISE (epoch ~2010.5) match around propagated Gaia position
        ra_2m, dec_2m = propagate_coords(gra, gdec, pmra, pmdec, 2000.0 - 2016.0)
        best_2m = None
        best_2m_sep = 99.0
        for t in tm_rows:
            sep = angsep_arcsec(ra_2m, dec_2m, float(t["ra"]), float(t["dec"]))
            if sep <= 4.0 and sep < best_2m_sep:
                best_2m_sep = sep
                best_2m = t

        ra_w, dec_w = propagate_coords(gra, gdec, pmra, pmdec, 2010.5 - 2016.0)
        best_w = None
        best_w_sep = 99.0
        for w in wise_rows:
            sep = angsep_arcsec(ra_w, dec_w, float(w["ra"]), float(w["dec"]))
            if sep <= 5.0 and sep < best_w_sep:
                best_w_sep = sep
                best_w = w

        bands, waves, fluxes, errs = build_sed_arrays(g, best_2m, best_w)
        fit = fit_blackbody_dyson(waves, fluxes, errs, t_init=3200.0)

        w1 = safe_float(best_w.get("w1mpro")) if best_w else None
        w2 = safe_float(best_w.get("w2mpro")) if best_w else None
        w3 = safe_float(best_w.get("w3mpro")) if best_w else None
        w4 = safe_float(best_w.get("w4mpro")) if best_w else None
        w1_w3 = round(w1 - w3, 3) if (w1 is not None and w3 is not None) else None
        w1_w4 = round(w1 - w4, 3) if (w1 is not None and w4 is not None) else None
        w3snr = safe_float(best_w.get("w3snr")) if best_w else None
        w4snr = safe_float(best_w.get("w4snr")) if best_w else None

        # Legacy DR10 optical neighbors within 8" (WISE W3 PSF FWHM = 6.5")
        ra_ls, dec_ls = propagate_coords(gra, gdec, pmra, pmdec, 2020.0 - 2016.0)
        ls_near = []
        ls_galaxies_6p5 = 0
        ls_other_8 = 0
        for lrow in ls_rows:
            sep_l = angsep_arcsec(ra_ls, dec_ls, float(lrow["ra"]), float(lrow["dec"]))
            if sep_l <= 8.0:
                ltype = str(lrow.get("type") or "").strip()
                ls_near.append((sep_l, ltype, safe_float(lrow.get("flux_r")), safe_float(lrow.get("flux_w3"))))
                if sep_l > 1.2:
                    ls_other_8 += 1
                    if ltype and ltype != "PSF":
                        ls_galaxies_6p5 += 1

        vlass = vlass_peak_snr(INPUTS / "cutouts" / f"heph_{label}_vlass.fits")
        ls_cut_opt = optical_fits_detection(INPUTS / "cutouts" / f"heph_{label}_ls_dr10.fits")
        fink_hits = fink_data.get(label, [])
        sim_hits = simbad_data.get(label, [])

        # Disposition assignment (purely data-driven from retrieved radio + LS DR10 + SED)
        has_radio_agn = (vlass.get("vlass_peak_snr") or 0.0) >= 4.5
        has_ext_blend = (ls_galaxies_6p5 >= 1) or (ls_other_8 >= 2 and (best_w_sep > 0.45))
        if has_radio_agn and has_ext_blend:
            disp = "RADIO_AGN_AND_GALAXY_BLEND_IN_WISE_PSF"
        elif has_radio_agn:
            disp = "RADIO_AGN_OR_HOT_DOG_CONTAMINANT"
        elif has_ext_blend:
            disp = "EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF"
        elif ls_other_8 >= 1:
            disp = "NEARBY_FAINT_NEIGHBOR_IN_WISE_PSF"
        else:
            disp = "UNBLENDED_IN_DR10_NEEDS_JWST_OR_ALMA"

        out_rows.append({
            "label": label,
            "gaia_source_id": gid,
            "ra_deg": round(gra, 6),
            "dec_deg": round(gdec, 6),
            "dist_pc": dist_pc,
            "g_mag": round(safe_float(g.get("phot_g_mean_mag")) or 0.0, 3),
            "bp_rp": round(safe_float(g.get("bp_rp")) or 0.0, 3),
            "wise_designation": best_w.get("designation", "") if best_w else "",
            "wise_sep_arcsec": round(best_w_sep, 3) if best_w else None,
            "w1": w1, "w2": w2, "w3": w3, "w4": w4,
            "w3snr": w3snr, "w4snr": w4snr,
            "w1_w3": w1_w3, "w1_w4": w1_w4,
            "ls_neighbors_1p2_to_8arcsec": ls_other_8,
            "ls_extended_galaxies_le8arcsec": ls_galaxies_6p5,
            "vlass_covered": vlass["vlass_covered"],
            "vlass_peak_snr": vlass["vlass_peak_snr"],
            "vlass_peak_mjy": vlass["vlass_peak_mjy"],
            "vlass_offset_arcsec": vlass.get("vlass_offset_arcsec"),
            "fink_lsst_alerts": len(fink_hits),
            "simbad_types": ";".join(h.get("otype", "") for h in sim_hits),
            **fit,
            "disposition": disp,
        })
    return out_rows


def build_grid(rows: list[dict[str, str]], ra_key: str = "ra", dec_key: str = "dec", step_deg: float = 0.01) -> dict[tuple[int, int], list[dict[str, str]]]:
    grid: dict[tuple[int, int], list[dict[str, str]]] = collections.defaultdict(list)
    inv = 1.0 / step_deg
    for r in rows:
        ra = safe_float(r.get(ra_key))
        dec = safe_float(r.get(dec_key))
        if ra is None or dec is None:
            continue
        grid[(int(math.floor(ra * inv)), int(math.floor(dec * inv)))].append(r)
    return grid


def query_grid(grid: dict[tuple[int, int], list[dict[str, str]]], ra0: float, dec0: float, max_arcsec: float, step_deg: float = 0.01) -> list[tuple[float, dict[str, str]]]:
    inv = 1.0 / step_deg
    cx, cy = int(math.floor(ra0 * inv)), int(math.floor(dec0 * inv))
    hits = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for row in grid.get((cx + dx, cy + dy), ()):
                sep = angsep_arcsec(ra0, dec0, float(row["ra"]), float(row["dec"]))
                if sep <= max_arcsec:
                    hits.append((sep, row))
    hits.sort(key=lambda x: x[0])
    return hits


def analyze_n1b_and_n1c() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    blind_stars: list[dict[str, Any]] = []
    blind_seps: list[tuple[dict[str, Any], list[str], np.ndarray, np.ndarray, np.ndarray]] = []
    blind_triggers: list[dict[str, Any]] = []

    vasco_gaia_total = 0
    vasco_gaia_matched_ls = 0
    vasco_candidates: list[dict[str, Any]] = []

    vasco_bounds_p = INPUTS / "vasco" / "ls_dr10_brick_bounds.json"
    brick_bounds = json.loads(vasco_bounds_p.read_text(encoding="utf-8")) if vasco_bounds_p.exists() else {}

    def in_brick_interior(ra_q: float, dec_q: float, b_list: list[list[float]], margin_deg: float = 0.005) -> bool:
        return any((b[0] + margin_deg) <= ra_q <= (b[1] - margin_deg) and (b[2] + margin_deg) <= dec_q <= (b[3] - margin_deg) for b in b_list)

    for fname, ra0, dec0 in DDFS:
        gaia = load_tap_table(INPUTS / "dyson_blind" / f"gaia_{fname}.csv")
        tm = load_tap_table(INPUTS / "dyson_blind" / f"twomass_{fname}.csv")
        wise = load_tap_table(INPUTS / "dyson_blind" / f"allwise_{fname}.csv")
        ls = load_tap_table(INPUTS / "dyson_blind" / f"ls_dr10_{fname}.csv")
        b_list = brick_bounds.get(fname, [])

        grid_tm = build_grid(tm)
        grid_w = build_grid(wise)
        grid_ls = build_grid(ls)
        # Also build a grid of ALL Gaia sources so we reject blended WISE stars cleanly
        grid_gaia = build_grid(gaia)

        for g in gaia:
            gra = safe_float(g.get("ra"))
            gdec = safe_float(g.get("dec"))
            gmag = safe_float(g.get("phot_g_mean_mag"))
            ruwe = safe_float(g.get("ruwe"))
            plx = safe_float(g.get("parallax")) or 0.0
            plx_snr = safe_float(g.get("parallax_over_error")) or 0.0
            pstar = safe_float(g.get("classprob_dsc_combmod_star")) or 0.0
            dup = str(g.get("duplicated_source") or "").strip().lower() in ("true", "1")
            pmra, pmdec = safe_float(g.get("pmra")), safe_float(g.get("pmdec"))
            solved = int(safe_float(g.get("astrometric_params_solved")) or 0)
            nobs = int(safe_float(g.get("phot_g_n_obs")) or 0)
            if gra is None or gdec is None or gmag is None or ruwe is None:
                continue

            # Check Gaia distance from DDF center <= 0.46 deg so WISE 0.52 deg cone avoids edge clipping!
            if angsep_arcsec(gra, gdec, ra0, dec0) > 0.46 * 3600.0:
                continue

            # Pillar N1C: Clean Gaia DR3 stellar sample strictly inside downloaded LS DR10 brick interior!
            ra_ls, dec_ls = propagate_coords(gra, gdec, pmra, pmdec, 2020.0 - 2016.0)
            if 16.0 <= gmag <= 20.5 and ruwe < 1.4 and not dup and solved >= 31 and nobs >= 50 and pstar >= 0.90 and in_brick_interior(ra_ls, dec_ls, b_list):
                vasco_gaia_total += 1
                ls_hits = query_grid(grid_ls, ra_ls, dec_ls, 3.0)
                if not ls_hits:
                    vasco_candidates.append({
                        "channel": "GAIA_VS_LS_DR10_MISSING",
                        "field": fname,
                        "source_id": g["source_id"],
                        "ra_deg": round(ra_ls, 7),
                        "dec_deg": round(dec_ls, 7),
                        "g_mag": round(gmag, 3),
                        "rp_mag": round(safe_float(g.get("phot_rp_mean_mag")) or gmag, 3),
                        "pm_masyr": round(math.hypot(pmra or 0.0, pmdec or 0.0), 2),
                        "ls_flux_r": None,
                        "ls_mag_r": None,
                        "ls_mag_z": None,
                        "delta_mag": None,
                        "ls_maskbits": "",
                        "prelim_reason": "NO_LS_DR10_MATCH_3ARCSEC",
                    })
                else:
                    vasco_gaia_matched_ls += 1
                    _, l0 = ls_hits[0]
                    fg = safe_float(l0.get("flux_g")) or 0.0
                    fr = safe_float(l0.get("flux_r")) or 0.0
                    fz = safe_float(l0.get("flux_z")) or 0.0
                    mr = 22.5 - 2.5 * math.log10(fr) if fr > 0 else 28.0
                    mz = 22.5 - 2.5 * math.log10(fz) if fz > 0 else 28.0
                    rpm = safe_float(g.get("phot_rp_mean_mag")) or gmag
                    # Check extreme dimming across BOTH optical & red bands (>= 1.5 mag dimmer in both r vs G and z vs RP)
                    if (mr - gmag >= 1.5) and (mz - rpm >= 1.5) and fr >= 0 and (int(safe_float(l0.get("maskbits")) or 0) == 0):
                        vasco_candidates.append({
                            "channel": "GAIA_VS_LS_DR10_EXTREME_DIM",
                            "field": fname,
                            "source_id": g["source_id"],
                            "ra_deg": round(ra_ls, 7),
                            "dec_deg": round(dec_ls, 7),
                            "g_mag": round(gmag, 3),
                            "rp_mag": round(rpm, 3),
                            "pm_masyr": round(math.hypot(pmra or 0.0, pmdec or 0.0), 2),
                            "ls_flux_r": round(fr, 3),
                            "ls_mag_r": round(mr, 3),
                            "ls_mag_z": round(mz, 3),
                            "delta_mag": round(min(mr - gmag, mz - rpm), 3),
                            "ls_maskbits": l0.get("maskbits", ""),
                            "prelim_reason": "DIM_IN_BOTH_R_AND_Z",
                        })

            # Pillar N1B: Clean nearby parallax-verified stars for Dyson sphere SED search
            if plx <= 0 or plx_snr < 5.0 or (1000.0 / plx) > 1000.0 or ruwe >= 1.4 or dup or pstar < 0.90:
                continue
            ra_2m, dec_2m = propagate_coords(gra, gdec, pmra, pmdec, 2000.0 - 2016.0)
            ra_w, dec_w = propagate_coords(gra, gdec, pmra, pmdec, 2010.5 - 2016.0)
            tm_hits = query_grid(grid_tm, ra_2m, dec_2m, 2.0)
            w_hits = query_grid(grid_w, ra_w, dec_w, 2.0)
            if not tm_hits or not w_hits:
                continue
            trow = tm_hits[0][1]
            wrow = w_hits[0][1]
            if str(wrow.get("cc_flags") or "") != "0000" or int(safe_float(wrow.get("ext_flg")) or 0) != 0:
                continue
            w3snr = safe_float(wrow.get("w3snr")) or 0.0
            w4snr = safe_float(wrow.get("w4snr")) or 0.0
            # Include all clean parallax stars with W1/W2 and check both W3>=3 and strict W3>=5
            w1 = safe_float(wrow.get("w1mpro"))
            w2 = safe_float(wrow.get("w2mpro"))
            w3 = safe_float(wrow.get("w3mpro"))
            w4 = safe_float(wrow.get("w4mpro"))
            if w1 is None or w2 is None or w3 is None or w3snr < 3.0:
                continue
            # Require no brighter Gaia neighbor within 6" to protect WISE PSF
            g_neib = query_grid(grid_gaia, gra, gdec, 6.0)
            if any(sg > 0.2 and (safe_float(ng.get("phot_g_mean_mag")) or 99.0) < gmag + 1.5 for sg, ng in g_neib):
                continue

            bands, waves, fluxes, errs = build_sed_arrays(g, trow, wrow)
            fit = fit_blackbody_dyson(waves, fluxes, errs, t_init=4000.0)
            w1_w3 = round(w1 - w3, 4)
            w1_w4 = round(w1 - w4, 4) if (w4 is not None and w4snr >= 3.0) else None
            trig = ((w1_w3 >= 1.0) or (w1_w4 is not None and w1_w4 >= 2.5 and w4snr >= 5.0)) and (fit["gamma"] >= 0.02) and (fit["delta_chi2"] >= 25.0)
            ra_ls, dec_ls = propagate_coords(gra, gdec, pmra, pmdec, 2020.0 - 2016.0)
            ls_around = query_grid(grid_ls, ra_ls, dec_ls, 6.5)
            ls_ext = sum(1 for sp, lr in ls_around if sp > 1.2 and str(lr.get("type") or "").strip() not in ("", "PSF"))
            rec = {
                "field": fname,
                "gaia_source_id": g["source_id"],
                "wise_designation": wrow.get("designation", ""),
                "ra_deg": round(gra, 6),
                "dec_deg": round(gdec, 6),
                "dist_pc": round(1000.0 / plx, 2),
                "g_mag": round(gmag, 3),
                "bp_rp": round(safe_float(g.get("bp_rp")) or 0.0, 3),
                "w1": w1, "w2": w2, "w3": w3, "w4": w4,
                "w3snr": w3snr, "w4snr": w4snr,
                "w1_w3": w1_w3, "w1_w4": w1_w4,
                "ls_neighbors_le6p5": max(0, len(ls_around) - 1),
                "ls_extended_le6p5": ls_ext,
                "triggered": trig,
                **fit,
            }
            blind_stars.append(rec)
            blind_seps.append((rec, bands, waves, fluxes, errs))
            if trig:
                blind_triggers.append(rec)

    # Synthetic injection-recovery on N1B clean stars (4 gammas x 3 T_DS x 100 = 1,200 trials)
    rng = np.random.default_rng(20261126)
    gammas = (0.01, 0.05, 0.15, 0.30)
    tds_list = (150.0, 300.0, 500.0)
    inj_grid = {}
    tot_rec = 0
    tot_trials = 0
    if blind_seps:
        for gam in gammas:
            for tds in tds_list:
                rec_cnt = 0
                for _ in range(100):
                    idx = int(rng.integers(0, len(blind_seps)))
                    srec, sbands, sw, sf, se = blind_seps[idx]
                    # Synthesize Dyson excess around Model 0 star: L_ds / L_star = gam / (1 - gam)
                    t_st = srec["t_star_0"]
                    b_s = bnu_jy(sw, t_st)
                    # Estimate om_star from optical bands
                    om_st = float(np.median(sf[:3] / np.maximum(1e-30, b_s[:3])))
                    om_ds = om_st * (gam / max(1e-6, 1.0 - gam)) * ((t_st / tds) ** 4)
                    added_jy = om_ds * bnu_jy(sw, tds)
                    # Reduce photospheric light by (1 - gam) and add thermal Dyson dust emission
                    sf_inj = sf * (1.0 - gam) + added_jy
                    # Check trigger colors W1, W3
                    i1 = sbands.index("W1")
                    i3 = sbands.index("W3")
                    w1_inj = -2.5 * math.log10(sf_inj[i1] / BAND_INFO["W1"][1])
                    w3_inj = -2.5 * math.log10(sf_inj[i3] / BAND_INFO["W3"][1])
                    fit_i = fit_blackbody_dyson(sw, sf_inj, se, t_init=t_st)
                    if ((w1_inj - w3_inj) >= 1.0) and (fit_i["gamma"] >= 0.02) and (fit_i["delta_chi2"] >= 25.0):
                        rec_cnt += 1
                    tot_trials += 1
                tot_rec += rec_cnt
                inj_grid[f"gamma_{gam:.2f}_T_{int(tds)}K"] = {"trials": 100, "recovered": rec_cnt, "completeness": round(rec_cnt / 100.0, 4)}

    eta_n1b = tot_rec / max(1, tot_trials)
    # Also compute completeness restricted to gamma >= 0.05 (detectable partial Dyson spheres)
    rec_ge05 = sum(v["recovered"] for k, v in inj_grid.items() if not k.startswith("gamma_0.01"))
    tr_ge05 = sum(v["trials"] for k, v in inj_grid.items() if not k.startswith("gamma_0.01"))
    eta_ge05 = rec_ge05 / max(1, tr_ge05)

    n_w3_snr5 = sum(1 for r in blind_stars if r["w3snr"] >= 5.0)
    n1b_summary = {
        "clean_parallax_stars_w3snr_ge3": len(blind_stars),
        "clean_parallax_stars_w3snr_ge5": n_w3_snr5,
        "by_field": {fn: sum(1 for r in blind_stars if r["field"] == fn) for fn, _, _ in DDFS},
        "triggered_candidates": len(blind_triggers),
        "injection_trials": tot_trials,
        "injection_completeness_all_grid": round(eta_n1b, 4),
        "injection_completeness_gamma_ge_0p05": round(eta_ge05, 4),
        "injection_grid": inj_grid,
        "bounds_all_clean_gamma_ge_0p05": bayesian_bounds(len(blind_stars), len(blind_stars) * eta_ge05),
    }

    # Pillar N1C Part 2: COSMOS Pan-STARRS1 DR2 (~2012) vs Legacy DR10 (~2020) strictly inside COSMOS LS DR10 brick interior
    ps1_rows = load_tap_table(INPUTS / "vasco" / "ps1_cosmos_0p25deg.csv")
    ls_cosmos = load_tap_table(INPUTS / "dyson_blind" / "ls_dr10_COSMOS.csv")
    b_list_cos = brick_bounds.get("COSMOS", [])
    grid_ls_cos = build_grid(ls_cosmos)
    ps1_clean_pts = 0
    ps1_matched_ls = 0
    for pr in ps1_rows:
        rmag = safe_float(pr.get("rMeanPSFMag"))
        ipsf = safe_float(pr.get("iMeanPSFMag"))
        ikron = safe_float(pr.get("iMeanKronMag"))
        ndet = int(safe_float(pr.get("nDetections")) or 0)
        pra = safe_float(pr.get("raMean"))
        pdec = safe_float(pr.get("decMean"))
        if pra is None or pdec is None or rmag is None or ipsf is None or ikron is None:
            continue
        if ndet >= 5 and (14.0 <= rmag <= 20.5) and abs(ipsf - ikron) < 0.15 and in_brick_interior(pra, pdec, b_list_cos):
            ps1_clean_pts += 1
            lh = query_grid(grid_ls_cos, pra, pdec, 2.5)
            if lh:
                ps1_matched_ls += 1
            else:
                vasco_candidates.append({
                    "channel": "PS1_DR2_VS_LS_DR10_MISSING",
                    "field": "COSMOS",
                    "source_id": pr.get("objID", ""),
                    "ra_deg": round(pra, 7),
                    "dec_deg": round(pdec, 7),
                    "g_mag": round(rmag, 3),
                    "rp_mag": round(ipsf, 3),
                    "pm_masyr": 0.0,
                    "ls_flux_r": None,
                    "ls_mag_r": None,
                    "ls_mag_z": None,
                    "delta_mag": None,
                    "ls_maskbits": "",
                    "prelim_reason": "NO_LS_DR10_MATCH_2P5ARCSEC",
                })

    n1c_summary = {
        "gaia_stars_screened_0p46deg_3ddfs": vasco_gaia_total,
        "gaia_matched_ls_dr10": vasco_gaia_matched_ls,
        "ps1_cosmos_point_sources_screened": ps1_clean_pts,
        "ps1_matched_ls_dr10": ps1_matched_ls,
        "total_preliminary_candidates": len(vasco_candidates),
        "bounds_gaia_vanishing": bayesian_bounds(vasco_gaia_total, float(vasco_gaia_total)),
        "bounds_ps1_vanishing": bayesian_bounds(ps1_clean_pts, float(ps1_clean_pts)),
    }
    return n1b_summary, blind_stars, n1c_summary, vasco_candidates


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    ml_p = RESULTS / "METHOD_LOCK.json"
    if ml_p.exists():
        ml = json.loads(ml_p.read_text(encoding="utf-8"))
        for rel, exp in ml.get("sha256", {}).items():
            actual = hashlib.sha256((WS / rel).read_bytes()).hexdigest()
            assert actual == exp, f"METHOD_LOCK mismatch on {rel}"

    heph = analyze_n1a_hephaistos()
    with (RESULTS / "N1A_HEPHAISTOS_7CANDIDATES.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(heph[0].keys()))
        w.writeheader()
        for r in heph:
            w.writerow(r)

    n1b_sum, n1b_stars, n1c_sum, n1c_cands = analyze_n1b_and_n1c()
    with (RESULTS / "N1B_BLIND_ALL_STARS.csv").open("w", newline="", encoding="utf-8") as fh:
        if n1b_stars:
            w = csv.DictWriter(fh, fieldnames=list(n1b_stars[0].keys()))
            w.writeheader()
            for r in n1b_stars:
                w.writerow(r)
    n1b_trigs = [r for r in n1b_stars if r["triggered"]]
    with (RESULTS / "N1B_BLIND_DYSON_CANDIDATES.csv").open("w", newline="", encoding="utf-8") as fh:
        fn = list(n1b_stars[0].keys()) if n1b_stars else ["gaia_source_id"]
        w = csv.DictWriter(fh, fieldnames=fn)
        w.writeheader()
        for r in n1b_trigs:
            w.writerow(r)

    with (RESULTS / "N1C_VASCO_CANDIDATES.csv").open("w", newline="", encoding="utf-8") as fh:
        fn_c = ["channel", "field", "source_id", "ra_deg", "dec_deg", "g_mag", "rp_mag", "pm_masyr", "ls_flux_r", "ls_mag_r", "ls_mag_z", "delta_mag", "ls_maskbits", "prelim_reason"]
        w = csv.DictWriter(fh, fieldnames=fn_c)
        w.writeheader()
        for r in n1c_cands:
            w.writerow(r)

    summary = {
        "campaign": "SPOR_N1_DYSON_HEPHAISTOS_AND_VASCO",
        "n1a_hephaistos": {
            "candidates": len(heph),
            "dispositions": dict(collections.Counter(r["disposition"] for r in heph)),
        },
        "n1b_blind_dyson": n1b_sum,
        "n1c_vasco": n1c_sum,
        "verified_eti": 0,
    }
    (RESULTS / "N1_ANALYZER_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
